#!/usr/bin/env python3
"""Model-free throughput dry run for the obs-pipeline fix (2026-09-08).

Zero model contacts, zero GPU, zero network: this replays the TIMING of a
sealed Earnings-21 attempt through a simulated dispatcher and reports what
``obs_prefetch_depth`` would have bought.

WHAT IT READS (both sealed, both under ``SPEECHRL_DATA_DIR/runs/``; neither
is ever written):

* ``<run>.trace.jsonl`` -- the COST records give one row per window request
  (``latency_seconds``, ``audio_seconds``) and their ids give the per-sample
  window counts in split order (``req-NNNN-iMMMM/cost``);
* ``<run>.server.log`` -- llama-server's own microsecond clock. Trace records
  carry no timestamps by contract, so the absolute timeline comes from the
  server's ``slot launch_slot_`` (a task takes a slot) and ``slot release``
  (it gives it back) lines. Those two are the send/receive boundary of every
  request as the SERVER saw it, which is exactly the resource this fix is
  about: slot occupancy.

The log's stamp is ``<minutes>.<seconds>.<milliseconds>.<microseconds>``
(llama.cpp's own format), so ``1.04.033.778`` is 64.033778 s after the
server started.

WHAT IT MEASURES on that timeline:

* mean busy slots, the share of wall with ZERO slots busy, windows per
  minute -- the three numbers every flight closure must report from now on;
* the per-call CPU phase: the gap between the last release of call N and the
  first launch of call N+1. With the sequential driver, nothing is in flight
  during that gap, so it IS the decode/cut/encode/register time plus the
  driver's own per-sample overhead -- measured, not modelled.

WHAT IT SIMULATES: a W-slot FIFO dispatcher fed by a driver with L samples of
lookahead, using the MEASURED per-request service times and the MEASURED
per-call CPU phases. L = 0 is today's driver (cut sample N+1 only after
sample N's last window is answered); L = 1 is ``obs_prefetch_depth: 1``. The
model's fidelity is reported, not assumed: the L = 0 arm's predicted wall is
printed beside the measured wall, and a receipt that disagrees with reality
is a receipt that says so.

STATED ASSUMPTIONS (the honest limits of the projection):

1. per-request service times are held FIXED across arms. They were measured
   with the server mostly saturated (65.4 % of the sealed wall had all six
   slots busy), which is the regime the pipelined arm runs in, but a busier
   server can still decode each request slightly slower -- so the predicted
   gain is an upper bound on the scheduling component, not a guarantee;
2. the CPU phase is held fixed too. Prefetch moves it off the critical path;
   it does not make it cheaper, and one extra cutting thread is well inside
   the host's 24 cores;
3. requests are assigned to slots greedily in sample order, which is the
   order the driver submits them; it does not model the server's own
   scheduler beyond slot count.

Usage (nothing is written without ``--write``)::

    python scripts/obs_pipeline_dry_run.py
    python scripts/obs_pipeline_dry_run.py --write

Authorizes nothing: no contact, no server, no scoring, no Stage-3 activity.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import re
import statistics
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECEIPT_DIR = (
    REPO / "docs" / "checks" / "speech-aware-evidence-acquisition"
    / "2026-09-08-e21-obs-pipeline"
)
RECEIPT_NAME = "obs-pipeline-dry-run.json"
SCHEMA = "saea-obs-pipeline-dry-run-v1"

DEFAULT_RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
#: The sealed comparator's serving geometry (configs/model/
#: q4km-e21-buf90-mmproj-gpu-04ccc72a-np6.json ``serving_geometry.slots``).
DEFAULT_SLOTS = 6
#: The depths compared. 0 is today's driver, by definition.
DEFAULT_DEPTHS = (0, 1)

_STAMP = re.compile(r"^(\d+)\.(\d\d)\.(\d\d\d)\.(\d\d\d) ")
_LAUNCH = re.compile(r"slot launch_slot_: id\s+(\d+) \| task (\d+) \| processing task")
_RELEASE = re.compile(r"slot\s+release: id\s+(\d+) \| task (\d+) \|")


class DryRunError(RuntimeError):
    """The sealed inputs do not support the measurement -- refuse, never guess."""


# ---------------------------------------------------------------------------
# Sealed inputs
# ---------------------------------------------------------------------------


def data_root() -> Path:
    raw = os.environ.get("SPEECHRL_DATA_DIR")
    if not raw:
        raise DryRunError("SPEECHRL_DATA_DIR is not set; the sealed runs live under it")
    root = Path(raw)
    if not root.is_dir():
        raise DryRunError(f"SPEECHRL_DATA_DIR {root} is not a directory")
    return root


def resolve_attempt(root: Path, run_id: str, attempt: str | None) -> Path:
    run_dir = root / "runs" / run_id
    if not run_dir.is_dir():
        raise DryRunError(f"no sealed run directory {run_dir}")
    if attempt is not None:
        path = run_dir / attempt
        if not path.is_dir():
            raise DryRunError(f"no attempt directory {path}")
        return path
    candidates = sorted(
        child for child in run_dir.iterdir()
        if child.is_dir() and child.name.startswith("attempt-")
    )
    if len(candidates) != 1:
        raise DryRunError(
            f"{run_dir} holds {len(candidates)} attempt directories; name one with "
            "--attempt so the receipt cannot silently pick a different timeline"
        )
    return candidates[0]


def parse_stamp(line: str) -> float | None:
    """llama.cpp's ``<min>.<sec>.<ms>.<us>`` stamp as seconds, or None."""

    match = _STAMP.match(line)
    if match is None:
        return None
    minutes, seconds, millis, micros = (int(value) for value in match.groups())
    return minutes * 60 + seconds + millis / 1e3 + micros / 1e6


