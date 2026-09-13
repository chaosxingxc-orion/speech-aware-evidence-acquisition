"""obs-agent-loop-ojw: the openJiuwen executor against the plain reference.

Red line 3 of the adoption memo (docs/readiness/2026-08-08-openjiuwen-
adoption.md): the openJiuwen executor must reproduce the plain-Python
``obs-agent-loop`` policy's behaviour on the same inputs before any
registered run uses it. Both executors run here over the SAME synthetic
fixtures (scripted fake adapter, synthetic PCM, monkeypatched decode — the
exact ``_World`` harness of ``test_obs_loop_policy``) and must produce:

- identical accepted-span sequences (re-derived per side from that side's
  own OBS trace records through the frozen pure functions, and pinned a
  second way by the tail-conditioning scenario, whose 4000-char tail embeds
  the entire stitched-so-far text into every subsequent request payload);
- identical slice derivation records (byte-for-byte);
- identical stitched output text and outputs-row hashes;
- identical trace record sequences (only the fake adapter emits no
  MODEL_REQUEST/COST records on either side; the volatile
  ``latency_seconds`` field is stripped defensively).

Determinism: the framework body is a LINEAR four-node chain, so every
Pregel super-step has exactly one ready node; ``test_determinism_five_runs``
verifies empirically that five fresh executor runs produce byte-identical
artifacts (and match the plain reference).

Requires openjiuwen (skip marker otherwise — D2 gate: the suite must pass
with openjiuwen absent; see ``test_obs_loop_ojw_absent.py``).
"""

import asyncio
from array import array
import dataclasses
import hashlib
import json
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip(
    "openjiuwen",
    reason="openjiuwen not installed; the ojw executor is exercised only in "
    "the pinned WSL research venv (D2: never a pyproject dependency)",
)

import speech_aware_evidence_acquisition.core  # noqa: F401,E402 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan  # noqa: E402
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    POLICIES,
    EvidenceItem,
    SampleContext,
)
from speech_aware_evidence_acquisition.core.model import SliceRegistry  # noqa: E402
from speech_aware_evidence_acquisition.core.driver.run import (  # noqa: E402
    materialize_evidence_binding,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (  # noqa: E402
    materialize_window_requests,
)
from speech_aware_evidence_acquisition.core.tracing import (  # noqa: E402
    TraceBuffer,
    TraceSink,
)
from speech_aware_evidence_acquisition.data.loader import SampleRef  # noqa: E402
from speech_aware_evidence_acquisition.reproduction import obs_loop  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    accept_up_to_boundary,
    parse_boundary_response,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: E402
    OBS_LOOP_POLICY_NAME,
    ObsLoopError,
)
from speech_aware_evidence_acquisition.reproduction.ojw import OJW_POLICY_NAME  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw.components import (  # noqa: E402
    FrozenCoreASR,
)
from speech_aware_evidence_acquisition.reproduction.ojw.policy import (  # noqa: E402
    ObsAgentLoopOjwPolicy,
)
from speech_aware_evidence_acquisition.reproduction import repair_loop  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.repair_loop import (  # noqa: E402
    OBS_REPAIR_LOOP_OJW_POLICY_NAME,
    ObsRepairLoopOjwPolicy,
    build_repair_window_hook,
)

from test_obs_loop_policy import (  # noqa: E402
    RUN_ID,
    SAMPLE_ID,
    _FlakyAdapter,
    _World,
    _boundary_text,
    _concat,
    _config_values,
    _fixed_mode_skip_values,
    _noise,
    _obs_payloads,
    _silence,
)
from test_obs_unit_plan import (  # noqa: E402
    PLAN_RELPATH,
    _plan_bytes,
    _plan_document,
    _plan_values,
)


