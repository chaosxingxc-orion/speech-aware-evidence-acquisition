"""Earnings-21 SPEAKER-TURN UNITS: the OBS-E1 transport unit, cut model-free.

The problem this solves
-----------------------
The sealed full-44 direct baseline transports each call as ``ceil(D / 90)`` fixed
90-second windows. A fixed cut has no reason to land in a pause and does not: the
2026-09-07 cross-carrier silence-tail preregistration measured **1,043 of the 1,593
buf90 windows (65.5 %) ending on an ACTIVE frame**, and **1,088 of the 1,549
INTERIOR windows (70.2 %) ending within 20 ms of active speech**. A window also
mixes speakers -- the sealed diarization artifact puts 943 of the 1,593 windows at
two or more speakers. So the unit the core is asked to understand is neither a
complete utterance nor one person's, and its semantic constraint drifts.

The owner's thesis for OBS-E1 is to cut by SPEAKER first and understand per
speaker. This module builds that unit, from two already-sealed inputs and nothing
else:

* the anonymous ``(start, end, speaker)`` segments of ``saea-diarization-v1``
  (``reproduction.diarization``), which carry no text and no identity, and
* an energy-based pause detector over the sealed 90-second obs-slices, reusing
  ``analysis.e22_clip_boundary.frame_rms_dbfs`` at its committed settings so the
  activity notion here and the activity notion in the 65.5 % measurement are the
  same function.

Model-free by construction: no frozen core, no diarizer re-run, no GPU, no
embedder, no tokenizer, no network. The PCM reads reduce samples to frame energies
and throw them away.

The five rules, in the order they are applied
----------------------------------------------
1. **Never cross a diarized speaker change.** The base partition is the diarized
   turn: consecutive segments of the same speaker are one turn, and a boundary is
   placed between two turns (at the midpoint of their gap, or at the incoming
   speaker's onset when the two overlap).
2. **Never end inside active speech.** Each interior boundary is snapped to the
   midpoint of the nearest pause of at least :data:`PAUSE_MIN_SECONDS` whose
   midpoint lies within :data:`SNAP_RADIUS_SECONDS` of it -- the study's own sealed
   ``obs_silence_snap_seconds`` radius. A boundary with no such pause stays where
   the turn change put it and is reported as a ``turn-boundary`` cut rather than
   quietly counted as a clean one.
3. **Cap at 90 s.** A unit longer than :data:`MAX_UNIT_SECONDS` is split at its
   LONGEST internal pause, recursively. A monologue with no admissible internal
   pause is split at exactly 90 s and flagged ``forced-cap-split``; that is a
   defect of the audio, and it is counted rather than hidden.
4. **Minimum 1.0 s.** A unit shorter than :data:`MIN_UNIT_SECONDS` merges into an
   adjacent unit with the SAME dominant speaker across a boundary that is not a
   speaker change (so rule 1 survives the merge) and whose result still fits the
   cap. Otherwise it is kept as its own unit and flagged ``short-kept`` -- a
   backchannel between two other speakers has no same-speaker neighbour by
   construction, and inventing one would cross a speaker change.
5. **A 2.0-second digital silence tail**, the admitted Earnings-22 convention,
   on the DELIVERED media only. The cut, the span and the tiling are untouched;
   :attr:`Unit.delivered_seconds` is ``duration_seconds + TAIL_SILENCE_SECONDS``.

What the plan is, and what it is not
-------------------------------------
The output is a PARTITION of every call: units tile ``[0, decoded_duration)`` with
no gap and no overlap, which :func:`assert_tiles` proves before any statistic is
computed. Total cut audio therefore equals the call's own duration exactly, and the
only delivered-audio delta against the 1,593 windows is the tail times the unit
count (§ :func:`call_summary`).

Reference words are attributed to units WITHOUT opening a reference transcript.
The sealed ``SAEA-E21-MF-WINDOW-PAIRING-V1`` rows give, per 90-second window, the
number of whole-string-normalized reference words the scorer's own alignment
charged to it. Cumulating those counts gives a monotone map from window boundary
TIME to reference-word INDEX; :func:`reference_word_partition` interpolates it
linearly inside a window and rounds, so consecutive units get consecutive
half-open index ranges that sum to the call's own reference-word total exactly.
It is exact at every window boundary and an interpolation inside one -- an
attribution, never a timestamped alignment, and it is labelled that way wherever
it is reported.

Nothing here decides anything and nothing here licenses a flight. It builds a
transport unit and writes receipts; flying it needs the obs seam, its own
preregistration, its own exposure row and the owner's GO.

OBS-E1 UNIT PLAN v2 (coordinator's decision, 2026-09-08)
---------------------------------------------------------
v1's rule 4 keeps a sub-1.0-s sliver as its own unit whenever both its
neighbours belong to a different diarized speaker -- rule 1 ("never cross a
diarized speaker change") admits no exception, so a backchannel and a bare
diarizer artifact are indistinguishable and both are kept and flagged
``short-kept``. The v1 receipt shows the cost: 166 of 5,288 units are under
1.0 s, all of them ``short-kept``, and the shortest is 0.001 s -- a 16-sample
sliver that, wrapped in the 2.0-second delivered tail, would cost one whole
contact to say nothing. The coordinator's ruling: "a 16-sample unit wrapped
in a 2-second tail is a diarizer artifact, not a transport unit."

Plan v2 (schema :data:`PLAN_SCHEMA_V2`, built by :func:`plan_units_v2`)
keeps rules 1-3 and 5 of v1 BYTE FOR BYTE (:func:`_base_spans` is the one
piece of code both builders call) and replaces rule 4 with ONE exception to
rule 1: a span shorter than :data:`MIN_UNIT_SECONDS` now merges into
whichever ADJACENT unit is LONGER, of either speaker, ties going to the
PRECEDING neighbour -- crossing a diarized speaker change if that is the
only way to absorb it. The 90 s cap still holds: a merge that would exceed
it tries the other neighbour, and a sliver with no admissible neighbour on
either side is kept and flagged ``short-kept``, exactly as in v1, and is
expected to be rare to none. The merged unit's speaker facts are recomputed
over its own new span (the same ``window_speakers`` call v1 already makes),
so its ``speaker``/``speaker_share``/``speaker_count`` already count the
absorbed sliver; :class:`UnitV2` additionally records every absorbed sliver
(``absorbed_units``: span, original speaker, whether absorbing it crossed a
speaker change) so a later reader never has to re-derive what a merge did
from the final span alone. :func:`plan_units` (v1) is untouched: it still
calls the same :func:`_base_spans` helper and its own unchanged
:func:`_merge_short`, so a v1 build reproduces the committed
``e21-speaker-turn-units-v1.json`` byte for byte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..reproduction.diarization import SpeakerSegment, window_speakers

#: Frame geometry and the activity gate, imported in spirit from
#: ``analysis.e22_clip_boundary`` (whose ``frame_rms_dbfs`` this module calls) so
#: "active" means here exactly what it meant in the 65.5 % measurement.
FRAME_MS = 20
PEAK_DROP_DB = 30.0
ABSOLUTE_FLOOR_DBFS = -55.0

#: A silence has to last this long to be a PAUSE a cut may be moved onto.
PAUSE_MIN_SECONDS = 0.300

#: How far a turn boundary may travel to reach a pause. 2.0 s is the study's own
#: sealed ``obs_silence_snap_seconds``, not a fresh number.
SNAP_RADIUS_SECONDS = 2.0

#: The transport cap: one unit is never longer than one sealed window.
MAX_UNIT_SECONDS = 90.0

#: Shorter than this and a unit is a fragment, not an utterance.
MIN_UNIT_SECONDS = 1.0

#: The admitted Earnings-22 convention, on the DELIVERED media only.
TAIL_SILENCE_SECONDS = 2.0

#: ``<sample_id>#u<index>`` -- the unit twin of ``e21_window_pairing``'s window id,
#: so ``call_of`` is the same one-liner on both.
UNIT_ID_SEPARATOR = "#u"

PLAN_SCHEMA = "saea-e21-speaker-turn-units-v1"

#: The coordinator's 2026-09-08 rule-4 replacement (module docstring, "OBS-E1
#: UNIT PLAN v2" section). Built by :func:`plan_units_v2`; v1's own schema and
#: builder are untouched.
PLAN_SCHEMA_V2 = "saea-e21-speaker-turn-units-v2"

#: Cut kinds, reported per boundary so a verdict can separate a clean cut from one
#: the audio refused to give.
CUT_PAUSE = "pause"
CUT_TURN_BOUNDARY = "turn-boundary"
CUT_CALL_START = "call-start"
CUT_CALL_END = "call-end"
CUT_FORCED = "forced-cap-split"

_EPSILON = 1e-9


class SpeakerTurnUnitError(RuntimeError):
    """A unit plan input is malformed, or a plan failed its own tiling proof."""


def unit_id(sample_id: str, index: int) -> str:
    if not isinstance(sample_id, str) or not sample_id or UNIT_ID_SEPARATOR in sample_id:
        raise SpeakerTurnUnitError(f"sample id {sample_id!r} cannot carry a unit suffix")
    if isinstance(index, bool) or not isinstance(index, int) or index < 1:
        raise SpeakerTurnUnitError("unit index must be a positive integer")
    return f"{sample_id}{UNIT_ID_SEPARATOR}{index:04d}"


def call_of(identifier: str) -> str:
    """The cluster key of a unit id -- the ``cluster_of`` callable an OBS-E1 paired
    read passes to ``analysis.paired``, identical in shape to the window one."""

    head, separator, _tail = identifier.partition(UNIT_ID_SEPARATOR)
    if not separator or not head:
        raise SpeakerTurnUnitError(f"{identifier!r} is not a unit id")
    return head


# ---------------------------------------------------------------------------
# 1. Activity and pauses, from the sealed slices' own samples.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pause:
    """A maximal run of inactive frames, in call time."""

    start_seconds: float
    end_seconds: float

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def midpoint_seconds(self) -> float:
        return 0.5 * (self.start_seconds + self.end_seconds)


def activate(
    levels,
    *,
    peak_drop_db: float = PEAK_DROP_DB,
    absolute_floor_dbfs: float = ABSOLUTE_FLOOR_DBFS,
):
    """Active flags for ONE window's frame levels.

    A frame is ACTIVE when its RMS is within ``peak_drop_db`` of that window's own
    peak and above the absolute floor -- byte for byte the gate
    ``e22_clip_boundary.energy_margins`` applies to one clip, which is what makes
    the unit-level ``ends_on_active_frame`` count comparable to the sealed 65.5 %
    window-end figure. A WHOLE-CALL threshold would let a loud passage silence a
    quiet one forty minutes later, which is why the gate stays per window.
    """

    import numpy as np  # noqa: PLC0415 (numpy stays a function-local import here)

    if levels.size == 0:
        return np.zeros(0, dtype=bool)
    threshold = max(float(levels.max()) - peak_drop_db, absolute_floor_dbfs)
    return levels >= threshold


def frame_activity(
    samples,
    sample_rate: int,
    window_frames: Sequence[tuple[int, int]],
    *,
    frame_ms: int = FRAME_MS,
    peak_drop_db: float = PEAK_DROP_DB,
    absolute_floor_dbfs: float = ABSOLUTE_FLOOR_DBFS,
):
    """Per-frame active/inactive over a whole call, thresholded PER WINDOW.

    ``window_frames`` gives each sealed 90-second window's half-open frame range.
    The runner never needs this form -- a sealed slice IS a window, so it frames
    and thresholds slice by slice through :func:`activate` and concatenates, which
    is identical because 90.0 s at 16 kHz is exactly 4,500 whole frames. This
    whole-call form exists so the equivalence is testable on one array.
    """

    import numpy as np  # noqa: PLC0415

    from .e22_clip_boundary import frame_rms_dbfs  # noqa: PLC0415

    frame_length = max(1, int(round(sample_rate * frame_ms / 1000.0)))
    levels = frame_rms_dbfs(samples, frame_length)
    active = np.zeros(int(levels.size), dtype=bool)
    if levels.size == 0:
        return active, levels, frame_length / sample_rate
    covered = 0
    for start, end in window_frames:
        lo = max(0, int(start))
        hi = min(int(levels.size), int(end))
        if hi <= lo:
            continue
        active[lo:hi] = activate(
            levels[lo:hi],
            peak_drop_db=peak_drop_db,
            absolute_floor_dbfs=absolute_floor_dbfs,
        )
        covered += hi - lo
    if covered != int(levels.size):
        raise SpeakerTurnUnitError(
            f"the window frame ranges cover {covered} of {int(levels.size)} frames; "
            "a call's windows must tile its frames"
        )
    return active, levels, frame_length / sample_rate


def window_frame_ranges(
    window_bounds: Sequence[tuple[float, float]], sample_rate: int, frame_length: int
) -> tuple[tuple[int, int], ...]:
    """Each window's half-open frame range, from its sealed time bounds."""

    ranges: list[tuple[int, int]] = []
    for start, end in window_bounds:
        ranges.append(
            (
                int(math.floor(start * sample_rate / frame_length)),
                int(math.floor(end * sample_rate / frame_length)),
            )
        )
    return tuple(ranges)


