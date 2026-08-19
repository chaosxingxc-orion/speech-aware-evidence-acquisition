"""Round-trip checks for ``configs/probes/g0-binding/pkey-flight.json`` --
the REGISTERED flight config a launcher (a later mission) reads to fly the
P-KEY probe. This module never touches a model; it only proves the config is
well-formed and internally consistent with the OTHER committed g0-binding
artifacts it reuses (the SAME sample manifest and roster table the consumed
P-SLU flight already used).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.pkey_flight import (
    EXPECTED_SPLIT_IDENTITY_HASH,
    PKEY_ARMS,
    assert_pinned_text_matches_config,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, load_pslu_sample_manifest

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pkey-flight.json"
_PARENT_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pslu-flight.json"


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def _load_parent_flight_config() -> dict:
    return json.loads(_PARENT_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-KEY"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(PKEY_ARMS)
    assert document["exposure_ledger_row"] == "SAEA-PROBE-pkey-303"


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


def test_flight_config_pinned_text_matches_the_module_constants():
    document = _load_flight_config()
    assert_pinned_text_matches_config(document)  # does not raise


def test_flight_config_silence_swap_reproduces_the_parents_own_sample_ids():
    """Same seeding discipline as the consumed P-SLU flight -- the 3
    silence-swap sample ids are DERIVED via the IDENTICAL rule/seed over the
    SAME frozen 60-sample manifest, so they must equal the parent flight's
    own frozen list exactly."""

    document = _load_flight_config()
    parent_document = _load_parent_flight_config()
    manifest_path = Path(__file__).resolve().parents[2] / document["sample_manifest"]
    manifest = load_pslu_sample_manifest(manifest_path)

    seed = document["silence_swap"]["seed"]
    assert seed == manifest.seed == parent_document["silence_swap"]["seed"]
    expected = sorted(random.Random(f"{seed}:silence-swap").sample(sorted(manifest.sample_ids), 3))

    assert document["silence_swap"]["sample_ids"] == expected
    assert document["silence_swap"]["sample_ids"] == parent_document["silence_swap"]["sample_ids"]
    assert document["silence_swap"]["count"] == 3 == len(expected)
    assert set(expected) <= set(manifest.sample_ids)
    assert document["silence_swap"]["arm"] == "AUD-SUP"


def test_flight_config_cost_budget_stays_within_the_registered_ceilings():
    document = _load_flight_config()
    n = len(load_pslu_sample_manifest(Path(__file__).resolve().parents[2] / document["sample_manifest"]).sample_ids)
    per_pass_calls = n * len(PKEY_ARMS)
    silence_calls = document["silence_swap"]["count"]
    total_calls = per_pass_calls + silence_calls
    assert total_calls == 303  # registration section 5: "303 requests (300 + 3 swaps)"
    assert total_calls <= document["execution_plan"]["planned_model_calls"]
    assert document["execution_plan"]["planned_model_calls"] <= 340  # registration's own cap
    assert document["execution_plan"]["planned_speech_audio_seconds"] <= 2500  # registration's own cap
    assert document["execution_plan"]["planned_gpu_hours"] <= 0.6  # registration's own cap
