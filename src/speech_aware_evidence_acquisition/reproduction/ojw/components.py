"""openJiuwen workflow components for the obs-agent-loop (single-door build).

Four components, each deriving from the framework's ``ComponentExecutable``
line (via ``WorkflowComponent``, the framework's own "standard
implementation combining both execution and graph construction" — owner
ruling 2026-08-08: components DERIVE from ComponentExecutable;
LoopGroup/FuncCondition/Session/Pregel are COMPOSED, never subclassed):

- ``FeedBuffer`` — cuts the current buffer slice from the decoded parent
  PCM (the same ``reproduction.obs_audio`` DSP and ``core.model.slices``
  registry the plain policy uses, called as plain functions — owner ruling:
  the framework tool abstraction is reserved for the phase-2 re-ask arm,
  NOT pipeline-internal DSP, because tools would change the semantics to
  model-decided invocation), registers the derivation record, and computes
  the conditioning tail from the accepted spans held in openJiuwen session
  global state.
- ``FrozenCoreASR`` — THE single door. Renders the iteration instruction
  (task + frozen boundary template + tail frame, byte-identical to the
  plain policy), builds the D2-frozen arm payload via
  ``core.policies.build_arm_payload``, and calls the constructor-injected
  adapter callable (the driver wires ``core.model.FrozenCoreAdapter.
  request``; tests inject fakes). No framework LLM client is ever touched.
- ``BoundaryResolve`` — the three-tier boundary logic, calling the exact
  ``reproduction.obs_audio`` functions (``parse_boundary_response``,
  ``resolve_advance``, ``accept_up_to_boundary``). The sentence-cut rule
  stays OURS: ``pysbd`` (shipped with openjiuwen) segments semantically
  (e.g. it refuses to break after abbreviations like "Dr."), so it cannot
  be pinned byte-equivalent to the frozen ``SENTENCE_FINAL_CHARS`` rfind
  rule — adopting it would change accepted spans (rebuild-notes §pysbd).
- ``AcceptAdvance`` — emits the per-iteration OBS trace record (identical
  field set and order to the plain policy), appends the accepted span to
  session global state (the loop-carried knowledge the next ``FeedBuffer``
  round conditions on) and mirrors the bookkeeping the post-loop stitch
  needs into the driver-side ``ObsSampleState``.

Dataflow: iteration-local values flow node-to-node through the framework's
``${node.field}`` input schemas (session state); loop-carried text state
flows through session GLOBAL state under the ``obs_agent_loop_*`` keys;
static per-sample values (sample identity, task instruction, evidence,
decoding params) are seeded into session state by the outer workflow's
``Start`` component from the driver-built invoke inputs and read back here
via ``session.get_global_state`` — see ``runner.py`` for the graph.

This module imports openjiuwen at module level and is therefore imported
ONLY behind ``policy.py``'s lazy seam (D2 gate: openjiuwen never enters
pyproject.toml; the suite passes with it absent).
"""

from __future__ import annotations

import asyncio
import hashlib
from collections.abc import Awaitable, Callable, Mapping

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent

from ...core.delivery import normalize_terminal_response
from ...core.model import SliceRecord
from ...data.loader import SampleRef
from ..obs_audio import (
    accept_up_to_boundary,
    encode_slice,
    parse_boundary_response,
    resolve_advance,
)
from ..obs_loop import (
    OBS_TAIL_FRAME_V1,
    ObsLoopError,
    _unit_trace_fields,
    request_slice_with_retry,
)
from . import OpenJiuwenExecutorError
from .state import ObsSampleState

# Session global-state keys for the loop-carried text state (single writer:
# AcceptAdvance; single reader: FeedBuffer). Flat underscore names — the
# framework's nested-path split is ".", so dotted keys would be misread as
# paths.
ACCEPTED_SPANS_KEY = "obs_agent_loop_accepted_spans"

# Static per-sample values seeded through the outer Start component
# (runner.build_invoke_inputs); read back via session global state under
# the Start node's output namespace.
START_NODE_ID = "start"
_STATIC_KEYS = (
    "sample",
    "task_instruction",
    "evidence",
    "arm",
    "decoding_params",
    "retrieval_query",
)


