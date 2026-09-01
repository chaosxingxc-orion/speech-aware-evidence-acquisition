"""Complete-surface and outer-parallel gates for the Audio2Tool cascade v2."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

from .a2t_self_transcript_cascade_bundle import (
    build_phase_bundle_material,
    build_policy_composite_texts,
    build_resend_composite_texts,
    build_use_composite_texts,
    canonical_payload_bytes,
    emit_composite_rows,
)
from .a2t_contract_preserving_cascade_flight import MATCHED_CONTACT_ID

RESEND_SELECTION_NAMESPACE = "a2t-contract-preserving-resend-v2"
EXPECTED_TIERS = 8
RESENDS_PER_TIER = 2


class ContractPreservingBundleError(RuntimeError):
    """A complete-surface, replay, or score-job invariant failed."""


def merge_canary_and_remaining(
    *,
    canary: Mapping[str, str],
    remaining: Mapping[str, str],
    expected_ids: Sequence[str],
) -> dict[str, str]:
    """Reuse canary responses exactly once in their full USE surface."""

    overlap = set(canary) & set(remaining)
    if overlap:
        raise ContractPreservingBundleError(
            f"canary and remaining responses overlap: {sorted(overlap)!r}"
        )
    expected = tuple(expected_ids)
    if not expected or len(set(expected)) != len(expected):
        raise ContractPreservingBundleError(
            "expected complete identities must be non-empty and unique"
        )
    merged = {**canary, **remaining}
    if set(merged) != set(expected):
        raise ContractPreservingBundleError(
            "canary and remaining responses do not form one complete surface"
        )
    if any(not isinstance(text, str) for text in merged.values()):
        raise ContractPreservingBundleError(
            "complete surface responses must be strings"
        )
    return {sample_id: merged[sample_id] for sample_id in sorted(expected)}


def _rank(sample_id: str) -> str:
    return hashlib.sha256(
        f"{RESEND_SELECTION_NAMESPACE}\0{sample_id}".encode("utf-8")
    ).hexdigest()


def select_resend_ids(sample_tiers: Mapping[str, str]) -> tuple[str, ...]:
    """Select exactly two stable, identity-only matched resends per tier."""

    if not isinstance(sample_tiers, Mapping) or not sample_tiers:
        raise ContractPreservingBundleError(
            "resend selection requires sample-to-tier identities"
        )
    by_tier: dict[str, list[str]] = {}
    for sample_id, tier in sample_tiers.items():
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(tier, str)
            or not tier
        ):
            raise ContractPreservingBundleError(
                "resend sample and tier identities must be non-empty text"
            )
        by_tier.setdefault(tier, []).append(sample_id)
    if len(by_tier) != EXPECTED_TIERS:
        raise ContractPreservingBundleError(
            "resend selection requires exactly eight tiers"
        )
    selected: list[str] = []
    for tier in sorted(by_tier):
        ranked = sorted(by_tier[tier], key=lambda value: (_rank(value), value))
        if len(ranked) < RESENDS_PER_TIER:
            raise ContractPreservingBundleError(
                f"tier {tier!r} has fewer than two resend candidates"
            )
        selected.extend(ranked[:RESENDS_PER_TIER])
    return tuple(selected)


def extract_exact_matched_payloads(
    trace_documents: Sequence[Mapping[str, object]],
    selected_ids: Sequence[str],
) -> dict[str, Mapping[str, object]]:
    """Extract byte-verified v2 matched requests from a mixed trace stream."""

    selected = tuple(selected_ids)
    if not selected or len(set(selected)) != len(selected):
        raise ContractPreservingBundleError(
            "selected resend identities must be non-empty and unique"
        )
    wanted = set(selected)
    found: dict[str, Mapping[str, object]] = {}
    for number, document in enumerate(trace_documents, start=1):
        if document.get("channel") != "MODEL_REQUEST":
            continue
        envelope = document.get("payload")
        if not isinstance(envelope, Mapping):
            raise ContractPreservingBundleError(
                f"trace document {number} lacks a request envelope"
            )
        payload = envelope.get("payload")
        recorded_hash = envelope.get("payload_sha256")
        if not isinstance(payload, Mapping) or not isinstance(recorded_hash, str):
            raise ContractPreservingBundleError(
                f"trace document {number} has a malformed request payload"
            )
        actual_hash = hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()
        if actual_hash != recorded_hash:
            raise ContractPreservingBundleError(
                f"trace document {number} request payload hash drifted"
            )
        request_id = payload.get("request_id")
        if (
            not isinstance(request_id, str)
            or not request_id
            or document.get("record_id") != f"{request_id}/request"
        ):
            raise ContractPreservingBundleError(
                f"trace document {number} request identity drifted"
            )
        history = payload.get("history")
        if not isinstance(history, list) or not any(
            isinstance(item, Mapping) and item.get("contact_id") == MATCHED_CONTACT_ID
            for item in history
        ):
            continue
        sample_id = payload.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ContractPreservingBundleError(
                f"trace document {number} matched request lacks sample_id"
            )
        if sample_id not in wanted:
            continue
        if sample_id in found:
            raise ContractPreservingBundleError(
                f"duplicate matched final request for {sample_id!r}"
            )
        found[sample_id] = payload
    if set(found) != wanted:
        raise ContractPreservingBundleError(
            "matched replay identity mismatch: "
            f"missing={sorted(wanted - set(found))!r}, "
            f"extra={sorted(set(found) - wanted)!r}"
        )
    return {sample_id: found[sample_id] for sample_id in sorted(found)}


def validate_parallel_score_plan(path: Path) -> dict[str, object]:
    """Require four full-manifest workers, then one default-score policy job."""

    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ContractPreservingBundleError(
            f"cannot read parallel score plan {path}: {error}"
        ) from error
    if not isinstance(plan, dict):
        raise ContractPreservingBundleError("parallel score plan must be an object")
    if plan.get("schema") != "saea-parallel-score-plan-v2":
        raise ContractPreservingBundleError("parallel score plan schema mismatch")
    if plan.get("entrypoint") != "scripts/evaluate_parallel.sh":
        raise ContractPreservingBundleError("parallel score entrypoint drifted")
    if plan.get("mode") != "per-wave":
        raise ContractPreservingBundleError("parallel score mode must be per-wave")
    if plan.get("official_scorer") != {
        "modified": False,
        "processes_per_job": 1,
        "invocations_per_complete_manifest": 1,
    }:
        raise ContractPreservingBundleError(
            "official scorer must remain unchanged and single-process per job"
        )
    if plan.get("dataset_sharding") is not False or plan.get(
        "shard_metric_averaging"
    ) is not False:
        raise ContractPreservingBundleError(
            "parallel score plan must reject sharding and shard averaging"
        )
    wave_1 = plan.get("wave_1")
    wave_2 = plan.get("wave_2")
    if not isinstance(wave_1, Mapping) or not isinstance(wave_2, Mapping):
        raise ContractPreservingBundleError("parallel score plan requires two waves")
    if wave_1.get("mode") not in {"--finalize", "--per-job-operation"}:
        raise ContractPreservingBundleError(
            "wave 1 must finalize live attempts or use frozen per-job operations"
        )
    if wave_2.get("mode") != "default-score":
        raise ContractPreservingBundleError(
            "wave 2 must use the launcher's default score mode"
        )
    jobs_1 = wave_1.get("jobs")
    jobs_2 = wave_2.get("jobs")
    if not isinstance(jobs_1, list) or len(jobs_1) != 4 or wave_1.get("workers") != 4:
        raise ContractPreservingBundleError(
            "wave 1 requires exactly four whole-manifest workers"
        )
    if wave_1.get("mode") == "--per-job-operation" and [
        job.get("operation") if isinstance(job, Mapping) else None for job in jobs_1
    ] != ["score", "score", "score", "finalize"]:
        raise ContractPreservingBundleError(
            "recovery wave operations must be three scores then one finalizer"
        )
    if not isinstance(jobs_2, list) or len(jobs_2) != 1 or wave_2.get("workers") != 1:
        raise ContractPreservingBundleError(
            "wave 2 requires one complete policy job"
        )
    identifiers: list[str] = []
    for job in jobs_1 + jobs_2:
        if not isinstance(job, Mapping):
            raise ContractPreservingBundleError("score job must be an object")
        job_id = job.get("job_id")
        job_input = job.get("input")
        if not isinstance(job_id, str) or not job_id:
            raise ContractPreservingBundleError("score job lacks job_id")
        if not isinstance(job_input, str) or "complete 104-row" not in job_input:
            raise ContractPreservingBundleError(
                "every score job input must be a complete 104-row manifest"
            )
        identifiers.append(job_id)
    duplicates = [
        job_id for job_id, count in Counter(identifiers).items() if count > 1
    ]
    if duplicates:
        raise ContractPreservingBundleError(
            f"parallel score jobs duplicate identities: {duplicates!r}"
        )
    aggregation = plan.get("aggregation_rule")
    if not isinstance(aggregation, str) or "Never split one dataset" not in aggregation:
        raise ContractPreservingBundleError(
            "parallel score plan must forbid dataset sharding"
        )
    return plan


__all__ = [
    "ContractPreservingBundleError",
    "RESEND_SELECTION_NAMESPACE",
    "build_phase_bundle_material",
    "build_policy_composite_texts",
    "build_resend_composite_texts",
    "build_use_composite_texts",
    "canonical_payload_bytes",
    "emit_composite_rows",
    "extract_exact_matched_payloads",
    "merge_canary_and_remaining",
    "select_resend_ids",
    "validate_parallel_score_plan",
]
