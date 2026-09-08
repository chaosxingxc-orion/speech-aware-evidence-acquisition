"""``analysis.e21_person_harm``: where an entity-class harm actually falls.

The module's claims are four, and each is pinned here as a property rather than
as a golden number: the per-word multiplicity reproduces the ConEC mirror's own
bucket counts; the operation kinds partition the reference; the per-span
reference blocks are a contiguous partition; and the position measures are
exact in words and honestly derived in seconds.

The 44 real calls are proven in the read's own receipt
(``docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1-person-harm-decomposition/``),
whose identity anchor refuses to write unless the pooled per-word rows reproduce
BOTH arms' sealed PERSON entity WER. These tests pin the algebra that anchor
rests on.
"""

from __future__ import annotations

import math
import random

import pytest

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp
from speech_aware_evidence_acquisition.analysis.e21_person_harm import (
    BOUNDARY_BINS,
    PersonHarmError,
    bin_label,
    boundary_distance_seconds,
    boundary_distance_words,
    bucket_counts,
    class_multiplicity,
    group_table,
    is_error,
    merge_units_below_threshold,
    operation_kinds_by_reference,
    seconds_per_reference_word,
    span_index_of_reference,
    span_reference_ranges,
    wer_percent,
)
from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec


# ---------------------------------------------------------------------------
# 1. Multiplicity -- the (word, entity id) pair is the unit of account.
# ---------------------------------------------------------------------------


def test_multiplicity_counts_one_id_per_word():
    owners = [(), ("a",), ("b",), None, ("a",)]
    types = {"a": "PERSON", "b": "ORG"}
    assert class_multiplicity(owners, types, "PERSON") == (0, 1, 0, 0, 1)
    assert class_multiplicity(owners, types, "ORG") == (0, 0, 1, 0, 0)


def test_multiplicity_counts_a_word_twice_when_two_ids_share_its_type():
    """fstalign's ``RecordTagWer`` visits the stitch once per tag, so a word
    carrying two PERSON ids is two PERSON reference words."""

    owners = [("a", "c"), ("a",)]
    types = {"a": "PERSON", "c": "PERSON"}
    assert class_multiplicity(owners, types, "PERSON") == (2, 1)


def test_multiplicity_never_claims_an_unresolved_position():
    assert class_multiplicity([None, None], {}, "PERSON") == (0, 0)


def test_multiplicity_refuses_an_untyped_entity_id():
    with pytest.raises(PersonHarmError, match="no type"):
        class_multiplicity([("a",)], {}, "PERSON")


def test_multiplicity_reproduces_the_conec_bucket_denominator():
    """The property the identity anchor rests on: the multiplicity-weighted count
    of class words equals the mirror's own ``reference_words`` for that class."""

    reference = ["a", "b", "c", "d"]
    hypothesis = ["a", "x", "c"]
    owners = [(), ("p1", "p2"), ("p1",), ("o1",)]
    types = {"p1": "PERSON", "p2": "PERSON", "o1": "ORG"}
    operations = conec.aligned_operations(reference, hypothesis)
    buckets = conec.entity_wer_buckets(operations, owners, types)
    weights = class_multiplicity(owners, types, "PERSON")
    assert sum(weights) == buckets["PERSON"]["reference_words"]


# ---------------------------------------------------------------------------
# 2. Operation kinds -- the S/D split, and never an insertion.
# ---------------------------------------------------------------------------


def test_operation_kinds_partition_the_reference():
    reference = ["a", "b", "c"]
    hypothesis = ["a", "z", "q", "c"]
    operations = conec.aligned_operations(reference, hypothesis)
    kinds = operation_kinds_by_reference(operations, len(reference))
    assert len(kinds) == len(reference)
    assert all(kind in (conec.OP_HIT, conec.OP_SUBSTITUTION, conec.OP_DELETION) for kind in kinds)


def test_operation_kinds_agree_with_the_bucket_counts():
    random.seed(20260908)
    vocabulary = "abcdefg"
    for _ in range(60):
        reference = [random.choice(vocabulary) for _ in range(random.randint(1, 14))]
        hypothesis = [random.choice(vocabulary) for _ in range(random.randint(0, 14))]
        operations = conec.aligned_operations(reference, hypothesis)
        owners = [("p",)] * len(reference)
        buckets = conec.entity_wer_buckets(operations, owners, {"p": "PERSON"})
        kinds = operation_kinds_by_reference(operations, len(reference))
        assert sum(1 for k in kinds if k == conec.OP_SUBSTITUTION) == buckets["PERSON"][
            "substitutions"
        ]
        assert sum(1 for k in kinds if k == conec.OP_DELETION) == buckets["PERSON"]["deletions"]
        assert buckets["PERSON"]["insertions"] == 0


