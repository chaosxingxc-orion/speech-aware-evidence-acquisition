"""Where a PERSON name is lost: the model-free decomposition of an Earnings-21
entity-WER harm into its operation kind, its position relative to the transport
unit's own boundaries, and the properties of the unit it fell in.

Why this module exists
----------------------
``SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1`` was REJECTED as HARM: the speaker-turn
transport unit bought +1.0487 points of corpus WER and sold 2.0912 points of
ConEC-mirror PERSON entity WER
(``docs/readiness/2026-09-08-e21-obs-speaker-turn-units-v1-verdict.md``). The
verdict names the sign and the size; it does not say WHICH names were lost or
WHERE. This module answers that at the grain of a single reference word, and it
does so with no new gold read of any kind: every input is either a sealed
alignment the registered scorers already computed or a committed plan.

The three facts this module is built on
---------------------------------------
1. **fstalign attributes no insertion to an entity.** ``reproduction.
   conec_entity_scoring.entity_wer_buckets`` mirrors ``src/wer.cpp::
   RecordTagWer`` exactly: an insertion stitch carries no NLP row, so every
   entity bucket -- PERSON included -- reports ``(S + D) / tagged reference
   words``. A PERSON harm is therefore ALWAYS a substitution/deletion story,
   and :func:`operation_kinds_by_reference` splits it into those two halves.
2. **A reference word carrying two entity IDs of one type counts twice.**
   fstalign visits the stitch once per tag, and the mirror does the same. So
   the unit of account here is the ``(reference word, entity ID)`` PAIR, and
   :func:`class_multiplicity` returns that multiplicity per word. Weighting
   every table by it is what makes the per-position sums reproduce the sealed
   PERSON numerator and denominator exactly.
3. **Charging alignment operations to spans is a PARTITION of the reference
   index range, and each span's block is CONTIGUOUS.** ``analysis.
   e21_window_pairing.charge_operations_to_windows`` assigns a span by a
   non-decreasing function of the hypothesis cursor, while reference indices
   are consumed strictly increasing, so each span's reference indices form one
   contiguous half-open block. :func:`span_reference_ranges` extracts those
   blocks and asserts both properties rather than assuming them.

Position, and the one approximation this module makes
------------------------------------------------------
The Earnings-21 reference layer carries **no word timestamps**: its ``.nlp``
files declare ``ts`` and ``endTs`` columns and every one of the 362,747 cells on
the 44 discovery calls is EMPTY. So a PERSON word's distance from a transport
boundary cannot be read off a clock; it has to be derived.

This module derives it in two steps and labels both:

* **Exact, in reference words.** ``distance_words = min(index - range_start,
  range_end - 1 - index)`` over the span's own contiguous block
  (:func:`boundary_distance_words`). This is exact given the arm's own
  alignment: no interpolation, no timing, no assumption.
* **Derived, in seconds.** ``seconds = (distance_words + 0.5) * span_seconds /
  span_reference_words`` (:func:`seconds_per_reference_word`,
  :func:`boundary_distance_seconds`) -- the span's OWN local speaking rate,
  never a corpus average. It is an attribution, never a timestamped alignment,
  and every table built on it must say so. Its resolution is the local rate
  itself: about 0.39 s per reference word on this carrier, so the 0-1 s bin is
  roughly the two or three reference words nearest a boundary.

The deletion-charging convention, stated because it matters
------------------------------------------------------------
``charge_operations_to_windows`` charges a deletion to the span its HYPOTHESIS
cursor stands in, so a name dropped at the very end of span *k* -- the cursor
having already advanced to span *k+1*'s first hypothesis word -- is charged to
the START of span *k+1*, not to the end of span *k*. That is why the primary
position measure here is the distance to the NEAREST boundary rather than the
distance to the span's end: nearest-boundary distance is invariant to which
side of a shared edge the instrument charged the operation to. Distances from
the start and from the end are still reported separately, so the asymmetry is
visible rather than hidden.

The one thing here that is not a measurement
---------------------------------------------
:func:`merge_units_below_threshold` prices a SUCCESSOR transport plan -- what a
raised minimum unit duration would cost in contacts and delivered audio -- by
re-running the committed plan's own rule 4 at a larger threshold. It is a design
instrument, not a decomposition: it reads no sealed output, it produces no
metric, and it never re-attributes a reference word. Kept in this module because
the successor it prices is the one this decomposition names.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping, Sequence

from ..reproduction.conec_entity_scoring import (
    OP_DELETION,
    OP_HIT,
    OP_INSERTION,
    OP_SUBSTITUTION,
)

RESULT_SCHEMA = "saea-e21-person-harm-v1"

EXPOSURE_ROW = "SAEA-E21-MF-OBS-E1-HARM-DECOMPOSITION-V1"

#: The class this read was opened for. Kept a parameter everywhere so the same
#: instrument answers ORG or GPE without a fork.
DEFAULT_ENTITY_CLASS = "PERSON"

#: The boundary-distance bins the read was registered with, in seconds, as
#: half-open ``[low, high)`` intervals. Fixed here rather than passed in, so two
#: tables in one receipt cannot silently use different edges.
BOUNDARY_BINS: tuple[tuple[float, float, str], ...] = (
    (0.0, 1.0, "0-1 s"),
    (1.0, 3.0, "1-3 s"),
    (3.0, 10.0, "3-10 s"),
    (10.0, math.inf, ">10 s"),
)

#: The tail this carrier's admitted media convention appends, in seconds. A
#: PERSON word whose distance to its span's END is under this is "inside the
#: tail's reach" for the tail-versus-boundary test.
TAIL_SECONDS = 2.0


class PersonHarmError(RuntimeError):
    """A decomposition input is malformed -- fail closed, never guess."""


# ---------------------------------------------------------------------------
# 1. Which reference words carry the class, and with what multiplicity.
# ---------------------------------------------------------------------------


def class_multiplicity(
    owners: Sequence[Sequence[str] | None],
    entity_types: Mapping[str, str],
    entity_class: str = DEFAULT_ENTITY_CLASS,
) -> tuple[int, ...]:
    """Per reference word, how many times ``entity_class`` claims it.

    ``owners[p]`` is the tuple of ``wer_tags`` entity IDs carried by
    whole-string reference word ``p`` -- exactly what ``reproduction.
    conec_entity_scoring.transfer_owners`` returns, ``None`` included for a
    position the transfer could not resolve. A word carrying two IDs of the
    same type is claimed twice, because fstalign's ``RecordTagWer`` visits the
    stitch once per tag and the mirror follows it; that multiplicity is what
    makes the per-position sums here reproduce the sealed bucket exactly.

    An unresolved (``None``) position claims nothing: it is charged to the
    mirror's own ``__UNLABELLED__`` bucket and can never quietly inflate or
    deflate an entity denominator.
    """

    out: list[int] = []
    for owner in owners:
        if owner is None:
            out.append(0)
            continue
        count = 0
        for entity_id in owner:
            entity_type = entity_types.get(entity_id)
            if entity_type is None:
                raise PersonHarmError(
                    f"entity id {entity_id!r} reached the decomposition with no type; "
                    "the caller must supply a type for every id it labels a word with"
                )
            if entity_type == entity_class:
                count += 1
        out.append(count)
    return tuple(out)


# ---------------------------------------------------------------------------
# 2. What happened to each reference word.
# ---------------------------------------------------------------------------


def operation_kinds_by_reference(
    operations: Sequence[tuple[str, int | None, int | None]], reference_length: int
) -> tuple[str, ...]:
    """Per reference word, the alignment operation that consumed it.

    Exactly one of :data:`~..reproduction.conec_entity_scoring.OP_HIT`,
    ``OP_SUBSTITUTION`` or ``OP_DELETION`` per position -- insertions consume
    no reference word and are not represented, which is the same reason no
    entity bucket ever carries one.
    """

    kinds: list[str | None] = [None] * reference_length
    for kind, ref_index, _hyp_index in operations:
        if kind == OP_INSERTION:
            continue
        if ref_index is None or not 0 <= ref_index < reference_length:
            raise PersonHarmError(
                f"operation {kind!r} carries reference index {ref_index!r}, outside "
                f"[0, {reference_length})"
            )
        if kinds[ref_index] is not None:
            raise PersonHarmError(f"reference index {ref_index} consumed twice")
        if kind not in (OP_HIT, OP_SUBSTITUTION, OP_DELETION):
            raise PersonHarmError(f"unknown reference-consuming operation {kind!r}")
        kinds[ref_index] = kind
    missing = [index for index, kind in enumerate(kinds) if kind is None]
    if missing:
        raise PersonHarmError(
            f"{len(missing)} reference words were consumed by no operation "
            f"(first: {missing[0]})"
        )
    return tuple(kind for kind in kinds if kind is not None)


def is_error(kind: str) -> bool:
    """A ConEC entity bucket's numerator: substitution or deletion, never a hit
    and never an insertion."""

    return kind in (OP_SUBSTITUTION, OP_DELETION)


# ---------------------------------------------------------------------------
# 3. Where a reference word sits inside its transport span.
# ---------------------------------------------------------------------------


def span_reference_ranges(
    charged: Sequence[Sequence[tuple[str, int | None, int | None]]],
    reference_length: int,
) -> tuple[tuple[int, int], ...]:
    """Half-open reference-index blocks, one per span, in span order.

    ``charged`` is ``analysis.e21_window_pairing.charge_operations_to_windows``'s
    own output for one call. Each span's reference indices are asserted
    contiguous and increasing, and the blocks are asserted to partition
    ``range(reference_length)`` exactly; a span that consumed no reference word
    gets an empty block ``(cursor, cursor)`` at the position its neighbours
    leave it.
    """

    ranges: list[tuple[int, int]] = []
    cursor = 0
    for position, operations in enumerate(charged):
        indices = [
            ref_index
            for kind, ref_index, _hyp in operations
            if kind != OP_INSERTION and ref_index is not None
        ]
        if not indices:
            ranges.append((cursor, cursor))
            continue
        low, high = indices[0], indices[-1]
        if indices != list(range(low, high + 1)):
            raise PersonHarmError(
                f"span {position} consumes a non-contiguous reference block "
                f"({len(indices)} indices spanning {low}..{high})"
            )
        if low != cursor:
            raise PersonHarmError(
                f"span {position} starts at reference index {low} where {cursor} was due"
            )
        ranges.append((low, high + 1))
        cursor = high + 1
    if cursor != reference_length:
        raise PersonHarmError(
            f"the span blocks account for {cursor} reference words, expected "
            f"{reference_length}"
        )
    return tuple(ranges)


def span_index_of_reference(
    ranges: Sequence[tuple[int, int]], reference_length: int
) -> tuple[int, ...]:
    """Per reference word, the position of the span whose block contains it."""

    out: list[int] = [-1] * reference_length
    for position, (low, high) in enumerate(ranges):
        for index in range(low, high):
            out[index] = position
    if any(value < 0 for value in out):
        raise PersonHarmError("a reference word belongs to no span")
    return tuple(out)


def boundary_distance_words(
    reference_range: tuple[int, int], index: int
) -> tuple[int, int, int]:
    """``(from_start, from_end, nearest)`` in reference words, all exact.

    ``from_start`` is how many reference words separate ``index`` from the
    span's first; ``from_end`` from its last. ``nearest`` is the smaller of the
    two -- the measure this read treats as primary, because it is invariant to
    which side of a shared edge the instrument charged a boundary operation to
    (module docstring, "the deletion-charging convention").
    """

    low, high = reference_range
    if not low <= index < high:
        raise PersonHarmError(f"reference index {index} is outside span block [{low}, {high})")
    from_start = index - low
    from_end = high - 1 - index
    return from_start, from_end, min(from_start, from_end)


def seconds_per_reference_word(span_seconds: float, reference_words: int) -> float:
    """The span's OWN local speaking rate, never a corpus average.

    Returns ``0.0`` for a span that carries no reference word, which is the
    only honest answer: such a span contributes no PERSON position either.
    """

    if reference_words <= 0:
        return 0.0
    if span_seconds <= 0:
        raise PersonHarmError(f"a span carrying {reference_words} words has {span_seconds} s")
    return span_seconds / reference_words


def boundary_distance_seconds(distance_words: int, rate_seconds_per_word: float) -> float:
    """``(distance_words + 0.5) * rate`` -- the word is placed at the centre of
    its own slot, so a word ON a boundary is half a slot away rather than zero.

    DERIVED, never measured: the Earnings-21 reference layer ships no
    timestamps (module docstring). Every table built on this must say so.
    """

    if distance_words < 0:
        raise PersonHarmError(f"a distance in words cannot be negative: {distance_words}")
    return (distance_words + 0.5) * rate_seconds_per_word


def bin_label(seconds: float, bins: Sequence[tuple[float, float, str]] = BOUNDARY_BINS) -> str:
    """The registered bin a derived offset falls in, half-open ``[low, high)``."""

    for low, high, label in bins:
        if low <= seconds < high:
            return label
    raise PersonHarmError(f"offset {seconds} falls in none of the registered bins")


# ---------------------------------------------------------------------------
# 4. Aggregation -- the proof obligation, and the tables.
# ---------------------------------------------------------------------------


def bucket_counts(rows: Iterable[Mapping[str, object]], arm: str) -> dict[str, int]:
    """Pool one arm's per-word rows into the ConEC bucket the scorer reports.

    ``substitutions + deletions`` over ``reference_words`` is exactly what
    ``entity_wer_buckets`` computes for an entity class, so this re-derivation
    is the read's own identity anchor against the sealed number.
    """

    substitutions = deletions = reference_words = 0
    for row in rows:
        weight = int(row["multiplicity"])
        reference_words += weight
        kind = str(row[f"{arm}_kind"])
        if kind == OP_SUBSTITUTION:
            substitutions += weight
        elif kind == OP_DELETION:
            deletions += weight
    errors = substitutions + deletions
    return {
        "substitutions": substitutions,
        "deletions": deletions,
        "errors": errors,
        "reference_words": reference_words,
    }


def wer_percent(counts: Mapping[str, int]) -> float:
    """``(S + D) / tagged reference words``, in points, or 0.0 on an empty bucket."""

    reference_words = int(counts["reference_words"])
    if reference_words <= 0:
        return 0.0
    return 100.0 * int(counts["errors"]) / reference_words


def merge_units_below_threshold(
    units: Sequence[Mapping[str, object]],
    threshold_seconds: float,
    cap_seconds: float = 90.0,
) -> tuple[tuple[float, float], ...]:
    """Price a raised minimum unit duration: plan v2's rule 4, re-run at a larger
    threshold, on the plan's OWN already-merged units.

    v2's rule 4 absorbs a span shorter than the minimum into whichever adjacent
    unit is LONGER, ties to the preceding neighbour, crossing a diarized speaker
    change if that is the only way, and refuses a merge that would exceed the
    cap (trying the other neighbour, then keeping the sliver). Running it again
    at a larger threshold over v2's output is a faithful CONTINUATION of that
    same rule, because v2 has already settled every span below 1.0 s.

    Returns the resulting ``(start_seconds, end_seconds)`` spans in order. This
    is a PRICING instrument for a successor plan -- unit count, delivered audio
    and contact count -- and never a reference-word attribution: merging changes
    which words land in which unit, and only a rebuilt plan can say how.
    """

    spans = [
        (float(unit["start_seconds"]), float(unit["end_seconds"])) for unit in units
    ]
    if not spans:
        return ()
    changed = True
    while changed and len(spans) > 1:
        changed = False
        for index, (start, end) in enumerate(spans):
            if end - start >= threshold_seconds:
                continue
            previous = spans[index - 1] if index > 0 else None
            following = spans[index + 1] if index + 1 < len(spans) else None
            candidates: list[int] = []
            if previous is not None and following is not None:
                previous_length = previous[1] - previous[0]
                following_length = following[1] - following[0]
                candidates = (
                    [index - 1, index + 1]
                    if previous_length >= following_length
                    else [index + 1, index - 1]
                )
            elif previous is not None:
                candidates = [index - 1]
            elif following is not None:
                candidates = [index + 1]
            for neighbour in candidates:
                low = min(spans[neighbour][0], start)
                high = max(spans[neighbour][1], end)
                if high - low > cap_seconds:
                    continue
                spans[min(neighbour, index)] = (low, high)
                del spans[max(neighbour, index)]
                changed = True
                break
            if changed:
                break
    return tuple(spans)


def group_table(
    rows: Iterable[Mapping[str, object]], key: str, arms: Sequence[str] = ("comparator", "cell")
) -> list[dict[str, object]]:
    """One row per distinct value of ``key``, each arm pooled inside it.

    ``improvement`` is signed so that POSITIVE means the CELL is better, the
    same convention every Earnings verdict in this repository uses.
    """

    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row[key]), []).append(row)
    table: list[dict[str, object]] = []
    for label in sorted(grouped):
        members = grouped[label]
        entry: dict[str, object] = {"stratum": label, "words": len(members)}
        for arm in arms:
            counts = bucket_counts(members, arm)
            entry[arm] = dict(counts)
            entry[f"{arm}_wer_percent"] = wer_percent(counts)
        if len(arms) == 2:
            entry["improvement_points"] = (
                float(entry[f"{arms[0]}_wer_percent"]) - float(entry[f"{arms[1]}_wer_percent"])
            )
        table.append(entry)
    return table
