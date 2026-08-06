"""Run-manifest construction: study commit, repo confinement, ``build_manifest``.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ...contracts import STUDY_SLUG, ExecutionPlan
from ...e0.artifacts import sha256_file, write_json_artifact
from ..attempts import AttemptError, AttemptStore, STATE_ABORTED
from ..base import RunResult
from ..config import ComposedConfig
from ..resources import NOT_AVAILABLE
from ..split_receipt import VerifiedSplit
from . import (
    RUN_MANIFEST_SCHEMA,
    STATUS_ABORTED,
    STATUS_COMPLETED,
    UNAVAILABLE_COMMIT_PREFIX,
    _VALID_STATUSES,
    BundleError,
    _confine_child_path,
    _refuse_if_inside_repo,
)

# ---------------------------------------------------------------------------
# Study commit (build time only -- never re-verified at verify_bundle time,
# since the study repo legitimately moves commits after a run was recorded).
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout.strip(), completed.stderr.strip()


def _study_commit(repo_root: Path) -> str:
    """Read the study repo's commit, fail-closed.

    Design choice (task-6 brief asks this be stated explicitly): a run
    manifest binds the EXACT commit the run executed against. If the tree is
    dirty, "the commit" is a lie -- uncommitted changes could be anything --
    so we refuse rather than record a commit that does not describe what
    actually ran. If ``git`` itself is unavailable or the directory is not a
    repository, we likewise refuse rather than silently omit study_commit
    (an optional/None field here would make every later manifest field's
    trustworthiness ambiguous: "was there no repo, or did we just not check?").
    This mirrors ``e0.runtime_receipt.build_runtime_receipt``'s existing
    dirty-tree refusal for the llama.cpp build tree -- same discipline,
    applied to the study tree itself.
    """

    code, dirty, stderr = _git(repo_root, "status", "--porcelain")
    if code != 0:
        raise BundleError(f"cannot read git status for {repo_root}: {stderr}")
    if dirty:
        raise BundleError(
            f"study repo {repo_root} has uncommitted changes; a run manifest must bind "
            f"the exact commit that produced the run, never a dirty tree:\n{dirty}"
        )
    code, commit, stderr = _git(repo_root, "rev-parse", "HEAD")
    if code != 0 or not commit:
        raise BundleError(f"cannot read the study repo's HEAD commit at {repo_root}: {stderr}")
    return commit


def require_clean_study_repo(repo_root: Path) -> str:
    """Public wrapper over :func:`_study_commit` (CRITICAL fix, T6 fix round):
    ``core.driver.run_experiment_bundled`` calls this BEFORE ``run_experiment``
    ever spends attempt budget, not only once a manifest is finally built at
    the end. Without this, a dirty/unreadable study repo let a run execute to
    completion (outputs written, calls/audio-seconds durably spent) and only
    THEN discover it could never produce a manifest -- leaving a
    budget-consuming run with no manifest and its attempt stuck OPENED
    forever, since the raising `build_manifest` call sat outside the
    try/except that would otherwise have aborted it. Returns the commit for
    convenience (unused by the caller today); raises :class:`BundleError`
    exactly as ``_study_commit`` does."""

    return _study_commit(Path(repo_root))


def _resolve_study_commit(repo_root: Path, status: str) -> str:
    """Read the study commit for a manifest being built, with a status-aware
    tolerance (IMPORTANT fix, T6 fix-2 round -- closes the sibling gap
    CRITICAL 2's fix left open).

    A COMPLETED manifest keeps the ORIGINAL, strict behavior unchanged: if
    ``_study_commit`` fails, ``build_manifest`` fails, full stop -- a
    COMPLETED record must always bind a real, clean commit.

    An ABORTED manifest is different in kind: it exists precisely BECAUSE
    something already went wrong, and the reviewed defect was exactly this --
    ``run_experiment_bundled``'s own dirty-tree check runs once, BEFORE
    ``run_experiment`` starts, but a real model-facing run can take long
    enough for the tree to become dirty DURING it (a genuine TOCTOU window,
    not a hypothetical one); a run that then fails for an UNRELATED reason
    must still leave a durable ABORTED record, not silently lose one to a
    second, unrelated ``BundleError`` about the tree. So an ABORTED manifest
    tries the strict read first (if the tree genuinely is still clean, the
    real commit is strictly more useful than a placeholder and is recorded),
    and only on failure substitutes
    ``f"{UNAVAILABLE_COMMIT_PREFIX}{reason}"``. An honest "commit unavailable,
    here is why" marker on a record that already says ABORTED is strictly
    better than no record at all for that attempt -- but it must never be
    mistakable for a COMPLETED one, which is why the COMPLETED path above
    never takes this fallback, and :func:`verify_bundle` separately refuses
    any manifest that claims ``status == COMPLETED`` while carrying this
    marker (defense in depth against a hand-tampered manifest, not just a
    structural guarantee about what ``build_manifest`` itself would ever
    produce).
    """

    if status == STATUS_COMPLETED:
        return _study_commit(Path(repo_root))
    try:
        return _study_commit(Path(repo_root))
    except BundleError as error:
        return f"{UNAVAILABLE_COMMIT_PREFIX}{error}"


def _artifact_meta(path: Path) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "sha256": sha256_file(path)}


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


def _manifest_document(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None,
    result: RunResult | None,
    now: Callable[[], datetime],
) -> dict[str, object]:
    if status not in _VALID_STATUSES:
        raise BundleError(f"manifest status must be one of {_VALID_STATUSES}, got {status!r}")
    if status == STATUS_COMPLETED:
        if failure_reason is not None:
            raise BundleError("a COMPLETED manifest must not carry a failure_reason")
        if result is None:
            raise BundleError("a COMPLETED manifest requires the run's RunResult")
    if status == STATUS_ABORTED and not (isinstance(failure_reason, str) and failure_reason.strip()):
        raise BundleError("an ABORTED manifest requires a non-empty failure_reason")

    attempt_id = plan.attempt_id
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise BundleError(
            "a run manifest requires a plan with a non-empty attempt_id (R0 repair T4/T6)"
        )
    run_id = plan.run_id
    run_dir = Path(run_dir).resolve()

    outputs_meta = None
    raw_trace_meta = None
    trace_manifest_meta = None
    cost = None
    if result is not None:
        outputs_path = Path(result.outputs_path).resolve()
        if not outputs_path.is_file():
            raise BundleError(f"RunResult.outputs_path does not exist: {outputs_path}")
        outputs_meta = _artifact_meta(outputs_path)
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        trace_manifest_path = run_dir / f"{run_id}.trace-manifest.json"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)
        if trace_manifest_path.is_file():
            trace_manifest_meta = _artifact_meta(trace_manifest_path)
        cost = dict(result.cost)
    else:
        # Best-effort: an aborted attempt may still have left a partial trace
        # (never outputs -- run_experiment only writes outputs after every
        # sample succeeds) on disk; bind whatever genuinely exists so the
        # aborted bundle is still auditable, never pretend it is complete.
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)
        # R0 repair T7 (I8): an ABORTED manifest must not carry cost=None --
        # that would silently omit any failed-attempt cost this attempt (or a
        # prior sibling attempt on the same run_id) genuinely incurred.
        cost = _best_effort_cost_for_aborted_attempt(data_root, run_id, attempt_id)

    session_meta = None
    if session_receipt_path is not None:
        session_path = Path(session_receipt_path).resolve()
        if session_path.is_file():
            session_meta = _artifact_meta(session_path)

    attempts_root = Path(data_root) / "attempts"
    attempt_state_path = attempts_root / run_id / f"{attempt_id}.json"

    return {
        "schema": RUN_MANIFEST_SCHEMA,
        "study": STUDY_SLUG,
        "run_id": run_id,
        "created_at": now().astimezone(timezone.utc).isoformat(),
        "status": status,
        "failure_reason": failure_reason,
        "study_commit": _resolve_study_commit(Path(repo_root), status),
        # I-1 fix: the arm this attempt actually ran under -- needed so
        # verify_bundle can independently recompute protocol_hash from
        # (config_hash, arm, split_identity_hash) via the exact same
        # core.config.protocol_hash convention core.driver.run_experiment
        # itself checks at run time, rather than merely trusting the
        # manifest's own protocol_hash field.
        "arm": str(composed.values.get("arm", "")),
        "config": {"fragments": dict(composed.fragments), "config_hash": composed.config_hash},
        "protocol_hash": plan.protocol_hash,
        "plan": {
            "schema": plan.schema,
            "study": plan.study,
            "run_id": plan.run_id,
            "execution_profile": plan.execution_profile,
            "carrier_lock_key": plan.carrier_lock_key,
            "split_role": plan.split_role,
            "split_identity_hash": plan.split_identity_hash,
            "planned_model_calls": plan.planned_model_calls,
            "planned_gpu_hours": plan.planned_gpu_hours,
            "planned_speech_audio_seconds": plan.planned_speech_audio_seconds,
            "protocol_hash": plan.protocol_hash,
            "attempt_id": plan.attempt_id,
        },
        "exposure_run_id": plan.run_id,
        "split": {
            "name": str(composed.values.get("split_name", "")),
            "role": verified_split.split_role,
            "carrier_lock_key": verified_split.carrier_lock_key,
            "identity_hash": verified_split.identity_hash,
            # I-1 fix: verify_bundle now cross-checks this against len(ids) --
            # a manifest whose ids were edited without updating this count
            # (or vice versa) refuses rather than being silently accepted.
            "count": len(verified_split.ids),
            "ids": sorted(verified_split.ids),
        },
        "session_receipt": session_meta,
        "outputs": outputs_meta,
        "raw_trace": raw_trace_meta,
        "trace_manifest": trace_manifest_meta,
        "scores": None,
        "scorers": list(composed.values.get("scorers", [])),
        "cost": cost,
        "attempt": {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "state_path": str(attempt_state_path),
        },
    }


def build_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None = None,
    result: RunResult | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> Path:
    """Build and durably write one attempt's run manifest; return its path."""

    # Repo confinement FIRST (IMPORTANT fix, T6 fix round): the cheapest,
    # dependency-free check, before touching git or the filesystem for
    # anything else -- a manifest destined for inside the repository is
    # refused before any other work happens, on COMPLETED and ABORTED calls
    # alike (they share this one function).
    _refuse_if_inside_repo(run_dir, "run manifest run_dir")

    document = _manifest_document(
        repo_root=repo_root,
        data_root=data_root,
        composed=composed,
        plan=plan,
        verified_split=verified_split,
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=status,
        failure_reason=failure_reason,
        result=result,
        now=now,
    )
    manifest_path = _confine_child_path(
        run_dir, f"{plan.run_id}.run-manifest.json", "run manifest path"
    )
    write_json_artifact(manifest_path, document)
    return manifest_path


def _attach_scores(manifest_path: Path, scores_path: Path) -> None:
    try:
        document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read run manifest {manifest_path}: {error}") from error
    document["scores"] = _artifact_meta(scores_path)
    write_json_artifact(manifest_path, document)
