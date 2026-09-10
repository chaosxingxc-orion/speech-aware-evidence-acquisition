"""Model-free audit artifacts for exact legacy speech feature-cache coverage.

This module verifies warm cache files against the shared exact-window inventory.
It never encodes audio and never grants permission for a model contact.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Callable
from pathlib import Path
from typing import Mapping

from .model import FrozenCoreError, inspect_legacy_cached_speech_feature_cache
from .model import speech_features
from .model.paths import _normalized_relative_path, _resolve_confined
from .preparation import (
    PreparationError,
    canonical_bytes,
    digest,
    hash_stable_file,
    load_artifact,
    prepare_artifact,
)
from .preparation_encoding import window_encoding_sources
from .preparation_windows import (
    WINDOW_FEATURE_INVENTORY_KIND,
    WINDOW_FEATURE_INVENTORY_SCHEMA,
    WindowFeatureEncoderIdentity,
    WindowRequestBatch,
    build_window_feature_inventory,
)

FEATURE_CACHE_AUDIT_SCHEMA = "saea-window-feature-cache-audit-v1"
FEATURE_CACHE_AUDIT_KIND = "window-feature-cache-audit-v1"
FEATURE_CACHE_AUDIT_STATE = "cache-files-verified-runtime-unqualified"


def _cache_fingerprint(
    cache_dir: Path, cache_key: str
) -> dict[str, tuple[int, int, int, int]]:
    try:
        paths = cache_dir.glob(f"{cache_key}_o*.feat")
        fingerprints = {}
        for path in paths:
            stat = path.stat()
            fingerprints[path.name] = (
                stat.st_ino,
                stat.st_size,
                stat.st_mtime_ns,
                stat.st_ctime_ns,
            )
        return fingerprints
    except OSError as error:
        raise PreparationError(
            f"cannot fingerprint legacy feature-cache files under {cache_dir}: {error}"
        ) from error


def _verify_descriptor_files(cache_dir: Path, entry: Mapping[str, object]) -> None:
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
            resolved = path.resolve(strict=True)
            resolved.relative_to(cache_dir.resolve(strict=True))
            raw = resolved.read_bytes()
        except (OSError, ValueError) as error:
            raise PreparationError(
                f"cannot reread audited cache chunk {filename!r} inside the cache directory"
            ) from error
        if (
            len(raw) != expected_size
            or hashlib.sha256(raw).hexdigest() != expected_hash
        ):
            raise PreparationError(
                f"legacy feature-cache chunk {filename!r} changed during audit"
            )


_SHA256 = re.compile(r"[0-9a-f]{64}")
_REQUEST_KEY = re.compile(r"(.+)#w([0-9]+)")
_INVENTORY_KEYS = {
    "schema",
    "state",
    "encoder_identity",
    "request_count",
    "unique_audio_count",
    "batches",
    "encoding_inputs",
}
_REQUEST_KEYS = {
    "request_key",
    "payload_sha256",
    "encoding_key_sha256",
    "source_provenance",
}
_PROVENANCE_KEYS = {
    "sample_id",
    "parent_media_relpath",
    "parent_sha256",
    "parent_bytes",
    "start_seconds",
    "end_seconds",
    "audio_seconds",
    "sample_rate_hz",
    "media_relpath",
    "sha256",
    "bytes",
    "iteration",
    "preprocess",
    "pre_sha256",
}
_ENCODING_INPUT_KEYS = {
    "audio_sha256",
    "audio_byte_count",
    "encoding_key_sha256",
    "requests",
}


def _lower_sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PreparationError(f"{label} must be a lowercase SHA256")
    return value


def _positive_int(value: object, label: str, *, zero: bool = False) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < (0 if zero else 1)
    ):
        raise PreparationError(f"{label} must be a valid integer")
    return value


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreparationError(f"{label} must be finite")
    result = float(value)
    if not math.isfinite(result):
        raise PreparationError(f"{label} must be finite")
    return result


def _inventory_source_snapshot(
    inventory: Mapping[str, object],
    *,
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
) -> dict[Path, tuple[int, str, tuple[int, int, int]]]:
    """Validate persisted inventory structure and re-hash every source binding."""

    if set(inventory) != _INVENTORY_KEYS:
        raise PreparationError("saved window inventory has unexpected fields")
    if (
        inventory.get("schema") != WINDOW_FEATURE_INVENTORY_SCHEMA
        or inventory.get("state") != "inputs-verified-features-not-materialized"
    ):
        raise PreparationError("saved window inventory schema or state is invalid")
    identity = encoder_identity.as_json()
    if inventory.get("encoder_identity") != identity:
        raise PreparationError("saved window inventory encoder identity mismatch")
    try:
        root = Path(data_root).resolve(strict=True)
    except OSError as error:
        raise PreparationError("window inventory data_root is unavailable") from error
    if not root.is_dir():
        raise PreparationError("window inventory data_root is unavailable")

    batches = inventory.get("batches")
    if not isinstance(batches, list) or not batches:
        raise PreparationError("saved window inventory batches are invalid")
    names: list[str] = []
    request_count = 0
    snapshots: dict[Path, tuple[int, str, tuple[int, int, int]]] = {}
    for batch in batches:
        if not isinstance(batch, Mapping) or set(batch) != {"name", "requests"}:
            raise PreparationError("saved window inventory batch is invalid")
        name = batch["name"]
        requests = batch["requests"]
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(requests, list)
            or not requests
        ):
            raise PreparationError("saved window inventory batch identity is invalid")
        names.append(name)
        for request in requests:
            if not isinstance(request, Mapping) or set(request) != _REQUEST_KEYS:
                raise PreparationError("saved window inventory request is invalid")
            request_key = request["request_key"]
            _lower_sha(request["payload_sha256"], "window payload hash")
            encoding_key = _lower_sha(
                request["encoding_key_sha256"], "window encoding key"
            )
            source = request["source_provenance"]
            if not isinstance(source, Mapping) or set(source) != _PROVENANCE_KEYS:
                raise PreparationError("saved window source provenance is invalid")
            sample_id = source["sample_id"]
            match = (
                _REQUEST_KEY.fullmatch(request_key)
                if isinstance(request_key, str)
                else None
            )
            iteration = _positive_int(
                source["iteration"], "window iteration", zero=True
            )
            if (
                not isinstance(sample_id, str)
                or not sample_id
                or match is None
                or match.group(1) != sample_id
                or int(match.group(2)) != iteration + 1
            ):
                raise PreparationError("saved window request key disagrees with source")
            source_sha = _lower_sha(source["sha256"], "window source hash")
            parent_sha = _lower_sha(source["parent_sha256"], "window parent hash")
            if source["pre_sha256"] is not None:
                _lower_sha(source["pre_sha256"], "window pre-transform hash")
            source_size = _positive_int(source["bytes"], "window source size")
            parent_size = _positive_int(source["parent_bytes"], "window parent size")
            _positive_int(source["sample_rate_hz"], "window sample rate")
            start = _finite(source["start_seconds"], "window start")
            end = _finite(source["end_seconds"], "window end")
            seconds = _finite(source["audio_seconds"], "window duration")
            if (
                start < 0
                or end <= start
                or seconds <= 0
                or abs(end - start - seconds) > 1e-3
            ):
                raise PreparationError("saved window source span is inconsistent")
            preprocess = source["preprocess"]
            if not isinstance(preprocess, list) or any(
                not isinstance(item, str) or not item for item in preprocess
            ):
                raise PreparationError("saved window preprocess chain is invalid")
            for path_field, expected_size, expected_hash, label in (
                ("media_relpath", source_size, source_sha, "window source media"),
                (
                    "parent_media_relpath",
                    parent_size,
                    parent_sha,
                    "window parent media",
                ),
            ):
                try:
                    relative = _normalized_relative_path(source[path_field], label)
                    path = _resolve_confined(root, relative, root, label, strict=True)
                except FrozenCoreError as error:
                    raise PreparationError(str(error)) from error
                if not path.is_file():
                    raise PreparationError(f"{label} is not a file")
                if path in snapshots:
                    measured = snapshots[path]
                    current = path.stat()
                    if (current.st_ino, current.st_size, current.st_mtime_ns) != measured[2]:
                        raise PreparationError(f"{label} changed during source verification")
                else:
                    measured = hash_stable_file(path, label)
                    snapshots[path] = measured
                if measured[0] != expected_size or measured[1] != expected_hash:
                    raise PreparationError(f"{label} differs from actual bytes")
            if encoding_key != digest(
                {"encoder_identity": identity, "audio_sha256": source_sha}
            ):
                raise PreparationError("saved window request encoding key mismatch")
            request_count += 1
    if names != sorted(names) or len(names) != len(set(names)):
        raise PreparationError("saved window inventory batch names are not canonical")
    if inventory.get("request_count") != request_count:
        raise PreparationError("saved window inventory request count mismatch")

    sources = window_encoding_sources(inventory)
    encoding_inputs = inventory.get("encoding_inputs")
    if not isinstance(encoding_inputs, list) or len(encoding_inputs) != len(sources):
        raise PreparationError("saved window inventory unique audio count mismatch")
    if inventory.get("unique_audio_count") != len(sources):
        raise PreparationError("saved window inventory unique audio count mismatch")
    audios: list[str] = []
    for entry in encoding_inputs:
        if not isinstance(entry, Mapping) or set(entry) != _ENCODING_INPUT_KEYS:
            raise PreparationError("saved window encoding input is invalid")
        audio = _lower_sha(entry["audio_sha256"], "window encoding audio hash")
        audios.append(audio)
        if _positive_int(
            entry["audio_byte_count"], "window encoding audio size"
        ) != sources[audio]["bytes"] or _lower_sha(
            entry["encoding_key_sha256"], "window encoding key"
        ) != digest({"encoder_identity": identity, "audio_sha256": audio}):
            raise PreparationError("saved window encoding input identity mismatch")
    if audios != sorted(audios):
        raise PreparationError("saved window encoding inputs are not canonical")
    return snapshots


def _load_saved_window_inventory(
    path: Path,
    *,
    expected_sha256: str,
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
) -> tuple[Mapping[str, object], tuple[int, str, tuple[int, int, int]]]:
    _lower_sha(expected_sha256, "window inventory artifact hash")
    artifact_path = Path(path)
    measured = hash_stable_file(artifact_path, "window inventory artifact")
    if measured[1] != expected_sha256:
        raise PreparationError("prepared artifact file hash mismatch")
    try:
        raw = artifact_path.read_bytes()
        document = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise PreparationError(f"cannot load prepared artifact: {error}") from error
    if canonical_bytes(document) != raw:
        raise PreparationError("window inventory artifact is not canonical JSON")
    if not isinstance(document, Mapping) or not isinstance(
        document.get("output"), Mapping
    ):
        raise PreparationError("window inventory artifact is invalid")
    inventory = document["output"]
    inputs = {
        "encoder_identity": inventory.get("encoder_identity"),
        "window_sources_sha256": digest(inventory.get("batches")),
    }
    loaded = load_artifact(
        artifact_path,
        expected_sha256=expected_sha256,
        kind=WINDOW_FEATURE_INVENTORY_KIND,
        inputs=inputs,
    )
    if not isinstance(loaded, Mapping):
        raise PreparationError("window inventory artifact output is invalid")
    _inventory_source_snapshot(
        loaded, data_root=data_root, encoder_identity=encoder_identity
    )
    return loaded, measured


def _build_feature_cache_audit(
    *,
    inventory: Mapping[str, object],
    data_root: Path,
    legacy_cache_dir: Path,
    expected_n_embd: int,
    final_inventory_check: Callable[[], None],
) -> dict[str, object]:
    cache_dir = Path(legacy_cache_dir)
    try:
        resolved_cache_dir = cache_dir.resolve(strict=True)
    except OSError as error:
        raise PreparationError(
            f"legacy feature-cache directory is unavailable: {cache_dir}"
        ) from error
    if not resolved_cache_dir.is_dir():
        raise PreparationError("legacy feature-cache root must be a directory")

    entries: list[dict[str, object]] = []
    key_audio: dict[str, str] = {}
    cache_snapshots: dict[str, dict[str, tuple[int, int, int, int]]] = {}
    provenance_index: dict[tuple[str, str], Mapping[str, object]] = {}
    for batch in inventory["batches"]:
        if not isinstance(batch, Mapping) or not isinstance(batch.get("name"), str):
            raise PreparationError("window inventory batch is invalid")
        for request in batch.get("requests", []):
            if not isinstance(request, Mapping):
                raise PreparationError("window inventory request is invalid")
            request_key = request.get("request_key")
            source_provenance = request.get("source_provenance")
            if not isinstance(request_key, str) or not isinstance(
                source_provenance, Mapping
            ):
                raise PreparationError("window inventory request provenance is invalid")
            reference = (batch["name"], request_key)
            if reference in provenance_index:
                raise PreparationError("window inventory repeats a request reference")
            provenance_index[reference] = source_provenance

    try:
        resolved_data_root = Path(data_root).resolve(strict=True)
    except (OSError, ValueError) as error:
        raise PreparationError("window inventory data_root is unavailable") from error

    for source in inventory["encoding_inputs"]:
        if not isinstance(source, Mapping):
            raise PreparationError("window inventory encoding input must be an object")
        audio_sha256 = source.get("audio_sha256")
        if not isinstance(audio_sha256, str):
            raise PreparationError("window inventory audio SHA256 is missing")
        requests = source.get("requests")
        if not isinstance(requests, list) or not requests:
            raise PreparationError("window inventory request references are missing")
        reference = requests[0]
        if not isinstance(reference, Mapping):
            raise PreparationError("window inventory request reference is invalid")
        reference_key = (reference.get("batch"), reference.get("request_key"))
        provenance = provenance_index.get(reference_key)
        if provenance is None:
            raise PreparationError(
                "window inventory audio source provenance is missing"
            )
        media_relpath = provenance.get("media_relpath")
        if not isinstance(media_relpath, str):
            raise PreparationError("window inventory media path is missing")
        try:
            audio_path = (resolved_data_root / media_relpath).resolve(strict=True)
            audio_path.relative_to(resolved_data_root)
        except (OSError, ValueError) as error:
            raise PreparationError(
                "window inventory audio path escapes data_root"
            ) from error
        try:
            audio_bytes = audio_path.read_bytes()
        except OSError as error:
            raise PreparationError(
                f"cannot reread inventoried audio {audio_path}: {error}"
            ) from error
        cache_key = speech_features.legacy_audio_feature_cache_key(audio_bytes)
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
        if inspection.cache_key != cache_key:
            raise PreparationError(
                f"legacy cache key disagrees with fingerprint for {audio_sha256}"
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
        cache_snapshots.setdefault(cache_key, before)

    for entry in entries:
        _verify_descriptor_files(resolved_cache_dir, entry)
    for cache_key, before in cache_snapshots.items():
        if _cache_fingerprint(resolved_cache_dir, cache_key) != before:
            raise PreparationError(
                f"legacy feature-cache changed after audit for key {cache_key}"
            )
    final_inventory_check()

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
        batches=batches, data_root=data_root, encoder_identity=encoder_identity
    )

    def final_check() -> None:
        try:
            final_inventory = build_window_feature_inventory(
                batches=batches,
                data_root=data_root,
                encoder_identity=encoder_identity,
            )
        except PreparationError as error:
            raise PreparationError(
                f"window source changed during final audit: {error}"
            ) from error
        if digest(final_inventory) != digest(inventory):
            raise PreparationError("window inventory changed during final audit")

    return _build_feature_cache_audit(
        inventory=inventory,
        data_root=data_root,
        legacy_cache_dir=legacy_cache_dir,
        expected_n_embd=expected_n_embd,
        final_inventory_check=final_check,
    )


def build_feature_cache_audit_from_inventory_artifact(
    *,
    inventory_path: Path,
    inventory_sha256: str,
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> dict[str, object]:
    """Audit cache coverage from a hash-pinned inventory without materialization."""

    inventory, artifact_fingerprint = _load_saved_window_inventory(
        inventory_path,
        expected_sha256=inventory_sha256,
        data_root=data_root,
        encoder_identity=encoder_identity,
    )

    def final_check() -> None:
        try:
            final_inventory, final_fingerprint = _load_saved_window_inventory(
                inventory_path,
                expected_sha256=inventory_sha256,
                data_root=data_root,
                encoder_identity=encoder_identity,
            )
        except PreparationError as error:
            raise PreparationError(
                f"window source changed during final audit: {error}"
            ) from error
        if final_fingerprint != artifact_fingerprint or digest(
            final_inventory
        ) != digest(inventory):
            raise PreparationError("window inventory changed during final audit")

    return _build_feature_cache_audit(
        inventory=inventory,
        data_root=data_root,
        legacy_cache_dir=legacy_cache_dir,
        expected_n_embd=expected_n_embd,
        final_inventory_check=final_check,
    )


def prepare_feature_cache_audit_from_inventory_artifact(
    path: Path,
    *,
    inventory_path: Path,
    inventory_sha256: str,
    data_root: Path,
    encoder_identity: WindowFeatureEncoderIdentity,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> dict[str, object]:
    """Persist an audit sourced from an immutable prepared window inventory."""

    output = build_feature_cache_audit_from_inventory_artifact(
        inventory_path=inventory_path,
        inventory_sha256=inventory_sha256,
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
        producer=lambda: {
            key: value for key, value in output.items() if key != "inputs"
        },
        contact_class="model-free",
    )


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
        producer=lambda: {
            key: value for key, value in output.items() if key != "inputs"
        },
        contact_class="model-free",
    )
