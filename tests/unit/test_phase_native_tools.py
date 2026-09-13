"""Native model-selected dispatch over the shared phase-tool implementation."""
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails.core_client import CoreCompletion
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.phase_tools import (
    LIVE_SPEECH_OBSERVATION_TOOL as LIVE, PHASE_KNOWLEDGE_TOOL as KNOWLEDGE,
    PhaseToolError, build_phase_tools)
from speech_aware_evidence_acquisition.rails.speech_observation import SpeechObservationSelection
from test_phase_tools import _context
from test_rails_controllers import _phase_supply
from test_rails_runner import _knowledge_snapshot

ARGS = {"span": "full-utterance", "representation": "asr-transcript",
        "distinction": "Resolve the spoken timer duration."}

class NativeProgram:
    program_id = "native-answer-or-tool-v1"
    stop_rule = "native-answer-or-tool"
    def phase_names(self):
        return ("decision-1", "decision-2", "final")

class LiveProvider:
    def __init__(self): self.calls = []
    def observe(self, *, context, arguments, source_response_sha256):
        self.calls.append((context.sample_id, dict(arguments), source_response_sha256))
        return SpeechObservationSelection(
            visible={"schema": "saea-live-speech-observation-selection-v1",
                     "evidence_id": "live-one", "artifact_sha256": "a" * 64,
                     "source_uri": "live-speech-observation://" + "a" * 64 + "/live-one",
                     "status": "ok", "transcript": "Set the timer for fifteen minutes.",
                     "sample_id": context.sample_id,
                     "speech_packet_id": context.query_state.speech_packet_id,
                     "speech_packet_sha256": context.query_state.speech_packet_sha256},
            lineage={
                "schema": "saea-live-speech-observation-lineage-v1",
                "source_response_sha256": source_response_sha256,
            })
    def receipt(self):
        return {"schema": "saea-live-speech-observation-provider-receipt-v1"}

class Custody:
    def __init__(self): self.calls = []
    def __call__(self, **facts):
        self.calls.append(facts)
        return {"invocation_id": f"tool-{len(self.calls)}"}

def native_config(*tools):
    return {"phase_tools": {phase: {"mode": "native-tools",
                                    "allowed_tools": list(tools),
                                    "knowledge_views": ["text"]}
                            for phase in ("decision-1", "decision-2")}}

def staged_native(tool_calls, *, phase="decision-1", prior_states=(), query_state=None):
    base = _context()
    if query_state is not None:
        base = replace(base, query_state=query_state)
    text = json.dumps([{"name": "canonical text is not authority"}])
    text_sha = hashlib.sha256(text.encode()).hexdigest()
    state = AgentStateArtifact(
        state_id=f"{phase}:s1", state_kind=f"phase:{phase}", content=text,
        source_query_state_sha256=base.query_state.content_hash(),
        source_response_sha256=text_sha, producer_policy_id=NativeProgram.program_id,
        cited_value_ids=()).validate()
    completion = CoreCompletion(
        text=text, request_id=f"request-{phase}", sample_id=base.sample_id,
        agent_contact_id=phase, request_sha256="b" * 64, response_sha256="c" * 64,
        response_text_sha256=text_sha,
        tool_calls_json=json.dumps(tool_calls, separators=(",", ":")).encode())
    return SimpleNamespace(**{**base.__dict__, "agent_states": (*prior_states, state),
                              "prior_response_sha256s": (text_sha,),
                              "core_completions": (completion,)})

def call(name=LIVE, arguments=None):
    return [{"id": "call-1", "type": "function",
             "function": {"name": name, "arguments": json.dumps(arguments or ARGS)}}]

def dispatcher(*tools, provider=None, supply=None, custody=None):
    return build_phase_tools(
        native_config(*tools), NativeProgram(), snapshot=_knowledge_snapshot(),
        supply_for_phase=supply, live_speech_observations=provider,
        tool_contact=custody or Custody())

def test_native_mode_exposes_only_configured_openai_functions():
    tool = dispatcher(LIVE, provider=LiveProvider())
    assert tool.native_enabled and tool.is_native_phase("decision-1")
    assert not tool.is_native_phase("final")
    schemas = tool.native_tool_schemas()
    assert len(schemas) == 1 and schemas[0]["type"] == "function"
    function = schemas[0]["function"]
    assert function["name"] == LIVE
    assert function["parameters"]["additionalProperties"] is False
    assert set(function["parameters"]["required"]) == set(ARGS)
    instruction = tool.instruction_for_phase("decision-1", _context())
    assert "answer the task directly" in instruction.lower() and "must call" not in instruction.lower()

