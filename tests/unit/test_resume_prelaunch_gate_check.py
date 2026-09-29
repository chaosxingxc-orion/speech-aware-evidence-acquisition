"""The resume prelaunch gate (coordinator, after the COMP-1 resume attempt 3 seal abort):
``scripts/checks/resume_prelaunch_gate_check.py`` reads a resume cell's ``resume_from``, verifies
every predecessor trace hashes to its declared identity, and runs
``scripts/analysis/replay_seal_consistency.py`` (the checker) over every predecessor under the
CURRENT code, refusing on any failing row or any row sealed twice.

The checker itself is exercised elsewhere (it composes real configs and replays a real trace); here
the checker is a FAKE script controlled by an environment variable, so these tests exercise only
this gate's own logic: reading ``resume_from`` (a single object today, a list for tomorrow),
verifying trace identity, building the checker's ``--attempt`` arguments, and deciding pass/refuse
from the checker's JSON report. Zero model, tokenizer, encoder, scorer, network and GPU contacts.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_CHECKS = _REPO / "scripts" / "checks"
if str(_CHECKS) not in sys.path:
    sys.path.insert(0, str(_CHECKS))

import resume_prelaunch_gate_check as gate  # noqa: E402

EXPERIMENT = "slurp-native-stage3-resumegate-fold-a-v1"
CELL = "slurp-native-stage3-resumegate-fold-a-v1"
RUN = "SAEA-SLURP-STAGE3-RESUMEGATE-FOLD-A-V1"
ATTEMPT_A = "attempt-slurp-native-stage3-resumegate-fold-a-generation-v1"
ATTEMPT_B = "attempt-slurp-native-stage3-resumegate-fold-a-generation-v1-second"

FAKE_CHECKER_SOURCE = """
import argparse, json, os, sys
p = argparse.ArgumentParser()
p.add_argument("--experiment", required=True)
p.add_argument("--run-id", required=True)
p.add_argument("--attempt", action="append", required=True)
p.add_argument("--repo-root", required=True)
p.add_argument("--data-root", required=True)
args = p.parse_args()
log = os.environ.get("FAKE_CHECKER_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(vars(args)) + "\\n")
canned = json.loads(open(os.environ["FAKE_CHECKER_CANNED"], encoding="utf-8").read())
sys.stdout.write(json.dumps(canned["report"]))
sys.exit(canned.get("exit_code", 0))
"""


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_experiment(repo: Path, *, resume_from: object | None, run_id: str = RUN,
                       experiment: str = EXPERIMENT, cell_id: str = CELL) -> None:
    cell: dict[str, object] = {"cell_id": cell_id, "run_id": run_id}
    if resume_from is not None:
        cell["resume_from"] = resume_from
    _write_json(repo / "configs" / "experiment" / f"{experiment}.json", {"cells": [cell]})


def _write_trace(data: Path, run_id: str, attempt_id: str, content: bytes) -> str:
    path = data / "runs" / run_id / attempt_id / f"{run_id}.trace.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return hashlib.sha256(content).hexdigest()


def _write_fake_checker(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FAKE_CHECKER_SOURCE, encoding="utf-8")


def _canned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, report: dict, exit_code: int = 0,
            log: bool = False) -> Path:
    canned_path = tmp_path / "canned.json"
    _write_json(canned_path, {"report": report, "exit_code": exit_code})
    monkeypatch.setenv("FAKE_CHECKER_CANNED", str(canned_path))
    if log:
        monkeypatch.setenv("FAKE_CHECKER_LOG", str(tmp_path / "checker-invocations.jsonl"))
    else:
        monkeypatch.delenv("FAKE_CHECKER_LOG", raising=False)
    return canned_path


@pytest.fixture
def world(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    checker = tmp_path / "fake_checker.py"
    _write_fake_checker(checker)
    return repo, data, checker


def _run(repo: Path, data: Path, checker: Path, *, experiment: str = EXPERIMENT,
          cell: str = CELL) -> tuple[int, str, str]:
    import contextlib
    import io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = gate.main([
            "--repo-root", str(repo), "--data-root", str(data),
            "--experiment", experiment, "--cell", cell,
            "--checker", str(checker), "--python", sys.executable,
        ])
    return code, out.getvalue(), err.getvalue()


def test_a_cell_without_resume_from_is_a_no_op_pass(world, monkeypatch) -> None:
    repo, data, checker = world
    _write_experiment(repo, resume_from=None)
    code, out, _ = _run(repo, data, checker)
    assert code == 0
    assert json.loads(out)["schema"] == gate.SCHEMA_NOT_APPLICABLE
    assert not (data / "checker-invocations.jsonl").exists()


def test_a_clean_replay_passes_and_prints_a_proof_receipt(world, monkeypatch) -> None:
    repo, data, checker = world
    digest = _write_trace(data, RUN, ATTEMPT_A, b'{"record_id": "x"}\n')
    _write_experiment(repo, resume_from={"attempt_id": ATTEMPT_A, "trace_sha256": digest})
    _canned(data, monkeypatch, report={
        "rows_checked_total": 4, "rows_failing_total": 0,
        "attempts": [{"attempt_id": ATTEMPT_A, "failures_by_check": {}}],
        "union": {"sealed_twice": 0},
    }, exit_code=0, log=True)
    code, out, err = _run(repo, data, checker)
    assert code == 0, err
    receipt = json.loads(out)
    assert receipt["schema"] == gate.SCHEMA_PROOF
    assert receipt["run_id"] == RUN
    assert receipt["predecessor_attempts"] == [ATTEMPT_A]
    assert receipt["rows_checked"] == 4
    assert receipt["rows_failing"] == 0
    assert receipt["sealed_twice"] == 0
    assert receipt["checker_sha256"] == hashlib.sha256(checker.read_bytes()).hexdigest()
    for field in gate.RESUME_REPLAY_PROOF_FIELDS:
        assert field in receipt


def test_one_failing_row_refuses_and_names_the_check(world, monkeypatch) -> None:
    repo, data, checker = world
    digest = _write_trace(data, RUN, ATTEMPT_A, b'{"record_id": "x"}\n')
    _write_experiment(repo, resume_from={"attempt_id": ATTEMPT_A, "trace_sha256": digest})
    _canned(data, monkeypatch, report={
        "rows_checked_total": 4, "rows_failing_total": 1,
        "attempts": [{"attempt_id": ATTEMPT_A, "failures_by_check": {"I7.text_hash": 1}}],
        "union": {"sealed_twice": 0},
    }, exit_code=1)
    code, _out, err = _run(repo, data, checker)
    assert code == 1
    assert "1 row(s) failing" in err
    assert "I7.text_hash" in err


def test_two_predecessors_overlapping_refuses_and_both_are_passed_to_the_checker(
    world, monkeypatch
) -> None:
    repo, data, checker = world
    digest_a = _write_trace(data, RUN, ATTEMPT_A, b'{"record_id": "a"}\n')
    digest_b = _write_trace(data, RUN, ATTEMPT_B, b'{"record_id": "b"}\n')
    _write_experiment(repo, resume_from=[
        {"attempt_id": ATTEMPT_A, "trace_sha256": digest_a},
        {"attempt_id": ATTEMPT_B, "trace_sha256": digest_b},
    ])
    _canned(data, monkeypatch, report={
        "rows_checked_total": 8, "rows_failing_total": 0,
        "attempts": [
            {"attempt_id": ATTEMPT_A, "failures_by_check": {}},
            {"attempt_id": ATTEMPT_B, "failures_by_check": {}},
        ],
        "union": {"sealed_twice": 2},
    }, exit_code=1, log=True)
    code, _out, err = _run(repo, data, checker)
    assert code == 1
    assert "2 row(s) sealed twice" in err
    invocations = (data / "checker-invocations.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(invocations) == 1
    call = json.loads(invocations[0])
    assert call["attempt"] == [ATTEMPT_A, ATTEMPT_B]


def test_a_moved_predecessor_trace_refuses_before_the_checker_ever_runs(world, monkeypatch) -> None:
    repo, data, checker = world
    _write_trace(data, RUN, ATTEMPT_A, b'{"record_id": "x"}\n')
    _write_experiment(repo, resume_from={"attempt_id": ATTEMPT_A, "trace_sha256": "0" * 64})
    _canned(data, monkeypatch, report={"rows_checked_total": 0, "rows_failing_total": 0,
                                        "attempts": [], "union": {"sealed_twice": 0}}, log=True)
    code, _out, err = _run(repo, data, checker)
    assert code == 2
    assert "not the declared" in err
    assert not (data / "checker-invocations.jsonl").exists()


def test_a_malformed_resume_from_is_refused(world) -> None:
    repo, data, checker = world
    _write_experiment(repo, resume_from={"attempt_id": ATTEMPT_A})  # trace_sha256 missing
    code, _out, err = _run(repo, data, checker)
    assert code == 2
    assert "resume_from" in err


def test_an_unknown_cell_is_refused(world) -> None:
    repo, data, checker = world
    _write_experiment(repo, resume_from=None)
    code, _out, err = _run(repo, data, checker, cell="no-such-cell")
    assert code == 2
    assert "no-such-cell" in err
