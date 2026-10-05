"""Prove fresh observation and owned-process cleanup without Windows or a model."""

import json
import subprocess
import sys
import threading
import time

import pytest

from speech_aware_evidence_acquisition.core.session.windows_memory import WindowsMemoryObserver


def fixture_observer(change="", *, timeout=0.5, spawn_delay=0):
    children = []
    source = """
import json,os,sys,time
for line in sys.stdin:
    if line.strip() == 'STOP': break
    q=json.loads(line)
    value=dict(nonce=q['nonce'],sequence=q['sequence'],sampled_at=time.time()*1000,
               available_bytes=20*1024**3,total_bytes=64*1024**3,observer_pid=os.getpid(),
               sample_elapsed_ms=0.01)
    CHANGE
    print(json.dumps(value),flush=True)
""".replace("    CHANGE", "    " + change)

    def spawn(*args, **kwargs):
        time.sleep(spawn_delay)
        p = subprocess.Popen([sys.executable, "-B", "-c", source], **kwargs)
        children.append(p)
        return p

    return WindowsMemoryObserver(popen=spawn, executable="fixture", timeout=timeout), children


def test_fresh_reads_reuse_one_process_and_close_it():
    observer, children = fixture_observer()
    with observer:
        a, b = observer(), observer()
        assert a['host_free_gb'] == b['host_free_gb'] == 20
        assert a['observer_pid'] == b['observer_pid']
        assert a['sequence'] == 1 and b['sequence'] == 2
        assert b['sampled_at'] >= a['sampled_at']
    assert len(children) == 1 and children[0].poll() == 0
    assert observer()['host_free_gb'] is None


@pytest.mark.parametrize('change', [
    "value['nonce']='wrong'", "value['sequence']-=1",
    "value['sequence']=True", "value['sample_elapsed_ms']=-1",
    "value['sample_elapsed_ms']=20000", "value.pop('sample_elapsed_ms')", "value['sampled_at']=float('nan')",
    "value['available_bytes']=-1", "value['available_bytes']=True",
    "value['available_bytes']=100*1024**3", "value['total_bytes']=0",
    "value['observer_pid']=0", "value=[]", "value.pop('total_bytes')",
    "print('invalid',flush=True);sys.exit(0)",
    "print('x'*5000,flush=True);sys.exit(0)", "sys.exit(0)",
    "print('{}\\n{}',flush=True);sys.exit(0)",
    "value['observer_pid']+=q['sequence']",
])
def test_invalid_response_latches_closed_without_respawn(change):
    observer, children = fixture_observer(change)
    with observer:
        a = observer()
        if change == "value['observer_pid']+=q['sequence']":
            assert a['host_free_gb'] == 20
            a = observer()
        assert a['host_free_gb'] is None and a['host_memory_error']
        assert observer()['host_free_gb'] is None
    assert len(children) == 1 and children[0].poll() is not None


def test_timeout_is_bounded_and_does_not_return_old_memory():
    observer, children = fixture_observer("time.sleep(10) if q['sequence']>1 else None", timeout=.1)
    with observer:
        assert observer()['host_free_gb'] == 20
        started = time.monotonic()
        assert observer()['host_memory_error'] == 'timeout'
        assert time.monotonic()-started < .5
        assert observer()['host_free_gb'] is None
    assert children[0].poll() is not None


def test_close_during_delayed_spawn_cleans_up_late_child():
    observer, children = fixture_observer(spawn_delay=.15)
    t = threading.Thread(target=observer)
    t.start()
    time.sleep(.04)
    observer.close()
    t.join(timeout=3)
    assert not t.is_alive() and len(children) == 1
    assert children[0].poll() is not None


def test_spawn_error_is_latched():
    calls = []
    def failed(*args, **kwargs):
        calls.append(1)
        raise OSError('synthetic')
    with WindowsMemoryObserver(popen=failed, executable='fixture') as observer:
        assert observer()['host_free_gb'] is None
        assert observer()['host_free_gb'] is None
    assert len(calls) == 1


@pytest.mark.parametrize('timeout', [0, -1, 9, True, float('nan')])
def test_invalid_deadlines_cannot_weaken_guard(timeout):
    with pytest.raises(ValueError):
        WindowsMemoryObserver(timeout=timeout)


