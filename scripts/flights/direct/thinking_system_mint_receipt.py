#!/usr/bin/env python3
"""Mint the root-admission decision receipt of the 268-B read (the locked system on the Thinking core) on the data root from the package's draft.

Root's act, never an agent's. Copies ``docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-system-thinking-core-fold-b-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to overwrite an
existing receipt. The ``eligible_run_ids`` (three generation run ids and their three FIT identities, in chain order) and the budget caps are the draft's and are
not edited here. 

    python scripts/flights/direct/thinking_system_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations

import re

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import thinking_system_family as fam  # noqa: E402


def _authority_default() -> str:
    """The data-root default assigned in scripts/lib/data_root.sh (decision 274: one authority, no literal here)."""
    lib = Path(__file__).resolve().parents[2] / "lib" / "data_root.sh"
    match = re.search(r"^SAEA_DATA_ROOT_DEFAULT=(\S+)\s*$", lib.read_text(encoding="utf-8"), re.M)
    if match is None:
        raise SystemExit(f"{lib} does not assign SAEA_DATA_ROOT_DEFAULT")
    return match.group(1)


def _data_root_env() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or _authority_default()

DATA = _data_root_env()
ROOT = os.environ.get(
    "SAEA_STUDY_ROOT",
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition",
)


def expected_eligible(family=None) -> list[str]:
    return (family or fam).eligible_run_ids()


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


def mint(root: str, data: str, coordinator: str = "Fable5.1", dry: bool = False, now: datetime | None = None, family=None,
         tool: str = "scripts/flights/direct/thinking_system_mint_receipt.py") -> dict:
    """Build (and, unless dry, write) the receipt; returns a summary. Raises SystemExit on any mismatch.

    ``family`` selects the package family (default: the 268-B Fold B family); the DEV wrapper passes ``thinking_system_dev_family``."""

    fam = family or globals()["fam"]
    draft_path = f"{fam.PACKAGE}/root-admission-draft-v1.json"
    draft = json.loads(io.open(os.path.join(root, draft_path), encoding="utf-8").read())
    if draft.get("decision_id") != fam.DECISION_ID:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {fam.DECISION_ID!r}")
    if draft.get("eligible_run_ids") != expected_eligible(fam):
        raise SystemExit("the draft's eligible_run_ids are not this read's six run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = (now or datetime.now(timezone.utc)).isoformat()
    receipt["coordinator"] = coordinator
    receipt["minted_from"] = {"template_receipt": draft_path, "tool": tool}
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
