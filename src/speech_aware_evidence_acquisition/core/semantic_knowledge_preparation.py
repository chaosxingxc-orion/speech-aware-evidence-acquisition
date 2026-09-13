from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from speech_aware_evidence_acquisition.core.base import CoreError, KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    _acquire_artifact_locks,
    _publish_artifact,
    canonical_bytes,
    digest,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
)

REGISTRATION_SCHEMA = "saea-authored-semantic-knowledge-preparation-v1"
SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
ROSTER_SCHEMA = "saea-semantic-knowledge-roster-v1"
COMPLETION_SCHEMA = "saea-authored-semantic-knowledge-preparation-completion-v1"
_RELEASE_SCHEMA = "saea-knowledge-store-release-v1"
_SLUG = re.compile(r"^[a-z0-9]+(?:[-_.][a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SemanticKnowledgePreparationError(RuntimeError):
    """Raised when registered semantic knowledge preparation is invalid."""


@dataclass(frozen=True)
class _Pin:
    relpath: str
    sha256: str
    path: Path

    def as_json(self) -> dict[str, str]:
        return {"relpath": self.relpath, "sha256": self.sha256}


def _mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SemanticKnowledgePreparationError(f"{name} must be an object")
    return value


def _exact_keys(value: Mapping[str, Any], expected: set[str], *, name: str) -> None:
    if set(value) != expected:
        raise SemanticKnowledgePreparationError(
            f"{name} fields differ from the registered schema"
        )


def _text(value: object, *, name: str, slug: bool = False) -> str:
    if not isinstance(value, str) or not value:
        raise SemanticKnowledgePreparationError(f"{name} must be non-empty text")
    if slug and _SLUG.fullmatch(value) is None:
        raise SemanticKnowledgePreparationError(
            f"{name} must be a canonical identifier"
        )
    return value


def _relative(value: object, *, name: str) -> str:
    text = _text(value, name=name)
    if "\\" in text or ":" in text or text.startswith("/"):
        raise SemanticKnowledgePreparationError(
            f"{name} must be a canonical relative path"
        )
    parts = text.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SemanticKnowledgePreparationError(
            f"{name} must be a canonical relative path"
        )
    return text


def _confined(root: Path, relpath: str, *, name: str) -> Path:
    resolved_root = root.resolve()
    path = (resolved_root / relpath).resolve(strict=False)
    try:
        path.relative_to(resolved_root)
    except ValueError as exc:
        raise SemanticKnowledgePreparationError(
            f"{name} escapes its configured root"
        ) from exc
    return path


def _pin(value: object, *, root: Path, name: str) -> _Pin:
    mapping = _mapping(value, name=name)
    _exact_keys(mapping, {"relpath", "sha256"}, name=name)
    relpath = _relative(mapping["relpath"], name=f"{name}.relpath")
    sha256 = _text(mapping["sha256"], name=f"{name}.sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise SemanticKnowledgePreparationError(
            f"{name}.sha256 must be lowercase SHA-256"
        )
    return _Pin(relpath, sha256, _confined(root, relpath, name=name))


def _read_pin(pin: _Pin, *, name: str) -> bytes:
    try:
        raw = pin.path.read_bytes()
    except OSError as exc:
        raise SemanticKnowledgePreparationError(f"unable to read {name}") from exc
    if hashlib.sha256(raw).hexdigest() != pin.sha256:
        raise SemanticKnowledgePreparationError(f"{name} SHA-256 differs from its pin")
    return raw


def _json(raw: bytes, *, name: str) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(raw), name=name)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SemanticKnowledgePreparationError(
            f"{name} must be canonical JSON"
        ) from exc


