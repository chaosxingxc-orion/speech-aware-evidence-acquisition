"""Shared static-arm and speech-native AgentLoop execution.

The historical ``run_rails_experiment`` path remains the protocol-faithful
zero-supply/supplied baseline. ``run_speech_native_agent_loop`` is the
task-independent Stage-2 path: it consumes one frozen TRAIN knowledge
snapshot, binds every DEV trajectory to one pre-materialized speech packet,
runs trajectory-affine contacts concurrently, and delays gold-bearing
scoring until every runtime trajectory has stopped.

This module never builds knowledge and never starts a model process. A real
flight still reaches the frozen core through ``FrozenCoreClient`` and the
receipt-bound resident llama.cpp service; unit tests use in-process clients.
"""

from __future__ import annotations

import hashlib
import json
from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field, replace
from pathlib import Path
from queue import Queue
from typing import Callable, Generic, Hashable, Mapping, Protocol, Sequence, TypeVar

from ..contracts import ExecutionPlan, assert_execution_scope
from ..core.base import AGENT_CONTROLLERS, CoreError, Registry
from ..core.flight_lock import read_flight_lock
from ..core.tracing import TraceBuffer, set_current_trace_buffer
from .consumption import ConsumptionTrace
from .core_client import CoreClient, CoreCompletion, FrozenCoreClient, PreparedCoreRequest
from .errors import RailsError
from .hashing import content_hash
from .knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    KeyFacet,
    KnowledgeSnapshot,
    QueryState,
    RankResult,
    ValueBundle,
    assert_agent_step_binding,
    assert_knowledge_use_binding,
)
from .native_episode_config import NativeEpisodeRunBinding
from .obs import ObsPacket, default_obs_packet
from .solver_citation import (
    CITED_ANSWER_NORMALISER_IDS,
    CITED_ANSWER_RESPONSE_FORMAT_ID,
    SOLVER_CITATIONS_RECEIPT_SCHEMA,
    SolverCitationError,
    bind_cited_completion,
    cited_answer_response_format,
    cited_answer_response_format_for,
)
from .observe import ObserveStep
from .supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .task_adapter import TaskAdapter, TaskSample

ZERO_SUPPLY_ARM = "zero-supply"
SUPPLIED_ARM = "supplied"
RAILS_ARMS: tuple[str, ...] = (ZERO_SUPPLY_ARM, SUPPLIED_ARM)
TASK_ANSWER_RESULT_KIND = "task-answer"
ARTIFACT_RESULT_KIND = "artifact"
RESULT_KINDS = frozenset({TASK_ANSWER_RESULT_KIND, ARTIFACT_RESULT_KIND})

# (sample, obs, stable task contract) -> a SupplyPacket for the supplied arm, or
# None to skip supply for that one sample even though the arm ran (an
# adapter/caller-level choice, e.g. no evidence retrieved above threshold --
# distinct from the arm itself being absent from `arms`).
SupplyBuilder = Callable[[TaskSample, ObsPacket, str], SupplyPacket | None]


RequestBatchGate = Callable[[tuple[PreparedCoreRequest, ...]], None]


class RailsRunnerError(RailsError):
    """The runner refused: a bad plan, an unknown arm, or a missing supply_builder."""


#: Item E43 (2026-09-28, coordinator ruling on
#: ``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``): the
#: ``terminal_disposition.reason`` -- restated verbatim in
#: ``rails.native_episode_receipt`` (which keeps no runtime import of its
#: own, exactly as it restates :data:`.context_fit.CONTEXT_COMPACTION_DISPOSITION`) --
#: a row takes when a structured-output contract's own parser refused an
#: otherwise-authoritative (``finish_reason == "stop"``) completion at
#: capture time. Distinct from every OTHER :class:`RailsRunnerError`: those
#: name a runner-level invariant violation and must abort the flight; a
#: ``RailsRunnerError`` tagged with ``seal_refusal_completion`` (see
#: ``capture_completion`` below) names a parse/contract refusal of the
#: model's OWN well-formed output -- the seal, not the wire, refused it --
#: and ``reproduction.ojw.native_episode`` may dispose of it per row under
#: ``finite_completion_policy == "deliver-latest-or-abstain"`` (item E13),
#: the same programme rule the COMP-1/B7a/B8b-anchor abort class violated.
SEAL_REFUSAL_DISPOSITION = "seal_refusal"


@dataclass(frozen=True)
class ArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    protocol_hash: str
    arms: tuple[str, ...]
    results: tuple[ArmResult, ...]
    # Best-effort, advisory (core.flight_lock's own module docstring): None
    # whenever no flight ever ran under scripts/run_arm_sequence.sh, or the
    # lock file is missing/unreadable/malformed -- never itself a refusal.
    flight_lock: Mapping[str, object] | None


@dataclass(frozen=True)
class AgentContactPlan:
    """One controller-authored, speech-conditioned model contact."""

    contact_id: str
    query_state_sha256: str
    purpose: str
    instruction: str
    key_representation_id: str
    matcher_policy_id: str
    decoding_params: Mapping[str, object]

    def validate(self) -> "AgentContactPlan":
        for field_name in (
            "contact_id",
            "purpose",
            "instruction",
            "key_representation_id",
            "matcher_policy_id",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise RailsRunnerError(
                    f"AgentContactPlan.{field_name} must be a non-empty string"
                )
        if (
            not isinstance(self.query_state_sha256, str)
            or len(self.query_state_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.query_state_sha256
            )
        ):
            raise RailsRunnerError(
                "AgentContactPlan.query_state_sha256 must be lowercase 64-hex"
            )
        if not isinstance(self.decoding_params, Mapping):
            raise RailsRunnerError("AgentContactPlan.decoding_params must be a mapping")
        if "id_slot" in self.decoding_params:
            raise RailsRunnerError(
                "AgentContactPlan cannot choose id_slot; the runner owns slot affinity"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "contact_id": self.contact_id,
            "query_state_sha256": self.query_state_sha256,
            "purpose": self.purpose,
            "instruction": self.instruction,
            "key_representation_id": self.key_representation_id,
            "matcher_policy_id": self.matcher_policy_id,
            "decoding_params": dict(self.decoding_params),
        }


@dataclass(frozen=True)
class AgentContactBatch:
    """One causally independent contact wave over the same QueryState."""

    batch_id: str
    query_state_sha256: str
    contacts: tuple[AgentContactPlan, ...]
    fanout_semantics: str = "evidence_parallel"

    def validate(self) -> "AgentContactBatch":
        if not isinstance(self.batch_id, str) or not self.batch_id.strip():
            raise RailsRunnerError(
                "AgentContactBatch.batch_id must be a non-empty string"
            )
        if not isinstance(self.contacts, tuple) or not self.contacts:
            raise RailsRunnerError(
                "AgentContactBatch.contacts must be a non-empty tuple"
            )
        if self.fanout_semantics not in {
            "evidence_parallel",
            "action_alternatives",
        }:
            raise RailsRunnerError(
                "AgentContactBatch.fanout_semantics must be "
                "'evidence_parallel' or 'action_alternatives'"
            )
        contact_ids: list[str] = []
        for contact in self.contacts:
            if not isinstance(contact, AgentContactPlan):
                raise RailsRunnerError(
                    "AgentContactBatch.contacts entries must be AgentContactPlan"
                )
            contact.validate()
            if contact.query_state_sha256 != self.query_state_sha256:
                raise RailsRunnerError(
                    "AgentContactBatch contacts must bind the batch QueryState"
                )
            contact_ids.append(contact.contact_id)
        if len(set(contact_ids)) != len(contact_ids):
            raise RailsRunnerError(
                "AgentContactBatch contacts must have unique contact ids"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "batch_id": self.batch_id,
            "query_state_sha256": self.query_state_sha256,
            "fanout_semantics": self.fanout_semantics,
            "contacts": [contact.as_json() for contact in self.contacts],
        }


AgentContact = AgentContactPlan | AgentContactBatch
AgentResponse = str | tuple[str, ...]


@dataclass(frozen=True)
class AgentLoopAdvance:
    """The external controller's exact state/evidence delta after a contact."""

    transition: AgentStepTransition
    next_query_state: QueryState | None
    new_agent_states: tuple[AgentStateArtifact, ...]
    next_contact: AgentContact | None
    final_response_contact_id: str | None = None
    rank_result: RankResult | None = None
    fusion_decision: FusionDecision | None = None


@dataclass(frozen=True)
class AgentRuntimeContext:
    """Gold-free controller view; deliberately carries no task sample object."""

    sample_id: str
    knowledge_snapshot_sha256: str
    catalog_facet_ids: tuple[str, ...]
    catalog_value_ids: tuple[str, ...]
    query_state: QueryState
    task_contract: str
    agent_states: tuple[AgentStateArtifact, ...]
    prior_response_sha256s: tuple[str, ...]
    contact_index: int
    core_completions: tuple[CoreCompletion, ...] = ()
    execution_unit_id: str | None = None
    execution_unit_binding: Mapping[str, object] | None = None


class AgentController(Protocol):
    def initial_contact(self, context: AgentRuntimeContext) -> AgentContact: ...

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContact,
        response_text: AgentResponse,
    ) -> AgentLoopAdvance: ...


AgentControllerFactory = Callable[[str], AgentController]


def agent_response_sha256(
    contact: AgentContact,
    response: AgentResponse,
) -> str:
    """Bind controller artifacts to one response or one ordered batch."""

    if isinstance(contact, AgentContactPlan):
        contact.validate()
        if not isinstance(response, str):
            raise RailsRunnerError(
                "a single AgentContactPlan requires one string response"
            )
        return hashlib.sha256(response.encode("utf-8")).hexdigest()
    if isinstance(contact, AgentContactBatch):
        contact.validate()
        if (
            not isinstance(response, tuple)
            or len(response) != len(contact.contacts)
            or any(not isinstance(item, str) for item in response)
        ):
            raise RailsRunnerError(
                "an AgentContactBatch requires one ordered string response per contact"
            )
        return content_hash(
            {
                "schema_version": "AgentResponseEnvelopeV1",
                "contact_batch": contact.as_json(),
                "ordered_responses": [
                    {
                        "contact_id": plan.contact_id,
                        "response_sha256": hashlib.sha256(
                            response_text.encode("utf-8")
                        ).hexdigest(),
                    }
                    for plan, response_text in zip(
                        contact.contacts, response, strict=True
                    )
                ],
            }
        )
    raise RailsRunnerError(
        "Agent controller contact must be AgentContactPlan or AgentContactBatch"
    )


def _resolve_final_agent_response(
    contact: AgentContact,
    response: AgentResponse,
    final_response_contact_id: str | None,
    *,
    allow_empty: bool = False,
    empty_receipted: Callable[[str], bool] | None = None,
) -> str:
    """Keep final-answer authority inside an actual frozen-core response.

    ``empty_receipted`` names the contacts whose empty completion carries a ``saea-empty-completion-v1`` receipt: an empty final response
    is legal only for those (owner decision 199), never for an unreceipted one.
    """

    if isinstance(contact, AgentContactPlan):
        if not isinstance(response, str):
            raise RailsRunnerError(
                "a single AgentContactPlan requires one string response"
            )
        if final_response_contact_id not in {None, contact.contact_id}:
            raise RailsRunnerError(
                "final_response_contact_id must select the stopped contact"
            )
        if not response and not allow_empty and not (
            empty_receipted is not None and empty_receipted(contact.contact_id)
        ):
            raise RailsRunnerError("stop must select a non-empty model response")
        return response
    if isinstance(contact, AgentContactBatch):
        if not isinstance(response, tuple) or len(response) != len(contact.contacts):
            raise RailsRunnerError(
                "a stopped AgentContactBatch requires its ordered responses"
            )
        if (
            not isinstance(final_response_contact_id, str)
            or not final_response_contact_id
        ):
            raise RailsRunnerError(
                "a stopped AgentContactBatch requires final_response_contact_id"
            )
        for plan, response_text in zip(contact.contacts, response, strict=True):
            if plan.contact_id == final_response_contact_id:
                if not response_text and not allow_empty and not (
                    empty_receipted is not None and empty_receipted(plan.contact_id)
                ):
                    raise RailsRunnerError(
                        "stop must select a non-empty model response"
                    )
                return response_text
        raise RailsRunnerError(
            "final_response_contact_id must select a contact in the stopped batch"
        )
    raise RailsRunnerError(
        "Agent controller contact must be AgentContactPlan or AgentContactBatch"
    )


def perception_note_view_state(state, *, note_text: str):
    """LEVEL 2: the render-only view of a sealed Perception state that carries a
    non-A branch's OWN note.

    A's sealed state binds ``source_response_sha256`` to the sha256 of its own
    response text (``seal_phase_response_state``), and every consumer that
    parses the state (``parse_slurp_intent_hypothesis_state``) re-checks
    ``sha256(content) == source_response_sha256``. A view that swapped only
    ``content`` therefore no longer satisfied its own binding, so the branch is
    bound to its own note bytes exactly as A is bound to A's. Every other field
    (state id, kind, ``source_query_state_sha256``, producer, citations) is
    unchanged; the view is never registered as custody.
    """

    return replace(
        state, content=note_text,
        source_response_sha256=hashlib.sha256(note_text.encode("utf-8")).hexdigest(),
    )


def _protected_knowledge_material(snapshot: KnowledgeSnapshot) -> tuple[str, ...]:
    """Build the casefolded facet/value payload tuple once per run.

    ``_assert_agent_control_excludes_knowledge_payloads`` used to rebuild
    this tuple (every facet representation + value content, casefolded) on
    every contact wave -- O(waves x snapshot bytes) at train scale, even
    though the frozen ``snapshot`` never changes within a run. Callers
    compute this once (``run_speech_native_agent_loop``, after snapshot
    validation) and pass the result down explicitly.
    """

    return tuple(
        material.strip().casefold()
        for material in (
            *(facet.representation for facet in snapshot.facets),
            *(value.content for value in snapshot.values),
        )
        if len(material.strip()) >= 8
    )


#: Item E4 (2026-09-28): a process-lifetime cache of the two committed
#: relisten templates, keyed by (resolved repo root, template id) exactly as
#: ``rails.node_context_policy._TEMPLATE_CACHE`` caches its own committed
#: templates. ``rails.relisten.RelistenConfig`` already refuses any
#: ``blind_template_id`` / ``confirm_template_id`` other than the two v1
#: constants before this ever runs, so a config never selects an arbitrary
#: path -- the git-committed file bytes are the only pin v1 needs.
_RELISTEN_TEMPLATE_CACHE: dict[tuple[str, str], str] = {}


def _load_relisten_template(repo_root: object, template_id: str) -> str:
    """Read one committed ``configs/probes/<template_id>.txt`` file.

    Plain UTF-8 text with ``.format()`` placeholders (section 1's templates
    are one paragraph each, not the sectioned ``# node-context-template-v1``
    shape ``rails.node_context_policy.load_node_context_template`` parses),
    so this loader is deliberately simpler than that one.
    """

    key = (str(Path(repo_root).resolve()), template_id)
    cached = _RELISTEN_TEMPLATE_CACHE.get(key)
    if cached is not None:
        return cached
    path = Path(repo_root).resolve() / "configs" / "probes" / f"{template_id}.txt"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RailsRunnerError(
            f"cannot read relisten template {path}: {error}"
        ) from error
    _RELISTEN_TEMPLATE_CACHE[key] = text
    return text


def node_context_cleaning_messages(
    base_messages: Sequence[Mapping[str, object]],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    """E8b: the messages ONE context-cleaning contact is composed from.

    ``knowledge: "none"`` is what the cleaning contact's declared phase says, so
    this is where it is made true: the system contract stays, the speech part
    this harness attaches to every contact stays, and every knowledge key/value
    block the supply path put on the consumer's user turn is dropped. A
    cleaning contact restates text it was handed; it is not an evidence
    consumer, and the material it restates rides its instruction.

    Fail-closed: an evidence part that survives the filter, or a user turn that
    is not the shared speech content list, refuses the contact rather than
    sending a request whose knowledge exposure is not what its phase declares.
    """

    if len(base_messages) != 2:
        raise RailsRunnerError("node context cleaning requires the shared two messages")
    user = dict(base_messages[1])
    content = user.get("content")
    if not isinstance(content, list) or not content:
        raise RailsRunnerError("node context cleaning requires the shared speech turn")
    kept = [
        part for part in content
        if not (isinstance(part, Mapping) and isinstance(part.get("evidence_id"), str))
    ]
    if not kept or any(
        isinstance(part, Mapping) and "evidence_id" in part for part in kept
    ):
        raise RailsRunnerError("node context cleaning request carries evidence")
    user["content"] = kept
    return (dict(base_messages[0]), user)


def _assert_agent_control_excludes_knowledge_payloads(
    contact: AgentContact,
    protected_material: tuple[str, ...],
) -> None:
    """Prevent CONTROL text from bypassing traced key/value supply."""

    plans = (contact,) if isinstance(contact, AgentContactPlan) else contact.contacts
    for plan in plans:
        instruction = plan.instruction.casefold()
        if any(material in instruction for material in protected_material):
            raise RailsRunnerError(
                "Agent contact instruction cannot embed frozen knowledge key/value "
                "payloads; acquire them through traced knowledge supply"
            )


def _agent_wave_record(
    *,
    wave_index: int,
    contact: AgentContact,
    response: AgentResponse,
    slot_ids: tuple[int, ...],
    query_state: QueryState,
    advance: AgentLoopAdvance,
) -> AgentWaveRecord:
    plans = (contact,) if isinstance(contact, AgentContactPlan) else contact.contacts
    response_texts = (response,) if isinstance(response, str) else response
    if len(plans) != len(response_texts) or len(plans) != len(slot_ids):
        raise RailsRunnerError("Agent wave provenance cardinality mismatch")
    return AgentWaveRecord(
        wave_index=wave_index,
        batch_id=(
            contact.contact_id
            if isinstance(contact, AgentContactPlan)
            else contact.batch_id
        ),
        fanout_semantics=(
            "single"
            if isinstance(contact, AgentContactPlan)
            else contact.fanout_semantics
        ),
        query_state_sha256=query_state.content_hash(),
        speech_packet_sha256=query_state.speech_packet_sha256,
        contact_plans=plans,
        slot_ids=slot_ids,
        response_sha256s=tuple(
            hashlib.sha256(text.encode("utf-8")).hexdigest() for text in response_texts
        ),
        response_envelope_sha256=agent_response_sha256(contact, response),
        transition=advance.transition,
        rank_result=advance.rank_result,
        fusion_decision=advance.fusion_decision,
        selected_final_contact_id=advance.final_response_contact_id,
        next_query_state_sha256=(
            None
            if advance.next_query_state is None
            else advance.next_query_state.content_hash()
        ),
        termination_reason=(
            "controller-stop" if advance.transition.action_kind == "stop" else None
        ),
    )


def _rebind_contact(contact: AgentContact, query_state_sha256: str) -> AgentContact:
    """The controller's own contact, re-bound to an observed QueryState.

    Only ``query_state_sha256`` moves: the contact id, purpose, instruction,
    key representation, matcher policy and decoding params stay exactly what
    the controller authored. The Observer changes WHAT the next contact
    listens to, never WHAT it is asked.
    """

    if isinstance(contact, AgentContactPlan):
        return replace(contact, query_state_sha256=query_state_sha256).validate()
    return replace(
        contact,
        query_state_sha256=query_state_sha256,
        contacts=tuple(
            replace(plan, query_state_sha256=query_state_sha256)
            for plan in contact.contacts
        ),
    ).validate()


def _observe_relisten(
    *,
    observe_step: ObserveStep,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    sample_id: str,
    record_base: str,
    origin_packet: tuple[str, str],
    wave_index: int,
    relisten_index: int,
    query_state: QueryState,
    sink: AgentTraceSink,
) -> tuple[QueryState, AgentStepTransition] | None:
    """One optional Observer step between the wave that just settled and the
    wave about to be prepared.

    Returns ``None`` -- and touches nothing -- when the Reviewer flagged
    nothing for this (sample, wave) or every flag has already been
    re-listened to, which is why an absent ``observe_step`` and a silent
    Reviewer produce the identical graph. Otherwise it cuts the flagged span
    with its context margin through ``rails.observe`` (the replay loop's own
    re-cut and slice registry), records the move as a ``relisten``
    ``AgentStepTransition`` carrying the derivation, proves it through
    ``assert_agent_step_binding`` against the trajectory's ORIGINAL packet,
    and emits the OBS trace record. The caller re-binds the controller's next
    contact to the successor state and dispatches it.

    The step spends no model contact, so it is bounded by the Observer's own
    ``max_relistens_per_sample`` rather than by ``max_contacts``.
    """

    observation = observe_step.observe(
        sample_id=sample_id,
        wave_index=wave_index,
        origin_packet=origin_packet,
        relisten_index=relisten_index,
    )
    if observation is None:
        return None
    derivation = observation.derivation
    next_query_state = QueryState(
        query_id=f"{query_state.query_id}:relisten{relisten_index:04d}",
        query_sample_id=query_state.query_sample_id,
        speech_packet_id=derivation.derived_packet_id,
        speech_packet_sha256=derivation.derived_packet_sha256,
        use_split_identity_hash=query_state.use_split_identity_hash,
        loop_step=query_state.loop_step + 1,
        visible_facet_ids=query_state.visible_facet_ids,
        agent_state_ids=query_state.agent_state_ids,
        retrieved_value_ids=query_state.retrieved_value_ids,
        use_partition_role=query_state.use_partition_role,
        query_source=query_state.query_source,
    ).validate()
    transition = AgentStepTransition(
        snapshot_sha256=snapshot_sha256,
        prior_query_state_sha256=query_state.content_hash(),
        next_query_state_sha256=next_query_state.content_hash(),
        action_kind="relisten",
        action_target_refs=(derivation.derived_packet_id,),
        new_value_ids=(),
        used_value_ids=(),
        dropped_value_ids=(),
        new_agent_state_ids=(),
        dropped_agent_state_ids=(),
        speech_packet_derivation=derivation,
    ).validate()
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=query_state,
        next_query_state=next_query_state,
        transition=transition,
        snapshot_sha256=snapshot_sha256,
        origin_speech_packet=origin_packet,
    )
    sink.emit(
        "OBS",
        f"{record_base}/relisten{relisten_index:04d}",
        {
            "obs_wave_index": wave_index,
            "obs_prior_query_state_sha256": transition.prior_query_state_sha256,
            "obs_next_query_state_sha256": transition.next_query_state_sha256,
            **observation.trace_payload(),
        },
    )
    return next_query_state, transition


def _validate_agent_knowledge_decision(
    *,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    query_state: QueryState,
    advance: AgentLoopAdvance,
) -> None:
    supply_action = advance.transition.action_kind in {
        "acquire",
        "expand",
        "contrast",
    }
    if not supply_action:
        if advance.rank_result is not None or advance.fusion_decision is not None:
            raise RailsRunnerError(
                "only acquire, expand, or contrast may carry a retrieval decision"
            )
        return
    if advance.rank_result is None or advance.fusion_decision is None:
        raise RailsRunnerError(
            "knowledge acquisition requires RankResult and FusionDecision"
        )
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=query_state,
        rank_result=advance.rank_result,
        fusion_decision=advance.fusion_decision,
        snapshot_sha256=snapshot_sha256,
    )
    if advance.fusion_decision.selected_value_ids != advance.transition.new_value_ids:
        raise RailsRunnerError(
            "FusionDecision selected values must exactly match transition.new_value_ids"
        )
    newly_supporting_facets = tuple(
        facet_id
        for facet_id in advance.fusion_decision.supporting_facet_ids
        if facet_id not in query_state.visible_facet_ids
    )
    if not set(advance.transition.new_facet_ids).issubset(newly_supporting_facets):
        raise RailsRunnerError(
            "transition.new_facet_ids must be newly supporting FusionDecision facets"
        )
    if (
        not advance.fusion_decision.selected_value_ids
        and newly_supporting_facets != advance.transition.new_facet_ids
    ):
        raise RailsRunnerError(
            "facet-only acquisition must expose every newly supporting facet"
        )


class AgentTraceSink(Protocol):
    """Existing append-only trace seam used by AgentLoop runtime records."""

    @property
    def run_id(self) -> str: ...

    def emit(
        self, channel: str, record_id: str, payload: Mapping[str, object]
    ) -> str: ...


_ContactNodeT = TypeVar("_ContactNodeT")
_ContactResponseT = TypeVar("_ContactResponseT")


@dataclass(frozen=True)
class ContactDAGAdvance(Generic[_ContactNodeT]):
    """Newly ready nodes after one contact settles.

    ``ready_front`` is for evidence unlocked by the completed contact and is
    scheduled before older root backlog. ``ready_back`` is ordinary work that
    does not have that causal priority.
    """

    ready_front: tuple[_ContactNodeT, ...] = ()
    ready_back: tuple[_ContactNodeT, ...] = ()


@dataclass(frozen=True)
class ContactDAGCompletion(Generic[_ContactNodeT, _ContactResponseT]):
    node: _ContactNodeT
    response: _ContactResponseT


def run_bounded_contact_dag(
    *,
    initial_nodes: Sequence[_ContactNodeT],
    max_in_flight: int,
    queue_depth: int,
    node_key: Callable[[_ContactNodeT], Hashable],
    sort_key: Callable[[_ContactNodeT], tuple[object, ...]],
    is_runnable: Callable[[_ContactNodeT], bool],
    submit: Callable[[_ContactNodeT], Future[_ContactResponseT]],
    on_result: Callable[
        [_ContactNodeT, _ContactResponseT], ContactDAGAdvance[_ContactNodeT]
    ],
    on_error: Callable[[_ContactNodeT, BaseException], None],
) -> tuple[ContactDAGCompletion[_ContactNodeT, _ContactResponseT], ...]:
    """Run one bounded dynamic contact DAG without retries.

    The caller owns the executor and the domain state machine. This shared
    scheduler owns only readiness, causal front-priority, in-flight bounds,
    deterministic same-wave completion order, and one-shot node identity.
    That boundary lets existing task-specific policies retain their parsing
    semantics while reusing one concurrency implementation.
    """

    max_in_flight = _positive_int(max_in_flight, field="max_in_flight")
    queue_depth = _positive_int(queue_depth, field="queue_depth")
    if queue_depth < max_in_flight:
        raise RailsRunnerError("queue_depth must be at least max_in_flight")
    ready = deque(initial_nodes)
    pending: dict[Future[_ContactResponseT], _ContactNodeT] = {}
    scheduled: set[Hashable] = set()
    completions: list[ContactDAGCompletion[_ContactNodeT, _ContactResponseT]] = []

    while ready or pending:
        while ready and len(pending) < max_in_flight:
            node = ready.popleft()
            if not is_runnable(node):
                continue
            key = node_key(node)
            try:
                hash(key)
            except TypeError as error:
                raise RailsRunnerError(
                    "contact DAG node_key must return a hashable identity"
                ) from error
            if key in scheduled:
                raise RailsRunnerError(f"duplicate contact DAG node {key!r}")
            scheduled.add(key)
            try:
                future = submit(node)
            except BaseException as error:
                on_error(node, error)
                continue
            if not isinstance(future, Future):
                raise RailsRunnerError("contact DAG submit must return a Future")
            pending[future] = node

        if not pending:
            continue
        done, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
        for future in sorted(done, key=lambda item: sort_key(pending[item])):
            node = pending.pop(future)
            try:
                response = future.result()
            except BaseException as error:
                on_error(node, error)
                continue
            if not is_runnable(node):
                continue
            completions.append(ContactDAGCompletion(node=node, response=response))
            advance = on_result(node, response)
            if not isinstance(advance, ContactDAGAdvance):
                raise RailsRunnerError(
                    "contact DAG on_result must return ContactDAGAdvance"
                )
            if not isinstance(advance.ready_front, tuple) or not isinstance(
                advance.ready_back, tuple
            ):
                raise RailsRunnerError(
                    "ContactDAGAdvance ready collections must be tuples"
                )
            for child in reversed(advance.ready_front):
                ready.appendleft(child)
            ready.extend(advance.ready_back)

    return tuple(completions)


@dataclass(frozen=True)
class AgentContactRecord:
    plan: AgentContactPlan
    query_state_sha256: str
    speech_packet_sha256: str
    slot_id: int
    response_sha256: str

    def as_json(self) -> dict[str, object]:
        return {
            "plan": self.plan.as_json(),
            "query_state_sha256": self.query_state_sha256,
            "speech_packet_sha256": self.speech_packet_sha256,
            "slot_id": self.slot_id,
            "response_sha256": self.response_sha256,
        }


@dataclass(frozen=True)
class AgentWaveRecord:
    """Reconstructible fan-out/fan-in provenance for one Agent loop wave."""

    wave_index: int
    batch_id: str
    fanout_semantics: str
    query_state_sha256: str
    speech_packet_sha256: str
    contact_plans: tuple[AgentContactPlan, ...]
    slot_ids: tuple[int, ...]
    response_sha256s: tuple[str, ...]
    response_envelope_sha256: str
    transition: AgentStepTransition
    rank_result: RankResult | None
    fusion_decision: FusionDecision | None
    selected_final_contact_id: str | None
    next_query_state_sha256: str | None
    termination_reason: str | None

    def as_json(self) -> dict[str, object]:
        return {
            "wave_index": self.wave_index,
            "batch_id": self.batch_id,
            "fanout_semantics": self.fanout_semantics,
            "query_state_sha256": self.query_state_sha256,
            "speech_packet_sha256": self.speech_packet_sha256,
            "contact_plans": [plan.as_json() for plan in self.contact_plans],
            "slot_ids": list(self.slot_ids),
            "response_sha256s": list(self.response_sha256s),
            "response_envelope_sha256": self.response_envelope_sha256,
            "transition": self.transition.as_json(),
            "rank_result": (
                None if self.rank_result is None else self.rank_result.as_json()
            ),
            "fusion_decision": (
                None if self.fusion_decision is None else self.fusion_decision.as_json()
            ),
            "selected_final_contact_id": self.selected_final_contact_id,
            "next_query_state_sha256": self.next_query_state_sha256,
            "termination_reason": self.termination_reason,
        }


@dataclass(frozen=True)
class AgentLoopResult:
    sample_id: str
    initial_query_state: QueryState
    final_query_state: QueryState
    final_response_text: str
    contacts: tuple[AgentContactRecord, ...]
    waves: tuple[AgentWaveRecord, ...]
    transitions: tuple[AgentStepTransition, ...]
    agent_states: tuple[AgentStateArtifact, ...]
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace | None
    result_kind: str = TASK_ANSWER_RESULT_KIND
    native_episode_receipt: Mapping[str, object] | None = None
    execution_unit_id: str | None = None
    execution_unit_binding: Mapping[str, object] | None = None
    # E2b (SLURP v2 base program M2 live wiring): a top-level sibling of
    # native_episode_receipt, present exactly when this row's Solver visit
    # was grouped (samples >= 2). See _AgentRuntimeOutcome.solver_group.
    solver_group: Mapping[str, object] | None = None
    # Item E42 (2026-09-25, family VAR-2): the same kind of top-level sibling,
    # present exactly when this row's Solver visit was ARM-grouped. Declared
    # LAST and defaulted, so every construction written before E42 composes
    # exactly the result it always did.
    supply_variants: Mapping[str, object] | None = None
    # Item E4 (2026-09-28, owner decision 185): the same kind of top-level
    # sibling, present exactly when ``native_episode.relisten`` is armed and
    # the row was not an abstention -- the row's own ``saea-relisten-v1``
    # receipt (``rails.relisten.seal_relisten_receipt``). The delivered
    # ``final_response_text``/``text`` is NEVER mutated by this stage
    # (shadow delivery); the two shadow columns are rendered OFFLINE from
    # this receipt plus the sealed trace
    # (``scripts/analysis/stage3_rollout_score.py``'s
    # ``render_relisten_shadow_columns``). Declared LAST and defaulted, so
    # every construction written before E4 composes exactly the result it
    # always did.
    relisten: Mapping[str, object] | None = None

    def as_json(self) -> dict[str, object]:
        result = {
            "sample_id": self.sample_id,
            "initial_query_state": self.initial_query_state.as_json(),
            "final_query_state": self.final_query_state.as_json(),
            "final_response_text": self.final_response_text,
            "final_response_sha256": hashlib.sha256(
                self.final_response_text.encode("utf-8")
            ).hexdigest(),
            "contacts": [contact.as_json() for contact in self.contacts],
            "waves": [wave.as_json() for wave in self.waves],
            "transitions": [transition.as_json() for transition in self.transitions],
            "agent_states": [artifact.as_json() for artifact in self.agent_states],
            "metrics": dict(self.metrics),
            "consumption": (
                None if self.consumption is None else self.consumption.as_json()
            ),
        }
        if self.native_episode_receipt is not None:
            result["native_episode_receipt"] = dict(self.native_episode_receipt)
        if self.solver_group is not None:
            result["solver_group"] = dict(self.solver_group)
        if self.supply_variants is not None:
            result["supply_variants"] = dict(self.supply_variants)
        if self.relisten is not None:
            result["relisten"] = dict(self.relisten)
        if self.result_kind != TASK_ANSWER_RESULT_KIND:
            result["result_kind"] = self.result_kind
        if self.execution_unit_id is not None:
            result["execution_unit_id"] = self.execution_unit_id
            result["execution_unit_binding"] = dict(self.execution_unit_binding or {})
        return result


@dataclass(frozen=True)
class AgentLoopSummary:
    run_id: str
    protocol_hash: str
    controller_policy_id: str
    agent_executor_id: str
    agent_executor_version: str
    knowledge_snapshot_sha256: str
    results: tuple[AgentLoopResult, ...]
    flight_lock: Mapping[str, object] | None
    result_kind: str = TASK_ANSWER_RESULT_KIND

    def as_json(self) -> dict[str, object]:
        result = {
            "run_id": self.run_id,
            "protocol_hash": self.protocol_hash,
            "controller_policy_id": self.controller_policy_id,
            "agent_executor_id": self.agent_executor_id,
            "agent_executor_version": self.agent_executor_version,
            "knowledge_snapshot_sha256": self.knowledge_snapshot_sha256,
            "results": [result.as_json() for result in self.results],
            "flight_lock": (
                dict(self.flight_lock) if self.flight_lock is not None else None
            ),
        }
        if self.result_kind != TASK_ANSWER_RESULT_KIND:
            result["result_kind"] = self.result_kind
        return result


@dataclass(frozen=True)
class _PreparedAgentTask:
    index: int
    sample: TaskSample
    task_contract: str
    initial_query_state: QueryState
    initial_feedback_states: tuple = ()
    execution_unit_id: str | None = None
    execution_unit_binding: Mapping[str, object] | None = None


@dataclass(frozen=True)
class _AgentRuntimeOutcome:
    prepared: _PreparedAgentTask
    final_query_state: QueryState
    final_response_text: str
    contacts: tuple[AgentContactRecord, ...]
    waves: tuple[AgentWaveRecord, ...]
    transitions: tuple[AgentStepTransition, ...]
    agent_states: tuple[AgentStateArtifact, ...]
    final_supply: SupplyPacket | None
    trace_buffer: TraceBuffer
    native_episode_receipt: Mapping[str, object] | None = None
    # E2b (SLURP v2 base program M2 live wiring): every raw sample custody
    # plus commit provenance for a grouped Solver visit's delivered answer
    # (reproduction.ojw.native_group_solver.run_grouped_solver_samples's
    # solver_group), or None for a samples-1 (or non-native) outcome --
    # byte-identical to before this field existed.
    solver_group: Mapping[str, object] | None = None
    # Item E42 (2026-09-25, family VAR-2): every arm's declared knobs, supplied
    # value ids and item count for an arm-grouped Solver visit
    # (reproduction.ojw.native_supply_variants.run_supply_variant_arms's
    # supply_variants), or None for every other outcome -- byte-identical to
    # before this field existed.
    supply_variants: Mapping[str, object] | None = None
    # Item E4 (2026-09-28, owner decision 185): the row's own sealed
    # post-accept relisten receipt (``rails.relisten.seal_relisten_receipt``),
    # or None for every outcome without an armed ``native_episode.relisten``
    # -- byte-identical to before this field existed. See
    # ``AgentLoopResult.relisten``.
    relisten: Mapping[str, object] | None = None


@dataclass
class _ContactAgentState:
    prepared: _PreparedAgentTask
    controller: AgentController | None
    query_state: QueryState
    state_store: dict[str, AgentStateArtifact] = field(default_factory=dict)
    response_sha256s: list[str] = field(default_factory=list)
    contacts: list[AgentContactRecord] = field(default_factory=list)
    waves: list[AgentWaveRecord] = field(default_factory=list)
    transitions: list[AgentStepTransition] = field(default_factory=list)
    trace_buffers: dict[tuple[int, int], TraceBuffer] = field(default_factory=dict)
    trace_spool: object = None
    seen_contact_ids: set[str] = field(default_factory=set)
    wave_index: int = 0
    scheduled_contacts: int = 0
    # Observer steps taken for this sample so far (rails.observe): bounded by
    # the Observer's own budget, never by max_contacts -- a re-listen spends
    # no model contact.
    relisten_count: int = 0
    current_contact: AgentContact | None = None
    current_context: AgentRuntimeContext | None = None
    current_nodes: tuple[_AgentContactNode, ...] = ()
    final_outcome: _AgentRuntimeOutcome | None = None


@dataclass(frozen=True)
class _AgentContactNode:
    task_index: int
    wave_index: int
    branch_index: int
    contact: AgentContactPlan
    messages: tuple[Mapping[str, object], ...]
    context: AgentRuntimeContext
    trace_buffer: TraceBuffer

    @property
    def node_key(self) -> tuple[int, int, int, str]:
        return (
            self.task_index,
            self.wave_index,
            self.branch_index,
            self.contact.contact_id,
        )

    @property
    def sort_key(self) -> tuple[int, int, int]:
        return self.task_index, self.wave_index, self.branch_index


def _run_one_arm(
    *,
    arm: str,
    adapter: TaskAdapter,
    core_client: CoreClient,
    sample: TaskSample,
    supply: SupplyPacket | None,
    decoding_params: Mapping[str, object] | None,
) -> ArmResult:
    messages = adapter.assemble_prompt(sample, supply)
    response_text = core_client.complete(messages, decoding_params=decoding_params)
    metrics = adapter.score(sample, response_text)
    consumption = adapter.extract_consumption(sample, supply, response_text)
    return ArmResult(
        arm=arm,
        sample_id=sample.sample_id,
        messages=tuple(messages),
        response_text=response_text,
        metrics=metrics,
        consumption=consumption,
    )


def run_rails_experiment(
    *,
    data_root: Path,
    plan: ExecutionPlan,
    adapter: TaskAdapter,
    core_client: CoreClient,
    split_id: str,
    supply_builder: SupplyBuilder | None = None,
    arms: Sequence[str] = RAILS_ARMS,
    decoding_params: Mapping[str, object]
    | Callable[[TaskSample], Mapping[str, object] | None]
    | None = None,
) -> RunSummary:
    """Execute ``arms`` (default: zero-supply then supplied) for every
    sample ``adapter.load_split(split_id)`` returns, through
    ``core_client`` -- enforcing, before any sample runs:

    1. ``plan.validate()`` (raises ``contracts.ExecutionScopeError`` on a
       malformed plan -- this itself calls ``assert_execution_scope``
       internally).
    2. ``contracts.assert_execution_scope(plan.execution_profile)`` again,
       explicitly, so the enforcement point is named directly in this
       function's own body rather than only transitively via step 1.
    3. The advisory flight lock (``core.flight_lock.read_flight_lock`` --
       best-effort, never fail-closed by design; see that module's own
       docstring) is read and threaded into the returned summary for
       provenance, exactly as advisory as the module that produces it.

    ``SUPPLIED_ARM`` requires ``supply_builder``; requesting it without one
    is refused before any sample runs (fail closed, not a silent skip). For
    every sample, ``ObsPacket``/task contract are resolved ONCE
    (``rails.obs.default_obs_packet`` + ``adapter.build_task_contract``) and reused
    across every arm for that sample -- they do not depend on which arm is
    running, only on the sample itself.

    ``decoding_params`` is normally ONE mapping every request of the run
    carries. It may instead be a CALLABLE taking the sample and returning that
    sample's mapping -- the serial counterpart of what
    ``core.flight.FlightRuntime._dispatch_concurrent`` already does per request,
    and the seam a per-sample ``max_tokens`` rule travels
    (``core.flight.runtime.MAX_TOKENS_POLICY_KEY``). A mapping is passed
    through by identity, so a caller that hands one dispatches exactly as
    before this seam existed.
    """

    plan.validate()
    assert_execution_scope(plan.execution_profile)
    for arm in arms:
        if arm not in RAILS_ARMS:
            raise RailsRunnerError(
                f"unknown rails arm {arm!r}; known arms are {RAILS_ARMS}"
            )
    if SUPPLIED_ARM in arms and supply_builder is None:
        raise RailsRunnerError(
            f"arm {SUPPLIED_ARM!r} requires a supply_builder; none was given"
        )

    flight_lock = read_flight_lock(Path(data_root))
    samples = adapter.load_split(split_id)
    if not samples:
        raise RailsRunnerError(f"split {split_id!r} resolved to zero samples")

    results: list[ArmResult] = []
    for sample in samples:
        obs = default_obs_packet(sample)
        task_contract = adapter.build_task_contract(sample, obs)
        for arm in arms:
            supply = (
                supply_builder(sample, obs, task_contract)
                if arm == SUPPLIED_ARM
                else None
            )
            if supply is not None:
                supply.validate()
            results.append(
                _run_one_arm(
                    arm=arm,
                    adapter=adapter,
                    core_client=core_client,
                    sample=sample,
                    supply=supply,
                    decoding_params=(
                        decoding_params(sample)
                        if callable(decoding_params)
                        else decoding_params
                    ),
                )
            )

    return RunSummary(
        run_id=plan.run_id,
        protocol_hash=plan.protocol_hash,
        arms=tuple(arms),
        results=tuple(results),
        flight_lock=flight_lock,
    )


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RailsRunnerError(f"{field} must be a positive integer")
    return value


def _initial_query_state(
    *,
    plan: ExecutionPlan,
    sample: TaskSample,
    descriptor: Mapping[str, object],
    bootstrap_facet_ids: tuple[str, ...],
    bootstrap_value_ids: tuple[str, ...],
    query_source: str = "speech_features",
    execution_unit_id: str | None = None,
) -> QueryState:
    if not isinstance(descriptor, Mapping) or set(descriptor) != {
        "packet_id",
        "sha256",
    }:
        raise RailsRunnerError(
            f"speech packet binding for {sample.sample_id!r} must carry exact "
            "packet_id/sha256 keys"
        )
    return QueryState(
        query_id=f"{plan.run_id}:{execution_unit_id or sample.sample_id}:step0",
        query_sample_id=sample.sample_id,
        speech_packet_id=descriptor["packet_id"],
        speech_packet_sha256=descriptor["sha256"],
        use_split_identity_hash=plan.split_identity_hash,
        visible_facet_ids=bootstrap_facet_ids,
        retrieved_value_ids=bootstrap_value_ids,
        query_source=query_source,
    ).validate()


def _per_sample_bootstrap(
    values: object,
    sample_ids: Sequence[str],
    *,
    field: str,
) -> Mapping[str, Sequence[str]] | None:
    """``None`` for the flat, run-wide form; a per-sample mapping otherwise.

    E6: a supplied FIRST phase has no preceding ``advance`` to carry an
    ``acquire`` transition, so its (per-sample) selection is seeded into the
    initial ``QueryState`` instead -- ``rails.runner._agent_messages`` then
    renders it as the same typed content blocks with the same
    ``evidence_id``/``source_uri``/``knowledge_role``, and the SUPPLY trace
    record reports it per sample as ``supply_bootstrap_*_ids``. The run-wide
    sequence form is unchanged and remains the default.
    """

    if values is None or isinstance(values, (str, bytes)) or not isinstance(
        values, Mapping
    ):
        return None
    unknown = sorted(set(values) - set(sample_ids))
    if unknown:
        raise RailsRunnerError(
            f"{field} names sample(s) outside this split: {unknown[:5]}"
        )
    return values


def _restricted_split_samples(
    samples: tuple[object, ...],
    flown_sample_ids: object,
    *,
    split_id: str,
    execution_units: object,
) -> tuple[object, ...]:
    """The split restricted to an explicitly named subset, in split order.

    E10c (2026-09-18). A resume-recovery flies only the rows its predecessor
    did not finish (``core.flight.resume``), but the roster every runner entry
    point derives is ``adapter.load_split(split_id)`` -- the WHOLE split. The
    flight narrows the packet map instead, so the two disagreed and the loop
    refused with "speech_packet_bindings must materialize every query sample
    exactly once" after preflight, preprocess and serve had been paid for.

    The restriction is explicit and declarative: the caller names the rows,
    this function refuses any name the split does not carry, and the order is
    the SPLIT's own -- never the caller's -- so a recovery dispatches exactly
    the bytes an uninterrupted flight would have dispatched for those rows.
    It is not a selection mechanism: nothing here can widen a roster, and the
    only caller that supplies it is ``core.flight.runtime`` under a scanned
    predecessor attempt.
    """

    if isinstance(flown_sample_ids, (str, bytes)) or not isinstance(
        flown_sample_ids, Sequence
    ):
        raise RailsRunnerError(
            "flown_sample_ids must be a sequence of sample ids, or None"
        )
    if execution_units is not None:
        raise RailsRunnerError(
            "flown_sample_ids restricts a per-sample roster; an execution-unit "
            "roster is addressed by request key and cannot be restricted by it"
        )
    flown = tuple(str(sample_id) for sample_id in flown_sample_ids)
    if not flown:
        raise RailsRunnerError("flown_sample_ids must name at least one sample")
    if len(set(flown)) != len(flown):
        raise RailsRunnerError("flown_sample_ids contains duplicate sample ids")
    available = {sample.sample_id for sample in samples}
    unknown = sorted(set(flown) - available)
    if unknown:
        raise RailsRunnerError(
            f"flown_sample_ids names {len(unknown)} sample(s) outside split "
            f"{split_id!r}: {unknown[:5]}"
        )
    keep = set(flown)
    return tuple(sample for sample in samples if sample.sample_id in keep)


def _validated_bootstrap_value_ids(
    snapshot: KnowledgeSnapshot,
    values: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise RailsRunnerError("bootstrap_value_ids must be a sequence of value ids")
    value_ids = tuple(values)
    if any(not isinstance(value_id, str) or not value_id for value_id in value_ids):
        raise RailsRunnerError(
            "bootstrap_value_ids must contain only non-empty strings"
        )
    if len(set(value_ids)) != len(value_ids):
        raise RailsRunnerError("bootstrap_value_ids must be unique")
    known = {value.value_id for value in snapshot.values}
    unknown = set(value_ids) - known
    if unknown:
        raise RailsRunnerError(
            "bootstrap_value_ids reference values outside the frozen knowledge "
            f"snapshot: {sorted(unknown)}"
        )
    return value_ids


def _validated_bootstrap_facet_ids(
    snapshot: KnowledgeSnapshot,
    facets: Sequence[str],
) -> tuple[str, ...]:
    if isinstance(facets, (str, bytes)) or not isinstance(facets, Sequence):
        raise RailsRunnerError("bootstrap_facet_ids must be a sequence of facet ids")
    facet_ids = tuple(facets)
    if any(not isinstance(facet_id, str) or not facet_id for facet_id in facet_ids):
        raise RailsRunnerError(
            "bootstrap_facet_ids must contain only non-empty strings"
        )
    if len(set(facet_ids)) != len(facet_ids):
        raise RailsRunnerError("bootstrap_facet_ids must be unique")
    known = {facet.facet_id for facet in snapshot.facets}
    unknown = set(facet_ids) - known
    if unknown:
        raise RailsRunnerError(
            "bootstrap_facet_ids reference facets outside the frozen knowledge "
            f"snapshot: {sorted(unknown)}"
        )
    return facet_ids


def _visible_facets(
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
) -> tuple[KeyFacet, ...]:
    by_id = {facet.facet_id: facet for facet in snapshot.facets}
    unknown = set(query_state.visible_facet_ids) - set(by_id)
    if unknown:
        raise RailsRunnerError(
            "QueryState references facets outside the frozen knowledge snapshot: "
            f"{sorted(unknown)}"
        )
    return tuple(by_id[facet_id] for facet_id in query_state.visible_facet_ids)


def _visible_values(
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
) -> tuple[ValueBundle, ...]:
    by_id = {value.value_id: value for value in snapshot.values}
    unknown = set(query_state.retrieved_value_ids) - set(by_id)
    if unknown:
        raise RailsRunnerError(
            "QueryState references values outside the frozen knowledge snapshot: "
            f"{sorted(unknown)}"
        )
    return tuple(by_id[value_id] for value_id in query_state.retrieved_value_ids)


def _supply_for_state(
    snapshot: KnowledgeSnapshot,
    query_state: QueryState,
) -> SupplyPacket | None:
    values = _visible_values(snapshot, query_state)
    if not values:
        return None
    items = tuple(
        SupplyItem(
            item_id=f"knowledge:{value.value_id}",
            text=value.content,
            evidence_id=value.value_id,
        )
        for value in values
    )
    return SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(
            n_items=len(items),
            token_count=sum(len(item.text.split()) for item in items),
        ),
        prompt_block="\n".join(
            f"[value {item.evidence_id}] {item.text}" for item in items
        ),
        assembly_template_id="knowledge-value-bundle-v1",
        items=items,
    ).validate()


# ---------------------------------------------------------------------------
# Cell RANKVIS (owner decision 171, 2026-09-27): rank-ordered, rank-visible
# rendering of named knowledge stores. Reachable ONLY when
# ``native_episode.knowledge_value_rendering`` is armed; with the key absent
# neither function below is called and every request byte is unchanged.
#
# Why the order is changed HERE and not in the fuser: ``rails.kb_policy.
# _fuse_supply_filter`` returns ``tuple(sorted(set(selected_value_ids)))``, so
# the exemplar block renders in lexicographic value-id order and its
# retrieval rank dies there (M1 analysis section 4.2; Spearman between
# rendered position and rank 0.007). Re-ordering the ``FusionDecision`` at the
# runner's supply step keeps the selected SET, the rank result, the
# supporting facets and every hash edge of the decision, changes only the
# order of ``selected_value_ids`` inside each named store, and leaves the
# prepared-artifact identity modules (``rails.kb_policy``,
# ``rails.knowledge_provider``, ``rails.phase_supply``,
# ``rails.knowledge_stores``, ``core.flight.runtime``) byte-unchanged.
# ---------------------------------------------------------------------------

#: The visible rank label, prefixed to a named store's value content. The
#: transport renders the part as ``[evidence <id>] <text>``, so the model
#: reads ``[evidence <id>] retrieval rank 3: <content>``.
RANK_VISIBLE_LABEL = "retrieval rank {rank}: "


def _value_store_id(value_id: str) -> str | None:
    """The store prefix of a qualified value id (``<store>::<local>``), or None."""

    store, separator, _local = value_id.partition("::")
    return store if separator else None


def order_supply_by_retrieval_rank(supply, snapshot: KnowledgeSnapshot, stores):
    """``supply`` with each named store's selected values in retrieval-rank order.

    The rank of a selected value is the score of its best supporting facet in
    the supply's own ``RankResult`` (``rails.knowledge_index.
    value_retrieval_ranks``, the E21w arithmetic, unchanged), ties by value id.
    Values of a store not named in ``stores`` keep their positions and their
    order; the named store's values are sorted among the positions that store
    already occupies, so the interleaving of stores inside one composed supply
    is preserved. Returns the SAME object when nothing moves.
    """

    from .knowledge_index import value_retrieval_ranks  # noqa: PLC0415

    decision = supply.fusion_decision
    selected = tuple(decision.selected_value_ids)
    named = frozenset(stores)
    if not selected or not any(_value_store_id(v) in named for v in selected):
        return supply
    ranks = value_retrieval_ranks(
        rank_result=supply.rank_result,
        fusion_decision=decision,
        values=snapshot.values,
    )
    reordered = list(selected)
    for store in sorted(named):
        positions = [i for i, v in enumerate(selected) if _value_store_id(v) == store]
        if len(positions) < 2:
            continue
        members = sorted(
            (selected[i] for i in positions),
            key=lambda v: (ranks.get(v, {}).get("rank", len(selected) + 1), v),
        )
        for position, value_id in zip(positions, members, strict=True):
            reordered[position] = value_id
    if tuple(reordered) == selected:
        return supply
    return replace(
        supply,
        fusion_decision=replace(decision, selected_value_ids=tuple(reordered)).validate(),
    ).validate()


def rank_visible_value_renderer(*, snapshot_sha256: str, stores):
    """A ``knowledge_value_renderer`` that shows each named store's rank.

    It renders exactly the parts ``_agent_messages`` renders when no renderer
    is bound -- same values, same order, same ``evidence_id``, ``source_uri``
    and ``knowledge_role`` -- except that a value of a named store carries the
    :data:`RANK_VISIBLE_LABEL` prefix with its 1-based position among that
    store's values in ``QueryState.retrieved_value_ids``. Under
    ``order: retrieval-rank`` that position IS the retrieval rank: the
    first-phase seed arrives in the associated-values fuser's rank order, and
    every later supply step is re-ordered by
    :func:`order_supply_by_retrieval_rank` before it is acquired.
    """

    named = frozenset(stores)

    def render(snapshot, query_state, agent_states):  # noqa: ARG001
        counters: dict[str, int] = {}
        parts: list[Mapping[str, object]] = []
        for value in _visible_values(snapshot, query_state):
            store = _value_store_id(value.value_id)
            text = value.content
            if store in named:
                counters[store] = counters.get(store, 0) + 1
                text = RANK_VISIBLE_LABEL.format(rank=counters[store]) + text
            parts.append({
                "type": "text",
                "text": text,
                "evidence_id": value.value_id,
                "source_uri": f"knowledge-snapshot://{snapshot_sha256}/{value.value_id}",
                "knowledge_role": "value",
            })
        return parts

    return render


def _agent_messages(
    *,
    adapter: TaskAdapter,
    sample: TaskSample,
    task_contract: str,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    query_state: QueryState,
    agent_states: Sequence[AgentStateArtifact] = (),
    knowledge_value_renderer: object = None,
    knowledge_index: object = None,
    index_role_kind: str | None = None,
    index_sink: object = None,
    prepared_text: bool = False,
) -> tuple[Mapping[str, object], ...]:
    """The two messages one contact is composed from.

    Item E21 (the knowledge INDEX, not the Earnings-21 carrier), 2026-09-19,
    owner decisions 48 and 50: with ``knowledge_index`` bound -- which
    happens exactly when ``native_episode.knowledge_index`` is armed, and
    never otherwise -- the released index is appended as a PURE SUFFIX of
    the rendered contract fill and the row's ``value:`` evidence blocks are
    replaced by the pointer block plus the bounded expansion. Both halves
    move together (``rails.knowledge_index.apply_to_payload`` refuses one
    without the other by name), and with the key absent every byte below is
    exactly its pre-E21 self: ``knowledge_index`` is ``None``, the two
    branches are unreachable and the returned messages are byte-identical.
    """

    if prepared_text:
        from .prepared_text import PREPARED_TEXT_INSTRUCTION
        if (
            task_contract != PREPARED_TEXT_INSTRUCTION
            or query_state.visible_facet_ids or query_state.retrieved_value_ids
            or knowledge_value_renderer is not None or knowledge_index is not None
        ):
            raise RailsRunnerError("prepared text cannot consume fresh task knowledge")
        return (
            {"role": "system", "content": PREPARED_TEXT_INSTRUCTION},
            {"role": "user", "content": []},
        )
    base_messages = tuple(adapter.assemble_prompt(sample, None))
    if len(base_messages) != 2:
        raise RailsRunnerError(
            "TaskAdapter.assemble_prompt must return exactly system and user messages"
        )
    system = base_messages[0]
    if not isinstance(system, Mapping) or system.get("role") != "system":
        raise RailsRunnerError("TaskAdapter first message must have role 'system'")
    system_text = system.get("content")
    if not isinstance(system_text, str) or not system_text:
        raise RailsRunnerError("TaskAdapter system content must be a non-empty string")
    if task_contract not in system_text:
        system_text = f"{system_text}\n\nTask contract:\n{task_contract}"
    if knowledge_index is not None:
        # E21 layout rule 4.1: the index is a pure SUFFIX of the fill, so
        # the frozen template is untouched and the whole system message
        # stays CONSTANT across every contact of the row -- which is the
        # entire economic premise (E17 refusal 7).
        system_text = f"{system_text}{knowledge_index.suffix()}"

    if query_state.query_source == "speech_audio":
        content: list[Mapping[str, object]] = [
            {"type": "input_audio", "media_relpath": query_state.speech_packet_id}
        ]
    else:
        content = [
            {
                "type": "input_speech_features",
                "speech_features": {
                    "packet_id": query_state.speech_packet_id,
                    "sha256": query_state.speech_packet_sha256,
                    "role": "query",
                },
            }
        ]
    content.extend(
        {
            "type": "text",
            "text": facet.representation,
            "evidence_id": f"key:{facet.facet_id}",
            "source_uri": (f"knowledge-snapshot://{snapshot_sha256}/{facet.facet_id}"),
            "knowledge_role": "key",
        }
        for facet in _visible_facets(snapshot, query_state)
    )
    if knowledge_value_renderer is None:
        content.extend(
            {
                "type": "text",
                "text": value.content,
                "evidence_id": value.value_id,
                "source_uri": (f"knowledge-snapshot://{snapshot_sha256}/{value.value_id}"),
                "knowledge_role": "value",
            }
            for value in _visible_values(snapshot, query_state)
        )
    else:
        content.extend(knowledge_value_renderer(snapshot, query_state, agent_states))
    if knowledge_index is not None:
        content = _index_content(
            content,
            index=knowledge_index,
            agent_states=agent_states,
            role_kind=index_role_kind,
            sample_id=query_state.query_sample_id,
            sink=index_sink,
        )
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    )


def _index_content(
    content: Sequence[Mapping[str, object]],
    *,
    index: object,
    agent_states: Sequence[object],
    role_kind: str | None,
    sample_id: object,
    sink: object,
) -> list[Mapping[str, object]]:
    """E21: the row's ``value:`` blocks, replaced by pointers and expansions.

    The selection is derived from what THIS contact already has -- the
    Perception node's own sealed candidates, the retrieved exemplars' own
    construction intents and the candidate projection's bound slot types --
    and never from gold, a reference transcript or a future turn. Before
    Perception has answered there is no Perception state, so the retrieval
    order stands in and the provenance record says so.

    ``key`` blocks (the stable knowledge prefix) and the speech packet
    reference are untouched: the index replaces the per-row VALUE rendering
    and nothing else.
    """

    from .knowledge_index import KnowledgeIndexError  # noqa: PLC0415

    evidence = [
        part for part in content
        if isinstance(part, Mapping) and part.get("type") == "text"
    ]
    states = [
        state.as_json() if hasattr(state, "as_json") else state
        for state in agent_states or ()
    ]
    try:
        selection, provenance = index.select(
            evidence_items=evidence, agent_states=states, sample_id=sample_id,
        )
        assembly = index.assemble_for(selection, role_id=role_kind)
    except KnowledgeIndexError as error:
        raise RailsRunnerError(
            f"the knowledge index could not assemble this contact: {error}"
        ) from error
    kept = [
        part for part in content
        if not (
            isinstance(part, Mapping)
            and part.get("type") == "text"
            and part.get("knowledge_role") == "value"
        )
    ]
    composed = list(kept)
    composed.extend(
        {
            "type": "text",
            "text": item["content"],
            "evidence_id": item["evidence_id"],
            # E21 gap 1: the pointer and expansion blocks carry their OWN
            # source, so the payload's ``evidence_provenance`` names the
            # released view rather than the rails message that rendered it
            # (``rails.core_client`` derives one provenance row per part).
            "source_uri": item["source_uri"],
            "knowledge_role": "value",
        }
        for item in assembly.evidence_items()
    )
    if sink is not None:
        sink(assembly, selection, provenance)
    return composed


def _runtime_context(
    *,
    prepared: _PreparedAgentTask,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    query_state: QueryState,
    state_store: Mapping[str, AgentStateArtifact],
    response_sha256s: Sequence[str],
    contact_index: int,
) -> AgentRuntimeContext:
    try:
        ordered_states = tuple(
            state_store[state_id] for state_id in query_state.agent_state_ids
        )
    except KeyError as error:
        raise RailsRunnerError(
            f"QueryState references an unmaterialized Agent state {error.args[0]!r}"
        ) from None
    return AgentRuntimeContext(
        sample_id=prepared.sample.sample_id,
        execution_unit_id=prepared.execution_unit_id,
        execution_unit_binding=prepared.execution_unit_binding,
        knowledge_snapshot_sha256=snapshot_sha256,
        catalog_facet_ids=tuple(facet.facet_id for facet in snapshot.facets),
        catalog_value_ids=tuple(value.value_id for value in snapshot.values),
        query_state=query_state,
        task_contract=prepared.task_contract,
        agent_states=ordered_states,
        prior_response_sha256s=tuple(response_sha256s),
        contact_index=contact_index,
    )


def _validate_new_agent_states(
    *,
    artifacts: tuple[AgentStateArtifact, ...],
    transition: AgentStepTransition,
    prior_query_state: QueryState,
    response_sha256: str,
    snapshot: KnowledgeSnapshot,
    existing_state_ids: set[str],
) -> None:
    if not isinstance(artifacts, tuple):
        raise RailsRunnerError("AgentLoopAdvance.new_agent_states must be a tuple")
    artifact_ids: list[str] = []
    known_value_ids = {value.value_id for value in snapshot.values}
    for artifact in artifacts:
        if not isinstance(artifact, AgentStateArtifact):
            raise RailsRunnerError(
                "AgentLoopAdvance.new_agent_states entries must be AgentStateArtifact"
            )
        artifact.validate()
        if artifact.source_query_state_sha256 != prior_query_state.content_hash():
            raise RailsRunnerError(
                "Agent state artifact is bound to a different prior QueryState"
            )
        if artifact.source_response_sha256 != response_sha256:
            raise RailsRunnerError(
                "Agent state artifact is bound to a different model response"
            )
        unknown_citations = set(artifact.cited_value_ids) - known_value_ids
        if unknown_citations:
            raise RailsRunnerError(
                "Agent state artifact cites values outside the frozen snapshot: "
                f"{sorted(unknown_citations)}"
            )
        if artifact.state_id in existing_state_ids:
            raise RailsRunnerError(
                f"Agent state artifact {artifact.state_id!r} already exists"
            )
        artifact_ids.append(artifact.state_id)
    if tuple(artifact_ids) != transition.new_agent_state_ids:
        raise RailsRunnerError(
            "new Agent state artifacts must exactly match transition.new_agent_state_ids"
        )



#: Owner decision 266-E / 199: the receipt a non-native contact leaves when the frozen core delivered NO content (a thinking core that spends
#: its whole completion budget on reasoning leaves ``message.content`` empty). The row delivers the empty answer bytes -- an abstention the
#: scorer counts as a miss -- instead of aborting the flight. Added beside the existing records; no record of a non-empty completion moves.
EMPTY_COMPLETION_SCHEMA = "saea-empty-completion-v1"


def _emit_empty_completion_receipt(trace_buffer: TraceBuffer, arguments: Mapping[str, object]) -> None:
    """Receipt one empty non-native completion: ``cap_hit``, ``completion_tokens`` and ``finish_reason`` (Thinking transports forward it).

    ``cap_hit`` is true when the completion spent its whole budget: the wire ``finish_reason`` is ``length``, or the recorded
    ``completion_tokens`` reach the contact's ``max_tokens`` (the live cap rule ``core.delivery.terminal_response_saturated``).
    """

    from ..core.delivery import terminal_response_saturated

    cost_record_id, cost = None, {}
    for channel, record_id, payload in trace_buffer.iter_records():
        if channel == "COST" and record_id.endswith("/cost"):
            cost_record_id, cost = record_id, payload
    decoding = arguments.get("decoding_params")
    max_tokens = decoding.get("max_tokens") if isinstance(decoding, Mapping) else None
    completion_tokens = cost.get("completion_tokens")
    finish_reason = cost.get("finish_reason") if isinstance(cost.get("finish_reason"), str) else None
    by_tokens = terminal_response_saturated({"completion_tokens": completion_tokens}, max_tokens)
    contact_id = arguments.get("agent_contact_id")
    trace_buffer.emit(
        "TOOL", f"{contact_id}/empty-completion",
        {
            "schema": EMPTY_COMPLETION_SCHEMA,
            "agent_contact_id": contact_id,
            "request_id": None if cost_record_id is None else cost_record_id[: -len("/cost")],
            "response_text_sha256": hashlib.sha256(b"").hexdigest(),
            "disposition": "empty-delivery-abstention",
            "cap_hit": bool(by_tokens or finish_reason == "length"),
            "cap_hit_basis": "finish-reason-length" if finish_reason == "length" else (
                "completion-tokens-reach-max-tokens" if by_tokens else "not-at-cap"),
            "completion_tokens": completion_tokens if isinstance(completion_tokens, int) else None,
            "max_tokens": max_tokens if isinstance(max_tokens, int) and not isinstance(max_tokens, bool) else None,
            "finish_reason": finish_reason,
        },
    )


def _empty_completion_receipted(buffers: Sequence[TraceBuffer]) -> Callable[[str], bool]:
    """A lookup: does one of ``buffers`` hold the empty-completion receipt of this contact?"""

    def lookup(contact_id: str) -> bool:
        for buffer in buffers:
            for channel, record_id, payload in buffer.iter_records():
                if (channel == "TOOL" and record_id == f"{contact_id}/empty-completion"
                        and isinstance(payload, Mapping) and payload.get("schema") == EMPTY_COMPLETION_SCHEMA):
                    return True
        return False

    return lookup


def _role_thinking_policy(config, thinking_policy: Mapping[str, object] | None) -> dict[str, Mapping[str, object]] | None:
    """Re-key a ``thinking_policy`` (keyed by role KIND: perception, solver, ...) by this episode's role phase ids.

    Refuses a key that names no role of the episode, so a typo can never silently leave a node on its fragment default.
    """

    if not thinking_policy:
        return None
    by_kind = {role.role_kind: role.phase_id for role in config.roles}
    unknown = sorted(set(thinking_policy) - set(by_kind))
    if unknown:
        raise RailsRunnerError(f"thinking_policy names nodes that are not roles of this episode: {unknown}")
    return {by_kind[kind]: entry for kind, entry in thinking_policy.items()}


def _sampling_decoding_table(group, perception_phase_id, solver_phase_id):
    """Decision 338: ``{branch id: {role phase id: {decoding, seed_offsets}}}`` for a sampling group (see
    ``rails.supply_variants.sampling_decoding_table``)."""

    from .supply_variants import sampling_decoding_table

    return sampling_decoding_table(
        group, perception_phase_id=perception_phase_id, solver_phase_id=solver_phase_id,
    ) or None


def _branch_thinking_policy(config, group) -> dict[str, dict[str, Mapping[str, object]]] | None:
    """NX-T R1: re-key a thinking-policy column's per-branch ``{role kind: override}`` maps by this episode's role phase ids.

    ``{branch id: {role phase id: override}}`` for every candidate branch; ``None`` when the group is not a thinking-policy
    group (every other config). A policy naming a role kind that is not a role of the episode is refused by name.
    """

    if group is None or not group.is_thinking:
        return None
    by_kind = {role.role_kind: role.phase_id for role in config.roles}
    out: dict[str, dict[str, Mapping[str, object]]] = {}
    for branch in group.branches:
        if branch.thinking_policy is None:
            continue
        unknown = sorted(set(branch.thinking_policy) - set(by_kind))
        if unknown:
            raise RailsRunnerError(
                f"thinking arm {branch.branch_id!r} names nodes that are not roles of this episode: {unknown}"
            )
        out[branch.branch_id] = {by_kind[kind]: entry for kind, entry in branch.thinking_policy.items()}
    return out


def _apply_node_thinking(
    decoding_params: dict[str, object], thinking_policy: Mapping[str, object] | None,
    controller: object, contact_id: str,
) -> None:
    """Decision 283 A: resolve a contact's per-node thinking override in place (no-op without a policy or a named node)."""

    if not thinking_policy:
        return
    namer = getattr(controller, "phase_name_for_contact", None)
    node = namer(contact_id) if callable(namer) else None
    if node is None:
        return
    from ..core.reasoning_knobs import ReasoningKnobError, resolve_node_decoding  # noqa: PLC0415

    try:
        resolved = resolve_node_decoding(decoding_params, thinking_policy, node)
    except ReasoningKnobError as error:
        raise RailsRunnerError(str(error)) from error
    decoding_params.clear()
    decoding_params.update(resolved)


def _last_cost(trace_buffer: TraceBuffer) -> tuple[str | None, Mapping[str, object]]:
    from ..core.reasoning_knobs import last_cost_record  # noqa: PLC0415

    return last_cost_record(trace_buffer)


def _reasoning_fallback_reask(
    *, core_client: CoreClient, messages, arguments, trace_buffer: TraceBuffer,
) -> tuple[str, Mapping[str, object]] | None:
    """Decision 278 / 283 A: ONE receipted answer-only re-ask of a budgeted thinking contact that came back empty at its cap.

    Eligible only when the request carries a thinking budget with room for an answer (``max_tokens`` > budget, thinking on) and
    the recorded first completion hit its cap with empty content (finish reason ``length``, or completion tokens at
    ``max_tokens``). The re-ask repeats the same messages and arguments with ``enable_thinking: false`` and ``max_tokens`` = the
    reserve; it is metered and traced as an ordinary contact (it spends one unit of the plan's model-call budget) and leaves a
    ``saea-thinking-answer-fallback-v1`` receipt (ids, finish reasons, token counts; no text). Thinking text is never carried: the
    request is rebuilt from the same inputs. Returns the re-ask's text and its arguments, or None when not eligible.
    """

    from ..core.delivery import terminal_response_saturated  # noqa: PLC0415
    from ..core.reasoning_knobs import answer_only_decoding, fallback_receipt, fallback_reserve  # noqa: PLC0415

    decoding = arguments.get("decoding_params")
    if not isinstance(decoding, Mapping):
        return None
    reserve = fallback_reserve(decoding)
    if reserve is None:
        return None
    first_id, first_cost = _last_cost(trace_buffer)
    finish = first_cost.get("finish_reason") if isinstance(first_cost.get("finish_reason"), str) else None
    if not (finish == "length" or terminal_response_saturated(
            {"completion_tokens": first_cost.get("completion_tokens")}, decoding.get("max_tokens"))):
        return None
    reask_arguments = {**arguments, "decoding_params": answer_only_decoding(decoding)}
    text = core_client.complete(messages, **reask_arguments)
    if not isinstance(text, str):
        raise RailsRunnerError("frozen core response must be a string")
    second_id, second_cost = _last_cost(trace_buffer)
    if second_id == first_id:
        raise RailsRunnerError("the answer-only re-ask left no COST record")
    contact_id = arguments.get("agent_contact_id")
    trace_buffer.emit(
        "TOOL", f"{contact_id}/reasoning-fallback",
        fallback_receipt(
            agent_contact_id=contact_id,
            first_request_id=None if first_id is None else first_id[: -len("/cost")],
            reask_request_id=second_id[: -len("/cost")],
            first_finish_reason=finish,
            reask_finish_reason=second_cost.get("finish_reason"),
            first_tokens=first_cost, reask_tokens=second_cost, reserve=reserve, answered=text != "",
        ),
    )
    return text, reask_arguments


def _complete_agent_request(
    *, core_client: CoreClient, messages, arguments, trace_buffer: TraceBuffer,
    prepared_request: PreparedCoreRequest | None = None,
) -> tuple[str, CoreCompletion | None]:
    """Preserve response-local native metadata on the same metered request path."""
    native = "tool_choice" in arguments.get("decoding_params", {})
    method_name = (
        "complete_prepared_with_metadata" if native else "complete_prepared"
    ) if prepared_request is not None else (
        "complete_with_metadata" if native else "complete"
    )
    method = getattr(core_client, method_name, None)
    if not callable(method):
        raise RailsRunnerError(
            f"native contact requires shared client method {method_name}"
        )
    if prepared_request is None:
        result = method(messages, **arguments)
    else:
        result = method(
            prepared_request, id_slot=arguments["decoding_params"].get("id_slot"),
        )
    if not native:
        if not isinstance(result, str):
            raise RailsRunnerError("frozen core response must be a string")
        if result == "":
            reask = _reasoning_fallback_reask(
                core_client=core_client, messages=messages, arguments=arguments, trace_buffer=trace_buffer,
            )
            if reask is not None:
                result, arguments = reask
        if result == "":
            _emit_empty_completion_receipt(trace_buffer, arguments)
        return result, None
    if not isinstance(result, CoreCompletion):
        raise RailsRunnerError("native contact requires source-bound CoreCompletion")
    result.assert_binding(
        sample_id=arguments.get(
            "speech_feature_sample_id", arguments.get("raw_agent_sample_id")
        ),
        agent_contact_id=arguments["agent_contact_id"],
        response_text=result.text,
    )
    trace_buffer.emit(
        "TOOL", f"{result.request_id}/native-completion",
        {
            "schema": "saea-native-completion-v1",
            "request_id": result.request_id,
            "sample_id": result.sample_id,
            "agent_contact_id": result.agent_contact_id,
            "request_sha256": result.request_sha256,
            "response_sha256": result.response_sha256,
            "response_text_sha256": result.response_text_sha256,
            "native_tool_calls_json": result.tool_calls_json.decode("utf-8"),
            "native_tool_calls_sha256": result.tool_calls_sha256,
        },
    )
    return result.text, result


def _run_agent_trajectory(
    *,
    prepared: _PreparedAgentTask,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    protected_material: tuple[str, ...],
    adapter: TaskAdapter,
    controller_factory: AgentControllerFactory,
    controller_policy_id: str,
    core_client: CoreClient,
    max_contacts: int,
    slot_id: int,
    base_decoding_params: Mapping[str, object] | None,
    trace_buffer: TraceBuffer,
    observe_step: ObserveStep | None = None,
    record_namespace: str | None = None,
    knowledge_value_renderer: object = None,
    thinking_policy: Mapping[str, object] | None = None,
) -> _AgentRuntimeOutcome:
    controller = controller_factory(prepared.sample.sample_id)
    if not callable(getattr(controller, "initial_contact", None)) or not callable(
        getattr(controller, "advance", None)
    ):
        raise RailsRunnerError(
            f"controller factory for {controller_policy_id!r} returned an invalid controller"
        )

    query_state = prepared.initial_query_state
    origin_packet = (
        prepared.initial_query_state.speech_packet_id,
        prepared.initial_query_state.speech_packet_sha256,
    )
    observe_record_base = _agent_record_base(
        prepared.sample.sample_id, record_namespace, prepared.execution_unit_id
    )
    relisten_count = 0
    state_store = {item.state_id: item for item in prepared.initial_feedback_states}
    response_sha256s: list[str] = []
    contacts: list[AgentContactRecord] = []
    waves: list[AgentWaveRecord] = []
    transitions: list[AgentStepTransition] = []
    context = _runtime_context(
        prepared=prepared,
        snapshot=snapshot,
        snapshot_sha256=snapshot_sha256,
        query_state=query_state,
        state_store=state_store,
        response_sha256s=response_sha256s,
        contact_index=0,
    )
    contact = controller.initial_contact(context)

    for contact_index in range(max_contacts):
        if not isinstance(contact, AgentContactPlan):
            raise RailsRunnerError(
                "trajectory dispatch requires AgentContactPlan; "
                "AgentContactBatch requires contact dispatch"
            )
        contact.validate()
        _assert_agent_control_excludes_knowledge_payloads(contact, protected_material)
        if contact.query_state_sha256 != query_state.content_hash():
            raise RailsRunnerError(
                "AgentContactPlan is bound to a different QueryState"
            )
        context = _runtime_context(
            prepared=prepared,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            state_store=state_store,
            response_sha256s=response_sha256s,
            contact_index=contact_index,
        )
        decoding_params = dict(base_decoding_params or {})
        decoding_params.update(dict(contact.decoding_params))
        _apply_node_thinking(decoding_params, thinking_policy, controller, contact.contact_id)
        decoding_params["id_slot"] = slot_id
        messages = _agent_messages(
            adapter=adapter,
            sample=prepared.sample,
            task_contract=prepared.task_contract,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            agent_states=context.agent_states,
            knowledge_value_renderer=knowledge_value_renderer,
            prepared_text=getattr(core_client, "arm", None) == "prepared-context-text",
        )
        source_arguments = (
            {"text_only_sample_id": prepared.sample.sample_id}
            if getattr(core_client, "arm", None) == "prepared-context-text" else
            {"raw_agent_sample_id": prepared.sample.sample_id}
            if query_state.query_source == "speech_audio"
            else {
                "speech_feature_sample_id": prepared.sample.sample_id,
                "key_representation_id": contact.key_representation_id,
                "matcher_policy_id": contact.matcher_policy_id,
            }
        )
        response_text, completion = _complete_agent_request(
            core_client=core_client, messages=messages, trace_buffer=trace_buffer,
            arguments={
                "decoding_params": decoding_params,
                **source_arguments,
                "agent_state": tuple(a.as_json() for a in context.agent_states),
                "agent_contact_id": contact.contact_id,
                "contact_instruction": contact.instruction,
            },
        )
        if completion is not None:
            context = replace(context, core_completions=(completion,))
        response_sha256 = agent_response_sha256(contact, response_text)
        response_sha256s.append(response_sha256)
        contacts.append(
            AgentContactRecord(
                plan=contact,
                query_state_sha256=query_state.content_hash(),
                speech_packet_sha256=query_state.speech_packet_sha256,
                slot_id=slot_id,
                response_sha256=response_sha256,
            )
        )
        advance = controller.advance(context, contact, response_text)
        if not isinstance(advance, AgentLoopAdvance):
            raise RailsRunnerError(
                "Agent controller.advance must return AgentLoopAdvance"
            )
        _validate_agent_knowledge_decision(
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=query_state,
            advance=advance,
        )
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=query_state,
            next_query_state=advance.next_query_state,
            transition=advance.transition,
            snapshot_sha256=snapshot_sha256,
            origin_speech_packet=origin_packet,
        )
        _validate_new_agent_states(
            artifacts=advance.new_agent_states,
            transition=advance.transition,
            prior_query_state=query_state,
            response_sha256=response_sha256,
            snapshot=snapshot,
            existing_state_ids=set(state_store),
        )
        waves.append(
            _agent_wave_record(
                wave_index=contact_index,
                contact=contact,
                response=response_text,
                slot_ids=(slot_id,),
                query_state=query_state,
                advance=advance,
            )
        )
        transitions.append(advance.transition)

        if advance.transition.action_kind == "stop":
            if advance.next_contact is not None:
                raise RailsRunnerError("stop cannot schedule another Agent contact")
            final_response_text = _resolve_final_agent_response(
                contact,
                response_text,
                advance.final_response_contact_id,
                allow_empty=prepared.execution_unit_id is not None,
                empty_receipted=_empty_completion_receipted((trace_buffer,)),
            )
            return _AgentRuntimeOutcome(
                prepared=prepared,
                final_query_state=query_state,
                final_response_text=final_response_text,
                contacts=tuple(contacts),
                waves=tuple(waves),
                transitions=tuple(transitions),
                agent_states=tuple(
                    state_store[state_id] for state_id in query_state.agent_state_ids
                ),
                final_supply=_supply_for_state(snapshot, query_state),
                trace_buffer=trace_buffer,
            )

        if advance.next_query_state is None or advance.next_contact is None:
            raise RailsRunnerError(
                "non-stop Agent transition requires next QueryState and contact"
            )
        if advance.final_response_contact_id is not None:
            raise RailsRunnerError(
                "non-stop Agent transition cannot select a final response"
            )
        if advance.transition.action_kind == "backtrack":
            for state_id in advance.transition.dropped_agent_state_ids:
                if state_id not in state_store:
                    raise RailsRunnerError(
                        f"backtrack cannot drop unknown Agent state {state_id!r}"
                    )
                state_store.pop(state_id)
        else:
            for artifact in advance.new_agent_states:
                state_store[artifact.state_id] = artifact
        if set(advance.next_query_state.agent_state_ids) != set(state_store):
            raise RailsRunnerError(
                "successor QueryState Agent state ids do not match materialized state"
            )
        if contact_index + 1 >= max_contacts:
            raise RailsRunnerError(
                f"Agent trajectory exceeded its {max_contacts}-contact ceiling"
            )
        query_state = advance.next_query_state
        contact = advance.next_contact
        if observe_step is not None:
            observed = _observe_relisten(
                observe_step=observe_step,
                snapshot=snapshot,
                snapshot_sha256=snapshot_sha256,
                sample_id=prepared.sample.sample_id,
                record_base=observe_record_base,
                origin_packet=origin_packet,
                wave_index=contact_index,
                relisten_index=relisten_count,
                query_state=query_state,
                sink=trace_buffer,
            )
            if observed is not None:
                query_state, relisten_transition = observed
                transitions.append(relisten_transition)
                contact = _rebind_contact(contact, query_state.content_hash())
                relisten_count += 1

    raise RailsRunnerError(
        f"Agent trajectory exceeded its {max_contacts}-contact ceiling"
    )


def _solver_fragment_seed(program_id: str) -> int:
    """Deterministic per-config-fragment base seed for grouped Solver
    sampling (E2b, SLURP v2 base program M2 live wiring).

    ``reproduction.ojw.native_request.compose_solver_sample_decoding_params``
    seeds sample i of one Solver visit as ``fragment_seed + seed_offset +
    i``. Every row of one run shares this SAME base -- it is derived only
    from the composed program's own identity (``program.program_id``, the
    same "fragment identity" every other native-episode contact id and key
    representation id in this function already keys on), never from the row
    -- so a fixed N-way diversity set repeats identically across rows,
    exactly as an owner-picked constant seed would, without requiring the
    frozen ``roles.solver.decoding_overrides``/``commit`` config shape (E2)
    to carry one.
    """

    digest = content_hash({"saea_solver_fragment_seed_v1": program_id})
    return int(digest[:8], 16)


def _parse_perception_branch_note(text: str) -> tuple[str, tuple[str, ...], int]:
    """One Perception branch's own ``(note_parse_status,
    candidate_intent_ids, candidate_intent_ids_raw_count)``, read directly
    off its RAW response text -- never a sealed state, since a non-delivering
    branch (design section 3) registers none.

    Delegates to ``rails.native_episode_receipt.parse_perception_branch_note``
    (receipt schema v2), the one parse the resume replay and the bundle's I7v
    re-derivation also apply. Until 2026-09-29 this returned the parsed list
    VERBATIM, so a note that listed one intent twice sealed a list the
    receipt validator refused at seal time (the P-SV-1 abort, 61 branch notes
    over 49 of 1,080 rows); an empty ``candidates`` list and a malformed
    document both returned the ``("unparsed",)`` sentinel. Now duplicates
    collapse to their first occurrence (``duplicates-collapsed``), an empty
    list stays empty (``empty``), and a malformed note extracts nothing
    (``malformed``): every one a measured outcome, never a seal failure.
    """

    from .native_episode_receipt import parse_perception_branch_note

    return parse_perception_branch_note(text)


#: The synthetic evidence-id scheme a Perception branch's own presentation or
#: response-contract addition uses (design section 3, "What to build" items 2
#: and 3): distinguishable at a glance from a real snapshot value id (which
#: is always store-qualified with ``"::"``) and from a branch's own supplied
#: ids, so it can never be mistaken for either.
PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_SCHEME = "perception-branch-presentation"
PERCEPTION_BRANCH_CONTRACT_EVIDENCE_SCHEME = "perception-branch-contract"


def _perception_branch_value_renderer(*, branch, snapshot_sha256, supplied_value_ids):
    """The ``knowledge_value_renderer`` a non-A, non-T branch's own view
    renders with (design section 3, "What to build" item 2): ``rank-
    visible-v1`` wraps ``rank_visible_value_renderer`` over the stores THIS
    branch's own supplied ids span, so a branch's own view -- and only its
    own view, since ``base_messages``'s own ``value_renderer_override`` is
    per-call -- shows retrieval-rank labels. ``None`` for every other
    presentation (including no presentation at all), which leaves
    ``base_messages`` to use the row's own outer renderer, byte-identically
    to before this axis existed.
    """

    from ..core.base import PERCEPTION_PRESENTATIONS
    from .perception_presentations import RANK_VISIBLE_PRESENTATION_ID

    if branch.presentation_id != RANK_VISIBLE_PRESENTATION_ID:
        return None
    stores = tuple(sorted({
        store for store in (
            _value_store_id(value_id) for value_id in supplied_value_ids
        )
        if store
    }))
    presentation = PERCEPTION_PRESENTATIONS.resolve(RANK_VISIBLE_PRESENTATION_ID)
    return presentation(snapshot_sha256=snapshot_sha256, stores=stores)


def _carrier_hooks(profile):
    """The run's ``CarrierHooks`` (migration step 5), or ``None``. ``None``
    profile -- a config whose carrier declares no hooks, or a test double --
    keeps the SLURP defaults below, the only carrier these nodes run on."""

    if profile is None:
        return None
    from .consumption_module import resolve_carrier_hooks  # noqa: PLC0415

    return resolve_carrier_hooks(profile)


def _slurp_default_hooks():
    from .adapters.slurp_module_hooks import carrier_module_hooks  # noqa: PLC0415

    return carrier_module_hooks()


def _render_perception_branch_presentation(
    *, branch, supplied_value_ids, contrast_pairs, decision_candidates=None,
):
    """A non-A, non-T branch's own ``top2-contrast-v1`` content item, or a
    reason it renders none (design section 3, "What to build" item 2).

    Returns ``(extra_content_item_or_None, skip_reason_or_None)``. ``rank-
    visible-v1`` and "no presentation" both return ``(None, None)`` here --
    ``rank-visible-v1`` is wired separately, as a value-RENDERER override
    (:func:`_perception_branch_value_renderer`), because it reshapes how the
    whole value block renders rather than adding one block.

    Fewer than two DISTINCT candidate intents in the branch's own rendered
    supply (:func:`rails.perception_presentations.branch_supplied_intent_ids`)
    is checked BEFORE the contrast-pair table is ever consulted -- there is
    no rank-1/rank-2 pair to look up at all -- and is its own receipted
    reason (O5's own floor is a DIFFERENT, later reason: a genuine pair with
    too little pool support to have minted a table row).
    """

    from .perception_presentations import (
        TOP2_CONTRAST_PRESENTATION_ID, TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES,
    )

    if branch.presentation_id != TOP2_CONTRAST_PRESENTATION_ID:
        return None, None
    from ..core.base import PERCEPTION_PRESENTATIONS

    # Migration step 5: the decision-unit ids come from the carrier's
    # ``decision_candidates`` hook (SLURP's intent-boundary id shape).
    if decision_candidates is None:
        decision_candidates = _slurp_default_hooks().decision_candidates
    intents = decision_candidates(supplied_value_ids)
    if len(intents) < 2:
        return None, TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES
    presentation = PERCEPTION_PRESENTATIONS.resolve(TOP2_CONTRAST_PRESENTATION_ID)
    text, skip_reason = presentation(
        rank1_intent_id=intents[0], rank2_intent_id=intents[1],
        contrast_pairs=contrast_pairs or {},
    )
    if text is None:
        return None, skip_reason
    item = {
        "type": "text",
        "text": text,
        "evidence_id": (
            f"{PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_SCHEME}:{branch.branch_id}"
        ),
        "source_uri": (
            f"{PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_SCHEME}://"
            f"{branch.presentation_id}/{branch.branch_id}"
        ),
        # Tagged "value" rather than a wire-level-unregistered "contrast"
        # role: ``core.model.transport._ordered_speech_feature_content`` and
        # ``rails.core_client._typed_supply_part`` both admit only
        # {None, "key", "value"} on the actual wire path this study's native
        # episodes send (speech-feature-query arms), and widening that
        # closed, fail-closed set is out of this change's scope. "value" is
        # semantically apt regardless: this block is exactly the kind of
        # cache-MUTABLE, per-branch content a real value is (never a stable
        # instruction key), and its synthetic
        # ``perception-branch-presentation:`` evidence-id scheme keeps it
        # from ever being mistaken for a genuine snapshot value id or for
        # this branch's own ``supplied_value_ids``.
        "knowledge_role": "value",
    }
    return item, None


def _perception_branch_min_candidates_sentence(branch, max_candidates=None):
    """A non-A, non-T branch's own response-contract sentence (design
    section 3, "What to build" item 3), or ``None`` when the branch declares
    no ``min_candidates``.

    ``DEFAULT_MAX_SLURP_CANDIDATES`` (3) is this study's own fixed ceiling on
    a SLURP candidate list -- the SAME ceiling ``rails.native_episode_config``
    already validates every branch's own ``min_candidates`` against
    (``parse_perception_branches(..., max_candidates_ceiling=DEFAULT_MAX_
    SLURP_CANDIDATES)``) and the value every registered cell's own
    ``phase_material.perception.fill_params.max_candidates`` carries today.
    Stating it here needs no new plumbing from the row's own bound
    ``PhaseMaterial.response_format`` (a config-composition-time object this
    runner-level function does not have easy reach into) and stays accurate
    for as long as that coincidence holds; a future cell that ever declares a
    SMALLER ``max_candidates`` would need this sentence threaded from the
    bound material instead.
    """

    if branch.min_candidates is None:
        return None
    # Migration step 5: the ceiling is the carrier's ``max_decision_
    # candidates`` hook (SLURP: ``DEFAULT_MAX_SLURP_CANDIDATES``, 3).
    if max_candidates is None:
        max_candidates = _slurp_default_hooks().max_decision_candidates()

    sentence = (
        "This candidate list must carry at least "
        f"{branch.min_candidates} and at most {max_candidates} "
        "candidates."
    )
    return {
        "type": "text",
        "text": sentence,
        "evidence_id": (
            f"{PERCEPTION_BRANCH_CONTRACT_EVIDENCE_SCHEME}:{branch.branch_id}"
        ),
        "source_uri": (
            f"{PERCEPTION_BRANCH_CONTRACT_EVIDENCE_SCHEME}://"
            f"min-candidates/{branch.branch_id}"
        ),
        "knowledge_role": "value",
    }


async def _invoke_native_role_episode(
    *, state, run_contact, session, binding, adapter, core_client, snapshot,
    snapshot_sha256, protected_material, base_decoding_params, run_id,
    knowledge_value_renderer, run_local=None, system_policy_decision=None,
    role_input_runner=None,
):
    """Collect one public role graph through the shared speech request custody.

    ReAct owns model/tool iteration and history. Workflow owns routing. This
    adapter only binds their actual contacts to existing state, fit and traces.
    """
    from openjiuwen.core.foundation.tool import ToolCard
    from ..core.model.native_framework_history import native_tool_result_message
    from ..reproduction.ojw.native_episode import (
        NativeEpisodeActions, NativeEpisodeNodes, NativeEpisodeSpec, build_native_episode,
    )
    from ..reproduction.ojw.native_group_solver import GroupedSolverRoleNode
    from ..reproduction.ojw.native_request import (
        MeteredNativeSpeechRequest, NativeRoleSpeechBinding,
    )
    from ..reproduction.ojw.native_roles import (
        FrozenCoreRoleContextFitError,
        NativeRoleContactContext, NativeRoleModelRequest, NativeRoleNode,
        NativeRoleNodeSpec, NativeSourceFunction,
    )
    from ..core.model import FrozenCoreContextSizeError
    from .context_fit import (
        BlockAttachment, CONTEXT_COMPACTION_DISPOSITION, CompactableRequest,
        REVIEWER_AUDIT_BLOCK, SCENARIO_HINTS_BLOCK, canonical_bytes,
        compact_to_fit,
    )
    from .controllers import (
        advance_phase_response_state, native_planner_action_response_format,
        restrict_repeat_visit_supply, seal_phase_response_state,
    )
    from .material import PhaseMaterial

    from .execution_units import scoped_execution_contact_id
    config, program = binding.config, binding.program
    if config.solver_tool_access is not None:
        from .native_episode_config import validate_solver_tool_access

        if binding.tools_for_phase is None:
            raise ValueError("Solver lookup requires a bound phase tool dispatcher")
        validate_solver_tool_access(config, binding.tools_for_phase.specs,
                                    dispatcher=binding.tools_for_phase)
    # Item E4 (2026-09-28, owner decision 185): the post-accept targeted
    # re-listen's own config, resolved once. ``None`` for every config
    # written before E4 and every unarmed fragment, which leaves the
    # templates unread and every branch below (``run_relisten_stage`` and its
    # own dispatch helpers, defined further down beside their E8b
    # node-context-cleaning analogue) unreachable -- byte-identical to
    # before this feature existed.
    relisten_config = config.relisten
    # Migration step 5: carrier facts (decision candidates, the candidate-list
    # ceiling, delivered units) come from the run's carrier hooks.
    carrier_hooks = _carrier_hooks(getattr(config, "carrier_profile", None))
    relisten_blind_template = relisten_confirm_template = None
    if relisten_config is not None:
        if binding.repo_root is None:
            raise RailsRunnerError(
                "the relisten stage requires the repository root its "
                "committed blind/confirm templates are read from"
            )
        relisten_blind_template = _load_relisten_template(
            binding.repo_root, relisten_config.blind_template_id,
        )
        relisten_confirm_template = _load_relisten_template(
            binding.repo_root, relisten_config.confirm_template_id,
        )
    if bool(config.local_tool_workers) != (run_local is not None):
        raise RailsRunnerError("native local tool scheduling differs from its configuration")
    # Cell RANKVIS (owner decision 171): ``None`` for every config that does
    # not arm ``native_episode.knowledge_value_rendering`` -- which makes both
    # branches below unreachable and every request byte identical.
    value_rendering = getattr(config, "knowledge_value_rendering", None)
    rank_order_stores: tuple[str, ...] = ()
    if value_rendering is not None:
        if knowledge_value_renderer is not None:
            raise RailsRunnerError(
                "knowledge_value_rendering cannot combine with another value renderer"
            )
        if value_rendering["order"] == "retrieval-rank":
            rank_order_stores = tuple(value_rendering["stores"])
        if value_rendering["rank_visible"]:
            knowledge_value_renderer = rank_visible_value_renderer(
                snapshot_sha256=snapshot_sha256, stores=value_rendering["stores"],
            )
    # E2b (SLURP v2 base program M2 live wiring): the Solver role's own
    # registered grouped-sampling config, resolved once. A samples-1 Solver
    # (every config before this program, and every non-M2 config) carries
    # solver_role_id=None/solver_sampling=None below and an unwrapped node
    # further down -- byte-identical to before this feature existed.
    solver_role_config = config.role("solver")
    solver_group_samples = solver_role_config.samples
    solver_fragment_seed = (
        _solver_fragment_seed(program.program_id) if solver_group_samples > 1 else None
    )
    # E2c (SLURP v2 base program M2): the phase whose visits register ONE
    # committed state instead of one state per contact, or None -- for every
    # samples-1 Solver and every non-M2 config -- in which case none of the
    # E2c branches below is reachable at all.
    grouped_solver_phase_id = (
        solver_role_config.phase_id if solver_group_samples > 1 else None
    )
    # One grouped Solver visit's committed answer, handed over by the grouped
    # node the moment its commit policy has run and consumed by the ``settle``
    # of that visit's LAST sample. At most one is ever in flight: the graph
    # visits the Solver node once per round.
    solver_commit: dict[str, object] = {}
    # The ``(plan, completion, slot_id)`` of the grouped Solver samples of the
    # visit in flight, in sample order, so the visit's ONE wave can name every
    # one of its N contacts. Emptied when that wave is recorded.
    solver_group_contacts: list[tuple[AgentContactPlan, object, int]] = []
    # Item E42 (2026-09-25, Stage-3 family VAR-2): the Solver role's own
    # declared SUPPLY-variant arm group, resolved once. ``None`` for every
    # config written before E42 and every non-VAR-2 config, which makes every
    # branch below unreachable and the composed requests byte-identical.
    supply_variant_group = config.supply_variant_group
    supply_variant_phase_id = config.supply_variant_phase_id
    supply_variant_arms = config.supply_variant_arm_count
    # NX programme E1 (2026-10-09): True when the arm group is the NODE-TEMPLATE
    # kind -- every arm renders the delivering arm's own evidence and differs
    # only in its pinned instruction template. False (and every branch keyed on
    # it unreachable) for every config written before the programme.
    # NX-T R4 (2026-10-18): the node-DECODING kind shares this mode -- every arm
    # renders the delivering arm's own evidence; only the contact's sampling
    # parameters differ (``solver_arm_decoding`` below) and no arm carries a
    # template, so ``declared_template_arms`` is empty for it.
    template_variant_mode = bool(
        supply_variant_group is not None and supply_variant_group.unvaried_evidence
    )
    # ``{arm id: {sampling parameter: value}}`` for the decoding kind's candidate arms,
    # applied at request composition (``MeteredNativeSpeechRequest``); empty for every
    # other config, which leaves every composed request byte-identical.
    solver_arm_decoding = (
        {arm.arm_id: arm.decoding for arm in supply_variant_group.arms if arm.decoding is not None}
        if supply_variant_group is not None and supply_variant_group.is_decoding else {}
    )
    # The ``(plan, completion, slot_id)`` of the arms of the visit in flight, in
    # arm order, so the visit's ONE wave can name every one of its K contacts.
    # Emptied when that wave is recorded.
    supply_variant_contacts: list[tuple[AgentContactPlan, object, int]] = []
    # One record per arm of the visit in flight, keyed by contact id and written
    # by the binding provider -- the only place that knows which value ids an
    # arm's request actually carried, because it is the place that composed
    # them.
    supply_variant_records: dict[str, dict[str, object]] = {}
    # The CUMULATIVE value ids this node's own supply steps have acquired on
    # this row, in acquisition order. A non-delivering arm renders the row's
    # accumulated state with exactly these removed and its own resolved
    # selection put in their place, so its rendering is the same on a first
    # visit and on a REVISE revisit, where
    # ``restrict_repeat_visit_supply`` has already withheld everything visible.
    supply_variant_node_acquired: list[str] = []
    # Each arm's cumulative selection, keyed by arm id. Routers may return only
    # new values on a revision; those increments extend the same arm's history.
    # Resolved ONCE per visit, in ``settle``, against the SAME staged context
    # this row's ordinary ``supply_for_phase`` step is resolved against -- not at
    # binding composition, where the state already carries the node's own
    # increment and a route that excludes what is visible would answer a
    # different question.
    supply_variant_arm_selections: dict[str, tuple[str, ...]] = {}
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md): the Perception role's own declared BRANCH group, resolved
    # once. None for every config written before phase 2 and every
    # non-branched config, which makes every branch below unreachable and
    # the composed requests byte-identical.
    perception_branch_group = config.perception_branch_group
    perception_branch_phase_id = config.perception_branch_phase_id
    # NX programme E1, Perception node (2026-10-10): True when the Perception
    # branch group is the NODE-TEMPLATE kind -- every branch renders the
    # delivering branch's own evidence and differs only in its pinned Perception
    # instruction template. False (everything keyed on it unreachable) for every
    # config written before the programme.
    perception_template_mode = bool(
        perception_branch_group is not None and perception_branch_group.is_template
    )
    # NX-T R1 (2026-10-13): True when the Perception branch group is the per-node THINKING-POLICY kind -- every branch renders
    # the delivering branch's own evidence and instruction and differs only in the thinking decoding of its own contacts
    # (applied at request composition, ``reproduction.ojw.native_request``). False for every config written before NX-T R1.
    perception_thinking_mode = bool(
        perception_branch_group is not None and perception_branch_group.is_thinking
    )
    # Decision 338 (2026-10-19): True when the branch group is the SAMPLING kind -- a branch fans out k Perception samples
    # (merged into its shortlist) and/or n Solver samples (committed by the support policy), every sample a real contact. The
    # ordered contact slots map a node-global contact index to its ``(branch index, sample index)``; both slot lists are None
    # (everything keyed on them unreachable) for every config written before decision 338.
    perception_sampling_mode = bool(
        perception_branch_group is not None and perception_branch_group.is_sampling
    )
    sampling_perception_slots = None
    sampling_solver_slots = None
    if perception_sampling_mode:
        from .supply_variants import perception_contact_slots, solver_contact_slots

        sampling_perception_slots = perception_contact_slots(perception_branch_group)
        sampling_solver_slots = solver_contact_slots(perception_branch_group)
    # Per-branch sampling custody built contact by contact: ``{branch id: [per-sample stream rows]}`` for the Perception
    # samples (with their raw note texts and parsed lists, for the merge) and the Solver samples (with their raw texts, for
    # the commit), and the finished records the final receipt assembly folds into each branch row.
    sampling_perception_streams: dict[str, list[dict[str, object]]] = {}
    sampling_solver_streams: dict[str, list[dict[str, object]]] = {}
    sampling_records: dict[str, dict[str, object]] = {}
    # LEVEL 2 (merge set C item 1): the Solver's own phase id, resolved once,
    # so the Solver-fan-out messages/settle/contact-context seams below can
    # tell "this is the Solver's own phase" from "this is Perception's own
    # phase" without re-deriving it per contact. Every config declares
    # exactly one Solver role, branched or not.
    solver_phase_id = next(
        role.phase_id for role in config.roles if role.role_kind == "solver"
    )
    from .supply_variants import PERCEPTION_BRANCH_LEVEL_SOLVER
    # ``{branch_id: {sample_id: (value_id, ...)}}`` -- the flight-owned,
    # pre-flight seeds ``core.flight.runtime.FlightRuntime.
    # _perception_branch_seeds`` computed once, before any contact. None
    # unless ``perception_branch_group`` is declared.
    perception_branch_seeds = (
        binding.perception_branch_seeds if perception_branch_group is not None
        else None
    )
    # "What to build" item 1: every declared branch's own pinned, loaded,
    # verified contrast-pair table, keyed by branch id
    # (``core.flight.runtime.FlightRuntime._perception_contrast_pairs_for_
    # group``, computed once per flight, before any contact). None unless
    # ``perception_branch_group`` is declared, exactly like
    # ``perception_branch_seeds``.
    perception_contrast_pairs = (
        getattr(binding, "perception_contrast_pairs", None)
        if perception_branch_group is not None else None
    )
    # The ``(plan, completion, slot_id)`` of the branches of the visit in
    # flight, in branch order, so the visit's ONE wave can name every one of
    # its K contacts. Emptied when that wave is recorded. Perception has
    # exactly one visit per row (design section 3, "Branch visits"), so
    # unlike ``supply_variant_contacts`` this list is filled and cleared
    # exactly once per row.
    perception_branch_contacts: list[tuple[AgentContactPlan, object, int]] = []
    # One record per branch of the visit in flight, keyed by contact id and
    # written by the binding provider -- the only place that knows which
    # value ids a branch's request actually carried, because it is the
    # place that composed them.
    perception_branch_records: dict[str, dict[str, object]] = {}
    # LEVEL 2 (merge set C item 1, design section 3 "Level 2"): every
    # branch's own RAW note text, keyed by branch id, populated by
    # ``read_perception_branch_record`` once a branch's note is parsed and
    # kept for the rest of the row (never cleared) -- the Solver's later
    # first visit needs it to render a non-A branch's own history without a
    # second Perception contact. Empty unless ``perception_branch_group`` is
    # declared.
    perception_branch_notes: dict[str, str] = {}
    # The Solver-level twin of ``perception_branch_contacts``/
    # ``perception_branch_records``: the K in-flight Solver branch contacts
    # of the visit (cleared once its wave is sealed), the lightweight
    # pending row per contact id (``perception_branch_solver_messages``
    # writes it, ``read_perception_branch_solver_record`` completes it), and
    # the final per-branch Solver-column custody (``branch_id`` keyed), kept
    # for the whole row so the episode's final receipt assembly can fold it
    # into the ALREADY-SEALED ``perception_branches`` receipt (the Perception
    # visit that owns that receipt has completed long before the Solver's
    # own first visit runs). All three stay empty unless
    # ``perception_branch_group.level`` is 2.
    perception_branch_solver_contacts: list[tuple[AgentContactPlan, object, int]] = []
    perception_branch_solver_pending: dict[str, dict[str, object]] = {}
    perception_branch_solver_records: dict[str, dict[str, object]] = {}
    # LEVEL 2 render-defect fix (2026-10-09): each non-A, non-twin branch's own
    # resolved Solver-phase supply (its cumulative selected value ids), keyed
    # by branch id, resolved ONCE in ``settle`` against the staged context
    # whose sealed Perception state carries THAT branch's note; A's own
    # node-acquired ids (what a branch removes before putting its own in); the
    # rendered-content digest of each Solver contact (messages plus the exposed
    # history, contact-id free), keyed by contact id and then by branch id, for
    # the seal-time "a branch that saw a different note must not replicate A"
    # refusal.
    perception_branch_solver_selections: dict[str, tuple[str, ...]] = {}
    perception_branch_solver_node_acquired: list[str] = []
    perception_branch_solver_render: dict[str, str] = {}
    perception_branch_solver_render_by_branch: dict[str, str] = {}
    pending = {}
    visits = {}
    completed = {}
    role_configs = {role.phase_id: role for role in config.roles}
    # E18 (2026-09-19, owner decisions 43-44): the SIXTH node. Everything
    # below stays None/empty for every config that declares no
    # ``native_episode.acquisition`` -- which is every config written before
    # E18 and every OFF arm -- so an unarmed episode reaches the graph with
    # no acquisition node, ACQUIRE names no registered action, and the E15
    # retained-row disposition is byte-identically what it was.
    acquisition_policy = None
    acquisition_template = None
    acquisition_budget = None
    acquisition_role_config = config.acquisition_role
    #: The typed acquisition states waiting for the settle of the contact that
    #: AUTHORISED them (the Planner's ACQUIRE). At most one is ever in flight:
    #: the graph visits the Acquisition node once per ACQUIRE route.
    acquired_states: list[object] = []
    #: One record per acquisition visit, in visit order, for the receipt.
    acquisition_records: list[dict[str, object]] = []
    #: The model contacts this row's acquisitions have already spent.
    acquisition_contacts = 0
    #: Nodes this episode owns that are not one of the graph's six positions
    #: (today: the re-observation Perception node an acquisition kind (b)
    #: drives). Closed with the rest in the ``finally`` below.
    extra_nodes: list[object] = []
    if acquisition_role_config is not None:
        from .acquisition import (
            AcquisitionBudget,
            AcquisitionError,
            acquired_evidence_template,
            resolve_acquisition_policy,
        )

        if binding.repo_root is None:
            raise RailsRunnerError(
                "the acquisition node requires the repository root its committed "
                "evidence template is read from"
            )
        try:
            acquisition_policy = resolve_acquisition_policy(
                config.acquisition_policy_id
            )
            acquisition_budget = AcquisitionBudget(
                config.max_acquisitions_per_row, config.acquisition_contact_budget,
            ).validate()
        except AcquisitionError as error:
            raise RailsRunnerError(f"acquisition node is invalid: {error}") from error
        acquisition_template = acquired_evidence_template(binding.repo_root)
        role_configs[acquisition_role_config.phase_id] = acquisition_role_config
    context_binding = None
    context_compilations = {}
    proposal_documents, proposal_contacts = {}, {}
    # E8a (2026-09-17, Node Context Policy): the same two-object shape the
    # typed role context uses -- one binding resolved at the Perception visit
    # (the policy's candidate inventory is the Perception schema's own), and
    # one receipt record per contact. With no ``context_policy`` declared, or
    # with its OFF arm, ``config.context_policy_json`` is None and neither is
    # ever touched.
    node_context_binding = None
    node_context_compilations = {}
    # E19 (2026-09-19, owner decision 32): the node-context transform also
    # runs for a config that declares NO policy but DOES arm the Reviewer
    # slot audit. The composed policy is then the key's own bare "raw" arm,
    # so every boundary but the audited draft still emits a row whose
    # rendered bytes ARE the sealed bytes.
    node_context_declared = (
        config.context_policy_json is not None
        or config.reviewer_audit_json is not None
    )
    # E8b (Node Context Policy level L2): one cleaning contact's binding,
    # handed to the SECOND MeteredNativeSpeechRequest below by contact id, and
    # the per-phase invocation counter its contact identity is namespaced by.
    # Both stay empty unless a declared boundary is ``cleaned``.
    cleaning_bindings: dict[str, object] = {}
    cleaning_contact_counts: dict[str, int] = {}
    # E17 (2026-09-19, throughput lever L1): the ordered tool names EVERY
    # contact of this row renders, or None under the default ``per-role``
    # rendering. ``NativeEpisodeConfig.constant_tool_names`` is already
    # validated to be each tool-bearing role's own array, so an armed episode
    # only ever WIDENS the tool-free roles.
    constant_tool_names = config.constant_tool_names
    # One record per contact, in contact order, so a verdict can prove the
    # constancy claim from the sealed receipt alone: the role, the names it
    # may call, the names it rendered, and the sha256 of the rendered
    # ``tool_schemas`` array as the request actually carried it. Collected
    # only when the key is armed -- the OFF arm's receipt must stay
    # byte-identical to the pre-E17 tree's, and the per-role digests are
    # already sealed per request in ``rails.core_client.RequestTiming``.
    tool_rendering_records: list[dict[str, object]] = []
    # Gap G1 plumbing (``rails.solver_citation``): the supplied-id set of
    # every cited-answer contact, keyed by contact id, and the per-row
    # citation records sealed under ``solver_citations``. Both stay empty --
    # and the receipt byte-identical -- unless the ANSWERING phase declares
    # ``saea-solver-cited-answer-v1``.
    citation_contacts: dict[str, dict[str, object]] = {}
    citation_records: list[dict[str, object]] = []

    def context():
        return _runtime_context(
            prepared=state.prepared, snapshot=snapshot, snapshot_sha256=snapshot_sha256,
            query_state=state.query_state, state_store=state.state_store,
            response_sha256s=state.response_sha256s, contact_index=len(state.contacts),
        )

    def base_messages(
        ctx, *, index_role_kind=None, index_sink=None, snapshot_override=None,
        value_renderer_override=None,
    ):
        """Render one contact's two messages.

        Coordinator amendment, 2026-09-28 (the release-swap arm route):
        ``snapshot_override`` is ``None`` for every call site written before
        this fix -- the delivering arm, its twin and every ordinary contact --
        which renders from the row's own composite ``snapshot`` exactly as
        before, byte-identically. A release-swap arm's own visible facets and
        values are looked up in ITS OWN alternate composite snapshot instead
        (``rails.supply_variants.SupplyVariantReleaseSwap``,
        ``core.flight.runtime.FlightRuntime._supply_variant_binding``): the
        one store it repoints renders the alternate's content, and every other
        store renders identical bytes to the base snapshot (the runtime
        already refuses an alternate that moves any other store's pins), so
        using the alternate's own composite snapshot for the WHOLE arm
        rendering is exactly equivalent to swapping just the one store.

        Same-flight instrument, PHASE 2 (merge set C, "What to build" item 2):
        ``value_renderer_override`` is ``None`` for every call site above --
        every one renders with the row's own ``knowledge_value_renderer``,
        byte-identically. A Perception branch's own ``rank-visible-v1``
        presentation renders ONE branch's own view with a value renderer
        ``rank_visible_value_renderer`` builds for that branch alone
        (``_perception_branch_value_renderer``); every other branch, and
        every non-branch contact, is unaffected.
        """

        active_snapshot, active_snapshot_sha256 = (
            (snapshot, snapshot_sha256) if snapshot_override is None
            else (snapshot_override, snapshot_override.content_hash())
        )
        active_value_renderer = (
            knowledge_value_renderer if value_renderer_override is None
            else value_renderer_override
        )
        return _agent_messages(
            adapter=adapter, sample=state.prepared.sample,
            task_contract=state.prepared.task_contract, snapshot=active_snapshot,
            snapshot_sha256=active_snapshot_sha256, query_state=ctx.query_state,
            agent_states=ctx.agent_states, knowledge_value_renderer=active_value_renderer,
            # E21: None for every episode that does not arm
            # ``native_episode.knowledge_index``, which makes every line of
            # the index seam unreachable and the messages byte-identical.
            knowledge_index=knowledge_index,
            index_role_kind=index_role_kind, index_sink=index_sink,
        )

    def supply_variant_messages(ctx, *, request, plan):
        """Item E42: ONE arm's own two messages, plus that arm's receipt row.

        The delivering arm takes ``base_messages(ctx)`` unchanged -- it is the
        ordinary path, so its request bytes are the unvaried construction's by
        construction rather than by claim. That the flight's own independent
        per-arm resolution of it AGREES with this row's ordinary supply step is
        checked in ``settle``, where every arm is resolved, against the same
        staged context, before any arm's request is composed.

        Every other arm is rendered over a QueryState VIEW: the row's
        accumulated ids with this node's own contribution removed and that arm's
        resolved selection in its place. The view is used for rendering only and
        never for custody -- no transition, no wave, no state and no hash edge
        reads it -- so the episode's sealed state chain is exactly the one the
        delivering arm describes, and the non-delivering arms' evidence is
        declared in their own receipt rows instead.
        """

        from .supply_variants import (
            SupplyVariantError, arm_supplied_value_ids, supply_variant_arm_record,
        )

        arm_id = request.context.variant_arm_id
        if supply_variant_group is None or request.role_id != supply_variant_phase_id:
            raise RailsRunnerError(
                "only the registered supply-variant node may bind a variant arm"
            )
        try:
            arm = supply_variant_group.arm(arm_id)
        except SupplyVariantError as error:
            raise RailsRunnerError(str(error)) from error
        arm_index = supply_variant_group.arm_ids.index(arm_id)
        if arm_id not in supply_variant_arm_selections:
            raise RailsRunnerError(
                "a supply-variant arm was contacted before its visit resolved "
                "every arm's own supply"
            )
        selected = supply_variant_arm_selections[arm_id]
        if arm.deliver or arm.replicate_of is not None:
            # Item E42b (owner decision 172, merge set B, Q3 ruling): the
            # twin (``replicate_of`` set) declares no overrides and resolves
            # exactly the delivering arm's ids, so it takes the SAME
            # ``base_messages(ctx)`` the delivering arm does -- byte-identical
            # wire payload (AT2), the delivering arm's own greedy repeat in
            # the same contact batch.
            supplied = tuple(ctx.query_state.retrieved_value_ids)
            messages = base_messages(ctx)
        else:
            try:
                supplied = arm_supplied_value_ids(
                    retrieved_value_ids=ctx.query_state.retrieved_value_ids,
                    node_acquired_value_ids=tuple(supply_variant_node_acquired),
                    arm_selected_value_ids=selected,
                )
            except SupplyVariantError as error:
                raise RailsRunnerError(str(error)) from error
            snapshot_override = None
            if arm.all_release_swaps:
                # Loop item E-T6 (2026-10-11): an arm that swaps several stores
                # renders from ONE composite snapshot built over all of them.
                # Coordinator amendment, 2026-09-28 (the release-swap arm
                # route): this arm renders from its OWN alternate composite
                # snapshot -- the one the flight built over the base's
                # declared ``knowledge_stores.<store>.alternates`` entry for
                # this arm (``core.flight.runtime.FlightRuntime.
                # _supply_variant_binding``) -- not the flight's own
                # ``snapshot``. Bound as an attribute of the flight-owned
                # ``supply_variant_for_phase`` resolver, exactly as other
                # optional flight-owned extras are (e.g.
                # ``supply_for_phase.prefetch_recall``), so a resolver built
                # before this route existed -- or a test double that declares
                # no release-swap arm -- carries none and every arm renders
                # exactly as before.
                release_swap_snapshots = getattr(
                    binding.supply_variant_for_phase, "release_swap_snapshots", {},
                )
                snapshot_override = release_swap_snapshots.get(arm_id)
                if snapshot_override is None:
                    raise RailsRunnerError(
                        "a release-swap supply-variant arm has no resolved "
                        "alternate snapshot bound; the flight-owned resolver "
                        "must carry one alternate composite snapshot per "
                        "release-swap arm id"
                    )
            messages = base_messages(
                replace(
                    ctx,
                    query_state=replace(
                        ctx.query_state, retrieved_value_ids=supplied,
                    ),
                ),
                snapshot_override=snapshot_override,
            )
        try:
            record = supply_variant_arm_record(
                arm=arm, arm_index=arm_index, contact_id=plan.contact_id,
                supplied_value_ids=supplied,
                release_swaps_group=supply_variant_group.uses_release_swaps,
            )
        except SupplyVariantError as error:
            raise RailsRunnerError(str(error)) from error
        existing = supply_variant_records.setdefault(plan.contact_id, record)
        if existing != record:
            raise RailsRunnerError(
                "one supply-variant contact has conflicting arm records"
            )
        return messages

    def template_variant_messages(ctx, *, arm, plan):
        """NX programme E1: ONE template arm's two messages, plus its receipt row.

        Every arm -- the delivering arm, the twin and each template arm --
        renders ``base_messages(ctx)``: the SAME evidence blocks over the SAME
        QueryState, because a template arm varies the node's instruction and
        nothing else. The instruction (and the original query that carries it)
        was set by the caller, before the contact plan was minted. The arm's own
        receipt row records the pinned template it rendered.
        """

        from .supply_variants import SupplyVariantError, supply_variant_arm_record

        messages = base_messages(ctx)
        try:
            record = supply_variant_arm_record(
                arm=arm,
                arm_index=supply_variant_group.arm_ids.index(arm.arm_id),
                contact_id=plan.contact_id,
                supplied_value_ids=tuple(ctx.query_state.retrieved_value_ids),
                template_group=not supply_variant_group.is_decoding,
                decoding_group=supply_variant_group.is_decoding,
            )
        except SupplyVariantError as error:
            raise RailsRunnerError(str(error)) from error
        existing = supply_variant_records.setdefault(plan.contact_id, record)
        if existing != record:
            raise RailsRunnerError(
                "one template-variant contact has conflicting arm records"
            )
        return messages

    def perception_branch_messages(ctx, *, request, plan):
        """Same-flight instrument, PHASE 2: ONE Perception branch's own two
        messages, plus a LIGHTWEIGHT pending record for its receipt row.

        :func:`supply_variant_messages`'s own twin, with the one mechanical
        difference design section 3 states: a branch's supply is never
        resolved live against this row's accumulated state (there is none to
        resolve against -- Perception is the program's FIRST phase); it is
        the branch's own PRE-FLIGHT seed
        (``core.flight.runtime.FlightRuntime._perception_branch_seeds``),
        keyed by this row's own sample id.

        Branch A and its twin T take ``base_messages(ctx)`` UNCHANGED -- A is
        the ordinary path (the cell's own request, override-free) and T
        repeats it byte for byte in the same batch (AT-P1, AT-P2). Every
        other branch renders over a QueryState VIEW whose
        ``retrieved_value_ids`` are its own seed for this sample; the view is
        used for rendering only and never for custody, exactly as a
        non-delivering supply-variant arm's is.

        Unlike ``supply_variant_arm_record`` (built here, in full, because it
        needs no response text), a branch's full
        ``rails.supply_variants.perception_branch_record`` needs the
        RESPONSE (its note text, hence ``note_sha256``/``note_parse_status``/
        ``candidate_intent_ids``), which is not known until the contact
        completes. So only a lightweight pending row -- the branch identity,
        the value ids THIS request actually carried, and this branch's own
        presentation outcome (design section 3, "What to build" item 2) --
        is recorded here, keyed by contact id;
        :func:`read_perception_branch_record` completes it once the response
        is known.

        Same-flight instrument, PHASE 2 ("What to build" items 2 and 3): a
        non-A, non-T branch's own ``presentation_id`` or ``min_candidates``
        axis is rendered here, over the SAME QueryState view its seed is
        rendered from -- ``rank-visible-v1`` as a per-branch value-renderer
        override (:func:`_perception_branch_value_renderer`), ``top2-
        contrast-v1`` and ``min_candidates`` as one extra content item each,
        appended after the value items (:func:`_render_perception_branch_
        presentation`, :func:`_perception_branch_min_candidates_sentence`).
        A and T carry neither axis (parse-time refusal), so neither ever
        reaches this branch: their messages stay exactly
        ``base_messages(ctx)``.
        """

        from .supply_variants import PerceptionBranchError

        branch_id = request.context.perception_branch_id
        if (
            perception_branch_group is None
            or request.role_id != perception_branch_phase_id
        ):
            raise RailsRunnerError(
                "only the registered perception-branch node may bind a branch"
            )
        try:
            branch = perception_branch_group.branch(branch_id)
        except PerceptionBranchError as error:
            raise RailsRunnerError(str(error)) from error
        branch_index = perception_branch_group.branch_ids.index(branch_id)
        extra_item = None
        presentation_skip_reason = None
        if (
            branch.deliver or branch.is_twin or branch.instruction_template is not None or branch.thinking_policy is not None
            or perception_sampling_mode
        ):
            # NX programme E1, Perception node: a template branch varies the
            # instruction (set by the caller before the contact plan is minted)
            # and nothing else, so it renders the SAME evidence blocks over the
            # SAME QueryState as A: no seed, no presentation, no contract item.
            # AT-P1 / AT-P2: A is the cell's own request, override-free; the
            # twin (replicate_of A) resolves exactly A's ids and takes the
            # SAME base_messages(ctx) A does -- byte-identical wire payload,
            # A's own greedy repeat in the same branch batch.
            # Evidence-consumption module, ruling R3: the config loader admits
            # an axis on A only for a module's ADMITTED delivered policy
            # (``parse_perception_branches(..., delivering_axes_admitted=)``),
            # and no component is admitted yet. The wire rendering of A's
            # axes and their seal custody (``validate_perception_branch_
            # receipt``: "A and T must declare no axis") land together with
            # the first admission; until then an axis on A is refused here,
            # never silently dropped.
            delivering_branch = perception_branch_group.delivering_branch
            if (
                delivering_branch.presentation_id is not None
                or delivering_branch.min_candidates is not None
            ):
                raise RailsRunnerError(
                    "the delivering perception branch (A) carries a module-admitted "
                    "axis, whose wire rendering and seal custody are not built yet"
                )
            supplied = tuple(ctx.query_state.retrieved_value_ids)
            messages = base_messages(ctx)
        else:
            seed = (
                perception_branch_seeds.get(branch_id, {})
                if perception_branch_seeds else {}
            )
            supplied = tuple(seed.get(ctx.sample_id, ()))
            renderer_override = _perception_branch_value_renderer(
                branch=branch, snapshot_sha256=snapshot_sha256,
                supplied_value_ids=supplied,
            )
            messages = base_messages(
                replace(
                    ctx,
                    query_state=replace(ctx.query_state, retrieved_value_ids=supplied),
                ),
                value_renderer_override=renderer_override,
            )
            branch_contrast_pairs = (
                perception_contrast_pairs.get(branch_id)
                if perception_contrast_pairs else None
            )
            extra_item, presentation_skip_reason = _render_perception_branch_presentation(
                branch=branch, supplied_value_ids=supplied,
                contrast_pairs=branch_contrast_pairs,
                decision_candidates=(
                    None if carrier_hooks is None else carrier_hooks.decision_candidates
                ),
            )
            contract_item = _perception_branch_min_candidates_sentence(
                branch,
                max_candidates=(
                    None if carrier_hooks is None or carrier_hooks.max_decision_candidates is None
                    else carrier_hooks.max_decision_candidates()
                ),
            )
            extra_items = [item for item in (extra_item, contract_item) if item is not None]
            if extra_items:
                user_message = messages[1]
                messages = (
                    messages[0],
                    {**user_message, "content": [*user_message["content"], *extra_items]},
                )
        contrast_block_sha256 = (
            None if extra_item is None
            else hashlib.sha256(extra_item["text"].encode("utf-8")).hexdigest()
        )
        record = {
            "branch_id": branch_id, "branch_index": branch_index,
            "supplied_value_ids": supplied,
            "presentation_skip_reason": presentation_skip_reason,
            "contrast_block_sha256": contrast_block_sha256,
        }
        if perception_sampling_mode:
            # Decision 338: which sample of the branch's Perception fan-out this contact is (None for a branch that
            # declares no ``perception_samples`` axis). Added only for a sampling group, so every other group's pending row
            # is unchanged.
            record["sample_index"] = request.context.sample_index
        existing = perception_branch_records.setdefault(plan.contact_id, record)
        if existing != record:
            raise RailsRunnerError(
                "one perception-branch contact has conflicting branch records"
            )
        return messages

    def _perception_branch_solver_view(ctx, request):
        """LEVEL 2: the context ONE Perception branch's Solver contact is
        RENDERED from -- the whole of it, not just the messages.

        A and the twin take ``ctx`` unchanged. Every other branch gets a VIEW
        in which (1) the sealed Perception state's content is that branch's
        own note, and (2) the QueryState's ``retrieved_value_ids`` carry that
        branch's own Solver-phase supply (resolved in ``settle`` from the
        branch's note) in place of A's. Everything downstream of the messages
        -- the exposed history (``agent_state``), the role/node context
        compilers and the candidate-proposal block -- must read THIS view, not
        ``ctx``; that is the 2026-10-09 render defect (they read ``ctx`` and
        so every branch Solver column replicated A's request).
        The view is used for rendering only and never for custody.
        """

        from .supply_variants import (
            PERCEPTION_BRANCH_LEVEL_SOLVER, PerceptionBranchError,
            SupplyVariantError, arm_supplied_value_ids,
        )

        branch_id = request.context.perception_branch_id
        if (
            branch_id is None or perception_branch_group is None
            or perception_branch_group.level != PERCEPTION_BRANCH_LEVEL_SOLVER
            or request.role_id != solver_phase_id
        ):
            return ctx
        try:
            branch = perception_branch_group.branch(branch_id)
        except PerceptionBranchError as error:
            raise RailsRunnerError(str(error)) from error
        if branch.deliver or branch.is_twin:
            return ctx
        note_text = perception_branch_notes.get(branch_id)
        if not isinstance(note_text, str) or not note_text:
            raise RailsRunnerError(
                f"perception branch {branch_id!r} has no sealed note to "
                "render into the Solver's history"
            )
        query_state = ctx.query_state
        if binding.perception_branch_solver_supply is not None:
            if branch_id not in perception_branch_solver_selections:
                raise RailsRunnerError(
                    f"perception branch {branch_id!r} was contacted before its "
                    "Solver-phase supply was resolved from its own note"
                )
            try:
                supplied = arm_supplied_value_ids(
                    retrieved_value_ids=ctx.query_state.retrieved_value_ids,
                    node_acquired_value_ids=tuple(perception_branch_solver_node_acquired),
                    arm_selected_value_ids=perception_branch_solver_selections[branch_id],
                )
            except SupplyVariantError as error:
                raise RailsRunnerError(str(error)) from error
            query_state = replace(query_state, retrieved_value_ids=supplied)
        return replace(
            ctx,
            query_state=query_state,
            agent_states=_perception_note_view(ctx.agent_states, note_text=note_text),
        )

    def _perception_note_view(agent_states, *, note_text):
        """LEVEL 2: a VIEW of ``agent_states`` with the sealed Perception
        state's own ``content`` (A's note) replaced by ``note_text`` (a
        non-A branch's own note) -- used for rendering only, exactly as
        ``perception_branch_messages`` swaps ``retrieved_value_ids`` for a
        view rather than for custody. Every other state (the speech query,
        any earlier phase) is untouched.
        """

        expected_kind = f"phase:{perception_branch_phase_id}"
        matches = [
            index for index, state in enumerate(agent_states)
            if getattr(state, "state_kind", None) == expected_kind
        ]
        if len(matches) != 1:
            raise RailsRunnerError(
                "a perception-branch Solver view requires exactly one sealed "
                "Perception state to replace"
            )
        swapped = list(agent_states)
        swapped[matches[0]] = perception_note_view_state(
            swapped[matches[0]], note_text=note_text,
        )
        return tuple(swapped)

    def _rendered_candidate_value_ids(messages):
        """LEVEL 2: the ``value`` evidence ids THIS rendering actually
        carried -- ``perception_branch_record``'s own
        ``candidate_supply_value_ids`` field (design section 3, "Receipt"),
        read directly off the composed user message rather than re-derived
        from a separate candidate-supply resolution, so it can never drift
        from what the branch's own contact actually rendered.
        """

        user_message = messages[1] if len(messages) > 1 else None
        content = user_message.get("content") if isinstance(user_message, Mapping) else None
        if not isinstance(content, list):
            return ()
        return tuple(
            item["evidence_id"] for item in content
            if isinstance(item, Mapping)
            and item.get("knowledge_role") == "value"
            and isinstance(item.get("evidence_id"), str)
        )

    def perception_branch_solver_messages(ctx, *, request, plan):
        """LEVEL 2 (merge set C item 1, design section 3, "Level 2"): ONE
        Perception branch's own Solver contact -- structurally
        ``perception_branch_messages``'s twin, over the Solver's own phase
        instead of Perception's.

        A and T take ``base_messages(ctx)`` UNCHANGED: A is the ordinary
        path (this visit's own real Solver contact, spending no NEW request
        beyond what an unbranched episode would make) and T repeats it byte
        for byte in the same batch, reading the SAME already-sealed
        Perception state A's own note sealed. Every other branch renders
        over an ``agent_states`` VIEW whose sealed Perception state is
        replaced by that branch's OWN note (``perception_branch_notes``,
        populated by ``read_perception_branch_record`` at the earlier
        Perception visit) -- there is no supply to swap here (the Solver's
        own candidate construction is a pure function of the ``phase:
        <perception>`` state this view replaces, so it re-resolves on its
        own); the view is used for rendering only and never for custody.
        """

        from .supply_variants import (
            PERCEPTION_BRANCH_LEVEL_SOLVER, PerceptionBranchError,
        )

        branch_id = request.context.perception_branch_id
        if (
            perception_branch_group is None
            or perception_branch_group.level != PERCEPTION_BRANCH_LEVEL_SOLVER
            or request.role_id != solver_phase_id
        ):
            raise RailsRunnerError(
                "only the registered perception-branch Solver fan-out may "
                "bind a branch at the Solver's own phase"
            )
        try:
            branch = perception_branch_group.branch(branch_id)
        except PerceptionBranchError as error:
            raise RailsRunnerError(str(error)) from error
        # The WHOLE contact context is the branch's view (see
        # ``_perception_branch_solver_view``): A and the twin get ``ctx`` back
        # unchanged, so their messages stay ``base_messages(ctx)``.
        messages = base_messages(_perception_branch_solver_view(ctx, request))
        record = {
            "branch_id": branch_id,
            "candidate_supply_value_ids": _rendered_candidate_value_ids(messages),
        }
        if perception_sampling_mode:
            # Decision 338: which sample of the branch's Solver fan-out this contact is (None outside a ``solver_samples``
            # branch). Added only for a sampling group, so every other group's pending row is unchanged.
            record["sample_index"] = request.context.sample_index
        existing = perception_branch_solver_pending.setdefault(plan.contact_id, record)
        if existing != record:
            raise RailsRunnerError(
                "one perception-branch Solver contact has conflicting branch records"
            )
        return messages

    def settle(*, tool_step=None, rejected_steps=(), next_phase=None):
        if not pending:
            return
        completion, source, before, plan, slot_id = (
            pending[name] for name in ("completion", "source", "context", "plan", "slot_id")
        )
        if completion.tool_calls and tool_step is None and not rejected_steps:
            raise RailsRunnerError("native tool request has no source-bound observation")
        # E2c (SLURP v2 base program M2): module M2 is sample-and-aggregate
        # COMMIT, so the committed answer IS the Solver's draft. One grouped
        # Solver visit therefore takes ONE step -- one organize transition
        # registering ONE phase state, the committed (aggregated) answer, in
        # the SAME wire form a samples-1 (anchor) Solver state has -- and the
        # Reviewer and the Planner read one draft exactly as they do on the
        # anchor. The N raw samples stay in custody: each is its own
        # AgentContactRecord, its own MODEL_REQUEST/MODEL_RESPONSE/COST trace
        # record and its own metered cost, all N appear in the visit's ONE
        # wave as an ``action_alternatives`` batch with their own response
        # digests, and their seeds, decoding parameters and parsed answers
        # travel the delivered role result's ``solver_group``. Because the
        # group takes no step between its samples, the N sibling requests
        # also see the SAME QueryState and the SAME exposed history -- they
        # are independent draws of one draft, not a chain. The committed
        # state is sealed as a VIEW of the group's last sample
        # (``seal_phase_response_state``'s own state_content /
        # raw_response_text seam), so ``source_response_sha256`` still binds
        # real model bytes from the same contact its state id is namespaced
        # by. With ``samples`` absent or 1, ``grouped_solver_phase_id`` is
        # None and none of this is reachable.
        contact_record, response_record, slot_ids = plan, completion.text, (slot_id,)
        if pending["phase_id"] == grouped_solver_phase_id:
            sample_index = pending["sample_index"]
            if (
                isinstance(sample_index, bool)
                or not isinstance(sample_index, int)
                or not 0 <= sample_index < solver_group_samples
                or sample_index != len(solver_group_contacts)
            ):
                raise RailsRunnerError(
                    "grouped Solver samples settled out of their registered order"
                )
            if tool_step is not None or rejected_steps:
                raise RailsRunnerError("a grouped Solver contact cannot execute a tool")
            solver_group_contacts.append((plan, completion, slot_id))
            if sample_index < solver_group_samples - 1:
                pending.clear()
                return
            committed = solver_commit.pop("actor_output", None)
            if not isinstance(committed, str) or not committed:
                raise RailsRunnerError(
                    "grouped Solver visit settled without its committed answer"
                )
            source = seal_phase_response_state(
                phase_name=pending["phase_id"], sample_id=before.sample_id,
                state_content=committed, raw_response_text=completion.text,
                source_query_state_sha256=before.query_state.content_hash(),
                producer_policy_id=program.program_id,
                state_namespace=plan.contact_id,
            )
            contact_record = AgentContactBatch(
                batch_id=f"{solver_group_contacts[0][0].contact_id}:group",
                query_state_sha256=before.query_state.content_hash(),
                contacts=tuple(item[0] for item in solver_group_contacts),
                fanout_semantics="action_alternatives",
            ).validate()
            response_record = tuple(item[1].text for item in solver_group_contacts)
            slot_ids = tuple(item[2] for item in solver_group_contacts)
            solver_group_contacts.clear()
        if (
            pending["phase_id"] == supply_variant_phase_id
            and pending["variant_arm_id"] is not None
        ):
            # Item E42: the arm group. Structurally the grouped sampler's twin
            # just above, with the ONE difference that makes this form cheaper
            # to audit: the DELIVERING arm is the LAST arm and carries no
            # overrides, so its own ``source`` -- the ordinary seal
            # ``capture_completion`` already computed from its own completion --
            # is the state this visit registers. There is no aggregate, no
            # committed-state view and no delivery-binding exception; arms
            # 0..K-2 simply register no state at all, exactly as samples
            # 0..N-2 do. Because the group takes no step between arms, all K
            # bind the SAME QueryState and the SAME exposed history: they are
            # independent constructions of one draft, not a chain.
            #
            # Item E42b (owner decision 172, merge set B): this branch is
            # reached only for a REAL arm contact -- ``variant_arm_id`` is
            # ``None`` for every contact of every OTHER visit under
            # ``arm_visits: "first"`` (``contact_context`` above), which then
            # falls through to the ordinary single-contact path below,
            # byte-identical to an unarmed Solver visit.
            arm_id = pending["variant_arm_id"]
            expected = supply_variant_group.arm_ids[len(supply_variant_contacts)] if (
                len(supply_variant_contacts) < supply_variant_arms
            ) else None
            if arm_id is None or arm_id != expected:
                raise RailsRunnerError(
                    "supply-variant arms settled out of their declared order"
                )
            if tool_step is not None or rejected_steps:
                raise RailsRunnerError(
                    "a supply-variant arm contact cannot execute a tool"
                )
            supply_variant_contacts.append((plan, completion, slot_id))
            if len(supply_variant_contacts) < supply_variant_arms:
                pending.clear()
                return
            # Item E42b: a NEW, explicit assertion beside the structural
            # guarantee above ("arms 0..K-2 register no state at all") -- the
            # state this visit is about to register, which Reviewer and
            # Planner read from, is bound to the DELIVERING arm's own contact
            # and response alone.
            if arm_id != supply_variant_group.delivered_arm.arm_id:
                raise RailsRunnerError(
                    "a supply-variant visit registered downstream state from a "
                    "non-delivering arm; only the delivering arm's response "
                    "may reach the Reviewer or the Planner"
                )
            contact_record = AgentContactBatch(
                batch_id=f"{supply_variant_contacts[0][0].contact_id}:variants",
                query_state_sha256=before.query_state.content_hash(),
                contacts=tuple(item[0] for item in supply_variant_contacts),
                fanout_semantics="action_alternatives",
            ).validate()
            response_record = tuple(item[1].text for item in supply_variant_contacts)
            slot_ids = tuple(item[2] for item in supply_variant_contacts)
            supply_variant_contacts.clear()
        if (
            pending["phase_id"] == perception_branch_phase_id
            and pending["perception_branch_id"] is not None
        ):
            # Same-flight instrument, PHASE 2 (merge set C, design section 3,
            # "Messages and settle"): the branch group. Structurally the
            # supply-variant arm group's twin just above, with the ONE
            # difference that IS the whole point of the mechanism: a
            # NON-delivering branch's completion registers NO node state at
            # all -- the delivering branch (A) is the LAST branch and
            # carries no overrides, so its own ``source`` (the ordinary seal
            # ``capture_completion`` already computed from its own
            # completion) is the state this visit registers. Because the
            # group takes no step between branches, all K bind the SAME
            # QueryState and the SAME exposed history: they are independent
            # constructions of one draft, not a chain. Perception has
            # exactly one visit per row (design section 3, "Branch visits"),
            # so this block runs at most once per row.
            branch_id = pending["perception_branch_id"]
            # Decision 338: a sampling group's visit has one contact per SLOT (k for a perception_samples branch), so the
            # expected branch -- and sample -- of the next settled contact comes from the slot list; every other group has
            # one contact per branch.
            perception_slot_total = (
                len(sampling_perception_slots) if sampling_perception_slots is not None
                else perception_branch_group.branch_count
            )
            if len(perception_branch_contacts) < perception_slot_total:
                if sampling_perception_slots is not None:
                    slot_branch, slot_sample = sampling_perception_slots[len(perception_branch_contacts)]
                    expected = perception_branch_group.branch_ids[slot_branch]
                    if pending.get("sample_index") != slot_sample:
                        raise RailsRunnerError(
                            "perception-branch samples settled out of their declared order"
                        )
                else:
                    expected = perception_branch_group.branch_ids[len(perception_branch_contacts)]
            else:
                expected = None
            if branch_id is None or branch_id != expected:
                raise RailsRunnerError(
                    "perception branches settled out of their declared order"
                )
            if tool_step is not None or rejected_steps:
                raise RailsRunnerError(
                    "a perception-branch contact cannot execute a tool"
                )
            perception_branch_contacts.append((plan, completion, slot_id))
            if len(perception_branch_contacts) < perception_slot_total:
                pending.clear()
                return
            # A NEW, explicit assertion beside the structural guarantee
            # above ("a non-delivering branch registers no state at all")
            # -- the state this visit is about to register, which the
            # Solver, Reviewer and Planner read from, is bound to branch
            # A's own contact and response alone.
            if branch_id != perception_branch_group.delivering_branch.branch_id:
                raise RailsRunnerError(
                    "a perception-branch visit registered downstream state "
                    "from a non-delivering branch; only branch A's response "
                    "may reach the Solver, Reviewer or Planner"
                )
            contact_record = AgentContactBatch(
                batch_id=f"{perception_branch_contacts[0][0].contact_id}:branches",
                query_state_sha256=before.query_state.content_hash(),
                contacts=tuple(item[0] for item in perception_branch_contacts),
                fanout_semantics="action_alternatives",
            ).validate()
            response_record = tuple(item[1].text for item in perception_branch_contacts)
            slot_ids = tuple(item[2] for item in perception_branch_contacts)
            perception_branch_contacts.clear()
        if (
            pending["phase_id"] == solver_phase_id
            and pending["perception_branch_id"] is not None
        ):
            # LEVEL 2 (merge set C item 1, design section 3, "Level 2"): the
            # Solver's own first-visit branch fan-out -- structurally the
            # Perception branch group's own settle block just above, over the
            # Solver's phase instead: EVERY declared branch (A included)
            # carries ``perception_branch_id`` here (``contact_context``
            # below marks branch A's own contact too, exactly as the K - 1
            # non-A branches are, so A's contact is a REAL, marked contact
            # whose request bytes just happen to equal the unbranched
            # episode's own -- the same convention the Solver arm-group
            # route already uses for its own delivering arm). A is the LAST
            # declared branch, so its own contact is the one that reaches
            # this ``if`` block's tail and falls through to register state,
            # exactly as an ordinary Solver visit's single contact would.
            branch_id = pending["perception_branch_id"]
            solver_slot_total = (
                len(sampling_solver_slots) if sampling_solver_slots is not None
                else perception_branch_group.branch_count
            )
            if len(perception_branch_solver_contacts) < solver_slot_total:
                if sampling_solver_slots is not None:
                    slot_branch, slot_sample = sampling_solver_slots[len(perception_branch_solver_contacts)]
                    expected = perception_branch_group.branch_ids[slot_branch]
                    if pending.get("sample_index") != slot_sample:
                        raise RailsRunnerError(
                            "perception-branch Solver samples settled out of their declared order"
                        )
                else:
                    expected = perception_branch_group.branch_ids[len(perception_branch_solver_contacts)]
            else:
                expected = None
            if branch_id is None or branch_id != expected:
                raise RailsRunnerError(
                    "perception-branch Solver contacts settled out of their "
                    "declared order"
                )
            if tool_step is not None or rejected_steps:
                raise RailsRunnerError(
                    "a perception-branch Solver contact cannot execute a tool"
                )
            perception_branch_solver_contacts.append((plan, completion, slot_id))
            if len(perception_branch_solver_contacts) < solver_slot_total:
                pending.clear()
                return
            if branch_id != perception_branch_group.delivering_branch.branch_id:
                raise RailsRunnerError(
                    "a perception-branch Solver visit registered downstream "
                    "state from a non-delivering branch; only branch A's own "
                    "answer may reach the Reviewer or the Planner"
                )
            contact_record = AgentContactBatch(
                batch_id=f"{perception_branch_solver_contacts[0][0].contact_id}:branch-solver",
                query_state_sha256=before.query_state.content_hash(),
                contacts=tuple(item[0] for item in perception_branch_solver_contacts),
                fanout_semantics="action_alternatives",
            ).validate()
            response_record = tuple(item[1].text for item in perception_branch_solver_contacts)
            slot_ids = tuple(item[2] for item in perception_branch_solver_contacts)
            perception_branch_solver_contacts.clear()
        staged = replace(
            before, agent_states=before.agent_states + (source,),
            prior_response_sha256s=before.prior_response_sha256s + (completion.response_text_sha256,),
            core_completions=(completion,),
        )
        supply = None if tool_step is None else tool_step.supply
        if supply is None and next_phase is not None and binding.supply_for_phase is not None:
            supply = binding.supply_for_phase(next_phase, staged)
            if supply is not None and rank_order_stores:
                # Cell RANKVIS: re-order each named store's selection by
                # retrieval rank BEFORE the repeat-visit restriction and the
                # acquire transition, so the transition's ``new_value_ids`` are
                # exactly the re-ordered decision's.
                supply = order_supply_by_retrieval_rank(supply, snapshot, rank_order_stores)
        if supply is not None and next_phase is not None and program.phase(next_phase).knowledge != "supplied":
            raise RailsRunnerError("native knowledge supply requires a supplied destination")
        if supply is not None and next_phase is not None:
            # E3c: the Planner's REVISE route re-enters the Solver, and a
            # prepared phase supply is a pure function of (phase, sample), so
            # the SAME decision comes back for a phase whose values already
            # ride the accumulated QueryState. Acquire only what is new; the
            # first visit of every phase is returned unchanged.
            supply = restrict_repeat_visit_supply(supply, before, phase_name=next_phase)
        if (
            next_phase is not None and next_phase == solver_phase_id
            and perception_branch_group is not None
            and perception_branch_group.level == PERCEPTION_BRANCH_LEVEL_SOLVER
            and binding.perception_branch_solver_supply is not None
            and not perception_branch_solver_selections
        ):
            # LEVEL 2 render-defect fix (2026-10-09): the first Solver visit's
            # branch fan-out. Every non-A, non-twin branch's own Solver-phase
            # supply is resolved HERE, against the SAME staged context this
            # row's ordinary supply step was -- except that the sealed
            # Perception state carries THAT branch's own note -- so a branch's
            # candidate supply is a function of its own note, exactly as A's is
            # a function of A's. (A and the twin render A's supply.)
            perception_branch_solver_node_acquired.extend(
                () if supply is None else supply.fusion_decision.selected_value_ids
            )
            for branch in perception_branch_group.branches:
                if branch.deliver or branch.is_twin:
                    continue
                note_text = perception_branch_notes.get(branch.branch_id)
                if not isinstance(note_text, str) or not note_text:
                    raise RailsRunnerError(
                        f"perception branch {branch.branch_id!r} has no sealed note "
                        "to resolve its Solver-phase supply from"
                    )
                branch_source = perception_note_view_state(source, note_text=note_text)
                branch_staged = replace(
                    staged, agent_states=before.agent_states + (branch_source,),
                )
                branch_supply = binding.perception_branch_solver_supply(
                    branch_id=branch.branch_id, phase_id=next_phase,
                    context=branch_staged,
                )
                perception_branch_solver_selections[branch.branch_id] = (
                    () if branch_supply is None
                    else tuple(branch_supply.fusion_decision.selected_value_ids)
                )
        if (
            next_phase is not None and next_phase == supply_variant_phase_id
            and not template_variant_mode
        ):
            # Item E42, and THE reason an arm's supply is resolved here rather
            # than at binding composition: every arm is resolved against the
            # SAME ``staged`` context this row's ordinary supply step was, so
            # every arm answers the same question the delivering arm answers.
            if supply is not None:
                # What THIS node's own supply steps have put on the row,
                # cumulatively. It is the set a non-delivering arm replaces, and
                # the set the delivering arm's own resolved selection is checked
                # against below.
                supply_variant_node_acquired.extend(
                    supply.fusion_decision.selected_value_ids
                )
            from .supply_variants import accumulate_arm_selection

            for arm in supply_variant_group.arms:
                # ``staged``, not ``before``: a candidate-bound route reads the
                # sealed state of its candidate phase off the context it is
                # handed (``rails.knowledge_stores``' candidate/delta routes), so
                # resolving an arm against the PRE-seal context would hide the
                # Perception draft the delivering arm's own supply was resolved
                # against and make the two answer different questions.
                arm_supply = binding.supply_variant_for_phase(
                    arm_id=arm.arm_id, phase_id=next_phase, context=staged,
                )
                selected = (
                    () if arm_supply is None
                    else tuple(arm_supply.fusion_decision.selected_value_ids)
                )
                selected = accumulate_arm_selection(
                    supply_variant_arm_selections.get(arm.arm_id, ()), selected,
                )
                supply_variant_arm_selections[arm.arm_id] = selected
                if arm.deliver and selected != tuple(supply_variant_node_acquired):
                    # The delivering arm declares NO overrides, so the flight's
                    # own per-arm resolution -- a router built independently over
                    # the same released, pinned stores -- must reproduce exactly
                    # what this row's ordinary supply step acquired at this node.
                    # Checked live, fail-closed, before any arm's request is
                    # composed: this is the non-circular form of "the delivered
                    # request is the unvaried construction's request", and it is
                    # what lets the delivered number be read as the within-flight
                    # baseline of every other arm.
                    raise RailsRunnerError(
                        "the delivering supply-variant arm resolves a different "
                        "supply than this row's own supply step acquired at this "
                        "node; the delivered request would not be the unvaried "
                        "construction's request"
                    )
        if rejected_steps and (tool_step is not None or any(step.supply is not None for step in rejected_steps)):
            raise RailsRunnerError("rejected batch cannot execute a tool or introduce supply")
        added = (source,) + (() if tool_step is None else (tool_step.state,))
        added += tuple(step.state for step in rejected_steps)
        if acquired_states:
            # E18: a model-free acquisition makes no contact of its own, so
            # its typed state rides the settle of the contact that AUTHORISED
            # it -- the Planner's ACQUIRE -- exactly as a tool observation
            # rides the settle of the contact that called the tool. It was
            # sealed against this very context, so every binding
            # ``_validate_new_agent_states`` checks holds by construction.
            added += tuple(acquired_states)
            acquired_states.clear()
        next_state, transition = advance_phase_response_state(
            context=before, added_states=added,
            action_target_ref=f"{program.program_id}:{pending['phase_id']}:{plan.contact_id}",
            supply=supply,
        )
        advance = AgentLoopAdvance(
            transition=transition, next_query_state=next_state,
            new_agent_states=added, next_contact=None,
            rank_result=None if supply is None else supply.rank_result,
            fusion_decision=None if supply is None else supply.fusion_decision,
        )
        _validate_agent_knowledge_decision(
            snapshot=snapshot, snapshot_sha256=snapshot_sha256,
            query_state=before.query_state, advance=advance,
        )
        assert_agent_step_binding(
            snapshot=snapshot, snapshot_sha256=snapshot_sha256,
            prior_query_state=before.query_state, next_query_state=next_state,
            transition=transition,
            origin_speech_packet=(
                state.prepared.initial_query_state.speech_packet_id,
                state.prepared.initial_query_state.speech_packet_sha256,
            ),
        )
        _validate_new_agent_states(
            artifacts=added, transition=transition, prior_query_state=before.query_state,
            response_sha256=completion.response_text_sha256, snapshot=snapshot,
            existing_state_ids=set(state.state_store),
        )
        state.waves.append(_agent_wave_record(
            wave_index=len(state.waves), contact=contact_record,
            response=response_record, slot_ids=slot_ids,
            query_state=before.query_state, advance=advance,
        ))
        state.transitions.append(transition)
        state.state_store.update((artifact.state_id, artifact) for artifact in added)
        state.query_state = next_state
        pending.clear()

    def role_input(phase_id, episode_state):
        nonlocal context_binding, node_context_binding
        settle(next_phase=phase_id)
        ctx = context()
        previous = ctx.agent_states[-1] if ctx.agent_states else None
        material = binding.material_for_phase(
            phase_id, ctx, {} if previous is None else {ctx.sample_id: previous},
        )
        if not isinstance(material, PhaseMaterial):
            raise RailsRunnerError("native role material must be PhaseMaterial")
        material.validate()
        if config.role_context_json is not None and phase_id == config.role("perception").phase_id:
            from .role_context_binding import build_role_context_binding

            prepared_context = build_role_context_binding(
                config.role_context_json, material.response_format,
            )
            if context_binding is not None and (
                context_binding.source_format_sha256 != prepared_context.source_format_sha256
                or context_binding.config_sha256 != prepared_context.config_sha256
            ):
                raise RailsRunnerError("role context source schema changed inside the episode")
            context_binding = prepared_context
        if node_context_declared and phase_id == config.role("perception").phase_id:
            from .node_context_binding import build_node_context_policy_binding

            if binding.repo_root is None:
                raise RailsRunnerError(
                    "node context policy requires the repository root its committed "
                    "templates are read from"
                )
            prepared_policy = build_node_context_policy_binding(
                config.context_policy_json, material.response_format, binding.repo_root,
                # E12: the armed Reviewer slot-audit block, or None -- in
                # which case this call is byte-identical to its pre-E12 self.
                config.reviewer_audit_json,
                # E14: the armed Solver scenario-hints block and the data
                # root its released view is read from; both None leaves this
                # call byte-identical to its pre-E14 self.
                config.solver_hints_json,
                binding.data_root,
            )
            if node_context_binding is not None and (
                node_context_binding.source_format_sha256
                != prepared_policy.source_format_sha256
                or node_context_binding.config_sha256 != prepared_policy.config_sha256
            ):
                raise RailsRunnerError(
                    "node context policy source schema changed inside the episode"
                )
            node_context_binding = prepared_policy
        revision_index = episode_state["revision_count"]
        limits = {
            "revision_index": revision_index,
            "max_revisions": config.max_revisions,
            "remaining_model_contacts": config.max_contacts - state.scheduled_contacts,
            "role_max_iterations": role_configs[phase_id].max_iterations,
            "available_planner_actions": [
                config.actions[0],
                *([config.actions[1]] if revision_index < config.max_revisions else []),
            ],
        }
        if config.refresh_action is not None:
            remaining_refreshes = (
                config.max_candidate_refreshes - episode_state.get("candidate_refresh_count", 0)
            )
            limits["remaining_candidate_refreshes"] = remaining_refreshes
            if remaining_refreshes > 0 and revision_index < config.max_revisions:
                limits["available_planner_actions"].append(config.refresh_action)
        # E18: ACQUIRE is advertised exactly while it can be EXECUTED -- an
        # acquisition node exists, the row's acquisition allowance is not
        # spent, and a revision remains for the ACQUIRE to consume. Unarmed,
        # this block is skipped entirely and the advertised set is its
        # pre-E18 self.
        remaining_acquisitions = 0
        if acquisition_policy is not None:
            remaining_acquisitions = (
                config.max_acquisitions_per_row - len(acquisition_records)
            )
            limits["remaining_acquisitions"] = remaining_acquisitions
            limits["remaining_acquisition_contacts"] = (
                config.acquisition_contact_budget - acquisition_contacts
            )
            if remaining_acquisitions > 0 and revision_index < config.max_revisions:
                limits["available_planner_actions"].append(config.actions[2])
        if (
            config.planner_output_format == "json-action-v1"
            and role_configs[phase_id].role_kind == "planner"
        ):
            remaining_revisions = config.max_revisions - revision_index
            configured_actions = None
            if role_configs[phase_id].role_kind == "planner":
                try:
                    configured_actions = material.response_format["json_schema"][
                        "schema"
                    ]["properties"]["action"]["enum"]
                except (KeyError, TypeError):
                    raise RailsRunnerError(
                        "Planner response schema has no configured action enum"
                    ) from None
                legal_actions = [config.actions[0], config.actions[1]]
                if config.refresh_action is not None:
                    legal_actions.append(config.refresh_action)
                if acquisition_policy is not None:
                    # E18: an armed episode's Planner schema must be able to
                    # spell the action its graph can execute.
                    legal_actions.append(config.actions[2])
                if (
                    not isinstance(configured_actions, list)
                    or not configured_actions
                    or len(set(configured_actions)) != len(configured_actions)
                    or configured_actions != legal_actions
                    or material.response_format
                    != native_planner_action_response_format(configured_actions)
                ):
                    raise RailsRunnerError(
                        "Planner response schema differs from native episode actions"
                    )
            route_actions = [config.actions[0]]
            if remaining_revisions > 0:
                route_actions.append(config.actions[1])
                if config.refresh_action is not None and remaining_refreshes > 0:
                    route_actions.append(config.refresh_action)
                if acquisition_policy is not None and remaining_acquisitions > 0:
                    route_actions.append(config.actions[2])
            elif config.exhaustion_policy == "deliver-latest-solver":
                route_actions.append(config.actions[1])
                if config.refresh_action is not None:
                    route_actions.append(config.refresh_action)
                if acquisition_policy is not None:
                    route_actions.append(config.actions[2])
            available_actions = (
                route_actions
                if configured_actions is None
                else [action for action in route_actions if action in configured_actions]
            )
            limits.update(
                remaining_generation_revisions=remaining_revisions,
                available_planner_actions=available_actions,
            )
            if configured_actions is not None:
                material = replace(
                    material,
                    response_format=native_planner_action_response_format(
                        available_actions
                    ),
                ).validate()
        material = replace(
            material,
            instruction=material.instruction + "\n\nNative episode limits: "
            + json.dumps(limits, sort_keys=True),
        ).validate()
        phase = program.phase(phase_id)
        if (phase.response_format_id is not None) != (material.response_format is not None):
            raise RailsRunnerError("native role response format differs from its phase")
        visits[phase_id] = {
            "query": material.instruction, "material": material, "local_ids": [], "model_contacts": 0,
            # E8a: the same bounded limits this visit's instruction already
            # carries, kept so a node-context rendering can restate them
            # without inventing one (revision index, revision bound, the
            # actions still open to the Planner).
            "limits": dict(limits),
            # NX programme E1: the (context, sealed predecessor) this visit's
            # delivering material was built from, and the cache of each
            # template arm's own instruction -- the SAME inputs, only the
            # node's pinned instruction template differs.
            "material_inputs": (ctx, {} if previous is None else {ctx.sample_id: previous}),
            "arm_instructions": {},
        }
        return material.instruction

    def template_arm_instruction(arm_id, visit, phase_id=None):
        """NX programme E1: ONE template arm's complete instruction text.

        The arm's material is built by the flight-owned per-arm builder
        (``binding.template_variant_materials``: the node's phase material with
        ONLY ``instruction_template`` swapped, over the same fill, response
        format and predecessor state) from the SAME inputs the visit's
        delivering material was built from, then the visit's own bounded
        "Native episode limits" suffix is appended, so an arm and the
        delivering arm differ in the template text and in nothing else.
        Cached per visit: the node asks for it as the arm's query and the
        binding provider asks for it again as the arm's contact instruction,
        and the two must be the same string.
        """

        cached = visit["arm_instructions"].get(arm_id)
        if cached is not None:
            return cached
        builders = binding.template_variant_materials or {}
        builder = builders.get(arm_id)
        if builder is None:
            raise RailsRunnerError(
                f"template-variant arm {arm_id!r} has no flight-owned material builder"
            )
        arm_ctx, sealed = visit["material_inputs"]
        arm_material = builder(phase_id or supply_variant_phase_id, arm_ctx, sealed)
        if not isinstance(arm_material, PhaseMaterial):
            raise RailsRunnerError("template-variant arm material must be PhaseMaterial")
        arm_material.validate()
        if arm_material.response_format != visit["material"].response_format:
            raise RailsRunnerError(
                f"template-variant arm {arm_id!r} changed the node's response format; "
                "an arm overrides the instruction template and nothing else"
            )
        instruction = (
            arm_material.instruction + "\n\nNative episode limits: "
            + json.dumps(visit["limits"], sort_keys=True)
        )
        visit["arm_instructions"][arm_id] = instruction
        return instruction

    def template_arm_query(arm_index, default_query):
        """The query the node hands the framework for arm ``arm_index``: the
        arm's own instruction for a template arm, the visit's own query for
        the delivering arm and the twin (which render the locked template)."""

        arm = supply_variant_group.arms[arm_index]
        if arm.instruction_template is None:
            return default_query
        return template_arm_instruction(arm.arm_id, visits[supply_variant_phase_id])

    def perception_template_query(branch_index, default_query):
        """NX programme E1, Perception node: the query the node hands the
        framework for branch ``branch_index`` -- the branch's own instruction
        for a template branch, the visit's own query for the delivering branch
        and the twin (which render the locked template)."""

        branch = perception_branch_group.branch_at(branch_index)
        if branch.instruction_template is None:
            return default_query
        return template_arm_instruction(
            branch.branch_id, visits[perception_branch_phase_id],
            phase_id=perception_branch_phase_id,
        )

    def speech_binding(request):
        from .native_episode_config import select_native_role_history

        settle()
        ctx = context()
        role = role_configs[request.role_id]
        visit = visits[request.role_id]
        material = visit["material"]
        decoding = dict(base_decoding_params or {})
        if material.response_format is not None:
            decoding["response_format"] = dict(material.response_format)
        names = role.tool_names
        if config.reserve_final_report and names and visit["model_contacts"] >= role.max_iterations - 1:
            names = ()
        if request.visible_tool_names != names:
            raise RailsRunnerError("framework tool scope differs from the configured report turn")
        decoding.update(tool_choice="auto" if names else "none", parallel_tool_calls=False)
        contact_instruction, contact_query = material.instruction, visit["query"]
        template_arm = None
        if template_variant_mode and request.context.variant_arm_id is not None:
            # NX programme E1: the arm's contact instruction and original query
            # are its own template's; the delivering arm and the twin (no
            # template) keep the visit's, byte for byte.
            from .supply_variants import SupplyVariantError

            if request.role_id != supply_variant_phase_id:
                raise RailsRunnerError(
                    "only the registered template-variant node may bind a variant arm"
                )
            try:
                template_arm = supply_variant_group.arm(request.context.variant_arm_id)
            except SupplyVariantError as error:
                raise RailsRunnerError(str(error)) from error
            if template_arm.instruction_template is not None:
                contact_instruction = contact_query = template_arm_instruction(
                    template_arm.arm_id, visit,
                )
        if (
            perception_template_mode
            and request.context.perception_branch_id is not None
            and request.role_id == perception_branch_phase_id
        ):
            # NX programme E1, Perception node: the template branch's contact
            # instruction and original query are its own template's; A and the
            # twin keep the visit's, byte for byte.
            template_branch = perception_branch_group.branch(
                request.context.perception_branch_id
            )
            if template_branch.instruction_template is not None:
                contact_instruction = contact_query = template_arm_instruction(
                    template_branch.branch_id, visit,
                    phase_id=perception_branch_phase_id,
                )
        plan = AgentContactPlan(
            contact_id=request.context.agent_contact_id,
            query_state_sha256=ctx.query_state.content_hash(),
            purpose=program.phase(request.role_id).purpose,
            instruction=contact_instruction,
            key_representation_id=f"{program.program_id}:{request.role_id}",
            matcher_policy_id=program.program_id, decoding_params=decoding,
        ).validate()
        _assert_agent_control_excludes_knowledge_payloads(plan, protected_material)
        state.current_context, state.current_contact = ctx, plan
        if template_arm is not None:
            messages = template_variant_messages(ctx, arm=template_arm, plan=plan)
        elif knowledge_index is None and request.context.variant_arm_id is not None:
            # Item E42 (2026-09-25, family VAR-2): THE seam this whole form
            # lives at. One arm's knowledge construction is composed HERE, at
            # binding composition, and nowhere else -- the same place item E2
            # composes a grouped sample's decoding and item E39 a role's
            # completion cap, and for the same reason: the model fragment, the
            # serving-session identity, the prompt ORDER, the task contract and
            # the tool authority never move, only which evidence blocks this one
            # request carries. The key's absence is unreachable here
            # (``variant_arm_id`` is None for every contact of every episode
            # form written before E42), so every other form's bytes are
            # identical.
            messages = supply_variant_messages(ctx, request=request, plan=plan)
        elif (
            knowledge_index is None
            and request.context.perception_branch_id is not None
            and request.role_id == perception_branch_phase_id
        ):
            # Same-flight instrument, PHASE 2 (merge set C): the twin seam,
            # over the Perception role's own declared branch group instead
            # of the Solver's arm group. The key's absence is unreachable
            # here (``perception_branch_id`` is None for every contact of
            # every episode form written before phase 2), so every other
            # form's bytes are identical.
            messages = perception_branch_messages(ctx, request=request, plan=plan)
        elif (
            knowledge_index is None
            and request.context.perception_branch_id is not None
        ):
            # LEVEL 2 (merge set C item 1): the SAME context field, bound at
            # the SOLVER's own phase instead of Perception's -- the Solver's
            # first-visit branch fan-out (design section 3, "Level 2").
            messages = perception_branch_solver_messages(ctx, request=request, plan=plan)
        elif knowledge_index is None:
            messages = base_messages(ctx)
        else:
            # E21w: the per-role budget is resolved HERE, at request
            # composition, from the role's own kind -- which is the key the
            # config's ``roles.<role>.knowledge_index_budget`` overrides are
            # declared under. With no override every role receives the same
            # block the Solver receives (Q12's default, OFF).
            def _record_index(assembly, selection, provenance, plan=plan, role=role):
                index_contacts[plan.contact_id] = {
                    "assembly": assembly,
                    "selection": selection,
                    "provenance": provenance,
                    "role_kind": role.role_kind,
                }

            messages = base_messages(
                ctx, index_role_kind=role.role_kind, index_sink=_record_index,
            )
            record = index_contacts.get(plan.contact_id)
            if record is None:
                raise RailsRunnerError(
                    "an armed knowledge index composed no assembly for this contact"
                )
            record["system_message"] = messages[0]["content"]
        # LEVEL 2: everything below that reads the row's states reads the
        # branch's own view for a non-A, non-twin Solver branch contact (the
        # exposed history and the compilers); ``ctx`` itself stays the row's
        # custody context. Identity (``ctx``) for every other contact.
        render_ctx = _perception_branch_solver_view(ctx, request)
        exposed_states = select_native_role_history(
            role=role, solver_phase_id=config.role("solver").phase_id,
            states=render_ctx.agent_states, local_tool_result_ids=tuple(visit["local_ids"]),
        )
        if config.role_context_json is not None:
            if context_binding is None:
                raise RailsRunnerError("role context lacks its bound Perception schema")
            available_ids = [ctx.query_state.speech_packet_id]
            available_ids.extend(
                part["evidence_id"] for part in messages[1]["content"]
                if isinstance(part, Mapping) and isinstance(part.get("evidence_id"), str)
            )
            compiled = context_binding.compiler.compile(
                role_kind=role.role_kind,
                phase_ids={item.role_kind: item.phase_id for item in config.roles},
                sample_id=ctx.sample_id, states=render_ctx.agent_states,
                local_tool_result_ids=tuple(visit["local_ids"]),
                available_evidence_ids=tuple(dict.fromkeys(available_ids)),
                draft_response_schema=context_binding.draft_response_schema,
            )
            exposed_states = compiled.states
            record = {
                "contact_id": plan.contact_id,
                "context_config_sha256": context_binding.config_sha256,
                "perception_response_format_sha256": context_binding.source_format_sha256,
                "compilation": compiled.receipt,
            }
            existing = context_compilations.setdefault(plan.contact_id, record)
            if existing != record:
                raise RailsRunnerError("one native contact has conflicting context compilations")
        if node_context_declared:
            if node_context_binding is None:
                raise RailsRunnerError(
                    "node context policy lacks its bound Perception schema"
                )
            policy_evidence_ids = [ctx.query_state.speech_packet_id]
            policy_evidence_ids.extend(
                part["evidence_id"] for part in messages[1]["content"]
                if isinstance(part, Mapping) and isinstance(part.get("evidence_id"), str)
            )
            compiled_policy = node_context_binding.policy.compile(
                role_kind=role.role_kind,
                # E18: the OPTIONAL fifth entry names the acquisition phase,
                # so a state the Acquisition node sealed is classified
                # ``acquired-evidence`` instead of "not a role state". Absent
                # on every unarmed episode, where no such state can exist.
                phase_ids={
                    item.role_kind: item.phase_id for item in config.roles
                } | (
                    {}
                    if acquisition_role_config is None
                    else {"acquisition": acquisition_role_config.phase_id}
                ),
                sample_id=ctx.sample_id,
                states=exposed_states,
                local_tool_result_ids=tuple(visit["local_ids"]),
                available_evidence_ids=tuple(dict.fromkeys(policy_evidence_ids)),
                task_instruction=messages[0]["content"],
                episode_limits=visit["limits"],
                actions=config.actions,
                # E8b: the metered cleaning contact hook. A policy with no
                # cleaned boundary never calls it; a policy with one calls it
                # at most once per boundary per contact, ON THIS SLOT, in this
                # resident session, before this contact's own request is
                # dispatched.
                cleaning_invoker=lambda request: run_cleaning_contact(
                    request, ctx=ctx, visit=visit, base=messages,
                ),
            )
            exposed_states = compiled_policy.states
            policy_record = {
                "contact_id": plan.contact_id,
                "context_policy_config_sha256": node_context_binding.config_sha256,
                "perception_response_format_sha256": (
                    node_context_binding.source_format_sha256
                ),
                "template_sha256s": dict(node_context_binding.template_sha256s),
                "compilation": compiled_policy.receipt,
            }
            existing_policy = node_context_compilations.setdefault(
                plan.contact_id, policy_record
            )
            if existing_policy != policy_record:
                raise RailsRunnerError(
                    "one native contact has conflicting node context compilations"
                )
        if binding.candidate_proposal_for_context is not None and role.role_kind != "perception":
            proposal = binding.candidate_proposal_for_context(ctx)
            digest = proposal.content_hash()
            if proposal_documents and digest not in proposal_documents:
                raise RailsRunnerError("one episode changed its candidate proposal between roles")
            proposal_documents[digest] = proposal.as_json()
            text = proposal.model_text()
            messages = (
                messages[0],
                {**messages[1], "content": [*messages[1]["content"], {
                    "type": "text", "text": text,
                    "evidence_id": f"candidate-proposal:{digest}",
                    "source_uri": f"candidate-proposal://{digest}",
                }]},
            )
            record = {
                "contact_id": plan.contact_id, "role_kind": role.role_kind,
                "query_state_sha256": ctx.query_state.content_hash(),
                "proposal_sha256": digest,
                "rendered_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
            prior = proposal_contacts.setdefault(plan.contact_id, record)
            if prior != record:
                raise RailsRunnerError("one native contact changed its candidate proposal view")
        if program.phase(request.role_id).response_format_id == CITED_ANSWER_RESPONSE_FORMAT_ID:
            # Gap G1 plumbing (``rails.solver_citation``): the citation arrays
            # of this contact's response format may spell only the evidence
            # ids THIS request renders -- the same enumeration the role-context
            # and node-context seams take as ``available_evidence_ids`` -- so an
            # unsupplied citation is impossible under constrained decoding and
            # is refused again at the seal (``capture_completion``). Only the
            # response format moves: every message byte is the un-armed
            # contact's own, and the plan is re-bound so the sealed contact
            # plan carries the decoding it actually sent.
            if material.response_format != cited_answer_response_format():
                raise RailsRunnerError(
                    "cited-answer phase material differs from the registered contract"
                )
            if config.deliver_normaliser_id not in CITED_ANSWER_NORMALISER_IDS:
                # The loader refuses this pairing before contact; restated
                # here so a binding built around the loader cannot deliver
                # the envelope as the answer either.
                raise RailsRunnerError(
                    "the cited-answer contract requires a cited-answer delivery normaliser"
                )
            if request.context.variant_arm_id is not None:
                raise RailsRunnerError(
                    "the cited-answer contract does not compose with supply-variant arms"
                )
            supplied_ids = tuple(dict.fromkeys(
                part["evidence_id"] for part in messages[1]["content"]
                if isinstance(part, Mapping) and isinstance(part.get("evidence_id"), str)
            ))
            decoding = {
                **decoding, "response_format": cited_answer_response_format_for(supplied_ids),
            }
            plan = replace(plan, decoding_params=decoding).validate()
            state.current_contact = plan
            citation_record = {"supplied_value_ids": supplied_ids}
            prior_citation = citation_contacts.setdefault(plan.contact_id, citation_record)
            if prior_citation != citation_record:
                raise RailsRunnerError(
                    "one native contact changed its cited-answer supplied set"
                )
        if (
            request.context.perception_branch_id is not None
            and request.role_id == solver_phase_id
        ):
            # LEVEL 2: the contact-id-free digest of everything this branch
            # Solver contact will actually carry -- both messages and the
            # exposed history -- so the seal can refuse a branch column that
            # saw a different note yet rendered A's request.
            digest = hashlib.sha256(json.dumps(
                {"messages": list(messages), "agent_state": [a.as_json() for a in exposed_states]},
                sort_keys=True, separators=(",", ":"), default=str,
            ).encode("utf-8")).hexdigest()
            if perception_branch_solver_render.setdefault(plan.contact_id, digest) != digest:
                raise RailsRunnerError(
                    "one perception-branch Solver contact composed two different renderings"
                )
        return NativeRoleSpeechBinding(
            role_id=request.role_id, sample_id=ctx.sample_id,
            role_query=contact_query, base_messages=messages,
            core_kwargs={
                "decoding_params": {**decoding, "id_slot": visit["slot_id"]},
                **({
                    "key_representation_id": plan.key_representation_id,
                    "matcher_policy_id": plan.matcher_policy_id,
                } if ctx.query_state.query_source == "speech_features" else {}),
                "agent_state": [a.as_json() for a in exposed_states],
            },
            tool_names=names, local_tool_result_ids=tuple(visit["local_ids"]),
            query_source=ctx.query_state.query_source,
            # E17: authority (``tool_names``, and the ``tool_choice`` derived
            # from it above) is untouched; only what is RENDERED widens, and
            # only when the episode declares ``tool_schema_rendering``
            # ``"constant"``. None -- the default -- renders exactly
            # ``names``, byte-identically to the pre-E17 tree.
            rendered_tool_names=constant_tool_names,
        )

    def capture_completion(request, completion):
        if pending:
            raise RailsRunnerError("native completion overwrote an unsettled source")
        before, plan = state.current_context, state.current_contact
        if plan is not None and plan.contact_id in proposal_contacts:
            proposal_contacts[plan.contact_id].update(
                request_id=completion.request_id,
                request_sha256=completion.request_sha256,
                response_sha256=completion.response_sha256,
            )
        if config.role_context_json is not None:
            context_compilations[plan.contact_id].update(
                request_sha256=completion.request_sha256,
                response_sha256=completion.response_sha256,
            )
        if node_context_declared:
            node_context_compilations[plan.contact_id].update(
                request_sha256=completion.request_sha256,
                response_sha256=completion.response_sha256,
            )
        if before is None or plan is None or request.context.agent_contact_id != plan.contact_id:
            raise RailsRunnerError("native completion lost its actual speech contact")
        # Count every actual completion before interpreting or sealing its text.
        # A contract refusal still spent this contact, although its answer must
        # never enter the pending/completed delivery state below.
        slot_id = visits[request.role_id]["slot_id"]
        visits[request.role_id]["model_contacts"] += 1
        state.contacts.append(AgentContactRecord(
            plan=plan, query_state_sha256=before.query_state.content_hash(),
            speech_packet_sha256=before.query_state.speech_packet_sha256,
            slot_id=slot_id, response_sha256=completion.response_text_sha256,
        ))
        state.response_sha256s.append(completion.response_text_sha256)
        state_content, cited_value_ids = completion.text, ()
        empty_solver_completion = (
            request.role_id == config.role("solver").phase_id
            and not completion.tool_calls and not completion.text.strip()
        )
        if empty_solver_completion:
            if completion.finish_reason == "stop":
                # A source-bound empty answer is a completion-contract refusal,
                # not an infrastructure failure. The existing finite-completion
                # policy decides whether to retain the prior Solver or abstain;
                # strict configurations still raise. Never fabricate answer text.
                refusal = RailsRunnerError("Solver completion contains no answer text")
                refusal.seal_refusal_completion = completion
                refusal.seal_refusal_role_id = request.role_id
                raise refusal
        citation = citation_contacts.get(plan.contact_id)
        if citation is not None:
            # Gap G1 plumbing (``rails.solver_citation``): the sealed state is
            # the ANSWER's own bytes and ``cited_value_ids`` the ids it cites,
            # validated against the ids this very contact rendered; the raw
            # envelope stays bound through ``source_response_sha256``. A
            # citation of unsupplied evidence is a refusal, never a silent
            # drop. A non-``stop`` finish is sealed verbatim with no citation
            # and left to the finite-completion policy that owns it.
            try:
                capture = bind_cited_completion(
                    completion.text, finish_reason=completion.finish_reason,
                    supplied_value_ids=citation["supplied_value_ids"],
                    contact_id=plan.contact_id, role_id=request.role_id,
                    response_text_sha256=completion.response_text_sha256,
                )
            except SolverCitationError as error:
                # E43: tag the refusal with the exact completion it refused
                # (a "stop" finish; ``bind_cited_completion`` only parses on
                # that finish) and the role that made it, so
                # ``reproduction.ojw.native_episode`` can bind this ROW's
                # own disposition to it under ``finite_completion_policy``
                # instead of aborting the arm. ``RailsRunnerError`` itself
                # stays the one rails error type
                # (``rails.errors.RailsError``'s own discipline): every
                # OTHER caller of this seam sees exactly the error it always
                # has, and only a reader that knows to look for these two
                # attributes treats this one differently.
                refusal = RailsRunnerError(f"cited-answer contract refused: {error}")
                refusal.seal_refusal_completion = completion
                refusal.seal_refusal_role_id = request.role_id
                raise refusal from error
            state_content, cited_value_ids = capture.state_content, capture.cited_value_ids
            prior_records = [
                row for row in citation_records if row["contact_id"] == plan.contact_id
            ]
            if prior_records and prior_records != [dict(capture.record)]:
                raise RailsRunnerError("one native contact sealed two different citations")
            if not prior_records:
                citation_records.append(dict(capture.record))
        if (config.review_handoff == "slot-issues-v1"
                and request.role_id == config.role("reviewer").phase_id
                and not completion.tool_calls):
            from .review_handoff import normalize_review_handoff

            state_content = normalize_review_handoff(completion.text)
        if empty_solver_completion:
            # Preserve the raw empty response hash while allowing the later wire
            # projection to apply its existing non-stop completion disposition.
            state_content = '{"schema":"saea-empty-phase-response-v1","response_text":""}'
        source = seal_phase_response_state(
            phase_name=request.role_id, sample_id=before.sample_id,
            state_content=state_content, raw_response_text=completion.text,
            source_query_state_sha256=before.query_state.content_hash(),
            producer_policy_id=program.program_id,
            state_namespace=plan.contact_id,
            cited_value_ids=cited_value_ids,
        )
        if constant_tool_names is not None:
            # E17: the constancy evidence. ``tool_schemas_sha256`` is the
            # digest of the ``tool_schemas`` array this very request carried
            # (``rails.core_client.FrozenCoreClient._completion_metadata``),
            # so one distinct value across the whole list IS the proof that
            # the rendered tools block never toggled inside the row.
            tool_rendering_records.append({
                "contact_id": plan.contact_id,
                "role_id": request.role_id,
                "authority_tool_names": list(request.visible_tool_names),
                "rendered_tool_names": list(constant_tool_names),
                "tool_schemas_sha256": completion.tool_schemas_sha256,
            })
        if knowledge_index is not None:
            # E21w: one receipt row per contact, sealed exactly where E17's
            # ``tool_schema_rendering`` rows are. Digests, ids and counts
            # only -- the expansion block carries released card text and
            # construction utterances, and a receipt is not a place to copy
            # them to. Citations resolve by MEMBERSHIP, so a hallucinated id
            # is detectable rather than merely unparsed.
            from .knowledge_index import (  # noqa: PLC0415
                contact_receipt, extract_citations,
            )

            record = index_contacts.get(plan.contact_id)
            if record is None:
                raise RailsRunnerError(
                    "an armed knowledge index sealed no assembly for this contact"
                )
            row = contact_receipt(
                contact_id=plan.contact_id,
                role_id=request.role_id,
                assembly=record["assembly"],
                system_message=record["system_message"],
                index_text=knowledge_index.index_text,
                cited_ids=extract_citations(completion.text),
                table=knowledge_index.table,
                degradation=index_degradation.get(plan.contact_id, ()),
            )
            row["role_kind"] = record["role_kind"]
            row["selection"] = dict(record["provenance"])
            row["budget"] = knowledge_index.plan.budget_for(
                record["role_kind"]
            ).as_json()
            knowledge_index_records.append(row)
        completed[completion.agent_contact_id] = completion
        pending.update(
            completion=completion, source=source, context=before, plan=plan,
            slot_id=slot_id, phase_id=request.role_id,
            # E2c: which sample of a grouped Solver visit this contact is
            # (None for every ungrouped contact), so ``settle`` can tell the
            # group's last sample -- the one that registers the committed
            # state -- from the ones that register none.
            sample_index=request.context.sample_index,
            # Item E42: which declared arm of a supply-variant visit this
            # contact is (None for every contact of every other form), so
            # ``settle`` can tell the group's delivering arm -- the LAST one,
            # whose own seal is the state this visit registers -- from the ones
            # that register none.
            variant_arm_id=request.context.variant_arm_id,
            # Same-flight instrument, PHASE 2: which declared branch of a
            # Perception-branch visit this contact is (None for every
            # contact of every other form), so ``settle`` can tell the
            # group's delivering branch (A) -- the LAST one, whose own seal
            # is the state this visit registers -- from the ones that
            # register none.
            perception_branch_id=request.context.perception_branch_id,
        )
        if (binding.review_for_phase is not None and not completion.tool_calls
                and completion.finish_reason == "stop"):
            staged = replace(
                before, agent_states=before.agent_states + (source,),
                prior_response_sha256s=before.prior_response_sha256s + (completion.response_text_sha256,),
                core_completions=(completion,),
            )
            verdicts = binding.review_for_phase(request.role_id, staged, completion.text)
            if verdicts is None:
                verdicts = ()
            from ..core.base import JudgeVerdict
            if not isinstance(verdicts, Sequence) or isinstance(verdicts, (str, bytes)):
                raise RailsRunnerError("native phase judges must return structured criticism")
            for verdict in verdicts:
                if not isinstance(verdict, JudgeVerdict):
                    raise RailsRunnerError("native phase judge cannot replace an answer")
                verdict.validate()
            if verdicts:
                state.trace_buffers[(state.scheduled_contacts - 1, 0)].emit(
                    "USE", f"{completion.request_id}/native-phase-review",
                    {
                        "use_role_id": request.role_id,
                        "use_source_request_id": completion.request_id,
                        "use_source_response_sha256": completion.response_sha256,
                        "use_phase_judgments": [verdict.as_json() for verdict in verdicts],
                    },
                )

    def read_supply_variant_arm_record(arm_index, result):
        """Item E42: the receipt row the binding provider wrote for THIS arm.

        The arm's own contact id is read off its execution receipt, so the row
        the node seals is the row the request that produced this answer was
        composed from -- never a sibling arm's. Popped, so a row can be sealed
        exactly once and a second visit of the node starts from an empty table.
        """

        receipt = result.get("execution_receipt")
        final = receipt.get("final_contact") if isinstance(receipt, Mapping) else None
        contact_id = final.get("agent_contact_id") if isinstance(final, Mapping) else None
        record = supply_variant_records.pop(contact_id, None)
        if record is None or record.get("arm_index") != arm_index:
            raise RailsRunnerError(
                "a supply-variant arm sealed no recorded contact of its own"
            )
        return record

    def read_perception_branch_record(branch_index, result, sample_index=None):
        """Same-flight instrument, PHASE 2: the receipt row for THIS branch.

        Structurally :func:`read_supply_variant_arm_record`'s twin: the
        branch's own contact id, request and response digests are read off
        its OWN execution receipt's final contact -- the native framework's
        own per-contact custody, never recomputed here, exactly as the
        supply-variant arm route reads them for the bundle's I7v check --
        and combined with the LIGHTWEIGHT pending row
        ``perception_branch_messages`` recorded at request-composition time
        (the branch identity and the value ids the request actually
        carried), plus the note's own parse (``candidate_intent_ids``,
        ``note_parse_status``), read directly off this branch's raw
        response text since a non-delivering branch registers no sealed
        state to read it from instead.
        """

        from .supply_variants import perception_branch_record

        receipt = result.get("execution_receipt")
        final = receipt.get("final_contact") if isinstance(receipt, Mapping) else None
        contact_id = final.get("agent_contact_id") if isinstance(final, Mapping) else None
        pending_row = perception_branch_records.pop(contact_id, None)
        if pending_row is None or pending_row.get("branch_index") != branch_index:
            raise RailsRunnerError(
                "a perception branch sealed no recorded contact of its own"
            )
        if perception_sampling_mode and pending_row.get("sample_index") != sample_index:
            raise RailsRunnerError(
                "a perception-branch sample sealed another sample's recorded contact"
            )
        request_sha256 = final.get("request_sha256") if isinstance(final, Mapping) else None
        response_text_sha256 = (
            final.get("response_text_sha256") if isinstance(final, Mapping) else None
        )
        if not isinstance(request_sha256, str) or not isinstance(response_text_sha256, str):
            raise RailsRunnerError(
                "a perception branch's execution receipt has no request/response digest"
            )
        note_text = result.get("actor_output", "")
        note_sha256 = hashlib.sha256(note_text.encode("utf-8")).hexdigest()
        note_parse_status, candidate_intent_ids, raw_count = _parse_perception_branch_note(
            note_text,
        )
        branch = perception_branch_group.branch_at(branch_index)
        if perception_sampling_mode and branch.perception_samples is not None:
            # Decision 338, lever L2: keep this sample's custody; the LAST sample merges the k notes and the merged note
            # replaces the branch's own in ``perception_branch_notes`` (what its Solver contact renders). Sample 0 alone builds
            # the branch's row below; later samples return only the branch identity.
            axis = branch.perception_samples
            seed = adapter_request.branch_sample_seeds.get(contact_id)
            if seed is None:
                raise RailsRunnerError("a perception-sample contact composed no recorded seed")
            stream = sampling_perception_streams.setdefault(branch.branch_id, [])
            if sample_index != len(stream):
                raise RailsRunnerError("perception samples were read out of their declared order")
            stream.append({
                "contact_id": contact_id, "request_sha256": request_sha256,
                "response_text_sha256": response_text_sha256, "note_parse_status": note_parse_status,
                "candidate_intent_ids": list(candidate_intent_ids), "text": note_text, "seed": seed,
            })
            if sample_index == axis.k - 1:
                from .perception_merge_policies import build_merged_note
                from .supply_variants import (
                    derive_sample_seeds, merge_perception_samples, perception_samples_record,
                )

                outcome = merge_perception_samples(axis, [row["text"] for row in stream])
                if tuple(row["seed"] for row in stream) != derive_sample_seeds(stream[0]["seed"], axis.seed_offsets):
                    raise RailsRunnerError(
                        f"perception branch {branch.branch_id!r} samples carried seeds other than the lock seed plus its offsets"
                    )
                sampling_records.setdefault(branch.branch_id, {})["perception_samples"] = perception_samples_record(
                    axis, lock_seed=stream[0]["seed"],
                    samples=[{key: value for key, value in row.items() if key not in ("text", "seed")} for row in stream],
                    outcome=outcome,
                )
                perception_branch_notes[branch.branch_id] = build_merged_note(
                    [row["text"] for row in stream], outcome,
                )
            if sample_index != 0:
                return {"branch_id": branch.branch_id}
            # Sample 0 falls through to build the row; the notes entry below is sample 0's until the merge replaces it.
        # LEVEL 2 (merge set C item 1): keep this branch's own RAW note text
        # for the whole row -- the Solver's later first visit
        # (``perception_branch_solver_messages``) needs it to render a
        # non-A branch's own history without a second Perception contact.
        # Harmless at level 1 too (simply never read).
        if not (perception_sampling_mode and branch.perception_samples is not None and branch.branch_id in sampling_records):
            perception_branch_notes[branch.branch_id] = note_text
        # "What to build" item 3: a short list is a measured outcome, never
        # a refusal. Counted on the COLLAPSED list (a padded [x, x, y] meets
        # a bound of 2, not 3); an empty or malformed note carries no ids and
        # is honestly reported as NOT meeting the bound rather than raising.
        min_candidates_met = (
            None if branch.min_candidates is None
            else len(candidate_intent_ids) >= branch.min_candidates
        )
        return perception_branch_record(
            branch=branch, branch_index=branch_index, contact_id=contact_id,
            request_sha256=request_sha256, response_text_sha256=response_text_sha256,
            note_sha256=note_sha256, note_parse_status=note_parse_status,
            candidate_intent_ids=candidate_intent_ids,
            candidate_intent_ids_raw_count=raw_count,
            supplied_value_ids=pending_row["supplied_value_ids"],
            presentation_skip_reason=pending_row.get("presentation_skip_reason"),
            contrast_block_sha256=pending_row.get("contrast_block_sha256"),
            min_candidates_met=min_candidates_met,
            template_group=perception_template_mode,
            thinking_group=perception_thinking_mode,
            sampling_group=perception_sampling_mode, sampling_pending=perception_sampling_mode,
        )

    def record_solver_sample(branch, sample_index, *, contact_id, request_sha256, response_text_sha256, text, finite_reason):
        """Decision 338, lever L1: keep one Solver sample's custody; the LAST sample commits the n answers."""

        from .supply_variants import (
            commit_solver_samples, derive_sample_seeds, solver_sample_parse_status, solver_samples_record,
        )

        axis = branch.solver_samples
        seed = adapter_request.branch_sample_seeds.get(contact_id)
        if seed is None:
            raise RailsRunnerError("a solver-sample contact composed no recorded seed")
        stream = sampling_solver_streams.setdefault(branch.branch_id, [])
        if sample_index != len(stream):
            raise RailsRunnerError("solver samples were read out of their declared order")
        stream.append({
            "contact_id": contact_id, "request_sha256": request_sha256, "response_text_sha256": response_text_sha256,
            "parse_status": solver_sample_parse_status(text, finite_reason=finite_reason), "text": text, "seed": seed,
        })
        if sample_index != axis.n - 1:
            return
        if tuple(row["seed"] for row in stream) != derive_sample_seeds(stream[0]["seed"], axis.seed_offsets):
            raise RailsRunnerError(
                f"perception branch {branch.branch_id!r} Solver samples carried seeds other than the lock seed plus its offsets"
            )
        # The in-flight run declares no N1 source (it needs the supplied exemplar ids), so a configured gate reports
        # ``n1-unavailable`` and does not fire; the reader computes N1 offline.
        outcome = commit_solver_samples(axis, [row["text"] for row in stream], n1=None)
        sampling_records.setdefault(branch.branch_id, {})["solver_samples"] = solver_samples_record(
            axis, lock_seed=stream[0]["seed"],
            samples=[{key: value for key, value in row.items() if key not in ("text", "seed")} for row in stream],
            outcome=outcome,
        )

    def read_perception_branch_solver_record(branch_index, result, sample_index=None):
        """LEVEL 2 (merge set C item 1, design section 3, "Level 2"): one
        branch's own Solver-column custody.

        Structurally :func:`read_perception_branch_record`'s twin, over the
        Solver's own contact instead of Perception's: the branch's contact
        id, request and response digests are read off its OWN execution
        receipt's final contact, combined with the lightweight pending row
        ``perception_branch_solver_messages`` recorded at request-composition
        time (this contact's own rendered ``candidate_supply_value_ids``).
        The returned row is NOT embedded in the Solver's own result (unlike
        a supply-variant arm's row, there is no ``latest_solver`` custody key
        for it to ride): it is recorded into
        ``perception_branch_solver_records``, keyed by branch id, and folded
        into the ALREADY-SEALED ``perception_branches`` receipt at the
        episode's own final receipt assembly.
        """

        receipt = result.get("execution_receipt")
        final = receipt.get("final_contact") if isinstance(receipt, Mapping) else None
        contact_id = final.get("agent_contact_id") if isinstance(final, Mapping) else None
        pending_row = perception_branch_solver_pending.pop(contact_id, None)
        if pending_row is None:
            raise RailsRunnerError(
                "a perception-branch Solver contact sealed no recorded branch "
                "of its own"
            )
        branch = perception_branch_group.branch_at(branch_index)
        if pending_row["branch_id"] != branch.branch_id:
            raise RailsRunnerError(
                "a perception-branch Solver contact sealed another branch's "
                "pending record"
            )
        if perception_sampling_mode and pending_row.get("sample_index") != sample_index:
            raise RailsRunnerError(
                "a perception-branch Solver sample sealed another sample's pending record"
            )
        request_sha256 = final.get("request_sha256") if isinstance(final, Mapping) else None
        response_text_sha256 = (
            final.get("response_text_sha256") if isinstance(final, Mapping) else None
        )
        if not isinstance(request_sha256, str) or not isinstance(response_text_sha256, str):
            raise RailsRunnerError(
                "a perception-branch Solver contact has no request/response digest"
            )
        if perception_sampling_mode and branch.solver_samples is not None:
            record_solver_sample(
                branch, sample_index, contact_id=contact_id, request_sha256=request_sha256,
                response_text_sha256=response_text_sha256, text=result.get("actor_output"), finite_reason=None,
            )
            if sample_index != 0:
                # The branch's Solver column is its sample 0 contact; later samples only feed the sampling record.
                rendered = perception_branch_solver_render.get(contact_id)
                if rendered is not None and rendered != perception_branch_solver_render_by_branch.get(branch.branch_id):
                    raise RailsRunnerError(
                        f"perception branch {branch.branch_id!r} Solver samples rendered different requests"
                    )
                return {"branch_id": branch.branch_id}
        record = {
            "branch_id": branch.branch_id,
            "solver_contact_id": contact_id,
            "solver_request_sha256": request_sha256,
            "solver_response_text_sha256": response_text_sha256,
            "candidate_supply_value_ids": list(pending_row["candidate_supply_value_ids"]),
        }
        perception_branch_solver_records[branch.branch_id] = record
        rendered = perception_branch_solver_render.get(contact_id)
        if rendered is not None:
            perception_branch_solver_render_by_branch[branch.branch_id] = rendered
        return record

    def read_perception_branch_solver_absent(branch_index, error, sample_index=None):
        """LEVEL 2, NX-T R1 seal fix (2026-10-15): one NON-delivering branch's
        Solver contact that ended on a finite completion.

        ``read_perception_branch_solver_record``'s twin for the failure path.
        The contact was composed, sent and metered like any other (its
        request/response records are traced and it counts against the
        contact ceiling), so the SAME custody is read off the interrupted
        role's execution receipt and the SAME pending row is consumed -- the
        branch simply has no authoritative answer. The record carries
        ``solver_absent`` and ``absent_reason`` (the code path:
        ``finite-completion:<finish_reason>``) and is folded into the sealed
        ``perception_branches`` receipt by the same final assembly. Only the
        runner's fan-out calls this, and only for a branch that does not
        deliver; the delivering branch's finite completion keeps its
        fail-closed path.
        """

        receipt = getattr(error, "execution_receipt", None)
        final = receipt.get("final_contact") if isinstance(receipt, Mapping) else None
        contact_id = final.get("agent_contact_id") if isinstance(final, Mapping) else None
        pending_row = perception_branch_solver_pending.pop(contact_id, None)
        if pending_row is None:
            raise RailsRunnerError(
                "a perception-branch Solver contact that ended on a finite completion "
                "sealed no recorded branch of its own"
            )
        branch = perception_branch_group.branch_at(branch_index)
        if pending_row["branch_id"] != branch.branch_id:
            raise RailsRunnerError(
                "a perception-branch Solver contact that ended on a finite completion "
                "sealed another branch's pending record"
            )
        if branch.deliver:
            raise RailsRunnerError(
                "the delivering perception branch's finite completion cannot be recorded "
                "as an absent Solver column"
            )
        request_sha256 = final.get("request_sha256") if isinstance(final, Mapping) else None
        response_text_sha256 = (
            final.get("response_text_sha256") if isinstance(final, Mapping) else None
        )
        if not isinstance(request_sha256, str) or not isinstance(response_text_sha256, str):
            raise RailsRunnerError(
                "a perception-branch Solver contact that ended on a finite completion "
                "has no request/response digest"
            )
        if perception_sampling_mode and branch.solver_samples is not None:
            # A sample that ended on a finite completion casts no vote; the other samples still run. Only sample 0 (the
            # branch's Solver column) marks the branch row absent.
            record_solver_sample(
                branch, sample_index, contact_id=contact_id, request_sha256=request_sha256,
                response_text_sha256=response_text_sha256, text=None,
                finite_reason=str(getattr(error, "finish_reason", None)),
            )
            if sample_index != 0:
                return {"branch_id": branch.branch_id}
        record = {
            "branch_id": branch.branch_id,
            "solver_contact_id": contact_id,
            "solver_request_sha256": request_sha256,
            "solver_response_text_sha256": response_text_sha256,
            "candidate_supply_value_ids": list(pending_row["candidate_supply_value_ids"]),
            "solver_absent": True,
            "absent_reason": f"finite-completion:{getattr(error, 'finish_reason', None)}",
        }
        perception_branch_solver_records[branch.branch_id] = record
        rendered = perception_branch_solver_render.get(contact_id)
        if rendered is not None:
            perception_branch_solver_render_by_branch[branch.branch_id] = rendered
        return record

    def cleaning_binding_provider(request):
        """E8b: hand the cleaning contact its own prepared speech binding.

        The binding is composed by ``run_cleaning_contact`` below and stored
        under this contact's id, so the SAME
        ``MeteredNativeSpeechRequest.prepare`` that composes every role
        contact composes this one: same framework-history encoding, same
        decoding validation, same tool-scope check, same payload build.
        """

        binding_for_contact = cleaning_bindings.pop(
            request.context.agent_contact_id, None,
        )
        if binding_for_contact is None:
            raise RailsRunnerError("node context cleaning contact lost its binding")
        return binding_for_contact

    def capture_cleaning_completion(_request, _completion):
        """E8b: a cleaning contact registers NO phase state and settles NO
        episode step, so this sink deliberately does nothing.

        It exists because ``MeteredNativeSpeechRequest`` requires a completion
        hook, and because a cleaning contact must never reach
        ``capture_completion`` -- which would seal a phase state, overwrite the
        pending role completion and route the episode graph on text that is
        not a role's answer.

        E17 adds the ONE thing it does record: this contact's rendered
        tools-array digest, because it is a contact on the row's own slot and
        the constancy claim has to cover it. That is a receipt append, not a
        state registration -- nothing above changes.
        """

        if constant_tool_names is not None:
            tool_rendering_records.append({
                "contact_id": _request.context.agent_contact_id,
                "role_id": _request.role_id,
                "authority_tool_names": list(_request.visible_tool_names),
                "rendered_tool_names": list(constant_tool_names),
                "tool_schemas_sha256": _completion.tool_schemas_sha256,
            })

    def run_cleaning_contact(request, *, ctx, visit, base):
        """E8b: make ONE metered cleaning contact for a cleaned boundary.

        It runs inside the CONSUMER contact's own ``run_contact`` worker, on
        the consumer's pinned slot, so it reaches the same resident session and
        the same serving geometry. Everything that makes a contact a contact
        applies to it: the registered ceiling, a unique bound contact identity,
        its own trace buffer and USE record, the flight's request/fit gate, the
        shared ``FrozenCoreClient`` budget and cost path, and the episode's
        evidence pins. What it does NOT do is register a phase state or advance
        the episode -- it produces context for the contact that is composing.
        """

        from ..core.base import RESPONSE_FORMATS  # noqa: PLC0415
        from ..core.tracing import get_current_trace_buffer  # noqa: PLC0415
        from .node_context_policy import CleaningContactOutcome  # noqa: PLC0415

        if state.scheduled_contacts >= config.max_contacts:
            raise RailsRunnerError(
                "node context cleaning contact exceeds the registered contact ceiling"
            )
        index = cleaning_contact_counts.get(request.phase_id, 0)
        cleaning_contact_counts[request.phase_id] = index + 1
        contact_id = scoped_execution_contact_id(
            f"{program.program_id}:{request.phase_id}:{index}:{ctx.sample_id}",
            state.prepared.execution_unit_id,
        )
        if contact_id in state.seen_contact_ids:
            raise RailsRunnerError("native graph repeated a contact identity")
        # ``knowledge: "none"`` -- the shared contract and the speech packet,
        # with every evidence block of the consumer's turn dropped.
        system, user = node_context_cleaning_messages(base)
        decoding = dict(base_decoding_params or {})
        response_format = RESPONSE_FORMATS.resolve(request.response_format_id)()
        if not isinstance(response_format, Mapping) or not response_format:
            raise RailsRunnerError(
                "node context cleaning response format rendered nothing"
            )
        decoding["response_format"] = dict(response_format)
        decoding.update(tool_choice="none", parallel_tool_calls=False)
        cleaning_plan = AgentContactPlan(
            contact_id=contact_id,
            query_state_sha256=ctx.query_state.content_hash(),
            purpose=f"node-context-cleaning:{request.boundary_id}",
            instruction=request.instruction,
            key_representation_id=f"{program.program_id}:{request.phase_id}",
            matcher_policy_id=program.program_id,
            decoding_params=decoding,
        ).validate()
        _assert_agent_control_excludes_knowledge_payloads(
            cleaning_plan, protected_material,
        )
        cleaning_bindings[contact_id] = NativeRoleSpeechBinding(
            role_id=request.phase_id, sample_id=ctx.sample_id,
            role_query=request.instruction, base_messages=(system, user),
            core_kwargs={
                "decoding_params": {**decoding, "id_slot": visit["slot_id"]},
                **({
                    "key_representation_id": cleaning_plan.key_representation_id,
                    "matcher_policy_id": cleaning_plan.matcher_policy_id,
                } if ctx.query_state.query_source == "speech_features" else {}),
                # A cleaning contact reads its instruction and nothing else:
                # the material it restates is IN that instruction, so it needs
                # no agent-state history of its own.
                "agent_state": [],
            },
            tool_names=(), local_tool_result_ids=(),
            query_source=ctx.query_state.query_source,
            # E17: a cleaning contact runs on the CONSUMER's own pinned slot,
            # between two role contacts of the same row, so it has to render
            # the same constant array or it re-introduces exactly the toggle
            # this key removes. It calls nothing, as before: its authority
            # stays empty and its tool_choice stays 'none'.
            rendered_tool_names=constant_tool_names,
        )
        role_request = NativeRoleModelRequest(
            role_id=request.phase_id,
            context=NativeRoleContactContext(
                sample_id=ctx.sample_id,
                agent_contact_id=contact_id,
                evidence_pins={"knowledge_snapshot": snapshot_sha256},
                budget_id=run_id,
            ),
            messages=(system, {"role": "user", "content": request.instruction}),
            tool_schemas=(), visible_tool_names=(), decoding_controls={},
        )
        trace = TraceBuffer(run_id, spool=state.trace_spool)
        state.trace_buffers[(state.scheduled_contacts, 0)] = trace
        state.scheduled_contacts += 1
        state.seen_contact_ids.add(contact_id)
        consumer_trace = get_current_trace_buffer()
        set_current_trace_buffer(trace)
        try:
            prepared = cleaning_request.prepare(role_request)
            binding.request_gate(prepared.request)
            completion = cleaning_request.dispatch(prepared)
            trace.emit("USE", f"{completion.request_id}/native-role-contact", {
                "use_role_id": request.phase_id,
                "use_request_sha256": completion.request_sha256,
                "use_response_sha256": completion.response_sha256,
                "use_response_text_sha256": completion.response_text_sha256,
                "use_agent_contact_id": completion.agent_contact_id,
            })
        finally:
            cleaning_bindings.pop(contact_id, None)
            set_current_trace_buffer(consumer_trace)
        if completion.agent_contact_id != contact_id:
            raise RailsRunnerError("node context cleaning lost its actual contact")
        return CleaningContactOutcome(
            agent_contact_id=completion.agent_contact_id,
            request_id=completion.request_id,
            request_sha256=completion.request_sha256,
            response_sha256=completion.response_sha256,
            response_text_sha256=completion.response_text_sha256,
            text=completion.text,
        )

    def record_solver_commit(role_result):
        """E2c: take one grouped Solver visit's committed answer in custody.

        Called by ``GroupedSolverRoleNode`` immediately after its registered
        commit policy has aggregated the visit's N samples and BEFORE the
        graph advances, so the visit's last sample is still ``pending`` and
        the next ``settle`` -- the Reviewer's ``role_input``, or the terminal
        one in a review-off episode -- registers this exact text as the
        visit's one Solver phase state.
        """

        actor_output = (
            role_result.get("actor_output") if isinstance(role_result, Mapping) else None
        )
        if not isinstance(actor_output, str) or not actor_output:
            raise RailsRunnerError("grouped Solver visit produced no committed answer")
        if solver_commit:
            raise RailsRunnerError(
                "a grouped Solver visit's committed answer was never registered"
            )
        solver_commit["actor_output"] = actor_output

    adapter_request = MeteredNativeSpeechRequest(
        client=core_client, binding_provider=speech_binding,
        render_request=binding.render_request, completion_sink=capture_completion,
        solver_role_id=(
            solver_role_config.phase_id if solver_group_samples > 1 else None
        ),
        solver_sampling=(
            None if solver_group_samples <= 1 else {
                "fragment_seed": solver_fragment_seed,
                "decoding_overrides": dict(solver_role_config.decoding_overrides),
            }
        ),
        # Item E39 (2026-09-22): the per-role completion caps this episode
        # declares. Empty for every config written before E39, which leaves
        # every composed request byte-identical.
        role_completion_caps=config.role_completion_caps,
        # Decision 283 A: the per-node thinking override map, keyed by role phase id. None for every config that declares no
        # ``thinking_policy`` -- which leaves every composed request byte-identical.
        role_thinking_policy=_role_thinking_policy(config, binding.thinking_policy),
        # NX-T R1: the per-branch thinking override map of a thinking-policy column, ``{branch id: {role phase id: override}}``.
        # None for every config that declares no ``roles.perception.thinking_variants`` -- byte-identical requests.
        branch_thinking_policy=_branch_thinking_policy(config, perception_branch_group),
        # NX-T R4: the per-arm SAMPLING override of a decoding column, ``{arm id: {name: value}}`` bound to the Solver's
        # phase id. None for every config that declares no ``roles.solver.decoding_variants`` -- byte-identical requests.
        solver_arm_decoding=solver_arm_decoding or None,
        solver_arm_decoding_role_id=(supply_variant_phase_id if solver_arm_decoding else None),
        # Decision 338: the per-branch SAMPLING axes of a sampling column, ``{branch id: {role phase id: {decoding,
        # seed_offsets}}}``. None for every config that declares no ``roles.perception.sampling_variants`` -- byte-identical
        # requests.
        branch_sampling=(
            _sampling_decoding_table(perception_branch_group, perception_branch_phase_id, solver_phase_id)
            if perception_sampling_mode else None
        ),
    )
    # E8b: the SAME request composer, bound to the cleaning contact's own
    # binding provider and to a completion sink that settles nothing. It is a
    # second instance rather than a second path: every byte of a cleaning
    # request is built by MeteredNativeSpeechRequest.prepare exactly as a role
    # contact's is, and dispatched through the same FrozenCoreClient. It is
    # constructed unconditionally and used only when a boundary is ``cleaned``.
    cleaning_request = MeteredNativeSpeechRequest(
        client=core_client, binding_provider=cleaning_binding_provider,
        render_request=binding.render_request,
        completion_sink=capture_cleaning_completion,
    )

    def _relisten_binding_provider(_request):
        raise RailsRunnerError(
            "a relisten contact must be dispatched with its own composed "
            "binding (binding_override), never resolved through this "
            "placeholder provider"
        )

    def _capture_relisten_completion(_request, _completion):
        """Item E4: like a cleaning contact, a relisten contact registers NO
        phase state and settles NO episode step -- it runs strictly after the
        Planner's ACCEPT and the deliver normaliser, over an episode that has
        already finished routing -- so this sink deliberately does nothing.
        """

    # Item E4 (2026-09-28, owner decision 185): the SAME request composer, a
    # third instance beside ``adapter_request`` and ``cleaning_request``: every
    # byte of a relisten contact is built by ``MeteredNativeSpeechRequest.
    # prepare`` exactly as a role contact's is, and dispatched through the
    # same ``FrozenCoreClient``. Constructed unconditionally and used only
    # when ``native_episode.relisten`` is armed (``relisten_config is not
    # None``); ``_dispatch_relisten_contact`` below always passes its own
    # composed ``binding_override``, so ``_relisten_binding_provider`` is
    # never actually called.
    relisten_request = MeteredNativeSpeechRequest(
        client=core_client, binding_provider=_relisten_binding_provider,
        render_request=binding.render_request,
        completion_sink=_capture_relisten_completion,
    )

    def _dispatch_relisten_contact(*, slot_id, contact_kind, index, instruction, response_format_id):
        """Item E4: make ONE metered relisten contact (blind or confirm).

        Structurally ``run_cleaning_contact``'s sibling: the same ceiling
        check, the same unique bound contact identity, its own trace buffer
        and USE record, the flight's request/fit gate, and the shared
        ``FrozenCoreClient`` budget and cost path. What differs: the
        instruction and response format are named EXPLICITLY per call (never
        resolved from a fixed ``PhaseProgram`` phase, which the blind and
        forced-choice contacts could not share -- section 6's implementation
        table keys this stage on no such phase), and the messages are the
        packet ALONE (``node_context_cleaning_messages`` strips every
        evidence block, exactly as section 1 requires: "the packet ... but
        not c" -- no knowledge key/value block is evidence a relisten
        contact needs or may carry).
        """

        from ..core.base import RESPONSE_FORMATS  # noqa: PLC0415
        from ..core.tracing import get_current_trace_buffer  # noqa: PLC0415

        if state.scheduled_contacts >= config.max_contacts:
            raise RailsRunnerError(
                "native graph exceeds its registered contact ceiling"
            )
        contact_id = scoped_execution_contact_id(
            f"{program.program_id}:relisten:{contact_kind}:{index}:"
            f"{state.prepared.sample.sample_id}",
            state.prepared.execution_unit_id,
        )
        if contact_id in state.seen_contact_ids:
            raise RailsRunnerError("native graph repeated a contact identity")
        ctx = context()
        system, user = node_context_cleaning_messages(base_messages(ctx))
        decoding = dict(base_decoding_params or {})
        response_format = RESPONSE_FORMATS.resolve(response_format_id)()
        if not isinstance(response_format, Mapping) or not response_format:
            raise RailsRunnerError("relisten response format rendered nothing")
        decoding["response_format"] = dict(response_format)
        decoding.update(tool_choice="none", parallel_tool_calls=False)
        relisten_plan = AgentContactPlan(
            contact_id=contact_id,
            query_state_sha256=ctx.query_state.content_hash(),
            purpose=f"relisten:{contact_kind}",
            instruction=instruction,
            key_representation_id=f"{program.program_id}:relisten",
            matcher_policy_id=program.program_id,
            decoding_params=decoding,
        ).validate()
        _assert_agent_control_excludes_knowledge_payloads(relisten_plan, protected_material)
        relisten_binding = NativeRoleSpeechBinding(
            role_id="relisten", sample_id=ctx.sample_id,
            role_query=instruction, base_messages=(system, user),
            tool_names=(), query_source=ctx.query_state.query_source,
            core_kwargs={
                # E20/id_slot: the runner owns slot affinity, so it is added
                # here, as a COPY of the plan's own decoding params, exactly
                # as ``speech_binding`` adds it -- never into ``decoding``
                # itself, which ``relisten_plan.validate()`` (above) refuses
                # to see carry ``id_slot`` at all.
                "decoding_params": {**decoding, "id_slot": slot_id},
                **({
                    "key_representation_id": relisten_plan.key_representation_id,
                    "matcher_policy_id": relisten_plan.matcher_policy_id,
                } if ctx.query_state.query_source == "speech_features" else {}),
                # A relisten contact reads its instruction and the packet
                # alone: the targeted slot type and the decided intent are IN
                # that instruction, so it needs no agent-state history of its
                # own -- the same reason a cleaning contact needs none.
                "agent_state": [],
            },
        )
        role_request = NativeRoleModelRequest(
            role_id="relisten",
            context=NativeRoleContactContext(
                sample_id=ctx.sample_id, agent_contact_id=contact_id,
                evidence_pins={"knowledge_snapshot": snapshot_sha256}, budget_id=run_id,
            ),
            messages=(system, {"role": "user", "content": instruction}),
            tool_schemas=(), visible_tool_names=(), decoding_controls={},
        )
        trace = TraceBuffer(run_id, spool=state.trace_spool)
        state.trace_buffers[(state.scheduled_contacts, 0)] = trace
        state.scheduled_contacts += 1
        state.seen_contact_ids.add(contact_id)
        prior_trace = get_current_trace_buffer()
        set_current_trace_buffer(trace)
        try:
            prepared = relisten_request.prepare(role_request, binding_override=relisten_binding)
            binding.request_gate(prepared.request)
            completion = relisten_request.dispatch(prepared)
            trace.emit("USE", f"{completion.request_id}/native-role-contact", {
                "use_role_id": "relisten",
                "use_request_sha256": completion.request_sha256,
                "use_response_sha256": completion.response_sha256,
                "use_response_text_sha256": completion.response_text_sha256,
                "use_agent_contact_id": completion.agent_contact_id,
            })
        finally:
            set_current_trace_buffer(prior_trace)
        if completion.agent_contact_id != contact_id:
            raise RailsRunnerError("relisten contact lost its actual contact")
        return completion.request_id, completion.text

    async def send_relisten_contact(*, contact_kind, index, instruction, response_format_id):
        """Item E4: schedule one relisten contact on an assigned GPU slot,
        through the SAME ``run_contact`` scheduler every role contact uses,
        so a relisten contact participates in the flight's own fair,
        ready-first slot scheduling rather than running unscheduled."""

        def contact(slot_id):
            return _dispatch_relisten_contact(
                slot_id=slot_id, contact_kind=contact_kind, index=index,
                instruction=instruction, response_format_id=response_format_id,
            )
        options = {"prefix_family": "relisten"} if binding.prefix_slots is not None or binding.node_batch is not None or binding.node_pipeline is not None else {}
        return await run_contact(contact, **options)

    async def run_relisten_stage(delivered_text):
        """Item E4 (owner decision 185, section 1, extended by the section 8
        coordinator rulings): the post-accept targeted re-listen.

        Runs exactly once per row, over the NORMALISED delivered answer --
        the caller (below) calls this AFTER the deliver normaliser and BEFORE
        the seal, the same text the official scorer will read. Model-free
        targeting, canonical comparison, ordering and acceptance all live in
        ``rails.relisten``; this function only spends and traces the metered
        blind/forced-choice contacts and hands their parsed results to that
        module's pure decision functions. The returned receipt is sealed onto
        the row unconditionally (even when the delivered answer carries no
        entities to target), so a relisten-armed row is always visibly
        "relisten ran" rather than silently indistinguishable from an
        unarmed one.
        """

        from . import relisten as rl  # noqa: PLC0415

        # Migration step 5: the delivered units re-listen targets come from
        # the carrier's ``delivered_units`` hook (SLURP: parse_slu_response).
        units_hook = (
            carrier_hooks.delivered_units
            if carrier_hooks is not None and carrier_hooks.delivered_units is not None
            else _slurp_default_hooks().delivered_units
        )
        intent, entities, parsed = units_hook(delivered_text)
        if not parsed:
            return rl.seal_relisten_receipt(
                (), max_slots_per_row=relisten_config.max_slots_per_row,
            )
        sample_id = state.prepared.sample.sample_id
        records = []
        for index in rl.select_relisten_targets(entities, relisten_config.max_slots_per_row):
            entity = entities[index]
            _blind_request_id, blind_text = await send_relisten_contact(
                contact_kind="blind", index=index,
                instruction=relisten_blind_template.format(
                    slot_type=entity.type, intent=intent,
                ),
                response_format_id=rl.BLIND_RESPONSE_FORMAT_ID,
            )
            blind = rl.parse_blind_response(
                blind_text, max_words=relisten_config.value_max_words,
            )
            confirm_letter = confirm_contact_id = order = None
            if rl.should_fire_confirm(blind, entity.filler):
                order = rl.confirm_order(sample_id, entity.type)
                candidate_text = (
                    blind.value if blind.disposition == rl.BLIND_VALUE
                    else rl.UNHEARD_SENTINEL
                )
                option_text = {
                    rl.CONFIRM_DELIVERED: entity.filler,
                    rl.CONFIRM_CANDIDATE: candidate_text,
                }
                confirm_contact_id, confirm_text = await send_relisten_contact(
                    contact_kind="confirm", index=index,
                    instruction=relisten_confirm_template.format(
                        slot_type=entity.type, intent=intent,
                        option_a=option_text[order[0]], option_b=option_text[order[1]],
                    ),
                    response_format_id=rl.CONFIRM_RESPONSE_FORMAT_ID,
                )
                confirm_letter = rl.parse_confirm_letter(confirm_text)
            records.append(rl.decide_entity(
                index=index, slot_type=entity.type, delivered_value=entity.filler,
                blind=blind, blind_contact_id=_blind_request_id,
                confirm_letter=confirm_letter, order=order,
                confirm_contact_id=confirm_contact_id,
            ))
        return rl.seal_relisten_receipt(
            records, max_slots_per_row=relisten_config.max_slots_per_row,
        )

    # E20 (2026-09-19, owner decision 45): the dispatch-time context-fit
    # seam. ``None`` under ``context_fit_policy == "raise"`` -- every cell
    # written before E20 -- and then every line below is skipped and the
    # dispatch path is byte-identical to its pre-E20 self.
    context_fit_budget = (
        binding.context_fit_budget
        if config.context_fit_policy == "compact-or-abstain" else None
    )
    if config.context_fit_policy == "compact-or-abstain" and context_fit_budget is None:
        raise RailsRunnerError(
            "context_fit_policy 'compact-or-abstain' requires a live serving "
            "budget on the episode binding"
        )
    # Item E21 (the knowledge index, not the Earnings-21 carrier), 2026-09-19,
    # owner decisions 48 and 50: the knowledge INDEX is
    # armed in the config and RENDERED from a flight-owned binding, exactly
    # as E14's solver hints and E18's acquisition re-query are. The binding
    # is not built yet -- that is the index cell's own step -- so an armed
    # key must STOP the flight here rather than let a row fly whose config
    # hash claims an index its request bytes do not carry. Fail-closed, by
    # name, and unreachable for every config that does not arm the key.
    if config.knowledge_index_json is not None and binding.knowledge_index is None:
        raise RailsRunnerError(
            "native_episode.knowledge_index is armed but the episode binding "
            "carries no knowledge-index binding; an armed key with no renderer "
            "would compose a config hash that claims an index the request bytes "
            "do not carry"
        )
    # E21w: and the other direction. A binding with no armed key would render
    # an index no config hash claims, which is the same defect seen from the
    # other side; both are refused by name before any contact.
    if config.knowledge_index_json is None and binding.knowledge_index is not None:
        raise RailsRunnerError(
            "the episode binding carries a knowledge-index binding but "
            "native_episode.knowledge_index is not armed; an index no config "
            "hash claims would move request bytes outside the cell identity"
        )
    # Item E42 (2026-09-25): the arm group and its resolver are ONE module, in
    # both directions -- a declared group with no resolver would compose an arm
    # from nothing, and a resolver with no declared group would move request
    # bytes no config hash claims. Both are refused by name before any contact,
    # exactly as E21w's index binding is just above.
    if (
        supply_variant_group is not None and not template_variant_mode
        and binding.supply_variant_for_phase is None
    ):
        raise RailsRunnerError(
            "roles.solver.supply_variants is declared but the episode binding "
            "carries no supply_variant_for_phase resolver; an arm's own supply is "
            "flight-owned, exactly as supply_for_phase is"
        )
    if (
        supply_variant_group is None or template_variant_mode
    ) and binding.supply_variant_for_phase is not None:
        raise RailsRunnerError(
            "the episode binding carries a supply_variant_for_phase resolver but "
            "roles.solver.supply_variants is not declared; an arm no config hash "
            "claims would move request bytes outside the cell identity"
        )
    # NX programme E1: a template group and its per-arm material builders are
    # ONE module in both directions, exactly as the supply resolver above is.
    declared_template_arms = {
        arm.arm_id for arm in (supply_variant_group.arms if template_variant_mode else ())
        if arm.instruction_template is not None
    } | {
        branch.branch_id
        for branch in (perception_branch_group.branches if perception_template_mode else ())
        if branch.instruction_template is not None
    }
    if set(binding.template_variant_materials or {}) != declared_template_arms:
        raise RailsRunnerError(
            "the episode binding's template_variant_materials "
            f"{sorted(binding.template_variant_materials or {})} differ from the "
            f"template arms roles.solver.template_variants declares "
            f"{sorted(declared_template_arms)}; an instruction no config hash "
            "claims would move request bytes outside the cell identity"
        )
    # LEVEL 2 render-defect fix (2026-10-09): the branch Solver supply resolver
    # and the level-2 branch group are ONE module in both directions (the
    # same rule as the arm resolver above). A level-2 group beside a Solver
    # supply with NO resolver would render every branch Solver column over
    # A's supply -- the defect this seam closes -- so it is refused by name.
    level2_group = (
        perception_branch_group is not None
        and perception_branch_group.level == PERCEPTION_BRANCH_LEVEL_SOLVER
    )
    if (
        level2_group and binding.supply_for_phase is not None
        and binding.perception_branch_solver_supply is None
    ):
        raise RailsRunnerError(
            "roles.perception.branches declares level 2 beside a Solver supply but "
            "the episode binding carries no perception_branch_solver_supply "
            "resolver; every branch Solver column would render A's supply"
        )
    if not level2_group and binding.perception_branch_solver_supply is not None:
        raise RailsRunnerError(
            "the episode binding carries a perception_branch_solver_supply resolver "
            "but no level-2 roles.perception.branches group is declared; a supply no "
            "config hash claims would move request bytes outside the cell identity"
        )
    if level2_group and getattr(binding.supply_for_phase, "candidate_proposal_for_context", None) is not None:
        raise RailsRunnerError(
            "level-2 perception branches cannot combine with a candidate proposal: "
            "a branch's proposal would have to be re-derived from its own note"
        )
    expected_proposal = getattr(binding.supply_for_phase, "candidate_proposal_for_context", None)
    if binding.candidate_proposal_for_context != expected_proposal:
        raise RailsRunnerError("candidate proposal consumption differs from its supply binding")
    if expected_proposal is not None:
        if any((
            config.role_context_json is not None, config.context_policy_json is not None,
            config.reviewer_audit_json is not None, config.knowledge_index_json is not None,
            config.solver_hints_json is not None, config.context_fit_policy == "compact-or-abstain",
            supply_variant_group is not None, acquisition_policy is not None,
            config.max_candidate_refreshes != 0, grouped_solver_phase_id is not None,
            binding.system_episode_policy is not None,
        )):
            raise RailsRunnerError("candidate proposal cannot combine with another context transformation")
    knowledge_index = binding.knowledge_index
    #: E21w, per contact: the assembly this contact was composed from, the
    #: system message it carried, and where the row's selection came from.
    index_contacts: dict[str, dict] = {}
    #: E21w, per contact: the index degradation steps a dispatch-time
    #: compaction spent, in the order it spent them. Never silent.
    index_degradation: dict[str, list] = {}
    #: E21w: one receipt row per contact, in contact order.
    knowledge_index_records: list[dict] = []
    #: One row per contact, in contact order: the contact it describes and
    #: either its compaction record or ``None`` for a request that fitted.
    context_fit_records: list[dict[str, object]] = []

    def _context_attachments(contact_id):
        """The addressable scenario-hints / reviewer-audit blocks of ONE contact.

        Read from this contact's own node-context compilation receipt,
        which records each appended block's sha256 and character count (the
        policy never records its text). That is exactly enough to remove the
        block byte for byte and to refuse to remove anything else.
        """

        record = node_context_compilations.get(contact_id)
        if record is None:
            return ()
        rows = record.get("compilation", {}).get("boundaries", ())
        attachments = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            state_id = row.get("rendered_state_id")
            if not isinstance(state_id, str) or not state_id:
                continue
            for key, block in (
                ("solver_hints", SCENARIO_HINTS_BLOCK),
                ("slot_audit", REVIEWER_AUDIT_BLOCK),
            ):
                entry = row.get(key)
                if (
                    not isinstance(entry, Mapping)
                    or entry.get("applied") is not True
                    or not isinstance(entry.get("block_sha256"), str)
                    or not isinstance(entry.get("block_chars"), int)
                    or isinstance(entry.get("block_chars"), bool)
                    or entry["block_chars"] <= 0
                ):
                    continue
                attachments.append(BlockAttachment(
                    state_id=state_id, block=block,
                    chars=entry["block_chars"], sha256=entry["block_sha256"],
                ))
        return tuple(attachments)

    def _context_view(speech_binding_value, attachments, contact_id=None):
        messages = speech_binding_value.messages()
        kwargs = speech_binding_value.kwargs()
        content = messages[1].get("content")
        states = kwargs.get("agent_state")
        record = index_contacts.get(contact_id) if contact_id else None
        return CompactableRequest(
            content=tuple(content if isinstance(content, list) else ()),
            agent_states=tuple(states if isinstance(states, list) else ()),
            attachments=attachments,
            # E21w: the index's own ladder replaces E20's ``exemplar-supply``
            # ladder for exactly the parts the index authored, so ONE caller
            # drives both through ``rails.context_fit.apply_drops``. None --
            # and therefore E20's pre-E21 behaviour -- on every unarmed row.
            index_assembly=None if record is None else record["assembly"],
        )

    def _narrowed_binding(speech_binding_value, view):
        messages = speech_binding_value.messages()
        messages[1] = {**messages[1], "content": [dict(part) for part in view.content]}
        kwargs = speech_binding_value.kwargs()
        kwargs["agent_state"] = [dict(entry) for entry in view.agent_states]
        return replace(
            speech_binding_value, base_messages=tuple(messages), core_kwargs=kwargs
        )

    def fit_contact_to_slot(request, prepared):
        """Budget the REALISED request against the LIVE slot before sending it.

        Returns the contact to dispatch -- the one handed in when it already
        fits, or a re-prepared one composed over the same binding with the
        declared droppable blocks removed. Raises
        :class:`FrozenCoreRoleContextFitError` when two compaction passes
        are not enough, which the episode graph turns into a retained row.
        """

        if context_fit_budget is None:
            return prepared, None
        source_binding = prepared.binding
        if not isinstance(source_binding, NativeRoleSpeechBinding):
            raise RailsRunnerError("a context-fit check needs its prepared binding")
        attachments = _context_attachments(request.context.agent_contact_id)
        base_view = _context_view(
            source_binding, attachments, request.context.agent_contact_id,
        )
        limit = context_fit_budget.prompt_limit_tokens
        cache: dict[bytes, tuple[object, int]] = {}

        def key(view):
            return canonical_bytes(view.document())

        cache[key(base_view)] = (
            prepared, int(context_fit_budget.token_counter(prepared.body_bytes))
        )

        def measure(view):
            view_key = key(view)
            if view_key not in cache:
                candidate = adapter_request.prepare(
                    request, binding_override=_narrowed_binding(source_binding, view)
                )
                cache[view_key] = (
                    candidate,
                    int(context_fit_budget.token_counter(candidate.body_bytes)),
                )
            return cache[view_key][1]

        outcome = compact_to_fit(base_view, measure=measure, limit_tokens=limit)
        if not outcome.fitted:
            raise FrozenCoreRoleContextFitError(
                source="dispatch-budget",
                compaction_pass=outcome.passes,
                dropped_identifiers=outcome.dropped_identifiers(),
                tokens_before=outcome.tokens_before,
                tokens_after=outcome.tokens_after,
                limit_tokens=limit,
            )
        if outcome.passes == 0:
            return prepared, None
        _record_index_degradation(request.context.agent_contact_id, outcome)
        return cache[key(outcome.request)][0], outcome

    def _record_index_degradation(contact_id, outcome):
        """E21w: every index step a compaction spent, recorded, never silent.

        The honesty requirement owner decision 45 states for the serving
        side: an index block that left the request is a row disposition, not
        an invisible saving. The assembly is narrowed to what was actually
        sent so the receipt's ``expanded_ids`` name the bytes the model read.
        """

        record = index_contacts.get(contact_id)
        if record is None:
            return
        from .knowledge_index import (  # noqa: PLC0415
            INDEX_DROP_ORDER, degradation_step, narrow_assembly,
        )

        steps = [
            degradation_step(item, pass_index=outcome.passes)
            for item in outcome.dropped if item.block in INDEX_DROP_ORDER
        ]
        if not steps:
            return
        index_degradation.setdefault(contact_id, []).extend(steps)
        record["assembly"] = narrow_assembly(
            record["assembly"], outcome.dropped_identifiers()
        )

    async def metered(request):
        def contact(slot_id):
            if state.scheduled_contacts >= config.max_contacts:
                raise RailsRunnerError("native graph exceeds its registered contact ceiling")
            if request.context.agent_contact_id in state.seen_contact_ids:
                raise RailsRunnerError("native graph repeated a contact identity")
            state.seen_contact_ids.add(request.context.agent_contact_id)
            trace = TraceBuffer(run_id, spool=state.trace_spool)
            state.trace_buffers[(state.scheduled_contacts, 0)] = trace
            state.scheduled_contacts += 1
            visits[request.role_id]["slot_id"] = slot_id
            set_current_trace_buffer(trace)
            try:
                prepared = adapter_request.prepare(request)
                prepared, compaction = fit_contact_to_slot(request, prepared)
                if context_fit_budget is not None:
                    context_fit_records.append({
                        "contact_id": request.context.agent_contact_id,
                        "role_id": request.role_id,
                        "context_compaction": (
                            None if compaction is None else compaction.record()
                        ),
                    })
                binding.request_gate(prepared.request)
                try:
                    completion = adapter_request.dispatch(prepared)
                except FrozenCoreContextSizeError as error:
                    # E20: the fork refused the request for width after the
                    # harness budgeted it as fitting. Under the armed policy
                    # this is the SAME retained-row disposition; under
                    # ``"raise"`` it propagates exactly as it always did.
                    if context_fit_budget is None:
                        raise
                    raise FrozenCoreRoleContextFitError(
                        source="server-refusal",
                        compaction_pass=0 if compaction is None else compaction.passes,
                        dropped_identifiers=(
                            () if compaction is None
                            else compaction.dropped_identifiers()
                        ),
                        tokens_before=(
                            0 if compaction is None else compaction.tokens_before
                        ),
                        tokens_after=(
                            0 if compaction is None else compaction.tokens_after
                        ),
                        limit_tokens=context_fit_budget.prompt_limit_tokens,
                        server_message=(
                            error.server_message or "exceed_context_size_error"
                        ),
                    ) from error
                trace.emit("USE", f"{completion.request_id}/native-role-contact", {
                    "use_role_id": request.role_id,
                    "use_request_sha256": completion.request_sha256,
                    "use_response_sha256": completion.response_sha256,
                    "use_response_text_sha256": completion.response_text_sha256,
                    "use_agent_contact_id": completion.agent_contact_id,
                })
                return completion
            finally:
                set_current_trace_buffer(None)
        options = {"prefix_family": request.role_id} if binding.prefix_slots is not None or binding.node_batch is not None or binding.node_pipeline is not None else {}
        return await run_contact(contact, **options)

    def reject_tool_batch(phase_id, assistant_message):
        from ..reproduction.ojw.native_roles import restore_native_assistant_wire_message

        if not pending or pending["phase_id"] != phase_id:
            raise RailsRunnerError("rejected batch has no pending source completion")
        completion, source, before = (
            pending[name] for name in ("completion", "source", "context")
        )
        restore_native_assistant_wire_message(assistant_message, completion=completion)
        staged = replace(
            before, agent_states=before.agent_states + (source,),
            prior_response_sha256s=before.prior_response_sha256s + (completion.response_text_sha256,),
            core_completions=(completion,),
        )
        steps = binding.tools_for_phase.reject_native_batch(phase_id, staged)
        messages = tuple(native_tool_result_message(json.loads(step.state.content)) for step in steps)
        settle(rejected_steps=steps)
        visits[phase_id]["local_ids"].extend(step.state.state_id for step in steps)
        return messages

    def ability_for(role, schema):
        function = schema["function"]
        async def execute_arguments(arguments, *, invalid_arguments=False):
            def execute(_slot_id):
                if not pending or pending["phase_id"] != role.phase_id:
                    raise RailsRunnerError("tool has no pending completion for this role")
                completion = pending["completion"]
                calls = completion.tool_calls
                if len(calls) != 1:
                    raise RailsRunnerError("native role supports one analytical action per contact")
                call = calls[0]
                if (
                    call["function"]["name"] != function["name"]
                    or content_hash(json.loads(call["function"]["arguments"])) != content_hash(arguments)
                ):
                    raise RailsRunnerError("framework tool action differs from the frozen source")
                before, source = pending["context"], pending["source"]
                staged = replace(
                    before, agent_states=before.agent_states + (source,),
                    prior_response_sha256s=before.prior_response_sha256s + (completion.response_text_sha256,),
                    core_completions=(completion,),
                )
                if invalid_arguments:
                    steps = binding.tools_for_phase.reject_native_batch(
                        role.phase_id, staged, invalid_arguments=True,
                    )
                    step, = steps
                    message = native_tool_result_message(json.loads(step.state.content))
                    settle(rejected_steps=steps)
                    visits[role.phase_id]["local_ids"].append(step.state.state_id)
                    return message["content"]
                step = binding.tools_for_phase(role.phase_id, role.phase_id, staged)
                if step is None:
                    raise RailsRunnerError("analytical action has no counted observation")
                step.validate()
                document = json.loads(step.state.content)
                message = native_tool_result_message(document)
                settle(tool_step=step)
                visits[role.phase_id]["local_ids"].append(step.state.state_id)
                return message["content"]
            if run_local is not None:
                return await run_local(lambda: execute(None))
            options = {"prefix_family": role.phase_id} if binding.prefix_slots is not None or binding.node_batch is not None or binding.node_pipeline is not None else {}
            if binding.node_batch is not None or binding.node_pipeline is not None:
                options["contact_kind"] = "tool"
            return await run_contact(execute, **options)
        async def invoke(**arguments):
            return await execute_arguments(arguments)

        async def invalid_arguments(arguments):
            return await execute_arguments(arguments, invalid_arguments=True)

        return NativeSourceFunction(
            card=ToolCard(id=function["name"], name=function["name"],
                          description=function.get("description", ""),
                          input_params=function["parameters"]),
            func=invoke, invalid_arguments=invalid_arguments,
        )

    schema_by_name = {}
    if binding.tools_for_phase is not None:
        schema_by_name = {
            row["function"]["name"]: row
            for row in binding.tools_for_phase.native_tool_schemas()
        }
    prompt = base_messages(context())[0]["content"]
    nodes = {}
    try:
        for role in config.roles:
            if role.max_iterations == 0:
                # The review loop is off by configuration: Reviewer/Planner
                # never get a node, so they can never be contacted -- there
                # is no NativeRoleNode for them anywhere in this graph.
                continue

            def contact_context(index, role=role):
                kwargs = dict(
                    sample_id=state.prepared.sample.sample_id,
                    agent_contact_id=scoped_execution_contact_id(
                        f"{program.program_id}:{role.phase_id}:{index}:{state.prepared.sample.sample_id}",
                        state.prepared.execution_unit_id,
                    ),
                    evidence_pins={"knowledge_snapshot": snapshot_sha256},
                    budget_id=run_id,
                )
                if role.role_kind == "solver" and role.samples > 1:
                    # E2b: this node's own invocation index is GLOBAL across
                    # the whole episode (every revision's Solver visit), so
                    # it counts up in exact multiples of one grouped visit's
                    # sample count -- the same mapping
                    # rails.native_episode_receipt.validate_solver_group_receipt
                    # expects (sample_index ascending from 0 within a group).
                    kwargs["sample_index"] = index % role.samples
                if role.supply_variants is not None:
                    # Item E42: the SAME mapping E2b uses for its samples -- the
                    # node's own invocation index is GLOBAL across the whole
                    # episode (every revision's visit), so it counts up in exact
                    # multiples of one visit's arm count and
                    # ``rails.native_episode_receipt.
                    # validate_supply_variant_receipt`` sees the arms in their
                    # declared order, ascending from the first, within a group.
                    #
                    # Item E42b (owner decision 172, merge set B): under
                    # ``arm_visits: "first"`` this mapping covers ONLY the
                    # visit whose global contact indices are 0..arm_count-1;
                    # every later contact leaves ``variant_arm_id`` at its
                    # default ``None`` -- the ordinary, unarmed contact path
                    # (``request.context.variant_arm_id is not None`` below,
                    # ``speech_binding``) -- which is what makes a revisit
                    # contact the delivering arm alone, through no arm-scoped
                    # view of any kind. Byte-identical to before for the
                    # default "every", which never reaches this branch.
                    variant_group = role.supply_variants
                    if not (
                        variant_group.arm_visits == "first"
                        and index >= variant_group.arm_count
                    ):
                        kwargs["variant_arm_id"] = variant_group.arm_ids[
                            index % variant_group.arm_count
                        ]
                if role.perception_branches is not None:
                    # Same-flight instrument, PHASE 2 (merge set C): the same
                    # mapping E42's arm route uses, simplified by the ONE
                    # mechanical fact design section 3 ("Branch visits")
                    # states -- Perception has exactly ONE visit per row
                    # (max_iterations 1, no refresh), so there is no
                    # "first"/"every" choice to make: EVERY invocation of
                    # this node fans out to every declared branch, in order.
                    branch_group = role.perception_branches
                    if sampling_perception_slots is not None:
                        # Decision 338: one slot per contact -- k consecutive slots for a ``perception_samples`` branch.
                        slot_branch, slot_sample = sampling_perception_slots[
                            index % len(sampling_perception_slots)
                        ]
                        kwargs["perception_branch_id"] = branch_group.branch_ids[slot_branch]
                        kwargs["sample_index"] = slot_sample
                    else:
                        kwargs["perception_branch_id"] = branch_group.branch_ids[
                            index % branch_group.branch_count
                        ]
                if (
                    role.role_kind == "solver"
                    and perception_branch_group is not None
                    and perception_branch_group.level == PERCEPTION_BRANCH_LEVEL_SOLVER
                ):
                    # LEVEL 2 (merge set C item 1, design section 3, "Level
                    # 2"): forced ``arm_visits: "first"`` (there is no config
                    # knob for it, unlike the Solver's own supply-variant
                    # route) -- ONLY the Solver's global contact indices
                    # 0..branch_count-1 (its first visit) carry a branch id,
                    # A's own included (the SAME convention the supply-variant
                    # arm route uses for its own delivering arm); every later
                    # contact (a Planner REVISE route back to the Solver)
                    # leaves ``perception_branch_id`` at its default ``None``
                    # -- the ordinary, unbranched contact path, which is what
                    # makes a revisit contact branch A alone.
                    if sampling_solver_slots is not None:
                        # Decision 338: one slot per first-visit Solver contact -- n consecutive slots for a
                        # ``solver_samples`` branch, one for every other branch.
                        if index < len(sampling_solver_slots):
                            slot_branch, slot_sample = sampling_solver_slots[index]
                            kwargs["perception_branch_id"] = perception_branch_group.branch_ids[slot_branch]
                            kwargs["sample_index"] = slot_sample
                    elif index < perception_branch_group.branch_count:
                        kwargs["perception_branch_id"] = (
                            perception_branch_group.branch_ids[index]
                        )
                return NativeRoleContactContext(**kwargs)
            def role_delivery_allowed(_role: str, output: str) -> bool:
                return isinstance(output, str) and bool(output.strip())
            solver_node = NativeRoleNode(
                spec=NativeRoleNodeSpec(
                    role_id=role.phase_id, role_kind=role.role_kind, prompt=prompt,
                    max_iterations=role.max_iterations, ability_names=role.tool_names,
                    reserve_final_report=config.reserve_final_report and bool(role.tool_names),
                    solver_tool_access=(config.solver_tool_access if role.role_kind == "solver" else None),
                    # Item E39 (2026-09-22): under ``answering-node`` scope a
                    # NON-answering role keeps its truncated text and the
                    # episode continues to the node that does answer. False
                    # for the Solver always, and for every role of every
                    # config written before E39.
                    tolerate_length_truncation=(
                        config.finite_completion_scope == "answering-node"
                        and role.role_kind != "solver"
                    ),
                ),
                metered_request=metered, contact_context_provider=contact_context,
                reject_tool_batch=reject_tool_batch if role.tool_names else None,
                abilities=tuple(ability_for(role, schema_by_name[name]) for name in role.tool_names),
                tool_allowed=(
                    (lambda phase, name, role=role: phase == role.phase_id and name in role.tool_names)
                    if role.role_kind in {"reviewer", "planner"} or (
                        role.role_kind == "solver" and config.solver_tool_access is not None
                    ) else None
                ),
                delivery_allowed=role_delivery_allowed,
            )
            if role.role_kind == "solver" and role.samples > 1:
                # E2b: the grouped Solver visit -- N real invoke_direct
                # calls on the SAME solver_node above, through the SAME
                # metered request path, aggregated by the registered commit
                # policy. Every other role (and a samples-1 Solver) keeps
                # the plain node unwrapped, byte-identical to before.
                nodes[role.role_kind] = GroupedSolverRoleNode(
                    inner=solver_node, samples=role.samples,
                    fragment_seed=solver_fragment_seed,
                    decoding_overrides=role.decoding_overrides, commit=role.commit,
                    delivery_allowed=role_delivery_allowed,
                    # E2c: the committed answer is the reviewed draft.
                    on_commit=record_solver_commit,
                )
            elif role.supply_variants is not None:
                # Item E42: the arm-grouped Solver visit -- K real
                # invoke_direct calls on the SAME solver_node above, through
                # the SAME metered request path, each composed over its own
                # declared knowledge construction by the binding provider, the
                # LAST one delivered. Every other role keeps the plain node
                # unwrapped, byte-identical to before.
                from ..reproduction.ojw.native_supply_variants import (
                    SupplyVariantRoleNode,
                )

                nodes[role.role_kind] = SupplyVariantRoleNode(
                    inner=solver_node, group=role.supply_variants,
                    arm_record=read_supply_variant_arm_record,
                    delivery_allowed=role_delivery_allowed,
                    # NX programme E1: a template arm's framework query is its
                    # own instruction; None for the supply kind.
                    query_for_arm=(
                        template_arm_query if template_variant_mode else None
                    ),
                )
            elif (
                role.role_kind == "solver"
                and perception_branch_group is not None
                and perception_branch_group.level == PERCEPTION_BRANCH_LEVEL_SOLVER
            ):
                # LEVEL 2 (merge set C item 1, design section 3, "Level 2"):
                # the Solver's own first-visit branch fan-out -- K real
                # invoke_direct calls on the SAME solver_node above, through
                # the SAME metered request path, one per declared Perception
                # branch, A's (last, override-free) own answer delivered.
                # Refused beside ``role.supply_variants`` at config-parse
                # time (``roles.perception.branches`` cannot combine with
                # ``roles.solver.supply_variants``), so this ``elif`` and the
                # one above are mutually exclusive in practice. Every other
                # role keeps the plain node unwrapped, byte-identical to
                # before.
                from ..reproduction.ojw.native_supply_variants import (
                    PerceptionBranchSolverRoleNode,
                )

                nodes[role.role_kind] = PerceptionBranchSolverRoleNode(
                    inner=solver_node, group=perception_branch_group,
                    branch_record=read_perception_branch_solver_record,
                    delivery_allowed=role_delivery_allowed,
                    # NX-T R1 seal fix: a NON-delivering branch's finite
                    # completion is recorded as an absent column instead of
                    # ending the row (and the flight).
                    branch_absent=read_perception_branch_solver_absent,
                )
            elif role.perception_branches is not None:
                # Same-flight instrument, PHASE 2 (merge set C): the
                # branched Perception visit -- K real invoke_direct calls on
                # the SAME solver_node (here, the Perception node) above,
                # through the SAME metered request path, each composed over
                # its own declared axis by the binding provider, branch A's
                # (last, override-free) own answer delivered. Every other
                # role keeps the plain node unwrapped, byte-identical to
                # before.
                from ..reproduction.ojw.native_supply_variants import (
                    PerceptionBranchRoleNode,
                )

                nodes[role.role_kind] = PerceptionBranchRoleNode(
                    inner=solver_node, group=role.perception_branches,
                    branch_record=read_perception_branch_record,
                    delivery_allowed=role_delivery_allowed,
                    # NX programme E1, Perception node: a template branch's
                    # framework query is its own instruction.
                    query_for_branch=(
                        perception_template_query if perception_template_mode else None
                    ),
                )
            else:
                nodes[role.role_kind] = solver_node
        if acquisition_policy is not None:
            from ..reproduction.ojw.native_episode import (
                AcquisitionNode, AcquisitionNodeSpec,
            )
            from .acquisition import (
                AcquiredItem, AcquisitionError, AcquisitionRequest,
                derive_state_filters, supplied_value_ids,
            )

            acquisition_phase_id = acquisition_role_config.phase_id

            def acquisition_contact_context(index):
                return NativeRoleContactContext(
                    sample_id=state.prepared.sample.sample_id,
                    agent_contact_id=scoped_execution_contact_id(
                        f"{program.program_id}:{acquisition_phase_id}:{index}:"
                        f"{state.prepared.sample.sample_id}",
                        state.prepared.execution_unit_id,
                    ),
                    evidence_pins={"knowledge_snapshot": snapshot_sha256},
                    budget_id=run_id,
                )

            reobserve_node = None
            if acquisition_role_config.max_iterations:
                # E18 kind (b): the re-observation seat. It is a PERCEPTION
                # role node -- same node class, same metered path, same
                # authority rails, and (by the fragment's own
                # ``phase_material``) the same never-varied Perception
                # instruction template -- placed at the acquisition phase so
                # its contact is budgeted, traced and sealed as that phase's.
                # No new prompt text is introduced anywhere by E18.
                reobserve_node = NativeRoleNode(
                    spec=NativeRoleNodeSpec(
                        role_id=acquisition_phase_id, role_kind="perception",
                        prompt=prompt,
                        max_iterations=acquisition_role_config.max_iterations,
                        # Item E39: the re-observation seat is a Perception
                        # role and answers nothing, so it takes exactly the
                        # same tolerance the Perception node takes.
                        tolerate_length_truncation=(
                            config.finite_completion_scope == "answering-node"
                        ),
                    ),
                    metered_request=metered,
                    contact_context_provider=acquisition_contact_context,
                    delivery_allowed=(
                        lambda _role, output: isinstance(output, str)
                        and bool(output.strip())
                    ),
                )
                extra_nodes.append(reobserve_node)

            def acquisition_requery(*, filters, exclude_value_ids, scope):
                """Kind (a): the flight's own model-free knowledge re-query.

                Flight-owned exactly as ``supply_for_phase`` and
                ``tools_for_phase`` are: this runner never reaches for a
                store of its own, and an episode that arms the knowledge kind
                without binding the callback is refused here by name rather
                than acquiring nothing and calling it an acquisition.
                """

                requery = getattr(binding, "acquisition_requery", None)
                if requery is None:
                    raise RailsRunnerError(
                        "the knowledge re-query acquisition requires an "
                        "acquisition_requery binding"
                    )
                return requery(
                    phase_id=config.role("solver").phase_id,
                    filters=tuple(filters),
                    exclude_value_ids=frozenset(exclude_value_ids),
                    scope=dict(scope),
                    context=context(),
                )

            async def acquisition_reobserve(*, scope):
                """Kind (b): ONE re-scoped Perception contact at this seat."""

                if reobserve_node is None:
                    raise RailsRunnerError(
                        "a contact-spending acquisition has no re-observation node"
                    )
                query = role_input(acquisition_phase_id, acquisition_state)
                result = await reobserve_node.invoke_direct(query)
                if (
                    not isinstance(result, Mapping)
                    or result.get("result_type") != "answer"
                    or not isinstance(result.get("actor_output"), str)
                    or not result["actor_output"].strip()
                ):
                    raise RailsRunnerError(
                        "the re-observation acquisition returned no observation"
                    )
                acquisition_results.append(result)
                return AcquiredItem(
                    evidence_id=pending["plan"].contact_id,
                    source_id=acquisition_phase_id,
                    content=result["actor_output"],
                )

            acquisition_state: dict[str, object] = {}
            acquisition_results: list[Mapping[str, object]] = []

            async def run_acquisition(episode_state):
                nonlocal acquisition_contacts

                acquisition_state.clear()
                acquisition_state.update(episode_state)
                acquisition_results.clear()
                routes = episode_state.get("planner_routes") or []
                request = AcquisitionRequest(
                    policy_id=acquisition_policy.policy_id,
                    kind=acquisition_policy.kind,
                    sample_id=state.prepared.sample.sample_id,
                    visit_index=len(acquisition_records),
                    revision_count=int(episode_state["revision_count"]),
                    planner_route_index=max(len(routes) - 1, 0),
                    planner_action=config.actions[2],
                    state_filters=derive_state_filters(episode_state),
                    # The dedupe set: exactly the knowledge values this
                    # trajectory has already been supplied. An acquisition
                    # that returned one of them would spend a revision to
                    # change nothing.
                    supplied_value_ids=supplied_value_ids({
                        "supplied_value_ids": list(
                            state.query_state.retrieved_value_ids
                        ),
                    }),
                    budget=acquisition_budget,
                    contacts_used=acquisition_contacts,
                    scope=dict(acquisition_scope),
                    requery=acquisition_requery,
                    reobserve=acquisition_reobserve,
                )
                try:
                    evidence = await acquisition_policy(
                        request, template=acquisition_template,
                    )
                except AcquisitionError as error:
                    raise RailsRunnerError(f"acquisition refused: {error}") from error
                if not pending:
                    raise RailsRunnerError(
                        "an acquisition lost the contact that authorised it"
                    )
                before, completion, plan = (
                    pending["context"], pending["completion"], pending["plan"],
                )
                if evidence.contacts_used:
                    # Kind (b): the acquisition's OWN contact is the pending
                    # one. Re-seal its state as a VIEW of the re-observation
                    # -- the typed block as content, the model's own bytes as
                    # the source -- through the same
                    # ``seal_phase_response_state`` seam a grouped Solver
                    # visit uses, so the state the Solver reads is typed and
                    # the response it binds is real.
                    acquisition_contacts += evidence.contacts_used
                    pending["source"] = seal_phase_response_state(
                        phase_name=acquisition_phase_id,
                        sample_id=before.sample_id,
                        state_content=evidence.content,
                        raw_response_text=completion.text,
                        source_query_state_sha256=before.query_state.content_hash(),
                        producer_policy_id=program.program_id,
                        state_namespace=plan.contact_id,
                    )
                else:
                    # Kind (a) and kind (c): zero contacts, so the typed state
                    # is bound to the Planner completion that authorised it
                    # and rides that contact's settle.
                    acquired_states.append(seal_phase_response_state(
                        phase_name=acquisition_phase_id,
                        sample_id=before.sample_id,
                        state_content=evidence.content,
                        raw_response_text=completion.text,
                        source_query_state_sha256=before.query_state.content_hash(),
                        producer_policy_id=program.program_id,
                        state_namespace=(
                            f"{plan.contact_id}:acquisition:{len(acquisition_records)}"
                        ),
                    ))
                record = evidence.receipt(
                    visit_index=request.visit_index,
                    revision_count=request.revision_count,
                    planner_route_index=request.planner_route_index,
                    planner_action=request.planner_action,
                    state_filters=list(request.state_filters),
                )
                acquisition_records.append(dict(record))
                if acquisition_results:
                    record = dict(record)
                    record["execution_receipt"] = acquisition_results[0][
                        "execution_receipt"
                    ]
                return record

            # The declared re-scope of this node. E18 introduces NO prompt
            # text: a kind (b) re-observation is re-scoped through the
            # acquisition phase's OWN ``phase_material`` (the never-varied
            # Perception template plus that phase's ``fill_params``), so what
            # travels in the request here is the node's identity and the
            # kinds it may execute -- enough to make ``inputs_sha256``
            # re-derivable, and nothing a policy could mistake for content.
            acquisition_scope = {
                "phase_id": acquisition_phase_id,
                "kinds": list(acquisition_role_config.acquisition_kinds),
            }
            nodes["acquisition"] = AcquisitionNode(
                spec=AcquisitionNodeSpec(
                    node_id=acquisition_phase_id,
                    policy_id=acquisition_policy.policy_id,
                    kind=acquisition_policy.kind,
                ),
                execute=run_acquisition,
            )
        workflow = build_native_episode(
            spec=NativeEpisodeSpec(
                config.episode_id,
                config.max_revisions,
                NativeEpisodeActions(*config.actions),
                config.exhaustion_policy,
                config.refresh_action,
                config.max_candidate_refreshes,
                config.finite_completion_policy,
                config.planner_output_format,
                config.review_loop_enabled,
                config.max_acquisitions_per_row,
                # E20: keyword, because the spec's own field is last and
                # every positional argument above is the pre-E20 order.
                context_fit_policy=config.context_fit_policy,
                # E22: keyword for the same reason.
                react_exhaustion_policy=config.react_exhaustion_policy,
                # E37: keyword for the same reason.
                reviewer_verdict_vocabulary=config.reviewer_verdict_vocabulary,
                # E39: keyword for the same reason.
                finite_completion_scope=config.finite_completion_scope,
            ),
            nodes=NativeEpisodeNodes(**nodes),
            role_input_builder=(
                role_input if role_input_runner is None
                # Owner decision 159 (``role_input_offload``): the SAME
                # builder, awaited off the shared event loop.
                else (lambda phase_id, episode_state: role_input_runner(
                    role_input, phase_id, episode_state
                ))
            ),
        )
        result = await workflow.invoke_direct(state.prepared.task_contract, (), session=session)
        receipt = result["state"]
        from .native_episode_receipt import (
            validate_native_episode_delivery_receipt, validate_native_episode_finite_path,
            validate_native_episode_terminal_policy,
            validate_native_episode_truncation_scope,
        )

        # Item E39 (2026-09-22): a row may only survive a truncated auxiliary
        # node under a scope declared before the flight. Reads nothing and
        # refuses nothing on a row that carries no truncation, which is every
        # row of every cell written before E39.
        validate_native_episode_truncation_scope(
            receipt,
            finite_completion_scope=config.finite_completion_scope,
            error_type=RailsRunnerError,
        )
        raw_disposition = receipt.get("terminal_disposition")
        finite = (
            isinstance(raw_disposition, Mapping)
            and raw_disposition.get("reason") == "finite_completion"
        )
        # E20: a context-fit row quarantines NO completion -- the refused
        # request never reached the wire, or the wire refused it -- so it
        # takes neither the finite branch's custody check nor its wave
        # record. It settles exactly as an ordinary row does.
        context_degraded = (
            isinstance(raw_disposition, Mapping)
            and raw_disposition.get("reason") == CONTEXT_COMPACTION_DISPOSITION
        )
        # E43: the seal refused this row's deciding completion inside
        # ``capture_completion``, before either ``pending`` or ``completed``
        # ever recorded it -- there is no quarantined completion here to
        # cross-check, unlike a finite completion's (whose sink runs to
        # completion and only the LATER wire-turn projection refuses it).
        seal_refused = (
            isinstance(raw_disposition, Mapping)
            and raw_disposition.get("reason") == SEAL_REFUSAL_DISPOSITION
        )
        if context_degraded and config.context_fit_policy != "compact-or-abstain":
            raise RailsRunnerError(
                "context-fit disposition without its declared policy"
            )
        if seal_refused and config.finite_completion_policy != "deliver-latest-or-abstain":
            raise RailsRunnerError(
                "seal-refusal disposition without its declared policy"
            )
        if finite:
            if not pending:
                raise RailsRunnerError("finite episode lost its quarantined model completion")
            rejected = raw_disposition.get("rejected_contact")
            completion = pending["completion"]
            if (
                not isinstance(rejected, Mapping)
                or any(getattr(completion, key) != rejected.get(key) for key in (
                    "agent_contact_id", "request_id", "request_sha256",
                    "response_sha256", "response_text_sha256",
                ))
                or completion.finish_reason != raw_disposition.get("finish_reason")
                or pending["phase_id"] != raw_disposition.get("role_id")
                or config.finite_completion_policy != "deliver-latest-or-abstain"
            ):
                raise RailsRunnerError("finite episode disposition differs from its actual source")
        elif seal_refused:
            # E43: nothing here to settle or quarantine -- the receipt's own
            # ``rejected_contact``/``interrupted_role`` are the only source
            # of truth, and ``native_episode._seal_refusal_terminal_outcome``
            # already bound them to their invocation-local role checkpoint.
            pass
        else:
            settle()

        delivery = validate_native_episode_delivery_receipt(
            receipt, terminal_actions=config.terminal_actions, error_type=RailsRunnerError,
        )
        if config.refresh_action is not None:
            from .native_episode_receipt import validate_native_candidate_refresh_receipt

            validate_native_candidate_refresh_receipt(
                receipt, refresh_action=config.refresh_action,
                max_refreshes=config.max_candidate_refreshes, max_revisions=config.max_revisions,
                accept_action=config.actions[0], revise_action=config.actions[1],
                error_type=RailsRunnerError,
            )
        final_solver_receipt = delivery.solver_receipt
        terminal_disposition = delivery.terminal_disposition
        validate_native_episode_terminal_policy(
            delivery, exhaustion_policy=config.exhaustion_policy,
            finite_completion_policy=config.finite_completion_policy,
            context_fit_policy=config.context_fit_policy,
            # E22: the same prospective-configuration rule, read from the
            # composed fragment rather than from the row.
            react_exhaustion_policy=config.react_exhaustion_policy,
            max_revisions=config.max_revisions, error_type=RailsRunnerError,
        )
        if finite or context_degraded or seal_refused:
            validate_native_episode_finite_path(
                receipt, max_revisions=config.max_revisions, accept_action=config.actions[0],
                revise_action=config.actions[1], refresh_action=config.refresh_action,
                max_refreshes=config.max_candidate_refreshes,
                # E18: None/0 unarmed, which reduces the walker to exactly
                # its pre-E18 self.
                acquire_action=(
                    None if acquisition_policy is None else config.actions[2]
                ),
                max_acquisitions=config.max_acquisitions_per_row,
                error_type=RailsRunnerError,
            )
        accepted = delivery.final_contact
        # E20: a context-fit ABSTENTION has no delivered contact at all --
        # no Solver ever completed and no request was answered -- so there
        # is nothing to bind the delivered text to, and the block below is
        # skipped rather than satisfied with a placeholder.
        context_abstention = delivery.kind == "context-abstention"
        # E43: a seal-refusal ABSTENTION's rejected contact never reached
        # ``completed`` either (the same reason it never reached ``pending``
        # above), so there is nothing to look up for it -- it takes the
        # same no-delivered-contact bypass a context-fit abstention does.
        seal_refusal_abstention = seal_refused and delivery.kind == "abstention"
        completion = completed.get(accepted.get("agent_contact_id"))
        # E2b: a grouped Solver visit's delivered actor_output is the commit
        # policy's AGGREGATED answer, not the last raw sample's response
        # text -- solver_group's presence is what tells this apart from an
        # ordinary (samples-1) delivery, whose actor_output/completion.text
        # equality below is unchanged.
        solver_group = (
            None if delivery.kind in ("abstention", "context-abstention")
            else result["delivery"].get("solver_group")
        )
        if context_abstention or seal_refusal_abstention:
            if result["delivery"] != {
                "actor_output": "", "result_type": "abstention",
                "delivery_eligible": False,
            }:
                raise RailsRunnerError(
                    "abstention delivered something other than nothing"
                )
        elif (
            completion is None or completion.request_sha256 != accepted["request_sha256"]
            or completion.response_sha256 != accepted["response_sha256"]
            or completion.response_text_sha256 != accepted["response_text_sha256"]
            or (
                delivery.kind != "abstention" and solver_group is None
                and result["delivery"]["actor_output"] != completion.text
            )
            or (delivery.kind == "abstention" and result["delivery"] != {
                "actor_output": "", "result_type": "abstention", "delivery_eligible": False,
            })
        ):
            raise RailsRunnerError("native delivery is not bound to its actual source response")
        if solver_group is not None:
            from .native_episode_receipt import validate_solver_group_receipt

            validate_solver_group_receipt(
                solver_group, samples=solver_role_config.samples, error_type=RailsRunnerError,
            )
        # Item E42 (2026-09-25, family VAR-2): the arm group's own custody.
        # Absent on an abstention -- no arm ever answered -- exactly as
        # ``solver_group`` is.
        supply_variants = (
            None if delivery.kind in ("abstention", "context-abstention")
            else result["delivery"].get("supply_variants")
        )
        if supply_variant_group is not None and supply_variants is None:
            raise RailsRunnerError(
                "a declared supply-variant arm group delivered no arm custody"
            )
        if supply_variant_group is None and supply_variants is not None:
            raise RailsRunnerError(
                "a supply-variant receipt was delivered by an episode that "
                "declares no arm group"
            )
        if supply_variants is not None:
            from .native_episode_receipt import validate_supply_variant_receipt

            # ``retrieved_value_ids`` is deliberately NOT passed here: the
            # delivering arm's ids ARE this row's accumulated ids by
            # construction (it takes ``base_messages(ctx)`` unchanged), so
            # comparing them at the seal would restate the composition rather
            # than check it. The non-circular statement of that property is the
            # live refusal in ``supply_variant_messages``, which fails closed
            # when the flight's per-arm resolution of the delivering arm differs
            # from this row's own supply step. A POST-seal reader, which
            # reconstructs the state from the sealed wave instead of composing
            # it, passes the argument.
            validate_supply_variant_receipt(
                supply_variants,
                arm_ids=supply_variant_group.arm_ids,
                delivered_arm_id=supply_variant_group.delivered_arm.arm_id,
                phase_id=solver_role_config.phase_id,
                error_type=RailsRunnerError,
            )
            if template_variant_mode and not supply_variant_group.is_decoding and [
                row.get("instruction_template") for row in supply_variants["arms"]
            ] != [
                None if arm.instruction_template is None
                else arm.instruction_template.as_json()
                for arm in supply_variant_group.arms
            ]:
                raise RailsRunnerError(
                    "the sealed template-variant receipt names templates other "
                    "than the ones roles.solver.template_variants declared"
                )
            if supply_variant_group.is_decoding and [
                row.get("decoding_override") for row in supply_variants["arms"]
            ] != [arm.decoding for arm in supply_variant_group.arms]:
                raise RailsRunnerError(
                    "the sealed decoding-variant receipt names sampling overrides other "
                    "than the ones roles.solver.decoding_variants declared"
                )
        if supply_variant_records:
            raise RailsRunnerError(
                "supply-variant arm records were composed but never sealed"
            )
        final_text = (
            "" if delivery.kind in ("abstention", "context-abstention")
            else result["delivery"]["actor_output"] if solver_group is not None
            else completion.text
        )
        # E11 (2026-09-18, owner directive 26): the DELIVERY-TIME normaliser
        # node. It runs exactly ONCE per row, HERE -- after the Planner has
        # already ACCEPTed (or after the terminal delivery of the last
        # revision), after every guard above has bound the delivered answer
        # to its actual source response, and before that answer becomes the
        # row's delivered text. It makes no contact of any kind, so every
        # MODEL_REQUEST byte of the episode is already spent and unchanged;
        # it only rewrites what is delivered, and records the custody that
        # lets the seal and the bundle re-derive the delivered bytes from the
        # recorded response.
        #
        # An ABSTENTION is never normalised: it delivers empty text whose
        # identity is a DERIVED record (core.delivery.native_abstention_records),
        # there is no answer to project, and a normalisation receipt on such a
        # row would claim custody of bytes that came from no model response.
        deliver_normaliser_receipt = None
        if config.deliver_normaliser_id is not None and delivery.kind not in (
            "abstention", "context-abstention",
        ):
            from ..core.base import DELIVERY_NORMALISERS  # noqa: PLC0415
            from . import delivery_normalisers as _delivery_normalisers  # noqa: PLC0415, F401

            normalisation = DELIVERY_NORMALISERS.resolve(config.deliver_normaliser_id)(
                final_text
            )
            if normalisation.receipt.get("input_sha256") != hashlib.sha256(
                final_text.encode("utf-8")
            ).hexdigest():
                raise RailsRunnerError(
                    "delivery normaliser receipt does not bind its own input"
                )
            deliver_normaliser_receipt = dict(normalisation.receipt)
            final_text = normalisation.text
        # Item E4 (2026-09-28, owner decision 185): the post-accept targeted
        # re-listen. Runs exactly HERE -- after every guard above has bound
        # the delivered answer to its actual source response and after the
        # deliver normaliser, over the text the official scorer will read,
        # and before the seal below. It makes its own metered blind/
        # forced-choice contacts (never zero-contact like the normaliser),
        # so it runs before the trace merge a few lines down picks up every
        # contact's own trace buffer. An ABSTENTION is never relistened to,
        # for the same reason it is never normalised: there is no answer to
        # ask about. ``None`` for every config that does not arm
        # ``native_episode.relisten``, which leaves this row's contact count,
        # trace and receipt exactly what they were before E4.
        relisten_receipt = None
        if relisten_config is not None and delivery.kind not in (
            "abstention", "context-abstention",
        ):
            relisten_receipt = await run_relisten_stage(final_text)
        stop_transition = AgentStepTransition(
            snapshot_sha256=snapshot_sha256,
            prior_query_state_sha256=state.query_state.content_hash(),
            next_query_state_sha256=None, action_kind="stop", action_target_refs=(),
            new_value_ids=(), used_value_ids=(), dropped_value_ids=(),
            new_agent_state_ids=(), dropped_agent_state_ids=(),
        ).validate()
        if finite:
            state.waves.append(_agent_wave_record(
                wave_index=len(state.waves), contact=pending["plan"],
                response=pending["completion"].text, slot_ids=(pending["slot_id"],),
                query_state=pending["context"].query_state,
                advance=AgentLoopAdvance(
                    transition=stop_transition, next_query_state=None,
                    new_agent_states=(), next_contact=None,
                    final_response_contact_id=(
                        None if delivery.kind == "abstention" else completion.agent_contact_id
                    ),
                ),
            ))
            # Keep its raw request/response and cost; never promote finite text into semantic state.
            pending.clear()
        trace = TraceBuffer(run_id, spool=state.trace_spool)
        for key in sorted(state.trace_buffers):
            trace.extend_from(state.trace_buffers[key])
        compact_receipt = {key: receipt[key] for key in (
            "role_visits", "planner_routes", "accepted_solver_receipt", "interrupted_role",
            "abstention_receipt",
            # E8c: present exactly when a Planner output named no
            # registered action -- the row is retained and sealed, and
            # this is the count plus sha256 that says so.
            "planner_action_illegal",
            # E22: present exactly when a tool role of this row spent its
            # whole ReAct iteration budget on tool calls without an answer.
            # One record per exhausted VISIT -- the role, the visit index,
            # the iterations, every call's tool id and argument digest,
            # whether those calls were identical, and the last observation's
            # digest. Never an argument value and never an observation's
            # text. Absent on every unarmed row, so such a row's receipt is
            # byte-identical to its pre-E22 self.
            "react_exhaustion",
            # E37 (owner decision 84): present exactly when
            # native_episode.reviewer_verdict is armed -- one mark per
            # Reviewer visit of this row ({"visit", "token", "disposition",
            # "head"}, disposition one of legal / review_verdict_illegal /
            # react_exhaustion). Absent on every unarmed row, so such a
            # row's receipt is byte-identical to its pre-E37 self.
            "reviewer_verdicts",
            # Item E39 (2026-09-22): present exactly when a NON-answering
            # node of this row had a length-truncated completion tolerated
            # under native_episode.finite_completion_scope
            # "answering-node". One record per tolerated visit -- the role,
            # the stage, the visit index, the revision count and that
            # contact's own digests. Never the truncated text. Absent on
            # every "episode" row, so such a row's receipt is byte-identical
            # to its pre-E39 self.
            "truncation_events",
        ) if key in receipt}
        if system_policy_decision is not None:
            compact_receipt["system_policy_decision"] = system_policy_decision
        if not config.review_loop_enabled:
            # Configuration, not failure: record which phases never ran
            # rather than let their absence from role_visits speak alone.
            compact_receipt["review_loop_disposition"] = {
                "schema": "saea-native-review-loop-skip-v1",
                "status": "skipped_by_configuration",
                "reviewer_phase_id": config.role("reviewer").phase_id,
                "planner_phase_id": config.role("planner").phase_id,
            }
        if deliver_normaliser_receipt is not None:
            # E11: one block per row, naming the rule, its version, its
            # input/output digests and the counts of changed labels and
            # fillers. Never the text: a delivered SLURP answer carries slot
            # fillers taken from speech.
            compact_receipt["deliver_normaliser"] = deliver_normaliser_receipt
        if citation_records:
            # Gap G1 plumbing (``rails.solver_citation``): one block per row,
            # one record per cited-answer contact -- the ids this contact
            # rendered, the ids its answer cited (intent and per entity), the
            # answer's digest and the raw response digest it was cut from.
            # Ids, counts and digests only; never the answer or a knowledge
            # body. Absent on every un-armed row, so such a row's receipt is
            # byte-identical to its prior self. This is the per-row half of
            # the credit edge ``analysis.citation_credit`` aggregates.
            compact_receipt["solver_citations"] = {
                "schema": SOLVER_CITATIONS_RECEIPT_SCHEMA,
                "response_format_id": CITED_ANSWER_RESPONSE_FORMAT_ID,
                "contacts": [dict(row) for row in citation_records],
            }
        if acquisition_policy is not None:
            # E18: one block per row, naming the node, its registered policy
            # and budget, and one row per acquisition visit -- kind, policy,
            # what it brought in, what it cost, the Planner route that
            # triggered it, and the two digests that bind the question and
            # the answer. Never the acquired TEXT.
            from .acquisition import ACQUISITION_RECEIPT_SCHEMA  # noqa: PLC0415

            compact_receipt["acquisition"] = {
                "schema": ACQUISITION_RECEIPT_SCHEMA,
                "node_phase_id": acquisition_role_config.phase_id,
                "policy_id": acquisition_policy.policy_id,
                "kind": acquisition_policy.kind,
                "declared_kinds": list(acquisition_role_config.acquisition_kinds),
                "budget": acquisition_budget.as_json(),
                "acquisitions": [dict(row) for row in acquisition_records],
                "contacts_used": acquisition_contacts,
            }
        if constant_tool_names is not None:
            # E17: one block per row, naming the rendering mode, the one
            # array every contact carried, and the per-contact digest of
            # what was actually rendered. ``distinct_tool_schemas_sha256``
            # is the verdict-facing number: 1 means the tools block was
            # constant across every contact of this row.
            digests = [
                row["tool_schemas_sha256"] for row in tool_rendering_records
            ]
            compact_receipt["tool_schema_rendering"] = {
                "schema": "saea-native-tool-schema-rendering-v1",
                "mode": config.tool_schema_rendering,
                "rendered_tool_names": list(constant_tool_names),
                "contacts": [dict(row) for row in tool_rendering_records],
                "distinct_tool_schemas_sha256": len(set(digests)),
            }
        if knowledge_index is not None:
            # E21: one block per row, naming the released view and its three
            # digests, the granularity, the ordering, the budgets and any
            # per-role override, and one row per contact.
            # ``distinct_system_message_sha256`` is the verdict-facing
            # number: 1 means the constant prefix never toggled inside this
            # row, exactly as E17's ``distinct_tool_schemas_sha256`` does.
            compact_receipt["knowledge_index"] = knowledge_index.receipt(
                knowledge_index_records
            )
        if context_fit_budget is not None:
            # E20: one block per row, naming the policy, the live budget it
            # was measured against, and one row per contact carrying that
            # contact's compaction record or null. Present ONLY on the armed
            # arm, so an unarmed row's receipt is byte-identical to its
            # pre-E20 self.
            compact_receipt["context_fit"] = {
                "schema": "saea-native-context-fit-v1",
                "policy": config.context_fit_policy,
                "slot_tokens": context_fit_budget.slot_tokens,
                "prompt_limit_tokens": context_fit_budget.prompt_limit_tokens,
                "contacts": [dict(row) for row in context_fit_records],
                "compacted_contacts": sum(
                    1 for row in context_fit_records
                    if row["context_compaction"] is not None
                ),
            }
        if binding.candidate_proposal_for_context is not None:
            compact_receipt["candidate_proposal"] = {
                "schema": "saea-native-candidate-proposal-consumption-v1",
                "proposals": dict(proposal_documents),
                "contacts": [dict(row) for row in proposal_contacts.values() if "request_sha256" in row],
                "prepared_without_response": [
                    dict(row) for row in proposal_contacts.values() if "request_sha256" not in row
                ],
            }
        if perception_branch_group is not None:
            # Same-flight instrument, PHASE 2 (merge set C, design section 3,
            # "Receipt"): the Perception role's own result -- captured by
            # ``reproduction.ojw.native_episode._ApplyRole`` into
            # ``state["latest_perception"]``, exactly as the Solver's own
            # arm custody is captured into ``state["latest_solver"]`` --
            # carries the whole ``perception_branches`` receipt
            # (``rails.supply_variants.perception_branch_receipt``).
            # Perception is not necessarily the graph's own final delivering
            # role, so this is read off the graph's own final state here
            # rather than off ``result["delivery"]`` the way
            # ``supply_variants`` is.
            latest_perception = receipt.get("latest_perception")
            branches_block = (
                latest_perception.get("perception_branches")
                if isinstance(latest_perception, Mapping) else None
            )
            if not isinstance(branches_block, Mapping):
                raise RailsRunnerError(
                    "a declared Perception branch group delivered no branch custody"
                )
            branches_block = dict(branches_block)
            if perception_branch_group.level == PERCEPTION_BRANCH_LEVEL_SOLVER:
                # LEVEL 2 (merge set C item 1, design section 3, "Level 2"):
                # the Solver's own first-visit branch fan-out sealed its
                # per-branch custody into ``perception_branch_solver_
                # records`` (keyed by branch id) separately from -- and
                # strictly after -- the Perception visit that already sealed
                # ``branches_block`` above (Perception has exactly one visit
                # per row and has long completed by the time the Solver's
                # own first visit runs). Folded in here, at the episode's own
                # final receipt assembly, through the SAME validating
                # constructor (``perception_branch_record``) that sealed the
                # level-1 fields, so the merged row is re-validated in full
                # rather than patched by a raw dict update.
                from .supply_variants import perception_branch_record

                # LEVEL 2 render-defect guard (2026-10-09): a non-delivering
                # branch whose own Perception note differs from A's must have
                # RENDERED a different Solver request (its history carries its
                # own note), and the twin must have rendered exactly A's. A
                # column that replicated A's rendering although its note
                # differs is the defect itself, refused by name so it cannot
                # recur as a silent A/A replicate.
                _rows_by_branch = {
                    item["branch_id"]: item for item in branches_block.get("branches", [])
                }
                _delivering_id = perception_branch_group.delivering_branch.branch_id
                _a_render = perception_branch_solver_render_by_branch.get(_delivering_id)
                _a_note = _rows_by_branch[_delivering_id]["note_sha256"]
                for _row in branches_block.get("branches", []):
                    _branch = perception_branch_group.branch_at(_row["branch_index"])
                    if _branch.deliver or _a_render is None:
                        continue
                    _render = perception_branch_solver_render_by_branch.get(_branch.branch_id)
                    if _render is None:
                        continue
                    # Decision 338: a ``perception_samples`` branch's Solver reads its MERGED note, not the sample-0 note its
                    # row names, so the guard compares the note the Solver actually rendered.
                    _effective_note = (
                        hashlib.sha256(perception_branch_notes[_branch.branch_id].encode("utf-8")).hexdigest()
                        if perception_sampling_mode and _branch.perception_samples is not None
                        else _row["note_sha256"]
                    )
                    if _branch.is_twin:
                        if _render != _a_render:
                            raise RailsRunnerError(
                                f"level-2 perception branch {_branch.branch_id!r} (the twin) "
                                "rendered a Solver request different from branch A's"
                            )
                    elif _effective_note != _a_note and _render == _a_render:
                        raise RailsRunnerError(
                            f"level-2 perception branch {_branch.branch_id!r} Solver column "
                            "replicated branch A's rendered request although its own "
                            "Perception note differs from A's (the 2026-10-09 level-2 "
                            "render defect: the branch Solver never saw its own note)"
                        )
                sealed_branches = []
                for row in branches_block.get("branches", []):
                    branch = perception_branch_group.branch_at(row["branch_index"])
                    solver_row = perception_branch_solver_records.pop(
                        branch.branch_id, None,
                    )
                    if solver_row is None:
                        raise RailsRunnerError(
                            f"perception branch {branch.branch_id!r} sealed no "
                            "level-2 Solver column"
                        )
                    sealed_branches.append(perception_branch_record(
                        branch=branch, branch_index=row["branch_index"],
                        contact_id=row["contact_id"],
                        request_sha256=row["request_sha256"],
                        response_text_sha256=row["response_text_sha256"],
                        note_sha256=row["note_sha256"],
                        note_parse_status=row["note_parse_status"],
                        candidate_intent_ids=row["candidate_intent_ids"],
                        candidate_intent_ids_raw_count=row["candidate_intent_ids_raw_count"],
                        supplied_value_ids=row["supplied_value_ids"],
                        # 2026-09-29: carried through the fold. Before, this
                        # re-seal dropped the level-1 presentation outcome
                        # (every P-SV-1 ``b-top2contrast`` row sealed
                        # None/None) and would have refused every row of a
                        # level-2 ``min_candidates`` branch (P-SV-2
                        # ``b-list3``: "must carry a min_candidates_met bool").
                        presentation_skip_reason=row["presentation_skip_reason"],
                        contrast_block_sha256=row["contrast_block_sha256"],
                        min_candidates_met=row["min_candidates_met"],
                        solver_contact_id=solver_row["solver_contact_id"],
                        solver_request_sha256=solver_row["solver_request_sha256"],
                        solver_response_text_sha256=(
                            solver_row["solver_response_text_sha256"]
                        ),
                        candidate_supply_value_ids=(
                            solver_row["candidate_supply_value_ids"]
                        ),
                        template_group=perception_template_mode,
                        thinking_group=perception_thinking_mode,
                        **(
                            {
                                "sampling_group": True,
                                "sampling": (
                                    {
                                        "perception_samples": sampling_records.get(branch.branch_id, {}).get("perception_samples"),
                                        "solver_samples": sampling_records.get(branch.branch_id, {}).get("solver_samples"),
                                    }
                                    if branch.is_b else None
                                ),
                            } if perception_sampling_mode else {}
                        ),
                        solver_absent=bool(solver_row.get("solver_absent", False)),
                        absent_reason=solver_row.get("absent_reason"),
                    ))
                branches_block["branches"] = sealed_branches
                if perception_template_mode and [
                    row.get("instruction_template") for row in sealed_branches
                ] != [
                    None if branch.instruction_template is None
                    else branch.instruction_template.as_json()
                    for branch in perception_branch_group.branches
                ]:
                    raise RailsRunnerError(
                        "the sealed Perception template receipt names templates other "
                        "than the ones roles.perception.template_variants declared"
                    )
            compact_receipt["perception_branches"] = branches_block
        elif (
            isinstance(receipt.get("latest_perception"), Mapping)
            and "perception_branches" in receipt["latest_perception"]
        ):
            raise RailsRunnerError(
                "a perception-branch receipt was delivered by an episode "
                "that declares no branch group"
            )
        if perception_branch_records:
            raise RailsRunnerError(
                "perception-branch records were composed but never sealed"
            )
        if (
            perception_branch_group is None
            or perception_branch_group.level != PERCEPTION_BRANCH_LEVEL_SOLVER
        ) and perception_branch_solver_records:
            raise RailsRunnerError(
                "perception-branch Solver records were sealed by an episode "
                "that declares no level-2 branch group"
            )
        if perception_branch_solver_pending or perception_branch_solver_records:
            raise RailsRunnerError(
                "perception-branch Solver records were composed but never sealed"
            )
        if config.role_context_json is not None:
            compact_receipt["role_context_compilations"] = list(context_compilations.values())
        if node_context_declared:
            compact_receipt["node_context_policy_compilations"] = list(
                node_context_compilations.values()
            )
        if config.planner_output_format == "json-action-v1" and "planner_control" in receipt:
            # E8c: the raw plan is sealed as the SOURCE of the structured
            # control beside it.  A row whose final Planner output was
            # illegal has no control (native_episode pops it), and its
            # malformed text is not custody of anything -- the route
            # record and the receipt mark carry its sha256 instead.
            compact_receipt.update({
                key: receipt[key] for key in ("plan", "planner_control") if key in receipt
            })
        if terminal_disposition is not None:
            if final_solver_receipt is not None:
                compact_receipt["terminal_solver_receipt"] = dict(final_solver_receipt)
            compact_receipt["terminal_disposition"] = dict(terminal_disposition)
        if delivery.kind == "abstention" and seal_refused:
            # E43: the same quarantined-source derivation as the finite
            # abstention below, minus the finish_reason it never has (the
            # seal refused a "stop" finish, not the wire a length/
            # content_filter one) -- its own seal_refusal record stands in.
            from ..core.delivery import native_seal_refusal_abstention_records

            derived_id, derived_request, derived_response = (
                native_seal_refusal_abstention_records(
                    sample_id=state.prepared.sample.sample_id,
                    source_contact=delivery.final_contact,
                    seal_refusal=terminal_disposition["seal_refusal"],
                )
            )
            trace.emit("TOOL", f"{derived_id}/request", derived_request)
            trace.emit("TOOL", f"{derived_id}/response", derived_response)
        elif delivery.kind == "abstention":
            from ..core.delivery import native_abstention_records

            derived_id, derived_request, derived_response = native_abstention_records(
                sample_id=state.prepared.sample.sample_id,
                source_contact=delivery.final_contact,
                finish_reason=terminal_disposition["finish_reason"],
            )
            trace.emit("TOOL", f"{derived_id}/request", derived_request)
            trace.emit("TOOL", f"{derived_id}/response", derived_response)
        elif delivery.kind == "context-abstention":
            # E20: the same derivation, from the only custody this row has
            # -- its own disposition. No source contact exists: the refused
            # request was never answered.
            from ..core.delivery import native_context_abstention_records

            derived_id, derived_request, derived_response = (
                native_context_abstention_records(
                    sample_id=state.prepared.sample.sample_id,
                    disposition=terminal_disposition,
                )
            )
            trace.emit("TOOL", f"{derived_id}/request", derived_request)
            trace.emit("TOOL", f"{derived_id}/response", derived_response)
        episode_trace_id = scoped_execution_contact_id(
            f"{state.prepared.sample.sample_id}/{program.program_id}/native-episode",
            state.prepared.execution_unit_id,
        )
        for compilation in proposal_contacts.values():
            trace.emit("ORG", compilation["contact_id"] + "/candidate-proposal", {
                "org_candidate_proposal": compilation,
            })
        for compilation in context_compilations.values():
            trace.emit("ORG", compilation["contact_id"] + "/role-context", {
                "org_role_context": compilation,
            })
        for compilation in node_context_compilations.values():
            trace.emit("ORG", compilation["contact_id"] + "/node-context-policy", {
                "org_node_context_policy": compilation,
            })
        trace.emit("USE", episode_trace_id, {
            "use_native_episode": compact_receipt,
        })
        state.transitions.append(stop_transition)
        state.final_outcome = _AgentRuntimeOutcome(
            prepared=state.prepared, final_query_state=state.query_state,
            final_response_text=final_text, contacts=tuple(state.contacts),
            waves=tuple(state.waves), transitions=tuple(state.transitions),
            agent_states=tuple(state.state_store[k] for k in state.query_state.agent_state_ids),
            final_supply=_supply_for_state(snapshot, state.query_state),
            trace_buffer=trace, native_episode_receipt=compact_receipt,
            solver_group=solver_group,
            supply_variants=supply_variants,
            relisten=relisten_receipt,
        )
    finally:
        # Public framework resources are episode-owned, not role-visit-owned.
        # Keep reused nodes alive through revisions, then release every node.
        import sys

        original_error = sys.exception()
        cleanup_errors = []
        # E18: ``extra_nodes`` is empty unless an acquisition kind that
        # spends a contact built its own re-observation seat.
        for node in [*nodes.values(), *extra_nodes]:
            try:
                await node.close()
            except BaseException as error:
                cleanup_errors.append(error)
        if cleanup_errors:
            message = "native role cleanup failed: " + ", ".join(
                type(error).__name__ for error in cleanup_errors
            )
            if original_error is not None:
                original_error.add_note(message)
            else:
                raise RailsRunnerError(message) from cleanup_errors[0]


def _flush_agent_state_traces(states, trace_sink) -> None:
    """Preserve completed and interrupted episodes when their shared run fails."""
    for state in states:
        if state.final_outcome is not None:
            state.final_outcome.trace_buffer.flush_into(trace_sink)
        for key in sorted(state.trace_buffers):
            state.trace_buffers[key].flush_into(trace_sink)


class _SlotFillScheduler:
    """Owner decision 159 (``rails.dispatch_slot_fill``): the three scheduling
    switches of one native dispatch, owned for exactly its duration.

    Nothing here produces, reads or reorders a byte any node sees. The recall
    worker computes a function of a row's own sealed query that the row's
    supply step would otherwise compute itself (``rails.phase_supply``,
    ``prefetch_recall``); the role-input worker runs the unchanged builder on
    ONE dedicated thread, so role inputs stay mutually exclusive across rows
    exactly as they are on the event loop, with the calling task's context
    variables carried over; ``gc_freeze`` only moves the already-loaded heap
    out of the collector's generations.
    """

    def __init__(self, switches) -> None:
        from concurrent.futures import ThreadPoolExecutor

        self.switches = switches
        self._recall = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="saea-slotfill-recall")
            if switches.recall_prefetch else None
        )
        self._role_input = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="saea-slotfill-role-input")
            if switches.role_input_offload else None
        )
        self._froze = False
        if switches.gc_freeze:
            import gc

            gc.collect()
            gc.freeze()
            self._froze = True
        self.prefetched_rows = 0

    @classmethod
    def open(cls, switches):
        if switches is None:
            return None
        from .dispatch_slot_fill import DispatchSlotFill

        if not isinstance(switches, DispatchSlotFill):
            raise RailsRunnerError("slot fill requires a parsed DispatchSlotFill")
        return cls(switches)

    def prefetch(self, binding, sample_id: str) -> None:
        if self._recall is None:
            return
        forward = getattr(binding.supply_for_phase, "prefetch_recall", None)
        if callable(forward) and forward(sample_id, self._recall.submit):
            self.prefetched_rows += 1

    @property
    def role_input_runner(self):
        if self._role_input is None:
            return None
        executor = self._role_input

        async def run(builder, phase_id, episode_state):
            import asyncio
            import contextvars

            context = contextvars.copy_context()
            return await asyncio.get_running_loop().run_in_executor(
                executor, context.run, builder, phase_id, episode_state
            )

        return run

    def close(self) -> None:
        for executor in (self._recall, self._role_input):
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)
        if self._froze:
            import gc

            gc.unfreeze()
            self._froze = False


def _run_agent_openjiuwen(
    *,
    prepared_tasks: Sequence[_PreparedAgentTask],
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    protected_material: tuple[str, ...],
    adapter: TaskAdapter,
    controller_factory: AgentControllerFactory,
    controller_policy_id: str,
    core_client: CoreClient,
    max_contacts: int,
    slot_count: int,
    queue_depth: int,
    base_decoding_params: Mapping[str, object] | None,
    trace_sink: AgentTraceSink,
    run_id: str,
    observe_step: ObserveStep | None = None,
    record_namespace: str | None = None,
    request_batch_gate: RequestBatchGate | None = None,
    whole_roster_wave_barrier: bool = False,
    knowledge_value_renderer: object = None,
    native_episode_binding: NativeEpisodeRunBinding | None = None,
    thinking_policy: Mapping[str, object] | None = None,
    on_outcome: Callable[[_AgentRuntimeOutcome], object] | None = None,
) -> tuple[_AgentRuntimeOutcome, ...]:
    """Run the speech AgentLoop on the pinned openJiuwen workflow engine.

    ``on_outcome`` (owner decision 309, 2026-10-14) is called ONCE per row, the
    moment its episode has settled and its ``final_outcome`` is set -- before
    any other row finishes -- so the caller can make the row durable. It runs
    gold-free (scoring is still deferred to after the whole window) and its
    exceptions propagate: a checkpoint that cannot be written fails the row
    loudly rather than silently losing durability. ``None`` changes nothing."""

    from ..reproduction.ojw import (  # noqa: PLC0415
        DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
        OJW_INSTALL_HINT,
        openjiuwen_available,
    )

    if not openjiuwen_available():
        raise RailsRunnerError(OJW_INSTALL_HINT)
    from ..reproduction.ojw.runner import (  # noqa: PLC0415
        execute_speech_agent_workflows,
    )

    if native_episode_binding is not None:
        prefix_slots = native_episode_binding.prefix_slots
        scheduling_options = {}
        if prefix_slots is not None:
            from .dispatch_slot_fill import NativePrefixSlots, NativePrefixSlotsError
            if not isinstance(prefix_slots, NativePrefixSlots):
                raise RailsRunnerError("invalid native prefix slot binding")
            try:
                prefix_slots.validate(native_episode_binding.config, slot_count=slot_count)
            except NativePrefixSlotsError as error:
                raise RailsRunnerError(str(error)) from error
            scheduling_options["prefix_slot_bindings"] = prefix_slots.slot_bindings()
        if native_episode_binding.node_batch is not None:
            from .dispatch_slot_fill import NativeNodeBatch, NativeNodeBatchError
            node_batch = native_episode_binding.node_batch
            if not isinstance(node_batch, NativeNodeBatch) or prefix_slots is not None:
                raise RailsRunnerError("invalid or conflicting native node batch binding")
            try:
                node_batch.validate(native_episode_binding.config, queue_depth=queue_depth)
            except NativeNodeBatchError as error:
                raise RailsRunnerError(str(error)) from error
            scheduling_options.update(node_batch_order=node_batch.node_order,
                                      node_batch_size=node_batch.batch_size)
            def record_node_timing(state, event):
                from .execution_units import scoped_execution_contact_id
                index = sum(key[0] == -3 for key in state.trace_buffers)
                trace = TraceBuffer(run_id, spool=state.trace_spool)
                trace.emit("USE", scoped_execution_contact_id(
                    f"{state.prepared.sample.sample_id}/{native_episode_binding.program.program_id}/node-batch-timing/{index}",
                    state.prepared.execution_unit_id,
                ), {"use_node_batch_contact_timing": {
                    **event, "sample_id": state.prepared.sample.sample_id,
                    "execution_unit_id": state.prepared.execution_unit_id,
                }})
                state.trace_buffers[(-3, index)] = trace
            scheduling_options["node_batch_timing_sink"] = record_node_timing
        if native_episode_binding.node_pipeline is not None:
            from .dispatch_slot_fill import NativeNodePipeline, NativeNodePipelineError
            pipeline = native_episode_binding.node_pipeline
            if (not isinstance(pipeline, NativeNodePipeline) or prefix_slots is not None
                    or native_episode_binding.node_batch is not None):
                raise RailsRunnerError("invalid or conflicting native node pipeline binding")
            try:
                pipeline.validate(native_episode_binding.config)
            except NativeNodePipelineError as error:
                raise RailsRunnerError(str(error)) from error
            scheduling_options.update(
                node_pipeline_order=pipeline.node_order, node_pipeline_group_size=pipeline.group_size,
                node_pipeline_prepare_workers=pipeline.prepare_workers, node_pipeline_max_jobs=pipeline.max_jobs,
            )
            def record_pipeline_timing(state, event):
                from .execution_units import scoped_execution_contact_id
                if state.trace_spool is not None:
                    from ..core.trace_spool import process_memory_snapshot
                    event = {**event, "process_memory": process_memory_snapshot()}
                index = sum(key[0] == -4 for key in state.trace_buffers)
                trace = TraceBuffer(run_id, spool=state.trace_spool)
                trace.emit("USE", scoped_execution_contact_id(
                    f"{state.prepared.sample.sample_id}/{native_episode_binding.program.program_id}/node-pipeline-timing/{index}",
                    state.prepared.execution_unit_id,
                ), {"use_node_pipeline_timing": {
                    **event, "sample_id": state.prepared.sample.sample_id,
                    "execution_unit_id": state.prepared.execution_unit_id,
                }})
                state.trace_buffers[(-4, index)] = trace
            scheduling_options["node_pipeline_timing_sink"] = record_pipeline_timing
        selector = native_episode_binding.system_episode_policy
        if selector is not None:
            from .system_episode_policy import SystemEpisodePolicy
            if not isinstance(selector, SystemEpisodePolicy):
                raise RailsRunnerError("complete policy selector has an invalid type")
            selector.assert_envelope(native_episode_binding)
        trace_spool = None
        states = [
            _ContactAgentState(prepared=task, controller=None, query_state=task.initial_query_state, trace_spool=trace_spool)
            for task in prepared_tasks
        ]
        # Owner decision 159 (rails.dispatch_slot_fill): scheduling only.
        # ``None`` -- every committed configuration -- leaves every line below
        # exactly as it was; see _SlotFillScheduler for what each switch does.
        slot_fill = _SlotFillScheduler.open(native_episode_binding.slot_fill)

        async def invoke_episode(state, run_contact, session, *, run_local=None, run_prepare=None):
            selected_binding = native_episode_binding
            decision = None
            if selector is not None:
                ctx = _runtime_context(
                    prepared=state.prepared, snapshot=snapshot,
                    snapshot_sha256=snapshot_sha256, query_state=state.query_state,
                    state_store=state.state_store, response_sha256s=state.response_sha256s,
                    contact_index=0,
                )
                selected_binding, decision = selector.select(ctx)
                policy_trace = TraceBuffer(run_id, spool=state.trace_spool)
                policy_trace.emit(
                    "ORG", f"{state.prepared.sample.sample_id}/system-policy/initial",
                    {"org_system_policy_decision": decision},
                )
                state.trace_buffers[(-1, 0)] = policy_trace
            if slot_fill is not None:
                slot_fill.prefetch(selected_binding, state.prepared.sample.sample_id)
            await _invoke_native_role_episode(
                state=state, run_contact=run_contact, session=session, run_local=run_local,
                binding=selected_binding, adapter=adapter,
                system_policy_decision=decision,
                core_client=core_client, snapshot=snapshot,
                snapshot_sha256=snapshot_sha256, protected_material=protected_material,
                base_decoding_params=base_decoding_params, run_id=run_id,
                knowledge_value_renderer=knowledge_value_renderer,
                role_input_runner=(
                    (lambda builder, phase_id, episode_state: run_prepare(
                        lambda: builder(phase_id, episode_state), prefix_family=phase_id,
                    )) if run_prepare is not None
                    else (None if slot_fill is None else slot_fill.role_input_runner)
                ),
            )

        def record_sample_timing(state, timing):
            from .execution_units import scoped_execution_contact_id

            sample_id = state.prepared.sample.sample_id
            unit_id = state.prepared.execution_unit_id
            if state.final_outcome is not None:
                trace = state.final_outcome.trace_buffer
            else:
                trace = TraceBuffer(run_id, spool=state.trace_spool)
                state.trace_buffers[(-2, 0)] = trace
            trace.emit(
                "USE", scoped_execution_contact_id(
                    f"{sample_id}/{native_episode_binding.program.program_id}/sample-execution-timing",
                    unit_id,
                ),
                {"use_sample_execution_timing": {
                    **timing, "sample_id": sample_id, "execution_unit_id": unit_id,
                }},
            )
            # Decision 309: the row is whole here (episode records, then its
            # own timing record); make it durable before the next row's work.
            if on_outcome is not None and state.final_outcome is not None:
                on_outcome(state.final_outcome)

        panel_participation = native_episode_binding.workflow_panel
        if panel_participation is not None:
            from ..reproduction.ojw.panel import NativePanelParticipation
            if (not isinstance(panel_participation, NativePanelParticipation)
                    or native_episode_binding.node_pipeline is None):
                raise RailsRunnerError("panel participation requires the explicit node pipeline")

        try:
            pipeline = native_episode_binding.node_pipeline
            if pipeline is not None and pipeline.trace_spool is not None:
                from ..core.trace_spool import TraceSpool
                if native_episode_binding.data_root is None:
                    raise RailsRunnerError("node pipeline trace storage needs its owned data root")
                trace_spool = TraceSpool(
                    native_episode_binding.data_root, run_id,
                    max_record_bytes=pipeline.trace_spool.max_record_bytes,
                    max_total_bytes=pipeline.trace_spool.max_total_bytes,
                )
            for state in states:
                state.trace_spool = trace_spool
            execute = execute_speech_agent_workflows if panel_participation is None else (
                lambda states, **kwargs: panel_participation.execute(run_id, states, **kwargs)
            )
            execute(
                states, branch_count=1, slot_count=slot_count,
                queue_depth=queue_depth,
                workflow_timeout_seconds=DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
                episode_invoker=invoke_episode,
                local_tool_workers=native_episode_binding.config.local_tool_workers,
                sample_timing_sink=record_sample_timing,
                **scheduling_options,
            )
            if any(state.final_outcome is None for state in states):
                raise RailsRunnerError("native graph ended without an accepted Solver outcome")
        except BaseException:
            try:
                _flush_agent_state_traces(states, trace_sink)
            finally:
                if trace_spool is not None:
                    trace_spool.close()
            raise
        finally:
            if slot_fill is not None:
                slot_fill.close()
        return tuple(state.final_outcome for state in states)

    states: list[_ContactAgentState] = []

    def contacts_for(contact: AgentContact) -> tuple[AgentContactPlan, ...]:
        if isinstance(contact, AgentContactPlan):
            contact.validate()
            return (contact,)
        if isinstance(contact, AgentContactBatch):
            contact.validate()
            return contact.contacts
        raise RailsRunnerError(
            "Agent controller contact must be AgentContactPlan or AgentContactBatch"
        )

    def schedule_wave(state: _ContactAgentState, contact: AgentContact) -> None:
        plans = contacts_for(contact)
        _assert_agent_control_excludes_knowledge_payloads(contact, protected_material)
        query_state_sha256 = state.query_state.content_hash()
        if contact.query_state_sha256 != query_state_sha256:
            raise RailsRunnerError(
                "Agent contact wave is bound to a different QueryState"
            )
        if state.scheduled_contacts + len(plans) > max_contacts:
            raise RailsRunnerError(
                f"Agent trajectory exceeded its {max_contacts}-contact ceiling"
            )
        contact_ids = {plan.contact_id for plan in plans}
        duplicate_ids = contact_ids & state.seen_contact_ids
        if duplicate_ids:
            raise RailsRunnerError(
                f"Agent trajectory cannot reuse contact ids: {sorted(duplicate_ids)}"
            )
        context = _runtime_context(
            prepared=state.prepared,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=state.query_state,
            state_store=state.state_store,
            response_sha256s=state.response_sha256s,
            contact_index=state.scheduled_contacts,
        )
        messages = _agent_messages(
            adapter=adapter,
            sample=state.prepared.sample,
            task_contract=state.prepared.task_contract,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=state.query_state,
            agent_states=context.agent_states,
            knowledge_value_renderer=knowledge_value_renderer,
            prepared_text=getattr(core_client, "arm", None) == "prepared-context-text",
        )
        nodes: list[_AgentContactNode] = []
        for branch_index, plan in enumerate(plans):
            trace_buffer = TraceBuffer(run_id)
            state.trace_buffers[(state.wave_index, branch_index)] = trace_buffer
            nodes.append(
                _AgentContactNode(
                    task_index=state.prepared.index,
                    wave_index=state.wave_index,
                    branch_index=branch_index,
                    contact=plan,
                    messages=messages,
                    context=context,
                    trace_buffer=trace_buffer,
                )
            )
        state.current_contact = contact
        state.current_context = context
        state.current_nodes = tuple(nodes)
        state.seen_contact_ids.update(contact_ids)
        state.scheduled_contacts += len(plans)

    for prepared in prepared_tasks:
        controller = controller_factory(prepared.sample.sample_id)
        if not callable(getattr(controller, "initial_contact", None)) or not callable(
            getattr(controller, "advance", None)
        ):
            raise RailsRunnerError(
                f"controller factory for {controller_policy_id!r} returned an invalid controller"
            )
        state = _ContactAgentState(
            prepared=prepared,
            controller=controller,
            query_state=prepared.initial_query_state,
            state_store={item.state_id: item for item in prepared.initial_feedback_states},
        )
        initial_context = _runtime_context(
            prepared=prepared,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=state.query_state,
            state_store=state.state_store,
            response_sha256s=state.response_sha256s,
            contact_index=0,
        )
        schedule_wave(state, controller.initial_contact(initial_context))
        states.append(state)

    def request_arguments(node: _AgentContactNode, slot_id: int | None = None):
        decoding_params = dict(base_decoding_params or {})
        decoding_params.update(dict(node.contact.decoding_params))
        _apply_node_thinking(
            decoding_params, thinking_policy,
            next((s.controller for s in states if s.prepared.index == node.task_index), None),
            node.contact.contact_id,
        )
        if slot_id is not None:
            decoding_params["id_slot"] = slot_id
        source_arguments = (
            {"text_only_sample_id": node.context.sample_id}
            if getattr(core_client, "arm", None) == "prepared-context-text" else
            {"raw_agent_sample_id": node.context.sample_id}
            if node.context.query_state.query_source == "speech_audio"
            else {
                "speech_feature_sample_id": node.context.sample_id,
                "key_representation_id": node.contact.key_representation_id,
                "matcher_policy_id": node.contact.matcher_policy_id,
            }
        )
        return {
            "decoding_params": decoding_params,
            **source_arguments,
            "agent_state": tuple(a.as_json() for a in node.context.agent_states),
            "agent_contact_id": node.contact.contact_id,
            "contact_instruction": node.contact.instruction,
        }

    prepared_requests: dict[int, PreparedCoreRequest] = {}

    def prepare_request_batch(active_states) -> None:
        # Retained controllers already constructed their actual next requests.
        # Prepare once and send those same objects after the entire wave fits.
        if any(
            not isinstance(state.current_contact, AgentContactPlan)
            or len(state.current_nodes) != 1 for state in active_states
        ):
            raise RailsRunnerError("request batch fit requires one plain contact per sample")
        prepared_requests.clear()
        for state in active_states:
            node = state.current_nodes[0]
            prepared_requests[node.task_index] = core_client.prepare_request(
                node.messages, **request_arguments(node)
            )
        batch = tuple(prepared_requests[state.prepared.index] for state in active_states)
        ids = [request.as_payload()["sample_id"] for request in batch]
        if len(ids) != len(set(ids)) or set(ids) != {
            state.prepared.sample.sample_id for state in active_states
        }:
            raise RailsRunnerError("request batch fit requires the complete unique roster")
        request_batch_gate(batch)

    if request_batch_gate is not None and not whole_roster_wave_barrier:
        prepare_request_batch(states)

    def publish_workflow_state(
        state: _ContactAgentState,
        session: object,
    ) -> None:
        update_global_state = getattr(session, "update_global_state", None)
        if not callable(update_global_state):
            raise RailsRunnerError(
                "openJiuwen Agent workflow session lacks structured state"
            )
        current_contact = state.current_contact
        update_global_state(
            {
                "speech_agent_query_state": state.query_state.as_json(),
                "speech_agent_contact_wave": (
                    current_contact.as_json() if current_contact is not None else {}
                ),
                "speech_agent_visible_state_ids": list(
                    state.query_state.agent_state_ids
                ),
                "speech_agent_wave_index": state.wave_index,
                "speech_agent_stopped": state.final_outcome is not None,
            }
        )

    def prepare_workflow_wave(state_object: object, session: object) -> int:
        if not isinstance(state_object, _ContactAgentState):
            raise RailsRunnerError("openJiuwen received an invalid Agent state")
        publish_workflow_state(state_object, session)
        return len(state_object.current_nodes)

    # Keep immutable metadata outside OpenJiuwen's serialized response mapping.
    # Each fan-in consumes only the exact source sample/wave/branch reply.
    native_completions: dict[tuple[int, int, int], CoreCompletion] = {}

    def invoke_contact(
        state_object: object,
        branch_index: int,
        slot_id: int,
    ) -> Mapping[str, object]:
        if not isinstance(state_object, _ContactAgentState):
            raise RailsRunnerError("openJiuwen received an invalid Agent state")
        state = state_object
        node = state.current_nodes[branch_index]
        set_current_trace_buffer(node.trace_buffer)
        try:
            response_text, completion = _complete_agent_request(
                core_client=core_client, messages=node.messages,
                arguments=request_arguments(node, slot_id), trace_buffer=node.trace_buffer,
                prepared_request=(
                    prepared_requests[node.task_index] if request_batch_gate is not None
                    else None
                ),
            )
        finally:
            set_current_trace_buffer(None)
        result = {
            "response_text": response_text,
            "slot_id": slot_id,
            "response_sha256": agent_response_sha256(node.contact, response_text),
        }
        if completion is not None:
            native_completions[
                (node.task_index, node.wave_index, node.branch_index)
            ] = completion
        return result

    def combine_trace_buffers(state: _ContactAgentState) -> TraceBuffer:
        combined = TraceBuffer(run_id)
        for key in sorted(state.trace_buffers):
            combined.extend_from(state.trace_buffers[key])
        return combined

    def aggregate_wave(
        state_object: object,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        if not isinstance(state_object, _ContactAgentState):
            raise RailsRunnerError("openJiuwen received an invalid Agent state")
        state = state_object
        current_contact = state.current_contact
        context = state.current_context
        if current_contact is None or context is None:
            raise RailsRunnerError("Agent contact wave lost its controller context")
        plans = contacts_for(current_contact)
        if len(responses) != len(plans):
            raise RailsRunnerError("openJiuwen Agent fan-in changed the contact count")
        response_texts: list[str] = []
        slot_ids: list[int] = []
        wave_completions: list[CoreCompletion] = []
        for branch_index, (plan, response) in enumerate(zip(plans, responses, strict=True)):
            response_text = response["response_text"]
            slot_id = response["slot_id"]
            response_sha256 = response["response_sha256"]
            if (
                not isinstance(response_text, str)
                or isinstance(slot_id, bool)
                or not isinstance(slot_id, int)
                or not isinstance(response_sha256, str)
            ):
                raise RailsRunnerError(
                    "openJiuwen Agent fan-in returned malformed contact data"
                )
            expected_response_sha256 = hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest()
            if response_sha256 != expected_response_sha256:
                raise RailsRunnerError("openJiuwen Agent fan-in response hash mismatch")
            native = "tool_choice" in {
                **dict(base_decoding_params or {}), **dict(plan.decoding_params),
            }
            if native:
                metadata = native_completions.pop(
                    (state.prepared.index, state.wave_index, branch_index), None,
                )
                if metadata is None:
                    raise RailsRunnerError("openJiuwen native completion binding was lost")
                completion = metadata
                completion.assert_binding(
                    sample_id=context.sample_id, agent_contact_id=plan.contact_id,
                    response_text=response_text,
                )
                wave_completions.append(completion)
            response_texts.append(response_text)
            slot_ids.append(slot_id)
            state.contacts.append(
                AgentContactRecord(
                    plan=plan,
                    query_state_sha256=state.query_state.content_hash(),
                    speech_packet_sha256=state.query_state.speech_packet_sha256,
                    slot_id=slot_id,
                    response_sha256=response_sha256,
                )
            )
        controller_response: AgentResponse
        if isinstance(current_contact, AgentContactPlan):
            controller_response = response_texts[0]
        else:
            controller_response = tuple(response_texts)
        response_sha256 = agent_response_sha256(
            current_contact,
            controller_response,
        )
        state.response_sha256s.append(response_sha256)
        if wave_completions:
            context = replace(context, core_completions=tuple(wave_completions))
        advance = state.controller.advance(
            context,
            current_contact,
            controller_response,
        )
        if not isinstance(advance, AgentLoopAdvance):
            raise RailsRunnerError(
                "Agent controller.advance must return AgentLoopAdvance"
            )
        _validate_agent_knowledge_decision(
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            query_state=state.query_state,
            advance=advance,
        )
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=state.query_state,
            next_query_state=advance.next_query_state,
            transition=advance.transition,
            snapshot_sha256=snapshot_sha256,
            origin_speech_packet=(
                state.prepared.initial_query_state.speech_packet_id,
                state.prepared.initial_query_state.speech_packet_sha256,
            ),
        )
        _validate_new_agent_states(
            artifacts=advance.new_agent_states,
            transition=advance.transition,
            prior_query_state=state.query_state,
            response_sha256=response_sha256,
            snapshot=snapshot,
            existing_state_ids=set(state.state_store),
        )
        state.waves.append(
            _agent_wave_record(
                wave_index=state.wave_index,
                contact=current_contact,
                response=controller_response,
                slot_ids=tuple(slot_ids),
                query_state=state.query_state,
                advance=advance,
            )
        )
        state.transitions.append(advance.transition)
        if advance.transition.action_kind == "stop":
            if advance.next_contact is not None:
                raise RailsRunnerError("stop cannot schedule another Agent contact")
            final_response_text = _resolve_final_agent_response(
                current_contact,
                controller_response,
                advance.final_response_contact_id,
                allow_empty=state.prepared.execution_unit_id is not None,
                empty_receipted=_empty_completion_receipted(tuple(state.trace_buffers.values())),
            )
            state.final_outcome = _AgentRuntimeOutcome(
                prepared=state.prepared,
                final_query_state=state.query_state,
                final_response_text=final_response_text,
                contacts=tuple(state.contacts),
                waves=tuple(state.waves),
                transitions=tuple(state.transitions),
                agent_states=tuple(
                    state.state_store[state_id]
                    for state_id in state.query_state.agent_state_ids
                ),
                final_supply=_supply_for_state(snapshot, state.query_state),
                trace_buffer=combine_trace_buffers(state),
            )
            if on_outcome is not None:
                on_outcome(state.final_outcome)
            publish_workflow_state(state, session)
            return
        if advance.next_query_state is None or advance.next_contact is None:
            raise RailsRunnerError(
                "non-stop Agent transition requires next QueryState and contact"
            )
        if advance.final_response_contact_id is not None:
            raise RailsRunnerError(
                "non-stop Agent transition cannot select a final response"
            )
        if advance.transition.action_kind == "backtrack":
            for state_id in advance.transition.dropped_agent_state_ids:
                if state_id not in state.state_store:
                    raise RailsRunnerError(
                        f"backtrack cannot drop unknown Agent state {state_id!r}"
                    )
                state.state_store.pop(state_id)
        else:
            for artifact in advance.new_agent_states:
                state.state_store[artifact.state_id] = artifact
        if set(advance.next_query_state.agent_state_ids) != set(state.state_store):
            raise RailsRunnerError(
                "successor QueryState Agent state ids do not match materialized state"
            )
        state.query_state = advance.next_query_state
        settled_wave_index = state.wave_index
        state.wave_index += 1
        next_contact = advance.next_contact
        if observe_step is not None:
            # One buffer per observation, keyed BELOW this wave's branch 0 so
            # ``combine_trace_buffers``' sorted merge reads "observe, then
            # contact" -- the order the step actually runs in. Registered only
            # when an observation happened, so a silent Reviewer leaves the
            # buffer map exactly as it is today.
            observe_buffer = TraceBuffer(run_id)
            observed = _observe_relisten(
                observe_step=observe_step,
                snapshot=snapshot,
                snapshot_sha256=snapshot_sha256,
                sample_id=state.prepared.sample.sample_id,
                record_base=_agent_record_base(
                    state.prepared.sample.sample_id, record_namespace, state.prepared.execution_unit_id
                ),
                origin_packet=(
                    state.prepared.initial_query_state.speech_packet_id,
                    state.prepared.initial_query_state.speech_packet_sha256,
                ),
                wave_index=settled_wave_index,
                relisten_index=state.relisten_count,
                query_state=state.query_state,
                sink=observe_buffer,
            )
            if observed is not None:
                state.trace_buffers[(state.wave_index, -1)] = observe_buffer
                state.query_state, relisten_transition = observed
                state.transitions.append(relisten_transition)
                next_contact = _rebind_contact(
                    next_contact, state.query_state.content_hash()
                )
                state.relisten_count += 1
        schedule_wave(state, next_contact)
        publish_workflow_state(state, session)

    def flush_partial_traces() -> None:
        _flush_agent_state_traces(states, trace_sink)

    def execute_wave(active_states, *, one_wave: bool) -> None:
        starting_wave = {
            state.prepared.index: state.wave_index for state in active_states
        }
        execute_speech_agent_workflows(
            active_states,
            prepare_wave=prepare_workflow_wave,
            invoke_contact=invoke_contact,
            aggregate_wave=aggregate_wave,
            should_continue=lambda state: (
                state.final_outcome is None and (
                    not one_wave
                    or state.wave_index == starting_wave[state.prepared.index]
                )
            ),
            branch_count=max_contacts,
            slot_count=slot_count,
            queue_depth=queue_depth,
            workflow_timeout_seconds=DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
        )

    try:
        if whole_roster_wave_barrier:
            active_states = states
            while active_states:
                if request_batch_gate is not None:
                    prepare_request_batch(active_states)
                # Return only after every active sample settles this wave.
                # Preserve each controller, query state and trace buffer.
                execute_wave(active_states, one_wave=True)
                active_states = [
                    state for state in active_states if state.final_outcome is None
                ]
        else:
            execute_wave(states, one_wave=False)
        if any(state.final_outcome is None for state in states):
            raise RailsRunnerError("openJiuwen AgentLoop lost a trajectory result")
    except BaseException:
        flush_partial_traces()
        raise
    return tuple(
        state.final_outcome for state in states if state.final_outcome is not None
    )


def _agent_record_base(
    sample_id: str, record_namespace: str | None, execution_unit_id: str | None = None,
) -> str:
    """The trace record id prefix for one sample's agent-loop records.

    ``core.tracing.TraceSink`` refuses a duplicate record id, and a PHASE
    PROGRAM runs the same sample through several separate
    ``run_speech_native_agent_loop`` invocations that all share one sink
    (``rails.phase_runner.run_program``), so without a namespace the second
    phase's first record kills the run -- after its contacts are spent.
    ``record_namespace`` is inserted BEFORE ``agent-loop`` rather than after
    it, so ``/agent-loop/org`` and ``/agent-loop/runtime-use`` remain the
    record-id SUFFIXES every existing trace reader matches on. ``None``
    (every pre-existing caller) leaves the id byte-identical to before.
    """

    if execution_unit_id is not None:
        from .execution_units import execution_unit_scope
        scope = execution_unit_scope(execution_unit_id)
        record_namespace = f"{record_namespace}/{scope}" if record_namespace else scope
    if record_namespace is None:
        return f"{sample_id}/agent-loop"
    return f"{sample_id}/{record_namespace}/agent-loop"


def _emit_agent_runtime_trace(
    *,
    sink: AgentTraceSink,
    controller_policy_id: str,
    agent_executor_id: str,
    agent_executor_version: str,
    snapshot_sha256: str,
    outcome: _AgentRuntimeOutcome,
    record_namespace: str | None = None,
) -> str:
    """Persist gold-free Agent state, supply, and use records in split order."""

    sample_id = outcome.prepared.sample.sample_id
    record_base = _agent_record_base(sample_id, record_namespace, outcome.prepared.execution_unit_id)
    sink.emit(
        "ORG",
        f"{record_base}/org",
        {
            "org_controller_policy_id": controller_policy_id,
            "org_agent_executor_id": agent_executor_id,
            "org_agent_executor_version": agent_executor_version,
            "org_knowledge_snapshot_sha256": snapshot_sha256,
            "org_initial_query_state": outcome.prepared.initial_query_state.as_json(),
            "org_final_query_state": outcome.final_query_state.as_json(),
            "org_agent_states": [
                artifact.as_json() for artifact in outcome.agent_states
            ],
            **(
                {"org_prepared_feedback_seeds": [
                    artifact.as_json() for artifact in outcome.prepared.initial_feedback_states
                ]}
                if outcome.prepared.initial_feedback_states else {}
            ),
        },
    )
    sink.emit(
        "SUPPLY",
        f"{record_base}/supply",
        {
            "supply_bootstrap_facet_ids": list(
                outcome.prepared.initial_query_state.visible_facet_ids
            ),
            "supply_bootstrap_value_ids": list(
                outcome.prepared.initial_query_state.retrieved_value_ids
            ),
            "supply_acquired_value_ids_by_transition": [
                list(transition.new_value_ids)
                for transition in outcome.transitions
                if transition.new_value_ids
            ],
            "supply_acquired_facet_ids_by_transition": [
                list(transition.new_facet_ids)
                for transition in outcome.transitions
                if transition.new_facet_ids
            ],
            "supply_final_visible_facet_ids": list(
                outcome.final_query_state.visible_facet_ids
            ),
            "supply_final_visible_value_ids": list(
                outcome.final_query_state.retrieved_value_ids
            ),
        },
    )
    runtime_document: dict[str, object] = {
        "controller_policy_id": controller_policy_id,
        "agent_executor_id": agent_executor_id,
        "agent_executor_version": agent_executor_version,
        "knowledge_snapshot_sha256": snapshot_sha256,
        **({"execution_unit_id": outcome.prepared.execution_unit_id,
            "execution_unit_binding": dict(outcome.prepared.execution_unit_binding)}
           if outcome.prepared.execution_unit_id is not None else {}),
        "initial_query_state_sha256": outcome.prepared.initial_query_state.content_hash(),
        "final_query_state_sha256": outcome.final_query_state.content_hash(),
        "speech_packet_sha256": outcome.final_query_state.speech_packet_sha256,
        "contacts": [contact.as_json() for contact in outcome.contacts],
        "waves": [wave.as_json() for wave in outcome.waves],
        "transitions": [transition.as_json() for transition in outcome.transitions],
        "final_response_sha256": hashlib.sha256(
            outcome.final_response_text.encode("utf-8")
        ).hexdigest(),
    }
    runtime_trace_sha256 = content_hash(runtime_document)
    sink.emit(
        "USE",
        f"{record_base}/runtime-use",
        {
            "use_controller_policy_id": controller_policy_id,
            "use_agent_executor_id": agent_executor_id,
            "use_agent_executor_version": agent_executor_version,
            "use_knowledge_snapshot_sha256": snapshot_sha256,
            "use_initial_query_state_sha256": runtime_document[
                "initial_query_state_sha256"
            ],
            "use_final_query_state_sha256": runtime_document[
                "final_query_state_sha256"
            ],
            "use_speech_packet_sha256": runtime_document["speech_packet_sha256"],
            "use_contacts": runtime_document["contacts"],
            "use_waves": runtime_document["waves"],
            "use_transitions": runtime_document["transitions"],
            "use_final_response_sha256": runtime_document["final_response_sha256"],
            "use_runtime_trace_sha256": runtime_trace_sha256,
        },
    )
    return runtime_trace_sha256


def _emit_agent_posthoc_trace(
    *,
    sink: AgentTraceSink,
    result: AgentLoopResult,
    runtime_trace_sha256: str,
    record_namespace: str | None = None,
) -> None:
    sink.emit(
        "USE",
        f"{_agent_record_base(result.sample_id, record_namespace)}/posthoc-use",
        {
            "use_runtime_trace_sha256": runtime_trace_sha256,
            "use_final_response_sha256": hashlib.sha256(
                result.final_response_text.encode("utf-8")
            ).hexdigest(),
            "use_metrics": dict(result.metrics),
            "use_consumption": result.consumption.as_json(),
        },
    )


def run_speech_native_agent_loop(
    *,
    data_root: Path,
    plan: ExecutionPlan,
    adapter: TaskAdapter,
    core_client: CoreClient,
    split_id: str,
    knowledge_snapshot: KnowledgeSnapshot,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    execution_units=None,
    query_source: str = "speech_features",
    controller_policy_id: str,
    # Either a run-wide sequence (the original form: the same ids for every
    # sample) or, E6, a ``{sample_id: [ids]}`` mapping for a supplied FIRST
    # phase whose selection is per sample (see _per_sample_bootstrap).
    bootstrap_facet_ids: Sequence[str] | Mapping[str, Sequence[str]] = (),
    bootstrap_value_ids: Sequence[str] | Mapping[str, Sequence[str]] = (),
    max_contacts: int,
    slot_count: int,
    queue_depth: int,
    trace_sink: AgentTraceSink,
    agent_executor_id: str,
    decoding_params: Mapping[str, object] | None = None,
    controller_registry: Registry = AGENT_CONTROLLERS,
    trace_record_namespace: str | None = None,
    observe_step: ObserveStep | None = None,
    request_batch_gate: RequestBatchGate | None = None,
    whole_roster_wave_barrier: bool = False,
    knowledge_value_renderer: object = None,
    result_kind: str = TASK_ANSWER_RESULT_KIND,
    native_episode_binding: NativeEpisodeRunBinding | None = None,
    # Thinking-core harness knobs (decision 283 A): the composed config's per-node ``thinking_policy`` map, or None.
    thinking_policy: Mapping[str, object] | None = None,
    initial_feedback_states: Mapping[str, object] | None = None,
    # E10c: the OPTIONAL roster restriction a resume-recovery hands this loop
    # (see _restricted_split_samples). ``None`` -- every other caller -- runs
    # the whole split exactly as before.
    flown_sample_ids: Sequence[str] | None = None,
) -> AgentLoopSummary:
    """Run a bounded, batched, speech-native AgentLoop over one DEV split.

    BUILD is outside this function: ``knowledge_snapshot`` must already be a
    frozen TRAIN artifact. Formal AgentLoop runs use
    ``openjiuwen-workflow-v1``; ``reference-trajectory-v1`` is retained only
    as the dependency-free equivalence oracle.
    Runtime controllers receive only
    :class:`AgentRuntimeContext`, which deliberately excludes the adapter's
    gold-bearing sample object. All trajectories complete before ``score`` or
    ``extract_consumption`` is called.

    ``observe_step`` is the OPTIONAL Observer seam (``rails.observe``): between
    the wave that just settled and the wave about to be prepared, it turns the
    previous wave's REVIEW flags into a re-listen of the flagged span with a
    configured context margin, registers the derivation, and re-binds the
    controller's next contact to the observed ``QueryState``. ``None`` -- the
    default, and the ``observe: null`` arm of the config table -- runs exactly
    today's graph: no step, no record, no changed byte. Both executors call the
    same helper, so the ``reference-trajectory-v1`` equivalence oracle keeps
    covering the seam.

    ``query_source='speech_audio'`` is the explicit raw-native opt-in. Its
    binding entries carry the adapter-bound original media path and hash, or a
    slice already registered with the shared client. The historical default
    remains ``speech_features``.

    ``flown_sample_ids`` (E10c, 2026-09-18) is the resume-recovery seam: when
    given, the split is restricted to exactly those rows, in the split's own
    order, and EVERY roster-sized property of this call follows the restricted
    set -- the packet-binding assertion, the TRAIN-overlap check, the
    per-sample bootstrap seeds and ``planned_ceiling``. When absent the loop
    is byte-for-byte what it was before the keyword existed.
    """

    if native_episode_binding is not None:
        if not isinstance(native_episode_binding, NativeEpisodeRunBinding):
            raise RailsRunnerError("native episode requires the immutable flight binding")
        if (
            agent_executor_id != "openjiuwen-workflow-v1"
            or not isinstance(core_client, FrozenCoreClient)
            or whole_roster_wave_barrier or request_batch_gate is not None
            or observe_step is not None
        ):
            raise RailsRunnerError("native episodes require the shared client/executor and their actual-contact fit gate")
        if (
            controller_policy_id != native_episode_binding.program.program_id
            or max_contacts != native_episode_binding.config.max_contacts
            or not callable(native_episode_binding.request_gate)
            or not callable(native_episode_binding.render_request)
        ):
            raise RailsRunnerError("native episode program, ceiling or request custody differs")
    if result_kind not in RESULT_KINDS:
        raise RailsRunnerError(
            f"result_kind must be one of {sorted(RESULT_KINDS)}, got {result_kind!r}"
        )
    plan.validate()
    assert_execution_scope(plan.execution_profile)
    knowledge_snapshot.validate()
    snapshot_sha256 = knowledge_snapshot.content_hash()
    # Precomputed once per run and threaded down to every wave: the
    # snapshot_sha256 passthrough into assert_agent_step_binding /
    # assert_knowledge_use_binding, and the protected-material tuple for
    # _assert_agent_control_excludes_knowledge_payloads. The frozen snapshot
    # never changes within a run, so both are safe to compute exactly once.
    protected_material = _protected_knowledge_material(knowledge_snapshot)
    # Resolved against the roster once the split is known (below); the
    # run-wide form is validated here so a malformed flat sequence still
    # refuses before any adapter work.
    per_sample_facets_raw = bootstrap_facet_ids
    per_sample_values_raw = bootstrap_value_ids
    bootstrap_facets = (
        ()
        if isinstance(bootstrap_facet_ids, Mapping)
        else _validated_bootstrap_facet_ids(knowledge_snapshot, bootstrap_facet_ids)
    )
    bootstrap_ids = (
        ()
        if isinstance(bootstrap_value_ids, Mapping)
        else _validated_bootstrap_value_ids(knowledge_snapshot, bootstrap_value_ids)
    )
    if (
        not callable(getattr(trace_sink, "emit", None))
        or getattr(trace_sink, "run_id", None) != plan.run_id
    ):
        raise RailsRunnerError(
            "trace_sink must be an append-only trace sink bound to ExecutionPlan.run_id"
        )
    if not isinstance(controller_policy_id, str) or not controller_policy_id:
        raise RailsRunnerError("controller_policy_id must be a non-empty string")
    if not isinstance(controller_registry, Registry):
        raise RailsRunnerError("controller_registry must use core.base.Registry")
    try:
        controller_factory = controller_registry.resolve(controller_policy_id)
    except CoreError as error:
        raise RailsRunnerError(str(error)) from error
    if not callable(controller_factory):
        raise RailsRunnerError(
            f"registered Agent controller {controller_policy_id!r} must be callable"
        )
    max_contacts = _positive_int(max_contacts, field="max_contacts")
    slot_count = _positive_int(slot_count, field="slot_count")
    queue_depth = _positive_int(queue_depth, field="queue_depth")
    if queue_depth < slot_count:
        raise RailsRunnerError("queue_depth must be at least slot_count")
    if agent_executor_id not in {
        "reference-trajectory-v1",
        "openjiuwen-workflow-v1",
    }:
        raise RailsRunnerError(
            "agent_executor_id must be 'reference-trajectory-v1' or "
            "'openjiuwen-workflow-v1'"
        )
    if not isinstance(whole_roster_wave_barrier, bool):
        raise RailsRunnerError("whole_roster_wave_barrier must be a boolean")
    if whole_roster_wave_barrier and agent_executor_id != "openjiuwen-workflow-v1":
        raise RailsRunnerError(
            "whole-roster waves require the shared OpenJiuwen executor"
        )
    if request_batch_gate is not None:
        if not callable(request_batch_gate):
            raise RailsRunnerError("request_batch_gate must be callable")
        if agent_executor_id != "openjiuwen-workflow-v1" or (
            not whole_roster_wave_barrier
            and (
                max_contacts != 1
                or observe_step is not None
                or bootstrap_facet_ids
                or bootstrap_value_ids
            )
        ):
            raise RailsRunnerError(
                "request batch fit requires a solo OpenJiuwen phase without observe or seeds"
            )
        if not isinstance(core_client, FrozenCoreClient):
            raise RailsRunnerError(
                "request batch fit requires the shared FrozenCoreClient"
            )
    if agent_executor_id == "reference-trajectory-v1":
        if plan.execution_profile != "model-free-check":
            raise RailsRunnerError(
                "reference-trajectory-v1 is restricted to model-free-check"
            )
        if isinstance(core_client, FrozenCoreClient):
            raise RailsRunnerError(
                "reference-trajectory-v1 cannot use the real frozen-core client"
            )
        agent_executor_version = "repository-reference-v1"
    else:
        from ..reproduction.ojw import (  # noqa: PLC0415
            OpenJiuwenExecutorError,
            openjiuwen_runtime_version,
        )

        try:
            agent_executor_version = openjiuwen_runtime_version()
        except OpenJiuwenExecutorError as error:
            raise RailsRunnerError(str(error)) from error
    if decoding_params is not None and not isinstance(decoding_params, Mapping):
        raise RailsRunnerError("decoding_params must be a mapping or None")
    if decoding_params and "id_slot" in decoding_params:
        raise RailsRunnerError(
            "run-level decoding_params cannot choose id_slot; the runner owns it"
        )
    if query_source not in {"speech_features", "speech_audio"}:
        raise RailsRunnerError(
            "query_source must be 'speech_features' or 'speech_audio'"
        )
    from .prepared_text import PREPARED_TEXT_POLICIES

    raw_native_arm = "raw-speech-agent-native-tools"
    prepared_text = getattr(core_client, "arm", None) == "prepared-context-text"
    direct_programs = PREPARED_TEXT_POLICIES if prepared_text else {"phase-direct-only-v1"}
    raw_direct_only = (
        native_episode_binding is None
        and any(controller_policy_id in {policy, policy + ":direct"} for policy in direct_programs)
        and max_contacts == 1
    )
    if prepared_text and (
        not raw_direct_only or query_source != "speech_audio"
        or result_kind != ARTIFACT_RESULT_KIND or initial_feedback_states is None
        or request_batch_gate is None or not whole_roster_wave_barrier
        or native_episode_binding is not None or observe_step is not None
        or execution_units is not None or bootstrap_facet_ids or bootstrap_value_ids
        or knowledge_value_renderer is not None
    ):
        raise RailsRunnerError("prepared text requires a fitted scoreless direct-only prepared stage")
    if query_source == "speech_audio" and (
        not isinstance(core_client, FrozenCoreClient)
        or (core_client.arm != raw_native_arm and not prepared_text)
        or not (native_episode_binding is not None or raw_direct_only)
    ):
        raise RailsRunnerError(
            "speech_audio requires the explicit raw native client and either a "
            "native episode or the shared direct-only controller"
        )
    if (
        query_source == "speech_features"
        and isinstance(core_client, FrozenCoreClient)
        and core_client.arm == raw_native_arm
    ):
        raise RailsRunnerError(
            "the raw native client cannot receive a speech_features query"
        )

    samples = tuple(adapter.load_split(split_id))
    if not samples:
        raise RailsRunnerError(f"split {split_id!r} resolved to zero samples")
    sample_ids = tuple(sample.sample_id for sample in samples)
    if len(set(sample_ids)) != len(sample_ids):
        raise RailsRunnerError("AgentLoop split contains duplicate sample ids")
    if flown_sample_ids is not None:
        # E10c: the duplicate check above deliberately runs on the WHOLE
        # split, so a duplicate outside the restricted set still refuses.
        samples = _restricted_split_samples(
            samples,
            flown_sample_ids,
            split_id=split_id,
            execution_units=execution_units,
        )
        sample_ids = tuple(sample.sample_id for sample in samples)
    if (
        (execution_units is None or speech_packet_bindings)
        and set(speech_packet_bindings) != set(sample_ids)
    ):
        raise RailsRunnerError(
            "speech_packet_bindings must materialize every query sample exactly once"
        )
    overlap = set(sample_ids) & set(knowledge_snapshot.source_sample_ids)
    if overlap:
        raise RailsRunnerError(
            "AgentLoop query samples overlap the TRAIN knowledge source roster: "
            f"{sorted(overlap)}"
        )
    if knowledge_snapshot.source_split_identity_hash == plan.split_identity_hash:
        raise RailsRunnerError(
            "knowledge BUILD and AgentLoop USE must have different split identities"
        )
    from .execution_units import ExecutionUnitRoster
    if execution_units is not None and not isinstance(execution_units, ExecutionUnitRoster):
        raise RailsRunnerError("execution_units must be an ExecutionUnitRoster or None")
    if execution_units is not None:
        try:
            execution_units.validate(parent_sample_ids=sample_ids, max_contacts=max_contacts)
        except RailsError as error:
            raise RailsRunnerError(str(error)) from error
        for unit in execution_units.units:
            unit.query_descriptor(query_source)
        for unit in execution_units.units:
            record = unit.slice_record
            existing = core_client.registered_slice(unit.parent_sample_id, record.media_relpath)
            if existing is None:
                core_client.register_slice(record)
            elif existing != record:
                raise RailsRunnerError("execution unit differs from its registered original slice")
            else:
                core_client.admit_registered_slice(record)
    # Decision 278 / 283 A: a budgeted thinking request may spend one answer-only re-ask per contact. The plan ceiling allows the
    # family-level number of fallback contacts per row (0 for every request that is not a budgeted thinking request).
    from ..core.reasoning_knobs import fallback_contacts_per_row  # noqa: PLC0415

    planned_ceiling = (
        len(execution_units.units) if execution_units is not None else len(samples)
    ) * (max_contacts + fallback_contacts_per_row(controller_policy_id, decoding_params))
    if planned_ceiling > plan.planned_model_calls:
        raise RailsRunnerError(
            f"AgentLoop contact ceiling {planned_ceiling} exceeds the ExecutionPlan "
            f"budget {plan.planned_model_calls}"
        )

    per_sample_facets = _per_sample_bootstrap(
        per_sample_facets_raw, sample_ids, field="bootstrap_facet_ids"
    )
    per_sample_values = _per_sample_bootstrap(
        per_sample_values_raw, sample_ids, field="bootstrap_value_ids"
    )

    feedback_by_sample = {}
    if initial_feedback_states is not None:
        from .prepared_feedback import PreparedFeedbackStateArtifact

        if result_kind != ARTIFACT_RESULT_KIND or native_episode_binding is not None:
            raise RailsRunnerError(
                "prepared feedback requires a scoreless non-native proposal program"
            )
        if not isinstance(initial_feedback_states, Mapping) or set(initial_feedback_states) != set(sample_ids):
            raise RailsRunnerError("prepared feedback must bind every active sample exactly once")
        for sample_id, artifact in initial_feedback_states.items():
            if not isinstance(artifact, PreparedFeedbackStateArtifact):
                raise RailsRunnerError("initial feedback entries must be prepared feedback states")
            artifact.validate()
            feedback_by_sample[sample_id] = artifact

    prepared_tasks: list[_PreparedAgentTask] = []
    tasks = (
        tuple((sample, None) for sample in samples)
        if execution_units is None
        else tuple(
            (next(sample for sample in samples if sample.sample_id == unit.parent_sample_id), unit)
            for unit in execution_units.units
        )
    )
    for index, (sample, unit) in enumerate(tasks):
        obs = default_obs_packet(sample)
        if prepared_text:
            from .prepared_text import PREPARED_TEXT_INSTRUCTION
            task_contract = PREPARED_TEXT_INSTRUCTION
        else:
            task_contract = adapter.build_task_contract(sample, obs)
        if not isinstance(task_contract, str) or not task_contract.strip():
            raise RailsRunnerError(
                "TaskAdapter.build_task_contract must return non-empty English text"
            )
        if unit is not None:
            # Expose source geometry to both direct and agent requests, without labels.
            duration = unit.slice_record.audio_seconds
            task_contract += (
                f"\n\nCurrent speech window: local time starts at 0 seconds and ends "
                f"at {duration:.9g} seconds. Use this window-local coordinate system "
                "when referring to positions in the speech."
            )
        query_state = _initial_query_state(
            plan=plan,
            sample=sample,
            descriptor=(
                speech_packet_bindings[sample.sample_id]
                if unit is None
                else {
                    "packet_id": (
                        unit.query_descriptor(query_source)["packet_id"]
                        if query_source == "speech_features"
                        else unit.query_descriptor(query_source)["media_relpath"]
                    ),
                    "sha256": unit.query_descriptor(query_source)["sha256"],
                }
            ),
            bootstrap_facet_ids=(
                bootstrap_facets
                if per_sample_facets is None
                else _validated_bootstrap_facet_ids(
                    knowledge_snapshot,
                    tuple(per_sample_facets.get(sample.sample_id, ())),
                )
            ),
            bootstrap_value_ids=(
                bootstrap_ids
                if per_sample_values is None
                else _validated_bootstrap_value_ids(
                    knowledge_snapshot,
                    tuple(per_sample_values.get(sample.sample_id, ())),
                )
            ),
            query_source=query_source,
            execution_unit_id=None if unit is None else unit.request_key,
        )
        if query_source == "speech_audio":
            if (
                query_state.speech_packet_id == sample.audio_ref.path
                and query_state.speech_packet_sha256 != sample.audio_ref.sha256
            ):
                raise RailsRunnerError(
                    f"raw speech binding for {sample.sample_id!r} differs from the adapter source"
                )
            try:
                bound_identity = core_client.bound_raw_speech_identity(
                    sample.sample_id, query_state.speech_packet_id
                )
            except RailsError as error:
                raise RailsRunnerError(
                    f"raw speech binding for {sample.sample_id!r} is not admitted"
                ) from error
            if bound_identity != {
                "media_relpath": query_state.speech_packet_id,
                "sha256": query_state.speech_packet_sha256,
            }:
                raise RailsRunnerError(
                    f"raw speech binding for {sample.sample_id!r} differs from its source"
                )
        feedback = feedback_by_sample.get(sample.sample_id)
        initial_feedback = () if feedback is None else (feedback,)
        if initial_feedback:
            query_state = replace(
                query_state, agent_state_ids=tuple(item.state_id for item in initial_feedback)
            ).validate()
        prepared_tasks.append(
            _PreparedAgentTask(
                index=index,
                sample=sample,
                task_contract=task_contract,
                initial_query_state=query_state,
                initial_feedback_states=initial_feedback,
                execution_unit_id=None if unit is None else unit.request_key,
                execution_unit_binding=None if unit is None else unit.as_json(),
            )
        )

    flight_lock = read_flight_lock(Path(data_root))
    outcomes: list[_AgentRuntimeOutcome | None]

    # Owner decision 309 (2026-10-14): the gold-free runtime trace of a row is
    # emitted -- exactly as before, into the same buffer, after the row's own
    # records -- the moment the row settles instead of after the whole window,
    # and the row is handed to the sink's optional ``row_checkpoint`` so the
    # flight can make it durable. Idempotent per row; the record order inside
    # every row's buffer, and the order the buffers reach the trace sink, are
    # unchanged, so an uninterrupted flight's trace bytes are too.
    row_checkpoint = getattr(trace_sink, "row_checkpoint", None)
    runtime_trace_by_task: dict[int, str] = {}

    def settle_outcome(outcome: _AgentRuntimeOutcome) -> str:
        index = outcome.prepared.index
        known = runtime_trace_by_task.get(index)
        if known is not None:
            return known
        runtime_trace_sha256 = _emit_agent_runtime_trace(
            sink=outcome.trace_buffer,
            controller_policy_id=controller_policy_id,
            agent_executor_id=agent_executor_id,
            agent_executor_version=agent_executor_version,
            snapshot_sha256=snapshot_sha256,
            outcome=outcome,
            record_namespace=trace_record_namespace,
        )
        runtime_trace_by_task[index] = runtime_trace_sha256
        if callable(row_checkpoint) and outcome.prepared.execution_unit_id is None:
            row_checkpoint(
                outcome=outcome, trace_records=tuple(outcome.trace_buffer.iter_records()),
            )
        return runtime_trace_sha256

    if agent_executor_id == "openjiuwen-workflow-v1":
        outcomes = list(
            _run_agent_openjiuwen(
                prepared_tasks=prepared_tasks,
                snapshot=knowledge_snapshot,
                snapshot_sha256=snapshot_sha256,
                protected_material=protected_material,
                adapter=adapter,
                controller_factory=controller_factory,
                controller_policy_id=controller_policy_id,
                core_client=core_client,
                max_contacts=max_contacts,
                slot_count=slot_count,
                queue_depth=queue_depth,
                base_decoding_params=decoding_params,
                trace_sink=trace_sink,
                run_id=plan.run_id,
                observe_step=observe_step,
                record_namespace=trace_record_namespace,
                request_batch_gate=request_batch_gate,
                whole_roster_wave_barrier=whole_roster_wave_barrier,
                knowledge_value_renderer=knowledge_value_renderer,
                native_episode_binding=native_episode_binding,
                thinking_policy=thinking_policy,
                on_outcome=settle_outcome,
            )
        )
    else:
        slots: Queue[int] = Queue(maxsize=slot_count)
        for slot_id in range(slot_count):
            slots.put(slot_id)

        def execute(prepared: _PreparedAgentTask) -> _AgentRuntimeOutcome:
            slot_id = slots.get()
            trace_buffer = TraceBuffer(plan.run_id)
            set_current_trace_buffer(trace_buffer)
            try:
                return _run_agent_trajectory(
                    prepared=prepared,
                    snapshot=knowledge_snapshot,
                    snapshot_sha256=snapshot_sha256,
                    protected_material=protected_material,
                    adapter=adapter,
                    controller_factory=controller_factory,
                    controller_policy_id=controller_policy_id,
                    core_client=core_client,
                    max_contacts=max_contacts,
                    slot_id=slot_id,
                    base_decoding_params=decoding_params,
                    trace_buffer=trace_buffer,
                    observe_step=observe_step,
                    record_namespace=trace_record_namespace,
                    knowledge_value_renderer=knowledge_value_renderer,
                    thinking_policy=thinking_policy,
                )
            finally:
                set_current_trace_buffer(None)
                slots.put(slot_id)

        outcomes = [None] * len(prepared_tasks)
        with ThreadPoolExecutor(
            max_workers=min(slot_count, len(prepared_tasks)),
            thread_name_prefix="saea-agent-trajectory",
        ) as pool:
            pending: dict[Future[_AgentRuntimeOutcome], int] = {}
            next_index = 0
            while next_index < len(prepared_tasks) and len(pending) < queue_depth:
                future = pool.submit(execute, prepared_tasks[next_index])
                pending[future] = next_index
                next_index += 1
            while pending:
                completed, _ = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in completed:
                    index = pending.pop(future)
                    outcomes[index] = future.result()
                    if next_index < len(prepared_tasks):
                        next_future = pool.submit(execute, prepared_tasks[next_index])
                        pending[next_future] = next_index
                        next_index += 1

        if any(outcome is None for outcome in outcomes):
            raise RailsRunnerError("AgentLoop lost a trajectory result")

    # Gold-bearing adapter methods begin only after the whole runtime window
    # is sealed. Persist the runtime trajectory before scoring so no post-hoc
    # value can become a controller observation.
    runtime_trace_sha256s: list[str] = []
    try:
        for outcome in outcomes:
            assert outcome is not None
            runtime_trace_sha256s.append(settle_outcome(outcome))
            outcome.trace_buffer.flush_into(trace_sink)
    finally:
        for outcome in outcomes:
            if outcome is not None:
                outcome.trace_buffer.close_storage()

    results: list[AgentLoopResult] = []
    for outcome, runtime_trace_sha256 in zip(
        outcomes, runtime_trace_sha256s, strict=True
    ):
        assert outcome is not None
        if result_kind == ARTIFACT_RESULT_KIND or execution_units is not None:
            metrics = {}
            consumption = None
        else:
            metrics = adapter.score(
                outcome.prepared.sample,
                outcome.final_response_text,
            )
            consumption = adapter.extract_consumption(
                outcome.prepared.sample,
                outcome.final_supply,
                outcome.final_response_text,
            )
        results.append(
            AgentLoopResult(
                sample_id=outcome.prepared.sample.sample_id,
                initial_query_state=outcome.prepared.initial_query_state,
                final_query_state=outcome.final_query_state,
                final_response_text=outcome.final_response_text,
                contacts=outcome.contacts,
                waves=outcome.waves,
                transitions=outcome.transitions,
                agent_states=outcome.agent_states,
                metrics=metrics,
                consumption=consumption,
                result_kind=result_kind,
                native_episode_receipt=outcome.native_episode_receipt,
                execution_unit_id=outcome.prepared.execution_unit_id,
                execution_unit_binding=outcome.prepared.execution_unit_binding,
                solver_group=getattr(outcome, "solver_group", None),
                supply_variants=getattr(outcome, "supply_variants", None),
                relisten=getattr(outcome, "relisten", None),
            )
        )
        if result_kind == TASK_ANSWER_RESULT_KIND and execution_units is None:
            _emit_agent_posthoc_trace(
                sink=trace_sink,
                result=results[-1],
                runtime_trace_sha256=runtime_trace_sha256,
                record_namespace=trace_record_namespace,
            )

    return AgentLoopSummary(
        run_id=plan.run_id,
        protocol_hash=plan.protocol_hash,
        controller_policy_id=controller_policy_id,
        agent_executor_id=agent_executor_id,
        agent_executor_version=agent_executor_version,
        knowledge_snapshot_sha256=snapshot_sha256,
        results=tuple(results),
        flight_lock=flight_lock,
        result_kind=result_kind,
    )
