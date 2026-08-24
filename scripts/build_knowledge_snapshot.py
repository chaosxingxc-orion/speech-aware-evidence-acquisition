#!/usr/bin/env python3
"""CLI: build one KB-BUILD v1 TRAIN knowledge snapshot + coverage report +
decontamination receipt (work item C1, owner-approved 2026-08-23 knowledge-
plane baseline program; authority
``docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md`` sections 1
and 5).

MODEL-FREE: text facets and metadata only -- no embeddings, no model
contacts anywhere in this script or in ``rails.knowledge_build``, the module
this script drives.

Usage::

    python scripts/build_knowledge_snapshot.py --freeze-split-identity
    python scripts/build_knowledge_snapshot.py --size 1000
    python scripts/build_knowledge_snapshot.py --size 5000
    python scripts/build_knowledge_snapshot.py --size full

Artifacts::

    $SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-<N>/snapshot.json
    docs/receipts/knowledge/slurp-kb-size-<N>.json
    docs/receipts/knowledge/slurp-split-identity.json   (--freeze-split-identity only)

Deterministic: re-running the same ``--size`` against an unchanged TRAIN
corpus and unchanged decontamination receipts produces a byte-identical
governance receipt (sorted ids, fixed canonical JSON formatting via
``e0.artifacts.write_json_artifact``, explicit UTF-8).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_build import (  # noqa: E402
    KB_BUILD_POLICY_ID,
    SPLIT_IDENTITY_RECEIPT_RELPATH,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
    coverage_report,
    freeze_slurp_split_identity,
    slurp_kb_rows,
)

AUTHORITY = "docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md sections 1 and 5"
SEED = 20260823
RECEIPTS_DIR = REPO_ROOT / "docs" / "receipts" / "knowledge"
_FORBIDDEN_ROSTER_RECEIPTS = (
    SPLIT_IDENTITY_RECEIPT_RELPATH,
    "docs/receipts/probe-samples/FINAL60.json",
    "docs/receipts/probe-samples/DEV-100.json",
    "docs/receipts/probe-samples/DEV-500.json",
    "docs/receipts/probe-samples/DEV-1000.json",
)


def _parse_size(raw: str) -> int | None:
    if raw == "full":
        return None
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"--size must be a positive int or 'full', got {raw!r}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("--size must be a positive int or 'full'")
    return value


def _size_label(size: int | None) -> str:
    return "full" if size is None else str(size)


def freeze_split_identity() -> int:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    document = freeze_slurp_split_identity(lock, root)
    path = REPO_ROOT / SPLIT_IDENTITY_RECEIPT_RELPATH
    digest = write_json_artifact(path, document)
    print(f"wrote {path.relative_to(REPO_ROOT)}  sha256={digest[:16]}...")
    for split, block in document["splits"].items():
        print(f"  {split}: count={block['count']} identity_hash={block['identity_hash'][:16]}...")
    return 0


def build_one(size: int | None) -> int:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start
    print(f"loaded {len(rows)} TRAIN utterances in {load_seconds:.2f}s")

    spec = KnowledgeBuildSpec(carrier_lock_key="slurp", datastore_size=size, seed=SEED)
    build_start = time.monotonic()
    snapshot = build_knowledge_snapshot(
        spec, lock=lock, root=root, rows=rows, repo_root=REPO_ROOT
    )
    build_seconds = time.monotonic() - build_start
    print(
        f"built snapshot {snapshot.snapshot_id} "
        f"facets={len(snapshot.facets)} values={len(snapshot.values)} in {build_seconds:.2f}s"
    )

    report_start = time.monotonic()
    report = coverage_report(snapshot, rows)
    report_seconds = time.monotonic() - report_start

    frozen = snapshot.frozen_json()
    snapshot_sha256 = frozen["snapshot_sha256"]
    snapshot_path = (
        root
        / "knowledge"
        / "slurp"
        / KB_BUILD_POLICY_ID
        / f"size-{_size_label(size)}"
        / "snapshot.json"
    )
    write_json_artifact(snapshot_path, frozen)
    print(f"wrote {snapshot_path}  snapshot_sha256={snapshot_sha256[:16]}...")

    receipt = {
        "schema": "saea-kb-build-receipt-v1",
        "generator": "scripts/build_knowledge_snapshot.py",
        "authority": AUTHORITY,
        "builder_policy_id": KB_BUILD_POLICY_ID,
        "spec": {
            "carrier_lock_key": spec.carrier_lock_key,
            "datastore_size": spec.datastore_size,
            "seed": spec.seed,
            "dimensions": list(spec.dimensions),
        },
        "snapshot_sha256": snapshot_sha256,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_artifact_relpath": str(snapshot_path.relative_to(root)),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "coverage_report": report,
        "decontamination": {
            "verdict": "clean",
            "checked_sample_count": len(snapshot.source_sample_ids),
            "forbidden_roster_receipts": list(_FORBIDDEN_ROSTER_RECEIPTS),
        },
        "timing_seconds": {
            "load_train_rows": round(load_seconds, 3),
            "build_snapshot": round(build_seconds, 3),
            "coverage_report": round(report_seconds, 3),
        },
    }
    receipt_path = RECEIPTS_DIR / f"slurp-kb-size-{_size_label(size)}.json"
    receipt_sha256 = write_json_artifact(receipt_path, receipt)
    print(f"wrote {receipt_path.relative_to(REPO_ROOT)}  sha256={receipt_sha256[:16]}...")
    print(
        f"  intent_coverage={report['intent_coverage']:.4f} "
        f"entity_type_coverage={report['entity_type_coverage']:.4f} "
        f"long_tail_intent_coverage={report['long_tail_coverage']['intent']['coverage']:.4f} "
        f"kl={report['kl_selected_given_train_over_intent']:.6f}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze-split-identity",
        action="store_true",
        help="freeze docs/receipts/knowledge/slurp-split-identity.json and exit",
    )
    parser.add_argument("--size", type=str, default=None, help="positive int datastore size, or 'full'")
    args = parser.parse_args()
    if args.freeze_split_identity:
        return freeze_split_identity()
    if args.size is None:
        parser.error("pass --size <N|full> or --freeze-split-identity")
    return build_one(_parse_size(args.size))


if __name__ == "__main__":
    raise SystemExit(main())
