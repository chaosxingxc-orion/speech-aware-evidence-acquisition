"""Model-free coverage for the tiers-3/4/6/7 official-population roster and its
config surface.

Every assertion reads only committed receipts and fragments: no data root,
no media bytes, no model, network, tokenizer or scorer contact. The builder
is the tiers-2/5/8 one with a second tier group, so this file also pins the
facts that group exists for -- tier 4's variable shipped-recording counts
and tier 7's first-user-turn rule with its two identity exclusions.
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
    / "2026-09-04-a2t-tier3467-official-population-roster"
    / "flight-roster-receipt.json"
)
PROBE_RECEIPT = (
    REPO / "docs/receipts/probe-samples/a2t-tier3467-official-population-2000.json"
)
D1_SUPPLEMENT = (
    REPO / "docs/receipts/artifacts/d1-a2t-tier3467-official-population-2000.json"
)
PARENT_D1 = REPO / "docs/receipts/artifacts/d1-identity.json"
DATASET = REPO / "configs/dataset/audio2tool-tier3467-official-population-2000.json"
EXPERIMENT = REPO / "configs/experiment/a2t-tier3467-official-population-v1.json"
SMOKE = REPO / "configs/experiment/a2t-tier3467-official-population-smoke-v1.json"
PROBE_MANIFEST = REPO / "configs/probes/manifest.json"


def _module():
    spec = importlib.util.spec_from_file_location("a2t_tier3467_pop_roster_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_group_registry_keeps_the_two_flights_apart() -> None:
    module = _module()
    assert set(module.GROUPS) == {"tier258", "tier3467"}
    # The tiers-2/5/8 group is still the module-level default, so the committed
    # tier-2/5/8 receipt stays reproducible from this builder unchanged.
    assert module.GROUPS["tier258"]["tiers"] == module.TIERS
    assert module.GROUPS["tier258"]["split_name"] == module.SPLIT_NAME
    group = module.GROUPS["tier3467"]
    assert group["tiers"] == module.TIERS_T3467 == (
        "tier3_multi_intent",
        "tier4_implicit",
        "tier6_correction",
        "tier7_multiturn",
    )
    assert group["split_name"] == module.SPLIT_NAME_T3467
    assert group["probe_receipt_stem"] == module.PROBE_RECEIPT_STEM_T3467
    assert set(module.TIERS).isdisjoint(module.TIERS_T3467)


def test_roster_identity_and_shape() -> None:
    module = _module()
    roster = _load(ROSTER)
    assert roster["schema"] == "saea-a2t-agentloop-flight-roster-receipt-v1"
    assert roster["carrier"] == "audio2tool"
    assert roster["split_name"] == module.SPLIT_NAME_T3467
    assert roster["split_role"] == "discovery"
    assert roster["strata"] == "tier"
    assert roster["count"] == len(roster["items"]) == 4 * module.DRAW_COUNT_PER_TIER
    assert roster["tier_counts"] == {
        tier: module.DRAW_COUNT_PER_TIER for tier in module.TIERS_T3467
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
        assert item["tier"] in module.TIERS_T3467
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
    for tier in module.TIERS_T3467:
        block = roster["per_tier"][tier]
        assert block["count"] == module.DRAW_COUNT_PER_TIER
        assert block["shipped_recordings_per_query"] == (
            module.SHIPPED_SPEAKERS_PER_QUERY_T3467[tier]
        )
        assert block["official_loader"] == module.OFFICIAL_LOADERS_T3467[tier]
        audit = block["official_rule_audit"]
        assert audit["performed"] is True
        assert audit["disagreements"] == 0
        assert audit["query_directories_whose_csv_resolves_no_shipped_wav"] == []
        assert audit["agreements"] == audit["query_directories"]
    # tiers 3, 4 and 6 keep the released population whole; only tier 7 is
    # narrowed, and only by this repository's own identity closure.
    for tier in ("tier3_multi_intent", "tier4_implicit", "tier6_correction"):
        block = roster["per_tier"][tier]
        assert block["population_size"] == module.POPULATION_COUNTS_T3467[tier]
        assert "excluded_from_the_population" not in block


def test_tier4_variable_shipping_and_duplicate_manifest_rows_are_recorded() -> None:
    roster = _load(ROSTER)
    audit = roster["per_tier"]["tier4_implicit"]["official_rule_audit"]
    counts = audit["shipped_recordings_per_query_counts"]
    assert counts == {"2": 2125, "4": 7}
    assert sum(counts.values()) == 2132
    duplicates = audit["duplicated_manifest_rows"]
    assert {entry["query_dir"] for entry in duplicates} == {
        "query_00232",
        "query_00763",
    }
    for entry in duplicates:
        assert len(entry["ids"]) == 2
        assert entry["ids"][0] < entry["ids"][1]
    # the anomaly never changes the pick: the replay still agrees everywhere
    assert audit["agreements"] == 2132


def test_tier7_is_bound_to_the_first_user_turn() -> None:
    module = _module()
    roster = _load(ROSTER)
    block = roster["per_tier"]["tier7_multiturn"]
    audit = block["official_rule_audit"]
    assert audit["query_directories"] == module.POPULATION_COUNTS_T3467["tier7_multiturn"]
    assert audit["first_user_turn_index_counts"] == {"00": 2146}
    # every released tier-7 query has at least two user turns, so the released
    # evaluator never hears the turn the gold call resolves from
    assert audit["queries_where_the_first_user_turn_is_the_only_user_turn"] == 0
    assert audit["queries_with_later_user_turns"] == 2146
    assert audit["user_turns_per_query_counts"] == {"2": 1449, "3": 691, "4": 6}
    assert "turn_*_user_*.wav" in audit["method"]
    assert block["first_user_turn_index_counts"] == {"00": module.DRAW_COUNT_PER_TIER}
    assert block["speaker_idx_counts"] == {"None": module.DRAW_COUNT_PER_TIER}
    for item in roster["items"]:
        if item["tier"] == "tier7_multiturn":
            assert "/turn_00_user_" in item["media_relpath"]


def test_tier7_exclusions_are_named_and_applied() -> None:
    roster = _load(ROSTER)
    parent = _load(PARENT_D1)
    block = roster["per_tier"]["tier7_multiturn"]
    excluded = block["excluded_from_the_population"]
    base_ids = {
        int(str(entry["id"]).split(":")[1])
        for entry in parent["carriers"]["audio2tool"]["layers"]["media"]["manifest"]
        if str(entry["id"]).startswith("tier7_multiturn:")
    }
    assert set(excluded["already_bound_in_base_d1_to_the_final_user_turn"]) == base_ids
    assert excluded["chat_history_ends_on_an_agent_turn"] == [373, 1258, 1744, 2023]
    assert set(excluded["excluded_ids"]) == base_ids | {373, 1258, 1744, 2023}
    assert excluded["population_before_exclusions"] == 2146
    assert excluded["population_after_exclusions"] == block["population_size"] == 2092
    drawn = {
        int(item["id"]) for item in roster["items"] if item["tier"] == "tier7_multiturn"
    }
    assert drawn.isdisjoint(excluded["excluded_ids"])


def test_probe_receipt_is_additive_and_verifies() -> None:
    module = _module()
    roster = _load(ROSTER)
    receipt = _load(PROBE_RECEIPT)
    assert receipt["probe"] == module.PROBE_RECEIPT_STEM_T3467
    assert receipt["carrier"] == "audio2tool"
    assert receipt["split_role"] == "discovery"
    assert receipt["n_items"] == len(receipt["items"])
    assert receipt["target_gold_opened_before_receipt"] is False
    assert receipt["source_roster_sha256"] == _sha256(ROSTER)
    assert receipt["source_roster_count"] == roster["count"]
    assert receipt["split_identity_hash"] == module.sha256_lines(
        str(item["key"]) for item in receipt["items"]
    )
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
    # tier 7 is excluded from the base-D1 overlap by construction
    assert all(sample.startswith("tier7_multiturn:") for sample in ids if sample.startswith("tier7_multiturn:"))
    assert len([sample for sample in ids if sample.startswith("tier7_multiturn:")]) == 500
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
    assert experiment["experiment_id"] == "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1"
    assert experiment["execution_profile"] == "baseline-reproduction"
    cells = experiment["cells"]
    assert len(cells) == 1
    cell = cells[0]
    assert cell["cell_id"] == "T3467-official-pop-2000"
    assert cell["arm"] == "bare-core"
    assert cell["baseline_fragment"] == "a2t-direct-official-protocol"
    # three 654-second release-defect rows force the tier-1 cell's geometry
    assert cell["model_fragment"] == "q4km-featcache-a2t-official-np2-04ccc72a"
    assert cell["dataset_fragment"] == "audio2tool-tier3467-official-population-2000"

    plan = experiment["execution_plan"]
    assert plan["planned_model_calls"] == roster["count"] + 8
    assert plan["planned_speech_audio_seconds"] >= roster["audio_seconds_total"]
    assert plan["split_role"] == "discovery"
    paper = experiment["paper_row"]
    assert set(paper) - {"source"} == set(roster["per_tier"])
    floors = experiment["published_floors"]
    for key in ("qwen2_5_omni_7b", "weakest_published_speechlm"):
        assert set(floors[key]) - {"note"} == set(roster["per_tier"])
    assert experiment["decision"]["test_tuning"] is False
    assert experiment["decision"]["paper_scale"] is False


def test_the_np2_geometry_is_the_one_the_roster_forces() -> None:
    import math

    roster = _load(ROSTER)
    model = _load(REPO / "configs/model/q4km-featcache-a2t-official-np2-04ccc72a.json")
    geometry = model["serving_geometry"]
    assert geometry["slots"] == 2
    assert geometry["slot_tokens"] == 24576
    worst = 3581 + 13 * math.ceil(float(roster["audio_seconds_longest_item"])) + 256 + 2
    assert geometry["slot_tokens"] - worst >= 8192
    # -np 3 over the same 49,152 context would not clear the reserve
    assert (49152 // 3) - worst < 8192


def test_smoke_fragment_covers_every_stratum_and_the_worst_request() -> None:
    roster = _load(ROSTER)
    smoke = _load(SMOKE)
    assert smoke["execution_profile"] == "bounded-discovery-probe"
    block = smoke["smoke_populations"]["T3467-official-pop-2000"]
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
    longest = max(roster["items"], key=lambda item: float(item["audio_seconds"]))
    assert str(longest["sample_id"]) in ids
    # all three 654-second rows must be proved before the flight
    assert (
        len([sample for sample in ids if float(by_id[sample]["audio_seconds"]) > 600]) == 3
    )


def test_probe_manifest_registers_the_receipt() -> None:
    manifest = _load(PROBE_MANIFEST)
    receipt = _load(PROBE_RECEIPT)
    entry = manifest["samples"]["R1-audio2tool-official-tier3467-population"]
    assert entry["receipt"] == "a2t-tier3467-official-population-2000.json"
    assert entry["n_items"] == receipt["n_items"]
    assert entry["split_identity_hash"] == receipt["split_identity_hash"]
    assert entry["split_role"] == "discovery"
    probe = manifest["probes"]["R1-audio2tool-official-tier3467-population"]
    assert probe["profile"] == "baseline-reproduction"
    assert probe["sample_receipt"] == "a2t-tier3467-official-population-2000.json"
    assert probe["arms"]["direct"] == ["r1_audio2tool_official.txt"]