@pytest.mark.parametrize("packet_mode", [None, "query-only", "with-supply"])
def test_e21_four_row_fit_matches_real_ojw_controller_contacts(
    tmp_path, monkeypatch, synthetic_world, packet_mode
):
    """The held E21 proof fits and sends the same four synthetic requests."""
    from test_class_lists import CALL, _install

    source_root = Path(__file__).resolve().parents[2]
    plan_relpath = "docs/receipts/obs/e21-current-executor-four-row-proof-v1.json"
    plan_raw = (source_root / plan_relpath).read_bytes()
    plan = json.loads(plan_raw)
    call = plan["calls"][0]
    assert call["sample_id"] == CALL

    class VirtualPcm:
        """Represent the whole call while allocating only each selected cut."""

        def __len__(self):
            return round(call["decoded_duration_seconds"] * 16_000)

        def __getitem__(self, bounds):
            assert isinstance(bounds, slice) and bounds.step is None
            return array("h", [0]) * (bounds.stop - bounds.start)

    predecessors = []
    for parent in call["parent_windows"]:
        index = parent["window_index"]
        text = " ".join(
            f"window{index:02d}word{word:03d}"
            for word in range(parent["draft_words"])
        )
        predecessors.append(
            SimpleNamespace(
                window_id=f"{CALL}#w{index:04d}",
                start_seconds=parent["start_seconds"],
                end_seconds=parent["end_seconds"],
                text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
    snapshot = SimpleNamespace(for_sample=lambda sample_id: tuple(predecessors))
    monkeypatch.setattr(repair_loop, "_bound_snapshot", lambda *args: snapshot)

    values = json.loads(
        (source_root / "configs/baseline/e21-current-executor-four-row-proof-ojw.json")
        .read_text(encoding="utf-8")
    )
    values["predecessor_snapshot"] = {
        "receipt_relpath": "receipts/synthetic-predecessor.json",
        "receipt_sha256": "a" * 64,
    }
    values["decoding_params"] = {"temperature": 0, "max_tokens": 1024}
    values["ojw_workflow_timeout_seconds"] = 0
    targets = []
    for unit in call["units"]:
        predecessor = predecessors[unit["parent_window_index"] - 1]
        words = predecessor.text.split()
        targets.append(
            " ".join(
                words[
                    unit["predecessor_word_start"] : unit["predecessor_word_end"]
                ]
            )
        )

    world = _World(
        tmp_path,
        monkeypatch,
        pcm=VirtualPcm(),
        texts=targets,
        values=values,
        arm="fixed-legal-context",
        sample_id=CALL,
        decoding_params=values["decoding_params"],
    )
    copied_plan = world.repo_root / plan_relpath
    copied_plan.parent.mkdir(parents=True, exist_ok=True)
    copied_plan.write_bytes(plan_raw)
    assert hashlib.sha256(plan_raw).hexdigest() == values["obs_unit_plan_sha256"]

    lock = _install(synthetic_world)
    binding = materialize_evidence_binding(
        lock,
        synthetic_world.data_root,
        [world.ctx.sample],
        values,
        evidence_budget_bytes=1_000_000,
    )
    world.ctx.evidence = list(binding.evidence_by_sample[CALL])
    assert [item.evidence_id for item in world.ctx.evidence] == [
        f"conec-class-lists-roster/{CALL}",
        f"conec-class-lists-document/{CALL}",
    ]
    world.ctx.extras["execution_plan"] = ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="b" * 64,
        planned_model_calls=4,
        planned_gpu_hours=0.01,
        planned_speech_audio_seconds=42,
        protocol_hash="c" * 64,
        attempt_id="attempt-synthetic",
    ).validate()

    fitted = materialize_window_requests(
        [world.ctx],
        expected_sample_ids=[CALL],
        hook_factory=build_repair_window_hook,
        evidence_binding=binding,
    )
    assert fitted.request_keys == tuple(f"{CALL}#w{i:04d}" for i in range(1, 5))
    assert len(fitted.payloads) == len(fitted.source_bindings) == 4
    assert not world.adapter.payloads
    assert [source["media_relpath"] for source in fitted.source_bindings] == [
        f"derived/obs-slices/{RUN_ID}/{CALL}/i{i:04d}.wav" for i in range(4)
    ]
    expected_parent_ids = [f"{CALL}#w{i:04d}" for i in (5, 6, 9, 11)]
    for source, unit in zip(fitted.source_bindings, call["units"], strict=True):
        assert source["start_seconds"] == pytest.approx(unit["start_seconds"])
        assert source["end_seconds"] == pytest.approx(unit["end_seconds"])
        assert source["audio_seconds"] == pytest.approx(
            (
                round(unit["end_seconds"] * 16_000)
                - round(unit["start_seconds"] * 16_000)
            )
            / 16_000
        )
        assert (world.data_root / source["media_relpath"]).is_file()

    if packet_mode is not None:
        from speech_aware_evidence_acquisition.core.preparation_window_packets import (
            PreparedWindowFeaturePackets, WindowPacketBinding,
        )
        entries = tuple(
            WindowPacketBinding(
                key, f"{key}@{source['sha256']}",
                f"window-audio/{source['sha256'][:2]}/{source['sha256']}",
                hashlib.sha256(key.encode()).hexdigest(), source["sha256"], "123",
                ({"batch": "synthetic", "source_provenance": source},), (),
            )
            for key, source in zip(fitted.request_keys, fitted.source_bindings, strict=True)
        )
        world.ctx.extras["window_feature_packets"] = PreparedWindowFeaturePackets(
            "a" * 64, "b" * 64, "c" * 64, "d" * 64, {}, "unused", "unused",
            len(entries), len(entries), entries,
            {entry.request_key: entry for entry in entries},
        )
        world.ctx.arm = "speech-feature-query"
        values.update(
            arm="speech-feature-query",
            speech_feature_key_representation_id="synthetic-window-features",
            speech_feature_matcher_policy_id="exact-window-source",
        )
        if packet_mode == "query-only":
            values["evidence_source"] = "none"
            world.ctx.evidence = []
        original_instructions = [payload["task_instruction"] for payload in fitted.payloads]
        world.ctx.extras["slice_registry"] = SliceRegistry(
            data_root=world.data_root, run_id=RUN_ID,
            parent_facts={CALL: (world.parent_relpath, world.duration)},
        )
        fitted = materialize_window_requests(
            [world.ctx], expected_sample_ids=[CALL],
            hook_factory=build_repair_window_hook, evidence_binding=binding,
        )
        assert [payload["task_instruction"] for payload in fitted.payloads] == original_instructions
        assert all(payload["mmproj_loaded"] is False for payload in fitted.payloads)
        if packet_mode == "query-only":
            assert all(payload["supplied_evidence"] == [] for payload in fitted.payloads)

    world.ctx.extras["slice_registry"] = SliceRegistry(
        data_root=world.data_root,
        run_id=RUN_ID,
        parent_facts={CALL: (world.parent_relpath, world.duration)},
    )
    outcome = ObsRepairLoopOjwPolicy().run_sample(world.ctx)
    assert outcome.admitted
    assert len(world.adapter.payloads) == 4
    assert {
        payload["request_id"]: payload for payload in fitted.payloads
    } == {
        payload["request_id"]: payload for payload in world.adapter.payloads
    }

    trace = [
        json.loads(line)
        for line in (world.run_dir / f"{RUN_ID}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    obs = [row["payload"] for row in trace if row["record_id"].endswith("/obs")]
    uses = [
        row["payload"]
        for row in trace
        if row["record_id"].endswith("/window-controller")
    ]
    assert len(obs) == len(uses) == 4
    assert [row["obs_repair_predecessor_window_id"] for row in obs] == expected_parent_ids
    by_request = {payload["request_id"]: payload for payload in world.adapter.payloads}
    for index, (observed, used, source) in enumerate(
        zip(obs, uses, fitted.source_bindings, strict=True)
    ):
        query = used["use_query_state"]
        if packet_mode is None:
            assert query["query_source"] == "speech_audio"
            assert query["speech_packet_id"] == source["media_relpath"]
            assert query["speech_packet_sha256"] == source["sha256"]
        else:
            descriptor = fitted.payloads[index]["speech_feature_parts"][0]
            assert query["query_source"] == "speech_features"
            assert query["speech_packet_id"] == descriptor["packet_id"]
            assert query["speech_packet_sha256"] == descriptor["sha256"]
        request_id = used["use_terminal_request_id"]
        assert used["use_contact"]["instruction"] == by_request[request_id]["task_instruction"]
        assert used["use_sealed_state"]["content"] == targets[index]
        assert used["use_sealed_state"]["source_response_sha256"] == hashlib.sha256(
            targets[index].encode()
        ).hexdigest()
        assert used["use_delivered_text_sha256"] == hashlib.sha256(
            observed["obs_delivered_text"].encode()
        ).hexdigest()
        assert used["use_transition"]["action_kind"] == "stop"
    assert any(
        used["use_sealed_state"]["content"] != observed["obs_delivered_text"]
        for observed, used in zip(obs, uses, strict=True)
    )


@pytest.mark.parametrize("fail_transport", [False, True])
def test_flight_wire_check_real_ojw_request_parity_and_failure_cleanup(
    tmp_path, monkeypatch, synthetic_world, fail_transport
):
    """The FlightRuntime check uses the same fitter, hook, and OBS driver."""
    import socket

    from test_class_lists import CALL, _install

    def refuse_connection(*_args, **_kwargs):
        pytest.fail("the synthetic OBS check must never connect to a socket")

    monkeypatch.setattr(socket, "create_connection", refuse_connection)
    monkeypatch.setattr(socket.socket, "connect", refuse_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse_connection)

    from speech_aware_evidence_acquisition.core.bundle.finalize import (
        abort_attempt_if_opened,
    )
    from speech_aware_evidence_acquisition.core.attempts import STATE_ABORTED, AttemptStore
    from speech_aware_evidence_acquisition.core.config import ComposedConfig
    from speech_aware_evidence_acquisition.core.driver import run as driver_run
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

    source_root = Path(__file__).resolve().parents[2]
    plan_relpath = "docs/receipts/obs/e21-current-executor-four-row-proof-v1.json"
    plan_raw = (source_root / plan_relpath).read_bytes()
    plan_document = json.loads(plan_raw)
    call = plan_document["calls"][0]

    class VirtualPcm:
        def __len__(self):
            return round(call["decoded_duration_seconds"] * 16_000)

        def __getitem__(self, bounds):
            assert isinstance(bounds, slice) and bounds.step is None
            return array("h", [0]) * (bounds.stop - bounds.start)

    predecessors = []
    for parent in call["parent_windows"]:
        index = parent["window_index"]
        text = " ".join(
            f"window{index:02d}word{word:03d}" for word in range(parent["draft_words"])
        )
        predecessors.append(
            SimpleNamespace(
                window_id=f"{CALL}#w{index:04d}",
                start_seconds=parent["start_seconds"],
                end_seconds=parent["end_seconds"],
                text=text,
                text_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        )
    snapshot = SimpleNamespace(for_sample=lambda sample_id: tuple(predecessors))
    monkeypatch.setattr(repair_loop, "_bound_snapshot", lambda *args: snapshot)
    monkeypatch.setattr(obs_loop, "decode_parent_pcm", lambda *args: VirtualPcm())

    values = json.loads(
        (source_root / "configs/baseline/e21-current-executor-four-row-proof-ojw.json")
        .read_text(encoding="utf-8")
    )
    values["predecessor_snapshot"] = {
        "receipt_relpath": "receipts/synthetic-predecessor.json",
        "receipt_sha256": "a" * 64,
    }
    values["decoding_params"] = {"temperature": 0, "max_tokens": 1024}
    values["ojw_workflow_timeout_seconds"] = 0
    values.update(
        {
            "carrier_lock_key": "earnings21-original",
            "split_id": "synthetic-one-call",
            "split_name": "synthetic-one-call",
            "execution_plan": {
                "execution_profile": "bounded-discovery-probe",
                "split_role": "discovery",
                "planned_model_calls": 4,
                "planned_gpu_hours": 0.01,
                "planned_speech_audio_seconds": 42,
            },
        }
    )
    copied_plan = tmp_path / "repo" / plan_relpath
    copied_plan.parent.mkdir(parents=True, exist_ok=True)
    copied_plan.write_bytes(plan_raw)

    lock = _install(synthetic_world)
    parent_relpath = "datasets/earnings21-22/earnings21/media/4320211.mp3"
    parent = synthetic_world.data_root / parent_relpath
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"synthetic speech carrier")
    sample = SampleRef(
        carrier_lock_key="earnings21-original",
        sample_id=CALL,
        media_relpath=parent_relpath,
        audio_seconds=call["decoded_duration_seconds"],
        sample_rate_hz=16_000,
    )

    class WindowAdapter(TaskAdapter):
        def preprocess_plan(self):
            return {"kind": "raw-speech-windows"}

        def instruction(self, sample):
            return values["task_instruction"]

        def load_split(self, split_id):
            return (sample,)

        def build_task_contract(self, sample, obs):
            return "synthetic contract"

        def gold(self, sample):
            return None

        def score_response(self, gold, response):
            return {}

    config_hash = "d" * 64
    composed = ComposedConfig(
        values=values, config_hash=config_hash, fragments={"dataset": "synthetic"}
    )
    identity_hash = "b" * 64
    monkeypatch.setattr(
        driver_run,
        "_verify_split_for_run",
        lambda *args, **kwargs: SimpleNamespace(
            ids=(CALL,), split_role="discovery", carrier_lock_key="earnings21-original"
        ),
    )
    monkeypatch.setattr(
        driver_run.CARRIERS,
        "resolve",
        lambda _name: (lambda _lock, _root: (sample,)),
    )

    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = tmp_path / "repo"
    runtime._data_root = synthetic_world.data_root
    runtime._runtime_root = tmp_path / "runtime"
    runtime._run_id = "SAEA-SYNTHETIC-REGISTERED"
    runtime._attempt_id = "attempt-registered"
    runtime._explicit_run_dir = synthetic_world.data_root / "registered-attempt"
    runtime._composed = composed
    runtime._adapter = WindowAdapter()
    runtime._samples = (sample,)
    runtime._split_id = "synthetic-one-call"
    runtime._lock = lock
    runtime._plan = None
    runtime._gate = object()
    runtime._transport = object()
    runtime._client = None
    runtime._obs_result = None
    runtime._output_rows = []
    runtime._obs_runner = None
    runtime._clock = time.monotonic
    runtime._abort_attempt = abort_attempt_if_opened
    runtime._prepare = lambda: (
        values,
        "earnings21-original",
        "synthetic-one-call",
        identity_hash,
    )

    observed = []
    registered_state = (
        runtime._run_id,
        runtime._attempt_id,
        runtime._explicit_run_dir,
        runtime._gate,
        runtime._transport,
    )
    if fail_transport:
        from openjiuwen.core.common.exception.errors import ExecutionError

        from speech_aware_evidence_acquisition.core.base import CoreError
        from speech_aware_evidence_acquisition.core.flight.runtime import WireCheckTransport

        original_transport = WireCheckTransport.__call__
        reached = []

        def fail_after_arrival(transport, body):
            original_transport(transport, body)
            reached.append(json.loads(body))
            raise CoreError("synthetic transport failure after request arrival")

        monkeypatch.setattr(WireCheckTransport, "__call__", fail_after_arrival)
        with pytest.raises(ExecutionError, match="synthetic transport failure") as failure:
            runtime.wire_check(
                seal_and_score=False, request_payload_observer=observed.append
            )
        assert isinstance(failure.value.__cause__, CoreError)
        assert reached and len(reached) <= 4
        assert not observed
        wire_files = list((synthetic_world.data_root / "attempts").rglob("*.json"))
        assert len(wire_files) == 1
        attempt = json.loads(wire_files[0].read_text(encoding="utf-8"))
        assert attempt["state"] == STATE_ABORTED
        assert 1 <= attempt["actual"]["calls"] <= 4
        assert not (synthetic_world.data_root / "attempts" / runtime._run_id).exists()
        assert not runtime._explicit_run_dir.exists()
        assert (
            runtime._run_id,
            runtime._attempt_id,
            runtime._explicit_run_dir,
            runtime._gate,
            runtime._transport,
        ) == registered_state
        return

    receipt = runtime.wire_check(
        seal_and_score=False, request_payload_observer=observed.append
    )

    assert receipt["selected_window_count"] == 4
    assert receipt["contact_count"] == receipt["fake_transport_requests"] == 4
    assert receipt["fake_gate_attempts"] == 1
    assert receipt["sample_count"] == 1
    assert receipt["model_contacts"] == 0
    assert len(observed) == 4
    assert len(set(receipt["request_ids"])) == 4
    wire_attempt = AttemptStore(
        synthetic_world.data_root / "attempts"
    ).handle(receipt["wire_check_run_id"], receipt["attempt_id"])
    assert wire_attempt.state() == STATE_ABORTED
    assert json.loads(wire_attempt.path.read_text(encoding="utf-8"))["actual"]["calls"] == 4
    assert not (synthetic_world.data_root / "attempts" / runtime._run_id).exists()
    assert not runtime._explicit_run_dir.exists()
    assert (
        runtime._run_id,
        runtime._attempt_id,
        runtime._explicit_run_dir,
        runtime._gate,
        runtime._transport,
    ) == registered_state


def _scenario(name):
    """(pcm, texts, values, evidence, arm) per scenario — every behavioural
    surface of the plain policy the ojw executor must reproduce."""

    if name == "model-tails":
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            # 4000-char tail >= any stitched text here: every request payload
            # embeds the FULL accumulated span text, so payload equality pins
            # the accepted-span sequence directly.
            values=_config_values(obs_condition_tail_chars=4000),
        )
    if name == "vad-trim":
        return dict(
            pcm=_concat(_silence(10.0), _noise(55.0)),
            texts=[_boundary_text("Speech only.", 30)],
            values=_config_values(),
        )
    if name == "fixed-ablation":
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
        return dict(
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
    if name == "evidence-arm":
        item = EvidenceItem(
            evidence_id="conec/4000001",
            source_uri="conec://earnings21/contexts/4000001.txt",
            content="ACME Corp, Q3, John Smith",
            provenance={"lock_key": "conec", "relpath": "x", "sha256": "e" * 64},
        )
        return dict(
            pcm=_noise(90.0),
            texts=[_boundary_text("A. spill", 45), _boundary_text("B.", 10)],
            values=_config_values(obs_condition_tail_chars=400),
            evidence=[item],
            arm="fixed-legal-context",
        )
    if name == "rms-norm":
        return dict(
            pcm=_noise(40.0),
            texts=[_boundary_text("Quiet speech.", 20)],
            values=_config_values(obs_preprocess=["rms-norm"]),
        )
    if name == "tail-silence":
        # The 2026-09-07 Earnings-21 obs knob: 2.0 s of digital silence after
        # the buffered cut. The openJiuwen executor "mirrors it" only if the
        # slice BYTES, the derivation records (including the declared
        # tail-silence transform and pre_sha256) and every metered second come
        # out identical to the plain policy's -- which is what this scenario
        # puts through the equivalence harness rather than asserting
        # separately.
        values = _config_values(
            obs_buffer_seconds=30,
            obs_min_advance_seconds=30,
            obs_max_advance_seconds=30,
            obs_fallback_advance_seconds=30,
            obs_silence_snap_seconds=0,
            obs_boundary_mode="fixed",
            obs_vad_trim_min_seconds=0,
            obs_slice_tail_silence_seconds=2.0,
        )
        values.pop("obs_boundary_prompt")
        return dict(
            pcm=_noise(75.0),
            texts=["span one", "span two", "span three"],
            values=values,
        )
    if name == "fallback-boundary":
        return dict(
            pcm=_noise(90.0),
            texts=["no boundary line at all here.", _boundary_text("Tail end.", 10)],
            values=_config_values(),
        )
    if name == "retry-flaky":
        # live E-001 finding (2026-08-08): call #2 times out once, the retry
        # succeeds under a fresh request id -- both executors must retry
        # IDENTICALLY (same retry id, same trace, same metered sequence)
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            values=_config_values(obs_condition_tail_chars=4000),
            flaky_calls=(2,),
        )
    if name == "unit-plan":
        # OBS-E1 speaker-turn units (drift #1 of the 2026-09-08 openJiuwen
        # assessment, closed the same day). The plan replaces the clock with
        # three units of unequal length, so a clock-derived cutter on either
        # side would deliver different media, different slice bytes and
        # different derivation records -- which is exactly what this scenario
        # puts through the equivalence harness rather than asserting
        # separately. A plan forces fixed boundary mode, zero tail and zero
        # trim at config-load time, so those knobs are not free here.
        document = _plan_document(duration=150.0, edges=[40.0, 95.0])
        raw = _plan_bytes(document)
        return dict(
            pcm=_noise(150.0),
            texts=["unit one", "unit two", "unit three"],
            values=_plan_values(PLAN_RELPATH, hashlib.sha256(raw).hexdigest()),
            plan_bytes=raw,
        )
    if name == "window-hook":
        # KC-E1f's per-window seam (drift #2 of the 2026-09-08 openJiuwen
        # assessment, closed by the Decision 12-F port). The hook moves BOTH
        # legs a second-pass policy needs -- what each window is asked (a
        # per-window instruction suffix that lands verbatim in that window's
        # request payload) and what each window delivers (a rewritten span
        # plus its own OBS fields) -- so equality of payloads, OBS records,
        # stitched text and outcome here is exactly the statement that the
        # openJiuwen graph runs the same seam as the plain policy's own
        # sequential cutter. Fixed boundaries, no tail and no trim: the
        # legality every hook consumer declares, and the regime in which the
        # accepted span and the stripped transcript are the same string.
        values = _config_values(
            obs_buffer_seconds=50,
            obs_min_advance_seconds=50,
            obs_max_advance_seconds=50,
            obs_fallback_advance_seconds=50,
            obs_silence_snap_seconds=0,
            obs_boundary_mode="fixed",
            obs_vad_trim_min_seconds=0,
            obs_condition_tail_chars=0,
        )
        values.pop("obs_boundary_prompt")
        return dict(
            pcm=_noise(150.0),
            texts=["raw one", "raw two", "raw three"],
            values=values,
            window_hook=True,
        )
    if name == "window-hook-skip":
        # The same seam over a window the core never answered. Call #2 and
        # its retry both time out, so that window reaches the hook as the
        # empty string with ``skipped=True`` -- which is precisely the case a
        # substitution-only delivery rule exists to answer, and precisely the
        # case in which a graph that skipped the hook would still look right
        # on the other two windows.
        values = _fixed_mode_skip_values(
            obs_buffer_seconds=50,
            obs_min_advance_seconds=50,
            obs_max_advance_seconds=50,
            obs_fallback_advance_seconds=50,
            obs_condition_tail_chars=0,
        )
        return dict(
            pcm=_noise(150.0),
            texts=["raw one", "raw two", "raw three"],
            values=values,
            flaky_calls=(2, 3),
            window_hook=True,
        )
    if name == "retry-exhausted-skip":
        # Task 2 (2026-08-09): call #2 AND its retry (#3) both time out --
        # exhausted, skipped (never aborted) -- both executors must reach
        # byte-identical records for the surviving slices AND the skip
        # itself (obs_skipped, skipped_slices, the shortened stitch).
        return dict(
            pcm=_noise(150.0),
            texts=[
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
            values=_config_values(obs_condition_tail_chars=4000),
            flaky_calls=(2, 3),
        )
    raise AssertionError(name)


SCENARIOS = (
    "model-tails",
    "vad-trim",
    "fixed-ablation",
    "evidence-arm",
    "rms-norm",
    "tail-silence",
    "fallback-boundary",
    "retry-flaky",
    "retry-exhausted-skip",
    "unit-plan",
    "window-hook",
    "window-hook-skip",
)

#: The policy classes whose ``_window_hook`` a hooked scenario overrides --
#: one per executor, the SAME method name and the SAME signature, which is
#: what makes one test hook serve both sides.
_HOOKED_POLICY_CLASSES = (obs_loop.ObsAgentLoopPolicy, ObsAgentLoopOjwPolicy)


class _ScenarioWindowHook:
    """A deterministic stand-in for ``reproduction.repair_loop``'s own hook.

    It moves both legs the seam has -- the rendered instruction of every
    window's request and the text that window delivers into the stitch, plus
    its own OBS fields -- from values that depend only on the window's own
    iteration and cut bounds. Nothing here reads a clock, a file or a sealed
    receipt, so the plain executor and the openJiuwen executor building one
    each still produce identical bytes."""

    def __init__(self) -> None:
        self.seen: list[tuple[int, bool, bool]] = []

    def instruction(self, *, iteration, record, default):
        return f"{default}\n\nWINDOW {iteration} [{record.start_seconds}]"

    def accept(self, *, iteration, record, transcript, saturated, skipped):
        self.seen.append((iteration, bool(saturated), bool(skipped)))
        delivered = f"delivered {iteration}: {transcript}".strip()
        return delivered, {
            "obs_scenario_hook": True,
            "obs_scenario_hook_iteration": iteration,
            "obs_scenario_hook_skipped": bool(skipped),
            "obs_scenario_hook_raw_chars": len(transcript),
        }


def _run(tmp_path, monkeypatch, policy_name, scenario):
    if scenario.get("window_hook"):
        # One fresh hook per executor: the plain and the ojw run each build
        # their own, exactly as a real per-sample hook is built, and their
        # byte equality is then a statement about the two executors rather
        # than about a shared mutable object.
        hook = _ScenarioWindowHook()
        for policy_class in _HOOKED_POLICY_CLASSES:
            monkeypatch.setattr(
                policy_class,
                "_window_hook",
                lambda self, ctx, cfg, data_root, sample, _hook=hook: _hook,
            )
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=scenario["pcm"],
        texts=list(scenario["texts"]),
        values=dict(scenario["values"]),
        evidence=scenario.get("evidence"),
        arm=scenario.get("arm", "bare-core"),
    )
    if scenario.get("plan_bytes"):
        # The unit plan is a hash-pinned repo file; install it under THIS
        # world's own repo root before the config resolves it.
        path = world.repo_root / PLAN_RELPATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(scenario["plan_bytes"])
    if scenario.get("flaky_calls"):
        world.ctx.adapter = _FlakyAdapter(world.adapter, scenario["flaky_calls"])
    outcome = POLICIES.resolve(policy_name).run_sample(world.ctx)
    return world, outcome


def _trace_records(world):
    raw = (world.run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
    records = [json.loads(line) for line in raw.splitlines() if line]
    for record in records:
        payload = record.get("payload")
        if isinstance(payload, dict):
            payload.pop("latency_seconds", None)  # volatile (COST); defensive
    return records


def _derivation_bytes(world):
    return (world.run_dir / f"{RUN_ID}.obs-derivation.{SAMPLE_ID}.json").read_bytes()


def _accepted_spans(world, scenario):
    """Re-derive the accepted-span sequence from this world's own OBS trace
    records through the frozen pure functions (module docstring)."""

    obs = [
        record["payload"]
        for record in _trace_records(world)
        if record["record_id"].startswith("req-0001-i")
        and record["record_id"].endswith("/obs")
    ]
    obs.sort(key=lambda payload: payload["obs_iteration"])
    values = scenario["values"]
    spans = []
    for payload, text in zip(obs, list(scenario["texts"]), strict=True):
        if values.get("obs_boundary_mode", "model") == "model":
            transcript, _ = parse_boundary_response(text)
        else:
            transcript = text.strip()
        if payload["obs_final_window"] or values.get("obs_boundary_mode") == "fixed":
            accepted = transcript
        else:
            slice_seconds = (
                payload["obs_window_end_seconds"] - payload["obs_window_start_seconds"]
            )
            accepted, _ = accept_up_to_boundary(
                transcript, payload["obs_boundary_advance_seconds"] / slice_seconds
            )
        spans.append(accepted.strip())
    return spans


def _fingerprint(world, outcome):
    document = {
        "trace": _trace_records(world),
        "derivation": _derivation_bytes(world).decode("utf-8"),
        "outcome": dataclasses.asdict(outcome),
    }
    canonical = json.dumps(document, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class TestEquivalence:
    @pytest.mark.parametrize("name", SCENARIOS)
    def test_ojw_reproduces_the_plain_policy(self, tmp_path, monkeypatch, name):
        scenario = _scenario(name)
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        ojw_world, ojw_outcome = _run(
            tmp_path / "ojw", monkeypatch, OJW_POLICY_NAME, scenario
        )
        # accepted-span sequences
        assert _accepted_spans(ojw_world, scenario) == _accepted_spans(
            plain_world, scenario
        )
        # every request payload (slice relpaths, metered seconds, rendered
        # instruction incl. boundary template + tail, evidence fields)
        assert ojw_world.adapter.payloads == plain_world.adapter.payloads
        # slice derivation records, byte for byte
        assert _derivation_bytes(ojw_world) == _derivation_bytes(plain_world)
        # written slice bytes
        for payload in plain_world.adapter.payloads:
            relpath = payload["media_relpath"]
            assert (ojw_world.data_root / relpath).read_bytes() == (
                plain_world.data_root / relpath
            ).read_bytes()
        # stitched output text + the full outputs-row shape
        assert ojw_outcome == plain_outcome
        # the complete trace record sequence (OBS incl. trims, stitch, USE)
        assert _trace_records(ojw_world) == _trace_records(plain_world)

    def test_stitched_text_and_registry_state(self, tmp_path, monkeypatch):
        scenario = _scenario("model-tails")
        ojw_world, ojw_outcome = _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert ojw_outcome.text == "First span one. Second span two. Final span three."
        assert ojw_outcome.request_ids == (
            "req-0001-i0000",
            "req-0001-i0001",
            "req-0001-i0002",
        )
        for payload in ojw_world.adapter.payloads:
            record = ojw_world.registry.lookup(SAMPLE_ID, payload["media_relpath"])
            assert record is not None
            assert record.parent_sha256


class TestDeterminism:
    def test_determinism_five_runs(self, tmp_path, monkeypatch):
        """Five fresh executor runs over the same fixture must be
        byte-identical (and identical to the plain reference) — the
        empirical check behind the linear-chain determinism argument."""

        scenario = _scenario("model-tails")
        plain_world, plain_outcome = _run(
            tmp_path / "plain", monkeypatch, OBS_LOOP_POLICY_NAME, scenario
        )
        reference = _fingerprint(plain_world, plain_outcome)
        fingerprints = []
        for index in range(5):
            world, outcome = _run(
                tmp_path / f"ojw{index}", monkeypatch, OJW_POLICY_NAME, scenario
            )
            fingerprints.append(_fingerprint(world, outcome))
        assert fingerprints == [reference] * 5


class TestSingleDoor:
    def test_frozen_core_asr_requires_an_injected_callable(self):
        with pytest.raises(ObsLoopError, match="callable adapter request"):
            FrozenCoreASR(adapter_request=None, state=None)


class TestWindowHook:
    """The seam itself, asserted DIRECTLY on the openJiuwen executor rather
    than only inferred from ``TestEquivalence``.

    Equivalence over a hooked scenario is a strong statement only if the hook
    really ran on the graph: two executors that both ignored it would agree
    just as loudly. So this class pins, on the ojw side alone, that every
    window's request carried the hook's instruction, that the stitch is the
    hook's delivered text (never the raw response), that the hook's own fields
    reached the OBS records, and that the default really is ``None``."""

    def test_the_default_hook_is_none_on_both_executors(self, tmp_path):
        for policy in (obs_loop.ObsAgentLoopPolicy(), ObsAgentLoopOjwPolicy()):
            assert policy._window_hook(None, None, tmp_path, None) is None

    def test_the_graph_renders_and_delivers_through_the_hook(
        self, tmp_path, monkeypatch
    ):
        scenario = _scenario("window-hook")
        hook = _ScenarioWindowHook()
        monkeypatch.setattr(
            ObsAgentLoopOjwPolicy,
            "_window_hook",
            lambda self, ctx, cfg, data_root, sample: hook,
        )
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=scenario["pcm"],
            texts=list(scenario["texts"]),
            values=dict(scenario["values"]),
        )
        outcome = POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)

        assert [entry[0] for entry in hook.seen] == [0, 1, 2]
        # the instruction leg: every window's request carries the hook's text
        for index, payload in enumerate(world.adapter.payloads):
            assert payload["task_instruction"].endswith(f"WINDOW {index} [{index * 50.0}]")
        # the delivery leg: the stitch is what the hook returned, and the raw
        # response text ("raw one" ...) never reaches it unprefixed
        assert outcome.text == (
            "delivered 0: raw one delivered 1: raw two delivered 2: raw three"
        )
        obs = _obs_payloads(world)
        for index in range(3):
            record = obs[f"req-0001-i{index:04d}/obs"]
            assert record["obs_scenario_hook"] is True
            assert record["obs_scenario_hook_iteration"] == index
            assert record["obs_scenario_hook_skipped"] is False
            assert record["obs_accepted_chars"] == len(
                f"delivered {index}: {scenario['texts'][index]}"
            )

    def test_the_repair_sibling_registers_and_shares_one_hook_builder(
        self, monkeypatch
    ):
        """``obs-repair-loop-ojw`` is a THIN derivation: it resolves in the
        one policy registry, it IS the ojw policy plus two methods, and its
        hook comes from the same module-level builder the plain repair policy
        calls -- so there is no second repair implementation to drift."""

        policy = POLICIES.resolve(OBS_REPAIR_LOOP_OJW_POLICY_NAME)
        assert isinstance(policy, ObsRepairLoopOjwPolicy)
        assert isinstance(policy, ObsAgentLoopOjwPolicy)
        assert build_repair_window_hook.__module__.endswith("reproduction.repair_loop")

        sentinel = object()
        calls: list[tuple] = []
        monkeypatch.setattr(
            repair_loop,
            "build_repair_window_hook",
            lambda ctx, cfg, data_root, sample: (
                calls.append((ctx, cfg, data_root, sample)) or sentinel
            ),
        )
        for resolved in (
            POLICIES.resolve(OBS_REPAIR_LOOP_OJW_POLICY_NAME),
            POLICIES.resolve("obs-repair-loop"),
        ):
            assert resolved._window_hook("ctx", "cfg", "root", "sample") is sentinel
        assert calls == [("ctx", "cfg", "root", "sample")] * 2

    def test_the_repair_sibling_refuses_a_config_with_no_predecessor(self, tmp_path, monkeypatch):
        world = _World(
            tmp_path, monkeypatch, pcm=_noise(50.0), texts=["x"],
            values=_scenario("window-hook")["values"],
        )
        with pytest.raises(ObsLoopError, match="predecessor_snapshot"):
            POLICIES.resolve(OBS_REPAIR_LOOP_OJW_POLICY_NAME).run_sample(world.ctx)


class TestSaturation:
    """Per-slice decode-cap saturation reaches the ojw executor through the
    SAME shared seam (obs_loop.request_slice_with_retry) as the plain
    policy: FrozenCoreASR.invoke computes it, runner.py's ``${asr.saturated}``
    wiring carries it to AcceptAdvance, which emits it and mirrors it onto
    ObsSampleState.saturated_slices for policy._finalize_sample to read back
    into the outputs-row SampleOutcome -- proven directly against the ojw
    policy, not merely inferred from TestEquivalence (whose fake responses
    carry no usage at all, so saturated_slices stays 0 on both sides
    regardless of whether this wiring exists)."""

    def test_saturated_slice_reaches_the_outcome_and_the_obs_record(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(90.0),
            texts=[
                _boundary_text("First span done. Tail", 45),
                _boundary_text("Second done.", 10),
            ],
            usages=[{"completion_tokens": 5}, {"completion_tokens": 2}],
            decoding_params={"temperature": 0, "max_tokens": 5},
        )
        outcome = POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)
        assert outcome.saturated_slices == 1
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_saturated"] is True
        assert obs["req-0001-i0001/obs"]["obs_saturated"] is False


class TestSkip:
    """Exhausted-slice skip (Task 2, 2026-08-09) reaches the ojw executor
    through the SAME shared seam (obs_loop.request_slice_with_retry) as the
    plain policy: FrozenCoreASR.invoke passes the skip through,
    runner.py's ``${asr.skipped}`` wiring carries it to AcceptAdvance, which
    emits it and mirrors it onto ObsSampleState.skipped_slices/
    skip_exceeded, and policy._finalize_sample raises the SAME
    ObsLoopError (obs_loop._skip_bound_exceeded_message, the ONE function
    both executors call) when the bound is crossed -- proven directly
    against the ojw policy here, not merely inferred from TestEquivalence's
    "retry-exhausted-skip" scenario."""

    def test_exhausted_slice_reaches_the_outcome_and_the_obs_record(
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
        outcome = POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)
        assert outcome.skipped_slices == 1
        assert outcome.request_ids == ("req-0001-i0000",)
        obs = _obs_payloads(world)
        assert obs["req-0001-i0000/obs"]["obs_skipped"] is False
        assert obs["req-0001-i0001-r1/obs"]["obs_skipped"] is True
        assert obs["req-0001-i0001-r1/obs"]["obs_retry_of"] == "req-0001-i0001"

    def test_exceeding_the_skip_bound_raises_the_same_message_as_the_plain_policy(
        self, tmp_path, monkeypatch
    ):
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=_noise(120.0),
            texts=["one", "two", "three"],
            values=_fixed_mode_skip_values(),
        )
        flaky = _FlakyAdapter(world.adapter, fail_calls={2, 3, 4, 5})
        world.ctx.adapter = flaky
        with pytest.raises(ObsLoopError, match="obs_slice_skip_max=1"):
            POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)