def test_native_live_call_debits_custody_then_returns_bound_evidence():
    provider, custody = LiveProvider(), Custody()
    tool = dispatcher(LIVE, provider=provider, custody=custody)
    context = staged_native(call())
    step = tool("decision-1", "decision-2", context)
    assert provider.calls == [("s1", ARGS, context.agent_states[-1].source_response_sha256)]
    assert custody.calls[0]["tool_id"] == LIVE
    document = json.loads(step.state.content)
    assert document["selection_mode"] == "native-tools"
    assert document["tool_invocation"] == {"invocation_id": "tool-1"}
    assert "transcript" not in document["result"]
    query = replace(context.query_state, agent_state_ids=(step.state.state_id,))
    blocks = tool.render_values(_knowledge_snapshot(), query, (step.state,))
    assert [block.get("evidence_id") for block in blocks] == ["live-one"]
    assert "fifteen" in blocks[0]["text"]

@pytest.mark.parametrize("bad", [
    [], call() * 2,
    [{"id": "call-1", "type": "function",
      "function": {"name": LIVE, "arguments": "{"}}],
    [{"id": "call-1", "type": "function",
      "function": {"name": "not-allowed", "arguments": "{}"}}],
    [{"id": "call-1", "type": "function",
      "function": {"name": LIVE, "arguments": json.dumps({**ARGS, "path": "/tmp/x.wav"})}}],
])
def test_bad_native_calls_return_source_bound_tool_error_without_execution(bad):
    provider, custody = LiveProvider(), Custody()
    tool = dispatcher(LIVE, provider=provider, custody=custody)
    context = staged_native(bad)
    step = tool("decision-1", "decision-2", context)
    assert provider.calls == [] and custody.calls == []
    document = json.loads(step.state.content)
    assert document["schema"] == "saea-phase-tool-error-v1"
    assert document["source_response_sha256"] == context.agent_states[-1].source_response_sha256
    assert "tool_calls" not in document
    query = replace(context.query_state, agent_state_ids=(step.state.state_id,))
    blocks = tool.render_values(_knowledge_snapshot(), query, (step.state,))
    assert blocks[-1]["evidence_id"] == step.state.state_id
    assert "rejected" in blocks[-1]["text"]

def test_native_dispatch_ignores_canonical_text_fallback_and_requires_completion():
    provider = LiveProvider()
    tool = dispatcher(LIVE, provider=provider)
    context = staged_native(call())
    missing = SimpleNamespace(**{**context.__dict__, "core_completions": ()})
    step = tool("decision-1", "decision-2", missing)
    assert json.loads(step.state.content)["schema"] == "saea-phase-tool-error-v1"
    assert provider.calls == []

def test_live_observation_persists_when_later_knowledge_is_selected():
    provider = LiveProvider()
    snapshot = _knowledge_snapshot()
    tool = dispatcher(LIVE, KNOWLEDGE, provider=provider, supply=lambda _phase, ctx: _phase_supply(
            ctx, value_ids=(ctx.query_state.retrieved_value_ids[0],),
            facet_ids=(snapshot.facets[0].facet_id,)))
    query = replace(
        _context().query_state,
        retrieved_value_ids=(snapshot.values[0].value_id,),
    )
    first_context = staged_native(call(), query_state=query)
    first = tool("decision-1", "decision-2", first_context)
    second_context = staged_native(
        call(KNOWLEDGE, {"view": "text"}), phase="decision-2",
        prior_states=(first.state,), query_state=query,
    )
    second = tool("decision-2", "final", second_context)
    query = replace(second_context.query_state,
                    agent_state_ids=(first.state.state_id, second.state.state_id))
    blocks = tool.render_values(snapshot, query, (first.state, second.state))
    assert sum(block.get("evidence_id") == "live-one" for block in blocks) == 1
    assert any(block.get("knowledge_role") == "value" for block in blocks)

def test_native_config_requires_all_nonfinal_phases_and_live_custody():
    config = native_config(LIVE)
    del config["phase_tools"]["decision-2"]
    with pytest.raises(PhaseToolError):
        build_phase_tools(config, NativeProgram(), snapshot=_knowledge_snapshot())
    with pytest.raises(PhaseToolError, match="tool contact"):
        build_phase_tools(native_config(LIVE), NativeProgram(),
                          snapshot=_knowledge_snapshot(),
                          live_speech_observations=LiveProvider())
