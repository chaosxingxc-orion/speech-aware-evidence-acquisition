#!/usr/bin/env python3
"""build_population_counts.py -- the {stratum: population_count} counts a floored roster's
post-stratified weighting needs, extracted straight from a committed roster receipt's own
``per_intent`` table (owner, 2026-09-29: never by reading the test split).

WHY. ``docs/receipts/rosters/slurp-test-sample-3010-v1.json`` stratifies SLURP-TEST-SAMPLE-3010-V1
by gold intent with a floor (5 prompts) per intent, so the sample's own per-intent row counts are
NOT proportional to the full test split's per-intent counts -- the raw roster mean over-weights a
small intent that the floor inflated. The receipt already carries the full test split's per-intent
population counts, in its own committed ``per_intent`` table (never opened from ``test.jsonl``):
``per_intent[<intent>].test_recordings`` / ``.test_utterances``, recomputed and pinned when the
roster was frozen. This script is a straight, model-free, gold-free extraction of that table into
the flat ``{stratum: population_count}`` shape ``stage3_paired_read.py --population-counts`` reads
(``scripts.analysis.stage3_paired_read._load_population_weights``): it opens ONE committed receipt,
copies ONE already-computed integer field per intent, and writes the result with a sha256 for the
audit trail. It reads no audio, no gold label string, and no test split file.

The output covers every intent the roster receipt's ``per_intent`` table names (SLURP: 59, the full
test split's intent set), not only the strata a particular sub-roster (a sample, a closure) happens
to have rows for -- the READ driver itself drops and renormalises over whichever subset the roster
it is applied to actually carries (``general_greet`` is absent from SLURP-TEST-SAMPLE-3010-V1: decision
141's one-prompt intent went to the closure roster whole), so one counts file is reusable across a
sample and its sibling closure roster without regenerating it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

SCHEMA = "saea-population-counts-v1"
COUNT_FIELDS = ("test_recordings", "test_utterances")

_REPO = Path(__file__).resolve().parents[2]


class PopulationCountsError(RuntimeError):
    """The named roster receipt does not carry what this extraction needs."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(roster_path: Path, *, count_field: str, roster_relpath: str) -> dict[str, Any]:
    if count_field not in COUNT_FIELDS:
        raise PopulationCountsError(f"--count-field must be one of {COUNT_FIELDS}, not {count_field!r}")
    if not roster_path.is_file():
        raise PopulationCountsError(f"{roster_path} is not a file")
    document = json.loads(roster_path.read_text(encoding="utf-8"))
    per_intent = document.get("per_intent")
    if not isinstance(per_intent, Mapping) or not per_intent:
        raise PopulationCountsError(
            f"{roster_path}: no per_intent table (per-stratum full-test population counts) to read"
        )
    counts: dict[str, int] = {}
    for stratum in sorted(per_intent):
        row = per_intent[stratum]
        if not isinstance(row, Mapping) or count_field not in row:
            raise PopulationCountsError(f"{roster_path}: per_intent[{stratum!r}] carries no {count_field!r}")
        value = row[count_field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise PopulationCountsError(
                f"{roster_path}: per_intent[{stratum!r}][{count_field!r}] must be a nonnegative integer"
            )
        counts[stratum] = value
    return {
        "schema": SCHEMA,
        "source_roster_receipt": {
            "relpath": roster_relpath,
            "sha256": _sha256(roster_path),
            "roster_id": document.get("roster_id"),
            "split_identity_hash": document.get("split_identity_hash"),
        },
        "count_field": count_field,
        "strata_definition": document.get("strata_definition"),
        "population_counts": counts,
        "population_total": sum(counts.values()),
        "strata_count": len(counts),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--roster", required=True, help="repo-relative roster receipt path")
    parser.add_argument("--repo-root", default=str(_REPO))
    parser.add_argument(
        "--count-field", default="test_recordings", choices=COUNT_FIELDS,
        help="which per_intent field is the population count (default: test_recordings, matching "
             "a roster whose rows are recordings)",
    )
    parser.add_argument("--out", required=True, help="where to write the population-counts JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = Path(args.repo_root)
    roster_relpath = args.roster
    roster_path = Path(roster_relpath)
    if not roster_path.is_absolute():
        roster_path = repo_root / roster_path
    try:
        document = build(roster_path, count_field=args.count_field, roster_relpath=roster_relpath)
    except PopulationCountsError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, indent=2, sort_keys=True) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    sha = _sha256(out_path)
    print(json.dumps({
        "written": str(out_path),
        "sha256": sha,
        "strata_count": document["strata_count"],
        "population_total": document["population_total"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
