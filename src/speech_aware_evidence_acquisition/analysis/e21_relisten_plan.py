"""The E21-LOOP-1 SELECTIVE RE-LISTEN plan: which windows are heard again,
over which seconds, and against which slice of their own pass-1 text.

What it is
----------
KC-E1f repaired every one of the sealed comparator's 1,593 fixed 90-second
windows, each with the whole window's audio and the whole window's pass-1
text. E21-LOOP-1 changes exactly one thing: **the Reviewer decides which
windows are heard again, and the Observer hands the Solver a narrower cut of
that window's own audio with the matching slice of its own pass-1 text.** An
unflagged window is never contacted and delivers its predecessor verbatim.

Like ``analysis.e21_speaker_turn_units``' unit plan, and for the same reason,
this is DATA rather than code: every position is fixed before the first
contact, hash-pinned in the composed config, and re-proved by the runtime
loader against the bytes actually loaded. What is new is the shape of the
proof: a re-listen plan deliberately does NOT tile its call.

The proof obligation
--------------------
:func:`assert_relisten_units` refuses a plan unless, per call:

1. units are listed in ``unit_index`` order, numbered from 1;
2. every unit names a distinct ``parent_window_index``, in ascending order --
   one re-listen per flagged window, which is what makes the contact count
   equal the flagged-window count;
3. every unit's span lies inside its parent window's own span (a re-listen is
   a NARROWER look at audio the comparator already decoded, never new audio);
4. every unit is at least :data:`MIN_RELISTEN_SECONDS` long, or exactly its
   parent window when the parent is shorter -- the refusal-to-shrink rule;
5. every unit's predecessor word range is a non-empty half-open range inside
   its parent window's own pass-1 word count;
6. units do not overlap and are ordered in time.

Why the minimum length, and where the number comes from
--------------------------------------------------------
The OBS-E1 PERSON harm decomposition
(``docs/readiness/2026-09-08-e21-obs-e1-person-harm-decomposition-v1.md``)
measured what happens when Earnings-21 audio is delivered in short pieces:
units under 10 s carry **78.7 %** of the PERSON harm while holding 23.3 % of
the PERSON words, the duration ladder is monotone (under 3 s −14.545, 3–5 s
−5.469, 5–10 s −5.656, 10–30 s −2.541, 30–60 s −0.397) and units of 60 s or
more are BETTER than the 90-second windows. A re-cut of a two-word span is a
two-second unit, which is the worst rung of that ladder. So the plan widens
every flagged span by a context margin on each side and then refuses to go
below a floor -- and the preregistration carries the ladder, because a 10-second
floor still sits in a band the decomposition measured as harmful AS A
TRANSPORT. This is not a transport: the Solver is given the span's own pass-1
text as well, and the twin prices what the re-cut costs.

Position in seconds is DERIVED, and says so
--------------------------------------------
Earnings-21 ships no word timestamps (the harm decomposition checked: all
362,747 ``ts``/``endTs`` cells on the 44 discovery calls are empty), and a
draft carries none either. A flagged word span is therefore converted to
seconds by its window's OWN LOCAL RATE -- window seconds divided by window
draft words -- exactly the convention the harm decomposition uses, and the
inverse conversion brings the re-cut bounds back to a word range. It is an
attribution, never an alignment, and both directions use the same rate so
they are mutually consistent by construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

#: The plan schema ``reproduction.obs_loop`` consumes beside the speaker-turn
#: unit plans. A separate schema rather than a flag on theirs, because the two
#: carry DIFFERENT proof obligations and a loader that guessed which to apply
#: would be the defect this separation prevents.
RELISTEN_PLAN_SCHEMA = "saea-e21-relisten-plan-v1"

#: Seconds of the parent window added on each side of a flagged span. The
#: OBS-E1 harm decomposition prices +3 / +5 / +10 s; +5 is the operating point
#: E21-LOOP-1 preregisters (coordinator direction, 2026-09-08).
DEFAULT_CONTEXT_MARGIN_SECONDS = 5.0

#: The refusal-to-shrink floor: a re-listen window is never shorter than this,
#: however short the flagged span is (module docstring).
MIN_RELISTEN_SECONDS = 10.0

#: ``end_cut`` is required by the unit-plan loader's own validation and names
#: how a unit's right edge was chosen. A re-listen edge is neither a pause nor
#: a speaker change: it is a re-cut of a fixed window.
RELISTEN_END_CUT = "recut"


class RelistenPlanError(RuntimeError):
    """A re-listen plan input is malformed -- fail closed, never guess."""


@dataclass(frozen=True)
class ParentWindow:
    """One fixed 90-second window of the sealed comparator, as the plan sees
    it: its bounds, and how many whitespace words its pass-1 text carries."""

    window_index: int
    start_seconds: float
    end_seconds: float
    draft_words: int

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class RelistenUnit:
    """One re-listen: a narrower span of one flagged window, plus the half-open
    word range of that window's pass-1 text the span corresponds to."""

    sample_id: str
    unit_index: int
    parent_window_index: int
    start_seconds: float
    end_seconds: float
    predecessor_word_start: int
    predecessor_word_end: int

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    def as_json(self, *, unit_id: str) -> dict[str, object]:
        return {
            "unit_id": unit_id,
            "unit_index": self.unit_index,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "parent_window_index": self.parent_window_index,
            "predecessor_word_start": self.predecessor_word_start,
            "predecessor_word_end": self.predecessor_word_end,
            "speaker": None,
            "end_cut": RELISTEN_END_CUT,
        }


