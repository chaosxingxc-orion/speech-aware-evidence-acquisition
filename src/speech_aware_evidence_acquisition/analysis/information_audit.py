"""Generic, carrier-agnostic model-free dataset information audit.

Part B ("dataset information audit: one template, three carriers") of the
2026-09-03 recovery plan. This module answers the SAME eight standing
questions about task information supply for any carrier that hands it a
:class:`~.information_audit_specs.CarrierInformationSpec`:

1. Per-item fields / per-corpus structures and their legality class.
2. Task information requirement decomposed by OBS / ORG / SUPPLY / USE.
3. Natural population distribution and each evaluation roster's deviation
   from it (equal-stratum stress roster vs natural mixture).
4. Label-space entropy and prior-mass coverage.
5. Retrieval-reachability upper bounds -- label-blind grouped out-of-fold
   BM25 coverage@k for a shared construction corpus
   (``retrieval_mode="grouped_bm25"``), or direct own-call-vs-random-other-
   call membership reachability for a self-supplied evidence carrier
   (``retrieval_mode="self_supplied_membership"``).
6. Decontamination: identity overlap between the knowledge source and every
   evaluation roster, plus (for a self-supplied carrier) cross-call
   near-duplicate evidence.
7. External supplementation ledger.
8. Power: minimum detectable paired effect at the intended n, via a
   paired-binomial normal approximation to McNemar's test, using the
   historical discordant-pair rates recorded in ``HISTORICAL_DISCORDANCE_
   CITATIONS`` below.

Every question is a pure function over plain data (dicts, sequences,
mappings) so each is unit-testable on synthetic rows without touching any
governed dataset. Reused, not re-implemented: :class:`.a2t_lexical_ceiling.
Bm25Index` / :func:`.a2t_lexical_ceiling.tokenize` (carrier-blind BM25) and
:func:`.a2t_label_candidate_reduction.candidate_sample_metrics`
(carrier-blind coverage@k/recall/precision/distractor-burden on a
``{"required_tool_names", "ranked_tool_names", "positive_score_tool_names"}``
sample -- the field names are historical, not A2T-specific: this module
builds exactly that shape for whichever label vocabulary a carrier uses).
The label-blind grouped-fold union-find assignment
(:func:`assign_grouped_folds`) mirrors
``analysis.a2t_grouped_candidate_validation.assign_grouped_validation_folds``
but is reimplemented here directly over generic rows, because that module
hard-requires ``A2tKbRow`` instances (``isinstance`` checks) and is
therefore A2T-bound, not carrier-agnostic.

Zero model, GPU, scorer, embedding, or network contact. This module never
imports ``data.references`` (that import is restricted to
``core/scorers.py`` by ``tests/contract/test_reference_import_isolation.py``)
and never emits utterance text, reference transcripts, entity fillers, or
gold values -- only counts, shares, hashes, and derived rates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from statistics import NormalDist
from typing import Callable, Mapping, Sequence

from .a2t_label_candidate_reduction import candidate_sample_metrics
from .a2t_lexical_ceiling import Bm25Index, tokenize
from .information_audit_specs import (
    LEGALITY_CLASSES,
    CarrierInformationSpec,
    EvaluationRoster,
)

AUDIT_SCHEMA = "saea-carrier-information-audit-v1"
DEFAULT_SEED = 20260903
DEFAULT_KS = (5, 16, 32, 64)
DEFAULT_FOLD_COUNT = 5
NEAR_DUPLICATE_THRESHOLD = 0.80
_MASS_THRESHOLDS = (0.50, 0.80, 0.90, 0.95, 0.99, 1.00)
_TOP_K_REPORT = (1, 3, 5, 10, 20, 50, 100)

#: Historical paired-outcome discordant-pair rates from the two sealed SLURP
#: DEV-ladder verdicts this recovery plan names as Q8's empirical basis.
#: Both carriers' power tables use these rates: Earnings21+ConEC has no
#: sealed paired verdict of its own yet at the 44-call discovery scale, so
#: these are the best available empirical discordance-rate estimates,
#: explicitly cited as borrowed cross-task evidence in that carrier's own
#: README/readiness note.
HISTORICAL_DISCORDANCE_CITATIONS: tuple[Mapping[str, object], ...] = (
    {
        "label": "DEV-500 confirmatory (400 unexposed)",
        "n": 400,
        "wrong_to_correct": 81,
        "correct_to_wrong": 2,
        "discordant_rate": (81 + 2) / 400,
        "source": "docs/readiness/2026-08-24-dev500-confirmatory-verdict.md",
    },
    {
        "label": "DEV-1000 baseline lock (500 unexposed)",
        "n": 500,
        "wrong_to_correct": 106,
        "correct_to_wrong": 5,
        "discordant_rate": (106 + 5) / 500,
        "source": "docs/readiness/2026-08-25-baseline-lock-verdict.md",
    },
)


class InformationAuditError(ValueError):
    """An audit input, row, or invocation is malformed -- fail closed."""


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _validate_rows(rows: Sequence[Mapping[str, object]], *, label: str) -> tuple[Mapping[str, object], ...]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise InformationAuditError(f"{label} must be a non-empty sequence of row mappings")
    ordered = tuple(rows)
    ids: set[str] = set()
    for row in ordered:
        if not isinstance(row, Mapping) or "item_id" not in row:
            raise InformationAuditError(f"{label} rows must be mappings carrying 'item_id'")
        item_id = row["item_id"]
        if not isinstance(item_id, str) or not item_id:
            raise InformationAuditError(f"{label} row item_id must be non-empty text")
        if item_id in ids:
            raise InformationAuditError(f"{label} has a duplicate item_id {item_id!r}")
        ids.add(item_id)
    return ordered


# ---------------------------------------------------------------------------
# Q1: per-item fields / per-corpus structures and their legality class
# ---------------------------------------------------------------------------


def field_catalog(
    field_legality: Mapping[str, str], corpus_structure_legality: Mapping[str, str]
) -> dict[str, object]:
    """A JSON-compatible catalog of per-item fields and per-corpus
    structures, each tagged with its legality class. Pure passthrough +
    shape validation -- the legality values themselves are validated once,
    at spec-construction time, by ``CarrierInformationSpec.__post_init__``."""

    for label, mapping in (("field_legality", field_legality), ("corpus_structure_legality", corpus_structure_legality)):
        if not isinstance(mapping, Mapping):
            raise InformationAuditError(f"{label} must be a mapping")
        for key, value in mapping.items():
            if value not in LEGALITY_CLASSES:
                raise InformationAuditError(f"{label}[{key!r}] = {value!r} is not a legal legality class")
    return {
        "legality_classes": sorted(LEGALITY_CLASSES),
        "fields": dict(sorted(field_legality.items())),
        "corpus_structures": dict(sorted(corpus_structure_legality.items())),
    }


# ---------------------------------------------------------------------------
# Q2: task information requirement decomposed by OBS / ORG / SUPPLY / USE
# ---------------------------------------------------------------------------


def task_information_decomposition(task_kind: str, obs_org_supply_use: Mapping[str, str]) -> dict[str, object]:
    if not isinstance(task_kind, str) or not task_kind:
        raise InformationAuditError("task_kind must be non-empty text")
    if set(obs_org_supply_use) != {"obs", "org", "supply", "use"}:
        raise InformationAuditError("obs_org_supply_use must carry exactly obs/org/supply/use")
    return {"task_kind": task_kind, **{key: str(value) for key, value in obs_org_supply_use.items()}}


# ---------------------------------------------------------------------------
# Q3: natural population distribution + roster deviation
# ---------------------------------------------------------------------------


def stratum_histogram(
    rows: Sequence[Mapping[str, object]], *, stratum_of: Callable[[Mapping[str, object]], str]
) -> dict[str, int]:
    rows = _validate_rows(rows, label="rows")
    counts: Counter[str] = Counter()
    for row in rows:
        stratum = stratum_of(row)
        if not isinstance(stratum, str) or not stratum:
            raise InformationAuditError("stratum_of must return non-empty text")
        counts[stratum] += 1
    return dict(sorted(counts.items()))


def population_distribution(stratum_counts: Mapping[str, int]) -> dict[str, object]:
    if not isinstance(stratum_counts, Mapping) or not stratum_counts:
        raise InformationAuditError("stratum_counts must be a non-empty mapping")
    total = sum(stratum_counts.values())
    if total <= 0:
        raise InformationAuditError("stratum_counts must sum to a positive total")
    shares = {stratum: count / total for stratum, count in stratum_counts.items()}
    return {
        "counts": dict(sorted(stratum_counts.items())),
        "total": total,
        "shares": dict(sorted(shares.items())),
        "stratum_count": len(stratum_counts),
    }


def roster_deviation(
    natural_shares: Mapping[str, float], roster_counts: Mapping[str, int]
) -> dict[str, object]:
    """Total-variation distance of a roster's per-stratum shares from the
    natural (construction-population) shares, and from a perfectly equal
    per-stratum allocation -- whichever is smaller names the roster's own
    design (an "equal-stratum stress roster" vs a "natural-mixture roster"),
    exactly the distinction the recovery plan's Q3 asks for."""

    if not isinstance(natural_shares, Mapping) or not natural_shares:
        raise InformationAuditError("natural_shares must be a non-empty mapping")
    if not isinstance(roster_counts, Mapping) or not roster_counts:
        raise InformationAuditError("roster_counts must be a non-empty mapping")
    roster_total = sum(roster_counts.values())
    if roster_total <= 0:
        raise InformationAuditError("roster_counts must sum to a positive total")
    roster_shares = {stratum: count / roster_total for stratum, count in roster_counts.items()}
    strata = sorted(set(natural_shares) | set(roster_shares))
    tvd_from_natural = 0.5 * sum(
        abs(roster_shares.get(stratum, 0.0) - natural_shares.get(stratum, 0.0)) for stratum in strata
    )
    uniform_share = 1.0 / len(roster_shares)
    tvd_from_uniform = 0.5 * sum(
        abs(roster_shares.get(stratum, 0.0) - (uniform_share if stratum in roster_shares else 0.0))
        for stratum in strata
    )
    if abs(tvd_from_uniform - tvd_from_natural) < 1e-9:
        classification = "ambiguous"
    elif tvd_from_uniform < tvd_from_natural:
        classification = "near-equal-stratum"
    else:
        classification = "near-natural-mixture"
    return {
        "roster_total": roster_total,
        "roster_shares": dict(sorted(roster_shares.items())),
        "total_variation_distance_from_natural": tvd_from_natural,
        "total_variation_distance_from_uniform_allocation": tvd_from_uniform,
        "classification": classification,
    }


