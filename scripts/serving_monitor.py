#!/usr/bin/env python3
"""GPU + server + host-memory monitor for the always-on serving session (E7).

    python scripts/serving_monitor.py sample --session-id ID [--interval 10]
    python scripts/serving_monitor.py summarize --session-id ID [--from T0] [--to T1]

``sample`` appends one JSONL line per interval to ``$SPEECHRL_DATA_DIR/
serving/<session-id>/monitor.jsonl``: nvidia-smi utilization/memory/power/
pstate/clocks, ``GET /slots`` busy-vs-idle, a cumulative ``requests_total``
derived from slot task-id changes, ``GET /metrics`` when the server has it,
and ``host_memory`` -- the Windows host's total/free GB and the ``vmmemWSL``
working set beside the VM's own ``MemTotal``/``MemAvailable`` (E7c, added
after the 2026-09-07 host-memory incident: see
:func:`speech_aware_evidence_acquisition.core.session.serving.read_host_memory`).
``summarize`` prints the parked/active accounting through
``core.session.serving.summarize_monitor_samples`` -- the SAME function the
flight runtime folds into its seal receipt, so a hand-reported number and a
sealed one cannot disagree. Neither subcommand is a model contact: both
endpoints and the host-memory reading are read-only and no completion is
requested. See docs/readiness/2026-09-07-always-on-serving-operating-note.md.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.session.serving import (  # noqa: E402
    MONITOR_JSONL_NAME,
    SERVING_MONITOR_SAMPLE_SCHEMA,
    read_host_memory,
    read_monitor_samples,
    serving_session_dir,
    summarize_monitor_samples as summarize,
)

GPU_FIELDS = ("utilization_percent", "memory_used_mib", "power_watts", "pstate", "clocks_sm_mhz")
NVIDIA_SMI_QUERY = "utilization.gpu,memory.used,power.draw,pstate,clocks.sm"


def _number(text: object) -> float | None:
    try:
        return float(str(text))
    except (TypeError, ValueError):
        return None


def read_gpu(run=subprocess.run) -> dict[str, object] | None:
    """One nvidia-smi row, or None when the card cannot be read (a monitor
    that cannot see the GPU keeps sampling the server rather than dying)."""

    try:
        completed = run(
            ["nvidia-smi", f"--query-gpu={NVIDIA_SMI_QUERY}", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    rows = (completed.stdout or "").strip().splitlines()
    if getattr(completed, "returncode", 1) != 0 or not rows:
        return None
    parts = [part.strip() for part in rows[0].split(",")]
    if len(parts) != len(GPU_FIELDS):
        return None
    sample = dict(zip(GPU_FIELDS, parts))
    return {name: (sample[name] if name == "pstate" else _number(sample[name])) for name in GPU_FIELDS}


def _get(url: str, timeout_seconds: float) -> str | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            return response.read().decode("utf-8")
    except (OSError, urllib.error.HTTPError, UnicodeError):
        return None


def read_slots(base_url: str, *, get=_get) -> tuple[dict[str, object] | None, dict[int, object]]:
    """``GET /slots`` as busy/idle counts plus each slot's current task id."""

    body = get(f"{base_url}/slots", 10.0)
    try:
        slots = json.loads(body) if body is not None else None
    except json.JSONDecodeError:
        slots = None
    if not isinstance(slots, list):
        return None, {}
    busy = sum(1 for slot in slots if isinstance(slot, Mapping) and slot.get("is_processing"))
    tasks = {
        int(slot["id"]): slot.get("id_task")
        for slot in slots
        if isinstance(slot, Mapping) and isinstance(slot.get("id"), int)
    }
    return {"total": len(slots), "busy": busy, "idle": len(slots) - busy}, tasks