def _finite(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RelistenPlanError(f"{field} must be a finite number, got {value!r}")
    number = float(value)
    if not math.isfinite(number):
        raise RelistenPlanError(f"{field} must be a finite number, got {value!r}")
    return number


def words_to_seconds(window: ParentWindow, word_index: int) -> float:
    """The second offset of draft word ``word_index`` under the window's own
    local rate (module docstring). ``word_index`` may be ``draft_words``, which
    yields the window's own end."""

    if window.draft_words <= 0:
        return window.start_seconds
    fraction = max(0.0, min(1.0, word_index / window.draft_words))
    return window.start_seconds + fraction * window.duration_seconds


def seconds_to_words(window: ParentWindow, seconds: float) -> float:
    """The inverse of :func:`words_to_seconds`, in fractional words."""

    if window.duration_seconds <= 0:
        return 0.0
    fraction = (seconds - window.start_seconds) / window.duration_seconds
    return max(0.0, min(1.0, fraction)) * window.draft_words


def recut_bounds(
    window: ParentWindow,
    spans: Sequence[tuple[int, int]],
    *,
    margin_seconds: float = DEFAULT_CONTEXT_MARGIN_SECONDS,
    min_seconds: float = MIN_RELISTEN_SECONDS,
) -> tuple[float, float]:
    """The re-listen span of one flagged window: the union of its flagged word
    spans in seconds, widened by ``margin_seconds`` on each side, then grown
    symmetrically to at least ``min_seconds``, then clamped to the window.

    The growth is symmetric ABOUT THE MIDPOINT and re-clamped, so a span that
    hits one edge of the window spends its whole floor on the other side
    rather than silently staying short.
    """

    if not spans:
        raise RelistenPlanError(
            f"window {window.window_index} has no flagged span; a re-listen unit "
            "for a window nobody criticised is a broken plan"
        )
    if margin_seconds < 0 or not math.isfinite(margin_seconds):
        raise RelistenPlanError(f"margin_seconds must be >= 0, got {margin_seconds!r}")
    if min_seconds <= 0 or not math.isfinite(min_seconds):
        raise RelistenPlanError(f"min_seconds must be > 0, got {min_seconds!r}")
    low_word = min(start for start, _end in spans)
    high_word = max(end for _start, end in spans)
    if low_word < 0 or high_word <= low_word or high_word > max(window.draft_words, 1):
        raise RelistenPlanError(
            f"window {window.window_index}: flagged span union [{low_word}, "
            f"{high_word}) does not lie in its own {window.draft_words} draft words"
        )
    start = words_to_seconds(window, low_word) - margin_seconds
    end = words_to_seconds(window, high_word) + margin_seconds
    target = min(min_seconds, window.duration_seconds)
    if end - start < target:
        middle = 0.5 * (start + end)
        start = middle - 0.5 * target
        end = middle + 0.5 * target
    if start < window.start_seconds:
        end += window.start_seconds - start
        start = window.start_seconds
    if end > window.end_seconds:
        start -= end - window.end_seconds
        end = window.end_seconds
    start = max(start, window.start_seconds)
    end = min(end, window.end_seconds)
    if end <= start:
        raise RelistenPlanError(
            f"window {window.window_index}: re-cut collapsed to [{start}, {end})"
        )
    return (start, end)


def predecessor_word_range(
    window: ParentWindow, start_seconds: float, end_seconds: float
) -> tuple[int, int]:
    """The half-open word range of the window's pass-1 text that the re-cut
    span covers, under the same local rate (module docstring).

    Rounded OUTWARD -- floor on the left, ceil on the right -- so the text the
    Solver is shown is never narrower than the audio it hears. Always
    non-empty, and always inside the window's own word count."""

    low = int(math.floor(seconds_to_words(window, start_seconds)))
    high = int(math.ceil(seconds_to_words(window, end_seconds)))
    low = max(0, min(low, max(window.draft_words - 1, 0)))
    high = max(low + 1, min(high, window.draft_words))
    return (low, high)


def build_units(
    sample_id: str,
    windows: Sequence[ParentWindow],
    flags: Mapping[int, Sequence[tuple[int, int]]],
    *,
    margin_seconds: float = DEFAULT_CONTEXT_MARGIN_SECONDS,
    min_seconds: float = MIN_RELISTEN_SECONDS,
) -> tuple[RelistenUnit, ...]:
    """One re-listen unit per flagged window of one call, in window order."""

    by_index = {window.window_index: window for window in windows}
    units: list[RelistenUnit] = []
    for position, window_index in enumerate(sorted(flags), start=1):
        window = by_index.get(window_index)
        if window is None:
            raise RelistenPlanError(
                f"call {sample_id!r}: flagged window {window_index} is not one of "
                f"this call's {len(windows)} windows"
            )
        start, end = recut_bounds(
            window,
            list(flags[window_index]),
            margin_seconds=margin_seconds,
            min_seconds=min_seconds,
        )
        word_start, word_end = predecessor_word_range(window, start, end)
        units.append(
            RelistenUnit(
                sample_id=sample_id,
                unit_index=position,
                parent_window_index=window_index,
                start_seconds=start,
                end_seconds=end,
                predecessor_word_start=word_start,
                predecessor_word_end=word_end,
            )
        )
    return tuple(units)


def assert_relisten_units(
    units: Sequence[RelistenUnit],
    windows: Sequence[ParentWindow],
    *,
    min_seconds: float = MIN_RELISTEN_SECONDS,
    tolerance: float = 1e-6,
) -> None:
    """The proof obligation of the module docstring, in order.

    Deliberately NOT a tiling proof: a re-listen plan covers only the windows
    the Reviewer criticised, and demanding coverage of the call would make the
    selective loop unexpressible."""

    if not units:
        raise RelistenPlanError(
            "a call in a re-listen plan carries no units; a call with nothing to "
            "re-hear belongs OUT of the plan, never in it with an empty list"
        )
    by_index = {window.window_index: window for window in windows}
    previous_parent = 0
    previous_end = -math.inf
    for position, unit in enumerate(units, start=1):
        if unit.unit_index != position:
            raise RelistenPlanError(
                f"unit #{position} declares unit_index {unit.unit_index}; units must "
                "be listed in unit_index order, numbered from 1"
            )
        window = by_index.get(unit.parent_window_index)
        if window is None:
            raise RelistenPlanError(
                f"unit {unit.unit_index} names parent window "
                f"{unit.parent_window_index}, which this call does not have"
            )
        if unit.parent_window_index <= previous_parent:
            raise RelistenPlanError(
                f"unit {unit.unit_index} names parent window "
                f"{unit.parent_window_index} after {previous_parent}; one re-listen "
                "per flagged window, in ascending window order"
            )
        previous_parent = unit.parent_window_index
        if (
            unit.start_seconds < window.start_seconds - tolerance
            or unit.end_seconds > window.end_seconds + tolerance
        ):
            raise RelistenPlanError(
                f"unit {unit.unit_index} spans [{unit.start_seconds}, "
                f"{unit.end_seconds}) which leaves its parent window's "
                f"[{window.start_seconds}, {window.end_seconds}); a re-listen is a "
                "narrower look at audio the comparator already decoded"
            )
        floor = min(min_seconds, window.duration_seconds)
        if unit.duration_seconds < floor - tolerance:
            raise RelistenPlanError(
                f"unit {unit.unit_index} is {unit.duration_seconds} s, under the "
                f"refusal-to-shrink floor of {floor} s"
            )
        if unit.start_seconds < previous_end - tolerance:
            raise RelistenPlanError(
                f"unit {unit.unit_index} starts at {unit.start_seconds}, before the "
                f"previous unit ended at {previous_end}"
            )
        previous_end = unit.end_seconds
        if (
            unit.predecessor_word_start < 0
            or unit.predecessor_word_end <= unit.predecessor_word_start
            or unit.predecessor_word_end > window.draft_words
        ):
            raise RelistenPlanError(
                f"unit {unit.unit_index} names predecessor words "
                f"[{unit.predecessor_word_start}, {unit.predecessor_word_end}) "
                f"outside its parent window's own {window.draft_words}"
            )


def plan_document(
    *,
    source: str,
    margin_seconds: float,
    min_seconds: float,
    calls: Sequence[Mapping[str, object]],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """The plan artifact, in the shape ``reproduction.obs_loop`` consumes."""

    if source not in {"judges", "seeded-random"}:
        raise RelistenPlanError(
            f"source must be 'judges' or 'seeded-random', got {source!r}"
        )
    return {
        "schema": RELISTEN_PLAN_SCHEMA,
        "flag_source": source,
        "context_margin_seconds": _finite(margin_seconds, field="context_margin_seconds"),
        "min_relisten_seconds": _finite(min_seconds, field="min_relisten_seconds"),
        "provenance": dict(provenance),
        "calls": list(calls),
    }


__all__ = [
    "DEFAULT_CONTEXT_MARGIN_SECONDS",
    "MIN_RELISTEN_SECONDS",
    "RELISTEN_END_CUT",
    "RELISTEN_PLAN_SCHEMA",
    "ParentWindow",
    "RelistenPlanError",
    "RelistenUnit",
    "assert_relisten_units",
    "build_units",
    "plan_document",
    "predecessor_word_range",
    "recut_bounds",
    "seconds_to_words",
    "words_to_seconds",
]
