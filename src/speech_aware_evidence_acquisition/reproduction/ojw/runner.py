"""Build and run the per-sample openJiuwen workflow for the obs loop.

Graph (all framework constructs, composed — never subclassed):

    Workflow:  start(Start) ──> obsloop ──> end(End)
    obsloop =  AdvancedLoopComponent(
                   body = LoopGroup[ feed ─> asr ─> boundary ─> accept ],
                   condition = FuncCondition(state.should_continue))

- ``LoopGroup`` carries the OBS sliding-buffer loop body; the four nodes
  are connected in a LINEAR chain, so every Pregel super-step has exactly
  one ready node — the engine's execution order is structurally
  deterministic here (rebuild-notes §determinism, verified empirically by
  the 5x equivalence runs in ``tests/unit/test_obs_loop_ojw.py``).
- ``FuncCondition(state.should_continue)`` is the audio-not-exhausted
  condition (plus the trim/runaway/degenerate-window decisions the plain
  policy takes at the top of its ``while`` loop — ``state.py`` docstring).
- The loop-max guard is ``state.max_iterations`` — computed from config
  with the plain policy's exact arithmetic and enforced by the SAME
  condition (the framework's ``LOOP_NUMBER_MAX_LIMIT`` env applies only to
  number-typed ``LoopComponent`` loops, not ``FuncCondition`` loops, so
  the guard rides in the condition callable).
- ``AdvancedLoopComponent`` is the framework's own loop engine (what its
  ``LoopComponent`` wraps); we compose it directly because the
  ``LoopComponent`` input schema only admits static loop types
  (array/number/expression/always-true), not a dynamic Python condition.

Iteration-local dataflow uses the framework's ``${node.field}`` input
schemas; static per-sample values enter through ``Start`` from
``build_invoke_inputs``; loop-carried text state lives in session global
state (``components.ACCEPTED_SPANS_KEY``).

This module imports openjiuwen at module level and is imported only behind
``policy.py``'s lazy seam.
"""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Awaitable, Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

from openjiuwen.core.common.exception.codes import StatusCode
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen.core.session import WORKFLOW_EXECUTE_TIMEOUT
from openjiuwen.core.workflow import (
    End,
    FuncCondition,
    LoopGroup,
    Start,
    Workflow,
    create_workflow_session,
)

# AdvancedLoopComponent is the framework loop engine LoopComponent itself
# wraps; it is not re-exported by the workflow package root.
from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
    AdvancedLoopComponent,
)

from ...core.tracing import set_current_trace_buffer
from ..obs_loop import ObsLoopError
from . import OJW_WORKFLOW_TIMEOUT_KEY, OpenJiuwenExecutorError
from .components import (
    START_NODE_ID,
    AcceptAdvance,
    AggregateAgentWave,
    BoundaryResolve,
    ExecuteAgentContact,
    FeedBuffer,
    FrozenCoreASR,
    PrepareAgentWave,
)
from .state import ObsSampleState

LOOP_NODE_ID = "obsloop"
END_NODE_ID = "end"

# Slot affinity (SAEA-BENCH-idslot-q4km, 2026-08-11). A model fragment may
# declare decoding_params.id_slot = "per-sample"; the batch executor below
# resolves that sentinel to an allocated llama-server slot integer so every
# request of one sample lands on ONE slot, keeping the sample's stable
# evidence prefix in that slot's KV (measured under free assignment: zero
# prefix-cache hits; ~4.4k evidence tokens re-prefilled on every slice of an
# evidence arm). Zero concurrency cost by construction: a sample's slices
# are strictly sequential (slice k+1 needs slice k's boundary), so its
# pinned slot is always free when its next request is issued. The allocated
# slot NUMBER depends on completion timing under rolling concurrency, which
# changes request bytes across runs — irrelevant to numerics (the slot id
# selects a cache, not arithmetic) and run-to-run byte identity is already
# absent at this protocol (2026-08-11 determinism read-out).
SLOT_AFFINITY_SENTINEL = "per-sample"

ContactResult = TypeVar("ContactResult")


def _resolve_slot_affinity(state: "ObsSampleState", slot: int) -> bool:
    """Replace the sentinel with the allocated slot integer. Returns True
    iff this state asked for affinity (its slot must then be released when
    the sample settles)."""

    if state.decoding_params.get("id_slot") == SLOT_AFFINITY_SENTINEL:
        state.decoding_params["id_slot"] = int(slot)
        return True
    return False


