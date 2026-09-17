from __future__ import annotations

import copy
import base64
import hashlib
import json

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


def _finite_fixture(*, with_solver: bool, finish_reason: str = "length"):
    """Build a finite stop whose interrupted contact remains source evidence."""
    policy, phase_result, output, trace = _fixture()
    phase_result = copy.deepcopy(phase_result)
    episode = phase_result["native_episode_receipt"]
    visits = episode["role_visits"]
    interrupted_visit = visits[2] if with_solver else visits[1]
    completed_visits = visits[:2] if with_solver else visits[:1]
    interrupted_execution = copy.deepcopy(interrupted_visit["execution_receipt"])
    rejected_contact = interrupted_execution["final_contact"]
    rejected_request_id = rejected_contact["request_id"]
    rejected_text = trace[f"{rejected_request_id}/response"]["text"]
    usage = trace[f"{rejected_request_id}/response"]["usage"]
    trace[f"{rejected_request_id}/request"]["payload"]["decoding_params"] = {
        "max_tokens": 8,
    }
    wire_document = {
        "choices": [{
            "message": {"content": rejected_text},
            "finish_reason": finish_reason,
        }],
        "usage": usage,
    }
    raw_wire = json.dumps(wire_document).encode()
    trace[f"{rejected_request_id}/wire-response"] = {
        "request_id": rejected_request_id,
        "sample_id": "s1",
        "finish_reason": finish_reason,
        "response_b64": base64.b64encode(raw_wire).decode(),
        "response_sha256": hashlib.sha256(raw_wire).hexdigest(),
    }
    episode.clear()
    episode.update({
        "role_visits": completed_visits,
        "planner_routes": [],
        "interrupted_role": {
            "role_id": interrupted_visit["role_id"],
            "stage": interrupted_visit["stage"],
            "execution_receipt": interrupted_execution,
        },
        "terminal_disposition": {
            "reason": "finite_completion",
            "finish_reason": finish_reason,
            "role_id": interrupted_visit["role_id"],
            "stage": interrupted_visit["stage"],
            "revision_count": 0,
            "planner_accepted": False,
            "rejected_contact": rejected_contact,
        },
    })
    completed_contact_count = sum(
        len(visit["execution_receipt"]["contacts"]) for visit in completed_visits
    )
    phase_result["contacts"] = phase_result["contacts"][:
        completed_contact_count + len(interrupted_execution["contacts"])
    ]
    if with_solver:
        solver_receipt = copy.deepcopy(completed_visits[-1]["execution_receipt"])
        episode["terminal_solver_receipt"] = solver_receipt
        final_text = trace[f"{solver_receipt['final_contact']['request_id']}/response"]["text"]
    else:
        episode["abstention_receipt"] = {"source_contact": rejected_contact}
        final_text = ""
        from speech_aware_evidence_acquisition.core.delivery import native_abstention_records

        derived_id, request_document, response_document = native_abstention_records(
            sample_id="s1",
            source_contact=rejected_contact,
            finish_reason=finish_reason,
        )
        trace[f"{derived_id}/request"] = request_document
        trace[f"{derived_id}/response"] = response_document
        for suffix in ("runtime-use", "posthoc-use"):
            trace.pop(f"s1/{policy}/agent-loop/{suffix}")
    phase_result["final_response_text"] = final_text
    phase_result["final_response_sha256"] = _sha(final_text)
    output = {
        "sample_id": "s1",
        "text": final_text,
        "native_episode_receipt": episode,
    }
    if not with_solver:
        output.update(
            request_id=derived_id, request_sha256=request_document["payload_sha256"],
            response_sha256=response_document["response_sha256"],
            response_text_sha256=response_document["response_text_sha256"],
        )
        trace = {
            key: value for key, value in trace.items()
            if "/reviewer/tool-" not in key
        }
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
        "illegal_route_count": 0,
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


def test_accepted_delivery_rejects_a_conflicting_terminal_disposition():
    policy, phase_result, output, trace = _fixture()
    phase_result["native_episode_receipt"]["terminal_disposition"] = {
        "reason": "revision_limit", "planner_action": "REVISE",
        "revision_count": 0, "planner_accepted": False,
    }
    with pytest.raises(NativeEpisodeDiagnosticError, match="must not carry"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",), controller_policy_id=policy,
            phase_results={"s1": phase_result}, output_rows={"s1": output},
            trace_records=trace,
        )


@pytest.mark.parametrize("finish_reason", ["length", "content_filter"])
def test_finite_stop_flattens_interrupted_contacts_without_completing_the_visit(
    finish_reason,
):
    policy, phase_result, output, trace = _finite_fixture(
        with_solver=True, finish_reason=finish_reason,
    )
    delivery = validate_native_episode_delivery_receipt(
        phase_result["native_episode_receipt"],
        error_type=NativeEpisodeDiagnosticError,
    )
    assert delivery.kind == "finite"

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",), controller_policy_id=policy,
        phase_results={"s1": phase_result}, output_rows={"s1": output},
        trace_records=trace,
    )

    assert result["model_contacts"]["count"] == 4
    assert result["model_contacts"]["by_role"] == {
        "perception": 1, "reviewer": 2, "solver": 1,
    }
    assert result["planner"]["route_count"] == 0
    assert result["finite_stops"] == {
        "count": 1,
        "solver_delivery_count": 1,
        "abstention_count": 0,
        "by_finish_reason": {finish_reason: 1},
        "by_role": {"reviewer": 1},
        "by_stage": {"review": 1},
    }
    sample = result["samples"][0]
    assert sample["finite_solver"]["request_id"] == "request-solver-1"
    assert sample["finite_disposition"] == {
        "reason": "finite_completion",
        "finish_reason": finish_reason,
        "role_id": "reviewer",
        "stage": "review",
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": phase_result["native_episode_receipt"]
        ["interrupted_role"]["execution_receipt"]["final_contact"],
    }
    interrupted = [
        row for row in sample["model_contacts"] if row.get("interrupted") is True
    ]
    assert len(interrupted) == 2
    assert interrupted[-1]["completion"]["stop_reason"] == finish_reason
    assert result["native_tool_events"]["contacted_call_count"] == 1


