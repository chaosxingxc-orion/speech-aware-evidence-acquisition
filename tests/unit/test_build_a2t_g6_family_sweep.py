import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_builder():
    """Load ``scripts/build_a2t_g6_family_sweep.py`` by PATH, not by dotted import: ``verl`` installs a
    top-level ``scripts`` package in the shared venv, so ``from scripts.<name> import ...`` resolves to
    site-packages and fails collection unless the repo root happens to precede it on ``sys.path``
    (the same fix as ``test_e28_a2t_knowledge_index_view.py``)."""

    path = ROOT / "scripts" / "build_a2t_g6_family_sweep.py"
    spec = importlib.util.spec_from_file_location("build_a2t_g6_family_sweep_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


_BUILDER = _load_builder()
NAMESPACE = _BUILDER.NAMESPACE
build_roster = _BUILDER.build_roster
canonical_identity_hash = _BUILDER.canonical_identity_hash
manifest_identity_hash = _BUILDER.manifest_identity_hash
rank_digest = _BUILDER.rank_digest


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
