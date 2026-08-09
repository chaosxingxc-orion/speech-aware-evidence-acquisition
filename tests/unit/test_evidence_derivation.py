"""core.evidence_derivation: pinned/versioned transforms + the registry that
re-verifies a DerivedEvidenceRecord before its content is trusted
(docs/readiness/2026-08-09-conec-evidence-shape.md "Blocking gap").

These tests exercise the mechanism directly (hand-built records, a tiny local
transform for the registry-behaviour probes) -- source-specific happy-path /
wiring coverage for conec-contexts/conec-bias-list/distractor-only-bias-list
lives in test_core_components.py / test_bias_lists.py / test_driver.py.
"""

import hashlib
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.base import DerivedEvidenceRecord
from speech_aware_evidence_acquisition.core.evidence_derivation import (
    TRANSFORMS,
    DerivedEvidenceError,
    DerivedEvidenceRegistry,
    TransformRegistry,
    canonical_params_hash,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# DerivedEvidenceRecord -- the exact shape (deliverable 1)
# ---------------------------------------------------------------------------


def test_derived_evidence_record_shape_and_trace_view():
    record = DerivedEvidenceRecord(
        sample_id="s1",
        source_relpath="datasets/x/y.txt",
        source_sha256=_sha("hello world"),
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256=_sha("hello world"),
    )
    assert record.carrier_bound is True  # default
    assert record.trace_view() == {
        "sample_id": "s1",
        "source_relpath": "datasets/x/y.txt",
        "source_sha256": _sha("hello world"),
        "transform_name": "identity",
        "transform_version": "v1",
        "params_hash": canonical_params_hash({}),
        "derived_sha256": _sha("hello world"),
        "carrier_bound": True,
    }


def test_derived_evidence_record_can_declare_no_carrier_binding():
    record = DerivedEvidenceRecord(
        sample_id="s1",
        source_relpath="a.txt+b.txt",
        source_sha256=_sha("combined"),
        transform_name="distractor-only",
        transform_version="v1",
        params_hash=canonical_params_hash({"max_entries": 5}),
        derived_sha256=_sha("output"),
        carrier_bound=False,
    )
    assert record.carrier_bound is False
    assert record.trace_view()["carrier_bound"] is False


# ---------------------------------------------------------------------------
# canonical_params_hash
# ---------------------------------------------------------------------------


def test_canonical_params_hash_is_order_independent():
    assert canonical_params_hash({"b": 2, "a": 1}) == canonical_params_hash({"a": 1, "b": 2})


def test_canonical_params_hash_differs_for_different_params():
    assert canonical_params_hash({"max_entries": 5}) != canonical_params_hash({"max_entries": 6})


def test_canonical_params_hash_rejects_a_non_mapping():
    with pytest.raises(DerivedEvidenceError, match="mapping"):
        canonical_params_hash("not-a-mapping")


# ---------------------------------------------------------------------------
# TransformRegistry: an unregistered or unversioned transform must be
# impossible to use (deliverable 5)
# ---------------------------------------------------------------------------


def _upper(text: str, params) -> str:
    return text.upper()


def test_transform_registry_registers_and_resolves():
    registry = TransformRegistry()
    registry.register("upper", "v1", _upper)
    spec = registry.resolve("upper", "v1")
    assert spec.apply("abc", {}) == "ABC"


def test_transform_registry_refuses_an_unregistered_name():
    registry = TransformRegistry()
    with pytest.raises(DerivedEvidenceError, match="unregistered transform"):
        registry.resolve("never-registered", "v1")


def test_transform_registry_refuses_a_mismatched_version():
    registry = TransformRegistry()
    registry.register("upper", "v1", _upper)
    with pytest.raises(DerivedEvidenceError, match="does not match the pinned"):
        registry.resolve("upper", "v2")


def test_transform_registry_refuses_resolving_with_a_blank_version():
    registry = TransformRegistry()
    registry.register("upper", "v1", _upper)
    with pytest.raises(DerivedEvidenceError, match="does not match the pinned"):
        registry.resolve("upper", "")


@pytest.mark.parametrize("bad_version", ["", "1", "version-one", "v", "v-1"])
def test_transform_registry_refuses_registering_an_unversioned_transform(bad_version):
    registry = TransformRegistry()
    with pytest.raises(DerivedEvidenceError, match="version"):
        registry.register("upper", bad_version, _upper)


def test_transform_registry_refuses_duplicate_names():
    registry = TransformRegistry()
    registry.register("upper", "v1", _upper)
    with pytest.raises(DerivedEvidenceError, match="duplicate"):
        registry.register("upper", "v1", _upper)


def test_transform_registry_refuses_a_non_callable_apply():
    registry = TransformRegistry()
    with pytest.raises(DerivedEvidenceError, match="callable"):
        registry.register("upper", "v1", "not-callable")


def test_transform_registry_refuses_a_malformed_name():
    registry = TransformRegistry()
    with pytest.raises(DerivedEvidenceError, match="transform name"):
        registry.register("Not Valid!", "v1", _upper)


def test_transform_registry_names_are_sorted():
    registry = TransformRegistry()
    registry.register("zeta", "v1", _upper)
    registry.register("alpha", "v1", _upper)
    assert registry.names() == ["alpha", "zeta"]


def test_the_shared_transforms_singleton_carries_the_permanent_identity_transform():
    assert "identity" in TRANSFORMS.names()
    spec = TRANSFORMS.resolve("identity", "v1")
    assert spec.apply("unchanged", {}) == "unchanged"


def test_identity_transform_is_deterministic_across_independent_calls():
    spec_a = TRANSFORMS.resolve("identity", "v1")
    spec_b = TRANSFORMS.resolve("identity", "v1")
    assert spec_a.apply("hello world", {}) == spec_b.apply("hello world", {})


# ---------------------------------------------------------------------------
# DerivedEvidenceRegistry.register -- happy path + the four failure modes
# (deliverable 2/6)
# ---------------------------------------------------------------------------


def _identity_record(sample_id: str = "s1", source_text: str = "hello world", **overrides):
    source_bytes = source_text.encode("utf-8")
    fields = {
        "sample_id": sample_id,
        "source_relpath": "datasets/x/y.txt",
        "source_sha256": _sha(source_text),
        "transform_name": "identity",
        "transform_version": "v1",
        "params_hash": canonical_params_hash({}),
        "derived_sha256": _sha(source_text),
    }
    fields.update(overrides)
    return DerivedEvidenceRecord(**fields), source_bytes


def test_register_happy_path_accepts_a_correct_chain():
    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record()
    registered = registry.register(
        record, source_content=source_bytes, derived_content=source_bytes, params={}
    )
    assert registered is record
    assert registry.lookup("s1", "identity") is record
    assert registry.lookup("s1", "no-such-transform") is None
    assert registry.lookup("unknown-sample", "identity") is None


def test_register_refuses_a_tampered_source():
    """The link named SOURCE breaks: the bytes this run actually read do not
    hash to what the record claims (a tampered or substituted source)."""

    registry = DerivedEvidenceRegistry()
    record, _ = _identity_record()
    with pytest.raises(DerivedEvidenceError, match="broke at SOURCE"):
        registry.register(
            record,
            source_content=b"totally different bytes, not the real source",
            derived_content=b"hello world",
            params={},
        )


def test_register_refuses_tampered_bytes_about_to_be_sent():
    """The link named SENT CONTENT breaks: the record's own numbers are
    internally consistent, but the bytes this run will actually send were
    tampered after derivation."""

    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record()
    with pytest.raises(DerivedEvidenceError, match="broke at SENT CONTENT"):
        registry.register(
            record,
            source_content=source_bytes,
            derived_content=b"tampered after derivation, not what was derived",
            params={},
        )


def test_register_refuses_a_wrong_params_hash():
    """The link named PARAMS breaks: the record claims params the caller's
    (config-declared) params disagree with."""

    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record()  # record's params_hash claims {}
    with pytest.raises(DerivedEvidenceError, match="broke at PARAMS"):
        registry.register(
            record,
            source_content=source_bytes,
            derived_content=source_bytes,
            params={"max_entries": 5},
        )


def test_register_refuses_an_unregistered_transform():
    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record(transform_name="never-registered-transform")
    with pytest.raises(DerivedEvidenceError, match="unregistered transform"):
        registry.register(
            record, source_content=source_bytes, derived_content=source_bytes, params={}
        )


def test_register_refuses_a_registered_transform_at_the_wrong_pinned_version():
    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record(transform_version="v2")
    with pytest.raises(DerivedEvidenceError, match="does not match the pinned"):
        registry.register(
            record, source_content=source_bytes, derived_content=source_bytes, params={}
        )


def test_register_refuses_a_record_whose_derived_sha256_the_transform_cannot_reproduce():
    """The link named DERIVED CONTENT breaks: re-invoking the pinned
    transform on the (verified) source with the (verified) params does not
    reproduce the hash the record itself claims -- distinct from the
    SENT-CONTENT probe above, which tampers the bytes actually sent rather
    than the record's own claim."""

    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record()
    tampered_record = replace(record, derived_sha256="0" * 64)
    with pytest.raises(DerivedEvidenceError, match="broke at DERIVED CONTENT"):
        registry.register(
            tampered_record,
            source_content=source_bytes,
            derived_content=b"irrelevant, refused before this is even reached",
            params={},
        )


def test_register_refuses_duplicate_registration_for_the_same_sample_and_transform():
    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record()
    registry.register(record, source_content=source_bytes, derived_content=source_bytes, params={})
    with pytest.raises(DerivedEvidenceError, match="already registered"):
        registry.register(
            record, source_content=source_bytes, derived_content=source_bytes, params={}
        )


def test_register_rejects_a_non_record():
    registry = DerivedEvidenceRegistry()
    with pytest.raises(DerivedEvidenceError, match="DerivedEvidenceRecord"):
        registry.register("not-a-record", source_content=b"x", derived_content=b"x", params={})


@pytest.mark.parametrize("bad_sha", ["", "not-hex-at-all", "0" * 63, "G" * 64])
def test_register_rejects_a_malformed_source_sha256(bad_sha):
    registry = DerivedEvidenceRegistry()
    record, source_bytes = _identity_record(source_sha256=bad_sha)
    with pytest.raises(DerivedEvidenceError, match="sha256 hex digest"):
        registry.register(
            record, source_content=source_bytes, derived_content=source_bytes, params={}
        )


def test_register_rejects_empty_source_content():
    registry = DerivedEvidenceRegistry()
    record, _ = _identity_record()
    with pytest.raises(DerivedEvidenceError, match="non-empty bytes"):
        registry.register(record, source_content=b"", derived_content=b"x", params={})


def test_register_rejects_source_content_that_is_not_valid_utf8():
    """The source-hash self-check must pass first (matching source_sha256 to
    the malformed bytes) for the UTF-8 decode failure to be the thing that
    actually fires -- otherwise this would just re-probe the SOURCE link."""

    registry = DerivedEvidenceRegistry()
    bad_bytes = b"\xff\xfe"
    record = DerivedEvidenceRecord(
        sample_id="s1",
        source_relpath="datasets/x/y.txt",
        source_sha256=hashlib.sha256(bad_bytes).hexdigest(),
        transform_name="identity",
        transform_version="v1",
        params_hash=canonical_params_hash({}),
        derived_sha256="0" * 64,
    )
    with pytest.raises(DerivedEvidenceError, match="not valid UTF-8"):
        registry.register(record, source_content=bad_bytes, derived_content=b"x", params={})
