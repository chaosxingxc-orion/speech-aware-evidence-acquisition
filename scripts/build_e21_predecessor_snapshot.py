#!/usr/bin/env python3
"""Compatibility reader for the immutable historical predecessor receipt.

New parents use scripts/flights/bind_window_predecessor.py and an explicit
prospective parent contract through core.predecessor_builder. This entry keeps
the historical no-argument invocation and verifies its saved result; it never
recomputes or overwrites historical model-output derivatives.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
from speech_aware_evidence_acquisition.core.predecessor_snapshot import load_predecessor_binding
from speech_aware_evidence_acquisition.data.lock import data_root

REPO_ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="SAEA-E21-FULL44-DIRECT-BASELINE-V2")
    parser.add_argument("--attempt-id", default="attempt-20260904T233816Z-bcd338")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "docs/receipts/e21-predecessor-full44-direct-baseline-v2.json")
    parser.add_argument("--allow-dirty", action="store_true", help="Legacy option; this path is read-only.")
    args = parser.parse_args()
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    if not args.out.is_file():
        parser.error("Historical receipt is absent; build a new explicitly contracted parent with scripts/flights/bind_window_predecessor.py")
    snapshot = load_predecessor_binding(args.out, data_root())
    if (snapshot.run_id, snapshot.attempt_id) != (args.run_id, args.attempt_id):
        parser.error("The saved predecessor names a different run or attempt")
    print(json.dumps({"status": "VERIFIED_EXISTING", "windows": snapshot.window_count,
                      "calls": snapshot.call_count, "receipt_path": str(args.out),
                      "receipt_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest()}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
