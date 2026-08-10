"""Best-effort cost block for an ABORTED manifest.

Split out of ``core/bundle/manifest.py`` (R0 repair refactor stage 2, part C,
pure move, no behaviour change) purely for file size.
"""

from __future__ import annotations

from pathlib import Path

from ..attempts import AttemptError, AttemptStore, STATE_ABORTED
from ..resources import NOT_AVAILABLE

# ---------------------------------------------------------------------------
# R0 repair T7 (I8): an ABORTED manifest's best-effort cost block. Unlike the
# COMPLETED path (whose cost block is exactly `core.driver.run_experiment`'s
# already-fully-measured `RunResult.cost`), a run that failed never returns a
# RunResult at all -- its in-memory FrozenCoreAdapter/resource-sampler state
# is gone once the exception has propagated out of run_experiment. Everything
# genuinely computable here comes straight from the durable attempts store
# (never from memory that no longer exists), which is exactly why this task's
# "failed-attempt cost must not be silently omitted" requirement is met even
# for the run that never succeeded: `calls_used`/`audio_seconds_used` is THIS
# attempt's own durably recorded spend before it failed; `failed_attempt_*`
# folds in sibling attempts under the same run_id that are ALSO ABORTED.
# Every other field -- latency/tokens/tool_calls/cpu/gpu/evidence/setup --
# genuinely cannot be recovered post-hoc, so each is recorded as the literal
# NOT_AVAILABLE with a shared reason, per this task's deviation discipline:
# never a silent omission.
# ---------------------------------------------------------------------------

_ABORTED_COST_UNAVAILABLE_REASON = (
    "this attempt ended ABORTED before core.driver.run_experiment finished "
    "computing its own cost aggregate (a RunResult, and the in-memory "
    "adapter/resource-sampler state behind it, is only ever produced on "
    "success); only durable attempt-store usage -- calls_used/"
    "audio_seconds_used for this attempt, and failed_attempt_calls/"
    "failed_attempt_audio_seconds for prior sibling ABORTED attempts on the "
    "same run_id -- is recoverable post-hoc"
)


def _best_effort_cost_for_aborted_attempt(
    data_root: Path, run_id: str, attempt_id: str
) -> dict[str, object]:
    """Never raises: a read failure here must not break ``build_manifest``'s
    "always write a manifest" guarantee (T6) for the ABORTED path it exists
    to serve."""

    own_calls = 0
    own_audio_seconds = 0.0
    failed_calls = 0
    failed_audio_seconds = 0.0
    try:
        store = AttemptStore(Path(data_root) / "attempts")
        handle = store.handle(run_id, attempt_id)
        if handle.path.is_file():
            own_calls, own_audio_seconds = handle.actual_totals()
        failed_calls, failed_audio_seconds = store.actual_usage_in_states(
            run_id, frozenset({STATE_ABORTED}), exclude_attempt_id=attempt_id
        )
    except (AttemptError, OSError, ValueError):
        pass
    return {
        "calls_used": own_calls,
        "audio_seconds_used": own_audio_seconds,
        "latency_seconds_total": NOT_AVAILABLE,
        "prompt_tokens_total": NOT_AVAILABLE,
        "completion_tokens_total": NOT_AVAILABLE,
        "tool_calls": NOT_AVAILABLE,
        "cpu_seconds": NOT_AVAILABLE,
        "gate_setup_seconds": NOT_AVAILABLE,
        "supplied_evidence_bytes": NOT_AVAILABLE,
        "admitted_evidence_bytes": NOT_AVAILABLE,
        "gpu_seconds": NOT_AVAILABLE,
        "peak_vram_mib": NOT_AVAILABLE,
        "gpu_sampling_reason": _ABORTED_COST_UNAVAILABLE_REASON,
        "cost_unavailable_reason": _ABORTED_COST_UNAVAILABLE_REASON,
        "failed_attempt_calls": failed_calls,
        "failed_attempt_audio_seconds": failed_audio_seconds,
        # Key-shape parity with the COMPLETED cost dict (core.driver.cost.
        # _assemble_run_cost, 2026-08-09): saturated-slice bookkeeping lives
        # entirely in the per-sample request loop's in-memory SampleOutcome
        # values, never durably recorded anywhere an ABORTED attempt's
        # post-hoc read could recover it -- genuinely NOT_AVAILABLE here, same
        # reason as latency_seconds_total/prompt_tokens_total above.
        "saturated_slice_count": NOT_AVAILABLE,
        "saturated_sample_ids": NOT_AVAILABLE,
        # Key-shape parity, same reasoning, for the skipped-slice bookkeeping
        # (Task 2, 2026-08-09): also lives entirely in-memory in the request
        # loop, genuinely NOT_AVAILABLE for an attempt that never got there.
        "skipped_slice_count": NOT_AVAILABLE,
        "skipped_sample_ids": NOT_AVAILABLE,
        # M-3: key-shape parity with the COMPLETED cost dict (which carries
        # this whenever a FrozenCoreAdapter was genuinely constructed). An
        # attempt that ended ABORTED before that ever happened (or before the
        # gate returned a hash) has no lock hash to report -- None here, not a
        # missing key, so both cost-dict shapes carry the same field set.
        "umbrella_lock_sha256": None,
        # T7 fix: key-shape parity with core.driver.run_experiment's cost
        # dict (which can report failed_attempt_calls/audio_seconds as
        # NOT_AVAILABLE with this reason when a sibling attempt file is
        # unreadable). This function's own try/except above already
        # collapses ANY read failure (own attempt OR siblings) to 0/0.0
        # rather than distinguishing -- unchanged here -- so this stays None;
        # the key exists so both cost-dict shapes carry the same field set.
        "failed_attempt_cost_reason": None,
    }
