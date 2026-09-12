"""Create-only storage for source-verified native reward links.

The artifact is a cache of native numeric feedback and provenance identities.  Reading
it always re-verifies the authoritative bundle, score receipt, and construction
roster; local link hashes alone never establish source authority.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

from ..core.scoring_receipt import SavedScoreReceiptRef
from .experience_memory import ExperienceSource
from .hashing import content_hash
from .reward_links import (
    RewardLink,
    RewardLinkError,
    RewardProjection,
    build_reward_links,
    verify_reward_links,
)

REWARD_LINK_ARTIFACT_CONFIG_SCHEMA = "saea-reward-link-artifact-config-v1"
REWARD_LINK_ARTIFACT_SCHEMA = "saea-reward-link-artifact-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_CONFIG_KEYS = frozenset({
    "schema", "manifest", "complete_score_receipt",
    "construction_roster", "projection",
})
_ARTIFACT_KEYS = frozenset({
    "schema", "config_sha256", "source_pins", "projection", "links",
})
_LINK_KEYS = frozenset({
    "schema", "source", "carrier_lock_key", "construction_roster_sha256",
    "projection", "native_score_vector", "provenance", "link_sha256",
})


class RewardLinkArtifactError(ValueError):
    """A reward-link artifact or its pinned configuration is invalid."""


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise RewardLinkArtifactError(f"{field} must be an object")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RewardLinkArtifactError(f"{field} must be nonempty text")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RewardLinkArtifactError(f"{field} must be a lowercase SHA-256")
    return value


def _pin(value: object, field: str, *, receipt: bool = False) -> dict[str, str]:
    row = _mapping(value, field)
    keys = {"path", "sha256", "cell_id"} if receipt else {"path", "sha256"}
    if set(row) != keys:
        raise RewardLinkArtifactError(f"{field} pin has missing or unknown fields")
    declared_path = _text(row.get("path"), f"{field} path")
    if not Path(declared_path).is_absolute():
        raise RewardLinkArtifactError(f"{field} path must be absolute")
    result = {
        "path": declared_path,
        "sha256": _sha(row.get("sha256"), f"{field} hash"),
    }
    if receipt:
        result["cell_id"] = _text(row.get("cell_id"), f"{field} cell ID")
    return result


def _validated_config(config: object) -> tuple[dict[str, object], RewardProjection]:
    row = _mapping(config, "reward-link artifact config")
    if set(row) != _CONFIG_KEYS:
        raise RewardLinkArtifactError("reward-link artifact config has missing or unknown fields")
    if row.get("schema") != REWARD_LINK_ARTIFACT_CONFIG_SCHEMA:
        raise RewardLinkArtifactError("unsupported reward-link artifact config schema")
    try:
        projection = RewardProjection.from_json(row.get("projection"))
    except RewardLinkError as error:
        raise RewardLinkArtifactError(str(error)) from error
    normalized = {
        "schema": REWARD_LINK_ARTIFACT_CONFIG_SCHEMA,
        "manifest": _pin(row.get("manifest"), "manifest"),
        "complete_score_receipt": _pin(
            row.get("complete_score_receipt"), "complete score receipt", receipt=True,
        ),
        "construction_roster": _pin(row.get("construction_roster"), "construction roster"),
        "projection": projection.as_json(),
    }
    return normalized, projection


def _verify_source_pins(config: Mapping[str, object]) -> None:
    """Hash every declared input before any parser or source verifier opens it."""
    for key in ("manifest", "complete_score_receipt", "construction_roster"):
        pin = config[key]
        path = Path(pin["path"])
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise RewardLinkArtifactError(f"cannot read pinned {key}: {error}") from error
        if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
            raise RewardLinkArtifactError(f"pinned {key} hash mismatch")


def _source_arguments(config: Mapping[str, object]):
    receipt = config["complete_score_receipt"]
    return (
        Path(config["manifest"]["path"]),
        SavedScoreReceiptRef(receipt["cell_id"], Path(receipt["path"]), receipt["sha256"]),
        Path(config["construction_roster"]["path"]),
    )


def _parse_link(value: object) -> RewardLink:
    row = _mapping(value, "stored reward link")
    if set(row) != _LINK_KEYS:
        raise RewardLinkArtifactError("stored reward link has missing or unknown fields")
    try:
        link = RewardLink(
            source=ExperienceSource.from_json(row["source"]),
            carrier_lock_key=row["carrier_lock_key"],
            construction_roster_sha256=row["construction_roster_sha256"],
            projection=RewardProjection.from_json(row["projection"]),
            native_score_vector=_mapping(row["native_score_vector"], "native score vector"),
            provenance=_mapping(row["provenance"], "reward provenance"),
            link_sha256=row["link_sha256"],
            schema=row["schema"],
        )
        link.validate()
    except (RewardLinkError, ValueError, TypeError) as error:
        raise RewardLinkArtifactError(f"invalid stored reward link: {error}") from error
    return link


def _document(config: Mapping[str, object], links) -> dict[str, object]:
    return {
        "schema": REWARD_LINK_ARTIFACT_SCHEMA,
        "config_sha256": content_hash(config),
        "source_pins": {
            key: config[key]
            for key in ("manifest", "complete_score_receipt", "construction_roster")
        },
        "projection": config["projection"],
        "links": [link.as_json() for link in links],
    }


def _write_create_only(path: Path, raw: bytes) -> None:
    path = path.resolve()
    if os.path.lexists(path):
        raise RewardLinkArtifactError(f"output already exists: {path}")
    if not path.parent.is_dir():
        raise RewardLinkArtifactError(f"output parent does not exist: {path.parent}")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as error:
            raise RewardLinkArtifactError(f"output already exists: {path}") from error
    except OSError as error:
        raise RewardLinkArtifactError(f"cannot create reward-link artifact: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def build_reward_link_artifact(
    config: Mapping[str, object], output_path: Path,
) -> dict[str, str]:
    """Build and atomically publish one source-bound reward-link cache."""
    declared_output = Path(output_path)
    if os.path.lexists(declared_output):
        raise RewardLinkArtifactError(f"output already exists: {declared_output}")
    output = declared_output.resolve()
    normalized, projection = _validated_config(config)
    _verify_source_pins(normalized)
    manifest, receipt, roster = _source_arguments(normalized)
    try:
        links = build_reward_links(manifest, receipt, roster, projection)
        raw = (
            json.dumps(_document(normalized, links), ensure_ascii=False, sort_keys=True)
            + "\n"
        ).encode("utf-8")
    except (RewardLinkError, ValueError, RuntimeError, OSError) as error:
        raise RewardLinkArtifactError(f"cannot build verified reward links: {error}") from error
    _write_create_only(output, raw)
    return {"path": str(output), "sha256": hashlib.sha256(raw).hexdigest()}


def read_verified_reward_link_artifact(
    config: Mapping[str, object], artifact_path: Path,
) -> tuple[RewardLink, ...]:
    """Return stored links only after full authoritative source verification."""
    normalized, projection = _validated_config(config)
    _verify_source_pins(normalized)
    path = Path(artifact_path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RewardLinkArtifactError(f"cannot read reward-link artifact: {error}") from error
    row = _mapping(document, "reward-link artifact")
    if set(row) != _ARTIFACT_KEYS or row.get("schema") != REWARD_LINK_ARTIFACT_SCHEMA:
        raise RewardLinkArtifactError("reward-link artifact has invalid schema or fields")
    expected_sources = {
        key: normalized[key]
        for key in ("manifest", "complete_score_receipt", "construction_roster")
    }
    if (
        row.get("config_sha256") != content_hash(normalized)
        or row.get("source_pins") != expected_sources
        or row.get("projection") != projection.as_json()
    ):
        raise RewardLinkArtifactError("reward-link artifact binding differs from config")
    stored = row.get("links")
    if not isinstance(stored, list) or not stored:
        raise RewardLinkArtifactError("reward-link artifact must contain ordered links")
    links = tuple(_parse_link(item) for item in stored)
    manifest, receipt, roster = _source_arguments(normalized)
    try:
        return verify_reward_links(links, manifest, receipt, roster, projection)
    except (RewardLinkError, ValueError, RuntimeError, OSError) as error:
        raise RewardLinkArtifactError(
            f"reward-link artifact differs from authoritative sources: {error}"
        ) from error


def read_reward_link_artifact(
    config: Mapping[str, object], artifact_path: Path,
) -> tuple[ExperienceSource, ...]:
    """Return verified experience sources from the shared verified-link read."""
    return tuple(
        link.source
        for link in read_verified_reward_link_artifact(config, artifact_path)
    )


__all__ = [
    "REWARD_LINK_ARTIFACT_CONFIG_SCHEMA",
    "REWARD_LINK_ARTIFACT_SCHEMA",
    "RewardLinkArtifactError",
    "build_reward_link_artifact",
    "read_reward_link_artifact",
    "read_verified_reward_link_artifact",
]
