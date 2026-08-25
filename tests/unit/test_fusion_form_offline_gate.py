"""Unit tests for the pure arithmetic of the FUSION-FORM OFFLINE GATE.

Only the data-free logic is exercised here: the three scoring forms, the
blend-head variants, and the five-clause falsifier's own evaluation. Everything
else in that module reads sealed bytes under ``SPEECHRL_DATA_DIR`` and is
covered by the gate's own fail-closed C0 fidelity gates, which reproduce the
flown dispatch decisions, the flown supply and the sealed one-shot read's
published recall@k before a single variant number is read.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import dev100_damage_channel_analysis as dc
from speech_aware_evidence_acquisition.analysis import fusion_form_offline_gate as ffg
from speech_aware_evidence_acquisition.rails import kb_policy as kb


def _recall():
    """Three content facets and two prior-mass facets, all single-dimension.

    This is the shape the pinned TRAIN snapshots actually produce: a content
    facet carries only ``content`` and a prior-mass facet carries only
    ``label`` or ``prior``, so ``agreement`` is the constant 1/dims_total for
    every candidate.
    """

    return {
        "facet:content:1": {"content": 0.90},
        "facet:content:2": {"content": 0.70},
        "facet:content:3": {"content": 0.50},
        "facet:label:intent:a_b": {"label": 1.0},
        "facet:prior:a_b": {"prior": 1.0},
    }


def _state():
    return dc._query_state("s1", "0" * 64)


# ---------------------------------------------------------------------------
# The scoring forms
# ---------------------------------------------------------------------------


def test_cosine_only_keeps_the_cosine_and_deletes_the_other_two_summands():
    scored = ffg.score_cosine_only(_recall(), ffg.FROZEN_WEIGHTS)

    assert scored["facet:content:1"] == pytest.approx(0.5 * 0.90)
    assert scored["facet:content:3"] == pytest.approx(0.5 * 0.50)
    # A prior-mass facet carries no cosine dimension at all, so C1 scores it
    # exactly zero -- it can never compete for the top-m window again.
    assert scored["facet:label:intent:a_b"] == 0.0
    assert scored["facet:prior:a_b"] == 0.0


def test_cosine_only_uses_the_registered_dimension_scales():
    """A prior above its own bound is divided down by the REAL
    ``_dimension_scales``; a cosine, bounded by 1 as a theorem, is untouched."""

    recall = {"facet:content:1": {"content": 0.90}, "facet:prior:x": {"prior": 4.1}}
    scales = kb._dimension_scales(recall)

    assert scales["content"] == 1.0
    assert scales["prior"] == pytest.approx(4.1)
    scored = ffg.score_cosine_only(recall, ffg.FROZEN_WEIGHTS)
    assert scored["facet:content:1"] == pytest.approx(0.5 * 0.90)


def test_rrf_scores_are_one_over_k_plus_the_within_dimension_rank():
    scored = ffg.score_rrf(_recall())

    assert scored["facet:content:1"] == pytest.approx(1.0 / (ffg.RRF_K + 1))
    assert scored["facet:content:2"] == pytest.approx(1.0 / (ffg.RRF_K + 2))
    assert scored["facet:content:3"] == pytest.approx(1.0 / (ffg.RRF_K + 3))
    # Each prior-mass dimension recalls exactly one facet here, so both sit at
    # rank 1 of their own dimension and TIE with the best content facet. That
    # tie is the whole mechanism by which rank fusion evicts content facets
    # from the top-m window.
    assert scored["facet:label:intent:a_b"] == pytest.approx(1.0 / (ffg.RRF_K + 1))
    assert scored["facet:prior:a_b"] == pytest.approx(1.0 / (ffg.RRF_K + 1))


def test_rrf_top_m_window_admits_fewer_content_facets_than_cosine_only():
    state = _state()
    rrf = ffg.rank_for_form(
        ffg.FORM_C3,
        recall_scores=_recall(),
        snapshot_sha256="0" * 64,
        query_state=state,
        weights=ffg.FROZEN_WEIGHTS,
    )
    cosine = ffg.rank_for_form(
        ffg.FORM_C1,
        recall_scores=_recall(),
        snapshot_sha256="0" * 64,
        query_state=state,
        weights=ffg.FROZEN_WEIGHTS,
    )
    top_m = ffg.FROZEN_FUSE.m
    rrf_content = [
        candidate.facet_id
        for candidate in rrf.candidates[:top_m]
        if candidate.facet_id.startswith("facet:content:")
    ]
    cosine_content = [
        candidate.facet_id
        for candidate in cosine.candidates[:top_m]
        if candidate.facet_id.startswith("facet:content:")
    ]
    assert len(cosine_content) == 3
    assert len(rrf_content) <= len(cosine_content)


def test_c0_ranking_is_literally_the_registered_ranker():
    recall = _recall()
    state = _state()
    mine = ffg.rank_for_form(
        ffg.FORM_C0,
        recall_scores=recall,
        snapshot_sha256="0" * 64,
        query_state=state,
        weights=ffg.FROZEN_WEIGHTS,
    )
    registered = kb.rank_wcos_prior_agree_factory(ffg.FROZEN_WEIGHTS)(
        snapshot_sha256="0" * 64, query_state=state, recall_scores=recall
    )
    assert mine.content_hash() == registered.content_hash()


def test_c0_ranking_places_every_admissible_content_facet_above_every_prior_facet():
    """The honest prior the row registered in advance, as executable English:
    ``w_prior * 1.0 = 0.300 < w_cos * tau = 0.325``."""

    ranked = ffg.rank_for_form(
        ffg.FORM_C0,
        recall_scores=_recall(),
        snapshot_sha256="0" * 64,
        query_state=_state(),
        weights=ffg.FROZEN_WEIGHTS,
    )
    order = [candidate.facet_id for candidate in ranked.candidates]
    # cos 0.90 and 0.70 are both above tau = 0.65 and both outrank the priors;
    # cos 0.50 is not admissible and sinks below them, which is exactly why
    # C1 cannot change the admitted set.
    assert order.index("facet:content:1") < order.index("facet:label:intent:a_b")
    assert order.index("facet:content:2") < order.index("facet:prior:a_b")
    assert order.index("facet:content:3") > order.index("facet:prior:a_b")


def test_rank_for_form_refuses_a_form_that_does_not_own_a_ranking():
    with pytest.raises(ffg.GateError):
        ffg.rank_for_form(
            ffg.FORM_C2,
            recall_scores=_recall(),
            snapshot_sha256="0" * 64,
            query_state=_state(),
            weights=ffg.FROZEN_WEIGHTS,
        )


# ---------------------------------------------------------------------------
# The blend head
# ---------------------------------------------------------------------------


def _blend_fixture():
    label_targets = {"L1": "t1", "L2": "t2"}
    values_by_id = {
        "v1": SimpleNamespace(task_target="t1", associated_facet_ids=("f1",)),
        "v2": SimpleNamespace(task_target="t2", associated_facet_ids=("f2",)),
    }
    rank_result = ffg._sorted_rank_result(
        [
            ffg.RankedFacet(facet_id="f1", score=0.60),
            ffg.RankedFacet(facet_id="f2", score=0.20),
        ],
        snapshot_sha256="0" * 64,
        query_state=_state(),
    )
    prior = {"L1": 0.25, "L2": 0.75}
    return label_targets, values_by_id, rank_result, prior


def test_c0_c1_and_c3_use_the_registered_fused_label_scores_unchanged():
    label_targets, values_by_id, rank_result, prior = _blend_fixture()
    reference = kb._fused_label_scores(label_targets, values_by_id, ("v1", "v2"), rank_result)
    for form in (ffg.FORM_C0, ffg.FORM_C1, ffg.FORM_C3):
        assert (
            ffg.fused_label_scores_for_form(
                form,
                label_targets=label_targets,
                values_by_id=values_by_id,
                selected_value_ids=("v1", "v2"),
                rank_result=rank_result,
                prior_masses=prior,
                prior_distribution=ffg._normalize(prior),
            )
            == reference
        )


def test_c2_is_the_raw_score_times_the_prior_normalized_once():
    """The algebraic identity the module relies on to reuse the registered
    function: ``(raw_i p_i) / sum_j(raw_j p_j)``."""

    label_targets, values_by_id, rank_result, prior = _blend_fixture()
    got = ffg.fused_label_scores_for_form(
        ffg.FORM_C2,
        label_targets=label_targets,
        values_by_id=values_by_id,
        selected_value_ids=("v1", "v2"),
        rank_result=rank_result,
        prior_masses=prior,
        prior_distribution=ffg._normalize(prior),
    )
    raw = {"L1": 0.60, "L2": 0.20}
    weighted = {key: raw[key] * prior[key] for key in raw}
    total = sum(weighted.values())
    for key in raw:
        assert got[key] == pytest.approx(weighted[key] / total)
    assert sum(got.values()) == pytest.approx(1.0)


def test_c2b_interpolates_the_two_distributions_at_the_registered_lambda():
    label_targets, values_by_id, rank_result, prior = _blend_fixture()
    retrieval = kb._fused_label_scores(label_targets, values_by_id, ("v1", "v2"), rank_result)
    prior_dist = ffg._normalize(prior)
    for lam in ffg.LAMBDA_GRID:
        got = ffg.fused_label_scores_for_form(
            f"C2B-{lam:.2f}",
            label_targets=label_targets,
            values_by_id=values_by_id,
            selected_value_ids=("v1", "v2"),
            rank_result=rank_result,
            prior_masses=prior,
            prior_distribution=prior_dist,
        )
        for key in label_targets:
            assert got[key] == pytest.approx(
                (1.0 - lam) * retrieval[key] + lam * prior_dist[key]
            )
        assert sum(got.values()) == pytest.approx(1.0)


def test_c2_and_c2b_are_defined_for_every_registered_form_name():
    label_targets, values_by_id, rank_result, prior = _blend_fixture()
    for form in ffg.FORMS:
        ffg.fused_label_scores_for_form(
            form,
            label_targets=label_targets,
            values_by_id=values_by_id,
            selected_value_ids=("v1",),
            rank_result=rank_result,
            prior_masses=prior,
            prior_distribution=ffg._normalize(prior),
        )
    with pytest.raises(ffg.GateError):
        ffg.fused_label_scores_for_form(
            "C9",
            label_targets=label_targets,
            values_by_id=values_by_id,
            selected_value_ids=("v1",),
            rank_result=rank_result,
            prior_masses=prior,
            prior_distribution=ffg._normalize(prior),
        )


# ---------------------------------------------------------------------------
# The falsifier
# ---------------------------------------------------------------------------


def _entry(*, at1, at5, dispatched, non_empty, targets, values, gold_supply, identical):
    recall = {
        "n": 500,
        "recall_at_1_count": at1,
        "recall_at_1_rate": at1 / 500,
        "recall_at_5_count": at5,
        "recall_at_5_rate": at5 / 500,
        "gold_absent_from_candidate_list": 0,
    }
    return {
        "identical_to_control_on_every_measured_quantity": identical,
        "candidate_recall": {
            "content_facet": dict(recall),
            "any_facet": dict(recall),
        },
        "supply_axis": {
            "n": 500,
            "dispatched": dispatched,
            "dispatch_rate": dispatched / 500,
            "dispatched_with_non_empty_supply": non_empty,
            "aggregate_distinct_supplied_task_targets_on_dispatched": targets,
            "aggregate_supplied_values_on_dispatched": values,
            "dispatched_with_gold_bearing_supply": gold_supply,
            "admitted_facets_total": 0,
        },
    }


def _delta(*, gain, loss, changed):
    return {
        "dispatched_trajectories_GAINING_gold_bearing_supply": gain,
        "dispatched_trajectories_LOSING_gold_bearing_supply": loss,
        "decisions_changed_vs_c0": changed,
    }


_CONTROL = _entry(
    at1=300, at5=380, dispatched=160, non_empty=160, targets=400, values=500,
    gold_supply=120, identical=True,
)


def test_an_exact_identity_is_refused_as_no_measurable_gain_not_as_harmful():
    verdict = ffg.falsifier_verdict(
        population_id=ffg.SLURP_UNEXPOSED,
        control=_CONTROL,
        variant=_CONTROL,
        delta=_delta(gain=0, loss=0, changed=0),
        unexposed_decisions_changed=0,
    )
    assert "NO MEASURABLE GAIN" in verdict["verdict"]
    assert "HARMFUL" in verdict["verdict"]
    assert verdict["clauses"]["F1_must_improve"]["holds"] is False


def test_a_form_that_raises_recall_at_5_and_moves_nothing_else_survives_as_written():
    variant = _entry(
        at1=300, at5=395, dispatched=160, non_empty=160, targets=400, values=500,
        gold_supply=120, identical=False,
    )
    verdict = ffg.falsifier_verdict(
        population_id=ffg.SLURP_UNEXPOSED,
        control=_CONTROL,
        variant=variant,
        delta=_delta(gain=0, loss=0, changed=0),
        unexposed_decisions_changed=0,
    )
    assert verdict["all_five_clauses_hold"] is True
    assert verdict["verdict"].startswith("SURVIVES")


def test_the_k1_shape_is_refused_by_the_two_sided_clause_f2():
    """RRF-60's own measured shape: recall@5 up, recall@1 down."""

    variant = _entry(
        at1=280, at5=395, dispatched=160, non_empty=160, targets=400, values=500,
        gold_supply=120, identical=False,
    )
    verdict = ffg.falsifier_verdict(
        population_id=ffg.SLURP_UNEXPOSED,
        control=_CONTROL,
        variant=variant,
        delta=_delta(gain=9, loss=23, changed=40),
        unexposed_decisions_changed=40,
    )
    assert verdict["clauses"]["F1_must_improve"]["holds"] is True
    assert verdict["clauses"]["F2_must_not_degrade_matching"]["holds"] is False
    assert verdict["verdict"].startswith("REFUSED")


