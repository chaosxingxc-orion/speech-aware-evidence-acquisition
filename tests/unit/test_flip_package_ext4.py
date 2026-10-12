"""Model-free tests for the generic one-session package flip wrapper (flip_package_ext4.sh)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "scripts" / "flights" / "batch"
WRAPPER = BATCH / "flip_package_ext4.sh"
PKG = "docs/readiness/pkg-a"

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="bash flip scripts run in WSL")

_IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _clean_env() -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(_IDENT)
    return env


def _git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True, env=_clean_env())
    return done.stdout.strip()


def _make_master(tmp_path: Path, flip_body: str | None = None) -> Path:
    master = tmp_path / "master"
    (master / "scripts" / "flights" / "batch").mkdir(parents=True)
    (master / PKG).mkdir(parents=True)
    _git(master, "init", "-q", "-b", "master")
    shutil.copy(WRAPPER, master / "scripts" / "flights" / "batch" / "flip_package_ext4.sh")
    # decision 274: the inner pass sources the one data-root authority from the worktree.
    (master / "scripts" / "lib").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "lib" / "data_root.sh", master / "scripts" / "lib" / "data_root.sh")
    # commits on the first pass only; stable on the second (flip_ran.txt exists)
    flip = flip_body or (
        "#!/bin/bash\n"
        'cd "$SAEA_MAIN" || exit 1\n'
        'echo "kv=$FAKE_KV args=$*" > kv.txt\n'
        '[ -f flip_ran.txt ] || { echo ran > flip_ran.txt; git add flip_ran.txt kv.txt; git commit -q -m flip; }\n'
        'git rev-parse HEAD > "$FAKE_COMMIT_FILE"\n'
    )
    (master / "scripts" / "fake_flip.sh").write_text(flip, encoding="utf-8", newline="\n")
    (master / PKG / "pins.txt").write_text("v0\n", encoding="utf-8", newline="\n")
    (master / "kv.txt").write_text("seed\n", encoding="utf-8", newline="\n")
    _git(master, "add", "-A")
    _git(master, "commit", "-q", "-m", "init")
    return master


def _fakes(tmp_path: Path) -> dict:
    refresh = tmp_path / "refresh.sh"
    refresh.write_text('#!/bin/bash\necho "pins $*" >> "$PWD/%s/pins.txt"\n' % PKG, encoding="utf-8", newline="\n")
    regcheck = tmp_path / "regcheck.sh"
    regcheck.write_text('#!/bin/bash\necho "flight registration check: PASS $2"\necho "  [ok] fake"\n',
                        encoding="utf-8", newline="\n")
    msg = tmp_path / "msg.txt"
    msg.write_text("pins refresh\n", encoding="utf-8", newline="\n")
    return {"SAEA_REFRESH_PINS": f"bash {refresh}", "SAEA_REGCHECK": f"bash {regcheck}", "msg": msg}


def _run(master: Path, tmp_path: Path, extra=(), env_extra=None, skip_alive=True, cells="cell-1,cell-2"):
    fakes = _fakes(tmp_path)
    env = _clean_env()
    env.update(
        SAEA_FLIP_MASTER=str(master), SAEA_FLIP_WORKTREE=str(tmp_path / "wt"), SAEA_FLIGHT_COMMIT_DIR=str(tmp_path),
        FAKE_COMMIT_FILE=str(tmp_path / "x-flight-commit.txt"), SAEA_REFRESH_PINS=fakes["SAEA_REFRESH_PINS"],
        SAEA_REGCHECK=fakes["SAEA_REGCHECK"],
    )
    env.pop("SAEA_ALLOW_9P_FLIP", None)
    (tmp_path / "data").mkdir(exist_ok=True)
    env["SAEA_DATA_ROOT"] = str(tmp_path / "data")  # hermetic: never the host data root
    if skip_alive:
        env["SAEA_FLIP_SKIP_ALIVE_CHECK"] = "1"
    else:
        env.pop("SAEA_FLIP_SKIP_ALIVE_CHECK", None)
    env.update(env_extra or {})
    log = tmp_path / "out.log"
    cmd = ["bash", str(WRAPPER), "--flip", "scripts/fake_flip.sh arg1", "--package", PKG, "--cells", cells,
           "--pins-commit-msg", str(fakes["msg"]), "--log", str(log), *extra]
    done = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return done, log


def test_full_sequence_milestones_pins_gates_and_single_fast_forward(tmp_path):
    master = _make_master(tmp_path)
    before = _git(master, "rev-parse", "HEAD")
    done, log = _run(master, tmp_path, extra=["--", "FAKE_KV=hello"])
    assert done.returncode == 0, done.stdout + done.stderr
    text = log.read_text()
    assert re.search(r"^== flip pass 1 at [0-9a-f]{40} \d\d:\d\d:\d\dZ$", text, re.M)
    assert re.search(r"^   rc=0 HEAD [0-9a-f]{40} dirty=0$", text, re.M)
    assert "== refresh plan pins" in text and "   refresh rc=0" in text
    assert re.search(r"^   pins committed [0-9a-f]{7,}$", text, re.M)
    assert "== gate" in text
    assert "flight registration check: PASS cell-1" in text and "flight registration check: PASS cell-2" in text
    after = _git(master, "rev-parse", "HEAD")
    assert re.search(rf"^flight commit file: {after} HEAD {after}", text, re.M)
    assert re.search(r"^FLIP_CHAIN_DONE \d{4}-\d\d-\d\dT", text, re.M)
    assert text.count("== refresh plan pins") == 1 and text.count("== gate") == 1
    assert "== flip pass 2 at" in text
    # master moved by exactly the flip commit and the pins commit, fast-forwarded in one go
    assert _git(master, "rev-list", "--count", f"{before}..{after}") == "2"
    assert _git(master, "log", "-1", "--format=%s", "HEAD") == "pins refresh"
    assert "--package " + PKG in (master / PKG / "pins.txt").read_text()
    assert (master / "kv.txt").read_text().strip() == "kv=hello args=arg1"
    assert (tmp_path / "x-flight-commit.txt").read_text().strip() == after
    assert not [b for b in _git(master, "branch", "--list", "flip/*").splitlines() if b.strip()]


def test_default_log_name_is_package_basename():
    assert '/home/chao/$(basename "$PKG")-flip.out' in WRAPPER.read_text()


def test_non_convergence_aborts_and_leaves_master_alone(tmp_path):
    body = ('#!/bin/bash\ncd "$SAEA_MAIN" || exit 1\ndate +%N >> churn.txt\ngit add churn.txt\n'
            'git commit -q -m churn\n')
    master = _make_master(tmp_path, flip_body=body)
    head = _git(master, "rev-parse", "HEAD")
    done, log = _run(master, tmp_path)
    assert done.returncode == 6, done.stdout + done.stderr
    text = log.read_text()
    assert "FLIP DID NOT CONVERGE" in text and "FLIP_CHAIN_DONE" not in text
    assert text.count("== flip pass") == 6
    assert _git(master, "rev-parse", "HEAD") == head


def test_refuses_dirty_master_and_live_driver(tmp_path):
    master = _make_master(tmp_path)
    head = _git(master, "rev-parse", "HEAD")
    (master / "kv.txt").write_text("dirty\n", encoding="utf-8")
    done, log = _run(master, tmp_path)
    assert done.returncode == 4, done.stdout + done.stderr
    assert "FLIP_CHAIN_DONE" not in log.read_text()
    _git(master, "checkout", "--", "kv.txt")
    driver = subprocess.Popen(["bash", "-c", "sleep 30 # batch_driver.sh"])
    try:
        done, log = _run(master, tmp_path, skip_alive=False)
        assert done.returncode == 3, done.stdout + done.stderr
        assert "FLIP_CHAIN_DONE" not in log.read_text()
    finally:
        driver.kill()
        driver.wait()
    assert _git(master, "rev-parse", "HEAD") == head


def test_usage_errors(tmp_path):
    master = _make_master(tmp_path)
    done, _ = _run(master, tmp_path, extra=["--", "not-a-pair"])
    assert done.returncode == 2
    done = subprocess.run(["bash", str(WRAPPER), "--flip", "x"], capture_output=True, text=True, env=_clean_env())
    assert done.returncode == 2


# ---- --mode one-pass (owner decision 270 A) ----


def test_one_pass_mode_runs_the_flip_once_without_refresh_or_second_loop(tmp_path):
    body = ('#!/bin/bash\ncd "$SAEA_MAIN" || exit 1\n'
            '[ "$FLIP_MODE" = one-pass ] || { echo "not one-pass" >&2; exit 3; }\n'
            'echo onepass > op.txt; git add op.txt; git commit -q -m onepass\n'
            'git rev-parse HEAD > "$FAKE_COMMIT_FILE"\n')
    master = _make_master(tmp_path, flip_body=body)
    before = _git(master, "rev-parse", "HEAD")
    done, log = _run(master, tmp_path, extra=["--mode", "one-pass"])
    assert done.returncode == 0, done.stdout + done.stderr
    text = log.read_text()
    assert text.count("== one-pass flip at") == 1 and "== flip pass" not in text and "== refresh plan pins" not in text
    assert "== gate" in text and "FLIP_CHAIN_DONE" in text
    assert _git(master, "rev-list", "--count", f"{before}..HEAD") == "1"
    assert (tmp_path / "x-flight-commit.txt").read_text().strip() == _git(master, "rev-parse", "HEAD")


def test_one_pass_failure_and_verify_fixed_point(tmp_path):
    failing = '#!/bin/bash\ncd "$SAEA_MAIN" || exit 1\nexit 9\n'
    master = _make_master(tmp_path, flip_body=failing)
    head = _git(master, "rev-parse", "HEAD")
    done, log = _run(master, tmp_path, extra=["--mode", "one-pass"])
    assert done.returncode == 6 and "ONE-PASS FLIP FAILED" in log.read_text()
    assert _git(master, "rev-parse", "HEAD") == head
    # verify: the iterative pass must commit nothing; a flip that still has work in iterate mode is refused
    body = ('#!/bin/bash\ncd "$SAEA_MAIN" || exit 1\n'
            'if [ "$FLIP_MODE" = one-pass ]; then echo a > a.txt; else date +%N >> b.txt; fi\n'
            'git add -A; git commit -q -m x\n')
    tmp2 = tmp_path / "v"
    tmp2.mkdir()
    master2 = _make_master(tmp2, flip_body=body)
    done, log = _run(master2, tmp2, extra=["--mode", "one-pass", "--verify-fixed-point"])
    assert done.returncode == 6 and "NOT A FIXED POINT" in log.read_text()


def test_mode_defaults_to_iterate_and_rejects_unknown_values(tmp_path):
    master = _make_master(tmp_path)
    done, _ = _run(master, tmp_path, extra=["--mode", "bogus"])
    assert done.returncode == 2
    done, _ = _run(master, tmp_path, extra=["--verify-fixed-point"])
    assert done.returncode == 2
    assert 'MODE=iterate; VERIFY=0' in WRAPPER.read_text()
