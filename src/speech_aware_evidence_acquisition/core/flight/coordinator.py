"""Root-owned coordination for one shared tokenizer fit and resident session."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Mapping

from ..bundle.git_commit import require_clean_study_repo
from ..preparation_fit import fit_phase_runtime
from ..session.serving import assert_identity_matches, find_resident_session
from ..session.worker import attach_worker_session
from .lease import GenerationLease, WorkerExecutionPolicy


class CoordinatorError(RuntimeError):
    """A root-owned fit could not safely establish or retain serving custody."""


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
    if isinstance(contact_cap, bool) or not isinstance(contact_cap, int) or contact_cap < 1:
        raise CoordinatorError("coordinate-fit requires a positive contact cap")
    context = runtime.preparation_context()
    required_identity = context["required_identity"]
    warm = output.is_file()
    event_path = data_root / "coordination" / f"{expected_session_id}.coordinate-fit.jsonl"

    def event(name: str, **fields: object) -> None:
        _event(name, event_path=event_path, **fields)

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
    log_handle = None

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
            str(repo_root / "scripts/serving_session.sh"), "start", model_fragment,
            "--session-id", expected_session_id, "--runtime-root", str(runtime_root),
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
        nonlocal monitor_started
        command = [
            sys.executable, str(repo_root / "scripts/serving_monitor.py"), "sample",
            "--session-id", expected_session_id, "--interval", "10",
        ]
        process_factory(command, cwd=str(repo_root), env=os.environ | {
            "SPEECHRL_DATA_DIR": str(data_root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": f"{repo_root / 'src'}{os.pathsep}{os.environ.get('PYTHONPATH', '')}".rstrip(os.pathsep),
        }, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        monitor_started = True
        event("serving-monitor-started", session_id=expected_session_id, interval_seconds=10)

    def attach_after_materialization(**kwargs):
        nonlocal resident
        event("materialization-complete", sample_count=len(context["sample_ids"]))
        if resident is None:
            start_wrapper()
            resident = wait_for_session()
            start_monitor()
        else:
            start_monitor()
        return attach_runner(policy=WorkerExecutionPolicy(expected_session_id, lease.token), **kwargs)

    def hold_wrapper() -> None:
        if not wrapper_started or not hold_wrapper_foreground:
            return
        event("fit-receipt-published", output=str(output))
        while wrapper_process is not None and wrapper_process.poll() is None:
            sleep(1.0)
        event("serving-wrapper-exited", returncode=getattr(wrapper_process, "returncode", None))

    event("fit-start", run_id=context["run_id"], attempt_id=context["attempt_id"], warm=False)
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
        if log_handle is not None:
            log_handle.flush()
    event("fit-complete", output=str(output), wrapper_started=wrapper_started, session_reused=not wrapper_started)
    hold_wrapper()
    return {
        **result,
        "coordinator": {
            "warm": False, "wrapper_started": wrapper_started,
            "session_reused": not wrapper_started, "monitor_started": monitor_started,
        },
    }
