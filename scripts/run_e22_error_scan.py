#!/usr/bin/env python3
"""CLI: the Earnings-22 DEV semantic error scan (model-free, zero contacts).

Exposure row ``SAEA-E22-MF-SEMANTIC-ERROR-SCAN-V1`` (``model-free-check``),
registered before the first sealed byte was read.

I/O ONLY: every measurement and every receipt field lives in
``analysis.e22_error_taxonomy``. This script arms the offline guard, loads the
hash-pinned DEV10 reference layer and DEV10 segment table plus the three sealed
hypothesis files, hands them to ``build_receipts``, prints the headline and
writes the receipt directory with its ``MANIFEST.sha256``.

The six ESB TEST calls are unreachable from here: ``load_esb_references`` is
pinned to the dev10 receipt path alone, so ``e22-esb-test-references.jsonl`` is
never opened, and the segment-table loader reads the dev10 extracted table only.
No model, tokenizer, embedder, network, GPU or audio contact.

Usage (WSL2)::

    python scripts/run_e22_error_scan.py            # print only
    python scripts/run_e22_error_scan.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    build_receipts,
    load_segment_table,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-semantic-error-scan"
)


def write_manifest(directory: Path) -> None:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def headline(summary: dict) -> str:
    lines = []
    for arm in sorted(summary["arms"]):
        block = summary["arms"][arm]
        bins = block["gap_bins"]["bins"]
        lines.append(
            f"arm {arm}: corpus WER {block['corpus_wer_percent']:.4f} %"
            f" | agentic error rate {block['agentic_error_rate']['agentic_error_rate_percent']:.4f} %"
            f" (strict {block['agentic_error_rate_strict']['agentic_error_rate_percent']:.4f} %)"
            f" | identity gate {block['identity_gate']['reproduced']}"
        )
        lines.append(
            "    bins: "
            + ", ".join(
                f"{name} {values['wer_points']:.3f} pts" for name, values in bins.items()
            )
        )
        raw = block["raw_pass"]
        folded = 100.0 * raw["format_only_errors"] / raw["raw_errors"]
        lines.append(
            f"    raw pass: {raw['raw_errors']} raw errors, "
            f"{raw['format_only_errors']} format-only ({folded:.1f} % already folded)"
        )
        lines.append(
            "    top categories: "
            + ", ".join(
                f"{row['category']} {row['wer_points']:.3f}"
                for row in sorted(
                    block["category_table"], key=lambda row: -row["error_mass"]
                )[:4]
            )
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    root = Path(data_root())
    references = load_esb_references(
        root,
        repo_root=REPO_ROOT,
        receipt_relpaths=(ESB_DEV10_REFERENCE_RECEIPT_RELPATH,),
    )
    segments = load_segment_table(root, REPO_ROOT)

    summary, tables, read_sample = build_receipts(
        repo_root=REPO_ROOT,
        root=root,
        references=references,
        segments=segments,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )

    print(headline(summary))
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", summary)
    write_json_artifact(OUT_DIR / "read-sample-ids.json", read_sample)
    (OUT_DIR / "per-arm-tables.md").write_text(tables, encoding="utf-8", newline="\n")
    write_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
