"""Carrier-neutral promotion of audit-pinned legacy speech cache packets."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .data_root_placeholder import expand_data_root
from .model import (
    inspect_legacy_cached_speech_feature_cache,
    materialize_legacy_cached_speech_feature_packets,
)
from .preparation_feature_provenance import canonical_receipt_sha256
from .session import SessionReceipt, verify_against_runtime_receipt

PLAN_SCHEMA = "saea-legacy-speech-packet-promotion-plan-v1"
RECEIPT_SCHEMA = "saea-legacy-speech-packet-promotion-receipt-v1"
AUDIT_SCHEMA = "saea-legacy-cache-inspection-report-v1"
_SHA256 = set("0123456789abcdef")
_ROLES = {"legacy", "inference", "preprocess"}


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - _SHA256:
        raise ValueError(f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _read_pinned_json(
    path: Path, expected_sha256: object, label: str
) -> Mapping[str, object]:
    """Hash and parse the same stable bytes; never hash one read and parse another."""

    _require_sha256(expected_sha256, f"{label} SHA-256")
    path = Path(path)
    try:
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
    except OSError as error:
        raise ValueError(f"cannot read {label}: {error}") from error
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
        after.st_ino,
        after.st_size,
        after.st_mtime_ns,
    ):
        raise ValueError(f"{label} changed while it was read")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"{label} SHA-256 mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot parse {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return document


def _read_receipt_artifact(
    descriptor: object, label: str, *, canonical: bool
) -> Mapping[str, object]:
    if not isinstance(descriptor, Mapping):
        raise ValueError(f"{label} descriptor must be an object")
    required = {"path", "file_sha256"}
    if canonical:
        required.add("document_sha256")
    if set(descriptor) != required:
        raise ValueError(f"{label} descriptor has invalid fields")
    path = Path(str(descriptor["path"]))
    if not path.is_absolute():
        raise ValueError(f"{label} path must be absolute")
    document = _read_pinned_json(path, descriptor["file_sha256"], label)
    if canonical and canonical_receipt_sha256(document) != _require_sha256(
        descriptor["document_sha256"], f"{label} document_sha256"
    ):
        raise ValueError(f"{label} canonical document SHA-256 mismatch")
    return document


def _confined_file(root: Path, relative: object, label: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError(f"{label} must be a non-empty slash-separated relative path")
    candidate = Path(relative)
    if candidate.is_absolute() or any(part in ("", ".", "..") for part in candidate.parts):
        raise ValueError(f"{label} is unsafe")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"{label} escapes source_root") from error
    return resolved


def _packet_id(sample_id: object) -> str:
    if not isinstance(sample_id, str) or not sample_id.strip() or sample_id != sample_id.strip():
        raise ValueError("source roster sample_id must be non-blank and unpadded")
    from .flight.runtime import packet_id_for_sample
    from .model.paths import _normalized_relative_path

    return _normalized_relative_path(
        packet_id_for_sample(sample_id), "source roster packet_id"
    )


def _validate_plan(plan: Mapping[str, object]) -> dict[str, object]:
    plan = expand_data_root(dict(plan))
    required = {
        "schema", "source_root", "source_roster_path", "source_roster_sha256",
        "cache_provenance_path", "cache_provenance_sha256", "cache_audit_path",
        "cache_audit_sha256", "legacy_cache_dir", "feature_root", "receipt_output",
        "decoder_gguf_sha256", "mmproj_sha256", "expected_n_embd",
        "causal_attention", "workers",
    }
    if set(plan) != required or plan.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"promotion plan must have exact schema and keys {sorted(required)}")
    for field in (
        "source_roster_sha256", "cache_provenance_sha256", "cache_audit_sha256",
        "decoder_gguf_sha256", "mmproj_sha256",
    ):
        _require_sha256(plan[field], field)
    source_root = Path(str(plan["source_root"]))
    paths = {
        name: Path(str(plan[name]))
        for name in (
            "source_roster_path", "cache_provenance_path", "cache_audit_path",
            "legacy_cache_dir", "feature_root", "receipt_output",
        )
    }
    if not source_root.is_absolute() or any(not path.is_absolute() for path in paths.values()):
        raise ValueError("promotion plan roots and artifacts must be absolute paths")
    if not paths["legacy_cache_dir"].is_dir():
        raise ValueError("legacy_cache_dir is unavailable")
    if paths["legacy_cache_dir"].resolve() == paths["feature_root"].resolve():
        raise ValueError("legacy_cache_dir and feature_root must differ")
    if paths["receipt_output"].exists():
        raise ValueError("promotion receipt already exists")
    if not isinstance(plan["expected_n_embd"], int) or isinstance(plan["expected_n_embd"], bool) or plan["expected_n_embd"] <= 0:
        raise ValueError("expected_n_embd must be positive")
    if not isinstance(plan["causal_attention"], bool):
        raise ValueError("causal_attention must be boolean")
    if not isinstance(plan["workers"], int) or isinstance(plan["workers"], bool) or not 1 <= plan["workers"] <= 20:
        raise ValueError("workers must be an integer in [1, 20]")
    return {**plan, "source_root": source_root.resolve(), **paths}


def _verify_historical_sessions(provenance: Mapping[str, object], plan: Mapping[str, object]) -> dict[str, tuple[str, str]]:
    sessions = provenance.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise ValueError("cache provenance must contain sessions")
    runtime_by_session: dict[str, tuple[str, str]] = {}
    for index, entry in enumerate(sessions):
        required = {
            "session_id", "runtime_receipt", "session_receipt", "stop_receipt",
            "model_fragment",
        }
        if not isinstance(entry, Mapping) or not required.issubset(entry):
            raise ValueError(f"cache provenance session {index} has invalid fields")
        runtime = _read_receipt_artifact(
            entry["runtime_receipt"], f"runtime receipt {index}", canonical=True
        )
        session_document = _read_receipt_artifact(
            entry["session_receipt"], f"session receipt {index}", canonical=True
        )
        stop = _read_receipt_artifact(
            entry["stop_receipt"], f"stop receipt {index}", canonical=True
        )
        model = _read_receipt_artifact(
            entry["model_fragment"], f"model fragment {index}", canonical=False
        )
        try:
            session = SessionReceipt.from_json(session_document)
            verify_against_runtime_receipt(session, runtime)
        except Exception as error:
            raise ValueError(f"historical session {index} does not bind its runtime") from error
        if entry["session_id"] != session.session_id or session.role not in _ROLES:
            raise ValueError(f"historical session {index} identity or role is invalid")
        model_files = runtime.get("gguf_files", [])
        decoder = [item.get("sha256") for item in model_files
                   if "mmproj" not in Path(str(item.get("path"))).name.lower()]
        mmproj = [item.get("sha256") for item in model_files
                  if "mmproj" in Path(str(item.get("path"))).name.lower()]
        if decoder != [plan["decoder_gguf_sha256"]] or mmproj != [plan["mmproj_sha256"]]:
            raise ValueError("historical runtime model identity disagrees with promotion plan")
        runtime_sha = canonical_receipt_sha256(runtime)
        session_sha = canonical_receipt_sha256(session_document)
        if (
            stop.get("session_id") != session.session_id
            or stop.get("session_role") != session.role
            or stop.get("session_receipt_sha256") != session_sha
            or stop.get("runtime_receipt_sha256") != runtime_sha
            or stop.get("forced") is not False
            or stop.get("termination_signal") not in {"SIGTERM", "ALREADY_EXITED"}
        ):
            raise ValueError(f"historical stop receipt {index} is not a normal bound stop")
        server_env = model.get("server_env")
        if not isinstance(server_env, Mapping) or server_env.get("LLAMA_MTMD_FEAT_CACHE_DIR") != str(plan["legacy_cache_dir"]):
            raise ValueError(f"historical model fragment {index} does not bind legacy_cache_dir")
        if session.session_id in runtime_by_session:
            raise ValueError(f"duplicate historical session {session.session_id!r}")
        runtime_by_session[session.session_id] = (runtime_sha, session.role)
    return runtime_by_session


def _audit_rows(
    *,
    audit: Mapping[str, object],
    roster: Mapping[str, Mapping[str, object]],
    plan: Mapping[str, object],
) -> None:
    required = {
        "schema", "roster_sha256", "legacy_cache_dir", "expected_n_embd",
        "count", "status_counts", "entries",
    }
    if not required.issubset(audit) or audit["schema"] != AUDIT_SCHEMA:
        raise ValueError("cache audit schema is invalid")
    if (
        audit["legacy_cache_dir"] != str(plan["legacy_cache_dir"])
        or audit["expected_n_embd"] != plan["expected_n_embd"]
        or audit["count"] != len(audit["entries"])
        or audit["count"] != len(roster)
        or not isinstance(audit["status_counts"], Mapping)
        or audit["status_counts"].get("valid") != audit["count"]
        or not isinstance(audit["entries"], list)
    ):
        raise ValueError("cache audit root/count/status does not agree")
    seen: set[str] = set()
    def inspect_one(index_entry):
        index, entry = index_entry
        if not isinstance(entry, Mapping) or set(entry) != {"sample_id", "status", "inspection"}:
            raise ValueError(f"cache audit entry {index} has invalid fields")
        sample_id = entry["sample_id"]
        if sample_id not in roster or entry["status"] != "valid":
            raise ValueError(f"cache audit entry {index} does not match source roster")
        inspection = entry["inspection"]
        required_inspection = {"audio_sha256", "cache_key", "chunks"}
        if not isinstance(inspection, Mapping) or set(inspection) != required_inspection:
            raise ValueError(f"cache audit inspection {index} has invalid fields")
        if inspection["audio_sha256"] != roster[sample_id]["audio_sha256"]:
            raise ValueError(f"cache audit audio hash disagrees for {sample_id!r}")
        media = Path(str(roster[sample_id]["audio_path"]))
        checked = inspect_legacy_cached_speech_feature_cache(
            audio_path=media,
            legacy_cache_dir=plan["legacy_cache_dir"],
            expected_n_embd=plan["expected_n_embd"],
        )
        chunks = [
            {
                "ordinal": chunk.ordinal,
                "relative_filename": chunk.relative_filename,
                "file_sha256": chunk.file_sha256,
                "file_size": chunk.file_size,
                "n_tokens": chunk.n_tokens,
                "n_embd": chunk.n_embd,
            }
            for chunk in checked.chunks
        ]
        if (
            checked.audio_sha256 != inspection["audio_sha256"]
            or checked.cache_key != inspection["cache_key"]
            or chunks != inspection["chunks"]
        ):
            raise ValueError(f"legacy cache audit drift for {sample_id!r}")
        return sample_id

    with ThreadPoolExecutor(max_workers=plan["workers"]) as pool:
        checked_ids = list(pool.map(inspect_one, enumerate(audit["entries"])))
    seen.update(checked_ids)
    if len(checked_ids) != len(seen):
        raise ValueError("cache audit contains duplicate source IDs")

    if seen != set(roster):
        raise ValueError("cache audit does not cover exactly the source roster")


def _preflight_bindings(plan: Mapping[str, object]) -> tuple[tuple[dict[str, str], ...], Mapping[str, object], Mapping[str, object]]:
    roster_document = _read_pinned_json(plan["source_roster_path"], plan["source_roster_sha256"], "source roster")
    provenance = _read_pinned_json(plan["cache_provenance_path"], plan["cache_provenance_sha256"], "cache provenance")
    audit = _read_pinned_json(plan["cache_audit_path"], plan["cache_audit_sha256"], "cache audit")
    required_roster = {"schema", "count", "samples", "source_roster_original_sha256"}
    if not required_roster.issubset(roster_document) or not isinstance(roster_document["samples"], list):
        raise ValueError("source roster must contain schema/count/samples/source_roster_original_sha256")
    original_sha = _require_sha256(roster_document["source_roster_original_sha256"], "source_roster_original_sha256")
    if roster_document["count"] != len(roster_document["samples"]) or not roster_document["samples"]:
        raise ValueError("source roster count disagrees with samples")
    if provenance.get("cache_audit_sha256") != plan["cache_audit_sha256"] or provenance.get("source_roster_sha256") != original_sha or audit.get("roster_sha256") != original_sha:
        raise ValueError("source/provenance/cache-audit roster binding disagrees")
    runtime_by_session = _verify_historical_sessions(provenance, plan)
    sources = provenance.get("sources")
    if not isinstance(sources, list):
        raise ValueError("cache provenance must contain sources")
    source_rows: dict[str, Mapping[str, object]] = {}
    for index, source in enumerate(sources):
        required = {
            "sample_id", "audio_sha256", "encoder_receipt_sha256",
            "decoder_gguf_sha256", "mmproj_sha256", "session_role", "session_id",
        }
        if not isinstance(source, Mapping) or not required.issubset(source):
            raise ValueError(f"cache provenance source {index} lacks required fields")
        sample_id = source["sample_id"]
        _packet_id(sample_id)
        if sample_id in source_rows:
            raise ValueError(f"duplicate cache provenance sample_id {sample_id!r}")
        for field in ("audio_sha256", "encoder_receipt_sha256", "decoder_gguf_sha256", "mmproj_sha256"):
            _require_sha256(source[field], f"cache provenance {field}")
        if source["session_role"] not in _ROLES or source["session_id"] not in runtime_by_session:
            raise ValueError(f"cache provenance source {index} session is invalid")
        if (source["encoder_receipt_sha256"], source["session_role"]) != runtime_by_session[source["session_id"]]:
            raise ValueError(f"cache provenance source {index} runtime hash is invalid")
        if source["decoder_gguf_sha256"] != plan["decoder_gguf_sha256"] or source["mmproj_sha256"] != plan["mmproj_sha256"]:
            raise ValueError("cache provenance model identity disagrees with promotion plan")
        source_rows[sample_id] = source
    roster: dict[str, Mapping[str, object]] = {}
    bindings: list[dict[str, str]] = []
    for index, sample in enumerate(roster_document["samples"]):
        required = {"sample_id", "media_relpath", "audio_sha256"}
        if not isinstance(sample, Mapping) or not required.issubset(sample):
            raise ValueError(f"source roster sample {index} lacks required fields")
        sample_id = sample["sample_id"]
        if sample_id in roster:
            raise ValueError(f"duplicate source roster sample_id {sample_id!r}")
        _packet_id(sample_id)
        audio_sha = _require_sha256(sample["audio_sha256"], "source roster audio_sha256")
        source = source_rows.get(sample_id)
        if source is None or source["audio_sha256"] != audio_sha:
            raise ValueError(f"source roster item {sample_id!r} lacks matching cache provenance")
        media = _confined_file(plan["source_root"], sample["media_relpath"], "source roster media_relpath")
        roster[sample_id] = {"audio_sha256": audio_sha, "audio_path": str(media)}
        bindings.append({"packet_id": _packet_id(sample_id), "audio_path": str(media)})
    if set(source_rows) != set(roster):
        raise ValueError("cache provenance sources must cover exactly the source roster")
    _audit_rows(audit=audit, roster=roster, plan=plan)
    return tuple(bindings), provenance, audit


def promote_pinned_roster_legacy_cache(
    *, promotion_plan: Path, promotion_plan_sha256: str
) -> Mapping[str, object]:
    """Promote verified cached features; the provenance bundle becomes encoder identity."""

    plan = _validate_plan(_read_pinned_json(Path(promotion_plan), promotion_plan_sha256, "promotion plan"))
    bindings, provenance, audit = _preflight_bindings(plan)
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=plan["feature_root"], bindings=bindings,
        legacy_cache_dir=plan["legacy_cache_dir"],
        encoder_receipt_sha256=plan["cache_provenance_sha256"],
        decoder_gguf_sha256=plan["decoder_gguf_sha256"], mmproj_sha256=plan["mmproj_sha256"],
        expected_n_embd=plan["expected_n_embd"], causal_attention=plan["causal_attention"],
        workers=plan["workers"],
    )
    # Reinspect the same pinned cache and source bytes before writing the seal.
    _preflight_bindings(plan)
    packet_rows = []
    for packet in packets:
        if packet.encoder_receipt_sha256 != plan["cache_provenance_sha256"]:
            raise ValueError(f"promoted packet {packet.packet_id} has wrong provenance identity")
        packet_rows.append({
            "packet_id": packet.packet_id, "packet_sha256": packet.packet_sha256,
            "audio_sha256": packet.audio_sha256,
            "encoder_receipt_sha256": packet.encoder_receipt_sha256,
            "decoder_gguf_sha256": packet.decoder_gguf_sha256, "mmproj_sha256": packet.mmproj_sha256,
        })
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "source_roster_path": str(plan["source_roster_path"]),
        "source_roster_sha256": plan["source_roster_sha256"],
        "cache_provenance_path": str(plan["cache_provenance_path"]),
        "cache_provenance_sha256": plan["cache_provenance_sha256"],
        "cache_audit_path": str(plan["cache_audit_path"]),
        "cache_audit_sha256": plan["cache_audit_sha256"],
        "legacy_cache_dir": str(plan["legacy_cache_dir"]),
        "feature_root": str(plan["feature_root"]), "count": len(packet_rows),
        # Compatibility field: aggregate historical provenance-bundle file hash,
        # not a claim that the historical sessions were a preprocess role.
        "runtime_receipt_sha256": plan["cache_provenance_sha256"],
        "runtime_receipt_semantics": "historical-provenance-bundle-file-sha256",
        "packets": packet_rows,
    }
    output = plan["receipt_output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(receipt, handle, ensure_ascii=True, sort_keys=True, indent=2)
            handle.write("\n")
    except FileExistsError as error:
        raise ValueError("promotion receipt already exists") from error
    return receipt
