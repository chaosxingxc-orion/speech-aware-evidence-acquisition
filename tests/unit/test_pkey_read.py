"""``analysis.pkey_read``: the P-KEY pinned offline read suite.

Engineering-only, zero live model contact -- every fixture here is a
hand-authored synthetic attempt directory. This module is never pointed at
a real flight attempt directory; that is a separate, one-shot registered
read.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.bootstrap import BootstrapResult
from speech_aware_evidence_acquisition.analysis.pkey_read import (
    BOOTSTRAP_CI_LEVEL,
    BOOTSTRAP_N_REPLICATES,
    BOOTSTRAP_SEED,
    KEY_ONLY_MAX_ABS,
    NEAR_MISS_CENSUS_TOTAL,
    NEAR_MISS_COUNT,
    NEAR_MISS_CROSS_REF_CAVEAT,
    SPEECH_TERM_PRESENT_MIN,
    TEXT_DOMINANT_MAX,
    PKeyOutputRow,
    PKeyReadError,
    ReachabilityStatement,
    build_pkey_report,
    compute_converted_set,
    compute_duplicate_block_delta_f1,
    compute_interaction_bootstrap,
    compute_reachability_statement,
    compute_t0_wer,
    evaluate_interaction,
    evaluate_interaction_ci_gated,
    find_duplicate_reuse_mismatches,
    find_gold_leak_violations,
    find_transcript_reuse_mismatches,
    load_attempt_rows,
    load_gold_sentence_by_sample_id,
    load_pphon_classes,
    main as pkey_read_main,
    perception_gap,
)
from speech_aware_evidence_acquisition.analysis.pslu_read import ArmAggregate, RowAnalysis
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.consumption import ConsumptionTrace
from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (
    AUD_NOSUP_ARM,
    AUD_SUP_ARM,
    T0_ARM,
    TXT_NOSUP_ARM,
    TXT_SUP_ARM,
    assemble_t0_messages,
    assemble_txt_messages,
    build_transcript_record,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, pslu_supply_packet
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SluScore

SLURP_IDS = (101, 900, 901)


# ---------------------------------------------------------------------------
# evaluate_interaction -- the four verdicts, directly (no world needed).
# ---------------------------------------------------------------------------


def _agg(slu_f1_f1: float, *, arm: str = "AUD-NOSUP") -> ArmAggregate:
    zero_score = SluScore(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    return ArmAggregate(
        arm=arm, n_samples=60, aggregate_score=zero_score,
        slu_f1_precision=slu_f1_f1, slu_f1_recall=slu_f1_f1, slu_f1_f1=slu_f1_f1,
        slot_f1_exact_precision=0.0, slot_f1_exact_recall=0.0, slot_f1_exact_f1=0.0,
        slot_f1_exact_tp_sum=0.0, intent_accuracy=0.0, copy_rate=0.0, copy_records=0,
        copy_records_total=0, induced_substitution_count=0,
    )


def _aggregates(aud_nosup: float, aud_sup: float, txt_nosup: float, txt_sup: float) -> dict[str, ArmAggregate]:
    return {
        AUD_NOSUP_ARM: _agg(aud_nosup, arm=AUD_NOSUP_ARM),
        AUD_SUP_ARM: _agg(aud_sup, arm=AUD_SUP_ARM),
        TXT_NOSUP_ARM: _agg(txt_nosup, arm=TXT_NOSUP_ARM),
        TXT_SUP_ARM: _agg(txt_sup, arm=TXT_SUP_ARM),
    }


def test_interaction_thresholds_match_the_registration():
    assert SPEECH_TERM_PRESENT_MIN == 0.06
    assert KEY_ONLY_MAX_ABS == 0.03
    assert TEXT_DOMINANT_MAX == -0.06


def test_evaluate_interaction_speech_term_present():
    # Delta_AUD=+0.50, Delta_TXT=0.00 -> I=+0.50 >= +0.06.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.70, txt_nosup=0.50, txt_sup=0.50))
    assert verdict.interaction == pytest.approx(0.50)
    assert verdict.speech_term_present.verdict == "met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "SPEECH-TERM-PRESENT"


def test_evaluate_interaction_key_only():
    # Delta_AUD=Delta_TXT=+0.30 -> I=0.00, |I|<=0.03.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))
    assert verdict.interaction == pytest.approx(0.0)
    assert verdict.key_only.verdict == "met"
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "KEY-ONLY"


def test_evaluate_interaction_key_only_at_the_boundary():
    # I == +0.03 exactly -> still KEY-ONLY (non-strict <=). Values chosen to
    # land on the boundary WITHOUT floating-point subtraction error (e.g.
    # 0.33 - 0.30 computes to 0.030000000000000027, not 0.03).
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=0.03, txt_nosup=0.0, txt_sup=0.0))
    assert verdict.interaction == pytest.approx(0.03)
    assert verdict.key_only.verdict == "met"
    assert verdict.overall == "KEY-ONLY"


def test_evaluate_interaction_text_dominant():
    # Delta_AUD=0.00, Delta_TXT=+0.50 -> I=-0.50 <= -0.06.
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.40, aud_sup=0.40, txt_nosup=0.10, txt_sup=0.60))
    assert verdict.interaction == pytest.approx(-0.50)
    assert verdict.text_dominant.verdict == "met"
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.overall == "TEXT-DOMINANT"


def test_evaluate_interaction_inconclusive_key():
    # I=+0.045 -- strictly between the KEY-ONLY ceiling (0.03) and the
    # SPEECH-TERM-PRESENT floor (0.06).
    verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=0.045, txt_nosup=0.0, txt_sup=0.0))
    assert verdict.interaction == pytest.approx(0.045)
    assert verdict.speech_term_present.verdict == "not_met"
    assert verdict.key_only.verdict == "not_met"
    assert verdict.text_dominant.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-KEY"


def test_evaluate_interaction_verdicts_are_mutually_exclusive_densely():
    for i in range(-100, 101):
        i_value = i / 100.0
        verdict = evaluate_interaction(_aggregates(aud_nosup=0.0, aud_sup=i_value, txt_nosup=0.0, txt_sup=0.0))
        fired = [
            c.verdict == "met"
            for c in (verdict.speech_term_present, verdict.key_only, verdict.text_dominant)
        ]
        assert sum(fired) <= 1, f"I={i_value} fired more than one clause"


# ---------------------------------------------------------------------------
# evaluate_interaction_ci_gated -- CI-gate fixtures (2026-08-19 amendment
# items 1-2, mission work item 4).
# ---------------------------------------------------------------------------


def _bootstrap_fixture(ci_low: float, ci_high: float, *, point_estimate: float | None = None, sigma_hat: float = 0.01) -> BootstrapResult:
    return BootstrapResult(
        point_estimate=point_estimate if point_estimate is not None else (ci_low + ci_high) / 2.0,
        replicates=(), sigma_hat=sigma_hat, ci_low=ci_low, ci_high=ci_high,
        ci_level=0.90, n_replicates=100, seed=20260807,
    )


def _reachability_fixture(*, reachable: bool, max_attainable: float = 0.5) -> ReachabilityStatement:
    return ReachabilityStatement(
        aud_nosup_failure_count=10, n_samples=60, near_miss_count=NEAR_MISS_COUNT,
        near_miss_census_total=NEAR_MISS_CENSUS_TOTAL, near_miss_rate=NEAR_MISS_COUNT / NEAR_MISS_CENSUS_TOTAL,
        eligible_near_miss_samples=min(NEAR_MISS_COUNT, 10), max_attainable_interaction=max_attainable,
        speech_term_present_reachable=reachable, detail="test fixture",
    )


def test_ci_gated_ci_entirely_inside_band_and_reachable_is_key_only():
    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))  # I=0.0
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(-0.02, 0.02), _reachability_fixture(reachable=True))
    assert result.key_only.verdict == "met"
    assert result.overall == "KEY-ONLY"


def test_ci_gated_point_inside_band_but_ci_crossing_is_inconclusive_key():
    """Amendment item 1, quoted verbatim: 'a point estimate inside the band
    with a CI crossing it is INCONCLUSIVE-KEY.'"""

    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))  # I=0.0
    assert point.key_only.verdict == "met"  # point-only reading WOULD have fired
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(-0.05, 0.05), _reachability_fixture(reachable=True))
    assert result.key_only.verdict == "not_met"
    assert result.overall == "INCONCLUSIVE-KEY"


