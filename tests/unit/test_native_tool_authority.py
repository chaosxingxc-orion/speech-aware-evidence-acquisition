"""Source authority binds historical native calls to their actual exposure."""

import copy
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_history import (
    project_native_history,
)
from speech_aware_evidence_acquisition.rails.core_client import _tool_schemas_sha256
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.native_tool_authority import (
    NativeToolAuthorityError,
    build_native_tool_authority,
)
from test_native_history_projection import project, world
from test_phase_native_tools import LIVE, LiveProvider, call, dispatcher, staged_native

ROLE = "reviewer"


def _completion(context, schemas, *, content=None):
    old = context.core_completions[0]
    calls = call()
    message = {"role": "assistant", "content": content, "tool_calls": calls}
    wire = json.dumps(
        {"choices": [{"message": message, "finish_reason": "tool_calls"}]},
        separators=(",", ":"),
    ).encode()
    return replace(
        old,
        request_sha256="1" * 64,
        response_sha256="2" * 64,
        tool_calls_json=json.dumps(
            calls, sort_keys=True, separators=(",", ":")
        ).encode(),
        wire_response_bytes=wire,
        tool_names=tuple(s["function"]["name"] for s in schemas),
        tool_schemas_sha256=_tool_schemas_sha256(schemas),
    )


def _authority_world():
    tool = dispatcher(LIVE, provider=LiveProvider(), authority_role=ROLE)
    context = staged_native(call())
    completion = _completion(context, tool.native_tool_schemas())
    context = SimpleNamespace(**{**context.__dict__, "core_completions": (completion,)})
    counted = []
    custody = SimpleNamespace(
        _samples=[SimpleNamespace(sample_id=context.sample_id)],
        _live_speech_source_bindings={
            context.sample_id: {
                "packet_id": context.query_state.speech_packet_id,
                "packet_sha256": context.query_state.speech_packet_sha256,
            }
        },
        _client=SimpleNamespace(record_tool_call=lambda **facts: counted.append(facts)),
        assert_generation_lease=lambda: None,
        _live_speech_units=lambda: None,
    )
    tool.tool_contact = lambda **facts: FlightRuntime._record_phase_tool_contact(
        custody, **facts
    )
    step = tool("decision-1", "decision-2", context)
    states = (*context.agent_states, step.state)
    from speech_aware_evidence_acquisition.rails.core_client import _agent_history
    from speech_aware_evidence_acquisition.core.model.transport import (
        _speech_history_texts,
    )

    history = _agent_history(
        agent_state=[s.as_json() for s in states],
        agent_contact_id="final",
        contact_instruction="Deliver the final task JSON.",
    )
    texts = _speech_history_texts(history)
    payload = {
        "sample_id": context.sample_id,
        "speech_feature_parts": [
            {
                "packet_id": context.query_state.speech_packet_id,
                "sha256": context.query_state.speech_packet_sha256,
                "role": "query",
            }
        ],
        "history": history,
        "tool_schemas": [],
        "decoding_params": {"tool_choice": "none", "parallel_tool_calls": False},
        "supplied_evidence": [],
    }
    messages = [
        {"role": "system", "content": "Solve."},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": payload["speech_feature_parts"][0],
                },
                *({"type": "text", "text": v} for v in texts),
            ],
        },
    ]
    return tool, context, completion, step, payload, messages, texts, counted


def test_builder_preserves_null_assistant_and_exact_source_scope():
    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    completion = _completion(context, tool.native_tool_schemas())
    authority = build_native_tool_authority(
        completion,
        role_id=ROLE,
        phase_id="decision-1",
        selected_tool_schemas=tool.native_tool_schemas(),
    )
    assert authority["schema"] == "saea-native-tool-source-authority-v1"
    assert authority["selected_tool_names"] == [LIVE]
    assert authority["selected_tool_schemas_sha256"] == completion.tool_schemas_sha256
    assert authority["original_assistant_message"]["content"] is None
    assert authority["source_request_sha256"] == completion.request_sha256
    assert len(authority["completion_sha256"]) == 64


