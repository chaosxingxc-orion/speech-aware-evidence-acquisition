"""Audit preserved llama.cpp cache measurements without changing model requests.

Callers must hold the exact complete-family read authorization and obtain their
source through verify_native_episode_source. This exporter does not grant read,
learning or runtime admission, and never invokes a model or an official scorer.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Mapping

from ..rails.hashing import content_hash
from .native_episode_source import VerifiedNativeEpisodeSource
from .system_trajectory import export_system_trajectories


class CacheCostError(ValueError):
    """Cache measurements are malformed or not bound to the verified source."""


# These meanings follow the pinned llama.cpp server serializer. In particular,
# tokens_cached is final slot residency, not reused input or a cache hit count.
_PATHS = {
    "input_tokens": ("usage.prompt_tokens", "usage.input_tokens"),
    "reused_input_tokens": (
        "usage.prompt_tokens_details.cached_tokens",
        "usage.input_tokens_details.cached_tokens", "timings.cache_n",
    ),
    "evaluated_input_tokens": ("timings.prompt_n",),
    "generated_tokens": ("usage.completion_tokens", "usage.output_tokens", "timings.predicted_n"),
    "prefill_ms": ("timings.prompt_ms",),
    "generation_ms": ("timings.predicted_ms",),
    "final_resident_tokens": ("tokens_cached",),
}


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CacheCostError("wire JSON contains duplicate keys")
        result[key] = value
    return result


def _finite_float(text):
    value = float(text)
    if not math.isfinite(value):
        raise CacheCostError("wire JSON contains a nonfinite number")
    return value


def _constant(_text):
    raise CacheCostError("wire JSON contains a nonfinite constant")


def _value(body, path):
    current = body
    for key in path.split("."):
        if current is None:
            return None
        if not isinstance(current, Mapping):
            raise CacheCostError("cache metric container must be an object")
        current = current.get(key)
    return current


def _empty_metrics():
    return {"values": dict.fromkeys(_PATHS), "sources": {key: [] for key in _PATHS}}


def read_llama_cache_metrics(raw: bytes, *, expected_sha256: str) -> dict:
    """Extract only numeric metadata from hash-verified, non-streaming wire JSON.

    Missing or null metadata stays unknown. Alias disagreements fail closed.
    Do not infer evaluated input from input minus reused tokens: multimodal and
    server-version accounting require their own measured timing fields.
    """
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise CacheCostError("wire response hash does not match the source")
    try:
        body = json.loads(raw, object_pairs_hook=_object, parse_float=_finite_float,
                          parse_constant=_constant)
    except (ValueError, UnicodeError) as error:
        raise CacheCostError("wire response is not unambiguous finite JSON") from error
    if not isinstance(body, Mapping):
        raise CacheCostError("wire response must be an object")
    result = _empty_metrics()
    for name, paths in _PATHS.items():
        observed = []
        for path in paths:
            value = _value(body, path)
            if value is None:
                continue
            token_count = name.endswith("tokens")
            valid = (type(value) is int if token_count else type(value) in (int, float))
            if not valid or value < 0 or (isinstance(value, float) and not math.isfinite(value)):
                raise CacheCostError(f"invalid numeric metadata at {path}")
            observed.append(value)
            result["sources"][name].append(path)
        if observed:
            if any(value != observed[0] for value in observed):
                raise CacheCostError(f"conflicting aliases for {name}")
            result["values"][name] = observed[0]
    values = result["values"]
    if (values["input_tokens"] is not None and values["reused_input_tokens"] is not None
            and values["reused_input_tokens"] > values["input_tokens"]):
        raise CacheCostError("reused input exceeds the recorded input total")
    result["wire_sha256"] = expected_sha256
    return result


def _contact_metrics(source, trajectory, visit, contact):
    wire_ref = contact["wire_response"]
    request_id = contact["request_record_id"].removesuffix("/request")
    request = source.bundle.trace_records[contact["request_record_id"]]
    if content_hash(request) != contact["request_record_sha256"]:
        raise CacheCostError("request record differs from the verified trajectory")
    slot = request["payload"].get("decoding_params", {}).get("id_slot")
    if slot is not None and (type(slot) is not int or slot < -1):
        raise CacheCostError("requested slot must be resolved; -1 denotes automatic selection")
    row = {
        "sample_id": trajectory["sample_id"], "request_id": request_id,
        "visit_index": visit["index"], "role_id": visit["role_id"],
        "stage": visit["stage"], "interrupted": visit["interrupted"],
        "requested_slot_id": slot,
        "trajectory_sha256": trajectory["trajectory_sha256"],
        "request_record_sha256": contact["request_record_sha256"],
        "request_payload_sha256": contact["request_payload_sha256"],
        "wire_response": dict(wire_ref), "metrics": _empty_metrics(),
    }
    if "record_id" not in wire_ref:
        return row
    record = source.bundle.trace_records[wire_ref["record_id"]]
    if content_hash(record) != wire_ref["content_sha256"]:
        raise CacheCostError("wire record differs from the verified trajectory")
    if record.get("sample_id") != row["sample_id"] or record.get("request_id") != request_id:
        raise CacheCostError("wire record is bound to another sample or request")
    try:
        raw = base64.b64decode(record["response_b64"], validate=True)
        row["metrics"] = read_llama_cache_metrics(raw, expected_sha256=record["response_sha256"])
    except (ValueError, TypeError, KeyError) as error:
        raise CacheCostError("wire measurements failed source verification") from error
    return row


def export_system_cache_cost(source: VerifiedNativeEpisodeSource) -> dict:
    """Preserve every complete-episode contact, including missing measurements.

    All totals distinguish observed sums from complete accounting. Reused input,
    final slot residency and prompt processing are separate quantities. This
    export contains neither task answer text nor quality measurements. The slot
    field records a request parameter, not server assignment; -1 means automatic
    selection and None means absent. Summing final residency gives repeated
    snapshots, never peak or allocated memory.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise CacheCostError("source must be a verified native episode source")
    try:
        exported = export_system_trajectories(source)
        contacts = [
            _contact_metrics(source, trajectory, visit, contact)
            for trajectory in exported["trajectories"]
            for visit in trajectory["role_visits"]
            for contact in visit["contacts"]
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise CacheCostError("complete source failed cache cost export") from error
    totals = {}
    for name in _PATHS:
        observed = [row["metrics"]["values"][name] for row in contacts
                    if row["metrics"]["values"][name] is not None]
        total = sum(observed) if observed else None
        totals[name] = {
            "observed_contacts": len(observed), "total_contacts": len(contacts),
            "sum_observed": total,
            "complete_total": total if len(observed) == len(contacts) else None,
        }
    report = {
        "schema": "saea-system-cache-cost-v1", "source": exported["source"],
        "contacts": contacts, "totals": totals,
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "claim_scope": "Recorded cache cost only; no cache-policy or quality comparison.",
    }
    report["content_sha256"] = content_hash(report)
    return report