def read_tasks(server_log: Path) -> list[tuple[float, float, int]]:
    """``(launch, release, slot)`` per server task, in LAUNCH order."""

    launches: dict[int, tuple[float, int]] = {}
    releases: dict[int, float] = {}
    order: list[int] = []
    with server_log.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stamp = parse_stamp(line)
            if stamp is None:
                continue
            match = _LAUNCH.search(line)
            if match is not None:
                task = int(match.group(2))
                if task in launches:
                    raise DryRunError(f"server log launches task {task} twice")
                launches[task] = (stamp, int(match.group(1)))
                order.append(task)
                continue
            match = _RELEASE.search(line)
            if match is not None:
                releases[int(match.group(2))] = stamp
    missing = [task for task in order if task not in releases]
    if missing:
        raise DryRunError(
            f"{len(missing)} server tasks never released; this attempt's timeline is "
            "incomplete and cannot be replayed"
        )
    return [(launches[task][0], releases[task], launches[task][1]) for task in order]


def read_window_counts(trace: Path) -> tuple[list[str], dict[str, int], float]:
    """Per-sample window counts in split order, plus total audio seconds."""

    counts: Counter = Counter()
    audio_seconds = 0.0
    with trace.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            document = json.loads(line)
            if document["channel"] != "COST":
                continue
            record_id = str(document["record_id"])
            if "-i" not in record_id:
                raise DryRunError(
                    f"COST record {record_id!r} is not a per-window obs request; this "
                    "replay only understands the obs-agent-loop slice protocol"
                )
            counts[record_id.split("-i")[0]] += 1
            audio_seconds += float(document["payload"]["audio_seconds"])
    if not counts:
        raise DryRunError(f"{trace} carries no COST records")
    return sorted(counts), dict(counts), audio_seconds


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def occupancy(intervals, slots: int) -> dict[str, float]:
    """Mean busy slots, zero-busy share and wall over a set of intervals."""

    events: list[tuple[float, int]] = []
    for start, end in intervals:
        events.append((start, 1))
        events.append((end, -1))
    events.sort()
    busy = 0
    previous = events[0][0]
    held: Counter = Counter()
    for stamp, delta in events:
        held[busy] += stamp - previous
        previous = stamp
        busy += delta
    total = sum(held.values())
    if total <= 0:
        raise DryRunError("degenerate timeline: zero wall")
    mean_busy = sum(level * seconds for level, seconds in held.items()) / total
    return {
        "wall_seconds": total,
        "mean_busy_slots": mean_busy,
        "mean_slot_utilisation_pct": 100.0 * mean_busy / slots,
        "zero_busy_share_pct": 100.0 * held[0] / total,
        "zero_busy_seconds": held[0],
        "all_slots_busy_share_pct": 100.0 * held[slots] / total,
    }


