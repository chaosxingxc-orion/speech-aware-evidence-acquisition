"""Round-trip checks for ``configs/probes/g0-binding/pa2t-a0-flight.json``
-- the frozen A0-only flight config a launcher (a later mission) reads to
fly the P-A2T Stage-1 baseline. Cross-checks it against the frozen probe
receipt and the (draft, not-registrable-as-a-whole) P-A2T binding table it
references. Never touches a model.
"""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.runner import RAILS_ARMS

_G0_BINDING_DIR = Path(__file__).resolve().parents[2] / "configs" / "probes" / "g0-binding"
_FLIGHT_CONFIG_PATH = _G0_BINDING_DIR / "pa2t-a0-flight.json"
_RECEIPT_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "receipts" / "probe-samples" / "r1-audio2tool-sample.json"
)


def _load_flight_config() -> dict:
    return json.loads(_FLIGHT_CONFIG_PATH.read_text(encoding="utf-8"))


def test_flight_config_is_well_formed_and_zero_supply_only():
    document = _load_flight_config()
    assert document["probe"] == "P-A2T"
    assert document["arms"] == ["zero-supply"]
    assert set(document["arms"]) <= set(RAILS_ARMS)
    assert document["runner_call"]["supply_builder"] is None


def test_flight_config_execution_plan_uses_the_baseline_reproduction_profile():
    document = _load_flight_config()
    assert document["execution_plan"]["execution_profile"] == "baseline-reproduction"
    assert document["execution_plan"]["carrier_lock_key"] == "audio2tool"


def test_flight_config_split_identity_matches_the_frozen_probe_receipt():
    document = _load_flight_config()
    receipt = json.loads(_RECEIPT_PATH.read_text(encoding="utf-8"))
    assert document["split_identity"]["split_identity_hash"] == receipt["split_identity_hash"]
    assert document["execution_plan"]["split_identity_hash"] == receipt["split_identity_hash"]
    assert document["split_identity"]["split_role"] == receipt["split_role"] == "discovery"
    assert document["split_identity"]["seed"] == receipt["seed"]
    assert document["split_identity"]["n_items"] == len(receipt["items"]) == 400


def test_flight_config_call_ceiling_covers_one_request_per_item():
    document = _load_flight_config()
    receipt = json.loads(_RECEIPT_PATH.read_text(encoding="utf-8"))
    n_items = len(receipt["items"])
    assert n_items <= document["execution_plan"]["planned_model_calls"]


def test_flight_config_references_the_binding_source_it_is_scoped_from():
    document = _load_flight_config()
    binding_path = Path(__file__).resolve().parents[2] / document["binding_source"]
    assert binding_path.is_file()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    assert binding["probe"] == "P-A2T"
    # The binding table's own split_identity carries the SAME hash this
    # flight config is scoped to -- proves the A0-only config was not
    # accidentally bound to a different split than the draft's own record.
    assert binding["split_identity"]["split_identity_hash"] == (
        document["execution_plan"]["split_identity_hash"]
    )
