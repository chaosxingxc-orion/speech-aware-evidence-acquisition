"""Pure numeric finite-policy tests; synthetic identities and counts only."""

from dataclasses import FrozenInstanceError, replace
import math

import pytest

from speech_aware_evidence_acquisition.rails.finite_action_policy import (
    CountSum, FinitePolicyError, PolicySnapshot, RoundDescriptor, TerminalFeedback,
    official_utility, sample_action, sample_balanced_round, update_complete_round,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def sha(number: int) -> str:
    return f"{number:064x}"


def snapshot() -> PolicySnapshot:
    return PolicySnapshot.create(actions=("default", "examples"), states=("empty", "agree"), f0=0.8)


def terminal(sid: str, index: int, decision, *, tp=1, fp=0, fn=0, action=None):
    return TerminalFeedback(
        sample_id=sid, trajectory_sha256=sha(index), source_hashes=(("scores", sha(900)),),
        decision=decision, action=action or decision.action,
        logged_propensity=decision.propensity, tp=tp, fp=fp, fn=fn,
        intent_exact=1, format_ok=True, fallback_flags=(),
    )


def descriptor(policy, ids, *, round_id="r1", epsilon=1.0, kind="epsilon-greedy", quotas=()):
    return RoundDescriptor(round_id, tuple(ids), sha(800), policy.sha256,
                           epsilon, kind, tuple(quotas))


def test_utility_penalizes_empty_gold_false_positive_and_rejects_boolean():
    assert official_utility(tp=0, fp=0, fn=0, f0=0.8) == 0
    assert official_utility(tp=0, fp=1, fn=0, f0=0.8) == -0.8
    assert official_utility(tp=0, fp=0, fn=1, f0=0.8) == -0.8
    for value in (True, -1, math.nan, math.inf):
        with pytest.raises(FinitePolicyError):
            official_utility(tp=0, fp=value, fn=0, f0=0.8)


def test_tie_order_unknown_global_zero_and_epsilon_probability_endpoints():
    policy = snapshot()
    assert policy.preferred_action("empty") == "default"
    zero = sample_action(policy, state_id="empty", epsilon=0, draw=0.99)
    assert zero.action == "default" and zero.probabilities == (1.0, 0.0) and zero.propensity == 1
    mixed = sample_action(policy, state_id="empty", epsilon=0.2, draw=0.89)
    assert mixed.action == "default" and mixed.probabilities == (0.9, 0.1)
    assert sample_action(policy, state_id="empty", epsilon=0.2, draw=0.9).action == "examples"
    uniform = sample_action(policy, state_id="empty", epsilon=1, draw=0.5)
    assert uniform.action == "examples" and uniform.probabilities == (0.5, 0.5)
    with pytest.raises(FinitePolicyError):
        sample_action(policy, state_id="empty", epsilon=1, draw=1)


def test_snapshot_immutable_canonical_hash_and_complete_round_credit():
    before = snapshot()
    same = snapshot()
    assert before.sha256 == same.sha256 == content_hash(before.as_json())
    decision = sample_action(before, state_id="empty", epsilon=1, draw=0.9)
    after = update_complete_round(before, descriptor(before, ("s1",)),
                                  (terminal("s1", 1, decision, tp=0, fp=1),))
    assert before.global_stats == (CountSum(), CountSum())
    assert after.global_stats[1] == CountSum(1, -0.8)
    assert after.parent_sha256 == before.sha256 and after.sha256 != before.sha256
    assert after.credited[0].fp == 1 and after.credited[0].source_hashes == (("scores", sha(900)),)
    assert after.credited[0].round_descriptor_sha256 == descriptor(before, ("s1",)).sha256
    assert after.credited[0].decision == decision
    assert after.credited[0].decision.as_json()["probabilities"] == [0.5, 0.5]
    with pytest.raises(FrozenInstanceError):
        after.f0 = 0.5
    with pytest.raises(FinitePolicyError, match="credited utility"):
        replace(after, credited=(replace(after.credited[0], utility=0.0),),
                global_stats=(CountSum(), CountSum(1, 0.0)),
                cell_stats=(CountSum(), CountSum(1, 0.0), CountSum(), CountSum()))
    with pytest.raises(FinitePolicyError, match="already credited|duplicate"):
        update_complete_round(after, descriptor(after, ("s1",), round_id="r1"),
                              (terminal("s1", 1, sample_action(after, state_id="empty", epsilon=1, draw=0.9)),))


def test_sparse_cell_uses_same_action_global_mean_until_twenty():
    policy = snapshot()
    ids = tuple(f"s{i}" for i in range(39))
    rows = []
    for index, sid in enumerate(ids):
        state = "empty" if index < 19 else "agree"
        draw = 0.9 if index < 19 else 0.1
        decision = sample_action(policy, state_id=state, epsilon=1, draw=draw)
        rows.append(terminal(sid, index + 1, decision,
                             tp=1 if index < 19 else 0,
                             fn=0 if index < 19 else 1))
    updated = update_complete_round(policy, descriptor(policy, ids), rows)
    assert updated.cell_stats[1].count == 19
    assert updated.global_stats[1].count == 19
    assert updated.preferred_action("empty") == "examples"
    assert updated.preferred_action("agree") == "examples"


def test_sparse_cell_switches_from_global_to_local_at_twenty():
    policy = snapshot()
    ids = tuple(f"s{i}" for i in range(49))
    rows = []
    for index, sid in enumerate(ids):
        state = "empty" if index < 19 else "agree"
        decision = sample_action(policy, state_id=state, epsilon=1, draw=0.1)
        rows.append(terminal(sid, index + 1, decision,
                             tp=1 if index < 19 else 0,
                             fn=0 if index < 19 else 1))
    after_19 = update_complete_round(policy, descriptor(policy, ids), rows)
    assert after_19.cell_stats[0].count == 19
    assert after_19.global_stats[0].mean < 0
    assert after_19.preferred_action("empty") == "examples"
    next_decision = sample_action(after_19, state_id="empty", epsilon=1, draw=0.1)
    after_20 = update_complete_round(
        after_19, descriptor(after_19, ("s49",), round_id="r2"),
        (terminal("s49", 50, next_decision, tp=1),),
    )
    assert after_20.cell_stats[0].count == 20
    assert after_20.preferred_action("empty") == "default"


def test_round_refuses_partial_duplicate_conflicting_action_policy_and_propensity():
    policy = snapshot()
    decisions = [sample_action(policy, state_id="empty", epsilon=1, draw=draw)
                 for draw in (0.1, 0.9)]
    ids = ("s1", "s2")
    rows = (terminal("s1", 1, decisions[0]), terminal("s2", 2, decisions[1]))
    desc = descriptor(policy, ids)
    for bad in ((rows[0],), (rows[0], rows[0])):
        with pytest.raises(FinitePolicyError, match="complete|ids"):
            update_complete_round(policy, desc, bad)
    for bad_row in (
        replace(rows[1], trajectory_sha256=rows[0].trajectory_sha256),
        replace(rows[1], action="default"),
        replace(rows[1], logged_propensity=0.4),
        replace(rows[1], decision=replace(rows[1].decision, snapshot_sha256=sha(77))),
    ):
        with pytest.raises(FinitePolicyError):
            update_complete_round(policy, desc, (rows[0], bad_row))
    after = update_complete_round(policy, desc, rows)
    next_decision = sample_action(after, state_id="empty", epsilon=1, draw=0.1)
    with pytest.raises(FinitePolicyError, match="duplicate or conflicting"):
        update_complete_round(after, descriptor(after, ("s3",), round_id="r2"),
                              (terminal("s3", 1, next_decision),))


def test_balanced_without_replacement_uses_conditional_probabilities_and_replays():
    policy = snapshot()
    roster = (("s1", "empty"), ("s2", "empty"), ("s3", "agree"))
    decisions = sample_balanced_round(policy, roster_states=roster,
                                      initial_quotas=(2, 1), draws=(0.1, 0.9, 0.7))
    assert tuple(decision.action for decision in decisions) == ("default", "examples", "default")
    assert tuple(decision.probabilities for decision in decisions) == ((2 / 3, 1 / 3), (0.5, 0.5), (1.0, 0.0))
    rows = tuple(terminal(sid, index + 1, decision)
                 for index, ((sid, _), decision) in enumerate(zip(roster, decisions, strict=True)))
    desc = descriptor(policy, (sid for sid, _ in roster), epsilon=None,
                      kind="balanced-without-replacement", quotas=(2, 1))
    assert len(update_complete_round(policy, desc, rows).credited) == 3
    with pytest.raises(FinitePolicyError, match="allocation|probability"):
        update_complete_round(policy, desc, (rows[0], replace(rows[1], decision=replace(
            rows[1].decision, probabilities=(0.5, 0.5), allocation_kind="epsilon-greedy",
            epsilon=1.0)), rows[2]))
    with pytest.raises(FinitePolicyError, match="quotas"):
        sample_balanced_round(policy, roster_states=roster,
                              initial_quotas=(3, 0), draws=(0.1, 0.9, 0.7))


def test_nonfinite_propensity_and_extreme_integer_are_refused():
    policy = snapshot()
    decision = sample_action(policy, state_id="empty", epsilon=1, draw=0.1)
    for propensity in (True, math.nan, math.inf, -0.1):
        with pytest.raises(FinitePolicyError):
            update_complete_round(policy, descriptor(policy, ("s1",)),
                                  (replace(terminal("s1", 1, decision), logged_propensity=propensity),))
    with pytest.raises(FinitePolicyError):
        official_utility(tp=10 ** 1000, fp=0, fn=0, f0=0.8)
    with pytest.raises(FinitePolicyError, match="computed utility"):
        official_utility(tp=1e308, fp=1e308, fn=1e308, f0=0.8)


def test_nested_sources_must_be_immutable_and_last_positive_mass_catches_roundoff():
    policy = snapshot()
    decision = sample_action(policy, state_id="empty", epsilon=1, draw=0.1)
    mutable_sources = [["scores", sha(900)]]
    with pytest.raises(FinitePolicyError, match="immutable"):
        update_complete_round(policy, descriptor(policy, ("s1",)),
                              (replace(terminal("s1", 1, decision), source_hashes=mutable_sources),))
    with pytest.raises(FinitePolicyError, match="immutable"):
        replace(decision, probabilities=[0.5, 0.5])
    many = PolicySnapshot.create(actions=tuple(f"a{i}" for i in range(7)), states=("s",), f0=0.8)
    balanced = sample_balanced_round(many, roster_states=tuple((f"s{i}", "s") for i in range(7)),
                                     initial_quotas=(1,) * 7,
                                     draws=(math.nextafter(1.0, 0.0),) + (0.0,) * 6)
    assert balanced[0].action == "a6"
    assert balanced[0].propensity > 0
