"""obs-agent-loop policy (owner directive 2026-08-08): the model-driven OBS
segmentation loop, tested against a scripted fake adapter + a real TraceSink
+ a real SliceRegistry, with the parent decode monkeypatched to synthetic
PCM (no soundfile/ffmpeg, no model, no real audio).
"""

import hashlib
import json
import random
from array import array
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.base import POLICIES, SampleContext
from speech_aware_evidence_acquisition.core.base import EvidenceItem
from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.loader import SampleRef
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.reproduction import obs_loop
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    OBS_LOOP_POLICY_NAME,
    OBS_TAIL_FRAME_V1,
    ObsAgentLoopPolicy,
    ObsLoopConfig,
    ObsLoopError,
)

RATE = 16000
RUN_ID = "SAEA-E-000-obsloop"
SAMPLE_ID = "4000001"
PARENT_RELPATH = "datasets/earnings21-22/earnings21/media/4000001.mp3"
TEMPLATE_RELPATH = "probes/obs_boundary_v1.txt"


def _noise(seconds: float, seed: int = 3) -> array:
    rng = random.Random(seed)
    return array(
        "h", (int(6000 * (2 * rng.random() - 1)) for _ in range(int(seconds * RATE)))
    )


def _silence(seconds: float) -> array:
    return array("h", [0] * int(seconds * RATE))


def _concat(*chunks: array) -> array:
    out = array("h")
    for chunk in chunks:
        out.extend(chunk)
    return out


class _FakeResponse:
    def __init__(self, text: str, tag: str, usage: dict | None = None) -> None:
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{tag}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(f"resp-{tag}".encode()).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        # Mirrors core.model.CoreResponse.usage: a real response always
        # carries a mapping (possibly empty), never None.
        self.usage = usage if usage is not None else {}


class _ScriptedAdapter:
    """Returns the scripted texts in order and records every payload.

    ``usages`` (optional, same length as ``texts``) lets a scenario pin each
    response's ``usage`` mapping -- e.g. ``completion_tokens`` for the
    saturation tests below; a response with no entry gets ``{}``, matching a
    real transport's own "usage keys present but not this one" shape.
    """

    def __init__(self, texts: list[str], usages: list[dict | None] | None = None) -> None:
        self._texts = list(texts)
        self._usages = list(usages) if usages is not None else [None] * len(texts)
        self.payloads: list[dict] = []

    def request(self, payload):
        self.payloads.append(dict(payload))
        if not self._texts:
            raise AssertionError("policy sent more requests than the script expected")
        text = self._texts.pop(0)
        usage = self._usages.pop(0) if self._usages else None
        return _FakeResponse(text, tag=str(len(self.payloads)), usage=usage)


class _FlakyAdapter:
    """Wraps a scripted adapter: the given 1-based call indices raise
    TimeoutError('timed out') — the live E-001 slice-hang shape — exactly
    once each; a raised call consumes no scripted text (the real transport
    never returned bytes either)."""

    def __init__(self, inner, fail_calls) -> None:
        self._inner = inner
        self._fail = set(fail_calls)
        self.calls = 0
        self.failed_request_ids: list[str] = []

    def request(self, payload):
        self.calls += 1
        if self.calls in self._fail:
            self._fail.discard(self.calls)
            self.failed_request_ids.append(str(payload["request_id"]))
            raise TimeoutError("timed out")
        return self._inner.request(payload)


def _config_values(**overrides):
    values = {
        "obs_buffer_seconds": 60,
        "obs_min_advance_seconds": 20,
        "obs_max_advance_seconds": 55,
        "obs_silence_snap_seconds": 2.0,
        "obs_fallback_advance_seconds": 50,
        "obs_boundary_mode": "model",
        "obs_boundary_prompt": TEMPLATE_RELPATH,
        "obs_vad": "energy",
        "obs_vad_trim_min_seconds": 5.0,
        "obs_preprocess": [],
        "obs_condition_tail_chars": 0,
    }
    values.update(overrides)
    return values


class _World:
    def __init__(
        self,
        tmp_path: Path,
        monkeypatch,
        *,
        pcm: array,
        texts: list[str],
        values=None,
        evidence=None,
        arm="bare-core",
        usages=None,
        decoding_params=None,
        sample_id=SAMPLE_ID,
    ):
        # ``sample_id`` (OBS-E1 obs seam, 2026-09-08): every world before it
        # was the one synthetic call, and a unit plan is keyed BY call -- a
        # data-backed falsifier that replays a real sealed call needs that
        # call's own id here. Defaults to SAMPLE_ID, so every world built
        # before this parameter existed is unchanged.
        self.sample_id = str(sample_id)
        parent_relpath = PARENT_RELPATH.replace(SAMPLE_ID, self.sample_id)
        self.parent_relpath = parent_relpath
        self.data_root = tmp_path / "data"
        self.run_dir = tmp_path / "run"
        self.repo_root = tmp_path / "repo"
        parent = self.data_root / parent_relpath
        parent.parent.mkdir(parents=True)
        parent.write_bytes(b"fake-mp3-bytes-for-" + self.sample_id.encode())
        template = self.repo_root / "configs" / TEMPLATE_RELPATH
        template.parent.mkdir(parents=True)
        template.write_text(
            "After the transcript report BOUNDARY_SECONDS as instructed.\n",
            encoding="utf-8",
        )
        self.duration = len(pcm) / RATE
        monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda path, rate=RATE: pcm)
        self.registry = SliceRegistry(
            data_root=self.data_root,
            run_id=RUN_ID,
            parent_facts={self.sample_id: (parent_relpath, self.duration)},
        )
        self.adapter = _ScriptedAdapter(texts, usages=usages)
        self.sink = TraceSink(self.run_dir, RUN_ID)
        self.ctx = SampleContext(
            sample=SampleRef(
                carrier_lock_key="earnings21-original",
                sample_id=self.sample_id,
                media_relpath=parent_relpath,
                audio_seconds=self.duration,
                sample_rate_hz=RATE,
            ),
            evidence=evidence or [],
            adapter=self.adapter,
            sink=self.sink,
            arm=arm,
            task_instruction="Transcribe the speech verbatim.",
            decoding_params=decoding_params if decoding_params is not None else {"temperature": 0},
            request_id_base="req-0001",
            extras={
                "slice_registry": self.registry,
                "data_root": self.data_root,
                "run_dir": self.run_dir,
                "repo_root": self.repo_root,
                "config_values": values or _config_values(),
            },
        )

    def run(self):
        return ObsAgentLoopPolicy().run_sample(self.ctx)


