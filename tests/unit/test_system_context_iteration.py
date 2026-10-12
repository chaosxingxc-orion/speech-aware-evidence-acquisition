"""Complete synthetic baseline iterations use real proposal/history/accounting paths."""
import os
import copy
import importlib.util
import json
import random

import pytest

from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_context_learning import setup, pin, repin


def iteration_fixture(tmp_path, monkeypatch, algorithm="gepa", outcome="improve"):
    f = setup(tmp_path, monkeypatch)
    plan = {"schema": "saea-context-learning-iteration-plan-v1", "algorithm": algorithm, "iteration": 1,
        "input_recipe": f.recipe_pin, "selection_seed": 0,
        "callback_caps": {"summarize": 80, "compare": 20, "update_experience": 1, "propose": 4 if algorithm.startswith("tf") else 1,
                          "evaluate": 1}, "evaluation_candidate_trajectories_cap": 80,
        "evaluation_control_trajectories_cap": 40,
        "acceptance": "strict-registered-utility-sum", "automatic_next_iteration": False}
    f.plan_pin = pin(f.root, "iteration-plan.json", plan)
    # The plan commits the recipe before the protocol commits the plan: an acyclic
    # plan cannot also pin that recipe's transitive hash. Use the immutable family
    # identity/sample commitment instead of a reciprocal recipe hash.
    del plan["input_recipe"]
    plan["input_family_id"] = f.recipe["family_id"]
    plan["sample_ids_sha256"] = content_hash(f.recipe["sample_ids"])
    f.plan_pin = pin(f.root, "iteration-plan.json", plan)
    f.protocol["iteration_plan"] = f.plan_pin
    repin(f)
    f.calls = []
    def envelope(stage, value):
        return {"value": value, "provenance": {"kind": "synthetic-test", "request_id": f"{stage}-{len(f.calls)}"},
                "usage": {"provider_contacts": None, "input_tokens": None, "output_tokens": None}}
    def summarize(task):
        f.calls.append("summarize")
        return envelope("summarize", "Observed source support and retained uncertainty.")
    def compare(task):
        f.calls.append("compare")
        assert len(task["summaries"]) == 4
        return envelope("compare", "The winner preserves supported entities; the loser adds unsupported values.")
    def experience(task):
        f.calls.append("update_experience")
        assert len(task["comparisons"]) == 19
        return envelope("experience", [{"operation": "add", "id": "G1", "text": "Preserve supported entity boundaries."}])
    def propose(task):
        f.calls.append("propose")
        field, _, role = task["component"].partition(".")
        changes = ({"role_text": {role: "Preserve direct source support and uncertainty."}} if role else
                   {"context_layout": {"native_role_query_placement": "before-speech-v1"}} if field == "context_layout" else
                   {"node_context": {"tool_schema_rendering": "per-role", "reviewer_history_scope": "full"}} if field == "node_context" else
                   {"role_text": {"solver": "Preserve direct source support and uncertainty."}})
        if outcome == "no-change":
            changes = {}
        elif outcome == "invalid":
            changes = {"temperature": .7}
        document = {"schema": "saea-context-policy-update-proposal-v1", "algorithm": algorithm, "iteration": 1,
            "candidate_id": task["candidate_id"], "component": task["component"], "parent_ids": [task["parent_bundle_id"]],
            "changes": changes, "rationale": "Test source-supported component changes.", "hypotheses": [],
            "evidence": [task["input_sha256"]]}
        document["iteration"] = task["iteration"]
        return envelope("propose", document)
    def evaluate(task):
        f.calls.append("evaluate")
        assert len(task["policies"]) == 4
        assert len(set(task["policies"].values())) == 4
        # Synthetic source decoding only; the actual qualification boundary is
        # exercised separately in test_system_context_learning.
        e = copy.deepcopy(f.evidence)
        recipe = copy.deepcopy(f.recipe)
        registration = copy.deepcopy(f.registration)
        protocol = copy.deepcopy(f.protocol)
        recipe["family_id"] = registration["family_id"] = protocol["family_id"] = "context-trial20-v1"
        e["family_id"] = recipe["family_id"]
        for cid, binding in registration["member_bindings"].items():
            binding["run_id"] += "-trial"
            binding["attempt_id"] += "-trial"
            if cid in task["policies"]:
                binding["bundle_id"] = task["policies"][cid]
            registration["expected_members"][cid] = binding["run_id"]
        recipe["expected_members"] = registration["expected_members"]
        for source in e["feedback"]["sources"]:
            source.update(registration["member_bindings"][source["candidate_id"]])
        for group in e["feedback"]["groups"]:
            for member in group["members"]:
                if member["candidate_id"] in task["changed_members"]:
                    for axis in ("word", "char"):
                        member["native_counts"][f"slu_f1_{axis}_tp"] += 2 if outcome == "improve" else 0
                        member["native_counts"][f"slu_f1_{axis}_fp"] += .1 if outcome == "regress" else 0
        f.trial = (e, recipe, registration, protocol, list(f.policies), ["seed", "seed-aa"], f.reference.as_json()["reference"])
        return envelope("evaluate", {"bindings": [{"candidate_id": c} for c in registration["member_bindings"]],
                                      "recipe_pin": {"relpath": "trial-recipe.json", "sha256": "b" * 64}})
    f.callbacks = learning.ContextLearningCallbacks(summarize=summarize, compare=compare,
        update_experience=experience, propose=propose, evaluate=evaluate)
    actual_qualified = learning._qualified_feedback
    def qualified(bindings, *, recipe_pin, repo_root):
        if recipe_pin["relpath"] == "trial-recipe.json":
            return f.trial
        return actual_qualified(bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    monkeypatch.setattr(learning, "_qualified_feedback", qualified)
    return f


def run(f, algorithm="gepa", **kwargs):
    return learning.run_context_learning_iteration(f.archive, bindings=f.bindings, recipe_pin=f.recipe_pin,
        repo_root=f.root, algorithm=algorithm, iteration=1, policies=f.policies, callbacks=f.callbacks, **kwargs)


@pytest.mark.parametrize("outcome,status", [("improve", "retained-for-optimization"), ("equal", "rejected"),
    ("regress", "rejected"), ("no-change", "no-change"), ("invalid", "invalid")])
def test_gepa_complete_propose_evaluate_retain_or_reject(tmp_path, monkeypatch, outcome, status):
    f = iteration_fixture(tmp_path, monkeypatch, outcome=outcome)
    d = run(f)
    assert d["status"] == status and d["formal_adoption"] is False
    assert d["sampling"] == {"temperature": 0, "seed": 20260913}
    assert d["selection_seed"] == 0
    assert d["accounting"]["callback_counts"]["propose"] == 1
    assert d["accounting"]["provider_contacts"] is None
    assert d["accounting"]["evaluation_candidate_trajectories_reserved"] == (80 if outcome in {"improve", "equal", "regress"} else 0)
    assert d["accounting"]["evaluation_control_trajectories_reserved"] == (40 if outcome in {"improve", "equal", "regress"} else 0)
    assert f.calls == ["propose", "evaluate"] if outcome in {"improve", "equal", "regress"} else f.calls == ["propose"]
    assert len(list((f.archive.root / "context-learning/iterations/gepa-1/events").glob("*-reserved.json"))) == len(f.calls)
    original = {c: p.bundle_id for c, p in f.policies.items()}
    if status == "retained-for-optimization":
        assert d["state_after"]["active_bundle_ids"] != original
        assert len(d["state_after"]["programs"]) == 5
        child = d["updates"][0]["bundle_id"]
        parent = d["schedule"]["parent_bundle_id"]
        assert d["state_after"]["component_cursors"][child] == d["state_after"]["component_cursors"][parent]
    else:
        assert d["state_after"]["active_bundle_ids"] == original
        assert len(d["state_after"]["programs"]) == 4
    before = list(f.calls)
    with pytest.raises(PolicyError, match="exists|consumed"):
        run(f)
    assert f.calls == before


def test_tf_full_group_summary_semantic_experience_four_proposals_and_trial(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "retained-for-optimization"
    assert f.calls.count("summarize") == 76
    assert f.calls.count("compare") == 19
    assert f.calls.count("update_experience") == 1
    assert f.calls.count("propose") == 4
    assert f.calls.count("evaluate") == 1
    assert len(d["updates"]) == 4
    assert d["state_after"]["experience"] == {"G1": "Preserve supported entity boundaries."}
    assert d["accounting"]["evaluation_candidate_trajectories_reserved"] == 80
    assert d["fidelity"]["tf_retention"] == "quality-gated-study-adaptation"
    assert "relative_return" not in json.dumps(d)


@pytest.mark.parametrize("algorithm", ["gepa", "tf-grpo-context-diversity"])
def test_callback_exception_consumes_opportunity_and_preserves_failure(tmp_path, monkeypatch, algorithm):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm=algorithm)
    def fail(task):
        raise RuntimeError("Synthetic callback failed after attempted contact.")
    from dataclasses import replace
    f.callbacks = replace(f.callbacks, propose=fail)
    d = run(f, algorithm)
    assert d["status"] == "failed"
    assert d["accounting"]["provider_contacts"] is None
    assert list((f.archive.root / f"context-learning/iterations/{algorithm}-1/events").glob("*-failed.json"))


def test_zero_variation_tf_skips_all_callbacks_and_has_no_advantage(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    for group in f.evidence["feedback"]["groups"]:
        for member in group["members"]:
            member["native_counts"] = copy.deepcopy(group["members"][0]["native_counts"])
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "skip-zero-variation" and f.calls == []
    assert d["accounting"]["provider_contacts"] == 0


@pytest.mark.parametrize("fault", ["callback-cap", "trajectory-cap", "decode-seed", "missing-control", "wrong-child", "reused-run", "reference"])
def test_malformed_plan_or_unbound_trial_cannot_be_retained(tmp_path, monkeypatch, fault):
    f = iteration_fixture(tmp_path, monkeypatch)
    if fault in {"callback-cap", "trajectory-cap"}:
        plan = json.loads((f.root / "iteration-plan.json").read_text())
        if fault == "callback-cap":
            plan["callback_caps"]["propose"] = 0
        else:
            plan["evaluation_candidate_trajectories_cap"] = 79
        f.protocol["iteration_plan"] = pin(f.root, "iteration-plan.json", plan)
        repin(f)
    elif fault == "decode-seed":
        f.protocol["sampling"]["seed"] = 0
        repin(f)
    else:
        original = f.callbacks.evaluate
        def bad_trial(task):
            response = original(task)
            e, recipe, registration, protocol, cs, controls, reference = f.trial
            if fault == "missing-control":
                controls.pop()
            elif fault == "wrong-child":
                registration["member_bindings"][task["changed_members"][0]]["bundle_id"] = "d" * 64
            elif fault == "reused-run":
                c = task["changed_members"][0]
                registration["member_bindings"][c]["run_id"] = f.registration["member_bindings"][c]["run_id"]
            else:
                reference["f1"] = .5
            return response
        f.callbacks = learning.ContextLearningCallbacks(propose=f.callbacks.propose, evaluate=bad_trial)
    if fault in {"callback-cap", "trajectory-cap", "decode-seed"}:
        with pytest.raises(PolicyError):
            run(f)
        assert f.calls == []
    else:
        d = run(f)
        assert d["status"] == "failed"
        assert d["state_after"]["active_bundle_ids"] == {c: p.bundle_id for c, p in f.policies.items()}


def test_exact_gepa_selector_matches_hash_pinned_upstream_helpers():
    from pathlib import Path
    import hashlib
    path = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET") + "/references/system-context-baselines-iterations-v1/gepa/src/gepa/gepa_utils.py")
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "ac272a7d411c5c6273be369ec012d14121b1ce5a3bdc87409f419216b6f6a0e3"
    spec = importlib.util.spec_from_file_location("_pinned_gepa_utils", path)
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    for scores in ([[0, 0], [0, 0], [0, 0]], [[3, 0], [0, 3], [1, 1]], [[2, 3], [2, 3], [1, 1]]):
        programs = [{"bundle_id": content_hash(i), "scores": dict(zip(["a", "b"], v, strict=True))} for i, v in enumerate(scores)]
        front = {sid: {i for i, p in enumerate(programs) if p["scores"][sid] == max(q["scores"][sid] for q in programs)} for sid in ("a", "b")}
        aggregate = [sum(v) / len(v) for v in scores]
        for seed in (0, 1, 20260913):
            expected = upstream.select_program_candidate_from_pareto_front(front, aggregate, random.Random(seed))
            actual = learning.select_gepa_task(programs, sample_ids=["a", "b"], selection_seed=seed)
            assert actual["parent_bundle_id"] == programs[expected]["bundle_id"]
            assert actual["component"] == "role_text.perception"
            next_task = learning.select_gepa_task([programs[expected]], sample_ids=["a", "b"],
                selection_seed=seed, state=actual["state_after"])
            assert next_task["component"] == "role_text.solver"


def test_measured_usage_and_invalid_payload_are_retained(tmp_path, monkeypatch):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch)
    original = f.callbacks.propose
    def invalid(task):
        r = original(task)
        r["value"]["changes"] = {"knowledge": {}}
        r["usage"] = {"provider_contacts": 2, "input_tokens": 15, "output_tokens": 3}
        return r
    f.callbacks = replace(f.callbacks, propose=invalid)
    d = run(f)
    assert d["status"] == "invalid" and d["accounting"]["provider_contacts"] == 2
    assert d["accounting"]["callback_counts"]["propose"] == 1
    assert d["accounting"]["input_tokens"] == 15
    assert d["events"][0]["provenance"]["kind"] == "synthetic-test"
    assert d["events"][0]["callback_elapsed_seconds"] >= 0


@pytest.mark.parametrize("kind", ["missing-envelope", "negative-usage", "wrong-system"])
def test_bad_callback_provenance_or_task_binding_is_not_a_learned_update(tmp_path, monkeypatch, kind):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch)
    original = f.callbacks.propose
    def bad(task):
        r = original(task)
        if kind == "missing-envelope":
            return r["value"]
        if kind == "negative-usage":
            r["usage"]["provider_contacts"] = -1
        else:
            r["value"]["candidate_id"] = "foreign-system"
        return r
    f.callbacks = replace(f.callbacks, propose=bad)
    d = run(f)
    assert d["status"] == ("invalid" if kind == "wrong-system" else "failed")
    assert d["state_after"]["active_bundle_ids"] == {c: p.bundle_id for c, p in f.policies.items()}
    assert d["accounting"]["callback_counts"]["propose"] == 1


