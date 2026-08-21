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
    assert_evidence_materialization_id_legal,
    conec_names_file_relpath,
    evidence_file_relpath,
    resolve_declared_transform_params,
    resolve_evidence_materialization_id,
    rotated_mismatch,
)
from speech_aware_evidence_acquisition.core.evidence_derivation import DerivedEvidenceRegistry
from speech_aware_evidence_acquisition.data.lock import load_lock


def test_carriers_are_registered_and_load(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    e21 = CARRIERS.resolve("earnings21-original")(lock, synthetic_world.data_root)
    e22 = CARRIERS.resolve("earnings22-original")(lock, synthetic_world.data_root)
    assert len(e21) == 3 and len(e22) == 12


def test_slurp_carrier_loads_the_composed_dataset_view(monkeypatch, tmp_path):
    captured = {}

    def load_speech_native(lock, root, **kwargs):
        captured.update(kwargs)
        return ["configured-sample"]

    monkeypatch.setattr(carriers, "load_slurp_speech_native_carrier", load_speech_native)
    loader = CARRIERS.resolve("slurp")
    dataset_path = tmp_path / "configs/dataset/slurp-speech-native-opt-a36.json"
    result = loader.load_for_config(
        {},
        tmp_path,
        dataset_path=dataset_path,
        values={"split_name": "OPT-A36", "count": 36},
    )

    assert result == ["configured-sample"]
    assert captured == {
        "config_path": dataset_path,
        "expected_split_name": "OPT-A36",
        "expected_count": 36,
    }


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


# ---------------------------------------------------------------------------
# derived-candidates (Part 1, offline-materialized retrieval-gated candidate
# evidence -- E-003R / KC-Q3): carrier-independent, so these tests write
# their own file directly under synthetic_world.data_root/derived/... rather
# than extending SyntheticWorld's carrier layout at all. Mirrors the
# conec-names tests above line for line wherever the shape matches.
# ---------------------------------------------------------------------------


def _write_derived_candidates(data_root, materialization_id, sample_id, content):
    path = (
        data_root
        / "derived"
        / "evidence-candidates"
        / materialization_id
        / f"{sample_id}.candidates.txt"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_derived_candidates_source_loads_and_hashes(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "alpha\nbravo\n")
    items = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_source": "derived-candidates", "evidence_materialization_id": "mat-test"},
    )
    assert len(items) == 1
    item = items[0]
    assert item.content == "alpha\nbravo\n"
    assert item.provenance["lock_key"] == "derived-candidates"
    assert item.provenance["materialization_id"] == "mat-test"
    assert len(item.provenance["sha256"]) == 64


def test_derived_candidates_source_returns_empty_for_a_zero_byte_file(synthetic_world):
    """SAEA-P2 abort fix (2026-08-15 P2 abort): a materialized candidates
    file that exists and reads cleanly but is genuinely empty (a call with
    zero benchmark errors, e.g. p1-oracle-v2) must never reach
    ``EvidenceItem(content=...).validate()`` -- it mirrors ``_none_source``'s
    own "no evidence for this sample" shape instead."""

    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "")
    items = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_source": "derived-candidates", "evidence_materialization_id": "mat-test"},
    )
    assert items == []


def test_derived_candidates_source_returns_empty_for_a_whitespace_only_file(synthetic_world):
    """Same "no evidence" shape for a file with only blank lines -- zero
    NON-BLANK lines, the exact test ``reproduction.replay_loop._pack_terms``
    already applies to this same file."""

    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "\n  \n\n")
    items = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_source": "derived-candidates", "evidence_materialization_id": "mat-test"},
    )
    assert items == []


def test_derived_candidates_source_fails_closed_when_missing(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="missing"):
        EVIDENCE_SOURCES.resolve("derived-candidates")(
            lock,
            synthetic_world.data_root,
            "0000000",
            "earnings21-original",
            {"evidence_materialization_id": "mat-test"},
        )


def test_derived_candidates_source_never_reads_a_carrier(synthetic_world):
    """No CarrierDescriptor lookup happens at all -- unlike conec-contexts/
    conec-names, an unregistered/nonsense carrier_lock_key is still fine as
    long as the materialized file itself exists."""

    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "alpha\n")
    items = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "not-a-registered-carrier-at-all",
        {"evidence_materialization_id": "mat-test"},
    )
    assert items[0].content == "alpha\n"


