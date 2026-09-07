"""``brief-term-recall-v1``: coverage, recall and the per-field table.

Synthetic references and hypotheses throughout -- the metric is arithmetic over
two word sequences and a five-field term set, and this file asserts that
arithmetic rather than any corpus number.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.reproduction import brief_term_recall as btr

TERMS = {
    "Ticker symbol": "COST",
    "Country": "United States",
    "UN region": "Europe and Northern America",
    "Major dialect family": "North American",
    "Language family and area": "English",
}


def test_the_scorer_is_registered_under_its_preregistered_id():
    assert SCORERS.resolve("brief-term-recall-v1") is btr.score_brief_term_recall_outputs


def test_terms_normalize_to_word_tuples():
    tuples = btr.term_tuples(TERMS)
    assert tuples["Ticker symbol"] == (("cost",),)
    assert tuples["Country"] == (("united", "states"),)
    assert tuples["UN region"] == (("europe", "and", "northern", "america"),)


def test_coverage_matches_multi_word_terms_as_contiguous_ngrams():
    words = btr.whisper_words("we grew in the United States and in Europe and Northern America")
    cover = btr.cover_reference(words, btr.term_tuples(TERMS))
    assert cover[words.index("united")] == "Country"
    assert cover[words.index("united") + 1] == "Country"
    start = words.index("europe")
    assert cover[start : start + 4] == ["UN region"] * 4
    assert cover[0] is None


def test_the_longest_term_wins_at_a_position():
    terms = dict(TERMS, **{"Ticker symbol": "North", "Major dialect family": "North American"})
    words = btr.whisper_words("our north american segment")
    cover = btr.cover_reference(words, btr.term_tuples(terms))
    assert cover[1:3] == ["Major dialect family"] * 2


def test_recall_counts_a_covered_word_only_when_the_alignment_hits_it():
    counts = btr.clip_counts(
        "we operate in the United States and in India",
        "we operate in the United Kingdom and in India",
        dict(TERMS, Country="United States"),
    )
    assert counts["brief_term_reference_words"] == 2
    assert counts["brief_term_hits"] == 1
    assert counts["recall"] == pytest.approx(0.5)


def test_a_deleted_term_word_is_not_recalled():
    counts = btr.clip_counts(
        "revenue in the United States rose",
        "revenue rose",
        TERMS,
    )
    assert counts["brief_term_reference_words"] == 2
    assert counts["brief_term_hits"] == 0


def test_a_clip_with_no_term_word_contributes_no_denominator():
    counts = btr.clip_counts("nothing here at all", "nothing here at all", TERMS)
    assert counts["brief_term_reference_words"] == 0
    assert counts["recall"] == 0.0
    assert counts["reference_words"] == 4


def test_the_aggregate_is_pooled_not_a_mean_of_per_clip_rates():
    long_clip = btr.clip_counts(
        "united states united states united states",
        "united states united states united states",
        TERMS,
    )
    short_clip = btr.clip_counts("united states", "united kingdom", TERMS)
    aggregate = btr.merge_counts([long_clip, short_clip])
    # Pooled: 7 hits of 8 covered words (the short clip keeps "united" and
    # substitutes "states"), NOT the mean of the two clips' 1.0 and 0.5.
    assert aggregate["brief_term_reference_words"] == 8
    assert aggregate["brief_term_hits"] == 7
    assert aggregate["brief_term_recall"] == pytest.approx(0.875)
    assert (long_clip["recall"] + short_clip["recall"]) / 2 == pytest.approx(0.75)


def test_the_per_field_table_keeps_a_fixed_row_order():
    aggregate = btr.merge_counts(
        [btr.clip_counts("united states and english", "united states and english", TERMS)]
    )
    assert [row["field"] for row in aggregate["per_field"]] == list(btr.FIELD_LABELS)
    by_field = {row["field"]: row for row in aggregate["per_field"]}
    assert by_field["Country"]["reference_words"] == 2
    assert by_field["Language family and area"]["reference_words"] == 1
    assert by_field["Ticker symbol"]["reference_words"] == 0


def test_the_homograph_is_counted_rather_than_excluded():
    """``COST`` normalizes to ``cost``, ordinary earnings vocabulary. The metric
    does not special-case it -- it counts it, which dilutes an effect and biases
    neither arm, and the audit's own diagnostic is what makes that visible."""

    counts = btr.clip_counts(
        "the cost of goods sold rose", "the cost of goods sold rose", TERMS
    )
    assert counts["brief_term_reference_words"] == 1
    assert counts["brief_term_hits"] == 1


def test_a_field_with_no_text_value_is_refused():
    with pytest.raises(btr.BriefTermRecallError, match="no text value"):
        btr.term_tuples(dict(TERMS, Country=None))
