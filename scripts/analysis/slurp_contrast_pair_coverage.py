#!/usr/bin/env python3
"""How much of a Perception-branch's own prepared seed a contrast-pair table actually covers
(same-flight instrument phase 2, merge set C, O7 ruling, docs/superpowers/specs/2026-09-28-
same-flight-instrument-phase2-perception-variants-design.md).

WHAT IT MEASURES. ``scripts/build_slurp_intent_contrast_pairs.py`` mines a table of pairs; whether
the ``top2-contrast-v1`` Perception presentation (``rails.perception_presentations.
_Top2ContrastPresentation``) actually RENDERS anything for a given row depends on whether that
row's own rank-1/rank-2 candidate pair happens to be a key in the table. This script counts that,
row by row, over a branch's already-prepared seed (``rails.native_episode_config``'s
``perception-branch-seeds-v1`` schema: ``output.branches.<branch_id>`` maps each sample id to the
SAME ordered list of qualified boundary value ids -- ``<store>::intent-boundary:<intent_id>`` --
the runner itself would resolve for that branch). For every row it classifies:

  * HIT -- the row's first two DISTINCT candidate intents (in rendered order, exactly what
    ``rails.perception_presentations.branch_supplied_intent_ids`` reads off the row) form an
    unordered pair that IS a key in the table's ``rows`` mapping;
  * NO-TABLE-ROW -- the row names two distinct candidates, but their pair is not a table key
    (below the pool-support floor at mining time, or never considered at all);
  * FEWER-THAN-TWO-INTENTS -- the row's own supply resolves to fewer than two distinct candidate
    intents (nothing to contrast at all) -- the runner's own
    ``TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES`` case, checked before the table is even
    consulted.

It also reports the top ``--top-missing`` NO-TABLE-ROW pairs by row count: the pairs a wider table
would need to cover next.

BOUNDARY. Model-free: zero model, server, encoder, embedder, ASR, scorer, network, GPU and
paid-API contact. Reads only qualified value ids and a pinned pair table's ``intents``/row keys --
never a gold label, an utterance, a cue word, an activation/exclusion sentence or any model output.
Prints intent ids and counts only.

    python scripts/analysis/slurp_contrast_pair_coverage.py --data-root "$SPEECHRL_DATA_DIR" \\
        --seed prepared/SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1/perception-branch-seeds-v1.json \\
        --branch b-top2contrast \\
        --table prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1/table-v1.json
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails.perception_presentations import (  # noqa: E402
    branch_supplied_intent_ids,
)

HIT = "hit"
NO_TABLE_ROW = "no-table-row"
FEWER_THAN_TWO = "fewer-than-two-intents"


class CoverageError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise CoverageError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise CoverageError(f"{path} is not valid JSON: {error}") from error


def table_pairs(table_doc: dict) -> set[frozenset]:
    """The set of unordered intent-id pairs a contrast-pair table's ``rows`` mapping keys on --
    never the sentences or cue words, only the ``intents`` id pair each row names."""

    rows = table_doc.get("rows")
    if not isinstance(rows, dict):
        raise CoverageError("table has no 'rows' mapping")
    pairs: set[frozenset] = set()
    for row_key, row in rows.items():
        intents = row.get("intents") if isinstance(row, dict) else None
        if (
            not isinstance(intents, list) or len(intents) != 2
            or any(not isinstance(item, str) or not item for item in intents)
        ):
            raise CoverageError(f"table row {row_key!r} has a malformed 'intents' field")
        pairs.add(frozenset(intents))
    return pairs


def branch_rows(seed_doc: dict, branch_id: str) -> dict[str, list]:
    branches = seed_doc.get("output", {}).get("branches", {})
    if not isinstance(branches, dict) or branch_id not in branches:
        available = sorted(branches) if isinstance(branches, dict) else []
        raise CoverageError(f"seed has no branch {branch_id!r}; branches present: {available}")
    rows = branches[branch_id]
    if not isinstance(rows, dict):
        raise CoverageError(f"branch {branch_id!r} is not a {{sample_id: [value_id, ...]}} mapping")
    return rows


def classify(rows: dict[str, list], pairs: set[frozenset]) -> dict:
    """Per-row classification counts and the NO-TABLE-ROW pairs, by count."""

    counts: collections.Counter = collections.Counter()
    missing: collections.Counter = collections.Counter()
    for _sample_id, value_ids in rows.items():
        if not isinstance(value_ids, list):
            raise CoverageError("a branch row is not a list of value ids")
        candidates = branch_supplied_intent_ids(value_ids)
        if len(candidates) < 2:
            counts[FEWER_THAN_TWO] += 1
            continue
        key = frozenset(candidates)
        if key in pairs:
            counts[HIT] += 1
        else:
            counts[NO_TABLE_ROW] += 1
            missing[tuple(sorted(key))] += 1
    return {"counts": counts, "missing": missing}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("SPEECHRL_DATA_DIR", "")))
    parser.add_argument(
        "--seed", required=True,
        help="relpath under --data-root of a perception-branch-seeds-v1 prepared artifact",
    )
    parser.add_argument("--branch", default="b-top2contrast", help="branch id under output.branches")
    parser.add_argument("--table", required=True, help="relpath under --data-root of a contrast-pair table-v1.json")
    parser.add_argument("--top-missing", type=int, default=10, help="how many missing pairs to report")
    args = parser.parse_args(argv)
    root: Path = args.data_root
    if not str(root) or not root.is_dir():
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required")

    seed_doc = load_json(root / args.seed)
    rows = branch_rows(seed_doc, args.branch)
    table_doc = load_json(root / args.table)
    pairs = table_pairs(table_doc)

    result = classify(rows, pairs)
    counts, missing = result["counts"], result["missing"]
    total = sum(counts.values())
    top_missing = [
        {"intents": list(pair), "count": count} for pair, count in missing.most_common(args.top_missing)
    ]

    print(json.dumps({
        "seed": args.seed,
        "branch": args.branch,
        "table": args.table,
        "table_artifact_id": table_doc.get("artifact_id"),
        "rows_total": total,
        "rows_hit": counts[HIT],
        "rows_no_table_row": counts[NO_TABLE_ROW],
        "rows_fewer_than_two_intents": counts[FEWER_THAN_TWO],
        "distinct_missing_pairs": len(missing),
        "top_missing_pairs": top_missing,
    }, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CoverageError as error:
        raise SystemExit(f"slurp_contrast_pair_coverage: {error}") from error
