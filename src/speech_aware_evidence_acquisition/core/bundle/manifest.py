"""Run-manifest construction: repo confinement, ``build_manifest``.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). R0 repair refactor stage 2 (part C):
the git-commit resolution helpers (``_git``/``_study_commit``/
``require_clean_study_repo``/``_resolve_study_commit``) and the ABORTED-
manifest best-effort cost block (``_best_effort_cost_for_aborted_attempt``)
moved to ``git_commit.py``/``aborted_cost.py`` respectively, again purely for
file size -- both stay importable from exactly ``core.bundle`` (this
module re-exports ``require_clean_study_repo``, the one name
``core/bundle/__init__.py`` itself re-exports onward).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ...contracts import STUDY_SLUG, ExecutionPlan
from ...e0.artifacts import sha256_file, write_json_artifact
from ..base import RunResult
from ..config import ComposedConfig
from ..split_receipt import VerifiedSplit
from . import (
    RUN_MANIFEST_SCHEMA,
    STATUS_ABORTED,
    STATUS_COMPLETED,
    _VALID_STATUSES,
    BundleError,
    _confine_child_path,
    _refuse_if_inside_repo,
)
from .aborted_cost import _best_effort_cost_for_aborted_attempt
from .git_commit import _resolve_study_commit, require_clean_study_repo  # noqa: F401 (re-export)


def _artifact_meta(path: Path) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "sha256": sha256_file(path)}


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