def activity_from_sealed_slices(
    data_root, slices: Sequence[Mapping[str, object]], *, expect_rate: int = 16_000
):
    """Frame activity over one whole call, read slice by slice off the sealed WAVs.

    Each slice's SHA-256 is re-verified against its sealed ``obs-derivation``
    record before a sample is read, so a plan can never be cut from bytes that
    are not the ones the flight observed.

    A sealed slice IS a 90-second window, and 90.0 s at 16 kHz is exactly 4,500
    whole frames, so framing each slice and concatenating is identical to framing
    the whole call -- and it never materializes a forty-minute float64 array.
    """

    import hashlib  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    from .e22_clip_boundary import frame_rms_dbfs, read_wav_int16  # noqa: PLC0415

    frame_length = int(round(expect_rate * FRAME_MS / 1000.0))
    blocks = []
    for record in slices:
        if int(record["sample_rate_hz"]) != expect_rate:
            raise SpeakerTurnUnitError(f"slice {record['media_relpath']} is not {expect_rate} Hz")
        path = Path(data_root) / str(record["media_relpath"])
        if hashlib.sha256(path.read_bytes()).hexdigest() != record["sha256"]:
            raise SpeakerTurnUnitError(f"sealed slice {path} does not match its receipt SHA-256")
        samples, rate = read_wav_int16(path)
        if rate != expect_rate:
            raise SpeakerTurnUnitError(f"slice {path} decodes at {rate} Hz")
        blocks.append(activate(frame_rms_dbfs(samples, frame_length)))
    active = np.concatenate(blocks) if blocks else np.zeros(0, dtype=bool)
    return active, frame_length / expect_rate