# ---------------------------------------------------------------------------
# Q4: label-space entropy and prior-mass coverage
# ---------------------------------------------------------------------------


def label_space_entropy_from_counts(
    counts: Mapping[str, int], *, top_k: Sequence[int] = _TOP_K_REPORT
) -> dict[str, object]:
    if not isinstance(counts, Mapping) or not counts:
        raise InformationAuditError("counts must be a non-empty mapping")
    for label, count in counts.items():
        if not isinstance(label, str) or not label:
            raise InformationAuditError("counts keys must be non-empty text")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise InformationAuditError(f"counts[{label!r}] must be a non-negative int")
    total = sum(counts.values())
    if total <= 0:
        raise InformationAuditError("counts must sum to a positive total")
    ranked = sorted((label for label, count in counts.items() if count > 0), key=lambda label: (-counts[label], label))
    if not ranked:
        raise InformationAuditError("counts has no positive-count label")
    probabilities = [counts[label] / total for label in ranked]
    entropy_bits = -sum(p * math.log2(p) for p in probabilities)
    effective_label_count = 2.0**entropy_bits
    label_count = len(counts)
    normalized_entropy = entropy_bits / math.log2(label_count) if label_count > 1 else 0.0
    cumulative: list[float] = []
    running = 0
    for label in ranked:
        running += counts[label]
        cumulative.append(running / total)
    minimum_k_for_mass: dict[str, int] = {}
    for rank, mass in enumerate(cumulative, start=1):
        for threshold in _MASS_THRESHOLDS:
            key = f"{threshold:.2f}"
            if key not in minimum_k_for_mass and mass >= threshold - 1e-12:
                minimum_k_for_mass[key] = rank
    top_k_mass = {
        str(k): cumulative[min(k, len(cumulative)) - 1] for k in top_k if k >= 1
    }
    return {
        "label_count": label_count,
        "observed_label_count": len(ranked),
        "total_occurrences": total,
        "entropy_bits": entropy_bits,
        "effective_label_count": effective_label_count,
        "normalized_entropy": normalized_entropy,
        "top_k_mass": top_k_mass,
        "minimum_k_for_mass": minimum_k_for_mass,
    }


