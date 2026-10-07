"""Prove precontact waiting never becomes a worker retry or a lower floor."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts/flights/batch/wait_for_start_memory.py"
)


def module():
    spec = importlib.util.spec_from_file_location("start_memory_wait", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Clock:
    now = 0.0

    def time(self):
        return self.now

    def sleep(self, duration):
        assert duration > 0
        self.now += duration


def run(tmp_path, values, **kwargs):
    kwargs.setdefault("floor_gib", 10.0)
    m = module()
    readings = iter(values)
    clock = Clock()
    result = m.wait_for_memory(
        tmp_path / "receipt",
        tmp_path / "STOP",
        14.5,
        60,
        3,
        host_reader=lambda: {"host_free_gb": next(readings)},
        monotonic=clock.time,
        sleep=clock.sleep,
        **kwargs,
    )
    events = [
        json.loads(x)
        for x in (tmp_path / "receipt/events.jsonl").read_text().splitlines()
    ]
    return result, events


def test_transient_low_memory_waits_and_requires_consecutive_samples(tmp_path):
    result, events = run(tmp_path, [14.08, 15, 14.2, 14.5, 15, 15])
    assert result["status"] == "ready" and result["exit_code"] == 0
    assert result["elapsed_seconds"] == 50
    assert [x["consecutive"] for x in events if x["event"] == "sample"] == [
        0,
        1,
        0,
        1,
        2,
        3,
    ]
    assert result["worker_started"] is False
    assert set(p.name for p in tmp_path.iterdir()) == {"receipt"}


def test_persistent_low_memory_times_out_without_start_or_retry(tmp_path):
    result, events = run(tmp_path, [14.0] * 20)
    assert result["status"] == "wait-expired" and result["exit_code"] == 125
    assert result["elapsed_seconds"] == 60
    assert result["worker_started"] is False
    assert not any(x["event"] == "worker-start" for x in events)


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), -1])
def test_invalid_observation_fails_closed_without_second_sample(tmp_path, value):
    result, events = run(tmp_path, [value, 20, 20, 20])
    assert result["status"] == "observation-failed"
    assert len([x for x in events if x["event"] == "sample"]) == 1


def test_material_running_floor_violation_stops_wait(tmp_path):
    result, _ = run(tmp_path, [9.99, 20, 20, 20])
    assert result["status"] == "resource-floor-violation"


def test_existing_stop_is_preserved(tmp_path):
    (tmp_path / "STOP").write_bytes(b"original stop")
    result, events = run(tmp_path, [])
    assert result["status"] == "stop-present"
    assert (tmp_path / "STOP").read_bytes() == b"original stop"
    assert not any(e["event"] == "sample" for e in events)


def test_stop_appearing_during_wait_prevents_admission(tmp_path):
    m = module()
    clock = Clock()

    def pause(duration):
        clock.sleep(duration)
        (tmp_path / "STOP").write_text("owner stop")

    result = m.wait_for_memory(
        tmp_path / "receipt",
        tmp_path / "STOP",
        14.5,
        60,
        3,
        host_reader=lambda: {"host_free_gb": 20},
        monotonic=clock.time,
        sleep=pause,
    )
    assert result["status"] == "stop-present"


@pytest.mark.parametrize(
    "start,seconds,samples",
    [
        (3.99, 60, 3),
        (float("nan"), 60, 3),
        (14.5, 0, 3),
        (14.5, 3601, 3),
        (14.5, 10, 3),
        (14.5, 60, 1),
        (14.5, 60, True),
        (14.5, 60, 2.5),
    ],
)
def test_invalid_policy_refused_before_receipt(tmp_path, start, seconds, samples):
    with pytest.raises(ValueError):
        module().wait_for_memory(
            tmp_path / "receipt", tmp_path / "STOP", start, seconds, samples
        )
    assert not (tmp_path / "receipt").exists()


def test_existing_receipt_is_not_overwritten(tmp_path):
    (tmp_path / "receipt").mkdir()
    (tmp_path / "receipt/old").write_text("preserved")
    with pytest.raises(FileExistsError):
        run(tmp_path, [20, 20, 20])
    assert (tmp_path / "receipt/old").read_text() == "preserved"


def test_reader_exception_and_interruption_do_not_launch(tmp_path):
    m = module()

    def broken():
        raise OSError("unavailable")

    result = m.wait_for_memory(
        tmp_path / "receipt", tmp_path / "STOP", 14.5, 60, 3, host_reader=broken
    )
    assert result["status"] == "observation-failed"

    def interrupted(_):
        raise KeyboardInterrupt()

    result = m.wait_for_memory(
        tmp_path / "other",
        tmp_path / "STOP",
        14.5,
        60,
        3,
        host_reader=lambda: {"host_free_gb": 14},
        sleep=interrupted,
    )
    assert result["status"] == "interrupted"


def test_observation_cannot_cross_deadline_and_grant_start(tmp_path):
    m = module()
    clock = Clock()
    calls = []

    def reader():
        calls.append(1)
        if len(calls) == 3:
            clock.now = 60
        return {"host_free_gb": 20}

    result = m.wait_for_memory(
        tmp_path / "receipt",
        tmp_path / "STOP",
        14.5,
        60,
        3,
        host_reader=reader,
        monotonic=clock.time,
        sleep=clock.sleep,
    )
    assert result["status"] == "wait-expired"


def test_stop_appearing_in_last_read_wins_over_stable_memory(tmp_path):
    m = module()
    clock = Clock()
    calls = []

    def reader():
        calls.append(1)
        if len(calls) == 3:
            (tmp_path / "STOP").write_text("stop during last observation")
        return {"host_free_gb": 20}

    result = m.wait_for_memory(
        tmp_path / "receipt",
        tmp_path / "STOP",
        14.5,
        60,
        3,
        host_reader=reader,
        monotonic=clock.time,
        sleep=clock.sleep,
    )
    assert result["status"] == "stop-present"


def test_stale_sample_does_not_allow_wait_to_mask_observer_failure(
    tmp_path, monkeypatch
):
    m = module()
    monkeypatch.setattr(
        m,
        "_sample",
        lambda *a: {
            "available_gib": 20,
            "reason": "sample-too-old",
            "elapsed_seconds": 11,
        },
    )
    result = m.wait_for_memory(tmp_path / "receipt", tmp_path / "STOP", 14.5, 60, 3)
    assert result["status"] == "observation-failed"


def test_cli_confinement_and_existing_stop(tmp_path, monkeypatch, capsys):
    m = module()
    data = tmp_path / "data"
    stop = tmp_path / "STOP"
    stop.write_text("preserved")
    args = [
        "--data-root",
        str(data),
        "--receipt-dir",
        str(data / "coordination/wait"),
        "--stop-marker",
        str(stop),
        "--start-gib",
        "14.5",
        "--wait-seconds",
        "600",
        "--stable-samples",
        "3",
    ]
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    assert m.main(args) == 125
    assert json.loads(capsys.readouterr().out)["status"] == "stop-present"
    args[args.index("--receipt-dir") + 1] = str(tmp_path / "outside")
    with pytest.raises(SystemExit):
        m.main(args)
    assert not (tmp_path / "outside").exists()
    args[args.index("--receipt-dir") + 1] = str(data / "coordination/other")
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "0")
    with pytest.raises(SystemExit):
        m.main(args)
    assert not (data / "coordination/other").exists()


def test_owner_eight_gib_floor_is_used_by_wait_not_old_ten(tmp_path):
    m = module()
    clock = Clock()
    readings = iter([8, 11, 12.5, 13, 14])
    result = m.wait_for_memory(
        tmp_path / "receipt",
        tmp_path / "STOP",
        12.5,
        60,
        3,
        floor_gib=8,
        host_reader=lambda: {"host_free_gb": next(readings)},
        monotonic=clock.time,
        sleep=clock.sleep,
    )
    assert result["status"] == "ready" and result["running_floor_gib"] == 8


@pytest.mark.parametrize("failure", [False, True])
def test_default_wait_reuses_owned_fresh_windows_observer(tmp_path, monkeypatch, failure):
    m=module(); clock=Clock(); instances=[]
    class Observer:
        def __init__(self): self.calls=0; self.closed=False; instances.append(self)
        def __enter__(self): return self
        def __exit__(self,*args): self.closed=True
        def __call__(self):
            self.calls+=1
            return {"host_free_gb": None if failure else 20, "transport":"fresh-test-pipe", "observer_pid":123, "sequence":self.calls}
    monkeypatch.setattr(m,"WindowsMemoryObserver",Observer,raising=False)
    result=m.wait_for_memory(tmp_path/'receipt',tmp_path/'STOP',14.5,60,3,
                             monotonic=clock.time,sleep=clock.sleep)
    assert len(instances)==1 and instances[0].closed
    assert instances[0].calls==(1 if failure else 3)
    assert result['status']==('observation-failed' if failure else 'ready')
    events=[json.loads(x) for x in (tmp_path/'receipt/events.jsonl').read_text().splitlines()]
    samples=[x for x in events if x['event']=='sample']
    assert [x['observer']['sequence'] for x in samples]==list(range(1,len(samples)+1))
    assert all(x['observer']['transport']=='fresh-test-pipe' for x in samples)


def test_invalid_policy_does_not_create_default_observer(tmp_path,monkeypatch):
    m=module()
    def forbidden(): raise AssertionError('Observer must not be created')
    monkeypatch.setattr(m,'WindowsMemoryObserver',forbidden,raising=False)
    with pytest.raises(ValueError):
        m.wait_for_memory(tmp_path/'receipt',tmp_path/'STOP',3.99,60,3)


def test_explicit_reader_never_creates_default_observer(tmp_path,monkeypatch):
    m=module(); clock=Clock()
    def forbidden(): raise AssertionError('Observer must not be created')
    monkeypatch.setattr(m,'WindowsMemoryObserver',forbidden,raising=False)
    result=m.wait_for_memory(tmp_path/'receipt',tmp_path/'STOP',14.5,60,3,
        host_reader=lambda:{'host_free_gb':20},monotonic=clock.time,sleep=clock.sleep)
    assert result['status']=='ready'


def test_default_observer_closed_if_receipt_already_exists(tmp_path,monkeypatch):
    m=module(); closed=[]; (tmp_path/'receipt').mkdir()
    class Observer:
        def __enter__(self): return self
        def __exit__(self,*args): closed.append(True)
        def __call__(self): raise AssertionError('No read before receipt ownership')
    monkeypatch.setattr(m,'WindowsMemoryObserver',Observer,raising=False)
    with pytest.raises(FileExistsError):m.wait_for_memory(tmp_path/'receipt',tmp_path/'STOP',14.5,60,3)
    assert closed==[True]