def read_metrics(base_url: str, *, get=_get) -> dict[str, float] | None:
    """``GET /metrics`` (Prometheus text) as ``{metric: value}``, or None.

    The pinned fragments do NOT pass ``--metrics`` -- that flag would change
    the argv and so the serving identity every flight compares -- so an
    absent /metrics is the normal case, not a fault."""

    body = get(f"{base_url}/metrics", 10.0)
    if body is None:
        return None
    values: dict[str, float] = {}
    for line in body.splitlines():
        if line.startswith("#") or not line.startswith("llamacpp:"):
            continue
        metric, _, number = line[len("llamacpp:"):].strip().partition(" ")
        parsed = _number(number.strip())
        if parsed is not None:
            values[metric] = parsed
    return values or None


def count_new_requests(previous: Mapping[int, object], current: Mapping[int, object]) -> int:
    """New tasks that occupied a slot between two ``/slots`` polls.

    llama-server exposes no completed-request counter; this is the honest
    substitute -- monotone and a LOWER BOUND at the sampling interval (two
    requests sharing one slot between polls count once)."""

    return sum(
        1
        for slot_id, task in current.items()
        if task is not None and previous.get(slot_id) != task
    )


def build_sample(
    *,
    now: float,
    gpu: Mapping[str, object] | None,
    slots: Mapping[str, object] | None,
    metrics: Mapping[str, float] | None,
    requests_total: int,
    host_memory: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema": SERVING_MONITOR_SAMPLE_SCHEMA,
        "sampled_at": now,
        "sampled_at_iso": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
        "gpu": dict(gpu) if gpu is not None else None,
        "slots": dict(slots) if slots is not None else None,
        "metrics": dict(metrics) if metrics is not None else None,
        "host_memory": dict(host_memory) if host_memory is not None else None,
        "requests_total": requests_total,
        "server_ok": slots is not None,
    }


def sample_loop(args) -> int:
    session_dir = serving_session_dir(args.data_root, args.session_id)
    if not session_dir.is_dir():
        raise SystemExit(f"no serving session directory at {session_dir}")
    path = session_dir / MONITOR_JSONL_NAME
    base_url = f"http://{args.host}:{args.port}"
    previous_tasks: dict[int, object] = {}
    requests_total = 0
    deadline = time.monotonic() + args.duration if args.duration else None
    while True:
        slots, tasks = read_slots(base_url)
        requests_total += count_new_requests(previous_tasks, tasks)
        previous_tasks = tasks
        sample = build_sample(
            now=time.time(),
            gpu=read_gpu(),
            slots=slots,
            metrics=read_metrics(base_url),
            requests_total=requests_total,
            host_memory=read_host_memory(),
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, ensure_ascii=False, sort_keys=True) + "\n")
        if deadline is not None and time.monotonic() >= deadline:
            return 0
        time.sleep(args.interval)


def summarize_command(args) -> int:
    session_dir = serving_session_dir(args.data_root, args.session_id)
    print(
        json.dumps(
            summarize(
                read_monitor_samples(session_dir / MONITOR_JSONL_NAME),
                from_epoch=args.from_epoch,
                to_epoch=args.to_epoch,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--session-id", required=True)
    common.add_argument("--data-root", type=Path, default=None)

    parser = argparse.ArgumentParser(prog="saea-serving-monitor", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    sample = subparsers.add_parser("sample", parents=[common], help="append monitor samples")
    sample.add_argument("--interval", type=float, default=10.0)
    sample.add_argument("--host", default="127.0.0.1")
    sample.add_argument("--port", type=int, default=8080)
    sample.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    sample.set_defaults(handler=sample_loop)
    window = subparsers.add_parser(
        "summarize", parents=[common], help="parked/active accounting over a window"
    )
    window.add_argument("--from", dest="from_epoch", type=float, default=None)
    window.add_argument("--to", dest="to_epoch", type=float, default=None)
    window.set_defaults(handler=summarize_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.data_root is None:
        from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: PLC0415

        args.data_root = data_root()
    return int(args.handler(args))


if __name__ == "__main__":  # pragma: no cover -- operator entry point
    raise SystemExit(main())
