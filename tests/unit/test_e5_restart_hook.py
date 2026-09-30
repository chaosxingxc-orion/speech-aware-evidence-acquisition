"""The E5-0 shell layer on fakes: scripts/flights/e5/e5_tool_pass.sh, scripts/flights/batch/serving_restart_hook_e5.sh
and serving_swap.sh --gap-hook.

A fake tool pass / fake python record their arguments; the serving swap runs on the synthetic host of
tests/unit/test_serving_swap.py (fake pgrep, powershell, serving_session.sh). Nothing starts or stops a server,
loads a model or touches the GPU.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / "scripts/flights/batch/serving_restart_hook_e5.sh"
PASS = REPO / "scripts/flights/e5/e5_tool_pass.sh"
SWAP = REPO / "scripts/flights/batch/serving_swap.sh"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("flock") is None or os.name == "nt",
    reason="the operations scripts run under WSL bash with util-linux flock",
)


@pytest.mark.parametrize("script", [HOOK, PASS, SWAP])
def test_every_script_parses(script):
    assert subprocess.run(["bash", "-n", str(script)], capture_output=True).returncode == 0


class Hook:
    def __init__(self, root: Path, rc: int = 0):
        self.root = root
        self.request = root / "e5-tool-pass.request"
        self.log = root / "e5-tool-pass.log"
        self.calls = root / "calls.txt"
        self.fake = root / "fake_pass.sh"
        self.fake.write_text(f'#!/bin/bash\necho "$*" >> "{self.calls}"\necho "fake pass $*"\nexit {rc}\n',
                             encoding="utf-8", newline="\n")

    def env(self):
        env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
        env.update(SAEA_E5_REQUEST=str(self.request), SAEA_E5_LOG=str(self.log),
                   SAEA_E5_LOCKFILE=str(self.root / "e5.lock"), SAEA_E5_TOOL_PASS=str(self.fake))
        return env

    def run(self):
        return subprocess.run(["bash", str(HOOK)], capture_output=True, text=True, env=self.env(), timeout=60)

    def lines(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def called(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []


def test_no_request_is_a_logged_no_op(tmp_path):
    h = Hook(tmp_path)
    r = h.run()
    assert r.returncode == 0 and "E5-0 SKIP" in r.stdout and h.called() == []


def test_a_request_runs_both_rosters_once_and_is_consumed(tmp_path):
    h = Hook(tmp_path)
    h.request.write_text("requested by root\n")
    r = h.run()
    assert r.returncode == 0, r.stdout
    assert h.called() == ["both"]
    assert any("E5-0 START" in line for line in h.lines()) and any("E5-0 DONE" in line for line in h.lines())
    assert not h.request.exists()
    again = h.run()                     # idempotent: the request is gone, nothing runs twice
    assert again.returncode == 0 and "E5-0 SKIP" in again.stdout and h.called() == ["both"]


def test_the_cpu_mode_line_selects_the_fallback(tmp_path):
    h = Hook(tmp_path)
    h.request.write_text("mode=cpu\n")
    assert h.run().returncode == 0 and h.called() == ["both --cpu"]


def test_a_failed_pass_is_not_retried(tmp_path):
    h = Hook(tmp_path, rc=3)
    h.request.write_text("x\n")
    r = h.run()
    assert r.returncode == 3 and any("E5-0 FAILED rc=3" in line for line in h.lines())
    assert not h.request.exists() and list(tmp_path.glob("e5-tool-pass.request.failed-*"))
    assert h.run().returncode == 0 and h.called() == ["both"]


def test_a_concurrent_hook_is_busy_and_keeps_the_request(tmp_path):
    h = Hook(tmp_path)
    h.request.write_text("x\n")
    holder = subprocess.Popen(["flock", str(tmp_path / "e5.lock"), "python3", "-c", "import time; time.sleep(30)"])
    try:
        time.sleep(0.5)
        r = h.run()
        assert r.returncode == 0 and "E5-0 BUSY" in r.stdout and h.request.exists() and h.called() == []
    finally:
        holder.kill()
        holder.wait()


# ---------------------------------------------------------------------------- e5_tool_pass.sh


def _fake_python(root: Path, fail_roster: str | None = None) -> Path:
    fake = root / "python"
    body = f'#!/bin/bash\necho "$*" >> "{root}/py.txt"\n'
    if fail_roster:
        body += f'case "$*" in *"--roster {fail_roster}"*) exit 3 ;; esac\n'
    fake.write_text(body + "exit 0\n", encoding="utf-8", newline="\n")
    fake.chmod(0o755)
    return fake


def _pass(root: Path, *args, fail=None):
    env = {k: v for k, v in os.environ.items() if k not in ("GIT_DIR", "GIT_WORK_TREE")}
    env.update(SAEA_E5_PY=str(_fake_python(root, fail)), SPEECHRL_DATA_DIR=str(root), SAEA_E5_LOCK=str(root / "l"))
    return subprocess.run(["bash", str(PASS), *args], capture_output=True, text=True, env=env, timeout=60)


def test_the_tool_pass_runs_fold_a_then_fold_b_and_stops_at_the_first_failure(tmp_path):
    r = _pass(tmp_path, "both", "--cpu")
    assert r.returncode == 0, r.stdout
    calls = (tmp_path / "py.txt").read_text().splitlines()
    assert len(calls) == 2 and "run --roster fold-a" in calls[0] and "run --roster fold-b" in calls[1]
    assert all(c.endswith("--cpu") for c in calls)
    (tmp_path / "py.txt").unlink()
    r = _pass(tmp_path, "both", fail="fold-a")
    assert r.returncode == 3 and len((tmp_path / "py.txt").read_text().splitlines()) == 1
    (tmp_path / "py.txt").unlink()
    assert _pass(tmp_path, "fold-b", "--check").returncode == 0
    assert "check --roster fold-b" in (tmp_path / "py.txt").read_text()
    assert _pass(tmp_path, "fold-c").returncode == 64


# ---------------------------------------------------------------------------- serving_swap.sh --gap-hook


def _host_module():
    spec = importlib.util.spec_from_file_location("serving_swap_harness", REPO / "tests/unit/test_serving_swap.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_gap_hook_runs_between_the_stop_and_the_start_and_never_blocks_the_start(tmp_path):
    hs = _host_module()
    host = hs.Host(tmp_path)
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(hs.PORT_SERVER)
    probe = tmp_path / "gap.sh"
    probe.write_text(f'#!/bin/bash\n[ -f "{host.state}/server_up" ] && echo up > "{tmp_path}/gap.seen" '
                     f'|| echo down > "{tmp_path}/gap.seen"\n'
                     f'[ -f "{host.home}/serving-swap.pending" ] && echo pending >> "{tmp_path}/gap.seen"\nexit 5\n',
                     encoding="utf-8", newline="\n")
    result, summary = host.swap("slurp-np4", "--restart", "--gap-hook", str(probe))
    assert result.returncode == 0 and summary["result"] == "swapped", result.stdout
    assert (tmp_path / "gap.seen").read_text().split() == ["down", "pending"]
    steps = [(s["step"], s["verdict"]) for s in summary["steps"]]
    names = [s for s, _ in steps]
    assert ("gap-hook", "exit-5") in steps
    assert names.index("gap-hook") > names.index("port-8080") and names.index("gap-hook") < names.index("task-start")
    assert (host.state / "resident").read_text() == hs.GEOMETRY["slurp-np4"][0]


def test_the_gap_hook_needs_restart_and_an_existing_script(tmp_path):
    hs = _host_module()
    host = hs.Host(tmp_path)
    probe = tmp_path / "gap.sh"
    probe.write_text("#!/bin/bash\nexit 0\n")
    r = host.run(["bash", str(SWAP), "slurp-np4", "--gap-hook", str(probe)])
    assert r.returncode == 64 and "--gap-hook needs --restart" in r.stdout
    r = host.run(["bash", str(SWAP), "slurp-np4", "--restart", "--gap-hook", str(tmp_path / "missing.sh")])
    assert r.returncode == 64 and "not found" in r.stdout
