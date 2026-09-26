"""Bounded views keep complete system events and expose every omission."""

import copy
import json

import pytest

from speech_aware_evidence_acquisition.analysis.system_event_view import (
    project_system_events,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def episode():
    tool = {
        "schema": "saea-phase-tool-result-v2",
        "tool_id": "lookup",
        "arguments": {"key": "date"},
        "result": {"text": "Do not invent dates."},
        "source_authority": {"custody": "large"},
        "new_observation": "retain me",
    }
    return {
        "source_episode_sha256": "a" * 64,
        "contacts": [
            {
                "role_id": "reviewer",
                "interrupted": True,
                "recorded_request": {
                    "supplied_evidence": [{"content": "Full intent and slot guidance"}],
                    "history": [
                        {
                            "role": "agent_state",
                            "state_kind": "phase:solver",
                            "content": "raw draft",
                        },
                        {
                            "role": "agent_state",
                            "state_kind": "tool-result",
                            "content": json.dumps(tool),
                        },
                        {
                            "role": "control",
                            "content": json.dumps(
                                {
                                    "messages": [
                                        {
                                            "role": "user",
                                            "content": "Review independently",
                                        }
                                    ]
                                }
                            ),
                        },
                    ],
                },
                "response_record": {
                    "text": "A claim, not an invocation",
                    "usage": {"completion_tokens": 7},
                },
                "wire_response_utf8": json.dumps(
                    {
                        "choices": [
                            {"finish_reason": "length", "message": {"content": "raw"}}
                        ],
                        "timings": {"ms": 1},
                    }
                ),
            }
        ],
        "actual_tool_records": [
            {
                "record_id": "actual-tool",
                "record": {
                    "use_result": tool["result"],
                    "use_arguments": tool["arguments"],
                    "use_source_authority": tool["source_authority"],
                    "use_new_observation": "retain me",
                },
            }
        ],
        "timeline_record_ids": ["request", "response", "actual-tool"],
        "control_receipt": {"planner_routes": [{"action": "ACCEPT"}]},
        "delivered_text": "",
        "delivery": {"kind": "abstention"},
    }


def test_all_contacts_tools_supply_control_and_terminal_events_are_retained():
    original = episode()
    before = copy.deepcopy(original)
    view = project_system_events(original)
    assert original == before
    assert view["source_projection_sha256"] == content_hash(original)
    contact = view["contacts"][0]
    assert (
        contact["recorded_request"]["supplied_evidence"]
        == original["contacts"][0]["recorded_request"]["supplied_evidence"]
    )
    assert contact["response_record"] == original["contacts"][0]["response_record"]
    assert contact["interrupted"]
    history = contact["recorded_request"]["history"]
    assert history[0]["content"] == "raw draft"
    assert history[1]["content_view"]["document"]["result"] == {
        "text": "Do not invent dates."
    }
    assert history[1]["content_view"]["document"]["new_observation"] == "retain me"
    assert history[1]["content_view"]["omitted_fields"] == ["source_authority"]
    assert (
        history[2]["content_view"]["document"]["messages"][0]["content"]
        == "Review independently"
    )
    wire = contact["wire_response_view"]
    assert wire["document"]["choices"][0]["finish_reason"] == "length"
    assert wire["omitted_fields"] == ["timings"]
    tool = view["actual_tool_records"][0]
    assert tool["record"]["use_result"] == {"text": "Do not invent dates."}
    assert tool["record"]["use_new_observation"] == "retain me"
    assert tool["omitted_fields"] == ["use_source_authority"]
    for field in (
        "control_receipt",
        "timeline_record_ids",
        "delivery",
        "delivered_text",
    ):
        assert view[field] == original[field]


@pytest.mark.parametrize(
    "raw", ["not JSON", '{"x":1,"x":2}', '{"x":NaN}', "null", "[1,2]"]
)
def test_malformed_or_nonobject_json_is_retained_literally(raw):
    source = episode()
    source["contacts"][0]["wire_response_utf8"] = raw
    source["contacts"][0]["recorded_request"]["history"][1]["content"] = raw
    view = project_system_events(source)
    contact = view["contacts"][0]
    assert contact["wire_response_utf8"] == raw
    assert contact["recorded_request"]["history"][1]["content"] == raw


def test_missing_wire_and_plain_history_survive_without_inventing_events():
    source = episode()
    source["contacts"][0]["wire_response_utf8"] = None
    source["contacts"][0]["recorded_request"]["history"] = [{"content": "legacy state"}]
    source["actual_tool_records"] = []
    view = project_system_events(source)
    assert view["contacts"][0]["wire_response_utf8"] is None
    assert view["contacts"][0]["recorded_request"]["history"] == [
        {"content": "legacy state"}
    ]
    assert view["actual_tool_records"] == []
