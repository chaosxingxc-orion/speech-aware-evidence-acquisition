"""Framework history must reach the actual speech request exactly once."""

import copy
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    framework_contact_instruction, native_tool_result_message,
    project_native_framework_history,
)
from speech_aware_evidence_acquisition.core.model.transport import _speech_history_texts
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    project_native_assistant_message,
)
from test_native_tool_authority import _authority_world


def world():
    _tool, context, completion, step, payload, messages, _texts, _counted = _authority_world()
    document = json.loads(step.state.content)
    framework = [
        {"role": "system", "content": "Solve."},
        {"role": "user", "content": "Review the original speech."},
        project_native_assistant_message(completion).model_dump(mode="json", exclude_none=True),
        native_tool_result_message(document),
    ]
    instruction = framework_contact_instruction(
        role_id="reviewer", sample_id=context.sample_id, contact_id="final",
        messages=framework, local_tool_result_ids=(step.state.state_id,),
    )
    history = _agent_history(
        agent_state=[s.as_json() for s in (*context.agent_states, step.state)],
        agent_contact_id="final", contact_instruction=instruction,
    )
    payload.update(history=history, task_instruction="Solve.")
    texts = _speech_history_texts(history)
    base = messages[1]["content"][0]
    messages[1]["content"] = [base, *({"type": "text", "text": v} for v in texts)]
    return payload, messages, texts, framework


def test_full_framework_history_restores_null_and_preserves_tool_json_once():
    payload, messages, texts, framework = world()
    original = copy.deepcopy(payload)
    rendered, descriptors = project_native_framework_history(
        payload=payload, messages=messages, state_texts=texts,
    )
    assert [row["role"] for row in rendered] == ["system", "user", "assistant", "tool"]
    assert rendered[1]["content"][-1] == {"type": "text", "text": framework[1]["content"]}
    assert rendered[2]["content"] is None
    assert rendered[2]["tool_calls"] == framework[2]["tool_calls"]
    assert rendered[3] == framework[3]
    assert "agent state" not in json.dumps(rendered)
    assert payload == original
    assert descriptors == []


@pytest.mark.parametrize("change", ["tool_content", "raw_arguments", "system", "missing_pair", "reordered"])
def test_changed_or_dropped_framework_history_is_rejected(change):
    payload, messages, texts, framework = world()
    control = json.loads(payload["history"][-1]["content"])
    if change == "tool_content":
        control["messages"][-1]["content"] = "{}"
    elif change == "raw_arguments":
        control["messages"][-2]["tool_calls"][0]["function"]["arguments"] += " "
    elif change == "system":
        control["messages"][0]["content"] = "Different instructions."
    elif change == "missing_pair":
        control["local_tool_result_ids"] = []
    else:
        control["messages"][-2:] = reversed(control["messages"][-2:])
    import hashlib
    content = json.dumps(control, sort_keys=True)
    payload["history"][-1].update(content=content, content_sha256=hashlib.sha256(content.encode()).hexdigest())
    texts = _speech_history_texts(payload["history"])
    messages[1]["content"][-1] = {"type": "text", "text": texts[-1]}
    with pytest.raises(FrozenCoreError):
        project_native_framework_history(payload=payload, messages=messages, state_texts=texts)


def test_nonframework_control_keeps_legacy_projection_available():
    assert project_native_framework_history(
        payload={"history": [{"role": "control", "content": "Ordinary instruction."}]},
        messages=[], state_texts=[],
    ) is None
