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

import hashlib

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import WorkflowComponent

from ...core.model import SliceRecord
from ...data.loader import SampleRef
from ..obs_audio import (
    accept_up_to_boundary,
    parse_boundary_response,
    resolve_advance,
    rms_normalize,
    write_wav_bytes,
)
from ..obs_loop import OBS_TAIL_FRAME_V1, ObsLoopError, request_slice_with_retry
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

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
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
        is_final = end_frame >= len(state.pcm)
        raw_bytes = write_wav_bytes(slice_samples, state.rate)
        pre_sha256: str | None = None
        if "rms-norm" in cfg.preprocess:
            pre_sha256 = hashlib.sha256(raw_bytes).hexdigest()
            slice_samples = rms_normalize(slice_samples, cfg.rms_target_dbfs)
            raw_bytes = write_wav_bytes(slice_samples, state.rate)
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
            preprocess=cfg.preprocess,
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

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
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

        slice_ref = SampleRef(
            carrier_lock_key=sample_view["carrier_lock_key"],
            sample_id=sample_view["sample_id"],
            media_relpath=slice_spec["relpath"],
            audio_seconds=slice_spec["slice_seconds"],
            sample_rate_hz=state.rate,
        )
        base_request_id = f"{sample_view['request_id_base']}-i{slice_spec['iteration']:04d}"
        # Deferred import (same reason as the plain policy): core.policies
        # registers the ojw policy, so importing build_arm_payload at module
        # level here would be circular; by run time both are always loaded.
        from ...core.policies import build_arm_payload  # noqa: PLC0415

        def _payload(rid):
            return build_arm_payload(
                arm,
                slice_ref,
                rid,
                instruction,
                decoding_params,
                evidence=evidence,
                retrieval_query=retrieval_query,
            )

        # Bounded per-slice retry: the SAME shared helper the plain policy
        # calls (obs_loop.request_slice_with_retry), so the two executors can
        # never diverge in retry behaviour (live E-001 finding 2026-08-08).
        request_id, response, retry_of = request_slice_with_retry(
            self._adapter_request, _payload, base_request_id, cfg.slice_retry_max
        )
        return {
            "text": response.text,
            "usage": dict(getattr(response, "usage", None) or {}),
            "request_id": request_id,
            "request_sha256": response.request_sha256,
            "response_sha256": response.response_sha256,
            "retry_of": retry_of,
        }


class BoundaryResolve(WorkflowComponent):
    """Three-tier boundary resolution + the frozen deterministic sentence
    cut — exactly ``reproduction.obs_audio`` (module docstring for why the
    cut rule is not delegated to pysbd)."""

    def __init__(self, state: ObsSampleState) -> None:
        super().__init__()
        self._state = state

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
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
            transcript, estimate = text.strip(), None
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
            accepted, dropped = accept_up_to_boundary(transcript, advance / slice_seconds)
        return {"accepted": accepted, "dropped": dropped, "resolution": resolution}


class AcceptAdvance(WorkflowComponent):
    """Emit the per-iteration OBS trace record, commit the accepted span to
    session global state (the tail source for the next round), advance the
    cursor and mirror the stitch bookkeeping into the driver-side state."""

    def __init__(self, state: ObsSampleState) -> None:
        super().__init__()
        self._state = state

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
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
            },
        )
        span = accepted.strip()
        spans = list(session.get_global_state(ACCEPTED_SPANS_KEY) or [])
        spans.append(span)
        session.update_global_state({ACCEPTED_SPANS_KEY: spans})
        state.accepted_spans.append(span)
        state.request_ids.append(request_id)
        state.iteration_request_sha256s.append(inputs["request_sha256"])
        state.iteration_response_sha256s.append(inputs["response_sha256"])
        state.cursor = float(slice_spec["start_seconds"]) + float(resolution["advance"])
        state.iteration += 1
        return {"accepted_spans_count": len(spans)}
