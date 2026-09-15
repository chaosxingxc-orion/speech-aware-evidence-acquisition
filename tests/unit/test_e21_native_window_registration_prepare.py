from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.cli import load_campaign_plan
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.core.flight.runtime import compute_protocol_hash
from speech_aware_evidence_acquisition.core.preparation_fit import (
    validate_native_contact_fit_config,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program


ROOT = Path(__file__).resolve().parents[2]
DIRECT_EXPERIMENT = "e21-native-window-direct-full44-registration-v1"
DIRECT_BASELINE = "e21-native-window-direct-full44-registration-v1"
SYSTEM_EXPERIMENT = "e21-native-window-context-tools-full44-registration-v1"
SYSTEM_BASELINE = "e21-native-window-context-tools-full44-v1"
MODEL = "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1"
DATASET = "earnings21-native-window-full44-v1"
SPLIT = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
READINESS = ROOT / "docs/readiness/2026-09-15-e21-native-window-registration-prepare-v1"


def _compose(experiment: str, baseline: str):
    return compose(ROOT, MODEL, DATASET, baseline, experiment)


def test_direct_fit_and_generation_share_one_held_configuration() -> None:
    fit, generation = load_campaign_cells(ROOT, DIRECT_EXPERIMENT)
    assert (fit.run_id, fit.attempt_id) == (
        "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1",
        "attempt-e21-native-window-direct-full44-fit-v1",
    )
    assert (generation.run_id, generation.attempt_id) == (
        "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-V1",
        "attempt-e21-native-window-direct-full44-v1",
    )
    assert fit.document["allowed_execution_stages"] == ["check", "prompt-fit"]
    assert generation.document["allowed_execution_stages"] == ["check", "campaign"]
    assert fit.document["readiness"]["state"] == "held"
    assert generation.document["readiness"]["state"] == "held"
    assert fit.document["baseline_fragment"] == generation.document["baseline_fragment"]
    assert (
        ROOT / "configs/baseline/e21-native-window-direct-full44-registration-v1.json"
    ).read_bytes() == (
        ROOT / "configs/baseline/e21-native-window-direct-full44-v1.json"
    ).read_bytes()

    composed = _compose(DIRECT_EXPERIMENT, DIRECT_BASELINE)
    assert composed.values["execution_plan"] == {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 4.0,
        "planned_model_calls": 1593,
        "planned_speech_audio_seconds": 141346,
        "split_role": "discovery",
    }
    assert composed.values["population"] == {
        "count": 44,
        "execution_units": 1593,
        "historically_exposed": True,
        "split_identity_hash": SPLIT,
    }
    assert "prepared_request_fit" not in composed.values


def test_system_and_campaign_preserve_bounds_order_and_authority() -> None:
    system, = load_campaign_cells(ROOT, SYSTEM_EXPERIMENT)
    assert (system.run_id, system.attempt_id) == (
        "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1",
        "attempt-e21-native-window-context-tools-full44-v1",
    )
    assert system.document["allowed_execution_stages"] == ["check", "campaign"]
    assert system.document["readiness"]["state"] == "held"

    composed = _compose(SYSTEM_EXPERIMENT, SYSTEM_BASELINE)
    values = composed.values
    assert values["execution_plan"] == {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 24.0,
        "planned_model_calls": 17523,
        "planned_speech_audio_seconds": 1554805,
        "split_role": "discovery",
    }
    fit = validate_native_contact_fit_config(
        values, default_phase_program(values["policy"])
    )
    assert fit == {
        "attempt_id": "attempt-e21-native-window-context-tools-full44-v1-fit",
        "contact_cap": 70092,
        "max_speech_packets": 1,
        "run_id": "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1-FIT",
    }
    assert values["live_speech_observations"]["execution_plan"]["sha256"] == (
        "9a374d7569795a853594c1b96788756b6ed2fc3e9fafe339ca3f3d3335143ffc"
    )
    assert set(values["knowledge_stores"]) == {
        "document-lexicon",
        "participant-roster",
    }
    assert all(
        set(store["context_supply"]) == {"solver"}
        for store in values["knowledge_stores"].values()
    )

    selected = load_campaign_plan(
        ROOT,
        ROOT
        / "configs/campaign/e21-native-window-direct-vs-context-tools-full44-registration-v1.json",
    )
    assert [cell.run_id for _, cell in selected] == [
        "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-V1",
        "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1",
    ]


def test_draft_plans_match_current_composed_protocols_without_claiming_final_hashes() -> None:
    direct = _compose(DIRECT_EXPERIMENT, DIRECT_BASELINE)
    system = _compose(SYSTEM_EXPERIMENT, SYSTEM_BASELINE)
    protocols = {
        "direct": compute_protocol_hash(direct.config_hash, direct.values["arm"], SPLIT),
        "system": compute_protocol_hash(system.config_hash, system.values["arm"], SPLIT),
    }
    expected = {
        "direct-fit-plan-draft-v1.json": (
            "direct",
            "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-FIT-V1",
            4780,
            4.0,
            141346,
        ),
        "direct-generation-plan-draft-v1.json": (
            "direct",
            "SAEA-E21-NATIVE-WINDOW-DIRECT-FULL44-V1",
            1593,
            4.0,
            141346,
        ),
        "system-generation-plan-draft-v1.json": (
            "system",
            "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1",
            17523,
            24.0,
            1554805,
        ),
        "system-native-fit-plan-draft-v1.json": (
            "system",
            "SAEA-E21-NATIVE-WINDOW-CONTEXT-TOOLS-FULL44-V1-FIT",
            70092,
            24.0,
            1554805,
        ),
    }
    for name, (arm, run_id, calls, gpu_hours, speech_seconds) in expected.items():
        document = json.loads((READINESS / name).read_text(encoding="utf-8"))
        plan = ExecutionPlan(**document["execution_plan"]).validate()
        assert document["status"] == "DRAFT_NO_CONTACT_AUTHORITY"
        assert plan.run_id == run_id
        assert plan.protocol_hash == protocols[arm]
        assert plan.planned_model_calls == calls
        assert plan.planned_gpu_hours == gpu_hours
        assert plan.planned_speech_audio_seconds == speech_seconds
