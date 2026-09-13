"""Native decisions through the real shared client and OpenJiuwen; no network."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.controllers import (
    EvidenceAgentController, PhaseToolStep, default_phase_program,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_rails_frozen_core_client import _World, _client, _plan, _speech_feature_world
from test_rails_runner import _FakeAdapter, _knowledge_snapshot, _controller_registry


class NativeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, request_bytes):
        payload = json.loads(request_bytes)
        self.calls.append(payload)
        sample = payload["sample_id"]
        contact = payload["history"][-1]["contact_id"]
        requested = sample == "s2" and not contact.endswith(":final")
        if requested:
            calls = [{
                "id": "native-" + contact,
                "type": "function",
                "function": {"name": "fake_evidence", "arguments": "{}"},
            }]
            text = '[{"name":"fake_evidence","arguments":{}}]'
        else:
            calls = None
            text = "final-answer-" + sample
        return json.dumps({
            "text": text, "usage": {"prompt_tokens": 8, "completion_tokens": 4},
            "tool_calls": calls,
        }).encode()


class NativeEvidence:
    native_enabled = True

    def __init__(self):
        self.calls = []

    def is_action_phase(self, phase):
        return phase != "final"

    def is_native_phase(self, phase):
        return phase != "final"

    def __call__(self, phase, next_phase, context):
        completion = context.core_completions[0]
        self.calls.append((phase, context.sample_id, completion))
        return PhaseToolStep(
            supply=None,
            state=AgentStateArtifact(
                state_id=f"evidence:{context.sample_id}:{phase}",
                state_kind="tool-result",
                content=f"Returned evidence for {context.sample_id} from {phase}.",
                source_query_state_sha256=context.query_state.content_hash(),
                source_response_sha256=completion.response_text_sha256,
                producer_policy_id="fake-evidence-v1", cited_value_ids=(),
            ).validate(),
        )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("prepared", [False, True])
def test_native_agent_keeps_response_provenance_and_observations_across_real_executor(
    tmp_path, prepared,
):
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    transport = NativeTransport()
    plan = _plan()
    client, _, _ = _client(
        world, tmp_path, plan=plan, transport=transport,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root, speech_packet_bindings=bindings,
        tool_schemas=[{
            "type": "function",
            "function": {"name": "fake_evidence", "description": "Read evidence.",
                         "parameters": {"type": "object", "properties": {}}},
        }],
    )
    tools = NativeEvidence()
    registry = _controller_registry(
        "native-test-v1",
        lambda _sample_id: EvidenceAgentController(
            program=default_phase_program("native-answer-or-tool-v1"),
            tools_for_phase=tools,
            material_for_phase=lambda name, ctx: PhaseMaterial(
                instruction="Answer the task or request needed evidence.",
                response_format=None, contact_id=f"{ctx.sample_id}:{name}",
                purpose=name,
            ),
        ),
    )
    fitted = []

    def fit_gate(batch):
        fitted.append([request.as_payload() for request in batch])
        assert all(p["decoding_params"]["tool_choice"] in {"auto", "none"} for p in fitted[-1])

    trace = TraceBuffer(plan.run_id)
    summary = run_speech_native_agent_loop(
        data_root=world.data_root, plan=plan,
        adapter=_FakeAdapter(samples=tuple(world.samples)), core_client=client,
        split_id="all", knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings=bindings, controller_policy_id="native-test-v1",
        controller_registry=registry, max_contacts=3, slot_count=2, queue_depth=2,
        trace_sink=trace, agent_executor_id="openjiuwen-workflow-v1",
        decoding_params={"max_tokens": 256},
        request_batch_gate=fit_gate if prepared else None,
        whole_roster_wave_barrier=prepared,
    )
    assert [result.final_response_text for result in summary.results] == [
        "final-answer-s1", "final-answer-s2",
    ]
    assert [len(result.contacts) for result in summary.results] == [1, 3]
    assert [(p, s) for p, s, _ in tools.calls] == [
        ("decision-1", "s2"), ("decision-2", "s2"),
    ]
    assert len(transport.calls) == 4
    for phase, sample, completion in tools.calls:
        completion.assert_binding(
            sample_id=sample, agent_contact_id=f"{sample}:{phase}",
            response_text='[{"name":"fake_evidence","arguments":{}}]',
        )
    second = next(p for p in transport.calls
                  if p["history"][-1]["contact_id"] == "s2:decision-2")
    final = next(p for p in transport.calls
                 if p["history"][-1]["contact_id"] == "s2:final")
    assert "Returned evidence for s2 from decision-1." in json.dumps(second["history"])
    assert "Returned evidence for s2 from decision-1." in json.dumps(final["history"])
    assert "Returned evidence for s2 from decision-2." in json.dumps(final["history"])
    assert final["decoding_params"]["tool_choice"] == "none"
    provenance = [payload for channel, _record, payload in trace.records
                  if channel == "TOOL" and payload.get("schema") == "saea-native-completion-v1"]
    assert len(provenance) == 4
    assert {p["request_id"] for p in provenance} == {p["request_id"] for p in transport.calls}
    for p in provenance:
        assert hashlib.sha256(p["native_tool_calls_json"].encode()).hexdigest() == p["native_tool_calls_sha256"]
    if prepared:
        assert [[p["sample_id"] for p in wave] for wave in fitted] == [["s1", "s2"], ["s2"], ["s2"]]
        for checked in (p for wave in fitted for p in wave):
            actual = next(p for p in transport.calls
                          if p["history"][-1]["contact_id"] == checked["history"][-1]["contact_id"])
            actual = json.loads(json.dumps(actual))
            actual["request_id"] = checked["request_id"]
            actual["decoding_params"].pop("id_slot", None)
            assert actual == checked
    client.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_native_early_stop_fits_shrinking_real_request_waves(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_fit as fitting
    from speech_aware_evidence_acquisition.core.preparation_fit import (
        build_live_phase_fit_gate,
    )
    from speech_aware_evidence_acquisition.rails.phase_runner import (
        run_continuous_program,
    )
    from test_live_phase_fit import Runtime as FitRuntime
    from test_live_phase_fit import Tokenizer, values as fit_values

    monkeypatch.setattr(fitting, "packet_token_counts", lambda *_a, **_k: (1,))
    world = _World(tmp_path)
    feature_root, _packet, bindings = _speech_feature_world(world, tmp_path)
    transport = NativeTransport()
    execution_plan = _plan(planned_model_calls=6)
    client, _, _ = _client(
        world,
        tmp_path,
        plan=execution_plan,
        transport=transport,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
        tool_schemas=[
            {
                "type": "function",
                "function": {
                    "name": "fake_evidence",
                    "description": "Read evidence.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    tokenizer = Tokenizer()
    fit_runtime = FitRuntime(
        tmp_path,
        fit_values(
            live_phase_fit={
                "run_id": "SAEA-G6-LIVE-FIT-V1",
                "attempt_id": "attempt-g6-fit-v1",
                "contact_cap": 21,
            }
        ),
    )
    program = default_phase_program("native-answer-or-tool-v1")
    fit_gate = build_live_phase_fit_gate(
        fit_runtime,
        program,
        execution_plan,
        client_factory=lambda **_k: tokenizer,
        native_active_roster=True,
    )
    tools = NativeEvidence()
    tools.render_values = lambda _snapshot, _query_state, _agent_states: ()
    trace = TraceBuffer(execution_plan.run_id)

    try:
        summary = run_continuous_program(
            program=program,
            adapter=_FakeAdapter(samples=tuple(world.samples)),
            plan=execution_plan,
            data_root=world.data_root,
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=bindings,
            trace_sink=trace,
            decoding_params={"max_tokens": 256},
            material_for_phase=lambda name, context, _sealed: PhaseMaterial(
                instruction="Answer the task or request needed evidence.",
                response_format=None,
                contact_id=f"{context.sample_id}:{name}",
                purpose=name,
            ),
            tools_for_phase=tools,
            slot_count=2,
            queue_depth=2,
            whole_roster_wave_barrier=True,
            request_batch_gate=fit_gate,
        )
    finally:
        client.close()

    results = {result.sample_id: result for result in summary.results}
    assert set(results) == {"s1", "s2"}
    assert results["s1"].final_response_text == "final-answer-s1"
    assert results["s2"].final_response_text == "final-answer-s2"
    assert [len(results[sample].contacts) for sample in ("s1", "s2")] == [1, 3]
    assert all(sample != "s1" for _phase, sample, _completion in tools.calls)
    assert [(phase, sample) for phase, sample, _completion in tools.calls] == [
        ("decision-1", "s2"),
        ("decision-2", "s2"),
    ]
    assert [receipt["phase"] for receipt in fit_gate.receipts] == [
        "decision-1",
        "decision-2",
        "final",
    ]
    assert fit_gate.execution_plan.planned_model_calls == 21
    assert len(tokenizer.calls) == 15

    fit_root = (
        tmp_path
        / "prepared"
        / fit_gate.execution_plan.run_id
        / fit_gate.execution_plan.attempt_id
    )
    fitted = {}
    for phase in ("decision-1", "decision-2", "final"):
        document = json.loads((fit_root / f"{phase}.request-fit.json").read_text())
        assert document["output"]["every_request_fits"] is True
        assert document["output"]["generation_contacts"] == 0
        for payload in document["inputs"]["sources"]["payloads"]:
            fitted[payload["history"][-1]["contact_id"]] = payload
    sent = {payload["history"][-1]["contact_id"]: payload for payload in transport.calls}
    assert fitted.keys() == sent.keys()
    for contact_id, payload in fitted.items():
        actual = json.loads(json.dumps(sent[contact_id]))
        actual["request_id"] = payload["request_id"]
        actual["decoding_params"].pop("id_slot", None)
        assert actual == payload
