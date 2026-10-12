#!/usr/bin/env python3
"""Mint the COMP-1b TEST-SAMPLE milestone's root-admission decision receipt (owner decisions 151 and 202)
on the data root from the package's draft.

Root's act, never an agent's. Copies
``docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-comp1b-testsample-v1/root-admission-v1.json``, sets
``status`` to ``decided`` and ``recorded_at_utc`` to now, records the conversational first-contact
report of decision 151 (``--report-date``, ``--report-arm``; both required), re-hashes every
antecedent path, and refuses to overwrite an existing receipt. It refuses first on every refusal of
``comp1b_testsample_preflip_check.py`` (expectation not re-declared, FIT run ids not permitted by
the pinned allowance, pending pins, missing data-root artifacts).

    python scripts/flights/comp1/comp1b_testsample_mint_receipt.py --report-date YYYY-MM-DD \\
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

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1"
DRAFT = PACKAGE + "/root-admission-draft-v1.json"
FACTS = PACKAGE + "/registered-facts-v1.json"
OUT_DIR = "coordination/slurp-stage3-comp1b-testsample-v1"
OUT_NAME = "root-admission-v1.json"
DECISION_ID = "slurp-stage3-comp1b-testsample-milestone-admission-v1"
ARM_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1"
ELIGIBLE = [
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-FIT-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1",
    "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1",
]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comp1b_testsample_preflip_check import refusals  # noqa: E402


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
    parser.add_argument("--report-date", required=True, help="date of the coordinator's conversational report to the owner (decision 151)")
    parser.add_argument("--report-arm", required=True, help="the dev-admitted arm reported, with its dev read")
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    found = refusals(Path(root), Path(DATA))
    if found:
        for line in found:
            print("REFUSED " + line)
        raise SystemExit(f"refusing to mint: {len(found)} preflip refusal(s)")
    facts = json.loads(io.open(os.path.join(root, FACTS), encoding="utf-8").read())
    declared = facts["stage3_measurement"][ARM_RUN]["expected_effect_pp"]
    if isinstance(declared, bool) or not isinstance(declared, (int, float)):
        raise SystemExit(f"refusing to mint: expected_effect_pp is {declared!r}, not a declared number")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != DECISION_ID or draft.get("eligible_run_ids") != ELIGIBLE:
        raise SystemExit("the draft's decision id or eligible run ids are not the milestone's")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["declared_expected_effect_pp"] = declared
    receipt["first_contact_report"] = {"date": args.report_date, "arm": args.report_arm,
                                       "note": "decision 151: the coordinator reported this dev-admitted composed arm to the owner in conversation"}
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/comp1/comp1b_testsample_mint_receipt.py"}
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