def test_ci_gated_ci_boundary_entirely_inside_is_key_only():
    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))  # I=0.0
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(-0.03, 0.03), _reachability_fixture(reachable=True))
    assert result.key_only.verdict == "met"
    assert result.overall == "KEY-ONLY"


def test_ci_gated_ci_barely_crossing_the_boundary_is_inconclusive_key():
    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))  # I=0.0
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(-0.03, 0.0301), _reachability_fixture(reachable=True))
    assert result.key_only.verdict == "not_met"
    assert result.overall == "INCONCLUSIVE-KEY"


def test_ci_gated_speech_term_present_is_point_based_regardless_of_ci():
    """Amendment: SPEECH-TERM-PRESENT is 'unchanged on the point estimate' --
    fires from point.speech_term_present alone, checked BEFORE key_only, so
    a wide CI (even one that would also satisfy the KEY-ONLY band, which
    this fixture's own CI does not) never overrides it."""

    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.70, txt_nosup=0.50, txt_sup=0.50))  # I=0.50
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(0.40, 0.60), _reachability_fixture(reachable=True))
    assert result.overall == "SPEECH-TERM-PRESENT"


def test_ci_gated_text_dominant_is_point_based_regardless_of_ci():
    point = evaluate_interaction(_aggregates(aud_nosup=0.40, aud_sup=0.40, txt_nosup=0.10, txt_sup=0.60))  # I=-0.50
    result = evaluate_interaction_ci_gated(point, _bootstrap_fixture(-0.60, -0.40), _reachability_fixture(reachable=True))
    assert result.overall == "TEXT-DOMINANT"


def test_ci_gated_unreachable_downgrades_an_otherwise_firing_key_only_to_inconclusive():
    """Amendment item 2, quoted verbatim: 'If SPEECH-TERM-PRESENT is
    unreachable, KEY-ONLY may not be reported as an affirmative negative --
    only as INCONCLUSIVE with the reachability bound.'"""

    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))  # I=0.0
    result = evaluate_interaction_ci_gated(
        point, _bootstrap_fixture(-0.02, 0.02), _reachability_fixture(reachable=False, max_attainable=0.01)
    )
    assert result.key_only.verdict == "not_met"
    assert result.overall == "INCONCLUSIVE-KEY"
    assert "UNREACHABLE" in result.key_only.detail
    assert "0.01" in result.key_only.detail


def test_ci_gated_carries_the_point_and_bootstrap_and_reachability_through_unchanged():
    point = evaluate_interaction(_aggregates(aud_nosup=0.20, aud_sup=0.50, txt_nosup=0.10, txt_sup=0.40))
    bootstrap = _bootstrap_fixture(-0.02, 0.02)
    reachability = _reachability_fixture(reachable=True)
    result = evaluate_interaction_ci_gated(point, bootstrap, reachability)
    assert result.point is point
    assert result.bootstrap is bootstrap
    assert result.reachability is reachability
    # point's OWN speech_term_present/text_dominant clauses are read through unchanged.
    assert result.point.speech_term_present.verdict == "not_met"
    assert result.point.text_dominant.verdict == "not_met"


# ---------------------------------------------------------------------------
# compute_interaction_bootstrap -- determinism + a hand-checkable tiny case.
# ---------------------------------------------------------------------------


def _score(word_tp: float, word_fp: float, word_fn: float) -> SluScore:
    return SluScore(0, 0, 0, 0, 0, 0, word_tp, word_fp, word_fn, 0, 0, 0)


