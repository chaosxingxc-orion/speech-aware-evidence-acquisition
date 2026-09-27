"""The handoff freshness gate, on synthetic repositories.

``scripts/checks/handoff_freshness_check.py`` keeps the standing handoff
``docs/handoff/HANDOFF-TO-CHATGPT.md`` from going stale: its
``Last refreshed:`` stamp must not be older than the newest
``docs/results/*.md`` or the newest date-led entry heading of the results
ledger, and must not be in the future. Every finding is exercised here on a
miniature tree in a temporary directory, with ``--now`` pinned so the
arithmetic is deterministic, plus one real git repository built in a temporary
directory to prove the commit-date preference. One test at the end runs the
gate against the real repository and asserts only that it terminates with a
documented exit code (0 or 1).

Zero model, tokenizer, encoder, scorer, network and GPU contacts; no
``SPEECHRL_DATA_DIR`` read. The only subprocess is ``git`` inside ``tmp_path``.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_CHECKS = _REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import handoff_freshness_check as gate  # noqa: E402

NOW = dt.datetime(2026, 9, 26, 18, 0, 0, tzinfo=dt.timezone.utc)


def _build(
    root: Path,
    *,
    stamp: str | None = "2026-09-26T17:00:00Z",
    result_mtime: dt.datetime = NOW - dt.timedelta(hours=4),
    ledger_heading_date: str = "2026-09-25",
    handoff_exists: bool = True,
    stamp_line: str | None = None,
) -> None:
    """One synthetic tree: one handoff, one result note, one results ledger."""

    (root / "docs" / "handoff").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "results").mkdir(parents=True, exist_ok=True)

    if handoff_exists:
        line = stamp_line if stamp_line is not None else (
            f"Last refreshed: {stamp} - maintainer: synthetic" if stamp else "no stamp here"
        )
        (root / "docs" / "handoff" / "HANDOFF-TO-CHATGPT.md").write_text(
            f"# Handoff to ChatGPT\n\n{line}\n\n## 1. State\n\nsynthetic\n",
            encoding="utf-8",
        )

    ledger = root / "docs" / "results" / "stage2-results-ledger.md"
    ledger.write_text(
        "# Stage-2 results ledger\n\n"
        "## The rules this ledger follows\n\nsynthetic\n\n"
        f"## {ledger_heading_date}: a synthetic verdict\n\nsynthetic\n",
        encoding="utf-8",
    )
    note = root / "docs" / "results" / "2026-09-26-synthetic-read.md"
    note.write_text("# A synthetic result note\n", encoding="utf-8")
    for path in (ledger, note):
        stamp_seconds = result_mtime.timestamp()
        os.utime(path, (stamp_seconds, stamp_seconds))


def _evaluate(root: Path, **kwargs) -> dict:
    kwargs.setdefault("use_git", False)
    kwargs.setdefault("now", NOW)
    return gate.evaluate(root, **kwargs)


def _kinds(data: dict) -> list[str]:
    return [finding["kind"] for finding in data["findings"]]


# --------------------------------------------------------------------------
# the happy path and the missing file
# --------------------------------------------------------------------------


def test_a_fresh_handoff_passes(tmp_path: Path) -> None:
    _build(tmp_path)
    data = _evaluate(tmp_path)
    assert data["findings"] == []
    assert data["passed"] is True
    assert data["stamp"] == "2026-09-26T17:00:00+00:00"
    assert data["newest_result"]["source"] == "filesystem mtime"
    assert data["newest_ledger_entry"]["heading_date"] == "2026-09-25"
    assert gate.main(["--repo-root", str(tmp_path), "--no-git", "--now", NOW.isoformat()]) == 0


def test_a_missing_handoff_fails_and_names_the_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _build(tmp_path, handoff_exists=False)
    data = _evaluate(tmp_path)
    assert _kinds(data) == ["missing-file"]
    assert gate.HANDOFF.as_posix() in data["findings"][0]["message"]
    assert data["passed"] is False
    assert gate.main(["--repo-root", str(tmp_path), "--no-git", "--now", NOW.isoformat()]) == 1
    assert "docs/handoff/HANDOFF-TO-CHATGPT.md" in capsys.readouterr().out


# --------------------------------------------------------------------------
# the stamp
# --------------------------------------------------------------------------


def test_a_handoff_with_no_stamp_fails(tmp_path: Path) -> None:
    _build(tmp_path, stamp=None)
    assert _kinds(_evaluate(tmp_path)) == ["missing-stamp"]


@pytest.mark.parametrize(
    "token",
    [
        "yesterday",
        "2026-09-26",  # a date is not a timestamp
        "2026-09-26T17:00:00",  # naive
        "2026-09-26T17:00:00+02:00",  # not UTC
        "26/09/2026 17:00Z",
    ],
)
def test_a_stamp_that_is_not_strict_iso_8601_utc_fails(tmp_path: Path, token: str) -> None:
    _build(tmp_path, stamp=token)
    data = _evaluate(tmp_path)
    assert _kinds(data) == ["unparsable-stamp"]
    assert data["stamp_token"] == token.split()[0]


@pytest.mark.parametrize("token", ["2026-09-26T17:00:00Z", "2026-09-26T17:00:00+00:00"])
def test_both_utc_spellings_are_accepted(tmp_path: Path, token: str) -> None:
    _build(tmp_path, stamp=token)
    assert _evaluate(tmp_path)["findings"] == []


def test_a_stamp_in_the_future_fails(tmp_path: Path) -> None:
    _build(tmp_path, stamp="2026-09-27T09:00:00Z")
    data = _evaluate(tmp_path)
    assert _kinds(data) == ["stamp-in-future"]
    assert "ahead of now" in data["findings"][0]["message"]


def test_a_stamp_inside_the_clock_slack_passes(tmp_path: Path) -> None:
    inside = (NOW + dt.timedelta(seconds=gate.FUTURE_TOLERANCE_SECONDS - 30)).isoformat()
    _build(tmp_path, stamp=inside)
    assert _evaluate(tmp_path)["findings"] == []


# --------------------------------------------------------------------------
# staleness
# --------------------------------------------------------------------------


def test_a_stamp_older_than_the_newest_result_fails(tmp_path: Path) -> None:
    _build(tmp_path, stamp="2026-09-26T10:00:00Z", result_mtime=NOW - dt.timedelta(hours=1))
    data = _evaluate(tmp_path)
    assert _kinds(data) == ["stale-vs-results"]
    assert "2026-09-26-synthetic-read.md" in data["findings"][0]["message"] or (
        "stage2-results-ledger.md" in data["findings"][0]["message"]
    )


def test_a_stamp_older_than_the_newest_ledger_heading_fails(tmp_path: Path) -> None:
    _build(
        tmp_path,
        stamp="2026-09-24T09:00:00Z",
        result_mtime=dt.datetime(2026, 9, 24, 0, 0, tzinfo=dt.timezone.utc),
        ledger_heading_date="2026-09-26",
    )
    data = _evaluate(tmp_path)
    assert _kinds(data) == ["stale-vs-ledger"]
    assert "2026-09-26" in data["findings"][0]["message"]


def test_a_ledger_with_no_date_led_heading_is_not_a_finding(tmp_path: Path) -> None:
    _build(tmp_path)
    ledger = tmp_path / "docs" / "results" / "stage2-results-ledger.md"
    ledger.write_text(
        "# Stage-2 results ledger\n\n## The rules this ledger follows\n\nsynthetic\n",
        encoding="utf-8",
    )
    # Re-pin the rewritten ledger's mtime to the synthetic clock _build uses: left at the wall-clock time of the
    # write, it is newer than the pinned stamp on any day after 2026-09-26 and the gate (correctly) reports
    # stale-vs-results -- the test went red on the calendar, not on a change.
    stamp_seconds = (NOW - dt.timedelta(hours=4)).timestamp()
    os.utime(ledger, (stamp_seconds, stamp_seconds))
    data = _evaluate(tmp_path)
    assert data["newest_ledger_entry"]["heading_date"] is None
    assert _kinds(data) == []


def test_max_age_hours_is_off_by_default_and_enforced_when_asked(tmp_path: Path) -> None:
    _build(
        tmp_path,
        stamp="2026-09-20T18:00:00Z",
        result_mtime=dt.datetime(2026, 9, 19, 0, 0, tzinfo=dt.timezone.utc),
        ledger_heading_date="2026-09-19",
    )
    assert _evaluate(tmp_path)["findings"] == []
    data = _evaluate(tmp_path, max_age_hours=24)
    assert _kinds(data) == ["over-max-age"]
    assert _evaluate(tmp_path, max_age_hours=24 * 30)["findings"] == []


# --------------------------------------------------------------------------
# dating the result notes
# --------------------------------------------------------------------------


def test_without_git_the_mtimes_are_used_and_said_so(tmp_path: Path) -> None:
    _build(tmp_path)
    data = _evaluate(tmp_path, use_git=True)
    assert data["newest_result"]["source"] == "filesystem mtime"
    assert "not a git checkout" in data["newest_result"]["dating"]


@pytest.mark.skipif(shutil.which("git") is None, reason="no git on PATH")
def test_a_tracked_file_is_dated_by_its_commit_not_its_mtime(tmp_path: Path) -> None:
    """A fresh clone's mtimes are the clone time, so git dates must win."""

    _build(tmp_path, stamp="2026-09-26T17:00:00Z")
    run = lambda *args: subprocess.run(  # noqa: E731 - one-line helper
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    run("init", "-q", "-b", "main")
    run("add", "docs")
    committed = "2026-09-26T12:00:00+00:00"
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=synthetic",
            "-c",
            "user.email=synthetic@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "-m",
            "synthetic",
            f"--date={committed}",
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_COMMITTER_DATE": committed},
    )
    # the working-tree mtimes say "one hour ago", the commit says 12:00 UTC
    future = NOW - dt.timedelta(hours=1)
    for path in (tmp_path / "docs" / "results").glob("*.md"):
        os.utime(path, (future.timestamp(), future.timestamp()))

    data = _evaluate(tmp_path, use_git=True)
    assert data["newest_result"]["source"] == "git commit date"
    assert data["newest_result"]["timestamp"].startswith("2026-09-26T12:00:00")
    assert data["newest_result"]["tracked_files"] == 2
    assert data["findings"] == []  # the 17:00 stamp is newer than the commit

    # an untracked result note still counts, by its mtime
    untracked = tmp_path / "docs" / "results" / "2026-09-26-untracked-read.md"
    untracked.write_text("# later\n", encoding="utf-8")
    later = NOW - dt.timedelta(minutes=5)
    os.utime(untracked, (later.timestamp(), later.timestamp()))
    data = _evaluate(tmp_path, use_git=True)
    assert data["newest_result"]["source"] == "filesystem mtime"
    assert data["newest_result"]["file"].endswith("2026-09-26-untracked-read.md")
    assert _kinds(data) == ["stale-vs-results"]