def _boundary_text(body: str, boundary: float) -> str:
    return f"TRANSCRIPT:\n{body}\nBOUNDARY_SECONDS: {boundary}"


def _obs_payloads(world) -> dict[str, dict]:
    """OBS trace records keyed by record_id -> payload (the pattern already
    inlined repeatedly above, factored out for the saturation tests below)."""

    raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
    return {
        document["record_id"]: document["payload"]
        for document in (json.loads(line) for line in raw.splitlines() if line)
        if document["record_id"].endswith("/obs")
    }


def test_policy_is_registered():
    assert POLICIES.resolve(OBS_LOOP_POLICY_NAME) is not None


class TestModelModeLoop:
    def test_three_iteration_loop_stitches_and_chains(self, tmp_path, monkeypatch):
        # 150s of speech-like noise: it0 [0,60) boundary 45 -> advance 45;
        # it1 [45,105) boundary 50 -> advance 50 -> cursor 95; it2 [95,150) final.
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
        )
        outcome = world.run()
        assert len(world.adapter.payloads) == 3
        relpaths = [p["media_relpath"] for p in world.adapter.payloads]
        assert relpaths == [
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0000.wav",
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0001.wav",
            f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0002.wav",
        ]
        assert [p["audio_seconds"] for p in world.adapter.payloads] == [60.0, 60.0, 55.0]
        # accepted: cut at last '.' inside the boundary share; final accepts all
        assert outcome.text == "First span one. Second span two. Final span three."
        assert outcome.sample_id == SAMPLE_ID
        assert outcome.request_ids == ("req-0001-i0000", "req-0001-i0001", "req-0001-i0002")
        assert outcome.response_text_sha256 == hashlib.sha256(
            outcome.text.encode("utf-8")
        ).hexdigest()
        # every slice was written and registered under the run's slice tree
        for relpath in relpaths:
            assert (world.data_root / relpath).is_file()
            assert world.registry.lookup(SAMPLE_ID, relpath) is not None

    def test_stitch_trace_records_bind_the_outputs_row_shape(self, tmp_path, monkeypatch):
        """I7: {base}/request + {base}/response records carry exactly the
        hashes/text the outputs row will carry (the bundle cross-check reads
        these fields verbatim)."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("Alpha beta. Gamma", 45),
                _boundary_text("Delta done.", 20),
            ],
        )
        outcome = world.run()
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        request_record = records["req-0001/request"]
        response_record = records["req-0001/response"]
        assert request_record["payload"]["payload_sha256"] == outcome.request_sha256
        assert request_record["payload"]["stitch"] is True
        assert response_record["payload"]["text"] == outcome.text
        assert response_record["payload"]["response_sha256"] == outcome.response_sha256
        assert (
            response_record["payload"]["response_text_sha256"]
            == outcome.response_text_sha256
        )
        assert records["req-0001/use"]["payload"]["use_admitted"] is True
        # per-iteration OBS records exist and carry the boundary tiers
        obs_payload = records["req-0001-i0000/obs"]["payload"]
        assert obs_payload["obs_boundary_estimate_seconds"] == 45.0
        assert obs_payload["obs_boundary_fallback"] is False

    def test_unparseable_boundary_falls_back_and_flags(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                "no boundary line at all here.",
                _boundary_text("Tail end.", 10),
            ],
        )
        world.run()
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        first = records["req-0001-i0000/obs"]
        assert first["obs_boundary_fallback"] is True
        assert first["obs_boundary_advance_seconds"] == 50.0

    def test_derivation_record_is_written_lf(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
        )
        world.run()
        record_path = world.run_dir / f"{RUN_ID}.obs-derivation.{SAMPLE_ID}.json"
        raw = record_path.read_bytes()
        assert b"\r" not in raw
        document = json.loads(raw.decode("utf-8"))
        assert document["schema"] == "saea-obs-derivation-v1"
        assert document["sample_id"] == SAMPLE_ID
        assert len(document["slices"]) == 2
        assert document["slices"][0]["parent_media_relpath"] == PARENT_RELPATH


class TestFixedModeAblation:
    def test_fixed_windows_no_boundary_prompt(self, tmp_path, monkeypatch):
        values = _config_values(
            obs_buffer_seconds=30,
            obs_min_advance_seconds=30,
            obs_max_advance_seconds=30,
            obs_fallback_advance_seconds=30,
            obs_silence_snap_seconds=0,
            obs_boundary_mode="fixed",
            obs_vad_trim_min_seconds=0,
        )
        values.pop("obs_boundary_prompt")
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
        outcome = world.run()
        assert [p["audio_seconds"] for p in world.adapter.payloads] == [30.0, 30.0, 15.0]
        for payload in world.adapter.payloads:
            assert payload["task_instruction"] == "Transcribe the speech verbatim."
        assert outcome.text == "span one span two span three"


class TestVadPreTrim:
    def test_long_leading_silence_is_skipped_and_not_metered(self, tmp_path, monkeypatch):
        # 10s leading silence + 55s speech: the trimmed window [~10, 65) fits
        # one final buffer (frame-granular trim can land at 9.99, still final).
        pcm = _concat(_silence(10.0), _noise(55.0))
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=pcm,
            texts=[_boundary_text("Speech only.", 30)],
        )
        outcome = world.run()
        assert len(world.adapter.payloads) == 1
        payload = world.adapter.payloads[0]
        # window starts after the trimmed silence and never re-covers it
        record = world.registry.lookup(SAMPLE_ID, payload["media_relpath"])
        assert record.start_seconds == pytest.approx(10.0, abs=0.6)
        assert payload["audio_seconds"] == pytest.approx(
            world.duration - record.start_seconds, abs=0.01
        )
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        trim_records = [line for line in raw.splitlines() if "obs_trim_to_seconds" in line]
        assert len(trim_records) == 1
        assert outcome.text == "Speech only."


class TestTailConditioning:
    def test_tail_rides_in_the_instruction(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                # boundary 50/60 -> share 0.833 -> the window includes the '.'
                # so the accepted span is exactly the first sentence
                _boundary_text("First accepted span ends here. Trailing", 50),
                _boundary_text("Second.", 10),
            ],
            values=_config_values(obs_condition_tail_chars=12),
        )
        world.run()
        first_instruction = world.adapter.payloads[0]["task_instruction"]
        second_instruction = world.adapter.payloads[1]["task_instruction"]
        assert OBS_TAIL_FRAME_V1.split("{tail}")[0][:30] not in first_instruction
        expected_tail = "First accepted span ends here."[-12:]
        assert OBS_TAIL_FRAME_V1.format(tail=expected_tail) in second_instruction

    def test_zero_tail_chars_reproduces_the_unconditioned_loop_exactly(
        self, tmp_path, monkeypatch
    ):
        texts = [
            _boundary_text("First accepted span ends here. Trailing", 45),
            _boundary_text("Second.", 10),
        ]
        conditioned = _World(
            tmp_path / "a", monkeypatch, pcm=_noise(90.0), texts=list(texts),
            values=_config_values(obs_condition_tail_chars=0),
        )
        conditioned.run()
        plain_instruction = conditioned.ctx.task_instruction
        for payload in conditioned.adapter.payloads:
            assert "transcript so far" not in payload["task_instruction"]
            assert payload["task_instruction"].startswith(plain_instruction)


class TestEvidenceEveryIteration:
    def test_supplied_evidence_rides_every_request(self, tmp_path, monkeypatch):
        item = EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="ACME Corp, Q3, John Smith",
            provenance={"lock_key": "conec", "relpath": "x", "sha256": "e" * 64},
        )
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
            evidence=[item],
            arm="fixed-legal-context",
        )
        world.run()
        for payload in world.adapter.payloads:
            assert payload["supplied_evidence"][0]["content"] == "ACME Corp, Q3, John Smith"

    def test_empty_by_materialization_evidence_is_tolerated(self, tmp_path, monkeypatch):
        """SAEA-P2 abort fix (2026-08-15 P2 abort): an evidence-bearing arm
        whose resolved evidence is an empty list BECAUSE this run's
        evidence_source is a legitimately-empty derived-candidates
        materialization (core.evidence._derived_candidates module comment)
        must still complete -- build_arm_payload attaches "supplied_evidence"
        with empty content rather than refusing the sample."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
            evidence=[],
            arm="fixed-legal-context",
            values=_config_values(
                evidence_source="derived-candidates",
                evidence_materialization_id="mat-p2-empty",
            ),
        )
        world.run()
        assert len(world.adapter.payloads) == 2
        for payload in world.adapter.payloads:
            assert payload["supplied_evidence"] == []

    def test_generic_empty_evidence_still_refuses_outside_derived_candidates(
        self, tmp_path, monkeypatch
    ):
        """The tolerance above is scoped to evidence_source="derived-
        candidates" only -- an evidence-bearing arm with empty evidence for
        any OTHER reason (e.g. evidence_source left at its "none" default)
        must keep failing loud, unchanged."""

        from speech_aware_evidence_acquisition.core.policies import ArmError

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
            evidence=[],
            arm="fixed-legal-context",
        )
        with pytest.raises(ArmError, match="requires non-empty evidence"):
            world.run()