class _FakeResponseById:
    """Deterministic, ORDER-INDEPENDENT fake hashes (keyed by request id +
    text): interleaved batch execution and per-sample sequential reference
    runs must produce identical outcome/stitch hashes."""

    def __init__(self, text, request_id):
        self.text = text
        self.request_sha256 = hashlib.sha256(f"req-{request_id}".encode()).hexdigest()
        self.response_sha256 = hashlib.sha256(
            f"resp-{request_id}-{text}".encode()
        ).hexdigest()
        self.response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()


class _SampleScriptedAdapter:
    """Per-sample scripts, thread-safe (batch mode calls request from
    asyncio.to_thread workers); records every payload in arrival order."""

    def __init__(self, scripts):
        self._scripts = {sid: list(texts) for sid, texts in scripts.items()}
        self._lock = threading.Lock()
        self.payloads = []

    def request(self, payload):
        with self._lock:
            self.payloads.append(dict(payload))
            texts = self._scripts[payload["sample_id"]]
            if not texts:
                raise AssertionError(
                    f"sample {payload['sample_id']} sent more requests than scripted"
                )
            text = texts.pop(0)
        return _FakeResponseById(text, payload["request_id"])


def _parent_relpath(sample_id):
    return f"datasets/earnings21-22/earnings21/media/{sample_id}.mp3"


