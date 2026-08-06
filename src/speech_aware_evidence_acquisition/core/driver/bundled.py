"""``run_experiment_bundled``: run one attempt and ALWAYS produce a run manifest.

Split out of the former monolithic ``core/driver.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). Every ``build_manifest`` call below
goes through a live reference to the ``core.driver`` package object
(``_driver_pkg``) rather than the bare/imported name, so that
``monkeypatch.setattr(driver_module, "build_manifest", spy)``
(``tests/unit/test_bundle.py``) is observed here exactly as it was when this
function lived directly in ``driver.py`` -- see ``core/driver/__init__.py``'s
own module comment for the full reasoning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Mapping

import speech_aware_evidence_acquisition.core.driver as _driver_pkg

from ...contracts import ExecutionPlan
from ...e0.artifacts import REPO_ROOT
from ..bundle import STATUS_ABORTED, STATUS_COMPLETED, abort_attempt_if_opened, require_clean_study_repo
from ..config import ComposedConfig
from ..resources import ResourceSampler
from ..split_receipt import load_verified_split
from .run import run_experiment


def run_experiment_bundled(
    composed: ComposedConfig,
    plan: ExecutionPlan,
    gate: object,
    lock: Mapping[str, object],
    root: Path,
    run_dir: Path,
    transport: Callable[[bytes], bytes],
    *,
    repo_root: Path = REPO_ROOT,
    session_receipt_path: Path | None = None,
    resource_sampler: ResourceSampler | None = None,
) -> Path:
    """R0 repair T6 (I7): run one attempt and ALWAYS produce a run manifest --
    the audit trail, not a raised exception alone, is the record of what
    happened.

    On success: ``run_experiment`` runs to completion and this returns the
    path to a manifest with status COMPLETED, binding every artifact it
    produced.

    On any failure: the attempt is marked ABORTED on disk (if it was ever
    opened at all -- ``core.bundle.abort_attempt_if_opened`` is a no-op
    otherwise) with the failure's own message as the reason, a manifest is
    still durably written to the SAME deterministic path
    (``run_dir / f"{plan.run_id}.run-manifest.json"``) with status ABORTED
    binding whatever partial artifacts genuinely exist, and then the
    original exception is RE-RAISED (this function does not swallow errors
    -- callers that need the manifest path after a failure can reconstruct
    it from ``run_dir``/``plan.run_id``, or use ``core.bundle.verify_bundle``
    against that path directly). Either way, an ABORTED manifest can never
    later be finalized as COMPLETED (I7; see ``core.bundle.finalize_bundle``).

    CRITICAL fix (T6 fix round): a run that can never produce a valid
    manifest -- e.g. a dirty/unreadable study repo -- must never be allowed
    to spend attempt budget first and discover that only afterward. Two
    guarantees now hold that did not before:

    1. :func:`core.bundle.require_clean_study_repo` runs BEFORE
       ``run_experiment`` is even called, so a dirty tree refuses with no
       attempt ever opened and no budget ever spent -- not merely no
       manifest.
    2. The trailing (success-path) manifest build is itself wrapped: if IT
       fails for any reason (the repo went dirty mid-run, the run_dir became
       unwritable, an artifact vanished between ``run_experiment`` returning
       and the manifest build reading it), the attempt is force-marked
       ABORTED and a best-effort ABORTED manifest is still attempted --
       never silently leaving a successful, budget-consuming run with NO
       manifest and its attempt stuck OPENED forever.

    IMPORTANT fix (T6 fix-2 round): the sibling gap in the ABOVE-DESCRIBED
    "on any failure" path (``except Exception as error:`` around
    ``run_experiment`` itself) is now closed too: that manifest write is
    wrapped the same way, so a SECOND failure while recording the ABORTED
    manifest (the reviewed TOCTOU case: the tree was clean at
    ``require_clean_study_repo`` time but became dirty during a long
    model-facing ``run_experiment`` call, then the run failed for an
    unrelated reason) can never mask or replace the run's ORIGINAL failure,
    and is chained onto it as ``__context__`` instead of silently dropped.
    Combined with ``core.bundle._resolve_study_commit`` now tolerating a
    dirty/unreadable repo for an ABORTED manifest specifically (recording
    ``UNAVAILABLE:<reason>`` as ``study_commit`` rather than raising), the
    reviewed TOCTOU scenario no longer even reaches the wrapped except branch
    in practice -- the wrap is the backstop for whatever else could still
    fail.
    """

    verified_split = load_verified_split(repo_root, str(composed.values["split_name"]), lock, root)
    # CRITICAL fix (T6 fix round), part 1: validate the study repo BEFORE any
    # budget is spent. Previously this check only happened as a side effect
    # of the trailing build_manifest() call, AFTER run_experiment had already
    # opened the attempt and metered every request against it.
    require_clean_study_repo(repo_root)
    try:
        result = run_experiment(
            composed, plan, gate, lock, root, run_dir, transport, repo_root=repo_root,
            resource_sampler=resource_sampler,
        )
    except Exception as error:
        abort_attempt_if_opened(root, plan.run_id, plan.attempt_id, reason=str(error))
        # IMPORTANT fix (T6 fix-2 round): the ORIGINAL run failure -- `error`
        # -- must ALWAYS be what propagates from this function, never masked
        # or replaced by a SECOND failure while trying to record it. Without
        # this wrapping, a dirty-tree TOCTOU during a long model-facing run
        # (the tree was clean when require_clean_study_repo ran, but became
        # dirty before this ABORTED-path manifest write) let build_manifest
        # raise its own BundleError here, which replaced `error` entirely and
        # left zero manifest on disk -- contradicting this function's own
        # "a manifest is still durably written ... either way" contract. With
        # core.bundle._resolve_study_commit now tolerating a dirty/unreadable
        # repo for an ABORTED manifest (recording an
        # UNAVAILABLE:<reason> study_commit instead of raising), this branch
        # should now rarely trigger at all -- but the wrap stays as the
        # backstop for whatever OTHER reason a manifest write could still
        # fail (e.g. a genuinely unwritable run_dir).
        try:
            _driver_pkg.build_manifest(
                repo_root=repo_root,
                data_root=root,
                composed=composed,
                plan=plan,
                verified_split=verified_split,
                session_receipt_path=session_receipt_path,
                run_dir=run_dir,
                status=STATUS_ABORTED,
                failure_reason=str(error),
                result=None,
            )
        except Exception:
            # Re-raising `error` HERE, while still inside this nested except
            # block, sets error.__context__ to the manifest-build failure
            # (visible in tracebacks/logs: "During handling of the above
            # exception, another exception occurred") WITHOUT changing what
            # actually propagates -- `error`, unmodified. This is the
            # deliberate mechanism, not an oversight: it chains the manifest
            # failure as context rather than silently dropping it OR letting
            # it replace the original.
            raise error
        raise
    # CRITICAL fix (T6 fix round), part 2: the run itself succeeded (budget
    # already spent, outputs/trace already durable) -- but building ITS
    # manifest can still fail (a race, an unwritable run_dir, disk pressure).
    # That failure must not leave the attempt OPENED with no manifest at
    # all: force it to ABORTED and try once more, best-effort, to record an
    # ABORTED manifest before re-raising. Mirrors the same
    # never-mask-the-original-failure discipline as the except block above.
    try:
        return _driver_pkg.build_manifest(
            repo_root=repo_root,
            data_root=root,
            composed=composed,
            plan=plan,
            verified_split=verified_split,
            session_receipt_path=session_receipt_path,
            run_dir=run_dir,
            status=STATUS_COMPLETED,
            failure_reason=None,
            result=result,
        )
    except Exception as manifest_error:
        reason = f"run succeeded but its COMPLETED manifest could not be built: {manifest_error}"
        abort_attempt_if_opened(root, plan.run_id, plan.attempt_id, reason=reason)
        try:
            _driver_pkg.build_manifest(
                repo_root=repo_root,
                data_root=root,
                composed=composed,
                plan=plan,
                verified_split=verified_split,
                session_receipt_path=session_receipt_path,
                run_dir=run_dir,
                status=STATUS_ABORTED,
                failure_reason=reason,
                result=None,
            )
        except Exception:
            # Best-effort only: whatever broke the COMPLETED build may break
            # this too (e.g. a truly unwritable run_dir). The attempt is
            # already ABORTED via abort_attempt_if_opened above either way --
            # that is the one guarantee this branch exists to protect. Chain
            # (not replace) for the same reason as above.
            raise manifest_error
        raise