class TestPreprocess:
    def test_rms_norm_records_pre_and_post_hashes(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(40.0),
            texts=[_boundary_text("Quiet speech.", 20)],
            values=_config_values(obs_preprocess=["rms-norm"]),
        )
        world.run()
        record = world.registry.lookup(
            SAMPLE_ID, world.adapter.payloads[0]["media_relpath"]
        )
        assert record.preprocess == ("rms-norm",)
        assert record.pre_sha256 is not None
        assert record.pre_sha256 != record.sha256


class TestConfigValidation:
    def test_min_above_max_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="min <= max"):
            ObsLoopConfig.from_values(
                _config_values(obs_min_advance_seconds=56), tmp_path
            )

    def test_unknown_obs_key_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="unknown obs-loop config keys"):
            ObsLoopConfig.from_values(
                _config_values(obs_bufffer_seconds=60), tmp_path
            )

    def test_model_mode_requires_a_boundary_prompt(self, tmp_path):
        values = _config_values()
        values.pop("obs_boundary_prompt")
        with pytest.raises(ObsLoopError, match="obs_boundary_prompt"):
            ObsLoopConfig.from_values(values, tmp_path)

    def test_missing_template_file_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="cannot read"):
            ObsLoopConfig.from_values(_config_values(), tmp_path)

    def test_unsupported_preprocess_refused(self, tmp_path):
        with pytest.raises(ObsLoopError, match="unsupported transforms"):
            ObsLoopConfig.from_values(
                _config_values(obs_preprocess=["denoise"]), tmp_path
            )

    def test_slice_retry_max_parses_and_bad_values_refuse(self, tmp_path):
        fixed = {
            "obs_boundary_mode": "fixed",
            "obs_buffer_seconds": 30,
            "obs_min_advance_seconds": 30,
            "obs_max_advance_seconds": 30,
            "obs_fallback_advance_seconds": 30,
        }
        assert ObsLoopConfig.from_values(fixed, tmp_path).slice_retry_max == 1
        assert (
            ObsLoopConfig.from_values(
                dict(fixed, obs_slice_retry_max=0), tmp_path
            ).slice_retry_max
            == 0
        )
        assert (
            ObsLoopConfig.from_values(
                dict(fixed, obs_slice_retry_max=2), tmp_path
            ).slice_retry_max
            == 2
        )
        for bad in (-1, True, 1.5, "once"):
            with pytest.raises(ObsLoopError, match="obs_slice_retry_max"):
                ObsLoopConfig.from_values(dict(fixed, obs_slice_retry_max=bad), tmp_path)

    def test_batch_samples_parses_and_bad_values_refuse(self, tmp_path):
        fixed = {
            "obs_boundary_mode": "fixed",
            "obs_buffer_seconds": 30,
            "obs_min_advance_seconds": 30,
            "obs_max_advance_seconds": 30,
            "obs_fallback_advance_seconds": 30,
        }
        assert ObsLoopConfig.from_values(fixed, tmp_path).batch_samples == 1
        assert (
            ObsLoopConfig.from_values(
                dict(fixed, obs_batch_samples=4), tmp_path
            ).batch_samples
            == 4
        )
        for bad in (0, -1, True, 1.5, "four"):
            with pytest.raises(ObsLoopError, match="obs_batch_samples"):
                ObsLoopConfig.from_values(dict(fixed, obs_batch_samples=bad), tmp_path)

    def test_missing_slice_registry_refused(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path, monkeypatch, pcm=_noise(30.0), texts=[_boundary_text("A.", 10)]
        )
        world.ctx.extras["slice_registry"] = None
        with pytest.raises(ObsLoopError, match="SliceRegistry"):
            world.run()


