"""The three EVO-A1 loop rosters: how they are cut, and the proof they are disjoint.

``analysis.a2t_evo_capacity`` decides how many rows each targeted tool can
afford; this module turns that decision into three frozen
``core.roster.freeze_roster`` receipts and the disjointness proof a reviewer
needs. Identity only -- sample id, tier, ``query_idx``, manifest id, gold
primary ``tool_name`` -- and no I/O beyond what the caller hands in.

* ``A2T-EVO-FOLD-A-V1`` -- stage-one reward rows: each fold-capable target tool
  at its contention-resolved quota, plus a tier-stratified background drawn
  from tools no MF-1 target names. The background exists so the confirmation
  can see the failure a per-target count rule cannot: a rewrite that wins its
  own pair by breaking the tools nobody targeted.
* ``A2T-EVO-FOLD-B-V1`` -- the same shape on disjoint blocks.
* ``A2T-EVO-EXEMPLARS-V1`` -- every remaining unit of a fold-capable tool, and
  up to ``EXEMPLAR_RESERVE`` for each tool the census dropped so the proposer
  can still see both sides of a pair it is asked to separate. Text-only.

Two group-key regimes inside one draw, which is why ``exclude_groups`` is built
per row rather than per roster. A TARGET row's group is its own unit, because a
tool with 20 units in 5 blocks must be allowed several units of one block. A
BACKGROUND row's group is its BLOCK, so drawing one background row claims the
whole block and fold B can be given fold A's ids to exclude and get block
disjointness for free.
"""

from __future__ import annotations

import collections
import hashlib
from typing import Callable, Mapping, Sequence

from ..core.roster import RosterItem, freeze_roster
from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY
from .a2t_evo_capacity import BUCKETS, EXEMPLAR_RESERVE

FOLD_A_ID = "A2T-EVO-FOLD-A-V1"
FOLD_B_ID = "A2T-EVO-FOLD-B-V1"
EXEMPLARS_ID = "A2T-EVO-EXEMPLARS-V1"
BACKGROUND_ROWS = 120
BACKGROUND_PREFIX = "background:"

DESIGN = (
    "EVO-A1 loop roster, roster_role 'construction' (owner decision 2026-09-05): these "
    "identities may be read WITH their gold offline, and gold may reach the frozen core only "
    "through the text-only 'construction-proposer-text' arm as prompt artifacts, never answers. "
    "split_role stays 'discovery', the TRAIN90 precedent. Block-disjoint from the Audio2Tool "
    "exposure union, from the reserved A2T-FRESH-800-V1, and from the other two EVO rosters."
)

__all__ = [
    "FOLD_A_ID",
    "FOLD_B_ID",
    "EXEMPLARS_ID",
    "BACKGROUND_ROWS",
    "BACKGROUND_PREFIX",
    "DESIGN",
    "roster_items",
    "blocks_of",
    "ids_of",
    "gate_identity_hash",
    "background_quota",
    "freeze_evo_rosters",
    "disjointness_proof",
    "roster_documents",
    "ROLES",
]


def roster_items(rows: Sequence[object], stratum_of: Callable[[object], str]) -> list[RosterItem]:
    """One :class:`RosterItem` per unit, the wav chosen by the release's own
    first-successful-speaker rule -- the unit's lowest manifest id."""

    return [
        RosterItem(
            sample_id=row.sample_ids[0],  # type: ignore[attr-defined]
            stratum=stratum_of(row),
            extra={
                "id": row.item_ids[0],  # type: ignore[attr-defined]
                "key": f"{AUDIO2TOOL_LOCK_KEY}:{row.sample_ids[0]}",  # type: ignore[attr-defined]
                "query_idx": row.query_idx,  # type: ignore[attr-defined]
                "tier": row.tier,  # type: ignore[attr-defined]
                "tool_name": row.tool_name,  # type: ignore[attr-defined]
            },
        )
        for row in sorted(rows, key=lambda row: row.unit_id)  # type: ignore[attr-defined]
    ]


def blocks_of(receipt: Mapping[str, object]) -> set[int]:
    return {int(item["query_idx"]) for item in receipt["items"]}  # type: ignore[index,union-attr]


def ids_of(receipt: Mapping[str, object]) -> set[str]:
    return {str(item["sample_id"]) for item in receipt["items"]}  # type: ignore[index,union-attr]