def _write_template(repo_root):
    template = repo_root / "configs" / "probes/obs_boundary_v1.txt"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "After the transcript report BOUNDARY_SECONDS as instructed.\n",
        encoding="utf-8",
    )


def _batch_specs():
    """Two whole-call samples with different lengths/scripts."""

    return {
        "4000001": (
            _noise(150.0, seed=3),
            [
                _boundary_text("First span one. First tail", 45),
                _boundary_text("Second span two. Second tail", 50),
                _boundary_text("Final span three.", 30),
            ],
        ),
        "4000002": (
            _noise(90.0, seed=11),
            [
                _boundary_text("Other call alpha. spill", 45),
                _boundary_text("Other call omega.", 10),
            ],
        ),
    }


def _ctx_for(sample_id, base, pcm, values, *, data_root, run_dir, repo_root,
             registry, adapter, sink, pcm_map):
    parent = data_root / _parent_relpath(sample_id)
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"fake-audio-" + sample_id.encode())
    pcm_map[f"{sample_id}.mp3"] = pcm
    duration = len(pcm) / 16000
    return SampleContext(
        sample=SampleRef(
            carrier_lock_key="earnings21-original",
            sample_id=sample_id,
            media_relpath=_parent_relpath(sample_id),
            audio_seconds=duration,
            sample_rate_hz=16000,
        ),
        evidence=[],
        adapter=adapter,
        sink=sink,
        arm="bare-core",
        task_instruction="Transcribe the speech verbatim.",
        decoding_params={"temperature": 0},
        request_id_base=base,
        extras={
            "slice_registry": registry,
            "data_root": data_root,
            "run_dir": run_dir,
            "repo_root": repo_root,
            "config_values": values,
        },
    )


