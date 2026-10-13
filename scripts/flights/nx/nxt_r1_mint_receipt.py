#!/usr/bin/env python3
"""Mint the root-admission decision receipt of NX-T R1 (the per-node thinking-policy column) on the data root from the package's draft.

Root's act, never an agent's. The 268-B minting logic (``thinking_system_mint_receipt.mint``) with the NX-T R1 family: copies
``docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-nxt-r1-thinking-policy-fold-b-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and ``recorded_at_utc`` to
now, re-hashes every antecedent that names a repository file, and refuses to overwrite an existing receipt. The ``eligible_run_ids`` (the smoke and the
column flight, each with its FIT identity, in chain order) and the budget caps are the draft's and are not edited here.

    python scripts/flights/nx/nxt_r1_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "direct"))

import nxt_r1_family as fam  # noqa: E402
import thinking_system_mint_receipt as base  # noqa: E402

TOOL = "scripts/flights/nx/nxt_r1_mint_receipt.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = base.ROOT.rstrip("/")
    summary = base.mint(root, base.DATA, args.coordinator, args.dry, family=fam, tool=TOOL)
    if args.dry:
        print(summary.pop("text"))
        print(f"(dry) would write {summary['out']}; re-hashed {summary['rehashed_paths']} antecedent path(s)")
        return 0
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
