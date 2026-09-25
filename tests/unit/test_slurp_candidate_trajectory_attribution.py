"""Whole-trajectory diagnostics preserve candidate reach and terminal failures."""
import copy
import pytest

from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import (
    candidate_recovery_view, candidate_recovery_summary,
)


def trajectory(*, prepared=False, unreached=False):
    proposal = {
        "original_candidate_ids": ["alarm_remove"],
        "candidate_ids": ["alarm_remove", "alarm_set"],
        "selected_exemplars": [{"task_target": "alarm_set"}, {"task_target": "alarm_remove"}],
    }
    block = {
        "proposals": {} if unreached else {"a"*64: proposal},
        "contacts": [] if prepared or unreached else [
            {"role_kind": role, "proposal_sha256": "a"*64}
            for role in ("solver", "reviewer", "planner", "solver", "reviewer", "planner")
        ],
        "prepared_without_response": [{"request_id": "r"}] if prepared else [],
    }
    return {"candidate_proposal": {"receipt": block, "receipt_sha256": "b"*64}}


def view(label, correct=False):
    return {"predicted_intent": label, "format_ok": label is not None,
            "task_exact": correct, "intent_correct": correct}


def test_candidate_supply_tracks_revision_and_delivery_without_claiming_causality():
    result = candidate_recovery_view(
        trajectory(), gold_intent="alarm_set", first=view("alarm_remove"),
        last=view("alarm_set", True), delivered=view("alarm_remove"))
    assert result["status"] == "supplied"
    assert result["coverage_group"] == "newly_covered"
    assert result["original_covered"] is False and result["proposed_covered"] is True
    assert result["selection_origin"] == {"first": "original", "last": "added", "delivered": "original"}
    assert result["contact_counts_by_role"] == {"solver": 2, "reviewer": 2, "planner": 2}
    assert result["selected_exemplar_target_counts"] == {"alarm_remove": 1, "alarm_set": 1}
    assert "semantic_use" not in result


@pytest.mark.parametrize("label,expected", [(None, "malformed"), ("weather_query", "outside")])
def test_legal_answer_space_is_not_mistaken_for_a_hard_candidate_filter(label, expected):
    result = candidate_recovery_view(
        trajectory(), gold_intent="alarm_set", first=None, last=None, delivered=view(label))
    assert result["selection_origin"]["first"] == "unavailable"
    assert result["selection_origin"]["delivered"] == expected


def test_unreached_prepared_only_and_legacy_are_distinct():
    kwargs = dict(gold_intent="alarm_set", first=None, last=None, delivered=view(None))
    assert candidate_recovery_view({}, **kwargs) is None
    unreached = candidate_recovery_view(trajectory(unreached=True), **kwargs)
    prepared = candidate_recovery_view(trajectory(prepared=True), **kwargs)
    assert unreached["status"] == "not_reached" and unreached["proposed_covered"] is None
    assert unreached["selection_origin"]["delivered"] == "proposal_unavailable"
    assert prepared["status"] == "prepared_without_response" and prepared["proposed_covered"]
    assert not prepared["contact_counts_by_role"]


def test_full_population_summary_separates_local_coverage_and_retained_task_repairs():
    rows = []
    for sid, stage in (("a", "supplied"), ("b", "unreached"), ("c", "prepared")):
        projection = candidate_recovery_view(
            trajectory(unreached=stage=="unreached", prepared=stage=="prepared"),
            gold_intent="alarm_set", first=view("alarm_remove"), last=view("alarm_set", True),
            delivered=view("alarm_remove"))
        rows.append({"sample_id": sid, "scenario": "alarm", "candidate_recovery": projection,
                     "solver_visits": 2 if stage=="supplied" else 0,
                     "delivered": view("alarm_remove"),
                     "revision_task_transition": "repair" if stage=="supplied" else "unavailable"})
    result = candidate_recovery_summary(rows)
    assert result["rows"] == 3 and result["supplied_rows"] == 1
    assert result["proposed_covered_rows"] == 2
    assert result["supplied_proposed_covered_rows"] == 1
    assert result["coverage_groups"]["newly_covered"]["rows"] == 2
    assert result["coverage_groups"]["not_reached"]["rows"] == 1
    assert result["coverage_groups"]["newly_covered"]["task_repairs_lost"] == 1
    assert result["coverage_groups"]["newly_covered"]["task_repairs_retained"] == 0
    assert result["coverage_groups"]["newly_covered"]["final_task_exact_rows"] == 0
    assert result["per_scenario"]["alarm"]["rows"] == 3
    assert "not counterfactual" in result["interpretation"]


def test_mixed_missing_projection_refuses_instead_of_dropping_failure_rows():
    assert candidate_recovery_summary([{"sample_id": "old"}]) is None
    good = {"sample_id": "a", "candidate_recovery": {}, "scenario": "alarm"}
    with pytest.raises(ValueError, match="every"):
        candidate_recovery_summary([good, {"sample_id": "b", "scenario": "alarm"}])
    with pytest.raises(ValueError, match="unique"):
        candidate_recovery_summary([good, copy.deepcopy(good)])
