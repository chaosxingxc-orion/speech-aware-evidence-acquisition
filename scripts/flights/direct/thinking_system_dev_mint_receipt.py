#!/usr/bin/env python3
"""Mint the root-admission decision receipt of the P3.1 replicate (the locked system on the Thinking core, DEV-2000-ADDED) on the data root.

Root's act, never an agent's. The Fold B minting logic (``thinking_system_mint_receipt.mint``) with the DEV family: copies
``docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/slurp-system-thinking-core-dev2000-added-v1/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, re-hashes every antecedent that names a repository file, and refuses to overwrite an existing receipt.

FAILS CLOSED while the DEV Thinking promotion receipt is absent or while any cell baseline still carries the zero sentinel for it: a receipt must
not be minted for cells whose packets do not exist.

    python scripts/flights/direct/thinking_system_dev_mint_receipt.py [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import thinking_system_dev_family as fam  # noqa: E402
import thinking_system_mint_receipt as base  # noqa: E402

TOOL = "scripts/flights/direct/thinking_system_dev_mint_receipt.py"


def require_packets(root: str) -> str:
    """The pinned sha256 of the DEV promotion receipt; SystemExit when the receipt is absent or any baseline carries another pin."""

    sha = fam.thinking_promotion_sha256()
    for key in fam.ALL_KEYS:
        path = Path(root) / "configs" / "baseline" / f"{fam.CELLS[key]['baseline']}.json"
        pinned = json.loads(path.read_text(encoding="utf-8")).get("speech_packet_promotion_receipt_sha256")
        if pinned != sha:
            raise SystemExit(f"REFUSED: {path.name} pins {pinned!r}, the DEV promotion receipt is {sha}; re-run thinking_system_dev_derive_cells.py --require-receipt")
    return sha


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = base.ROOT.rstrip("/")
    require_packets(root)
    summary = base.mint(root, base.DATA, args.coordinator, args.dry, family=fam, tool=TOOL)
    if args.dry:
        print(summary.pop("text"))
        print(f"(dry) would write {summary['out']}; re-hashed {summary['rehashed_paths']} antecedent path(s)")
        return 0
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
