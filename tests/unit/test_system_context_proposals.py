"""Prospective context edits obey one pinned scope in both search branches."""
import copy
import json

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_optimization import (
    load_optimization_panel, require_context_only_changes, require_optimization_scope,
)
from speech_aware_evidence_acquisition.rails.system_proposer_capsule import ProposerCapsule
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal, apply_text_proposal,
)
from test_system_optimization import fixture as panel_fixture, pin
from test_system_proposer_capsule import fixture, reseal


SCOPE = "saea-context-layout-search-scope-v2"
PROPOSAL = "saea-text-policy-update-proposal-v2"
AUTHORITY = "docs/receipts/owner/2026-10-03-context-space-and-node-timing-amendment.json"
FIELD = "native_role_query_placement"


def scope():
    return {"schema": SCOPE, "purpose": "reused-optimization-panel",
            "editable": ["role_text", "context_layout"], "plan_sha256": "a" * 64,
            "context_authority_sha256": "b" * 64}


def expanded_protocol(tmp_path):
    protocol, _ = panel_fixture(tmp_path)
    authority = pin(tmp_path, AUTHORITY, {
        "schema": "saea-owner-context-space-amendment-v1",
        "gpu_dispatch_authorized_by_this_record": False,
        "new_human_permission_required_within_owner227": False,
    })
    protocol["optimization_panel"].update(schema=SCOPE,
        editable=["role_text", "context_layout"], context_authority=authority)
    return protocol


@pytest.mark.parametrize("placement", [None, "before-speech-v1"])
def test_v2_joint_proposal_compiles_identity_and_retains_parent_exposure(tmp_path, placement):
    packet, _ = fixture(tmp_path)
    packet["optimization_scope"] = scope()
    parent = SystemTextPolicyBundle.from_json(packet["parent_policy"])
    contract = TextPolicyUpdateProposal.response_contract(packet)
    assert contract["example"]["schema"] == PROPOSAL
    assert set(contract["editable_changes"]) == {"role_text", "context_layout"}
    document = contract["example"]
    document["changes"] = {"context_layout": {FIELD: placement},
        "role_text": {"solver": "Use source-bound evidence and deliver task JSON."}}
    proposal = TextPolicyUpdateProposal.from_json(document)
    child = apply_text_proposal(proposal, parents=[parent], added_sources=[])
    assert child.as_json()["schema"] == "saea-system-text-policy-bundle-v2"
    assert child.as_json()["context_layout"] == {FIELD: placement}
    assert child.as_json()["cumulative_sources"] == parent.as_json()["cumulative_sources"]
    assert child.bundle_id != parent.bundle_id


@pytest.mark.parametrize("changes", [{"supply": {}}, {"code": "x"},
    {"context_layout": {}}, {"context_layout": {FIELD: True}},
    {"context_layout": {FIELD: "arbitrary"}}, {"context_layout": {FIELD: None, "scorer": "x"}}])
def test_v2_proposals_refuse_unimplemented_or_frozen_surfaces(changes):
    p = {"schema": PROPOSAL, "branch": "L", "round": 1, "slot": 1,
         "parent_ids": ["a" * 64], "changes": changes, "rationale": "Test declared scope.",
         "hypotheses": [], "evidence": []}
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_json(p)


def test_new_scope_requires_exact_prospective_authority_and_protocol(tmp_path):
    protocol = expanded_protocol(tmp_path)
    assert load_optimization_panel(protocol, "update-3", repo_root=tmp_path)
    from speech_aware_evidence_acquisition.rails.system_optimization import optimization_scope_for
    packet = {"round": 3, "optimization_scope": optimization_scope_for(protocol, 3)}
    require_optimization_scope(packet, protocol=protocol)
    assert packet["optimization_scope"]["schema"] == SCOPE
    require_context_only_changes({"context_layout": {FIELD: None}},
        protocol=protocol, stage="update-3", repo_root=tmp_path)
    with pytest.raises(PolicyError):
        require_context_only_changes({"supply": {}}, protocol=protocol,
                                     stage="update-3", repo_root=tmp_path)
    changed = copy.deepcopy(protocol)
    changed["optimization_panel"]["context_authority"]["sha256"] = "c" * 64
    with pytest.raises(PolicyError):
        require_optimization_scope(packet, protocol=changed)
    with pytest.raises(PolicyError):
        load_optimization_panel(changed, "update-3", repo_root=tmp_path)


