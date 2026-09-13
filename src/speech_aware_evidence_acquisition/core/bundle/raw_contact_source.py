"""Verification of an unsealed, aborted model-contact source.

This module is intentionally carrier agnostic. It verifies only pinned attempt,
generation-plan, and raw-trace provenance; label parsing, references, scoring,
and projection remain outside the bundle layer.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from ...contracts import ExecutionPlan, TraceRecord
from ...core.attempts import STATE_ABORTED
from ...data.splits import prefixed, split_identity_hash


class RawContactSourceError(ValueError):
    """An unsealed contact source failed closed."""


@dataclass(frozen=True)
class AbortedContactSourceVerification:
    """Read-only source provenance and one-to-one contact bindings."""

    attempt: Mapping[str, object]
    generation_plan: Mapping[str, object]
    trace_records: Mapping[str, Mapping[str, object]]
    contacts_by_sample_id: Mapping[str, Mapping[str, object]]


def _map(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RawContactSourceError(f"{label} must be a mapping")
    return value


def _pin(value: object, label: str) -> tuple[Path, str]:
    binding = _map(value, label)
    raw_path, expected = binding.get("path"), binding.get("sha256")
    if not isinstance(raw_path, str) or not raw_path:
        raise RawContactSourceError(f"{label}.path must be nonempty text")
    if not isinstance(expected, str) or len(expected) != 64:
        raise RawContactSourceError(f"{label}.sha256 must be a 64-character hash")
    path = Path(raw_path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RawContactSourceError(f"{label} cannot be read: {error}") from error
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise RawContactSourceError(
            f"{label} hash mismatch: configured {expected}, measured {actual}"
        )
    return path, expected


def _json(raw: bytes, label: str) -> Mapping[str, object]:
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_raw_json_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RawContactSourceError(f"{label} is not valid JSON: {error}") from error
    return _map(document, label)


def _raw_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise RawContactSourceError(f"raw trace has duplicate JSON key {key!r}")
        document[key] = value
    return document


def _transport_response_sha256(
    raw_wire: bytes,
    *,
    expected_text: str,
    expected_usage: object,
    expected_finish_reason: object,
) -> str:
    """Rebuild the adapter envelope hash from the immutable wire bytes."""
    try:
        parsed = json.loads(raw_wire.decode("utf-8"), object_pairs_hook=_raw_json_object)
        choice = parsed["choices"][0]
        message = choice["message"]
        response_tool_calls = message.get("tool_calls") if isinstance(message, Mapping) else None
        argument_errors: list[int] = []
        if isinstance(response_tool_calls, list) and response_tool_calls:
            canonical_calls = []
            for index, call in enumerate(response_tool_calls):
                function = call["function"]
                name = function["name"]
                raw_arguments = function.get("arguments")
                try:
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else None
                    if not isinstance(arguments, dict):
                        raise ValueError("tool call arguments must decode to an object")
                except (TypeError, ValueError):
                    arguments = {}
                    argument_errors.append(index)
                canonical_calls.append({"name": name, "arguments": arguments})
            text = json.dumps(canonical_calls)
        else:
            text = message["content"]
        usage = {
            str(key): int(value)
            for key, value in dict(parsed.get("usage", {})).items()
            if not isinstance(value, Mapping)
        }
        envelope: dict[str, object] = {"text": text, "usage": usage}
        envelope["wire_response_b64"] = base64.b64encode(raw_wire).decode("ascii")
        envelope["wire_response_sha256"] = hashlib.sha256(raw_wire).hexdigest()
        envelope["wire_finish_reason"] = choice.get("finish_reason")
        if isinstance(response_tool_calls, list) and response_tool_calls:
            envelope["tool_calls"] = response_tool_calls
            if argument_errors:
                envelope["tool_call_argument_parse_errors"] = argument_errors
        if isinstance(choice, Mapping) and "logprobs" in choice:
            envelope["logprobs"] = choice["logprobs"]
    except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as error:
        raise RawContactSourceError(
            f"wire response cannot reconstruct the transport envelope: {error}"
        ) from error
    if (
        text != expected_text
        or usage != expected_usage
        or envelope["wire_finish_reason"] != expected_finish_reason
    ):
        raise RawContactSourceError(
            "wire response disagrees with normalized response fields"
        )
    return hashlib.sha256(json.dumps(envelope).encode("utf-8")).hexdigest()


def _trace_records(
    trace_pin: object,
) -> tuple[dict[str, Mapping[str, object]], Path, str]:
    trace_path, trace_sha = _pin(trace_pin, "raw trace")
    try:
        raw = trace_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != trace_sha:
            raise RawContactSourceError("raw trace changed after its pinned verification")
        lines = raw.decode("utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise RawContactSourceError(f"raw trace cannot be read: {error}") from error
    records: dict[str, tuple[str, Mapping[str, object]]] = {}
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            document = json.loads(line, object_pairs_hook=_raw_json_object)
            record = TraceRecord(
                channel=document["channel"],
                record_id=document["record_id"],
                payload=document["payload"],
            ).validate()
        except (KeyError, TypeError, ValueError) as error:
            raise RawContactSourceError(
                f"invalid raw trace line {number}: {error}"
            ) from error
        if record.record_id in records:
            raise RawContactSourceError(
                f"raw trace duplicates record_id {record.record_id!r}"
            )
        records[record.record_id] = (record.channel, dict(record.payload))
    if not records:
        raise RawContactSourceError("raw trace is empty")
    return records, trace_path, trace_sha


def _request_id(record_id: object, suffix: str) -> str:
    if not isinstance(record_id, str) or not record_id.endswith(suffix):
        raise RawContactSourceError(
            f"raw trace record ID must end with {suffix!r}: {record_id!r}"
        )
    request_id = record_id[: -len(suffix)]
    if not request_id:
        raise RawContactSourceError("raw trace request ID is empty")
    return request_id


def _readonly_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


def _verify_trace(
    trace_pin: object,
    *,
    expected_sample_ids: tuple[str, ...],
    expected_audio_seconds: float,
) -> tuple[
    Mapping[str, Mapping[str, object]],
    Mapping[str, Mapping[str, object]],
]:
    if len(expected_sample_ids) != len(set(expected_sample_ids)):
        raise RawContactSourceError("expected_sample_ids contains duplicates")
    if any(not isinstance(sample_id, str) or not sample_id for sample_id in expected_sample_ids):
        raise RawContactSourceError("expected_sample_ids must be nonempty strings")
    records, _trace_path, _trace_sha = _trace_records(trace_pin)
    required = ("MODEL_REQUEST", "MODEL_RESPONSE", "MODEL_WIRE_RESPONSE", "COST")
    channels: dict[str, dict[str, Mapping[str, object]]] = {}
    for record_id, (channel, payload) in records.items():
        channels.setdefault(channel, {})[record_id] = payload
    missing = [channel for channel in required if channel not in channels]
    if missing:
        raise RawContactSourceError(f"raw trace lacks required channels: {missing}")
    indexed: dict[str, dict[str, Mapping[str, object]]] = {}
    suffixes = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "MODEL_WIRE_RESPONSE": "/wire-response",
        "COST": "/cost",
    }
    for channel in required:
        indexed[channel] = {}
        for record_id, payload in channels[channel].items():
            request_id = _request_id(record_id, suffixes[channel])
            if request_id in indexed[channel]:
                raise RawContactSourceError(
                    f"raw trace has duplicate {channel} request ID {request_id!r}"
                )
            indexed[channel][request_id] = payload
    request_ids = set(indexed["MODEL_REQUEST"])
    if any(set(indexed[channel]) != request_ids for channel in required[1:]):
        raise RawContactSourceError(
            "raw trace required channels do not have identical request IDs"
        )
    if len(request_ids) != len(expected_sample_ids):
        raise RawContactSourceError("raw request count does not match the pinned roster")
    contacts: dict[str, Mapping[str, object]] = {}
    audio_seconds = 0.0
    for request_id, request in indexed["MODEL_REQUEST"].items():
        inner = request.get("payload")
        if (
            not isinstance(inner, Mapping)
            or inner.get("request_id") != request_id
            or not isinstance(inner.get("sample_id"), str)
            or not inner["sample_id"]
        ):
            raise RawContactSourceError(f"raw request {request_id!r} identity is invalid")
        request_payload_hash = request.get("payload_sha256")
        canonical_request = json.dumps(
            inner, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        if request_payload_hash != hashlib.sha256(canonical_request).hexdigest():
            raise RawContactSourceError(f"raw request {request_id!r} payload hash is invalid")
        sample_id = inner["sample_id"]
        if sample_id in contacts:
            raise RawContactSourceError(f"raw trace has duplicate sample ID {sample_id!r}")
        response = indexed["MODEL_RESPONSE"][request_id]
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise RawContactSourceError(f"raw response {request_id!r} text hash is invalid")
        wire = indexed["MODEL_WIRE_RESPONSE"][request_id]
        if wire.get("request_id") != request_id or wire.get("sample_id") != sample_id:
            raise RawContactSourceError(f"raw wire response {request_id!r} identity is invalid")
        if wire.get("finish_reason") != "stop":
            raise RawContactSourceError(f"raw wire response {request_id!r} did not stop normally")
        try:
            raw_wire = base64.b64decode(wire["response_b64"], validate=True)
        except (KeyError, TypeError, ValueError) as error:
            raise RawContactSourceError(
                f"raw wire response {request_id!r} bytes are invalid"
            ) from error
        wire_sha = hashlib.sha256(raw_wire).hexdigest()
        if wire.get("response_sha256") != wire_sha:
            raise RawContactSourceError(f"raw response {request_id!r} wire hash is invalid")
        normalized_sha = _transport_response_sha256(
            raw_wire,
            expected_text=text,
            expected_usage=response.get("usage", {}),
            expected_finish_reason=wire.get("finish_reason"),
        )
        if response.get("response_sha256") != normalized_sha:
            raise RawContactSourceError(
                f"raw response {request_id!r} normalized envelope hash is invalid"
            )
        cost = indexed["COST"][request_id]
        if cost.get("request_id", request_id) != request_id or cost.get("calls") != 1:
            raise RawContactSourceError(f"raw cost {request_id!r} identity/calls are invalid")
        audio = cost.get("audio_seconds")
        if (
            isinstance(audio, bool)
            or not isinstance(audio, (int, float))
            or not math.isfinite(audio)
            or audio < 0
        ):
            raise RawContactSourceError(f"raw cost {request_id!r} audio is invalid")
        audio_seconds += audio
        contacts[sample_id] = _readonly_mapping(
            {
                "request_id": request_id,
                "request": request,
                "response": response,
                "wire": wire,
                "cost": cost,
            }
        )
    if not math.isclose(audio_seconds, expected_audio_seconds, rel_tol=1e-9, abs_tol=1e-6):
        raise RawContactSourceError("raw trace audio cost differs from the aborted attempt")
    if set(contacts) != set(expected_sample_ids):
        raise RawContactSourceError("raw response sample IDs do not match the pinned roster")
    return (
        MappingProxyType({record_id: payload for record_id, (_channel, payload) in records.items()}),
        MappingProxyType({sample_id: contacts[sample_id] for sample_id in expected_sample_ids}),
    )


def _load_verified_trace(
    trace_pin: object,
    *,
    expected_sample_ids: Sequence[str],
    expected_audio_seconds: float,
) -> tuple[Mapping[str, Mapping[str, object]], Mapping[str, Mapping[str, object]]]:
    return _verify_trace(
        trace_pin,
        expected_sample_ids=tuple(expected_sample_ids),
        expected_audio_seconds=expected_audio_seconds,
    )


def verify_aborted_contact_source(
    *,
    attempt_pin: object,
    trace_pin: object,
    generation_plan_pin: object,
    expected_sample_ids: Sequence[str],
) -> AbortedContactSourceVerification:
    """Verify one pinned ABORTED attempt and its complete unsealed contact trace."""
    expected_ids = tuple(expected_sample_ids)
    if len(expected_ids) != len(set(expected_ids)):
        raise RawContactSourceError("expected_sample_ids contains duplicates")
    attempt_path, _attempt_sha = _pin(attempt_pin, "aborted source attempt")
    plan_path, _plan_sha = _pin(generation_plan_pin, "source generation plan")
    attempt = _json(attempt_path.read_bytes(), "aborted source attempt")
    generation_plan = _json(plan_path.read_bytes(), "source generation plan")
    if attempt.get("schema") != "saea-attempt-v1" or attempt.get("state") != STATE_ABORTED:
        raise RawContactSourceError("raw source must have an ABORTED attempt")
    try:
        plan = ExecutionPlan(
            **_map(generation_plan.get("execution_plan"), "execution plan")
        ).validate()
    except Exception as error:
        raise RawContactSourceError(f"source execution plan is invalid: {error}") from error
    for key in ("run_id", "attempt_id", "carrier_lock_key"):
        if attempt.get(key) != getattr(plan, key):
            raise RawContactSourceError(f"aborted attempt differs from source plan: {key}")
    actual = _map(attempt.get("actual"), "attempt actual cost")
    reserved = _map(attempt.get("reserved"), "attempt reserved cost")
    if (
        actual.get("calls") != len(expected_ids)
        or reserved.get("calls") != plan.planned_model_calls
        or reserved.get("audio_seconds") != plan.planned_speech_audio_seconds
        or len(expected_ids) > plan.planned_model_calls
    ):
        raise RawContactSourceError("aborted attempt cost does not match plan and roster")
    actual_audio = actual.get("audio_seconds")
    if (
        isinstance(actual_audio, bool)
        or not isinstance(actual_audio, (int, float))
        or not math.isfinite(actual_audio)
        or not 0 <= actual_audio <= plan.planned_speech_audio_seconds
    ):
        raise RawContactSourceError("aborted attempt audio cost is invalid")
    split_hash = plan.split_identity_hash
    if split_hash != split_identity_hash(prefixed(plan.carrier_lock_key, expected_ids)):
        raise RawContactSourceError("source plan split identity does not match pinned roster")
    trace_records, contacts = _verify_trace(
        trace_pin,
        expected_sample_ids=expected_ids,
        expected_audio_seconds=float(actual_audio),
    )
    return AbortedContactSourceVerification(
        attempt=_readonly_mapping(attempt),
        generation_plan=_readonly_mapping(generation_plan),
        trace_records=trace_records,
        contacts_by_sample_id=contacts,
    )


__all__ = [
    "AbortedContactSourceVerification",
    "RawContactSourceError",
    "verify_aborted_contact_source",
]
