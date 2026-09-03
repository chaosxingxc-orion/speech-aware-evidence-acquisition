"""Contract checks for the prospective G8C fixed12 successor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
RECEIPT = REPO / "docs/receipts/a2t/A2T-G8C-ACTION-SUPPORT-FIXED12.json"
EXPERIMENT = (
    REPO / "configs/experiment/a2t-g8c-action-support-reachability-fixed12-v1.json"
)
BASELINE = REPO / "configs/baseline/a2t-g8c-action-support-reachability-agentloop.json"
G8B_EXPERIMENT = (
    REPO / "configs/experiment/a2t-g8b-action-support-reachability-fixed16-v1.json"
)


def test_g8c_preregistration_binds_the_exact_remaining_identity_surface() -> None:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))

    assert experiment["experiment_id"] == "SAEA-A2T-G8C-ACTION-SUPPORT-REACHABILITY-FIXED12-V1"
    assert experiment["status"] == "PREREGISTERED_NO_CONTACT_AUTHORIZATION"
    assert experiment["population"]["receipt_sha256"] == hashlib.sha256(
        RECEIPT.read_bytes()
    ).hexdigest()
    assert experiment["population"]["split_identity_hash"] == receipt["split_identity_hash"]
    assert experiment["population"]["count"] == 12
    assert experiment["population"]["support_remainder_count"] == 0


def test_g8c_preserves_g8b_actions_context_batch_and_one_shot_behavior() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    parent = json.loads(G8B_EXPERIMENT.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert experiment["macro_actions"] == parent["macro_actions"]
    for key in (
        "ordered_shared_contacts",
        "shared_contacts_per_row",
        "ordered_branch_contacts",
        "new_contacts_per_row_maximum",
        "temperature",
        "repair_contacts",
        "retries",
        "resends",
        "cumulative_raw_history",
        "max_concurrent_model_requests",
        "batch_slots",
        "queue_depth",
        "sample_affine_state",
        "network_jitter_testing",
        "empty_selection_binding_behavior",
    ):
        assert experiment["protocol"][key] == parent["protocol"][key]
    for key in (
        "maximum_selection_calls",
        "selection_response_utf8_bytes_maximum",
        "binding_response_utf8_bytes_maximum",
        "duplicates",
        "binding_alignment",
    ):
        assert experiment["protocol"]["decomposed_response_contract"][key] == parent[
            "protocol"
        ]["decomposed_response_contract"][key]
    assert experiment["prompt_fit"] == parent["prompt_fit"]
    assert baseline["per_slot_context_tokens"] == 32768
    assert baseline["prompt_plus_completion_cap_per_slot"] == 24576
    assert baseline["operational_headroom_token_minimum"] == 8192
    assert baseline["obs_batch_samples"] == 2
    assert baseline["max_concurrent_model_requests"] == 2
    assert baseline["queue_depth"] == 4
    assert baseline["network_jitter_testing"] is False


def test_g8c_dynamic_budget_scoring_and_promotion_gate_are_frozen() -> None:
    experiment = json.loads(EXPERIMENT.read_text(encoding="utf-8"))
    budget = experiment["contact_budget"]
    scoring = experiment["sealing_and_scoring"]
    promotion = experiment["promotion_rule"]

    assert budget["sample_count"] == 12
    assert budget["shared_model_calls"] == 348
    assert budget["branch_model_calls_maximum"] == 60
    assert budget["max_model_calls"] == 408
    assert budget["actual_dynamic_model_calls_minimum"] == 384
    assert budget["actual_dynamic_rule"] == (
        "396 + nonempty_valid_selections - invalid_selects - invalid_binds"
    )
    assert budget["repeated_speech_audio_seconds"] == 76.694
    assert budget["max_speech_audio_seconds"] == 2608
    assert "whole 12-row branch manifest" in scoring["manifest_rule"]
    assert scoring["outer_parallelism_workers"] == 4
    assert promotion["oracle_exact_count_minimum"] == 11
    assert promotion["oracle_exact_denominator"] == 12
    assert promotion["oracle_slot_micro_f1_strictly_greater_than"] == 0.9
    assert "approximately 100-row" in promotion["pass"]
    assert "Vowpal Wabbit" in promotion["pass"]
