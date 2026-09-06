"""``numeric-value-accuracy-v1``: did the numbers survive the transcription?

Owner ruling 2026-09-06: "WER is not a reasonable speech-agentic task".
Corpus WER stays the alignment anchor against the published Earnings-21 rows,
but the paper-facing line for Earnings mechanisms becomes entity-level metrics
plus a semantic error rate. Earnings calls are number-dense and the numbers are
the payload -- a transcript that renders every word but moves a guidance figure
is a worse agent output than one that fumbles a filler.

DEFINITION
----------
Both sides are normalized once, as whole strings, with the vendored Whisper
``EnglishTextNormalizer`` (``reproduction.asr_wer_whisper``) -- the SAME
normalization ``asr-wer-whisper`` applies, so the reference word population
here is exactly that scorer's own (359,765 words on the 44 Earnings-21
discovery calls) and the two numbers sit in the same normalizer family.

That normalizer is what makes "numbers, currencies, percentages and dates" a
single mechanical class rather than a taxonomy to invent: it expands spelled
numbers to digits ("twenty two" -> "22"), unifies currency ("one dollar
twenty" -> "$1.20"), unifies percentages ("five percent" -> "5%"), strips
thousands separators ("1,234" -> "1234") and leaves ordinals in digit form
("third" -> "3rd"). Every one of those lands as a token carrying at least one
ASCII digit, and nothing else in English earnings-call text does. So:

    a NUMERIC VALUE is a normalized word containing at least one ASCII digit.

Matching is a MULTISET (bag) match, not a positional one. For each distinct
numeric value ``v``, ``matched(v) = min(count in reference, count in
hypothesis)``; accuracy is ``sum(matched) / sum(reference count)``. Bag
matching is deliberate: the flight transcribes a call as 90-second windows and
concatenates, so a value can legitimately move a few words without being wrong,
and the question this metric asks is "was the figure carried across at all",
not "was it carried at the same offset". It is a RECALL: a hypothesis that
invents extra figures is not rewarded, and the count of those is reported
beside it as ``spurious_numeric_words`` so over-generation stays visible.

``by_kind`` splits the same counts into currency / percent / ordinal / decimal
/ year / integer / other, classified in that fixed order from the normalized
surface form alone. No gold entity annotation is consulted anywhere in this
metric: it needs only the reference transcript, so it applies unchanged to any
carrier with a reference layer.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, Mapping, Sequence

from .asr_wer_whisper import WHISPER_NORMALIZER_NAME, normalize_whisper_english

NUMERIC_VALUE_SCORER_VERSION = "numeric-value-accuracy-v1"

_DIGIT = re.compile(r"[0-9]")
_CURRENCY = re.compile(r"[$¢€£¥]")
_ORDINAL = re.compile(r"^[0-9]+(?:st|nd|rd|th)$")
_YEAR = re.compile(r"^(?:1[89][0-9]{2}|20[0-9]{2})$")
_INTEGER = re.compile(r"^[0-9]+$")
_DECIMAL = re.compile(r"^[0-9]*\.[0-9]+$|^[0-9]+\.[0-9]*$")

KINDS = ("currency", "percent", "ordinal", "decimal", "year", "integer", "other")


def is_numeric_value(word: str) -> bool:
    """A normalized word counts as a numeric value when it carries a digit."""

    return _DIGIT.search(word) is not None


def numeric_kind(word: str) -> str:
    """Fixed-order classification of one numeric value's surface form."""

    if _CURRENCY.search(word):
        return "currency"
    if "%" in word:
        return "percent"
    if _ORDINAL.match(word):
        return "ordinal"
    if _DECIMAL.match(word):
        return "decimal"
    if _YEAR.match(word):
        return "year"
    if _INTEGER.match(word):
        return "integer"
    return "other"


def numeric_values(words: Iterable[str]) -> list[str]:
    return [word for word in words if is_numeric_value(word)]


def whisper_words(text: str) -> list[str]:
    return normalize_whisper_english(text).split()


def reference_whisper_words(tokens: Sequence[str]) -> list[str]:
    return normalize_whisper_english(" ".join(tokens)).split()


def _rate(matched: int, expected: int) -> float:
    return (matched / expected) if expected else 0.0


def numeric_value_counts(
    reference_words: Sequence[str], hypothesis_words: Sequence[str]
) -> dict[str, object]:
    """Bag-match the reference's numeric values against the hypothesis's.

    Returns the pooled counts plus a ``by_kind`` block. Every count is an
    integer so a corpus figure can be summed from per-call rows and divided
    once (:func:`merge_numeric_counts`), never averaged across calls.
    """

    reference = Counter(numeric_values(reference_words))
    hypothesis = Counter(numeric_values(hypothesis_words))
    by_kind: dict[str, dict[str, int]] = {
        kind: {"expected": 0, "matched": 0, "hypothesis": 0} for kind in KINDS
    }
    expected_total = matched_total = 0
    for value, count in reference.items():
        matched = min(count, hypothesis.get(value, 0))
        kind = numeric_kind(value)
        by_kind[kind]["expected"] += count
        by_kind[kind]["matched"] += matched
        expected_total += count
        matched_total += matched
    hypothesis_total = 0
    for value, count in hypothesis.items():
        by_kind[numeric_kind(value)]["hypothesis"] += count
        hypothesis_total += count
    return {
        "expected_numeric_words": expected_total,
        "matched_numeric_words": matched_total,
        "hypothesis_numeric_words": hypothesis_total,
        "spurious_numeric_words": hypothesis_total - matched_total,
        "reference_words": len(reference_words),
        "hypothesis_words": len(hypothesis_words),
        "accuracy": _rate(matched_total, expected_total),
        "by_kind": {
            kind: {
                **values,
                "accuracy": _rate(values["matched"], values["expected"]),
            }
            for kind, values in by_kind.items()
        },
    }


def merge_numeric_counts(
    per_sample: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Pool per-call counts, then divide once."""

    totals = {
        "expected_numeric_words": 0,
        "matched_numeric_words": 0,
        "hypothesis_numeric_words": 0,
        "reference_words": 0,
        "hypothesis_words": 0,
    }
    kinds: dict[str, dict[str, int]] = {
        kind: {"expected": 0, "matched": 0, "hypothesis": 0} for kind in KINDS
    }
    samples = 0
    for row in per_sample:
        samples += 1
        for key in totals:
            totals[key] += int(row[key])  # type: ignore[arg-type]
        by_kind = row["by_kind"]
        assert isinstance(by_kind, Mapping)
        for kind, values in by_kind.items():
            for key in ("expected", "matched", "hypothesis"):
                kinds[kind][key] += int(values[key])
    return {
        **totals,
        "samples": samples,
        "spurious_numeric_words": (
            totals["hypothesis_numeric_words"] - totals["matched_numeric_words"]
        ),
        "accuracy": _rate(totals["matched_numeric_words"], totals["expected_numeric_words"]),
        "by_kind": {
            kind: {**values, "accuracy": _rate(values["matched"], values["expected"])}
            for kind, values in kinds.items()
        },
        "scorer_version": NUMERIC_VALUE_SCORER_VERSION,
        "normalizer": WHISPER_NORMALIZER_NAME,
    }
