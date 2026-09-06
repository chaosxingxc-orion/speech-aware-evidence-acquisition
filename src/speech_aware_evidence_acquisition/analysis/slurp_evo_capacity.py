"""EVO-S1 construction capacity on SLURP TRAIN (model-free, zero contacts).

Exposure row ``SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1``. Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections
4c and 5, whose loop needs three DISJOINT slices of every target: fold-A
reward rows, fold-B reward rows, and an exemplar pool of at least ``M = 8``
utterances per proposer draw. On Audio2Tool that requirement is a wall
(``analysis.a2t_evo_capacity``: nine of the twenty-three targeted tools
cannot supply it). On SLURP the target is a SCENARIO and the corpus is two
orders of magnitude larger per target, so this census exists to state the
absence of a wall with numbers rather than to discover one.

The block unit is the UTTERANCE id: SLURP records one sentence once and
several speakers read it, so every recording of a sentence has to stay in one
fold or a fold-B confirmation would be scoring rows whose text fold A already
paid for. Every count below is therefore an utterance count unless it says
"recordings".

Split discipline. Only ``train`` is opened, through the two base loaders that
can reach nothing else: :func:`data.slurp.load_slurp_train_material` (its
metadata path is ``_SPLIT_FILES["train"]``) and
:func:`data.slurp.load_slurp_intent_slot_schema` (no ``split`` parameter at
all). The DEV-1000 mixture the folds mirror is read from the committed
probe-sample receipt, never from ``devel.jsonl``. TRAIN sentence text is never
read as text: this module consults no ``sentence`` field and renders no
filler; the only text path is the base loader's own entity-filler join, which
reaches this module already reduced to mention COUNTS.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..data.slurp import (
    SlurpIntentSlotSchema,
    load_slurp_intent_slot_schema,
    load_slurp_train_material,
)

CAPACITY_SCHEMA = "saea-slurp-evo-construction-capacity-v1"

#: Program section 5 transposed to scenarios (the EVO-S1 brief, 2026-09-06):
#: 30 utterances per scenario in each of the two folds, an exemplar pool of at
#: least 24 per scenario so three seeded draws of ``M`` can differ in
#: membership, and ``M = 8`` exemplars shown per proposer draw.
FOLD_QUOTA_PER_SCENARIO = 30
EXEMPLAR_QUOTA_PER_SCENARIO = 24
EXEMPLAR_DRAW_M = 8

_HEADSET_SUFFIX = "-headset.flac"


@dataclass(frozen=True)
class TrainUnit:
    """One TRAIN utterance as the loop sees it: a block, not a recording."""

    utterance_id: str
    scenario: str
    action: str
    recordings: int
    headset_recordings: int
    speakers: tuple[str, ...]
    entity_types: tuple[str, ...]

    @property
    def intent(self) -> str:
        return f"{self.scenario}_{self.action}"

    @property
    def far_field_recordings(self) -> int:
        return self.recordings - self.headset_recordings

    @property
    def has_entities(self) -> bool:
        return bool(self.entity_types)


def train_units(lock: Mapping[str, object], root: Path) -> tuple[TrainUnit, ...]:
    """Every real TRAIN utterance with its recording, speaker and type facts."""

    material = load_slurp_train_material(lock, root)
    units: list[TrainUnit] = []
    for item in material:
        headset = sum(
            1 for rec in item.recordings if rec.media_relpath.endswith(_HEADSET_SUFFIX)
        )
        units.append(
            TrainUnit(
                utterance_id=item.utterance_id,
                scenario=item.scenario,
                action=item.action,
                recordings=len(item.recordings),
                headset_recordings=headset,
                speakers=tuple(sorted({rec.speaker_id for rec in item.recordings})),
                entity_types=tuple(item.entity_types),
            )
        )
    return tuple(sorted(units, key=lambda unit: (unit.scenario, unit.utterance_id)))


def _group_rows(units: Sequence[TrainUnit], key: str) -> list[dict[str, object]]:
    buckets: dict[str, list[TrainUnit]] = {}
    for unit in units:
        buckets.setdefault(getattr(unit, key), []).append(unit)
    rows: list[dict[str, object]] = []
    for name in sorted(buckets):
        members = buckets[name]
        speakers = {speaker for unit in members for speaker in unit.speakers}
        headset = sum(unit.headset_recordings for unit in members)
        recordings = sum(unit.recordings for unit in members)
        with_entities = sum(1 for unit in members if unit.has_entities)
        inventory = Counter()
        for unit in members:
            for entity_type in unit.entity_types:
                inventory[entity_type] += 1
        rows.append(
            {
                key: name,
                "utterances": len(members),
                "recordings": recordings,
                "headset_recordings": headset,
                "far_field_recordings": recordings - headset,
                "headset_share": round(headset / recordings, 6) if recordings else 0.0,
                "speakers": len(speakers),
                "utterances_with_entities": with_entities,
                "zero_entity_share": round(1.0 - with_entities / len(members), 6),
                "entity_types": len(inventory),
                "entity_type_utterance_counts": dict(
                    sorted(inventory.items(), key=lambda item: (-item[1], item[0]))
                ),
            }
        )
    return rows


def _mentions_by_intent(schema: SlurpIntentSlotSchema) -> dict[str, dict[str, int]]:
    return {
        intent: {
            entity_type: count for entity_type, count, _share in profile.types
        }
        for intent, profile in schema.intents.items()
    }


def _scenario_of_intent(units: Sequence[TrainUnit]) -> dict[str, str]:
    return {unit.intent: unit.scenario for unit in units}


def capacity_rows(
    units: Sequence[TrainUnit],
    *,
    fold_quota: int = FOLD_QUOTA_PER_SCENARIO,
    exemplar_quota: int = EXEMPLAR_QUOTA_PER_SCENARIO,
) -> list[dict[str, object]]:
    """Per scenario: what the loop needs, what TRAIN has, and the headroom."""

    need = 2 * fold_quota + exemplar_quota
    buckets: dict[str, list[TrainUnit]] = {}
    for unit in units:
        buckets.setdefault(unit.scenario, []).append(unit)
    rows: list[dict[str, object]] = []
    for scenario in sorted(buckets):
        members = buckets[scenario]
        with_entities = sum(1 for unit in members if unit.has_entities)
        rows.append(
            {
                "scenario": scenario,
                "train_utterances": len(members),
                "required_utterances": need,
                "utterances_with_entities": with_entities,
                "required_exemplar_utterances": exemplar_quota,
                "fold_quota": fold_quota,
                "headroom_utterances": len(members) - need,
                "headroom_exemplar_utterances": with_entities - exemplar_quota,
                "satisfies_folds": len(members) >= need,
                "satisfies_exemplars": with_entities >= exemplar_quota,
            }
        )
    return rows


def census_document(
    units: Sequence[TrainUnit],
    *,
    schema_full: SlurpIntentSlotSchema,
    schema_committed: Mapping[str, object],
    dev_mixture: Mapping[str, int],
    dev_receipt: Mapping[str, object],
    fold_quota: int = FOLD_QUOTA_PER_SCENARIO,
    exemplar_quota: int = EXEMPLAR_QUOTA_PER_SCENARIO,
    shared: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """The whole ``capacity.json`` payload; pure, so the caller writes it."""

    mentions = _mentions_by_intent(schema_full)
    scenario_of = _scenario_of_intent(units)
    capacity = capacity_rows(
        units, fold_quota=fold_quota, exemplar_quota=exemplar_quota
    )
    mentions_by_scenario: dict[str, Counter] = {}
    for intent, counts in mentions.items():
        bucket = mentions_by_scenario.setdefault(scenario_of[intent], Counter())
        for entity_type, count in counts.items():
            bucket[entity_type] += count
    scenarios = _group_rows(units, "scenario")
    for row in scenarios:
        counts = mentions_by_scenario.get(str(row["scenario"]), Counter())
        row["entity_mentions"] = sum(counts.values())
        row["entity_type_mention_counts"] = dict(
            sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        )
    intents = _group_rows(units, "intent")
    for row in intents:
        counts = mentions.get(str(row["intent"]), {})
        row["entity_mentions"] = sum(counts.values())
        row["scenario"] = scenario_of[str(row["intent"])]
        profile = schema_committed.get(str(row["intent"]))
        row["committed_schema_types"] = 0 if profile is None else int(profile)
    document: dict[str, object] = {
        "schema": CAPACITY_SCHEMA,
        "block_unit": "utterance id (every recording of a sentence stays in one fold)",
        "quotas": {
            "fold_quota_per_scenario": fold_quota,
            "exemplar_quota_per_scenario": exemplar_quota,
            "exemplar_draw_m": EXEMPLAR_DRAW_M,
            "required_utterances_per_scenario": 2 * fold_quota + exemplar_quota,
        },
        "population": {
            "source_split": schema_full.source_split,
            "source_identity_hash": schema_full.source_identity_hash,
            "utterances": len(units),
            "recordings": sum(unit.recordings for unit in units),
            "headset_recordings": sum(unit.headset_recordings for unit in units),
            "far_field_recordings": sum(unit.far_field_recordings for unit in units),
            "speakers": len({s for unit in units for s in unit.speakers}),
            "scenarios": len({unit.scenario for unit in units}),
            "intents": len({unit.intent for unit in units}),
            "utterances_with_entities": sum(1 for unit in units if unit.has_entities),
        },
        "dev_1000_mixture": {
            "receipt": "docs/receipts/probe-samples/DEV-1000.json",
            "split_identity_hash": dev_receipt.get("split_identity_hash"),
            "run_identity_hash": dev_receipt.get("run_identity_hash"),
            "scenario_allocation": dict(sorted(dev_mixture.items())),
        },
        "capacity": capacity,
        "scenarios": scenarios,
        "intents": intents,
        "verdict": {
            "scenarios_short_of_folds": [
                row["scenario"] for row in capacity if not row["satisfies_folds"]
            ],
            "scenarios_short_of_exemplars": [
                row["scenario"] for row in capacity if not row["satisfies_exemplars"]
            ],
            "min_headroom_utterances": min(
                int(row["headroom_utterances"]) for row in capacity
            ),
            "min_headroom_exemplar_utterances": min(
                int(row["headroom_exemplar_utterances"]) for row in capacity
            ),
            "capacity_wall": any(
                not row["satisfies_folds"] or not row["satisfies_exemplars"]
                for row in capacity
            ),
        },
    }
    if shared:
        document.update(dict(shared))
    return document


def load_schemas(
    lock: Mapping[str, object], root: Path
) -> tuple[SlurpIntentSlotSchema, SlurpIntentSlotSchema]:
    """``(unfloored, committed)`` -- the full inventory and the artifact
    ``A_0`` the loop evolves, both mined from TRAIN by the same base loader."""

    return (
        load_slurp_intent_slot_schema(lock, root, min_share=0.0),
        load_slurp_intent_slot_schema(lock, root),
    )


__all__ = [
    "CAPACITY_SCHEMA",
    "EXEMPLAR_DRAW_M",
    "EXEMPLAR_QUOTA_PER_SCENARIO",
    "FOLD_QUOTA_PER_SCENARIO",
    "TrainUnit",
    "capacity_rows",
    "census_document",
    "load_schemas",
    "train_units",
]