def label_field_entropy(
    rows: Sequence[Mapping[str, object]],
    *,
    labels_of: Callable[[Mapping[str, object]], Mapping[str, Sequence[str]]],
    label_fields: Sequence[str],
) -> dict[str, object]:
    rows = _validate_rows(rows, label="rows")
    result: dict[str, object] = {}
    for field in label_fields:
        counts: Counter[str] = Counter()
        for row in rows:
            counts.update(labels_of(row).get(field, ()))
        if counts:
            result[field] = label_space_entropy_from_counts(counts)
    if not result:
        raise InformationAuditError("no label_fields produced any occurrence")
    return result


# ---------------------------------------------------------------------------
# Q5, mode A: label-blind grouped out-of-fold BM25 coverage@k
# ---------------------------------------------------------------------------


def _union_find_components(
    item_ids: Sequence[str], signature_groups: Sequence[Sequence[tuple[object, str]]]
) -> tuple[tuple[str, ...], ...]:
    parent = {item_id: item_id for item_id in item_ids}

    def find(value: str) -> str:
        root = value
        while parent[root] != root:
            root = parent[root]
        while parent[value] != value:
            nxt = parent[value]
            parent[value] = root
            value = nxt
        return root

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root == right_root:
            return
        smaller, larger = sorted((left_root, right_root))
        parent[larger] = smaller

    for group in signature_groups:
        first_by_signature: dict[object, str] = {}
        for signature, item_id in group:
            first = first_by_signature.setdefault(signature, item_id)
            union(first, item_id)

    grouped: dict[str, list[str]] = {}
    for item_id in item_ids:
        grouped.setdefault(find(item_id), []).append(item_id)
    return tuple(sorted((tuple(sorted(members)) for members in grouped.values()), key=lambda members: members))


def label_blind_components(
    rows: Sequence[Mapping[str, object]],
    *,
    key_text_of: Callable[[Mapping[str, object]], str],
    group_of: Callable[[Mapping[str, object]], str],
) -> tuple[tuple[str, ...], ...]:
    """Connected components of rows that must stay in one fold together:
    same ``group_of`` value (e.g. a query block or utterance), same
    normalized key text, or the same BM25 token sequence -- the same three
    signature families
    ``analysis.a2t_grouped_candidate_validation._components`` unions,
    reimplemented here over generic rows (module docstring)."""

    rows = _validate_rows(rows, label="rows")
    item_ids = [row["item_id"] for row in rows]
    groups = [
        [(group_of(row), row["item_id"]) for row in rows],
        [(_normalize(key_text_of(row)), row["item_id"]) for row in rows],
        [(tokenize(key_text_of(row)), row["item_id"]) for row in rows],
    ]
    return _union_find_components(item_ids, groups)


def _component_hash(seed: int, members: Sequence[str]) -> str:
    payload = f"{seed}\0" + "\0".join(members)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assign_grouped_folds(
    rows: Sequence[Mapping[str, object]],
    *,
    key_text_of: Callable[[Mapping[str, object]], str],
    group_of: Callable[[Mapping[str, object]], str],
    seed: int,
    fold_count: int,
) -> tuple[tuple[str, ...], ...]:
    if type(fold_count) is not int or fold_count < 2:
        raise InformationAuditError("fold_count must be an int >= 2")
    components = label_blind_components(rows, key_text_of=key_text_of, group_of=group_of)
    if len(components) < fold_count:
        raise InformationAuditError(
            f"fold_count={fold_count} exceeds the {len(components)} label-blind components available"
        )
    ordered = sorted(components, key=lambda members: (_component_hash(seed, members), members[0]))
    folds: list[list[str]] = [[] for _ in range(fold_count)]
    loads = [0] * fold_count
    for members in ordered:
        target = min(range(fold_count), key=lambda index: (loads[index], index))
        folds[target].extend(members)
        loads[target] += len(members)
    result = tuple(tuple(sorted(fold)) for fold in folds)
    if any(not fold for fold in result):
        raise InformationAuditError("grouped fold assignment produced an empty fold")
    return result


