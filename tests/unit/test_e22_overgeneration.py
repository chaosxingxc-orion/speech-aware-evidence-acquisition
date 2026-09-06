"""Unit tests for the Earnings-22 over-generation analysis, on synthetic rows.

Nothing here reads the data root, the sealed arms or any real clip: every row
is hand-built with a known reference, a known hypothesis, a known token count
and a known geometry, so the harm/benefit accounting and the cap arithmetic
are checked against answers computed by hand rather than against the module's
own output. That is the point -- if the module can be wrong about a population
it was handed, the receipts it writes over the real one cannot be trusted
either.
"""

from __future__ import annotations

import hashlib
import json
import math

import pytest

from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (
    ALPHA_LADDER,
    OvergenerationError,
    RowMetrics,
    build_rows,
    cap_frontier,
    cap_tokens,
    ends_sentence_final,
    excess_by_duration,
    excess_by_overlap,
    excess_distribution,
    identity_gate,
    kept_words,
    load_clip_geometry,
    load_flight_tokens,
    per_row_csv,
    sentence_final_table,
    simulate_cap,
    token_profile,
    tokens_per_word,
    words_per_second_p95,
)

CLIP_HEADER = (
    "sample_id,call,segment_index,start_seconds,end_seconds,timestamp_seconds,"
    "media_seconds,duration_delta_seconds,end_clamped,gap_previous_seconds,"
    "gap_next_seconds,previous_overlap_seconds,next_overlap_seconds,frames,"
    "active_share,peak_dbfs,leading_silence_seconds,trailing_silence_seconds,"
    "previous_zone_active_share,next_zone_active_share,arm_a_tail_spans,"
    "arm_a_tail_words,arm_a_tail_contained_06,arm_a_head_spans,arm_a_head_words,"
    "arm_a_head_contained_06"
)


def _row(
    sample_id: str = "C1-0",
    *,
    call: str = "C1",
    seconds: float = 10.0,
    gap_next: float | None = -0.14,
    bleed: int = 0,
    reference: tuple[str, ...] = ("one", "two", "three", "four"),
    hypothesis: tuple[str, ...] = ("one", "two", "three", "four"),
    tokens: int | None = None,
    sentence_final: bool = True,
) -> RowMetrics:
    return RowMetrics(
        sample_id=sample_id,
        call=call,
        media_seconds=seconds,
        gap_next_seconds=gap_next,
        tail_bleed_06=bleed,
        tail_words=0,
        reference_words=len(reference),
        hypothesis_words=len(hypothesis),
        completion_tokens=len(hypothesis) if tokens is None else tokens,
        sentence_final=sentence_final,
        ref_tokens=reference,
        hyp_tokens=hypothesis,
    )


# ---------------------------------------------------------------------------
# Sentence-final detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("We are done.", True),
        ("We are done!  ", True),
        ("Is that right?", True),
        ('He said "we are done."', True),
        ("(we are done.)", True),
        ("and then the", False),
        ("or or is that something that's", False),
        ("", False),
        ("   ", False),
        ("对对对。", True),
        ("no closing mark", False),
    ],
)
def test_sentence_final_reads_the_raw_text(text: str, expected: bool) -> None:
    assert ends_sentence_final(text) is expected


def test_sentence_final_ignores_the_normalizers_stripping() -> None:
    """The normalizer removes punctuation, so the detector must read the raw
    text -- a normalized string can never end sentence-final."""

    assert ends_sentence_final("we are done") is False
    assert ends_sentence_final("we are done.") is True


# ---------------------------------------------------------------------------
# The excess
# ---------------------------------------------------------------------------


