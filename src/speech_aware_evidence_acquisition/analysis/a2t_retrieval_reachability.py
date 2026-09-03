"""Pure post-seal retrieval-coverage oracle analysis for Audio2Tool.

The caller supplies already-sealed ranked retrieval identities and gold-required
identities that become available only for post-seal analysis.  This module has
no file, network, model, scorer, or runtime access.  Its output measures
retrieval coverage; it is not a model-consumption upper bound and must never be
used to choose runtime evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from types import MappingProxyType
from typing import Mapping, Sequence


RESULT_SCHEMA = "saea-a2t-postseal-retrieval-reachability-v1"
DIMENSIONS = ("tool", "skeleton", "value_rule")
SCOPE_NOTE = (
    "This post-seal result is a retrieval-coverage oracle, not a model-consumption "
    "upper bound; gold-required identities and this audit must never be used at runtime."
)


class RetrievalReachabilityError(ValueError):
    """A seal, identity, duplicate, type, or audit-shape invariant failed."""


@dataclass(frozen=True)
class RetrievalReachabilitySample:
    """One sealed retrieval result paired with post-seal required identities."""

    sample_id: str
    retrieval_sealed: bool
    required_tool_ids: Sequence[str]
    ranked_tool_ids: Sequence[str]
    required_skeleton_ids: Sequence[str]
    ranked_skeleton_ids: Sequence[str]
    required_value_rule_ids: Sequence[str]
    ranked_value_rule_ids: Sequence[str]


@dataclass(frozen=True)
class DimensionReachability:
    """One sample's exact set-reachability metrics for one identity dimension."""

    required_ids: tuple[str, ...]
    retrieved_ids_at_k: tuple[str, ...]
    matched_required_ids_at_k: tuple[str, ...]
    required_count: int
    retrieved_count_at_k: int
    matched_required_count_at_k: int
    required_item_recall_at_k: float
    full_set_coverage_at_k: bool
    distractor_burden_at_k: int
    precision_at_k: float

    def as_json(self) -> dict[str, object]:
        """Return a JSON-compatible metric record."""

        return {
            "required_ids": list(self.required_ids),
            "retrieved_ids_at_k": list(self.retrieved_ids_at_k),
            "matched_required_ids_at_k": list(self.matched_required_ids_at_k),
            "required_count": self.required_count,
            "retrieved_count_at_k": self.retrieved_count_at_k,
            "matched_required_count_at_k": self.matched_required_count_at_k,
            "required_item_recall_at_k": self.required_item_recall_at_k,
            "full_set_coverage_at_k": self.full_set_coverage_at_k,
            "distractor_burden_at_k": self.distractor_burden_at_k,
            "precision_at_k": self.precision_at_k,
        }


@dataclass(frozen=True)
class SampleReachability:
    """Deterministically ordered per-dimension metrics for one sample."""

    sample_id: str
    metrics: Mapping[str, DimensionReachability]

    def as_json(self) -> dict[str, object]:
        """Return a JSON-compatible sample record."""

        return {
            "sample_id": self.sample_id,
            "metrics": {
                dimension: self.metrics[dimension].as_json() for dimension in DIMENSIONS
            },
        }


@dataclass(frozen=True)
class AggregateDimensionReachability:
    """Micro ratios and sample-level full-set coverage for one dimension."""

    sample_count: int
    total_required_count: int
    total_retrieved_count_at_k: int
    total_matched_required_count_at_k: int
    required_item_recall_at_k: float
    full_set_coverage_at_k: float
    total_distractor_burden_at_k: int
    mean_distractor_burden_at_k: float
    precision_at_k: float

    def as_json(self) -> dict[str, object]:
        """Return a JSON-compatible aggregate metric record."""

        return {
            "sample_count": self.sample_count,
            "total_required_count": self.total_required_count,
            "total_retrieved_count_at_k": self.total_retrieved_count_at_k,
            "total_matched_required_count_at_k": (
                self.total_matched_required_count_at_k
            ),
            "required_item_recall_at_k": self.required_item_recall_at_k,
            "full_set_coverage_at_k": self.full_set_coverage_at_k,
            "total_distractor_burden_at_k": self.total_distractor_burden_at_k,
            "mean_distractor_burden_at_k": self.mean_distractor_burden_at_k,
            "precision_at_k": self.precision_at_k,
        }


