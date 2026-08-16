"""P2 R-ladder offline read suite: hand-authored synthetic fixtures only.

Every numerator/denominator, guard trigger, the n=6 legitimate-empty
exclusion, the voiding precedence, and the Wilcoxon reuse are exercised
against fixtures built in this file -- never against
$SPEECHRL_DATA_DIR/runs/SAEA-P2-*/... or SAEA-D4-*/... (the pre-registered
P2 results stay unread).

ONE documented exception (F1): a handful of tests near the end of this file
read the PRESERVED r0bias salvage archive (docs/checks/speech-aware-
evidence-acquisition/2026-08-16-p2-r0bias-salvage/) through
:func:`read_arm_from_salvage`. That archive's read is already spent
(one-shot semantics, docs/p2-branch-rule-pins.md Pin 1) and its bytes are
durably preserved specifically so F1 could be developed against the real
schema; those tests never open $SPEECHRL_DATA_DIR/runs/SAEA-P2-* (no run
directory for any arm is read there, salvage or otherwise)."""

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis import p2_reads as p2
from speech_aware_evidence_acquisition.core.bundle import RUN_MANIFEST_SCHEMA, STATUS_COMPLETED
from speech_aware_evidence_acquisition.data.lock import load_lock


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# guarded_rate / compare_via_raw_counts (docs/p2-metric-definitions-mirror.md
# sections 3.1 / 4.1, IDENTICAL guard for HER and RIR).
# ---------------------------------------------------------------------------


def test_guarded_rate_resolved_at_or_above_the_floor():
    rate = p2.guarded_rate(3, 10, label="HER[macro]")
    assert rate.status == "resolved"
    assert rate.rate == pytest.approx(0.3)
    assert rate.numerator == 3 and rate.denominator == 10


def test_guarded_rate_descriptive_only_below_the_floor():
    rate = p2.guarded_rate(1, 3, label="HER[macro]")
    assert rate.status == "descriptive_only"
    assert rate.rate == pytest.approx(1 / 3)
    assert "descriptive only" in rate.note


def test_guarded_rate_zero_denominator_is_descriptive_only_with_no_rate():
    rate = p2.guarded_rate(0, 0, label="RIR")
    assert rate.status == "descriptive_only"
    assert rate.rate is None


def test_guarded_rate_refuses_numerator_exceeding_denominator():
    with pytest.raises(p2.P2ReadsError):
        p2.guarded_rate(5, 3, label="HER[macro]")


def test_guarded_rate_refuses_negative_inputs():
    with pytest.raises(p2.P2ReadsError):
        p2.guarded_rate(-1, 3, label="HER[macro]")


def test_compare_via_raw_counts_favors_lower_when_lower_is_better():
    a = p2.guarded_rate(1, 3, label="a")
    b = p2.guarded_rate(2, 3, label="b")
    assert p2.compare_via_raw_counts(a, b, lower_is_better=True) == "favors_a"
    assert p2.compare_via_raw_counts(b, a, lower_is_better=True) == "favors_b"


def test_compare_via_raw_counts_tie():
    a = p2.guarded_rate(2, 3, label="a")
    b = p2.guarded_rate(2, 5, label="b")
    assert p2.compare_via_raw_counts(a, b, lower_is_better=True) == "tie"


def test_compare_via_raw_counts_unresolved_when_either_denominator_is_zero():
    a = p2.guarded_rate(0, 0, label="a")
    b = p2.guarded_rate(1, 3, label="b")
    assert p2.compare_via_raw_counts(a, b, lower_is_better=True) == "unresolved"
    assert p2.compare_via_raw_counts(b, a, lower_is_better=True) == "unresolved"


# ---------------------------------------------------------------------------
# HER -- exact numerator/denominator, the strict-inequality harm criterion,
# and the mandatory <10 guard (mirror section 3 / 3.1).
# ---------------------------------------------------------------------------


def _splice(sample_id, macro_pass1, macro_post, entity_pass1=0, entity_post=0):
    return p2.SpliceScore(
        sample_id=sample_id, window_iteration=0, span_index=0,
        macro_pass1_errors=macro_pass1, macro_post_errors=macro_post,
        entity_pass1_errors=entity_pass1, entity_post_errors=entity_post,
    )


def test_splice_is_harmful_requires_strict_increase_equality_is_not_harm():
    equal = _splice("s1", macro_pass1=2, macro_post=2)
    increased = _splice("s2", macro_pass1=2, macro_post=3)
    decreased = _splice("s3", macro_pass1=3, macro_post=2)
    assert p2.splice_is_harmful(equal, "macro") is False
    assert p2.splice_is_harmful(increased, "macro") is True
    assert p2.splice_is_harmful(decreased, "macro") is False


def test_splice_is_harmful_rejects_unknown_ledger():
    with pytest.raises(p2.P2ReadsError):
        p2.splice_is_harmful(_splice("s1", 1, 1), "phoneme")


def test_compute_her_below_guard_floor_is_descriptive_only_with_exact_counts():
    # mirror's own worked example shape: 3 accepted splices, denominator < 10.
    splices = [
        _splice("s1", macro_pass1=1, macro_post=2),  # harmful
        _splice("s2", macro_pass1=2, macro_post=1),  # not harmful (improved)
        _splice("s3", macro_pass1=1, macro_post=1),  # not harmful (equal)
    ]
    result = p2.compute_her(splices, "macro")
    assert result.harmful_splices == 1
    assert result.accepted_splices == 3
    assert result.rate.status == "descriptive_only"
    assert result.rate.rate == pytest.approx(1 / 3)
    assert result.harmful_sample_ids == ("s1",)


def test_compute_her_at_or_above_guard_floor_is_resolved():
    splices = [_splice(f"s{i}", macro_pass1=1, macro_post=2) for i in range(4)] + [
        _splice(f"s{i}", macro_pass1=2, macro_post=1) for i in range(6)
    ]
    result = p2.compute_her(splices, "macro")
    assert result.accepted_splices == 10
    assert result.harmful_splices == 4
    assert result.rate.status == "resolved"
    assert result.rate.rate == pytest.approx(0.4)


def test_compute_her_zero_accepted_splices_is_degenerate():
    result = p2.compute_her([], "macro")
    assert result.accepted_splices == 0
    assert result.rate.status == "descriptive_only"
    assert result.rate.rate is None


def test_compute_her_ledgers_are_independent():
    splices = [_splice("s1", macro_pass1=1, macro_post=2, entity_pass1=1, entity_post=1)]
    macro = p2.compute_her(splices, "macro")
    entity = p2.compute_her(splices, "entity")
    assert macro.harmful_splices == 1
    assert entity.harmful_splices == 0


# ---------------------------------------------------------------------------
# RIR -- exact numerator/denominator and the same guard (mirror section 4/4.1).
# ---------------------------------------------------------------------------


def _rir(sample_id, entity_id, wrong, delivered, correct_final):
    return p2.RIRTokenRecord(
        sample_id=sample_id, entity_id=entity_id,
        wrong_in_pass1=wrong, correct_form_delivered=delivered, correct_in_final=correct_final,
    )


def test_compute_rir_denominator_is_wrong_and_delivered_numerator_is_also_correct_in_final():
    records = [
        _rir("s1", "e1", wrong=True, delivered=True, correct_final=True),  # numerator + denominator
        _rir("s1", "e2", wrong=True, delivered=True, correct_final=False),  # denominator only
        _rir("s1", "e3", wrong=True, delivered=False, correct_final=True),  # not delivered -> excluded
        _rir("s1", "e4", wrong=False, delivered=True, correct_final=True),  # not wrong -> excluded
    ]
    result = p2.compute_rir(records)
    assert result.denominator == 2
    assert result.numerator == 1
    assert result.rate.rate == pytest.approx(0.5)
    assert result.rate.status == "descriptive_only"  # denominator 2 < 10


def test_compute_rir_at_or_above_guard_floor_is_resolved():
    records = [_rir(f"s{i}", f"e{i}", wrong=True, delivered=True, correct_final=(i < 7)) for i in range(10)]
    result = p2.compute_rir(records)
    assert result.denominator == 10
    assert result.numerator == 7
    assert result.rate.status == "resolved"
    assert result.rate.rate == pytest.approx(0.7)


