"""Business quality and original sample latency remain separate objectives."""
import copy

import pytest

from speech_aware_evidence_acquisition.analysis.context_configuration import describe_configurations
from speech_aware_evidence_acquisition.analysis.system_cache_cost import summarize_sample_execution_timing
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def fixture():
    ids = [f"slurp:train:{i}:audio" for i in range(4)]
    roster = {sid: {"sample_id": sid, "utterance_id": str(i // 2),
                    "stratum": "a" if i < 2 else "b"} for i, sid in enumerate(ids)}
    pairs = [{"layout": name, "primary": name + "-p", "aa": name + "-r"}
             for name in ("legacy-trajectory", "before-speech-trajectory", "legacy-role", "before-speech-role")]
    members = {}
    for pair in pairs:
        for repeat in ("primary", "aa"):
            run = pair[repeat]
            timing = summarize_sample_execution_timing([
                {"schema": "saea-sample-execution-timing-v1", "sample_id": sid,
                 "execution_unit_id": None, "admission_index": i, "expected_samples": 4,
                 "slot_count": 4, "queue_depth": 4, "batch_started_ns": 0,
                 "admitted_ns": i * 1_000_000_000,
                 "finished_ns": (i + duration) * 1_000_000_000,
                 "status": "completed", "error_type": None}
                for i, (sid, duration) in enumerate(zip(ids, [20, 4, 8, 12], strict=True))
            ], expected_sample_ids=ids)
            rows = {sid: {"tp": 9 if i == 0 else 0, "fp": 1 if i == 1 else 0,
                          "fn": 1 if i == 0 else 0, "intent": float(i != 1),
                          "reliable_completion": i != 2, "abstained": i == 2,
                          "delivery_kind": "abstention" if i == 2 else "accepted",
                          "model_calls": 4, "tool_calls": 0,
                          "prompt_tokens": None, "completion_tokens": None}
                    for i, sid in enumerate(ids)}
            members[run] = {"rows": rows, "official": {"slu_f1": 0.9, "intent": 0.75},
                            "sample_timing": timing, "node_timing": {"by_role": {"solver": {"reused_input_fraction": 0.8}}}}
    return members, pairs, roster


def describe(members, pairs, roster):
    return describe_configurations(members, comparisons=pairs, roster=roster,
                                   bootstrap_draws=20, seed=20261003)


def test_pooled_quality_first_admission_all_repeats_and_no_automatic_choice():
    members, pairs, roster = fixture()
    report = describe(members, pairs, roster)
    row = report["members"][pairs[0]["primary"]]
    assert row["slu_f1"] == pytest.approx(0.9)  # Not mean per-input F1.
    assert row["all_samples_mean_seconds"] == 11
    assert row["first_admitted_seconds"] == 20
    assert row["remaining_samples_mean_seconds"] == 8
    assert row["reliable_completion_rate"] == 0.75
    assert row["abstention_rate"] == 0.25
    assert row["prompt_tokens"] is None
    assert report["sample_count"] == 4 and report["cluster_count"] == 2
    assert len(report["members"]) == 8 and len(report["comparisons"]) == 16
    assert len(report["per_stratum"]) == 2
    assert report["selection"] is None and report["optimizer_export"] is False
    assert report["members"][pairs[0]["primary"]]["node_timing"] == members[pairs[0]["primary"]]["node_timing"]
    assert report["equal_stratum"][pairs[0]["primary"]]["slu_f1"] == pytest.approx(0.45)
    null = report["comparisons"][0]
    assert null["kind"] == "own-repeat"
    assert null["metrics"]["slu_f1"]["point_estimate"] == 0
    assert null["metrics"]["remaining_samples_mean_seconds"]["point_estimate"] == 0


def test_zero_entity_counts_keep_false_positives_and_official_zero_convention():
    members, pairs, roster = fixture()
    for member in members.values():
        for row in member["rows"].values():
            row.update(tp=0, fn=0)
        member["official"]["slu_f1"] = 0.0
    report = describe(members, pairs, roster)
    row = report["members"][pairs[0]["primary"]]
    assert row["slu_f1"] == 0 and row["official_counts"]["fp"] == 1


def test_faster_lower_quality_high_cache_member_remains_visible():
    members, pairs, roster = fixture()
    run = pairs[-1]["primary"]
    member = members[run]
    for row in member["rows"].values():
        row.update(tp=0, intent=0)
    member["official"] = {"slu_f1": 0, "intent": 0}
    member["node_timing"]["by_role"]["solver"]["reused_input_fraction"] = 0.99
    report = describe(members, pairs, roster)
    assert report["members"][run]["slu_f1"] == 0
    assert report["selection"] is None


@pytest.mark.parametrize("fault", ["missing_member", "extra_member", "duplicate_pair", "missing_row",
                                   "different_first", "partial_timing", "bad_aggregate", "nan_count",
                                   "negative_count", "bad_intent", "bad_cost", "bad_terminal",
                                   "cross_stratum_cluster", "duplicate_timing", "bad_draws"])
def test_incomplete_or_inconsistent_comparisons_refuse(fault):
    members, pairs, roster = fixture()
    key = pairs[0]["primary"]
    sid = next(iter(roster))
    member = members[key]
    draws = 20
    if fault == "missing_member":
        members.pop(key)
    elif fault == "extra_member":
        members["unregistered"] = copy.deepcopy(member)
    elif fault == "duplicate_pair":
        pairs[1] = copy.deepcopy(pairs[0])
    elif fault == "missing_row":
        member["rows"].pop(sid)
    elif fault == "different_first":
        member["sample_timing"]["samples"].reverse()
    elif fault == "partial_timing":
        member["sample_timing"]["available"] = False
    elif fault == "bad_aggregate":
        member["official"]["slu_f1"] = 0.4
    elif fault == "nan_count":
        member["rows"][sid]["tp"] = float("nan")
    elif fault == "negative_count":
        member["rows"][sid]["fp"] = -1
    elif fault == "bad_intent":
        member["rows"][sid]["intent"] = 2
    elif fault == "bad_cost":
        member["rows"][sid]["model_calls"] = True
    elif fault == "bad_terminal":
        member["rows"][sid]["reliable_completion"] = 1
    elif fault == "cross_stratum_cluster":
        list(roster.values())[-1]["utterance_id"] = "0"
    elif fault == "duplicate_timing":
        member["sample_timing"]["samples"][1]["sample_id"] = sid
    elif fault == "bad_draws":
        draws = 0
    with pytest.raises((PolicyError, ValueError)):
        describe_configurations(members, comparisons=pairs, roster=roster,
                                bootstrap_draws=draws, seed=20261003)


def test_failed_workflow_is_retained_but_refuses_latency_selection():
    members, pairs, roster = fixture()
    member = members[pairs[0]["primary"]]
    member["sample_timing"]["eligible_for_efficiency_comparison"] = False
    report = describe(members, pairs, roster)
    assert report["efficiency_eligible"] is False
    assert len(report["members"]) == 8 and report["selection"] is None
