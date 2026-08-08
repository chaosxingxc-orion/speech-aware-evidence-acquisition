"""Pure OBS audio/boundary functions for the obs-agent-loop policy (v1).

Owner directive (session message, 2026-08-08): the OBS layer is a
model-driven agent loop -- per sample a sliding audio buffer is transcribed
one buffer per request, the model reports a rough end-of-last-complete-
sentence boundary, and the boundary is resolved through three tiers:

1. the model's rough estimate (parsed here, :func:`parse_boundary_response`);
2. deterministic VAD snap -- move to the nearest speech/non-speech
   TRANSITION within ``+/- snap_window`` seconds of the estimate
   (:func:`vad_transitions` + :func:`nearest_transition`; owner addition
   2026-08-08: VAD transitions, not raw RMS minima);
3. clamp into ``[min_advance, max_advance]``; an unparseable/out-of-range
   estimate falls back to a fixed advance and is flagged
   (:func:`resolve_advance`).

The v1 VAD engine is a deterministic pure-Python energy VAD
(:func:`energy_vad_flags`: frame RMS + noise-floor threshold + hangover) --
the zero-dependency default (``obs_vad: "energy"``). ``webrtcvad`` is
runtime-detected by the policy layer, never imported here and never added to
``pyproject.toml`` (the dependency set is pinned at zero; the D2 artifact
fails closed on additions). Preprocessing v1 is RMS loudness normalization
only (:func:`rms_normalize`), default OFF.

Everything in this module is deterministic pure Python over stdlib
``array``/``math`` -- no numpy, no soundfile, no filesystem, no model. That
is a determinism guarantee, not a performance compromise a test would hide:
the same samples produce the same flags/bytes on every platform, so the
slice/derivation hashes the payload-binding rail re-verifies are stable.
"""

from __future__ import annotations

import io
import math
import re
import wave
from array import array
from typing import Sequence

INT16_FULL_SCALE = 32768.0
DEFAULT_VAD_FRAME_SECONDS = 0.03
# Sentence-final punctuation for the deterministic acceptance cut (Latin +
# CJK full-width; the ellipsis counts as sentence-final for cut purposes).
SENTENCE_FINAL_CHARS = ".!?…。！？"

_BOUNDARY_LINE = re.compile(
    r"^\s*BOUNDARY_SECONDS\s*[:=]\s*([0-9]+(?:\.[0-9]+)?)\s*$", re.IGNORECASE
)
_TRANSCRIPT_LABEL = re.compile(r"^\s*TRANSCRIPT\s*:\s*", re.IGNORECASE)


class ObsAudioError(RuntimeError):
    """A pure OBS audio/boundary function was given unusable inputs."""


# ---------------------------------------------------------------------------
# Frame energy + energy VAD
# ---------------------------------------------------------------------------


def frame_rms(samples: Sequence[int], frame_len: int) -> list[float]:
    """RMS per non-overlapping frame (last partial frame included)."""

    if isinstance(frame_len, bool) or not isinstance(frame_len, int) or frame_len <= 0:
        raise ObsAudioError(f"frame_len must be a positive integer, got {frame_len!r}")
    out: list[float] = []
    total = len(samples)
    for start in range(0, total, frame_len):
        frame = samples[start : start + frame_len]
        acc = 0
        for value in frame:
            acc += value * value
        out.append(math.sqrt(acc / len(frame)))
    return out


