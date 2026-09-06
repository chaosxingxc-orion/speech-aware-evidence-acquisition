"""Earnings-22 DEV clip-boundary audit (``SAEA-E22-MF-CLIP-BOUNDARY-AUDIT-V1``).

The 2026-09-06 semantic error scan
(:mod:`~speech_aware_evidence_acquisition.analysis.e22_error_taxonomy`) put
8.358 of arm A's 17.565 dev WER points -- 47.6 % -- on speech at the CLIP
BOUNDARY: 868 of 2,828 tail insertion spans reproduce the NEXT published
utterance's own reference at >= 0.6 containment and 287 of 603 head spans
reproduce the PREVIOUS one. That reading was made entirely from the
transcripts. This module makes the same measurement from the TIMESTAMPS and
the AUDIO, so the boundary stops being an inference about text and becomes a
property of the cut.

Three measurements, none of which needs a model.

**Geometry.** Every dev clip's media duration against its own
``end_ts - start_ts``, and the signed gap to the PREVIOUS and NEXT segment of
the same call. A NEGATIVE gap means the two published segments themselves
overlap, so the clip provably carries some of its neighbour's speech; a
positive gap means the clip is tight and anything past its own words is the
core continuing past the audio it was given. Those are different mechanisms
with different fixes, and the sign of one number separates them.

**Margins.** A deliberately crude frame-energy gate over the derived 16 kHz
int16 WAV bytes -- not a VAD, and named as such everywhere it is reported.
Per clip it answers two questions: how much silence sits at each end, and how
much of the OVERLAP ZONE (the final ``-gap_next`` seconds, the stretch the
next segment also claims) carries frames above the clip's own activity
threshold. A clip whose overlap zone is active is one whose neighbour's speech
was audibly delivered.

**The cross.** Every arm-A boundary insertion span is re-derived with the
scan's own containment rule and joined to its clip's geometry, so the 868/287
bleed spans split into those sitting on OVERLAPPING clips (the cut caused it)
and those sitting on TIGHT clips (the core continued past the audio).

Model-free by construction: no frozen core, tokenizer, embedder, retriever,
scorer, network or GPU contact. The WAV reads are local PCM reads through the
standard library's :mod:`wave`; they deliver audio to nothing. The six ESB
TEST calls are unreachable from here -- every input is pinned to the dev10
roster, the dev10 segment table and the dev10 reference layer.

Nothing here licenses a fix. It measures a cut and writes receipts; re-cutting
any clip needs its own preregistration, its own owner decision and its own
exposure row.
"""

from __future__ import annotations

import hashlib
import json
import math
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .e22_error_taxonomy import (
    ARM_SOURCES,
    UtteranceContext,
    _contained_in_neighbour,
    align_spans,
    build_contexts,
    build_entity_inventory,
    load_hypotheses,
    normalized_tokens,
    outputs_path,
)

AUDIT_VERSION = "saea-e22-clip-boundary-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-CLIP-BOUNDARY-AUDIT-V1"

#: The committed dev10 roster receipt. It carries, per clip, the published
#: ``start_ts``/``end_ts`` the cut was made at, the MEASURED media duration and
#: the media identity -- everything the geometry needs, already in Git.
ROSTER_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-e22-dev-esb-prompt-ab-v1/roster/flight-roster-receipt.json"
)

#: The additive D1 media supplement the dev clips entered D1's identity closure
#: through. Read for the per-file SHA-256 the margins pass re-verifies against.
D1_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json"

#: The frame-energy gate. 20 ms frames; a frame is ACTIVE when its RMS is within
#: ``PEAK_DROP_DB`` of the clip's own loudest frame, subject to an absolute
#: floor so a clip that is silence throughout does not manufacture activity from
#: its own noise. These three numbers are a crude gate, not a trained VAD, and
#: every figure derived from them is reported as such.
FRAME_MS = 20
PEAK_DROP_DB = 30.0
ABSOLUTE_FLOOR_DBFS = -55.0

#: Full-scale for 16-bit PCM.
INT16_FULL_SCALE = 32768.0

#: Gap buckets, in seconds, for the overlap distribution. Left-exclusive,
#: right-inclusive, ordered.
GAP_BUCKET_EDGES: tuple[float, ...] = (
    -0.20,
    -0.18,
    -0.16,
    -0.12,
    -0.08,
    -0.04,
    0.0,
    0.25,
    1.0,
    4.0,
)


