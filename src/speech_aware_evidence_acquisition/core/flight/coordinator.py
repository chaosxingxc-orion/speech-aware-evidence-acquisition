"""Root-owned coordination for one shared tokenizer fit and resident session."""
from __future__ import annotations

import os
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from ..bundle.git_commit import require_clean_study_repo
from ..preparation_fit import fit_phase_runtime
from ..session.serving import assert_identity_matches, find_resident_session
from ..session.worker import attach_worker_session
from .lease import GenerationLease, WorkerExecutionPolicy


class CoordinatorError(RuntimeError):
    """A root-owned fit could not safely establish or retain serving custody."""


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _event(event: str, *, event_path: Path | None = None, **fields: object) -> None:
    """Emit only lifecycle metadata; never print prompts, tokens or raw payloads."""
    import json

    payload = {"component": "coordinate-fit", "event": event, **fields}
    line = json.dumps(payload, sort_keys=True)
    if event_path is not None:
        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    print(line, flush=True)


def coordinate_fit(
    runtime,
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    output: Path,
    owner: str,
    expected_session_id: str,
    contact_cap: int,
    model_fragment: str,
    lease_factory: Callable = GenerationLease.acquire,
    fit_runner: Callable = fit_phase_runtime,
    attach_runner: Callable = attach_worker_session,
    find_resident: Callable = find_resident_session,
    process_factory: Callable = subprocess.Popen,
    sleep: Callable = time.sleep,
    monotonic: Callable = time.monotonic,
    ready_timeout_seconds: float = 120.0,
    study_head_factory: Callable = require_clean_study_repo,
    hold_wrapper_foreground: bool = True,
    pid_alive: Callable[[int], bool] = _pid_alive,
) -> Mapping[str, object]:
    """Run a fit under a root lease, starting at most one existing wrapper.

    Materialization is performed inside :func:`fit_phase_runtime` before its
    injected attach callback. The callback therefore is the sole transition
    from CPU preparation to serving startup and tokenizer contact. A cold
    failure deliberately leaves lease metadata and any started wrapper for
    root reconciliation; this function never kills or restarts either one.
    """
    repo_root, data_root, runtime_root, output = map(
        Path, (repo_root, data_root, runtime_root, output)
    )
    if not owner.strip() or not expected_session_id.strip():
        raise CoordinatorError("coordinate-fit requires nonempty owner and expected session id")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", expected_session_id) is None:
        raise CoordinatorError("expected session id must be one plain path segment")
    if isinstance(contact_cap, bool) or not isinstance(contact_cap, int) or contact_cap < 1:
        raise CoordinatorError("coordinate-fit requires a positive contact cap")
    context = runtime.preparation_context()
    required_identity = context["required_identity"]
    host = required_identity.get("host")
    port = required_identity.get("port")
    if not isinstance(host, str) or not host.strip() or isinstance(port, bool) or not isinstance(port, int) or port < 1:
        raise CoordinatorError("fit serving identity must provide a nonempty host and positive port")
    warm = output.is_file()
    event_path = data_root / "coordination" / f"{expected_session_id}.coordinate-fit.jsonl"

    def event(name: str, **fields: object) -> None:
        event_fields = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "monotonic_seconds": time.monotonic(),
            "run_id": context["run_id"],
            "attempt_id": context["attempt_id"],
            "session_id": expected_session_id,
            **fields,
        }
        _event(name, event_path=event_path, **event_fields)

    resident = None
    if not warm:
        resident = find_resident(data_root)
        if resident is not None:
            _, document = resident
            if document.get("session_id") != expected_session_id:
                raise CoordinatorError("resident session differs from expected session; refusing model start")
            try:
                assert_identity_matches(document, required_identity)
            except Exception as error:  # noqa: BLE001 -- preserve exact identity refusal
                raise CoordinatorError(f"resident session identity mismatch; refusing model start: {error}") from error

    if warm:
        event("warm-fit-start", output=str(output))
        result = fit_runner(runtime, output, policy=None, contact_cap=contact_cap)
        event("warm-fit-complete", output=str(output))
        return {**result, "coordinator": {"warm": True, "wrapper_started": False, "session_reused": False}}

    lease = lease_factory(
        data_root,
        owner=owner,
        run_id=context["run_id"],
        attempt_id=context["attempt_id"],
        session_id=expected_session_id,
        study_head=study_head_factory(repo_root),
    )
    wrapper_started = False
    monitor_started = False
    wrapper_process = None
    monitor_process = None
    monitor_owned = False
    log_handle = None
    monitor_log_handle = None
    monitor_receipt = data_root / "coordination" / f"{expected_session_id}.monitor-owner.json"

    def start_wrapper() -> None:
        nonlocal wrapper_started, wrapper_process, log_handle
        log_path = data_root / "serving" / f"{expected_session_id}.coordinate-fit.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("ab")
        env = os.environ.copy()
        env.update({
            "SPEECHRL_DATA_DIR": str(data_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{repo_root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep),
            "SAEA_REPO_ROOT": str(repo_root),
        })
        command = [
            "bash", str(repo_root / "scripts/serving_session.sh"), "start", model_fragment,
            "--session-id", expected_session_id, "--host", host, "--port", str(port),
            "--runtime-root", str(runtime_root),
        ]
        wrapper_process = process_factory(
            command, cwd=str(repo_root), env=env, stdout=log_handle, stderr=subprocess.STDOUT,
        )
        wrapper_started = True
        event("serving-wrapper-started", session_id=expected_session_id)

    def wait_for_session() -> tuple[Path, Mapping[str, object]]:
        deadline = monotonic() + ready_timeout_seconds
        while True:
            resident_now = find_resident(data_root)
            if resident_now is not None:
                session_dir, document = resident_now
                if document.get("session_id") != expected_session_id:
                    raise CoordinatorError("a different resident session appeared; wrapper remains for root reconciliation")
                try:
                    assert_identity_matches(document, required_identity)
                except Exception as error:  # noqa: BLE001
                    raise CoordinatorError(f"started resident identity mismatch; wrapper remains: {error}") from error
                return Path(session_dir), document
            if wrapper_process is not None and wrapper_process.poll() is not None:
                raise CoordinatorError(f"serving wrapper exited before session became ready (code {wrapper_process.returncode})")
            if monotonic() >= deadline:
                raise CoordinatorError("serving wrapper did not publish an identity-matching session before timeout")
            sleep(0.25)

    def start_monitor() -> None:
        nonlocal monitor_started, monitor_process, monitor_owned, monitor_log_handle
        if not wrapper_started:
            try:
                receipt = json.loads(monitor_receipt.read_text(encoding="utf-8"))
            except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError) as error:
                raise CoordinatorError("matching resident session has no readable monitor ownership receipt") from error
            pid = receipt.get("pid") if isinstance(receipt, Mapping) else None
            if (
                not isinstance(receipt, Mapping)
                or receipt.get("session_id") != expected_session_id
                or not isinstance(pid, int)
                or not pid_alive(pid)
            ):
                raise CoordinatorError("matching resident session monitor is not owned and healthy")
            event("serving-monitor-reused", session_id=expected_session_id, pid=pid)
            return
        if monitor_receipt.exists():
            try:
                old = json.loads(monitor_receipt.read_text(encoding="utf-8"))
                old_pid = old.get("pid") if isinstance(old, Mapping) else None
            except (OSError, UnicodeError, json.JSONDecodeError):
                old_pid = None
            if isinstance(old_pid, int) and pid_alive(old_pid):
                raise CoordinatorError("live monitor ownership receipt blocks a second monitor")
            monitor_receipt.unlink(missing_ok=True)
        monitor_log = data_root / "serving" / f"{expected_session_id}.monitor.log"
        monitor_log.parent.mkdir(parents=True, exist_ok=True)
        monitor_log_handle = monitor_log.open("ab")
        command = [
            sys.executable, str(repo_root / "scripts/serving_monitor.py"), "sample",
            "--session-id", expected_session_id, "--data-root", str(data_root),
            "--host", host, "--port", str(port), "--interval", "10",
        ]
        monitor_process = process_factory(command, cwd=str(repo_root), env=os.environ | {
            "SPEECHRL_DATA_DIR": str(data_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{repo_root / 'src'}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep),
        }, stdout=monitor_log_handle, stderr=monitor_log_handle)
        pid = getattr(monitor_process, "pid", None)
        if isinstance(pid, bool) or not isinstance(pid, int) or pid < 1:
            raise CoordinatorError("monitor process did not expose a valid pid")
        monitor_receipt.parent.mkdir(parents=True, exist_ok=True)
        monitor_receipt.write_text(json.dumps({
            "schema": "saea-coordinate-fit-monitor-owner-v1",
            "session_id": expected_session_id, "pid": pid,
            "coordinator_pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }, sort_keys=True) + "\n", encoding="utf-8")
        monitor_owned = True
        monitor_started = True
        event("serving-monitor-started", session_id=expected_session_id, pid=pid, interval_seconds=10)

    def cleanup_monitor() -> None:
        if not monitor_owned or monitor_process is None or wrapper_process is None:
            return
        if wrapper_process.poll() is None:
            return
        owner_pid = None
        try:
            receipt = json.loads(monitor_receipt.read_text(encoding="utf-8"))
            owner_pid = receipt.get("pid") if isinstance(receipt, Mapping) else None
        except (OSError, UnicodeError, json.JSONDecodeError):
            return
        if owner_pid != getattr(monitor_process, "pid", None):
            return
        if monitor_process.poll() is None:
            monitor_process.terminate()
            monitor_process.wait(timeout=10)
        monitor_receipt.unlink(missing_ok=True)
        if monitor_log_handle is not None:
            monitor_log_handle.close()

    def close_logs() -> None:
        if log_handle is not None and not log_handle.closed:
            log_handle.flush()
            log_handle.close()
        if monitor_log_handle is not None and not monitor_log_handle.closed and not monitor_owned:
            monitor_log_handle.flush()
            monitor_log_handle.close()

    def attach_after_materialization(**kwargs):
        nonlocal resident
        event("materialization-complete", sample_count=len(context["sample_ids"]))
        if resident is None:
            start_wrapper()
            resident = wait_for_session()
            start_monitor()
        else:
            start_monitor()
        original_policy = kwargs.pop("policy", None)
        policy = WorkerExecutionPolicy(expected_session_id, lease.token)
        if original_policy is not policy and original_policy != policy:
            raise CoordinatorError("fit attach callback supplied a policy different from the root lease")
        return attach_runner(policy=original_policy, **kwargs)

    def hold_wrapper() -> None:
        if not wrapper_started or not hold_wrapper_foreground:
            return
        while wrapper_process is not None and wrapper_process.poll() is None:
            sleep(1.0)
        event("serving-wrapper-exited", returncode=getattr(wrapper_process, "returncode", None))

    event("fit-start", warm=False)
    try:
        with lease:
            policy = WorkerExecutionPolicy(expected_session_id, lease.token)
            result = fit_runner(
                runtime, output, policy=policy, contact_cap=contact_cap,
                attach=attach_after_materialization,
            )
    except Exception as error:  # noqa: BLE001 -- lifecycle status must be durable and visible
        event("fit-failed", error_type=type(error).__name__, error=str(error), lease_metadata_preserved=True)
        hold_wrapper()
        raise
    finally:
        cleanup_monitor()
        if wrapper_process is None or wrapper_process.poll() is not None or monitor_process is None:
            close_logs()
    if not isinstance(result, Mapping):
        raise CoordinatorError("fit runner returned no structured receipt")
    compact = {key: result[key] for key in ("path", "sha256", "cache", "contact_class") if key in result}
    event("fit-receipt-published", output=compact)
    hold_wrapper()
    cleanup_monitor()
    close_logs()
    return {
        **result,
        "coordinator": {
            "warm": False, "wrapper_started": wrapper_started,
            "session_reused": not wrapper_started, "monitor_started": monitor_started,
        },
    }
