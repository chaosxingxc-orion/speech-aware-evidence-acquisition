"""Deterministic same-type VALUE projection for SLURP slot fillers.

The sibling of ``reproduction.slurp_scoring``'s legal-LABEL projection, and
built for the same reason. That rule maps a predicted ``(scenario, action)``
pair onto the nearest legal pair the TRAIN corpus actually carries; this one
maps a predicted slot FILLER onto the nearest surface form the TRAIN corpus
actually carries **for that same slot type**. Both are model-free
post-processors over an already-sealed response, both are mined from TRAIN
alone, and both are scoring-side: they run strictly between the parse and the
official prediction file, they never touch the parse, and they never rewrite
a slot TYPE.

Why a value projection is worth a rule at all. The official SLURP
``evaluate.py`` lower-cases the GOLD filler at load time and does **not**
lower-case the predicted one (``reproduction.slurp_scoring`` module
docstring reproduces that asymmetry byte for byte, deliberately). So a
prediction that heard the words perfectly but wrote ``"Sunday"`` where the
gold annotation says ``"sunday"`` pays a word-distance of 1.0 and a
char-distance of 1/6 on a span it got exactly right. The same happens to
every spelling the corpus writes one way and the model writes another
(``"7 am"`` against ``"seven am"``, ``"tmrw"`` against ``"tomorrow"``).
Projecting onto the corpus's own surface form is the deterministic repair of
that class, and the threshold is what stops it from rewriting a genuinely
different value into a corpus one.

What the rule is, exactly.

* The inventory is the distinct TRAIN filler surface forms per entity type,
  with their TRAIN mention counts. It is mined from ``train.jsonl`` and from
  nothing else: no devel value, no gold value of the row under repair, and
  no held-out byte ever enters it.
* A predicted ``(type, filler)`` is eligible when the type has an inventory
  and the filler is non-empty.
* The comparison string is the filler ``casefold()``-ed with its whitespace
  collapsed, because the inventory side is already lower-cased by
  ``data.slurp._entity_filler`` -- the very join the official gold side uses.
* Distance is ``reproduction.slurp_scoring``'s OWN normalized character
  distance, imported rather than re-implemented, so the quantity the rule
  thresholds on is the quantity the metric charges for.
* The projection fires when the nearest inventory surface form is at
  distance ``<= threshold``; the winner is the smallest distance, ties broken
  by the larger TRAIN mention count and then lexicographically, so the rule
  is a pure function of the sealed bytes.
* ``threshold = 0.0`` is a meaningful special case rather than a no-op: it
  fires only on an exact match after case folding, which is precisely the
  normalization half of the repair with none of the rewriting half.

What the rule never does: invent a filler for a type the model did not
predict, delete a prediction, change a slot type, reorder entities, or look
at anything but the prediction and the TRAIN inventory.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from .slurp_scoring import SlotEntity, _char_distance

#: Identity of the rule implemented by :func:`project_slot_value`. Bumped only
#: when the RULE changes (candidate set, distance, normalization, tie-break
#: order, or which predictions are eligible) -- never when the corpus the
#: inventory is mined from moves, which the umbrella lock pins instead. Same
#: bump policy as ``reproduction.slurp_scoring.SLURP_LABEL_PROJECTION_ID``.
SLURP_VALUE_PROJECTION_ID = "slurp-value-projection-v1"

#: The branch a predicted filler took, carried on :class:`ValueProjection` so a
#: receipt can count branches instead of inferring them from a before/after map.
VALUE_BRANCH_EMPTY = "empty-filler"
VALUE_BRANCH_NO_INVENTORY = "no-inventory"
VALUE_BRANCH_EXACT = "exact"
VALUE_BRANCH_CASE_FOLD = "case-fold"
VALUE_BRANCH_PROJECTED = "projected"
VALUE_BRANCH_TOO_FAR = "too-far"

#: Every branch name, in the order a receipt reports them.
VALUE_BRANCHES = (
    VALUE_BRANCH_EMPTY,
    VALUE_BRANCH_NO_INVENTORY,
    VALUE_BRANCH_EXACT,
    VALUE_BRANCH_CASE_FOLD,
    VALUE_BRANCH_PROJECTED,
    VALUE_BRANCH_TOO_FAR,
)


class SlurpValueProjectionError(ValueError):
    """The rule refuses its own parameters -- never a model output."""


def normalize_filler(filler: str) -> str:
    """The comparison form: ``casefold()`` with whitespace collapsed.

    The inventory side is already lower-cased by ``data.slurp._entity_filler``
    (the official gold join), so folding the prediction is what puts the two
    sides in the same space. Whitespace is collapsed because a predicted
    filler routinely arrives with a stray double space that no corpus surface
    form carries, and that difference is a formatting artefact rather than a
    heard difference.
    """

    return " ".join(str(filler).casefold().split())


@dataclass(frozen=True)
class ValueProjectionInventory:
    """Distinct TRAIN filler surface forms per entity type, with counts.

    ``fillers`` maps an entity type to its surface forms sorted by descending
    TRAIN mention count then lexicographically -- the same order
    :func:`project_slot_value` breaks ties in, so a receipt can read the
    tie-break off the inventory. ``counts`` carries the mention count of each
    ``(type, filler)`` pair. ``source_identity_hash`` is the sha256 of the
    newline-joined sorted ``type\\tfiller`` lines, so a receipt binds the
    inventory without carrying it.
    """

    source_split: str
    utterance_count: int
    fillers: Mapping[str, tuple[str, ...]]
    counts: Mapping[tuple[str, str], int]
    source_identity_hash: str

    @property
    def entity_types(self) -> tuple[str, ...]:
        """The types carrying at least one surface form, sorted."""

        return tuple(sorted(self.fillers))

    @property
    def distinct_fillers(self) -> int:
        """Distinct ``(type, filler)`` pairs across the whole inventory."""

        return sum(len(values) for values in self.fillers.values())

    def as_json(self) -> dict[str, object]:
        return {
            "projection_id": SLURP_VALUE_PROJECTION_ID,
            "source_split": self.source_split,
            "utterance_count": self.utterance_count,
            "entity_types": len(self.fillers),
            "distinct_fillers": self.distinct_fillers,
            "source_identity_hash": self.source_identity_hash,
            "fillers_per_type": {
                entity_type: len(values)
                for entity_type, values in sorted(self.fillers.items())
            },
        }


@dataclass(frozen=True)
class ValueProjection:
    """One predicted filler's outcome under the rule."""

    entity_type: str
    source_filler: str
    projected_filler: str
    branch: str
    distance: float | None
    changed: bool

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "from": self.source_filler,
            "to": self.projected_filler,
            "branch": self.branch,
            "distance": self.distance,
            "changed": self.changed,
        }


