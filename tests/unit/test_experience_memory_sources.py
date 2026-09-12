"""Real sealed synthetic sources govern corrective-memory provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
import test_reward_links as reward_fixtures

from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability, ExperienceRecord, SourceRef, ValidationBinding,
    load_experience_memory_manifest,
)
from speech_aware_evidence_acquisition.rails.reward_link_io import (
    REWARD_LINK_ARTIFACT_CONFIG_SCHEMA, build_reward_link_artifact,
    read_verified_reward_link_artifact,
)
from speech_aware_evidence_acquisition.rails.experience_memory_sources import (
    MemorySourceVerificationError, load_verified_memory_sources,
    prepare_experience_memory_sources, reward_link_source_ref,
)

pytest_plugins = ("test_bundle",)
completed_source = reward_fixtures.completed_source
slurp_source = reward_fixtures.slurp_source


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def source_world(slurp_source, tmp_path):
    manifest, receipt, roster, projection, _ = slurp_source
    config = {
        "schema": REWARD_LINK_ARTIFACT_CONFIG_SCHEMA,
        "manifest": {"path": str(manifest), "sha256": _sha(manifest)},
        "complete_score_receipt": {
            "path": str(receipt.path), "sha256": receipt.sha256, "cell_id": receipt.cell_id,
        },
        "construction_roster": {"path": str(roster), "sha256": _sha(roster)},
        "projection": projection.as_json(),
    }
    artifact = tmp_path / "reward-links.json"
    pin = build_reward_link_artifact(config, artifact)
    links = read_verified_reward_link_artifact(config, artifact)
    return roster, links, [{"config": config, "artifact": pin}]


def _catalog(tmp_path, roster, links, **changes):
    record = ExperienceRecord.create(
        record_id="source-bound-rule", revision=1, kind="conditional-rule",
        train_construction_sha256=_sha(roster), source=links[0].source,
        applicability=Applicability(
            ("slurp-slot-slu",), ("revise",), ("supply", "use"),
            ("state:prior-response-present",), (),
        ),
        diagnosis="Available observations disagree.",
        guidance="Inspect the conflicting observation before revising.",
        limitations=("A conflict does not establish which answer is correct.",),
        supporting_source_refs=(reward_link_source_ref(links[0]),),
        contradicting_source_refs=(reward_link_source_ref(links[1]),),
        validation=ValidationBinding("admitted", "7" * 64, "8" * 64, "9" * 64, "a" * 64),
    )
    if changes:
        doc = record.unsigned_json()
        doc.update(changes)
        record = ExperienceRecord.from_unsigned_json(doc)
    path = tmp_path / "memory.json"
    path.write_text(json.dumps({
        "schema": "saea-experience-memory-manifest-v1", "memory_id": "verified-memory",
        "memory_version": 1, "construction_partition_role": "train",
        "train_construction_sha256": _sha(roster), "records": [record.as_json()],
    }))
    return load_experience_memory_manifest(
        path, expected_sha256=_sha(path), expected_train_construction_sha256=_sha(roster),
        expected_train_sample_ids=tuple(link.source.source_sample_id for link in links),
    )


def test_real_verified_sources_create_outcome_free_proof_and_preserve_archives(source_world, tmp_path):
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    paths = [Path(bindings[0]["artifact"]["path"]), roster]
    before = {path: path.read_bytes() for path in paths}
    output = tmp_path / "source-proof.json"

    prepare_experience_memory_sources(catalog, bindings, output)
    proof = load_verified_memory_sources(catalog, output, expected_sha256=_sha(output))

    assert proof["status"] == "source-verified"
    assert proof["records"][0]["source"] == links[0].source.as_json()
    assert proof["records"][0]["supporting_link_sha256s"] == [links[0].link_sha256]
    assert proof["records"][0]["contradicting_link_sha256s"] == [links[1].link_sha256]
    for forbidden in ("native_score_vector", "ordered_events", "synthetic-answer", "gold"):
        assert forbidden not in output.read_text()
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert catalog.records[0].validation.status == "admitted"


@pytest.mark.parametrize("field", ["supporting_source_refs", "contradicting_source_refs"])
@pytest.mark.parametrize("kind", ["unknown", "alias"])
def test_secondary_reference_requires_real_link_membership(source_world, tmp_path, field, kind):
    roster, links, bindings = source_world
    ref = (SourceRef("reward-link:" + "f" * 64, "f" * 64) if kind == "unknown"
           else SourceRef("claimed-train-alias", links[0].link_sha256))
    catalog = _catalog(tmp_path, roster, links, **{field: [ref.as_json()]})
    with pytest.raises(MemorySourceVerificationError, match="reference"):
        prepare_experience_memory_sources(catalog, bindings, tmp_path / "rejected.json")
    assert not (tmp_path / "rejected.json").exists()


@pytest.mark.parametrize("field", [
    "trajectory_sha256", "action_sha256", "response_sha256", "outcome_sha256",
])
def test_primary_source_requires_full_authoritative_match(source_world, tmp_path, field):
    roster, links, bindings = source_world
    source = replace(links[0].source, **{field: "f" * 64})
    catalog = _catalog(tmp_path, roster, links, source=source.as_json())
    with pytest.raises(MemorySourceVerificationError, match="primary source"):
        prepare_experience_memory_sources(catalog, bindings, tmp_path / "rejected.json")


def test_source_artifact_tamper_cannot_be_hidden_by_recomputed_outer_pin(source_world, tmp_path):
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    artifact = Path(bindings[0]["artifact"]["path"])
    doc = json.loads(artifact.read_text())
    doc["links"][0]["source"]["outcome_sha256"] = "f" * 64
    artifact.write_text(json.dumps(doc))
    bindings[0]["artifact"]["sha256"] = _sha(artifact)
    with pytest.raises(MemorySourceVerificationError, match="verified|hash|authoritative"):
        prepare_experience_memory_sources(catalog, bindings, tmp_path / "rejected.json")


def test_runtime_proof_load_never_reopens_authoritative_scores(source_world, tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.rails.reward_link_io as reward_io
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    output = tmp_path / "source-proof.json"
    prepare_experience_memory_sources(catalog, bindings, output)
    Path(bindings[0]["config"]["manifest"]["path"]).unlink()
    def forbidden(*args, **kwargs):
        raise AssertionError("Answering runtime opened offline reward sources")
    monkeypatch.setattr(reward_io, "read_verified_reward_link_artifact", forbidden)
    assert load_verified_memory_sources(
        catalog, output, expected_sha256=_sha(output),
    )["status"] == "source-verified"


def test_receipt_cannot_rebind_to_different_memory(source_world, tmp_path):
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    output = tmp_path / "source-proof.json"
    prepare_experience_memory_sources(catalog, bindings, output)
    changed = _catalog(tmp_path, roster, links, guidance="Keep the original answer.")
    with pytest.raises(MemorySourceVerificationError, match="identity|binding"):
        load_verified_memory_sources(changed, output, expected_sha256=_sha(output))


def test_duplicate_binding_is_not_independent_source_evidence(source_world, tmp_path):
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    with pytest.raises(MemorySourceVerificationError, match="duplicate"):
        prepare_experience_memory_sources(catalog, bindings * 2, tmp_path / "rejected.json")


def test_other_construction_roster_cannot_supply_training_evidence(source_world, tmp_path):
    from speech_aware_evidence_acquisition.core.roster import RosterItem, freeze_roster, write_roster
    import copy
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    other = tmp_path / "other-construction.json"
    write_roster(freeze_roster(
        carrier_lock_key="slurp", roster_id="other-construction", roster_role="construction",
        split_role="discovery", seed=7, per_stratum=len(links),
        candidates=[RosterItem(link.source.source_sample_id, "synthetic") for link in links],
    ), other)
    config = copy.deepcopy(bindings[0]["config"])
    config["construction_roster"] = {"path": str(other), "sha256": _sha(other)}
    pin = build_reward_link_artifact(config, tmp_path / "other-rewards.json")
    with pytest.raises(MemorySourceVerificationError, match="construction"):
        prepare_experience_memory_sources(
            catalog, [{"config": config, "artifact": pin}], tmp_path / "rejected.json",
        )


def test_real_source_proof_enters_live_loader_without_archived_score_access(source_world, tmp_path):
    import shutil
    from speech_aware_evidence_acquisition.rails.experience_memory_runtime import (
        load_experience_memory_binding,
    )
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    proof = tmp_path / "source-proof.json"
    prepare_experience_memory_sources(catalog, bindings, proof)
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps({
        "schema": "saea-experience-memory-admission-v2", "status": "admitted",
        "manifest_sha256": catalog.manifest_sha256,
        "construction_roster_sha256": _sha(roster),
        "admitted_record_sha256s": [record.record_sha256 for record in catalog.records],
        "source_verification_sha256": _sha(proof),
    }))
    frozen_roster = tmp_path / "train-roster.json"
    shutil.copyfile(roster, frozen_roster)
    config = {"experience_memory": {
        "manifest": {"relpath": "memory.json", "sha256": catalog.manifest_sha256},
        "construction_roster": {"repo_relpath": frozen_roster.name, "sha256": _sha(roster)},
        "admission": {"relpath": admission.name, "sha256": _sha(admission)},
        "source_verification": {"relpath": proof.name, "sha256": _sha(proof)},
        "task_id": "slurp-slot-slu", "component_tags": ["supply", "use"], "max_records": 1,
    }}
    Path(bindings[0]["config"]["manifest"]["path"]).unlink()
    Path(bindings[0]["config"]["complete_score_receipt"]["path"]).unlink()
    Path(bindings[0]["artifact"]["path"]).unlink()
    loaded = load_experience_memory_binding(
        config, repo_root=tmp_path, data_root=tmp_path, carrier_lock_key="slurp",
    )
    assert loaded.catalog.records == catalog.records
    assert loaded.source_verification_sha256 == _sha(proof)


def test_artifact_replacement_between_pin_and_authoritative_read_is_refused(source_world, tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.rails.reward_link_io as reward_io
    roster, links, bindings = source_world
    catalog = _catalog(tmp_path, roster, links)
    artifact = Path(bindings[0]["artifact"]["path"])
    verified_read = reward_io.read_verified_reward_link_artifact
    def swap_valid_encoding(config, path):
        # Both encodings rebuild to the same valid links, but only the original
        # bytes are pinned. Verification must name the bytes actually consumed.
        artifact.write_text(json.dumps(json.loads(artifact.read_text()), indent=2))
        return verified_read(config, path)
    monkeypatch.setattr(reward_io, "read_verified_reward_link_artifact", swap_valid_encoding)
    with pytest.raises(MemorySourceVerificationError, match="changed|hash"):
        prepare_experience_memory_sources(catalog, bindings, tmp_path / "rejected.json")
    assert not (tmp_path / "rejected.json").exists()