def test_duplicate_runtime_systems_are_not_fabricated_to_fill_k(tmp_path, monkeypatch):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity")
    original = f.callbacks.propose
    def duplicate(task):
        r = original(task)
        policy = f.policies["context-0"].as_json()
        r["value"]["changes"] = {k: policy[k] for k in ("role_text", "context_layout", "node_context")}
        return r
    f.callbacks = replace(f.callbacks, propose=duplicate)
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == "failed" and "distinct" in d["error"]["message"]
    assert f.calls.count("propose") == 4 and "evaluate" not in f.calls
    assert d["state_after"]["active_bundle_ids"] == {c: p.bundle_id for c, p in f.policies.items()}


def test_common_feedback_protocol_can_pin_both_algorithm_plans(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch)
    first = json.loads((f.root / "iteration-plan.json").read_text())
    other = copy.deepcopy(first)
    other["algorithm"] = "tf-grpo-context-diversity"
    other["callback_caps"]["propose"] = 4
    f.protocol["iteration_plans"] = {"gepa": f.protocol.pop("iteration_plan"),
        "tf-grpo-context-diversity": pin(f.root, "tf-iteration-plan.json", other)}
    repin(f)
    assert run(f)["status"] == "retained-for-optimization"


def test_previous_iteration_state_refuses_tampering_and_rejected_parent(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch, outcome="equal")
    d = run(f)
    assert d["status"] == "rejected"
    assert d["updates"][0]["bundle_id"] not in {p["bundle_id"] for p in d["state_after"]["programs"]}
    path = f.archive.root / "context-learning/iterations/gepa-1/decision.json"
    changed = json.loads(path.read_text())
    changed["state_after"]["active_bundle_ids"]["context-0"] = d["updates"][0]["bundle_id"]
    path.write_text(json.dumps(changed))
    with pytest.raises(PolicyError, match="custody"):
        learning._load_iteration_state(f.archive, d["decision_sha256"], algorithm="gepa", iteration=2,
            ids=d["sample_ids"], reference=f.reference.as_json()["reference"], repo_root=f.root)


