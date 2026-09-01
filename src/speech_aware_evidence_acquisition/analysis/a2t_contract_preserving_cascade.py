"""Label-free structural gates for the Audio2Tool cascade v2.

This module never accepts task labels, expected calls, scores, or model-answer
meaning.  It selects the eight early USE identities and checks only whether
their raw responses preserve the frozen registry call envelope.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

from . import training_free_a2t_self_transcript_cascade as selftx

EXPERIMENT_ID = "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2"
CANARY_SELECTION_NAMESPACE = "a2t-contract-preserving-use-canary-v2"
CANARY_ROWS_PER_ARM = 8
MIN_POOLED_VALID = 15
MIN_MATCHED_VALID = 7
MIN_SHUFFLED_VALID = 7
MAX_CALLS = 4
MIN_INFORMATION_GAIN = 3
MIN_POLICY_USES = 5
MAX_POLICY_USES = 52
MIN_POLICY_SAVES = 4
MAX_POLICY_HARMS = 1
MIN_POLICY_NET_GAIN = 3
MIN_POSITIVE_FOLDS = 2


class ContractPreservingCascadeError(RuntimeError):
    """A frozen identity-only or structural gate failed closed."""


@dataclass(frozen=True)
class EnvelopeCheck:
    valid: bool
    reason: str
    call_count: int

    def as_json(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "call_count": self.call_count,
        }


def _invalid(reason: str) -> EnvelopeCheck:
    return EnvelopeCheck(valid=False, reason=reason, call_count=0)


def validate_output_envelope(
    response_text: object,
    registry_names: object,
) -> EnvelopeCheck:
    """Accept only an exact, nonempty ``name``/``arguments`` JSON array."""

    if not isinstance(response_text, str) or not response_text.strip():
        return _invalid("response_not_nonempty_text")
    if not isinstance(registry_names, (set, frozenset)) or not registry_names:
        raise ContractPreservingCascadeError(
            "registry names must be a non-empty set"
        )
    if any(not isinstance(name, str) or not name for name in registry_names):
        raise ContractPreservingCascadeError(
            "registry names must contain non-empty strings only"
        )
    try:
        payload = json.loads(response_text.strip())
    except json.JSONDecodeError:
        return _invalid("response_not_exact_json")
    if not isinstance(payload, list):
        return _invalid("response_not_array")
    if not 1 <= len(payload) <= MAX_CALLS:
        return _invalid("call_count_out_of_range")
    for call in payload:
        if not isinstance(call, dict):
            return _invalid("call_not_object")
        if set(call) != {"name", "arguments"}:
            return _invalid("call_keys_not_exact")
        if call["name"] not in registry_names:
            return _invalid("call_name_not_in_registry")
        if not isinstance(call["arguments"], dict):
            return _invalid("call_arguments_not_object")
    return EnvelopeCheck(valid=True, reason="valid", call_count=len(payload))


def _rank(sample_id: str) -> str:
    return hashlib.sha256(
        f"{CANARY_SELECTION_NAMESPACE}\0{sample_id}".encode("utf-8")
    ).hexdigest()


def select_canary_ids(sample_tiers: Mapping[str, str]) -> tuple[str, ...]:
    """Select one stable identity per tier without task content or outcomes."""

    if not isinstance(sample_tiers, Mapping) or not sample_tiers:
        raise ContractPreservingCascadeError(
            "canary selection requires sample-to-tier identities"
        )
    by_tier: dict[str, list[str]] = {}
    for sample_id, tier in sample_tiers.items():
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(tier, str)
            or not tier
        ):
            raise ContractPreservingCascadeError(
                "canary sample and tier identities must be non-empty text"
            )
        by_tier.setdefault(tier, []).append(sample_id)
    if len(by_tier) != CANARY_ROWS_PER_ARM:
        raise ContractPreservingCascadeError(
            "canary selection requires exactly eight tiers"
        )
    return tuple(
        min(by_tier[tier], key=lambda sample_id: (_rank(sample_id), sample_id))
        for tier in sorted(by_tier)
    )


@dataclass(frozen=True)
class StructuralCanaryReport:
    passed: bool
    row_count: int
    matched_valid: int
    shuffled_valid: int
    pooled_valid: int
    tiers_with_valid: int
    gates: Mapping[str, bool]
    matched_checks: Mapping[str, EnvelopeCheck]
    shuffled_checks: Mapping[str, EnvelopeCheck]
    gold_read: bool = False

    def as_json(self) -> dict[str, object]:
        return {
            "schema": "saea-a2t-contract-envelope-canary-v2",
            "experiment_id": EXPERIMENT_ID,
            "passed": self.passed,
            "row_count": self.row_count,
            "matched_valid": self.matched_valid,
            "shuffled_valid": self.shuffled_valid,
            "pooled_valid": self.pooled_valid,
            "tiers_with_valid": self.tiers_with_valid,
            "gates": dict(self.gates),
            "matched_checks": {
                key: value.as_json() for key, value in self.matched_checks.items()
            },
            "shuffled_checks": {
                key: value.as_json() for key, value in self.shuffled_checks.items()
            },
            "gold_read": self.gold_read,
        }


def evaluate_structural_canary(
    *,
    matched: Mapping[str, str],
    shuffled: Mapping[str, str],
    sample_tiers: Mapping[str, str],
    registry_names: set[str] | frozenset[str],
) -> StructuralCanaryReport:
    """Apply the frozen 15/16, 7/8, 7/8, all-tier conjunction."""

    identities = set(matched)
    if (
        len(identities) != CANARY_ROWS_PER_ARM
        or set(shuffled) != identities
        or set(sample_tiers) != identities
    ):
        raise ContractPreservingCascadeError(
            "canary arms and tier map must share exactly eight identities"
        )
    tier_counts = Counter(sample_tiers.values())
    if len(tier_counts) != CANARY_ROWS_PER_ARM or set(tier_counts.values()) != {1}:
        raise ContractPreservingCascadeError(
            "canary identities must contain exactly one row per tier"
        )
    matched_checks = {
        sample_id: validate_output_envelope(matched[sample_id], registry_names)
        for sample_id in sorted(identities)
    }
    shuffled_checks = {
        sample_id: validate_output_envelope(shuffled[sample_id], registry_names)
        for sample_id in sorted(identities)
    }
    matched_valid = sum(check.valid for check in matched_checks.values())
    shuffled_valid = sum(check.valid for check in shuffled_checks.values())
    pooled_valid = matched_valid + shuffled_valid
    tiers_with_valid = sum(
        matched_checks[sample_id].valid or shuffled_checks[sample_id].valid
        for sample_id in identities
    )
    gates = {
        "pooled_valid": pooled_valid >= MIN_POOLED_VALID,
        "matched_valid": matched_valid >= MIN_MATCHED_VALID,
        "shuffled_valid": shuffled_valid >= MIN_SHUFFLED_VALID,
        "tier_coverage": tiers_with_valid == CANARY_ROWS_PER_ARM,
    }
    return StructuralCanaryReport(
        passed=all(gates.values()),
        row_count=2 * CANARY_ROWS_PER_ARM,
        matched_valid=matched_valid,
        shuffled_valid=shuffled_valid,
        pooled_valid=pooled_valid,
        tiers_with_valid=tiers_with_valid,
        gates=gates,
        matched_checks=matched_checks,
        shuffled_checks=shuffled_checks,
    )


def promotion_gates(
    base_report: object,
    *,
    liveness_passed: bool,
    canary_passed: bool,
    route_available_count: int,
    resend_absolute_exact_count_difference: int,
) -> dict[str, bool]:
    """Apply the prospectively frozen v2 promotion conjunction."""

    metrics = getattr(base_report, "metrics", None)
    prior_gates = getattr(base_report, "gates", None)
    if metrics is None or not isinstance(prior_gates, Mapping):
        raise ContractPreservingCascadeError(
            "promotion requires a complete cross-fitted base report"
        )
    for label, value in (
        ("route-available count", route_available_count),
        ("resend exact-count difference", resend_absolute_exact_count_difference),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ContractPreservingCascadeError(
                f"{label} must be a non-negative integer"
            )
    used = int(metrics.used)
    net_gain = int(metrics.net_gain)
    folds = tuple(metrics.fold_net_gains)
    return {
        "observation_liveness": liveness_passed,
        "structural_canary": canary_passed,
        "top5_information_gain": (
            int(metrics.top5_gold_tool_correct_count)
            >= int(metrics.m0_tool_correct_count) + MIN_INFORMATION_GAIN
        ),
        "matched_vs_m0_exact": (
            int(metrics.matched_m0_exact_gain) >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_m0_tool": (
            int(metrics.matched_m0_tool_gain) >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_shuffled_exact": (
            int(metrics.matched_shuffled_exact_gain) >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_shuffled_tool": (
            int(metrics.matched_shuffled_tool_gain) >= MIN_INFORMATION_GAIN
        ),
        "matched_vs_shuffled_positive_ci90_lower": (
            float(metrics.matched_shuffled_ci_low) > 0.0
        ),
        "both_actions": 0 < used < int(metrics.n_samples),
        "use_range": MIN_POLICY_USES <= used <= MAX_POLICY_USES,
        "policy_saved_minimum": int(metrics.saved) >= MIN_POLICY_SAVES,
        "policy_harm_maximum": int(metrics.harmed) <= MAX_POLICY_HARMS,
        "policy_net_gain": net_gain >= MIN_POLICY_NET_GAIN,
        "policy_gain_exceeds_resend_floor": (
            net_gain > resend_absolute_exact_count_difference
        ),
        "policy_positive_ci90_lower": float(metrics.policy_ci_low) > 0.0,
        "policy_tool_accuracy_nonnegative": (
            int(metrics.tool_accuracy_net_gain) >= 0
        ),
        "policy_slot_micro_f1_nonnegative": (
            float(metrics.slot_micro_f1_net_gain) >= 0.0
        ),
        "every_fold_nonnegative": all(int(value) >= 0 for value in folds),
        "positive_fold_count": (
            sum(int(value) > 0 for value in folds) >= MIN_POSITIVE_FOLDS
        ),
        "policy_gain_exceeds_always_use_by_two": (
            net_gain >= int(metrics.always_use_net_gain) + 2
        ),
        "policy_fewer_final_contacts": (
            int(metrics.final_contacts) < route_available_count
        ),
        "state_liveness": prior_gates.get("state_liveness") is True,
    }


def evaluate_policy(
    outcomes: Sequence[selftx.SelfTranscriptOutcome],
    *,
    liveness_passed: bool,
    canary_passed: bool,
    resend_absolute_exact_count_difference: int,
    seed: int = selftx.FOLD_SEED,
    n_folds: int = selftx.N_FOLDS,
    n_replicates: int = 10_000,
) -> selftx.PolicyReport:
    """Cross-fit the frozen v1 memory and replace only the v2 pass gates."""

    base = selftx.evaluate_policy(
        outcomes,
        liveness_passed=liveness_passed,
        resend_absolute_exact_count_difference=(
            resend_absolute_exact_count_difference
        ),
        seed=seed,
        n_folds=n_folds,
        n_replicates=n_replicates,
    )
    gates = promotion_gates(
        base,
        liveness_passed=liveness_passed,
        canary_passed=canary_passed,
        route_available_count=sum(item.route_available for item in outcomes),
        resend_absolute_exact_count_difference=(
            resend_absolute_exact_count_difference
        ),
    )
    return selftx.PolicyReport(
        state_class_counts=base.state_class_counts,
        metrics=base.metrics,
        gates=gates,
        promotion_passed=all(gates.values()),
        decisions=base.decisions,
    )


__all__ = [
    "CANARY_ROWS_PER_ARM",
    "CANARY_SELECTION_NAMESPACE",
    "ContractPreservingCascadeError",
    "EnvelopeCheck",
    "EXPERIMENT_ID",
    "StructuralCanaryReport",
    "evaluate_structural_canary",
    "evaluate_policy",
    "promotion_gates",
    "select_canary_ids",
    "validate_output_envelope",
]
