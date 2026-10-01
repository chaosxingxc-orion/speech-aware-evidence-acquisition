"""Bind on-demand targets to exact released authored construction relations.

Reuse the same slot relation as automatic candidate supply. Never infer a
relation from a value ID or prose without rebuilding its pinned source first.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from .errors import RailsError
from .hashing import content_hash
from .knowledge import KnowledgeSnapshot


@dataclass(frozen=True)
class ReleasedTargetIndex:
    snapshot_sha256: str
    mappings: Mapping[str, tuple[str, ...]]
    receipt: Mapping[str, object]

    def validate(self, snapshot: KnowledgeSnapshot) -> "ReleasedTargetIndex":
        if self.snapshot_sha256 != snapshot.content_hash():
            raise RailsError("released target index belongs to another snapshot")
        values = {value.value_id for value in snapshot.values}
        for target, ids in self.mappings.items():
            if (not isinstance(target, str) or not target
                    or not isinstance(ids, tuple) or not ids
                    or len(ids) != len(set(ids)) or not set(ids) <= values):
                raise RailsError("released target index contains invalid mappings")
        unsigned = {k: v for k, v in self.receipt.items() if k != "index_sha256"}
        if (self.receipt.get("snapshot_sha256") != self.snapshot_sha256
                or self.receipt.get("mappings_sha256") != content_hash(dict(self.mappings))
                or self.receipt.get("index_sha256") != content_hash(unsigned)):
            raise RailsError("released target index receipt differs from its mappings")
        return self


def build_released_target_index(
    store: object, *, data_root: Path, legal_candidate_ids: Sequence[str], target_axis: str = "task",
) -> ReleasedTargetIndex | None:
    """Rebuild supported legacy stores and bind their explicit target relations.

    Return None for other builders, preserving the existing task_target lookup.
    Historical snapshots and value bytes remain unchanged.
    """
    from .candidate_semantic_supply import (
        AUTHORED_SOURCE_SCHEMA, _read_released_source, _released_candidate_index,
    )
    from .semantic_knowledge_build import (
        AuthoredSemanticKnowledgeSpec, INTENT_BOUNDARY_BUILD_POLICY_ID,
        SLOT_CONTRACT_BUILD_POLICY_ID, build_intent_boundary_snapshot,
    )

    if target_axis not in {"task", "slot-type"}:
        raise RailsError("unknown released target axis")
    snapshot = store.snapshot
    if target_axis == "slot-type" and snapshot.builder_policy_id != SLOT_CONTRACT_BUILD_POLICY_ID:
        raise RailsError("slot-type lookup requires a released slot-contract store")
    policy = snapshot.builder_policy_id
    if policy not in {INTENT_BOUNDARY_BUILD_POLICY_ID, SLOT_CONTRACT_BUILD_POLICY_ID}:
        return None
    legal = tuple(legal_candidate_ids)
    if (not legal or any(not isinstance(item, str) or not item for item in legal)
            or len(set(legal)) != len(legal)):
        raise RailsError("released target lookup requires the full legal candidate inventory")
    if policy == SLOT_CONTRACT_BUILD_POLICY_ID:
        mappings = _released_candidate_index(
            store, data_root=data_root, legal_candidate_ids=legal,
        )
        relation = "authored-slot-intent-bindings-v1"
        if target_axis == "slot-type":
            # The verified authored source defines the slot identity. Never
            # recover it by parsing arbitrary value IDs or model prose.
            source = _read_released_source(store, data_root)
            mappings = {row["slot_id"]: (f"slot-contract:{row['slot_id']}",)
                        for row in source["rows"]}
            relation = "authored-slot-id-v1"
    else:
        source = _read_released_source(store, data_root)
        if (set(source) != {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}
                or source["schema"] != AUTHORED_SOURCE_SCHEMA
                or source["builder_policy_id"] != policy
                or source["source_split_identity_hash"] != snapshot.source_split_identity_hash):
            raise RailsError("released intent source identity differs from its snapshot")
        rebuilt = build_intent_boundary_snapshot(
            AuthoredSemanticKnowledgeSpec(
                carrier_lock_key="slurp",
                source_split_identity_hash=snapshot.source_split_identity_hash,
                permitted_source_sample_ids=snapshot.source_sample_ids,
                source_partition_role=snapshot.source_partition_role,
            ),
            rows=source["rows"],
        )
        if rebuilt.frozen_json() != snapshot.frozen_json():
            raise RailsError("released intent source differs from its snapshot")
        mappings = {
            row["intent_id"]: (f"intent-boundary:{row['intent_id']}",)
            for row in source["rows"]
        }
        if not set(mappings) <= set(legal):
            raise RailsError("released intent target is outside the legal inventory")
        relation = "authored-intent-id-v1"
    mappings = MappingProxyType(dict(mappings))
    receipt = {
        "schema": "saea-released-target-index-v1",
        "snapshot_sha256": snapshot.content_hash(),
        "builder_policy_id": policy,
        "relation_policy_id": relation,
        "source_sha256": store.source_pin["sha256"],
        "release_sha256": store.release_pin["sha256"],
        "legal_candidate_ids_sha256": content_hash(sorted(legal)),
        "mappings_sha256": content_hash(dict(mappings)),
    }
    receipt["index_sha256"] = content_hash(receipt)
    return ReleasedTargetIndex(
        snapshot.content_hash(), mappings, MappingProxyType(receipt),
    ).validate(snapshot)
