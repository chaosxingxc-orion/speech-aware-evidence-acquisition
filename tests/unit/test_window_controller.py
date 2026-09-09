"""The shared controller owns real E21 window contacts without wire drift."""

from __future__ import annotations

import json
import hashlib
from dataclasses import replace

import pytest
import test_e21_repair_loop as fixtures

from speech_aware_evidence_acquisition.core.bundle import verify_bundle
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.errors import RailsError

repair_repo = fixtures.repair_repo


def test_query_state_names_bound_raw_speech_honestly():
    state = QueryState(
        "query", "call", "audio-window", "a" * 64, "b" * 64, query_source="speech_audio"
    )
    assert state.validate().as_json()["query_source"] == "speech_audio"
    with pytest.raises(RailsError):
        replace(state, query_source="generated_transcript").validate()


@pytest.mark.parametrize(
    "policy",
    ["obs-agent-loop", "obs-repair-loop", "obs-agent-loop-ojw", "obs-repair-loop-ojw"],
)
@pytest.mark.parametrize("terminal", ["success", "retry", "skip", "saturation"])
def test_controller_bridge_preserves_requests_and_delivered_outputs(
    synthetic_world, tmp_path, repair_repo, policy, terminal
):
    sent = []

    def transport(raw):
        request = json.loads(raw)
        sent.append(request)
        rid = request["request_id"]
        first = "-i0000" in rid
        if first and (
            terminal == "skip" or (terminal == "retry" and not rid.endswith("-r1"))
        ):
            raise TimeoutError("synthetic retry")
        source = (
            fixtures._predecessor_of(request)
            if policy.startswith("obs-repair-loop")
            else "direct transcript"
        )
        return json.dumps(
            {
                "text": "  " + source.replace("Ponton", "Pontone") + "  ",
                "usage": {
                    "completion_tokens": 10 if first and terminal == "saturation" else 1
                },
            }
        ).encode()

    overrides = dict(
        policy=policy,
        obs_slice_retry_max=1,
        decoding_params={"temperature": 0, "max_tokens": 10},
    )
    plain_path, _ = fixtures._run(
        synthetic_world,
        tmp_path,
        repair_repo,
        transport,
        run_id="SAEA-E-000-window-historical",
        **overrides,
    )
    historical_requests = list(sent)
    sent.clear()
    bridge_path, _ = fixtures._run(
        synthetic_world,
        tmp_path,
        repair_repo,
        transport,
        run_id="SAEA-E-000-window-controller",
        obs_controller_program="phase-direct-only-v1",
        **overrides,
    )
    historical, bridge = verify_bundle(plain_path), verify_bundle(bridge_path)

    def wire_identity(request):
        # Run-scoped artifact names differ, but their actual speech bytes and
        # every other model-visible request field must match exactly.
        request = dict(request)
        path = synthetic_world.data_root / request.pop("media_relpath")
        request["audio_bytes_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return request

    assert sorted(map(wire_identity, sent), key=lambda r: r["request_id"]) == sorted(
        map(wire_identity, historical_requests), key=lambda r: r["request_id"]
    )
    assert [row["text"] for row in bridge.outputs_rows] == [
        row["text"] for row in historical.outputs_rows
    ]
    records = [
        (rid, payload)
        for rid, payload in bridge.trace_records.items()
        if rid.endswith("/window-controller")
    ]
    assert len(records) == 6
    state_ids = [
        payload["use_sealed_state"]["state_id"]
        for _, payload in records
        if payload["use_sealed_state"] is not None
    ]
    assert len(state_ids) == len(set(state_ids))
    for rid, record in records:
        actual = record["use_terminal_request_id"]
        assert rid == f"{actual}/window-controller"
        assert record["use_program_id"] == "phase-direct-only-v1"
        assert record["use_query_state"]["query_source"] == "speech_audio"
        assert record["use_query_state"]["query_sample_id"] in fixtures.E21_IDS
        assert (
            record["use_contact"]["instruction"]
            == bridge.trace_records[f"{actual}/request"]["payload"]["task_instruction"]
        )
        if record["use_skipped"]:
            assert record["use_transition"] is None
            assert record["use_sealed_state"] is None
            assert f"{actual}/response" not in bridge.trace_records
        else:
            response = bridge.trace_records[f"{actual}/response"]
            assert (
                record["use_sealed_state"]["source_response_sha256"]
                == response["response_text_sha256"]
            )
            assert record["use_transition"]["action_kind"] == "stop"


@pytest.mark.parametrize(
    "values",
    [
        {"obs_controller_program": "phase-draft-revise-v1"},
        {"obs_controller_program": "phase-direct-only-v1", "policy": "fixed"},
        {
            "obs_controller_program": "phase-direct-only-v1",
            "policy": "obs-agent-loop-ojw",
            "obs_boundary_mode": "model",
        },
        {
            "obs_controller_program": "phase-direct-only-v1",
            "policy": "obs-agent-loop-ojw",
            "judges": {"on": True},
        },
    ],
)
def test_bridge_refuses_unimplemented_programs_and_inert_module_switches(values):
    from speech_aware_evidence_acquisition.reproduction.window_controller import (
        validate_window_controller,
        WindowControllerError,
    )

    with pytest.raises(WindowControllerError):
        validate_window_controller(values)


def test_controller_requires_real_plan_and_one_bound_terminal_response():
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
    from speech_aware_evidence_acquisition.reproduction.window_controller import (
        ControllerWindowHook,
        WindowControllerError,
    )

    ctx = SimpleNamespace(
        extras={},
        sample=SimpleNamespace(sample_id="call"),
        request_id_base="req-1",
        task_instruction="Transcribe.",
        sink=TraceBuffer("synthetic"),
    )
    with pytest.raises(WindowControllerError, match="ExecutionPlan"):
        ControllerWindowHook(ctx)
    ctx.extras["execution_plan"] = ExecutionPlan(
        run_id="SAEA-E-000-synthetic",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=1,
        planned_gpu_hours=1,
        planned_speech_audio_seconds=1,
        protocol_hash="b" * 64,
        attempt_id="attempt-synthetic",
    )
    hook = ControllerWindowHook(ctx)
    record = SimpleNamespace(sha256="c" * 64, media_relpath="derived/window.wav")
    assert (
        hook.instruction(iteration=0, record=record, default="Transcribe.")
        == "Transcribe."
    )
    with pytest.raises(WindowControllerError, match="changed"):
        hook.instruction(iteration=0, record=record, default="Different.")
    with pytest.raises(WindowControllerError, match="authoritative"):
        hook.accept(iteration=0, record=record, transcript="text")
    with pytest.raises(WindowControllerError, match="binding"):
        hook.terminal(
            iteration=0,
            request_id="req-1-i0000",
            response=None,
            skipped=False,
            saturated=False,
        )
    with pytest.raises(WindowControllerError, match="identity"):
        hook.terminal(
            iteration=0,
            request_id="other-i0000",
            response=None,
            skipped=True,
            saturated=False,
        )
    hook.terminal(
        iteration=0,
        request_id="req-1-i0000-r1",
        response=None,
        skipped=True,
        saturated=False,
    )
    with pytest.raises(WindowControllerError, match="already"):
        hook.terminal(
            iteration=0,
            request_id="req-1-i0000-r1",
            response=None,
            skipped=True,
            saturated=False,
        )
    assert hook.accept(iteration=0, record=record, transcript="", skipped=True) == (
        "",
        {"obs_controller_program": "phase-direct-only-v1"},
    )
    with pytest.raises(WindowControllerError, match="authoritative"):
        hook.accept(iteration=0, record=record, transcript="", skipped=True)


def test_controller_context_records_ordered_evidence_without_changing_window_instruction():
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.base import EvidenceItem
    from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
    from speech_aware_evidence_acquisition.reproduction.window_controller import (
        ControllerWindowHook,
        _NULL_KNOWLEDGE,
    )

    plan = ExecutionPlan(
        run_id="SAEA-E-000-synthetic",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=1,
        planned_gpu_hours=1,
        planned_speech_audio_seconds=1,
        protocol_hash="b" * 64,
        attempt_id="attempt-synthetic",
    )

    def hook_for(evidence):
        ctx = SimpleNamespace(
            extras={"execution_plan": plan},
            evidence=evidence,
            sample=SimpleNamespace(sample_id="call"),
            request_id_base="req-1",
            task_instruction="Transcribe.",
            sink=TraceBuffer("synthetic"),
        )
        return ControllerWindowHook(ctx)

    record = SimpleNamespace(sha256="c" * 64, media_relpath="derived/window.wav")
    empty = hook_for([])
    assert empty.instruction(iteration=0, record=record, default="Transcribe.") == "Transcribe."
    assert empty._windows[0].knowledge == _NULL_KNOWLEDGE
    first = EvidenceItem("first", "source://one", "one", {"lock_key": "x", "relpath": "x", "sha256": "a" * 64})
    second = EvidenceItem("second", "source://two", "two", {"lock_key": "x", "relpath": "y", "sha256": "b" * 64})
    bound = hook_for([first, second])
    assert bound.instruction(iteration=0, record=record, default="Transcribe.") == "Transcribe."
    knowledge = bound._windows[0].knowledge
    assert knowledge["schema"] == "saea-window-controller-context-v2"
    assert knowledge["knowledge"] == "external-evidence"
    assert [item["evidence_id"] for item in knowledge["items"]] == ["first", "second"]
    bound.terminal(
        iteration=0,
        request_id="req-1-i0000",
        response=None,
        skipped=True,
        saturated=False,
    )
    bound.accept(iteration=0, record=record, transcript="", skipped=True)
    assert bound._ctx.sink.records[-1][2]["use_context"] == knowledge
    changed = hook_for([replace(first, content="changed"), second])
    changed.instruction(iteration=0, record=record, default="Transcribe.")
    assert changed._windows[0].context.knowledge_snapshot_sha256 != bound._windows[0].context.knowledge_snapshot_sha256
