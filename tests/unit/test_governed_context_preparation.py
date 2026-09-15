"""CPU-only governed source preparation through the common knowledge entry."""
import hashlib

import pytest

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    SemanticKnowledgePreparationError, prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding


def _write(path, value, root=None):
    raw = value if isinstance(value, bytes) else canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"relpath": str(path.relative_to(root or path.parent)),
            "sha256": hashlib.sha256(raw).hexdigest()}


def world(tmp_path, role="participant-roster"):
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    lock_path = tmp_path / "datasets.lock.json"
    lock = {"datasets": [{"name": "conec", "local_subdir": "datasets/conec"}]}
    lock_pin = _write(lock_path, lock)
    layer = "e21_participant_names" if role == "participant-roster" else "e21_contexts"
    sources, manifest = {}, []
    for scope, name in (("call-a", "Jane Doe"), ("call-b", "John Roe")):
        raw = (name + " - CFO\nUnaffiliated Person\n").encode() if role == "participant-roster" else b"Revenue 2\nmargin 3\n1234 1\n"
        suffix = f"participant_names/{scope}.names.txt" if role == "participant-roster" else f"{scope}.txt"
        rel = "datasets/conec/earnings21/contexts/" + suffix
        sources[scope] = _write(data / rel, raw, data)
        manifest.append({"id": scope, "bytes": len(raw), "sha256": sources[scope]["sha256"]})
    d1 = _write(repo / "docs/receipts/artifacts/d1.json", {
        "carriers": {"conec": {"layers": {layer: {"manifest": manifest}}}},
    }, repo)
    e0 = _write(repo / "docs/receipts/e0-closure.json", {
        "deliverables": {"d1_identity": {"artifact": "artifacts/d1.json", "sha256": d1["sha256"]}},
    }, repo)
    registration = {
        "schema": "saea-governed-context-store-preparation-v1",
        "registration_id": "SYNTHETIC-GOVERNED-PREP",
        "carrier_lock_key": "earnings21-original",
        "source_partition_role": "external-governed",
        "store_id": role, "store_role": role,
        "builder_policy_id": "saea-governed-context-store-v1",
        "lexical_limit": 16,
        "datasets_lock": {"path": str(lock_path), "sha256": lock_pin["sha256"]},
        "e0": e0, "d1": d1, "d1_evidence_supplement": None,
        "scope_sample_ids": ["call-a", "call-b"],
        "output_namespace": f"knowledge/governed/{role}",
    }
    path = repo / "registration.json"
    _write(path, registration)
    return repo, data, path, registration, sources


@pytest.mark.parametrize("role", ["participant-roster", "document-lexicon"])
def test_governed_store_cold_warm_release_and_scoped_provenance(tmp_path, role):
    repo, data, path, registration, sources = world(tmp_path, role)
    result = prepare_semantic_knowledge_store(path, repo_root=repo, data_root=data)
    assert result["cache"] == "cold"
    completion = result["completion"]
    assert completion["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    binding = load_knowledge_store_binding({"knowledge_stores": {role: {
        "store_role": role, "snapshot": completion["snapshot"], "release": completion["release"],
    }}}, data_root=data)
    snapshot = binding.store(role).snapshot
    assert snapshot.source_partition_role == "external-governed"
    assert len(snapshot.facets) == len(snapshot.values) == 2
    assert {f.representation for f in snapshot.facets} == set(sources)
    assert set(snapshot.source_sample_ids).isdisjoint(sources)
    assert all(v.task_target is None and v.prior_score is None for v in snapshot.values)
    if role == "participant-roster":
        assert "Jane Doe" in snapshot.values[0].content
        assert "Unaffiliated Person" in snapshot.values[0].content
    else:
        assert all("1234" not in v.content for v in snapshot.values)
    before = {p.name: p.read_bytes() for p in (data / registration["output_namespace"]).glob("*.json")}
    warm = prepare_semantic_knowledge_store(path, repo_root=repo, data_root=data)
    assert warm["cache"] == "warm"
    assert before == {p.name: p.read_bytes() for p in (data / registration["output_namespace"]).glob("*.json")}


@pytest.mark.parametrize("tamper", ["bytes", "unknown-call", "carrier", "source-role", "d1-pin", "lock-pin", "escape"])
def test_governed_preparation_refuses_before_publication(tmp_path, tamper):
    repo, data, path, registration, sources = world(tmp_path)
    if tamper == "bytes":
        (data / sources["call-a"]["relpath"]).write_bytes(b"Changed - CEO\n")
    elif tamper == "unknown-call":
        registration["scope_sample_ids"].append("call-c")
    elif tamper == "carrier":
        registration["carrier_lock_key"] = "earnings22-original"
    elif tamper == "source-role":
        registration["source_partition_role"] = "train"
    elif tamper == "d1-pin":
        registration["d1"]["sha256"] = "0" * 64
    elif tamper == "lock-pin":
        registration["datasets_lock"]["sha256"] = "0" * 64
    else:
        registration["scope_sample_ids"] = ["../references"]
    _write(path, registration)
    with pytest.raises(SemanticKnowledgePreparationError):
        prepare_semantic_knowledge_store(path, repo_root=repo, data_root=data)
    assert not (data / registration["output_namespace"]).exists()


def test_changed_configuration_cannot_overwrite_existing_outputs(tmp_path):
    repo, data, path, registration, _ = world(tmp_path, "document-lexicon")
    prepare_semantic_knowledge_store(path, repo_root=repo, data_root=data)
    registration["lexical_limit"] = 1
    _write(path, registration)
    with pytest.raises(SemanticKnowledgePreparationError, match="collision"):
        prepare_semantic_knowledge_store(path, repo_root=repo, data_root=data)
