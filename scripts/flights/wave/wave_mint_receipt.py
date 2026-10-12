#!/usr/bin/env python3
"""Mint the knowledge wave's shared A/A root-admission decision receipt on the data root from its draft.

Root's act, never an agent's, and ONLY after the A/A's byte-identity proof reads ``IDENTICAL``
(``docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1/shared-aa-proof-v1.json``, written by
``scripts/flights/wave/wave_shared_aa_proof.py``): decision 164 reads the wave arms at "ONE shared
in-chain A/A of the AGREE arm's own bytes", and a receipt for an A/A not proven to be those bytes
would authorise the wrong instrument. Copies the package's ``root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-wave1-aa-fold-a-v1/root-admission-v1.json``, sets
``status`` to ``decided`` and ``recorded_at_utc`` to now, re-hashes every antecedent
``{"path": ..., "sha256": ...}`` that names a repository file (the flip rewrites the package, and
the receipt must pin the bytes current when it is minted), and refuses to overwrite an existing
receipt. The TWO eligible run ids are the A/A's generation run and its FIT spend identity:

    SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1
    SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1

The wave arms' own receipts are minted by their own scripts (``scripts/flights/w1/w1_mint_receipt.py``,
``scripts/flights/w3/w3_mint_receipt.py``, ``scripts/flights/w4/w4_mint_receipt.py``).

    python scripts/flights/wave/wave_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
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
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1"
DRAFT = PACKAGE + "/root-admission-draft-v1.json"
PROOF = PACKAGE + "/shared-aa-proof-v1.json"
OUT_DIR = "coordination/slurp-stage3-wave1-aa-fold-a-v1"
OUT_NAME = "root-admission-v1.json"
DECISION_ID = "slurp-stage3-wave1-aa-fold-a-admission-v1"
ELIGIBLE = [
    "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
    "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1",
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
    proof_path = os.path.join(root, PROOF)
    if not os.path.isfile(proof_path):
        raise SystemExit(f"refusing to mint: {PROOF} is missing (scripts/flights/wave/wave_shared_aa_proof.py)")
    verdict = json.loads(io.open(proof_path, encoding="utf-8").read()).get("verdict")
    if verdict != "IDENTICAL":
        raise SystemExit(f"refusing to mint: the shared A/A proof reads {verdict!r}, not IDENTICAL (owner decision 164)")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != ELIGIBLE:
        raise SystemExit("the draft's eligible_run_ids are not the two wave A/A run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["shared_aa_proof_verdict"] = verdict
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/wave/wave_mint_receipt.py"}
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
                      "eligible_run_ids": ELIGIBLE, "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
