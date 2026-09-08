"""``saea-obs-context-ownership-v1``: which words of a context-delivered unit
are the unit's OWN.

The problem
-----------
OBS-E1b (``docs/readiness/2026-09-08-e21-obs-e1b-context-units-v1-
preregistration.md``) delivers each plan-v3 unit as ``[left context | the turn
| right context]`` audio, because the PERSON harm decomposition found the
damage on BOTH edges of a short unit -- a missing-context failure, not a
truncate-at-the-tail one. The frozen core transcribes what it hears, so the
response covers the context too, and stitching it whole would duplicate every
overlap into the corpus hypothesis and move the one metric OBS-E1 actually
won. Something has to decide where the turn's own text begins and ends.

Earnings-21 ships no word timestamps, and this repository's one word-level
locator -- ``core.span_surgery.align_words``, the MMS_FA forced aligner
``reproduction.replay_loop`` uses to keep only the words inside a flagged span
of a context window -- is a tool-model contact. One alignment per unit is
5,122 of them, and the point of this module is that none is needed.

The mechanism: the overlap is transcribed TWICE
-----------------------------------------------
Plan v3's context bounds overlap by construction. Around boundary ``k`` (the
end of unit ``k``, the start of unit ``k + 1``) the region
``[start_{k+1} - left_{k+1}, end_k + right_k]`` is delivered to BOTH units, so
both responses contain a transcription of it. Find a run of consecutive words
the two responses AGREE on there, choose one position inside it as the ANCHOR,
and cut both texts at it: unit ``k`` keeps everything before the anchor, unit
``k + 1`` everything from it.

That single choice is what makes the stitch safe. Inside a shared run the two
texts are the same words in the same order, so
``left[:anchor] + right[anchor:]`` covers the audio once and only once. Where
in the run the anchor sits changes WHICH decode supplies a word, never WHETHER
a word is supplied: no gap and no duplication, for every position in the run.
The rule places it as close to the true boundary as the two units' own local
word rates can say, so a word is charged to the unit whose turn contains it --
and a displaced anchor moves a word between two neighbours without removing it
from the corpus. Measured on the sealed OBS-E1 texts, the displacement is a
median of zero words and a mean of 1.87
(``docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1b-stitch-proof/``).

Contiguity, not a longest common subsequence, is the safety argument. A
subsequence match would pair a "the" at one end of the overlap with a "the" at
the other and cut there, dropping everything between; three consecutive words
in the same order is, on this material, the same speech heard twice.

Four rules, in order, and every one of them recorded
------------------------------------------------------
* ``no-overlap`` -- the two units share no delivered audio (a long unit the
  90 s cap left with no context). The cut is the left text's own end and the
  right text's own start: byte for byte what a v1/v2 plan already does, which
  is why this module is inert without context bounds.
* ``anchor`` -- a shared run of at least :data:`MIN_ANCHOR_RUN` words. Among
  ALL such runs the one is taken whose implied cut lands nearest the boundary,
  with length only as a tie-break: on sparse or repetitive speech the LONGEST
  shared block can sit at the far end of the search zone and imply a cut ten
  words away, which is how a false anchor loses words.
* ``anchor-short`` -- the same rule at :data:`SHORT_ANCHOR_RUN` words, tried
  only when no longer run exists, and counted separately because two agreeing
  words is weaker evidence than three. It exists for the genuinely sparse
  stretch: parts of call 4361631 decode at under one word per second, where a
  ten-second overlap holds three words in total.
* ``proportional`` -- no shared run at all. Each text is cut at the position
  the boundary occupies in its own delivered span, by that unit's own local
  word rate. This is the ONE rule that can drop or duplicate a word across the
  seam, so it is counted per boundary and reported: the preregistration reads
  its rate as a guard, not as a detail. Measured at plan v3's own margin it
  fired on 1 of 5,078 boundaries.

Order, and one refusal
----------------------
Boundaries are resolved left to right and a unit's right cut may never fall
before its own left cut. The anchor branches enforce that inside the SEARCH --
a run entirely before the floor is skipped, and the position inside the chosen
run is bounded below by it -- so they never need to clamp and never drop a
word for order's sake. Only ``proportional`` can clamp, and it says so
(``left_clamped``/``right_clamped``). If a decision still leaves ``keep_from >
keep_to``, :class:`OwnershipError` is raised: that is a broken invariant, never
a data condition, and it stops the call rather than stitching something the
module cannot describe.

Pure and model-free
-------------------
Nothing here opens a file, a socket or a model. It takes spans and strings and
returns spans and strings, which is what lets the whole protocol be PROVED
against the sealed OBS-E1 outputs before anything is flown
(``scripts/e21_obs_e1b_stitch_proof.py``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

#: Versioned by name; it lands in the plan's ``rules`` block, in the OBS trace
#: of every unit and in the run's obs-derivation receipt.
OWNERSHIP_PROTOCOL = "saea-obs-context-ownership-v1"

#: How far outside the estimated overlap zone the anchor search may look, in
#: words. The estimate is a local word rate over a unit's own delivered span
#: (the same attribution the harm decomposition used, at a median 0.388 s per
#: reference word), so it is good to a word or two; six words of slack on each
#: side covers that without letting the search wander into unrelated text.
ZONE_SLACK_WORDS = 12

#: A hard ceiling on either search zone, so the alignment stays O(1) per
#: boundary whatever a runaway decode produces.
MAX_ZONE_WORDS = 120

#: The shortest run of consecutive agreeing words that may carry an anchor.
#: Two decodes of the same three words in the same order is the same speech
#: heard twice; a single shared function word is not.
MIN_ANCHOR_RUN = 3

#: The second tier, tried only when no run of :data:`MIN_ANCHOR_RUN` exists and
#: recorded under its own rule name, so a receipt can separate the two.
SHORT_ANCHOR_RUN = 2

RULE_NO_OVERLAP = "no-overlap"
RULE_ANCHOR = "anchor"
RULE_SHORT_ANCHOR = "anchor-short"
RULE_PROPORTIONAL = "proportional"
RULE_CALL_EDGE = "call-edge"

_EPSILON = 1e-9
_WORD = re.compile(r"\S+")
_KEY_STRIP = re.compile(r"[^a-z0-9']+")


class OwnershipError(RuntimeError):
    """The ownership stitch refused: a malformed unit, or a decision that
    would leave a unit owning a negative range of its own words."""


@dataclass(frozen=True)
class OwnershipUnit:
    """One context-delivered unit as the stitch sees it: where its turn is,
    where its delivered audio is, and what came back."""

    unit_id: str
    turn_start_seconds: float
    turn_end_seconds: float
    context_start_seconds: float
    context_end_seconds: float
    text: str

    def validate(self) -> "OwnershipUnit":
        if self.turn_end_seconds <= self.turn_start_seconds:
            raise OwnershipError(
                f"unit {self.unit_id!r} has a non-positive turn "
                f"[{self.turn_start_seconds}, {self.turn_end_seconds})"
            )
        if self.context_start_seconds > self.turn_start_seconds + 1e-6:
            raise OwnershipError(
                f"unit {self.unit_id!r} does not deliver its own turn's start"
            )
        if self.context_end_seconds < self.turn_end_seconds - 1e-6:
            raise OwnershipError(
                f"unit {self.unit_id!r} does not deliver its own turn's end"
            )
        return self


@dataclass(frozen=True)
class OwnershipDecision:
    """What one unit contributes, and how that was decided.

    ``keep_from``/``keep_to`` are half-open indices into the unit's own
    whitespace-token list; ``delivered_text`` is the corresponding SLICE OF THE
    ORIGINAL STRING (by character offset, never a re-join), so a unit that
    keeps everything delivers its response unchanged.
    """

    unit_id: str
    words_total: int
    keep_from: int
    keep_to: int
    left_rule: str
    right_rule: str
    left_clamped: bool
    right_clamped: bool
    delivered_text: str

    @property
    def words_kept(self) -> int:
        return self.keep_to - self.keep_from

    @property
    def words_dropped(self) -> int:
        return self.words_total - self.words_kept

    def trace_fields(self) -> dict[str, object]:
        """What the OBS record carries beside the raw response, so a later
        reader can re-derive the stitch from the sealed trace alone."""

        return {
            "obs_ownership_protocol": OWNERSHIP_PROTOCOL,
            "obs_ownership_words_total": self.words_total,
            "obs_ownership_keep_from": self.keep_from,
            "obs_ownership_keep_to": self.keep_to,
            "obs_ownership_left_rule": self.left_rule,
            "obs_ownership_right_rule": self.right_rule,
            "obs_ownership_left_clamped": self.left_clamped,
            "obs_ownership_right_clamped": self.right_clamped,
            "obs_delivered_text": self.delivered_text,
        }


def words_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """``(token, start_char, end_char)`` per whitespace-separated token."""

    return [(match.group(0), match.start(), match.end()) for match in _WORD.finditer(text)]


def ownership_key(word: str) -> str:
    """The form two decodes are compared on: lowercase, letters/digits and the
    apostrophe only. Punctuation and casing differ between two decodes of the
    same audio far more often than the word does, and neither carries the
    identity the anchor needs."""

    return _KEY_STRIP.sub("", word.lower())


def _words_before(count: int, start: float, end: float, moment: float) -> int:
    """How many of ``count`` words, spread evenly over ``[start, end)``, sit
    before ``moment``. Clamped into ``[0, count]``. This is the module's ONE
    piece of timing arithmetic and it is an attribution, never an alignment:
    its resolution is the unit's own local word rate."""

    if count <= 0:
        return 0
    span = end - start
    if span <= _EPSILON:
        return 0 if moment <= start else count
    position = count * (moment - start) / span
    return max(0, min(count, int(round(position))))