class TestBatchExecution:
    """Owner batching directive (2026-08-08): sample-level concurrency in
    the ojw executor via run_samples (asyncio.gather + semaphore); per
    sample everything must stay byte-identical to the sequential plain
    reference, and rows/trace stay in split-id order."""

    def _reference(self, root, sample_id, base, pcm, texts, values, pcm_map):
        """The plain policy run sequentially over ONE sample — the
        per-sample ground truth the batch run must reproduce exactly."""

        data_root, run_dir, repo_root = root / "data", root / "run", root / "repo"
        _write_template(repo_root)
        registry = SliceRegistry(
            data_root=data_root,
            run_id=RUN_ID,
            parent_facts={sample_id: (_parent_relpath(sample_id), len(pcm) / 16000)},
        )
        adapter = _SampleScriptedAdapter({sample_id: texts})
        sink = TraceSink(run_dir, RUN_ID)
        ctx = _ctx_for(
            sample_id, base, pcm, values, data_root=data_root, run_dir=run_dir,
            repo_root=repo_root, registry=registry, adapter=adapter, sink=sink,
            pcm_map=pcm_map,
        )
        outcome = POLICIES.resolve(OBS_LOOP_POLICY_NAME).run_sample(ctx)
        raw = (run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        records = [
            (doc["channel"], doc["record_id"], doc["payload"])
            for doc in (json.loads(line) for line in raw.splitlines() if line)
        ]
        derivation = (
            run_dir / f"{RUN_ID}.obs-derivation.{sample_id}.json"
        ).read_bytes()
        return outcome, records, derivation

    def _batch_world(self, root, specs, values, pcm_map):
        data_root, run_dir, repo_root = root / "data", root / "run", root / "repo"
        _write_template(repo_root)
        registry = SliceRegistry(
            data_root=data_root,
            run_id=RUN_ID,
            parent_facts={
                sid: (_parent_relpath(sid), len(pcm) / 16000)
                for sid, (pcm, _) in specs.items()
            },
        )
        adapter = _SampleScriptedAdapter(
            {sid: texts for sid, (_, texts) in specs.items()}
        )
        contexts, buffers = [], {}
        for index, sid in enumerate(sorted(specs), start=1):
            pcm, _ = specs[sid]
            buffer = TraceBuffer(RUN_ID)
            buffers[sid] = buffer
            contexts.append(
                _ctx_for(
                    sid, f"req-{index:04d}", pcm, values, data_root=data_root,
                    run_dir=run_dir, repo_root=repo_root, registry=registry,
                    adapter=adapter, sink=buffer, pcm_map=pcm_map,
                )
            )
        return contexts, buffers, adapter, registry, data_root, run_dir

    def test_slot_affinity_sentinel_resolves_to_distinct_stable_slots(
        self, tmp_path, monkeypatch
    ):
        """Slot affinity (SAEA-BENCH-idslot-q4km, 2026-08-11): with
        decoding_params.id_slot = 'per-sample', every request of one sample
        carries ONE allocated integer slot, distinct across concurrently
        batched samples and inside [0, batch_size) — so a sample's stable
        evidence prefix stays in a single llama-server slot's KV."""

        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        values = _config_values(obs_condition_tail_chars=400, obs_batch_samples=2)
        contexts, _, adapter, _, _, _ = self._batch_world(
            tmp_path / "batch", specs, dict(values), pcm_map
        )
        contexts = [
            dataclasses.replace(
                ctx, decoding_params={"temperature": 0, "id_slot": "per-sample"}
            )
            for ctx in contexts
        ]
        POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)

        slots_by_sample = {}
        for payload in adapter.payloads:
            slot = payload["decoding_params"]["id_slot"]
            slots_by_sample.setdefault(payload["sample_id"], set()).add(slot)
        assert set(slots_by_sample) == set(specs)
        for sample_id, slots in slots_by_sample.items():
            assert len(slots) == 1, f"{sample_id} hopped slots: {slots}"
            (slot,) = slots
            assert isinstance(slot, int) and 0 <= slot < 2
        assert len({next(iter(s)) for s in slots_by_sample.values()}) == len(specs)

    def test_batch_of_two_matches_sequential_plain_per_sample(
        self, tmp_path, monkeypatch
    ):
        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        values = _config_values(obs_condition_tail_chars=400, obs_batch_samples=2)

        references = {}
        for index, sid in enumerate(sorted(specs), start=1):
            pcm, texts = specs[sid]
            references[sid] = self._reference(
                tmp_path / f"ref-{sid}", sid, f"req-{index:04d}", pcm, texts,
                dict(values), pcm_map,
            )

        contexts, buffers, adapter, registry, data_root, run_dir = self._batch_world(
            tmp_path / "batch", specs, dict(values), pcm_map
        )
        outcomes = POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)

        assert len(outcomes) == len(contexts)
        for ctx, outcome in zip(contexts, outcomes):
            sid = ctx.sample.sample_id
            ref_outcome, ref_records, ref_derivation = references[sid]
            assert outcome == ref_outcome
            assert buffers[sid].records == ref_records
            assert (
                run_dir / f"{RUN_ID}.obs-derivation.{sid}.json"
            ).read_bytes() == ref_derivation

        # slice-file collision check (item 4): per-sample-unique paths, all
        # registered, all written under the shared data root
        by_sample = {}
        for payload in adapter.payloads:
            by_sample.setdefault(payload["sample_id"], set()).add(
                payload["media_relpath"]
            )
        sids = sorted(by_sample)
        assert len(sids) == 2
        assert by_sample[sids[0]].isdisjoint(by_sample[sids[1]])
        for sid, relpaths in by_sample.items():
            for relpath in relpaths:
                assert f"/{sid}/" in relpath
                assert (data_root / relpath).is_file()
                assert registry.lookup(sid, relpath) is not None

        # deterministic per-run trace file: flush in split-id order
        sink = TraceSink(run_dir, RUN_ID)
        for ctx in contexts:
            buffers[ctx.sample.sample_id].flush_into(sink)
        raw = (run_dir / f"{RUN_ID}.trace.jsonl").read_text(encoding="utf-8")
        flushed_ids = [json.loads(line)["record_id"] for line in raw.splitlines() if line]
        expected_ids = [
            record_id
            for sid in sorted(specs)
            for _, record_id, _ in references[sid][1]
        ]
        assert flushed_ids == expected_ids

    def test_batch_size_one_is_todays_behaviour(self, tmp_path, monkeypatch):
        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        results = {}
        for batch in (1, 2):
            values = _config_values(
                obs_condition_tail_chars=400, obs_batch_samples=batch
            )
            contexts, buffers, _, _, _, _ = self._batch_world(
                tmp_path / f"batch-{batch}", specs, values, pcm_map
            )
            outcomes = POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)
            results[batch] = (
                outcomes,
                {sid: list(buffer.records) for sid, buffer in buffers.items()},
            )
        assert results[1] == results[2]

    def test_batch_failure_surfaces_first_sample_in_split_order(
        self, tmp_path, monkeypatch
    ):
        """When SEVERAL samples fail concurrently, the error that surfaces is
        deterministically the FIRST in split-id order — never whichever task
        happened to fail first in wall-clock time. (The framework wraps a
        component failure as ExecutionError 100054, the same shape the live
        run showed; the batch runner preserves that error, only choosing
        WHICH one propagates.)"""

        pcm_map = {}
        monkeypatch.setattr(
            obs_loop,
            "decode_parent_pcm",
            lambda path, rate=16000: pcm_map[Path(path).name],
        )
        specs = _batch_specs()
        values = _config_values(obs_condition_tail_chars=400, obs_batch_samples=2)
        contexts, _, adapter, _, _, _ = self._batch_world(
            tmp_path / "batch", specs, values, pcm_map
        )
        # Exhaust BOTH scripts so both samples fail; the LONGER sample
        # (4000001, 3 slices) necessarily fails LATER in wall-clock time than
        # the shorter one (4000002, 2 slices) -- so "first in split-id order"
        # and "first to fail" are genuinely different answers here.
        for sample_id in specs:
            adapter._scripts[sample_id].pop()
        with pytest.raises(Exception) as failure:
            POLICIES.resolve(OJW_POLICY_NAME).run_samples(contexts)
        message = str(failure.value)
        assert "more requests than scripted" in message
        assert "4000001" in message  # split-id order wins
        assert "4000002" not in message


