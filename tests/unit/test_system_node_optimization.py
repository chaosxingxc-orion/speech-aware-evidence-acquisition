"""Full node text and implemented context choices share one immutable policy."""
import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal,
    apply_text_proposal, compile_system_text_policy, verify_system_text_binding,
)
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_optimization import (
    load_optimization_panel, optimization_scope_for, require_optimization_scope,
)
from test_system_text_policy import seed_document, BASE, ROOT
from test_system_text_policy_binding import bound  # noqa: F401 - pytest fixture
from test_system_context_proposals import expanded_protocol
from test_system_optimization import pin
from test_system_proposer_capsule import fixture

BUNDLE = "saea-system-text-policy-bundle-v3"
PROPOSAL = "saea-text-policy-update-proposal-v3"
SCOPE = "saea-node-context-search-scope-v3"
AUTHORITY = "docs/receipts/owner/2026-10-04-node-optimization-space.json"


def upgraded(parent=None):
    d = seed_document() if parent is None else parent.as_json()
    baseline = json.loads((ROOT / BASE).read_text())
    d.update(schema=BUNDLE,
             parent_ids=[] if parent is None else [parent.bundle_id],
             context_layout={"native_role_query_placement": None},
             node_context={"tool_schema_rendering": "constant", "reviewer_history_scope": "full"})
    d["role_text"]["perception"] = (ROOT / "configs" / baseline["phase_material"]["perception"]["instruction_template"]).read_text()
    return SystemTextPolicyBundle.from_json(d, parents=[] if parent is None else [parent])


def packet(tmp_path):
    p, _ = fixture(tmp_path)
    parent = upgraded()
    p.update(parent_policy=parent.as_json(), parent_bundle_id=parent.bundle_id, seed_bundle_id=parent.bundle_id)
    p["optimization_scope"] = {"schema": SCOPE, "purpose": "reused-optimization-panel",
        "editable": ["role_text", "context_layout", "node_context"], "plan_sha256": "a" * 64,
        "context_authority_sha256": "b" * 64}
    return p, parent


@pytest.mark.parametrize("role", ["perception", "solver", "reviewer", "planner"])
def test_entire_node_instruction_is_editable_and_independent(tmp_path, role):
    p, parent = packet(tmp_path)
    contract = TextPolicyUpdateProposal.response_contract(p)
    assert contract["example"]["schema"] == PROPOSAL
    assert "perception" in contract["editable_changes"]["role_text"]
    assert set(contract["editable_changes"]) == {"role_text", "context_layout", "node_context"}
    proposal = contract["example"]
    # A long full replacement is intentional: new prefill count is not an edit cap.
    replacement = "Use the current speech and distinguish observation from hypothesis. " * 80
    proposal["changes"] = {"role_text": {role: replacement},
        "node_context": {"tool_schema_rendering": "per-role", "reviewer_history_scope": "full"}}
    child = apply_text_proposal(TextPolicyUpdateProposal.from_json(proposal),
        parents=[parent], added_sources=[])
    assert child.as_json()["role_text"][role] == replacement
    for other in set(parent.as_json()["role_text"]) - {role}:
        assert child.as_json()["role_text"][other] == parent.as_json()["role_text"][other]
    assert child.as_json()["cumulative_sources"] == parent.as_json()["cumulative_sources"]


@pytest.mark.parametrize("history", ["full", "latest-solver-and-local-tools"])
@pytest.mark.parametrize("rendering", ["constant", "per-role"])
def test_full_compile_archive_binding_and_default_off(bound, history, rendering):  # noqa: F811
    _, _, repo, data, baseline, parent = bound
    child = upgraded(parent)
    target = repo / AUTHORITY
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / AUTHORITY).read_bytes())
    d = child.as_json()
    d["node_context"] = {"tool_schema_rendering": rendering, "reviewer_history_scope": history}
    child = SystemTextPolicyBundle.from_json(d, parents=[parent])
    compiled = compile_system_text_policy(baseline, child, repo_root=ROOT, output_root=repo)
    assert compile_system_text_policy(baseline, child, repo_root=ROOT, output_root=repo, enabled=False) == baseline
    assert compiled["native_episode"]["tool_schema_rendering"] == rendering
    assert compiled["native_episode"]["roles"]["reviewer"]["history_scope"] == history
    for role, text in d["role_text"].items():
        path = repo / "configs" / compiled["phase_material"][role]["instruction_template"]
        assert path.read_text() == text
        assert compiled["phase_material"][role]["response_format_id"] == baseline["phase_material"][role]["response_format_id"]
    from test_consumption_node_context import runtime_values
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
    runtime = load_native_episode_config(runtime_values(compiled), default_phase_program(compiled["policy"]))
    assert runtime.tool_schema_rendering == rendering
    assert runtime.role("reviewer").history_scope == history
    assert compiled["scorers"] == baseline["scorers"]
    assert compiled["native_episode"]["max_revisions"] == baseline["native_episode"]["max_revisions"]
    assert compiled["phase_tools"]["planner"]["max_calls_per_sample"] == 1
    archive = SystemSearchArchive(data / "search")
    archive.store_policy(child)
    rel = "search/policies/" + child.bundle_id + ".json"
    binding = {"schema": "saea-system-text-role-binding-v1", "bundle_id": child.bundle_id,
               "bundle": {"relpath": rel, "sha256": hashlib.sha256((data / rel).read_bytes()).hexdigest()}}
    result = verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)
    assert set(result["role_sha256"]) == {"perception", "solver", "reviewer", "planner"}
    assert result["node_context"] == d["node_context"]
    assert archive.load_policy(child.bundle_id).as_json() == d
    compiled["native_episode"]["roles"]["reviewer"]["history_scope"] = "full" if history != "full" else "latest-solver-and-local-tools"
    with pytest.raises(PolicyError):
        verify_system_text_binding(compiled, binding, repo_root=repo, data_root=data)