def build_obs_workflow(state: ObsSampleState, adapter_request) -> Workflow:
    """The per-sample workflow graph (module docstring). ``adapter_request``
    is the injected single-door callable handed to ``FrozenCoreASR``."""

    loop_group = LoopGroup()
    loop_group.add_workflow_comp("feed", FeedBuffer(state))
    loop_group.add_workflow_comp(
        "asr",
        FrozenCoreASR(adapter_request, state),
        inputs_schema={"slice_spec": "${feed.slice_spec}", "tail": "${feed.tail}"},
    )
    loop_group.add_workflow_comp(
        "boundary",
        BoundaryResolve(state),
        inputs_schema={"slice_spec": "${feed.slice_spec}", "text": "${asr.text}"},
    )
    loop_group.add_workflow_comp(
        "accept",
        AcceptAdvance(state),
        inputs_schema={
            "slice_spec": "${feed.slice_spec}",
            "tail": "${feed.tail}",
            "request_id": "${asr.request_id}",
            "request_sha256": "${asr.request_sha256}",
            "response_sha256": "${asr.response_sha256}",
            "retry_of": "${asr.retry_of}",
            "saturated": "${asr.saturated}",
            "skipped": "${asr.skipped}",
            "accepted": "${boundary.accepted}",
            "dropped": "${boundary.dropped}",
            "resolution": "${boundary.resolution}",
        },
    )
    loop_group.start_nodes(["feed"])
    loop_group.end_nodes(["accept"])
    loop_group.add_connection("feed", "asr")
    loop_group.add_connection("asr", "boundary")
    loop_group.add_connection("boundary", "accept")

    loop_node = AdvancedLoopComponent(loop_group, FuncCondition(state.should_continue))

    flow = Workflow()
    flow.set_start_comp(
        START_NODE_ID,
        Start(),
        inputs_schema={
            "sample": "${sample}",
            "task_instruction": "${task_instruction}",
            "evidence": "${evidence}",
            "arm": "${arm}",
            "decoding_params": "${decoding_params}",
            "retrieval_query": "${retrieval_query}",
        },
    )
    flow.set_end_comp(
        END_NODE_ID, End(), inputs_schema={"loop": "${" + LOOP_NODE_ID + "}"}
    )
    flow.add_workflow_comp(LOOP_NODE_ID, loop_node)
    flow.add_connection(START_NODE_ID, LOOP_NODE_ID)
    flow.add_connection(LOOP_NODE_ID, END_NODE_ID)
    return flow


def build_invoke_inputs(state: ObsSampleState) -> dict[str, object]:
    """The workflow invoke inputs Start maps into session state — the
    driver-resolved static values ``components._static`` reads back."""

    return {
        "sample": {
            "carrier_lock_key": state.sample.carrier_lock_key,
            "sample_id": state.sample.sample_id,
            "request_id_base": state.request_id_base,
        },
        "task_instruction": state.task_instruction,
        "evidence": state.evidence,
        "arm": state.arm,
        "decoding_params": dict(state.decoding_params),
        "retrieval_query": state.retrieval_query,
    }


async def _build_and_invoke(
    state: ObsSampleState, adapter_request, workflow_timeout_seconds: float
) -> None:
    # Built INSIDE the running loop: the framework's graph vertices create
    # asyncio primitives at construction time, which must belong to the same
    # event loop that drives them.
    flow = build_obs_workflow(state, adapter_request)
    # Per-sample execution ceiling (real-run blocker 2026-08-08): the
    # framework's builtin session env WORKFLOW_EXECUTE_TIMEOUT defaults to
    # 60 s (SessionConfig._load_builtin_configs_) and Workflow.invoke kills
    # the run at that limit (error 100101). The sanctioned override is the
    # session env: create_workflow_session(envs=...) -> Workflow.
    # _create_workflow_session -> config().set_envs(...), which merges OVER
    # the builtin default. <= 0 disables (framework convention).
    session = create_workflow_session(
        envs={WORKFLOW_EXECUTE_TIMEOUT: float(workflow_timeout_seconds)}
    )
    try:
        await flow.invoke(inputs=build_invoke_inputs(state), session=session)
    except BaseError as error:
        if getattr(error, "code", None) == StatusCode.WORKFLOW_EXECUTION_TIMEOUT.code:
            raise ObsLoopError(
                f"openJiuwen killed sample {state.sample.sample_id!r} at the "
                f"per-sample workflow ceiling ({workflow_timeout_seconds} s); "
                f"raise {OJW_WORKFLOW_TIMEOUT_KEY} in the baseline fragment "
                "(<= 0 disables the limit) if the sample legitimately needs "
                "longer"
            ) from error
        raise