class TestWorkflowTimeout:
    """Real-run blocker (2026-08-08): the framework kills each per-sample
    workflow at a builtin 60 s WORKFLOW_EXECUTE_TIMEOUT (error 100101). The
    fragment knob ``ojw_workflow_timeout_seconds`` must genuinely reach the
    framework session env, default to the generous backstop when absent,
    and a real kill must surface as an actionable ObsLoopError."""

    def _spy_envs(self, monkeypatch):
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        captured = {}
        real = runner.create_workflow_session

        def spy(*args, **kwargs):
            captured.update(kwargs.get("envs") or {})
            return real(*args, **kwargs)

        monkeypatch.setattr(runner, "create_workflow_session", spy)
        return captured

    def test_configured_value_reaches_the_framework_session_env(
        self, tmp_path, monkeypatch
    ):
        from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT

        captured = self._spy_envs(monkeypatch)
        scenario = _scenario("vad-trim")
        scenario["values"]["ojw_workflow_timeout_seconds"] = 1234.5
        _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert captured[WORKFLOW_EXECUTE_TIMEOUT] == 1234.5

    def test_absent_key_defaults_to_the_generous_backstop(
        self, tmp_path, monkeypatch
    ):
        from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT

        from speech_aware_evidence_acquisition.reproduction.ojw import (
            DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
        )

        captured = self._spy_envs(monkeypatch)
        scenario = _scenario("vad-trim")
        assert "ojw_workflow_timeout_seconds" not in scenario["values"]
        _run(tmp_path, monkeypatch, OJW_POLICY_NAME, scenario)
        assert captured[WORKFLOW_EXECUTE_TIMEOUT] == DEFAULT_WORKFLOW_TIMEOUT_SECONDS
        assert DEFAULT_WORKFLOW_TIMEOUT_SECONDS == 21600.0

    def test_framework_kill_surfaces_as_actionable_obs_loop_error(
        self, tmp_path, monkeypatch
    ):
        """End to end against the REAL framework limit: a tiny configured
        ceiling plus a slow adapter must reproduce the live incident's
        100101 kill, translated to an ObsLoopError naming the knob."""

        import time

        scenario = _scenario("vad-trim")
        scenario["values"]["ojw_workflow_timeout_seconds"] = 0.2
        world = _World(
            tmp_path,
            monkeypatch,
            pcm=scenario["pcm"],
            texts=list(scenario["texts"]),
            values=dict(scenario["values"]),
        )
        real_request = world.adapter.request

        def slow_request(payload):
            time.sleep(0.6)
            return real_request(payload)

        world.adapter.request = slow_request
        with pytest.raises(ObsLoopError, match="ojw_workflow_timeout_seconds"):
            POLICIES.resolve(OJW_POLICY_NAME).run_sample(world.ctx)


def _agent_contact_result(slot_id):
    return {
        "response_text": "ok",
        "slot_id": slot_id,
        "response_sha256": "0" * 64,
    }


def _patch_agent_workflow_builder(monkeypatch, invoke_flow):
    """Replace only the framework graph shell; keep the real batch scheduler."""

    from speech_aware_evidence_acquisition.reproduction.ojw import runner

    build_count = 0

    def build_speech_agent_workflow(**kwargs):
        nonlocal build_count
        workflow_index = build_count
        build_count += 1

        class FakeFlow:
            async def invoke(self, inputs, session):
                return await invoke_flow(workflow_index, kwargs["invoke_contact"])

        return FakeFlow()

    monkeypatch.setattr(
        runner, "build_speech_agent_workflow", build_speech_agent_workflow
    )
    monkeypatch.setattr(
        runner, "create_workflow_session", lambda **_kwargs: object()
    )
    return runner


def _execute_fake_agent_workflows(runner, states, invoke_contact, *, queue_depth=2):
    return runner.execute_speech_agent_workflows(
        states,
        prepare_wave=lambda _state, _session: 1,
        invoke_contact=invoke_contact,
        aggregate_wave=lambda _state, _responses, _session: None,
        should_continue=lambda _state: False,
        branch_count=2,
        slot_count=2,
        queue_depth=queue_depth,
        workflow_timeout_seconds=10.0,
    )


