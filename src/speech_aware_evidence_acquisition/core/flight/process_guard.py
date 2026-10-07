"""Bound one owned campaign or leased worker with sampled Windows memory admission.

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

from ..session.windows_memory import WindowsMemoryObserver


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
    floor_gib: float = 4.0
    interval_seconds: float = 5.0
    read_timeout_seconds: float = 10.0
    stop_grace_seconds: float = 5.0

    def __post_init__(self):
        if not all(_finite(v) for v in asdict(self).values()) or not (
            self.start_gib >= self.floor_gib >= 4
            and 0 < self.interval_seconds <= 10
            and 0 < self.read_timeout_seconds <= 15
            and 0 < self.stop_grace_seconds <= 30
        ):
            raise FlightProcessGuardError(
                "invalid flight memory policy or floor below owner-authorized 4 GiB"
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
        "reader_error": value.get("host_memory_error") if isinstance(value, Mapping) else error,
        "reader_diagnostics": value.get("host_memory_diagnostics", {}) if isinstance(value, Mapping) else {},
        "observer": {key: value[key] for key in
                     ("transport", "observer_pid", "sequence", "sampled_at",
                      "freshness", "sample_elapsed_ms")
                     if key in value} if isinstance(value, Mapping) else {},
    }


_MEMINFO_FIELDS = ("MemFree", "MemAvailable", "Cached", "Buffers", "AnonPages",
                   "Shmem", "Mlocked", "Unevictable", "Slab", "SwapFree")


def _bounded_proc_read(path, *, limit=65536):
    """Read a bounded operational proc record, never command or task content."""
    with Path(path).open("rb") as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("proc record exceeds bounded read")
    return raw.decode("ascii")


def _proc_starttime(root, pid):
    raw = _bounded_proc_read(root / str(pid) / "stat", limit=4096)
    fields = raw[raw.rindex(")") + 2:].split()
    if int(raw.split(" ", 1)[0]) != pid:
        raise ValueError("proc PID differs")
    return int(fields[19])


def _memory_fields(raw, names):
    result = dict.fromkeys(names)
    for line in raw.splitlines():
        key, _, value = line.partition(":")
        if key in result:
            parts = value.split()
            if len(parts) == 2 and parts[1] == "kB" and parts[0].isdigit():
                result[key] = int(parts[0])
    return result


class ProcessMemoryDiagnostics:
    """One in-flight, nonblocking Linux memory diagnostic; never admission."""

    def __init__(self, *, proc_root=Path("/proc"), server_pid=None):
        self.root = Path(proc_root)
        self.server_pid = server_pid
        self.server_error = None
        self.identities = {}
        self.thread = None
        self.results = queue.Queue(maxsize=1)
        self.latest = {"status": "not-sampled"}

    def _process(self, role, pid):
        if pid is None:
            return {"status": "not-started"}
        result = {"pid": pid}
        try:
            start = _proc_starttime(self.root, pid)
            identity = {"pid": pid, "starttime_ticks": start}
            result["identity"] = identity
            bound = self.identities.setdefault(role, identity)
            if bound != identity:
                result["error"] = "pid-identity-changed"
                return result
            memory = _memory_fields(_bounded_proc_read(self.root / str(pid) / "smaps_rollup"),
                                    ("Rss", "Pss", "Swap"))
            if _proc_starttime(self.root, pid) != start:
                result["error"] = "pid-identity-changed"
                return result
            result["memory_kib"] = memory
        except Exception as error:
            result["error"] = type(error).__name__
        return result

    def collect(self, worker_pid):
        started = time.monotonic()
        result = {"schema": "saea-process-memory-diagnostics-v1", "started_at": time.time()}
        try:
            result["meminfo_kib"] = _memory_fields(
                _bounded_proc_read(self.root / "meminfo"), _MEMINFO_FIELDS)
        except Exception as error:
            result["meminfo_error"] = type(error).__name__
        result["worker"] = self._process("worker", worker_pid)
        result["server"] = ({"error": self.server_error} if self.server_error else
                            self._process("server", self.server_pid))
        result["completed_at"] = time.time()
        result["elapsed_seconds"] = time.monotonic() - started
        return result

    def start(self, worker_pid):
        self.snapshot()
        if self.thread is not None and self.thread.is_alive():
            return
        def read():
            try:
                value = self.collect(worker_pid)
            except Exception as error:
                value = {"error": type(error).__name__}
            self.results.put_nowait(value)
        self.thread = threading.Thread(target=read, daemon=True)
        self.thread.start()

    def snapshot(self):
        try:
            self.latest = self.results.get_nowait()
        except queue.Empty:
            pass
        return {**self.latest, "pending": bool(self.thread and self.thread.is_alive()),
                "age_seconds": max(0, time.time() - self.latest["completed_at"])
                if "completed_at" in self.latest else None}


def _diagnostic_start(diagnostics, pid):
    try:
        diagnostics.start(pid)
    except Exception as error:
        return {"scheduling_error": type(error).__name__}
    return None


def _diagnostic_snapshot(diagnostics, scheduling_error):
    try:
        result = diagnostics.snapshot()
    except Exception as error:
        result = {"snapshot_error": type(error).__name__}
    return {**result, **(scheduling_error or {})}


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
    command, receipt_dir, policy, *, host_reader=None, identity=None, diagnostics=None
):
    """Execute once, preserve exit status, and stop only this private group."""
    if host_reader is None:
        with WindowsMemoryObserver() as observer:
            return _run_guarded(command, receipt_dir, policy,
                                host_reader=observer, identity=identity, diagnostics=diagnostics)
    return _run_guarded(command, receipt_dir, policy,
                        host_reader=host_reader, identity=identity, diagnostics=diagnostics)


def _run_guarded(command, receipt_dir, policy, *, host_reader, identity, diagnostics=None):
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
    diagnostic_error = None
    with (root / "events.jsonl").open("x") as log:

        def emit(event, **fields):
            if diagnostics is not None:
                fields["memory_diagnostics"] = _diagnostic_snapshot(diagnostics, diagnostic_error)
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
            if diagnostics is not None:
                doc["memory_diagnostics"] = _diagnostic_snapshot(diagnostics, diagnostic_error)
            with (root / "finished.json").open("x") as handle:
                handle.write(json.dumps(doc, sort_keys=True, indent=2) + "\n")
            emit("finished", **asdict(result))
            return result

        if diagnostics is not None:
            diagnostic_error = _diagnostic_start(diagnostics, None)
        initial = _sample(host_reader, policy)
        emit("start-sample", **initial)
        if initial["reason"] or initial["available_gib"] < policy.start_gib:
            return finish("start-refused", 125)
        try:
            process = subprocess.Popen(list(command), start_new_session=True)
            emit("worker-start", pid=process.pid)
            while process.poll() is None:
                if diagnostics is not None:
                    diagnostic_error = _diagnostic_start(diagnostics, process.pid)
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


def _registered_diagnostics(data, session_id):
    """Resolve only the registered service PID, reporting diagnostic errors."""
    diagnostics = ProcessMemoryDiagnostics()
    try:
        session_root = (data / "serving").resolve()
        session_path = (session_root / session_id / "session-receipt.json").resolve()
        if not session_path.is_relative_to(session_root):
            raise ValueError("diagnostic session path escapes serving root")
        session = json.loads(_bounded_proc_read(session_path))
        pid = session.get("pid")
        if session.get("session_id") != session_id or type(pid) is not int or pid <= 0:
            raise ValueError("diagnostic resident identity mismatch")
        diagnostics.server_pid = pid
    except Exception as error:
        diagnostics.server_error = type(error).__name__
    return diagnostics

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "repo-root",
        "data-root",
        "runtime-root",
        "lock-path",
        "owner",
        "expected-session-id",
        "receipt-dir",
    ):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--memory-diagnostics", action="store_true")
    parser.add_argument("--experiment")
    parser.add_argument("--campaign-plan", type=Path)
    parser.add_argument("--start-gib", type=float, required=True)
    parser.add_argument("--floor-gib", type=float, default=4.0)
    parser.add_argument("--mode", choices=("campaign", "worker", "node-panel", "node-panel-worker"), default="campaign")
    parser.add_argument("--lease-token-file")
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

    if args.mode in {"node-panel", "node-panel-worker"}:
        from .cli import load_node_panel_plan

        if args.campaign_plan is None or args.experiment or args.lease_token_file:
            parser.error("node-panel requires only its exact committed campaign plan")
        plan_path = args.campaign_plan.resolve()
        if not plan_path.is_relative_to(repo):
            parser.error("node panel plan must be confined beneath repo-root")
        selected, panel_id, _members = load_node_panel_plan(repo, plan_path, mode=args.mode)
        cells = tuple(cell for _, cell in selected)
        ownership = {"panel_id": panel_id, "members": [
            {"run_id": cell.run_id, "attempt_id": cell.attempt_id} for cell in cells]}
    elif args.mode == "campaign" and args.campaign_plan is not None:
        from .cli import load_campaign_plan
        import hashlib

        if args.experiment or args.lease_token_file:
            parser.error("campaign plan requires no experiment or external worker token")
        plan_path = args.campaign_plan.resolve()
        if not plan_path.is_relative_to(repo):
            parser.error("campaign plan must be confined beneath repo-root")
        plan_sha256 = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        selected = load_campaign_plan(repo, plan_path)
        cells = tuple(cell for _, cell in selected)
        ownership = {"campaign_plan": {"relpath": plan_path.relative_to(repo).as_posix(),
                                      "sha256": plan_sha256},
                     "members": [{"experiment": experiment, "cell": cell.document["cell_id"],
                                  "run_id": cell.run_id, "attempt_id": cell.attempt_id}
                                 for experiment, cell in selected]}
    else:
        if not args.experiment or args.campaign_plan is not None:
            parser.error("ordinary guarded workers require one experiment")
        cells = load_campaign_cells(repo, args.experiment)
        if len(cells) != 1:
            parser.error("memory-contained process requires exactly one registered campaign cell")
    for cell in cells:
        cell.assert_mode(args.mode)
        state = declared_readiness(cell, data)
        if state.state != "ready":
            parser.error("registered cell is not ready: " + state.reason)
    if args.mode not in {"node-panel", "node-panel-worker"} and args.campaign_plan is None:
        ownership = {"run_id": cells[0].run_id, "attempt_id": cells[0].attempt_id}
    command = [
        sys.executable,
        "-B",
        "-m",
        "speech_aware_evidence_acquisition.core.flight.cli",
        args.mode,
    ]
    for name in (
        "repo-root",
        "data-root",
        "runtime-root",
        "lock-path",
        "owner",
        "expected-session-id",
    ):
        command.extend(["--" + name, getattr(args, name.replace("-", "_"))])
    if args.campaign_plan is not None:
        command.extend(["--campaign-plan", str(plan_path)])
    else:
        command.extend(["--experiment", args.experiment])
    if args.mode == "worker":
        from .lease import WorkerExecutionPolicy

        if not args.lease_token_file:
            parser.error("worker mode requires the existing leased worker token")
        token_path = Path(args.lease_token_file).resolve()
        if not token_path.is_relative_to(data / "coordination"):
            parser.error("worker token must be confined beneath data-root/coordination")
        token = json.loads(token_path.read_text())
        if not isinstance(token, dict) or any((
            token.get("schema") != "saea-worker-lease-handoff-v1",
            token.get("run_id") != cell.run_id,
            token.get("attempt_id") != cell.attempt_id,
            token.get("session_id") != args.expected_session_id,
            token.get("stage", "worker") != "worker",
            not isinstance(token.get("token"), str) or not token.get("token"),
        )):
            parser.error("worker token does not name this exact registered worker")
        WorkerExecutionPolicy(args.expected_session_id, token["token"]).assert_lease(
            data, run_id=cell.run_id, attempt_id=cell.attempt_id
        )
        command.extend(["--cell", cell.document["cell_id"],
                        "--lease-token-file", str(token_path)])
    elif args.lease_token_file is not None:
        parser.error("campaign mode does not accept an external worker token")
    policy = MemoryPolicy(args.start_gib, args.floor_gib)
    from ..bundle.git_commit import require_clean_study_repo

    study_head = require_clean_study_repo(repo)
    if args.mode == "campaign" and args.campaign_plan is not None:
        if hashlib.sha256(plan_path.read_bytes()).hexdigest() != plan_sha256:
            parser.error("campaign plan changed during clean-source validation")

    def interrupted(signum, frame):
        raise InterruptedError("owned process supervisor interrupted")

    diagnostics = None
    if args.memory_diagnostics:
        diagnostics = _registered_diagnostics(data, args.expected_session_id)
    prior = signal.signal(signal.SIGTERM, interrupted)
    try:
        result = run_guarded(
            command,
            receipt,
            policy,
            diagnostics=diagnostics,
            identity={
                **ownership,
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