def _analysis_with_score(sample_id: str, score: SluScore) -> RowAnalysis:
    row = _t0_row(sample_id, "{}")
    return RowAnalysis(
        row=row, predicted_scenario=None, predicted_action=None, predicted_entities=(), parsed=True,
        recomputed_score=score, recheck_mismatches=(), roster_reconciliation=None, induced_substitutions=0,
    )


def test_compute_interaction_bootstrap_is_deterministic_for_the_same_seed():
    aud_nosup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(1, 0, 0))]
    aud_sup = [_analysis_with_score("s1", _score(1, 0, 0)), _analysis_with_score("s2", _score(1, 0, 0))]
    txt_nosup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(1, 0, 0))]
    txt_sup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(1, 0, 0))]

    result_a = compute_interaction_bootstrap(
        aud_nosup_analyses=aud_nosup, aud_sup_analyses=aud_sup,
        txt_nosup_analyses=txt_nosup, txt_sup_analyses=txt_sup, n_replicates=500, seed=20260807,
    )
    result_b = compute_interaction_bootstrap(
        aud_nosup_analyses=aud_nosup, aud_sup_analyses=aud_sup,
        txt_nosup_analyses=txt_nosup, txt_sup_analyses=txt_sup, n_replicates=500, seed=20260807,
    )
    assert result_a.replicates == result_b.replicates
    assert result_a.ci == result_b.ci
    assert result_a.sigma_hat == result_b.sigma_hat


def test_compute_interaction_bootstrap_defaults_match_the_registered_discipline():
    assert BOOTSTRAP_N_REPLICATES == 10_000
    assert BOOTSTRAP_SEED == 20260807
    assert BOOTSTRAP_CI_LEVEL == 0.90


def test_compute_interaction_bootstrap_hand_checkable_two_sample_case():
    """Hand-computable by construction: AUD-SUP repairs s1 (word F1 0 -> 1)
    and leaves s2 unchanged; TXT-SUP == TXT-NOSUP exactly (zero TXT
    improvement, same ingredients as AUD-NOSUP) -- so Delta_TXT is EXACTLY
    0.0 for every possible resample, and I == Delta_AUD deterministically.
    With only 2 unique ids, every resample is one of (s1,s1)/(s2,s2)/mixed,
    each with an exactly hand-computable pooled-F1 delta."""

    aud_nosup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(2, 0, 0))]
    aud_sup = [_analysis_with_score("s1", _score(1, 0, 0)), _analysis_with_score("s2", _score(2, 0, 0))]
    txt_nosup = aud_nosup
    txt_sup = aud_nosup  # zero TXT improvement, by construction

    result = compute_interaction_bootstrap(
        aud_nosup_analyses=aud_nosup, aud_sup_analyses=aud_sup,
        txt_nosup_analyses=txt_nosup, txt_sup_analyses=txt_sup, n_replicates=2000, seed=20260807,
    )

    # Point estimate: original (s1, s2) exactly once each.
    # aud_nosup pooled: tp=0+2=2, fp=1, fn=1 -> F1 = 2*2/(2*2+1+1) = 4/6 = 0.66667
    # aud_sup pooled:   tp=1+2=3, fp=0, fn=0 -> F1 = 1.0
    # delta_aud = 1.0 - 0.66667 = 0.33333; delta_txt = 0.0 (identical arms) -> I = 0.33333
    assert result.point_estimate == pytest.approx(1.0 / 3.0, abs=1e-4)
    # Every replicate must be one of exactly three hand-computed values:
    #   (s1,s1): aud_nosup F1=0, aud_sup F1=1 -> I=1.0
    #   (s2,s2): aud_nosup F1=1, aud_sup F1=1 -> I=0.0
    #   mixed:   I=0.33333 (same arithmetic as the point estimate)
    rounded = {round(v, 4) for v in result.replicates}
    assert rounded <= {0.0, round(1.0 / 3.0, 4), 1.0}
    assert rounded == {0.0, round(1.0 / 3.0, 4), 1.0}  # n_replicates=2000 sees all three
    assert result.sigma_hat > 0.0
    assert result.ci_level == 0.90


def test_compute_interaction_bootstrap_raises_on_zero_common_sample_ids():
    aud_nosup = [_analysis_with_score("s1", _score(0, 1, 1))]
    aud_sup = [_analysis_with_score("s2", _score(1, 0, 0))]  # disjoint from aud_nosup
    with pytest.raises(PKeyReadError, match="no sample id is present in all four"):
        compute_interaction_bootstrap(
            aud_nosup_analyses=aud_nosup, aud_sup_analyses=aud_sup,
            txt_nosup_analyses=aud_nosup, txt_sup_analyses=aud_sup, n_replicates=10,
        )


# ---------------------------------------------------------------------------
# compute_reachability_statement -- reachability-statement arithmetic
# (mission work item 4).
# ---------------------------------------------------------------------------


def test_compute_reachability_statement_arithmetic_below_the_floor():
    analyses = [
        _analysis("s1", fully_correct=False),
        _analysis("s2", fully_correct=False),
        _analysis("s3", fully_correct=True),
    ]
    result = compute_reachability_statement(analyses, n_samples=60)
    assert result.aud_nosup_failure_count == 2
    assert result.n_samples == 60
    assert result.near_miss_count == NEAR_MISS_COUNT == 4
    assert result.near_miss_census_total == NEAR_MISS_CENSUS_TOTAL == 85
    assert result.near_miss_rate == pytest.approx(4 / 85)
    assert result.eligible_near_miss_samples == min(4, 2) == 2
    assert result.max_attainable_interaction == pytest.approx(2 / 60)
    assert result.speech_term_present_reachable is False  # 2/60 =~ 0.0333 < 0.06
    assert "UNREACHABLE" in result.detail
    assert "4/85" in result.detail


def test_compute_reachability_statement_reachable_when_failures_reach_the_cap():
    analyses = [_analysis(f"s{i}", fully_correct=False) for i in range(10)]
    result = compute_reachability_statement(analyses, n_samples=60)
    assert result.aud_nosup_failure_count == 10
    assert result.eligible_near_miss_samples == 4  # capped at NEAR_MISS_COUNT, not 10
    assert result.max_attainable_interaction == pytest.approx(4 / 60)
    assert result.speech_term_present_reachable is True  # 4/60 =~ 0.0667 >= 0.06
    assert "REACHABLE" in result.detail


