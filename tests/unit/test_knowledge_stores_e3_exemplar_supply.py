"""E3 fix: a named store's plain, LATER-phase ``phase_supply`` must actually
be consulted by ``automatic_for_phase`` once something else (context_supply
or candidate_supply) already earns the router a dispatcher -- and must stay
silent, exactly as before, when nothing else does.
"""

from __future__ import annotations

import hashlib
import json

from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)

from test_governed_context_named_stores import _config as _context_config
from test_governed_context_named_stores import _context, _snapshot
from test_knowledge_stores import _config as _plain_config


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _plain_store_on_parent_ids(tmp_path, *, phase="decision-2"):
    """A third named store, KU-S3-shaped (kb-facet-v1 / plain phase_supply),
    keyed on the SAME 'parent-a'/'parent-b' sample ids
    ``test_governed_context_named_stores._context`` uses, so it can be
    exercised in the SAME call as that module's two context-scoped stores."""

    store_id = "train-exemplars-like"
    snapshot = _snapshot(store_id)
    snapshot_relpath = f"k/{store_id}/snapshot.json"
    (tmp_path / snapshot_relpath).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / snapshot_relpath).write_text(json.dumps(snapshot.frozen_json()))
    source_relpath = f"k/{store_id}/source.json"
    source_sha = _write(tmp_path / source_relpath, {"synthetic": store_id})
    release = {
        "schema": "saea-knowledge-store-release-v1",
        "store_id": store_id,
        "store_role": store_id,
        "snapshot_sha256": snapshot.content_hash(),
        "source_split_identity_hash": "a" * 64,
        "builder_policy_id": "synthetic",
        "source": {"relpath": source_relpath, "sha256": source_sha},
    }
    release_relpath = f"k/{store_id}/release.json"
    release_sha = _write(tmp_path / release_relpath, release)

    query_relpath = f"k/{store_id}/query.jsonl"
    facet_relpath = f"k/{store_id}/facets.jsonl"
    query_lines = "\n".join(
        json.dumps({"id": parent, "vectors": {"source-scope": [1.0]}})
        for parent in ("parent-a", "parent-b")
    )
    (tmp_path / query_relpath).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / query_relpath).write_bytes(query_lines.encode())
    query_sha = hashlib.sha256(query_lines.encode()).hexdigest()
    facet_lines = "\n".join(
        json.dumps({"id": facet.facet_id, "vectors": {"source-scope": [1.0]}})
        for facet in snapshot.facets
    )
    (tmp_path / facet_relpath).write_bytes(facet_lines.encode())
    facet_sha = hashlib.sha256(facet_lines.encode()).hexdigest()

    def source(relpath, sha, signal):
        return {
            "kind": "sealed-vectors",
            "relpath": relpath,
            "sha256": sha,
            "tool_contact_ledger_row": "SYNTHETIC-NO-CONTACT",
            "embedded_signal": signal,
        }

    supply = {
        "provider": "kb-facet-v1",
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-associated-values-v1",
        # saea-fuse-supplyfilter-v1 (the E3 store's OWN production fuse
        # policy, already verified against real, task_target-bearing
        # exemplar values by scripts/estimate_slurp_exemplar_prompt_fit.py's
        # real-provider cross-check) requires an answer-bearing
        # ValueBundle.task_target; this synthetic fixture's values (borrowed
        # from test_governed_context_named_stores._snapshot) carry none, so
        # this test uses the sibling fuser that "supplies associated content
        # without requiring an answer-bearing target" (its own docstring) --
        # a fixture-only substitution, not a claim about the production
        # store's own fuse policy.
        "k": 1,
        "tau": 0.0,
        "dimensions": ["source-scope"],
        "fuse_coverage": {"m": 1, "c": 1, "top_l": 1},
        "query_source": source(query_relpath, query_sha, "speech: synthetic query"),
        "facet_source": source(facet_relpath, facet_sha, "text: synthetic facet"),
    }
    store = {
        "store_role": store_id,
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {"relpath": release_relpath, "sha256": release_sha},
        "phase_supply": {phase: supply},
    }
    return store_id, store, snapshot


def test_plain_later_phase_supply_composes_alongside_context_supply(tmp_path):
    """The E3 fix: once context_supply already earns ``automatic_for_phase``
    a dispatcher, a DIFFERENT store's plain phase_supply on the SAME later
    phase is now consulted too, and its value is composed into the result
    alongside the context-scoped stores' own values -- in the SAME call, for
    the SAME sample."""

    config = _context_config(tmp_path, phase="decision-2")
    plain_store_id, plain_store, plain_snapshot = _plain_store_on_parent_ids(tmp_path)
    config["knowledge_stores"][plain_store_id] = plain_store

    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=default_phase_program("native-answer-or-tool-v1"),
        data_root=tmp_path,
    )
    assert hasattr(router, "automatic_for_phase")

    supply = router.automatic_for_phase("decision-2", _context("parent-a", "a0"))
    selected = set(supply.fusion_decision.selected_value_ids)

    # The two context-scoped stores' own values (unchanged behavior).
    assert "participant-roster::v-parent-a" in selected
    assert "document-lexicon::v-parent-a" in selected
    # The E3 fix: the plain phase_supply store's value is now ALSO composed
    # in, where before this loop never called route() for it at all.
    plain_value_id = plain_snapshot.values[0].value_id
    assert f"{plain_store_id}::{plain_value_id}" in selected
    assert supply.fusion_decision.snapshot_sha256 == binding.binding_sha256


def test_plain_later_phase_supply_alone_still_yields_no_dispatcher(tmp_path):
    """DELIBERATELY UNCHANGED (module docstring in rails/knowledge_stores.py):
    a config whose stores declare later-phase phase_supply and NOTHING ELSE
    (no context_supply, no candidate_supply anywhere) still gets no
    ``automatic_for_phase`` at all -- exactly what
    test_knowledge_stores.test_real_request_gate_retains_exact_qualified_
    store_evidence already pins, reproduced here as an independent,
    single-purpose regression guard."""

    plain_document, _snapshots = _plain_config(tmp_path)
    binding = load_knowledge_store_binding(plain_document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=default_phase_program("native-answer-or-tool-v1"),
        data_root=tmp_path,
    )
    assert not hasattr(router, "automatic_for_phase")