# --------------------------------------------------------------------------
# unreadable trees and the command line
# --------------------------------------------------------------------------


def test_a_tree_with_no_results_directory_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "docs" / "handoff").mkdir(parents=True)
    with pytest.raises(gate.HandoffFreshnessCheckError):
        _evaluate(tmp_path)


def test_a_results_directory_with_no_markdown_is_an_error(tmp_path: Path) -> None:
    _build(tmp_path)
    for path in (tmp_path / "docs" / "results").glob("*.md"):
        path.unlink()
    with pytest.raises(gate.HandoffFreshnessCheckError):
        _evaluate(tmp_path)


def test_a_missing_results_ledger_is_an_error(tmp_path: Path) -> None:
    _build(tmp_path)
    (tmp_path / "docs" / "results" / "stage2-results-ledger.md").unlink()
    with pytest.raises(gate.HandoffFreshnessCheckError):
        _evaluate(tmp_path)


def test_the_three_compared_timestamps_are_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _build(tmp_path)
    assert gate.main(["--repo-root", str(tmp_path), "--no-git", "--now", NOW.isoformat()]) == 0
    out = capsys.readouterr().out
    assert "compared: stamp 2026-09-26T17:00:00+00:00" in out
    assert "newest ledger entry heading 2026-09-25" in out
    assert "handoff freshness check: PASS" in out


def test_json_output_carries_the_comparison(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _build(tmp_path, handoff_exists=False)
    assert (
        gate.main(
            ["--repo-root", str(tmp_path), "--no-git", "--now", NOW.isoformat(), "--json"]
        )
        == 1
    )
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "saea-handoff-freshness-check-v1"
    assert data["newest_result"]["file"].startswith("docs/results/")
    assert [finding["kind"] for finding in data["findings"]] == ["missing-file"]


def test_a_bad_now_is_refused(tmp_path: Path) -> None:
    _build(tmp_path)
    assert gate.main(["--repo-root", str(tmp_path), "--now", "half past four"]) == 1


def test_the_real_repository_terminates_with_a_documented_exit_code() -> None:
    """The gate runs on the real tree and returns one of its two exit codes."""

    assert gate.main(["--repo-root", str(_REPO)]) in (0, 1)
