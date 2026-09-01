"""Complete-composite, exact-replay, and score-plan gates for the cascade."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping, Sequence

from ...core.tracing import TraceBuffer, TraceSink
from .a2t_self_transcript_cascade_flight import (
    MATCHED_CONTACT_ID,
    MATCHED_USE_PHASE,
    OBSERVATION_PHASE,
    SHUFFLED_USE_PHASE,
)

RESEND_SELECTION_PREFIX = "resend-self-transcript-v1\n"
COMPOSITE_TOOL_ID = "saea-a2t-self-transcript-composite-v1"
_PHASES = {
    "M0_DIRECT",
    OBSERVATION_PHASE,
    MATCHED_USE_PHASE,
    SHUFFLED_USE_PHASE,
}
_VARIANTS = {"matched", "shuffled-evidence", "resend", "policy"}


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
        if document.get("channel") != "MODEL_REQUEST":
            continue
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


def _trace_parts(
    documents: Sequence[Mapping[str, object]],
) -> tuple[
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
]:
    requests: dict[str, Mapping[str, object]] = {}
    responses: dict[str, Mapping[str, object]] = {}
    costs: dict[str, Mapping[str, object]] = {}
    targets = {
        "MODEL_REQUEST": ("/request", requests),
        "MODEL_RESPONSE": ("/response", responses),
        "COST": ("/cost", costs),
    }
    for number, document in enumerate(documents, start=1):
        if not isinstance(document, Mapping):
            raise SelfTranscriptBundleError(
                f"trace document {number} must be an object"
            )
        channel = document.get("channel")
        target = targets.get(channel) if isinstance(channel, str) else None
        if target is None:
            continue
        suffix, destination = target
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(record_id, str)
            or not record_id.endswith(suffix)
            or not isinstance(payload, Mapping)
        ):
            raise SelfTranscriptBundleError(
                f"trace document {number} has a malformed {channel} record"
            )
        request_id = record_id[: -len(suffix)]
        if not request_id or request_id in destination:
            raise SelfTranscriptBundleError(
                f"trace has a duplicate or blank {channel} request id"
            )
        destination[request_id] = payload
    return requests, responses, costs


def _cost_number(payload: Mapping[str, object], field: str) -> float:
    value = payload.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0.0
    ):
        raise SelfTranscriptBundleError(
            f"trace cost field {field!r} must be finite and non-negative"
        )
    return float(value)


def build_phase_bundle_material(
    summary: object,
    trace_documents: Sequence[Mapping[str, object]],
    *,
    phase: str,
    umbrella_lock_sha256: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    """Convert one sealed one-contact AgentLoop phase to bundle material."""

    if phase not in _PHASES:
        raise SelfTranscriptBundleError(f"unknown cascade phase {phase!r}")
    if (
        not isinstance(umbrella_lock_sha256, str)
        or len(umbrella_lock_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in umbrella_lock_sha256
        )
    ):
        raise SelfTranscriptBundleError(
            "umbrella lock identity must be lowercase 64-hex"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise SelfTranscriptBundleError(
            "AgentLoop summary must contain non-empty tuple results"
        )
    result_by_id: dict[str, object] = {}
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        response_text = getattr(result, "final_response_text", None)
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(response_text, str)
            or sample_id in result_by_id
        ):
            raise SelfTranscriptBundleError(
                "AgentLoop results contain malformed or duplicate samples"
            )
        result_by_id[sample_id] = result
    requests, responses, costs = _trace_parts(trace_documents)
    if set(requests) != set(responses) or set(requests) != set(costs):
        raise SelfTranscriptBundleError(
            "phase trace request, response, and cost identities differ"
        )
    request_by_sample: dict[str, str] = {}
    for request_id, outer in requests.items():
        payload = outer.get("payload")
        if not isinstance(payload, Mapping):
            raise SelfTranscriptBundleError(
                f"request {request_id!r} lacks its model payload"
            )
        sample_id = payload.get("sample_id")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or sample_id in request_by_sample
        ):
            raise SelfTranscriptBundleError(
                "phase trace has malformed or duplicate sample identities"
            )
        if outer.get("arm") != "speech-feature-query":
            raise SelfTranscriptBundleError(
                f"request {request_id!r} has the wrong arm"
            )
        request_by_sample[sample_id] = request_id
    if set(request_by_sample) != set(result_by_id):
        raise SelfTranscriptBundleError(
            "phase trace and AgentLoop result identities differ"
        )

    rows: list[dict[str, object]] = []
    for sample_id in sorted(result_by_id):
        result = result_by_id[sample_id]
        request_id = request_by_sample[sample_id]
        request = requests[request_id]
        response = responses[request_id]
        response_text = getattr(result, "final_response_text")
        response_text_sha256 = hashlib.sha256(
            response_text.encode("utf-8")
        ).hexdigest()
        if (
            response.get("text") != response_text
            or response.get("response_text_sha256") != response_text_sha256
        ):
            raise SelfTranscriptBundleError(
                f"response trace drift for {sample_id!r}"
            )
        request_sha256 = request.get("payload_sha256")
        response_sha256 = response.get("response_sha256")
        if any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in (request_sha256, response_sha256)
        ):
            raise SelfTranscriptBundleError(
                f"request or response hash is malformed for {sample_id!r}"
            )
        rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "audio2tool",
                "arm": "speech-feature-query",
                "text": response_text,
                "admitted": True,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "phase": phase,
            }
        )

    calls_used = 0
    audio_seconds = 0.0
    latency_seconds = 0.0
    prompt_tokens = 0
    completion_tokens = 0
    for request_id in sorted(costs):
        cost = costs[request_id]
        calls = _cost_number(cost, "calls")
        if calls != 1.0:
            raise SelfTranscriptBundleError(
                f"request {request_id!r} must account for exactly one call"
            )
        calls_used += 1
        audio_seconds += _cost_number(cost, "audio_seconds")
        latency_seconds += _cost_number(cost, "latency_seconds")
        for field in ("prompt_tokens", "completion_tokens"):
            value = _cost_number(cost, field)
            if not value.is_integer():
                raise SelfTranscriptBundleError(
                    f"trace cost field {field!r} must be integral"
                )
            if field == "prompt_tokens":
                prompt_tokens += int(value)
            else:
                completion_tokens += int(value)
    if calls_used != len(rows):
        raise SelfTranscriptBundleError(
            "phase cost row count differs from output row count"
        )
    return tuple(rows), {
        "calls_used": calls_used,
        "audio_seconds_used": audio_seconds,
        "latency_seconds_total": latency_seconds,
        "prompt_tokens_total": prompt_tokens,
        "completion_tokens_total": completion_tokens,
        "tool_calls": 0,
        "umbrella_lock_sha256": umbrella_lock_sha256,
    }


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


def build_use_composite_texts(
    *,
    m0_texts: Mapping[str, str],
    use_texts: Mapping[str, str],
    routed_ids: Sequence[str],
) -> dict[str, str]:
    routed = tuple(routed_ids)
    if len(set(routed)) != len(routed) or set(routed) != set(use_texts):
        raise SelfTranscriptBundleError(
            "routed identities and USE response identities must match uniquely"
        )
    if not set(routed) <= set(m0_texts):
        raise SelfTranscriptBundleError(
            "routed identities fall outside the frozen M0 cohort"
        )
    if any(not isinstance(text, str) for text in m0_texts.values()) or any(
        not isinstance(text, str) for text in use_texts.values()
    ):
        raise SelfTranscriptBundleError("composite responses must be strings")
    result = dict(m0_texts)
    result.update(use_texts)
    return assert_complete_composite(result, expected_ids=tuple(m0_texts))


def build_resend_composite_texts(
    matched_texts: Mapping[str, str],
    *,
    selected_ids: Sequence[str],
    resend_responses: Mapping[str, str],
) -> dict[str, str]:
    selected = tuple(selected_ids)
    if not selected or len(set(selected)) != len(selected):
        raise SelfTranscriptBundleError(
            "selected resend identities must be non-empty and unique"
        )
    if set(selected) != set(resend_responses):
        raise SelfTranscriptBundleError(
            "selected ids and resend response identities differ"
        )
    if not set(selected) <= set(matched_texts):
        raise SelfTranscriptBundleError(
            "resend identities fall outside the matched composite"
        )
    result = dict(matched_texts)
    result.update(resend_responses)
    return assert_complete_composite(result, expected_ids=tuple(matched_texts))


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


def emit_composite_rows(
    *,
    texts: Mapping[str, str],
    source_by_id: Mapping[str, Mapping[str, str]],
    sink: TraceSink | TraceBuffer,
    variant: str,
) -> tuple[dict[str, object], ...]:
    """Bind one complete model-free composition to deterministic TOOL records."""

    if variant not in _VARIANTS:
        raise SelfTranscriptBundleError(
            f"unknown composite variant {variant!r}"
        )
    if not texts or set(texts) != set(source_by_id):
        raise SelfTranscriptBundleError(
            "composite text and source identities must be equal and non-empty"
        )
    rows: list[dict[str, object]] = []
    for index, sample_id in enumerate(sorted(texts), start=1):
        text = texts[sample_id]
        source = source_by_id[sample_id]
        if not isinstance(text, str) or not isinstance(source, Mapping):
            raise SelfTranscriptBundleError("composite text or source is malformed")
        request_id = f"self-transcript-{variant}-composite-{index:04d}"
        request_document = {
            "tool_id": COMPOSITE_TOOL_ID,
            "variant": variant,
            "sample_id": sample_id,
            "source": dict(source),
        }
        request_sha256 = hashlib.sha256(
            canonical_payload_bytes(request_document)
        ).hexdigest()
        response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        response_document = {
            "tool_id": COMPOSITE_TOOL_ID,
            "variant": variant,
            "sample_id": sample_id,
            "source": dict(source),
            "text_sha256": response_text_sha256,
        }
        response_sha256 = hashlib.sha256(
            canonical_payload_bytes(response_document)
        ).hexdigest()
        sink.emit(
            "TOOL",
            f"{request_id}/request",
            {
                "tool_id": COMPOSITE_TOOL_ID,
                "variant": variant,
                "sample_id": sample_id,
                "source": dict(source),
                "payload_sha256": request_sha256,
            },
        )
        sink.emit(
            "TOOL",
            f"{request_id}/response",
            {
                "tool_id": COMPOSITE_TOOL_ID,
                "variant": variant,
                "sample_id": sample_id,
                "source": dict(source),
                "text": text,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
            },
        )
        rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "audio2tool",
                "arm": "speech-feature-query",
                "text": text,
                "admitted": True,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "composite_variant": variant,
                "composite_source": dict(source),
            }
        )
    return tuple(rows)


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
    if plan.get("mode") != "per-wave":
        raise SelfTranscriptBundleError("parallel score mode must be per-wave")
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
    if wave_1.get("mode") != "--finalize" or wave_2.get("mode") != "--score":
        raise SelfTranscriptBundleError(
            "wave 1 must finalize and model-free wave 2 must score"
        )
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
    "COMPOSITE_TOOL_ID",
    "RESEND_SELECTION_PREFIX",
    "SelfTranscriptBundleError",
    "assert_complete_composite",
    "build_phase_bundle_material",
    "build_policy_composite_texts",
    "build_resend_composite_texts",
    "build_use_composite_texts",
    "canonical_payload_bytes",
    "extract_exact_matched_payloads",
    "emit_composite_rows",
    "select_resend_ids",
    "validate_parallel_score_plan",
]
