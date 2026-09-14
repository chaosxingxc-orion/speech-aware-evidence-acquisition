"""Synthetic custody tests for finite native episode outcomes."""

import copy
import hashlib

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_native_episode_delivery_receipt,
    validate_native_episode_finite_path,
    validate_native_episode_terminal_policy,
)


def contact(name):
    digest = hashlib.sha256(name.encode()).hexdigest()
    return dict(agent_contact_id=name, request_id=name, request_sha256=digest,
                response_sha256=digest, response_text_sha256=digest)


def visit(stage):
    c = contact(stage)
    return dict(role_id=stage, stage=stage,
                execution_receipt=dict(contacts=[c], final_contact=c))


def finite_receipt(stages, interrupted):
    rejected = contact("interrupted")
    row = dict(role_visits=[visit(s) for s in stages], planner_routes=[],
        interrupted_role=dict(role_id=interrupted, stage=interrupted,
            execution_receipt=dict(contacts=[rejected], final_contact=rejected)),
        terminal_disposition=dict(reason="finite_completion", finish_reason="length",
            role_id=interrupted, stage=interrupted, revision_count=0,
            planner_accepted=False, rejected_contact=rejected))
    if "solver" in stages:
        row["terminal_solver_receipt"] = row["role_visits"][stages.index("solver")]["execution_receipt"]
    else:
        row["abstention_receipt"] = dict(source_contact=rejected)
    return row


@pytest.mark.parametrize("stages,interrupted,kind", [
    ([], "perception", "abstention"),
    (["perception"], "solver", "abstention"),
    (["perception", "solver"], "review", "finite"),
    (["perception", "solver", "review"], "planner", "finite"),
])
def test_finite_delivery_preserves_complete_prefix(stages, interrupted, kind):
    row = finite_receipt(stages, interrupted)
    delivery = validate_native_episode_delivery_receipt(row)
    assert delivery.kind == kind
    assert validate_native_episode_finite_path(
        row, max_revisions=1, accept_action="ACCEPT", revise_action="REVISE"
    ) == 0
    validate_native_episode_terminal_policy(
        delivery, exhaustion_policy="raise", finite_completion_policy="deliver-latest-or-abstain",
        max_revisions=1,
    )
    with pytest.raises(ValueError, match="configured"):
        validate_native_episode_terminal_policy(
            delivery, exhaustion_policy="raise", finite_completion_policy="raise",
            max_revisions=1,
        )


@pytest.mark.parametrize("mutation", ["partial_solver", "fake_route", "wrong_stage", "wrong_contact", "unknown_finish"])
def test_finite_receipt_rejects_forged_terminal_authority(mutation):
    row = finite_receipt(["perception", "solver"], "review")
    if mutation == "partial_solver":
        row["terminal_solver_receipt"] = row["interrupted_role"]["execution_receipt"]
    elif mutation == "fake_route":
        row["planner_routes"] = [dict(action="ACCEPT", role_visit_index=1, revision_count=0)]
    elif mutation == "wrong_stage":
        row["terminal_disposition"]["stage"] = "planner"
    elif mutation == "wrong_contact":
        row["terminal_disposition"]["rejected_contact"] = contact("other")
    else:
        row["terminal_disposition"]["finish_reason"] = "server_error"
    with pytest.raises(ValueError):
        validate_native_episode_delivery_receipt(row)
        validate_native_episode_finite_path(
            row, max_revisions=1, accept_action="ACCEPT", revise_action="REVISE"
        )


def test_abstention_cannot_discard_an_existing_complete_solver():
    row = finite_receipt(["perception", "solver"], "review")
    row["abstention_receipt"] = dict(source_contact=row["terminal_disposition"]["rejected_contact"])
    row.pop("terminal_solver_receipt")
    with pytest.raises(ValueError, match="Solver"):
        validate_native_episode_delivery_receipt(row)


def test_refresh_prefix_can_stop_before_a_revised_solver():
    row = finite_receipt(["perception", "solver", "review", "planner"], "perception")
    row["planner_routes"] = [dict(action="REFRESH", role_visit_index=3, revision_count=0)]
    row["terminal_disposition"]["revision_count"] = 1
    assert validate_native_episode_finite_path(
        row, max_revisions=1, accept_action="ACCEPT", revise_action="REVISE",
        refresh_action="REFRESH", max_refreshes=1,
    ) == 0
    changed = copy.deepcopy(row)
    changed["terminal_disposition"]["revision_count"] = 0
    with pytest.raises(ValueError, match="revision"):
        validate_native_episode_finite_path(
            changed, max_revisions=1, accept_action="ACCEPT", revise_action="REVISE",
            refresh_action="REFRESH", max_refreshes=1,
        )


def test_abstention_uses_separate_immutable_derived_identity():
    from speech_aware_evidence_acquisition.core.delivery import native_abstention_records
    from speech_aware_evidence_acquisition.core.bundle.outputs import (
        _minimum_model_calls_from_trace, _verify_outputs_trace_binding,
    )
    raw = contact("source")
    original = copy.deepcopy(raw)
    request_id, request, response = native_abstention_records(
        sample_id="sample", source_contact=raw, finish_reason="length",
    )
    assert raw == original
    assert request_id != raw["request_id"] and response["text"] == ""
    assert response["response_text_sha256"] != raw["response_text_sha256"]
    trace = {
        "source/request": {"arm": "speech", "payload": {}, "payload_sha256": raw["request_sha256"]},
        "source/response": {"text": "quarantined", "response_sha256": raw["response_sha256"]},
        request_id + "/request": request, request_id + "/response": response,
    }
    row = dict(request_id=request_id, text="", request_sha256=request["payload_sha256"],
               response_sha256=response["response_sha256"],
               response_text_sha256=response["response_text_sha256"])
    _verify_outputs_trace_binding((row,), trace)
    assert _minimum_model_calls_from_trace(trace) == 1
    changed = dict(row, text="forged")
    from speech_aware_evidence_acquisition.core.bundle import BundleError
    with pytest.raises(BundleError):
        _verify_outputs_trace_binding((changed,), trace)
