"""A derived SLURP proposal extends cards without changing the original dose."""

from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    A2T_CANDIDATE_SEMANTIC_PROVIDER_ID,
    SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    SlurpCandidateSemanticProvider,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.errors import RailsError

from test_candidate_semantic_supply import _config
from test_slurp_candidate_proposal import _build, _state


def _provider(tmp_path, *, fallback=()):
    config, inventory = _config(tmp_path, inventory=("alpha", "beta", "gamma", "delta", "epsilon"))
    snapshot = load_knowledge_store_binding(config, data_root=tmp_path).store("slot-contracts").snapshot
    provider = SlurpCandidateSemanticProvider(
        candidate_values={
            "alpha": ("slot-contract:alpha_one", "slot-contract:shared"),
            "beta": ("slot-contract:beta_one", "slot-contract:shared"),
            "gamma": ("slot-contract:alpha_one", "slot-contract:gamma_one", "slot-contract:unused"),
            "delta": ("slot-contract:gamma_one", "slot-contract:unused"),
        },
        legal_candidate_ids=inventory, max_candidates=3,
        max_values_per_candidate=2, max_total_values=4,
        compact_source_phase="perception",
        projection_policy="bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
        fallback_candidates=fallback,
    ).adopt(
        snapshot, policy_id=snapshot.builder_policy_id,
        source_ids=snapshot.source_sample_ids,
        snapshot_sha256=snapshot.content_hash(),
    )
    state = _state()
    query_state = QueryState(
        query_id="query:row-1", query_sample_id="row-1",
        speech_packet_id="packet:row-1", speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()
    base = {"query_state": query_state, "candidate_state": state, "sample_id": "row-1"}
    return provider, base


def test_proposal_preserves_baseline_prefix_and_adds_unique_cards(tmp_path):
    provider, query = _provider(tmp_path)
    provider.candidates(query, k=4)
    baseline = provider.fuse(
        [provider.candidates(query, k=4)], k=4,
        policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    ).selected_value_ids
    assert baseline == (
        "slot-contract:alpha_one", "slot-contract:beta_one", "slot-contract:shared",
    )
    baseline_audit = provider.last_selection_audit()
    assert "candidate_proposal_sha256" not in baseline_audit
    proposal = _build(original_state=query["candidate_state"])
    augmented = {**query, "candidate_proposal": proposal,
                 "candidate_proposal_added_value_cap": 2}
    ranking = provider.candidates(augmented, k=6)
    decision = provider.fuse(
        [ranking], k=6, policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    )
    assert decision.selected_value_ids[:len(baseline)] == baseline
    assert decision.selected_value_ids[len(baseline):] == (
        "slot-contract:gamma_one", "slot-contract:unused",
    )
    audit = provider.last_selection_audit()
    assert audit["candidate_proposal_sha256"] == proposal.content_hash()
    assert audit["candidate_proposal_original_ids"] == ["alpha", "beta"]
    assert audit["candidate_proposal_baseline_value_ids"] == list(baseline)
    assert audit["candidate_proposal_added_value_ids"] == [
        "slot-contract:gamma_one", "slot-contract:unused",
    ]
    assert audit["candidate_proposal_added_value_cap"] == 2
    mappings = {item["candidate_id"]: item for item in audit["mappings"]}
    assert {"gamma", "delta"} <= mappings.keys()
    assert any(item["reason"] == "shared-value-already-selected"
               for item in mappings["gamma"]["ignored_mappings"])
    with pytest.raises(RailsError):
        provider.fuse([ranking], k=4, policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID)


@pytest.mark.parametrize("mutate", [
    lambda p: replace(p, sample_id="another"),
    lambda p: replace(p, original_state_sha256="f" * 64),
    lambda p: replace(p, original_response_sha256="f" * 64),
    lambda p: replace(p, original_candidate_ids=("gamma",)),
    lambda p: replace(p, candidate_ids=("alpha", "beta", "illegal")),
    lambda p: replace(p, candidate_ids=("alpha", "beta", "gamma", "gamma")),
])
def test_proposal_identity_and_inventory_are_checked(tmp_path, mutate):
    provider, query = _provider(tmp_path)
    with pytest.raises(RailsError):
        provider.candidates({
            **query, "candidate_proposal": mutate(_build(original_state=query["candidate_state"])),
            "candidate_proposal_added_value_cap": 2,
        }, k=6)


@pytest.mark.parametrize("proposal,cap,k", [
    ("unsupported", 2, 6), (None, 2, 6),
    ("real", None, 4), ("real", 0, 4),
    ("real", True, 5), ("real", 999, 1003),
])
def test_proposal_requires_bounded_coherent_budget(tmp_path, proposal, cap, k):
    provider, query = _provider(tmp_path)
    if proposal == "real":
        proposal = _build(original_state=query["candidate_state"])
    with pytest.raises(RailsError):
        provider.candidates({
            **query, "candidate_proposal": proposal,
            "candidate_proposal_added_value_cap": cap,
        }, k=k)


def test_proposal_rejected_with_fallback_or_audio2tool_provider(tmp_path):
    provider, query = _provider(tmp_path, fallback=("epsilon",))
    proposal = _build(original_state=query["candidate_state"])
    with pytest.raises(RailsError):
        provider.candidates({
            **query, "candidate_proposal": proposal,
            "candidate_proposal_added_value_cap": 2,
        }, k=6)
    provider._provider_id = A2T_CANDIDATE_SEMANTIC_PROVIDER_ID
    with pytest.raises(RailsError):
        provider.candidates({
            **query, "candidate_proposal": proposal,
            "candidate_proposal_added_value_cap": 2,
        }, k=6)


def test_proposal_with_no_new_intents_keeps_baseline_cards(tmp_path):
    provider, query = _provider(tmp_path)
    proposal = _build(
        original_state=query["candidate_state"],
        exemplar_values=(),
    )
    ranking = provider.candidates({
        **query, "candidate_proposal": proposal,
        "candidate_proposal_added_value_cap": 2,
    }, k=6)
    decision = provider.fuse(
        [ranking], k=6, policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    )
    assert decision.selected_value_ids == (
        "slot-contract:alpha_one", "slot-contract:beta_one", "slot-contract:shared",
    )
    assert provider.last_selection_audit()["candidate_proposal_added_value_ids"] == []

