#!/usr/bin/env python3
"""PRE Track A, verify-only slice manifest (tool(pre) build; SAEA-TOOL-
precut-buf90-v1).

The 34 kb-construction-sample calls' buf90 slices ALREADY EXIST under
``$SPEECHRL_DATA_DIR/derived/obs-slices/SAEA-BENCH-kb34-floor/<id>/`` (1,251
slices, written by the already-consumed ``SAEA-BENCH-kb34-floor`` run). This
script hashes every slice WAV on disk (20-worker ``ThreadPoolExecutor`` --
I/O + hashlib only, no GPU/model touch, no re-cutting) and cross-verifies
each ``sha256``/``bytes`` pair against that run's own already-committed
``<run_id>.obs-derivation.<sample_id>.json`` records. Never opens a model
session; never reads a reference/gold layer.

Writes ``$SPEECHRL_DATA_DIR/derived/obs-slices-precut/buf90-v1/manifest.json``
(schema ``saea-precut-manifest-v1``). A mismatch is FATAL: the manifest still
records every mismatch found (so a partial run is diagnosable), but the
process exits non-zero whenever ``cross_verification.mismatches`` or
``failures`` is non-empty, so a mismatch can never be missed at the
terminal.

The split identity hash recorded here is the SLASH convention execution
plans use (``sha256`` over sorted ``f"{carrier_lock_key}/{id}"`` keys, via
``data.splits.split_identity_hash``) -- NOT the colon-convention hash the
``kb-construction-sample.json`` receipt itself stores under its own
``split_identity_hash`` key (a receipt-schema artifact of
``reproduction.sampling.split_identity_hash`` hashing ``"carrier:id"`` keys
instead). The two conventions were the exact subject of the 2026-08-14
``SAEA-BENCH-kb34-floor`` ledger amendment (``docs/exposure-ledger.md``);
this script reuses the canonical ``data.splits`` implementation rather than
re-deriving either hash by hand.

Usage:
    python scripts/precut_manifest.py
    python scripts/precut_manifest.py --workers 20 --run-id SAEA-BENCH-kb34-floor
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

SCHEMA = "saea-precut-manifest-v1"
LEDGER_ROW = "SAEA-TOOL-precut-buf90-v1"
DEFAULT_RUN_ID = "SAEA-BENCH-kb34-floor"
DEFAULT_CARRIER = "earnings21-original"
DEFAULT_SPLIT_NAME = "kb-construction-sample"
DEFAULT_IDS_FILE = (
    REPO_ROOT / "docs" / "receipts" / "probe-samples" / "kb-construction-sample.json"
)
DEFAULT_WORKERS = 20
DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)


class PrecutError(RuntimeError):
    """The slice corpus, an obs-derivation record, or the id list cannot be resolved."""


def load_ids(ids_file: Path) -> list[str]:
    document = json.loads(Path(ids_file).read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise PrecutError(f"{ids_file}: no usable 'items' list")
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise PrecutError(f"{ids_file}: duplicate ids")
    return sorted(ids)


def sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def load_obs_derivation_record(
    run_dir: Path, run_id: str, sample_id: str
) -> Mapping[str, object]:
    matches = sorted(run_dir.glob(f"attempt-*/{run_id}.obs-derivation.{sample_id}.json"))
    if not matches:
        raise PrecutError(f"no obs-derivation record for sample {sample_id!r} under {run_dir}")
    if len(matches) > 1:
        raise PrecutError(
            f"ambiguous obs-derivation records for sample {sample_id!r}: {matches}"
        )
    document = json.loads(matches[0].read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise PrecutError(f"{matches[0]}: obs-derivation record must be a JSON object")
    return document


def hash_slice_dir(call_dir: Path, workers: int) -> dict[str, tuple[str, int]]:
    wav_paths = sorted(call_dir.glob("i*.wav"))
    results: dict[str, tuple[str, int]] = {}
    if not wav_paths:
        return results
    with ThreadPoolExecutor(max_workers=min(workers, len(wav_paths))) as pool:
        futures = {pool.submit(sha256_and_size, path): path for path in wav_paths}
        for future in as_completed(futures):
            path = futures[future]
            results[path.name] = future.result()
    return results


def verify_call(
    sample_id: str, obs_slices_dir: Path, run_dir: Path, run_id: str, workers: int
) -> tuple[dict[str, object], list[dict[str, object]], int]:
    """One call's ``(per_call entry, mismatches, records_compared)``."""

    call_dir = obs_slices_dir / sample_id
    record = load_obs_derivation_record(run_dir, run_id, sample_id)
    slices_record = record.get("slices")
    if not isinstance(slices_record, list) or not slices_record:
        raise PrecutError(f"obs-derivation record for {sample_id!r} has no usable 'slices'")

    hashed = hash_slice_dir(call_dir, workers)
    mismatches: list[dict[str, object]] = []
    slices_out: list[dict[str, object]] = []
    seen_filenames: set[str] = set()

    for slice_entry in sorted(slices_record, key=lambda entry: entry["iteration"]):
        media_relpath = slice_entry["media_relpath"]
        filename = Path(media_relpath).name
        seen_filenames.add(filename)
        expected_sha256 = slice_entry["sha256"]
        expected_bytes = slice_entry["bytes"]
        if filename not in hashed:
            mismatches.append(
                {
                    "sample_id": sample_id,
                    "iteration": slice_entry["iteration"],
                    "filename": filename,
                    "reason": "missing_on_disk",
                }
            )
            continue
        actual_sha256, actual_bytes = hashed[filename]
        if actual_sha256 != expected_sha256 or actual_bytes != expected_bytes:
            mismatches.append(
                {
                    "sample_id": sample_id,
                    "iteration": slice_entry["iteration"],
                    "filename": filename,
                    "reason": "hash_or_size_mismatch",
                    "expected_sha256": expected_sha256,
                    "actual_sha256": actual_sha256,
                    "expected_bytes": expected_bytes,
                    "actual_bytes": actual_bytes,
                }
            )
            continue
        slices_out.append(
            {
                "iteration": slice_entry["iteration"],
                "sha256": actual_sha256,
                "bytes": actual_bytes,
                "start_seconds": slice_entry["start_seconds"],
                "end_seconds": slice_entry["end_seconds"],
                "source_path": media_relpath,
            }
        )

    for filename in sorted(set(hashed) - seen_filenames):
        mismatches.append(
            {"sample_id": sample_id, "filename": filename, "reason": "extra_file_not_in_record"}
        )

    per_call = {
        "parent_media_relpath": record.get("parent_media_relpath"),
        "parent_sha256": record.get("parent_sha256"),
        "slice_count": len(slices_out),
        "slices": slices_out,
    }
    return per_call, mismatches, len(slices_record)


