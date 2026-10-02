"""Bound one owned campaign process with sampled Windows memory admission.

This supervisor never changes a service, attempt, lease, STOP marker or queue.
The original campaign CLI still owns execution and scoring. A stopped worker's
records remain evidence for an explicit disposition; no retry occurs here.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping

from ..session.serving import read_host_memory


class FlightProcessGuardError(ValueError):
    """Refuse ambiguous custody or a weakened resource policy."""


def _finite(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


@dataclass(frozen=True)
class MemoryPolicy:
    start_gib: float
    floor_gib: float = 10.0
    interval_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    stop_grace_seconds: float = 5.0

    def __post_init__(self):
        if not all(_finite(v) for v in asdict(self).values()) or not (
            self.start_gib >= self.floor_gib >= 8
            and 0 < self.interval_seconds <= 10
            and 0 < self.read_timeout_seconds <= 15
            and 0 < self.stop_grace_seconds <= 30
        ):
            raise FlightProcessGuardError(
                "invalid flight memory policy or floor below owner-authorized 8 GiB"
            )


@dataclass(frozen=True)
class GuardResult:
    status: str
    exit_code: int
    pid: int | None
    worker_returncode: int | None


def _sample(reader, policy):
    started = time.monotonic()
    result = queue.Queue(maxsize=1)

    def read():
        try:
            result.put((reader(), None))
        except BaseException as error:
            result.put((None, type(error).__name__))

    # A blocked observer must not prevent stopping the owned child. There is
    # no next observation after timeout; the daemon cannot grant late permission.
    threading.Thread(target=read, daemon=True).start()
    try:
        value, error = result.get(timeout=policy.read_timeout_seconds)
    except queue.Empty:
        value, error = None, "timeout"
    elapsed = time.monotonic() - started
    available = value.get("host_free_gb") if isinstance(value, Mapping) else None
    if error == "timeout" or elapsed > policy.read_timeout_seconds:
        reason = "sample-too-old"
    elif error:
        reason = "reader-failed:" + error
    elif not _finite(available) or available < 0:
        reason = "windows-reading-unavailable"
    else:
        reason = None
    return {
        "available_gib": available if _finite(available) else None,
        "elapsed_seconds": elapsed,
        "reason": reason,
    }


def _stop_owned(process, policy, emit):
    if process.poll() is not None:
        return
    # start_new_session creates this private group. Never signal by name,
    # another session's PID or a stale receipt; the owned child must be alive.
    try:
        if os.getpgid(process.pid) != process.pid:
            raise FlightProcessGuardError(
                "owned child is no longer its private process-group leader"
            )
        emit("stop-owned-group", pid=process.pid, signal="SIGTERM")
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        if process.poll() is not None:
            return
        raise
    # Do not reap the group leader during the grace period. Its unreaped PID
    # reserves the group identity even if it exits before a scoring descendant.
    # Reaping it early would both miss that descendant and permit PID reuse.
    time.sleep(policy.stop_grace_seconds)
    if os.getpgid(process.pid) != process.pid:
        raise FlightProcessGuardError(
            "private process identity changed before escalation"
        )
    emit("stop-owned-group", pid=process.pid, signal="SIGKILL")
    os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def run_guarded(
    command, receipt_dir, policy, *, host_reader=read_host_memory, identity=None
):
    """Execute once, preserve exit status, and stop only this private group."""
    if (
        os.name != "posix"
        or not command
        or any(not isinstance(x, str) or not x for x in command)
    ):
        raise FlightProcessGuardError(
            "a nonempty argument vector and POSIX process custody are required"
        )
    root = Path(receipt_dir)
    try:
        root.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise FlightProcessGuardError(
            "guard receipt directory already exists"
        ) from error
    process = None
    with (root / "events.jsonl").open("x") as log:

        def emit(event, **fields):
            log.write(
                json.dumps(
                    {"event": event, "at": time.time(), **fields},
                    sort_keys=True,
                    allow_nan=False,
                )
                + "\n"
            )
            log.flush()

        def finish(status, code):
            result = GuardResult(
                status,
                code,
                process.pid if process else None,
                process.poll() if process else None,
            )
            doc = {
                "schema": "saea-flight-process-memory-guard-v1",
                **asdict(result),
                "policy": asdict(policy),
                "command": list(command),
                "identity": identity or {},
            }
            with (root / "finished.json").open("x") as handle:
                handle.write(json.dumps(doc, sort_keys=True, indent=2) + "\n")
            emit("finished", **asdict(result))
            return result

        initial = _sample(host_reader, policy)
        emit("start-sample", **initial)
        if initial["reason"] or initial["available_gib"] < policy.start_gib:
            return finish("start-refused", 125)
        try:
            process = subprocess.Popen(list(command), start_new_session=True)
            emit("worker-start", pid=process.pid)
            while process.poll() is None:
                observation = _sample(host_reader, policy)
                emit("running-sample", **observation)
                if (
                    observation["reason"]
                    or observation["available_gib"] < policy.floor_gib
                ):
                    _stop_owned(process, policy, emit)
                    return finish("resource-stop", 125)
                try:
                    process.wait(timeout=policy.interval_seconds)
                except subprocess.TimeoutExpired:
                    pass
            code = process.returncode
            return finish("completed" if code == 0 else "worker-failed", code)
        except BaseException as error:
            emit("guard-error", error_type=type(error).__name__)
            if process is not None:
                _stop_owned(process, policy, emit)
            return finish("guard-failed", 125)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo-root",
        "data-root",
        "runtime-root",
        "lock-path",
        "experiment",
        "owner",
        "expected-session-id",
        "receipt-dir",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--start-gib", type=float, required=True)
    parser.add_argument("--floor-gib", type=float, default=10.0)
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    data = Path(args.data_root).resolve()
    if repo != Path(__file__).resolve().parents[4]:
        parser.error("guard must be imported from the exact frozen repo-root")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    receipt = Path(args.receipt_dir).resolve()
    if not receipt.is_relative_to(data / "coordination"):
        parser.error("guard receipt must be confined beneath data-root/coordination")
    from .campaign import load_campaign_cells, declared_readiness

    cells = load_campaign_cells(repo, args.experiment)
    if len(cells) != 1:
        parser.error(
            "memory-contained process requires exactly one registered campaign cell"
        )
    cell = cells[0]
    cell.assert_mode("campaign")
    state = declared_readiness(cell, data)
    if state.state != "ready":
        parser.error("registered cell is not ready: " + state.reason)
    command = [
        sys.executable,
        "-B",
        "-m",
        "speech_aware_evidence_acquisition.core.flight.cli",
        "campaign",
    ]
    for name in (
        "repo-root",
        "data-root",
        "runtime-root",
        "lock-path",
        "experiment",
        "owner",
        "expected-session-id",
    ):
        command.extend(["--" + name, getattr(args, name.replace("-", "_"))])
    policy = MemoryPolicy(args.start_gib, args.floor_gib)
    from ..bundle.git_commit import require_clean_study_repo

    study_head = require_clean_study_repo(repo)

    def interrupted(signum, frame):
        raise InterruptedError("owned process supervisor interrupted")

    prior = signal.signal(signal.SIGTERM, interrupted)
    try:
        result = run_guarded(
            command,
            receipt,
            policy,
            identity={
                "run_id": cell.run_id,
                "attempt_id": cell.attempt_id,
                "repo_root": str(repo),
                "study_head": study_head,
                "session_id": args.expected_session_id,
            },
        )
    finally:
        signal.signal(signal.SIGTERM, prior)
    print(json.dumps(asdict(result), sort_keys=True))
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
