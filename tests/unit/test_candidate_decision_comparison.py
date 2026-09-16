from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.candidate_decision_comparison import (
    CANDIDATE_DECISION_COMPARISON_SCHEMA,
    CandidateDecisionComparisonError,
    CandidateDecisionRow,
    compare_candidate_decisions,
)


def _row(
    sample_id: str,
    *,
    available: bool = True,
    width: int | None = 1,
    covered: bool = False,
    correct: bool = False,
    membership: bool | None = False,
) -> CandidateDecisionRow:
    return CandidateDecisionRow(
        sample_id=sample_id,
        candidate_available=available,
        candidate_width=width,
        gold_covered=covered,
        final_correct=correct,
        final_in_candidates=membership,
    )


def _cohort():
    left = (
        _row("a", width=2, covered=True, correct=True, membership=True),
        # Gold is absent, but the incorrect final remains inside a candidate.
        _row("b", width=1, membership=True),
        _row("c", width=4, covered=True, membership=None),
        _row("d", available=False, width=None, membership=None),
        _row("e", width=1, membership=None),
    )
    right = (
        _row("a", width=3, covered=True, membership=False),
        _row("b", width=2, covered=True, correct=True, membership=True),
        _row(
            "c",
            available=False,
            width=None,
            correct=True,
            membership=None,
        ),
        # A valid, correct final outside an uncovered candidate set is an
        # observed boundary escape because membership is explicitly false.
        _row("d", width=1, correct=True, membership=False),
        _row("e", width=1, membership=False),
    )
    metadata = (
        {"sample_id": "a", "scenario": "music", "speaker": "s1"},
        {"sample_id": "b", "scenario": "music", "speaker": "s2"},
        {"sample_id": "c", "scenario": "weather", "speaker": "s1"},
        {"sample_id": "d", "scenario": "weather", "speaker": "s3"},
        {"sample_id": "e", "scenario": "zero", "speaker": "s4"},
    )
    return left, right, metadata


def test_comparison_counts_all_partitions_denominators_and_membership_states():
    left, right, metadata = _cohort()
    result = compare_candidate_decisions(left, right, metadata=metadata)

    assert result["schema"] == CANDIDATE_DECISION_COMPARISON_SCHEMA
    assert result["roster_count"] == 5
    full = result["full_cohort"]
    assert full["coverage_partition"] == {
        "gained": {"count": 1, "denominator": 5, "ratio": 0.2},
        "lost": {"count": 1, "denominator": 5, "ratio": 0.2},
        "retained": {"count": 1, "denominator": 5, "ratio": 0.2},
        "neither": {"count": 2, "denominator": 5, "ratio": 0.4},
    }

    assert full["left"]["candidate_availability"] == {
        "available": 4,
        "unavailable": 1,
        "denominator": 5,
        "available_ratio": 0.8,
        "unavailable_ratio": 0.2,
    }
    assert full["left"]["candidate_width"] == {
        "count": 4,
        "sum": 8,
        "min": 1,
        "max": 4,
        "mean": 2.0,
        "histogram": {"1": 2, "2": 1, "4": 1},
    }
    assert full["right"]["candidate_width"] == {
        "count": 4,
        "sum": 7,
        "min": 1,
        "max": 3,
        "mean": 1.75,
        "histogram": {"1": 2, "2": 1, "3": 1},
    }
    assert full["left"]["final_membership"] == {
        "in_candidates": 2,
        "outside_candidates": 0,
        "unavailable_or_invalid": 3,
        "denominator": 5,
        "in_candidates_ratio": 0.4,
        "outside_candidates_ratio": 0.0,
        "unavailable_or_invalid_ratio": 0.6,
    }
    assert full["right"]["final_membership"] == {
        "in_candidates": 1,
        "outside_candidates": 3,
        "unavailable_or_invalid": 1,
        "denominator": 5,
        "in_candidates_ratio": 0.2,
        "outside_candidates_ratio": 0.6,
        "unavailable_or_invalid_ratio": 0.2,
    }

    assert full["left"]["coverage"] == {
        "numerator": 2,
        "denominator": 5,
        "ratio": 0.4,
    }
    assert full["right"]["coverage"] == {
        "numerator": 2,
        "denominator": 5,
        "ratio": 0.4,
    }
    assert full["left"]["own_covered_final_accuracy"] == {
        "numerator": 1,
        "denominator": 2,
        "ratio": 0.5,
    }
    assert full["right"]["own_covered_final_accuracy"] == {
        "numerator": 1,
        "denominator": 2,
        "ratio": 0.5,
    }
    assert full["left"]["common_covered_final_accuracy"] == {
        "numerator": 1,
        "denominator": 1,
        "ratio": 1.0,
    }
    assert full["right"]["common_covered_final_accuracy"] == {
        "numerator": 0,
        "denominator": 1,
        "ratio": 0.0,
    }
    assert full["left"]["final_accuracy"] == {
        "numerator": 1,
        "denominator": 5,
        "ratio": 0.2,
    }
    assert full["right"]["final_accuracy"] == {
        "numerator": 3,
        "denominator": 5,
        "ratio": 0.6,
    }


