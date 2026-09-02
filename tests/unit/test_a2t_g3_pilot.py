from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_g3_pilot import (
    G3_PER_TIER,
    G3_SELECTION_NAMESPACE,
    G3_TIERS,
    PilotRosterError,
    build_pilot_roster,
    build_repo_pilot_roster,
)
from speech_aware_evidence_acquisition.reproduction.sampling import split_identity_hash

REPO_ROOT = Path(__file__).resolve().parents[2]


def _rank(sample_id: str) -> str:
    return hashlib.sha256(
        f"{G3_SELECTION_NAMESPACE}\0{sample_id}".encode("utf-8")
    ).hexdigest()


def _exposed_item(tier: str, item_id: int) -> dict[str, object]:
    sample_id = f"{tier}:{item_id:06d}"
    return {
        "audio_seconds": float(item_id),
        "audio_sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
        "id": item_id,
        "key": f"audio2tool:{sample_id}",
        "media_relpath": (
            f"datasets/audio2tool/public/{tier}_audios/"
            f"query_{item_id:05d}/turn.wav"
        ),
        "sample_id": sample_id,
        "tier": tier,
        # These fields are deliberately present but must not affect selection.
        "query": f"private transcript {item_id}",
        "expected_tool_call": f"private gold {item_id}",
        "score": item_id % 2,
    }


def _parent_item(tier: str, item_id: int) -> dict[str, object]:
    return {
        "id": item_id,
        "key": f"audio2tool:{tier}:{item_id:06d}",
        "query_idx": 1000 + item_id,
        "tier": tier,
    }


def _fixture() -> tuple[dict[str, object], dict[str, dict[str, object]]]:
    parent_items: list[dict[str, object]] = []
    exposed_items: list[dict[str, object]] = []
    for tier_index, tier in enumerate(G3_TIERS):
        start = tier_index * 100
        parent_items.extend(_parent_item(tier, start + offset) for offset in range(1, 13))
        exposed_items.extend(_exposed_item(tier, start + offset) for offset in range(1, 9))
    parent = {"items": parent_items, "split_identity_hash": "a" * 64}
    receipts = {
        "first.json": {"items": exposed_items[::2]},
        "second.json": {"items": exposed_items[1::2]},
        # A duplicate proves the input is interpreted as a union.
        "third.json": {"items": [exposed_items[0]]},
    }
    return parent, receipts


def test_pilot_roster_is_balanced_unique_deterministic_and_identity_only() -> None:
    parent, receipts = _fixture()

    receipt = build_pilot_roster(
        parent, receipts, expected_parent_per_tier=12, expected_exposed_per_tier=8
    )
    reordered = build_pilot_roster(
        {**parent, "items": list(reversed(parent["items"]))},
        dict(reversed(tuple(receipts.items()))),
        expected_parent_per_tier=12,
        expected_exposed_per_tier=8,
    )

    assert receipt == reordered
    assert receipt["count"] == len(receipt["items"]) == len(G3_TIERS) * G3_PER_TIER
    assert receipt["strata_counts"] == {tier: G3_PER_TIER for tier in G3_TIERS}
    assert len({item["sample_id"] for item in receipt["items"]}) == 40
    assert len({item["query_block"] for item in receipt["items"]}) == 40
    assert all(item["selection_rank_sha256"] == _rank(item["sample_id"]) for item in receipt["items"])
    assert all("query" not in item and "expected_tool_call" not in item and "score" not in item for item in receipt["items"])
    assert receipt["selection_proof"]["gold_used"] is False
    assert receipt["selection_proof"]["transcripts_used"] is False
    assert receipt["selection_proof"]["prior_outputs_used"] is False
    assert receipt["selection_proof"]["prior_scores_used"] is False
    assert receipt["run_identity_hash"] == split_identity_hash(
        f"audio2tool/{item['sample_id']}" for item in receipt["items"]
    )


def test_pilot_roster_proves_confirmation_reserve_disjointness() -> None:
    parent, receipts = _fixture()

    receipt = build_pilot_roster(
        parent, receipts, expected_parent_per_tier=12, expected_exposed_per_tier=8
    )
    reserve = receipt["confirmation_reserve"]
    selected_ids = {item["sample_id"] for item in receipt["items"]}
    reserve_ids = {item["sample_id"] for item in reserve["items"]}

    assert reserve["count"] == len(reserve_ids) == 32
    assert reserve["strata_counts"] == {tier: 4 for tier in G3_TIERS}
    assert selected_ids.isdisjoint(reserve_ids)
    assert reserve["pilot_overlap_count"] == 0
    assert len(reserve["split_identity_hash"]) == 64


def test_pilot_roster_refuses_parent_or_exposed_geometry_drift() -> None:
    parent, receipts = _fixture()
    receipts["first.json"]["items"] = receipts["first.json"]["items"][:-1]

    with pytest.raises(PilotRosterError, match="exposed union"):
        build_pilot_roster(
            parent, receipts, expected_parent_per_tier=12, expected_exposed_per_tier=8
        )

    parent, receipts = _fixture()
    parent["items"] = parent["items"][:-1]
    with pytest.raises(PilotRosterError, match="parent population"):
        build_pilot_roster(
            parent, receipts, expected_parent_per_tier=12, expected_exposed_per_tier=8
        )


def test_materialized_real_roster_is_exactly_reproducible_from_frozen_receipts() -> None:
    path = REPO_ROOT / "docs" / "receipts" / "a2t" / "A2T-G3-PILOT-40.json"
    materialized = json.loads(path.read_text(encoding="utf-8"))

    assert materialized == build_repo_pilot_roster(REPO_ROOT)
    assert materialized["count"] == 40
    assert materialized["selection_proof"]["exposed_union_count"] == 312
    assert materialized["confirmation_reserve"]["count"] == 88
    assert materialized["confirmation_reserve"]["pilot_overlap_count"] == 0
