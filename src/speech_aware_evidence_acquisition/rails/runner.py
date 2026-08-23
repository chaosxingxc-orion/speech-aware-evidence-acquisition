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
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Callable, Mapping, Protocol, Sequence

from ..contracts import ExecutionPlan, assert_execution_scope
from ..core.base import AGENT_CONTROLLERS, CoreError, Registry
from ..core.flight_lock import read_flight_lock
from .consumption import ConsumptionTrace
from .core_client import CoreClient
from .errors import RailsError
from .knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    KnowledgeSnapshot,
    QueryState,
    ValueBundle,
    assert_agent_step_binding,
)
from .obs import ObsPacket, default_obs_packet
from .supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket
from .task_adapter import TaskAdapter, TaskSample

ZERO_SUPPLY_ARM = "zero-supply"
SUPPLIED_ARM = "supplied"
RAILS_ARMS: tuple[str, ...] = (ZERO_SUPPLY_ARM, SUPPLIED_ARM)

# (sample, obs, stable task contract) -> a SupplyPacket for the supplied arm, or
# None to skip supply for that one sample even though the arm ran (an
# adapter/caller-level choice, e.g. no evidence retrieved above threshold --
# distinct from the arm itself being absent from `arms`).
SupplyBuilder = Callable[[TaskSample, ObsPacket, str], SupplyPacket | None]


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
            raise RailsRunnerError(
                "AgentContactPlan.decoding_params must be a mapping"
            )
        if "id_slot" in self.decoding_params:
            raise RailsRunnerError(
                "AgentContactPlan cannot choose id_slot; the runner owns slot affinity"
            )
        return self


@dataclass(frozen=True)
class AgentLoopAdvance:
    """The external controller's exact state/evidence delta after a contact."""

    transition: AgentStepTransition
    next_query_state: QueryState | None
    new_agent_states: tuple[AgentStateArtifact, ...]
    next_contact: AgentContactPlan | None


@dataclass(frozen=True)
class AgentRuntimeContext:
    """Gold-free controller view; deliberately carries no task sample object."""

    sample_id: str
    knowledge_snapshot: KnowledgeSnapshot
    query_state: QueryState
    task_contract: str
    agent_states: tuple[AgentStateArtifact, ...]
    prior_response_sha256s: tuple[str, ...]
    contact_index: int


class AgentController(Protocol):
    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan: ...

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: str,
    ) -> AgentLoopAdvance: ...


AgentControllerFactory = Callable[[str], AgentController]


@dataclass(frozen=True)
class AgentContactRecord:
    plan: AgentContactPlan
    query_state_sha256: str
    speech_packet_sha256: str
    slot_id: int
    response_sha256: str


@dataclass(frozen=True)
class AgentLoopResult:
    sample_id: str
    final_query_state: QueryState
    final_response_text: str
    contacts: tuple[AgentContactRecord, ...]
    transitions: tuple[AgentStepTransition, ...]
    agent_states: tuple[AgentStateArtifact, ...]
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace


@dataclass(frozen=True)
class AgentLoopSummary:
    run_id: str
    protocol_hash: str
    controller_policy_id: str
    knowledge_snapshot_sha256: str
    results: tuple[AgentLoopResult, ...]
    flight_lock: Mapping[str, object] | None


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
    transitions: tuple[AgentStepTransition, ...]
    agent_states: tuple[AgentStateArtifact, ...]
    final_supply: SupplyPacket | None


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
    decoding_params: Mapping[str, object] | None = None,
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
    """

    plan.validate()
    assert_execution_scope(plan.execution_profile)
    for arm in arms:
        if arm not in RAILS_ARMS:
            raise RailsRunnerError(f"unknown rails arm {arm!r}; known arms are {RAILS_ARMS}")
    if SUPPLIED_ARM in arms and supply_builder is None:
        raise RailsRunnerError(f"arm {SUPPLIED_ARM!r} requires a supply_builder; none was given")

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
                    decoding_params=decoding_params,
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
    ).validate()


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
            "text": value.content,
            "evidence_id": value.value_id,
            "source_uri": (
                f"knowledge-snapshot://{snapshot_sha256}/{value.value_id}"
            ),
        }
        for value in _visible_values(snapshot, query_state)
    )
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    )


def _runtime_context(
    *,
    prepared: _PreparedAgentTask,
    snapshot: KnowledgeSnapshot,
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
        knowledge_snapshot=snapshot,
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
    adapter: TaskAdapter,
    controller_factory: AgentControllerFactory,
    controller_policy_id: str,
    core_client: CoreClient,
    max_contacts: int,
    slot_id: int,
    base_decoding_params: Mapping[str, object] | None,
) -> _AgentRuntimeOutcome:
    controller = controller_factory(prepared.sample.sample_id)
    if not callable(getattr(controller, "initial_contact", None)) or not callable(
        getattr(controller, "advance", None)
    ):
        raise RailsRunnerError(
            f"controller factory for {controller_policy_id!r} returned an invalid controller"
        )

    query_state = prepared.initial_query_state
    state_store: dict[str, AgentStateArtifact] = {}
    response_sha256s: list[str] = []
    contacts: list[AgentContactRecord] = []
    transitions: list[AgentStepTransition] = []
    context = _runtime_context(
        prepared=prepared,
        snapshot=snapshot,
        query_state=query_state,
        state_store=state_store,
        response_sha256s=response_sha256s,
        contact_index=0,
    )
    contact = controller.initial_contact(context)

    for contact_index in range(max_contacts):
        if not isinstance(contact, AgentContactPlan):
            raise RailsRunnerError(
                "Agent controller must return AgentContactPlan for every contact"
            )
        contact.validate()
        if contact.query_state_sha256 != query_state.content_hash():
            raise RailsRunnerError(
                "AgentContactPlan is bound to a different QueryState"
            )
        context = _runtime_context(
            prepared=prepared,
            snapshot=snapshot,
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
        response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
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
            raise RailsRunnerError("Agent controller.advance must return AgentLoopAdvance")
        assert_agent_step_binding(
            snapshot=snapshot,
            prior_query_state=query_state,
            next_query_state=advance.next_query_state,
            transition=advance.transition,
        )
        _validate_new_agent_states(
            artifacts=advance.new_agent_states,
            transition=advance.transition,
            prior_query_state=query_state,
            response_sha256=response_sha256,
            snapshot=snapshot,
            existing_state_ids=set(state_store),
        )
        transitions.append(advance.transition)

        if advance.transition.action_kind == "stop":
            if advance.next_contact is not None:
                raise RailsRunnerError("stop cannot schedule another Agent contact")
            return _AgentRuntimeOutcome(
                prepared=prepared,
                final_query_state=query_state,
                final_response_text=response_text,
                contacts=tuple(contacts),
                transitions=tuple(transitions),
                agent_states=tuple(
                    state_store[state_id] for state_id in query_state.agent_state_ids
                ),
                final_supply=_supply_for_state(snapshot, query_state),
            )

        if advance.next_query_state is None or advance.next_contact is None:
            raise RailsRunnerError(
                "non-stop Agent transition requires next QueryState and contact"
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

    raise RailsRunnerError(f"Agent trajectory exceeded its {max_contacts}-contact ceiling")


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
    max_contacts: int,
    slot_count: int,
    queue_depth: int,
    decoding_params: Mapping[str, object] | None = None,
    controller_registry: Registry = AGENT_CONTROLLERS,
) -> AgentLoopSummary:
    """Run a bounded, batched, speech-native AgentLoop over one DEV split.

    BUILD is outside this function: ``knowledge_snapshot`` must already be a
    frozen TRAIN artifact. Runtime controllers receive only
    :class:`AgentRuntimeContext`, which deliberately excludes the adapter's
    gold-bearing sample object. All trajectories complete before ``score`` or
    ``extract_consumption`` is called.
    """

    plan.validate()
    assert_execution_scope(plan.execution_profile)
    knowledge_snapshot.validate()
    snapshot_sha256 = knowledge_snapshot.content_hash()
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
    slots: Queue[int] = Queue(maxsize=slot_count)
    for slot_id in range(slot_count):
        slots.put(slot_id)

    def execute(prepared: _PreparedAgentTask) -> _AgentRuntimeOutcome:
        slot_id = slots.get()
        try:
            return _run_agent_trajectory(
                prepared=prepared,
                snapshot=knowledge_snapshot,
                snapshot_sha256=snapshot_sha256,
                adapter=adapter,
                controller_factory=controller_factory,
                controller_policy_id=controller_policy_id,
                core_client=core_client,
                max_contacts=max_contacts,
                slot_id=slot_id,
                base_decoding_params=decoding_params,
            )
        finally:
            slots.put(slot_id)

    outcomes: list[_AgentRuntimeOutcome | None] = [None] * len(prepared_tasks)
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
    # is sealed. Controllers never receive these metrics or full samples.
    results: list[AgentLoopResult] = []
    for outcome in outcomes:
        assert outcome is not None
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
                final_query_state=outcome.final_query_state,
                final_response_text=outcome.final_response_text,
                contacts=outcome.contacts,
                transitions=outcome.transitions,
                agent_states=outcome.agent_states,
                metrics=metrics,
                consumption=consumption,
            )
        )

    return AgentLoopSummary(
        run_id=plan.run_id,
        protocol_hash=plan.protocol_hash,
        controller_policy_id=controller_policy_id,
        knowledge_snapshot_sha256=snapshot_sha256,
        results=tuple(results),
        flight_lock=flight_lock,
    )
