"""Label-blind grouped out-of-fold validation for Audio2Tool retrieval.

Rows sharing a query block or a retrieval-equivalent text representation stay
in one fold. Optional alternate texts let a factorial comparison freeze one
common split before either representation is scored. Labels, skeletons, call
counts, and retrieval outcomes never influence fold assignment.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

from .a2t_label_candidate_reduction import (
    analyze_label_candidate_reduction,
    candidate_sample_metrics,
)
from .a2t_lexical_ceiling import tokenize
from ..rails.knowledge_build_a2t import A2tKbRow


RESULT_SCHEMA = "saea-a2t-grouped-candidate-validation-v2"
NEAR_DUPLICATE_THRESHOLD = 0.80


class GroupedCandidateValidationError(ValueError):
    """The grouped validation boundary or assignment is malformed."""


@dataclass(frozen=True)
class GroupedCandidateValidationAudit:
    """A JSON-compatible report and its canonical serialization."""

    report: Mapping[str, object]
    canonical_json: str


def _validate_rows(rows: Sequence[A2tKbRow]) -> tuple[A2tKbRow, ...]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise GroupedCandidateValidationError("construction_rows must be non-empty")
    ordered = tuple(sorted(rows, key=lambda row: getattr(row, "unit_id", "")))
    if any(not isinstance(row, A2tKbRow) for row in ordered):
        raise GroupedCandidateValidationError(
            "construction_rows must contain A2tKbRow values"
        )
    unit_ids = [row.unit_id for row in ordered]
    if any(not unit_id for unit_id in unit_ids) or len(unit_ids) != len(set(unit_ids)):
        raise GroupedCandidateValidationError(
            "construction_rows have duplicate or malformed unit ids"
        )
    if any(not isinstance(row.text, str) or not row.text.strip() for row in ordered):
        raise GroupedCandidateValidationError("construction_rows have empty text")
    if any(type(row.query_idx) is not int or row.query_idx < 0 for row in ordered):
        raise GroupedCandidateValidationError(
            "construction_rows have malformed query_idx"
        )
    return ordered


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _validate_alternate_texts(
    rows: Sequence[A2tKbRow], values: Mapping[str, str] | None
) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, Mapping):
        raise GroupedCandidateValidationError(
            "alternate_text_by_unit_id must be a mapping"
        )
    unit_ids = {row.unit_id for row in rows}
    unknown = sorted(set(values) - unit_ids)
    if unknown:
        raise GroupedCandidateValidationError(
            "alternate_text_by_unit_id names an unknown unit"
        )
    result: dict[str, str] = {}
    for unit_id in sorted(values):
        value = values[unit_id]
        if not isinstance(value, str) or not value.strip():
            raise GroupedCandidateValidationError(
                "alternate_text_by_unit_id values must be non-empty text"
            )
        result[unit_id] = value
    return result


def _components(
    rows: Sequence[A2tKbRow], alternate: Mapping[str, str]
) -> tuple[tuple[str, ...], ...]:
    parent = {row.unit_id: row.unit_id for row in rows}

    def find(value: str) -> str:
        root = value
        while parent[root] != root:
            root = parent[root]
        while parent[value] != value:
            next_value = parent[value]
            parent[value] = root
            value = next_value
        return root

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root == right_root:
            return
        smaller, larger = sorted((left_root, right_root))
        parent[larger] = smaller

    def union_signatures(values: Sequence[tuple[object, str]]) -> None:
        first_by_signature: dict[object, str] = {}
        for signature, unit_id in values:
            first = first_by_signature.setdefault(signature, unit_id)
            union(first, unit_id)

    union_signatures([(row.query_idx, row.unit_id) for row in rows])
    union_signatures([(_normalized_text(row.text), row.unit_id) for row in rows])
    union_signatures([(tokenize(row.text), row.unit_id) for row in rows])
    alternate_rows = [(unit_id, alternate[unit_id]) for unit_id in sorted(alternate)]
    union_signatures(
        [(_normalized_text(text), unit_id) for unit_id, text in alternate_rows]
    )
    union_signatures([(tokenize(text), unit_id) for unit_id, text in alternate_rows])

    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(find(row.unit_id), []).append(row.unit_id)
    return tuple(
        sorted(
            (tuple(sorted(unit_ids)) for unit_ids in grouped.values()),
            key=lambda members: members,
        )
    )


def _component_hash(seed: int, members: Sequence[str]) -> str:
    payload = f"{seed}\0" + "\0".join(members)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def assign_grouped_validation_folds(
    construction_rows: Sequence[A2tKbRow],
    *,
    seed: int,
    fold_count: int,
    alternate_text_by_unit_id: Mapping[str, str] | None = None,
) -> tuple[tuple[str, ...], ...]:
    """Assign label-blind, retrieval-equivalent connected components to folds."""

    rows = _validate_rows(construction_rows)
    if type(seed) is not int or seed < 0:
        raise GroupedCandidateValidationError("seed must be a non-negative integer")
    if type(fold_count) is not int or fold_count < 2:
        raise GroupedCandidateValidationError("fold_count must be at least two")
    alternate = _validate_alternate_texts(rows, alternate_text_by_unit_id)
    components = _components(rows, alternate)
    if len(components) < fold_count:
        raise GroupedCandidateValidationError(
            "fold_count exceeds the fewer grouped components available"
        )
    ordered_components = sorted(
        components,
        key=lambda members: (_component_hash(seed, members), members[0]),
    )
    folds: list[list[str]] = [[] for _ in range(fold_count)]
    loads = [0] * fold_count
    for members in ordered_components:
        fold_id = min(range(fold_count), key=lambda value: (loads[value], value))
        folds[fold_id].extend(members)
        loads[fold_id] += len(members)
    result = tuple(tuple(sorted(fold)) for fold in folds)
    if any(not fold for fold in result):
        raise GroupedCandidateValidationError(
            "grouped assignment produced an empty fold"
        )
    assigned = [unit_id for fold in result for unit_id in fold]
    if sorted(assigned) != sorted(row.unit_id for row in rows):
        raise GroupedCandidateValidationError(
            "grouped assignment did not assign every unit exactly once"
        )
    return result


def _assignment_sha256(folds: Sequence[Sequence[str]]) -> str:
    payload = "\n".join(
        f"{fold_id}:{unit_id}" for fold_id, fold in enumerate(folds) for unit_id in fold
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _metrics_by_group(
    samples: Sequence[Mapping[str, object]],
    *,
    k_values: Sequence[int],
    registry_count: int,
) -> dict[str, dict[str, object]]:
    if not samples:
        return {}
    return {
        str(k): candidate_sample_metrics(
            samples,
            k=k,
            registry_count=registry_count,
        )
        for k in k_values
    }


def maximum_token_jaccard(
    build: Sequence[A2tKbRow], validation: Sequence[A2tKbRow]
) -> dict[str, float]:
    build_sets = [frozenset(tokenize(row.text)) for row in build]
    postings: dict[str, list[int]] = {}
    for index, tokens in enumerate(build_sets):
        for token in tokens:
            postings.setdefault(token, []).append(index)
    result: dict[str, float] = {}
    for row in validation:
        query = frozenset(tokenize(row.text))
        candidates = {index for token in query for index in postings.get(token, ())}
        best = 0.0
        for index in candidates:
            other = build_sets[index]
            union = len(query | other)
            if union:
                best = max(best, len(query & other) / union)
        result[row.unit_id] = best
    return result


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction + 0.999999) - 1))
    return ordered[index]


def analyze_grouped_candidate_validation(
    *,
    construction_rows: Sequence[A2tKbRow],
    registry_tool_names: Sequence[str],
    seed: int,
    fold_count: int,
    k_grid: Sequence[int],
    alternate_text_by_unit_id: Mapping[str, str] | None = None,
    public_tool_key_text_by_name: Mapping[str, str] | None = None,
) -> GroupedCandidateValidationAudit:
    """Measure pooled and worst-fold label retrieval on grouped folds."""

    rows = _validate_rows(construction_rows)
    alternate = _validate_alternate_texts(rows, alternate_text_by_unit_id)
    folds = assign_grouped_validation_folds(
        rows,
        seed=seed,
        fold_count=fold_count,
        alternate_text_by_unit_id=alternate,
    )
    k_values = tuple(sorted(k_grid))
    if (
        not k_values
        or len(k_values) != len(set(k_values))
        or any(type(k) is not int or k <= 0 for k in k_values)
    ):
        raise GroupedCandidateValidationError(
            "k_grid must contain unique positive integers"
        )
    registry = tuple(sorted(registry_tool_names))
    if not registry or len(registry) != len(set(registry)):
        raise GroupedCandidateValidationError(
            "registry_tool_names must contain unique labels"
        )
    rows_by_id = {row.unit_id: row for row in rows}
    fold_reports: list[dict[str, object]] = []
    all_samples: list[dict[str, object]] = []
    for fold_id, fold_ids in enumerate(folds):
        validation_set = frozenset(fold_ids)
        validation = tuple(rows_by_id[unit_id] for unit_id in fold_ids)
        build = tuple(row for row in rows if row.unit_id not in validation_set)
        result = analyze_label_candidate_reduction(
            construction_rows=build,
            validation_rows=validation,
            registry_tool_names=registry,
            k_grid=k_values,
            public_tool_key_text_by_name=public_tool_key_text_by_name,
        )
        jaccard_by_unit = maximum_token_jaccard(build, validation)
        samples = [
            dict(
                sample,
                fold_id=fold_id,
                maximum_build_token_jaccard=jaccard_by_unit[sample["unit_id"]],
            )
            for sample in result.report["samples"]
        ]
        all_samples.extend(samples)
        build_labels = {
            name for row in build for name in (row.tool_name, *row.extra_call_names)
        }
        validation_labels = {
            name
            for row in validation
            for name in (row.tool_name, *row.extra_call_names)
        }
        tier_counts = Counter(row.tier for row in validation)
        fold_reports.append(
            {
                "fold_id": fold_id,
                "build_units": len(build),
                "validation_units": len(validation),
                "validation_query_blocks": len({row.query_idx for row in validation}),
                "validation_tier_counts": dict(sorted(tier_counts.items())),
                "validation_multi_call_units": sum(
                    row.call_count > 1 for row in validation
                ),
                "validation_required_labels_absent_from_build": sorted(
                    validation_labels - build_labels
                ),
                "candidate_report_sha256": hashlib.sha256(
                    result.canonical_json.encode("ascii")
                ).hexdigest(),
                "k_metrics": result.report["k_metrics"],
            }
        )

    if len(all_samples) != len(rows) or len(
        {sample["unit_id"] for sample in all_samples}
    ) != len(rows):
        raise GroupedCandidateValidationError(
            "out-of-fold validation did not score every unit exactly once"
        )
    tiers = sorted({str(sample["tier"]) for sample in all_samples})
    per_tier = {
        tier: _metrics_by_group(
            [sample for sample in all_samples if sample["tier"] == tier],
            k_values=k_values,
            registry_count=len(registry),
        )
        for tier in tiers
    }
    multi_call = [
        sample
        for sample in all_samples
        if int(sample["required_call_occurrence_count"]) > 1
    ]
    single_call = [
        sample
        for sample in all_samples
        if int(sample["required_call_occurrence_count"]) == 1
    ]
    multiple_distinct = [
        sample for sample in all_samples if len(sample["required_tool_names"]) > 1
    ]
    duplicate_occurrences = [
        sample
        for sample in all_samples
        if int(sample["duplicate_required_call_occurrence_count"]) > 0
    ]
    aggregate_metrics = _metrics_by_group(
        all_samples,
        k_values=k_values,
        registry_count=len(registry),
    )
    near_duplicates = [
        sample
        for sample in all_samples
        if float(sample["maximum_build_token_jaccard"]) >= NEAR_DUPLICATE_THRESHOLD
    ]
    no_near_duplicates = [
        sample
        for sample in all_samples
        if float(sample["maximum_build_token_jaccard"]) < NEAR_DUPLICATE_THRESHOLD
    ]
    jaccard_values = [
        float(sample["maximum_build_token_jaccard"]) for sample in all_samples
    ]
    worst_fold = {
        str(k): {
            "minimum_full_set_coverage": min(
                fold["k_metrics"][str(k)]["full_set_coverage"] for fold in fold_reports
            ),
            "minimum_required_item_recall": min(
                fold["k_metrics"][str(k)]["required_item_recall"]
                for fold in fold_reports
            ),
            "maximum_mean_distractor_burden": max(
                fold["k_metrics"][str(k)]["mean_distractor_burden"]
                for fold in fold_reports
            ),
        }
        for k in k_values
    }
    component_groups = _components(rows, alternate)
    quality_by_k: dict[str, dict[str, bool]] = {}
    for k in k_values:
        key = str(k)
        checks = {
            "overall_full_set_at_least_0_95": aggregate_metrics[key][
                "full_set_coverage"
            ]
            >= 0.95,
            "overall_label_recall_at_least_0_97": aggregate_metrics[key][
                "required_item_recall"
            ]
            >= 0.97,
            "mean_distractors_at_most_15": aggregate_metrics[key][
                "mean_distractor_burden"
            ]
            <= 15.0,
            "worst_fold_full_set_at_least_0_93": worst_fold[key][
                "minimum_full_set_coverage"
            ]
            >= 0.93,
            "every_tier_full_set_at_least_0_90": all(
                metrics[key]["full_set_coverage"] >= 0.90
                for metrics in per_tier.values()
            ),
            "multi_call_full_set_at_least_0_90": (
                bool(multi_call)
                and _metrics_by_group(
                    multi_call,
                    k_values=(k,),
                    registry_count=len(registry),
                )[key]["full_set_coverage"]
                >= 0.90
            ),
            "no_near_duplicate_full_set_at_least_0_95": (
                bool(no_near_duplicates)
                and _metrics_by_group(
                    no_near_duplicates,
                    k_values=(k,),
                    registry_count=len(registry),
                )[key]["full_set_coverage"]
                >= 0.95
            ),
            "fixed_candidate_count_at_most_32": min(k, len(registry)) <= 32,
        }
        quality_by_k[key] = checks
    passing = [int(key) for key, checks in quality_by_k.items() if all(checks.values())]
    report: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "scope": {
            "construction_training_rows_only": True,
            "label_retrieval_only": True,
            "runtime_eligible": False,
            "model_consumption_upper_bound": False,
            "model_contacts": 0,
            "network_contacts": 0,
            "scorer_contacts": 0,
        },
        "split_policy": {
            "seed": seed,
            "label_blind": True,
            "groups_query_idx": True,
            "groups_normalized_text_twins": True,
            "groups_bm25_token_sequence_twins": True,
            "groups_alternate_representation_twins": bool(alternate),
            "component_identity_binds_all_member_ids": True,
            "assignment": (
                "Sort components by SHA256(seed NUL complete sorted member ids), "
                "then minimum member id; assign to minimum (row load, fold id)."
            ),
            "assignment_sha256": _assignment_sha256(folds),
        },
        "population": {
            "unit_count": len(rows),
            "fold_count": fold_count,
            "component_count": len(component_groups),
            "largest_component_units": max(map(len, component_groups)),
            "registry_label_count": len(registry),
        },
        "retrieval_key_design": {
            "construction_key_count_per_fold": "fold build unit count",
            "public_tool_key_count": (
                len(public_tool_key_text_by_name)
                if public_tool_key_text_by_name is not None
                else 0
            ),
            "public_tool_keys_applied_identically_to_every_fold": (
                public_tool_key_text_by_name is not None
            ),
            "public_tool_key_text_emitted": False,
        },
        "folds": fold_reports,
        "cross_fold_duplicate_audit": {
            "query_idx_overlap_count": 0,
            "normalized_text_twin_validation_units": 0,
            "bm25_token_sequence_twin_validation_units": 0,
            "alternate_representation_twin_validation_units": 0,
        },
        "aggregate": {
            "k_metrics": aggregate_metrics,
            "per_tier": per_tier,
            "single_call": {
                "unit_count": len(single_call),
                "k_metrics": _metrics_by_group(
                    single_call,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
            },
            "multi_call": {
                "unit_count": len(multi_call),
                "k_metrics": _metrics_by_group(
                    multi_call,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
            },
            "multiple_distinct_required_labels": {
                "unit_count": len(multiple_distinct),
                "k_metrics": _metrics_by_group(
                    multiple_distinct,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
            },
            "duplicate_call_occurrences": {
                "unit_count": len(duplicate_occurrences),
                "k_metrics": _metrics_by_group(
                    duplicate_occurrences,
                    k_values=k_values,
                    registry_count=len(registry),
                ),
            },
            "near_duplicate_sensitivity": {
                "threshold": NEAR_DUPLICATE_THRESHOLD,
                "metric": "maximum token-set Jaccard against the fold build index",
                "maximum_jaccard": {
                    "minimum": min(jaccard_values),
                    "median": _percentile(jaccard_values, 0.50),
                    "p90": _percentile(jaccard_values, 0.90),
                    "maximum": max(jaccard_values),
                },
                "near_duplicate": {
                    "unit_count": len(near_duplicates),
                    "k_metrics": _metrics_by_group(
                        near_duplicates,
                        k_values=k_values,
                        registry_count=len(registry),
                    ),
                },
                "no_near_duplicate": {
                    "unit_count": len(no_near_duplicates),
                    "k_metrics": _metrics_by_group(
                        no_near_duplicates,
                        k_values=k_values,
                        registry_count=len(registry),
                    ),
                },
            },
            "worst_fold_full_set_coverage": worst_fold,
        },
        "quality_gate": {
            "by_k": quality_by_k,
            "passing_fixed_k": passing,
            "near_duplicate_sensitivity_measured": True,
            "admitted": bool(passing),
        },
    }
    canonical_json = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return GroupedCandidateValidationAudit(
        report=report,
        canonical_json=canonical_json,
    )


__all__ = [
    "GroupedCandidateValidationAudit",
    "GroupedCandidateValidationError",
    "RESULT_SCHEMA",
    "NEAR_DUPLICATE_THRESHOLD",
    "analyze_grouped_candidate_validation",
    "assign_grouped_validation_folds",
    "maximum_token_jaccard",
]