class ClipBoundaryError(RuntimeError):
    """An input is missing, has drifted from its committed hash, or is malformed."""


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClipGeometry:
    """One dev clip's cut, measured rather than assumed.

    ``gap_previous_seconds`` and ``gap_next_seconds`` are ``None`` at the two
    ends of a call. A negative gap is an OVERLAP: the published segments claim
    the same audio, so this clip carries some of that neighbour's speech.
    """

    sample_id: str
    call: str
    segment_index: int
    start_seconds: float
    end_seconds: float
    timestamp_seconds: float
    media_seconds: float
    end_clamped: bool
    gap_previous_seconds: float | None
    gap_next_seconds: float | None

    @property
    def duration_delta_seconds(self) -> float:
        """Media duration minus the timestamp span. Non-zero only where the cut
        was clamped to the decoded parent."""

        return self.media_seconds - self.timestamp_seconds

    @property
    def overlaps_previous(self) -> bool:
        return self.gap_previous_seconds is not None and self.gap_previous_seconds < 0.0

    @property
    def overlaps_next(self) -> bool:
        return self.gap_next_seconds is not None and self.gap_next_seconds < 0.0

    @property
    def previous_overlap_seconds(self) -> float:
        return max(0.0, -(self.gap_previous_seconds or 0.0))

    @property
    def next_overlap_seconds(self) -> float:
        return max(0.0, -(self.gap_next_seconds or 0.0))


def clip_geometry(items: Sequence[Mapping[str, Any]]) -> dict[str, ClipGeometry]:
    """Per-clip geometry from roster items, neighbours resolved by segment index.

    The roster's ``sample_id`` is ``<call>-<segment index>`` by construction and
    the builder refuses any id that is not, so the neighbour lookup is a sort
    rather than a search. A call whose segment indices are not the contiguous
    range ``0..n-1`` is a defect and refuses here: a hole would make every gap
    across it a fiction.
    """

    by_call: dict[str, list[tuple[int, Mapping[str, Any]]]] = {}
    for item in items:
        sample_id = str(item["sample_id"])
        call = str(item["parent_sample_id"])
        head, _, tail = sample_id.rpartition("-")
        if head != call or not tail.isdigit():
            raise ClipBoundaryError(
                f"roster item {sample_id!r} is not <call>-<segment index> for call {call!r}"
            )
        by_call.setdefault(call, []).append((int(tail), item))

    geometry: dict[str, ClipGeometry] = {}
    for call, rows in by_call.items():
        rows.sort(key=lambda pair: pair[0])
        indices = [index for index, _ in rows]
        if indices != list(range(len(indices))):
            raise ClipBoundaryError(
                f"call {call} has non-contiguous segment indices "
                f"({indices[:3]}...{indices[-3:]}); a gap would make every neighbour "
                "distance a fiction"
            )
        for position, (index, item) in enumerate(rows):
            start = float(item["segment_start_seconds"])
            end = float(item["segment_end_seconds"])
            previous_gap = (
                start - float(rows[position - 1][1]["segment_end_seconds"])
                if position > 0
                else None
            )
            next_gap = (
                float(rows[position + 1][1]["segment_start_seconds"]) - end
                if position + 1 < len(rows)
                else None
            )
            geometry[str(item["sample_id"])] = ClipGeometry(
                sample_id=str(item["sample_id"]),
                call=call,
                segment_index=index,
                start_seconds=start,
                end_seconds=end,
                timestamp_seconds=end - start,
                media_seconds=float(item["audio_seconds"]),
                end_clamped=bool(item.get("end_clamped_to_decoded_parent", False)),
                gap_previous_seconds=previous_gap,
                gap_next_seconds=next_gap,
            )
    return geometry


def _bucket_label(value: float, edges: Sequence[float]) -> str:
    if value <= edges[0]:
        return f"<= {edges[0]:.2f}"
    for lower, upper in zip(edges, edges[1:]):
        if lower < value <= upper:
            return f"({lower:.2f}, {upper:.2f}]"
    return f"> {edges[-1]:.2f}"


def gap_distribution(
    geometry: Mapping[str, ClipGeometry], *, edges: Sequence[float] = GAP_BUCKET_EDGES
) -> dict[str, Any]:
    """The distribution of the signed gap between consecutive published segments.

    One entry per adjacent PAIR (so ``clips - calls`` of them), because the gap
    is a property of the pair, not of either clip.
    """

    gaps = [
        clip.gap_next_seconds
        for clip in geometry.values()
        if clip.gap_next_seconds is not None
    ]
    if not gaps:
        raise ClipBoundaryError("no adjacent segment pairs; geometry is empty")
    ordered = sorted(gaps)
    buckets: dict[str, int] = {}
    for value in gaps:
        label = _bucket_label(value, edges)
        buckets[label] = buckets.get(label, 0) + 1
    negative = [value for value in gaps if value < 0.0]
    return {
        "pairs": len(gaps),
        "overlapping_pairs": len(negative),
        "overlapping_share": round(len(negative) / len(gaps), 6),
        "touching_pairs": sum(1 for value in gaps if value == 0.0),
        "separated_pairs": sum(1 for value in gaps if value > 0.0),
        "overlap_seconds_total": round(-sum(negative), 6),
        "min_seconds": round(ordered[0], 6),
        "max_seconds": round(ordered[-1], 6),
        "mean_seconds": round(sum(gaps) / len(gaps), 6),
        "percentiles": {
            str(point): round(_percentile(ordered, point), 6)
            for point in (1, 5, 25, 50, 75, 95, 99)
        },
        "buckets": buckets,
        "bucket_edges": list(edges),
    }


