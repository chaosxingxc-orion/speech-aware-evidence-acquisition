#!/usr/bin/env python3
"""Compute the resume MODE of the NX-T R3 rec2 registration and write it into the committed rec2 recovery input (model-free, READ-ONLY on the data root).

Owner ruling 328: "a stopped attempt is resumed, never re-flown whole, whenever a checkpoint or trace exists" -- mode B (the row checkpoint) when the code identity
the checkpoint was written under is unchanged, else mode A (the trace). The choice is a computation, never a typed value:

1. code identity: ``git diff --quiet <rec1 flight commit> HEAD`` over the three modules a mode-B resume compares (core/flight/runtime.py, rails/runner.py,
   core/row_checkpoint.py), and the snapshot's recorded-versus-current sha256 of the same three files;
2. the header binding: ``read_checkpoint_predecessor`` -- the very reader a mode-B launch runs -- is called on the data root's checkpoint (read-only; the kept trace is
   materialised in a scratch directory) with the protocol hash and split identity hash the rec2 registration derives, and with the current implementation identity.
   The protocol hash covers the whole experiment fragment (including the cell's attempt id), so it is computed from the DERIVED rec2 configuration, not assumed.

Mode B is chosen iff both hold; otherwise mode A, and the refusal text is recorded verbatim in the input. The tool rewrites ``resume_mode`` / ``resume_mode_basis``
(and ``resume_mode_evidence``) in the input and re-derives the cell fragments for the final mode.

    python -B scripts/flights/nx/nxt_r3_rec2_mode.py --data-root DIR --rec1-flight-commit 9790c071f --scratch DIR
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for _dir in (HERE, HERE.parent / "lib", REPO_ROOT / "src"):
    if str(_dir) not in sys.path:
        sys.path.insert(0, str(_dir))

import nxt_r3_rec2_snapshot as snapmod  # noqa: E402
import recovery as rcv  # noqa: E402

INPUT = "docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/recovery-input-arm-rec2-v1.json"
SNAPSHOT = "docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/predecessor-snapshot-arm-rec2-v1.json"


def _run(*cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=REPO_ROOT, capture_output=True, text=True)


def _derive_ids() -> dict:
    """Re-derive the cell fragments from the CURRENT input and return the arm cell's protocol hash and split identity hash (a fresh interpreter: the family reads the
    input at import)."""

    done = _run(sys.executable, "-B", "scripts/flights/nx/nxt_r3_derive_cells.py")
    if done.returncode:
        raise SystemExit(f"the derive failed: {done.stderr[-600:]}")
    probe = ("import json, sys; sys.path.insert(0, 'scripts/flights/nx'); import nxt_r3_write_registration as w; from pathlib import Path; "
             "i = w.identities(Path('.'))['arm']; print(json.dumps({'protocol_hash': i['protocol_hash'], 'split_identity_hash': i['split_identity_hash'], "
             "'composed_config_hash': i['composed_config_hash'], 'attempt_id': i['attempt_id']}))")
    out = _run(sys.executable, "-B", "-c", probe)
    if out.returncode:
        raise SystemExit(f"the identity probe failed: {out.stderr[-600:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--rec1-flight-commit", required=True, help="the commit the stopped rec1 attempt flew from (its checkpoint's code identity)")
    parser.add_argument("--scratch", required=True)
    args = parser.parse_args(argv)
    input_path, snapshot_path = REPO_ROOT / INPUT, REPO_ROOT / SNAPSHOT
    snap = rcv.load_snapshot(snapshot_path)
    header = snap["resume"]["checkpoint_header"]
    attempt_id, run_id = snap["attempt_id"], snap["run_id"]

    # 1. code identity
    differing_git = []
    for name, rel in snapmod.IMPLEMENTATION_MODULES.items():
        if _run("git", "diff", "--quiet", args.rec1_flight_commit, "HEAD", "--", rel).returncode:
            differing_git.append(name)
    current = snapmod.current_implementation()
    differing_sha = sorted(name for name in current if (header["implementation"] or {}).get(name) != current[name])
    code_same = not differing_git and not differing_sha

    # 2. the header binding, through the launch-time reader, on the rec2 configuration derived for a trial mode-B declaration
    document = json.loads(input_path.read_text(encoding="utf-8"))
    document.update(resume_mode="checkpoint", resume_mode_basis="trial (nxt_r3_rec2_mode.py derives the rec2 configuration before it decides)")
    input_path.write_bytes((json.dumps(document, indent=2) + "\n").encode("utf-8"))
    ids = _derive_ids()
    from speech_aware_evidence_acquisition.core.flight.resume import ResumeRecoveryError, read_checkpoint_predecessor  # noqa: PLC0415

    refusal = None
    try:
        read_checkpoint_predecessor(
            run_id=run_id, attempt_id=attempt_id, attempt_dir=Path(args.data_root) / "runs" / run_id / attempt_id,
            expected_checkpoint_sha256=snap["trace"]["checkpoint_sha256"], materialize_dir=Path(args.scratch) / "mode-probe",
            protocol_hash=ids["protocol_hash"], split_identity_hash=ids["split_identity_hash"], implementation=current)
    except ResumeRecoveryError as error:
        refusal = str(error).replace(str(Path(args.data_root)), "$SPEECHRL_DATA_DIR")
    hash_same = ids["protocol_hash"] == header["protocol_hash"]
    mode = "checkpoint" if (code_same and refusal is None) else "trace"
    evidence = {
        "rec1_flight_commit": args.rec1_flight_commit,
        "modules_differing_by_git_diff": differing_git, "modules_differing_by_sha256_against_the_checkpoint_header": differing_sha,
        "rec2_protocol_hash": ids["protocol_hash"], "checkpoint_header_protocol_hash": header["protocol_hash"], "protocol_hash_equal": hash_same,
        "rec2_split_identity_hash": ids["split_identity_hash"], "checkpoint_header_split_identity_hash": header["split_identity_hash"],
        "rec2_composed_config_hash": ids["composed_config_hash"], "checkpoint_header_config_hash": header["config_hash"],
        "checkpoint_reader_refusal": refusal,
    }
    if mode == "checkpoint":
        basis = (f"the code identity a checkpoint resume compares (core/flight/runtime.py, rails/runner.py, core/row_checkpoint.py) is byte-identical between the rec1 "
                 f"flight commit {args.rec1_flight_commit} and this registration (git diff --quiet and the sha256 recorded in the checkpoint header), and the launch-time "
                 "checkpoint reader accepts the header against the rec2 protocol hash and split identity hash.")
    else:
        why = []
        if not code_same:
            why.append(f"the code identity changed in {sorted(set(differing_git) | set(differing_sha))}")
        if refusal is not None:
            why.append("the launch-time checkpoint reader refuses the rec1 checkpoint for the rec2 attempt: " + refusal)
        basis = (f"the runtime, runner and row_checkpoint modules are {'byte-identical' if code_same else 'NOT byte-identical'} between the rec1 flight commit "
                 f"{args.rec1_flight_commit} and this registration, but " + "; ".join(why) + ". The protocol hash covers the whole experiment fragment, including the cell's "
                 f"attempt id, so a new attempt id of the same cell can never present the header's protocol hash ({header['protocol_hash'][:12]}... against the rec2 "
                 f"{ids['protocol_hash'][:12]}...). The trace pin has no such binding and its complete-row set equals the checkpoint's (same kept-row id hash).")
    document.update(resume_mode=mode, resume_mode_basis=basis, resume_mode_evidence=evidence)
    input_path.write_bytes((json.dumps(document, indent=2) + "\n").encode("utf-8"))
    _derive_ids()                                   # leave the derived fragments in the final mode's form
    print(json.dumps({"resume_mode": mode, "code_same": code_same, "protocol_hash_equal": hash_same, "refusal": refusal}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
