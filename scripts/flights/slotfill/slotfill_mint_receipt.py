#!/usr/bin/env python3
"""Mint the SLOTFILL family's root-admission decision receipt on the data root from the package's draft.

Root's act, never an agent's. Copies
``docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json``, sets
``status`` to ``decided`` and ``recorded_at_utc`` to now, re-hashes every antecedent
``{"path": ..., "sha256": ...}`` that names a repository file (the draft's hashes are those of the
package as registered; the flip rewrites the package, and the receipt must pin the bytes that are
current when it is minted), and refuses to overwrite an existing receipt. The SIX
``eligible_run_ids`` and the budget caps are the draft's and are not edited here: change them in
the draft, in the package, and re-run. ``--drop-aa`` removes the A/A pair from the eligible ids
for the case where the round shares one A/A across its base items (the campaign plan and the package
must already say so).

    python scripts/flights/slotfill/slotfill_mint_receipt.py [--coordinator "Fable5.1"] [--dry] [--drop-aa]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get(
    "SAEA_STUDY_ROOT",
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition",
)
DRAFT = "docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1/root-admission-draft-v1.json"
OUT_DIR = "coordination/slurp-stage3-slotfill-fold-a-v1"
OUT_NAME = "root-admission-v1.json"
DECISION_ID = "slurp-stage3-slotfill-fold-a-admission-v1"
ELIGIBLE = [
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1",
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-FIT-V1",
    "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1",
    "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-FIT-V1",
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1",
    "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-FIT-V1",
]
AA_IDS = {"SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1", "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-FIT-V1"}


def rehash(node, root: str) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and os.path.isfile(os.path.join(root, path)):
            node["sha256"] = hashlib.sha256(
                io.open(os.path.join(root, path), "rb").read()
            ).hexdigest()
            count += 1
        for value in node.values():
            count += rehash(value, root)
    elif isinstance(node, list):
        for value in node:
            count += rehash(value, root)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    parser.add_argument("--drop-aa", action="store_true", help="round 3 shares one A/A: mint without the SLOTFILL A/A pair")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != ELIGIBLE:
        raise SystemExit("the draft's eligible_run_ids are not the six SLOTFILL run ids")
    receipt = json.loads(json.dumps(draft))
    if args.drop_aa:
        receipt["eligible_run_ids"] = [run for run in ELIGIBLE if run not in AA_IDS]
        receipt["aa_dropped_note"] = "round 3 shares one in-chain A/A across its items; the SLOTFILL A/A pair is not eligible under this receipt"
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/slotfill/slotfill_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out_dir = os.path.join(DATA, OUT_DIR)
    out = os.path.join(out_dir, OUT_NAME)
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(out_dir, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({
        "written": out,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "decision_id": DECISION_ID,
        "eligible_run_ids": receipt["eligible_run_ids"],
        "rehashed_paths": rehashed,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
