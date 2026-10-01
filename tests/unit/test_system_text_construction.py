"""Actual generation, instruction custody and the shared semantic release join."""
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.system_text_construction import (
    materialize_slot_construction, verify_released_slot_construction,
)
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import SLOT_CONTRACT_BUILD_POLICY_ID
from test_semantic_knowledge_edits import rows, contract, proposal
from test_semantic_knowledge_preparation import _write, _roster

INSTRUCTION = "Revise source-supported slot values while preserving routing."


def generation(tmp_path, monkeypatch):
    base = rows()
    spec = contract(base)
    pin = _write(tmp_path / "generation.json", {"status": "COMPLETED"})
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "result_kind": "artifact", "plan": {"split_role": "discovery"}},
        attempt_state="FINALIZED",
        outputs_rows=[{"sample_id": "slurp:train:new", "request_id": "generator", "text": json.dumps(proposal(base))}],
        trace_records={"generator/request": {"payload": {"sample_id": "slurp:train:new", "task_instruction": INSTRUCTION}}},
    )
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle", lambda _: bundle)
    kwargs = dict(base_rows=base, contract=spec, generation_pin=pin, instruction=INSTRUCTION, data_root=tmp_path)
    return bundle, kwargs


def test_materializes_actual_output_and_keeps_all_feedback_ancestry(tmp_path, monkeypatch):
    _, kwargs = generation(tmp_path, monkeypatch)
    result = materialize_slot_construction(**kwargs)
    assert result["rows"][0]["extraction_cues"] == proposal(rows())["edits"][0]["replacement"]
    assert result["optimizer_construction_sample_ids"] == ["slurp:train:new", "slurp:train:tie"]


@pytest.mark.parametrize("defect", ["unsealed", "test", "instruction", "unexecuted", "base"])
def test_rejects_unexecuted_or_unbound_construction(tmp_path, monkeypatch, defect):
    bundle, kwargs = generation(tmp_path, monkeypatch)
    if defect == "unsealed":
        bundle.attempt_state = "ABORTED"
    elif defect == "test":
        bundle.outputs_rows[0]["sample_id"] = "slurp:test:future"
    elif defect == "instruction":
        kwargs["instruction"] = "A new instruction that was never executed."
    elif defect == "unexecuted":
        bundle.trace_records["generator/request"]["payload"]["task_instruction"] = "Unrelated instruction."
        bundle.trace_records["unrelated/response"] = {"payload": {"task_instruction": INSTRUCTION}}
    else:
        p = proposal(rows())
        p["base_rows_sha256"] = "0" * 64
        bundle.outputs_rows[0]["text"] = json.dumps(p)
    with pytest.raises(PolicyError):
        materialize_slot_construction(**kwargs)


def test_rechecks_actual_shared_release_not_snapshot_file_hash(tmp_path, monkeypatch):
    data, repo = tmp_path / "data", tmp_path / "repo"
    data.mkdir()
    repo.mkdir()
    _, kwargs = generation(data, monkeypatch)
    result = materialize_slot_construction(**kwargs)
    support = _roster(tuple(result["rows"][0]["source_support"]["source_sample_ids"]), roster_id="support")
    roster_pin = _write(repo / "support.json", support)
    forbidden_pin = _write(repo / "forbidden.json", _roster(("slurp:train:held",), roster_id="held", roster_role="evaluation"))
    authored_pin = _write(data / "authored.json", {
        "schema": "saea-authored-semantic-knowledge-source-v1", "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "source_split_identity_hash": support["split_identity_hash"], "rows": result["rows"],
    })
    registration = {
        "schema": "saea-authored-semantic-knowledge-preparation-v1", "registration_id": "SYNTHETIC-TEXT-SEARCH-V1",
        "carrier_lock_key": "slurp", "source_partition_role": "train",
        "source_split_identity_hash": support["split_identity_hash"], "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "store_id": "slot-contracts", "store_role": "slot-contracts", "authored_source": authored_pin,
        "construction_scope": roster_pin, "permitted_roster": roster_pin, "forbidden_rosters": [forbidden_pin],
        "output_namespace": "knowledge/semantic/synthetic-slot-contracts-v1",
    }
    registration_pin = _write(repo / "registration.json", registration)
    prepared = prepare_semantic_knowledge_store(repo / "registration.json", repo_root=repo, data_root=data)
    link = {"schema": "saea-system-text-construction-link-v1", "instruction_sha256": content_hash(INSTRUCTION),
        "knowledge": {k: prepared["completion"][k] for k in ("snapshot", "release")},
        "base_rows": _write(data / "base.json", kwargs["base_rows"]),
        "edit_contract": _write(data / "contract.json", kwargs["contract"]),
        "generation": kwargs["generation_pin"], "registration": registration_pin,
        "completion": prepared["completion_pin"]}
    verified = verify_released_slot_construction(link, instruction=INSTRUCTION, data_root=data, repo_root=repo)
    assert verified == result
    authored = json.loads((data / "authored.json").read_text())
    authored["rows"][0]["missing_behavior"] = "This was never generated."
    registration["authored_source"] = _write(data / "authored.json", authored)
    link["registration"] = _write(repo / "registration.json", registration)
    with pytest.raises(PolicyError, match="differs from generated"):
        verify_released_slot_construction(link, instruction=INSTRUCTION, data_root=data, repo_root=repo)
