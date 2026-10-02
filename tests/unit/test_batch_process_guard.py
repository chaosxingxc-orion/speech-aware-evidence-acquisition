"""Exercise actual batch routing with isolated fake campaign/scorer boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def run_batch_fixture(tmp_path, worker_exit, changes=None, wait_exit=0):
    driver = (
        Path(__file__).resolve().parents[2] / "scripts/flights/batch/batch_driver.sh"
    )
    loop = driver.read_text().split("for ((i=0; i<N; i++)); do", 1)[1]
    loop = loop.replace("/home/chao/batch-campaign-", str(tmp_path / "batch-campaign-"))
    steps = [
        dict(
            order=i,
            short=f"member-{i}",
            kind="cell",
            experiment=f"experiment-{i}",
            cell=f"cell-{i}",
            campaign_plan=None,
            run_id=f"run-{i}",
            gen_attempt_id=f"attempt-{i}",
            expected_rows=400,
            ceiling_per_row=13,
            notool=False,
            owner="root-fixture",
            process_start_gib=14.5,
            process_floor_gib=10.0,
        )
        for i in (1, 2)
    ]
    for step in steps:
        step.update(changes or {})
    (tmp_path / "queue.json").write_text(json.dumps(steps))
    wrapper = tmp_path / "python-wrapper"
    wrapper.write_text(
        "#!"
        + sys.executable
        + "\n"
        + "import os,sys,json\nargs=sys.argv[1:]\nif '-m' in args:\n with open(os.environ['DISPATCHES'],'a') as f:f.write(json.dumps(args)+'\\n')\n raise SystemExit(int(os.environ['WORKER_EXIT']))\nos.execv(sys.executable,[sys.executable]+args)\n"
    )
    wrapper.chmod(0o755)
    (tmp_path / "batch_inspect.py").write_text(
        'print(\'{"structural_check":"PASS"}\')\n'
    )
    (tmp_path / "wait_for_start_memory.py").write_text(
        "import os,sys,json\nwith open(os.environ['WAITS'],'a') as f:f.write(json.dumps(sys.argv[1:])+'\\n')\nraise SystemExit(int(os.environ['WAIT_EXIT']))\n"
    )
    prefix = r"""
N=2
field() { "$PY" -c 'import json,os,sys; v=json.load(open(os.environ["QUEUE"]))[int(sys.argv[1])].get(sys.argv[2]); print("" if v is None else str(v).lower() if isinstance(v,bool) else v)' "$1" "$2"; }
log() { printf '%s %s\n' "$1" "$2" >> "$STATUS"; }
stop() { log STOP "$1"; exit 9; }
prelaunch() { log test-prelaunch ok; }
sleep() { :; }
"""
    env = dict(
        os.environ,
        PY=str(wrapper),
        QUEUE=str(tmp_path / "queue.json"),
        STATUS=str(tmp_path / "status"),
        SP=str(tmp_path),
        DATA=str(tmp_path),
        REPO=str(tmp_path),
        FLIGHT_COMMIT="fake",
        DONE_MARK=str(tmp_path / "done"),
        SESSION="session",
        LOCK="lock",
        DISPATCHES=str(tmp_path / "dispatches"),
        WORKER_EXIT=str(worker_exit),
        WAIT_EXIT=str(wait_exit),
        WAITS=str(tmp_path / "waits"),
        STOP=str(tmp_path / "STOP"),
    )
    result = subprocess.run(
        ["bash"],
        input=prefix + "for ((i=0; i<N; i++)); do" + loop,
        text=True,
        capture_output=True,
        env=env,
    )
    path = tmp_path / "dispatches"
    dispatches = (
        [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
    )
    return result, dispatches


@pytest.mark.parametrize("worker_exit", [0, 125])
def test_sequential_guarded_steps_preserve_order_and_stop_on_failure(
    tmp_path, worker_exit
):
    result, dispatches = run_batch_fixture(tmp_path, worker_exit)
    assert all(
        x[x.index("-m") + 1]
        == "speech_aware_evidence_acquisition.core.flight.process_guard"
        for x in dispatches
    )
    assert all("--campaign-plan" not in x for x in dispatches)
    assert [x[x.index("--experiment") + 1] for x in dispatches] == (
        ["experiment-1"] if worker_exit else ["experiment-1", "experiment-2"]
    )
    assert len({x[x.index("--receipt-dir") + 1] for x in dispatches}) == len(dispatches)
    assert result.returncode == (9 if worker_exit else 0)
    assert (tmp_path / "done").exists() == (worker_exit == 0)


@pytest.mark.parametrize(
    "changes",
    [
        {"process_start_gib": None},
        {"process_floor_gib": None},
        {"campaign_plan": "plans/multi.json"},
        {"smoke_experiment": "separate-smoke"},
        {"kind": "invalid"},
        {"process_start_gib": None, "process_floor_gib": None},
    ],
)
def test_ambiguous_guarded_step_cannot_dispatch(tmp_path, changes):
    result, dispatches = run_batch_fixture(tmp_path, 0, changes)
    assert result.returncode == 9
    assert dispatches == []
    assert not (tmp_path / "done").exists()


def test_existing_plan_route_keeps_original_cli_arguments(tmp_path):
    result, dispatches = run_batch_fixture(
        tmp_path,
        0,
        {
            "process_start_gib": None,
            "process_floor_gib": None,
            "campaign_plan": "plans/registered.json",
        },
    )
    assert result.returncode == 0 and len(dispatches) == 2
    for args in dispatches:
        assert (
            args[args.index("-m") + 1]
            == "speech_aware_evidence_acquisition.core.flight.cli"
        )
        assert args[args.index("--campaign-plan") + 1] == str(
            tmp_path / "plans/registered.json"
        )
        assert "--experiment" not in args and "--start-gib" not in args


@pytest.mark.parametrize("wait_exit", [0, 125])
def test_memory_wait_is_before_prelaunch_and_never_retries_worker(tmp_path, wait_exit):
    result, dispatches = run_batch_fixture(
        tmp_path,
        0,
        {"process_start_wait_seconds": 600, "process_start_stable_samples": 3},
        wait_exit=wait_exit,
    )
    waits = [json.loads(x) for x in (tmp_path / "waits").read_text().splitlines()]
    assert len(waits) == (1 if wait_exit else 2)
    assert all(x[x.index("--start-gib") + 1] == "14.5" for x in waits)
    assert all(x[x.index("--stable-samples") + 1] == "3" for x in waits)
    assert len(dispatches) == (0 if wait_exit else 2)
    assert result.returncode == (9 if wait_exit else 0)
    status = (tmp_path / "status").read_text()
    if wait_exit:
        assert "test-prelaunch" not in status
    else:
        assert status.index("memory-wait-ok") < status.index("test-prelaunch")


@pytest.mark.parametrize(
    "changes",
    [
        {"process_start_wait_seconds": 600},
        {"process_start_stable_samples": 3},
        {
            "process_start_wait_seconds": 600,
            "process_start_stable_samples": 3,
            "process_start_gib": None,
            "process_floor_gib": None,
            "campaign_plan": "plans/old.json",
        },
    ],
)
def test_incomplete_wait_policy_never_dispatches(tmp_path, changes):
    result, dispatches = run_batch_fixture(tmp_path, 0, changes)
    assert result.returncode == 9 and dispatches == []