def test_compute_reachability_statement_zero_failures_is_unreachable():
    analyses = [_analysis("s1", fully_correct=True), _analysis("s2", fully_correct=True)]
    result = compute_reachability_statement(analyses, n_samples=60)
    assert result.aud_nosup_failure_count == 0
    assert result.eligible_near_miss_samples == 0
    assert result.max_attainable_interaction == pytest.approx(0.0)
    assert result.speech_term_present_reachable is False


def test_compute_reachability_statement_defaults_n_samples_to_len_analyses():
    analyses = [_analysis("s1", fully_correct=False)]
    result = compute_reachability_statement(analyses)
    assert result.n_samples == 1


def test_near_miss_cross_ref_caveat_cites_the_n_le_4_bound():
    assert "n<=4" in NEAR_MISS_CROSS_REF_CAVEAT
    assert "mechanism claim" in NEAR_MISS_CROSS_REF_CAVEAT


# ---------------------------------------------------------------------------
# perception_gap.
# ---------------------------------------------------------------------------


def test_perception_gap_is_txt_nosup_minus_aud_nosup():
    aggregates = _aggregates(aud_nosup=0.30, aud_sup=0.90, txt_nosup=0.55, txt_sup=0.60)
    assert perception_gap(aggregates) == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# compute_t0_wer -- direct, no world.
# ---------------------------------------------------------------------------


def _t0_row(sample_id: str, response_text: str) -> PKeyOutputRow:
    return PKeyOutputRow(
        arm=T0_ARM, sample_id=sample_id, silence_swapped=False, transcript_sha256_used=None,
        messages=(), response_text=response_text, metrics={}, consumption={},
    )


def test_compute_t0_wer_exact_match_is_zero_and_a_divergent_one_is_positive():
    rows = [_t0_row("s1", "check my email"), _t0_row("s2", "turn on the kitchen light")]
    gold = {"s1": "check my email", "s2": "turn on the kitchen lights"}
    result = compute_t0_wer(rows, gold)
    assert result.per_sample["s1"] == pytest.approx(0.0)
    assert result.per_sample["s2"] > 0.0
    assert result.macro_wer == pytest.approx((result.per_sample["s1"] + result.per_sample["s2"]) / 2.0)


def test_compute_t0_wer_skips_samples_with_no_gold_and_handles_empty_input():
    assert compute_t0_wer([], {}).macro_wer == 0.0
    rows = [_t0_row("no-gold", "x")]
    result = compute_t0_wer(rows, {})
    assert result.per_sample == {}
    assert result.macro_wer == 0.0


# ---------------------------------------------------------------------------
# load_pphon_classes -- soft, read-only, tolerate-absence.
# ---------------------------------------------------------------------------


def test_load_pphon_classes_none_path_is_empty():
    assert load_pphon_classes(None) == {}


def test_load_pphon_classes_missing_file_is_empty(tmp_path):
    assert load_pphon_classes(tmp_path / "does-not-exist.json") == {}


def test_load_pphon_classes_malformed_json_is_empty(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_pphon_classes(path) == {}


def test_load_pphon_classes_samples_shape(tmp_path):
    path = tmp_path / "pphon-verdict.json"
    path.write_text(json.dumps({"samples": {"sid-1": {"class": "NEAR-MISS"}, "sid-2": "FAR-MISS"}}), encoding="utf-8")
    assert load_pphon_classes(path) == {"sid-1": "NEAR-MISS", "sid-2": "FAR-MISS"}


def test_load_pphon_classes_flat_shape(tmp_path):
    path = tmp_path / "pphon-verdict-flat.json"
    path.write_text(json.dumps({"sid-1": "NEAR-MISS"}), encoding="utf-8")
    assert load_pphon_classes(path) == {"sid-1": "NEAR-MISS"}


# ---------------------------------------------------------------------------
# compute_converted_set -- direct, using RowAnalysis-shaped fixtures.
# ---------------------------------------------------------------------------


def _analysis(sample_id: str, *, fully_correct: bool):
    from speech_aware_evidence_acquisition.analysis.pslu_read import RowAnalysis

    row = _t0_row(sample_id, "{}")
    score = (
        SluScore(1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if fully_correct
        else SluScore(0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0)
    )
    return RowAnalysis(
        row=row, predicted_scenario=None, predicted_action=None, predicted_entities=(),
        parsed=True, recomputed_score=score, recheck_mismatches=(), roster_reconciliation=None,
        induced_substitutions=0,
    )


def test_compute_converted_set_aud_only_perception_repair_set():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=False)],
    )
    assert result.aud_converted == ("s1",)
    assert result.txt_converted == ()
    assert result.aud_only == ("s1",)
    assert result.pphon_class_by_sample == {}


def test_compute_converted_set_soft_pphon_cross_reference():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=False)],
        pphon_classes={"s1": "NEAR-MISS", "unrelated": "FAR-MISS"},
    )
    assert result.aud_only == ("s1",)
    assert result.pphon_class_by_sample == {"s1": "NEAR-MISS"}


def test_compute_converted_set_both_converted_is_excluded_from_aud_only():
    result = compute_converted_set(
        aud_nosup_analyses=[_analysis("s1", fully_correct=False)],
        aud_sup_analyses=[_analysis("s1", fully_correct=True)],
        txt_nosup_analyses=[_analysis("s1", fully_correct=False)],
        txt_sup_analyses=[_analysis("s1", fully_correct=True)],
    )
    assert result.aud_converted == ("s1",)
    assert result.txt_converted == ("s1",)
    assert result.aud_only == ()


# ---------------------------------------------------------------------------
# Synthetic SLURP world (mirrors tests/unit/test_pslu_read.py's own
# PsluWorld): 101 (scenario "iot", one gold entity house_place=kitchen)
# plus two neutral no-entity samples (900/901, scenario "email").
# ---------------------------------------------------------------------------


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.2) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": s, "id": i, "lemma": s, "pos": "NN"} for i, s in enumerate(surfaces)]


