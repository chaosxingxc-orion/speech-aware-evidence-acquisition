"""``scripts/flights/batch/resume_gate_lib.sh`` (coordinator, after the COMP-1 resume attempt 3
seal abort): the scoping ``batch_driver.sh`` sources so its resume-replay gate runs ONLY for a
cell whose experiment config declares ``resume_from``, and is never even invoked for an ordinary
cell. Exercised here by sourcing the library directly under real bash with fake ``stop``/``log``
functions and a fake gate script -- no model, server or GPU contact, and no dependency on
``batch_driver.sh``'s much heavier preconditions (a pinned flight worktree, a resident session,
the real registration gate).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "scripts" / "flights" / "batch" / "resume_gate_lib.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")

#: Prints its own invocation to STDOUT (not a side file) so resume_gate_run's own capture
#: (``out=$(bash "$gate" ... 2>&1)``, written to the report path) is exactly what a test asserts
#: on -- a fake gate that logged to a side file instead would leave the report empty, since
#: resume_gate_run never reads anything but the real gate's stdout/stderr.
FAKE_GATE = """#!/bin/bash
echo "fake gate invoked: $*"
exit "${GATE_RC:-0}"
"""


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _harness(
    tmp_path: Path, *, experiment: str, cell: str, resume_from: object | None, gate_rc: int = 0,
) -> subprocess.CompletedProcess[str]:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    cell_doc: dict[str, object] = {"cell_id": cell, "run_id": "SOME-RUN"}
    if resume_from is not None:
        cell_doc["resume_from"] = resume_from
    _write(repo / "configs" / "experiment" / f"{experiment}.json",
           json.dumps({"cells": [cell_doc]}))

    gate = tmp_path / "fake_gate.sh"
    _write(gate, FAKE_GATE)
    gate.chmod(0o755)

    report = tmp_path / "report.out"
    stop_log = tmp_path / "stop.log"
    event_log = tmp_path / "events.log"

    script = f"""
set -u
source "{LIB}"
stop() {{ echo "STOP:$1" >> "{stop_log}"; exit 9; }}
log() {{ echo "LOG:$1:$2" >> "{event_log}"; }}
export PY="{sys.executable}"
export GATE_RC="{gate_rc}"
resume_gate_run 1 "{repo}" "{data}" "{experiment}" "{cell}" "{gate}" "{report}"
echo "resume_gate_run rc=$?"
"""
    script_path = tmp_path / "run.sh"
    _write(script_path, script)
    return subprocess.run(["bash", str(script_path)], capture_output=True, text=True)


def test_resume_gate_declared_reads_resume_from(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _write(repo / "configs" / "experiment" / "exp.json", json.dumps({
        "cells": [
            {"cell_id": "resume-cell", "run_id": "R", "resume_from": {"attempt_id": "a"}},
            {"cell_id": "plain-cell", "run_id": "R2"},
        ],
    }))
    script = f"""
source "{LIB}"
export PY="{sys.executable}"
resume_gate_declared "{repo}" exp resume-cell
resume_gate_declared "{repo}" exp plain-cell
resume_gate_declared "{repo}" exp no-such-cell
resume_gate_declared "{repo}" no-such-experiment resume-cell
"""
    script_path = tmp_path / "declared.sh"
    _write(script_path, script)
    completed = subprocess.run(["bash", str(script_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == ["yes", "no", "no", "no"]


def test_non_resume_cell_never_invokes_the_gate(tmp_path: Path) -> None:
    completed = _harness(tmp_path, experiment="plain-exp", cell="plain-cell", resume_from=None)
    assert completed.returncode == 0, completed.stderr
    assert "resume_gate_run rc=0" in completed.stdout
    assert not (tmp_path / "report.out").exists()
    assert not (tmp_path / "events.log").exists()


def test_a_resume_cell_invokes_the_gate_and_passes(tmp_path: Path) -> None:
    completed = _harness(
        tmp_path, experiment="resume-exp", cell="resume-cell",
        resume_from={"attempt_id": "a", "trace_sha256": "0" * 64}, gate_rc=0,
    )
    assert completed.returncode == 0, completed.stderr
    assert "resume_gate_run rc=0" in completed.stdout
    assert "resume-replay-gate-ok" in (tmp_path / "events.log").read_text(encoding="utf-8")
    report_text = (tmp_path / "report.out").read_text(encoding="utf-8").strip()
    assert report_text == (
        "fake gate invoked: --repo-root " + str(tmp_path / "repo")
        + " --data-root " + str(tmp_path / "data")
        + " --experiment resume-exp --cell resume-cell"
    )


def test_a_resume_cell_gate_failure_stops_and_never_logs_ok(tmp_path: Path) -> None:
    completed = _harness(
        tmp_path, experiment="resume-exp", cell="resume-cell",
        resume_from={"attempt_id": "a", "trace_sha256": "0" * 64}, gate_rc=1,
    )
    assert completed.returncode == 9
    assert "resume_gate_run rc=" not in completed.stdout  # stop() exits before the caller resumes
    stop_text = (tmp_path / "stop.log").read_text(encoding="utf-8")
    assert "resume replay gate REFUSED" in stop_text
    assert not (tmp_path / "events.log").exists()  # stop() runs before the success-only log()


def test_the_batch_driver_sources_the_lib_and_scopes_prelaunch_to_resume_cells() -> None:
    text = (REPO / "scripts" / "flights" / "batch" / "batch_driver.sh").read_text(encoding="utf-8")
    assert 'source "$SP/resume_gate_lib.sh"' in text
    assert "RESUMEGATE=$SP/resume_prelaunch_gate.sh" in text
    prelaunch = text.split("prelaunch() {", 1)[1].split("\n}\n", 1)[0]
    assert 'registration_gate "$1"' in prelaunch
    assert "resume_gate_run " in prelaunch
    assert '"$RESUMEGATE"' in prelaunch


def test_the_comp1_resume_chain_calls_the_gate_before_the_driver() -> None:
    text = (REPO / "scripts" / "flights" / "comp1" / "batch_chain_comp1_resume.sh").read_text(
        encoding="utf-8"
    )
    gate_call = text.index("resume_prelaunch_gate.sh")
    driver_call = text.index("bash $SP/batch_driver.sh")
    assert gate_call < driver_call
    assert "GATERC -ne 0" in text and "exit 5" in text
