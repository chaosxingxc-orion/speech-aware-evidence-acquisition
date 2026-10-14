#!/usr/bin/env python3
"""Generic recovery re-registration helpers for flight packages. Model-free.

A (run_id, attempt_id) pair is a one-time key (``core/attempts/store.py``), so a cell whose attempt stopped is re-flown WHOLE under new attempt ids
(``-rec1``): a new generation attempt id AND a new live-phase-fit run id and attempt id, with a plan that carries the original plan plus the failed
attempt's REALISED spend (the adapter budget is run-cumulative across the attempts of a run id; every attempt state counts, an OPENED one included).

This module lifts the mechanism of ``scripts/flights/direct/direct_fb_family.py`` / ``direct_fb_write_registration.py`` (which stay untouched) into
functions that take the recoveries mapping as an argument, so any family can use them. A recovery record is a plain dict (keys in
:data:`REQUIRED_KEYS`, validated by :func:`validate_recovery`). The failed attempt's spend is NEVER typed by hand: :func:`snapshot_predecessor` reads the
attempt record on the data root into a small committed snapshot receipt, :func:`predecessor_from_snapshot` turns it into the record's ``predecessors``
entry, and :func:`verify_predecessor_snapshot` re-reads the data root whenever it is present.

    python -B scripts/flights/lib/recovery.py snapshot --data-root DIR --run-id RUN --attempt-id ATT [--fit-run-id RUN --fit-attempt-id ATT] --out FILE

The CLI only READS the data root (attempt record, a directory listing of the FIT prepared directory) and writes the one output file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REC = "-rec1"
SNAPSHOT_SCHEMA = "saea-recovery-predecessor-snapshot-v1"

#: Keys every recovery record carries (the writer prints them; the persisted subset is :data:`PERSISTED_RECOVERY_KEYS`).
REQUIRED_KEYS = (
    "recovery_index", "recovered_at", "ledger_title", "agent", "predecessor_attempt_id", "predecessor_fit_run_id", "predecessor_fit_attempt_id",
    "fit_predecessor_phrase", "predecessor_state", "predecessors", "reason", "root_cause", "amendment", "fix", "unchanged", "rule", "fit_cap_rule",
)
#: Persisted into plan and protocol documents. Text only the writer prints (ledger title, agent, fix, unchanged ...) is NOT persisted.
PERSISTED_RECOVERY_KEYS = (
    "amendment", "fit_cap_rule", "predecessor_attempt_id", "predecessor_fit_attempt_id", "predecessor_fit_run_id", "predecessor_state",
    "predecessors", "reason", "recovered_at", "recovery_index", "root_cause", "rule",
)
LEDGER_COLUMN_NAMES = ["date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split", "split role",
                       "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes"]


class RecoveryError(ValueError):
    """A recovery record or snapshot is malformed or disagrees with the data root."""


# ---- the record -----------------------------------------------------------------------------------------------------------------------


def validate_recovery(rec: Mapping[str, Any]) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in rec]
    if missing:
        raise RecoveryError(f"recovery record misses keys: {missing}")
    if not rec["predecessors"]:
        raise RecoveryError("a recovery record names at least one predecessor attempt")
    for p in rec["predecessors"]:
        for k in ("attempt_id", "state", "contacts_spent", "speech_seconds_spent"):
            if k not in p:
                raise RecoveryError(f"predecessor entry misses {k!r}: {p}")
    if rec["predecessor_attempt_id"] not in [p["attempt_id"] for p in rec["predecessors"]]:
        raise RecoveryError("predecessor_attempt_id is not among the predecessors")


def recovery(recoveries: Mapping[str, Mapping], key: str) -> Mapping | None:
    return recoveries.get(key)


def rec_suffix(recoveries: Mapping[str, Mapping], key: str) -> str:
    return REC if key in recoveries else ""


def predecessor_spend(recoveries: Mapping[str, Mapping], key: str) -> tuple[int, float]:
    """(model calls, speech seconds) the failed attempts of the cell spent, as recorded."""

    rec = recoveries.get(key)
    if not rec:
        return 0, 0.0
    return (sum(int(p["contacts_spent"]) for p in rec["predecessors"]),
            sum(float(p.get("speech_seconds_spent", 0.0)) for p in rec["predecessors"]))


def cumulative_budget(recoveries: Mapping[str, Mapping], key: str, original_calls: int, original_audio: float) -> tuple[int, int]:
    """The run-cumulative plan budget: the original plan plus the failed attempts' realised spend (audio rounded up)."""

    calls, audio = predecessor_spend(recoveries, key)
    return original_calls + calls, math.ceil(original_audio + audio - 1e-9)


