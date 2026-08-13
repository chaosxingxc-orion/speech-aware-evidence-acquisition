"""Registered carriers and evidence sources resolve through the ONE registry."""

import hashlib

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
    conec_names_file_relpath,
    evidence_file_relpath,
    resolve_declared_transform_params,
    rotated_mismatch,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import DerivedEvidenceRegistry
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


def test_evidence_file_relpath_matches_the_conec_contexts_source_layout(synthetic_world):
    """IMPORTANT 1 (external review round 4): evidence_file_relpath -- the
    path the D1 evidence-identity rail re-hashes -- must resolve to the SAME
    on-disk file _conec_contexts itself reads (data.carriers.EvidenceLayout,
    never hand-coded)."""

    lock = load_lock(synthetic_world.lock_path)
    relpath = evidence_file_relpath(lock, "earnings21-original", "4000001")
    assert relpath == "datasets/conec/earnings21/contexts/4000001.txt"
    assert (synthetic_world.data_root / relpath).is_file()
    assert (synthetic_world.data_root / relpath).read_text(encoding="utf-8") == "ctx"


def test_evidence_file_relpath_fails_closed_for_a_carrier_with_no_evidence_layer(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        evidence_file_relpath(lock, "earnings22-original", "5000000")


# ---------------------------------------------------------------------------
# conec-names (2026-08-12): a second verbatim ConEC source pointed at the
# per-sample participant-names roster instead of the context file -- SAME
# machinery as conec-contexts above (carrier gate, identity transform,
# EvidenceItem/DerivedEvidenceRecord shape), a different source file. These
# tests mirror the conec-contexts ones above line for line; the conec-
# contexts tests themselves are UNCHANGED, proving conec-names' addition
# leaves the existing source's behaviour untouched.
# ---------------------------------------------------------------------------


def test_conec_names_source_loads_and_hashes(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    items = EVIDENCE_SOURCES.resolve("conec-names")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )
    assert len(items) == 1
    assert items[0].content == "Jane Doe - CEO\n"
    assert items[0].provenance["lock_key"] == "conec"
    assert len(items[0].provenance["sha256"]) == 64


def test_conec_names_source_fails_closed_when_missing(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        EVIDENCE_SOURCES.resolve("conec-names")(
            lock, synthetic_world.data_root, "0000000", "earnings21-original"
        )


def test_conec_names_source_fails_closed_for_a_carrier_with_no_evidence_layer(synthetic_world):
    """Same fail-closed discipline as conec-contexts: earnings22-original
    declares no ConEC evidence layer at all, so conec-names must refuse
    rather than guess at another carrier's participant-names path."""

    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        EVIDENCE_SOURCES.resolve("conec-names")(
            lock, synthetic_world.data_root, "5000000", "earnings22-original"
        )


def test_conec_names_file_relpath_matches_the_conec_names_source_layout(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    relpath = conec_names_file_relpath(lock, "earnings21-original", "4000001")
    assert relpath == "datasets/conec/earnings21/contexts/participant_names/4000001.names.txt"
    assert (synthetic_world.data_root / relpath).is_file()
    assert (synthetic_world.data_root / relpath).read_text(encoding="utf-8") == "Jane Doe - CEO\n"


def test_conec_names_file_relpath_fails_closed_for_a_carrier_with_no_evidence_layer(
    synthetic_world,
):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="no ConEC evidence layer"):
        conec_names_file_relpath(lock, "earnings22-original", "5000000")


def test_conec_names_carries_an_identity_derivation_record(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-names")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == "4000001"
    assert record.transform_name == "identity"
    assert record.transform_version == "v1"
    assert record.carrier_bound is True
    assert record.source_relpath == conec_names_file_relpath(lock, "earnings21-original", "4000001")
    # identity: derived == source, byte for byte.
    assert record.derived_sha256 == record.source_sha256
    assert item.derivation_source_bytes == b"Jane Doe - CEO\n"
    assert record.source_sha256 == hashlib.sha256(b"Jane Doe - CEO\n").hexdigest()


def test_conec_names_derivation_record_passes_the_registry(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-names")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )[0]
    params = resolve_declared_transform_params(item.derivation.transform_name, None)
    registry = DerivedEvidenceRegistry()
    registered = registry.register(
        item.derivation,
        source_content=item.derivation_source_bytes,
        derived_content=item.content.encode("utf-8"),
        params=params,
    )
    assert registered is item.derivation
    assert registry.lookup("4000001", "identity") is item.derivation


def test_conec_contexts_and_conec_names_are_distinct_registered_sources(synthetic_world):
    """Registering conec-names cannot silently replace/alias conec-contexts
    (core.base.Registry.register refuses a duplicate name by construction);
    this pins that both resolve to different callables and independently
    read their own file, never each other's."""

    lock = load_lock(synthetic_world.lock_path)
    contexts_source = EVIDENCE_SOURCES.resolve("conec-contexts")
    names_source = EVIDENCE_SOURCES.resolve("conec-names")
    assert contexts_source is not names_source
    contexts_item = contexts_source(lock, synthetic_world.data_root, "4000001", "earnings21-original")[0]
    names_item = names_source(lock, synthetic_world.data_root, "4000001", "earnings21-original")[0]
    assert contexts_item.content == "ctx"
    assert names_item.content == "Jane Doe - CEO\n"


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


# ---------------------------------------------------------------------------
# Derivation-chain rail (2026-08-09, docs/readiness/2026-08-09-conec-
# evidence-shape.md "Blocking gap"): conec-contexts is a verbatim passthrough
# -- deliverable 4's "the identity transform, byte-identical to before this
# rail existed" -- proven both by the pre-existing content/provenance
# assertions above (unchanged) and by these new derivation-record checks.
# ---------------------------------------------------------------------------


def test_conec_contexts_carries_an_identity_derivation_record(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-contexts")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == "4000001"
    assert record.transform_name == "identity"
    assert record.transform_version == "v1"
    assert record.carrier_bound is True
    assert record.source_relpath == evidence_file_relpath(lock, "earnings21-original", "4000001")
    # identity: derived == source, byte for byte.
    assert record.derived_sha256 == record.source_sha256
    assert item.derivation_source_bytes == b"ctx"
    assert record.source_sha256 == hashlib.sha256(b"ctx").hexdigest()


def test_conec_contexts_derivation_record_passes_the_registry(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    item = EVIDENCE_SOURCES.resolve("conec-contexts")(
        lock, synthetic_world.data_root, "4000001", "earnings21-original"
    )[0]
    params = resolve_declared_transform_params(item.derivation.transform_name, None)
    registry = DerivedEvidenceRegistry()
    registered = registry.register(
        item.derivation,
        source_content=item.derivation_source_bytes,
        derived_content=item.content.encode("utf-8"),
        params=params,
    )
    assert registered is item.derivation
    assert registry.lookup("4000001", "identity") is item.derivation
