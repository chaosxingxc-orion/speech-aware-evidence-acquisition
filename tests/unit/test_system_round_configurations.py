"""Prospective full-system actor cells remain held and share one model identity."""

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import (
    compose,
    effective_request_decoding_params,
)
from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignError,
    declared_readiness,
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.core.stage3_algorithms import (
    resolve_stage3_algorithm,
)

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "slurp-native-stage3-system-round1-r01c"
MODEL = "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1"


def read(relative):
    return json.loads((ROOT / relative).read_text())


def test_four_full_actor_cells_share_model_and_policy_but_distinct_seeds(tmp_path):
    hashes, seeds, runs, attempts = set(), set(), set(), set()
    for replica in range(1, 5):
        name = f"{PREFIX}-s{replica}-v1"
        (cell,) = load_campaign_cells(ROOT, name)
        d = cell.document
        assert d["model_fragment"] == MODEL
        c = compose(ROOT, MODEL, d["dataset_fragment"], d["baseline_fragment"], name)
        values = c.values
        assert "execution_plan" not in values
        assert "prepared_phase_supply" not in values
        assert values["policy"] == "phase-native-candidates-review-revise-v1"
        assert values["native_episode"]["max_revisions"] == 1
        assert values["native_episode"]["roles"]["solver"] == {
            "phase_id": "solver",
            "max_iterations": 1,
        }
        assert (
            values["population"]["count"] == len(values["populations"][0]["ids"]) == 625
        )
        assert declared_readiness(cell, tmp_path).state == "held"
        for mode in ["worker", "campaign", "prompt-fit", "wire-check"]:
            with pytest.raises(CampaignError, match="does not permit"):
                cell.assert_mode(mode)
        decoded = effective_request_decoding_params(values)
        assert decoded["temperature"] == 0.7
        assert decoded["max_tokens"] == 512
        assert decoded["top_p"] == 1 and decoded["top_k"] == 0 and decoded["min_p"] == 0
        hashes.add(c.config_hash)
        seeds.add(decoded["seed"])
        runs.add(d["run_id"])
        attempts.add(d["attempt_id"])
    assert len(hashes) == len(runs) == len(attempts) == 4
    assert seeds == set(range(2026092601, 2026092605))


def test_common_store_contents_and_graph_are_identical_across_cohorts():
    assets = read("configs/analysis/slurp-system-update-round-assets-v1.json")
    baselines = [
        read(f"configs/baseline/slurp-native-stage3-system-common-{suffix}-v1.json")
        for suffix in ["r01c", "fold-a", "fold-b"]
    ]
    for b, cohort in zip(baselines, assets["cohorts"], strict=True):
        assert b["native_episode"] == baselines[0]["native_episode"]
        assert b["phase_material"] == baselines[0]["phase_material"]
        assert (
            b["speech_packet_promotion_receipt_sha256"] == cohort["promotion"]["sha256"]
        )
        for store in baselines[0]["knowledge_stores"]:
            assert (
                b["knowledge_stores"][store]["snapshot"]
                == baselines[0]["knowledge_stores"][store]["snapshot"]
            )
            assert (
                b["knowledge_stores"][store]["release"]
                == baselines[0]["knowledge_stores"][store]["release"]
            )
        intent = b["knowledge_stores"]["intent-boundaries"]["phase_supply"][
            "perception"
        ]
        examples = b["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
        assert intent["query_source"]["sha256"] == cohort["segment_vectors"]["sha256"]
        assert examples["query_source"]["sha256"] == cohort["content_vectors"]["sha256"]
        assert examples["k"] == 20
        assert "prepared_phase_supply" not in b and "native_contact_fit" not in b


def test_memory_arms_are_unbound_templates_not_silent_default_cells():
    d = read(
        "docs/readiness/2026-09-26-slurp-system-round-configs/memory-arm-templates.json"
    )
    assert d["launch_authority"] is False
    assert {a["name"] for a in d["arms"]} == {"round2", "E", "M1", "M2"}
    for arm in d["arms"]:
        assert arm["status"] == "requires-sealed-memory-binding"
        assert "candidate_experience_memory" in arm["required_runtime_bindings"]
        assert arm["baseline_patch"]["phase_tools"]["reviewer"]["allowed_tools"] == [
            "saea-tool-corrective-memory-v1"
        ]
        assert not (
            ROOT / "configs/experiment" / f"{arm['prospective_experiment']}.json"
        ).exists()
    empty = next(a for a in d["arms"] if a["name"] == "E")
    m2 = next(a for a in d["arms"] if a["name"] == "M2")
    assert empty["baseline_patch"] == m2["baseline_patch"]
    assert empty["memory_source"] == m2["memory_source"] == "M2"
    assert empty["ordered_selection"] == []
    assert m2["ordered_selection"] == "all-records-in-frozen-snapshot-order"


def test_greedy_default_is_matched_and_held(tmp_path):
    name = "slurp-native-stage3-system-eval-default-fold-b-v1"
    (cell,) = load_campaign_cells(ROOT, name)
    d = cell.document
    c = compose(ROOT, MODEL, d["dataset_fragment"], d["baseline_fragment"], name)
    assert effective_request_decoding_params(c.values)["temperature"] == 0
    assert "request_decoding_overrides" not in c.values
    assert c.values["population"]["count"] == 1080
    assert declared_readiness(cell, tmp_path).state == "held"
    assert "candidate_experience_memory" not in c.values


def test_new_algorithm_record_does_not_reopen_historical_delta_route():
    record = resolve_stage3_algorithm("tfgrpo-system-memory-disjoint-v1")
    assert record.status == "planned"
    assert record.family == "training-free-grpo"
    assert "disjoint" in record.what_it_changes.lower()
    assert record.id != "tfgrpo-semantic-advantage-v1"
