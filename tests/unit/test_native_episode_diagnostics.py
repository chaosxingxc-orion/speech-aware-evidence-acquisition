from __future__ import annotations

import copy
import hashlib

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_diagnostics import (
    NativeEpisodeDiagnosticError,
    analyze_verified_native_episode_statistics,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_native_episode_delivery_receipt,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _fixture():
    sample_id = "s1"
    policy = "native-policy"
    trace = {}
    phase_contacts = []

    def contact(role: str, index: int, text: str, *, ceiling: bool = True, supplied=None):
        request_id = f"request-{role}-{index}"
        agent_id = f"{policy}:{role}:{index}:{sample_id}"
        request_hash = _sha(f"request:{request_id}")
        response_hash = _sha(f"response:{request_id}")
        payload = {
            "request_id": request_id,
            "sample_id": sample_id,
            "history": [],
        }
        if ceiling:
            payload["decoding_params"] = {"max_tokens": 8}
        if supplied is not None:
            payload["supplied_evidence"] = supplied
        text_hash = _sha(text)
        trace[f"{request_id}/request"] = {
            "payload": payload,
            "payload_sha256": request_hash,
        }
        trace[f"{request_id}/response"] = {
            "text": text,
            "response_sha256": response_hash,
            "response_text_sha256": text_hash,
            "usage": {"completion_tokens": 8 if role == "solver" else 2},
        }
        trace[f"{request_id}/native-role-contact"] = {
            "use_role_id": role,
            "use_agent_contact_id": agent_id,
            "use_request_sha256": request_hash,
            "use_response_sha256": response_hash,
            "use_response_text_sha256": text_hash,
        }
        receipt = {
            "agent_contact_id": agent_id,
            "request_id": request_id,
            "request_sha256": request_hash,
            "response_sha256": response_hash,
            "response_text_sha256": text_hash,
        }
        phase_contacts.append({
            "plan": {"contact_id": agent_id},
            "response_sha256": text_hash,
        })
        return receipt

    perception = contact("perception", 1, "perception", supplied=[])
    solver = contact(
        "solver", 1, '{"answer":"accepted"}',
        supplied=[
            {"evidence_id": "slot-card-1", "knowledge_role": "value"},
            {"evidence_id": "slot-card-2", "knowledge_role": "value"},
        ],
    )
    reviewer_first = contact("reviewer", 1, "tool call", supplied=[])
    reviewer_final = contact("reviewer", 2, "review complete", ceiling=False)
    planner = contact("planner", 1, "ACCEPT", supplied=[])

    def visit(role, stage, contacts):
        return {
            "role_id": role,
            "stage": stage,
            "execution_receipt": {
                "contacts": contacts,
                "final_contact": contacts[-1],
            },
        }

    episode = {
        "role_visits": [
            visit("perception", "perception", [perception]),
            visit("solver", "solver", [solver]),
            visit("reviewer", "review", [reviewer_first, reviewer_final]),
            visit("planner", "planner", [planner]),
        ],
        "planner_routes": [
            {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"}
        ],
        "accepted_solver_receipt": {
            "contacts": [solver],
            "final_contact": solver,
        },
    }
    tool_suffix = content_hash({
        "request_id": reviewer_first["request_id"],
        "tool_call_id": "call-1",
    })
    tool_base = f"{sample_id}/{policy}/reviewer"
    common_tool = {
        "use_sample_id": sample_id,
        "use_phase": "reviewer",
        "use_tool_id": "task-contract",
        "use_core_request_id": reviewer_first["request_id"],
        "use_tool_call_id": "call-1",
    }
    trace[f"{tool_base}/tool-attempt/{tool_suffix}"] = dict(common_tool)
    trace[f"{tool_base}/tool-result/{tool_suffix}"] = {
        **common_tool,
        "use_tool_invocation": {
            "schema": "saea-native-phase-tool-contact-v2",
            "sample_id": sample_id,
            "phase": "reviewer",
            "next_phase": "reviewer",
            "tool_id": "task-contract",
            "request_id": reviewer_first["request_id"],
            "tool_call_id": "call-1",
        },
    }
    final_text = '{"answer":"accepted"}'
    consumption = {
        "records": [
            {"span_id": "final", "supplied_item_id": "slot-card-1", "outcome": "copy", "evidence": "one"},
            {"span_id": "final", "supplied_item_id": "slot-card-2", "outcome": "use", "evidence": "two"},
            {"span_id": "final", "supplied_item_id": "slot-card-3", "outcome": "ignore", "evidence": "three"},
        ],
        "copy_rate": 1 / 3,
        "dose_realized": 2,
        "trace_version": "consumption-trace-v1",
    }
    runtime_hash = "9" * 64
    trace[f"{sample_id}/{policy}/agent-loop/runtime-use"] = {
        "use_runtime_trace_sha256": runtime_hash,
        "use_final_response_sha256": _sha(final_text),
    }
    trace[f"{sample_id}/{policy}/agent-loop/posthoc-use"] = {
        "use_runtime_trace_sha256": runtime_hash,
        "use_final_response_sha256": _sha(final_text),
        "use_consumption": consumption,
    }
    phase_result = {
        "sample_id": sample_id,
        "final_response_text": final_text,
        "final_response_sha256": _sha(final_text),
        "contacts": phase_contacts,
        "consumption": consumption,
        "native_episode_receipt": episode,
    }
    output = {
        "sample_id": sample_id,
        "text": final_text,
        "native_episode_receipt": episode,
    }
    return policy, phase_result, output, trace


def _terminal_fixture(*, planner_text: str = "REVISE"):
    """Turn the synthetic accepted episode into an honest terminal delivery."""
    policy, phase_result, output, trace = _fixture()
    phase_result = copy.deepcopy(phase_result)
    episode = phase_result["native_episode_receipt"]
    planner = episode["role_visits"][-1]["execution_receipt"]
    planner_contact = planner["final_contact"]
    request_id = planner_contact["request_id"]
    response_sha256 = _sha(f"response:{request_id}:terminal:{planner_text}")
    response_text_sha256 = _sha(planner_text)
    trace[f"{request_id}/response"].update({
        "text": planner_text,
        "response_sha256": response_sha256,
        "response_text_sha256": response_text_sha256,
    })
    trace[f"{request_id}/native-role-contact"].update({
        "use_response_sha256": response_sha256,
        "use_response_text_sha256": response_text_sha256,
    })
    for contact in planner["contacts"]:
        contact.update({
            "response_sha256": response_sha256,
            "response_text_sha256": response_text_sha256,
        })
    planner_contact.update({
        "response_sha256": response_sha256,
        "response_text_sha256": response_text_sha256,
    })
    phase_result["contacts"][-1]["response_sha256"] = response_text_sha256
    route = episode["planner_routes"][-1]
    route["action"] = "REVISE"
    episode.pop("accepted_solver_receipt")
    episode["terminal_solver_receipt"] = copy.deepcopy(
        episode["role_visits"][1]["execution_receipt"]
    )
    episode["terminal_disposition"] = {
        "reason": "revision_limit",
        "planner_action": "REVISE",
        "revision_count": 0,
        "planner_accepted": False,
    }
    output = {**output, "native_episode_receipt": episode}
    return policy, phase_result, output, trace


def test_counts_react_contacts_by_role_and_preserves_accepted_solver_custody():
    policy, phase_result, output, trace = _fixture()

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",),
        controller_policy_id=policy,
        phase_results={"s1": phase_result},
        output_rows={"s1": output},
        trace_records=trace,
    )

    assert result["model_contacts"]["count"] == 5
    assert result["model_contacts"]["by_role"] == {
        "perception": 1,
        "planner": 1,
        "reviewer": 2,
        "solver": 1,
    }
    assert result["samples"][0]["accepted_solver"]["request_id"] == "request-solver-1"
    assert result["planner"] == {
        "route_count": 1,
        "action_counts": {"ACCEPT": 1},
        "revision_count_histogram": {"0": 1},
    }
    assert result["native_tool_events"]["by_axis_and_event"]["analytical"] == {
        "attempt": 1,
        "failed": 0,
        "rejected": 0,
        "result": 1,
    }
    assert result["native_tool_events"]["contacted_call_count"] == 1
    assert result["knowledge"]["supply"]["supplied_value_occurrences"] == 2
    assert result["knowledge"]["lexical_consumption"]["outcome_counts"] == {
        "copy": 1,
        "use": 1,
        "ignore": 1,
    }


def test_missing_optional_metadata_stays_unknown():
    policy, phase_result, output, trace = _fixture()

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",),
        controller_policy_id=policy,
        phase_results={"s1": phase_result},
        output_rows={"s1": output},
        trace_records=trace,
    )

    reviewer = result["model_contacts"]["role_completion_cap"]["reviewer"]
    assert reviewer["contact_count"] == 2
    assert reviewer["metadata_unavailable_count"] == 1
    assert reviewer["at_cap_unknown_count"] == 1
    assert result["knowledge"]["supply"]["contacts_without_metadata"] == 1
    assert result["model_contacts"]["final_completion_cap"]["at_cap_count"] == 1
    assert result["model_contacts"]["final_completion_cap"]["length_stop_unknown_count"] == 1


