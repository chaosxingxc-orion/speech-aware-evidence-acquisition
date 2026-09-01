"""Gold-free composition and exact-resend gates for factor-top-1 flight.

The official scorer consumes one complete output manifest. The flight itself
has two answer authorities: the frozen M0 response for ``STOP_M0`` and the
second frozen-core contact for ``USE_FACTOR_TOP1``. This module composes those
authorities without reading gold and emits explicit deterministic-tool trace
records that bind every output row to that composition decision.

The resend control does not reconstruct an equivalent AgentLoop call. It
extracts the already traced final-contact payload and returns the exact mapping
that ``FrozenCoreAdapter.request`` serialized, including request id, slot id,
speech packet, state, supplied value, and decoding parameters.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Mapping, Sequence

from ...core.tracing import TraceBuffer, TraceSink
from .a2t_factor_top1_flight import FINAL_CONTACT_ID

COMPOSITE_TOOL_ID = "saea-a2t-factor-top1-composite-v1"
RESEND_SELECTION_PREFIX = "resend-v1\n"


class FactorTop1BundleError(RuntimeError):
    """A structural, replay, or complete-composite invariant failed."""


def canonical_payload_bytes(payload: Mapping[str, object]) -> bytes:
    """Match the frozen adapter's byte-level request canonicalization."""

    if not isinstance(payload, Mapping):
        raise FactorTop1BundleError("request payload must be a mapping")
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _summary_results(summary: object) -> tuple[object, ...]:
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise FactorTop1BundleError(
            "AgentLoop summary must carry non-empty tuple results"
        )
    sample_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise FactorTop1BundleError("AgentLoop result lacks sample_id")
        sample_ids.append(sample_id)
    if len(set(sample_ids)) != len(sample_ids):
        raise FactorTop1BundleError("AgentLoop summary duplicates sample ids")
    return results


def _available(result: object) -> bool:
    query_state = getattr(result, "final_query_state", None)
    value_ids = getattr(query_state, "retrieved_value_ids", None)
    if not isinstance(value_ids, tuple):
        raise FactorTop1BundleError(
            "AgentLoop result lacks a tuple final retrieved-value state"
        )
    if len(value_ids) > 1:
        raise FactorTop1BundleError(
            "factor-top-1 result acquired more than one registry value"
        )
    return len(value_ids) == 1


def select_resend_ids(
    summary: object,
    *,
    per_tier: int = 2,
) -> tuple[str, ...]:
    """Select hash-ranked available samples without reading final responses."""

    if isinstance(per_tier, bool) or not isinstance(per_tier, int) or per_tier <= 0:
        raise FactorTop1BundleError("per_tier must be a positive integer")
    by_tier: dict[str, list[str]] = defaultdict(list)
    for result in _summary_results(summary):
        sample_id = getattr(result, "sample_id")
        if _available(result):
            tier, separator, _suffix = sample_id.rpartition(":")
            if not separator or not tier:
                raise FactorTop1BundleError(
                    f"sample id {sample_id!r} lacks its tier prefix"
                )
            by_tier[tier].append(sample_id)
    tiers = {
        getattr(result, "sample_id").rpartition(":")[0]
        for result in _summary_results(summary)
    }
    if "" in tiers:
        raise FactorTop1BundleError("one or more sample ids lack a tier prefix")
    selected: list[str] = []
    for tier in sorted(tiers):
        eligible = by_tier.get(tier, [])
        if len(eligible) < per_tier:
            raise FactorTop1BundleError(
                f"tier {tier!r} has fewer than {per_tier} available resend samples"
            )
        ranked = sorted(
            eligible,
            key=lambda sample_id: hashlib.sha256(
                f"{RESEND_SELECTION_PREFIX}{sample_id}".encode("utf-8")
            ).hexdigest(),
        )
        selected.extend(ranked[:per_tier])
    return tuple(sorted(selected))


def _is_final_contact_payload(payload: Mapping[str, object]) -> bool:
    history = payload.get("history")
    if not isinstance(history, list) or not history:
        return False
    control = history[-1]
    return (
        isinstance(control, Mapping)
        and control.get("role") == "control"
        and control.get("contact_id") == FINAL_CONTACT_ID
    )


