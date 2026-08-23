"""One registry mechanism; boundary-safe evidence items."""

import pytest

from speech_aware_evidence_acquisition.contracts import BoundaryViolation
from speech_aware_evidence_acquisition.core.base import (
    AGENT_CONTROLLERS,
    CoreError,
    EvidenceError,
    EvidenceItem,
    KNOWLEDGE_BUILDERS,
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_RANKERS,
    Registry,
)


def test_registry_registers_resolves_and_fails_closed():
    registry = Registry("widget")
    registry.register("a", 1)
    assert registry.resolve("a") == 1
    assert registry.names() == ["a"]
    with pytest.raises(CoreError, match="duplicate"):
        registry.register("a", 2)
    with pytest.raises(CoreError, match="blank"):
        registry.register("", 3)
    with pytest.raises(CoreError, match="unknown widget 'zz'"):
        registry.resolve("zz")


def test_knowledge_agent_seams_reuse_the_single_registry_mechanism():
    registries = (
        KNOWLEDGE_BUILDERS,
        KNOWLEDGE_RANKERS,
        KNOWLEDGE_FUSERS,
        AGENT_CONTROLLERS,
    )

    assert all(isinstance(registry, Registry) for registry in registries)
    assert len({id(registry) for registry in registries}) == len(registries)


def _item(provenance=None):
    return EvidenceItem(
        evidence_id="ev-1",
        source_uri="conec://earnings21/contexts/4000001.txt",
        content="context text",
        provenance=provenance
        or {"lock_key": "conec", "relpath": "earnings21/contexts/4000001.txt", "sha256": "0" * 64},
    )


def test_evidence_item_validates_and_projects_views():
    item = _item().validate()
    assert set(item.runtime_view()) == {"evidence_id", "source_uri", "content"}
    assert set(item.provenance_view()) == {"lock_key", "relpath", "sha256"}


def test_evidence_item_refuses_missing_provenance_keys():
    with pytest.raises(EvidenceError, match="provenance"):
        _item(provenance={"lock_key": "conec"}).validate()


def test_evidence_item_refuses_forbidden_field_smuggling():
    bad = _item(
        provenance={"lock_key": "conec", "relpath": "r", "sha256": "0" * 64, "reference": "x"}
    )
    with pytest.raises(BoundaryViolation):
        bad.validate()
