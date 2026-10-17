#!/usr/bin/env python3
"""Snapshot the stopped NX-T R1 rec1 column attempt for the rec2 mode-A RESUME (model-free, READ-ONLY on the data root).

Owner ruling 320 B (2026-10-16): the rec2 registration keeps the complete rows of the stopped rec1 attempt by trace replay (``resume_from`` =
{attempt id, trace sha256}) and flies the rest. Nothing about the predecessor is typed by hand: this tool reads, from the data root,

* the attempt record (state, realised calls and speech seconds; ``recovery.py`` machinery),
* the live phase fit's prepared directory listing (a count of request-fit envelopes; no envelope is opened),
* the identity of the trace and of the row checkpoint (size, sha256),
* the trace's own replay classification (``core.flight.resume.read_predecessor_attempt``: COMPLETE rows, INCOMPLETE rows and why, rows never started),

and writes ONE committed snapshot receipt (``saea-recovery-predecessor-snapshot-v1`` plus ``trace`` and ``resume`` blocks). The family module
(``nxt_r1_family.py``) builds the rec2 recovery record from that receipt and from the rec1 snapshot of the first attempt; the writer re-verifies both against the
data root whenever the root is present. No model, tokenizer, encoder, scorer, server or GPU contact; no response text is read into the output (counts, ids,
hashes only).

    python -B scripts/flights/nx/nxt_r1_rec2_snapshot.py --data-root DIR --run-id RUN --attempt-id STOPPED --fit-run-id FITRUN --fit-attempt-id FITATT \\
        --program-id phase-native-module-v1-c10 --roster docs/receipts/rosters/slurp-evo-fold-b-v2.json --out FILE
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for _dir in (HERE.parent / "lib", REPO_ROOT / "src"):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import recovery as rcv  # noqa: E402

RESUME_SCHEMA = "saea-nxt-r1-rec2-resume-pin-v1"


def resume_block(data_root: Path, run_id: str, attempt_id: str, program_id: str, roster_path: Path, trace_sha256: str) -> dict:
    """The replay classification of the stopped attempt against the registered roster: kept (COMPLETE) and flown (the rest, partial first)."""

    from speech_aware_evidence_acquisition.core.flight.resume import kept_sample_ids_sha256, read_predecessor_attempt  # noqa: PLC0415

    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    ids = [str(item["sample_id"]) for item in roster["items"]]
    scan = read_predecessor_attempt(run_id=run_id, attempt_id=attempt_id, attempt_dir=data_root / "runs" / run_id / attempt_id,
                                    expected_trace_sha256=trace_sha256, program_id=program_id)
    complete = set(scan.complete_sample_ids)
    outside = sorted((complete | set(scan.started_sample_ids)) - set(ids))
    if outside:
        raise SystemExit(f"{len(outside)} sample(s) of the stopped attempt are outside the registered roster: {outside[:3]}")
    kept = [sid for sid in ids if sid in complete]
    flown = [sid for sid in ids if sid not in complete]
    partial = [sid for sid in flown if sid in scan.incomplete]
    return {
        "schema": RESUME_SCHEMA, "mode": "trace", "program_id": program_id, "roster_relpath": str(roster_path.relative_to(REPO_ROOT)) if roster_path.is_relative_to(REPO_ROOT) else str(roster_path),
        "roster_rows": len(ids), "trace_record_count": scan.record_count, "predecessor_contacts": scan.contact_count(),
        "counts": {"roster": len(ids), "kept": len(kept), "flown": len(flown), "partial": len(partial), "unstarted": len(flown) - len(partial)},
        "kept_sample_ids_sha256": kept_sample_ids_sha256(kept), "partial_sample_ids": partial,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True, help="the STOPPED attempt (the rec1 generation attempt)")
    parser.add_argument("--fit-run-id", required=True)
    parser.add_argument("--fit-attempt-id", required=True)
    parser.add_argument("--program-id", required=True)
    parser.add_argument("--roster", required=True, help="the registered arm roster receipt (repo-relative or absolute)")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    roster = Path(args.roster) if Path(args.roster).is_absolute() else REPO_ROOT / args.roster
    doc = rcv.snapshot_predecessor(data_root, args.run_id, args.attempt_id, args.fit_run_id, args.fit_attempt_id, trace_pin=True)
    doc["resume"] = resume_block(data_root, args.run_id, args.attempt_id, args.program_id, roster, doc["trace"]["trace_sha256"])
    Path(args.out).write_bytes((json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({"attempt_id": doc["attempt_id"], "state": doc["state"], "actual_calls": doc["actual_calls"], "actual_audio_seconds": doc["actual_audio_seconds"],
                      "trace_sha256": doc["trace"]["trace_sha256"], "counts": doc["resume"]["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