def _percentile(ordered: Sequence[float], point: float) -> float:
    if not ordered:
        raise ClipBoundaryError("percentile of an empty sequence")
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * point / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[int(position)])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


# ---------------------------------------------------------------------------
# Margins: a crude frame-energy gate, not a VAD
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClipMargins:
    """Where the energy is inside one clip.

    ``leading_seconds`` / ``trailing_seconds`` are the silence at each end.
    ``previous_zone_active_share`` / ``next_zone_active_share`` are the share of
    ACTIVE frames inside the stretch the neighbouring segment also claims -- the
    direct measurement of whether the overlap actually delivered speech.
    """

    frames: int
    frame_seconds: float
    active_frames: int
    peak_dbfs: float
    threshold_dbfs: float
    leading_seconds: float
    trailing_seconds: float
    silent: bool
    previous_zone_frames: int
    previous_zone_active: int
    next_zone_frames: int
    next_zone_active: int

    @property
    def active_share(self) -> float:
        return self.active_frames / self.frames if self.frames else 0.0

    @property
    def previous_zone_active_share(self) -> float | None:
        if not self.previous_zone_frames:
            return None
        return self.previous_zone_active / self.previous_zone_frames

    @property
    def next_zone_active_share(self) -> float | None:
        if not self.next_zone_frames:
            return None
        return self.next_zone_active / self.next_zone_frames


