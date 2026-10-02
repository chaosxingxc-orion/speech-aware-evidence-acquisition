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