def energy_vad_flags(
    samples: Sequence[int],
    sample_rate_hz: int,
    *,
    frame_seconds: float = DEFAULT_VAD_FRAME_SECONDS,
    threshold_factor: float = 3.0,
    absolute_floor: float = 30.0,
    hangover_frames: int = 5,
) -> list[bool]:
    """Deterministic energy VAD: one speech/non-speech flag per frame.

    Threshold = ``max(absolute_floor, threshold_factor * noise_floor)`` where
    the noise floor is the 10th-percentile frame RMS -- adaptive to the
    recording's own quiet frames, with an absolute floor so an all-loud
    signal never declares its quietest moments "silence" spuriously and an
    all-digital-silence signal never divides by zero. A hangover keeps speech
    active ``hangover_frames`` frames past the last energetic frame so brief
    intra-word dips do not fragment spans.
    """

    if sample_rate_hz <= 0:
        raise ObsAudioError(f"sample_rate_hz must be positive, got {sample_rate_hz!r}")
    frame_len = max(1, int(frame_seconds * sample_rate_hz))
    rms = frame_rms(samples, frame_len)
    if not rms:
        return []
    noise_floor = sorted(rms)[max(0, len(rms) // 10 - 1)] if len(rms) > 1 else rms[0]
    threshold = max(absolute_floor, threshold_factor * noise_floor)
    flags = [value > threshold for value in rms]
    with_hangover = list(flags)
    countdown = 0
    for index, active in enumerate(flags):
        if active:
            countdown = hangover_frames
        elif countdown > 0:
            with_hangover[index] = True
            countdown -= 1
    return with_hangover


def nonspeech_spans(
    flags: Sequence[bool], frame_seconds: float, *, min_seconds: float
) -> list[tuple[float, float]]:
    """Maximal non-speech ``(start_s, end_s)`` spans lasting >= ``min_seconds``."""

    spans: list[tuple[float, float]] = []
    run_start: int | None = None
    for index, active in enumerate(list(flags) + [True]):  # sentinel closes a tail run
        if not active and run_start is None:
            run_start = index
        elif active and run_start is not None:
            start_s = run_start * frame_seconds
            end_s = index * frame_seconds
            if end_s - start_s >= min_seconds:
                spans.append((start_s, end_s))
            run_start = None
    return spans


def vad_transitions(flags: Sequence[bool], frame_seconds: float) -> list[float]:
    """Times (seconds) where the VAD flag changes state -- the candidate
    boundary points tier 2 snaps to."""

    return [
        index * frame_seconds
        for index in range(1, len(flags))
        if flags[index] != flags[index - 1]
    ]


def nearest_transition(
    transitions: Sequence[float], t: float, window: float
) -> float | None:
    """The transition nearest ``t`` within ``+/- window`` seconds, else None."""

    best: float | None = None
    for candidate in transitions:
        if abs(candidate - t) <= window and (
            best is None or abs(candidate - t) < abs(best - t)
        ):
            best = candidate
    return best


# ---------------------------------------------------------------------------
# Preprocessing (v1: RMS loudness normalization only, default OFF)
# ---------------------------------------------------------------------------


def rms_normalize(samples: Sequence[int], target_dbfs: float) -> array:
    """Scale int16 samples so overall RMS hits ``target_dbfs`` (dB re full
    scale). Pure gain, no dynamics; values clip at the int16 rails rather
    than wrapping. Digital silence is returned unchanged."""

    acc = 0
    for value in samples:
        acc += value * value
    if not len(samples) or acc == 0:
        return array("h", samples)
    current_rms = math.sqrt(acc / len(samples))
    target_rms = INT16_FULL_SCALE * (10.0 ** (target_dbfs / 20.0))
    gain = target_rms / current_rms
    return array(
        "h",
        (min(32767, max(-32768, int(round(value * gain)))) for value in samples),
    )


# ---------------------------------------------------------------------------
# WAV bytes (deterministic: stdlib wave writer, 44-byte canonical header)
# ---------------------------------------------------------------------------


def write_wav_bytes(samples: Sequence[int], sample_rate_hz: int) -> bytes:
    """16-bit mono PCM WAV bytes for ``samples`` -- deterministic for the
    same inputs (stdlib ``wave`` writes no metadata chunks)."""

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(array("h", samples).tobytes())
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Boundary-response parsing and the deterministic acceptance cut
# ---------------------------------------------------------------------------


def parse_boundary_response(text: str) -> tuple[str, float | None]:
    """Split a model response into (transcript, boundary_seconds).

    Exact rule: the LAST line matching ``BOUNDARY_SECONDS: <number>`` supplies
    the boundary; the transcript is everything BEFORE that line (trailing
    lines after it are dropped -- the frozen template puts the boundary line
    last, so anything after it is model overflow, not transcript). A leading
    ``TRANSCRIPT:`` label is stripped. No parseable boundary line -> the whole
    text is transcript and the boundary is ``None`` (the caller's fallback
    tier fires).
    """

    lines = text.split("\n")
    boundary: float | None = None
    boundary_index: int | None = None
    for index, line in enumerate(lines):
        match = _BOUNDARY_LINE.fullmatch(line)
        if match is not None:
            boundary = float(match.group(1))
            boundary_index = index
    transcript_lines = lines[:boundary_index] if boundary_index is not None else lines
    transcript = "\n".join(transcript_lines)
    transcript = _TRANSCRIPT_LABEL.sub("", transcript, count=1)
    return transcript.strip(), boundary


def accept_up_to_boundary(text: str, fraction: float) -> tuple[str, str]:
    """Deterministic acceptance cut: keep the transcript up to the boundary's
    share of the text, dropped trailing partial sentence removed.

    Exact rule: ``limit = round(len(text) * clamp(fraction, 0, 1))``; within
    ``text[:limit]`` find the LAST sentence-final character
    (``SENTENCE_FINAL_CHARS``) and accept through it (inclusive). If the
    window contains no sentence-final character, accept the raw
    ``text[:limit]`` cut unchanged (dropping everything would lose real
    content; the seam lands mid-clause and the next buffer re-covers it).
    ``fraction >= 1`` accepts everything; ``fraction <= 0`` accepts nothing.
    """

    if fraction >= 1.0:
        return text, ""
    if fraction <= 0.0 or not text:
        return "", text
    limit = int(round(len(text) * fraction))
    if limit <= 0:
        return "", text
    window = text[:limit]
    cut = max(window.rfind(char) for char in SENTENCE_FINAL_CHARS)
    if cut >= 0:
        return text[: cut + 1], text[cut + 1 :]
    return window, text[limit:]


# ---------------------------------------------------------------------------
# Three-tier boundary resolution
# ---------------------------------------------------------------------------


def resolve_advance(
    estimate: float | None,
    *,
    transitions: Sequence[float],
    snap_window: float,
    min_advance: float,
    max_advance: float,
    fallback_advance: float,
    buffer_seconds: float,
) -> dict[str, object]:
    """Resolve the model's rough boundary estimate into the actual buffer
    advance, through the three tiers (module docstring). Returns every tier's
    value for the OBS trace record: ``{"estimate", "snapped", "advance",
    "clamped", "fallback"}`` -- ``snapped`` is None when no transition lay
    within the window (or on the fallback path).
    """

    usable = (
        estimate is not None
        and isinstance(estimate, (int, float))
        and not isinstance(estimate, bool)
        and math.isfinite(estimate)
        and 0.0 < float(estimate) <= buffer_seconds + 1.0
    )
    if not usable:
        advance = min(max(fallback_advance, min_advance), max_advance)
        return {
            "estimate": estimate if isinstance(estimate, (int, float)) else None,
            "snapped": None,
            "advance": advance,
            "clamped": advance != fallback_advance,
            "fallback": True,
        }
    target = min(float(estimate), buffer_seconds)
    snapped = nearest_transition(transitions, target, snap_window)
    resolved = snapped if snapped is not None else target
    advance = min(max(resolved, min_advance), max_advance)
    return {
        "estimate": float(estimate),
        "snapped": snapped,
        "advance": advance,
        "clamped": advance != resolved,
        "fallback": False,
    }