@pytest.mark.parametrize(
    "field,value",
    [
        ("tool_names", ("foreign",)),
        ("tool_schemas_sha256", "0" * 64),
        ("request_sha256", "short"),
        ("response_text_sha256", "0" * 64),
    ],
)
def test_builder_refuses_changed_completion_identity_or_scope(field, value):
    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    completion = replace(
        _completion(context, tool.native_tool_schemas()), **{field: value}
    )
    with pytest.raises(NativeToolAuthorityError):
        build_native_tool_authority(
            completion,
            role_id=ROLE,
            phase_id="decision-1",
            selected_tool_schemas=tool.native_tool_schemas(),
        )


def test_v2_dispatch_counts_only_after_authority_validation_and_projects_into_empty_scope():
    _tool, _context, _completion, step, payload, messages, texts, counted = (
        _authority_world()
    )
    document = json.loads(step.state.content)
    assert document["schema"] == "saea-phase-tool-result-v2"
    assert document["tool_invocation"]["schema"] == "saea-native-phase-tool-contact-v2"
    assert document["source_authority_sha256"] == content_hash(
        document["source_authority"]
    )
    assert (
        document["tool_invocation"]["source_authority_sha256"]
        == document["source_authority_sha256"]
    )
    assert counted == [{"count": 1}]
    rendered, _ = project_native_history(
        payload=payload, messages=messages, state_texts=texts
    )
    assistant = next(x for x in rendered if x["role"] == "assistant")
    assert (
        assistant == document["source_authority"]["original_assistant_message"]
        and assistant["content"] is None
    )
    assert payload["tool_schemas"] == []


@pytest.mark.parametrize("target", ["authority", "invocation", "call", "content"])
def test_v2_history_refuses_changed_source_authority_call_or_content(target):
    _tool, _context, _completion, _step, payload, messages, texts, _ = (
        _authority_world()
    )
    state = next(x for x in payload["history"] if x.get("state_kind") == "tool-result")
    document = json.loads(state["content"])
    if target == "authority":
        document["source_authority"]["role_id"] = "solver"
    elif target == "invocation":
        document["tool_invocation"]["source_authority_sha256"] = "0" * 64
    elif target == "call":
        document["native_tool_calls_json"] = "[]"
    else:
        document["source_authority"]["original_assistant_message"]["content"] = (
            "changed"
        )
    state["content"] = json.dumps(document, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    with pytest.raises(FrozenCoreError):
        project_native_history(payload=payload, messages=messages, state_texts=texts)


def test_runtime_refuses_changed_authority_before_counting():
    tool, context, completion, _step, _payload, _messages, _texts, _ = (
        _authority_world()
    )
    authority = build_native_tool_authority(
        completion,
        role_id=ROLE,
        phase_id="decision-1",
        selected_tool_schemas=tool.native_tool_schemas(),
    )
    authority["sample_id"] = "foreign"
    counted = []
    runtime = SimpleNamespace(
        _samples=[SimpleNamespace(sample_id=context.sample_id)],
        _live_speech_source_bindings={
            context.sample_id: {
                "packet_id": context.query_state.speech_packet_id,
                "packet_sha256": context.query_state.speech_packet_sha256,
            }
        },
        _client=SimpleNamespace(record_tool_call=lambda **facts: counted.append(facts)),
        assert_generation_lease=lambda: None,
        _live_speech_units=lambda: None,
    )
    with pytest.raises(FlightRuntimeError):
        FlightRuntime._record_phase_tool_contact(
            runtime,
            sample_id=context.sample_id,
            phase="decision-1",
            next_phase="decision-2",
            tool_id=LIVE,
            arguments=json.loads(call()[0]["function"]["arguments"]),
            source_response_sha256=completion.response_text_sha256,
            request_id=completion.request_id,
            tool_call_id="call-1",
            tool_calls_sha256=completion.tool_calls_sha256,
            source_authority=authority,
            source_authority_role=ROLE,
        )
    assert counted == []


def test_legacy_projection_and_document_bytes_are_unchanged():
    payload, messages, texts = world()
    state = next(x for x in payload["history"] if x.get("state_kind") == "tool-result")
    before = state["content"]
    result, descriptors = project(payload, copy.deepcopy(messages), texts)
    assert (
        json.loads(state["content"])["schema"] == "saea-phase-tool-result-v1"
        and state["content"] == before
    )
    assert result[2]["content"] is None and descriptors == []


def test_v2_missing_source_authority_does_not_fall_back():
    _tool, _context, _completion, _step, payload, messages, texts, _ = (
        _authority_world()
    )
    state = next(
        item for item in payload["history"] if item.get("state_kind") == "tool-result"
    )
    document = json.loads(state["content"])
    document.pop("source_authority")
    state["content"] = json.dumps(document, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    with pytest.raises(FrozenCoreError):
        project_native_history(payload=payload, messages=messages, state_texts=texts)


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(schema="foreign"),
        lambda value: value.update(role_id=""),
        lambda value: value.update(source_request_sha256="bad"),
        lambda value: value.update(selected_tool_names=["foreign"]),
        lambda value: value["original_assistant_message"].update(role="user"),
        lambda value: value["original_assistant_message"].pop("tool_calls"),
        lambda value: value["original_assistant_message"]["tool_calls"][0][
            "function"
        ].update(name="foreign"),
        lambda value: value.update(original_assistant_message_sha256="0" * 64),
        lambda value: value.update(completion_sha256="0" * 64),
    ],
)
def test_authority_document_validation_refuses_changed_fields(change):
    from speech_aware_evidence_acquisition.rails.native_tool_authority import (
        validate_native_tool_authority,
    )

    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    authority = build_native_tool_authority(
        _completion(context, tool.native_tool_schemas()),
        role_id=ROLE,
        phase_id="decision-1",
        selected_tool_schemas=tool.native_tool_schemas(),
    )
    change(authority)
    with pytest.raises(NativeToolAuthorityError):
        validate_native_tool_authority(authority)


