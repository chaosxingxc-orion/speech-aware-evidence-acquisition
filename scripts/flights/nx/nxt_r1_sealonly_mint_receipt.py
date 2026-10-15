#!/usr/bin/env python3
"""Mint the NX-T R1 SEAL-ONLY completion decision receipt on the data root from the package's draft.

Root's act, taken only after root has countersigned the seal-only clauses (``countersign-row-texts-v1.json``). Copies
``docs/readiness/<date>-slurp-nxt-r1-thinking-policy-fold-b-v1-sealonly-v1/root-admission-sealonly-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-nxt-r1-thinking-policy-fold-b-v1/root-admission-sealonly-v1.json`` (beside the column's own receipt, which is NOT touched):

* decision id ``slurp-nxt-r1-thinking-policy-fold-b-sealonly-admission-v1``; status ``decided``; recorded now;
* eligible run ids the arm and its rec1 FIT identity only (nothing is flown, so no dry run); eligible attempt the seal-only attempt only; the FIT attempt id the fresh
  seal-only one (all checked against the draft and the family);
* ``resume_from`` checked against the committed experiment config AND against the stopped attempt's trace on the data root (re-hashed; refused when it moved);
* ``resume_replay_proof`` re-read from the package's generation plan (refused unless every complete row was checked, none failing, none sealed twice);
* every repository antecedent ``{"path", "sha256"}`` re-hashed to the bytes current at minting.

Refuses to overwrite an existing receipt. Writes nothing with ``--dry``.

    python scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nxt_r1_family as fam  # noqa: E402

SPEC = fam.sealonly_spec()
DATA = os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"
ROOT = os.environ.get("SAEA_STUDY_ROOT", str(fam.REPO_ROOT))
PACKAGE = SPEC["package"]
DRAFT = PACKAGE + "/root-admission-sealonly-draft-v1.json"
EXPERIMENT = f"configs/experiment/{SPEC['experiment']}.json"
OUT_RELPATH = SPEC["decision_relpath"]
DECISION_ID, RUN, FIT_RUN, SO, FSO = SPEC["decision_id"], SPEC["run"], SPEC["fit_run"], SPEC["attempt"], SPEC["fit_attempt"]
PRED = SPEC["predecessor_attempt"]
TOOL = "scripts/flights/nx/nxt_r1_sealonly_mint_receipt.py"


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


def _sha_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(root: str, data: str) -> tuple[dict, dict, dict]:
    """Refuse (SystemExit) unless the draft, the committed cell, the plan and the data root agree. Returns ``(draft, plan, resume_from)``."""

    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != [RUN, FIT_RUN] or draft.get("eligible_attempt_ids") != [SO]:
        raise SystemExit("the draft's eligible run / attempt ids are not the seal-only completion's")
    if draft.get("fit_attempt_ids") != {FIT_RUN: FSO}:
        raise SystemExit("the draft's FIT attempt id is not the registered one")
    cell = json.loads(io.open(os.path.join(root, EXPERIMENT), encoding="utf-8").read())["cells"][0]
    resume_from = cell.get("resume_from")
    if cell.get("attempt_id") != SO or not isinstance(resume_from, dict) or resume_from.get("attempt_id") != PRED or set(resume_from) != {"attempt_id", "trace_sha256"}:
        raise SystemExit("refusing to mint: the committed seal-only cell does not declare the seal-only attempt and a mode-A resume_from the stopped attempt")
    if draft.get("resume_from") != resume_from:
        raise SystemExit("the draft's resume_from is not the committed cell's")
    plan = json.loads(io.open(os.path.join(root, PACKAGE, "generation-plan-registered-v1.json"), encoding="utf-8").read())
    proof = plan.get("resume_replay_proof") or {}
    rows = (plan.get("roster") or {}).get("rows")
    if not isinstance(rows, int) or (proof.get("rows_checked"), proof.get("rows_failing"), proof.get("sealed_twice"), proof.get("union_complete_rows")) != (rows, 0, 0, rows):
        raise SystemExit(f"refusing to mint: the registered resume_replay_proof is not {rows} checked / 0 failing / 0 sealed twice "
                         f"({proof.get('rows_checked')} / {proof.get('rows_failing')} / {proof.get('sealed_twice')})")
    if os.path.isdir(data):
        trace = os.path.join(data, "runs", RUN, PRED, f"{RUN}.trace.jsonl")
        if not os.path.isfile(trace) or _sha_file(trace) != resume_from["trace_sha256"]:
            raise SystemExit("refusing to mint: the stopped attempt's trace is missing or no longer hashes to the registered resume_from")
    return draft, plan, resume_from


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    draft, plan, _resume_from = check(root, DATA)
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["resume_replay_proof"] = plan["resume_replay_proof"]
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": TOOL}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, OUT_RELPATH)
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "decision_id": DECISION_ID,
                      "eligible_run_ids": receipt["eligible_run_ids"], "eligible_attempt_ids": receipt["eligible_attempt_ids"], "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
