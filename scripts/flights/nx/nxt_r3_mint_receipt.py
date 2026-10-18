#!/usr/bin/env python3
"""Mint the root-admission decision receipt of NX-T R3 (the Solver instruction-template column) on the data root from the package's draft.

Root's act, never an agent's. The 268-B minting logic (``thinking_system_mint_receipt.mint``) with the NX-T R3 family: copies
``docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-nxt-r3-solver-template-fold-b-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and ``recorded_at_utc`` to
now, re-hashes every antecedent that names a repository file, and refuses to overwrite an existing receipt. The ``eligible_run_ids`` (the smoke and the
column flight, each with its FIT identity, in chain order) and the budget caps are the draft's and are not edited here.

    python scripts/flights/nx/nxt_r3_mint_receipt.py [--coordinator "Fable5.1"] [--dry] [--supersede]

RECOVERY rec1 / rec2: the draft carries the recovery block, the new plan sha256 and the predecessor snapshots as antecedents, and ``eligible_run_ids`` gains the
FIT run id of each recovery. ``--supersede`` renames the existing first-registration receipt to ``root-admission-v1.json.superseded-<UTC>-by-rec1.bak`` (never deleted; restored
if the mint is refused) after proving its run ids are a strict prefix of the rec1 list.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "direct"))

import nxt_r3_family as fam  # noqa: E402
import thinking_system_mint_receipt as base  # noqa: E402

TOOL = "scripts/flights/nx/nxt_r3_mint_receipt.py"


def check_supersedable(out: str) -> list[str]:
    """The existing receipt's eligible run ids, after proving it is the first-registration receipt of THIS decision: same decision id, and its run ids are a
    strict prefix of the rec1 list (the recovery only appends the rec1 FIT run id)."""

    old = json.loads(Path(out).read_text(encoding="utf-8"))
    if old.get("decision_id") != fam.DECISION_ID:
        raise SystemExit(f"the existing receipt is decision {old.get('decision_id')!r}, expected {fam.DECISION_ID!r}")
    old_ids, new_ids = list(old.get("eligible_run_ids") or []), fam.eligible_run_ids()
    if not old_ids or len(new_ids) <= len(old_ids) or new_ids[:len(old_ids)] != old_ids:
        raise SystemExit("the existing receipt's eligible_run_ids are not a strict prefix of the rec1 list; refusing to supersede it")
    return old_ids


def backup_name(out: str, now: datetime) -> str:
    return f"{out}.superseded-{now.strftime('%Y%m%dT%H%M%SZ')}-by-rec1.bak"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    parser.add_argument("--supersede", action="store_true",
                        help="the recovery re-mint: rename the existing first-registration receipt to a dated backup (never deleted), then mint the rec1 receipt")
    args = parser.parse_args()
    root = base.ROOT.rstrip("/")
    out = os.path.join(base.DATA, fam.DECISION_RELPATH)
    now = datetime.now(timezone.utc)
    backup = None
    if os.path.exists(out):
        if not args.supersede and not args.dry:
            raise SystemExit(f"refusing to overwrite an existing receipt: {out} (a recovery re-mint passes --supersede)")
        if args.supersede:
            check_supersedable(out)
            backup = backup_name(out, now)
    if backup and not args.dry:
        os.rename(out, backup)
    try:
        summary = base.mint(root, base.DATA, args.coordinator, args.dry, now=now, family=fam, tool=TOOL)
    except BaseException:
        if backup and not args.dry and os.path.exists(backup) and not os.path.exists(out):
            os.rename(backup, out)                      # a refused mint leaves the first-registration receipt exactly where it was
        raise
    if backup:
        summary["superseded_receipt_backup"] = backup
    if args.dry:
        print(summary.pop("text"))
        print(f"(dry) would write {summary['out']}; re-hashed {summary['rehashed_paths']} antecedent path(s)"
              + (f"; would first rename the existing receipt to {backup}" if backup else ""))
        return 0
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
