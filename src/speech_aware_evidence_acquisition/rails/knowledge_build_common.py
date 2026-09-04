"""Shared, task-independent helpers factored out of ``rails.knowledge_build``
(SLURP) and ``rails.knowledge_build_a2t`` (Audio2Tool) -- consolidation slice
C4b ("one knowledge interface").

Before this module existed, both build modules carried their own private
copies of the same shingle/Jaccard/apportionment/diversity-pick machinery.
``_shingles``, ``_jaccard`` and ``_hamilton_apportion`` were already
byte-identical function BODIES in both files (only ``knowledge_build_a2t``'s
docstrings were shorter); ``_greedy_diverse_pick`` was the SAME algorithm
over two different row shapes -- SLURP's ``speaker_of``/``row.utterance_id``/
``row.content`` versus Audio2Tool's hardcoded ``row.tool_name``/
``row.unit_id``/``row.text`` -- so it is generalized here over injected
``text_of``/``id_of``/``group_of`` accessors rather than merely relocated;
each build module keeps its OLD private name and OLD call signature as a
thin alias that plugs in its own row accessors, so no existing call site or
test changes. ``distribution_sample`` (SLURP's already-public datastore
selector) moves here verbatim -- it has no A2T twin (Audio2Tool's own
``distribution_sample_a2t`` uses a materially different three-floor scheme
and stays in ``knowledge_build_a2t``) -- and ``rails.knowledge_build``
re-exports it unchanged so every existing importer
(``rails.knowledge_build.distribution_sample``,
``analysis.slurp_intent_coverage_check``) keeps working.

See ``tests/unit/test_knowledge_build_common.py`` for the byte-identity
proof: both build modules' OLD call paths, exercised on synthetic inputs,
reproduce fixed expected values captured from the pre-consolidation code.

No model, filesystem, or network access anywhere in this module.
"""

from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from typing import Callable, Mapping, Sequence, TypeVar

from .errors import RailsError

Row = TypeVar("Row")


# ---------------------------------------------------------------------------
# Content-shingle novelty (moved verbatim from both build modules)
# ---------------------------------------------------------------------------


def shingles(text: str) -> frozenset[str]:
    """Word-bigram shingle fingerprint (unigrams if the text is too short)."""

    tokens = text.lower().split()
    if len(tokens) < 2:
        return frozenset(tokens)
    return frozenset(f"{a} {b}" for a, b in zip(tokens, tokens[1:]))


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


# ---------------------------------------------------------------------------
# Greedy content-diversity pick, generalized over row shape
# ---------------------------------------------------------------------------


def greedy_diverse_pick(
    candidates: Sequence[Row],
    count: int,
    already_selected: Sequence[Row],
    rng: random.Random,
    *,
    text_of: Callable[[Row], str],
    id_of: Callable[[Row], str],
    group_of: Callable[[Row], str],
    group_cap: int,
) -> list[Row]:
    """Greedy farthest-point content-diversity selection, generalized over
    row shape (module docstring): at each round, picks the remaining
    candidate whose bigram-shingle Jaccard similarity to its CLOSEST
    already-selected row is lowest -- the biggest novelty, a model-free
    proxy for an uncovered content-cluster medoid -- honoring a soft
    per-group cap (bypassed only when every remaining candidate is already
    at the cap, so a pick is never refused outright). Ties are broken via
    ``rng`` over the ``id_of``-sorted tied set, so the result is pool-order
    independent and reproducible for a fixed seed.

    ``text_of``/``id_of``/``group_of``/``group_cap`` are exactly the
    per-row accessors ``rails.knowledge_build``'s own
    ``speaker_of``/``speaker_cap`` and ``rails.knowledge_build_a2t``'s own
    hardcoded ``row.tool_name``/``tool_cap`` supplied inline before this
    consolidation -- injecting them here makes one implementation back both
    call sites, unchanged in observable behavior (see each module's own
    thin ``_greedy_diverse_pick`` alias and this module's own test suite for
    the byte-identity proof).
    """

    selected_shingles = [shingles(text_of(row)) for row in already_selected]
    group_counts: Counter[str] = Counter(group_of(row) for row in already_selected)
    remaining = sorted(candidates, key=id_of)
    shingle_of = {id_of(row): shingles(text_of(row)) for row in remaining}
    picked: list[Row] = []
    while remaining and len(picked) < count:
        capped = {group for group, n in group_counts.items() if n >= group_cap}
        eligible = [row for row in remaining if group_of(row) not in capped] or remaining
        best_score: float | None = None
        best_rows: list[Row] = []
        for row in eligible:
            row_shingles = shingle_of[id_of(row)]
            max_sim = max(
                (jaccard(row_shingles, other) for other in selected_shingles), default=0.0
            )
            novelty = 1.0 - max_sim
            if best_score is None or novelty > best_score + 1e-12:
                best_score, best_rows = novelty, [row]
            elif abs(novelty - best_score) <= 1e-12:
                best_rows.append(row)
        chosen = (
            sorted(best_rows, key=id_of)[rng.randrange(len(best_rows))]
            if len(best_rows) > 1
            else best_rows[0]
        )
        picked.append(chosen)
        selected_shingles.append(shingle_of[id_of(chosen)])
        group_counts[group_of(chosen)] += 1
        remaining = [row for row in remaining if id_of(row) != id_of(chosen)]
    return picked


