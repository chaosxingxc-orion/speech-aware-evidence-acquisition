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
from speech_aware_evidence_acquisition.core.roster import (
    CONSTRUCTION_ROSTER_ROLE,
    RECEIPT_SCHEMA,
    RosterError,
    read_roster,
)
from speech_aware_evidence_acquisition.core.split_receipt import SplitReceiptError
from speech_aware_evidence_acquisition.reproduction.probe_split import (
    PROBE_SAMPLES_DIRNAME,
    load_verified_probe_split,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
)

REGISTRATION_SCHEMA = "saea-authored-semantic-knowledge-preparation-v1"
SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
COMPLETION_SCHEMA = "saea-authored-semantic-knowledge-preparation-completion-v1"
_RELEASE_SCHEMA = "saea-knowledge-store-release-v1"
_STORE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class SemanticKnowledgePreparationError(RuntimeError):
    """Raised when registered semantic knowledge preparation is invalid."""


@dataclass(frozen=True)
class _Pin:
    relpath: str
    sha256: str
    path: Path
    root: str
    explicit_root: bool = False

    def as_json(self, *, include_root: bool = True) -> dict[str, str]:
        result = {"relpath": self.relpath, "sha256": self.sha256}
        if include_root and self.explicit_root:
            result["root"] = self.root
        return result


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
    if slug and _STORE_ID.fullmatch(value) is None:
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


def _pin(
    value: object,
    *,
    roots: Mapping[str, Path],
    default_root: str,
    allowed_roots: frozenset[str],
    name: str,
) -> _Pin:
    mapping = _mapping(value, name=name)
    if set(mapping) not in ({"relpath", "sha256"}, {"relpath", "sha256", "root"}):
        raise SemanticKnowledgePreparationError(
            f"{name} fields differ from the registered schema"
        )
    root_name = mapping.get("root", default_root)
    if not isinstance(root_name, str) or root_name not in allowed_roots:
        raise SemanticKnowledgePreparationError(f"{name}.root is not permitted")
    relpath = _relative(mapping["relpath"], name=f"{name}.relpath")
    sha256 = _text(mapping["sha256"], name=f"{name}.sha256")
    if _SHA256.fullmatch(sha256) is None:
        raise SemanticKnowledgePreparationError(
            f"{name}.sha256 must be lowercase SHA-256"
        )
    return _Pin(
        relpath,
        sha256,
        _confined(roots[root_name], relpath, name=name),
        root_name,
        "root" in mapping,
    )


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


@dataclass(frozen=True)
class _RosterReceipt:
    roster_id: str
    split_identity_hash: str
    sample_ids: tuple[str, ...]
    roster_role: str | None
    split_role: str


