"""Strict intermediate diagnostics are separate from official terminal scores."""
import json
from types import SimpleNamespace

from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import (
    answer_view, describe_changes, summarize_rows,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity


def answer(label="set", entities=()):
    return json.dumps({"scenario": "alarm", "action": label,
                      "entities": [{"type": t, "filler": v} for t, v in entities]})


def gold(entities=()):
    return SimpleNamespace(scenario="alarm", action="set",
                           entities=tuple(SlotEntity(*item) for item in entities))


def test_intermediate_revision_and_delivery_changes_are_separate():
    target = gold([("time", "six")])
    first = answer_view(answer("remove"), target)
    last = answer_view(answer(entities=[("time", "Six")]), target)
    delivered = answer_view(answer(entities=[("time", "six")]), target)
    row = describe_changes(first, last, delivered)
    assert row["revision_intent_transition"] == "repair"
    assert row["revision_task_transition"] == "unchanged_wrong"
    assert row["delivery_task_transition"] == "repair"
    assert row["end_to_end_task_transition"] == "repair"


def test_new_harm_and_empty_entity_false_positive_are_preserved():
    target = gold()
    correct = answer_view(answer(), target)
    wrong = answer_view(answer(entities=[("time", "six")]), target)
    assert correct["task_exact"] and not wrong["task_exact"]
    assert wrong["empty_target_emission"] and wrong["entity_fp"] == 1
    assert describe_changes(correct, wrong, wrong)["revision_task_transition"] == "harm"


def test_absent_solver_is_unknown_not_an_incorrect_generated_answer():
    target = gold()
    terminal = answer_view("", target)
    row = describe_changes(None, None, terminal)
    assert row["end_to_end_task_transition"] == "unavailable"
    assert not terminal["format_ok"]
    assert "filler" not in str(row)


def test_duplicate_entities_are_not_collapsed_and_malformed_is_not_correct_empty():
    target = gold([("time", "six")])
    duplicate = answer_view(answer(entities=[("time", "six"), ("time", "six")]), target)
    assert (duplicate["entity_tp"], duplicate["entity_fp"], duplicate["entity_fn"]) == (1, 1, 0)
    assert not answer_view("", gold())["task_exact"]


def test_summary_retains_full_population_and_weights_scenarios_equally():
    a = {"sample_id": "a", "scenario": "alarm", "first": None, "last": None,
         "delivered": {"intent_correct": True, "task_exact": True},
         "solver_visits": 0, "planner_actions": [], "candidate_covered": True,
         "empty_target": False, "routes": [], "end_to_end_task_transition": "unavailable"}
    b = dict(a, sample_id="b", scenario="music", delivered={"intent_correct": False, "task_exact": False})
    c = dict(b, sample_id="c")
    summary = summarize_rows([a, b, c])
    assert summary["rows"] == 3 and summary["solver_not_reached"] == 3
    assert summary["final_task_exact_rate"] == 1 / 3
    assert summary["equal_scenario_final_task_exact_rate"] == 0.5
    assert summary["per_scenario"]["music"]["rows"] == 2


def test_cross_node_summary_preserves_a_repair_lost_during_delivery():
    from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import cross_node_summary
    target = gold()
    wrong = answer_view(answer("remove"), target)
    right = answer_view(answer(), target)
    row = {"first": wrong, "last": right, "delivered": wrong, "solver_visits": 2,
           "final_error_group": "covered_intent_wrong", "role_context": [],
           "revision_task_transition": "repair"}
    summary = cross_node_summary([row])
    assert summary["transitions"]["revision_task_repairs"] == 1
    assert summary["transitions"]["revision_task_repairs_retained"] == 0
    assert summary["transitions"]["revision_task_repairs_lost"] == 1

def test_tool_events_do_not_double_count_calls_or_drop_no_action_rows():
    from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import tool_activity_summary
    base={"request_id":"r","tool_call_id":"c","contact_receipt_available":True}
    rejection={"request_id":None,"tool_call_id":None,"contact_receipt_available":False,"event":"rejected"}
    rows=[{"sample_id":"a","tool_events":[dict(base,event="attempt"),dict(base,event="result")]},
          {"sample_id":"b","tool_events":[rejection]},
          {"sample_id":"c","tool_events":[]}]
    result=tool_activity_summary(rows)
    assert result["contacted_calls"]==1
    assert result["event_counts"]=={"attempt":1,"result":1,"rejected":1}
    assert result["rows_with_events"]==2 and result["rows_without_tool_events"]==1


def test_tool_summary_requires_observed_events_instead_of_assuming_zero():
    import pytest
    from speech_aware_evidence_acquisition.analysis.slurp_system_attribution import tool_activity_summary
    with pytest.raises(KeyError):tool_activity_summary([{"sample_id":"a"}])
