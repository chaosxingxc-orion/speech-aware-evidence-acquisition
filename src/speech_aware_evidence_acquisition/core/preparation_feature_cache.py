"""Model-free audit artifacts for exact legacy speech feature-cache coverage.

This module verifies warm cache files against the shared exact-window inventory.
It never encodes audio and never grants permission for a model contact.
""" 

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

from .model import FrozenCoreError, inspect_legacy_cached_speech_feature_cache
from .model.speech_features import legacy_audio_feature_cache_key
from .preparation import PreparationError, digest, prepare_artifact
from .preparation_windows import (
    WindowFeatureEncoderIdentity,
    WindowRequestBatch,
    build_window_feature_inventory,
)

FEATURE_CACHE_AUDIT_SCHEMA = "saea-window-feature-cache-audit-v1"
FEATURE_CACHE_AUDIT_KIND = "window-feature-cache-audit-v1"
FEATURE_CACHE_AUDIT_STATE = "cache-files-verified-runtime-unqualified"


def _cache_fingerprint(cache_dir: Path, cache_key: str) -> dict[str, tuple[int, int, int]]:
    try:
        paths = cache_dir.glob(f"{cache_key}_o*.feat")
        return {
            path.name: (
                path.stat().st_ino,
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in paths
        }
    except OSError as error:
        raise PreparationError(
            f"cannot fingerprint legacy feature-cache files under {cache_dir}: {error}"
        ) from error


def _verify_descriptor_files(
    cache_dir: Path, entry: Mapping[str, object]
) -> None:
    chunks = entry["chunks"]
    if not isinstance(chunks, list):
        raise PreparationError("cache audit chunks must be a list")
    for chunk in chunks:
        if not isinstance(chunk, Mapping):
            raise PreparationError("cache audit chunk must be an object")
        filename = chunk.get("relative_filename")
        expected_hash = chunk.get("file_sha256")
        expected_size = chunk.get("file_size")
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or Path(filename).is_absolute()
            or not isinstance(expected_hash, str)
            or not isinstance(expected_size, int)
        ):
            raise PreparationError("cache audit chunk descriptor is invalid")
        path = cache_dir / filename
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise PreparationError(
                f"cannot reread audited cache chunk {filename!r}: {error}"
            ) from error
        if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise PreparationError(
                f"legacy feature-cache chunk {filename!r} changed during audit"
            )


def build_feature_cache_audit(
    *,
    batches: Mapping[str, WindowRequestBatch],
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> dict[str, object]:
    """Build a model-free, file-coverage audit from the shared inventory."""

    inventory = build_window_feature_inventory(
        batches=batches,
        data_root=data_root,
        encoder_identity=encoder_identity,
    )
    cache_dir = Path(legacy_cache_dir)
    try:
        resolved_cache_dir = cache_dir.resolve(strict=True)
    except OSError as error:
        raise PreparationError(f"legacy feature-cache directory is unavailable: {cache_dir}") from error
    if not resolved_cache_dir.is_dir():
        raise PreparationError("legacy feature-cache root must be a directory")

    entries: list[dict[str, object]] = []
    key_audio: dict[str, str] = {}
    for source in inventory["encoding_inputs"]:
        if not isinstance(source, Mapping):
            raise PreparationError("window inventory encoding input must be an object")
        audio_sha256 = source.get("audio_sha256")
        if not isinstance(audio_sha256, str):
            raise PreparationError("window inventory audio SHA256 is missing")
        requests = source.get("requests")
        if not isinstance(requests, list):
            raise PreparationError("window inventory request references are missing")
        provenance = None
        for batch in inventory["batches"]:
            for request in batch["requests"]:
                if request["request_key"] == requests[0]["request_key"] and (
                    {"batch": batch["name"], "request_key": request["request_key"]}
                    in requests
                ):
                    provenance = request["source_provenance"]
                    break
            if provenance is not None:
                break
        if not isinstance(provenance, Mapping):
            raise PreparationError("window inventory audio source provenance is missing")
        media_relpath = provenance.get("media_relpath")
        if not isinstance(media_relpath, str):
            raise PreparationError("window inventory media path is missing")
        audio_path = data_root / media_relpath
        cache_key = legacy_audio_feature_cache_key(audio_path.read_bytes())
        before = _cache_fingerprint(resolved_cache_dir, cache_key)
        try:
            inspection = inspect_legacy_cached_speech_feature_cache(
                audio_path=audio_path,
                legacy_cache_dir=resolved_cache_dir,
                expected_n_embd=expected_n_embd,
            )
        except (FrozenCoreError, OSError) as error:
            raise PreparationError(
                f"legacy feature-cache inspection failed for {audio_sha256}: {error}"
            ) from error
        after = _cache_fingerprint(resolved_cache_dir, cache_key)
        if before != after:
            raise PreparationError(
                f"legacy feature-cache changed during audit for key {cache_key}"
            )
        if inspection.audio_sha256 != audio_sha256:
            raise PreparationError(
                f"legacy cache audio SHA256 disagrees with inventory for {audio_sha256}"
            )
        previous_audio = key_audio.setdefault(inspection.cache_key, audio_sha256)
        if previous_audio != audio_sha256:
            raise PreparationError(
                f"ambiguous legacy cache key {inspection.cache_key!r} maps to distinct audio"
            )
        entry = {
            "audio_sha256": inspection.audio_sha256,
            "cache_key": inspection.cache_key,
            "requests": requests,
            "chunks": [
                {
                    "ordinal": chunk.ordinal,
                    "relative_filename": chunk.relative_filename,
                    "file_sha256": chunk.file_sha256,
                    "file_size": chunk.file_size,
                    "n_tokens": chunk.n_tokens,
                    "n_embd": chunk.n_embd,
                }
                for chunk in inspection.chunks
            ],
        }
        _verify_descriptor_files(resolved_cache_dir, entry)
        entries.append(entry)

    inputs = {
        "inventory_sha256": digest(inventory),
        "encoder_identity": inventory["encoder_identity"],
        "legacy_cache_dir": str(resolved_cache_dir),
        "expected_n_embd": expected_n_embd,
        "entries": entries,
    }
    return {
        "schema": FEATURE_CACHE_AUDIT_SCHEMA,
        "state": FEATURE_CACHE_AUDIT_STATE,
        "inventory": inventory,
        "inventory_sha256": digest(inventory),
        "encoder_identity": inventory["encoder_identity"],
        "legacy_cache_dir": str(resolved_cache_dir),
        "expected_n_embd": expected_n_embd,
        "entries": entries,
        "inputs": inputs,
    }


def prepare_feature_cache_audit(
    path: Path,
    *,
    batches: Mapping[str, WindowRequestBatch],
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> dict[str, object]:
    """Persist one model-free cache audit through the shared artifact gate."""

    output = build_feature_cache_audit(
        batches=batches,
        data_root=data_root,
        encoder_identity=encoder_identity,
        legacy_cache_dir=legacy_cache_dir,
        expected_n_embd=expected_n_embd,
    )
    inputs = output["inputs"]
    if not isinstance(inputs, Mapping):
        raise PreparationError("cache audit inputs are invalid")
    return prepare_artifact(
        path,
        kind=FEATURE_CACHE_AUDIT_KIND,
        inputs=inputs,
        producer=lambda: {key: value for key, value in output.items() if key != "inputs"},
        contact_class="model-free",
    )
