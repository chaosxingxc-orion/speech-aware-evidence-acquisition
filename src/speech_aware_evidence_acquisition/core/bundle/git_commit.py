"""Study-repo git commit resolution for a run manifest's ``study_commit`` field.

Split out of ``core/bundle/manifest.py`` (R0 repair refactor stage 2, part C,
pure move, no behaviour change) purely for file size.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from . import UNAVAILABLE_COMMIT_PREFIX, STATUS_COMPLETED, BundleError

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