def pauses_from_activity(
    active, frame_seconds: float, *, min_seconds: float = PAUSE_MIN_SECONDS
) -> tuple[Pause, ...]:
    """Every maximal inactive run of at least ``min_seconds``, in call time."""

    pauses: list[Pause] = []
    run_start: int | None = None
    total = len(active)
    for index in range(total + 1):
        inactive = index < total and not bool(active[index])
        if inactive and run_start is None:
            run_start = index
        elif not inactive and run_start is not None:
            start = run_start * frame_seconds
            end = index * frame_seconds
            if end - start >= min_seconds - _EPSILON:
                pauses.append(Pause(start_seconds=start, end_seconds=end))
            run_start = None
    return tuple(pauses)


def ends_on_active_frame(active, frame_seconds: float, end_seconds: float) -> bool:
    """Is the frame the cut falls in an ACTIVE one? The unit-level mirror of the
    sealed window-end audit's headline number."""

    if len(active) == 0:
        return False
    index = int(math.floor((end_seconds - _EPSILON) / frame_seconds))
    index = min(max(index, 0), len(active) - 1)
    return bool(active[index])


# ---------------------------------------------------------------------------
# 2. Turns -> boundaries -> units.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Unit:
    """One speaker-turn unit: a half-open span of call time and how it was cut."""

    sample_id: str
    unit_index: int
    start_seconds: float
    end_seconds: float
    speaker: str | None
    speaker_share: float
    speaker_count: int
    start_cut: str
    end_cut: str
    ends_active: bool
    flags: tuple[str, ...]

    @property
    def identifier(self) -> str:
        return unit_id(self.sample_id, self.unit_index)

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def delivered_seconds(self) -> float:
        return self.duration_seconds + TAIL_SILENCE_SECONDS

    def as_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.identifier,
            "sample_id": self.sample_id,
            "unit_index": self.unit_index,
            "start_seconds": round(self.start_seconds, 6),
            "end_seconds": round(self.end_seconds, 6),
            "duration_seconds": round(self.duration_seconds, 6),
            "delivered_seconds": round(self.delivered_seconds, 6),
            "speaker": self.speaker,
            "speaker_share": round(self.speaker_share, 6),
            "speaker_count": self.speaker_count,
            "start_cut": self.start_cut,
            "end_cut": self.end_cut,
            "ends_on_active_frame": self.ends_active,
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class UnitV2(Unit):
    """A v2 unit: everything :class:`Unit` carries, plus every sub-1.0-s
    sliver the coordinator's rule 4 (module docstring, "OBS-E1 UNIT PLAN v2")
    absorbed into it. Empty for a unit no merge ever touched.

    Each entry of ``absorbed_units`` is ``{"start_seconds", "end_seconds",
    "duration_seconds", "speaker", "crossed_speaker_change"}`` -- the
    sliver's OWN span and dominant speaker before it was absorbed, and
    whether absorbing it crossed a diarized speaker change. The surviving
    unit's own ``speaker``/``speaker_share``/``speaker_count`` are computed
    the same way v1's are, over the merged span, so they already count every
    absorbed sliver; this field is a record of the merge, not a correction.
    """

    absorbed_units: tuple[dict[str, object], ...] = ()

    def as_dict(self) -> dict[str, object]:
        document = super().as_dict()
        document["absorbed_units"] = [dict(item) for item in self.absorbed_units]
        return document


def turns(segments: Sequence[SpeakerSegment]) -> tuple[tuple[str, float, float], ...]:
    """Consecutive same-speaker segments collapsed into ``(speaker, start, end)``."""

    ordered = sorted(segments, key=lambda s: (s.start_seconds, s.end_seconds))
    collapsed: list[list[object]] = []
    for segment in ordered:
        if collapsed and collapsed[-1][0] == segment.speaker:
            collapsed[-1][2] = max(float(collapsed[-1][2]), segment.end_seconds)
        else:
            collapsed.append([segment.speaker, segment.start_seconds, segment.end_seconds])
    return tuple((str(a), float(b), float(c)) for a, b, c in collapsed)