def build_manifest(
    *,
    data_root: Path,
    run_id: str,
    ids: list[str],
    carrier_lock_key: str,
    split_name: str,
    workers: int,
) -> dict[str, object]:
    obs_slices_dir = data_root / "derived" / "obs-slices" / run_id
    run_dir = data_root / "runs" / run_id

    per_call: dict[str, object] = {}
    all_mismatches: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    records_compared = 0
    total_slices = 0

    start = time.monotonic()
    for sample_id in ids:
        try:
            entry, mismatches, compared = verify_call(
                sample_id, obs_slices_dir, run_dir, run_id, workers
            )
        except PrecutError as error:
            failures.append({"sample_id": sample_id, "error": str(error)})
            continue
        per_call[sample_id] = entry
        all_mismatches.extend(mismatches)
        records_compared += compared
        total_slices += entry["slice_count"]
    wall_seconds = time.monotonic() - start

    try:
        import resource

        peak_rss_mb: float | None = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        peak_rss_mb = None

    calls_per_min = (len(ids) / wall_seconds * 60.0) if wall_seconds > 0 else None
    slices_per_min = (total_slices / wall_seconds * 60.0) if wall_seconds > 0 else None

    prefixed_ids = prefixed(carrier_lock_key, ids)
    manifest = {
        "schema": SCHEMA,
        "ledger_row": LEDGER_ROW,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "split": {
            "name": split_name,
            "carrier_lock_key": carrier_lock_key,
            "ids": sorted(ids),
            "split_identity_hash": split_identity_hash(prefixed_ids),
            "convention": "slash (carrier_lock_key/id, sorted, LF-joined, sha256)",
        },
        "per_call": per_call,
        "cross_verification": {
            "against_run": run_id,
            "records_compared": records_compared,
            "mismatches": all_mismatches,
        },
        "throughput": {
            "slices_per_min": slices_per_min,
            "calls_per_min": calls_per_min,
            "wall_seconds": wall_seconds,
            "workers": workers,
            "peak_rss_mb": peak_rss_mb,
        },
        "failures": failures,
    }
    return manifest


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--ids-file", type=Path, default=DEFAULT_IDS_FILE)
    parser.add_argument("--carrier-lock-key", default=DEFAULT_CARRIER)
    parser.add_argument("--split-name", default=DEFAULT_SPLIT_NAME)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--out", type=Path, default=None, help="TEST-ONLY override of the manifest output path"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    try:
        ids = load_ids(args.ids_file)
        manifest = build_manifest(
            data_root=args.data_root,
            run_id=args.run_id,
            ids=ids,
            carrier_lock_key=args.carrier_lock_key,
            split_name=args.split_name,
            workers=args.workers,
        )
    except PrecutError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    out_path = args.out or (
        args.data_root / "derived" / "obs-slices-precut" / "buf90-v1" / "manifest.json"
    )
    manifest_sha256 = write_json_artifact(out_path, manifest)

    mismatches = manifest["cross_verification"]["mismatches"]
    failures = manifest["failures"]
    print(
        json.dumps(
            {
                "manifest": str(out_path),
                "manifest_sha256": manifest_sha256,
                "calls": len(manifest["per_call"]),
                "records_compared": manifest["cross_verification"]["records_compared"],
                "mismatches": len(mismatches),
                "failures": len(failures),
                "throughput": manifest["throughput"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if mismatches or failures:
        print(
            f"REFUSED: {len(mismatches)} mismatch(es), {len(failures)} failure(s) -- see "
            f"{out_path}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
