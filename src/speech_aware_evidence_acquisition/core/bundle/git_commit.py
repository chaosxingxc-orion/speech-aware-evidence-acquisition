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
time preflight (:func:`require_clean_study_repo`, called by
``core.driver.run_experiment_bundled`` BEFORE any budget is spent) is
UNCHANGED by that fix and stays fully strict -- refusing early, before
compute is spent, is exactly the right behaviour there. What changed is
narrower: :func:`_study_commit_for_completed_manifest`, used ONLY for the
COMPLETED-manifest's own ``study_commit`` bind (the step that actually fired
in the incident, well after compute was already spent), tolerates dirt
CONFINED outside :data:`LOAD_BEARING_SURFACE_PREFIXES` -- code, config
fragments, arm files, and launch scripts still refuse outright; a stray edit
to a wiki page, a readiness note, or any other governance document does not.

SCORING-SIDE SYMMETRY (2026-09-09). That narrowing was applied to the SEAL
half only. The SCORE half -- ``core.scorers._assert_scoring_entry_gate``,
reached by ``score_bundle``/``finalize_bundle``/``saea-driver score
--manifest`` -- kept calling :func:`require_clean_study_repo`, so from the
2026-08-16 commit onward a manifest could seal COMPLETED over a stray
governance document and then be UNSCOREABLE and UNFINALIZABLE on the very
same tree: the incident, moved one step later. The measured symptom was the
Audio2Tool wire checks' ``seal_and_score = SCORING_FAILED`` / "official
scorer exited with status 1" over an untracked readiness note (receipt:
``docs/checks/speech-aware-evidence-acquisition/
2026-09-09-a2t-official-scorer-seal-and-score-diagnosis/``). The two halves
now share ONE rule, :func:`require_clean_load_bearing_surface`: whatever
seals can be scored, and whatever the seal refuses the score refuses too.
The guarantee the scoring gate exists for is untouched, because every file
whose bytes can change a score -- the driver's own ``src/`` (including
``data/references.py``, which the D3 freeze over ``scoring/*.py`` does not
cover), the composed ``configs/``, ``docs/arms/`` and ``scripts/`` -- is
inside the load-bearing surface and still refuses.
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
    )
    # Status columns and path bytes are significant: stripping stdout erases
    # the index column of a first unstaged change. Decode without newline
    # conversion so a filename containing CR/LF also survives unchanged.
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", errors="surrogateescape"),
        completed.stderr.decode("utf-8", errors="surrogateescape").strip(),
    )


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
    commit = commit.strip()
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
    """Parse porcelain v1 ``-z``, preserving paths and both sides of a move.

    Git emits ``XY path<NUL>``; a rename/copy adds ``source<NUL>`` after its
    destination. Both paths affect the cleanliness boundary. NUL delimiters
    make spaces, quotes, arrows and newlines literal filename bytes. Refuse
    malformed output instead of classifying an incomplete path as harmless.
    """

    if not porcelain:
        return []
    if not porcelain.endswith("\0"):
        raise BundleError("malformed git porcelain: missing terminal NUL")
    entries = porcelain[:-1].split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if (
            len(entry) < 4
            or entry[2] != " "
            or any(status not in " MADRCUT?!" for status in entry[:2])
            or entry[:2] == "  "
        ):
            raise BundleError("malformed git porcelain: invalid status or missing path")
        paths.append(entry[3:])
        if "R" in entry[:2] or "C" in entry[:2]:
            if index >= len(entries) or not entries[index]:
                raise BundleError("malformed git porcelain: rename/copy source is missing")
            paths.append(entries[index])
            index += 1
    return paths


def require_clean_load_bearing_surface(repo_root: Path) -> tuple[str, list[str]]:
    """The ONE rule both halves of a seal share: refuse dirt inside
    :data:`LOAD_BEARING_SURFACE_PREFIXES`, tolerate and REPORT dirt outside
    it.

    Refuses (:class:`BundleError`) when ``git status``/``git rev-parse``
    themselves fail -- mirroring :func:`_study_commit`'s own refusal,
    unchanged -- or when any dirty path falls inside the load-bearing
    surface: code, config fragments, arm files and launch scripts describe
    WHAT the run executed and what computes its score, so dirt there is
    exactly the "the commit is a lie" case :func:`_study_commit`'s docstring
    already refuses, and this function refuses it identically.

    Otherwise returns ``(commit, non_load_bearing_dirty_paths)``, the second
    element empty on a genuinely clean tree.

    Used by :func:`_study_commit_for_completed_manifest` (which adds the
    flight-lock HEAD-move check on top) when a COMPLETED manifest binds its
    commit, and by ``core.scorers._assert_scoring_entry_gate`` when that
    manifest is scored. Sharing it is the point: a manifest that sealed can
    always be scored and finalized on the same tree, and a tree the seal
    refuses is refused at scoring too."""

    repo_root = Path(repo_root)
    code, porcelain, stderr = _git(
        repo_root, "status", "--porcelain=v1", "-z", "--untracked-files=all"
    )
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
    commit = commit.strip()
    if code != 0 or not commit:
        raise BundleError(f"cannot read the study repo's HEAD commit at {repo_root}: {stderr}")

    return commit, non_load_bearing_dirty


def _study_commit_for_completed_manifest(repo_root: Path, data_root: Path) -> tuple[str, list[str]]:
    """Read the study repo's commit for a COMPLETED manifest, tolerating
    dirt CONFINED outside :data:`LOAD_BEARING_SURFACE_PREFIXES` (see this
    module's own docstring for the incident this repairs).

    Refuses (:class:`BundleError`) when:

    - ``git status``/``git rev-parse`` themselves fail, or any dirty path
      falls inside the load-bearing surface -- both are
      :func:`require_clean_load_bearing_surface`, the rule this function now
      shares with the scoring entry gate rather than spelling out a second
      time;
    - a flight lock exists under ``data_root/locks/flight.lock`` (written at
      launch by ``scripts/run_arm_sequence.sh``) whose recorded
      ``study_head`` no longer matches the tree's CURRENT HEAD -- a HEAD
      MOVE during the flight is a different code identity underneath the
      run, not mere dirt, and the load-bearing-surface carve-out was never
      meant to tolerate that. This check is build-time only: it is about the
      flight that produced the outputs, not about the process that scores
      them afterwards.

    Otherwise returns ``(commit, non_load_bearing_dirty_paths)``: the second
    element is empty on a genuinely clean tree, and is recorded onto the
    manifest by the caller for auditability -- never silently dropped."""

    commit, non_load_bearing_dirty = require_clean_load_bearing_surface(Path(repo_root))

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
    exactly as ``_study_commit`` does.

    This is the LAUNCH-TIME rule and stays maximally strict: refusing on any
    dirt at all, before a single call or audio-second is spent, costs
    nothing and is what keeps a flight's commit honest. It is deliberately
    NOT the rule the SCORING entry gate applies (2026-09-09) -- by the time
    scoring runs the compute is already spent and the manifest already
    sealed, so that gate uses :func:`require_clean_load_bearing_surface`, the
    same rule the COMPLETED bind uses, and this module's own docstring says
    why."""

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
