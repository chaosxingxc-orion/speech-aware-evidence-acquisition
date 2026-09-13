"""Contract tests for the opt-in targetless associated-value fuser.

The legacy supply filter deliberately requires ``task_target``.  Semantic
intent-boundary values do not carry one, so the opt-in policy must admit them
only through ranked, percept-admitted facet associations.  All fixtures are
synthetic English metadata; no dataset payloads are read here.
"""

from __future__ import annotations

from speech_aware_evidence_acquisition.rails.kb_policy import (
    FuseKnobs,
    fuse_associated_values_factory,
    fuse_supplyfilter_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
    ValueBundle,
)


_SNAPSHOT_SHA256 = "a" * 64
_SPEECH_SHA256 = "b" * 64
_SPLIT_SHA256 = "c" * 64


def _query_state(*, retrieved_value_ids: tuple[str, ...] = ()) -> QueryState:
    return QueryState(
        query_id="query-associated-values",
        query_sample_id="dev:associated-values",
        speech_packet_id="packet-associated-values",
        speech_packet_sha256=_SPEECH_SHA256,
        use_split_identity_hash=_SPLIT_SHA256,
        retrieved_value_ids=retrieved_value_ids,
    ).validate()


def _snapshot(
    *,
    facet_ids: tuple[str, ...],
    values: tuple[ValueBundle, ...],
) -> KnowledgeSnapshot:
    source_ids = tuple(f"train:{facet_id}" for facet_id in facet_ids)
    return KnowledgeSnapshot(
        snapshot_id="associated-values-fuser-test-v1",
        source_split_identity_hash=_SPLIT_SHA256,
        source_sample_ids=source_ids,
        builder_policy_id="synthetic-associated-values-builder-v1",
        facets=tuple(
            KeyFacet(
                facet_id,
                "semantic-intent-boundary",
                "text",
                f"English boundary facet {facet_id}",
                (f"train:{facet_id}",),
            )
            for facet_id in facet_ids
        ),
        values=values,
    ).validate()


def _value(
    value_id: str,
    associated_facet_ids: tuple[str, ...],
) -> ValueBundle:
    return ValueBundle(
        value_id=value_id,
        content=f"English associated semantic value {value_id}",
        associated_facet_ids=associated_facet_ids,
        source_sample_ids=(f"train:{associated_facet_ids[0]}",),
        provenance_refs=(f"synthetic:{value_id}",),
        # These semantic boundary values intentionally do not name a task
        # target.  The new fuser must not invent one to admit them.
        task_target=None,
        prior_score=0.5,
    ).validate()


def _rank_result(
    query_state: QueryState,
    candidates: tuple[tuple[str, float], ...],
) -> RankResult:
    return RankResult(
        snapshot_sha256=_SNAPSHOT_SHA256,
        query_state_sha256=query_state.content_hash(),
        ranking_policy_id="synthetic-ranked-facets-v1",
        candidates=tuple(RankedFacet(facet_id, score) for facet_id, score in candidates),
    ).validate()


def _decide(
    fuser,
    *,
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
    candidates: tuple[tuple[str, float], ...],
    recall_scores: dict[str, dict[str, float]],
):
    return fuser(
        snapshot=snapshot,
        snapshot_sha256=_SNAPSHOT_SHA256,
        query_state=query_state,
        rank_result=_rank_result(query_state, candidates),
        recall_scores=recall_scores,
    )


def test_associated_values_admits_meaningful_targetless_value_legacy_leaves_empty():
    snapshot = _snapshot(
        facet_ids=("facet:intent-boundary",),
        values=(_value("value:intent-boundary", ("facet:intent-boundary",)),),
    )
    query_state = _query_state()
    candidates = (("facet:intent-boundary", 0.9),)
    recall_scores = {"facet:intent-boundary": {"semantic": 0.9}}
    knobs = FuseKnobs(tau=0.8, m=1, c=1, top_l=8)

    decision = _decide(
        fuse_associated_values_factory(knobs),
        snapshot=snapshot,
        query_state=query_state,
        candidates=candidates,
        recall_scores=recall_scores,
    )
    legacy = _decide(
        fuse_supplyfilter_factory(knobs),
        snapshot=snapshot,
        query_state=query_state,
        candidates=candidates,
        recall_scores=recall_scores,
    )

    assert decision.fusion_policy_id == "saea-fuse-associated-values-v1"
    assert decision.selected_value_ids == ("value:intent-boundary",)
    assert decision.supporting_facet_ids == ("facet:intent-boundary",)
    assert legacy.selected_value_ids == ()
    assert legacy.supporting_facet_ids == ()


