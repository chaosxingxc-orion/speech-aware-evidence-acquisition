"""Append the P-EMB-3L FLOWN note to its exposure-ledger row's NOTES cell.

Surgical and fail-closed by design:

  * reads and writes the ledger with an EXPLICIT utf-8 encoding (this machine's
    Python defaults to GBK, which would mangle every non-ASCII character in the
    file's other rows);
  * touches EXACTLY ONE line -- the single row whose run-id cell is
    ``SAEA-PROBE-pemb3l-234`` -- and refuses if that row is not found exactly
    once, or if the note is already present (idempotence);
  * appends to the NOTES cell only. The CONSUMED cell is asserted to be ``no``
    both before and after: this is a FLIGHT note, and consumed stays ``no``
    until the separately-registered one-shot read executes;
  * asserts the row's cell COUNT is unchanged, so a stray ``|`` inside the note
    can never silently split the row into a different shape.

Usage: update_ledger.py <ledger-path> <note-file>
"""

from __future__ import annotations

import sys
from pathlib import Path

RUN_ID = "SAEA-PROBE-pemb3l-234"
FLOWN_MARKER = "**FLOWN 2026-08-20**"


def main() -> int:
    ledger_path = Path(sys.argv[1])
    note = Path(sys.argv[2]).read_text(encoding="utf-8").strip()

    if "|" in note:
        raise SystemExit("refusing: the note contains a '|', which would split the ledger row")
    if FLOWN_MARKER not in note:
        raise SystemExit(f"refusing: the note does not carry the {FLOWN_MARKER!r} marker")

    text = ledger_path.read_text(encoding="utf-8")
    lines = text.split("\n")

    matches = [i for i, line in enumerate(lines) if f"| {RUN_ID} |" in line]
    if len(matches) != 1:
        raise SystemExit(f"refusing: expected exactly 1 row for {RUN_ID}, found {len(matches)}")
    index = matches[0]
    row = lines[index]

    if FLOWN_MARKER in row:
        raise SystemExit(f"refusing: {RUN_ID} row already carries {FLOWN_MARKER} (idempotence)")

    cells = row.split("|")
    n_cells_before = len(cells)

    # The NOTES cell is the last non-empty cell (the row ends with a trailing
    # '|', so cells[-1] is the empty string after it).
    # Verified against the live row before this script was written: 17 cells,
    # notes at index 15 (len-2, the last cell before the trailing '|'), and
    # consumed six cells earlier at index 9 -- the intervening cells are
    # calls, speech-audio-seconds, gpu-hours, the leakage note and the
    # artifacts cell.
    notes_index = len(cells) - 2
    consumed_index = notes_index - 6
    if len(cells) != 17:
        raise SystemExit(f"refusing: expected a 17-cell row, found {len(cells)}")

    consumed_before = cells[consumed_index].strip()
    if consumed_before.lower() != "no":
        raise SystemExit(
            f"refusing: consumed cell is {consumed_before!r}, expected 'no' -- this is a FLIGHT "
            "note and must not touch a consumed row"
        )

    cells[notes_index] = f"{cells[notes_index].rstrip()} {note} "
    new_row = "|".join(cells)

    if len(new_row.split("|")) != n_cells_before:
        raise SystemExit("refusing: cell count changed")
    new_cells = new_row.split("|")
    if new_cells[consumed_index].strip().lower() != "no":
        raise SystemExit("refusing: consumed cell changed")
    for i, (before, after) in enumerate(zip(cells, new_cells)):
        if i != notes_index and before != after:
            raise SystemExit(f"refusing: cell {i} changed unexpectedly")

    lines[index] = new_row
    ledger_path.write_text("\n".join(lines), encoding="utf-8", newline="")

    print(f"ledger row {index} updated ({n_cells_before} cells, unchanged)")
    print(f"  consumed cell: {new_cells[consumed_index].strip()!r} (unchanged, still 'no')")
    print(f"  notes cell grew from {len(cells[notes_index]) - len(note) - 1} to {len(new_cells[notes_index])} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
