"""Unit tests for the E2 grouped-Solver COMMIT policy (SLURP v2 base program
M2): plurality intent, tie-break, entity clustering, medoid selection,
min_support and malformed-vote handling."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
from speech_aware_evidence_acquisition.rails import commit_policies as commit_policies_module
from speech_aware_evidence_acquisition.rails.commit_policies import (
    PLURALITY_SUPPORT_V1,
    CommitPolicyError,
    ParsedSlurpAnswer,
    SolverSampleVote,
    character_level_f1,
    commit_plurality_support_v1,
)


def _answer(scenario, action, entities=()):
    return ParsedSlurpAnswer(
        scenario=scenario, action=action,
        entities=tuple(SlotEntity(type=t, filler=f) for t, f in entities),
    )


def _vote(index, answer):
    return SolverSampleVote(sample_index=index, parsed=answer)


def test_registration_is_visible_in_core_base():
    assert commit_policies_module  # module import triggers registration
    assert COMMIT_POLICIES.resolve(PLURALITY_SUPPORT_V1) is commit_plurality_support_v1


def test_character_level_f1_is_symmetric_and_bounded():
    assert character_level_f1("", "") == 1.0
    assert character_level_f1("abc", "") == 0.0
    assert character_level_f1("", "abc") == 0.0
    assert character_level_f1("kitchen", "kitchen") == 1.0
    assert character_level_f1("kitchen", "the kitchen") == character_level_f1("the kitchen", "kitchen")
    assert 0.0 < character_level_f1("kitchen", "kitchan") < 1.0


def test_character_level_f1_requires_strings():
    with pytest.raises(CommitPolicyError):
        character_level_f1("a", 1)


def test_plurality_intent_majority_wins():
    votes = [
        _vote(0, _answer("alarm", "set")),
        _vote(1, _answer("alarm", "set")),
        _vote(2, _answer("alarm", "cancel")),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)
    assert (outcome.answer.scenario, outcome.answer.action) == ("alarm", "set")
    assert outcome.intent_support == 2
    assert outcome.intent_member_sample_indices == (0, 1)
    assert outcome.intent_tie_break_sample_index is None


def test_plurality_intent_tie_breaks_on_lowest_first_occurrence_sample_index():
    votes = [
        _vote(0, _answer("alarm", "cancel")),
        _vote(1, _answer("alarm", "set")),
        _vote(2, _answer("alarm", "set")),
        _vote(3, _answer("alarm", "cancel")),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)
    # "cancel" first seen at 0, "set" first seen at 1: cancel wins the tie.
    assert (outcome.answer.scenario, outcome.answer.action) == ("alarm", "cancel")
    assert outcome.intent_support == 2
    assert outcome.intent_tie_break_sample_index == 0


def test_malformed_samples_cast_no_vote_but_do_not_break_the_others():
    votes = [
        _vote(0, _answer("alarm", "set")),
        _vote(1, None),
        _vote(2, _answer("alarm", "set")),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)
    assert outcome.intent_support == 2
    assert outcome.intent_member_sample_indices == (0, 2)


def test_every_sample_malformed_fails_closed_to_empty_answer():
    votes = [_vote(0, None), _vote(1, None)]
    outcome = commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)
    assert outcome.answer.scenario == ""
    assert outcome.answer.action == ""
    assert outcome.answer.entities == ()
    assert outcome.intent_support == 0
    assert outcome.intent_member_sample_indices == ()
    assert outcome.entities == ()


def test_entity_clustering_keeps_only_clusters_at_or_above_min_support():
    votes = [
        _vote(0, _answer("alarm", "set", [("time", "six am")])),
        _vote(1, _answer("alarm", "set", [("time", "six a m")])),
        _vote(2, _answer("alarm", "set", [("time", "nine pm")])),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=2, similarity_threshold=0.6)
    fillers = {(e.type, e.filler) for e in outcome.entities}
    assert ("time", "nine pm") not in fillers  # support 1 < min_support 2
    assert any(t == "time" for t, _ in fillers)  # the "six am"/"six a m" cluster survives
    (kept,) = [e for e in outcome.entities if e.type == "time"]
    assert kept.support == 2
    assert kept.member_sample_indices == (0, 1)


def test_entity_clustering_threshold_separates_dissimilar_fillers():
    votes = [
        _vote(0, _answer("alarm", "set", [("time", "six am")])),
        _vote(1, _answer("alarm", "set", [("time", "nine pm")])),
        _vote(2, _answer("alarm", "set", [("time", "six am")])),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=2, similarity_threshold=0.95)
    kept_types = [(e.type, e.filler, e.support) for e in outcome.entities]
    assert kept_types == [("time", "six am", 2)]


def test_medoid_is_the_member_with_highest_mean_similarity_tie_breaks_low_index():
    # Two identical spellings and one slightly different one: the identical
    # pair's members tie for highest mean similarity, so the lower
    # sample_index wins as the medoid and the tie is recorded.
    votes = [
        _vote(0, _answer("alarm", "set", [("time", "six am")])),
        _vote(1, _answer("alarm", "set", [("time", "six am")])),
        _vote(2, _answer("alarm", "set", [("time", "six a m")])),
    ]
    outcome = commit_plurality_support_v1(votes, min_support=3, similarity_threshold=0.5)
    (entity,) = outcome.entities
    assert entity.filler == "six am"
    assert entity.support == 3
    assert entity.tie_break_sample_index == 0


def test_min_support_and_similarity_threshold_are_validated():
    votes = [_vote(0, _answer("alarm", "set"))]
    with pytest.raises(CommitPolicyError, match="min_support"):
        commit_plurality_support_v1(votes, min_support=0, similarity_threshold=0.8)
    with pytest.raises(CommitPolicyError, match="similarity_threshold"):
        commit_plurality_support_v1(votes, min_support=1, similarity_threshold=1.5)
    with pytest.raises(CommitPolicyError, match="similarity_threshold"):
        commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.0)


def test_votes_must_be_ordered_by_distinct_ascending_sample_index():
    votes = [_vote(1, _answer("a", "b")), _vote(0, _answer("a", "b"))]
    with pytest.raises(CommitPolicyError, match="ordered"):
        commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)
    votes = [_vote(0, _answer("a", "b")), _vote(0, _answer("a", "b"))]
    with pytest.raises(CommitPolicyError, match="ordered"):
        commit_plurality_support_v1(votes, min_support=1, similarity_threshold=0.8)


def test_deterministic_repeat_calls_produce_the_same_outcome():
    votes = [
        _vote(0, _answer("alarm", "set", [("time", "six am")])),
        _vote(1, _answer("alarm", "set", [("time", "six a m")])),
        _vote(2, _answer("alarm", "cancel", [("time", "nine pm")])),
    ]
    first = commit_plurality_support_v1(votes, min_support=2, similarity_threshold=0.6)
    second = commit_plurality_support_v1(votes, min_support=2, similarity_threshold=0.6)
    assert first == second
