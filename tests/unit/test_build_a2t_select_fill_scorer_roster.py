"""Identity-only scorer roster construction for the SELECT/FILL flight."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_select_fill_scorer_roster.py"
ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-select-fill-fresh-roster-v1"
    / "flight-roster-receipt.json"
)
D1 = (
    REPO
    / "docs/receipts/artifacts"
    / "d1-a2t-semantic-agentloop-select-fill-104.json"
)


def _module():
    spec = importlib.util.spec_from_file_location("select_fill_scorer_roster", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_roster_build_is_identity_only_exact_and_deterministic() -> None:
    module = _module()

    first = module.build_receipt(ROSTER, D1)
    second = module.build_receipt(ROSTER, D1)

    assert first == second
    assert first["n_items"] == 104
    assert first["split_role"] == "discovery"
    assert first["source_roster_sha256"] == hashlib.sha256(
        ROSTER.read_bytes()
    ).hexdigest()
    assert first["d1_media_identity_receipt_sha256"] == hashlib.sha256(
        D1.read_bytes()
    ).hexdigest()
    assert first["run_identity_hash"] == (
        "122da6752c7c4011c2f632cee4e737899bfbb451501666fb47aa0676f372d2c8"
    )
    assert first["strata_counts"] == {
        "tier1_direct": 13,
        "tier2_parametric": 13,
        "tier3_multi_intent": 13,
        "tier4_implicit": 13,
        "tier5_needle": 13,
        "tier6_correction": 13,
        "tier7_multiturn": 13,
        "tier8_intent_blending": 13,
    }
    assert set(first["items"][0]) == {"id", "key", "query_idx", "tier"}
    assert all("gold" not in item for item in first["items"])
    assert all("transcript" not in item for item in first["items"])


def test_builder_rejects_d1_or_roster_identity_drift(tmp_path: Path) -> None:
    module = _module()
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    roster["items"][0]["key"] = "audio2tool:tier1_direct:999999"
    bad_roster = tmp_path / "roster.json"
    bad_roster.write_text(json.dumps(roster), encoding="utf-8")

    with pytest.raises(ValueError):
        module.build_receipt(bad_roster, D1)

    supplement = json.loads(D1.read_text(encoding="utf-8"))
    supplement["manifest"][0]["id"] = "tier1_direct:999999"
    bad_d1 = tmp_path / "d1.json"
    bad_d1.write_text(json.dumps(supplement), encoding="utf-8")

    with pytest.raises(ValueError):
        module.build_receipt(ROSTER, bad_d1)
