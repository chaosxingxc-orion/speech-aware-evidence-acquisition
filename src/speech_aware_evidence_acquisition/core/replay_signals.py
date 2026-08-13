"""Pure signal-extraction functions for the future listen-score-replay
policy's SCORE stage (``core.model.transport`` module docstring,
2026-08-12: "prep infrastructure for the future listen-score-replay
policy"). No policy integration yet -- nothing here reads a live
``FrozenCoreAdapter`` response, touches a model, or writes a trace record.

Two signal families, both already grounded by the D-1 probe
(``docs/readiness/2026-08-09-d1-signal-probe.md``):

1. the D-1-measured words/speech-second CATASTROPHE detector
   (:func:`words_per_second`, :func:`is_catastrophic`) -- a healthy
   obs-agent-loop run measured 2.40 words/speech-second against a collapsed
   whole-call protocol's 0.004, a ~600x separation; the probe's stated
   consequence is that this signal is a regime detector, not a
   fine-grained quality ranker (no per-call signal reached |rho| >= 0.6 at
   n=10), so the threshold below lives two orders of magnitude inside that
   gap, at words/s < 0.5;
2. per-slice token-logprob summary statistics (:func:`slice_logprob_stats`)
   -- a per-token confidence signal for whatever adapter exposes one
   (llama.cpp ``--logprobs``), and contiguous low-scoring-word span
   detection (:func:`flag_spans`) -- the span-selection primitive
   ``core.span_surgery.cut_span`` will consume once this policy is wired.

Every function here is deterministic pure Python over stdlib ``math`` only
-- no numpy, no torch, no model, no filesystem -- same discipline as
``reproduction.obs_audio``.
"""

from __future__ import annotations

import math
from typing import Sequence

# D-1-measured regime-detector threshold (module docstring; docs/readiness/
# 2026-08-09-d1-signal-probe.md): two orders of magnitude inside the
# healthy-vs-collapsed gap (2.40 vs 0.004 words/speech-second).
CATASTROPHIC_WPS_THRESHOLD = 0.5


class ReplaySignalsError(RuntimeError):
    """A pure replay-signal function was given unusable inputs."""


def _is_finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def slice_logprob_stats(
    token_logprobs: Sequence[float], *, below_threshold: float
) -> dict[str, float | int]:
    """Summary statistics over one slice's per-token log-probabilities:
    ``{"mean", "min", "p10", "count", "below_threshold_count"}``.

    ``p10`` uses the SAME "sorted, floor-indexed" convention as
    ``reproduction.obs_audio.energy_vad_flags``'s noise floor: the value at
    ``ordered[max(0, count // 10 - 1)]`` (``ordered[0]`` when ``count`` is
    1). ``count`` is the total number of tokens; ``below_threshold_count``
    counts entries strictly less than ``below_threshold`` -- the caller
    supplies the threshold explicitly, no default is baked in here (unlike
    :func:`is_catastrophic`, no D-1 measurement grounds a specific logprob
    cut yet).

    Fails closed on an empty sequence or any non-finite/non-numeric entry
    (a ``bool`` is rejected too -- ``isinstance(True, int)`` is a Python
    trap, same guard as ``obs_audio.resolve_advance``'s ``usable`` check).
    """

    values = list(token_logprobs)
    if not values:
        raise ReplaySignalsError("token_logprobs must be a non-empty sequence")
    for value in values:
        if not _is_finite_number(value):
            raise ReplaySignalsError(
                f"token_logprobs entries must be finite numbers, got {value!r}"
            )
    if not _is_finite_number(below_threshold):
        raise ReplaySignalsError(
            f"below_threshold must be a finite number, got {below_threshold!r}"
        )
    ordered = sorted(float(value) for value in values)
    count = len(ordered)
    p10_index = max(0, count // 10 - 1) if count > 1 else 0
    return {
        "mean": sum(ordered) / count,
        "min": ordered[0],
        "p10": ordered[p10_index],
        "count": count,
        "below_threshold_count": sum(1 for value in ordered if value < below_threshold),
    }


def words_per_second(word_count: int, audio_seconds: float) -> float:
    """Words spoken per second of audio -- the D-1-measured regime
    detector's input signal (module docstring; docs/readiness/
    2026-08-09-d1-signal-probe.md).

    Fails closed on a negative/non-integer ``word_count`` or a non
    -positive/non-finite ``audio_seconds`` (a zero-duration sample is
    already an invalid input, never silently divided by)."""

    if isinstance(word_count, bool) or not isinstance(word_count, int) or word_count < 0:
        raise ReplaySignalsError(
            f"word_count must be a non-negative integer, got {word_count!r}"
        )
    if not _is_finite_number(audio_seconds) or audio_seconds <= 0:
        raise ReplaySignalsError(
            f"audio_seconds must be a positive finite number, got {audio_seconds!r}"
        )
    return word_count / audio_seconds


def is_catastrophic(wps: float, threshold: float = CATASTROPHIC_WPS_THRESHOLD) -> bool:
    """D-1-measured regime detector (module docstring; docs/readiness/
    2026-08-09-d1-signal-probe.md): a healthy obs-agent-loop run measured
    2.40 words/speech-second, a collapsed whole-call protocol 0.004 -- a
    ~600x separation. The default ``threshold`` (0.5) sits two orders of
    magnitude inside that gap and is deliberately a CATASTROPHE cut, not a
    fine-grained quality ranking one -- the same probe found no per-call
    signal (including this one) rank-correlates with WER at |rho| >= 0.6.

    Fails closed on a non-finite/non-numeric ``wps``."""

    if not _is_finite_number(wps):
        raise ReplaySignalsError(f"wps must be a finite number, got {wps!r}")
    return wps < threshold


def flag_spans(
    words: Sequence[str],
    word_scores: Sequence[float],
    low_threshold: float,
    min_run: int,
) -> list[tuple[int, int]]:
    """Contiguous runs of low-scoring words: word index ``i`` is "low" when
    ``word_scores[i] < low_threshold``. Adjacent low indices merge into one
    ``(start, end)`` span with ``end`` EXCLUSIVE (Python slice convention --
    ``words[start:end]`` is the flagged run). Runs shorter than ``min_run``
    words are dropped entirely, never truncated. Deterministic: the same
    inputs always produce the same span list, in ascending ``start`` order.

    Fails closed when ``words`` and ``word_scores`` differ in length (a
    mismatch means the caller mis-paired two independently-produced lists,
    and any span reported against it would be meaningless), on a non
    -finite/non-numeric score, or on a non-positive ``min_run``."""

    words = list(words)
    word_scores = list(word_scores)
    if len(words) != len(word_scores):
        raise ReplaySignalsError(
            f"words ({len(words)}) and word_scores ({len(word_scores)}) length mismatch"
        )
    if isinstance(min_run, bool) or not isinstance(min_run, int) or min_run < 1:
        raise ReplaySignalsError(f"min_run must be a positive integer, got {min_run!r}")
    for score in word_scores:
        if not _is_finite_number(score):
            raise ReplaySignalsError(f"word_scores entries must be finite numbers, got {score!r}")
    if not _is_finite_number(low_threshold):
        raise ReplaySignalsError(f"low_threshold must be a finite number, got {low_threshold!r}")

    spans: list[tuple[int, int]] = []
    run_start: int | None = None
    for index, score in list(enumerate(word_scores)) + [(len(word_scores), None)]:
        low = score is not None and score < low_threshold
        if low and run_start is None:
            run_start = index
        elif not low and run_start is not None:
            if index - run_start >= min_run:
                spans.append((run_start, index))
            run_start = None
    return spans
