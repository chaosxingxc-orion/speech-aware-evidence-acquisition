"""Construction-only dense and hybrid Audio2Tool candidate validation.

The caller supplies already-materialized per-unit vectors. This module performs
no file, network, embedding-model, frozen-core, or scorer contact. Every fold
fits tool-tier centroids and a non-parametric exemplar index only on that
fold's construction partition, then scores gold labels after rankings exist.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Mapping, Sequence

from .a2t_grouped_candidate_validation import (
    NEAR_DUPLICATE_THRESHOLD,
    assign_grouped_validation_folds,
    maximum_token_jaccard,
)
from .a2t_label_candidate_reduction import (
    analyze_label_candidate_reduction,
    candidate_sample_metrics,
)
from ..rails.knowledge_build_a2t import A2tKbRow


RESULT_SCHEMA = "saea-a2t-dense-candidate-validation-v2"
RRF_CONSTANT = 60
DEFAULT_QUERY_BATCH_SIZE = 256


class DenseCandidateValidationError(ValueError):
    """The construction-only dense validation boundary is malformed."""


@dataclass(frozen=True)
class DenseCandidateValidationAudit:
    """A JSON-compatible report and its canonical serialization."""

    report: Mapping[str, object]
    canonical_json: str


def _validate_rows(rows: Sequence[A2tKbRow]) -> tuple[A2tKbRow, ...]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise DenseCandidateValidationError("construction_rows must be non-empty")
    ordered = tuple(sorted(rows, key=lambda row: getattr(row, "unit_id", "")))
    if any(not isinstance(row, A2tKbRow) for row in ordered):
        raise DenseCandidateValidationError(
            "construction_rows must contain A2tKbRow values"
        )
    unit_ids = [row.unit_id for row in ordered]
    if any(not value for value in unit_ids) or len(unit_ids) != len(set(unit_ids)):
        raise DenseCandidateValidationError(
            "construction_rows have duplicate or malformed unit ids"
        )
    if any(not row.text.strip() for row in ordered):
        raise DenseCandidateValidationError("construction_rows have empty text")
    if any(row.call_count != 1 + len(row.extra_call_names) for row in ordered):
        raise DenseCandidateValidationError(
            "construction_rows have inconsistent call labels"
        )
    return ordered


def _validate_registry(
    names: Sequence[str], rows: Sequence[A2tKbRow]
) -> tuple[str, ...]:
    if isinstance(names, (str, bytes)) or not isinstance(names, Sequence):
        raise DenseCandidateValidationError(
            "registry_tool_names must contain unique non-empty labels"
        )
    registry = tuple(names)
    if (
        not registry
        or len(registry) != len(set(registry))
        or any(not isinstance(name, str) or not name for name in registry)
    ):
        raise DenseCandidateValidationError(
            "registry_tool_names must contain unique non-empty labels"
        )
    unknown = sorted(
        {
            name
            for row in rows
            for name in (row.tool_name, *row.extra_call_names)
            if name not in registry
        }
    )
    if unknown:
        raise DenseCandidateValidationError(
            f"construction_rows name unknown registry labels: {unknown!r}"
        )
    return tuple(sorted(registry))


def _validate_k_grid(k_grid: Sequence[int]) -> tuple[int, ...]:
    if isinstance(k_grid, (str, bytes)) or not isinstance(k_grid, Sequence):
        raise DenseCandidateValidationError(
            "k_grid must contain unique positive integers"
        )
    values = tuple(k_grid)
    if (
        not values
        or len(values) != len(set(values))
        or any(type(value) is not int or value <= 0 for value in values)
    ):
        raise DenseCandidateValidationError(
            "k_grid must contain unique positive integers"
        )
    return tuple(sorted(values))


def _validate_vectors(
    rows: Sequence[A2tKbRow], vectors_by_unit_id: Mapping[str, Sequence[Real]]
) -> tuple[dict[str, object], int, str]:
    import numpy as np

    if not isinstance(vectors_by_unit_id, Mapping):
        raise DenseCandidateValidationError("vectors_by_unit_id must be a mapping")
    expected_ids = {row.unit_id for row in rows}
    if set(vectors_by_unit_id) != expected_ids:
        raise DenseCandidateValidationError(
            "vectors_by_unit_id must exactly cover construction unit ids"
        )
    dimension: int | None = None
    ordered_ids = sorted(expected_ids)
    vector_rows: list[object] = []
    vector_identity = hashlib.sha256()
    for unit_id in ordered_ids:
        raw = vectors_by_unit_id[unit_id]
        if isinstance(raw, (str, bytes)):
            raise DenseCandidateValidationError(
                f"vector {unit_id!r} must be a non-empty numeric sequence"
            )
        try:
            values = np.asarray(raw, dtype=np.float64)
        except (TypeError, ValueError) as error:
            raise DenseCandidateValidationError(
                f"vector {unit_id!r} must contain finite numeric values"
            ) from error
        if values.ndim != 1 or values.size == 0:
            raise DenseCandidateValidationError(
                f"vector {unit_id!r} must be a non-empty numeric sequence"
            )
        if any(isinstance(value, bool) for value in raw):
            raise DenseCandidateValidationError(
                f"vector {unit_id!r} must contain finite numeric values"
            )
        if not bool(np.isfinite(values).all()):
            raise DenseCandidateValidationError(
                f"vector {unit_id!r} must contain finite numeric values"
            )
        if dimension is None:
            dimension = int(values.size)
        elif values.size != dimension:
            raise DenseCandidateValidationError(
                "all vectors must have the same dimension"
            )
        unit_bytes = unit_id.encode("utf-8")
        vector_identity.update(len(unit_bytes).to_bytes(8, "big"))
        vector_identity.update(unit_bytes)
        vector_identity.update(int(values.size).to_bytes(8, "big"))
        vector_identity.update(values.astype(">f8", copy=False).tobytes())
        vector_rows.append(values)
    assert dimension is not None
    matrix = np.stack(vector_rows)
    norms = np.linalg.norm(matrix, axis=1)
    if not bool(np.isfinite(norms).all()) or bool((norms == 0.0).any()):
        raise DenseCandidateValidationError("vectors must have nonzero norm")
    matrix = matrix / norms[:, None]
    return (
        {unit_id: matrix[index] for index, unit_id in enumerate(ordered_ids)},
        dimension,
        vector_identity.hexdigest(),
    )


def _validate_folds(
    rows: Sequence[A2tKbRow], folds: Sequence[Sequence[str]]
) -> tuple[tuple[str, ...], ...]:
    if isinstance(folds, (str, bytes)) or not isinstance(folds, Sequence):
        raise DenseCandidateValidationError("validation_folds must be a sequence")
    if len(folds) < 2:
        raise DenseCandidateValidationError(
            "validation_folds must contain at least two folds"
        )
    expected = {row.unit_id for row in rows}
    result: list[tuple[str, ...]] = []
    for fold in folds:
        if isinstance(fold, (str, bytes)) or not isinstance(fold, Sequence) or not fold:
            raise DenseCandidateValidationError(
                "validation_folds must contain non-empty unit-id sequences"
            )
        members = tuple(fold)
        if any(not isinstance(unit_id, str) or not unit_id for unit_id in members):
            raise DenseCandidateValidationError(
                "validation_folds must contain non-empty unit ids"
            )
        unknown = sorted(set(members) - expected)
        if unknown:
            raise DenseCandidateValidationError(
                f"validation_folds name an unknown unit: {unknown!r}"
            )
        result.append(tuple(sorted(members)))
    assigned = [unit_id for fold in result for unit_id in fold]
    if len(assigned) != len(expected) or set(assigned) != expected:
        raise DenseCandidateValidationError(
            "validation_folds must assign every unit exactly once"
        )
    fold_by_unit = {
        unit_id: fold_id for fold_id, fold in enumerate(result) for unit_id in fold
    }
    fold_by_query: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        fold_by_query[row.query_idx].add(fold_by_unit[row.unit_id])
    if any(len(fold_ids) != 1 for fold_ids in fold_by_query.values()):
        raise DenseCandidateValidationError(
            "validation_folds split a query_idx grouped block"
        )
    return tuple(result)


def _resolve_folds(
    rows: Sequence[A2tKbRow],
    *,
    validation_folds: Sequence[Sequence[str]] | None,
    seed: int | None,
    fold_count: int | None,
) -> tuple[tuple[tuple[str, ...], ...], str]:
    supplied = validation_folds is not None
    generated = seed is not None or fold_count is not None
    if supplied == generated:
        raise DenseCandidateValidationError(
            "provide exactly one fold source: validation_folds or seed and fold_count"
        )
    if supplied:
        assert validation_folds is not None
        return _validate_folds(rows, validation_folds), "caller_supplied_grouped_folds"
    if seed is None or fold_count is None:
        raise DenseCandidateValidationError(
            "seed and fold_count must both be supplied for generated folds"
        )
    try:
        folds = assign_grouped_validation_folds(
            rows,
            seed=seed,
            fold_count=fold_count,
        )
    except ValueError as error:
        raise DenseCandidateValidationError(str(error)) from error
    return _validate_folds(rows, folds), "existing_grouped_fold_assigner"


def _assignment_sha256(folds: Sequence[Sequence[str]]) -> str:
    payload = "\n".join(
        f"{fold_id}:{unit_id}" for fold_id, fold in enumerate(folds) for unit_id in fold
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _labels(row: A2tKbRow) -> tuple[str, ...]:
    return tuple(dict.fromkeys((row.tool_name, *row.extra_call_names)))


def _centroids(
    build: Sequence[A2tKbRow], vectors: Mapping[str, object]
) -> dict[str, tuple[object, ...]]:
    import numpy as np

    members: dict[tuple[str, str], list[object]] = defaultdict(list)
    for row in build:
        for tool in _labels(row):
            members[(tool, row.tier)].append(vectors[row.unit_id])
    by_tool: dict[str, list[object]] = defaultdict(list)
    for (tool, tier), values in sorted(members.items()):
        mean = np.asarray(values, dtype=np.float64).mean(axis=0)
        norm = float(np.linalg.norm(mean))
        if not math.isfinite(norm) or norm == 0.0:
            raise DenseCandidateValidationError(
                f"tool-tier centroid {tool!r}/{tier!r} must have nonzero norm"
            )
        by_tool[tool].append(mean / norm)
    return {tool: tuple(values) for tool, values in sorted(by_tool.items())}


def _dense_rankings(
    validation: Sequence[A2tKbRow],
    *,
    vectors: Mapping[str, Sequence[float]],
    centroids: Mapping[str, Sequence[Sequence[float]]],
    registry: Sequence[str],
) -> dict[str, tuple[tuple[str, ...], tuple[str, ...]]]:
    import numpy as np

    centroid_rows: list[Sequence[float]] = []
    centroid_tools: list[str] = []
    for tool in sorted(centroids):
        for centroid in centroids[tool]:
            centroid_rows.append(centroid)
            centroid_tools.append(tool)
    if not centroid_rows:
        raise DenseCandidateValidationError(
            "each fold build partition must produce at least one centroid"
        )
    query_matrix = np.asarray(
        [vectors[row.unit_id] for row in validation], dtype=np.float64
    )
    centroid_matrix = np.asarray(centroid_rows, dtype=np.float64)
    cosine_by_centroid = query_matrix @ centroid_matrix.T
    registry_index = {tool: index for index, tool in enumerate(registry)}
    scores = np.full((len(validation), len(registry)), -np.inf, dtype=np.float64)
    for centroid_index, tool in enumerate(centroid_tools):
        tool_index = registry_index[tool]
        scores[:, tool_index] = np.maximum(
            scores[:, tool_index], cosine_by_centroid[:, centroid_index]
        )
    return {
        row.unit_id: (
            tuple(
                sorted(
                    registry,
                    key=lambda tool: (
                        -float(scores[row_index, registry_index[tool]]),
                        tool,
                    ),
                )
            ),
            tuple(
                tool
                for tool in registry
                if float(scores[row_index, registry_index[tool]]) > 0.0
            ),
        )
        for row_index, row in enumerate(validation)
    }


def _exemplar_rankings(
    validation: Sequence[A2tKbRow],
    build: Sequence[A2tKbRow],
    *,
    vectors: Mapping[str, object],
    registry: Sequence[str],
    query_batch_size: int,
) -> tuple[dict[str, tuple[tuple[str, ...], tuple[str, ...]]], int, int]:
    import numpy as np

    build_matrix = np.asarray([vectors[row.unit_id] for row in build], dtype=np.float64)
    build_indices_by_tool: dict[str, list[int]] = defaultdict(list)
    for build_index, row in enumerate(build):
        for tool in _labels(row):
            build_indices_by_tool[tool].append(build_index)
    registry_index = {tool: index for index, tool in enumerate(registry)}
    result: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
    maximum_batch_rows = 0
    batch_count = 0
    for start in range(0, len(validation), query_batch_size):
        batch = validation[start : start + query_batch_size]
        maximum_batch_rows = max(maximum_batch_rows, len(batch))
        batch_count += 1
        query_matrix = np.asarray(
            [vectors[row.unit_id] for row in batch], dtype=np.float64
        )
        cosine_by_build_row = query_matrix @ build_matrix.T
        scores = np.full((len(batch), len(registry)), -np.inf, dtype=np.float64)
        for tool, build_indices in build_indices_by_tool.items():
            scores[:, registry_index[tool]] = np.max(
                cosine_by_build_row[:, build_indices], axis=1
            )
        for batch_index, row in enumerate(batch):
            ranking = tuple(
                sorted(
                    registry,
                    key=lambda tool: (
                        -float(scores[batch_index, registry_index[tool]]),
                        tool,
                    ),
                )
            )
            positive = tuple(
                tool
                for tool in registry
                if float(scores[batch_index, registry_index[tool]]) > 0.0
            )
            result[row.unit_id] = (ranking, positive)
    return result, maximum_batch_rows, batch_count


def reciprocal_rank_fusion(
    left: Sequence[str], right: Sequence[str], *, constant: int = RRF_CONSTANT
) -> tuple[str, ...]:
    """Fuse two complete unique rankings with deterministic name tie-breaking."""

    if type(constant) is not int or constant <= 0:
        raise DenseCandidateValidationError("RRF constant must be a positive integer")
    if (
        isinstance(left, (str, bytes))
        or isinstance(right, (str, bytes))
        or not isinstance(left, Sequence)
        or not isinstance(right, Sequence)
        or not left
        or set(left) != set(right)
        or len(left) != len(set(left))
        or len(right) != len(set(right))
        or any(not isinstance(name, str) or not name for name in (*left, *right))
    ):
        raise DenseCandidateValidationError(
            "RRF inputs must be complete unique rankings over the same labels"
        )
    left_rank = {tool: rank for rank, tool in enumerate(left, start=1)}
    right_rank = {tool: rank for rank, tool in enumerate(right, start=1)}
    return tuple(
        sorted(
            left,
            key=lambda tool: (
                -(
                    1.0 / (constant + left_rank[tool])
                    + 1.0 / (constant + right_rank[tool])
                ),
                tool,
            ),
        )
    )


def _sample(
    row: A2tKbRow,
    ranking: Sequence[str],
    supported_tools: Sequence[str],
    *,
    maximum_build_token_jaccard: float,
) -> dict[str, object]:
    call_names = (row.tool_name, *row.extra_call_names)
    required = tuple(dict.fromkeys(call_names))
    return {
        "unit_id": row.unit_id,
        "tier": row.tier,
        "required_tool_names": list(required),
        "required_call_occurrence_count": len(call_names),
        "duplicate_required_call_occurrence_count": len(call_names) - len(required),
        "ranked_tool_names": list(ranking),
        "positive_score_tool_names": list(supported_tools),
        "maximum_build_token_jaccard": maximum_build_token_jaccard,
    }


def _k_metrics(
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


def _method_report(
    samples: Sequence[Mapping[str, object]],
    fold_samples: Sequence[Sequence[Mapping[str, object]]],
    *,
    k_values: Sequence[int],
    registry_count: int,
) -> dict[str, object]:
    tiers = sorted({str(sample["tier"]) for sample in samples})
    per_tier = {
        tier: _k_metrics(
            [sample for sample in samples if sample["tier"] == tier],
            k_values=k_values,
            registry_count=registry_count,
        )
        for tier in tiers
    }
    single = [
        sample
        for sample in samples
        if int(sample["required_call_occurrence_count"]) == 1
    ]
    multi = [
        sample
        for sample in samples
        if int(sample["required_call_occurrence_count"]) > 1
    ]
    near_duplicates = [
        sample
        for sample in samples
        if float(sample["maximum_build_token_jaccard"]) >= NEAR_DUPLICATE_THRESHOLD
    ]
    no_near_duplicates = [
        sample
        for sample in samples
        if float(sample["maximum_build_token_jaccard"]) < NEAR_DUPLICATE_THRESHOLD
    ]
    per_fold = [
        {
            "fold_id": fold_id,
            "validation_unit_count": len(values),
            "k_metrics": _k_metrics(
                values,
                k_values=k_values,
                registry_count=registry_count,
            ),
        }
        for fold_id, values in enumerate(fold_samples)
    ]
    worst_fold = {
        str(k): {
            "minimum_full_set_coverage": min(
                fold["k_metrics"][str(k)]["full_set_coverage"] for fold in per_fold
            ),
            "minimum_required_item_recall": min(
                fold["k_metrics"][str(k)]["required_item_recall"] for fold in per_fold
            ),
            "maximum_mean_distractor_burden": max(
                fold["k_metrics"][str(k)]["mean_distractor_burden"] for fold in per_fold
            ),
        }
        for k in k_values
    }
    return {
        "pooled": {
            "k_metrics": _k_metrics(
                samples,
                k_values=k_values,
                registry_count=registry_count,
            ),
            "per_tier": per_tier,
            "single_call": {
                "unit_count": len(single),
                "k_metrics": _k_metrics(
                    single,
                    k_values=k_values,
                    registry_count=registry_count,
                ),
            },
            "multi_call": {
                "unit_count": len(multi),
                "k_metrics": _k_metrics(
                    multi,
                    k_values=k_values,
                    registry_count=registry_count,
                ),
            },
            "near_duplicate_sensitivity": {
                "threshold": NEAR_DUPLICATE_THRESHOLD,
                "metric": "maximum token-set Jaccard against the fold build index",
                "near_duplicate": {
                    "unit_count": len(near_duplicates),
                    "k_metrics": _k_metrics(
                        near_duplicates,
                        k_values=k_values,
                        registry_count=registry_count,
                    ),
                },
                "no_near_duplicate": {
                    "unit_count": len(no_near_duplicates),
                    "k_metrics": _k_metrics(
                        no_near_duplicates,
                        k_values=k_values,
                        registry_count=registry_count,
                    ),
                },
            },
        },
        "per_fold": per_fold,
        "worst_fold": worst_fold,
    }


def analyze_dense_candidate_validation(
    *,
    construction_rows: Sequence[A2tKbRow],
    vectors_by_unit_id: Mapping[str, Sequence[Real]],
    registry_tool_names: Sequence[str],
    k_grid: Sequence[int],
    validation_folds: Sequence[Sequence[str]] | None = None,
    seed: int | None = None,
    fold_count: int | None = None,
    query_batch_size: int = DEFAULT_QUERY_BATCH_SIZE,
) -> DenseCandidateValidationAudit:
    """Compare BM25, dense centroid/exemplar, and paired RRF out of fold."""

    rows = _validate_rows(construction_rows)
    registry = _validate_registry(registry_tool_names, rows)
    k_values = _validate_k_grid(k_grid)
    if type(query_batch_size) is not int or query_batch_size <= 0:
        raise DenseCandidateValidationError(
            "query_batch_size must be a positive integer"
        )
    vectors, dimension, vector_mapping_sha256 = _validate_vectors(
        rows, vectors_by_unit_id
    )
    folds, fold_source = _resolve_folds(
        rows,
        validation_folds=validation_folds,
        seed=seed,
        fold_count=fold_count,
    )
    rows_by_id = {row.unit_id: row for row in rows}
    samples_by_method: dict[str, list[dict[str, object]]] = {
        "bm25": [],
        "dense": [],
        "rrf": [],
        "dense_exemplar": [],
        "rrf_exemplar": [],
    }
    fold_samples_by_method: dict[str, list[list[dict[str, object]]]] = {
        method: [] for method in samples_by_method
    }
    fold_design: list[dict[str, object]] = []
    for fold_id, fold in enumerate(folds):
        validation_ids = frozenset(fold)
        validation = tuple(rows_by_id[unit_id] for unit_id in fold)
        build = tuple(row for row in rows if row.unit_id not in validation_ids)
        lexical = analyze_label_candidate_reduction(
            construction_rows=build,
            validation_rows=validation,
            registry_tool_names=registry,
            k_grid=k_values,
        )
        lexical_by_id = {
            sample["unit_id"]: sample for sample in lexical.report["samples"]
        }
        centroid_by_tool = _centroids(build, vectors)
        centroid_count = sum(len(values) for values in centroid_by_tool.values())
        dense_ranking_by_id = _dense_rankings(
            validation,
            vectors=vectors,
            centroids=centroid_by_tool,
            registry=registry,
        )
        exemplar_ranking_by_id, maximum_batch_rows, exemplar_batch_count = (
            _exemplar_rankings(
                validation,
                build,
                vectors=vectors,
                registry=registry,
                query_batch_size=query_batch_size,
            )
        )
        jaccard_by_unit = maximum_token_jaccard(build, validation)
        fold_design.append(
            {
                "fold_id": fold_id,
                "build_unit_count": len(build),
                "validation_unit_count": len(validation),
                "tool_tier_centroid_count": centroid_count,
                "tool_with_centroid_count": len(centroid_by_tool),
                "maximum_exemplar_query_batch_rows": maximum_batch_rows,
                "exemplar_query_batch_count": exemplar_batch_count,
                "maximum_exemplar_similarity_matrix_cells": (
                    maximum_batch_rows * len(build)
                ),
            }
        )
        current = {method: [] for method in samples_by_method}
        for row in validation:
            lexical_sample = lexical_by_id[row.unit_id]
            bm25_ranking = tuple(lexical_sample["ranked_tool_names"])
            bm25_supported = tuple(lexical_sample["positive_score_tool_names"])
            dense_ranking, dense_positive = dense_ranking_by_id[row.unit_id]
            exemplar_ranking, exemplar_positive = exemplar_ranking_by_id[row.unit_id]
            rrf_ranking = reciprocal_rank_fusion(
                bm25_ranking,
                dense_ranking,
                constant=RRF_CONSTANT,
            )
            rrf_supported = tuple(sorted(set(bm25_supported) | set(dense_positive)))
            rrf_exemplar_ranking = reciprocal_rank_fusion(
                bm25_ranking,
                exemplar_ranking,
                constant=RRF_CONSTANT,
            )
            rrf_exemplar_supported = tuple(
                sorted(set(bm25_supported) | set(exemplar_positive))
            )
            sample_kwargs = {
                "maximum_build_token_jaccard": jaccard_by_unit[row.unit_id]
            }
            current["bm25"].append(
                _sample(row, bm25_ranking, bm25_supported, **sample_kwargs)
            )
            current["dense"].append(
                _sample(row, dense_ranking, dense_positive, **sample_kwargs)
            )
            current["rrf"].append(
                _sample(row, rrf_ranking, rrf_supported, **sample_kwargs)
            )
            current["dense_exemplar"].append(
                _sample(row, exemplar_ranking, exemplar_positive, **sample_kwargs)
            )
            current["rrf_exemplar"].append(
                _sample(
                    row,
                    rrf_exemplar_ranking,
                    rrf_exemplar_supported,
                    **sample_kwargs,
                )
            )
        for method in samples_by_method:
            samples_by_method[method].extend(current[method])
            fold_samples_by_method[method].append(current[method])

    method_reports = {
        method: _method_report(
            samples_by_method[method],
            fold_samples_by_method[method],
            k_values=k_values,
            registry_count=len(registry),
        )
        for method in ("bm25", "dense", "rrf", "dense_exemplar", "rrf_exemplar")
    }
    report: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "scope": {
            "construction_training_rows_only": True,
            "caller_supplied_precomputed_vectors_only": True,
            "gold_used_for_post_ranking_measurement_only": True,
            "label_candidate_retrieval_only": True,
            "runtime_eligible": False,
            "model_consumption_upper_bound": False,
            "model_contacts": 0,
            "embedding_model_contacts": 0,
            "network_contacts": 0,
            "scorer_contacts": 0,
        },
        "provenance": {
            "vectors_exactly_cover_construction_units": True,
            "vectors_validated_finite_equal_dimension_nonzero": True,
            "embedding_identity_asserted_by_this_module": False,
            "embedding_receipt_verified_by_this_module": False,
            "caller_retains_embedding_identity_and_receipt_responsibility": True,
            "validated_float64_vector_mapping_sha256": vector_mapping_sha256,
            "vector_values_emitted": False,
            "source_text_emitted": False,
            "candidate_rankings_emitted": False,
        },
        "split_policy": {
            "source": fold_source,
            "seed": seed,
            "assignment_sha256": _assignment_sha256(folds),
            "query_idx_group_integrity_validated": True,
            "every_unit_assigned_exactly_once": True,
        },
        "population": {
            "unit_count": len(rows),
            "registry_label_count": len(registry),
            "fold_count": len(folds),
            "vector_dimension": dimension,
        },
        "dense_design": {
            "unit_vectors_l2_normalized_before_aggregation": True,
            "centroid_partition": "registered tool name and construction tier",
            "centroids_l2_normalized": True,
            "batched_matrix_cosine": True,
            "primary_and_extra_labels_attached": True,
            "tool_score": "maximum cosine over available build-only tool-tier centroids",
            "unobserved_build_tools_rank_after_observed_tools": True,
            "ranking_tie_break": "ascending registered tool name",
        },
        "dense_exemplar_design": {
            "non_parametric": True,
            "build_unit_vectors_l2_normalized": True,
            "primary_and_extra_labels_attached": True,
            "tool_score": (
                "maximum cosine over every build-row vector attached to the tool"
            ),
            "query_batch_size": query_batch_size,
            "similarity_matrix_dtype": "float64",
            "full_query_by_build_matrix_materialized": False,
            "build_vector_matrix_materialized_once_per_fold": True,
            "ranking_tie_break": "ascending registered tool name",
        },
        "hybrid_design": {
            "method": "equal-weight reciprocal-rank fusion",
            "inputs": ["bm25", "dense"],
            "rrf_constant": RRF_CONSTANT,
            "ranking_tie_break": "ascending registered tool name",
        },
        "hybrid_exemplar_design": {
            "method": "equal-weight reciprocal-rank fusion",
            "inputs": ["bm25", "dense_exemplar"],
            "rrf_constant": RRF_CONSTANT,
            "ranking_tie_break": "ascending registered tool name",
        },
        "fold_design": fold_design,
        "methods": method_reports,
    }
    canonical_json = json.dumps(
        report,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    return DenseCandidateValidationAudit(
        report=report,
        canonical_json=canonical_json,
    )


__all__ = [
    "DenseCandidateValidationAudit",
    "DenseCandidateValidationError",
    "DEFAULT_QUERY_BATCH_SIZE",
    "RESULT_SCHEMA",
    "RRF_CONSTANT",
    "analyze_dense_candidate_validation",
    "reciprocal_rank_fusion",
]
