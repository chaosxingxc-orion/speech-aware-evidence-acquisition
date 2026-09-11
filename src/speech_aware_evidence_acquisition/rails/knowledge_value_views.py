"""Prepared TRAIN-knowledge views for frozen knowledge values.

The catalog is separate from KnowledgeSnapshot: it binds optional speech
packets to already-frozen values without changing the snapshot or its content
hash. role='key' is the legacy wire role for an additional speech packet. It
does not describe, replace, or modify retrieval embeddings.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from ..core.model import FrozenCoreError
from ..core.model.speech_features import load_speech_feature_packet
from .errors import RailsError
from .knowledge import KnowledgeSnapshot, TRAIN_PARTITION_ROLE, ValueBundle

KNOWLEDGE_VIEW_CATALOG_SCHEMA = "saea-train-knowledge-view-catalog-v1"
KnowledgeView = Literal["text", "speech", "paired"]

_SHA256 = re.compile(r"[0-9a-f]{64}")
_CATALOG_KEYS = {
    "schema",
    "snapshot_sha256",
    "source_split_identity_hash",
    "source_partition_role",
    "decoder_gguf_sha256",
    "mmproj_sha256",
    "episodes",
}
_EPISODE_KEYS = {
    "episode_id",
    "value_id",
    "source_sample_id",
    "audio_sha256",
    "packet_id",
    "packet_sha256",
    "encoder_receipt_sha256",
}


class KnowledgeViewError(RailsError):
    """A prepared knowledge view is malformed or disagrees with its sources."""


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeViewError(f"{field} must be a non-empty string")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise KnowledgeViewError(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def _read_catalog(path: Path, expected_sha256: object) -> Mapping[str, object]:
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise KnowledgeViewError(
            f"cannot read knowledge view catalog {path}: {error}"
        ) from error
    expected = _require_sha256(expected_sha256, field="expected manifest SHA-256")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise KnowledgeViewError("knowledge view catalog manifest SHA-256 mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise KnowledgeViewError(
            f"knowledge view catalog is not valid JSON: {error}"
        ) from error
    if not isinstance(document, Mapping) or set(document) != _CATALOG_KEYS:
        raise KnowledgeViewError(
            f"knowledge view catalog must have exact keys {sorted(_CATALOG_KEYS)}"
        )
    return document


@dataclass(frozen=True)
class KnowledgeEpisodeBinding:
    """One frozen TRAIN episode's value-to-speech binding."""

    episode_id: str
    value_id: str
    source_sample_id: str
    audio_sha256: str
    packet_id: str
    packet_sha256: str
    encoder_receipt_sha256: str

    def speech_block(self) -> dict[str, object]:
        return {
            "type": "input_speech_features",
            "speech_features": {
                "packet_id": self.packet_id,
                "sha256": self.packet_sha256,
                "role": "key",
            },
        }


@dataclass(frozen=True)
class PreparedKnowledgeViewCatalog:
    """Validated immutable catalog for text, speech, and paired knowledge views."""

    manifest_sha256: str
    snapshot_sha256: str
    source_split_identity_hash: str
    decoder_gguf_sha256: str
    mmproj_sha256: str
    episodes: tuple[KnowledgeEpisodeBinding, ...]

    def assemble(
        self,
        selected_value_ids: Sequence[str],
        *,
        view: KnowledgeView,
        snapshot: KnowledgeSnapshot,
    ) -> tuple[Mapping[str, object], ...]:
        """Delegate to the shared renderer with this prepared speech catalog."""

        return assemble_knowledge_values(
            snapshot, selected_value_ids, view=view, catalog=self
        )


