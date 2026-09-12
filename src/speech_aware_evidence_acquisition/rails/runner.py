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
from .core_client import CoreClient, FrozenCoreClient, PreparedCoreRequest
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
from .obs import ObsPacket, default_obs_packet
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
) -> str:
    """Keep final-answer authority inside an actual frozen-core response."""

    if isinstance(contact, AgentContactPlan):
        if not isinstance(response, str):
            raise RailsRunnerError(
                "a single AgentContactPlan requires one string response"
            )
        if final_response_contact_id not in {None, contact.contact_id}:
            raise RailsRunnerError(
                "final_response_contact_id must select the stopped contact"
            )
        if not response:
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
                if not response_text:
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
        if self.result_kind != TASK_ANSWER_RESULT_KIND:
            result["result_kind"] = self.result_kind
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


@dataclass
class _ContactAgentState:
    prepared: _PreparedAgentTask
    controller: AgentController
    query_state: QueryState
    state_store: dict[str, AgentStateArtifact] = field(default_factory=dict)
    response_sha256s: list[str] = field(default_factory=list)
    contacts: list[AgentContactRecord] = field(default_factory=list)
    waves: list[AgentWaveRecord] = field(default_factory=list)
    transitions: list[AgentStepTransition] = field(default_factory=list)
    trace_buffers: dict[tuple[int, int], TraceBuffer] = field(default_factory=dict)
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
        query_id=f"{plan.run_id}:{sample.sample_id}:step0",
        query_sample_id=sample.sample_id,
        speech_packet_id=descriptor["packet_id"],
        speech_packet_sha256=descriptor["sha256"],
        use_split_identity_hash=plan.split_identity_hash,
        visible_facet_ids=bootstrap_facet_ids,
        retrieved_value_ids=bootstrap_value_ids,
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
) -> tuple[Mapping[str, object], ...]:
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

    content: list[Mapping[str, object]] = [
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
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    )


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
        prepared.sample.sample_id, record_namespace
    )
    relisten_count = 0
    state_store: dict[str, AgentStateArtifact] = {}
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
        )
        response_text = core_client.complete(
            messages,
            decoding_params=decoding_params,
            speech_feature_sample_id=prepared.sample.sample_id,
            key_representation_id=contact.key_representation_id,
            matcher_policy_id=contact.matcher_policy_id,
            agent_state=tuple(artifact.as_json() for artifact in context.agent_states),
            agent_contact_id=contact.contact_id,
            contact_instruction=contact.instruction,
        )
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
) -> tuple[_AgentRuntimeOutcome, ...]:
    """Run the speech AgentLoop on the pinned openJiuwen workflow engine."""

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
        if slot_id is not None:
            decoding_params["id_slot"] = slot_id
        return {
            "decoding_params": decoding_params,
            "speech_feature_sample_id": node.context.sample_id,
            "key_representation_id": node.contact.key_representation_id,
            "matcher_policy_id": node.contact.matcher_policy_id,
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
            if request_batch_gate is None:
                response_text = core_client.complete(
                    node.messages, **request_arguments(node, slot_id)
                )
            else:
                response_text = core_client.complete_prepared(
                    prepared_requests[node.task_index], id_slot=slot_id,
                )
        finally:
            set_current_trace_buffer(None)
        if not isinstance(response_text, str):
            raise RailsRunnerError("frozen core response must be a string")
        return {
            "response_text": response_text,
            "slot_id": slot_id,
            "response_sha256": agent_response_sha256(node.contact, response_text),
        }

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
        for plan, response in zip(plans, responses, strict=True):
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
                    state.prepared.sample.sample_id, record_namespace
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
        for state in states:
            if state.final_outcome is not None:
                state.final_outcome.trace_buffer.flush_into(trace_sink)
                continue
            for key in sorted(state.trace_buffers):
                state.trace_buffers[key].flush_into(trace_sink)

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


def _agent_record_base(sample_id: str, record_namespace: str | None) -> str:
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
    record_base = _agent_record_base(sample_id, record_namespace)
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
    """

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

    samples = tuple(adapter.load_split(split_id))
    if not samples:
        raise RailsRunnerError(f"split {split_id!r} resolved to zero samples")
    sample_ids = tuple(sample.sample_id for sample in samples)
    if len(set(sample_ids)) != len(sample_ids):
        raise RailsRunnerError("AgentLoop split contains duplicate sample ids")
    if set(speech_packet_bindings) != set(sample_ids):
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
    planned_ceiling = len(samples) * max_contacts
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

    prepared_tasks: list[_PreparedAgentTask] = []
    for index, sample in enumerate(samples):
        obs = default_obs_packet(sample)
        task_contract = adapter.build_task_contract(sample, obs)
        if not isinstance(task_contract, str) or not task_contract.strip():
            raise RailsRunnerError(
                "TaskAdapter.build_task_contract must return non-empty English text"
            )
        query_state = _initial_query_state(
            plan=plan,
            sample=sample,
            descriptor=speech_packet_bindings[sample.sample_id],
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
        )
        prepared_tasks.append(
            _PreparedAgentTask(
                index=index,
                sample=sample,
                task_contract=task_contract,
                initial_query_state=query_state,
            )
        )

    flight_lock = read_flight_lock(Path(data_root))
    outcomes: list[_AgentRuntimeOutcome | None]
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
    for outcome in outcomes:
        assert outcome is not None
        runtime_trace_sha256s.append(
            _emit_agent_runtime_trace(
                sink=outcome.trace_buffer,
                controller_policy_id=controller_policy_id,
                agent_executor_id=agent_executor_id,
                agent_executor_version=agent_executor_version,
                snapshot_sha256=snapshot_sha256,
                outcome=outcome,
                record_namespace=trace_record_namespace,
            )
        )
        outcome.trace_buffer.flush_into(trace_sink)

    results: list[AgentLoopResult] = []
    for outcome, runtime_trace_sha256 in zip(
        outcomes, runtime_trace_sha256s, strict=True
    ):
        assert outcome is not None
        if result_kind == ARTIFACT_RESULT_KIND:
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
            )
        )
        if result_kind == TASK_ANSWER_RESULT_KIND:
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