def frame_rms_dbfs(samples: Any, frame_length: int) -> Any:
    """Per-frame RMS in dBFS over int16 PCM. A trailing partial frame is dropped."""

    import numpy as np  # noqa: PLC0415 (numpy stays a function-local import here)

    if frame_length <= 0:
        raise ClipBoundaryError("frame_length must be positive")
    data = np.asarray(samples, dtype=np.float64)
    usable = (len(data) // frame_length) * frame_length
    if usable == 0:
        return np.zeros(0, dtype=np.float64)
    frames = data[:usable].reshape(-1, frame_length) / INT16_FULL_SCALE
    rms = np.sqrt(np.mean(np.square(frames), axis=1))
    return 20.0 * np.log10(np.maximum(rms, 1e-12))


def energy_margins(
    samples: Any,
    sample_rate: int,
    *,
    previous_overlap_seconds: float = 0.0,
    next_overlap_seconds: float = 0.0,
    frame_ms: int = FRAME_MS,
    peak_drop_db: float = PEAK_DROP_DB,
    absolute_floor_dbfs: float = ABSOLUTE_FLOOR_DBFS,
) -> ClipMargins:
    """Leading/trailing silence and overlap-zone activity for one clip."""

    import numpy as np  # noqa: PLC0415

    frame_length = max(1, int(round(sample_rate * frame_ms / 1000.0)))
    levels = frame_rms_dbfs(samples, frame_length)
    frames = int(levels.size)
    frame_seconds = frame_length / sample_rate
    if frames == 0:
        return ClipMargins(
            frames=0,
            frame_seconds=frame_seconds,
            active_frames=0,
            peak_dbfs=float("-inf"),
            threshold_dbfs=float("-inf"),
            leading_seconds=0.0,
            trailing_seconds=0.0,
            silent=True,
            previous_zone_frames=0,
            previous_zone_active=0,
            next_zone_frames=0,
            next_zone_active=0,
        )
    peak = float(levels.max())
    threshold = max(peak - peak_drop_db, absolute_floor_dbfs)
    active = levels >= threshold
    indices = np.flatnonzero(active)
    if indices.size == 0:
        return ClipMargins(
            frames=frames,
            frame_seconds=frame_seconds,
            active_frames=0,
            peak_dbfs=peak,
            threshold_dbfs=threshold,
            leading_seconds=frames * frame_seconds,
            trailing_seconds=frames * frame_seconds,
            silent=True,
            previous_zone_frames=0,
            previous_zone_active=0,
            next_zone_frames=0,
            next_zone_active=0,
        )
    leading = int(indices[0]) * frame_seconds
    trailing = (frames - 1 - int(indices[-1])) * frame_seconds
    lead_zone = min(frames, int(round(previous_overlap_seconds / frame_seconds)))
    tail_zone = min(frames, int(round(next_overlap_seconds / frame_seconds)))
    return ClipMargins(
        frames=frames,
        frame_seconds=frame_seconds,
        active_frames=int(active.sum()),
        peak_dbfs=peak,
        threshold_dbfs=threshold,
        leading_seconds=leading,
        trailing_seconds=trailing,
        silent=False,
        previous_zone_frames=lead_zone,
        previous_zone_active=int(active[:lead_zone].sum()) if lead_zone else 0,
        next_zone_frames=tail_zone,
        next_zone_active=int(active[frames - tail_zone :].sum()) if tail_zone else 0,
    )


def read_wav_int16(path: Path) -> tuple[Any, int]:
    """Read one mono 16-bit PCM WAV with the standard library only.

    A local PCM read, not a model contact: the samples are reduced to frame
    energies and thrown away, and nothing is sent anywhere.
    """

    import numpy as np  # noqa: PLC0415

    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ClipBoundaryError(
                f"{path} is not mono 16-bit PCM "
                f"({handle.getnchannels()} channels, {handle.getsampwidth()} bytes/sample)"
            )
        rate = handle.getframerate()
        payload = handle.readframes(handle.getnframes())
    return np.frombuffer(payload, dtype="<i2"), rate


# ---------------------------------------------------------------------------
# The cross: boundary spans against the geometry that produced them
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundarySpan:
    """One arm insertion span at a clip edge, with the scan's containment share.

    ``whole_hypothesis`` marks a span that is simultaneously the head AND the
    tail of its hypothesis -- the entire output is one insertion, which happens
    when the reference normalizes to nothing. The 2026-09-06 scan's two separate
    loops count such a span on BOTH sides; this audit assigns it to the tail
    once, and the receipt reports the difference rather than hiding it.
    """

    sample_id: str
    call: str
    side: str
    words: int
    containment: float
    whole_hypothesis: bool = False


def boundary_spans(contexts: Mapping[str, UtteranceContext]) -> list[BoundarySpan]:
    """Re-derive the scan's tail/head insertion spans and their containment.

    The 2026-09-06 scan reported these as four aggregate buckets only, so the
    per-row attribution is rebuilt here with the same rule -- the longest
    contiguous run of the inserted words that also occurs in the neighbouring
    reference, as a share of the span.
    """

    spans: list[BoundarySpan] = []
    for sample_id, context in contexts.items():
        alignment = align_spans(context.ref_tokens, context.hyp_tokens)
        for span in alignment.spans:
            if span.op != "INS":
                continue
            at_tail = span.hyp_end == len(context.hyp_tokens)
            at_head = span.hyp_start == 0
            if at_tail:
                side, neighbour = "tail", context.next_tokens
            elif at_head:
                side, neighbour = "head", context.previous_tokens
            else:
                continue
            spans.append(
                BoundarySpan(
                    sample_id=sample_id,
                    call=context.call,
                    side=side,
                    words=len(span.hyp_tokens),
                    containment=_contained_in_neighbour(span.hyp_tokens, neighbour),
                    whole_hypothesis=at_tail and at_head,
                )
            )
    return spans


def containment_bucket(share: float) -> str:
    if share >= 0.6:
        return "contains_0.6_or_more"
    if share >= 0.34:
        return "contains_0.34_to_0.6"
    if share > 0.0:
        return "contains_some"
    return "contains_none"


def cross_boundary_geometry(
    spans: Iterable[BoundarySpan],
    geometry: Mapping[str, ClipGeometry],
    *,
    reference_words: int,
) -> dict[str, Any]:
    """Split every boundary span by whether ITS OWN clip overlaps that neighbour.

    A span at the tail of a clip whose ``gap_next`` is negative sits on audio the
    next segment also claims: the cut delivered those words. A span at the tail
    of a clip whose ``gap_next`` is positive sits on audio that had already
    stopped: the core continued past it. Same words, two mechanisms.
    """

    report: dict[str, Any] = {}
    for side in ("tail", "head"):
        cells: dict[str, dict[str, Any]] = {}
        span_total = 0
        word_total = 0
        for span in spans:
            if span.side != side:
                continue
            clip = geometry[span.sample_id]
            gap = clip.gap_next_seconds if side == "tail" else clip.gap_previous_seconds
            if gap is None:
                edge = "no_neighbour"
            elif gap < 0.0:
                edge = "overlapping_clip"
            else:
                edge = "tight_clip"
            bucket = containment_bucket(span.containment)
            cell = cells.setdefault(bucket, {})
            entry = cell.setdefault(edge, {"spans": 0, "words": 0})
            entry["spans"] += 1
            entry["words"] += span.words
            span_total += 1
            word_total += span.words
        for cell in cells.values():
            for edge in ("overlapping_clip", "tight_clip", "no_neighbour"):
                entry = cell.setdefault(edge, {"spans": 0, "words": 0})
                entry["wer_points"] = (
                    round(100.0 * entry["words"] / reference_words, 4)
                    if reference_words
                    else 0.0
                )
        report[side] = {
            "spans": span_total,
            "words": word_total,
            "by_containment": cells,
        }
    return report


def cross_boundary_activity(
    spans: Iterable[BoundarySpan],
    geometry: Mapping[str, ClipGeometry],
    margins: Mapping[str, ClipMargins],
    *,
    active_zone_threshold: float = 0.5,
) -> dict[str, Any]:
    """The same split again, decided by the AUDIO rather than by the timestamps.

    A tail span sits on an ``audible_overlap`` clip when the stretch the next
    segment also claims is at least ``active_zone_threshold`` active by the
    frame-energy gate. This is the weaker of the two tests -- the gate is crude
    and an overlap zone can be a breath -- and it exists so the timestamp answer
    is not the only answer.
    """

    report: dict[str, Any] = {}
    for side in ("tail", "head"):
        cells: dict[str, dict[str, int]] = {}
        for span in spans:
            if span.side != side:
                continue
            clip = geometry[span.sample_id]
            margin = margins.get(span.sample_id)
            share = None
            if margin is not None:
                share = (
                    margin.next_zone_active_share
                    if side == "tail"
                    else margin.previous_zone_active_share
                )
            overlap = clip.next_overlap_seconds if side == "tail" else clip.previous_overlap_seconds
            if overlap <= 0.0:
                label = "no_overlap_zone"
            elif share is None:
                label = "zone_not_measured"
            elif share >= active_zone_threshold:
                label = "audible_overlap"
            else:
                label = "quiet_overlap"
            bucket = containment_bucket(span.containment)
            cell = cells.setdefault(bucket, {})
            cell[label] = cell.get(label, 0) + 1
        report[side] = cells
    report["active_zone_threshold"] = active_zone_threshold
    return report


def margin_summary(
    geometry: Mapping[str, ClipGeometry], margins: Mapping[str, ClipMargins]
) -> dict[str, Any]:
    """Where the energy sits at each clip edge, grouped by whether that edge overlaps."""

    groups: dict[str, dict[str, list[float]]] = {
        "tail_overlapping": {"margin": [], "zone": []},
        "tail_tight": {"margin": [], "zone": []},
        "head_overlapping": {"margin": [], "zone": []},
        "head_tight": {"margin": [], "zone": []},
    }
    silent = 0
    for sample_id, clip in geometry.items():
        margin = margins.get(sample_id)
        if margin is None:
            continue
        if margin.silent:
            silent += 1
            continue
        if clip.gap_next_seconds is not None:
            key = "tail_overlapping" if clip.overlaps_next else "tail_tight"
            groups[key]["margin"].append(margin.trailing_seconds)
            share = margin.next_zone_active_share
            if share is not None:
                groups[key]["zone"].append(share)
        if clip.gap_previous_seconds is not None:
            key = "head_overlapping" if clip.overlaps_previous else "head_tight"
            groups[key]["margin"].append(margin.leading_seconds)
            share = margin.previous_zone_active_share
            if share is not None:
                groups[key]["zone"].append(share)

    def describe(values: Sequence[float]) -> dict[str, Any]:
        if not values:
            return {"n": 0}
        ordered = sorted(values)
        return {
            "n": len(ordered),
            "mean": round(sum(ordered) / len(ordered), 6),
            "p25": round(_percentile(ordered, 25), 6),
            "median": round(_percentile(ordered, 50), 6),
            "p75": round(_percentile(ordered, 75), 6),
            "p95": round(_percentile(ordered, 95), 6),
        }

    report: dict[str, Any] = {
        "clips_measured": len(margins),
        "clips_with_no_active_frame": silent,
        "frame_ms": FRAME_MS,
        "peak_drop_db": PEAK_DROP_DB,
        "absolute_floor_dbfs": ABSOLUTE_FLOOR_DBFS,
        "gate_note": (
            "a crude frame-energy gate, not a VAD: a frame is ACTIVE when its RMS "
            "is within peak_drop_db of the clip's own loudest frame, floored at "
            "absolute_floor_dbfs. Every figure derived from it inherits that crudeness."
        ),
    }
    for name, buckets in groups.items():
        report[name] = {
            "silence_seconds": describe(buckets["margin"]),
            "overlap_zone_active_share": describe(buckets["zone"]),
            "edge_is_active_share": round(
                sum(1 for value in buckets["margin"] if value <= 1e-9) / len(buckets["margin"]),
                6,
            )
            if buckets["margin"]
            else 0.0,
        }
    return report


PER_CLIP_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "call",
    "segment_index",
    "start_seconds",
    "end_seconds",
    "timestamp_seconds",
    "media_seconds",
    "duration_delta_seconds",
    "end_clamped",
    "gap_previous_seconds",
    "gap_next_seconds",
    "previous_overlap_seconds",
    "next_overlap_seconds",
    "frames",
    "active_share",
    "peak_dbfs",
    "leading_silence_seconds",
    "trailing_silence_seconds",
    "previous_zone_active_share",
    "next_zone_active_share",
    "arm_a_tail_spans",
    "arm_a_tail_words",
    "arm_a_tail_contained_06",
    "arm_a_head_spans",
    "arm_a_head_words",
    "arm_a_head_contained_06",
)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return ""
        return f"{value:.6f}"
    return str(value)


