"""``analysis.e21_speaker_turn_units`` on SYNTHETIC diarization and synthetic PCM.

No sealed artifact, no audio file and no reference is opened here: every fixture is
built in the test, which is what lets the five rules be exercised at the edges
(a monologue with no pause, a backchannel with no same-speaker neighbour, a snap
that would reorder two boundaries) that a real call may or may not contain.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from speech_aware_evidence_acquisition.analysis import e21_speaker_turn_units as stu
from speech_aware_evidence_acquisition.reproduction.diarization import SpeakerSegment

RATE = 16_000
FRAME = int(RATE * stu.FRAME_MS / 1000)


def _pcm(spans, duration, *, rate=RATE, amplitude=8000):
    """int16 PCM: silence everywhere except the ``(start, end)`` spans."""

    samples = np.zeros(int(round(duration * rate)), dtype=np.int64)
    tone = np.arange(len(samples))
    for start, end in spans:
        lo = int(round(start * rate))
        hi = min(int(round(end * rate)), len(samples))
        samples[lo:hi] = (amplitude * np.sin(tone[lo:hi] * 0.3)).astype(np.int64)
    return samples.astype(np.int16)


def _activity(samples, duration, *, window_seconds=90.0, rate=RATE):
    count = max(1, math.ceil(duration / window_seconds))
    bounds = [
        (index * window_seconds, min((index + 1) * window_seconds, duration))
        for index in range(count)
    ]
    ranges = stu.window_frame_ranges(bounds, rate, FRAME)
    ranges = list(ranges)
    ranges[-1] = (ranges[-1][0], len(samples) // FRAME)
    return stu.frame_activity(samples, rate, ranges)


def _plan(segments, spans, duration, **kwargs):
    samples = _pcm(spans, duration)
    active, _levels, frame_seconds = _activity(samples, duration)
    pauses = stu.pauses_from_activity(active, frame_seconds)
    return stu.plan_units("CALL", segments, duration, pauses, active, frame_seconds, **kwargs)


def _plan_v2(segments, spans, duration, **kwargs):
    samples = _pcm(spans, duration)
    active, _levels, frame_seconds = _activity(samples, duration)
    pauses = stu.pauses_from_activity(active, frame_seconds)
    return stu.plan_units_v2("CALL", segments, duration, pauses, active, frame_seconds, **kwargs)


# ---------------------------------------------------------------------------
# identity helpers
# ---------------------------------------------------------------------------


def test_a_unit_id_round_trips_to_its_call():
    assert stu.unit_id("4320211", 7) == "4320211#u0007"
    assert stu.call_of("4320211#u0007") == "4320211"


@pytest.mark.parametrize("bad", ["4320211", "#u0001", ""])
def test_a_non_unit_id_is_refused_rather_than_guessed(bad):
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.call_of(bad)


def test_a_sample_id_that_already_carries_the_separator_is_refused():
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.unit_id("call#u1", 1)


# ---------------------------------------------------------------------------
# activity and pauses
# ---------------------------------------------------------------------------


def test_the_threshold_is_per_window_so_a_loud_passage_cannot_silence_a_quiet_one():
    duration = 180.0
    loud = _pcm([(0.0, 80.0)], duration, amplitude=30000)
    quiet = _pcm([(95.0, 175.0)], duration, amplitude=300)
    samples = (loud.astype(np.int64) + quiet.astype(np.int64)).astype(np.int16)
    active, _levels, frame_seconds = _activity(samples, duration)
    quiet_frame = int(120.0 / frame_seconds)
    assert bool(active[quiet_frame]) is True


def test_a_pause_shorter_than_the_minimum_is_not_a_pause():
    duration = 20.0
    samples = _pcm([(0.0, 9.9), (10.0, 20.0)], duration)
    active, _levels, frame_seconds = _activity(samples, duration)
    pauses = stu.pauses_from_activity(active, frame_seconds)
    assert all(pause.duration_seconds >= stu.PAUSE_MIN_SECONDS - 1e-9 for pause in pauses)
    assert not any(9.5 < pause.midpoint_seconds < 10.5 for pause in pauses)


def test_a_pause_at_or_over_the_minimum_is_found_where_it_is():
    duration = 20.0
    samples = _pcm([(0.0, 9.0), (10.0, 20.0)], duration)
    active, _levels, frame_seconds = _activity(samples, duration)
    pauses = stu.pauses_from_activity(active, frame_seconds)
    assert any(abs(pause.midpoint_seconds - 9.5) < 0.05 for pause in pauses)


def test_frame_ranges_that_do_not_tile_the_call_are_a_load_time_error():
    samples = _pcm([(0.0, 10.0)], 10.0)
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.frame_activity(samples, RATE, [(0, 10)])


def _write_slice(path, samples, rate=RATE):
    import wave

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.astype("<i2").tobytes())
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_slice_by_slice_activity_equals_whole_call_activity(tmp_path):
    duration = 180.0
    samples = _pcm([(0.0, 40.0), (95.0, 175.0)], duration)
    per_window = int(90.0 * RATE)
    records = []
    for index in range(2):
        block = samples[index * per_window : (index + 1) * per_window]
        relpath = f"slices/i{index:04d}.wav"
        digest = _write_slice(tmp_path / relpath, block)
        records.append(
            {"media_relpath": relpath, "sha256": digest, "sample_rate_hz": RATE}
        )
    sliced, frame_seconds = stu.activity_from_sealed_slices(tmp_path, records)
    whole, _levels, whole_frame_seconds = _activity(samples, duration)
    assert frame_seconds == pytest.approx(whole_frame_seconds)
    assert np.array_equal(sliced, whole)


def test_a_slice_whose_bytes_moved_is_refused_before_a_sample_is_read(tmp_path):
    samples = _pcm([(0.0, 5.0)], 10.0)
    relpath = "slices/i0000.wav"
    _write_slice(tmp_path / relpath, samples)
    records = [{"media_relpath": relpath, "sha256": "0" * 64, "sample_rate_hz": RATE}]
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.activity_from_sealed_slices(tmp_path, records)


def test_a_slice_at_the_wrong_rate_is_refused(tmp_path):
    samples = _pcm([(0.0, 5.0)], 10.0)
    relpath = "slices/i0000.wav"
    digest = _write_slice(tmp_path / relpath, samples)
    records = [{"media_relpath": relpath, "sha256": digest, "sample_rate_hz": 8000}]
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.activity_from_sealed_slices(tmp_path, records)


def test_ends_on_active_frame_reports_the_frame_the_cut_falls_in():
    duration = 20.0
    samples = _pcm([(0.0, 9.0), (10.0, 20.0)], duration)
    active, _levels, frame_seconds = _activity(samples, duration)
    assert stu.ends_on_active_frame(active, frame_seconds, 5.0) is True
    assert stu.ends_on_active_frame(active, frame_seconds, 9.5) is False


# ---------------------------------------------------------------------------
# rule 1 -- never cross a diarized speaker change
# ---------------------------------------------------------------------------


def test_consecutive_same_speaker_segments_are_one_turn():
    segments = [
        SpeakerSegment(0.0, 5.0, "speaker_0"),
        SpeakerSegment(5.5, 9.0, "speaker_0"),
        SpeakerSegment(11.0, 18.0, "speaker_1"),
    ]
    assert stu.turns(segments) == (
        ("speaker_0", 0.0, 9.0),
        ("speaker_1", 11.0, 18.0),
    )


def test_a_turn_boundary_is_the_midpoint_of_the_gap():
    segments = [
        SpeakerSegment(0.0, 9.0, "speaker_0"),
        SpeakerSegment(11.0, 18.0, "speaker_1"),
    ]
    assert stu.turn_boundaries(segments) == (10.0,)


def test_overlapping_turns_cut_at_the_incoming_speakers_onset():
    segments = [
        SpeakerSegment(0.0, 9.0, "speaker_0"),
        SpeakerSegment(8.0, 18.0, "speaker_1"),
    ]
    assert stu.turn_boundaries(segments) == (8.0,)


def test_every_unit_of_a_two_speaker_call_is_pure():
    duration = 40.0
    segments = [
        SpeakerSegment(0.0, 18.0, "speaker_0"),
        SpeakerSegment(21.0, 40.0, "speaker_1"),
    ]
    units = _plan(segments, [(0.0, 18.0), (21.0, 40.0)], duration)
    assert len(units) == 2
    assert [unit.speaker for unit in units] == ["speaker_0", "speaker_1"]
    assert all(unit.speaker_count == 1 for unit in units)
    assert all(unit.speaker_share == pytest.approx(1.0) for unit in units)


# ---------------------------------------------------------------------------
# rule 2 -- never end inside active speech when a pause is reachable
# ---------------------------------------------------------------------------


def test_a_turn_boundary_inside_speech_snaps_onto_the_nearby_pause():
    duration = 40.0
    # The diarizer puts the change at 20.0; the real pause is 21.0-22.0.
    segments = [
        SpeakerSegment(0.0, 19.5, "speaker_0"),
        SpeakerSegment(20.5, 40.0, "speaker_1"),
    ]
    units = _plan(segments, [(0.0, 21.0), (22.0, 40.0)], duration)
    assert len(units) == 2
    assert units[0].end_cut == stu.CUT_PAUSE
    assert units[0].end_seconds == pytest.approx(21.5, abs=0.05)
    assert units[0].ends_active is False


def test_a_boundary_with_no_pause_in_range_stays_and_is_reported_as_such():
    duration = 40.0
    segments = [
        SpeakerSegment(0.0, 20.0, "speaker_0"),
        SpeakerSegment(20.0, 40.0, "speaker_1"),
    ]
    units = _plan(segments, [(0.0, 40.0)], duration)
    assert units[0].end_cut == stu.CUT_TURN_BOUNDARY
    assert units[0].end_seconds == pytest.approx(20.0)
    assert units[0].ends_active is True


def test_snapping_prefers_the_nearest_pause_and_breaks_a_tie_to_the_earlier_one():
    pauses = (stu.Pause(8.0, 9.0), stu.Pause(11.0, 12.0))
    moved, kind = stu.snap_to_pause(10.0, pauses)
    assert kind == stu.CUT_PAUSE
    assert moved == pytest.approx(8.5)


def test_a_pause_beyond_the_snap_radius_is_out_of_reach():
    pauses = (stu.Pause(0.0, 1.0),)
    moved, kind = stu.snap_to_pause(20.0, pauses)
    assert (moved, kind) == (20.0, stu.CUT_TURN_BOUNDARY)


def test_a_snap_that_would_reorder_two_boundaries_is_reverted_not_applied():
    duration = 60.0
    # Three turns whose changes sit at 20.4 and 21.4, with one long pause at 30 s
    # that both would otherwise snap onto and fold the middle unit to nothing.
    segments = [
        SpeakerSegment(0.0, 20.0, "speaker_0"),
        SpeakerSegment(20.8, 21.0, "speaker_1"),
        SpeakerSegment(21.8, 60.0, "speaker_2"),
    ]
    units = _plan(segments, [(0.0, 29.0), (32.0, 60.0)], duration)
    stu.assert_tiles(units, duration)
    assert all(unit.duration_seconds > 0 for unit in units)
    starts = [unit.start_seconds for unit in units]
    assert starts == sorted(starts)


# ---------------------------------------------------------------------------
# rule 3 -- the 90-second cap
# ---------------------------------------------------------------------------


def test_a_long_monologue_splits_at_its_longest_internal_pause():
    duration = 150.0
    segments = [SpeakerSegment(0.0, 150.0, "speaker_0")]
    # a 0.5 s pause at 40 s and a 3 s pause at 80.5 s: the longest wins
    units = _plan(segments, [(0.0, 39.75), (40.25, 79.0), (82.0, 150.0)], duration)
    assert len(units) == 2
    assert units[0].end_seconds == pytest.approx(80.5, abs=0.05)
    assert units[0].end_cut == stu.CUT_PAUSE
    assert all(unit.duration_seconds <= stu.MAX_UNIT_SECONDS + 1e-6 for unit in units)


def test_the_cap_split_recurses_until_every_piece_fits():
    duration = 300.0
    segments = [SpeakerSegment(0.0, 300.0, "speaker_0")]
    # The longest pause is at 200 s, which leaves a 200-second LEFT piece; a
    # one-sided recursion would emit it over the cap.
    units = _plan(
        segments,
        [(0.0, 49.6), (50.4, 129.6), (130.4, 198.0), (202.0, 300.0)],
        duration,
    )
    assert all(unit.duration_seconds <= stu.MAX_UNIT_SECONDS + 1e-6 for unit in units)
    assert all(unit.duration_seconds > 0 for unit in units)
    stu.assert_tiles(units, duration)


def test_a_monologue_with_no_admissible_pause_is_force_split_and_flagged():
    duration = 200.0
    segments = [SpeakerSegment(0.0, 200.0, "speaker_0")]
    units = _plan(segments, [(0.0, 200.0)], duration)
    assert [round(unit.duration_seconds, 3) for unit in units] == [90.0, 90.0, 20.0]
    assert units[0].end_cut == stu.CUT_FORCED
    assert all("forced-cap-split" in unit.flags for unit in units)


def test_no_unit_ever_exceeds_the_cap():
    duration = 400.0
    segments = [
        SpeakerSegment(0.0, 200.0, "speaker_0"),
        SpeakerSegment(201.0, 400.0, "speaker_1"),
    ]
    units = _plan(segments, [(0.0, 200.0), (201.0, 400.0)], duration)
    assert all(unit.duration_seconds <= stu.MAX_UNIT_SECONDS + 1e-6 for unit in units)


# ---------------------------------------------------------------------------
# rule 4 -- the 1.0-second minimum
# ---------------------------------------------------------------------------


def test_a_backchannel_with_no_same_speaker_neighbour_is_kept_and_flagged():
    duration = 60.0
    segments = [
        SpeakerSegment(0.0, 25.0, "speaker_0"),
        SpeakerSegment(25.3, 25.7, "speaker_1"),
        SpeakerSegment(26.0, 60.0, "speaker_2"),
    ]
    units = _plan(segments, [(0.0, 60.0)], duration)
    short = [unit for unit in units if unit.duration_seconds < stu.MIN_UNIT_SECONDS]
    assert short, "the backchannel should survive as its own unit"
    assert all("short-kept" in unit.flags for unit in short)
    assert all(unit.speaker == "speaker_1" for unit in short)


def test_a_short_piece_of_one_turn_merges_into_its_same_speaker_neighbour():
    duration = 100.0
    segments = [SpeakerSegment(0.0, 100.0, "speaker_0")]
    # A pause at 99.4-99.9 would otherwise leave a 0.35 s tail unit.
    units = _plan(segments, [(0.0, 99.4), (99.9, 100.0)], duration)
    assert all(unit.duration_seconds >= stu.MIN_UNIT_SECONDS - 1e-9 for unit in units)


def test_a_merge_that_would_break_the_cap_is_refused():
    duration = 91.0
    segments = [SpeakerSegment(0.0, 91.0, "speaker_0")]
    units = _plan(segments, [(0.0, 89.6), (90.1, 91.0)], duration)
    assert all(unit.duration_seconds <= stu.MAX_UNIT_SECONDS + 1e-6 for unit in units)


# ---------------------------------------------------------------------------
# rule 4, v2 -- the coordinator's 2026-09-08 minimum (module docstring,
# "OBS-E1 UNIT PLAN v2"): a short span merges into whichever neighbour is
# LONGER, either speaker, ties to the preceding neighbour; v1's builder is
# untouched, so the very same scenario is exercised through both.
# ---------------------------------------------------------------------------


def test_v1_keeps_a_cross_speaker_sliver_but_v2_merges_it_into_the_longer_neighbour():
    duration = 60.0
    segments = [
        SpeakerSegment(0.0, 25.0, "speaker_0"),
        SpeakerSegment(25.3, 25.7, "speaker_1"),
        SpeakerSegment(26.0, 60.0, "speaker_2"),
    ]
    spans = [(0.0, 60.0)]

    v1_units = _plan(segments, spans, duration)
    v1_short = [unit for unit in v1_units if unit.duration_seconds < stu.MIN_UNIT_SECONDS]
    assert v1_short and all("short-kept" in unit.flags for unit in v1_short)

    v2_units = _plan_v2(segments, spans, duration)
    assert not any(unit.duration_seconds < stu.MIN_UNIT_SECONDS for unit in v2_units)
    assert len(v2_units) == 2
    # speaker_2's span (25.85-60.0, 34.15 s) is longer than speaker_0's
    # (0-25.15, 25.15 s), so the sliver merges into speaker_2's unit.
    merged = v2_units[1]
    assert merged.speaker == "speaker_2"
    assert "cross-speaker-merge" in merged.flags
    assert "short-merged" in merged.flags
    assert "same-speaker-merge" not in merged.flags
    assert len(merged.absorbed_units) == 1
    absorbed = merged.absorbed_units[0]
    assert absorbed["speaker"] == "speaker_1"
    assert absorbed["crossed_speaker_change"] is True
    assert absorbed["duration_seconds"] == pytest.approx(0.7, abs=0.05)
    stu.assert_tiles(v2_units, duration)


def test_v2_purity_is_recomputed_to_count_the_absorbed_sliver():
    duration = 60.0
    segments = [
        SpeakerSegment(0.0, 25.0, "speaker_0"),
        SpeakerSegment(25.3, 25.7, "speaker_1"),
        SpeakerSegment(26.0, 60.0, "speaker_2"),
    ]
    v2_units = _plan_v2(segments, [(0.0, 60.0)], duration)
    merged = v2_units[1]
    assert merged.speaker_count == 2
    assert merged.speaker_share < 1.0
    # The recount is over the merged span [25.15, 60.0), by the SAME
    # attributed-time formula every unit's speaker_share uses (never wall
    # clock): speaker_1 contributes its full 0.4 s (25.3-25.7), speaker_2
    # its full 34.0 s (26.0-60.0), so the dominant share is 34.0 / 34.4,
    # not 1.0 -- the sliver it absorbed is counted, not discarded.
    assert merged.speaker_share == pytest.approx(34.0 / 34.4, abs=1e-9)


def test_v2_prefers_the_longer_same_speaker_neighbour_where_v1_always_takes_the_preceding_one():
    # Both neighbours are the SAME speaker, so rule 1 is not at stake for
    # either version -- only the neighbour CHOICE differs. v1's ``_merge_short``
    # tries the preceding neighbour first and stops there; v2 compares
    # durations and merges into the following, longer one instead.
    segments = [SpeakerSegment(0.0, 100.0, "speaker_0")]
    spans = [
        (0.0, 10.0, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (10.0, 10.5, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (10.5, 100.0, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
    ]
    v1_merged = stu._merge_short(spans, segments, "CALL", max_seconds=90.0, min_seconds=1.0)
    assert len(v1_merged) == 2
    assert v1_merged[0][:2] == (0.0, 10.5)
    assert "short-merged" in v1_merged[0][4]

    v2_merged = stu._merge_short_v2(spans, segments, "CALL", max_seconds=90.0, min_seconds=1.0)
    assert len(v2_merged) == 2
    assert v2_merged[0][:2] == (0.0, 10.0)
    assert v2_merged[1][:2] == (10.0, 100.0)
    flags = v2_merged[1][4]
    assert "same-speaker-merge" in flags
    assert "cross-speaker-merge" not in flags
    absorbed = v2_merged[1][5]
    assert absorbed == ((10.0, 10.5, "speaker_0", False),)


def test_v2_an_edge_sliver_merges_inward():
    duration = 40.6
    segments = [
        SpeakerSegment(0.4, 0.6, "speaker_0"),
        SpeakerSegment(1.0, 40.6, "speaker_1"),
    ]
    # Continuous tone over the whole call: no pause exists to compete with
    # the one turn boundary, so the only cut is at 0.8 (the gap's midpoint)
    # and the leading [0, 0.8) piece is a genuine call-edge sliver.
    units = _plan_v2(segments, [(0.0, 40.6)], duration)
    assert not any(unit.duration_seconds < stu.MIN_UNIT_SECONDS for unit in units)
    assert len(units) == 1
    assert units[0].speaker == "speaker_1"
    assert "short-merged" in units[0].flags
    assert len(units[0].absorbed_units) == 1
    assert units[0].absorbed_units[0]["start_seconds"] == pytest.approx(0.0)
    assert units[0].absorbed_units[0]["end_seconds"] == pytest.approx(0.8)
    stu.assert_tiles(units, duration)


def test_v2_tie_break_goes_to_the_preceding_neighbour():
    segments = [SpeakerSegment(0.0, 40.6, "speaker_0")]
    spans = [
        (0.0, 20.0, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (20.0, 20.6, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (20.6, 40.6, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
    ]
    merged = stu._merge_short_v2(
        spans, segments, "CALL", max_seconds=stu.MAX_UNIT_SECONDS, min_seconds=stu.MIN_UNIT_SECONDS
    )
    assert len(merged) == 2
    assert merged[0][:2] == (0.0, 20.6)
    assert merged[1][:2] == (20.6, 40.6)


def test_v2_cap_still_holds_and_tries_the_other_neighbour():
    # The preceding neighbour is longer (89.9 s) but merging into it would
    # exceed the 90 s cap; the shorter following neighbour (5.0 s) is tried
    # instead and admits the merge.
    segments = [SpeakerSegment(0.0, 95.2, "speaker_0")]
    spans = [
        (0.0, 89.9, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (89.9, 90.2, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (90.2, 95.2, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
    ]
    merged = stu._merge_short_v2(
        spans, segments, "CALL", max_seconds=stu.MAX_UNIT_SECONDS, min_seconds=stu.MIN_UNIT_SECONDS
    )
    assert len(merged) == 2
    assert merged[0][:2] == (0.0, 89.9)
    assert merged[1][:2] == (89.9, 95.2)
    assert all(end - start <= stu.MAX_UNIT_SECONDS + 1e-6 for start, end, *_ in merged)


def test_v2_both_neighbours_over_cap_keeps_the_sliver_short_kept():
    segments = [SpeakerSegment(0.0, 180.1, "speaker_0")]
    spans = [
        (0.0, 89.9, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (89.9, 90.2, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
        (90.2, 180.1, stu.CUT_PAUSE, stu.CUT_PAUSE, ()),
    ]
    merged = stu._merge_short_v2(
        spans, segments, "CALL", max_seconds=stu.MAX_UNIT_SECONDS, min_seconds=stu.MIN_UNIT_SECONDS
    )
    assert len(merged) == 3
    kept = merged[1]
    assert kept[:2] == (89.9, 90.2)
    assert "short-kept" in kept[4]
    assert "short-merged" not in kept[4]


def test_unit_as_dict_carries_no_absorbed_units_key_but_unit_v2_does():
    kwargs = dict(
        sample_id="CALL",
        unit_index=1,
        start_seconds=0.0,
        end_seconds=10.0,
        speaker="speaker_0",
        speaker_share=1.0,
        speaker_count=1,
        start_cut=stu.CUT_CALL_START,
        end_cut=stu.CUT_CALL_END,
        ends_active=False,
        flags=(),
    )
    assert "absorbed_units" not in stu.Unit(**kwargs).as_dict()
    v2_unit = stu.UnitV2(**kwargs, absorbed_units=({"start_seconds": 1.0},))
    document = v2_unit.as_dict()
    assert document["absorbed_units"] == [{"start_seconds": 1.0}]


def test_rules_block_v2_names_the_new_rule_and_leaves_v1s_untouched():
    v1_rules = stu.rules_block()
    v2_rules = stu.rules_block_v2()
    assert "min_unit_merge_rule" not in v1_rules
    assert v2_rules["min_unit_merge_rule"]
    assert {key: v2_rules[key] for key in v1_rules} == v1_rules


def test_plan_document_and_summary_document_default_to_v1_but_accept_v2_overrides():
    v1_document = stu.plan_document(
        carrier_lock_key="k",
        split_identity_hash="h",
        source_run_id="r",
        source_attempt_id="a",
        diarization_run_id="d",
        window_rows_sha256="w",
        calls=[],
        corpus={},
    )
    assert v1_document["schema"] == stu.PLAN_SCHEMA
    assert v1_document["exposure_row"] == stu.EXPOSURE_ROW
    assert "min_unit_merge_rule" not in v1_document["rules"]

    v2_document = stu.plan_document(
        carrier_lock_key="k",
        split_identity_hash="h",
        source_run_id="r",
        source_attempt_id="a",
        diarization_run_id="d",
        window_rows_sha256="w",
        calls=[],
        corpus={},
        schema=stu.PLAN_SCHEMA_V2,
        exposure_row=stu.EXPOSURE_ROW_V2,
        rules=stu.rules_block_v2(),
    )
    assert v2_document["schema"] == stu.PLAN_SCHEMA_V2
    assert v2_document["exposure_row"] == stu.EXPOSURE_ROW_V2
    assert v2_document["rules"]["min_unit_merge_rule"]

    v1_summary = stu.summary_document(
        plan_path="p", plan_sha256="s", elapsed_seconds=1.0, corpus={}, per_call=[]
    )
    assert v1_summary["schema"] == stu.SUMMARY_SCHEMA
    assert v1_summary["exposure_row"] == stu.EXPOSURE_ROW

    v2_summary = stu.summary_document(
        plan_path="p",
        plan_sha256="s",
        elapsed_seconds=1.0,
        corpus={},
        per_call=[],
        schema=stu.SUMMARY_SCHEMA_V2,
        exposure_row=stu.EXPOSURE_ROW_V2,
        rules=stu.rules_block_v2(),
    )
    assert v2_summary["schema"] == stu.SUMMARY_SCHEMA_V2
    assert v2_summary["exposure_row"] == stu.EXPOSURE_ROW_V2


def test_v2_call_summary_reports_merges_via_the_generic_flag_counts():
    duration = 60.0
    segments = [
        SpeakerSegment(0.0, 25.0, "speaker_0"),
        SpeakerSegment(25.3, 25.7, "speaker_1"),
        SpeakerSegment(26.0, 60.0, "speaker_2"),
    ]
    units = _plan_v2(segments, [(0.0, 60.0)], duration)
    summary = stu.call_summary("CALL", units, duration, window_count=1)
    assert summary["units_under_1s"] == 0
    assert summary["flags"].get("cross-speaker-merge") == 1
    assert summary["flags"].get("short-merged") == 1
    assert "short-kept" not in summary["flags"]


# ---------------------------------------------------------------------------
# rule 5 and the tiling proof
# ---------------------------------------------------------------------------


def test_the_tail_changes_delivered_seconds_and_not_the_cut():
    duration = 40.0
    segments = [SpeakerSegment(0.0, 40.0, "speaker_0")]
    units = _plan(segments, [(0.0, 40.0)], duration)
    unit = units[0]
    assert unit.duration_seconds == pytest.approx(40.0)
    assert unit.delivered_seconds == pytest.approx(40.0 + stu.TAIL_SILENCE_SECONDS)


def test_the_plan_tiles_the_call_exactly():
    duration = 300.0
    segments = [
        SpeakerSegment(0.0, 100.0, "speaker_0"),
        SpeakerSegment(101.0, 200.0, "speaker_1"),
        SpeakerSegment(201.0, 300.0, "speaker_2"),
    ]
    units = _plan(
        segments, [(0.0, 100.0), (101.0, 200.0), (201.0, 300.0)], duration
    )
    stu.assert_tiles(units, duration)
    assert sum(unit.duration_seconds for unit in units) == pytest.approx(duration)


def test_a_broken_tiling_is_refused_rather_than_reported():
    unit = stu.Unit(
        sample_id="CALL",
        unit_index=1,
        start_seconds=0.0,
        end_seconds=10.0,
        speaker="speaker_0",
        speaker_share=1.0,
        speaker_count=1,
        start_cut=stu.CUT_CALL_START,
        end_cut=stu.CUT_CALL_END,
        ends_active=False,
        flags=(),
    )
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.assert_tiles([unit], 20.0)


def test_a_call_with_no_diarized_speech_still_produces_one_unit():
    duration = 30.0
    units = _plan([], [(0.0, 30.0)], duration)
    assert len(units) == 1
    assert units[0].speaker is None
    assert units[0].speaker_count == 0


def test_a_silent_unit_is_counted_as_silent_and_never_as_a_pure_one():
    duration = 30.0
    units = _plan([], [(0.0, 30.0)], duration)
    summary = stu.call_summary("CALL", units, duration, window_count=1)
    assert summary["silent_units"] == 1
    assert summary["single_speaker_units"] == 0


# ---------------------------------------------------------------------------
# reference-word attribution
# ---------------------------------------------------------------------------


def _rows(counts, window_seconds=90.0):
    return [
        {
            "start_seconds": index * window_seconds,
            "end_seconds": (index + 1) * window_seconds,
            "reference_words": count,
        }
        for index, count in enumerate(counts)
    ]


def _units_at(edges, duration):
    units = []
    bounds = [0.0, *edges, duration]
    for index in range(len(bounds) - 1):
        units.append(
            stu.Unit(
                sample_id="CALL",
                unit_index=index + 1,
                start_seconds=bounds[index],
                end_seconds=bounds[index + 1],
                speaker="speaker_0",
                speaker_share=1.0,
                speaker_count=1,
                start_cut=stu.CUT_CALL_START,
                end_cut=stu.CUT_CALL_END,
                ends_active=False,
                flags=(),
            )
        )
    return units


def test_the_reference_partition_sums_to_the_sealed_total_exactly():
    rows = _rows([200, 180, 220])
    units = _units_at([45.0, 130.0, 200.0], 270.0)
    ranges = stu.reference_word_partition(units, rows)
    assert ranges[0][0] == 0
    assert ranges[-1][1] == 600
    assert sum(high - low for low, high in ranges) == 600


def test_the_partition_is_exact_at_a_window_boundary():
    rows = _rows([200, 180, 220])
    units = _units_at([90.0, 180.0], 270.0)
    ranges = stu.reference_word_partition(units, rows)
    assert ranges == ((0, 200), (200, 380), (380, 600))


def test_the_ranges_are_contiguous_and_non_decreasing():
    rows = _rows([200, 0, 220])
    units = _units_at([10.0, 95.0, 100.0, 250.0], 270.0)
    ranges = stu.reference_word_partition(units, rows)
    for previous, following in zip(ranges, ranges[1:]):
        assert previous[1] == following[0]
        assert following[1] >= following[0]


def test_a_call_with_no_window_rows_is_refused():
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.reference_word_partition(_units_at([], 90.0), [])


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------


def test_the_call_summary_reports_the_cut_kinds_and_the_delivered_delta():
    duration = 40.0
    segments = [
        SpeakerSegment(0.0, 18.0, "speaker_0"),
        SpeakerSegment(21.0, 40.0, "speaker_1"),
    ]
    units = _plan(segments, [(0.0, 18.0), (21.0, 40.0)], duration)
    summary = stu.call_summary("CALL", units, duration, window_count=1)
    assert summary["units"] == 2
    assert summary["cut_seconds"] == pytest.approx(duration)
    assert summary["delivered_seconds"] == pytest.approx(
        duration + 2 * stu.TAIL_SILENCE_SECONDS
    )
    assert summary["window_delivered_seconds"] == pytest.approx(duration)


def test_the_corpus_summary_pools_counts_then_divides_once():
    rows = [
        {
            "units": 3,
            "windows": 2,
            "cut_seconds": 120.0,
            "delivered_seconds": 126.0,
            "window_delivered_seconds": 120.0,
            "ends_pause": 2,
            "ends_turn_boundary": 0,
            "ends_forced": 0,
            "ends_call_end": 1,
            "ends_on_active_frame": 1,
            "single_speaker_units": 3,
            "silent_units": 0,
            "units_under_1s": 0,
            "reference_words": 300,
            "units_with_no_reference_words": 0,
            "flags": {"short-kept": 1},
        },
        {
            "units": 2,
            "windows": 1,
            "cut_seconds": 80.0,
            "delivered_seconds": 84.0,
            "window_delivered_seconds": 80.0,
            "ends_pause": 1,
            "ends_turn_boundary": 0,
            "ends_forced": 0,
            "ends_call_end": 1,
            "ends_on_active_frame": 0,
            "single_speaker_units": 2,
            "silent_units": 1,
            "units_under_1s": 1,
            "reference_words": 200,
            "units_with_no_reference_words": 1,
            "flags": {"short-kept": 2},
        },
    ]
    pooled = stu.corpus_summary(rows)
    assert pooled["calls"] == 2
    assert pooled["units"] == 5
    assert pooled["delivered_delta_seconds"] == pytest.approx(10.0)
    assert pooled["mean_unit_seconds"] == pytest.approx(40.0)
    assert pooled["flags"] == {"short-kept": 3}
    assert pooled["silent_units"] == 1
    assert pooled["units_under_1s"] == 1


def test_pooling_no_calls_is_refused():
    with pytest.raises(stu.SpeakerTurnUnitError):
        stu.corpus_summary([])
