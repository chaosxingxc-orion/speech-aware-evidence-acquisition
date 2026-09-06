"""``numeric-value-accuracy-v1``: the numeric-value contract, its bag match,
its kind classification, and hand-computed end-to-end numbers."""

import json

import pytest

from speech_aware_evidence_acquisition.core import scorers  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import SCORERS
from speech_aware_evidence_acquisition.core.scorers import (
    ScoringPhaseError,
    score_numeric_value_accuracy_outputs,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.numeric_value_accuracy import (
    NUMERIC_VALUE_SCORER_VERSION,
    is_numeric_value,
    merge_numeric_counts,
    numeric_kind,
    numeric_value_counts,
    reference_whisper_words,
    whisper_words,
)


def _write_nlp(path, tokens):
    lines = ["token|speaker|tags|wer_tags"]
    for token in tokens:
        lines.append(f"{token}|0||[]")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_outputs(tmp_path, rows):
    path = tmp_path / "y.outputs.jsonl"
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return path


def test_numeric_value_accuracy_is_registered():
    assert "numeric-value-accuracy-v1" in SCORERS.names()
    assert SCORERS.resolve("numeric-value-accuracy-v1") is score_numeric_value_accuracy_outputs


# ---------------------------------------------------------------------------
# What counts as a numeric value, and of which kind.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("word", ["2020", "$1.20", "5%", "3rd", "1234", "q1", "covid19"])
def test_digit_bearing_words_are_numeric_values(word):
    assert is_numeric_value(word) is True


@pytest.mark.parametrize("word", ["revenue", "quarter", "percent", "", "point"])
def test_digit_free_words_are_not_numeric_values(word):
    assert is_numeric_value(word) is False


@pytest.mark.parametrize(
    "word,kind",
    [
        ("$1.20", "currency"),
        ("5%", "percent"),
        ("3rd", "ordinal"),
        ("1.5", "decimal"),
        ("2020", "year"),
        ("1234", "integer"),
        ("q1", "other"),
    ],
)
def test_numeric_kind_classification(word, kind):
    assert numeric_kind(word) == kind


def test_the_whisper_normalizer_is_what_makes_spelled_numbers_numeric():
    # "twenty two million" is three digit-free words until the normalizer runs;
    # afterwards it is one numeric value.
    assert whisper_words("twenty two million") == ["22000000"]
    assert whisper_words("five percent") == ["5%"]
    assert numeric_value_counts(["22000000"], ["22000000"])["accuracy"] == 1.0


# ---------------------------------------------------------------------------
# The bag match itself.
# ---------------------------------------------------------------------------


def test_counts_are_a_multiset_recall_not_a_positional_match():
    reference = ["2020", "grew", "5%", "to", "$3.10"]
    # Same three values, different order, plus one figure the reference never had.
    hypothesis = ["$3.10", "5%", "in", "2020", "and", "7%"]
    counts = numeric_value_counts(reference, hypothesis)
    assert counts["expected_numeric_words"] == 3
    assert counts["matched_numeric_words"] == 3
    assert counts["accuracy"] == pytest.approx(1.0)
    assert counts["hypothesis_numeric_words"] == 4
    assert counts["spurious_numeric_words"] == 1


def test_a_repeated_value_is_matched_by_multiplicity():
    counts = numeric_value_counts(["5%", "5%", "5%"], ["5%", "5%"])
    assert counts["expected_numeric_words"] == 3
    assert counts["matched_numeric_words"] == 2
    assert counts["accuracy"] == pytest.approx(2 / 3)


def test_a_wrong_figure_is_a_miss_even_when_the_word_count_matches():
    counts = numeric_value_counts(["$3.10"], ["$3.20"])
    assert counts["matched_numeric_words"] == 0
    assert counts["accuracy"] == 0.0
    assert counts["spurious_numeric_words"] == 1


def test_by_kind_splits_the_same_counts():
    counts = numeric_value_counts(["2020", "5%", "$3.10"], ["2020", "6%", "$3.10"])
    by_kind = counts["by_kind"]
    assert by_kind["year"]["expected"] == 1 and by_kind["year"]["matched"] == 1
    assert by_kind["percent"]["expected"] == 1 and by_kind["percent"]["matched"] == 0
    assert by_kind["currency"]["accuracy"] == pytest.approx(1.0)
    assert sum(values["expected"] for values in by_kind.values()) == 3


def test_no_numeric_values_gives_accuracy_zero_without_dividing_by_zero():
    counts = numeric_value_counts(["revenue", "grew"], ["revenue", "grew"])
    assert counts["expected_numeric_words"] == 0
    assert counts["accuracy"] == 0.0


def test_merge_pools_counts_and_divides_once():
    left = numeric_value_counts(["5%"], ["5%"])
    right = numeric_value_counts(["2020", "2021", "2022"], ["1999", "1998", "1997"])
    merged = merge_numeric_counts([left, right])
    # Pooled 1/4, not the mean of 1.0 and 0.0.
    assert merged["accuracy"] == pytest.approx(0.25)
    assert merged["expected_numeric_words"] == 4
    assert merged["samples"] == 2
    assert merged["scorer_version"] == NUMERIC_VALUE_SCORER_VERSION


# ---------------------------------------------------------------------------
# End to end.
# ---------------------------------------------------------------------------


def test_end_to_end_hand_computed(synthetic_world, tmp_path):
    tokens = ["Revenue", "grew", "five", "percent", "in", "2020", "to", "three", "billion"]
    _write_nlp(synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp", tokens)
    reference = reference_whisper_words(tokens)
    # The normalizer turns "five percent" into "5%" and leaves "3 billion".
    assert "5%" in reference and "2020" in reference

    outputs = _write_outputs(
        tmp_path,
        [
            {
                "sample_id": "4000001",
                "carrier_lock_key": "earnings21-original",
                "text": "revenue grew six percent in 2020 to three billion",
            }
        ],
    )
    lock = load_lock(synthetic_world.lock_path)
    scores = score_numeric_value_accuracy_outputs(outputs, lock, synthetic_world.data_root)

    sample = scores["per_sample"][0]
    assert sample["sample_id"] == "4000001"
    expected = sample["expected_numeric_words"]
    assert expected == len([word for word in reference if any(c.isdigit() for c in word)])
    # Exactly one figure moved (5% -> 6%); everything else carried across.
    assert sample["matched_numeric_words"] == expected - 1
    assert scores["aggregate"]["accuracy"] == pytest.approx((expected - 1) / expected)
    assert scores["aggregate"]["samples"] == 1


def test_end_to_end_refuses_a_missing_reference(synthetic_world, tmp_path):
    outputs = _write_outputs(
        tmp_path,
        [{"sample_id": "9999999", "carrier_lock_key": "earnings21-original", "text": "hi"}],
    )
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ScoringPhaseError, match="cannot resolve references"):
        score_numeric_value_accuracy_outputs(outputs, lock, synthetic_world.data_root)
