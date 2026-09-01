"""Bundle verification: outputs.jsonl / raw-trace parsing and the outputs<->trace
cross-checks (I7).

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

from ...contracts import BoundaryViolation, TraceContractError, TraceRecord
from . import BundleError


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _minimum_model_calls_from_trace(
    trace_records: Mapping[str, Mapping[str, object]],
    *,
    output_request_ids: frozenset[str] | None = None,
) -> int:
    """Derive the model-call cost floor while admitting traced tool composites.

    A normal model request carries the transport envelope fields ``arm``,
    ``payload``, and ``payload_sha256``. A deterministic tool-derived output
    instead carries ``tool_id`` and must bind either a model response in the
    same trace or immutable source bytes whose SHA-256 is re-measured here.
    The latter is what lets a complete prediction manifest reuse a frozen M0
    row without pretending that the current attempt made another model call.
    """

    model_requests = 0
    derived_ids = (
        output_request_ids
        if output_request_ids is not None
        else frozenset(
            record_id[: -len("/request")]
            for record_id, payload in trace_records.items()
            if record_id.endswith("/request") and "tool_id" in payload
        )
    )
    for record_id, payload in trace_records.items():
        if not record_id.endswith("/request"):
            continue
        request_id = record_id[: -len("/request")]
        if (
            isinstance(payload.get("arm"), str)
            and isinstance(payload.get("payload"), Mapping)
            and _is_sha256(payload.get("payload_sha256"))
        ):
            model_requests += 1
            continue
        if request_id not in derived_ids:
            continue
        tool_id = payload.get("tool_id")
        source = payload.get("source")
        if not isinstance(tool_id, str) or not tool_id or not isinstance(source, Mapping):
            raise BundleError(
                f"tool-derived output {request_id!r} lacks bound source provenance"
            )
        source_request_id = source.get("source_request_id")
        if isinstance(source_request_id, str) and source_request_id:
            if f"{source_request_id}/response" not in trace_records:
                raise BundleError(
                    f"tool-derived output {request_id!r} source provenance names "
                    f"missing response {source_request_id!r}"
                )
            continue
        source_path_value = source.get("source_artifact_path")
        source_sha256 = source.get("source_artifact_sha256")
        if not isinstance(source_path_value, str) or not _is_sha256(source_sha256):
            raise BundleError(
                f"tool-derived output {request_id!r} lacks bound source provenance"
            )
        source_path = Path(source_path_value)
        if not source_path.is_absolute() or not source_path.is_file():
            raise BundleError(
                f"tool-derived output {request_id!r} source artifact is unavailable"
            )
        actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if actual_sha256 != source_sha256:
            raise BundleError(
                f"tool-derived output {request_id!r} source artifact hash drifted"
            )
    return model_requests


def _split_jsonl(text: str) -> list[str]:
    """Split on the literal record separator only (matches ``core.tracing``'s
    and ``core.scorers``' own discipline): ``json.dumps(ensure_ascii=False)``
    leaves U+2028/U+2029 inside string values, which ``str.splitlines()``
    would wrongly treat as line breaks."""

    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    return lines


_REQUIRED_OUTPUTS_FIELDS = frozenset(
    {
        "request_id",
        "sample_id",
        "carrier_lock_key",
        "arm",
        "text",
        "admitted",
        "request_sha256",
        "response_sha256",
        "response_text_sha256",
    }
)


def _verify_outputs(
    raw: bytes | None, split_ids: frozenset, carrier_lock_key: str, arm: str
) -> tuple[Mapping[str, object], ...]:
    if raw is None:
        return ()
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"outputs artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    if not lines:
        raise BundleError("outputs artifact is empty")
    rows: list[Mapping[str, object]] = []
    seen: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"outputs line {number} malformed: {error}") from error
        if not isinstance(row, Mapping):
            raise BundleError(f"outputs line {number} must be a JSON object")
        missing = _REQUIRED_OUTPUTS_FIELDS - set(row)
        if missing:
            raise BundleError(f"outputs line {number} lacks required fields {sorted(missing)}")
        # IMPORTANT fix (round-2 external-threat-model review): an outputs
        # row's own carrier_lock_key/arm must BIND to the manifest's
        # VERIFIED split carrier/arm, never merely be internally present.
        # Before this, verify_bundle only checked that carrier_lock_key
        # existed on each row -- core.scorers.score_asr_outputs then resolves
        # the reference corpus straight from that unverified field.
        # Demonstrated: a manifest split carrier of earnings21-original with
        # every outputs row rewritten to carrier_lock_key=earnings22-original
        # (text and every row hash left untouched, only the outer outputs
        # artifact hash recomputed) verified successfully and scored a
        # "totally wrong" hypothesis against the OTHER carrier's references
        # (mean_wer=0.0) -- an internally inconsistent bundle that
        # verify_bundle had no check that would ever notice. `arm` is bound
        # the same way: it is load-bearing for the protocol_hash
        # re-derivation below, so an outputs row silently disagreeing with
        # the manifest's own arm must refuse too, not merely be ignored.
        row_carrier = row["carrier_lock_key"]
        if row_carrier != carrier_lock_key:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} carrier_lock_key {row_carrier!r} "
                "does not match the manifest's verified split carrier_lock_key "
                f"{carrier_lock_key!r} -- an outputs row must bind to the split it claims "
                "to belong to, never merely carry some carrier value of its own (I7 round-2)"
            )
        row_arm = row["arm"]
        if row_arm != arm:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} arm {row_arm!r} does not match the "
                f"manifest's own arm {arm!r} -- arm is load-bearing for the protocol-hash "
                "re-derivation and must bind to the manifest, not merely be present"
            )
        text_value = row["text"]
        if not isinstance(text_value, str):
            raise BundleError(f"outputs line {number} field 'text' must be a string")
        recomputed = hashlib.sha256(text_value.encode("utf-8")).hexdigest()
        if recomputed != row["response_text_sha256"]:
            raise BundleError(
                f"outputs row {row.get('sample_id')!r} (request {row.get('request_id')!r}): "
                "text does not match its recorded response_text_sha256 -- the text was "
                "mutated after the model response was recorded (I7)"
            )
        sample_id = row["sample_id"]
        if not isinstance(sample_id, str):
            raise BundleError(f"outputs line {number} field 'sample_id' must be a string")
        seen[sample_id] = seen.get(sample_id, 0) + 1
        rows.append(row)
    duplicates = sorted(sample_id for sample_id, count in seen.items() if count > 1)
    if duplicates:
        raise BundleError(f"outputs sample set contains duplicate sample ids: {duplicates}")
    row_ids = frozenset(seen)
    missing_ids = sorted(split_ids - row_ids)
    if missing_ids:
        raise BundleError(
            f"outputs sample set is missing frozen split ids: {missing_ids[:10]}"
            + (" (+more)" if len(missing_ids) > 10 else "")
        )
    extra_ids = sorted(row_ids - split_ids)
    if extra_ids:
        raise BundleError(
            f"outputs sample set contains ids outside the frozen split: {extra_ids[:10]}"
            + (" (+more)" if len(extra_ids) > 10 else "")
        )
    return tuple(rows)


def _verify_raw_trace(
    raw: bytes | None, trace_manifest_raw: bytes | None
) -> Mapping[str, Mapping[str, object]]:
    if raw is None:
        return {}
    try:
        text = raw.decode("utf-8")
    except UnicodeError as error:
        raise BundleError(f"raw trace artifact is not valid UTF-8: {error}") from error
    lines = _split_jsonl(text)
    records: dict[str, Mapping[str, object]] = {}
    hashes: dict[str, str] = {}
    for number, line in enumerate(lines, start=1):
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise BundleError(f"raw trace line {number} malformed: {error}") from error
        if not isinstance(document, Mapping) or not {"channel", "record_id", "payload"} <= set(
            document
        ):
            raise BundleError(f"raw trace line {number} must carry channel/record_id/payload")
        record_id = document["record_id"]
        if not isinstance(record_id, str):
            raise BundleError(f"raw trace line {number} record_id must be a string")
        if record_id in records:
            raise BundleError(f"raw trace contains duplicate record_id {record_id!r}")
        try:
            content_hash = TraceRecord(
                channel=document["channel"], record_id=record_id, payload=document["payload"]
            ).content_hash()
        except (TraceContractError, BoundaryViolation) as error:
            raise BundleError(f"raw trace record {record_id!r} is invalid: {error}") from error
        records[record_id] = dict(document["payload"])
        hashes[record_id] = content_hash

    if trace_manifest_raw is not None:
        try:
            trace_manifest_doc = json.loads(trace_manifest_raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise BundleError(f"trace manifest artifact is not valid JSON: {error}") from error
        manifest_records = trace_manifest_doc.get("records")
        if not isinstance(manifest_records, Mapping):
            raise BundleError("trace manifest artifact lacks a 'records' mapping")
        missing_in_manifest = sorted(set(hashes) - set(manifest_records))
        extra_in_manifest = sorted(set(manifest_records) - set(hashes))
        if missing_in_manifest or extra_in_manifest:
            raise BundleError(
                "trace manifest does not match the raw trace record set: "
                f"missing_in_manifest={missing_in_manifest[:10]} "
                f"extra_in_manifest={extra_in_manifest[:10]}"
            )
        for record_id, recorded_hash in manifest_records.items():
            if hashes[record_id] != recorded_hash:
                raise BundleError(
                    f"trace manifest hash for record {record_id!r} does not match the "
                    "raw trace record bytes (I7: trace manifest must match raw trace)"
                )
    return records


def _verify_outputs_trace_binding(
    outputs_rows: tuple[Mapping[str, object], ...], trace_records: Mapping[str, Mapping[str, object]]
) -> None:
    # CRITICAL fix (T6 fix round): the ORIGINAL code also returned early when
    # trace_records was empty -- "there are no trace records to bind against"
    # -- which meant an emptied (or never-populated) trace silently defeated
    # this ENTIRE check for a non-empty outputs file: truncate raw_trace to
    # nothing, empty trace_manifest's records, recompute those two outer
    # hashes, and any forged outputs text (with its response_text_sha256
    # recomputed to match) sailed straight through verify_bundle. There is
    # no legitimate reason for a COMPLETED, non-empty outputs bundle to have
    # zero trace records (every sample emits at least an OBS record and a
    # MODEL_RESPONSE record) -- so an empty/short trace against non-empty
    # outputs must FAIL, not silently skip. Only truly EMPTY outputs (already
    # refused earlier as "outputs artifact is empty" whenever an outputs
    # artifact exists at all) has nothing to bind.
    if not outputs_rows:
        return
    for row in outputs_rows:
        request_id = row["request_id"]
        response_record_id = f"{request_id}/response"
        if response_record_id not in trace_records:
            raise BundleError(
                f"outputs request_id {request_id!r} has no matching trace record "
                f"{response_record_id!r} (I7: every outputs request_id must appear in the trace)"
            )
        payload = trace_records[response_record_id]
        for field in ("text", "response_sha256", "response_text_sha256"):
            if payload.get(field) != row.get(field):
                raise BundleError(
                    f"outputs {field} for request {request_id!r} disagrees with the trace "
                    f"record {response_record_id!r}"
                )
        # LOW/INFO fix (T6 fix-2 round): this was previously hedged
        # (`if request_payload is not None and ...`), so deleting the
        # `{request_id}/request` trace record (and its trace-manifest entry,
        # self-consistently) let a hand-forged request_sha256 pass -- the
        # SAME "must exist" discipline the /response check above already
        # enforces unconditionally, now applied here too.
        request_record_id = f"{request_id}/request"
        if request_record_id not in trace_records:
            raise BundleError(
                f"outputs request_id {request_id!r} has no matching trace record "
                f"{request_record_id!r} (I7: every outputs request_id must appear in the trace)"
            )
        request_payload = trace_records[request_record_id]
        if request_payload.get("payload_sha256") != row.get("request_sha256"):
            raise BundleError(
                f"outputs request_sha256 for request {request_id!r} disagrees with the trace "
                f"record {request_record_id!r}"
            )
