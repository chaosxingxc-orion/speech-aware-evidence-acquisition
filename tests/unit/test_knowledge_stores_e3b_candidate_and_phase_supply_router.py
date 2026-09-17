"""E3b (SLURP v2 base program M1 / cell B1): the reviewed fix for the E3
store-router guard (``rails.knowledge_stores.build_knowledge_store_supply``)
that refused a candidate supply and a DIFFERENT store's plain, later-phase
``phase_supply`` on the same phase -- exactly this program's anchor case,
``slot-contracts`` ``candidate_supply.solver`` alongside ``train-exemplars``
``phase_supply.solver``.

The blocker receipt (``$SPEECHRL_DATA_DIR/coordination/
slurp-b1-exemplars-k20-v1/store-router-blocker-v1.json``) diagnosed a
sufficient but IMPRECISE fix: narrowing the collision test against
``candidate_specs`` to the program's first phase for a store's own explicit
``phase_supply``, while leaving ``scoped_phases`` (context_supply) checked
unconditionally on every phase. That formula also permits a store's
``phase_supply`` to coexist with its OWN ``candidate_supply`` on the very
same later phase -- never proven safe and never the case this program
needs. This module tests the four precise rules the reviewed fix
implements instead:

1. A candidate supply and a plain phase supply from DIFFERENT stores may
   coexist on a non-first phase (the new admission).
2. The first phase still refuses any overlap (defensive; structurally
   unreachable today via the public candidate_supply API, proven anyway by
   forging the mapping ``build_knowledge_store_supply`` reads).
3. Explicit/scoped overlaps that were refused before stay refused: a
   store's own phase_supply against its OWN candidate_supply on the same
   later phase, and a scoped (context_supply) overlap against ANY store's
   candidate_supply on ANY phase.
4. Two stores both claiming candidate supply on one phase stay refused
   (enforced upstream, in ``load_candidate_semantic_supply_specs``,
   unaffected by this fix; reproduced here as a regression guard).

It also tests the dispatch-time composition the blocker receipt left
"still unproven": that ``rails.knowledge_stores._compose_supplies``, reached
only through ``router.automatic_for_phase``, actually accepts the candidate
supply alongside the plain exemplar supply and merges both into one
``PhaseSupply``, in cosine rank order, store-prefixed, with the exact
configured k.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
    CandidateSemanticSupplyError,
)
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)

from test_candidate_semantic_supply import (
    _artifact,
    _config as _candidate_config,
    _context as _candidate_context,
    _program as _candidate_program,
    _slot_row,
    _store,
)
SHA_A = "a" * 64


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _source(relpath, sha, signal):
    return {
        "kind": "sealed-vectors",
        "relpath": relpath,
        "sha256": sha,
        "tool_contact_ledger_row": "SYNTHETIC-NO-CONTACT",
        "embedded_signal": signal,
    }


def _plain_phase_supply_store(
    tmp_path,
    *,
    phase,
    store_id="train-exemplars-like",
    sample_id="s1",
    facets=(("ex1", (1.0, 0.0)), ("ex2", (0.7, 0.7)), ("ex3", (0.0, 1.0))),
    query_vector=(1.0, 0.0),
    k=None,
):
    """A KU-S3/train-exemplars-shaped plain store: kb-facet-v1 provider,
    dimension 'content', keyed on the SAME sample id the candidate test's
    ``_context`` helper uses. ``facets`` is ``(local_id, vector)`` pairs.
    Vectors are 2-D and compared to ``query_vector`` by COSINE similarity
    (angle, not magnitude -- a 1-D vector space cannot separate facets by
    score at all, since every nonzero 1-D vector has cosine +/-1 against any
    other), so distinct facets must point in genuinely different
    directions to get a genuinely different, checkable rank order."""

    snapshot_facets = tuple(
        KeyFacet(f"f-{local_id}", "content", "synthetic", f"{store_id} facet {local_id}", ("train-1",))
        for local_id, _vector in facets
    )
    snapshot_values = tuple(
        ValueBundle(f"v-{local_id}", f"{store_id} exemplar {local_id}", (f"f-{local_id}",), ("train-1",), ("synthetic",))
        for local_id, _vector in facets
    )
    snapshot = KnowledgeSnapshot(
        store_id, SHA_A, ("train-1",), "synthetic", snapshot_facets, snapshot_values,
    ).validate()
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
        "source_split_identity_hash": SHA_A,
        "builder_policy_id": "synthetic",
        "source": {"relpath": source_relpath, "sha256": source_sha},
    }
    release_relpath = f"k/{store_id}/release.json"
    release_sha = _write(tmp_path / release_relpath, release)

    query_relpath = f"k/{store_id}/query.jsonl"
    query_line = json.dumps({"id": sample_id, "vectors": {"content": list(query_vector)}})
    (tmp_path / query_relpath).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / query_relpath).write_bytes(query_line.encode())
    query_sha = hashlib.sha256(query_line.encode()).hexdigest()

    facet_relpath = f"k/{store_id}/facets.jsonl"
    facet_lines = "\n".join(
        json.dumps({"id": f"f-{local_id}", "vectors": {"content": list(vector)}})
        for local_id, vector in facets
    )
    (tmp_path / facet_relpath).write_bytes(facet_lines.encode())
    facet_sha = hashlib.sha256(facet_lines.encode()).hexdigest()

    kk = k if k is not None else len(facets)
    supply = {
        "provider": "kb-facet-v1",
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-associated-values-v1",
        "k": kk,
        "tau": 0.0,
        "dimensions": ["content"],
        "fuse_coverage": {"m": kk, "c": kk, "top_l": kk},
        "query_source": _source(query_relpath, query_sha, "speech: synthetic query"),
        "facet_source": _source(facet_relpath, facet_sha, "text: synthetic facet"),
    }
    store_doc = {
        "store_role": store_id,
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {"relpath": release_relpath, "sha256": release_sha},
        "phase_supply": {phase: supply},
    }
    return store_id, store_doc, snapshot


# ---------------------------------------------------------------------------
# Rule 1 + dispatch proof: a candidate supply and a DIFFERENT store's plain
# phase_supply on the same non-first phase now compose.
# ---------------------------------------------------------------------------


def test_candidate_supply_and_a_different_stores_phase_supply_compose_on_a_later_phase(
    tmp_path,
):
    document, inventory = _candidate_config(tmp_path)
    plain_id, plain_store, plain_snapshot = _plain_phase_supply_store(
        tmp_path, phase="solve", facets=(("ex1", (1.0, 0.0)),)
    )
    document["knowledge_stores"][plain_id] = plain_store

    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=inventory,
    )
    assert hasattr(router, "automatic_for_phase")

    context = _candidate_context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    supply = router.automatic_for_phase("solve", context)
    selected = supply.fusion_decision.selected_value_ids

    # automatic_for_phase composes context-scoped supplies, then plain
    # later-phase phase_supply stores, then the candidate supply LAST -- so
    # the plain exemplar store's value leads and the candidate cards follow
    # (unchanged single-store order, matching test_candidate_semantic_
    # supply.py's own equivalent call).
    assert selected[0] == f"{plain_id}::{plain_snapshot.values[0].value_id}"
    assert selected[1:] == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
        "slot-contracts::slot-contract:gamma_one",
    )
    # The E3b fix, restated: BOTH supplies are present in the SAME composed
    # decision, where the pre-fix guard refused router construction
    # outright the moment both a candidate_supply and a different store's
    # phase_supply named the same phase.
    assert any(v.startswith("slot-contracts::") for v in selected)
    assert supply.fusion_decision.snapshot_sha256 == binding.binding_sha256


def test_composed_decision_carries_only_opaque_ids_never_exemplar_payload_text(
    tmp_path,
):
    """Defect 2's instruction-safety claim: the composed PhaseSupply that
    reaches a phase's ``QueryState`` (and from there the acquire transition)
    carries only store-prefixed VALUE IDS -- never the exemplar's rendered
    text. Turning an id into model-facing text is a SEPARATE, explicit step
    (``KnowledgeValueRenderer.assemble``/``model_evidence_block``), never
    something ``automatic_for_phase``/``_compose_supplies`` does, and never
    something an instruction template touches (``rails.controllers``'
    "Traced supply": a supplied phase's instruction is byte-identical to
    the same phase's unsupplied one)."""

    document, inventory = _candidate_config(tmp_path)
    plain_id, plain_store, plain_snapshot = _plain_phase_supply_store(
        tmp_path, phase="solve", facets=(("ex1", (1.0, 0.0)),)
    )
    document["knowledge_stores"][plain_id] = plain_store
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=inventory,
    )
    context = _candidate_context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    supply = router.automatic_for_phase("solve", context)

    # PhaseSupply itself: rank_result/fusion_decision carry hashes and ID
    # tuples only -- no free-form text field exists to leak a payload into.
    assert supply.packet is None
    exemplar_text = plain_snapshot.values[0].content
    for value_id in supply.fusion_decision.selected_value_ids:
        assert isinstance(value_id, str)
        assert exemplar_text not in value_id
    for candidate in supply.rank_result.candidates:
        assert exemplar_text not in candidate.facet_id

    # Turning the exemplar's id into text is a distinct, explicit call --
    # never invoked by automatic_for_phase itself.
    from speech_aware_evidence_acquisition.rails.knowledge_value_views import (
        KnowledgeValueRenderer,
    )

    plain_value_id = f"{plain_id}::{plain_snapshot.values[0].value_id}"
    assert plain_value_id in supply.fusion_decision.selected_value_ids
    blocks = KnowledgeValueRenderer(binding.composite_snapshot).assemble(
        (plain_value_id,)
    )
    assert len(blocks) == 1
    assert blocks[0]["text"] == exemplar_text