def per_clip_table(
    geometry: Mapping[str, ClipGeometry],
    margins: Mapping[str, ClipMargins],
    spans: Sequence[BoundarySpan],
) -> str:
    """The per-clip receipt, as CSV. Numbers and identifiers only -- no text."""

    tallies: dict[str, dict[str, int]] = {}
    for span in spans:
        entry = tallies.setdefault(
            span.sample_id,
            {
                "tail_spans": 0,
                "tail_words": 0,
                "tail_contained": 0,
                "head_spans": 0,
                "head_words": 0,
                "head_contained": 0,
            },
        )
        entry[f"{span.side}_spans"] += 1
        entry[f"{span.side}_words"] += span.words
        if span.containment >= 0.6:
            entry[f"{span.side}_contained"] += 1

    empty = {
        "tail_spans": 0,
        "tail_words": 0,
        "tail_contained": 0,
        "head_spans": 0,
        "head_words": 0,
        "head_contained": 0,
    }
    lines = [",".join(PER_CLIP_COLUMNS)]
    for sample_id in sorted(geometry, key=lambda key: (geometry[key].call, geometry[key].segment_index)):
        clip = geometry[sample_id]
        margin = margins.get(sample_id)
        tally = tallies.get(sample_id, empty)
        row = [
            clip.sample_id,
            clip.call,
            clip.segment_index,
            clip.start_seconds,
            clip.end_seconds,
            clip.timestamp_seconds,
            clip.media_seconds,
            clip.duration_delta_seconds,
            clip.end_clamped,
            clip.gap_previous_seconds,
            clip.gap_next_seconds,
            clip.previous_overlap_seconds,
            clip.next_overlap_seconds,
            margin.frames if margin else None,
            margin.active_share if margin else None,
            margin.peak_dbfs if margin else None,
            margin.leading_seconds if margin else None,
            margin.trailing_seconds if margin else None,
            margin.previous_zone_active_share if margin else None,
            margin.next_zone_active_share if margin else None,
            tally["tail_spans"],
            tally["tail_words"],
            tally["tail_contained"],
            tally["head_spans"],
            tally["head_words"],
            tally["head_contained"],
        ]
        lines.append(",".join(_cell(value) for value in row))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def load_roster(repo_root: Path) -> Mapping[str, Any]:
    """The committed dev10 roster receipt, with its own item digest re-checked."""

    path = Path(repo_root) / ROSTER_RECEIPT_RELPATH
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ClipBoundaryError(f"cannot read roster receipt {path}: {error}") from error
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise ClipBoundaryError(f"roster receipt {path} carries no items")
    payload = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    measured = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if measured != document.get("items_sha256"):
        raise ClipBoundaryError(
            f"roster items hash to {measured[:12]}..., the receipt pins "
            f"{str(document.get('items_sha256'))[:12]}..."
        )
    if str(document.get("split_role")) != "dev":
        raise ClipBoundaryError(
            f"roster receipt {path} is not the dev population "
            f"(split_role={document.get('split_role')!r})"
        )
    return document


