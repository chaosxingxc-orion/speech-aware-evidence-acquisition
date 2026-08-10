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
from . import OJW_WORKFLOW_TIMEOUT_KEY
from .components import (
    START_NODE_ID,
    AcceptAdvance,
    BoundaryResolve,
    FeedBuffer,
    FrozenCoreASR,
)
from .state import ObsSampleState

LOOP_NODE_ID = "obsloop"
END_NODE_ID = "end"


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
    flow.set_end_comp(END_NODE_ID, End(), inputs_schema={"loop": "${" + LOOP_NODE_ID + "}"})
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
    driver's per-sample loop is synchronous and strictly sequential, so the
    framework's async engine runs to completion inside ``asyncio.run`` —
    one fresh event loop, workflow and session per sample.
    ``workflow_timeout_seconds`` is the fragment-declared per-sample ceiling
    (``policy.workflow_timeout_seconds``); a framework timeout kill (error
    100101) is translated into an actionable ``ObsLoopError`` naming the
    knob (inside ``_build_and_invoke``, shared with the batch path)."""

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

    async def _run_all():
        semaphore = asyncio.Semaphore(batch_size)

        async def one(ctx):
            set_current_trace_buffer(ctx.sink)
            async with semaphore:
                state = await asyncio.to_thread(prepare, ctx)
                await _build_and_invoke(
                    state, ctx.adapter.request, workflow_timeout_seconds
                )
                return finalize(ctx, state)

        tasks = [asyncio.create_task(one(ctx)) for ctx in contexts]
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(_run_all())
    for result in results:  # first failure in split-id order wins
        if isinstance(result, BaseException):
            raise result
    return list(results)
