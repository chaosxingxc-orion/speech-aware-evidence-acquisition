#!/usr/bin/env python3
"""CLI: freeze the SLURP per-intent TRAIN slot schema receipt (program
prerequisite MF-3; authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` section 3
and ``docs/readiness/2026-09-05-slurp-use2-slot-stage-v1-preregistration.md``).

MODEL-FREE and TRAIN-ONLY: ``data.slurp.load_slurp_intent_slot_schema`` opens
the governed ``train.jsonl`` and nothing else, and this script opens no other
file. Deterministic: an unchanged TRAIN corpus gives byte-identical receipt
bytes at ``docs/receipts/knowledge/slurp-intent-slot-schema-v1.json``.

Usage::

    python scripts/build_slurp_intent_slot_schema.py [--lock PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_intent_slot_schema,
    slurp_intent_slot_schema_receipt,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

GENERATOR = "scripts/build_slurp_intent_slot_schema.py"
RECEIPT_RELPATH = "docs/receipts/knowledge/slurp-intent-slot-schema-v1.json"


def write_slurp_intent_slot_schema_receipt(
    path: Path, lock, root: Path
) -> tuple[str, dict]:
    """Build the schema, render its receipt document and write it canonically.
    Returns ``(receipt file sha256, receipt document)``."""

    schema = load_slurp_intent_slot_schema(lock, root)
    document = slurp_intent_slot_schema_receipt(schema, generator=GENERATOR)
    return write_json_artifact(Path(path), document), document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lock",
        type=Path,
        default=None,
        help="umbrella datasets lock path (default: the registered adjacent layout)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / RECEIPT_RELPATH,
        help=f"receipt path (default: {RECEIPT_RELPATH})",
    )
    args = parser.parse_args()
    lock = load_lock(args.lock if args.lock is not None else umbrella_lock_path(REPO_ROOT))
    digest, document = write_slurp_intent_slot_schema_receipt(args.out, lock, data_root())
    print(f"wrote {args.out}  sha256={digest[:16]}...")
    print(f"  content_hash={document['content_hash'][:16]}...")
    print(f"  totals={document['totals']}")
    print(f"  rendered_full_text={document['rendered_full_text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
