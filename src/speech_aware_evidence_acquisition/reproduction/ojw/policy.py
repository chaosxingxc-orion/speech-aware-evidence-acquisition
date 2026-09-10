"""The ``obs-agent-loop-ojw`` policy: the obs loop on the openJiuwen executor.

Same contract as the plain ``obs-agent-loop`` policy (``reproduction.
obs_loop`` — one whole-call sample -> N buffer-slice requests -> one
stitched hypothesis; same trace kinds/fields, same slice rail, same
outputs-row shape), with the per-sample loop orchestrated by the
openJiuwen framework (``runner.py`` graph) instead of a plain ``while``.
Equivalence between the two executors is a hard red line
(``docs/readiness/2026-08-08-openjiuwen-adoption.md`` §3) and is asserted
by ``tests/unit/test_obs_loop_ojw.py`` over shared synthetic fixtures.

Batching (owner directive 2026-08-08): this policy also implements the
``run_samples`` batch seam — up to ``obs_batch_samples`` per-sample
workflows run concurrently (``runner.execute_obs_batch``:
``asyncio.gather`` + semaphore; the model call itself hops to a worker
thread inside ``FrozenCoreASR``, so N samples genuinely overlap while each
sample's own slice chain stays strictly sequential — slice k+1 depends on
slice k's boundary, which is inherent, not an implementation limit). The
per-sample pipeline is shared VERBATIM between the two entry points
(``_prepare_state`` / ``_finalize_sample`` below), so a batched sample is
byte-identical to a sequential one.

This module imports NO openjiuwen. The framework enters through exactly
one lazy seam (``_load_runner``), so registering this policy in
``core.policies`` costs nothing when openjiuwen is absent — the policy
then refuses at run time with the install hint (D2 gate: openjiuwen never
enters ``pyproject.toml``).

Everything the plain policy computes OUTSIDE its request loop is computed
here by the same functions of the same modules (``ObsLoopConfig``,
``decode_parent_pcm``, ``_vad_flags``, ``vad_transitions``,
``nonspeech_spans``, ``_sha256_file``, ``_canonical_bytes`` — resolved
through the ``obs_loop`` module object so test monkeypatches apply to both
executors identically), and the loop-internal steps live in
``components.py`` calling the same ``obs_audio``/``core.model.slices``
primitives. What differs is orchestration only.

Unit plan (OBS-E1), 2026-09-08: this executor consumes ``obs_unit_plan``
instead of refusing it. Drift #1 of the 2026-09-08 openJiuwen assessment
recorded the refusal as an honest fail-closed stop-gap -- the executor's
window came from a clock, so a plan reaching it would have been silently
ignored -- and the port that closes it is three lines of state
(``state.ObsSampleState.plan_units`` plus a plan-aware ``window_frames``),
the plain policy's own ``is_final`` form in ``FeedBuffer``, the plain
policy's own ``_unit_trace_fields`` in ``AcceptAdvance``, and the plain
policy's own ``units_for``/``max_iterations``/``boundary_mode``
substitutions here. No unit-plan logic is reimplemented: every decision is
made by a function ``reproduction.obs_loop`` already owns, and the
``unit-plan`` scenario of ``tests/unit/test_obs_loop_ojw.py``'s equivalence
suite proves the two executors deliver the same media, records and bytes.

Window hook (KC-E1f), 2026-09-08, owner Decision 12-F: drift #2 of the same
assessment is closed the same way. ``_window_hook`` below has the plain
policy's exact signature and its exact default (``None``); ``_prepare_state``
carries the resolved hook into ``ObsSampleState``; ``FrozenCoreASR`` renders
the window instruction through it and ``AcceptAdvance`` delivers the window's
span through it. No hook LOGIC is implemented here --
``reproduction.repair_loop`` owns the one builder both executors call, and
``obs-repair-loop-ojw`` is two overridden methods over this class. The
``window-hook`` scenario of the equivalence suite compares this graph against
the plain policy's SEQUENTIAL cutter, which gained the same site in the same
change, so a hooked run is byte-identical across executors.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Sequence

from ...core.base import SampleContext, SampleOutcome
from ...core.model import SliceRegistry
from ...data.loader import SampleRef
from ...e0.artifacts import write_json_artifact
from .. import obs_loop
from ..obs_audio import nonspeech_spans, vad_transitions
from ..obs_loop import (
    OBS_DERIVATION_SCHEMA,
    OBS_UNIT_PLAN_BOUNDARY_MODE,
    SLICE_SAMPLE_RATE_HZ,
    ObsLoopConfig,
    ObsLoopError,
)
from . import (
    DEFAULT_WORKFLOW_TIMEOUT_SECONDS,
    OJW_INSTALL_HINT,
    OJW_POLICY_NAME,
    OJW_WORKFLOW_TIMEOUT_KEY,
)
from .state import ObsSampleState

__all__ = ["OJW_POLICY_NAME", "ObsAgentLoopOjwPolicy", "workflow_timeout_seconds"]


def _load_runner():
    """The ONE lazy seam through which openjiuwen enters (module docstring):
    fail-closed with the install hint when the framework is absent."""

    try:
        from . import runner  # noqa: PLC0415 (lazy: openjiuwen-dependent)
    except ImportError as error:
        raise ObsLoopError(OJW_INSTALL_HINT) from error
    return runner


def workflow_timeout_seconds(config_values) -> float:
    """The per-sample workflow execution ceiling from the baseline fragment
    (``ojw_workflow_timeout_seconds``; package ``__init__`` docstring for the
    real-run blocker this replaces the framework's builtin 60 s default
    for). Absent -> ``DEFAULT_WORKFLOW_TIMEOUT_SECONDS``; a non-finite,
    boolean or non-numeric value refuses (a typo here must never silently
    re-enable the 60 s kill); <= 0 disables the limit (framework
    convention, ``Workflow._execute_with_timeout``)."""

    value = config_values.get(OJW_WORKFLOW_TIMEOUT_KEY, DEFAULT_WORKFLOW_TIMEOUT_SECONDS)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ObsLoopError(
            f"config {OJW_WORKFLOW_TIMEOUT_KEY} must be a finite number of seconds "
            f"(<= 0 disables the limit), got {value!r}"
        )
    return float(value)


def _context_facts(ctx: SampleContext) -> tuple[SliceRegistry, Path, Path, Path, dict]:
    """Validate and unpack the driver-supplied run facts — the same checks
    (and messages) for the sequential and batched entry points."""

    registry = ctx.extras.get("slice_registry")
    if not isinstance(registry, SliceRegistry):
        raise ObsLoopError(
            f"{OJW_POLICY_NAME} requires a core.model.SliceRegistry in "
            "SampleContext.extras['slice_registry'] (supplied by "
            "core.driver.run_experiment); refusing to cut unchained slices"
        )
    try:
        data_root = Path(ctx.extras["data_root"])
        run_dir = Path(ctx.extras["run_dir"])
        repo_root = Path(ctx.extras["repo_root"])
        config_values = ctx.extras["config_values"]
    except KeyError as error:
        raise ObsLoopError(
            f"{OJW_POLICY_NAME} SampleContext.extras lacks {error}; supplied "
            "only by core.driver.run_experiment"
        ) from error
    return registry, data_root, run_dir, repo_root, config_values


def _prepare_state(
    ctx: SampleContext, cfg: ObsLoopConfig, window_hook: object | None = None
) -> ObsSampleState:
    """Decode the parent, run VAD, and build the per-sample loop state —
    exactly the plain policy's pre-loop section, via the same ``obs_loop``
    module functions (monkeypatch-compatible). CPU/decoder-bound and free of
    shared mutable state, so the batch runner may call it from a worker
    thread.

    ``window_hook`` is this sample's per-window hook, resolved by the calling
    policy's own ``_window_hook`` (the SAME method name and the SAME shape the
    plain policy uses). ``None`` -- the base executor's answer, always -- is
    byte-identical to every run before the seam existed."""

    registry, data_root, _, _, _ = _context_facts(ctx)
    sample: SampleRef = ctx.sample
    rate = SLICE_SAMPLE_RATE_HZ
    parent_path = data_root / sample.media_relpath
    pcm = obs_loop.decode_parent_pcm(parent_path, rate)
    if not len(pcm):
        raise ObsLoopError(f"decoded zero samples from {parent_path}")
    duration = len(pcm) / rate
    parent_sha256 = obs_loop._sha256_file(parent_path)

    need_vad = cfg.boundary_mode == "model" or cfg.vad_trim_min_seconds > 0
    engine_descriptor = "vad-not-run"
    transitions: list[float] = []
    trim_spans: list[tuple[float, float]] = []
    if need_vad:
        flags, engine_descriptor = obs_loop._vad_flags(pcm, rate, cfg.vad_engine)
        frame_seconds = 0.03
        transitions = vad_transitions(flags, frame_seconds)
        if cfg.vad_trim_min_seconds > 0:
            trim_spans = nonspeech_spans(
                flags, frame_seconds, min_seconds=cfg.vad_trim_min_seconds
            )

    evidence = ctx.evidence if ctx.arm != "bare-core" else None
    effective_min = (
        cfg.buffer_seconds if cfg.boundary_mode == "fixed" else cfg.min_advance_seconds
    )
    max_iterations = math.ceil(duration / max(effective_min, 1e-9)) + len(trim_spans) + 8

    # The unit plan, resolved ONCE per sample before the first cut (OBS-E1
    # preregistration section 8.3) -- through the SAME ``UnitPlan.units_for``
    # the plain policy calls at both of ITS cut sites, so a roster call the
    # plan does not cover, or a plan cut against different audio, refuses here
    # with the identical message before either executor writes a byte.
    # ``None`` is the historical fixed-window cutter, byte for byte.
    plan_units = (
        None
        if cfg.unit_plan is None
        else cfg.unit_plan.units_for(sample.sample_id, duration)
    )
    if plan_units is not None:
        # The plan's own length IS the iteration bound; the clock-derived one
        # above describes a cutter that is not running. Exactly the plain
        # policy's own substitution.
        max_iterations = len(plan_units) + 8

    from ..window_controller import build_controller_window_hook

    window_hook = build_controller_window_hook(ctx, cfg, window_hook)
    return ObsSampleState(
        cfg=cfg,
        pcm=pcm,
        rate=rate,
        duration=duration,
        parent_sha256=parent_sha256,
        transitions=transitions,
        trim_spans=trim_spans,
        engine_descriptor=engine_descriptor,
        sample=sample,
        arm=ctx.arm,
        evidence=evidence,
        task_instruction=ctx.task_instruction,
        decoding_params=dict(ctx.decoding_params),
        request_id_base=ctx.request_id_base,
        retrieval_query=ctx.retrieval_query,
        registry=registry,
        data_root=data_root,
        sink=ctx.sink,
        effective_min=effective_min,
        max_iterations=max_iterations,
        plan_units=plan_units,
        window_hook=window_hook,
        # The run's shared dispatch-slot pool, supplied by
        # ``core.driver.run_experiment`` only when ``obs_prefetch_depth > 0``;
        # absent (None) for every config written before 2026-09-08, and the
        # runner then takes its historical per-sample slot arithmetic.
        dispatcher=ctx.extras.get("obs_dispatcher"),
        request_extras=dict(ctx.extras),
    )


def _finalize_sample(ctx: SampleContext, state: ObsSampleState) -> SampleOutcome:
    """Post-loop guards, derivation artifact, stitch records and the outputs
    row — exactly the plain policy's post-loop section, emitted into the
    sample's own sink (the real TraceSink sequentially, the sample's
    TraceBuffer under batching)."""

    _, _, run_dir, _, _ = _context_facts(ctx)
    cfg = state.cfg
    sample = state.sample
    if state.runaway:
        raise ObsLoopError(
            f"obs loop exceeded {state.max_iterations} iterations for sample "
            f"{sample.sample_id!r}; refusing a runaway loop"
        )
    # Skip-bound-exceeded (Task 2, 2026-08-09): mirrors the runaway check
    # immediately above -- AcceptAdvance flagged this the instant the bound
    # was crossed (state.py's own comment for why the raise is deferred to
    # here rather than happening inside the component's own invoke()); the
    # SAME message-building function the plain policy calls, so the two
    # executors can never diverge in wording for the same scenario.
    if state.skip_exceeded:
        raise ObsLoopError(
            obs_loop._skip_bound_exceeded_message(sample.sample_id, state.skipped_slices, cfg)
        )
    if not state.request_ids:
        raise ObsLoopError(
            f"sample {sample.sample_id!r} produced no successful requests (entirely "
            "trimmed as non-speech, or every slice skipped after exhausting retries?); "
            "refusing to emit an empty hypothesis silently"
        )

    stitched = " ".join(span for span in state.accepted_spans if span)
    write_json_artifact(
        run_dir / f"{ctx.sink.run_id}.obs-derivation.{sample.sample_id}.json",
        {
            "schema": OBS_DERIVATION_SCHEMA,
            "run_id": ctx.sink.run_id,
            "sample_id": sample.sample_id,
            "parent_media_relpath": sample.media_relpath,
            "parent_sha256": state.parent_sha256,
            "decoded_duration_seconds": state.duration,
            "vad_engine": state.engine_descriptor,
            # Under a plan the advance semantics are still `fixed` (every
            # position was known before the first contact) but the cut came
            # from the plan, and a sealed run must say which (preregistration
            # section 8.4) -- the plain policy's own distinction, verbatim.
            "boundary_mode": (
                OBS_UNIT_PLAN_BOUNDARY_MODE
                if cfg.unit_plan is not None
                else cfg.boundary_mode
            ),
            "boundary_prompt_relpath": cfg.boundary_prompt_relpath,
            "boundary_prompt_sha256": cfg.boundary_prompt_sha256,
            # The plan this run was cut by, named and pinned; null on every
            # fixed-window run, and key for key identical to the plain
            # policy's own ``saea-obs-derivation-v1`` receipt, which is what
            # TestEquivalence in tests/unit/test_obs_loop_ojw.py fingerprints.
            "unit_plan_path": cfg.unit_plan_relpath,
            "unit_plan_sha256": cfg.unit_plan_sha256,
            # OBS-E1b: which rule decided what this run stitched. Null on every
            # clock-cut and every v1/v2 run -- the plain policy's own value,
            # verbatim, for the same fingerprint reason as the keys above.
            "text_ownership": (
                obs_loop.OWNERSHIP_PROTOCOL
                if cfg.unit_plan is not None and cfg.unit_plan.has_context
                else None
            ),
            "condition_tail_chars": cfg.condition_tail_chars,
            "trims": state.trim_events,
            "slices": [record.trace_view() for record in state.slice_records],
        },
    )

    request_descriptor = obs_loop._canonical_bytes(
        {
            "stitched_request_ids": state.request_ids,
            "iteration_request_sha256s": state.iteration_request_sha256s,
        }
    )
    request_sha256 = hashlib.sha256(request_descriptor).hexdigest()
    response_descriptor = obs_loop._canonical_bytes(
        {
            "stitched_text": stitched,
            "stitched_from_response_sha256s": state.iteration_response_sha256s,
        }
    )
    response_sha256 = hashlib.sha256(response_descriptor).hexdigest()
    response_text_sha256 = hashlib.sha256(stitched.encode("utf-8")).hexdigest()
    ctx.sink.emit(
        "MODEL_REQUEST",
        f"{ctx.request_id_base}/request",
        {
            "arm": ctx.arm,
            "payload_sha256": request_sha256,
            "stitch": True,
            "stitched_request_ids": state.request_ids,
        },
    )
    ctx.sink.emit(
        "MODEL_RESPONSE",
        f"{ctx.request_id_base}/response",
        {
            "text": stitched,
            "response_sha256": response_sha256,
            "response_text_sha256": response_text_sha256,
            "stitch": True,
            "stitched_from_response_sha256s": state.iteration_response_sha256s,
        },
    )
    ctx.sink.emit(
        "USE",
        f"{ctx.request_id_base}/use",
        {
            "use_response_sha256": response_sha256,
            "use_admitted": True,
            "use_stitched_iterations": len(state.request_ids),
        },
    )
    return SampleOutcome(
        sample_id=sample.sample_id,
        request_ids=tuple(state.request_ids),
        text=stitched,
        admitted=True,
        request_sha256=request_sha256,
        response_sha256=response_sha256,
        response_text_sha256=response_text_sha256,
        saturated_slices=state.saturated_slices,
        skipped_slices=state.skipped_slices,
    )


class ObsAgentLoopOjwPolicy:
    """One whole-call sample -> the openJiuwen workflow of ``runner.py`` ->
    one stitched hypothesis; ``run_samples`` batches up to
    ``obs_batch_samples`` samples concurrently over the same per-sample
    pipeline (module docstring). Stateless; every run fact arrives through
    ``SampleContext`` exactly as for the plain policy."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        _, data_root, _, repo_root, config_values = _context_facts(ctx)
        runner = _load_runner()
        cfg = ObsLoopConfig.from_values(config_values, repo_root)
        timeout_seconds = workflow_timeout_seconds(config_values)
        state = _prepare_state(
            ctx, cfg, self._window_hook(ctx, cfg, data_root, ctx.sample)
        )
        runner.execute_obs_workflow(
            state,
            adapter_request=ctx.adapter.request,
            workflow_timeout_seconds=timeout_seconds,
        )
        return _finalize_sample(ctx, state)

    def _window_hook(self, ctx, cfg, data_root, sample):
        """This executor's per-window hook, or ``None``.

        ``None`` here, always, for exactly the reason
        ``reproduction.obs_loop.ObsAgentLoopPolicy._window_hook`` gives: this
        policy sends one bare request per window and delivers what came back.
        A second-pass executor overrides THIS and nothing else -- the graph,
        the cut, the retry and skip semantics, the stitch and the outcome are
        shared verbatim (``reproduction.repair_loop.ObsRepairLoopOjwPolicy``).
        The signature is deliberately the plain policy's, so one hook builder
        serves both executors."""

        return None

    def run_samples(self, contexts: Sequence[SampleContext]) -> list[SampleOutcome]:
        """The batch seam ``core.driver.run_experiment`` dispatches to when
        ``obs_batch_samples > 1``. Contract: outcomes aligned to
        ``contexts`` (split-id order, exactly as handed in); on failure the
        FIRST failed sample's error in that order is raised after all tasks
        settle; each sample's trace lands in its own ``ctx.sink`` (the
        driver's per-sample TraceBuffer), routed for the shared adapter via
        ``core.tracing.set_current_trace_buffer`` inside the runner task."""

        contexts = list(contexts)
        if not contexts:
            return []
        for ctx in contexts:
            _context_facts(ctx)  # fail-closed before any work
        _, data_root, _, repo_root, config_values = _context_facts(contexts[0])
        runner = _load_runner()
        cfg = ObsLoopConfig.from_values(config_values, repo_root)
        timeout_seconds = workflow_timeout_seconds(config_values)
        return runner.execute_obs_batch(
            contexts,
            prepare=lambda ctx: _prepare_state(
                ctx, cfg, self._window_hook(ctx, cfg, data_root, ctx.sample)
            ),
            finalize=_finalize_sample,
            batch_size=cfg.batch_samples,
            workflow_timeout_seconds=timeout_seconds,
        )