def common_runs(
    left: Sequence[str], right: Sequence[str], *, minimum: int
) -> list[tuple[int, int, int]]:
    """Every CONTIGUOUS block of at least ``minimum`` words the two key
    sequences share, as ``(left_start, right_start, length)``, in order.

    Contiguity is the whole safety argument. A longest common SUBSEQUENCE
    would happily pair a "the" at one end of the overlap with a "the" at the
    other and produce a cut that drops or duplicates everything between them;
    a run of three or more consecutive words in the same order is, on this
    material, the same speech heard twice. ``difflib`` enumerates the blocks
    deterministically, so the same inputs always give the same list.
    """

    from difflib import SequenceMatcher  # noqa: PLC0415

    if not left or not right:
        return []
    matcher = SequenceMatcher(None, list(left), list(right), autojunk=False)
    return [
        (block.a, block.b, block.size)
        for block in matcher.get_matching_blocks()
        if block.size >= minimum
    ]


def _resolve_boundary(
    left: OwnershipUnit,
    left_words: Sequence[tuple[str, int, int]],
    right: OwnershipUnit,
    right_words: Sequence[tuple[str, int, int]],
    floor: int,
) -> tuple[int, int, str, bool]:
    """One boundary: ``(keep_to for the left unit, keep_from for the right
    unit, rule, clamped)``. ``floor`` is the left unit's own left cut, which
    its right cut may never fall below."""

    boundary = left.turn_end_seconds
    low = max(left.context_start_seconds, right.context_start_seconds)
    high = min(left.context_end_seconds, right.context_end_seconds)
    n_left, n_right = len(left_words), len(right_words)

    if high - low <= 1e-6:
        # No shared audio: the cut is each text's own edge, which is exactly
        # what a v1/v2 plan does and is why this module is inert without
        # context bounds.
        return n_left, 0, RULE_NO_OVERLAP, False

    target_left = _words_before(
        n_left, left.context_start_seconds, left.context_end_seconds, boundary
    )
    target_right = _words_before(
        n_right, right.context_start_seconds, right.context_end_seconds, boundary
    )

    zone_left_start = max(
        0,
        _words_before(n_left, left.context_start_seconds, left.context_end_seconds, low)
        - ZONE_SLACK_WORDS,
    )
    zone_left_start = max(zone_left_start, n_left - MAX_ZONE_WORDS)
    zone_right_end = min(
        n_right,
        _words_before(n_right, right.context_start_seconds, right.context_end_seconds, high)
        + ZONE_SLACK_WORDS,
    )
    zone_right_end = min(zone_right_end, MAX_ZONE_WORDS)

    left_keys = [ownership_key(word) for word, _s, _e in left_words[zone_left_start:]]
    right_keys = [ownership_key(word) for word, _s, _e in right_words[:zone_right_end]]
    # Every admissible run, scored by WHERE the cut it implies would land.
    # "Longest" is the wrong criterion on sparse or repetitive transcripts: the
    # longest shared block can sit at the far end of the search zone and imply
    # a cut ten words from the boundary, which is how a false anchor loses
    # words. The best-LOCATED run of at least MIN_ANCHOR_RUN words is what the
    # rule takes, with length only as a tie-break.
    best: tuple[int, int, int, int] | None = None
    minimum = MIN_ANCHOR_RUN
    runs = common_runs(left_keys, right_keys, minimum=minimum)
    if not runs and SHORT_ANCHOR_RUN < MIN_ANCHOR_RUN:
        # Second tier, recorded under its own rule name. On a sparse stretch --
        # call 4361631 decodes under one word per second in places -- a ten
        # second overlap can hold three words in total and no three-word run
        # can exist. Two consecutive agreeing words is weaker evidence than
        # three and is counted separately, but it is still an alignment, and
        # the alternative is the proportional rule, which is none.
        minimum = SHORT_ANCHOR_RUN
        runs = common_runs(left_keys, right_keys, minimum=minimum)
    for offset, position, length in runs:
        run_left = zone_left_start + offset
        floor_inside = max(0, floor - run_left)
        if floor_inside > length:
            # Entirely before this unit's own left cut: no position in it could
            # keep the two cuts in order.
            continue
        inside = int(round(0.5 * ((target_left - run_left) + (target_right - position))))
        inside = max(floor_inside, min(length, inside))
        cost = abs((run_left + inside) - target_left) + abs(
            (position + inside) - target_right
        )
        candidate = (cost, -length, run_left + inside, position + inside)
        if best is None or candidate < best:
            best = candidate
    if best is not None:
        _cost, _size, keep_to, keep_from = best
        rule = RULE_ANCHOR if minimum >= MIN_ANCHOR_RUN else RULE_SHORT_ANCHOR
        return keep_to, keep_from, rule, False
    keep_to = max(target_left, floor)
    return keep_to, target_right, RULE_PROPORTIONAL, target_left < floor