class TestSliceRetry:
    """Bounded per-slice retry (live E-001 finding, 2026-08-08): one slice
    request hung server-side and the whole attempt died. A retryable failure
    (timeout / FrozenCoreError) now gets ONE fresh, separately-metered
    request under a new request id; a SECOND failure is skipped (Task 2,
    2026-08-09 -- see TestSkip below for the degrade-not-abort behaviour and
    its bound), never propagated fail-closed the way it used to be."""

    def test_flaky_slice_retries_once_and_completes(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2})
        world.ctx.adapter = flaky
        outcome = world.run()
        # three attempts total: i0000 ok, i0001 timed out, i0001-r1 ok
        assert flaky.calls == 3
        assert flaky.failed_request_ids == ["req-0001-i0001"]
        assert outcome.request_ids == ("req-0001-i0000", "req-0001-i0001-r1")
        # the retry was a FRESH request: new request_id in the resent payload
        assert [p["request_id"] for p in world.adapter.payloads] == [
            "req-0001-i0000",
            "req-0001-i0001-r1",
        ]
        assert outcome.text == "First span done. Second done."
        assert outcome.skipped_slices == 0
        # audit visibility: the OBS record carries retry_of
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        assert records["req-0001-i0000/obs"]["obs_retry_of"] is None
        assert records["req-0001-i0001-r1/obs"]["obs_retry_of"] == "req-0001-i0001"

    def test_helper_retries_frozen_core_error_but_not_foreign_errors(self):
        from speech_aware_evidence_acquisition.core.model import FrozenCoreError
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        # FrozenCoreError (e.g. malformed response) is retryable
        outcomes = [FrozenCoreError("malformed"), "ok"]
        built = []

        def build(rid):
            built.append(rid)
            return {"request_id": rid}

        def flaky_request(payload):
            result = outcomes.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        rid, response, retry_of, saturated, skipped = request_slice_with_retry(
            flaky_request, build, "req-0001-i0007", 1
        )
        assert (rid, response, retry_of) == (
            "req-0001-i0007-r1",
            "ok",
            "req-0001-i0007",
        )
        # "ok" (a plain string) has no .usage attribute at all -- the missing
        # block must never crash, and never be flagged saturated.
        assert saturated is False
        assert skipped is False
        assert built == ["req-0001-i0007", "req-0001-i0007-r1"]

        # a foreign error (a bug, not a transport/core failure) never retries
        def broken_request(payload):
            raise ValueError("bug")

        with pytest.raises(ValueError):
            request_slice_with_retry(broken_request, build, "req-0001-i0008", 1)

    def test_first_attempt_success_reports_no_retry(self):
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        rid, response, retry_of, saturated, skipped = request_slice_with_retry(
            lambda payload: "ok", lambda rid: {"request_id": rid}, "req-0001-i0000", 1
        )
        assert (rid, response, retry_of) == ("req-0001-i0000", "ok", None)
        assert saturated is False
        assert skipped is False

    def test_helper_never_raises_on_retry_exhaustion(self):
        """Task 2 (2026-08-09): the raw helper itself never raises once every
        attempt is exhausted on a RETRYABLE failure -- it reports the skip
        instead (response=None, skipped=True), the id of the LAST attempt
        made, and retry_of naming the original id (a retry WAS attempted)."""

        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        def always_times_out(payload):
            raise TimeoutError("timed out")

        rid, response, retry_of, saturated, skipped = request_slice_with_retry(
            always_times_out, lambda rid: {"request_id": rid}, "req-0001-i0003", 1
        )
        assert rid == "req-0001-i0003-r1"
        assert response is None
        assert retry_of == "req-0001-i0003"
        assert saturated is False
        assert skipped is True

    def test_exhaustion_logs_each_swallowed_failure(self, caplog):
        """2026-08-11 live incident: two slices skipped on a build-time
        FrozenCoreError left NO on-disk evidence of the actual failure — the
        exception was swallowed unlogged and an ABORTED attempt never persists
        its OBS trace. Every swallowed retryable failure now emits one WARNING
        naming the attempt id, the class, and the message."""

        import logging as _logging

        from speech_aware_evidence_acquisition.core.model import FrozenCoreError
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        def always_refused(payload):
            raise FrozenCoreError("the real reason the gate refused")

        with caplog.at_level(
            _logging.WARNING,
            logger="speech_aware_evidence_acquisition.reproduction.obs_loop",
        ):
            *_, skipped = request_slice_with_retry(
                always_refused, lambda rid: {"request_id": rid}, "req-0001-i0042", 1
            )
        assert skipped is True
        warnings = [r for r in caplog.records if "failed retryably" in r.getMessage()]
        assert len(warnings) == 2  # the original attempt plus one retry
        assert "req-0001-i0042 attempt 1/2" in warnings[0].getMessage()
        assert "req-0001-i0042-r1 attempt 2/2" in warnings[1].getMessage()
        for record in warnings:
            assert "FrozenCoreError" in record.getMessage()
            assert "the real reason the gate refused" in record.getMessage()

    def test_helper_never_raises_on_retry_exhaustion_with_retries_disabled(self):
        """retry_max=0 exhausts on the FIRST failure -- still a skip, never a
        raise, and retry_of is None (no retry was ever attempted)."""

        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            request_slice_with_retry,
        )

        def always_times_out(payload):
            raise TimeoutError("timed out")

        rid, response, retry_of, saturated, skipped = request_slice_with_retry(
            always_times_out, lambda rid: {"request_id": rid}, "req-0001-i0004", 0
        )
        assert rid == "req-0001-i0004"
        assert response is None
        assert retry_of is None
        assert saturated is False
        assert skipped is True


