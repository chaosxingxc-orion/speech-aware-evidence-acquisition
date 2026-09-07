"""``saea-diarization-v1``: speaker diarization as a frozen TOOL-level OBSERVATION.

What this is, and what it is not
---------------------------------
Speaker diarization enters this study as an **OBS artifact**, never as evidence and
never as an answer. It says who spoke when; it never reaches a prompt, never
changes a hypothesis, and carries no answer authority -- the frozen core keeps
that, exactly as the study charter's "frozen tool-level retriever/judge" clause
requires. Its only two jobs are (1) to give each 90-second window a speaker
stratum, so an Earnings verdict can report per-stratum tables at the unit the
owner ruled on (``analysis.e21_window_pairing``), and (2) to tie the pre-meeting
brief's participant roster to actual speaker turns.

Why this module, and where it sits
-----------------------------------
It is an artifact READER for a pinned tool's output -- the same shape and the same
placement as ``reproduction.semantic_impact``, which reads the Earnings-22 scan's
committed taxonomy for a registered scorer. It deliberately registers nothing in a
``core.base`` registry: the owner's 2026-09-03 base rules reserve those registries
for ``policy`` / ``evidence_source`` / ``scorers`` values that a ``configs/``
fragment names, and a diarization artifact is none of the three -- it is a read-time
stratification input. No new module under ``rails/probes/``, no ``TaskAdapter`` or
controller subclass, no launcher directory.

The artifact is self-checking
------------------------------
A per-window block is a DERIVATION of the segment list, so :func:`load_diarization`
recomputes every window's dominant speaker, speaker count and overlap share from
the segments and refuses on any disagreement. A hand-edited window row, a segment
list truncated after the fact, or a window grid that does not tile the call is a
load-time error rather than a silently wrong stratum.

Speaker ids are anonymous, and naming them is a separate, gated step
---------------------------------------------------------------------
The pinned diarizer emits ``speaker_0 … speaker_3``; the ids carry no identity and
are not comparable across calls. Everything this module exposes -- speaker count,
dominant-speaker class, overlap share, per-window speaker seconds -- works on
anonymous ids alone, which is all a stratum needs. Mapping an id to a NAME is a
different question with a hard rule attached: a mapping may be built only from the
call's own pre-meeting brief (ConEC context, ``runtime-legal-input``) or from the
frozen core's own outputs, **never** from a reference transcript, a ``wer_tags``
sidecar or a timestamp file, and the mapping's accuracy against ConEC's roster is
an audit read under its own exposure row. :func:`speaker_roster_mapping` therefore
takes the candidate names it is given and refuses to invent any; there is no
reference-reading path in this module at all.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

DIARIZATION_SCHEMA = "saea-diarization-v1"
STUDY_SLUG = "speech-aware-evidence-acquisition"

#: A window's speaker stratum is reported at two grains: how many speakers it
#: carries, and whether one of them dominates it. Both are computed from
#: anonymous ids, so neither depends on a roster mapping existing.
SINGLE_SPEAKER = "speakers=1"
TWO_SPEAKERS = "speakers=2"
MANY_SPEAKERS = "speakers>=3"
NO_SPEECH = "speakers=0"

#: A window is DOMINATED when one speaker holds at least this share of its
#: attributed speech time; otherwise it is SHARED. The threshold is a reporting
#: convention, stated once here and never re-chosen per verdict.
DOMINANCE_THRESHOLD = 0.60
DOMINATED = "dominated"
SHARED = "shared"


class DiarizationError(RuntimeError):
    """A diarization artifact is malformed or internally inconsistent."""


@dataclass(frozen=True)
class SpeakerSegment:
    """One contiguous stretch attributed to one anonymous speaker id."""

    start_seconds: float
    end_seconds: float
    speaker: str

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class WindowSpeakers:
    """One 90-second window's speaker facts, all derived from the segments."""

    window_id: str
    window_index: int
    start_seconds: float
    end_seconds: float
    speaker_seconds: Mapping[str, float]
    dominant_speaker: str | None
    dominant_share: float
    speaker_count: int
    overlap_share: float

    @property
    def count_stratum(self) -> str:
        if self.speaker_count <= 0:
            return NO_SPEECH
        if self.speaker_count == 1:
            return SINGLE_SPEAKER
        if self.speaker_count == 2:
            return TWO_SPEAKERS
        return MANY_SPEAKERS

    @property
    def dominance_stratum(self) -> str:
        if self.speaker_count <= 0:
            return NO_SPEECH
        return DOMINATED if self.dominant_share >= DOMINANCE_THRESHOLD else SHARED

    def as_dict(self) -> dict[str, object]:
        return {
            "window_id": self.window_id,
            "window_index": self.window_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "speaker_seconds": {
                speaker: round(seconds, 6)
                for speaker, seconds in sorted(self.speaker_seconds.items())
            },
            "dominant_speaker": self.dominant_speaker,
            "dominant_share": self.dominant_share,
            "speaker_count": self.speaker_count,
            "overlap_share": self.overlap_share,
        }


