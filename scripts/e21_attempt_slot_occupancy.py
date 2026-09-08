#!/usr/bin/env python3
"""Slot-occupancy replay for one attempt's own contact window on a SHARED session log.

Section 6 of `docs/readiness/2026-09-08-e21-obs-pipeline-v1.md` makes three numbers
mandatory at every flight closure: mean slot utilisation, zero-slot share and windows
per minute.  `scripts/obs_pipeline_dry_run.py` measures them from llama-server's own
microsecond clock (``slot launch_slot_`` -> ``slot release``) on an attempt that owned
its server and therefore owned its log.

Under the always-on serving rule the log belongs to the SESSION and holds every flight
of the day, so this script does the same measurement on a slice of it: stamps are
converted to epoch through the session's own ``started_at`` and the tasks whose whole
service falls inside the attempt's contact window are the attempt's tasks.  The parsing
and the occupancy arithmetic are IMPORTED from the dry-run script, never re-implemented,
so the depth-1 arm and the depth-0 receipt are measured by one instrument.

``measure()``'s per-sample grouping is deliberately NOT reused: it assumes each call's
tasks are contiguous in launch order, which is exactly what the dispatcher stops being
true.  What replaces it is the zero-busy RUN structure, which needs no such assumption.

Zero contacts, zero GPU, read-only.

usage: throughput.py <session_dir> <t0_epoch> <t1_epoch> <expected_windows> <label> <out.json>
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
for candidate in (REPO / "src", REPO / "scripts"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import obs_pipeline_dry_run as dry  # noqa: E402

SLOTS = 6


def session_start_epoch(session_dir: Path) -> tuple[float, str]:
    document = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
    raw = str(document["started_at"])
    return datetime.fromisoformat(raw).timestamp(), raw


def read_tasks_in_window(server_log: Path, origin: float, t0: float, t1: float):
    """``(launch_epoch, release_epoch, slot)`` for tasks whose whole service is inside
    the window.  Streamed: the session log is hundreds of megabytes."""

    launches: dict[int, tuple[float, int]] = {}
    order: list[int] = []
    releases: dict[int, float] = {}
    unreleased = 0
    with server_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stamp = dry.parse_stamp(line)
            if stamp is None:
                continue
            epoch = origin + stamp
            if epoch > t1 + 600.0:
                break
            match = dry._LAUNCH.search(line)
            if match is not None:
                task = int(match.group(2))
                launches[task] = (epoch, int(match.group(1)))
                order.append(task)
                continue
            match = dry._RELEASE.search(line)
            if match is not None:
                releases[int(match.group(2))] = epoch
    selected = []
    for task in order:
        launch, slot = launches[task]
        release = releases.get(task)
        if release is None:
            if t0 <= launch <= t1:
                unreleased += 1
            continue
        if launch >= t0 and release <= t1:
            selected.append((launch, release, slot))
    selected.sort()
    return selected, unreleased


def zero_busy_runs(intervals, floor_seconds: float = 1.0):
    """The maximal stretches inside the span with NO slot busy, longest first."""

    events = []
    for start, end in intervals:
        events.append((start, 1))
        events.append((end, -1))
    events.sort()
    runs = []
    busy = 0
    idle_since = None
    for stamp, delta in events:
        if busy == 0 and idle_since is not None and delta == +1:
            length = stamp - idle_since
            if length >= floor_seconds:
                runs.append({"from": idle_since, "to": stamp, "seconds": length})
            idle_since = None
        busy += delta
        if busy == 0:
            idle_since = stamp
    runs.sort(key=lambda row: -row["seconds"])
    return runs


def main(argv: list[str]) -> int:
    if len(argv) < 7:
        print(__doc__)
        return 2
    session_dir = Path(argv[1])
    t0, t1 = float(argv[2]), float(argv[3])
    expected = int(argv[4])
    label = argv[5]
    out = Path(argv[6])

    origin, started_at = session_start_epoch(session_dir)
    tasks, unreleased = read_tasks_in_window(
        session_dir / "server.log", origin, t0, t1
    )
    if not tasks:
        raise SystemExit(f"no server tasks inside {t0}-{t1}; the origin or the window is wrong")
    intervals = [(launch, release) for launch, release, _slot in tasks]
    stats = dry.occupancy(intervals, SLOTS)
    first = min(launch for launch, _r, _s in tasks)
    last = max(release for _l, release, _s in tasks)
    span = last - first
    runs = zero_busy_runs(intervals)
    result = {
        "schema": "saea-e21-attempt-slot-occupancy-v1",
        "label": label,
        "session_dir": str(session_dir),
        "session_started_at": started_at,
        "session_start_epoch": origin,
        "contact_window": {"from": t0, "to": t1, "seconds": t1 - t0},
        "tasks_in_window": len(tasks),
        "expected_windows": expected,
        "task_count_matches_expected": len(tasks) == expected,
        "tasks_launched_in_window_never_released": unreleased,
        "first_launch_epoch": first,
        "last_release_epoch": last,
        "span_seconds": span,
        "windows_per_minute_over_span": len(tasks) / (span / 60.0),
        "windows_per_minute_over_contact_window": len(tasks) / ((t1 - t0) / 60.0),
        "mean_busy_slots": stats["mean_busy_slots"],
        "mean_slot_utilisation_pct": stats["mean_slot_utilisation_pct"],
        "zero_busy_share_pct": stats["zero_busy_share_pct"],
        "zero_busy_seconds": stats["zero_busy_seconds"],
        "all_slots_busy_share_pct": stats["all_slots_busy_share_pct"],
        "zero_busy_runs": {
            "count_at_least_1s": len(runs),
            "total_seconds_at_least_1s": sum(row["seconds"] for row in runs),
            "longest": [
                {
                    "seconds": round(row["seconds"], 3),
                    "from_offset_seconds": round(row["from"] - first, 3),
                }
                for row in runs[:15]
            ],
        },
        "basis": (
            "obs_pipeline_dry_run.parse_stamp / _LAUNCH / _RELEASE / occupancy, applied to "
            "the resident session's own server.log over this attempt's contact window. "
            "Stamps are llama.cpp's own microsecond clock, converted to epoch through "
            "session.json started_at; a task counts for this attempt only if BOTH its launch "
            "and its release fall inside the window."
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        key: result[key] for key in (
            "label", "tasks_in_window", "task_count_matches_expected", "span_seconds",
            "windows_per_minute_over_span", "mean_slot_utilisation_pct",
            "zero_busy_share_pct", "zero_busy_seconds", "all_slots_busy_share_pct",
        )
    }, indent=1))
    print(json.dumps(result["zero_busy_runs"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
