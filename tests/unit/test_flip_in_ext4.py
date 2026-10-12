"""Model-free tests for the ext4 flip wrapper and the SAEA_MAIN override of the flip scripts."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WRAPPER = REPO / "scripts" / "flights" / "batch" / "flip_in_ext4.sh"
MASTER_LITERAL = "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash flip scripts run in WSL")


def _git(cwd: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=str(cwd), capture_output=True, text=True, check=True, env=env,
    )
    return done.stdout.strip()


def _make_master(tmp_path: Path) -> Path:
    master = tmp_path / "master"
    master.mkdir()
    _git(master, "init", "-q", "-b", "master")
    flip = master / "scripts" / "fake_flip.sh"
    flip.parent.mkdir()
    flip.write_text(
        "#!/bin/bash\n"
        'cd "$SAEA_MAIN" || exit 1\n'
        'echo "main=$SAEA_MAIN" > flip_ran.txt\n'
        'git add flip_ran.txt && git -c user.name=t -c user.email=t@t commit -q -m flip\n'
        'git rev-parse HEAD > "$FAKE_COMMIT_FILE"\n',
        encoding="utf-8", newline="\n",
    )
    (master / "scripts" / "bad_flip.sh").write_text("#!/bin/bash\nexit 9\n", encoding="utf-8", newline="\n")
    _git(master, "add", "-A")
    _git(master, "commit", "-q", "-m", "init")
    return master


def _run(master: Path, wt: Path, script: str, tmp_path: Path, extra_env=None):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(SAEA_FLIP_MASTER=str(master), SAEA_FLIP_WORKTREE=str(wt), SAEA_FLIP_SKIP_ALIVE_CHECK="1",
               FAKE_COMMIT_FILE=str(tmp_path / "x-flight-commit.txt"))
    env.update(extra_env or {})
    return subprocess.run(["bash", str(WRAPPER), script], capture_output=True, text=True, env=env)


def test_fast_forwards_master_and_runs_in_worktree(tmp_path):
    master, wt = _make_master(tmp_path), tmp_path / "wt"
    before = _git(master, "rev-parse", "HEAD")
    done = _run(master, wt, "scripts/fake_flip.sh", tmp_path)
    assert done.returncode == 0, done.stdout + done.stderr
    after = _git(master, "rev-parse", "HEAD")
    assert after != before and _git(master, "rev-parse", "HEAD~1") == before
    assert (master / "flip_ran.txt").read_text().strip() == f"main={wt}"
    assert (tmp_path / "x-flight-commit.txt").read_text().strip() == after
    assert "step=fast_forward" in done.stdout
    assert not [b for b in _git(master, "branch", "--list", "flip/*").splitlines() if b.strip()]
    # a second run reuses the worktree (fast-forwarded to the new master HEAD)
    assert _run(master, wt, "scripts/fake_flip.sh", tmp_path).returncode == 0


def test_refuses_dirty_master_and_failed_flip_leaves_master_alone(tmp_path):
    master, wt = _make_master(tmp_path), tmp_path / "wt"
    head = _git(master, "rev-parse", "HEAD")
    (master / "scripts" / "fake_flip.sh").write_text("#!/bin/bash\n# dirty\n", encoding="utf-8")
    assert _run(master, wt, "scripts/fake_flip.sh", tmp_path).returncode == 4
    _git(master, "checkout", "--", "scripts/fake_flip.sh")
    assert _run(master, wt, "scripts/bad_flip.sh", tmp_path).returncode == 6
    assert _git(master, "rev-parse", "HEAD") == head


def test_refuses_when_master_moves_during_flip(tmp_path):
    master, wt = _make_master(tmp_path), tmp_path / "wt"
    (master / "scripts" / "moving_flip.sh").write_text(
        "#!/bin/bash\ncd \"$SAEA_MAIN\"; git -c user.name=t -c user.email=t@t commit -q --allow-empty -m wt\n"
        f"git -C {master} -c user.name=t -c user.email=t@t commit -q --allow-empty -m other\n",
        encoding="utf-8", newline="\n",
    )
    _git(master, "add", "-A")
    _git(master, "commit", "-q", "-m", "add moving")
    done = _run(master, wt, "scripts/moving_flip.sh", tmp_path)
    assert done.returncode == 7, done.stdout + done.stderr


@pytest.mark.parametrize("rel", [
    "scripts/flights/batch/repin_cell_generic.sh",
    "scripts/flights/batch/repin_loop_generic.sh",
    "scripts/flights/direct/direct_fb_flip.sh",
    "scripts/flights/tfrl/tfrl_i1_flip.sh",
])
def test_saea_main_override_is_honoured(rel, tmp_path):
    # Each script cds into $MAIN first and exits 1 when it does not exist: proves the override is read.
    env = {**os.environ, "SAEA_MAIN": str(tmp_path / "nonexistent-main")}
    done = subprocess.run(["bash", str(REPO / rel), "column", "x", "x", "x", "x"], capture_output=True, text=True, env=env)
    assert done.returncode == 1, done.stdout + done.stderr


def test_no_raw_master_path_left_in_flip_scripts():
    offenders = []
    for path in (REPO / "scripts" / "flights").rglob("*.sh"):
        if path.name == "flip_in_ext4.sh" or ("flip" not in path.name and "repin" not in path.name):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if MASTER_LITERAL in line and "SAEA_MAIN:-" + MASTER_LITERAL not in line:
                offenders.append(f"{path.relative_to(REPO)}:{number}")
    assert not offenders, offenders


@pytest.mark.parametrize("rel", [
    "scripts/flights/batch/repin_cell_generic.sh",
    "scripts/flights/batch/repin_loop_generic.sh",
    "scripts/flights/direct/direct_fb_flip.sh",
    "scripts/flights/tfrl/tfrl_i1_flip.sh",
])
def test_flip_scripts_refuse_a_9p_repo_root(rel):
    env = {k: v for k, v in os.environ.items() if k != "SAEA_ALLOW_9P_FLIP"}
    env["SAEA_MAIN"] = "/mnt/nonexistent-9p-main"
    done = subprocess.run(["bash", str(REPO / rel), "column", "x", "x", "x", "x"], capture_output=True, text=True, env=env)
    assert done.returncode == 64, done.stdout + done.stderr
    assert "9p" in done.stdout and len(done.stdout.strip().splitlines()) == 1
    env["SAEA_ALLOW_9P_FLIP"] = "1"  # escape hatch: gets past the guard (then fails on the missing directory)
    done = subprocess.run(["bash", str(REPO / rel), "column", "x", "x", "x", "x"], capture_output=True, text=True, env=env)
    assert done.returncode != 64


def test_wrapper_refuses_a_9p_worktree(tmp_path):
    master = _make_master(tmp_path)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "SAEA_ALLOW_9P_FLIP"}
    env.update(SAEA_FLIP_MASTER=str(master), SAEA_FLIP_WORKTREE="/mnt/nonexistent-wt", SAEA_FLIP_SKIP_ALIVE_CHECK="1")
    done = subprocess.run(["bash", str(WRAPPER), "scripts/fake_flip.sh"], capture_output=True, text=True, env=env)
    assert done.returncode == 64, done.stdout + done.stderr


def test_repin_cli_refuses_a_9p_repo_root(monkeypatch, capsys):
    from speech_aware_evidence_acquisition.core.flight import repin

    monkeypatch.delenv("SAEA_ALLOW_9P_FLIP", raising=False)
    assert repin.nine_p_refusal(Path("/mnt/d/x")).startswith("refusing: repo root /mnt/d/x")
    assert repin.nine_p_refusal(Path("/tmp")) is None
    monkeypatch.setenv("SAEA_ALLOW_9P_FLIP", "1")
    assert repin.nine_p_refusal(Path("/mnt/d/x")) is None
    monkeypatch.delenv("SAEA_ALLOW_9P_FLIP")
    argv = ["--repo-root", "/mnt/d/x", "--data-root", "/tmp", "--runtime-root", "/tmp", "--lock-path", "/tmp/l",
            "--readiness-dir", "r", "--preregistration", "p", "--experiment", "e", "--cell", "c"]
    assert repin.main(argv) == 64
    assert "9p" in capsys.readouterr().err