def turn_boundaries(segments: Sequence[SpeakerSegment]) -> tuple[float, ...]:
    """Where the floor changes hands: the midpoint of the gap between two turns,
    or the incoming speaker's onset when the two overlap."""

    grouped = turns(segments)
    boundaries: list[float] = []
    for previous, following in zip(grouped, grouped[1:]):
        _prev_speaker, _prev_start, prev_end = previous
        _next_speaker, next_start, _next_end = following
        boundaries.append(
            0.5 * (prev_end + next_start) if next_start >= prev_end else next_start
        )
    return tuple(boundaries)


def snap_to_pause(
    boundary: float,
    pauses: Sequence[Pause],
    *,
    radius: float = SNAP_RADIUS_SECONDS,
) -> tuple[float, str]:
    """Move a boundary to the nearest qualifying pause's midpoint, or leave it.

    Ties (two pauses equidistant) go to the EARLIER one, so the result cannot
    depend on iteration order.
    """

    best: tuple[float, float] | None = None
    for pause in pauses:
        distance = abs(pause.midpoint_seconds - boundary)
        if distance > radius + _EPSILON:
            continue
        if best is None or distance < best[0] - _EPSILON:
            best = (distance, pause.midpoint_seconds)
    if best is None:
        return boundary, CUT_TURN_BOUNDARY
    return best[1], CUT_PAUSE


def _longest_pause_within(
    pauses: Sequence[Pause], start: float, end: float, *, margin: float
) -> Pause | None:
    """The longest pause whose midpoint leaves both halves at least ``margin``."""

    best: Pause | None = None
    for pause in pauses:
        centre = pause.midpoint_seconds
        if centre < start + margin - _EPSILON or centre > end - margin + _EPSILON:
            continue
        if best is None or pause.duration_seconds > best.duration_seconds + _EPSILON:
            best = pause
    return best


def _cap_split(
    spans: Sequence[tuple[float, float, str, str, tuple[str, ...]]],
    pauses: Sequence[Pause],
    *,
    max_seconds: float,
    min_seconds: float,
) -> list[tuple[float, float, str, str, tuple[str, ...]]]:
    """Rule 3: recursively split any span longer than the cap."""

    output: list[tuple[float, float, str, str, tuple[str, ...]]] = []
    pending = list(spans)
    while pending:
        start, end, start_cut, end_cut, flags = pending.pop(0)
        if end - start <= max_seconds + _EPSILON:
            output.append((start, end, start_cut, end_cut, flags))
            continue
        pause = _longest_pause_within(pauses, start, end, margin=min_seconds)
        if pause is not None:
            centre = pause.midpoint_seconds
            split_cut = CUT_PAUSE
            split_flags: tuple[str, ...] = ()
        else:
            centre = start + max_seconds
            split_cut = CUT_FORCED
            split_flags = ("forced-cap-split",)
        left = (start, centre, start_cut, split_cut, tuple(sorted(set(flags + split_flags))))
        right = (centre, end, split_cut, end_cut, tuple(sorted(set(flags + split_flags))))
        # BOTH halves go back on the queue: splitting at the longest pause can
        # leave the LEFT piece over the cap too, and a one-sided recursion would
        # emit it. Each split removes at least ``min_seconds``, so this ends.
        pending.insert(0, right)
        pending.insert(0, left)
    return sorted(output, key=lambda span: span[0])


def _base_spans(
    sample_id: str,
    segments: Sequence[SpeakerSegment],
    duration_seconds: float,
    pauses: Sequence[Pause],
    *,
    max_seconds: float,
    min_seconds: float,
    snap_radius: float,
) -> list[tuple[float, float, str, str, tuple[str, ...]]]:
    """Rules 1-3, shared by every plan builder (v1 and v2 alike): the
    diarized turn boundaries (rule 1), each snapped onto a nearby pause or
    left at the turn change (rule 2), then split at the 90 s cap (rule 3).
    Rule 4 -- the minimum -- is where the builders diverge and is applied by
    the caller, on the spans this returns."""

    if duration_seconds <= 0:
        raise SpeakerTurnUnitError(f"call {sample_id!r} has non-positive duration")

    # Rule 1: the diarized turn changes are the only boundaries that exist yet.
    raw = [b for b in turn_boundaries(segments) if _EPSILON < b < duration_seconds - _EPSILON]

    # Rule 2: snap each to a pause when one is close enough, keeping the sequence
    # strictly increasing -- a snap that would reorder two boundaries is reverted
    # rather than allowed to fold a unit to zero.
    snapped: list[tuple[float, str]] = []
    previous = 0.0
    for index, boundary in enumerate(raw):
        moved, kind = snap_to_pause(boundary, pauses, radius=snap_radius)
        ceiling = raw[index + 1] if index + 1 < len(raw) else duration_seconds
        if not (previous + _EPSILON < moved < ceiling - _EPSILON):
            moved, kind = boundary, CUT_TURN_BOUNDARY
        if moved <= previous + _EPSILON:
            continue
        snapped.append((moved, kind))
        previous = moved

    spans: list[tuple[float, float, str, str, tuple[str, ...]]] = []
    cursor = 0.0
    entry_cut = CUT_CALL_START
    for moved, kind in snapped:
        spans.append((cursor, moved, entry_cut, kind, ()))
        cursor, entry_cut = moved, kind
    spans.append((cursor, duration_seconds, entry_cut, CUT_CALL_END, ()))

    # Rule 3: the cap.
    return _cap_split(spans, pauses, max_seconds=max_seconds, min_seconds=min_seconds)


