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
from statistics import median

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


def _measurement_summary(values):
    observed = sorted(value for value in values if value is not None)
    total = math.fsum(observed) if observed else None
    return {
        "observed_contacts": len(observed), "total_contacts": len(values),
        "sum_observed": total,
        "complete_total": total if len(observed) == len(values) else None,
        "mean_observed": total / len(observed) if observed else None,
        "p50_observed": median(observed) if observed else None,
        "p95_observed": observed[math.ceil(.95 * len(observed)) - 1] if observed else None,
    }


def _client_cost(source, contact):
    record_id = contact["request_id"] + "/cost"
    if record_id not in source.bundle.trace_records:
        return {"available": False}, None
    record = source.bundle.trace_records[record_id]
    if (not isinstance(record, Mapping) or type(record.get("calls")) is not int
            or record["calls"] != 1):
        raise CacheCostError("node timing COST must identify one model contact")
    for key in ("sample_id", "request_id"):
        if key in record and record[key] != contact[key]:
            raise CacheCostError("node timing COST belongs to another sample or request")
    latency = record.get("latency_seconds")
    if (type(latency) not in (int, float) or latency < 0
            or not math.isfinite(latency) or not math.isfinite(latency * 1000)):
        raise CacheCostError("node timing COST latency must be finite and nonnegative")
    return {"available": True, "record_id": record_id,
            "content_sha256": content_hash(record)}, latency * 1000


def export_system_node_timing(source: VerifiedNativeEpisodeSource) -> dict:
    """Summarize measured node contacts after the same complete-source read gate.

    This optional sidecar leaves the existing cache export unchanged. A contact
    includes every model invocation, including tool continuations and revisits.
    Means are contact weighted; p50 is the median and p95 the nearest-rank value
    over observed contacts only. Missing values remain unknown, never zero.

    COST latency spans the adapter's transport call, including work within that
    transport. Server prompt/decode timers have different measurement boundaries.
    Do not subtract them to invent queue time, or sum overlapping contacts to
    infer episode wall time. Reuse is token weighted and requires full coverage.
    The caller still supplies the exact complete-family READ authorization.
    """
    cached = export_system_cache_cost(source)
    contacts = []
    for row in cached["contacts"]:
        values = {name: value for name, value in row["metrics"]["values"].items()
                  if name != "final_resident_tokens"}
        cost, values["client_transport_ms"] = _client_cost(source, row)
        prefill, generation = values["prefill_ms"], values["generation_ms"]
        values["server_prefill_and_generation_ms"] = (
            prefill + generation if prefill is not None and generation is not None else None)
        contacts.append({
            "sample_id": row["sample_id"], "request_id": row["request_id"],
            "role_id": row["role_id"], "visit_index": row["visit_index"],
            "interrupted": row["interrupted"], "cache_contact_sha256": content_hash(row),
            "cost_record": cost, "measurements": values,
        })
    by_role = {}
    for role in sorted({row["role_id"] for row in contacts}):
        rows = [row for row in contacts if row["role_id"] == role]
        metrics = {name: _measurement_summary([row["measurements"][name] for row in rows])
                   for name in rows[0]["measurements"]}
        total = metrics["input_tokens"]["complete_total"]
        reused = metrics["reused_input_tokens"]["complete_total"]
        by_role[role] = {
            "contacts": len(rows), "samples": len({row["sample_id"] for row in rows}),
            "visits": len({(row["sample_id"], row["visit_index"]) for row in rows}),
            "metrics": metrics,
            "reused_input_fraction": reused / total if total and reused is not None else None,
        }
    report = {
        "schema": "saea-system-node-timing-v1", "source": cached["source"],
        "cache_export_content_sha256": cached["content_sha256"],
        "contacts": contacts, "by_role": by_role,
        "model_contacts_added": 0, "scorer_contacts_added": 0,
        "statistics": "Contact-weighted mean; median p50; nearest-rank p95 over observed values; token-weighted reuse with complete coverage.",
        "timing_scope": "Server prefill/decode and client transport have distinct boundaries. Contact sums are not episode wall time or isolated GPU time; queue time is not inferred.",
        "claim_scope": "Descriptive cost observations only; cache reuse is not a policy eligibility threshold or proof of quality.",
    }
    report["content_sha256"] = content_hash(report)
    return report


def _sample_seconds_summary(values):
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "mean_seconds": math.fsum(ordered) / len(ordered) if ordered else None,
        "p50_seconds": median(ordered) if ordered else None,
        "p95_seconds": ordered[math.ceil(.95 * len(ordered)) - 1] if ordered else None,
    }


