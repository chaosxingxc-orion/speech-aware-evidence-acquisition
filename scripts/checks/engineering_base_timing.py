#!/usr/bin/env python3
"""Model-free timing receipt for the engineering base (owner directive 2026-10-12, decision 274).

Measures, per repository checkout and per data root, the costs decision 267 names as the efficiency
floor -- and nothing that contacts a model, a GPU, an encoder, a dataset row or the network:

* ``cli_import``       a fresh ``python -B -c "import <module>"`` with ``PYTHONPATH=<repo>/src``
                       (default module ``speech_aware_evidence_acquisition.core.flight.cli``)
* ``git_status``       ``git -C <repo> status --porcelain`` wall time
* ``snapshot_load``    read + ``json.loads`` + sha256 of one knowledge snapshot under each root
* ``small_files``      stat + full read of the first N regular files under ``<root>/<subdir>``

Each measurement repeats ``--repeat`` times (default 1: a 9p checkout costs tens of seconds per
import) and records every sample; the receipt compares the minimum to the manifest's
``timing_budget``. Campaign prelude, check and seal times are flight facts, read from the driver's
status log, never measured here.

Usage (WSL):
  python -B scripts/checks/engineering_base_timing.py --repo /home/chao/saea-worktrees/fable-batch-flight \\
      --repo /mnt/d/.../speech-aware-evidence-acquisition --root /home/chao/saea-data/speechrl-data \\
      --root $SAEA_DATA_ROOT --out docs/checks/.../timing-receipt.json
Exit 0 when every measured minimum is within budget, 1 when one is over (the receipt is written
either way), 2 on a usage error.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

DEFAULT_MODULE = "speech_aware_evidence_acquisition.core.flight.cli"
DEFAULT_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json"
DEFAULT_SMALL_SUBDIR = "knowledge"
MANIFEST_RELPATH = "configs/base/engineering-base-v1.json"
BUDGET_KEYS = {
    "cli_import": "cli_import_seconds",
    "git_status": "git_status_seconds",
    "snapshot_load": "knowledge_snapshot_load_seconds",
    "small_files": "small_file_stat_read_2000_seconds",
}


def _timed(action: Callable[[], object]) -> tuple[float, object]:
    start = time.perf_counter()
    result = action()
    return time.perf_counter() - start, result


def _fstype(path: Path) -> str | None:
    try:
        text = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    except OSError:
        return None
    resolved = os.path.realpath(path)
    best: tuple[int, str] | None = None
    for line in text.splitlines():
        left, sep, right = line.partition(" - ")
        fields = left.split()
        if not sep or len(fields) < 5 or not right.split():
            continue
        point = fields[4]
        if resolved == point or resolved.startswith(point.rstrip("/") + "/") or point == "/":
            if best is None or len(point) > best[0]:
                best = (len(point), right.split()[0])
    return None if best is None else best[1]


def measure_import(repo: Path, module: str, python: str) -> dict:
    env = dict(os.environ, PYTHONPATH=str(repo / "src"), PYTHONDONTWRITEBYTECODE="1")
    seconds, completed = _timed(lambda: subprocess.run(
        [python, "-B", "-c", f"import {module}"], cwd=str(repo), env=env,
        capture_output=True, text=True, check=False))
    return {"seconds": round(seconds, 3), "ok": completed.returncode == 0,
            **({} if completed.returncode == 0 else {"stderr_tail": completed.stderr[-400:]})}


def measure_git_status(repo: Path) -> dict:
    seconds, completed = _timed(lambda: subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True, check=False))
    return {"seconds": round(seconds, 3), "ok": completed.returncode == 0,
            "dirty_entries": len(completed.stdout.splitlines()) if completed.returncode == 0 else None}


def measure_snapshot(root: Path, relpath: str) -> dict:
    path = root / relpath

    def load() -> tuple[int, str]:
        raw = path.read_bytes()
        json.loads(raw)
        return len(raw), hashlib.sha256(raw).hexdigest()

    try:
        seconds, (size, sha) = _timed(load)
    except (OSError, ValueError) as error:
        return {"seconds": None, "ok": False, "error": str(error)[:300]}
    return {"seconds": round(seconds, 3), "ok": True, "bytes": size, "sha256": sha}


def measure_small_files(root: Path, subdir: str, count: int) -> dict:
    base = root / subdir

    def walk() -> int:
        seen = 0
        for directory, _dirs, files in os.walk(base):
            for name in sorted(files):
                path = Path(directory) / name
                try:
                    path.stat()
                    path.read_bytes()
                except OSError:
                    continue
                seen += 1
                if seen >= count:
                    return seen
        return seen

    if not base.is_dir():
        return {"seconds": None, "ok": False, "error": f"{base} is not a directory"}
    seconds, seen = _timed(walk)
    return {"seconds": round(seconds, 3), "ok": seen > 0, "files": seen,
            "scaled_to_2000_seconds": round(seconds * 2000 / seen, 3) if seen else None}


def _best(samples: list[dict], key: str = "seconds") -> float | None:
    values = [s[key] for s in samples if s.get("ok") and s.get(key) is not None]
    return min(values) if values else None


def run(args: argparse.Namespace) -> tuple[dict, bool]:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        budget = json.loads((repo_root / MANIFEST_RELPATH).read_text(encoding="utf-8"))["timing_budget"]
    except (OSError, ValueError, KeyError):
        budget = {}
    rows: list[dict] = []
    for repo in args.repo:
        repo = Path(repo)
        imports = [measure_import(repo, args.module, args.python) for _ in range(args.repeat)]
        statuses = [measure_git_status(repo) for _ in range(args.repeat)]
        rows.append({"kind": "repo", "path": str(repo), "fstype": _fstype(repo),
                     "cli_import": {"best": _best(imports), "samples": imports},
                     "git_status": {"best": _best(statuses), "samples": statuses}})
    for root in args.root:
        root = Path(root)
        snapshots = [measure_snapshot(root, args.snapshot_relpath) for _ in range(args.repeat)]
        smalls = [measure_small_files(root, args.small_subdir, args.small_count) for _ in range(args.repeat)]
        rows.append({"kind": "data-root", "path": str(root), "resolved": os.path.realpath(root), "fstype": _fstype(root),
                     "snapshot_load": {"relpath": args.snapshot_relpath, "best": _best(snapshots), "samples": snapshots},
                     "small_files": {"subdir": args.small_subdir, "best": _best(smalls, "scaled_to_2000_seconds"), "samples": smalls}})
    verdicts: list[dict] = []
    within = True
    for row in rows:
        for measure, key in BUDGET_KEYS.items():
            if measure not in row or key not in budget:
                continue
            best = row[measure]["best"]
            ok = best is not None and best <= float(budget[key])
            within &= ok
            verdicts.append({"path": row["path"], "measure": measure, "best_seconds": best,
                             "budget_seconds": budget[key], "within_budget": ok})
    receipt = {
        "schema": "saea-engineering-base-timing-receipt-v1",
        "written_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "host": platform.node(), "python": args.python, "module": args.module, "repeat": args.repeat,
        "model_free": True,
        "rows": rows, "verdicts": verdicts, "all_within_budget": within,
        "not_measured_here": ["flight_cli_check_seconds", "campaign_prelude_seconds", "seal_seconds"],
    }
    return receipt, within


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="model-free engineering-base timing receipt")
    parser.add_argument("--repo", action="append", default=[], help="a repository checkout (repeatable)")
    parser.add_argument("--root", action="append", default=[], help="a data root (repeatable)")
    parser.add_argument("--module", default=DEFAULT_MODULE)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--snapshot-relpath", default=DEFAULT_SNAPSHOT)
    parser.add_argument("--small-subdir", default=DEFAULT_SMALL_SUBDIR)
    parser.add_argument("--small-count", type=int, default=2000)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--out", type=Path, help="receipt path (default: print only)")
    args = parser.parse_args(argv)
    if not args.repo and not args.root:
        parser.error("name at least one --repo or --root")
    if args.repeat < 1 or args.small_count < 1:
        parser.error("--repeat and --small-count must be positive")
    receipt, within = run(args)
    text = json.dumps(receipt, indent=1) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    for verdict in receipt["verdicts"]:
        print(f"{'OK  ' if verdict['within_budget'] else 'OVER'} {verdict['measure']:<14} {verdict['best_seconds']!s:>9} s "
              f"(budget {verdict['budget_seconds']} s)  {verdict['path']}")
    print(f"engineering base timing: {'WITHIN BUDGET' if within else 'OVER BUDGET'}"
          f"{f' (receipt {args.out})' if args.out else ''}")
    return 0 if within else 1


if __name__ == "__main__":
    sys.exit(main())
