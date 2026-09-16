"""Source-bound knowledge references preserve actual information and tool custody."""

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    native_tool_result_message,
    project_native_framework_history,
)
from speech_aware_evidence_acquisition.core.model.native_evidence_projection import (
    POLICY_ID,
    project_native_knowledge_references,
)


def document(*, text="Use the full semantic contract.", evidence_id="value:alpha",
             snapshot="a" * 64, call_id="lookup-1", knowledge=True):
    uri = f"knowledge-snapshot://{snapshot}/{evidence_id}"
    block = {"type": "text", "evidence_id": evidence_id, "source_uri": uri,
             "text": text, "knowledge_role": "value"}
    result = {"knowledge_view": "text", "selected_value_ids": [evidence_id],
              "supply_disposition": "already-visible"}
    if not knowledge:
        result = {"evidence_id": evidence_id, "source_uri": uri}
    return {"snapshot_sha256": snapshot, "tool_call_id": call_id,
            "result": result, "native_result_content": [block]}


def world(doc=None, *, visible=True, speech="input_speech_features"):
    doc = doc or document()
    block = doc["native_result_content"][0]
    evidence = {"evidence_id": block["evidence_id"], "source_uri": block["source_uri"],
                "content": block["text"]}
    parts = [{"type": speech, "opaque": "unchanged-speech"}]
    if visible:
        parts.append({"type": "text", "text": f"[evidence {block['evidence_id']}] {block['text']}"})
    messages = [
        {"role": "system", "content": "Review the evidence."},
        {"role": "user", "content": parts},
        {"role": "assistant", "content": None, "tool_calls": [{"id": doc["tool_call_id"]}]},
        native_tool_result_message(doc),
    ]
    return {"supplied_evidence": [evidence]}, messages, ((3, doc),)


def project(payload, messages, results):
    return project_native_knowledge_references(
        payload=payload, messages=messages, local_results=results,
    )


@pytest.mark.parametrize("speech", ["input_speech_features", "input_audio"])
def test_visible_knowledge_is_referenced_and_custody_is_unchanged(speech):
    payload, messages, results = world(speech=speech)
    original = copy.deepcopy((payload, messages, results))
    rendered, receipt = project(payload, messages, results)
    tool = json.loads(rendered[3]["content"])
    entry = tool["evidence"][0]
    assert "content" not in entry
    assert entry["reference"]["message_index"] == 1
    assert entry["reference"]["content_sha256"] == hashlib.sha256(
        results[0][1]["native_result_content"][0]["text"].encode()
    ).hexdigest()
    assert tool["result"] == results[0][1]["result"]
    assert rendered[:3] == messages[:3]
    assert rendered[3]["tool_call_id"] == messages[3]["tool_call_id"]
    assert (payload, messages, results) == original
    assert receipt["policy_id"] == POLICY_ID
    assert receipt["referenced_blocks"] == 1
    assert receipt["retained_blocks"] == 0
    assert receipt["source_messages_sha256"] != receipt["projected_messages_sha256"]
    assert receipt["placements"][0]["source_document_sha256"]


def test_state_visibility_flag_without_a_visible_body_does_not_create_reference():
    payload, messages, results = world(visible=False)
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["retained_blocks"] == 1
    assert receipt["referenced_blocks"] == 0


def test_new_evidence_is_retained_and_later_repeat_refers_to_actual_prior_body():
    first = document(call_id="lookup-1")
    payload, messages, results = world(first, visible=False)
    second = document(call_id="lookup-2")
    messages.extend([{"role": "assistant", "content": None, "tool_calls": [{"id": "lookup-2"}]},
                     native_tool_result_message(second)])
    rendered, receipt = project(payload, messages, results + ((5, second),))
    assert json.loads(rendered[3]["content"])["evidence"][0]["content"] == first["native_result_content"][0]["text"]
    later = json.loads(rendered[5]["content"])["evidence"][0]
    assert later["reference"]["message_index"] == 3
    assert later["reference"]["evidence_index"] == 0
    assert receipt["retained_blocks"] == receipt["referenced_blocks"] == 1
    assert [m.get("tool_call_id") for m in rendered if m["role"] == "tool"] == ["lookup-1", "lookup-2"]


def test_prior_validated_tool_body_can_supply_reference():
    first = document(call_id="prior-call")
    payload, messages, _ = world(first, visible=False)
    second = document(call_id="local-call")
    messages.extend([{"role": "assistant", "content": None}, native_tool_result_message(second)])
    rendered, receipt = project(payload, messages, ((5, second),))
    assert rendered[:5] == messages[:5]
    assert json.loads(rendered[5]["content"])["evidence"][0]["reference"]["message_index"] == 3
    assert receipt["referenced_blocks"] == 1


@pytest.mark.parametrize("change", ["source", "id"])
def test_equal_text_with_distinct_identity_is_not_merged(change):
    doc = document()
    payload, messages, results = world(doc)
    item = payload["supplied_evidence"][0]
    if change == "source":
        item["source_uri"] = "knowledge-snapshot://" + "b" * 64 + "/value:alpha"
    else:
        item["evidence_id"] = "value:other"
        messages[1]["content"][1]["text"] = f"[evidence value:other] {item['content']}"
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["referenced_blocks"] == 0


def test_conflicting_content_for_same_source_identity_refuses():
    payload, messages, results = world()
    payload["supplied_evidence"][0]["content"] = "Conflicting content."
    messages[1]["content"][1]["text"] = "[evidence value:alpha] Conflicting content."
    with pytest.raises(FrozenCoreError, match="conflict"):
        project(payload, messages, results)


def test_nonknowledge_observation_remains_full_even_if_text_matches():
    payload, messages, results = world(document(knowledge=False))
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["referenced_blocks"] == 0


