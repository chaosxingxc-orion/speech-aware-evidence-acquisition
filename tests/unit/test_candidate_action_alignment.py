"""Pure exhaustive checks for ordered candidate-action alignment."""

from __future__ import annotations

from itertools import combinations, product

import pytest

from speech_aware_evidence_acquisition.analysis.candidate_action_alignment import (
    CandidateActionAlignmentError,
    candidate_action_alignment,
)


def _unordered_oracle(expected, actions):
    best = 0
    for assignment in product(range(-1, len(actions)), repeat=len(expected)):
        used = [index for index in assignment if index >= 0]
        if len(used) != len(set(used)):
            continue
        matched = sum(
            action >= 0 and name in actions[action]
            for name, action in zip(expected, assignment, strict=True)
        )
        if matched == len(used):
            best = max(best, matched)
    return best


def _ordered_oracle(expected, actions):
    for width in range(min(len(expected), len(actions)), -1, -1):
        for reference_indices in combinations(range(len(expected)), width):
            for action_indices in combinations(range(len(actions)), width):
                if all(
                    expected[reference] in actions[action]
                    for reference, action in zip(
                        reference_indices, action_indices, strict=True
                    )
                ):
                    return width
    raise AssertionError("zero-width ordered alignment must exist")


def test_crossed_actions_separate_unordered_ordered_and_strict_counts():
    report = candidate_action_alignment(("alpha", "beta"), (("beta",), ("alpha",)))

    assert report["reference_occurrence_count"] == 2
    assert report["union_coverage_count"] == 2
    assert report["unordered_one_to_one_match_count"] == 2
    assert report["ordered_one_to_one_match_count"] == 1
    assert report["strict_same_position_match_count"] == 0
    assert report["full_coverage"] == {
        "union": True,
        "unordered_one_to_one": True,
        "ordered_one_to_one": False,
        "strict_one_for_one": False,
    }
    assert report["descriptive_losses"] == {
        "unavailable": 0,
        "absent_from_union": 0,
        "action_capacity_or_grouping": 0,
        "order_incompatibility": 1,
        "strict_position": 1,
        "total": 2,
    }


def test_one_candidate_action_cannot_cover_two_expected_occurrences():
    report = candidate_action_alignment(("alpha", "beta"), (("alpha", "beta"),))

    assert report["union_coverage_count"] == 2
    assert report["unordered_one_to_one_match_count"] == 1
    assert report["ordered_one_to_one_match_count"] == 1
    assert report["strict_same_position_match_count"] == 1
    assert report["descriptive_losses"]["action_capacity_or_grouping"] == 1


def test_repeated_reference_occurrences_need_distinct_candidate_actions():
    one = candidate_action_alignment(("alpha", "alpha"), (("alpha",),))
    two = candidate_action_alignment(
        ("alpha", "alpha"), (("alpha",), ("alpha",))
    )

    assert one["union_coverage_count"] == 2
    assert one["unordered_one_to_one_match_count"] == 1
    assert one["ordered_one_to_one_match_count"] == 1
    assert two["unordered_one_to_one_match_count"] == 2
    assert two["ordered_one_to_one_match_count"] == 2
    assert two["full_coverage"]["strict_one_for_one"] is True


def test_maximum_matching_handles_an_overlap_case_where_greedy_fails():
    report = candidate_action_alignment(
        ("alpha", "beta"),
        (("alpha", "beta"), ("alpha",)),
    )

    assert report["unordered_one_to_one_match_count"] == 2
    assert report["ordered_one_to_one_match_count"] == 1
    assert report["strict_same_position_match_count"] == 1


def test_unavailable_and_available_empty_states_are_distinct():
    unavailable = candidate_action_alignment(("alpha", "beta"), None)
    empty = candidate_action_alignment(("alpha", "beta"), ())

    assert unavailable["candidate_state_available"] is False
    assert unavailable["unavailable_reference_count"] == 2
    assert unavailable["absent_from_union_count"] == 0
    assert unavailable["descriptive_losses"]["unavailable"] == 2
    assert set(unavailable["full_coverage"].values()) == {False}

    assert empty["candidate_state_available"] is True
    assert empty["unavailable_reference_count"] == 0
    assert empty["absent_from_union_count"] == 2
    assert empty["descriptive_losses"]["absent_from_union"] == 2
    assert empty["descriptive_losses"]["total"] == 2


