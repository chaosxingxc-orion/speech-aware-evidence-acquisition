"""Shared entity/note-state primitives for the sealed-credit inner loop.

This module is the single source of truth for the pure, pool-kind-agnostic
functions the sealed-credit row-state extractor (``analysis.sealed_credit.
row_states``) shares with two pre-existing sealed analysis drivers:

* ``scripts/analysis/slurp_agree_arm_error_sources.py`` -- ``canonical``,
  ``norm_distance``, ``contiguous_in``, ``pair_kind``, ``entity_items``,
  ``fold``, ``edit_distance``, ``ENTITY_KINDS``, ``NEAR_THRESHOLD``;
* ``scripts/analysis/slurp_node_gain_ledger.py`` -- ``note_state``,
  ``gold_item_states``, ``PARTIAL_STOP``.

Design spec ``docs/superpowers/specs/2026-09-29-sealed-credit-inner-loop-
run-1-design.md`` section 5, task 2: "lift ... note_state, gold_item_states
and entity_items out of the ledger and error-source scripts (both then
import them; their ``--check`` stays byte-equal)". ``fold``/``edit_distance``/
``canonical``/``norm_distance``/``contiguous_in``/``pair_kind`` are lifted
alongside them because ``entity_items`` cannot be moved without its own
transitive closure -- leaving them behind in the error-source script would
make this module import FROM a script under ``scripts/analysis`` at src/
layer, inverting the repository's own layering (``common``/``src`` provides
helpers; ``scripts`` are drivers built on top of it).

``derive_arm`` (the ledger's own two-arm, single-sample, Fold-A-only row
derivation) is deliberately NOT lifted here: the design spec's own inventory
(section 1c) already records that it does not generalise to grouped or
supply-variant pools, and its remaining dependencies (``RD.own_key``,
``W5.printed_pairs``, the exemplar-vote pool) are themselves other
``scripts/analysis`` drivers, not primitives. ``analysis.sealed_credit.
row_states`` writes a NEW extractor for every pool kind on top of the
primitives this module exports; the two original scripts keep their own
``derive_arm``/``load_node_states`` unchanged.

Every function here is pure (no I/O, no global state) and byte-identical in
behaviour to the code it replaces; the accompanying test
(``tests/unit/test_sealed_credit_entity_states.py``) exercises each one
directly, and both source scripts' own ``--check`` mode is the end-to-end
regression proof (re-run after this module landed: identical bytes apart
from ``generated_at``).

Text discipline unchanged: every function here compares gold/predicted
filler TEXT in-process and returns only class names, indices, and distances
-- never a filler string.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# fold() / edit_distance() (moved verbatim from
# scripts/analysis/slurp_gold_position_and_solver_freedom_read.py)

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^\w\s'-]", re.UNICODE)


def fold(text: str) -> str:
    """Casefold, NFKC, punctuation stripped except apostrophes and hyphens,
    whitespace collapsed -- the bank's own P2r1 rung, applied identically to
    both sides of every comparison so no comparison favours one side."""
    return _WS_RE.sub(" ", _PUNCT_RE.sub(" ", unicodedata.normalize("NFKC", text).casefold())).strip()


def edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left or not right:
        return len(left) + len(right)
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, start=1):
        current = [i]
        for j, rchar in enumerate(right, start=1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (lchar != rchar)))
        previous = current
    return previous[-1]


# ---------------------------------------------------------------------------
# canonical filler form and entity error classes (moved verbatim from
# scripts/analysis/slurp_agree_arm_error_sources.py)

NEAR_THRESHOLD = 0.4
ENTITY_KINDS = ("FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE", "WRONG-TYPE", "MISSING", "SPURIOUS")

_NUM_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
    "fifteen sixteen seventeen eighteen nineteen".split())}
_NUM_TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
_ORD_UNITS = {w: i + 1 for i, w in enumerate(
    "first second third fourth fifth sixth seventh eighth ninth tenth eleventh twelfth thirteenth "
    "fourteenth fifteenth sixteenth seventeenth eighteenth nineteenth".split())}
_ORD_TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twentieth thirtieth fortieth fiftieth sixtieth seventieth eightieth ninetieth".split())}
_ORD_SUFFIX = re.compile(r"^(\d+)(st|nd|rd|th)$")
_DROP_TOKENS = {"oclock"}


def _words_to_number(tokens: list) -> list:
    out, value, active = [], 0, False
    for token in tokens + ["<end>"]:
        if token in _NUM_UNITS:
            value, active = value + _NUM_UNITS[token], True
            continue
        if token in _NUM_TENS:
            value, active = value + _NUM_TENS[token], True
            continue
        if token == "hundred" and active:
            value *= 100
            continue
        if token in _ORD_UNITS or token in _ORD_TENS:
            out.append(str(value + _ORD_UNITS.get(token, 0) + _ORD_TENS.get(token, 0)))
            value, active = 0, False
            continue
        if token == "and" and active:
            continue
        if active:
            out.append(str(value))
            value, active = 0, False
        if token != "<end>":
            out.append(token)
    return out


def canonical(text: str) -> str:
    """fold() (the bank's P2r1 rung), then apostrophes and hyphens dropped,
    'a m'/'p m' joined, 'o'clock' dropped, number and ordinal words to digits,
    ordinal suffixes stripped.  Applied identically to gold and prediction."""

    base = fold(text).replace("'", "").replace("-", " ")
    base = re.sub(r"\b([ap]) m\b", r"\1m", base)
    tokens = [t for t in base.split() if t and t not in _DROP_TOKENS]
    tokens = [(_ORD_SUFFIX.match(t).group(1) if _ORD_SUFFIX.match(t) else t) for t in tokens]
    return " ".join(_words_to_number(tokens))


def norm_distance(left: str, right: str) -> float:
    return edit_distance(left, right) / max(len(left), len(right), 1)


def contiguous_in(short: list, long: list) -> bool:
    if not short or len(short) > len(long):
        return False
    return any(long[i:i + len(short)] == short for i in range(len(long) - len(short) + 1))


def pair_kind(gold_filler: str, pred_filler: str) -> tuple:
    """(kind, subkind, canonical normalised char distance) of one gold/prediction pair."""

    g, p = canonical(gold_filler), canonical(pred_filler)
    dist = norm_distance(g, p)
    if g == p:
        return "FORMAT", ("case-punct" if fold(gold_filler) == fold(pred_filler) else "number-time-token"), 0.0
    gt, ptk = g.split(), p.split()
    if contiguous_in(gt, ptk):
        return "BOUNDARY", "prediction-longer", dist
    if contiguous_in(ptk, gt):
        return "BOUNDARY", "prediction-shorter", dist
    if dist <= NEAR_THRESHOLD:
        return "NEAR", "near-value", dist
    return "WRONG-VALUE", "different-value", dist


def entity_items(gold: tuple, pred: tuple) -> list:
    """Every entity error item of one row.  Exact {type, filler} matches (the
    official exact matcher) are removed first; same-type leftovers are paired
    greedily by canonical distance; cross-type leftovers that carry the same, a
    span-related or a near value become WRONG-TYPE; the rest are MISSING /
    SPURIOUS."""

    unmatched_pred, taken = [], set()
    for pindex, entity in enumerate(pred):
        hit = next((gi for gi, g in enumerate(gold) if gi not in taken and g == entity), None)
        if hit is None:
            unmatched_pred.append((pindex, entity))
        else:
            taken.add(hit)
    free_gold = [(gi, g) for gi, g in enumerate(gold) if gi not in taken]
    candidates = []
    for gi, g in free_gold:
        for pi, p in unmatched_pred:
            if p.type == g.type:
                candidates.append((norm_distance(canonical(g.filler), canonical(p.filler)), gi, pi))
    used_g, used_p, items = set(), set(), []
    for _, gi, pi in sorted(candidates):
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        kind, sub, dist = pair_kind(gold[gi].filler, pred[pi].filler)
        items.append({"kind": kind, "sub": sub, "type": gold[gi].type, "gold_index": gi, "pred_index": pi,
                      "distance": round(dist, 4)})
    cross = []
    for gi, g in free_gold:
        if gi in used_g:
            continue
        for pi, p in unmatched_pred:
            if pi in used_p or p.type == g.type:
                continue
            kind, _, dist = pair_kind(g.filler, p.filler)
            if kind in ("FORMAT", "BOUNDARY", "NEAR"):
                cross.append((dist, gi, pi, kind))
    for dist, gi, pi, kind in sorted(cross):
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        items.append({"kind": "WRONG-TYPE", "sub": "same-value" if kind == "FORMAT" else "related-value",
                      "type": gold[gi].type, "pred_type": pred[pi].type, "gold_index": gi, "pred_index": pi,
                      "distance": round(dist, 4)})
    for gi, g in free_gold:
        if gi not in used_g:
            items.append({"kind": "MISSING", "sub": "missing", "type": g.type, "gold_index": gi, "pred_index": None,
                          "distance": None})
    for pi, p in unmatched_pred:
        if pi not in used_p:
            items.append({"kind": "SPURIOUS", "sub": "spurious", "type": p.type, "gold_index": None,
                          "pred_index": pi, "distance": None})
    return sorted(items, key=lambda i: (ENTITY_KINDS.index(i["kind"]), i["type"],
                                        -1 if i["gold_index"] is None else i["gold_index"],
                                        -1 if i["pred_index"] is None else i["pred_index"]))


# ---------------------------------------------------------------------------
# Perception-note contiguity and per-item gold state (moved verbatim from
# scripts/analysis/slurp_node_gain_ledger.py)

PARTIAL_STOP = frozenset("a an the of to in on at for and or my me i is it this that with from by be what please "
                         "can could you your".split())
NOTE_STATES = ("CONTIGUOUS", "NEAR", "PARTIAL", "ABSENT")


def note_state(gold_filler: str, tokens: list) -> str:
    g = canonical(gold_filler)
    gt = g.split()
    if not gt or not tokens:
        return "ABSENT"
    if contiguous_in(gt, tokens):
        return "CONTIGUOUS"
    for width in (len(gt) - 1, len(gt), len(gt) + 1):
        if width <= 0 or width > len(tokens):
            continue
        for i in range(len(tokens) - width + 1):
            if norm_distance(g, " ".join(tokens[i:i + width])) <= NEAR_THRESHOLD:
                return "NEAR"
    if any(t in tokens for t in gt if t not in PARTIAL_STOP):
        return "PARTIAL"
    return "ABSENT"


def gold_item_states(gold: tuple, pred: tuple) -> tuple:
    """(state per gold index, spurious prediction indices) under ``entity_items``."""

    states = ["EXACT"] * len(gold)
    spurious = []
    for item in entity_items(gold, pred):
        if item["gold_index"] is None:
            spurious.append(item["pred_index"])
        else:
            states[item["gold_index"]] = item["kind"]
    return states, spurious


__all__ = [
    "NEAR_THRESHOLD", "ENTITY_KINDS", "NOTE_STATES", "PARTIAL_STOP",
    "fold", "edit_distance", "canonical", "norm_distance", "contiguous_in",
    "pair_kind", "entity_items", "note_state", "gold_item_states",
]
