#!/usr/bin/env python3
"""The idle-filler queue's decision function (owner decision 162). Model-free and side-effect free: it
reads markers, the process table, the serving status and git, and prints ONE JSON line
``{"decision": "LAUNCH" | "WAIT" | "HALT", "chunk": k | null, "reason": ..., "checks": {...}}``.

THE RULE, in order (the first rule that fires decides):

1. ``HALT``  -- ``/home/chao/batch-STOP`` exists. A STOP is a failure that needs a root diagnosis; the
   queue never skips past it (a failed chunk is never re-flown or stepped over automatically).
2. ``WAIT``  -- ``/home/chao/mainline-ready`` exists: a main-line chain is flip-ready and has priority.
   The queue never launches a filler while that marker exists; a main-line chain therefore waits at most
   the one chunk already in flight (about 24 GPU-minutes).
3. ``WAIT``  -- a ``core.flight.cli`` / ``batch_driver.sh`` / ``lease_cli`` process is alive.
4. ``WAIT``  -- ``$SPEECHRL_DATA_DIR/locks/flight.lock`` exists.
5. ``WAIT``  -- ``/home/chao/batch-flight-repo.txt`` exists (a stale flight-worktree override; blocker 1).
6. ``WAIT``  -- ``/home/chao/batch-done`` is younger than the grace period (default 300 s), so a
   coordinator queue task that is polling for that marker sees it before a filler chain archives it.
7. ``WAIT``  -- the np4 SLURP session is not resident and healthy: ``scripts/serving_session.sh status
   --session-id serving-slurp-native-candidate-five-train-a-np4-v1`` must report
   ``last_monitor_sample.server_ok`` true, ``slots.busy`` 0, the expected session id, and a monitor sample
   no older than the freshness bound (default 300 s) -- the batch driver's own prelaunch check plus
   freshness.
8. ``LAUNCH k`` -- the lowest chunk k that is UNFLOWN (no ``runs/<run id>`` directory on the data root and
   no launch recorded in the queue state file), MINTED (``coordination/<package>/root-admission-v1.json``
   with status ``decided`` naming the run id) and FLIPPED (``/home/chao/filler-flight-commit-cKK.txt``
   names a commit at which the chunk's experiment fragment -- and chunk 1's smoke -- is ``ready``).
9. ``WAIT``  -- no chunk is eligible (the summary names why for each).

Every path and command is injectable so the rule is unit-tested without a WSL host
(``tests/unit/test_filler_queue_decide.py``).
"""

from __future__ import annotations
import os

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
PACKAGE_RE = re.compile(r"^2026-09-27-slurp-stage3-filler-fold-b-c(\d{2})-v1$")
PROCESS_PATTERN = "core.flight.cli|batch_driver.sh|lease_cli"


@dataclass
class Env:
    home: Path
    data_root: Path
    main: Path
    session: str = SESSION
    grace_seconds: float = 300.0
    monitor_max_age: float = 300.0
    state_file: Path | None = None
    now: Callable[[], float] = time.time
    processes: Callable[[], list[str]] = field(default=lambda: _pgrep())
    serving_status: Callable[[], dict | None] = field(default=lambda: None)
    fragment_at: Callable[[str, str], dict | None] = field(default=lambda commit, relpath: None)