def test_finite_stop_without_solver_validates_deterministic_empty_abstention():
    policy, phase_result, output, trace = _finite_fixture(with_solver=False)
    episode = phase_result["native_episode_receipt"]
    delivery = validate_native_episode_delivery_receipt(
        episode, error_type=NativeEpisodeDiagnosticError,
    )
    assert delivery.kind == "abstention"
    assert delivery.solver_receipt is None
    assert delivery.final_contact == episode["terminal_disposition"]["rejected_contact"]

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",), controller_policy_id=policy,
        phase_results={"s1": phase_result}, output_rows={"s1": output},
        trace_records=trace,
    )

    assert output["text"] == ""
    assert result["model_contacts"]["count"] == 2
    assert result["finite_stops"]["solver_delivery_count"] == 0
    assert result["finite_stops"]["abstention_count"] == 1
    sample = result["samples"][0]
    assert "finite_solver" not in sample
    assert sample["abstention"]["delivered_solver"] is False
    assert sample["abstention"]["source_request_id"] == "request-solver-1"
    assert sample["abstention"]["completion"]["metadata_available"] is False
    assert "no Solver response was delivered" in (
        sample["abstention"]["completion"]["missing_reason"]
    )
    assert result["model_contacts"]["final_completion_cap"] == {
        "contact_count": 1,
        "metadata_available_count": 0,
        "metadata_unavailable_count": 1,
        "completion_tokens_available_count": 0,
        "at_cap_count": 0,
        "at_cap_unknown_count": 1,
        "length_stop_count": 0,
        "length_stop_unknown_count": 1,
    }


def test_abstention_rejects_a_trace_derivative_that_differs_from_shared_builder():
    policy, phase_result, output, trace = _finite_fixture(with_solver=False)
    derived_response = next(
        key for key in trace
        if key.endswith("/response") and "native-abstention" in key
    )
    trace[derived_response] = {**trace[derived_response], "text": "partial source text"}

    with pytest.raises(NativeEpisodeDiagnosticError, match="abstention derivative"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",), controller_policy_id=policy,
            phase_results={"s1": phase_result}, output_rows={"s1": output},
            trace_records=trace,
        )


def test_finite_stop_rejects_wire_reason_not_bound_to_disposition():
    policy, phase_result, output, trace = _finite_fixture(with_solver=True)
    interrupted = phase_result["native_episode_receipt"]["interrupted_role"]
    request_id = interrupted["execution_receipt"]["final_contact"]["request_id"]
    trace[f"{request_id}/wire-response"]["finish_reason"] = "content_filter"

    with pytest.raises(NativeEpisodeDiagnosticError, match="wire finish reason"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",), controller_policy_id=policy,
            phase_results={"s1": phase_result}, output_rows={"s1": output},
            trace_records=trace,
        )


def test_finite_stop_rejects_finite_metadata_before_interrupted_final_contact():
    policy, phase_result, output, trace = _finite_fixture(with_solver=True)
    trace["request-reviewer-1/wire-response"] = {"finish_reason": "length"}

    with pytest.raises(NativeEpisodeDiagnosticError, match="only the interrupted role final"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",), controller_policy_id=policy,
            phase_results={"s1": phase_result}, output_rows={"s1": output},
            trace_records=trace,
        )


@pytest.mark.parametrize("planner_text", [
    '{"action":"REVISE"}',
    ' { "action" : "REVISE" }\n',
])
def test_terminal_json_planner_uses_validated_raw_control(planner_text):
    policy, phase_result, output, trace = _terminal_fixture(planner_text=planner_text)
    episode = phase_result["native_episode_receipt"]
    episode.update(plan=planner_text, planner_control={"action": "REVISE"})

    result = analyze_verified_native_episode_statistics(
        sample_ids=("s1",), controller_policy_id=policy,
        phase_results={"s1": phase_result}, output_rows={"s1": output},
        trace_records=trace,
    )

    assert result["terminal_stops"]["by_planner_action"] == {"REVISE": 1}
    assert result["samples"][0]["terminal_disposition"]["planner_accepted"] is False
    assert trace["request-planner-1/response"]["text"] == planner_text


@pytest.mark.parametrize("mutation", ["missing-control", "wrong-action", "stale-raw-plan", "duplicate-key"])
def test_terminal_json_planner_rejects_broken_control_custody(mutation):
    raw = '{"action":"REVISE"}'
    if mutation == "duplicate-key":
        raw = '{"action":"REVISE","action":"REVISE"}'
    policy, phase_result, output, trace = _terminal_fixture(planner_text=raw)
    episode = phase_result["native_episode_receipt"]
    if mutation != "missing-control":
        episode.update(plan=raw, planner_control={"action": "REVISE"})
    if mutation == "wrong-action":
        episode["planner_control"]["action"] = "ACCEPT"
    if mutation == "stale-raw-plan":
        episode["plan"] = '{ "action": "REVISE" }'

    with pytest.raises(NativeEpisodeDiagnosticError, match="Planner"):
        analyze_verified_native_episode_statistics(
            sample_ids=("s1",), controller_policy_id=policy,
            phase_results={"s1": phase_result}, output_rows={"s1": output},
            trace_records=trace,
        )