@pytest.mark.parametrize(
    "change", ["wrong-type", "empty-role", "missing-contact", "missing-wire", "stop"]
)
def test_builder_requires_real_bound_tool_completion(change):
    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    completion = _completion(context, tool.native_tool_schemas())
    role = ROLE
    if change == "wrong-type":
        completion = object()
    elif change == "empty-role":
        role = ""
    elif change == "missing-contact":
        completion = replace(completion, agent_contact_id=None)
    elif change == "missing-wire":
        completion = replace(completion, wire_response_bytes=None)
    else:
        wire = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": call(),
                        },
                        "finish_reason": "stop",
                    }
                ]
            }
        ).encode()
        completion = replace(completion, wire_response_bytes=wire)
    with pytest.raises(NativeToolAuthorityError):
        build_native_tool_authority(
            completion,
            role_id=role,
            phase_id="decision-1",
            selected_tool_schemas=tool.native_tool_schemas(),
        )


def test_v2_projection_uses_source_scope_when_solver_scope_is_unrelated():
    _tool, _context, _completion, _step, payload, messages, texts, _ = (
        _authority_world()
    )
    payload["tool_schemas"] = [
        {"type": "function", "function": {"name": "solver-only"}}
    ]
    rendered, _ = project_native_history(
        payload=payload, messages=messages, state_texts=texts
    )
    assert (
        next(item for item in rendered if item["role"] == "assistant")["tool_calls"][0][
            "function"
        ]["name"]
        == LIVE
    )


