"""Native model-selected dispatch over the shared phase-tool implementation."""
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.core_client import (
    CoreCompletion,
    _tool_schemas_sha256,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.phase_tools import (
    LIVE_SPEECH_OBSERVATION_TOOL as LIVE, PHASE_KNOWLEDGE_TOOL as KNOWLEDGE,
    TASK_CONTRACT_TOOL as TASK,
    PhaseToolError, build_phase_tools, load_phase_tool_specs)
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


class NativeRoleProgram:
    program_id = "native-role-episode-v1"
    stop_rule = "native-role-episode"

    def phase_names(self):
        return ("reviewer", "planner", "final")

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

def dispatcher(*tools, provider=None, supply=None, custody=None, authority_role=None):
    config = native_config(*tools)
    if authority_role is not None:
        for spec in config["phase_tools"].values():
            spec["source_authority_role"] = authority_role
    return build_phase_tools(
        config, NativeProgram(), snapshot=_knowledge_snapshot(),
        supply_for_phase=supply, live_speech_observations=provider,
        tool_contact=custody or Custody())


def role_episode_config(*, reviewer=None, planner=None):
    entries = {}
    for role, tools in (("reviewer", reviewer), ("planner", planner)):
        if tools is not None:
            entries[role] = {
                "mode": "native-tools",
                "allowed_tools": list(tools),
                "knowledge_views": ["text"],
                "source_authority_role": role,
            }
    return {"phase_tools": entries}


def staged_role_episode(tool, *, request_id, call_id, role="reviewer", text=None,
                        contact_role=None, prior_states=()):
    base = _context()
    calls = call(arguments=ARGS)
    calls[0]["id"] = call_id
    text = text or json.dumps(
        [{"request_id": request_id, "call_id": call_id}], sort_keys=True
    )
    text_sha = hashlib.sha256(text.encode()).hexdigest()
    state = AgentStateArtifact(
        state_id=f"{role}:{request_id}:{base.sample_id}",
        state_kind=f"phase:{role}",
        content=text,
        source_query_state_sha256=base.query_state.content_hash(),
        source_response_sha256=text_sha,
        producer_policy_id=NativeRoleProgram.program_id,
        cited_value_ids=(),
    ).validate()
    schemas = tuple(
        schema for schema in tool.native_tool_schemas()
        if schema["function"]["name"] == LIVE
    )
    contact_role = contact_role or role
    contact_id = (
        f"{NativeRoleProgram.program_id}:{contact_role}:1:{base.sample_id}"
    )
    message = {"role": "assistant", "content": None, "tool_calls": calls}
    wire = json.dumps({
        "choices": [{"message": message, "finish_reason": "tool_calls"}]
    }, separators=(",", ":")).encode()
    completion = CoreCompletion(
        text=text,
        request_id=request_id,
        sample_id=base.sample_id,
        agent_contact_id=contact_id,
        request_sha256="b" * 64,
        response_sha256="c" * 64,
        response_text_sha256=text_sha,
        tool_calls_json=json.dumps(
            calls, sort_keys=True, separators=(",", ":")
        ).encode(),
        wire_response_bytes=wire,
        tool_names=(LIVE,),
        tool_schemas_sha256=_tool_schemas_sha256(schemas),
    )
    return SimpleNamespace(**{
        **base.__dict__,
        "agent_states": (*prior_states, state),
        "prior_response_sha256s": (text_sha,),
        "core_completions": (completion,),
    })

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


def test_role_episode_exposes_ordered_union_for_only_selected_roles():
    config = role_episode_config(reviewer=(LIVE,), planner=(TASK, LIVE))
    tool = build_phase_tools(
        config,
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=LiveProvider(),
        tool_contact=Custody(),
    )
    assert tool.native_enabled
    assert tool.is_native_phase("reviewer")
    assert tool.is_native_phase("planner")
    assert not tool.is_native_phase("final")
    assert [schema["function"]["name"] for schema in tool.native_tool_schemas()] == [
        LIVE,
        TASK,
    ]

    selected = build_phase_tools(
        role_episode_config(reviewer=(LIVE,)),
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=LiveProvider(),
        tool_contact=Custody(),
    )
    assert selected.is_native_phase("reviewer")
    assert not selected.is_native_phase("planner")
    assert [
        schema["function"]["name"] for schema in selected.native_tool_schemas()
    ] == [LIVE]


def test_role_episode_rejects_one_tool_name_with_different_role_schemas():
    config = role_episode_config(reviewer=(KNOWLEDGE,), planner=(KNOWLEDGE,))
    config["phase_tools"]["planner"]["knowledge_views"] = ["speech"]
    with pytest.raises(PhaseToolError, match="different schemas"):
        load_phase_tool_specs(config, NativeRoleProgram())


def test_role_episode_allows_two_successive_counted_calls_in_one_role():
    provider, custody, events = LiveProvider(), Custody(), []
    tool = build_phase_tools(
        role_episode_config(reviewer=(LIVE,)),
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=provider,
        tool_contact=custody,
        trace_sink=SimpleNamespace(
            emit=lambda axis, event_id, payload: events.append(
                (axis, event_id, payload)
            )
        ),
    )
    first_context = staged_role_episode(
        tool, request_id="request-1", call_id="call-1"
    )
    first = tool("reviewer", "reviewer", first_context)
    second_context = staged_role_episode(
        tool,
        request_id="request-2",
        call_id="call-2",
        prior_states=(first.state,),
    )
    second = tool("reviewer", "reviewer", second_context)

    assert len(provider.calls) == len(custody.calls) == 2
    assert tool.receipt()["attempts"] == tool.receipt()["completed"] == 2
    assert first.state.state_id != second.state.state_id
    result_event_ids = [event_id for _, event_id, _ in events if "tool-result" in event_id]
    assert len(result_event_ids) == len(set(result_event_ids)) == 2
    for context, step in ((first_context, first), (second_context, second)):
        document = json.loads(step.state.content)
        assert document["query_state_sha256"] == context.query_state.content_hash()
        assert document["source_response_sha256"] == (
            context.agent_states[-1].source_response_sha256
        )
        assert document["source_authority"]["role_id"] == "reviewer"


def test_role_episode_refuses_duplicate_source_without_duplicate_execution():
    provider, custody = LiveProvider(), Custody()
    tool = build_phase_tools(
        role_episode_config(reviewer=(LIVE,)),
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=provider,
        tool_contact=custody,
    )
    context = staged_role_episode(tool, request_id="request-1", call_id="call-1")
    tool("reviewer", "reviewer", context)
    with pytest.raises(PhaseToolError, match="source completion/tool call"):
        tool("reviewer", "reviewer", context)
    assert len(provider.calls) == len(custody.calls) == 1


@pytest.mark.parametrize("mismatch", ["source", "role"])
def test_role_episode_refuses_wrong_completion_source_or_role(mismatch):
    provider, custody = LiveProvider(), Custody()
    tool = build_phase_tools(
        role_episode_config(reviewer=(LIVE,)),
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=provider,
        tool_contact=custody,
    )
    context = staged_role_episode(
        tool,
        request_id="request-1",
        call_id="call-1",
        contact_role="planner" if mismatch == "role" else "reviewer",
    )
    if mismatch == "source":
        completion = replace(context.core_completions[0], text="foreign source")
        context = SimpleNamespace(**{
            **context.__dict__, "core_completions": (completion,)
        })
    with pytest.raises(PhaseToolError):
        tool("reviewer", "reviewer", context)
    assert provider.calls == [] and custody.calls == []
    assert tool.receipt()["native_rejected_requests"]["count"] == 1


def test_legacy_native_attempt_scope_and_selective_config_remain_unchanged():
    selective = native_config(LIVE)
    del selective["phase_tools"]["decision-2"]
    with pytest.raises(PhaseToolError, match="every nonfinal phase"):
        load_phase_tool_specs(selective, NativeProgram())

    provider, custody = LiveProvider(), Custody()
    tool = dispatcher(LIVE, provider=provider, custody=custody)
    context = staged_native(call())
    tool("decision-1", "decision-2", context)
    with pytest.raises(PhaseToolError, match="phase/sample"):
        tool("decision-1", "decision-2", context)
    assert len(provider.calls) == len(custody.calls) == 1

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


def test_native_receipt_counts_rejected_requests_without_changing_tool_counts():
    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native([])
    tool("decision-1", "decision-2", context)
    receipt = tool.receipt()
    assert receipt["attempts"] == 0 and receipt["completed"] == 0
    assert receipt["native_rejected_requests"]["count"] == 1
    assert len(receipt["native_rejected_requests"]["hashes"]) == 1


def test_conflicting_duplicate_live_evidence_is_rejected():
    class ConflictingProvider(LiveProvider):
        def observe(self, **kwargs):
            selection = super().observe(**kwargs)
            if len(self.calls) == 2:
                visible = dict(selection.visible)
                visible["transcript"] = "Conflicting transcript."
                return SpeechObservationSelection(
                    visible=visible, lineage=selection.lineage
                )
            return selection

    provider = ConflictingProvider()
    tool = dispatcher(LIVE, provider=provider)
    first_context = staged_native(call())
    first = tool("decision-1", "decision-2", first_context)
    second_context = staged_native(
        call(), phase="decision-2", prior_states=(first.state,)
    )
    with pytest.raises(PhaseToolError, match="conflicting"):
        tool("decision-2", "final", second_context)


def test_legacy_dispatcher_receipt_has_no_native_rejection_extension():
    from test_phase_tools import config as legacy_config

    tool = build_phase_tools(
        legacy_config("fixed"),
        rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(),
    )
    assert "native_rejected_requests" not in tool.receipt()
