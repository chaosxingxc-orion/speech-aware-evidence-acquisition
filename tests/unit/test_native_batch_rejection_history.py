"""Native history preserves one complete rejected multi-call source group."""

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    framework_contact_instruction,
    native_tool_result_message,
    project_native_framework_history,
)
from speech_aware_evidence_acquisition.core.model.native_history import (
    project_native_history,
)
from speech_aware_evidence_acquisition.core.model.transport import _speech_history_texts
from speech_aware_evidence_acquisition.rails import native_tool_authority
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_native_tool_authority import _authority_world


def _rejection_world():
    _tool, context, _completion, step, payload, messages, _texts, _counted = (
        _authority_world()
    )
    template = json.loads(step.state.content)
    calls = json.loads(template["native_tool_calls_json"])
    second = copy.deepcopy(calls[0])
    second["id"] = "call-2"
    calls.append(second)
    raw_calls = json.dumps(
        calls, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    calls_sha256 = hashlib.sha256(raw_calls.encode()).hexdigest()
    assistant = copy.deepcopy(
        template["source_authority"]["original_assistant_message"]
    )
    assistant["tool_calls"] = copy.deepcopy(calls)

    authority = copy.deepcopy(template["source_authority"])
    authority["original_assistant_message"] = assistant
    authority["original_assistant_message_sha256"] = content_hash(assistant)
    authority["source_tool_calls_sha256"] = calls_sha256
    authority["role_id"] = authority["phase_id"]
    authority["completion_sha256"] = content_hash(
        native_tool_authority._completion_identity(authority)
    )
    authority_sha256 = content_hash(authority)

    result = native_tool_authority.multiple_call_rejection_result(2)
    documents = []
    states = []
    for index, call in enumerate(calls, 1):
        document = copy.deepcopy(template)
        document.update(
            schema="saea-phase-tool-rejection-v1",
            native_tool_calls_json=raw_calls,
            tool_calls_sha256=calls_sha256,
            tool_call_id=call["id"],
            tool_id=call["function"]["name"],
            arguments=json.loads(call["function"]["arguments"]),
            next_phase=template["phase"],
            source_authority=copy.deepcopy(authority),
            source_authority_sha256=authority_sha256,
            result=copy.deepcopy(result),
            result_sha256=content_hash(result),
            native_result_content=[],
            native_result_content_sha256=content_hash({"blocks": []}),
        )
        document.pop("tool_invocation")
        content_text = json.dumps(document, sort_keys=True)
        state = step.state.as_json()
        state.update(
            state_id=f"tool-rejection:{index}",
            content=content_text,
            content_sha256=hashlib.sha256(content_text.encode()).hexdigest(),
        )
        documents.append(document)
        states.append(state)

    source = context.agent_states[0].as_json()
    history = _agent_history(
        agent_state=[source, *states],
        agent_contact_id="final",
        contact_instruction="Deliver the final task JSON.",
    )
    payload["history"] = history
    texts = _speech_history_texts(history)
    base = messages[1]["content"][0]
    messages[1]["content"] = [
        base,
        *({"type": "text", "text": value} for value in texts),
    ]
    return context, payload, messages, texts, assistant, documents, states


def _framework_world():
    context, payload, messages, _texts, assistant, documents, states = (
        _rejection_world()
    )
    framework = [
        {"role": "system", "content": "Solve."},
        {"role": "user", "content": "Review the original speech."},
        {**copy.deepcopy(assistant), "content": ""},
        *(native_tool_result_message(document) for document in documents),
    ]
    instruction = framework_contact_instruction(
        role_id="decision-1",
        sample_id=context.sample_id,
        contact_id="final",
        messages=framework,
        local_tool_result_ids=tuple(state["state_id"] for state in states),
    )
    source = next(
        state
        for state in payload["history"]
        if state.get("state_kind", "").startswith("phase:")
    )
    history = _agent_history(
        agent_state=[source, *states],
        agent_contact_id="final",
        contact_instruction=instruction,
    )
    payload.update(history=history, task_instruction="Solve.")
    texts = _speech_history_texts(history)
    base = messages[1]["content"][0]
    messages[1]["content"] = [
        base,
        *({"type": "text", "text": value} for value in texts),
    ]
    return payload, messages, texts, framework


def test_inherited_history_projects_one_assistant_and_all_rejections():
    _context, payload, messages, texts, assistant, documents, _states = (
        _rejection_world()
    )
    before = copy.deepcopy((payload, messages))
    rendered, descriptors = project_native_history(
        payload=payload,
        messages=messages,
        state_texts=texts,
    )
    assert [row["role"] for row in rendered] == [
        "system",
        "user",
        "assistant",
        "tool",
        "tool",
        "user",
    ]
    assert rendered[2] == assistant
    assert [row["tool_call_id"] for row in rendered[3:5]] == ["call-1", "call-2"]
    assert [json.loads(row["content"])["result"] for row in rendered[3:5]] == [
        document["result"] for document in documents
    ]
    assert descriptors == []
    assert (payload, messages) == before


def test_framework_history_accepts_complete_ordered_rejection_group():
    payload, messages, texts, framework = _framework_world()
    before = copy.deepcopy((payload, messages))
    rendered, descriptors = project_native_framework_history(
        payload=payload,
        messages=messages,
        state_texts=texts,
    )
    assert [row["role"] for row in rendered] == [
        "system",
        "user",
        "assistant",
        "tool",
        "tool",
    ]
    assert rendered[2]["content"] is None
    assert rendered[2]["tool_calls"] == framework[2]["tool_calls"]
    assert rendered[3:] == framework[3:]
    assert descriptors == []
    assert (payload, messages) == before


@pytest.mark.parametrize(
    "change",
    [
        "omitted",
        "reordered",
        "duplicate",
        "mixed",
        "interposed",
        "empty-framework",
    ],
)
def test_framework_history_refuses_incomplete_or_mixed_source_group(change):
    payload, messages, _texts, _framework = _framework_world()
    control = json.loads(payload["history"][-1]["content"])
    rejection_ids = control["local_tool_result_ids"]
    if change == "empty-framework":
        control["messages"] = []
    elif change == "omitted":
        control["local_tool_result_ids"] = rejection_ids[:1]
        control["messages"] = control["messages"][:-1]
    elif change == "reordered":
        control["local_tool_result_ids"] = list(reversed(rejection_ids))
        control["messages"][-2:] = reversed(control["messages"][-2:])
    elif change == "duplicate":
        control["local_tool_result_ids"] = [rejection_ids[0], rejection_ids[0]]
    elif change == "mixed":
        state = next(
            item
            for item in payload["history"]
            if item.get("state_id") == rejection_ids[1]
        )
        document = json.loads(state["content"])
        document["schema"] = "saea-phase-tool-result-v2"
        state["content"] = json.dumps(document, sort_keys=True)
        state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    else:
        source_index = next(
            index
            for index, item in enumerate(payload["history"])
            if item.get("state_kind", "").startswith("phase:")
        )
        unrelated = copy.deepcopy(payload["history"][source_index])
        unrelated["state_id"] = "unrelated-state"
        payload["history"].insert(source_index + 1, unrelated)
    control_content = json.dumps(control, sort_keys=True)
    payload["history"][-1].update(
        content=control_content,
        content_sha256=hashlib.sha256(control_content.encode()).hexdigest(),
    )
    texts = _speech_history_texts(payload["history"])
    messages[1]["content"] = [
        messages[1]["content"][0],
        *({"type": "text", "text": value} for value in texts),
    ]
    with pytest.raises(FrozenCoreError):
        project_native_framework_history(
            payload=payload,
            messages=messages,
            state_texts=texts,
        )


@pytest.mark.parametrize("change", ["omitted", "reordered", "duplicate", "mixed"])
def test_inherited_history_refuses_incomplete_or_changed_source_group(change):
    _context, payload, messages, _texts, _assistant, _documents, states = (
        _rejection_world()
    )
    first_id, second_id = (state["state_id"] for state in states)
    history = payload["history"]
    if change == "omitted":
        payload["history"] = [
            item for item in history if item.get("state_id") != second_id
        ]
    elif change == "reordered":
        positions = {item.get("state_id"): index for index, item in enumerate(history)}
        first_index, second_index = positions[first_id], positions[second_id]
        history[first_index], history[second_index] = (
            history[second_index],
            history[first_index],
        )
    else:
        state = next(item for item in history if item.get("state_id") == second_id)
        document = json.loads(state["content"])
        if change == "duplicate":
            document["tool_call_id"] = "call-1"
        else:
            document["schema"] = "saea-phase-tool-result-v2"
        state["content"] = json.dumps(document, sort_keys=True)
        state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    texts = _speech_history_texts(payload["history"])
    messages[1]["content"] = [
        messages[1]["content"][0],
        *({"type": "text", "text": value} for value in texts),
    ]
    with pytest.raises(FrozenCoreError):
        project_native_history(
            payload=payload,
            messages=messages,
            state_texts=texts,
        )


@pytest.mark.parametrize("missing_field", ["phase", "speech_packet_id"])
def test_success_result_missing_required_custody_field_fails_closed(
    missing_field,
):
    _tool, _context, _completion, _step, payload, messages, texts, _counted = (
        _authority_world()
    )
    state = next(
        item for item in payload["history"] if item.get("state_kind") == "tool-result"
    )
    document = json.loads(state["content"])
    document.pop(missing_field)
    state["content"] = json.dumps(document, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    with pytest.raises(FrozenCoreError):
        project_native_history(
            payload=payload,
            messages=messages,
            state_texts=texts,
        )
