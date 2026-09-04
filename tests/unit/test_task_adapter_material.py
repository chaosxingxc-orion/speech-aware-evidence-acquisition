"""``rails.material.PhaseMaterial``: validate() refusals and content_hash()
determinism/sensitivity (C2 consolidation)."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial


def _material(**overrides) -> PhaseMaterial:
    fields = dict(
        instruction="Do the thing.",
        response_format=None,
        contact_id="contact-1",
        purpose="acquire",
    )
    fields.update(overrides)
    return PhaseMaterial(**fields)


def test_valid_material_validates_and_returns_self():
    material = _material()
    assert material.validate() is material


@pytest.mark.parametrize("field", ["instruction", "contact_id", "purpose"])
def test_empty_string_fields_are_refused(field):
    with pytest.raises(RailsError, match=field):
        _material(**{field: ""}).validate()


@pytest.mark.parametrize("field", ["instruction", "contact_id", "purpose"])
def test_whitespace_only_fields_are_refused(field):
    with pytest.raises(RailsError, match=field):
        _material(**{field: "   "}).validate()


@pytest.mark.parametrize("field", ["instruction", "contact_id", "purpose"])
def test_non_string_fields_are_refused(field):
    with pytest.raises(RailsError, match=field):
        _material(**{field: 123}).validate()


def test_response_format_none_is_legal():
    _material(response_format=None).validate()


def test_response_format_mapping_is_legal():
    _material(response_format={"type": "object"}).validate()


def test_response_format_non_mapping_is_refused():
    with pytest.raises(RailsError, match="response_format"):
        _material(response_format=["not", "a", "mapping"]).validate()


def test_content_hash_is_deterministic_and_field_sensitive():
    a = _material()
    b = _material()
    assert a.content_hash() == b.content_hash()

    different_instruction = _material(instruction="Do a different thing.")
    different_contact = _material(contact_id="contact-2")
    different_purpose = _material(purpose="answer")
    different_format = _material(response_format={"type": "object"})
    assert a.content_hash() != different_instruction.content_hash()
    assert a.content_hash() != different_contact.content_hash()
    assert a.content_hash() != different_purpose.content_hash()
    assert a.content_hash() != different_format.content_hash()


def test_content_hash_is_64_lowercase_hex():
    digest = _material().content_hash()
    assert len(digest) == 64
    assert digest == digest.lower()
    int(digest, 16)  # raises ValueError if not hex
