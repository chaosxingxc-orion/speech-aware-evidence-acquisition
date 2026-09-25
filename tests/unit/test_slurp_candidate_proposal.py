"""Pure, source-bound proposal construction from selected TRAIN exemplars."""

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import seal_phase_response_state
from speech_aware_evidence_acquisition.rails.knowledge import ValueBundle
from speech_aware_evidence_acquisition.rails.slurp_candidate_proposal import (
    CandidateProposalError, build_candidate_proposal,
)

SHA = "a" * 64
LEGAL = ("alpha", "beta", "gamma", "delta", "epsilon")


def _state(ids=("alpha", "beta", "alpha")):
    content = json.dumps({"candidates": [
        {"intent_id": intent, "distinction": "A speech intent",
         "evidence_refs": [], "unresolved_fields": []}
        for intent in ids
    ]})
    return seal_phase_response_state(
        phase_name="perception", sample_id="row-1", state_content=content,
        raw_response_text=content, source_query_state_sha256=SHA,
        producer_policy_id="synthetic-policy",
    )


def _value(value_id, target):
    return ValueBundle(
        value_id=value_id, content=f"TRAIN speech exemplar {value_id}",
        associated_facet_ids=("facet",), source_sample_ids=("train-1",),
        provenance_refs=("train-source",), task_target=target,
    ).validate()


def _build(**overrides):
    args = dict(
        sample_id="row-1", original_state=_state(),
        parsed_candidates=("alpha", "beta"),
        exemplar_values=(
            _value("v1", "gamma"), _value("v2", "delta"),
            _value("v3", "gamma"), _value("v4", "epsilon"),
            _value("v5", "delta"), _value("v6", "alpha"),
        ),
        exemplar_snapshot_sha256="b" * 64,
        exemplar_selection_sha256="c" * 64,
        legal_candidate_ids=LEGAL, max_candidates=4,
    )
    args.update(overrides)
    return build_candidate_proposal(**args)


def test_retains_originals_then_frequency_and_lexical_tie_with_support():
    original = _state()
    result = _build(original_state=original)
    assert result.original_candidate_ids == ("alpha", "beta")
    assert result.candidate_ids == ("alpha", "beta", "delta", "gamma")
    assert [(item.intent_id, item.supporting_exemplar_value_ids) for item in result.additions] == [
        ("delta", ("v2", "v5")), ("gamma", ("v1", "v3")),
    ]
    assert result.original_state_sha256 == original.content_hash()
    assert result.original_response_sha256 == original.source_response_sha256
    assert result.as_json()["selected_exemplars"][0]["content_sha256"] == hashlib.sha256(
        _value("v1", "gamma").content.encode()
    ).hexdigest()
    assert result.content_hash() != _build(max_candidates=3).content_hash()
    text = result.model_text()
    assert "Original Perception" in text and "exemplar-supported" in text
    assert "not confidence" in text and "full legal" in text
    assert all(secret not in text for secret in (
        "row-1", "train-1", SHA, "v1", "synthetic-policy", "TRAIN speech exemplar v1",
    ))
    assert original == _state()
    assert "gold" not in result.as_json()


@pytest.mark.parametrize("change", [
    {"parsed_candidates": ("alpha", "gamma")},
    {"parsed_candidates": ("alpha", "alpha")},
    {"exemplar_values": (_value("v1", "gamma"), _value("v1", "delta"))},
    {"exemplar_values": (_value("v1", "not-legal"),)},
    {"exemplar_values": (_value("v1", None),)},
    {"exemplar_snapshot_sha256": "bad"},
    {"exemplar_selection_sha256": "bad"},
    {"max_candidates": 1},
    {"max_candidates": 33},
    {"sample_id": "another-row"},
])
def test_rejects_invalid_selection_or_identity(change):
    with pytest.raises(CandidateProposalError):
        _build(**change)


def test_rejects_source_content_mutation_and_foreign_phase():
    source = _state()
    with pytest.raises(CandidateProposalError):
        _build(original_state=replace(source, content=source.content + " "))
    with pytest.raises(CandidateProposalError):
        _build(original_state=replace(source, state_kind="phase:solver"))


def test_zero_additions_retains_originals():
    result = _build(exemplar_values=(_value("v1", "alpha"),), max_candidates=8)
    assert result.candidate_ids == result.original_candidate_ids
    assert result.additions == ()



def test_bound_selection_constructor_refuses_wrong_query_snapshot_or_values():
    from speech_aware_evidence_acquisition.rails.controllers import PhaseSupply
    from speech_aware_evidence_acquisition.rails.knowledge import (
        KnowledgeSnapshot, FusionDecision, RankResult, RankedFacet,
    )
    from speech_aware_evidence_acquisition.rails.slurp_candidate_proposal import (
        build_candidate_proposal_from_selection,
    )
    from test_rails_runner import _knowledge_snapshot
    from test_phase_planner import _context

    base = _knowledge_snapshot()
    facet = base.facets[0].facet_id
    values = tuple(replace(v, associated_facet_ids=(facet,),
                           source_sample_ids=base.values[0].source_sample_ids)
                   for v in (_value("v1", "gamma"), _value("v2", "delta")))
    snapshot = replace(base, values=values).validate()
    query = replace(_context().query_state, query_sample_id="row-1").validate()
    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(), ranking_policy_id="synthetic-rank",
        candidates=(RankedFacet(facet_id=facet, score=1.0),),
    ).validate()
    fusion = FusionDecision(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query.content_hash(), rank_result_sha256=rank.content_hash(),
        fusion_policy_id="synthetic-fuse", supporting_facet_ids=(facet,),
        selected_value_ids=("v1", "v2"),
    ).validate()
    supply = PhaseSupply(rank_result=rank, fusion_decision=fusion).validate()
    kwargs = dict(
        sample_id="row-1", original_state=_state(), parsed_candidates=("alpha", "beta"),
        exemplar_snapshot=snapshot, exemplar_supply=supply, query_state=query,
        legal_candidate_ids=LEGAL, max_candidates=8,
    )
    proposal = build_candidate_proposal_from_selection(**kwargs)
    assert proposal.candidate_ids == ("alpha", "beta", "delta", "gamma")
    assert proposal.exemplar_selection_sha256 == fusion.content_hash()
    assert proposal.exemplar_snapshot_sha256 == snapshot.content_hash()
    for changed in (
        {"query_state": replace(query, query_sample_id="wrong-row")},
        {"exemplar_snapshot": replace(snapshot, snapshot_id="changed")},
        {"exemplar_supply": replace(supply, fusion_decision=replace(fusion, rank_result_sha256="f"*64))},
        {"exemplar_supply": replace(supply, fusion_decision=replace(fusion, selected_value_ids=("absent",)))},
    ):
        with pytest.raises(CandidateProposalError):
            build_candidate_proposal_from_selection(**(kwargs | changed))