def resolve_ownership(units: Sequence[OwnershipUnit]) -> tuple[OwnershipDecision, ...]:
    """The whole call, left to right. One decision per unit."""

    if not units:
        raise OwnershipError("a call must carry at least one unit")
    ordered = [unit.validate() for unit in units]
    for previous, following in zip(ordered, ordered[1:]):
        if abs(previous.turn_end_seconds - following.turn_start_seconds) > 1e-6:
            raise OwnershipError(
                f"units {previous.unit_id!r} and {following.unit_id!r} do not abut: "
                f"{previous.turn_end_seconds} then {following.turn_start_seconds}"
            )
    tokens = [words_with_offsets(unit.text) for unit in ordered]

    keep_from = [0] * len(ordered)
    keep_to = [len(words) for words in tokens]
    left_rule = [RULE_CALL_EDGE] * len(ordered)
    right_rule = [RULE_CALL_EDGE] * len(ordered)
    left_clamped = [False] * len(ordered)
    right_clamped = [False] * len(ordered)

    for index in range(len(ordered) - 1):
        cut_to, cut_from, rule, clamped = _resolve_boundary(
            ordered[index],
            tokens[index],
            ordered[index + 1],
            tokens[index + 1],
            keep_from[index],
        )
        keep_to[index] = cut_to
        keep_from[index + 1] = cut_from
        right_rule[index] = rule
        left_rule[index + 1] = rule
        right_clamped[index] = clamped
        left_clamped[index + 1] = clamped

    decisions: list[OwnershipDecision] = []
    for index, unit in enumerate(ordered):
        words = tokens[index]
        low, high = keep_from[index], keep_to[index]
        if low > high:
            raise OwnershipError(
                f"unit {unit.unit_id!r} would own words [{low}, {high}): the two "
                "boundaries around it crossed, which the clamp is supposed to make "
                "unreachable"
            )
        if high > len(words) or low < 0:
            raise OwnershipError(
                f"unit {unit.unit_id!r} would own words [{low}, {high}) of "
                f"{len(words)}"
            )
        text = "" if high <= low else unit.text[words[low][1] : words[high - 1][2]]
        decisions.append(
            OwnershipDecision(
                unit_id=unit.unit_id,
                words_total=len(words),
                keep_from=low,
                keep_to=high,
                left_rule=left_rule[index],
                right_rule=right_rule[index],
                left_clamped=left_clamped[index],
                right_clamped=right_clamped[index],
                delivered_text=text,
            )
        )
    return tuple(decisions)