def _required_labels(row: Mapping[str, object], *, labels_of, label_fields: Sequence[str]) -> tuple[str, ...]:
    values = labels_of(row)
    return tuple(dict.fromkeys(label for field in label_fields for label in values.get(field, ())))


def retrieval_reachability_grouped_bm25(
    rows: Sequence[Mapping[str, object]],
    *,
    key_text_of: Callable[[Mapping[str, object]], str],
    group_of: Callable[[Mapping[str, object]], str],
    labels_of: Callable[[Mapping[str, object]], Mapping[str, Sequence[str]]],
    label_fields: Sequence[str],
    stratum_of: Callable[[Mapping[str, object]], str],
    seed: int,
    fold_count: int,
    ks: Sequence[int],
) -> dict[str, object]:
    """Label-blind, grouped, 5-fold-by-default out-of-fold BM25 required-
    label-set coverage@k -- the SLURP/Audio2Tool Q5 protocol. Reuses
    :class:`.a2t_lexical_ceiling.Bm25Index` for scoring and
    :func:`.a2t_label_candidate_reduction.candidate_sample_metrics` for the
    coverage/recall/precision/distractor-burden metrics themselves."""

    rows = _validate_rows(rows, label="rows")
    k_values = tuple(sorted({int(k) for k in ks}))
    if not k_values or k_values[0] < 1:
        raise InformationAuditError("ks must contain positive integers")
    registry = sorted({label for row in rows for label in _required_labels(row, labels_of=labels_of, label_fields=label_fields)})
    if not registry:
        raise InformationAuditError("no row produced any required label")
    folds = assign_grouped_folds(rows, key_text_of=key_text_of, group_of=group_of, seed=seed, fold_count=fold_count)
    rows_by_id = {row["item_id"]: row for row in rows}

    all_samples: list[dict[str, object]] = []
    fold_reports: list[dict[str, object]] = []
    for fold_id, fold_ids in enumerate(folds):
        validation_set = frozenset(fold_ids)
        validation_rows = [rows_by_id[item_id] for item_id in fold_ids]
        build_rows = [row for row in rows if row["item_id"] not in validation_set]
        if not build_rows:
            raise InformationAuditError(f"fold {fold_id} has an empty build side")
        documents = tuple((row["item_id"], key_text_of(row)) for row in build_rows)
        index = Bm25Index.build(documents)
        labels_by_document = tuple(
            _required_labels(row, labels_of=labels_of, label_fields=label_fields) for row in build_rows
        )
        samples: list[dict[str, object]] = []
        for row in validation_rows:
            required = _required_labels(row, labels_of=labels_of, label_fields=label_fields)
            if not required:
                continue
            scores = index.scores(key_text_of(row))
            score_by_label = {label: 0.0 for label in registry}
            for document_index, score in scores.items():
                for label in labels_by_document[document_index]:
                    if score > score_by_label[label]:
                        score_by_label[label] = score
            ranking = sorted(registry, key=lambda label: (-score_by_label[label], label))
            positive = sorted(label for label in registry if score_by_label[label] > 0.0)
            samples.append(
                {
                    "item_id": row["item_id"],
                    "stratum": stratum_of(row),
                    "required_tool_names": list(required),
                    "ranked_tool_names": ranking,
                    "positive_score_tool_names": positive,
                }
            )
        if not samples:
            raise InformationAuditError(f"fold {fold_id} scored zero validation rows")
        all_samples.extend(samples)
        fold_reports.append(
            {
                "fold_id": fold_id,
                "build_units": len(build_rows),
                "validation_units": len(validation_rows),
                "scored_units": len(samples),
                "k_metrics": {
                    str(k): candidate_sample_metrics(samples, k=k, registry_count=len(registry)) for k in k_values
                },
            }
        )

    aggregate_metrics = {
        str(k): candidate_sample_metrics(all_samples, k=k, registry_count=len(registry)) for k in k_values
    }
    strata = sorted({str(sample["stratum"]) for sample in all_samples})
    per_stratum = {
        stratum: {
            str(k): candidate_sample_metrics(
                [sample for sample in all_samples if sample["stratum"] == stratum], k=k, registry_count=len(registry)
            )
            for k in k_values
        }
        for stratum in strata
    }
    worst_fold = {
        str(k): min(fold["k_metrics"][str(k)]["full_set_coverage"] for fold in fold_reports) for k in k_values
    }
    return {
        "mode": "grouped_bm25",
        "seed": seed,
        "fold_count": fold_count,
        "registry_label_count": len(registry),
        "scored_unit_count": len(all_samples),
        "folds": fold_reports,
        "aggregate": aggregate_metrics,
        "per_stratum": per_stratum,
        "worst_fold_full_set_coverage": worst_fold,
    }


# ---------------------------------------------------------------------------
# Q5, mode B: self-supplied own-call-vs-random-other-call membership
# ---------------------------------------------------------------------------


def deterministic_derangement(item_ids: Sequence[str], seed: int) -> dict[str, str]:
    """A seeded random cyclic permutation of ``item_ids`` -- guaranteed to
    have no fixed point (a derangement) whenever ``len(item_ids) >= 2``,
    used as the deterministic "random other call" pairing for the
    negative-control side of Q5's self-supplied membership check."""

    ordered = sorted(set(item_ids))
    if len(ordered) < 2:
        raise InformationAuditError("deterministic_derangement needs at least 2 distinct item ids")
    order = ordered[:]
    random.Random(seed).shuffle(order)
    n = len(order)
    return {order[index]: order[(index + 1) % n] for index in range(n)}


