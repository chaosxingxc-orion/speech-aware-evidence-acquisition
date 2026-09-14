#!/usr/bin/env python3
"""Watch one exact campaign attempt using validated local metadata only."""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time


ATTEMPT_SCHEMA = "saea-attempt-v1"
ATTEMPT_STATES = frozenset({"RESERVED", "OPENED", "FINALIZED", "ABORTED"})
TERMINAL_STATES = frozenset({"FINALIZED", "ABORTED"})
ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def validated_id(value, label):
    if not isinstance(value, str) or ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"{label} must match {ID_PATTERN.pattern!r}")
    return value


def authoritative_attempt_path(data_root, run_id, attempt_id):
    """Return the sole permitted durable attempt-ledger path."""
    return (
        Path(data_root)
        / "attempts"
        / validated_id(run_id, "run_id")
        / f"{validated_id(attempt_id, 'attempt_id')}.json"
    )


def process_identity(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        fields = raw.rsplit(") ", 1)[1].split()
        command = Path(f"/proc/{pid}/cmdline").read_bytes()
        return {
            "start_ticks": fields[19],
            "command_sha256": hashlib.sha256(command).hexdigest(),
            "live": fields[0] not in {"Z", "X"},
        }
    except (OSError, IndexError):
        return None


def _finite_nonnegative(value, label, *, integer=False):
    expected = int if integer else (int, float)
    if isinstance(value, bool) or not isinstance(value, expected):
        raise ValueError(f"{label} must be a finite nonnegative number")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{label} must be a finite nonnegative number")
    return int(value) if integer else float(value)


def read_attempt(path, run_id, attempt_id):
    if not path.exists():
        return None, "waiting"
    try:
        document = json.loads(path.read_text())
        if not isinstance(document, dict):
            raise ValueError("attempt document must be an object")
        if document.get("schema") != ATTEMPT_SCHEMA:
            raise ValueError(f"attempt schema must be {ATTEMPT_SCHEMA}")
        if document.get("run_id") != run_id or document.get("attempt_id") != attempt_id:
            raise ValueError("attempt identity mismatch")
        state = document.get("state")
        if state not in ATTEMPT_STATES:
            raise ValueError("attempt state is not recognized")
        actual = document.get("actual")
        if not isinstance(actual, dict):
            raise ValueError("attempt actual must be an object")
        calls = _finite_nonnegative(actual.get("calls"), "actual.calls", integer=True)
        audio = _finite_nonnegative(actual.get("audio_seconds"), "actual.audio_seconds")
        return {"state": state, "calls": calls, "audio_seconds": audio}, None
    except (OSError, json.JSONDecodeError, OverflowError, TypeError, ValueError) as error:
        return None, f"invalid-attempt-metadata: {error}"


def read_manifest(path, run_id, attempt_id):
    if path is None or not path.exists():
        return None, None
    try:
        document = json.loads(path.read_text())
        identity = document.get("attempt") or {}
        if document.get("run_id") != run_id or identity.get("attempt_id") != attempt_id:
            raise ValueError("manifest identity mismatch")
        scores = document.get("scores") or {}
        return {
            "status": document.get("status"),
            "scores_bound": bool(scores.get("path") and scores.get("sha256")),
        }, None
    except (OSError, json.JSONDecodeError, TypeError, AttributeError, ValueError) as error:
        return None, f"invalid-manifest-metadata: {error}"


class Events:
    def __init__(self):
        self.waiting_reported = False
        self.previous_phase = None
        self.first_progress_seen = False
        self.last_calls = None
        self.last_change = None
        self.stall_reported = False

    def update(self, attempt, manifest, alive, pid_reused, error, waiting, now):
        if pid_reused:
            return ["pid-identity-loss"]
        if error:
            return ["observer-error"]
        if not alive:
            return ["process-termination"]
        events = []
        if waiting and not self.waiting_reported:
            events.append("waiting-for-attempt-ledger")
            self.waiting_reported = True
        if attempt is None:
            return events
        phase = (attempt["state"], (manifest or {}).get("status"),
                 (manifest or {}).get("scores_bound"))
        if phase != self.previous_phase:
            events.append("attempt-terminal" if attempt["state"] in TERMINAL_STATES
                          else "phase-change")
        self.previous_phase = phase
        calls = attempt["calls"]
        if calls > 0 and not self.first_progress_seen:
            events.append("first-progress")
            self.first_progress_seen = True
        if calls != self.last_calls:
            if self.stall_reported and self.last_calls is not None and calls > self.last_calls:
                events.append("resumed-progress")
            self.last_calls, self.last_change, self.stall_reported = calls, now, False
        elif (attempt["state"] not in TERMINAL_STATES and self.last_change is not None
              and now - self.last_change >= 600 and not self.stall_reported):
            events.append("unchanged-calls-over-600s")
            self.stall_reported = True
        return events


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--manifest-path", type=Path)
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()
    try:
        run_id = validated_id(args.run_id, "run_id")
        attempt_id = validated_id(args.attempt_id, "attempt_id")
    except ValueError as error:
        parser.error(str(error))
    if args.interval < 1:
        parser.error("--interval must be at least 1")
    attempt_path = authoritative_attempt_path(args.data_root, run_id, attempt_id)
    expected = process_identity(args.pid)
    if not expected or not expected["live"]:
        parser.error("The specified campaign PID is not live.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events = Events()
    while True:
        current = process_identity(args.pid)
        pid_reused = bool(current and current["live"] and (
            current["start_ticks"] != expected["start_ticks"]
            or current["command_sha256"] != expected["command_sha256"]
        ))
        alive = bool(current and current["live"] and not pid_reused)
        attempt, attempt_status = read_attempt(attempt_path, run_id, attempt_id)
        manifest, manifest_error = read_manifest(args.manifest_path, run_id, attempt_id)
        waiting = attempt_status == "waiting"
        error = manifest_error or (None if waiting else attempt_status)
        changes = events.update(
            attempt, manifest, alive, pid_reused, error, waiting, time.monotonic()
        )
        record = {
            "timestamp": time.time(), "run_id": run_id, "attempt_id": attempt_id,
            "attempt_path": str(attempt_path), "pid": args.pid,
            "pid_start_ticks": expected["start_ticks"],
            "pid_command_sha256": expected["command_sha256"],
            "campaign_alive": alive, "pid_reused": pid_reused,
            "attempt": attempt, "manifest": manifest,
            "waiting_for_attempt_ledger": waiting, "metadata_error": error,
            "events": changes, "cpu_activity": "unknown",
            "scope": "Attempt finalization is not proof of completed official scoring.",
        }
        temp = args.output_dir / "latest.tmp"
        temp.write_text(json.dumps(record, sort_keys=True) + "\n")
        os.replace(temp, args.output_dir / "latest.json")
        if changes:
            with (args.output_dir / "events.jsonl").open("a") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
            print(json.dumps(record, sort_keys=True), flush=True)
        terminal = bool(error or pid_reused or not alive or (
            attempt and attempt["state"] in TERMINAL_STATES
        ))
        if terminal:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
