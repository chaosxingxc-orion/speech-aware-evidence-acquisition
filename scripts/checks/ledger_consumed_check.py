#!/usr/bin/env python3
"""Model-free gate: no flown cell may keep ``consumed = no`` in the exposure ledger.

``docs/exposure-ledger.md`` is the register of what each model or tool contact consumed, and
``flight_registration_check.py`` reads ``consumed = yes`` plus a recorded ``COMPLETED`` /
``Verdict:`` disposition as the proof that a cell was flown. A flight that sealed while its rows
still read ``no`` leaves the register understating exposure. This gate reports every such row.

For each table row dated on or after ``--since`` (default 2026-09-27) whose ``consumed`` cell is
exactly ``no``:

* with the data root present (``--data-root`` / ``$SPEECHRL_DATA_DIR``): a finding when the run id
  has a sealed attempt (manifest ``COMPLETED``), when a FIT row's paired run is sealed and its FIT
  receipt exists, or when a read row is cited by a results note and its artefacts exist -- the same
  evidence ``scripts/flights/batch/ledger_mark_consumed.py`` closes;
* with the data root absent: a finding when a ``docs/results/`` note carries the run id in a
  paragraph that also says ``sealed`` or ``Verdict:``.

Repair: ``python scripts/flights/batch/ledger_mark_consumed.py --apply``. Reads sealed run
directories read-only; no model, GPU, network or dataset contact.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]
SINCE_DEFAULT = "2026-09-27"


class LedgerConsumedCheckError(Exception):
    pass


def _helper(repo_root: Path):
    batch = repo_root / "scripts" / "flights" / "batch"
    if str(batch) not in sys.path:
        sys.path.insert(0, str(batch))
    import ledger_mark_consumed  # noqa: PLC0415

    return ledger_mark_consumed


def _paragraph_evidence(notes: dict[str, str], run_id: str) -> str | None:
    for name, text in notes.items():
        for paragraph in re.split(r"\n\s*\n", text):
            if run_id in paragraph and re.search(r"\bsealed\b|Verdict:", paragraph, re.IGNORECASE):
                return name
    return None


def evaluate(repo_root: Path, data_root: Path | None, since: str = SINCE_DEFAULT) -> dict:
    helper = _helper(repo_root)
    ledger = repo_root / helper.LEDGER
    if not ledger.is_file():
        raise LedgerConsumedCheckError(f"missing {helper.LEDGER}")
    lines = io.open(ledger, encoding="utf-8", newline="").read().split("\n")
    notes = helper.results_notes(repo_root)
    mode = "data-root" if data_root is not None and (data_root / "runs").is_dir() else "results-notes"
    findings: list[dict] = []
    open_rows = 0
    for _index, cells in helper.iter_open_rows(lines, since):
        open_rows += 1
        run_id = cells[helper.RUN_COL].strip()
        if mode == "data-root":
            evidence = helper.classify(data_root, notes, run_id)
            basis = evidence["kind"] if evidence else None
        else:
            note = _paragraph_evidence(notes, run_id)
            basis = f"results note {note}" if note else None
        if basis:
            findings.append({"run_id": run_id, "date": cells[helper.DATE_COL].strip()[:10], "basis": basis})
    return {"mode": mode, "since": since, "open_rows": open_rows, "findings": findings, "passed": not findings}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # pragma: no cover
                pass
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--since", default=SINCE_DEFAULT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    env = os.environ.get("SPEECHRL_DATA_DIR")
    data_root = args.data_root or (Path(env) if env else None)
    if data_root is None:
        helper = _helper(args.repo_root.resolve())
        fallback = Path(helper.DEFAULT_DATA_ROOT)
        data_root = fallback if fallback.is_dir() else None
    try:
        data = evaluate(args.repo_root.resolve(), data_root, args.since)
    except LedgerConsumedCheckError as exc:
        print(f"ledger consumed check: FAIL: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0 if data["passed"] else 1
    # The results-notes fallback (data root absent, e.g. a Windows run) only knows that a note MENTIONS the run id near
    # "sealed" / "Verdict:"; it cannot see the manifest, so its findings are advisory. The data-root mode is the gate.
    severity = "FAIL" if data["mode"] == "data-root" else "ADVISORY"
    for finding in data["findings"]:
        print(f"ledger consumed check: {severity}: {finding['date']} {finding['run_id']} is sealed ({finding['basis']}) but consumed = no")
    if data["findings"]:
        print(
            f"ledger consumed check: {severity} ({len(data['findings'])} row(s) in {data['mode']} mode; "
            "repair with ledger_mark_consumed.py --apply, or re-run with the data root present)"
        )
        return 1 if severity == "FAIL" else 0
    print(
        f"ledger consumed check: PASS ({data['open_rows']} open row(s) since {data['since']} checked "
        f"against {data['mode']}, 0 sealed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
