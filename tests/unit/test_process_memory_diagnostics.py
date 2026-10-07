"""Offline process-memory identity and bounded diagnostic coverage."""
import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.core.flight.process_guard import ProcessMemoryDiagnostics, _bounded_proc_read

def stat(pid, start):
    return f"{pid} (name with spaces) S " + " ".join(["0"] * 18 + [str(start)])

def fixture(root, pid=123, start=44):
    root.mkdir(exist_ok=True)
    (root / "meminfo").write_text("MemFree: 12 kB\nMemAvailable: 34 kB\nCached: 56 kB\n")
    d=root/str(pid); d.mkdir(exist_ok=True)
    (d/"stat").write_text(stat(pid,start))
    (d/"smaps_rollup").write_text("Rss: 10 kB\nPss: 8 kB\nSwap: 2 kB\nPrivate_Clean: 7 kB\n")
    return d

def test_fields_missing_and_identity_reuse(tmp_path):
    d=fixture(tmp_path)
    collector=ProcessMemoryDiagnostics(proc_root=tmp_path, server_pid=123)
    row=collector.collect(None)
    assert row["meminfo_kib"]["MemAvailable"]==34
    assert row["meminfo_kib"]["Shmem"] is None
    assert row["server"]["memory_kib"]=={"Rss":10,"Pss":8,"Swap":2}
    (d/"stat").write_text(stat(123,45))
    row=collector.collect(None)
    assert row["server"]["error"]=="pid-identity-changed"
    assert "memory_kib" not in row["server"]

def test_disappeared_pid(tmp_path):
    fixture(tmp_path)
    collector=ProcessMemoryDiagnostics(proc_root=tmp_path, server_pid=123)
    collector.collect(None)
    (tmp_path/"123/stat").unlink()
    assert collector.collect(None)["server"]["error"]=="FileNotFoundError"

def test_bounded_read(tmp_path):
    p=tmp_path/"large";p.write_bytes(b"x"*100)
    with pytest.raises(ValueError,match="bounded"):
        _bounded_proc_read(p,limit=10)

def test_worker_and_server_separate(tmp_path):
    fixture(tmp_path,123,44);fixture(tmp_path,124,55)
    row=ProcessMemoryDiagnostics(proc_root=tmp_path,server_pid=123).collect(124)
    assert row["worker"]["identity"]=={"pid":124,"starttime_ticks":55}
    assert row["server"]["identity"]=={"pid":123,"starttime_ticks":44}


def test_one_pending_thread_no_wait(tmp_path):
    import threading
    collector=ProcessMemoryDiagnostics(proc_root=tmp_path)
    release=threading.Event()
    collector.collect=lambda pid: (release.wait(), {"ok":True})[1]
    collector.start(None); thread=collector.thread
    for _ in range(20):
        collector.start(123)
        assert collector.thread is thread
        assert collector.snapshot()["pending"] is True
    release.set();thread.join(timeout=1)
    assert collector.snapshot()["ok"] is True

@pytest.mark.skipif(__import__("os").name != "posix", reason="owned POSIX group")
def test_pending_diagnostics_cannot_delay_floor_stop(tmp_path):
    import sys,threading,time
    from speech_aware_evidence_acquisition.core.flight.process_guard import run_guarded,MemoryPolicy
    collector=ProcessMemoryDiagnostics(proc_root=tmp_path)
    release=threading.Event();collector.collect=lambda pid: (release.wait(),{})[1]
    values=iter([20.,1.])
    before=time.monotonic()
    try:
        result=run_guarded([sys.executable,"-B","-c","import time;time.sleep(20)"],
            tmp_path/"guard",MemoryPolicy(4,4,.01,.1,.01),
            host_reader=lambda:{"host_free_gb":next(values)},diagnostics=collector)
        assert result.status=="resource-stop" and result.exit_code==125
        assert time.monotonic()-before<2
        rows=[json.loads(x) for x in (tmp_path/"guard/events.jsonl").read_text().splitlines()]
        assert rows[0]["memory_diagnostics"]["pending"] is True
    finally:
        release.set()