def _sample_ids(value: object, *, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise SemanticKnowledgePreparationError(f"{name} must be a non-empty list")
    result = tuple(_text(item, name=f"{name} entry") for item in value)
    if len(set(result)) != len(result):
        raise SemanticKnowledgePreparationError(f"{name} must not contain duplicates")
    return result


def _roster(
    raw: bytes, *, name: str, carrier: str
) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    roster = _json(raw, name=name)
    _exact_keys(
        roster,
        {
            "schema",
            "roster_id",
            "carrier_lock_key",
            "roster_role",
            "split_identity_hash",
            "sample_ids",
        },
        name=name,
    )
    if roster["schema"] != ROSTER_SCHEMA:
        raise SemanticKnowledgePreparationError(f"{name} has unsupported schema")
    if roster["carrier_lock_key"] != carrier or roster["roster_role"] != "construction":
        raise SemanticKnowledgePreparationError(f"{name} has wrong carrier or role")
    _text(roster["roster_id"], name=f"{name}.roster_id")
    _text(roster["split_identity_hash"], name=f"{name}.split_identity_hash")
    return roster, _sample_ids(roster["sample_ids"], name=f"{name}.sample_ids")


def _source_rows(
    raw: bytes, *, builder_id: str, source_identity: str
) -> Sequence[Mapping[str, Any]]:
    source = _json(raw, name="authored_source")
    _exact_keys(
        source,
        {"schema", "builder_policy_id", "source_split_identity_hash", "rows"},
        name="authored_source",
    )
    if source["schema"] != SOURCE_SCHEMA:
        raise SemanticKnowledgePreparationError(
            "authored_source has unsupported schema"
        )
    if source["builder_policy_id"] != builder_id:
        raise SemanticKnowledgePreparationError(
            "authored_source builder identity differs"
        )
    if source["source_split_identity_hash"] != source_identity:
        raise SemanticKnowledgePreparationError(
            "authored_source split identity differs"
        )
    rows = source["rows"]
    if (
        not isinstance(rows, list)
        or not rows
        or any(not isinstance(row, Mapping) for row in rows)
    ):
        raise SemanticKnowledgePreparationError(
            "authored_source.rows must be non-empty objects"
        )
    return rows


def _registration(
    path: Path, raw: bytes, *, repo_root: Path, data_root: Path
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    registration = _json(raw, name="registration")
    _exact_keys(
        registration,
        {
            "schema",
            "registration_id",
            "carrier_lock_key",
            "source_partition_role",
            "source_split_identity_hash",
            "builder_policy_id",
            "store_id",
            "store_role",
            "authored_source",
            "construction_scope",
            "permitted_roster",
            "forbidden_rosters",
            "output_namespace",
        },
        name="registration",
    )
    if registration["schema"] != REGISTRATION_SCHEMA:
        raise SemanticKnowledgePreparationError("registration has unsupported schema")
    _text(registration["registration_id"], name="registration.registration_id")
    for key in ("carrier_lock_key", "builder_policy_id", "store_id", "store_role"):
        _text(registration[key], name=f"registration.{key}", slug=True)
    if registration["source_partition_role"] != "train":
        raise SemanticKnowledgePreparationError(
            "registration source partition must be train"
        )
    source_identity = _text(
        registration["source_split_identity_hash"],
        name="registration.source_split_identity_hash",
    )
    output_namespace = _relative(
        registration["output_namespace"], name="registration.output_namespace"
    )
    forbidden = registration["forbidden_rosters"]
    if not isinstance(forbidden, list) or not forbidden:
        raise SemanticKnowledgePreparationError(
            "registration.forbidden_rosters must be a list"
        )
    pins = {
        "authored_source": _pin(
            registration["authored_source"], root=data_root, name="authored_source"
        ),
        "construction_scope": _pin(
            registration["construction_scope"],
            root=repo_root,
            name="construction_scope",
        ),
        "permitted_roster": _pin(
            registration["permitted_roster"], root=repo_root, name="permitted_roster"
        ),
        "forbidden_rosters": tuple(
            _pin(value, root=repo_root, name=f"forbidden_rosters[{index}]")
            for index, value in enumerate(forbidden)
        ),
        "output_namespace": output_namespace,
    }
    try:
        registration_relpath = (
            path.resolve().relative_to(repo_root.resolve()).as_posix()
        )
    except ValueError as exc:
        raise SemanticKnowledgePreparationError(
            "registration must be confined to repo_root"
        ) from exc
    pins["registration"] = _Pin(
        registration_relpath, hashlib.sha256(raw).hexdigest(), path.resolve()
    )
    pins["source_identity"] = source_identity
    return registration, pins


@contextmanager
def _output_locks(paths: Sequence[Path]) -> Iterator[None]:
    handles = []
    try:
        handles = _acquire_artifact_locks(
            [{"path": path, "resolved": path.resolve()} for path in paths]
        )
        yield
    except PreparationError as exc:
        raise SemanticKnowledgePreparationError(str(exc)) from exc
    finally:
        for handle in reversed(handles):
            try:
                os.close(handle)
            except OSError:
                pass


def _existing_bytes(path: Path) -> bytes | None:
    if not os.path.lexists(path):
        return None
    if path.is_symlink():
        raise SemanticKnowledgePreparationError(f"output collision at {path.name}")
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SemanticKnowledgePreparationError(
            f"unable to validate output {path.name}"
        ) from exc


def prepare_semantic_knowledge_store(
    registration_path: Path,
    *,
    repo_root: Path,
    data_root: Path,
) -> Mapping[str, Any]:
    """Build or exactly reuse one registered, source-bound named knowledge store."""

    registration_path = Path(registration_path)
    repo_root = Path(repo_root)
    data_root = Path(data_root)
    try:
        registration_raw = registration_path.read_bytes()
    except OSError as exc:
        raise SemanticKnowledgePreparationError("unable to read registration") from exc
    registration, pins = _registration(
        registration_path, registration_raw, repo_root=repo_root, data_root=data_root
    )

    # Verify every declared input byte before parsing any source content or building outputs.
    source_raw = _read_pin(pins["authored_source"], name="authored_source")
    scope_raw = _read_pin(pins["construction_scope"], name="construction_scope")
    permitted_raw = _read_pin(pins["permitted_roster"], name="permitted_roster")
    forbidden_raw = tuple(
        _read_pin(pin, name=f"forbidden_rosters[{index}]")
        for index, pin in enumerate(pins["forbidden_rosters"])
    )

    carrier = registration["carrier_lock_key"]
    scope, scope_ids = _roster(scope_raw, name="construction_scope", carrier=carrier)
    permitted, permitted_ids = _roster(
        permitted_raw, name="permitted_roster", carrier=carrier
    )
    if permitted["split_identity_hash"] != pins["source_identity"]:
        raise SemanticKnowledgePreparationError(
            "permitted roster split identity differs"
        )
    if not set(permitted_ids).issubset(scope_ids):
        raise SemanticKnowledgePreparationError(
            "permitted support roster is outside construction scope"
        )

    forbidden_records = []
    forbidden_ids: set[str] = set()
    for index, raw in enumerate(forbidden_raw):
        roster, ids = _roster(raw, name=f"forbidden_rosters[{index}]", carrier=carrier)
        forbidden_records.append((roster, ids))
        forbidden_ids.update(ids)

    rows = _source_rows(
        source_raw,
        builder_id=registration["builder_policy_id"],
        source_identity=pins["source_identity"],
    )
    try:
        # Importing the shared registration module installs the registered builders only.
        importlib.import_module(
            "speech_aware_evidence_acquisition.rails.knowledge_build"
        )

        builder = KNOWLEDGE_BUILDERS.resolve(registration["builder_policy_id"])
        snapshot = builder(
            AuthoredSemanticKnowledgeSpec(
                carrier_lock_key=carrier,
                source_split_identity_hash=pins["source_identity"],
                permitted_source_sample_ids=permitted_ids,
                source_partition_role=registration["source_partition_role"],
            ),
            rows=rows,
            forbidden_sample_ids=frozenset(forbidden_ids),
        )
    except (CoreError, RailsError, TypeError, ValueError) as exc:
        raise SemanticKnowledgePreparationError(str(exc)) from exc

    namespace = _confined(data_root, pins["output_namespace"], name="output_namespace")
    snapshot_path = namespace / "snapshot.json"
    release_path = namespace / "release.json"
    completion_path = namespace / "completion.json"
    snapshot_relpath = snapshot_path.relative_to(data_root.resolve()).as_posix()
    release_relpath = release_path.relative_to(data_root.resolve()).as_posix()
    completion_relpath = completion_path.relative_to(data_root.resolve()).as_posix()

    snapshot_raw = canonical_bytes(snapshot.frozen_json())
    snapshot_pin = {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()}
    release = {
        "schema": _RELEASE_SCHEMA,
        "store_id": registration["store_id"],
        "store_role": registration["store_role"],
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": pins["source_identity"],
        "builder_policy_id": registration["builder_policy_id"],
        "source": pins["authored_source"].as_json(),
    }
    release_raw = canonical_bytes(release)
    release_pin = {
        "relpath": release_relpath,
        "sha256": hashlib.sha256(release_raw).hexdigest(),
    }
    binding = {
        "registration": pins["registration"].as_json(),
        "authored_source": pins["authored_source"].as_json(),
        "construction_scope": pins["construction_scope"].as_json(),
        "permitted_roster": pins["permitted_roster"].as_json(),
        "forbidden_rosters": [pin.as_json() for pin in pins["forbidden_rosters"]],
        "source_split_identity_hash": pins["source_identity"],
        "builder_policy_id": registration["builder_policy_id"],
        "store_id": registration["store_id"],
        "store_role": registration["store_role"],
        "output_namespace": pins["output_namespace"],
    }
    completion = {
        "schema": COMPLETION_SCHEMA,
        "registration_id": registration["registration_id"],
        "binding_sha256": digest(binding),
        "binding": binding,
        "outer_construction_scope": {
            "roster_id": scope["roster_id"],
            "split_identity_hash": scope["split_identity_hash"],
            "sample_count": len(scope_ids),
        },
        "exact_support_roster": {
            "roster_id": permitted["roster_id"],
            "split_identity_hash": permitted["split_identity_hash"],
            "sample_count": len(permitted_ids),
        },
        "forbidden_rosters": [
            {
                "roster_id": roster["roster_id"],
                "split_identity_hash": roster["split_identity_hash"],
                "sample_count": len(ids),
            }
            for roster, ids in forbidden_records
        ],
        "snapshot": snapshot_pin,
        "snapshot_file_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "release": release_pin,
        "contacts": {"model": 0, "tool": 0, "scorer": 0},
    }
    completion_raw = canonical_bytes(completion)
    expected = (
        (snapshot_path, snapshot_raw),
        (release_path, release_raw),
        (completion_path, completion_raw),
    )

    with _output_locks([path for path, _ in expected]):
        prior = []
        for path, raw in expected:
            existing = _existing_bytes(path)
            if existing is not None and existing != raw:
                raise SemanticKnowledgePreparationError(
                    f"output collision at {path.name}"
                )
            prior.append(existing is not None)
        for path, raw in expected:
            if not os.path.lexists(path):
                try:
                    _publish_artifact(path, raw, contact_class="model-free")
                except PreparationError as exc:
                    raise SemanticKnowledgePreparationError(str(exc)) from exc
        for path, raw in expected:
            if _existing_bytes(path) != raw:
                raise SemanticKnowledgePreparationError(
                    f"published output differs at {path.name}"
                )

    return {
        "cache": "warm" if all(prior) else "cold",
        "completion": completion,
        "completion_pin": {
            "relpath": completion_relpath,
            "sha256": hashlib.sha256(completion_raw).hexdigest(),
        },
    }
