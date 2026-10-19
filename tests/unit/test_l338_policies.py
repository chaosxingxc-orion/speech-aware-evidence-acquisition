"""Decision 338: first-support commit policy and candidate-union merge policy."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES, PERCEPTION_MERGE_POLICIES
from speech_aware_evidence_acquisition.rails import commit_policies as cp
from speech_aware_evidence_acquisition.rails import perception_merge_policies as mp
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity


def _ans(*entities, scenario="alarm", action="set"):
    return cp.ParsedSlurpAnswer(
        scenario=scenario, action=action,
        entities=tuple(SlotEntity(type=t, filler=f) for t, f in entities),
    )


def _votes(*answers):
    return [cp.SolverSampleVote(sample_index=i, parsed=a) for i, a in enumerate(answers)]


def test_registries_resolve_new_ids():
    assert COMMIT_POLICIES.resolve(cp.FIRST_SUPPORT_V1) is cp.commit_first_support_v1
    assert cp.FIRST_SUPPORT_V1 == "saea-commit-first-support-v1"
    assert PERCEPTION_MERGE_POLICIES.resolve(mp.CANDIDATE_UNION_V1) is mp.merge_candidate_union_v1
    assert mp.CANDIDATE_UNION_V1 == "saea-perception-candidate-union-v1"


def test_support_filter_keeps_labels_and_supported_entities():
    votes = _votes(
        _ans(("time", "seven am"), ("date", "monday")),
        _ans(("time", "seven am")),
        _ans(("time", "seven am"), ("place", "kitchen")),
        _ans(), _ans(),
    )
    out = cp.commit_first_support_v1(votes, min_support=2, similarity_threshold=0.8)
    assert (out.answer.scenario, out.answer.action) == ("alarm", "set")
    assert [(e.type, e.filler) for e in out.entities] == [("time", "seven am")]
    assert out.entities[0].support == 3 and out.entities[0].member_sample_indices == (0, 1, 2)
    assert out.gate is None


def test_support_filter_labels_never_move_and_malformed_sample_zero_uses_lowest_valid():
    votes = [
        cp.SolverSampleVote(0, None),
        cp.SolverSampleVote(1, _ans(("time", "noon"), scenario="calendar", action="query")),
        cp.SolverSampleVote(2, _ans(("time", "noon"), scenario="alarm", action="set")),
    ]
    out = cp.commit_first_support_v1(votes, min_support=2, similarity_threshold=0.8)
    assert (out.answer.scenario, out.answer.action) == ("calendar", "query")
    assert [e.filler for e in out.entities] == ["noon"]


def test_all_malformed_fails_closed_to_empty():
    out = cp.commit_first_support_v1(
        [cp.SolverSampleVote(0, None), cp.SolverSampleVote(1, None)],
        min_support=2, similarity_threshold=0.8,
    )
    assert out.answer.scenario == "" and out.entities == ()


def _gate_votes(empty_others):
    answers = [_ans(("time", "seven am"))] + [_ans() for _ in range(empty_others)]
    answers += [_ans(("time", "seven am"))] * (4 - empty_others)
    return _votes(*answers)


@pytest.mark.parametrize("n1,empties,fires", [
    (0.2, 3, True), (0.19, 3, False), (0.5, 2, False), (0.5, 4, True), (0.0, 4, False),
])
def test_n1_gate(n1, empties, fires):
    out = cp.commit_first_support_v1(
        _gate_votes(empties), min_support=1, similarity_threshold=0.8,
        n1=n1, n1_min=0.2, empty_votes_min=3,
    )
    assert out.gate["status"] == ("fired" if fires else "not-fired")
    assert (out.entities == ()) is fires
    assert (out.answer.entities == ()) is fires
    assert out.answer.action == "set"


def test_gate_without_n1_does_not_fire_and_says_so():
    out = cp.commit_first_support_v1(
        _gate_votes(4), min_support=1, similarity_threshold=0.8, n1_min=0.2, empty_votes_min=3,
    )
    assert out.gate["status"] == "n1-unavailable" and len(out.entities) == 1


def test_malformed_sample_casts_no_empty_vote():
    votes = _votes(_ans(("time", "x")), _ans(), _ans())
    votes += [cp.SolverSampleVote(3, None), cp.SolverSampleVote(4, None)]
    out = cp.commit_first_support_v1(
        votes, min_support=1, similarity_threshold=0.8, n1=0.9, n1_min=0.2, empty_votes_min=3,
    )
    assert out.gate["empty_votes"] == 2 and out.gate["status"] == "not-fired"


@pytest.mark.parametrize("kwargs", [
    {"min_support": 0, "similarity_threshold": 0.8},
    {"min_support": 2, "similarity_threshold": 0},
    {"min_support": 2, "similarity_threshold": 0.8, "n1_min": 0.2},
    {"min_support": 2, "similarity_threshold": 0.8, "n1_min": 1.5, "empty_votes_min": 3},
    {"min_support": 2, "similarity_threshold": 0.8, "n1": 2.0},
])
def test_parameter_refusals(kwargs):
    with pytest.raises(cp.CommitPolicyError):
        cp.commit_first_support_v1(_votes(_ans()), **kwargs)


def test_union_ordering_and_cap():
    out = mp.merge_candidate_union_v1(
        [["a", "b"], ["a", "c", "d"], ["c", "e"], ["d", "c"]], cap=4,
    )
    # sample 0 verbatim; then c (3 samples), d (2 samples), e (1)
    assert out.merged_candidate_ids == ("a", "b", "c", "d")
    assert out.appended_candidate_ids == ("c", "d")
    assert out.truncated is True
    assert dict(out.support_counts)["c"] == 3 and dict(out.best_ranks)["d"] == 1


def test_union_tie_breaks_on_best_rank_then_id():
    out = mp.merge_candidate_union_v1([["a"], ["z", "b"], ["y", "c"]], cap=5)
    # b, c, y, z all have support 1; best rank: z=1,y=1,b=2,c=2 -> y,z then b,c
    assert out.merged_candidate_ids == ("a", "y", "z", "b", "c")


def test_union_never_displaces_rank_one_and_truncates_sample_zero():
    out = mp.merge_candidate_union_v1([["a", "b", "c", "d"], ["x"]], cap=3)
    assert out.merged_candidate_ids == ("a", "b", "c") and out.appended_candidate_ids == ()


def test_union_with_unusable_sample_zero_and_none_lists():
    out = mp.merge_candidate_union_v1([None, ["b", "a"], ["a"]], cap=3)
    assert out.merged_candidate_ids == ("a", "b") and out.usable_samples == 2


def test_union_cap_three_with_duplicates_collapsed():
    out = mp.merge_candidate_union_v1([["a", "a", "b"], ["b"]], cap=3)
    assert out.merged_candidate_ids == ("a", "b")


@pytest.mark.parametrize("bad", [[], "ab", [["a", 1]], [[""]]])
def test_union_refuses_malformed_lists(bad):
    with pytest.raises(mp.MergePolicyError):
        mp.merge_candidate_union_v1(bad, cap=3)


@pytest.mark.parametrize("cap", [0, -1, True, 2.5])
def test_union_refuses_bad_cap(cap):
    with pytest.raises(mp.MergePolicyError):
        mp.merge_candidate_union_v1([["a"]], cap=cap)
