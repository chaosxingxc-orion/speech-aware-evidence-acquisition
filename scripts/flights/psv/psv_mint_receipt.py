#!/usr/bin/env python3
"""Mint the root-admission decision receipt of P-SV-1, P-SV-2 or P-SV-3 (owner decisions 184, 186, 188) on the
data root from the package's draft. ``cell`` is any key in ``psv_family.CELLS`` (today psv1, psv2, psv3, psv4; P-SV-4's package is dated 2026-09-30,
resolved through ``psv_family.names``).

Root's act, never an agent's. Copies
``docs/readiness/2026-09-29-slurp-stage3-psvK-fold-b-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-psvK-fold-b-v1/root-admission-v1.json``, sets ``status`` to
``decided`` and ``recorded_at_utc`` to now, re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names
a repository file, and refuses to overwrite an existing receipt. The FOUR ``eligible_run_ids`` (arm, smoke and
their FIT identities) and the budget caps are the draft's and are not edited here. No A/A cell: the twin branch
flies inside every row.

P-SV-1 is REFUSED while its registered facts still carry the contrast-pair placeholder pin
(``TO-BE-PINNED-AFTER-CONTRAST-PAIR-BUILD``): the top2-contrast-v1 branch has nothing to render from.

    python scripts/flights/psv/psv_mint_receipt.py psv1|psv2|psv3|psv4 [--coordinator "Fable5.1"] [--dry]
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

import psv_family as ff  # noqa: E402

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
    parser.add_argument("cell", choices=sorted(ff.CELLS))
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    arm, smoke = ff.names(args.cell, "arm"), ff.names(args.cell, "smoke")
    draft_path = f"{arm['package']}/root-admission-draft-v1.json"
    facts = json.loads(io.open(os.path.join(root, arm["package"], "registered-facts-v1.json"), encoding="utf-8").read())
    if ff.CONTRAST_PAIR_PLACEHOLDER in json.dumps(facts):
        raise SystemExit(f"refusing: {ff.CELLS[args.cell]['label']} still carries the placeholder pin "
                         f"{ff.CONTRAST_PAIR_PLACEHOLDER}; build and pin the contrast-pair table first")
    draft = json.loads(io.open(os.path.join(root, draft_path), encoding="utf-8").read())
    eligible = [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]
    if draft.get("decision_id") != arm["decision_id"]:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {arm['decision_id']!r}")
    if draft.get("eligible_run_ids") != eligible:
        raise SystemExit("the draft's eligible_run_ids are not this cell's four run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["minted_from"] = {"template_receipt": draft_path, "tool": "scripts/flights/psv/psv_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, arm["decision_relpath"])
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
                      "decision_id": arm["decision_id"], "eligible_run_ids": eligible,
                      "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
