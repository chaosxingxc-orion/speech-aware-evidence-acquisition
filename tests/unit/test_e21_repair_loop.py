"""The ``obs-repair-loop`` policy and the delivered-text recovery.

Three layers, smallest first:

1. the window recovery in ``analysis.e21_window_pairing`` -- the additive
   ``obs_delivered_text`` branch, and the proof that a trace WITHOUT the key
   reads exactly as it did before;
2. ``RepairWindowHook`` on its own -- what a window's request carries, and the
   bounds refusal;
3. the whole policy through the real ``run_experiment_bundled``, so the
   delivered spans, the sealed trace, the stitched outputs row and the
   window-pairing recovery all agree on the same bytes.
"""

from __future__ import annotations

import hashlib
import json
import random
import subprocess
from array import array
from dataclasses import dataclass

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import POLICIES
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import (
    load_split,
    run_experiment_bundled,
)
from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
    BINDING_SCHEMA,
    SNAPSHOT_SCHEMA,
    window_text_chain_sha256,
)
from speech_aware_evidence_acquisition.core.repair_alignment import (
    accept_entity_repair,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import freeze_splits
from speech_aware_evidence_acquisition.reproduction import obs_loop
from speech_aware_evidence_acquisition.reproduction.obs_loop import ObsLoopError
from speech_aware_evidence_acquisition.reproduction.repair_loop import (
    OBS_REPAIR_LOOP_POLICY_NAME,
    REPAIR_FRAME_V1,
    RepairWindowHook,
)

RATE = 16000
RUN_ID = "SAEA-E-000-repairloop-e2e"
BINDING_RELPATH = "receipts/test-predecessor-binding.json"
ARTIFACT_RELPATH = "derived/e21-predecessor/test/window-hypotheses.json"
E21_IDS = ("4000001", "4000002", "4000003")

#: 45-second windows over the fixture's 90 seconds: two per call.
BUFFER_SECONDS = 45.0
PASS1_TEXT = {
    (sample_id, index): (
        f"good morning everyone this is window {index} of call {sample_id} "
        "and I will now hand over to Brett Ponton for the operational review"
    )
    for sample_id in E21_IDS
    for index in (1, 2)
}


# ---------------------------------------------------------------------------
# 1. The recovery: a delivered span, and the untouched old shape.
# ---------------------------------------------------------------------------


def _trace(tmp_path, spans, *, delivered=None, saturated=None):
    """A trace shaped like ``obs_loop`` emits, optionally carrying a policy's
    own ``obs_delivered_text`` per window."""

    lines: list[dict] = []
    request_ids = []
    for index, (text, start, end) in enumerate(spans, start=1):
        request_id = f"req-0001-i{index:04d}"
        request_ids.append(request_id)
        obs_payload = {
            "obs_iteration": index,
            "obs_window_start_seconds": start,
            "obs_window_end_seconds": end,
            "obs_saturated": request_id == saturated,
        }
        if delivered is not None:
            obs_payload["obs_delivered_text"] = delivered[index - 1]
            obs_payload["obs_repair"] = True
        lines.append(
            {
                "channel": "MODEL_REQUEST",
                "record_id": f"{request_id}/request",
                "payload": {
                    "arm": "bare-core",
                    "payload": {"sample_id": "4320211", "audio_seconds": end - start},
                },
            }
        )
        lines.append(
            {"channel": "OBS", "record_id": f"{request_id}/obs", "payload": obs_payload}
        )
        lines.append(
            {
                "channel": "MODEL_RESPONSE",
                "record_id": f"{request_id}/response",
                "payload": {"text": text},
            }
        )
    lines.append(
        {
            "channel": "MODEL_REQUEST",
            "record_id": "req-0001/request",
            "payload": {"stitch": True, "stitched_request_ids": request_ids},
        }
    )
    lines.append(
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "req-0001/response",
            "payload": {"stitch": True, "text": "ignored"},
        }
    )
    path = tmp_path / "trace.jsonl"
    path.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8"
    )
    return path


SPANS = [("raw one", 0.0, 90.0), ("raw two", 90.0, 180.0)]