def test_an_off_switch_is_refused_by_f4_on_the_dispatch_rate_alone():
    variant = _entry(
        at1=320, at5=400, dispatched=40, non_empty=40, targets=100, values=120,
        gold_supply=130, identical=False,
    )
    verdict = ffg.falsifier_verdict(
        population_id=ffg.SLURP_UNEXPOSED,
        control=_CONTROL,
        variant=variant,
        delta=_delta(gain=15, loss=0, changed=200),
        unexposed_decisions_changed=200,
    )
    assert verdict["clauses"]["F4_must_not_degrade_dispatch_rate"]["holds"] is False
    assert verdict["clauses"]["F3_must_not_degrade_extraction"]["holds"] is False


def test_f5_reports_the_locked_cell_movement_for_every_form():
    variant = _entry(
        at1=300, at5=395, dispatched=161, non_empty=161, targets=402, values=503,
        gold_supply=121, identical=False,
    )
    verdict = ffg.falsifier_verdict(
        population_id=ffg.SLURP_UNEXPOSED,
        control=_CONTROL,
        variant=variant,
        delta=_delta(gain=1, loss=0, changed=3),
        unexposed_decisions_changed=3,
    )
    clause = verdict["clauses"]["F5_must_not_move_the_locked_cell_blindly"]
    assert clause["unexposed_500_decisions_changed"] == 3
    assert clause["reported"] is True
    assert clause["holds"] is False
    assert clause["holds_under_the_reporting_duty_reading"] is True


def test_dispatch_rate_check_is_evaluated_against_every_registered_flown_rate():
    check = ffg.dispatch_rate_check(
        population_id=ffg.SLURP_UNEXPOSED,
        variant_axis={"dispatch_rate": 160 / 500},
    )
    assert set(check["rows"]) == {"flown_v2", "locked_v1_reachable"}
    assert check["rows"]["locked_v1_reachable"]["relative_to_flown"] == pytest.approx(1.0)
    assert check["passed"] is True


def test_the_falsifier_constant_is_the_registered_text_and_names_all_five_clauses():
    for clause in ("(F1)", "(F2)", "(F3)", "(F4)", "(F5)"):
        assert clause in ffg.FALSIFIER
    assert ffg.FALSIFIER.startswith('"A candidate scoring form is REFUSED unless ALL FIVE')
    assert ffg.FALSIFIER.endswith('would have answered."')
    assert "163/500 = 32.60 percent" in ffg.FALSIFIER
    assert "15/104 = 14.42 percent" in ffg.FALSIFIER