def test_operation_kinds_refuse_a_reference_word_no_operation_consumed():
    with pytest.raises(PersonHarmError, match="consumed by no operation"):
        operation_kinds_by_reference((("hit", 0, 0),), 2)


def test_is_error_is_the_bucket_numerator():
    assert is_error(conec.OP_SUBSTITUTION)
    assert is_error(conec.OP_DELETION)
    assert not is_error(conec.OP_HIT)
    assert not is_error(conec.OP_INSERTION)


# ---------------------------------------------------------------------------
# 3. Span reference blocks -- a contiguous partition, always.
# ---------------------------------------------------------------------------


def _charged(reference, spans_text):
    """Charge one call's operations to its spans exactly as the registered
    instrument does, from the span texts alone."""

    stitched = " ".join(text for text in spans_text if text)
    hypothesis = stitched.split()
    operations = conec.aligned_operations(reference, hypothesis)
    boundaries = []
    prefix: list[str] = []
    for text in spans_text:
        if text:
            prefix.extend(text.split())
        boundaries.append(len(prefix))
    charged = wp.charge_operations_to_windows(operations, boundaries, len(hypothesis))
    return operations, charged


def test_span_reference_ranges_partition_and_are_contiguous():
    reference = ["a", "b", "c", "d", "e", "f"]
    operations, charged = _charged(reference, ["a b", "c q", "e f"])
    ranges = span_reference_ranges(charged, len(reference))
    assert ranges[0][0] == 0
    assert ranges[-1][1] == len(reference)
    for (_, high), (low, _) in zip(ranges, ranges[1:]):
        assert high == low
    del operations


def test_span_reference_ranges_admit_an_empty_span():
    reference = ["a", "b"]
    _operations, charged = _charged(reference, ["a b", ""])
    ranges = span_reference_ranges(charged, len(reference))
    assert ranges[-1][0] == ranges[-1][1]


def test_span_reference_ranges_random_property():
    random.seed(20260908)
    vocabulary = "abcdef"
    for _ in range(60):
        reference = [random.choice(vocabulary) for _ in range(random.randint(1, 16))]
        spans_text = [
            " ".join(random.choice(vocabulary) for _ in range(random.randint(0, 4)))
            for _ in range(random.randint(1, 4))
        ]
        _operations, charged = _charged(reference, spans_text)
        ranges = span_reference_ranges(charged, len(reference))
        covered = [index for low, high in ranges for index in range(low, high)]
        assert covered == list(range(len(reference)))


def test_span_index_of_reference_is_the_inverse():
    ranges = ((0, 2), (2, 2), (2, 5))
    assert span_index_of_reference(ranges, 5) == (0, 0, 2, 2, 2)


def test_span_index_of_reference_refuses_an_uncovered_word():
    with pytest.raises(PersonHarmError, match="belongs to no span"):
        span_index_of_reference(((0, 2),), 3)


# ---------------------------------------------------------------------------
# 4. Position -- exact in words, derived in seconds, and labelled.
# ---------------------------------------------------------------------------


def test_boundary_distance_words_is_symmetric_and_exact():
    assert boundary_distance_words((10, 15), 10) == (0, 4, 0)
    assert boundary_distance_words((10, 15), 12) == (2, 2, 2)
    assert boundary_distance_words((10, 15), 14) == (4, 0, 0)


def test_boundary_distance_words_refuses_a_word_outside_its_block():
    with pytest.raises(PersonHarmError, match="outside span block"):
        boundary_distance_words((10, 15), 15)


def test_seconds_per_reference_word_is_local_and_zero_on_an_empty_span():
    assert seconds_per_reference_word(90.0, 225) == pytest.approx(0.4)
    assert seconds_per_reference_word(90.0, 0) == 0.0


def test_seconds_per_reference_word_refuses_a_zero_length_span_with_words():
    with pytest.raises(PersonHarmError, match="has 0"):
        seconds_per_reference_word(0.0, 3)


def test_boundary_distance_seconds_centres_the_word_in_its_slot():
    assert boundary_distance_seconds(0, 0.4) == pytest.approx(0.2)
    assert boundary_distance_seconds(2, 0.4) == pytest.approx(1.0)


