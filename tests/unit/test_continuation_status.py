"""Status reporting over synthetic batch metadata only."""

import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).parents[2] / "scripts" / "flights" / "batch"
sys.path.insert(0, str(SCRIPT))
from continuation_status import StatusReadError, summarize  # noqa: E402


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
        "state": "running", "handoff_required": False,
        "current_step": {"order": 2, "short": "second", "cell": "cell-b"},
        "completed_steps": [{"order": 1, "short": "first", "cell": "cell-a"}],
        "reason": None, "attempt_state": "FINALIZED", "manifest_status": "COMPLETED",
        "ignored_incomplete_tail": False,
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