def plan_file_name(stem: str, plan_kind: str, recovered: bool) -> str:
    """Package file name of a registered plan: ``<stem><kind>-plan-registered[-rec1]-v1.json`` (``stem`` carries its own trailing dash or is empty)."""

    return f"{stem}{plan_kind}-plan-registered{REC if recovered else ''}-v1.json"


def superseded_plan_file_names(stem: str, recovered: bool, kinds: tuple[str, ...] = ("generation", "fit")) -> list[str]:
    """First-attempt plan names a recovery supersedes (removed from the package; git history keeps them, the failed attempt stays on the data root)."""

    return [plan_file_name(stem, kind, False) for kind in kinds] if recovered else []


# ---- the predecessor: read from the data root, never typed ---------------------------------------------------------------------------


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_predecessor_attempt(data_root: str | Path, run_id: str, attempt_id: str) -> dict:
    """Read the attempt record of a failed attempt (read-only): state, realised calls / audio seconds, the reservation, the record's sha256."""

    path = Path(data_root) / "attempts" / run_id / f"{attempt_id}.json"
    if not path.is_file():
        raise RecoveryError(f"no attempt record at {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("run_id") != run_id or doc.get("attempt_id") != attempt_id:
        raise RecoveryError(f"{path} names {doc.get('run_id')!r}/{doc.get('attempt_id')!r}")
    actual, reserved = doc.get("actual") or {}, doc.get("reserved") or {}
    calls, audio = actual.get("calls"), actual.get("audio_seconds")
    if isinstance(calls, bool) or not isinstance(calls, int) or calls < 0 or not isinstance(audio, (int, float)) or audio < 0:
        raise RecoveryError(f"{path} carries a malformed actual block: {actual!r}")
    return {"run_id": run_id, "attempt_id": attempt_id, "state": doc.get("state"), "actual_calls": calls, "actual_audio_seconds": float(audio),
            "reserved_calls": reserved.get("calls"), "reserved_audio_seconds": reserved.get("audio_seconds"),
            "attempt_record_relpath": f"attempts/{run_id}/{attempt_id}.json", "attempt_record_sha256": _sha256_file(path)}


def read_fit_progress(data_root: str | Path, fit_run_id: str, fit_attempt_id: str) -> dict:
    """What the live phase fit of the failed attempt left behind (read-only): whether an attempt record exists and how many request-fit envelopes
    sit in its prepared directory (a directory listing; no envelope is opened)."""

    attempt = Path(data_root) / "attempts" / fit_run_id / f"{fit_attempt_id}.json"
    prepared = Path(data_root) / "prepared" / fit_run_id / fit_attempt_id
    envelopes = sum(1 for p in prepared.iterdir() if p.name.endswith(".request-fit.json")) if prepared.is_dir() else 0
    return {"run_id": fit_run_id, "attempt_id": fit_attempt_id, "attempt_record_present": attempt.is_file(),
            "prepared_dir_present": prepared.is_dir(), "prepared_request_fit_envelopes": envelopes}


def snapshot_predecessor(data_root: str | Path, run_id: str, attempt_id: str, fit_run_id: str | None = None, fit_attempt_id: str | None = None,
                         now: datetime | None = None) -> dict:
    """The committed snapshot receipt of a failed attempt's realised spend."""

    doc = {"schema": SNAPSHOT_SCHEMA, "snapshotted_at_utc": (now or datetime.now(timezone.utc)).isoformat(), **read_predecessor_attempt(data_root, run_id, attempt_id)}
    if fit_run_id and fit_attempt_id:
        doc["fit"] = read_fit_progress(data_root, fit_run_id, fit_attempt_id)
    return doc


def load_snapshot(path: str | Path) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if doc.get("schema") != SNAPSHOT_SCHEMA:
        raise RecoveryError(f"{path} is not a {SNAPSHOT_SCHEMA} document")
    return doc


def predecessor_from_snapshot(snapshot: Mapping[str, Any]) -> dict:
    """The ``predecessors`` entry of a recovery record, from the snapshot (the spend is the snapshot's, not typed)."""

    return {"attempt_id": snapshot["attempt_id"], "state": snapshot["state"], "contacts_spent": int(snapshot["actual_calls"]),
            "speech_seconds_spent": float(snapshot["actual_audio_seconds"])}


def verify_predecessor_snapshot(snapshot: Mapping[str, Any], data_root: str | Path) -> dict:
    """Re-read the data root and compare realised calls and audio seconds with the snapshot (state and record bytes may move: an abort rewrites them,
    the realised spend of a dead attempt does not). Raises :class:`RecoveryError` on a mismatch; returns the fresh reading."""

    fresh = read_predecessor_attempt(data_root, snapshot["run_id"], snapshot["attempt_id"])
    if fresh["actual_calls"] != snapshot["actual_calls"] or abs(fresh["actual_audio_seconds"] - snapshot["actual_audio_seconds"]) > 1e-6:
        raise RecoveryError(f"the data root reads {fresh['actual_calls']} calls / {fresh['actual_audio_seconds']} s for {snapshot['attempt_id']}; "
                            f"the snapshot says {snapshot['actual_calls']} / {snapshot['actual_audio_seconds']}: the predecessor is still spending, or the snapshot is stale")
    return fresh


# ---- persisted blocks and text ------------------------------------------------------------------------------------------------------


def persisted_recovery(recoveries: Mapping[str, Mapping], key: str, recovery_at: str, recovery_base: str) -> dict:
    """The recovery block of a plan or protocol document: the persisted subset plus its own registration stamp and base commit."""

    rec = recoveries[key]
    out = {name: rec[name] for name in PERSISTED_RECOVERY_KEYS}
    out["registered_at_utc"] = rec.get("registered_at_utc") or recovery_at
    out["base_commit"] = rec.get("base_commit") or recovery_base
    return dict(sorted(out.items()))


def recovery_budget(recoveries: Mapping[str, Mapping], key: str, caps: Mapping[str, Any]) -> dict:
    """A recovered cell's run-cumulative budget statement: the original plan, the failed attempts' recorded spend, their sum."""

    spent_calls, spent_audio = predecessor_spend(recoveries, key)
    cumulative_calls, cumulative_audio = int(caps["generation_calls_cap"]), int(caps["repeated_speech_audio_seconds_cap"])
    return {
        "original_plan": {"planned_model_calls": cumulative_calls - spent_calls,
                          "planned_speech_audio_seconds": cumulative_audio - int(spent_audio + 0.999999999)},
        "failed_attempt_spend": {"model_calls": spent_calls, "speech_audio_seconds": spent_audio,
                                 "attempt_ids": [p["attempt_id"] for p in recoveries[key]["predecessors"]]},
        "cumulative_plan": {"planned_model_calls": cumulative_calls, "planned_speech_audio_seconds": cumulative_audio},
        "rule": "The adapter budget is run-cumulative across the attempts of a run id; the FIT cap is structural and never scaled.",
    }


def recovery_section(recoveries: Mapping[str, Mapping], key: str, *, role: str, run: str, attempt: str, fit_run: str, fit_attempt: str,
                     caps: Mapping[str, Any], plan_names: tuple[str, str]) -> str:
    """The rec1 text of the README and the preregistration: failed attempt, root cause, fix, rec1 ids, cumulative budget, untouched cells."""

    rec, budget = recoveries[key], recovery_budget(recoveries, key, caps)
    receipt = rec.get("receipt_clause") or f"the generation run id `{run}` is unchanged; the decision receipt is re-minted with the rec1 FIT run id"
    extra = f"- {rec['extra_note']}\n" if rec.get("extra_note") else ""
    return (
        f"\n## Recovery rec1: the {role} (the cell's single recovery re-registration)\n\n"
        f"{rec['reason']}\n\n{rec['amendment']}\n\n"
        f"- Failed attempt: `{rec['predecessor_attempt_id']}` ({rec['predecessor_state']})\n"
        f"- Root cause: {rec['root_cause']}.\n"
        f"- Fix: {rec['fix']}\n"
        f"- Re-flown whole under generation attempt `{attempt}` and FIT run `{fit_run}` / attempt `{fit_attempt}`; {receipt}.\n"
        f"- Run-cumulative plan budget: {budget['original_plan']['planned_model_calls']} + {budget['failed_attempt_spend']['model_calls']} = "
        f"{budget['cumulative_plan']['planned_model_calls']} calls; {budget['original_plan']['planned_speech_audio_seconds']} + "
        f"{budget['failed_attempt_spend']['speech_audio_seconds']:g} = {budget['cumulative_plan']['planned_speech_audio_seconds']} "
        "speech-seconds; the FIT cap stays structural.\n"
        f"- Plans: `{plan_names[0]}`, `{plan_names[1]}` (the first-attempt plan files are superseded and removed from the package; the git history keeps them, "
        "and the failed attempt stays on the data root).\n"
        f"- {rec['unchanged']}\n"
        f"{extra}"
        f"- {rec['rule']}\n")


def countersign_text(recoveries: Mapping[str, Mapping], key: str, *, authority: str, role: str, label: str, attempt: str, fit_run: str, fit_attempt: str,
                     receipt_clause: str, tail: str) -> str:
    """The countersign text of a recovered generation or FIT row (the coordinator replaces the row's notes with it)."""

    rec = recoveries[key]
    calls, audio = predecessor_spend(recoveries, key)
    spend = "0 spent" if calls == 0 else f"{calls} calls and {audio:g} speech-seconds spent"
    return ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: "
            f"{authority}; RECOVERY rec1 of the {role}, the cell's single root-diagnosed recovery re-registration: {label}; the predecessor attempt "
            f"{rec['predecessor_attempt_id']} {rec['predecessor_state']} Root cause: {rec['root_cause']}. Re-flown whole under generation attempt {attempt} and "
            f"FIT run {fit_run} / attempt {fit_attempt}; the plan budget is run-cumulative (original plan + {spend}); {receipt_clause}; {tail})")


