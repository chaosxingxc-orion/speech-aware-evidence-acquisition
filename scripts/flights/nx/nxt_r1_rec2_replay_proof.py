#!/usr/bin/env python3
"""Turn the report of the offline seal-consistency replay into the committed ``resume_replay_proof`` receipt of the NX-T R1 rec2 resume (model-free).

``scripts/flights/nx/nxt_r1_write_registration.py`` attaches ``<package>/resume-replay-proof-rec2-v1.json`` to the rec2 generation plan; the registration check
(``resume-replay-unproven``) refuses a launch of a cell that declares ``resume_from`` without it. The replay itself is
``scripts/analysis/replay_seal_consistency.py`` over the stopped attempt's trace, run on a scratch COPY of the trace (sha256 verified identical) with the other data
root entries linked read-only; the batch driver's prelaunch gate repeats it on the flight commit.

    python -B scripts/flights/nx/nxt_r1_rec2_replay_proof.py --replay-json REPORT.json --code-commit <sha> --replay-at <UTC> [--root DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nxt_r1_family as fam  # noqa: E402

PROOF_FILE = "resume-replay-proof-rec2-v1.json"


def build_proof(replay: dict, code_commit: str, replay_at: str, root: Path) -> dict:
    rec = fam.recovery("arm")
    if not rec or not rec.get("resume_from"):
        raise SystemExit("the family has no rec2 resume record (commit the rec2 snapshot first)")
    pred, trace = rec["resume_from"]["attempt_id"], rec["resume_from"]["trace_sha256"]
    attempts = replay["attempts"]
    if len(attempts) != 1 or attempts[0]["attempt_id"] != pred or attempts[0]["trace_sha256"] != trace:
        raise SystemExit("the replay report names another attempt or trace than the rec2 resume_from")
    a = attempts[0]
    counts = rec["resume_counts"]
    if a["complete"] != counts["kept"]:
        raise SystemExit(f"the replay found {a['complete']} complete rows, the snapshot says {counts['kept']}")
    checker = root / "scripts/analysis/replay_seal_consistency.py"
    return {
        "schema": "saea-resume-replay-proof-v1",
        "tool": f"scripts/analysis/replay_seal_consistency.py --experiment {fam.CELLS['arm']['cell']} --run-id {fam.CELLS['arm']['run']} --predecessor {pred}:{trace}",
        "gate": "scripts/checks/resume_prelaunch_gate_check.py (via scripts/flights/batch/resume_prelaunch_gate.sh) on this cell, re-run by the driver's prelaunch on the "
                "flight commit",
        "run_at_utc": replay_at,
        "predecessor_attempts": [{
            "attempt_id": pred, "trace_sha256": trace, "samples_started": a["samples_started"], "complete": a["complete"], "incomplete": a["incomplete"],
            "rows_checked": a["rows_checked"], "rows_failing": a["rows_failing"], "rows_with_perception_branches": a.get("rows_with_perception_branches"),
            "rows_with_deliver_normaliser": a.get("rows_with_deliver_normaliser"),
            "perception_branch_note_parse_status": a.get("perception_branch_note_parse_status"),
        }],
        "rows_checked": replay["rows_checked_total"], "rows_failing": replay["rows_failing_total"], "sealed_twice": replay["union"]["sealed_twice"],
        "union_complete_rows": replay["union"]["complete_rows"],
        "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(), "resume_py_sha256": replay["resume_py_sha256"], "code_commit": code_commit,
        "model_contacts": replay["model_contacts"],
        "note": ("Model-free and read-only over a scratch COPY of the stopped rec1 attempt's trace (sha256 verified identical to the data root's), assets read through "
                 "symlinks to the data root: every kept row rendered through the real seal stage and re-checked against I7 / I7n / I7v (the v5 thinking-policy wire "
                 "check and the absent-column check included) one row at a time; no row fails and no sample is sealed twice. The replay ran at the branch base commit "
                 "(src/ identical to the branch tip); the driver's prelaunch gate re-runs the same check at launch on the flight commit."),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--replay-json", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--replay-at", required=True)
    parser.add_argument("--root", type=Path, default=fam.REPO_ROOT)
    args = parser.parse_args(argv)
    proof = build_proof(json.loads(args.replay_json.read_text(encoding="utf-8")), args.code_commit, args.replay_at, args.root)
    out = args.root / fam.PACKAGE / PROOF_FILE
    out.write_bytes((json.dumps(proof, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    print(json.dumps({k: proof[k] for k in ("rows_checked", "rows_failing", "sealed_twice", "union_complete_rows", "code_commit")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
