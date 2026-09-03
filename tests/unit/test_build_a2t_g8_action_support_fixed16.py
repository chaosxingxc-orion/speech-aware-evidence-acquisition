"""Identity-only tests for the G8 action-support fixed16 roster."""

import importlib.util
import hashlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build_a2t_g8_action_support_fixed16.py"
SPEC = importlib.util.spec_from_file_location("build_a2t_g8", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
NAMESPACE = MODULE.NAMESPACE
build_roster = MODULE.build_roster
make_receipt = MODULE.make_receipt
manifest_identity_hash = MODULE.manifest_identity_hash
rank_digest = MODULE.rank_digest
main = MODULE.main


G7 = ROOT / "docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json"
G8 = ROOT / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
EXPERIMENT = (
    ROOT / "configs/experiment/a2t-g8-action-support-reachability-fixed16-v1.json"
)


def test_g8_selects_two_per_tier_from_exact_g7_support_remainder() -> None:
    source = json.loads(G7.read_text(encoding="utf-8"))
    roster = build_roster(G7)
    source_ids = {row["sample_id"] for row in source["support_remainder"]}
    selected_ids = {row["sample_id"] for row in roster["selected"]}
    remainder_ids = {row["sample_id"] for row in roster["support_remainder"]}

    assert len(source_ids) == 44
    assert len(selected_ids) == 16
    assert len(remainder_ids) == 28
    assert selected_ids | remainder_ids == source_ids
    assert selected_ids.isdisjoint(remainder_ids)
    assert all(value == 2 for value in roster["selected_tier_counts"].values())


def test_g8_is_disjoint_from_g7_and_namespace_hash_stable() -> None:
    source = json.loads(G7.read_text(encoding="utf-8"))
    first = build_roster(G7)
    second = build_roster(G7)
    selected_ids = {row["sample_id"] for row in first["selected"]}
    g7_ids = {row["sample_id"] for row in source["selected"]}

    assert NAMESPACE == "speech-aware-evidence-acquisition-g8-action-support-fixed16-v1"
    assert first == second
    assert selected_ids.isdisjoint(g7_ids)
    assert all(
        row["selection_rank_sha256"] == rank_digest(row["sample_id"])
        for row in first["selected"]
    )
    assert first["manifest_split_identity_hash"] == manifest_identity_hash(
        first["selected"]
    )


def test_g8_receipt_declares_identity_only_selection() -> None:
    receipt = make_receipt(ROOT)
    selection = receipt["selection"]

    assert selection["fields_read"] == ["key", "sample_id", "tier"]
    for forbidden_use in (
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
        assert selection[forbidden_use] is False
    assert receipt["source_surface"] == "exact 44-row G7 support_remainder"
    assert receipt["split_identity_hash"] == receipt["manifest_split_identity_hash"]


def test_checked_in_g8_receipt_is_reproducible() -> None:
    assert json.loads(G8.read_text(encoding="utf-8")) == make_receipt(ROOT)


def test_g8_experiment_freezes_reachability_not_policy_fitting() -> None:
    config = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    actions = {action["action_id"]: action for action in config["macro_actions"]}

    assert list(actions) == [
        "STOP_M0",
        "EXHAUSTIVE_G7",
        "SUPPORT_ONLY_RESOLVE",
        "DECOMPOSED_SELECT_BIND_RESOLVE",
    ]
    assert config["status"] == "IMPLEMENTED_CONTACT_REQUIRES_MATCHED_LEDGER_AND_EXECUTION_PLAN"
    assert config["population"]["receipt_sha256"] == hashlib.sha256(
        G8.read_bytes()
    ).hexdigest()
    assert config["population"]["split_identity_hash"] == json.loads(
        G8.read_text(encoding="utf-8")
    )["split_identity_hash"]
    assert config["protocol"]["shared_contacts_per_row"] == 29
    assert config["protocol"]["new_contacts_per_row"] == 34
    assert config["protocol"]["batch_slots"] == 2
    assert config["protocol"]["network_jitter_testing"] is False
    assert actions["STOP_M0"]["new_model_contacts_per_row"] == 0
    assert actions["SUPPORT_ONLY_RESOLVE"]["filter_is_model_free"] is True
    assert actions["DECOMPOSED_SELECT_BIND_RESOLVE"]["selection_contacts_per_row"] == 1
    assert actions["DECOMPOSED_SELECT_BIND_RESOLVE"]["binding_contacts_per_row"] == 1
    assert config["sealing_and_scoring"]["score_invocation_limit"].startswith(
        "Exactly one"
    )
    assert config["promotion_rule"]["oracle_exact_count_minimum"] == 15
    assert (
        config["promotion_rule"]["oracle_slot_micro_f1_strictly_greater_than"]
        == 0.9
    )
    assert config["promotion_rule"]["scale1000_closed"] is True
    assert "no policy fitting" in config["claim_scope"]


def test_g8_rejects_nonexact_source_size(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"support_remainder": []}', encoding="utf-8")

    with pytest.raises(RuntimeError, match="exact 44-row"):
        build_roster(invalid)


def test_g8_rejects_a_tier_with_fewer_than_two_identities(tmp_path: Path) -> None:
    document = json.loads(G7.read_text(encoding="utf-8"))
    rows = document["support_remainder"]
    tier1_rows = [row for row in rows if row["tier"] == "tier1_direct"]
    moved_ids = {row["sample_id"] for row in tier1_rows[1:]}
    moved_index = 0
    for index, row in enumerate(rows):
        if row["sample_id"] in moved_ids:
            rows[index] = {
                "sample_id": f"tier2_parametric:synthetic-identity-{moved_index}",
                "key": f"audio2tool:tier2_parametric:synthetic-identity-{moved_index}",
                "tier": "tier2_parametric",
            }
            moved_index += 1
    invalid = tmp_path / "invalid-tier.json"
    invalid.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RuntimeError, match="fewer than two"):
        build_roster(invalid)


def test_g8_cli_renders_stdout_and_writes_requested_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--root", str(ROOT), "--stdout"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == make_receipt(ROOT)

    output = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--root", str(ROOT), "--output", str(output)],
    )
    assert main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == make_receipt(ROOT)
