"""C4a consolidation: one whole-roster single-phase runner
(:func:`run_agent_phase`) plus one program sequencer (:func:`run_program`),
extracted from the near-identical ``run_phase`` bodies of
``rails.probes.a2t_semantic_agentloop`` and
``rails.probes.a2t_select_fill_agentloop`` and generalized over any
:class:`~.controllers.PhaseProgram`.

How the ``select-then-fill`` barrier is realized
-------------------------------------------------

``rails.runner.run_speech_native_agent_loop`` runs one independent
per-sample trajectory per row; it has no notion of "every row reached phase
X" partway through a run. A hard barrier between two phases (phase 2 must
never start for ANY row before phase 1 has settled for EVERY row) therefore
cannot live inside a single ``run_speech_native_agent_loop`` call -- it can
only be a property of HOW MANY TIMES, and in what order, that call is made.

``run_program`` realizes the barrier this way: it iterates
``program.phases`` in declared order and, for each phase, makes exactly one
BLOCKING, WHOLE-ROSTER call to :func:`run_agent_phase` (which itself reduces
the program to that one phase via ``PhaseProgram.solo`` and runs it with
``max_contacts=1`` -- one contact per sample, for every sample in the
split). Because ``run_agent_phase`` does not return until every row's
single contact for that phase has completed, the NEXT phase's call cannot
begin until the whole prior phase is done -- exactly the barrier semantics
``PhaseSpec.barrier`` declares. Each completed phase's raw response is
sealed into a plain ``sample_id -> AgentStateArtifact`` mapping
(:func:`_seal_phase_state`) and handed to the NEXT phase's
``material_for_phase`` callable, so ``fill`` can read ``select``'s answer
even though the two phases are two entirely separate
``run_speech_native_agent_loop`` invocations with no shared runtime state
(mirrors ``rails.probes.a2t_select_fill_agentloop``'s own external
``PhaseMaterial.predecessor`` threading).

``run_program`` applies this SAME per-phase, whole-roster sequencing to
EVERY program, not only a barrier one: this consolidation slice does not
implement true single-trajectory phase fusion (pipelining a fast sample's
``fill`` contact against a slow sample's still-running ``select`` contact).
A caller that wants a genuinely continuous multi-contact trajectory for a
non-barrier program (e.g. ``phase-direct-evidence-alpha-blend-v1``, the way
``rails.kb_policy.KbAlphaBlendController`` runs its own direct/evidence pair
as one trajectory) constructs ``controllers.EvidenceAgentController``
directly with the FULL (non-``solo``) ``PhaseProgram`` and calls
``run_speech_native_agent_loop`` itself, bypassing ``run_program`` entirely
-- ``EvidenceAgentController`` was built generically enough to support
either shape (module docstring in ``rails.controllers``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..contracts import ExecutionPlan
from ..core.base import Registry
from .controllers import (
    EvidenceAgentController,
    MaterialForPhase,
    PhaseProgram,
    ReviewForPhase,
    StopPolicy,
    SupplyForPhase,
    seal_phase_response_state,
)
from .core_client import CoreClient
from .errors import RailsError
from .knowledge import AgentStateArtifact, KnowledgeSnapshot
from .phase_review import emit_review_records
from .runner import (
    AgentLoopSummary,
    AgentTraceSink,
    RequestBatchGate,
    run_speech_native_agent_loop,
)
from .task_adapter import TaskAdapter

#: ``material_for_phase(phase_name, context, sealed_states)`` -- the richer
#: shape ``run_program`` calls, where ``sealed_states`` is the immediately
#: preceding phase's own ``sample_id -> AgentStateArtifact`` mapping (empty
#: for the program's first phase, which has no predecessor).
ProgramMaterialForPhase = Callable[
    [str, "object", Mapping[str, AgentStateArtifact]], "object"
]

DEFAULT_AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"


class PhaseRunnerError(RailsError):
    """A ``run_agent_phase``/``run_program`` input, or the phase summary it
    got back, violated the shape this module requires."""


def _expected_execution_ids(bindings, execution_units):
    if execution_units is None:
        return tuple(bindings)
    from .execution_units import ExecutionUnitRoster
    if not isinstance(execution_units, ExecutionUnitRoster):
        raise PhaseRunnerError("execution_units must be an ExecutionUnitRoster")
    parents = tuple(bindings) or tuple(
        dict.fromkeys(unit.parent_sample_id for unit in execution_units.units)
    )
    execution_units.validate(parent_sample_ids=parents, max_contacts=1)
    return tuple(unit.request_key for unit in execution_units.units)


def _result_execution_identity(result, execution_units):
    parent_id = getattr(result, "sample_id", None)
    if execution_units is None:
        return parent_id
    unit_id = getattr(result, "execution_unit_id", None)
    parents = {unit.request_key: unit.parent_sample_id for unit in execution_units.units}
    if not isinstance(unit_id, str) or not unit_id or parents.get(unit_id) != parent_id:
        raise PhaseRunnerError("execution unit result differs from its declared parent binding")
    return unit_id


def run_agent_phase(
    *,
    phase_name: str,
    program: PhaseProgram,
    adapter: TaskAdapter,
    plan: ExecutionPlan,
    data_root: Path,
    core_client: CoreClient,
    split_id: str,
    knowledge_snapshot: KnowledgeSnapshot,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    execution_units: object = None,
    query_source: str = "speech_features",
    trace_sink: AgentTraceSink,
    decoding_params: Mapping[str, object],
    material_for_phase: MaterialForPhase,
    supply_for_phase: SupplyForPhase | None = None,
    review_for_phase: ReviewForPhase | None = None,
    bootstrap_facet_ids: object = (),
    bootstrap_value_ids: object = (),
    expected_row_count: int | None = None,
    slot_count: int | None = None,
    queue_depth: int | None = None,
    agent_executor_id: str = DEFAULT_AGENT_EXECUTOR_ID,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
    request_batch_gate: RequestBatchGate | None = None,
    result_kind: str = "task-answer",
    thinking_policy: Mapping[str, object] | None = None,
) -> AgentLoopSummary:
    """Run exactly one named phase of ``program`` for the whole roster in
    ``speech_packet_bindings``, as one blocking ``max_contacts=1`` call.

    Builds a private ``core.base.Registry`` and registers a factory
    producing one ``controllers.EvidenceAgentController`` per sample, bound
    to ``program.solo(phase_name)`` (module docstring). ``slot_count`` /
    ``queue_depth`` default from ``adapter.serving_geometry()`` when not
    given (``queue_depth = 4 * slots``). Refuses ``response_format`` inside
    the run-level ``decoding_params`` (every phase's own response format, if
    any, comes from its ``PhaseMaterial`` instead -- mirrors
    ``rails.runner.run_speech_native_agent_loop``'s own refusal for
    ``id_slot``). Validates the returned summary: bound to
    ``agent_executor_id``, exactly one contact per result, row count matches
    ``expected_row_count`` (or ``len(speech_packet_bindings)`` when not
    given), and sample identities are unique and match the roster exactly.
    """

    if request_batch_gate is not None and (
        not callable(request_batch_gate)
        or supply_for_phase is not None
        or review_for_phase is not None
        or bootstrap_facet_ids
        or bootstrap_value_ids
        or agent_executor_id != DEFAULT_AGENT_EXECUTOR_ID
    ):
        raise PhaseRunnerError(
            "staged request fit requires a plain solo OpenJiuwen phase without supply or review"
        )
    program.validate()
    if result_kind not in {"task-answer", "artifact"}:
        raise PhaseRunnerError("result_kind must be task-answer or artifact")
    solo_program = program.solo(phase_name)
    if not callable(material_for_phase):
        raise PhaseRunnerError("run_agent_phase requires a callable material_for_phase")
    if supply_for_phase is not None and not callable(supply_for_phase):
        raise PhaseRunnerError(
            "run_agent_phase supply_for_phase must be callable or None"
        )
    if review_for_phase is not None and not callable(review_for_phase):
        raise PhaseRunnerError(
            "run_agent_phase review_for_phase must be callable or None"
        )
    if not isinstance(decoding_params, Mapping) or "response_format" in decoding_params:
        raise PhaseRunnerError(
            "run-level decoding_params must leave response_format to each "
            "phase's own material"
        )
    if not isinstance(speech_packet_bindings, Mapping) or (
        not speech_packet_bindings and execution_units is None
    ):
        raise PhaseRunnerError("speech_packet_bindings must be a non-empty mapping without units")
    if expected_row_count is not None:
        if (
            isinstance(expected_row_count, bool)
            or not isinstance(expected_row_count, int)
            or expected_row_count <= 0
        ):
            raise PhaseRunnerError(
                "expected_row_count must be a positive integer or None"
            )
        declared_row_count = (
            len(execution_units.units)
            if execution_units is not None and hasattr(execution_units, "units")
            else len(speech_packet_bindings)
        )
        if declared_row_count != expected_row_count:
            raise PhaseRunnerError(
                f"phase {phase_name!r} requires exactly {expected_row_count} "
                f"{'execution units' if execution_units is not None else 'speech packet bindings'}"
            )

    geometry = adapter.serving_geometry()
    resolved_slot_count = slot_count if slot_count is not None else geometry["slots"]
    resolved_queue_depth = (
        queue_depth if queue_depth is not None else resolved_slot_count * 4
    )
    if (
        isinstance(resolved_slot_count, bool)
        or not isinstance(resolved_slot_count, int)
        or resolved_slot_count <= 0
    ):
        raise PhaseRunnerError(
            "slot_count (or the adapter's serving_geometry) must be a positive int"
        )
    if (
        isinstance(resolved_queue_depth, bool)
        or not isinstance(resolved_queue_depth, int)
        or resolved_queue_depth < resolved_slot_count
    ):
        raise PhaseRunnerError("queue_depth must be an int >= slot_count")

    if execution_units is not None:
        from dataclasses import replace
        from .execution_units import scoped_execution_contact_id
        source_material = material_for_phase

        def material_for_phase(name, context):
            material = source_material(name, context)
            return replace(material, contact_id=scoped_execution_contact_id(
                material.contact_id, context.execution_unit_id,
            ))

    controller_registry = Registry(
        f"phase runner controller: {solo_program.program_id}"
    )
    controller_registry.register(
        solo_program.program_id,
        lambda sample_id: EvidenceAgentController(
            program=solo_program,
            material_for_phase=material_for_phase,
            supply_for_phase=supply_for_phase,
            review_for_phase=review_for_phase,
        ),
    )

    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=split_id,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        **({"execution_units": execution_units} if execution_units is not None else {}),
        query_source=query_source,
        controller_policy_id=solo_program.program_id,
        bootstrap_facet_ids=bootstrap_facet_ids,
        bootstrap_value_ids=bootstrap_value_ids,
        max_contacts=1,
        slot_count=resolved_slot_count,
        queue_depth=resolved_queue_depth,
        trace_sink=trace_sink,
        agent_executor_id=agent_executor_id,
        decoding_params=decoding_params,
        controller_registry=controller_registry,
        # Every phase of a program shares ONE trace sink, and
        # core.tracing.TraceSink refuses a duplicate record id, so a
        # two-phase program's second phase would kill the run on its first
        # emitted record -- after its contacts were spent. Namespacing by
        # phase name is what makes the shared sink safe, and it is also what
        # lets a reader tell which phase a trace record came from.
        trace_record_namespace=phase_name,
        **({"result_kind": "artifact"} if result_kind == "artifact" else {}),
        # Decision 283 A: the per-node thinking override map, passed only when declared (byte-identical call otherwise).
        **({"thinking_policy": thinking_policy} if thinking_policy else {}),
        **(
            {"request_batch_gate": request_batch_gate}
            if request_batch_gate is not None
            else {}
        ),
    )

    if getattr(summary, "agent_executor_id", None) != agent_executor_id:
        raise PhaseRunnerError(
            f"phase {phase_name!r} summary is not bound to agent_executor_id "
            f"{agent_executor_id!r}"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise PhaseRunnerError(
            f"phase {phase_name!r} must return a non-empty results tuple"
        )
    row_target = (
        expected_row_count
        if expected_row_count is not None
        else len(execution_units.units) if execution_units is not None
        else len(speech_packet_bindings)
    )
    if len(results) != row_target:
        raise PhaseRunnerError(
            f"phase {phase_name!r} must return exactly {row_target} results, "
            f"got {len(results)}"
        )
    sample_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise PhaseRunnerError(
                f"phase {phase_name!r} result lacks a sample identity"
            )
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise PhaseRunnerError(
                f"phase {phase_name!r} every result must contain exactly one contact"
            )
        sample_ids.append(_result_execution_identity(result, execution_units))
    expected_ids = _expected_execution_ids(speech_packet_bindings, execution_units)
    if len(set(sample_ids)) != len(sample_ids):
        raise PhaseRunnerError(
            f"phase {phase_name!r} results have "
            f"{'duplicate execution identities' if execution_units is not None else 'duplicate sample ids'}"
        )
    if set(sample_ids) != set(expected_ids) or (
        execution_units is not None and tuple(sample_ids) != expected_ids
    ):
        raise PhaseRunnerError(
            f"phase {phase_name!r} result identities differ from "
            f"{'the declared unit roster' if execution_units is not None else 'speech_packet_bindings'}"
        )
    # The Reviewer's verdicts are collected per row WHILE the wave flies and
    # written out HERE, once, in sorted order -- the same "buffer per sample,
    # flush deterministically" discipline rails.runner and core.tracing
    # already use, and the reason rails.phase_review never touches the sink
    # from inside a trajectory (that module's own docstring).
    # record_namespace stays None here: run_agent_phase already reduces the
    # program to this ONE phase, and the base below is f"{sample}/{phase}/
    # review" -- the same per-phase namespacing rails.runner applies with
    # trace_record_namespace=phase_name, without repeating the phase twice.
    emit_review_records(review_for_phase, trace_sink, phase_name=phase_name)
    return summary


def _seal_phase_state(
    result: object, *, phase_name: str, producer_policy_id: str
) -> AgentStateArtifact:
    """Reconstruct the completed phase's sealed state purely from the
    ``AgentLoopResult`` ``run_agent_phase`` already validated -- the same
    ``state_id``/``state_kind`` shape ``EvidenceAgentController.advance``
    seals internally for a continuous multi-phase trajectory, but rebuilt
    externally here because a solo, immediate-stop phase invocation never
    merges its own final wave into ``rails.runner``'s internal state store
    (``rails.runner._run_agent_trajectory`` only merges ``new_agent_states``
    on a NON-stop transition; a solo phase always stops on its one and only
    contact). For that same reason ``result.initial_query_state`` and
    ``result.final_query_state`` are identical here -- the trajectory never
    advances past step 0.
    """

    final_response_text = getattr(result, "final_response_text")
    initial_query_state = getattr(result, "initial_query_state")
    sample_id = getattr(result, "sample_id")
    return seal_phase_response_state(
        phase_name=phase_name,
        sample_id=sample_id,
        state_content=final_response_text,
        raw_response_text=final_response_text,
        source_query_state_sha256=initial_query_state.content_hash(),
        producer_policy_id=producer_policy_id,
        cited_value_ids=(),
    )


def run_program(
    *,
    program: PhaseProgram,
    adapter: TaskAdapter,
    plan: ExecutionPlan,
    data_root: Path,
    core_client: CoreClient,
    split_id: str,
    knowledge_snapshot: KnowledgeSnapshot,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    execution_units: object = None,
    query_source: str = "speech_features",
    trace_sink: AgentTraceSink,
    decoding_params: Mapping[str, object],
    material_for_phase: ProgramMaterialForPhase,
    supply_for_phase: SupplyForPhase | None = None,
    review_for_phase: ReviewForPhase | None = None,
    bootstrap_facet_ids_by_phase: Mapping[str, object] | None = None,
    bootstrap_value_ids_by_phase: Mapping[str, object] | None = None,
    expected_row_count: int | None = None,
    slot_count: int | None = None,
    queue_depth: int | None = None,
    agent_executor_id: str = DEFAULT_AGENT_EXECUTOR_ID,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
    request_batch_gate: Callable[[str, tuple], None] | None = None,
    result_kind: str = "task-answer",
    thinking_policy: Mapping[str, object] | None = None,
) -> tuple[AgentLoopSummary, ...]:
    """Run every phase of ``program`` in order, each as one whole-roster
    :func:`run_agent_phase` call (module docstring: this is how the barrier
    is realized). Returns one ``AgentLoopSummary`` per phase, in phase order.

    ``material_for_phase(phase_name, context, sealed_states)`` receives the
    immediately preceding phase's sealed states (``sample_id ->
    AgentStateArtifact``, built by :func:`_seal_phase_state`); the first
    phase receives an empty mapping.
    """

    program.validate()
    if result_kind not in {"task-answer", "artifact"}:
        raise PhaseRunnerError("result_kind must be task-answer or artifact")
    if not callable(material_for_phase):
        raise PhaseRunnerError("run_program requires a callable material_for_phase")

    if request_batch_gate is not None and (
        not callable(request_batch_gate)
        or supply_for_phase is not None
        or review_for_phase is not None
        or any((bootstrap_facet_ids_by_phase or {}).values())
        or any((bootstrap_value_ids_by_phase or {}).values())
        or agent_executor_id != DEFAULT_AGENT_EXECUTOR_ID
    ):
        raise PhaseRunnerError(
            "staged request fit requires plain whole-roster phases without supply or review"
        )

    summaries: list[AgentLoopSummary] = []
    sealed_states: Mapping[str, AgentStateArtifact] = {}
    for phase in program.phases:

        def _phase_material_for_phase(
            name: str,
            context: object,
            *,
            _sealed: Mapping[str, AgentStateArtifact] = sealed_states,
        ) -> object:
            return material_for_phase(name, context, _sealed)

        summary = run_agent_phase(
            phase_name=phase.name,
            program=program,
            adapter=adapter,
            plan=plan,
            data_root=data_root,
            core_client=core_client,
            split_id=split_id,
            knowledge_snapshot=knowledge_snapshot,
            speech_packet_bindings=speech_packet_bindings,
            execution_units=execution_units,
            query_source=query_source,
            trace_sink=trace_sink,
            decoding_params=decoding_params,
            material_for_phase=_phase_material_for_phase,
            supply_for_phase=supply_for_phase,
            review_for_phase=review_for_phase,
            bootstrap_facet_ids=(bootstrap_facet_ids_by_phase or {}).get(
                phase.name, ()
            ),
            bootstrap_value_ids=(bootstrap_value_ids_by_phase or {}).get(
                phase.name, ()
            ),
            expected_row_count=expected_row_count,
            slot_count=slot_count,
            queue_depth=queue_depth,
            agent_executor_id=agent_executor_id,
            agent_runner=agent_runner,
            request_batch_gate=(
                None
                if request_batch_gate is None
                else lambda batch, name=phase.name: request_batch_gate(name, batch)
            ),
            **({"result_kind": "artifact"} if result_kind == "artifact" else {}),
            **({"thinking_policy": thinking_policy} if thinking_policy else {}),
        )
        summaries.append(summary)
        sealed_states = {
            _result_execution_identity(result, execution_units): _seal_phase_state(
                result, phase_name=phase.name, producer_policy_id=program.program_id
            )
            for result in summary.results
        }

    return tuple(summaries)


def run_continuous_program(
    *,
    program: PhaseProgram,
    adapter: TaskAdapter,
    plan: ExecutionPlan,
    data_root: Path,
    core_client: CoreClient,
    split_id: str,
    knowledge_snapshot: KnowledgeSnapshot,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    execution_units: object = None,
    query_source: str = "speech_features",
    trace_sink: AgentTraceSink,
    decoding_params: Mapping[str, object],
    material_for_phase: ProgramMaterialForPhase,
    supply_for_phase: SupplyForPhase | None = None,
    review_for_phase: ReviewForPhase | None = None,
    stop_policy: StopPolicy | None = None,
    tools_for_phase: object = None,
    bootstrap_facet_ids: object = (),
    bootstrap_value_ids: object = (),
    slot_count: int | None = None,
    queue_depth: int | None = None,
    agent_executor_id: str = DEFAULT_AGENT_EXECUTOR_ID,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
    whole_roster_wave_barrier: bool = False,
    request_batch_gate: Callable[[str, tuple], None] | None = None,
    result_kind: str = "task-answer",
    native_episode_binding: object = None,
    initial_feedback_states: Mapping[str, object] | None = None,
    flown_sample_ids: Sequence[str] | None = None,
    thinking_policy: Mapping[str, object] | None = None,
) -> AgentLoopSummary:
    """Run the WHOLE program as ONE continuous per-sample trajectory (E6).

    :func:`run_program` runs each phase as a separate whole-roster
    ``max_contacts=1`` call, which is how the ``select-then-fill`` barrier is
    realized -- and which means a phase's controller never reaches its own
    ``advance``. A TRACED supply decision can only ride the ``advance`` of
    the phase BEFORE the supplied one (``rails.controllers``, "Traced
    supply"), so a program with a supplied non-first phase must run as one
    trajectory instead. This is the shape ``rails.kb_policy.
    KbAlphaBlendController`` has always used and the shape
    ``rails.phase_runner``'s own module docstring already describes as the
    alternative for a non-barrier program.

    Default scheduling refuses a declared whole-roster barrier. Explicit
    whole_roster_wave_barrier retains the same controller trajectory while
    executing one complete roster wave at a time on OpenJiuwen. The optional
    request gate sees real prior-state and evidence requests before each wave.
    Early-stopped samples do not enter later active rosters.

    Returns ONE ``AgentLoopSummary`` for the whole program (one result per
    sample, ``len(program.phases)`` contacts each unless the program's stop
    rule ended a trajectory early).

    ``flown_sample_ids`` (E10c) is the resume-recovery seam and is forwarded
    to ``rails.runner.run_speech_native_agent_loop``, which restricts the
    split it loads to exactly those rows. Because this function's own roster
    is ``speech_packet_bindings`` -- which ``core.flight.runtime`` narrows to
    the same set -- the two must name the same rows, and a disagreement
    refuses here rather than after the contacts are spent. ``None`` -- every
    other caller -- passes nothing on and changes no byte.
    """

    program.validate()
    if (program.stop_rule == "native-role-episode") != (native_episode_binding is not None):
        raise PhaseRunnerError("native role program and episode binding must be supplied together")
    if native_episode_binding is not None:
        from .native_episode_config import NativeEpisodeRunBinding

        if (
            not isinstance(native_episode_binding, NativeEpisodeRunBinding)
            or native_episode_binding.program != program
            or native_episode_binding.material_for_phase is not material_for_phase
            or native_episode_binding.tools_for_phase is not tools_for_phase
            or whole_roster_wave_barrier or request_batch_gate is not None
            or stop_policy is not None
        ):
            raise PhaseRunnerError("native episode custody differs from the continuous program")
    if result_kind not in {"task-answer", "artifact"}:
        raise PhaseRunnerError("result_kind must be task-answer or artifact")
    if not callable(material_for_phase):
        raise PhaseRunnerError(
            "run_continuous_program requires a callable material_for_phase"
        )
    if supply_for_phase is not None and not callable(supply_for_phase):
        raise PhaseRunnerError(
            "run_continuous_program supply_for_phase must be callable or None"
        )
    if review_for_phase is not None and not callable(review_for_phase):
        raise PhaseRunnerError(
            "run_continuous_program review_for_phase must be callable or None"
        )
    if stop_policy is not None and (
        not callable(stop_policy)
        or program.stop_rule != "stop-policy-optional-early-exit"
    ):
        raise PhaseRunnerError(
            "stop_policy requires a callable and optional early-exit program"
        )
    barriers = [phase.name for phase in program.phases if phase.barrier]
    if not isinstance(whole_roster_wave_barrier, bool):
        raise PhaseRunnerError("whole_roster_wave_barrier must be a boolean")
    if whole_roster_wave_barrier and agent_executor_id != DEFAULT_AGENT_EXECUTOR_ID:
        raise PhaseRunnerError(
            "whole-roster waves require the shared OpenJiuwen executor"
        )
    if request_batch_gate is not None and (
        not callable(request_batch_gate) or not whole_roster_wave_barrier
    ):
        raise PhaseRunnerError("continuous request fitting requires whole-roster waves")
    if barriers and not whole_roster_wave_barrier:
        raise PhaseRunnerError(
            f"program {program.program_id!r} declares a barrier on phase(s) "
            f"{barriers}; a barrier is a whole-roster property and can only be "
            "realized by run_program's per-phase waves, never by one continuous "
            "trajectory"
        )
    if not isinstance(decoding_params, Mapping) or "response_format" in decoding_params:
        raise PhaseRunnerError(
            "run-level decoding_params must leave response_format to each "
            "phase's own material"
        )
    if not isinstance(speech_packet_bindings, Mapping) or (
        not speech_packet_bindings and execution_units is None
    ):
        raise PhaseRunnerError("speech_packet_bindings must be a non-empty mapping without units")

    geometry = adapter.serving_geometry()
    resolved_slot_count = slot_count if slot_count is not None else geometry["slots"]
    resolved_queue_depth = (
        queue_depth if queue_depth is not None else resolved_slot_count * 4
    )
    phase_names = list(program.phase_names())

    def controller_factory(sample_id: str) -> EvidenceAgentController:
        holder: dict[str, EvidenceAgentController] = {}

        def _material(name: str, context: object):
            controller = holder["controller"]
            index = phase_names.index(name)
            sealed: Mapping[str, AgentStateArtifact] = {}
            if index > 0:
                artifact = controller.sealed_states.get(phase_names[index - 1])
                if artifact is not None:
                    sealed = {sample_id: artifact}
            material = material_for_phase(name, context, sealed)
            if execution_units is not None:
                from dataclasses import replace
                from .execution_units import scoped_execution_contact_id
                material = replace(material, contact_id=scoped_execution_contact_id(
                    material.contact_id, context.execution_unit_id,
                ))
            return material

        controller = EvidenceAgentController(
            program=program,
            material_for_phase=_material,
            supply_for_phase=supply_for_phase,
            review_for_phase=review_for_phase,
            **(
                {"tools_for_phase": tools_for_phase}
                if tools_for_phase is not None
                else {}
            ),
            **({"stop_policy": stop_policy} if stop_policy is not None else {}),
        )
        holder["controller"] = controller
        return controller

    controller_registry = Registry(f"continuous phase program: {program.program_id}")
    controller_registry.register(program.program_id, controller_factory)

    wave_index = 0

    def gate_wave(batch):
        nonlocal wave_index
        if wave_index >= len(program.phases):
            raise PhaseRunnerError("request wave exceeds the phase program")
        request_batch_gate(program.phases[wave_index].name, batch)
        wave_index += 1

    runner_options = {}
    if flown_sample_ids is not None:
        if isinstance(flown_sample_ids, (str, bytes)) or not isinstance(
            flown_sample_ids, Sequence
        ):
            raise PhaseRunnerError(
                "flown_sample_ids must be a sequence of sample ids, or None"
            )
        if execution_units is not None:
            raise PhaseRunnerError(
                "flown_sample_ids restricts a per-sample roster and cannot be "
                "combined with an execution-unit roster"
            )
        if set(flown_sample_ids) != set(speech_packet_bindings):
            raise PhaseRunnerError(
                "flown_sample_ids and speech_packet_bindings must name the same "
                "rows: one dispatch flies one roster"
            )
        runner_options["flown_sample_ids"] = tuple(flown_sample_ids)
    if initial_feedback_states is not None:
        runner_options["initial_feedback_states"] = initial_feedback_states
    if native_episode_binding is not None:
        runner_options["native_episode_binding"] = native_episode_binding
    if thinking_policy:
        runner_options["thinking_policy"] = thinking_policy
    if whole_roster_wave_barrier:
        runner_options["whole_roster_wave_barrier"] = True
    if request_batch_gate is not None:
        runner_options["request_batch_gate"] = gate_wave

    try:
        summary = agent_runner(
            data_root=data_root,
            plan=plan,
            adapter=adapter,
            core_client=core_client,
            split_id=split_id,
            knowledge_snapshot=knowledge_snapshot,
            speech_packet_bindings=speech_packet_bindings,
            **({"execution_units": execution_units} if execution_units is not None else {}),
            query_source=query_source,
            controller_policy_id=program.program_id,
            bootstrap_facet_ids=bootstrap_facet_ids,
            bootstrap_value_ids=bootstrap_value_ids,
            max_contacts=(program.max_contacts if native_episode_binding is not None else len(program.phases)),
            slot_count=resolved_slot_count,
            queue_depth=resolved_queue_depth,
            trace_sink=trace_sink,
            agent_executor_id=agent_executor_id,
            decoding_params=decoding_params,
            controller_registry=controller_registry,
            trace_record_namespace=program.program_id,
            **({"result_kind": "artifact"} if result_kind == "artifact" else {}),
            **(
                {"knowledge_value_renderer": tools_for_phase.render_values}
                if tools_for_phase is not None
                else {}
            ),
            **runner_options,
        )
    finally:
        # Preserve completed criticism even if fitting or a later contact fails.
        emit_review_records(
            review_for_phase, trace_sink, record_namespace=program.program_id
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise PhaseRunnerError(
            f"program {program.program_id!r} must return a non-empty results tuple"
        )
    sample_ids = [_result_execution_identity(result, execution_units) for result in results]
    if len(set(sample_ids)) != len(sample_ids):
        raise PhaseRunnerError(
            f"program {program.program_id!r} results have "
            f"{'duplicate execution identities' if execution_units is not None else 'duplicate sample ids'}"
        )
    expected_ids = _expected_execution_ids(speech_packet_bindings, execution_units)
    if set(sample_ids) != set(expected_ids) or (
        execution_units is not None and tuple(sample_ids) != expected_ids
    ):
        raise PhaseRunnerError(
            f"program {program.program_id!r} result identities differ from "
            f"{'the declared unit roster' if execution_units is not None else 'speech_packet_bindings'}"
        )
    return summary


__all__ = [
    "DEFAULT_AGENT_EXECUTOR_ID",
    "PhaseRunnerError",
    "ProgramMaterialForPhase",
    "run_agent_phase",
    "run_continuous_program",
    "run_program",
]