@pytest.mark.parametrize("bad", [{}, {"tool_schema_rendering": "constant"},
    {"tool_schema_rendering": "constant", "reviewer_history_scope": "invented"},
    {"tool_schema_rendering": True, "reviewer_history_scope": "full"},
    {"tool_schema_rendering": "constant", "reviewer_history_scope": "full", "code": "x"}])
def test_node_context_is_an_exact_implemented_surface(bad):
    d = upgraded().as_json()
    d["node_context"] = bad
    with pytest.raises(PolicyError):
        SystemTextPolicyBundle.from_json(d)


def test_new_bundle_does_not_downgrade_or_invent_unknown_roles():
    parent = upgraded()
    d = parent.as_json()
    d["parent_ids"] = [parent.bundle_id]
    d.pop("node_context")
    d["role_text"].pop("perception")
    d["schema"] = "saea-system-text-policy-bundle-v2"
    with pytest.raises(PolicyError, match="downgrade"):
        SystemTextPolicyBundle.from_json(d, parents=[parent])
    d = parent.as_json()
    d["role_text"]["summarizer"] = "Add a second answering model."
    with pytest.raises(PolicyError):
        SystemTextPolicyBundle.from_json(d)


@pytest.mark.parametrize("schema", ["saea-text-policy-update-proposal-v1", "saea-text-policy-update-proposal-v2"])
def test_old_proposer_schema_cannot_borrow_new_role_authority(tmp_path, schema):
    p, parent = packet(tmp_path)
    proposal = TextPolicyUpdateProposal.response_contract(p)["example"]
    proposal.update(schema=schema, changes={"role_text": {"perception": "Change candidates."}})
    with pytest.raises(PolicyError):
        apply_text_proposal(TextPolicyUpdateProposal.from_json(proposal), parents=[parent], added_sources=[])


def test_prospective_node_scope_binds_identical_branch_contracts(tmp_path):
    protocol = expanded_protocol(tmp_path)
    authority = pin(tmp_path, AUTHORITY, {
        "schema": "saea-owner-node-optimization-space-v1",
        "gpu_dispatch_authorized_by_this_record": False,
        "new_human_permission_required_within_owner227": False,
    })
    protocol["optimization_panel"].update(schema=SCOPE,
        editable=["role_text", "context_layout", "node_context"], context_authority=authority)
    assert load_optimization_panel(protocol, "update-3", repo_root=tmp_path)
    projected = optimization_scope_for(protocol, 3)
    assert projected["schema"] == SCOPE
    for branch in ("L", "B"):
        p = {"round": 3, "branch": branch, "optimization_scope": projected}
        require_optimization_scope(p, protocol=protocol)
    wrong = copy.deepcopy(protocol)
    wrong["optimization_panel"]["context_authority"]["relpath"] = "arbitrary.json"
    with pytest.raises(PolicyError):
        load_optimization_panel(wrong, "update-3", repo_root=tmp_path)


@pytest.mark.parametrize("field", ["construction_instruction", "supply", "slot_value_edits",
                                   "new_tool", "scorers", "code"])
def test_node_search_keeps_fixed_system_factors(tmp_path, field):
    p, _ = packet(tmp_path)
    d = TextPolicyUpdateProposal.response_contract(p)["example"]
    d["changes"] = {field: {}}
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_json(d)


def test_node_successor_refuses_to_reuse_a_three_role_seed_identity(tmp_path):
    from test_system_search_successor import setup
    from speech_aware_evidence_acquisition.rails.system_search_successor import (
        build_successor)
    old, new, repo, _, _, args = setup(tmp_path)
    before = {p.relative_to(old.root): p.read_bytes() for p in old.root.rglob("*.json")}
    authority = pin(repo, AUTHORITY, {
        "schema": "saea-owner-node-optimization-space-v1",
        "gpu_dispatch_authorized_by_this_record": False,
        "new_human_permission_required_within_owner227": False,
    })
    decision = json.loads((repo / args["transition"]["relpath"]).read_text())
    decision["context_authority"] = authority
    args["transition"] = pin(repo, "node-transition.json", decision)
    with pytest.raises(PolicyError, match="four-role seed"):
        build_successor(old, new, **args)
    assert not new.root.exists()
    assert all((old.root / relative).read_bytes() == raw for relative, raw in before.items())


