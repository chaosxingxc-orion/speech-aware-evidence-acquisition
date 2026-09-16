"""Pure descriptive comparison of paired candidate-decision rows.

Source verification and row construction belong to callers. This module only
validates a complete ordered cohort and emits sufficient numeric counts for
descriptive reporting and the shared pooled-ratio comparison.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias


CANDIDATE_DECISION_COMPARISON_SCHEMA = "saea-candidate-decision-comparison-v1"
_METADATA_FIELDS = frozenset({"sample_id", "scenario", "speaker"})


class CandidateDecisionComparisonError(ValueError):
    """A candidate row, metadata row, or paired cohort is inconsistent."""


@dataclass(frozen=True)
class CandidateDecisionRow:
    """One arm's candidate availability and final-decision diagnostics."""

    sample_id: str
    candidate_available: bool
    candidate_width: int | None
    gold_covered: bool
    final_correct: bool
    final_in_candidates: bool | None

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, str) or not self.sample_id.strip():
            raise CandidateDecisionComparisonError("sample_id must be nonempty text")
        for field in ("candidate_available", "gold_covered", "final_correct"):
            if type(getattr(self, field)) is not bool:
                raise CandidateDecisionComparisonError(f"{field} must be boolean")
        if self.final_in_candidates is not None and type(self.final_in_candidates) is not bool:
            raise CandidateDecisionComparisonError(
                "final_in_candidates must be boolean or None"
            )
        if not self.candidate_available:
            if self.candidate_width is not None:
                raise CandidateDecisionComparisonError(
                    "unavailable candidate must have width None"
                )
            if self.gold_covered:
                raise CandidateDecisionComparisonError(
                    "unavailable candidate must have gold_covered False"
                )
            if self.final_in_candidates is not None:
                raise CandidateDecisionComparisonError(
                    "unavailable candidate must have membership None"
                )
            return
        if (
            isinstance(self.candidate_width, bool)
            or not isinstance(self.candidate_width, int)
            or self.candidate_width < 1
        ):
            raise CandidateDecisionComparisonError(
                "available candidate must have a positive width"
            )
        if self.final_correct and self.final_in_candidates != self.gold_covered:
            raise CandidateDecisionComparisonError(
                "correct final membership must equal gold coverage"
            )


Ratio: TypeAlias = dict[str, int | float | None]
ArmSummary: TypeAlias = dict[str, object]


