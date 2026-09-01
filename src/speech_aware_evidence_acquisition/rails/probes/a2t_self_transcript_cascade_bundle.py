"""Complete-composite, exact-replay, and score-plan gates for the cascade."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from .a2t_self_transcript_cascade_flight import MATCHED_CONTACT_ID

RESEND_SELECTION_PREFIX = "resend-self-transcript-v1\n"


class SelfTranscriptBundleError(RuntimeError):
    """A replay, complete-composite, or whole-manifest invariant failed."""


def canonical_payload_bytes(payload: Mapping[str, object]) -> bytes:
    if not isinstance(payload, Mapping):
        raise SelfTranscriptBundleError("request payload must be a mapping")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def select_resend_ids(
    routed_sample_tiers: Mapping[str, str],
    *,
    per_tier: int = 2,
) -> tuple[str, ...]:
    """Select the frozen hash-ranked count from each routed tier."""

    if isinstance(per_tier, bool) or not isinstance(per_tier, int) or per_tier <= 0:
        raise SelfTranscriptBundleError("per_tier must be a positive integer")
    if not routed_sample_tiers:
        raise SelfTranscriptBundleError("resend selection requires routed samples")
    by_tier: dict[str, list[str]] = defaultdict(list)
    for sample_id, tier in routed_sample_tiers.items():
        if not sample_id or not tier:
            raise SelfTranscriptBundleError(
                "resend sample and tier identities must be non-empty"
            )
        by_tier[tier].append(sample_id)
    selected: list[str] = []
    for tier, sample_ids in sorted(by_tier.items()):
        if len(sample_ids) < per_tier:
            raise SelfTranscriptBundleError(
                f"tier {tier!r} has fewer than {per_tier} routed samples"
            )
        ranked = sorted(
            sample_ids,
            key=lambda sample_id: (
                hashlib.sha256(
                    f"{RESEND_SELECTION_PREFIX}{sample_id}".encode("utf-8")
                ).hexdigest(),
                sample_id,
            ),
        )
        selected.extend(ranked[:per_tier])
    return tuple(sorted(selected))


def _request_parts(
    document: Mapping[str, object], *, number: int
) -> tuple[str, Mapping[str, object], str]:
    if document.get("channel") != "MODEL_REQUEST":
        raise SelfTranscriptBundleError(
            f"trace document {number} is not a MODEL_REQUEST"
        )
    envelope = document.get("payload")
    if not isinstance(envelope, Mapping):
        raise SelfTranscriptBundleError(
            f"trace document {number} lacks a request envelope"
        )
    payload = envelope.get("payload")
    recorded_hash = envelope.get("payload_sha256")
    if not isinstance(payload, Mapping) or not isinstance(recorded_hash, str):
        raise SelfTranscriptBundleError(
            f"trace document {number} has a malformed request payload"
        )
    actual_hash = hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()
    if actual_hash != recorded_hash:
        raise SelfTranscriptBundleError(
            f"trace document {number} request payload hash drifted"
        )
    sample_id = payload.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id:
        raise SelfTranscriptBundleError(
            f"trace document {number} request lacks sample_id"
        )
    history = payload.get("history")
    if not isinstance(history, list) or not any(
        isinstance(item, Mapping) and item.get("contact_id") == MATCHED_CONTACT_ID
        for item in history
    ):
        raise SelfTranscriptBundleError(
            f"trace document {number} is not a matched final request"
        )
    return sample_id, payload, actual_hash


def extract_exact_matched_payloads(
    trace_documents: Sequence[Mapping[str, object]],
    selected_ids: Sequence[str],
) -> dict[str, Mapping[str, object]]:
    """Extract exact matched requests without rebuilding an AgentLoop call."""

    selected = tuple(selected_ids)
    if not selected or len(set(selected)) != len(selected):
        raise SelfTranscriptBundleError(
            "selected resend identities must be non-empty and unique"
        )
    wanted = set(selected)
    found: dict[str, Mapping[str, object]] = {}
    for number, document in enumerate(trace_documents, start=1):
        sample_id, payload, _payload_hash = _request_parts(document, number=number)
        if sample_id not in wanted:
            continue
        if sample_id in found:
            raise SelfTranscriptBundleError(
                f"duplicate matched final request for {sample_id!r}"
            )
        found[sample_id] = payload
    if set(found) != wanted:
        raise SelfTranscriptBundleError(
            "matched replay identity mismatch: "
            f"missing={sorted(wanted - set(found))!r}, "
            f"extra={sorted(set(found) - wanted)!r}"
        )
    return {sample_id: found[sample_id] for sample_id in sorted(found)}


def assert_complete_composite(
    texts: Mapping[str, str],
    *,
    expected_ids: Sequence[str],
) -> dict[str, str]:
    expected = tuple(expected_ids)
    if not expected or len(set(expected)) != len(expected):
        raise SelfTranscriptBundleError(
            "expected composite identities must be non-empty and unique"
        )
    if any(not isinstance(text, str) for text in texts.values()):
        raise SelfTranscriptBundleError("composite responses must be strings")
    expected_set = set(expected)
    observed_set = set(texts)
    if observed_set != expected_set:
        raise SelfTranscriptBundleError(
            "complete composite identity mismatch: "
            f"missing={sorted(expected_set - observed_set)!r}, "
            f"extra={sorted(observed_set - expected_set)!r}"
        )
    return {sample_id: texts[sample_id] for sample_id in sorted(expected_set)}


def build_policy_composite_texts(
    *,
    m0_texts: Mapping[str, str],
    matched_texts: Mapping[str, str],
    actions: Mapping[str, str],
) -> dict[str, str]:
    rosters = (set(m0_texts), set(matched_texts), set(actions))
    if not rosters[0] or any(roster != rosters[0] for roster in rosters[1:]):
        raise SelfTranscriptBundleError(
            "M0, matched, and policy action identities must match exactly"
        )
    result: dict[str, str] = {}
    for sample_id in sorted(rosters[0]):
        action = actions[sample_id]
        if action == "STOP_M0":
            result[sample_id] = m0_texts[sample_id]
        elif action == "USE_MATCHED":
            result[sample_id] = matched_texts[sample_id]
        else:
            raise SelfTranscriptBundleError(
                f"unknown policy action {action!r} for {sample_id!r}"
            )
    return result


def validate_parallel_score_plan(path: Path) -> dict[str, object]:
    """Validate outer parallelism over complete manifests, never score shards."""

    try:
        plan = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SelfTranscriptBundleError(
            f"cannot read parallel score plan {path}: {error}"
        ) from error
    if not isinstance(plan, dict):
        raise SelfTranscriptBundleError("parallel score plan must be an object")
    if plan.get("schema") != "saea-parallel-score-plan-v1":
        raise SelfTranscriptBundleError("parallel score plan schema mismatch")
    if plan.get("entrypoint") != "scripts/evaluate_parallel.sh":
        raise SelfTranscriptBundleError("parallel score entrypoint drifted")
    if plan.get("mode") != "--finalize":
        raise SelfTranscriptBundleError("parallel score mode must be --finalize")
    official = plan.get("official_scorer")
    expected_official = {
        "modified": False,
        "processes_per_job": 1,
        "invocations_per_complete_manifest": 1,
    }
    if official != expected_official:
        raise SelfTranscriptBundleError(
            "official scorer must remain unchanged and single-process per job"
        )
    wave_1 = plan.get("wave_1")
    wave_2 = plan.get("wave_2")
    if not isinstance(wave_1, Mapping) or not isinstance(wave_2, Mapping):
        raise SelfTranscriptBundleError("parallel score plan requires two waves")
    jobs_1 = wave_1.get("jobs")
    jobs_2 = wave_2.get("jobs")
    if not isinstance(jobs_1, list) or len(jobs_1) != 3:
        raise SelfTranscriptBundleError("wave 1 requires exactly three jobs")
    if wave_1.get("workers") != 3:
        raise SelfTranscriptBundleError("wave 1 requires exactly three workers")
    if not isinstance(jobs_2, list) or len(jobs_2) != 1 or wave_2.get("workers") != 1:
        raise SelfTranscriptBundleError("wave 2 requires one complete policy job")
    all_jobs = jobs_1 + jobs_2
    identifiers: list[str] = []
    for job in all_jobs:
        if not isinstance(job, Mapping):
            raise SelfTranscriptBundleError("score job must be an object")
        job_id = job.get("job_id")
        job_input = job.get("input")
        if not isinstance(job_id, str) or not job_id:
            raise SelfTranscriptBundleError("score job lacks job_id")
        if not isinstance(job_input, str) or "complete 104-row" not in job_input:
            raise SelfTranscriptBundleError(
                "every score job input must be a complete 104-row manifest"
            )
        identifiers.append(job_id)
    duplicates = [
        job_id for job_id, count in Counter(identifiers).items() if count > 1
    ]
    if duplicates:
        raise SelfTranscriptBundleError(
            f"parallel score jobs duplicate identities: {duplicates}"
        )
    aggregation = plan.get("aggregation_rule")
    if not isinstance(aggregation, str) or "Never split one dataset" not in aggregation:
        raise SelfTranscriptBundleError(
            "parallel score plan must forbid dataset sharding"
        )
    return plan


__all__ = [
    "RESEND_SELECTION_PREFIX",
    "SelfTranscriptBundleError",
    "assert_complete_composite",
    "build_policy_composite_texts",
    "canonical_payload_bytes",
    "extract_exact_matched_payloads",
    "select_resend_ids",
    "validate_parallel_score_plan",
]
