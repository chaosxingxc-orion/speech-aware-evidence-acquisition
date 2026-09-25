"""Validated, pure feedback primitives for SLURP construction rollouts.

These helpers read official per-sample counts. They do not score audio, read gold,
contact a model, or alter a sealed artifact. The frozen baseline is supplied by
the caller before any variant contrast is inspected.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence


class FeedbackError(ValueError):
    """An official-score binding or rollout group is incomplete or invalid."""


_COUNT_FIELDS = (
    "slu_f1_word_tp", "slu_f1_word_fp", "slu_f1_word_fn",
    "slu_f1_char_tp", "slu_f1_char_fp", "slu_f1_char_fn",
)


def _nonnegative(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FeedbackError(f"{name} must be a finite nonnegative number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise FeedbackError(f"{name} must be a finite nonnegative number")
    return number


def _baseline(value: object) -> float:
    number = _nonnegative(value, "frozen baseline F0")
    if number > 1:
        raise FeedbackError("frozen baseline F0 must be in [0, 1]")
    return number


def _identity(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise FeedbackError(f"{name} must be nonempty text")
    return value


@dataclass(frozen=True)
class OfficialFeedback:
    """Official word-plus-character SLU counts and joint intent correctness."""

    sample_id: str
    tp: float
    fp: float
    fn: float
    intent_exact: float

    @property
    def denominator(self) -> float:
        return 2 * self.tp + self.fp + self.fn


def extract_official_feedback(row: Mapping[str, object]) -> OfficialFeedback:
    """Extract combined counts from one official per-sample score row."""
    if not isinstance(row, Mapping):
        raise FeedbackError("official score row must be a mapping")
    sid = _identity(row.get("sample_id"), "sample_id")
    values = {}
    for field in _COUNT_FIELDS:
        if field not in row:
            raise FeedbackError(f"official score row is missing {field}")
        values[field] = _nonnegative(row[field], field)
    if "scenario_action_exact" not in row:
        raise FeedbackError("official score row is missing scenario_action_exact")
    intent = _nonnegative(row["scenario_action_exact"], "scenario_action_exact")
    if intent not in (0.0, 1.0):
        raise FeedbackError("scenario_action_exact must be 0 or 1")
    return OfficialFeedback(
        sid,
        values["slu_f1_word_tp"] + values["slu_f1_char_tp"],
        values["slu_f1_word_fp"] + values["slu_f1_char_fp"],
        values["slu_f1_word_fn"] + values["slu_f1_char_fn"],
        intent,
    )


def pooled_f1(rows: Sequence[OfficialFeedback]) -> float:
    """Official micro F1 over combined word and character counts."""
    tp = fp = fn = 0.0
    for item in rows:
        if not isinstance(item, OfficialFeedback):
            raise FeedbackError("pooled rows must contain OfficialFeedback")
        tp += item.tp
        fp += item.fp
        fn += item.fn
    denominator = 2 * tp + fp + fn
    return 0.0 if denominator == 0 else 2 * tp / denominator


def frozen_baseline_f1(rows: Sequence[OfficialFeedback]) -> float:
    """Compute F0 once from the sealed baseline roster."""
    if not rows:
        raise FeedbackError("frozen baseline roster must be nonempty")
    return pooled_f1(rows)


def utility(row: OfficialFeedback, frozen_baseline: float) -> float:
    """Additive official-metric reward: 2TP - F0(2TP + FP + FN).

    Summed over an aligned roster, the sign equals that roster's pooled-F1
    change relative to the frozen F0 when the pooled denominator is positive.
    """
    if not isinstance(row, OfficialFeedback):
        raise FeedbackError("utility requires OfficialFeedback")
    f0 = _baseline(frozen_baseline)
    return 2 * row.tp - f0 * row.denominator


def align_feedback_groups(
    utterance_ids: Sequence[str],
    variants: Mapping[str, Sequence[Mapping[str, object]]],
) -> dict[str, dict[str, OfficialFeedback]]:
    """Join complete per-variant score rows by utterance identity.

    Every declared variant must contain each declared utterance exactly once.
    No extra, duplicate, partial, or unnamed group is accepted.
    """
    if not utterance_ids or isinstance(utterance_ids, (str, bytes)):
        raise FeedbackError("utterance_ids must be a nonempty sequence")
    ids = tuple(_identity(x, "utterance id") for x in utterance_ids)
    if len(set(ids)) != len(ids):
        raise FeedbackError("utterance_ids contain duplicates")
    if not isinstance(variants, Mapping) or not variants:
        raise FeedbackError("variants must be a nonempty mapping")
    groups: dict[str, dict[str, OfficialFeedback]] = {sid: {} for sid in ids}
    for variant, rows in variants.items():
        _identity(variant, "variant id")
        if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
            raise FeedbackError(f"variant {variant} rows must be a sequence")
        seen: dict[str, OfficialFeedback] = {}
        for raw in rows:
            item = extract_official_feedback(raw)
            if item.sample_id in seen:
                raise FeedbackError(f"variant {variant} repeats {item.sample_id}")
            seen[item.sample_id] = item
        if set(seen) != set(ids):
            raise FeedbackError(f"variant {variant} has missing or extra utterance identities")
        for sid in ids:
            groups[sid][variant] = seen[sid]
    return groups


def group_centered_advantages(
    groups: Mapping[str, Mapping[str, OfficialFeedback]], frozen_baseline: float
) -> dict[str, dict[str, float]]:
    """Subtract each utterance's variant-mean utility without mutating inputs."""
    _baseline(frozen_baseline)
    if not isinstance(groups, Mapping) or not groups:
        raise FeedbackError("groups must be nonempty")
    expected: set[str] | None = None
    output: dict[str, dict[str, float]] = {}
    for sid, variants in groups.items():
        _identity(sid, "utterance id")
        if not isinstance(variants, Mapping) or not variants:
            raise FeedbackError(f"utterance {sid} has no variants")
        names = set(variants)
        if expected is None:
            expected = names
        elif names != expected:
            raise FeedbackError("partial variant group")
        scores = {}
        for variant, item in variants.items():
            _identity(variant, "variant id")
            if not isinstance(item, OfficialFeedback) or item.sample_id != sid:
                raise FeedbackError(f"variant {variant} has wrong utterance binding")
            scores[variant] = utility(item, frozen_baseline)
        center = sum(scores.values()) / len(scores)
        output[sid] = {name: score - center for name, score in scores.items()}
    return output


