#!/usr/bin/env python3
"""Resume prelaunch gate: EVERY resume launch first passes the OFFLINE full-trace replay check.

Coordinator ruling after the COMP-1 resume attempt 3 seal abort: a four-row dry-run smoke cannot
see the seal-time consistency checks a resume-recovery's KEPT rows must still pass under the
CURRENT code (the abort itself was exactly this -- a harness change the smoke never exercised).
So before a resume cell's generation flight opens, this gate:

1. reads the named cell's ``resume_from`` declaration from ``configs/experiment/<experiment>.json``
   (today a single ``{"attempt_id", "trace_sha256"}`` object; this reader also accepts a LIST of
   such objects, so a future multi-predecessor resume does not need a new gate; owner decision 309
   adds the mode-B object ``{"attempt_id", "checkpoint_sha256"}``, verified by hash and chain and
   not replayed -- a kept row is the stored canonical record);
2. verifies, for every declared predecessor, that its trace file on the data root hashes to the
   declared ``trace_sha256`` -- the identity binding a resume-recovery depends on
   (``core.flight.resume.predecessor_trace_path``, read-only, zero model contact);
3. runs ``scripts/analysis/replay_seal_consistency.py`` (the checker) over every declared
   predecessor attempt, under the code THIS PROCESS is running, and
4. exits non-zero, naming the failing row count and the check names, if any row fails or any row
   is sealed twice (across ALL declared predecessors together, so an overlap between two
   predecessors is caught even though neither open now).

Zero model, tokenizer, encoder, scorer, server, GPU and network contact -- everything here is a
local file read, a subprocess of the checker (itself model-free), or ``git rev-parse``. It never
prints utterance text, transcripts or model output: only counts, check-kind names and hashes.

On success it prints a receipt (``schema saea-resume-replay-proof-v1``) with the fields a
readiness package's ``*plan-registered*.json`` should carry as its own ``resume_replay_proof``
block (see ``scripts/flights/batch/README.md`` and the ``resume-replay-unproven`` finding of
``scripts/checks/flight_registration_check.py``, which refuses a launch lacking that block).

Exit codes: 0 the cell is not a resume cell, or every predecessor replays clean; 1 the replay
proves a problem (a failing row or a row sealed twice); 2 the cell, its ``resume_from``
declaration, a predecessor trace, or the checker itself cannot be read or trusted.

Flags: ``--repo-root``, ``--data-root``, ``--experiment``, ``--cell``, ``--checker`` (testing
override for the checker script path; defaults to ``scripts/analysis/replay_seal_consistency.py``
under ``--repo-root``), ``--python`` (testing override for the interpreter that runs it; defaults
to this process's own interpreter).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

SCHEMA_PROOF = "saea-resume-replay-proof-v1"
SCHEMA_NOT_APPLICABLE = "saea-resume-prelaunch-gate-not-applicable-v1"

#: The fields ``resume_replay_proof`` (in a readiness package's ``*plan-registered*.json``) must
#: name -- kept as one tuple so the gate's own receipt and the registration-check finding
#: (``scripts/checks/flight_registration_check.py``) can never drift apart on the spelling.
RESUME_REPLAY_PROOF_FIELDS = (
    "rows_checked", "rows_failing", "sealed_twice", "checker_sha256", "code_commit",
)


class GateError(RuntimeError):
    """The cell, its ``resume_from`` declaration, a predecessor trace, or the checker is unusable."""


def _load_cell(repo_root: Path, experiment: str, cell_id: str) -> dict[str, Any]:
    path = repo_root / "configs" / "experiment" / f"{experiment}.json"
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GateError(f"cannot read {path}: {error}") from error
    cells = document.get("cells") if isinstance(document, dict) else None
    if not isinstance(cells, list):
        raise GateError(f"{path} declares no cells")
    matches = [item for item in cells if isinstance(item, dict) and item.get("cell_id") == cell_id]
    if len(matches) != 1:
        raise GateError(f"cell {cell_id!r} appears {len(matches)} times in {path}")
    return matches[0]


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def resume_declarations(cell: dict[str, Any]) -> list[dict[str, str]]:
    """Normalise ``cell["resume_from"]`` to a list of ``{"attempt_id", "trace_sha256"}``.

    ``None`` (no key) -> ``[]``: the cell is not a resume cell. A single object -> a one-item
    list (today's only registered shape). A list of objects is also accepted, read-only, so a
    future multi-predecessor resume needs no new reader here; nothing in ``core.flight.resume``
    or ``core.flight.campaign`` is changed or relied on to accept that shape yet.
    """

    resume_from = cell.get("resume_from")
    if resume_from is None:
        return []
    if isinstance(resume_from, dict):
        candidates: list[Any] = [resume_from]
    elif isinstance(resume_from, list):
        candidates = list(resume_from)
    else:
        raise GateError("resume_from must be an object or a list of objects")
    declarations: list[dict[str, str]] = []
    for item in candidates:
        if not isinstance(item, dict) or set(item) not in (
            {"attempt_id", "trace_sha256"}, {"attempt_id", "checkpoint_sha256"},
        ):
            raise GateError(
                "each resume_from entry must declare exactly {'attempt_id', 'trace_sha256'} "
                "(mode A) or {'attempt_id', 'checkpoint_sha256'} (mode B, owner decision 309)"
            )
        attempt_id = item["attempt_id"]
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise GateError("resume_from.attempt_id must be a non-empty string")
        if "checkpoint_sha256" in item:
            if not _is_sha256(item["checkpoint_sha256"]):
                raise GateError(
                    "resume_from.checkpoint_sha256 must be a 64-hex SHA-256 of the "
                    "predecessor attempt's row checkpoint file"
                )
            declarations.append(
                {"attempt_id": attempt_id, "checkpoint_sha256": item["checkpoint_sha256"]}
            )
            continue
        trace_sha256 = item["trace_sha256"]
        if not _is_sha256(trace_sha256):
            raise GateError(
                "resume_from.trace_sha256 must be a 64-hex SHA-256 of the predecessor attempt's "
                "trace file"
            )
        declarations.append({"attempt_id": attempt_id, "trace_sha256": trace_sha256})
    return declarations


def _verify_checkpoint_identity(
    data_root: Path, run_id: str, declaration: dict[str, str]
) -> tuple[list[str], int]:
    """Mode B: the checkpoint must hash to its pin and chain end to end. Returns
    ``(keepable sample ids, rows the checkpoint holds)`` -- no replay is possible or
    needed: a kept row is the stored canonical record, used verbatim."""

    from speech_aware_evidence_acquisition.core.row_checkpoint import (  # noqa: PLC0415
        RowCheckpointError, checkpoint_path, read_checkpoint,
    )

    attempt_dir = data_root / "runs" / run_id / declaration["attempt_id"]
    path = checkpoint_path(attempt_dir, run_id)
    if not path.is_file():
        raise GateError(
            f"predecessor attempt {declaration['attempt_id']!r} has no row checkpoint at {path}"
        )
    try:
        document = read_checkpoint(path, expected_sha256=declaration["checkpoint_sha256"])
    except RowCheckpointError as error:
        raise GateError(str(error)) from error
    return [row.sample_id for row in document.rows if row.keepable], len(document.rows)


def _verify_trace_identity(data_root: Path, run_id: str, declaration: dict[str, str]) -> None:
    from speech_aware_evidence_acquisition.core.flight.resume import (  # noqa: PLC0415
        predecessor_trace_path,
    )

    attempt_dir = data_root / "runs" / run_id / declaration["attempt_id"]
    trace_path = predecessor_trace_path(attempt_dir, run_id)
    if not trace_path.is_file():
        raise GateError(
            f"predecessor attempt {declaration['attempt_id']!r} has no trace at {trace_path}"
        )
    digest = hashlib.sha256()
    with trace_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    actual = digest.hexdigest()
    expected = declaration["trace_sha256"]
    if actual != expected:
        raise GateError(
            f"predecessor trace {trace_path} hashes to {actual}, not the declared {expected}; a "
            "resume replay applies only to the exact predecessor bytes resume_from names"
        )


def _git_head(repo_root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _check_names(report: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    for attempt in report.get("attempts") or ():
        if isinstance(attempt, dict):
            names.update((attempt.get("failures_by_check") or {}).keys())
    return sorted(names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--cell", required=True)
    parser.add_argument(
        "--checker", type=Path, default=None,
        help="override scripts/analysis/replay_seal_consistency.py (testing only)",
    )
    parser.add_argument(
        "--python", default=sys.executable,
        help="interpreter to run the checker with (testing only)",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()

    try:
        cell = _load_cell(repo_root, args.experiment, args.cell)
        run_id = str(cell.get("run_id") or "").strip()
        if not run_id:
            raise GateError(f"cell {args.cell!r} declares no run_id")
        declarations = resume_declarations(cell)
        if not declarations:
            print(json.dumps({
                "schema": SCHEMA_NOT_APPLICABLE,
                "experiment": args.experiment,
                "cell": args.cell,
                "note": "cell declares no resume_from; nothing to replay",
            }, indent=2, sort_keys=True))
            return 0
        checkpoint_kept: list[str] = []
        for declaration in declarations:
            if "checkpoint_sha256" in declaration:
                keepable, _held = _verify_checkpoint_identity(data_root, run_id, declaration)
                checkpoint_kept.extend(keepable)
            else:
                _verify_trace_identity(data_root, run_id, declaration)
    except GateError as error:
        print(f"resume prelaunch gate REFUSED: {error}", file=sys.stderr)
        return 2
    trace_declarations = [d for d in declarations if "trace_sha256" in d]
    checkpoint_twice = len(checkpoint_kept) - len(set(checkpoint_kept))

    if not trace_declarations:
        # Mode B only (owner decision 309): the identity and the chain were verified above; a
        # stored row is not re-rendered, so there is nothing for the replay checker to read.
        if checkpoint_twice:
            print(
                f"resume prelaunch gate REFUSED: {checkpoint_twice} row(s) sealed twice across "
                f"{len(declarations)} checkpoint predecessor(s)", file=sys.stderr,
            )
            return 1
        print(json.dumps({
            "schema": SCHEMA_PROOF,
            "experiment": args.experiment,
            "cell": args.cell,
            "run_id": run_id,
            "predecessor_attempts": [d["attempt_id"] for d in declarations],
            "mode": "checkpoint",
            "rows_checked": len(checkpoint_kept),
            "rows_failing": 0,
            "sealed_twice": 0,
            "checker_sha256": hashlib.sha256(
                (Path(__file__).resolve().parents[2] / "src" / "speech_aware_evidence_acquisition"
                 / "core" / "row_checkpoint.py").read_bytes()
            ).hexdigest(),
            "code_commit": _git_head(repo_root),
        }, indent=2, sort_keys=True))
        return 0

    checker = (args.checker or (repo_root / "scripts" / "analysis" / "replay_seal_consistency.py"))
    checker = Path(checker).resolve()
    if not checker.is_file():
        print(f"resume prelaunch gate REFUSED: checker script missing: {checker}", file=sys.stderr)
        return 2

    command = [
        str(args.python), "-B", str(checker),
        "--experiment", args.experiment, "--run-id", run_id,
        "--repo-root", str(repo_root), "--data-root", str(data_root),
    ]
    for declaration in trace_declarations:
        command += ["--attempt", declaration["attempt_id"]]
    completed = subprocess.run(command, capture_output=True, text=True)

    try:
        report = json.loads(completed.stdout)
    except (json.JSONDecodeError, TypeError):
        print(
            "resume prelaunch gate REFUSED: the checker produced no parseable report "
            f"(exit {completed.returncode})",
            file=sys.stderr,
        )
        if completed.stderr:
            print(completed.stderr[-1000:], file=sys.stderr)
        return 2

    rows_checked = int(report.get("rows_checked_total") or 0) + len(checkpoint_kept)
    rows_failing = int(report.get("rows_failing_total") or 0)
    sealed_twice = int((report.get("union") or {}).get("sealed_twice") or 0) + checkpoint_twice
    checks = _check_names(report)
    if completed.returncode != 0 or rows_failing or sealed_twice:
        print(
            "resume prelaunch gate REFUSED: "
            f"{rows_failing} row(s) failing ({', '.join(checks) or 'no check names reported'}), "
            f"{sealed_twice} row(s) sealed twice across {len(declarations)} predecessor(s) "
            f"(checker exit {completed.returncode})",
            file=sys.stderr,
        )
        print(completed.stdout)
        return 1

    receipt = {
        "schema": SCHEMA_PROOF,
        "experiment": args.experiment,
        "cell": args.cell,
        "run_id": run_id,
        "predecessor_attempts": [declaration["attempt_id"] for declaration in declarations],
        "rows_checked": rows_checked,
        "rows_failing": rows_failing,
        "sealed_twice": sealed_twice,
        "checker_sha256": hashlib.sha256(checker.read_bytes()).hexdigest(),
        "code_commit": _git_head(repo_root),
    }
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
