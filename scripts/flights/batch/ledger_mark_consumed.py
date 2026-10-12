#!/usr/bin/env python3
"""Close exposure-ledger rows whose flight sealed (``consumed = no`` -> ``yes``).

Model-free. Reads sealed run directories under ``$SPEECHRL_DATA_DIR`` read-only and rewrites,
in place, ONLY the ``consumed`` cell and the front of the ``notes`` cell of rows that are still
``consumed = no``. Row order, row count, every other cell and any countersignature text already in
the notes cell are preserved. The calls / speech-audio-seconds / gpu-hours cells keep the
registered ceilings (the convention of every ``yes`` row since 2026-09-22 -- the FIT rows carry
four times the run's calls, so those cells are budgets, not measurements); the measured figures
go into the disposition text at the front of the notes cell, as ``cell1_verdict.py`` does.

Evidence by row kind (a row is closed only when its evidence exists):

* run / smoke row -- ``runs/<run id>/<attempt>/<run id>.run-manifest.json`` with ``status ==
  COMPLETED`` (the sealed attempt; when an attempt record ``attempts/<run id>/<attempt>.json``
  exists its ``state`` must be ``FINALIZED`` or ``OPENED`` -- smoke runs stay OPENED). The latest sealed attempt is quoted.
* FIT row -- ``prepared/<FIT id>/`` holds the FIT receipt AND the paired run (the id with its
  ``-FIT`` token removed) has a sealed attempt.
* model-free read / paired-analysis row -- the id is cited by a results note under
  ``docs/results/`` AND either ``analysis/<id>/`` holds artefacts or the parent run (the id with its
  ``-POOL-READ`` / ``-COLUMN-READ`` suffix replaced by ``-V1``) has a sealed attempt.

Dry run is the default; ``--apply`` writes. A row without evidence stays ``no`` (HELD, retired,
superseded and never-flown cells).
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

LEDGER = "docs/exposure-ledger.md"
RESULTS_DIR = "docs/results"
def _authority_default() -> str:
    """The data-root default assigned in scripts/lib/data_root.sh (decision 274: one authority)."""
    lib = Path(__file__).resolve().parents[2] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


DEFAULT_DATA_ROOT = _authority_default()
DATE_COL, RUN_COL, CONSUMED_COL, NOTES_COL = 1, 2, 9, 15
EXPECTED_CELLS = 17
STAMP = "ledger_mark_consumed.py"

#: Attempt states that coexist with a COMPLETED run manifest. Production runs end FINALIZED; the
#: four-row smoke and structural runs keep their attempt record OPENED after the manifest seals.
SEALED_STATES = ("FINALIZED", "OPENED")

_MF_TOKENS = re.compile(r"PAIRED-ANALYSIS|-READ(?:-|$)|-BUILD-|-PROOF-")


def data_root_default() -> Path:
    return Path(os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or DEFAULT_DATA_ROOT)


def iter_open_rows(lines: list[str], since: str):
    """``(line index, cells)`` of every table row whose consumed cell is exactly ``no``."""
    for index, line in enumerate(lines):
        if not line.startswith("| 20"):
            continue
        cells = line.split("|")
        if len(cells) != EXPECTED_CELLS:
            continue
        if cells[CONSUMED_COL].strip() != "no":
            continue
        if cells[DATE_COL].strip()[:10] < since:
            continue
        yield index, cells


def _non_empty_dir(path: Path) -> bool:
    return path.is_dir() and any(path.iterdir())


def sealed_attempt(data_root: Path, run_id: str) -> dict | None:
    """The latest sealed (manifest ``COMPLETED``, attempt ``FINALIZED`` when recorded) attempt."""
    found = []
    for manifest in sorted((data_root / "runs" / run_id).glob("*/*.run-manifest.json")):
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if payload.get("status") != "COMPLETED" or payload.get("run_id", run_id) != run_id:
            continue
        attempt_id = (payload.get("attempt") or {}).get("attempt_id") or manifest.parent.name
        state = None
        record = data_root / "attempts" / run_id / f"{attempt_id}.json"
        if record.is_file():
            try:
                state = json.loads(record.read_text(encoding="utf-8")).get("state")
            except (OSError, UnicodeError, json.JSONDecodeError):
                state = "UNREADABLE"
            if state not in SEALED_STATES:
                continue
        cost = payload.get("cost") or {}
        found.append(
            {
                "attempt_id": attempt_id,
                "state": state,
                "sealed_at": str(payload.get("created_at") or "")[:19],
                "calls": cost.get("calls_used"),
                "audio_seconds": cost.get("audio_seconds_used"),
                "latency_seconds": cost.get("latency_seconds_total"),
                "study_commit": str(payload.get("study_commit") or "")[:9],
            }
        )
    found.sort(key=lambda item: item["sealed_at"])
    return found[-1] if found else None


def paired_run_ids(fit_id: str) -> list[str]:
    """Candidate run ids of a FIT row: the id with one ``-FIT`` token removed."""
    out = []
    for match in re.finditer(r"-FIT(?=-|$)", fit_id):
        out.append(fit_id[: match.start()] + fit_id[match.end():])
    stripped = re.sub(r"-FIT-V\d+$", "", fit_id)  # "<run id>-FIT-V1" where the run id itself ends in -V1
    if stripped != fit_id and stripped not in out:
        out.append(stripped)
    # "<stem>-FIT-REC<n>-V1": the recovery re-registration's FIT run (the generation run id keeps its name, "<stem>-V1";
    # the 266-E Instruct rec1 of 2026-10-11 was the first such row).
    rec = re.sub(r"-FIT-REC\d+-V(\d+)$", r"-V\1", fit_id)
    if rec != fit_id and rec not in out:
        out.append(rec)
    return out


def results_notes(repo_root: Path) -> dict[str, str]:
    notes = {}
    for path in sorted((repo_root / RESULTS_DIR).glob("*.md")):
        try:
            notes[path.name] = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    return notes


def classify(data_root: Path, notes: dict[str, str], run_id: str) -> dict | None:
    """Evidence that this open row's cell was flown / read, or ``None``."""
    sealed = sealed_attempt(data_root, run_id)
    if sealed is not None:
        return {"kind": "run", **sealed}
    if "-FIT" in run_id:
        prepared = data_root / "prepared" / run_id
        if _non_empty_dir(prepared):
            for candidate in paired_run_ids(run_id):
                paired = sealed_attempt(data_root, candidate)
                if paired is not None:
                    return {"kind": "fit", "paired": candidate, "attempt_id": paired["attempt_id"]}
    if _MF_TOKENS.search(run_id):
        cited = [name for name, text in notes.items() if run_id in text]
        if cited:
            if _non_empty_dir(data_root / "analysis" / run_id):
                return {"kind": "read", "note": cited[0], "basis": f"analysis/{run_id}"}
            parent = re.sub(r"-(?:POOL-|COLUMN-)?READ-V1$", "-V1", run_id)
            if parent != run_id and sealed_attempt(data_root, parent) is not None:
                return {"kind": "read", "note": cited[0], "basis": f"sealed parent run {parent}"}
    return None


