"""Unit tests for the Earnings-22 model-usage cells verdict, on synthetic rows.

Nothing here reads the data root, the sealed arms, the roster receipt or any
real score file: every row is hand-built with a known error count, a known call
stratum and a known HIGH-impact charge, so the pooled arithmetic, the identity
gate and the preregistered decision rule are checked against answers computed by
hand rather than against the module's own output. If the module can be wrong
about a population it was handed, the receipts it writes over the real one
cannot be trusted either.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import ErrorSpan, ScoredSpan
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (
    AGENTIC_MARGIN_POINTS,
    UsageCellsError,
    boundary_charge,
    decide,
    duration_table,
    high_impact_charge,
    identity_gate,
    load_roster,
    load_score_rows,
    per_call_csv,
    per_call_table,
    pooled_delta,
    weightings,
    write_check_manifest,
)

WHISPER = "asr-wer-esb-whisper"
FROZEN = "asr-wer-esb"


# ---------------------------------------------------------------------------
# Fixtures: two calls, four rows each, with hand-computed totals.
# ---------------------------------------------------------------------------


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
def population() -> dict[str, object]:
    """Eight rows over two calls; arm A carries one extra insertion on four."""

    sample_ids = tuple(f"{call}-{index}" for call in ("c1", "c2") for index in range(4))
    call_of = {sample_id: sample_id.split("-")[0] for sample_id in sample_ids}
    base = {sid: _row(9, 1, 0, 2) for sid in sample_ids}
    cell = {sid: _row(9, 1, 0, 1) for sid in sample_ids}
    arms = {
        "A": {
            "scores": {WHISPER: dict(base), FROZEN: dict(base)},
            "charge": {sid: 1 for sid in sample_ids},
            "reference_words_of": {sid: 10 for sid in sample_ids},
        },
        "CELL": {
            "scores": {WHISPER: dict(cell), FROZEN: dict(cell)},
            "charge": {sid: 0 for sid in sample_ids},
            "reference_words_of": {sid: 10 for sid in sample_ids},
        },
    }
    return {"sample_ids": sample_ids, "call_of": call_of, "arms": arms}


def _numerator(arms):
    def inner(arm: str, sample_id: str) -> float:
        row = arms[arm]["scores"][WHISPER][sample_id]
        return row["substitutions"] + row["deletions"] + row["insertions"]

    return inner


def _denominator(arms):
    def inner(arm: str, sample_id: str) -> float:
        row = arms[arm]["scores"][WHISPER][sample_id]
        return row["hits"] + row["substitutions"] + row["deletions"]

    return inner


# ---------------------------------------------------------------------------
# The identity gate
# ---------------------------------------------------------------------------


def test_identity_gate_passes_when_every_pair_reproduces():
    measured = {"A": {"wer": 17.40123}, "Q8": {"wer": 16.97079}}
    gate = identity_gate(measured, {"A": {"wer": 17.4012}, "Q8": {"wer": 16.9708}})
    assert gate["reproduced"] is True
    assert [row["arm"] for row in gate["pairs"]] == ["A", "Q8"]


def test_identity_gate_refuses_a_single_drifted_digit():
    measured = {"A": {"wer": 17.4013}, "Q8": {"wer": 16.9708}}
    with pytest.raises(UsageCellsError, match="identity gate FAILED"):
        identity_gate(measured, {"A": {"wer": 17.4012}, "Q8": {"wer": 16.9708}})


def test_identity_gate_names_every_failing_pair_not_just_the_first():
    measured = {"A": {"wer": 1.0, "agentic": 2.0}}
    with pytest.raises(UsageCellsError) as error:
        identity_gate(measured, {"A": {"wer": 9.0, "agentic": 8.0}})
    assert "wer" in str(error.value) and "agentic" in str(error.value)


# ---------------------------------------------------------------------------
# The pooled contrast
# ---------------------------------------------------------------------------


def test_pooled_delta_is_the_ratio_difference_not_the_mean_of_row_deltas(population):
    arms = population["arms"]
    block = pooled_delta(
        population["sample_ids"],
        _numerator(arms),
        _denominator(arms),
        left="A",
        right="CELL",
        call_of=population["call_of"],
    )
    # 8 rows x 10 reference words = 80; arm A has 8x3 = 24 errors, the cell 8x2 = 16.
    expected = 100.0 * (16 / 80 - 24 / 80)
    assert block["stratified"]["point_estimate"] == pytest.approx(expected, abs=1e-9)
    assert block["clustered"]["point_estimate"] == pytest.approx(expected, abs=1e-9)


def test_pooled_delta_records_the_preregistered_draw_on_both_intervals(population):
    arms = population["arms"]
    block = pooled_delta(
        population["sample_ids"],
        _numerator(arms),
        _denominator(arms),
        left="A",
        right="CELL",
        call_of=population["call_of"],
    )
    for label in ("stratified", "clustered"):
        assert block[label]["seed"] == 20260903
        assert block[label]["n_replicates"] == 10_000
        assert block[label]["ci_level"] == 0.90
        assert block[label]["ci_low"] <= block[label]["point_estimate"] <= block[label]["ci_high"]


def test_pooled_delta_stratified_and_clustered_are_different_draws():
    """A one-call-only effect must widen under the call-clustered resample."""

    sample_ids = tuple(f"{call}-{index}" for call in ("c1", "c2") for index in range(20))
    call_of = {sid: sid.split("-")[0] for sid in sample_ids}
    arms = {
        "A": {"scores": {WHISPER: {sid: _row(9, 1, 0, 2) for sid in sample_ids}}},
        "CELL": {
            "scores": {
                WHISPER: {
                    sid: (_row(9, 1, 0, 0) if call_of[sid] == "c1" else _row(9, 1, 0, 2))
                    for sid in sample_ids
                }
            }
        },
    }
    block = pooled_delta(
        sample_ids,
        _numerator(arms),
        _denominator(arms),
        left="A",
        right="CELL",
        call_of=call_of,
    )
    stratified = block["stratified"]["ci_high"] - block["stratified"]["ci_low"]
    clustered = block["clustered"]["ci_high"] - block["clustered"]["ci_low"]
    assert clustered > stratified


# ---------------------------------------------------------------------------
# The preregistered decision rule
# ---------------------------------------------------------------------------


def _stat(point: float, low: float, high: float) -> dict[str, object]:
    return {"stratified": {"point_estimate": point, "ci_low": low, "ci_high": high}}


def test_decide_admits_only_when_both_clauses_hold():
    verdict = decide(_stat(-0.43, -0.65, -0.22), _stat(-0.06, -0.15, 0.02))
    assert verdict["admitted"] is True
    assert verdict["clause_1_corpus_wer_improves_with_ci90_upper_below_zero"] is True
    assert verdict["clause_2_agentic_ci90_upper_below_margin"] is True


def test_decide_refuses_a_wer_gain_whose_interval_touches_zero():
    verdict = decide(_stat(-0.14, -0.30, 0.015), _stat(-0.02, -0.09, 0.01))
    assert verdict["admitted"] is False
    assert verdict["clause_1_corpus_wer_improves_with_ci90_upper_below_zero"] is False


def test_decide_refuses_an_agentic_upper_bound_above_the_fixed_margin():
    just_over = AGENTIC_MARGIN_POINTS + 0.0044
    verdict = decide(_stat(-0.43, -0.65, -0.22), _stat(-0.02, -0.09, just_over))
    assert verdict["admitted"] is False
    assert verdict["clause_2_agentic_ci90_upper_below_margin"] is False
    assert verdict["clause_2_margin_points"] == 0.05


def test_decide_refuses_a_worsening_agentic_rate_even_inside_the_margin():
    """Clause 2's other half: the point estimate must not be above the comparator's."""

    verdict = decide(_stat(-0.43, -0.65, -0.22), _stat(0.01, -0.02, 0.04))
    assert verdict["clause_2_agentic_ci90_upper_below_margin"] is False
    assert verdict["clause_2_point_estimate"] == 0.01
    assert verdict["admitted"] is False


def test_decide_refuses_a_worsening_wer_even_with_a_negative_upper_bound():
    verdict = decide(_stat(0.20, -0.40, -0.01), _stat(0.0, -0.01, 0.01))
    assert verdict["admitted"] is False


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------


def test_per_call_table_carries_both_normalizers_and_every_delta(population):
    table = per_call_table(
        population["arms"], population["sample_ids"], population["call_of"]
    )
    assert [row["call"] for row in table] == ["c1", "c2"]
    for row in table:
        assert row["rows"] == 4
        assert row["A_corpus_wer_whisper"] == pytest.approx(30.0)
        assert row["A_corpus_wer_saea_v1"] == pytest.approx(30.0)
        assert row["CELL_delta_whisper"] == pytest.approx(-10.0)
        assert row["CELL_delta_agentic"] == pytest.approx(-10.0)
    assert "A_delta_whisper" not in table[0]


def test_weightings_report_natural_and_equal_call_side_by_side(population):
    table = per_call_table(
        population["arms"], population["sample_ids"], population["call_of"]
    )
    block = weightings(population["arms"], table, population["sample_ids"])
    assert block["A"]["natural_mixture_corpus_wer"] == pytest.approx(30.0)
    assert block["A"]["equal_call_corpus_wer"] == pytest.approx(30.0)
    assert block["CELL"]["natural_mixture_agentic"] == pytest.approx(0.0)


def test_duration_table_skips_empty_buckets_and_signs_the_delta(population):
    seconds = {sid: 5.0 for sid in population["sample_ids"]}
    table = duration_table(population["arms"], population["sample_ids"], seconds)
    assert len(table) == 1
    assert table[0]["bucket"] == "[4, 8)"
    assert table[0]["rows"] == 8
    assert table[0]["CELL_delta"] == pytest.approx(-10.0)


def test_per_call_csv_is_a_rectangle_with_a_header(population):
    table = per_call_table(
        population["arms"], population["sample_ids"], population["call_of"]
    )
    text = per_call_csv(table)
    lines = text.strip().split("\n")
    assert len(lines) == 3
    assert lines[0].startswith("call,rows,")
    assert all(len(line.split(",")) == len(lines[0].split(",")) for line in lines)


# ---------------------------------------------------------------------------
# The per-row HIGH-impact charge
# ---------------------------------------------------------------------------


class _Span:
    def __init__(self, charge: int) -> None:
        self.reference_word_charge = charge


class _Scored:
    def __init__(self, sample_id: str, category: str, rule: str, impact: str, charge: int):
        self.sample_id = sample_id
        self.category = category
        self.rule = rule
        self.content_impact = impact
        self.span = _Span(charge)


def test_high_impact_charge_obeys_the_same_neutrality_ruling_as_the_corpus_rate():
    scored = [
        _Scored("a", "named-entity", "named-entity/call-inventory", "HIGH", 2),
        _Scored("a", "other", "other/substituted-content-word", "HIGH", 1),
        _Scored("b", "segmentation-artifact", "segmentation-artifact/neighbour-bleed", "HIGH", 9),
        _Scored("b", "model-behaviour", "model-behaviour/hypothesis-repetition", "HIGH", 7),
        _Scored("c", "acoustic-misrecognition", "acoustic-misrecognition/string-near", "LOW", 4),
    ]
    charge = high_impact_charge(scored)
    assert charge == {"a": 3}


# ---------------------------------------------------------------------------
# Loaders, fail-closed
# ---------------------------------------------------------------------------


def _roster_receipt(tmp_path, items):
    directory = tmp_path / "docs" / "receipts" / "rosters"
    directory.mkdir(parents=True)
    (directory / "e22-dev-esb-1500-v1.json").write_text(
        json.dumps(
            {
                "items": items,
                "split_identity_hash": "c626e62f",
                "roster_id": "E22-DEV-ESB-1500-V1",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_load_roster_returns_sorted_ids_with_their_strata_and_durations(tmp_path):
    repo = _roster_receipt(
        tmp_path,
        [
            {"sample_id": "c2-1", "stratum": "c2", "audio_seconds": 3.5},
            {"sample_id": "c1-1", "stratum": "c1", "audio_seconds": 1.25},
        ],
    )
    roster = load_roster(repo)
    assert roster["sample_ids"] == ("c1-1", "c2-1")
    assert roster["call_of"]["c2-1"] == "c2"
    assert roster["seconds_of"]["c1-1"] == pytest.approx(1.25)
    assert roster["split_identity_hash"] == "c626e62f"
    assert len(roster["receipt_sha256"]) == 64


def test_load_roster_refuses_a_duplicated_id(tmp_path):
    repo = _roster_receipt(
        tmp_path,
        [
            {"sample_id": "c1-1", "stratum": "c1", "audio_seconds": 1.0},
            {"sample_id": "c1-1", "stratum": "c1", "audio_seconds": 1.0},
        ],
    )
    with pytest.raises(UsageCellsError, match="unique"):
        load_roster(repo)


def _score_file(tmp_path, rows):
    run = tmp_path / "runs" / "RUN" / "attempt"
    run.mkdir(parents=True, exist_ok=True)
    block = {"aggregate": {}, "per_sample": rows}
    (run / "RUN.scores.json").write_text(
        json.dumps({WHISPER: block, FROZEN: block}), encoding="utf-8"
    )
    return {"run_id": "RUN", "attempt": "attempt"}


def test_load_score_rows_refuses_a_missing_roster_row(tmp_path):
    source = _score_file(
        tmp_path,
        [dict(sample_id="c1-1", wer=0.1, hits=9, substitutions=1, deletions=0, insertions=0)],
    )
    assert set(load_score_rows(tmp_path, source, ["c1-1"])[WHISPER]) == {"c1-1"}
    with pytest.raises(UsageCellsError, match="missing 1 roster rows"):
        load_score_rows(tmp_path, source, ["c1-1", "c1-2"])


def test_load_score_rows_folds_a_variant_suffix_onto_the_published_segment(tmp_path):
    """Deviation D-ENC-1: a media-variant cell's rows join on the published key."""

    source = _score_file(
        tmp_path,
        [
            dict(sample_id="c1-1@ts2", wer=0.1, hits=9, substitutions=1, deletions=0, insertions=0),
            dict(sample_id="c1-2@ts2", wer=0.2, hits=8, substitutions=2, deletions=0, insertions=0),
        ],
    )
    rows = load_score_rows(tmp_path, source, ["c1-1", "c1-2"])[WHISPER]
    assert set(rows) == {"c1-1", "c1-2"}
    assert rows["c1-2"]["substitutions"] == pytest.approx(2.0)