def test_no_forward_reference_to_body_after_tool_result():
    payload, messages, results = world()
    part = messages[1]["content"].pop()
    messages.append({"role": "user", "content": [part]})
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["referenced_blocks"] == 0


@pytest.mark.parametrize("change", ["content", "call_id", "role", "index", "duplicate"])
def test_unbound_or_repeated_local_messages_are_refused(change):
    payload, messages, results = world()
    if change == "content":
        messages[3]["content"] = "{}"
    elif change == "call_id":
        messages[3]["tool_call_id"] = "other"
    elif change == "role":
        messages[3]["role"] = "user"
    elif change == "index":
        results = ((100, results[0][1]),)
    else:
        results += results
    with pytest.raises(FrozenCoreError):
        project(payload, messages, results)


def test_rejection_results_and_empty_knowledge_are_preserved():
    payload, messages, results = world()
    doc = {"result": {"status": "rejected", "lookup_performed": False},
           "native_result_content": [], "tool_call_id": "lookup-1"}
    messages[3] = native_tool_result_message(doc)
    rendered, receipt = project(payload, messages, ((3, doc),))
    assert rendered == messages
    assert receipt["placements"] == []


def test_duplicate_reference_uses_visible_full_body_instead_of_reference_chain():
    payload, messages, results = world()
    for n in (2, 3):
        doc = document(call_id=f"lookup-{n}")
        messages.extend([{"role": "assistant", "content": None}, native_tool_result_message(doc)])
        results += ((len(messages) - 1, doc),)
    rendered, receipt = project(payload, messages, results)
    assert receipt["referenced_blocks"] == 3
    assert all(json.loads(rendered[i]["content"])["evidence"][0]["reference"]["message_index"] == 1
               for i in (3, 5, 7))


def test_unrelated_user_text_is_not_a_knowledge_body():
    payload, messages, results = world()
    messages[1]["content"][1]["text"] = "An opinion containing: " + messages[1]["content"][1]["text"]
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["referenced_blocks"] == 0


def test_framework_rejects_opt_in_without_receipt_sink_or_without_native_contract():
    from test_native_framework_history import world as framework_world
    payload, messages, texts, _ = framework_world()
    with pytest.raises(FrozenCoreError, match="receipt"):
        project_native_framework_history(payload=payload, messages=messages,
                                         state_texts=texts, evidence_projection=POLICY_ID)
    with pytest.raises(FrozenCoreError, match="framework"):
        project_native_framework_history(payload={}, messages=[], state_texts=[],
                                         evidence_projection=POLICY_ID, receipt_sink=lambda r: None)


def test_framework_preserves_default_and_records_opt_in_custody():
    from test_native_framework_history import world as framework_world
    payload, messages, texts, _ = framework_world()
    default = project_native_framework_history(payload=payload, messages=messages, state_texts=texts)
    receipts = []
    projected = project_native_framework_history(
        payload=payload, messages=messages, state_texts=texts,
        evidence_projection=POLICY_ID, receipt_sink=receipts.append,
    )
    assert projected == default
    assert len(receipts) == 1
    assert receipts[0]["referenced_blocks"] == 0


def test_ambiguous_base_source_does_not_authorize_reference():
    payload, messages, results = world()
    other = dict(payload["supplied_evidence"][0], source_uri="knowledge://other")
    payload["supplied_evidence"].append(other)
    rendered, receipt = project(payload, messages, results)
    assert rendered == messages
    assert receipt["referenced_blocks"] == 0


@pytest.mark.parametrize("index", [-1, True, "3"])
def test_invalid_local_index_refuses(index):
    payload, messages, results = world()
    with pytest.raises(FrozenCoreError):
        project(payload, messages, ((index, results[0][1]),))


@pytest.mark.parametrize("policy", ["unknown-projection", "", True, {}])
def test_framework_rejects_invalid_policy(policy):
    from test_native_framework_history import world as framework_world
    payload, messages, texts, _ = framework_world()
    with pytest.raises(FrozenCoreError, match="projection"):
        project_native_framework_history(
            payload=payload, messages=messages, state_texts=texts,
            evidence_projection=policy, receipt_sink=lambda r: None,
        )


def test_large_selection_retains_order_and_complete_value_access():
    doc = document()
    doc["native_result_content"] = []
    doc["result"]["selected_value_ids"] = []
    payload = {"supplied_evidence": []}
    parts = [{"type": "input_speech_features", "opaque": "unchanged"}]
    for index in range(21):
        item = document(evidence_id=f"value:{index}", text=f"Contract {index}. " * 150)
        block = item["native_result_content"][0]
        doc["native_result_content"].append(block)
        doc["result"]["selected_value_ids"].append(block["evidence_id"])
        payload["supplied_evidence"].append({
            "evidence_id": block["evidence_id"], "source_uri": block["source_uri"],
            "content": block["text"],
        })
        parts.append({"type": "text", "text": f"[evidence {block['evidence_id']}] {block['text']}"})
    messages = [{"role": "user", "content": parts},
                {"role": "assistant", "content": None},
                native_tool_result_message(doc)]
    rendered, receipt = project(payload, messages, ((2, doc),))
    content = json.loads(rendered[2]["content"])
    assert receipt["referenced_blocks"] == 21
    assert content["result"] == doc["result"]
    assert [entry["evidence_id"] for entry in content["evidence"]] == doc["result"]["selected_value_ids"]
    for entry, block in zip(content["evidence"], doc["native_result_content"], strict=True):
        reference = entry["reference"]
        target = rendered[reference["message_index"]]["content"][reference["content_part_index"]]
        assert target["text"] == f"[evidence {block['evidence_id']}] {block['text']}"
    assert len(rendered[2]["content"].encode()) < len(messages[2]["content"].encode())