class TestSaturation:
    """Per-slice decode-cap saturation (2026-08-09, continues the retry
    finding above SLICE_RETRYABLE_EXCEPTIONS): a slice whose completion hits
    the configured decoding_params.max_tokens cap is a runaway decode, not a
    genuine transcript end -- the exposure ledger commits to "counted and
    reported, not scored silently"."""

    def test_slice_under_the_cap_is_not_flagged(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
            usages=[{"completion_tokens": 4}, {"completion_tokens": 3}],
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = world.run()
        assert outcome.saturated_slices == 0
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_saturated"] is False
        assert obs["req-0001-i0001/obs"]["obs_saturated"] is False

    def test_slice_exactly_at_the_cap_is_flagged(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
            # completion_tokens EQUALS max_tokens on the first slice -- the
            # boundary case (>=, not >).
            usages=[{"completion_tokens": 5}, {"completion_tokens": 4}],
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = world.run()
        assert outcome.saturated_slices == 1
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_saturated"] is True
        assert obs["req-0001-i0001/obs"]["obs_saturated"] is False

    def test_no_max_tokens_configured_never_flags(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(30.0),
            texts=[_boundary_text("Whole thing.", 10)],
            # a huge completion_tokens count would trip any cap that existed
            usages=[{"completion_tokens": 999999}],
            decoding_params={"temperature": 0},  # no max_tokens key at all
        )
        outcome = world.run()
        assert outcome.saturated_slices == 0
        assert _obs_payloads(world)["req-0001-i0000/obs"]["obs_saturated"] is False

    def test_missing_usage_never_crashes_and_never_flags(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(30.0),
            texts=[_boundary_text("Whole thing.", 10)],
            # usages omitted entirely -> _FakeResponse.usage == {} -- a real
            # response's "usage present but no completion_tokens key" shape.
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = world.run()
        assert outcome.saturated_slices == 0
        assert _obs_payloads(world)["req-0001-i0000/obs"]["obs_saturated"] is False

    def test_multiple_saturated_slices_aggregate_onto_the_outcome(
        self, tmp_path, monkeypatch
    ):
        """The per-sample aggregate (SampleOutcome.saturated_slices) counts
        every saturated slice across the sample's whole loop, not merely the
        last one or a boolean flag.

        Quarantine-era geometry (2026-08-11): a saturated slice's text and
        boundary estimate are refused, so it advances by the FALLBACK tier
        (50 s here), not its scripted 45 s boundary — the 200 s sample now
        completes in 4 slices (50 + 45 + 50 → final window), and the last
        scripted text/usage pair is simply never requested."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(200.0),
            texts=[_boundary_text(f"S{i}.", 45) for i in range(4)]
            + [_boundary_text("Last.", 10)],
            usages=[
                {"completion_tokens": 5},  # saturated -> quarantined, fallback 50
                {"completion_tokens": 2},  # not -> boundary 45
                {"completion_tokens": 5},  # saturated -> fallback 50
                {"completion_tokens": 5},  # saturated (final window)
                {"completion_tokens": 1},  # never requested
            ],
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = world.run()
        assert outcome.saturated_slices == 3
        obs = _obs_payloads(world)
        flags = [
            obs[f"req-0001-i{index:04d}/obs"]["obs_saturated"] for index in range(4)
        ]
        assert flags == [True, False, True, True]
        # The quarantined slices contribute NOTHING to the stitched text —
        # only the one healthy slice's accepted span survives.
        assert "S1" in outcome.text
        for garbage in ("S0", "S2", "S3"):
            assert garbage not in outcome.text


class TestSliceParallel:
    """Slice-level dispatch (2026-08-12): with fixed windows, no tail and no
    trim, iterations are independent — obs_batch_slices > 1 cuts every
    window upfront and dispatches concurrently, falling through to the SAME
    finalize path as the sequential loop."""

    def _values(self, **overrides):
        values = _config_values(
            obs_boundary_mode="fixed",
            obs_condition_tail_chars=0,
            obs_vad_trim_min_seconds=0,
            obs_batch_slices=3,
        )
        values.update(overrides)
        return values

    def test_legality_is_fail_closed(self, tmp_path):
        from speech_aware_evidence_acquisition.reproduction.obs_loop import (
            ObsLoopConfig,
            ObsLoopError,
        )

        for bad in (
            {"obs_boundary_mode": "model"},
            {"obs_condition_tail_chars": 400},
            {"obs_vad_trim_min_seconds": 5.0},
        ):
            with pytest.raises(ObsLoopError, match="obs_batch_slices"):
                ObsLoopConfig.from_values(self._values(**bad), tmp_path)
        ObsLoopConfig.from_values(self._values(), tmp_path)  # legal set passes

    def test_parallel_matches_sequential_and_actually_overlaps(
        self, tmp_path, monkeypatch
    ):
        """The parallel pass must reproduce the sequential fixed/notail
        outcome (same stitched text, same request-id order, full OBS trail)
        while genuinely overlapping requests."""

        import dataclasses
        import threading as _threading

        class _IndexedAdapter:
            """Thread-safe: answers by the slice index parsed from the
            request id, so concurrent arrival order cannot mis-assign
            scripted texts. Tracks peak in-flight concurrency."""

            def __init__(self, texts):
                self._texts = texts
                self._lock = _threading.Lock()
                self._in_flight = 0
                self.peak = 0
                self._gate = _threading.Semaphore(0)
                self.payloads = []

            def request(self, payload):
                idx = int(payload["request_id"].split("-i")[1].split("-")[0])
                with self._lock:
                    self.payloads.append(dict(payload))
                    self._in_flight += 1
                    self.peak = max(self.peak, self._in_flight)
                import time as _time

                _time.sleep(0.05)  # widen the overlap window
                with self._lock:
                    self._in_flight -= 1
                return _FakeResponse(self._texts[idx], payload["request_id"])

        pcm = _noise(150.0)  # 3 fixed 60s windows: 60 + 60 + 30
        texts = ["First window text.", "Second window text.", "Third window text."]
        world = _World(
            tmp_path, monkeypatch, pcm=pcm, texts=texts, values=self._values()
        )
        world.adapter = _IndexedAdapter(texts)
        world.ctx = dataclasses.replace(world.ctx, adapter=world.adapter)
        outcome = world.run()

        assert outcome.text == "First window text. Second window text. Third window text."
        assert list(outcome.request_ids) == [
            "req-0001-i0000", "req-0001-i0001", "req-0001-i0002",
        ]
        assert world.adapter.peak >= 2, "requests never overlapped"
        obs = _obs_payloads(world)
        for index in range(3):
            payload = obs[f"req-0001-i{index:04d}/obs"]
            assert payload["obs_dispatch"] == "slice-parallel"
            assert payload["obs_tail_chars_used"] == 0
            assert payload["obs_boundary_mode"] == "fixed"

    def test_slot_affinity_sentinel_resolved_per_dispatch_slot(
        self, tmp_path, monkeypatch
    ):
        """The plain parallel path resolves id_slot='per-sample' itself
        (first launch was refused fail-closed by the adapter because only the
        ojw executor resolved it): each in-flight request carries a distinct
        integer slot from a pool of size obs_batch_slices."""

        import dataclasses
        import threading as _threading

        seen = []
        lock = _threading.Lock()

        class _SentinelAdapter:
            def request(self, payload):
                idx = int(payload["request_id"].split("-i")[1].split("-")[0])
                slot = payload["decoding_params"]["id_slot"]
                with lock:
                    seen.append(slot)
                import time as _time

                _time.sleep(0.03)
                return _FakeResponse(f"T{idx}.", payload["request_id"])

        pcm = _noise(150.0)
        world = _World(
            tmp_path, monkeypatch, pcm=pcm, texts=["x"] * 3,
            values=self._values(),
            decoding_params={"temperature": 0, "id_slot": "per-sample"},
        )
        world.adapter = _SentinelAdapter()
        world.ctx = dataclasses.replace(world.ctx, adapter=world.adapter)
        outcome = world.run()
        assert outcome.text  # completed
        assert all(isinstance(s, int) and 0 <= s < 3 for s in seen), seen


def _fixed_mode_skip_values(**overrides):
    """Deterministic fixed-mode config (no VAD at all -- boundary_mode
    'fixed' and vad_trim_min_seconds 0 -- so every advance is exactly
    obs_buffer_seconds, with no seed-dependent VAD snap to hand-compute):
    the skip-bound tests below need EXACT control over which iteration is
    final and how many total iterations exist."""

    values = _config_values(
        obs_buffer_seconds=40,
        obs_min_advance_seconds=40,
        obs_max_advance_seconds=40,
        obs_fallback_advance_seconds=40,
        obs_silence_snap_seconds=0,
        obs_boundary_mode="fixed",
        obs_vad_trim_min_seconds=0,
    )
    values.pop("obs_boundary_prompt")  # fixed mode needs no boundary template
    values.update(overrides)
    return values


class TestSkip:
    """Exhausted-slice skip (Task 2, 2026-08-09, continues the E-001 retry
    finding above SLICE_RETRYABLE_EXCEPTIONS): a slice that exhausts
    obs_slice_retry_max is skipped as an honest hole -- the SAMPLE
    completes using whatever other slices succeeded -- unless the number of
    skips in one sample crosses obs_slice_skip_max (default 1), which is
    still fatal."""

    def test_exhausted_slice_is_skipped_and_the_sample_completes(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3})
        world.ctx.adapter = flaky
        outcome = world.run()  # must NOT raise -- the old behaviour aborted here
        # i0000 ok, i0001 timed out, i0001-r1 timed out -> exhausted -> skipped
        assert flaky.calls == 3
        assert flaky.failed_request_ids == ["req-0001-i0001", "req-0001-i0001-r1"]
        # the second slice's script was never even read (nothing to stitch)
        assert len(world.adapter.payloads) == 1
        assert outcome.skipped_slices == 1
        assert outcome.request_ids == ("req-0001-i0000",)
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        assert records["req-0001-i0000/obs"]["obs_skipped"] is False
        # the exhausted slice's OWN record lands under its FINAL attempt id
        # (module comment: request_id_used is the last attempt made).
        assert records["req-0001-i0001-r1/obs"]["obs_skipped"] is True
        assert records["req-0001-i0001-r1/obs"]["obs_retry_of"] == "req-0001-i0001"
        # no transcript survived that slice, so nothing was accepted from it
        assert records["req-0001-i0001-r1/obs"]["obs_accepted_chars"] == 0

    def test_skipped_slice_advances_via_the_fallback_tier(self, tmp_path, monkeypatch):
        """A skipped NON-final slice has no estimate at all -- resolved
        through the SAME fallback tier an unparseable boundary response
        already uses (obs_audio.resolve_advance with estimate=None), never
        a second advance-computation path. (The final window uses a fixed
        "consume everything" resolution regardless of skip -- this scenario
        therefore skips the FIRST slice, which is never final for a 90s
        sample over a 60s buffer, so the fallback tier genuinely fires.)"""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("Final.", 10)],
            values=_config_values(
                obs_fallback_advance_seconds=33, obs_silence_snap_seconds=0
            ),
        )
        # i0000's original attempt + its retry both time out -> skipped;
        # i0001 (the only real call) then covers the rest of the audio.
        flaky = _FlakyAdapter(world.adapter, fail_calls={1, 2})
        world.ctx.adapter = flaky
        world.run()
        obs = _obs_payloads(world)
        skipped_record = obs["req-0001-i0000-r1/obs"]
        assert skipped_record["obs_final_window"] is False
        assert skipped_record["obs_boundary_estimate_seconds"] is None
        assert skipped_record["obs_boundary_fallback"] is True
        assert skipped_record["obs_boundary_advance_seconds"] == 33

    def test_exceeding_the_skip_bound_aborts_the_sample(self, tmp_path, monkeypatch):
        """A SECOND skipped slice in the same sample crosses the default
        obs_slice_skip_max=1 -- fatal, exactly because a run that quietly
        skipped its audio must never be scorable as clean."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(120.0),
            texts=["one", "two", "three"],
            values=_fixed_mode_skip_values(),
        )
        # i0000 ok (call 1); i0001 + its retry both fail (calls 2, 3) -> skip
        # #1 (within the default bound); i0002 + its retry both fail (calls
        # 4, 5) -> skip #2 -> exceeds obs_slice_skip_max=1.
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3, 4, 5})
        world.ctx.adapter = flaky
        with pytest.raises(ObsLoopError, match="obs_slice_skip_max=1"):
            world.run()
        assert flaky.calls == 5
        # the FIRST skip's own OBS record was still emitted before the
        # second skip's bound-exceeded refusal -- reported, not swallowed.
        raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = {
            document["record_id"]: document["payload"]
            for document in (json.loads(line) for line in raw.splitlines() if line)
        }
        assert records["req-0001-i0001-r1/obs"]["obs_skipped"] is True
        assert records["req-0001-i0002-r1/obs"]["obs_skipped"] is True

    def test_skip_bound_zero_makes_any_skip_fatal(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(120.0),
            texts=["one", "two", "three"],
            values=_fixed_mode_skip_values(obs_slice_skip_max=0),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3})
        world.ctx.adapter = flaky
        with pytest.raises(ObsLoopError, match="obs_slice_skip_max=0"):
            world.run()

    def test_a_higher_configured_bound_tolerates_more_skips(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(120.0),
            texts=["one", "two", "three"],
            values=_fixed_mode_skip_values(obs_slice_skip_max=2),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3, 4, 5})
        world.ctx.adapter = flaky
        outcome = world.run()  # both skips tolerated under the raised bound
        assert outcome.skipped_slices == 2
        assert outcome.request_ids == ("req-0001-i0000",)

    def test_retry_zero_disables_retries_but_the_sample_still_completes_via_skip(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[_boundary_text("A.", 45), _boundary_text("B.", 10)],
            values=_config_values(obs_slice_retry_max=0),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2})
        world.ctx.adapter = flaky
        outcome = world.run()
        assert flaky.calls == 2  # i0000 ok, i0001 failed once, NO retry attempted
        assert outcome.skipped_slices == 1
        assert outcome.request_ids == ("req-0001-i0000",)

    def test_retry_zero_disables_retries_and_a_sole_skip_still_refuses_empty_output(
        self, tmp_path, monkeypatch
    ):
        """A sample whose ONLY slice fails is skipped (within the default
        bound) but then still hits the PRE-EXISTING empty-hypothesis guard
        -- skip degrades a sample that has OTHER surviving content, it does
        not fabricate content where literally none survived at all."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(30.0),
            texts=[_boundary_text("A.", 10)],
            values=_config_values(obs_slice_retry_max=0),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={1})
        world.ctx.adapter = flaky
        with pytest.raises(ObsLoopError, match="no successful requests"):
            world.run()
        assert flaky.calls == 1


class TestBudgetArithmeticSanity:
    def test_iteration_count_matches_the_ceiling_model(self, tmp_path, monkeypatch):
        """~duration/mean_advance requests: every boundary resolves to 45s
        over 200s of audio -> cursors 0,45,90,135,180; [180,200) is final =
        5 windows; metered = 4x60 + 20 = 260s = 1.3x the call's duration
        (the tail-overlap fraction the runbook's budget arithmetic uses)."""

        texts = [_boundary_text(f"S{i}.", 45) for i in range(4)] + [
            _boundary_text("Last.", 10)
        ]
        world = _World(tmp_path, monkeypatch, pcm=_noise(200.0), texts=texts)
        world.run()
        assert len(world.adapter.payloads) == 5
        metered = sum(p["audio_seconds"] for p in world.adapter.payloads)
        assert metered == pytest.approx(60 * 4 + 20, abs=0.01)
        assert metered / world.duration == pytest.approx(1.3, abs=0.01)


class TestExemplarBank:
    """Acoustic exemplar bank (core.exemplars, M-C-prime prep infrastructure):
    every slice of a sample carries the SAME resolved
    ``SampleContext.exemplar_bank`` -- both the sequential loop and the
    slice-parallel dispatch path build every request through the SAME
    ``core.policies.build_arm_payload`` seam. No D2-frozen arm declares
    "exemplar_bank" yet (core.policies module comment), so these tests
    temporarily extend "bare-core"'s own ARM_VISIBLE_FIELDS entry
    (monkeypatch, reverted at teardown) the same way test_policies.py does,
    rather than registering a real new arm."""

    _BANK = (
        {"media_relpath": "derived/exemplar-pairs/mc2-v1/4000001/alpha.wav", "label": "alpha"},
    )

    def _with_exemplar_bank_field(self, monkeypatch):
        monkeypatch.setitem(
            ARM_VISIBLE_FIELDS, "bare-core", ARM_VISIBLE_FIELDS["bare-core"] + ("exemplar_bank",)
        )

    def test_sequential_loop_every_slice_carries_the_same_bank(self, tmp_path, monkeypatch):
        import dataclasses

        self._with_exemplar_bank_field(monkeypatch)
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
        )
        world.ctx = dataclasses.replace(world.ctx, exemplar_bank=self._BANK)
        world.run()
        assert len(world.adapter.payloads) == 3
        for payload in world.adapter.payloads:
            assert payload["exemplar_bank"] == list(self._BANK)

    def test_slice_parallel_pass_every_slice_carries_the_same_bank(self, tmp_path, monkeypatch):
        import dataclasses

        self._with_exemplar_bank_field(monkeypatch)
        values = _config_values(
            obs_boundary_mode="fixed",
            obs_condition_tail_chars=0,
            obs_vad_trim_min_seconds=0,
            obs_batch_slices=3,
        )
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(150.0),
            texts=["First.", "Second.", "Third."],
            values=values,
        )
        world.ctx = dataclasses.replace(world.ctx, exemplar_bank=self._BANK)
        world.run()
        assert len(world.adapter.payloads) == 3
        for payload in world.adapter.payloads:
            assert payload["exemplar_bank"] == list(self._BANK)

    def test_empty_bank_is_attached_as_an_empty_list_not_dropped(self, tmp_path, monkeypatch):
        import dataclasses

        self._with_exemplar_bank_field(monkeypatch)
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
        )
        world.ctx = dataclasses.replace(world.ctx, exemplar_bank=())
        world.run()
        assert len(world.adapter.payloads) == 2
        for payload in world.adapter.payloads:
            assert payload["exemplar_bank"] == []

    def test_absent_exemplar_bank_omits_the_payload_field(self, tmp_path, monkeypatch):
        """ctx.exemplar_bank defaults to None -- byte-identical to before
        this feature existed: no "exemplar_bank" key at all on any slice's
        payload, not even an empty list. Deliberately does NOT extend
        ARM_VISIBLE_FIELDS -- absence must be safe against the unmodified
        D2 freeze too."""

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
        )
        world.run()
        assert len(world.adapter.payloads) == 2
        assert all("exemplar_bank" not in payload for payload in world.adapter.payloads)


