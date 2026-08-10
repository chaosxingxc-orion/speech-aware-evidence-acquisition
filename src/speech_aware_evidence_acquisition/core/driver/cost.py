"""``run_experiment``'s post-loop cost assembly (R0 repair T7, invariant I8).

Split out of ``run.py`` (R0 repair refactor stage 2, part C, pure move, no
behaviour change) purely for file size: durably records this run's measured
GPU-seconds, best-effort folds in sibling ABORTED attempts' cost on the same
run_id, and assembles the final cost dict every ``RunResult`` carries.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Mapping

from ...contracts import ExecutionPlan
from ..attempts import STATE_ABORTED, AttemptError, AttemptStore
from ..resources import NOT_AVAILABLE


def _assemble_run_cost(
    *,
    root: Path,
    plan: ExecutionPlan,
    adapter: object,
    resource_summary: Mapping[str, object],
    cpu_seconds: float,
    gate_setup_seconds: float,
    supplied_evidence_bytes: int,
    admitted_evidence_bytes: int,
    saturated_slice_count: int,
    saturated_sample_ids: list[str],
    skipped_slice_count: int,
    skipped_sample_ids: list[str],
) -> dict[str, object]:
    # Minor (fix-wave2, external-threat-model review round 2): gpu hours was
    # the only budget dimension with no derived counterpart, even though
    # gpu_seconds IS measured here, per run. Feed the measured total back
    # into THIS attempt's own durable record (AttemptStore.record_gpu_seconds)
    # so it is available to any reader of this run's actual usage --
    # AttemptStore.all_actual_usage() is no longer read by a slice-wide
    # budget-cap check (that check was retired by the 2026-08-06 owner
    # amendment, SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS), but durable,
    # accurate per-run cost accounting stays useful regardless.
    # Best-effort and never allowed to turn a genuinely successful run into a
    # false failure: `resource_summary["gpu_seconds"]` legitimately reads the
    # NOT_AVAILABLE sentinel string (no sampler, or a broken nvidia-smi -- see
    # core.resources) far more often than a real run ever measures it, and a
    # durable-file write failure here is exactly the kind of sibling-
    # bookkeeping failure the failed_attempt_* read just below already
    # tolerates the same way -- this run's own request loop, outputs and
    # trace are already durable on disk by this point regardless.
    measured_gpu_seconds = resource_summary.get("gpu_seconds")
    if (
        isinstance(measured_gpu_seconds, (int, float))
        and not isinstance(measured_gpu_seconds, bool)
        and math.isfinite(measured_gpu_seconds)
        and measured_gpu_seconds >= 0
    ):
        try:
            AttemptStore(Path(root) / "attempts").handle(
                plan.run_id, plan.attempt_id
            ).record_gpu_seconds(measured_gpu_seconds)
        except (AttemptError, OSError, ValueError):
            pass
    # R0 repair T7 (I8): failed-attempt cost. Sibling attempts under this SAME
    # run_id that are (as of manifest time) ABORTED -- e.g. a crashed attempt
    # this run_id's caller retried under a fresh attempt_id -- spent real
    # calls/audio this run's OWN plan budget already counts (core.attempts.
    # AttemptStore.prior_actual_usage folds every state in), but a reader of
    # this successful attempt's OWN cost block previously had no way to see
    # that extra, wasted spend. `exclude_attempt_id` keeps this run's own
    # attempt (never itself ABORTED on this success path) out of the sum.
    #
    # T7 fix (reviewer-flagged IMPORTANT): this read happens AFTER the run has
    # already fully succeeded -- every model call made, outputs/trace already
    # durable on disk. It must therefore be best-effort, mirroring
    # core.bundle._best_effort_cost_for_aborted_attempt's identical read:
    # a corrupted or unreadable SIBLING attempt file (someone else's crash,
    # not this run's) must never raise here and turn a genuinely successful,
    # budget-spent run into a false ABORTED manifest via
    # run_experiment_bundled's `except Exception`. On failure this specific
    # pair degrades to NOT_AVAILABLE + a reason -- every OTHER cost field
    # (this run's own calls/audio/latency/tokens/gpu/cpu/evidence/tool_calls)
    # stays fully measured and the run still completes.
    try:
        failed_attempt_calls, failed_attempt_audio_seconds = AttemptStore(
            Path(root) / "attempts"
        ).actual_usage_in_states(
            plan.run_id, frozenset({STATE_ABORTED}), exclude_attempt_id=plan.attempt_id
        )
        failed_attempt_cost_reason = None
    except (AttemptError, OSError, ValueError) as error:
        failed_attempt_calls = NOT_AVAILABLE
        failed_attempt_audio_seconds = NOT_AVAILABLE
        failed_attempt_cost_reason = (
            "could not read sibling ABORTED attempts' usage for run_id "
            f"{plan.run_id!r} from the durable attempts store: {error}; this "
            "run itself succeeded and every other cost field is unaffected"
        )
    cost = dict(adapter.cost_summary())
    cost.update(
        {
            "cpu_seconds": cpu_seconds,
            "gate_setup_seconds": gate_setup_seconds,
            "supplied_evidence_bytes": supplied_evidence_bytes,
            "admitted_evidence_bytes": admitted_evidence_bytes,
            "failed_attempt_calls": failed_attempt_calls,
            "failed_attempt_audio_seconds": failed_attempt_audio_seconds,
            "failed_attempt_cost_reason": failed_attempt_cost_reason,
            # Per-slice decode-cap saturation aggregate (2026-08-09, continues
            # the obs-loop E-001 retry finding): a straight sum/collection of
            # what every SampleOutcome.saturated_slices already reported
            # during the request loop above -- genuinely measured whenever a
            # RunResult exists at all (I8), never best-effort, so this is a
            # real 0/[] for a run with no saturated slices, not a stand-in for
            # missing data.
            "saturated_slice_count": saturated_slice_count,
            "saturated_sample_ids": saturated_sample_ids,
            # Exhausted-slice skip aggregate (Task 2, 2026-08-09, continues
            # the obs-loop E-001 retry finding): a straight sum/collection of
            # what every SampleOutcome.skipped_slices already reported during
            # the request loop above -- the SAME "genuinely measured whenever
            # a RunResult exists, never best-effort" discipline as the
            # saturation pair immediately above. This is deliberately what
            # makes a skipped-slice run impossible to mistake for a clean one
            # (module comment above SLICE_RETRYABLE_EXCEPTIONS): the count
            # belongs in the manifest, not only in a trace.
            "skipped_slice_count": skipped_slice_count,
            "skipped_sample_ids": skipped_sample_ids,
            # Every field above this line is genuinely measured whenever this
            # function returns a RunResult at all (I8: nothing here is a
            # silent omission) -- unlike gpu_seconds/peak_vram_mib, which
            # `resource_summary` may legitimately report as NOT_AVAILABLE
            # (with `gpu_sampling_reason`) when no sampler -- or no working
            # nvidia-smi -- was available, and unlike failed_attempt_calls/
            # failed_attempt_audio_seconds just above, which may legitimately
            # report NOT_AVAILABLE (with failed_attempt_cost_reason) when a
            # SIBLING attempt file could not be read.
            "cost_unavailable_reason": None,
        }
    )
    cost.update(resource_summary)
    return cost
