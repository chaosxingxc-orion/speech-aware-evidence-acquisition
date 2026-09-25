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
        return render_candidate_proposal_text(
            self.original_candidate_ids,
            tuple((item.intent_id, len(item.supporting_exemplar_value_ids))
                  for item in self.additions),
        )


def render_candidate_proposal_text(original_candidate_ids, added_support_counts):
    """Render task text; source validation remains the proposal builder's job."""
    lines = [
        "Original Perception intent candidates, in model order: "
        + ", ".join(original_candidate_ids) + ".",
        "Additional exemplar-supported intent possibilities:",
    ]
    if added_support_counts:
        lines.extend(
            f"- {intent}: supported by {count} selected TRAIN speech exemplar(s)."
            for intent, count in added_support_counts
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



def validate_candidate_proposal_consumption(
    episode_receipt, *, sample_id, trace_records, error_type=ValueError,
):
    """Join all completed continuation contacts to the proposal and real requests.

    Snapshot membership and release identity are checked by the bound supply
    router before contact. This independent seal/read check proves actual
    downstream consumption and ties the derived view to the raw Perception.
    """
    from collections.abc import Mapping

    def refuse(message):
        raise error_type("candidate proposal custody: " + message)

    block = episode_receipt.get("candidate_proposal")
    if block is None:
        return
    if (
        not isinstance(block, Mapping)
        or set(block) != {"schema", "proposals", "contacts", "prepared_without_response"}
        or block["schema"] != "saea-native-candidate-proposal-consumption-v1"
        or not isinstance(block["proposals"], Mapping)
        or not isinstance(block["contacts"], list)
        or not isinstance(block["prepared_without_response"], list)
    ):
        refuse("malformed consumption receipt")
    expected = {}
    perception_contacts = []
    visits = list(episode_receipt.get("role_visits", ()))
    if isinstance(episode_receipt.get("interrupted_role"), Mapping):
        visits.append(episode_receipt["interrupted_role"])
    for visit in visits:
        contacts = visit.get("execution_receipt", {}).get("contacts", ())
        if visit.get("role_id") == "perception":
            perception_contacts.extend(contacts)
            continue
        for contact in contacts:
            expected[contact["agent_contact_id"]] = (visit["role_id"], contact)
    actual = block["contacts"]
    if (any(not isinstance(row, Mapping) for row in actual)
            or len(actual) != len(expected)
            or {row.get("contact_id") for row in actual} != set(expected)):
        refuse("completed downstream contacts do not match the whole native trajectory")
    proposals = block["proposals"]
    if len(proposals) != (1 if actual or block["prepared_without_response"] else 0):
        refuse("one episode must retain one proposal when its continuation is reached")
    if not proposals:
        return
    digest, document = next(iter(proposals.items()))
    if (not isinstance(document, Mapping) or document.get("schema") != PROPOSAL_SCHEMA
            or content_hash(document) != digest or document.get("sample_id") != sample_id):
        refuse("proposal document hash or sample differs")
    try:
        fields = {k: v for k, v in document.items()
                  if k not in {"schema", "additions", "selected_exemplars",
                               "original_candidate_ids", "candidate_ids"}}
        proposal = CandidateProposal(
            **fields,
            additions=tuple(ExemplarAddition(
                item["intent_id"], tuple(item["supporting_exemplar_value_ids"]),
            ) for item in document["additions"]),
            selected_exemplars=tuple(SelectedExemplar(**item) for item in document["selected_exemplars"]),
            original_candidate_ids=tuple(document["original_candidate_ids"]),
            candidate_ids=tuple(document["candidate_ids"]),
        )
        if proposal.as_json() != document:
            refuse("proposal has undeclared fields")
    except (KeyError, TypeError) as error:
        refuse(f"proposal shape is invalid: {error}")
    source_states = [
        state for payload in trace_records.values()
        if isinstance(payload.get("org_final_query_state"), Mapping)
        and payload["org_final_query_state"].get("query_sample_id") == sample_id
        for state in payload.get("org_agent_states", ())
        if state.get("state_id") == proposal.original_state_id
    ]
    if len(source_states) != 1:
        refuse("original Perception is absent or duplicated in the sealed state chain")
    source = AgentStateArtifact.from_json(source_states[0])
    if (
        source.state_kind != "phase:perception"
        or source.content_hash() != proposal.original_state_sha256
        or source.source_query_state_sha256 != proposal.original_query_state_sha256
        or source.source_response_sha256 != proposal.original_response_sha256
        or hashlib.sha256(source.content.encode("utf-8")).hexdigest() != proposal.original_response_sha256
        or not any(contact.get("response_text_sha256") == proposal.original_response_sha256
                   for contact in perception_contacts)
    ):
        refuse("proposal has a different raw Perception source")
    authority_labels = tuple(dict.fromkeys((
        *proposal.candidate_ids, *(item.task_target for item in proposal.selected_exemplars),
    )))
    parsed = parse_slurp_intent_hypothesis_state(
        source, expected_sample_id=sample_id, legal_intent_ids=authority_labels,
        max_candidates=min(3, len(authority_labels)), compact_source_phase="perception",
        projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        # A reduced authority set bounds distinct labels, not raw duplicate positions.
        raw_max_candidates=3,
    )
    if tuple(item.intent_id for item in parsed.candidates) != proposal.original_candidate_ids:
        refuse("original candidates differ from raw Perception")
    support = {}
    for item in proposal.selected_exemplars:
        support.setdefault(item.task_target, []).append(item.value_id)
    order = sorted(
        (label for label in support if label not in proposal.original_candidate_ids),
        key=lambda label: (-len(support[label]), label),
    )[:proposal.max_candidates - len(proposal.original_candidate_ids)]
    expected_additions = tuple(ExemplarAddition(label, tuple(support[label])) for label in order)
    if (
        proposal.additions != expected_additions
        or proposal.candidate_ids != proposal.original_candidate_ids + tuple(order)
        or len(proposal.candidate_ids) != len(set(proposal.candidate_ids))
    ):
        refuse("proposal differs from its deterministic exemplar interpretation")
    text = proposal.model_text()
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    for row in actual:
        role_id, source_contact = expected[row["contact_id"]]
        if (row.get("role_kind") != role_id or row.get("proposal_sha256") != digest
                or row.get("rendered_text_sha256") != text_hash
                or any(row.get(key) != source_contact.get(key) for key in (
                    "request_id", "request_sha256", "response_sha256",
                ))):
            refuse("proposal contact differs from the native execution receipt")
        request = trace_records.get(row["request_id"] + "/request", {})
        response = trace_records.get(row["request_id"] + "/response", {})
        body = request.get("payload", {})
        if (request.get("payload_sha256") != row["request_sha256"]
                or body.get("sample_id") != sample_id
                or response.get("response_sha256") != row["response_sha256"]):
            refuse("proposal contact has no matching raw request and response")
        evidence = [part for part in body.get("supplied_evidence", ())
                    if str(part.get("evidence_id", "")).startswith("candidate-proposal:")]
        if (len(evidence) != 1
                or evidence[0].get("evidence_id") != "candidate-proposal:" + digest
                or evidence[0].get("content") != text):
            refuse("the actual request did not consume the exact proposal")
        org = trace_records.get(row["contact_id"] + "/candidate-proposal", {})
        if org.get("org_candidate_proposal") != row:
            refuse("proposal contact lost its separate ORG derivation")

__all__ = [
    "CandidateProposal", "CandidateProposalError", "ExemplarAddition",
    "SelectedExemplar", "build_candidate_proposal",
    "build_candidate_proposal_from_selection", "validate_candidate_proposal_consumption",
]