@dataclass(frozen=True)
class RetrievalReachabilityAudit:
    """Complete deterministic post-seal retrieval-coverage audit."""

    k: int
    samples: tuple[SampleReachability, ...]
    aggregate: Mapping[str, AggregateDimensionReachability]
    schema: str = RESULT_SCHEMA
    analysis_phase: str = "post-seal"
    runtime_eligible: bool = False
    upper_bound_kind: str = "retrieval-coverage-oracle"
    scope_note: str = SCOPE_NOTE
    dimensions: tuple[str, ...] = DIMENSIONS

    def as_json(self) -> dict[str, object]:
        """Return a JSON-compatible audit in fixed semantic order."""

        return {
            "schema": self.schema,
            "analysis_phase": self.analysis_phase,
            "runtime_eligible": self.runtime_eligible,
            "upper_bound_kind": self.upper_bound_kind,
            "scope_note": self.scope_note,
            "k": self.k,
            "dimensions": list(self.dimensions),
            "samples": [sample.as_json() for sample in self.samples],
            "aggregate": {
                dimension: self.aggregate[dimension].as_json()
                for dimension in DIMENSIONS
            },
        }

    def canonical_json(self) -> str:
        """Serialize the audit as deterministic canonical JSON."""

        return json.dumps(
            self.as_json(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )


_FIELD_PAIRS = {
    "tool": ("required_tool_ids", "ranked_tool_ids"),
    "skeleton": ("required_skeleton_ids", "ranked_skeleton_ids"),
    "value_rule": ("required_value_rule_ids", "ranked_value_rule_ids"),
}


def _validate_id_sequence(value: object, label: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise RetrievalReachabilityError(f"{label} must be a sequence of identities")
    identities = tuple(value)
    if any(not isinstance(item, str) or not item for item in identities):
        raise RetrievalReachabilityError(
            f"{label} identities must each be non-empty text"
        )
    if len(set(identities)) != len(identities):
        raise RetrievalReachabilityError(f"{label} contains a duplicate identity")
    return identities


def _dimension_metrics(
    *,
    required: tuple[str, ...],
    ranked: tuple[str, ...],
    k: int,
) -> DimensionReachability:
    retrieved = ranked[:k]
    required_set = set(required)
    matched = tuple(item for item in retrieved if item in required_set)
    matched_count = len(matched)
    required_count = len(required)
    retrieved_count = len(retrieved)
    recall = matched_count / required_count if required_count else 1.0
    precision = (
        matched_count / retrieved_count
        if retrieved_count
        else (1.0 if required_count == 0 else 0.0)
    )
    return DimensionReachability(
        required_ids=required,
        retrieved_ids_at_k=retrieved,
        matched_required_ids_at_k=matched,
        required_count=required_count,
        retrieved_count_at_k=retrieved_count,
        matched_required_count_at_k=matched_count,
        required_item_recall_at_k=recall,
        full_set_coverage_at_k=matched_count == required_count,
        distractor_burden_at_k=retrieved_count - matched_count,
        precision_at_k=precision,
    )


def _aggregate_dimension(
    metrics: Sequence[DimensionReachability],
) -> AggregateDimensionReachability:
    sample_count = len(metrics)
    required = sum(metric.required_count for metric in metrics)
    retrieved = sum(metric.retrieved_count_at_k for metric in metrics)
    matched = sum(metric.matched_required_count_at_k for metric in metrics)
    distractors = sum(metric.distractor_burden_at_k for metric in metrics)
    recall = matched / required if required else 1.0
    precision = matched / retrieved if retrieved else (1.0 if required == 0 else 0.0)
    return AggregateDimensionReachability(
        sample_count=sample_count,
        total_required_count=required,
        total_retrieved_count_at_k=retrieved,
        total_matched_required_count_at_k=matched,
        required_item_recall_at_k=recall,
        full_set_coverage_at_k=(
            sum(metric.full_set_coverage_at_k for metric in metrics) / sample_count
        ),
        total_distractor_burden_at_k=distractors,
        mean_distractor_burden_at_k=distractors / sample_count,
        precision_at_k=precision,
    )


def audit_retrieval_reachability_at_k(
    *,
    samples: Sequence[RetrievalReachabilitySample],
    k: int,
) -> RetrievalReachabilityAudit:
    """Measure sealed retrieval coverage against post-seal gold requirements.

    Required-item recall and precision are micro-aggregated across samples.
    Full-set coverage is the fraction of samples for which every required
    identity appears in the top-k list.  Distractor burden counts retrieved
    identities outside the required set.  An empty required set has vacuous
    recall and full-set coverage; an empty retrieved set has precision one only
    when its required set is also empty.
    """

    if type(k) is not int or k < 1:
        raise RetrievalReachabilityError("k must be a positive integer")
    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
        raise RetrievalReachabilityError("samples must be a non-empty sequence")
    if not samples:
        raise RetrievalReachabilityError("samples must be a non-empty sequence")

    validated: list[
        tuple[str, Mapping[str, tuple[tuple[str, ...], tuple[str, ...]]]]
    ] = []
    sample_ids: set[str] = set()
    for index, sample in enumerate(samples):
        if not isinstance(sample, RetrievalReachabilitySample):
            raise RetrievalReachabilityError(
                f"samples[{index}] must be a RetrievalReachabilitySample"
            )
        if not isinstance(sample.sample_id, str) or not sample.sample_id:
            raise RetrievalReachabilityError(f"samples[{index}].sample_id is malformed")
        if sample.sample_id in sample_ids:
            raise RetrievalReachabilityError(
                f"duplicate sample_id {sample.sample_id!r}"
            )
        sample_ids.add(sample.sample_id)
        if sample.retrieval_sealed is not True:
            if not isinstance(sample.retrieval_sealed, bool):
                raise RetrievalReachabilityError(
                    f"sample {sample.sample_id!r} retrieval_sealed must be boolean"
                )
            raise RetrievalReachabilityError(
                f"sample {sample.sample_id!r} retrieval is not sealed"
            )

        dimensions: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {}
        for dimension, (required_field, ranked_field) in _FIELD_PAIRS.items():
            dimensions[dimension] = (
                _validate_id_sequence(
                    getattr(sample, required_field),
                    f"sample {sample.sample_id!r} {required_field}",
                ),
                _validate_id_sequence(
                    getattr(sample, ranked_field),
                    f"sample {sample.sample_id!r} {ranked_field}",
                ),
            )
        validated.append((sample.sample_id, MappingProxyType(dimensions)))

    per_sample: list[SampleReachability] = []
    for sample_id, dimensions in sorted(validated, key=lambda item: item[0]):
        metrics = {
            dimension: _dimension_metrics(
                required=dimensions[dimension][0],
                ranked=dimensions[dimension][1],
                k=k,
            )
            for dimension in DIMENSIONS
        }
        per_sample.append(
            SampleReachability(
                sample_id=sample_id,
                metrics=MappingProxyType(metrics),
            )
        )

    aggregate = {
        dimension: _aggregate_dimension(
            tuple(sample.metrics[dimension] for sample in per_sample)
        )
        for dimension in DIMENSIONS
    }
    return RetrievalReachabilityAudit(
        k=k,
        samples=tuple(per_sample),
        aggregate=MappingProxyType(aggregate),
    )


__all__ = [
    "AggregateDimensionReachability",
    "DIMENSIONS",
    "DimensionReachability",
    "RESULT_SCHEMA",
    "RetrievalReachabilityAudit",
    "RetrievalReachabilityError",
    "RetrievalReachabilitySample",
    "SCOPE_NOTE",
    "SampleReachability",
    "audit_retrieval_reachability_at_k",
]