@pytest.mark.skipif(__import__("os").name != "posix", reason="owned POSIX group")
def test_disabled_receipts_have_no_new_keys(tmp_path):
    import sys
    from speech_aware_evidence_acquisition.core.flight.process_guard import run_guarded,MemoryPolicy
    run_guarded([sys.executable,"-B","-c","pass"],tmp_path/"guard",MemoryPolicy(4),
                host_reader=lambda:{"host_free_gb":20.})
    rows=[json.loads(x) for x in (tmp_path/"guard/events.jsonl").read_text().splitlines()]
    assert all("memory_diagnostics" not in x for x in rows)
    assert "memory_diagnostics" not in json.loads((tmp_path/"guard/finished.json").read_text())

def test_unavailable_meminfo_and_fields_are_not_zero(tmp_path):
    d=fixture(tmp_path)
    (tmp_path/"meminfo").unlink();(d/"smaps_rollup").write_text("Rss: invalid kB\n")
    row=ProcessMemoryDiagnostics(proc_root=tmp_path,server_pid=123).collect(None)
    assert row["meminfo_error"]=="FileNotFoundError"
    assert row["server"]["memory_kib"]=={"Rss":None,"Pss":None,"Swap":None}


def test_pid_changes_during_smaps_read(tmp_path,monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard
    fixture(tmp_path)
    values=iter([44,45])
    monkeypatch.setattr(guard,"_proc_starttime",lambda root,pid:next(values))
    row=ProcessMemoryDiagnostics(proc_root=tmp_path,server_pid=123).collect(None)
    assert row["server"]["error"]=="pid-identity-changed"
    assert "memory_kib" not in row["server"]

def test_bounded_meminfo_error_and_bad_stat(tmp_path):
    d=fixture(tmp_path)
    (tmp_path/"meminfo").write_bytes(b"x"*65537)
    (d/"stat").write_text("invalid")
    row=ProcessMemoryDiagnostics(proc_root=tmp_path,server_pid=123).collect(None)
    assert row["meminfo_error"]=="ValueError"
    assert row["server"]["error"]=="ValueError"

def test_collector_exception_is_separate(tmp_path):
    collector=ProcessMemoryDiagnostics(proc_root=tmp_path)
    def fail(pid):
        raise RuntimeError("diagnostic failure")
    collector.collect=fail;collector.start(None);collector.thread.join(timeout=1)
    assert collector.snapshot()["error"]=="RuntimeError"


@pytest.mark.skipif(__import__("os").name != "posix", reason="owned POSIX group")
@pytest.mark.parametrize("values,expected",[([20.,1.],"resource-stop"),([20.]*20,"completed")])
def test_diagnostic_scheduling_and_snapshot_failures_do_not_control(tmp_path,values,expected):
    import sys
    from speech_aware_evidence_acquisition.core.flight.process_guard import run_guarded,MemoryPolicy
    class Broken:
        def start(self,pid): raise RuntimeError("thread unavailable")
        def snapshot(self): raise ValueError("snapshot unavailable")
    readings=iter(values)
    r=run_guarded([sys.executable,"-B","-c","import time;time.sleep(.03)"],tmp_path/"guard",
        MemoryPolicy(4,4,.01,.1,.01),host_reader=lambda:{"host_free_gb":next(readings)},diagnostics=Broken())
    assert r.status==expected
    rows=[json.loads(x) for x in (tmp_path/"guard/events.jsonl").read_text().splitlines()]
    assert all(x["memory_diagnostics"]["snapshot_error"]=="ValueError" for x in rows)
    assert rows[0]["memory_diagnostics"]["scheduling_error"]=="RuntimeError"


def test_registered_service_pid_binding_and_error_isolation(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.process_guard import _registered_diagnostics
    p=tmp_path/"serving/registered/session-receipt.json";p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"session_id":"registered","pid":123,"argv":["never collected"]}))
    collector=_registered_diagnostics(tmp_path,"registered")
    assert collector.server_pid==123 and collector.server_error is None
    p.write_text(json.dumps({"session_id":"foreign","pid":124}))
    collector=_registered_diagnostics(tmp_path,"registered")
    assert collector.server_pid is None and collector.server_error=="ValueError"
    assert _registered_diagnostics(tmp_path,"../../outside").server_error=="ValueError"