def _static(session: Session, key: str, *, required: bool = True) -> object:
    """A driver-seeded static value from session state (Start's outputs),
    resolved leaf-path first (``start.<key>``), then through the node's own
    output mapping. Fail-closed for required values: a missing seed means
    the workflow was invoked without ``runner.build_invoke_inputs`` —
    refuse rather than guess."""

    if key not in _STATIC_KEYS:
        raise ObsLoopError(f"unknown static session key {key!r}")
    value = session.get_global_state(f"{START_NODE_ID}.{key}")
    if value is None:
        values = session.get_global_state(START_NODE_ID)
        if isinstance(values, dict) and key in values:
            value = values[key]
    if value is None and required:
        raise ObsLoopError(
            f"obs-agent-loop-ojw session state lacks the driver-seeded value "
            f"{key!r} under the {START_NODE_ID!r} node; the workflow must be "
            "invoked with runner.build_invoke_inputs(state)"
        )
    return value


class FeedBuffer(WorkflowComponent):
    """Cut, preprocess, write and register the current buffer slice; compute
    the conditioning tail from the session-held accepted spans."""

    def __init__(self, state: ObsSampleState) -> None:
        super().__init__()
        self._state = state

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = self._state
        cfg = state.cfg
        start_frame, end_frame = state.window_frames()
        if end_frame <= start_frame:  # condition guarantees this never runs
            raise ObsLoopError(
                "obs-agent-loop-ojw FeedBuffer scheduled on a degenerate window "
                f"[{start_frame}, {end_frame}); the loop condition must exit first"
            )
        slice_samples = state.pcm[start_frame:end_frame]
        slice_seconds = (end_frame - start_frame) / state.rate
        # Under a unit plan the LAST UNIT is the final window, not the end of
        # the decoded parent (the plan's own last unit may stop short of it).
        # Exactly the plain policy's own two forms, at both of its cut sites.
        is_final = (
            state.iteration == len(state.plan_units) - 1
            if state.plan_units is not None
            else end_frame >= len(state.pcm)
        )
        raw_bytes, transforms, pre_sha256 = encode_slice(
            slice_samples,
            state.rate,
            preprocess=cfg.preprocess,
            rms_target_dbfs=cfg.rms_target_dbfs,
            tail_silence_seconds=cfg.slice_tail_silence_seconds,
        )
        relpath = state.registry.slice_relpath(state.sample.sample_id, state.iteration)
        slice_path = state.data_root / relpath
        slice_path.parent.mkdir(parents=True, exist_ok=True)
        slice_path.write_bytes(raw_bytes)
        record = SliceRecord(
            sample_id=state.sample.sample_id,
            parent_media_relpath=state.sample.media_relpath,
            parent_sha256=state.parent_sha256,
            start_seconds=start_frame / state.rate,
            end_seconds=end_frame / state.rate,
            audio_seconds=slice_seconds,
            sample_rate_hz=state.rate,
            media_relpath=relpath,
            sha256=hashlib.sha256(raw_bytes).hexdigest(),
            bytes=len(raw_bytes),
            iteration=state.iteration,
            preprocess=transforms,
            pre_sha256=pre_sha256,
        )
        state.registry.register(record)
        state.slice_records.append(record)

        spans = session.get_global_state(ACCEPTED_SPANS_KEY) or []
        stitched_so_far = " ".join(span for span in spans if span)
        tail = (
            stitched_so_far[-cfg.condition_tail_chars :]
            if cfg.condition_tail_chars > 0 and stitched_so_far
            else ""
        )
        return {
            "slice_spec": {
                "iteration": state.iteration,
                "relpath": relpath,
                "start_seconds": record.start_seconds,
                "end_seconds": record.end_seconds,
                "slice_seconds": slice_seconds,
                "is_final": is_final,
                "sha256": record.sha256,
                "pre_sha256": pre_sha256,
            },
            "tail": tail,
        }


