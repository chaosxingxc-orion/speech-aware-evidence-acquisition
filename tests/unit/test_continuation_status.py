"""Status reporting over synthetic batch metadata only."""

import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "flights" / "batch"
sys.path.insert(0, str(SCRIPT))
from continuation_status import StatusReadError, _process_snapshot, summarize  # noqa: E402


def fixture(tmp_path, events, *, tail=""):
    queue = tmp_path / "queue.json"
    status = tmp_path / "status.jsonl"
    data = tmp_path / "data"
    queue.write_text(json.dumps([
        {"order": 1, "short": "first", "cell": "cell-a", "run_id": "RUN-A", "gen_attempt_id": "attempt-a"},
        {"order": 2, "short": "second", "cell": "cell-b", "run_id": "RUN-B", "gen_attempt_id": "attempt-b"},
    ]), encoding="utf-8")
    status.write_text("".join(json.dumps({"event": event, "detail": detail}) + "\n" for event, detail in events) + tail, encoding="utf-8")
    return queue, status, data


def test_running_with_completed_step_and_sealed_metadata(tmp_path):
    queue, status, data = fixture(tmp_path, [
        ("step-done", {"step": 1, "short": "first"}),
        ("step-start", {"step": 2, "short": "second"}),
        ("arm-start", {"step": 2, "log": "/private/raw.log"}),
    ])
    attempt = data / "attempts" / "RUN-B" / "attempt-b.json"
    attempt.parent.mkdir(parents=True)
    attempt.write_text(json.dumps({"state": "FINALIZED", "actual": {"secret": "never report"}}))
    manifest = data / "runs" / "RUN-B" / "attempt-b" / "seal.run-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"status": "COMPLETED", "output": "never report"}))
    result = summarize(queue, status, data)
    assert result == {
        "state": "running-unverified", "handoff_required": False,
        "current_step": {"order": 2, "short": "second", "cell": "cell-b"},
        "completed_steps": [{"order": 1, "short": "first", "cell": "cell-a"}],
        "reason": None, "attempt_state": "FINALIZED", "manifest_status": "COMPLETED",
        "ignored_incomplete_tail": False, "status_parse_error": None,
    }
    assert "secret" not in json.dumps(result) and "raw.log" not in json.dumps(result)


def test_stop_survives_incomplete_final_line(tmp_path):
    queue, status, data = fixture(tmp_path, [
        ("step-start", {"step": 1, "short": "first"}),
        ("STOP", "GPU ramp preflight failed before step 1"),
    ], tail='{"event":"driver-done",')
    result = summarize(queue, status, data)
    assert result["state"] == "handoff-required"
    assert result["handoff_required"] is True
    assert result["reason"] == "GPU ramp preflight failed before step 1"
    assert result["ignored_incomplete_tail"] is True


def test_aborted_attempt_requires_handoff(tmp_path):
    queue, status, data = fixture(tmp_path, [("step-start", {"step": 1, "short": "first"})])
    attempt = data / "attempts" / "RUN-A" / "attempt-a.json"
    attempt.parent.mkdir(parents=True)
    attempt.write_text(json.dumps({"state": "ABORTED", "failure_reason": "lease expired", "answer": "secret"}))
    result = summarize(queue, status, data)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "lease expired"
    assert "secret" not in json.dumps(result)


def test_driver_done_is_complete(tmp_path):
    queue, status, data = fixture(tmp_path, [
        ("step-done", {"step": 1, "short": "first"}),
        ("step-done", {"step": 2, "short": "second"}),
        ("driver-done", {"steps": 2}),
    ])
    result = summarize(queue, status, data)
    assert result["state"] == "complete"
    assert result["current_step"] is None
    assert len(result["completed_steps"]) == 2


def test_driver_done_with_pending_step_requires_handoff(tmp_path):
    queue, status, data = fixture(tmp_path, [
        ("step-done", {"step": 1, "short": "first"}),
        ("driver-done", {"steps": 2}),
    ])
    result = summarize(queue, status, data)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "driver ended with 1 incomplete step"