def test_compute_rir_zero_denominator_is_degenerate():
    records = [_rir("s1", "e1", wrong=False, delivered=True, correct_final=True)]
    result = p2.compute_rir(records)
    assert result.denominator == 0
    assert result.rate.status == "descriptive_only"
    assert result.rate.rate is None


# ---------------------------------------------------------------------------
# Wilcoxon reuse + the n=6 legitimate-empty exclusion (arms file: four of
# the ten calls fly legitimate-empty -> paired Wilcoxon effective n=6).
# ---------------------------------------------------------------------------


def _call(sample_id, macro_wer, entity_correct, expected_total=10, legitimate_empty=False):
    return p2.PerCallMetrics(
        sample_id=sample_id, macro_wer=macro_wer,
        macro_ref_hit_mask=(True,) * (expected_total - 1) + (False,),
        entity_wer=1.0 - entity_correct / expected_total if expected_total else 0.0,
        entity_correct=entity_correct, entity_expected_total=expected_total,
        legitimate_empty=legitimate_empty,
    )


def test_build_wilcoxon_contrast_matches_direct_call_on_a_hand_checkable_example():
    """Same two-point example test_context_dose_comparison.py's own
    ``test_wilcoxon_signed_rank_exact_on_a_hand_checkable_pair`` uses,
    wired through this module's contrast builder instead of called bare --
    proves the reuse is bit-identical, not a re-derivation."""

    from speech_aware_evidence_acquisition.analysis.context_dose import wilcoxon_signed_rank_exact

    condition = {"s1": _call("s1", macro_wer=0.30, entity_correct=6), "s2": _call("s2", macro_wer=0.10, entity_correct=6)}
    reference = {"s1": _call("s1", macro_wer=0.20, entity_correct=6), "s2": _call("s2", macro_wer=0.40, entity_correct=6)}
    contrast = p2.build_wilcoxon_contrast("t", "cond", "ref", "macro", condition, reference)
    assert contrast.diffs == (pytest.approx(0.10), pytest.approx(-0.30))
    assert contrast.wilcoxon == wilcoxon_signed_rank_exact([0.10, -0.30])


def test_build_wilcoxon_contrast_excludes_legitimate_empty_calls_to_n6():
    ids = [f"s{i}" for i in range(10)]
    empty_ids = {"s0", "s3", "s6", "s9"}  # mirrors "four of the ten calls"
    condition = {sid: _call(sid, macro_wer=0.2, entity_correct=6, legitimate_empty=sid in empty_ids) for sid in ids}
    reference = {sid: _call(sid, macro_wer=0.3, entity_correct=5) for sid in ids}
    contrast = p2.build_wilcoxon_contrast("t", "cond", "ref", "macro", condition, reference)
    assert len(contrast.included_sample_ids) == 6
    assert contrast.excluded_legitimate_empty == ("s0", "s3", "s6", "s9")
    assert contrast.wilcoxon.n_pairs == 6


def test_build_wilcoxon_contrast_excludes_when_EITHER_side_is_legitimate_empty():
    ids = [f"s{i}" for i in range(4)]
    condition = {sid: _call(sid, 0.2, 6, legitimate_empty=(sid == "s0")) for sid in ids}
    reference = {sid: _call(sid, 0.3, 5, legitimate_empty=(sid == "s1")) for sid in ids}
    contrast = p2.build_wilcoxon_contrast("t", "cond", "ref", "macro", condition, reference)
    assert contrast.included_sample_ids == ("s2", "s3")
    assert contrast.excluded_legitimate_empty == ("s0", "s1")


def test_build_wilcoxon_contrast_refuses_mismatched_sample_sets():
    condition = {"s1": _call("s1", 0.1, 6)}
    reference = {"s2": _call("s2", 0.1, 6)}
    with pytest.raises(p2.P2ReadsError):
        p2.build_wilcoxon_contrast("t", "cond", "ref", "macro", condition, reference)


def test_build_wilcoxon_contrast_per_call_macro_transitions_reuse_flag_transitions():
    condition = {"s1": _call("s1", 0.1, 6, expected_total=4)}
    reference = {"s1": _call("s1", 0.1, 6, expected_total=4)}
    # override ref_hit_mask directly to a hand-picked transition
    condition["s1"] = condition["s1"].__class__(
        **{**condition["s1"].__dict__, "macro_ref_hit_mask": (True, True, False, True)}
    )
    reference["s1"] = reference["s1"].__class__(
        **{**reference["s1"].__dict__, "macro_ref_hit_mask": (True, False, False, False)}
    )
    contrast = p2.build_wilcoxon_contrast("t", "cond", "ref", "macro", condition, reference)
    transitions = contrast.per_call[0].macro_transitions
    # reference=(T,F,F,F), condition=(T,T,F,T): pos0 T->T, pos1 F->T,
    # pos2 F->F, pos3 F->T.
    assert transitions.correct_to_correct == 1  # position 0
    assert transitions.wrong_to_correct == 2  # positions 1, 3
    assert transitions.correct_to_wrong == 0
    assert transitions.wrong_to_wrong == 1  # position 2


def test_ledger_value_rejects_unknown_ledger():
    with pytest.raises(p2.P2ReadsError):
        p2._ledger_value(_call("s1", 0.1, 6), "phoneme")


# ---------------------------------------------------------------------------
# per_term_flip_list.
# ---------------------------------------------------------------------------


def test_per_term_flip_list():
    flips = p2.per_term_flip_list(
        "r1verify", "r0bias",
        reference_correct_terms={"acme", "bistricer"},
        condition_correct_terms={"bistricer", "micheal"},
    )
    assert flips.flipped_to_correct == ("micheal",)
    assert flips.flipped_to_wrong == ("acme",)


# ---------------------------------------------------------------------------
# format_normalized_wer -- reuses align/tokens_v1 unchanged; only the
# normalization input changes (module docstring note 5).
# ---------------------------------------------------------------------------


def test_format_normalized_wer_survives_punctuation_and_case_drift():
    result = p2.format_normalized_wer(["co-op", "revenue"], "Co Op, Revenue!")
    assert result.wer == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# delivered_reference_text -- exemplars_attached is a FLAT list of label
# strings in the authoritative runtime schema (reproduction/replay_loop.py),
# not a list of {"label": ...} mappings (a correction relative to the
# salvage script's own assumption; see module docstring/comment).
# ---------------------------------------------------------------------------


def test_delivered_reference_text_candidates_and_flat_exemplar_labels():
    window = {
        "replay_candidates": [{"text": "Acme", "score": 0.9}, {"text": "Corp", "score": 0.5}],
        "replay_exemplars_attached": ["Jane Doe", None, ""],
    }
    assert p2.delivered_reference_text(window) == "Acme Corp Jane Doe"


def test_delivered_reference_text_handles_missing_fields():
    assert p2.delivered_reference_text({}) == ""


# ---------------------------------------------------------------------------
# copy_count_for_arm -- reuses reproduction.replay_loop guard predicates and
# core.retrieval.normalize_term; measured on PRE-LOCALIZE replay text (D7E
# guard-2 aperture note).
# ---------------------------------------------------------------------------


def _window(sample_id, *, replay_text, pass1_text, candidates=(), exemplars=(), accepted=True, localized_words=None):
    return {
        "replay_sample_id": sample_id,
        "replay_window_iteration": 0,
        "replay_span_index": 0,
        "replay_candidates": [{"text": t, "score": 1.0} for t in candidates],
        "replay_exemplars_attached": list(exemplars),
        "replay_pass1_text": pass1_text,
        "replay_replay_text": replay_text,
        "replay_accepted": accepted,
        "replay_reject_reason": None if accepted else "rejected",
        "replay_localized_words": localized_words if localized_words is not None else (replay_text or "").split(),
    }