def load_media_digests(repo_root: Path) -> dict[str, str]:
    """``{sample_id -> sha256}`` from the committed D1 media supplement."""

    path = Path(repo_root) / D1_SUPPLEMENT_RELPATH
    document = json.loads(path.read_text(encoding="utf-8"))
    manifest = document.get("manifest")
    if not isinstance(manifest, list) or not manifest:
        raise ClipBoundaryError(f"D1 supplement {path} carries no manifest")
    return {str(row["id"]): str(row["sha256"]) for row in manifest}


def measure_margins(
    root: Path,
    roster_items: Sequence[Mapping[str, Any]],
    geometry: Mapping[str, ClipGeometry],
    digests: Mapping[str, str],
) -> tuple[dict[str, ClipMargins], dict[str, Any]]:
    """Read every dev clip once and reduce it to frame energies.

    Media identity is re-verified against the committed D1 supplement as the
    bytes go past, so a margin can never be measured on a file that is not the
    one the sealed flight was served.
    """

    margins: dict[str, ClipMargins] = {}
    bytes_read = 0
    verified = 0
    for item in roster_items:
        sample_id = str(item["sample_id"])
        path = Path(root) / str(item["media_relpath"])
        payload = path.read_bytes()
        bytes_read += len(payload)
        measured = hashlib.sha256(payload).hexdigest()
        expected = digests.get(sample_id) or str(item["audio_sha256"])
        if measured != expected:
            raise ClipBoundaryError(
                f"clip {sample_id} hashes to {measured[:12]}..., D1 pins {expected[:12]}..."
            )
        verified += 1
        samples, rate = read_wav_int16(path)
        clip = geometry[sample_id]
        margins[sample_id] = energy_margins(
            samples,
            rate,
            previous_overlap_seconds=clip.previous_overlap_seconds,
            next_overlap_seconds=clip.next_overlap_seconds,
        )
    return margins, {
        "clips_read": len(margins),
        "bytes_read": bytes_read,
        "media_identity_verified": verified,
        "identity_source": D1_SUPPLEMENT_RELPATH,
    }


