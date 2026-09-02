"""Model-free repricing of the executable-ground prompt for fresh packets."""

from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_ground_prompt_fit_inheritance import (
    PromptFitInheritanceError,
    reprice_prompt_fit,
)


def _source() -> tuple[dict[str, object], dict[str, object]]:
    prompt_fit = {
        "bounds": {
            "completion_token_allowance": 1024,
            "context_tokens": 65536,
            "context_tokens_per_slot": 32768,
            "slot_count": 2,
            "envelopes": [
                {
                    "envelope_id": "ground-direct",
                    "text_prompt_tokens": 12557,
                    "speech_feature_token_reserve": 455,
                    "special_token_reserve": 2,
                    "observation_token_allowance": 0,
                    "prompt_tokens_with_all_reserves": 13014,
                },
                {
                    "envelope_id": "ground-agent-observed",
                    "text_prompt_tokens": 12572,
                    "speech_feature_token_reserve": 455,
                    "special_token_reserve": 2,
                    "observation_token_allowance": 1024,
                    "prompt_tokens_with_all_reserves": 14053,
                },
            ],
        },
        "message_sha256": {"ground-direct": "a", "ground-agent-observed": "b"},
        "runtime_verification": {"llama_cpp_build_commit": "frozen"},
        "handbook": {"characters": 54881},
    }
    preprocessing = {
        "count": 104,
        "packets_promoted": 104,
        "promotion_receipt_sha256": "b" * 64,
        "speech_feature_tokens": {
            "distribution": {"count": 104, "max": 468},
            "packets": [
                {"packet_id": f"tier/sample-{index:03d}", "n_tokens": 468 if index == 0 else 1}
                for index in range(104)
            ],
        },
    }
    return prompt_fit, preprocessing


def test_reprice_prompt_fit_changes_only_the_measured_speech_reserve() -> None:
    prompt_fit, preprocessing = _source()
    result = reprice_prompt_fit(prompt_fit, preprocessing)
    assert result["old_speech_feature_token_reserve"] == 455
    assert result["new_speech_feature_token_reserve"] == 468
    assert result["speech_reserve_delta"] == 13
    assert result["envelopes"] == [
        {
            "envelope_id": "ground-direct",
            "observation_token_allowance": 0,
            "prompt_tokens_with_all_reserves": 13027,
            "special_token_reserve": 2,
            "speech_feature_token_reserve": 468,
            "text_prompt_tokens": 12557,
        },
        {
            "envelope_id": "ground-agent-observed",
            "observation_token_allowance": 1024,
            "prompt_tokens_with_all_reserves": 14066,
            "special_token_reserve": 2,
            "speech_feature_token_reserve": 468,
            "text_prompt_tokens": 12572,
        },
    ]
    assert result["maximum_prompt_tokens_with_all_reserves"] == 14066
    assert result["required_context_per_slot"] == 15090
    assert result["context_margin_tokens"] == 17678
    assert result["maximum_prompt_fits_one_slot"] is True
    assert result["message_sha256"] == prompt_fit["message_sha256"]
    assert result["runtime_verification"] == prompt_fit["runtime_verification"]
    assert result["handbook"] == prompt_fit["handbook"]


@pytest.mark.parametrize("mutation", ["count", "packet_count", "maximum", "old_reserve"])
def test_reprice_prompt_fit_refuses_source_drift(mutation: str) -> None:
    prompt_fit, preprocessing = _source()
    prompt_fit = copy.deepcopy(prompt_fit)
    preprocessing = copy.deepcopy(preprocessing)
    if mutation == "count":
        preprocessing["count"] = 103
    elif mutation == "packet_count":
        preprocessing["speech_feature_tokens"]["packets"].pop()
    elif mutation == "maximum":
        preprocessing["speech_feature_tokens"]["distribution"]["max"] = 467
    else:
        prompt_fit["bounds"]["envelopes"][0]["speech_feature_token_reserve"] = 454
    with pytest.raises(PromptFitInheritanceError):
        reprice_prompt_fit(prompt_fit, preprocessing)
