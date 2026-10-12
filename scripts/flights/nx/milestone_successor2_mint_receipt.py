#!/usr/bin/env python3
"""Mint the root-admission decision receipt of the SLURP test-sample SUCCESSOR-2 composed cell (owner decisions 233, 241, 250 A, 251 A)
on the data root from the package's draft.

Root's act, never an agent's. Copies ``docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/root-admission-draft-v1.json``
to ``$SPEECHRL_DATA_DIR/coordination/slurp-milestone-successor2-composed-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, records the conversational first-contact report of the allowance gate (``--report-date``,
``--report-arm``; both required: the allowance names that report in the root countersignature of the first consumed row),
re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to overwrite an existing
receipt. It refuses first on every refusal of ``milestone_successor2_preflip_check.py``. The TWO ``eligible_run_ids`` (the read run id
and its FIT id) and the budget caps are the draft's and are not edited here.

    python scripts/flights/nx/milestone_successor2_mint_receipt.py --report-date YYYY-MM-DD \\
        --report-arm "<arm and its dev read>" [--coordinator "Fable5.1"] [--dry]
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

import milestone_successor2_preflip_check as pf  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get(
    "SAEA_STUDY_ROOT",
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition",
)
PACKAGE = "docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1"
DRAFT = PACKAGE + "/root-admission-draft-v1.json"
FACTS = PACKAGE + "/registered-facts-v1.json"
DECISION_ID = "slurp-milestone-successor2-admission-v1"
DECISION_RELPATH = "coordination/slurp-milestone-successor2-composed-v1/root-admission-v1.json"
ELIGIBLE = [pf.RUN, pf.FIT_RUN]


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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--report-date", required=True, help="date of the coordinator's conversational report to the owner (allowance first_contact_gate)")
    parser.add_argument("--report-arm", required=True, help="the dev-admitted arm reported, with its dev read")
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    found = pf.refusals(Path(root), Path(DATA))
    if found:
        for line in found:
            print("REFUSED " + line)
        raise SystemExit(f"refusing to mint: {len(found)} preflip refusal(s)")
    facts = json.loads(io.open(os.path.join(root, FACTS), encoding="utf-8").read())
    declared = facts["stage3_measurement"][pf.RUN]["expected_effect_pp"]
    if isinstance(declared, bool) or not isinstance(declared, (int, float)):
        raise SystemExit(f"refusing to mint: expected_effect_pp is {declared!r}, not a declared number")
    if facts["stage3_measurement"][pf.RUN]["measurement_design"] != "cross-flight-no-replicate" \
            or "owner_ruling_decision_250" not in facts["stage3_measurement"][pf.RUN]:
        raise SystemExit("refusing to mint: the measurement block does not record the decision-250 exception")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {DECISION_ID!r}")
    if draft.get("eligible_run_ids") != ELIGIBLE:
        raise SystemExit("the draft's eligible_run_ids are not this cell's two run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["declared_expected_effect_pp"] = declared
    receipt["first_contact_report"] = {
        "date": args.report_date, "arm": args.report_arm,
        "note": "the allowance first_contact_gate: the coordinator reported the dev-admitted arm (R5 read, NEUTRAL) to the owner in conversation",
    }
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/nx/milestone_successor2_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, DECISION_RELPATH)
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
                      "decision_id": DECISION_ID, "eligible_run_ids": ELIGIBLE,
                      "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
