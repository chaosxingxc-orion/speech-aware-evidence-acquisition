"""Round-trip checks for ``configs/probes/g0-binding/pslu-flight.json`` --
the frozen flight config a launcher (a later mission) reads to fly the
REGISTERED P-SLU probe. This module never touches a model; it only proves
the config is well-formed and internally consistent with the OTHER
committed g0-binding artifacts it references.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    PSLU_ARMS,
    load_pslu_rosters,
    load_pslu_sample_manifest,
)

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pslu-flight.json"


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-SLU"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(PSLU_ARMS)


def test_flight_config_execution_plan_split_identity_hash_matches_the_sample_manifest():
    document = _load_flight_config()
    manifest_path = Path(__file__).resolve().parents[2] / document["sample_manifest"]
    manifest = load_pslu_sample_manifest(manifest_path)
    assert document["execution_plan"]["split_identity_hash"] == manifest.split_identity_hash
    assert document["execution_plan"]["carrier_lock_key"] == "slurp"
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"


def test_flight_config_referenced_roster_table_is_loadable_and_legal_tier():
    document = _load_flight_config()
    roster_path = Path(__file__).resolve().parents[2] / document["roster_table"]
    rosters = load_pslu_rosters(roster_path)  # raises if legality_tier != "legal"
    assert len(rosters.global_types) == 55


def test_flight_config_silence_swap_sample_ids_are_reproducible_from_the_declared_rule():
    """The 3 silence-swap sample ids are DERIVED, not hand-picked -- proves
    the frozen list in the config matches the declared deterministic
    selection rule (module docstring: rails.silence_swap negative control,
    docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md)."""

    document = _load_flight_config()
    manifest_path = Path(__file__).resolve().parents[2] / document["sample_manifest"]
    manifest = load_pslu_sample_manifest(manifest_path)
    seed = document["silence_swap"]["seed"]
    assert seed == manifest.seed
    expected = sorted(random.Random(f"{seed}:silence-swap").sample(sorted(manifest.sample_ids), 3))
    assert document["silence_swap"]["sample_ids"] == expected
    assert document["silence_swap"]["count"] == 3 == len(expected)
    # Every silence-swap id must actually belong to the frozen 60.
    assert set(expected) <= set(manifest.sample_ids)


def test_flight_config_cost_budget_stays_within_the_preregistered_ceilings():
    document = _load_flight_config()
    n = len(load_pslu_sample_manifest(
        Path(__file__).resolve().parents[2] / document["sample_manifest"]
    ).sample_ids)
    phase1_calls = n
    phase2_calls = n * 5
    silence_calls = document["silence_swap"]["count"]
    total_calls = phase1_calls + phase2_calls + silence_calls
    assert total_calls == 363
    assert total_calls <= document["execution_plan"]["planned_model_calls"]
    assert document["execution_plan"]["planned_model_calls"] <= 450  # preregistration's own cap