def retrieval_reachability_self_supplied(
    rows: Sequence[Mapping[str, object]],
    *,
    key_text_of: Callable[[Mapping[str, object]], str],
    labels_of: Callable[[Mapping[str, object]], Mapping[str, Sequence[str]]],
    mention_field: str,
    mention_separator: str,
    seed: int,
) -> dict[str, object]:
    """Direct own-call-vs-random-other-call membership reachability: for
    every gold ``(entity_type, normalized_filler)`` mention, is the
    normalized filler a substring of the call's own supplied evidence text
    (positive) versus a deterministically-paired random OTHER call's
    evidence text (negative control)? This is the Earnings21+ConEC Q5
    protocol -- there is no shared construction corpus to rank against, so
    BM25 grouped-fold retrieval (mode A above) does not apply."""

    rows = _validate_rows(rows, label="rows")
    pairing = deterministic_derangement([row["item_id"] for row in rows], seed)
    text_by_id = {row["item_id"]: _normalize(key_text_of(row)) for row in rows}

    total = 0
    own_present = 0
    other_present = 0
    per_type: dict[str, list[int]] = {}
    per_call: list[dict[str, object]] = []
    for row in rows:
        item_id = str(row["item_id"])
        own_text = text_by_id[item_id]
        other_text = text_by_id[pairing[item_id]]
        mentions = labels_of(row).get(mention_field, ())
        call_total = 0
        call_own = 0
        call_other = 0
        for entry in mentions:
            if mention_separator not in entry:
                raise InformationAuditError(f"mention entry {entry!r} lacks the mention separator")
            entity_type, filler = entry.split(mention_separator, 1)
            if not filler:
                continue
            total += 1
            call_total += 1
            present_own = filler in own_text
            present_other = filler in other_text
            own_present += int(present_own)
            other_present += int(present_other)
            call_own += int(present_own)
            call_other += int(present_other)
            bucket = per_type.setdefault(entity_type, [0, 0, 0])
            bucket[0] += 1
            bucket[1] += int(present_own)
            bucket[2] += int(present_other)
        per_call.append(
            {
                "item_id": item_id,
                "other_item_id": pairing[item_id],
                "mention_count": call_total,
                "own_context_present": call_own,
                "random_other_context_present": call_other,
            }
        )
    if total == 0:
        raise InformationAuditError("self-supplied reachability found zero mentions across all rows")
    return {
        "mode": "self_supplied_membership",
        "seed": seed,
        "item_count": len(rows),
        "mention_total": total,
        "own_context_reachability": own_present / total,
        "random_other_context_reachability": other_present / total,
        "per_entity_type": {
            entity_type: {
                "mention_count": counts[0],
                "own_context_reachability": counts[1] / counts[0],
                "random_other_context_reachability": counts[2] / counts[0],
            }
            for entity_type, counts in sorted(per_type.items())
        },
        "per_call": sorted(per_call, key=lambda entry: entry["item_id"]),
    }


# ---------------------------------------------------------------------------
# Q6: decontamination
# ---------------------------------------------------------------------------


def decontamination_identity(
    construction_ids: frozenset[str] | set[str], roster_ids: frozenset[str] | set[str]
) -> dict[str, object]:
    if not construction_ids:
        raise InformationAuditError("construction_ids must be non-empty")
    if not roster_ids:
        raise InformationAuditError("roster_ids must be non-empty")
    overlap = frozenset(construction_ids) & frozenset(roster_ids)
    return {
        "construction_count": len(construction_ids),
        "roster_count": len(roster_ids),
        "identity_overlap_count": len(overlap),
        "identity_overlap_sample": sorted(overlap)[:10],
        "clean": len(overlap) == 0,
    }


def near_duplicate_pairs(
    rows: Sequence[Mapping[str, object]],
    *,
    key_text_of: Callable[[Mapping[str, object]], str],
    threshold: float = NEAR_DUPLICATE_THRESHOLD,
) -> dict[str, object]:
    """Pairwise near-duplicate audit WITHIN one set of rows (token-set
    Jaccard >= ``threshold``) -- used for a self-supplied carrier's own
    cross-call template/boilerplate-reuse check (Earnings21+ConEC Q6)."""

    rows = _validate_rows(rows, label="rows")
    token_sets = {row["item_id"]: frozenset(tokenize(key_text_of(row))) for row in rows}
    ids = sorted(token_sets)
    pairs: list[dict[str, object]] = []
    for left_index in range(len(ids)):
        left = ids[left_index]
        left_tokens = token_sets[left]
        for right in ids[left_index + 1 :]:
            right_tokens = token_sets[right]
            union = len(left_tokens | right_tokens)
            if union == 0:
                continue
            jaccard = len(left_tokens & right_tokens) / union
            if jaccard >= threshold:
                pairs.append({"left": left, "right": right, "jaccard": jaccard})
    pairs.sort(key=lambda pair: (-float(pair["jaccard"]), str(pair["left"]), str(pair["right"])))
    return {
        "threshold": threshold,
        "metric": "token-set Jaccard",
        "item_count": len(ids),
        "pair_count": len(pairs),
        "pairs": pairs[:20],
    }


# ---------------------------------------------------------------------------
# Q7: external supplementation ledger
# ---------------------------------------------------------------------------


def external_supplementation_ledger(rows: Sequence[Mapping[str, str]]) -> dict[str, object]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise InformationAuditError("external_supplementation rows must be a non-empty sequence")
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != {"need", "source", "legality"}:
            raise InformationAuditError("external_supplementation rows must carry need/source/legality")
        if row["legality"] not in LEGALITY_CLASSES:
            raise InformationAuditError(f"external_supplementation legality {row['legality']!r} is invalid")
    return {"rows": [dict(row) for row in rows]}


