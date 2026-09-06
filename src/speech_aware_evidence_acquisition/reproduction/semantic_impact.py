"""``semantic-high-impact-error-rate-v1``: the hook, and its taxonomy contract.

Owner ruling 2026-09-06 makes the paper-facing Earnings line "entity-level
metrics with published numbers plus a semantic high-impact error rate". The
TAXONOMY that decides which errors are high-impact is not this module's to
invent: it is the deliverable of the Earnings-22 semantic scan (branch
``wt/e22``, in progress). This module is the metric and the file interface the
scan has to satisfy -- so the scan can land a taxonomy and every Earnings cell
gets its number without another code change, and so nothing here silently
guesses an impact level in the meantime.

**Its Earnings-21 value is therefore NOT computed yet.** The registered scorer
``semantic-high-impact-error-rate-v1`` fails closed, by name, until the scan's
taxonomy file lands at :data:`ACTIVE_TAXONOMY_RELPATH`.

METRIC
------
    high-impact error rate = HIGH-impact reference-word mass / reference words

Both sides are Whisper-normalized as whole strings (the ``asr-wer-whisper``
convention, so the denominator is the same reference-word population as the
corpus WER anchor) and aligned with the same operation trace the ConEC mirror
uses (``reproduction.conec_entity_scoring.aligned_operations``). Every
reference word that is not a hit is one ERROR INSTANCE carrying one reference
word of mass:

* a substitution contributes ``(reference word, hypothesis word)``;
* a deletion contributes ``(reference word, "<deleted>")``.

An insertion carries NO reference word, so it contributes zero mass by
construction -- the metric is a fraction of the reference, and an inserted word
is not part of it. Insertions are still classified and reported separately as
``high_impact_insertions`` so an over-generating arm cannot hide behind a
denominator it does not appear in.

TAXONOMY FILE INTERFACE (schema ``saea-semantic-impact-taxonomy-v1``)
---------------------------------------------------------------------
A single JSON object::

    {
      "schema": "saea-semantic-impact-taxonomy-v1",
      "taxonomy_id": "e22-semantic-scan-<date>",
      "normalizer": "whisper-english-v20240930",
      "levels": ["HIGH", "MEDIUM", "LOW"],
      "high_level": "HIGH",
      "rules": [
        {"id": "r1", "level": "HIGH",   "ref": "billion", "hyp": "million"},
        {"id": "r2", "level": "HIGH",   "ref": "guidance", "hyp": "*"},
        {"id": "r3", "level": "LOW",    "ref": "*", "hyp": "<deleted>"},
        {"id": "r4", "level": "MEDIUM", "ref": "*", "hyp": "*"}
      ]
    }

* ``ref`` is an exact NORMALIZED reference word or the wildcard ``"*"``.
* ``hyp`` is an exact normalized hypothesis word, the wildcard ``"*"``, or the
  sentinel :data:`DELETED` for "the word was dropped". ``"*"`` on the
  hypothesis side matches a deletion too.
* ``level`` must be one of ``levels``; ``high_level`` names the one that goes
  in the numerator (default ``"HIGH"``).
* ``normalizer`` must name the normalizer the taxonomy was built under, and it
  must equal this repository's vendored one -- a taxonomy authored against a
  different normalization would classify strings that never occur.

LOOKUP is by exact key, in one fixed order of decreasing specificity:
``(ref, hyp)``, then ``(ref, "*")``, then ``("*", hyp)``, then ``("*", "*")``.
The first key present wins, so a rule can never be shadowed ambiguously and the
result does not depend on file order. Two rules sharing a key are a load-time
error, not a silent last-one-wins. An error instance no key matches is counted
under ``unclassified_reference_words`` and reaches no level -- so a partial
taxonomy under-reports visibly instead of assuming LOW.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .asr_wer_whisper import WHISPER_NORMALIZER_NAME
from .conec_entity_scoring import (
    OP_DELETION,
    OP_HIT,
    OP_INSERTION,
    OP_SUBSTITUTION,
)

SEMANTIC_IMPACT_SCORER_VERSION = "semantic-high-impact-error-rate-v1"
TAXONOMY_SCHEMA = "saea-semantic-impact-taxonomy-v1"

ACTIVE_TAXONOMY_RELPATH = "docs/taxonomies/semantic-high-impact/ACTIVE.json"
"""Where the registered scorer looks for the Earnings-22 scan's taxonomy,
relative to the study checkout. Absent today, deliberately."""

DELETED = "<deleted>"
"""Hypothesis-side sentinel for a deleted reference word."""

WILDCARD = "*"

UNCLASSIFIED = "__UNCLASSIFIED__"


class TaxonomyError(RuntimeError):
    """The taxonomy file is missing, malformed, or built for another normalizer."""


@dataclass(frozen=True)
class ImpactTaxonomy:
    """A loaded, validated taxonomy: an exact-key rule index plus its levels."""

    taxonomy_id: str
    levels: tuple[str, ...]
    high_level: str
    rules: Mapping[tuple[str, str], tuple[str, str]]
    normalizer: str

    def classify(self, reference_word: str, hypothesis_word: str) -> tuple[str, str]:
        """The (level, rule id) for one error instance, or
        ``(UNCLASSIFIED, "")`` when no key matches."""

        for key in (
            (reference_word, hypothesis_word),
            (reference_word, WILDCARD),
            (WILDCARD, hypothesis_word),
            (WILDCARD, WILDCARD),
        ):
            found = self.rules.get(key)
            if found is not None:
                return found
        return (UNCLASSIFIED, "")


def load_taxonomy(path: Path) -> ImpactTaxonomy:
    """Read and validate a taxonomy file. Fails closed on every defect."""

    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise TaxonomyError(f"cannot read semantic-impact taxonomy {path}: {error}") from error
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as error:
        raise TaxonomyError(f"semantic-impact taxonomy {path} is not valid JSON: {error}") from error
    if not isinstance(document, Mapping) or document.get("schema") != TAXONOMY_SCHEMA:
        raise TaxonomyError(
            f"semantic-impact taxonomy {path} must be an object carrying schema {TAXONOMY_SCHEMA!r}"
        )
    taxonomy_id = document.get("taxonomy_id")
    if not isinstance(taxonomy_id, str) or not taxonomy_id.strip():
        raise TaxonomyError(f"semantic-impact taxonomy {path} lacks a usable taxonomy_id")
    normalizer = document.get("normalizer")
    if normalizer != WHISPER_NORMALIZER_NAME:
        raise TaxonomyError(
            f"semantic-impact taxonomy {path} declares normalizer {normalizer!r}; this metric "
            f"classifies words normalized by {WHISPER_NORMALIZER_NAME!r} and refuses a taxonomy "
            "authored under another one"
        )
    levels = document.get("levels")
    if (
        not isinstance(levels, list)
        or not levels
        or not all(isinstance(level, str) and level.strip() for level in levels)
        or len(set(levels)) != len(levels)
    ):
        raise TaxonomyError(
            f"semantic-impact taxonomy {path} levels must be a non-empty list of distinct names"
        )
    high_level = document.get("high_level", "HIGH")
    if high_level not in levels:
        raise TaxonomyError(
            f"semantic-impact taxonomy {path} high_level {high_level!r} is not one of {levels}"
        )
    rules_value = document.get("rules")
    if not isinstance(rules_value, list) or not rules_value:
        raise TaxonomyError(f"semantic-impact taxonomy {path} carries no rules")
    rules: dict[tuple[str, str], tuple[str, str]] = {}
    for index, rule in enumerate(rules_value):
        if not isinstance(rule, Mapping) or set(rule) != {"id", "level", "ref", "hyp"}:
            raise TaxonomyError(
                f"semantic-impact taxonomy {path} rule {index} must carry exactly "
                "id, level, ref and hyp"
            )
        rule_id, level, reference, hypothesis = (
            rule["id"],
            rule["level"],
            rule["ref"],
            rule["hyp"],
        )
        for name, value in (("id", rule_id), ("ref", reference), ("hyp", hypothesis)):
            if not isinstance(value, str) or not value:
                raise TaxonomyError(
                    f"semantic-impact taxonomy {path} rule {index} has a non-string {name}"
                )
        if level not in levels:
            raise TaxonomyError(
                f"semantic-impact taxonomy {path} rule {rule_id!r} has level {level!r} "
                f"outside {levels}"
            )
        key = (str(reference), str(hypothesis))
        if key in rules:
            raise TaxonomyError(
                f"semantic-impact taxonomy {path} has two rules on key {key}; the lookup is by "
                "exact key, so a duplicate is ambiguous rather than an override"
            )
        rules[key] = (str(level), str(rule_id))
    return ImpactTaxonomy(
        taxonomy_id=str(taxonomy_id),
        levels=tuple(levels),
        high_level=str(high_level),
        rules=rules,
        normalizer=str(normalizer),
    )


def semantic_impact_counts(
    operations: Sequence[tuple[str, int | None, int | None]],
    reference_words: Sequence[str],
    hypothesis_words: Sequence[str],
    taxonomy: ImpactTaxonomy,
) -> dict[str, object]:
    """HIGH-impact reference-word mass over reference words, for one sample."""

    by_level: dict[str, int] = {level: 0 for level in taxonomy.levels}
    by_level[UNCLASSIFIED] = 0
    insertions_by_level: dict[str, int] = {level: 0 for level in taxonomy.levels}
    insertions_by_level[UNCLASSIFIED] = 0
    by_rule: dict[str, int] = {}
    reference_total = 0
    for kind, reference_index, hypothesis_index in operations:
        if kind == OP_HIT:
            reference_total += 1
            continue
        if kind == OP_INSERTION:
            assert hypothesis_index is not None
            level, _ = taxonomy.classify(WILDCARD, hypothesis_words[hypothesis_index])
            insertions_by_level[level] = insertions_by_level.get(level, 0) + 1
            continue
        reference_total += 1
        assert reference_index is not None
        reference_word = reference_words[reference_index]
        if kind == OP_SUBSTITUTION:
            assert hypothesis_index is not None
            hypothesis_word = hypothesis_words[hypothesis_index]
        elif kind == OP_DELETION:
            hypothesis_word = DELETED
        else:  # pragma: no cover - operation_counts already refuses this
            raise TaxonomyError(f"unknown alignment operation {kind!r}")
        level, rule_id = taxonomy.classify(reference_word, hypothesis_word)
        by_level[level] = by_level.get(level, 0) + 1
        if rule_id:
            by_rule[rule_id] = by_rule.get(rule_id, 0) + 1
    high = by_level.get(taxonomy.high_level, 0)
    return {
        "taxonomy_id": taxonomy.taxonomy_id,
        "reference_words": reference_total,
        "high_impact_reference_words": high,
        "high_impact_error_rate": (high / reference_total) if reference_total else 0.0,
        "unclassified_reference_words": by_level.get(UNCLASSIFIED, 0),
        "high_impact_insertions": insertions_by_level.get(taxonomy.high_level, 0),
        "reference_words_by_level": dict(sorted(by_level.items())),
        "insertions_by_level": dict(sorted(insertions_by_level.items())),
        "reference_words_by_rule": dict(sorted(by_rule.items())),
    }


def merge_semantic_counts(
    per_sample: Iterable[Mapping[str, object]], taxonomy: ImpactTaxonomy
) -> dict[str, object]:
    """Pool per-sample counts, then divide once."""

    reference_total = high = unclassified = high_insertions = 0
    by_level: dict[str, int] = {}
    insertions_by_level: dict[str, int] = {}
    by_rule: dict[str, int] = {}
    samples = 0
    for row in per_sample:
        samples += 1
        reference_total += int(row["reference_words"])  # type: ignore[arg-type]
        high += int(row["high_impact_reference_words"])  # type: ignore[arg-type]
        unclassified += int(row["unclassified_reference_words"])  # type: ignore[arg-type]
        high_insertions += int(row["high_impact_insertions"])  # type: ignore[arg-type]
        for source, target in (
            (row["reference_words_by_level"], by_level),
            (row["insertions_by_level"], insertions_by_level),
            (row["reference_words_by_rule"], by_rule),
        ):
            assert isinstance(source, Mapping)
            for key, value in source.items():
                target[key] = target.get(key, 0) + int(value)
    return {
        "scorer_version": SEMANTIC_IMPACT_SCORER_VERSION,
        "normalizer": WHISPER_NORMALIZER_NAME,
        "taxonomy_id": taxonomy.taxonomy_id,
        "samples": samples,
        "reference_words": reference_total,
        "high_impact_reference_words": high,
        "high_impact_error_rate": (high / reference_total) if reference_total else 0.0,
        "unclassified_reference_words": unclassified,
        "high_impact_insertions": high_insertions,
        "reference_words_by_level": dict(sorted(by_level.items())),
        "insertions_by_level": dict(sorted(insertions_by_level.items())),
        "reference_words_by_rule": dict(sorted(by_rule.items())),
    }