class TestDeltaCandidatesSeam:
    """obs_loop's own slice payload builder (2026-08-13, reproduction.
    replay_loop module docstring): PASS 1 has no delta candidates of its
    own to offer (RETRIEVE is a per-flagged-span REPLAY concept), but an
    arm whose D2-frozen field set declares "delta_candidates" requires the
    key on EVERY request that arm sends, PASS 1's own slice requests
    included (core.model.FrozenCoreAdapter's own allowlist demands an
    exact key-set match). obs_loop now attaches an always-empty placeholder
    exactly when the run's arm declares the field, and omits it
    (byte-identical to before this fix) for every arm that does not --
    exercised here against the REAL, D2-registered "fixed-legal-context-
    replay" arm rather than a monkeypatched field set."""

    _EVIDENCE = [
        EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="acme merger guidance",
            provenance={"lock_key": "conec", "relpath": "x.txt", "sha256": "0" * 64},
        )
    ]

    def test_an_arm_that_does_not_declare_it_never_sees_the_key(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
        )
        world.run()
        assert len(world.adapter.payloads) == 2
        assert all("delta_candidates" not in payload for payload in world.adapter.payloads)

    def test_an_arm_that_declares_it_gets_an_always_empty_placeholder_sequential(
        self, tmp_path, monkeypatch
    ):
        import dataclasses

        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(70.0),
            texts=[_boundary_text("One two. Three", 40), _boundary_text("Rest.", 5)],
            evidence=self._EVIDENCE,
            arm="fixed-legal-context-replay",
        )
        # "fixed-legal-context-replay" also declares "exemplar_bank" (its own
        # field set is fixed-legal-context's plus BOTH tiers) -- an empty,
        # non-None bank satisfies that requirement without this test caring
        # about exemplar content (TestExemplarBank above covers that).
        world.ctx = dataclasses.replace(world.ctx, exemplar_bank=())
        world.run()
        assert len(world.adapter.payloads) == 2
        for payload in world.adapter.payloads:
            assert payload["delta_candidates"] == []
            assert payload["exemplar_bank"] == []

    def test_an_arm_that_declares_it_gets_an_always_empty_placeholder_slice_parallel(
        self, tmp_path, monkeypatch
    ):
        import dataclasses

        values = _config_values(
            obs_boundary_mode="fixed",
            obs_condition_tail_chars=0,
            obs_vad_trim_min_seconds=0,
            obs_batch_slices=3,
        )
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(150.0),
            texts=["First.", "Second.", "Third."],
            values=values,
            evidence=self._EVIDENCE,
            arm="fixed-legal-context-replay",
        )
        world.ctx = dataclasses.replace(world.ctx, exemplar_bank=())
        world.run()
        assert len(world.adapter.payloads) == 3
        for payload in world.adapter.payloads:
            assert payload["delta_candidates"] == []


