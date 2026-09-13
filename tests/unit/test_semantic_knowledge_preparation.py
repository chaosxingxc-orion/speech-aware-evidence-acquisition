from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.driver.cli import main
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    SemanticKnowledgePreparationError,
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    INTENT_BOUNDARY_BUILD_POLICY_ID,
    SLOT_CONTRACT_BUILD_POLICY_ID,
)


def _write(path: Path, document: object) -> dict[str, str]:
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {"relpath": path.name, "sha256": hashlib.sha256(raw).hexdigest()}


def _roster(
    identity: str, ids: tuple[str, ...], *, roster_id: str
) -> dict[str, object]:
    return {
        "schema": "saea-semantic-knowledge-roster-v1",
        "roster_id": roster_id,
        "carrier_lock_key": "slurp",
        "roster_role": "construction",
        "split_identity_hash": identity,
        "sample_ids": list(ids),
    }


def _intent(intent_id: str, sample_id: str) -> dict[str, object]:
    return {
        "intent_id": intent_id,
        "activation_boundary": ["An illustrative observable cue."],
        "confusable_exclusions": [
            {
                "neighboring_intent_id": "other_intent",
                "distinction": "An illustrative distinction.",
            }
        ],
        "uncertainty_behavior": "Preserve uncertainty when evidence is insufficient.",
        "limitations": ["This illustrative value does not determine slots."],
        "source_support": {
            "source_sample_ids": [sample_id],
            "provenance_refs": [f"synthetic:{sample_id}"],
        },
    }


def _slot(slot_id: str, sample_id: str) -> dict[str, object]:
    return {
        "slot_id": slot_id,
        "intent_bindings": [
            {"intent_id": "intent_one", "semantic_role": "An illustrative role."}
        ],
        "extraction_cues": ["An illustrative extraction cue."],
        "admissible_formats": ["An illustrative format."],
        "missing_behavior": "Leave the slot absent when unsupported.",
        "ambiguity_behavior": "Preserve ambiguity when evidence is insufficient.",
        "limitations": ["This illustrative value does not determine intent."],
        "source_support": {
            "source_sample_ids": [sample_id],
            "provenance_refs": [f"synthetic:{sample_id}"],
        },
    }


def _world(tmp_path: Path, *, builder: str = INTENT_BOUNDARY_BUILD_POLICY_ID):
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir(parents=True)
    data_root.mkdir(parents=True)
    scope_identity, support_identity = "a" * 64, "b" * 64
    scope_pin = _write(
        repo_root / "scope.json",
        _roster(scope_identity, ("train-1", "train-2", "train-3"), roster_id="scope"),
    )
    support_pin = _write(
        repo_root / "support.json",
        _roster(support_identity, ("train-1", "train-2"), roster_id="support"),
    )
    forbidden_pin = _write(
        repo_root / "forbidden.json",
        _roster("c" * 64, ("forbidden-1",), roster_id="forbidden"),
    )
    rows = (
        [_slot("slot_one", "train-1"), _slot("slot_two", "train-2")]
        if builder == SLOT_CONTRACT_BUILD_POLICY_ID
        else [_intent("intent_one", "train-1"), _intent("intent_two", "train-2")]
    )
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": builder,
        "source_split_identity_hash": support_identity,
        "rows": rows,
    }
    source_pin = _write(data_root / "authored.json", source)
    registration = {
        "schema": "saea-authored-semantic-knowledge-preparation-v1",
        "registration_id": "SYNTHETIC-SEMANTIC-PREP-V1",
        "carrier_lock_key": "slurp",
        "source_partition_role": "train",
        "source_split_identity_hash": support_identity,
        "builder_policy_id": builder,
        "store_id": "intent-boundaries",
        "store_role": "intent-boundaries",
        "authored_source": source_pin,
        "construction_scope": scope_pin,
        "permitted_roster": support_pin,
        "forbidden_rosters": [forbidden_pin],
        "output_namespace": "knowledge/semantic/intent-boundaries-v1",
    }
    registration_path = repo_root / "registration.json"
    registration_path.write_bytes(canonical_bytes(registration))
    return repo_root, data_root, registration_path, registration


