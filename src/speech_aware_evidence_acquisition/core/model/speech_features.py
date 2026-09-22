"""Auditable, path-confined speech-feature packets for decoder-only inference.

The packet is the durable hand-off between the legacy preprocessing process
(decoder + mmproj, allowed to populate/reuse the existing ext4 feature cache)
and the formal inference process (decoder only). Runtime requests carry only a
packet id, packet hash, and semantic role; they never carry caller-supplied
floating-point arrays or an arbitrary filesystem path.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Mapping, Sequence

from . import FrozenCoreError
from .paths import _normalized_relative_path, _resolve_confined

SPEECH_FEATURE_PACKET_SCHEMA = "saea-speech-feature-packet-v1"
SPEECH_PACKET_PROMOTION_RECEIPT_SCHEMA = (
    "saea-speech-packet-promotion-receipt-v1"
)
PACKET_MANIFEST_NAME = "packet.json"
# Item E40. A promotion pass either encoded its own cache entries first or
# promoted an already-warm cache with zero contacts; the receipt says which. A
# receipt written before item E40 carries no "mode" key and is read as the
# historical ENCODE + PROMOTE pass.
PROMOTION_MODE_ENCODE_AND_PROMOTE = "encode-and-promote"
PROMOTION_MODE_PROMOTE_ONLY = "promote-only"
PROMOTION_MODES = frozenset(
    {PROMOTION_MODE_ENCODE_AND_PROMOTE, PROMOTION_MODE_PROMOTE_ONLY}
)
PROMOTION_RECEIPT_OPTIONAL_KEYS = frozenset(
    {"mode", "encode_contacts", "shared_packets", "shared_packet_count"}
)
_SHA256_LENGTH = 64
_LEGACY_FEAT_HEADER = struct.Struct("<QQ")
_MAX_PACKET_I32 = (1 << 31) - 1


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_sha256(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise FrozenCoreError(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def _canonical(document: Mapping[str, object]) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _packet_dir(feature_root: Path, packet_id: object, *, strict: bool) -> tuple[str, Path]:
    normalized = _normalized_relative_path(packet_id, "speech feature packet_id")
    path = _resolve_confined(
        Path(feature_root),
        normalized,
        Path(feature_root),
        "speech feature packet_id",
        strict=strict,
    )
    return normalized, path


@dataclass(frozen=True)
class SpeechFeatureChunkData:
    """One preprocessing-produced chunk before it is materialized."""

    n_tokens: int
    n_pos: int
    n_embd: int
    feature_bytes: bytes
    position_bytes: bytes
    dtype: str = "float32"

    def validate(self) -> "SpeechFeatureChunkData":
        for field, value in (
            ("n_tokens", self.n_tokens),
            ("n_pos", self.n_pos),
            ("n_embd", self.n_embd),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise FrozenCoreError(f"speech feature chunk {field} must be positive")
        if self.dtype != "float32":
            raise FrozenCoreError("SpeechFeaturePacketV1 initially permits float32 only")
        if not isinstance(self.feature_bytes, bytes):
            raise FrozenCoreError("speech feature chunk feature_bytes must be bytes")
        if len(self.feature_bytes) != self.n_tokens * self.n_embd * 4:
            raise FrozenCoreError(
                "speech feature chunk feature byte length disagrees with "
                "n_tokens * n_embd * sizeof(float32)"
            )
        if not isinstance(self.position_bytes, bytes):
            raise FrozenCoreError("speech feature chunk position_bytes must be bytes")
        if len(self.position_bytes) != self.n_tokens * 4 * 4:
            raise FrozenCoreError(
                "speech feature chunk position byte length disagrees with "
                "n_tokens * four M-RoPE axes * sizeof(int32)"
            )
        return self


@dataclass(frozen=True)
class LegacyCachedChunkDescriptor:
    """Auditable metadata for one validated legacy feature-cache file."""

    ordinal: int
    relative_filename: str
    file_sha256: str
    file_size: int
    n_tokens: int
    n_embd: int


@dataclass(frozen=True)
class LegacyFeatureCacheInspection:
    """Validated, model-free identity and chunk metadata for a warm cache."""

    audio_sha256: str
    cache_key: str
    chunks: tuple[LegacyCachedChunkDescriptor, ...]


@dataclass(frozen=True)
class SpeechFeatureChunkV1:
    ordinal: int
    n_tokens: int
    n_pos: int
    n_embd: int
    dtype: str
    feature_relpath: str
    feature_sha256: str
    position_relpath: str
    position_sha256: str

    def as_json(self) -> dict[str, object]:
        return {
            "ordinal": self.ordinal,
            "n_tokens": self.n_tokens,
            "n_pos": self.n_pos,
            "n_embd": self.n_embd,
            "dtype": self.dtype,
            "feature_relpath": self.feature_relpath,
            "feature_sha256": self.feature_sha256,
            "position_relpath": self.position_relpath,
            "position_sha256": self.position_sha256,
        }


@dataclass(frozen=True)
class SpeechFeaturePacketV1:
    packet_id: str
    audio_sha256: str
    encoder_receipt_sha256: str
    decoder_gguf_sha256: str
    mmproj_sha256: str
    position_mode: str
    causal_attention: bool
    chunks: tuple[SpeechFeatureChunkV1, ...]
    packet_sha256: str
    schema: str = SPEECH_FEATURE_PACKET_SCHEMA

    def unsigned_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "packet_id": self.packet_id,
            "audio_sha256": self.audio_sha256,
            "encoder_receipt_sha256": self.encoder_receipt_sha256,
            "decoder_gguf_sha256": self.decoder_gguf_sha256,
            "mmproj_sha256": self.mmproj_sha256,
            "position_mode": self.position_mode,
            "causal_attention": self.causal_attention,
            "chunks": [chunk.as_json() for chunk in self.chunks],
        }

    def as_json(self) -> dict[str, object]:
        return {**self.unsigned_json(), "packet_sha256": self.packet_sha256}

    def validate(self, feature_root: Path) -> "SpeechFeaturePacketV1":
        if self.schema != SPEECH_FEATURE_PACKET_SCHEMA:
            raise FrozenCoreError(
                f"speech feature packet schema must be {SPEECH_FEATURE_PACKET_SCHEMA!r}"
            )
        packet_id, directory = _packet_dir(feature_root, self.packet_id, strict=True)
        if packet_id != self.packet_id:
            raise FrozenCoreError("speech feature packet_id is not normalized")
        for field, value in (
            ("audio_sha256", self.audio_sha256),
            ("encoder_receipt_sha256", self.encoder_receipt_sha256),
            ("decoder_gguf_sha256", self.decoder_gguf_sha256),
            ("mmproj_sha256", self.mmproj_sha256),
            ("packet_sha256", self.packet_sha256),
        ):
            _require_sha256(value, field)
        if self.position_mode != "mrope_1d":
            raise FrozenCoreError("speech feature packet position_mode must be 'mrope_1d'")
        if not isinstance(self.causal_attention, bool):
            raise FrozenCoreError("speech feature packet causal_attention must be boolean")
        if not self.chunks:
            raise FrozenCoreError("speech feature packet must contain at least one chunk")
        dimensions: set[int] = set()
        for expected_ordinal, chunk in enumerate(self.chunks):
            if chunk.ordinal != expected_ordinal:
                raise FrozenCoreError("speech feature chunk ordinals must be contiguous from zero")
            for field, value in (
                ("n_tokens", chunk.n_tokens),
                ("n_pos", chunk.n_pos),
                ("n_embd", chunk.n_embd),
            ):
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    raise FrozenCoreError(
                        f"speech feature chunk {field} must be a positive integer"
                    )
            if chunk.dtype != "float32":
                raise FrozenCoreError("SpeechFeaturePacketV1 initially permits float32 only")
            dimensions.add(chunk.n_embd)
            feature_relpath = _normalized_relative_path(
                chunk.feature_relpath, f"speech feature chunk {chunk.ordinal} feature_relpath"
            )
            position_relpath = _normalized_relative_path(
                chunk.position_relpath, f"speech feature chunk {chunk.ordinal} position_relpath"
            )
            feature_path = _resolve_confined(
                directory,
                feature_relpath,
                directory,
                "speech feature bytes",
                strict=True,
            )
            position_path = _resolve_confined(
                directory,
                position_relpath,
                directory,
                "speech feature positions",
                strict=True,
            )
            try:
                feature_bytes = feature_path.read_bytes()
                position_bytes = position_path.read_bytes()
            except OSError as error:
                raise FrozenCoreError(
                    f"cannot read speech feature chunk {chunk.ordinal}: {error}"
                ) from error
            if len(feature_bytes) != chunk.n_tokens * chunk.n_embd * 4:
                raise FrozenCoreError(
                    f"speech feature bytes length mismatch for chunk {chunk.ordinal}"
                )
            if len(position_bytes) != chunk.n_tokens * 4 * 4:
                raise FrozenCoreError(
                    f"speech feature position bytes length mismatch for chunk {chunk.ordinal}"
                )
            if _sha256(feature_bytes) != _require_sha256(
                chunk.feature_sha256, "chunk feature_sha256"
            ):
                raise FrozenCoreError(
                    f"speech feature bytes SHA-256 mismatch for chunk {chunk.ordinal}"
                )
            if _sha256(position_bytes) != _require_sha256(
                chunk.position_sha256, "chunk position_sha256"
            ):
                raise FrozenCoreError(
                    f"speech feature position bytes SHA-256 mismatch for chunk {chunk.ordinal}"
                )
        if len(dimensions) != 1:
            raise FrozenCoreError("all speech feature chunks must use the same n_embd")
        if _sha256(_canonical(self.unsigned_json())) != self.packet_sha256:
            raise FrozenCoreError("speech feature packet SHA-256 mismatch")
        return self


@dataclass(frozen=True)
class SharedSpeechFeaturePacketRecord:
    """One already-materialized packet accepted under a different encoder receipt.

    Item E40. The packet bytes are the evidence authority. When an existing
    packet disagrees with the expected identity in exactly
    ``encoder_receipt_sha256`` -- the hash of the RECEIPT DOCUMENT describing
    the encoder, not of anything the encoder produced -- and the chunk count
    and every chunk hash still agree, the packet is shared between the two
    provenances. The difference is recorded here rather than refused (which
    would strand a byte-identical packet) or overwritten (which would destroy
    the earlier promotion's evidence).
    """

    packet_id: str
    existing_encoder_receipt_sha256: str
    verified_against_encoder_receipt_sha256: str
    existing_packet_sha256: str
    chunk_count: int

    def as_json(self) -> dict[str, object]:
        return {
            "packet_id": self.packet_id,
            "existing_encoder_receipt_sha256": self.existing_encoder_receipt_sha256,
            "verified_against_encoder_receipt_sha256": (
                self.verified_against_encoder_receipt_sha256
            ),
            "existing_packet_sha256": self.existing_packet_sha256,
            "chunk_count": self.chunk_count,
        }


def _chunk_from_json(document: object) -> SpeechFeatureChunkV1:
    required = {
        "ordinal",
        "n_tokens",
        "n_pos",
        "n_embd",
        "dtype",
        "feature_relpath",
        "feature_sha256",
        "position_relpath",
        "position_sha256",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise FrozenCoreError(
            f"speech feature chunk must have exact keys {sorted(required)}"
        )
    return SpeechFeatureChunkV1(**document)  # type: ignore[arg-type]


def load_speech_feature_packet(
    feature_root: Path,
    packet_id: object,
    *,
    expected_sha256: object | None = None,
    expected_decoder_gguf_sha256: str | None = None,
    expected_n_embd: int | None = None,
) -> SpeechFeaturePacketV1:
    normalized, directory = _packet_dir(feature_root, packet_id, strict=True)
    manifest = directory / PACKET_MANIFEST_NAME
    try:
        document = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FrozenCoreError(f"cannot read speech feature packet {normalized!r}: {error}") from error
    required = {
        "schema",
        "packet_id",
        "audio_sha256",
        "encoder_receipt_sha256",
        "decoder_gguf_sha256",
        "mmproj_sha256",
        "position_mode",
        "causal_attention",
        "chunks",
        "packet_sha256",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise FrozenCoreError(
            f"speech feature packet manifest must have exact keys {sorted(required)}"
        )
    chunks = document["chunks"]
    if not isinstance(chunks, list):
        raise FrozenCoreError("speech feature packet chunks must be a list")
    packet = SpeechFeaturePacketV1(
        schema=document["schema"],
        packet_id=document["packet_id"],
        audio_sha256=document["audio_sha256"],
        encoder_receipt_sha256=document["encoder_receipt_sha256"],
        decoder_gguf_sha256=document["decoder_gguf_sha256"],
        mmproj_sha256=document["mmproj_sha256"],
        position_mode=document["position_mode"],
        causal_attention=document["causal_attention"],
        chunks=tuple(_chunk_from_json(chunk) for chunk in chunks),
        packet_sha256=document["packet_sha256"],
    ).validate(Path(feature_root))
    if packet.packet_id != normalized:
        raise FrozenCoreError("speech feature packet manifest packet_id disagrees with lookup id")
    if expected_sha256 is not None and packet.packet_sha256 != _require_sha256(
        expected_sha256, "expected speech packet sha256"
    ):
        raise FrozenCoreError("speech feature packet hash does not match the request")
    if (
        expected_decoder_gguf_sha256 is not None
        and packet.decoder_gguf_sha256 != expected_decoder_gguf_sha256
    ):
        raise FrozenCoreError("speech feature packet is bound to a different decoder GGUF")
    if expected_n_embd is not None and any(
        chunk.n_embd != expected_n_embd for chunk in packet.chunks
    ):
        raise FrozenCoreError("speech feature packet n_embd does not match the decoder")
    return packet


def load_speech_feature_packets(
    feature_root: Path,
    bindings: Sequence[Mapping[str, object]],
    *,
    workers: int = 8,
    expected_decoder_gguf_sha256: str | None = None,
    expected_n_embd: int | None = None,
) -> tuple[SpeechFeaturePacketV1, ...]:
    """Validate independent packets concurrently and return input order.

    This is the bounded preflight path for a frozen small-scale experiment.
    Each item is still fully validated by :func:`load_speech_feature_packet`;
    concurrency only overlaps independent manifest/chunk reads and never
    weakens packet hashes, decoder binding, dimensions, or path confinement.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise FrozenCoreError("speech packet validation workers must be an integer in [1, 64]")
    normalized: list[tuple[str, str]] = []
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or set(binding) != {"packet_id", "sha256"}:
            raise FrozenCoreError(
                f"speech packet binding {index} must carry exact packet_id/sha256"
            )
        packet_id = _normalized_relative_path(
            binding["packet_id"], f"speech packet binding {index} packet_id"
        )
        if packet_id in seen:
            raise FrozenCoreError(f"duplicate speech packet binding {packet_id!r}")
        seen.add(packet_id)
        normalized.append(
            (packet_id, _require_sha256(binding["sha256"], f"speech packet binding {index} sha256"))
        )
    if not normalized:
        return ()

    def load_one(binding: tuple[str, str]) -> SpeechFeaturePacketV1:
        packet_id, packet_sha256 = binding
        return load_speech_feature_packet(
            feature_root,
            packet_id,
            expected_sha256=packet_sha256,
            expected_decoder_gguf_sha256=expected_decoder_gguf_sha256,
            expected_n_embd=expected_n_embd,
        )

    worker_count = min(workers, len(normalized))
    if worker_count == 1:
        return tuple(load_one(binding) for binding in normalized)
    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="saea-speech-packet",
    ) as pool:
        return tuple(pool.map(load_one, normalized))


