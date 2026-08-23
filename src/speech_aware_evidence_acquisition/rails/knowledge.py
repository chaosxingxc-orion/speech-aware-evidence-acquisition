"""Task-independent contracts for knowledge BUILD, USE, and optimization.

This module is the strict seam between two processes that earlier probes
accidentally mixed together:

* BUILD consumes only a TRAIN partition and freezes a content-addressed
  :class:`KnowledgeSnapshot`.
* USE consumes that frozen snapshot from a disjoint DEV query partition.
  Every :class:`QueryState` keeps the original speech-feature packet bound;
  agent state and previously retrieved values are auxiliary references, never
  a replacement text-only query.

The contracts deliberately do not prescribe one task, one label vocabulary,
or one retrieval implementation.  A key is a collection of independently
rankable facets (content, speaker, entity, domain, operation, or a task-defined
dimension); a value carries sample-associated evidence and optional prior/task
metadata; ranking and fusion remain separately hash-bound decisions.

No model or filesystem access occurs here.  Existing drivers can adopt these
contracts incrementally while their historical receipts remain readable.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Mapping

from .errors import RailsError
from .hashing import content_hash

KNOWLEDGE_SNAPSHOT_VERSION = "knowledge-snapshot-v1"
QUERY_STATE_VERSION = "knowledge-query-state-v1"
RANK_RESULT_VERSION = "knowledge-rank-result-v1"
FUSION_DECISION_VERSION = "knowledge-fusion-decision-v1"
AGENT_STEP_TRANSITION_VERSION = "knowledge-agent-step-transition-v1"
AGENT_STATE_ARTIFACT_VERSION = "knowledge-agent-state-artifact-v1"

AGENT_ACTION_KINDS = frozenset(
    {
        "stop",
        "organize",
        "acquire",
        "expand",
        "contrast",
        "verify",
        "backtrack",
    }
)
_SUPPLY_ACTION_KINDS = frozenset({"acquire", "expand", "contrast"})

TRAIN_PARTITION_ROLE = "train"
DEV_PARTITION_ROLE = "dev"

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RailsError(f"{field} must be a non-empty string")
    return value


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise RailsError(f"{field} must be a 64-hex SHA-256")
    return value


def _require_unique_texts(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if not isinstance(values, tuple):
        raise RailsError(f"{field} must be a tuple")
    if len(set(values)) != len(values):
        raise RailsError(f"{field} must contain unique values")
    for value in values:
        _require_text(value, field=f"{field} entry")
    return values


@dataclass(frozen=True)
class KeyFacet:
    """One independently matchable dimension of a knowledge key.

    ``representation_kind`` is open rather than enum-closed so text remains
    the maintainable default while bounded speech/hybrid controls stay
    representable without changing this task-independent contract.
    ``representation`` is either the English key material itself or a stable
    content-addressed reference, as declared by ``representation_kind``.
    """

    facet_id: str
    dimension: str
    representation_kind: str
    representation: str
    source_sample_ids: tuple[str, ...]
    parent_facet_ids: tuple[str, ...] = ()

    def validate(self) -> "KeyFacet":
        _require_text(self.facet_id, field="KeyFacet.facet_id")
        _require_text(self.dimension, field="KeyFacet.dimension")
        _require_text(self.representation_kind, field="KeyFacet.representation_kind")
        _require_text(self.representation, field="KeyFacet.representation")
        _require_unique_texts(
            self.source_sample_ids, field="KeyFacet.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError(
                "KeyFacet.source_sample_ids must bind the facet to TRAIN samples"
            )
        _require_unique_texts(self.parent_facet_ids, field="KeyFacet.parent_facet_ids")
        if self.facet_id in self.parent_facet_ids:
            raise RailsError("KeyFacet cannot name itself as a parent")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "facet_id": self.facet_id,
            "dimension": self.dimension,
            "representation_kind": self.representation_kind,
            "representation": self.representation,
            "source_sample_ids": list(self.source_sample_ids),
            "parent_facet_ids": list(self.parent_facet_ids),
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "KeyFacet":
        return cls(
            facet_id=document["facet_id"],
            dimension=document["dimension"],
            representation_kind=document["representation_kind"],
            representation=document["representation"],
            source_sample_ids=tuple(document.get("source_sample_ids", [])),
            parent_facet_ids=tuple(document.get("parent_facet_ids", [])),
        ).validate()


@dataclass(frozen=True)
class ValueBundle:
    """Sample-associated evidence returned by knowledge retrieval.

    ``content`` is the task-helpful payload that can later become an
    ``EvidenceItem``/``SupplyItem``.  ``task_target`` and ``prior_score`` are
    metadata: they model train-derived associations and priors but are not key
    text.  This keeps key matching separate from the result/evidence carried by
    the value.
    """

    value_id: str
    content: str
    associated_facet_ids: tuple[str, ...]
    source_sample_ids: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    task_target: str | None = None
    prior_score: float | None = None

    def validate(self) -> "ValueBundle":
        _require_text(self.value_id, field="ValueBundle.value_id")
        _require_text(self.content, field="ValueBundle.content")
        _require_unique_texts(
            self.associated_facet_ids,
            field="ValueBundle.associated_facet_ids",
        )
        if not self.associated_facet_ids:
            raise RailsError(
                "ValueBundle must be associated with at least one key facet"
            )
        _require_unique_texts(
            self.source_sample_ids, field="ValueBundle.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError(
                "ValueBundle.source_sample_ids must bind the value to TRAIN samples"
            )
        _require_unique_texts(self.provenance_refs, field="ValueBundle.provenance_refs")
        if not self.provenance_refs:
            raise RailsError("ValueBundle.provenance_refs must be non-empty")
        if self.task_target is not None:
            _require_text(self.task_target, field="ValueBundle.task_target")
        if self.prior_score is not None and (
            isinstance(self.prior_score, bool)
            or not isinstance(self.prior_score, (int, float))
            or not math.isfinite(float(self.prior_score))
        ):
            raise RailsError("ValueBundle.prior_score must be finite or None")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "value_id": self.value_id,
            "content": self.content,
            "associated_facet_ids": list(self.associated_facet_ids),
            "source_sample_ids": list(self.source_sample_ids),
            "provenance_refs": list(self.provenance_refs),
            "task_target": self.task_target,
            "prior_score": self.prior_score,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ValueBundle":
        return cls(
            value_id=document["value_id"],
            content=document["content"],
            associated_facet_ids=tuple(document.get("associated_facet_ids", [])),
            source_sample_ids=tuple(document.get("source_sample_ids", [])),
            provenance_refs=tuple(document.get("provenance_refs", [])),
            task_target=document.get("task_target"),
            prior_score=document.get("prior_score"),
        ).validate()


@dataclass(frozen=True)
class KnowledgeSnapshot:
    """A content-addressed, immutable-by-contract TRAIN knowledge build."""

    snapshot_id: str
    source_split_identity_hash: str
    source_sample_ids: tuple[str, ...]
    builder_policy_id: str
    facets: tuple[KeyFacet, ...]
    values: tuple[ValueBundle, ...]
    source_partition_role: str = TRAIN_PARTITION_ROLE
    snapshot_version: str = KNOWLEDGE_SNAPSHOT_VERSION

    def validate(self) -> "KnowledgeSnapshot":
        _require_text(self.snapshot_id, field="KnowledgeSnapshot.snapshot_id")
        _require_sha256(
            self.source_split_identity_hash,
            field="KnowledgeSnapshot.source_split_identity_hash",
        )
        if self.source_partition_role != TRAIN_PARTITION_ROLE:
            raise RailsError(
                "KnowledgeSnapshot.source_partition_role must be 'train'; DEV/TEST "
                "samples cannot construct runtime knowledge"
            )
        if self.snapshot_version != KNOWLEDGE_SNAPSHOT_VERSION:
            raise RailsError(
                f"KnowledgeSnapshot.snapshot_version must be "
                f"{KNOWLEDGE_SNAPSHOT_VERSION!r}"
            )
        _require_text(
            self.builder_policy_id, field="KnowledgeSnapshot.builder_policy_id"
        )
        _require_unique_texts(
            self.source_sample_ids, field="KnowledgeSnapshot.source_sample_ids"
        )
        if not self.source_sample_ids:
            raise RailsError("KnowledgeSnapshot.source_sample_ids must be non-empty")
        if not isinstance(self.facets, tuple) or not self.facets:
            raise RailsError("KnowledgeSnapshot.facets must be a non-empty tuple")
        if not isinstance(self.values, tuple) or not self.values:
            raise RailsError("KnowledgeSnapshot.values must be a non-empty tuple")

        facet_ids: set[str] = set()
        used_source_ids: set[str] = set()
        for facet in self.facets:
            if not isinstance(facet, KeyFacet):
                raise RailsError(
                    "KnowledgeSnapshot.facets entries must be KeyFacet instances"
                )
            facet.validate()
            if facet.facet_id in facet_ids:
                raise RailsError(
                    f"KnowledgeSnapshot has duplicate facet_id {facet.facet_id!r}"
                )
            facet_ids.add(facet.facet_id)
            used_source_ids.update(facet.source_sample_ids)
        for facet in self.facets:
            unknown_parents = set(facet.parent_facet_ids) - facet_ids
            if unknown_parents:
                raise RailsError(
                    f"KeyFacet {facet.facet_id!r} references unknown parent facets "
                    f"{sorted(unknown_parents)}"
                )
        self._assert_acyclic_facets()

        value_ids: set[str] = set()
        for value in self.values:
            if not isinstance(value, ValueBundle):
                raise RailsError(
                    "KnowledgeSnapshot.values entries must be ValueBundle instances"
                )
            value.validate()
            if value.value_id in value_ids:
                raise RailsError(
                    f"KnowledgeSnapshot has duplicate value_id {value.value_id!r}"
                )
            value_ids.add(value.value_id)
            unknown_facets = set(value.associated_facet_ids) - facet_ids
            if unknown_facets:
                raise RailsError(
                    f"ValueBundle {value.value_id!r} references unknown facets "
                    f"{sorted(unknown_facets)}"
                )
            used_source_ids.update(value.source_sample_ids)

        declared_source_ids = set(self.source_sample_ids)
        unknown_source_ids = used_source_ids - declared_source_ids
        if unknown_source_ids:
            raise RailsError(
                "KnowledgeSnapshot records reference source samples outside the frozen "
                f"TRAIN roster: {sorted(unknown_source_ids)}"
            )
        unused_source_ids = declared_source_ids - used_source_ids
        if unused_source_ids:
            raise RailsError(
                "KnowledgeSnapshot source roster contains samples with no facet or value "
                f"provenance: {sorted(unused_source_ids)}"
            )
        return self

    def _assert_acyclic_facets(self) -> None:
        parents = {facet.facet_id: facet.parent_facet_ids for facet in self.facets}
        active: set[str] = set()
        complete: set[str] = set()

        def visit(facet_id: str) -> None:
            if facet_id in complete:
                return
            if facet_id in active:
                raise RailsError("KnowledgeSnapshot facet hierarchy contains a cycle")
            active.add(facet_id)
            for parent_id in parents[facet_id]:
                visit(parent_id)
            active.remove(facet_id)
            complete.add(facet_id)

        for facet_id in parents:
            visit(facet_id)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "snapshot_version": self.snapshot_version,
            "snapshot_id": self.snapshot_id,
            "source_partition_role": self.source_partition_role,
            "source_split_identity_hash": self.source_split_identity_hash,
            "source_sample_ids": list(self.source_sample_ids),
            "builder_policy_id": self.builder_policy_id,
            "facets": [facet.as_json() for facet in self.facets],
            "values": [value.as_json() for value in self.values],
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    def frozen_json(self) -> dict[str, object]:
        document = self.as_json()
        return {**document, "snapshot_sha256": content_hash(document)}

    @classmethod
    def from_frozen_json(cls, document: Mapping[str, object]) -> "KnowledgeSnapshot":
        claimed_hash = _require_sha256(
            document.get("snapshot_sha256"), field="KnowledgeSnapshot.snapshot_sha256"
        )
        body = dict(document)
        body.pop("snapshot_sha256", None)
        if content_hash(body) != claimed_hash:
            raise RailsError("KnowledgeSnapshot frozen document hash mismatch")
        snapshot = cls(
            snapshot_id=body["snapshot_id"],
            source_partition_role=body["source_partition_role"],
            source_split_identity_hash=body["source_split_identity_hash"],
            source_sample_ids=tuple(body.get("source_sample_ids", [])),
            builder_policy_id=body["builder_policy_id"],
            facets=tuple(KeyFacet.from_json(item) for item in body.get("facets", [])),
            values=tuple(
                ValueBundle.from_json(item) for item in body.get("values", [])
            ),
            snapshot_version=body["snapshot_version"],
        ).validate()
        if snapshot.content_hash() != claimed_hash:
            raise RailsError(
                "KnowledgeSnapshot contains unsupported or non-canonical fields"
            )
        return snapshot


@dataclass(frozen=True)
class QueryState:
    """A DEV use-time query with speech permanently bound as the primary input."""

    query_id: str
    query_sample_id: str
    speech_packet_id: str
    speech_packet_sha256: str
    use_split_identity_hash: str
    loop_step: int = 0
    agent_state_ids: tuple[str, ...] = ()
    retrieved_value_ids: tuple[str, ...] = ()
    use_partition_role: str = DEV_PARTITION_ROLE
    query_source: str = "speech_features"
    query_state_version: str = QUERY_STATE_VERSION

    def validate(self) -> "QueryState":
        _require_text(self.query_id, field="QueryState.query_id")
        _require_text(self.query_sample_id, field="QueryState.query_sample_id")
        _require_text(self.speech_packet_id, field="QueryState.speech_packet_id")
        _require_sha256(
            self.speech_packet_sha256, field="QueryState.speech_packet_sha256"
        )
        _require_sha256(
            self.use_split_identity_hash,
            field="QueryState.use_split_identity_hash",
        )
        if self.use_partition_role != DEV_PARTITION_ROLE:
            raise RailsError(
                "QueryState.use_partition_role must be 'dev' for Stage-2 USE/OPTIMIZE"
            )
        if self.query_source != "speech_features":
            raise RailsError(
                "QueryState.query_source must be 'speech_features'; agent state or "
                "generated text cannot replace the original speech query"
            )
        if self.query_state_version != QUERY_STATE_VERSION:
            raise RailsError(
                f"QueryState.query_state_version must be {QUERY_STATE_VERSION!r}"
            )
        if (
            isinstance(self.loop_step, bool)
            or not isinstance(self.loop_step, int)
            or self.loop_step < 0
        ):
            raise RailsError("QueryState.loop_step must be a non-negative integer")
        _require_unique_texts(self.agent_state_ids, field="QueryState.agent_state_ids")
        _require_unique_texts(
            self.retrieved_value_ids, field="QueryState.retrieved_value_ids"
        )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "query_state_version": self.query_state_version,
            "query_id": self.query_id,
            "query_sample_id": self.query_sample_id,
            "speech_packet_id": self.speech_packet_id,
            "speech_packet_sha256": self.speech_packet_sha256,
            "query_source": self.query_source,
            "use_partition_role": self.use_partition_role,
            "use_split_identity_hash": self.use_split_identity_hash,
            "loop_step": self.loop_step,
            "agent_state_ids": list(self.agent_state_ids),
            "retrieved_value_ids": list(self.retrieved_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "QueryState":
        return cls(
            query_id=document["query_id"],
            query_sample_id=document["query_sample_id"],
            speech_packet_id=document["speech_packet_id"],
            speech_packet_sha256=document["speech_packet_sha256"],
            query_source=document.get("query_source", "speech_features"),
            use_partition_role=document.get("use_partition_role", DEV_PARTITION_ROLE),
            use_split_identity_hash=document["use_split_identity_hash"],
            loop_step=document.get("loop_step", 0),
            agent_state_ids=tuple(document.get("agent_state_ids", [])),
            retrieved_value_ids=tuple(document.get("retrieved_value_ids", [])),
            query_state_version=document.get(
                "query_state_version", QUERY_STATE_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class RankedFacet:
    facet_id: str
    score: float

    def validate(self) -> "RankedFacet":
        _require_text(self.facet_id, field="RankedFacet.facet_id")
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(float(self.score))
        ):
            raise RailsError("RankedFacet.score must be finite")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {"facet_id": self.facet_id, "score": self.score}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "RankedFacet":
        return cls(facet_id=document["facet_id"], score=document["score"]).validate()


@dataclass(frozen=True)
class RankResult:
    snapshot_sha256: str
    query_state_sha256: str
    ranking_policy_id: str
    candidates: tuple[RankedFacet, ...]
    rank_result_version: str = RANK_RESULT_VERSION

    def validate(self) -> "RankResult":
        _require_sha256(self.snapshot_sha256, field="RankResult.snapshot_sha256")
        _require_sha256(self.query_state_sha256, field="RankResult.query_state_sha256")
        _require_text(self.ranking_policy_id, field="RankResult.ranking_policy_id")
        if self.rank_result_version != RANK_RESULT_VERSION:
            raise RailsError(
                f"RankResult.rank_result_version must be {RANK_RESULT_VERSION!r}"
            )
        if not isinstance(self.candidates, tuple):
            raise RailsError("RankResult.candidates must be a tuple")
        ids: set[str] = set()
        previous_score: float | None = None
        previous_id: str | None = None
        for candidate in self.candidates:
            if not isinstance(candidate, RankedFacet):
                raise RailsError(
                    "RankResult.candidates entries must be RankedFacet instances"
                )
            candidate.validate()
            if candidate.facet_id in ids:
                raise RailsError(
                    f"RankResult has duplicate facet_id {candidate.facet_id!r}"
                )
            ids.add(candidate.facet_id)
            score = float(candidate.score)
            if previous_score is not None and (
                score > previous_score
                or (score == previous_score and candidate.facet_id < previous_id)
            ):
                raise RailsError(
                    "RankResult.candidates must be sorted by score descending, then "
                    "facet_id ascending"
                )
            previous_score = score
            previous_id = candidate.facet_id
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "rank_result_version": self.rank_result_version,
            "snapshot_sha256": self.snapshot_sha256,
            "query_state_sha256": self.query_state_sha256,
            "ranking_policy_id": self.ranking_policy_id,
            "candidates": [candidate.as_json() for candidate in self.candidates],
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "RankResult":
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            query_state_sha256=document["query_state_sha256"],
            ranking_policy_id=document["ranking_policy_id"],
            candidates=tuple(
                RankedFacet.from_json(item) for item in document.get("candidates", [])
            ),
            rank_result_version=document.get(
                "rank_result_version", RANK_RESULT_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class FusionDecision:
    snapshot_sha256: str
    query_state_sha256: str
    rank_result_sha256: str
    fusion_policy_id: str
    supporting_facet_ids: tuple[str, ...]
    selected_value_ids: tuple[str, ...]
    fusion_decision_version: str = FUSION_DECISION_VERSION

    def validate(self) -> "FusionDecision":
        _require_sha256(self.snapshot_sha256, field="FusionDecision.snapshot_sha256")
        _require_sha256(
            self.query_state_sha256, field="FusionDecision.query_state_sha256"
        )
        _require_sha256(
            self.rank_result_sha256, field="FusionDecision.rank_result_sha256"
        )
        _require_text(self.fusion_policy_id, field="FusionDecision.fusion_policy_id")
        _require_unique_texts(
            self.supporting_facet_ids,
            field="FusionDecision.supporting_facet_ids",
        )
        _require_unique_texts(
            self.selected_value_ids,
            field="FusionDecision.selected_value_ids",
        )
        if self.selected_value_ids and not self.supporting_facet_ids:
            raise RailsError(
                "FusionDecision cannot select values without supporting ranked facets"
            )
        if self.fusion_decision_version != FUSION_DECISION_VERSION:
            raise RailsError(
                f"FusionDecision.fusion_decision_version must be "
                f"{FUSION_DECISION_VERSION!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "fusion_decision_version": self.fusion_decision_version,
            "snapshot_sha256": self.snapshot_sha256,
            "query_state_sha256": self.query_state_sha256,
            "rank_result_sha256": self.rank_result_sha256,
            "fusion_policy_id": self.fusion_policy_id,
            "supporting_facet_ids": list(self.supporting_facet_ids),
            "selected_value_ids": list(self.selected_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "FusionDecision":
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            query_state_sha256=document["query_state_sha256"],
            rank_result_sha256=document["rank_result_sha256"],
            fusion_policy_id=document["fusion_policy_id"],
            supporting_facet_ids=tuple(document.get("supporting_facet_ids", [])),
            selected_value_ids=tuple(document.get("selected_value_ids", [])),
            fusion_decision_version=document.get(
                "fusion_decision_version", FUSION_DECISION_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class AgentStateArtifact:
    """One bounded ORG artifact produced from a speech-conditioned contact.

    Agent state is auxiliary organization, never knowledge SUPPLY. The two
    source hashes prove which speech-bound query state and model response
    produced it. ``cited_value_ids`` records any train-built values it
    summarizes without reclassifying those values as newly acquired.
    """

    state_id: str
    state_kind: str
    content: str
    source_query_state_sha256: str
    source_response_sha256: str
    producer_policy_id: str
    cited_value_ids: tuple[str, ...]
    state_artifact_version: str = AGENT_STATE_ARTIFACT_VERSION

    def validate(self) -> "AgentStateArtifact":
        _require_text(self.state_id, field="AgentStateArtifact.state_id")
        _require_text(self.state_kind, field="AgentStateArtifact.state_kind")
        _require_text(self.content, field="AgentStateArtifact.content")
        _require_sha256(
            self.source_query_state_sha256,
            field="AgentStateArtifact.source_query_state_sha256",
        )
        _require_sha256(
            self.source_response_sha256,
            field="AgentStateArtifact.source_response_sha256",
        )
        _require_text(
            self.producer_policy_id,
            field="AgentStateArtifact.producer_policy_id",
        )
        _require_unique_texts(
            self.cited_value_ids,
            field="AgentStateArtifact.cited_value_ids",
        )
        if self.state_artifact_version != AGENT_STATE_ARTIFACT_VERSION:
            raise RailsError(
                "AgentStateArtifact.state_artifact_version must be "
                f"{AGENT_STATE_ARTIFACT_VERSION!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "state_artifact_version": self.state_artifact_version,
            "state_id": self.state_id,
            "state_kind": self.state_kind,
            "content": self.content,
            "source_query_state_sha256": self.source_query_state_sha256,
            "source_response_sha256": self.source_response_sha256,
            "producer_policy_id": self.producer_policy_id,
            "cited_value_ids": list(self.cited_value_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "AgentStateArtifact":
        return cls(
            state_id=document["state_id"],
            state_kind=document["state_kind"],
            content=document["content"],
            source_query_state_sha256=document["source_query_state_sha256"],
            source_response_sha256=document["source_response_sha256"],
            producer_policy_id=document["producer_policy_id"],
            cited_value_ids=tuple(document.get("cited_value_ids", [])),
            state_artifact_version=document.get(
                "state_artifact_version", AGENT_STATE_ARTIFACT_VERSION
            ),
        ).validate()


@dataclass(frozen=True)
class AgentStepTransition:
    """One speech-bound external AgentLoop decision and its information delta.

    The transition distinguishes new train-built values (SUPPLY), values
    merely revisited by verification (USE), generated state references (ORG),
    and information discarded by backtracking. It carries identities only;
    task predictions and post-hoc reward remain outside this runtime contract.
    """

    snapshot_sha256: str
    prior_query_state_sha256: str
    next_query_state_sha256: str | None
    action_kind: str
    action_target_refs: tuple[str, ...]
    new_value_ids: tuple[str, ...]
    used_value_ids: tuple[str, ...]
    dropped_value_ids: tuple[str, ...]
    new_agent_state_ids: tuple[str, ...]
    dropped_agent_state_ids: tuple[str, ...]
    transition_version: str = AGENT_STEP_TRANSITION_VERSION

    def validate(self) -> "AgentStepTransition":
        _require_sha256(
            self.snapshot_sha256,
            field="AgentStepTransition.snapshot_sha256",
        )
        _require_sha256(
            self.prior_query_state_sha256,
            field="AgentStepTransition.prior_query_state_sha256",
        )
        if self.next_query_state_sha256 is not None:
            _require_sha256(
                self.next_query_state_sha256,
                field="AgentStepTransition.next_query_state_sha256",
            )
        if self.transition_version != AGENT_STEP_TRANSITION_VERSION:
            raise RailsError(
                "AgentStepTransition.transition_version must be "
                f"{AGENT_STEP_TRANSITION_VERSION!r}"
            )
        if self.action_kind not in AGENT_ACTION_KINDS:
            raise RailsError(
                "AgentStepTransition.action_kind must be one of "
                f"{sorted(AGENT_ACTION_KINDS)}"
            )
        for field_name in (
            "action_target_refs",
            "new_value_ids",
            "used_value_ids",
            "dropped_value_ids",
            "new_agent_state_ids",
            "dropped_agent_state_ids",
        ):
            _require_unique_texts(
                getattr(self, field_name),
                field=f"AgentStepTransition.{field_name}",
            )
        if set(self.new_value_ids) & set(self.dropped_value_ids):
            raise RailsError(
                "AgentStepTransition cannot add and drop the same value"
            )
        if set(self.new_agent_state_ids) & set(self.dropped_agent_state_ids):
            raise RailsError(
                "AgentStepTransition cannot add and drop the same agent state"
            )

        if self.action_kind == "stop":
            if self.next_query_state_sha256 is not None or any(
                (
                    self.action_target_refs,
                    self.new_value_ids,
                    self.used_value_ids,
                    self.dropped_value_ids,
                    self.new_agent_state_ids,
                    self.dropped_agent_state_ids,
                )
            ):
                raise RailsError(
                    "stop must have no successor, target, or information delta"
                )
            return self

        if self.next_query_state_sha256 is None:
            raise RailsError(
                "a non-stop AgentStepTransition requires a successor QueryState"
            )
        if not self.action_target_refs:
            raise RailsError(
                "a non-stop AgentStepTransition requires action_target_refs"
            )
        if self.action_kind in _SUPPLY_ACTION_KINDS and not self.new_value_ids:
            raise RailsError(
                f"{self.action_kind} must introduce at least one new value"
            )
        if self.action_kind == "organize" and not self.new_agent_state_ids:
            raise RailsError("organize must introduce at least one new agent state")
        if self.action_kind == "verify" and not self.used_value_ids:
            raise RailsError("verify must use at least one previously supplied value")
        if self.action_kind == "backtrack" and not (
            self.dropped_value_ids or self.dropped_agent_state_ids
        ):
            raise RailsError("backtrack must drop at least one value or agent state")
        if self.action_kind != "backtrack" and (
            self.dropped_value_ids or self.dropped_agent_state_ids
        ):
            raise RailsError("only backtrack may drop values or agent states")
        if self.action_kind not in _SUPPLY_ACTION_KINDS and self.new_value_ids:
            raise RailsError(
                "only acquire, expand, or contrast may claim new supplied values"
            )
        if self.action_kind == "backtrack" and (
            self.new_agent_state_ids or self.used_value_ids
        ):
            raise RailsError(
                "backtrack cannot create agent state or claim value use"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "transition_version": self.transition_version,
            "snapshot_sha256": self.snapshot_sha256,
            "prior_query_state_sha256": self.prior_query_state_sha256,
            "next_query_state_sha256": self.next_query_state_sha256,
            "action_kind": self.action_kind,
            "action_target_refs": list(self.action_target_refs),
            "new_value_ids": list(self.new_value_ids),
            "used_value_ids": list(self.used_value_ids),
            "dropped_value_ids": list(self.dropped_value_ids),
            "new_agent_state_ids": list(self.new_agent_state_ids),
            "dropped_agent_state_ids": list(self.dropped_agent_state_ids),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "AgentStepTransition":
        return cls(
            snapshot_sha256=document["snapshot_sha256"],
            prior_query_state_sha256=document["prior_query_state_sha256"],
            next_query_state_sha256=document.get("next_query_state_sha256"),
            action_kind=document["action_kind"],
            action_target_refs=tuple(document.get("action_target_refs", [])),
            new_value_ids=tuple(document.get("new_value_ids", [])),
            used_value_ids=tuple(document.get("used_value_ids", [])),
            dropped_value_ids=tuple(document.get("dropped_value_ids", [])),
            new_agent_state_ids=tuple(document.get("new_agent_state_ids", [])),
            dropped_agent_state_ids=tuple(
                document.get("dropped_agent_state_ids", [])
            ),
            transition_version=document.get(
                "transition_version", AGENT_STEP_TRANSITION_VERSION
            ),
        ).validate()


def assert_agent_step_binding(
    *,
    snapshot: KnowledgeSnapshot,
    prior_query_state: QueryState,
    next_query_state: QueryState | None,
    transition: AgentStepTransition,
) -> None:
    """Prove one Agent step preserves speech and reports its exact delta."""

    snapshot.validate()
    prior_query_state.validate()
    transition.validate()
    snapshot_sha256 = snapshot.content_hash()
    if transition.snapshot_sha256 != snapshot_sha256:
        raise RailsError("AgentStepTransition is bound to a different snapshot")
    if transition.prior_query_state_sha256 != prior_query_state.content_hash():
        raise RailsError("AgentStepTransition is bound to a different prior QueryState")
    if prior_query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "AgentStepTransition query overlaps the TRAIN snapshot source roster"
        )

    if transition.action_kind == "stop":
        if next_query_state is not None:
            raise RailsError("stop cannot bind a successor QueryState")
        return
    if next_query_state is None:
        raise RailsError("non-stop AgentStepTransition requires next_query_state")
    next_query_state.validate()
    if transition.next_query_state_sha256 != next_query_state.content_hash():
        raise RailsError("AgentStepTransition is bound to a different next QueryState")
    if next_query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "AgentStepTransition successor overlaps the TRAIN snapshot source roster"
        )

    stable_query_fields = (
        "query_sample_id",
        "speech_packet_id",
        "speech_packet_sha256",
        "use_split_identity_hash",
        "use_partition_role",
        "query_source",
    )
    if any(
        getattr(prior_query_state, field_name)
        != getattr(next_query_state, field_name)
        for field_name in stable_query_fields
    ):
        raise RailsError(
            "AgentStepTransition must keep the same original speech packet and "
            "DEV query binding across every step"
        )
    if next_query_state.loop_step != prior_query_state.loop_step + 1:
        raise RailsError(
            "AgentStepTransition successor loop_step must increment by exactly one"
        )

    known_value_ids = {value.value_id for value in snapshot.values}
    referenced_value_ids = set(
        (
            *transition.new_value_ids,
            *transition.used_value_ids,
            *transition.dropped_value_ids,
        )
    )
    unknown_value_ids = referenced_value_ids - known_value_ids
    if unknown_value_ids:
        raise RailsError(
            "AgentStepTransition references values outside the frozen snapshot: "
            f"{sorted(unknown_value_ids)}"
        )

    prior_values = set(prior_query_state.retrieved_value_ids)
    next_values = set(next_query_state.retrieved_value_ids)
    prior_states = set(prior_query_state.agent_state_ids)
    next_states = set(next_query_state.agent_state_ids)
    repeated_values = set(transition.new_value_ids) & prior_values
    if repeated_values:
        raise RailsError(
            "AgentStepTransition cannot claim already visible values as new SUPPLY: "
            f"{sorted(repeated_values)}"
        )
    repeated_states = set(transition.new_agent_state_ids) & prior_states
    if repeated_states:
        raise RailsError(
            "AgentStepTransition cannot claim already visible Agent states as new ORG: "
            f"{sorted(repeated_states)}"
        )
    absent_dropped_values = set(transition.dropped_value_ids) - prior_values
    absent_dropped_states = set(transition.dropped_agent_state_ids) - prior_states
    if absent_dropped_values or absent_dropped_states:
        raise RailsError(
            "AgentStepTransition cannot drop values or states that were not visible: "
            f"values={sorted(absent_dropped_values)}, "
            f"states={sorted(absent_dropped_states)}"
        )
    if transition.action_kind == "backtrack":
        expected_values = prior_values - set(transition.dropped_value_ids)
        expected_states = prior_states - set(transition.dropped_agent_state_ids)
    else:
        expected_values = prior_values | set(transition.new_value_ids)
        expected_states = prior_states | set(transition.new_agent_state_ids)
    if next_values != expected_values:
        raise RailsError(
            "AgentStepTransition new/dropped value ids do not match the successor QueryState"
        )
    if next_states != expected_states:
        raise RailsError(
            "AgentStepTransition new/dropped state ids do not match the successor QueryState"
        )
    if not set(transition.used_value_ids).issubset(next_values):
        raise RailsError(
            "AgentStepTransition used values must remain visible in the successor QueryState"
        )


def assert_knowledge_use_binding(
    *,
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
    rank_result: RankResult,
    fusion_decision: FusionDecision,
) -> None:
    """Fail closed unless one DEV decision uses one disjoint TRAIN snapshot.

    This is the machine-enforced BUILD/USE boundary.  It verifies every hash
    edge, query/knowledge sample disjointness, prior-loop value references,
    ranked facet membership, and the final facet-to-value association.
    """

    snapshot.validate()
    query_state.validate()
    rank_result.validate()
    fusion_decision.validate()

    if query_state.query_sample_id in set(snapshot.source_sample_ids):
        raise RailsError(
            "knowledge USE query sample overlaps the TRAIN snapshot source roster"
        )
    snapshot_sha256 = snapshot.content_hash()
    query_state_sha256 = query_state.content_hash()
    if rank_result.snapshot_sha256 != snapshot_sha256:
        raise RailsError("RankResult is bound to a different KnowledgeSnapshot")
    if rank_result.query_state_sha256 != query_state_sha256:
        raise RailsError("RankResult is bound to a different QueryState")
    if fusion_decision.snapshot_sha256 != snapshot_sha256:
        raise RailsError("FusionDecision is bound to a different KnowledgeSnapshot")
    if fusion_decision.query_state_sha256 != query_state_sha256:
        raise RailsError("FusionDecision is bound to a different QueryState")
    if fusion_decision.rank_result_sha256 != rank_result.content_hash():
        raise RailsError("FusionDecision is bound to a different RankResult")

    values_by_id = {value.value_id: value for value in snapshot.values}
    unknown_previous_values = set(query_state.retrieved_value_ids) - set(values_by_id)
    if unknown_previous_values:
        raise RailsError(
            "QueryState references values outside the frozen snapshot: "
            f"{sorted(unknown_previous_values)}"
        )
    facet_ids = {facet.facet_id for facet in snapshot.facets}
    ranked_facet_ids = {candidate.facet_id for candidate in rank_result.candidates}
    unknown_ranked_facets = ranked_facet_ids - facet_ids
    if unknown_ranked_facets:
        raise RailsError(
            f"RankResult references facets outside the snapshot: "
            f"{sorted(unknown_ranked_facets)}"
        )
    support_ids = set(fusion_decision.supporting_facet_ids)
    if not support_ids.issubset(ranked_facet_ids):
        raise RailsError(
            "FusionDecision supporting facets must be present in RankResult"
        )
    unknown_values = set(fusion_decision.selected_value_ids) - set(values_by_id)
    if unknown_values:
        raise RailsError(
            f"FusionDecision selects values outside the snapshot: {sorted(unknown_values)}"
        )
    for value_id in fusion_decision.selected_value_ids:
        value_facets = set(values_by_id[value_id].associated_facet_ids)
        if value_facets.isdisjoint(support_ids):
            raise RailsError(
                f"FusionDecision value {value_id!r} has no association with its "
                "supporting ranked facets"
            )


__all__ = [
    "AGENT_ACTION_KINDS",
    "AGENT_STATE_ARTIFACT_VERSION",
    "AGENT_STEP_TRANSITION_VERSION",
    "AgentStateArtifact",
    "AgentStepTransition",
    "DEV_PARTITION_ROLE",
    "FUSION_DECISION_VERSION",
    "FusionDecision",
    "KNOWLEDGE_SNAPSHOT_VERSION",
    "KeyFacet",
    "KnowledgeSnapshot",
    "QUERY_STATE_VERSION",
    "QueryState",
    "RANK_RESULT_VERSION",
    "RankResult",
    "RankedFacet",
    "TRAIN_PARTITION_ROLE",
    "ValueBundle",
    "assert_agent_step_binding",
    "assert_knowledge_use_binding",
]