# ---------------------------------------------------------------------------
# Largest-remainder apportionment (moved verbatim from both build modules)
# ---------------------------------------------------------------------------


def hamilton_apportion(capacity_by_key: Mapping[str, int], total: int) -> dict[str, int]:
    """Largest-remainder (Hamilton) apportionment of ``total`` seats across
    ``capacity_by_key``'s keys, weighted by capacity and capped at each key's
    own capacity. Deterministic: fractional-remainder ties are broken by
    ascending key name. Requires ``0 <= total <= sum(capacity_by_key.values())``.
    """

    if isinstance(total, bool) or not isinstance(total, int) or total < 0:
        raise RailsError("hamilton_apportion: total must be a non-negative int")
    keys = sorted(capacity_by_key)
    total_capacity = sum(capacity_by_key[key] for key in keys)
    if total > total_capacity:
        raise RailsError("hamilton_apportion: total exceeds total capacity")
    result = {key: 0 for key in keys}
    if total == 0 or total_capacity == 0:
        return result
    raw = {key: total * capacity_by_key[key] / total_capacity for key in keys}
    for key in keys:
        result[key] = min(int(raw[key]), capacity_by_key[key])
    remainder = total - sum(result.values())
    order = sorted(keys, key=lambda key: (-(raw[key] - int(raw[key])), key))
    guard = 0
    while remainder > 0:
        progressed = False
        for key in order:
            if remainder <= 0:
                break
            if result[key] < capacity_by_key[key]:
                result[key] += 1
                remainder -= 1
                progressed = True
        if not progressed:
            raise RailsError("hamilton_apportion: failed to converge (internal invariant)")
        guard += 1
        if guard > 10_000:
            raise RailsError("hamilton_apportion: exceeded iteration guard")
    return result


# ---------------------------------------------------------------------------
# SLURP TRAIN datastore selection (moved verbatim; no Audio2Tool twin --
# ``knowledge_build_a2t.distribution_sample_a2t`` uses a materially
# different three-floor scheme and stays where it is)
# ---------------------------------------------------------------------------