class TestDeliveredTextRecovery:
    def test_a_trace_without_the_key_reads_exactly_as_before(self, tmp_path):
        windows = wp.stitched_windows_from_trace(_trace(tmp_path, SPANS))
        assert [span.text for span in windows["4320211"]] == ["raw one", "raw two"]

    def test_a_saturated_window_without_the_key_still_contributes_nothing(self, tmp_path):
        path = _trace(tmp_path, SPANS, saturated="req-0001-i0002")
        windows = wp.stitched_windows_from_trace(path)
        assert [span.text for span in windows["4320211"]] == ["raw one", ""]
        assert windows["4320211"][1].saturated is True

    def test_the_delivered_span_wins_when_the_policy_recorded_one(self, tmp_path):
        path = _trace(
            tmp_path, SPANS, delivered=["delivered one", "delivered two"]
        )
        windows = wp.stitched_windows_from_trace(path)
        assert [span.text for span in windows["4320211"]] == [
            "delivered one",
            "delivered two",
        ]

    def test_a_saturated_repair_window_delivers_its_predecessor_not_the_empty_string(
        self, tmp_path
    ):
        path = _trace(
            tmp_path,
            SPANS,
            delivered=["delivered one", "the sealed pass one text"],
            saturated="req-0001-i0002",
        )
        windows = wp.stitched_windows_from_trace(path)
        assert windows["4320211"][1].saturated is True
        assert windows["4320211"][1].text == "the sealed pass one text"
        assert wp.stitched_text(windows["4320211"]) == (
            "delivered one the sealed pass one text"
        )


# ---------------------------------------------------------------------------
# 2. The hook on its own.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Record:
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class _Predecessor:
    window_id: str
    start_seconds: float
    end_seconds: float
    text: str
    text_sha256: str = "0" * 64


def _hook(**kwargs):
    predecessors = kwargs.pop(
        "predecessors",
        (
            _Predecessor("4000001#w0001", 0.0, 45.0, "hand over to Brett Ponton now"),
            _Predecessor("4000001#w0002", 45.0, 90.0, "revenue grew eleven percent"),
        ),
    )
    return RepairWindowHook(
        sample_id="4000001",
        predecessors=predecessors,
        frame=REPAIR_FRAME_V1,
        rule=lambda pass1, response: accept_entity_repair(
            pass1, response, max_substituted_fraction=1.0
        ),
        **kwargs,
    )


class TestHook:
    def test_the_instruction_appends_the_windows_own_predecessor(self):
        hook = _hook()
        rendered = hook.instruction(
            iteration=1, record=_Record(45.0, 90.0), default="Base instruction."
        )
        assert rendered.startswith("Base instruction.\n\n")
        assert "revenue grew eleven percent" in rendered
        assert "Brett Ponton" not in rendered
        assert "not a reference transcript" in rendered

    def test_the_delivery_is_the_repaired_predecessor_not_the_response(self):
        hook = _hook()
        delivered, fields = hook.accept(
            iteration=0,
            record=_Record(0.0, 45.0),
            transcript="hand over to Brent Ponton now",
            saturated=False,
            skipped=False,
        )
        assert delivered == "hand over to Brent Ponton now"
        assert fields["obs_delivered_text"] == delivered
        assert fields["obs_repair"] is True
        assert fields["obs_repair_predecessor_window_id"] == "4000001#w0001"
        assert fields["obs_repair_substitutions"] == 1

    def test_a_saturated_pass_two_delivers_the_predecessor_and_is_a_named_refusal(self):
        hook = _hook()
        delivered, fields = hook.accept(
            iteration=0,
            record=_Record(0.0, 45.0),
            transcript="",
            saturated=True,
            skipped=False,
        )
        assert delivered == "hand over to Brett Ponton now"
        assert fields["obs_repair_refused"] is True
        assert fields["obs_repair_refusal_reason"] == "empty_response"
        assert fields["obs_repair_pass2_saturated"] is True

    def test_a_bounds_mismatch_refuses_rather_than_repairing_the_wrong_window(self):
        hook = _hook()
        with pytest.raises(ObsLoopError, match="not tiling the same audio"):
            hook.instruction(
                iteration=0, record=_Record(0.0, 90.0), default="Base instruction."
            )

    def test_a_window_beyond_the_sealed_tiling_refuses(self):
        hook = _hook()
        with pytest.raises(ObsLoopError, match="only 2"):
            hook.instruction(
                iteration=2, record=_Record(90.0, 135.0), default="Base instruction."
            )