class FrozenCoreASR(WorkflowComponent):
    """The SINGLE door to the frozen core: renders the iteration
    instruction, builds the D2-frozen arm payload, calls the injected
    adapter. Never a framework LLM/model client."""

    def __init__(self, adapter_request, state: ObsSampleState) -> None:
        super().__init__()
        if not callable(adapter_request):
            raise ObsLoopError(
                "FrozenCoreASR requires a callable adapter request "
                "(core.model.FrozenCoreAdapter.request or a test fake); got "
                f"{type(adapter_request).__name__}"
            )
        self._adapter_request = adapter_request
        self._state = state

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = self._state
        cfg = state.cfg
        slice_spec = inputs["slice_spec"]
        tail = inputs.get("tail") or ""
        sample_view = _static(session, "sample")
        task_instruction = _static(session, "task_instruction")
        evidence = _static(session, "evidence", required=False)
        arm = _static(session, "arm")
        decoding_params = _static(session, "decoding_params")
        retrieval_query = _static(session, "retrieval_query", required=False)

        instruction = task_instruction
        if cfg.boundary_mode == "model":
            instruction = f"{instruction}\n\n{cfg.boundary_prompt_text}"
        if tail:
            instruction = f"{instruction}\n\n{OBS_TAIL_FRAME_V1.format(tail=tail)}"
        # Share exact request construction with offline capacity materialization.
        # The framework still owns its static inputs, tail, and decoding slot.
        from types import SimpleNamespace
        from ..obs_loop import window_request_factory

        record = state.slice_record_for(slice_spec["iteration"])
        request_context = SimpleNamespace(
            arm=arm, task_instruction=instruction, decoding_params=decoding_params,
            request_id_base=sample_view["request_id_base"],
            retrieval_query=retrieval_query, exemplar_bank=None,
            extras=state.request_extras,
        )
        base_request_id, _payload = window_request_factory(
            request_context,
            (slice_spec["iteration"], record, slice_spec["is_final"],
             slice_spec["slice_seconds"], slice_spec.get("pre_sha256"), None),
            sample=state.sample, rate=state.rate, evidence=evidence,
            window_hook=state.window_hook,
        )

        # Per-slice saturation (obs_loop._slice_saturated): read the decode
        # cap from the SAME composed decoding_params every slice payload
        # above actually carries -- identical seam and identical source of
        # truth to the plain policy, never a second reimplementation.
        max_tokens = (
            decoding_params.get("max_tokens")
            if isinstance(decoding_params, dict)
            else None
        )
        # Bounded per-slice retry: the SAME shared helper the plain policy
        # calls (obs_loop.request_slice_with_retry), so the two executors can
        # never diverge in retry, saturation OR exhausted-slice-skip
        # behaviour (live E-001 finding 2026-08-08, continued 2026-08-09
        # twice). The blocking adapter call hops to a worker thread (owner
        # batching directive 2026-08-08): under sample-level concurrency the
        # event loop must stay free while this sample's HTTP request blocks,
        # or N "concurrent" samples would serialize on the loop thread.
        # to_thread copies the task's contextvars, so the adapter's trace
        # emissions still route to THIS sample's buffer (core.tracing.
        # DispatchingSink).
        request_id, response, retry_of, saturated, skipped = await asyncio.to_thread(
            request_slice_with_retry,
            self._adapter_request,
            _payload,
            base_request_id,
            cfg.slice_retry_max,
            max_tokens,
        )
        from ..window_controller import record_controller_terminal

        record_controller_terminal(
            self._state.window_hook, iteration=slice_spec["iteration"],
            request_id=request_id, response=response, saturated=saturated, skipped=skipped,
        )
        # Task 2 (2026-08-09): a skipped slice has no response at all -- the
        # framework's own state-merge convention would DELETE a None-valued
        # key (BoundaryResolve's own comment below), so this returns real,
        # present values (empty text, no hashes) rather than None, and
        # AcceptAdvance reads request_sha256/response_sha256 ONLY on the
        # non-skipped path (never risks that deletion at all).
        # Saturation QUARANTINE (2026-08-11, SAEA-BENCH-cacheorder-q4km
        # read-out): a slice that hit the max_tokens cap is a runaway
        # repetition, not a transcript — admitting its text into the stitch
        # cost one sample +20.6 pp WER the night this landed. The raw
        # response stays fully traced by the adapter's own MODEL_RESPONSE
        # record; only ACCEPTANCE is refused: empty text here makes the
        # boundary tiers fall back exactly like an unparseable response
        # (identical treatment in the plain policy, same commit). The hole
        # is counted and reported (obs_saturated per slice,
        # saturated_slice_count/saturated_sample_ids in the manifest cost
        # block), never scored silently — and deliberately does NOT count
        # toward obs_slice_skip_max: a skip is an UNKNOWN failure
        # (fail-closed caution), a saturation is a detected, bounded
        # degeneracy whose cost is one fallback-advance hole.
        return {
            "text": ""
            if saturated
            else (response.text if response is not None else ""),
            "usage": dict(getattr(response, "usage", None) or {}),
            "request_id": request_id,
            "request_sha256": response.request_sha256 if response is not None else "",
            "response_sha256": response.response_sha256 if response is not None else "",
            "retry_of": retry_of,
            "saturated": saturated,
            "skipped": skipped,
        }