def test_prepared_windows_and_payloads_match_live_parallel_requests(tmp_path, monkeypatch):
    pcm = _noise(90)
    values = _config_values(obs_boundary_mode="fixed", obs_vad_trim_min_seconds=0,
                            obs_condition_tail_chars=0, obs_batch_slices=3)
    world = _World(tmp_path, monkeypatch, pcm=pcm, texts=["first", "second"], values=values)
    cfg = ObsLoopConfig.from_values(values, world.repo_root)
    windows, records = obs_loop.materialize_fixed_windows(
        cfg, world.registry, world.data_root, world.ctx.sample, RATE, pcm, 90,
        hashlib.sha256((world.data_root / world.parent_relpath).read_bytes()).hexdigest())
    prepared = []
    for window in windows:
        rid, factory = obs_loop.window_request_factory(
            world.ctx, window, sample=world.ctx.sample, rate=RATE, evidence=None)
        prepared.append(factory(rid))
    assert not world.adapter.payloads
    assert len(records) == 2
    assert [r.audio_seconds for r in records] == [60, 30]
    assert all((world.data_root / r.media_relpath).is_file() for r in records)
    world.ctx.extras["slice_registry"] = SliceRegistry(
        data_root=world.data_root, run_id=RUN_ID,
        parent_facts={SAMPLE_ID: (world.parent_relpath, world.duration)})
    world.run()
    assert sorted(prepared, key=lambda p: p["request_id"]) == sorted(
        world.adapter.payloads, key=lambda p: p["request_id"])


