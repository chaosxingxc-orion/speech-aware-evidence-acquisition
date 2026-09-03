"""Configuration contract for the fresh SELECT/FILL 104-row experiment."""

from pathlib import Path

from speech_aware_evidence_acquisition.core.config import compose


REPO = Path(__file__).resolve().parents[2]


def test_select_fill_config_freezes_fair_four_arm_experiment() -> None:
    composed = compose(
        REPO,
        "q4km-mmproj-free-speech-native-np2-a2t-select-fill-max1024",
        "audio2tool-semantic-agentloop-select-fill-104-v1",
        "a2t-semantic-agentloop-select-fill-top32",
        "a2t-semantic-agentloop-select-fill-104-v1",
    )
    values = composed.values

    assert values["experiment_id"] == "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-V1"
    assert values["execution_profile"] == "bounded-discovery-probe"
    assert values["speech_feature_root"] == (
        "/home/chao/feat-cache/"
        "a2t-semantic-agentloop-select-fill-v1-packets-04ccc72a"
    )
    assert values["profile_slot_count"] == 2
    assert values["generation_slots"] == 2
    assert values["generation_queue_depth"] == 4
    assert values["semantic_candidate_count"] == 32
    assert values["semantic_encoder_batch_size"] == 32
    assert values["model_prompt_batching"] is False
    assert values["agent_phases"] == [
        "OBS_SEMANTIC_STATE",
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    ]
    prompt = values["prompt_budget_policy"]
    assert prompt["physical_context_tokens_per_slot"] == 32768
    assert prompt["operational_maximum_required_window_tokens"] == 24576
    assert prompt["reserved_tokens"] == 8192
    assert prompt["whole_phase_preflight"] is True
    experiment = values["select_fill_experiment"]
    assert experiment["execution"]["generation_contacts"] == 624
    assert experiment["execution"]["embedding_logical_items"] == 104
    assert experiment["execution"]["embedding_physical_requests"] == 4
    assert experiment["evaluation"]["scored_complete_manifests"] == 4
    assert experiment["runtime_arms"]["joint_draft_revise"]["draft_reused"] is True
    assert experiment["decision"]["post_training_free_rl_target_over_0_90"] is True
    assert experiment["decision"]["baseline_over_0_90_required"] is False


def test_select_fill_config_never_enables_generation_batching_or_test_tuning() -> None:
    values = compose(
        REPO,
        "q4km-mmproj-free-speech-native-np2-a2t-select-fill-max1024",
        "audio2tool-semantic-agentloop-select-fill-104-v1",
        "a2t-semantic-agentloop-select-fill-top32",
        "a2t-semantic-agentloop-select-fill-104-v1",
    ).values

    experiment = values["select_fill_experiment"]
    assert experiment["execution"]["generation_request_batch_size"] == 1
    assert experiment["execution"]["retry_or_repair"] is False
    assert experiment["execution"]["network_jitter_study"] is False
    assert experiment["decision"]["test_tuning"] is False
    assert experiment["decision"]["training_free_rl_fit_in_this_flight"] is False
