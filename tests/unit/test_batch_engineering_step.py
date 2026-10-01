"""Exercise the real batch loop with isolated fake worker and inspector boundaries."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "mutation",
    [
        None,
        {"expected_rows": 400},
        {"campaign_plan": "forbidden.json"},
        {"smoke_run_id": "different"},
    ],
)
def test_engineering_queue_never_dispatches_campaign(tmp_path, mutation):
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
    if mutation:
        assert result.returncode == 9
        assert "test-smoke-worker" not in events
        assert not (tmp_path / "done").exists()
    else:
        assert result.returncode == 0, result.stderr
        assert "test-smoke-worker" in events and "smoke-inspect" in events
        assert '"engineering_only":true' in events
        assert (tmp_path / "done").exists()
