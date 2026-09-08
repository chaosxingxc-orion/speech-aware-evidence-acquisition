"""``analysis.e21_relisten_plan`` -- the E21-LOOP-1 selective re-listen plan.

Pure arithmetic and pure refusals: no model, no GPU, no audio, no sealed run
directory, no ConEC file. What is asserted is the geometry of a re-cut (margin,
floor, clamp, the word range that comes back), and every clause of the proof
obligation the runtime loader re-runs on the bytes it loads.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis import e21_relisten_plan as rp


def window(index: int = 1, start: float = 0.0, end: float = 90.0, words: int = 180):
    return rp.ParentWindow(
        window_index=index, start_seconds=start, end_seconds=end, draft_words=words
    )


def unit(**kwargs):
    base = {
        "sample_id": "4320211",
        "unit_index": 1,
        "parent_window_index": 1,
        "start_seconds": 10.0,
        "end_seconds": 25.0,
        "predecessor_word_start": 20,
        "predecessor_word_end": 50,
    }
    base.update(kwargs)
    return rp.RelistenUnit(**base)


# ---------------------------------------------------------------------------
# 1. The rate conversion, in both directions.
# ---------------------------------------------------------------------------


def test_the_local_rate_maps_words_to_seconds_and_back():
    parent = window(words=180)  # 90 s / 180 words = 0.5 s per word
    assert rp.words_to_seconds(parent, 0) == 0.0
    assert rp.words_to_seconds(parent, 180) == 90.0
    assert rp.words_to_seconds(parent, 90) == 45.0
    assert rp.seconds_to_words(parent, 45.0) == 90.0


def test_a_window_with_no_draft_words_maps_everything_to_its_start():
    parent = window(words=0)
    assert rp.words_to_seconds(parent, 5) == parent.start_seconds


def test_the_conversion_is_clamped_to_the_window():
    parent = window(start=90.0, end=180.0, words=180)
    assert rp.words_to_seconds(parent, -5) == 90.0
    assert rp.words_to_seconds(parent, 500) == 180.0
    assert rp.seconds_to_words(parent, 0.0) == 0.0
    assert rp.seconds_to_words(parent, 1000.0) == 180.0


# ---------------------------------------------------------------------------
# 2. The re-cut: margin, floor, clamp.
# ---------------------------------------------------------------------------


def test_a_flagged_span_is_widened_by_the_margin_on_each_side():
    parent = window(words=180)
    start, end = rp.recut_bounds(parent, [(40, 42)], margin_seconds=5.0, min_seconds=1.0)
    assert start == pytest.approx(15.0)  # word 40 -> 20 s, minus 5
    assert end == pytest.approx(26.0)  # word 42 -> 21 s, plus 5


def test_the_union_of_several_flagged_spans_is_taken():
    parent = window(words=180)
    start, end = rp.recut_bounds(
        parent, [(40, 42), (10, 12), (100, 101)], margin_seconds=0.0, min_seconds=1.0
    )
    assert start == pytest.approx(5.0)
    assert end == pytest.approx(50.5)


def test_the_floor_grows_a_short_recut_about_its_midpoint():
    parent = window(words=180)
    start, end = rp.recut_bounds(parent, [(40, 41)], margin_seconds=0.0, min_seconds=10.0)
    assert end - start == pytest.approx(10.0)
    assert 0.5 * (start + end) == pytest.approx(20.25)


def test_a_recut_at_the_window_edge_spends_its_whole_floor_on_the_other_side():
    parent = window(words=180)
    start, end = rp.recut_bounds(parent, [(0, 1)], margin_seconds=5.0, min_seconds=10.0)
    assert start == pytest.approx(0.0)
    assert end - start >= 10.0
    end_start, end_end = rp.recut_bounds(
        parent, [(179, 180)], margin_seconds=5.0, min_seconds=10.0
    )
    assert end_end == pytest.approx(90.0)
    assert end_end - end_start >= 10.0


def test_the_recut_never_leaves_its_parent_window():
    parent = window(start=180.0, end=270.0, words=180)
    start, end = rp.recut_bounds(parent, [(0, 180)], margin_seconds=30.0, min_seconds=10.0)
    assert start == pytest.approx(180.0)
    assert end == pytest.approx(270.0)


def test_a_floor_longer_than_the_window_is_capped_by_the_window():
    parent = window(start=0.0, end=6.0, words=12)
    start, end = rp.recut_bounds(parent, [(5, 6)], margin_seconds=0.0, min_seconds=10.0)
    assert (start, end) == (0.0, 6.0)


def test_a_window_with_no_flag_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="no flagged span"):
        rp.recut_bounds(window(), [])


def test_a_flagged_span_outside_the_draft_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="draft words"):
        rp.recut_bounds(window(words=10), [(5, 40)])


# ---------------------------------------------------------------------------
# 3. The predecessor word range comes back outward-rounded and non-empty.
# ---------------------------------------------------------------------------


def test_the_word_range_is_rounded_outward_so_the_text_covers_the_audio():
    parent = window(words=180)
    assert rp.predecessor_word_range(parent, 15.0, 26.0) == (30, 52)


def test_the_word_range_is_never_empty_even_for_a_hairline_recut():
    parent = window(words=180)
    low, high = rp.predecessor_word_range(parent, 10.0, 10.0)
    assert high == low + 1


def test_the_word_range_stays_inside_the_window():
    parent = window(words=180)
    assert rp.predecessor_word_range(parent, 0.0, 90.0) == (0, 180)


# ---------------------------------------------------------------------------
# 4. build_units: one unit per flagged window, in window order.
# ---------------------------------------------------------------------------


def test_one_unit_is_built_per_flagged_window_in_window_order():
    windows = [window(index, (index - 1) * 90.0, index * 90.0) for index in (1, 2, 3)]
    units = rp.build_units("4320211", windows, {3: [(10, 12)], 1: [(4, 6)]})
    assert [entry.unit_index for entry in units] == [1, 2]
    assert [entry.parent_window_index for entry in units] == [1, 3]
    rp.assert_relisten_units(units, windows)


def test_a_flag_on_a_window_the_call_does_not_have_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="not one of"):
        rp.build_units("4320211", [window(1)], {7: [(1, 2)]})


def test_the_units_a_builder_produces_always_pass_the_proof():
    windows = [window(index, (index - 1) * 90.0, index * 90.0) for index in range(1, 9)]
    flags = {index: [(index, index + 2)] for index in range(1, 9)}
    rp.assert_relisten_units(rp.build_units("4320211", windows, flags), windows)


# ---------------------------------------------------------------------------
# 5. The proof obligation, clause by clause.
# ---------------------------------------------------------------------------


def test_an_empty_plan_block_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="no units"):
        rp.assert_relisten_units([], [window()])


def test_units_out_of_index_order_are_refused():
    with pytest.raises(rp.RelistenPlanError, match="unit_index"):
        rp.assert_relisten_units([unit(unit_index=2)], [window()])


def test_a_unit_naming_an_unknown_parent_window_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="does not have"):
        rp.assert_relisten_units([unit(parent_window_index=9)], [window()])


def test_two_units_on_the_same_parent_window_are_refused():
    windows = [window(1), window(2, 90.0, 180.0)]
    units = [unit(), unit(unit_index=2, start_seconds=40.0, end_seconds=60.0)]
    with pytest.raises(rp.RelistenPlanError, match="ascending window order"):
        rp.assert_relisten_units(units, windows)


def test_a_unit_leaving_its_parent_window_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="narrower look"):
        rp.assert_relisten_units([unit(end_seconds=200.0)], [window()])


def test_a_unit_under_the_refusal_to_shrink_floor_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="refusal-to-shrink"):
        rp.assert_relisten_units(
            [unit(start_seconds=10.0, end_seconds=13.0)], [window()], min_seconds=10.0
        )


def test_a_short_parent_window_lowers_the_floor_rather_than_failing():
    parent = window(start=0.0, end=4.0, words=8)
    rp.assert_relisten_units(
        [unit(start_seconds=0.0, end_seconds=4.0, predecessor_word_start=0,
              predecessor_word_end=8)],
        [parent],
        min_seconds=10.0,
    )


def test_overlapping_units_are_refused():
    windows = [window(1), window(2, 90.0, 180.0)]
    units = [
        unit(end_seconds=95.0),
        unit(unit_index=2, parent_window_index=2, start_seconds=90.0,
             end_seconds=110.0),
    ]
    with pytest.raises(rp.RelistenPlanError, match="narrower look"):
        rp.assert_relisten_units(units, windows)


def test_a_word_range_outside_the_parent_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="predecessor words"):
        rp.assert_relisten_units(
            [unit(predecessor_word_end=9999)], [window(words=180)]
        )


def test_an_empty_word_range_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="predecessor words"):
        rp.assert_relisten_units(
            [unit(predecessor_word_start=30, predecessor_word_end=30)], [window()]
        )


# ---------------------------------------------------------------------------
# 6. The document shape.
# ---------------------------------------------------------------------------


def test_the_plan_document_declares_the_schema_the_runtime_consumes():
    document = rp.plan_document(
        source="judges",
        margin_seconds=5.0,
        min_seconds=10.0,
        calls=[{"sample_id": "4320211"}],
        provenance={"exposure_row": "SAEA-E21-MF-LOOP-1-PREP-V1"},
    )
    assert document["schema"] == rp.RELISTEN_PLAN_SCHEMA
    assert document["flag_source"] == "judges"
    assert document["context_margin_seconds"] == 5.0
    assert document["min_relisten_seconds"] == 10.0


def test_an_unknown_flag_source_is_refused():
    with pytest.raises(rp.RelistenPlanError, match="seeded-random"):
        rp.plan_document(
            source="whatever", margin_seconds=5.0, min_seconds=10.0, calls=[],
            provenance={},
        )


def test_a_unit_renders_the_keys_the_loader_requires():
    payload = unit().as_json(unit_id="4320211#u0001")
    assert set(payload) == {
        "unit_id",
        "unit_index",
        "start_seconds",
        "end_seconds",
        "parent_window_index",
        "predecessor_word_start",
        "predecessor_word_end",
        "speaker",
        "end_cut",
    }
    assert payload["end_cut"] == rp.RELISTEN_END_CUT
    assert payload["speaker"] is None
