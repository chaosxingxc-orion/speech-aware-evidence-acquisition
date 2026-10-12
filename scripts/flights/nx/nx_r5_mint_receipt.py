#!/usr/bin/env python3
"""Mint the root-admission decision receipt of NX round R5 (the composed read on DEV-2000-ADDED) on the data root from the
package's draft.

Root's act, never an agent's. Copies ``docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-nx-r5-composed-dev2000-added-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to
overwrite an existing receipt. The FOUR ``eligible_run_ids`` (composed arm, smoke and their FIT identities) and the budget caps are the
draft's and are not edited here.

The replicate's receipt is the MODULE package's own (``scripts/flights/module/module_comp1bdev_mint_receipt.py``): it must be minted too,
or the replicate's launch gate reports ``receipt-missing``.

    python scripts/flights/nx/nx_r5_mint_receipt.py [--coordinator "Fable5.1"] [--dry]

Decision 238 is PROPOSED: mint only after it is ruled and the R1 iteration-2 verdict is on file.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import nx_r5_family as nf  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get(
    "SAEA_STUDY_ROOT",
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition",
)


def rehash(node, root: str) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and os.path.isfile(os.path.join(root, path)):
            node["sha256"] = hashlib.sha256(io.open(os.path.join(root, path), "rb").read()).hexdigest()
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
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    draft_path = f"{nf.PACKAGE}/root-admission-draft-v1.json"
    draft = json.loads(io.open(os.path.join(root, draft_path), encoding="utf-8").read())
    eligible = [nf.ARM["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["run_id"], nf.SMOKE["fit_run_id"]]
    if draft.get("decision_id") != nf.DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {nf.DECISION_ID!r}")
    if draft.get("eligible_run_ids") != eligible:
        raise SystemExit("the draft's eligible_run_ids are not this cell's four run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["minted_from"] = {"template_receipt": draft_path, "tool": "scripts/flights/nx/nx_r5_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, nf.DECISION_RELPATH)
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "decision_id": nf.DECISION_ID, "eligible_run_ids": eligible, "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