def _pgrep() -> list[str]:
    try:
        out = subprocess.run(["pgrep", "-af", PROCESS_PATTERN], capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return ["<pgrep unavailable>"]
    me = str(os.getpid())
    return [line for line in out.splitlines() if line.strip() and "pgrep" not in line and not line.startswith(me + " ")]


def _serving_status(main: Path, session: str) -> dict | None:
    try:
        run = subprocess.run(["bash", "scripts/serving_session.sh", "status", "--session-id", session],
                             cwd=main, capture_output=True, text=True, timeout=90)
        return json.loads(run.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _fragment_at(main: Path, commit: str, relpath: str) -> dict | None:
    try:
        run = subprocess.run(["git", "-C", str(main), "show", f"{commit}:{relpath}"],
                             capture_output=True, text=True, timeout=60)
        return json.loads(run.stdout) if run.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def chunk_names(k: int) -> dict:
    k2 = f"{k:02d}"
    base = f"filler-fold-b-c{k2}"
    return {
        "run": f"SAEA-SLURP-STAGE3-FILLER-FOLD-B-C{k2}-V1",
        "cell": f"slurp-native-stage3-{base}-v1",
        "smoke_cell": f"slurp-native-stage3-{base}-smoke-4-v1" if k == 1 else None,
        "package": f"slurp-stage3-{base}-v1",
        "commit_file": f"filler-flight-commit-c{k2}.txt",
    }


def registered_chunks(main: Path) -> list[int]:
    readiness = main / "docs" / "readiness"
    out = []
    if readiness.is_dir():
        for entry in readiness.iterdir():
            match = PACKAGE_RE.match(entry.name)
            if match and entry.is_dir():
                out.append(int(match.group(1)))
    return sorted(out)


def launched_chunks(state_file: Path | None) -> set[int]:
    """Chunks the queue launched, in record order: a launch record adds a chunk; a ``released`` record
    (the chain refused before the driver started, so nothing flew) removes it again."""

    out: set[int] = set()
    if state_file and state_file.is_file():
        for line in state_file.read_text(encoding="utf-8").splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict) or not isinstance(record.get("chunk"), int):
                continue
            if record.get("released") is True:
                out.discard(record["chunk"])
            else:
                out.add(record["chunk"])
    return out


def chunk_status(k: int, env: Env, launched: set[int]) -> dict:
    n = chunk_names(k)
    if (env.data_root / "runs" / n["run"]).exists():
        return {"eligible": False, "why": "flown (runs/<run id> exists)"}
    if k in launched:
        return {"eligible": False, "why": "launched before (queue state file)"}
    receipt_path = env.data_root / "coordination" / n["package"] / "root-admission-v1.json"
    if not receipt_path.is_file():
        return {"eligible": False, "why": "not minted"}
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except ValueError:
        return {"eligible": False, "why": "receipt unreadable"}
    if receipt.get("status") != "decided" or n["run"] not in (receipt.get("eligible_run_ids") or []):
        return {"eligible": False, "why": "receipt not decided for this run id"}
    commit_path = env.home / n["commit_file"]
    if not commit_path.is_file():
        return {"eligible": False, "why": "not flipped (no flight commit file)"}
    commit = commit_path.read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        return {"eligible": False, "why": "flight commit file does not hold a full sha"}
    for cell in [n["cell"]] + ([n["smoke_cell"]] if n["smoke_cell"] else []):
        document = env.fragment_at(commit, f"configs/experiment/{cell}.json")
        state = (((document or {}).get("cells") or [{}])[0].get("readiness") or {}).get("state")
        if state != "ready":
            return {"eligible": False, "why": f"{cell} is {state!r} at {commit[:8]}, not ready"}
    return {"eligible": True, "why": "unflown, minted, flipped", "commit": commit}


def serving_ok(env: Env) -> tuple[bool, str]:
    status = env.serving_status()
    if not isinstance(status, dict):
        return False, "serving status unreadable"
    sample = status.get("last_monitor_sample") or {}
    session = (status.get("session") or {}).get("session_id")
    if session != env.session:
        return False, f"resident session is {session!r}, not {env.session}"
    if sample.get("server_ok") is not True:
        return False, "server_ok is not true"
    if (sample.get("slots") or {}).get("busy") != 0:
        return False, f"slots busy {(sample.get('slots') or {}).get('busy')!r}"
    sampled = sample.get("sampled_at")
    if not isinstance(sampled, (int, float)) or env.now() - float(sampled) > env.monitor_max_age:
        return False, "the last monitor sample is stale"
    return True, "np4 resident, healthy and idle"


def decide(env: Env) -> dict:
    checks: dict = {}
    stop = env.home / "batch-STOP"
    if stop.exists():
        first = stop.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
        return {"decision": "HALT", "chunk": None, "reason": f"batch-STOP present: {first[0] if first else ''}", "checks": checks}
    if (env.home / "mainline-ready").exists():
        return {"decision": "WAIT", "chunk": None, "reason": f"main-line chain ready ({env.home / 'mainline-ready'})", "checks": checks}
    alive = env.processes()
    checks["processes"] = len(alive)
    if alive:
        return {"decision": "WAIT", "chunk": None, "reason": f"flight/driver process alive: {alive[0][:120]}", "checks": checks}
    if (env.data_root / "locks" / "flight.lock").exists():
        return {"decision": "WAIT", "chunk": None, "reason": "locks/flight.lock present", "checks": checks}
    if (env.home / "batch-flight-repo.txt").exists():
        return {"decision": "WAIT", "chunk": None, "reason": "stale flight-repo override /home/chao/batch-flight-repo.txt present", "checks": checks}
    done = env.home / "batch-done"
    if done.exists():
        age = env.now() - done.stat().st_mtime
        checks["batch_done_age_s"] = round(age)
        if age < env.grace_seconds:
            return {"decision": "WAIT", "chunk": None, "reason": f"batch-done is {round(age)} s old (grace {int(env.grace_seconds)} s)", "checks": checks}
    ok, why = serving_ok(env)
    checks["serving"] = why
    if not ok:
        return {"decision": "WAIT", "chunk": None, "reason": f"serving not ready: {why}", "checks": checks}
    launched = launched_chunks(env.state_file)
    summary = {}
    for k in registered_chunks(env.main):
        status = chunk_status(k, env, launched)
        summary[f"c{k:02d}"] = status["why"]
        if status["eligible"]:
            checks["chunks"] = summary
            return {"decision": "LAUNCH", "chunk": k, "commit": status["commit"], "reason": status["why"], "checks": checks}
    checks["chunks"] = summary
    return {"decision": "WAIT", "chunk": None, "reason": "no eligible chunk", "checks": checks}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--home", default="/home/chao")
    parser.add_argument("--data-root", default=(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
    parser.add_argument("--main", default="/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
    parser.add_argument("--session", default=SESSION)
    parser.add_argument("--grace-seconds", type=float, default=300.0)
    parser.add_argument("--monitor-max-age", type=float, default=300.0)
    parser.add_argument("--state-file", default="/home/chao/filler-queue-state.jsonl")
    parser.add_argument("--status-json", help="read the serving status from this file instead of serving_session.sh (dry runs)")
    args = parser.parse_args(argv)
    main_path = Path(args.main)
    if args.status_json:
        status_fn = lambda: json.loads(Path(args.status_json).read_text(encoding="utf-8"))  # noqa: E731
    else:
        status_fn = lambda: _serving_status(main_path, args.session)  # noqa: E731
    env = Env(home=Path(args.home), data_root=Path(args.data_root), main=main_path, session=args.session,
              grace_seconds=args.grace_seconds, monitor_max_age=args.monitor_max_age,
              state_file=Path(args.state_file), serving_status=status_fn,
              fragment_at=lambda commit, relpath: _fragment_at(main_path, commit, relpath))
    print(json.dumps(decide(env), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