def test_dispatch_selects_actual_narrowed_schema_and_preserves_structured_content():
    from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL

    tool = dispatcher(
        LIVE, TASK_CONTRACT_TOOL, provider=LiveProvider(), authority_role=ROLE
    )
    context = staged_native(call())
    registered = tool.native_tool_schemas()
    selected = tuple(
        schema for schema in registered if schema["function"]["name"] == LIVE
    )
    structured = [{"type": "text", "text": "I need the speech observation."}]
    completion = _completion(context, selected, content=structured)
    context = SimpleNamespace(**{**context.__dict__, "core_completions": (completion,)})
    counted = []
    runtime = SimpleNamespace(
        _samples=[SimpleNamespace(sample_id=context.sample_id)],
        _live_speech_source_bindings={
            context.sample_id: {
                "packet_id": context.query_state.speech_packet_id,
                "packet_sha256": context.query_state.speech_packet_sha256,
            }
        },
        _client=SimpleNamespace(record_tool_call=lambda **facts: counted.append(facts)),
        assert_generation_lease=lambda: None,
        _live_speech_units=lambda: None,
    )
    tool.tool_contact = lambda **facts: FlightRuntime._record_phase_tool_contact(
        runtime, **facts
    )
    step = tool("decision-1", "decision-2", context)
    document = json.loads(step.state.content)
    authority = document["source_authority"]
    assert [schema["function"]["name"] for schema in registered] == [
        LIVE,
        TASK_CONTRACT_TOOL,
    ]
    assert authority["selected_tool_names"] == [LIVE]
    assert authority["selected_tool_schemas"] == list(selected)
    assert authority["original_assistant_message"]["content"] == structured
    assert counted == [{"count": 1}]

    from speech_aware_evidence_acquisition.core.model.transport import (
        _speech_history_texts,
    )
    from speech_aware_evidence_acquisition.rails.core_client import _agent_history

    states = (*context.agent_states, step.state)
    history = _agent_history(
        agent_state=[state.as_json() for state in states],
        agent_contact_id="solver",
        contact_instruction="Deliver the final task JSON.",
    )
    state_texts = _speech_history_texts(history)
    query_descriptor = {
        "packet_id": context.query_state.speech_packet_id,
        "sha256": context.query_state.speech_packet_sha256,
        "role": "query",
    }
    payload = {
        "sample_id": context.sample_id,
        "speech_feature_parts": [query_descriptor],
        "history": history,
        "tool_schemas": [],
        "decoding_params": {"tool_choice": "none", "parallel_tool_calls": False},
        "supplied_evidence": [],
    }
    messages = [
        {"role": "system", "content": "Solve."},
        {
            "role": "user",
            "content": [
                {"type": "input_speech_features", "speech_features": query_descriptor},
                *({"type": "text", "text": text} for text in state_texts),
            ],
        },
    ]
    rendered, _ = project_native_history(
        payload=payload, messages=messages, state_texts=state_texts
    )
    projected = next(item for item in rendered if item["role"] == "assistant")
    assert projected["content"] == structured
    assert projected["tool_calls"][0]["function"]["name"] == LIVE


def test_persisted_authority_requires_tool_calls_finish_reason():
    from speech_aware_evidence_acquisition.rails.native_tool_authority import (
        validate_native_tool_authority,
    )

    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    authority = build_native_tool_authority(
        _completion(context, tool.native_tool_schemas()),
        role_id=ROLE,
        phase_id="decision-1",
        selected_tool_schemas=tool.native_tool_schemas(),
    )
    authority["source_finish_reason"] = "stop"
    with pytest.raises(NativeToolAuthorityError, match="finish reason"):
        validate_native_tool_authority(authority)


@pytest.mark.parametrize(
    "names",
    [(), ("missing",), (LIVE, LIVE)],
)
def test_registered_schema_selection_rejects_missing_unknown_or_repeated_names(names):
    from speech_aware_evidence_acquisition.rails.native_tool_authority import (
        select_completion_tool_schemas,
    )

    tool = dispatcher(LIVE, provider=LiveProvider())
    context = staged_native(call())
    completion = replace(
        _completion(context, tool.native_tool_schemas()), tool_names=names
    )
    with pytest.raises(NativeToolAuthorityError):
        select_completion_tool_schemas(completion, tool.native_tool_schemas())