def summarize_sample_execution_timing(records, *, expected_sample_ids) -> dict:
    """Validate one complete, ordered, single-execution-per-sample dispatch.

    This pure numeric helper grants no source/read permission. Callers must bind
    records to their original structural authority or finalized scientific source.
    Refuse partial coverage, mixed batches and execution-unit mixtures. A failed
    workflow remains measured but disqualifies the report for efficiency selection.
    Completed means executor completion, not a correct or reliable task answer.
    """
    ids = tuple(expected_sample_ids)
    if (not ids or any(not isinstance(sid, str) or not sid for sid in ids)
            or len(set(ids)) != len(ids)):
        raise CacheCostError("sample timing requires a unique ordered roster")
    rows = list(records)
    if len(rows) != len(ids):
        raise CacheCostError("sample timing requires complete roster coverage")
    indexed = {}
    common = None
    for row in rows:
        if not isinstance(row, Mapping) or row.get("schema") != "saea-sample-execution-timing-v1":
            raise CacheCostError("sample timing schema is invalid")
        integer_fields = ("admission_index", "expected_samples", "slot_count", "queue_depth",
                          "batch_started_ns", "admitted_ns", "finished_ns")
        if any(type(row.get(key)) is not int or not 0 <= row[key] < 2**63 for key in integer_fields):
            raise CacheCostError("sample timing boundaries and counts must be nonnegative integers")
        index = row["admission_index"]
        if (index >= len(ids) or index in indexed or row.get("sample_id") != ids[index]
                or row.get("execution_unit_id") is not None or "execution_unit_id" not in row
                or row["expected_samples"] != len(ids)
                or row["slot_count"] < 1 or row["queue_depth"] < 1
                or not row["batch_started_ns"] <= row["admitted_ns"] <= row["finished_ns"]):
            raise CacheCostError("sample timing identity, order or boundaries are inconsistent")
        status, error = row.get("status"), row.get("error_type")
        if (not isinstance(status, str) or status not in {"completed", "failed"} or "error_type" not in row
                or (status == "completed" and error is not None)
                or (status == "failed" and (not isinstance(error, str) or not error.isidentifier()))):
            raise CacheCostError("sample timing completion status is invalid")
        identity = (row["batch_started_ns"], row["slot_count"], row["queue_depth"])
        if common is not None and common != identity:
            raise CacheCostError("sample timing cannot splice batches or scheduling envelopes")
        common = identity
        indexed[index] = dict(row)
    ordered = [indexed[index] for index in range(len(ids))]
    if any(left["admitted_ns"] > right["admitted_ns"] for left, right in zip(ordered, ordered[1:])):
        raise CacheCostError("sample timing admission clocks reverse roster order")
    samples = [{
        "sample_id": row["sample_id"], "admission_index": row["admission_index"],
        "status": row["status"], "error_type": row["error_type"],
        "elapsed_seconds": (row["finished_ns"] - row["admitted_ns"]) / 1e9,
        "admission_wait_seconds": (row["admitted_ns"] - row["batch_started_ns"]) / 1e9,
        "timing_record_sha256": content_hash(row),
    } for row in ordered]
    elapsed = [row["elapsed_seconds"] for row in samples]
    wall = (max(row["finished_ns"] for row in ordered) - common[0]) / 1e9
    failed = sum(row["status"] == "failed" for row in ordered)
    report = {
        "schema": "saea-system-sample-timing-v1", "available": True,
        "samples": samples, "all_samples": _sample_seconds_summary(elapsed),
        "first_admitted_sample": samples[0],
        "excluding_first": _sample_seconds_summary(elapsed[1:]),
        "first_slot_count_admissions": _sample_seconds_summary(elapsed[:common[1]]),
        "after_first_slot_count_admissions": _sample_seconds_summary(elapsed[common[1]:]),
        "admission_wait": _sample_seconds_summary([row["admission_wait_seconds"] for row in samples]),
        "batch_dispatch_wall_seconds": wall,
        "batch_dispatch_wall_seconds_per_sample": wall / len(samples),
        "completed_samples": len(samples) - failed, "failed_samples": failed,
        "eligible_for_efficiency_comparison": failed == 0,
        "slot_count": common[1], "queue_depth": common[2],
        "first_sample_rule": "First admitted roster member, regardless of finish order; exclude exactly this member from the separately reported remaining-sample mean.",
        "cold_start_limit": "First slot-count admissions are a diagnostic group, not a proven cold wave; the remaining samples are not guaranteed warm. No slow-sample trimming.",
        "timing_scope": "Monotonic admission-to-settled-workflow wall time includes internal model/tool waits, FIT and cleanup. Pre-admission wait is separate. Roster preparation, final persistence and official scoring are excluded. Batch wall per sample measures throughput, not individual latency.",
        "quality_constraint": "Executor completion does not establish answer correctness or reliability. Compare official task quality and delivery reliability alongside latency; cache reuse is diagnostic only.",
    }
    report["content_sha256"] = content_hash(report)
    return report


def export_system_sample_timing(source: VerifiedNativeEpisodeSource) -> dict:
    """Export numeric sample timing under the unchanged complete-source read gate.

    Historical sources without timing stay unavailable. Partial measurements are
    refused rather than silently reducing the denominator or reconstructing time.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise CacheCostError("source must be a verified native episode source")
    exported = export_system_trajectories(source)
    from ..rails.controllers import default_phase_program

    program = default_phase_program(source.composed.values["policy"]).program_id
    records, refs = [], []
    for record_id, payload in source.bundle.trace_records.items():
        if "use_sample_execution_timing" not in payload:
            continue
        row = payload["use_sample_execution_timing"]
        if (not isinstance(row, Mapping)
                or record_id != f"{row.get('sample_id')}/{program}/sample-execution-timing"):
            raise CacheCostError("sample timing trace is bound to another execution")
        records.append(row)
        refs.append({"record_id": record_id, "content_sha256": content_hash(payload)})
    report = (summarize_sample_execution_timing(records, expected_sample_ids=source.sample_ids)
              if records else {
                  "schema": "saea-system-sample-timing-v1", "available": False,
                  "reason": "Original explicit sample execution boundaries are absent.",
                  "eligible_for_efficiency_comparison": False,
              })
    report.update(source=exported["source"], timing_trace_records=sorted(refs, key=lambda r: r["record_id"]),
                  model_contacts_added=0, scorer_contacts_added=0)
    report.pop("content_sha256", None)
    report["content_sha256"] = content_hash(report)
    return report