def test_copy_count_for_arm_counts_verbatim_copies_on_pre_localize_text():
    windows = [
        _window("s1", replay_text="the model said wrongname here", pass1_text="something else", candidates=["wrongname"]),
        _window("s2", replay_text="clean transcript with no copy", pass1_text="clean transcript", candidates=["othername"]),
        _window("s3", replay_text=None, pass1_text=None, candidates=["unreachable"], accepted=False),  # no-candidates skip
    ]
    result = p2.copy_count_for_arm("r0wrong", windows)
    assert result.total_windows == 3
    assert result.called_windows == 2  # s3 never received a call
    assert result.windows_with_copy == 1
    assert result.total_copy_occurrences == 1
    assert result.novel_copies == 1  # "wrongname" absent from pass1
    assert result.copy_rate == pytest.approx(0.5)


def test_copy_count_for_arm_zero_called_windows_has_zero_rate_not_a_zerodivisionerror():
    result = p2.copy_count_for_arm("r0wrong", [])
    assert result.called_windows == 0
    assert result.copy_rate == 0.0


def test_copy_count_for_arm_counts_a_non_novel_copy():
    windows = [
        _window("s1", replay_text="wrongname was already in pass1", pass1_text="wrongname stayed", candidates=["wrongname"]),
    ]
    result = p2.copy_count_for_arm("r0wrong", windows)
    assert result.windows_with_copy == 1
    assert result.novel_copies == 0  # "wrongname" WAS present in pass1 already


# ---------------------------------------------------------------------------
# Mechanical branch-rule evaluator: voiding precedence, AFFIRM/COLLAPSE/
# UNRESOLVED, clauses quoted verbatim against the actual arms file text.
# ---------------------------------------------------------------------------


def test_branch_rules_text_matches_the_registered_arms_file_verbatim():
    arms_file = (
        Path(__file__).resolve().parents[2] / "docs" / "arms" / "p2-rladder.arms"
    ).read_text(encoding="utf-8")
    # BRANCH_RULES_TEXT is a whitespace-joined rendering of the commented
    # block; every distinctive substring below must appear verbatim in the
    # committed registration so this module can never silently drift from it.
    for fragment in (
        "operator AFFIRMED iff at",
        "least one of (R2-R1>0) / (R1 beats R0-bias at matched entity gain",
        "with lower HER) / (wrongref copy rate materially lower under verify",
        "than bias framing). Taxonomy COLLAPSE iff R1~R0-bias on both ledgers",
        "Wrong-reference copying in R1/R2",
        "voids the audio-verification claim regardless of WER deltas.",
    ):
        assert fragment in arms_file
        assert fragment in p2.BRANCH_RULES_TEXT


def _contrast(diffs, entity_deltas=None):
    entity_deltas = entity_deltas if entity_deltas is not None else [0] * len(diffs)
    per_call = tuple(
        p2.PerCallRow(sample_id=f"s{i}", condition_value=0.0, reference_value=0.0, diff=d,
                       macro_transitions=None, entity_correct_delta=ed)
        for i, (d, ed) in enumerate(zip(diffs, entity_deltas))
    )
    from speech_aware_evidence_acquisition.analysis.context_dose import wilcoxon_signed_rank_exact
    return p2.ContrastResult(
        name="t", condition_arm="a", reference_arm="b", ledger="macro",
        included_sample_ids=tuple(row.sample_id for row in per_call),
        excluded_legitimate_empty=(), diffs=tuple(diffs),
        wilcoxon=wilcoxon_signed_rank_exact(diffs), per_call=per_call,
    )


def _copy(windows_with_copy, called_windows):
    return p2.CopyCountResult(
        arm="x", total_windows=called_windows, called_windows=called_windows, accepted_splices=0,
        total_copy_occurrences=windows_with_copy, windows_with_copy=windows_with_copy,
        novel_copies=0, guard3_unsupported=0, copy_window_sample_ids=(),
    )


def _her(harmful, accepted, rate=None):
    r = p2.guarded_rate(harmful, accepted, label="HER[entity]")
    return p2.HERResult(ledger="entity", harmful_splices=harmful, accepted_splices=accepted, rate=r, harmful_sample_ids=())


def test_voiding_precedence_bars_affirm_even_when_an_affirm_clause_would_fire():
    # r2 beats r1 on entities (clause A would AFFIRM) but r1wrong copies its
    # wrong reference verbatim -> VOIDED, and AFFIRM must NOT be "met".
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([-0.1] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[1] * 6),
        macro_r2_vs_r1=_contrast([-0.1] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[1] * 6),
        her_r1verify=_her(1, 20), her_r0bias=_her(5, 20),
        copy_r1wrong=_copy(windows_with_copy=3, called_windows=10),
        copy_r0wrong=_copy(windows_with_copy=0, called_windows=10),
        copy_r2draft=_copy(windows_with_copy=0, called_windows=10),
    )
    assert verdict.voided is True
    assert verdict.affirm == "not_met"
    assert verdict.overall.startswith("VOIDED")
    # the affirm clauses are still computed and reported (transparency),
    # even though voiding bars the overall AFFIRM verdict.
    assert verdict.affirm_clauses[0].verdict == "met"


def test_affirm_via_clause_a_r2_beats_r1_on_entities():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        # F4: clause A is conjunctive (Pin 2) -- BOTH ledgers must move in
        # R2's favor, so the macro contrast here must be strictly negative
        # too, not a bare tie.
        macro_r2_vs_r1=_contrast([-0.05] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[2] * 6),  # R2 recovers more entities
        her_r1verify=_her(1, 20), her_r0bias=_her(1, 20),
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm == "met"
    assert verdict.overall == "AFFIRMED"
    assert verdict.affirm_clauses[0].verdict == "met"
    assert verdict.affirm_clauses[0].clause_text == "(R2-R1>0)"


def test_clause_a_mixed_result_does_not_fire_and_is_reported_mixed():
    """Pin 2 (F4): a mixed result -- only ONE ledger moves in R2's favor --
    does not fire the limb and is reported "not_met" with a "mixed" detail
    path, never silently resolved via either ledger alone."""

    entity_up_only = p2._clause_a_r2_beats_r1(
        _contrast([0.0] * 6, entity_deltas=[3] * 6),  # entity delta=18>0
        _contrast([0.0] * 6),  # macro delta=0, not strictly <0
    )
    assert entity_up_only.verdict == "not_met"
    assert "mixed" in entity_up_only.detail

    macro_down_only = p2._clause_a_r2_beats_r1(
        _contrast([0.0] * 6, entity_deltas=[0] * 6),  # entity delta=0, not >0
        _contrast([-0.05] * 6),  # macro delta=-0.05, strictly <0
    )
    assert macro_down_only.verdict == "not_met"
    assert "mixed" in macro_down_only.detail


def test_affirm_via_clause_b_r1_beats_r0bias_matched_entity_gain_lower_her():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[3] * 6),  # R1 gains entities vs R0bias
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(1, 20), her_r0bias=_her(5, 20),  # R1's HER is lower
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm == "met"
    assert verdict.affirm_clauses[1].verdict == "met"


def test_affirm_via_clause_b_falls_back_to_raw_her_counts_when_guard_bound():
    # denominators < 10 on both sides -> HER is descriptive_only -> clause B
    # falls back to raw harmful-splice counts (mirror section 3.1).
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[1] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(0, 3), her_r0bias=_her(2, 3),
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm_clauses[1].verdict == "met"
    assert "guard-bound" in verdict.affirm_clauses[1].detail


def test_clause_b_unresolved_when_her_denominators_are_both_zero():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[1] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(0, 0), her_r0bias=_her(0, 0),
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm_clauses[1].verdict == "unresolved"
    assert verdict.affirm == "unresolved"
    assert "UNRESOLVED" in verdict.overall


def test_affirm_via_clause_c_wrongref_copy_rate_materially_lower_under_verify():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(1, 20), her_r0bias=_her(1, 20),
        # r1wrong must stay at ZERO copies here: any nonzero r1wrong copy
        # count fires the VOIDING clause regardless of clause C, which is
        # exactly what test_voiding_precedence_bars_affirm_even_when_an_
        # affirm_clause_would_fire covers separately.
        copy_r1wrong=_copy(windows_with_copy=0, called_windows=10),  # 0% copy rate
        copy_r0wrong=_copy(windows_with_copy=8, called_windows=10),  # 80% copy rate
        copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm_clauses[2].verdict == "met"
    assert verdict.affirm == "met"