def extract_parse_format_status(record: Mapping[str, object]) -> tuple[str, str]:
    """Read a sealed sample's parse status and optional format status."""
    if not isinstance(record, Mapping):
        raise FeedbackError("sample record must be a mapping")
    parse = _identity(record.get("parse_status"), "parse_status")
    format_value = record.get("format_status", "unreported")
    format_status = _identity(format_value, "format_status")
    return parse, format_status


def canonical_answer(answer: Mapping[str, object]) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    """Canonical structured answer for gold-free disagreement detection."""
    if not isinstance(answer, Mapping):
        raise FeedbackError("answer must be a mapping")
    scenario = answer.get("scenario")
    action = answer.get("action")
    if not isinstance(scenario, str) or not isinstance(action, str):
        raise FeedbackError("answer requires scenario and action text")
    entities = answer.get("entities")
    if not isinstance(entities, (list, tuple)):
        raise FeedbackError("answer is missing an entities list")
    canonical = []
    for entity in entities:
        if not isinstance(entity, Mapping):
            raise FeedbackError("entity must be a mapping")
        slot_type = _identity(entity.get("type"), "entity type")
        filler = entity.get("filler")
        if not isinstance(filler, str):
            raise FeedbackError("entity filler must be text")
        canonical.append((slot_type, filler))
    return scenario, action, tuple(sorted(canonical))


def answers_disagree(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    """Compare only two model-produced structured answers, never gold."""
    return canonical_answer(left) != canonical_answer(right)
