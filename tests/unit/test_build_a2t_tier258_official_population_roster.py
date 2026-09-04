"""Model-free coverage for the tiers-2/5/8 official-population roster and its
config surface.

Every assertion reads only committed receipts and fragments: no data root,
no media bytes, no model, network, tokenizer or scorer contact.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_tier258_official_population_roster.py"
ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-tier258-official-population-roster"
    / "flight-roster-receipt.json"
)
PROBE_RECEIPT = (
    REPO / "docs/receipts/probe-samples/a2t-tier258-official-population-1500.json"
)
D1_SUPPLEMENT = (
    REPO / "docs/receipts/artifacts/d1-a2t-tier258-official-population-1500.json"
)
PARENT_D1 = REPO / "docs/receipts/artifacts/d1-identity.json"
DATASET = REPO / "configs/dataset/audio2tool-tier258-official-population-1500.json"
EXPERIMENT = REPO / "configs/experiment/a2t-tier258-official-population-v1.json"
SMOKE = REPO / "configs/experiment/a2t-tier258-official-population-smoke-v1.json"
PROBE_MANIFEST = REPO / "configs/probes/manifest.json"


def _module():
    spec = importlib.util.spec_from_file_location("a2t_tier258_pop_roster_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_roster_identity_and_shape() -> None:
    module = _module()
    roster = _load(ROSTER)
    assert roster["schema"] == "saea-a2t-agentloop-flight-roster-receipt-v1"
    assert roster["carrier"] == "audio2tool"
    assert roster["split_name"] == module.SPLIT_NAME
    assert roster["split_role"] == "discovery"
    assert roster["strata"] == "tier"
    assert roster["count"] == len(roster["items"]) == 3 * module.DRAW_COUNT_PER_TIER
    assert roster["tier_counts"] == {
        tier: module.DRAW_COUNT_PER_TIER for tier in module.TIERS
    }
    assert roster["contacts"] == {"audio": 0, "model": 0, "network": 0, "scorer": 0}
    assert roster["status"] == "PREPARED_NOT_CONTACT_AUTHORITY"
    assert roster["selection"]["seed"] == module.DRAW_SEED
    assert roster["selection"]["uses_gold_at_runtime"] is False
    assert roster["selection"]["uses_test"] is False

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
    seen: set[str] = set()
    total = 0.0
    for item in roster["items"]:
        assert set(item) == expected_keys
        assert item["tier"] in module.TIERS
        assert item["key"] == f"audio2tool:{item['sample_id']}"
        assert item["sample_id"] == f"{item['tier']}:{int(item['id']):06d}"
        assert len(item["audio_sha256"]) == 64
        assert item["media_relpath"].startswith("datasets/audio2tool/public/")
        assert item["media_relpath"].endswith(".wav")
        assert item["sample_id"] not in seen
        seen.add(item["sample_id"])
        total += float(item["audio_seconds"])
    assert [item["sample_id"] for item in roster["items"]] == sorted(seen)
    assert roster["audio_seconds_total"] == pytest.approx(total, abs=1e-6)


def test_roster_identity_hashes_recompute() -> None:
    module = _module()
    roster = _load(ROSTER)
    keys = [str(item["key"]) for item in roster["items"]]
    assert roster["split_identity_hash"] == module.sha256_lines(keys)

    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    recomputed = split_identity_hash(
        prefixed("audio2tool", [str(item["sample_id"]) for item in roster["items"]])
    )
    assert roster["flight_split_identity_hash"] == recomputed


def test_population_rule_audit_is_recorded_per_tier() -> None:
    module = _module()
    roster = _load(ROSTER)
    for tier in module.TIERS:
        block = roster["per_tier"][tier]
        assert block["count"] == module.DRAW_COUNT_PER_TIER
        assert block["population_size"] == module.POPULATION_COUNTS[tier]
        assert block["shipped_recordings_per_query"] == module.SHIPPED_SPEAKERS_PER_QUERY[tier]
        audit = block["official_rule_audit"]
        assert audit["performed"] is True
        assert audit["disagreements"] == 0
        assert audit["agreements"] == module.POPULATION_COUNTS[tier]
        assert audit["query_directories_whose_csv_resolves_no_shipped_wav"] == []
    # tier 5's own released loader cannot read the released bytes; that fact is
    # recorded rather than smoothed over.
    literal = roster["per_tier"]["tier5_needle"]["official_rule_audit"][
        "literal_loader_replay"
    ]
    assert literal["rows_resolved"] == 0
    assert "no query_dir/<basename> fallback" in literal["finding"]
    # tier 8 has no speaker choice to make.
    assert roster["per_tier"]["tier8_intent_blending"]["speaker_idx_counts"] == {
        "None": module.DRAW_COUNT_PER_TIER
    }
    assert "mixed.wav" in roster["per_tier"]["tier8_intent_blending"][
        "official_rule_audit"
    ]["how_the_file_order_rule_resolved"]


def test_probe_receipt_is_additive_and_verifies() -> None:
    module = _module()
    roster = _load(ROSTER)
    receipt = _load(PROBE_RECEIPT)
    assert receipt["probe"] == module.PROBE_RECEIPT_STEM
    assert receipt["carrier"] == "audio2tool"
    assert receipt["split_role"] == "discovery"
    assert receipt["n_items"] == len(receipt["items"])
    assert receipt["target_gold_opened_before_receipt"] is False
    assert receipt["source_roster_sha256"] == _sha256(ROSTER)
    assert receipt["source_roster_count"] == roster["count"]
    assert receipt["split_identity_hash"] == module.sha256_lines(
        str(item["key"]) for item in receipt["items"]
    )
    # data.audio2tool refuses a sample id carried by two receipts, so this one
    # must be exactly the roster's ids minus the ids already covered elsewhere.
    receipt_ids = {f"{item['tier']}:{int(item['id']):06d}" for item in receipt["items"]}
    roster_ids = {str(item["sample_id"]) for item in roster["items"]}
    assert receipt_ids <= roster_ids
    already = {
        sample
        for hits in receipt["already_covered_by_other_receipts"].values()
        for sample in hits
    }
    assert receipt_ids == roster_ids - already
    assert receipt["strata_counts"] == dict(
        sorted(Counter(str(item["tier"]) for item in receipt["items"]).items())
    )


def test_d1_supplement_is_additive_and_binds_the_roster() -> None:
    roster = _load(ROSTER)
    supplement = _load(D1_SUPPLEMENT)
    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "audio2tool"
    assert supplement["parent_d1_sha256"] == _sha256(PARENT_D1)
    assert supplement["source_binding_sha256"] == _sha256(ROSTER)
    assert supplement["count"] == len(supplement["manifest"])

    roster_by_id = {str(item["sample_id"]): item for item in roster["items"]}
    parent = _load(PARENT_D1)
    base_ids = {
        str(entry["id"])
        for entry in parent["carriers"]["audio2tool"]["layers"]["media"]["manifest"]
    }
    ids = [str(entry["id"]) for entry in supplement["manifest"]]
    assert ids == sorted(ids)
    assert set(ids) == set(roster_by_id) - base_ids
    assert supplement["ids_sha256"] == hashlib.sha256(
        "\n".join(ids).encode("utf-8")
    ).hexdigest()
    for entry in supplement["manifest"]:
        item = roster_by_id[str(entry["id"])]
        assert entry["sha256"] == item["audio_sha256"]
        assert entry["media_relpath"] == item["media_relpath"]
        assert entry["audio_seconds"] == pytest.approx(float(item["audio_seconds"]), abs=1e-6)
        assert entry["roles"] == ["query"]
    assert supplement["total_bytes"] == sum(
        int(entry["bytes"]) for entry in supplement["manifest"]
    )


def test_dataset_fragment_pins_the_receipts_it_names() -> None:
    roster = _load(ROSTER)
    fragment = _load(DATASET)
    assert fragment["carrier_lock_key"] == "audio2tool"
    assert fragment["split_id"] == roster["split_name"]
    assert "split_name" not in fragment
    assert fragment["a2t_calibration_count"] == roster["count"]
    assert fragment["a2t_calibration_split_role"] == "discovery"
    assert fragment["a2t_calibration_subset_receipt_sha256"] == _sha256(ROSTER)
    assert fragment["d1_media_supplement_sha256"] == _sha256(D1_SUPPLEMENT)
    assert fragment["a2t_calibration_split_identity_hash"] == roster["split_identity_hash"]
    assert (
        fragment["a2t_calibration_flight_split_identity_hash"]
        == roster["flight_split_identity_hash"]
    )
    assert fragment["a2t_calibration_audio_seconds_total"] == roster["audio_seconds_total"]
    assert (
        fragment["a2t_calibration_audio_seconds_longest_item"]
        == roster["audio_seconds_longest_item"]
    )


def test_experiment_fragment_declares_one_cell_and_a_covering_plan() -> None:
    roster = _load(ROSTER)
    experiment = _load(EXPERIMENT)
    assert experiment["experiment_id"] == "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1"
    assert experiment["execution_profile"] == "baseline-reproduction"
    cells = experiment["cells"]
    assert len(cells) == 1
    cell = cells[0]
    assert cell["cell_id"] == "T258-official-pop-1500"
    assert cell["arm"] == "bare-core"
    assert cell["baseline_fragment"] == "a2t-direct-official-protocol"
    assert cell["model_fragment"] == "q4km-featcache-a2t-official-04ccc72a"
    assert cell["dataset_fragment"] == "audio2tool-tier258-official-population-1500"

    plan = experiment["execution_plan"]
    assert plan["planned_model_calls"] == roster["count"] + 8
    assert plan["planned_speech_audio_seconds"] >= roster["audio_seconds_total"]
    assert plan["split_role"] == "discovery"
    paper = experiment["paper_row"]
    assert set(paper) - {"source"} == set(roster["per_tier"])
    assert experiment["decision"]["test_tuning"] is False
    assert experiment["decision"]["paper_scale"] is False


def test_smoke_fragment_covers_every_stratum_and_the_worst_request() -> None:
    roster = _load(ROSTER)
    smoke = _load(SMOKE)
    assert smoke["execution_profile"] == "bounded-discovery-probe"
    block = smoke["smoke_populations"]["T258-official-pop-1500"]
    ids = block["sample_ids"]
    assert len(ids) == block["count"] == 4
    by_id = {str(item["sample_id"]): item for item in roster["items"]}
    assert set(ids) <= set(by_id)
    assert {sample.split(":")[0] for sample in ids} == set(roster["per_tier"])
    assert block["parent_split_identity_hash"] == roster["flight_split_identity_hash"]

    from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash

    assert block["split_identity_hash"] == split_identity_hash(
        prefixed("audio2tool", sorted(ids))
    )
    seconds = sum(float(by_id[sample]["audio_seconds"]) for sample in ids)
    assert block["audio_seconds_one_pass"] == pytest.approx(seconds, abs=1e-6)
    # the longest row of the whole roster must be inside the smoke
    longest = max(roster["items"], key=lambda item: float(item["audio_seconds"]))
    assert str(longest["sample_id"]) in ids


def test_probe_manifest_registers_the_receipt() -> None:
    manifest = _load(PROBE_MANIFEST)
    receipt = _load(PROBE_RECEIPT)
    entry = manifest["samples"]["R1-audio2tool-official-tier258-population"]
    assert entry["receipt"] == "a2t-tier258-official-population-1500.json"
    assert entry["n_items"] == receipt["n_items"]
    assert entry["split_identity_hash"] == receipt["split_identity_hash"]
    assert entry["split_role"] == "discovery"
    probe = manifest["probes"]["R1-audio2tool-official-tier258-population"]
    assert probe["profile"] == "baseline-reproduction"
    assert probe["sample_receipt"] == "a2t-tier258-official-population-1500.json"
    assert probe["arms"]["direct"] == ["r1_audio2tool_official.txt"]