# ---------------------------------------------------------------------------
# 2b. The hook under a SELECTIVE RE-LISTEN plan (E21-LOOP-1).
# ---------------------------------------------------------------------------


W1 = "good morning everyone and welcome i will hand over to Brett Ponton our chief now"
W2 = "revenue grew eleven percent in the quarter and margins held steady overall"
W3 = "with that we will take your questions from the analysts on the line"

RELISTEN_WINDOWS = (
    _Predecessor("4000001#w0001", 0.0, 45.0, W1),
    _Predecessor("4000001#w0002", 45.0, 90.0, W2),
    _Predecessor("4000001#w0003", 90.0, 135.0, W3),
)


def _plan_unit(index, parent, start, end, word_start, word_end):
    return obs_loop.PlannedUnit(
        unit_id=f"4000001#u{index:04d}",
        unit_index=index,
        start_seconds=start,
        end_seconds=end,
        speaker=None,
        end_cut="recut",
        parent_window_index=parent,
        predecessor_word_start=word_start,
        predecessor_word_end=word_end,
    )


class TestSelectiveRelistenHook:
    """One unit per FLAGGED window: the contact hears a narrower cut, is shown
    the matching words of its own pass-1 text, and the windows nobody
    criticised are delivered from the predecessor without a contact."""

    def _hook(self, units):
        return _hook(predecessors=RELISTEN_WINDOWS, units=units)

    def test_the_instruction_carries_the_recut_span_words_not_the_whole_window(self):
        hook = self._hook([_plan_unit(1, 1, 10.0, 25.0, 4, 15)])
        rendered = hook.instruction(
            iteration=0, record=_Record(10.0, 25.0), default="Base instruction."
        )
        assert '"welcome i will hand over to Brett Ponton our chief now"' in rendered
        assert "good morning" not in rendered

    def test_the_repaired_subspan_is_reseated_in_its_own_window(self):
        hook = self._hook([_plan_unit(1, 1, 10.0, 25.0, 4, 15)])
        delivered, fields = hook.accept(
            iteration=0,
            record=_Record(10.0, 25.0),
            transcript="welcome i will hand over to Brett Ponten our chief now",
            saturated=False,
            skipped=False,
        )
        assert fields["obs_repair_substitutions"] == 1
        assert fields["obs_relisten_window_text"] == W1.replace("Ponton", "Ponten")
        assert fields["obs_relisten_predecessor_word_start"] == 4
        assert fields["obs_relisten_predecessor_word_end"] == 15
        assert fields["obs_relisten_recut_seconds"] == 15.0
        # Window 1 is the only unit, so this delivery also back-fills the two
        # windows nobody criticised.
        assert delivered == " ".join([W1.replace("Ponton", "Ponten"), W2, W3])
        assert fields["obs_relisten_backfilled_windows"] == 2
        assert hook.uncontacted_windows == 2

    def test_the_gap_before_a_flagged_window_is_delivered_by_that_unit(self):
        hook = self._hook([_plan_unit(1, 2, 50.0, 70.0, 0, 12)])
        delivered, _fields = hook.accept(
            iteration=0,
            record=_Record(50.0, 70.0),
            transcript=W2,
            saturated=False,
            skipped=False,
        )
        assert delivered == " ".join([W1, W2, W3])

    def test_two_units_partition_the_call_between_them(self):
        hook = self._hook(
            [
                _plan_unit(1, 1, 10.0, 25.0, 4, 15),
                _plan_unit(2, 3, 95.0, 115.0, 0, 13),
            ]
        )
        first, _ = hook.accept(
            iteration=0, record=_Record(10.0, 25.0),
            transcript="welcome i will hand over to Brett Ponten our chief now",
            saturated=False, skipped=False,
        )
        second, _ = hook.accept(
            iteration=1, record=_Record(95.0, 115.0),
            transcript=W3, saturated=False, skipped=False,
        )
        assert f"{first} {second}" == " ".join(
            [W1.replace("Ponton", "Ponten"), W2, W3]
        )
        assert hook.uncontacted_windows == 1

    def test_a_refused_response_still_delivers_the_whole_call(self):
        hook = self._hook([_plan_unit(1, 2, 50.0, 70.0, 0, 12)])
        delivered, fields = hook.accept(
            iteration=0, record=_Record(50.0, 70.0),
            transcript="", saturated=True, skipped=False,
        )
        assert fields["obs_repair_refused"] is True
        assert delivered == " ".join([W1, W2, W3])

    def test_a_recut_that_leaves_its_parent_window_is_refused(self):
        hook = self._hook([_plan_unit(1, 1, 10.0, 60.0, 4, 15)])
        with pytest.raises(ObsLoopError, match="narrower look"):
            hook.instruction(
                iteration=0, record=_Record(10.0, 60.0), default="Base instruction."
            )

    def test_a_word_range_the_predecessor_cannot_carry_is_refused(self):
        hook = self._hook([_plan_unit(1, 1, 10.0, 25.0, 4, 99)])
        with pytest.raises(ObsLoopError, match="built against a different pass-1 text"):
            hook.instruction(
                iteration=0, record=_Record(10.0, 25.0), default="Base instruction."
            )

    def test_a_unit_beyond_the_plan_refuses(self):
        hook = self._hook([_plan_unit(1, 1, 10.0, 25.0, 4, 15)])
        with pytest.raises(ObsLoopError, match="carries only 1"):
            hook.instruction(
                iteration=1, record=_Record(10.0, 25.0), default="Base instruction."
            )

    def test_without_a_plan_the_hook_is_kc_e1fs_byte_for_byte(self):
        """The null arm: no units, no re-listen field anywhere, and the whole
        window's own text on the wire and in the delivery."""

        hook = _hook(predecessors=RELISTEN_WINDOWS)
        rendered = hook.instruction(
            iteration=0, record=_Record(0.0, 45.0), default="Base instruction."
        )
        assert f'"{W1}"' in rendered
        delivered, fields = hook.accept(
            iteration=0, record=_Record(0.0, 45.0),
            transcript=W1.replace("Ponton", "Ponten"), saturated=False, skipped=False,
        )
        assert delivered == W1.replace("Ponton", "Ponten")
        assert not [key for key in fields if key.startswith("obs_relisten")]
        assert hook.uncontacted_windows == 0


