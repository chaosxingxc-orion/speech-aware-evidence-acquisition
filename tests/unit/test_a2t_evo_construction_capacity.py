"""Unit tests for the EVO-A1 construction-capacity arithmetic.

Synthetic pool only: no carrier bytes, no lock, no receipts, no network.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (
    BUCKETS,
    EXEMPLAR_RESERVE,
    capacity_verdict,
    realized_quota,
    rule_quota,
    split_blocks,
    target_capacity,
    tool_capacity,
)


@dataclass(frozen=True)
class Row:
    tool_name: str
    tier: str
    query_idx: int


def pool(spec: dict[str, list[tuple[int, int]]]) -> list[Row]:
    """``{tool: [(block, units_in_block), ...]}`` rendered as rows, one tier
    per unit index so the tier histogram is exercised too."""

    return [
        Row(tool, f"tier{(index % 8) + 1}", block)
        for tool, blocks in spec.items()
        for block, count in blocks
        for index in range(count)
    ]


def test_rule_quota_is_the_preregistered_formula() -> None:
    assert rule_quota(0) == 0
    assert rule_quota(8) == 0
    assert rule_quota(9) == 0  # floor((9 - 8) / 2)
    assert rule_quota(20) == 6
    assert rule_quota(48) == 20  # capped
    assert rule_quota(1000) == 20
    with pytest.raises(ValueError):
        rule_quota(-1)


def test_split_blocks_partitions_every_block_exactly_once() -> None:
    units_by_block = {block: 3 for block in range(12)}
    buckets, have = split_blocks(units_by_block, quota=9, key="seed:tool")
    assigned = [block for name in BUCKETS for block in buckets[name]]
    assert sorted(assigned) == sorted(units_by_block)
    assert len(assigned) == len(set(assigned))
    assert have["fold_a"] >= 9 and have["fold_b"] >= 9
    assert have["exemplars"] >= EXEMPLAR_RESERVE
    assert sum(have.values()) == sum(units_by_block.values())


def test_split_blocks_is_deterministic_for_one_key() -> None:
    units_by_block = {block: (block % 4) + 1 for block in range(20)}
    first = split_blocks(units_by_block, quota=7, key="20260906:setLighting")
    second = split_blocks(units_by_block, quota=7, key="20260906:setLighting")
    other = split_blocks(units_by_block, quota=7, key="20260906:setColor")
    assert first == second
    assert first != other


def test_realized_quota_lowers_an_infeasible_unit_quota() -> None:
    # 30 units in ten blocks of three: the unit rule says 11 per fold, but a
    # whole-block split can only reach 9 / 9 / 8 -- three blocks each for the
    # folds and the rest to the exemplar reserve.
    units_by_block = {block: 3 for block in range(10)}
    assert rule_quota(30) == 11
    quota, buckets, have = realized_quota(units_by_block, key="k")
    assert quota == 9
    assert have["fold_a"] >= quota and have["fold_b"] >= quota
    assert have["exemplars"] >= EXEMPLAR_RESERVE
    assert sorted(block for name in BUCKETS for block in buckets[name]) == sorted(units_by_block)


def test_realized_quota_is_zero_when_a_tool_is_too_small() -> None:
    quota, _buckets, have = realized_quota({1: 1, 2: 1, 3: 1}, key="k")
    assert quota == 0
    assert have["fold_a"] == 0 and have["fold_b"] == 0 and have["exemplars"] == 3


def test_tool_capacity_counts_units_blocks_tiers_and_drops_small_tools() -> None:
    rows = pool(
        {
            "big": [(1, 10), (2, 10), (3, 10), (4, 10), (5, 10)],
            "small": [(6, 4), (7, 3)],
            "absent": [],
        }
    )
    capacity = tool_capacity(rows, ["big", "small", "absent"], seed=20260906)
    assert capacity["big"]["units"] == 50
    assert capacity["big"]["blocks"] == 5
    assert sum(capacity["big"]["units_by_tier"].values()) == 50
    assert capacity["big"]["survives"] is True
    assert capacity["big"]["fold_quota"] == capacity["big"]["realized_quota"]
    assert capacity["small"]["units"] == 7
    assert capacity["small"]["survives"] is False
    assert capacity["small"]["fold_quota"] == 0
    assert capacity["absent"]["units"] == 0 and capacity["absent"]["survives"] is False
    # The three slices never share a block, for any tool.
    for row in capacity.values():
        blocks = [block for name in BUCKETS for block in row["blocks_by_bucket"][name]]
        assert len(blocks) == len(set(blocks))


def _targets() -> list[dict[str, object]]:
    return [
        {
            "target_id": "kept",
            "tools": ["big", "other"],
            "pairs": ["big|other"],
            "strict_mass": 30,
            "component_mass": 30,
        },
        {
            "target_id": "lost",
            "tools": ["big", "small", "other"],
            "pairs": ["big|small", "big|other"],
            "strict_mass": 40,
            "component_mass": 40,
        },
    ]


def test_target_capacity_kills_a_target_whose_dominant_pair_loses_a_side() -> None:
    rows = pool(
        {
            "big": [(index, 10) for index in range(1, 6)],
            "other": [(index, 10) for index in range(6, 11)],
            "small": [(11, 3)],
        }
    )
    capacity = tool_capacity(rows, ["big", "other", "small"], seed=20260906)
    per_target = target_capacity(_targets(), capacity, {"big|other": 30, "big|small": 40})
    kept, lost = per_target
    assert kept["survives"] is True
    assert kept["dominant_pair"] == "big|other" and kept["dominant_pair_intact"] is True
    assert lost["survives"] is False
    assert lost["dominant_pair"] == "big|small"
    assert lost["dropped_tools"] == ["small"]
    # The target still holds one intact pair, which is what the relaxed
    # reading keeps and the strict reading throws away.
    assert lost["intact_pair_mass"] == 30


def test_capacity_verdict_prices_both_readings() -> None:
    rows = pool(
        {
            "big": [(index, 10) for index in range(1, 6)],
            "other": [(index, 10) for index in range(6, 11)],
            "small": [(11, 3)],
        }
    )
    capacity = tool_capacity(rows, ["big", "other", "small"], seed=20260906)
    per_target = target_capacity(_targets(), capacity, {"big|other": 30, "big|small": 40})
    verdict = capacity_verdict(per_target, capacity, target_strict_mass_total=70)
    assert verdict["strict"]["targets"] == ["kept"]
    assert verdict["relaxed"]["targets"] == ["kept", "lost"]
    assert verdict["strict"]["addressable_strict_mass"] == 30
    assert verdict["relaxed"]["addressable_strict_mass"] == 60
    assert verdict["dropped_targets"] == ["lost"]
    assert verdict["dropped_tools"] == ["small"]
    assert set(verdict["fold_quotas"]) == {"big", "other"}


def test_a_multi_tool_pair_side_needs_every_tool_alive() -> None:
    rows = pool({"a": [(1, 30)], "b": [(2, 30)], "tiny": [(3, 2)]})
    capacity = tool_capacity(rows, ["a", "b", "tiny"], seed=1)
    targets = [
        {
            "target_id": "cluster",
            "tools": ["a", "b", "tiny"],
            "pairs": ["a+tiny|b"],
            "strict_mass": 9,
            "component_mass": 9,
        }
    ]
    per_target = target_capacity(targets, capacity, {"a+tiny|b": 9})
    assert per_target[0]["dominant_pair_intact"] is False
    assert per_target[0]["survives"] is False