def test_derived_candidates_source_fails_closed_without_a_materialization_id(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        EVIDENCE_SOURCES.resolve("derived-candidates")(
            lock, synthetic_world.data_root, "4000001", "earnings21-original"
        )


def test_derived_candidates_source_fails_closed_on_an_empty_materialization_id(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        EVIDENCE_SOURCES.resolve("derived-candidates")(
            lock,
            synthetic_world.data_root,
            "4000001",
            "earnings21-original",
            {"evidence_materialization_id": ""},
        )


def test_derived_candidates_carries_an_identity_derivation_record_not_carrier_bound(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "alpha\n")
    item = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_materialization_id": "mat-test"},
    )[0]
    record = item.derivation
    assert record is not None
    assert record.sample_id == "4000001"
    assert record.transform_name == "identity"
    assert record.transform_version == "v1"
    assert record.carrier_bound is False
    assert record.derived_sha256 == record.source_sha256
    assert item.derivation_source_bytes == b"alpha\n"
    assert record.source_sha256 == hashlib.sha256(b"alpha\n").hexdigest()


def test_derived_candidates_derivation_record_passes_the_registry(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "alpha\n")
    item = EVIDENCE_SOURCES.resolve("derived-candidates")(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_materialization_id": "mat-test"},
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


# ---------------------------------------------------------------------------
# evidence_materialization_id key-legality matrix: required by, and legal
# ONLY WITH, evidence_source == "derived-candidates" (fail closed both
# directions).
# ---------------------------------------------------------------------------


def test_resolve_evidence_materialization_id_returns_a_valid_value():
    assert resolve_evidence_materialization_id({"evidence_materialization_id": "mat-1"}) == "mat-1"


def test_resolve_evidence_materialization_id_refuses_when_absent():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        resolve_evidence_materialization_id({})


def test_resolve_evidence_materialization_id_refuses_when_absent_values_none():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        resolve_evidence_materialization_id(None)


def test_resolve_evidence_materialization_id_refuses_when_empty():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        resolve_evidence_materialization_id({"evidence_materialization_id": ""})


def test_resolve_evidence_materialization_id_refuses_a_non_string():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        resolve_evidence_materialization_id({"evidence_materialization_id": 7})


def test_evidence_materialization_id_required_when_derived_candidates_is_selected():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        assert_evidence_materialization_id_legal({"evidence_source": "derived-candidates"})


def test_evidence_materialization_id_empty_string_refused_when_derived_candidates_is_selected():
    with pytest.raises(EvidenceError, match="evidence_materialization_id"):
        assert_evidence_materialization_id_legal(
            {"evidence_source": "derived-candidates", "evidence_materialization_id": ""}
        )


def test_evidence_materialization_id_accepted_when_derived_candidates_is_selected():
    assert_evidence_materialization_id_legal(
        {"evidence_source": "derived-candidates", "evidence_materialization_id": "mat-1"}
    )


@pytest.mark.parametrize(
    "evidence_source", ["none", "conec-contexts", "conec-names", "conec-bias-list"]
)
def test_evidence_materialization_id_illegal_with_any_other_evidence_source(evidence_source):
    with pytest.raises(EvidenceError, match="only legal with"):
        assert_evidence_materialization_id_legal(
            {"evidence_source": evidence_source, "evidence_materialization_id": "mat-1"}
        )


def test_evidence_materialization_id_illegal_even_with_an_empty_value_under_another_source():
    """Presence alone is illegal -- an empty/falsy value does not exempt a
    stray key from the refusal."""

    with pytest.raises(EvidenceError, match="only legal with"):
        assert_evidence_materialization_id_legal(
            {"evidence_source": "conec-contexts", "evidence_materialization_id": ""}
        )


def test_evidence_materialization_id_absent_key_is_fine_regardless_of_source():
    assert_evidence_materialization_id_legal({"evidence_source": "conec-contexts"})
    assert_evidence_materialization_id_legal({"evidence_source": "none"})
    assert_evidence_materialization_id_legal({})


def test_derived_candidates_is_registered_and_distinct_from_conec_sources(synthetic_world):
    lock = load_lock(synthetic_world.lock_path)
    _write_derived_candidates(synthetic_world.data_root, "mat-test", "4000001", "alpha\n")
    derived_source = EVIDENCE_SOURCES.resolve("derived-candidates")
    contexts_source = EVIDENCE_SOURCES.resolve("conec-contexts")
    names_source = EVIDENCE_SOURCES.resolve("conec-names")
    assert derived_source is not contexts_source
    assert derived_source is not names_source
    derived_item = derived_source(
        lock,
        synthetic_world.data_root,
        "4000001",
        "earnings21-original",
        {"evidence_materialization_id": "mat-test"},
    )[0]
    assert derived_item.content == "alpha\n"
