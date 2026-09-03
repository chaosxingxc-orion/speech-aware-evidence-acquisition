"""Contract checks for the prospective G8B action-support preregistration."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
RECEIPT = REPO / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"
EXPERIMENT = (
    REPO / "configs/experiment/a2t-g8b-action-support-reachability-fixed16-v1.json"
)
BASELINE = REPO / "configs/baseline/a2t-g8b-action-support-reachability-agentloop.json"


def test_g8b_preregistration_binds_the_new_identity_only_roster() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))

    assert experiment["experiment_id"] == "SAEA-A2T-G8B-ACTION-SUPPORT-REACHABILITY-FIXED16-V1"
    assert experiment["status"] == "PREREGISTERED_NO_CONTACT_AUTHORIZATION"
    assert experiment["population"]["receipt_sha256"] == hashlib.sha256(
        RECEIPT.read_bytes()
    ).hexdigest()
    assert experiment["population"]["split_identity_hash"] == receipt["split_identity_hash"]
    assert experiment["population"]["support_remainder_count"] == 12


def test_g8b_freezes_the_four_branches_and_empty_or_invalid_decomposition_behavior() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    actions = {action["action_id"]: action for action in experiment["macro_actions"]}
    protocol = experiment["protocol"]

    assert list(actions) == [
        "STOP_M0",
        "EXHAUSTIVE_G7",
        "SUPPORT_ONLY_RESOLVE",
        "DECOMPOSED_SELECT_BIND_RESOLVE",
    ]
    assert actions["STOP_M0"]["new_model_contacts_per_row"] == 0
    assert actions["DECOMPOSED_SELECT_BIND_RESOLVE"]["empty_selection_behavior"] == (
        "Log a model-free empty-bind passthrough, then send the empty sealed selection and "
        "empty sealed binding to final resolve without fallback, inference, repair, or reuse."
    )
    assert protocol["invalid_decomposed_output_behavior"] == (
        "Treat an invalid selection or invalid binding for a nonempty valid selection as the "
        "row-local raw frozen-core invalid output; make no later row contact, retry, repair, "
        "or substitution. Continue the cohort and score all 16 rows."
    )
    assert protocol["all_four_outputs_required_per_row"] is True
    assert protocol["cohort_continues_after_row_local_invalid_output"] is True


def test_g8b_budget_prompt_fit_and_scoring_boundaries_are_prospective() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert experiment["contact_budget"]["max_model_calls"] == 544
    assert experiment["contact_budget"]["actual_dynamic_model_calls_upper_bound"] == 544
    assert experiment["prompt_fit"]["measurement_rule"].startswith("Render and measure the actual")
    assert experiment["protocol"]["max_concurrent_model_requests"] == 2
    assert experiment["protocol"]["queue_depth"] == 4
    assert experiment["protocol"]["network_jitter_testing"] is False
    assert experiment["sealing_and_scoring"]["gold_open_rule"].startswith(
        "Keep gold"
    )
    assert "four complete 16-row branch manifests" in experiment["sealing_and_scoring"][
        "gold_open_rule"
    ]
    assert baseline["speech_native_contact_ceiling_per_task"] == 34
    assert baseline["max_concurrent_model_requests"] == 2
    assert baseline["queue_depth"] == 4
    assert baseline["network_jitter_testing"] is False
