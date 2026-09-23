#!/usr/bin/env python3
"""CLI: Stage-3 S3-5, the authored-deltas -> RELEASE SOURCE conversion (the
step between curation and registration; ``docs/superpowers/specs/2026-09-22-
stage3-tfrl-base-loop-engineering.md`` sections S3-5 and S3-6).

MODEL-FREE. Zero frozen-core, tool, embedding, encoder, tokenizer, scorer,
GPU and network contacts: it reads one already-curated local JSON document
and writes a permutation-free re-envelope of it plus a two-digest receipt.

Why this step exists
--------------------
``scripts/build_slurp_stage3_delta_store.py`` writes the CURATION document
(schema ``saea-stage3-authored-deltas-v1`` / ``-v2``: ``schema``,
``iteration``, ``rows``, and for a twin ``twin_of_seed``), and
``scripts/build_slurp_stage3_delta_twin.py`` writes a derangement of it in
the same shape. Neither is the shape a release registration may pin:
``core.semantic_knowledge_preparation.prepare_semantic_knowledge_store``
reads its ``authored_source`` through ``_source_rows``, which requires the
shared envelope ``saea-authored-semantic-knowledge-source-v1`` with EXACTLY

    {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}

and cross-checks ``builder_policy_id`` and ``source_split_identity_hash``
against the registration's own. This CLI performs that conversion, and it
is the ONLY difference between the two documents: every row crosses over
verbatim, in its own order, with its exact key set re-validated.

Because the envelope's four keys are checked for exact equality, the
wrapper cannot carry a provenance field of its own. The link back to the
document it was built from is therefore a RECEIPT written beside it
(``saea-stage3-delta-source-wrap-receipt-v1``), pinning the authored
document's SHA-256, the wrapper's SHA-256, the authored schema, the
iteration (and a twin's seed) and the row count. The release registration
pins the WRAPPER; the receipt is what closes the chain back to curation.

The generation store's wrapper is normally written by the curator itself
(``--out-source``, one process with the curation that produced the rows, so
a drift in curation moves the wrapper's digest and the preparer fails
closed on the pin). This CLI is the same conversion for a document the
curator did not write -- above all the derangement TWIN -- and for
re-wrapping an existing document by hand.

Console output is ids, counts and digests only: no statement text, no
utterance text, no gold, ever.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Sequence

#: The conversion itself lives beside the curation it belongs to, so the two
#: can never drift apart; this CLI loads that module by file path (the same
#: idiom this repository's tests use for every ``scripts/`` module -- the
#: scripts directory is not an importable package).
_CURATOR_PATH = Path(__file__).resolve().parent / "build_slurp_stage3_delta_store.py"
_spec = importlib.util.spec_from_file_location(
    "_saea_build_slurp_stage3_delta_store", _CURATOR_PATH
)
_curator = importlib.util.module_from_spec(_spec)
sys.modules.setdefault(_spec.name, _curator)
_spec.loader.exec_module(_curator)  # type: ignore[union-attr]

Stage3DeltaStoreError = _curator.Stage3DeltaStoreError
build_authored_source_document = _curator.build_authored_source_document
default_source_receipt_path = _curator.default_source_receipt_path
write_authored_source = _curator.write_authored_source


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--authored", required=True, type=Path,
        help="the curated (or twinned) authored-deltas document to wrap",
    )
    parser.add_argument(
        "--out", required=True, type=Path,
        help=(
            "the release source document to write, under the DATA root "
            "(a registration's authored_source pin allows no other root)"
        ),
    )
    parser.add_argument(
        "--source-split-identity-hash", required=True,
        help=(
            "the construction population's split identity; must equal the "
            "release registration's own source_split_identity_hash"
        ),
    )
    parser.add_argument(
        "--builder-policy-id", default=None,
        help=(
            "optional cross-check: the builder the registration names. It is "
            "DERIVED from the authored schema, so this only fails closed on a "
            "mismatch and never overrides."
        ),
    )
    parser.add_argument(
        "--receipt", default=None, type=Path,
        help="wrap receipt path (default: <--out stem>-wrap-receipt.json)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = write_authored_source(
        args.authored,
        out_path=args.out,
        source_split_identity_hash=args.source_split_identity_hash,
        builder_policy_id=args.builder_policy_id,
        receipt_path=args.receipt,
    )
    print(json.dumps(report, indent=2, sort_keys=True))  # noqa: T201 -- ids/counts/hashes only
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
