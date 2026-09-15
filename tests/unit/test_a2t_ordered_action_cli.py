"""Tests for distinct sample, stratum and occurrence coverage denominators."""

from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_ordered_action_cli import (
    _verified_bytes,
    build_report,
)
from speech_aware_evidence_acquisition.analysis.candidate_action_alignment import (
    candidate_action_alignment,
)


def _row(sid, tier, names, actions, direct=0, system=0):
    count = len(names)
    return {
        "sample_id": sid, "tier": tier, "domain": tier,
        "expected_tool_names": names, "expanded_expected_count": count,
        "official_expected_count": count, "unknown_reference_names": [],
        "candidate_action_count": len(actions) if actions is not None else "unavailable",
        "reference_count_class": "multiple" if count > 1 else "single",
        "first_compatibility_failure": "fixture",
        "alignment": candidate_action_alignment(names, actions),
        "quality": {
            arm: dict.fromkeys((
                "official_tool", "official_exact", "repo_ordered_tool",
                "repo_multiset_tool", "repo_exact",
            ), float(value))
            for arm, value in (("direct", direct), ("system", system))
        },
    }


def test_denominators_weightings_and_missing_state_remain_distinct():
    rows = [
        _row("one", "tier1", ["a", "a"], [["a"]], system=1),
        _row("two", "tier1", ["a"], None),
        _row("three", "tier2", ["b"], [["b"]], direct=1, system=1),
    ]
    before = deepcopy(rows)
    report = build_report(rows)
    assert rows == before
    natural = report["natural"]
    assert natural["sample_count"] == 3
    assert natural["reference_occurrence_count"] == 4
    assert natural["candidate_state_unavailable_count"] == 1
    assert natural["full_coverage_counts"]["union"] == 2
    assert natural["full_coverage_rates"]["union"] == pytest.approx(2 / 3)
    assert natural["full_coverage_rates"]["ordered_one_to_one"] == pytest.approx(1 / 3)
    assert natural["occurrence_micro_rates"]["union_coverage_count"] == 0.75
    assert natural["occurrence_micro_rates"]["ordered_one_to_one_match_count"] == 0.5
    assert natural["descriptive_occurrence_losses"] == {
        "unavailable": 1, "absent_from_union": 0,
        "action_capacity_or_grouping": 1, "order_incompatibility": 0,
        "strict_position": 0, "total": 2,
    }
    assert report["equal_tier"]["full_coverage_rates"]["union"] == 0.75
    assert report["equal_tier"]["quality"]["system"]["official_exact"] == 0.75
    assert natural["quality"]["system"]["official_exact"]["rate"] == pytest.approx(2 / 3)
    assert report["conditional_full_coverage"]["union"]["True"]["sample_count"] == 2
    assert report["by_candidate_action_count"]["unavailable"]["sample_count"] == 1


def test_hash_failure_precedes_json_or_label_projection(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text("not JSON or a model request")
    with pytest.raises(ValueError, match="source hash mismatch"):
        _verified_bytes({"path": str(path), "sha256": "0" * 64})


def test_crossed_order_does_not_change_saved_quality_or_invent_causality():
    row = _row("crossed", "tier", ["a", "b"], [["b"], ["a"]], direct=1, system=1)
    report = build_report([row])
    assert report["natural"]["full_coverage_counts"] == {
        "union": 1, "unordered_one_to_one": 1,
        "ordered_one_to_one": 0, "strict_one_for_one": 0,
    }
    assert report["natural"]["quality_delta"]["official_exact"] == 0
    assert report["status"] == "POSTHOC_DESCRIPTIVE_NO_NEW_VERDICT"


def test_no_reference_remains_undefined_even_in_equal_stratum_views():
    report = build_report([_row("empty", "tier", [], [])])
    assert report["natural"]["coverage_applicable_sample_count"] == 0
    assert set(report["natural"]["full_coverage_rates"].values()) == {None}
    assert set(report["equal_tier"]["full_coverage_rates"].values()) == {None}
    assert set(report["equal_tier"]["coverage_applicable_strata"].values()) == {0}
