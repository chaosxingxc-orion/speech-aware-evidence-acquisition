"""Unit tests for the pure arithmetic of the ALPHA TRADE SIZING.

Only the data-free logic is exercised here: the registered grid, the branch
decision read off ``kb_policy``'s own blend head, the margin arithmetic on both
sides of 0.5, the locked-cell outcome rule, and the risk / supply-quality /
projection blocks. Everything else in that module reads sealed bytes under
``SPEECHRL_DATA_DIR`` and is covered by the loaders' own fail-closed fidelity
gates plus this module's own published-reach control gate, which must reproduce
160/500, 166/500 and 15/104 before any grid point's number is read.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis import alpha_trade_sizing as ats
from speech_aware_evidence_acquisition.analysis import contrast_fewshot_preanalysis as cf
from speech_aware_evidence_acquisition.analysis import k1_hybrid_ranking_gate as k1


LABEL_TARGETS = {
    "facet:label:intent:a_b": "a_b",
    "facet:label:intent:c_d": "c_d",
    "facet:label:intent:e_f": "e_f",
}


def _trajectory(
    *,
    sample_id: str = "s1",
    direct_label: str | None = "facet:label:intent:a_b",
    fused: dict[str, float] | None = None,
    supply_empty: bool = False,
    gold_target: str = "c_d",
    supplied_targets: tuple[str, ...] = ("c_d",),
    direct_correct: bool = False,
    sealed_correct: bool = False,
    m0_correct: bool | None = False,
    flown_dispatched: bool = False,
) -> ats.Trajectory:
    fused = fused if fused is not None else {"facet:label:intent:c_d": 1.0}
    full = {label_id: fused.get(label_id, 0.0) for label_id in LABEL_TARGETS}
    rank = supplied_targets.index(gold_target) + 1 if gold_target in supplied_targets else None
    return ats.Trajectory(
        sample_id=sample_id,
        direct_label=direct_label,
        supply_empty=supply_empty,
        selected_value_ids=() if supply_empty else ("value:1",),
        admitted_facet_ids=("facet:content:1",),
        supplied_targets=() if supply_empty else supplied_targets,
        gold_target=gold_target,
        gold_supplied=(not supply_empty) and gold_target in supplied_targets,
        gold_target_rank=None if supply_empty else rank,
        fused_label_scores=full,
        direct_correct=direct_correct,
        sealed_correct=sealed_correct,
        m0_correct=m0_correct,
        flown_dispatched=flown_dispatched,
        direct_text="{}",
    )


# ---------------------------------------------------------------------------
# The registered grid
# ---------------------------------------------------------------------------


def test_the_grid_is_the_registered_one_and_carries_the_frozen_control():
    assert ats.ALPHA_GRID == (0.40, 0.45, 0.50, 0.55, 0.60, 0.65)
    assert ats.CONTROL_ALPHA == cf.FROZEN_ALPHA == 0.45
    assert ats.CONTROL_ALPHA in ats.ALPHA_GRID
    # The grid must straddle 0.5, which is the whole point of the sweep.
    assert any(alpha < 0.5 for alpha in ats.ALPHA_GRID)
    assert any(alpha > 0.5 for alpha in ats.ALPHA_GRID)
    assert 0.50 in ats.ALPHA_GRID


def test_the_frozen_cell_is_reported_unchanged():
    assert ats.FROZEN_FUSE.tau == 0.65
    assert ats.FROZEN_FUSE.m == 5
    assert ats.FROZEN_FUSE.c == 2
    assert ats.FROZEN_FUSE.top_l == 3
    assert ats.FROZEN_TOP_K == 5


# ---------------------------------------------------------------------------
# The margin arithmetic
# ---------------------------------------------------------------------------


def test_the_guaranteed_margin_is_plus_ten_points_at_the_locked_alpha():
    block = ats.margin_arithmetic(0.45)

    assert block["guaranteed_margin_1_minus_2alpha"] == pytest.approx(0.10)
    assert block["veto_holds_for_every_supply"] is True
    # A rival would need more fused mass than exists: sum(fused) <= 1 caps the
    # attainable gap at 1.0, and 0.55/0.45 is above it.
    assert block["fused_mass_gap_a_rival_must_exceed"] == pytest.approx(0.55 / 0.45)
    assert block["that_gap_is_attainable"] is False


def test_at_alpha_one_half_the_worst_case_is_an_exact_tie():
    block = ats.margin_arithmetic(0.50)

    assert block["guaranteed_margin_1_minus_2alpha"] == pytest.approx(0.0)
    assert block["veto_holds_for_every_supply"] is False
    assert block["fused_mass_gap_a_rival_must_exceed"] == pytest.approx(1.0)
    assert block["worst_case_is_an_exact_tie"] is True


def test_above_one_half_a_supply_can_outvote_the_direct_label():
    block = ats.margin_arithmetic(0.65)

    assert block["guaranteed_margin_1_minus_2alpha"] < 0.0
    assert block["fused_mass_gap_a_rival_must_exceed"] == pytest.approx(0.35 / 0.65)
    assert block["that_gap_is_attainable"] is True


# ---------------------------------------------------------------------------
# The dispatch branch, through the REAL blend head
# ---------------------------------------------------------------------------


def test_an_empty_supply_retains_at_every_alpha_without_forming_a_blend():
    trajectory = _trajectory(supply_empty=True)

    for alpha in ats.ALPHA_GRID:
        decision = ats.decide(trajectory, alpha=alpha, label_targets=LABEL_TARGETS)
        assert decision.dispatched is False
        assert decision.branch == ats.BRANCH_RETAIN_EMPTY
        assert decision.best_labels == ()


def test_a_recovered_direct_label_vetoes_the_worst_possible_supply_below_one_half():
    """All fused mass on a rival -- the worst case the theorem allows."""

    trajectory = _trajectory(fused={"facet:label:intent:c_d": 1.0})

    for alpha in (0.40, 0.45):
        decision = ats.decide(trajectory, alpha=alpha, label_targets=LABEL_TARGETS)
        assert decision.dispatched is False
        assert decision.branch == ats.BRANCH_RETAIN_VETO
        assert decision.best_labels == ("facet:label:intent:a_b",)


def test_at_exactly_one_half_the_worst_case_supply_ties_and_the_controller_dispatches():
    trajectory = _trajectory(fused={"facet:label:intent:c_d": 1.0})

    decision = ats.decide(trajectory, alpha=0.50, label_targets=LABEL_TARGETS)
    assert decision.dispatched is True
    assert decision.branch == ats.BRANCH_DISPATCH_TIE
    assert decision.best_labels == (
        "facet:label:intent:a_b",
        "facet:label:intent:c_d",
    )


def test_above_one_half_a_concentrated_supply_outvotes_the_direct_label():
    trajectory = _trajectory(fused={"facet:label:intent:c_d": 1.0})

    decision = ats.decide(trajectory, alpha=0.65, label_targets=LABEL_TARGETS)
    assert decision.dispatched is True
    assert decision.branch == ats.BRANCH_DISPATCH_OUTVOTED
    assert decision.best_labels == ("facet:label:intent:c_d",)


def test_a_split_supply_does_not_reach_the_bar_at_alpha_fifty_five():
    """0.55 needs a fused-mass gap above 0.8182; a 0.6/0.4 split gives 0.2."""

    trajectory = _trajectory(
        fused={"facet:label:intent:c_d": 0.6, "facet:label:intent:e_f": 0.4}
    )

    decision = ats.decide(trajectory, alpha=0.55, label_targets=LABEL_TARGETS)
    assert decision.dispatched is False
    assert decision.branch == ats.BRANCH_RETAIN_VETO


def test_a_dead_direct_trajectory_dispatches_at_every_alpha():
    trajectory = _trajectory(direct_label=None)

    for alpha in ats.ALPHA_GRID:
        decision = ats.decide(trajectory, alpha=alpha, label_targets=LABEL_TARGETS)
        assert decision.dispatched is True
        assert decision.branch == ats.BRANCH_DISPATCH_DEAD


def test_the_branches_are_a_partition():
    assert len(set(ats.BRANCHES)) == len(ats.BRANCHES) == 5
    assert set(ats.BRANCH_DESCRIPTIONS) == set(ats.BRANCHES)


# ---------------------------------------------------------------------------
# The locked-cell outcome rule
# ---------------------------------------------------------------------------


def test_a_retained_trajectorys_locked_outcome_is_its_own_direct_decode():
    trajectory = _trajectory(direct_correct=True, sealed_correct=False)

    assert ats.locked_outcome(trajectory, control_dispatched=False) is True
    assert ats.locked_outcome(trajectory, control_dispatched=True) is False


# ---------------------------------------------------------------------------
# The reported blocks
# ---------------------------------------------------------------------------


def test_reach_block_branch_counts_partition_the_population():
    trajectories = {
        "a": _trajectory(sample_id="a", direct_label=None),
        "b": _trajectory(sample_id="b"),
        "c": _trajectory(sample_id="c", supply_empty=True),
    }
    decisions = {
        sid: ats.decide(t, alpha=0.45, label_targets=LABEL_TARGETS)
        for sid, t in trajectories.items()
    }

    block = ats.reach_block(trajectories, decisions)
    assert block["n"] == 3
    assert block["dispatched"] == 1
    assert block["retained"] == 2
    assert block["branch_partition_sums_to_n"] is True
    assert block["branch_counts"][ats.BRANCH_DISPATCH_DEAD] == 1
    assert block["branch_counts"][ats.BRANCH_RETAIN_VETO] == 1
    assert block["branch_counts"][ats.BRANCH_RETAIN_EMPTY] == 1


def test_supply_quality_histogram_partitions_the_set():
    trajectories = {
        "a": _trajectory(sample_id="a", gold_target="c_d", supplied_targets=("c_d", "e_f")),
        "b": _trajectory(sample_id="b", gold_target="e_f", supplied_targets=("c_d", "e_f")),
        "c": _trajectory(sample_id="c", gold_target="zz", supplied_targets=("c_d",)),
    }

    block = ats.supply_quality_block(("a", "b", "c"), trajectories)
    assert block["n"] == 3
    assert block["would_receive_a_gold_bearing_supply"] == 2
    assert block["fused_rank_histogram"]["fused_rank_1"] == 1
    assert block["fused_rank_histogram"]["fused_rank_2_or_3"] == 1
    assert block["fused_rank_histogram"]["gold_absent_from_the_supply"] == 1
    assert block["histogram_sums_to_n"] is True


def test_risk_block_counts_currently_correct_trajectories_and_carries_the_prior():
    trajectories = {
        "a": _trajectory(sample_id="a", direct_correct=True, supplied_targets=("c_d",)),
        "b": _trajectory(sample_id="b", direct_correct=True, gold_target="zz",
                         supplied_targets=("c_d",)),
        "c": _trajectory(sample_id="c", direct_correct=False),
    }

    block = ats.risk_block(
        ("a", "b", "c"),
        trajectories,
        control_dispatched={"a": False, "b": False, "c": False},
        population_n=10,
    )
    assert block["newly_dispatching"] == 3
    assert block["currently_correct_put_at_risk"] == 2
    assert block["of_those_at_risk_the_supply_names_gold_FIRST"] == 1
    assert block["of_those_at_risk_the_supply_omits_gold"] == 1
    assert block["share_of_the_population"] == pytest.approx(0.2)
    assert "RECOVERED 0 OF 3 AND DAMAGED 3 OF 3" in block["adverse_prior"]
    assert "recovered 11 of 11" in block["adverse_prior"]


def test_projection_prices_only_the_changed_trajectories_and_labels_itself():
    trajectories = {
        # unchanged retain -- exact, its own direct decode
        "a": _trajectory(sample_id="a", direct_correct=True),
        # newly dispatched, no sealed evidence decode -- priced at an anchor
        "b": _trajectory(sample_id="b", direct_correct=False, supplied_targets=("c_d",)),
        # newly dispatched but the FLIGHT dispatched it -- MEASURED, not priced
        "c": _trajectory(
            sample_id="c", direct_correct=False, sealed_correct=True, flown_dispatched=True
        ),
    }
    control = {"a": False, "b": False, "c": False}
    variant = {"a": False, "b": True, "c": True}

    block = ats.projection_block(
        trajectories, control_dispatched=control, variant_dispatched=variant
    )
    assert block["exact_outcomes_retained_trajectories"] == 1
    assert block["exact_outcomes_MEASURED_sealed_evidence_decode"] == 1
    assert block["projected_trajectories_priced_at_an_anchor"] == 1
    assert block["locked_cell_correct"] == 1
    # a: 1 (exact), c: 1 (measured), b: the measured top-1 anchor
    assert block["projected_central"] == pytest.approx(2.0 + k1.ANCHOR_TOP1)
    assert "PROJECTION" in block["label"]
    assert "no_expected_accuracy_headline" in block


def test_the_hard_stop_refuses_to_recommend_a_value():
    assert "RECOMMENDS NO VALUE OF ALPHA" in ats.HARD_STOP
    assert "AUTHORIZES NO CHANGE" in ats.HARD_STOP
    assert "d9fef537" in ats.HARD_STOP
    assert "byte_identical_transfer" in ats.TRADE_BEYOND_ACCURACY
    assert "per_carrier_alpha" in ats.TRADE_BEYOND_ACCURACY


def test_the_published_control_reach_gate_names_all_three_populations():
    assert set(ats.PUBLISHED_CONTROL_REACH) == {
        ats.SLURP_UNEXPOSED,
        ats.SLURP_EXPOSED,
        ats.A2T_POPULATION,
    }
    assert ats.PUBLISHED_CONTROL_REACH[ats.SLURP_UNEXPOSED][:2] == (160, 500)
    assert ats.PUBLISHED_CONTROL_REACH[ats.SLURP_EXPOSED][:2] == (166, 500)
    assert ats.PUBLISHED_CONTROL_REACH[ats.A2T_POPULATION][:2] == (15, 104)
