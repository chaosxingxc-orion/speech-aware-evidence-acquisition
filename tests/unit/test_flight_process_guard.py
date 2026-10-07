"""Exercise owned-process resource custody without a model or serving service."""

from pathlib import Path
import json
import os
import subprocess
import sys
import time

import pytest

from speech_aware_evidence_acquisition.core.flight.process_guard import (
    FlightProcessGuardError,
    MemoryPolicy,
    run_guarded,
)

POLICY = MemoryPolicy(
    start_gib=14.5,
    floor_gib=10.0,
    interval_seconds=0.02,
    read_timeout_seconds=0.1,
    stop_grace_seconds=0.1,
)


def command(code):
    return [sys.executable, "-B", "-c", code]


def events(root):
    return [json.loads(x) for x in (root / "events.jsonl").read_text().splitlines()]


@pytest.mark.parametrize(
    "reading", [9.0, 14.49, None, True, float("nan"), float("inf")]
)
def test_start_refuses_before_process_or_attempt_can_exist(tmp_path, reading):
    marker = tmp_path / "started"
    result = run_guarded(
        command(f"open({str(marker)!r}, 'w').write('started')"),
        tmp_path / "guard",
        POLICY,
        host_reader=lambda: {"host_free_gb": reading},
    )
    assert result.exit_code == 125 and result.status == "start-refused"
    assert result.pid is None and not marker.exists()
    assert [x["event"] for x in events(tmp_path / "guard")] == [
        "start-sample",
        "finished",
    ]


def test_success_preserves_arguments_and_exit_status(tmp_path):
    marker = tmp_path / "received"
    cmd = command(
        f"import json,sys;open({str(marker)!r},'w').write(json.dumps(sys.argv[1:]))"
    )
    cmd += ["spaces and punctuation; $(literal)", "second"]
    result = run_guarded(
        cmd, tmp_path / "guard", POLICY, host_reader=lambda: {"host_free_gb": 20.0}
    )
    assert result.status == "completed" and result.exit_code == 0
    assert json.loads(marker.read_text()) == cmd[-2:]
    assert json.loads((tmp_path / "guard/finished.json").read_text())["exit_code"] == 0


def test_child_failure_is_not_retried(tmp_path):
    count = tmp_path / "calls"
    result = run_guarded(
        command(f"open({str(count)!r},'a').write('x');raise SystemExit(7)"),
        tmp_path / "guard",
        POLICY,
        host_reader=lambda: {"host_free_gb": 20.0},
    )
    assert result.status == "worker-failed" and result.exit_code == 7
    assert count.read_text() == "x"


@pytest.mark.parametrize("reading", [9.99, None, False, float("nan")])
def test_pressure_stops_only_the_owned_process_group(tmp_path, reading):
    samples = iter([20.0, reading])
    sibling = subprocess.Popen(
        command("import time;time.sleep(20)"), start_new_session=True
    )
    try:
        result = run_guarded(
            command("import time;time.sleep(20)"),
            tmp_path / "guard",
            POLICY,
            host_reader=lambda: {"host_free_gb": next(samples)},
        )
        assert result.status == "resource-stop" and result.exit_code == 125
        assert result.worker_returncode is not None
        assert sibling.poll() is None
        assert any(x["event"] == "stop-owned-group" for x in events(tmp_path / "guard"))
    finally:
        sibling.terminate()
        sibling.wait(timeout=5)


def test_exact_running_floor_is_admitted(tmp_path):
    samples = iter([20.0, 10.0])
    result = run_guarded(
        command("pass"),
        tmp_path / "guard",
        POLICY,
        host_reader=lambda: {"host_free_gb": next(samples, 10.0)},
    )
    assert result.exit_code == 0


def test_slow_read_is_not_permission_to_start(tmp_path):
    marker = tmp_path / "started"

    def slow():
        time.sleep(0.12)
        return {"host_free_gb": 100.0}

    result = run_guarded(
        command(f"open({str(marker)!r},'w').write('x')"),
        tmp_path / "guard",
        POLICY,
        host_reader=slow,
    )
    assert result.status == "start-refused" and not marker.exists()
    assert events(tmp_path / "guard")[0]["reason"] == "sample-too-old"