def extract_exact_final_payloads(
    trace_documents: Sequence[Mapping[str, object]],
    selected_ids: Sequence[str],
) -> dict[str, dict[str, object]]:
    """Return byte-verified final-contact payloads for the fixed resend ids."""

    selected = tuple(selected_ids)
    if not selected or len(set(selected)) != len(selected):
        raise FactorTop1BundleError(
            "selected resend identities must be non-empty and unique"
        )
    selected_set = set(selected)
    payloads: dict[str, dict[str, object]] = {}
    saw_selected_nonfinal: set[str] = set()
    for document in trace_documents:
        if document.get("channel") != "MODEL_REQUEST":
            continue
        outer = document.get("payload")
        if not isinstance(outer, Mapping):
            raise FactorTop1BundleError("MODEL_REQUEST trace lacks its outer payload")
        payload = outer.get("payload")
        if not isinstance(payload, Mapping):
            raise FactorTop1BundleError("MODEL_REQUEST trace lacks its request payload")
        sample_id = payload.get("sample_id")
        if sample_id not in selected_set:
            continue
        if not _is_final_contact_payload(payload):
            saw_selected_nonfinal.add(str(sample_id))
            continue
        if sample_id in payloads:
            raise FactorTop1BundleError(
                f"selected sample {sample_id!r} has duplicate final requests"
            )
        recorded_hash = outer.get("payload_sha256")
        actual_hash = hashlib.sha256(canonical_payload_bytes(payload)).hexdigest()
        if recorded_hash != actual_hash:
            raise FactorTop1BundleError(
                f"selected sample {sample_id!r} final request hash drifted"
            )
        payloads[str(sample_id)] = dict(payload)
    missing = selected_set - set(payloads)
    if missing:
        qualifier = " final request" if missing <= saw_selected_nonfinal else " request"
        raise FactorTop1BundleError(
            f"selected resend samples lack one exact{qualifier}: {sorted(missing)}"
        )
    return {sample_id: payloads[sample_id] for sample_id in sorted(payloads)}


def build_main_composite_texts(
    summary: object,
    m0_responses: Mapping[str, str],
) -> dict[str, str]:
    """Use the phase-3 response only when exactly one row was available."""

    results = _summary_results(summary)
    result_ids = {getattr(result, "sample_id") for result in results}
    if result_ids != set(m0_responses):
        raise FactorTop1BundleError("AgentLoop and frozen M0 identities differ")
    texts: dict[str, str] = {}
    for result in results:
        sample_id = getattr(result, "sample_id")
        response = getattr(result, "final_response_text", None)
        m0 = m0_responses[sample_id]
        if not isinstance(response, str) or not isinstance(m0, str):
            raise FactorTop1BundleError("main and M0 responses must be strings")
        texts[sample_id] = response if _available(result) else m0
    return {sample_id: texts[sample_id] for sample_id in sorted(texts)}


def build_resend_composite_texts(
    main_texts: Mapping[str, str],
    *,
    selected_ids: Sequence[str],
    resend_responses: Mapping[str, str],
) -> dict[str, str]:
    """Replace only the fixed resend rows in one complete main composite."""

    selected = tuple(selected_ids)
    if not selected or len(set(selected)) != len(selected):
        raise FactorTop1BundleError("selected resend identities must be unique")
    if set(selected) != set(resend_responses):
        raise FactorTop1BundleError("selected ids and resend response ids differ")
    if not set(selected) <= set(main_texts):
        raise FactorTop1BundleError("resend identities fall outside the main composite")
    if any(not isinstance(text, str) for text in main_texts.values()) or any(
        not isinstance(text, str) for text in resend_responses.values()
    ):
        raise FactorTop1BundleError("composite responses must be strings")
    result = dict(main_texts)
    result.update(resend_responses)
    return {sample_id: result[sample_id] for sample_id in sorted(result)}


def emit_composite_rows(
    *,
    texts: Mapping[str, str],
    source_by_id: Mapping[str, Mapping[str, str]],
    sink: TraceSink | TraceBuffer,
    variant: str,
) -> tuple[dict[str, object], ...]:
    """Bind a complete deterministic composition to auditable TOOL records."""

    if variant not in {"main", "resend"}:
        raise FactorTop1BundleError("composite variant must be main or resend")
    if not texts or set(texts) != set(source_by_id):
        raise FactorTop1BundleError(
            "composite text and source identities must be equal and non-empty"
        )
    rows: list[dict[str, object]] = []
    for index, sample_id in enumerate(sorted(texts), start=1):
        text = texts[sample_id]
        source = source_by_id[sample_id]
        if not isinstance(text, str) or not isinstance(source, Mapping):
            raise FactorTop1BundleError("composite text or source is malformed")
        request_id = f"factor-{variant}-composite-{index:04d}"
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


__all__ = [
    "COMPOSITE_TOOL_ID",
    "RESEND_SELECTION_PREFIX",
    "FactorTop1BundleError",
    "build_main_composite_texts",
    "build_resend_composite_texts",
    "canonical_payload_bytes",
    "emit_composite_rows",
    "extract_exact_final_payloads",
    "select_resend_ids",
]
