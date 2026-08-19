"""Round-trip checks for ``configs/probes/g0-binding/ptrap-flight.json`` --
the REGISTERED flight config a launcher (a later mission) reads to fly the
P-TRAP probe. This module never touches a model; it only proves the config
is well-formed and internally consistent with the OTHER committed
g0-binding artifacts it reuses (the SAME sample manifest and roster table
the consumed P-SLU/P-KEY flights already used).
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, load_pslu_sample_manifest
from speech_aware_evidence_acquisition.rails.probes.ptrap_flight import (
    DEFAULT_TRAP_SEED,
    EXPECTED_SPLIT_IDENTITY_HASH,
    PTRAP_ARMS,
    TRAP_K_CAP,
)

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "ptrap-flight.json"
_PARENT_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pslu-flight.json"


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def _load_parent_flight_config() -> dict:
    return json.loads(_PARENT_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-TRAP"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(PTRAP_ARMS)
    assert document["exposure_ledger_row"] == "SAEA-PROBE-ptrap-120"


def test_flight_config_execution_plan_split_identity_hash_is_verbatim_the_registered_value():
    document = _load_flight_config()
    assert document["execution_plan"]["split_identity_hash"] == EXPECTED_SPLIT_IDENTITY_HASH
    assert document["execution_plan"]["carrier_lock_key"] == "slurp"
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"


def test_flight_config_split_identity_hash_matches_the_sample_manifest():
    document = _load_flight_config()
    manifest_path = Path(__file__).resolve().parents[2] / document["sample_manifest"]
    manifest = load_pslu_sample_manifest(manifest_path)
    assert document["execution_plan"]["split_identity_hash"] == manifest.split_identity_hash


def test_flight_config_reuses_the_same_sample_manifest_and_roster_table_as_the_parent_flight():
    document = _load_flight_config()
    parent_document = _load_parent_flight_config()
    assert document["sample_manifest"] == parent_document["sample_manifest"]
    assert document["roster_table"] == parent_document["roster_table"]


def test_flight_config_referenced_roster_table_is_loadable_and_legal_tier():
    document = _load_flight_config()
    roster_path = Path(__file__).resolve().parents[2] / document["roster_table"]
    rosters = load_pslu_rosters(roster_path)  # raises if legality_tier != "legal"
    assert len(rosters.full_roster) == 100


def test_flight_config_trap_source_block_agrees_with_the_module_constants():
    document = _load_flight_config()
    trap_source = document["trap_source"]
    assert trap_source["trap_k_cap"] == TRAP_K_CAP == 5
    assert trap_source["trap_donor_seed"] == DEFAULT_TRAP_SEED == 20260807
    assert trap_source["consumed_pslu_arm"] == "A0"
    assert trap_source["consumed_pslu_attempt_id"] == "attempt-20260818T010218Z-4c97cb"


def test_flight_config_cost_budget_stays_within_the_registered_ceilings():
    document = _load_flight_config()
    n = len(load_pslu_sample_manifest(Path(__file__).resolve().parents[2] / document["sample_manifest"]).sample_ids)
    total_calls = n * len(PTRAP_ARMS)
    assert total_calls == 120  # preregistration section 4: "120 requests (2x60)"
    assert n == 60

    assert document["execution_plan"]["planned_model_calls"] == total_calls == 120
    assert document["execution_plan"]["planned_model_calls"] <= document["cost_budget"]["call_ceiling"]
    assert document["cost_budget"]["call_ceiling"] <= 140  # registered ceiling
    assert document["execution_plan"]["planned_speech_audio_seconds"] <= 1000  # registered ceiling
    assert document["execution_plan"]["planned_gpu_hours"] <= 0.3  # registered ceiling


def test_flight_config_bootstrap_block_matches_the_shared_primitive_defaults():
    from speech_aware_evidence_acquisition.analysis.bootstrap import (
        DEFAULT_CI_LEVEL,
        DEFAULT_N_REPLICATES,
        DEFAULT_SEED,
    )

    document = _load_flight_config()
    assert document["bootstrap"]["n_replicates"] == DEFAULT_N_REPLICATES == 10_000
    assert document["bootstrap"]["seed"] == DEFAULT_SEED == 20260807
    assert document["bootstrap"]["ci_level"] == DEFAULT_CI_LEVEL == 0.90