def execute_obs_workflow(
    state: ObsSampleState, adapter_request, workflow_timeout_seconds: float
) -> None:
    """Build the graph and drive it to completion. Synchronous wrapper: the
    driver's per-sample loop is synchronous, so the framework's async engine
    runs to completion inside ``asyncio.run`` — one fresh event loop,
    workflow and session per sample. ``workflow_timeout_seconds`` is the
    fragment-declared per-sample ceiling
    (``policy.workflow_timeout_seconds``); a framework timeout kill (error
    100101) is translated into an actionable ``ObsLoopError`` naming the
    knob (inside ``_build_and_invoke``, shared with the batch path).

    THE RUN'S DISPATCHER (obs-pipeline throughput fix, ported to this
    executor by owner Decision 12-F, 2026-09-08). ``state.dispatcher`` is
    ``None`` for every config written before the knob existed, and this
    function then behaves exactly as it always has: strictly one sample at a
    time, slot 0 trivially free. When ``core.driver.run_experiment`` runs the
    prefetch pipeline it hands every sample the RUN's
    ``reproduction.obs_loop.ObsDispatcher``, and one slot of that pool is
    held for the whole of THIS sample's model phase:

    * it is the in-flight bound -- this graph sends one request at a time per
      sample, so "samples holding a slot" and "requests in flight" are the
      same number, and the pool's width caps both;
    * it is also the ``id_slot="per-sample"`` affinity itself, in its
      strongest form: the integer is taken once and held until the sample
      settles, so every slice of one call really does land on one
      llama-server slot (the plain policy's pipelined path can only resolve
      the sentinel PER REQUEST, because one sample there spans the pool);
    * it is acquired AFTER ``policy._prepare_state`` has decoded and cut, so
      the next call's CPU phase overlaps this call's requests -- which is the
      whole point of the prefetch, and the reason the acquire is here rather
      than around ``run_sample``.
    """

    dispatcher = state.dispatcher
    if dispatcher is None:
        # Sequential single-sample execution: slot 0 is trivially free.
        _resolve_slot_affinity(state, 0)
        asyncio.run(_build_and_invoke(state, adapter_request, workflow_timeout_seconds))
        return
    with dispatcher.dispatch_slot() as slot:
        _resolve_slot_affinity(state, slot)
        asyncio.run(_build_and_invoke(state, adapter_request, workflow_timeout_seconds))


