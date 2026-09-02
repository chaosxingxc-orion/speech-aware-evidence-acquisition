"""Model-free integrity checks for the prospective G6 fixed16 registration."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_g6_fixed16_config_freezes_the_authorized_family_sweep() -> None:
    baseline = json.loads(
        (ROOT / "configs/baseline/a2t-g6-exhaustive-family-sweep-agentloop.json").read_text()
    )
    experiment = json.loads(
        (ROOT / "configs/experiment/a2t-g6-exhaustive-family-sweep-fixed16-v1.json").read_text()
    )

    assert baseline["speech_native_contact_ceiling_per_task"] == 29
    assert baseline["obs_batch_samples"] == 2
    assert baseline["family_scan_contacts_per_task"] == 28
    assert baseline["resolve_contacts_per_task"] == 1
    assert baseline["max_concurrent_model_requests"] == 2
    assert baseline["queue_depth"] == 4
    assert baseline["prompt_token_cap_per_slot"] == 32768
    assert baseline["temperature"] == 0
    assert baseline["repair_contacts"] == baseline["retries"] == baseline["resends"] == 0

    assert experiment["execution_profile"] == "bounded-discovery-probe"
    assert experiment["population"]["count"] == 16
    assert experiment["population"]["split_identity_hash"] == (
        "a99a64f004534516399c520c742132dc31d5c06cab5e59240653ff586a60fcb5"
    )
    assert experiment["protocol"]["contacts_per_sample"] == 29
    assert experiment["protocol"]["family_scan"]["contacts_per_sample"] == 28
    assert experiment["protocol"]["resolve"]["requires_all_28_sealed_reports"] is True
    assert experiment["contact_budget"]["planned_model_calls"] == 16 * 29 == 464
    assert experiment["contact_budget"]["selected_one_pass_speech_audio_seconds"] == 87.001
    assert experiment["contact_budget"]["repeated_speech_audio_seconds_cap"] == 2600
    assert experiment["scoring"]["whole_manifest_only"] is True
    assert experiment["scoring"]["single_process"] is True
    assert experiment["decision_rule"]["scale1000_closed"] is True
