#!/usr/bin/env python3
"""Pure selection logic for the idle watchdog's ready-chain list (owner decision 182,
docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md row 182; carrier gate added by the
owner's 2026-09-28 ~23:45Z SLURP-only ruling, row 187). Model-free and side-effect free: given the
parsed ``ready_chains.json`` config plus the handful of facts the shell wrapper
(``idle_watchdog.sh``) has already read (file existence, the current batch-flight-commit, whether
batch-done is present, whether batch-STOP is present), it picks AT MOST one entry to launch next and
explains every entry it skipped.

Selection rule, evaluated once per entry IN LIST ORDER (the first eligible entry wins):

1. ``stop_present`` true -> no entry is ever selected (a STOP halts the whole list; row 182: "never
   launches onto a STOP").
2. ``enabled`` false -> skipped.
3. no ``carrier`` declared -> skipped (every entry must declare one; owner directive 2026-09-28).
4. ``carrier`` not in ``allowed_carriers`` -> skipped.
5. ``hold_file`` set and present on disk -> skipped.
6. ``flight_commit_file`` set:
     - missing on disk -> skipped ("not yet flipped");
     - present but empty -> skipped;
     - present, non-empty, AND ``batch_done_present`` is true AND its content equals the current
       ``batch_flight_commit`` -> skipped ("already flown at this commit").
   ``flight_commit_file`` unset (``null``) -> no flight-commit gate at all (the ``filler`` entry
   manages its own chunk commits internally, see ``scripts/flights/filler/filler_queue_decide.py``).
7. otherwise the entry is selected and the search stops.

CLI: reads the JSON config file plus flags mirroring the facts above and prints one JSON decision
line, for use from ``idle_watchdog.sh``. Unit tests import ``select_entry`` directly
(``tests/unit/test_idle_watchdog.py``) so the rule needs neither a WSL host nor real markers.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable, Optional


def select_entry(
    config: dict,
    *,
    exists: Callable[[str], bool],
    read_first_line: Callable[[str], str],
    batch_flight_commit: Optional[str],
    batch_done_present: bool,
    stop_present: bool,
) -> dict:
    """Returns ``{"decision": "launch" | "none", "entry": <name or None>, "commit": <str or None>,
    "geometry": ..., "chain_script": ..., "ext4_copy_target": ..., "log": ["<line>", ...]}``."""
    log: list[str] = []
    if stop_present:
        log.append("batch-STOP present; no chain is ever selected onto a STOP")
        return {"decision": "none", "entry": None, "commit": None, "geometry": None,
                "chain_script": None, "ext4_copy_target": None, "log": log}

    allowed = set(config.get("allowed_carriers") or [])
    for entry in config.get("chains", []):
        name = entry.get("name", "<unnamed>")

        if not entry.get("enabled", True):
            note = entry.get("note")
            log.append(f"{name}: disabled" + (f" ({note})" if note else "") + ", skipped")
            continue

        carrier = entry.get("carrier")
        if not carrier:
            log.append(f"{name}: no carrier declared, skipped")
            continue
        if allowed and carrier not in allowed:
            log.append(f"{name}: carrier {carrier!r} not in allowed_carriers {sorted(allowed)}, skipped")
            continue

        hold_file = entry.get("hold_file")
        if hold_file and exists(hold_file):
            log.append(f"{name}: hold file {hold_file} present, skipped")
            continue

        commit_file = entry.get("flight_commit_file")
        commit = None
        if commit_file:
            if not exists(commit_file):
                log.append(f"{name}: flight commit file {commit_file} missing (not yet flipped), skipped")
                continue
            commit = (read_first_line(commit_file) or "").strip()
            if not commit:
                log.append(f"{name}: flight commit file {commit_file} is empty, skipped")
                continue
            if batch_done_present and batch_flight_commit == commit:
                log.append(f"{name}: batch-done already present for commit {commit[:8]}, skipped")
                continue

        log.append(f"{name}: selected" + (f" at commit {commit[:8]}" if commit else " (no flight-commit gate)"))
        return {
            "decision": "launch",
            "entry": name,
            "commit": commit,
            "geometry": entry.get("geometry"),
            "chain_script": entry.get("chain_script"),
            "ext4_copy_target": entry.get("ext4_copy_target"),
            "log": log,
        }

    log.append("no eligible entry in the ready-chain list")
    return {"decision": "none", "entry": None, "commit": None, "geometry": None,
            "chain_script": None, "ext4_copy_target": None, "log": log}


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_first_line(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.readline().strip()
    except OSError:
        return ""


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Select the next ready-chain entry to launch (owner decision 182).")
    parser.add_argument("--config", required=True, help="path to ready_chains.json")
    parser.add_argument("--batch-flight-commit", default=None, help="content of /home/chao/batch-flight-commit.txt, if any")
    parser.add_argument("--batch-done-present", action="store_true", help="a non-empty /home/chao/batch-done exists")
    parser.add_argument("--stop-present", action="store_true", help="/home/chao/batch-STOP exists")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config))
    result = select_entry(
        config,
        exists=lambda p: Path(p).exists(),
        read_first_line=_read_first_line,
        batch_flight_commit=args.batch_flight_commit,
        batch_done_present=args.batch_done_present,
        stop_present=args.stop_present,
    )
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