def execute_obs_batch(
    contexts,
    *,
    prepare,
    finalize,
    batch_size: int,
    workflow_timeout_seconds: float,
) -> list:
    """Sample-level concurrency (owner batching directive 2026-08-08): up to
    ``batch_size`` per-sample workflows in flight at once over ONE event
    loop — ``asyncio.gather`` over per-sample tasks, a semaphore bounding
    concurrency AND peak memory (a sample's PCM is decoded inside its task,
    under the semaphore, so at most ``batch_size`` decoded calls are ever
    live). Real overlap comes from ``FrozenCoreASR`` hopping the blocking
    adapter call to a worker thread (``asyncio.to_thread``); everything
    intra-sample stays strictly sequential (slice k+1 needs slice k's
    boundary — inherent).

    Determinism contract: results are returned aligned to ``contexts``
    (split-id order); on failure, ALL tasks are allowed to settle
    (``return_exceptions=True`` — no completion-order cancellation) and the
    FIRST failed sample's error in split-id order is raised. Each task
    binds its sample's trace sink as the current trace-routing target
    (``core.tracing.set_current_trace_buffer``, task-local contextvar,
    propagated into ``to_thread`` workers) so the shared adapter's records
    land in that sample's buffer."""

    contexts = list(contexts)

    # Two schedulers must never compose silently (the same rule
    # ObsLoopConfig.from_values and core.driver.run_experiment both enforce
    # from their own side): this path owns sample-level concurrency and its
    # own free-slot pool, so a run dispatcher reaching it would mean the
    # driver's prefetch pipeline and this semaphore were both live. Refused
    # here too, because a silently ignored dispatcher would look exactly like
    # a working one.
    if any(getattr(ctx, "extras", {}).get("obs_dispatcher") is not None for ctx in contexts):
        raise ObsLoopError(
            "the openJiuwen sample-batch executor cannot run under the driver's "
            "prefetch dispatcher: obs_batch_samples > 1 already owns sample-level "
            "concurrency and its own slot pool; set obs_prefetch_depth 0 or "
            "obs_batch_samples 1"
        )

    async def _run_all():
        semaphore = asyncio.Semaphore(batch_size)
        # Free-slot pool for slot affinity: at most ``batch_size`` samples
        # hold the semaphore, so a pool of the same size can never run dry.
        # Allocation and release are synchronous list operations inside one
        # event loop — no await sits between pop and use.
        free_slots = list(range(batch_size))

        async def one(ctx):
            set_current_trace_buffer(ctx.sink)
            async with semaphore:
                state = await asyncio.to_thread(prepare, ctx)
                pinned = _resolve_slot_affinity(state, free_slots[0])
                if pinned:
                    free_slots.pop(0)
                try:
                    await _build_and_invoke(
                        state, ctx.adapter.request, workflow_timeout_seconds
                    )
                    return finalize(ctx, state)
                finally:
                    if pinned:
                        free_slots.append(int(state.decoding_params["id_slot"]))

        tasks = [asyncio.create_task(one(ctx)) for ctx in contexts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(_run_all())
    for result in results:  # first failure in split-id order wins
        if isinstance(result, BaseException):
            raise result
    return list(results)


def build_speech_agent_workflow(
    *,
    prepare_wave: Callable[[object], int],
    invoke_contact: Callable[[int], Awaitable[Mapping[str, object]]],
    aggregate_wave: Callable[[tuple[Mapping[str, object], ...], object], None],
    should_continue: Callable[[], bool],
    branch_count: int,
) -> Workflow:
    """Build one native openJiuwen fan-out/fan-in AgentLoop graph."""

    loop_group = LoopGroup()
    loop_group.add_workflow_comp(
        "prepare_agent_wave",
        PrepareAgentWave(prepare_wave, branch_count),
    )
    contact_node_ids: list[str] = []
    for branch_index in range(branch_count):
        node_id = f"agent_contact_{branch_index}"
        contact_node_ids.append(node_id)
        loop_group.add_workflow_comp(
            node_id,
            ExecuteAgentContact(branch_index, invoke_contact),
            inputs_schema={"active_count": "${prepare_agent_wave.active_count}"},
        )
        loop_group.add_connection("prepare_agent_wave", node_id)
    aggregate_inputs: dict[str, object] = {
        "active_count": "${prepare_agent_wave.active_count}"
    }
    for branch_index, node_id in enumerate(contact_node_ids):
        aggregate_inputs[f"branch_{branch_index}"] = {
            "active": "${" + node_id + ".active}",
            "response_text": "${" + node_id + ".response_text}",
            "slot_id": "${" + node_id + ".slot_id}",
            "response_sha256": "${" + node_id + ".response_sha256}",
        }
    loop_group.add_workflow_comp(
        "aggregate_agent_wave",
        AggregateAgentWave(branch_count, aggregate_wave),
        inputs_schema=aggregate_inputs,
    )
    loop_group.start_nodes(["prepare_agent_wave"])
    loop_group.end_nodes(["aggregate_agent_wave"])
    loop_group.add_connection(contact_node_ids, "aggregate_agent_wave")

    flow = Workflow()
    flow.set_start_comp("agent_start", Start(), inputs_schema={})
    flow.add_workflow_comp(
        "agent_loop",
        AdvancedLoopComponent(loop_group, FuncCondition(should_continue)),
    )
    flow.set_end_comp(
        "agent_end",
        End(),
        inputs_schema={"agent_loop": "${agent_loop}"},
    )
    flow.add_connection("agent_start", "agent_loop")
    flow.add_connection("agent_loop", "agent_end")
    return flow


def execute_speech_agent_workflows(
    states: Sequence[object],
    *,
    prepare_wave: Callable[[object, object], int] | None = None,
    invoke_contact: Callable[[object, int, int], Mapping[str, object]] | None = None,
    aggregate_wave: (
        Callable[[object, tuple[Mapping[str, object], ...], object], None] | None
    ) = None,
    should_continue: Callable[[object], bool] | None = None,
    branch_count: int,
    slot_count: int,
    queue_depth: int,
    workflow_timeout_seconds: float,
    episode_invoker: Callable[..., Awaitable[object]] | None = None,
    local_tool_workers: int = 0,
) -> list[object]:
    """Run speech Agent workflows on one openJiuwen event loop.

    The framework owns the loop, parallel graph execution, and fan-in
    barrier. This wrapper admits at most ``queue_depth`` workflows, pins each
    admitted trajectory to one llama.cpp slot from its first contact through
    workflow completion, and serializes that trajectory's branches on the
    pinned slot. Cross-sample workflows remain parallel. A cancelled
    component waits for its blocking worker to settle before the slot can be
    released. The repository's frozen-core callback remains the only model
    door; no framework LLM client is instantiated.

    When ``episode_invoker`` is configured, it replaces only the legacy
    graph construction for one admitted state. It receives that state, a
    generic ``run_contact(blocking_contact)`` awaitable, and the configured
    OpenJiuwen session. ``blocking_contact`` takes the trajectory's stable
    primary slot id and runs through the same serialized, shielded worker
    lifecycle as a legacy branch. The invoker must use the supplied session
    for its workflow invocation so the configured framework timeout remains
    authoritative. With no invoker, the legacy graph path is unchanged.

    Opt-in local_tool_workers supplies a fourth keyword-only callback,
    run_local(blocking_tool). It releases the trajectory's model slot before
    waiting for the shared CPU worker pool; the next model contact reacquires a
    slot. The synchronous tool settles before cancellation completes. This is a
    resource policy only: the caller still owns tool authority, accounting and
    evidence custody. The default retains stable slot affinity.
    """

    if (
        isinstance(local_tool_workers, bool)
        or not isinstance(local_tool_workers, int)
        or not 0 <= local_tool_workers <= 8
        or (local_tool_workers and episode_invoker is None)
    ):
        raise ValueError("local_tool_workers requires a native episode and an integer in 0..8")

    if episode_invoker is None and any(
        callback is None
        for callback in (
            prepare_wave,
            invoke_contact,
            aggregate_wave,
            should_continue,
        )
    ):
        raise TypeError(
            "legacy speech Agent execution requires prepare_wave, "
            "invoke_contact, aggregate_wave, and should_continue"
        )

    ordered_states = list(states)

    async def _run_all():
        local_executor = (
            ThreadPoolExecutor(max_workers=local_tool_workers, thread_name_prefix="saea-local-tool")
            if local_tool_workers else None
        )
        local_capacity = asyncio.Semaphore(local_tool_workers)
        slots: asyncio.Queue[int] = asyncio.Queue(maxsize=slot_count)
        for slot_id in range(slot_count):
            slots.put_nowait(slot_id)

        async def one(state: object):
            primary_slot_id: int | None = None
            slot_assignment_lock = asyncio.Lock()
            contact_lock = asyncio.Lock()
            worker_tasks: set[asyncio.Future[object]] = set()

            async def primary_slot() -> int:
                nonlocal primary_slot_id
                if primary_slot_id is None:
                    async with slot_assignment_lock:
                        if primary_slot_id is None:
                            primary_slot_id = await slots.get()
                return primary_slot_id

            async def run_contact(
                blocking_contact: Callable[[int], ContactResult],
            ) -> ContactResult:
                async with contact_lock:
                    slot_id = await primary_slot()
                    worker = asyncio.create_task(
                        asyncio.to_thread(blocking_contact, slot_id)
                    )
                    worker_tasks.add(worker)
                    try:
                        return await asyncio.shield(worker)
                    except asyncio.CancelledError:
                        # Cancelling the await does not stop the synchronous
                        # worker. Keep the trajectory lock and primary slot
                        # until that worker has genuinely settled.
                        await asyncio.gather(worker, return_exceptions=True)
                        raise
                    finally:
                        if worker.done():
                            worker_tasks.discard(worker)

            async def run_local(
                blocking_tool: Callable[[], ContactResult],
            ) -> ContactResult:
                nonlocal primary_slot_id
                if local_executor is None:
                    raise RuntimeError("local tool scheduling was not configured")
                async with contact_lock:
                    if primary_slot_id is not None:
                        slots.put_nowait(primary_slot_id)
                        primary_slot_id = None
                    # Wait before submitting, so cancellation while queued never
                    # causes a tool contact after its caller has stopped.
                    async with local_capacity:
                        context = contextvars.copy_context()
                        worker = asyncio.get_running_loop().run_in_executor(
                            local_executor, context.run, blocking_tool
                        )
                        worker_tasks.add(worker)
                        try:
                            return await asyncio.shield(worker)
                        except asyncio.CancelledError:
                            # Repeated cancellation must not cancel the Future
                            # while its synchronous tool still mutates custody.
                            while not worker.done():
                                try:
                                    await asyncio.shield(worker)
                                except asyncio.CancelledError:
                                    continue
                                except BaseException:
                                    break
                            if not worker.cancelled():
                                worker.exception()
                            raise
                        finally:
                            if worker.done():
                                worker_tasks.discard(worker)

            async def invoke_branch(branch_index: int) -> Mapping[str, object]:
                assert invoke_contact is not None
                return await run_contact(
                    lambda slot_id: invoke_contact(
                        state,
                        branch_index,
                        slot_id,
                    )
                )

            if episode_invoker is None:
                assert prepare_wave is not None
                assert aggregate_wave is not None
                assert should_continue is not None
                flow = build_speech_agent_workflow(
                    prepare_wave=lambda session: prepare_wave(state, session),
                    invoke_contact=invoke_branch,
                    aggregate_wave=lambda responses, session: aggregate_wave(
                        state, responses, session
                    ),
                    should_continue=lambda: should_continue(state),
                    branch_count=branch_count,
                )
            session = create_workflow_session(
                envs={WORKFLOW_EXECUTE_TIMEOUT: float(workflow_timeout_seconds)}
            )
            try:
                try:
                    if episode_invoker is None:
                        await flow.invoke(inputs={}, session=session)
                    elif local_tool_workers:
                        await episode_invoker(state, run_contact, session, run_local=run_local)
                    else:
                        await episode_invoker(state, run_contact, session)
                except BaseError as error:
                    if (
                        getattr(error, "code", None)
                        == StatusCode.WORKFLOW_EXECUTION_TIMEOUT.code
                    ):
                        raise OpenJiuwenExecutorError(
                            "openJiuwen killed a speech Agent workflow at the "
                            f"{workflow_timeout_seconds}-second ceiling"
                        ) from error
                    raise
                return state
            finally:
                if worker_tasks:
                    await asyncio.gather(*tuple(worker_tasks), return_exceptions=True)
                if primary_slot_id is not None:
                    slots.put_nowait(primary_slot_id)

        failures: dict[int, BaseException] = {}
        next_index = 0
        admission_lock = asyncio.Lock()

        async def next_admission() -> tuple[int, object] | None:
            nonlocal next_index
            async with admission_lock:
                if failures or next_index >= len(ordered_states):
                    return None
                admitted = (next_index, ordered_states[next_index])
                next_index += 1
                return admitted

        async def admission_worker() -> None:
            while True:
                admitted = await next_admission()
                if admitted is None:
                    return
                index, state = admitted
                try:
                    await one(state)
                except BaseException as error:
                    async with admission_lock:
                        failures[index] = error
                    return

        worker_count = min(queue_depth, len(ordered_states))
        admission_workers = [
            asyncio.create_task(admission_worker()) for _ in range(worker_count)
        ]
        try:
            await asyncio.gather(*admission_workers)
            return failures
        finally:
            # Admission cleanup drains any synchronous contact before pool shutdown.
            await asyncio.gather(*admission_workers, return_exceptions=True)
            if local_executor is not None:
                local_executor.shutdown(wait=True, cancel_futures=True)

    failures = asyncio.run(_run_all())
    if failures:
        raise failures[min(failures)]
    return ordered_states
