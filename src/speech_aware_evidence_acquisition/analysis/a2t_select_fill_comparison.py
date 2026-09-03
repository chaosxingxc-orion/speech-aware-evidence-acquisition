"""Model-free post-seal analysis for the fresh Audio2Tool SELECT/FILL flight.

The module consumes already-scored per-row outcomes and already-sealed
diagnostics.  It performs no file I/O and imports no model, scorer, transport,
or network client.  Gold-derived reachability and correctness fields are
refused unless the caller explicitly declares that the flight is post-seal.
"""

from __future__ import annotations

import random
import statistics
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from math import comb, isfinite
from typing import Callable, Mapping, Sequence


DIRECT_M0 = "DIRECT_M0"
JOINT_ONE_CALL = "JOINT_ONE_CALL"
JOINT_DRAFT_REVISE = "JOINT_DRAFT_REVISE"
SELECT_THEN_FILL = "SELECT_THEN_FILL"
ARM_ORDER = (
    DIRECT_M0,
    JOINT_ONE_CALL,
    JOINT_DRAFT_REVISE,
    SELECT_THEN_FILL,
)
ATTRIBUTION_ORDER = ("SUPPLY", "SELECT", "FILL", "SUCCESS")
ROW_COUNT = 104
TIERS = 8
ROWS_PER_TIER = 13
BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260903
CI_LEVEL = 0.90
RESULT_SCHEMA = "saea-a2t-select-fill-comparison-v1"


class AnalysisError(ValueError):
    """A scored outcome or sealed diagnostic violates the analysis contract."""


def distinct_name_set_equal(
    expected_names: Sequence[str], predicted_names: Sequence[str]
) -> bool:
    """Compare only the distinct tool names, intentionally ignoring repeats."""

    return set(expected_names) == set(predicted_names)


def name_multiplicity_equal(
    expected_names: Sequence[str], predicted_names: Sequence[str]
) -> bool:
    """Compare the complete tool-name multiset, including duplicate counts."""

    return Counter(expected_names) == Counter(predicted_names)


@dataclass(frozen=True)
class TierStratifiedBootstrapResult:
    """Deterministic percentile-bootstrap result with its tier contract."""

    point_estimate: float
    sigma_hat: float
    ci_low: float
    ci_high: float
    ci_level: float
    n_replicates: int
    seed: int
    strata: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "point_estimate": self.point_estimate,
            "sigma_hat": self.sigma_hat,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "ci_level": self.ci_level,
            "n_replicates": self.n_replicates,
            "seed": self.seed,
            "stratification": "tier",
            "strata": list(self.strata),
        }


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AnalysisError(f"{label} must be non-empty text")
    return value


def _boolean(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise AnalysisError(f"{label} must be boolean")
    return value


def _unit(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} must be a finite score")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise AnalysisError(f"{label} must be within [0, 1]")
    return result


def _nonnegative_number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} must be a nonnegative number")
    if not isfinite(float(value)) or value < 0:
        raise AnalysisError(f"{label} must be a nonnegative number")
    return value


def _row_identity(row: Mapping[str, object], label: str) -> tuple[str, str]:
    sample_id = _text(row.get("sample_id"), f"{label}.sample_id")
    tier = _text(row.get("tier"), f"{label}.tier")
    if sample_id.rsplit(":", 1)[0] != tier:
        raise AnalysisError(f"{label} tier must match its sample identity")
    return sample_id, tier


