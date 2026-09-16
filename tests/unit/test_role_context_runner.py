"""Synthetic shared-runner integration for typed role-context compilation."""

from __future__ import annotations

import json
import re
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.role_context_binding import (
    validate_role_context_config,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_role_context_binding import DRAFT_SCHEMA, context_spec, perception_format


_DERIVED_STATE = re.compile(
    r"^\[agent state (?P<state_id>.+) "
    r"kind=(?P<state_kind>role-context:[^\]]+)\] (?P<content>.+)$"
)


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _derived_states(body: dict[str, object]) -> list[dict[str, object]]:
    states = []
    for text in _strings(body):
        match = _DERIVED_STATE.fullmatch(text)
        if match is None:
            continue
        document = json.loads(match.group("content"))
        states.append(
            {
                "state_id": match.group("state_id"),
                "state_kind": match.group("state_kind"),
                "content": document,
            }
        )
    return states


def _speech_parts(body: dict[str, object]) -> list[dict[str, object]]:
    parts = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") in {"input_speech_features", "input_audio"}:
                parts.append(value)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(body)
    return parts


def _tool_messages(body: dict[str, object]) -> list[dict[str, object]]:
    return [
        message
        for message in body["messages"]
        if isinstance(message, dict) and message.get("role") == "tool"
    ]


def _configure_typed_context(harness: _ActualEpisodeHarness) -> dict[str, str]:
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, response_format_id="slurp-intent-hypotheses-v1")
            if phase.name == "perception"
            else phase
            for phase in harness.program.phases
        ),
    ).validate()
    canonical = validate_role_context_config(context_spec())
    harness.config = replace(harness.config, role_context_json=canonical)
    original_material = harness.material_for_phase

    def material_for_phase(phase, context, sealed):
        material = original_material(phase, context, sealed)
        if phase == "perception":
            return replace(
                material,
                response_format=perception_format(),
            ).validate()
        return material

    packet_id = harness.speech_bindings["s1"]["packet_id"]
    missing_id = "unavailable:evidence:not-exposed"
    first_draft = {
        "scenario": "alarm",
        "action": "remove",
        "entities": [{"type": "time", "filler": "seven"}],
    }
    revised_draft = {
        "scenario": "alarm",
        "action": "set",
        "entities": [{"type": "time", "filler": "seven"}],
    }
    candidates = {
        "candidates": [
            {
                "intent_id": "alarm_set",
                "distinction": "The command may create an alarm.",
                "evidence_refs": [packet_id],
                "unresolved_fields": ["alarm operation"],
            },
            {
                "intent_id": "alarm_remove",
                "distinction": "The command may remove an alarm.",
                "evidence_refs": [missing_id],
                "unresolved_fields": ["alarm operation"],
            },
        ]
    }
    supported_finding = {
        "schema": "saea-review-findings-v1",
        "verdict": "supported-issue",
        "findings": [
            {
                "dimension": "intent",
                "rationale": "The draft selects removal while setting remains plausible.",
                "evidence_ids": [packet_id, missing_id],
            }
        ],
        "recommendation": "reconsider",
        "remaining_uncertainty": "The speech remains the authority.",
    }
    no_issue = {
        "schema": "saea-review-findings-v1",
        "verdict": "no-supported-issue",
        "findings": [],
        "recommendation": "retain",
        "remaining_uncertainty": "",
    }

    def output(key):
        _sample_id, phase, visit, turn = key
        if harness.reviewer_tool and phase == "reviewer" and visit == turn == 1:
            return None
        if phase == "perception":
            return _json(candidates)
        if phase == "solver":
            return _json(first_draft if visit == 1 else revised_draft)
        if phase == "reviewer":
            return _json(supported_finding if visit == 1 else no_issue)
        if phase == "planner":
            return harness.planner_actions[visit - 1]
        raise AssertionError(phase)

    harness.material_for_phase = material_for_phase
    harness._output = output
    assert json.loads(canonical)["params"]["draft_response_schema"] == DRAFT_SCHEMA
    return {
        "packet_id": packet_id,
        "missing_id": missing_id,
        "first_draft": _json(first_draft),
        "revised_draft": _json(revised_draft),
        "candidates": _json(candidates),
        "supported_finding": _json(supported_finding),
        "no_issue": _json(no_issue),
    }


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_typed_role_context_reaches_actual_requests_without_losing_custody(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    expected = _configure_typed_context(harness)
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    receipt = result.native_episode_receipt
    assert result.final_response_text == expected["revised_draft"]
    assert json.loads(result.final_response_text) == {
        "scenario": "alarm",
        "action": "set",
        "entities": [{"type": "time", "filler": "seven"}],
    }
    assert close_summary["request_count"] == len(result.contacts) == 8
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
        "solver",
        "review",
        "planner",
    ]
    accepted = receipt["accepted_solver_receipt"]["final_contact"]
    assert accepted == harness.traced_contact(accepted["agent_contact_id"])
    assert accepted["response_text_sha256"] == harness.dispatched[
        ("s1", "solver", 2, 1)
    ]["response_text_sha256"]

    for key, prepared in harness.prepared.items():
        assert harness.events.index(("fit", key)) < harness.events.index(
            ("dispatch", key)
        )
        speech = _speech_parts(prepared["rendered"])
        assert len(speech) == 1
        assert speech[0]["type"] == "input_speech_features"
        assert speech[0]["speech_features"]["packet_id"] == expected["packet_id"]

    solver_one = _derived_states(
        harness.prepared[("s1", "solver", 1, 1)]["rendered"]
    )
    assert [state["state_kind"] for state in solver_one] == [
        "role-context:candidate-hypothesis"
    ]
    candidate_context = solver_one[0]["content"]
    assert candidate_context["schema"] == "saea-typed-role-context-state-v1"
    assert candidate_context["semantic_class"] == "candidate-hypothesis"
    assert candidate_context["declaration_status"] == "unverified-model-hypotheses"
    assert [
        candidate["intent_id"]
        for candidate in candidate_context["view"]["candidates"]
    ] == ["alarm_set", "alarm_remove"]
    assert candidate_context["source"] == {
        "state_id": candidate_context["source"]["state_id"],
        "state_kind": "phase:perception",
    }
    assert candidate_context["view"]["evidence_ref_availability"] == [
        {
            "intent_id": "alarm_set",
            "evidence_refs": [
                {"evidence_id": expected["packet_id"], "available": True}
            ],
        },
        {
            "intent_id": "alarm_remove",
            "evidence_refs": [
                {"evidence_id": expected["missing_id"], "available": False}
            ],
        },
    ]

    reviewer_one = _derived_states(
        harness.prepared[("s1", "reviewer", 1, 1)]["rendered"]
    )
    assert {state["state_kind"] for state in reviewer_one} == {
        "role-context:candidate-hypothesis",
        "role-context:current-draft",
    }
    draft_context = next(
        state["content"]
        for state in reviewer_one
        if state["state_kind"] == "role-context:current-draft"
    )
    assert draft_context["view"] == {
        "parsed": json.loads(expected["first_draft"]),
    }

    reviewer_next = harness.prepared[("s1", "reviewer", 1, 2)]["rendered"]
    planner_one = harness.prepared[("s1", "planner", 1, 1)]["rendered"]
    tool_chains = [_tool_messages(body) for body in (reviewer_next, planner_one)]
    assert [len(messages) for messages in tool_chains] == [1, 1]
    for tool_messages in tool_chains:
        assert tool_messages[0]["tool_call_id"] == "call-task-contract-1"
        assert json.loads(tool_messages[0]["content"])["result"] == {
            "task_contract": "task-contract-for-s1"
        }

    planner_states = _derived_states(planner_one)
    planner_draft = next(
        state["content"]
        for state in planner_states
        if state["state_kind"] == "role-context:current-draft"
    )
    assert planner_draft["view"] == {
        "source_state_id": planner_draft["source"]["state_id"],
        "parse_status": "parsed",
    }
    review_context = next(
        state["content"]
        for state in planner_states
        if state["state_kind"] == "role-context:review-finding"
    )
    assert review_context["view"]["report"] == json.loads(
        expected["supported_finding"]
    )
    citation_status = {
        item["evidence_id"]: item["available"]
        for item in review_context["view"]["citation_availability"]
    }
    assert citation_status == {
        expected["packet_id"]: True,
        expected["missing_id"]: False,
    }
    assert expected["missing_id"] not in review_context["source"].values()

    revised_solver = _derived_states(
        harness.prepared[("s1", "solver", 2, 1)]["rendered"]
    )
    assert "role-context:review-finding" in {
        state["state_kind"] for state in revised_solver
    }

    # Compilation changes request views, never the canonical episode ledger.
    raw_contents = {state.content for state in result.agent_states}
    assert expected["candidates"] in raw_contents
    assert expected["first_draft"] in raw_contents
    assert expected["supported_finding"] in raw_contents
    assert expected["revised_draft"] in raw_contents
    assert all(
        not state.state_kind.startswith("role-context:")
        for state in result.agent_states
    )
    assert any(state.state_kind == "tool-result" for state in result.agent_states)

    compilations = receipt["role_context_compilations"]
    assert len(compilations) == len(result.contacts) == 8
    assert len({record["contact_id"] for record in compilations}) == 8
    for record in compilations:
        traced = harness.traced_contact(record["contact_id"])
        assert record["request_sha256"] == traced["request_sha256"]
        assert record["response_sha256"] == traced["response_sha256"]
        assert len(record["context_config_sha256"]) == 64
        assert len(record["perception_response_format_sha256"]) == 64
        compilation = record["compilation"]
        assert compilation["schema"] == "saea-role-context-compilation-v1"
        assert compilation["sample_id"] == "s1"
        assert len(compilation["receipt_sha256"]) == 64
        assert len(compilation["output_state_ids"]) == len(
            set(compilation["output_state_ids"])
        )

    solver_one_contact_id = receipt["role_visits"][1]["execution_receipt"][
        "final_contact"
    ]["agent_contact_id"]
    solver_one_compilation = next(
        record["compilation"]
        for record in compilations
        if record["contact_id"] == solver_one_contact_id
    )
    candidate_retained = next(
        row
        for row in solver_one_compilation["retained"]
        if row["state_kind"] == "role-context:candidate-hypothesis"
    )
    assert len(candidate_retained["projection"]["raw_positions"]) == 2
    assert set(candidate_retained["source"]) == {
        "state_id",
        "state_kind",
        "artifact_sha256",
        "content_sha256",
        "source_response_sha256",
        "source_query_state_sha256",
        "producer_policy_id",
        "source_position",
    }
    raw_candidate = next(
        state
        for state in result.agent_states
        if state.state_id == candidate_retained["source"]["state_id"]
    )
    assert candidate_retained["source"]["artifact_sha256"] == raw_candidate.content_hash()
    assert (
        candidate_retained["source"]["source_response_sha256"]
        == raw_candidate.source_response_sha256
    )
    assert raw_candidate.source_response_sha256 == harness.dispatched[
        ("s1", "perception", 1, 1)
    ]["response_text_sha256"]

    planner_contact_id = receipt["role_visits"][3]["execution_receipt"][
        "final_contact"
    ]["agent_contact_id"]
    planner_compilation = next(
        record["compilation"]
        for record in compilations
        if record["contact_id"] == planner_contact_id
    )
    assert expected["packet_id"] in planner_compilation["available_evidence_ids"]
    assert expected["missing_id"] not in planner_compilation["available_evidence_ids"]

    org_records = [
        (record_id, payload)
        for channel, record_id, payload in harness.trace.records
        if channel == "ORG" and record_id.endswith("/role-context")
    ]
    assert len(org_records) == len(compilations)
    assert [payload["org_role_context"] for _, payload in org_records] == compilations


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_default_native_episode_request_and_receipt_remain_unchanged(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    assert result.final_response_text == "solver-answer:s1:visit:1"
    assert close_summary["request_count"] == len(result.contacts) == 4
    assert set(result.native_episode_receipt) == {
        "role_visits",
        "planner_routes",
        "accepted_solver_receipt",
    }
    assert all(
        "saea-typed-role-context-state-v1"
        not in json.dumps(prepared["rendered"], sort_keys=True)
        for prepared in harness.prepared.values()
    )
    assert not [
        record_id
        for channel, record_id, _payload in harness.trace.records
        if channel == "ORG" and record_id.endswith("/role-context")
    ]
    for key in harness.prepared:
        assert harness.events.index(("fit", key)) < harness.events.index(
            ("dispatch", key)
        )
        assert len(_speech_parts(harness.prepared[key]["rendered"])) == 1
