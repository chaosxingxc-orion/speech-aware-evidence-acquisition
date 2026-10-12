#!/usr/bin/env python3
"""Empty-slot accounting of a sealed native flight, and the fit gate on the same clock.

Owner decision 159 (2026-09-27): the dispatcher slot-fill engineering-base item.
Two uses, one script:

1. REPRODUCE the empty-slot accounting of
   ``docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md`` on the
   sealed ROLL-2 trace (``--compare-note``, the default run id) before the
   runtime is changed. The note parsed the session log's LAST lifetime; later
   lifetimes have been appended since, so this script selects the lifetime that
   launched the most tasks inside the attempt's own contact window, anchored at
   the attach receipt's ``serving_session_started_at``.
2. The THROUGHPUT READ of any later native flight on a resident session
   (``--run-id/--attempt-id/--fit-run-id/--fit-attempt-id``): slot capacity,
   empty slot-seconds, all-slots-empty seconds, mean busy slots, contacts per
   hour of the contact window and per-role client turnaround, joined one to one
   from the server's own per-slot task log to the sealed trace.

It also joins every contact to its own sealed native-contact fit receipt
(``prepared/<fit run id>/<fit attempt>/<identity>.request-fit.json``) to place
the fit gate -- which ``core.preparation_fit.build_native_contact_fit_gate`` runs
for every contact inside one process-wide ``fit_lock`` while the row holds its
slot -- on the server's clock (file times: medians only, see the receipt).

Zero model, server, encoder, scorer and endpoint contacts. It reads only the
sealed trace, the server log, the attach receipt, the fit receipts' inputs and
file times, and (with ``--compare-note``) the note's own receipt. It never prints
or persists utterance text, transcripts, gold, knowledge bodies, model output or
sample identifiers -- counts, times and shares only.

Usage (WSL, stdlib only):

    PYTHONDONTWRITEBYTECODE=1 python3 scripts/analysis/slotfill_gap_decomposition.py \\
        --compare-note --out /tmp/gap.json
"""
from __future__ import annotations
import os

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = Path((os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"))
RUN_ID = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1"
ATTEMPT = "attempt-slurp-native-stage3-roll-2-fold-a-v1-generation"
FIT_RUN_ID = "SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-FIT-V1"
FIT_ATTEMPT = "attempt-slurp-native-stage3-roll-2-fold-a-v1-fit"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
NOTE_RECEIPT = REPO / "docs/receipts/slurp-throughput-baseline-and-levers-v1.json"
DRIVER = REPO / "scripts/analysis/slurp_throughput_baseline_and_levers.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("_tput_driver", DRIVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_tput_driver"] = module
    spec.loader.exec_module(module)
    return module


def parse_lifetime(tput, path: Path, lifetime_index: int, segment_start_utc: float):
    """The driver's parser restricted to ONE lifetime [start_k, start_k+1)."""
    starts = []
    with path.open("rb") as fh:
        for index, raw in enumerate(fh):
            if b"log_info: verbosity" in raw:
                starts.append(index)
    first = starts[lifetime_index]
    stop = starts[lifetime_index + 1] if lifetime_index + 1 < len(starts) else None
    tasks: dict[tuple[int, int], dict] = {}
    with path.open("rb") as fh:
        for index, raw in enumerate(fh):
            if index < first:
                continue
            if stop is not None and index >= stop:
                break
            line = raw.decode("utf-8", "replace").rstrip("\n")
            m = tput.TS_RE.match(line)
            if not m:
                continue
            t = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 1e3 + int(m.group(4)) / 1e6
            sm = tput.SLOT_RE.search(m.group(6))
            if not sm:
                continue
            slot, task, rest = int(sm.group(1)), int(sm.group(2)), sm.group(3)
            if task < 0:
                continue
            rec = tasks.setdefault((slot, task), {"slot": slot, "task": task})
            if "processing task" in rest:
                rec["t_launch"] = t
            elif (mm := tput.MTMD_RE.search(rest)):
                rec["mtmd_tokens"] = rec.get("mtmd_tokens", 0) + int(mm.group(1))
            elif (pm := tput.PROMPT_RE.search(rest)):
                rec["prompt_ms"], rec["prompt_n"] = float(pm.group(1)), int(pm.group(2))
            elif (em := tput.EVAL_RE.search(rest)) and "prompt" not in rest:
                rec["eval_ms"], rec["eval_n"] = float(em.group(1)), int(em.group(2))
            elif (rm := tput.RELEASE_RE.search(rest)):
                rec["t_release"], rec["n_ctx_release"] = t, int(rm.group(1))
            elif (nm := tput.NPAST_RE.search(rest)):
                rec["full_hit_n_past"] = int(nm.group(1))
    out = []
    for rec in tasks.values():
        if "t_launch" not in rec or "t_release" not in rec:
            continue
        rec["t_launch_utc"] = segment_start_utc + rec["t_launch"]
        rec["t_release_utc"] = segment_start_utc + rec["t_release"]
        for key, default in (("prompt_n", 0), ("prompt_ms", 0.0), ("eval_n", 0), ("eval_ms", 0.0), ("mtmd_tokens", 0)):
            rec.setdefault(key, default)
        rec["full_prompt"] = rec["n_ctx_release"] - rec["eval_n"]
        rec["cached"] = rec["full_prompt"] - rec["prompt_n"]
        out.append(rec)
    out.sort(key=lambda r: (r["t_launch"], r["slot"]))
    return out, len(starts)


def contact_ids_by_flight(trace: Path) -> dict[str, str]:
    """flight-<seq> -> sha256(agent_contact_id), from the MODEL_REQUEST records."""
    out = {}
    with trace.open("rb") as fh:
        for raw in fh:
            if b'"MODEL_REQUEST"' not in raw[:200]:
                continue
            rec = json.loads(raw)
            fid = rec["record_id"].split("/")[0]
            if not fid.startswith("flight-"):
                continue
            env = json.loads(rec["payload"]["payload"]["history"][-1]["content"])
            out[fid] = hashlib.sha256(env["contact_id"].encode("utf-8")).hexdigest()
    return out


def fit_times(fit_dir: Path) -> dict[str, dict]:
    """sha256(agent_contact_id) -> fit file times (start marker, journal, end)."""
    out = {}
    for path in sorted(fit_dir.glob("*.request-fit.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        contact_id = doc["inputs"]["native_contact"]["agent_contact_id"]
        lock = path.with_name(path.name + ".producer.lock")
        journal = path.with_name(path.name + ".contacts.jsonl")
        out[hashlib.sha256(contact_id.encode("utf-8")).hexdigest()] = {
            "start": lock.stat().st_mtime if lock.exists() else None,
            "journal": journal.stat().st_mtime if journal.exists() else None,
            "end": path.stat().st_mtime,
            "endpoint_contacts": int(doc["output"]["contacts"]),
        }
    return out


def union_seconds(intervals, t0, t1):
    total = 0.0
    last = t0
    for a, b in sorted((max(a, t0), min(b, t1)) for a, b in intervals if b > t0 and a < t1):
        if b <= last:
            continue
        total += b - max(a, last)
        last = b
    return total


def _lifetime_covering(tput, path: Path, rel_from: float, rel_to: float) -> tuple[int, int]:
    """One pass: the 0-based lifetime with the most task launches whose
    minute stamp (seconds since that lifetime's start) falls in [rel_from,
    rel_to], and the number of lifetimes in the file."""

    counts: collections.Counter = collections.Counter()
    k = -1
    with path.open("rb") as fh:
        for raw in fh:
            if b"log_info: verbosity" in raw:
                k += 1
                continue
            if b"processing task" not in raw:
                continue
            m = tput.TS_RE.match(raw.decode("utf-8", "replace"))
            if not m:
                continue
            t = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 1e3 + int(m.group(4)) / 1e6
            if rel_from <= t <= rel_to:
                counts[k] += 1
    if not counts:
        raise SystemExit("no server lifetime launches a task inside the contact window")
    return counts.most_common(1)[0][0], k + 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-id", default=RUN_ID)
    ap.add_argument("--attempt-id", default=ATTEMPT)
    ap.add_argument("--fit-run-id", default=FIT_RUN_ID)
    ap.add_argument("--fit-attempt-id", default=FIT_ATTEMPT)
    ap.add_argument("--lifetime-index", type=int, default=None,
                    help="0-based server lifetime; default: the one launching the most tasks in the contact window")
    ap.add_argument("--compare-note", action="store_true",
                    help="compare against the 2026-09-27 throughput note's receipt (ROLL-2 only)")
    ap.add_argument("--dump", default=None, help="optional per-contact numeric timeline (JSON)")
    args = ap.parse_args(argv)
    tput = _load_driver()
    run_dir = DATA / "runs" / args.run_id / args.attempt_id
    attach = json.loads(next(run_dir.glob("*.session-attach-receipt.json")).read_text(encoding="utf-8"))
    t0, t1 = attach["contact_window"]["from"], attach["contact_window"]["to"]
    seg_start = tput.parse_iso(attach["serving_session_started_at"])
    session = attach["session_id"]
    # the join window: the contact window with the note's own five-second margin
    arm_start, arm_exit = t0, t1
    note = None
    if args.compare_note:
        note = json.loads(NOTE_RECEIPT.read_text(encoding="utf-8"))
        arm_start, arm_exit = (tput.parse_iso(x) for x in note["arm_window_driver_utc"])
        if abs(tput.parse_iso(note["session_started_at"]) - seg_start) > 1.0:
            raise SystemExit("the note's session start is not this attempt's")
    server_log = DATA / "serving" / session / "server.log"

    # --- 1. the server lifetime that flew this attempt
    if args.lifetime_index is None:
        chosen, n_starts = _lifetime_covering(tput, server_log, t0 - seg_start - 5, t1 - seg_start + 5)
    else:
        chosen, n_starts = args.lifetime_index, None
    tasks, n_starts = parse_lifetime(tput, server_log, chosen, seg_start)

    # --- 2. the note's accounting, reproduced
    contacts, order_ok = tput.extract_trace(run_dir / f"{args.run_id}.trace.jsonl")
    joined, window_tasks, join_report = tput.join(contacts, tasks, arm_start, arm_exit)
    acc, conc_pf, conc_dec, _scaling = tput.sweep([c["srv"] for c in joined], t0, t1)
    wall = t1 - t0
    by_slot = collections.defaultdict(list)
    for c in joined:
        by_slot[c["slot"]].append(c)
        c["turnaround_s"] = None
        c["prev_release"] = None
    for cs in by_slot.values():
        cs.sort(key=lambda c: c["seq"])
        for a, b in zip(cs, cs[1:]):
            b["turnaround_s"] = b["srv"]["t_launch_utc"] - a["srv"]["t_release_utc"]
            b["prev_release"] = a["srv"]["t_release_utc"]

    def role_class(c):
        if c["role"] == "solver":
            return "solver#1" if (c["has_prev"] and c["first_diff"] != "none") or not c["has_prev"] else "solver#2-5(full hit)"
        return c["role"]

    roles = ("perception", "solver#1", "solver#2-5(full hit)", "reviewer", "planner")
    reproduced = {
        "server_lifetime_index": chosen, "server_lifetimes_in_file": n_starts,
        "server_tasks_in_arm_window": len(window_tasks), "trace_contacts": len(contacts),
        "joined_contacts": len(joined), "join_report": join_report,
        "contact_window_utc": [tput.iso(t0), tput.iso(t1)], "wall_s": round(wall, 1),
        "states_s": acc,
        "slot_capacity": {
            "slot_seconds_total": round(4 * wall, 1),
            "server_compute_slot_s": round(sum(c["srv"]["prompt_ms"] + c["srv"]["eval_ms"] for c in joined) / 1000, 1),
            "empty_slot_s": round(4 * wall - acc["slot_seconds_busy"], 1),
            "client_turnaround_slot_s": round(sum(c["turnaround_s"] or 0 for c in joined), 1),
        },
        "mean_busy_slots": round(acc["slot_seconds_busy"] / wall, 3),
        "turnaround_by_role": {
            cls: {
                "contacts": len(cs),
                "turnaround_slot_s": round(sum(c["turnaround_s"] or 0 for c in cs), 1),
                "turnaround_mean_s": round(statistics.fmean([c["turnaround_s"] for c in cs if c["turnaround_s"] is not None]), 2),
            }
            for cls in roles
            if (cs := [c for c in joined if role_class(c) == cls])
        },
        "contacts_per_gpu_hour_contact_window": round(len(joined) / wall * 3600, 0),
    }
    if note is not None:
        ref = {
            "empty_slot_s": note["time_split"]["slot_capacity"]["empty_slot_s"],
            "client_turnaround_slot_s": note["time_split"]["slot_capacity"]["client_turnaround_slot_s"],
            "all_idle_s": note["time_split"]["states_s"]["all_idle"],
            "joined_contacts": note["joined_contacts"],
            "turnaround_slot_s_by_role": {k: v["turnaround_slot_seconds"] for k, v in note["per_role"].items()},
        }
        reproduced["matches_note"] = {
            "empty_slot_s": abs(reproduced["slot_capacity"]["empty_slot_s"] - ref["empty_slot_s"]) <= 0.5,
            "client_turnaround_slot_s": abs(reproduced["slot_capacity"]["client_turnaround_slot_s"] - ref["client_turnaround_slot_s"]) <= 0.5,
            "all_idle_s": abs(acc["all_idle"] - ref["all_idle_s"]) <= 0.5,
            "joined_contacts": len(joined) == ref["joined_contacts"],
            "turnaround_by_role": all(
                abs(reproduced["turnaround_by_role"][k]["turnaround_slot_s"] - v) <= 0.5
                for k, v in ref["turnaround_slot_s_by_role"].items()
            ),
        }
        reproduced["note_reference"] = ref

    # --- 3. the fit gate on the same clock
    ids = contact_ids_by_flight(run_dir / f"{args.run_id}.trace.jsonl")
    fits = fit_times(DATA / "prepared" / args.fit_run_id / args.fit_attempt_id)
    for c in joined:
        c["fit"] = fits.get(ids.get(c["fid"]))
    have = [c for c in joined if c["fit"] and c["fit"]["start"] is not None]
    # File times come from the drvfs clock, launches and releases from the
    # server's own minute stamps anchored at the session start. Causality
    # bounds the offset from BOTH sides: a contact's fit starts after the
    # previous contact on its slot released (the row holds its slot), and the
    # server launches the task after its fit ended. The offset is the
    # midpoint of the feasible interval [lo, hi] (0.1 % quantiles, so a
    # single mistimed file cannot move it).
    lag = sorted(c["srv"]["t_launch_utc"] - c["fit"]["end"] for c in have)
    lead = sorted(c["prev_release"] - c["fit"]["start"] for c in have if c["prev_release"] is not None)
    hi = lag[max(0, int(0.001 * len(lag)))]
    lo = lead[min(len(lead) - 1, int(0.999 * len(lead)))]
    offset = (lo + hi) / 2
    for c in have:
        c["fit_start"] = c["fit"]["start"] + offset
        c["fit_end"] = c["fit"]["end"] + offset
    fit_iv = [(c["fit_start"], c["fit_end"]) for c in have]
    fit_busy_sum = sum(b - a for a, b in fit_iv)
    fit_union = union_seconds(fit_iv, t0, t1)
    # overlap check: a process-wide lock admits one fit at a time
    ordered = sorted(fit_iv)
    overlaps = sum(1 for (a1, b1), (a2, b2) in zip(ordered, ordered[1:]) if a2 < b1 - 1e-3)
    # consecutive fit hand-over: end of fit i -> start of fit i+1 (lock hand-over + render + inputs)
    handover = [a2 - b1 for (_a1, b1), (a2, _b2) in zip(ordered, ordered[1:]) if 0 <= a2 - b1 < 5]
    # per-contact split of the turnaround: [prev release, fit start] | fit | [fit end, launch]
    split = collections.defaultdict(lambda: collections.defaultdict(float))
    for c in have:
        if c["prev_release"] is None:
            continue
        cls = role_class(c)
        pre = c["fit_start"] - c["prev_release"]
        fit = c["fit_end"] - c["fit_start"]
        post = c["srv"]["t_launch_utc"] - c["fit_end"]
        split[cls]["pre_fit_s"] += pre
        split[cls]["fit_s"] += fit
        split[cls]["post_fit_s"] += post
        split[cls]["n"] += 1
    # the lock's queue: how long the lock was busy while at least one slot
    # was empty waiting for its own contact
    fit_share = fit_union / wall
    decomposition = {
        "fit_receipts": len(fits), "contacts_with_fit_times": len(have),
        "clock_offset_s_applied_to_file_times": round(offset, 3),
        "clock_offset_feasible_interval_s": [round(lo, 3), round(hi, 3)],
        "launch_minus_fit_end_s": tput.stats([x - offset for x in lag], 3),
        "fit_seconds_sum": round(fit_busy_sum, 1),
        "fit_seconds_union_in_window": round(fit_union, 1),
        "fit_lock_busy_share_of_window": round(fit_share, 4),
        "fit_intervals_overlapping_their_predecessor": overlaps,
        "fit_duration_s": tput.stats([b - a for a, b in fit_iv], 3),
        "fit_to_fit_gap_s_under_5s": tput.stats(handover, 3),
        "endpoint_contacts_per_fit": tput.stats([c["fit"]["endpoint_contacts"] for c in have], 2),
        "turnaround_split_by_role_s": {
            cls: {k: round(v, 1) for k, v in d.items()} for cls, d in sorted(split.items())
        },
    }
    receipt = {
        "schema": "saea-slotfill-gap-decomposition-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": args.run_id, "attempt_id": args.attempt_id, "fit_run_id": args.fit_run_id,
        "fit_attempt_id": args.fit_attempt_id, "session_id": session, "contacts_made": 0,
        "reproduced_note_accounting": reproduced,
        "fit_gate_on_the_server_clock": decomposition,
        "trace_order_per_slot_monotone": order_ok,
    }
    Path(args.out).write_text(json.dumps(receipt, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.dump:
        # numbers only: per contact its slot, role class, row ordinal on the
        # slot, server launch/release, server prefill/decode ms and fit times
        rows = []
        for c in sorted(joined, key=lambda c: c["seq"]):
            rows.append({
                "seq": c["seq"], "slot": c["slot"], "role": role_class(c),
                "launch": c["srv"]["t_launch_utc"], "release": c["srv"]["t_release_utc"],
                "prompt_ms": c["srv"]["prompt_ms"], "eval_ms": c["srv"]["eval_ms"],
                "prompt_n": c["srv"]["prompt_n"], "eval_n": c["srv"]["eval_n"],
                "fit_start": c.get("fit_start"), "fit_end": c.get("fit_end"),
                "turnaround": c["turnaround_s"],
            })
        Path(args.dump).write_text(json.dumps({"t0": t0, "t1": t1, "contacts": rows}) + "\n", encoding="utf-8")
    print(json.dumps({"reproduced": reproduced.get("matches_note"), "slot_capacity": reproduced["slot_capacity"],
                      "all_idle": acc["all_idle"], "fit": {k: decomposition[k] for k in (
                          "fit_seconds_union_in_window", "fit_lock_busy_share_of_window",
                          "fit_intervals_overlapping_their_predecessor", "fit_duration_s",
                          "clock_offset_s_applied_to_file_times", "launch_minus_fit_end_s")},
                      "split": decomposition["turnaround_split_by_role_s"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
