"""Governed public context preparation through shared pins, D1 checks and publication."""
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import re

from ..contracts import FrozenCoreGate, GateClosed
from ..data.lock import load_lock
from ..rails.errors import RailsError
from ..rails.governed_context_build import (
    GOVERNED_CONTEXT_BUILD_POLICY_ID, GOVERNED_CONTEXT_STORE_ROLES,
    GovernedContextBuildSpec, GovernedContextRecord, build_governed_context_snapshot,
)
from .evidence import evidence_file_relpath, conec_names_file_relpath
from .preparation import canonical_bytes, digest
from .semantic_knowledge_preparation import (
    SemanticKnowledgePreparationError as Error,
    _confined, _exact_keys, _json, _pin, _publish_exact_artifacts,
    _read_pin, _relative, _text,
)

REGISTRATION_SCHEMA = "saea-governed-context-store-preparation-v1"


def prepare_governed_context_store(
    registration_path: Path, registration_raw: bytes, *, repo_root: Path, data_root: Path,
):
    """Build legal public sources; never open a model, reference transcript or scorer."""
    repo_root, data_root = repo_root.resolve(), data_root.resolve()
    document = _json(registration_raw, name="governed registration")
    _exact_keys(document, {
        "schema", "registration_id", "carrier_lock_key", "source_partition_role",
        "store_id", "store_role", "builder_policy_id", "lexical_limit", "datasets_lock",
        "e0", "d1", "d1_evidence_supplement", "scope_sample_ids", "output_namespace",
    }, name="governed registration")
    if (
        document["schema"] != REGISTRATION_SCHEMA
        or document["carrier_lock_key"] != "earnings21-original"
        or document["source_partition_role"] != "external-governed"
        or document["builder_policy_id"] != GOVERNED_CONTEXT_BUILD_POLICY_ID
        or document["store_role"] not in GOVERNED_CONTEXT_STORE_ROLES
    ):
        raise Error("governed registration has an unsupported source or builder identity")
    for field in ("registration_id", "store_id"):
        _text(document[field], name=field, slug=field == "store_id")
    try:
        registration_relative = registration_path.resolve().relative_to(repo_root).as_posix()
    except ValueError as error:
        raise Error("registration must be confined to repo_root") from error
    scopes = document["scope_sample_ids"]
    if (
        not isinstance(scopes, list) or not scopes
        or any(not isinstance(s, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", s) is None
               for s in scopes)
        or len(scopes) != len(set(scopes))
    ):
        raise Error("scope_sample_ids must be unique safe source sample identifiers")
    namespace = _confined(
        data_root, _relative(document["output_namespace"], name="output_namespace"),
        name="output_namespace",
    )
    lock_pin = document["datasets_lock"]
    if not isinstance(lock_pin, dict) or set(lock_pin) != {"path", "sha256"}:
        raise Error("datasets_lock requires an absolute path and SHA-256")
    lock_path = Path(_text(lock_pin["path"], name="datasets_lock.path"))
    if not lock_path.is_absolute():
        raise Error("datasets_lock must address the existing absolute umbrella lock")
    lock_source = _pin(
        {"relpath": lock_path.name, "sha256": lock_pin["sha256"]},
        roots={"lock": lock_path.parent}, default_root="lock",
        allowed_roots=frozenset({"lock"}), name="datasets_lock",
    )
    _read_pin(lock_source, name="datasets_lock")
    lock = load_lock(lock_path)
    roots = {"repo": repo_root}
    pins = {field: _pin(document[field], roots=roots, default_root="repo",
                        allowed_roots=frozenset({"repo"}), name=field)
            for field in ("e0", "d1")}
    raw_pins = {field: _read_pin(pin, name=field) for field, pin in pins.items()}
    e0 = _json(raw_pins["e0"], name="e0")
    d1_entry = e0.get("deliverables", {}).get("d1_identity", {})
    if d1_entry.get("sha256") != pins["d1"].sha256:
        raise Error("E0 and D1 pins disagree")
    supplement = None
    if document["d1_evidence_supplement"] is not None:
        supplement = _pin(document["d1_evidence_supplement"], roots=roots, default_root="repo",
                          allowed_roots=frozenset({"repo"}), name="d1_evidence_supplement")
        _read_pin(supplement, name="d1_evidence_supplement")

    # Construct only the independent evidence identity rail. No model admission is requested.
    gate = FrozenCoreGate.for_study_repo(repo_root, data_root, data_root)
    gate = replace(
        gate, e0_receipt=pins["e0"].path, lock_path=lock_path,
        d1_evidence_supplement=None if supplement is None else supplement.path,
        d1_evidence_supplement_sha256=None if supplement is None else supplement.sha256,
    )
    role = document["store_role"]
    resolver = conec_names_file_relpath if role == "participant-roster" else evidence_file_relpath
    try:
        if gate._d1_identity_artifact_path().resolve() != pins["d1"].path.resolve():
            raise Error("E0 resolves a different D1 artifact")
        relpaths = {scope: resolver(lock, document["carrier_lock_key"], scope) for scope in scopes}
        gate.verify_evidence_identity(document["carrier_lock_key"], relpaths)
        consumed = {
            scope: _confined(data_root, relpath, name="governed source").read_bytes()
            for scope, relpath in relpaths.items()
        }
        gate.verify_evidence_content_identity(document["carrier_lock_key"], consumed, relpaths)
        records = tuple(GovernedContextRecord(
            source_id=f"conec://{role}/{scope}", scope_sample_id=scope, source_kind=role,
            source_sha256=hashlib.sha256(consumed[scope]).hexdigest(),
            content=consumed[scope].decode("utf-8"),
        ) for scope in sorted(scopes))
    except (GateClosed, OSError, UnicodeError, ValueError) as error:
        raise Error(f"governed source verification refused: {error}") from error
    source_rows = [{
        "source_id": record.source_id, "scope_sample_id": record.scope_sample_id,
        "source_kind": role, "source_relpath": relpaths[record.scope_sample_id],
        "source_sha256": record.source_sha256,
        "source_bytes": len(consumed[record.scope_sample_id]),
    } for record in records]
    identity = digest({
        "source_partition_role": "external-governed", "records": source_rows,
        "datasets_lock_sha256": lock_pin["sha256"],
    })
    try:
        snapshot = build_governed_context_snapshot(records, spec=GovernedContextBuildSpec(
            snapshot_id=document["registration_id"], source_split_identity_hash=identity,
            store_role=role, lexical_limit=document["lexical_limit"],
        ))
    except (TypeError, ValueError, RailsError) as error:
        raise Error(f"governed context builder refused: {error}") from error
    source = {
        "schema": "saea-governed-context-source-v1", "records": source_rows,
        "source_split_identity_hash": identity, "source_partition_role": "external-governed",
        "datasets_lock": lock_pin, "e0": document["e0"], "d1": document["d1"],
        "d1_evidence_supplement": document["d1_evidence_supplement"],
        "builder_policy_id": document["builder_policy_id"], "lexical_limit": document["lexical_limit"],
    }
    source_raw = canonical_bytes(source)
    source_path = namespace / "source.json"
    source_pin = {"relpath": str(source_path.relative_to(data_root)),
                  "sha256": hashlib.sha256(source_raw).hexdigest()}
    snapshot_raw = canonical_bytes(snapshot.frozen_json())
    snapshot_pin = {"relpath": str((namespace / "snapshot.json").relative_to(data_root)),
                    "sha256": snapshot.content_hash()}
    release = {
        "schema": "saea-knowledge-store-release-v1",
        "store_id": document["store_id"], "store_role": role,
        "snapshot_sha256": snapshot.content_hash(), "source_split_identity_hash": identity,
        "builder_policy_id": snapshot.builder_policy_id, "source": source_pin,
    }
    release_raw = canonical_bytes(release)
    release_pin = {"relpath": str((namespace / "release.json").relative_to(data_root)),
                   "sha256": hashlib.sha256(release_raw).hexdigest()}
    completion = {
        "schema": "saea-governed-context-store-completion-v1",
        "registration": {"relpath": registration_relative,
                         "sha256": hashlib.sha256(registration_raw).hexdigest()},
        "source": source_pin, "snapshot": snapshot_pin, "release": release_pin,
        "snapshot_file_sha256": hashlib.sha256(snapshot_raw).hexdigest(),
        "source_partition_role": "external-governed", "scope_count": len(scopes),
        "value_count": len(snapshot.values),
        "source_bytes": sum(row["source_bytes"] for row in source_rows),
        "contacts": {"model": 0, "tool": 0, "scorer": 0},
    }
    completion_raw = canonical_bytes(completion)
    expected = (
        (source_path, source_raw), (namespace / "snapshot.json", snapshot_raw),
        (namespace / "release.json", release_raw), (namespace / "completion.json", completion_raw),
    )
    input_paths = {registration_path.resolve(), lock_path.resolve(), *(p.path for p in pins.values())}
    input_paths.update(_confined(data_root, rel, name="governed source") for rel in relpaths.values())
    if supplement is not None:
        input_paths.add(supplement.path)
    if any(path.resolve() in input_paths for path, _ in expected):
        raise Error("governed context output aliases an input")
    for field, pin in pins.items():
        _read_pin(pin, name=field)
    _read_pin(lock_source, name="datasets_lock")
    if supplement is not None:
        _read_pin(supplement, name="d1_evidence_supplement")
    cache = _publish_exact_artifacts(expected)
    return {
        "cache": cache, "completion": completion,
        "completion_pin": {
            "relpath": str((namespace / "completion.json").relative_to(data_root)),
            "sha256": hashlib.sha256(completion_raw).hexdigest(),
        },
    }