class TestSpeechAgentWorkflowScheduling:
    def test_native_episode_contacts_overlap_and_keep_one_primary_slot(
        self, monkeypatch
    ):
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        states = [object(), object()]
        slots_by_state = {state: [] for state in states}
        simultaneous_contacts = threading.Barrier(2)

        monkeypatch.setattr(
            runner,
            "build_speech_agent_workflow",
            lambda **_kwargs: pytest.fail("legacy workflow must not be built"),
        )

        async def episode_invoker(state, run_contact, _session):
            first = await run_contact(lambda _slot_id: "zero-argument-result")
            assert first == "zero-argument-result"

            def blocking_contact(slot_id):
                slots_by_state[state].append(slot_id)
                if len(slots_by_state[state]) == 1:
                    simultaneous_contacts.wait(timeout=1.0)
                return len(slots_by_state[state])

            assert await run_contact(blocking_contact) == 1
            assert await run_contact(blocking_contact) == 2

        results = runner.execute_speech_agent_workflows(
            states,
            branch_count=2,
            slot_count=2,
            queue_depth=2,
            workflow_timeout_seconds=10.0,
            episode_invoker=episode_invoker,
        )

        assert results == states
        assert all(len(set(slots)) == 1 for slots in slots_by_state.values())
        assert len({slots[0] for slots in slots_by_state.values()}) == 2

    def test_native_episode_cancellation_drains_contact_before_slot_release(
        self, monkeypatch
    ):
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        blocker_active = threading.Event()
        blocker_slot = []
        later_contacts = []
        states = [object(), object()]

        async def episode_invoker(state, run_contact, _session):
            if state is states[0]:
                blocking = asyncio.create_task(run_contact(blocking_contact))
                while not blocker_active.is_set():
                    await asyncio.sleep(0)
                blocking.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await blocking
                raise RuntimeError("planned native episode failure")
            while not blocker_active.is_set():
                await asyncio.sleep(0)
            await run_contact(later_contact)

        def blocking_contact(slot_id):
            blocker_slot.append(slot_id)
            blocker_active.set()
            time.sleep(0.10)
            blocker_active.clear()
            return "settled"

        def later_contact(slot_id):
            later_contacts.append((slot_id, blocker_active.is_set()))
            return "later"

        with pytest.raises(RuntimeError, match="planned native episode failure"):
            runner.execute_speech_agent_workflows(
                states,
                branch_count=1,
                slot_count=1,
                queue_depth=2,
                workflow_timeout_seconds=10.0,
                episode_invoker=episode_invoker,
            )

        assert blocker_slot
        assert later_contacts == [(blocker_slot[0], False)]

    def test_native_episode_raises_first_failure_in_input_order(self):
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        both_admitted = asyncio.Event()
        admitted = set()

        async def episode_invoker(state, _run_contact, _session):
            admitted.add(state)
            if len(admitted) == 2:
                both_admitted.set()
            await both_admitted.wait()
            if state == 0:
                await asyncio.sleep(0.02)
                raise RuntimeError("first input failure")
            raise RuntimeError("second input failure")

        with pytest.raises(RuntimeError, match="first input failure"):
            runner.execute_speech_agent_workflows(
                [0, 1],
                branch_count=1,
                slot_count=2,
                queue_depth=2,
                workflow_timeout_seconds=10.0,
                episode_invoker=episode_invoker,
            )

    def test_native_episode_uses_shared_session_timeout_translation(
        self, monkeypatch
    ):
        from openjiuwen.core.common.exception.codes import StatusCode
        from openjiuwen.core.common.exception.errors import BaseError
        from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT

        from speech_aware_evidence_acquisition.reproduction.ojw import (
            OpenJiuwenExecutorError,
            runner,
        )

        captured = {}
        session = object()

        def create_session(*, envs):
            captured.update(envs)
            return session

        monkeypatch.setattr(runner, "create_workflow_session", create_session)

        async def episode_invoker(_state, _run_contact, actual_session):
            assert actual_session is session
            raise BaseError(StatusCode.WORKFLOW_EXECUTION_TIMEOUT)

        with pytest.raises(OpenJiuwenExecutorError, match="7.5-second ceiling"):
            runner.execute_speech_agent_workflows(
                [object()],
                branch_count=1,
                slot_count=1,
                queue_depth=1,
                workflow_timeout_seconds=7.5,
                episode_invoker=episode_invoker,
            )

        assert captured[WORKFLOW_EXECUTE_TIMEOUT] == 7.5

    def test_sibling_failure_does_not_recycle_a_running_worker_slot(
        self, monkeypatch
    ):
        blocker_active = threading.Event()
        blocker_slot = []
        later_contacts = []
        states = [object(), object()]

        async def invoke_flow(workflow_index, invoke_contact):
            if workflow_index == 0:
                blocking = asyncio.create_task(invoke_contact(0))
                while not blocker_active.is_set():
                    await asyncio.sleep(0)
                blocking.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await blocking
                raise RuntimeError("planned sibling failure")
            while not blocker_active.is_set():
                await asyncio.sleep(0)
            await invoke_contact(0)

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)

        def invoke_contact(state, branch_index, slot_id):
            if state is states[0]:
                assert branch_index == 0
                blocker_slot.append(slot_id)
                blocker_active.set()
                time.sleep(0.15)
                blocker_active.clear()
                return _agent_contact_result(slot_id)
            later_contacts.append((slot_id, blocker_active.is_set()))
            return _agent_contact_result(slot_id)

        with pytest.raises(RuntimeError, match="planned sibling failure"):
            runner.execute_speech_agent_workflows(
                states,
                prepare_wave=lambda _state, _session: 1,
                invoke_contact=invoke_contact,
                aggregate_wave=lambda _state, _responses, _session: None,
                should_continue=lambda _state: False,
                branch_count=1,
                slot_count=1,
                queue_depth=2,
                workflow_timeout_seconds=10.0,
            )

        assert blocker_slot
        assert later_contacts == [(blocker_slot[0], False)]

    def test_timeout_does_not_recycle_a_running_worker_slot(self, monkeypatch):
        blocker_active = threading.Event()
        later_contact_observed_blocker = []
        states = [object(), object()]

        async def invoke_flow(workflow_index, invoke_contact):
            if workflow_index == 0:
                await asyncio.wait_for(invoke_contact(0), timeout=0.02)
                return
            while not blocker_active.is_set():
                await asyncio.sleep(0)
            await invoke_contact(0)

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)

        def invoke_contact(state, _branch_index, slot_id):
            if state is states[0]:
                blocker_active.set()
                time.sleep(0.10)
                blocker_active.clear()
            else:
                later_contact_observed_blocker.append(blocker_active.is_set())
            return _agent_contact_result(slot_id)

        with pytest.raises(TimeoutError):
            runner.execute_speech_agent_workflows(
                states,
                prepare_wave=lambda _state, _session: 1,
                invoke_contact=invoke_contact,
                aggregate_wave=lambda _state, _responses, _session: None,
                should_continue=lambda _state: False,
                branch_count=1,
                slot_count=1,
                queue_depth=2,
                workflow_timeout_seconds=10.0,
            )

        assert later_contact_observed_blocker == [False]

    def test_framework_timeout_waits_for_the_contact_worker_to_settle(self):
        from speech_aware_evidence_acquisition.reproduction.ojw import (
            OpenJiuwenExecutorError,
        )
        from speech_aware_evidence_acquisition.reproduction.ojw import runner

        state = {"done": False}

        def invoke_contact(_state, _branch_index, slot_id):
            time.sleep(0.10)
            return _agent_contact_result(slot_id)

        started = time.monotonic()
        with pytest.raises(OpenJiuwenExecutorError, match="workflow at the"):
            runner.execute_speech_agent_workflows(
                [state],
                prepare_wave=lambda _state, _session: 1,
                invoke_contact=invoke_contact,
                aggregate_wave=lambda current, _responses, _session: current.update(
                    done=True
                ),
                should_continue=lambda current: not current["done"],
                branch_count=1,
                slot_count=1,
                queue_depth=1,
                workflow_timeout_seconds=0.02,
            )

        assert time.monotonic() - started >= 0.10

    def test_three_waves_keep_one_primary_slot_per_trajectory(self, monkeypatch):
        states = [object()]
        calls = {state: [] for state in states}

        async def invoke_flow(_workflow_index, invoke_contact):
            for _wave_index in range(3):
                await invoke_contact(0)

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)

        def invoke_contact(state, _branch_index, slot_id):
            calls[state].append(slot_id)
            return _agent_contact_result(slot_id)

        results = _execute_fake_agent_workflows(runner, states, invoke_contact)

        assert results == states
        assert all(len(set(slots)) == 1 for slots in calls.values())

    def test_cross_sample_trajectories_remain_parallel(self, monkeypatch):
        states = [object(), object()]
        slots_by_state = {}
        simultaneous_contacts = threading.Barrier(2)

        async def invoke_flow(_workflow_index, invoke_contact):
            await invoke_contact(0)

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)

        def invoke_contact(state, _branch_index, slot_id):
            slots_by_state[state] = slot_id
            simultaneous_contacts.wait(timeout=1.0)
            return _agent_contact_result(slot_id)

        results = _execute_fake_agent_workflows(runner, states, invoke_contact)

        assert results == states
        assert len(set(slots_by_state.values())) == 2

    def test_one_hundred_workflows_respect_bounded_admission(self, monkeypatch):
        active = 0
        peak_active = 0

        async def invoke_flow(_workflow_index, _invoke_contact):
            nonlocal active, peak_active
            active += 1
            peak_active = max(peak_active, active)
            try:
                await asyncio.sleep(0.005)
            finally:
                active -= 1

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)
        states = list(range(100))
        results = _execute_fake_agent_workflows(
            runner,
            states,
            lambda _state, _branch, slot_id: _agent_contact_result(slot_id),
            queue_depth=4,
        )

        assert results == states
        assert peak_active == 4

    def test_first_fatal_failure_stops_new_workflow_admission(self, monkeypatch):
        admitted = []
        failure_started = asyncio.Event()

        async def invoke_flow(workflow_index, _invoke_contact):
            admitted.append(workflow_index)
            while len(admitted) < 4:
                await asyncio.sleep(0)
            if workflow_index == 0:
                failure_started.set()
                raise RuntimeError("fatal workflow failure")
            await failure_started.wait()
            await asyncio.sleep(0.02)

        runner = _patch_agent_workflow_builder(monkeypatch, invoke_flow)

        with pytest.raises(RuntimeError, match="fatal workflow failure"):
            _execute_fake_agent_workflows(
                runner,
                list(range(100)),
                lambda _state, _branch, slot_id: _agent_contact_result(slot_id),
                queue_depth=4,
            )

        assert admitted == [0, 1, 2, 3]


