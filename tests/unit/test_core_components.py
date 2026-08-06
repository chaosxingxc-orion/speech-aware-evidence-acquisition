"""Registered carriers and evidence sources resolve through the ONE registry."""

import pytest

from speech_aware_evidence_acquisition.core import carriers, evidence  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import (
    CARRIERS,
    EVIDENCE_SOURCES,
    EvidenceError,
    EvidenceItem,
)
from speech_aware_evidence_acquisition.core.evidence import (
    OracleEvidenceError,
    rotated_mismatch,
)
from speech_aware_evidence_acquisition.data.lock import load_lock


def test_carriers_are_registered_and_load(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    e21 = CARRIERS.resolve("earnings21-original")(lock, synthetic_world.data_root)
    e22 = CARRIERS.resolve("earnings22-original")(lock, synthetic_world.data_root)
    assert len(e21) == 3 and len(e22) == 12


def test_none_source_returns_empty(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    assert (
        EVIDENCE_SOURCES.resolve("none")(
            lock, synthetic_world.data_root, "x", "earnings21-original"
        )
        == []
    )


def test_conec_source_loads_and_hashes(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-contexts")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )
    assert len(items) == 1
    assert items[0].content == "ctx"
    assert items[0].provenance["lock_key"] == "conec"
    assert len(items[0].provenance["sha256"]) == 64


def test_conec_source_fails_closed_when_missing(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        EVIDENCE_SOURCES.resolve("conec-contexts")(
            lock, synthetic_world.data_root, "0000000", "earnings21-original"
        )


def test_conec_source_fails_closed_for_a_carrier_with_no_evidence_layer(synthetic_world):
    """R0 repair refactor stage 2 (part B): earnings22-original's descriptor
    declares no ConEC evidence layer (its ConEC contexts are per-call PDF
    packets, a different shape ``_conec_contexts`` never read) -- this must
    fail closed with a clear message, never silently read earnings21-
    original's contexts for an earnings22 sample id."""

    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        EVIDENCE_SOURCES.resolve("conec-contexts")(
            lock, synthetic_world.data_root, "5000000", "earnings22-original"
        )


def _item(evidence_id):
    return EvidenceItem(
        evidence_id=evidence_id, source_uri="u://x", content=evidence_id,
        provenance={"lock_key": "conec", "relpath": "r", "sha256": "0" * 64},
    )


def test_rotated_mismatch_is_a_derangement():
    table = {"a": [_item("ev-a")], "b": [_item("ev-b")], "c": [_item("ev-c")]}
    rotated = rotated_mismatch(table)
    assert set(rotated) == set(table)
    for sample_id, items in rotated.items():
        assert items != table[sample_id], sample_id
    with pytest.raises(EvidenceError, match="at least 2"):
        rotated_mismatch({"a": [_item("ev-a")]})


def test_oracle_source_never_enters_runtime(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(OracleEvidenceError, match="scoring-side"):
        EVIDENCE_SOURCES.resolve("oracle")(
            lock, synthetic_world.data_root, "4000001", "earnings21-original"
        )
