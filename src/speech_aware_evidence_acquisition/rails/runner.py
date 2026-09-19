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
        if not response and not allow_empty:
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
                if not response_text and not allow_empty:
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
        source_arguments = (
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


async def _invoke_native_role_episode(
    *, state, run_contact, session, binding, adapter, core_client, snapshot,
    snapshot_sha256, protected_material, base_decoding_params, run_id,
    knowledge_value_renderer, run_local=None,
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
        NativeRoleContactContext, NativeRoleModelRequest, NativeRoleNode,
        NativeRoleNodeSpec, NativeSourceFunction,
    )
    from .controllers import (
        advance_phase_response_state, native_planner_action_response_format,
        restrict_repeat_visit_supply, seal_phase_response_state,
    )
    from .material import PhaseMaterial

    from .execution_units import scoped_execution_contact_id
    config, program = binding.config, binding.program
    if bool(config.local_tool_workers) != (run_local is not None):
        raise RailsRunnerError("native local tool scheduling differs from its configuration")
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
    pending = {}
    visits = {}
    completed = {}
    role_configs = {role.phase_id: role for role in config.roles}
    context_binding = None
    context_compilations = {}
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

    def context():
        return _runtime_context(
            prepared=state.prepared, snapshot=snapshot, snapshot_sha256=snapshot_sha256,
            query_state=state.query_state, state_store=state.state_store,
            response_sha256s=state.response_sha256s, contact_index=len(state.contacts),
        )

    def base_messages(ctx):
        return _agent_messages(
            adapter=adapter, sample=state.prepared.sample,
            task_contract=state.prepared.task_contract, snapshot=snapshot,
            snapshot_sha256=snapshot_sha256, query_state=ctx.query_state,
            agent_states=ctx.agent_states, knowledge_value_renderer=knowledge_value_renderer,
        )

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
        staged = replace(
            before, agent_states=before.agent_states + (source,),
            prior_response_sha256s=before.prior_response_sha256s + (completion.response_text_sha256,),
            core_completions=(completion,),
        )
        supply = None if tool_step is None else tool_step.supply
        if supply is None and next_phase is not None and binding.supply_for_phase is not None:
            supply = binding.supply_for_phase(next_phase, staged)
        if supply is not None and next_phase is not None and program.phase(next_phase).knowledge != "supplied":
            raise RailsRunnerError("native knowledge supply requires a supplied destination")
        if supply is not None and next_phase is not None:
            # E3c: the Planner's REVISE route re-enters the Solver, and a
            # prepared phase supply is a pure function of (phase, sample), so
            # the SAME decision comes back for a phase whose values already
            # ride the accumulated QueryState. Acquire only what is new; the
            # first visit of every phase is returned unchanged.
            supply = restrict_repeat_visit_supply(supply, before, phase_name=next_phase)
        if rejected_steps and (tool_step is not None or any(step.supply is not None for step in rejected_steps)):
            raise RailsRunnerError("rejected batch cannot execute a tool or introduce supply")
        added = (source,) + (() if tool_step is None else (tool_step.state,))
        added += tuple(step.state for step in rejected_steps)
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
            elif config.exhaustion_policy == "deliver-latest-solver":
                route_actions.append(config.actions[1])
                if config.refresh_action is not None:
                    route_actions.append(config.refresh_action)
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
        }
        return material.instruction

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
        plan = AgentContactPlan(
            contact_id=request.context.agent_contact_id,
            query_state_sha256=ctx.query_state.content_hash(),
            purpose=program.phase(request.role_id).purpose,
            instruction=material.instruction,
            key_representation_id=f"{program.program_id}:{request.role_id}",
            matcher_policy_id=program.program_id, decoding_params=decoding,
        ).validate()
        _assert_agent_control_excludes_knowledge_payloads(plan, protected_material)
        state.current_context, state.current_contact = ctx, plan
        messages = base_messages(ctx)
        exposed_states = select_native_role_history(
            role=role, solver_phase_id=config.role("solver").phase_id,
            states=ctx.agent_states, local_tool_result_ids=tuple(visit["local_ids"]),
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
                sample_id=ctx.sample_id, states=ctx.agent_states,
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
                phase_ids={item.role_kind: item.phase_id for item in config.roles},
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
        return NativeRoleSpeechBinding(
            role_id=request.role_id, sample_id=ctx.sample_id,
            role_query=visit["query"], base_messages=messages,
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
        source = seal_phase_response_state(
            phase_name=request.role_id, sample_id=before.sample_id,
            state_content=completion.text, raw_response_text=completion.text,
            source_query_state_sha256=before.query_state.content_hash(),
            producer_policy_id=program.program_id,
            state_namespace=plan.contact_id,
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
        slot_id = visits[request.role_id]["slot_id"]
        visits[request.role_id]["model_contacts"] += 1
        state.contacts.append(AgentContactRecord(
            plan=plan, query_state_sha256=before.query_state.content_hash(),
            speech_packet_sha256=before.query_state.speech_packet_sha256,
            slot_id=slot_id, response_sha256=completion.response_text_sha256,
        ))
        state.response_sha256s.append(completion.response_text_sha256)
        completed[completion.agent_contact_id] = completion
        pending.update(
            completion=completion, source=source, context=before, plan=plan,
            slot_id=slot_id, phase_id=request.role_id,
            # E2c: which sample of a grouped Solver visit this contact is
            # (None for every ungrouped contact), so ``settle`` can tell the
            # group's last sample -- the one that registers the committed
            # state -- from the ones that register none.
            sample_index=request.context.sample_index,
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
        trace = TraceBuffer(run_id)
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

    async def metered(request):
        def contact(slot_id):
            if state.scheduled_contacts >= config.max_contacts:
                raise RailsRunnerError("native graph exceeds its registered contact ceiling")
            if request.context.agent_contact_id in state.seen_contact_ids:
                raise RailsRunnerError("native graph repeated a contact identity")
            state.seen_contact_ids.add(request.context.agent_contact_id)
            trace = TraceBuffer(run_id)
            state.trace_buffers[(state.scheduled_contacts, 0)] = trace
            state.scheduled_contacts += 1
            visits[request.role_id]["slot_id"] = slot_id
            set_current_trace_buffer(trace)
            try:
                prepared = adapter_request.prepare(request)
                binding.request_gate(prepared.request)
                completion = adapter_request.dispatch(prepared)
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
        return await run_contact(contact)

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
        async def invoke(**arguments):
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
            return await run_contact(execute)
        return NativeSourceFunction(
            card=ToolCard(id=function["name"], name=function["name"],
                          description=function.get("description", ""),
                          input_params=function["parameters"]),
            func=invoke,
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
                return NativeRoleContactContext(**kwargs)
            def role_delivery_allowed(_role: str, output: str) -> bool:
                return isinstance(output, str) and bool(output.strip())
            solver_node = NativeRoleNode(
                spec=NativeRoleNodeSpec(
                    role_id=role.phase_id, role_kind=role.role_kind, prompt=prompt,
                    max_iterations=role.max_iterations, ability_names=role.tool_names,
                    reserve_final_report=config.reserve_final_report and bool(role.tool_names),
                ),
                metered_request=metered, contact_context_provider=contact_context,
                reject_tool_batch=reject_tool_batch if role.tool_names else None,
                abilities=tuple(ability_for(role, schema_by_name[name]) for name in role.tool_names),
                tool_allowed=(
                    (lambda phase, name, role=role: phase == role.phase_id and name in role.tool_names)
                    if role.role_kind in {"reviewer", "planner"} else None
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
            else:
                nodes[role.role_kind] = solver_node
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
            ),
            nodes=NativeEpisodeNodes(**nodes),
            role_input_builder=role_input,
        )
        result = await workflow.invoke_direct(state.prepared.task_contract, (), session=session)
        receipt = result["state"]
        from .native_episode_receipt import (
            validate_native_episode_delivery_receipt, validate_native_episode_finite_path,
            validate_native_episode_terminal_policy,
        )
        raw_disposition = receipt.get("terminal_disposition")
        finite = (
            isinstance(raw_disposition, Mapping)
            and raw_disposition.get("reason") == "finite_completion"
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
            max_revisions=config.max_revisions, error_type=RailsRunnerError,
        )
        if finite:
            validate_native_episode_finite_path(
                receipt, max_revisions=config.max_revisions, accept_action=config.actions[0],
                revise_action=config.actions[1], refresh_action=config.refresh_action,
                max_refreshes=config.max_candidate_refreshes, error_type=RailsRunnerError,
            )
        accepted = delivery.final_contact
        completion = completed.get(accepted.get("agent_contact_id"))
        # E2b: a grouped Solver visit's delivered actor_output is the commit
        # policy's AGGREGATED answer, not the last raw sample's response
        # text -- solver_group's presence is what tells this apart from an
        # ordinary (samples-1) delivery, whose actor_output/completion.text
        # equality below is unchanged.
        solver_group = (
            None if delivery.kind == "abstention" else result["delivery"].get("solver_group")
        )
        if (
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
        final_text = (
            "" if delivery.kind == "abstention"
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
        if config.deliver_normaliser_id is not None and delivery.kind != "abstention":
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
        trace = TraceBuffer(run_id)
        for key in sorted(state.trace_buffers):
            trace.extend_from(state.trace_buffers[key])
        compact_receipt = {key: receipt[key] for key in (
            "role_visits", "planner_routes", "accepted_solver_receipt", "interrupted_role",
            "abstention_receipt",
            # E8c: present exactly when a Planner output named no
            # registered action -- the row is retained and sealed, and
            # this is the count plus sha256 that says so.
            "planner_action_illegal",
        ) if key in receipt}
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
        if delivery.kind == "abstention":
            from ..core.delivery import native_abstention_records

            derived_id, derived_request, derived_response = native_abstention_records(
                sample_id=state.prepared.sample.sample_id,
                source_contact=delivery.final_contact,
                finish_reason=terminal_disposition["finish_reason"],
            )
            trace.emit("TOOL", f"{derived_id}/request", derived_request)
            trace.emit("TOOL", f"{derived_id}/response", derived_response)
        episode_trace_id = scoped_execution_contact_id(
            f"{state.prepared.sample.sample_id}/{program.program_id}/native-episode",
            state.prepared.execution_unit_id,
        )
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
        )
    finally:
        # Public framework resources are episode-owned, not role-visit-owned.
        # Keep reused nodes alive through revisions, then release every node.
        import sys

        original_error = sys.exception()
        cleanup_errors = []
        for node in nodes.values():
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

    if native_episode_binding is not None:
        states = [
            _ContactAgentState(prepared=task, controller=None, query_state=task.initial_query_state)
            for task in prepared_tasks
        ]

        async def invoke_episode(state, run_contact, session, *, run_local=None):
            await _invoke_native_role_episode(
                state=state, run_contact=run_contact, session=session, run_local=run_local,
                binding=native_episode_binding, adapter=adapter,
                core_client=core_client, snapshot=snapshot,
                snapshot_sha256=snapshot_sha256, protected_material=protected_material,
                base_decoding_params=base_decoding_params, run_id=run_id,
                knowledge_value_renderer=knowledge_value_renderer,
            )

        try:
            execute_speech_agent_workflows(
                states, branch_count=1, slot_count=slot_count,
                queue_depth=queue_depth,
                workflow_timeout_seconds=DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
                episode_invoker=invoke_episode,
                local_tool_workers=native_episode_binding.config.local_tool_workers,
            )
        except BaseException:
            _flush_agent_state_traces(states, trace_sink)
            raise
        if any(state.final_outcome is None for state in states):
            raise RailsRunnerError("native graph ended without an accepted Solver outcome")
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
        if slot_id is not None:
            decoding_params["id_slot"] = slot_id
        source_arguments = (
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
    raw_native_arm = "raw-speech-agent-native-tools"
    raw_direct_only = (
        native_episode_binding is None
        and controller_policy_id in {
            "phase-direct-only-v1",
            "phase-direct-only-v1:direct",
        }
        and max_contacts == 1
    )
    if query_source == "speech_audio" and (
        not isinstance(core_client, FrozenCoreClient)
        or core_client.arm != raw_native_arm
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
    planned_ceiling = (
        len(execution_units.units) if execution_units is not None else len(samples)
    ) * max_contacts
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
