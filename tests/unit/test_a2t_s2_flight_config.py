"""Round-trip checks for ``configs/probes/g0-binding/a2t-s2-flight.json`` --
the frozen flight config a launcher (a later, model-touching mission) reads
to fly the REGISTERED P-A2T Stage-2 supply probe. This module never touches
a model; it only proves the config is well-formed and internally consistent
with the other committed artifacts it references.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.probes.a2t_s2_flight import (
    A2T_S2_ARMS,
    DEFAULT_SEED,
    HEADROOM_N,
    N0R_TARGET_N,
    load_headroom_manifest,
    n0r_seeded_draw,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FLIGHT_CONFIG_PATH = _REPO_ROOT / "configs" / "probes" / "g0-binding" / "a2t-s2-flight.json"


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_json_and_declares_the_registered_probe():
    document = _load_flight_config()
    assert document["probe"] == "P-A2T"
    assert document["status"] == "REGISTERED"
    assert document["arms"] == list(A2T_S2_ARMS)
    assert document["seed"] == DEFAULT_SEED


def test_flight_config_execution_plan_uses_the_bounded_discovery_probe_profile():
    document = _load_flight_config()
    assert document["execution_plan"]["execution_profile"] == "bounded-discovery-probe"
    assert document["execution_plan"]["carrier_lock_key"] == "audio2tool"


def test_flight_config_references_a_headroom_manifest_that_actually_loads():
    document = _load_flight_config()
    headroom_path = _REPO_ROOT / document["headroom_manifest"]
    manifest = load_headroom_manifest(headroom_path)
    assert len(manifest.sample_ids) == HEADROOM_N == 120


def test_flight_config_n0r_draw_is_reproducible_from_its_own_declared_seed():
    document = _load_flight_config()
    headroom_path = _REPO_ROOT / document["headroom_manifest"]
    manifest = load_headroom_manifest(headroom_path)
    seed = document["n0r"]["seed"]
    target_n = document["n0r"]["target_n"]
    assert target_n == N0R_TARGET_N == 40
    draw = n0r_seeded_draw(manifest.sample_ids, seed=seed, target_n=target_n)
    assert len(draw) == target_n
    assert set(draw) <= set(manifest.sample_ids)


def test_flight_config_cost_budget_matches_the_call_formula_and_stays_within_ceilings():
    document = _load_flight_config()
    n = HEADROOM_N
    n0r_n = document["n0r"]["target_n"]
    total_calls = 3 * n + n0r_n  # S1p + S2 + S4 per headroom sample, + N0r
    assert total_calls == 400
    assert total_calls <= document["execution_plan"]["planned_model_calls"]
    assert document["execution_plan"]["planned_model_calls"] <= 450  # preregistration's own cap
    assert document["execution_plan"]["planned_gpu_hours"] <= 1.0
    assert document["execution_plan"]["planned_speech_audio_seconds"] <= 3500


def test_flight_config_split_identity_hash_matches_the_frozen_a0_split():
    document = _load_flight_config()
    receipt_path = (
        _REPO_ROOT / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert document["execution_plan"]["split_identity_hash"] == receipt["split_identity_hash"]


def test_flight_config_references_the_preregistration_it_is_scoped_from():
    document = _load_flight_config()
    prereg_path = _REPO_ROOT / document["preregistration"]
    assert prereg_path.is_file()
    text = prereg_path.read_text(encoding="utf-8")
    assert "REGISTERED" in text
    assert document["exposure_ledger_row"] in text
