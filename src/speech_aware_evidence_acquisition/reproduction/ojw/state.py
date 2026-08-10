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
2. trim consumption — the plain loop handles one long-non-speech span per
   ``while`` round via ``continue``; consecutive rounds without a model
   call collapse here into one condition evaluation that consumes every
   applicable span in sequence, emitting byte-identical OBS trim records
   (same ``-trim{n:04d}`` ids, same fields, same order — a trim round
   never touched anything but the cursor and the trace);
3. exhaustion — ``cursor < duration - epsilon``, the plain ``while`` head;
4. the degenerate zero-length window — the plain loop ``break``s when the
   rounded frame window collapses (``end_frame <= start_frame``); the same
   arithmetic decides here before a body round is ever scheduled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from ...core.model import SliceRecord, SliceRegistry
from ...data.loader import SampleRef
from ..obs_loop import ObsAgentLoopPolicy, ObsLoopConfig

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

    def should_continue(self) -> bool:
        """The framework loop's ``FuncCondition`` callable (module docstring
        for the exact plain-policy fragments each step reproduces)."""

        if self.iteration > self.max_iterations:
            self.runaway = True
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
        start_frame = int(round(self.cursor * self.rate))
        end_frame = min(
            int(round((self.cursor + self.cfg.buffer_seconds) * self.rate)), len(self.pcm)
        )
        return end_frame > start_frame

    def window_frames(self) -> tuple[int, int]:
        """The current buffer window's frame bounds — the SAME arithmetic as
        ``should_continue``'s degenerate-window check and the plain policy's
        slice cut, computed in one place so they can never diverge."""

        start_frame = int(round(self.cursor * self.rate))
        end_frame = min(
            int(round((self.cursor + self.cfg.buffer_seconds) * self.rate)), len(self.pcm)
        )
        return start_frame, end_frame