DEVEL_RECORDS = [
    {
        "slurp_id": 101,
        "sentence": "turn on the kitchen lights",
        "sentence_annotation": "turn on the [house_place : kitchen] lights",
        "intent": "iot_hue_lighton",
        "scenario": "iot",
        "action": "hue_lighton",
        "tokens": _tokens("turn", "on", "the", "kitchen", "lights"),
        "entities": [{"span": [3], "type": "house_place"}],
        "recordings": [{"file": "audio-101.flac", "wer": 0.0, "ent_wer": 0.0, "status": "correct"}],
    },
    {
        "slurp_id": 900,
        "sentence": "check my email",
        "sentence_annotation": "check my email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("check", "my", "email"),
        "entities": [],
        "recordings": [{"file": "audio-900.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
    {
        "slurp_id": 901,
        "sentence": "any new email",
        "sentence_annotation": "any new email",
        "intent": "email_query",
        "scenario": "email",
        "action": "query",
        "tokens": _tokens("any", "new", "email"),
        "entities": [],
        "recordings": [{"file": "audio-901.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    },
]

ROSTER_DOC = {
    "probe": "P-SLU",
    "legality_tier": "legal",
    "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
    "arms": {
        "A1_scenario_roster": {"rosters": {"iot": [["house_place", "kitchen"]], "email": [["email_folder", "inbox"]]}},
        "A2_global_type_vocabulary": {"types": ["house_place", "email_folder"]},
        "A3_full_ontology_dose_capped": {"roster": [["house_place", "kitchen"], ["email_folder", "inbox"]]},
        "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
    },
}


class PKeyWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.lock_path = tmp_path / "lock.json"
        audio_root = self.data_root / "datasets" / "slurp"
        metadata_dir = audio_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "devel.jsonl").write_text(
            "\n".join(json.dumps(r) for r in DEVEL_RECORDS) + "\n", encoding="utf-8"
        )
        real_dir = audio_root / "slurp_real"
        for record in DEVEL_RECORDS:
            for recording in record["recordings"]:
                _write_flac(real_dir / recording["file"])
        lock_doc = {
            "datasets": [
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0",
                    "annotations": {"governed_copy": "datasets/slurp/metadata"},
                }
            ]
        }
        self.lock_path.write_text(json.dumps(lock_doc), encoding="utf-8")
        self.lock = load_lock(self.lock_path)
        self.adapter = SlurpAdapter(self.lock, self.data_root)
        samples = {s.sample_id: s for s in self.adapter.load_split("devel")}
        self.sid = {slurp_id: self._find(samples, slurp_id) for slurp_id in SLURP_IDS}

        self.roster_table_path = tmp_path / "rosters.json"
        self.roster_table_path.write_text(json.dumps(ROSTER_DOC), encoding="utf-8")
        self.rosters = load_pslu_rosters(self.roster_table_path)
        self.a3_supply = pslu_supply_packet("A3", scenario=None, rosters=self.rosters)

        self.sample_manifest_path = tmp_path / "manifest.json"
        manifest_doc = {
            "probe": "P-SLU",
            "seed": 20260807,
            "split_identity_hash": "a" * 64,
            "items": [{"sample_id": self.sid[slurp_id].sample_id} for slurp_id in SLURP_IDS],
        }
        self.sample_manifest_path.write_text(json.dumps(manifest_doc), encoding="utf-8")

    @staticmethod
    def _find(samples: dict, slurp_id: int):
        needle = f":{slurp_id:06d}:"
        for sample_id, sample in samples.items():
            if needle in sample_id:
                return sample
        raise KeyError(slurp_id)


@pytest.fixture()
def pkey_world(tmp_path):
    return PKeyWorld(tmp_path)


def _resp(scenario: str, action: str, entities: list[tuple[str, str]]) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": [{"type": t, "filler": f} for t, f in entities]}
    )


NEUTRAL = _resp("email", "query", [])
IOT_WRONG = _resp("iot", "hue_lighton", [])
IOT_RIGHT = _resp("iot", "hue_lighton", [("house_place", "kitchen")])

T0_RESPONSES = {101: "turn on the kitchen light", 900: "check my email", 901: "any new email"}


def _row(world: PKeyWorld, sample, arm: str, response_text: str, *, transcript_registry, silence_swapped=False) -> dict:
    if arm == T0_ARM:
        messages = list(assemble_t0_messages(sample))
        metrics: dict = {}
        consumption = world.adapter.extract_consumption(sample, None, response_text).as_json()
        transcript_sha256_used = None
    elif arm in (AUD_NOSUP_ARM, AUD_SUP_ARM):
        supply = None if arm == AUD_NOSUP_ARM else world.a3_supply
        messages = list(world.adapter.assemble_prompt(sample, supply))
        if silence_swapped:
            relpath = f"derived/silence/{sample.sample_id.replace(':', '_')}.flac"
            user_message = messages[1]
            new_content = []
            for part in user_message["content"]:
                if isinstance(part, dict) and part.get("type") == "input_audio":
                    new_content.append({**part, "media_relpath": relpath})
                else:
                    new_content.append(dict(part))
            messages[1] = {"role": "user", "content": new_content}
        metrics = dict(world.adapter.score(sample, response_text))
        consumption = world.adapter.extract_consumption(sample, supply, response_text).as_json()
        transcript_sha256_used = None
    else:  # TXT_NOSUP_ARM / TXT_SUP_ARM
        supply = None if arm == TXT_NOSUP_ARM else world.a3_supply
        messages = list(assemble_txt_messages(sample, supply, transcript_registry))
        metrics = dict(world.adapter.score(sample, response_text))
        consumption = world.adapter.extract_consumption(sample, supply, response_text).as_json()
        transcript_sha256_used = transcript_registry[sample.sample_id].sha256
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "silence_swapped": silence_swapped,
        "transcript_sha256_used": transcript_sha256_used,
        "messages": messages,
        "response_text": response_text,
        "metrics": metrics,
        "consumption": consumption,
    }


def _build_rows(
    world: PKeyWorld,
    *,
    aud_nosup: dict[int, str],
    aud_sup: dict[int, str],
    txt_nosup: dict[int, str],
    txt_sup: dict[int, str],
    silence_sample_ids: tuple[int, ...] = SLURP_IDS,
    silence_responses: dict[int, str] | None = None,
) -> list[dict]:
    transcript_registry = {
        world.sid[slurp_id].sample_id: build_transcript_record(world.sid[slurp_id].sample_id, T0_RESPONSES[slurp_id])
        for slurp_id in SLURP_IDS
    }
    rows: list[dict] = []
    for slurp_id in SLURP_IDS:
        sample = world.sid[slurp_id]
        rows.append(_row(world, sample, T0_ARM, T0_RESPONSES[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], AUD_NOSUP_ARM, aud_nosup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], AUD_SUP_ARM, aud_sup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], TXT_NOSUP_ARM, txt_nosup[slurp_id], transcript_registry=transcript_registry))
    for slurp_id in SLURP_IDS:
        rows.append(_row(world, world.sid[slurp_id], TXT_SUP_ARM, txt_sup[slurp_id], transcript_registry=transcript_registry))
    silence_responses = silence_responses or {slurp_id: aud_sup[slurp_id] for slurp_id in silence_sample_ids}
    for slurp_id in silence_sample_ids:
        rows.append(
            _row(
                world, world.sid[slurp_id], AUD_SUP_ARM, silence_responses[slurp_id],
                transcript_registry=transcript_registry, silence_swapped=True,
            )
        )
    return rows


