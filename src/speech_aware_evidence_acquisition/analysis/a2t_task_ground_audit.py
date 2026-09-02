"""Prospective qualification rules and landed-surface diagnosis for A2T ground."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping

MIN_EXACT_MATCH = 0.90
TARGET_EXACT_MATCH = 0.95
MIN_TOOL_ACCURACY = 0.95
MIN_SLOT_MICRO_F1 = 0.90
MIN_PARSE_RATE = 0.99


@dataclass(frozen=True)
class GroundMetrics:
    """Official quality channels for one complete ground manifest."""

    n_samples: int
    exact_count: int
    tool_correct_count: int
    parse_failures: int
    slot_micro_f1: float

    def __post_init__(self) -> None:
        if (
            isinstance(self.n_samples, bool)
            or not isinstance(self.n_samples, int)
            or self.n_samples <= 0
        ):
            raise ValueError("n_samples must be a positive integer")
        for field, value in (
            ("exact_count", self.exact_count),
            ("tool_correct_count", self.tool_correct_count),
            ("parse_failures", self.parse_failures),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 0 <= value <= self.n_samples
            ):
                raise ValueError(f"{field} must be an integer in [0, n_samples]")
        if (
            isinstance(self.slot_micro_f1, bool)
            or not isinstance(self.slot_micro_f1, (int, float))
            or not 0.0 <= float(self.slot_micro_f1) <= 1.0
        ):
            raise ValueError("slot_micro_f1 must lie in [0, 1]")

    @property
    def rates(self) -> dict[str, float]:
        return {
            "exact_match": self.exact_count / self.n_samples,
            "tool_accuracy": self.tool_correct_count / self.n_samples,
            "slot_micro_f1": float(self.slot_micro_f1),
            "parse_rate": 1.0 - self.parse_failures / self.n_samples,
        }

    def as_json(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GroundQualification:
    """Mechanical decision under the owner-set ground quality contract."""

    rates: Mapping[str, float]
    gates: Mapping[str, bool]
    minimum_ground_passed: bool
    target_95_exact_passed: bool

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def qualify_ground(metrics: GroundMetrics) -> GroundQualification:
    """Apply the frozen floor to one complete official-score manifest."""

    rates = metrics.rates
    gates = {
        "exact_at_least_90_percent": rates["exact_match"] >= MIN_EXACT_MATCH,
        "tool_at_least_95_percent": rates["tool_accuracy"] >= MIN_TOOL_ACCURACY,
        "slot_f1_at_least_90_percent": (
            rates["slot_micro_f1"] >= MIN_SLOT_MICRO_F1
        ),
        "parse_rate_at_least_99_percent": rates["parse_rate"] >= MIN_PARSE_RATE,
    }
    return GroundQualification(
        rates=rates,
        gates=gates,
        minimum_ground_passed=all(gates.values()),
        target_95_exact_passed=rates["exact_match"] >= TARGET_EXACT_MATCH,
    )


def diagnose_landed_surface(
    *,
    full_registry_tool_accuracy: float,
    full_registry_exact_match: float,
    top5_gold_tool_coverage: float,
    matched_exact_match: float,
    postcontact_oracle_exact_match: float,
    highlighted_correct_row_conversion: float,
    highlighted_correct_row_retention: float,
    highlighted_default_substitutions: int,
) -> dict[str, bool]:
    """Classify already-published aggregate evidence without fitting a policy."""

    rates = (
        full_registry_tool_accuracy,
        full_registry_exact_match,
        top5_gold_tool_coverage,
        matched_exact_match,
        postcontact_oracle_exact_match,
        highlighted_correct_row_conversion,
        highlighted_correct_row_retention,
    )
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not 0.0 <= float(value) <= 1.0
        for value in rates
    ):
        raise ValueError("landed aggregate rates must lie in [0, 1]")
    if (
        isinstance(highlighted_default_substitutions, bool)
        or not isinstance(highlighted_default_substitutions, int)
        or highlighted_default_substitutions < 0
    ):
        raise ValueError("default substitutions must be a non-negative integer")

    diagnosis = {
        "full_registry_is_not_a_qualified_ground": (
            full_registry_tool_accuracy < MIN_TOOL_ACCURACY
            or full_registry_exact_match < MIN_EXACT_MATCH
        ),
        "top5_surface_cannot_reach_the_ground_floor": (
            top5_gold_tool_coverage < MIN_EXACT_MATCH
            or matched_exact_match < MIN_EXACT_MATCH
        ),
        "perfect_m0_matched_arbitration_cannot_reach_the_ground_floor": (
            postcontact_oracle_exact_match < MIN_EXACT_MATCH
        ),
        "correct_tool_row_does_not_supply_execution_knowledge": (
            highlighted_correct_row_conversion < MIN_EXACT_MATCH
            or highlighted_correct_row_retention < MIN_TOOL_ACCURACY
        ),
        "literal_defaults_are_a_copy_hazard": (
            highlighted_default_substitutions > 0
        ),
    }
    diagnosis["knowledge_expansion_required_before_candidate_optimization"] = all(
        diagnosis.values()
    )
    return diagnosis


__all__ = [
    "GroundMetrics",
    "GroundQualification",
    "MIN_EXACT_MATCH",
    "MIN_PARSE_RATE",
    "MIN_SLOT_MICRO_F1",
    "MIN_TOOL_ACCURACY",
    "TARGET_EXACT_MATCH",
    "diagnose_landed_surface",
    "qualify_ground",
]