def test_collapse_when_every_similarity_clause_holds():
    # NOTE (F2/F3 interlock, see _voiding_clause's own docstring): clause C
    # can only resolve cleanly to "not_met" when C_verify (== copy_r1wrong's
    # raw count) is >= 2 -- but that ALSO trips voiding (Pin 6, F3) and
    # overrides the overall verdict to "VOIDED" regardless of collapse. To
    # isolate the COLLAPSE similarity-conjunct machinery under test here
    # from clause C's OWN Pin-4 threshold arithmetic (which has its
    # dedicated tests elsewhere in this file), this scenario overrides
    # material_relative_drop down so a NON-voiding C_verify=1 against a
    # C_bias=4 base still resolves clause C "not_met" cleanly.
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(2, 20), her_r0bias=_her(2, 20),
        copy_r1wrong=_copy(1, 10), copy_r0wrong=_copy(4, 10), material_relative_drop=0.1,
        copy_r2draft=_copy(0, 10),
    )
    assert verdict.voided is False
    assert verdict.affirm == "not_met"
    assert verdict.collapse == "met"
    assert verdict.overall == "COLLAPSE"


def test_neither_affirmed_nor_collapsed_when_no_clause_fires():
    # Same F2/F3-interlock override as test_collapse_when_every_similarity_
    # clause_holds above (see its note): a non-voiding, cleanly-"not_met"
    # clause C requires overriding material_relative_drop away from its
    # Pin-4 default of 0.5 for this particular AFFIRM/COLLAPSE-plumbing
    # test; clause C's own default-threshold arithmetic is covered
    # separately (test_clause_c_unresolved_when_c_bias_below_floor / test_
    # clause_c_met_and_not_met_around_the_50_percent_threshold below).
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[-1] * 6),  # R1 LOSES vs R0bias
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),  # tie, not similar-enough win
        her_r1verify=_her(5, 20), her_r0bias=_her(1, 20),  # R1's HER is HIGHER (worse)
        # r1wrong stays at 1 copy (a count >= 2 would fire VOIDING, tested
        # separately) with r0wrong at 4 -- clause C is cleanly "not_met"
        # under the overridden 10% drop threshold (1 > 0.1*4).
        copy_r1wrong=_copy(1, 10), copy_r0wrong=_copy(4, 10), material_relative_drop=0.1,
        copy_r2draft=_copy(0, 10),
    )
    assert verdict.voided is False
    assert verdict.affirm == "not_met"
    assert verdict.collapse == "not_met"
    assert verdict.overall == "NEITHER AFFIRMED NOR COLLAPSED (no clause fired either way)"


# ---------------------------------------------------------------------------
# F2 -- clause C: basis is raw total_copy_occurrences, 50% relative-drop
# threshold, C_bias >= 4 floor (below it -> unresolved, never not_met).
# ---------------------------------------------------------------------------


def test_clause_c_unresolved_when_c_bias_below_floor():
    result = p2._clause_c_wrongref_copy_rate(_copy(0, 10), _copy(3, 10))
    assert result.verdict == "unresolved"
    assert "floor" in result.detail


def test_clause_c_met_and_not_met_around_the_50_percent_threshold():
    # C_bias=10 (>= floor 4), C_verify=5 -> exactly 50% -> met (Pin 4: "<=").
    met = p2._clause_c_wrongref_copy_rate(_copy(5, 10), _copy(10, 10))
    assert met.verdict == "met"
    # C_verify=6 -> 60%, strictly above the 50% drop -> not_met.
    not_met = p2._clause_c_wrongref_copy_rate(_copy(6, 10), _copy(10, 10))
    assert not_met.verdict == "not_met"


# ---------------------------------------------------------------------------
# F3 -- voiding: basis is raw total_copy_occurrences, void iff >= 2 on
# EITHER side; exactly 1 does not void but is a reported material weakening.
# ---------------------------------------------------------------------------


def test_voiding_exactly_one_copy_does_not_void_but_notes_a_weakening():
    clause, note = p2._voiding_clause(_copy(1, 10), _copy(0, 10))
    assert clause.verdict == "not_met"
    assert note is not None
    assert "r1wrong=1" in note


def test_voiding_two_or_more_copies_voids_with_no_weakening_note():
    clause, note = p2._voiding_clause(_copy(2, 10), _copy(0, 10))
    assert clause.verdict == "met"
    assert note is None