def plan_units(
    sample_id: str,
    segments: Sequence[SpeakerSegment],
    duration_seconds: float,
    pauses: Sequence[Pause],
    active,
    frame_seconds: float,
    *,
    max_seconds: float = MAX_UNIT_SECONDS,
    min_seconds: float = MIN_UNIT_SECONDS,
    snap_radius: float = SNAP_RADIUS_SECONDS,
) -> tuple[Unit, ...]:
    """The five rules, applied in order, to one call. Returns a TILING."""

    spans = _base_spans(
        sample_id,
        segments,
        duration_seconds,
        pauses,
        max_seconds=max_seconds,
        min_seconds=min_seconds,
        snap_radius=snap_radius,
    )

    # Rule 4: the minimum, merged only where rule 1 survives it.
    spans = _merge_short(
        spans, segments, sample_id, max_seconds=max_seconds, min_seconds=min_seconds
    )

    units: list[Unit] = []
    for index, (start, end, start_cut, end_cut, flags) in enumerate(spans, start=1):
        facts = window_speakers(
            segments,
            window_id=unit_id(sample_id, index),
            window_index=index,
            start_seconds=start,
            end_seconds=end,
        )
        units.append(
            Unit(
                sample_id=sample_id,
                unit_index=index,
                start_seconds=start,
                end_seconds=end,
                speaker=facts.dominant_speaker,
                speaker_share=facts.dominant_share,
                speaker_count=facts.speaker_count,
                start_cut=start_cut,
                end_cut=end_cut,
                ends_active=ends_on_active_frame(active, frame_seconds, end),
                flags=flags,
            )
        )
    assert_tiles(units, duration_seconds)
    return tuple(units)


def _dominant(segments: Sequence[SpeakerSegment], sample_id: str, start: float, end: float):
    return window_speakers(
        segments,
        window_id=unit_id(sample_id, 1),
        window_index=1,
        start_seconds=start,
        end_seconds=end,
    ).dominant_speaker


def _merge_short(
    spans: Sequence[tuple[float, float, str, str, tuple[str, ...]]],
    segments: Sequence[SpeakerSegment],
    sample_id: str,
    *,
    max_seconds: float,
    min_seconds: float,
) -> list[tuple[float, float, str, str, tuple[str, ...]]]:
    """Rule 4. A short span joins a neighbour only when the neighbour's dominant
    speaker is its own AND the boundary between them is not a speaker change AND
    the merged span still fits the cap; otherwise it stays and is flagged."""

    working = [list(span) for span in spans]
    index = 0
    while index < len(working):
        start, end, start_cut, end_cut, flags = working[index]
        if end - start >= min_seconds - _EPSILON:
            index += 1
            continue
        speaker = _dominant(segments, sample_id, start, end)
        merged = False
        for neighbour in (index - 1, index + 1):
            if not 0 <= neighbour < len(working):
                continue
            shared_cut = start_cut if neighbour < index else end_cut
            if shared_cut == CUT_TURN_BOUNDARY:
                continue
            n_start, n_end, n_start_cut, n_end_cut, n_flags = working[neighbour]
            if _dominant(segments, sample_id, n_start, n_end) != speaker:
                continue
            if max(n_end, end) - min(n_start, start) > max_seconds + _EPSILON:
                continue
            combined = (
                min(n_start, start),
                max(n_end, end),
                n_start_cut if neighbour < index else start_cut,
                end_cut if neighbour < index else n_end_cut,
                tuple(sorted(set(tuple(flags) + tuple(n_flags) + ("short-merged",)))),
            )
            low = min(index, neighbour)
            working[low : low + 2] = [list(combined)]
            index = max(low - 1, 0)
            merged = True
            break
        if not merged:
            working[index][4] = tuple(sorted(set(tuple(flags) + ("short-kept",))))
            index += 1
    return [(a, b, c, d, tuple(e)) for a, b, c, d, e in working]


#: ``(sliver_start, sliver_end, sliver_speaker, crossed_speaker_change)``.
#: ``sliver_speaker`` is ``str | None`` at runtime; left as ``object`` here so
#: this module-level alias needs no forward reference.
_AbsorbedSliver = tuple[float, float, object, bool]
_SpanV2 = tuple[float, float, str, str, tuple[str, ...], tuple[_AbsorbedSliver, ...]]


def _merge_short_v2(
    spans: Sequence[tuple[float, float, str, str, tuple[str, ...]]],
    segments: Sequence[SpeakerSegment],
    sample_id: str,
    *,
    max_seconds: float,
    min_seconds: float,
) -> list[_SpanV2]:
    """Rule 4, v2 (module docstring, "OBS-E1 UNIT PLAN v2"): a short span
    merges into whichever ADJACENT span is LONGER -- of either speaker --
    ties going to the PRECEDING neighbour (index - 1 always sorts before
    index + 1, so a plain stable sort by duration already gives that tie
    break). This is the one, explicit exception to rule 1's "never cross a
    diarized speaker change".

    The 90 s cap still holds: a candidate neighbour whose merge would exceed
    it is dropped before the longer-wins comparison, so the OTHER neighbour
    is tried instead; a span with no admissible neighbour on either side
    keeps its sliver and is flagged ``short-kept``, exactly as v1 flags a
    backchannel it cannot merge.

    Every merge is recorded as an ``(sliver_start, sliver_end,
    sliver_speaker, crossed_speaker_change)`` tuple on the surviving span, so
    the final unit can report every sliver it absorbed. A span that absorbed
    at least one crossing sliver is flagged ``cross-speaker-merge``; one
    whose absorptions were all same-speaker (exactly what v1 would also have
    merged) is flagged ``same-speaker-merge`` instead -- the two are mutually
    exclusive per unit, so a receipt can just sum ``flags``.
    """

    working: list[list[object]] = [list(span) + [tuple()] for span in spans]
    index = 0
    while index < len(working):
        start, end, start_cut, end_cut, flags, absorbed = working[index]
        if end - start >= min_seconds - _EPSILON:
            index += 1
            continue
        sliver_speaker = _dominant(segments, sample_id, start, end)
        candidates: list[tuple[int, float]] = []
        for neighbour in (index - 1, index + 1):
            if not 0 <= neighbour < len(working):
                continue
            n_start, n_end = working[neighbour][0], working[neighbour][1]
            if max(n_end, end) - min(n_start, start) <= max_seconds + _EPSILON:
                candidates.append((neighbour, n_end - n_start))
        if not candidates:
            working[index][4] = tuple(sorted(set(tuple(flags) + ("short-kept",))))
            index += 1
            continue
        # The LONGER neighbour wins; a tie goes to the smaller index, which is
        # always the PRECEDING one (index - 1 < index + 1).
        candidates.sort(key=lambda item: (-item[1], item[0]))
        neighbour, _duration = candidates[0]
        n_start, n_end, n_start_cut, n_end_cut, n_flags, n_absorbed = working[neighbour]
        neighbour_speaker = _dominant(segments, sample_id, n_start, n_end)
        crossed = sliver_speaker is None or sliver_speaker != neighbour_speaker
        record: _AbsorbedSliver = (start, end, sliver_speaker, crossed)
        preceding = neighbour < index
        combined_start = min(n_start, start)
        combined_end = max(n_end, end)
        combined_start_cut = n_start_cut if preceding else start_cut
        combined_end_cut = end_cut if preceding else n_end_cut
        combined_flags = tuple(sorted(set(tuple(flags) + tuple(n_flags) + ("short-merged",))))
        combined_absorbed = (
            tuple(n_absorbed) + (record,) if preceding else (record,) + tuple(n_absorbed)
        )
        combined = [
            combined_start,
            combined_end,
            combined_start_cut,
            combined_end_cut,
            combined_flags,
            combined_absorbed,
        ]
        low = min(index, neighbour)
        working[low : low + 2] = [combined]
        # Rewind to the merged span's own new left neighbour: a merge can
        # leave that neighbour, or the merged span itself, still short.
        index = max(low - 1, 0)

    result: list[_SpanV2] = []
    for start, end, start_cut, end_cut, flags, absorbed in working:
        if "short-merged" in flags:
            crossed_any = any(item[3] for item in absorbed)
            flags = tuple(
                sorted(
                    set(flags) | {"cross-speaker-merge" if crossed_any else "same-speaker-merge"}
                )
            )
        result.append((start, end, start_cut, end_cut, flags, tuple(absorbed)))
    return result