def test_complete_malformed_line_is_error(tmp_path):
    queue, status, data = fixture(tmp_path, [], tail='{"event":\n')
    with pytest.raises(StatusReadError):
        summarize(queue, status, data)


def test_existing_stop_marker_without_event_requires_handoff(tmp_path):
    queue, status, data = fixture(tmp_path, [])
    stop = tmp_path / "STOP"
    stop.write_text("2026-09-25T00:00:00Z prior failure\n")
    result = summarize(queue, status, data, stop_marker=stop)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "2026-09-25T00:00:00Z prior failure"


def test_malformed_history_reports_explicit_stop_and_parse_error(tmp_path):
    queue, status, data = fixture(tmp_path, [("step-start", {"step": 1, "short": "first"})])
    with status.open("a", encoding="utf-8") as handle:
        handle.write('INSPECT FAILED: "no manifest"\n')
        handle.write('{"event":"STOP","detail":"later event"}\n')
    stop = tmp_path / "STOP"
    stop.write_text("2026-09-25T09:49:19Z structural failure\n")
    result = summarize(queue, status, data, stop_marker=stop)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "2026-09-25T09:49:19Z structural failure"
    assert result["status_parse_error"] == "malformed complete status line 2"
    assert result["completed_steps"] == []


DRIVER = "/mnt/d/project/scripts/flights/batch/batch_driver.sh"
SESSION = "serving-train-a"
SERVICE = "speech_aware_evidence_acquisition.core.session.serving"


def test_process_check_requires_driver_and_matching_service(tmp_path):
    queue, status, data = fixture(tmp_path, [("step-start", {"step": 1, "short": "first"})])
    result = summarize(queue, status, data, process_snapshot=[
        ["/usr/bin/bash", DRIVER],
        ["/home/chao/.venvs/speechrl/bin/python", "-m", SERVICE, "start", "q4", "--session-id", SESSION],
    ], driver_script=DRIVER, session_id=SESSION)
    assert result["state"] == "running"
    assert result["reason"] is None


def test_wrong_process_identity_does_not_prove_liveness(tmp_path):
    queue, status, data = fixture(tmp_path, [("arm-start", {"step": 1})])
    result = summarize(queue, status, data, process_snapshot=[
        ["/usr/bin/bash", "/other/batch_driver.sh"],
        ["/usr/bin/python", "-m", SERVICE, "start", "q4", "--session-id", "other-session"],
        ["/usr/bin/bash", "-c", f"echo {DRIVER} {SESSION}"],
    ], driver_script=DRIVER, session_id=SESSION)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "batch driver and serving session processes absent"


def test_driver_present_but_service_missing_requires_handoff(tmp_path):
    queue, status, data = fixture(tmp_path, [("arm-start", {"step": 1})])
    result = summarize(queue, status, data, process_snapshot=[
        ["bash", DRIVER],
    ], driver_script=DRIVER, session_id=SESSION)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "serving session process absent"


def test_proc_scanner_reads_only_cmdline_of_numeric_entries(tmp_path):
    proc = tmp_path / "proc"
    (proc / "123").mkdir(parents=True)
    (proc / "123" / "cmdline").write_bytes(b"bash\0/mnt/d/project/scripts/flights/batch/batch_driver.sh\0")
    (proc / "self").mkdir()
    (proc / "self" / "cmdline").write_bytes(b"fake\0")
    assert _process_snapshot(proc) == [["bash", DRIVER]]


def telemetry_record(**updates):
    row = {
        "schema": "saea-serving-monitor-sample-v1", "sampled_at": 1000.0,
        "sampled_at_iso": "1970-01-01T00:16:40+00:00", "server_ok": True,
        "gpu": {"utilization_percent": 98.0, "memory_used_mib": 23000, "power_watts": 95.0},
        "slots": {"busy": 4, "idle": 0, "total": 4}, "requests_total": 42,
        "untrusted_extra": "do not forward",
    }
    return {**row, **updates}


