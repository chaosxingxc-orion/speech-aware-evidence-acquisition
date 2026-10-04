"""Prospective K16 scope never relaxes historical K4 or algorithm isolation."""
import copy
import pytest
from test_system_context_learning import setup, pin, repin, prepare
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def population(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    owner = {"schema": "saea-owner-template-population-k16-v1", "resolution": {
        "K": 16, "M": 4, "N": 20, "temperature": 0, "seed": 20260913,
        "candidate_trajectories": 320, "control_trajectories": 40,
        "total_scientific_trajectories": 360, "semantic_agents": 1,
        "semantic_batch_requests": 1, "fixed_knowledge": True, "case_free_learner": True}}
    f.protocol.update(K=16, algorithms=["tf-grpo-context-diversity"],
        population_authorization=pin(tmp_path, "population-owner.json", owner),
        candidate_members=[f"branch-{i:02d}" for i in range(1, 17)])
    old = f.registration["member_bindings"]
    bindings = {c: {"run_id": "run-"+c, "attempt_id": "attempt-"+c,
        "config_hash": content_hash(c), "bundle_id": content_hash({"policy": c})}
        for c in f.protocol["candidate_members"]}
    bindings.update({c: old[c] for c in ["seed", "seed-aa"]})
    f.registration["member_bindings"] = bindings
    f.registration["expected_members"] = {c:b["run_id"] for c,b in bindings.items()}
    f.recipe["expected_members"] = copy.deepcopy(f.registration["expected_members"])
    repin(f)
    return f, owner


def scope(f):
    return learning._validate_scope(f.recipe, f.registration, f.protocol, root=f.root)


def test_exact_16_branches_and_controls_accepted(tmp_path, monkeypatch):
    f, _ = population(tmp_path, monkeypatch)
    assert scope(f) == (f.protocol["candidate_members"], ["seed", "seed-aa"])


@pytest.mark.parametrize("fault", ["missing-owner", "wrong-owner-schema", "owner-budget", "owner-models",
    "owner-knowledge", "owner-abstraction", "changed-owner-bytes", "K4", "K32", "N80", "gepa", "no-controls",
    "missing-branch", "duplicate-bundle", "renamed-branch", "temperature", "seed", "wrong-roster"])
def test_k16_refuses_unregistered_or_partial_scope(tmp_path, monkeypatch, fault):
    f, owner = population(tmp_path, monkeypatch)
    if fault == "missing-owner": del f.protocol["population_authorization"]
    elif fault == "wrong-owner-schema": owner["schema"] = "other"
    elif fault == "owner-budget": owner["resolution"]["total_scientific_trajectories"] = 320
    elif fault == "owner-models": owner["resolution"]["semantic_agents"] = 16
    elif fault == "owner-knowledge": owner["resolution"]["fixed_knowledge"] = False
    elif fault == "owner-abstraction": owner["resolution"]["case_free_learner"] = False
    elif fault == "K4": f.protocol["K"] = 4
    elif fault == "K32": f.protocol["K"] = 32
    elif fault == "N80": f.protocol["N"] = 80
    elif fault == "gepa": f.protocol["algorithms"].append("gepa")
    elif fault == "no-controls": f.protocol["control_members"] = []
    elif fault == "missing-branch": f.registration["member_bindings"].pop("branch-16")
    elif fault == "duplicate-bundle": f.registration["member_bindings"]["branch-16"]["bundle_id"] = f.registration["member_bindings"]["branch-01"]["bundle_id"]
    elif fault == "renamed-branch": f.protocol["candidate_members"][0] = "preferred"
    elif fault == "temperature": f.protocol["sampling"]["temperature"] = .2
    elif fault == "seed": f.protocol["sampling"]["seed"] += 1
    elif fault == "wrong-roster": f.recipe["sample_ids"].reverse()
    if fault.startswith("owner-") or fault == "wrong-owner-schema":
        f.protocol["population_authorization"] = pin(f.root, "population-owner.json", owner)
    repin(f)
    if fault == "changed-owner-bytes": (f.root / "population-owner.json").write_text("{}")
    with pytest.raises((PolicyError, KeyError)): scope(f)


def test_legacy_four_policy_scope_still_works(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    assert len(scope(f)[0]) == 4
    assert prepare(f)["budget"]["family_trajectories"] == 120


def test_optimizer_cannot_export_to_unregistered_algorithm(tmp_path, monkeypatch):
    f = setup(tmp_path, monkeypatch)
    f.protocol["algorithms"] = ["tf-grpo-context-diversity"]
    monkeypatch.setattr(learning, "_qualified_feedback", lambda *a, **kw: (
        f.evidence, f.recipe, f.registration, f.protocol,
        f.protocol["candidate_members"], f.protocol["control_members"], f.reference.as_json()["reference"]))
    with pytest.raises(PolicyError, match="algorithm.*registered|registered.*algorithm"):
        prepare(f, algorithm="gepa")
    assert not (f.archive.root / "context-learning").exists()
