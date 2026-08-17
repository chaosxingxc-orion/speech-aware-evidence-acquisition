"""Study-repo git commit resolution for a run manifest's ``study_commit`` field.

Split out of ``core/bundle/manifest.py`` (R0 repair refactor stage 2, part C,
pure move, no behaviour change) purely for file size.

E0-prime flight protection (2026-08-16 incident): a governance-document edit
(outside any load-bearing surface) landed in the working tree mid-flight and
:func:`_study_commit`'s ORIGINAL, unconditional dirty-tree refusal fired at
COMPLETED-manifest build time, destroying 156 minutes of already-spent
inference -- ``run_experiment_bundled`` forced the attempt to ABORTED and I7
forbids ever finalizing an ABORTED manifest as COMPLETED afterward, so the
real, complete outputs on disk became permanently unfinalizable. The launch-
time preflight (``require_clean_study_repo``, called by
``core.driver.run_experiment_bundled`` BEFORE any budget is spent, and again
by ``core.scorers._assert_scoring_entry_gate`` at scoring time) is UNCHANGED
by this fix and stays fully strict -- refusing early, before compute is
spent, is exactly the right behaviour there. What changed is narrower:
:func:`_study_commit_for_completed_manifest`, used ONLY for the COMPLETED-
manifest's own ``study_commit`` bind (the step that actually fired in the
incident, well after compute was already spent), now tolerates dirt CONFINED
outside :data:`LOAD_BEARING_SURFACE_PREFIXES` -- code, config fragments, arm
files, and launch scripts still refuse outright; a stray edit to a wiki page,
a readiness note, or any other governance document does not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..flight_lock import read_flight_lock
from . import UNAVAILABLE_COMMIT_PREFIX, STATUS_COMPLETED, BundleError

# The load-bearing surface a run's SCIENCE actually depends on: the code the
# driver imports (src/), the config fragments a run composes (configs/), the
# committed arm files a sequence launches from (docs/arms/), and the launch
# scripts themselves (scripts/). Trailing slash on every entry is load-
# bearing for _is_load_bearing_relpath's prefix match below -- do not drop
# it when adding an entry.
LOAD_BEARING_SURFACE_PREFIXES = ("src/", "configs/", "docs/arms/", "scripts/")

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


def _is_load_bearing_relpath(relpath: str) -> bool:
    """True if a repo-relative, forward-slash path falls inside
    :data:`LOAD_BEARING_SURFACE_PREFIXES`. A bare directory name (no
    trailing slash, e.g. from an unusual porcelain rendering) still matches
    its own prefix -- this is a prefix test, not merely ``startswith`` on
    the raw entry."""

    return any(
        relpath == prefix[:-1] or relpath.startswith(prefix)
        for prefix in LOAD_BEARING_SURFACE_PREFIXES
    )


def _dirty_relpaths(porcelain: str) -> list[str]:
    """Parse ``git status --porcelain`` (v1) output into repo-relative,
    forward-slash paths -- one per dirty entry. A rename/copy entry
    (``R  old -> new`` / ``C  old -> new``) contributes only the
    POST-rename path, matching what stays dirty going forward. Git quotes a
    path containing unusual characters in double quotes; those quotes are
    stripped so the result is a bare path either way."""

    paths: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        # Porcelain v1: exactly 2 status chars, then one space, then the
        # path (``line[3:]``); tolerate a shorter/malformed line rather than
        # raising on a git version's format quirk we did not anticipate.
        entry = line[3:] if len(line) > 3 else line[2:].lstrip()
        if " -> " in entry:
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip()
        if len(entry) >= 2 and entry[0] == '"' and entry[-1] == '"':
            entry = entry[1:-1]
        if entry:
            paths.append(entry.replace("\\", "/"))
    return paths


def _study_commit_for_completed_manifest(repo_root: Path, data_root: Path) -> tuple[str, list[str]]:
    """Read the study repo's commit for a COMPLETED manifest, tolerating
    dirt CONFINED outside :data:`LOAD_BEARING_SURFACE_PREFIXES` (see this
    module's own docstring for the incident this repairs).

    Refuses (:class:`BundleError`) when:

    - ``git status``/``git rev-parse`` themselves fail -- mirrors
      :func:`_study_commit`'s own refusal, unchanged;
    - any dirty path falls inside the load-bearing surface -- code, config,
      arm files, or launch scripts describe WHAT the run executed, so dirt
      there is exactly the "the commit is a lie" case :func:`_study_commit`'s
      docstring already refuses, and this function refuses it identically;
    - a flight lock exists under ``data_root/locks/flight.lock`` (written at
      launch by ``scripts/run_arm_sequence.sh``) whose recorded
      ``study_head`` no longer matches the tree's CURRENT HEAD -- a HEAD
      MOVE during the flight is a different code identity underneath the
      run, not mere dirt, and the load-bearing-surface carve-out was never
      meant to tolerate that.

    Otherwise returns ``(commit, non_load_bearing_dirty_paths)``: the second
    element is empty on a genuinely clean tree, and is recorded onto the
    manifest by the caller for auditability -- never silently dropped."""

    code, porcelain, stderr = _git(repo_root, "status", "--porcelain")
    if code != 0:
        raise BundleError(f"cannot read git status for {repo_root}: {stderr}")

    dirty_paths = _dirty_relpaths(porcelain)
    load_bearing_dirty = sorted(p for p in dirty_paths if _is_load_bearing_relpath(p))
    non_load_bearing_dirty = sorted(p for p in dirty_paths if not _is_load_bearing_relpath(p))

    if load_bearing_dirty:
        raise BundleError(
            f"study repo {repo_root} has uncommitted changes inside the load-bearing "
            f"surface {LOAD_BEARING_SURFACE_PREFIXES}; a run manifest must bind the exact "
            "commit that produced the run, never a dirty tree over code/config/arms/scripts:\n"
            + "\n".join(load_bearing_dirty)
        )

    code, commit, stderr = _git(repo_root, "rev-parse", "HEAD")
    if code != 0 or not commit:
        raise BundleError(f"cannot read the study repo's HEAD commit at {repo_root}: {stderr}")

    lock = read_flight_lock(data_root)
    if lock is not None:
        expected_head = lock.get("study_head")
        if isinstance(expected_head, str) and expected_head and expected_head != commit:
            raise BundleError(
                f"study repo {repo_root} HEAD moved during the flight: the flight lock "
                f"recorded study_head {expected_head!r} at launch, HEAD is now {commit!r}; "
                "refusing to bind a COMPLETED manifest to a commit the flight never ran "
                "under, even though the working tree's own dirt is confined outside the "
                "load-bearing surface"
            )

    return commit, non_load_bearing_dirty


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


def _resolve_study_commit(repo_root: Path, data_root: Path, status: str) -> tuple[str, list[str]]:
    """Read the study commit for a manifest being built, with a status-aware
    tolerance (IMPORTANT fix, T6 fix-2 round -- closes the sibling gap
    CRITICAL 2's fix left open; NARROWED for COMPLETED by the 2026-08-16
    flight-protection fix, see this module's docstring).

    A COMPLETED manifest now uses :func:`_study_commit_for_completed_manifest`:
    dirt confined outside :data:`LOAD_BEARING_SURFACE_PREFIXES` (and a HEAD
    that has not moved since the flight's launch, per the flight lock) is
    tolerated and recorded rather than refused; dirt inside that surface, an
    unreadable repo, or a moved HEAD still refuse exactly as before.

    An ABORTED manifest is different in kind, and UNCHANGED by that
    narrowing: it exists precisely BECAUSE something already went wrong, and
    the reviewed defect was exactly this -- ``run_experiment_bundled``'s own
    dirty-tree check runs once, BEFORE ``run_experiment`` starts, but a real
    model-facing run can take long enough for the tree to become dirty DURING
    it (a genuine TOCTOU window, not a hypothetical one); a run that then
    fails for an UNRELATED reason must still leave a durable ABORTED record,
    not silently lose one to a second, unrelated ``BundleError`` about the
    tree. So an ABORTED manifest tries the ORIGINAL strict read first (if the
    tree genuinely is still clean, the real commit is strictly more useful
    than a placeholder and is recorded), and only on failure substitutes
    ``f"{UNAVAILABLE_COMMIT_PREFIX}{reason}"``. An honest "commit unavailable,
    here is why" marker on a record that already says ABORTED is strictly
    better than no record at all for that attempt -- but it must never be
    mistakable for a COMPLETED one, which is why the COMPLETED path above
    never takes this fallback, and :func:`verify_bundle` separately refuses
    any manifest that claims ``status == COMPLETED`` while carrying this
    marker (defense in depth against a hand-tampered manifest, not just a
    structural guarantee about what ``build_manifest`` itself would ever
    produce).

    Returns ``(study_commit, non_load_bearing_dirty_paths)`` in both cases --
    the second element is always empty for an ABORTED manifest (its
    UNAVAILABLE marker already carries the reason inline; there is no
    separate dirt list to record), and empty for a COMPLETED manifest built
    against a genuinely clean tree.
    """

    if status == STATUS_COMPLETED:
        return _study_commit_for_completed_manifest(Path(repo_root), Path(data_root))
    try:
        return _study_commit(Path(repo_root)), []
    except BundleError as error:
        return f"{UNAVAILABLE_COMMIT_PREFIX}{error}", []