@dataclass(frozen=True, init=False)
class KnowledgeValueRenderer:
    """One-time validated and indexed renderer for repeated agent requests."""

    snapshot_sha256: str
    source_split_identity_hash: str
    values_by_id: Mapping[str, ValueBundle]
    episodes_by_value: Mapping[str, KnowledgeEpisodeBinding]
    catalog: PreparedKnowledgeViewCatalog | None

    def __init__(
        self,
        snapshot: KnowledgeSnapshot,
        catalog: PreparedKnowledgeViewCatalog | None = None,
    ) -> None:
        snapshot.validate()
        snapshot_sha256 = snapshot.content_hash()
        if catalog is not None and (
            snapshot.source_partition_role != TRAIN_PARTITION_ROLE
            or snapshot_sha256 != catalog.snapshot_sha256
            or snapshot.source_split_identity_hash != catalog.source_split_identity_hash
        ):
            raise KnowledgeViewError(
                "knowledge view catalog snapshot identity mismatch"
            )
        object.__setattr__(self, "snapshot_sha256", snapshot_sha256)
        object.__setattr__(
            self, "source_split_identity_hash", snapshot.source_split_identity_hash
        )
        object.__setattr__(
            self,
            "values_by_id",
            MappingProxyType({value.value_id: value for value in snapshot.values}),
        )
        object.__setattr__(
            self,
            "episodes_by_value",
            MappingProxyType(
                {
                    episode.value_id: episode
                    for episode in (() if catalog is None else catalog.episodes)
                }
            ),
        )
        object.__setattr__(self, "catalog", catalog)

    def assemble(
        self,
        selected_value_ids: Sequence[str],
        *,
        view: KnowledgeView = "text",
    ) -> tuple[Mapping[str, object], ...]:
        """Render typed content blocks without revalidating the full snapshot."""

        if view not in {"text", "speech", "paired"}:
            raise KnowledgeViewError(
                "knowledge view must be 'text', 'speech', or 'paired'"
            )
        if isinstance(selected_value_ids, (str, bytes)) or not isinstance(
            selected_value_ids, Sequence
        ):
            raise KnowledgeViewError("selected value IDs must be a sequence")

        selected: list[ValueBundle] = []
        seen: set[str] = set()
        for index, value_id in enumerate(selected_value_ids):
            value_id = _require_text(value_id, field=f"selected value ID {index}")
            if value_id in seen:
                raise KnowledgeViewError("selected value IDs must be unique")
            seen.add(value_id)
            value = self.values_by_id.get(value_id)
            if value is None:
                raise KnowledgeViewError(
                    f"selected value {value_id!r} is outside the frozen snapshot"
                )
            selected.append(value)
        if not selected:
            return ()
        if view != "text" and self.catalog is None:
            raise KnowledgeViewError(
                f"{view} knowledge view requires a prepared catalog"
            )
        if view != "text":
            missing = [
                value.value_id
                for value in selected
                if value.value_id not in self.episodes_by_value
            ]
            if missing:
                raise KnowledgeViewError(
                    f"selected speech knowledge values are not prepared: {missing}"
                )

        blocks: list[Mapping[str, object]] = []
        for value in selected:
            if view in {"text", "paired"}:
                blocks.append(
                    {
                        "type": "text",
                        "text": value.content,
                        "evidence_id": value.value_id,
                        "source_uri": (
                            f"knowledge-snapshot://{self.snapshot_sha256}/{value.value_id}"
                        ),
                        "knowledge_role": "value",
                    }
                )
            if view in {"speech", "paired"}:
                blocks.append(self.episodes_by_value[value.value_id].speech_block())
        return tuple(blocks)


def assemble_knowledge_values(
    snapshot: KnowledgeSnapshot,
    selected_value_ids: Sequence[str],
    *,
    view: KnowledgeView = "text",
    catalog: PreparedKnowledgeViewCatalog | None = None,
) -> tuple[Mapping[str, object], ...]:
    """Compatibility renderer for standalone calls.

    Repeated request paths should construct KnowledgeValueRenderer once and reuse
    it so full snapshot validation, hashing, and indexing happen once.
    """

    return KnowledgeValueRenderer(snapshot, catalog).assemble(
        selected_value_ids, view=view
    )