def _write_attempt_dir(path: Path, rows: list[dict], *, status="COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _build_report(world: PKeyWorld, tmp_path: Path, rows: list[dict], **kwargs):
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    return build_pkey_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=world.sample_manifest_path, roster_table_path=world.roster_table_path,
        **kwargs,
    )


def _clean_rows(world: PKeyWorld) -> list[dict]:
    return _build_rows(
        world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
    )


# ---------------------------------------------------------------------------
# load_gold_sentence_by_sample_id.
# ---------------------------------------------------------------------------


def test_load_gold_sentence_by_sample_id(pkey_world):
    sample_ids = [pkey_world.sid[slurp_id].sample_id for slurp_id in SLURP_IDS]
    sentences = load_gold_sentence_by_sample_id(pkey_world.lock, pkey_world.data_root, sample_ids)
    assert sentences[pkey_world.sid[101].sample_id] == "turn on the kitchen lights"
    assert sentences[pkey_world.sid[900].sample_id] == "check my email"


# ---------------------------------------------------------------------------
# build_pkey_report -- happy path.
# ---------------------------------------------------------------------------


def test_happy_path_key_only_and_zero_defects(pkey_world, tmp_path):
    # Deliberately NOT _clean_rows()'s own default silence_responses (which
    # equal the real AUD-SUP responses on every sample -- unanimous
    # unchanged, see test_silence_swap_unanimous_unchanged_voids_the_read):
    # sample 101 flips under silence here, so the silence-swap VOID clause
    # stays not_met and this fixture can assert a clean, non-VOID read.
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        silence_responses={101: NEUTRAL, 900: NEUTRAL, 901: NEUTRAL},
    )
    report = _build_report(pkey_world, tmp_path, rows)

    assert report.recheck_mismatches == ()
    assert report.harness_defect_reasons == ()
    assert report.gold_leak_violations == ()
    assert report.transcript_mismatches == ()
    assert report.void_verdict.voided is False

    assert report.aggregates[AUD_NOSUP_ARM].slu_f1_f1 == pytest.approx(0.0)
    assert report.aggregates[AUD_SUP_ARM].slu_f1_f1 == pytest.approx(1.0)
    assert report.aggregates[TXT_NOSUP_ARM].slu_f1_f1 == pytest.approx(0.0)
    assert report.aggregates[TXT_SUP_ARM].slu_f1_f1 == pytest.approx(1.0)
    assert report.interaction.delta_aud == pytest.approx(1.0)
    assert report.interaction.delta_txt == pytest.approx(1.0)
    assert report.interaction.interaction == pytest.approx(0.0)
    assert report.interaction.overall == "KEY-ONLY"
    assert report.overall == "KEY-ONLY"

    assert report.perception_gap == pytest.approx(0.0)
    assert report.t0_wer.per_sample[pkey_world.sid[900].sample_id] == pytest.approx(0.0)
    assert report.t0_wer.per_sample[pkey_world.sid[101].sample_id] > 0.0

    # Both AUD-SUP and TXT-SUP convert sample 101 -> aud_only is empty.
    assert report.converted_set.aud_only == ()


# ---------------------------------------------------------------------------
# converted-set difference (perception-repair set) over the full report.
# ---------------------------------------------------------------------------


def test_converted_set_difference_via_full_report(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},  # TXT never converts 101
    )
    pphon_path = tmp_path / "pphon-verdict.json"
    pphon_path.write_text(
        json.dumps({"samples": {pkey_world.sid[101].sample_id: {"class": "NEAR-MISS"}}}), encoding="utf-8"
    )
    report = _build_report(pkey_world, tmp_path, rows, pphon_verdict_path=pphon_path)

    assert report.converted_set.aud_converted == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.txt_converted == ()
    assert report.converted_set.aud_only == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.pphon_class_by_sample == {pkey_world.sid[101].sample_id: "NEAR-MISS"}


def test_converted_set_difference_without_pphon_output_tolerates_absence(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
    )
    report = _build_report(pkey_world, tmp_path, rows)  # no pphon_verdict_path
    assert report.converted_set.aud_only == (pkey_world.sid[101].sample_id,)
    assert report.converted_set.pphon_class_by_sample == {}


# ---------------------------------------------------------------------------
# Legality: gold text must never appear inside any prompt.
# ---------------------------------------------------------------------------


