#!/usr/bin/env python3
"""CLI: Stage-3 S3-6, the stage3-deltas store's derangement TWIN (the form
control for the delta-cell read, docs/superpowers/specs/2026-09-22-stage3-
tfrl-base-loop-engineering.md section S3-6; the same twin idiom as B1's
``scripts/build_slurp_exemplar_twin_vectors.py`` and IDXT's
``docs/readiness/2026-09-20-slurp-b1-index-twin-v1/``).

MODEL-FREE. Zero frozen-core, tool, embedding, GPU or network contacts:
every byte read and written is a permutation of an already-curated authored-
deltas document (S3-5's own ``--out-authored`` output).

What the twin is
-----------------
A delta's CONTENT (statement text, task_target, prior_score, provenance)
stays byte-identical; only its ``associated_facet_ids`` -- which candidate
intents the row router may attach it to -- is reassigned from ANOTHER row's
by a seeded derangement (Sattolo's algorithm: a single n-cycle over the row
order, so no delta keeps its own facet ids and every row of two or more has
zero fixed points by construction). This answers exactly the question the
B1/IDXT twins answer: does it matter that a delta is attached to the RIGHT
target, or would ANY delta of the store move the number by the same amount.

Refuses (fail-closed) a document with fewer than two rows: a derangement of
one element does not exist.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Mapping, MutableMapping, Sequence

REPO_SRC = Path(__file__).resolve().parent.parent / "src"
if str(REPO_SRC) not in sys.path:
    sys.path.insert(0, str(REPO_SRC))

from speech_aware_evidence_acquisition.rails.hashing import (  # noqa: E402
    canonical_json_bytes,
)

AUTHORED_SCHEMA = "saea-stage3-authored-deltas-v1"


class Stage3DeltaTwinError(RuntimeError):
    """The authored-deltas document cannot be deranged as given."""


def _sattolo_cycle(n: int, *, seed: int) -> list[int]:
    """A single n-cycle permutation of ``range(n)`` (Sattolo's algorithm):
    zero fixed points for any n >= 2."""

    if n < 2:
        raise Stage3DeltaTwinError("a derangement requires at least two rows")
    order = list(range(n))
    rng = random.Random(seed)
    for i in range(n - 1, 0, -1):
        j = rng.randrange(0, i)
        order[i], order[j] = order[j], order[i]
    return order


def derange_facet_assignment(
    rows: Sequence[Mapping[str, object]], *, seed: int
) -> list[dict[str, object]]:
    """Reassign every row's ``associated_facet_ids`` from a DIFFERENT row's,
    by a seeded Sattolo derangement over the row order. Every other field is
    copied byte-identical (deep-equal on read-back)."""

    order = _sattolo_cycle(len(rows), seed=seed)
    twinned: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        donor = rows[order[index]]
        new_row: MutableMapping[str, object] = dict(row)
        new_row["associated_facet_ids"] = list(donor["associated_facet_ids"])
        twinned.append(dict(new_row))
    return twinned


def build_twin_document(
    document: Mapping[str, object], *, seed: int
) -> dict[str, object]:
    if document.get("schema") != AUTHORED_SCHEMA:
        raise Stage3DeltaTwinError(f"expected schema {AUTHORED_SCHEMA!r}")
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise Stage3DeltaTwinError("authored document has no rows")
    twinned_rows = derange_facet_assignment(rows, seed=seed)
    fixed_points = sum(
        1
        for original, twin in zip(rows, twinned_rows)
        if set(original["associated_facet_ids"]) == set(twin["associated_facet_ids"])
    )
    if fixed_points:
        raise Stage3DeltaTwinError(
            f"derangement produced {fixed_points} fixed point(s); refusing a twin "
            "that is not a genuine derangement"
        )
    return {
        "schema": AUTHORED_SCHEMA,
        "iteration": document.get("iteration"),
        "twin_of_seed": seed,
        "rows": twinned_rows,
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authored", required=True, type=Path)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    document = json.loads(args.authored.read_text(encoding="utf-8"))
    twin = build_twin_document(document, seed=args.seed)
    raw = canonical_json_bytes(twin)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(raw)
    import hashlib

    report = {
        "schema": "saea-stage3-delta-twin-report-v1",
        "seed": args.seed,
        "row_count": len(twin["rows"]),
        "out": {"relpath": str(args.out), "sha256": hashlib.sha256(raw).hexdigest()},
    }
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts/hashes only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