def load_prepared_knowledge_view_catalog(
    manifest_path: Path,
    *,
    expected_sha256: object,
    feature_root: Path,
    snapshot: KnowledgeSnapshot,
    expected_decoder_gguf_sha256: object,
    expected_mmproj_sha256: object,
) -> PreparedKnowledgeViewCatalog:
    """Load and fully validate a source-, runtime-, and packet-bound catalog."""

    document = _read_catalog(Path(manifest_path), expected_sha256)
    if document["schema"] != KNOWLEDGE_VIEW_CATALOG_SCHEMA:
        raise KnowledgeViewError(
            f"knowledge view catalog schema must be {KNOWLEDGE_VIEW_CATALOG_SCHEMA!r}"
        )
    snapshot.validate()
    if snapshot.source_partition_role != TRAIN_PARTITION_ROLE:
        raise KnowledgeViewError("knowledge view snapshot must have TRAIN source role")
    if document["source_partition_role"] != TRAIN_PARTITION_ROLE:
        raise KnowledgeViewError("knowledge view catalog must have TRAIN source role")

    snapshot_sha256 = _require_sha256(
        document["snapshot_sha256"], field="catalog snapshot SHA-256"
    )
    if snapshot_sha256 != snapshot.content_hash():
        raise KnowledgeViewError("knowledge view catalog snapshot identity mismatch")
    split_hash = _require_sha256(
        document["source_split_identity_hash"], field="catalog split identity hash"
    )
    if split_hash != snapshot.source_split_identity_hash:
        raise KnowledgeViewError("knowledge view catalog split identity mismatch")
    decoder_sha = _require_sha256(
        document["decoder_gguf_sha256"], field="catalog decoder GGUF SHA-256"
    )
    if decoder_sha != _require_sha256(
        expected_decoder_gguf_sha256, field="expected decoder GGUF SHA-256"
    ):
        raise KnowledgeViewError("knowledge view catalog decoder identity mismatch")
    mmproj_sha = _require_sha256(
        document["mmproj_sha256"], field="catalog mmproj SHA-256"
    )
    if mmproj_sha != _require_sha256(
        expected_mmproj_sha256, field="expected mmproj SHA-256"
    ):
        raise KnowledgeViewError("knowledge view catalog mmproj identity mismatch")

    raw_episodes = document["episodes"]
    if not isinstance(raw_episodes, list):
        raise KnowledgeViewError("knowledge view catalog episodes must be a list")
    values = {value.value_id: value for value in snapshot.values}
    source_roster = set(snapshot.source_sample_ids)
    seen_episode_ids: set[str] = set()
    seen_value_ids: set[str] = set()
    episodes: list[KnowledgeEpisodeBinding] = []
    for index, item in enumerate(raw_episodes):
        if not isinstance(item, Mapping) or set(item) != _EPISODE_KEYS:
            raise KnowledgeViewError(
                f"knowledge episode {index} must have exact keys {sorted(_EPISODE_KEYS)}"
            )
        episode_id = _require_text(item["episode_id"], field=f"episode {index} ID")
        value_id = _require_text(item["value_id"], field=f"episode {index} value ID")
        source_sample_id = _require_text(
            item["source_sample_id"], field=f"episode {index} source sample ID"
        )
        if episode_id in seen_episode_ids:
            raise KnowledgeViewError("knowledge catalog episode IDs must be unique")
        if value_id in seen_value_ids:
            raise KnowledgeViewError("knowledge catalog value IDs must be unique")
        seen_episode_ids.add(episode_id)
        seen_value_ids.add(value_id)
        value = values.get(value_id)
        if value is None:
            raise KnowledgeViewError(
                f"knowledge episode names unknown value {value_id!r}"
            )
        if (
            source_sample_id not in source_roster
            or source_sample_id not in value.source_sample_ids
        ):
            raise KnowledgeViewError(
                f"knowledge episode source sample {source_sample_id!r} "
                f"does not bind value {value_id!r}"
            )

        audio_sha = _require_sha256(
            item["audio_sha256"], field=f"episode {index} audio SHA-256"
        )
        packet_id = _require_text(item["packet_id"], field=f"episode {index} packet ID")
        packet_sha = _require_sha256(
            item["packet_sha256"], field=f"episode {index} packet SHA-256"
        )
        encoder_sha = _require_sha256(
            item["encoder_receipt_sha256"],
            field=f"episode {index} encoder receipt SHA-256",
        )
        try:
            packet = load_speech_feature_packet(
                Path(feature_root),
                packet_id,
                expected_sha256=packet_sha,
                expected_decoder_gguf_sha256=decoder_sha,
            )
        except FrozenCoreError as error:
            raise KnowledgeViewError(
                f"knowledge episode {episode_id!r} packet validation failed: {error}"
            ) from error
        if packet.audio_sha256 != audio_sha:
            raise KnowledgeViewError(
                f"knowledge episode {episode_id!r} audio identity mismatch"
            )
        if packet.encoder_receipt_sha256 != encoder_sha:
            raise KnowledgeViewError(
                f"knowledge episode {episode_id!r} encoder identity mismatch"
            )
        if packet.mmproj_sha256 != mmproj_sha:
            raise KnowledgeViewError(
                f"knowledge episode {episode_id!r} mmproj identity mismatch"
            )
        episodes.append(
            KnowledgeEpisodeBinding(
                episode_id=episode_id,
                value_id=value_id,
                source_sample_id=source_sample_id,
                audio_sha256=audio_sha,
                packet_id=packet.packet_id,
                packet_sha256=packet.packet_sha256,
                encoder_receipt_sha256=encoder_sha,
            )
        )

    return PreparedKnowledgeViewCatalog(
        manifest_sha256=_require_sha256(
            expected_sha256, field="expected manifest SHA-256"
        ),
        snapshot_sha256=snapshot_sha256,
        source_split_identity_hash=split_hash,
        decoder_gguf_sha256=decoder_sha,
        mmproj_sha256=mmproj_sha,
        episodes=tuple(episodes),
    )
