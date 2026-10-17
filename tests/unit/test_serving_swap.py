"""The serving-lifecycle operations scripts of owner decision 163 (scripts/flights/batch/serving_swap.sh,
serving_wait_ready.sh + serving_ready_probe.py, serving_lib.sh, queue_lib.sh, the four serving_switch_*.sh and the
decision-162 sidecar admission of the preparation launchers).

Every script runs for real under bash with FAKE ``pgrep``, ``curl``, ``powershell.exe``, ``sleep``, ``nvidia-smi``
and ``serving_session.sh`` first on PATH (or named through the scripts' own SAEA_* overrides), a temporary data
root and a temporary runtime root: nothing here starts, stops or probes a server, and no port is contacted. Fake
process ids sit above the kernel's pid_max so a stray ``kill`` can never reach a real process.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
BATCH = REPO / "scripts" / "flights" / "batch"

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("flock") is None or os.name == "nt",
    reason="the operations scripts run under WSL bash with util-linux flock",
)

GEOMETRY = {
    "slurp-np4": ("serving-slurp-native-candidate-five-train-a-np4-v1",
                  "q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1", 4, 24576,
                  "SAEA-Serving", "SAEA-Monitor", "serving-slurp-native-np4-"),
    "a2t-np3": ("serving-a2t-native-role-base-np3-max2048-v3",
                "q4km-mmproj-free-a2t-native-role-np3-max2048-v1", 3, 32768,
                "SAEA-Serving-A2T", "SAEA-Monitor-A2T", "serving-a2t-np3-"),
    "e21-np4": ("serving-e21-native-window-flightruntime-np4-max1024-v1",
                "q4km-e21-native-window-packets-cddb000c-np4-max1024-v1", 4, 24576,
                "SAEA-Serving-E21", "SAEA-Monitor-E21", "serving-e21-np4-"),
    "det-np1": ("serving-slurp-native-det-np1-nocache-v1",
                "q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1", 1, 24576,
                "SAEA-Serving-DET", "SAEA-Monitor-DET", "serving-slurp-det-np1-"),
    "think-np4": ("serving-slurp-thinking-direct-fold-b-np4-max8192-v1",
                  "q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1", 4, 24576,
                  "SAEA-Serving-THINK", "SAEA-Monitor-THINK", "serving-slurp-think-np4-"),
    "think-budget-np4": ("serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1",
                         "q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1", 4, 24576,
                         "SAEA-Serving-THINKB", "SAEA-Monitor-THINKB", "serving-slurp-thinkb-np4-"),
    # NX-T R2b (owner rulings 323 / 325 A): the same np4 x 24576 server geometry, a new session id for the raised geometry cap (max_tokens 7168)
    "think-budget7168-np4": ("serving-slurp-thinking-module-fold-b-np4-budget3072-max7168-v1",
                             "q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max7168-v1", 4, 24576,
                             "SAEA-Serving-THINKB7", "SAEA-Monitor-THINKB7", "serving-slurp-thinkb7-np4-"),
}
PORT_SERVER = "9000101 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8080 -m m.gguf"
SIDECAR = "9000201 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8081 -m m.gguf -ngl 0"
PREPROCESS = "9000202 python -B scripts/slurp_evo_fold_preprocess.py --roster test-sample-3010 --run --workers 4"
WORKTREE_PREPARE = (
    "9000301 python -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-supply --repo-root "
    "/home/chao/saea-worktrees/fable-x --data-root /data/x --runtime-root /home/chao --lock-path /tmp/l"
)
WORKTREE_CHECK = "9000302 python -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root /w"
CAMPAIGN = "9000401 python -B -m speech_aware_evidence_acquisition.core.flight.cli campaign --repo-root /r"
WORKER = "9000402 python -B -m speech_aware_evidence_acquisition.core.flight.cli worker --repo-root /r"
DRIVER = "9000403 bash /mnt/d/x/scripts/flights/batch/batch_driver.sh"
LEASE = "9000404 python -B -m speech_aware_evidence_acquisition.core.flight.lease_cli --stage worker"

_FAKES = {
    "pgrep": r"""#!/bin/bash
list=0
while [ $# -gt 1 ]; do case "$1" in -af|-fa|-a) list=1 ;; esac; shift; done
[ -f "$FAKE_STATE/procs" ] || exit 1
out=$(grep -E -- "$1" "$FAKE_STATE/procs") || exit 1
if [ $list = 1 ]; then printf '%s\n' "$out"; else printf '%s\n' "$out" | awk '{print $1}'; fi
""",
    "curl": r"""#!/bin/bash
for a in "$@"; do url=$a; done
echo "$url" >> "$FAKE_STATE/curl.log"
[ -f "$FAKE_STATE/server_up" ] || exit 7
case "$url" in
  */health) echo '{"status":"ok"}' ;;
  */props) cat "$FAKE_STATE/props.json" ;;
  *) echo '[]' ;;