class BoundaryResolve(WorkflowComponent):
    """Three-tier boundary resolution + the frozen deterministic sentence
    cut — exactly ``reproduction.obs_audio`` (module docstring for why the
    cut rule is not delegated to pysbd)."""

    def __init__(self, state: ObsSampleState) -> None:
        super().__init__()
        self._state = state

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = self._state
        cfg = state.cfg
        slice_spec = inputs["slice_spec"]
        # Framework state-merge convention (openjiuwen.core.session.utils.
        # update_dict): a None value DELETES the key, so None-able fields are
        # read back with .get() — missing means None, exactly what was set.
        text = inputs.get("text", "")
        slice_seconds = float(slice_spec["slice_seconds"])
        if cfg.boundary_mode == "model":
            transcript, estimate = parse_boundary_response(text)
        else:
            transcript, estimate = normalize_terminal_response(text), None
        if slice_spec.get("is_final", False):
            accepted, dropped = transcript, ""
            resolution: dict[str, object] = {
                "estimate": estimate,
                "snapped": None,
                "advance": slice_seconds,
                "clamped": False,
                "fallback": False,
            }
        elif cfg.boundary_mode == "fixed":
            accepted, dropped = transcript, ""
            resolution = {
                "estimate": None,
                "snapped": None,
                "advance": slice_seconds,
                "clamped": False,
                "fallback": False,
            }
        else:
            window_start = float(slice_spec["start_seconds"])
            local_transitions = [
                t - window_start
                for t in state.transitions
                if window_start <= t <= window_start + slice_seconds
            ]
            resolution = resolve_advance(
                estimate,
                transitions=local_transitions,
                snap_window=cfg.silence_snap_seconds,
                min_advance=cfg.min_advance_seconds,
                max_advance=cfg.max_advance_seconds,
                fallback_advance=cfg.fallback_advance_seconds,
                buffer_seconds=slice_seconds,
            )
            advance = min(float(resolution["advance"]), slice_seconds)
            resolution["advance"] = advance
            accepted, dropped = accept_up_to_boundary(
                transcript, advance / slice_seconds
            )
        return {"accepted": accepted, "dropped": dropped, "resolution": resolution}


