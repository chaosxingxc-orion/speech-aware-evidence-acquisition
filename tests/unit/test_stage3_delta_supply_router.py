"""Stage-3 S3-6w: the router wiring proof obligations.

Covers the named-store router (``rails.knowledge_stores.build_knowledge_store_supply``)
finally recognising a ``store_role: "stage3-deltas"`` store's ``context_supply`` --
the ONE piece the S3-4..6 item deliberately left unwired (module docstring of
``rails/stage3_delta_supply.py``, and the S3-6 readiness package's "documented
scope decision").

Three obligations, matching the S3-6w task brief:

1. Every EXISTING route (the two admitted candidate_supply roles --
   slot-contracts here, the anchor case's exemplar phase_supply) stays
   byte-identical when a stage3-deltas store is added alongside them.
2. A synthetic end-to-end composition: a tiny stage3-deltas snapshot, bound
   through ``load_knowledge_store_binding``, routed for a synthetic
   ``QueryState`` with two candidate intents, returns the capped ranked
   deltas and a routing receipt.
3. The spec's own validation surface (store_role, rank_by, cap, phase order,
   legal candidate inventory) is enforced fail-closed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    KnowledgeStoreError,
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_stage3_delta_snapshot,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    STAGE3_DELTA_CONTEXT_PROVIDER_ID,
)

from test_candidate_semantic_supply import (
    _artifact,
    _config as _candidate_config,
    _context as _candidate_context,
    _latest_context,
    _program as _candidate_program,
    _store,
)
from test_knowledge_stores_e3b_candidate_and_phase_supply_router import (
    _plain_phase_supply_store,
)

SHA_A = "a" * 64


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _delta_row(suffix, facet_ids, prior_score, *, source_sample_ids=("train-1",)):
    return {
        "value_id": f"delta:1:{suffix}",
        "content": f"Synthetic delta statement {suffix}.",
        "associated_facet_ids": list(facet_ids),
        "source_sample_ids": list(source_sample_ids),
        "provenance_refs": [f"advantage:SAEA-TEST-RUN:row-{suffix}:0:1"],
        "task_target": f"stage3-delta-target:{facet_ids[0]}",
        "prior_score": prior_score,
    }


def _stage3_delta_store_doc(tmp_path, *, rows, store_id="stage3-deltas",
                             role="stage3-deltas",
                             permitted_source_sample_ids=("train-1",)):
    snapshot = build_stage3_delta_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=tuple(permitted_source_sample_ids),
        ),
        rows=rows,
    )
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(rows),
    }
    store_doc = _store(tmp_path, store_id, role, snapshot, source)
    return store_doc, snapshot


def _delta_supply_spec(*, candidate_state_phase="hypotheses", cap=8):
    return {
        "provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        "candidate_state_phase": candidate_state_phase,
        "cap": cap,
        "rank_by": "prior_score",
    }


# ---------------------------------------------------------------------------
# 1. Existing routes stay byte-identical
# ---------------------------------------------------------------------------


def test_existing_two_admitted_routes_stay_byte_identical_when_stage3_deltas_is_added(
    tmp_path,
):
    # -- before: the E3b anchor case alone (slot-contracts candidate_supply +
    #    a train-exemplars-shaped plain phase_supply on the same "solve" phase).
    before_root = tmp_path / "before"
    document, inventory = _candidate_config(before_root)
    plain_id, plain_store, _plain_snapshot = _plain_phase_supply_store(
        before_root, phase="solve", facets=(("ex1", (1.0, 0.0)),)
    )
    document["knowledge_stores"][plain_id] = plain_store
    binding_before = load_knowledge_store_binding(document, data_root=before_root)
    router_before = build_knowledge_store_supply(
        binding_before, program=_candidate_program(), data_root=before_root,
        legal_candidate_ids=inventory,
    )
    context_before = _candidate_context(binding_before, _artifact("s1", ("beta", "alpha", "gamma")))
    supply_before = router_before.automatic_for_phase("solve", context_before)
    receipt_before = router_before.receipt

    # -- after: the identical anchor case, PLUS a stage3-deltas store routed
    #    to the SAME "solve" phase through context_supply.
    after_root = tmp_path / "after"
    document2, inventory2 = _candidate_config(after_root)
    assert inventory2 == inventory
    plain_id2, plain_store2, _plain_snapshot2 = _plain_phase_supply_store(
        after_root, phase="solve", facets=(("ex1", (1.0, 0.0)),)
    )
    document2["knowledge_stores"][plain_id2] = plain_store2
    assert plain_id2 == plain_id
    delta_rows = [
        _delta_row("aaaaaaaaaaaa", ("alpha",), 0.9),
        _delta_row("bbbbbbbbbbbb", ("beta",), 0.5),
    ]
    delta_store, _delta_snapshot = _stage3_delta_store_doc(after_root, rows=delta_rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document2["knowledge_stores"]["stage3-deltas"] = delta_store
    binding_after = load_knowledge_store_binding(document2, data_root=after_root)
    router_after = build_knowledge_store_supply(
        binding_after, program=_candidate_program(), data_root=after_root,
        legal_candidate_ids=inventory2,
    )
    context_after = _candidate_context(binding_after, _artifact("s1", ("beta", "alpha", "gamma")))
    supply_after = router_after.automatic_for_phase("solve", context_after)
    receipt_after = router_after.receipt

    # The two PRE-EXISTING stores' own receipt entries are untouched -- every
    # field EXCEPT the ones DERIVED from composite_snapshot_sha256 (the whole
    # BINDING's hash across every bound store, which correctly moves whenever
    # any store is added, and the selection_receipt_sha256 that embeds it in
    # turn) -- that is the composite identity working as designed, not a
    # per-store regression.
    _COMPOSITE_DERIVED_KEYS = {"composite_snapshot_sha256", "selection_receipt_sha256"}

    def _without_composite(value):
        if isinstance(value, dict):
            return {
                k: _without_composite(v)
                for k, v in value.items()
                if k not in _COMPOSITE_DERIVED_KEYS
            }
        if isinstance(value, list):
            return [_without_composite(item) for item in value]
        return value

    for store_id in ("slot-contracts", plain_id):
        before_entry = receipt_before["stores"][store_id]
        after_entry = receipt_after["stores"][store_id]
        assert _without_composite(before_entry) == _without_composite(after_entry)
        assert content_hash(_without_composite(before_entry)) == content_hash(
            _without_composite(after_entry)
        )
    # Same candidate_supply/candidate_selections bookkeeping at the top level.
    assert _without_composite(receipt_before["candidate_supply"]) == _without_composite(
        receipt_after["candidate_supply"]
    )

    # And the two admitted stores' SELECTED VALUES for this exact row are
    # unaffected by the third store's presence: the same exemplar leads,
    # the same slot-contract cards follow, in the same order.
    before_selected = supply_before.fusion_decision.selected_value_ids
    after_selected = supply_after.fusion_decision.selected_value_ids
    before_non_delta = tuple(v for v in before_selected if not v.startswith("stage3-deltas::"))
    after_non_delta = tuple(v for v in after_selected if not v.startswith("stage3-deltas::"))
    assert before_non_delta == after_non_delta

    # The new store's own entry appears, additively.
    assert "stage3-deltas" not in receipt_before["stores"]
    assert receipt_after["stores"]["stage3-deltas"]["context_supply"] == ["solve"]


# ---------------------------------------------------------------------------
# 2. Synthetic end-to-end: two candidate intents, capped ranked deltas.
# ---------------------------------------------------------------------------


def test_synthetic_end_to_end_two_candidate_intents_returns_capped_ranked_deltas(
    tmp_path,
):
    rows = [
        _delta_row("aaaaaaaaaaaa", ("alpha",), 0.9),
        _delta_row("bbbbbbbbbbbb", ("beta",), 0.5),
        _delta_row("cccccccccccc", ("gamma",), 0.95),  # not a candidate: excluded
        _delta_row("dddddddddddd", ("alpha", "beta"), 0.7),
        _delta_row("eeeeeeeeeeee", ("alpha",), 0.6),
    ]
    delta_store, snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec(cap=3)}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    legal = ("alpha", "beta", "gamma", "delta")

    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    assert hasattr(router, "automatic_for_phase")

    context = _candidate_context(binding, _artifact("s1", ("beta", "alpha")))
    supply = router.automatic_for_phase("solve", context)
    selected = supply.fusion_decision.selected_value_ids

    # Candidates alpha+beta intersect every row except the gamma-only one;
    # capped at 3, ordered by prior_score descending: aaaaaaaaaaaa (0.9),
    # dddddddddddd (0.7), eeeeeeeeeeee (0.6).
    assert selected == (
        "stage3-deltas::delta:1:aaaaaaaaaaaa",
        "stage3-deltas::delta:1:dddddddddddd",
        "stage3-deltas::delta:1:eeeeeeeeeeee",
    )

    receipt = router.receipt
    assert receipt["schema"] == "saea-named-knowledge-store-routing-v1"
    assert receipt["stores"]["stage3-deltas"]["context_supply"] == ["solve"]
    assert receipt["stores"]["stage3-deltas"]["store_role"] == "stage3-deltas"


def test_cap_eight_matches_the_production_delta_cell_fragment_shape(tmp_path):
    rows = [
        _delta_row(f"{index:012x}", ("alpha",), float(index) / 10)
        for index in range(10)
    ]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec(cap=8)}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    legal = ("alpha", "beta")

    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    context = _candidate_context(binding, _artifact("s1", ("alpha",)))
    supply = router.automatic_for_phase("solve", context)
    selected = supply.fusion_decision.selected_value_ids
    assert len(selected) == 8
    # Highest prior_score (index 9..2) wins the cap, descending.
    assert selected[0] == "stage3-deltas::delta:1:000000000009"
    assert selected[-1] == "stage3-deltas::delta:1:000000000002"


def test_no_matching_candidate_supplies_nothing_rather_than_an_empty_acquire(tmp_path):
    """The CELL-1 smoke's third failure (2026-09-23), at the router.

    This test used to assert "an empty but VALID supply" -- and that is
    precisely what killed the flight. A supply object, any supply object,
    makes ``rails.controllers.advance_phase_response_state`` emit an
    ``action_kind="acquire"`` transition, and an acquire that introduces
    neither a value nor a facet is refused by ``AgentStepTransition.validate``.
    The route now DECLINES the phase instead, and the skip is receipted.
    """

    rows = [_delta_row("aaaaaaaaaaaa", ("gamma",), 0.9)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    legal = ("alpha", "beta", "gamma")

    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    context = _candidate_context(binding, _artifact("s1", ("alpha", "beta")))
    assert router.automatic_for_phase("solve", context) is None

    entry = next(iter(router.receipt["delta_supply"].values()))
    assert entry["selected"] == 0
    assert entry["already_acquired"] == 0
    assert entry["phase"] == "solve"
    assert entry["sample_id"] == "s1"
    assert entry["store_id"] == "stage3-deltas"
    assert entry["reason"] == "no delta of this node slice matches the row candidates"


def test_the_empty_supply_this_route_no_longer_returns_is_a_refused_acquire(tmp_path):
    """Why the route declines instead of returning an empty decision.

    The pre-fix object, built by hand and handed to the production advance,
    raises the exact refusal the openJiuwen vertex ``reviewer_0_input``
    raised on 2026-09-23 after 12 metered contacts. The transition invariant
    stays STRICT; the route stops handing it nothing.
    """

    from speech_aware_evidence_acquisition.rails.controllers import (
        PhaseSupply,
        advance_phase_response_state,
    )
    from speech_aware_evidence_acquisition.rails.knowledge import (
        FusionDecision,
        RailsError,
        RankResult,
    )

    rows = [_delta_row("aaaaaaaaaaaa", ("gamma",), 0.9)]
    delta_store, snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    context = _candidate_context(binding, _artifact("s1", ("alpha", "beta")))
    query_hash = context.query_state.content_hash()

    rank = RankResult(
        snapshot_sha256=snapshot.content_hash(),
        query_state_sha256=query_hash,
        ranking_policy_id=STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        candidates=(),
    ).validate()
    empty = PhaseSupply(
        rank_result=rank,
        fusion_decision=FusionDecision(
            snapshot_sha256=snapshot.content_hash(),
            query_state_sha256=query_hash,
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id=STAGE3_DELTA_CONTEXT_PROVIDER_ID,
            supporting_facet_ids=(),
            selected_value_ids=(),
        ).validate(),
        action_target_ref=f"{STAGE3_DELTA_CONTEXT_PROVIDER_ID}:node=reviewer:cap=4",
    ).validate()

    with pytest.raises(
        RailsError, match="acquire must introduce at least one new value or facet"
    ):
        advance_phase_response_state(
            context=context,
            added_states=(_artifact("s1", ("alpha",), state_id="phase:solve:s1",
                                    state_kind="phase:solve"),),
            action_target_ref="synthetic-hypotheses-then-solve-v1:solve:contact-1",
            supply=empty,
        )


def test_a_revisited_node_acquires_only_what_is_new_and_declines_when_nothing_is(
    tmp_path,
):
    """The cumulative value set, at the route.

    A per-node selection is a pure function of (phase, sample): a revisited
    node is handed the SAME ids, and the agent's value set is cumulative, so
    those ids are already in ``QueryState.retrieved_value_ids``. The route
    drops them and caps what REMAINS; when nothing remains it declines.
    """

    rows = [
        _delta_row("aaaaaaaaaaaa", ("alpha",), 0.9),
        _delta_row("bbbbbbbbbbbb", ("alpha",), 0.8),
        _delta_row("cccccccccccc", ("alpha",), 0.7),
    ]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec(cap=2)}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=("alpha", "beta"),
    )
    artifact = _artifact("s1", ("alpha",))

    # First visit: the cap picks the two highest priors, exactly as before.
    first = router.automatic_for_phase("solve", _candidate_context(binding, artifact))
    assert first.fusion_decision.selected_value_ids == (
        "stage3-deltas::delta:1:aaaaaaaaaaaa",
        "stage3-deltas::delta:1:bbbbbbbbbbbb",
    )

    # Revisit with those two already acquired: the cap now applies to the NEW
    # values, so the third delta -- which the pre-fix k=cap ranking never even
    # reached -- is what this visit acquires.
    second = router.automatic_for_phase(
        "solve",
        _latest_context(
            binding,
            (artifact,),
            retrieved_value_ids=first.fusion_decision.selected_value_ids,
        ),
    )
    assert second.fusion_decision.selected_value_ids == (
        "stage3-deltas::delta:1:cccccccccccc",
    )

    # Revisit with the whole slice acquired: nothing new, so no supply step.
    assert (
        router.automatic_for_phase(
            "solve",
            _latest_context(
                binding,
                (artifact,),
                retrieved_value_ids=(
                    first.fusion_decision.selected_value_ids
                    + second.fusion_decision.selected_value_ids
                ),
            ),
        )
        is None
    )
    entry = next(
        item
        for item in router.receipt["delta_supply"].values()
        if item["already_acquired"] == 3
    )
    assert entry["selected"] == 0
    assert entry["reason"] == (
        "every ranked delta of this node slice is already acquired in this episode"
    )


def test_deterministic_across_two_independent_calls(tmp_path):
    rows = [
        _delta_row("aaaaaaaaaaaa", ("alpha",), 0.5),
        _delta_row("bbbbbbbbbbbb", ("alpha",), 0.5),  # tie: value_id tie-break
    ]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    legal = ("alpha", "beta")

    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    context = _candidate_context(binding, _artifact("s1", ("alpha",)))
    first = router.automatic_for_phase("solve", context).fusion_decision.selected_value_ids
    second = router.automatic_for_phase("solve", context).fusion_decision.selected_value_ids
    assert first == second == (
        "stage3-deltas::delta:1:aaaaaaaaaaaa",
        "stage3-deltas::delta:1:bbbbbbbbbbbb",
    )


# ---------------------------------------------------------------------------
# 3. Validation surface
# ---------------------------------------------------------------------------


def test_refuses_a_store_role_other_than_stage3_deltas(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(
        tmp_path, rows=rows, store_id="not-stage3-deltas", role="some-other-role"
    )
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"not-stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="candidate-bound, capped"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


def test_refuses_rank_by_other_than_prior_score(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    spec = _delta_supply_spec()
    spec["rank_by"] = "recency"
    delta_store["context_supply"] = {"solve": spec}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="candidate-bound, capped"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


@pytest.mark.parametrize("bad_cap", [0, -1, 1.5, "8", True])
def test_refuses_a_non_positive_integer_cap(tmp_path, bad_cap):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    spec = _delta_supply_spec()
    spec["cap"] = bad_cap
    delta_store["context_supply"] = {"solve": spec}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="candidate-bound, capped"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


def test_refuses_a_candidate_state_phase_not_earlier_than_the_target_phase(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec(candidate_state_phase="solve")}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="candidate-bound, capped"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


def test_refuses_the_first_phase_as_the_target(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    # "hypotheses" is the program's first phase; a stage3-deltas route
    # cannot target it (candidate_state_phase would have to precede it).
    delta_store["context_supply"] = {
        "hypotheses": {
            "provider": STAGE3_DELTA_CONTEXT_PROVIDER_ID,
            "candidate_state_phase": "hypotheses",
            "cap": 8,
            "rank_by": "prior_score",
        }
    }
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="candidate-bound, capped"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


def test_requires_the_legal_candidate_inventory(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    with pytest.raises(KnowledgeStoreError, match="legal candidate inventory"):
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=None,
        )


def test_refuses_an_unrecognised_provider_in_context_supply(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": {"provider": "not-a-real-provider-v1"}}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    with pytest.raises(KnowledgeStoreError, match="unrecognised provider"):
        binding = load_knowledge_store_binding(document, data_root=tmp_path)
        build_knowledge_store_supply(
            binding, program=_candidate_program(), data_root=tmp_path,
            legal_candidate_ids=("alpha", "beta"),
        )


def test_refuses_a_missing_or_duplicate_candidate_state(tmp_path):
    rows = [_delta_row("aaaaaaaaaaaa", ("alpha",), 0.5)]
    delta_store, _snapshot = _stage3_delta_store_doc(tmp_path, rows=rows)
    delta_store["context_supply"] = {"solve": _delta_supply_spec()}
    document = {"knowledge_stores": {"stage3-deltas": delta_store}}
    binding = load_knowledge_store_binding(document, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_candidate_program(), data_root=tmp_path,
        legal_candidate_ids=("alpha", "beta"),
    )
    artifact = _artifact("s1", ("alpha",))
    query = QueryState(
        query_id="query:s1", query_sample_id="s1", speech_packet_id="packet:s1",
        speech_packet_sha256="b" * 64, use_split_identity_hash=SHA_A,
        query_source="speech_features",
    ).validate()
    no_state_context = AgentRuntimeContext(
        sample_id="s1", knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=(), catalog_value_ids=(), query_state=query,
        task_contract="synthetic", agent_states=(), prior_response_sha256s=(),
        contact_index=1,
    )
    with pytest.raises(KnowledgeStoreError, match="exactly one source-bound"):
        router.automatic_for_phase("solve", no_state_context)

    two_states_context = AgentRuntimeContext(
        sample_id="s1", knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=(), catalog_value_ids=(), query_state=query,
        task_contract="synthetic", agent_states=(artifact, artifact),
        prior_response_sha256s=(), contact_index=1,
    )
    with pytest.raises(KnowledgeStoreError, match="exactly one source-bound"):
        router.automatic_for_phase("solve", two_states_context)
