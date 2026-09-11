"""Generic source-bound media inventories and a thin SLURP TRAIN adapter."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from .model import FrozenCoreError
from .model.paths import _normalized_relative_path, _resolve_confined
from .preparation import PreparationError, digest, prepare_artifact
from .preparation_windows import WindowFeatureEncoderIdentity

SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA = "saea-source-media-feature-inventory-v1"
SOURCE_MEDIA_FEATURE_INVENTORY_KIND = "source-media-feature-inventory-v1"
SLURP_TRAIN_RECALLED_ROSTER_SCHEMA = (
    "saea-slurp-train-recalled-candidate-preparation-roster-v1"
)
_SOURCE_KEYS = {"sample_id", "media_relpath", "sha256", "bytes"}
_INVENTORY_SOURCE_KEYS = _SOURCE_KEYS | {"source_kind"}
_INPUT_KEYS = {"audio_sha256", "source_sample_id"}
_AUTHORITY_KEYS = {"carrier", "partition", "roster_schema", "roster_sha256"}
_ROSTER_ENTRY_KEYS = {
    "candidate_facet_id",
    "source_sample_id",
    "media_relpath",
    "audio_sha256",
    "audio_bytes",
    "utterance_id",
}
_SLURP_TRAIN_SAMPLE_ID = re.compile(r"slurp:train:[0-9]{6}:[^/\\]+")
_SLURP_TRAIN_MEDIA_PREFIX = "datasets/slurp/slurp_real/"


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PreparationError(f"{label} must be a lowercase SHA256")
    return value


def _identity(encoder_identity: Mapping[str, object]) -> dict[str, str]:
    try:
        return WindowFeatureEncoderIdentity(**dict(encoder_identity)).as_json()
    except (TypeError, ValueError, PreparationError) as error:
        raise PreparationError("source media encoder identity is invalid") from error


def _read_confined_media(data_root: Path, relpath: object) -> tuple[str, bytes]:
    try:
        normalized = _normalized_relative_path(relpath, "source media_relpath")
        candidate = _resolve_confined(
            data_root,
            normalized,
            data_root,
            "source media",
            strict=True,
        )
    except FrozenCoreError as error:
        raise PreparationError("source media path is not confined") from error
    try:
        return normalized, candidate.read_bytes()
    except OSError as error:
        raise PreparationError("cannot read source media") from error


def _validated_authority(authority: Mapping[str, object]) -> dict[str, str]:
    if not isinstance(authority, Mapping) or set(authority) != _AUTHORITY_KEYS:
        raise PreparationError("source media authority has an invalid shape")
    result = dict(authority)
    for field in ("carrier", "partition", "roster_schema"):
        if not isinstance(result[field], str) or not result[field]:
            raise PreparationError(f"source media authority {field} is invalid")
    result["roster_sha256"] = _sha256(
        result["roster_sha256"], "source media authority roster_sha256"
    )
    return result


def build_source_media_feature_inventory(
    *,
    sources: Sequence[Mapping[str, object]],
    source_authority: Mapping[str, object],
    data_root: Path,
    encoder_identity: Mapping[str, object],
) -> dict[str, object]:
    """Validate generic registered media into a non-OBS encoding inventory."""
    authority = _validated_authority(source_authority)
    identity = _identity(encoder_identity)
    root = Path(data_root).resolve(strict=True)
    if (
        not isinstance(sources, Sequence)
        or isinstance(sources, (str, bytes))
        or not sources
    ):
        raise PreparationError("source media inventory requires nonempty sources")
    seen_samples: set[str] = set()
    seen_audio: set[str] = set()
    inventory_sources: list[dict[str, object]] = []
    for source in sources:
        if not isinstance(source, Mapping) or set(source) != _SOURCE_KEYS:
            raise PreparationError("source media source has an invalid shape")
        sample_id = source["sample_id"]
        if not isinstance(sample_id, str) or not sample_id:
            raise PreparationError("source media sample identity is invalid")
        audio = _sha256(source["sha256"], "source media audio_sha256")
        declared_bytes = source["bytes"]
        if (
            isinstance(declared_bytes, bool)
            or not isinstance(declared_bytes, int)
            or declared_bytes < 1
        ):
            raise PreparationError("source media bytes is invalid")
        if sample_id in seen_samples or audio in seen_audio:
            raise PreparationError("source media sources are ambiguous")
        seen_samples.add(sample_id)
        seen_audio.add(audio)
        relpath, content = _read_confined_media(root, source["media_relpath"])
        if (
            hashlib.sha256(content).hexdigest() != audio
            or len(content) != declared_bytes
        ):
            raise PreparationError("source media bytes differ from the frozen roster")
        inventory_sources.append(
            {
                "source_kind": "registered-media",
                "sample_id": sample_id,
                "media_relpath": relpath,
                "sha256": audio,
                "bytes": declared_bytes,
            }
        )
    inventory_sources.sort(key=lambda source: str(source["sample_id"]))
    return {
        "schema": SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA,
        "source_kind": "registered-media",
        "source_authority": authority,
        "encoder_identity": identity,
        "sources": inventory_sources,
        "encoding_inputs": [
            {
                "audio_sha256": source["sha256"],
                "source_sample_id": source["sample_id"],
            }
            for source in inventory_sources
        ],
    }


def _load_slurp_train_recalled_sources(
    *, roster_path: Path, expected_roster_sha256: str
) -> tuple[dict[str, str], list[dict[str, object]]]:
    roster_file = Path(roster_path).resolve(strict=True)
    raw = roster_file.read_bytes()
    expected = _sha256(expected_roster_sha256, "source roster sha256")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise PreparationError("source roster SHA256 differs from its registered pin")
    try:
        roster = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreparationError("source roster is not valid JSON") from error
    if (
        not isinstance(roster, Mapping)
        or roster.get("schema") != SLURP_TRAIN_RECALLED_ROSTER_SCHEMA
    ):
        raise PreparationError("source roster schema is not admitted for this adapter")
    readiness = roster.get("source_readiness")
    if not isinstance(readiness, Mapping) or set(readiness) != {
        "path",
        "sha256",
        "entry_canonical_sha256",
    }:
        raise PreparationError("SLURP TRAIN roster lacks declared source readiness")
    readiness_sha = _sha256(readiness["sha256"], "SLURP TRAIN source readiness sha256")
    entries_sha = _sha256(
        readiness["entry_canonical_sha256"], "SLURP TRAIN readiness entries"
    )
    if not isinstance(readiness["path"], str) or not readiness["path"]:
        raise PreparationError("SLURP TRAIN source readiness path is invalid")
    readiness_path = Path(readiness["path"])
    if not readiness_path.is_absolute():
        raise PreparationError("SLURP TRAIN source readiness path must be absolute")
    try:
        readiness_raw = readiness_path.read_bytes()
        readiness_document = json.loads(readiness_raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PreparationError(
            "SLURP TRAIN source readiness cannot be loaded"
        ) from error
    if hashlib.sha256(readiness_raw).hexdigest() != readiness_sha:
        raise PreparationError("SLURP TRAIN source readiness SHA256 differs")
    source_inventory = (
        readiness_document.get("source_to_media_inventory")
        if isinstance(readiness_document, Mapping)
        else None
    )
    readiness_entries = (
        source_inventory.get("entries")
        if isinstance(source_inventory, Mapping)
        else None
    )
    if (
        not isinstance(readiness_document, Mapping)
        or readiness_document.get("schema")
        != "saea-slurp-train-candidate-media-readiness-v1"
        or not isinstance(source_inventory, Mapping)
        or not isinstance(readiness_entries, list)
        or source_inventory.get("entry_canonical_sha256") != entries_sha
        or digest(readiness_entries) != entries_sha
    ):
        raise PreparationError("SLURP TRAIN source readiness authority disagrees")
    readiness_sources = {}
    for item in readiness_entries:
        if not isinstance(item, Mapping):
            raise PreparationError("SLURP TRAIN readiness entry is invalid")
        facet = item.get("candidate_facet_id")
        selected = item.get("deterministic_selected_source")
        utterance_id = item.get("utterance_id")
        if (
            not isinstance(facet, str)
            or not isinstance(selected, Mapping)
            or set(selected) != {"sample_id", "media_relpath"}
            or not isinstance(selected.get("sample_id"), str)
            or not isinstance(selected.get("media_relpath"), str)
            or not isinstance(utterance_id, str)
            or not utterance_id
            or facet in readiness_sources
        ):
            raise PreparationError("SLURP TRAIN readiness entry is invalid")
        readiness_sources[facet] = {
            "sample_id": selected["sample_id"],
            "media_relpath": selected["media_relpath"],
            "utterance_id": utterance_id,
        }
    entries = roster.get("entries")
    if (
        not isinstance(entries, list)
        or roster.get("roster_count") != len(entries)
        or not entries
    ):
        raise PreparationError("source roster count disagrees with its entries")
    if len(readiness_sources) != len(entries):
        raise PreparationError(
            "source roster does not cover the declared readiness selection"
        )
    sources: list[dict[str, object]] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != _ROSTER_ENTRY_KEYS:
            raise PreparationError("source roster entry has an invalid shape")
        sample_id = entry["source_sample_id"]
        selected = readiness_sources.get(entry["candidate_facet_id"])
        if (
            selected is None
            or selected["sample_id"] != sample_id
            or selected["media_relpath"] != entry["media_relpath"]
            or selected["utterance_id"] != entry["utterance_id"]
        ):
            raise PreparationError(
                "source roster entry disagrees with readiness selection"
            )
        if (
            not isinstance(sample_id, str)
            or _SLURP_TRAIN_SAMPLE_ID.fullmatch(sample_id) is None
        ):
            raise PreparationError("source roster contains a non-TRAIN sample identity")
        media = entry["media_relpath"]
        if not isinstance(media, str) or not media.startswith(
            _SLURP_TRAIN_MEDIA_PREFIX
        ):
            raise PreparationError(
                "source roster contains media outside SLURP real TRAIN"
            )
        sources.append(
            {
                "sample_id": sample_id,
                "media_relpath": media,
                "sha256": entry["audio_sha256"],
                "bytes": entry["audio_bytes"],
            }
        )
    return {
        "carrier": "slurp",
        "partition": "train",
        "roster_schema": SLURP_TRAIN_RECALLED_ROSTER_SCHEMA,
        "roster_sha256": expected,
    }, sources


def build_slurp_train_recalled_media_feature_inventory(
    *,
    roster_path: Path,
    expected_roster_sha256: str,
    data_root: Path,
    encoder_identity: Mapping[str, object],
) -> dict[str, object]:
    """Adapt the admitted recalled TRAIN roster to the generic inventory rail."""
    authority, sources = _load_slurp_train_recalled_sources(
        roster_path=roster_path,
        expected_roster_sha256=expected_roster_sha256,
    )
    return build_source_media_feature_inventory(
        sources=sources,
        source_authority=authority,
        data_root=data_root,
        encoder_identity=encoder_identity,
    )


def prepare_slurp_train_recalled_media_feature_inventory(
    output_path: Path,
    *,
    roster_path: Path,
    expected_roster_sha256: str,
    data_root: Path,
    encoder_identity: Mapping[str, object],
):
    """Persist the thin-adapter inventory through the shared artifact rail."""
    identity = _identity(encoder_identity)
    inputs = {
        "roster_path": str(Path(roster_path).resolve(strict=True)),
        "roster_sha256": _sha256(expected_roster_sha256, "source roster sha256"),
        "encoder_identity": identity,
        "source_partition": "train",
    }
    return prepare_artifact(
        Path(output_path),
        kind=SOURCE_MEDIA_FEATURE_INVENTORY_KIND,
        inputs=inputs,
        producer=lambda: build_slurp_train_recalled_media_feature_inventory(
            roster_path=roster_path,
            expected_roster_sha256=expected_roster_sha256,
            data_root=data_root,
            encoder_identity=identity,
        ),
    )


def source_media_encoding_sources(
    inventory: Mapping[str, object],
) -> dict[str, Mapping[str, object]]:
    """Validate and expose every registered source media input exactly once."""
    if inventory.get("schema") != SOURCE_MEDIA_FEATURE_INVENTORY_SCHEMA:
        raise PreparationError("source media inventory schema is invalid")
    if inventory.get("source_kind") != "registered-media":
        raise PreparationError("source media inventory kind is invalid")
    _validated_authority(inventory.get("source_authority"))
    sources = inventory.get("sources")
    inputs = inventory.get("encoding_inputs")
    if not isinstance(sources, list) or not isinstance(inputs, list) or not sources:
        raise PreparationError("source media inventory has no sources")
    by_sample: dict[str, Mapping[str, object]] = {}
    by_audio: dict[str, Mapping[str, object]] = {}
    for source in sources:
        if not isinstance(source, Mapping) or set(source) != _INVENTORY_SOURCE_KEYS:
            raise PreparationError("source media inventory source has an invalid shape")
        if source.get("source_kind") != "registered-media":
            raise PreparationError("source media inventory source kind is invalid")
        sample = source.get("sample_id")
        if not isinstance(sample, str) or not sample:
            raise PreparationError("source media inventory sample identity is invalid")
        audio = _sha256(source.get("sha256"), "source media audio_sha256")
        if sample in by_sample or audio in by_audio:
            raise PreparationError("source media inventory source is ambiguous")
        by_sample[sample] = source
        by_audio[audio] = source
    pairs: set[tuple[str, str]] = set()
    for entry in inputs:
        if not isinstance(entry, Mapping) or set(entry) != _INPUT_KEYS:
            raise PreparationError("source media encoding input has an invalid shape")
        audio = _sha256(entry.get("audio_sha256"), "source media encoding audio_sha256")
        sample = entry.get("source_sample_id")
        if not isinstance(sample, str) or not sample:
            raise PreparationError("source media encoding sample identity is invalid")
        if (audio, sample) in pairs or by_sample.get(sample) is not by_audio.get(audio):
            raise PreparationError(
                "source media encoding input disagrees with its source"
            )
        pairs.add((audio, sample))
    if len(pairs) != len(by_audio):
        raise PreparationError("source media encoding inputs do not cover sources")
    return dict(by_audio)
