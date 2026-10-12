#!/usr/bin/env python3
"""Mint one of item E41's root-admission decision receipts on the data root from the package's draft.

Root's act, never an agent's. ``--which dry-run`` copies
``docs/readiness/2026-09-27-e21-native-window-e41-v1/root-admission-draft-dry-run-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/e21-native-window-e41-v1/root-admission-dry-run-v1.json``;
``--which sub10`` copies ``root-admission-draft-sub10-v1.json`` to ``root-admission-sub10-v1.json``.
It sets ``status`` to ``decided`` and ``recorded_at_utc`` to now, re-hashes every antecedent
``{"path": ..., "sha256": ...}`` that names a repository file (the draft's hashes are those of the package as
registered; the flip rewrites the package, and the receipt must pin the bytes current when it is minted), and
refuses (a) to overwrite an existing receipt, (b) when any antecedent path does not resolve to a repository
file -- which is how the sub10 receipt stays unmintable until root fills its ``dry_run_read`` antecedent with
the committed E41 dry-run read (row 103: the dry run before the sub10 re-read), and (c) the sub10 receipt
while the dry-run receipt does not exist.

    python scripts/flights/e41/e41_mint_receipt.py --which dry-run|sub10 [--coordinator "Fable5.1"] [--dry]
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
PACKAGE = "docs/readiness/2026-09-27-e21-native-window-e41-v1"
OUT_DIR = "coordination/e21-native-window-e41-v1"
WHICH = {
    "dry-run": {
        "draft": f"{PACKAGE}/root-admission-draft-dry-run-v1.json",
        "out": "root-admission-dry-run-v1.json",
        "decision_id": "e21-native-window-e41-dry-run-admission-v1",
        "eligible": ["SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1", "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-FIT-V1"],
    },
    "sub10": {
        "draft": f"{PACKAGE}/root-admission-draft-sub10-v1.json",
        "out": "root-admission-sub10-v1.json",
        "decision_id": "e21-native-window-e41-sub10-admission-v1",
        "eligible": ["SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1", "SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1-FIT-V1"],
    },
}


def rehash(node, root: str, missing: list[str]) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and "sha256" in node:
            full = os.path.join(root, path)
            if os.path.isfile(full):
                node["sha256"] = hashlib.sha256(io.open(full, "rb").read()).hexdigest()
                count += 1
            else:
                missing.append(path)
        for value in node.values():
            count += rehash(value, root, missing)
    elif isinstance(node, list):
        for value in node:
            count += rehash(value, root, missing)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--which", required=True, choices=sorted(WHICH))
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    spec = WHICH[args.which]
    root = ROOT.rstrip("/")
    draft = json.loads(io.open(os.path.join(root, spec["draft"]), encoding="utf-8").read())
    if draft.get("decision_id") != spec["decision_id"]:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {spec['decision_id']!r}")
    if draft.get("eligible_run_ids") != spec["eligible"]:
        raise SystemExit(f"the draft's eligible_run_ids are not the two E41 {args.which} run ids")
    out_dir = os.path.join(DATA, OUT_DIR)
    if args.which == "sub10" and not os.path.isfile(os.path.join(out_dir, WHICH["dry-run"]["out"])):
        raise SystemExit("refusing: the dry-run receipt does not exist; the dry run flies and is read before the sub10 re-read")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["minted_from"] = {"template_receipt": spec["draft"], "tool": "scripts/flights/e41/e41_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    missing: list[str] = []
    rehashed = rehash(receipt, root, missing)
    if missing:
        raise SystemExit(f"refusing: antecedent path(s) do not resolve to repository files: {missing}")
    out = os.path.join(out_dir, spec["out"])
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
                      "decision_id": spec["decision_id"], "eligible_run_ids": spec["eligible"],
                      "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
