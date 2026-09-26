"""Resource freshness follows boot time even when UTC is corrected."""

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.session import resource_guard as guard

SESSION = SimpleNamespace(session_id="clock-fixture", pid=41, started_at="frozen")
LIMITS = {
    "schema": "saea-serving-resource-limits-v1",
    "windows_start_gib": 32, "windows_admit_gib": 12, "windows_stop_gib": 10,
    "gpu_admit_free_mib": 2048, "gpu_stop_free_mib": 1024,
    "max_sample_age_seconds": 15,
}


def publish(path, *, wall=(1000, 999), elapsed=(100, 101), host=25):
    wall, elapsed = iter(wall), iter(elapsed)
    return guard.publish_sample(
        path, SESSION, LIMITS, now=lambda: next(wall),
        elapsed_clock=lambda: next(elapsed), boot_id_reader=lambda: "boot-a",
        host_reader=lambda: {"host_free_gb": host},
        gpu_reader=lambda: {"memory_free_mib": 3706},
    )


@pytest.mark.parametrize("wall", [(1000, 999), (1000, 1600)])
def test_utc_adjustment_does_not_close_a_fresh_healthy_observation(tmp_path, wall):
    doc = publish(tmp_path, wall=wall)
    assert doc["decision"] == "admit"
    assert (doc["sampled_at"], doc["completed_at"]) == wall
    guard.assert_admission(
        tmp_path, SESSION, LIMITS, now=lambda: 10,
        elapsed_clock=lambda: 102, boot_id_reader=lambda: "boot-a",
    )


def test_real_sampling_delay_still_stops_when_wall_time_is_flat(tmp_path):
    doc = publish(tmp_path, wall=(1000, 1000), elapsed=(100, 117))
    assert doc["decision"] == "stop"
    assert doc["reasons"] == ["observation-too-old"]


@pytest.mark.parametrize("clock,boot", [(116, "boot-a"), (99, "boot-a"), (102, "boot-b")])
def test_stale_future_or_other_boot_receipt_never_dispatches(tmp_path, clock, boot):
    publish(tmp_path)
    calls = []
    transport = guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw), tmp_path, SESSION, LIMITS,
        now=lambda: 1000, elapsed_clock=lambda: clock, boot_id_reader=lambda: boot,
    )
    with pytest.raises(guard.ResourceAdmissionError):
        transport(b"must not post")
    assert calls == []


def test_backward_wall_time_cannot_hide_actual_memory_pressure(tmp_path):
    doc = publish(tmp_path, host=9)
    assert doc["decision"] == "stop"
    assert doc["reasons"] == ["windows-hard-floor"]


@pytest.mark.parametrize("change", ["missing", "kind", "end", "nan"])
def test_new_clock_receipt_cannot_fall_back_to_wall_time(tmp_path, change):
    doc = publish(tmp_path, wall=(1000, 1001))
    if change == "missing":
        doc.pop("elapsed_clock")
    elif change == "kind":
        doc["elapsed_clock"]["kind"] = "unsupported"
    elif change == "end":
        doc["elapsed_clock"]["completed_at"] = 99
    else:
        doc["elapsed_clock"]["sampled_at"] = float("nan")
    (tmp_path / guard.SNAPSHOT_NAME).write_text(json.dumps(doc))
    with pytest.raises(guard.ResourceAdmissionError):
        guard.assert_admission(
            tmp_path, SESSION, LIMITS, now=lambda: 1002,
            elapsed_clock=lambda: 102, boot_id_reader=lambda: "boot-a",
        )


def test_fresh_clock_transport_preserves_original_bytes_once(tmp_path):
    publish(tmp_path)
    calls = []
    transport = guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw) or b"ok", tmp_path, SESSION, LIMITS,
        now=lambda: 900, elapsed_clock=lambda: 102, boot_id_reader=lambda: "boot-a",
    )
    assert transport(b"original request") == b"ok"
    assert calls == [b"original request"]
