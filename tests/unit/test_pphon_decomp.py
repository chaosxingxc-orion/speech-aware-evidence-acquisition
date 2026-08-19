"""``analysis.pphon_decomp``: the P-PHON failure-class decomposition
registered model-free re-read (SAEA-CHECK-pphon-decomp).

Engineering-only, zero live model contact. Exercises the pure normalization/
classification/verdict/reconciliation primitives directly with hand-authored
fixtures, mirroring ``test_a2t_loss_decomp.py``'s own testing style (pure
functions unit-tested with literal inputs; ``verify_archive_manifest``/
``reconcile`` unit-tested with ``tmp_path``). This module is NEVER pointed
at a real, already-consumed attempt directory; that is a separately gated,
one-shot execution mission.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pphon_decomp import (
    EQUIV_FORMAT,
    FAR_WRONG,
    FORMAT_DOMINANT,
    MISSING,
    MIXED,
    NEAR_MISS,
    SPEECH_SNAP_PRESENT,
    ArmClassTable,
    ClassCounts,
    PphonDecompError,
    _align_failed_slots,
    _exact_match_indices,
    _sha256_file,
    build_a2t_baseline,
    build_a2t_conversion,
    build_class_table,
    build_slurp_baseline,
    build_slurp_conversion,
    classify_failure,
    compute_em_flips,
    evaluate_concordance,
    evaluate_pphon_verdict,
    normalize_value,
    normalized_levenshtein,
    reconcile,
    verify_archive_manifest,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


def _write_manifest_for_dir(dir_path: Path) -> None:
    entries = []
    for path in sorted(Path(dir_path).rglob("*")):
        if path.is_file() and path.name != "MANIFEST.sha256":
            rel = path.relative_to(dir_path).as_posix()
            entries.append(f"{_sha256_file(path)} *./{rel}")
    (Path(dir_path) / "MANIFEST.sha256").write_text("\n".join(entries) + "\n", encoding="utf-8")


@dataclass
class _Gold:
    entities: tuple


def _slu_response(entities: list[dict]) -> str:
    return json.dumps({"scenario": "x", "action": "y", "entities": entities})


def _class_table(carrier: str, arm: str, counts: dict[str, tuple[int, int]]) -> ArmClassTable:
    from speech_aware_evidence_acquisition.analysis.pphon_decomp import FAILURE_CLASSES

    classes = {klass: ClassCounts(*counts.get(klass, (0, 0))) for klass in FAILURE_CLASSES}
    return ArmClassTable(
        carrier=carrier,
        arm=arm,
        classes=classes,
        total_baseline_failures=sum(c.baseline_failures for c in classes.values()),
        total_converted=sum(c.converted for c in classes.values()),
    )


# ===========================================================================
# normalize_value -- the pinned normalization table.
# ===========================================================================


def test_normalize_value_casefolds():
    assert normalize_value("LONDON") == "london"


def test_normalize_value_strips_punctuation():
    assert normalize_value("rock, pop!") == "rock pop"


def test_normalize_value_collapses_whitespace():
    assert normalize_value("rock   pop") == "rock pop"


def test_normalize_value_digit_to_word():
    assert normalize_value("10") == "ten"
    assert normalize_value("ten") == "ten"


def test_normalize_value_digit_and_word_forms_agree():
    assert normalize_value("10") == normalize_value("ten")


def test_normalize_value_strips_articles():
    assert normalize_value("the beatles") == "beatles"
    assert normalize_value("a coffee") == "coffee"
    assert normalize_value("an apple") == "apple"


def test_normalize_value_combines_all_pinned_rules():
    assert normalize_value("The 10 Beatles!") == normalize_value("ten beatles") == "ten beatles"


def test_normalize_value_empty_string():
    assert normalize_value("") == ""


def test_normalize_value_article_only_token_not_stripped_mid_word():
    # "than" must never be mangled by the bare "an"/"a" article strip (a
    # TOKEN-level strip, never a substring strip).
    assert normalize_value("than") == "than"


# ===========================================================================
# normalized_levenshtein -- banding at the 0.5 boundary.
# ===========================================================================


def test_normalized_levenshtein_zero_for_identical_strings():
    assert normalized_levenshtein("london", "london") == 0.0


def test_normalized_levenshtein_zero_for_both_empty():
    assert normalized_levenshtein("", "") == 0.0


def test_normalized_levenshtein_one_for_totally_disjoint_equal_length():
    assert normalized_levenshtein("london", "zzzzzz") == 1.0


def test_normalized_levenshtein_exact_half_boundary():
    # "abcd" vs "abzy": 2 substitutions out of 4 chars -> ratio exactly 0.5.
    assert normalized_levenshtein("abcd", "abzy") == 0.5


def test_normalized_levenshtein_just_above_half_boundary():
    # "abcd" vs "azyx": 3 substitutions out of 4 chars -> ratio 0.75.
    assert normalized_levenshtein("abcd", "azyx") == 0.75


def test_normalized_levenshtein_below_half():
    # "abcde" vs "abcdz": 1 substitution out of 5 chars -> ratio 0.2.
    assert normalized_levenshtein("abcde", "abcdz") == 0.2


# ===========================================================================
# classify_failure -- the four mechanical classes + the 0.5 boundary.
# ===========================================================================


def test_classify_failure_missing_when_nothing_emitted():
    assert classify_failure("three", None) == MISSING


def test_classify_failure_equiv_format_digit_word():
    assert classify_failure("10", "ten") == EQUIV_FORMAT


def test_classify_failure_equiv_format_case_and_punctuation():
    assert classify_failure("The Beatles!", "beatles") == EQUIV_FORMAT


def test_classify_failure_near_miss_close_misspelling():
    assert classify_failure("london", "londun") == NEAR_MISS


def test_classify_failure_near_miss_at_exact_half_boundary():
    assert classify_failure("abcd", "abzy") == NEAR_MISS


def test_classify_failure_far_wrong_just_above_half_boundary():
    assert classify_failure("abcd", "azyx") == FAR_WRONG


def test_classify_failure_far_wrong_unrelated_value():
    assert classify_failure("london", "zzzzzz") == FAR_WRONG


def test_classify_failure_missing_is_never_confused_with_empty_string():
    # A genuinely emitted, blank value classifies through the normal path,
    # never MISSING (module docstring precondition).
    assert classify_failure("london", "") != MISSING


# ===========================================================================
# build_class_table -- per-class/per-arm tables + CR(c).
# ===========================================================================


def test_build_class_table_counts_baseline_and_converted_per_class():
    outcomes = [(NEAR_MISS, True), (NEAR_MISS, False), (FAR_WRONG, False), (MISSING, True)]
    table = build_class_table("slurp", "A3", outcomes)
    assert table.classes[NEAR_MISS].baseline_failures == 2
    assert table.classes[NEAR_MISS].converted == 1
    assert table.classes[NEAR_MISS].conversion_rate == 0.5
    assert table.classes[FAR_WRONG].conversion_rate == 0.0
    assert table.classes[EQUIV_FORMAT].baseline_failures == 0
    assert table.classes[EQUIV_FORMAT].conversion_rate == 0.0  # zero-baseline guard, never a ZeroDivisionError
    assert table.total_baseline_failures == 4
    assert table.total_converted == 2
    assert table.conversion_rate_overall == 0.5


def test_build_class_table_empty_outcomes_is_all_zero():
    table = build_class_table("slurp", "A3", [])
    assert table.total_baseline_failures == 0
    assert table.total_converted == 0
    assert table.conversion_rate_overall == 0.0


# ===========================================================================
# evaluate_pphon_verdict -- SPEECH-SNAP-PRESENT / FORMAT-DOMINANT / MIXED /
# the boundary co-fire case.
# ===========================================================================


def test_evaluate_pphon_verdict_speech_snap_present():
    table = _class_table(
        "slurp", "A3", {NEAR_MISS: (10, 5), FAR_WRONG: (10, 3), EQUIV_FORMAT: (5, 1), MISSING: (5, 1)}
    )
    verdict = evaluate_pphon_verdict(table)

    assert verdict.near_miss_share == pytest.approx(0.5)
    assert verdict.near_miss_share_clause.verdict == "met"
    assert verdict.near_miss_margin_clause.verdict == "met"
    assert verdict.speech_snap_present is True
    assert verdict.format_dominant is False
    assert verdict.boundary_co_fire is False
    assert verdict.overall == SPEECH_SNAP_PRESENT


def test_evaluate_pphon_verdict_format_dominant():
    table = _class_table(
        "slurp", "A3", {EQUIV_FORMAT: (10, 7), NEAR_MISS: (10, 1), FAR_WRONG: (10, 1), MISSING: (10, 1)}
    )
    verdict = evaluate_pphon_verdict(table)

    assert verdict.equiv_format_share == pytest.approx(0.7)
    assert verdict.format_dominant_clause.verdict == "met"
    assert verdict.format_dominant is True
    assert verdict.speech_snap_present is False
    assert verdict.overall == FORMAT_DOMINANT


def test_evaluate_pphon_verdict_mixed_when_share_met_but_margin_is_not():
    table = _class_table(
        "slurp", "A3", {NEAR_MISS: (10, 2), EQUIV_FORMAT: (10, 2), FAR_WRONG: (10, 2), MISSING: (10, 2)}
    )
    verdict = evaluate_pphon_verdict(table)

    assert verdict.near_miss_share == pytest.approx(0.25)
    assert verdict.near_miss_share_clause.verdict == "met"  # exactly at the 25% floor
    assert verdict.near_miss_margin_clause.verdict == "not_met"  # CR(NEAR-MISS)==CR(FAR-WRONG), margin 0
    assert verdict.speech_snap_present is False
    assert verdict.format_dominant is False
    assert verdict.overall == MIXED


def test_evaluate_pphon_verdict_zero_conversions_is_mixed_not_a_crash():
    table = _class_table("slurp", "A3", {})
    verdict = evaluate_pphon_verdict(table)

    assert verdict.overall == MIXED
    assert verdict.speech_snap_present is False
    assert verdict.format_dominant is False


def test_evaluate_pphon_verdict_boundary_co_fire():
    """The 85% split the prereg's own arithmetic note names: >=25% NEAR-MISS
    and >=60% EQUIV-FORMAT can both fire only when conversions concentrate
    almost entirely in those two classes."""

    table = _class_table("slurp", "A3", {EQUIV_FORMAT: (100, 65), NEAR_MISS: (100, 25), FAR_WRONG: (100, 10)})
    verdict = evaluate_pphon_verdict(table)

    assert verdict.speech_snap_present is True
    assert verdict.format_dominant is True
    assert verdict.boundary_co_fire is True
    assert verdict.overall == f"{SPEECH_SNAP_PRESENT} + {FORMAT_DOMINANT} (boundary co-fire)"


# ===========================================================================
# evaluate_concordance -- A1'r vs A3.
# ===========================================================================


def test_evaluate_concordance_concordant_when_both_speech_snap_present():
    a3 = evaluate_pphon_verdict(
        _class_table("slurp", "A3", {NEAR_MISS: (10, 5), FAR_WRONG: (10, 3), EQUIV_FORMAT: (5, 1), MISSING: (5, 1)})
    )
    a1r = evaluate_pphon_verdict(
        _class_table("slurp", "A1r", {NEAR_MISS: (8, 4), FAR_WRONG: (8, 2), EQUIV_FORMAT: (4, 1), MISSING: (4, 1)})
    )
    result = evaluate_concordance(a3, a1r)
    assert result.concordant is True


def test_evaluate_concordance_discordant_when_they_diverge():
    a3 = evaluate_pphon_verdict(
        _class_table("slurp", "A3", {NEAR_MISS: (10, 5), FAR_WRONG: (10, 3), EQUIV_FORMAT: (5, 1), MISSING: (5, 1)})
    )  # SPEECH-SNAP-PRESENT
    a1r = evaluate_pphon_verdict(
        _class_table("slurp", "A1r", {EQUIV_FORMAT: (10, 7), NEAR_MISS: (10, 1), FAR_WRONG: (10, 1), MISSING: (10, 1)})
    )  # FORMAT-DOMINANT
    result = evaluate_concordance(a3, a1r)
    assert result.concordant is False


# ===========================================================================
# SLURP per-slot walk: _exact_match_indices / _align_failed_slots /
# build_slurp_baseline / build_slurp_conversion.
# ===========================================================================


def test_exact_match_indices_matches_and_tracks_original_gold_index():
    gold = (SlotEntity(type="artist_name", filler="the beatles"), SlotEntity(type="song_name", filler="hey jude"))
    predicted = (SlotEntity(type="song_name", filler="hey jude"),)
    matched, leftover = _exact_match_indices(gold, predicted)
    assert matched == frozenset({1})
    assert leftover == ()


def test_exact_match_indices_leftover_when_predicted_has_no_gold_match():
    gold = (SlotEntity(type="artist_name", filler="the beatles"),)
    predicted = (SlotEntity(type="artist_name", filler="wrong band"),)
    matched, leftover = _exact_match_indices(gold, predicted)
    assert matched == frozenset()
    assert leftover == (SlotEntity(type="artist_name", filler="wrong band"),)


def test_align_failed_slots_none_when_no_same_type_candidate():
    gold = (SlotEntity(type="artist_name", filler="the beatles"),)
    aligned = _align_failed_slots([0], gold, ())
    assert aligned == {0: None}


def test_build_slurp_baseline_classifies_all_four_classes():
    gold_by_id = {
        "s1": _Gold(entities=(SlotEntity(type="artist_name", filler="10"),)),
        "s2": _Gold(entities=(SlotEntity(type="artist_name", filler="the beatles"),)),
        "s3": _Gold(entities=(SlotEntity(type="artist_name", filler="london"),)),
        "s4": _Gold(entities=(SlotEntity(type="artist_name", filler="london"),)),
        "s5": _Gold(entities=(SlotEntity(type="artist_name", filler="london"),)),
    }
    a0_response_by_id = {
        "s1": _slu_response([{"type": "artist_name", "filler": "ten"}]),  # EQUIV-FORMAT
        "s2": _slu_response([{"type": "artist_name", "filler": "beatles"}]),  # EQUIV-FORMAT
        "s3": _slu_response([{"type": "artist_name", "filler": "londun"}]),  # NEAR-MISS
        "s4": _slu_response([]),  # MISSING
        "s5": _slu_response([{"type": "artist_name", "filler": "zzzzzz"}]),  # FAR-WRONG
    }
    baseline = build_slurp_baseline(list(gold_by_id), gold_by_id, a0_response_by_id)

    classes = {slot.sample_id: slot.failure_class for slot in baseline.failed_slots}
    assert classes["s1"] == EQUIV_FORMAT
    assert classes["s2"] == EQUIV_FORMAT
    assert classes["s3"] == NEAR_MISS
    assert classes["s4"] == MISSING
    assert classes["s5"] == FAR_WRONG
    assert baseline.total_failures == 5
    assert baseline.n_gold_entities_total == 5


def test_build_slurp_baseline_excludes_already_exact_matched_slots():
    gold_by_id = {"s1": _Gold(entities=(SlotEntity(type="artist_name", filler="beatles"),))}
    a0_response_by_id = {"s1": _slu_response([{"type": "artist_name", "filler": "beatles"}])}
    baseline = build_slurp_baseline(["s1"], gold_by_id, a0_response_by_id)
    assert baseline.total_failures == 0
    assert baseline.n_gold_entities_total == 1


def test_build_slurp_conversion_marks_converted_and_counts_regressions():
    gold_by_id = {
        "s1": _Gold(
            entities=(
                SlotEntity(type="artist_name", filler="beatles"),
                SlotEntity(type="song_name", filler="hey jude"),
            )
        )
    }
    a0_response_by_id = {
        "s1": _slu_response(
            [
                {"type": "artist_name", "filler": "beatles"},  # exact under A0
                {"type": "song_name", "filler": "hey jud"},  # near-miss under A0
            ]
        )
    }
    baseline = build_slurp_baseline(["s1"], gold_by_id, a0_response_by_id)
    assert baseline.total_failures == 1
    assert baseline.failed_slots[0].failure_class == NEAR_MISS

    arm_response_by_id = {
        "s1": _slu_response(
            [
                {"type": "song_name", "filler": "hey jude"},  # converted
                # artist_name dropped entirely -> a regression
            ]
        )
    }
    result = build_slurp_conversion("A3", baseline, arm_response_by_id)
    assert result.table.classes[NEAR_MISS].converted == 1
    assert result.table.total_converted == 1
    assert result.regressions == 1


def test_build_slurp_conversion_not_converted_when_still_wrong():
    gold_by_id = {"s1": _Gold(entities=(SlotEntity(type="artist_name", filler="beatles"),))}
    a0_response_by_id = {"s1": _slu_response([{"type": "artist_name", "filler": "zzzzzz"}])}
    baseline = build_slurp_baseline(["s1"], gold_by_id, a0_response_by_id)
    assert baseline.failed_slots[0].failure_class == FAR_WRONG

    arm_response_by_id = {"s1": _slu_response([{"type": "artist_name", "filler": "still wrong"}])}
    result = build_slurp_conversion("A3", baseline, arm_response_by_id)
    assert result.table.total_converted == 0
    assert result.regressions == 0


# ===========================================================================
# A2T per-argument walk: build_a2t_baseline / build_a2t_conversion /
# compute_em_flips.
# ===========================================================================


def test_build_a2t_baseline_classifies_and_excludes_non_string_and_correct_args():
    gold_calls = {
        "s1": (ToolCall(name="setTemp", arguments={"zone": "10", "mode": 2}),),
        "s2": (ToolCall(name="setTemp", arguments={"zone": "living room"}),),
        "s3": (ToolCall(name="setTemp", arguments={"zone": "kitchen"}),),
    }
    a0_calls = {
        "s1": (ToolCall(name="setTemp", arguments={"zone": "ten", "mode": 2}),),  # zone EQUIV-FORMAT
        "s2": (ToolCall(name="setTemp", arguments={}),),  # zone MISSING
        "s3": (ToolCall(name="setTemp", arguments={"zone": "kitchen"}),),  # already correct -- excluded
    }
    baseline = build_a2t_baseline(["s1", "s2", "s3"], gold_calls, a0_calls)
    by_key = {(arg.sample_id, arg.key): arg.failure_class for arg in baseline.failed_arguments}

    assert by_key[("s1", "zone")] == EQUIV_FORMAT
    assert by_key[("s2", "zone")] == MISSING
    assert ("s1", "mode") not in by_key  # non-string gold value excluded (module docstring note 5)
    assert ("s3", "zone") not in by_key  # already correct under A0 -- not a baseline failure
    assert baseline.total_failures == 2


def test_build_a2t_conversion_marks_converted_via_canonical_bare_key_match():
    gold_calls = {"s1": (ToolCall(name="setTemp", arguments={"zone": "10"}),)}
    a0_calls = {"s1": (ToolCall(name="setTemp", arguments={"zone": "ten"}),)}
    baseline = build_a2t_baseline(["s1"], gold_calls, a0_calls)

    converted_calls = {"s1": (ToolCall(name="setTemp", arguments={"zone": "10"}),)}
    table = build_a2t_conversion("B1", baseline, converted_calls)
    assert table.classes[EQUIV_FORMAT].converted == 1
    assert table.total_converted == 1

    not_converted_calls = {"s1": (ToolCall(name="setTemp", arguments={"zone": "paris"}),)}
    table2 = build_a2t_conversion("B1", baseline, not_converted_calls)
    assert table2.classes[EQUIV_FORMAT].converted == 0
    assert table2.total_converted == 0


def test_compute_em_flips_counts_only_a0_wrong_arm_right():
    gold = {"s1": (ToolCall(name="t", arguments={"x": "1"}),), "s2": (ToolCall(name="t", arguments={"x": "2"}),)}
    a0 = {
        "s1": (ToolCall(name="t", arguments={"x": "1"}),),  # already EM=1 under A0 -- never a flip
        "s2": (ToolCall(name="t", arguments={"x": "wrong"}),),  # EM=0 under A0
    }
    arm_flips = {
        "s1": (ToolCall(name="t", arguments={"x": "1"}),),
        "s2": (ToolCall(name="t", arguments={"x": "2"}),),  # now correct
    }
    assert compute_em_flips(["s1", "s2"], gold, a0, arm_flips) == 1

    arm_no_flip = {
        "s1": (ToolCall(name="t", arguments={"x": "1"}),),
        "s2": (ToolCall(name="t", arguments={"x": "still wrong"}),),
    }
    assert compute_em_flips(["s1", "s2"], gold, a0, arm_no_flip) == 0


# ===========================================================================
# verify_archive_manifest -- MANIFEST-tamper refusal fixtures.
# ===========================================================================


def test_verify_archive_manifest_passes_for_a_consistent_archive(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("alpha", encoding="utf-8")
    (archive / "b.txt").write_text("beta", encoding="utf-8")
    _write_manifest_for_dir(archive)

    verified = verify_archive_manifest(archive)
    assert verified == ("a.txt", "b.txt")


def test_verify_archive_manifest_refuses_missing_manifest(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("alpha", encoding="utf-8")

    with pytest.raises(PphonDecompError, match="missing"):
        verify_archive_manifest(archive)


def test_verify_archive_manifest_refuses_on_tampered_file(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "verdict.json").write_text('{"aggregates": {}}', encoding="utf-8")
    _write_manifest_for_dir(archive)

    (archive / "verdict.json").write_text("TAMPERED", encoding="utf-8")

    with pytest.raises(PphonDecompError, match="sha256 mismatch"):
        verify_archive_manifest(archive)


def test_verify_archive_manifest_cross_check_refuses_on_drifted_live_copy(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "headroom.json").write_text('{"sample_ids": ["a"]}', encoding="utf-8")
    _write_manifest_for_dir(archive)

    live = tmp_path / "attempt" / "headroom.json"
    live.parent.mkdir()
    live.write_text('{"sample_ids": ["TAMPERED"]}', encoding="utf-8")

    with pytest.raises(PphonDecompError, match="does not match the archived"):
        verify_archive_manifest(archive, cross_check={"headroom.json": live})


def test_verify_archive_manifest_cross_check_passes_on_byte_identical_live_copy(tmp_path):
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "headroom.json").write_text('{"sample_ids": ["a"]}', encoding="utf-8")
    _write_manifest_for_dir(archive)

    live = tmp_path / "attempt" / "headroom.json"
    live.parent.mkdir()
    live.write_text('{"sample_ids": ["a"]}', encoding="utf-8")

    verified = verify_archive_manifest(archive, cross_check={"headroom.json": live})
    assert verified == ("headroom.json",)


# ===========================================================================
# reconcile -- three-way reconciliation + the real-scale exact gate
# (reconciliation-gate refusal fixtures).
# ===========================================================================


def test_reconcile_matches_when_all_three_agree():
    row = reconcile("slurp-A3-conversions-net-of-regressions", 44, 44, 44)
    assert row.matched is True


def test_reconcile_refuses_when_archived_disagrees():
    row = reconcile("slurp-A3-conversions-net-of-regressions", 44, 44, 43)
    assert row.matched is False


def test_reconcile_refuses_when_parent_recomputed_disagrees():
    row = reconcile("slurp-A3-conversions-net-of-regressions", 44, 40, 44)
    assert row.matched is False


def test_reconcile_exact_gate_applies_and_passes_at_real_scale():
    row = reconcile("a2t-B1-em-flips", 8, 8, 8, exact_gate=(8, 120), n_samples=120)
    assert row.matched is True
    assert "exact_gate=8/120 (applies" in row.detail


def test_reconcile_exact_gate_refuses_when_count_disagrees_at_real_scale():
    """The mission's own literal requirement: at the real 120-sample scale,
    B1 must yield EXACTLY 8 EM-flips, even when the three-way count
    otherwise agrees internally at some OTHER number."""

    row = reconcile("a2t-B1-em-flips", 7, 7, 7, exact_gate=(8, 120), n_samples=120)
    assert row.computed == row.parent_recomputed == row.archived == 7
    assert row.matched is False


def test_reconcile_gate_not_applicable_at_a_smaller_synthetic_scale():
    row = reconcile("a2t-B1-em-flips", 3, 3, 3, exact_gate=(8, 120), n_samples=20)
    assert row.matched is True  # gate skipped -- n_samples=20 != the real B1 size (120)
    assert "not applicable at n_samples=20" in row.detail