def test_find_gold_leak_violations_clean_fixture_has_none(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)
    parsed_rows = load_attempt_rows(attempt_dir)
    gold = load_gold_sentence_by_sample_id(
        pkey_world.lock, pkey_world.data_root, [pkey_world.sid[i].sample_id for i in SLURP_IDS]
    )
    assert find_gold_leak_violations(parsed_rows, gold) == ()


def test_gold_leak_fixture_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    leaked_sample_id = pkey_world.sid[101].sample_id
    for row in rows:
        if row["arm"] == AUD_SUP_ARM and row["sample_id"] == leaked_sample_id and not row["silence_swapped"]:
            # Appended AFTER the roster+audio content parts, to isolate the
            # gold-leak clause from the (unrelated) roster-shape harness-
            # defect check -- content_text_parts still finds texts[0] ==
            # the real roster block, so only the leak clause fires here.
            row["messages"][1]["content"].append({"type": "text", "text": "turn on the kitchen lights"})
    report = _build_report(pkey_world, tmp_path, rows)

    assert len(report.gold_leak_violations) >= 1
    assert any(v.sample_id == leaked_sample_id for v in report.gold_leak_violations)
    assert report.void_verdict.voided is True
    assert report.overall == "VOID"
    leak_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "gold sentence text found inside a prompt")
    assert leak_clause.verdict == "met"


# ---------------------------------------------------------------------------
# Transcript-reuse byte-identity fixture.
# ---------------------------------------------------------------------------


def test_transcript_mismatch_fixture_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    corrupted_sample_id = pkey_world.sid[101].sample_id
    for row in rows:
        if row["arm"] == TXT_NOSUP_ARM and row["sample_id"] == corrupted_sample_id:
            row["messages"][1]["content"][-1]["text"] = "The user said: a completely different transcript"
    report = _build_report(pkey_world, tmp_path, rows)

    assert len(report.transcript_mismatches) >= 1
    assert any(m.sample_id == corrupted_sample_id for m in report.transcript_mismatches)
    assert report.void_verdict.voided is True
    assert report.overall == "VOID"
    transcript_clause = next(
        c for c in report.void_verdict.clauses
        if c.clause_text == "a TXT-* row's transcript disagrees with its own T0 output (byte-identity)"
    )
    assert transcript_clause.verdict == "met"


def test_find_transcript_reuse_mismatches_direct():
    t0_rows = [_t0_row("s1", "hello world")]
    good_row = PKeyOutputRow(
        arm=TXT_NOSUP_ARM, sample_id="s1", silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": "The user said: hello world"}]}),
        response_text="{}", metrics={}, consumption={},
    )
    bad_row = PKeyOutputRow(
        arm=TXT_SUP_ARM, sample_id="s1", silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": "The user said: goodbye world"}]}),
        response_text="{}", metrics={}, consumption={},
    )
    mismatches = find_transcript_reuse_mismatches(t0_rows, [good_row, bad_row])
    assert len(mismatches) == 1
    assert mismatches[0].arm == TXT_SUP_ARM


# ---------------------------------------------------------------------------
# Duplicate-block byte-identity (2026-08-19 amendment item 4, mission work
# item 4): "fixture where a resend differs -> refuse."
# ---------------------------------------------------------------------------


def _txt_nosup_row(sample_id: str, text: str) -> PKeyOutputRow:
    return PKeyOutputRow(
        arm=TXT_NOSUP_ARM, sample_id=sample_id, silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": text}]}),
        response_text="{}", metrics={}, consumption={},
    )


def _dup_row_direct(sample_id: str, text: str) -> PKeyOutputRow:
    return PKeyOutputRow(
        arm=TXT_NOSUP_ARM, sample_id=sample_id, silence_swapped=False, transcript_sha256_used=None,
        messages=({"role": "system", "content": "x"}, {"role": "user", "content": [{"type": "text", "text": text}]}),
        response_text="{}", metrics={}, consumption={}, txt_duplicate=True,
    )


def test_find_duplicate_reuse_mismatches_accepts_a_matching_resend():
    originals = [_txt_nosup_row("s1", "The user said: hello")]
    good = _dup_row_direct("s1", "The user said: hello")
    assert find_duplicate_reuse_mismatches(originals, [good]) == ()


def test_find_duplicate_reuse_mismatches_refuses_a_resend_that_differs():
    originals = [_txt_nosup_row("s1", "The user said: hello")]
    diverged = _dup_row_direct("s1", "The user said: something else entirely")
    mismatches = find_duplicate_reuse_mismatches(originals, [diverged])
    assert len(mismatches) == 1
    assert mismatches[0].sample_id == "s1"


def test_find_duplicate_reuse_mismatches_reports_a_missing_original():
    originals = [_txt_nosup_row("s1", "The user said: hello")]
    orphan = _dup_row_direct("s2", "The user said: goodbye")  # no s2 original at all
    mismatches = find_duplicate_reuse_mismatches(originals, [orphan])
    assert len(mismatches) == 1
    assert mismatches[0].sample_id == "s2"
    assert "no original pass-3" in mismatches[0].detail


def test_duplicate_block_byte_identity_violation_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)
    transcript_registry = {
        pkey_world.sid[slurp_id].sample_id: build_transcript_record(pkey_world.sid[slurp_id].sample_id, T0_RESPONSES[slurp_id])
        for slurp_id in SLURP_IDS
    }
    dup_row = _row(
        pkey_world, pkey_world.sid[101], TXT_NOSUP_ARM, IOT_WRONG, transcript_registry=transcript_registry
    )
    dup_row["txt_duplicate"] = True
    # Corrupt the duplicate's own rendered transcript text -- a resend that
    # diverges from its own pass-3 original.
    dup_row["messages"][1]["content"][0]["text"] = "The user said: a totally different resend"
    rows = rows + [dup_row]

    report = _build_report(pkey_world, tmp_path, rows)

    assert len(report.duplicate_mismatches) >= 1
    assert any(m.sample_id == pkey_world.sid[101].sample_id for m in report.duplicate_mismatches)
    assert report.void_verdict.voided is True
    assert report.overall == "VOID"
    clause = next(
        c for c in report.void_verdict.clauses
        if c.clause_text == "a txt_duplicate row disagrees with its own pass-3 TXT-NOSUP original (byte-identity)"
    )
    assert clause.verdict == "met"


