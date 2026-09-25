"""Pure proposal of legal SLURP intents from a sealed Perception state and TRAIN values.

The proposal is a separate consumption artifact. It never rewrites Perception,
selects a final answer, or reads labels from the current task row.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .errors import RailsError
from .hashing import content_hash
from .knowledge import AgentStateArtifact, KnowledgeSnapshot, QueryState, ValueBundle
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    SlurpIntentHypothesisError,
    parse_slurp_intent_hypothesis_state,
)

if TYPE_CHECKING:
    from .controllers import PhaseSupply


PROPOSAL_SCHEMA = "saea-slurp-exemplar-candidate-proposal-v1"
MAX_PROPOSAL_CANDIDATES = 32


class CandidateProposalError(RailsError):
    """A proposal cannot be tied to its sealed source and selected values."""


def _sha(value: object, field: str) -> str:
    if (
        not isinstance(value, str) or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise CandidateProposalError(f"{field} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True)
class ExemplarAddition:
    intent_id: str
    supporting_exemplar_value_ids: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "intent_id": self.intent_id,
            "supporting_exemplar_value_ids": list(self.supporting_exemplar_value_ids),
        }


@dataclass(frozen=True)
class SelectedExemplar:
    value_id: str
    task_target: str
    content_sha256: str
    value_sha256: str

    def as_json(self) -> dict[str, str]:
        return {
            "value_id": self.value_id,
            "task_target": self.task_target,
            "content_sha256": self.content_sha256,
            "value_sha256": self.value_sha256,
        }


@dataclass(frozen=True)
class CandidateProposal:
    sample_id: str
    original_candidate_ids: tuple[str, ...]
    candidate_ids: tuple[str, ...]
    additions: tuple[ExemplarAddition, ...]
    original_state_id: str
    original_state_sha256: str
    original_response_sha256: str
    original_query_state_sha256: str
    exemplar_snapshot_sha256: str
    exemplar_selection_sha256: str
    selected_exemplars: tuple[SelectedExemplar, ...]
    max_candidates: int

    def as_json(self) -> dict[str, object]:
        return {
            "schema": PROPOSAL_SCHEMA,
            "sample_id": self.sample_id,
            "original_candidate_ids": list(self.original_candidate_ids),
            "candidate_ids": list(self.candidate_ids),
            "additions": [item.as_json() for item in self.additions],
            "original_state_id": self.original_state_id,
            "original_state_sha256": self.original_state_sha256,
            "original_response_sha256": self.original_response_sha256,
            "original_query_state_sha256": self.original_query_state_sha256,
            "exemplar_snapshot_sha256": self.exemplar_snapshot_sha256,
            "exemplar_selection_sha256": self.exemplar_selection_sha256,
            "selected_exemplars": [item.as_json() for item in self.selected_exemplars],
            "max_candidates": self.max_candidates,
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    def model_text(self) -> str:
        """Render only task-usable labels and transparent, non-authoritative provenance."""
        originals = ", ".join(self.original_candidate_ids)
        lines = [
            "Original Perception intent candidates, in model order: " + originals + ".",
            "Additional exemplar-supported intent possibilities:",
        ]
        if self.additions:
            lines.extend(
                f"- {item.intent_id}: supported by "
                f"{len(item.supporting_exemplar_value_ids)} selected TRAIN speech exemplar(s)."
                for item in self.additions
            )
        else:
            lines.append("- None.")
        lines.append(
            "Exemplar frequency is not confidence. These proposals are evidence "
            "cues, not a hard answer filter. The full legal inventory remains "
            "available; task judgment still depends on the speech and evidence."
        )
        return "\n".join(lines)


def build_candidate_proposal(
    *,
    sample_id: str,
    original_state: AgentStateArtifact,
    parsed_candidates: tuple[str, ...],
    exemplar_values: tuple[ValueBundle, ...],
    exemplar_snapshot_sha256: str,
    exemplar_selection_sha256: str,
    legal_candidate_ids: tuple[str, ...],
    max_candidates: int,
) -> CandidateProposal:
    """Append unseen legal TRAIN labels by frequency, with lexical ties.

    The caller supplies the actual ordered selection from the released exemplar
    snapshot. This pure function validates each value and records its digest;
    the named-store caller remains responsible for proving snapshot membership
    and that the selection hash belongs to its rank/fusion decision.
    """
    if not isinstance(sample_id, str) or not sample_id:
        raise CandidateProposalError("sample_id must be non-empty")
    if not isinstance(original_state, AgentStateArtifact):
        raise CandidateProposalError("original_state must be an AgentStateArtifact")
    try:
        original_state.validate()
    except RailsError as error:
        raise CandidateProposalError(str(error)) from error
    if original_state.state_kind != "phase:perception":
        raise CandidateProposalError("original state must be sealed Perception")
    response_sha = hashlib.sha256(original_state.content.encode("utf-8")).hexdigest()
    if response_sha != original_state.source_response_sha256:
        raise CandidateProposalError("Perception content differs from its real response hash")
    _sha(exemplar_snapshot_sha256, "exemplar_snapshot_sha256")
    _sha(exemplar_selection_sha256, "exemplar_selection_sha256")
    if (
        not isinstance(legal_candidate_ids, tuple) or not legal_candidate_ids
        or any(not isinstance(item, str) or not item for item in legal_candidate_ids)
        or len(set(legal_candidate_ids)) != len(legal_candidate_ids)
    ):
        raise CandidateProposalError("legal_candidate_ids must be a unique nonempty tuple")
    if (
        not isinstance(parsed_candidates, tuple) or not parsed_candidates
        or any(not isinstance(item, str) or not item for item in parsed_candidates)
        or len(set(parsed_candidates)) != len(parsed_candidates)
        or not set(parsed_candidates) <= set(legal_candidate_ids)
    ):
        raise CandidateProposalError("parsed candidates must be ordered, unique, and legal")
    if (
        isinstance(max_candidates, bool) or not isinstance(max_candidates, int)
        or max_candidates < len(parsed_candidates)
        or max_candidates > MAX_PROPOSAL_CANDIDATES
    ):
        raise CandidateProposalError("max_candidates is outside the legal proposal bound")
    try:
        parsed = parse_slurp_intent_hypothesis_state(
            original_state,
            expected_sample_id=sample_id,
            legal_intent_ids=legal_candidate_ids,
            max_candidates=min(3, len(legal_candidate_ids)),
            compact_source_phase="perception",
            projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        )
    except SlurpIntentHypothesisError as error:
        raise CandidateProposalError(str(error)) from error
    if tuple(item.intent_id for item in parsed.candidates) != parsed_candidates:
        raise CandidateProposalError(
            "parsed candidates differ from the sealed Perception projection"
        )
    if not isinstance(exemplar_values, tuple):
        raise CandidateProposalError("exemplar_values must be an ordered tuple")
    seen_values: set[str] = set()
    support: dict[str, list[str]] = {}
    selected: list[SelectedExemplar] = []
    for value in exemplar_values:
        if not isinstance(value, ValueBundle):
            raise CandidateProposalError("selected exemplar must be a ValueBundle")
        try:
            value.validate()
        except RailsError as error:
            raise CandidateProposalError(str(error)) from error
        if value.value_id in seen_values:
            raise CandidateProposalError("selected exemplar IDs must be unique")
        seen_values.add(value.value_id)
        if value.task_target not in legal_candidate_ids:
            raise CandidateProposalError("selected exemplar lacks a legal TRAIN intent label")
        support.setdefault(value.task_target, []).append(value.value_id)
        selected.append(SelectedExemplar(
            value_id=value.value_id,
            task_target=value.task_target,
            content_sha256=hashlib.sha256(value.content.encode("utf-8")).hexdigest(),
            value_sha256=content_hash(value.as_json()),
        ))
    ordered = sorted(
        (intent for intent in support if intent not in parsed_candidates),
        key=lambda intent: (-len(support[intent]), intent),
    )
    additions = tuple(
        ExemplarAddition(intent, tuple(support[intent]))
        for intent in ordered[:max_candidates - len(parsed_candidates)]
    )
    return CandidateProposal(
        sample_id=sample_id,
        original_candidate_ids=parsed_candidates,
        candidate_ids=parsed_candidates + tuple(item.intent_id for item in additions),
        additions=additions,
        original_state_id=original_state.state_id,
        original_state_sha256=original_state.content_hash(),
        original_response_sha256=original_state.source_response_sha256,
        original_query_state_sha256=original_state.source_query_state_sha256,
        exemplar_snapshot_sha256=exemplar_snapshot_sha256,
        exemplar_selection_sha256=exemplar_selection_sha256,
        selected_exemplars=tuple(selected),
        max_candidates=max_candidates,
    )





def build_candidate_proposal_from_selection(
    *,
    sample_id: str,
    original_state: AgentStateArtifact,
    parsed_candidates: tuple[str, ...],
    exemplar_snapshot: KnowledgeSnapshot,
    exemplar_supply: PhaseSupply,
    query_state: QueryState,
    legal_candidate_ids: tuple[str, ...],
    max_candidates: int,
) -> CandidateProposal:
    """Bind proposals to the actual local named-store rank/fusion selection.

    Use this boundary before qualifying local value IDs into the composite
    snapshot. The caller has already validated the released store and split
    exclusion; no new retrieval or filesystem read occurs here.
    """
    from .controllers import PhaseSupply

    if not isinstance(exemplar_snapshot, KnowledgeSnapshot):
        raise CandidateProposalError("proposal selection requires a KnowledgeSnapshot")
    if not isinstance(exemplar_supply, PhaseSupply) or not isinstance(query_state, QueryState):
        raise CandidateProposalError("proposal selection requires a PhaseSupply and QueryState")
    try:
        exemplar_snapshot.validate()
        exemplar_supply.validate()
        query_state.validate()
    except RailsError as error:
        raise CandidateProposalError(str(error)) from error
    rank, fusion = exemplar_supply.rank_result, exemplar_supply.fusion_decision
    snapshot_sha, query_sha = exemplar_snapshot.content_hash(), query_state.content_hash()
    if query_state.query_sample_id != sample_id:
        raise CandidateProposalError("proposal selection belongs to another sample")
    if any(item.snapshot_sha256 != snapshot_sha or item.query_state_sha256 != query_sha
           for item in (rank, fusion)):
        raise CandidateProposalError("proposal selection has a different snapshot or query")
    if fusion.rank_result_sha256 != rank.content_hash():
        raise CandidateProposalError("proposal fusion does not bind its rank result")
    values = {value.value_id: value for value in exemplar_snapshot.values}
    selected_ids = fusion.selected_value_ids
    facets = {facet.facet_id for facet in exemplar_snapshot.facets}
    if (any(value_id not in values for value_id in selected_ids)
            or any(facet_id not in facets for facet_id in fusion.supporting_facet_ids)
            or any(item.facet_id not in facets for item in rank.candidates)):
        raise CandidateProposalError("proposal selection cites absent released values or facets")
    selected = tuple(values[value_id] for value_id in selected_ids)
    if any(sample_id in value.source_sample_ids for value in selected):
        raise CandidateProposalError("current sample cannot supply its own candidate labels")
    return build_candidate_proposal(
        sample_id=sample_id, original_state=original_state,
        parsed_candidates=parsed_candidates, exemplar_values=selected,
        exemplar_snapshot_sha256=snapshot_sha,
        exemplar_selection_sha256=fusion.content_hash(),
        legal_candidate_ids=legal_candidate_ids, max_candidates=max_candidates,
    )


__all__ = [
    "CandidateProposal", "CandidateProposalError", "ExemplarAddition",
    "SelectedExemplar", "build_candidate_proposal",
    "build_candidate_proposal_from_selection",
]