def build_value_projection_inventory(
    material: Iterable[object], *, source_split: str = "train"
) -> ValueProjectionInventory:
    """Mine the inventory from loaded TRAIN material.

    ``material`` is any iterable of objects carrying an ``entities`` sequence
    of ``(type, filler)`` pairs -- ``data.slurp.SlurpTrainMaterial`` in
    production, a small hand-built stand-in in the tests. Taking the loaded
    material rather than a path is what keeps the rule testable without the
    governed corpus, and what keeps the SPLIT decision at the one call site
    that names it.
    """

    counts: dict[tuple[str, str], int] = {}
    utterances = 0
    for utterance in material:
        utterances += 1
        entities = getattr(utterance, "entities", ())
        for entity in entities:
            entity_type = str(getattr(entity, "type", "")).strip()
            filler = normalize_filler(getattr(entity, "filler", ""))
            if not entity_type or not filler:
                continue
            key = (entity_type, filler)
            counts[key] = counts.get(key, 0) + 1
    grouped: dict[str, list[str]] = {}
    for entity_type, filler in counts:
        grouped.setdefault(entity_type, []).append(filler)
    fillers = {
        entity_type: tuple(
            sorted(values, key=lambda value: (-counts[(entity_type, value)], value))
        )
        for entity_type, values in sorted(grouped.items())
    }
    identity = hashlib.sha256(
        "\n".join(
            f"{entity_type}\t{filler}" for entity_type, filler in sorted(counts)
        ).encode("utf-8")
    ).hexdigest()
    return ValueProjectionInventory(
        source_split=source_split,
        utterance_count=utterances,
        fillers=MappingProxyType(fillers),
        counts=MappingProxyType(dict(counts)),
        source_identity_hash=identity,
    )