@pytest.mark.parametrize(
    "builder", [INTENT_BOUNDARY_BUILD_POLICY_ID, SLOT_CONTRACT_BUILD_POLICY_ID]
)
def test_builds_create_only_store_and_round_trips_through_named_store_loader(
    tmp_path, builder
):
    repo_root, data_root, registration_path, registration = _world(
        tmp_path, builder=builder
    )
    if builder == SLOT_CONTRACT_BUILD_POLICY_ID:
        registration["store_id"] = registration["store_role"] = "slot-contracts"
        registration_path.write_bytes(canonical_bytes(registration))
    result = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )
    assert result["cache"] == "cold"
    completion = result["completion"]
    assert completion["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    store_id = registration["store_id"]
    config = {
        "knowledge_stores": {
            store_id: {
                "store_role": registration["store_role"],
                "snapshot": completion["snapshot"],
                "release": completion["release"],
            }
        }
    }
    binding = load_knowledge_store_binding(config, data_root=data_root)
    assert binding.store_ids == (store_id,)
    assert binding.snapshot_for(store_id).source_sample_ids == ("train-1", "train-2")


def test_identical_binding_reuses_validated_outputs_without_rewriting(tmp_path):
    repo_root, data_root, registration_path, _ = _world(tmp_path)
    first = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )
    paths = [
        data_root / first["completion"][name]["relpath"]
        for name in ("snapshot", "release")
    ]
    paths.append(data_root / "knowledge/semantic/intent-boundaries-v1/completion.json")
    before = [(path.stat().st_ino, path.stat().st_mtime_ns) for path in paths]
    second = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )
    assert second["cache"] == "warm"
    assert before == [(path.stat().st_ino, path.stat().st_mtime_ns) for path in paths]


@pytest.mark.parametrize(
    "target", ["authored_source", "construction_scope", "permitted_roster", "forbidden"]
)
def test_changed_input_pin_refuses_before_outputs(tmp_path, target):
    repo_root, data_root, registration_path, registration = _world(tmp_path)
    pin = (
        registration["forbidden_rosters"][0]
        if target == "forbidden"
        else registration[target]
    )
    pin["sha256"] = "f" * 64
    registration_path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError, match="SHA-256"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )
    assert not (data_root / registration["output_namespace"]).exists()


def test_wrong_source_identity_unknown_builder_and_support_outside_scope_refuse(
    tmp_path,
):
    repo_root, data_root, registration_path, registration = _world(tmp_path)
    registration["source_split_identity_hash"] = "d" * 64
    registration_path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError, match="identity"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )

    repo_root, data_root, registration_path, _ = _world(
        tmp_path / "unknown", builder="missing-builder"
    )
    with pytest.raises(SemanticKnowledgePreparationError, match="builder"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )

    repo_root, data_root, registration_path, registration = _world(tmp_path / "outside")
    registration["permitted_roster"] = _write(
        repo_root / "support.json",
        _roster("b" * 64, ("train-1", "outside"), roster_id="support"),
    )
    source = json.loads((data_root / "authored.json").read_text())
    source["rows"][1] = _intent("intent_two", "outside")
    registration["authored_source"] = _write(data_root / "authored.json", source)
    registration_path.write_bytes(canonical_bytes(registration))
    with pytest.raises(
        SemanticKnowledgePreparationError, match="outside construction scope"
    ):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )


def test_forbidden_support_and_output_collision_refuse(tmp_path):
    repo_root, data_root, registration_path, registration = _world(tmp_path)
    registration["forbidden_rosters"] = [
        _write(
            repo_root / "forbidden.json",
            _roster("c" * 64, ("train-2",), roster_id="forbidden"),
        )
    ]
    registration_path.write_bytes(canonical_bytes(registration))
    with pytest.raises(SemanticKnowledgePreparationError, match="forbidden"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )

    repo_root, data_root, registration_path, registration = _world(
        tmp_path / "collision"
    )
    output = data_root / registration["output_namespace"]
    output.mkdir(parents=True)
    (output / "snapshot.json").write_text("different", encoding="utf-8")
    with pytest.raises(SemanticKnowledgePreparationError, match="collision"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )
    assert (output / "snapshot.json").read_text() == "different"


def test_changed_registration_cannot_reuse_existing_namespace(tmp_path):
    repo_root, data_root, registration_path, registration = _world(tmp_path)
    first = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )
    completion_path = data_root / first["completion_pin"]["relpath"]
    before = completion_path.read_bytes()
    registration["registration_id"] = "SYNTHETIC-SEMANTIC-PREP-V2"
    registration_path.write_bytes(canonical_bytes(registration))

    with pytest.raises(SemanticKnowledgePreparationError, match="collision"):
        prepare_semantic_knowledge_store(
            registration_path, repo_root=repo_root, data_root=data_root
        )
    assert completion_path.read_bytes() == before


def test_cli_dispatches_shared_preparation_without_contacts(tmp_path, capsys):
    repo_root, data_root, registration_path, _ = _world(tmp_path)
    assert (
        main(
            [
                "prepare-semantic-knowledge",
                "--registration",
                str(registration_path),
                "--repo-root",
                str(repo_root),
                "--data-root",
                str(data_root),
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["completion"]["contacts"]["model"] == 0