def test_repair_fit_materializes_all_actual_windows_without_response_or_accept(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.preparation_windows import materialize_window_requests
    from speech_aware_evidence_acquisition.reproduction.repair_loop import RepairWindowHook
    pcm = _noise(90)
    values = _config_values(obs_boundary_mode="fixed", obs_vad_trim_min_seconds=0,
                            obs_batch_slices=3, obs_condition_tail_chars=0)
    world = _World(tmp_path, monkeypatch, pcm=pcm, texts=[], values=values)
    hook = RepairWindowHook(
        sample_id=SAMPLE_ID,
        predecessors=[SimpleNamespace(start_seconds=0, end_seconds=60, text="draft first"),
                      SimpleNamespace(start_seconds=60, end_seconds=90, text="draft final")],
        frame="Correct this draft: {predecessor}",
        rule=lambda *args: pytest.fail("fit must never deliver a fabricated response"))
    batch = materialize_window_requests(
        [world.ctx], expected_sample_ids=[SAMPLE_ID],
        hook_factory=lambda *args: hook)
    assert len(batch.payloads) == 2
    assert batch.request_keys == (f"{SAMPLE_ID}#w0001", f"{SAMPLE_ID}#w0002")
    assert "draft first" in batch.payloads[0]["task_instruction"]
    assert "draft final" in batch.payloads[1]["task_instruction"]
    assert not world.adapter.payloads
    assert not hook.outcomes
    for payload, source in zip(batch.payloads, batch.source_bindings, strict=True):
        raw = (world.data_root / payload["media_relpath"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["parent_sha256"] == hashlib.sha256(
            (world.data_root / world.parent_relpath).read_bytes()).hexdigest()
        assert batch.request_key(payload) in batch.request_keys


def test_window_fit_refuses_missing_call_or_dependent_geometry(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    from speech_aware_evidence_acquisition.core.preparation_windows import materialize_window_requests
    world = _World(tmp_path, monkeypatch, pcm=_noise(5), texts=[])
    with pytest.raises(PreparationError, match="roster"):
        materialize_window_requests([world.ctx], expected_sample_ids=["foreign"])
    with pytest.raises(PreparationError, match="independent"):
        materialize_window_requests([world.ctx], expected_sample_ids=[SAMPLE_ID])
