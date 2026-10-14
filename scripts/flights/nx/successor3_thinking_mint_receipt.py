#!/usr/bin/env python3
"""Mint the root-admission decision receipt of the SUCCESSOR-3 cell (the Thinking system on the signed test sample; owner ruling 301 A) on the data root.

Root's act, never an agent's. Copies ``docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-milestone-successor3-thinking-system-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and ``recorded_at_utc`` to now,
records the conversational first-contact report of the allowance gate (``--report-date``, ``--report-arm``; both required), re-hashes every antecedent
``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to overwrite an existing receipt. It refuses first on every refusal of
``successor3_thinking_preflip_check.py`` (which includes the absent Thinking sample promotion receipt and the zero packet-receipt pin).

    python scripts/flights/nx/successor3_thinking_mint_receipt.py --report-date YYYY-MM-DD --report-arm "<arm and its dev read>" [--coordinator "Fable5.1"] [--dry]
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

sys.path.insert(0, str(Path(__file__).resolve().parent))

import successor3_thinking_family as fam  # noqa: E402
import successor3_thinking_preflip_check as pf  # noqa: E402

DATA = os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
DRAFT = fam.package_file("root-admission-draft-v1.json")
FACTS = fam.package_file("registered-facts-v1.json")


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
    block = facts["stage3_measurement"][fam.RUN]
    declared = block["expected_effect_pp"]
    if isinstance(declared, bool) or not isinstance(declared, (int, float)):
        raise SystemExit(f"refusing to mint: expected_effect_pp is {declared!r}, not a declared number")
    if block["measurement_design"] != "cross-flight-no-replicate" or "owner_ruling_301_a" not in block or block["claims_benefit"] is not False:
        raise SystemExit("refusing to mint: the measurement block does not record the ruling-301 exception with claims_benefit false")
    draft = json.loads(io.open(os.path.join(root, DRAFT), encoding="utf-8").read())
    if draft.get("decision_id") != fam.DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {fam.DECISION_ID!r}")
    if draft.get("eligible_run_ids") != fam.eligible_run_ids():
        raise SystemExit("the draft's eligible_run_ids are not this cell's two run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["declared_expected_effect_pp"] = declared
    receipt["first_contact_report"] = {"date": args.report_date, "arm": args.report_arm,
                                       "note": "the allowance first_contact_gate: the coordinator reported the P3.1 read (NOMINATED) to the owner in conversation"}
    receipt["minted_from"] = {"template_receipt": DRAFT, "tool": "scripts/flights/nx/successor3_thinking_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, fam.DECISION_RELPATH)
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "decision_id": fam.DECISION_ID,
                      "eligible_run_ids": fam.eligible_run_ids(), "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
