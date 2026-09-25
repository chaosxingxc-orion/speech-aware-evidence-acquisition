"""Synthetic, read-only closure checks for the F10 successor chain."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts/flights/batch/batch_chain_f10.sh"
_READ_ID = "SAEA-SLURP-STAGE3-VAR2-RECOVERY-SUPPLY-READ-V1"
_COMMIT = "b" * 40
_CONFIG = "a" * 64
_SCORES = "c" * 64


def _write(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def closed_recovery(tmp_path):
    home, data = tmp_path / "home", tmp_path / "data"
    home.mkdir()
    data.mkdir()
    full = {
        "experiment": "full-experiment", "cell_id": "full-cell",
        "run_id": "FULL-RUN", "fit_run_id": "FULL-FIT",
        "attempt_id": "full-attempt", "composed_config_hash": _CONFIG, "rows": 625,
    }
    smoke = {
        "experiment": "smoke-experiment", "cell_id": "smoke-cell",
        "run_id": "SMOKE-RUN", "fit_run_id": "SMOKE-FIT",
        "attempt_id": "smoke-attempt", "composed_config_hash": "d" * 64, "rows": 4,
    }
    protocol = tmp_path / "protocol.json"
    _write(protocol, {
        "schema": "saea-var2-recovery-protocol-v1",
        "cells": {"full": full, "smoke": smoke},
    })
    _write(home / "batch-queue.json", [{
        "short": "var2-recovery", "experiment": full["experiment"],
        "cell": full["cell_id"], "run_id": full["run_id"],
        "fit_run_id": full["fit_run_id"], "gen_attempt_id": full["attempt_id"],
        "smoke_experiment": smoke["experiment"], "smoke_cell": smoke["cell_id"],
        "smoke_run_id": smoke["run_id"], "smoke_attempt_id": smoke["attempt_id"],
        "expected_rows": 625, "ceiling_per_row": 17,
    }])
    events = []
    for cell, event, state in (
        (smoke, "smoke-inspect", "OPENED"),
        (full, "arm-inspect", "FINALIZED"),
    ):
        _write(
            data / "attempts" / cell["run_id"] / (cell["attempt_id"] + ".json"),
            {"state": state},
        )
        manifest = (
            data / "runs" / cell["run_id"] / cell["attempt_id"]
            / (cell["run_id"] + ".run-manifest.json")
        )
        _write(manifest, {
            "status": "COMPLETED", "study_commit": _COMMIT,
            "study_repo_dirt": False,
            "config": {"config_hash": cell["composed_config_hash"]},
            "scores": {"sha256": _SCORES},
        })
        events.append({
            "event": event,
            "detail": {
                "pass": True, "run_id": cell["run_id"],
                "attempt_id": cell["attempt_id"], "attempt_state": state,
                "manifest_status": "COMPLETED",
                "sha256_run-manifest": _sha(manifest),
                "rows": cell["rows"], "distinct": cell["rows"],
            },
        })
    events += [
        {"event": "step-done", "detail": {"short": "var2-recovery"}},
        {"event": "driver-done", "detail": {"steps": 1}},
    ]
    (home / "batch-status.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    (home / "batch-done").write_text("done", encoding="utf-8")
    summary_dir = data / "analysis" / _READ_ID
    summary_dir.mkdir(parents=True)
    arms = {}
    for arm in ("exk10", "exk30", "exdiv", "plan"):
        score = summary_dir / f"arm-{arm}-slurp-slu-official-train-scores.json"
        _write(score, {"synthetic": arm})
        arms[arm] = {"rows": 625, "scores_sha256": _sha(score)}
    manifest = (
        data / "runs" / full["run_id"] / full["attempt_id"]
        / (full["run_id"] + ".run-manifest.json")
    )
    summary = {
        "schema": "saea-stage3-supply-variant-first-visit-v1",
        "stage": "score", "scorer_id": "slurp-slu-official-train",
        "arm_order": ["exk10", "exk30", "exdiv", "plan"],
        "arms": arms, "sealed_delivered_rows": 625,
        "contacts": {"scorer": 4},
        "sealed_delivered_scores_sha256": _SCORES,
        "source": {
            "run_id": full["run_id"], "attempt_id": full["attempt_id"],
            "config_hash": _CONFIG, "manifest_path": str(manifest),
            "manifest_sha256": _sha(manifest),
            "sealed_scores_sha256": _SCORES,
        },
    }
    summary_path = summary_dir / "score-summary.json"
    _write(summary_path, summary)
    env = os.environ.copy()
    env.update({
        "F10_TEST_HOME": str(home), "F10_TEST_DATA": str(data),
        "F10_TEST_VAR2_PROTOCOL": str(protocol),
        "F10_TEST_VAR2_COMMIT": _COMMIT,
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return home, data, summary_path, env


def _check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_SCRIPT), "--check-boundary"],
        env=env, capture_output=True, text=True, check=False,
    )


def test_completed_opened_smoke_and_finalized_full_are_ready(closed_recovery):
    _, _, _, env = closed_recovery
    result = _check(env)
    assert result.returncode == 0, result.stderr
    assert "READY" in result.stdout


def test_batch_done_without_derived_scores_is_pending(closed_recovery):
    _, _, summary, env = closed_recovery
    summary.unlink()
    result = _check(env)
    assert result.returncode == 10
    assert "WAIT" in result.stdout


def test_stop_marker_refuses(closed_recovery):
    home, _, _, env = closed_recovery
    (home / "batch-STOP").write_text("failure", encoding="utf-8")
    result = _check(env)
    assert result.returncode == 20
    assert "STOP" in result.stderr


@pytest.mark.parametrize("mutation", ["aborted_smoke", "smoke_manifest", "score_hash"])
def test_broken_custody_refuses(closed_recovery, mutation):
    _, data, summary, env = closed_recovery
    if mutation == "aborted_smoke":
        _write(data / "attempts/SMOKE-RUN/smoke-attempt.json", {"state": "ABORTED"})
    elif mutation == "smoke_manifest":
        path = data / "runs/SMOKE-RUN/smoke-attempt/SMOKE-RUN.run-manifest.json"
        _write(path, {"status": "COMPLETED", "study_commit": "0" * 40})
    else:
        document = json.loads(summary.read_text(encoding="utf-8"))
        document["source"]["manifest_sha256"] = "0" * 64
        _write(summary, document)
    result = _check(env)
    assert result.returncode == 20
    assert "REFUSED" in result.stderr