def test_load_score_rows_refuses_two_variants_of_one_published_segment(tmp_path):
    source = _score_file(
        tmp_path,
        [
            dict(sample_id="c1-1@ts2", wer=0.1, hits=9, substitutions=1, deletions=0, insertions=0),
            dict(sample_id="c1-1@p30", wer=0.3, hits=7, substitutions=3, deletions=0, insertions=0),
        ],
    )
    with pytest.raises(UsageCellsError, match="two rows for published segment"):
        load_score_rows(tmp_path, source, ["c1-1"])


# ---------------------------------------------------------------------------
# The per-row BOUNDARY charge, clause 3's estimand
# ---------------------------------------------------------------------------


def _span(op: str, ref: tuple[str, ...], hyp: tuple[str, ...]) -> ErrorSpan:
    return ErrorSpan(
        op=op,
        ref_start=0,
        ref_end=len(ref),
        hyp_start=0,
        hyp_end=len(hyp),
        ref_tokens=ref,
        hyp_tokens=hyp,
        ref_left=(),
        ref_right=(),
        hyp_left=(),
        hyp_right=(),
    )


def _scored(sample_id: str, category: str, rule: str, span: ErrorSpan) -> ScoredSpan:
    return ScoredSpan(
        sample_id=sample_id,
        call=sample_id.split("-")[0],
        category=category,
        rule=rule,
        content_impact="LOW",
        impact="LOW",
        span=span,
    )


