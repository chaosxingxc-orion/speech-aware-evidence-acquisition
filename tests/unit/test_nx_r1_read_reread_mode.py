"""NX R1 read driver, RE-READ mode (--node-local-out): its refusals, model-free and without a scorer or a real data root."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DRIVER = REPO / "scripts" / "analysis" / "nx_r1_read.sh"
PY = Path("/home/chao/.venvs/speechrl/bin/python")
RECIPES = {
    1: "docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/analysis-recipe-v1.json",
    2: "docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/analysis-recipe-v1.json",
}

pytestmark = pytest.mark.skipif(not PY.exists(), reason="the WSL speechrl venv is required by the driver")


def _ids(iteration: int) -> tuple[str, str, str]:
    recipe = json.loads((REPO / RECIPES[iteration]).read_text(encoding="utf-8"))
    return recipe["arms"]["arm"]["run_id"], recipe["arms"]["arm"]["attempt_id"], recipe["read_run_id"]


def _run(data: Path, *args: str):
    env = dict(os.environ, SAEA_REPO_ROOT=str(REPO), SAEA_DATA_ROOT=str(data), SPEECHRL_DATA_DIR=str(data), PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(["bash", str(DRIVER), *args], capture_output=True, text=True, env=env, timeout=120)


def _seal(data: Path, iteration: int) -> Path:
    run, attempt, read_run = _ids(iteration)
    rundir = data / "runs" / run / attempt
    rundir.mkdir(parents=True)
    (rundir / f"{run}.run-manifest.json").write_text("{}", encoding="utf-8")
    return data / "analysis" / read_run


@pytest.mark.parametrize("name", ["node-local", "supply-variants", "offline-v4", "cross-iteration", "aa-vs-lock", "r1-c3-vs-lock",
                                  "../x", "a/b", ".hidden", "bad name"])
def test_reserved_or_unplain_subfolder_names_are_refused_before_anything_is_read(tmp_path, name):
    proc = _run(tmp_path, "--iteration", "1", "--node-local-out", name, "--dry-run")
    assert proc.returncode == 2 and "REFUSED" in proc.stdout, (proc.stdout, proc.stderr)
    assert not (tmp_path / "analysis").exists()


@pytest.mark.parametrize("flag", ["--rescore", "--skip-offline"])
def test_reread_mode_does_not_combine_with_the_full_read_flags(tmp_path, flag):
    proc = _run(tmp_path, "--iteration", "1", "--node-local-out", "node-local-v2", flag, "--dry-run")
    assert proc.returncode == 2 and "REFUSED" in proc.stdout


@pytest.mark.parametrize("iteration", [1, 2])
def test_an_iteration_without_a_sealed_run_is_refused(tmp_path, iteration):
    proc = _run(tmp_path, "--iteration", str(iteration), "--node-local-out", "node-local-v2", "--dry-run")
    assert proc.returncode == 3 and "no sealed run manifest" in proc.stdout, (proc.stdout, proc.stderr)
    assert not (tmp_path / "analysis").exists()


def test_a_non_empty_subfolder_is_refused_and_left_untouched(tmp_path):
    out = _seal(tmp_path, 1)
    target = out / "node-local-v2"
    target.mkdir(parents=True)
    (target / "keep.txt").write_text("x", encoding="utf-8")
    proc = _run(tmp_path, "--iteration", "1", "--node-local-out", "node-local-v2", "--dry-run")
    assert proc.returncode == 6 and "REFUSED" in proc.stdout, (proc.stdout, proc.stderr)
    assert sorted(p.name for p in target.iterdir()) == ["keep.txt"]
    # a plain file in the way is refused too
    (out / "afile").write_text("x", encoding="utf-8")
    assert _run(tmp_path, "--iteration", "1", "--node-local-out", "afile", "--dry-run").returncode == 6


def test_dry_run_of_a_new_subfolder_writes_nothing_and_names_only_the_node_local_step(tmp_path):
    out = _seal(tmp_path, 1)
    proc = _run(tmp_path, "--iteration", "1", "--node-local-out", "node-local-v2", "--dry-run")
    assert proc.returncode == 0, (proc.stdout, proc.stderr)
    assert "re-read mode" in proc.stdout and "ONLY the node-local step" in proc.stdout
    assert not out.exists()