def disposition(evidence: dict, run_id: str, today: str) -> str:
    kind = evidence["kind"]
    if kind == "run":
        figures = []
        if evidence["calls"] is not None:
            figures.append(f"{evidence['calls']} contacts")
        if evidence["audio_seconds"] is not None:
            figures.append(f"{evidence['audio_seconds']:.1f} speech-audio seconds")
        if evidence["latency_seconds"] is not None:
            figures.append(
                f"{evidence['latency_seconds'] / 3600:.2f} summed call-latency hours (slot-hours; "
                "the seal records no wall-clock GPU-h)"
            )
        return (
            f"CONSUMED (sealed): {', '.join(figures)}; manifest COMPLETED, attempt "
            f"`{evidence['attempt_id']}`"
            + (f" ({evidence['state']})" if evidence["state"] else "")
            + f", sealed {evidence['sealed_at']}Z, study commit {evidence['study_commit']}; the calls / "
            "audio / gpu cells above keep the registered ceilings."
        )
    if kind == "fit":
        return (
            f"CONSUMED (fit receipt present under prepared/{run_id}; paired run "
            f"`{evidence['paired']}` sealed, attempt `{evidence['attempt_id']}`)."
        )
    return (
        f"CONSUMED (model-free read; basis {evidence['basis']}; results note "
        f"`docs/results/{evidence['note']}`)."
    )


def plan(repo_root: Path, data_root: Path, since: str, only: set[str] | None = None):
    text = io.open(repo_root / LEDGER, encoding="utf-8", newline="").read()
    lines = text.split("\n")
    notes = results_notes(repo_root)
    closable = []
    left = []
    for index, cells in iter_open_rows(lines, since):
        run_id = cells[RUN_COL].strip()
        if only is not None and run_id not in only:
            continue
        evidence = classify(data_root, notes, run_id)
        (closable if evidence else left).append((index, cells, run_id, evidence))
    return lines, closable, left


def apply_closures(lines: list[str], closable, today: str) -> None:
    for index, cells, run_id, evidence in closable:
        cells[CONSUMED_COL] = " yes "
        cells[NOTES_COL] = f" {disposition(evidence, run_id, today)} [{STAMP}, {today}]" + cells[NOTES_COL]
        lines[index] = "|".join(cells)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--since", default="2026-10-01", help="earliest row date (YYYY-MM-DD)")
    parser.add_argument("--today", default="2026-10-11")
    parser.add_argument("--run-id", action="append", default=None, help="restrict to these run ids")
    parser.add_argument("--apply", action="store_true", help="write the ledger (default is a dry run)")
    parser.add_argument("--expect-rows", type=int, default=None)
    args = parser.parse_args(argv)
    repo = args.repo_root.resolve()
    data_root = (args.data_root or data_root_default())
    if not (data_root / "runs").is_dir():
        print(f"ledger mark consumed: FAIL: no runs/ under {data_root}", file=sys.stderr)
        return 1
    lines, closable, left = plan(repo, data_root, args.since, set(args.run_id) if args.run_id else None)
    by_kind = {}
    for _, _, _, evidence in closable:
        by_kind[evidence["kind"]] = by_kind.get(evidence["kind"], 0) + 1
    print(
        f"ledger mark consumed: {len(closable)} closable {by_kind}, {len(left)} left at no "
        f"(since {args.since}, {'APPLY' if args.apply else 'DRY RUN'})"
    )
    for _, cells, run_id, evidence in closable:
        print(f"  close {cells[DATE_COL].strip()[:10]} {run_id} [{evidence['kind']}]")
    if args.expect_rows is not None and args.expect_rows != len(closable):
        print(f"ledger mark consumed: FAIL: expected {args.expect_rows} rows, found {len(closable)}", file=sys.stderr)
        return 1
    if args.apply:
        apply_closures(lines, closable, args.today)
        io.open(repo / LEDGER, "w", encoding="utf-8", newline="").write("\n".join(lines))
        print(f"ledger mark consumed: wrote {len(closable)} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