def test_duplicate_block_matching_resend_is_not_voided_and_reports_delta_f1(pkey_world, tmp_path):
    # NOT _clean_rows()'s own default silence_responses (unanimous unchanged
    # -- see test_silence_swap_unanimous_unchanged_voids_the_read): sample
    # 101 flips under silence here, so THAT clause stays not_met and this
    # fixture isolates the duplicate-block clause exactly the way
    # test_happy_path_key_only_and_zero_defects does for the parent probe.
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        silence_responses={101: NEUTRAL, 900: NEUTRAL, 901: NEUTRAL},
    )
    transcript_registry = {
        pkey_world.sid[slurp_id].sample_id: build_transcript_record(pkey_world.sid[slurp_id].sample_id, T0_RESPONSES[slurp_id])
        for slurp_id in SLURP_IDS
    }
    # A BYTE-IDENTICAL resend of the sample 101 TXT-NOSUP row (same
    # response text -> same score -> zero measured floor for this sample).
    dup_row = _row(
        pkey_world, pkey_world.sid[101], TXT_NOSUP_ARM, IOT_WRONG, transcript_registry=transcript_registry
    )
    dup_row["txt_duplicate"] = True
    rows = rows + [dup_row]

    report = _build_report(pkey_world, tmp_path, rows)

    assert report.duplicate_mismatches == ()
    assert report.void_verdict.voided is False
    assert report.duplicate_block is not None
    assert report.duplicate_block.n_samples == 1
    assert report.duplicate_block.delta_f1 == pytest.approx(0.0)
    assert report.duplicate_block.abs_delta_f1 == pytest.approx(0.0)


def test_duplicate_block_is_none_when_no_duplicate_rows_present(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)  # no duplicate rows at all
    report = _build_report(pkey_world, tmp_path, rows)
    assert report.duplicate_block is None
    assert report.duplicate_mismatches == ()


def test_compute_duplicate_block_delta_f1_hand_computable():
    txt_nosup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(1, 0, 0))]
    # s1's resend scores DIFFERENTLY (empirical non-determinism, not a byte-
    # identity violation -- the PROMPT is identical, the RESPONSE differs).
    duplicate = [_analysis_with_score("s1", _score(1, 0, 0))]

    result = compute_duplicate_block_delta_f1(txt_nosup_analyses=txt_nosup, duplicate_analyses=duplicate)
    assert result.n_samples == 1
    assert result.original_slu_f1 == pytest.approx(0.0)  # s1-only subset of the original pass-3 rows
    assert result.duplicate_slu_f1 == pytest.approx(1.0)
    assert result.delta_f1 == pytest.approx(1.0)
    assert result.abs_delta_f1 == pytest.approx(1.0)


def test_compute_duplicate_block_delta_f1_zero_when_scores_match():
    txt_nosup = [_analysis_with_score("s1", _score(0, 1, 1)), _analysis_with_score("s2", _score(1, 0, 0))]
    duplicate = [_analysis_with_score("s1", _score(0, 1, 1))]  # SAME ingredients as the original s1
    result = compute_duplicate_block_delta_f1(txt_nosup_analyses=txt_nosup, duplicate_analyses=duplicate)
    assert result.delta_f1 == pytest.approx(0.0)
    assert result.abs_delta_f1 == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Silence-swap unanimity VOID bar.
# ---------------------------------------------------------------------------


def test_silence_swap_unanimous_unchanged_voids_the_read(pkey_world, tmp_path):
    rows = _clean_rows(pkey_world)  # silence_responses defaults to aud_sup (unchanged)
    report = _build_report(pkey_world, tmp_path, rows)
    assert all(c.unchanged for c in report.silence_comparisons)
    assert report.void_verdict.voided is True
    silence_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "silence-swap answers persist unchanged")
    assert silence_clause.verdict == "met"


def test_silence_swap_not_unanimous_does_not_void_via_that_clause(pkey_world, tmp_path):
    rows = _build_rows(
        pkey_world,
        aud_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        aud_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        txt_nosup={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},
        txt_sup={101: IOT_RIGHT, 900: NEUTRAL, 901: NEUTRAL},
        silence_responses={101: IOT_WRONG, 900: NEUTRAL, 901: NEUTRAL},  # 101 flips under silence
    )
    report = _build_report(pkey_world, tmp_path, rows)
    assert not all(c.unchanged for c in report.silence_comparisons)
    silence_clause = next(c for c in report.void_verdict.clauses if c.clause_text == "silence-swap answers persist unchanged")
    assert silence_clause.verdict == "not_met"
    assert report.void_verdict.voided is False


# ---------------------------------------------------------------------------
# Loading-layer errors.
# ---------------------------------------------------------------------------


def test_build_pkey_report_raises_on_missing_outputs_jsonl(tmp_path):
    (tmp_path / "attempt").mkdir()
    with pytest.raises(PKeyReadError, match="no outputs.jsonl"):
        load_attempt_rows(tmp_path / "attempt")


# ---------------------------------------------------------------------------
# CLI: idempotence guard (refuses to run twice against the same output dir).
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world: PKeyWorld) -> Path:
    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_cli_refuses_to_run_twice_against_the_same_output_dir(pkey_world, tmp_path, monkeypatch, capsys):
    rows = _clean_rows(pkey_world)
    attempt_dir = _write_attempt_dir(tmp_path / "attempt", rows)

    repo_root = _cli_repo_layout(tmp_path, pkey_world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(pkey_world.data_root))
    output_dir = tmp_path / "read-report"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(pkey_world.sample_manifest_path),
        "--roster-table", str(pkey_world.roster_table_path),
    ]

    first_exit = pkey_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = pkey_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert "already exists" in captured.err
    assert verdict_path.read_bytes() == first_bytes  # untouched by the refused second run