class AcceptAdvance(WorkflowComponent):
    """Emit the per-iteration OBS trace record, commit the accepted span to
    session global state (the tail source for the next round), advance the
    cursor and mirror the stitch bookkeeping into the driver-side state."""

    def __init__(self, state: ObsSampleState) -> None:
        super().__init__()
        self._state = state

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = self._state
        cfg = state.cfg
        slice_spec = inputs["slice_spec"]
        tail = inputs.get("tail") or ""
        resolution = inputs["resolution"]
        # None-able fields read with .get(): the framework's state merge
        # deletes None-valued keys (see BoundaryResolve.invoke), so a missing
        # key here IS the None that was set — the emitted record matches the
        # plain policy's byte for byte.
        accepted = inputs.get("accepted", "")
        dropped = inputs.get("dropped", "")
        request_id = inputs["request_id"]
        # Never None (FrozenCoreASR always returns a real bool), so -- unlike
        # the None-able boundary/retry fields above -- required, not .get().
        saturated = inputs["saturated"]
        # Task 2 (2026-08-09): also never None, same discipline as saturated.
        skipped = inputs["skipped"]
        # The per-window hook's delivery leg (KC-E1f; drift #2 of the
        # 2026-09-08 assessment, closed by the Decision 12-F port). Handed the
        # ACCEPTED span -- what this window would contribute -- it returns what
        # the run actually stitches plus the fields that say why, and it is
        # called for EVERY window, saturated and skipped ones included, exactly
        # as on the plain policy's two cutters. Under the fixed-boundary,
        # zero-tail legality every hook consumer declares, ``accepted`` IS the
        # stripped transcript the slice-parallel pass hands its own hook, so
        # the three sites are one seam and not three.
        hook_fields: dict[str, object] = {}
        if state.window_hook is not None:
            accepted, hook_fields = state.window_hook.accept(
                iteration=slice_spec["iteration"],
                record=state.slice_record_for(slice_spec["iteration"]),
                transcript=accepted,
                saturated=saturated,
                skipped=skipped,
            )
        state.sink.emit(
            "OBS",
            f"{request_id}/obs",
            {
                "obs_iteration": slice_spec["iteration"],
                "obs_window_start_seconds": slice_spec["start_seconds"],
                "obs_window_end_seconds": slice_spec["end_seconds"],
                "obs_final_window": slice_spec.get("is_final", False),
                "obs_slice_relpath": slice_spec["relpath"],
                "obs_slice_sha256": slice_spec["sha256"],
                "obs_pre_sha256": slice_spec.get("pre_sha256"),
                "obs_preprocess": list(cfg.preprocess),
                "obs_vad_engine": state.engine_descriptor,
                "obs_boundary_mode": cfg.boundary_mode,
                "obs_boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                "obs_boundary_estimate_seconds": resolution.get("estimate"),
                "obs_boundary_snapped_seconds": resolution.get("snapped"),
                "obs_boundary_advance_seconds": resolution["advance"],
                "obs_boundary_clamped": resolution["clamped"],
                "obs_boundary_fallback": resolution["fallback"],
                "obs_accepted_chars": len(accepted),
                "obs_dropped_chars": len(dropped),
                "obs_tail_chars_used": len(tail),
                "obs_tail_sha256": (
                    hashlib.sha256(tail.encode("utf-8")).hexdigest() if tail else None
                ),
                # Retry audit trail, identical to the plain policy's record;
                # None-deletion means a missing key IS the None that was set.
                "obs_retry_of": inputs.get("retry_of"),
                # Per-slice decode-cap saturation, identical to the plain
                # policy's record (obs_loop._slice_saturated).
                "obs_saturated": saturated,
                # Exhausted-slice skip, identical to the plain policy's
                # record (module comment above obs_loop.
                # SLICE_RETRYABLE_EXCEPTIONS) -- emitted for the
                # bound-triggering skip too, before state.skip_exceeded ever
                # stops the loop, so the audit trail is complete right up to
                # the refusal.
                "obs_skipped": skipped,
                # Unit-plan fields (OBS-E1 preregistration section 8.3),
                # present only when a plan supplied this cut -- the SAME
                # ``obs_loop._unit_trace_fields`` the plain policy calls, over
                # the unit read from the driver-side state rather than from
                # session state (``ObsSampleState.unit_for``: a unit's speaker
                # is legitimately None, and the framework's state merge
                # DELETES None-valued keys).
                **_unit_trace_fields(state.unit_for(slice_spec["iteration"])),
                # The hook's own fields, merged last and in the same position
                # as on the plain policy's two cutters, so what was delivered
                # and why sits in the sealed trace beside what was said. Empty
                # without a hook -- which is every run this executor has flown.
                **hook_fields,
            },
        )
        span = accepted.strip()
        spans = list(session.get_global_state(ACCEPTED_SPANS_KEY) or [])
        spans.append(span)
        session.update_global_state({ACCEPTED_SPANS_KEY: spans})
        state.accepted_spans.append(span)
        if saturated:
            state.saturated_slices += 1
        # A skipped slice has no real response: nothing to hash into the
        # stitch (module comment above obs_loop.SLICE_RETRYABLE_EXCEPTIONS)
        # -- request_ids/the per-iteration sha lists stay in lockstep with
        # the plain policy, covering only iterations that actually
        # contributed content. skip_exceeded is set here, the instant the
        # bound is crossed, but never raised here (state.py's own comment:
        # a component's invoke() failure is wrapped by the framework into
        # its own error type) -- should_continue sees the flag next and
        # stops the loop, and policy._finalize_sample raises the real,
        # identically-worded ObsLoopError once the workflow returns.
        if skipped:
            state.skipped_slices += 1
            if state.skipped_slices > cfg.slice_skip_max:
                state.skip_exceeded = True
        else:
            state.request_ids.append(request_id)
            state.iteration_request_sha256s.append(inputs["request_sha256"])
            state.iteration_response_sha256s.append(inputs["response_sha256"])
        state.cursor = float(slice_spec["start_seconds"]) + float(resolution["advance"])
        state.iteration += 1
        return {"accepted_spans_count": len(spans)}


