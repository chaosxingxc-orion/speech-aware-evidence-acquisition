"""Verify parameter attribution partitions retain overlapping error kinds."""

from copy import deepcopy

from speech_aware_evidence_acquisition.analysis.a2t_primary_parameter_cli import report
from speech_aware_evidence_acquisition.analysis.a2t_primary_parameter_errors import (
    diagnose_primary_parameters,
)


def _row(sid, tier, direct_correct, system_correct, pred, gold):
    row = {
        "sample_id": sid, "tier": tier, "domain": tier,
        "primary_reference_tool": "fixtureTool", "reference_empty": not bool(gold),
        "ordered_candidate_coverage": True,
    }
    for arm, correct in (("direct", direct_correct), ("system", system_correct)):
        diag = diagnose_primary_parameters(pred, gold, {})
        row[arm] = {
            "diagnostics": diag,
            "saved": {
                "tool_correct": correct, "exact_match": correct and diag["param_exact"],
                "param_predicted_keys": diag["predicted_normalized_key_count"],
                "param_gold_keys": diag["reference_normalized_key_count"],
                "param_correct_keys": diag["correct_normalized_key_count"],
            },
            "repo_exact": False, "repo_extra_keys_stripped": 0,
            "parser_comparable": True, "parser_parameter_disagreement": False,
            "official_wrong_keys_matching_repo_parse": [],
            "official_missing_keys_matching_repo_parse": [],
        }
    return row


def test_shared_correct_cohort_overlapping_errors_and_equal_strata_are_separate():
    rows = [
        _row("a", "tier1", True, True, {"x": 2, "extra": 3}, {"x": 1, "missing": 4}),
        _row("b", "tier1", False, True, {}, {}),
        _row("c", "tier2", True, True, {}, {}),
    ]
    before = deepcopy(rows)
    result = report(rows)
    assert rows == before
    assert result["scopes"]["both_primary_tools_correct"]["sample_count"] == 2
    assert result["scopes"]["system_primary_tool_correct"]["sample_count"] == 3
    errors = result["scopes"]["all"]["arms"]["system"]["errors"]
    assert all(errors[field]["samples"] == 1 for field in errors)
    assert result["equal_stratum_error_sample_rates"]["by_tier"]["system"]["missing_keys"] == 0.25
    combinations = result["scopes"]["all"]["arms"]["system"]["error_combinations"]
    assert combinations["missing_keys+extra_keys+wrong_value_keys"] == 1
    assert combinations["none"] == 2


def test_empty_shared_correct_cohort_is_unavailable_not_perfect():
    result = report([_row("a", "tier1", False, False, {}, {"required": 1})])
    assert result["scopes"]["both_primary_tools_correct"]["sample_count"] == 0
    assert set(result["equal_stratum_error_sample_rates"]["both_correct_by_tier"]["system"].values()) == {None}
