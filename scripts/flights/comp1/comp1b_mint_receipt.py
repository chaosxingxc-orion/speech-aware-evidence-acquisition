#!/usr/bin/env python3
"""Mint cell COMP-1b's root-admission decision receipt on the data root from the package's draft.

The pattern of ``comp1_mint_receipt.py`` (owner decision 198). Root's act, never an agent's. The arm's
``expected_effect_pp`` (4.26) is declared at registration, so the placeholder guard only refuses a
non-numeric declaration. Copies
``docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1/root-admission-draft-v1.json``
to ``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json``,
sets ``status`` to ``decided`` and ``recorded_at_utc`` to now, re-hashes every antecedent
``{"path": ..., "sha256": ...}`` that names a repository file (the flip rewrites the package,
and the receipt must pin the bytes current when it is minted), and refuses to overwrite an
existing receipt. The four ``eligible_run_ids`` and the budget caps are the draft's.

    python scripts/flights/comp1/comp1b_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
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
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1"
DRAFT = PACKAGE + "/root-admission-draft-v1.json"
FACTS = PACKAGE + "/registered-facts-v1.json"
PREREG = PACKAGE + "-preregistration.md"
OUT_DIR = "coordination/slurp-stage3-comp1b-fold-a-v1"
OUT_NAME = "root-admission-v1.json"
DECISION_ID = "slurp-stage3-comp1b-fold-a-admission-v1"
PLACEHOLDER = "TO-BE-DECLARED-BY-COORDINATOR"
ARM_RUN = "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1"
ELIGIBLE = [
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-FIT-V1",
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1",
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-FIT-V1",
]


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
    facts = json.loads(io.open(os.path.join(root, FACTS), encoding="utf-8").read())
    declared = facts["stage3_measurement"][ARM_RUN]["expected_effect_pp"]
    if (isinstance(declared, str) and PLACEHOLDER in declared) or isinstance(declared, bool) or not isinstance(declared, (int, float)):
        raise SystemExit(f"refusing to mint: the arm's expected_effect_pp in {FACTS} is {declared!r}, not a declared number (owner decisions 139 and 152)")
    if PLACEHOLDER in io.open(os.path.join(root, PREREG), encoding="utf-8").read():
        raise SystemExit(f"refusing to mint: {PREREG} still carries the placeholder; declare the same number in its fence")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != ELIGIBLE:
        raise SystemExit("the draft's eligible_run_ids are not the four COMP-1b run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["declared_expected_effect_pp"] = declared
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/comp1/comp1b_mint_receipt.py"}
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
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "decision_id": DECISION_ID,
                      "eligible_run_ids": ELIGIBLE, "declared_expected_effect_pp": declared, "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