def test_optional_telemetry_is_bounded_allowlisted_and_ignores_partial_tail(tmp_path):
    from continuation_status import telemetry_summary

    path = tmp_path / "monitor.jsonl"
    path.write_bytes(b"old junk" * 20000 + b"\n" + json.dumps(telemetry_record()).encode() +
                     b'\n{"schema":')
    result = telemetry_summary(path, now=1010)
    assert result["server_ok"] is True
    assert result["age_seconds"] == 10
    assert result["slots_busy"] == 4
    assert result["service_requests_total"] == 42
    assert result["warnings"] == []
    assert "untrusted_extra" not in json.dumps(result)
    assert "do not forward" not in json.dumps(result)


@pytest.mark.parametrize("updates,now,warning", [
    ({}, 1100, "serving telemetry is stale"),
    ({"server_ok": False}, 1010, "serving monitor reports unhealthy service"),
    ({"sampled_at": 1200}, 1010, "serving telemetry timestamp is in the future"),
])
def test_telemetry_reports_observational_warnings(tmp_path, updates, now, warning):
    from continuation_status import telemetry_summary

    path = tmp_path / "monitor.jsonl"
    path.write_text(json.dumps(telemetry_record(**updates)) + "\n")
    assert warning in telemetry_summary(path, now=now)["warnings"]


def test_idle_gpu_is_not_a_failure(tmp_path):
    from continuation_status import telemetry_summary

    path = tmp_path / "monitor.jsonl"
    path.write_text(json.dumps(telemetry_record(
        gpu={"utilization_percent": 0.0}, slots={"busy": 0, "idle": 4, "total": 4}
    )) + "\n")
    assert telemetry_summary(path, now=1010)["warnings"] == []


@pytest.mark.parametrize("raw", [
    b'{"schema":"wrong","sampled_at":1000}\n',
    b'{"schema":"saea-serving-monitor-sample-v1","sampled_at":NaN}\n',
    b'{"schema":',
])
def test_bad_telemetry_reports_unknown_not_healthy(tmp_path, raw):
    from continuation_status import telemetry_summary

    path = tmp_path / "monitor.jsonl"
    path.write_bytes(raw)
    result = telemetry_summary(path, now=1010)
    assert result["server_ok"] is None
    assert result["warnings"] == ["serving telemetry is unavailable or malformed"]


def test_telemetry_requested_adds_snapshot_without_changing_queue_verdict(tmp_path):
    queue, status, data = fixture(tmp_path, [("step-start", {"step": 1, "short": "first"})])
    telemetry = tmp_path / "monitor.jsonl"
    telemetry.write_text(json.dumps(telemetry_record(server_ok=False)) + "\n")
    result = summarize(queue, status, data, telemetry_path=telemetry, now=1010)
    assert result["state"] == "running-unverified"
    assert result["telemetry"]["server_ok"] is False
    assert result["telemetry"]["warnings"]


@pytest.mark.parametrize("old_event,detail", [
    ("driver-done", {"steps": 2}),
    ("STOP", "previous family stopped"),
    ("arm-exit", {"step": 1, "rc": 9}),
])
def test_new_driver_epoch_does_not_inherit_previous_terminal_event(tmp_path, old_event, detail):
    queue, status, data = fixture(tmp_path, [
        ("step-done", {"step": 1, "short": "first"}),
        (old_event, detail),
        ("driver-start", {"flight_commit": "new"}),
        ("step-skip-done", {"step": 1, "short": "first"}),
        ("step-start", {"step": 2, "short": "second"}),
    ])
    result = summarize(queue, status, data)
    assert result["state"] == "running-unverified"
    assert result["reason"] is None
    assert result["current_step"]["short"] == "second"
    assert len(result["completed_steps"]) == 1


def test_new_driver_epoch_does_not_clear_a_stop_marker(tmp_path):
    queue, status, data = fixture(tmp_path, [
        ("driver-done", {"steps": 2}),
        ("driver-start", {"flight_commit": "new"}),
    ])
    stop = tmp_path / "STOP"
    stop.write_text("explicit unreleased failure")
    result = summarize(queue, status, data, stop_marker=stop)
    assert result["state"] == "handoff-required"
    assert result["reason"] == "explicit unreleased failure"
