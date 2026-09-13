"""Verified TRAIN feedback reaches the actual shared proposal request and fit gate."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.core.preparation_fit import boundary_identity
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_artifact_result_kind import _plan as artifact_plan, _roster, _values
from test_prepared_feedback_serialization import _prepared_state
from test_rails_frozen_core_client import _CapturingTransport, _World, _client, _plan, _speech_feature_world
from test_rails_runner import _FakeAdapter, _knowledge_snapshot


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("seeded", [False, True])
def test_shared_proposal_fit_and_send_use_identical_initial_feedback(tmp_path, seeded):
    world = _World(tmp_path)
    root, _packet, bindings = _speech_feature_world(world, tmp_path)
    transport = _CapturingTransport(lambda _payload: "Provisional correction.")
    plan = _plan(planned_model_calls=2)
    client, _, _ = _client(
        world, tmp_path, plan=plan, transport=transport, arm="speech-feature-query",
        speech_feature_root=root, speech_packet_bindings=bindings,
    )
    state = _prepared_state()
    fitted = []
    trace = TraceBuffer(plan.run_id)

    def fit(phase, requests):
        assert phase == "direct"
        assert not transport.calls
        fitted.extend(request.as_payload() for request in requests)

    options = {"initial_feedback_states": {sample: state for sample in bindings}} if seeded else {}
    try:
        summary = run_continuous_program(
            program=default_phase_program("phase-direct-only-v1"),
            adapter=_FakeAdapter(samples=tuple(world.samples)), plan=plan,
            data_root=world.data_root, core_client=client, split_id="all",
            knowledge_snapshot=_knowledge_snapshot(), speech_packet_bindings=bindings,
            trace_sink=trace, decoding_params={"max_tokens": 512},
            material_for_phase=lambda phase, ctx, sealed: PhaseMaterial(
                instruction="Propose a provisional correction from the organized feedback.",
                response_format=None, contact_id=f"proposal:{ctx.sample_id}", purpose=phase,
            ),
            result_kind="artifact", whole_roster_wave_barrier=True,
            request_batch_gate=fit, slot_count=2, queue_depth=2, **options,
        )
        assert len(transport.calls) == len(fitted) == 2
        assert all(result.metrics == {} for result in summary.results)
        actual = {row["sample_id"]: row for row in transport.calls}
        for checked in fitted:
            sent = actual[checked["sample_id"]]
            assert boundary_identity((checked,)) == boundary_identity((sent,))
            history = sent["history"]
            assert history[-1]["role"] == "control"
            assert state.content not in history[-1]["content"]
            if seeded:
                assert history[0]["content"] == state.content
                assert history[0]["prepared_artifact_sha256"] == state.prepared_artifact_sha256
                assert "source_response_sha256" not in history[0]
                assert history[0]["state_id"] == state.state_id
            else:
                assert [row["role"] for row in history] == ["control"]
        org = [row for kind, _, row in trace.records if kind == "ORG" and "org_initial_query_state" in row]
        assert len(org) == 2
        assert all(("org_prepared_feedback_seeds" in row) == seeded for row in org)
        assert not any(kind == "SCORE" for kind, _, _ in trace.records)
    finally:
        client.close()


def test_runtime_feedback_binding_checks_role_and_threads_verified_cohort(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting
    import speech_aware_evidence_acquisition.rails.prepared_feedback as feedback

    ids, identity, roster, digest = _roster(tmp_path)
    values = _values(roster, digest, carrier_lock_key="slurp", prepared_training_feedback={"pinned": "fixture"})
    calls = []
    states = {sample: _prepared_state() for sample in ids}
    def load(spec, **kwargs):
        calls.append((spec, kwargs))
        return states, {"verified": True}
    monkeypatch.setattr(feedback, "load_prepared_feedback", load)
    monkeypatch.setattr(fitting, "validate_live_phase_fit_config", lambda *_args: {"enabled": True})
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._samples = tuple(SimpleNamespace(sample_id=sample) for sample in ids)
    runtime._plan = artifact_plan(identity)
    runtime._repo_root = tmp_path
    runtime._data_root = tmp_path / "data"
    program = default_phase_program("phase-direct-only-v1")
    assert runtime._prepared_feedback_binding(program) == (states, {"verified": True})
    assert calls[0][1]["sample_ids"] == ids
    assert calls[0][1]["construction_roster_sha256"] == digest
    assert calls[0][1]["artifact_role"] == "training-feedback-proposal"
    values["result_kind"] = "task-answer"
    with pytest.raises(FlightRuntimeError, match="artifact_result"):
        runtime._prepared_feedback_binding(program)
    assert len(calls) == 1
    values["result_kind"] = "artifact"
    monkeypatch.setattr(fitting, "validate_live_phase_fit_config", lambda *_args: None)
    with pytest.raises(FlightRuntimeError, match="actual per-wave"):
        runtime._prepared_feedback_binding(program)
    assert len(calls) == 1
