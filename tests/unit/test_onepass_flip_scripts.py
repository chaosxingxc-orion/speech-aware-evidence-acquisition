"""Refusals of the one-pass flip entry points are preserved (owner decision 270 A): 9p root, missing receipt."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
FLIGHTS = REPO / "scripts" / "flights"
pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash flip scripts run in WSL")


def _env(tmp_path: Path, **extra) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "SAEA_"))}
    env.update({"SAEA_MAIN": str(REPO), "SAEA_FLIP_DATA": str(tmp_path / "data"), "FLIP_MODE": "one-pass", **extra})
    return env


def _run(args, env):
    return subprocess.run(["bash", *args], capture_output=True, text=True, env=env, cwd=str(REPO))


@pytest.mark.parametrize("script,extra", [
    ("direct/direct_fb_flip.sh", []),
    ("tfrl/tfrl_i1_flip.sh", ["column"]),
    ("tfrl/tfrl_i1_flip.sh", ["proposers"]),
])
def test_missing_decision_receipt_is_refused_in_one_pass_mode(tmp_path, script, extra):
    (tmp_path / "data").mkdir()
    done = _run([str(FLIGHTS / script), *extra], _env(tmp_path, SAEA_ALLOW_9P_FLIP="1"))
    assert done.returncode == 6, done.stdout + done.stderr
    assert "decision receipt is not minted" in done.stdout


def test_nine_p_root_is_refused_by_every_one_pass_entry_point(tmp_path):
    env = _env(tmp_path, SAEA_MAIN="/mnt/c/not-a-repo")
    env.pop("SAEA_ALLOW_9P_FLIP", None)
    for script, extra in (("direct/direct_fb_flip.sh", []), ("tfrl/tfrl_i1_flip.sh", ["column"])):
        done = _run([str(FLIGHTS / script), *extra], env)
        assert done.returncode == 64, done.stdout + done.stderr
    done = _run([str(FLIGHTS / "batch/onepass_flip.sh"), "--readiness-dir", "r", "--prereg", "p", "--package", "k",
                 "--decision-path", "d", "--decision-id", "i", "--commit-msg", str(REPO / "README.md"), "cell"], env)
    assert done.returncode == 64, done.stdout + done.stderr


def test_onepass_flip_usage_error(tmp_path):
    done = _run([str(FLIGHTS / "batch/onepass_flip.sh")], _env(tmp_path))
    assert done.returncode == 2


def test_one_pass_branches_exist_and_default_stays_iterate():
    for script in ("direct/direct_fb_flip.sh", "tfrl/tfrl_i1_flip.sh"):
        text = (FLIGHTS / script).read_text(encoding="utf-8")
        assert '"${FLIP_MODE:-iterate}" = one-pass' in text and "onepass_flip.sh" in text