def test_previous_accepted_state_requalifies_full_source_family(tmp_path, monkeypatch):
    f = iteration_fixture(tmp_path, monkeypatch)
    d = run(f)
    calls = list(f.calls)
    state = learning._load_iteration_state(f.archive, d["decision_sha256"], algorithm="gepa", iteration=2,
        ids=d["sample_ids"], reference=f.reference.as_json()["reference"], repo_root=f.root)
    assert state["active_bundle_ids"] == d["state_after"]["active_bundle_ids"]
    assert f.calls == calls
    original = learning._qualified_feedback
    def refuse_history(bindings, *, recipe_pin, repo_root):
        if recipe_pin["relpath"] == "trial-recipe.json":
            raise PolicyError("historical control not finalized")
        return original(bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    monkeypatch.setattr(learning, "_qualified_feedback", refuse_history)
    with pytest.raises(PolicyError, match="control"):
        learning._load_iteration_state(f.archive, d["decision_sha256"], algorithm="gepa", iteration=2,
            ids=d["sample_ids"], reference=f.reference.as_json()["reference"], repo_root=f.root)


@pytest.mark.parametrize("kind", ["continue", "missing-historical-parent", "rejected-next-parent"])
def test_next_iteration_carries_rng_component_cursor_and_only_retained_parents(tmp_path, monkeypatch, kind):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch, outcome="equal" if kind == "rejected-next-parent" else "improve")
    original_source = learning._qualified_feedback(f.bindings, recipe_pin=f.recipe_pin, repo_root=f.root)
    d = run(f)
    old_trial = f.trial
    changed = d["updates"][0]["proposal"]["candidate_id"]
    child = d["updates"][0]["bundle_id"]
    if kind != "missing-historical-parent":
        f.policies[changed] = f.archive.load_policy(child)
        current = copy.deepcopy(old_trial)
    else:
        current = copy.deepcopy(original_source)
    e, recipe, registration, protocol, candidates, controls, reference = current
    recipe["family_id"] = registration["family_id"] = protocol["family_id"] = "context-next20-v1"
    protocol["iteration"] = 2
    plan = json.loads((f.root / "iteration-plan.json").read_text())
    plan.update(iteration=2, input_family_id=recipe["family_id"])
    protocol["iteration_plan"] = pin(f.root, "next-plan.json", plan)
    next_pin = pin(f.root, "next-recipe.json", recipe)
    def qualified(bindings, *, recipe_pin, repo_root):
        if recipe_pin["relpath"] == "next-recipe.json":
            return current
        return old_trial if recipe_pin["relpath"] == "trial-recipe.json" else original_source
    monkeypatch.setattr(learning, "_qualified_feedback", qualified)
    original_propose = f.callbacks.propose
    def nochange(task):
        r = original_propose(task)
        r["value"]["changes"] = {}
        return r
    f.callbacks = replace(f.callbacks, propose=nochange)
    prior_calls = list(f.calls)
    args = dict(bindings=f.bindings, recipe_pin=next_pin, repo_root=f.root, algorithm="gepa", iteration=2,
                policies=f.policies, callbacks=f.callbacks, previous_decision_sha256=d["decision_sha256"])
    if kind == "continue":
        next_decision = learning.run_context_learning_iteration(f.archive, **args)
        assert next_decision["status"] == "no-change"
        assert next_decision["schedule"]["parent_bundle_id"] == child
        assert next_decision["schedule"]["component"] == "role_text.solver"
        assert next_decision["state_after"]["component_cursors"][child] == 2
    else:
        with pytest.raises(PolicyError, match="historical parent|rejected/unregistered"):
            learning.run_context_learning_iteration(f.archive, **args)
        assert f.calls == prior_calls


