"""Identity-only tests for the G7 construction-example fixed16 roster."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
SCRIPT = ROOT / "scripts/build_a2t_g7_example_fixed16.py"
SPEC = importlib.util.spec_from_file_location("build_a2t_g7", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
NAMESPACE = MODULE.NAMESPACE
build_roster = MODULE.build_roster
manifest_identity_hash = MODULE.manifest_identity_hash
rank_digest = MODULE.rank_digest


G6 = ROOT / "docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json"


def test_g7_selects_two_per_tier_only_from_exact_g6_remainder() -> None:
    roster = build_roster(G6)

    assert len(roster["selected"]) == 16
    assert len(roster["support_remainder"]) == 44
    assert all(value == 2 for value in roster["selected_tier_counts"].values())
    assert all(value >= 5 for value in roster["support_tier_counts"].values())
    assert {row["sample_id"] for row in roster["selected"]}.isdisjoint(
        {row["sample_id"] for row in roster["support_remainder"]}
    )


def test_g7_selection_is_namespace_hash_stable_and_manifest_bound() -> None:
    roster = build_roster(G6)

    assert NAMESPACE == "speech-aware-evidence-acquisition-g7-example-fixed16-v1"
    assert roster == build_roster(G6)
    assert all(
        row["selection_rank_sha256"] == rank_digest(row["sample_id"])
        for row in roster["selected"]
    )
    assert roster["manifest_split_identity_hash"] == manifest_identity_hash(
        roster["selected"]
    )
