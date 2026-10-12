#!/usr/bin/env python3
"""Mint the E4-1 SEAL-ONLY completion decision receipt (owner decision 194) on the data root.

Root's act, never an agent's, and ONLY after the owner has admitted the seal-only completion (decision 194) and root
has countersigned the seal-only DRAFT clauses. Copies
``docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/root-admission-sealonly-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json``:

* decision id ``slurp-stage3-relisten-fold-a-sealonly-admission-v1``; status ``decided``; recorded now;
* eligible run ids the arm and its FIT identity only (nothing is flown, so no dry run); eligible attempt the seal-only
  attempt only; the FIT attempt id the fresh seal-only one (all checked against the draft);
* ``resume_from`` checked against the committed experiment config;
* ``resume_replay_proof`` re-read from the package's generation plan (refused unless 1,080 / 0 / 0);
* every repository antecedent ``{"path", "sha256"}`` re-hashed to the bytes current at minting.

Refuses to overwrite an existing receipt. Writes nothing with ``--dry``.

    python scripts/flights/e4/e4_sealonly_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
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
PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1"
DRAFT = PACKAGE + "/root-admission-sealonly-draft-v1.json"
EXPERIMENT = "configs/experiment/slurp-native-stage3-relisten-fold-a-v1-resume.json"
OUT_DIR = "coordination/slurp-stage3-relisten-fold-a-v1"
OUT_NAME = "root-admission-sealonly-v1.json"
DECISION_ID = "slurp-stage3-relisten-fold-a-sealonly-admission-v1"
RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1"
FIT_RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1"
SO = "attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-relisten-fold-a-fit-v1-seal-only"
RESUME_FROM = {"attempt_id": "attempt-slurp-native-stage3-relisten-fold-a-generation-v1",
               "trace_sha256": "966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6"}


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
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != [RUN, FIT_RUN] or draft.get("eligible_attempt_ids") != [SO]:
        raise SystemExit("the draft's eligible run / attempt ids are not the seal-only completion's")
    if draft.get("fit_attempt_ids") != {FIT_RUN: FSO} or draft.get("resume_from") != RESUME_FROM:
        raise SystemExit("the draft's FIT attempt id or resume_from is not the registered one")
    cell = json.loads(io.open(os.path.join(root, EXPERIMENT), encoding="utf-8").read())["cells"][0]
    if cell.get("attempt_id") != SO or cell.get("resume_from") != RESUME_FROM:
        raise SystemExit("refusing to mint: the committed resume cell does not declare the seal-only attempt and its resume_from")
    plan = json.loads(io.open(os.path.join(root, PACKAGE, "generation-plan-registered-v1.json"), encoding="utf-8").read())
    proof = plan.get("resume_replay_proof") or {}
    if (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice")) != (1080, 0, 0):
        raise SystemExit(f"refusing to mint: the registered resume_replay_proof is not 1,080 / 0 / 0 ({proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')})")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["resume_replay_proof"] = proof
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/e4/e4_sealonly_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out_dir = os.path.join(DATA, OUT_DIR)
    out = os.path.join(out_dir, OUT_NAME)
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(out_dir, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "decision_id": DECISION_ID, "eligible_run_ids": receipt["eligible_run_ids"],
                      "eligible_attempt_ids": receipt["eligible_attempt_ids"], "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