def load_value_projection_inventory(
    lock: Mapping[str, object], root: Path, *, source_split: str = "train"
) -> ValueProjectionInventory:
    """The production entry point: mine the inventory from ``train.jsonl``.

    Split discipline mirrors ``data.slurp.load_slurp_intent_slot_schema``'s:
    the loader this calls has no ``split`` parameter at all, so a devel or
    test file cannot be reached through here.
    """

    if source_split != "train":
        raise SlurpValueProjectionError(
            f"the value-projection inventory is mined from TRAIN and only from TRAIN; "
            f"got source_split={source_split!r}"
        )
    from ..data.slurp import load_slurp_train_material  # noqa: PLC0415 (import cost)

    material = load_slurp_train_material(lock, root)
    return build_value_projection_inventory(material, source_split=source_split)


def nearest_surface_form(
    inventory: ValueProjectionInventory, entity_type: str, normalized: str
) -> tuple[str, float] | None:
    """The nearest TRAIN surface form of ``entity_type`` to ``normalized``.

    ``None`` when the type carries no inventory. Split out of
    :func:`project_slot_value` because the answer does not depend on the
    threshold at all, so a threshold SWEEP can memoize it once per distinct
    ``(type, normalized filler)`` pair instead of recomputing an edit-distance
    scan per threshold.
    """

    candidates = inventory.fillers.get(entity_type)
    if not candidates:
        return None
    best_filler = candidates[0]
    best_distance = _char_distance(best_filler, normalized)
    if best_distance == 0.0:
        return best_filler, best_distance
    for candidate in candidates[1:]:
        distance = _char_distance(candidate, normalized)
        # `candidates` is already ordered by descending TRAIN count then
        # lexicographically, so a strict `<` keeps that order as the tie-break.
        if distance < best_distance:
            best_filler = candidate
            best_distance = distance
            if best_distance == 0.0:
                break
    return best_filler, best_distance