@dataclass(frozen=True)
class CallDiarization:
    sample_id: str
    audio_seconds: float
    segments: tuple[SpeakerSegment, ...]
    windows: tuple[WindowSpeakers, ...]

    @property
    def speakers(self) -> tuple[str, ...]:
        return tuple(sorted({segment.speaker for segment in self.segments}))


@dataclass(frozen=True)
class DiarizationArtifact:
    run_id: str
    carrier_lock_key: str
    tool: Mapping[str, object]
    window_seconds: float
    calls: Mapping[str, CallDiarization]

    def window_strata(self, grain: str = "count") -> dict[str, str]:
        """``window_id -> stratum label``, ready for ``analysis.paired``'s
        ``strata_of``. ``grain`` is ``"count"`` (how many speakers),
        ``"dominance"`` (one speaker holds the window, or several share it) or
        ``"both"``."""

        if grain not in {"count", "dominance", "both"}:
            raise DiarizationError(f"unknown stratum grain {grain!r}")
        strata: dict[str, str] = {}
        for call in self.calls.values():
            for window in call.windows:
                if grain == "count":
                    strata[window.window_id] = window.count_stratum
                elif grain == "dominance":
                    strata[window.window_id] = window.dominance_stratum
                else:
                    strata[window.window_id] = (
                        f"{window.count_stratum}/{window.dominance_stratum}"
                    )
        return strata


# ---------------------------------------------------------------------------
# Derivation: segments -> per-window facts. Used to BUILD an artifact and, by
# the loader, to RE-DERIVE and check one.
# ---------------------------------------------------------------------------


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def window_speakers(
    segments: Sequence[SpeakerSegment],
    *,
    window_id: str,
    window_index: int,
    start_seconds: float,
    end_seconds: float,
) -> WindowSpeakers:
    """One window's speaker facts from the call's segments.

    ``speaker_seconds`` is each speaker's attributed time INSIDE the window.
    ``dominant_share`` is the top speaker's share of the summed attributed time
    (not of the wall-clock window, so a mostly silent window is not
    automatically "shared"). ``overlap_share`` is the fraction of the window's
    wall clock during which two or more speakers are simultaneously attributed --
    the diarizer's own crosstalk estimate, and the reason a 4-speaker bound
    matters on an earnings call.
    """

    if end_seconds <= start_seconds:
        raise DiarizationError(f"window {window_id!r} has a non-positive duration")
    seconds: dict[str, float] = {}
    covered: list[tuple[float, float]] = []
    for segment in segments:
        inside = _overlap(
            segment.start_seconds, segment.end_seconds, start_seconds, end_seconds
        )
        if inside <= 0.0:
            continue
        seconds[segment.speaker] = seconds.get(segment.speaker, 0.0) + inside
        covered.append(
            (max(segment.start_seconds, start_seconds), min(segment.end_seconds, end_seconds))
        )
    total = sum(seconds.values())
    if seconds:
        dominant_speaker = max(sorted(seconds), key=lambda name: seconds[name])
        dominant_share = seconds[dominant_speaker] / total if total else 0.0
    else:
        dominant_speaker, dominant_share = None, 0.0

    # Overlap: the wall-clock time covered by two or more of the clipped spans.
    boundaries = sorted({value for span in covered for value in span})
    overlap_seconds = 0.0
    for left, right in zip(boundaries, boundaries[1:]):
        if right <= left:
            continue
        depth = sum(1 for span in covered if span[0] <= left and span[1] >= right)
        if depth >= 2:
            overlap_seconds += right - left
    return WindowSpeakers(
        window_id=window_id,
        window_index=window_index,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        speaker_seconds=dict(sorted(seconds.items())),
        dominant_speaker=dominant_speaker,
        dominant_share=dominant_share,
        speaker_count=len(seconds),
        overlap_share=overlap_seconds / (end_seconds - start_seconds),
    )


