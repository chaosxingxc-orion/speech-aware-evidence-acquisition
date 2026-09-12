#!/usr/bin/env python3
"""GPU + server + host-memory monitor for the always-on serving session (E7).

    python scripts/serving_monitor.py sample --session-id ID [--interval 10] \
        [--host-free-warn-gb 6.0]
    python scripts/serving_monitor.py summarize --session-id ID [--from T0] [--to T1]

``sample`` appends one JSONL line per interval to ``$SPEECHRL_DATA_DIR/
serving/<session-id>/monitor.jsonl``: nvidia-smi utilization/memory/power/
pstate/clocks, ``GET /slots`` busy-vs-idle, a cumulative ``requests_total``
derived from slot task-id changes, ``GET /metrics`` when the server has it,
and ``host_memory`` -- the Windows host's total/free GB and the ``vmmemWSL``
working set beside the VM's own ``MemTotal``/``MemAvailable`` (E7c, added
after the 2026-09-07 host-memory incident: see
:func:`speech_aware_evidence_acquisition.core.session.serving.read_host_memory`).
A sample whose host free GB drops below ``--host-free-warn-gb`` (default
6.0) writes one ``WARN host-memory`` line to ``monitor.log`` beside the
JSONL -- never to stdout -- at most once per minute.
``summarize`` prints the parked/active accounting through
``core.session.serving.summarize_monitor_samples`` -- the SAME function the
flight runtime folds into its seal receipt, so a hand-reported number and a
sealed one cannot disagree; it now also reports the window's host-memory
minimum/last/maximum fields. Neither subcommand is a model contact: both
endpoints and the host-memory reading are read-only and no completion is
requested. See docs/readiness/2026-09-07-always-on-serving-operating-note.md.
"""

from __future__ import annotations

import argparse
import json
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

from speech_aware_evidence_acquisition.core.session.telemetry import (  # noqa: E402,F401
    GPU_FIELDS, NVIDIA_SMI_QUERY, _number, read_gpu,
)

#: The monitor's own operator log, beside ``monitor.jsonl`` in the same
#: session directory -- a WARN line about the host running low on memory is
#: an operator signal, never stdout spam mixed into the JSONL a flight reads.
MONITOR_LOG_NAME = "monitor.log"

#: A host-memory WARN is written at most this often, however low the reading
#: stays: a host parked below the floor for an hour must write one line, not
#: one every sampling interval.
HOST_MEMORY_WARN_INTERVAL_SECONDS = 60.0


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


def warn_host_memory_if_low(
    log_path: Path,
    host_memory: Mapping[str, object] | None,
    *,
    threshold_gb: float,
    sampled_at_iso: str,
    now_monotonic: float,
    last_warn_monotonic: float | None,
) -> float | None:
    """Append one ``WARN host-memory`` line to the monitor's own log
    (``monitor.log``, beside ``monitor.jsonl`` in the same session
    directory) when this sample's host free GB is below ``threshold_gb`` --
    never to stdout, which is the monitor's JSONL data channel, not an
    operator feed. At most once per
    :data:`HOST_MEMORY_WARN_INTERVAL_SECONDS`, so a host parked below the
    floor for an hour writes one line, not 360.

    Returns the monotonic time of the warning just written, or the unchanged
    ``last_warn_monotonic`` when nothing was (no reading, the reading is at
    or above the threshold, or the interval has not yet elapsed) -- the
    caller threads this back in as next call's ``last_warn_monotonic``.
    """

    free_gb = host_memory.get("host_free_gb") if isinstance(host_memory, Mapping) else None
    if isinstance(free_gb, bool) or not isinstance(free_gb, (int, float)):
        return last_warn_monotonic
    if float(free_gb) >= threshold_gb:
        return last_warn_monotonic
    if (
        last_warn_monotonic is not None
        and now_monotonic - last_warn_monotonic < HOST_MEMORY_WARN_INTERVAL_SECONDS
    ):
        return last_warn_monotonic
    with Path(log_path).open("a", encoding="utf-8") as handle:
        handle.write(
            f"{sampled_at_iso} WARN host-memory: host_free_gb={float(free_gb):.2f} < "
            f"--host-free-warn-gb {float(threshold_gb):.2f}\n"
        )
    return now_monotonic


def sample_loop(args) -> int:
    session_dir = serving_session_dir(args.data_root, args.session_id)
    if not session_dir.is_dir():
        raise SystemExit(f"no serving session directory at {session_dir}")
    path = session_dir / MONITOR_JSONL_NAME
    log_path = session_dir / MONITOR_LOG_NAME
    base_url = f"http://{args.host}:{args.port}"
    previous_tasks: dict[int, object] = {}
    requests_total = 0
    last_warn_monotonic: float | None = None
    deadline = time.monotonic() + args.duration if args.duration else None
    while True:
        slots, tasks = read_slots(base_url)
        requests_total += count_new_requests(previous_tasks, tasks)
        previous_tasks = tasks
        host_memory = read_host_memory()
        sample = build_sample(
            now=time.time(),
            gpu=read_gpu(),
            slots=slots,
            metrics=read_metrics(base_url),
            requests_total=requests_total,
            host_memory=host_memory,
        )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(sample, ensure_ascii=False, sort_keys=True) + "\n")
        last_warn_monotonic = warn_host_memory_if_low(
            log_path,
            host_memory,
            threshold_gb=args.host_free_warn_gb,
            sampled_at_iso=sample["sampled_at_iso"],
            now_monotonic=time.monotonic(),
            last_warn_monotonic=last_warn_monotonic,
        )
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
    sample.add_argument(
        "--host-free-warn-gb",
        type=float,
        default=6.0,
        help=(
            "write a WARN host-memory line to monitor.log (not stdout) when the host's "
            "free memory drops below this, at most once per minute"
        ),
    )
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
