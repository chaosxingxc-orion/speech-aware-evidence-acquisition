"""Model-free coverage for the A2T-CALIBRATION-400 flight roster builder.

Every assertion reads only committed receipts: no data root, no media
bytes, no model, network, tokenizer or scorer contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_calibration_400_roster.py"
PARENT = REPO / "docs/receipts/probe-samples/r1-audio2tool-sample.json"
ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json"
)


def _load_script_module():
    spec = importlib.util.spec_from_file_location("a2t_calibration_roster_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_parent_key_convention_reproduces_the_frozen_400_identity_hash() -> None:
    module = _load_script_module()
    parent = _load(PARENT)
    recomputed = module.sha256_lines(item["key"] for item in parent["items"])
    assert recomputed == module.PARENT_SPLIT_IDENTITY_HASH
    assert parent["split_identity_hash"] == module.PARENT_SPLIT_IDENTITY_HASH


def test_committed_roster_is_the_frozen_400_with_no_draw() -> None:
    module = _load_script_module()
    parent = _load(PARENT)
    roster = _load(ROSTER)
    assert roster["schema"] == "saea-a2t-agentloop-flight-roster-receipt-v1"
    assert roster["carrier"] == "audio2tool"
    assert roster["split_name"] == module.SPLIT_NAME
    assert roster["split_role"] == "discovery"
    assert roster["count"] == module.EXPECTED_COUNT == len(roster["items"])
    assert roster["selection"]["rule"] == "the frozen 400 split, no draw"
    assert roster["parent"]["receipt"] == module.PARENT_RECEIPT_RELPATH
    assert roster["parent"]["split_identity_hash"] == module.PARENT_SPLIT_IDENTITY_HASH
    parent_ids = {f"{i['tier']}:{int(i['id']):06d}" for i in parent["items"]}
    assert {item["sample_id"] for item in roster["items"]} == parent_ids


def test_committed_roster_identity_hashes_are_both_reproducible() -> None:
    module = _load_script_module()
    roster = _load(ROSTER)
    keys = [item["key"] for item in roster["items"]]
    assert module.sha256_lines(keys) == roster["split_identity_hash"]
    assert roster["split_identity_hash"] == module.PARENT_SPLIT_IDENTITY_HASH
    prefixed = [f"audio2tool/{item['sample_id']}" for item in roster["items"]]
    assert module.sha256_lines(prefixed) == roster["flight_split_identity_hash"]
    assert roster["split_identity_hash"] != roster["flight_split_identity_hash"]


def test_committed_roster_item_shape_and_aggregates() -> None:
    module = _load_script_module()
    roster = _load(ROSTER)
    expected_keys = {
        "audio_seconds",
        "audio_sha256",
        "id",
        "key",
        "media_relpath",
        "query_idx",
        "sample_id",
        "tier",
    }
    total = 0.0
    for item in roster["items"]:
        assert set(item) == expected_keys
        assert item["key"] == f"audio2tool:{item['sample_id']}"
        assert item["sample_id"] == f"{item['tier']}:{int(item['id']):06d}"
        assert len(item["audio_sha256"]) == 64
        assert item["audio_seconds"] > 0
        assert not item["media_relpath"].startswith("/")
        assert item["media_relpath"].startswith("datasets/audio2tool/")
        total += float(item["audio_seconds"])
    assert roster["audio_seconds_total"] == pytest.approx(total, abs=1e-6)
    assert roster["tier_counts"] == dict(
        sorted(Counter(item["tier"] for item in roster["items"]).items())
    )
    assert set(roster["tier_counts"].values()) == {module.EXPECTED_PER_TIER}
    assert roster["contacts"] == {"audio": 0, "model": 0, "network": 0, "scorer": 0}


def test_committed_roster_media_roster_hash_is_reproducible() -> None:
    module = _load_script_module()
    roster = _load(ROSTER)
    rows = [
        {
            "sample_id": item["sample_id"],
            "media_relpath": item["media_relpath"],
            "audio_sha256": item["audio_sha256"],
            "audio_seconds": item["audio_seconds"],
        }
        for item in sorted(roster["items"], key=lambda row: row["sample_id"])
    ]
    assert module.canonical_sha256(rows) == roster["media_roster_sha256"]


def test_config_fragments_pin_the_committed_roster_bytes() -> None:
    digest = hashlib.sha256(ROSTER.read_bytes()).hexdigest()
    dataset = _load(REPO / "configs/dataset/audio2tool-calibration-400.json")
    assert dataset["a2t_calibration_subset_receipt_sha256"] == digest
    assert dataset["a2t_calibration_count"] == 400
    assert "d1_media_supplement" not in dataset
    assert "d1_media_supplement_sha256" not in dataset
    experiment = _load(REPO / "configs/experiment/a2t-calibration-400-preprocess.json")
    scope = experiment["a2t_calibration_preprocess_scope"]
    assert scope["subset_receipt_sha256"] == digest
    flight = _load(REPO / "configs/experiment/a2t-direct-calibration-400-v1.json")
    assert flight["population"]["receipt_sha256"] == digest


def test_flight_experiment_cells_and_plan_are_consistent() -> None:
    flight = _load(REPO / "configs/experiment/a2t-direct-calibration-400-v1.json")
    cells = flight["cells"]
    assert len(cells) == 4
    assert {cell["arm"] for cell in cells} == {
        "bare-core",
        "bare-core-native-tools",
        "speech-feature-query",
        "speech-feature-query-native-tools",
    }
    for cell in cells:
        baseline = _load(REPO / f"configs/baseline/{cell['baseline_fragment']}.json")
        assert baseline["arm"] == cell["arm"]
        assert baseline["policy"] == "fixed"
        assert baseline["rails_arms"] == ["zero-supply"]
        assert baseline["scorers"] == ["a2t-toolcall", "a2t-toolcall-v2", "cost"]
        model = _load(REPO / f"configs/model/{cell['model_fragment']}.json")
        geometry = model["serving_geometry"]
        args = model["server_args"]
        assert int(args[args.index("-np") + 1]) == geometry["slots"]
        assert int(args[args.index("-c") + 1]) == geometry["slots"] * geometry["slot_tokens"]
    plan = flight["execution_plan"]
    assert set(plan) == {
        "execution_profile",
        "split_role",
        "planned_model_calls",
        "planned_gpu_hours",
        "planned_speech_audio_seconds",
    }
    assert plan["execution_profile"] == "baseline-reproduction"
    assert plan["split_role"] == "discovery"
    assert isinstance(plan["planned_model_calls"], int)
    assert isinstance(plan["planned_speech_audio_seconds"], int)
    assert plan["planned_speech_audio_seconds"] >= 4 * 2159.688


def test_smoke_plan_covers_every_cell_because_budget_is_run_cumulative() -> None:
    """core.model.adapter.FrozenCoreAdapter enforces planned_model_calls
    RUN-cumulatively: it re-reads every prior attempt's durable actuals for
    the run id on each request. All four smoke cells are attempts of ONE run
    id, so a per-cell plan is exhausted the moment the second cell asks for
    its first contact -- observed 2026-09-04 as "allows 4 calls (4 already
    spent by other attempts on this run)". A plan must cover prior spend
    plus its own worst case."""

    smoke = _load(REPO / "configs/experiment/a2t-direct-calibration-400-smoke-v1.json")
    plan = smoke["execution_plan"]
    cells = len(smoke["cells"])
    rows = len(smoke["smoke_population"]["sample_ids"])
    assert cells == 4 and rows == 4
    assert plan["planned_model_calls"] >= cells * rows
    assert plan["planned_speech_audio_seconds"] >= (
        smoke["smoke_population"]["audio_seconds_four_cells"]
    )


def test_flight_plan_also_covers_every_cell() -> None:
    flight = _load(REPO / "configs/experiment/a2t-direct-calibration-400-v1.json")
    plan = flight["execution_plan"]
    cells = len(flight["cells"])
    rows = flight["population"]["count"]
    assert plan["planned_model_calls"] >= cells * rows
    assert plan["planned_speech_audio_seconds"] >= (
        cells * flight["population"]["audio_seconds_one_pass"]
    )