def build_summary(
    *,
    roster: Mapping[str, Any],
    geometry: Mapping[str, ClipGeometry],
    margins: Mapping[str, ClipMargins],
    media_read: Mapping[str, Any],
    arms: Mapping[str, Sequence[BoundarySpan]],
    reference_words: int,
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> dict[str, Any]:
    """The receipt body. Every figure here is a measurement, not a proposal."""

    per_call: dict[str, Any] = {}
    for clip in geometry.values():
        entry = per_call.setdefault(
            clip.call,
            {
                "clips": 0,
                "media_seconds": 0.0,
                "pairs": 0,
                "overlapping_pairs": 0,
                "overlap_seconds": 0.0,
            },
        )
        entry["clips"] += 1
        entry["media_seconds"] += clip.media_seconds
        if clip.gap_next_seconds is not None:
            entry["pairs"] += 1
            if clip.gap_next_seconds < 0.0:
                entry["overlapping_pairs"] += 1
                entry["overlap_seconds"] += -clip.gap_next_seconds
    for entry in per_call.values():
        entry["media_seconds"] = round(entry["media_seconds"], 6)
        entry["overlap_seconds"] = round(entry["overlap_seconds"], 6)
        entry["overlapping_share"] = (
            round(entry["overlapping_pairs"] / entry["pairs"], 6) if entry["pairs"] else 0.0
        )

    clamped = [clip.sample_id for clip in geometry.values() if clip.end_clamped]
    drifted = [
        clip.sample_id
        for clip in geometry.values()
        if abs(clip.duration_delta_seconds) > 1e-4 and not clip.end_clamped
    ]
    return {
        "schema": "saea-e22-clip-boundary-audit-v1",
        "audit_version": AUDIT_VERSION,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "population": {
            "split_id": roster.get("split_name"),
            "split_role": roster.get("split_role"),
            "carrier_lock_key": roster.get("carrier"),
            "clips": len(geometry),
            "calls": len(per_call),
            "reference_words": reference_words,
            "test_split_read": False,
        },
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
            "audio_seconds_delivered_to_a_service": 0,
            "outbound_connection_attempts": outbound_attempts,
            "outbound_targets": list(outbound_targets),
            "local_pcm_reads": media_read["clips_read"],
        },
        "cut": {
            "segment_table": {
                "repo_id": "sanchit-gandhi/earnings22_split",
                "revision": "f9fb35f4134e32b9c8100199d949398fd6d08a5f",
                "split": "train",
                "columns": ["source_id", "segment_id", "sentence", "start_ts", "end_ts", "id"],
                "audio_column_materialized": False,
            },
            "slicer": "scripts/build_e22_esb_utterance_roster.py::_cut_one_call",
            "rule": (
                "pcm[max(0, round(start_ts * 16000)) : min(frames, round(end_ts * 16000))] -- "
                "the published boundaries verbatim, ZERO padding on either side"
            ),
            "decoder": roster.get("decoder"),
            "writer": roster.get("writer"),
            "sample_rate_hz": roster.get("sample_rate_hz"),
            "padding_seconds": 0.0,
            "clips_clamped_to_decoded_parent": clamped,
            "clips_with_unexplained_duration_drift": drifted,
        },
        "media_read": dict(media_read),
        "gap_distribution": gap_distribution(geometry),
        "per_call": per_call,
        "margins": margin_summary(geometry, margins),
        "boundary_cross": {
            arm: {
                "by_timestamp": cross_boundary_geometry(
                    spans, geometry, reference_words=reference_words
                ),
                "by_audio": cross_boundary_activity(spans, geometry, margins),
                "scan_reconciliation": {
                    "whole_hypothesis_spans": sum(
                        1 for span in spans if span.whole_hypothesis
                    ),
                    "note": (
                        "a span that is simultaneously the head and the tail of its "
                        "hypothesis is counted on BOTH sides by the 2026-09-06 scan's "
                        "two separate loops and on the TAIL only here, so this audit's "
                        "head totals are lower than the scan's by exactly this count"
                    ),
                },
            }
            for arm, spans in arms.items()
        },
        "arm_labels": {arm: ARM_SOURCES[arm]["label"] for arm in arms},
    }


