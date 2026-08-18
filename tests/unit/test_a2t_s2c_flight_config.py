"""Round-trip checks for ``configs/probes/g0-binding/a2t-s2c-flight.json``
-- the frozen flight config a later, model-touching launcher reads to fly
the REGISTERED P-A2T Stage-2c form-robustness probe. This module never
touches a model; it only proves the config is well-formed and internally
consistent with the other committed artifacts it references (mirrors
``tests/unit/test_a2t_s2b_flight_config.py``'s own discipline for
Stage-2b's config).
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.a2t_s2c_flight import A2T_S2C_ARMS
from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
    HEADROOM_N,
    load_headroom_manifest,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLIGHT_CONFIG_PATH = _REPO_ROOT / "configs" / "probes" / "g0-binding" / "a2t-s2c-flight.json"
_STAGE2B_FLIGHT_CONFIG_PATH = _REPO_ROOT / "configs" / "probes" / "g0-binding" / "a2t-s2b-flight.json"
_STAGE2_FLIGHT_RECEIPT_PATH = (
    _REPO_ROOT
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-08-18-a2t-s2-flight"
    / "flight-receipt.json"
)

REGISTERED_SEED = 20260807
REGISTERED_CALLS_CEILING = 400
REGISTERED_AUDIO_SECONDS_CEILING = 3000
REGISTERED_GPU_HOURS_CEILING = 0.75


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-A2T"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(A2T_S2C_ARMS) == ["C1", "C2", "C3"]
    assert document["seed"] == REGISTERED_SEED


def test_flight_config_execution_plan_uses_the_bounded_discovery_probe_profile():
    document = _load_flight_config()
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
    assert document["execution_plan"]["carrier_lock_key"] == "audio2tool"


def test_flight_config_references_a_headroom_manifest_that_actually_loads():
    document = _load_flight_config()
    headroom_path = _REPO_ROOT / document["headroom_manifest"]
    manifest = load_headroom_manifest(headroom_path)
    assert len(manifest.sample_ids) == HEADROOM_N == 120


def test_flight_config_reuses_the_same_headroom_manifest_and_split_hash_as_stage2b():
    """Prereg intro: 'the SAME 120 headroom ids ... same binding paths as
    Stage-2b'."""

    document = _load_flight_config()
    stage2b_document = json.loads(_STAGE2B_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))
    assert document["headroom_manifest"] == stage2b_document["headroom_manifest"]
    assert document["execution_plan"]["split_identity_hash"] == (
        stage2b_document["execution_plan"]["split_identity_hash"]
    )
    assert document["stage2_arm_plan_path"]["path"] == stage2b_document["stage2_arm_plan_path"]["path"]


def test_flight_config_cost_budget_matches_the_call_formula_and_stays_within_ceilings():
    document = _load_flight_config()
    n = HEADROOM_N
    total_calls = 3 * n  # C1 + C2 + C3 per headroom sample
    assert total_calls == 360
    assert total_calls <= document["execution_plan"]["planned_model_calls"]
    assert document["execution_plan"]["planned_model_calls"] <= REGISTERED_CALLS_CEILING
    assert document["cost_budget"]["call_ceiling"] == REGISTERED_CALLS_CEILING
    assert document["execution_plan"]["planned_gpu_hours"] <= REGISTERED_GPU_HOURS_CEILING
    assert document["cost_budget"]["gpu_hours_ceiling"] == REGISTERED_GPU_HOURS_CEILING
    assert document["execution_plan"]["planned_speech_audio_seconds"] <= REGISTERED_AUDIO_SECONDS_CEILING
    assert document["cost_budget"]["audio_seconds_ceiling"] == REGISTERED_AUDIO_SECONDS_CEILING


def test_flight_config_split_identity_hash_matches_the_frozen_a0_split():
    document = _load_flight_config()
    receipt_path = _REPO_ROOT / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert document["execution_plan"]["split_identity_hash"] == receipt["split_identity_hash"]


def test_flight_config_references_the_preregistration_it_is_scoped_from():
    document = _load_flight_config()
    prereg_path = _REPO_ROOT / document["preregistration"]
    assert prereg_path.is_file()
    text = prereg_path.read_text(encoding="utf-8")
    assert "REGISTERED" in text
    assert document["exposure_ledger_row"] in text


def test_flight_config_stage2_arm_plan_path_names_the_real_flown_attempt():
    """The reused-verbatim mapping source names Stage-2's OWN already-flown
    attempt (cross-checked against that flight's own archived receipt, so a
    stale/typo'd attempt id here is caught mechanically)."""

    document = _load_flight_config()
    path_field = document["stage2_arm_plan_path"]["path"]
    assert path_field.startswith("$SPEECHRL_DATA_DIR/")
    assert path_field.endswith(".arm-plan.json")

    stage2_receipt = json.loads(_STAGE2_FLIGHT_RECEIPT_PATH.read_text(encoding="utf-8"))
    assert stage2_receipt["status"] == "COMPLETED"
    assert stage2_receipt["attempt_id"] in path_field
    assert stage2_receipt["run_id"] in path_field
