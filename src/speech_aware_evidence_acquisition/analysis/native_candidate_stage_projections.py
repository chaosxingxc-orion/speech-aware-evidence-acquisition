"""Project source-bound C0/C1 candidates from verified native episodes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re

from ..rails.hashing import content_hash
from ..rails.knowledge import AgentStateArtifact
from ..rails.native_episode_receipt import validate_native_episode_delivery_receipt
from ..rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    parse_slurp_intent_hypothesis_state,
)
from .slurp_topn_diagnostics_cli import verify_native_perception_state_contact

PROJECTION_CONFIG_SCHEMA = "saea-native-candidate-stage-projection-config-v1"
PROJECTION_POLICY_ID = "first-perception-and-last-before-delivered-solver-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class NativeCandidateStageProjectionError(ValueError):
    """A verified native source cannot prove its C0/C1 projection."""


@dataclass(frozen=True)
class NativeCandidateStage:
    """One validated Perception visit and its bounded candidate set."""

    visit_index: int
    state_id: str
    state_sha256: str
    query_state_sha256: str
    agent_contact_id: str
    request_id: str
    request_sha256: str
    response_sha256: str
    response_text_sha256: str
    candidate_ids: tuple[str, ...]
    candidate_set_sha256: str

    def diagnostic_json(self) -> dict[str, object]:
        return {
            "visit_index": self.visit_index,
            "state_id": self.state_id,
            "candidate_width": len(self.candidate_ids),
            "state_sha256": self.state_sha256,
            "query_state_sha256": self.query_state_sha256,
            "agent_contact_id": self.agent_contact_id,
            "request_id": self.request_id,
            "request_sha256": self.request_sha256,
            "response_sha256": self.response_sha256,
            "response_text_sha256": self.response_text_sha256,
            "candidate_set_sha256": self.candidate_set_sha256,
        }


@dataclass(frozen=True)
class NativeCandidateStagePair:
    """C0 and C1 for one sample, selected by verified execution order."""

    sample_id: str
    c0: NativeCandidateStage | None
    c1: NativeCandidateStage | None
    refresh_executed: bool
    refresh_after_delivered_solver: bool = False

    @property
    def refresh_used_by_delivered_solver(self) -> bool:
        """Identify a completed refresh that supplied the delivered Solver."""
        return (
            self.c0 is not None and self.c1 is not None
            and self.c0.visit_index != self.c1.visit_index
        )


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NativeCandidateStageProjectionError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NativeCandidateStageProjectionError(f"{label} must be an ordered sequence")
    return value


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise NativeCandidateStageProjectionError(f"{label} must be nonempty text")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise NativeCandidateStageProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _stage(
    *,
    source: object,
    sample_id: str,
    result: Mapping[str, object],
    visit_index: int,
    visit: Mapping[str, object],
    legal_candidate_ids: frozenset[str],
    max_candidates: int,
    projection_policy: str,
) -> NativeCandidateStage:
    execution = _mapping(
        visit.get("execution_receipt"),
        f"Perception execution receipt {sample_id!r}[{visit_index}]",
    )
    contacts = _sequence(execution.get("contacts"), "Perception execution contacts")
    final_contact = _mapping(
        execution.get("final_contact"), "Perception execution final contact"
    )
    if not contacts or final_contact != contacts[-1]:
        raise NativeCandidateStageProjectionError(
            "Perception final contact must equal its last execution contact"
        )
    agent_contact_id = _required_text(
        final_contact.get("agent_contact_id"), "Perception agent contact ID"
    )
    request_id = _required_text(
        final_contact.get("request_id"), "Perception request ID"
    )
    request_sha256 = _sha256(
        final_contact.get("request_sha256"), "Perception request hash"
    )
    response_sha256 = _sha256(
        final_contact.get("response_sha256"), "Perception response hash"
    )
    response_text_sha256 = _sha256(
        final_contact.get("response_text_sha256"), "Perception response text hash"
    )
    result_contacts = _sequence(result.get("contacts"), f"contacts for {sample_id!r}")
    matched_contacts = []
    for raw_contact in result_contacts:
        contact = _mapping(raw_contact, f"contact for {sample_id!r}")
        plan = contact.get("plan")
        if isinstance(plan, Mapping) and plan.get("contact_id") == agent_contact_id:
            matched_contacts.append(contact)
    if len(matched_contacts) != 1:
        raise NativeCandidateStageProjectionError(
            f"Perception visit {visit_index} has no unique serialized contact"
        )
    contact = matched_contacts[0]
    plan = _mapping(contact.get("plan"), "Perception contact plan")
    query_hash = _sha256(
        contact.get("query_state_sha256"), "Perception query state hash"
    )
    if (
        plan.get("query_state_sha256") != query_hash
        or contact.get("response_sha256") != response_text_sha256
    ):
        raise NativeCandidateStageProjectionError(
            f"Perception visit {visit_index} differs from its serialized contact"
        )

    raw_states = _sequence(result.get("agent_states"), f"states for {sample_id!r}")
    expected_state_id = f"{agent_contact_id}:perception:{sample_id}"
    matched_states = [
        raw
        for raw in raw_states
        if isinstance(raw, Mapping) and raw.get("state_id") == expected_state_id
    ]
    if len(matched_states) != 1:
        raise NativeCandidateStageProjectionError(
            f"Perception visit {visit_index} has no unique sealed phase state"
        )
    try:
        state = AgentStateArtifact.from_json(matched_states[0]).validate()
        if (
            state.state_kind != "phase:perception"
            or state.source_query_state_sha256 != query_hash
            or state.source_response_sha256 != response_text_sha256
        ):
            raise NativeCandidateStageProjectionError(
                f"Perception visit {visit_index} state binding differs"
            )
        parsed = parse_slurp_intent_hypothesis_state(
            state,
            expected_sample_id=sample_id,
            legal_intent_ids=legal_candidate_ids,
            max_candidates=max_candidates,
            compact_source_phase="perception",
            projection_policy=projection_policy,
        )
        verify_native_perception_state_contact(
            source.bundle,
            sample_id=sample_id,
            source_phase="perception",
            state=state,
            contact=contact,
            allow_prior_history=True,
            execution_contact=final_contact,
        )
    except NativeCandidateStageProjectionError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise NativeCandidateStageProjectionError(
            f"Perception visit {visit_index} candidate state is invalid: {error}"
        ) from error
    candidate_ids = tuple(candidate.intent_id for candidate in parsed.candidates)
    return NativeCandidateStage(
        visit_index=visit_index,
        state_id=state.state_id,
        state_sha256=state.content_hash(),
        query_state_sha256=query_hash,
        agent_contact_id=agent_contact_id,
        request_id=request_id,
        request_sha256=request_sha256,
        response_sha256=response_sha256,
        response_text_sha256=response_text_sha256,
        candidate_ids=candidate_ids,
        candidate_set_sha256=content_hash({"candidate_ids": list(candidate_ids)}),
    )


def project_verified_native_candidate_stages(
    source: object,
    *,
    legal_candidate_ids: frozenset[str],
    max_candidates: int,
    projection_policy: str = BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
) -> tuple[NativeCandidateStagePair, ...]:
    """Return C0/C1 after joining visits, delivery, contacts, states, and traces."""

    if (
        not legal_candidate_ids
        or any(not isinstance(item, str) or not item for item in legal_candidate_ids)
        or isinstance(max_candidates, bool)
        or not isinstance(max_candidates, int)
        or not 1 <= max_candidates <= len(legal_candidate_ids)
        or projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
        or (
            max_candidates > 3
            and projection_policy
            != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        )
    ):
        raise NativeCandidateStageProjectionError(
            "candidate stage projection requires bounded candidates and legal inventory"
        )
    sample_ids = tuple(getattr(source, "sample_ids", ()))
    results = getattr(source, "phase_results", None)
    if (
        not sample_ids
        or len(sample_ids) != len(set(sample_ids))
        or not isinstance(results, Mapping)
        or set(results) != set(sample_ids)
    ):
        raise NativeCandidateStageProjectionError(
            "verified native source has an invalid exact result cohort"
        )
    pairs = []
    for sample_id in sample_ids:
        result = _mapping(results[sample_id], f"phase result {sample_id!r}")
        receipt = _mapping(
            result.get("native_episode_receipt"), f"episode receipt {sample_id!r}"
        )
        visits = _sequence(receipt.get("role_visits"), f"role visits {sample_id!r}")
        delivery = validate_native_episode_delivery_receipt(
            receipt, role_visits=visits, error_type=NativeCandidateStageProjectionError
        )
        delivered_solver_indices = [] if delivery.solver_receipt is None else [
            (index, _mapping(raw_visit, f"role visit {sample_id!r}[{index}]"))
            for index, raw_visit in enumerate(visits)
            if isinstance(raw_visit, Mapping)
            and raw_visit.get("stage") == "solver"
            and raw_visit.get("execution_receipt") == delivery.solver_receipt
        ]
        if delivery.solver_receipt is not None and len(delivered_solver_indices) != 1:
            raise NativeCandidateStageProjectionError(
                f"delivered Solver visit is not unique for {sample_id!r}"
            )
        solver_index = (
            delivered_solver_indices[0][0] if delivered_solver_indices else None
        )
        all_perception_visits = [
            (index, _mapping(raw_visit, f"role visit {sample_id!r}[{index}]"))
            for index, raw_visit in enumerate(visits)
            if isinstance(raw_visit, Mapping) and raw_visit.get("stage") == "perception"
        ]
        if all_perception_visits and all_perception_visits[0][0] != 0:
            raise NativeCandidateStageProjectionError(
                f"C0 must be the first actual role visit for {sample_id!r}"
            )
        later_perception = (
            solver_index is not None
            and any(index > solver_index for index, _ in all_perception_visits)
        )
        if later_perception and delivery.kind != "finite":
            raise NativeCandidateStageProjectionError(
                f"Perception appears after the delivered Solver for {sample_id!r}"
            )
        if solver_index is not None and not any(
            index < solver_index for index, _ in all_perception_visits
        ):
            raise NativeCandidateStageProjectionError(
                f"delivered Solver requires a completed Perception for {sample_id!r}"
            )
        c0 = None
        if all_perception_visits:
            c0_index, c0_visit = all_perception_visits[0]
            c0 = _stage(
                source=source, sample_id=sample_id, result=result,
                visit_index=c0_index, visit=c0_visit,
                legal_candidate_ids=legal_candidate_ids,
                max_candidates=max_candidates, projection_policy=projection_policy,
            )
        c1 = None
        if solver_index is not None:
            prior_perceptions = [
                item for item in all_perception_visits if item[0] < solver_index
            ]
            if prior_perceptions:
                c1_index, c1_visit = prior_perceptions[-1]
                c1 = c0 if c0 is not None and c1_index == c0.visit_index else _stage(
                    source=source, sample_id=sample_id, result=result,
                    visit_index=c1_index, visit=c1_visit,
                    legal_candidate_ids=legal_candidate_ids,
                    max_candidates=max_candidates, projection_policy=projection_policy,
                )
        pairs.append(
            NativeCandidateStagePair(
                sample_id=sample_id,
                c0=c0,
                c1=c1,
                refresh_executed=len(all_perception_visits) > 1,
                refresh_after_delivered_solver=later_perception,
            )
        )
    return tuple(pairs)


__all__ = [
    "PROJECTION_CONFIG_SCHEMA",
    "PROJECTION_POLICY_ID",
    "NativeCandidateStage",
    "NativeCandidateStagePair",
    "NativeCandidateStageProjectionError",
    "project_verified_native_candidate_stages",
]
