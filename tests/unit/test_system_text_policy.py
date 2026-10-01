"""Whole-policy compilation and isolation; no model contacts or task labels."""
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal,
    compile_system_text_policy, cumulative_sources, assert_roster_disjoint, apply_text_proposal,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash

ROOT = Path(__file__).resolve().parents[2]
BASE = "configs/baseline/slurp-native-stage3-knowledge-opportunity-c-v1.json"


def seed_document():
    baseline = json.loads((ROOT / BASE).read_text())
    return {
        "schema": "saea-system-text-policy-bundle-v1", "parent_ids": [],
        "seed_config_sha256": content_hash(baseline),
        "construction_instruction": "Preserve source-supported slot boundaries and uncertainty.",
        "role_text": {r: (ROOT / "configs" / baseline["phase_material"][r]["instruction_template"]).read_text()
                      for r in ("solver", "reviewer", "planner")},
        "supply": {"mode": "targeted", "value_limit": 2},
        "knowledge": {"snapshot": baseline["knowledge_stores"]["slot-contracts"]["snapshot"],
                      "release": baseline["knowledge_stores"]["slot-contracts"]["release"]},
        "construction_receipt": None,
        "cumulative_sources": [{"kind": "knowledge", "sha256": "a" * 64,
                                "sample_ids": ["slurp:train:900:audio-1"]}],
        "optimizer_experience": [],
    }


def test_bundle_is_immutable_and_ancestry_cannot_shrink():
    raw = seed_document()
    bundle = SystemTextPolicyBundle.from_json(raw)
    raw["role_text"]["solver"] = "Changed outside the bundle."
    assert bundle.as_json()["role_text"]["solver"] != raw["role_text"]["solver"]
    more = [{"kind": "feedback", "sha256": "b" * 64, "sample_ids": ["slurp:train:2"]}]
    sources = cumulative_sources([bundle], more)
    assert len(sources) == 2
    with pytest.raises(PolicyError, match="overlap"):
        assert_roster_disjoint(sources, ["slurp:train:900:audio-2"])


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(scorer="different"),
    lambda d: d["supply"].update(value_limit=3),
    lambda d: d["supply"].update(retriever="new"),
    lambda d: d["cumulative_sources"][0].update(sample_ids=["slurp:test:1"]),
    lambda d: d["role_text"].update(perception="Change intent selection."),
])
def test_closed_edit_surface(mutation):
    raw = seed_document()
    mutation(raw)
    with pytest.raises(PolicyError):
        SystemTextPolicyBundle.from_json(raw)


def test_joint_compile_and_off_preserve_shared_executor(tmp_path):
    baseline = json.loads((ROOT / BASE).read_text())
    raw = seed_document()
    raw["role_text"]["solver"] += "\nUse relevant slot material conservatively.\n"
    raw["role_text"]["reviewer"] += "\nIdentify uncertain extraction boundaries.\n"
    raw["supply"]["value_limit"] = 1
    bundle = SystemTextPolicyBundle.from_json(raw)
    assert compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=tmp_path,
                                      enabled=False) == baseline
    result = compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=tmp_path)
    assert result["policy"] == baseline["policy"]
    assert result["scorers"] == baseline["scorers"]
    assert result["phase_material"]["perception"] == baseline["phase_material"]["perception"]
    assert result["phase_tools"]["planner"]["knowledge_value_limit"] == 1
    assert result["phase_tools"]["planner"]["max_calls_per_sample"] == 1
    assert result["native_episode"]["max_revisions"] == 1
    assert result["phase_material"]["solver"]["instruction_template"] != baseline["phase_material"]["solver"]["instruction_template"]
    from speech_aware_evidence_acquisition.rails.consumption_module import verify_declared_module
    verify_declared_module(result["native_episode"]["consumption_module"], result, repo_root=ROOT)


def test_construction_edit_requires_materialized_successor():
    parent = SystemTextPolicyBundle.from_json(seed_document())
    doc = parent.as_json()
    doc["parent_ids"] = [parent.bundle_id]
    doc["construction_instruction"] += " Explain adjacent types."
    with pytest.raises(PolicyError, match="materialized"):
        SystemTextPolicyBundle.from_json(doc, parents=[parent])


