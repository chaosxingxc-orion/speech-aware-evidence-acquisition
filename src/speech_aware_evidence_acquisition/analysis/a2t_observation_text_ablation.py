"""Construction-only Audio2Tool observation-information ablation.

The analysis compares label retrieval from the final user turn with retrieval
from the complete preceding dialogue plus final user turn for multiturn
construction units.  Caller-supplied construction and validation folds must be
query-block disjoint.  Complete-dialogue text is hashed but never emitted.

This is a perfect-text observation oracle for diagnosis.  It is not runtime
material, a model-consumption ceiling, or permission to expose reference
transcripts to the frozen core.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
from typing import Mapping, Sequence

from .a2t_label_candidate_reduction import analyze_label_candidate_reduction
from ..rails.knowledge_build_a2t import A2tKbRow


RESULT_SCHEMA = "saea-a2t-observation-text-factorial-v2"
MULTITURN_TIER = "tier7_multiturn"
_DELTA_METRICS = (
    "required_item_recall",
    "full_set_coverage",
    "precision",
    "mean_distractor_burden",
    "positive_score_required_item_recall",
    "positive_score_full_set_coverage",
    "mean_zero_score_fallback_count",
)


class ObservationTextAblationError(ValueError):
    """The construction-only observation ablation boundary is malformed."""


@dataclass(frozen=True)
class ObservationTextAblationAudit:
    """A JSON-compatible report and its canonical serialization."""

    report: Mapping[str, object]
    canonical_json: str


def _validate_rows(rows: Sequence[A2tKbRow], *, label: str) -> tuple[A2tKbRow, ...]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence) or not rows:
        raise ObservationTextAblationError(f"{label} must be non-empty")
    ordered = tuple(sorted(rows, key=lambda row: getattr(row, "unit_id", "")))
    if any(not isinstance(row, A2tKbRow) for row in ordered):
        raise ObservationTextAblationError(f"{label} must contain A2tKbRow values")
    unit_ids = [row.unit_id for row in ordered]
    if any(not unit_id for unit_id in unit_ids) or len(unit_ids) != len(set(unit_ids)):
        raise ObservationTextAblationError(f"{label} has duplicate or malformed units")
    return ordered


def _validate_dialogue_texts(
    *,
    construction: Sequence[A2tKbRow],
    validation: Sequence[A2tKbRow],
    values: Mapping[str, str],
) -> dict[str, str]:
    if not isinstance(values, Mapping):
        raise ObservationTextAblationError(
            "complete dialogue mapping must exactly cover multiturn units"
        )
    required = {
        row.unit_id
        for row in (*construction, *validation)
        if row.tier == MULTITURN_TIER
    }
    provided = set(values)
    if provided != required:
        missing = len(required - provided)
        extra = len(provided - required)
        raise ObservationTextAblationError(
            "complete dialogue mapping must exactly cover multiturn units "
            f"(missing={missing}, extra={extra})"
        )
    result: dict[str, str] = {}
    for unit_id in sorted(required):
        text = values[unit_id]
        if not isinstance(text, str) or not text.strip():
            raise ObservationTextAblationError(
                "complete dialogue values must be non-empty English text"
            )
        normalized = " ".join(text.split())
        if not normalized.isascii():
            raise ObservationTextAblationError(
                "complete dialogue values must be English ASCII before analysis"
            )
        result[unit_id] = normalized
    return result


def _replace_multiturn_text(
    rows: Sequence[A2tKbRow], values: Mapping[str, str]
) -> tuple[A2tKbRow, ...]:
    return tuple(
        replace(row, text=values[row.unit_id]) if row.tier == MULTITURN_TIER else row
        for row in rows
    )


def _metric_view(report: Mapping[str, object]) -> dict[str, object]:
    k_metrics = report["k_metrics"]
    per_tier = report["per_tier"]
    assert isinstance(k_metrics, Mapping)
    assert isinstance(per_tier, Mapping)
    tier_metrics = per_tier.get(MULTITURN_TIER, {})
    return {
        "overall": k_metrics,
        MULTITURN_TIER: tier_metrics,
        "last_required_label_rank": report["last_required_label_rank"],
    }


def _delta_by_k(
    before: Mapping[str, object], after: Mapping[str, object]
) -> dict[str, dict[str, float]]:
    if set(before) != set(after):
        raise ObservationTextAblationError("comparison k grids disagree")
    delta: dict[str, dict[str, float]] = {}
    for key in sorted(before, key=int):
        before_metrics = before[key]
        after_metrics = after[key]
        if not isinstance(before_metrics, Mapping) or not isinstance(
            after_metrics, Mapping
        ):
            raise ObservationTextAblationError("comparison metrics are malformed")
        delta[key] = {
            metric: float(after_metrics[metric]) - float(before_metrics[metric])
            for metric in _DELTA_METRICS
        }
    return delta


def _interaction_by_k(
    baseline: Mapping[str, object],
    key_only: Mapping[str, object],
    observation_only: Mapping[str, object],
    joint: Mapping[str, object],
) -> dict[str, dict[str, float]]:
    if not (set(baseline) == set(key_only) == set(observation_only) == set(joint)):
        raise ObservationTextAblationError("factorial k grids disagree")
    result: dict[str, dict[str, float]] = {}
    for key in sorted(baseline, key=int):
        cells = (baseline[key], key_only[key], observation_only[key], joint[key])
        if any(not isinstance(cell, Mapping) for cell in cells):
            raise ObservationTextAblationError("factorial metrics are malformed")
        base_metrics, key_metrics, obs_metrics, joint_metrics = cells
        result[key] = {
            metric: (
                float(joint_metrics[metric])
                - float(key_metrics[metric])
                - float(obs_metrics[metric])
                + float(base_metrics[metric])
            )
            for metric in _DELTA_METRICS
        }
    return result


def _contrast_view(
    before: Mapping[str, object], after: Mapping[str, object]
) -> dict[str, object]:
    before_overall = before["overall"]
    after_overall = after["overall"]
    before_tier = before[MULTITURN_TIER]
    after_tier = after[MULTITURN_TIER]
    assert isinstance(before_overall, Mapping)
    assert isinstance(after_overall, Mapping)
    assert isinstance(before_tier, Mapping)
    assert isinstance(after_tier, Mapping)
    return {
        "overall": _delta_by_k(before_overall, after_overall),
        MULTITURN_TIER: _delta_by_k(before_tier, after_tier),
    }


def _text_identity(values: Mapping[str, str]) -> dict[str, object]:
    payload = json.dumps(
        [[unit_id, values[unit_id]] for unit_id in sorted(values)],
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    return {
        "unit_count": len(values),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "text_emitted": False,
    }


def analyze_observation_text_ablation(
    *,
    construction_rows: Sequence[A2tKbRow],
    validation_rows: Sequence[A2tKbRow],
    registry_tool_names: Sequence[str],
    complete_dialogue_text_by_unit_id: Mapping[str, str],
    k_grid: Sequence[int],
) -> ObservationTextAblationAudit:
    """Compare final-turn and complete-dialogue label retrieval."""

    construction = _validate_rows(construction_rows, label="construction_rows")
    validation = _validate_rows(validation_rows, label="validation_rows")
    if {row.query_idx for row in construction} & {row.query_idx for row in validation}:
        raise ObservationTextAblationError(
            "construction and validation must be query-block-disjoint"
        )
    dialogue_texts = _validate_dialogue_texts(
        construction=construction,
        validation=validation,
        values=complete_dialogue_text_by_unit_id,
    )

    complete_construction = _replace_multiturn_text(construction, dialogue_texts)
    complete_validation = _replace_multiturn_text(validation, dialogue_texts)
    baseline = analyze_label_candidate_reduction(
        construction_rows=construction,
        validation_rows=validation,
        registry_tool_names=registry_tool_names,
        k_grid=k_grid,
    ).report
    key_only = analyze_label_candidate_reduction(
        construction_rows=complete_construction,
        validation_rows=validation,
        registry_tool_names=registry_tool_names,
        k_grid=k_grid,
    ).report
    observation_only = analyze_label_candidate_reduction(
        construction_rows=construction,
        validation_rows=complete_validation,
        registry_tool_names=registry_tool_names,
        k_grid=k_grid,
    ).report
    joint = analyze_label_candidate_reduction(
        construction_rows=complete_construction,
        validation_rows=complete_validation,
        registry_tool_names=registry_tool_names,
        k_grid=k_grid,
    ).report
    cells = {
        "final_key_final_query": _metric_view(baseline),
        "complete_key_final_query": _metric_view(key_only),
        "final_key_complete_query": _metric_view(observation_only),
        "complete_key_complete_query": _metric_view(joint),
    }
    observation_contrast = _contrast_view(
        cells["final_key_final_query"], cells["final_key_complete_query"]
    )
    key_contrast = _contrast_view(
        cells["final_key_final_query"], cells["complete_key_final_query"]
    )
    joint_contrast = _contrast_view(
        cells["final_key_final_query"], cells["complete_key_complete_query"]
    )
    interaction: dict[str, object] = {}
    for scope in ("overall", MULTITURN_TIER):
        scoped = tuple(cells[name][scope] for name in cells)
        assert all(isinstance(value, Mapping) for value in scoped)
        interaction[scope] = _interaction_by_k(*scoped)
    tier_observation = observation_contrast[MULTITURN_TIER]
    tier_key = key_contrast[MULTITURN_TIER]
    assert isinstance(tier_observation, Mapping)
    assert isinstance(tier_key, Mapping)
    observation_information = any(
        metrics["full_set_coverage"] > 0.0 or metrics["required_item_recall"] > 0.0
        for metrics in tier_observation.values()
    )
    key_information = any(
        metrics["full_set_coverage"] > 0.0 or metrics["required_item_recall"] > 0.0
        for metrics in tier_key.values()
    )

    report: dict[str, object] = {
        "schema": RESULT_SCHEMA,
        "input_boundary": {
            "construction_rows_only": True,
            "evaluation_or_test_rows_consumed": 0,
            "complete_dialogue_text_emitted": False,
            "gold_used_only_for_postranking_measurement": True,
            "model_contacts": 0,
            "network_contacts": 0,
            "runtime_eligible": False,
            "scorer_contacts": 0,
        },
        "population": {
            "construction_units": len(construction),
            "validation_units": len(validation),
            "tier7_construction_units": sum(
                row.tier == MULTITURN_TIER for row in construction
            ),
            "tier7_validation_units": sum(
                row.tier == MULTITURN_TIER for row in validation
            ),
        },
        "complete_dialogue_text_identity": _text_identity(dialogue_texts),
        "cells": cells,
        "contrasts": {
            "observation_only_minus_baseline": observation_contrast,
            "construction_key_only_minus_baseline": key_contrast,
            "joint_minus_baseline": joint_contrast,
            "factorial_interaction": interaction,
        },
        "decision": {
            "observation_information_gain_detected": observation_information,
            "construction_key_information_gain_detected": key_information,
            "runtime_repair_if_observation_positive": (
                "OBSERVE_AND_ORGANIZE_PRIOR_DIALOGUE"
            ),
            "construction_repair_if_key_positive": (
                "INDEX_COMPLETE_DIALOGUE_RELATIONS_WITHOUT_CONCRETE_VALUES"
            ),
            "knowledge_value_expansion_inferred": False,
            "interpretation": (
                "The two simple contrasts separate query observation from key-index "
                "construction; the interaction reports any gain that requires both. "
                "Runtime must recover history from speech and known agent turns, and "
                "construction reference text must never enter runtime."
            ),
        },
    }
    canonical_json = json.dumps(
        report,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return ObservationTextAblationAudit(
        report=report,
        canonical_json=canonical_json,
    )


__all__ = [
    "MULTITURN_TIER",
    "ObservationTextAblationAudit",
    "ObservationTextAblationError",
    "RESULT_SCHEMA",
    "analyze_observation_text_ablation",
]
