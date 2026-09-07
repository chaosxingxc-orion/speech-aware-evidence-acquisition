"""Unit tests for the Earnings-22 encoding-probe verdict, on synthetic rows.

Nothing here reads the data root, the sealed arms, a roster receipt or any real
score file: every receipt is hand-built with known totals, so the falsifier
gate, the media-cost arithmetic, the boundary contrast, the head/tail table and
the three-clause decision rule are checked against answers computed by hand
rather than against the module's own output.

The rule under test is stricter than the base's in two ways that were both fixed
before any number existed -- clause 1's ``-0.2356`` disjointness threshold and
clause 3's 2.0-point boundary drop -- and each is asserted separately, because a
verdict that silently relaxed either would still look like a verdict.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.e22_encoding_probes import (
    BOUNDARY_DROP_POINTS,
    SHORT_RECUT_SECONDS,
    WER_CI90_UPPER_MAX_POINTS,
    EncodingProbesError,
    boundary_asymmetry,
    boundary_by_call,
    boundary_by_duration,
    comparator_media_cost,
    contrast,
    falsifier_check,
    media_cost,
    short_recut_clips,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import decide

WHISPER = "asr-wer-esb-whisper"


# ---------------------------------------------------------------------------
# The section 4.1 falsifier, which runs before any score is opened
# ---------------------------------------------------------------------------


def _falsifier_receipt(tmp_path, **overrides):
    payload = {
        "verdict": "HOLDS",
        "rows_checked": 1500,
        "rows_expected": 1500,
        "rows_where_the_falsifier_holds": 1500,
        "disagreements": [],
        "measured_prompt_tokens_total": 210663,
        "predicted_prompt_tokens_total": 210663,
        "text_envelope_tokens": 49,
    }
    payload.update(overrides)
    path = tmp_path / "falsifier.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return {"falsifier_relpath": "falsifier.json"}


def test_falsifier_check_carries_a_holding_receipt_forward_with_its_hash(tmp_path):
    cell = _falsifier_receipt(tmp_path)
    block = falsifier_check(tmp_path, cell)
    assert block["verdict"] == "HOLDS"
    assert block["rows_where_the_falsifier_holds"] == 1500
    assert len(block["receipt_sha256"]) == 64


def test_falsifier_check_refuses_a_receipt_that_does_not_say_holds(tmp_path):
    cell = _falsifier_receipt(tmp_path, verdict="FALSIFIED")
    with pytest.raises(EncodingProbesError, match="section 4.1 falsifier"):
        falsifier_check(tmp_path, cell)


def test_falsifier_check_refuses_a_receipt_with_a_single_disagreeing_row(tmp_path):
    cell = _falsifier_receipt(
        tmp_path, rows_where_the_falsifier_holds=1499, disagreements=["4453225-103@bx1"]
    )
    with pytest.raises(EncodingProbesError):
        falsifier_check(tmp_path, cell)


def test_falsifier_check_refuses_a_prompt_token_total_that_does_not_match(tmp_path):
    cell = _falsifier_receipt(tmp_path, measured_prompt_tokens_total=210664)
    with pytest.raises(EncodingProbesError):
        falsifier_check(tmp_path, cell)


# ---------------------------------------------------------------------------
# Media cost
# ---------------------------------------------------------------------------


def _media_roster(tmp_path, items, **extra):
    payload = {"items": items, "count": len(items)}
    payload.update(extra)
    (tmp_path / "roster.json").write_text(json.dumps(payload), encoding="utf-8")
    return "roster.json"


def test_media_cost_sums_seconds_tokens_and_zero_pad_frames(tmp_path):
    relpath = _media_roster(
        tmp_path,
        [
            {
                "sample_id": "c-1@ts2",
                "audio_seconds": 2.5,
                "audio_tokens": 39,
                "zero_pad_frames": 99,
                "source_audio_seconds": 0.5,
                "samples_removed": 0,
            },
            {
                "sample_id": "c-2@ts2",
                "audio_seconds": 4.0,
                "audio_tokens": 52,
                "zero_pad_frames": 0,
                "source_audio_seconds": 2.0,
                "samples_removed": 0,
            },
        ],
        audio_seconds_longest_item=4.0,
        audio_seconds_shortest_item=2.5,
    )
    block = media_cost(tmp_path, relpath)
    assert block["rows"] == 2
    assert block["audio_seconds_total"] == pytest.approx(6.5)
    assert block["audio_tokens_total"] == 91
    assert block["zero_pad_frames_total"] == 99
    assert block["zero_pad_seconds_total"] == pytest.approx(0.99)
    assert block["rows_carrying_a_zero_pad_block"] == 1
    assert len(block["receipt_sha256"]) == 64


def test_comparator_media_cost_reads_the_committed_audit_population(tmp_path):
    directory = tmp_path / "docs/checks/speech-aware-evidence-acquisition"
    directory /= "2026-09-07-e22-short-clip-encoding-audit"
    directory.mkdir(parents=True)
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "populations": {
                    "E22-ESB-DEV1500-UTTERANCES": {
                        "clips": 1500,
                        "audio_seconds_total": 9948.983,
                        "llamacpp_audio_tokens_total": 139282,
                        "hf_audio_tokens_total": 129542,
                        "extra_audio_tokens_total": 9740,
                        "zero_pad_frames_total": 75330,
                        "zero_pad_seconds_total": 753.3,
                        "clips_with_zero_pad": 1498,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    block = comparator_media_cost(tmp_path)
    assert block["audio_tokens_total"] == 139282
    assert block["padding_derived_audio_tokens_total"] == 9740
    assert block["rows_carrying_a_zero_pad_block"] == 1498


def test_short_recut_clips_names_every_clip_under_the_threshold(tmp_path):
    relpath = _media_roster(
        tmp_path,
        [
            {
                "sample_id": "c-1@bx1",
                "audio_seconds": 0.12,
                "audio_tokens": 13,
                "zero_pad_frames": 87,
                "source_audio_seconds": 0.24,
                "samples_removed": 1920,
            },
            {
                "sample_id": "c-2@bx1",
                "audio_seconds": 0.30,
                "audio_tokens": 13,
                "zero_pad_frames": 69,
                "source_audio_seconds": 0.40,
                "samples_removed": 1600,
            },
            {
                "sample_id": "c-3@bx1",
                "audio_seconds": 5.0,
                "audio_tokens": 65,
                "zero_pad_frames": 1,
                "source_audio_seconds": 5.0,
                "samples_removed": 0,
            },
        ],
    )
    block = short_recut_clips(tmp_path, relpath)
    assert block["threshold_seconds"] == SHORT_RECUT_SECONDS
    assert [row["sample_id"] for row in block["clips_under_threshold"]] == ["c-1@bx1"]
    assert block["clips_that_lose_audio"] == 2
    assert block["max_seconds_removed"] == pytest.approx(0.12)
    assert block["mean_seconds_removed"] == pytest.approx(0.11)


# ---------------------------------------------------------------------------
# The boundary block
# ---------------------------------------------------------------------------


def _arm(rows, call_of, *, charge, boundary, head, tail):
    return {
        "scores": {WHISPER: rows},
        "charge": charge,
        "boundary": boundary,
        "reference_words_of": {sid: 10 for sid in call_of},
        "category_mass": {
            "boundary": {
                "runaway_head_mass": head["mass"],
                "runaway_tail_mass": tail["mass"],
                "segmentation_artifact_mass": 100,
                "total_error_mass": head["mass"] + tail["mass"] + 100,
                "wer_points": 1.23,
                "containment": {
                    "head": {
                        "insertion_spans": head["spans"],
                        "inserted_words": head["words"],
                        "spans_by_containment": {"contains_0.6_or_more": head["contained"]},
                    },
                    "tail": {
                        "insertion_spans": tail["spans"],
                        "inserted_words": tail["words"],
                        "spans_by_containment": {"contains_0.6_or_more": tail["contained"]},
                    },
                },
            }
        },
    }


def _row(hits: int, sub: int, dele: int, ins: int) -> dict[str, float]:
    reference = hits + sub + dele
    return {
        "hits": float(hits),
        "substitutions": float(sub),
        "deletions": float(dele),
        "insertions": float(ins),
        "wer": (sub + dele + ins) / reference,
    }


@pytest.fixture()
def population():
    sample_ids = tuple(f"{call}-{index}" for call in ("c1", "c2") for index in range(4))
    call_of = {sid: sid.split("-")[0] for sid in sample_ids}
    arms = {
        "A": _arm(
            {sid: _row(9, 1, 0, 2) for sid in sample_ids},
            call_of,
            charge={sid: 1 for sid in sample_ids},
            boundary={sid: 2 for sid in sample_ids},
            head={"mass": 70, "spans": 149, "words": 266, "contained": 73},
            tail={"mass": 1179, "spans": 704, "words": 1950, "contained": 218},
        ),
        "CELL": _arm(
            {sid: _row(9, 1, 0, 1) for sid in sample_ids},
            call_of,
            charge={sid: 0 for sid in sample_ids},
            boundary={sid: 1 for sid in sample_ids},
            head={"mass": 41, "spans": 135, "words": 227, "contained": 68},
            tail={"mass": 22, "spans": 39, "words": 75, "contained": 20},
        ),
    }
    return {"sample_ids": sample_ids, "call_of": call_of, "arms": arms}


def test_boundary_asymmetry_reports_both_ends_separately(population):
    table = {row["arm"]: row for row in boundary_asymmetry(population["arms"])}
    assert table["A"]["tail_insertion_spans"] == 704
    assert table["CELL"]["tail_insertion_spans"] == 39
    # The point of the table: the head barely moves while the tail collapses.
    assert table["A"]["head_insertion_spans"] - table["CELL"]["head_insertion_spans"] == 14
    assert table["A"]["tail_insertion_spans"] - table["CELL"]["tail_insertion_spans"] == 665


def test_boundary_by_call_pools_the_charge_and_signs_the_delta(population):
    table = boundary_by_call(
        population["arms"], population["sample_ids"], population["call_of"]
    )
    assert [row["group"] for row in table] == ["c1", "c2"]
    for row in table:
        # 4 rows x 10 reference words = 40; arm A charges 8, the cell 4.
        assert row["A_wer_points"] == pytest.approx(20.0)
        assert row["CELL_wer_points"] == pytest.approx(10.0)
        assert row["CELL_delta"] == pytest.approx(-10.0)


def test_boundary_by_duration_skips_empty_buckets(population):
    seconds = {sid: 0.5 for sid in population["sample_ids"]}
    table = boundary_by_duration(population["arms"], population["sample_ids"], seconds)
    assert len(table) == 1
    assert table[0]["group"] == "[0, 1)"
    assert table[0]["rows"] == 8
    assert table[0]["CELL_delta"] == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# The contrast
# ---------------------------------------------------------------------------


def test_contrast_is_signed_right_minus_left_on_every_estimand(population):
    block = contrast(
        population["arms"],
        population["sample_ids"],
        population["call_of"],
        left="A",
        right="CELL",
    )
    # errors 24 -> 16 over 80 reference words; charge 8 -> 0; boundary 16 -> 8.
    assert block["corpus_wer_delta_points"]["stratified"]["point_estimate"] == pytest.approx(
        -10.0, abs=1e-9
    )
    assert block["agentic_delta_points"]["stratified"]["point_estimate"] == pytest.approx(
        -10.0, abs=1e-9
    )
    assert block["boundary_delta_points"]["stratified"]["point_estimate"] == pytest.approx(
        -10.0, abs=1e-9
    )
    assert block["per_row_wer"]["saves"] == 8
    assert block["per_row_wer"]["harms"] == 0
    assert "CELL minus A" in block["signed_as"]


def test_contrast_can_omit_an_estimand_for_a_pairwise_read(population):
    block = contrast(
        population["arms"],
        population["sample_ids"],
        population["call_of"],
        left="A",
        right="CELL",
        estimands=("wer", "boundary"),
    )
    assert "agentic_delta_points" not in block
    assert "boundary_delta_points" in block


# ---------------------------------------------------------------------------
# The three-clause rule, at the thresholds this preregistration fixed
# ---------------------------------------------------------------------------


def _stat(point: float, low: float, high: float) -> dict[str, object]:
    return {"stratified": {"point_estimate": point, "ci_low": low, "ci_high": high}}


def _verdict(wer, agentic, boundary):
    return decide(
        wer,
        agentic,
        wer_ci_upper_max=WER_CI90_UPPER_MAX_POINTS,
        boundary=boundary,
        boundary_drop_points=BOUNDARY_DROP_POINTS,
    )


def test_all_three_clauses_hold_admits():
    verdict = _verdict(
        _stat(-8.0, -8.9, -7.1), _stat(-0.16, -0.31, -0.02), _stat(-7.17, -7.9, -6.4)
    )
    assert verdict["admitted"] is True
    assert verdict["clause_3_boundary_block_falls_by_at_least_points"] is True


def test_a_wer_gain_inside_the_same_request_null_is_refused():
    """A cell whose interval overlaps the measured null fails clause 1."""

    just_inside = WER_CI90_UPPER_MAX_POINTS + 0.0001
    verdict = _verdict(
        _stat(-0.30, -0.42, just_inside), _stat(-0.01, -0.05, 0.01), _stat(-3.0, -3.4, -2.6)
    )
    assert verdict["clause_1_corpus_wer_improves_with_ci90_upper_below_zero"] is False
    assert verdict["admitted"] is False
    assert verdict["clause_1_ci90_upper_threshold"] == WER_CI90_UPPER_MAX_POINTS


def test_a_boundary_drop_short_of_two_points_is_a_corpus_wer_effect_without_a_mechanism():
    verdict = _verdict(
        _stat(-1.5, -1.9, -1.1), _stat(-0.01, -0.05, 0.01), _stat(-1.99, -2.4, -1.5)
    )
    assert verdict["clause_1_corpus_wer_improves_with_ci90_upper_below_zero"] is True
    assert verdict["clause_2_agentic_ci90_upper_below_margin"] is True
    assert verdict["clause_3_boundary_block_falls_by_at_least_points"] is False
    assert verdict["admitted"] is False


def test_an_agentic_upper_bound_above_the_margin_is_refused_even_with_a_huge_boundary_drop():
    verdict = _verdict(
        _stat(-8.0, -8.9, -7.1), _stat(0.02, -0.05, 0.0501), _stat(-7.17, -7.9, -6.4)
    )
    assert verdict["clause_2_agentic_ci90_upper_below_margin"] is False
    assert verdict["admitted"] is False


def test_the_rule_string_names_both_fixed_thresholds():
    verdict = _verdict(
        _stat(-8.0, -8.9, -7.1), _stat(-0.16, -0.31, -0.02), _stat(-7.17, -7.9, -6.4)
    )
    assert "-0.2356" in verdict["rule"]
    assert "2 WER" in verdict["rule"]