def plan_units_v2(
    sample_id: str,
    segments: Sequence[SpeakerSegment],
    duration_seconds: float,
    pauses: Sequence[Pause],
    active,
    frame_seconds: float,
    *,
    max_seconds: float = MAX_UNIT_SECONDS,
    min_seconds: float = MIN_UNIT_SECONDS,
    snap_radius: float = SNAP_RADIUS_SECONDS,
) -> tuple[UnitV2, ...]:
    """The v2 plan (coordinator's decision, 2026-09-08; module docstring,
    "OBS-E1 UNIT PLAN v2"). Rules 1-3 and 5 are v1's, byte for byte
    (:func:`_base_spans`); rule 4 is :func:`_merge_short_v2`. Returns a
    TILING, proved by the same :func:`assert_tiles` v1 uses."""

    spans = _base_spans(
        sample_id,
        segments,
        duration_seconds,
        pauses,
        max_seconds=max_seconds,
        min_seconds=min_seconds,
        snap_radius=snap_radius,
    )
    merged = _merge_short_v2(
        spans, segments, sample_id, max_seconds=max_seconds, min_seconds=min_seconds
    )

    units: list[UnitV2] = []
    for index, (start, end, start_cut, end_cut, flags, absorbed) in enumerate(merged, start=1):
        facts = window_speakers(
            segments,
            window_id=unit_id(sample_id, index),
            window_index=index,
            start_seconds=start,
            end_seconds=end,
        )
        units.append(
            UnitV2(
                sample_id=sample_id,
                unit_index=index,
                start_seconds=start,
                end_seconds=end,
                speaker=facts.dominant_speaker,
                speaker_share=facts.dominant_share,
                speaker_count=facts.speaker_count,
                start_cut=start_cut,
                end_cut=end_cut,
                ends_active=ends_on_active_frame(active, frame_seconds, end),
                flags=flags,
                absorbed_units=tuple(
                    {
                        "start_seconds": round(a_start, 6),
                        "end_seconds": round(a_end, 6),
                        "duration_seconds": round(a_end - a_start, 6),
                        "speaker": a_speaker,
                        "crossed_speaker_change": bool(a_crossed),
                    }
                    for a_start, a_end, a_speaker, a_crossed in absorbed
                ),
            )
        )
    assert_tiles(units, duration_seconds)
    return tuple(units)


def assert_tiles(units: Sequence[Unit], duration_seconds: float) -> None:
    """The proof obligation: units cover ``[0, duration)`` with no gap, no overlap
    and no zero-length piece. Refuse to report anything about a plan that does
    not."""

    if not units:
        raise SpeakerTurnUnitError("a call must carry at least one unit")
    if abs(units[0].start_seconds) > 1e-6:
        raise SpeakerTurnUnitError(f"the first unit starts at {units[0].start_seconds}, not 0")
    if abs(units[-1].end_seconds - duration_seconds) > 1e-6:
        raise SpeakerTurnUnitError(
            f"the last unit ends at {units[-1].end_seconds}, not {duration_seconds}"
        )
    for previous, following in zip(units, units[1:]):
        if abs(previous.end_seconds - following.start_seconds) > 1e-6:
            raise SpeakerTurnUnitError(
                f"units {previous.identifier} and {following.identifier} do not abut: "
                f"{previous.end_seconds} then {following.start_seconds}"
            )
    for unit in units:
        if unit.duration_seconds <= 0:
            raise SpeakerTurnUnitError(f"unit {unit.identifier} is empty")
        if unit.duration_seconds > MAX_UNIT_SECONDS + 1e-6:
            raise SpeakerTurnUnitError(
                f"unit {unit.identifier} is {unit.duration_seconds} s, over the cap"
            )


# ---------------------------------------------------------------------------
# 3. Reference words, from the sealed per-window COUNTS and nothing else.
# ---------------------------------------------------------------------------


def reference_word_partition(
    units: Sequence[Unit], window_rows: Sequence[Mapping[str, object]]
) -> tuple[tuple[int, int], ...]:
    """Half-open reference-word index ranges, one per unit, summing to the call's
    own total.

    ``window_rows`` are the sealed ``SAEA-E21-MF-WINDOW-PAIRING-V1`` rows of ONE
    call in window order: each carries ``start_seconds``, ``end_seconds`` and the
    ``reference_words`` the scorer's own alignment charged to that window. No
    reference TEXT is read here, and none can be: the input is a count per window.
    """

    ordered = sorted(window_rows, key=lambda row: float(row["start_seconds"]))
    if not ordered:
        raise SpeakerTurnUnitError("a call must carry at least one sealed window row")
    edges: list[float] = [float(ordered[0]["start_seconds"])]
    cumulative: list[int] = [0]
    for row in ordered:
        edges.append(float(row["end_seconds"]))
        cumulative.append(cumulative[-1] + int(row["reference_words"]))

    def at(time: float) -> int:
        if time <= edges[0]:
            return 0
        if time >= edges[-1]:
            return cumulative[-1]
        for index in range(1, len(edges)):
            if time <= edges[index]:
                span = edges[index] - edges[index - 1]
                if span <= 0:
                    return cumulative[index]
                fraction = (time - edges[index - 1]) / span
                low, high = cumulative[index - 1], cumulative[index]
                return int(round(low + fraction * (high - low)))
        return cumulative[-1]

    ranges: list[tuple[int, int]] = []
    cursor = 0
    for position, unit in enumerate(units):
        end = cumulative[-1] if position == len(units) - 1 else max(cursor, at(unit.end_seconds))
        ranges.append((cursor, end))
        cursor = end
    if ranges[-1][1] != cumulative[-1]:
        raise SpeakerTurnUnitError(
            f"the unit partition accounts for {ranges[-1][1]} reference words but the "
            f"sealed windows charge {cumulative[-1]}"
        )
    return tuple(ranges)


