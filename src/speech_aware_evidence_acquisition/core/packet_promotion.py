"""Carrier-neutral promotion of verified legacy speech cache packets."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from .model import materialize_legacy_cached_speech_feature_packets
from .preparation import hash_stable_file

PLAN_SCHEMA = "saea-legacy-speech-packet-promotion-plan-v1"
RECEIPT_SCHEMA = "saea-legacy-speech-packet-promotion-receipt-v1"
_SHA256 = set("0123456789abcdef")


def _require_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or set(value) - _SHA256:
        raise ValueError(f"{label} must be a lowercase 64-hex SHA-256")
    return value


def _load_pinned_json(path: Path, expected_sha256: object, label: str) -> Mapping[str, object]:
    _require_sha256(expected_sha256, f"{label} SHA-256")
    _, actual, _ = hash_stable_file(path, label)
    if actual != expected_sha256:
        raise ValueError(f"{label} SHA-256 mismatch")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"{label} must be a JSON object")
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
    if sample_id.count(":") != 1:
        raise ValueError("source roster sample_id must be tier:item")
    tier, item = sample_id.split(":")
    if not tier or not item or "/" in sample_id or "\\" in sample_id:
        raise ValueError("source roster sample_id is unsafe")
    return f"{tier}/{item}"


def _validate_plan(plan: Mapping[str, object]) -> dict[str, object]:
    required = {
        "schema", "source_root", "source_roster_path", "source_roster_sha256",
        "cache_provenance_path", "cache_provenance_sha256", "legacy_cache_dir",
        "feature_root", "receipt_output", "decoder_gguf_sha256", "mmproj_sha256",
        "expected_n_embd", "causal_attention", "workers",
    }
    if set(plan) != required or plan.get("schema") != PLAN_SCHEMA:
        raise ValueError(f"promotion plan must have exact schema and keys {sorted(required)}")
    for field in (
        "source_roster_sha256", "cache_provenance_sha256",
        "decoder_gguf_sha256", "mmproj_sha256",
    ):
        _require_sha256(plan[field], field)
    source_root = Path(str(plan["source_root"]))
    paths = {
        name: Path(str(plan[name]))
        for name in ("source_roster_path", "cache_provenance_path", "legacy_cache_dir",
                     "feature_root", "receipt_output")
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
    if not isinstance(plan["workers"], int) or isinstance(plan["workers"], bool) or not 1 <= plan["workers"] <= 64:
        raise ValueError("workers must be an integer in [1, 64]")
    return {**plan, "source_root": source_root.resolve(), **paths}


def _preflight_bindings(plan: Mapping[str, object]) -> tuple[tuple[dict[str, str], ...], Mapping[str, object]]:
    roster = _load_pinned_json(
        plan["source_roster_path"], plan["source_roster_sha256"], "source roster"
    )
    provenance = _load_pinned_json(
        plan["cache_provenance_path"], plan["cache_provenance_sha256"], "cache provenance"
    )
    required_roster = {"schema", "count", "samples"}
    if set(roster) != required_roster or not isinstance(roster["samples"], list):
        raise ValueError("source roster must contain exact schema/count/samples")
    if roster["count"] != len(roster["samples"]) or not roster["samples"]:
        raise ValueError("source roster count disagrees with samples")
    if not isinstance(provenance.get("sources"), list):
        raise ValueError("cache provenance must carry a sources list")
    sources: dict[str, Mapping[str, object]] = {}
    for index, source in enumerate(provenance["sources"]):
        if not isinstance(source, Mapping):
            raise ValueError(f"cache provenance source {index} must be an object")
        required_source = {
            "sample_id", "audio_sha256", "encoder_receipt_sha256",
            "decoder_gguf_sha256", "mmproj_sha256", "session_role",
        }
        if set(source) != required_source:
            raise ValueError(f"cache provenance source {index} has unexpected fields")
        sample_id = source["sample_id"]
        _packet_id(sample_id)
        if sample_id in sources:
            raise ValueError(f"duplicate cache provenance sample_id {sample_id!r}")
        for field in (
            "audio_sha256", "encoder_receipt_sha256",
            "decoder_gguf_sha256", "mmproj_sha256",
        ):
            _require_sha256(source[field], f"cache provenance {field}")
        if source["session_role"] not in {"legacy", "inference", "preprocess"}:
            raise ValueError("cache provenance session_role must be legacy, inference, or preprocess")
        if source["decoder_gguf_sha256"] != plan["decoder_gguf_sha256"] or source["mmproj_sha256"] != plan["mmproj_sha256"]:
            raise ValueError("cache provenance model identity disagrees with promotion plan")
        sources[sample_id] = source
    bindings: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, sample in enumerate(roster["samples"]):
        if not isinstance(sample, Mapping) or set(sample) != {"sample_id", "media_relpath", "audio_sha256"}:
            raise ValueError(f"source roster sample {index} must have exact fields")
        sample_id = sample["sample_id"]
        packet_id = _packet_id(sample_id)
        if sample_id in seen:
            raise ValueError(f"duplicate source roster sample_id {sample_id!r}")
        seen.add(sample_id)
        audio_sha256 = _require_sha256(sample["audio_sha256"], "source roster audio_sha256")
        source = sources.get(sample_id)
        if source is None or source["audio_sha256"] != audio_sha256:
            raise ValueError(f"source roster item {sample_id!r} lacks matching cache provenance")
        media = _confined_file(plan["source_root"], sample["media_relpath"], "source roster media_relpath")
        _, actual, _ = hash_stable_file(media, f"source media {sample_id}")
        if actual != audio_sha256:
            raise ValueError(f"source media SHA-256 mismatch for {sample_id!r}")
        bindings.append({"packet_id": packet_id, "audio_path": str(media)})
    if set(sources) != seen:
        raise ValueError("cache provenance sources must cover exactly the source roster")
    return tuple(bindings), provenance


def promote_pinned_roster_legacy_cache(
    *,
    promotion_plan: Path,
    promotion_plan_sha256: str,
) -> Mapping[str, object]:
    """Promote one immutable source roster after all source bindings preflight."""

    plan = _validate_plan(_load_pinned_json(
        Path(promotion_plan), promotion_plan_sha256, "promotion plan"
    ))
    bindings, _ = _preflight_bindings(plan)
    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=plan["feature_root"],
        bindings=bindings,
        legacy_cache_dir=plan["legacy_cache_dir"],
        encoder_receipt_sha256=plan["cache_provenance_sha256"],
        decoder_gguf_sha256=plan["decoder_gguf_sha256"],
        mmproj_sha256=plan["mmproj_sha256"],
        expected_n_embd=plan["expected_n_embd"],
        causal_attention=plan["causal_attention"],
        workers=plan["workers"],
    )
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "source_roster_path": str(plan["source_roster_path"]),
        "source_roster_sha256": plan["source_roster_sha256"],
        "cache_provenance_path": str(plan["cache_provenance_path"]),
        "cache_provenance_sha256": plan["cache_provenance_sha256"],
        "legacy_cache_dir": str(plan["legacy_cache_dir"]),
        "feature_root": str(plan["feature_root"]),
        "count": len(packets),
        "packets": [
            {
                "packet_id": packet.packet_id,
                "packet_sha256": packet.packet_sha256,
                "audio_sha256": packet.audio_sha256,
                "decoder_gguf_sha256": packet.decoder_gguf_sha256,
                "mmproj_sha256": packet.mmproj_sha256,
            }
            for packet in packets
        ],
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