def gate_identity_hash(receipt: Mapping[str, object]) -> str:
    """The identity ``contracts.gate_exposure`` recomputes for a construction
    roster: sha256 over the LF-joined sorted ``<carrier>/<sample_id>`` keys.

    Recomputed here rather than trusted from ``split_identity_hash`` so the
    receipt and the gate that will read it are proven to agree before the
    receipt is written, not on the first refused flight.
    """

    keys = sorted(
        f"{AUDIO2TOOL_LOCK_KEY}/{item['sample_id']}"  # type: ignore[index]
        for item in receipt["items"]  # type: ignore[union-attr]
    )
    return hashlib.sha256("\n".join(keys).encode("utf-8")).hexdigest()


def background_quota(tiers: Sequence[str], total: int) -> dict[str, int]:
    """``total`` background rows spread evenly over ``tiers``, the remainder
    going to the earliest tiers by name so the split is deterministic."""

    per_tier, extra = divmod(total, len(tiers))
    return {
        f"{BACKGROUND_PREFIX}{tier}": per_tier + (1 if index < extra else 0)
        for index, tier in enumerate(sorted(tiers))
    }


def freeze_evo_rosters(
    pool: Sequence[object],
    tools: Sequence[str],
    capacity: Mapping[str, Mapping[str, object]],
    *,
    seed: int,
    exposed: frozenset[str],
    background_rows: int = BACKGROUND_ROWS,
) -> dict[str, dict[str, object]]:
    """Freeze all three rosters in one pass, so they can be proven disjoint."""

    named = set(tools)
    bucket_of: dict[int, str] = {
        int(block): name
        for tool in tools
        for name in BUCKETS
        for block in capacity[tool]["blocks_by_bucket"][name]  # type: ignore[index]
    }
    occupied = {
        int(row.query_idx) for row in pool if row.tool_name in named  # type: ignore[attr-defined]
    }
    background = [
        row
        for row in pool
        if row.tool_name not in named and int(row.query_idx) not in occupied  # type: ignore[attr-defined]
    ]
    groups = {
        **{
            row.sample_ids[0]: f"unit:{row.unit_id}"  # type: ignore[attr-defined]
            for row in pool
            if row.tool_name in named  # type: ignore[attr-defined]
        },
        **{
            row.sample_ids[0]: f"block:{row.query_idx}"  # type: ignore[attr-defined]
            for row in background
        },
    }
    quotas = {
        **{tool: int(capacity[tool]["fold_quota"]) for tool in tools if capacity[tool]["fold_quota"]},
        **background_quota(sorted({str(row.tier) for row in background}), background_rows),  # type: ignore[attr-defined]
    }

    def stratum(row: object) -> str:
        tool = str(getattr(row, "tool_name"))
        return tool if tool in named else f"{BACKGROUND_PREFIX}{getattr(row, 'tier')}"

    def fold(roster_id: str, bucket: str, exclude: set[str]) -> dict[str, object]:
        rows = [
            row
            for row in pool
            if row.tool_name in named  # type: ignore[attr-defined]
            and capacity[row.tool_name]["fold_quota"]  # type: ignore[attr-defined,index]
            and bucket_of.get(int(row.query_idx)) == bucket  # type: ignore[attr-defined]
        ] + background
        return freeze_roster(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            candidates=roster_items(rows, stratum),
            per_stratum=quotas,
            seed=seed,
            split_role="discovery",
            exclude_sample_ids=set(exposed) | exclude,
            exclude_groups=groups,
            roster_id=roster_id,
            roster_role="construction",
        )

    fold_a = fold(FOLD_A_ID, "fold_a", set())
    fold_b = fold(FOLD_B_ID, "fold_b", ids_of(fold_a))
    left = [
        row
        for row in pool
        if row.tool_name in named  # type: ignore[attr-defined]
        and bucket_of.get(int(row.query_idx)) == "exemplars"  # type: ignore[attr-defined]
    ]
    available = collections.Counter(
        str(getattr(row, "tool_name")) for row in left
    )
    exemplars = freeze_roster(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        candidates=roster_items(left, stratum),
        per_stratum={
            tool: (
                count
                if capacity[tool]["fold_quota"]
                else min(EXEMPLAR_RESERVE, count)
            )
            for tool, count in available.items()
        },
        seed=seed,
        split_role="discovery",
        exclude_sample_ids=set(exposed) | ids_of(fold_a) | ids_of(fold_b),
        exclude_groups=groups,
        roster_id=EXEMPLARS_ID,
        roster_role="construction",
    )
    return {
        "fold_a": fold_a,
        "fold_b": fold_b,
        "exemplars": exemplars,
        "pool": {
            "fold_eligible_units": len(pool),
            "fold_eligible_blocks": len({int(row.query_idx) for row in pool}),  # type: ignore[attr-defined]
            "target_tool_blocks": len(occupied),
            "background_candidate_units": len(background),
            "background_candidate_blocks": len({int(row.query_idx) for row in background}),  # type: ignore[attr-defined]
            "exemplar_units_available": dict(sorted(available.items())),
        },
    }