def test_every_scenario_is_reported_and_zero_covered_ratio_is_null():
    left, right, metadata = _cohort()
    result = compare_candidate_decisions(left, right, metadata=metadata)

    assert list(result["by_scenario"]) == ["music", "weather", "zero"]
    assert result["by_scenario"]["music"]["coverage_partition"] == {
        "gained": {"count": 1, "denominator": 2, "ratio": 0.5},
        "lost": {"count": 0, "denominator": 2, "ratio": 0.0},
        "retained": {"count": 1, "denominator": 2, "ratio": 0.5},
        "neither": {"count": 0, "denominator": 2, "ratio": 0.0},
    }
    zero = result["by_scenario"]["zero"]
    assert zero["left"]["own_covered_final_accuracy"] == {
        "numerator": 0,
        "denominator": 0,
        "ratio": None,
    }
    assert zero["right"]["common_covered_final_accuracy"] == {
        "numerator": 0,
        "denominator": 0,
        "ratio": None,
    }
    assert zero["left"]["candidate_width"]["mean"] == 1.0


def test_ratio_rows_are_numeric_sufficient_counts_with_common_coverage():
    left, right, metadata = _cohort()
    result = compare_candidate_decisions(left, right, metadata=metadata)
    left_rows = result["ratio_rows"]["left"]
    right_rows = result["ratio_rows"]["right"]

    assert list(left_rows) == ["a", "b", "c", "d", "e"]
    assert left_rows["a"] == {
        "coverage_numerator": 1,
        "coverage_denominator": 1,
        "own_covered_final_numerator": 1,
        "own_covered_final_denominator": 1,
        "common_covered_final_numerator": 1,
        "common_covered_final_denominator": 1,
        "final_accuracy_numerator": 1,
        "final_accuracy_denominator": 1,
    }
    assert right_rows["a"]["common_covered_final_numerator"] == 0
    assert right_rows["b"]["own_covered_final_denominator"] == 1
    assert right_rows["b"]["common_covered_final_denominator"] == 0
    assert left_rows["c"]["own_covered_final_denominator"] == 1
    assert left_rows["c"]["own_covered_final_numerator"] == 0
    assert right_rows["c"]["coverage_denominator"] == 1
    assert right_rows["c"]["coverage_numerator"] == 0
    assert right_rows["c"]["final_accuracy_numerator"] == 1
    for arm in ("left", "right"):
        for row in result["ratio_rows"][arm].values():
            assert row
            assert all(type(value) is int and value in (0, 1) for value in row.values())


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {
                "available": False,
                "width": 1,
                "membership": None,
            },
            "unavailable candidate.*width",
        ),
        (
            {
                "available": False,
                "width": None,
                "covered": True,
                "membership": None,
            },
            "unavailable candidate.*gold_covered",
        ),
        (
            {
                "available": False,
                "width": None,
                "membership": False,
            },
            "unavailable candidate.*membership",
        ),
        ({"width": None}, "available candidate.*positive width"),
        ({"width": 0}, "available candidate.*positive width"),
        ({"width": True}, "available candidate.*positive width"),
        (
            {"covered": True, "correct": True, "membership": False},
            "correct final membership.*gold coverage",
        ),
        (
            {"covered": False, "correct": True, "membership": True},
            "correct final membership.*gold coverage",
        ),
        (
            {"covered": True, "correct": True, "membership": None},
            "correct final membership.*gold coverage",
        ),
    ],
)
def test_row_invariants_fail_closed(kwargs, match):
    with pytest.raises(CandidateDecisionComparisonError, match=match):
        _row("x", **kwargs)


@pytest.mark.parametrize("field", ["candidate_available", "gold_covered", "final_correct"])
def test_row_boolean_fields_require_actual_booleans(field):
    values = {
        "sample_id": "x",
        "candidate_available": True,
        "candidate_width": 1,
        "gold_covered": False,
        "final_correct": False,
        "final_in_candidates": False,
    }
    values[field] = 1
    with pytest.raises(CandidateDecisionComparisonError, match=field):
        CandidateDecisionRow(**values)


