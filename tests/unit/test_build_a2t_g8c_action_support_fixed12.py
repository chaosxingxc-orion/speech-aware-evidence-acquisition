"""Identity-only tests for the G8C action-support fixed12 roster."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/build_a2t_g8c_action_support_fixed12.py"
SPEC = importlib.util.spec_from_file_location("build_a2t_g8c", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

G8 = ROOT / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
G8B = ROOT / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"
G8C = ROOT / "docs/receipts/a2t/A2T-G8C-ACTION-SUPPORT-FIXED12.json"


def test_g8c_inherits_every_g8b_support_identity_without_reranking() -> None:
    source = json.loads(G8B.read_text(encoding="utf-8"))
    roster = MODULE.build_roster(G8B)

    assert roster["selected"] == [
        {key: row[key] for key in ("sample_id", "key", "tier")}
        for row in source["support_remainder"]
    ]
    assert roster["support_remainder"] == []
    assert roster["source_count"] == roster["selected_count"] == 12
    assert roster["manifest_split_identity_hash"] == MODULE.manifest_identity_hash(
        roster["selected"]
    )


def test_g8c_is_disjoint_from_both_consumed_predecessor_rosters() -> None:
    g8 = json.loads(G8.read_text(encoding="utf-8"))
    g8b = json.loads(G8B.read_text(encoding="utf-8"))
    selected = {row["sample_id"] for row in MODULE.build_roster(G8B)["selected"]}

    assert selected.isdisjoint({row["sample_id"] for row in g8["selected"]})
    assert selected.isdisjoint({row["sample_id"] for row in g8b["selected"]})
    assert selected == {row["sample_id"] for row in g8b["support_remainder"]}


def test_g8c_receipt_is_identity_only_and_reproducible() -> None:
    receipt = MODULE.make_receipt(ROOT)
    selection = receipt["selection"]

    assert receipt["split_name"] == "A2T-G8C-ACTION-SUPPORT-FIXED12"
    assert receipt["source_surface"] == "exact 12-row G8B support_remainder"
    assert selection["algorithm"] == "Retain every source row in frozen source order."
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
    assert json.loads(G8C.read_text(encoding="utf-8")) == receipt


def test_g8c_rejects_any_source_semantic_drift(tmp_path: Path) -> None:
    source = json.loads(G8B.read_text(encoding="utf-8"))
    for mutation in ("missing", "duplicate", "selected-overlap"):
        document = json.loads(json.dumps(source))
        if mutation == "missing":
            document["support_remainder"].pop()
        elif mutation == "duplicate":
            document["support_remainder"][-1] = document["support_remainder"][0]
        else:
            document["support_remainder"][0] = document["selected"][0]
        invalid = tmp_path / f"{mutation}.json"
        invalid.write_text(json.dumps(document), encoding="utf-8")
        with pytest.raises(RuntimeError, match="exact G8B support semantics"):
            MODULE.build_roster(invalid)


@pytest.mark.parametrize(
    "support",
    [
        {},
        [None] * 12,
        [{"sample_id": "", "key": "key", "tier": "tier"}] * 12,
    ],
)
def test_g8c_rejects_malformed_identity_rows(tmp_path: Path, support: object) -> None:
    document = json.loads(G8B.read_text(encoding="utf-8"))
    document["support_remainder"] = support
    invalid = tmp_path / "malformed.json"
    invalid.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(RuntimeError, match="exact G8B support semantics"):
        MODULE.build_roster(invalid)


def test_g8c_builder_cli_renders_stdout_and_writes_an_explicit_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--root", str(ROOT), "--stdout"],
    )
    assert MODULE.main() == 0
    assert json.loads(capsys.readouterr().out)["split_name"] == (
        "A2T-G8C-ACTION-SUPPORT-FIXED12"
    )

    output = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [str(SCRIPT), "--root", str(ROOT), "--output", str(output)],
    )
    assert MODULE.main() == 0
    assert json.loads(output.read_text(encoding="utf-8")) == MODULE.make_receipt(ROOT)
