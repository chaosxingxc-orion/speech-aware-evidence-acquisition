#!/usr/bin/env python3
"""Snapshot the stopped NX-T R2 rec1 column attempt for the rec2 RESUME (model-free, READ-ONLY on the data root).

Owner ruling 328 (2026-10-17): the rec2 registration keeps the complete rows of the stopped rec1 attempt (its row checkpoint, mode B, or its trace, mode A) and
flies the rest. Nothing about the predecessor is typed by hand: this tool reads, from the data root,

* the attempt record (state, realised calls and speech seconds; ``recovery.py`` machinery),
* the live phase fit's prepared directory listing (a count of request-fit envelopes; no envelope is opened),
* the identity of the trace and of the row checkpoint (size, sha256; ``recovery.py snapshot --trace-pin``),
* BOTH replay classifications of the stopped attempt against the registered roster: the trace scan (mode A, ``core.flight.resume.read_predecessor_attempt``) and
  the checkpoint scan (mode B, ``read_checkpoint_predecessor``, materialised in a scratch directory outside the data root),
* the checkpoint header's identity (protocol hash, split identity hash, config hash, implementation sha256 of the three modules a mode-B resume compares) beside the
  CURRENT sha256 of those modules, so the mode choice is a computed comparison, never a typed one.

and writes ONE committed snapshot receipt (``saea-recovery-predecessor-snapshot-v1`` plus ``trace``, ``resume`` and ``mode_inputs`` blocks). The family module
(``nxt_r2_family.py``) builds the rec2 recovery record from that receipt, the rec1 snapshot of the first attempt and the committed diagnosis input. No model, tokenizer,
encoder, scorer, server or GPU contact; no response text is read into the output (counts, ids, hashes only).

    python -B scripts/flights/nx/nxt_r2_rec2_snapshot.py --data-root DIR --run-id RUN --attempt-id STOPPED --fit-run-id FITRUN --fit-attempt-id FITATT \\
        --program-id phase-native-module-v1-c6 --roster docs/receipts/rosters/<arm roster>.json --scratch DIR --out FILE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for _dir in (HERE.parent / "lib", REPO_ROOT / "src"):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import recovery as rcv  # noqa: E402

RESUME_SCHEMA = "saea-nxt-r2-rec2-resume-pin-v1"
#: The three modules whose bytes a mode-B resume compares (``FlightRuntime.row_checkpoint_implementation``), as repo-relative paths.
IMPLEMENTATION_MODULES = {
    "runtime": "src/speech_aware_evidence_acquisition/core/flight/runtime.py",
    "runner": "src/speech_aware_evidence_acquisition/rails/runner.py",
    "row_checkpoint": "src/speech_aware_evidence_acquisition/core/row_checkpoint.py",
}


def current_implementation(root: Path = REPO_ROOT) -> dict[str, str]:
    """The sha256 of the three modules under ``root`` (what ``FlightRuntime.row_checkpoint_implementation`` reads from the running code)."""

    return {name: hashlib.sha256((Path(root) / rel).read_bytes()).hexdigest() for name, rel in IMPLEMENTATION_MODULES.items()}


def _classify(roster_ids: list[str], complete: set[str], incomplete: dict[str, str], started: set[str]) -> dict:
    outside = sorted((complete | started) - set(roster_ids))
    if outside:
        raise SystemExit(f"{len(outside)} sample(s) of the stopped attempt are outside the registered roster: {outside[:3]}")
    kept = [sid for sid in roster_ids if sid in complete]
    flown = [sid for sid in roster_ids if sid not in complete]
    partial = [sid for sid in flown if sid in started]
    from speech_aware_evidence_acquisition.core.flight.resume import kept_sample_ids_sha256  # noqa: PLC0415

    return {
        "counts": {"roster": len(roster_ids), "kept": len(kept), "flown": len(flown), "partial": len(partial), "unstarted": len(flown) - len(partial)},
        "kept_sample_ids_sha256": kept_sample_ids_sha256(kept), "partial_sample_ids": partial,
        "incomplete_reasons": {sid: incomplete[sid] for sid in sorted(incomplete)},
    }


def resume_blocks(data_root: Path, run_id: str, attempt_id: str, program_id: str, roster_path: Path, trace_sha256: str, checkpoint_sha256: str, scratch: Path) -> dict:
    """The replay classification of the stopped attempt against the registered roster in BOTH modes."""

    from speech_aware_evidence_acquisition.core.flight.resume import read_checkpoint_predecessor, read_predecessor_attempt  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.row_checkpoint import checkpoint_path, read_checkpoint  # noqa: PLC0415

    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    ids = [str(item["sample_id"]) for item in roster["items"]]
    attempt_dir = data_root / "runs" / run_id / attempt_id
    scan = read_predecessor_attempt(run_id=run_id, attempt_id=attempt_id, attempt_dir=attempt_dir, expected_trace_sha256=trace_sha256, program_id=program_id)
    trace = _classify(ids, set(scan.complete_sample_ids), dict(scan.incomplete), set(scan.started_sample_ids))
    trace.update(mode="trace", trace_record_count=scan.record_count, predecessor_contacts=scan.contact_count())
    document = read_checkpoint(checkpoint_path(attempt_dir, run_id), expected_sha256=checkpoint_sha256)
    ckpt_scan = read_checkpoint_predecessor(run_id=run_id, attempt_id=attempt_id, attempt_dir=attempt_dir, expected_checkpoint_sha256=checkpoint_sha256,
                                            materialize_dir=scratch / "materialize")
    checkpoint = _classify(ids, set(ckpt_scan.complete_sample_ids), dict(ckpt_scan.incomplete), set(ckpt_scan.started_sample_ids))
    checkpoint.update(mode="checkpoint", checkpoint_rows=len(document.rows), predecessor_contacts=ckpt_scan.contact_count())
    header = {key: document.header.get(key) for key in ("run_id", "attempt_id", "protocol_hash", "split_identity_hash", "config_hash", "policy", "implementation")}
    return {"schema": RESUME_SCHEMA, "program_id": program_id, "roster_relpath": str(roster_path.relative_to(REPO_ROOT)) if roster_path.is_relative_to(REPO_ROOT) else str(roster_path),
            "roster_rows": len(ids), "trace": trace, "checkpoint": checkpoint, "checkpoint_header": header}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True, help="the STOPPED attempt (the rec1 generation attempt)")
    parser.add_argument("--fit-run-id", required=True)
    parser.add_argument("--fit-attempt-id", required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--roster", required=True, help="the registered arm roster receipt (repo-relative or absolute)")
    parser.add_argument("--scratch", required=True, help="a scratch directory OUTSIDE the data root (the checkpoint scan materialises the kept trace there)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    scratch = Path(args.scratch).resolve()
    if scratch.is_relative_to(data_root.resolve()):
        raise SystemExit("--scratch must be outside the data root (the data root is read-only here)")
    roster = Path(args.roster) if Path(args.roster).is_absolute() else REPO_ROOT / args.roster
    doc = rcv.snapshot_predecessor(data_root, args.run_id, args.attempt_id, args.fit_run_id, args.fit_attempt_id, trace_pin=True)
    if "checkpoint_sha256" not in doc["trace"]:
        raise SystemExit("the stopped attempt has no row checkpoint to pin")
    doc["resume"] = resume_blocks(data_root, args.run_id, args.attempt_id, args.program_id, roster, doc["trace"]["trace_sha256"], doc["trace"]["checkpoint_sha256"], scratch)
    recorded, current = doc["resume"]["checkpoint_header"]["implementation"], current_implementation()
    doc["mode_inputs"] = {
        "implementation_recorded_in_checkpoint": recorded, "implementation_current_at_snapshot": current,
        "implementation_differing_modules": sorted(name for name in current if (recorded or {}).get(name) != current[name]),
        "implementation_modules": IMPLEMENTATION_MODULES,
    }
    Path(args.out).write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"attempt_id": doc["attempt_id"], "state": doc["state"], "actual_calls": doc["actual_calls"], "actual_audio_seconds": doc["actual_audio_seconds"],
                      "trace_sha256": doc["trace"]["trace_sha256"], "checkpoint_sha256": doc["trace"]["checkpoint_sha256"],
                      "trace_counts": doc["resume"]["trace"]["counts"], "checkpoint_counts": doc["resume"]["checkpoint"]["counts"],
                      "differing_modules": doc["mode_inputs"]["implementation_differing_modules"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
