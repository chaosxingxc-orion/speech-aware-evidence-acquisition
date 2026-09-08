"""The E21-LOOP-1 Reviewer, applied to a sealed Earnings-21 draft.

One authority for two readers
------------------------------
``scripts/e21_loop_judge_receipt.py`` prices the judge inventory against the
ConEC alignment and ``scripts/build_e21_relisten_plan.py`` turns the same
flags into the cell's hash-pinned re-listen plan. If those two computed the
flags separately the plan could be built from a different criticism than the
one that was measured, which is precisely the defect a receipt exists to
prevent. Both therefore call :func:`window_flags` here, and the plan records
the judge ids and versions it was built from.

What this module may read
--------------------------
The ConEC participant roster, through ``core.evidence``'s own registered
reader, and nothing else: no reference transcript, no ``wer_tags`` sidecar, no
timestamp file, no score file. The judges themselves are gold-free by
construction -- that is what makes them legal inside a loop -- so the flags
this module produces could have been computed at run time by the flight
itself. They are computed ahead of it only because a plan fixes every position
before the first contact.

Heavy imports stay inside the functions that use them, the discipline the
whole ``analysis`` package follows.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

#: The brief cap KC-E1 and KC-E1f both flew, and the one E21-LOOP-1 supplies.
BRIEF_MAX_ENTRIES_PER_CLASS = 12

#: The judges the cell's Reviewer runs on the sealed pass-1 draft. The
#: substitution-alignment judge is deliberately NOT here: on a pass-1 draft its
#: predecessor is the draft itself, so it can only report a perfect alignment.
#: It belongs after the Solve, where the delivery rule's refusals are what it
#: reports, and the receipt measures that it flags nothing here rather than
#: assuming it.
DRAFT_JUDGE_IDS = (
    "e21-brief-name-near-miss-v1",
    "earnings-numeric-format-flag-v1",
)


class LoopFlagError(RuntimeError):
    """A Reviewer input is malformed -- fail closed, never guess."""


def brief_classes(
    lock: Mapping[str, object],
    data_root: Path,
    sample_id: str,
    *,
    carrier_lock_key: str = "earnings21-original",
    max_entries: int = BRIEF_MAX_ENTRIES_PER_CLASS,
) -> tuple[list[str], list[str]]:
    """This call's PERSON and ORG brief entries, at the flown cap.

    Read through the SAME registered reader the evidence source uses and split
    by the SAME registered class builders the brief renderer uses, so the judge
    is priced against the entries the Solver would actually be shown rather
    than a second hand-rolled parse of the roster file.

    PERSON entries are the roster's own NAME fields rather than the rendered
    ``Name (role)`` lines: a role is not a person name, and admitting role
    words ("president", "operations") as near-miss targets would make the judge
    fire on ordinary vocabulary.
    """

    from ..core import class_lists  # noqa: PLC0415 (import cost)
    from ..core import evidence as evidence_module  # noqa: PLC0415

    raw = evidence_module._conec_names(lock, data_root, sample_id, carrier_lock_key)[0]
    entries = class_lists.roster_entries(raw.content)
    people = class_lists._dedupe([name for name, _role in entries])
    organizations = class_lists.affiliation_class(entries)
    return (people[:max_entries], organizations[:max_entries])


def window_flags(
    draft: str,
    person_terms: Sequence[str],
    org_terms: Sequence[str],
    *,
    judge_ids: Sequence[str] = DRAFT_JUDGE_IDS,
    params: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, list[tuple[int, int]]]:
    """``{judge id: [(start, end), ...]}`` over the draft's RAW whitespace
    words, for one window.

    Every judge's own span convention is honoured and then normalised to raw
    words, because that is the space the re-listen plan converts to seconds:

    * ``e21-brief-name-near-miss-v1`` already flags raw-word spans;
    * ``earnings-numeric-format-flag-v1`` flags WHISPER-NORMALIZED word spans,
      so a flagged normalized index is mapped back to the raw word that
      produced it through the same prefix-normalization the window-pairing
      instrument uses. A normalized token the normalizer merged across two raw
      words is charged to the EARLIER one, the convention that instrument
      already applies at the window grain.

    Returns an empty list per judge rather than raising when the draft is
    empty: a window with no text has nothing to criticise, and it is the
    caller's business whether that is worth a contact (it is not).
    """

    from ..core.base import JUDGES  # noqa: PLC0415 (import cost)
    from ..core import policies as _policies  # noqa: PLC0415,F401 (registries)

    material_for = {
        "e21-brief-name-near-miss-v1": {
            "person_terms": list(person_terms),
            "org_terms": list(org_terms),
        },
        "earnings-numeric-format-flag-v1": {},
    }
    words = draft.split()
    found: dict[str, list[tuple[int, int]]] = {}
    normalized_to_raw: list[int] | None = None
    for judge_id in judge_ids:
        if judge_id not in material_for:
            raise LoopFlagError(
                f"judge {judge_id!r} has no declared material in this module; a "
                "judge whose signal is not wired would report 'nothing to "
                "criticise' for the wrong reason"
            )
        material = dict(material_for[judge_id])
        material.update(dict((params or {}).get(judge_id, {})))
        if not words:
            found[judge_id] = []
            continue
        verdict = JUDGES.resolve(judge_id)(draft, material, {})
        spans: list[tuple[int, int]] = []
        for flag in verdict.flags:
            if flag.span is None:
                continue
            if judge_id == "earnings-numeric-format-flag-v1":
                if normalized_to_raw is None:
                    normalized_to_raw = _normalized_to_raw(words)
                mapped = [
                    normalized_to_raw[index]
                    for index in range(flag.span[0], flag.span[1])
                    if 0 <= index < len(normalized_to_raw)
                ]
                if not mapped:
                    continue
                spans.append((min(mapped), max(mapped) + 1))
            else:
                spans.append((flag.span[0], min(flag.span[1], len(words))))
        found[judge_id] = _merged(spans)
    return found


def _normalized_to_raw(words: Sequence[str]) -> list[int]:
    """For each whole-string-normalized word of this draft, the index of the
    raw word that produced it (module docstring's charging convention)."""

    from ..reproduction.asr_wer_whisper import (  # noqa: PLC0415 (import cost)
        normalize_whisper_english,
    )

    owner: list[int] = []
    prefix = ""
    previous = 0
    for index, word in enumerate(words):
        prefix = f"{prefix} {word}" if prefix else word
        count = len(normalize_whisper_english(prefix).split())
        owner.extend([index] * max(0, count - previous))
        previous = count
    return owner


def _merged(spans: Sequence[tuple[int, int]]) -> list[tuple[int, int]]:
    """Overlapping or abutting spans folded into one, in ascending order --
    the shape the plan's union arithmetic expects."""

    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if end <= start:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def union_spans(flags: Mapping[str, Sequence[tuple[int, int]]]) -> list[tuple[int, int]]:
    """Every judge's flags on one window, merged -- the inventory's own
    criticism of that window, and what the re-listen plan widens."""

    return _merged([span for spans in flags.values() for span in spans])


__all__ = [
    "BRIEF_MAX_ENTRIES_PER_CLASS",
    "DRAFT_JUDGE_IDS",
    "LoopFlagError",
    "brief_classes",
    "union_spans",
    "window_flags",
]