@pytest.mark.parametrize("fault", ["schema", "missing-pin", "authority-path", "authority-value", "editable"])
def test_expanded_scope_cannot_be_inferred_from_old_protocol(tmp_path, fault):
    protocol = expanded_protocol(tmp_path)
    block = protocol["optimization_panel"]
    if fault == "schema":
        block.pop("schema")
    elif fault == "missing-pin":
        block.pop("context_authority")
    elif fault == "authority-path":
        block["context_authority"] = pin(tmp_path, "other.json", {
            "schema": "saea-owner-context-space-amendment-v1"})
    elif fault == "authority-value":
        block["context_authority"] = pin(tmp_path, AUTHORITY, {"schema": "unknown"})
    else:
        block["editable"].append("supply")
    with pytest.raises(PolicyError):
        load_optimization_panel(protocol, "update-3", repo_root=tmp_path)


@pytest.mark.parametrize("branch", ["L", "B"])
@pytest.mark.parametrize("profile", ["full-index-v1", "typed-coherent-feedback-v1"])
def test_capsules_expose_same_context_contract_without_blind_feedback(tmp_path, branch, profile):
    from test_system_proposer_views import learning_fixture
    packet, roots = learning_fixture(tmp_path) if branch == "L" else fixture(tmp_path)
    packet["optimization_scope"] = scope()
    packet["parent_policy"].update(schema="saea-system-text-policy-bundle-v2", context_layout={FIELD: None})
    packet["parent_bundle_id"] = packet["seed_bundle_id"] = content_hash(packet["parent_policy"])
    reseal(packet)
    capsule = ProposerCapsule.from_packet(packet, roots=roots, view_profile=profile)
    initial = capsule.initial_input()
    assert initial["response_contract"] == TextPolicyUpdateProposal.response_contract(packet)
    assert initial["packet"]["parent_policy"]["context_layout"] == {FIELD: None}
    if branch == "B":
        assert "feedback_summary" not in initial and "feedback_chain" not in initial
        assert "feedback" not in initial["packet"]


@pytest.mark.parametrize("expanded,reply_v2", [(True, True), (True, False), (False, True)])
def test_import_pins_response_schema_and_preserves_spent_invalid_slot(tmp_path, expanded, reply_v2):
    packet, _ = fixture(tmp_path)
    if expanded:
        packet["optimization_scope"] = scope()
    reseal(packet)
    archive = SystemSearchArchive(tmp_path / "archive")
    archive.store_input(packet)
    reply = {"schema": PROPOSAL if reply_v2 else "saea-text-policy-update-proposal-v1",
        "branch": "B", "round": 1, "slot": 1, "parent_ids": [packet["parent_bundle_id"]],
        "changes": {}, "rationale": "No supported revision.", "hypotheses": [], "evidence": []}
    receipt = {"raw_response": json.dumps(reply), "session_id": packet["session_id"],
        "model_version": packet["model_version"], "input_sha256": packet["input_sha256"],
        "input_tokens": 10, "output_tokens": 10}
    result = archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)
    assert result["status"] == ("no-change" if expanded == reply_v2 else "invalid")
    with pytest.raises(PolicyError, match="consumed|exists"):
        archive.import_response(branch="B", round_index=1, slot=1, receipt=receipt)


