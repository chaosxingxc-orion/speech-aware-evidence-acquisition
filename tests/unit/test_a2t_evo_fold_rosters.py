"""Unit tests for the three EVO-A1 loop rosters, on a synthetic pool.

No carrier bytes, no lock, no committed receipts, no network.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import joint_capacity
from speech_aware_evidence_acquisition.analysis.a2t_evo_rosters import (
    BACKGROUND_PREFIX,
    EXEMPLARS_ID,
    FOLD_A_ID,
    FOLD_B_ID,
    background_quota,
    blocks_of,
    disjointness_proof,
    freeze_evo_rosters,
    gate_identity_hash,
    ids_of,
    roster_documents,
)

TIERS = ("tier1_direct", "tier2_parametric", "tier3_multi_intent", "tier4_implicit")


@dataclass(frozen=True)
class Row:
    unit_id: str
    tier: str
    query_idx: int
    tool_name: str
    sample_ids: tuple[str, ...]
    item_ids: tuple[int, ...]


def row(tool: str, block: int, index: int) -> Row:
    tier = TIERS[index % len(TIERS)]
    sample_id = f"{tier}:{block:03d}{index:03d}"
    return Row(
        unit_id=f"{tier}:{block}:{index}",
        tier=tier,
        query_idx=block,
        tool_name=tool,
        sample_ids=(sample_id,),
        item_ids=(block * 1000 + index,),
    )


def synthetic_pool() -> tuple[list[Row], list[str]]:
    """Three target tools with room to spare, one that cannot supply folds,
    and enough non-target rows in untouched blocks to fill a background."""

    rows: list[Row] = []
    block = 0
    for tool in ("alpha", "beta", "gamma"):
        for _ in range(16):
            block += 1
            rows.extend(row(tool, block, index) for index in range(4))
    for _ in range(5):
        block += 1
        rows.append(row("tiny", block, 0))
    for _ in range(60):
        block += 1
        rows.extend(row("other", block, index) for index in range(2))
    return rows, ["alpha", "beta", "gamma", "tiny"]


def cut_synthetic(background_rows: int = 8):
    rows, tools = synthetic_pool()
    capacity, _blocks = joint_capacity(rows, tools, seed=20260906)
    cut = freeze_evo_rosters(
        rows,
        tools,
        capacity,
        seed=20260906,
        exposed=frozenset(),
        background_rows=background_rows,
    )
    return rows, tools, capacity, cut


def test_background_quota_spreads_evenly_and_deterministically() -> None:
    quotas = background_quota(["b", "a", "c"], 8)
    assert quotas == {f"{BACKGROUND_PREFIX}a": 3, f"{BACKGROUND_PREFIX}b": 3, f"{BACKGROUND_PREFIX}c": 2}
    assert sum(quotas.values()) == 8


def test_the_three_rosters_are_block_disjoint_and_id_disjoint() -> None:
    _rows, _tools, _capacity, cut = cut_synthetic()
    proof = disjointness_proof(cut, exposure_blocks=set(), exposed=frozenset())
    assert proof == {
        "fold_a_vs_fold_b_blocks": 0,
        "fold_a_vs_exemplars_blocks": 0,
        "fold_b_vs_exemplars_blocks": 0,
        "any_vs_exposure_union_blocks": 0,
        "any_vs_exposure_union_sample_ids": 0,
        "duplicate_sample_ids_across_rosters": 0,
    }
    assert blocks_of(cut["fold_a"]) and blocks_of(cut["fold_b"]) and blocks_of(cut["exemplars"])


def test_the_two_folds_carry_the_same_per_tool_quotas() -> None:
    _rows, tools, capacity, cut = cut_synthetic()
    for tool in tools:
        quota = int(capacity[tool]["fold_quota"])
        assert cut["fold_a"]["strata_counts"].get(tool, 0) == quota
        assert cut["fold_b"]["strata_counts"].get(tool, 0) == quota
    assert cut["fold_a"]["roster_id"] == FOLD_A_ID
    assert cut["fold_b"]["roster_id"] == FOLD_B_ID
    assert cut["exemplars"]["roster_id"] == EXEMPLARS_ID


def test_a_dropped_tool_has_no_fold_rows_but_keeps_exemplars() -> None:
    _rows, _tools, capacity, cut = cut_synthetic()
    assert capacity["tiny"]["survives"] is False
    assert "tiny" not in cut["fold_a"]["strata_counts"]
    assert "tiny" not in cut["fold_b"]["strata_counts"]
    assert cut["exemplars"]["strata_counts"]["tiny"] == 5


def test_background_rows_come_only_from_untargeted_tools_and_one_per_block() -> None:
    _rows, tools, _capacity, cut = cut_synthetic(background_rows=8)
    for fold in ("fold_a", "fold_b"):
        background = [
            item
            for item in cut[fold]["items"]
            if str(item["stratum"]).startswith(BACKGROUND_PREFIX)
        ]
        assert len(background) == 8
        assert all(item["tool_name"] not in tools for item in background)
        blocks = [item["query_idx"] for item in background]
        assert len(blocks) == len(set(blocks))


def test_every_roster_is_a_construction_discovery_roster_the_gate_will_accept() -> None:
    _rows, _tools, capacity, cut = cut_synthetic()
    proof = disjointness_proof(cut, exposure_blocks=set(), exposed=frozenset())
    documents = roster_documents(
        cut,
        capacity,
        proof=proof,
        exposure={"union_sample_ids": 0},
        exposure_blocks=0,
        shared={"authority": "test"},
    )
    assert [stem for stem, _ in documents] == [
        "a2t-evo-fold-a-v1",
        "a2t-evo-fold-b-v1",
        "a2t-evo-exemplars-v1",
    ]
    for _stem, document in documents:
        assert document["roster_role"] == "construction"
        assert document["split_role"] == "discovery"
        assert document["gate_exposure_identity_hash"] == document["split_identity_hash"]
        assert document["target_gold_opened_before_receipt"] is False


def test_a_tampered_receipt_is_refused_before_it_is_written() -> None:
    _rows, _tools, capacity, cut = cut_synthetic()
    broken = {key: dict(value) for key, value in cut.items() if key != "pool"}
    broken["fold_a"]["split_identity_hash"] = "0" * 64
    with pytest.raises(ValueError, match="disagrees with freeze_roster"):
        roster_documents(
            broken,
            capacity,
            proof=disjointness_proof(cut, exposure_blocks=set(), exposed=frozenset()),
            exposure={"union_sample_ids": 0},
            exposure_blocks=0,
            shared={},
        )


def test_gate_identity_hash_is_over_carrier_prefixed_sorted_ids() -> None:
    import hashlib

    receipt = {"items": [{"sample_id": "b"}, {"sample_id": "a"}]}
    expected = hashlib.sha256(b"audio2tool/a\naudio2tool/b").hexdigest()
    assert gate_identity_hash(receipt) == expected


def test_exposed_ids_are_never_drawn() -> None:
    # Exposure is excluded from the pool upstream, so the slack is in the
    # background tool; a targeted tool's quota is exact and fails closed.
    rows, tools = synthetic_pool()
    capacity, _blocks = joint_capacity(rows, tools, seed=20260906)
    spare = [row for row in rows if row.tool_name == "other"]
    banned = frozenset({spare[0].sample_ids[0], spare[1].sample_ids[0]})
    cut = freeze_evo_rosters(
        rows, tools, capacity, seed=20260906, exposed=banned, background_rows=8
    )
    drawn = ids_of(cut["fold_a"]) | ids_of(cut["fold_b"]) | ids_of(cut["exemplars"])
    assert not drawn & set(banned)
