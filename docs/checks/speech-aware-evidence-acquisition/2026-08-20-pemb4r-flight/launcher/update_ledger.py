"""Append the P-EMB-4R FLOWN note to exposure row SAEA-PROBE-pemb4r-4100.

SURGICAL, fail-closed, byte-conservative:

* the file is read and written with EXPLICIT utf-8 and ``newline="\\n"``
  (this machine's default text encoding is GBK -- a wholesale rewrite would
  corrupt the ledger);
* exactly ONE line may carry the anchor ``| SAEA-PROBE-pemb4r-4100 |``;
* the row's cell COUNT must be unchanged after the edit;
* the ``consumed`` cell (column index 8) must read ``no`` BEFORE and must
  still read ``no`` AFTER -- this flight spends the requests, the row is
  consumed only by the separately-registered one-shot read;
* every OTHER line in the file must be byte-identical afterwards, and every
  other cell of the edited row must be byte-identical too. Both are asserted,
  not assumed.

Usage: update_ledger.py --note-file <path> [--check]
       ``--check`` re-verifies an ALREADY-edited ledger without writing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
LEDGER = REPO / "docs/exposure-ledger.md"
RUN_ID = "SAEA-PROBE-pemb4r-4100"
ANCHOR = f"| {RUN_ID} |"
CONSUMED_COLUMN_INDEX = 8


def split_cells(line: str) -> list[str]:
    return line.strip().strip("|").split("|")


def locate(lines: list[str]) -> int:
    matches = [i for i, line in enumerate(lines) if ANCHOR in line]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly 1 ledger row matching {ANCHOR!r}, found {len(matches)}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--note-file", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    note = Path(args.note_file).read_text(encoding="utf-8").strip()
    if not note:
        raise SystemExit("--note-file is empty")
    if "|" in note or "\n" in note:
        raise SystemExit("the note must be a single line and must not contain a pipe (it is one table cell)")

    original = LEDGER.read_text(encoding="utf-8")
    lines = original.split("\n")
    index = locate(lines)
    row = lines[index]
    cells = split_cells(row)
    n_cells = len(cells)
    consumed_before = cells[CONSUMED_COLUMN_INDEX].strip()
    print(f"row line: {index + 1} (1-indexed)")
    print(f"cells: {n_cells}")
    print(f"consumed BEFORE: {consumed_before!r}")
    if consumed_before != "no":
        raise SystemExit(f"consumed cell reads {consumed_before!r}, expected 'no' -- refusing")

    if args.check:
        present = note in cells[-1]
        print(f"note present in the notes cell? {present}")
        print(f"consumed AFTER: {cells[CONSUMED_COLUMN_INDEX].strip()!r}")
        print("LEDGER CHECK OK" if present and consumed_before == "no" else "LEDGER CHECK FAILED")
        return 0 if present else 1

    if note in cells[-1]:
        raise SystemExit("the note is already present in the notes cell -- refusing to duplicate it")

    new_cells = list(cells)
    new_cells[-1] = new_cells[-1].rstrip() + " " + note + " "
    new_row = "|" + "|".join(new_cells) + "|"

    # Fail-closed structural assertions BEFORE writing.
    verify = split_cells(new_row)
    if len(verify) != n_cells:
        raise SystemExit(f"edited row has {len(verify)} cells, expected {n_cells} -- refusing")
    for position, (before, after) in enumerate(zip(cells, verify)):
        if position == len(cells) - 1:
            continue
        if before != after:
            raise SystemExit(f"cell {position} changed ({before!r} -> {after!r}) -- refusing")
    if verify[CONSUMED_COLUMN_INDEX].strip() != "no":
        raise SystemExit("consumed cell would change -- refusing")

    new_lines = list(lines)
    new_lines[index] = new_row
    updated = "\n".join(new_lines)

    # Every other line byte-identical.
    for position, (before, after) in enumerate(zip(lines, new_lines)):
        if position != index and before != after:
            raise SystemExit(f"line {position + 1} changed unexpectedly -- refusing")
    if len(lines) != len(new_lines):
        raise SystemExit("line count changed -- refusing")

    LEDGER.write_text(updated, encoding="utf-8", newline="\n")
    print(f"consumed AFTER: {split_cells(new_row)[CONSUMED_COLUMN_INDEX].strip()!r}")
    print(f"notes cell grew by {len(new_row) - len(row)} bytes")
    print("LEDGER UPDATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