def stitch(decisions: Sequence[OwnershipDecision]) -> str:
    """``reproduction.obs_loop``'s own join rule, over the delivered texts."""

    return " ".join(
        decision.delivered_text for decision in decisions if decision.delivered_text
    )


def ownership_summary(decisions: Sequence[OwnershipDecision]) -> dict[str, object]:
    """Counts a receipt reports: how each boundary was decided and what the
    stitch dropped."""

    boundaries = max(len(decisions) - 1, 0)
    rules: dict[str, int] = {}
    for decision in decisions[:-1] if decisions else []:
        rules[decision.right_rule] = rules.get(decision.right_rule, 0) + 1
    return {
        "units": len(decisions),
        "boundaries": boundaries,
        "rules": dict(sorted(rules.items())),
        "anchor_share": (
            round(
                (rules.get(RULE_ANCHOR, 0) + rules.get(RULE_SHORT_ANCHOR, 0)) / boundaries,
                8,
            )
            if boundaries
            else 0.0
        ),
        "clamped_boundaries": sum(
            1 for decision in decisions[:-1] if decision.right_clamped
        ),
        "empty_units": sum(1 for decision in decisions if not decision.delivered_text),
        "words_total": sum(decision.words_total for decision in decisions),
        "words_kept": sum(decision.words_kept for decision in decisions),
        "words_dropped": sum(decision.words_dropped for decision in decisions),
    }


__all__ = [
    "MAX_ZONE_WORDS",
    "MIN_ANCHOR_RUN",
    "SHORT_ANCHOR_RUN",
    "OWNERSHIP_PROTOCOL",
    "RULE_ANCHOR",
    "RULE_CALL_EDGE",
    "RULE_NO_OVERLAP",
    "RULE_PROPORTIONAL",
    "RULE_SHORT_ANCHOR",
    "ZONE_SLACK_WORDS",
    "OwnershipDecision",
    "OwnershipError",
    "OwnershipUnit",
    "common_runs",
    "ownership_key",
    "ownership_summary",
    "resolve_ownership",
    "stitch",
    "words_with_offsets",
]
