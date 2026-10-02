"""Recover completed streamed items without accepting deltas as final output."""
import copy
import pytest

from speech_aware_evidence_acquisition.rails.system_proposer_responses import completed_stream_output
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def stream():
    item = {"id": "msg_one", "type": "message", "status": "completed", "role": "assistant",
            "content": [{"type": "output_text", "text": "Synthetic complete answer"}]}
    return [
        {"type": "response.created", "response": {"id": "resp_one"}},
        {"type": "response.output_item.added", "output_index": 0, "item": {**item, "status": "in_progress", "content": []}},
        {"type": "response.output_item.done", "output_index": 0, "item": item},
        {"type": "response.completed", "response": {"id": "resp_one", "status": "completed", "output": [], "usage": {"input_tokens": 220, "output_tokens": 10}}},
    ]


def test_complete_stream_reconciles_omitted_aggregate_without_mutation():
    events = stream()
    saved = copy.deepcopy(events)
    result = completed_stream_output(events[-1]["response"], events, subscription=True)
    assert result["output"] == [events[2]["item"]]
    assert result["usage"]["output_tokens"] == 10
    assert events == saved


@pytest.mark.parametrize("case", ["no_created", "wrong_response", "no_added", "no_done", "duplicate", "wrong_item", "gap", "unfinished", "aggregate_conflict"])
def test_reconciliation_requires_complete_single_response_custody(case):
    events = stream()
    if case == "no_created": events.pop(0)
    elif case == "wrong_response": events[-1]["response"]["id"] = "resp_other"
    elif case == "no_added": events.pop(1)
    elif case == "no_done": events.pop(2)
    elif case == "duplicate": events.insert(3, copy.deepcopy(events[2]))
    elif case == "wrong_item": events[2]["item"]["id"] = "msg_other"
    elif case == "gap": events[1]["output_index"] = events[2]["output_index"] = 1
    elif case == "unfinished": events[2]["item"]["status"] = "in_progress"
    else: events[-1]["response"]["output"] = [{"different": True}]
    with pytest.raises(PolicyError):
        completed_stream_output(events[-1]["response"], events, subscription=True)


def test_hard_profile_cannot_reconstruct_empty_aggregate():
    events = stream()
    with pytest.raises(PolicyError):
        completed_stream_output(events[-1]["response"], events, subscription=False)


def reasoning_stream():
    events = stream()
    for event in events:
        if "output_index" in event:
            event["output_index"] = 1
    reasoning = {"id": "rs_one", "type": "reasoning", "summary": [],
                 "content": [], "encrypted_content": "synthetic-opaque-state"}
    events[1:1] = [
        {"type": "response.output_item.added", "output_index": 0, "item": copy.deepcopy(reasoning)},
        {"type": "response.output_item.done", "output_index": 0, "item": copy.deepcopy(reasoning)},
    ]
    return events


def test_completed_reasoning_without_optional_status_keeps_opaque_state():
    events = reasoning_stream()
    original = copy.deepcopy(events)
    result = completed_stream_output(events[-1]["response"], events, subscription=True)
    assert result["output"] == [events[2]["item"], events[4]["item"]]
    assert "status" not in result["output"][0]
    assert events == original


@pytest.mark.parametrize("case", ["reasoning_in_progress", "reasoning_incomplete", "reasoning_null", "message_missing_status", "type_changed", "done_before_created"])
def test_optional_reasoning_status_does_not_relax_item_custody(case):
    events = reasoning_stream()
    if case == "reasoning_in_progress": events[2]["item"]["status"] = "in_progress"
    elif case == "reasoning_incomplete": events[2]["item"]["status"] = "incomplete"
    elif case == "reasoning_null": events[2]["item"]["status"] = None
    elif case == "message_missing_status": del events[4]["item"]["status"]
    elif case == "type_changed": events[2]["item"]["type"] = "message"; events[2]["item"]["status"] = "completed"
    else: events.insert(3, events.pop(0))
    with pytest.raises(PolicyError):
        completed_stream_output(events[-1]["response"], events, subscription=True)