def test_voiding_weakening_note_surfaces_through_evaluate_branch_rules_and_rendering():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(2, 20), her_r0bias=_her(2, 20),
        copy_r1wrong=_copy(1, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.voided is False
    assert verdict.weakening_note is not None
    rendered = p2.render_branch_verdict(verdict)
    assert "WEAKENING NOTE" in rendered
    document = p2._branch_verdict_json(verdict)
    assert document["weakening_note"] == verdict.weakening_note


# ---------------------------------------------------------------------------
# F5 -- clause B: MATCHED_GAIN_TOKEN_MARGIN=25, entity_gain redefined as
# entity_delta >= -25, and a guard-bound RAW-COUNT TIE (not just a zero
# denominator) resolves the clause UNRESOLVED, never not_met.
# ---------------------------------------------------------------------------


def test_clause_b_unresolved_on_a_raw_tie_not_just_zero_denominators():
    contrast = _contrast([0.0] * 6, entity_deltas=[0] * 6)
    result = p2._clause_b_r1_beats_r0bias(contrast, _her(2, 5), _her(2, 8))
    assert result.verdict == "unresolved"


def test_clause_b_matched_entity_gain_margin_boundary_both_sides():
    at_margin = _contrast([0.0] * 6, entity_deltas=[-25] + [0] * 5)  # sum=-25
    beyond_margin = _contrast([0.0] * 6, entity_deltas=[-26] + [0] * 5)  # sum=-26
    her_r1_lower, her_r0bias_higher = _her(1, 20), _her(5, 20)  # resolved, her_lower=True
    at = p2._clause_b_r1_beats_r0bias(at_margin, her_r1_lower, her_r0bias_higher)
    beyond = p2._clause_b_r1_beats_r0bias(beyond_margin, her_r1_lower, her_r0bias_higher)
    assert at.verdict == "met"  # exactly -25 tokens: still "matched" (Pin 5: <=)
    assert beyond.verdict == "not_met"  # -26 tokens: no longer matched


# ---------------------------------------------------------------------------
# F6 -- COLLAPSE: macro tie floor 0.001 fractional (0.10pp), the entity
# conjunct compares entity_correct_delta (not entity_wer) at a 25-token
# margin, and collapse_her falls back to raw counts when guard-bound
# (a degenerate raw comparison -> unresolved, never auto-"met").
# ---------------------------------------------------------------------------


def test_collapse_macro_similarity_tie_floor_boundary_both_sides():
    at_floor = _contrast([0.001] * 6)
    beyond_floor = _contrast([0.0011] * 6)
    assert p2._collapse_clause_macro_similarity(at_floor).verdict == "met"
    assert p2._collapse_clause_macro_similarity(beyond_floor).verdict == "not_met"


def test_collapse_entity_similarity_token_margin_boundary_both_sides():
    at_margin = _contrast([0.0] * 6, entity_deltas=[25] + [0] * 5)
    beyond_margin = _contrast([0.0] * 6, entity_deltas=[26] + [0] * 5)
    assert p2._collapse_clause_entity_similarity(at_margin).verdict == "met"
    assert p2._collapse_clause_entity_similarity(beyond_margin).verdict == "not_met"


def test_collapse_her_similarity_falls_back_to_raw_counts_when_guard_bound():
    tie = p2._collapse_her_similarity(_her(1, 5), _her(1, 5))  # equal raw counts, guard-bound -> unresolved
    assert tie.verdict == "unresolved"

    resolved_similar = p2._collapse_her_similarity(_her(2, 20), _her(2, 20))  # resolved rates, equal
    assert resolved_similar.verdict == "met"

    resolved_not_similar = p2._collapse_her_similarity(_her(1, 20), _her(5, 20))  # resolved rates, differ
    assert resolved_not_similar.verdict == "not_met"

    guard_bound_not_similar = p2._collapse_her_similarity(_her(1, 5), _her(4, 5))  # raw counts differ, guard-bound
    assert guard_bound_not_similar.verdict == "not_met"


def test_collapse_unresolved_when_her_conjunct_is_0_vs_0():
    """Both clause B (AFFIRM) and the collapse HER conjunct are guard-aware
    over the SAME her_r1verify/her_r0bias inputs (Pin 3/5) -- a 0-vs-0 raw
    tie leaves BOTH unresolved, so neither AFFIRM nor COLLAPSE can be
    cleanly declared (F5/F6)."""

    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(0, 0), her_r0bias=_her(0, 0),
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    assert verdict.affirm_clauses[1].verdict == "unresolved"  # clause B
    assert verdict.collapse_clauses[2].verdict == "unresolved"  # collapse_her
    assert verdict.affirm == "unresolved"
    assert verdict.collapse == "unresolved"
    assert "UNRESOLVED" in verdict.overall


def test_render_branch_verdict_quotes_every_clause_and_the_registered_text():
    verdict = p2.evaluate_branch_rules(
        macro_r1_vs_r0bias=_contrast([0.0] * 6),
        entity_r1_vs_r0bias=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        macro_r2_vs_r1=_contrast([0.0] * 6),
        entity_r2_vs_r1=_contrast([0.0] * 6, entity_deltas=[0] * 6),
        her_r1verify=_her(2, 20), her_r0bias=_her(2, 20),
        copy_r1wrong=_copy(0, 10), copy_r0wrong=_copy(0, 10), copy_r2draft=_copy(0, 10),
    )
    rendered = p2.render_branch_verdict(verdict)
    assert p2.BRANCH_RULES_TEXT in rendered
    assert "(R2-R1>0)" in rendered
    assert "OVERALL:" in rendered


# ---------------------------------------------------------------------------
# Offline extraction layer: real arm run dir shape -> ArmRead. Reuses
# find_completed_attempt (context_dose) and the frozen scorers; never
# touches speechrl-data/runs -- everything below is written under tmp_path.
# ---------------------------------------------------------------------------


def _write_fake_arm_run(
    tmp_path, run_id, attempt_id, *, carrier_lock_key, samples, replay_windows
):
    """Mirrors tests/unit/test_scorers.py's _write_fake_run, extended with a
    trace.jsonl carrying REPLAY channel records -- the same on-disk shape
    core.bundle.build_manifest + a real run's trace sink produce."""

    runs_root = tmp_path / "runs"
    attempt_dir = runs_root / run_id / attempt_id
    attempt_dir.mkdir(parents=True)
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    outputs_text = "".join(
        json.dumps({"sample_id": sid, "carrier_lock_key": carrier_lock_key, "text": text}, sort_keys=True) + "\n"
        for sid, text in samples
    )
    outputs_path.write_text(outputs_text, encoding="utf-8")

    trace_path = attempt_dir / f"{run_id}.trace.jsonl"
    trace_text = "".join(
        json.dumps({"channel": "REPLAY", "payload": window}, sort_keys=True) + "\n" for window in replay_windows
    )
    trace_path.write_text(trace_text, encoding="utf-8")

    manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "run_id": run_id,
        "created_at": "2026-08-16T00:00:00+00:00",
        "status": STATUS_COMPLETED,
        "failure_reason": None,
        "plan": {"carrier_lock_key": carrier_lock_key},
        "outputs": {"path": str(outputs_path.resolve()), "sha256": _sha256_text(outputs_text)},
    }
    (attempt_dir / f"{run_id}.run-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return runs_root / run_id


def test_read_arm_end_to_end_on_a_synthetic_run_dir(tmp_path, synthetic_world):
    # Sample 4000001: a genuine reference, an accepted splice that is
    # HARMFUL on macro but NOT on entity (verifies the ledgers stay
    # independent through the whole extraction pipeline), plus one RIR-
    # eligible delivered candidate and one wrong-reference copy.
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text(
        "token|tags|wer_tags\n"
        "bistricer||['0']\n"
        "said||[]\n"
        "the||[]\n"
        "revenue||[]\n"
        "grew||[]\n",
        encoding="utf-8",
    )
    sidecar = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json"
    sidecar.write_text(json.dumps({"0": {"entity_type": "PERSON"}}), encoding="utf-8")

    # Sample 4000002: legitimate-empty (zero replay windows), perfectly
    # scored final hypothesis.
    nlp2 = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000002.nlp"
    nlp2.write_text("token|tags|wer_tags\nok||[]\nfine||[]\n", encoding="utf-8")
    sidecar2 = synthetic_world.e21 / "transcripts" / "wer_tags" / "4000002.wer_tag.json"
    sidecar2.write_text("{}", encoding="utf-8")

    samples = [
        ("4000001", "bistricer said the revenue grew"),
        ("4000002", "ok fine"),
    ]
    windows = [
        # accepted splice: pass1 span "grew" (4 macro errors vs full ref),
        # post-splice span "grew extra hallucinated words" (7 macro errors)
        # -> HARMFUL on macro. Neither span contains the entity mention
        # ("bistricer") -> entity errors equal (1 vs 1) -> NOT harmful on
        # entity.
        {
            "replay_sample_id": "4000001", "replay_window_iteration": 0, "replay_span_index": 0,
            "replay_candidates": [], "replay_exemplars_attached": [],
            "replay_pass1_text": "grew", "replay_replay_text": "grew extra hallucinated words",
            "replay_accepted": True, "replay_reject_reason": None,
            "replay_localized_words": ["grew", "extra", "hallucinated", "words"],
        },
        # a second, rejected window that delivers the correct form of the
        # PERSON entity ("Bistricer") after a garbled pass-1 ("bistricher")
        # -> RIR-eligible (wrong in pass1, delivered, correct in final).
        {
            "replay_sample_id": "4000001", "replay_window_iteration": 1, "replay_span_index": 1,
            "replay_candidates": [{"text": "Bistricer", "score": 0.9}], "replay_exemplars_attached": [],
            "replay_pass1_text": "bistricher", "replay_replay_text": "bistricher",
            "replay_accepted": False, "replay_reject_reason": "low-confidence",
            "replay_localized_words": [],
        },
        # a window that COPIES its delivered (here, incidentally correct)
        # candidate verbatim into the pre-localize replay text -- exercises
        # the copy-count path end to end.
        {
            "replay_sample_id": "4000001", "replay_window_iteration": 2, "replay_span_index": 2,
            "replay_candidates": [{"text": "revenue", "score": 0.5}], "replay_exemplars_attached": [],
            "replay_pass1_text": "sales", "replay_replay_text": "revenue figures were strong",
            "replay_accepted": True, "replay_reject_reason": None,
            "replay_localized_words": ["revenue", "figures", "were", "strong"],
        },
    ]

    run_id, attempt_id = "SAEA-TEST-P2-r1verify", "attempt-0001-aaaaaa"
    run_dir = _write_fake_arm_run(
        synthetic_world.data_root, run_id, attempt_id,
        carrier_lock_key="earnings21-original", samples=samples, replay_windows=windows,
    )
    lock = load_lock(synthetic_world.lock_path)

    arm_read = p2.read_arm("r1verify", run_dir, lock, synthetic_world.data_root)

    # F8: read_arm's own extraction path is always "completed-attempt".
    assert arm_read.source == "completed-attempt"

    # per-call metrics + legitimate-empty flag
    by_sample = {c.sample_id: c for c in arm_read.calls}
    assert by_sample["4000001"].macro_wer == pytest.approx(0.0)
    assert by_sample["4000002"].macro_wer == pytest.approx(0.0)
    assert arm_read.legitimate_empty_sample_ids == ("4000002",)

    # HER: two accepted splices (window iterations 0 and 2 -- iteration 1
    # was REJECTED, not a unit per mirror section 3). Window 0 is harmful on
    # macro (span "grew" -> 4 errors against the full reference; post-splice
    # "grew extra hallucinated words" -> 5 errors, verified via the real
    # frozen align()/tokens_v1() functions directly, not hand-computed).
    # Window 2 is NOT harmful (pass1 "sales" -> 5 errors, post-splice
    # "revenue figures were strong" -> 5 errors, equal -- "equality is not
    # harm"). Neither window is harmful on entity (the sole PERSON mention
    # "bistricer" is absent from every span variant on both sides).
    assert arm_read.her["macro"].accepted_splices == 2
    assert arm_read.her["macro"].harmful_splices == 1
    assert arm_read.her["macro"].rate.status == "descriptive_only"  # denom 2 < 10
    assert arm_read.her["entity"].harmful_splices == 0

    # RIR: the "Bistricer" candidate is wrong-in-pass1 ("bistricher" !=
    # "bistricer"), delivered, and correct in the final hypothesis.
    assert arm_read.rir.denominator >= 1
    assert arm_read.rir.numerator >= 1

    # copy count: one window copies its delivered candidate verbatim.
    assert arm_read.copy_count.called_windows == 3
    assert arm_read.copy_count.windows_with_copy == 1


def test_read_arm_refuses_when_no_completed_attempt_exists(tmp_path, synthetic_world):
    with pytest.raises(p2.P2ReadsError):
        p2.read_arm("r1verify", tmp_path / "runs" / "never-existed", load_lock(synthetic_world.lock_path), synthetic_world.data_root)


def test_build_p2_report_refuses_an_incomplete_arm_set(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(p2.P2ReadsError, match="missing arm"):
        p2.build_p2_report({"r0bias": Path("/nonexistent")}, lock, synthetic_world.data_root)


# ---------------------------------------------------------------------------
# build_p2_report / report_to_json / render_report / main(): the full
# five-arm orchestration and CLI wiring, on tiny synthetic arms (no replay
# windows -- HER/RIR/copy-count are legitimately all-zero/degenerate here;
# the metric ARITHMETIC is already covered above, this proves the PLUMBING).
# ---------------------------------------------------------------------------


def _write_minimal_arm(synthetic_world, run_id, texts):
    return _write_fake_arm_run(
        synthetic_world.data_root, run_id, "attempt-0001-aaaaaa",
        carrier_lock_key="earnings21-original", samples=list(texts.items()), replay_windows=[],
    )


@pytest.fixture()
def five_arm_run_dirs(synthetic_world):
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags|wer_tags\nhello||[]\nworld||[]\n", encoding="utf-8")
    (synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json").write_text("{}", encoding="utf-8")

    run_dirs = {}
    for arm in p2.ARM_NAMES:
        run_dirs[arm] = _write_minimal_arm(
            synthetic_world, f"SAEA-TEST-P2-{arm}", {"4000001": "hello world"}
        )
    return run_dirs


def test_build_p2_report_full_five_arm_orchestration(synthetic_world, five_arm_run_dirs):
    lock = load_lock(synthetic_world.lock_path)
    report = p2.build_p2_report(five_arm_run_dirs, lock, synthetic_world.data_root)
    assert set(report["reads"]) == set(p2.ARM_NAMES)
    assert set(report["contrasts"]) == {name for name, _, _ in p2.CONTRASTS}
    for name in report["contrasts"]:
        assert set(report["contrasts"][name]) == set(p2.LEDGERS)
    verdict = report["branch_verdict"]
    assert verdict.overall  # a verdict string was produced, never blank

    document = p2.report_to_json(report)
    assert document["schema"] == p2.REPORT_SCHEMA
    assert set(document["arms"]) == set(p2.ARM_NAMES)
    assert document["per_term_flip_lists"]["available"] is False
    assert document["format_normalized_secondary"]["available"] is False
    # JSON-serializable end to end (no dataclasses/non-primitive leftovers).
    json.dumps(document)

    rendered = p2.render_report(report)
    assert "HER (mirror section 3)" in rendered
    assert "RIR (mirror section 4)" in rendered
    assert p2.BRANCH_RULES_TEXT in rendered


def test_main_writes_a_verdict_and_never_touches_the_attempt_dirs(
    tmp_path, monkeypatch, synthetic_world, five_arm_run_dirs
):
    import speech_aware_evidence_acquisition.data.lock as lock_module
    from speech_aware_evidence_acquisition.analysis import p2_reads as p2_module

    monkeypatch.setattr(lock_module, "data_root", lambda: synthetic_world.data_root)
    monkeypatch.setattr(lock_module, "umbrella_lock_path", lambda repo_root=None: synthetic_world.lock_path)

    runs_root = synthetic_world.data_root / "runs"
    entries_before = sorted(p.relative_to(synthetic_world.data_root) for p in runs_root.rglob("*"))

    output_path = tmp_path / "p2-reads-report.json"
    argv = ["--output", str(output_path)]
    for arm in p2.ARM_NAMES:
        argv.extend([f"--{arm}-run-dir", str(five_arm_run_dirs[arm])])

    exit_code = p2_module.main(argv)
    assert exit_code == 0
    assert output_path.is_file()
    document = json.loads(output_path.read_text(encoding="utf-8"))
    assert document["schema"] == p2.REPORT_SCHEMA

    entries_after = sorted(p.relative_to(synthetic_world.data_root) for p in runs_root.rglob("*"))
    assert entries_after == entries_before


def test_main_refuses_a_missing_arm_run_dir(tmp_path, monkeypatch, synthetic_world, five_arm_run_dirs, capsys):
    import speech_aware_evidence_acquisition.data.lock as lock_module
    from speech_aware_evidence_acquisition.analysis import p2_reads as p2_module

    monkeypatch.setattr(lock_module, "data_root", lambda: synthetic_world.data_root)
    monkeypatch.setattr(lock_module, "umbrella_lock_path", lambda repo_root=None: synthetic_world.lock_path)

    output_path = tmp_path / "p2-reads-report.json"
    argv = ["--output", str(output_path)]
    for arm in p2.ARM_NAMES:
        run_dir = five_arm_run_dirs[arm] if arm != "r1wrong" else tmp_path / "runs" / "never-existed"
        argv.extend([f"--{arm}-run-dir", str(run_dir)])

    exit_code = p2_module.main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert not output_path.exists()


# ---------------------------------------------------------------------------
# F1 -- the salvage input path: read_arm_from_salvage() against miniature,
# hand-authored salvage-shaped fixtures, plus (per the task brief, an
# explicitly-allowed exception -- see the module docstring) a smoke test
# against the PRESERVED r0bias salvage archive bytes. Never opens
# $SPEECHRL_DATA_DIR/runs/SAEA-P2-* anywhere in this section.
# ---------------------------------------------------------------------------


def _write_salvage_fixture(salvage_dir, arm, *, asr, entity, copycount_rows):
    salvage_dir.mkdir(parents=True, exist_ok=True)
    (salvage_dir / f"{arm}.asr-wer.json").write_text(json.dumps(asr), encoding="utf-8")
    (salvage_dir / f"{arm}.entity-wer.json").write_text(json.dumps(entity), encoding="utf-8")
    (salvage_dir / f"{arm}.copycount.json").write_text(json.dumps(copycount_rows), encoding="utf-8")


def test_read_arm_from_salvage_on_a_miniature_fixture(tmp_path, synthetic_world):
    # Only sample 4000001 carries an ACCEPTED splice row, so only it needs a
    # real reference layer for _score_span_errors to score against.
    nlp = synthetic_world.e21 / "transcripts" / "nlp_references" / "4000001.nlp"
    nlp.write_text("token|tags|wer_tags\nrevenue||[]\ngrew||[]\nfast||[]\n", encoding="utf-8")
    (synthetic_world.e21 / "transcripts" / "wer_tags" / "4000001.wer_tag.json").write_text("{}", encoding="utf-8")

    asr = {
        "aggregate": {"mean_wer": 0.2, "samples": 3},
        "per_sample": [
            {"sample_id": "4000001", "wer": 0.1, "hits": 9, "substitutions": 1, "deletions": 0, "insertions": 0,
             "ref_hit_mask": [True] * 9 + [False]},
            {"sample_id": "4000002", "wer": 0.3, "hits": 7, "substitutions": 2, "deletions": 1, "insertions": 0,
             "ref_hit_mask": [True] * 7 + [False] * 3},
            {"sample_id": "4000003", "wer": 0.0, "hits": 5, "substitutions": 0, "deletions": 0, "insertions": 0,
             "ref_hit_mask": [True] * 5},
        ],
    }
    entity = {
        "aggregate": {"correct": 10, "expected_total": 15, "entity_wer": 0.3333},
        "per_sample": [
            {"sample_id": "4000001", "correct": 4, "expected_total": 5, "entity_wer": 0.2},
            {"sample_id": "4000002", "correct": 3, "expected_total": 5, "entity_wer": 0.4},
            {"sample_id": "4000003", "correct": 3, "expected_total": 5, "entity_wer": 0.4},
        ],
    }
    copycount_rows = [
        # 4000001: one ACCEPTED splice (win 0) + one rejected window (win 1,
        # no-copy).
        {"sample": "4000001", "win": 0, "span": 0, "ref": "revenue", "pre": "revenue figures were strong",
         "pass1": "sales", "localized": "revenue figures were strong", "accepted": True, "reason": None,
         "copies_pre": 1, "copies_pass1": 0, "novel_copy": True, "echo_pre": False, "echo_post": False,
         "guard3_pre": False},
        {"sample": "4000001", "win": 1, "span": 1, "ref": "bistricer", "pre": "bistricher", "pass1": "bistricher",
         "localized": "", "accepted": False, "reason": "low-confidence", "copies_pre": 0, "copies_pass1": 0,
         "novel_copy": False, "echo_pre": False, "echo_post": None, "guard3_pre": None},
        # 4000002: one rejected, copying window -- NOT legitimate-empty
        # (it has a row), even though it never accepted a splice.
        {"sample": "4000002", "win": 0, "span": 0, "ref": "acme", "pre": "the acme corp said", "pass1": "corp said",
         "localized": "", "accepted": False, "reason": "reference-echo", "copies_pre": 1, "copies_pass1": 0,
         "novel_copy": True, "echo_pre": True, "echo_post": False, "guard3_pre": False},
        # 4000003 has ZERO rows -> legitimate-empty (F1's literal rule).
    ]

    salvage_dir = tmp_path / "salvage"
    _write_salvage_fixture(salvage_dir, "r0bias", asr=asr, entity=entity, copycount_rows=copycount_rows)
    lock = load_lock(synthetic_world.lock_path)

    arm_read = p2.read_arm_from_salvage("r0bias", salvage_dir, lock, synthetic_world.data_root)

    assert arm_read.source == "salvage-json"  # F8
    assert arm_read.macro_aggregate == asr["aggregate"]
    assert arm_read.entity_aggregate == entity["aggregate"]

    by_sample = {c.sample_id: c for c in arm_read.calls}
    assert by_sample["4000001"].macro_wer == pytest.approx(0.1)
    assert by_sample["4000001"].entity_correct == 4
    assert by_sample["4000001"].entity_expected_total == 5
    assert by_sample["4000001"].legitimate_empty is False
    assert by_sample["4000002"].legitimate_empty is False  # has a row, just no accepted splice
    assert by_sample["4000003"].legitimate_empty is True  # zero rows
    assert arm_read.legitimate_empty_sample_ids == ("4000003",)

    # HER: exactly the one ACCEPTED row (4000001/win0) becomes a splice,
    # scored via the real _score_span_errors reuse (module docstring note 1).
    assert arm_read.her["macro"].accepted_splices == 1

    # RIR is NOT derivable from the preserved salvage outputs (F1).
    assert arm_read.rir.available is False
    assert arm_read.rir.numerator == 0 and arm_read.rir.denominator == 0
    assert arm_read.rir.unavailable_reason is not None
    assert "not derivable" in arm_read.rir.unavailable_reason

    # copy count: basis is copies_pre over CALLED rows (pre is not None) --
    # 4000001/win0 and 4000002/win0 each contribute 1 -> total 2.
    assert arm_read.copy_count.total_windows == 3
    assert arm_read.copy_count.called_windows == 3
    assert arm_read.copy_count.accepted_splices == 1
    assert arm_read.copy_count.total_copy_occurrences == 2
    assert arm_read.copy_count.windows_with_copy == 2


def test_read_arm_from_salvage_refuses_mismatched_sample_sets(tmp_path, synthetic_world):
    asr = {
        "aggregate": {"mean_wer": 0.0, "samples": 1},
        "per_sample": [{"sample_id": "4000001", "wer": 0.0, "hits": 1, "substitutions": 0, "deletions": 0,
                         "insertions": 0, "ref_hit_mask": [True]}],
    }
    entity = {
        "aggregate": {"correct": 0, "expected_total": 0, "entity_wer": 0.0},
        "per_sample": [{"sample_id": "4000002", "correct": 0, "expected_total": 0, "entity_wer": 0.0}],
    }
    salvage_dir = tmp_path / "salvage"
    _write_salvage_fixture(salvage_dir, "r0bias", asr=asr, entity=entity, copycount_rows=[])
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(p2.P2ReadsError):
        p2.read_arm_from_salvage("r0bias", salvage_dir, lock, synthetic_world.data_root)


def test_read_arm_from_salvage_refuses_missing_files(tmp_path, synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(p2.P2ReadsError):
        p2.read_arm_from_salvage("r0bias", tmp_path / "does-not-exist", lock, synthetic_world.data_root)


REAL_R0BIAS_SALVAGE_DIR = (
    Path(__file__).resolve().parents[2]
    / "docs" / "checks" / "speech-aware-evidence-acquisition" / "2026-08-16-p2-r0bias-salvage"
)


def test_read_arm_from_salvage_smoke_on_the_real_r0bias_archive():
    """Smoke test against the PRESERVED r0bias salvage bytes (already-spent
    one-shot read; docs/checks/.../2026-08-16-p2-r0bias-salvage/README.md).
    Explicitly allowed by the task brief: "developing F1 against those real
    schemas is encouraged". Uses the REAL umbrella lock/data root (not
    synthetic_world) because scoring the three accepted HER splices reads
    the real earnings21-original reference transcripts -- exactly the real-
    data access docs/checks/.../score_r0bias.py itself used. This NEVER
    opens $SPEECHRL_DATA_DIR/runs/SAEA-P2-*; the three preserved salvage
    JSONs are the only input."""

    from speech_aware_evidence_acquisition.data.lock import (
        AssetResolutionError, data_root, load_lock, umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    if not REAL_R0BIAS_SALVAGE_DIR.is_dir():
        pytest.skip("real r0bias salvage archive not present in this checkout")
    try:
        root = data_root()
        lock = load_lock(umbrella_lock_path(REPO_ROOT))
    except AssetResolutionError:
        pytest.skip("SPEECHRL_DATA_DIR / umbrella lock not configured in this environment")

    arm_read = p2.read_arm_from_salvage("r0bias", REAL_R0BIAS_SALVAGE_DIR, lock, root)

    assert arm_read.source == "salvage-json"
    assert arm_read.her["macro"].accepted_splices == 3
    assert arm_read.copy_count.accepted_splices == 3
    assert arm_read.entity_aggregate["correct"] == 5462
    assert arm_read.macro_aggregate["mean_wer"] == pytest.approx(0.12762, abs=1e-4)
    assert set(arm_read.legitimate_empty_sample_ids) == {"4365024", "4365948", "4366429", "4384964"}


# ---------------------------------------------------------------------------
# F8 -- build_p2_report threads the r0bias_read salvage path through, and
# every cross-arm contrast states both sides' sources.
# ---------------------------------------------------------------------------


def test_build_p2_report_refuses_when_both_r0bias_sources_given(synthetic_world, five_arm_run_dirs, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    asr = {"aggregate": {"mean_wer": 0.0, "samples": 1},
           "per_sample": [{"sample_id": "4000001", "wer": 0.0, "hits": 2, "substitutions": 0, "deletions": 0,
                            "insertions": 0, "ref_hit_mask": [True, True]}]}
    entity = {"aggregate": {"correct": 0, "expected_total": 0, "entity_wer": 0.0},
              "per_sample": [{"sample_id": "4000001", "correct": 0, "expected_total": 0, "entity_wer": 0.0}]}
    salvage_dir = tmp_path / "salvage"
    _write_salvage_fixture(salvage_dir, "r0bias", asr=asr, entity=entity, copycount_rows=[])
    r0bias_read = p2.read_arm_from_salvage("r0bias", salvage_dir, lock, synthetic_world.data_root)

    with pytest.raises(p2.P2ReadsError, match="r0bias"):
        p2.build_p2_report(five_arm_run_dirs, lock, synthetic_world.data_root, r0bias_read=r0bias_read)


def test_build_p2_report_threads_r0bias_salvage_source_into_contrasts(synthetic_world, five_arm_run_dirs, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    asr = {"aggregate": {"mean_wer": 0.0, "samples": 1},
           "per_sample": [{"sample_id": "4000001", "wer": 0.0, "hits": 2, "substitutions": 0, "deletions": 0,
                            "insertions": 0, "ref_hit_mask": [True, True]}]}
    entity = {"aggregate": {"correct": 0, "expected_total": 0, "entity_wer": 0.0},
              "per_sample": [{"sample_id": "4000001", "correct": 0, "expected_total": 0, "entity_wer": 0.0}]}
    salvage_dir = tmp_path / "salvage"
    # Zero copycount rows for 4000001 -> legitimate-empty, matching the
    # OTHER four arms' own 4000001 (five_arm_run_dirs carries no replay
    # windows for any arm) -- required so build_wilcoxon_contrast's sample-
    # set pairing succeeds.
    _write_salvage_fixture(salvage_dir, "r0bias", asr=asr, entity=entity, copycount_rows=[])
    r0bias_read = p2.read_arm_from_salvage("r0bias", salvage_dir, lock, synthetic_world.data_root)

    run_dirs = {arm: five_arm_run_dirs[arm] for arm in p2.ARM_NAMES if arm != "r0bias"}
    report = p2.build_p2_report(run_dirs, lock, synthetic_world.data_root, r0bias_read=r0bias_read)

    assert report["reads"]["r0bias"].source == "salvage-json"
    assert report["reads"]["r1verify"].source == "completed-attempt"

    contrast = report["contrasts"]["r1verify_vs_r0bias"]["macro"]
    assert contrast.condition_source == "completed-attempt"
    assert contrast.reference_source == "salvage-json"

    document = p2.report_to_json(report)
    assert document["arms"]["r0bias"]["source"] == "salvage-json"
    contrast_json = document["contrasts"]["r1verify_vs_r0bias"]["macro"]
    assert contrast_json["condition_source"] == "completed-attempt"
    assert contrast_json["reference_source"] == "salvage-json"


# ---------------------------------------------------------------------------
# F1 CLI wiring -- --r0bias-salvage-dir is mutually exclusive with
# --r0bias-run-dir, exactly one required.
# ---------------------------------------------------------------------------


def test_main_accepts_r0bias_salvage_dir_instead_of_run_dir(
    tmp_path, monkeypatch, synthetic_world, five_arm_run_dirs
):
    import speech_aware_evidence_acquisition.data.lock as lock_module
    from speech_aware_evidence_acquisition.analysis import p2_reads as p2_module

    monkeypatch.setattr(lock_module, "data_root", lambda: synthetic_world.data_root)
    monkeypatch.setattr(lock_module, "umbrella_lock_path", lambda repo_root=None: synthetic_world.lock_path)

    asr = {"aggregate": {"mean_wer": 0.0, "samples": 1},
           "per_sample": [{"sample_id": "4000001", "wer": 0.0, "hits": 2, "substitutions": 0, "deletions": 0,
                            "insertions": 0, "ref_hit_mask": [True, True]}]}
    entity = {"aggregate": {"correct": 0, "expected_total": 0, "entity_wer": 0.0},
              "per_sample": [{"sample_id": "4000001", "correct": 0, "expected_total": 0, "entity_wer": 0.0}]}
    salvage_dir = tmp_path / "salvage"
    _write_salvage_fixture(salvage_dir, "r0bias", asr=asr, entity=entity, copycount_rows=[])

    output_path = tmp_path / "p2-reads-report.json"
    argv = ["--output", str(output_path), "--r0bias-salvage-dir", str(salvage_dir)]
    for arm in p2.ARM_NAMES:
        if arm == "r0bias":
            continue
        argv.extend([f"--{arm}-run-dir", str(five_arm_run_dirs[arm])])

    exit_code = p2_module.main(argv)
    assert exit_code == 0
    document = json.loads(output_path.read_text(encoding="utf-8"))
    assert document["arms"]["r0bias"]["source"] == "salvage-json"


def test_cli_parser_requires_exactly_one_of_r0bias_run_dir_or_salvage_dir(tmp_path, five_arm_run_dirs):
    parser = p2._cli_parser()
    base_argv = ["--output", str(tmp_path / "out.json")]
    for arm in p2.ARM_NAMES:
        if arm == "r0bias":
            continue
        base_argv.extend([f"--{arm}-run-dir", str(five_arm_run_dirs[arm])])

    # Neither r0bias source given -> argparse refuses (required group).
    with pytest.raises(SystemExit):
        parser.parse_args(base_argv)

    # Both given -> argparse refuses (mutually exclusive group).
    both_argv = base_argv + [
        "--r0bias-run-dir", str(five_arm_run_dirs["r0bias"]),
        "--r0bias-salvage-dir", str(tmp_path / "salvage"),
    ]
    with pytest.raises(SystemExit):
        parser.parse_args(both_argv)


# ---------------------------------------------------------------------------
# F7 -- build_p2_report loudly (never silently) flags a decisive-contrast
# n_effective_paired / exclusion-set mismatch.
# ---------------------------------------------------------------------------


def _contrast_with_exclusion(name, included_ids, excluded_ids):
    from speech_aware_evidence_acquisition.analysis.context_dose import wilcoxon_signed_rank_exact

    diffs = [0.0] * len(included_ids)
    per_call = tuple(
        p2.PerCallRow(sample_id=sid, condition_value=0.0, reference_value=0.0, diff=0.0,
                       macro_transitions=None, entity_correct_delta=0)
        for sid in included_ids
    )
    return p2.ContrastResult(
        name=name, condition_arm="a", reference_arm="b", ledger="macro",
        included_sample_ids=tuple(included_ids), excluded_legitimate_empty=tuple(excluded_ids),
        diffs=tuple(diffs), wilcoxon=wilcoxon_signed_rank_exact(diffs), per_call=per_call,
    )


def test_check_decisive_contrast_exclusions_flags_a_synthetic_five_sample_exclusion():
    """F7: a SYNTHETIC 5-sample exclusion (not the registered 4) trips the
    loud mismatch banner rather than being silently accepted."""

    bad_excluded = ("1111111", "2222222", "3333333", "4444444", "5555555")
    included = ("6666666", "7777777", "8888888", "9999999", "1010101")  # 5 -> n_effective=5, not 6
    contrasts = {
        "r1verify_vs_r0bias": {
            "macro": _contrast_with_exclusion("r1verify_vs_r0bias", included, bad_excluded),
        },
    }
    warnings = p2._check_decisive_contrast_exclusions(contrasts)
    assert len(warnings) == 1
    assert "r1verify_vs_r0bias" in warnings[0]
    assert "n_effective_paired=5" in warnings[0]


def test_check_decisive_contrast_exclusions_empty_when_exactly_the_registered_four():
    good_excluded = tuple(sorted(p2.EXPECTED_LEGITIMATE_EMPTY_IDS))
    included = tuple(f"s{i}" for i in range(6))
    contrasts = {
        name: {"macro": _contrast_with_exclusion(name, included, good_excluded)}
        for name in p2.DECISIVE_CONTRAST_NAMES
    }
    assert p2._check_decisive_contrast_exclusions(contrasts) == []


def test_render_report_and_json_surface_the_f7_banner_on_a_natural_mismatch(synthetic_world, five_arm_run_dirs):
    """five_arm_run_dirs' single, legitimate-empty sample naturally
    mismatches the registered n_effective_paired==6 / four-id exclusion
    set -- proving the F7 banner surfaces in BOTH the JSON and the human-
    readable text output, not just the isolated pure-function checks
    above."""

    lock = load_lock(synthetic_world.lock_path)
    report = p2.build_p2_report(five_arm_run_dirs, lock, synthetic_world.data_root)
    assert report["exclusion_warnings"]  # non-empty: a real mismatch here

    document = p2.report_to_json(report)
    assert document["exclusion_warnings"] == report["exclusion_warnings"]

    rendered = p2.render_report(report)
    assert "PROMINENT WARNING (F7)" in rendered