def test_excess_distribution_counts_longer_equal_and_shorter() -> None:
    rows = [
        _row("a", hypothesis=("one", "two", "three", "four", "five")),  # +1
        _row("b"),  # 0
        _row("c", hypothesis=("one", "two")),  # -2
    ]
    summary = excess_distribution(rows)
    assert summary["rows"] == 3
    assert summary["rows_longer"] == 1
    assert summary["rows_equal"] == 1
    assert summary["rows_shorter"] == 1
    assert summary["reference_words"] == 12
    assert summary["hypothesis_words"] == 11
    assert summary["net_excess_words"] == -1
    assert summary["gross_excess_words"] == 1
    assert summary["gross_deficit_words"] == 2
    assert summary["length_ratio"] == pytest.approx(11 / 12)


def test_excess_buckets_partition_the_population() -> None:
    rows = [
        _row(f"r{index}", hypothesis=tuple("w" * 1 for _ in range(index)))
        for index in range(0, 30)
    ]
    summary = excess_distribution(rows)
    assert sum(bucket["rows"] for bucket in summary["buckets"]) == len(rows)


def test_excess_by_overlap_splits_on_the_sign_of_gap_next() -> None:
    rows = [
        _row("over", gap_next=-0.16, hypothesis=("one", "two", "three", "four", "x")),
        _row("tight", gap_next=0.80),
        _row("last", gap_next=None),
    ]
    table = {block["label"]: block for block in excess_by_overlap(rows)}
    assert table["next segment overlaps"]["rows"] == 1
    assert table["next segment overlaps"]["net_excess_words"] == 1
    assert table["next segment is tight"]["rows"] == 1
    assert table["no next segment"]["rows"] == 1


def test_excess_by_duration_uses_the_audits_own_buckets() -> None:
    rows = [_row("a", seconds=0.5), _row("b", seconds=9.0), _row("c", seconds=40.0)]
    table = excess_by_duration(rows)
    counts = {block["label"]: block["rows"] for block in table}
    assert counts["0-1 s"] == 1
    assert counts["8-16 s"] == 1
    assert counts["16 s+"] == 1
    assert sum(counts.values()) == 3


def test_sentence_final_table_splits_and_keeps_the_duration_view() -> None:
    rows = [
        _row("a", sentence_final=True, seconds=5.0),
        _row("b", sentence_final=False, seconds=5.0),
        _row("c", sentence_final=False, seconds=20.0),
    ]
    table = sentence_final_table(rows)
    assert table["sentence_final"]["rows"] == 1
    assert table["run_on"]["rows"] == 2
    by_duration = {block["label"]: block for block in table["by_duration"]}
    assert by_duration["4-8 s"]["run_on"] == 1
    assert by_duration["16 s+"]["run_on"] == 1


# ---------------------------------------------------------------------------
# The cap arithmetic
# ---------------------------------------------------------------------------


def test_cap_tokens_is_the_declared_formula_and_is_floored_at_one() -> None:
    assert cap_tokens(1.0, 10.0, 5.0, 1.3) == math.ceil(1.0 * 10.0 * 5.0 * 1.3)
    assert cap_tokens(1.5, 4.0, 5.0, 1.3) == math.ceil(1.5 * 4.0 * 5.0 * 1.3)
    assert cap_tokens(0.01, 0.2, 5.0, 1.3) == 1


def test_kept_words_is_the_identity_when_the_cap_does_not_bite() -> None:
    row = _row(hypothesis=("a", "b", "c", "d"), tokens=8)
    assert kept_words(row, 8) == 4
    assert kept_words(row, 100) == 4


def test_kept_words_floors_a_partial_word_away() -> None:
    """10 tokens for 4 words; a cap of 7 buys 2.8 words, which is 2."""

    row = _row(hypothesis=("a", "b", "c", "d"), tokens=10)
    assert kept_words(row, 7) == 2
    assert kept_words(row, 5) == 2
    assert kept_words(row, 2) == 0


def test_words_per_second_p95_reads_the_reference_side() -> None:
    rows = [
        _row("a", seconds=1.0, reference=("x",) * 1),
        _row("b", seconds=1.0, reference=("x",) * 2),
        _row("c", seconds=1.0, reference=("x",) * 100),
    ]
    # The hypothesis lengths are irrelevant to this statistic by construction.
    assert words_per_second_p95(rows) == pytest.approx(100.0)