class PrepareAgentWave(WorkflowComponent):
    """Expose one controller-authored contact wave to the workflow graph."""

    def __init__(
        self,
        prepare_wave: Callable[[Session], int],
        branch_count: int,
    ) -> None:
        super().__init__()
        self._prepare_wave = prepare_wave
        self._branch_count = branch_count

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        active_count = self._prepare_wave(session)
        if (
            isinstance(active_count, bool)
            or not isinstance(active_count, int)
            or not 1 <= active_count <= self._branch_count
        ):
            raise OpenJiuwenExecutorError(
                "openJiuwen Agent wave must activate between one and "
                f"{self._branch_count} contacts"
            )
        return {"active_count": active_count}


class ExecuteAgentContact(WorkflowComponent):
    """Run one active contact branch through the injected frozen-core door."""

    def __init__(
        self,
        branch_index: int,
        invoke_contact: Callable[[int], Awaitable[Mapping[str, object]]],
    ) -> None:
        super().__init__()
        self._branch_index = branch_index
        self._invoke_contact = invoke_contact

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        active_count = inputs["active_count"]
        if self._branch_index >= active_count:
            return {
                "active": False,
                "response_text": "",
                "slot_id": -1,
                "response_sha256": "",
            }
        result = await self._invoke_contact(self._branch_index)
        required = {
            "response_text",
            "slot_id",
            "response_sha256",
        }
        if not isinstance(result, Mapping) or set(result) != required:
            raise OpenJiuwenExecutorError(
                "openJiuwen Agent contact callback returned a malformed result"
            )
        return {"active": True, **dict(result)}


class AggregateAgentWave(WorkflowComponent):
    """Join an ordered contact wave and advance the controller exactly once."""

    def __init__(
        self,
        branch_count: int,
        aggregate_wave: Callable[[tuple[Mapping[str, object], ...], Session], None],
    ) -> None:
        super().__init__()
        self._branch_count = branch_count
        self._aggregate_wave = aggregate_wave

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        active_count = inputs["active_count"]
        ordered = tuple(
            inputs[f"branch_{index}"] for index in range(self._branch_count)
        )
        active = tuple(branch for branch in ordered if branch["active"])
        if len(active) != active_count:
            raise OpenJiuwenExecutorError(
                "openJiuwen Agent fan-in did not receive every active contact"
            )
        self._aggregate_wave(active, session)
        return {"active_count": active_count}