# ---------------------------------------------------------------------------
# 4. Per-call reporting.
# ---------------------------------------------------------------------------


def _quantile(ordered: Sequence[float], fraction: float) -> float:
    if not ordered:
        return 0.0
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[int(position)])
    weight = position - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


def call_summary(
    sample_id: str,
    units: Sequence[Unit],
    duration_seconds: float,
    window_count: int,
    reference_ranges: Sequence[tuple[int, int]] | None = None,
) -> dict[str, object]:
    """Everything the receipt reports for one call, all derived from the plan."""

    durations = sorted(unit.duration_seconds for unit in units)
    shares = sorted(unit.speaker_share for unit in units)
    # A unit the diarizer attributes to NOBODY is not a "pure" unit; it is a
    # silent one, and conflating the two would inflate the purity headline.
    pure = sum(1 for unit in units if unit.speaker_count == 1)
    silent = sum(1 for unit in units if unit.speaker_count == 0)
    cut_counts: dict[str, int] = {}
    for unit in units:
        cut_counts[unit.end_cut] = cut_counts.get(unit.end_cut, 0) + 1
    flags: dict[str, int] = {}
    for unit in units:
        for flag in unit.flags:
            flags[flag] = flags.get(flag, 0) + 1
    cut_seconds = sum(unit.duration_seconds for unit in units)
    summary: dict[str, object] = {
        "sample_id": sample_id,
        "units": len(units),
        "windows": window_count,
        "decoded_duration_seconds": round(duration_seconds, 6),
        "cut_seconds": round(cut_seconds, 6),
        "delivered_seconds": round(cut_seconds + TAIL_SILENCE_SECONDS * len(units), 6),
        "window_delivered_seconds": round(duration_seconds, 6),
        "duration_min": round(durations[0], 6),
        "duration_p25": round(_quantile(durations, 0.25), 6),
        "duration_median": round(_quantile(durations, 0.50), 6),
        "duration_p75": round(_quantile(durations, 0.75), 6),
        "duration_p90": round(_quantile(durations, 0.90), 6),
        "duration_max": round(durations[-1], 6),
        "duration_mean": round(cut_seconds / len(units), 6),
        "ends_pause": cut_counts.get(CUT_PAUSE, 0),
        "ends_turn_boundary": cut_counts.get(CUT_TURN_BOUNDARY, 0),
        "ends_forced": cut_counts.get(CUT_FORCED, 0),
        "ends_call_end": cut_counts.get(CUT_CALL_END, 0),
        "ends_on_active_frame": sum(1 for unit in units if unit.ends_active),
        "single_speaker_units": pure,
        "silent_units": silent,
        "units_under_1s": sum(1 for unit in units if unit.duration_seconds < MIN_UNIT_SECONDS),
        "purity_min": round(shares[0], 6),
        "purity_median": round(_quantile(shares, 0.50), 6),
        "purity_mean": round(sum(shares) / len(shares), 6),
        "flags": dict(sorted(flags.items())),
    }
    if reference_ranges is not None:
        counts = [high - low for low, high in reference_ranges]
        summary["reference_words"] = sum(counts)
        summary["reference_words_per_unit_median"] = round(
            _quantile(sorted(float(c) for c in counts), 0.50), 6
        )
        summary["units_with_no_reference_words"] = sum(1 for c in counts if c == 0)
    return summary


