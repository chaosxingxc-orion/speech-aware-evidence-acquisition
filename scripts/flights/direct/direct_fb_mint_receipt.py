#!/usr/bin/env python3
"""Mint the root-admission decision receipt of the 266-E bare-core read on the data root from the package's draft.

Root's act, never an agent's. Copies ``docs/readiness/2026-10-11-slurp-direct-only-fold-b-thinking-vs-instruct-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-direct-only-fold-b-thinking-vs-instruct-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to overwrite an
existing receipt. The ``eligible_run_ids`` (four generation run ids, their four first-registration FIT identities and the rec1 FIT run id of each recovered cell) and the budget caps are the draft's and are
not edited here. The zero packet-promotion sentinel of the Thinking baselines is the flip's concern (``direct_fb_flip.sh``), not the receipt's.

    python scripts/flights/direct/direct_fb_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
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

import direct_fb_family as fam  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get(
    "SAEA_STUDY_ROOT",
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition",
)


def expected_eligible() -> list[str]:
    return fam.eligible_run_ids()


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


def mint(root: str, data: str, coordinator: str = "Fable5.1", dry: bool = False, now: datetime | None = None) -> dict:
    """Build (and, unless dry, write) the receipt; returns a summary. Raises SystemExit on any mismatch."""

    draft_path = f"{fam.PACKAGE}/root-admission-draft-v1.json"
    draft = json.loads(io.open(os.path.join(root, draft_path), encoding="utf-8").read())
    if draft.get("decision_id") != fam.DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {fam.DECISION_ID!r}")
    if draft.get("eligible_run_ids") != expected_eligible():
        raise SystemExit("the draft's eligible_run_ids are not this read's eight run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = (now or datetime.now(timezone.utc)).isoformat()
    receipt["coordinator"] = coordinator
    receipt["minted_from"] = {"template_receipt": draft_path, "tool": "scripts/flights/direct/direct_fb_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(data, fam.DECISION_RELPATH)
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    summary = {"out": out, "decision_id": fam.DECISION_ID, "eligible_run_ids": receipt["eligible_run_ids"], "rehashed_paths": rehashed,
               "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
    if dry:
        return {**summary, "dry": True, "text": text}
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    summary = mint(ROOT.rstrip("/"), DATA, args.coordinator, args.dry)
    if args.dry:
        print(summary.pop("text"))
        print(f"(dry) would write {summary['out']}; re-hashed {summary['rehashed_paths']} antecedent path(s)")
        return 0
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
