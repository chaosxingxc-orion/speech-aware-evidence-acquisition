"""The unit-draft ownership stitch: sealed speaker-turn units regrouped into
the sealed 90-second comparator windows, without a contact and without a
re-cut.

Why this module exists
----------------------
Owner Decision 13-J (2026-09-09) asks for a DRAFT-THEN-REFRESH episode on
Earnings-21: the Observe stage uses the SHORT speech to produce drafts quickly,
and the Plan stage then hands the model the LONG speech together with the prior
draft and lets it refresh the transcript once. The short-speech half already
exists and is sealed -- ``SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`` decoded all
5,122 speaker-turn units of the 44 discovery calls -- so pass 1 is NOT re-flown
here any more than KC-E1f re-flew its own. What is missing is the ARITHMETIC
that carries a 5,122-unit hypothesis onto the 1,593-window grid every Earnings
paired read is built on.

That is this module, and it is deliberately nothing else. It moves no byte of
audio, aligns no words, opens no reference layer and contacts nothing: it
decides, per unit, which window owns it, and concatenates.

The ownership rule, fixed here and quoted by the preregistration
-----------------------------------------------------------------
1. A unit is owned by the sealed window it OVERLAPS MOST (in seconds).
2. A tie goes to the EARLIER window. Windows are scanned in ascending index and
   an overlap must be strictly greater to displace the incumbent, so the rule
   is deterministic and needs no second sort key.
3. A window's DRAFT is the concatenation, in unit order, of the sealed texts of
   the units it owns, joined by a single space, empty texts contributing
   nothing -- ``reproduction.obs_loop``'s own stitch rule, applied one level
   down.

Two properties follow, and both are asserted rather than assumed.

**Monotonicity.** Units tile their call in ascending time and do not overlap
each other; windows do the same. So the owning window index is NON-DECREASING
in unit index (:func:`assert_ownership_is_monotone`). Without it the stitch
below would reorder the call's own words.

**Exact reproduction.** Because ownership is a PARTITION of the units and it is
monotone, concatenating the per-window drafts of a call in window order is the
same string as concatenating every unit's text in unit order -- which is the
sealed OBS-E1 hypothesis for that call, byte for byte
(:func:`assert_drafts_reproduce_units`). The builder refuses to write a
snapshot until that holds on all 44 calls, exactly as
``analysis.e21_window_pairing.assert_stitch_reproduces_outputs`` refuses for
the comparator.

The window that owns nothing, reported rather than smoothed over
-----------------------------------------------------------------
A window shorter than the unit covering it can lose every tie and end up owning
no unit at all. On the committed plan v2 this happens exactly TWICE in 1,593 --
``4361631#w0050`` (1.429 s) and ``4387865#w0025`` (2.573 s), both the last,
remainder window of their call -- and it costs the corpus nothing, because the
words spoken there are inside the covering unit's text and that text is
delivered by the PRECEDING window. Such a window's draft is the empty string,
it is counted in the receipt, and what a cell then does with an empty draft is
the cell's delivery rule's business, not this module's.

What this module is NOT
-----------------------
It is not a scorer, it never sees a reference transcript, a ``wer_tags``
sidecar or a gold label, it re-cuts no audio and it runs no forced alignment.
It is also not OBS-E1b's ``saea-obs-context-ownership-v1`` stitch: that one
splits the text of ONE contact between two windows by an overlap alignment and
can drop a word; this one moves whole sealed unit texts and provably drops
none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .e21_window_pairing import WindowSpan, window_id

#: The schema a built snapshot's rows declare they were stitched under.
STITCH_RULE_ID = "saea-e21-unit-draft-majority-overlap-v1"


class UnitDraftStitchError(RuntimeError):
    """An ownership stitch input is malformed -- fail closed, never guess."""


@dataclass(frozen=True)
class WindowDraft:
    """One sealed 90-second window and the unit draft it owns.

    ``window_id``/``sample_id``/``window_index``/bounds are the COMPARATOR's
    own, because the window grid this draft is carried onto is the comparator's
    grid and a DR-1 pass-2 contact tiles exactly it. ``text`` is model output
    from the OTHER sealed run and never leaves ``SPEECHRL_DATA_DIR``.
    """

    window_id: str
    sample_id: str
    window_index: int
    start_seconds: float
    end_seconds: float
    audio_seconds: float
    text: str
    unit_ids: tuple[str, ...]
    saturated_units: int

    @property
    def unit_count(self) -> int:
        return len(self.unit_ids)

    @property
    def empty(self) -> bool:
        return not self.text


def overlap_seconds(
    first: tuple[float, float], second: tuple[float, float]
) -> float:
    """Seconds two half-open spans share; never negative."""

    return max(0.0, min(first[1], second[1]) - max(first[0], second[0]))


def assign_units_to_windows(
    units: Sequence[WindowSpan], windows: Sequence[WindowSpan]
) -> tuple[int, ...]:
    """The owning window index (0-based) of every unit, in unit order.

    Module docstring for the rule. Refuses a unit that overlaps no window at
    all, because a unit outside the comparator's own tiling would mean the two
    sealed runs did not hear the same call.
    """

    if not windows:
        raise UnitDraftStitchError("a call with no sealed window cannot own a draft")
    if not units:
        raise UnitDraftStitchError("a call with no sealed unit carries no draft")
    bounds = [(float(span.start_seconds), float(span.end_seconds)) for span in windows]
    owners: list[int] = []
    for unit in units:
        span = (float(unit.start_seconds), float(unit.end_seconds))
        best_index = -1
        best_overlap = 0.0
        for index, window in enumerate(bounds):
            shared = overlap_seconds(span, window)
            if shared > best_overlap:
                best_overlap = shared
                best_index = index
        if best_index < 0:
            raise UnitDraftStitchError(
                f"unit {unit.identifier!r} [{span[0]}, {span[1]}) overlaps none of the "
                f"{len(windows)} sealed windows of {unit.sample_id!r}"
            )
        owners.append(best_index)
    return tuple(owners)


def assert_ownership_is_monotone(
    owners: Sequence[int], units: Sequence[WindowSpan]
) -> None:
    """Refuse an assignment that would reorder a call's own words."""

    for position in range(1, len(owners)):
        if owners[position] < owners[position - 1]:
            raise UnitDraftStitchError(
                f"unit {units[position].identifier!r} is owned by window "
                f"{owners[position]} while its predecessor "
                f"{units[position - 1].identifier!r} is owned by "
                f"{owners[position - 1]}; ownership must be non-decreasing or the "
                "stitch reorders the call"
            )