# ---------------------------------------------------------------------------
# Q8: power (paired-binomial normal approximation to McNemar's test)
# ---------------------------------------------------------------------------


def minimum_detectable_paired_effect_pp(
    *, n: int, historical_discordant_rate: float, alpha: float = 0.05, power: float = 0.80
) -> dict[str, object]:
    """Minimum detectable paired accuracy delta (percentage points) at
    sample size ``n``, given a historical discordant-pair rate, for a
    two-sided McNemar test at significance ``alpha`` and target ``power``.

    Paired-binomial normal approximation: the expected discordant-pair
    count is ``m = n * historical_discordant_rate``; the minimum detectable
    departure of the discordant-pair split from 0.5 is the standard
    two-sided one-sample-proportion minimum-detectable-effect formula with
    pooled null variance, ``mde_p = (z_(alpha/2) + z_power) * sqrt(0.25 /
    m)``; converted back to an overall paired accuracy delta via
    ``mde_pp = historical_discordant_rate * 2 * mde_p * 100``. This is the
    same approximation family the study's own 104-row A2T flight cites
    (~12.3 pp at a 20/104 discordant rate, alpha=.05, 80% power)."""

    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise InformationAuditError("n must be a positive int")
    if not isinstance(historical_discordant_rate, (int, float)) or not (0.0 < historical_discordant_rate <= 1.0):
        raise InformationAuditError("historical_discordant_rate must be in (0, 1]")
    if not (0.0 < alpha < 1.0):
        raise InformationAuditError("alpha must be in (0, 1)")
    if not (0.0 < power < 1.0):
        raise InformationAuditError("power must be in (0, 1)")
    expected_discordant_pairs = n * historical_discordant_rate
    if expected_discordant_pairs < 1.0:
        raise InformationAuditError(
            f"expected discordant pairs {expected_discordant_pairs:.3f} < 1 at n={n}; "
            "this approximation needs at least one expected discordant pair"
        )
    z_alpha_half = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    z_power = NormalDist().inv_cdf(power)
    mde_p = (z_alpha_half + z_power) * math.sqrt(0.25 / expected_discordant_pairs)
    mde_p = min(mde_p, 0.5)
    mde_pp = historical_discordant_rate * (2.0 * mde_p) * 100.0
    return {
        "n": n,
        "historical_discordant_rate": historical_discordant_rate,
        "expected_discordant_pairs": expected_discordant_pairs,
        "alpha": alpha,
        "power": power,
        "z_alpha_half": z_alpha_half,
        "z_power": z_power,
        "minimum_detectable_discordant_split_delta": 2.0 * mde_p,
        "minimum_detectable_effect_pp": mde_pp,
    }