def test_rejects_an_accepted_solver_receipt_not_equal_to_a_solver_visit():
    policy, phase_result, output, trace = _fixture()
    episode = dict(phase_result["native_episode_receipt"])
    episode["accepted_solver_receipt"] = {
        "contacts": [episode["role_visits"][0]["execution_receipt"]["final_contact"]],
        "final_contact": episode["role_visits"][0]["execution_receipt"]["final_contact"],
    }
    phase_result = {**phase_result, "native_episode_receipt": episode}
    output = {**output, "native_episode_receipt": episode}

    with pytest.raises(NativeEpisodeDiagnosticError, match="exact last Solver visit"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",),
            controller_policy_id=policy,
            phase_results={"s1": phase_result},
            output_rows={"s1": output},
            trace_records=trace,
        )


def test_counts_opt_in_terminal_delivery_separately_without_an_accepted_solver():
    policy, phase_result, output, trace = _terminal_fixture()
    # Full graph state retains its initialized null accepted field.  It is not
    # an acceptance and must not make the terminal delivery ambiguous.
    phase_result["native_episode_receipt"]["accepted_solver_receipt"] = None
    output = {
        **output,
        "native_episode_receipt": phase_result["native_episode_receipt"],
    }
    delivery = validate_native_episode_delivery_receipt(
        phase_result["native_episode_receipt"],
        terminal_actions=("REVISE", "ACQUIRE"),
        error_type=NativeEpisodeDiagnosticError,
    )
    assert delivery.kind == "terminal"

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",),
        controller_policy_id=policy,
        phase_results={"s1": phase_result},
        output_rows={"s1": output},
        trace_records=trace,
    )

    assert result["terminal_stops"] == {
        "count": 1,
        "by_planner_action": {"REVISE": 1},
        "by_revision_count": {"0": 1},
    }
    assert "accepted_solver" not in result["samples"][0]
    assert result["samples"][0]["terminal_disposition"] == {
        "reason": "revision_limit",
        "planner_action": "REVISE",
        "revision_count": 0,
        "planner_accepted": False,
    }


def test_rejects_terminal_disposition_that_does_not_match_the_planner_response():
    policy, phase_result, output, trace = _terminal_fixture(planner_text="ACCEPT")

    with pytest.raises(NativeEpisodeDiagnosticError, match="Planner response"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",),
            controller_policy_id=policy,
            phase_results={"s1": phase_result},
            output_rows={"s1": output},
            trace_records=trace,
        )


def test_rejects_ambiguous_accepted_and_terminal_delivery_receipts():
    policy, phase_result, output, trace = _terminal_fixture()
    episode = phase_result["native_episode_receipt"]
    episode["accepted_solver_receipt"] = copy.deepcopy(episode["terminal_solver_receipt"])
    output = {**output, "native_episode_receipt": episode}

    with pytest.raises(NativeEpisodeDiagnosticError, match="exactly one delivery receipt"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",),
            controller_policy_id=policy,
            phase_results={"s1": phase_result},
            output_rows={"s1": output},
            trace_records=trace,
        )
