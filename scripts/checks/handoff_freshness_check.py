#!/usr/bin/env python3
"""Model-free gate: the standing handoff must not go stale.

``docs/handoff/HANDOFF-TO-CHATGPT.md`` is the standing counterpart to
``docs/handoff/HANDOFF-TO-FABLE51.md``: ONE short file, refreshed in place
after every landed result, no log section. A handoff that is one result behind
is worse than no handoff, because the reader cannot tell which. So the file
carries its own stamp,

    Last refreshed: 2026-09-26T14:30:00Z

and this script compares that stamp against the newest thing the program has
landed. A result that landed after the stamp means the handoff does not mention
it, and that staleness is the maintainer's defect.

**The three timestamps compared**, all printed on every run:

1. **the stamp** -- the ``Last refreshed:`` line, parsed STRICTLY: ISO-8601,
   timezone-aware, and UTC (a ``Z`` suffix or a ``+00:00`` offset). A naive or
   non-UTC stamp is a finding, not a guess.
2. **the newest result** -- over ``docs/results/*.md``. For a TRACKED file the
   git commit date is preferred over the filesystem mtime, because a fresh
   clone's mtimes are all the clone time and would make every handoff look
   stale; for an untracked file (a result note written but not yet committed)
   the mtime is all there is. The output names which source it used and for
   which file. ``--no-git`` forces mtimes; a tree that is not a git checkout,
   or a machine with no ``git`` on PATH, falls back to mtimes and says so.
3. **the newest ledger entry** -- the newest date-led heading of
   ``docs/results/stage2-results-ledger.md`` (``## 2026-09-24: cell CELL-3,
   ...``), read as that date at 00:00 UTC. The ledger's headings are the
   program's own index of landed verdicts, so a heading newer than the stamp is
   a landed verdict the handoff has not seen.

**Findings** (each a separate printed line, each a FAIL, exit 1):

``missing-file``
    The handoff file does not exist. The message names the path.
``missing-stamp``
    No ``Last refreshed:`` line.
``unparsable-stamp``
    The stamp is not a strict ISO-8601 UTC timestamp.
``stale-vs-results``
    The stamp is older than the newest ``docs/results/*.md``.
``stale-vs-ledger``
    The stamp is older than the newest date-led heading of the results ledger.
``stamp-in-future``
    The stamp is ahead of now by more than :data:`FUTURE_TOLERANCE_SECONDS`
    (a few minutes of clock slack, because the maintainer stamps by hand and
    WSL / host clocks drift).
``over-max-age``
    Only with ``--max-age-hours N``: the stamp is older than N hours even
    though nothing newer has landed. Off by default -- the default contract is
    relative freshness, not a heartbeat.

Exit 0 when no finding remains, 1 otherwise. Both exit codes are documented:
there is no third outcome, and an unreadable tree is exit 1 with the reason on
stderr.

Zero model contacts, zero GPU, no network, no ``SPEECHRL_DATA_DIR`` read. The
only subprocess is ``git`` on the local repository, read-only.

Flags: ``--repo-root``, ``--handoff``, ``--results-dir``, ``--ledger``,
``--max-age-hours``, ``--no-git``, ``--now``, ``--json``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

HANDOFF = Path("docs/handoff/HANDOFF-TO-CHATGPT.md")
RESULTS_DIR = Path("docs/results")
RESULTS_LEDGER = Path("docs/results/stage2-results-ledger.md")

#: The one line shape the handoff must carry.
STAMP_PATTERN = re.compile(r"^Last refreshed:\s*(\S+)", re.MULTILINE)

#: A date-led heading of the results ledger: ``## 2026-09-24: cell CELL-3 ...``
LEDGER_HEADING = re.compile(r"^#{1,6}\s+(\d{4}-\d{2}-\d{2})\b", re.MULTILINE)

#: Hand-written stamps and drifting WSL clocks earn a few minutes of slack.
FUTURE_TOLERANCE_SECONDS = 300


class HandoffFreshnessCheckError(RuntimeError):
    """The gate could not read something it must read."""


def _parse_stamp(token: str) -> tuple[dt.datetime | None, str | None]:
    """``(the timestamp, why it is not one)`` -- strict ISO-8601 UTC."""

    try:
        parsed = dt.datetime.fromisoformat(token)
    except ValueError as error:
        return None, f"{token!r} is not an ISO-8601 timestamp ({error})"
    if parsed.tzinfo is None:
        return None, (
            f"{token!r} carries no timezone; the stamp must be UTC, written with a "
            "trailing 'Z' or a '+00:00' offset"
        )
    if parsed.utcoffset() != dt.timedelta(0):
        return None, (
            f"{token!r} is not UTC (offset {parsed.utcoffset()}); the stamp must be UTC"
        )
    return parsed.astimezone(dt.timezone.utc), None


def _git(repo_root: Path, *args: str) -> tuple[int, str]:
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as error:
        return 127, str(error)
    return completed.returncode, completed.stdout


def _mtime(path: Path) -> dt.datetime:
    return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)


def _newest_result(
    repo_root: Path, results_dir: Path, use_git: bool
) -> dict[str, Any]:
    """The newest ``*.md`` under ``results_dir``, and how it was dated."""

    directory = repo_root / results_dir
    if not directory.is_dir():
        raise HandoffFreshnessCheckError(f"missing {results_dir.as_posix()}")
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise HandoffFreshnessCheckError(
            f"{results_dir.as_posix()} holds no *.md file to compare the stamp against"
        )

    git_available = False
    git_reason = "--no-git: filesystem mtimes only"
    newest: dt.datetime | None = None
    newest_file: str | None = None
    newest_source: str | None = None

    if use_git:
        code, _ = _git(repo_root, "rev-parse", "--git-dir")
        if code == 0:
            git_available = True
            git_reason = "git commit dates for tracked files, mtimes for untracked ones"
        elif code == 127:
            git_reason = "no usable git on PATH: filesystem mtimes only"
        else:
            git_reason = "not a git checkout: filesystem mtimes only"

    tracked: set[str] = set()
    if git_available:
        pathspec = f"{results_dir.as_posix()}/*.md"
        code, out = _git(repo_root, "ls-files", "--", pathspec)
        if code == 0:
            tracked = {line.strip() for line in out.splitlines() if line.strip()}
        code, out = _git(
            repo_root, "log", "-1", "--format=%cI", "--name-only", "--", pathspec
        )
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        if code == 0 and lines:
            stamp, *touched = lines
            try:
                parsed = dt.datetime.fromisoformat(stamp).astimezone(dt.timezone.utc)
            except ValueError as error:  # pragma: no cover - git's own format
                raise HandoffFreshnessCheckError(
                    f"cannot read the git commit date {stamp!r}: {error}"
                ) from error
            in_scope = [name for name in touched if name.startswith(f"{results_dir.as_posix()}/")]
            newest = parsed
            newest_file = sorted(in_scope)[0] if in_scope else pathspec
            newest_source = "git commit date"

    # A tracked file's date came from git above; without a git date (a tree with
    # no commit touching these paths) every file falls back to its mtime.
    skip_tracked = newest is not None
    for path in paths:
        relpath = path.relative_to(repo_root).as_posix()
        if skip_tracked and relpath in tracked:
            continue
        stamp = _mtime(path)
        if newest is None or stamp > newest:
            newest = stamp
            newest_file = relpath
            newest_source = "filesystem mtime"

    assert newest is not None and newest_file is not None  # noqa: S101 - paths non-empty
    return {
        "timestamp": newest,
        "file": newest_file,
        "source": newest_source,
        "dating": git_reason,
        "files_considered": len(paths),
        "tracked_files": len(tracked),
    }


def _newest_ledger_entry(repo_root: Path, ledger: Path) -> dict[str, Any]:
    path = repo_root / ledger
    if not path.is_file():
        raise HandoffFreshnessCheckError(f"missing {ledger.as_posix()}")
    text = path.read_text(encoding="utf-8", errors="replace")
    dates = sorted({match for match in LEDGER_HEADING.findall(text)})
    if not dates:
        return {"timestamp": None, "heading_date": None, "headings": 0}
    newest = dates[-1]
    return {
        "timestamp": dt.datetime.fromisoformat(f"{newest}T00:00:00+00:00"),
        "heading_date": newest,
        "headings": len(dates),
    }


def evaluate(
    repo_root: Path,
    handoff: Path = HANDOFF,
    results_dir: Path = RESULTS_DIR,
    ledger: Path = RESULTS_LEDGER,
    max_age_hours: float | None = None,
    use_git: bool = True,
    now: dt.datetime | None = None,
) -> dict[str, Any]:
    now = (now or dt.datetime.now(tz=dt.timezone.utc)).astimezone(dt.timezone.utc)
    findings: list[dict[str, str]] = []

    path = repo_root / handoff
    stamp: dt.datetime | None = None
    stamp_token: str | None = None
    if not path.is_file():
        findings.append(
            {
                "kind": "missing-file",
                "message": (
                    f"{handoff.as_posix()} does not exist; the standing handoff to the other "
                    "collaborator is the file this gate keeps fresh, so its absence is the "
                    "first failure and not an exemption"
                ),
            }
        )
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        match = STAMP_PATTERN.search(text)
        if match is None:
            findings.append(
                {
                    "kind": "missing-stamp",
                    "message": (
                        f"{handoff.as_posix()} carries no 'Last refreshed: <ISO-8601 UTC>' "
                        "line; without it nobody can tell which results the handoff has seen"
                    ),
                }
            )
        else:
            stamp_token = match[1]
            stamp, problem = _parse_stamp(stamp_token)
            if stamp is None:
                findings.append(
                    {
                        "kind": "unparsable-stamp",
                        "message": (
                            f"{handoff.as_posix()}: 'Last refreshed:' {problem}"
                        ),
                    }
                )

    newest_result = _newest_result(repo_root, results_dir, use_git)
    newest_entry = _newest_ledger_entry(repo_root, ledger)

    if stamp is not None:
        if stamp < newest_result["timestamp"]:
            findings.append(
                {
                    "kind": "stale-vs-results",
                    "message": (
                        f"the stamp {stamp.isoformat()} is older than "
                        f"{newest_result['file']} at "
                        f"{newest_result['timestamp'].isoformat()} "
                        f"({newest_result['source']}); a landed result the handoff does not "
                        "mention is staleness, and the fix is to refresh the handoff in place"
                    ),
                }
            )
        if (
            newest_entry["timestamp"] is not None
            and stamp < newest_entry["timestamp"]
        ):
            findings.append(
                {
                    "kind": "stale-vs-ledger",
                    "message": (
                        f"the stamp {stamp.isoformat()} is older than the newest entry "
                        f"heading of {ledger.as_posix()} ({newest_entry['heading_date']}, "
                        f"read as {newest_entry['timestamp'].isoformat()})"
                    ),
                }
            )
        ahead = (stamp - now).total_seconds()
        if ahead > FUTURE_TOLERANCE_SECONDS:
            findings.append(
                {
                    "kind": "stamp-in-future",
                    "message": (
                        f"the stamp {stamp.isoformat()} is {ahead / 60:.1f} minute(s) ahead of "
                        f"now ({now.isoformat()}), beyond the "
                        f"{FUTURE_TOLERANCE_SECONDS}s clock slack; a stamp in the future "
                        "cannot be evidence of a refresh that happened"
                    ),
                }
            )
        if max_age_hours is not None:
            age_hours = (now - stamp).total_seconds() / 3600.0
            if age_hours > max_age_hours:
                findings.append(
                    {
                        "kind": "over-max-age",
                        "message": (
                            f"the stamp {stamp.isoformat()} is {age_hours:.2f}h old, over the "
                            f"requested --max-age-hours {max_age_hours:g}"
                        ),
                    }
                )

    return {
        "schema": "saea-handoff-freshness-check-v1",
        "repo_root": str(repo_root),
        "handoff": handoff.as_posix(),
        "results_dir": results_dir.as_posix(),
        "ledger": ledger.as_posix(),
        "now": now.isoformat(),
        "max_age_hours": max_age_hours,
        "future_tolerance_seconds": FUTURE_TOLERANCE_SECONDS,
        "stamp_token": stamp_token,
        "stamp": stamp.isoformat() if stamp else None,
        "newest_result": {
            "timestamp": newest_result["timestamp"].isoformat(),
            "file": newest_result["file"],
            "source": newest_result["source"],
            "dating": newest_result["dating"],
            "files_considered": newest_result["files_considered"],
            "tracked_files": newest_result["tracked_files"],
        },
        "newest_ledger_entry": {
            "timestamp": (
                newest_entry["timestamp"].isoformat()
                if newest_entry["timestamp"]
                else None
            ),
            "heading_date": newest_entry["heading_date"],
            "headings": newest_entry["headings"],
        },
        "findings": findings,
        "passed": not findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--handoff", type=Path, default=HANDOFF)
    parser.add_argument("--results-dir", type=Path, default=RESULTS_DIR)
    parser.add_argument("--ledger", type=Path, default=RESULTS_LEDGER)
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=None,
        help="additionally require the stamp to be no older than N hours (off by default)",
    )
    parser.add_argument(
        "--no-git",
        action="store_true",
        help="date the result notes by filesystem mtime only, never by git commit date",
    )
    parser.add_argument(
        "--now",
        default=None,
        metavar="ISO-8601",
        help="treat this instant as now (for tests and for asking 'is it stale at T?')",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    now = None
    if args.now is not None:
        now, problem = _parse_stamp(args.now)
        if now is None:
            print(f"handoff freshness check: FAIL: --now {problem}", file=sys.stderr)
            return 1

    try:
        data = evaluate(
            args.repo_root.resolve(),
            args.handoff,
            args.results_dir,
            args.ledger,
            args.max_age_hours,
            not args.no_git,
            now,
        )
    except HandoffFreshnessCheckError as error:
        print(f"handoff freshness check: FAIL: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1

    for finding in data["findings"]:
        print(f"handoff freshness check: FAIL: [{finding['kind']}] {finding['message']}")

    result = data["newest_result"]
    entry = data["newest_ledger_entry"]
    print(
        f"handoff freshness check: compared: stamp {data['stamp'] or '<none>'} | newest "
        f"{result['file']} {result['timestamp']} ({result['source']}; "
        f"{result['dating']}; {result['files_considered']} file(s), "
        f"{result['tracked_files']} tracked) | newest ledger entry heading "
        f"{entry['heading_date'] or '<none>'} ({entry['timestamp'] or '-'}) | now "
        f"{data['now']}"
    )
    summary = (
        f"{data['handoff']}; "
        + (
            f"--max-age-hours {data['max_age_hours']:g}"
            if data["max_age_hours"] is not None
            else "no max age requested"
        )
        + f"; {len(data['findings'])} finding(s)"
    )
    if data["passed"]:
        print(f"handoff freshness check: PASS ({summary})")
        return 0
    print(f"handoff freshness check: FAIL ({summary})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