esac
""",
    "powershell.exe": r"""#!/bin/bash
name=; script=; verb=
while [ $# -gt 0 ]; do
  case "$1" in -Name) name=$2; shift ;; -Script) script=$2; shift ;; -Start|-Stop|-Status) verb=$1 ;; esac
  shift
done
echo "$verb $name $script" >> "$FAKE_STATE/ps.log"
case "$verb" in
  -Status) echo "$name : state=Ready lastRun=1 lastResult=0 action=-d Ubuntu-24.04 bash $script" ;;
  -Stop) [ -f "$FAKE_STATE/on_stop_$name" ] && bash "$FAKE_STATE/on_stop_$name"; echo "$name stopped" ;;
  -Start)
    rc=0; [ -f "$FAKE_STATE/ps_rc_$name" ] && rc=$(cat "$FAKE_STATE/ps_rc_$name")
    [ "$rc" = 0 ] && [ -f "$FAKE_STATE/on_start_$name" ] && bash "$FAKE_STATE/on_start_$name"
    echo "$name started: state=Running"; exit "$rc" ;;
esac
exit 0
""",
    "sleep": "#!/bin/bash\nexit 0\n",
    "nvidia-smi": "#!/bin/bash\necho '560 MiB'\n",
    "serving_session.sh": r"""#!/bin/bash
cmd=$1; shift
sid=; min=12; margin=0
while [ $# -gt 0 ]; do
  case "$1" in --session-id) sid=$2; shift ;; --min-host-free-gb) min=$2; shift ;; --margin-gb) margin=$2; shift ;; esac
  shift
done
echo "$cmd $sid" >> "$FAKE_STATE/ss.log"
case "$cmd" in
  resident)
    if [ -s "$FAKE_STATE/resident" ]; then
      printf '{"resident": true, "session_id": "%s", "process_state": "%s", "stale": false}\n' \
        "$(cat "$FAKE_STATE/resident")" "$(cat "$FAKE_STATE/process_state" 2>/dev/null || echo running)"
      exit 0
    fi
    echo '{"resident": false}'; exit 3 ;;
  host-memory)
    python3 - "$min" "$margin" "$FAKE_STATE/host_free_gb" <<'PY'
import json, sys
minimum, margin, path = float(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
try:
    free = float(open(path).read())
except OSError:
    free = None
admits = None if free is None else free >= minimum + margin
print(json.dumps({"host_free_gb": free, "admits": admits, "required_gb": minimum + margin}))
sys.exit(4 if admits is False else 0)
PY
    exit $? ;;
  stop)
    [ -f "$FAKE_STATE/stop_rc" ] && exit "$(cat "$FAKE_STATE/stop_rc")"
    python3 -c 'import json,sys; from datetime import datetime, timezone; open(sys.argv[1], "w").write(json.dumps({"stopped_at": datetime.now(timezone.utc).isoformat()}))' \
      "$SAEA_DATA/serving/$sid/session-stop.json"
    rm -f "$FAKE_STATE/resident" "$FAKE_STATE/server_up"
    sed -i '/--port 8080/d' "$FAKE_STATE/procs" 2>/dev/null
    echo '{"stopped": true}' ;;
esac
""",
    "fake_up.py": r"""import json, sys, time
from datetime import datetime, timezone
from pathlib import Path
session_dir, sid, fragment, slots, n_ctx, state = sys.argv[1:7]
d = Path(session_dir); d.mkdir(parents=True, exist_ok=True)
(d / "session.json").write_text(json.dumps({
    "session_id": sid, "started_at": datetime.now(timezone.utc).isoformat(),
    "identity": {"model_fragment": fragment}}))
(d / "session-stop.json").unlink(missing_ok=True)
state = Path(state)
(state / "resident").write_text(sid)
(state / "server_up").write_text("up")
(state / "props.json").write_text(json.dumps({"total_slots": int(slots), "default_generation_settings": {"n_ctx": int(n_ctx)}}))
with (state / "procs").open("a") as handle:
    handle.write("9000101 /home/chao/llama.cpp-featcache/build/bin/llama-server --host 127.0.0.1 --port 8080 -m m.gguf\n")
""",
    "fake_monitor.py": r"""import json, sys, time
from pathlib import Path
with (Path(sys.argv[1]) / "monitor.jsonl").open("a") as handle:
    handle.write(json.dumps({"sampled_at": time.time() + 0.001, "sampled_at_iso": "now", "server_ok": True}) + "\n")
