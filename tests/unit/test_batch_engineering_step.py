"""Exercise the real batch loop with isolated fake worker and inspector boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "mutation,success",
    [
        (None, True),
        ({"expected_rows": 400}, False),
        ({"campaign_plan": "forbidden.json"}, False),
        ({"smoke_run_id": "different"}, False),
        ({"process_start_gib": 12.5, "process_floor_gib": 8, "process_start_wait_seconds": 600, "process_start_stable_samples": 3}, True),
    ],
)
def test_engineering_queue_never_dispatches_campaign(tmp_path, mutation, success):
    driver = (
        Path(__file__).resolve().parents[2] / "scripts/flights/batch/batch_driver.sh"
    )
    loop = driver.read_text().split("for ((i=0; i<N; i++)); do", 1)[1]
    step = dict(
        order=1,
        short="engineering-test",
        kind="engineering",
        experiment="e",
        cell="c",
        smoke_experiment="e",
        smoke_cell="c",
        campaign_plan=None,
        run_id="r",
        smoke_run_id="r",
        gen_attempt_id="a",
        smoke_attempt_id="a",
        expected_rows=4,
        ceiling_per_row=13,
        notool=False,
        owner="test",
    )
    step.update(mutation or {})
    (tmp_path / "queue.json").write_text(json.dumps([step]))
    (tmp_path / "batch_inspect.py").write_text(
        'import json; print(json.dumps({"structural_check": "PASS"}))\n'
    )
    (tmp_path / "wait_for_start_memory.py").write_text('print("{}")\n')
    prefix = r"""
N=1
field() { "$PY" -c 'import json,os,sys; v=json.load(open(os.environ["QUEUE"]))[int(sys.argv[1])].get(sys.argv[2]); print("" if v is None else str(v).lower() if isinstance(v,bool) else v)' "$1" "$2"; }
log() { printf '%s %s\n' "$1" "$2" >> "$STATUS"; }
stop() { log STOP "$1"; exit 9; }
prelaunch() { log test-prelaunch ok; }
fly_smoke() { log test-smoke-worker ok; }
sleep() { :; }
"""
    env = dict(
        os.environ,
        PY=sys.executable,
        QUEUE=str(tmp_path / "queue.json"),
        STATUS=str(tmp_path / "status"),
        SP=str(tmp_path),
        DATA=str(tmp_path),
        REPO=str(tmp_path),
        FLIGHT_COMMIT="fake",
        DONE_MARK=str(tmp_path / "done"),
    )
    result = subprocess.run(
        ["bash"],
        input=prefix + "for ((i=0; i<N; i++)); do" + loop,
        env=env,
        text=True,
        capture_output=True,
    )
    events = (tmp_path / "status").read_text()
    assert "arm-start" not in events
    assert "arm-exit" not in events
    if not success:
        assert result.returncode == 9
        assert "test-smoke-worker" not in events
        assert not (tmp_path / "done").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert "test-smoke-worker" in events and "smoke-inspect" in events
        assert '"engineering_only":true' in events
        assert (tmp_path / "done").exists()


@pytest.mark.parametrize("diagnostics", [False, True])
@pytest.mark.parametrize("guarded,worker_exit", [(True, 0), (True, 125), (False, 0)])
def test_real_smoke_function_guards_worker_and_preserves_failed_lease(tmp_path, guarded, worker_exit, diagnostics):
    driver = Path(__file__).resolve().parents[2] / "scripts/flights/batch/batch_driver.sh"
    source = driver.read_text()
    function = source[source.index("fly_smoke() {"):source.index("for ((i=0; i<N; i++)); do")]
    function = function.replace("/home/chao/batch-smoke-", str(tmp_path / "batch-smoke-"))
    wrapper = tmp_path / "python-wrapper"
    wrapper.write_text(
        "#!" + sys.executable + "\n"
        "import os,sys,json\nfrom pathlib import Path\n"
        "args=sys.argv[1:]\nmodule=args[args.index('-m')+1]\n"
        "if module.endswith('lease_cli'):\n"
        " token=Path(os.environ['DATA'])/args[args.index('--token-output')+1]\n"
        " token.parent.mkdir(parents=True,exist_ok=True);token.write_text('{}')\n"
        " command=sys.stdin.readline().strip()\n"
        " Path(os.environ['LEASE_COMMAND']).write_text(command)\n"
        " if command=='release':token.unlink()\n"
        " raise SystemExit(0 if command=='release' else 2)\n"
        "with open(os.environ['DISPATCHES'],'a') as f:f.write(json.dumps(args)+'\\n')\n"
        "raise SystemExit(int(os.environ['WORKER_EXIT']))\n"
    )
    wrapper.chmod(0o755)
    prefix = r"""
log() { printf '%s %s\n' "$1" "$2" >> "$STATUS"; }
stop() { log STOP "$1"; exit 9; }
sleep() { /bin/sleep .01; }
"""
    env = dict(os.environ, PY=str(wrapper), REPO=str(tmp_path), DATA=str(tmp_path),
               LOCK="synthetic-lock", SESSION="synthetic-session", STATUS=str(tmp_path / "status"),
               DISPATCHES=str(tmp_path / "dispatches"), LEASE_COMMAND=str(tmp_path / "lease-command"),
               WORKER_EXIT=str(worker_exit), process_start="12.5" if guarded else "",
               process_floor="8" if guarded else "")
    result = subprocess.run(["bash"], input=prefix + function + ('\ndiagnostic_args=(--memory-diagnostics)\n' if diagnostics else '\ndiagnostic_args=()\n') + 'fly_smoke 1 e c owner\n',
                            text=True, env=env, capture_output=True, timeout=10)
    commands = [json.loads(x) for x in (tmp_path / "dispatches").read_text().splitlines()]
    assert len(commands) == 1
    cmd = commands[0]
    module = cmd[cmd.index("-m") + 1]
    assert module.endswith("process_guard" if guarded else "flight.cli")
    if guarded:
        assert cmd[cmd.index("--mode") + 1] == "worker"
        assert cmd[cmd.index("--start-gib") + 1] == "12.5"
        assert cmd[cmd.index("--floor-gib") + 1] == "8"
    assert ("--memory-diagnostics" in cmd) == (guarded and diagnostics)
    assert "campaign" not in cmd and "--lease-token-file" in cmd
    failed = guarded and worker_exit != 0
    assert result.returncode == (9 if failed else 0), result.stderr
    assert (tmp_path / "lease-command").read_text() == ("preserve" if failed else "release")
    assert (tmp_path / "coordination/c.worker-lease.json").exists() == failed
