"""Unit tests for the Earnings-22 clip-boundary audit, on synthetic segments.

Nothing here reads the data root, the sealed arms or any real clip: the geometry
is built from hand-written segment rows whose gaps and overlaps are known by
construction, and the energy gate runs over synthetic PCM. That is the point --
if the module can be wrong about a segment table it was handed, the receipts it
writes over the real one cannot be trusted either.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.analysis.e22_clip_boundary import (
    BoundarySpan,
    ClipBoundaryError,
    clip_geometry,
    containment_bucket,
    cross_boundary_activity,
    cross_boundary_geometry,
    energy_margins,
    frame_rms_dbfs,
    gap_distribution,
    margin_summary,
    per_clip_table,
)

SAMPLE_RATE = 16000


def _item(call: str, index: int, start: float, end: float, media: float | None = None) -> dict:
    return {
        "sample_id": f"{call}-{index}",
        "parent_sample_id": call,
        "segment_start_seconds": start,
        "segment_end_seconds": end,
        "audio_seconds": end - start if media is None else media,
        "audio_sha256": "0" * 64,
        "media_relpath": f"derived/{call}/{call}-{index}.wav",
        "end_clamped_to_decoded_parent": media is not None,
    }


def _three_clip_call() -> list[dict]:
    """One call whose first pair OVERLAPS by 0.18 s and whose second pair is
    separated by 0.50 s."""

    return [
        _item("C1", 0, 0.00, 2.00),
        _item("C1", 1, 1.82, 4.00),
        _item("C1", 2, 4.50, 6.00),
    ]


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


def test_gaps_are_signed_and_neighbourless_ends_are_none():
    geometry = clip_geometry(_three_clip_call())
    first, middle, last = geometry["C1-0"], geometry["C1-1"], geometry["C1-2"]

    assert first.gap_previous_seconds is None
    assert last.gap_next_seconds is None
    assert first.gap_next_seconds == pytest.approx(-0.18)
    assert middle.gap_previous_seconds == pytest.approx(-0.18)
    assert middle.gap_next_seconds == pytest.approx(0.50)
    assert last.gap_previous_seconds == pytest.approx(0.50)


def test_overlap_flags_and_overlap_seconds_follow_the_sign():
    geometry = clip_geometry(_three_clip_call())

    assert geometry["C1-0"].overlaps_next is True
    assert geometry["C1-0"].next_overlap_seconds == pytest.approx(0.18)
    assert geometry["C1-1"].overlaps_next is False
    assert geometry["C1-1"].next_overlap_seconds == 0.0
    assert geometry["C1-2"].previous_overlap_seconds == 0.0


def test_duration_delta_is_zero_unless_the_cut_was_clamped():
    items = _three_clip_call()
    items[2] = _item("C1", 2, 4.50, 6.00, media=1.30)
    geometry = clip_geometry(items)

    assert geometry["C1-0"].duration_delta_seconds == pytest.approx(0.0)
    assert geometry["C1-2"].duration_delta_seconds == pytest.approx(-0.20)
    assert geometry["C1-2"].end_clamped is True


def test_a_hole_in_the_segment_indices_refuses():
    items = [_item("C1", 0, 0.0, 1.0), _item("C1", 2, 2.0, 3.0)]

    with pytest.raises(ClipBoundaryError, match="non-contiguous"):
        clip_geometry(items)


def test_an_id_that_is_not_call_dash_index_refuses():
    item = _item("C1", 0, 0.0, 1.0)
    item["sample_id"] = "C1-000a"

    with pytest.raises(ClipBoundaryError, match="not <call>-<segment index>"):
        clip_geometry([item])


def test_two_calls_never_share_a_neighbour():
    geometry = clip_geometry(
        [_item("C1", 0, 0.0, 1.0), _item("C1", 1, 1.0, 2.0), _item("C2", 0, 0.0, 1.0)]
    )

    assert geometry["C1-1"].gap_next_seconds is None
    assert geometry["C2-0"].gap_previous_seconds is None
    assert geometry["C2-0"].gap_next_seconds is None


def test_gap_distribution_counts_pairs_not_clips():
    report = gap_distribution(clip_geometry(_three_clip_call()))

    assert report["pairs"] == 2
    assert report["overlapping_pairs"] == 1
    assert report["separated_pairs"] == 1
    assert report["touching_pairs"] == 0
    assert report["overlap_seconds_total"] == pytest.approx(0.18, abs=1e-6)
    assert report["min_seconds"] == pytest.approx(-0.18, abs=1e-6)


def test_gap_distribution_buckets_a_touching_pair_as_neither():
    geometry = clip_geometry([_item("C1", 0, 0.0, 1.0), _item("C1", 1, 1.0, 2.0)])
    report = gap_distribution(geometry)

    assert (report["overlapping_pairs"], report["touching_pairs"]) == (0, 1)
    assert report["overlap_seconds_total"] == 0.0


# ---------------------------------------------------------------------------
# The energy gate
# ---------------------------------------------------------------------------


def _tone(seconds: float, amplitude: int = 8000) -> list[int]:
    frames = int(round(seconds * SAMPLE_RATE))
    return [
        int(amplitude * math.sin(2.0 * math.pi * 220.0 * index / SAMPLE_RATE))
        for index in range(frames)
    ]


def _silence(seconds: float) -> list[int]:
    return [0] * int(round(seconds * SAMPLE_RATE))


def test_frame_rms_dbfs_drops_the_trailing_partial_frame():
    levels = frame_rms_dbfs([1000] * 500, 320)

    assert levels.size == 1


def test_margins_find_the_silence_at_both_ends():
    samples = _silence(0.30) + _tone(0.50) + _silence(0.20)
    margins = energy_margins(samples, SAMPLE_RATE)

    assert margins.silent is False
    assert margins.leading_seconds == pytest.approx(0.30, abs=0.02)
    assert margins.trailing_seconds == pytest.approx(0.20, abs=0.02)


def test_a_clip_that_ends_in_speech_has_no_trailing_margin():
    margins = energy_margins(_silence(0.10) + _tone(0.40), SAMPLE_RATE)

    assert margins.trailing_seconds == pytest.approx(0.0, abs=1e-9)


def test_an_all_silent_clip_is_flagged_rather_than_gated_against_its_own_noise():
    margins = energy_margins(_silence(0.50), SAMPLE_RATE)

    assert margins.silent is True
    assert margins.active_frames == 0


def test_the_overlap_zone_share_reads_only_the_end_of_the_clip():
    # Speech for 0.4 s, then 0.2 s of silence; the last 0.2 s is the overlap zone.
    margins = energy_margins(
        _tone(0.40) + _silence(0.20), SAMPLE_RATE, next_overlap_seconds=0.20
    )

    assert margins.next_zone_frames == 10
    assert margins.next_zone_active_share == pytest.approx(0.0)

    # The same clip reversed puts the speech inside the zone.
    margins = energy_margins(
        _silence(0.20) + _tone(0.40), SAMPLE_RATE, next_overlap_seconds=0.20
    )

    assert margins.next_zone_active_share == pytest.approx(1.0)


def test_no_overlap_means_no_zone_and_a_none_share():
    margins = energy_margins(_tone(0.40), SAMPLE_RATE)

    assert margins.next_zone_frames == 0
    assert margins.next_zone_active_share is None
    assert margins.previous_zone_active_share is None


def test_an_empty_clip_measures_nothing_rather_than_dividing_by_zero():
    margins = energy_margins([], SAMPLE_RATE)

    assert (margins.frames, margins.active_share, margins.silent) == (0, 0.0, True)


# ---------------------------------------------------------------------------
# The cross
# ---------------------------------------------------------------------------


def test_containment_buckets_match_the_scan_thresholds():
    assert containment_bucket(0.0) == "contains_none"
    assert containment_bucket(0.2) == "contains_some"
    assert containment_bucket(0.34) == "contains_0.34_to_0.6"
    assert containment_bucket(0.6) == "contains_0.6_or_more"


def test_the_cross_separates_overlapping_clips_from_tight_ones():
    geometry = clip_geometry(_three_clip_call())
    spans = [
        BoundarySpan("C1-0", "C1", "tail", 3, 1.0),  # overlapping edge
        BoundarySpan("C1-1", "C1", "tail", 2, 1.0),  # tight edge
        BoundarySpan("C1-2", "C1", "tail", 4, 1.0),  # no neighbour
        BoundarySpan("C1-1", "C1", "head", 1, 0.0),  # overlapping edge, no containment
    ]
    report = cross_boundary_geometry(spans, geometry, reference_words=1000)

    tail = report["tail"]["by_containment"]["contains_0.6_or_more"]
    assert tail["overlapping_clip"]["spans"] == 1
    assert tail["overlapping_clip"]["words"] == 3
    assert tail["overlapping_clip"]["wer_points"] == pytest.approx(0.3)
    assert tail["tight_clip"]["spans"] == 1
    assert tail["no_neighbour"]["spans"] == 1
    assert report["tail"]["spans"] == 3
    assert report["tail"]["words"] == 9

    head = report["head"]["by_containment"]["contains_none"]
    assert head["overlapping_clip"]["spans"] == 1


def test_the_audio_cross_uses_the_zone_share_not_the_timestamps():
    geometry = clip_geometry(_three_clip_call())
    margins = {
        "C1-0": energy_margins(
            _silence(0.20) + _tone(0.40), SAMPLE_RATE, next_overlap_seconds=0.18
        ),
        "C1-1": energy_margins(_tone(0.40), SAMPLE_RATE),
    }
    spans = [
        BoundarySpan("C1-0", "C1", "tail", 3, 1.0),
        BoundarySpan("C1-1", "C1", "tail", 2, 1.0),
    ]
    report = cross_boundary_activity(spans, geometry, margins)

    cell = report["tail"]["contains_0.6_or_more"]
    assert cell["audible_overlap"] == 1
    assert cell["no_overlap_zone"] == 1


def test_margin_summary_groups_each_edge_by_its_own_overlap_sign():
    geometry = clip_geometry(_three_clip_call())
    margins = {
        sample_id: energy_margins(
            _tone(0.40) + _silence(0.20),
            SAMPLE_RATE,
            previous_overlap_seconds=geometry[sample_id].previous_overlap_seconds,
            next_overlap_seconds=geometry[sample_id].next_overlap_seconds,
        )
        for sample_id in geometry
    }
    report = margin_summary(geometry, margins)

    # C1-0 overlaps its next neighbour; C1-1 does not; C1-2 has no next neighbour.
    assert report["tail_overlapping"]["silence_seconds"]["n"] == 1
    assert report["tail_tight"]["silence_seconds"]["n"] == 1
    # C1-1 overlaps its previous neighbour; C1-2 does not; C1-0 has no previous.
    assert report["head_overlapping"]["silence_seconds"]["n"] == 1
    assert report["head_tight"]["silence_seconds"]["n"] == 1
    assert report["clips_measured"] == 3


def test_the_per_clip_table_carries_identifiers_and_numbers_only():
    geometry = clip_geometry(_three_clip_call())
    spans = [
        BoundarySpan("C1-0", "C1", "tail", 3, 1.0),
        BoundarySpan("C1-0", "C1", "tail", 1, 0.0),
    ]
    text = per_clip_table(geometry, {}, spans)
    lines = text.strip().split("\n")

    assert len(lines) == 4
    assert lines[0].startswith("sample_id,call,segment_index,")
    first = dict(zip(lines[0].split(","), lines[1].split(",")))
    assert first["sample_id"] == "C1-0"
    assert first["arm_a_tail_spans"] == "2"
    assert first["arm_a_tail_words"] == "4"
    assert first["arm_a_tail_contained_06"] == "1"
    assert first["gap_previous_seconds"] == ""
    assert first["gap_next_seconds"].startswith("-0.18")
    # No margins were supplied, so every energy column is empty rather than zero.
    assert first["leading_silence_seconds"] == ""