def test_invalid_live_observation_stops_owned_worker_and_closes_observer(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard
    observer, children = fixture_observer("value['nonce']='wrong' if q['sequence']>1 else q['nonce']")
    monkeypatch.setattr(guard, 'WindowsMemoryObserver', lambda: observer)
    result = guard.run_guarded([sys.executable,'-B','-c','import time;time.sleep(20)'],
                              tmp_path/'guard',guard.MemoryPolicy(20,8,.01,1,.01))
    assert result.status=='resource-stop' and result.worker_returncode is not None
    assert len(children)==1 and children[0].poll() is not None
    samples=[json.loads(x) for x in (tmp_path/'guard/events.jsonl').read_text().splitlines()]
    assert samples[0]['observer']['transport']=='persistent-windows-physical-memory-v1'
    assert samples[2]['reader_error']=='ValueError'


def test_default_guard_owns_observer_on_success_and_refusal(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard
    for index, reading in enumerate((20, 5)):
        calls = []
        class Observer:
            def __enter__(self): return self
            def __exit__(self, *args): calls.append('closed')
            def __call__(self): return {'host_free_gb':reading}
        monkeypatch.setattr(guard, 'WindowsMemoryObserver', Observer)
        r = guard.run_guarded([sys.executable,'-B','-c','pass'],tmp_path/str(index),
                              guard.MemoryPolicy(20,8, .01))
        assert r.status == ('completed' if reading==20 else 'start-refused')
        assert calls == ['closed']


@pytest.mark.parametrize('change,code', [
    ("value['nonce']='PRIVATE_NONCE'", 'response-identity-or-type'),
    ("value['sample_elapsed_ms']=-1", 'request-causal-freshness'),
    ("value['available_bytes']=-1", 'physical-memory-range'),
    ("value['observer_pid']=0", 'observer-process-identity'),
    ("print('PRIVATE_BROKEN_JSON',flush=True);sys.exit(0)", 'invalid-json'),
])
def test_failures_preserve_bounded_diagnostics_without_raw_response(change, code):
    observer, children = fixture_observer(change)
    with observer:
        value = observer()
        assert value['host_free_gb'] is None
        diagnostic = value['host_memory_diagnostics']
        assert diagnostic['failure_code'] == code
        assert diagnostic['roundtrip_seconds'] >= 0
        assert 'PRIVATE' not in json.dumps(value)
        assert observer()['host_memory_diagnostics'] == diagnostic
    assert children[0].poll() is not None


def test_guard_receipt_keeps_clock_diagnostics(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard
    observer, _ = fixture_observer("value['sample_elapsed_ms']=-1 if q['sequence']>1 else .01")
    monkeypatch.setattr(guard, 'WindowsMemoryObserver', lambda: observer)
    result = guard.run_guarded([sys.executable,'-B','-c','import time;time.sleep(20)'],
                              tmp_path/'guard',guard.MemoryPolicy(20,8,.01,1,.01))
    assert result.status == 'resource-stop'
    events = [json.loads(x) for x in (tmp_path/'guard/events.jsonl').read_text().splitlines()]
    failed = next(e for e in events if e.get('reason') == 'windows-reading-unavailable')
    assert failed['reader_diagnostics']['failure_code'] == 'request-causal-freshness'
    assert failed['reader_diagnostics']['sample_elapsed_ms'] == -1


@pytest.mark.parametrize('offset', [-86400000, 86400000])
def test_independent_wallclock_offset_does_not_reject_causally_fresh_sample(offset):
    observer, _ = fixture_observer(f"value['sampled_at']+={offset}")
    with observer:
        assert observer()['host_free_gb'] == 20
        assert observer()['sequence'] == 2


@pytest.mark.parametrize('elapsed', [True, float('nan'), float('inf'), 1000])
def test_invalid_or_impossible_same_clock_elapsed_fails_closed(elapsed):
    expression = repr(elapsed) if isinstance(elapsed, (bool, int)) else f"float('{elapsed}')"
    observer, _ = fixture_observer(f"value['sample_elapsed_ms']={expression}")
    with observer:
        assert observer()['host_free_gb'] is None
        assert observer()['host_free_gb'] is None


def test_windows_script_samples_after_request_and_uses_same_clock_duration():
    from speech_aware_evidence_acquisition.core.session.windows_memory import SCRIPT
    positions = [SCRIPT.index(token) for token in (
        '$q=ConvertFrom-Json $line', 'Stopwatch]::StartNew()',
        '$free=$info.AvailablePhysicalMemory', '$total=$info.TotalPhysicalMemory',
        '$watch.Stop()', '[Console]::Out.WriteLine')]
    assert positions == sorted(positions)
    assert 'sample_elapsed_ms=$watch.Elapsed.TotalMilliseconds' in SCRIPT


def test_guard_receipt_preserves_causal_freshness_proof(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import process_guard as guard
    observer, _ = fixture_observer("value['sampled_at']-=86400000")
    monkeypatch.setattr(guard, 'WindowsMemoryObserver', lambda: observer)
    result = guard.run_guarded([sys.executable, '-B', '-c', 'pass'],
                              tmp_path/'guard', guard.MemoryPolicy(20,8,.01))
    assert result.status == 'completed'
    events = [json.loads(x) for x in (tmp_path/'guard/events.jsonl').read_text().splitlines()]
    assert events[0]['observer']['freshness'] == 'request-causal-monotonic-v1'
    assert events[0]['observer']['sample_elapsed_ms'] == .01