def ledger_row(registered_at: str, run_id: str, profile: str, scope: str, model_tool: str, carrier: str, split_hash: str, calls: Any, audio: Any,
               gpu: Any, inherited: str, artifact: str, notes: str, consumed: str = "no") -> str:
    line = " | ".join(["", registered_at, run_id, profile, scope, model_tool, carrier, "discovery", split_hash, consumed, str(calls), str(audio), str(gpu),
                       inherited, artifact, notes, ""]).strip()
    if line.count("\n") or line.count("|") != 16:
        raise RecoveryError(f"a ledger row is malformed ({line.count('|')} pipes)")
    return line


def recovery_ledger_block(recoveries: Mapping[str, Mapping], key: str, *, mark: str, authority: str, package: str, role: str, run: str, fit_run: str,
                          attempt: str, fit_attempt: str, session: str, scope: str, fit_scope: str, model_tool: str, carrier: str, split_hash: str,
                          caps: Mapping[str, Any], config_hash: str, protocol_hash: str, registered_at: str, base_commit: str, worktree: str,
                          branch: str, plan_names: tuple[str, str], inherited: str, profile: str = "bounded-discovery-probe") -> str:
    """The two DRAFT rows of a recovered cell (generation, FIT) as one new ledger block; the first-attempt rows stay exactly as they are
    (same form as the 266-E ``recovery rec1`` blocks of ``docs/exposure-ledger.md``)."""

    rec = recoveries[key]
    budget = recovery_budget(recoveries, key, caps)
    registered_at = rec.get("registered_at_utc") or registered_at
    base_commit = rec.get("base_commit") or base_commit
    worktree, branch = rec.get("worktree") or worktree, rec.get("branch") or branch
    common = (f"RECOVERY RE-REGISTRATION (root-diagnosed, the cell's single one, {rec['recovered_at']}): this row SUPERSEDES the first-attempt row of the same run id "
              "(the coordinator folds the earlier row into this one when countersigning). ")
    gen_notes = (
        f"REGISTERED (DRAFT, root countersignature pending) {registered_at[:10]} at base commit {base_commit} by {rec['agent']} "
        f"(worktree {worktree}, branch {branch}); {authority}. {common}Attempt {rec['predecessor_attempt_id']} {rec['predecessor_state']} "
        f"Root cause: {rec['root_cause']}. The cell is re-flown whole under generation attempt {attempt}, a (run_id, attempt_id) pair being a one-time key; "
        f"the plan budget is run-cumulative across the attempts of the run id: the original plan plus the failed attempt's recorded spend, "
        f"{budget['original_plan']['planned_model_calls']} + {budget['failed_attempt_spend']['model_calls']} = {budget['cumulative_plan']['planned_model_calls']} calls and "
        f"{budget['original_plan']['planned_speech_audio_seconds']} + {budget['failed_attempt_spend']['speech_audio_seconds']:g} = "
        f"{budget['cumulative_plan']['planned_speech_audio_seconds']} speech-seconds. Composed config {config_hash}, protocol {protocol_hash} "
        f"(the re-pin tool rewrites both at the flip). Expected session {session}. A second failure closes the cell. "
        f"HELD: this registration performs no contact and authorises none.")
    fit_notes = (
        f"REGISTERED (DRAFT, root countersignature pending) {registered_at[:10]} at base commit {base_commit} by {rec['agent']} "
        f"(worktree {worktree}, branch {branch}); {authority}. {common}The FIT row of {run} under the rec1 identities: FIT run {fit_run}, "
        f"FIT attempt {fit_attempt} (supersedes FIT run {rec['predecessor_fit_run_id']} / attempt {rec['predecessor_fit_attempt_id']}, {rec['fit_predecessor_phrase']}). "
        f"Root cause: {rec['root_cause']}. The FIT cap stays structural ({caps['fit_endpoint_calls_cap']}, not scaled); speech seconds and GPU hours are the "
        "generation row's ceilings, shared and not additive. HELD: this registration performs no contact and authorises none.")
    gen = ledger_row(registered_at, run, profile, scope, model_tool, carrier, split_hash, caps["generation_calls_cap"], caps["repeated_speech_audio_seconds_cap"],
                     caps["gpu_hours_fit_inclusive"], inherited, f"{package}/{plan_names[0]}", gen_notes)
    fit = ledger_row(registered_at, fit_run, profile, fit_scope, model_tool, carrier, split_hash, caps["fit_endpoint_calls_cap"],
                     caps["repeated_speech_audio_seconds_cap"], caps["gpu_hours_fit_inclusive"], inherited, f"{package}/{plan_names[1]}", fit_notes)
    header = (f"\n{mark}{rec['ledger_title']} (DRAFT, root countersignature pending)\n\n"
              f"Two unconsumed rows -- the recovered generation row and its rec1 live-phase-fit identity -- for the single recovery re-registration of the {role} of "
              f"{authority}. Package {package}. Neither row is countersigned and neither authorises a contact; the first-attempt rows above are unchanged.\n\n"
              "| " + " | ".join(LEDGER_COLUMN_NAMES) + " |\n"
              "| " + " | ".join("---" for _ in LEDGER_COLUMN_NAMES) + " |\n")
    return header + gen + "\n" + fit + "\n"