def test_boundary_distance_seconds_refuses_a_negative_distance():
    with pytest.raises(PersonHarmError, match="cannot be negative"):
        boundary_distance_seconds(-1, 0.4)


def test_bins_are_half_open_and_exhaustive():
    assert bin_label(0.0) == "0-1 s"
    assert bin_label(0.999) == "0-1 s"
    assert bin_label(1.0) == "1-3 s"
    assert bin_label(3.0) == "3-10 s"
    assert bin_label(10.0) == ">10 s"
    assert bin_label(1e9) == ">10 s"
    assert BOUNDARY_BINS[-1][1] == math.inf


def test_bin_label_refuses_a_negative_offset():
    with pytest.raises(PersonHarmError, match="falls in none"):
        bin_label(-0.1)


# ---------------------------------------------------------------------------
# 5. Aggregation.
# ---------------------------------------------------------------------------


def _row(multiplicity, comparator_kind, cell_kind, stratum="x"):
    return {
        "multiplicity": multiplicity,
        "comparator_kind": comparator_kind,
        "cell_kind": cell_kind,
        "stratum": stratum,
    }


def test_bucket_counts_weight_by_multiplicity():
    rows = [
        _row(2, conec.OP_SUBSTITUTION, conec.OP_HIT),
        _row(1, conec.OP_DELETION, conec.OP_DELETION),
        _row(1, conec.OP_HIT, conec.OP_SUBSTITUTION),
    ]
    assert bucket_counts(rows, "comparator") == {
        "substitutions": 2,
        "deletions": 1,
        "errors": 3,
        "reference_words": 4,
    }
    assert bucket_counts(rows, "cell") == {
        "substitutions": 1,
        "deletions": 1,
        "errors": 2,
        "reference_words": 4,
    }


def test_wer_percent_is_zero_on_an_empty_bucket():
    assert wer_percent({"errors": 0, "reference_words": 0}) == 0.0
    assert wer_percent({"errors": 1, "reference_words": 4}) == pytest.approx(25.0)


def test_merge_units_below_threshold_absorbs_into_the_longer_neighbour():
    units = [
        {"start_seconds": 0.0, "end_seconds": 20.0},
        {"start_seconds": 20.0, "end_seconds": 22.0},
        {"start_seconds": 22.0, "end_seconds": 27.0},
    ]
    assert merge_units_below_threshold(units, 3.0) == ((0.0, 22.0), (22.0, 27.0))


def test_merge_units_below_threshold_tiles_without_gap_or_overlap():
    units = [
        {"start_seconds": 0.0, "end_seconds": 4.0},
        {"start_seconds": 4.0, "end_seconds": 5.0},
        {"start_seconds": 5.0, "end_seconds": 30.0},
        {"start_seconds": 30.0, "end_seconds": 31.0},
    ]
    spans = merge_units_below_threshold(units, 10.0)
    assert spans[0][0] == 0.0
    assert spans[-1][1] == 31.0
    for (_, end), (start, _) in zip(spans, spans[1:]):
        assert end == start
    assert all(end - start >= 10.0 for start, end in spans)


def test_merge_units_below_threshold_respects_the_cap():
    """A merge that would exceed the 90-second cap tries the other neighbour;
    with neither admissible the sliver is kept, exactly as plan v2's rule 4."""

    units = [
        {"start_seconds": 0.0, "end_seconds": 90.0},
        {"start_seconds": 90.0, "end_seconds": 90.5},
        {"start_seconds": 90.5, "end_seconds": 180.5},
    ]
    spans = merge_units_below_threshold(units, 5.0)
    assert spans == ((0.0, 90.0), (90.0, 90.5), (90.5, 180.5))


def test_merge_units_below_threshold_is_a_no_op_below_the_plan_minimum():
    units = [
        {"start_seconds": 0.0, "end_seconds": 20.0},
        {"start_seconds": 20.0, "end_seconds": 40.0},
    ]
    assert merge_units_below_threshold(units, 1.0) == ((0.0, 20.0), (20.0, 40.0))


def test_group_table_signs_improvement_so_positive_means_the_cell_is_better():
    rows = [
        _row(1, conec.OP_SUBSTITUTION, conec.OP_HIT, "near"),
        _row(1, conec.OP_HIT, conec.OP_SUBSTITUTION, "far"),
    ]
    table = {entry["stratum"]: entry for entry in group_table(rows, "stratum")}
    assert table["near"]["improvement_points"] == pytest.approx(100.0)
    assert table["far"]["improvement_points"] == pytest.approx(-100.0)
    assert table["near"]["words"] == 1
