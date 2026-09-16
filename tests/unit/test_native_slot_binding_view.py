"""Wire projection preserves canonical custody while labeling derived content."""

import copy
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model import native_slot_binding_view as module
from test_native_evidence_projection import document, world


@pytest.fixture
def context(monkeypatch):
    context = SimpleNamespace(policy_id=module.POLICY_ID, context_sha256="b" * 64,
                              value_ids=("value:alpha",))
    monkeypatch.setattr(module, "_validate_context", lambda value: None)
    monkeypatch.setattr(module, "_scope_for_payload", lambda payload, value: {
        "eligible": True, "candidate_ids": ["a"], "fallback_reason": None,
        "source_states": [{"content_sha256": "c" * 64}],
    })
    def project(value, *, evidence_id, source_uri, content, scope):
        if evidence_id not in value.value_ids:
            return content, None
        if not scope["eligible"]:
            return content, {"disposition": "retained", "reason": "nonconsumer"}
        return "Retained global rules and role A.", {
            "disposition": "projected",
            "selected_binding_addresses": ["intent_bindings/0"],
            "excluded_binding_addresses": ["intent_bindings/1"],
        }
    monkeypatch.setattr(module, "_project_slot_value", project)
    return context


@pytest.mark.parametrize("speech", ["input_audio", "input_speech_features"])
def test_base_and_tool_have_explicit_views_without_mutating_source(context, speech):
    payload, messages, results = world(document(), speech=speech)
    original = copy.deepcopy((payload, messages, results))
    rendered, receipt = module.project_native_slot_binding_view(
        payload=payload, messages=messages, local_results=results,
        projection_context=context,
    )
    assert rendered[1]["content"][0] == messages[1]["content"][0]
    assert "derived knowledge view" in rendered[1]["content"][1]["text"]
    assert "Retained global rules and role A." in rendered[1]["content"][1]["text"]
    tool = json.loads(rendered[3]["content"])
    assert tool["result"] == json.loads(messages[3]["content"])["result"]
    assert tool["evidence"][0]["evidence_id"] == "value:alpha"
    assert "content" not in tool["evidence"][0]
    view = tool["evidence"][0]["derived_view"]
    assert view["content"] == "Retained global rules and role A."
    assert view["source_content_sha256"]
    assert rendered[2] == messages[2]
    assert rendered[3]["tool_call_id"] == messages[3]["tool_call_id"]
    assert (payload, messages, results) == original
    assert receipt["projected_occurrences"] == 2
    assert receipt["context_sha256"] == context.context_sha256
    assert len(receipt["local_tool_messages"]) == 1


def test_nonconsumer_and_fallback_keep_bytes_exact(context, monkeypatch):
    payload, messages, results = world()
    monkeypatch.setattr(module, "_scope_for_payload", lambda *args: {
        "eligible": False, "candidate_ids": [], "fallback_reason": "nonconsumer",
    })
    rendered, receipt = module.project_native_slot_binding_view(
        payload=payload, messages=messages, local_results=results,
        projection_context=context,
    )
    assert rendered == messages
    assert receipt["projected_occurrences"] == 0


def test_changed_local_tool_custody_is_refused(context):
    payload, messages, results = world()
    messages[-1]["content"] = "{}"
    with pytest.raises(FrozenCoreError):
        module.project_native_slot_binding_view(
            payload=payload, messages=messages, local_results=results,
            projection_context=context,
        )


def test_observation_and_unrelated_text_remain_full(context):
    payload, messages, results = world(document(knowledge=False))
    messages[1]["content"][1]["text"] = "unrelated text"
    rendered, receipt = module.project_native_slot_binding_view(
        payload=payload, messages=messages, local_results=results,
        projection_context=context,
    )
    assert rendered == messages
    assert receipt["projected_occurrences"] == 0


def test_two_evidence_origins_with_same_text_are_not_conflated(context):
    payload, messages, results = world()
    payload["supplied_evidence"].append({
        **payload["supplied_evidence"][0], "source_uri": "knowledge://different",
    })
    with pytest.raises(FrozenCoreError, match="ambiguous"):
        module.project_native_slot_binding_view(
            payload=payload, messages=messages, local_results=results,
            projection_context=context,
        )