@pytest.mark.parametrize("profile", ["full-index-v1", "typed-coherent-feedback-v1"])
def test_capsule_advertises_full_node_fields_without_runtime_feedback(tmp_path, profile):
    from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
    from test_system_proposer_capsule import reseal
    p, roots = fixture(tmp_path)
    d = upgraded().as_json()
    d["knowledge"] = p["parent_policy"]["knowledge"]
    parent = SystemTextPolicyBundle.from_json(d)
    p.update(parent_policy=d, parent_bundle_id=parent.bundle_id, seed_bundle_id=parent.bundle_id)
    p["optimization_scope"] = {"schema": SCOPE, "purpose": "reused-optimization-panel",
        "editable": ["role_text", "context_layout", "node_context"], "plan_sha256": "a" * 64,
        "context_authority_sha256": "b" * 64}
    reseal(p)
    capsule = ProposerCapsule.from_packet(p, roots=roots, view_profile=profile)
    rendered = capsule.initial_input()
    text = json.dumps(rendered)
    assert PROPOSAL in text and "perception/solver/reviewer/planner" in text
    assert rendered["packet"]["parent_policy"]["node_context"] == d["node_context"]
    assert set(rendered["packet"]["parent_policy"]["role_text"]) == set(d["role_text"])
    assert not {"feedback", "learning_history", "complementary_policies"} & set(rendered["packet"])
    assert not any(a["kind"] in {"complete-feedback", "complete-history-index", "trajectory"}
                   for a in capsule.as_json()["artifacts"])


def test_v3_scope_requires_a_prospectively_frozen_four_node_parent(tmp_path):
    p, _ = packet(tmp_path)
    p["parent_policy"] = seed_document()
    with pytest.raises(PolicyError, match="four-role parent"):
        TextPolicyUpdateProposal.response_contract(p)


@pytest.mark.parametrize("schema", [PROPOSAL, "saea-text-policy-update-proposal-v2"])
def test_node_response_import_spends_exactly_one_slot_even_when_schema_is_wrong(tmp_path, schema):
    from test_system_proposer_capsule import reseal
    p, parent = packet(tmp_path)
    reseal(p)
    archive = SystemSearchArchive(tmp_path / "node-import")
    archive.store_policy(parent)
    archive.store_input(p)
    reply = TextPolicyUpdateProposal.response_contract(p)["example"]
    reply.update(schema=schema, changes={"role_text": {"perception": "Keep source uncertainty visible."}})
    receipt = {"raw_response": json.dumps(reply), "session_id": p["session_id"],
        "model_version": p["model_version"], "input_sha256": p["input_sha256"],
        "input_tokens": 10, "output_tokens": 10}
    result = archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)
    assert result["status"] == ("provisional" if schema == PROPOSAL else "invalid")
    with pytest.raises(PolicyError, match="consumed|exists"):
        archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)


def test_node_successor_continues_only_an_explicit_four_role_seed_protocol(tmp_path):
    from test_system_search_successor import setup
    from speech_aware_evidence_acquisition.rails.system_search_successor import (
        build_successor, register_successor)
    old, new, repo, seed, legacy, args = setup(tmp_path)
    # This fixture represents a prospectively frozen schema transition, not a
    # relabeling of an old input or a production seed migration utility.
    node_seed = upgraded(seed)
    old.store_policy(node_seed)
    prior = json.loads((repo / args["previous_protocol"]["relpath"]).read_text())
    prior["seed_bundle"]["bundle_id"] = node_seed.bundle_id
    args["previous_protocol"] = pin(repo, "explicit-four-role-seed-protocol.json", prior)
    authority = pin(repo, AUTHORITY, {
        "schema": "saea-owner-node-optimization-space-v1",
        "gpu_dispatch_authorized_by_this_record": False,
        "new_human_permission_required_within_owner227": False})
    decision = json.loads((repo / args["transition"]["relpath"]).read_text())
    decision["context_authority"] = authority
    args["transition"] = pin(repo, "node-transition.json", decision)
    successor = build_successor(old, new, **args)
    assert successor["schema"] == "saea-system-search-successor-sequence-v3"
    assert successor["seed_bundle_id"] == node_seed.bundle_id
    assert successor["earlier_allocations"] == legacy["earlier_allocations"]
    assert successor["held_allocations"] == legacy["held_allocations"]
    register_successor(old, new, successor, repo_root=repo)
    assert new.allocation_extension(4) == successor
    assert new.load_policy(node_seed.bundle_id).as_json() == node_seed.as_json()



def test_node_branches_receive_the_same_system_quality_and_latency_objective(tmp_path):
    p, _ = packet(tmp_path)
    rules = []
    for branch in ("L", "B"):
        p["branch"] = branch
        r = TextPolicyUpdateProposal.response_contract(p)["rules"]
        assert "official SLU-F1" in r
        assert "intent" in r and "reliable completion" in r
        assert "non-first sample" in r and "mean" in r
        assert "first sample" in r
        rules.append(r)
    assert rules[0] == rules[1]