# ---------------------------------------------------------------------------
# The cross-call pipeline property (owner Decision 12-F, 2026-09-08)
# ---------------------------------------------------------------------------
#
# The plain path bought its throughput on 2026-09-08 with two halves of one
# mechanism (docs/readiness/2026-09-08-e21-obs-pipeline-v1.md): PREFETCH --
# the driver keeps ``obs_prefetch_depth`` samples of lookahead in flight, so
# the next call's decode/cut runs while this call's windows are still being
# answered -- and SLOT-SATURATING DISPATCH -- one ``ObsDispatcher`` for the
# whole run, so sample N+1's first request occupies the slot sample N's tail
# is releasing. The port REUSES both halves rather than growing parallel
# components inside the graph: the driver's pipelined loop calls
# ``policy.run_sample`` on a worker per sample exactly as it does for the
# plain policy, and ``runner.execute_obs_workflow`` holds ONE slot of the
# run's dispatcher for the whole of a sample's model phase (that graph sends
# one request at a time per sample, so a per-sample hold is both the
# in-flight bound and the ``id_slot="per-sample"`` affinity itself).
#
# What the port therefore does NOT carry, stated rather than discovered
# later: intra-sample slice parallelism. The plain policy's
# ``_slice_parallel_pass`` puts ``obs_batch_slices`` windows of ONE call in
# flight; this graph puts one. The run's in-flight ceiling on the ojw path is
# ``obs_prefetch_depth + 1``, which is why the driver refuses a dispatch
# width narrower than that, and why a flight that wants the sealed
# comparator's 8-wide occupancy declares depth 7 rather than slice width 8.

from test_obs_pipeline import (  # noqa: E402
    _CountingTransport,
    _OverlapTransport,
    _fly,
    _obs_records,
    _request_payload_sha256s,
    _static_transport,
    _trace_documents,
    _trace_lines_modulo_latency,
    _values,
    pipeline_repo,  # noqa: F401 (fixture, registered by this import)
)

_OJW_PIPELINE_VALUES = dict(policy=OJW_POLICY_NAME, obs_batch_slices=4)


def _load_ojw_runner():
    from speech_aware_evidence_acquisition.reproduction.ojw import runner

    return runner


class TestPipelineLegality:
    """What the config and driver layers will and will not admit, decided
    before a byte of audio is cut."""

    def test_the_graph_needs_no_slice_width_but_the_plain_cutter_does(self, tmp_path):
        """The plain policy's sequential cutter is refused a pipeline because
        its cursor is ``run_sample``-local; the openJiuwen executors are
        admitted because every loop-carried value of a sample lives in that
        sample's own ``ObsSampleState`` and its own workflow session."""

        with pytest.raises(ObsLoopError, match="obs_batch_slices > 1"):
            obs_loop.ObsLoopConfig.from_values(
                _values(obs_prefetch_depth=1, obs_batch_slices=1), tmp_path
            )
        for policy_name in (OJW_POLICY_NAME, OBS_REPAIR_LOOP_OJW_POLICY_NAME):
            cfg = obs_loop.ObsLoopConfig.from_values(
                _values(
                    obs_prefetch_depth=1,
                    obs_batch_slices=1,
                    policy=policy_name,
                    serving_geometry={"slots": 6},
                ),
                tmp_path,
            )
            assert cfg.prefetch_depth == 1

    def test_two_schedulers_never_compose(self, tmp_path):
        """``obs_batch_samples`` is the graph's OWN sample-level concurrency
        with its own slot pool; the prefetch pipeline is the driver's. The
        config layer refuses the pair, and the batch runner refuses a
        dispatcher that reached it anyway -- a silently ignored dispatcher
        would look exactly like a working one."""

        with pytest.raises(ObsLoopError, match="obs_batch_samples 1"):
            obs_loop.ObsLoopConfig.from_values(
                _values(
                    obs_prefetch_depth=1, obs_batch_samples=2, policy=OJW_POLICY_NAME
                ),
                tmp_path,
            )

        class _Ctx:
            extras = {"obs_dispatcher": obs_loop.ObsDispatcher(2)}

        with pytest.raises(ObsLoopError, match="cannot run under the driver"):
            _load_ojw_runner().execute_obs_batch(
                [_Ctx()],
                prepare=lambda ctx: None,
                finalize=lambda ctx, state: None,
                batch_size=2,
                workflow_timeout_seconds=60.0,
            )

    def test_the_driver_refuses_a_width_narrower_than_the_lookahead(
        self, synthetic_world, pipeline_repo, tmp_path  # noqa: F811 (the imported fixture, by name)
    ):
        """One request per sample means the run's in-flight ceiling IS
        ``depth + 1``; a narrower pool would serialize exactly the samples the
        prefetch just cut, which is a defect worth refusing rather than
        measuring."""

        from speech_aware_evidence_acquisition.core.base import CoreError

        lock, repo_root = pipeline_repo
        with pytest.raises(CoreError, match="dispatch width of at least 3"):
            _fly(
                synthetic_world,
                repo_root,
                lock,
                tmp_path / "narrow",
                _static_transport,
                "SAEA-E-000-ojw-narrow",
                obs_prefetch_depth=2,
                obs_batch_slices=2,
                policy=OJW_POLICY_NAME,
            )


class TestPipelineOnTheGraph:
    """Depth 0 is the graph this executor has always run; depth 1 asks the
    frozen core for exactly the same things, in a different order."""

    def test_depth_zero_is_byte_identical_to_declaring_nothing(
        self, synthetic_world, pipeline_repo, tmp_path  # noqa: F811 (the imported fixture, by name)
    ):
        lock, repo_root = pipeline_repo
        run_id = "SAEA-E-000-ojw-zero"
        silent_dir = tmp_path / "silent"
        zero_dir = tmp_path / "zero"
        silent = _fly(
            synthetic_world, repo_root, lock, silent_dir, _static_transport, run_id,
            attempt_suffix="silent", **_OJW_PIPELINE_VALUES,
        )
        zero = _fly(
            synthetic_world, repo_root, lock, zero_dir, _static_transport, run_id,
            attempt_suffix="zero", obs_prefetch_depth=0, **_OJW_PIPELINE_VALUES,
        )
        assert _trace_lines_modulo_latency(
            silent_dir, run_id
        ) == _trace_lines_modulo_latency(zero_dir, run_id)
        assert silent.outputs_path.read_bytes() == zero.outputs_path.read_bytes()

    def test_depth_one_sends_the_same_payload_set_and_overlaps_two_calls(
        self, synthetic_world, pipeline_repo, tmp_path  # noqa: F811 (the imported fixture, by name)
    ):
        """The property the port had to carry: the SAME set of request
        payloads and the SAME per-sample OBS records at depth 0 and depth 1,
        with two different calls genuinely in flight at once."""

        lock, repo_root = pipeline_repo
        run_id = "SAEA-E-000-ojw-one"
        zero_dir = tmp_path / "zero"
        one_dir = tmp_path / "one"
        zero = _fly(
            synthetic_world, repo_root, lock, zero_dir, _static_transport, run_id,
            attempt_suffix="seq", **_OJW_PIPELINE_VALUES,
        )
        overlap = _OverlapTransport()
        one = _fly(
            synthetic_world, repo_root, lock, one_dir, overlap, run_id,
            attempt_suffix="pipe", obs_prefetch_depth=1, **_OJW_PIPELINE_VALUES,
        )

        zero_documents = _trace_documents(zero_dir, run_id)
        one_documents = _trace_documents(one_dir, run_id)
        assert _request_payload_sha256s(zero_documents) == _request_payload_sha256s(
            one_documents
        ), "the pipeline moved a request byte"
        assert _obs_records(zero_documents) == _obs_records(one_documents)
        assert zero.outputs_path.read_bytes() == one.outputs_path.read_bytes()
        assert zero.cost["calls_used"] == one.cost["calls_used"] == 6
        assert overlap.saw_two_samples.is_set(), "the pipeline never overlapped two calls"
        assert overlap.max_distinct_samples >= 2

    def test_a_call_holds_one_slot_for_its_whole_life(
        self, synthetic_world, pipeline_repo, tmp_path  # noqa: F811 (the imported fixture, by name)
    ):
        """The affinity claim, measured on the wire: the pool bounds the
        in-flight count, no two live requests share an ``id_slot``, and each
        call's windows all carry the SAME slot integer -- the strongest form
        of ``id_slot='per-sample'``, and the form the plain policy's pipelined
        path cannot offer because one sample there spans the whole pool."""

        lock, repo_root = pipeline_repo
        run_id = "SAEA-E-000-ojw-slots"
        transport = _CountingTransport()
        result = _fly(
            synthetic_world, repo_root, lock, tmp_path / "slots", transport, run_id,
            obs_prefetch_depth=1, policy=OJW_POLICY_NAME, obs_batch_slices=2,
            decoding_params={
                "temperature": 0, "seed": 20260803, "id_slot": "per-sample",
            },
        )
        assert result.cost["calls_used"] == 6
        assert transport.peak_in_flight <= 2
        assert transport.peak_in_flight >= 2, "the pipeline never dispatched concurrently"
        assert transport.max_duplicate_slot == 1, "two live requests shared one id_slot"
        assert transport.slots_seen <= {0, 1}

        slots_by_call: dict[str, set] = {}
        for document in _trace_documents(tmp_path / "slots", run_id):
            if document["channel"] != "MODEL_REQUEST" or "-i" not in document["record_id"]:
                continue
            call = document["record_id"].split("-i")[0]
            slot = dict(document["payload"].get("decoding_params") or {}).get("id_slot")
            slots_by_call.setdefault(call, set()).add(slot)
        assert len(slots_by_call) == 3
        assert all(len(slots) == 1 for slots in slots_by_call.values()), slots_by_call
