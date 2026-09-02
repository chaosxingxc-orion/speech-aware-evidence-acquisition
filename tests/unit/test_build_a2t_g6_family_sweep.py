import json
from pathlib import Path

from scripts.build_a2t_g6_family_sweep import (
    NAMESPACE,
    build_roster,
    canonical_identity_hash,
    manifest_identity_hash,
    rank_digest,
)


ROOT = Path(__file__).resolve().parents[2]
G1 = ROOT / "docs/receipts/a2t/A2T-G1-104.json"
G3 = ROOT / "docs/receipts/a2t/A2T-G3-PILOT-40.json"
G5 = ROOT / "docs/receipts/a2t/A2T-G5-FIXED16-IDENTITY.json"


def test_rank_is_sha256_namespace_nul_identity():
    import hashlib

    sample_id = "tier1_direct:000001"
    expected = hashlib.sha256((NAMESPACE + "\0" + sample_id).encode()).hexdigest()
    assert rank_digest(sample_id) == expected


def test_build_excludes_authorities_and_selects_two_per_tier():
    roster = build_roster(G1, G3, G5)
    assert len(roster["selected"]) == 16
    assert len(roster["remainder"]) == 60
    assert roster["eligible_count"] == 76
    assert all(count == 2 for count in roster["selected_tier_counts"].values())
    selected = {item["sample_id"] for item in roster["selected"]}
    remainder = {item["sample_id"] for item in roster["remainder"]}
    assert selected.isdisjoint(remainder)
    assert len(selected | remainder) == 76


def test_build_is_order_independent_and_hashable():
    first = build_roster(G1, G3, G5)
    second = build_roster(G1, G3, G5)
    assert first == second
    assert first["selection_identity_hash"] == canonical_identity_hash(first["selected"])
    assert first["manifest_split_identity_hash"] == manifest_identity_hash(first["selected"])


def test_generated_receipt_is_identity_only():
    receipt = json.loads((ROOT / "docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json").read_text())
    assert receipt["selection"]["uses_task_text"] is False
    assert receipt["selection"]["uses_audio"] is False
    assert receipt["selection"]["uses_gold"] is False
    assert receipt["selected_tier_counts"] == {tier: 2 for tier in receipt["tier_order"]}
    assert len(receipt["selected"]) == 16
    assert len(receipt["remainder"]) == 60
    assert receipt["split_identity_hash"] == receipt["manifest_split_identity_hash"]