def _index_rows(
    rows: Sequence[Mapping[str, object]], label: str
) -> dict[str, Mapping[str, object]]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise AnalysisError(f"{label} must be a non-empty row sequence")
    indexed: dict[str, Mapping[str, object]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise AnalysisError(f"{label}[{index}] must be an object")
        sample_id, _tier = _row_identity(row, f"{label}[{index}]")
        if sample_id in indexed:
            raise AnalysisError(f"{label} contains duplicate identity {sample_id!r}")
        indexed[sample_id] = row
    return indexed


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def tier_stratified_paired_bootstrap(
    *,
    sample_ids: Sequence[str],
    tiers_by_id: Mapping[str, str],
    statistic: Callable[[Sequence[str]], float],
    n_replicates: int = BOOTSTRAP_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = CI_LEVEL,
) -> TierStratifiedBootstrapResult:
    """Resample paired identities with replacement independently within tiers."""

    if isinstance(sample_ids, (str, bytes)) or not sample_ids:
        raise AnalysisError("tier-stratified bootstrap requires sample identities")
    if type(n_replicates) is not int or n_replicates <= 0:
        raise AnalysisError("bootstrap replicates must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise AnalysisError("bootstrap seed must be an integer")
    if not 0.0 < ci_level < 1.0:
        raise AnalysisError("bootstrap CI level must be strictly within (0, 1)")
    ids = tuple(sorted(sample_ids))
    if len(set(ids)) != len(ids):
        raise AnalysisError("bootstrap sample identities must be unique")
    if set(tiers_by_id) != set(ids):
        raise AnalysisError("bootstrap tiers must cover the exact sample identities")
    by_tier: dict[str, tuple[str, ...]] = {}
    for tier in sorted(set(tiers_by_id.values())):
        members = tuple(item for item in ids if tiers_by_id[item] == tier)
        if not members:
            raise AnalysisError("bootstrap strata must not be empty")
        by_tier[tier] = members

    point_estimate = float(statistic(ids))
    rng = random.Random(seed)
    replicates: list[float] = []
    for _ in range(n_replicates):
        resampled: list[str] = []
        for members in by_tier.values():
            resampled.extend(members[rng.randrange(len(members))] for _ in members)
        replicates.append(float(statistic(tuple(resampled))))
    tail = (1.0 - ci_level) / 2.0
    return TierStratifiedBootstrapResult(
        point_estimate=point_estimate,
        sigma_hat=statistics.pstdev(replicates) if len(replicates) > 1 else 0.0,
        ci_low=_percentile(replicates, tail),
        ci_high=_percentile(replicates, 1.0 - tail),
        ci_level=ci_level,
        n_replicates=n_replicates,
        seed=seed,
        strata=tuple(by_tier),
    )


def _validate_outcomes(
    outcomes_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
) -> tuple[
    dict[str, dict[str, Mapping[str, object]]], tuple[str, ...], dict[str, str]
]:
    if not isinstance(outcomes_by_arm, Mapping) or set(outcomes_by_arm) != set(
        ARM_ORDER
    ):
        raise AnalysisError("outcomes_by_arm must cover exactly the four arms")
    indexed: dict[str, dict[str, Mapping[str, object]]] = {}
    for arm in ARM_ORDER:
        raw = _index_rows(outcomes_by_arm[arm], f"outcomes_by_arm.{arm}")
        normalized: dict[str, Mapping[str, object]] = {}
        for sample_id, row in raw.items():
            exact = _unit(row.get("exact_match"), f"{arm}/{sample_id}.exact_match")
            tool = _unit(row.get("tool_accuracy"), f"{arm}/{sample_id}.tool_accuracy")
            slot = _unit(row.get("slot_f1"), f"{arm}/{sample_id}.slot_f1")
            parsed = _boolean(row.get("parsed"), f"{arm}/{sample_id}.parsed")
            if exact not in {0.0, 1.0}:
                raise AnalysisError(f"{arm}/{sample_id}.exact_match must be binary")
            if tool not in {0.0, 1.0}:
                raise AnalysisError(f"{arm}/{sample_id}.tool_accuracy must be binary")
            if exact > tool:
                raise AnalysisError(
                    f"{arm}/{sample_id} exact match cannot exceed tool accuracy"
                )
            if exact and not parsed:
                raise AnalysisError(f"{arm}/{sample_id} exact match must be parsed")
            normalized[sample_id] = {
                "sample_id": sample_id,
                "tier": str(row["tier"]),
                "exact_match": exact,
                "tool_accuracy": tool,
                "paired_item_slot_f1": slot,
                "parsed": parsed,
            }
        indexed[arm] = normalized
    sample_ids = tuple(sorted(indexed[DIRECT_M0]))
    if any(set(indexed[arm]) != set(sample_ids) for arm in ARM_ORDER):
        raise AnalysisError("all four arms must contain the same exact identities")
    tiers = {item: str(indexed[DIRECT_M0][item]["tier"]) for item in sample_ids}
    for arm in ARM_ORDER[1:]:
        if any(indexed[arm][item]["tier"] != tiers[item] for item in sample_ids):
            raise AnalysisError("tier identities must agree across all four arms")
    return indexed, sample_ids, tiers


def _validate_official_metrics(
    official_metrics_by_arm: Mapping[str, Mapping[str, object]],
    outcomes: Mapping[str, Mapping[str, Mapping[str, object]]],
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
) -> dict[str, dict[str, Mapping[str, int | float]]]:
    if not isinstance(official_metrics_by_arm, Mapping) or set(
        official_metrics_by_arm
    ) != set(ARM_ORDER):
        raise AnalysisError("official_metrics_by_arm must cover exactly the four arms")
    result: dict[str, dict[str, Mapping[str, int | float]]] = {}
    tier_names = set(tiers.values())
    for arm in ARM_ORDER:
        arm_value = official_metrics_by_arm[arm]
        if not isinstance(arm_value, Mapping) or set(arm_value) != {
            "overall",
            "per_tier",
        }:
            raise AnalysisError(
                f"official_metrics_by_arm.{arm} must contain overall and per_tier"
            )
        per_tier = arm_value["per_tier"]
        if not isinstance(per_tier, Mapping) or set(per_tier) != tier_names:
            raise AnalysisError(f"{arm} official per-tier identities are incomplete")
        normalized: dict[str, Mapping[str, int | float]] = {}
        groups = {"overall": tuple(sample_ids)}
        groups.update(
            {
                tier: tuple(item for item in sample_ids if tiers[item] == tier)
                for tier in sorted(tier_names)
            }
        )
        for group, ids in groups.items():
            raw = arm_value["overall"] if group == "overall" else per_tier[group]
            if not isinstance(raw, Mapping):
                raise AnalysisError(f"{arm}/{group} official metrics must be an object")
            samples = raw.get("samples")
            if type(samples) is not int or samples != len(ids):
                raise AnalysisError(f"{arm}/{group} official sample count disagrees")
            metrics = {
                name: _unit(raw.get(name), f"{arm}/{group}.{name}")
                for name in (
                    "exact_match",
                    "tool_accuracy",
                    "slot_precision",
                    "slot_recall",
                    "slot_f1",
                )
            }
            for metric in ("exact_match", "tool_accuracy"):
                item_mean = sum(float(outcomes[arm][item][metric]) for item in ids) / len(
                    ids
                )
                if abs(metrics[metric] - item_mean) > 1e-12:
                    raise AnalysisError(
                        f"{arm}/{group} official {metric} disagrees with per-sample rows"
                    )
            normalized[group] = {"samples": samples, **metrics}
        result[arm] = normalized
    return result


def _validate_population(sample_ids: Sequence[str], tiers: Mapping[str, str]) -> None:
    if len(sample_ids) != ROW_COUNT:
        raise AnalysisError("population mode requires exactly 104 identities")
    counts = Counter(tiers.values())
    if len(counts) != TIERS or set(counts.values()) != {ROWS_PER_TIER}:
        raise AnalysisError("population mode requires exactly 13 rows per tier across 8 tiers")


def _sealed_diagnostics(
    rows: Sequence[Mapping[str, object]],
    *,
    label: str,
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
) -> dict[str, Mapping[str, object]]:
    indexed = _index_rows(rows, label)
    if set(indexed) != set(sample_ids):
        raise AnalysisError(f"{label} identities must match the scored identities")
    for sample_id, row in indexed.items():
        if row["tier"] != tiers[sample_id]:
            raise AnalysisError(f"{label}/{sample_id} tier disagrees with scored tier")
        if row.get("sealed") is not True:
            raise AnalysisError(f"{label}/{sample_id} must be sealed")
    return indexed


def _validate_reachability(
    rows: Sequence[Mapping[str, object]],
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
) -> dict[str, bool]:
    indexed = _sealed_diagnostics(
        rows,
        label="candidate_reachability",
        sample_ids=sample_ids,
        tiers=tiers,
    )
    return {
        item: _boolean(
            indexed[item].get("required_tools_reachable"),
            f"candidate_reachability/{item}.required_tools_reachable",
        )
        for item in sample_ids
    }


def _validate_selector(
    rows: Sequence[Mapping[str, object]],
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
) -> dict[str, Mapping[str, object]]:
    indexed = _sealed_diagnostics(
        rows,
        label="selector_diagnostics",
        sample_ids=sample_ids,
        tiers=tiers,
    )
    result: dict[str, Mapping[str, object]] = {}
    for item in sample_ids:
        row = indexed[item]
        count = row.get("gold_call_count")
        if type(count) is not int or not 1 <= count <= 7:
            raise AnalysisError(
                f"selector_diagnostics/{item}.gold_call_count must be in [1, 7]"
            )
        result[item] = {
            "name": _boolean(
                row.get("distinct_name_set_correct"),
                f"selector_diagnostics/{item}.distinct_name_set_correct",
            ),
            "multiplicity": _boolean(
                row.get("multiplicity_correct"),
                f"selector_diagnostics/{item}.multiplicity_correct",
            ),
            "gold_call_count": count,
        }
    return result


def _validate_joint(
    rows: Sequence[Mapping[str, object]],
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
) -> dict[str, Mapping[str, bool]]:
    indexed = _sealed_diagnostics(
        rows,
        label="joint_diagnostics",
        sample_ids=sample_ids,
        tiers=tiers,
    )
    prefixes = ("one_call", "draft", "revised")
    result: dict[str, Mapping[str, bool]] = {}
    for item in sample_ids:
        result[item] = {
            f"{prefix}_{suffix}": _boolean(
                indexed[item].get(f"{prefix}_{suffix}"),
                f"joint_diagnostics/{item}.{prefix}_{suffix}",
            )
            for prefix in prefixes
            for suffix in ("distinct_name_set_correct", "multiplicity_correct")
        }
    return result


def _validate_efficiency(
    efficiency_by_arm: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    if not isinstance(efficiency_by_arm, Mapping) or set(efficiency_by_arm) != set(
        ARM_ORDER
    ):
        raise AnalysisError("efficiency_by_arm must cover exactly the four arms")
    for arm in ARM_ORDER:
        item = efficiency_by_arm[arm]
        if not isinstance(item, Mapping):
            raise AnalysisError(f"efficiency_by_arm.{arm} must be an object")
        for field in ("prompt_tokens", "contacts", "raw_total_latency_seconds"):
            if field not in item:
                raise AnalysisError(f"efficiency_by_arm.{arm} must contain {field}")
            _nonnegative_number(item[field], f"efficiency_by_arm.{arm}.{field}")
        if type(item["contacts"]) is not int:
            raise AnalysisError(f"efficiency_by_arm.{arm}.contacts must be an integer")
    return deepcopy(efficiency_by_arm)


def _metric_summary(
    rows: Mapping[str, Mapping[str, object]],
    ids: Sequence[str],
    official: Mapping[str, int | float],
) -> dict[str, int | float]:
    return {
        "samples": len(ids),
        "exact_match": official["exact_match"],
        "tool_accuracy": official["tool_accuracy"],
        "slot_precision": official["slot_precision"],
        "slot_recall": official["slot_recall"],
        "slot_f1": official["slot_f1"],
        "paired_item_slot_f1": sum(
            float(rows[item]["paired_item_slot_f1"]) for item in ids
        )
        / len(ids),
        "parse_rate": sum(bool(rows[item]["parsed"]) for item in ids) / len(ids),
    }


def _with_tiers(
    sample_ids: Sequence[str], tiers: Mapping[str, str], build: Callable[[tuple[str, ...]], object]
) -> dict[str, object]:
    return {
        tier: build(tuple(item for item in sample_ids if tiers[item] == tier))
        for tier in sorted(set(tiers.values()))
    }


def _correctness_summary(
    *,
    ids: Sequence[str],
    name: Mapping[str, bool],
    multiplicity: Mapping[str, bool],
) -> dict[str, int | float]:
    return {
        "samples": len(ids),
        "distinct_name_set_accuracy": sum(name[item] for item in ids) / len(ids),
        "multiplicity_accuracy": sum(multiplicity[item] for item in ids) / len(ids),
        "combined_accuracy": sum(
            name[item] and multiplicity[item] for item in ids
        )
        / len(ids),
    }


def _diagnostic_view(
    *,
    sample_ids: Sequence[str],
    tiers: Mapping[str, str],
    name: Mapping[str, bool],
    multiplicity: Mapping[str, bool],
) -> Mapping[str, object]:
    return {
        "overall": _correctness_summary(
            ids=sample_ids, name=name, multiplicity=multiplicity
        ),
        "per_tier": _with_tiers(
            sample_ids,
            tiers,
            lambda ids: _correctness_summary(
                ids=ids, name=name, multiplicity=multiplicity
            ),
        ),
    }


def _attribution_summary(categories: Sequence[str]) -> Mapping[str, object]:
    counts = {category: categories.count(category) for category in ATTRIBUTION_ORDER}
    return {
        "samples": len(categories),
        "counts": counts,
        "rates": {key: value / len(categories) for key, value in counts.items()},
    }


def _sign_test(saves: int, harms: int) -> Mapping[str, object]:
    non_ties = saves + harms
    tail = (
        sum(comb(non_ties, index) for index in range(min(saves, harms) + 1))
        / (2**non_ties)
        if non_ties
        else 1.0
    )
    return {
        "test": "exact-two-sided-paired-sign-test",
        "non_ties": non_ties,
        "p_value": min(1.0, 2.0 * tail),
    }


def _contrast(
    *,
    role: str,
    left: Mapping[str, Mapping[str, object]],
    right: Mapping[str, Mapping[str, object]],
    left_official: Mapping[str, int | float],
    right_official: Mapping[str, int | float],
    sample_ids: tuple[str, ...],
    tiers: Mapping[str, str],
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> Mapping[str, object]:
    saves = sum(
        float(left[item]["exact_match"]) > float(right[item]["exact_match"])
        for item in sample_ids
    )
    harms = sum(
        float(left[item]["exact_match"]) < float(right[item]["exact_match"])
        for item in sample_ids
    )
    ties = len(sample_ids) - saves - harms
    metrics: dict[str, Mapping[str, object]] = {}
    for metric in (
        "exact_match",
        "tool_accuracy",
        "paired_item_slot_f1",
        "parse_rate",
    ):

        def statistic(ids: Sequence[str], metric_name: str = metric) -> float:
            if metric_name == "parse_rate":
                return sum(
                    bool(left[item]["parsed"]) - bool(right[item]["parsed"])
                    for item in ids
                ) / len(ids)
            return sum(
                float(left[item][metric_name]) - float(right[item][metric_name])
                for item in ids
            ) / len(ids)

        bootstrap = tier_stratified_paired_bootstrap(
            sample_ids=sample_ids,
            tiers_by_id=tiers,
            statistic=statistic,
            n_replicates=bootstrap_replicates,
            seed=bootstrap_seed,
        )
        metrics[metric] = {
            "point_estimate": bootstrap.point_estimate,
            "paired_bootstrap": bootstrap.as_json(),
        }
    metrics["official_corpus_micro_slot_f1"] = {
        "point_estimate": float(left_official["slot_f1"])
        - float(right_official["slot_f1"]),
        "paired_bootstrap": None,
    }

    def tier_exact(ids: tuple[str, ...]) -> Mapping[str, int]:
        tier_saves = sum(
            float(left[item]["exact_match"]) > float(right[item]["exact_match"])
            for item in ids
        )
        tier_harms = sum(
            float(left[item]["exact_match"]) < float(right[item]["exact_match"])
            for item in ids
        )
        return {
            "samples": len(ids),
            "saves": tier_saves,
            "harms": tier_harms,
            "ties": len(ids) - tier_saves - tier_harms,
            "net_exact_loss": tier_harms - tier_saves,
        }

    return {
        "role": role,
        "direction": "SELECT_THEN_FILL minus comparator",
        "exact": {
            "saves": saves,
            "harms": harms,
            "ties": ties,
            "sign_test": _sign_test(saves, harms),
            "per_tier": _with_tiers(sample_ids, tiers, tier_exact),
        },
        "metrics": metrics,
    }


def analyze_select_fill_comparison(
    *,
    outcomes_by_arm: Mapping[str, Sequence[Mapping[str, object]]],
    official_metrics_by_arm: Mapping[str, Mapping[str, object]],
    candidate_reachability: Sequence[Mapping[str, object]],
    selector_diagnostics: Sequence[Mapping[str, object]],
    joint_diagnostics: Sequence[Mapping[str, object]],
    efficiency_by_arm: Mapping[str, Mapping[str, object]],
    post_seal: bool,
    population_mode: bool = False,
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> Mapping[str, object]:
    """Return the complete preregistered four-arm comparison report."""

    if post_seal is not True:
        raise AnalysisError("gold-derived analysis inputs are accepted only post-seal")
    if type(population_mode) is not bool:
        raise AnalysisError("population_mode must be boolean")
    if population_mode and (
        bootstrap_replicates != BOOTSTRAP_REPLICATES
        or bootstrap_seed != BOOTSTRAP_SEED
    ):
        raise AnalysisError(
            "population mode requires 10,000 replicates and seed 20260903"
        )
    outcomes, sample_ids, tiers = _validate_outcomes(outcomes_by_arm)
    if population_mode:
        _validate_population(sample_ids, tiers)
    official = _validate_official_metrics(
        official_metrics_by_arm, outcomes, sample_ids, tiers
    )
    reachable = _validate_reachability(candidate_reachability, sample_ids, tiers)
    selector = _validate_selector(selector_diagnostics, sample_ids, tiers)
    joint = _validate_joint(joint_diagnostics, sample_ids, tiers)
    efficiency = _validate_efficiency(efficiency_by_arm)

    selector_name = {item: bool(selector[item]["name"]) for item in sample_ids}
    selector_multiplicity = {
        item: bool(selector[item]["multiplicity"]) for item in sample_ids
    }
    joint_views: dict[str, Mapping[str, object]] = {}
    joint_correct: dict[str, dict[str, bool]] = {}
    for stage in ("one_call", "draft", "revised"):
        names = {
            item: bool(joint[item][f"{stage}_distinct_name_set_correct"])
            for item in sample_ids
        }
        multiplicities = {
            item: bool(joint[item][f"{stage}_multiplicity_correct"])
            for item in sample_ids
        }
        joint_correct[stage] = {
            item: names[item] and multiplicities[item] for item in sample_ids
        }
        joint_views[stage] = _diagnostic_view(
            sample_ids=sample_ids,
            tiers=tiers,
            name=names,
            multiplicity=multiplicities,
        )

    selected_correct = {
        DIRECT_M0: {
            item: float(outcomes[DIRECT_M0][item]["tool_accuracy"]) == 1.0
            for item in sample_ids
        },
        JOINT_ONE_CALL: joint_correct["one_call"],
        JOINT_DRAFT_REVISE: joint_correct["revised"],
        SELECT_THEN_FILL: {
            item: selector_multiplicity[item]
            for item in sample_ids
        },
    }
    for arm in (JOINT_ONE_CALL, JOINT_DRAFT_REVISE, SELECT_THEN_FILL):
        for item in sample_ids:
            official_tool_correct = bool(outcomes[arm][item]["tool_accuracy"])
            if selected_correct[arm][item] != official_tool_correct:
                raise AnalysisError(
                    f"{arm}/{item} sealed multiplicity diagnostic disagrees "
                    "with official tool accuracy"
                )
            if selected_correct[arm][item] and not reachable[item]:
                raise AnalysisError(
                    f"{arm}/{item} cannot select the required multiset when it is unreachable"
                )
    categories_by_arm: dict[str, dict[str, str]] = {}
    for arm in ARM_ORDER:
        categories: dict[str, str] = {}
        for item in sample_ids:
            exact = bool(outcomes[arm][item]["exact_match"])
            correct = selected_correct[arm][item]
            if arm != DIRECT_M0 and not reachable[item]:
                category = "SUPPLY"
            elif not correct:
                category = "SELECT"
            elif exact:
                category = "SUCCESS"
            else:
                category = "FILL"
            categories[item] = category
        categories_by_arm[arm] = categories

    attribution = {
        arm: {
            "by_sample": {
                item: categories_by_arm[arm][item] for item in sample_ids
            },
            "overall": _attribution_summary(
                [categories_by_arm[arm][item] for item in sample_ids]
            ),
            "per_tier": _with_tiers(
                sample_ids,
                tiers,
                lambda ids, arm_name=arm: _attribution_summary(
                    [categories_by_arm[arm_name][item] for item in ids]
                ),
            ),
        }
        for arm in ARM_ORDER
    }

    conditional_ids = tuple(
        item for item in sample_ids if selected_correct[SELECT_THEN_FILL][item]
    )

    def conditional_summary(ids: tuple[str, ...]) -> Mapping[str, int | float | None]:
        if not ids:
            return {
                "eligible_rows": 0,
                "exact_count": 0,
                "exact_accuracy": None,
                "paired_item_slot_f1": None,
                "parse_rate": None,
            }
        rows = outcomes[SELECT_THEN_FILL]
        return {
            "eligible_rows": len(ids),
            "exact_count": int(sum(float(rows[item]["exact_match"]) for item in ids)),
            "exact_accuracy": sum(float(rows[item]["exact_match"]) for item in ids)
            / len(ids),
            "paired_item_slot_f1": sum(
                float(rows[item]["paired_item_slot_f1"]) for item in ids
            )
            / len(ids),
            "parse_rate": sum(bool(rows[item]["parsed"]) for item in ids) / len(ids),
        }

    contrasts = {
        "split_vs_revise": _contrast(
            role="primary",
            left=outcomes[SELECT_THEN_FILL],
            right=outcomes[JOINT_DRAFT_REVISE],
            left_official=official[SELECT_THEN_FILL]["overall"],
            right_official=official[JOINT_DRAFT_REVISE]["overall"],
            sample_ids=sample_ids,
            tiers=tiers,
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        ),
        "split_vs_joint_one_call": _contrast(
            role="secondary",
            left=outcomes[SELECT_THEN_FILL],
            right=outcomes[JOINT_ONE_CALL],
            left_official=official[SELECT_THEN_FILL]["overall"],
            right_official=official[JOINT_ONE_CALL]["overall"],
            sample_ids=sample_ids,
            tiers=tiers,
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        ),
        "split_vs_direct_m0": _contrast(
            role="secondary",
            left=outcomes[SELECT_THEN_FILL],
            right=outcomes[DIRECT_M0],
            left_official=official[SELECT_THEN_FILL]["overall"],
            right_official=official[DIRECT_M0]["overall"],
            sample_ids=sample_ids,
            tiers=tiers,
            bootstrap_replicates=bootstrap_replicates,
            bootstrap_seed=bootstrap_seed,
        ),
    }
    both_joint = ("split_vs_revise", "split_vs_joint_one_call")
    gates = {
        "positive_lower_exact_ci_vs_both_joint_controls": all(
            float(contrasts[name]["metrics"]["exact_match"]["paired_bootstrap"]["ci_low"])
            > 0.0
            for name in both_joint
        ),
        "nonnegative_tool_effect_vs_both_joint_controls": all(
            float(contrasts[name]["metrics"]["tool_accuracy"]["point_estimate"])
            >= 0.0
            for name in both_joint
        ),
        "nonnegative_slot_effect_vs_both_joint_controls": all(
            float(
                contrasts[name]["metrics"]["official_corpus_micro_slot_f1"][
                    "point_estimate"
                ]
            )
            >= 0.0
            for name in both_joint
        ),
        "positive_exact_effect_vs_direct_m0": float(
            contrasts["split_vs_direct_m0"]["metrics"]["exact_match"][
                "point_estimate"
            ]
        )
        > 0.0,
        "no_tier_over_one_net_exact_loss": all(
            int(tier_result["net_exact_loss"]) <= 1
            for contrast in contrasts.values()
            for tier_result in contrast["exact"]["per_tier"].values()
        ),
    }

    multi_call_ids = tuple(
        item for item in sample_ids if int(selector[item]["gold_call_count"]) > 1
    )
    selector_view = dict(
        _diagnostic_view(
            sample_ids=sample_ids,
            tiers=tiers,
            name=selector_name,
            multiplicity=selector_multiplicity,
        )
    )
    selector_view["multi_call"] = _correctness_summary(
        ids=multi_call_ids,
        name=selector_name,
        multiplicity=selector_multiplicity,
    ) if multi_call_ids else {
        "samples": 0,
        "distinct_name_set_accuracy": None,
        "multiplicity_accuracy": None,
        "combined_accuracy": None,
    }

    return {
        "schema": RESULT_SCHEMA,
        "analysis_phase": "post-seal",
        "runtime_eligible": False,
        "population_mode": population_mode,
        "row_count": len(sample_ids),
        "bootstrap_contract": {
            "kind": "tier-stratified paired percentile bootstrap",
            "replicates": bootstrap_replicates,
            "seed": bootstrap_seed,
            "ci_level": CI_LEVEL,
        },
        "arms": {
            arm: {
                "overall": _metric_summary(
                    outcomes[arm], sample_ids, official[arm]["overall"]
                ),
                "per_tier": _with_tiers(
                    sample_ids,
                    tiers,
                    lambda ids, arm_name=arm: _metric_summary(
                        outcomes[arm_name], ids, official[arm_name][tiers[ids[0]]]
                    ),
                ),
            }
            for arm in ARM_ORDER
        },
        "candidate_reachability": {
            "overall": {
                "samples": len(sample_ids),
                "reachable_count": sum(reachable.values()),
                "reachable_rate": sum(reachable.values()) / len(sample_ids),
            },
            "per_tier": _with_tiers(
                sample_ids,
                tiers,
                lambda ids: {
                    "samples": len(ids),
                    "reachable_count": sum(reachable[item] for item in ids),
                    "reachable_rate": sum(reachable[item] for item in ids)
                    / len(ids),
                },
            ),
        },
        "attribution": attribution,
        "selector_diagnostics": selector_view,
        "joint_name_diagnostics": joint_views,
        "conditional_fill_diagnostic": {
            "diagnostic_only": True,
            "conditioning_event": (
                "sealed SELECT name multiplicity matches the expected calls"
            ),
            "causal_decision_criterion": "paired final exact outcome",
            "overall": conditional_summary(conditional_ids),
            "per_tier": _with_tiers(
                sample_ids,
                tiers,
                lambda ids: conditional_summary(
                    tuple(item for item in ids if item in conditional_ids)
                ),
            ),
        },
        "paired_contrasts": contrasts,
        "efficiency": efficiency,
        "promotion_decision": {
            "promote": all(gates.values()),
            "gates": gates,
            "scope": (
                "Discovery-stage architecture promotion only; no confirmatory, "
                "scale, training-free RL, or paper claim is authorized."
            ),
        },
    }


__all__ = [
    "ARM_ORDER",
    "ATTRIBUTION_ORDER",
    "BOOTSTRAP_REPLICATES",
    "BOOTSTRAP_SEED",
    "DIRECT_M0",
    "JOINT_DRAFT_REVISE",
    "JOINT_ONE_CALL",
    "SELECT_THEN_FILL",
    "AnalysisError",
    "TierStratifiedBootstrapResult",
    "analyze_select_fill_comparison",
    "distinct_name_set_equal",
    "name_multiplicity_equal",
    "tier_stratified_paired_bootstrap",
]