def window_grid(audio_seconds: float, window_seconds: float) -> tuple[tuple[float, float], ...]:
    """The SAME fixed grid the OBS loop cuts: ``ceil(D / W)`` non-overlapping
    windows, the last one short (the full-44 roster receipt's own ``window_rule``).
    Stated here so a diarization artifact's windows and a flight's windows are the
    same objects, never two grids that happen to look alike."""

    if audio_seconds <= 0 or window_seconds <= 0:
        raise DiarizationError("audio_seconds and window_seconds must be positive")
    count = math.ceil(audio_seconds / window_seconds)
    return tuple(
        (index * window_seconds, min((index + 1) * window_seconds, audio_seconds))
        for index in range(count)
    )


# ---------------------------------------------------------------------------
# Loading.
# ---------------------------------------------------------------------------


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DiarizationError(f"{label} must be a number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise DiarizationError(f"{label} must be finite")
    return number


def _segments(rows: object, sample_id: str) -> tuple[SpeakerSegment, ...]:
    if not isinstance(rows, list):
        raise DiarizationError(f"call {sample_id!r} segments must be a list")
    segments: list[SpeakerSegment] = []
    previous_start = -math.inf
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != {
            "start_seconds",
            "end_seconds",
            "speaker",
        }:
            raise DiarizationError(
                f"call {sample_id!r} segment {index} must carry exactly "
                "start_seconds, end_seconds and speaker"
            )
        start = _number(row["start_seconds"], f"call {sample_id!r} segment {index} start")
        end = _number(row["end_seconds"], f"call {sample_id!r} segment {index} end")
        speaker = row["speaker"]
        if not isinstance(speaker, str) or not speaker:
            raise DiarizationError(f"call {sample_id!r} segment {index} has no speaker id")
        if end <= start:
            raise DiarizationError(
                f"call {sample_id!r} segment {index} has a non-positive duration"
            )
        if start < previous_start:
            raise DiarizationError(
                f"call {sample_id!r} segments are not in start order at index {index}"
            )
        previous_start = start
        segments.append(SpeakerSegment(start_seconds=start, end_seconds=end, speaker=speaker))
    if not segments:
        raise DiarizationError(f"call {sample_id!r} carries no speaker segments")
    return tuple(segments)


def _check_window(claimed: Mapping[str, object], derived: WindowSpeakers) -> None:
    """Refuse a window row that disagrees with what its own segments imply."""

    for key, derived_value in (
        ("dominant_speaker", derived.dominant_speaker),
        ("speaker_count", derived.speaker_count),
    ):
        if claimed.get(key) != derived_value:
            raise DiarizationError(
                f"window {derived.window_id!r} claims {key}={claimed.get(key)!r} but its "
                f"own segments imply {derived_value!r}"
            )
    for key, derived_value in (
        ("dominant_share", derived.dominant_share),
        ("overlap_share", derived.overlap_share),
    ):
        claimed_value = _number(claimed.get(key), f"window {derived.window_id!r} {key}")
        if abs(claimed_value - derived_value) > 1e-6:
            raise DiarizationError(
                f"window {derived.window_id!r} claims {key}={claimed_value} but its own "
                f"segments imply {derived_value}"
            )


def load_diarization(path: Path | str) -> DiarizationArtifact:
    """Read and VALIDATE one ``saea-diarization-v1`` artifact.

    Every per-window fact is re-derived from the call's segments and compared to
    the artifact's own claim (module docstring): the file is a record of a tool
    run, and a record that disagrees with itself is refused rather than trusted.
    """

    file_path = Path(path)
    try:
        document = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DiarizationError(f"cannot read diarization artifact {file_path}: {error}") from error
    if not isinstance(document, Mapping):
        raise DiarizationError(f"diarization artifact {file_path} must be a JSON object")
    if document.get("schema") != DIARIZATION_SCHEMA:
        raise DiarizationError(
            f"diarization artifact schema mismatch: expected {DIARIZATION_SCHEMA!r}, "
            f"found {document.get('schema')!r}"
        )
    if document.get("study") != STUDY_SLUG:
        raise DiarizationError("diarization artifact study identity mismatch")
    tool = document.get("tool")
    if not isinstance(tool, Mapping) or not tool:
        raise DiarizationError("diarization artifact carries no tool block")
    for key in ("lock_key", "model_sha256", "runtime", "runtime_binary_sha256", "device"):
        if not isinstance(tool.get(key), str) or not tool[key]:
            raise DiarizationError(f"diarization artifact tool block lacks {key!r}")
    run_id = document.get("run_id")
    carrier = document.get("carrier_lock_key")
    if not isinstance(run_id, str) or not run_id:
        raise DiarizationError("diarization artifact carries no run_id")
    if not isinstance(carrier, str) or not carrier:
        raise DiarizationError("diarization artifact carries no carrier_lock_key")
    window_seconds = _number(document.get("window_seconds"), "window_seconds")
    if window_seconds <= 0:
        raise DiarizationError("window_seconds must be positive")

    rows = document.get("calls")
    if not isinstance(rows, list) or not rows:
        raise DiarizationError("diarization artifact carries no calls")
    calls: dict[str, CallDiarization] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise DiarizationError("a diarization call row is not an object")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise DiarizationError("a diarization call row has no sample_id")
        if sample_id in calls:
            raise DiarizationError(f"diarization artifact repeats call {sample_id!r}")
        audio_seconds = _number(row.get("audio_seconds"), f"call {sample_id!r} audio_seconds")
        segments = _segments(row.get("segments"), sample_id)
        claimed_windows = row.get("windows")
        if not isinstance(claimed_windows, list) or not claimed_windows:
            raise DiarizationError(f"call {sample_id!r} carries no windows")
        grid = window_grid(audio_seconds, window_seconds)
        if len(grid) != len(claimed_windows):
            raise DiarizationError(
                f"call {sample_id!r} carries {len(claimed_windows)} windows but its "
                f"{audio_seconds}s of audio tile into {len(grid)} at {window_seconds}s"
            )
        windows: list[WindowSpeakers] = []
        for index, (claimed, (start, end)) in enumerate(zip(claimed_windows, grid), start=1):
            if not isinstance(claimed, Mapping):
                raise DiarizationError(f"call {sample_id!r} window {index} is not an object")
            window_identifier = claimed.get("window_id")
            if not isinstance(window_identifier, str) or not window_identifier:
                raise DiarizationError(f"call {sample_id!r} window {index} has no window_id")
            if claimed.get("window_index") != index:
                raise DiarizationError(
                    f"call {sample_id!r} window {index} claims window_index "
                    f"{claimed.get('window_index')!r}"
                )
            for key, expected in (("start_seconds", start), ("end_seconds", end)):
                value = _number(claimed.get(key), f"call {sample_id!r} window {index} {key}")
                if abs(value - expected) > 1e-6:
                    raise DiarizationError(
                        f"call {sample_id!r} window {index} claims {key}={value} but the "
                        f"fixed {window_seconds}s grid puts it at {expected}"
                    )
            derived = window_speakers(
                segments,
                window_id=window_identifier,
                window_index=index,
                start_seconds=start,
                end_seconds=end,
            )
            _check_window(claimed, derived)
            windows.append(derived)
        calls[sample_id] = CallDiarization(
            sample_id=sample_id,
            audio_seconds=audio_seconds,
            segments=segments,
            windows=tuple(windows),
        )
    return DiarizationArtifact(
        run_id=run_id,
        carrier_lock_key=carrier,
        tool=dict(tool),
        window_seconds=window_seconds,
        calls=calls,
    )


def build_call_block(
    *,
    sample_id: str,
    audio_seconds: float,
    segments: Iterable[SpeakerSegment],
    window_seconds: float,
    window_id_of: "object" = None,
) -> dict[str, object]:
    """The ``calls[]`` entry for one call, with its window block DERIVED here --
    the one place that derivation is written, so a builder and the loader can
    never disagree about what a window's dominant speaker is.

    ``window_id_of`` is the callable that names a window; the Earnings flight
    passes ``analysis.e21_window_pairing.window_id`` so the diarization windows
    and the paired-analysis windows share one id space. Left ``None``, ids are
    ``<sample_id>#w<index>`` -- the same spelling.
    """

    ordered = tuple(sorted(segments, key=lambda segment: (segment.start_seconds, segment.speaker)))
    grid = window_grid(audio_seconds, window_seconds)
    naming = window_id_of if window_id_of is not None else (
        lambda sample, index: f"{sample}#w{index:04d}"
    )
    windows = [
        window_speakers(
            ordered,
            window_id=naming(sample_id, index),
            window_index=index,
            start_seconds=start,
            end_seconds=end,
        ).as_dict()
        for index, (start, end) in enumerate(grid, start=1)
    ]
    return {
        "sample_id": sample_id,
        "audio_seconds": audio_seconds,
        "segments": [
            {
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "speaker": segment.speaker,
            }
            for segment in ordered
        ],
        "windows": windows,
    }


def speaker_roster_mapping(
    artifact: DiarizationArtifact,
    sample_id: str,
    candidate_names: Mapping[str, str],
) -> dict[str, str]:
    """Attach roster NAMES to anonymous speaker ids -- from candidates the caller
    supplies, never from anything this module reads.

    ``candidate_names`` maps a speaker id to a name the CALLER derived under its
    own exposure row, from the call's pre-meeting brief or from the frozen core's
    own outputs. This function only checks that every id it names exists in the
    artifact and that no two ids claim one name; it has no reference-reading path
    and cannot acquire one, which is the point (module docstring). An id with no
    candidate stays anonymous rather than being guessed.
    """

    call = artifact.calls.get(sample_id)
    if call is None:
        raise DiarizationError(f"diarization artifact carries no call {sample_id!r}")
    known = set(call.speakers)
    mapping: dict[str, str] = {}
    for speaker, name in candidate_names.items():
        if speaker not in known:
            raise DiarizationError(
                f"call {sample_id!r} has no speaker {speaker!r}; it has {sorted(known)}"
            )
        if not isinstance(name, str) or not name:
            raise DiarizationError(f"speaker {speaker!r} was given an empty name")
        mapping[speaker] = name
    if len(set(mapping.values())) != len(mapping):
        raise DiarizationError(
            f"call {sample_id!r} maps two speaker ids to one roster name"
        )
    return dict(sorted(mapping.items()))
