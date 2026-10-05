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
               available_bytes=20*1024**3,total_bytes=64*1024**3,observer_pid=os.getpid())
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
    "value['sequence']=True", "value['sampled_at']-=20000",
    "value['sampled_at']+=20000", "value['sampled_at']=float('nan')",
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