def disjointness_proof(
    rosters: Mapping[str, Mapping[str, object]],
    *,
    exposure_blocks: set[int],
    exposed: frozenset[str],
) -> dict[str, int]:
    """Every overlap that must be zero, recomputed from the receipts."""

    names = ("fold_a", "fold_b", "exemplars")
    blocks = {name: blocks_of(rosters[name]) for name in names}
    ids = {name: ids_of(rosters[name]) for name in names}
    drawn: set[str] = set().union(*ids.values())
    proof = {
        f"{left}_vs_{right}_blocks": len(blocks[left] & blocks[right])
        for index, left in enumerate(names)
        for right in names[index + 1 :]
    }
    proof["any_vs_exposure_union_blocks"] = len(set().union(*blocks.values()) & exposure_blocks)
    proof["any_vs_exposure_union_sample_ids"] = len(drawn & set(exposed))
    proof["duplicate_sample_ids_across_rosters"] = sum(len(ids[name]) for name in names) - len(drawn)
    return proof


#: Receipt file stem and one-line role per roster key.
ROLES = {
    "fold_a": ("a2t-evo-fold-a-v1", "stage-one reward rows, fold A"),
    "fold_b": ("a2t-evo-fold-b-v1", "stage-two confirmation rows, fold B"),
    "exemplars": ("a2t-evo-exemplars-v1", "the proposer's exemplar pool; text-only"),
}

BLOCK_POLICY = (
    "block-level: a query_idx block is the leakage unit, because the carrier re-renders one "
    "base scenario at several tiers. Every block belongs to at most one of the three rosters, "
    "by construction and re-proved here"
)

SELECTION_RULE = (
    "one wav per (tier, query_idx) unit: the unit's lowest manifest id, which is the release's "
    "own first-successful-speaker pick"
)


def roster_documents(
    cut: Mapping[str, Mapping[str, object]],
    capacity: Mapping[str, Mapping[str, object]],
    *,
    proof: Mapping[str, int],
    exposure: Mapping[str, object],
    exposure_blocks: int,
    shared: Mapping[str, object],
) -> list[tuple[str, dict[str, object]]]:
    """``[(file stem, receipt document)]``, one per roster, gate-hash verified.

    Raises :class:`ValueError` when a receipt's own ``split_identity_hash``
    disagrees with what ``contracts.gate_exposure`` would recompute -- a
    disagreement is a refused flight later, and is refused here instead.
    """

    common = {
        **shared,
        "design": DESIGN,
        "status": "FROZEN_CONSTRUCTION_ROSTER",
        "sample_selection_rule": SELECTION_RULE,
        "target_gold_opened_before_receipt": False,
        "tool_capacity": {tool: dict(capacity[tool]) for tool in sorted(capacity)},
        "exposure_union": exposure,
    }
    out: list[tuple[str, dict[str, object]]] = []
    for key, (stem, role) in ROLES.items():
        receipt = cut[key]
        document = {
            **receipt,
            **common,
            "role": role,
            "gate_exposure_identity_hash": gate_identity_hash(receipt),
            "block_disjointness": {
                "policy": BLOCK_POLICY,
                "distinct_blocks": len(blocks_of(receipt)),
                "exposure_union_sample_ids": exposure["union_sample_ids"],
                "exposure_union_blocks": exposure_blocks,
                **proof,
            },
        }
        if document["gate_exposure_identity_hash"] != receipt["split_identity_hash"]:
            raise ValueError(
                f"{receipt['roster_id']}: the gate's identity hash disagrees with freeze_roster"
            )
        out.append((stem, document))
    return out
