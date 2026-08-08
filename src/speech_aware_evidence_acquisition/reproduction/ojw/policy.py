"""The ``obs-agent-loop-ojw`` policy: the obs loop on the openJiuwen executor.

Same contract as the plain ``obs-agent-loop`` policy (``reproduction.
obs_loop`` — one whole-call sample -> N buffer-slice requests -> one
stitched hypothesis; same trace kinds/fields, same slice rail, same
outputs-row shape), with the per-sample loop orchestrated by the
openJiuwen framework (``runner.py`` graph) instead of a plain ``while``.
Equivalence between the two executors is a hard red line
(``docs/readiness/2026-08-08-openjiuwen-adoption.md`` §3) and is asserted
by ``tests/unit/test_obs_loop_ojw.py`` over shared synthetic fixtures.

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
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from ...core.base import SampleContext, SampleOutcome
from ...core.model import SliceRegistry
from ...data.loader import SampleRef
from ...e0.artifacts import write_json_artifact
from .. import obs_loop
from ..obs_audio import nonspeech_spans, vad_transitions
from ..obs_loop import (
    OBS_DERIVATION_SCHEMA,
    SLICE_SAMPLE_RATE_HZ,
    ObsLoopConfig,
    ObsLoopError,
)
from . import OJW_INSTALL_HINT, OJW_POLICY_NAME
from .state import ObsSampleState

__all__ = ["OJW_POLICY_NAME", "ObsAgentLoopOjwPolicy"]


def _load_runner():
    """The ONE lazy seam through which openjiuwen enters (module docstring):
    fail-closed with the install hint when the framework is absent."""

    try:
        from . import runner  # noqa: PLC0415 (lazy: openjiuwen-dependent)
    except ImportError as error:
        raise ObsLoopError(OJW_INSTALL_HINT) from error
    return runner


class ObsAgentLoopOjwPolicy:
    """One whole-call sample -> the openJiuwen workflow of ``runner.py`` ->
    one stitched hypothesis. Stateless; every run fact arrives through
    ``SampleContext`` exactly as for the plain policy."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
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
        runner = _load_runner()
        cfg = ObsLoopConfig.from_values(config_values, repo_root)
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

        state = ObsSampleState(
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
        )
        runner.execute_obs_workflow(state, adapter_request=ctx.adapter.request)

        if state.runaway:
            raise ObsLoopError(
                f"obs loop exceeded {max_iterations} iterations for sample "
                f"{sample.sample_id!r}; refusing a runaway loop"
            )
        if not state.request_ids:
            raise ObsLoopError(
                f"sample {sample.sample_id!r} produced no requests (entirely trimmed "
                "as non-speech?); refusing to emit an empty hypothesis silently"
            )

        stitched = " ".join(span for span in state.accepted_spans if span)
        write_json_artifact(
            run_dir / f"{ctx.sink.run_id}.obs-derivation.{sample.sample_id}.json",
            {
                "schema": OBS_DERIVATION_SCHEMA,
                "run_id": ctx.sink.run_id,
                "sample_id": sample.sample_id,
                "parent_media_relpath": sample.media_relpath,
                "parent_sha256": parent_sha256,
                "decoded_duration_seconds": duration,
                "vad_engine": engine_descriptor,
                "boundary_mode": cfg.boundary_mode,
                "boundary_prompt_relpath": cfg.boundary_prompt_relpath,
                "boundary_prompt_sha256": cfg.boundary_prompt_sha256,
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
        )
