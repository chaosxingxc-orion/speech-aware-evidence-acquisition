"""Fail-closed checks for the committed self-consistency result summary."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-01-a2t-self-consistency-104-v1/result-summary.json"
)


def _summary() -> dict[str, object]:
    return json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))


def test_result_summary_closes_scale_after_negative_arm_results() -> None:
    summary = _summary()
    arms = summary["arm_metrics"]
    assert summary["promotion_passed"] is False
    assert summary["selected_candidate"] is None
    assert "do not scale" in summary["decision"]
    assert arms["M0"]["exact_match_count"] == 29
    assert arms["REOBSERVE_DIRECT"]["exact_match_count"] == 23
    assert arms["SUPPLY_UNION_STRIPPED"]["exact_match_count"] == 23


def test_result_summary_preserves_signed_information_and_policy_outcome() -> None:
    summary = _summary()
    information = summary["information_gain"]
    policy = summary["training_free_policy"]
    assert information["observation_saves"] == 0
    assert information["observation_harms"] == 6
    assert information["eligible_supply_saves"] == 4
    assert information["eligible_supply_harms"] == 10
    assert sum(policy["actions"].values()) == 104
    assert policy["actions"] == {"STOP_M0": 104, "SUPPLY_UNION_STRIPPED": 0}
    assert policy["fold_net_gains"] == [0, 0, 0, 0, 0]
    assert policy["grouped_ci90"] == [0.0, 0.0]


def test_result_summary_records_whole_manifest_parallelism_and_contact_budget() -> None:
    summary = _summary()
    parallel = summary["parallel_scoring"]
    contacts = summary["contact_accounting"]
    incident = summary["finalization_incident"]
    assert parallel["whole_manifest_jobs"] == 2
    assert parallel["workers"] == 2
    assert parallel["dataset_shards"] == 0
    assert parallel["effective_speedup"] > 1.8
    assert parallel["wall_seconds"] < parallel["sum_job_seconds"]
    assert parallel["official_scorers_modified"] is False
    assert contacts["total_calls"] == (
        contacts["observation_calls"] + contacts["supply_calls"]
    )
    assert contacts["total_calls"] <= contacts["registered_ceiling"]
    assert contacts["audio_seconds"] <= contacts["registered_audio_seconds_ceiling"]
    assert incident["scientific_scores_complete"] is True
    assert incident["prediction_reflight"] is False