""",
}


def _iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _stamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class Host:
    """A synthetic host: data root, runtime root, fake binaries, fake state."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.data = root / "data"
        self.home = root / "home"
        self.state = root / "state"
        self.bin = root / "bin"
        for directory in (self.data / "serving", self.data / "locks", self.home, self.state, self.bin):
            directory.mkdir(parents=True, exist_ok=True)
        for name, body in _FAKES.items():
            path = self.bin / name
            path.write_text(body, encoding="utf-8", newline="\n")
            path.chmod(0o755)
        (self.state / "procs").write_text("", encoding="utf-8")
        for target, (sid, fragment, slots, n_ctx, serving, monitor, _) in GEOMETRY.items():
            (self.data / "serving" / sid).mkdir(parents=True, exist_ok=True)
            self.on_start(serving, "up", target)
            self.on_start(monitor, "monitor", target)

    # ---------------------------------------------------------------- state helpers
    def env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)
        env.update(
            PATH=f"{self.bin}:{env.get('PATH', '/usr/bin:/bin')}",
            FAKE_STATE=str(self.state),
            SAEA_DATA=str(self.data),
            SAEA_RUNTIME_ROOT=str(self.home),
            SAEA_MAIN=str(REPO),
            SAEA_SERVING_SESSION=str(self.bin / "serving_session.sh"),
            SAEA_POWERSHELL=str(self.bin / "powershell.exe"),
            SAEA_MIN_HOST_FREE_GB="12.0",
            PYTHONDONTWRITEBYTECODE="1",
        )
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        env.update(extra)
        return env

    def procs(self, *lines: str) -> None:
        (self.state / "procs").write_text("".join(line + "\n" for line in lines), encoding="utf-8")

    def host_free(self, gb: float | None) -> None:
        path = self.state / "host_free_gb"
        if gb is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(str(gb), encoding="utf-8")

    def session_dir(self, target: str) -> Path:
        return self.data / "serving" / GEOMETRY[target][0]

    def up(self, target: str) -> None:
        sid, fragment, slots, n_ctx, *_ = GEOMETRY[target]
        subprocess.run(
            ["python3", str(self.bin / "fake_up.py"), str(self.session_dir(target)), sid, fragment,
             str(slots), str(n_ctx), str(self.state)],
            check=True,
        )
        self.monitor(target)

    def monitor(self, target: str) -> None:
        subprocess.run(["python3", str(self.bin / "fake_monitor.py"), str(self.session_dir(target))], check=True)

    def on_start(self, task: str, behaviour: str, target: str) -> None:
        sid, fragment, slots, n_ctx, _, _, server_log = GEOMETRY[target]
        if behaviour == "up":
            body = (f'python3 "{self.bin}/fake_up.py" "{self.session_dir(target)}" {sid} {fragment} '
                    f'{slots} {n_ctx} "{self.state}"\n')
        elif behaviour == "monitor":
            body = f'python3 "{self.bin}/fake_monitor.py" "{self.session_dir(target)}"\n'
        elif behaviour == "refuse":
            body = (f'echo "serving_session: refusing to start: the host\'s free memory is 11.7 GB, below '
                    f'--min-host-free-gb 12.0 GB" > "{self.home}/{server_log}$(date -u +%Y%m%dT%H%M%SZ).log"\n')
        elif behaviour == "wrong":
            body = (f'python3 "{self.bin}/fake_up.py" "{self.session_dir(target)}" {sid} {fragment} '
                    f'{slots + 1} {n_ctx} "{self.state}"\n')
        else:
            raise ValueError(behaviour)
        (self.state / f"on_start_{task}").write_text(body, encoding="utf-8", newline="\n")

    def log(self, name: str) -> list[str]:
        path = self.state / name
        return path.read_text(encoding="utf-8").splitlines() if path.exists() else []

    # ---------------------------------------------------------------- runners
    def run(self, argv: list[str], timeout: float = 120, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=self.env(**extra),
                              cwd=str(self.root))

    def swap(self, *args: str, **extra: str) -> tuple[subprocess.CompletedProcess, dict]:
        result = self.run(["bash", str(BATCH / "serving_swap.sh"), *args], **extra)
        summary = json.loads(result.stdout.strip().splitlines()[-1])
        return result, summary

    def lib(self, script: str, **extra: str) -> subprocess.CompletedProcess:
        return self.run(["bash", "-c", f'source "{BATCH}/serving_lib.sh"\n{script}'], **extra)


@pytest.fixture
def host(tmp_path):
    return Host(tmp_path)