def append_recovery_ledger_block(ledger_path: str | Path, block: str, attempt: str) -> bool:
    """Append ``block`` at the end of the ledger unless the rec1 generation attempt id already appears in it (idempotent). Returns True when appended."""

    path = Path(ledger_path)
    text = path.read_bytes().decode("utf-8")
    if attempt in text:
        return False
    path.write_bytes((text + ("" if text.endswith("\n") else "\n") + block).encode("utf-8"))
    return True


# ---- CLI ------------------------------------------------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    snap = sub.add_parser("snapshot", help="read a failed attempt's realised spend from the data root into a snapshot receipt (read-only on the data root)")
    snap.add_argument("--data-root", required=True)
    snap.add_argument("--run-id", required=True)
    snap.add_argument("--attempt-id", required=True)
    snap.add_argument("--fit-run-id")
    snap.add_argument("--fit-attempt-id")
    snap.add_argument("--out", required=True)
    ver = sub.add_parser("verify", help="re-read the data root and compare it with a snapshot receipt")
    ver.add_argument("--data-root", required=True)
    ver.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "snapshot":
        doc = snapshot_predecessor(args.data_root, args.run_id, args.attempt_id, args.fit_run_id, args.fit_attempt_id)
        Path(args.out).write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
        print(json.dumps({k: doc[k] for k in ("run_id", "attempt_id", "state", "actual_calls", "actual_audio_seconds")}, sort_keys=True))
        return 0
    fresh = verify_predecessor_snapshot(load_snapshot(args.snapshot), args.data_root)
    print(json.dumps({"verified": True, "actual_calls": fresh["actual_calls"], "actual_audio_seconds": fresh["actual_audio_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