# ---------------------------------------------------------------------------
# 3. The whole policy, through the real driver.
# ---------------------------------------------------------------------------


def _noise(seconds: float, seed: int = 11) -> array:
    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


def _git(repo_root, *args):
    subprocess.run(
        ["git", *args], cwd=repo_root, check=True, capture_output=True, text=True
    )


def _write_binding(repo_root, data_root):
    rows = []
    for sample_id in E21_IDS:
        for index in (1, 2):
            text = PASS1_TEXT[(sample_id, index)]
            rows.append(
                {
                    "window_id": f"{sample_id}#w{index:04d}",
                    "sample_id": sample_id,
                    "window_index": index,
                    "request_id": f"req-x-i{index:04d}",
                    "start_seconds": BUFFER_SECONDS * (index - 1),
                    "end_seconds": BUFFER_SECONDS * index,
                    "audio_seconds": BUFFER_SECONDS,
                    "saturated": False,
                    "text": text,
                    "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "prompt_tokens": 100,
                    "completion_tokens": 30,
                }
            )
    artifact = data_root / ARTIFACT_RELPATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(
        json.dumps(
            {
                "schema": SNAPSHOT_SCHEMA,
                "run_id": "SAEA-E21-TEST",
                "attempt_id": "attempt-test",
                "windows": len(rows),
                "calls": len(E21_IDS),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    blob = artifact.read_bytes()
    receipt_path = repo_root / "docs" / BINDING_RELPATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {
                "schema": BINDING_SCHEMA,
                "run_id": "SAEA-E21-TEST",
                "attempt_id": "attempt-test",
                "artifact": {
                    "relpath": ARTIFACT_RELPATH,
                    "sha256": hashlib.sha256(blob).hexdigest(),
                    "bytes": len(blob),
                },
                "windows": len(rows),
                "calls": len(E21_IDS),
                "window_text_sha256_chain": window_text_chain_sha256(rows),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(receipt_path.read_bytes()).hexdigest()


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _composed(receipt_sha256, **overrides):
    values = {
        "carrier_lock_key": "earnings21-original",
        "split_name": "discovery",
        "arm": "bare-core",
        "policy": OBS_REPAIR_LOOP_POLICY_NAME,
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["asr-wer"],
        "task_instruction": "Repair only the named entities.",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-000",
        "predecessor_snapshot": {
            "receipt_relpath": BINDING_RELPATH,
            "receipt_sha256": receipt_sha256,
        },
        "repair_frame": "e21-entity-repair-frame-v1",
        "response_postprocessor": "e21-entity-repair-substitutions-v1",
        "response_postprocessor_params": {"max_substituted_fraction": 0.25},
        "obs_buffer_seconds": BUFFER_SECONDS,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 45,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 45,
        "obs_boundary_mode": "fixed",
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
        "obs_batch_slices": 2,
    }
    values.update(overrides)
    return ComposedConfig(
        values=values,
        config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )


def _predecessor_of(payload) -> str:
    """The predecessor this request actually carried, read back off the wire."""

    instruction = payload["task_instruction"]
    marker = 'instruction):\n"'
    start = instruction.index(marker) + len(marker)
    return instruction[start:-1]


def _transport_factory(edit):
    def transport(request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        return json.dumps(
            {
                "text": edit(_predecessor_of(payload)),
                "usage": {"prompt_tokens": 3},
            }
        ).encode()

    return transport


@pytest.fixture()
def repair_repo(synthetic_world, tmp_path, monkeypatch):
    monkeypatch.setattr(
        obs_loop, "decode_parent_pcm", lambda path, rate=RATE: _noise(90.0)
    )
    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    manifest_entries = []
    for sample_id in E21_IDS:
        nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / f"{sample_id}.nlp"
        nlp.write_text("token|tags\nhello|\nworld|\n", encoding="utf-8")
        raw = nlp.read_bytes()
        manifest_entries.append(
            {"id": sample_id, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        )
    artifacts_dir = receipts / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    (artifacts_dir / "d1-identity.json").write_text(
        json.dumps(
            {
                "carriers": {
                    "earnings21-original": {
                        "layers": {"nlp_references": {"manifest": manifest_entries}}
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (receipts / "e0-closure.json").write_text(
        json.dumps(
            {"deliverables": {"d1_identity": {"artifact": "artifacts/d1-identity.json"}}}
        ),
        encoding="utf-8",
    )
    receipt_sha256 = _write_binding(repo_root, synthetic_world.data_root)
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "repair loop snapshot")
    return lock, repo_root, receipt_sha256


def _run(synthetic_world, tmp_path, repair_repo, transport, *, run_id=RUN_ID, **overrides):
    lock, repo_root, receipt_sha256 = repair_repo
    _ids, split_hash, _ = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    composed = _composed(receipt_sha256, **overrides)
    plan = ExecutionPlan(
        run_id=run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=20,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash(
            composed.config_hash, composed.values["arm"], split_hash
        ),
        attempt_id=f"attempt-{run_id}",
    )
    run_dir = tmp_path / run_id
    manifest_path = run_experiment_bundled(
        composed, plan, _OpenGate(), lock, synthetic_world.data_root,
        run_dir, transport, repo_root=repo_root,
    )
    return manifest_path, run_dir


class TestPolicyEndToEnd:
    def test_the_policy_id_resolves_in_the_core_base_registry(self):
        assert POLICIES.resolve(OBS_REPAIR_LOOP_POLICY_NAME) is not None

    def test_a_name_repair_reaches_the_stitched_row_and_nothing_else_does(
        self, synthetic_world, tmp_path, repair_repo
    ):
        manifest_path, run_dir = _run(
            synthetic_world,
            tmp_path,
            repair_repo,
            _transport_factory(lambda text: text.replace("Ponton", "Pontone")),
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "COMPLETED"
        assert manifest["cost"]["calls_used"] == 6  # 3 calls x 2 windows, ONE pass

        rows = [
            json.loads(line)
            for line in (run_dir / f"{RUN_ID}.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        for row in rows:
            expected = " ".join(
                PASS1_TEXT[(row["sample_id"], index)].replace("Ponton", "Pontone")
                for index in (1, 2)
            )
            assert row["text"] == expected

    def test_an_inserting_response_changes_nothing_at_all(
        self, synthetic_world, tmp_path, repair_repo
    ):
        manifest_path, run_dir = _run(
            synthetic_world,
            tmp_path,
            repair_repo,
            _transport_factory(lambda text: text + " and thank you all for joining"),
            run_id="SAEA-E-000-repairloop-insert",
        )
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "COMPLETED"
        rows = [
            json.loads(line)
            for line in (run_dir / "SAEA-E-000-repairloop-insert.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        for row in rows:
            sealed = " ".join(PASS1_TEXT[(row["sample_id"], index)] for index in (1, 2))
            assert row["text"] == sealed

    def test_a_garbage_response_delivers_the_sealed_predecessor(
        self, synthetic_world, tmp_path, repair_repo
    ):
        manifest_path, run_dir = _run(
            synthetic_world,
            tmp_path,
            repair_repo,
            _transport_factory(lambda text: "I cannot help with that request."),
            run_id="SAEA-E-000-repairloop-garbage",
        )
        assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "COMPLETED"
        rows = [
            json.loads(line)
            for line in (run_dir / "SAEA-E-000-repairloop-garbage.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        for row in rows:
            sealed = " ".join(PASS1_TEXT[(row["sample_id"], index)] for index in (1, 2))
            assert row["text"] == sealed

    def test_the_sealed_trace_recovers_the_delivered_windows_exactly(
        self, synthetic_world, tmp_path, repair_repo
    ):
        _manifest_path, run_dir = _run(
            synthetic_world,
            tmp_path,
            repair_repo,
            _transport_factory(lambda text: text.replace("Ponton", "Pontone")),
            run_id="SAEA-E-000-repairloop-trace",
        )
        run_id = "SAEA-E-000-repairloop-trace"
        windows = wp.stitched_windows_from_trace(run_dir / f"{run_id}.trace.jsonl")
        outputs = {
            json.loads(line)["sample_id"]: json.loads(line)["text"]
            for line in (run_dir / f"{run_id}.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        }
        # The whole point of the additive recovery branch: the same instrument
        # that decomposed KC-E1 decomposes this cell, byte for byte.
        wp.assert_stitch_reproduces_outputs(windows, outputs)
        for spans in windows.values():
            assert len(spans) == 2
            assert all("Pontone" in span.text for span in spans)

    def test_the_token_count_never_moves_off_the_predecessor(
        self, synthetic_world, tmp_path, repair_repo
    ):
        _manifest_path, run_dir = _run(
            synthetic_world,
            tmp_path,
            repair_repo,
            _transport_factory(lambda text: " ".join(text.split()[:4])),
            run_id="SAEA-E-000-repairloop-truncated",
        )
        rows = [
            json.loads(line)
            for line in (run_dir / "SAEA-E-000-repairloop-truncated.outputs.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line
        ]
        for row in rows:
            sealed = " ".join(PASS1_TEXT[(row["sample_id"], index)] for index in (1, 2))
            assert len(row["text"].split()) == len(sealed.split())

    def test_a_missing_delivery_rule_refuses_before_any_audio_is_cut(
        self, synthetic_world, tmp_path, repair_repo
    ):
        with pytest.raises(Exception, match="response_postprocessor"):
            _run(
                synthetic_world,
                tmp_path,
                repair_repo,
                _transport_factory(lambda text: text),
                run_id="SAEA-E-000-repairloop-norule",
                response_postprocessor=None,
            )