def _probe_module():
    spec = importlib.util.spec_from_file_location("serving_ready_probe", BATCH / "serving_ready_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------- defect 1: precise flight detection


@pytest.mark.parametrize("line", [WORKTREE_PREPARE, WORKTREE_CHECK, SIDECAR, PREPROCESS])
def test_a_model_free_flight_cli_or_a_sidecar_is_not_a_flight(host, line):
    host.procs(line)
    # The 2026-09-27 13:08Z reproduction: the old pattern matched the model-free worktree run and refused the swap.
    old = subprocess.run(["grep", "-E", "core.flight.cli|batch_driver.sh"], input=line + "\n",
                         capture_output=True, text=True)
    if "core.flight.cli" in line:
        assert old.returncode == 0
    result = host.lib('if saea_flight_alive; then echo ALIVE; else echo NONE; fi')
    assert result.stdout.strip().splitlines()[-1] == "NONE", result.stdout + result.stderr


@pytest.mark.parametrize("line", [CAMPAIGN, WORKER, DRIVER, LEASE])
def test_a_generation_flight_process_is_a_flight(host, line):
    host.procs(WORKTREE_PREPARE, line)
    result = host.lib('if saea_flight_alive; then echo ALIVE; else echo NONE; fi')
    assert "ALIVE" in result.stdout and line.split()[0] in result.stdout
    assert WORKTREE_PREPARE.split()[0] not in result.stdout


def test_a_flight_lock_is_a_flight(host):
    (host.data / "locks" / "flight.lock").write_text("{}", encoding="utf-8")
    result = host.lib('if saea_flight_alive; then echo ALIVE; else echo NONE; fi')
    assert "flight.lock present" in result.stdout and "ALIVE" in result.stdout


def test_the_switch_scripts_let_a_model_free_worktree_run_through_and_refuse_a_campaign(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(WORKTREE_PREPARE, PORT_SERVER)
    passed = host.run(["bash", str(BATCH / "serving_switch_to_a2t.sh")])
    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert "stop serving-slurp-native-candidate-five-train-a-np4-v1" in host.log("ss.log")
    host.up("slurp-np4")
    host.procs(CAMPAIGN)
    refused = host.run(["bash", str(BATCH / "serving_switch_to_e21.sh")])
    assert refused.returncode == 7 and "refusing" in refused.stdout


# ---------------------------------------------------------------------------- defect 2: host memory before the stop


def test_the_switch_script_refuses_before_its_stop_when_the_host_is_short(host):
    host.up("slurp-np4")
    host.host_free(11.7)
    host.procs(PORT_SERVER, SIDECAR, PREPROCESS)
    result = host.run(["bash", str(BATCH / "serving_switch_to_e21.sh")])
    assert result.returncode == 8, result.stdout
    assert "nothing is stopped" in result.stdout and "8081" in result.stdout
    assert not any(line.startswith("stop") for line in host.log("ss.log"))


def test_the_swap_refuses_on_host_memory_and_names_the_sidecar_without_stopping(host):
    host.up("slurp-np4")
    host.host_free(12.3)  # above the bare guard, under guard + the 0.5 GB margin
    host.procs(PORT_SERVER, SIDECAR, PREPROCESS)
    result, summary = host.swap("e21-np4")
    assert result.returncode == 8 and summary["result"] == "refused"
    step = {s["step"]: s for s in summary["steps"]}["host-memory"]
    assert step["verdict"] == "short" and "8081" in step["detail"] and "slurp_evo_fold_preprocess" in step["detail"]
    assert not any(line.startswith("stop") for line in host.log("ss.log"))
    assert not any(line.startswith(("-Stop", "-Start")) for line in host.log("ps.log"))
    assert (host.session_dir("slurp-np4") / "session.json").exists()
    assert not (host.session_dir("slurp-np4") / "session-stop.json").exists()


def test_the_sidecar_admission_needs_a_running_resident_session_and_no_pending_swap(host):
    refused = host.lib('saea_sidecar_admission; echo "rc=$?"')
    assert "no GPU serving session is resident" in refused.stdout and "rc=1" in refused.stdout
    host.up("slurp-np4")
    admitted = host.lib('saea_sidecar_admission; echo "rc=$?"')
    assert admitted.stdout.strip().endswith("rc=0"), admitted.stdout
    (host.state / "process_state").write_text("defunct")
    defunct = host.lib('saea_sidecar_admission; echo "rc=$?"')
    assert "not running" in defunct.stdout and "rc=1" in defunct.stdout
    (host.state / "process_state").unlink()
    pending = host.home / "serving-swap.pending"
    pending.write_text(json.dumps({"pid": os.getpid(), "target": "a2t-np3"}))
    during = host.lib('saea_sidecar_admission; echo "rc=$?"')
    assert "serving swap is in progress" in during.stdout and "rc=1" in during.stdout
    pending.write_text(json.dumps({"pid": 9_000_999, "target": "a2t-np3"}))  # its swap is gone: stale
    stale = host.lib('saea_sidecar_admission; echo "rc=$?"')
    assert stale.stdout.strip().endswith("rc=0")


def test_the_preparation_launchers_call_the_sidecar_admission():
    generic = (BATCH / "prep_generic_task_entry.sh").read_text(encoding="utf-8")
    sample = (REPO / "scripts/flights/testsample/prep_test_sample.sh").read_text(encoding="utf-8")
    assert generic.index("saea_sidecar_admission") < generic.index("--run \\")
    assert sample.index("saea_sidecar_admission") < sample.index("bash scripts/flights/batch/prep_generic_task_entry.sh")


# ---------------------------------------------------------------------------- defect 3: the strict wait


def _stale_np4(host, *, refusal: bool) -> None:
    """The 12:39Z state: an old np4 session.json, the stop record of the 12:26Z swap newer than it, a task entry
    started at 12:39:13Z and (with ``refusal``) the start guard's refusal in the new server log."""
    now = time.time()
    directory = host.session_dir("slurp-np4")
    (directory / "session.json").write_text(json.dumps({
        "session_id": GEOMETRY["slurp-np4"][0], "started_at": _iso(now - 7200),
        "identity": {"model_fragment": GEOMETRY["slurp-np4"][1]}}))
    (directory / "session-stop.json").write_text(json.dumps({"stopped_at": _iso(now - 800)}))
    (host.home / f"serving-task-{_stamp(now - 20)}.log").write_text("task entry\nwrapper pid 1\n")
    if refusal:
        (host.home / f"serving-slurp-native-np4-{_stamp(now - 15)}.log").write_text(
            "serving_session: refusing to start: the host's free memory is 11.7 GB, below --min-host-free-gb 12.0 GB\n")


def test_the_legacy_wait_reports_the_real_refusal_with_a_non_zero_exit(host):
    _stale_np4(host, refusal=True)
    result = host.run(["bash", str(BATCH / "slurp_wait_ready.sh")])
    assert result.returncode == 3, result.stdout
    assert "SESSION STOPPED EARLY" in result.stdout and "11.7 GB" in result.stdout


def test_the_legacy_wait_takes_an_older_stop_record_as_stale_not_as_this_start(host):
    _stale_np4(host, refusal=False)
    result = host.run(["bash", str(BATCH / "slurp_wait_ready.sh"), "--timeout", "0"])
    assert result.returncode == 2, result.stdout
    assert "TIMEOUT" in result.stdout and "SESSION STOPPED EARLY" not in result.stdout


def test_the_wait_is_ready_only_with_every_check(host):
    since = int(time.time()) - 1
    host.up("a2t-np3")
    ok = host.run(["bash", str(BATCH / "a2t_wait_ready.sh"), "--since", str(since), "--timeout", "0"])
    assert ok.returncode == 0, ok.stdout
    assert "A2T SESSION READY" in ok.stdout and "slots 3" in ok.stdout
    # A session document from before the swap start is not this start.
    late = host.run(["bash", str(BATCH / "a2t_wait_ready.sh"), "--since", str(int(time.time()) + 5),
                     "--timeout", "0"])
    assert late.returncode == 2 and "earlier start" in late.stdout


def test_the_wait_refuses_a_missing_monitor_sample_and_a_down_server(host):
    since = int(time.time()) - 1
    host.up("e21-np4")
    (host.session_dir("e21-np4") / "monitor.jsonl").unlink()
    no_monitor = host.run(["bash", str(BATCH / "e21_wait_ready.sh"), "--since", str(since), "--timeout", "0"])
    assert no_monitor.returncode == 2 and "no monitor sample" in no_monitor.stdout
    host.monitor("e21-np4")
    (host.state / "server_up").unlink()
    down = host.run(["bash", str(BATCH / "e21_wait_ready.sh"), "--since", str(since), "--timeout", "0"])
    assert down.returncode == 2 and "/health is not ok" in down.stdout


def test_the_wait_names_a_wrong_slot_geometry(host):
    since = int(time.time()) - 1
    host.up("slurp-np4")
    (host.state / "props.json").write_text(json.dumps({"total_slots": 1, "default_generation_settings": {"n_ctx": 24576}}))
    result = host.run(["bash", str(BATCH / "serving_wait_ready.sh"), "slurp-np4", "--since", str(since), "--timeout", "0"])
    assert result.returncode == 4 and "WRONG GEOMETRY" in result.stdout


def test_the_wait_reports_a_stop_of_this_start(host):
    since = int(time.time()) - 5
    host.up("det-np1")
    (host.session_dir("det-np1") / "session-stop.json").write_text(json.dumps({"stopped_at": _iso(time.time())}))
    result = host.run(["bash", str(BATCH / "serving_wait_ready.sh"), "det-np1", "--since", str(since), "--timeout", "0"])
    assert result.returncode == 3 and "SESSION STOPPED EARLY" in result.stdout


def test_the_probe_holds_a_fresh_session_behind_an_unarchived_stale_stop(tmp_path):
    probe = _probe_module()
    now = time.time()
    (tmp_path / "session.json").write_text(json.dumps({
        "session_id": "s", "started_at": _iso(now), "identity": {"model_fragment": "f"}}))
    (tmp_path / "session-stop.json").write_text(json.dumps({"stopped_at": _iso(now - 600)}))
    state, reasons, _ = probe.verdict(
        session_dir=tmp_path, session_id="s", fragment="f", geometry=(4, 24576), since=now - 60,
        health='{"status":"ok"}', props={"total_slots": 4, "default_generation_settings": {"n_ctx": 24576}},
        monitor_lines=[json.dumps({"sampled_at": now + 1, "server_ok": True})], refusals=[],
    )
    assert state == probe.WAITING and any("not archived" in reason for reason in reasons)
    (tmp_path / "session-stop.json").unlink()
    state, reasons, _ = probe.verdict(
        session_dir=tmp_path, session_id="s", fragment="f", geometry=(4, 24576), since=now - 60,
        health='{"status":"ok"}', props={"total_slots": 4, "default_generation_settings": {"n_ctx": 24576}},
        monitor_lines=[json.dumps({"sampled_at": now + 1, "server_ok": True})], refusals=[],
    )
    assert state == probe.READY and reasons == []


def test_the_probe_reads_the_geometry_from_the_fragment():
    probe = _probe_module()
    for sid, fragment, slots, n_ctx, *_ in GEOMETRY.values():
        assert probe.fragment_geometry(REPO / "configs" / "model" / f"{fragment}.json") == (slots, n_ctx)


# ---------------------------------------------------------------------------- defect 4: the one swap tool


@pytest.mark.parametrize("target", sorted(GEOMETRY))
def test_the_dry_run_prints_the_plan_and_every_verdict_and_acts_on_nothing(host, target):
    source = "a2t-np3" if target == "slurp-np4" else "slurp-np4"
    host.up(source)
    host.host_free(20.0)
    host.procs(PORT_SERVER, WORKTREE_PREPARE)
    result, summary = host.swap(target, "--dry-run")
    assert result.returncode == 0, result.stdout
    assert summary["result"] == "dry-run" and summary["from"] == source and summary["target"] == target
    verdicts = {s["step"]: s["verdict"] for s in summary["steps"]}
    assert verdicts["swap-lock"] == "free" and verdicts["flight"] == "none"
    assert verdicts["resident"] == source and verdicts["host-memory"] == "admits" and verdicts["plan"] == "go"
    assert verdicts["target-entries"] == "present"
    assert {line.split()[0] for line in host.log("ps.log")} == {"-Status"}
    assert host.log("ss.log") == ["resident ", "host-memory "]
    assert not (host.home / "serving-swap.pending").exists()


def test_the_swap_runs_in_order_and_reports_swapped(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(PORT_SERVER, WORKTREE_PREPARE, SIDECAR)
    result, summary = host.swap("a2t-np3")
    assert result.returncode == 0, result.stdout
    assert summary["result"] == "swapped" and summary["from"] == "slurp-np4"
    actions = [line.split()[:2] for line in host.log("ps.log") if not line.startswith("-Status")]
    assert actions == [["-Stop", "SAEA-Serving"], ["-Stop", "SAEA-Monitor"],
                       ["-Start", "SAEA-Serving-A2T"], ["-Start", "SAEA-Monitor-A2T"]]
    start_line = [line for line in host.log("ps.log") if line.startswith("-Start SAEA-Serving-A2T")][0]
    assert start_line.endswith(str(REPO / "scripts/flights/batch/serving_task_entry_a2t.sh"))
    assert host.log("ss.log")[:3] == ["resident ", "host-memory ", "stop serving-slurp-native-candidate-five-train-a-np4-v1"]
    assert (host.state / "resident").read_text() == GEOMETRY["a2t-np3"][0]
    assert not (host.home / "serving-swap.pending").exists()
    history = (host.home / "serving-swap.jsonl").read_text().splitlines()
    assert json.loads(history[-1])["result"] == "swapped"


def test_a_failed_target_start_restores_the_previous_geometry(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(PORT_SERVER)
    host.on_start("SAEA-Serving-E21", "refuse", "e21-np4")
    result, summary = host.swap("e21-np4")
    assert result.returncode == 12, result.stdout
    assert summary["result"] == "failed-restored"
    verdicts = {s["step"]: s["verdict"] for s in summary["steps"]}
    assert verdicts["ready-e21-np4"] == "not-ready-exit-3" and verdicts["ready-slurp-np4"] == "ready"
    starts = [line.split()[1] for line in host.log("ps.log") if line.startswith("-Start")]
    assert starts == ["SAEA-Serving-E21", "SAEA-Monitor-E21", "SAEA-Serving", "SAEA-Monitor"]
    assert (host.state / "resident").read_text() == GEOMETRY["slurp-np4"][0]


def test_a_wrong_geometry_is_torn_down_and_restored(host):
    host.up("a2t-np3")
    host.host_free(20.0)
    host.procs(PORT_SERVER)
    host.on_start("SAEA-Serving", "wrong", "slurp-np4")
    result, summary = host.swap("slurp-np4")
    assert result.returncode == 12, result.stdout
    assert "stop serving-slurp-native-candidate-five-train-a-np4-v1" in host.log("ss.log")
    assert (host.state / "resident").read_text() == GEOMETRY["a2t-np3"][0]


def test_a_failed_restore_is_reported_unrestored(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(PORT_SERVER)
    host.on_start("SAEA-Serving-A2T", "refuse", "a2t-np3")
    host.on_start("SAEA-Serving", "refuse", "slurp-np4")
    result, summary = host.swap("a2t-np3", "--wait-timeout", "1")
    assert result.returncode == 13 and summary["result"] == "failed-unrestored", result.stdout


def test_a_task_start_refusal_is_a_failure_not_a_success(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(PORT_SERVER)
    (host.state / "ps_rc_SAEA-Serving-DET").write_text("3")
    result, summary = host.swap("det-np1")
    assert result.returncode == 12, result.stdout
    verdicts = {s["step"]: s["verdict"] for s in summary["steps"]}
    assert "SAEA-Serving-DET-failed" in [s["verdict"] for s in summary["steps"] if s["step"] == "task-start"]
    assert verdicts["ready-slurp-np4"] == "ready"


def test_the_swap_refuses_a_flight_an_unrecorded_server_and_a_held_lock(host):
    host.up("slurp-np4")
    host.host_free(20.0)
    host.procs(PORT_SERVER, DRIVER)
    result, summary = host.swap("a2t-np3")
    assert result.returncode == 7 and summary["result"] == "refused"
    assert not any(line.startswith("stop") for line in host.log("ss.log"))
    (host.state / "resident").unlink()
    host.procs(PORT_SERVER)
    result, summary = host.swap("a2t-np3")
    assert result.returncode == 10 and {s["step"]: s["verdict"] for s in summary["steps"]}["resident"] == "unrecorded-server"
    host.up("slurp-np4")
    holder = subprocess.Popen(["flock", str(host.home / "serving-swap.lock"), "python3", "-c",
                               "import time; time.sleep(30)"])
    try:
        time.sleep(0.5)
        result, summary = host.swap("a2t-np3")
        assert result.returncode == 9 and summary["result"] == "refused"
    finally:
        holder.kill()
        holder.wait()


def test_the_swap_to_the_resident_geometry_is_a_no_op(host):
    host.up("slurp-np4")
    host.host_free(5.0)
    host.procs(PORT_SERVER, CAMPAIGN)  # a flight on the resident geometry does not block a read-only no-op
    result, summary = host.swap("slurp-np4")
    assert result.returncode == 0 and summary["result"] == "no-op", result.stdout
    assert not any(line.startswith(("-Stop", "-Start")) for line in host.log("ps.log"))


def test_a_swap_from_an_empty_card_starts_the_target_without_a_restore(host):
    host.host_free(20.0)
    result, summary = host.swap("slurp-np4")
    assert result.returncode == 0 and summary["from"] == "none" and summary["result"] == "swapped", result.stdout


# ---------------------------------------------------------------------------- item 5: the queue library


def test_the_queue_library_keeps_every_exit_status(host):
    fake_swap = host.bin / "fake_swap.sh"
    fake_swap.write_text('#!/bin/bash\necho "swap $*"\nexit "$(cat "$FAKE_STATE/swap_rc" 2>/dev/null || echo 0)"\n')
    (host.state / "swap_rc").write_text("3")
    log = host.home / "queue.out"
    driver = host.home / "batch-driver.out"
    driver.write_text("2026-09-27T00:00:00Z driver-start commit abc123\n")
    script = f"""
source "{BATCH}/queue_lib.sh"
ql_init "{log}"
ql_wait_driver_start abc123 0 || ql_halt 3 "no driver"
echo "done" > "{host.home}/batch-done"
ql_wait_terminal; echo "terminal=$?"
ql_swap a2t-np3; echo "swap=$?"
rm -f "{host.home}/batch-done"; touch "{host.home}/batch-STOP"
ql_wait_terminal; echo "terminal=$?"
ql_halt_on_stop; echo "unreachable"
"""
    result = host.run(["bash", "-c", script], SAEA_SERVING_SWAP=str(fake_swap))
    assert result.returncode == 4, result.stdout + result.stderr
    assert "terminal=0" in result.stdout and "swap=3" in result.stdout and "terminal=4" in result.stdout
    assert "unreachable" not in result.stdout
    text = log.read_text()
    assert "swap to a2t-np3 exit 3" in text and "HALT (exit 4)" in text


def test_the_queue_library_halts_when_the_flight_processes_vanish(host):
    host.procs(WORKTREE_PREPARE)  # a model-free worktree run is not the chain
    result = host.run(["bash", "-c", f'source "{BATCH}/queue_lib.sh"\nQL_LOG=/dev/null\nql_wait_terminal; echo "rc=$?"'])
    assert result.stdout.strip().endswith("rc=5")


# ---------------------------------------------------------------------------- the stop-only / start-only window (266-E GPU packets)


def test_stop_only_stops_the_resident_session_starts_nothing_and_never_restores(host):
    host.up("slurp-np4")
    host.procs(PORT_SERVER, SIDECAR)
    result, summary = host.swap("--stop-only")
    assert result.returncode == 0, result.stdout
    assert summary["result"] == "stopped" and summary["target"] == "none" and summary["from"] == "slurp-np4"
    verdicts = {s["step"]: s["verdict"] for s in summary["steps"]}
    assert verdicts["host-memory"] == "not-needed" and verdicts["target-entries"] == "not-needed" and verdicts["stop-only"] == "stopped"
    actions = [line.split()[:2] for line in host.log("ps.log") if not line.startswith("-Status")]
    assert actions == [["-Stop", "SAEA-Serving"], ["-Stop", "SAEA-Monitor"]]       # no -Start of any kind
    assert "host-memory " not in host.log("ss.log")                                   # nothing starts, so no host-memory reading
    assert not (host.state / "resident").exists()                                     # the card is empty
    assert (host.session_dir("slurp-np4") / "session-stop.json").exists()
    assert not (host.home / "serving-swap.pending").exists()


def test_stop_only_dry_run_acts_on_nothing_and_an_empty_card_is_a_no_op(host):
    host.up("think-np4")
    result, summary = host.swap("--stop-only", "--dry-run")
    assert result.returncode == 0 and summary["result"] == "dry-run" and summary["from"] == "think-np4", result.stdout
    assert {line.split()[0] for line in host.log("ps.log")} == {"-Status"}
    assert not any(line.startswith("stop") for line in host.log("ss.log"))
    (host.state / "resident").unlink()
    host.procs()
    result, summary = host.swap("--stop-only")
    assert result.returncode == 0 and summary["result"] == "no-op", result.stdout
    assert not any(line.startswith(("-Stop", "-Start")) for line in host.log("ps.log"))


def test_stop_only_refuses_a_flight_a_target_and_the_other_mode(host):
    host.up("slurp-np4")
    host.procs(PORT_SERVER, CAMPAIGN)
    result, summary = host.swap("--stop-only")
    assert result.returncode == 7 and summary["result"] == "refused"
    assert not any(line.startswith("stop") for line in host.log("ss.log"))
    assert host.run(["bash", str(BATCH / "serving_swap.sh"), "--stop-only", "think-np4"]).returncode == 64
    assert host.run(["bash", str(BATCH / "serving_swap.sh"), "think-np4", "--stop-only", "--start-only"]).returncode == 64
    assert host.run(["bash", str(BATCH / "serving_swap.sh"), "--stop-only", "--restart"]).returncode == 64


def test_start_only_starts_the_target_on_an_empty_card_and_refuses_a_different_resident_geometry(host):
    host.host_free(20.0)
    result, summary = host.swap("think-np4", "--start-only")
    assert result.returncode == 0 and summary["result"] == "swapped" and summary["from"] == "none", result.stdout
    starts = [line.split()[1] for line in host.log("ps.log") if line.startswith("-Start")]
    assert starts == ["SAEA-Serving-THINK", "SAEA-Monitor-THINK"]
    assert (host.state / "resident").read_text() == GEOMETRY["think-np4"][0]
    # the target already resident is the readiness-checked no-op; a different resident geometry is refused untouched
    result, summary = host.swap("think-np4", "--start-only")
    assert result.returncode == 0 and summary["result"] == "no-op"
    result, summary = host.swap("slurp-np4", "--start-only")
    assert result.returncode == 10 and summary["result"] == "refused", result.stdout
    assert {s["step"]: s["verdict"] for s in summary["steps"]}["start-only"] == "refused"
    assert (host.state / "resident").read_text() == GEOMETRY["think-np4"][0]


def test_start_only_failure_tears_the_target_down_and_leaves_the_restore_to_the_caller(host):
    host.host_free(20.0)
    host.on_start("SAEA-Serving-THINK", "refuse", "think-np4")
    result, summary = host.swap("think-np4", "--start-only", "--wait-timeout", "1")
    assert result.returncode == 13 and summary["result"] == "failed-unrestored", result.stdout
    assert not (host.state / "resident").exists()