def power_table(
    *,
    ns: Mapping[str, int],
    citations: Sequence[Mapping[str, object]] = HISTORICAL_DISCORDANCE_CITATIONS,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, object]:
    if not isinstance(ns, Mapping) or not ns:
        raise InformationAuditError("ns must be a non-empty mapping of roster/segment name -> n")
    rows: dict[str, object] = {}
    for name, n in sorted(ns.items()):
        by_citation: dict[str, object] = {}
        for citation in citations:
            try:
                by_citation[str(citation["label"])] = minimum_detectable_paired_effect_pp(
                    n=n, historical_discordant_rate=float(citation["discordant_rate"]), alpha=alpha, power=power
                )
            except InformationAuditError as error:
                by_citation[str(citation["label"])] = {"n": n, "error": str(error)}
        rows[name] = by_citation
    return {
        "alpha": alpha,
        "power": power,
        "citations": [dict(citation) for citation in citations],
        "by_n": rows,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_information_audit(
    spec: CarrierInformationSpec,
    *,
    out_dir: Path,
    seed: int = DEFAULT_SEED,
    ks: Sequence[int] = DEFAULT_KS,
    folds: int = DEFAULT_FOLD_COUNT,
) -> dict[str, object]:
    """Run the eight-question audit for ``spec`` and write ``summary.json``
    + ``README.md`` under ``out_dir``. Refuses to overwrite an existing
    ``summary.json`` (a fresh audit run needs a fresh output directory)."""

    out_dir = Path(out_dir)
    summary_path = out_dir / "summary.json"
    if summary_path.exists():
        raise InformationAuditError(f"refusing to overwrite existing {summary_path}")

    construction_rows = _validate_rows(tuple(spec.construction_loader()), label="construction rows")

    q1 = field_catalog(spec.field_legality, spec.corpus_structure_legality)
    q2 = task_information_decomposition(spec.task_kind, spec.obs_org_supply_use)

    construction_stratum_counts = stratum_histogram(construction_rows, stratum_of=spec.stratum_of)
    natural = population_distribution(construction_stratum_counts)
    roster_q3: dict[str, object] = {}
    for roster in spec.evaluation_rosters:
        roster_q3[roster.name] = {
            "split_role": roster.split_role,
            "intended_n": roster.intended_n,
            "selection_rule_note": roster.selection_rule_note,
            "deviation": roster_deviation(natural["shares"], roster.stratum_counts),
        }
    q3 = {"strata_key": spec.strata_key, "natural": natural, "rosters": roster_q3}

    q4 = label_field_entropy(construction_rows, labels_of=spec.labels_of, label_fields=spec.label_fields)

    if spec.retrieval_mode == "grouped_bm25":
        q5 = retrieval_reachability_grouped_bm25(
            construction_rows,
            key_text_of=spec.key_text_of,
            group_of=spec.group_of,
            labels_of=spec.labels_of,
            label_fields=spec.label_fields,
            stratum_of=spec.stratum_of,
            seed=seed,
            fold_count=folds,
            ks=ks,
        )
    elif spec.retrieval_mode == "self_supplied_membership":
        from .information_audit_specs import MENTION_FIELD_SEPARATOR

        q5 = retrieval_reachability_self_supplied(
            construction_rows,
            key_text_of=spec.key_text_of,
            labels_of=spec.labels_of,
            mention_field=spec.label_fields[-1],
            mention_separator=MENTION_FIELD_SEPARATOR,
            seed=seed,
        )
    else:
        raise InformationAuditError(f"unknown retrieval_mode {spec.retrieval_mode!r}")

    construction_ids = frozenset(row["item_id"] for row in construction_rows)
    roster_identity: dict[str, object] = {}
    for roster in spec.evaluation_rosters:
        roster_identity[roster.name] = decontamination_identity(construction_ids, roster.identity_loader())
    q6: dict[str, object] = {"identity": roster_identity}
    if spec.retrieval_mode == "self_supplied_membership":
        q6["cross_call_near_duplicate"] = near_duplicate_pairs(construction_rows, key_text_of=spec.key_text_of)

    q7 = external_supplementation_ledger(spec.external_supplementation)

    q8 = power_table(ns={roster.name: roster.intended_n for roster in spec.evaluation_rosters})

    summary: dict[str, object] = {
        "schema": AUDIT_SCHEMA,
        "carrier_lock_key": spec.carrier_lock_key,
        "task_kind": spec.task_kind,
        "knowledge_source": spec.knowledge_source,
        "retrieval_mode": spec.retrieval_mode,
        "seed": seed,
        "ks": list(sorted({int(k) for k in ks})),
        "fold_count": folds,
        "construction_unit_count": len(construction_rows),
        "q1_field_catalog": q1,
        "q2_task_information_decomposition": q2,
        "q3_population_distribution": q3,
        "q4_label_space_entropy": q4,
        "q5_retrieval_reachability": q5,
        "q6_decontamination": q6,
        "q7_external_supplementation_ledger": q7,
        "q8_power": q8,
        "contacts": {"model": 0, "network": 0, "scorer": 0, "gpu": 0, "audio_seconds": 0},
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    (out_dir / "README.md").write_text(_render_readme(summary), encoding="utf-8")
    return summary


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100.0:.2f}%"


def _render_readme(summary: Mapping[str, object]) -> str:
    lines: list[str] = []
    carrier = summary["carrier_lock_key"]
    lines.append(f"# Dataset information audit -- {carrier}")
    lines.append("")
    lines.append(
        f"Schema `{summary['schema']}`. Task kind `{summary['task_kind']}`. Knowledge source: "
        f"{summary['knowledge_source']}. Retrieval mode `{summary['retrieval_mode']}`. Seed "
        f"`{summary['seed']}`. Construction units: {summary['construction_unit_count']}. Zero model, "
        "GPU, scorer, embedding, or network contact."
    )
    lines.append("")

    lines.append("## Q1: fields and corpus structures")
    lines.append("")
    lines.append("| field | legality |")
    lines.append("|---|---|")
    q1 = summary["q1_field_catalog"]
    for field, legality in q1["fields"].items():
        lines.append(f"| {field} | {legality} |")
    lines.append("")
    lines.append("| corpus structure | legality |")
    lines.append("|---|---|")
    for structure, legality in q1["corpus_structures"].items():
        lines.append(f"| {structure} | {legality} |")
    lines.append("")

    lines.append("## Q2: task information requirement (OBS / ORG / SUPPLY / USE)")
    lines.append("")
    q2 = summary["q2_task_information_decomposition"]
    for key in ("obs", "org", "supply", "use"):
        lines.append(f"- **{key.upper()}**: {q2[key]}")
    lines.append("")

    lines.append("## Q3: natural population distribution and roster deviation")
    lines.append("")
    q3 = summary["q3_population_distribution"]
    lines.append(f"Strata key: `{q3['strata_key']}`. Natural (construction) distribution:")
    lines.append("")
    lines.append("| stratum | count | share |")
    lines.append("|---|---:|---:|")
    for stratum, count in q3["natural"]["counts"].items():
        lines.append(f"| {stratum} | {count} | {_pct(q3['natural']['shares'][stratum])} |")
    lines.append("")
    for roster_name, roster in q3["rosters"].items():
        deviation = roster["deviation"]
        lines.append(
            f"**{roster_name}** (`{roster['split_role']}`, intended n={roster['intended_n']}): "
            f"TVD from natural = {deviation['total_variation_distance_from_natural']:.4f}, "
            f"TVD from uniform allocation = {deviation['total_variation_distance_from_uniform_allocation']:.4f}, "
            f"classification = **{deviation['classification']}**. {roster['selection_rule_note']}"
        )
        lines.append("")

    lines.append("## Q4: label-space entropy and prior-mass coverage")
    lines.append("")
    for field, entropy in summary["q4_label_space_entropy"].items():
        lines.append(
            f"**{field}**: {entropy['observed_label_count']} of {entropy['label_count']} labels observed, "
            f"{entropy['total_occurrences']} occurrences, entropy {entropy['entropy_bits']:.3f} bits "
            f"(effective {entropy['effective_label_count']:.2f} labels)."
        )
        lines.append("")
        lines.append("| mass threshold | minimum k |")
        lines.append("|---|---:|")
        for threshold, k in entropy["minimum_k_for_mass"].items():
            lines.append(f"| {threshold} | {k} |")
        lines.append("")

    lines.append("## Q5: retrieval reachability")
    lines.append("")
    q5 = summary["q5_retrieval_reachability"]
    if q5["mode"] == "grouped_bm25":
        lines.append(
            f"Label-blind grouped {q5['fold_count']}-fold BM25 coverage over {q5['registry_label_count']} "
            f"registered labels, {q5['scored_unit_count']} scored units."
        )
        lines.append("")
        lines.append("| k | full-set coverage | label recall | mean distractors | worst-fold full-set |")
        lines.append("|---:|---:|---:|---:|---:|")
        for k, metrics in q5["aggregate"].items():
            lines.append(
                f"| {k} | {_pct(metrics['full_set_coverage'])} | {_pct(metrics['required_item_recall'])} | "
                f"{metrics['mean_distractor_burden']:.2f} | {_pct(q5['worst_fold_full_set_coverage'][k])} |"
            )
        lines.append("")
    else:
        lines.append(
            f"Self-supplied own-call-vs-random-other-call membership over {q5['item_count']} calls, "
            f"{q5['mention_total']} gold entity mentions."
        )
        lines.append("")
        lines.append(
            f"Own-context reachability: **{_pct(q5['own_context_reachability'])}**. "
            f"Random-other-context reachability (negative control): "
            f"**{_pct(q5['random_other_context_reachability'])}**."
        )
        lines.append("")
        lines.append("| entity type | mentions | own-context | random-other-context |")
        lines.append("|---|---:|---:|---:|")
        for entity_type, row in q5["per_entity_type"].items():
            lines.append(
                f"| {entity_type} | {row['mention_count']} | {_pct(row['own_context_reachability'])} | "
                f"{_pct(row['random_other_context_reachability'])} |"
            )
        lines.append("")

    lines.append("## Q6: decontamination")
    lines.append("")
    q6 = summary["q6_decontamination"]
    lines.append("| roster | construction n | roster n | identity overlap | clean |")
    lines.append("|---|---:|---:|---:|---|")
    for roster_name, row in q6["identity"].items():
        lines.append(
            f"| {roster_name} | {row['construction_count']} | {row['roster_count']} | "
            f"{row['identity_overlap_count']} | {row['clean']} |"
        )
    lines.append("")
    if "cross_call_near_duplicate" in q6:
        near = q6["cross_call_near_duplicate"]
        lines.append(
            f"Cross-call near-duplicate audit (token-set Jaccard >= {near['threshold']}): "
            f"{near['pair_count']} of {near['item_count'] * (near['item_count'] - 1) // 2} pairs."
        )
        lines.append("")

    lines.append("## Q7: external supplementation ledger")
    lines.append("")
    lines.append("| need | source | legality |")
    lines.append("|---|---|---|")
    for row in summary["q7_external_supplementation_ledger"]["rows"]:
        lines.append(f"| {row['need']} | {row['source']} | {row['legality']} |")
    lines.append("")

    lines.append("## Q8: power")
    lines.append("")
    q8 = summary["q8_power"]
    lines.append(
        f"Two-sided alpha={q8['alpha']}, target power={q8['power']}. Historical discordant-pair rate "
        "citations:"
    )
    lines.append("")
    lines.append("| citation | n | discordant rate | source |")
    lines.append("|---|---:|---:|---|")
    for citation in q8["citations"]:
        lines.append(
            f"| {citation['label']} | {citation['n']} | {_pct(citation['discordant_rate'])} | "
            f"{citation['source']} |"
        )
    lines.append("")
    lines.append("| n (roster/segment) | citation | minimum detectable effect (pp) |")
    lines.append("|---|---|---:|")
    for name, by_citation in q8["by_n"].items():
        for citation_label, result in by_citation.items():
            if "error" in result:
                lines.append(f"| {name} | {citation_label} | n/a ({result['error']}) |")
            else:
                lines.append(f"| {name} | {citation_label} | {result['minimum_detectable_effect_pp']:.2f} |")
    lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", required=True, choices=("audio2tool", "slurp", "earnings21-conec"))
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    from ..data.lock import REPO_ROOT, data_root, load_lock, umbrella_lock_path
    from .information_audit_specs import audio2tool_spec, earnings21_conec_spec, slurp_spec

    repo_root = args.repo_root if args.repo_root is not None else REPO_ROOT
    root = args.data_root if args.data_root is not None else data_root()
    lock = load_lock(umbrella_lock_path(repo_root))

    builders: Mapping[str, Callable[[Mapping[str, object], Path, Path], CarrierInformationSpec]] = {
        "audio2tool": audio2tool_spec,
        "slurp": slurp_spec,
        "earnings21-conec": earnings21_conec_spec,
    }
    spec = builders[args.carrier](lock, root, repo_root)
    result = run_information_audit(spec, out_dir=args.out_dir, seed=args.seed)
    print(
        json.dumps(
            {
                "carrier": args.carrier,
                "out_dir": str(args.out_dir),
                "construction_unit_count": result["construction_unit_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_SEED",
    "DEFAULT_KS",
    "DEFAULT_FOLD_COUNT",
    "NEAR_DUPLICATE_THRESHOLD",
    "HISTORICAL_DISCORDANCE_CITATIONS",
    "InformationAuditError",
    "field_catalog",
    "task_information_decomposition",
    "stratum_histogram",
    "population_distribution",
    "roster_deviation",
    "label_space_entropy_from_counts",
    "label_field_entropy",
    "label_blind_components",
    "assign_grouped_folds",
    "retrieval_reachability_grouped_bm25",
    "deterministic_derangement",
    "retrieval_reachability_self_supplied",
    "decontamination_identity",
    "near_duplicate_pairs",
    "external_supplementation_ledger",
    "minimum_detectable_paired_effect_pp",
    "power_table",
    "run_information_audit",
    "main",
]