def test_reader_exception_is_recorded_without_start(tmp_path):
    def failed():
        raise OSError("fixture unavailable")

    result = run_guarded(
        command("pass"), tmp_path / "guard", POLICY, host_reader=failed
    )
    assert result.status == "start-refused"
    assert events(tmp_path / "guard")[0]["reason"] == "reader-failed:OSError"


def test_existing_receipt_cannot_be_overwritten(tmp_path):
    root = tmp_path / "guard"
    root.mkdir()
    old = root / "finished.json"
    old.write_bytes(b"preserved")
    with pytest.raises(FlightProcessGuardError, match="exists"):
        run_guarded(
            command("pass"), root, POLICY, host_reader=lambda: {"host_free_gb": 20.0}
        )
    assert old.read_bytes() == b"preserved"


@pytest.mark.parametrize(
    "changes",
    [
        dict(start_gib=7),
        dict(floor_gib=3.99),
        dict(start_gib=True),
        dict(interval_seconds=0),
        dict(interval_seconds=11),
        dict(read_timeout_seconds=0),
        dict(read_timeout_seconds=16),
        dict(stop_grace_seconds=0),
        dict(floor_gib=float("nan")),
    ],
)
def test_invalid_or_weaker_policy_is_rejected(changes):
    values = dict(
        start_gib=14.5,
        floor_gib=10.0,
        interval_seconds=5,
        read_timeout_seconds=15,
        stop_grace_seconds=5,
    )
    values.update(changes)
    with pytest.raises(FlightProcessGuardError):
        MemoryPolicy(**values)


def test_hung_observer_stops_child_without_waiting_for_reader(tmp_path):
    calls = []

    def reader():
        calls.append(1)
        if len(calls) > 1:
            time.sleep(2)
        return {"host_free_gb": 20.0}

    before = time.monotonic()
    result = run_guarded(
        command("import time;time.sleep(20)"),
        tmp_path / "guard",
        POLICY,
        host_reader=reader,
    )
    assert result.status == "resource-stop" and time.monotonic() - before < 1


def test_uncooperative_owned_child_is_escalated(tmp_path):
    ready = tmp_path / "ready"
    calls = []

    def reader():
        calls.append(1)
        return {"host_free_gb": 9.0 if ready.exists() else 20.0}

    result = run_guarded(
        command(
            f"import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open({str(ready)!r},'w').write('ready');time.sleep(20)"
        ),
        tmp_path / "guard",
        POLICY,
        host_reader=reader,
    )
    assert result.status == "resource-stop"
    assert [
        e["signal"]
        for e in events(tmp_path / "guard")
        if e["event"] == "stop-owned-group"
    ] == ["SIGTERM", "SIGKILL"]


def test_spawn_failure_is_preserved_without_retry(tmp_path):
    result = run_guarded(
        [str(tmp_path / "missing-executable")],
        tmp_path / "guard",
        POLICY,
        host_reader=lambda: {"host_free_gb": 20},
    )
    assert result.status == "guard-failed" and result.pid is None
    assert events(tmp_path / "guard")[-2]["error_type"] == "FileNotFoundError"


