"""Source-bound provenance for exact-window speech feature preparation.

This module validates already-written receipts and cache audits. It performs
no encoding, service management, model contact, or cache parsing.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..contracts import STUDY_SLUG
from .preparation import (
    PreparationError,
    digest,
    hash_stable_file,
    load_artifact,
    prepare_artifact,
)
from .preparation_encoding import (
    KIND as ENCODING_KIND,
    SCHEMA as ENCODING_RECORD_SCHEMA,
)
from .preparation_feature_cache import (
    FEATURE_CACHE_AUDIT_KIND,
    FEATURE_CACHE_AUDIT_SCHEMA,
    FEATURE_CACHE_AUDIT_STATE,
)
from .preparation_windows import (
    WINDOW_FEATURE_INVENTORY_SCHEMA,
    WindowFeatureEncoderIdentity,
)
from .session import (
    PROCESS_STATE_GONE,
    SessionError,
    load_runtime_receipt,
    process_state,
    read_session_receipt,
    verify_against_runtime_receipt,
)

PROVENANCE_SCHEMA = "saea-window-feature-preparation-provenance-v1"
PROVENANCE_KIND = "window-feature-preparation-provenance-v1"
PROVENANCE_STATE = "source-bound-feature-cache-verified-serving-unqualified"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STOP_BASE_KEYS = {
    "schema",
    "study",
    "session_id",
    "session_role",
    "session_receipt_sha256",
    "runtime_receipt_sha256",
    "pid",
    "termination_signal",
    "forced",
    "stopped_at",
}
_ENCODING_KEYS = {
    "schema",
    "study",
    "run_id",
    "attempt_id",
    "session_id",
    "runtime_receipt_file_sha256",
    "runtime_receipt_document_sha256",
    "session_receipt_file_sha256",
    "inventory_sha256",
    "encoder_identity",
    "trace_manifest_hash",
    "cost",
    "current_contact_count",
    "entries",
    "feature_outputs",
}
_FEATURE_OUTPUT_KEYS = {"audio_sha256", "cache_key", "chunks"}
_CHUNK_KEYS = {
    "ordinal",
    "relative_filename",
    "file_sha256",
    "file_size",
    "n_tokens",
    "n_embd",
}
_ENTRY_KEYS = {
    "audio_sha256",
    "cache_key",
    "status",
    "success",
    "current_contact_id",
    "source_contact_id",
    "source_provenance_receipt_sha256",
}


def canonical_receipt_sha256(document: Mapping[str, object]) -> str:
    """Return the canonical hash used by session stop receipts."""

    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PreparationError(f"{label} must be a lowercase SHA256")
    return value


def _plain_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise PreparationError(f"{label} must be a non-empty string")
    return value


def _load_json(path: Path, label: str) -> tuple[Mapping[str, object], str]:
    size, file_sha256, _fingerprint = hash_stable_file(path, label)
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PreparationError(f"cannot read {label} {path}: {error}") from error
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != file_sha256:
        raise PreparationError(f"{label} changed while it was read")
    if not isinstance(document, Mapping):
        raise PreparationError(f"{label} must be a JSON object")
    return document, file_sha256


def load_preprocess_stop_chain(
    *,
    session_receipt_path: Path,
    stop_receipt_path: Path,
    runtime_receipt: Mapping[str, object],
    require_normal_stop: bool = False,
    process_state_reader: Callable[[int], str] | None = None,
):
    """Verify a preprocess session and its bound stop receipt.

    The default preserves the historical packet-promotion behavior. Strict
    callers additionally require an unforced normal stop and independently
    observe that the receipt PID is gone; a reused live PID therefore refuses.
    """

    session = read_session_receipt(session_receipt_path)
    verify_against_runtime_receipt(session, runtime_receipt)
    if session.role != "preprocess":
        raise ValueError(
            "speech packet promotion requires a preprocess session receipt"
        )
    try:
        stop_document, _stop_file_sha256 = _load_json(
            Path(stop_receipt_path), "preprocess stop receipt"
        )
    except PreparationError as error:
        raise ValueError(str(error)) from error
    wrapper_keys = {
        "schema",
        "study",
        "session_id",
        "stopped_at",
        "stop_receipt",
        "stale",
        "observed",
        "server_exit",
        "monitor_summary",
    }
    if stop_document.get("schema") == "saea-serving-session-stop-v1":
        if set(stop_document) != wrapper_keys:
            raise ValueError("preprocess serving stop wrapper has unexpected keys")
        if (
            stop_document.get("study") != STUDY_SLUG
            or stop_document.get("session_id") != session.session_id
        ):
            raise ValueError("preprocess serving stop wrapper identity does not match")
        if stop_document.get("stale") is not False:
            raise ValueError("preprocess serving stop wrapper is stale")
        if require_normal_stop and stop_document.get("server_exit") is not None:
            raise ValueError(
                "preprocess serving stop wrapper records an unrequested server exit"
            )
        embedded = stop_document.get("stop_receipt")
        if not isinstance(embedded, Mapping):
            raise ValueError("preprocess serving stop wrapper lacks stop_receipt")
        stop = dict(embedded)
    else:
        stop = dict(stop_document)
    allowed_keys = (_STOP_BASE_KEYS, _STOP_BASE_KEYS | {"final_process_state"})
    if set(stop) not in allowed_keys:
        raise ValueError(
            "preprocess stop receipt must carry exact legacy or current stop keys"
        )
    if (
        stop["schema"] != "saea-session-stop-receipt-v1"
        or stop["study"] != STUDY_SLUG
        or stop["session_role"] != "preprocess"
        or stop["session_id"] != session.session_id
        or stop["pid"] != session.pid
        or stop["session_receipt_sha256"] != canonical_receipt_sha256(session.as_json())
        or stop["runtime_receipt_sha256"] != canonical_receipt_sha256(runtime_receipt)
    ):
        raise ValueError("preprocess session/stop/runtime receipt chain does not match")
    if require_normal_stop:
        if stop["forced"] is not False:
            raise ValueError("preprocess stop receipt is forced")
        if stop["termination_signal"] not in {"SIGTERM", "ALREADY_EXITED"}:
            raise ValueError("preprocess stop receipt does not record a normal stop")
        reader = process_state if process_state_reader is None else process_state_reader
        observed = reader(session.pid)
        if observed != PROCESS_STATE_GONE:
            raise ValueError(
                f"preprocess session pid {session.pid} is not gone: {observed}"
            )
    return session, stop


def _load_prepared_output(
    path: Path, *, kind: str, label: str
) -> tuple[Mapping[str, object], str]:
    wrapper, file_sha256 = _load_json(path, label)
    inputs = wrapper.get("inputs")
    if not isinstance(inputs, Mapping):
        raise PreparationError(f"{label} inputs must be an object")
    output = load_artifact(
        path,
        expected_sha256=file_sha256,
        kind=kind,
        inputs=inputs,
    )
    if not isinstance(output, Mapping):
        raise PreparationError(f"{label} output must be an object")
    return output, file_sha256


def _encoder_identity(value: object, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {
        "runtime_receipt_sha256",
        "build_commit",
        "decoder_gguf_sha256",
        "mmproj_sha256",
    }:
        raise PreparationError(f"{label} encoder identity is invalid")
    try:
        identity = WindowFeatureEncoderIdentity(**dict(value)).as_json()
    except (PreparationError, TypeError) as error:
        raise PreparationError(
            f"{label} encoder identity is invalid: {error}"
        ) from error
    return identity


def _runtime_encoder_identity(
    runtime: Mapping[str, object], runtime_file_sha256: str
) -> dict[str, str]:
    if runtime.get("role") != "preprocess":
        raise PreparationError("runtime receipt role must be preprocess")
    llama_cpp = runtime.get("llama_cpp")
    gguf_files = runtime.get("gguf_files")
    if not isinstance(llama_cpp, Mapping) or not isinstance(gguf_files, list):
        raise PreparationError("preprocess runtime receipt is incomplete")
    decoder = []
    mmproj = []
    for entry in gguf_files:
        if not isinstance(entry, Mapping):
            raise PreparationError("preprocess runtime GGUF entry must be an object")
        target = (
            mmproj if "mmproj" in Path(str(entry.get("path"))).name.lower() else decoder
        )
        target.append(entry)
    if len(decoder) != 1 or len(mmproj) != 1:
        raise PreparationError(
            "preprocess runtime receipt must bind exactly one decoder and one mmproj"
        )
    return _encoder_identity(
        {
            "runtime_receipt_sha256": runtime_file_sha256,
            "build_commit": llama_cpp.get("build_commit"),
            "decoder_gguf_sha256": decoder[0].get("sha256"),
            "mmproj_sha256": mmproj[0].get("sha256"),
        },
        "runtime receipt",
    )


def _validate_encoding_entries(
    record: Mapping[str, object],
) -> tuple[list[dict[str, object]], int]:
    raw_entries = record.get("entries")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise PreparationError("encoding record entries must be a non-empty list")
    entries = []
    seen_sources = set()
    current_contacts = set()
    successful_current_contacts = 0
    for raw in raw_entries:
        if not isinstance(raw, Mapping) or set(raw) != _ENTRY_KEYS:
            raise PreparationError("encoding record entry keys are invalid")
        entry = dict(raw)
        audio_sha256 = _sha(entry["audio_sha256"], "encoding audio")
        cache_key = entry["cache_key"]
        if not isinstance(cache_key, str) or not cache_key.isdecimal():
            raise PreparationError("encoding cache_key must be a decimal FNV key")
        source = (audio_sha256, cache_key)
        if source in seen_sources:
            raise PreparationError("encoding record has duplicate audio/cache coverage")
        seen_sources.add(source)
        status = entry["status"]
        success = entry["success"]
        current = entry["current_contact_id"]
        source_contact = entry["source_contact_id"]
        source_receipt = entry["source_provenance_receipt_sha256"]
        if status == "encoded":
            if success is not True or not isinstance(current, str) or not current:
                raise PreparationError("encoded entry lacks successful current contact")
            if source_contact is not None or source_receipt is not None:
                raise PreparationError("encoded entry must not claim a source receipt")
        elif status == "verified-warm-reuse":
            if (
                success is not True
                or current is not None
                or not isinstance(source_contact, str)
                or not source_contact
            ):
                raise PreparationError("warm reuse contact provenance is invalid")
            _sha(source_receipt, "warm source provenance receipt")
        else:
            raise PreparationError("encoding record status is unknown")
        if current is not None:
            if current in current_contacts:
                raise PreparationError(
                    "encoding record has duplicate current contact IDs"
                )
            current_contacts.add(current)
        if status == "encoded":
            successful_current_contacts += 1
        entries.append(entry)
    return entries, successful_current_contacts


def _validate_feature_outputs(
    value: object,
) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value:
        raise PreparationError("encoding feature_outputs must be a non-empty list")
    outputs = []
    seen = set()
    for raw in value:
        if not isinstance(raw, Mapping) or set(raw) != _FEATURE_OUTPUT_KEYS:
            raise PreparationError("encoding feature output keys are invalid")
        audio_sha256 = _sha(raw["audio_sha256"], "encoding feature output audio")
        cache_key = raw["cache_key"]
        chunks = raw["chunks"]
        if not isinstance(cache_key, str) or not cache_key.isdecimal():
            raise PreparationError("encoding feature output cache key is invalid")
        identity = (audio_sha256, cache_key)
        if identity in seen:
            raise PreparationError(
                "encoding feature outputs repeat audio/cache identity"
            )
        seen.add(identity)
        if not isinstance(chunks, list) or not chunks:
            raise PreparationError("encoding feature output chunks are missing")
        normalized_chunks = []
        for expected_ordinal, raw_chunk in enumerate(chunks):
            if not isinstance(raw_chunk, Mapping) or set(raw_chunk) != _CHUNK_KEYS:
                raise PreparationError("encoding feature chunk keys are invalid")
            chunk = dict(raw_chunk)
            ordinal = chunk["ordinal"]
            filename = chunk["relative_filename"]
            if (
                isinstance(ordinal, bool)
                or not isinstance(ordinal, int)
                or ordinal != expected_ordinal
                or not isinstance(filename, str)
                or filename != f"{cache_key}_o{ordinal}.feat"
            ):
                raise PreparationError("encoding feature chunk identity is invalid")
            _sha(chunk["file_sha256"], "encoding feature chunk file")
            for field in ("file_size", "n_tokens", "n_embd"):
                number = chunk[field]
                if (
                    isinstance(number, bool)
                    or not isinstance(number, int)
                    or number < 1
                ):
                    raise PreparationError(
                        f"encoding feature chunk {field} must be a positive integer"
                    )
            normalized_chunks.append(chunk)
        outputs.append(
            {
                "audio_sha256": audio_sha256,
                "cache_key": cache_key,
                "chunks": normalized_chunks,
            }
        )
    return outputs


def _validate_encoding_record_components(
    record: Mapping[str, object],
    *,
    expected_run_id: str,
    expected_attempt_id: str,
    expected_session_id: str,
) -> tuple[list[dict[str, object]], dict[str, str]]:
    if set(record) != _ENCODING_KEYS or record.get("schema") != ENCODING_RECORD_SCHEMA:
        raise PreparationError("encoding record schema or keys are invalid")
    if record.get("study") != STUDY_SLUG:
        raise PreparationError("encoding record study is invalid")
    for field, expected in (
        ("run_id", expected_run_id),
        ("attempt_id", expected_attempt_id),
        ("session_id", expected_session_id),
    ):
        _plain_id(expected, f"expected {field}")
        if record.get(field) != expected:
            raise PreparationError(f"encoding record {field} does not match")
    for field in (
        "runtime_receipt_file_sha256",
        "runtime_receipt_document_sha256",
        "session_receipt_file_sha256",
        "inventory_sha256",
        "trace_manifest_hash",
    ):
        _sha(record.get(field), f"encoding record {field}")
    identity = _encoder_identity(record.get("encoder_identity"), "encoding record")
    entries, observed_contacts = _validate_encoding_entries(record)
    feature_outputs = _validate_feature_outputs(record.get("feature_outputs"))
    entry_sources = {(entry["audio_sha256"], entry["cache_key"]) for entry in entries}
    feature_sources = {
        (output["audio_sha256"], output["cache_key"]) for output in feature_outputs
    }
    if entry_sources != feature_sources or len(entries) != len(feature_outputs):
        raise PreparationError("encoding entries and feature output coverage differ")
    declared_contacts = record.get("current_contact_count")
    if (
        isinstance(declared_contacts, bool)
        or not isinstance(declared_contacts, int)
        or declared_contacts < 0
    ):
        raise PreparationError("encoding record current contact count is invalid")
    cost = record.get("cost")
    if not isinstance(cost, Mapping):
        raise PreparationError("encoding record cost must be an object")
    calls_used = cost.get("calls_used")
    if (
        isinstance(calls_used, bool)
        or not isinstance(calls_used, int)
        or calls_used < 0
    ):
        raise PreparationError("encoding record cost calls_used is invalid")
    if declared_contacts != observed_contacts:
        raise PreparationError(
            "encoding record current contact count does not match entries"
        )
    if calls_used != declared_contacts:
        raise PreparationError(
            "encoding record cost calls_used does not match contact count"
        )
    return entries, identity


def validate_window_feature_encoding_record(
    record: Mapping[str, object],
    *,
    expected_run_id: str,
    expected_attempt_id: str,
    expected_session_id: str,
) -> dict[str, object]:
    """Validate one complete all-success encoder-operation handoff."""

    entries, identity = _validate_encoding_record_components(
        record,
        expected_run_id=expected_run_id,
        expected_attempt_id=expected_attempt_id,
        expected_session_id=expected_session_id,
    )
    normalized = dict(record)
    normalized["entries"] = entries
    normalized["feature_outputs"] = _validate_feature_outputs(record["feature_outputs"])
    normalized["encoder_identity"] = identity
    normalized["cost"] = dict(record["cost"])
    return normalized


def _source_outputs(
    paths: Sequence[Path],
) -> dict[str, Mapping[str, object]]:
    outputs = {}
    for path in paths:
        output, file_sha256 = _load_prepared_output(
            Path(path), kind=PROVENANCE_KIND, label="source provenance receipt"
        )
        if (
            output.get("schema") != PROVENANCE_SCHEMA
            or output.get("state") != PROVENANCE_STATE
        ):
            raise PreparationError("source provenance receipt is not complete")
        if file_sha256 in outputs:
            raise PreparationError("source provenance receipt is duplicated")
        outputs[file_sha256] = output
    return outputs


def _verify_warm_sources(
    entries: Sequence[Mapping[str, object]],
    *,
    encoder_identity: Mapping[str, object],
    feature_outputs: Sequence[Mapping[str, object]],
    source_outputs: Mapping[str, Mapping[str, object]],
) -> None:
    for entry in entries:
        if entry["status"] != "verified-warm-reuse":
            continue
        receipt_sha = str(entry["source_provenance_receipt_sha256"])
        source = source_outputs.get(receipt_sha)
        if source is None:
            raise PreparationError("warm reuse source provenance receipt is missing")
        if source.get("encoder_identity") != encoder_identity:
            raise PreparationError("warm reuse source encoder identity does not match")
        matches = [
            candidate
            for candidate in source.get("entries", ())
            if isinstance(candidate, Mapping)
            and candidate.get("audio_sha256") == entry["audio_sha256"]
            and candidate.get("cache_key") == entry["cache_key"]
        ]
        if len(matches) != 1 or matches[0].get("success") is not True:
            raise PreparationError(
                "warm reuse source audio/cache coverage does not match"
            )
        inherited = (
            matches[0].get("current_contact_id")
            if matches[0].get("status") == "encoded"
            else matches[0].get("source_contact_id")
        )
        if inherited != entry["source_contact_id"]:
            raise PreparationError("warm reuse source contact does not match")
        current_features = [
            item
            for item in feature_outputs
            if item["audio_sha256"] == entry["audio_sha256"]
            and item["cache_key"] == entry["cache_key"]
        ]
        source_features = [
            item
            for item in source.get("feature_outputs", ())
            if isinstance(item, Mapping)
            and item.get("audio_sha256") == entry["audio_sha256"]
            and item.get("cache_key") == entry["cache_key"]
        ]
        if len(current_features) != 1 or source_features != current_features:
            raise PreparationError("warm reuse source feature outputs do not match")


def prepare_window_feature_provenance(
    path: Path,
    *,
    runtime_receipt_path: Path,
    session_receipt_path: Path,
    stop_receipt_path: Path,
    encoding_record_path: Path,
    cache_audit_path: Path,
    expected_run_id: str,
    expected_attempt_id: str,
    expected_session_id: str,
    source_provenance_paths: Sequence[Path] = (),
) -> dict[str, object]:
    """Validate and persist the complete source-bound preparation chain."""

    runtime, runtime_file_sha256 = _load_json(
        runtime_receipt_path, "preprocess runtime receipt"
    )
    # Reuse the session loader used everywhere else, after stable file hashing.
    runtime_loaded = load_runtime_receipt(runtime_receipt_path)
    if runtime_loaded != runtime:
        raise PreparationError("preprocess runtime receipt changed while it was read")
    runtime_document_sha256 = canonical_receipt_sha256(runtime)
    runtime_identity = _runtime_encoder_identity(runtime, runtime_file_sha256)

    session_document, session_file_sha256 = _load_json(
        session_receipt_path, "preprocess session receipt"
    )
    stop_document, stop_file_sha256 = _load_json(
        stop_receipt_path, "preprocess stop receipt"
    )
    try:
        session, stop = load_preprocess_stop_chain(
            session_receipt_path=session_receipt_path,
            stop_receipt_path=stop_receipt_path,
            runtime_receipt=runtime,
            require_normal_stop=True,
        )
    except (ValueError, SessionError) as error:
        raise PreparationError(str(error)) from error
    stop_document_for_compare = stop_document
    if stop_document.get("schema") == "saea-serving-session-stop-v1":
        stop_document_for_compare = stop_document.get("stop_receipt")
    if session.as_json() != session_document or stop != stop_document_for_compare:
        raise PreparationError(
            "preprocess session or stop receipt changed while it was read"
        )
    if stop_document.get("schema") == "saea-serving-session-stop-v1":
        current_wrapper, current_wrapper_sha256 = _load_json(
            stop_receipt_path, "preprocess stop receipt"
        )
        if (
            current_wrapper != stop_document
            or current_wrapper_sha256 != stop_file_sha256
        ):
            raise PreparationError("preprocess stop wrapper changed while it was read")
    if session.session_id != expected_session_id:
        raise PreparationError("preprocess session ID does not match expected session")

    record, encoding_file_sha256 = _load_prepared_output(
        encoding_record_path,
        kind=ENCODING_KIND,
        label="window encoding artifact",
    )
    record = validate_window_feature_encoding_record(
        record,
        expected_run_id=expected_run_id,
        expected_attempt_id=expected_attempt_id,
        expected_session_id=expected_session_id,
    )
    entries = record["entries"]
    feature_outputs = record["feature_outputs"]
    encoding_identity = record["encoder_identity"]
    if record["runtime_receipt_file_sha256"] != runtime_file_sha256:
        raise PreparationError("encoding runtime receipt file identity does not match")
    if record["runtime_receipt_document_sha256"] != runtime_document_sha256:
        raise PreparationError(
            "encoding runtime receipt document identity does not match"
        )
    if record["session_receipt_file_sha256"] != session_file_sha256:
        raise PreparationError("encoding session receipt identity does not match")
    if encoding_identity != runtime_identity:
        raise PreparationError("encoding/runtime encoder identity does not match")

    audit, audit_file_sha256 = _load_prepared_output(
        cache_audit_path,
        kind=FEATURE_CACHE_AUDIT_KIND,
        label="window feature cache audit",
    )
    if (
        audit.get("schema") != FEATURE_CACHE_AUDIT_SCHEMA
        or audit.get("state") != FEATURE_CACHE_AUDIT_STATE
    ):
        raise PreparationError(
            "window feature cache audit schema or state does not match"
        )
    audit_identity = _encoder_identity(audit.get("encoder_identity"), "cache audit")
    if audit_identity != runtime_identity:
        raise PreparationError("cache audit/runtime encoder identity does not match")
    inventory = audit.get("inventory")
    if not isinstance(inventory, Mapping):
        raise PreparationError("cache audit inventory is missing")
    inventory_sha256 = digest(inventory)
    if (
        audit.get("inventory_sha256") != inventory_sha256
        or record["inventory_sha256"] != inventory_sha256
    ):
        raise PreparationError("encoding/cache audit inventory identity does not match")

    if inventory.get("schema") != WINDOW_FEATURE_INVENTORY_SCHEMA:
        raise PreparationError("cache audit inventory schema does not match")
    inventory_inputs = inventory.get("encoding_inputs")
    if not isinstance(inventory_inputs, list) or not inventory_inputs:
        raise PreparationError("cache audit inventory encoding inputs are missing")
    inventory_audio = [
        _sha(item.get("audio_sha256"), "window inventory audio")
        for item in inventory_inputs
        if isinstance(item, Mapping)
    ]
    if len(inventory_audio) != len(inventory_inputs) or len(inventory_audio) != len(
        set(inventory_audio)
    ):
        raise PreparationError("window inventory unique-audio coverage is invalid")

    audit_entries = audit.get("entries")
    if not isinstance(audit_entries, list) or not audit_entries:
        raise PreparationError("cache audit entries are missing")
    audit_sources = []
    for entry in audit_entries:
        if not isinstance(entry, Mapping):
            raise PreparationError("cache audit entry is invalid")
        cache_key = entry.get("cache_key")
        if not isinstance(cache_key, str) or not cache_key.isdecimal():
            raise PreparationError("cache audit key must be a decimal FNV key")
        audit_sources.append(
            (
                _sha(entry.get("audio_sha256"), "cache audit audio"),
                cache_key,
            )
        )
    if len(audit_sources) != len(set(audit_sources)):
        raise PreparationError("cache audit has duplicate audio/cache coverage")
    if {audio for audio, _key in audit_sources} != set(inventory_audio):
        raise PreparationError("cache audit does not cover inventory unique audio")
    encoded_sources = [(entry["audio_sha256"], entry["cache_key"]) for entry in entries]
    if set(encoded_sources) != set(audit_sources) or len(encoded_sources) != len(
        audit_sources
    ):
        raise PreparationError("encoding/cache audit coverage does not match")
    encoded_feature_map = {
        (entry["audio_sha256"], entry["cache_key"]): entry["chunks"]
        for entry in feature_outputs
    }
    audit_feature_map = {
        (entry["audio_sha256"], entry["cache_key"]): entry["chunks"]
        for entry in audit_entries
    }
    if encoded_feature_map != audit_feature_map:
        raise PreparationError("encoding/cache audit feature outputs do not match")
    if any(
        entry["status"] == "failed" or entry["success"] is not True for entry in entries
    ):
        raise PreparationError("encoding record contains a failed input")

    sources = _source_outputs(source_provenance_paths)
    _verify_warm_sources(
        entries,
        encoder_identity=runtime_identity,
        feature_outputs=feature_outputs,
        source_outputs=sources,
    )
    used_source_hashes = {
        entry["source_provenance_receipt_sha256"]
        for entry in entries
        if entry["status"] == "verified-warm-reuse"
    }
    if set(sources) != used_source_hashes:
        raise PreparationError("unused or missing warm source provenance receipt")

    output = {
        "schema": PROVENANCE_SCHEMA,
        "state": PROVENANCE_STATE,
        "study": STUDY_SLUG,
        "run_id": expected_run_id,
        "attempt_id": expected_attempt_id,
        "session_id": expected_session_id,
        "runtime_receipt_file_sha256": runtime_file_sha256,
        "runtime_receipt_document_sha256": runtime_document_sha256,
        "session_receipt_file_sha256": session_file_sha256,
        "stop_receipt_file_sha256": stop_file_sha256,
        "encoding_record_file_sha256": encoding_file_sha256,
        "cache_audit_file_sha256": audit_file_sha256,
        "inventory_sha256": inventory_sha256,
        "encoder_identity": runtime_identity,
        "trace_manifest_hash": record["trace_manifest_hash"],
        "cost": dict(record["cost"]),
        "current_contact_count": record["current_contact_count"],
        "unique_audio_count": len(entries),
        "entries": entries,
        "feature_outputs": feature_outputs,
    }
    inputs = {
        key: output[key]
        for key in (
            "run_id",
            "attempt_id",
            "session_id",
            "runtime_receipt_file_sha256",
            "runtime_receipt_document_sha256",
            "session_receipt_file_sha256",
            "stop_receipt_file_sha256",
            "encoding_record_file_sha256",
            "cache_audit_file_sha256",
            "inventory_sha256",
            "encoder_identity",
        )
    }
    inputs["source_provenance_receipt_sha256s"] = sorted(sources)
    return prepare_artifact(
        path,
        kind=PROVENANCE_KIND,
        inputs=inputs,
        producer=lambda: output,
        contact_class="model-free",
    )
