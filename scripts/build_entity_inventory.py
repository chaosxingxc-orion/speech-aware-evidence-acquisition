#!/usr/bin/env python3
"""PRE Track A gold-side entity inventory (tool(pre) build).

RUNTIME-PROHIBITED. Per call, per mention: ``entity_id``, ``entity_type``,
the reference-token ``token_indices``, the mention's own tokens, and a
SPAN -- ``{start_index, end_index, contiguous}`` computed as the
min/max of ``token_indices`` (``data.references.EntityMention`` carries no
character-offset information, so a token-index span is the finest-grained
"span" the reference layer exposes; ``contiguous`` records whether the
mention's indices form an unbroken run, since Earnings21 entity spans are
documented as not always contiguous).

Read via ``speech_aware_evidence_acquisition.data.references.
reference_entity_mentions`` -- the SAME scoring-side reader
``core.scorers`` uses for entity-class WER. That module is import-
restricted: ``tests/contract/test_reference_import_isolation.py`` scans
only ``src/**/*.py`` and refuses any module OTHER than ``core/scorers.py``
that imports it. This script lives under ``scripts/`` specifically so it
can import ``data.references`` directly without tripping that contract --
the isolation test's own scan boundary is exactly why an entity-inventory
generator cannot be a ``src/`` module.

Every output file -- both each per-call ``<id>.json`` and the manifest --
carries a top-level ``{"runtime_prohibited": true, "note": "gold-derived;
scoring-side only; must never enter a runtime path"}``: this inventory is
for OFFLINE SCORING-SIDE analysis only. 12-worker ``ThreadPoolExecutor``
(I/O + ``ast.literal_eval`` parsing; no GPU/model touch).

Writes ``$SPEECHRL_DATA_DIR/derived/entity-inventory/v1/<id>.json`` plus a
``manifest.json``.

Usage:
    python scripts/build_entity_inventory.py
    python scripts/build_entity_inventory.py --workers 12
"""

from __future__ import annotations
import os

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.references import (  # noqa: E402
    EntityMention,
    ReferenceError,
    reference_entity_mentions,
)
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

RUNTIME_PROHIBITED_NOTE = "gold-derived; scoring-side only; must never enter a runtime path"
DEFAULT_CARRIER = "earnings21-original"
DEFAULT_SPLIT_NAME = "kb-construction-sample"
DEFAULT_IDS_FILE = (
    REPO_ROOT / "docs" / "receipts" / "probe-samples" / "kb-construction-sample.json"
)
DEFAULT_WORKERS = 12
OUT_SUBDIR = Path("derived") / "entity-inventory" / "v1"
DEFAULT_DATA_ROOT = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)


class EntityInventoryError(RuntimeError):
    """The id list cannot be resolved."""


def load_ids(ids_file: Path) -> list[str]:
    document = json.loads(Path(ids_file).read_text(encoding="utf-8"))
    items = document.get("items")
    if not isinstance(items, list) or not items:
        raise EntityInventoryError(f"{ids_file}: no usable 'items' list")
    ids = [item["id"] for item in items]
    if len(set(ids)) != len(ids):
        raise EntityInventoryError(f"{ids_file}: duplicate ids")
    return sorted(ids)


def mention_record(mention: EntityMention) -> dict[str, object]:
    indices = list(mention.token_indices)
    start, end = min(indices), max(indices)
    return {
        "entity_id": mention.entity_id,
        "entity_type": mention.entity_type,
        "token_indices": indices,
        "tokens": list(mention.tokens),
        "span": {
            "start_index": start,
            "end_index": end,
            "contiguous": indices == list(range(start, end + 1)),
        },
    }


def build_call_inventory(
    lock: Mapping[str, object], root: Path, carrier_lock_key: str, sample_id: str
) -> dict[str, object]:
    mentions = reference_entity_mentions(lock, root, carrier_lock_key, sample_id)
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": "saea-entity-inventory-v1",
        "carrier_lock_key": carrier_lock_key,
        "sample_id": sample_id,
        "entity_count": len(mentions),
        "mentions": [mention_record(mention) for mention in mentions],
    }