def project_slot_value(
    entity: SlotEntity,
    inventory: ValueProjectionInventory,
    *,
    threshold: float,
    nearest: tuple[str, float] | None = None,
) -> ValueProjection:
    """Project one predicted ``(type, filler)`` onto the nearest TRAIN surface
    form of the SAME type, when that form is within ``threshold``.

    Returns the outcome; the caller decides what to do with it. The rule never
    changes ``entity.type``. ``nearest`` is an optional memoized
    :func:`nearest_surface_form` result for this exact ``(type, filler)``; it
    is a cache, never an override, and the function refuses one that does not
    reproduce.
    """

    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise SlurpValueProjectionError("threshold must be a number")
    if not 0.0 <= float(threshold) <= 1.0:
        raise SlurpValueProjectionError(
            f"threshold must lie in [0.0, 1.0]; got {threshold!r}"
        )
    entity_type = str(entity.type)
    normalized = normalize_filler(entity.filler)
    if not normalized:
        return ValueProjection(
            entity_type=entity_type,
            source_filler=entity.filler,
            projected_filler=entity.filler,
            branch=VALUE_BRANCH_EMPTY,
            distance=None,
            changed=False,
        )
    resolved = (
        nearest
        if nearest is not None
        else nearest_surface_form(inventory, entity_type, normalized)
    )
    if resolved is None:
        return ValueProjection(
            entity_type=entity_type,
            source_filler=entity.filler,
            projected_filler=entity.filler,
            branch=VALUE_BRANCH_NO_INVENTORY,
            distance=None,
            changed=False,
        )
    best_filler, best_distance = resolved
    if best_filler not in inventory.fillers.get(entity_type, ()):
        raise SlurpValueProjectionError(
            f"memoized nearest {best_filler!r} is not a TRAIN surface form of "
            f"{entity_type!r}"
        )
    if best_distance > float(threshold):
        return ValueProjection(
            entity_type=entity_type,
            source_filler=entity.filler,
            projected_filler=entity.filler,
            branch=VALUE_BRANCH_TOO_FAR,
            distance=best_distance,
            changed=False,
        )
    if best_distance == 0.0:
        branch = (
            VALUE_BRANCH_EXACT if best_filler == entity.filler else VALUE_BRANCH_CASE_FOLD
        )
    else:
        branch = VALUE_BRANCH_PROJECTED
    return ValueProjection(
        entity_type=entity_type,
        source_filler=entity.filler,
        projected_filler=best_filler,
        branch=branch,
        distance=best_distance,
        changed=best_filler != entity.filler,
    )


def project_slu_entities(
    entities: Sequence[SlotEntity],
    inventory: ValueProjectionInventory,
    *,
    threshold: float,
    nearest_cache: dict[tuple[str, str], tuple[str, float] | None] | None = None,
) -> tuple[tuple[SlotEntity, ...], tuple[ValueProjection, ...]]:
    """Apply :func:`project_slot_value` to a whole prediction, in order.

    The returned entity list has the same length and the same types as the
    input, in the same order: the rule is a value rewrite and nothing else.
    ``nearest_cache`` is an optional caller-owned memo of
    :func:`nearest_surface_form`, keyed by ``(type, normalized filler)``, which
    a threshold sweep fills once and reuses across every threshold.
    """

    projected: list[SlotEntity] = []
    outcomes: list[ValueProjection] = []
    for entity in entities:
        nearest = None
        if nearest_cache is not None:
            key = (str(entity.type), normalize_filler(entity.filler))
            if key[1]:
                if key not in nearest_cache:
                    nearest_cache[key] = nearest_surface_form(inventory, key[0], key[1])
                nearest = nearest_cache[key]
        outcome = project_slot_value(
            entity, inventory, threshold=threshold, nearest=nearest
        )
        outcomes.append(outcome)
        projected.append(
            SlotEntity(type=entity.type, filler=outcome.projected_filler)
        )
    return tuple(projected), tuple(outcomes)


def branch_counts(outcomes: Iterable[ValueProjection]) -> dict[str, int]:
    """Every branch, in :data:`VALUE_BRANCHES` order, zero-filled."""

    counts = {branch: 0 for branch in VALUE_BRANCHES}
    for outcome in outcomes:
        if outcome.branch not in counts:
            raise SlurpValueProjectionError(f"unknown branch {outcome.branch!r}")
        counts[outcome.branch] += 1
    return counts


__all__ = [
    "SLURP_VALUE_PROJECTION_ID",
    "VALUE_BRANCHES",
    "VALUE_BRANCH_CASE_FOLD",
    "VALUE_BRANCH_EMPTY",
    "VALUE_BRANCH_EXACT",
    "VALUE_BRANCH_NO_INVENTORY",
    "VALUE_BRANCH_PROJECTED",
    "VALUE_BRANCH_TOO_FAR",
    "SlurpValueProjectionError",
    "ValueProjection",
    "ValueProjectionInventory",
    "branch_counts",
    "build_value_projection_inventory",
    "load_value_projection_inventory",
    "nearest_surface_form",
    "normalize_filler",
    "project_slot_value",
    "project_slu_entities",
]