def test_extra_leading_action_preserves_order_but_breaks_strict_one_for_one():
    report = candidate_action_alignment(
        ("alpha", "beta"),
        (("other",), ("alpha",), ("beta",)),
    )

    assert report["ordered_one_to_one_match_count"] == 2
    assert report["strict_same_position_match_count"] == 0
    assert report["full_coverage"]["ordered_one_to_one"] is True
    assert report["full_coverage"]["strict_one_for_one"] is False


def test_empty_reference_has_zero_counts_and_undefined_coverage_flags():
    for actions in (None, (), (("alpha",),)):
        report = candidate_action_alignment((), actions)
        assert report["reference_occurrence_count"] == 0
        assert report["unavailable_reference_count"] == 0
        assert report["absent_from_union_count"] == 0
        assert report["union_coverage_count"] == 0
        assert report["unordered_one_to_one_match_count"] == 0
        assert report["ordered_one_to_one_match_count"] == 0
        assert report["strict_same_position_match_count"] == 0
        assert set(report["full_coverage"].values()) == {None}
        assert set(report["descriptive_losses"].values()) == {0}


@pytest.mark.parametrize(
    "expected,actions,match",
    (
        (("",), (), "expected tool names"),
        ((" alpha",), (), "expected tool names"),
        (("alpha ",), (), "expected tool names"),
        (("alph\N{LATIN SMALL LETTER A WITH ACUTE}",), (), "expected tool names"),
        (("alpha",), ("alpha",), "candidate actions"),
        (("alpha",), (("alpha", "alpha"),), "unique tool names"),
        (("alpha",), ((" beta",),), "candidate tool names"),
        (("alpha",), (None,), "candidate actions"),
    ),
)
def test_invalid_names_and_action_shapes_are_rejected(expected, actions, match):
    with pytest.raises(CandidateActionAlignmentError, match=match):
        candidate_action_alignment(expected, actions)


def test_small_exhaustive_space_matches_independent_reference_oracles():
    names = ("alpha", "beta")
    candidate_sets = ((), ("alpha",), ("beta",), ("alpha", "beta"))
    case_count = 0
    for reference_width in range(4):
        for expected in product(names, repeat=reference_width):
            for action_width in range(4):
                for actions in product(candidate_sets, repeat=action_width):
                    case_count += 1
                    report = candidate_action_alignment(expected, actions)
                    union = {name for action in actions for name in action}
                    union_count = sum(name in union for name in expected)
                    strict = sum(
                        expected[index] in actions[index]
                        for index in range(min(len(expected), len(actions)))
                    )
                    assert report["union_coverage_count"] == union_count
                    assert report["unordered_one_to_one_match_count"] == (
                        _unordered_oracle(expected, actions)
                    )
                    assert report["ordered_one_to_one_match_count"] == (
                        _ordered_oracle(expected, actions)
                    )
                    assert report["strict_same_position_match_count"] == strict
                    losses = report["descriptive_losses"]
                    assert losses["total"] == sum(
                        value for key, value in losses.items() if key != "total"
                    )
                    assert report["reference_occurrence_count"] == (
                        report["unavailable_reference_count"]
                        + report["absent_from_union_count"]
                        + losses["action_capacity_or_grouping"]
                        + losses["order_incompatibility"]
                        + losses["strict_position"]
                        + report["strict_same_position_match_count"]
                    )
                    assert (
                        report["strict_same_position_match_count"]
                        <= report["ordered_one_to_one_match_count"]
                        <= report["unordered_one_to_one_match_count"]
                        <= report["union_coverage_count"]
                        <= report["reference_occurrence_count"]
                    )
                    coverage = report["full_coverage"]
                    if reference_width == 0:
                        assert set(coverage.values()) == {None}
                    else:
                        assert not coverage["strict_one_for_one"] or coverage[
                            "ordered_one_to_one"
                        ]
                        assert not coverage["ordered_one_to_one"] or coverage[
                            "unordered_one_to_one"
                        ]
                        assert not coverage["unordered_one_to_one"] or coverage[
                            "union"
                        ]
    assert case_count == 1_275
