"""Contract checks for the native structured-action fixed-eight screen."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
RECEIPT = REPO / "docs/receipts/a2t/A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json"
BUILD_RECEIPT = (
    REPO / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-structured-action-schema-build-v1/build-receipt.json"
)
EXPERIMENT = REPO / "configs/experiment/a2t-native-structured-action-fixed8-v1.json"
BASELINE = REPO / "configs/baseline/a2t-native-structured-action.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_preregistration_binds_frozen_roster_and_schema_build() -> None:
    receipt = _load(RECEIPT)
    build_receipt = _load(BUILD_RECEIPT)
    experiment = _load(EXPERIMENT)

    assert experiment["experiment_id"] == (
        "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
    )
    assert experiment["status"] == "PREREGISTERED_NO_CONTACT_AUTHORIZATION"
    assert (
        experiment["population"]["receipt_sha256"]
        == hashlib.sha256(RECEIPT.read_bytes()).hexdigest()
    )
    assert (
        experiment["population"]["split_identity_hash"]
        == receipt["split_identity_hash"]
    )
    assert experiment["population"]["count"] == 8
    schema = experiment["frozen_inputs"]["structured_action_schema"]
    assert (
        schema["build_receipt_sha256"]
        == hashlib.sha256(BUILD_RECEIPT.read_bytes()).hexdigest()
    )
    assert schema["artifact_sha256"] == build_receipt["schema_artifact"]["sha256"]
    assert schema["tool_count"] == 152
    assert schema["branch_count"] == 338
    assert schema["compatibility_rule_count"] == 43


def test_two_by_two_factor_and_contact_budget_are_frozen() -> None:
    experiment = _load(EXPERIMENT)
    baseline = _load(BASELINE)

    assert experiment["factorial"]["cell_order"] == [
        "REGISTRY_NO_SCHEMA",
        "REGISTRY_STRICT_ACTION",
        "HANDBOOK_NO_SCHEMA",
        "HANDBOOK_STRICT_ACTION",
    ]
    assert experiment["factorial"]["new_contact_cells"] == [
        "REGISTRY_STRICT_ACTION",
        "HANDBOOK_STRICT_ACTION",
    ]
    assert experiment["execution_protocol"]["new_cell_order"] == [
        "REGISTRY_STRICT_ACTION",
        "HANDBOOK_STRICT_ACTION",
    ]
    assert experiment["contact_budget"] == {
        "sample_count": 8,
        "new_model_calls": 16,
        "planned_model_calls": 16,
        "exact_speech_audio_seconds": 90.192,
        "planned_speech_audio_seconds": 91,
        "planned_gpu_hours": 0.2,
        "embedding_contacts": 0,
        "tokenizer_contacts": 0,
        "paid_api_spend": 0,
    }
    assert baseline["obs_batch_samples"] == 2
    assert baseline["max_concurrent_model_requests"] == 2
    assert baseline["queue_depth"] == 4
    assert baseline["temperature"] == 0
    assert baseline["seed"] == 20260803
    assert baseline["max_tokens"] == 1024
    assert baseline["repair_contacts"] == 0
    assert baseline["retries"] == 0
    assert baseline["resends"] == 0
    assert baseline["network_jitter_testing"] is False


def test_dynamic_context_scoring_and_reachability_gates_are_frozen() -> None:
    experiment = _load(EXPERIMENT)
    prompt_fit = experiment["prompt_fit"]
    scoring = experiment["postseal_scoring"]
    gates = experiment["mechanism_gates"]

    assert prompt_fit["per_slot_context_tokens"] == 32768
    assert prompt_fit["prompt_plus_completion_tokens_maximum"] == 24576
    assert prompt_fit["operational_headroom_tokens_minimum"] == 8192
    assert "immediately before every" in prompt_fit["measurement_rule"]
    assert scoring["whole_manifest_jobs"] == 4
    assert scoring["outer_workers"] == 4
    assert scoring["dataset_sharding"] is False
    assert scoring["shard_metric_averaging"] is False
    assert gates["oracle_exact_minimum"] == {"numerator": 8, "denominator": 8}
    assert gates["oracle_slot_micro_f1_minimum"] == 0.9
    assert gates["strict_cell_exact_minimum"] == {"numerator": 7, "denominator": 8}
    assert gates["strict_cell_tool_minimum"] == {"numerator": 8, "denominator": 8}
    assert gates["strict_cell_slot_micro_f1_minimum"] == 0.9
    assert experiment["downstream_training_free_control"]["implementation"] == (
        "vowpalwabbit==9.11.2 cb_explore_adf"
    )
    assert (
        experiment["downstream_training_free_control"]["local_learner_allowed"] is False
    )
