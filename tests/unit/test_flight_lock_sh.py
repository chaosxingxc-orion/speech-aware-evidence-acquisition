"""scripts/lib/flight_lock.sh: the BASH acquire/release/stale-detection side
of the E0-prime flight lock (2026-08-16 flight-protection fix). Exercised by
shelling out to bash and sourcing the library directly -- this is shell
logic, not importable Python, and the shell IS the real contract
run_arm_sequence.sh depends on.

Skipped outright (not merely soft-failed) on a platform with no usable
``bash`` -- this suite runs the ML stack under WSL2 per CLAUDE.md, where
bash is always present; a bare-Windows invocation of this same test file
must not report a false failure over a missing interpreter."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

LIB = REPO_ROOT / "scripts" / "lib" / "flight_lock.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="no bash interpreter on this platform")


def _run_bash(script: str, *, data_root: Path, timeout: float = 30.0) -> subprocess.CompletedProcess:
    assert LIB.is_file(), f"missing {LIB}"
    preamble = f'set -uo pipefail\n. "{LIB}"\nexport SPEECHRL_DATA_DIR="{data_root}"\n'
    return subprocess.run(
        ["bash", "-c", preamble + script],
        cwd=data_root, capture_output=True, text=True, timeout=timeout,
    )


def _lock_path(data_root: Path) -> Path:
    return data_root / "locks" / "flight.lock"


def test_flight_lock_path_matches_the_python_reader_convention(tmp_path):
    result = _run_bash('flight_lock_path', data_root=tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(_lock_path(tmp_path))


def test_flight_lock_acquire_creates_a_well_shaped_lock_and_release_removes_it(tmp_path):
    result = _run_bash(
        'flight_lock_acquire \'["arm-a","arm-b"]\' && echo ACQUIRED && '
        'cat "$(flight_lock_path)"',
        data_root=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "ACQUIRED" in result.stdout
    lock_line = [line for line in result.stdout.splitlines() if line.startswith("{")][0]
    document = json.loads(lock_line)
    assert document["run_ids"] == ["arm-a", "arm-b"]
    assert isinstance(document["pid"], int)
    assert document["started_at"]
    assert document["study_head"]
    # The EXIT trap fires when the bash process that acquired the lock ends
    # -- the file must be gone from the Python side's point of view too.
    assert not _lock_path(tmp_path).exists()


def test_flight_lock_acquire_refuses_a_second_call_while_the_first_lock_is_live(tmp_path):
    # Both acquires happen inside ONE bash process, so the lock's recorded
    # pid ($$) is genuinely alive for the whole script -- a live-lock refusal
    # without needing to orchestrate two real overlapping processes.
    result = _run_bash(
        'flight_lock_acquire \'["first-flight"]\' && echo ACQUIRE1_OK\n'
        'if flight_lock_acquire \'["second-flight"]\'; then\n'
        '  echo ACQUIRE2_UNEXPECTEDLY_OK\n'
        'else\n'
        '  echo ACQUIRE2_REFUSED\n'
        'fi\n'
        'cat "$(flight_lock_path)"\n',
        data_root=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "ACQUIRE1_OK" in result.stdout
    assert "ACQUIRE2_REFUSED" in result.stdout
    assert "ACQUIRE2_UNEXPECTEDLY_OK" not in result.stdout
    assert "REFUSED" in result.stderr
    lock_line = [line for line in result.stdout.splitlines() if line.startswith("{")][0]
    document = json.loads(lock_line)
    # The refused second call must never have touched the first's lock.
    assert document["run_ids"] == ["first-flight"]


def test_flight_lock_acquire_replaces_a_stale_lock_with_a_loud_warning(tmp_path):
    # A lock file hand-written with a PID guaranteed dead (spawn a no-op
    # child, then `wait` for it so it is reaped before we ever read its pid)
    # simulates an operator's previous flight whose process is long gone.
    script = (
        'mkdir -p "$(dirname "$(flight_lock_path)")"\n'
        '( : ) & DEAD_PID=$!\n'
        'wait "$DEAD_PID"\n'
        'printf \'{"run_ids": ["stale-arm"], "pid": %s, "started_at": '
        '"2020-01-01T00:00:00Z", "study_head": "deadbeef"}\\n\' "$DEAD_PID" '
        '> "$(flight_lock_path)"\n'
        'if flight_lock_is_stale "$(flight_lock_path)"; then\n'
        '  echo STALE_DETECTED\n'
        'else\n'
        '  echo STALE_NOT_DETECTED\n'
        'fi\n'
        'if flight_lock_acquire \'["fresh-arm"]\'; then\n'
        '  echo ACQUIRE_AFTER_STALE_OK\n'
        'else\n'
        '  echo ACQUIRE_AFTER_STALE_FAILED\n'
        'fi\n'
        'cat "$(flight_lock_path)"\n'
    )
    result = _run_bash(script, data_root=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "STALE_DETECTED" in result.stdout
    assert "ACQUIRE_AFTER_STALE_OK" in result.stdout
    assert "WARNING" in result.stderr
    assert "stale flight lock" in result.stderr
    lock_line = [line for line in result.stdout.splitlines() if line.startswith("{")][0]
    document = json.loads(lock_line)
    # The stale lock was REPLACED, not merely left in place.
    assert document["run_ids"] == ["fresh-arm"]


def test_flight_lock_is_stale_reports_false_for_a_live_pid(tmp_path):
    script = (
        'mkdir -p "$(dirname "$(flight_lock_path)")"\n'
        'printf \'{"run_ids": ["x"], "pid": %s, "started_at": "t", '
        '"study_head": "h"}\\n\' "$$" > "$(flight_lock_path)"\n'
        'if flight_lock_is_stale "$(flight_lock_path)"; then\n'
        '  echo STALE\n'
        'else\n'
        '  echo LIVE\n'
        'fi\n'
    )
    result = _run_bash(script, data_root=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "LIVE" in result.stdout
    assert "STALE" not in result.stdout