def distribution_sample(
    rows: Sequence[Row], size: int | None, seed: int
) -> tuple[Row, ...]:
    """Distribution-modeled TRAIN datastore selection (moved verbatim from
    ``rails.knowledge_build``): proportional allocation over INTENT with two
    hard floors -- every intent keeps at least one utterance and every
    entity type observed anywhere in TRAIN keeps at least one exemplar
    utterance -- then greedy content-diversity picks
    (:func:`greedy_diverse_pick`) fill the remainder of each intent's
    Hamilton-apportioned quota, honoring a soft per-speaker cap.

    ``rows`` duck-types SLURP's own ``KbRow`` (``utterance_id``, ``content``,
    ``intent``, ``entity_types``, ``primary_speaker_id``) rather than
    importing that dataclass -- ``rails.knowledge_build`` imports ``KbRow``
    from nowhere but its own module, so a concrete import here would create
    an import cycle (this module is imported BY ``rails.knowledge_build``).

    ``size=None`` selects the entire pool (the 'full' tier). When the hard
    floors alone already meet or exceed ``size``, the floor set IS the
    returned (larger) selection: floors are a HARD requirement, ``size`` is a
    best-effort target, never the other way around.

    Deterministic and pool-order independent: every random draw samples from
    a ``utterance_id``-sorted candidate list via ``random.Random`` seeded by
    ``f"{seed}:{stratum}"`` (stratum = intent name, for both the per-intent
    floor draw and the per-intent diversity fill); the entity-type floor draw
    uses the namespaced tag ``f"{seed}:entity:{entity_type}"`` since it is not
    itself a per-stratum draw.
    """

    rows = tuple(rows)
    if not rows:
        raise RailsError("distribution_sample: rows must be non-empty")
    rows_by_id = {row.utterance_id: row for row in rows}
    if len(rows_by_id) != len(rows):
        raise RailsError("distribution_sample: rows must have unique utterance_id values")

    if size is None or size >= len(rows):
        return tuple(sorted(rows, key=lambda row: row.utterance_id))
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise RailsError("distribution_sample: size must be a positive int or None")

    rows_by_intent: dict[str, list[Row]] = defaultdict(list)
    for row in rows:
        rows_by_intent[row.intent].append(row)

    selected_ids: set[str] = set()

    # Phase 1: every intent keeps >=1 utterance.
    for intent in sorted(rows_by_intent):
        candidates = sorted(rows_by_intent[intent], key=lambda row: row.utterance_id)
        rng = random.Random(f"{seed}:{intent}")
        selected_ids.add(candidates[rng.randrange(len(candidates))].utterance_id)

    # Phase 2: every entity type observed anywhere in TRAIN keeps >=1 exemplar.
    rows_by_entity_type: dict[str, list[Row]] = defaultdict(list)
    all_entity_types: set[str] = set()
    for row in rows:
        for entity_type in row.entity_types:
            rows_by_entity_type[entity_type].append(row)
            all_entity_types.add(entity_type)
    covered_types = {
        entity_type
        for utterance_id in selected_ids
        for entity_type in rows_by_id[utterance_id].entity_types
    }
    for entity_type in sorted(all_entity_types - covered_types):
        candidates = sorted(rows_by_entity_type[entity_type], key=lambda row: row.utterance_id)
        unselected = [row for row in candidates if row.utterance_id not in selected_ids]
        pool = unselected or candidates
        rng = random.Random(f"{seed}:entity:{entity_type}")
        selected_ids.add(pool[rng.randrange(len(pool))].utterance_id)

    floor_count = len(selected_ids)
    if size <= floor_count:
        return tuple(
            sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.utterance_id)
        )

    # Phase 3: Hamilton-apportion the remaining budget over intents by
    # remaining (post-floor) capacity, then fill each intent's extra quota
    # with a diversity-seeking pick.
    remaining_budget = size - floor_count
    floor_by_intent: Counter[str] = Counter(rows_by_id[i].intent for i in selected_ids)
    capacity_by_intent = {
        intent: len(members) - floor_by_intent.get(intent, 0)
        for intent, members in rows_by_intent.items()
    }
    additional_by_intent = hamilton_apportion(capacity_by_intent, remaining_budget)

    for intent in sorted(rows_by_intent):
        extra = additional_by_intent.get(intent, 0)
        if extra <= 0:
            continue
        already_selected_rows = [
            rows_by_id[i] for i in selected_ids if rows_by_id[i].intent == intent
        ]
        candidate_pool = [
            row for row in rows_by_intent[intent] if row.utterance_id not in selected_ids
        ]
        target_stratum_size = len(already_selected_rows) + extra
        speaker_cap = max(1, math.ceil(0.10 * target_stratum_size))
        rng = random.Random(f"{seed}:{intent}")
        picked = greedy_diverse_pick(
            candidate_pool,
            extra,
            already_selected_rows,
            rng,
            text_of=lambda row: row.content,
            id_of=lambda row: row.utterance_id,
            group_of=lambda row: row.primary_speaker_id,
            group_cap=speaker_cap,
        )
        for row in picked:
            selected_ids.add(row.utterance_id)

    return tuple(
        sorted((rows_by_id[i] for i in selected_ids), key=lambda row: row.utterance_id)
    )


__all__ = [
    "distribution_sample",
    "greedy_diverse_pick",
    "hamilton_apportion",
    "jaccard",
    "shingles",
]
