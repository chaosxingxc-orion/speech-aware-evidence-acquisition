"""Per-sample obs-loop execution state shared by the openJiuwen components.

This module imports NO openjiuwen: it is the plain-Python state holder the
driver-side policy builds per sample and constructor-injects into the
framework components (heavy, non-serializable run objects — decoded PCM,
the slice registry, the trace sink — never travel through framework session
state; the loop-carried TEXT state, accepted spans and the conditioning
tail, DOES live in openJiuwen session global state, written by
``AcceptAdvance`` and read back by ``FeedBuffer`` — see ``components.py``).

``should_continue`` is the exact ``FuncCondition`` callable of the
framework loop (``AdvancedLoopComponent(condition=FuncCondition(
state.should_continue))``). It reproduces, in order, everything the plain
policy's ``while`` head and top-of-iteration trim branch decide
(``reproduction.obs_loop.ObsAgentLoopPolicy.run_sample``):

1. runaway guard — the plain policy raises after the iteration that
   crosses ``max_iterations``; here the NEXT round's condition sees the
   crossed counter first thing, flags ``runaway`` and exits the loop, and
   the policy raises the same ``ObsLoopError`` after the workflow returns
   (identical trace prefix, identical number of model calls);
2. skip-bound guard (Task 2, 2026-08-09) — the plain policy raises the
   instant a skipped slice crosses ``obs_slice_skip_max``; here
   ``AcceptAdvance`` flags ``skip_exceeded`` at that same instant and the
   NEXT round's condition sees it first thing (right after the runaway
   check), so no further request is ever sent either way -- the policy
   raises the identically-worded ``ObsLoopError`` after the workflow
   returns (``obs_loop._skip_bound_exceeded_message``);
3. trim consumption — the plain loop handles one long-non-speech span per
   ``while`` round via ``continue``; consecutive rounds without a model
   call collapse here into one condition evaluation that consumes every
   applicable span in sequence, emitting byte-identical OBS trim records
   (same ``-trim{n:04d}`` ids, same fields, same order — a trim round
   never touched anything but the cursor and the trace);
4. exhaustion — ``cursor < duration - epsilon``, the plain ``while`` head;
5. the degenerate zero-length window — the plain loop ``break``s when the
   rounded frame window collapses (``end_frame <= start_frame``); the same
   arithmetic decides here before a body round is ever scheduled, through
   :meth:`ObsSampleState.window_frames` -- which is also where the unit
   plan's own exhaustion (``iteration >= len(plan_units)``, the plain loop's
   OTHER ``break``) becomes the same degenerate window.

Unit plan (OBS-E1; drift #1 of the 2026-09-08 openJiuwen assessment, closed
2026-09-08): ``plan_units`` is this call's units, resolved ONCE per sample by
``policy._prepare_state`` through the SAME ``UnitPlan.units_for`` the plain
policy calls, and ``None`` on every fixed-window run -- which keeps the
clock-derived cutter byte for byte. A plan forces fixed boundary mode, a zero
conditioning tail and zero VAD trim at config-load time
(``ObsLoopConfig.from_values``), so under a plan step 3's trim branch and the
model-boundary tier are inert by construction: the ONLY thing that moves is
where the window comes from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ...core.model import SliceRecord, SliceRegistry
from ...data.loader import SampleRef
from ..obs_loop import ObsAgentLoopPolicy, ObsLoopConfig, PlannedUnit

_EPSILON_SECONDS = 1e-6  # exactly obs_loop._EPSILON_SECONDS (loop-head epsilon)


@dataclass
class ObsSampleState:
    """Everything one whole-call sample's loop needs, plus the loop-carried
    counters. Built once per sample by ``policy.ObsAgentLoopOjwPolicy``."""

    # -- frozen per-sample facts (set once, never mutated) ------------------
    cfg: ObsLoopConfig
    pcm: Sequence[int]
    rate: int
    duration: float
    parent_sha256: str
    transitions: list[float]
    trim_spans: list[tuple[float, float]]
    engine_descriptor: str
    sample: SampleRef
    arm: str
    evidence: list | None
    task_instruction: str
    decoding_params: dict
    request_id_base: str
    retrieval_query: str | None
    registry: SliceRegistry
    data_root: Path
    sink: object  # core.tracing.TraceSink (duck-typed: .emit / .run_id)
    effective_min: float
    max_iterations: int
    # This call's speaker-turn units (OBS-E1), resolved once by
    # ``policy._prepare_state``; ``None`` is the clock-derived fixed-window
    # cutter every sealed run took, byte for byte.
    plan_units: tuple[PlannedUnit, ...] | None = None
    # This sample's per-window hook (KC-E1f; drift #2 of the 2026-09-08
    # openJiuwen assessment, closed by the Decision 12-F port), resolved once
    # by ``policy._prepare_state`` through the SAME policy method the plain
    # executor calls. ``None`` -- ``obs-agent-loop-ojw``'s own answer, always
    # -- leaves every byte of this graph exactly where it was. A hook is
    # consumed in two places and nowhere else: ``FrozenCoreASR`` renders the
    # window's instruction through ``hook.instruction`` and ``AcceptAdvance``
    # delivers the window's span through ``hook.accept``.
    window_hook: object | None = None
    # The RUN's shared dispatch-slot pool
    # (``reproduction.obs_loop.ObsDispatcher``) when the driver's prefetch
    # pipeline is on, else ``None``. Held for the whole SAMPLE by
    # ``runner.execute_obs_workflow`` -- this graph sends one request at a
    # time per sample, so a per-sample hold is both the in-flight bound and
    # the ``id_slot="per-sample"`` affinity the sentinel asks for.
    dispatcher: object | None = None
    # Run-bound representation/config facts stay outside framework JSON state.
    request_extras: dict = field(default_factory=dict)

    # -- loop-carried state (single writer per field; see components.py) ----
    cursor: float = 0.0
    iteration: int = 0
    trims: int = 0
    accepted_spans: list[str] = field(default_factory=list)
    request_ids: list[str] = field(default_factory=list)
    iteration_request_sha256s: list[str] = field(default_factory=list)
    iteration_response_sha256s: list[str] = field(default_factory=list)
    slice_records: list[SliceRecord] = field(default_factory=list)
    trim_events: list[dict] = field(default_factory=list)
    runaway: bool = False
    # Per-slice decode-cap saturation (obs_loop._slice_saturated); single
    # writer AcceptAdvance, same discipline as every other loop-carried
    # counter above -- read back by policy._finalize_sample into the
    # outputs-row SampleOutcome.saturated_slices.
    saturated_slices: int = 0
    # Exhausted-slice skip (Task 2, 2026-08-09, continues the obs_loop
    # E-001 retry finding; module comment above obs_loop.
    # SLICE_RETRYABLE_EXCEPTIONS): single writer AcceptAdvance, same
    # discipline as saturated_slices above -- read back by policy.
    # _finalize_sample into the outputs-row SampleOutcome.skipped_slices.
    skipped_slices: int = 0
    # Skip-bound-exceeded (Task 2): mirrors `runaway` exactly -- AcceptAdvance
    # sets this the instant skipped_slices crosses cfg.slice_skip_max rather
    # than raising directly (a component's invoke() failure is wrapped by
    # the framework into its own error type, which would make the two
    # executors diverge on exactly the exception this bound exists to raise
    # identically -- see policy._finalize_sample, which raises the real
    # ObsLoopError, built by obs_loop._skip_bound_exceeded_message, the SAME
    # function the plain policy calls). should_continue sees the flag on its
    # very next evaluation and stops the loop before any further request is
    # sent -- identical in effect to the plain policy's immediate raise.
    skip_exceeded: bool = False

    def should_continue(self) -> bool:
        """The framework loop's ``FuncCondition`` callable (module docstring
        for the exact plain-policy fragments each step reproduces)."""

        if self.iteration > self.max_iterations:
            self.runaway = True
            return False
        if self.skip_exceeded:
            return False
        while self.cursor < self.duration - _EPSILON_SECONDS:
            trimmed = ObsAgentLoopPolicy._next_trim(
                self.trim_spans, self.cursor, self.cfg.vad_trim_min_seconds
            )
            if trimmed is None:
                break
            span_start, span_end = trimmed
            new_cursor = min(span_end, self.duration)
            self.sink.emit(
                "OBS",
                f"{self.request_id_base}-trim{self.trims:04d}/obs",
                {
                    "obs_trim_from_seconds": self.cursor,
                    "obs_trim_to_seconds": new_cursor,
                    "obs_trim_span_start_seconds": span_start,
                    "obs_trim_span_end_seconds": span_end,
                    "obs_vad_engine": self.engine_descriptor,
                },
            )
            self.trim_events.append(
                {
                    "from_seconds": self.cursor,
                    "to_seconds": new_cursor,
                    "engine": self.engine_descriptor,
                }
            )
            self.trims += 1
            self.cursor = new_cursor
        if not self.cursor < self.duration - _EPSILON_SECONDS:
            return False
        start_frame, end_frame = self.window_frames()
        return end_frame > start_frame

    def window_frames(self) -> tuple[int, int]:
        """The current buffer window's frame bounds — the SAME arithmetic as
        ``should_continue``'s degenerate-window check and the plain policy's
        slice cut, computed in one place so they can never diverge.

        Under a unit plan the bounds are the plan's, not the clock's, and an
        exhausted plan returns a degenerate ``(0, 0)`` window: the plain
        policy's ``if iteration >= len(plan_units): break`` and its
        ``if end_frame <= start_frame: break`` are the same exit here, decided
        before a body round is ever scheduled."""

        if self.plan_units is not None:
            if self.iteration >= len(self.plan_units):
                return 0, 0
            unit = self.plan_units[self.iteration]
            start_frame = int(round(unit.start_seconds * self.rate))
            end_frame = min(int(round(unit.end_seconds * self.rate)), len(self.pcm))
            return start_frame, end_frame
        start_frame = int(round(self.cursor * self.rate))
        end_frame = min(
            int(round((self.cursor + self.cfg.buffer_seconds) * self.rate)), len(self.pcm)
        )
        return start_frame, end_frame

    def slice_record_for(self, iteration: int) -> SliceRecord:
        """The ``SliceRecord`` ``FeedBuffer`` cut for one iteration.

        Read from THIS driver-side state for the same reason ``unit_for``
        is: a ``SliceRecord`` is a run object, not framework session state,
        and the graph's ``${node.field}`` channel carries only the JSON
        ``slice_spec``. ``FeedBuffer`` appends exactly one record per round,
        in iteration order, so the index IS the iteration -- asserted rather
        than assumed, because a hook that repaired the wrong window would be
        a silent defect."""

        if not 0 <= iteration < len(self.slice_records):
            raise IndexError(
                f"iteration {iteration} has no cut slice record "
                f"(this sample has cut {len(self.slice_records)})"
            )
        record = self.slice_records[iteration]
        if record.iteration != iteration:
            raise IndexError(
                f"slice record at index {iteration} reports iteration "
                f"{record.iteration}; the cut order and the loop counter have "
                "diverged"
            )
        return record

    def unit_for(self, iteration: int) -> PlannedUnit | None:
        """The unit that supplied one iteration's window, or ``None`` on the
        fixed-window path. Read from THIS driver-side state rather than from
        framework session state on purpose: the framework's state merge
        deletes None-valued keys (``components.BoundaryResolve``'s own note),
        and a unit's ``speaker`` is legitimately ``None``."""

        if self.plan_units is None:
            return None
        if not 0 <= iteration < len(self.plan_units):
            raise IndexError(
                f"iteration {iteration} is outside this call's "
                f"{len(self.plan_units)}-unit plan"
            )
        return self.plan_units[iteration]