def scan_arms(
    root: Path,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, list[BoundarySpan]], int]:
    """Boundary spans for all three sealed 2026-09-05 arms, plus the denominator.

    The entity inventory the taxonomy's context builder wants is rebuilt exactly
    as the scan built it; it plays no part in the boundary rule, but the context
    type carries it.
    """

    raw_by_call: dict[str, list[str]] = {}
    for sample_id, sentence in references.items():
        raw_by_call.setdefault(str(segments[sample_id]["source_id"]), []).append(sentence)
    inventory = build_entity_inventory(raw_by_call)
    arms: dict[str, list[BoundarySpan]] = {}
    reference_words = 0
    for arm in sorted(ARM_SOURCES):
        hypotheses = load_hypotheses(outputs_path(root, arm))
        contexts = build_contexts(references, segments, hypotheses, inventory)
        arms[arm] = boundary_spans(contexts)
        if arm == "A":
            reference_words = sum(
                len(normalized_tokens(references[sample_id])) for sample_id in contexts
            )
    return arms, reference_words


def headline(summary: Mapping[str, Any]) -> str:
    """The operator-facing summary of one audit run."""

    gaps = summary["gap_distribution"]
    lines = [
        f"clips {summary['population']['clips']} over {summary['population']['calls']} calls; "
        f"slicer padding {summary['cut']['padding_seconds']} s",
        f"adjacent pairs {gaps['pairs']}: overlapping {gaps['overlapping_pairs']} "
        f"({100.0 * gaps['overlapping_share']:.1f} %), touching {gaps['touching_pairs']}, "
        f"separated {gaps['separated_pairs']}",
        f"gap seconds: min {gaps['min_seconds']:.4f}, median {gaps['percentiles']['50']:.4f}, "
        f"max {gaps['max_seconds']:.4f}; overlap total {gaps['overlap_seconds_total']:.1f} s",
    ]
    for name in ("tail_overlapping", "tail_tight", "head_overlapping", "head_tight"):
        block = summary["margins"][name]
        lines.append(
            f"{name}: n={block['silence_seconds']['n']} "
            f"median silence {block['silence_seconds'].get('median', 0.0):.3f} s, "
            f"edge active {100.0 * block['edge_is_active_share']:.1f} %, "
            f"median overlap-zone active share "
            f"{block['overlap_zone_active_share'].get('median', 0.0):.3f}"
        )
    for arm, block in sorted(summary["boundary_cross"].items()):
        for side in ("tail", "head"):
            cell = block["by_timestamp"][side]["by_containment"].get(
                "contains_0.6_or_more", {}
            )
            overlapping = cell.get("overlapping_clip", {}).get("spans", 0)
            tight = cell.get("tight_clip", {}).get("spans", 0)
            lines.append(
                f"arm {arm} {side} bleed at >= 0.6 containment: "
                f"{overlapping} on overlapping clips, {tight} on tight clips"
            )
    return "\n".join(lines)


__all__ = [
    "ABSOLUTE_FLOOR_DBFS",
    "ARM_SOURCES",
    "AUDIT_VERSION",
    "BoundarySpan",
    "ClipBoundaryError",
    "ClipGeometry",
    "ClipMargins",
    "D1_SUPPLEMENT_RELPATH",
    "EXPOSURE_ROW_ID",
    "FRAME_MS",
    "GAP_BUCKET_EDGES",
    "PER_CLIP_COLUMNS",
    "PEAK_DROP_DB",
    "ROSTER_RECEIPT_RELPATH",
    "boundary_spans",
    "build_summary",
    "clip_geometry",
    "containment_bucket",
    "cross_boundary_activity",
    "cross_boundary_geometry",
    "energy_margins",
    "frame_rms_dbfs",
    "gap_distribution",
    "headline",
    "load_media_digests",
    "load_roster",
    "margin_summary",
    "measure_margins",
    "per_clip_table",
    "read_wav_int16",
    "scan_arms",
]