def test_associated_values_requires_real_cosine_at_or_above_threshold():
    snapshot = _snapshot(
        facet_ids=("facet:intent-boundary",),
        values=(_value("value:intent-boundary", ("facet:intent-boundary",)),),
    )
    query_state = _query_state()

    decision = _decide(
        fuse_associated_values_factory(FuseKnobs(tau=0.8, m=1, c=1, top_l=8)),
        snapshot=snapshot,
        query_state=query_state,
        candidates=(("facet:intent-boundary", 0.99),),
        recall_scores={"facet:intent-boundary": {"semantic": 0.799}},
    )

    assert decision.selected_value_ids == ()
    assert decision.supporting_facet_ids == ()


def test_associated_values_deduplicates_across_ranked_facets_with_provenance():
    snapshot = _snapshot(
        facet_ids=("facet:high", "facet:low"),
        values=(
            _value("value:shared", ("facet:high", "facet:low")),
            _value("value:low-only", ("facet:low",)),
        ),
    )
    query_state = _query_state()

    decision = _decide(
        fuse_associated_values_factory(FuseKnobs(tau=0.8, m=2, c=2, top_l=8)),
        snapshot=snapshot,
        query_state=query_state,
        candidates=(("facet:high", 0.9), ("facet:low", 0.8)),
        recall_scores={
            "facet:high": {"semantic": 0.9},
            "facet:low": {"semantic": 0.9},
        },
    )

    assert decision.selected_value_ids == ("value:shared", "value:low-only")
    assert decision.supporting_facet_ids == ("facet:high", "facet:low")


def test_associated_values_excludes_values_already_visible_to_query():
    snapshot = _snapshot(
        facet_ids=("facet:intent-boundary",),
        values=(
            _value("value:already-visible", ("facet:intent-boundary",)),
            _value("value:fresh", ("facet:intent-boundary",)),
        ),
    )
    query_state = _query_state(retrieved_value_ids=("value:already-visible",))

    decision = _decide(
        fuse_associated_values_factory(FuseKnobs(tau=0.8, m=1, c=2, top_l=8)),
        snapshot=snapshot,
        query_state=query_state,
        candidates=(("facet:intent-boundary", 0.9),),
        recall_scores={"facet:intent-boundary": {"semantic": 0.9}},
    )

    assert decision.selected_value_ids == ("value:fresh",)
    assert decision.supporting_facet_ids == ("facet:intent-boundary",)


def test_associated_values_is_deterministic_for_ties_value_order_and_caps():
    # The fixture intentionally stores values in a different order from their
    # ids.  Equal-ranked facets are valid only in ascending facet-id order;
    # each facet must then traverse its own associated values by value_id.
    snapshot = _snapshot(
        facet_ids=("facet:a", "facet:b", "facet:c"),
        values=(
            _value("value:z", ("facet:a",)),
            _value("value:a", ("facet:a",)),
            _value("value:c", ("facet:b",)),
            _value("value:b", ("facet:b",)),
            _value("value:excluded-by-m", ("facet:c",)),
        ),
    )
    query_state = _query_state()
    fuser = fuse_associated_values_factory(FuseKnobs(tau=0.8, m=2, c=2, top_l=3))
    inputs = dict(
        snapshot=snapshot,
        query_state=query_state,
        candidates=(
            ("facet:a", 0.9),
            ("facet:b", 0.9),
            ("facet:c", 0.8),
        ),
        recall_scores={
            "facet:a": {"semantic": 0.9},
            "facet:b": {"semantic": 0.9},
            "facet:c": {"semantic": 0.9},
        },
    )

    first = _decide(fuser, **inputs)
    second = _decide(fuser, **inputs)

    assert first.selected_value_ids == ("value:a", "value:z", "value:b")
    assert first.supporting_facet_ids == ("facet:a", "facet:b")
    assert second == first