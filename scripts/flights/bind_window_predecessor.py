#!/usr/bin/env python3
"""Bind a prospectively declared new Earnings parent through the shared builder."""
import argparse
import json
from pathlib import Path
from speech_aware_evidence_acquisition.core.predecessor_builder import build_predecessor_snapshot

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("manifest", "repo-root", "data-root", "contract", "receipt"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--exposure-row", required=True)
    args = parser.parse_args()
    print(json.dumps(build_predecessor_snapshot(
        manifest_path=args.manifest, repo_root=args.repo_root, data_root=args.data_root,
        contract=json.loads(args.contract.read_text()), receipt_path=args.receipt,
        exposure_row=args.exposure_row,
    ), sort_keys=True))

if __name__ == "__main__":
    main()