def test_exemplar_supply_composes_in_cosine_order_with_store_prefix_and_exact_k(
    tmp_path,
):
    """Defect 2 detail: k exemplar typed-content blocks, store-prefixed, in
    cosine rank order -- not just "present somewhere in the selection"."""

    document, inventory = _candidate_config(tmp_path)
    # Query vector (1.0, 0.0); facets at increasing angles from it, so
    # cosine similarity strictly decreases low-angle-first: high ~0.99,
    # mid ~0.707, low ~0.10.
    facets = (("low", (0.1, 0.995)), ("high", (0.99, 0.141)), ("mid", (0.7, 0.7)))
    plain_id, plain_store, plain_snapshot = _plain_phase_supply_store(
        tmp_path, phase="solve", facets=facets, k=3
    )
    document["knowledge_stores"][plain_id] = plain_store
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=inventory,
    )
    context = _candidate_context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    supply = router.automatic_for_phase("solve", context)
    selected = supply.fusion_decision.selected_value_ids

    plain_selected = [value_id for value_id in selected if value_id.startswith(f"{plain_id}::")]
    assert len(plain_selected) == 3
    # Cosine rank order: highest score first.
    assert plain_selected == [
        f"{plain_id}::v-high",
        f"{plain_id}::v-mid",
        f"{plain_id}::v-low",
    ]
    # Every candidate card still present, unaffected by store order.
    assert sum(1 for value_id in selected if value_id.startswith("slot-contracts::")) == 3


