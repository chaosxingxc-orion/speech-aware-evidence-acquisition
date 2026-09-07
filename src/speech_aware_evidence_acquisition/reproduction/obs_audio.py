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

import hashlib
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

    Threshold rule: ``max(absolute_floor, min(threshold_factor * noise_floor,
    0.5 * p90))`` where the noise floor is the 10th-percentile frame RMS and
    ``p90`` the 90th. The adaptive term (factor x quietest frames) separates
    speech from a genuinely quiet floor; the ``0.5 * p90`` cap keeps a
    UNIFORMLY energetic recording (no quiet frames at all -- so the "noise
    floor" IS the signal) from being declared entirely non-speech, which
    would otherwise let the pre-trim tier silently skip a whole call; the
    absolute floor keeps digital silence non-speech regardless. A hangover
    keeps speech active ``hangover_frames`` frames past the last energetic
    frame so brief intra-word dips do not fragment spans.
    """

    if sample_rate_hz <= 0:
        raise ObsAudioError(f"sample_rate_hz must be positive, got {sample_rate_hz!r}")
    frame_len = max(1, int(frame_seconds * sample_rate_hz))
    rms = frame_rms(samples, frame_len)
    if not rms:
        return []
    ordered = sorted(rms)
    noise_floor = ordered[max(0, len(ordered) // 10 - 1)] if len(ordered) > 1 else ordered[0]
    p90 = ordered[min(len(ordered) - 1, (len(ordered) * 9) // 10)]
    threshold = max(absolute_floor, min(threshold_factor * noise_floor, 0.5 * p90))
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
# Slice tail silence (obs_slice_tail_silence_seconds, 2026-09-07)
# ---------------------------------------------------------------------------

SLICE_TAIL_SILENCE_TRANSFORM = "tail-silence"
"""Name recorded in a slice's ``preprocess`` tuple when a tail was appended.

Spelled with its length at the call site (``tail-silence-2.0s``) so the
derivation record says how much silence, not merely that there was some.
"""


def tail_silence_samples(sample_rate_hz: int, seconds: float) -> int:
    """The exact zero-sample count for ``seconds`` at ``sample_rate_hz``.

    Stated in SECONDS and resolved against the file's OWN rate, which is the
    rule ``scripts/build_cross_carrier_tail2s_media.py`` proves byte-identical
    to the pinned Earnings-22 ``transform('tail-silence-2s', ...)`` at 16 kHz
    -- there, 2.0 s is 32,000 samples. A length that is not a whole number of
    samples at this rate is REFUSED rather than silently rounded: the tail is
    the factor under test and it must be exact.
    """

    if (
        isinstance(sample_rate_hz, bool)
        or not isinstance(sample_rate_hz, int)
        or sample_rate_hz <= 0
    ):
        raise ValueError(f"sample_rate_hz must be a positive integer, got {sample_rate_hz!r}")
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        raise ValueError(f"tail seconds must be a number, got {seconds!r}")
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"tail seconds must be finite and >= 0, got {seconds!r}")
    exact = float(seconds) * sample_rate_hz
    count = int(round(exact))
    if abs(exact - count) > 1e-9:
        raise ValueError(
            f"a {seconds} s tail is not a whole number of samples at {sample_rate_hz} Hz"
        )
    return count


def append_tail_silence(
    samples: Sequence[int], sample_rate_hz: int, seconds: float
) -> array:
    """``samples`` followed by exactly ``seconds`` of digital silence.

    Strictly ADDITIVE: nothing is removed, no sample is altered, the sample
    rate never changes. ``seconds == 0`` returns the samples unchanged (a
    fresh ``array``), so the default knob value is byte-identical to the
    historical path.
    """

    tail = tail_silence_samples(sample_rate_hz, seconds)
    return array("h", samples) + array("h", bytes(2 * tail))


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
# The ONE slice encoder every obs executor calls
# ---------------------------------------------------------------------------


def encode_slice(
    slice_samples: Sequence[int],
    sample_rate_hz: int,
    *,
    preprocess: Sequence[str] = (),
    rms_target_dbfs: float = -20.0,
    tail_silence_seconds: float = 0.0,
) -> tuple[bytes, tuple[str, ...], str | None]:
    """Turn one already-cut window into the bytes that go on the wire.

    Returns ``(wav_bytes, transforms, pre_sha256)`` -- exactly the three
    values a :class:`core.model.SliceRecord` needs beyond the span, and the
    single place the transform ORDER is decided. Both obs executors (the
    sequential and parallel paths of ``reproduction.obs_loop`` and the
    openJiuwen ``FeedBuffer`` component) call this one function, so the two
    can never diverge in what they send.

    Order: raw cut -> ``rms-norm`` (when declared) -> tail silence (when
    ``tail_silence_seconds > 0``). ``pre_sha256`` is the hash of the RAW cut,
    before any declared transform, which is what
    :meth:`core.model.SliceRegistry.register` requires whenever
    ``transforms`` is non-empty.

    With ``preprocess=()`` and ``tail_silence_seconds=0.0`` this is
    ``write_wav_bytes(slice_samples, sample_rate_hz)`` and ``((), None)`` --
    byte-identical to the historical path, which is what keeps every sealed
    Earnings run reproducible.
    """

    transforms = tuple(preprocess)
    raw_bytes = write_wav_bytes(slice_samples, sample_rate_hz)
    pre_sha256: str | None = None
    if "rms-norm" in transforms:
        pre_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        slice_samples = rms_normalize(slice_samples, rms_target_dbfs)
        raw_bytes = write_wav_bytes(slice_samples, sample_rate_hz)
    if tail_silence_seconds > 0:
        if pre_sha256 is None:
            pre_sha256 = hashlib.sha256(raw_bytes).hexdigest()
        slice_samples = append_tail_silence(
            slice_samples, sample_rate_hz, tail_silence_seconds
        )
        raw_bytes = write_wav_bytes(slice_samples, sample_rate_hz)
        transforms = transforms + (
            f"{SLICE_TAIL_SILENCE_TRANSFORM}-{tail_silence_seconds:g}s",
        )
    return raw_bytes, transforms, pre_sha256


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
