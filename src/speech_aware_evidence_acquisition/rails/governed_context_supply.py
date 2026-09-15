"""Deterministic parent-scoped supply from frozen external-governed context."""

from __future__ import annotations

from typing import Mapping, Sequence

from ..core.base import KNOWLEDGE_FUSERS, KNOWLEDGE_RANKERS
from .errors import RailsError
from .knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    FusionDecision,
    KnowledgeSnapshot,
    QueryState,
    RankResult,
    RankedFacet,
)
from .knowledge_provider import KnowledgeProvider, RankedEntry, Ranking

SOURCE_SCOPED_CONTEXT_PROVIDER_ID = "source-scoped-context-v1"
SOURCE_SCOPED_CONTEXT_RANK_POLICY_ID = "saea-source-scoped-context-rank-v1"
SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID = "saea-source-scoped-context-fuse-v1"
_SCOPE_DIMENSION = "source-scope"
_SCOPE_REPRESENTATION_KIND = "parent-sample-id"


class GovernedContextSupplyError(RailsError):
    """A governed context snapshot cannot prove one-source-only routing."""


class SourceScopedContextProvider(KnowledgeProvider):
    """Select exactly one released value by the original query parent ID."""

    def __init__(self, *, snapshot: KnowledgeSnapshot, value_id_namespace: str | None = None) -> None:
        super().__init__(provider_id=SOURCE_SCOPED_CONTEXT_PROVIDER_ID)
        snapshot.validate()
        if snapshot.source_partition_role != EXTERNAL_GOVERNED_PARTITION_ROLE:
            raise GovernedContextSupplyError(
                "source-scoped context requires an external-governed snapshot"
            )
        self._scope_values = self._validate_snapshot(snapshot)
        self._value_id_namespace = value_id_namespace
        self.adopt(
            snapshot,
            policy_id=snapshot.builder_policy_id,
            source_ids=snapshot.source_sample_ids,
            snapshot_sha256=snapshot.content_hash(),
        )
        self._last_rank: RankResult | None = None
        self._last_query: QueryState | None = None
        self._last_ranking: Ranking | None = None

    @staticmethod
    def _validate_snapshot(snapshot: KnowledgeSnapshot) -> Mapping[str, tuple[str, str]]:
        facets = {}
        for facet in snapshot.facets:
            if (
                facet.dimension != _SCOPE_DIMENSION
                or facet.representation_kind != _SCOPE_REPRESENTATION_KIND
                or facet.parent_facet_ids
                or facet.representation in facets
            ):
                raise GovernedContextSupplyError("malformed or duplicate source-scope facet")
            if facet.representation in facet.source_sample_ids:
                raise GovernedContextSupplyError("scope parent cannot be an external context source")
            facets[facet.representation] = (facet.facet_id, facet.source_sample_ids)
        values: dict[str, tuple[str, str]] = {}
        for value in snapshot.values:
            if value.task_target is not None or value.prior_score is not None:
                raise GovernedContextSupplyError("source-scoped values cannot carry task_target or prior")
            if len(value.associated_facet_ids) != 1:
                raise GovernedContextSupplyError("source-scoped value has mixed association scopes")
            facet_id = value.associated_facet_ids[0]
            scope = next((key for key, item in facets.items() if item[0] == facet_id), None)
            if scope is None or scope in values:
                raise GovernedContextSupplyError("source-scoped values require one value per scope")
            if value.source_sample_ids != facets[scope][1] or scope in value.source_sample_ids:
                raise GovernedContextSupplyError("source-scoped facet and value provenance differs")
            values[scope] = (facet_id, value.value_id)
        if set(values) != set(facets):
            raise GovernedContextSupplyError("every source scope requires exactly one associated value")
        return values

    def build(self, source_rows: object, *, policy_id: str) -> object:
        raise GovernedContextSupplyError("source-scoped context adopts a frozen snapshot")

    def _built_sample_ids(self) -> frozenset[str]:
        return frozenset(self._built_object().source_sample_ids)

    def candidates(self, query: object, *, k: int) -> Ranking:
        if not isinstance(query, Mapping):
            raise GovernedContextSupplyError("source-scoped context query must be a mapping")
        context, query_state = query.get("context"), query.get("query_state")
        sample_id = getattr(context, "sample_id", None)
        if not isinstance(query_state, QueryState) or sample_id != query_state.query_sample_id:
            raise GovernedContextSupplyError("context sample_id must equal original query sample ID")
        if type(k) is not int or k < 1 or sample_id not in self._scope_values:
            raise GovernedContextSupplyError("unknown or invalid source-scoped query")
        facet_id, _value_id = self._scope_values[sample_id]
        rank = KNOWLEDGE_RANKERS.resolve(SOURCE_SCOPED_CONTEXT_RANK_POLICY_ID)()(
            snapshot_sha256=self.snapshot_sha256(), query_state=query_state, facet_id=facet_id
        )
        self._last_rank, self._last_query = rank, query_state
        ranking = Ranking(
            entries=(RankedEntry(facet_id, 1.0, {}),),
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_state.content_hash(), source=self.provider_id,
        ).validate()
        self._last_ranking = ranking
        return ranking

    def fuse(self, rankings: Sequence[Ranking], *, k: int, policy_id: str) -> FusionDecision:
        if (
            policy_id != SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID
            or type(k) is not int or k < 1 or len(rankings) != 1
            or self._last_rank is None or self._last_query is None or self._last_ranking is None
        ):
            raise GovernedContextSupplyError("invalid source-scoped fusion")
        facet_id = self._last_rank.candidates[0].facet_id
        scope = self._last_query.query_sample_id
        expected_facet, value_id = self._scope_values[scope]
        if facet_id != expected_facet or rankings[0].as_json() != self._last_ranking.as_json():
            raise GovernedContextSupplyError("source-scoped ranking changed before fusion")
        return KNOWLEDGE_FUSERS.resolve(SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID)()(
            rank=self._last_rank, facet_id=facet_id, value_id=value_id,
            query_state=self._last_query, value_id_namespace=self._value_id_namespace,
        )

    def last_rank_result(self) -> RankResult | None:
        return self._last_rank


def _source_scoped_rank(_knobs: object = None):
    def rank(*, snapshot_sha256, query_state, facet_id):
        return RankResult(snapshot_sha256, query_state.content_hash(), SOURCE_SCOPED_CONTEXT_RANK_POLICY_ID, (RankedFacet(facet_id, 1.0),)).validate()
    return rank


def _source_scoped_fuse(_knobs: object = None):
    def fuse(*, rank, facet_id, value_id, query_state, value_id_namespace=None):
        from .knowledge_stores import qualify_id

        rank.validate()
        query_state.validate()
        if rank.query_state_sha256 != query_state.content_hash():
            raise GovernedContextSupplyError("source-scoped fusion query binding changed")
        visible_id = value_id if value_id_namespace is None else qualify_id(value_id_namespace, value_id)
        if tuple(item.facet_id for item in rank.candidates) != (facet_id,):
            raise GovernedContextSupplyError("source-scoped fusion requires its singleton rank")
        return FusionDecision(
            snapshot_sha256=rank.snapshot_sha256,
            query_state_sha256=rank.query_state_sha256,
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id=SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID,
            supporting_facet_ids=(facet_id,),
            selected_value_ids=() if visible_id in query_state.retrieved_value_ids else (value_id,),
        ).validate()
    return fuse
