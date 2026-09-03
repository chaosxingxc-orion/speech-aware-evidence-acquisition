from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.rails.a2t_semantic_router import (
    SemanticRouterError,
    ToolTierSemanticIndex,
    fuse_semantic_rankings,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _row(
    unit_id: str,
    *,
    query_idx: int,
    tool: str,
    tier: str,
    extras: tuple[str, ...] = (),
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=unit_id,
        tier=tier,
        query_idx=query_idx,
        text=f"private construction representation {unit_id}",
        domain="private",
        category="private",
        tool_id=query_idx,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE",
        extra_call_names=extras,
        call_count=1 + len(extras),
        sample_ids=(unit_id,),
        item_ids=(query_idx,),
        media_relpath_by_sample_id={},
        speaker_ids=("private",),
    )


def _index() -> ToolTierSemanticIndex:
    rows = (
        _row("a-direct", query_idx=1, tool="alphaTool", tier="direct"),
        _row("a-implicit", query_idx=2, tool="alphaTool", tier="implicit"),
        _row(
            "b-direct",
            query_idx=3,
            tool="betaTool",
            tier="direct",
            extras=("gammaTool",),
        ),
    )
    vectors = {
        "a-direct": (1.0, 0.0, 0.0),
        "a-implicit": (0.8, 0.2, 0.0),
        "b-direct": (0.0, 1.0, 0.0),
    }
    return ToolTierSemanticIndex.build(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unseenTool"),
    )


def test_index_ranks_by_maximum_tool_tier_centroid_and_keeps_extra_labels() -> None:
    index = _index()

    ranking = index.rank((0.0, 1.0, 0.0), top_k=3)

    assert ranking.selected_tool_names == (
        "betaTool",
        "gammaTool",
        "alphaTool",
    )
    assert ranking.full_ranked_tool_names[-1] == "unseenTool"
    assert ranking.selected[0].score == pytest.approx(1.0)
    assert ranking.selected[0].supported_by_construction is True
    assert ranking.index_sha256 == index.index_sha256
    assert len(ranking.query_vector_sha256) == 64
    assert index.dimension == 3
    assert index.tool_tier_centroid_count == 4


def test_index_is_order_invariant_and_has_a_stable_identity() -> None:
    first = _index()
    rows = tuple(reversed(first.construction_rows))
    vectors = {
        row.unit_id: {
            "a-direct": (1.0, 0.0, 0.0),
            "a-implicit": (0.8, 0.2, 0.0),
            "b-direct": (0.0, 1.0, 0.0),
        }[row.unit_id]
        for row in rows
    }
    second = ToolTierSemanticIndex.build(
        construction_rows=rows,
        vectors_by_unit_id=vectors,
        registry_tool_names=tuple(reversed(first.registry_tool_names)),
    )

    assert first.index_sha256 == second.index_sha256
    assert first.rank((1.0, 0.0, 0.0), top_k=4).full_ranked_tool_names == (
        "alphaTool",
        "betaTool",
        "gammaTool",
        "unseenTool",
    )


@pytest.mark.parametrize(
    "query",
    [(), (0.0, 0.0, 0.0), (1.0, 0.0), (1.0, math.nan, 0.0)],
)
def test_rank_refuses_malformed_query_vectors(query: tuple[float, ...]) -> None:
    with pytest.raises(SemanticRouterError):
        _index().rank(query, top_k=2)


def test_rank_refuses_an_invalid_candidate_count() -> None:
    index = _index()
    for value in (0, 5, True):
        with pytest.raises(SemanticRouterError, match="top_k"):
            index.rank((1.0, 0.0, 0.0), top_k=value)


def test_build_requires_exact_vector_coverage_and_valid_rows() -> None:
    row = _row("a", query_idx=1, tool="alphaTool", tier="direct")
    with pytest.raises(SemanticRouterError, match="exactly cover"):
        ToolTierSemanticIndex.build(
            construction_rows=(row,),
            vectors_by_unit_id={},
            registry_tool_names=("alphaTool",),
        )
    with pytest.raises(SemanticRouterError, match="unknown"):
        ToolTierSemanticIndex.build(
            construction_rows=(row,),
            vectors_by_unit_id={"a": (1.0, 0.0)},
            registry_tool_names=("otherTool",),
        )


def test_fusion_uses_complete_rankings_and_is_deterministic() -> None:
    index = _index()
    transcript = index.rank((1.0, 0.0, 0.0), top_k=2)
    intent = index.rank((0.0, 1.0, 0.0), top_k=2)

    fused = fuse_semantic_rankings(
        (transcript, intent),
        top_k=3,
        source_names=("self_transcript", "model_intent"),
    )

    assert fused.selected_tool_names == ("betaTool", "alphaTool", "gammaTool")
    assert fused.source_names == ("self_transcript", "model_intent")
    assert fused.index_sha256 == index.index_sha256
    assert fused.rrf_constant == 60
    assert len(fused.fusion_sha256) == 64


def test_fusion_refuses_mismatched_indices_or_source_names() -> None:
    index = _index()
    first = index.rank((1.0, 0.0, 0.0), top_k=2)
    other = ToolTierSemanticIndex.build(
        construction_rows=(_row("x", query_idx=9, tool="alphaTool", tier="direct"),),
        vectors_by_unit_id={"x": (1.0, 0.0, 0.0)},
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unseenTool"),
    ).rank((1.0, 0.0, 0.0), top_k=2)

    with pytest.raises(SemanticRouterError, match="same index"):
        fuse_semantic_rankings(
            (first, other),
            top_k=2,
            source_names=("one", "two"),
        )
    with pytest.raises(SemanticRouterError, match="source_names"):
        fuse_semantic_rankings((first,), top_k=2, source_names=("one", "two"))
