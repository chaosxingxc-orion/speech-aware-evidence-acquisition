"""The COMMITTED ``e21_participant_names`` D1 evidence supplement, checked against
the COMMITTED base D1 artifact -- repository bytes only, no ``SPEECHRL_DATA_DIR``.

``tests/contract/test_d1_evidence_supplement.py`` proves the RAIL on a synthetic
world. This module proves the one real document the KC-E1 flight will carry is
the document that rail will accept: its two digests recompute, its parent binding
names the live base D1, its sample universe is the carrier's own frozen 44, and
the layer it declares is genuinely absent from the base artifact (so it adds
rather than shadows).
"""

import hashlib
import json
from pathlib import Path

from speech_aware_evidence_acquisition.contracts.gate_evidence_identity import (
    EVIDENCE_SUPPLEMENT_SCHEMA,
    _layer_ids_sha256,
    _layer_manifest_sha256,
    _parse_evidence_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_D1 = REPO_ROOT / "docs/receipts/artifacts/d1-identity.json"
SUPPLEMENT = REPO_ROOT / "docs/receipts/artifacts/d1-e21-participant-names.json"
DATASET_FRAGMENT = REPO_ROOT / "configs/dataset/earnings21-discovery-conec-names.json"
LAYER_KEY = "e21_participant_names"
DEFAULT_LAYER_KEY = "e21_contexts"


def _document(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _conec_layers() -> dict:
    return _document(BASE_D1)["carriers"]["conec"]["layers"]


def test_the_base_d1_still_lacks_the_roster_layer():
    """If this ever fails the supplement has become a shadow, and the gate will
    say so -- but the repair is to retire the supplement, not to keep both."""

    assert LAYER_KEY not in _conec_layers()


def test_the_supplement_declares_one_absent_layer_for_the_right_carrier():
    document = _document(SUPPLEMENT)
    assert document["schema"] == EVIDENCE_SUPPLEMENT_SCHEMA
    assert document["study"] == "speech-aware-evidence-acquisition"
    assert document["carrier_lock_key"] == "conec"
    assert document["d1_layer_key"] == LAYER_KEY


def test_the_supplement_binds_to_the_live_base_d1():
    document = _document(SUPPLEMENT)
    assert document["parent_d1_sha256"] == hashlib.sha256(BASE_D1.read_bytes()).hexdigest()


def test_the_supplement_covers_exactly_the_carriers_frozen_sample_universe():
    document = _document(SUPPLEMENT)
    universe = _conec_layers()[DEFAULT_LAYER_KEY]["ids_sha256"]
    assert document["source_binding_sha256"] == universe
    assert document["ids_sha256"] == universe
    assert document["count"] == 44


def test_both_digests_recompute_from_the_manifest_the_gate_reads():
    document = _document(SUPPLEMENT)
    recorded = _parse_evidence_manifest(document["manifest"], "committed supplement")
    assert len(recorded) == document["count"]
    assert _layer_ids_sha256(recorded) == document["ids_sha256"]
    assert _layer_manifest_sha256(recorded) == document["manifest_sha256"]
    assert sum(facts[0] for facts in recorded.values()) == document["total_bytes"]


def test_the_stray_aggregate_roster_is_recorded_as_a_non_layer_file():
    """ConEC ships one ``names.txt`` beside the 44 per-call rosters. It is not a
    sample, it is not silently dropped, and it never enters the manifest."""

    document = _document(SUPPLEMENT)
    assert document["excluded_non_layer_files"] == ["names.txt"]
    assert all(entry["id"] != "names" for entry in document["manifest"])


def test_the_kc_e1_dataset_fragment_pins_this_exact_supplement():
    fragment = _document(DATASET_FRAGMENT)
    assert fragment["d1_evidence_supplement"] == "receipts/artifacts/d1-e21-participant-names.json"
    assert (
        fragment["d1_evidence_supplement_sha256"]
        == hashlib.sha256(SUPPLEMENT.read_bytes()).hexdigest()
    )
    assert "d1_media_supplement" not in fragment