# ---------------------------------------------------------------------------
# Rule 3: same-store candidate_supply + phase_supply on the same later phase
# stays refused (the refinement over the blocker receipt's diagnosed fix,
# which did not distinguish store identity).
# ---------------------------------------------------------------------------


def test_same_store_candidate_and_phase_supply_on_the_same_later_phase_still_refused(
    tmp_path,
):
    document, inventory = _candidate_config(tmp_path)
    # Attach a phase_supply.solve entry directly onto the SAME store that
    # already declares candidate_supply.solve.
    _plain_id, plain_store, _snap = _plain_phase_supply_store(
        tmp_path, phase="solve", store_id="slot-contracts-solo-check",
    )
    document["knowledge_stores"]["slot-contracts"]["phase_supply"] = plain_store[
        "phase_supply"
    ]
    # Reuse the same store's own snapshot/release pins (the phase_supply
    # dict itself does not reference the snapshot, only its own vector
    # files, so this is a legal same-store attachment).
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    with pytest.raises(KnowledgeStoreError, match=r"phase\(s\) \['solve'\]"):
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=inventory,
        )


# ---------------------------------------------------------------------------
# Rule 3 (continued): scoped (context_supply) and candidate supply from
# DIFFERENT stores still refused on any phase -- unchanged by this fix,
# which only widens the EXPLICIT phase_supply branch.
# ---------------------------------------------------------------------------