def build_inventory(
    *,
    data_root: Path,
    lock: Mapping[str, object],
    carrier_lock_key: str,
    ids: list[str],
    out_dir: Path,
    workers: int,
    split_name: str,
) -> tuple[dict[str, object], Path, str]:
    out_dir.mkdir(parents=True, exist_ok=True)

    def _one(sample_id: str) -> tuple[str, dict[str, object] | None, str | None]:
        try:
            document = build_call_inventory(lock, data_root, carrier_lock_key, sample_id)
        except ReferenceError as error:
            return sample_id, None, str(error)
        return sample_id, document, None

    per_sample: dict[str, object] = {}
    failures: list[dict[str, object]] = []
    total_entities = 0

    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(workers, len(ids))) as pool:
        for sample_id, document, error in pool.map(_one, ids):
            if error is not None:
                failures.append({"sample_id": sample_id, "error": error})
                continue
            path = out_dir / f"{sample_id}.json"
            file_sha256 = write_json_artifact(path, document)
            per_sample[sample_id] = {
                "entity_count": document["entity_count"],
                "sha256": file_sha256,
                "bytes": path.stat().st_size,
            }
            total_entities += document["entity_count"]
    wall_seconds = time.monotonic() - start

    try:
        import resource

        peak_rss_mb: float | None = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except ImportError:
        peak_rss_mb = None

    calls_per_min = (len(ids) / wall_seconds * 60.0) if wall_seconds > 0 else None
    entities_per_min = (total_entities / wall_seconds * 60.0) if wall_seconds > 0 else None

    prefixed_ids = prefixed(carrier_lock_key, ids)
    manifest = {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": "saea-entity-inventory-manifest-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "carrier_lock_key": carrier_lock_key,
        "split": {
            "name": split_name,
            "ids": sorted(ids),
            "split_identity_hash": split_identity_hash(prefixed_ids),
            "convention": "slash (carrier_lock_key/id, sorted, LF-joined, sha256)",
        },
        "per_sample": per_sample,
        "failures": failures,
        "throughput": {
            "calls_per_min": calls_per_min,
            "entities_per_min": entities_per_min,
            "wall_seconds": wall_seconds,
            "workers": workers,
            "peak_rss_mb": peak_rss_mb,
        },
    }
    manifest_path = out_dir / "manifest.json"
    manifest_sha256 = write_json_artifact(manifest_path, manifest)
    return manifest, manifest_path, manifest_sha256


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ids-file", type=Path, default=DEFAULT_IDS_FILE)
    parser.add_argument("--carrier-lock-key", default=DEFAULT_CARRIER)
    parser.add_argument("--split-name", default=DEFAULT_SPLIT_NAME)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument(
        "--lock-path", type=Path, default=None, help="TEST-ONLY override of the umbrella lock path"
    )
    parser.add_argument(
        "--out-dir", type=Path, default=None, help="TEST-ONLY override of the output directory"
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    try:
        ids = load_ids(args.ids_file)
        lock_path = args.lock_path if args.lock_path else umbrella_lock_path(REPO_ROOT)
        lock = load_lock(lock_path)
    except EntityInventoryError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    out_dir = args.out_dir or (args.data_root / OUT_SUBDIR)
    manifest, manifest_path, manifest_sha256 = build_inventory(
        data_root=args.data_root,
        lock=lock,
        carrier_lock_key=args.carrier_lock_key,
        ids=ids,
        out_dir=out_dir,
        workers=args.workers,
        split_name=args.split_name,
    )

    failures = manifest["failures"]
    print(
        json.dumps(
            {
                "out_dir": str(out_dir),
                "manifest": str(manifest_path),
                "manifest_sha256": manifest_sha256,
                "covered": len(manifest["per_sample"]),
                "requested": len(ids),
                "failures": len(failures),
                "throughput": manifest["throughput"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if failures:
        print(f"REFUSED: {len(failures)} failure(s) -- see {manifest_path}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