def test_tokens_per_word_is_pooled_not_averaged() -> None:
    rows = [
        _row("a", hypothesis=("x",), tokens=10),
        _row("b", hypothesis=("x",) * 9, tokens=9),
    ]
    # Pooled: 19 tokens over 10 words. A per-row mean would give 5.5.
    assert tokens_per_word(rows) == pytest.approx(1.9)


def test_simulate_cap_separates_benefit_from_harm() -> None:
    """One row whose surplus is cut (benefit) and one whose reference is cut
    (harm), under a cap chosen so both bite."""

    benefit = _row(
        "benefit",
        seconds=1.0,
        reference=("a", "b"),
        hypothesis=("a", "b", "c", "d"),
        tokens=4,
    )
    harm = _row(
        "harm",
        seconds=1.0,
        reference=("a", "b", "c", "d"),
        hypothesis=("a", "b", "c", "d"),
        tokens=4,
    )
    # cap = ceil(alpha * 1.0 * wps * tpw); pick constants so the cap is 2.
    result = simulate_cap([benefit, harm], alpha=1.0, wps_p95=2.0, tpw=1.0)
    assert result["rows_capped"] == 2
    assert result["benefit_rows"] == 1
    assert result["harm_rows_realized"] == 1
    assert result["harm_rows_cap_below_reference"] == 1
    assert result["harm_reference_words_realized"] == 2
    assert result["surplus_words_removed"] == 2
    assert result["completion_tokens_saved"] == 4


def test_simulate_cap_leaves_an_uncapped_population_at_the_sealed_number() -> None:
    rows = [
        _row(
            "a",
            seconds=100.0,
            reference=("alpha", "bravo", "charlie", "delta"),
            hypothesis=("alpha", "bravo", "charlie", "delta"),
            tokens=4,
        )
    ]
    result = simulate_cap(rows, alpha=3.0, wps_p95=5.0, tpw=1.3)
    assert result["rows_capped"] == 0
    assert result["benefit_rows"] == 0
    assert result["harm_rows_realized"] == 0
    assert result["corpus_wer_percent"] == pytest.approx(0.0)


def test_simulate_cap_counts_the_bleed_rows_it_actually_cuts() -> None:
    rows = [
        _row("bleeds", seconds=1.0, bleed=1, hypothesis=("a",) * 6, tokens=6),
        _row("quiet", seconds=1.0, bleed=0, hypothesis=("a",) * 6, tokens=6),
    ]
    result = simulate_cap(rows, alpha=1.0, wps_p95=2.0, tpw=1.0)
    assert result["tail_bleed_rows_total"] == 1
    assert result["tail_bleed_rows_capped"] == 1


def test_cap_frontier_reports_every_declared_rung() -> None:
    rows = [_row(f"r{index}", seconds=5.0) for index in range(4)]
    frontier = cap_frontier(rows)
    assert [rung["alpha"] for rung in frontier["rungs"]] == list(ALPHA_LADDER)
    assert "agentic" not in frontier["rungs"][0]
    assert frontier["formula"].startswith("n_predict = ceil(")


def test_cap_frontier_is_monotone_in_the_rows_it_touches() -> None:
    """A larger alpha is a looser cap, so it can never cut more rows."""

    rows = [
        _row(f"r{index}", seconds=1.0 + index, hypothesis=("a",) * (5 + index), tokens=5 + index)
        for index in range(20)
    ]
    frontier = cap_frontier(rows)
    capped = [rung["rows_capped"] for rung in frontier["rungs"]]
    assert capped == sorted(capped, reverse=True)


# ---------------------------------------------------------------------------
# The identity gate
# ---------------------------------------------------------------------------


