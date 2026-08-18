"""Round-trip checks for ``configs/probes/g0-binding/pslu-s2-flight.json`` --
the frozen flight config a launcher (a later mission) reads to fly the
REGISTERED P-SLU Stage-2 follow-up probe (SAEA-PROBE-pslu-s2-183). This
module never touches a model; it only proves the config is well-formed and
internally consistent with the OTHER committed g0-binding artifacts it
references (including the PARENT flight's own frozen config).
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.pslu_flight import load_pslu_rosters, load_pslu_sample_manifest
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_filler import load_filler_lexicon
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import PSLU_S2_ARMS

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pslu-s2-flight.json"
_PARENT_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pslu-flight.json"

# docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md section 3
# ("Discipline"), verbatim.
_REGISTERED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def _load_parent_flight_config() -> dict:
    return json.loads(_PARENT_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-SLU-S2"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(PSLU_S2_ARMS)
    assert document["exposure_ledger_row"] == "SAEA-PROBE-pslu-s2-183"


def test_flight_config_execution_plan_split_identity_hash_is_verbatim_the_registered_value():
    document = _load_flight_config()
    assert document["execution_plan"]["split_identity_hash"] == _REGISTERED_SPLIT_IDENTITY_HASH
    assert document["execution_plan"]["carrier_lock_key"] == "slurp"
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"


def test_flight_config_split_identity_hash_matches_the_sample_manifest():
    document = _load_flight_config()
    manifest_path = Path(__file__).resolve().parents[2] / document["sample_manifest"]
    manifest = load_pslu_sample_manifest(manifest_path)
    assert document["execution_plan"]["split_identity_hash"] == manifest.split_identity_hash


def test_flight_config_reuses_the_same_sample_manifest_as_the_parent_flight():
    document = _load_flight_config()
    parent_document = _load_parent_flight_config()
    assert document["sample_manifest"] == parent_document["sample_manifest"]
    assert document["roster_table"] == parent_document["roster_table"]


def test_flight_config_referenced_roster_table_is_loadable_and_legal_tier():
    document = _load_flight_config()
    roster_path = Path(__file__).resolve().parents[2] / document["roster_table"]
    rosters = load_pslu_rosters(roster_path)  # raises if legality_tier != "legal"
    assert len(rosters.global_types) == 55


def test_flight_config_referenced_filler_lexicon_is_loadable():
    document = _load_flight_config()
    lexicon_path = Path(__file__).resolve().parents[2] / document["filler_lexicon"]
    words = load_filler_lexicon(lexicon_path)
    assert len(words) == 300


def test_flight_config_silence_swap_reproduces_the_parents_own_sample_ids():
    """Same seeding discipline as the parent (mission instruction) -- the 3
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
    assert document["silence_swap"]["arm"] == "A1r"


def test_flight_config_cost_budget_stays_within_the_registered_ceilings():
    document = _load_flight_config()
    n = len(load_pslu_sample_manifest(
        Path(__file__).resolve().parents[2] / document["sample_manifest"]
    ).sample_ids)
    f1_calls = n
    a1r_phase1_calls = n
    a1r_phase2_calls = n
    silence_calls = document["silence_swap"]["count"]
    total_calls = f1_calls + a1r_phase1_calls + a1r_phase2_calls + silence_calls
    assert total_calls == 183  # registration section 3: "180 audio requests + 3 silence-swap = 183"
    assert total_calls <= document["execution_plan"]["planned_model_calls"]
    assert document["execution_plan"]["planned_model_calls"] <= 220  # registration's own cap
    assert document["execution_plan"]["planned_speech_audio_seconds"] <= 2000  # registration's own cap
    assert document["execution_plan"]["planned_gpu_hours"] <= 0.5  # registration's own cap
