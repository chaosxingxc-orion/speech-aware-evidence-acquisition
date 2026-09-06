#!/usr/bin/env python3
"""CLI: the ESB released-array duration check (model-free, zero contacts).

Exposure row ``SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1`` (``model-free-check``),
registered before the reading pass.

I/O ONLY: every measurement lives in ``analysis.e22_esb_array_durations``. This
script arms the offline guard, loads the committed 2026-09-04 segment-table
receipt, re-hashes the pinned ``segments-test.jsonl`` against it, size-checks
the four locally materialized TEST shards, reads each shard once for its
per-row blob LENGTH and RIFF/WAVE container header, and writes the receipt
directory with its ``MANIFEST.sha256``.

No text, no audio content, no outputs: the ``sentence`` column is never
projected, the JSONL's ``sentence`` field is dropped inside the loader, no
sealed output or reference layer is reachable from here, and no audio sample is
decoded. No model, tokenizer, embedder, network or GPU contact.

Usage (WSL2)::

    python scripts/run_e22_esb_array_durations.py            # print only
    python scripts/run_e22_esb_array_durations.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_esb_array_durations import (  # noqa: E402
    adjacent_pairs,
    build_arrays,
    build_summary,
    headline,
    load_receipt,
    load_test_segment_table,
    per_utterance_table,
    read_shard_headers,
    resolve_shards,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-esb-array-durations"
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

    started = time.time()
    attempts = arm_offline_guard()
    root = Path(data_root())

    receipt = load_receipt(REPO_ROOT)
    segments = load_test_segment_table(root, receipt)
    shards = resolve_shards(root, receipt)

    shard_rows: list[dict[str, object]] = []
    for shard in shards:
        rows = read_shard_headers(shard["path"])
        print(f"read {shard['relpath']}: {len(rows)} rows")
        shard_rows.extend(rows)

    arrays = build_arrays(shard_rows, segments)
    pairs = adjacent_pairs(arrays)
    summary = build_summary(
        arrays=arrays,
        pairs=pairs,
        shards=shards,
        receipt=receipt,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )
    # Wall time is PRINTED, never stored: summary.json must be byte-deterministic
    # so a second run of the same inputs reproduces the same MANIFEST.sha256.
    print(headline(summary))
    print(f"wall seconds {time.time() - started:.3f}")

    if not args.write:
        print("\n(dry run: pass --write to emit the receipt directory)")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUT_DIR / "per-utterance-table.csv").write_text(
        per_utterance_table(arrays, pairs), encoding="utf-8"
    )
    write_manifest(OUT_DIR)
    print(f"\nwrote {OUT_DIR}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
