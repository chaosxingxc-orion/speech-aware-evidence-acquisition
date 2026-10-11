"""The construction-role roster scan skips declared companions and nothing else.

``docs/receipts/rosters/a2t-paired-400-v1.comparator-rows.json`` is pinned by path
and sha256 from the roster receipt, so it stays beside the rosters; the gate must
not mistake it for a roster, yet any other non-roster schema stays fail-closed.
"""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts.gate import GateClosed
from speech_aware_evidence_acquisition.contracts.gate_exposure import (
    ROSTER_COMPANION_SCHEMAS,
    ROSTER_RECEIPT_SCHEMA,
    ROSTER_RECEIPTS_RELDIR,
    _ExposureAndCarrierMixin,
)

CARRIER = "audio2tool-test"


def _scan(root):
    return _ExposureAndCarrierMixin._construction_roster_identity_hashes(
        SimpleNamespace(source_root=root), CARRIER
    )


def _write(root, name, document):
    directory = root / ROSTER_RECEIPTS_RELDIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(json.dumps(document), encoding="utf-8")


def _roster():
    ids = ["a", "b"]
    digest = hashlib.sha256("\n".join(sorted(f"{CARRIER}/{i}" for i in ids)).encode()).hexdigest()
    return digest, {
        "schema": ROSTER_RECEIPT_SCHEMA,
        "carrier_lock_key": CARRIER,
        "roster_role": "construction",
        "split_identity_hash": digest,
        "items": [{"sample_id": i} for i in ids],
    }


def test_declared_companion_is_skipped_and_the_roster_is_found(tmp_path):
    digest, roster = _roster()
    _write(tmp_path, "r.json", roster)
    _write(tmp_path, "r.comparator-rows.json", {"schema": "saea-a2t-paired-roster-comparator-rows-v1"})
    assert "saea-a2t-paired-roster-comparator-rows-v1" in ROSTER_COMPANION_SCHEMAS
    assert list(_scan(tmp_path)) == [digest]


def test_a_declared_non_roster_schema_is_skipped_but_a_schemaless_file_fails_closed(tmp_path):
    digest, roster = _roster()
    _write(tmp_path, "r.json", roster)
    _write(tmp_path, "x.json", {"schema": "something-else-v1"})
    _write(tmp_path, "subset.json", {"schema": "saea-runtime-subset-receipt-v1"})
    hashes = _scan(tmp_path)
    assert set(hashes) == {digest}
    _write(tmp_path, "noschema.json", {"items": []})
    with pytest.raises(GateClosed, match="declares no schema"):
        _scan(tmp_path)