def test_gold_absent_prediction_inside_wrong_candidate_is_not_an_escape():
    row = _row("x", covered=False, correct=False, membership=True)
    metadata = ({"sample_id": "x", "scenario": "one", "speaker": "s"},)
    result = compare_candidate_decisions((row,), (row,), metadata=metadata)
    membership = result["full_cohort"]["left"]["final_membership"]

    assert membership["in_candidates"] == 1
    assert membership["outside_candidates"] == 0


@pytest.mark.parametrize(
    "mutator,match",
    [
        (lambda left, right, meta: (left, tuple(reversed(right)), meta), "ordered roster"),
        (
            lambda left, right, meta: (left, right[:-1] + (_row("other"),), meta),
            "ordered roster",
        ),
        (lambda left, right, meta: (left, right, tuple(reversed(meta))), "metadata roster"),
        (
            lambda left, right, meta: (
                left,
                right,
                meta[:-1]
                + (
                    {
                        "sample_id": "e",
                        "scenario": "zero",
                        "speaker": "s4",
                        "extra": "forbidden",
                    },
                ),
            ),
            "exactly",
        ),
    ],
)
def test_nonidentical_roster_order_and_metadata_are_rejected(mutator, match):
    left, right, metadata = _cohort()
    left, right, metadata = mutator(left, right, metadata)
    with pytest.raises(CandidateDecisionComparisonError, match=match):
        compare_candidate_decisions(left, right, metadata=metadata)


def test_empty_duplicate_and_nonrow_inputs_are_rejected():
    with pytest.raises(CandidateDecisionComparisonError, match="nonempty"):
        compare_candidate_decisions((), (), metadata=())
    row = _row("same")
    metadata = (
        {"sample_id": "same", "scenario": "one", "speaker": "s1"},
        {"sample_id": "same", "scenario": "one", "speaker": "s1"},
    )
    with pytest.raises(CandidateDecisionComparisonError, match="unique"):
        compare_candidate_decisions((row, row), (row, row), metadata=metadata)
    with pytest.raises(CandidateDecisionComparisonError, match="CandidateDecisionRow"):
        compare_candidate_decisions(
            ({"sample_id": "x"},),
            ({"sample_id": "x"},),
            metadata=({"sample_id": "x", "scenario": "one", "speaker": "s"},),
        )


@pytest.mark.parametrize("field,value", [("sample_id", ""), ("scenario", ""), ("speaker", 2)])
def test_metadata_fields_are_nonempty_text(field, value):
    row = _row("x")
    metadata = {"sample_id": "x", "scenario": "one", "speaker": "s"}
    metadata[field] = value
    with pytest.raises(CandidateDecisionComparisonError, match=field):
        compare_candidate_decisions((row,), (row,), metadata=(metadata,))


def test_all_unavailable_group_keeps_width_and_membership_unavailable():
    row = _row("x", available=False, width=None, membership=None)
    metadata = ({"sample_id": "x", "scenario": "none", "speaker": "s"},)
    result = compare_candidate_decisions((row,), (row,), metadata=metadata)
    arm = result["full_cohort"]["left"]

    assert arm["candidate_width"] == {
        "count": 0,
        "sum": 0,
        "min": None,
        "max": None,
        "mean": None,
        "histogram": {},
    }
    assert arm["candidate_availability"]["unavailable"] == 1
    assert arm["final_membership"]["unavailable_or_invalid"] == 1


def test_ratio_rows_feed_the_existing_pooled_ratio_comparator():
    from speech_aware_evidence_acquisition.analysis.pooled_ratio_compare import (
        compare_pooled_ratios,
    )

    left, right, metadata = _cohort()
    result = compare_candidate_decisions(left, right, metadata=metadata)
    ratio_metadata = {
        row["sample_id"]: {"speaker": row["speaker"]}
        for row in metadata
    }
    metrics = {
        name: {
            "numerator_field": f"{name}_numerator",
            "denominator_field": f"{name}_denominator",
            "direction": "higher",
        }
        for name in (
            "coverage",
            "own_covered_final",
            "common_covered_final",
            "final_accuracy",
        )
    }
    compared = compare_pooled_ratios(
        result["ratio_rows"]["left"],
        result["ratio_rows"]["right"],
        ratio_metadata,
        metrics,
        groupings={},
        seed=7,
        n_replicates=2,
        ci_level=0.9,
        cluster_field="speaker",
    )

    assert compared["coverage"]["natural_mixture"]["left_ratio_pct"] == 40.0
    assert compared["own_covered_final"]["natural_mixture"]["left_ratio_pct"] == 50.0
    assert (
        compared["common_covered_final"]["natural_mixture"]["left_ratio_pct"]
        == 100.0
    )
    assert compared["final_accuracy"]["natural_mixture"]["right_ratio_pct"] == 60.0