def test_identity_gate_refuses_a_population_that_is_not_the_sealed_arm() -> None:
    with pytest.raises(OvergenerationError, match="identity gate"):
        identity_gate([_row("a")])


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _trace_line(channel: str, record_id: str, payload: dict) -> str:
    return json.dumps({"channel": channel, "record_id": record_id, "payload": payload})


def test_load_flight_tokens_joins_on_request_id(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    path.write_text(
        "\n".join(
            [
                _trace_line(
                    "MODEL_REQUEST",
                    "r1/request",
                    {"payload": {"request_id": "r1", "sample_id": "C1-0"}},
                ),
                _trace_line(
                    "MODEL_RESPONSE",
                    "r1/response",
                    {
                        "response_text_sha256": "0" * 64,
                        "usage": {"completion_tokens": 12, "prompt_tokens": 88},
                    },
                ),
                _trace_line("COST", "r1/cost", {}),
                "",
            ]
        ),
        encoding="utf-8",
    )
    tokens = load_flight_tokens(path)
    assert tokens == {
        "C1-0": {
            "completion_tokens": 12,
            "prompt_tokens": 88,
            "response_text_sha256": "0" * 64,
        }
    }


def test_load_flight_tokens_refuses_a_response_without_its_request(tmp_path) -> None:
    path = tmp_path / "trace.jsonl"
    path.write_text(
        _trace_line(
            "MODEL_RESPONSE",
            "ghost/response",
            {"response_text_sha256": "0" * 64, "usage": {"completion_tokens": 1, "prompt_tokens": 1}},
        ),
        encoding="utf-8",
    )
    with pytest.raises(OvergenerationError, match="unknown request"):
        load_flight_tokens(path)


def test_load_flight_tokens_refuses_a_repeated_request(tmp_path) -> None:
    line = _trace_line(
        "MODEL_REQUEST", "r1/request", {"payload": {"request_id": "r1", "sample_id": "C1-0"}}
    )
    path = tmp_path / "trace.jsonl"
    path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(OvergenerationError, match="repeats request"):
        load_flight_tokens(path)


def _write_clip_table(tmp_path, rows: list[str], *, digest: str | None = None):
    directory = tmp_path / "audit"
    directory.mkdir()
    payload = "\n".join([CLIP_HEADER, *rows]) + "\n"
    (directory / "per-clip-table.csv").write_text(payload, encoding="utf-8", newline="\n")
    recorded = digest or hashlib.sha256(payload.encode("utf-8")).hexdigest()
    (directory / "MANIFEST.sha256").write_text(
        f"{recorded} *per-clip-table.csv\n", encoding="utf-8", newline="\n"
    )
    return tmp_path


def _clip_row(sample_id: str = "C1-0", gap_next: str = "-0.140000") -> str:
    cells = [sample_id, "C1", "0", "0.0", "10.0", "10.0", "10.000000", "0.0", "0"]
    cells += ["", gap_next, "0.0", "0.14", "500", "0.5", "-16.0", "0.0", "0.0", "", "0.6"]
    cells += ["1", "4", "0", "0", "0", "0"]
    return ",".join(cells)


def test_load_clip_geometry_reads_the_committed_table(tmp_path, monkeypatch) -> None:
    from speech_aware_evidence_acquisition.analysis import e22_overgeneration as module

    root = _write_clip_table(tmp_path, [_clip_row()])
    monkeypatch.setattr(module, "CLIP_AUDIT_DIR_RELPATH", "audit")
    rows = load_clip_geometry(root)
    assert list(rows) == ["C1-0"]
    assert rows["C1-0"]["media_seconds"] == "10.000000"
    assert rows["C1-0"]["arm_a_tail_contained_06"] == "0"


def test_load_clip_geometry_refuses_a_drifted_table(tmp_path, monkeypatch) -> None:
    from speech_aware_evidence_acquisition.analysis import e22_overgeneration as module

    root = _write_clip_table(tmp_path, [_clip_row()], digest="f" * 64)
    monkeypatch.setattr(module, "CLIP_AUDIT_DIR_RELPATH", "audit")
    with pytest.raises(OvergenerationError, match="identity drift"):
        load_clip_geometry(root)


def test_load_clip_geometry_returns_rows_by_sample_id(tmp_path, monkeypatch) -> None:
    from speech_aware_evidence_acquisition.analysis import e22_overgeneration as module

    root = _write_clip_table(tmp_path, [_clip_row("C1-0"), _clip_row("C1-1", "0.500000")])
    monkeypatch.setattr(module, "CLIP_AUDIT_DIR_RELPATH", "audit")
    rows = load_clip_geometry(root)
    assert sorted(rows) == ["C1-0", "C1-1"]
    assert rows["C1-1"]["gap_next_seconds"] == "0.500000"


# ---------------------------------------------------------------------------
# build_rows
# ---------------------------------------------------------------------------


def _inputs():
    # Deliberately NOT number words: the Whisper EnglishTextNormalizer folds
    # "one two three four" into the single token "1234", which would make this
    # fixture test the normalizer rather than the module.
    references = {"C1-0": "alpha bravo charlie delta."}
    hypotheses = {"C1-0": "alpha bravo charlie delta echo."}
    flight_tokens = {"C1-0": {"completion_tokens": 7, "prompt_tokens": 90}}
    geometry = {
        "C1-0": {
            "media_seconds": "10.000000",
            "gap_next_seconds": "-0.140000",
            "arm_a_tail_contained_06": "1",
            "arm_a_tail_words": "3",
        }
    }
    segments = {"C1-0": {"source_id": "C1", "segment_id": "0"}}
    return references, hypotheses, flight_tokens, geometry, segments


def test_build_rows_carries_the_five_inputs_into_one_record() -> None:
    references, hypotheses, flight_tokens, geometry, segments = _inputs()
    rows = build_rows(
        references=references,
        hypotheses=hypotheses,
        flight_tokens=flight_tokens,
        geometry=geometry,
        segments=segments,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.call == "C1"
    assert row.reference_words == 4
    assert row.hypothesis_words == 5
    assert row.excess_words == 1
    assert row.completion_tokens == 7
    assert row.overlaps_next is True
    assert row.sentence_final is True
    assert row.tokens_per_word == pytest.approx(1.4)


@pytest.mark.parametrize(
    "drop,message",
    [
        ("references", "has no reference"),
        ("flight_tokens", "has no sealed usage record"),
        ("geometry", "absent from the clip table"),
        ("segments", "absent from the segment table"),
    ],
)
def test_build_rows_refuses_a_short_population(drop: str, message: str) -> None:
    references, hypotheses, flight_tokens, geometry, segments = _inputs()
    inputs = {
        "references": references,
        "hypotheses": hypotheses,
        "flight_tokens": flight_tokens,
        "geometry": geometry,
        "segments": segments,
    }
    inputs[drop] = {}
    with pytest.raises(OvergenerationError, match=message):
        build_rows(**inputs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# The receipt table carries no dev sentence text
# ---------------------------------------------------------------------------


def test_per_row_csv_never_writes_a_transcript() -> None:
    references, hypotheses, flight_tokens, geometry, segments = _inputs()
    rows = build_rows(
        references=references,
        hypotheses=hypotheses,
        flight_tokens=flight_tokens,
        geometry=geometry,
        segments=segments,
    )
    payload = per_row_csv(rows)
    for word in ("alpha", "bravo", "charlie", "delta", "echo"):
        assert word not in payload
    assert payload.splitlines()[0].startswith("sample_id,call,media_seconds")
    assert payload.endswith("\n")


def test_token_profile_reports_the_ceiling_it_was_flown_under() -> None:
    rows = [_row("a", tokens=10), _row("b", tokens=130)]
    profile = token_profile(rows)
    assert profile["declared_max_tokens"] == 1024
    assert profile["quantiles"]["max"] == 130.0
    assert profile["rows_at_ceiling"] == 0
    assert profile["total_completion_tokens"] == 140


# ---------------------------------------------------------------------------
# The subset projection
# ---------------------------------------------------------------------------


def test_population_baseline_is_the_uncapped_population() -> None:
    from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (
        population_baseline,
    )

    rows = [
        _row(
            "a",
            reference=("alpha", "bravo", "charlie", "delta"),
            hypothesis=("alpha", "bravo", "charlie", "echo"),
            tokens=4,
        )
    ]
    baseline = population_baseline(rows)
    assert baseline["rows"] == 1
    assert baseline["reference_words"] == 4
    assert baseline["substitutions"] == 1
    assert baseline["corpus_wer_percent"] == pytest.approx(25.0)
    assert "agentic" not in baseline


def test_simulate_cap_takes_its_delta_against_the_baseline_it_is_given() -> None:
    rows = [
        _row(
            "a",
            seconds=100.0,
            reference=("alpha", "bravo"),
            hypothesis=("alpha", "bravo"),
            tokens=2,
        )
    ]
    result = simulate_cap(rows, alpha=3.0, wps_p95=5.0, tpw=1.3, baseline_wer_percent=0.0)
    assert result["baseline_wer_percent"] == 0.0
    assert result["corpus_wer_delta_points"] == pytest.approx(0.0)


def test_build_receipts_runs_the_identity_gate_before_any_projection() -> None:
    """A synthetic population fails the gate, and it fails there rather than
    somewhere downstream -- a projection can never be produced from a
    population the gate refused."""

    from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (
        build_receipts,
    )

    with pytest.raises(OvergenerationError, match="identity gate"):
        build_receipts(
            rows=[_row("a")],
            outbound_attempts=0,
            outbound_targets=[],
            alphas=(1.5,),
            subset_ids=["not-a-row"],
            subset_label="X",
        )


def test_the_subset_projection_refuses_an_id_the_population_lacks(monkeypatch) -> None:
    from speech_aware_evidence_acquisition.analysis import e22_overgeneration as module

    rows = [
        _row(
            "a",
            reference=("alpha", "bravo", "charlie", "delta"),
            hypothesis=("alpha", "bravo", "charlie", "delta"),
            tokens=4,
        )
    ]
    monkeypatch.setattr(
        module,
        "SEALED_TOTALS",
        {"substitutions": 0, "deletions": 0, "insertions": 0, "reference_words": 4},
    )
    with pytest.raises(module.OvergenerationError, match="matched 0 of 1 declared ids"):
        module.build_receipts(
            rows=rows,
            outbound_attempts=0,
            outbound_targets=[],
            alphas=(1.5,),
            subset_ids=["not-a-row"],
            subset_label="X",
        )


def test_the_subset_projection_reports_its_own_baseline(monkeypatch) -> None:
    from speech_aware_evidence_acquisition.analysis import e22_overgeneration as module

    rows = [
        _row(
            "a",
            reference=("alpha", "bravo", "charlie", "delta"),
            hypothesis=("alpha", "bravo", "charlie", "delta"),
            tokens=4,
        ),
        _row(
            "b",
            reference=("alpha", "bravo"),
            hypothesis=("alpha", "bravo"),
            tokens=2,
        ),
    ]
    monkeypatch.setattr(
        module,
        "SEALED_TOTALS",
        {"substitutions": 0, "deletions": 0, "insertions": 0, "reference_words": 6},
    )
    summary, _ = module.build_receipts(
        rows=rows,
        outbound_attempts=0,
        outbound_targets=[],
        alphas=(1.5,),
        subset_ids=["b"],
        subset_label="SUBSET-1",
    )
    projection = summary["subset_projection"]
    assert projection["label"] == "SUBSET-1"
    assert projection["rows"] == 1
    assert projection["baseline"]["reference_words"] == 2
    rung = projection["cap_frontier"]["rungs"][0]
    assert rung["baseline_wer_percent"] == pytest.approx(
        projection["baseline"]["corpus_wer_percent"]
    )