def stitch_call(
    sample_id: str,
    units: Sequence[WindowSpan],
    windows: Sequence[WindowSpan],
) -> tuple[WindowDraft, ...]:
    """One call's per-window unit drafts, in window order.

    Every window of the call is returned, including one that owns no unit; the
    caller decides what an empty draft means and this module only reports it.
    """

    for span in (*units, *windows):
        if span.sample_id != sample_id:
            raise UnitDraftStitchError(
                f"span {span.identifier!r} belongs to {span.sample_id!r}, not "
                f"{sample_id!r}"
            )
    owners = assign_units_to_windows(units, windows)
    assert_ownership_is_monotone(owners, units)
    owned: list[list[WindowSpan]] = [[] for _ in windows]
    for unit, index in zip(units, owners):
        owned[index].append(unit)
    drafts: list[WindowDraft] = []
    for index, window in enumerate(windows):
        members = owned[index]
        drafts.append(
            WindowDraft(
                window_id=window.identifier,
                sample_id=sample_id,
                window_index=window.window_index,
                start_seconds=float(window.start_seconds),
                end_seconds=float(window.end_seconds),
                audio_seconds=float(window.audio_seconds),
                text=" ".join(unit.text for unit in members if unit.text),
                unit_ids=tuple(unit.identifier for unit in members),
                saturated_units=sum(1 for unit in members if unit.saturated),
            )
        )
    return tuple(drafts)