@pytest.mark.parametrize("profile,scoped,expected", [
    ("full-index-v1", False, "f8e93269224d494243145a53a0486dcd4c2ad5702a4e657684190ee9d6a05408"),
    ("full-index-v1", True, "e1976a798d21a45ee8aefda3dca59b9b056b340374602008bdc2c9c59fffbe13"),
    ("typed-coherent-feedback-v1", False, "77d2e861c5e812a285f834e106f4c36578d9325b4641cd241ef7a69220fe09b8"),
    ("typed-coherent-feedback-v1", True, "0000733c3e0a4c3c8244a1f6baa07dd5771b20c96105248a569b40103045124c"),
])
def test_legacy_outbound_requests_retain_prechange_bytes(tmp_path, profile, scoped, expected):
    packet, roots = fixture(tmp_path)
    if scoped:
        packet["optimization_scope"] = {"purpose": "reused-optimization-panel",
            "editable": ["role_text"], "plan_sha256": "a" * 64}
    reseal(packet)
    assert content_hash(ProposerCapsule.from_packet(packet, roots=roots,
        view_profile=profile).request()) == expected


def test_successor_context_scope_preserves_spent_and_held_custody(tmp_path):
    from test_system_search_successor import setup
    from speech_aware_evidence_acquisition.rails.system_search_successor import build_successor, register_successor
    from speech_aware_evidence_acquisition.rails.system_search_archive import proposal_input
    from speech_aware_evidence_acquisition.rails.system_optimization import optimization_scope_for
    old, new, repo, seed, legacy, args = setup(tmp_path)
    protocol = expanded_protocol(repo)
    decision = json.loads((repo / args["transition"]["relpath"]).read_text())
    decision["context_authority"] = protocol["optimization_panel"]["context_authority"]
    args["transition"] = pin(repo, "context-transition.json", decision)
    successor = build_successor(old, new, **args)
    assert successor["schema"] == "saea-system-search-successor-sequence-v2"
    assert successor["earlier_allocations"] == legacy["earlier_allocations"]
    assert successor["held_allocations"] == legacy["held_allocations"]
    register_successor(old, new, successor, repo_root=repo)
    assert new.allocation_extension(4) == successor
    protocol["allocation_extension"] = successor
    protocol["optimization_panel"]["stages"] = ["update-4"]
    assert load_optimization_panel(protocol, "update-4", repo_root=repo)
    packet = proposal_input(branch="B", round_index=4, slot=1, seed=seed, parent=seed,
        model_version=successor["model_version"], session_id="context-fresh",
        input_token_cap=successor["input_token_cap"], output_token_cap=successor["output_token_cap"],
        allocation_extension=successor)
    packet["optimization_scope"] = optimization_scope_for(protocol, 4)
    reseal(packet)
    new.store_input(packet)
    reply = TextPolicyUpdateProposal.response_contract(packet)["example"]
    assert TextPolicyUpdateProposal.from_json(reply, allocation_extension=successor)
    with pytest.raises(PolicyError):
        TextPolicyUpdateProposal.from_json(reply, allocation_extension=legacy)
    protocol["allocation_extension"] = legacy
    with pytest.raises(PolicyError):
        load_optimization_panel(protocol, "update-4", repo_root=repo)
    for key in legacy["held_allocations"]:
        assert not (new.root / "inputs" / (key + ".json")).exists()


@pytest.mark.parametrize("fault", ["unbound-transition", "wrong-authority"])
def test_context_successor_refuses_silent_scope_expansion(tmp_path, fault):
    from test_system_search_successor import setup
    from speech_aware_evidence_acquisition.rails.system_search_successor import validate_successor
    old, new, repo, _, doc, _ = setup(tmp_path)
    protocol = expanded_protocol(repo)
    doc.update(schema="saea-system-search-successor-sequence-v2",
        editable=["role_text", "context_layout"],
        context_authority=protocol["optimization_panel"]["context_authority"])
    if fault == "wrong-authority":
        doc["context_authority"] = pin(repo, "other-authority.json", {})
    with pytest.raises(PolicyError):
        validate_successor(new, doc, repo_root=repo, preparing=True)