@pytest.mark.parametrize("start", ["4", "14.5"])
def test_guard_main_keeps_exact_single_cell_campaign_arguments(tmp_path, monkeypatch, start):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import (
        process_guard as guard,
        campaign,
    )
    from speech_aware_evidence_acquisition.core.bundle import git_commit

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    calls = []
    monkeypatch.setattr(
        guard,
        "__file__",
        str(
            repo / "src/speech_aware_evidence_acquisition/core/flight/process_guard.py"
        ),
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(
        campaign,
        "load_campaign_cells",
        lambda *a: [
            SimpleNamespace(
                run_id="run", attempt_id="attempt", assert_mode=lambda m: None
            )
        ],
    )
    monkeypatch.setattr(
        campaign,
        "declared_readiness",
        lambda *a: SimpleNamespace(state="ready", reason=""),
    )
    monkeypatch.setattr(git_commit, "require_clean_study_repo", lambda p: "a" * 40)
    monkeypatch.setattr(
        guard,
        "run_guarded",
        lambda *a, **kw: (
            calls.append((a, kw)) or guard.GuardResult("completed", 0, 1, 0)
        ),
    )
    args = [
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
        "--runtime-root",
        "runtime",
        "--lock-path",
        "lock",
        "--experiment",
        "experiment",
        "--owner",
        "owner",
        "--expected-session-id",
        "session",
        "--receipt-dir",
        str(data / "coordination/guard"),
        "--start-gib",
        start,
    ]
    assert guard.main(args) == 0
    assert calls[0][0][2].floor_gib == 4
    cmd = calls[0][0][0]
    assert cmd[:5] == [
        sys.executable,
        "-B",
        "-m",
        "speech_aware_evidence_acquisition.core.flight.cli",
        "campaign",
    ]
    assert (
        "--campaign-plan" not in cmd
        and cmd[cmd.index("--experiment") + 1] == "experiment"
    )
    assert calls[0][1]["identity"]["run_id"] == "run"
    for flag, replacement in [
        ("--repo-root", str(tmp_path / "other-repo")),
        ("--receipt-dir", str(tmp_path / "outside")),
    ]:
        changed = args.copy()
        changed[changed.index(flag) + 1] = replacement
        with pytest.raises(SystemExit):
            guard.main(changed)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    with pytest.raises(SystemExit):
        guard.main(args)
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    assert len(calls) == 1
    monkeypatch.setattr(
        campaign, "load_campaign_cells", lambda *a: [object(), object()]
    )
    with pytest.raises(SystemExit):
        guard.main(args)
    assert len(calls) == 1
    monkeypatch.setattr(
        campaign,
        "load_campaign_cells",
        lambda *a: [SimpleNamespace(assert_mode=lambda m: None)],
    )
    monkeypatch.setattr(
        campaign,
        "declared_readiness",
        lambda *a: SimpleNamespace(state="held", reason="pending owner"),
    )
    with pytest.raises(SystemExit):
        guard.main(args)
    assert len(calls) == 1


def test_stopping_worker_also_stops_term_ignoring_score_child(tmp_path):
    import signal
    import speech_aware_evidence_acquisition.core.flight.process_guard as guard

    ready = tmp_path / "score.pid"
    child_code = f"import os,signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);open({str(ready)!r},'w').write(str(os.getpid()));time.sleep(20)"
    worker_code = f"import subprocess,sys,time;subprocess.Popen([sys.executable,'-B','-c',{child_code!r}]);time.sleep(20)"
    result = None
    try:
        result = guard.run_guarded(
            command(worker_code),
            tmp_path / "guard",
            POLICY,
            host_reader=lambda: {"host_free_gb": 9 if ready.exists() else 20},
        )
        assert result.status == "resource-stop"
        child_pid = int(ready.read_text())
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            stat = Path(f"/proc/{child_pid}/stat")
            if not stat.exists() or stat.read_text().split(") ", 1)[1].startswith("Z"):
                break
            time.sleep(0.01)
        else:
            pytest.fail("owned scoring descendant survived resource stop")
    finally:
        # The fixture's own group is the only possible cleanup target.
        if result is not None:
            try:
                os.killpg(result.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("cmd", [[], [""], [None]])
def test_invalid_command_never_creates_receipt(tmp_path, cmd):
    with pytest.raises(FlightProcessGuardError):
        run_guarded(cmd, tmp_path / "guard", POLICY)
    assert not (tmp_path / "guard").exists()


@pytest.mark.parametrize(
    "running,expected", [(8.0, "completed"), (7.99, "resource-stop")]
)
def test_owner_eight_gib_floor_is_explicit_and_enforced(tmp_path, running, expected):
    policy = MemoryPolicy(
        start_gib=12.5,
        floor_gib=8,
        interval_seconds=0.02,
        read_timeout_seconds=0.1,
        stop_grace_seconds=0.1,
    )
    readings = iter([14.08, running])
    result = run_guarded(
        command("import time;time.sleep(.1)"),
        tmp_path / "guard",
        policy,
        host_reader=lambda: {"host_free_gb": next(readings, running)},
    )
    assert result.status == expected
    assert MemoryPolicy(start_gib=14.5).floor_gib == 4


@pytest.mark.parametrize(
    "fault", [None, "missing", "outside", "run", "stage", "campaign-token"]
)
def test_guard_worker_binds_existing_lease_without_campaign(
    tmp_path, monkeypatch, fault
):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import (
        process_guard as guard,
        campaign,
        lease,
    )
    from speech_aware_evidence_acquisition.core.bundle import git_commit

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    token = data / "coordination/token.json"
    token.parent.mkdir(parents=True)
    document = {
        "schema": "saea-worker-lease-handoff-v1",
        "run_id": "run",
        "attempt_id": "attempt",
        "session_id": "session",
        "token": "synthetic",
    }
    if fault == "run":
        document["run_id"] = "other"
    if fault == "stage":
        document["stage"] = "prompt-fit"
    token.write_text(json.dumps(document))
    calls, modes, leases = [], [], []
    monkeypatch.setattr(
        guard,
        "__file__",
        str(
            repo / "src/speech_aware_evidence_acquisition/core/flight/process_guard.py"
        ),
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    cell = SimpleNamespace(
        run_id="run",
        attempt_id="attempt",
        document={"cell_id": "cell"},
        assert_mode=modes.append,
    )
    monkeypatch.setattr(campaign, "load_campaign_cells", lambda *a: [cell])
    monkeypatch.setattr(
        campaign,
        "declared_readiness",
        lambda *a: SimpleNamespace(state="ready", reason=""),
    )
    monkeypatch.setattr(git_commit, "require_clean_study_repo", lambda p: "a" * 40)
    monkeypatch.setattr(
        lease.WorkerExecutionPolicy,
        "assert_lease",
        lambda self, *a, **kw: leases.append((self, a, kw)),
    )
    monkeypatch.setattr(
        guard,
        "run_guarded",
        lambda *a, **kw: (
            calls.append((a, kw)) or guard.GuardResult("completed", 0, 1, 0)
        ),
    )
    args = [
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
        "--runtime-root",
        "runtime",
        "--lock-path",
        "lock",
        "--experiment",
        "experiment",
        "--owner",
        "owner",
        "--expected-session-id",
        "session",
        "--receipt-dir",
        str(data / "coordination/guard"),
        "--start-gib",
        "12.5",
        "--floor-gib",
        "8",
        "--mode",
        "campaign" if fault == "campaign-token" else "worker",
    ]
    if fault != "missing":
        args += [
            "--lease-token-file",
            str(tmp_path / "outside.json") if fault == "outside" else str(token),
        ]
    if fault:
        with pytest.raises((SystemExit, ValueError)):
            guard.main(args)
        assert calls == []
    else:
        assert guard.main(args) == 0
        cmd = calls[0][0][0]
        assert cmd[4] == "worker" and "campaign" not in cmd
        assert cmd[cmd.index("--cell") + 1] == "cell"
        assert cmd[cmd.index("--lease-token-file") + 1] == str(token)
        assert modes == ["worker"] and len(leases) == 1
        assert calls[0][0][2].start_gib == 12.5 and calls[0][0][2].floor_gib == 8
    assert token.read_text() == json.dumps(document)


@pytest.mark.parametrize(
    "fault", [None, "held-peer", "outside-plan", "external-token", "mixed-selector"]
)
@pytest.mark.parametrize("mode", ["node-panel", "node-panel-worker"])
def test_guard_node_panel_keeps_one_process_and_all_exact_owners(
    tmp_path, monkeypatch, fault, mode
):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import (
        process_guard as guard,
        campaign,
        cli,
    )
    from speech_aware_evidence_acquisition.core.bundle import git_commit

    repo, data = tmp_path / "repo", tmp_path / "data"
    plan = repo / "docs/panel.json"
    calls, checked = [], []
    cells = [
        SimpleNamespace(
            run_id=f"r{i}", attempt_id=f"a{i}", assert_mode=lambda mode: None
        )
        for i in range(8)
    ]
    monkeypatch.setattr(
        guard, "__file__", str(repo / "src/pkg/core/flight/process_guard.py")
    )
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(
        cli,
        "load_node_panel_plan",
        lambda *a, **kw: (tuple(("e", c) for c in cells), "panel", ()),
    )

    def ready(cell, root):
        checked.append(cell.run_id)
        return SimpleNamespace(
            state="held" if fault == "held-peer" and cell is cells[-1] else "ready",
            reason="pending",
        )

    monkeypatch.setattr(campaign, "declared_readiness", ready)
    monkeypatch.setattr(git_commit, "require_clean_study_repo", lambda p: "a" * 40)
    monkeypatch.setattr(
        guard,
        "run_guarded",
        lambda *a, **kw: (
            calls.append((a, kw)) or guard.GuardResult("completed", 0, 1, 0)
        ),
    )
    args = [
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
        "--runtime-root",
        "runtime",
        "--lock-path",
        "lock",
        "--campaign-plan",
        str(tmp_path / "outside.json") if fault == "outside-plan" else str(plan),
        "--owner",
        "root",
        "--expected-session-id",
        "session",
        "--mode",
        mode,
        "--receipt-dir",
        str(data / "coordination/guard"),
        "--start-gib",
        "12.5",
        "--floor-gib",
        "8",
    ]
    if fault == "external-token":
        args += ["--lease-token-file", str(data / "token")]
    if fault == "mixed-selector":
        args += ["--experiment", "e"]
    if fault:
        with pytest.raises(SystemExit):
            guard.main(args)
        assert not calls
    else:
        assert guard.main(args) == 0
        assert checked == [f"r{i}" for i in range(8)]
        cmd = calls[0][0][0]
        assert cmd[4] == mode and "--experiment" not in cmd and "--cell" not in cmd
        assert cmd[cmd.index("--campaign-plan") + 1] == str(plan)
        assert calls[0][1]["identity"]["members"] == [
            {"run_id": c.run_id, "attempt_id": c.attempt_id} for c in cells
        ]
        assert calls[0][1]["identity"]["panel_id"] == "panel"


@pytest.mark.parametrize("fault", [None, "outside", "experiment", "token", "held", "worker", "dirty"])
def test_guard_main_exact_campaign_plan_identity(tmp_path, monkeypatch, fault):
    import hashlib
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard, campaign, cli
    from speech_aware_evidence_acquisition.core.bundle import git_commit
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()
    plan=repo/"campaign.json"
    plan.write_text('{"schema":"saea-campaign-plan-v1","cells":[]}',encoding="utf-8")
    monkeypatch.setattr(guard,"__file__",str(repo/"src/speech_aware_evidence_acquisition/core/flight/process_guard.py"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE","1")
    cells=[SimpleNamespace(run_id=f"run-{i}",attempt_id=f"attempt-{i}",document={"cell_id":f"cell-{i}"},assert_mode=lambda mode:None) for i in (1,2)]
    monkeypatch.setattr(cli,"load_campaign_plan",lambda root,path:tuple((f"experiment-{i}",c) for i,c in enumerate(cells,1)))
    monkeypatch.setattr(campaign,"declared_readiness",lambda cell,data:SimpleNamespace(state="held" if fault=="held" else "ready",reason="fixture"))
    def clean(root):
        if fault=="dirty":raise ValueError("dirty source")
        return "a"*40
    monkeypatch.setattr(git_commit,"require_clean_study_repo",clean)
    calls=[]
    monkeypatch.setattr(guard,"run_guarded",lambda *a,**kw:(calls.append((a,kw)) or guard.GuardResult("completed",0,1,0)))
    args=["--repo-root",str(repo),"--data-root",str(data),"--runtime-root","runtime","--lock-path","lock","--owner","owner","--expected-session-id","session","--receipt-dir",str(data/"coordination/guard"),"--start-gib","4","--floor-gib","4","--campaign-plan",str(plan)]
    if fault=="outside":args[-1]=str(tmp_path/"outside.json")
    elif fault=="experiment":args += ["--experiment","other"]
    elif fault=="token":args += ["--lease-token-file","private-token"]
    elif fault=="worker":args += ["--mode","worker"]
    if fault is not None:
        with pytest.raises((SystemExit,ValueError)):guard.main(args)
        assert not calls
        return
    assert guard.main(args)==0
    command,_,policy=calls[0][0]
    assert "--experiment" not in command and command[command.index("--campaign-plan")+1]==str(plan)
    identity=calls[0][1]["identity"]
    assert identity["campaign_plan"]=={"relpath":"campaign.json","sha256":hashlib.sha256(plan.read_bytes()).hexdigest()}
    assert identity["members"]==[{"experiment":f"experiment-{i}","cell":f"cell-{i}","run_id":f"run-{i}","attempt_id":f"attempt-{i}"}for i in (1,2)]
    assert identity["study_head"]=="a"*40 and policy.start_gib==policy.floor_gib==4