def load_speech_feature_packet_ids(
    feature_root: Path,
    packet_ids: Sequence[object],
    *,
    workers: int = 8,
    expected_decoder_gguf_sha256: str | None = None,
) -> tuple[SpeechFeaturePacketV1, ...]:
    """Discover fully validated packet hashes concurrently in input order.

    The generic driver uses this preflight before opening a model attempt: a
    committed label-free dataset view pins packet ids, while the packet
    manifests created after preprocessing supply their content hashes. The
    transport independently re-validates those hashes again on every send.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise FrozenCoreError("speech packet discovery workers must be an integer in [1, 64]")
    normalized: list[str] = []
    seen: set[str] = set()
    for index, packet_id in enumerate(packet_ids):
        value = _normalized_relative_path(packet_id, f"speech packet id {index}")
        if value in seen:
            raise FrozenCoreError(f"duplicate speech packet id {value!r}")
        seen.add(value)
        normalized.append(value)
    if not normalized:
        return ()

    def load_one(packet_id: str) -> SpeechFeaturePacketV1:
        return load_speech_feature_packet(
            feature_root,
            packet_id,
            expected_decoder_gguf_sha256=expected_decoder_gguf_sha256,
        )

    worker_count = min(workers, len(normalized))
    if worker_count == 1:
        return tuple(load_one(packet_id) for packet_id in normalized)
    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="saea-speech-discover",
    ) as pool:
        return tuple(pool.map(load_one, normalized))


def _validate_shared_packet_rows(
    document: Mapping[str, object], promoted_ids: set[str]
) -> None:
    """Validate the item E40 shared-packet ledger of a promotion receipt.

    A shared row records an already-materialized packet that this promotion
    accepted unchanged because its identity differed from the expected one in
    exactly ``encoder_receipt_sha256``. The row is provenance, never authority:
    the packet's own ``packet_sha256`` still appears in ``packets``, so
    re-verifying the receipt against the feature root is unchanged.
    """

    rows = document.get("shared_packets")
    declared = document.get("shared_packet_count")
    if rows is None and declared is None:
        return
    if not isinstance(rows, list):
        raise FrozenCoreError("speech packet promotion shared_packets must be a list")
    if (
        isinstance(declared, bool)
        or not isinstance(declared, int)
        or declared != len(rows)
    ):
        raise FrozenCoreError(
            "speech packet promotion shared_packet_count disagrees with shared_packets"
        )
    keys = {
        "packet_id",
        "existing_encoder_receipt_sha256",
        "verified_against_encoder_receipt_sha256",
        "existing_packet_sha256",
        "chunk_count",
    }
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != keys:
            raise FrozenCoreError(
                f"speech packet promotion shared item {index} must have exact "
                f"keys {sorted(keys)}"
            )
        packet_id = _normalized_relative_path(
            row["packet_id"], f"speech packet promotion shared item {index} packet_id"
        )
        if packet_id in seen:
            raise FrozenCoreError(
                f"duplicate speech packet promotion shared item {packet_id!r}"
            )
        seen.add(packet_id)
        if packet_id not in promoted_ids:
            raise FrozenCoreError(
                f"speech packet promotion shared item {packet_id!r} is not promoted"
            )
        for field in (
            "existing_encoder_receipt_sha256",
            "verified_against_encoder_receipt_sha256",
            "existing_packet_sha256",
        ):
            _require_sha256(
                row[field], f"speech packet promotion shared item {index} {field}"
            )
        if (
            row["existing_encoder_receipt_sha256"]
            == row["verified_against_encoder_receipt_sha256"]
        ):
            raise FrozenCoreError(
                f"speech packet promotion shared item {packet_id!r} records no "
                "encoder receipt difference"
            )
        count = row["chunk_count"]
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise FrozenCoreError(
                f"speech packet promotion shared item {index} chunk_count must "
                "be a positive integer"
            )


def load_speech_packet_promotion_receipt(
    receipt_path: Path,
    *,
    expected_sha256: object,
    expected_feature_root: Path,
    expected_dataset_runtime_view_sha256: object,
) -> Mapping[str, object]:
    """Load the protocol-pinned hand-off from preprocessing to inference.

    The receipt is written only after the receipt-bound preprocessing server
    has stopped and every legacy featcache entry has been promoted. Formal
    inference pins the receipt's file bytes in its composed config, then
    independently compares every packet identity against the packet manifests.
    """

    path = Path(receipt_path)
    if not path.is_absolute():
        raise FrozenCoreError("speech packet promotion receipt path must be absolute")
    try:
        raw = path.read_bytes()
        document = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FrozenCoreError(
            f"cannot read speech packet promotion receipt {path}: {error}"
        ) from error
    if _sha256(raw) != _require_sha256(
        expected_sha256, "speech packet promotion receipt sha256"
    ):
        raise FrozenCoreError("speech packet promotion receipt SHA-256 mismatch")
    required = {
        "schema",
        "study",
        "dataset_runtime_view_sha256",
        "preprocess_session_id",
        "preprocess_session_receipt_sha256",
        "preprocess_stop_receipt_sha256",
        "runtime_receipt_sha256",
        "legacy_cache_dir",
        "feature_root",
        "count",
        "packets",
    }
    if (
        not isinstance(document, Mapping)
        or not required.issubset(document)
        or set(document) - required - PROMOTION_RECEIPT_OPTIONAL_KEYS
    ):
        raise FrozenCoreError(
            f"speech packet promotion receipt must have exact keys {sorted(required)}"
            f" plus at most {sorted(PROMOTION_RECEIPT_OPTIONAL_KEYS)}"
        )
    if (
        document["schema"] != SPEECH_PACKET_PROMOTION_RECEIPT_SCHEMA
        or document["study"] != "speech-aware-evidence-acquisition"
    ):
        raise FrozenCoreError("speech packet promotion receipt identity is invalid")
    mode = document.get("mode", PROMOTION_MODE_ENCODE_AND_PROMOTE)
    if mode not in PROMOTION_MODES:
        raise FrozenCoreError(
            f"speech packet promotion receipt mode must be one of {sorted(PROMOTION_MODES)}"
        )
    if (
        not isinstance(document["preprocess_session_id"], str)
        or not document["preprocess_session_id"]
    ):
        raise FrozenCoreError("preprocess_session_id must be a non-empty string")
    session_fields = (
        "preprocess_session_receipt_sha256",
        "preprocess_stop_receipt_sha256",
    )
    if mode == PROMOTION_MODE_PROMOTE_ONLY:
        # Item E40. A promote-only pass opens no preprocessing server, so there
        # is no session or stop receipt to hash: both fields are null rather
        # than a fabricated digest. Encoder identity still comes from
        # ``runtime_receipt_sha256``, and every packet identity is re-verified
        # against the packet manifests independently of this document.
        if any(document[field] is not None for field in session_fields):
            raise FrozenCoreError(
                "a promote-only speech packet promotion receipt must carry null "
                "session and stop receipt hashes"
            )
    else:
        for field in session_fields:
            _require_sha256(document[field], field)
    for field in ("dataset_runtime_view_sha256", "runtime_receipt_sha256"):
        _require_sha256(document[field], field)
    contacts = document.get("encode_contacts")
    if contacts is not None and (
        isinstance(contacts, bool) or not isinstance(contacts, int) or contacts < 0
    ):
        raise FrozenCoreError(
            "speech packet promotion encode_contacts must be a non-negative integer"
        )
    if mode == PROMOTION_MODE_PROMOTE_ONLY and contacts not in (None, 0):
        raise FrozenCoreError(
            "a promote-only speech packet promotion receipt must declare zero contacts"
        )
    if document["dataset_runtime_view_sha256"] != _require_sha256(
        expected_dataset_runtime_view_sha256,
        "expected dataset runtime view sha256",
    ):
        raise FrozenCoreError(
            "speech packet promotion receipt names a different dataset runtime view"
        )
    feature_root = Path(str(document["feature_root"]))
    legacy_cache_dir = Path(str(document["legacy_cache_dir"]))
    if (
        not isinstance(document["feature_root"], str)
        or not feature_root.is_absolute()
        or feature_root != Path(expected_feature_root)
        or not isinstance(document["legacy_cache_dir"], str)
        or not legacy_cache_dir.is_absolute()
        or legacy_cache_dir == feature_root
    ):
        raise FrozenCoreError("speech packet promotion cache roots are invalid")
    count = document["count"]
    packets = document["packets"]
    if (
        isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        or not isinstance(packets, list)
        or len(packets) != count
    ):
        raise FrozenCoreError("speech packet promotion count disagrees with packets")
    packet_keys = {
        "packet_id",
        "packet_sha256",
        "audio_sha256",
        "decoder_gguf_sha256",
        "mmproj_sha256",
    }
    seen: set[str] = set()
    for index, packet in enumerate(packets):
        if not isinstance(packet, Mapping) or set(packet) != packet_keys:
            raise FrozenCoreError(
                f"speech packet promotion item {index} must have exact keys "
                f"{sorted(packet_keys)}"
            )
        packet_id = _normalized_relative_path(
            packet["packet_id"], f"speech packet promotion item {index} packet_id"
        )
        if packet_id in seen:
            raise FrozenCoreError(
                f"duplicate speech packet promotion item {packet_id!r}"
            )
        seen.add(packet_id)
        for field in (
            "packet_sha256",
            "audio_sha256",
            "decoder_gguf_sha256",
            "mmproj_sha256",
        ):
            _require_sha256(packet[field], f"speech packet promotion item {index} {field}")
    _validate_shared_packet_rows(document, seen)
    return document


def materialize_speech_feature_packet(
    *,
    feature_root: Path,
    packet_id: str,
    audio_sha256: str,
    encoder_receipt_sha256: str,
    decoder_gguf_sha256: str,
    mmproj_sha256: str,
    position_mode: str,
    causal_attention: bool,
    chunks: Sequence[SpeechFeatureChunkData],
    on_shared: Callable[[SharedSpeechFeaturePacketRecord], None] | None = None,
) -> SpeechFeaturePacketV1:
    """Atomically materialize one packet using the fixed packet layout.

    The caller is the preprocessing stage. Existing materializations are
    accepted when their fully re-verified packet identity is identical, and --
    item E40 -- when it differs in exactly ``encoder_receipt_sha256`` while the
    chunk count and every chunk hash still agree: that is a provenance-only
    difference over byte-identical evidence, so the packet is SHARED between
    the two promotions. It is reported through ``on_shared`` (never silently),
    not one byte of the feature root is written, and any other difference keeps
    the historical refusal. A conflicting packet id is never overwritten.
    """

    feature_root = Path(feature_root)
    feature_root.mkdir(parents=True, exist_ok=True)
    normalized = _normalized_relative_path(packet_id, "speech feature packet_id")
    directory = feature_root / normalized
    if directory.exists():
        existing = load_speech_feature_packet(feature_root, normalized)
        expected_identity = {
            "audio_sha256": audio_sha256,
            "encoder_receipt_sha256": encoder_receipt_sha256,
            "decoder_gguf_sha256": decoder_gguf_sha256,
            "mmproj_sha256": mmproj_sha256,
            "position_mode": position_mode,
            "causal_attention": causal_attention,
        }
        actual_identity = {
            field: getattr(existing, field) for field in expected_identity
        }
        differing = {
            field
            for field, value in expected_identity.items()
            if actual_identity[field] != value
        }
        # Item E40: ONLY the encoder receipt document hash may differ, and only
        # once the chunk comparison below has proved the bytes identical. Every
        # other identity difference keeps the historical refusal unchanged.
        if differing - {"encoder_receipt_sha256"}:
            raise FrozenCoreError(
                "existing speech feature packet id is bound to different source/model metadata"
            )
        expected_chunks = tuple(chunk.validate() for chunk in chunks)
        if len(expected_chunks) != len(existing.chunks):
            raise FrozenCoreError(
                "existing speech feature packet id has a different chunk count"
            )
        for expected, recorded in zip(expected_chunks, existing.chunks, strict=True):
            if (
                expected.n_tokens,
                expected.n_pos,
                expected.n_embd,
                expected.dtype,
                _sha256(expected.feature_bytes),
                _sha256(expected.position_bytes),
            ) != (
                recorded.n_tokens,
                recorded.n_pos,
                recorded.n_embd,
                recorded.dtype,
                recorded.feature_sha256,
                recorded.position_sha256,
            ):
                raise FrozenCoreError(
                    "existing speech feature packet id has different chunk bytes or shape"
                )
        if differing:
            shared = SharedSpeechFeaturePacketRecord(
                packet_id=existing.packet_id,
                existing_encoder_receipt_sha256=existing.encoder_receipt_sha256,
                verified_against_encoder_receipt_sha256=_require_sha256(
                    encoder_receipt_sha256, "encoder_receipt_sha256"
                ),
                existing_packet_sha256=existing.packet_sha256,
                chunk_count=len(existing.chunks),
            )
            if on_shared is not None:
                on_shared(shared)
        return existing
    validated = tuple(chunk.validate() for chunk in chunks)
    if not validated:
        raise FrozenCoreError("speech feature packet must contain at least one chunk")
    tmp = directory.with_name(f"{directory.name}.tmp-{os.getpid()}")
    if tmp.exists():
        raise FrozenCoreError(f"speech feature packet staging path already exists: {tmp}")
    (tmp / "chunks").mkdir(parents=True)
    (tmp / "positions").mkdir()
    records: list[SpeechFeatureChunkV1] = []
    try:
        for ordinal, chunk in enumerate(validated):
            feature_relpath = f"chunks/{ordinal:04d}.f32"
            position_relpath = f"positions/{ordinal:04d}.i32"
            (tmp / feature_relpath).write_bytes(chunk.feature_bytes)
            (tmp / position_relpath).write_bytes(chunk.position_bytes)
            records.append(
                SpeechFeatureChunkV1(
                    ordinal=ordinal,
                    n_tokens=chunk.n_tokens,
                    n_pos=chunk.n_pos,
                    n_embd=chunk.n_embd,
                    dtype=chunk.dtype,
                    feature_relpath=feature_relpath,
                    feature_sha256=_sha256(chunk.feature_bytes),
                    position_relpath=position_relpath,
                    position_sha256=_sha256(chunk.position_bytes),
                )
            )
        unsigned = {
            "schema": SPEECH_FEATURE_PACKET_SCHEMA,
            "packet_id": normalized,
            "audio_sha256": _require_sha256(audio_sha256, "audio_sha256"),
            "encoder_receipt_sha256": _require_sha256(
                encoder_receipt_sha256, "encoder_receipt_sha256"
            ),
            "decoder_gguf_sha256": _require_sha256(
                decoder_gguf_sha256, "decoder_gguf_sha256"
            ),
            "mmproj_sha256": _require_sha256(mmproj_sha256, "mmproj_sha256"),
            "position_mode": position_mode,
            "causal_attention": causal_attention,
            "chunks": [record.as_json() for record in records],
        }
        document = {**unsigned, "packet_sha256": _sha256(_canonical(unsigned))}
        (tmp / PACKET_MANIFEST_NAME).write_text(
            json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
            newline="\n",
        )
        directory.parent.mkdir(parents=True, exist_ok=True)
        os.replace(tmp, directory)
    except Exception:
        # Never recursively remove an unverified caller path. ``tmp`` is a
        # deterministic child created above under the confined feature root;
        # remove only files this function itself names, then empty dirs.
        for ordinal in range(len(validated)):
            for relpath in (
                f"chunks/{ordinal:04d}.f32",
                f"positions/{ordinal:04d}.i32",
            ):
                try:
                    (tmp / relpath).unlink()
                except OSError:
                    pass
        try:
            (tmp / PACKET_MANIFEST_NAME).unlink()
        except OSError:
            pass
        for child in (tmp / "chunks", tmp / "positions", tmp):
            try:
                child.rmdir()
            except OSError:
                pass
        raise
    return load_speech_feature_packet(feature_root, normalized)


def legacy_audio_feature_cache_key(audio_bytes: bytes) -> str:
    """Return the exact decimal FNV-1a id used by the existing llama.cpp cache.

    The legacy patch hashes the original encoded media bytes before audio
    decoding, stores the unsigned 64-bit value as decimal, and appends one
    media ordinal per encoder chunk. Keeping this calculation here lets the
    preprocessing boundary promote already-warm ext4 cache entries without
    re-encoding speech or guessing from filenames.
    """

    if not isinstance(audio_bytes, bytes) or not audio_bytes:
        raise FrozenCoreError("legacy feature-cache promotion requires non-empty audio bytes")
    value = 0xCBF29CE484222325
    for byte in audio_bytes:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return str(value)


def _validated_legacy_cached_chunks(
    *,
    audio_bytes: bytes,
    legacy_cache_dir: Path,
    expected_n_embd: int,
    strict_filenames: bool = False,
) -> tuple[tuple[SpeechFeatureChunkData, ...], tuple[LegacyCachedChunkDescriptor, ...]]:
    if (
        isinstance(expected_n_embd, bool)
        or not isinstance(expected_n_embd, int)
        or expected_n_embd <= 0
    ):
        raise FrozenCoreError("expected decoder dimension must be a positive integer")
    cache_dir = Path(legacy_cache_dir)
    if not cache_dir.is_dir():
        raise FrozenCoreError(f"legacy feature-cache directory is unavailable: {cache_dir}")
    key = legacy_audio_feature_cache_key(audio_bytes)
    candidates: dict[int, Path] = {}
    for path in cache_dir.glob(f"{key}_o*.feat"):
        suffix = path.name[len(key) + 2 : -len(".feat")]
        if not suffix.isdecimal():
            continue
        ordinal = int(suffix)
        if strict_filenames and path.name != f"{key}_o{ordinal}.feat":
            raise FrozenCoreError(
                f"legacy feature-cache chunk filename {path.name!r} is not canonical"
            )
        if strict_filenames:
            try:
                path.resolve().relative_to(cache_dir.resolve())
            except ValueError as error:
                raise FrozenCoreError(
                    f"legacy feature-cache chunk {path.name!r} resolves outside the cache directory"
                ) from error
        if ordinal in candidates:
            raise FrozenCoreError(f"duplicate legacy feature-cache ordinal {ordinal}")
        candidates[ordinal] = path
    if 0 not in candidates:
        raise FrozenCoreError(
            f"legacy feature-cache entry {key!r} has no ordinal zero; "
            "online encoder fallback is forbidden"
        )
    if set(candidates) != set(range(len(candidates))):
        raise FrozenCoreError("legacy feature-cache chunk ordinals are not contiguous from zero")

    chunks: list[SpeechFeatureChunkData] = []
    descriptors: list[LegacyCachedChunkDescriptor] = []
    for ordinal in range(len(candidates)):
        try:
            raw = candidates[ordinal].read_bytes()
        except OSError as error:
            raise FrozenCoreError(
                f"cannot read legacy feature-cache chunk {ordinal}: {error}"
            ) from error
        if len(raw) < _LEGACY_FEAT_HEADER.size:
            raise FrozenCoreError(f"legacy feature-cache chunk {ordinal} is truncated")
        n_tokens_u64, n_embd_u64 = _LEGACY_FEAT_HEADER.unpack_from(raw)
        if not 0 < n_tokens_u64 <= _MAX_PACKET_I32:
            raise FrozenCoreError(
                f"legacy feature-cache chunk {ordinal} has invalid token count"
            )
        if n_embd_u64 != expected_n_embd:
            raise FrozenCoreError(
                f"legacy feature-cache chunk {ordinal} decoder dimension "
                f"{n_embd_u64} != expected {expected_n_embd}"
            )
        n_tokens = int(n_tokens_u64)
        feature_bytes = raw[_LEGACY_FEAT_HEADER.size :]
        if len(feature_bytes) != n_tokens * expected_n_embd * 4:
            raise FrozenCoreError(
                f"legacy feature-cache chunk {ordinal} byte length disagrees with its header"
            )
        relative_positions = tuple(range(n_tokens)) * 4
        position_bytes = struct.pack(f"<{len(relative_positions)}i", *relative_positions)
        descriptors.append(
            LegacyCachedChunkDescriptor(
                ordinal=ordinal,
                relative_filename=candidates[ordinal].name,
                file_sha256=_sha256(raw),
                file_size=len(raw),
                n_tokens=n_tokens,
                n_embd=expected_n_embd,
            )
        )
        chunks.append(
            SpeechFeatureChunkData(
                n_tokens=n_tokens,
                n_pos=n_tokens,
                n_embd=expected_n_embd,
                feature_bytes=feature_bytes,
                position_bytes=position_bytes,
            ).validate()
        )
    return tuple(chunks), tuple(descriptors)


def _legacy_cached_chunks(
    *, audio_bytes: bytes, legacy_cache_dir: Path, expected_n_embd: int
) -> tuple[SpeechFeatureChunkData, ...]:
    """Validate and decode legacy chunks for the existing promotion path."""

    chunks, _ = _validated_legacy_cached_chunks(
        audio_bytes=audio_bytes,
        legacy_cache_dir=legacy_cache_dir,
        expected_n_embd=expected_n_embd,
    )
    return chunks


def inspect_legacy_cached_speech_feature_cache(
    *,
    audio_path: Path,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> LegacyFeatureCacheInspection:
    """Inspect a warm legacy cache without model calls, encoding, or writes.

    The returned identity is limited to the supplied audio bytes, the legacy
    FNV cache key, and validated chunk files. It carries no model or cache
    build identity; callers must bind those through an external receipt.
    """

    try:
        audio_bytes = Path(audio_path).read_bytes()
    except OSError as error:
        raise FrozenCoreError(
            f"cannot read governed speech media {audio_path}: {error}"
        ) from error
    _, descriptors = _validated_legacy_cached_chunks(
        audio_bytes=audio_bytes,
        legacy_cache_dir=Path(legacy_cache_dir),
        expected_n_embd=expected_n_embd,
        strict_filenames=True,
    )
    return LegacyFeatureCacheInspection(
        audio_sha256=_sha256(audio_bytes),
        cache_key=legacy_audio_feature_cache_key(audio_bytes),
        chunks=descriptors,
    )


def materialize_legacy_cached_speech_feature_packet(
    *,
    feature_root: Path,
    packet_id: str,
    audio_path: Path,
    legacy_cache_dir: Path,
    encoder_receipt_sha256: str,
    decoder_gguf_sha256: str,
    mmproj_sha256: str,
    expected_n_embd: int,
    causal_attention: bool,
    on_shared: Callable[[SharedSpeechFeaturePacketRecord], None] | None = None,
) -> SpeechFeaturePacketV1:
    """Promote an existing legacy ``.feat`` entry into an auditable packet.

    This is a preprocessing operation only. It never opens llama.cpp, never
    loads mmproj, and never creates a cache miss: absent or malformed legacy
    chunks fail closed so a formal materialization cannot silently perform
    online encoding.
    """

    audio_sha256, chunks = _prepare_legacy_cached_speech_feature_packet(
        audio_path=audio_path,
        legacy_cache_dir=legacy_cache_dir,
        expected_n_embd=expected_n_embd,
    )
    return materialize_speech_feature_packet(
        feature_root=feature_root,
        packet_id=packet_id,
        audio_sha256=audio_sha256,
        encoder_receipt_sha256=encoder_receipt_sha256,
        decoder_gguf_sha256=decoder_gguf_sha256,
        mmproj_sha256=mmproj_sha256,
        position_mode="mrope_1d",
        causal_attention=causal_attention,
        chunks=chunks,
        on_shared=on_shared,
    )


def _prepare_legacy_cached_speech_feature_packet(
    *,
    audio_path: Path,
    legacy_cache_dir: Path,
    expected_n_embd: int,
) -> tuple[str, tuple[SpeechFeatureChunkData, ...]]:
    """Read and validate one governed audio/cache pair without writing a packet."""

    try:
        audio_bytes = Path(audio_path).read_bytes()
    except OSError as error:
        raise FrozenCoreError(f"cannot read governed speech media {audio_path}: {error}") from error
    chunks = _legacy_cached_chunks(
        audio_bytes=audio_bytes,
        legacy_cache_dir=Path(legacy_cache_dir),
        expected_n_embd=expected_n_embd,
    )
    return _sha256(audio_bytes), chunks


def materialize_legacy_cached_speech_feature_packets(
    *,
    feature_root: Path,
    bindings: Sequence[Mapping[str, object]],
    legacy_cache_dir: Path,
    encoder_receipt_sha256: str,
    decoder_gguf_sha256: str,
    mmproj_sha256: str,
    expected_n_embd: int,
    causal_attention: bool,
    workers: int = 8,
    on_shared: Callable[[SharedSpeechFeaturePacketRecord], None] | None = None,
) -> tuple[SpeechFeaturePacketV1, ...]:
    """Promote independent warm-cache entries concurrently in input order.

    Each binding carries exactly ``packet_id`` and ``audio_path``. Binding and
    cache validation is completed for the whole batch before packet writing
    starts, so a missing or malformed cache entry cannot leave a partially
    promoted batch. Both phases run concurrently and preserve input order.

    Item E40: a binding whose packet already exists and differs from this
    promotion in exactly ``encoder_receipt_sha256``, with identical chunks, is
    accepted unchanged and reported through ``on_shared``. The callback is
    invoked AFTER the concurrent phase, once per shared packet, in input order,
    so a receipt writer never has to serialize worker threads itself.
    """

    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 64:
        raise FrozenCoreError("speech packet materialization workers must be an integer in [1, 64]")
    normalized: list[tuple[str, Path]] = []
    seen: set[str] = set()
    for index, binding in enumerate(bindings):
        if not isinstance(binding, Mapping) or set(binding) != {"packet_id", "audio_path"}:
            raise FrozenCoreError(
                f"legacy speech packet binding {index} must carry exact packet_id/audio_path"
            )
        packet_id = _normalized_relative_path(
            binding["packet_id"], f"legacy speech packet binding {index} packet_id"
        )
        if packet_id in seen:
            raise FrozenCoreError(f"duplicate speech packet binding {packet_id!r}")
        seen.add(packet_id)
        audio_path = binding["audio_path"]
        if not isinstance(audio_path, (str, os.PathLike)):
            raise FrozenCoreError(
                f"legacy speech packet binding {index} audio_path must be path-like"
            )
        normalized.append((packet_id, Path(audio_path)))
    if not normalized:
        return ()

    def prepare_one(
        binding: tuple[str, Path],
    ) -> tuple[str, str, tuple[SpeechFeatureChunkData, ...]]:
        packet_id, audio_path = binding
        audio_sha256, chunks = _prepare_legacy_cached_speech_feature_packet(
            audio_path=audio_path,
            legacy_cache_dir=legacy_cache_dir,
            expected_n_embd=expected_n_embd,
        )
        return packet_id, audio_sha256, chunks

    shared_records: dict[str, SharedSpeechFeaturePacketRecord] = {}
    shared_lock = Lock()

    def collect_shared(record: SharedSpeechFeaturePacketRecord) -> None:
        with shared_lock:
            shared_records[record.packet_id] = record

    def materialize_one(
        prepared: tuple[str, str, tuple[SpeechFeatureChunkData, ...]],
    ) -> SpeechFeaturePacketV1:
        packet_id, audio_sha256, chunks = prepared
        return materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=packet_id,
            audio_sha256=audio_sha256,
            encoder_receipt_sha256=encoder_receipt_sha256,
            decoder_gguf_sha256=decoder_gguf_sha256,
            mmproj_sha256=mmproj_sha256,
            position_mode="mrope_1d",
            causal_attention=causal_attention,
            chunks=chunks,
            on_shared=collect_shared,
        )

    def report_shared() -> None:
        if on_shared is None:
            return
        for packet_id, _ in normalized:
            record = shared_records.get(packet_id)
            if record is not None:
                on_shared(record)

    worker_count = min(workers, len(normalized))
    if worker_count == 1:
        prepared = tuple(prepare_one(binding) for binding in normalized)
        packets = tuple(materialize_one(item) for item in prepared)
        report_shared()
        return packets
    with ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="saea-speech-promote",
    ) as pool:
        prepared = tuple(pool.map(prepare_one, normalized))
        packets = tuple(pool.map(materialize_one, prepared))
    report_shared()
    return packets