def _roster(
    pin: _Pin,
    raw: bytes,
    *,
    name: str,
    carrier: str,
    require_construction: bool,
    repo_root: Path,
) -> _RosterReceipt:
    document = _json(raw, name=name)
    schema = document.get("schema")
    if schema == RECEIPT_SCHEMA:
        try:
            roster = read_roster(pin.path)
        except (OSError, UnicodeError, json.JSONDecodeError, RosterError) as exc:
            raise SemanticKnowledgePreparationError(
                f"{name} is not a verified roster"
            ) from exc
        if roster.get("carrier_lock_key") != carrier:
            raise SemanticKnowledgePreparationError(f"{name} has the wrong carrier")
        role = roster.get("roster_role", "evaluation")
        if require_construction and role != CONSTRUCTION_ROSTER_ROLE:
            raise SemanticKnowledgePreparationError(
                f"{name} must retain construction role"
            )
        roster_id = _text(roster.get("roster_id"), name=f"{name}.roster_id")
        split_role = _text(roster.get("split_role"), name=f"{name}.split_role")
        items = roster["items"]
        return _RosterReceipt(
            roster_id=roster_id,
            split_identity_hash=_text(
                roster["split_identity_hash"], name=f"{name}.split_identity_hash"
            ),
            sample_ids=tuple(str(item["sample_id"]) for item in items),
            roster_role=str(role),
            split_role=split_role,
        )
    if schema == "saea-dev-ladder-v1" and not require_construction:
        if pin.root != "repo":
            raise SemanticKnowledgePreparationError(
                f"{name} probe receipt must use the repository root"
            )
        expected_parent = Path("docs") / "receipts" / PROBE_SAMPLES_DIRNAME
        relative = Path(pin.relpath)
        if relative.parent != expected_parent or relative.suffix != ".json":
            raise SemanticKnowledgePreparationError(
                f"{name} probe receipt must use its governed repository path"
            )
        try:
            verified = load_verified_probe_split(repo_root, relative.stem)
        except SplitReceiptError as exc:
            raise SemanticKnowledgePreparationError(
                f"{name} is not a verified probe roster"
            ) from exc
        if verified.carrier_lock_key != carrier:
            raise SemanticKnowledgePreparationError(f"{name} has the wrong carrier")
        return _RosterReceipt(
            roster_id=_text(document.get("probe"), name=f"{name}.probe"),
            split_identity_hash=verified.identity_hash,
            sample_ids=verified.ids,
            roster_role=None,
            split_role=verified.split_role,
        )
    raise SemanticKnowledgePreparationError(
        f"{name} has unsupported governed roster schema"
    )


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
    for key in ("carrier_lock_key", "builder_policy_id"):
        _text(registration[key], name=f"registration.{key}")
    for key in ("store_id", "store_role"):
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
    roots = {"repo": repo_root, "data": data_root}
    pins = {
        "authored_source": _pin(
            registration["authored_source"],
            roots=roots,
            default_root="data",
            allowed_roots=frozenset({"data"}),
            name="authored_source",
        ),
        "construction_scope": _pin(
            registration["construction_scope"],
            roots=roots,
            default_root="repo",
            allowed_roots=frozenset({"repo", "data"}),
            name="construction_scope",
        ),
        "permitted_roster": _pin(
            registration["permitted_roster"],
            roots=roots,
            default_root="repo",
            allowed_roots=frozenset({"repo", "data"}),
            name="permitted_roster",
        ),
        "forbidden_rosters": tuple(
            _pin(
                value,
                roots=roots,
                default_root="repo",
                allowed_roots=frozenset({"repo"}),
                name=f"forbidden_rosters[{index}]",
            )
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
        registration_relpath, hashlib.sha256(raw).hexdigest(), path.resolve(), "repo"
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


def _publish_exact_artifacts(expected: Sequence[tuple[Path, bytes]]) -> str:
    """Create or exactly reuse prepared artifacts through one shared writer."""
    with _output_locks([path for path, _ in expected]):
        prior = []
        for path, raw in expected:
            existing = _existing_bytes(path)
            if existing is not None and existing != raw:
                raise SemanticKnowledgePreparationError(f"output collision at {path.name}")
            prior.append(existing is not None)
        for path, raw in expected:
            if not os.path.lexists(path):
                _publish_artifact(path, raw, contact_class="model-free")
        for path, raw in expected:
            if _existing_bytes(path) != raw:
                raise SemanticKnowledgePreparationError(f"published output differs at {path.name}")
    return "warm" if all(prior) else "cold"


COMPILED_REGISTRATION_SCHEMA = "saea-compiled-knowledge-store-preparation-v1"


def _prepare_compiled_store(
    registration_path: Path, registration_raw: bytes, *, repo_root: Path, data_root: Path
) -> Mapping[str, Any]:
    """Release an existing pinned compiler snapshot without rebuilding knowledge."""
    from ..rails.knowledge import KnowledgeSnapshot
    from ..rails.knowledge_compile_a2t import (
        validate_compiled_knowledge_snapshot,
    )

    registration = _json(registration_raw, name="registration")
    _exact_keys(registration, {
        "schema", "registration_id", "store_id", "store_role",
        "compilation_receipt", "snapshot", "output_namespace",
    }, name="compiled registration")
    _text(registration["registration_id"], name="registration_id")
    for key in ("store_id", "store_role"):
        _text(registration[key], name=key, slug=True)
    try:
        registration_relpath = registration_path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise SemanticKnowledgePreparationError("registration must be confined to repo_root") from error
    roots = {"repo": repo_root, "data": data_root}
    pins = {
        key: _pin(registration[key], roots=roots, default_root="data",
                  allowed_roots=frozenset({"data"}), name=key)
        for key in ("compilation_receipt", "snapshot")
    }
    receipt = _json(_read_pin(pins["compilation_receipt"], name="compilation receipt"),
                    name="compilation receipt")
    snapshot_raw = _read_pin(pins["snapshot"], name="compiled snapshot")
    try:
        snapshot = KnowledgeSnapshot.from_frozen_json(
            _json(snapshot_raw, name="snapshot")
        )
    except (RailsError, KeyError, TypeError, ValueError) as error:
        raise SemanticKnowledgePreparationError(
            "compiled snapshot is invalid"
        ) from error
    try:
        validate_compiled_knowledge_snapshot(
            receipt,
            snapshot,
            store_role=registration["store_role"],
            snapshot_file_sha256=pins["snapshot"].sha256,
            snapshot_path=pins["snapshot"].path,
        )
    except RailsError as error:
        raise SemanticKnowledgePreparationError(str(error)) from error

    sources = _mapping(receipt.get("sources"), name="compiler sources")
    for name, pin_value in sources.items():
        pin = _mapping(pin_value, name=name)
        path = Path(_text(pin["path"], name=f"{name}.path"))
        digest_value = _text(pin["sha256"], name=f"{name}.sha256")
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise SemanticKnowledgePreparationError(
                f"cannot verify compiler source {name}"
            ) from error
        if actual != digest_value:
            raise SemanticKnowledgePreparationError(
                f"compiler source {name} SHA-256 differs"
            )
    namespace = _confined(
        data_root, _relative(registration["output_namespace"], name="output_namespace"),
        name="output_namespace",
    )
    release_path, completion_path = namespace / "release.json", namespace / "completion.json"
    if {release_path, completion_path} & {pin.path for pin in pins.values()}:
        raise SemanticKnowledgePreparationError("compiled release output aliases an input")
    snapshot_pin = {"relpath": pins["snapshot"].relpath, "sha256": snapshot.content_hash()}
    release = {
        "schema": _RELEASE_SCHEMA,
        "store_id": registration["store_id"], "store_role": registration["store_role"],
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "builder_policy_id": snapshot.builder_policy_id,
        "source": pins["compilation_receipt"].as_json(include_root=False),
    }
    release_raw = canonical_bytes(release)
    release_pin = {
        "relpath": release_path.relative_to(data_root.resolve()).as_posix(),
        "sha256": hashlib.sha256(release_raw).hexdigest(),
    }
    completion = {
        "schema": "saea-compiled-knowledge-store-completion-v1",
        "registration": {"relpath": registration_relpath,
                         "sha256": hashlib.sha256(registration_raw).hexdigest()},
        "compilation_receipt": pins["compilation_receipt"].as_json(include_root=False),
        "snapshot": snapshot_pin, "snapshot_file_sha256": pins["snapshot"].sha256,
        "release": release_pin, "source_partition_role": snapshot.source_partition_role,
        "tool_count": len(snapshot.values),
        "contacts": {"model": 0, "tool": 0, "scorer": 0},
    }
    completion_raw = canonical_bytes(completion)
    expected = ((release_path, release_raw), (completion_path, completion_raw))
    cache = _publish_exact_artifacts(expected)

    return {
        "cache": cache,
        "completion": completion,
        "completion_pin": {
            "relpath": completion_path.relative_to(data_root.resolve()).as_posix(),
            "sha256": hashlib.sha256(completion_raw).hexdigest(),
        },
    }


def prepare_semantic_knowledge_store(
    registration_path: Path,
    *,
    repo_root: Path,
    data_root: Path,
) -> Mapping[str, Any]:
    """Build authored knowledge or release an existing governed compiler snapshot."""

    registration_path = Path(registration_path)
    repo_root = Path(repo_root)
    data_root = Path(data_root)
    try:
        registration_raw = registration_path.read_bytes()
    except OSError as exc:
        raise SemanticKnowledgePreparationError("unable to read registration") from exc
    if _json(registration_raw, name="registration").get("schema") == "saea-governed-context-store-preparation-v1":
        from .governed_context_preparation import prepare_governed_context_store

        return prepare_governed_context_store(
            registration_path, registration_raw, repo_root=repo_root, data_root=data_root,
        )
    if _json(registration_raw, name="registration").get("schema") == COMPILED_REGISTRATION_SCHEMA:
        return _prepare_compiled_store(
            registration_path, registration_raw, repo_root=repo_root, data_root=data_root
        )
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
    scope = _roster(
        pins["construction_scope"],
        scope_raw,
        name="construction_scope",
        carrier=carrier,
        require_construction=True,
        repo_root=repo_root,
    )
    permitted = _roster(
        pins["permitted_roster"],
        permitted_raw,
        name="permitted_roster",
        carrier=carrier,
        require_construction=True,
        repo_root=repo_root,
    )
    if permitted.split_identity_hash != pins["source_identity"]:
        raise SemanticKnowledgePreparationError(
            "permitted roster split identity differs"
        )
    if not set(permitted.sample_ids).issubset(scope.sample_ids):
        raise SemanticKnowledgePreparationError(
            "permitted support roster is outside construction scope"
        )

    forbidden_records = []
    forbidden_ids: set[str] = set()
    for index, raw in enumerate(forbidden_raw):
        roster = _roster(
            pins["forbidden_rosters"][index],
            raw,
            name=f"forbidden_rosters[{index}]",
            carrier=carrier,
            require_construction=False,
            repo_root=repo_root,
        )
        forbidden_records.append(roster)
        forbidden_ids.update(roster.sample_ids)

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
                permitted_source_sample_ids=permitted.sample_ids,
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
        "source": pins["authored_source"].as_json(include_root=False),
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
            "roster_id": scope.roster_id,
            "roster_role": scope.roster_role,
            "split_role": scope.split_role,
            "split_identity_hash": scope.split_identity_hash,
            "sample_count": len(scope.sample_ids),
        },
        "exact_support_roster": {
            "roster_id": permitted.roster_id,
            "roster_role": permitted.roster_role,
            "split_role": permitted.split_role,
            "split_identity_hash": permitted.split_identity_hash,
            "sample_count": len(permitted.sample_ids),
        },
        "forbidden_rosters": [
            {
                "roster_id": roster.roster_id,
                "roster_role": roster.roster_role,
                "split_role": roster.split_role,
                "split_identity_hash": roster.split_identity_hash,
                "sample_count": len(roster.sample_ids),
            }
            for roster in forbidden_records
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

    cache = _publish_exact_artifacts(expected)

    return {
        "cache": cache,
        "completion": completion,
        "completion_pin": {
            "relpath": completion_relpath,
            "sha256": hashlib.sha256(completion_raw).hexdigest(),
        },
    }