def test_scoped_context_supply_and_candidate_supply_cross_store_still_refused(tmp_path):
    # A 3-phase program so context_supply (never allowed on the first
    # phase) and the candidate supply's later target phase can be the SAME
    # non-first phase: intake (first, none) -> hypotheses (none) -> decide
    # (supplied, both context_supply and candidate_supply target it).
    program = PhaseProgram(
        program_id="synthetic-context-and-candidate-collision-v1",
        phases=(
            PhaseSpec("hypotheses", "propose", "none", None, False),
            PhaseSpec("decide", "decide", "supplied", None, False),
        ),
        max_contacts=2,
        stop_rule="always-run-full-program",
    ).validate()

    # Both this store's snapshot and the context store's snapshot below are
    # EXTERNAL_GOVERNED_PARTITION_ROLE: SourceScopedContextProvider (the
    # context_supply provider) refuses anything else, and _composite()
    # refuses a binding whose stores disagree on partition role -- so a
    # config that combines context_supply and candidate_supply at all must
    # put BOTH stores on that same role, unlike this program's own anchor
    # (default TRAIN throughout, no context_supply store).
    rows = (_slot_row("shared", ("alpha", "beta")),)
    slot_snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp", source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=("train-1",),
            source_partition_role="external-governed",
        ),
        rows=rows,
    )
    slot_source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": slot_snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(rows),
    }
    slot_store = _store(tmp_path, "slot-contracts", "slot-contracts", slot_snapshot, slot_source)
    slot_store["candidate_supply"] = {
        "decide": {
            "provider": "slurp-candidate-semantic-v1",
            "rank_policy": "saea-ranked-candidate-round-robin-v1",
            "fuse_policy": "saea-candidate-semantic-passthrough-v1",
            "candidate_state_phase": "hypotheses",
            "max_candidates": 2,
            "max_values_per_candidate": 1,
            "max_total_values": 2,
        }
    }
    # A minimal source-scoped context_supply store on the SAME "decide"
    # phase, built by hand rather than reusing test_governed_context_
    # named_stores._config, just to keep this module's own fixtures
    # self-contained.
    context_store_id = "context-like"
    context_facet = KeyFacet(
        f"f-{context_store_id}", "source-scope", "parent-sample-id", "s1",
        (f"ext-{context_store_id}",),
    )
    context_value = ValueBundle(
        f"v-{context_store_id}", f"{context_store_id} content",
        (context_facet.facet_id,), (f"ext-{context_store_id}",), ("synthetic",),
    )
    context_snapshot = KnowledgeSnapshot(
        context_store_id, SHA_A, (f"ext-{context_store_id}",), "synthetic",
        (context_facet,), (context_value,), EXTERNAL_GOVERNED_PARTITION_ROLE,
    ).validate()
    context_snapshot_relpath = f"k/{context_store_id}/snapshot.json"
    (tmp_path / context_snapshot_relpath).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / context_snapshot_relpath).write_text(json.dumps(context_snapshot.frozen_json()))
    context_source_relpath = f"k/{context_store_id}/source.json"
    context_source_sha = _write(tmp_path / context_source_relpath, {"synthetic": context_store_id})
    context_release = {
        "schema": "saea-knowledge-store-release-v1",
        "store_id": context_store_id,
        "store_role": context_store_id,
        "snapshot_sha256": context_snapshot.content_hash(),
        "source_split_identity_hash": SHA_A,
        "builder_policy_id": "synthetic",
        "source": {"relpath": context_source_relpath, "sha256": context_source_sha},
    }
    context_release_relpath = f"k/{context_store_id}/release.json"
    context_release_sha = _write(tmp_path / context_release_relpath, context_release)
    context_store = {
        "store_role": context_store_id,
        "snapshot": {"relpath": context_snapshot_relpath, "sha256": context_snapshot.content_hash()},
        "release": {"relpath": context_release_relpath, "sha256": context_release_sha},
        "context_supply": {"decide": {"provider": "source-scoped-context-v1"}},
    }
    document = {
        "knowledge_stores": {
            "slot-contracts": slot_store,
            context_store_id: context_store,
        }
    }
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    with pytest.raises(KnowledgeStoreError, match=r"phase\(s\) \['decide'\]"):
        build_knowledge_store_supply(
            binding, program=program, data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


# ---------------------------------------------------------------------------
# Rule 4: two stores both claiming candidate supply on one phase stay
# refused. Enforced upstream in load_candidate_semantic_supply_specs and
# unaffected by this fix; reproduced here as a regression guard so a future
# change to the per-store guard cannot silently reopen it.
# ---------------------------------------------------------------------------


def test_two_stores_both_claiming_candidate_supply_on_one_phase_still_refused(tmp_path):
    document, inventory = _candidate_config(tmp_path)
    second_rows = (_slot_row("shared", ("alpha", "beta")),)
    second_snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp", source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=second_rows,
    )
    second_source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": second_snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(second_rows),
    }
    second_store = _store(
        tmp_path, "slot-contracts-2", "slot-contracts", second_snapshot, second_source
    )
    second_store["candidate_supply"] = dict(
        document["knowledge_stores"]["slot-contracts"]["candidate_supply"]
    )
    document["knowledge_stores"]["slot-contracts-2"] = second_store
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="multiple candidate stores"):
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=inventory,
        )


