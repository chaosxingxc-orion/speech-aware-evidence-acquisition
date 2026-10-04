"""Template-first feedback keeps complete rewards without per-row model calls."""
import copy
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails import system_context_template_feedback as templates
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_context_learning import pin, repin
from test_system_context_iteration import iteration_fixture, run


def profile():
    return {"schema": "saea-template-feedback-profile-v1", "phase": "template-only",
            "examples_per_template": 3, "selection_seed": 20261004,
            "example_sampling": "stratified-stable-hash-v1",
            "semantic_summaries": False, "semantic_comparisons": False}


def configure(f):
    plan = json.loads((f.root / "iteration-plan.json").read_text())
    plan["feedback_profile"] = profile()
    plan["callback_caps"].update(summarize=0, compare=0,
                                update_experience=1 if plan["algorithm"].startswith("tf") else 0)
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    return plan


def test_template_tf_iteration_uses_one_batch_update_four_proposals(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    configure(f)
    observed = []
    def experience(task):
        f.calls.append("update_experience")
        assert "comparisons" not in task
        view = task["template_feedback"]
        assert len(view["templates"]) == 4
        assert "groups" not in view and view["rows_scored"] == 80
        assert all(len(t["examples"]) == 3 for t in view["templates"])
        observed.append(view)
        return {"value": [], "provenance": {"kind": "synthetic"},
                "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)}
    old_propose = f.callbacks.propose
    def propose(task):
        packet = task["qualified_input"]
        assert "groups" not in packet and "official_summaries" not in packet
        assert packet["template_feedback"] == observed[0]
        assert packet["source_input_sha256"] == task["input_sha256"]
        assert len(packet["policies"]) == 4
        return old_propose(task)
    f.callbacks = replace(f.callbacks, summarize=None, compare=None,
                          update_experience=experience, propose=propose)
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "retained-for-optimization", d["error"]
    assert f.calls == ["update_experience"] + ["propose"] * 4 + ["evaluate"]
    assert d["accounting"]["evaluation_candidate_trajectories_reserved"] == 80
    assert d["feedback_profile"] == profile()
    assert d["fidelity"]["reflection"] == "template-batch-study-adaptation-v1"
    raw = json.loads(next((f.archive.root / "context-learning/inputs").glob("*.json")).read_text())
    assert raw["template_feedback"]["numeric_source_sha256"] == content_hash(raw["groups"])
    assert len(raw["groups"]) == 20
    assert all("summary_tasks" not in g for g in raw["groups"])
    assert sum(t["rows"] for t in observed[0]["templates"]) == 80
    assert observed[0]["omissions"]["unsampled_trajectories"] == 68
    assert observed[0]["omissions"]["numeric_rows_omitted"] == 0


@pytest.mark.parametrize("fault", ["phase", "cap", "seed", "extra", "summaries", "callbacks"])
def test_profile_requires_explicit_bounded_registration(tmp_path, monkeypatch, fault):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    plan = configure(f)
    p = plan["feedback_profile"]
    if fault == "phase": p["phase"] = "knowledge-content"
    elif fault == "cap": p["examples_per_template"] = 20
    elif fault == "seed": p["selection_seed"] = True
    elif fault == "extra": p["sample_ids"] = ["slurp:test:1"]
    elif fault == "summaries": p["semantic_summaries"] = True
    else: plan["callback_caps"]["summarize"] = 80
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    with pytest.raises(PolicyError): run(f, "tf-grpo-context-diversity")
    assert f.calls == []


def test_gepa_template_view_preserves_component_selection(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch)
    configure(f)
    original = f.callbacks.propose
    def propose(task):
        assert "groups" not in task["qualified_input"]
        assert task["qualified_input"]["reflection_task"]["component"] == task["component"]
        assert len(task["qualified_input"]["template_feedback"]["templates"]) == 4
        return original(task)
    f.callbacks = replace(f.callbacks, propose=propose)
    d = run(f)
    assert d["status"] == "retained-for-optimization", d["error"]
    assert f.calls == ["propose", "evaluate"]


def test_projection_is_deterministic_and_cost_complete(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch)
    packet = learning.prepare_context_optimizer_input(f.archive, bindings=f.bindings,
        recipe_pin=f.recipe_pin, repo_root=f.root, algorithm="gepa", iteration=1,
        policies=f.policies, candidate_id="context-3", component="role_text.perception")
    a = templates.template_feedback(packet, profile())
    b = templates.template_feedback(copy.deepcopy(packet), profile())
    assert a == b
    assert a["numeric_source_sha256"] == content_hash(packet["groups"])
    for t, business in zip(a["templates"], packet["business_measurements"]):
        assert t["measurements"] == business
        assert t["first_sample_seconds"] == 1 + int(t["candidate_id"][-1])
        assert sum(t["category_counts"].values()) == 20
        assert len(t["unsampled_sample_ids"]) == 17
        assert t["utility_sum"] == pytest.approx(sum(
            m["utility"] for g in packet["groups"] for m in g["members"]
            if m["candidate_id"] == t["candidate_id"]))
    assert a["templates"][0]["category_counts"]["unreliable"] == 20
    view = templates.proposer_view({**packet, "template_feedback": a, "feedback_profile": profile()})
    assert "groups" not in view and "unsampled_sample_ids" not in json.dumps(view)
    assert len(view["template_feedback"]["templates"]) == 4


def test_template_mode_keeps_zero_variance_as_zero_signal(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    configure(f)
    for group in f.evidence["feedback"]["groups"]:
        for member in group["members"]:
            member["native_counts"] = copy.deepcopy(group["members"][0]["native_counts"])
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "skip-zero-variation" and f.calls == []


@pytest.mark.parametrize("fault", ["missing-row", "duplicate-sample", "missing-measurement", "nonfinite"])
def test_projection_rejects_partial_or_nonfinite_numeric_input(tmp_path, monkeypatch, fault):
    f = iteration_fixture(tmp_path, monkeypatch)
    packet = learning.prepare_context_optimizer_input(f.archive, bindings=f.bindings,
        recipe_pin=f.recipe_pin, repo_root=f.root, algorithm="gepa", iteration=1,
        policies=f.policies, candidate_id="context-3", component="role_text.perception")
    if fault == "missing-row": packet["groups"][0]["members"].pop()
    elif fault == "duplicate-sample": packet["groups"][1]["sample_id"] = packet["groups"][0]["sample_id"]
    elif fault == "missing-measurement": packet["business_measurements"].pop()
    else: packet["groups"][0]["members"][0]["utility"] = float("nan")
    with pytest.raises(PolicyError): templates.template_feedback(packet, profile())


def test_legacy_actor_view_is_unchanged():
    packet = {"schema": "original", "groups": [1]}
    assert templates.proposer_view(packet) is packet


def test_stage_one_rejects_knowledge_edit_without_replacement(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    configure(f)
    def experience(task):
        return {"value": [], "provenance": {"kind": "synthetic"},
                "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)}
    original = f.callbacks.propose
    def propose(task):
        r = original(task)
        r["value"]["changes"] = {"knowledge": {"content": "Unregistered new content."}}
        return r
    f.callbacks = replace(f.callbacks, update_experience=experience, propose=propose)
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "invalid"
    assert f.calls == ["propose"] * 4
    assert len(d["updates"]) == 4
    assert all(u["status"] == "invalid" for u in d["updates"])
    assert d["accounting"]["evaluation_candidate_trajectories_reserved"] == 0


def test_profile_cannot_be_added_after_registration(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch)
    with pytest.raises(PolicyError, match="prospectively registered"):
        learning.prepare_context_optimizer_input(f.archive, bindings=f.bindings,
            recipe_pin=f.recipe_pin, repo_root=f.root, algorithm="gepa", iteration=1,
            policies=f.policies, candidate_id="context-3", component="role_text.perception",
            feedback_profile=profile())
    assert not (f.archive.root / "context-learning").exists()


def test_actor_policy_view_keeps_all_editable_text_without_expanding_provenance(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    configure(f)
    original = f.callbacks.propose
    def propose(task):
        p = task["policy"]
        parent = f.policies[task["candidate_id"]].as_json()
        assert "cumulative_sources" not in p
        assert p["schema"] == "saea-template-policy-view-v1"
        assert p["source_policy_sha256"] == content_hash(parent)
        assert set(p) == {"schema", "source_policy_sha256", "role_text", "context_layout", "node_context"}
        assert not any(k in p for k in ("knowledge", "construction_instruction", "construction_receipt", "supply", "exposure_commitment"))
        assert p["role_text"] == parent["role_text"]
        assert p["context_layout"] == parent["context_layout"]
        assert p["node_context"] == parent["node_context"]
        assert task["qualified_input"]["policies"][task["candidate_id"]]["policy"] == p
        return original(task)
    f.callbacks = replace(f.callbacks, propose=propose,
        update_experience=lambda task: {"value": [], "provenance": {"kind": "synthetic"},
            "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)})
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "retained-for-optimization", d["error"]
    for update in d["updates"]:
        parent = f.policies[update["proposal"]["candidate_id"]].as_json()
        child = f.archive.load_policy(update["bundle_id"]).as_json()
        assert all(source in child["cumulative_sources"] for source in parent["cumulative_sources"])



def test_aggregate_only_profile_never_sends_sample_cases_or_knowledge(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    plan = configure(f)
    plan["feedback_profile"]["examples_per_template"] = 0
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    original = f.callbacks.propose
    def check(view):
        assert view["rows_scored"] == 80
        assert view["omissions"]["numeric_rows_omitted"] == 0
        assert view["omissions"]["unsampled_trajectories"] == 80
        assert all(t["examples"] == [] for t in view["templates"])
        assert "slurp:train:" not in json.dumps(view)
        assert all(sum(t["category_counts"].values()) == 20 for t in view["templates"])
    def experience(task):
        check(task["template_feedback"])
        assert set(task["policies"]) == set(f.policies)
        assert "Solver/Reviewer" in task["reflection_task"]["instructions"]
        assert "slurp:train:" not in json.dumps(task)
        for cid, policy in task["policies"].items():
            assert policy["policy"]["role_text"] == f.policies[cid].as_json()["role_text"]
        return {"value": [], "provenance": {"kind": "synthetic"},
                "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)}
    def propose(task):
        check(task["qualified_input"]["template_feedback"])
        instructions = task["qualified_input"]["reflection_task"]["instructions"]
        assert "Solver/Reviewer" in instructions
        assert "working hypothesis" in instructions
        assert "Do not request individual cases or source rosters" in instructions
        assert "bounded stratified cases" not in instructions
        for parent in task["qualified_input"]["policies"].values():
            assert set(parent["policy"]) == {"schema", "source_policy_sha256", "role_text", "context_layout", "node_context"}
        assert "slurp:train:" not in json.dumps(task)
        return original(task)
    f.callbacks = replace(f.callbacks, summarize=None, compare=None, update_experience=experience, propose=propose)
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "retained-for-optimization", d["error"]
    assert f.calls == ["propose"] * 4 + ["evaluate"]
    assert d["accounting"]["callback_counts"]["summarize"] == 0
    assert d["accounting"]["callback_counts"]["compare"] == 0


def test_explicit_template_phase_reset_preserves_policy_history(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity", outcome="no-change")
    plan = configure(f)
    plan["iteration"] = f.protocol["iteration"] = 2
    plan["feedback_profile"]["examples_per_template"] = 0
    previous_sha = "c" * 64
    plan["experience_transition"] = {"mode": "empty-template-phase-v1", "previous_decision_sha256": previous_sha}
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    previous = {"experience": {"old-case": "Observed slurp:train:42; retain in original archive only."},
                "programs": [{"bundle_id": p.bundle_id} for p in f.policies.values()],
                "active_bundle_ids": {c: p.bundle_id for c, p in f.policies.items()}, "component_cursors": {}}
    original = copy.deepcopy(previous)
    monkeypatch.setattr(learning, "_load_iteration_state", lambda *a, **k: previous)
    old_propose = f.callbacks.propose
    def experience(task):
        assert task["experience"] == {}
        assert "slurp:train:" not in json.dumps(task)
        return {"value": [], "provenance": {"kind": "synthetic"},
                "usage": dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)}
    def propose(task):
        assert task["experience"] == task["qualified_input"]["experience"] == {}
        assert "slurp:train:" not in json.dumps(task)
        return old_propose(task)
    callbacks = replace(f.callbacks, summarize=None, compare=None, update_experience=experience, propose=propose)
    d = learning.run_context_learning_iteration(f.archive, bindings=f.bindings, recipe_pin=f.recipe_pin,
        repo_root=f.root, algorithm="tf-grpo-context-diversity", iteration=2, policies=f.policies,
        callbacks=callbacks, previous_decision_sha256=previous_sha)
    assert d["status"] == "no-change", d["error"]
    assert previous == original
    assert d["experience_transition"]["prior_experience_sha256"] == content_hash(original["experience"])
    assert d["experience_transition"]["prior_experience_entries"] == 1
    assert d["state_after"]["experience"] == {}
    assert d["state_after"]["active_bundle_ids"] == original["active_bundle_ids"]
    assert {p["bundle_id"] for p in d["state_after"]["programs"]} == set(original["active_bundle_ids"].values())
    assert not any(stage in f.calls for stage in ("summarize", "compare", "evaluate"))


@pytest.mark.parametrize("fault", ["mode", "hash", "extra", "profile", "algorithm", "no-previous", "wrong-previous"])
def test_experience_reset_requires_exact_prospective_transition(tmp_path, monkeypatch, fault):
    algorithm = "gepa" if fault == "algorithm" else "tf-grpo-context-diversity"
    f = iteration_fixture(tmp_path, monkeypatch, algorithm=algorithm)
    plan = configure(f)
    plan["iteration"] = f.protocol["iteration"] = 2
    plan["feedback_profile"]["examples_per_template"] = 0
    plan["experience_transition"] = {"mode": "empty-template-phase-v1", "previous_decision_sha256": "c" * 64}
    if fault == "mode": plan["experience_transition"]["mode"] = "delete-history"
    if fault == "hash": plan["experience_transition"]["previous_decision_sha256"] = "invalid"
    if fault == "extra": plan["experience_transition"]["erase_archive"] = True
    if fault == "profile": plan["feedback_profile"]["examples_per_template"] = 3
    f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
    repin(f)
    if fault != "no-previous":
        monkeypatch.setattr(learning, "_load_iteration_state", lambda *a, **k:
            {"experience": {}, "programs": [], "active_bundle_ids": {}, "component_cursors": {}})
    with pytest.raises(PolicyError):
        learning.run_context_learning_iteration(f.archive, bindings=f.bindings, recipe_pin=f.recipe_pin,
            repo_root=f.root, algorithm=algorithm, iteration=2, policies=f.policies, callbacks=f.callbacks,
            previous_decision_sha256=None if fault == "no-previous" else ("d" if fault == "wrong-previous" else "c") * 64)
    assert f.calls == []