def stitched_draft_text(drafts: Sequence[WindowDraft]) -> str:
    """``reproduction.obs_loop``'s stitch rule over the per-window drafts."""

    return " ".join(draft.text for draft in drafts if draft.text)


def assert_drafts_reproduce_units(
    drafts: Sequence[WindowDraft], units: Sequence[WindowSpan]
) -> None:
    """The proof the whole cell rests on, per call.

    Concatenating the per-window drafts must be the same string as
    concatenating the sealed units -- which
    ``analysis.e21_window_pairing.assert_stitch_reproduces_outputs`` has
    already proved equals the sealed ``outputs.jsonl`` hypothesis for the call.
    Chaining the two is what lets a receipt say the stitch reproduces OBS-E1's
    sealed corpus text exactly.
    """

    rebuilt = stitched_draft_text(drafts)
    sealed = " ".join(unit.text for unit in units if unit.text)
    if rebuilt != sealed:
        raise UnitDraftStitchError(
            "the per-window unit drafts do not rebuild the call's sealed unit stitch "
            f"({len(rebuilt)} chars vs {len(sealed)})"
        )


def stitch_corpus(
    units_by_sample: Mapping[str, Sequence[WindowSpan]],
    windows_by_sample: Mapping[str, Sequence[WindowSpan]],
) -> dict[str, tuple[WindowDraft, ...]]:
    """Every call's per-window drafts, proved call by call as they are built."""

    if set(units_by_sample) != set(windows_by_sample):
        raise UnitDraftStitchError(
            "the unit run and the window run cover different calls: "
            f"units-only {sorted(set(units_by_sample) - set(windows_by_sample))}, "
            f"windows-only {sorted(set(windows_by_sample) - set(units_by_sample))}"
        )
    drafts: dict[str, tuple[WindowDraft, ...]] = {}
    for sample_id in sorted(units_by_sample):
        call_drafts = stitch_call(
            sample_id, units_by_sample[sample_id], windows_by_sample[sample_id]
        )
        assert_drafts_reproduce_units(call_drafts, units_by_sample[sample_id])
        drafts[sample_id] = call_drafts
    return drafts


def assert_window_identity(
    drafts: Mapping[str, Sequence[WindowDraft]],
    windows_by_sample: Mapping[str, Sequence[WindowSpan]],
) -> None:
    """Every draft names the comparator's own window, id and bounds included.

    ``reproduction.repair_loop.RepairWindowHook`` matches a cut window against
    its bound predecessor's bounds to 1e-6 s and refuses otherwise, so a draft
    row whose identity drifted from the comparator's would fail at the first
    contact of a flight rather than here. It fails here.
    """

    for sample_id, call_drafts in drafts.items():
        windows = windows_by_sample[sample_id]
        if len(call_drafts) != len(windows):
            raise UnitDraftStitchError(
                f"sample {sample_id!r} carries {len(call_drafts)} drafts for "
                f"{len(windows)} sealed windows"
            )
        for draft, window in zip(call_drafts, windows):
            expected = window_id(sample_id, window.window_index)
            if draft.window_id != expected or draft.window_index != window.window_index:
                raise UnitDraftStitchError(
                    f"draft {draft.window_id!r} does not name sealed window "
                    f"{expected!r}"
                )
            for name, drafted, sealed in (
                ("start", draft.start_seconds, window.start_seconds),
                ("end", draft.end_seconds, window.end_seconds),
                ("audio", draft.audio_seconds, window.audio_seconds),
            ):
                if abs(float(drafted) - float(sealed)) > 1e-9:
                    raise UnitDraftStitchError(
                        f"draft {draft.window_id!r} {name} {drafted} does not match the "
                        f"sealed window's {sealed}"
                    )


__all__ = [
    "STITCH_RULE_ID",
    "UnitDraftStitchError",
    "WindowDraft",
    "assert_drafts_reproduce_units",
    "assert_ownership_is_monotone",
    "assert_window_identity",
    "assign_units_to_windows",
    "overlap_seconds",
    "stitch_call",
    "stitch_corpus",
    "stitched_draft_text",
]
