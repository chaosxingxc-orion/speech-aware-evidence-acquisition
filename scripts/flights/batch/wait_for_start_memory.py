#!/usr/bin/env python3
"""Wait before prelaunch for stable host memory; never start or retry a worker.

This optional batch-boundary observer leaves frozen workers, scientific settings,
STOP and all attempts untouched. The original process guard rechecks admission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import time

from speech_aware_evidence_acquisition.core.flight.process_guard import (
    MemoryPolicy,
    _sample,
)
from speech_aware_evidence_acquisition.core.session.windows_memory import WindowsMemoryObserver


def wait_for_memory(
    receipt_dir,
    stop_marker,
    start_gib,
    wait_seconds,
    stable_samples,
    *,
    floor_gib=4.0,
    host_reader=None,
    monotonic=time.monotonic,
    sleep=time.sleep,
):
    policy = MemoryPolicy(start_gib=start_gib, floor_gib=floor_gib, interval_seconds=10)
    if (
        isinstance(wait_seconds, bool)
        or not isinstance(wait_seconds, (int, float))
        or not math.isfinite(wait_seconds)
        or not 0 < wait_seconds <= 3600
        or type(stable_samples) is not int
        or not 2 <= stable_samples <= 60
        or wait_seconds < 10 * (stable_samples - 1)
    ):
        raise ValueError(
            "bounded wait and at least two consecutive observations are required"
        )
    if host_reader is None:
        # Reuse the owned transport used by the running-worker guard. Every
        # measurement is fresh; observer failure still stops without reconnect.
        with WindowsMemoryObserver() as observer:
            return wait_for_memory(
                receipt_dir, stop_marker, start_gib, wait_seconds, stable_samples,
                floor_gib=floor_gib, host_reader=observer, monotonic=monotonic,
                sleep=sleep,
            )
    root = Path(receipt_dir)
    root.mkdir(parents=True, exist_ok=False)
    started = monotonic()
    consecutive = 0
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

        def finish(status):
            result = {
                "schema": "saea-precontact-memory-wait-v1",
                "status": status,
                "exit_code": 0 if status == "ready" else 125,
                "worker_started": False,
                "elapsed_seconds": monotonic() - started,
                "start_gib": start_gib,
                "running_floor_gib": policy.floor_gib,
                "wait_seconds": wait_seconds,
                "stable_samples": stable_samples,
                "interval_seconds": 10,
                "stop_marker": str(stop_marker),
                "observer_sha256": hashlib.sha256(
                    Path(__file__).read_bytes()
                ).hexdigest(),
            }
            with (root / "finished.json").open("x") as f:
                f.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
            emit("finished", **result)
            return result

        try:
            while True:
                if Path(stop_marker).exists():
                    return finish("stop-present")
                if monotonic() - started >= wait_seconds:
                    return finish("wait-expired")
                observation = _sample(host_reader, policy)
                available = observation["available_gib"]
                consecutive = (
                    consecutive + 1
                    if not observation["reason"] and available >= start_gib
                    else 0
                )
                emit("sample", **observation, consecutive=consecutive)
                if observation["reason"]:
                    return finish("observation-failed")
                if available < policy.floor_gib:
                    return finish("resource-floor-violation")
                if Path(stop_marker).exists():
                    return finish("stop-present")
                remaining = wait_seconds - (monotonic() - started)
                if remaining <= 0:
                    return finish("wait-expired")
                if consecutive >= stable_samples:
                    return finish("ready")
                sleep(min(10, remaining))
        except (KeyboardInterrupt, InterruptedError):
            return finish("interrupted")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("receipt-dir", "data-root", "stop-marker"):
        parser.add_argument("--" + field, required=True)
    parser.add_argument("--start-gib", type=float, required=True)
    parser.add_argument("--floor-gib", type=float, default=4.0)
    parser.add_argument("--wait-seconds", type=float, required=True)
    parser.add_argument("--stable-samples", type=int, required=True)
    args = parser.parse_args(argv)
    receipt = Path(args.receipt_dir).resolve()
    if not receipt.is_relative_to(Path(args.data_root).resolve() / "coordination"):
        parser.error("receipt must be beneath data-root/coordination")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")

    def interrupted(signum, frame):
        raise InterruptedError("memory observer interrupted")

    prior = signal.signal(signal.SIGTERM, interrupted)
    try:
        result = wait_for_memory(
            receipt,
            args.stop_marker,
            args.start_gib,
            args.wait_seconds,
            args.stable_samples,
            floor_gib=args.floor_gib,
        )
    finally:
        signal.signal(signal.SIGTERM, prior)
    print(json.dumps(result, sort_keys=True))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