# ---------------------------------------------------------------------------
# Rule 2: the first phase still refuses any overlap. Structurally
# unreachable today via the public candidate_supply API (a candidate
# supply's phase must be strictly later than its own candidate_state_phase,
# so candidate_specs can never key the first phase) -- proven anyway by
# forging the mapping build_knowledge_store_supply reads, so the guard does
# not silently rely on that invariant holding forever.
# ---------------------------------------------------------------------------


def test_first_phase_overlap_with_candidate_supply_stays_refused_even_if_forged(
    tmp_path, monkeypatch,
):
    import speech_aware_evidence_acquisition.rails.candidate_semantic_supply as css_module

    program = PhaseProgram(
        program_id="synthetic-supplied-intake-then-solve-v1",
        phases=(
            PhaseSpec("intake", "observe", "supplied", None, False),
            PhaseSpec("solve", "solve", "supplied", None, False),
        ),
        max_contacts=2,
        stop_rule="always-run-full-program",
    ).validate()

    rows = (_slot_row("shared", ("alpha", "beta")),)
    slot_snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp", source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=rows,
    )
    slot_source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": slot_snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(rows),
    }
    store_doc = _store(tmp_path, "slot-contracts", "slot-contracts", slot_snapshot, slot_source)
    store_doc["candidate_supply"] = {
        "solve": {
            "provider": "slurp-candidate-semantic-v1",
            "rank_policy": "saea-ranked-candidate-round-robin-v1",
            "fuse_policy": "saea-candidate-semantic-passthrough-v1",
            "candidate_state_phase": "intake",
            "max_candidates": 2,
            "max_values_per_candidate": 1,
            "max_total_values": 2,
        }
    }
    # This same store ALSO declares a plain phase_supply on the FIRST
    # phase, the normal Perception-style retrieval route (never read: the
    # guard is expected to raise first).
    store_doc["phase_supply"] = {
        "intake": {
            "provider": "kb-facet-v1",
            "rank_policy": "saea-rank-wcos-prior-agree-v1",
            "fuse_policy": "saea-fuse-associated-values-v1",
            "k": 1,
            "tau": 0.0,
            "dimensions": ["content"],
            "fuse_coverage": {"m": 1, "c": 1, "top_l": 1},
            "query_source": _source("unused/query.jsonl", "a" * 64, "speech: unread dummy"),
            "facet_source": _source("unused/facets.jsonl", "a" * 64, "text: unread dummy"),
        }
    }
    document = {"knowledge_stores": {"slot-contracts": store_doc}}
    binding = load_knowledge_store_binding(document, data_root=tmp_path)

    real_specs = css_module.load_candidate_semantic_supply_specs(binding, program)
    real_spec = real_specs["solve"]
    forged = {"solve": real_spec, "intake": replace(real_spec, phase="intake")}
    monkeypatch.setattr(
        css_module, "load_candidate_semantic_supply_specs", lambda *a, **k: forged
    )
    monkeypatch.setattr(
        css_module, "build_candidate_semantic_supply", lambda *a, **k: None
    )

    with pytest.raises(KnowledgeStoreError, match=r"phase\(s\) \['intake'\]"):
        build_knowledge_store_supply(
            binding, program=program, data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


# ---------------------------------------------------------------------------
# Dispatch proof, one layer closer to production: FlightRuntime's own
# ``_resolve_phase_supply`` -- the function ``core.flight.runtime`` calls to
# build the callable a real flight consults for the Solver phase -- fetches
# the task adapter's legal candidate inventory, builds the SAME router
# tested above, and returns its ``automatic_for_phase``. This proves the
# whole chain the blocker receipt's "still unproven" note names: adapter ->
# router construction -> automatic_for_phase -> a request that carries
# BOTH the candidate cards and the exemplar values for one sample.
# ---------------------------------------------------------------------------


def test_flight_runtime_resolve_phase_supply_composes_candidate_and_exemplar_stores(
    tmp_path,
):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.rails.task_adapter import CandidateInventory

    document, inventory = _candidate_config(tmp_path)
    plain_id, plain_store, plain_snapshot = _plain_phase_supply_store(
        tmp_path, phase="solve"
    )
    document["knowledge_stores"][plain_id] = plain_store
    binding = load_knowledge_store_binding(document, data_root=tmp_path)

    runtime = SimpleNamespace(
        _composed=SimpleNamespace(values=document),
        _data_root=tmp_path,
        _knowledge_store_binding=binding,
        _knowledge_store_supply=None,
        _adapter=SimpleNamespace(
            candidate_inventory=lambda: CandidateInventory(
                candidate_ids=tuple(inventory),
                source_sha256="a" * 64,
                source_authority="task-adapter-candidate-contract-provider",
            )
        ),
    )
    program = _candidate_program()
    supply_for_phase, specs = FlightRuntime._resolve_phase_supply(
        runtime, program, binding.composite_snapshot
    )
    assert "solve" in specs
    assert supply_for_phase is not None

    context = _candidate_context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    supply = supply_for_phase("solve", context)
    selected = supply.fusion_decision.selected_value_ids

    # Both supplies reach the SAME composed decision through the exact path
    # a real flight uses: FlightRuntime._resolve_phase_supply's returned
    # callable IS router.automatic_for_phase.
    assert any(value_id.startswith(f"{plain_id}::") for value_id in selected)
    assert any(value_id.startswith("slot-contracts::") for value_id in selected)
    assert runtime._knowledge_store_supply is not None
    assert runtime._knowledge_store_supply.automatic_for_phase is supply_for_phase
