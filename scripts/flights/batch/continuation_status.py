"""Read compact batch progress from explicit local metadata paths only.

Example: python continuation_status.py --queue /home/chao/batch-queue.json
    --status /home/chao/batch-status.jsonl --data-root /path/to/data

This command does not inspect output rows, scores, traces, campaign logs, or model endpoints.
Without --check-processes, an apparent running state is explicitly unverified.
"""

import argparse
import json
import math
import time
from pathlib import Path


class StatusReadError(ValueError):
    """A required metadata file is malformed."""


def _json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StatusReadError(f"cannot read metadata at {path}: {type(exc).__name__}") from exc


def _events(path):
    if not path.exists():
        return [], False, None
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StatusReadError(f"cannot read status at {path}: {type(exc).__name__}") from exc
    lines = raw.splitlines(keepends=True)
    events = []
    ignored_tail = False
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
            if not isinstance(event, dict) or not isinstance(event.get("event"), str):
                raise ValueError("event object required")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            if index == len(lines) - 1 and not line.endswith(b"\n"):
                ignored_tail = True
                break
            return events, False, f"malformed complete status line {index + 1}"
        events.append(event)
    return events, ignored_tail, None


def _stop_reason(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip() or "STOP marker present"
    except OSError as exc:
        raise StatusReadError(f"cannot read STOP marker: {type(exc).__name__}") from exc


def _component(value):
    if not isinstance(value, str) or not value or value in (".", "..") or "/" in value or "\\" in value:
        raise StatusReadError("queue contains an invalid run or attempt identifier")
    return value


def _step_view(step):
    return {key: step.get(key) for key in ("order", "short", "cell")}


def _process_snapshot(proc_root=Path("/proc")):
    """Read Linux argv metadata; disappearing or inaccessible PIDs are ignored."""
    try:
        entries = list(Path(proc_root).iterdir())
    except OSError as exc:
        raise StatusReadError(f"cannot inspect process table: {type(exc).__name__}") from exc
    snapshot = []
    for entry in entries:
        if not entry.name.isdecimal():
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
            argv = [part.decode("utf-8") for part in raw.rstrip(b"\0").split(b"\0") if part]
        except (OSError, UnicodeDecodeError):
            continue
        if argv:
            snapshot.append(argv)
    return snapshot


def _process_presence(snapshot, driver_script, session_id):
    driver = False
    service = False
    module = "speech_aware_evidence_acquisition.core.session.serving"
    for argv in snapshot:
        if len(argv) >= 2 and Path(argv[0]).name == "bash" and argv[1] == driver_script:
            driver = True
        if (len(argv) >= 6 and Path(argv[0]).name.startswith("python")
                and argv[1:4] == ["-m", module, "start"]):
            service = any(argv[i:i + 2] == ["--session-id", session_id]
                          for i in range(4, len(argv) - 1)) or service
    return driver, service


def _sealed_metadata(data_root, step):
    run = step.get("run_id")
    attempt = step.get("gen_attempt_id")
    if not run or not attempt:
        return None, None, None
    run, attempt = _component(run), _component(attempt)
    attempt_path = data_root / "attempts" / run / f"{attempt}.json"
    record = _json(attempt_path) if attempt_path.exists() else {}
    state = record.get("state")
    failure = record.get("failure_reason") or record.get("failure") if state == "ABORTED" else None
    manifest_dir = data_root / "runs" / run / attempt
    manifests = sorted(manifest_dir.glob("*.run-manifest.json"))
    if len(manifests) > 1:
        raise StatusReadError("multiple run manifests for current step")
    manifest_status = _json(manifests[0]).get("status") if manifests else None
    return state, manifest_status, failure



def telemetry_summary(path, *, now=None, stale_after_seconds=90):
    """Read one completed, bounded telemetry row; never inspect task results.

    Request totals belong to the serving process, not to the current experiment.
    Warnings describe observations and never restart or invalidate a flight.
    """
    unknown = {
        "server_ok": None,
        "warnings": ["serving telemetry is unavailable or malformed"],
    }
    try:
        with Path(path).open("rb") as handle:
            handle.seek(0, 2)
            end = handle.tell()
            start = max(0, end - 65536)
            handle.seek(start)
            raw = handle.read(65536)
        if start:
            raw = raw.partition(b"\n")[2]
        lines = raw.splitlines(keepends=True)
        if lines and not lines[-1].endswith(b"\n"):
            lines.pop()
        if not lines:
            return unknown
        row = json.loads(lines[-1])
        if not isinstance(row, dict) or row.get("schema") != "saea-serving-monitor-sample-v1":
            return unknown
        sampled = row.get("sampled_at")
        if (isinstance(sampled, bool) or not isinstance(sampled, (int, float))
                or not math.isfinite(sampled)):
            return unknown
        if not isinstance(row.get("server_ok"), bool):
            return unknown
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return unknown

    def number(mapping, name):
        value = mapping.get(name) if isinstance(mapping, dict) else None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return value if math.isfinite(value) and value >= 0 else None

    age = (time.time() if now is None else now) - sampled
    warnings = []
    if age > stale_after_seconds:
        warnings.append("serving telemetry is stale")
    elif age < -5:
        warnings.append("serving telemetry timestamp is in the future")
    if not row["server_ok"]:
        warnings.append("serving monitor reports unhealthy service")
    return {
        "sampled_at": sampled,
        "age_seconds": round(age, 3),
        "server_ok": row["server_ok"],
        "gpu_utilization_percent": number(row.get("gpu"), "utilization_percent"),
        "gpu_memory_used_mib": number(row.get("gpu"), "memory_used_mib"),
        "gpu_power_watts": number(row.get("gpu"), "power_watts"),
        "slots_busy": number(row.get("slots"), "busy"),
        "slots_total": number(row.get("slots"), "total"),
        "service_requests_total": number(row, "requests_total"),
        "warnings": warnings,
    }

def summarize(queue_path, status_path, data_root, *, stop_marker=None,
              process_snapshot=None, driver_script=None, session_id=None,
              telemetry_path=None, now=None):
    """Summarize one existing queue; all inputs are explicit, local, and read only."""
    queue_path, status_path, data_root = map(Path, (queue_path, status_path, data_root))
    queue = _json(queue_path)
    if not isinstance(queue, list) or any(not isinstance(step, dict) for step in queue):
        raise StatusReadError("queue must be a list of step objects")
    events, ignored_tail, parse_error = _events(status_path)
    has_stop_marker = stop_marker is not None and Path(stop_marker).exists()
    if parse_error and not has_stop_marker:
        raise StatusReadError(parse_error)
    done = {event["detail"].get("short") for event in events
            if event["event"] == "step-done" and isinstance(event.get("detail"), dict)}
    completed = [_step_view(step) for step in queue if step.get("short") in done]
    pending = [step for step in queue if step.get("short") not in done]
    current = pending[0] if pending else None
    attempt_state = manifest_status = failure = None
    if current is not None:
        attempt_state, manifest_status, failure = _sealed_metadata(data_root, current)
    # The append-only log spans queue families and manual resumptions.
    # Keep completed step identities for resume, but scope terminal events to
    # the latest driver invocation. An on-disk STOP remains authoritative.
    starts = [i for i, event in enumerate(events) if event["event"] == "driver-start"]
    epoch = events[starts[-1]:] if starts else events
    stops = [event.get("detail") for event in epoch if event["event"] == "STOP"]
    if parse_error:
        failure = _stop_reason(stop_marker)
    elif stops:
        failure = str(stops[-1])
    elif has_stop_marker:
        failure = _stop_reason(stop_marker)
    elif failure is None:
        exits = [event for event in epoch if event["event"] in ("arm-exit", "smoke-worker-exit")
                 and isinstance(event.get("detail"), dict) and event["detail"].get("rc") not in (None, 0)]
        if exits:
            last = exits[-1]
            failure = f"{last['event']} rc {last['detail']['rc']} on step {last['detail'].get('step')}"
    driver_done = any(event["event"] == "driver-done" for event in epoch)
    if driver_done and pending and not failure:
        failure = f"driver ended with {len(pending)} incomplete step" + ("s" if len(pending) != 1 else "")
    if failure:
        state = "handoff-required"
    elif driver_done and not pending:
        state = "complete"
    elif events:
        state = "running-unverified"
    else:
        state = "queued"
    if process_snapshot is not None and state == "running-unverified":
        if not driver_script or not session_id or not Path(driver_script).is_absolute():
            raise StatusReadError("process check requires absolute driver script and serving session id")
        driver, service = _process_presence(process_snapshot, str(driver_script), session_id)
        if driver and service:
            state = "running"
        else:
            missing = []
            if not driver:
                missing.append("batch driver")
            if not service:
                missing.append("serving session")
            failure = " and ".join(missing) + " process" + ("es" if len(missing) > 1 else "") + " absent"
            state = "handoff-required"
    result = {
        "state": state,
        "handoff_required": state == "handoff-required",
        "current_step": _step_view(current) if current is not None else None,
        "completed_steps": completed,
        "reason": failure,
        "attempt_state": attempt_state,
        "manifest_status": manifest_status,
        "ignored_incomplete_tail": ignored_tail,
        "status_parse_error": parse_error,
    }
    if telemetry_path is not None:
        result["telemetry"] = telemetry_summary(telemetry_path, now=now)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--stop-marker", type=Path, help="Optional explicit driver STOP marker path")
    parser.add_argument("--check-processes", action="store_true", help="Verify driver and serving session identities in Linux /proc")
    parser.add_argument("--driver-script", type=Path, help="Absolute batch_driver.sh path required with --check-processes")
    parser.add_argument("--session-id", help="Serving session id required with --check-processes")
    parser.add_argument("--telemetry", type=Path, help="Optional local serving monitor JSONL; bounded metadata only")
    args = parser.parse_args()
    if args.check_processes and (not args.driver_script or not args.session_id or not args.driver_script.is_absolute()):
        parser.error("--check-processes requires --driver-script as an absolute path and --session-id")
    try:
        snapshot = _process_snapshot() if args.check_processes else None
        result = summarize(args.queue, args.status, args.data_root, stop_marker=args.stop_marker,
                           process_snapshot=snapshot, driver_script=args.driver_script,
                           session_id=args.session_id, telemetry_path=args.telemetry)
    except StatusReadError as exc:
        parser.exit(2, f"status unavailable: {exc}\n")
    print(json.dumps(result, separators=(",", ":"), ensure_ascii=True))


if __name__ == "__main__":
    main()
