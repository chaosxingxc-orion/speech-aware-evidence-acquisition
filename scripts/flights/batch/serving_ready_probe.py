"""One readiness verdict for a resident serving geometry (owner decision 163: health-verified restarts).

Called once per poll by ``serving_wait_ready.sh``; stdlib only, so it runs under the system ``python3`` without
the study venv. A geometry is READY only when every one of these holds:

1. ``session.json`` belongs to the expected session id and model fragment and was started at or after ``--since``
   (the swap start), so a document left over from an earlier start never counts;
2. no ``session-stop.json`` sits beside it -- a stop record stamped at or after ``--since`` (or after the session's
   own start) means THIS start stopped; an older one is a stale record the task entry has not archived yet and
   keeps the verdict at "waiting", because ``find_resident_session`` treats any stop record as "not resident" and a
   flight would refuse to attach;
3. ``GET /health`` answered ``ok``;
4. ``GET /props`` reports ``total_slots == -np`` and a per-slot ``n_ctx == -c / -np`` of the fragment;
5. a monitor sample stamped at or after both ``--since`` and the session start says ``server_ok``.

A refusal line in a task or server log written at or after ``--since`` (the host-memory start guard, a wrapper
exit, an entry's "still resident" refusal) is a STOPPED verdict at once rather than a wait until the timeout.

Exit status: 0 ready, 1 waiting, 3 stopped, 4 wrong geometry, 64 usage.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

READY, WAITING, STOPPED, WRONG = 0, 1, 3, 4
STATE_NAMES = {READY: "ready", WAITING: "waiting", STOPPED: "stopped", WRONG: "wrong-geometry"}

#: Lines that end a start attempt, as the task entries and ``serving_session.sh start`` print them.
REFUSAL_PATTERN = re.compile(
    r"^serving_session: |wrapper exited|still (recorded )?resident|refusing"
)


def iso_epoch(value: object) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def read_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def fragment_geometry(fragment_path: Path) -> tuple[int, int]:
    """(slots, per-slot n_ctx) from the fragment's own ``server_args``."""

    document = read_json(fragment_path)
    if not isinstance(document, dict):
        raise SystemExit(f"serving_ready_probe: unreadable model fragment {fragment_path}")
    argv = [str(value) for value in document.get("server_args", ())]
    if "-c" not in argv or "-np" not in argv:
        raise SystemExit(f"serving_ready_probe: fragment {fragment_path} declares no -c/-np")
    context = int(argv[argv.index("-c") + 1])
    slots = int(argv[argv.index("-np") + 1])
    return slots, context // slots


def log_refusals(patterns: list[str], since: float) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        for name in sorted(glob.glob(pattern)):
            try:
                if os.path.getmtime(name) < since:
                    continue
                lines = Path(name).read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            found.extend(
                f"{os.path.basename(name)}: {line.strip()[:300]}"
                for line in lines
                if REFUSAL_PATTERN.search(line)
            )
    return found


def verdict(
    *,
    session_dir: Path,
    session_id: str,
    fragment: str,
    geometry: tuple[int, int],
    since: float,
    health: str,
    props: object | None,
    monitor_lines: list[str],
    refusals: list[str],
) -> tuple[int, list[str], dict[str, object]]:
    reasons: list[str] = []
    facts: dict[str, object] = {"since": since, "expected_slots": geometry[0], "expected_slot_n_ctx": geometry[1]}
    document = read_json(session_dir / "session.json")
    started = None
    fresh = False
    if isinstance(document, dict):
        started = iso_epoch(document.get("started_at"))
        facts["session_started_at"] = document.get("started_at")
        identity = document.get("identity") if isinstance(document.get("identity"), dict) else {}
        fresh = started is not None and started >= since
        if document.get("session_id") != session_id:
            return WRONG, [f"session.json names session {document.get('session_id')!r}, expected {session_id!r}"], facts
        if fresh and identity.get("model_fragment") != fragment:
            return WRONG, [
                f"session.json serves fragment {identity.get('model_fragment')!r}, expected {fragment!r}"
            ], facts
    stop = read_json(session_dir / "session-stop.json")
    if (session_dir / "session-stop.json").exists():
        stopped = iso_epoch(stop.get("stopped_at")) if isinstance(stop, dict) else None
        facts["stopped_at"] = stop.get("stopped_at") if isinstance(stop, dict) else None
        if stopped is None:
            return STOPPED, ["session-stop.json is present and unreadable"], facts
        this_start_stopped = stopped >= since if since > 0 else (started is None or stopped >= started)
        if fresh and stopped >= (started or 0):
            this_start_stopped = True
        if this_start_stopped:
            return STOPPED, [f"the session stopped at {facts['stopped_at']} (after the start being waited on)"], facts
        reasons.append("a stale session-stop.json from an earlier session is not archived yet")
    if refusals and not fresh:
        return STOPPED, refusals[-3:], facts
    if document is None:
        reasons.append("no session.json yet")
    elif not fresh:
        reasons.append(f"session.json is from an earlier start ({facts.get('session_started_at')})")
    if '"ok"' not in health:
        reasons.append("GET /health is not ok")
    if isinstance(props, dict):
        generation = props.get("default_generation_settings")
        slot_n_ctx = generation.get("n_ctx") if isinstance(generation, dict) else None
        facts["props_total_slots"], facts["props_slot_n_ctx"] = props.get("total_slots"), slot_n_ctx
        if fresh and '"ok"' in health and (props.get("total_slots"), slot_n_ctx) != geometry:
            return WRONG, [
                f"/props reports {props.get('total_slots')} slots of n_ctx {slot_n_ctx}, the fragment "
                f"declares {geometry[0]} of {geometry[1]}"
            ], facts
    else:
        reasons.append("GET /props gave no JSON object")
    floor = max(since, started or 0.0)
    samples = []
    for line in monitor_lines:
        try:
            sample = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(sample, dict) and isinstance(sample.get("sampled_at"), (int, float)):
            samples.append(sample)
    fresh_ok = [s for s in samples if s["sampled_at"] >= floor and s.get("server_ok") is True]
    facts["monitor_last_sampled_at"] = samples[-1].get("sampled_at_iso") if samples else None
    if not fresh_ok:
        reasons.append("no monitor sample with server_ok since the session started")
    return (READY if not reasons else WAITING), reasons, facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--fragment-json", type=Path, required=True)
    parser.add_argument("--since", type=float, default=0.0)
    parser.add_argument("--health-file", type=Path)
    parser.add_argument("--props-file", type=Path)
    parser.add_argument("--monitor-tail-file", type=Path)
    parser.add_argument("--refusal-log-glob", action="append", default=[])
    args = parser.parse_args(argv)

    def text(path: Path | None) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="replace") if path else ""
        except OSError:
            return ""

    props_text = text(args.props_file)
    try:
        props = json.loads(props_text) if props_text.strip() else None
    except json.JSONDecodeError:
        props = None
    state, reasons, facts = verdict(
        session_dir=args.session_dir,
        session_id=args.session_id,
        fragment=args.fragment_json.stem,
        geometry=fragment_geometry(args.fragment_json),
        since=args.since,
        health=text(args.health_file),
        props=props,
        monitor_lines=text(args.monitor_tail_file).splitlines(),
        refusals=log_refusals(args.refusal_log_glob, args.since),
    )
    print(json.dumps({"state": STATE_NAMES[state], "reasons": reasons, "facts": facts}, sort_keys=True))
    return state


if __name__ == "__main__":
    sys.exit(main())
