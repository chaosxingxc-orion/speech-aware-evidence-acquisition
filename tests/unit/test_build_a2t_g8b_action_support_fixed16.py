"""Identity-only tests for the G8B action-support fixed16 roster."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build_a2t_g8b_action_support_fixed16.py"
SPEC = importlib.util.spec_from_file_location("build_a2t_g8b", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

G8 = ROOT / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
G8B = ROOT / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"


def test_g8b_selects_two_per_tier_from_exact_g8_support_remainder() -> None:
    source = json.loads(G8.read_text(encoding="utf-8"))
    roster = MODULE.build_roster(G8)
    source_ids = {row["sample_id"] for row in source["support_remainder"]}
    selected_ids = {row["sample_id"] for row in roster["selected"]}
    remainder_ids = {row["sample_id"] for row in roster["support_remainder"]}

    assert len(source_ids) == 28
    assert len(selected_ids) == 16
    assert len(remainder_ids) == 12
    assert selected_ids | remainder_ids == source_ids
    assert selected_ids.isdisjoint(remainder_ids)
    assert all(value == 2 for value in roster["selected_tier_counts"].values())


def test_g8b_namespace_and_identity_hash_are_stable_and_disjoint() -> None:
    source = json.loads(G8.read_text(encoding="utf-8"))
    first = MODULE.build_roster(G8)

    assert MODULE.NAMESPACE == "speech-aware-evidence-acquisition-g8b-action-support-fixed16-v1"
    assert first == MODULE.build_roster(G8)
    assert {row["sample_id"] for row in first["selected"]}.isdisjoint(
        {row["sample_id"] for row in source["selected"]}
    )
    assert all(
        row["selection_rank_sha256"] == MODULE.rank_digest(row["sample_id"])
        for row in first["selected"]
    )
    assert first["manifest_split_identity_hash"] == MODULE.manifest_identity_hash(
        first["selected"]
    )


def test_g8b_receipt_is_identity_only_and_reproducible() -> None:
    receipt = MODULE.make_receipt(ROOT)
    selection = receipt["selection"]

    assert receipt["split_name"] == "A2T-G8B-ACTION-SUPPORT-FIXED16"
    assert receipt["source_surface"] == "exact 28-row G8 support_remainder"
    assert selection["fields_read"] == ["key", "sample_id", "tier"]
    for prohibited_input in (
        "uses_task_text",
        "uses_audio",
        "uses_gold",
        "uses_outputs",
        "uses_scores",
        "uses_rewards",
        "uses_test",
        "uses_future_turns",
        "uses_model_or_tool",
        "uses_network_or_tokenizer_or_scorer",
    ):
        assert selection[prohibited_input] is False
    assert receipt["split_identity_hash"] == receipt["manifest_split_identity_hash"]
    assert json.loads(G8B.read_text(encoding="utf-8")) == receipt


def test_g8b_rejects_nonexact_source_or_missing_tier_capacity(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"support_remainder": []}', encoding="utf-8")
    with pytest.raises(RuntimeError, match="exact 28-row"):
        MODULE.build_roster(invalid)

    document = json.loads(G8.read_text(encoding="utf-8"))
    tier1_rows = [
        row for row in document["support_remainder"] if row["tier"] == "tier1_direct"
    ]
    removed_ids = {row["sample_id"] for row in tier1_rows[1:]}
    document["support_remainder"] = [
        row for row in document["support_remainder"] if row["sample_id"] not in removed_ids
    ]
    document["support_remainder"].extend(
        {
            "sample_id": f"tier2_parametric:synthetic-{index}",
            "key": f"audio2tool:tier2_parametric:synthetic-{index}",
            "tier": "tier2_parametric",
        }
        for index in range(2)
    )
    invalid.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(RuntimeError, match="fewer than two"):
        MODULE.build_roster(invalid)