def _rows(value: object, label: str) -> tuple[CandidateDecisionRow, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CandidateDecisionComparisonError(f"{label} rows must be an ordered sequence")
    rows = tuple(value)
    if not rows:
        raise CandidateDecisionComparisonError("candidate comparison roster must be nonempty")
    if any(not isinstance(row, CandidateDecisionRow) for row in rows):
        raise CandidateDecisionComparisonError(
            f"{label} rows must contain only CandidateDecisionRow values"
        )
    return rows


def _metadata_rows(
    value: object,
) -> tuple[Mapping[str, object], ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CandidateDecisionComparisonError(
            "metadata must be an ordered sequence"
        )
    rows = tuple(value)
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != _METADATA_FIELDS:
            raise CandidateDecisionComparisonError(
                f"metadata row {index} must contain exactly "
                "{sample_id, scenario, speaker}"
            )
        for field in ("sample_id", "scenario", "speaker"):
            item = row[field]
            if not isinstance(item, str) or not item.strip():
                raise CandidateDecisionComparisonError(
                    f"metadata {field} must be nonempty text"
                )
    return rows


def _ratio(numerator: int, denominator: int) -> Ratio:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "ratio": None if denominator == 0 else numerator / denominator,
    }


def _count_ratio(count: int, denominator: int) -> dict[str, int | float]:
    return {
        "count": count,
        "denominator": denominator,
        "ratio": count / denominator,
    }


def _arm_summary(
    rows: tuple[CandidateDecisionRow, ...],
    *,
    common_covered: tuple[bool, ...],
) -> ArmSummary:
    denominator = len(rows)
    available = sum(row.candidate_available for row in rows)
    widths = [
        row.candidate_width
        for row in rows
        if row.candidate_available and row.candidate_width is not None
    ]
    in_candidates = sum(row.final_in_candidates is True for row in rows)
    outside_candidates = sum(row.final_in_candidates is False for row in rows)
    unavailable_membership = sum(row.final_in_candidates is None for row in rows)
    covered = sum(row.gold_covered for row in rows)
    own_correct = sum(row.gold_covered and row.final_correct for row in rows)
    common_denominator = sum(common_covered)
    common_correct = sum(
        common and row.final_correct
        for row, common in zip(rows, common_covered, strict=True)
    )
    final_correct = sum(row.final_correct for row in rows)
    return {
        "candidate_availability": {
            "available": available,
            "unavailable": denominator - available,
            "denominator": denominator,
            "available_ratio": available / denominator,
            "unavailable_ratio": (denominator - available) / denominator,
        },
        "candidate_width": {
            "count": len(widths),
            "sum": sum(widths),
            "min": min(widths) if widths else None,
            "max": max(widths) if widths else None,
            "mean": sum(widths) / len(widths) if widths else None,
            "histogram": {str(width): widths.count(width) for width in sorted(set(widths))},
        },
        "final_membership": {
            "in_candidates": in_candidates,
            "outside_candidates": outside_candidates,
            "unavailable_or_invalid": unavailable_membership,
            "denominator": denominator,
            "in_candidates_ratio": in_candidates / denominator,
            "outside_candidates_ratio": outside_candidates / denominator,
            "unavailable_or_invalid_ratio": unavailable_membership / denominator,
        },
        "coverage": _ratio(covered, denominator),
        "own_covered_final_accuracy": _ratio(own_correct, covered),
        "common_covered_final_accuracy": _ratio(common_correct, common_denominator),
        "final_accuracy": _ratio(final_correct, denominator),
    }


def _cohort_summary(
    left: tuple[CandidateDecisionRow, ...],
    right: tuple[CandidateDecisionRow, ...],
) -> dict[str, object]:
    denominator = len(left)
    common_covered = tuple(
        left_row.gold_covered and right_row.gold_covered
        for left_row, right_row in zip(left, right, strict=True)
    )
    gained = sum(
        not left_row.gold_covered and right_row.gold_covered
        for left_row, right_row in zip(left, right, strict=True)
    )
    lost = sum(
        left_row.gold_covered and not right_row.gold_covered
        for left_row, right_row in zip(left, right, strict=True)
    )
    retained = sum(common_covered)
    neither = denominator - gained - lost - retained
    return {
        "count": denominator,
        "left": _arm_summary(left, common_covered=common_covered),
        "right": _arm_summary(right, common_covered=common_covered),
        "coverage_partition": {
            "gained": _count_ratio(gained, denominator),
            "lost": _count_ratio(lost, denominator),
            "retained": _count_ratio(retained, denominator),
            "neither": _count_ratio(neither, denominator),
        },
    }


def _ratio_row(
    row: CandidateDecisionRow,
    *,
    common_covered: bool,
) -> dict[str, int]:
    own_covered = row.gold_covered
    return {
        "coverage_numerator": int(row.gold_covered),
        "coverage_denominator": 1,
        "own_covered_final_numerator": int(own_covered and row.final_correct),
        "own_covered_final_denominator": int(own_covered),
        "common_covered_final_numerator": int(
            common_covered and row.final_correct
        ),
        "common_covered_final_denominator": int(common_covered),
        "final_accuracy_numerator": int(row.final_correct),
        "final_accuracy_denominator": 1,
    }


def compare_candidate_decisions(
    left_rows: Sequence[CandidateDecisionRow],
    right_rows: Sequence[CandidateDecisionRow],
    *,
    metadata: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Validate and describe two arms on one exact ordered sample roster."""

    left = _rows(left_rows, "left")
    right = _rows(right_rows, "right")
    left_ids = tuple(row.sample_id for row in left)
    right_ids = tuple(row.sample_id for row in right)
    if (
        len(left_ids) != len(set(left_ids))
        or len(right_ids) != len(set(right_ids))
    ):
        raise CandidateDecisionComparisonError(
            "candidate comparison roster sample IDs must be unique"
        )
    if left_ids != right_ids:
        raise CandidateDecisionComparisonError(
            "left and right must have the exact same ordered roster"
        )
    metadata_rows = _metadata_rows(metadata)
    metadata_ids = tuple(str(row["sample_id"]) for row in metadata_rows)
    if metadata_ids != left_ids:
        raise CandidateDecisionComparisonError(
            "metadata roster must exactly match the ordered candidate roster"
        )

    by_scenario: dict[str, object] = {}
    scenarios = sorted({str(row["scenario"]) for row in metadata_rows})
    for scenario in scenarios:
        indices = tuple(
            index
            for index, row in enumerate(metadata_rows)
            if row["scenario"] == scenario
        )
        by_scenario[scenario] = _cohort_summary(
            tuple(left[index] for index in indices),
            tuple(right[index] for index in indices),
        )

    common_covered = tuple(
        left_row.gold_covered and right_row.gold_covered
        for left_row, right_row in zip(left, right, strict=True)
    )
    return {
        "schema": CANDIDATE_DECISION_COMPARISON_SCHEMA,
        "roster_count": len(left),
        "full_cohort": _cohort_summary(left, right),
        "by_scenario": by_scenario,
        "ratio_rows": {
            "left": {
                row.sample_id: _ratio_row(row, common_covered=common)
                for row, common in zip(left, common_covered, strict=True)
            },
            "right": {
                row.sample_id: _ratio_row(row, common_covered=common)
                for row, common in zip(right, common_covered, strict=True)
            },
        },
    }
