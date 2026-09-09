"""The unit-draft ownership stitch (``analysis.e21_unit_draft_stitch``).

DR-1's pass 1 is not re-flown; it is REGROUPED. Every number the family
reports rests on two properties of that regrouping -- ownership is monotone,
and the per-window drafts concatenate back to the sealed unit stitch byte for
byte -- so these tests fix both on synthetic spans, including the awkward case
the committed plan actually contains: a remainder window that owns no unit at
all.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.e21_unit_draft_stitch import (
    UnitDraftStitchError,
    assert_drafts_reproduce_units,
    assert_ownership_is_monotone,
    assert_window_identity,
    assign_units_to_windows,
    overlap_seconds,
    stitch_call,
    stitch_corpus,
    stitched_draft_text,
)
from speech_aware_evidence_acquisition.analysis.e21_window_pairing import WindowSpan


def span(sample_id, index, start, end, text, *, saturated=False):
    return WindowSpan(
        sample_id=sample_id,
        window_index=index,
        request_id=f"req-{sample_id}-{index}",
        start_seconds=float(start),
        end_seconds=float(end),
        audio_seconds=float(end) - float(start),
        text=text,
        saturated=saturated,
    )


def windows(sample_id, duration, size=90.0):
    bounds = []
    start = 0.0
    index = 1
    while start < duration - 1e-9:
        end = min(start + size, duration)
        bounds.append(span(sample_id, index, start, end, f"window {index} text"))
        start = end
        index += 1
    return tuple(bounds)


def test_overlap_is_never_negative():
    assert overlap_seconds((0.0, 10.0), (20.0, 30.0)) == 0.0
    assert overlap_seconds((0.0, 10.0), (5.0, 30.0)) == 5.0


class TestOwnership:
    def test_a_unit_is_owned_by_the_window_it_overlaps_most(self):
        grid = windows("c", 180.0)
        units = (
            span("c", 1, 0.0, 40.0, "alpha"),
            # 20 s in window 1, 30 s in window 2 -> window 2.
            span("c", 2, 70.0, 120.0, "beta"),
            span("c", 3, 120.0, 180.0, "gamma"),
        )
        assert assign_units_to_windows(units, grid) == (0, 1, 1)

    def test_a_tie_goes_to_the_earlier_window(self):
        grid = windows("c", 180.0)
        units = (
            span("c", 1, 0.0, 45.0, "alpha"),
            # exactly 45 s each side of the 90 s boundary.
            span("c", 2, 45.0, 135.0, "beta"),
            span("c", 3, 135.0, 180.0, "gamma"),
        )
        assert assign_units_to_windows(units, grid) == (0, 0, 1)

    def test_a_unit_outside_the_tiling_is_refused(self):
        grid = windows("c", 90.0)
        with pytest.raises(UnitDraftStitchError):
            assign_units_to_windows((span("c", 1, 200.0, 240.0, "x"),), grid)

    def test_a_reordering_assignment_is_refused(self):
        units = (span("c", 1, 0.0, 10.0, "a"), span("c", 2, 10.0, 20.0, "b"))
        assert_ownership_is_monotone((0, 0), units)
        with pytest.raises(UnitDraftStitchError):
            assert_ownership_is_monotone((1, 0), units)


class TestTheStitch:
    def test_the_drafts_rebuild_the_sealed_unit_stitch(self):
        grid = windows("c", 180.0)
        units = (
            span("c", 1, 0.0, 40.0, "alpha one"),
            span("c", 2, 40.0, 70.0, "alpha two"),
            span("c", 3, 70.0, 120.0, "beta"),
            span("c", 4, 120.0, 180.0, "gamma"),
        )
        drafts = stitch_call("c", units, grid)
        assert [draft.text for draft in drafts] == ["alpha one alpha two", "beta gamma"]
        assert_drafts_reproduce_units(drafts, units)
        assert stitched_draft_text(drafts) == "alpha one alpha two beta gamma"

    def test_a_saturated_unit_contributes_nothing_and_is_counted(self):
        grid = windows("c", 90.0)
        units = (
            span("c", 1, 0.0, 45.0, "kept words"),
            span("c", 2, 45.0, 90.0, "", saturated=True),
        )
        drafts = stitch_call("c", units, grid)
        assert drafts[0].text == "kept words"
        assert drafts[0].saturated_units == 1
        assert drafts[0].unit_count == 2
        assert_drafts_reproduce_units(drafts, units)

    def test_a_remainder_window_may_own_no_unit_and_the_stitch_still_holds(self):
        # The committed plan v2's own case: a 1.4-second last window entirely
        # inside a unit the preceding window wins.
        grid = windows("c", 91.4)
        assert len(grid) == 2
        units = (
            span("c", 1, 0.0, 84.0, "the long turn"),
            span("c", 2, 84.0, 91.4, "the closing turn"),
        )
        drafts = stitch_call("c", units, grid)
        assert drafts[1].text == ""
        assert drafts[1].empty is True
        assert drafts[1].unit_count == 0
        # Nothing is lost: the closing turn's words are delivered by window 1.
        assert_drafts_reproduce_units(drafts, units)
        assert stitched_draft_text(drafts) == "the long turn the closing turn"

    def test_a_span_of_the_wrong_call_is_refused(self):
        grid = windows("c", 90.0)
        with pytest.raises(UnitDraftStitchError):
            stitch_call("c", (span("other", 1, 0.0, 90.0, "x"),), grid)


class TestTheCorpus:
    def test_every_call_is_stitched_and_proved(self):
        grid_a = windows("a", 180.0)
        grid_b = windows("b", 90.0)
        units_a = (span("a", 1, 0.0, 90.0, "one"), span("a", 2, 90.0, 180.0, "two"))
        units_b = (span("b", 1, 0.0, 90.0, "three"),)
        drafts = stitch_corpus(
            {"a": units_a, "b": units_b}, {"a": grid_a, "b": grid_b}
        )
        assert set(drafts) == {"a", "b"}
        assert stitched_draft_text(drafts["a"]) == "one two"
        assert_window_identity(drafts, {"a": grid_a, "b": grid_b})

    def test_a_call_set_mismatch_is_refused(self):
        with pytest.raises(UnitDraftStitchError):
            stitch_corpus({"a": ()}, {"b": ()})

    def test_a_drafted_window_that_drifts_from_the_sealed_one_is_refused(self):
        grid = windows("a", 90.0)
        units = (span("a", 1, 0.0, 90.0, "one"),)
        drafts = stitch_corpus({"a": units}, {"a": grid})
        moved = (span("a", 1, 0.0, 89.0, "one"),)
        with pytest.raises(UnitDraftStitchError):
            assert_window_identity(drafts, {"a": moved})
