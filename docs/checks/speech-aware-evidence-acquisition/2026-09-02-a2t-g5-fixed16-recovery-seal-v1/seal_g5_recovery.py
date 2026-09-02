#!/usr/bin/env python3
"""Write the append-only, no-contact G5 fixed16 recovery seal."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.rails.probes.a2t_g5_recovery_seal import (  # noqa: E402
    build_recovery_seal,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mission-dir", required=True, type=Path)
    parser.add_argument("--attempts-root", required=True, type=Path)
    args = parser.parse_args()
    receipt = build_recovery_seal(args.mission_dir, attempts_root=args.attempts_root)
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
