#!/usr/bin/env python3
"""Regenerate configs/probes/manifest.json from the frozen templates (P0.C)."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.reproduction.manifest import write_manifest  # noqa: E402


def main() -> int:
    templates_dir = REPO_ROOT / "configs" / "probes"
    receipts_dir = REPO_ROOT / "docs" / "receipts" / "probe-samples"
    out_path = templates_dir / "manifest.json"
    write_manifest(templates_dir, receipts_dir, out_path)
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    print(f"wrote {out_path}")
    print(f"manifest sha256 (protocol-hash anchor): {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