def corpus_summary(per_call: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Pool the per-call rows: sum the counts, then divide ONCE."""

    rows = list(per_call)
    if not rows:
        raise SpeakerTurnUnitError("no calls to pool")
    total_units = sum(int(row["units"]) for row in rows)
    total_windows = sum(int(row["windows"]) for row in rows)
    cut_seconds = sum(float(row["cut_seconds"]) for row in rows)
    delivered = sum(float(row["delivered_seconds"]) for row in rows)
    window_delivered = sum(float(row["window_delivered_seconds"]) for row in rows)
    flags: dict[str, int] = {}
    for row in rows:
        for flag, count in dict(row.get("flags") or {}).items():
            flags[flag] = flags.get(flag, 0) + int(count)
    return {
        "calls": len(rows),
        "units": total_units,
        "windows": total_windows,
        "cut_seconds": round(cut_seconds, 6),
        "delivered_seconds": round(delivered, 6),
        "window_delivered_seconds": round(window_delivered, 6),
        "delivered_delta_seconds": round(delivered - window_delivered, 6),
        "delivered_delta_share": (
            round((delivered - window_delivered) / window_delivered, 8)
            if window_delivered
            else 0.0
        ),
        "mean_unit_seconds": round(cut_seconds / total_units, 6) if total_units else 0.0,
        "ends_pause": sum(int(row["ends_pause"]) for row in rows),
        "ends_turn_boundary": sum(int(row["ends_turn_boundary"]) for row in rows),
        "ends_forced": sum(int(row["ends_forced"]) for row in rows),
        "ends_call_end": sum(int(row["ends_call_end"]) for row in rows),
        "ends_on_active_frame": sum(int(row["ends_on_active_frame"]) for row in rows),
        "single_speaker_units": sum(int(row["single_speaker_units"]) for row in rows),
        "silent_units": sum(int(row.get("silent_units", 0)) for row in rows),
        "units_under_1s": sum(int(row.get("units_under_1s", 0)) for row in rows),
        "reference_words": sum(int(row.get("reference_words", 0)) for row in rows),
        "units_with_no_reference_words": sum(
            int(row.get("units_with_no_reference_words", 0)) for row in rows
        ),
        "flags": dict(sorted(flags.items())),
    }


# ---------------------------------------------------------------------------
# 5. The two committed documents, shaped here so the runner stays a driver.
# ---------------------------------------------------------------------------

STUDY_SLUG = "speech-aware-evidence-acquisition"
EXPOSURE_ROW = "SAEA-E21-MF-SPEAKER-TURN-UNITS-V1"
SUMMARY_SCHEMA = "saea-e21-speaker-turn-units-summary-v1"

#: v2's own exposure row and summary schema (module docstring, "OBS-E1 UNIT
#: PLAN v2"); v1's are untouched above.
EXPOSURE_ROW_V2 = "SAEA-E21-MF-SPEAKER-TURN-UNITS-V2"
SUMMARY_SCHEMA_V2 = "saea-e21-speaker-turn-units-summary-v2"

REFERENCE_ATTRIBUTION_NOTE = (
    "interpolated from the sealed per-window reference-word COUNTS and window "
    "timings of SAEA-E21-MF-WINDOW-PAIRING-V1; exact at every window boundary, "
    "linear inside one. An attribution, never a timestamped alignment, and no "
    "reference text, wer_tags sidecar or timestamp file was opened."
)
ZERO_CONTACT_NOTE = (
    "no frozen core, diarizer re-run, GPU, embedder, tokenizer, network or paid "
    "API; no MP3 decode and no resample, so ffmpeg stays absent. The only audio "
    "touch is a local PCM read of already-sealed slices, reduced to 20 ms frame "
    "energies and thrown away."
)


def rules_block() -> dict[str, object]:
    """The five rules' numeric settings, written into the plan so a later reader
    never has to guess which constants a committed plan was cut under."""

    return {
        "pause_min_seconds": PAUSE_MIN_SECONDS,
        "snap_radius_seconds": SNAP_RADIUS_SECONDS,
        "max_unit_seconds": MAX_UNIT_SECONDS,
        "min_unit_seconds": MIN_UNIT_SECONDS,
        "tail_silence_seconds": TAIL_SILENCE_SECONDS,
        "frame_ms": FRAME_MS,
        "peak_drop_db": PEAK_DROP_DB,
        "absolute_floor_dbfs": ABSOLUTE_FLOOR_DBFS,
    }


def rules_block_v2() -> dict[str, object]:
    """v1's rule settings, plus the name of the rule that replaces v1's rule
    4 (the coordinator's 2026-09-08 decision, module docstring "OBS-E1 UNIT
    PLAN v2"). ``min_unit_seconds`` itself is unchanged -- only what happens
    to a span under it moves."""

    block = rules_block()
    block["min_unit_merge_rule"] = (
        "v2-longer-neighbour-either-speaker-ties-preceding-cap-preserved"
    )
    return block


def plan_document(
    *,
    carrier_lock_key: str,
    split_identity_hash: str,
    source_run_id: str,
    source_attempt_id: str,
    diarization_run_id: str,
    window_rows_sha256: str,
    calls: Sequence[Mapping[str, object]],
    corpus: Mapping[str, object],
    schema: str = PLAN_SCHEMA,
    exposure_row: str = EXPOSURE_ROW,
    rules: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The hash-pinned unit plan: units, never audio.

    ``schema``/``exposure_row``/``rules`` default to v1's, so every existing
    call site reproduces its bytes exactly; a v2 build passes
    :data:`PLAN_SCHEMA_V2`, :data:`EXPOSURE_ROW_V2` and :func:`rules_block_v2`
    explicitly.
    """

    return {
        "schema": schema,
        "study": STUDY_SLUG,
        "exposure_row": exposure_row,
        "carrier_lock_key": carrier_lock_key,
        "split_identity_hash": split_identity_hash,
        "source_run_id": source_run_id,
        "source_attempt_id": source_attempt_id,
        "diarization_run_id": diarization_run_id,
        "window_rows_sha256": window_rows_sha256,
        "rules": dict(rules) if rules is not None else rules_block(),
        "reference_word_attribution": REFERENCE_ATTRIBUTION_NOTE,
        "zero_contact": ZERO_CONTACT_NOTE,
        "corpus": dict(corpus),
        "calls": [dict(call) for call in calls],
    }


def summary_document(
    *,
    plan_path: str,
    plan_sha256: str,
    elapsed_seconds: float,
    corpus: Mapping[str, object],
    per_call: Sequence[Mapping[str, object]],
    schema: str = SUMMARY_SCHEMA,
    exposure_row: str = EXPOSURE_ROW,
    rules: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The committed receipt beside the plan. Same default-preserving shape
    as :func:`plan_document`."""

    return {
        "schema": schema,
        "study": STUDY_SLUG,
        "exposure_row": exposure_row,
        "plan_path": plan_path,
        "plan_sha256": plan_sha256,
        "rules": dict(rules) if rules is not None else rules_block(),
        "zero_contact": ZERO_CONTACT_NOTE,
        "elapsed_seconds": round(float(elapsed_seconds), 3),
        "corpus": dict(corpus),
        "per_call": [dict(row) for row in per_call],
    }


__all__ = [
    "CUT_CALL_END",
    "CUT_CALL_START",
    "CUT_FORCED",
    "CUT_PAUSE",
    "CUT_TURN_BOUNDARY",
    "MAX_UNIT_SECONDS",
    "MIN_UNIT_SECONDS",
    "PAUSE_MIN_SECONDS",
    "PLAN_SCHEMA",
    "PLAN_SCHEMA_V2",
    "SNAP_RADIUS_SECONDS",
    "TAIL_SILENCE_SECONDS",
    "Pause",
    "SpeakerTurnUnitError",
    "Unit",
    "UnitV2",
    "activate",
    "activity_from_sealed_slices",
    "assert_tiles",
    "call_of",
    "call_summary",
    "corpus_summary",
    "ends_on_active_frame",
    "frame_activity",
    "pauses_from_activity",
    "plan_document",
    "plan_units",
    "plan_units_v2",
    "reference_word_partition",
    "rules_block",
    "rules_block_v2",
    "snap_to_pause",
    "summary_document",
    "turn_boundaries",
    "turns",
    "unit_id",
    "window_frame_ranges",
]