def test_proposal_cannot_smuggle_permission_or_scorer():
    proposal = {"schema": "saea-text-policy-update-proposal-v1", "branch": "L", "round": 1,
                "slot": 1, "parent_ids": ["a" * 64], "changes": {"scorers": []},
                "rationale": "Improve final quality.", "hypotheses": [], "evidence": []}
    with pytest.raises(PolicyError, match="editable"):
        TextPolicyUpdateProposal.from_json(proposal)


def test_joint_proposal_retains_feedback_ancestry_and_requires_build_for_values():
    parent = SystemTextPolicyBundle.from_json(seed_document())
    d = {"schema": "saea-text-policy-update-proposal-v1", "branch": "L", "round": 1,
         "slot": 1, "parent_ids": [parent.bundle_id],
         "changes": {"role_text": {"solver": "Use the recorded speech evidence and relevant slot definitions."},
                     "supply": {"mode": "reread", "value_limit": 1}},
         "rationale": "Test a joint revision.", "hypotheses": [], "evidence": []}
    proposal = TextPolicyUpdateProposal.from_json(d)
    feedback_sources = [{"kind": "feedback", "sha256": "b" * 64, "sample_ids": ["slurp:train:1"]}]
    child = apply_text_proposal(proposal, parents=[parent], added_sources=feedback_sources)
    assert child.as_json()["supply"]["mode"] == "reread"
    assert len(child.as_json()["cumulative_sources"]) == 2
    with pytest.raises(PolicyError, match="overlap"):
        assert_roster_disjoint(child.as_json()["cumulative_sources"], ["slurp:train:1:second-recording"])
    from test_semantic_knowledge_edits import proposal as edit_proposal, rows
    d["changes"]["slot_value_edits"] = edit_proposal(rows())
    with pytest.raises(PolicyError, match="construction"):
        apply_text_proposal(TextPolicyUpdateProposal.from_json(d), parents=[parent], added_sources=feedback_sources)
def test_new_knowledge_compilation_verifies_materialized_join_and_all_sources(tmp_path, monkeypatch):
    import hashlib
    from types import SimpleNamespace
    raw = seed_document()
    raw["knowledge"] = {k: {"relpath": f"new/{k}.json", "sha256": "d" * 64} for k in ("snapshot", "release")}
    receipt = {"schema": "saea-system-text-construction-link-v1",
               "instruction_sha256": content_hash(raw["construction_instruction"]), "knowledge": raw["knowledge"]}
    data = json.dumps(receipt).encode()
    (tmp_path / "receipt.json").write_bytes(data)
    raw["construction_receipt"] = {"relpath": "receipt.json", "sha256": hashlib.sha256(data).hexdigest()}
    raw["cumulative_sources"].append({"kind": "construction", "sha256": "e" * 64, "sample_ids": ["slurp:train:new"]})
    monkeypatch.setattr("speech_aware_evidence_acquisition.rails.system_text_construction.verify_released_slot_construction",
                        lambda *a, **k: {"optimizer_construction_sample_ids": ["slurp:train:new"]})
    monkeypatch.setattr("speech_aware_evidence_acquisition.rails.knowledge_stores.load_knowledge_store_binding",
        lambda *a, **k: SimpleNamespace(stores={"slot-contracts": SimpleNamespace(snapshot=SimpleNamespace(
            values=[SimpleNamespace(source_sample_ids=["slurp:train:new"])]))}))
    baseline = json.loads((ROOT / BASE).read_text())
    bundle = SystemTextPolicyBundle.from_json(raw)
    result = compile_system_text_policy(baseline, bundle, repo_root=ROOT, output_root=tmp_path / "worker", data_root=tmp_path)
    assert result["knowledge_stores"]["slot-contracts"]["snapshot"] == raw["knowledge"]["snapshot"]
    raw["cumulative_sources"].pop()
    with pytest.raises(PolicyError, match="ancestry"):
        compile_system_text_policy(baseline, SystemTextPolicyBundle.from_json(raw), repo_root=ROOT,
                                   output_root=tmp_path / "rejected", data_root=tmp_path)
    assert not (tmp_path / "rejected").exists()
