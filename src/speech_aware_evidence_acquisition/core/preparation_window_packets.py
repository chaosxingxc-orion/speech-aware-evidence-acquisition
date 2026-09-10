"""Promote source-bound exact-window cache entries into formal speech packets.

This module performs file validation and packet materialization only. It never
encodes audio, contacts a model, or manages a serving session.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from .model import load_speech_feature_packet, materialize_legacy_cached_speech_feature_packets
from .model.paths import _normalized_relative_path, _resolve_confined
from .preparation import PreparationError, canonical_bytes, digest, hash_stable_file, load_artifact, prepare_artifact
from .preparation_feature_cache import (
    FEATURE_CACHE_AUDIT_KIND, FEATURE_CACHE_AUDIT_SCHEMA, FEATURE_CACHE_AUDIT_STATE,
    _load_saved_window_inventory, _verify_descriptor_files,
)
from .preparation_feature_provenance import PROVENANCE_KIND, PROVENANCE_SCHEMA, PROVENANCE_STATE
from .preparation_windows import WindowFeatureEncoderIdentity

WINDOW_PACKET_PROMOTION_SCHEMA = "saea-window-feature-packet-promotion-v1"
WINDOW_PACKET_PROMOTION_KIND = "window-feature-packet-promotion-v1"
WINDOW_PACKET_PROMOTION_STATE = "source-bound-formal-packets-materialized"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_REQUEST_KEY = re.compile(r"(.+)#w([0-9]+)")


@dataclass(frozen=True)
class WindowPacketBinding:
    request_key: str
    source_key: str
    packet_id: str
    packet_sha256: str
    audio_sha256: str
    cache_key: str
    sources: tuple[Mapping[str, object], ...]
    chunks: tuple[Mapping[str, object], ...]

    def validate_source(self, source: Mapping[str, object]) -> None:
        if not isinstance(source, Mapping):
            raise PreparationError("window packet source must be a mapping")
        if _source_key(self.request_key, source) != self.source_key:
            raise PreparationError(f"window packet source key does not match {self.request_key!r}")
        actual = _source_identity(source)
        if actual not in [
            _source_identity(entry["source_provenance"]) for entry in self.sources
        ]:
            raise PreparationError(f"window packet source does not match {self.request_key!r}")


@dataclass(frozen=True)
class PreparedWindowFeaturePackets:
    inventory_file_sha256: str
    cache_audit_file_sha256: str
    provenance_file_sha256: str
    inventory_sha256: str
    encoder_identity: Mapping[str, str]
    legacy_cache_dir: str
    feature_root: str
    request_count: int
    unique_packet_count: int
    bindings: tuple[WindowPacketBinding, ...]
    by_request_key: Mapping[str, WindowPacketBinding]

    def binding_for(self, request_key: str, source: Mapping[str, object]) -> WindowPacketBinding:
        try:
            binding = self.by_request_key[request_key]
        except KeyError as error:
            raise PreparationError(f"no formal packet is bound to window request {request_key!r}") from error
        binding.validate_source(source)
        return binding


def _sha(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PreparationError(f"{label} must be a lowercase SHA256")
    return value


def _load_prepared_output(path: Path, *, expected_sha256: str, kind: str, label: str) -> Mapping[str, object]:
    _sha(expected_sha256, f"{label} hash")
    size, measured, _ = hash_stable_file(path, label)
    if measured != expected_sha256:
        raise PreparationError(f"{label} file hash mismatch")
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PreparationError(f"cannot read {label}: {error}") from error
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != measured:
        raise PreparationError(f"{label} changed while it was read")
    if canonical_bytes(document) != raw or not isinstance(document, Mapping):
        raise PreparationError(f"{label} must be a canonical prepared artifact")
    inputs = document.get("inputs")
    if not isinstance(inputs, Mapping):
        raise PreparationError(f"{label} prepared inputs are missing")
    output = load_artifact(Path(path), expected_sha256=expected_sha256, kind=kind, inputs=inputs)
    if not isinstance(output, Mapping):
        raise PreparationError(f"{label} output must be a mapping")
    return output


def _identity(value: object) -> WindowFeatureEncoderIdentity:
    if not isinstance(value, Mapping):
        raise PreparationError("window packet encoder identity is missing")
    try:
        identity = WindowFeatureEncoderIdentity(
            runtime_receipt_sha256=value["runtime_receipt_sha256"],
            build_commit=value["build_commit"],
            decoder_gguf_sha256=value["decoder_gguf_sha256"],
            mmproj_sha256=value["mmproj_sha256"],
        )
    except (KeyError, TypeError) as error:
        raise PreparationError("window packet encoder identity is malformed") from error
    if set(value) != set(identity.as_json()):
        raise PreparationError("window packet encoder identity has unexpected fields")
    identity.as_json()
    return identity


def _source_key(request_key: str, source: Mapping[str, object]) -> str:
    match = _REQUEST_KEY.fullmatch(request_key)
    iteration = source.get("iteration")
    if (
        match is None or not isinstance(iteration, int) or isinstance(iteration, bool)
        or match.group(1) != source.get("sample_id") or int(match.group(2)) != iteration + 1
    ):
        raise PreparationError("window packet request key disagrees with source")
    audio = _sha(source.get("sha256"), "window packet source audio")
    return f"{request_key}@{audio}"


def _source_identity(source: Mapping[str, object]) -> Mapping[str, object]:
    return {
        key: source.get(key)
        for key in (
            "sample_id", "parent_media_relpath", "parent_sha256",
            "start_seconds", "end_seconds", "audio_seconds", "sample_rate_hz",
            "sha256", "bytes", "iteration", "preprocess", "pre_sha256",
        )
    }


def _packet_id(audio_sha256: str) -> str:
    return f"window-audio/{audio_sha256[:2]}/{audio_sha256}"


def _validated_chain(
    *, inventory_path: Path, inventory_sha256: str, cache_audit_path: Path,
    cache_audit_sha256: str, provenance_path: Path, provenance_sha256: str,
    data_root: Path,
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    audit = _load_prepared_output(
        cache_audit_path, expected_sha256=cache_audit_sha256,
        kind=FEATURE_CACHE_AUDIT_KIND, label="window feature cache audit",
    )
    provenance = _load_prepared_output(
        provenance_path, expected_sha256=provenance_sha256,
        kind=PROVENANCE_KIND, label="window feature provenance",
    )
    if audit.get("schema") != FEATURE_CACHE_AUDIT_SCHEMA or audit.get("state") != FEATURE_CACHE_AUDIT_STATE:
        raise PreparationError("window feature cache audit is incomplete")
    if provenance.get("schema") != PROVENANCE_SCHEMA or provenance.get("state") != PROVENANCE_STATE:
        raise PreparationError("window feature provenance is incomplete")
    identity = _identity(provenance.get("encoder_identity"))
    inventory, _ = _load_saved_window_inventory(
        inventory_path, expected_sha256=inventory_sha256,
        data_root=data_root, encoder_identity=identity,
    )
    inventory_digest = digest(inventory)
    if (
        audit.get("inventory") != inventory
        or audit.get("inventory_sha256") != inventory_digest
        or provenance.get("inventory_sha256") != inventory_digest
        or audit.get("encoder_identity") != identity.as_json()
        or provenance.get("cache_audit_file_sha256") != cache_audit_sha256
    ):
        raise PreparationError("window packet artifact lineage does not match")
    audit_entries = audit.get("entries")
    features = provenance.get("feature_outputs")
    if not isinstance(audit_entries, list) or not isinstance(features, list):
        raise PreparationError("window packet feature coverage is missing")

    def keyed(rows: Sequence[object], label: str) -> dict[tuple[str, str], Mapping[str, object]]:
        result = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise PreparationError(f"{label} entry is invalid")
            cache_key = row.get("cache_key")
            key = (_sha(row.get("audio_sha256"), f"{label} audio"), cache_key)
            if not isinstance(cache_key, str) or not cache_key.isdecimal() or key in result:
                raise PreparationError(f"{label} coverage is duplicate or invalid")
            result[key] = row
        return result

    audited = keyed(audit_entries, "cache audit")
    proven = keyed(features, "feature provenance")
    if (
        len({audio for audio, _ in audited}) != len(audited)
        or len({key for _, key in audited}) != len(audited)
    ):
        raise PreparationError("cache audit coverage is ambiguous")
    if set(audited) != set(proven) or any(
        audited[key].get("chunks") != proven[key].get("chunks") for key in audited
    ):
        raise PreparationError("window packet audited feature descriptors do not match provenance")
    if provenance.get("unique_audio_count") != len(audited):
        raise PreparationError("window packet provenance unique-audio count is wrong")
    cache_dir = Path(str(audit.get("legacy_cache_dir")))
    for entry in audited.values():
        _verify_descriptor_files(cache_dir, entry)
    return inventory, audit, provenance


def _build_output(
    *, inventory: Mapping[str, object], audit: Mapping[str, object],
    provenance: Mapping[str, object], inventory_file_sha256: str,
    cache_audit_file_sha256: str, provenance_file_sha256: str,
    data_root: Path, feature_root: Path, workers: int,
) -> Mapping[str, object]:
    audit_by_audio = {entry["audio_sha256"]: entry for entry in audit["entries"]}
    request_sources: dict[str, list[dict[str, object]]] = {}
    source_identities: dict[str, Mapping[str, object]] = {}
    audio_by_request: dict[str, str] = {}
    for batch in inventory["batches"]:
        for request in batch["requests"]:
            key = request["request_key"]
            source = request["source_provenance"]
            _source_key(key, source)
            independent = _source_identity(source)
            previous = source_identities.setdefault(key, independent)
            if previous != independent:
                raise PreparationError("window packet request key collides with changed source identity")
            audio = source["sha256"]
            if audio_by_request.setdefault(key, audio) != audio:
                raise PreparationError("window packet request key collides with changed audio")
            request_sources.setdefault(key, []).append(
                {"batch": batch["name"], "source_provenance": dict(source)}
            )
    reference_rows = [
        (reference["batch"], reference["request_key"])
        for entry in audit["entries"] for reference in entry["requests"]
    ]
    references = set(reference_rows)
    if len(references) != len(reference_rows):
        raise PreparationError("window packet audit repeats request coverage")
    expected_references = {
        (source["batch"], key)
        for key, sources in request_sources.items() for source in sources
    }
    if references != expected_references:
        raise PreparationError("window packet audit request coverage does not match inventory")

    root = Path(data_root).resolve(strict=True)
    audio_paths: dict[str, Path] = {}
    for key, sources in request_sources.items():
        source = sources[0]["source_provenance"]
        relative = _normalized_relative_path(source["media_relpath"], "window packet source")
        audio_path = _resolve_confined(root, relative, root, "window packet source", strict=True)
        audio_paths.setdefault(audio_by_request[key], audio_path)

    packets = materialize_legacy_cached_speech_feature_packets(
        feature_root=Path(feature_root),
        bindings=tuple(
            {"packet_id": _packet_id(audio), "audio_path": str(audio_paths[audio])}
            for audio in sorted(audio_paths)
        ),
        legacy_cache_dir=Path(str(audit["legacy_cache_dir"])),
        encoder_receipt_sha256=str(provenance["runtime_receipt_document_sha256"]),
        decoder_gguf_sha256=str(provenance["encoder_identity"]["decoder_gguf_sha256"]),
        mmproj_sha256=str(provenance["encoder_identity"]["mmproj_sha256"]),
        expected_n_embd=int(audit["expected_n_embd"]),
        causal_attention=True,
        workers=workers,
    )
    packet_by_audio = {packet.audio_sha256: packet for packet in packets}
    if set(packet_by_audio) != set(audio_paths):
        raise PreparationError("promoted packet coverage does not match unique window audio")

    bindings = []
    for key in sorted(request_sources):
        audio = audio_by_request[key]
        packet = packet_by_audio[audio]
        audited = audit_by_audio[audio]
        bindings.append({
            "request_key": key,
            "source_key": f"{key}@{audio}",
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "audio_sha256": audio,
            "cache_key": audited["cache_key"],
            "sources": request_sources[key],
            "chunks": audited["chunks"],
        })
    return {
        "schema": WINDOW_PACKET_PROMOTION_SCHEMA,
        "state": WINDOW_PACKET_PROMOTION_STATE,
        "inventory_file_sha256": inventory_file_sha256,
        "cache_audit_file_sha256": cache_audit_file_sha256,
        "provenance_file_sha256": provenance_file_sha256,
        "inventory_sha256": digest(inventory),
        "encoder_identity": provenance["encoder_identity"],
        "legacy_cache_dir": audit["legacy_cache_dir"],
        "feature_root": str(Path(feature_root).resolve()),
        "request_count": len(bindings),
        "unique_packet_count": len(packets),
        "bindings": bindings,
    }


def prepare_window_feature_packets(
    path: Path, *, inventory_path: Path, inventory_sha256: str,
    cache_audit_path: Path, cache_audit_sha256: str, provenance_path: Path,
    provenance_sha256: str, data_root: Path, feature_root: Path, workers: int = 8,
) -> dict[str, object]:
    """Persist exact-window formal packets and their source-bound lookup."""

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 20:
        raise PreparationError("window packet workers must be an integer in [1, 20]")
    artifact_path = Path(path)
    if artifact_path.exists():
        _, artifact_sha256, _ = hash_stable_file(
            artifact_path, "window packet promotion"
        )
        prepared = load_prepared_window_feature_packets(
            artifact_path, artifact_sha256, data_root
        )
        if (
            prepared.inventory_file_sha256 != inventory_sha256
            or prepared.cache_audit_file_sha256 != cache_audit_sha256
            or prepared.provenance_file_sha256 != provenance_sha256
            or Path(prepared.feature_root) != Path(feature_root).resolve()
        ):
            raise PreparationError("window packet promotion artifact identity mismatch")
        return {
            "path": str(artifact_path),
            "sha256": artifact_sha256,
            "cache": "warm",
            "contact_class": "model-free",
        }
    inventory, audit, provenance = _validated_chain(
        inventory_path=inventory_path, inventory_sha256=inventory_sha256,
        cache_audit_path=cache_audit_path, cache_audit_sha256=cache_audit_sha256,
        provenance_path=provenance_path, provenance_sha256=provenance_sha256,
        data_root=data_root,
    )
    inputs = {
        "inventory_file_sha256": inventory_sha256,
        "cache_audit_file_sha256": cache_audit_sha256,
        "provenance_file_sha256": provenance_sha256,
        "inventory_sha256": digest(inventory),
        "encoder_identity": provenance["encoder_identity"],
        "legacy_cache_dir": audit["legacy_cache_dir"],
        "feature_root": str(Path(feature_root).resolve()),
    }

    def produce() -> Mapping[str, object]:
        output = _build_output(
            inventory=inventory, audit=audit, provenance=provenance,
            inventory_file_sha256=inventory_sha256,
            cache_audit_file_sha256=cache_audit_sha256,
            provenance_file_sha256=provenance_sha256, data_root=data_root,
            feature_root=feature_root, workers=workers,
        )
        final_inventory, _, _ = _validated_chain(
            inventory_path=inventory_path, inventory_sha256=inventory_sha256,
            cache_audit_path=cache_audit_path, cache_audit_sha256=cache_audit_sha256,
            provenance_path=provenance_path, provenance_sha256=provenance_sha256,
            data_root=data_root,
        )
        if digest(final_inventory) != digest(inventory):
            raise PreparationError("window packet source inventory changed during promotion")
        return output

    return prepare_artifact(
        path, kind=WINDOW_PACKET_PROMOTION_KIND, inputs=inputs, producer=produce
    )


def load_prepared_window_feature_packets(
    path: Path, expected_sha256: str, data_root: Path
) -> PreparedWindowFeaturePackets:
    """Load a pinned promotion artifact and recheck recorded sources and packets."""

    output = _load_prepared_output(
        path, expected_sha256=expected_sha256,
        kind=WINDOW_PACKET_PROMOTION_KIND, label="window packet promotion",
    )
    if (
        output.get("schema") != WINDOW_PACKET_PROMOTION_SCHEMA
        or output.get("state") != WINDOW_PACKET_PROMOTION_STATE
    ):
        raise PreparationError("window packet promotion is incomplete")
    entries = output.get("bindings")
    if not isinstance(entries, list) or not entries:
        raise PreparationError("window packet promotion bindings are missing")
    root = Path(data_root).resolve(strict=True)
    bindings = []
    seen = set()
    measured_files: dict[Path, tuple[int, str]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise PreparationError("window packet binding is invalid")
        request_key = entry.get("request_key")
        if not isinstance(request_key, str) or request_key in seen:
            raise PreparationError("window packet request binding is duplicate or invalid")
        seen.add(request_key)
        sources = entry.get("sources")
        chunks = entry.get("chunks")
        if not isinstance(sources, list) or not sources or not isinstance(chunks, list):
            raise PreparationError("window packet source or chunk lineage is missing")
        frozen_sources = []
        for source_entry in sources:
            if (
                not isinstance(source_entry, Mapping)
                or set(source_entry) != {"batch", "source_provenance"}
                or not isinstance(source_entry["batch"], str)
                or not isinstance(source_entry["source_provenance"], Mapping)
            ):
                raise PreparationError("window packet source lineage is invalid")
            source = dict(source_entry["source_provenance"])
            if _source_key(request_key, source) != entry.get("source_key"):
                raise PreparationError("window packet source key does not match source")
            for field, label in (
                ("media_relpath", "window packet source"),
                ("parent_media_relpath", "window packet parent"),
            ):
                relative = _normalized_relative_path(source[field], label)
                file_path = _resolve_confined(root, relative, root, label, strict=True)
                if file_path not in measured_files:
                    size, sha256, _ = hash_stable_file(file_path, label)
                    measured_files[file_path] = (size, sha256)
                size, sha256 = measured_files[file_path]
                expected_size = source["bytes" if field == "media_relpath" else "parent_bytes"]
                expected_sha = source["sha256" if field == "media_relpath" else "parent_sha256"]
                if size != expected_size or sha256 != expected_sha:
                    raise PreparationError(f"{label} differs from promotion lineage")
            frozen_sources.append(MappingProxyType({
                "batch": source_entry["batch"],
                "source_provenance": MappingProxyType(source),
            }))
        audio_sha256 = _sha(entry.get("audio_sha256"), "window packet audio")
        packet_id = entry.get("packet_id")
        cache_key = entry.get("cache_key")
        if packet_id != _packet_id(audio_sha256):
            raise PreparationError("window packet id is not canonical")
        if not isinstance(cache_key, str) or not cache_key.isdecimal():
            raise PreparationError("window packet cache key is invalid")
        binding = WindowPacketBinding(
            request_key=request_key,
            source_key=str(entry["source_key"]),
            packet_id=packet_id,
            packet_sha256=_sha(entry.get("packet_sha256"), "window packet hash"),
            audio_sha256=audio_sha256,
            cache_key=cache_key,
            sources=tuple(frozen_sources),
            chunks=tuple(MappingProxyType(dict(chunk)) for chunk in chunks),
        )
        bindings.append(binding)
    if output.get("request_count") != len(bindings):
        raise PreparationError("window packet request count does not match")
    unique = {binding.packet_id for binding in bindings}
    feature_root = Path(str(output["feature_root"]))
    for binding in bindings:
        packet = load_speech_feature_packet(feature_root, binding.packet_id)
        if (
            packet.packet_sha256 != binding.packet_sha256
            or packet.audio_sha256 != binding.audio_sha256
            or packet.decoder_gguf_sha256
            != output["encoder_identity"]["decoder_gguf_sha256"]
            or packet.mmproj_sha256 != output["encoder_identity"]["mmproj_sha256"]
        ):
            raise PreparationError("formal packet descriptor differs from promotion lineage")
    if output.get("unique_packet_count") != len(unique):
        raise PreparationError("window packet unique count does not match")
    by_key = MappingProxyType({binding.request_key: binding for binding in bindings})
    return PreparedWindowFeaturePackets(
        inventory_file_sha256=_sha(output.get("inventory_file_sha256"), "inventory file hash"),
        cache_audit_file_sha256=_sha(output.get("cache_audit_file_sha256"), "cache audit file hash"),
        provenance_file_sha256=_sha(output.get("provenance_file_sha256"), "provenance file hash"),
        inventory_sha256=_sha(output.get("inventory_sha256"), "inventory hash"),
        encoder_identity=MappingProxyType(dict(output["encoder_identity"])),
        legacy_cache_dir=str(output["legacy_cache_dir"]),
        feature_root=str(output["feature_root"]),
        request_count=len(bindings), unique_packet_count=len(unique),
        bindings=tuple(bindings), by_request_key=by_key,
    )