def test_boundary_charge_counts_the_category_and_the_two_runaway_rules_only():
    scored = [
        _scored("a", "segmentation-artifact", "segmentation-artifact/neighbour-bleed",
                _span("INS", (), ("one", "two", "three"))),
        _scored("a", "model-behaviour", "model-behaviour/runaway-tail",
                _span("INS", (), ("four", "five"))),
        _scored("b", "model-behaviour", "model-behaviour/runaway-head",
                _span("INS", (), ("six",))),
        # Neither of these belongs to the block the rule decides on.
        _scored("b", "model-behaviour", "model-behaviour/hypothesis-repetition",
                _span("INS", (), ("seven", "eight"))),
        _scored("c", "named-entity", "named-entity/call-inventory",
                _span("SUB", ("nine",), ("ten",))),
    ]
    assert boundary_charge(scored) == {"a": 5, "b": 1}


def test_boundary_charge_uses_the_taxonomys_own_span_mass_rule():
    """SUB and DEL charge reference words; INS charges hypothesis words."""

    scored = [
        _scored("a", "segmentation-artifact", "segmentation-artifact/boundary-substitution",
                _span("SUB", ("one", "two", "three"), ("x",))),
        _scored("a", "segmentation-artifact", "segmentation-artifact/boundary-deletion",
                _span("DEL", ("four", "five"), ())),
    ]
    assert boundary_charge(scored) == {"a": 5}