def test_empty_callback_exception_is_preserved_with_actionable_english_disposition(tmp_path, monkeypatch):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch)
    def fail(task):
        raise RuntimeError()
    f.callbacks = replace(f.callbacks, propose=fail)
    d = run(f)
    assert d["status"] == "failed" and d["error"]["type"] == "RuntimeError"
    assert "original exception source" in d["error"]["message"]


@pytest.mark.parametrize("outcome", ["invalid", "no-change", "regress"])
def test_tf_invalid_unchanged_and_regressing_batch_keep_exact_original_four(tmp_path, monkeypatch, outcome):
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity", outcome=outcome)
    d = run(f, "tf-grpo-context-diversity")
    assert d["status"] == ("rejected" if outcome == "regress" else outcome)
    assert d["accounting"]["callback_counts"]["propose"] == 4
    assert len(d["updates"]) == 4
    assert d["state_after"]["active_bundle_ids"] == {c: p.bundle_id for c, p in f.policies.items()}
    assert d["state_after"]["experience"] == {}
    assert d["qualified_input_family_budget"]["family_trajectories"] == 120
    assert d["input_family_is_reused_qualified_evidence"] is True
    assert f.calls.count("evaluate") == (1 if outcome == "regress" else 0)


def test_tf_proposal_cannot_redirect_a_reserved_system_opportunity(tmp_path, monkeypatch):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch, algorithm="tf-grpo-context-diversity", outcome="no-change")
    original = f.callbacks.propose
    def redirect(task):
        r = original(task)
        if task["candidate_id"] == "context-0":
            r["value"]["candidate_id"] = "context-1"
            r["value"]["parent_ids"] = [f.policies["context-1"].bundle_id]
        return r
    f.callbacks = replace(f.callbacks, propose=redirect)
    d = run(f, "tf-grpo-context-diversity")
    assert d["updates"][0]["status"] == "invalid"
    assert "reserved system task" in d["updates"][0]["error"]
    assert d["accounting"]["callback_counts"]["propose"] == 4
    assert "evaluate" not in f.calls


def test_non_json_callback_output_still_records_failed_opportunity_and_decision(tmp_path, monkeypatch):
    from dataclasses import replace
    f = iteration_fixture(tmp_path, monkeypatch)
    f.callbacks = replace(f.callbacks, propose=lambda task: {"not-json"})
    d = run(f)
    assert d["status"] == "failed"
    assert d["accounting"]["callback_counts"]["propose"] == 1
    assert d["events"][0]["status"] == "failed"
    assert d["events"][0]["response"] == {"invalid_response_type": "set"}
    assert d["accounting"]["provider_contacts"] is None
    assert list((f.archive.root / "context-learning/iterations/gepa-1/events").glob("*-failed.json"))
    assert (f.archive.root / "context-learning/iterations/gepa-1/decision.json").exists()
