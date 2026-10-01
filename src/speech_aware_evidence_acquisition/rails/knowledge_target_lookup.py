"""Pure, bounded knowledge selection for explicit task targets.

The caller supplies ordered candidate IDs. Source values are associated with
those candidates by a verified released relation or ``ValueBundle.task_target``; value IDs and
content never participate in the association decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .candidate_contract_lookup import CandidateContractRequest
from .controllers import PhaseSupply
from .hashing import content_hash
from .knowledge import (
    FusionDecision,
    KnowledgeSnapshot,
    QueryState,
    RankedFacet,
    RankResult,
)
from .knowledge_provider import (
    SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
    select_candidate_semantic_values,
)

TOOL_ID = "saea-tool-knowledge-target-lookup-v1"
SCHEMA = "saea-knowledge-target-selection-v1"
MAX_SELECTION_BOUND = 32


class KnowledgeTargetLookupError(ValueError):
    """A knowledge-target lookup argument is outside the bounded contract."""


@dataclass(frozen=True)
class KnowledgeTargetSelection:
    """The full bounded selection, optional new supply, and its audit record."""

    supply: PhaseSupply | None
    selected_value_ids: tuple[str, ...]
    audit: Mapping[str, object]


def _selection_bound(value: object, *, field: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= MAX_SELECTION_BOUND
    ):
        raise KnowledgeTargetLookupError(
            f"{field} must be a positive non-bool integer at most {MAX_SELECTION_BOUND}"
        )
    return value


def _already_visible_ids(
    value_ids: Sequence[str], *, local_value_ids: frozenset[str]
) -> tuple[str, ...]:
    if isinstance(value_ids, (str, bytes)):
        raise KnowledgeTargetLookupError("already_visible_value_ids must be a sequence")
    try:
        result = tuple(value_ids)
    except TypeError as error:
        raise KnowledgeTargetLookupError(
            "already_visible_value_ids must be a sequence"
        ) from error
    if any(not isinstance(value_id, str) or not value_id for value_id in result):
        raise KnowledgeTargetLookupError(
            "already_visible_value_ids must contain non-empty text"
        )
    if len(result) != len(set(result)):
        raise KnowledgeTargetLookupError(
            "already_visible_value_ids contains a duplicate"
        )
    unknown = sorted(set(result) - local_value_ids)
    if unknown:
        raise KnowledgeTargetLookupError(
            f"already_visible_value_ids must name local snapshot values: {unknown}"
        )
    return result


def _target_value_index(snapshot: KnowledgeSnapshot) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, list[str]] = {}
    for value in snapshot.values:
        if value.task_target is None:
            continue
        grouped.setdefault(value.task_target, []).append(value.value_id)
    return {
        task_target: tuple(sorted(value_ids))
        for task_target, value_ids in grouped.items()
    }


def _supporting_facet_ids(
    snapshot: KnowledgeSnapshot, value_ids: Sequence[str]
) -> tuple[str, ...]:
    value_by_id = {value.value_id: value for value in snapshot.values}
    facets: dict[str, None] = {}
    for value_id in value_ids:
        for facet_id in value_by_id[value_id].associated_facet_ids:
            facets.setdefault(facet_id, None)
    return tuple(facets)


def _new_value_supply(
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
    new_value_ids: tuple[str, ...],
    *,
    selection_sha256: str,
) -> PhaseSupply:
    snapshot_sha256 = snapshot.content_hash()
    query_state_sha256 = query_state.content_hash()
    supporting_facet_ids = _supporting_facet_ids(snapshot, new_value_ids)
    rank_result = RankResult(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        ranking_policy_id=SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
        candidates=tuple(
            RankedFacet(
                facet_id=facet_id,
                score=float(len(supporting_facet_ids) - index),
            )
            for index, facet_id in enumerate(supporting_facet_ids)
        ),
    ).validate()
    fusion_decision = FusionDecision(
        snapshot_sha256=snapshot_sha256,
        query_state_sha256=query_state_sha256,
        rank_result_sha256=rank_result.content_hash(),
        fusion_policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
        supporting_facet_ids=supporting_facet_ids,
        selected_value_ids=new_value_ids,
    ).validate()
    return PhaseSupply(
        rank_result=rank_result,
        fusion_decision=fusion_decision,
        action_target_ref=f"{TOOL_ID}:selection={selection_sha256}",
    ).validate()


def lookup_knowledge_targets(
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
    candidate_ids: Sequence[str],
    *,
    max_values_per_candidate: int,
    max_total_values: int,
    already_visible_value_ids: Sequence[str] = (),
    target_index=None,
    selection_mode: str = "targeted",
) -> KnowledgeTargetSelection:
    """Select new knowledge values for explicit ordered task targets.

    Selection is completed under the configured caps before already-visible
    values are removed. Consequently, a visible selected value is never
    replaced by a later value from the same target.
    """

    if selection_mode not in {"targeted", "reread"}:
        raise KnowledgeTargetLookupError("selection_mode must be targeted or reread")
    if not isinstance(snapshot, KnowledgeSnapshot):
        raise KnowledgeTargetLookupError("snapshot must be a KnowledgeSnapshot")
    if not isinstance(query_state, QueryState):
        raise KnowledgeTargetLookupError("query_state must be a QueryState")
    snapshot.validate()
    query_state.validate()
    request = CandidateContractRequest.from_ids(candidate_ids)
    per_candidate_bound = _selection_bound(
        max_values_per_candidate, field="max_values_per_candidate"
    )
    total_bound = _selection_bound(max_total_values, field="max_total_values")

    local_value_ids = frozenset(value.value_id for value in snapshot.values)
    visible = _already_visible_ids(
        already_visible_value_ids, local_value_ids=local_value_ids
    )
    visible_set = frozenset(visible)
    index = _target_value_index(snapshot)
    if target_index is not None:
        from .released_target_index import ReleasedTargetIndex

        if not isinstance(target_index, ReleasedTargetIndex):
            raise KnowledgeTargetLookupError("target index must be a released source binding")
        target_index.validate(snapshot)
        index = target_index.mappings
    selected_value_ids, mappings = select_candidate_semantic_values(
        request.candidate_ids,
        index,
        max_values_per_candidate=per_candidate_bound,
        max_total_values=total_bound,
    )
    if selection_mode == "reread":
        selected_value_ids = visible[:total_bound]
    new_value_ids = tuple(
        value_id for value_id in selected_value_ids if value_id not in visible_set
    )
    already_visible_selected_value_ids = tuple(
        value_id for value_id in selected_value_ids if value_id in visible_set
    )
    disposition = (
        "acquired"
        if new_value_ids
        else "already-visible"
        if selected_value_ids
        else "no-mapping"
    )
    audit: dict[str, object] = {
        "schema": SCHEMA,
        "snapshot_sha256": snapshot.content_hash(),
        "query_state_sha256": query_state.content_hash(),
        "candidate_ids": list(request.candidate_ids),
        "selection_policy_id": SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
        "max_values_per_candidate": per_candidate_bound,
        "max_total_values": total_bound,
        "mappings": mappings,
        "selected_value_ids": list(selected_value_ids),
        "new_value_ids": list(new_value_ids),
        "already_visible_selected_value_ids": list(already_visible_selected_value_ids),
        "supply_disposition": disposition,
    }
    if selection_mode != "targeted":
        audit["selection_mode"] = selection_mode
    if target_index is not None:
        audit["target_index"] = dict(target_index.receipt)
    audit["selection_sha256"] = content_hash(audit)
    supply = (
        _new_value_supply(
            snapshot,
            query_state,
            new_value_ids,
            selection_sha256=str(audit["selection_sha256"]),
        )
        if new_value_ids
        else None
    )
    return KnowledgeTargetSelection(
        supply=supply,
        selected_value_ids=selected_value_ids,
        audit=audit,
    )


__all__ = [
    "SCHEMA",
    "TOOL_ID",
    "KnowledgeTargetLookupError",
    "KnowledgeTargetSelection",
    "lookup_knowledge_targets",
]