# ---------------------------------------------------------------------------
# The three-clause form of the rule
# ---------------------------------------------------------------------------


def test_decide_without_a_boundary_block_is_the_two_clause_rule():
    verdict = decide(_stat(-0.43, -0.65, -0.22), _stat(-0.06, -0.15, 0.02))
    assert verdict["admitted"] is True
    assert "clause_3_boundary_block_falls_by_at_least_points" not in verdict
    assert verdict["clause_1_ci90_upper_threshold"] == 0.0


def test_decide_with_a_boundary_block_adds_clause_3():
    verdict = decide(
        _stat(-8.0, -8.9, -7.1),
        _stat(-0.16, -0.31, -0.02),
        wer_ci_upper_max=-0.2356,
        boundary=_stat(-7.17, -7.9, -6.4),
        boundary_drop_points=2.0,
    )
    assert verdict["clause_3_boundary_block_falls_by_at_least_points"] is True
    assert verdict["clause_3_required_drop_points"] == 2.0
    assert verdict["admitted"] is True


def test_decide_reads_the_stricter_wer_threshold_when_one_is_given():
    verdict = decide(
        _stat(-0.43, -0.65, -0.22),
        _stat(-0.06, -0.15, 0.02),
        wer_ci_upper_max=-0.2356,
        boundary=_stat(-5.0, -5.5, -4.5),
        boundary_drop_points=2.0,
    )
    # -0.22 clears zero but not the null's lower edge.
    assert verdict["clause_1_corpus_wer_improves_with_ci90_upper_below_zero"] is False
    assert verdict["admitted"] is False


# ---------------------------------------------------------------------------
# The receipt manifest
# ---------------------------------------------------------------------------


def test_write_check_manifest_is_sorted_lf_and_excludes_itself(tmp_path):
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    (tmp_path / "per-call-table.csv").write_text("call\n", encoding="utf-8")
    target = write_check_manifest(tmp_path)
    payload = target.read_bytes()
    assert b"\r" not in payload
    names = [line.split(" *")[1] for line in payload.decode("utf-8").strip().split("\n")]
    assert names == ["per-call-table.csv", "summary.json"]
    assert write_check_manifest(tmp_path).read_bytes() == payload
