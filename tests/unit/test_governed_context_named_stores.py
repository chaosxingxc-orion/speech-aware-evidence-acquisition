"""Public named-store integration for source-scoped governed context."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)

SHA = "a" * 64


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _snapshot(name):
    facets = tuple(
        KeyFacet(
            f"f-{parent}",
            "source-scope",
            "parent-sample-id",
            parent,
            (f"ext-{name}-{parent}",),
        )
        for parent in ("parent-a", "parent-b")
    )
    values = tuple(
        ValueBundle(
            f"v-{parent}",
            f"{name} {parent}",
            (f"f-{parent}",),
            (f"ext-{name}-{parent}",),
            ("synthetic",),
        )
        for parent in ("parent-a", "parent-b")
    )
    return KnowledgeSnapshot(
        name,
        SHA,
        tuple(f"ext-{name}-{p}" for p in ("parent-a", "parent-b")),
        "synthetic",
        facets,
        values,
        EXTERNAL_GOVERNED_PARTITION_ROLE,
    ).validate()


def _config(tmp_path, *, phase="decision-2", overlap=False):
    stores = {}
    for name in ("participant-roster", "document-lexicon"):
        snap = _snapshot(name)
        sp = f"k/{name}/snapshot.json"
        (tmp_path / sp).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / sp).write_text(json.dumps(snap.frozen_json()))
        src = f"k/{name}/source.json"
        source_sha = _write(tmp_path / src, {"synthetic": name})
        release = {
            "schema": "saea-knowledge-store-release-v1",
            "store_id": name,
            "store_role": name,
            "snapshot_sha256": snap.content_hash(),
            "source_split_identity_hash": SHA,
            "builder_policy_id": "synthetic",
            "source": {"relpath": src, "sha256": source_sha},
        }
        rp = f"k/{name}/release.json"
        release_sha = _write(tmp_path / rp, release)
        stores[name] = {
            "store_role": name,
            "snapshot": {"relpath": sp, "sha256": snap.content_hash()},
            "release": {"relpath": rp, "sha256": release_sha},
            "context_supply": {phase: {"provider": "source-scoped-context-v1"}},
        }
    if overlap:
        stores["participant-roster"]["phase_supply"] = {phase: {}}
    return {"knowledge_stores": stores}


def _context(parent, window):
    return SimpleNamespace(
        sample_id=parent,
        execution_unit_id=window,
        query_state=QueryState(
            f"q-{window}", parent, f"speech/{parent}", SHA, SHA
        ).validate(),
    )


def test_two_named_stores_automatically_supply_only_current_parent(tmp_path):
    binding = load_knowledge_store_binding(_config(tmp_path), data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding,
        program=default_phase_program("native-answer-or-tool-v1"),
        data_root=tmp_path,
    )
    for window in ("a0", "a1"):
        supply = router.automatic_for_phase("decision-2", _context("parent-a", window))
        assert set(supply.fusion_decision.selected_value_ids) == {
            "participant-roster::v-parent-a",
            "document-lexicon::v-parent-a",
        }
    local = router("participant-roster", "decision-2", _context("parent-b", "b0"))
    assert local.fusion_decision.selected_value_ids == ("v-parent-b",)
    qualified = binding.qualify_supply(
        "participant-roster", local, _context("parent-b", "b0").query_state
    )
    assert qualified.fusion_decision.selected_value_ids == (
        "participant-roster::v-parent-b",
    )
    assert "candidate_supply" not in router.receipt


@pytest.mark.parametrize("phase,overlap", [("decision-1", False), ("decision-2", True)])
def test_named_context_refuses_first_phase_and_overlap(tmp_path, phase, overlap):
    binding = load_knowledge_store_binding(
        _config(tmp_path, phase=phase, overlap=overlap), data_root=tmp_path
    )
    with pytest.raises(KnowledgeStoreError):
        build_knowledge_store_supply(
            binding,
            program=default_phase_program("native-answer-or-tool-v1"),
            data_root=tmp_path,
        )