def measure(tasks, sample_ids, counts, slots: int) -> dict:
    """What the sealed attempt actually did, and the per-call CPU phases."""

    total_windows = sum(counts.values())
    if len(tasks) != total_windows:
        raise DryRunError(
            f"the server log holds {len(tasks)} tasks but the trace holds "
            f"{total_windows} window requests; the two do not describe one attempt"
        )
    groups: list[list[tuple[float, float, int]]] = []
    cursor = 0
    for sample_id in sample_ids:
        size = counts[sample_id]
        groups.append(tasks[cursor : cursor + size])
        cursor += size
    per_sample = []
    gaps = []
    previous_end = None
    for sample_id, group in zip(sample_ids, groups):
        start = min(launch for launch, _release, _slot in group)
        end = max(release for _launch, release, _slot in group)
        if previous_end is not None:
            gaps.append(start - previous_end)
        per_sample.append(
            {
                "sample_id": sample_id,
                "windows": len(group),
                "first_launch_seconds": start,
                "last_release_seconds": end,
                "service_seconds": [release - launch for launch, release, _slot in group],
            }
        )
        previous_end = end
    intervals = [(launch, release) for launch, release, _slot in tasks]
    stats = occupancy(intervals, slots)
    wall = max(release for _launch, release, _slot in tasks) - min(
        launch for launch, _release, _slot in tasks
    )
    return {
        "windows": total_windows,
        "samples": len(sample_ids),
        "wall_seconds": wall,
        "windows_per_minute": total_windows / (wall / 60.0),
        "mean_busy_slots": stats["mean_busy_slots"],
        "mean_slot_utilisation_pct": stats["mean_slot_utilisation_pct"],
        "zero_busy_share_pct": stats["zero_busy_share_pct"],
        "zero_busy_seconds": stats["zero_busy_seconds"],
        "all_slots_busy_share_pct": stats["all_slots_busy_share_pct"],
        "call_boundary_gaps": {
            "count": len(gaps),
            "mean_seconds": statistics.mean(gaps),
            "median_seconds": statistics.median(gaps),
            "min_seconds": min(gaps),
            "max_seconds": max(gaps),
            "total_seconds": sum(gaps),
            "share_of_zero_busy_pct": 100.0 * sum(gaps) / stats["zero_busy_seconds"],
        },
        "per_sample": per_sample,
    }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def simulate(per_sample, cpu_seconds, slots: int, depth: int) -> dict:
    """A ``slots``-wide FIFO dispatcher behind a driver with ``depth``
    samples of lookahead.

    ``depth`` workers + 1 run at once; each takes its sample's CPU phase and
    then dispatches that sample's windows into the SHARED slot pool, so at
    depth >= 1 sample N+1's first windows can occupy slots sample N's tail is
    releasing. At depth 0 there is exactly one worker, which is the current
    driver: nothing overlaps a call boundary."""

    if depth < 0:
        raise DryRunError(f"depth must be >= 0, got {depth}")
    workers = [0.0] * (depth + 1)
    slot_free = [0.0] * slots
    heapq.heapify(workers)
    heapq.heapify(slot_free)
    intervals: list[tuple[float, float]] = []
    sample_ends: list[float] = []
    for index, sample in enumerate(per_sample):
        cut_start = heapq.heappop(workers)
        cut_end = cut_start + cpu_seconds[index]
        last = cut_end
        for service in sample["service_seconds"]:
            free_at = heapq.heappop(slot_free)
            start = max(free_at, cut_end)
            end = start + service
            heapq.heappush(slot_free, end)
            intervals.append((start, end))
            last = max(last, end)
        heapq.heappush(workers, last)
        sample_ends.append(last)
    wall = max(sample_ends)
    stats = occupancy(intervals, slots)
    windows = len(intervals)
    return {
        "prefetch_depth": depth,
        "dispatch_slots": slots,
        "wall_seconds": wall,
        "windows": windows,
        "windows_per_minute": windows / (wall / 60.0),
        "mean_busy_slots": stats["mean_busy_slots"],
        "mean_slot_utilisation_pct": stats["mean_slot_utilisation_pct"],
        "zero_busy_share_pct": stats["zero_busy_share_pct"],
        "zero_busy_seconds": stats["zero_busy_seconds"],
    }


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_receipt(run_id, attempt_dir, slots, depths) -> dict:
    trace = attempt_dir / f"{run_id}.trace.jsonl"
    server_log = attempt_dir / f"{run_id}.server.log"
    for path in (trace, server_log):
        if not path.is_file():
            raise DryRunError(f"sealed input {path} is missing")
    sample_ids, counts, audio_seconds = read_window_counts(trace)
    tasks = read_tasks(server_log)
    measured = measure(tasks, sample_ids, counts, slots)
    gaps = [
        measured["per_sample"][index]["first_launch_seconds"]
        - measured["per_sample"][index - 1]["last_release_seconds"]
        for index in range(1, len(sample_ids))
    ]
    # The first call has no measured predecessor: give it the median of the
    # 43 that do rather than inventing a number or pretending it is free.
    cpu_seconds = [statistics.median(gaps)] + gaps
    arms = [simulate(measured["per_sample"], cpu_seconds, slots, depth) for depth in depths]
    by_depth = {arm["prefetch_depth"]: arm for arm in arms}
    if 0 not in by_depth:
        raise DryRunError("depth 0 must be simulated: it is the arm the model is checked against")
    baseline = by_depth[0]
    fidelity = {
        "measured_wall_seconds": measured["wall_seconds"],
        "depth0_predicted_wall_seconds": baseline["wall_seconds"],
        "depth0_wall_error_pct": 100.0
        * (baseline["wall_seconds"] - measured["wall_seconds"])
        / measured["wall_seconds"],
        "measured_windows_per_minute": measured["windows_per_minute"],
        "depth0_predicted_windows_per_minute": baseline["windows_per_minute"],
    }
    # The purely MEASURED bound, free of every simulation assumption: the
    # sealed attempt's own wall with its own idle seconds removed. Nothing can
    # beat this without also making requests faster, and the whole of that
    # idle is the call boundaries this fix targets.
    recovered_wall = measured["wall_seconds"] - measured["zero_busy_seconds"]
    measured_ceiling = {
        "basis": (
            "the sealed attempt's own wall minus its own zero-busy seconds; "
            "measured, not simulated"
        ),
        "wall_seconds": recovered_wall,
        "windows_per_minute": measured["windows"] / (recovered_wall / 60.0),
        "windows_per_minute_gain_pct": 100.0
        * (
            measured["windows"] / (recovered_wall / 60.0)
            - measured["windows_per_minute"]
        )
        / measured["windows_per_minute"],
    }
    deltas = {}
    for depth, arm in sorted(by_depth.items()):
        if depth == 0:
            continue
        deltas[f"depth{depth}_vs_depth0"] = {
            "wall_seconds_saved": baseline["wall_seconds"] - arm["wall_seconds"],
            "wall_reduction_pct": 100.0
            * (baseline["wall_seconds"] - arm["wall_seconds"])
            / baseline["wall_seconds"],
            "windows_per_minute_before": baseline["windows_per_minute"],
            "windows_per_minute_after": arm["windows_per_minute"],
            "windows_per_minute_gain_pct": 100.0
            * (arm["windows_per_minute"] - baseline["windows_per_minute"])
            / baseline["windows_per_minute"],
            "zero_busy_share_pct_before": baseline["zero_busy_share_pct"],
            "zero_busy_share_pct_after": arm["zero_busy_share_pct"],
            "mean_slot_utilisation_pct_before": baseline["mean_slot_utilisation_pct"],
            "mean_slot_utilisation_pct_after": arm["mean_slot_utilisation_pct"],
        }
    # The per-sample service lists are the raw replay input; they are large
    # (1,593 floats) and their summary is what a reader needs.
    services = [
        service for sample in measured["per_sample"] for service in sample["service_seconds"]
    ]
    summary = dict(measured)
    summary["per_sample"] = [
        {
            "sample_id": sample["sample_id"],
            "windows": sample["windows"],
            "first_launch_seconds": sample["first_launch_seconds"],
            "last_release_seconds": sample["last_release_seconds"],
            "service_seconds_total": sum(sample["service_seconds"]),
        }
        for sample in measured["per_sample"]
    ]
    return {
        "schema": SCHEMA,
        "date": "2026-09-08",
        "purpose": (
            "Quantify, model-free, what obs_prefetch_depth would have bought the "
            "sealed Earnings-21 comparator: the measured slot occupancy and call- "
            "boundary idle of that attempt, replayed through a simulated dispatcher "
            "at prefetch depth 0 and 1."
        ),
        "execution_profile": "model-free-check",
        "contacts": 0,
        "inputs": {
            "run_id": run_id,
            "attempt_id": attempt_dir.name,
            "trace_sha256": sha256_file(trace),
            "trace_bytes": trace.stat().st_size,
            "server_log_sha256": sha256_file(server_log),
            "server_log_bytes": server_log.stat().st_size,
            "audio_seconds_metered": audio_seconds,
        },
        "geometry": {
            "dispatch_slots": slots,
            "source": (
                "configs/model/q4km-e21-buf90-mmproj-gpu-04ccc72a-np6.json "
                "serving_geometry.slots"
            ),
        },
        "measured": summary,
        "service_seconds": {
            "count": len(services),
            "mean": statistics.mean(services),
            "median": statistics.median(services),
            "min": min(services),
            "max": max(services),
        },
        "cpu_phase_seconds": {
            "measured_boundaries": len(gaps),
            "first_sample_assumed": cpu_seconds[0],
            "assumption": (
                "the first call has no measured predecessor gap, so it takes the "
                "median of the 43 that do"
            ),
        },
        "simulated": arms,
        "model_fidelity": fidelity,
        "measured_ceiling": measured_ceiling,
        "deltas": deltas,
        "assumptions": [
            "per-request service times are held fixed across arms; they were measured "
            "with the server mostly saturated, so the predicted gain is an upper bound "
            "on the scheduling component, not a guarantee",
            "the per-call CPU phase is held fixed; prefetch moves it off the critical "
            "path, it does not make it cheaper",
            "requests are assigned to slots greedily in sample order, the order the "
            "driver submits them; the server's own scheduler is modelled only by its "
            "slot count",
            "the depth-1 arm's ~100 % modelled slot occupancy is the MODEL's ceiling, "
            "not a promise: it assumes a window is always ready the instant a slot "
            "frees. The measured bound that survives every assumption is "
            "measured_ceiling, computed from the sealed attempt's own idle seconds",
            "greedy decoding is not bitwise reproducible across batch compositions, so "
            "a pipelined re-fly of a sealed cell will differ in text; the E21 own-null "
            "replicate is the measurement of that noise",
        ],
        "authorizes": (
            "nothing. No contact, no server, no scoring and no Stage-3 activity; "
            "no committed fragment is flipped to a non-zero depth by this receipt."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Obs-pipeline throughput dry run")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--attempt", default=None)
    parser.add_argument("--slots", type=int, default=DEFAULT_SLOTS)
    parser.add_argument(
        "--depth", type=int, action="append", default=None,
        help="prefetch depth to simulate; repeatable (default: 0 and 1)",
    )
    parser.add_argument("--write", action="store_true", help="write the receipt")
    args = parser.parse_args(argv)

    depths = tuple(args.depth) if args.depth else DEFAULT_DEPTHS
    if 0 not in depths:
        depths = (0, *depths)
    attempt_dir = resolve_attempt(data_root(), args.run_id, args.attempt)
    receipt = build_receipt(args.run_id, attempt_dir, args.slots, depths)

    measured = receipt["measured"]
    print(f"run              {args.run_id} / {attempt_dir.name}")
    print(f"windows          {measured['windows']} over {measured['samples']} calls")
    print(
        f"measured         {measured['windows_per_minute']:.2f} windows/min, "
        f"{measured['mean_slot_utilisation_pct']:.1f} % mean slot use, "
        f"{measured['zero_busy_share_pct']:.2f} % zero-busy"
    )
    boundaries = measured["call_boundary_gaps"]
    print(
        f"call boundaries  {boundaries['count']} gaps, mean "
        f"{boundaries['mean_seconds']:.2f} s, total {boundaries['total_seconds']:.1f} s "
        f"= {boundaries['share_of_zero_busy_pct']:.1f} % of all zero-busy time"
    )
    for arm in receipt["simulated"]:
        print(
            f"depth {arm['prefetch_depth']}          "
            f"{arm['windows_per_minute']:.2f} windows/min, "
            f"{arm['mean_slot_utilisation_pct']:.1f} % mean slot use, "
            f"{arm['zero_busy_share_pct']:.2f} % zero-busy, "
            f"wall {arm['wall_seconds'] / 3600:.2f} h"
        )
    ceiling = receipt["measured_ceiling"]
    print(
        f"measured ceiling {ceiling['windows_per_minute']:.2f} windows/min "
        f"({ceiling['windows_per_minute_gain_pct']:+.1f} %) if every idle second "
        "were recovered"
    )
    fidelity = receipt["model_fidelity"]
    print(f"model fidelity   depth-0 wall error {fidelity['depth0_wall_error_pct']:+.2f} %")
    for name, delta in receipt["deltas"].items():
        print(
            f"{name}   {delta['windows_per_minute_gain_pct']:+.1f} % windows/min, "
            f"{delta['wall_seconds_saved'] / 60:.1f} min saved"
        )

    if args.write:
        RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
        path = RECEIPT_DIR / RECEIPT_NAME
        path.write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_manifest(RECEIPT_DIR)
        print(f"wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
