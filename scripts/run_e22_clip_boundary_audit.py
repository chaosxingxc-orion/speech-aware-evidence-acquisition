#!/usr/bin/env python3
"""CLI: the Earnings-22 DEV clip-boundary audit (model-free, zero contacts).

Exposure row ``SAEA-E22-MF-CLIP-BOUNDARY-AUDIT-V1`` (``model-free-check``),
registered before the first segment timestamp or clip sample was read.

I/O ONLY: every measurement lives in ``analysis.e22_clip_boundary``. This script
arms the offline guard, loads the committed dev10 roster, the hash-pinned dev10
segment table and reference layer plus the three sealed hypothesis files, reads
each derived dev clip once for its frame energies, and writes the receipt
directory with its ``MANIFEST.sha256``.

The six ESB TEST calls are unreachable from here: the reference loader is pinned
to the dev10 receipt, the segment-table loader to the dev10 extracted table, and
every media path comes from the dev10 roster alone. No model, tokenizer,
embedder, network or GPU contact; no audio is delivered to any service.

Usage (WSL2)::

    python scripts/run_e22_clip_boundary_audit.py            # print only
    python scripts/run_e22_clip_boundary_audit.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_clip_boundary import (  # noqa: E402
    build_summary,
    clip_geometry,
    headline,
    load_media_digests,
    load_roster,
    measure_margins,
    per_clip_table,
    scan_arms,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    load_segment_table,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-clip-boundary-audit"
)


def write_manifest(directory: Path) -> None:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    root = Path(data_root())

    roster = load_roster(REPO_ROOT)
    items = list(roster["items"])
    geometry = clip_geometry(items)
    margins, media_read = measure_margins(
        root, items, geometry, load_media_digests(REPO_ROOT)
    )

    references = load_esb_references(
        root,
        repo_root=REPO_ROOT,
        receipt_relpaths=(ESB_DEV10_REFERENCE_RECEIPT_RELPATH,),
    )
    segments = load_segment_table(root, REPO_ROOT)
    arms, reference_words = scan_arms(root, references, segments)

    summary = build_summary(
        roster=roster,
        geometry=geometry,
        margins=margins,
        media_read=media_read,
        arms=arms,
        reference_words=reference_words,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )
    print(headline(summary))

    if not args.write:
        print("\n(dry run: pass --write to emit the receipt directory)")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "per-clip-table.csv").write_text(
        per_clip_table(geometry, margins, arms["A"]), encoding="utf-8"
    )
    write_manifest(OUT_DIR)
    print(f"\nwrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
