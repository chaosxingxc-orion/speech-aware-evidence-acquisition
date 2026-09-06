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
    python scripts/build_knowledge_snapshot.py --size full --dimensions label,speaker,prior

Artifacts::

    $SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/size-<tier>/snapshot.json
    docs/receipts/knowledge/slurp-kb-size-<tier>.json
    docs/receipts/knowledge/slurp-split-identity.json   (--freeze-split-identity only)

``<tier>`` is the size label alone for the DEFAULT dimension set (so the three
committed snapshots keep their paths) and ``<size>-<sorted dimensions>`` for a
restricted one.

Why a restricted dimension set exists (2026-09-05, KC-S1a/b). Every phase
program binds a frozen snapshot even when all its phases declare
``knowledge: "none"``, because ``rails.runner.run_speech_native_agent_loop``
requires one; the snapshot is what
``_assert_agent_control_excludes_knowledge_payloads`` enforces its leakage rule
against. The ``content`` dimension carries one facet per TRAIN utterance whose
representation is that utterance's raw text, and 11,514 SLURP utterances
include one-word and two-word ones -- ``calendar``, ``shopping``,
``how much`` -- so the rule's raw substring test over payloads of eight
characters or more makes SLURP's own scenario names, and ordinary English,
unsendable in a phase instruction. Dropping ``content`` (``KnowledgeBuildSpec.
validate`` explicitly allows any set containing ``content`` OR ``label``)
leaves the leakage rule at full strength over every exemplar value and every
label, speaker and prior facet -- 11,863 protected payloads -- while removing
the raw-utterance layer that produced the collisions.

Deterministic: re-running the same ``--size``/``--dimensions`` against an
unchanged TRAIN corpus and unchanged decontamination receipts produces a
byte-identical governance receipt (sorted ids, fixed canonical JSON formatting
via ``e0.artifacts.write_json_artifact``, explicit UTF-8).
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


def _parse_dimensions(raw: str) -> tuple[str, ...]:
    names = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not names:
        raise argparse.ArgumentTypeError("--dimensions must name at least one dimension")
    if len(set(names)) != len(names):
        raise argparse.ArgumentTypeError(f"--dimensions repeats a name: {raw!r}")
    return names


def _tier_label(size: int | None, dimensions: tuple[str, ...]) -> str:
    """The artifact and receipt label for one build.

    The DEFAULT dimension set keeps the historical ``size-<N>`` label, so the
    three committed snapshots and their receipts are untouched. A restricted
    set gets its dimensions appended in sorted order
    (``size-full-label-prior-speaker``), because two snapshots over the same
    TRAIN rows with different dimensions are different artifacts and must
    never share a path.
    """

    label = _size_label(size)
    if tuple(dimensions) == tuple(KnowledgeBuildSpec.dimensions):
        return label
    return "-".join((label, *sorted(dimensions)))


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


def build_one(size: int | None, dimensions: tuple[str, ...]) -> int:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start
    print(f"loaded {len(rows)} TRAIN utterances in {load_seconds:.2f}s")

    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=size,
        seed=SEED,
        dimensions=tuple(dimensions),
    ).validate()
    tier = _tier_label(size, tuple(dimensions))
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
        / f"size-{tier}"
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
    receipt_path = RECEIPTS_DIR / f"slurp-kb-size-{tier}.json"
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
    parser.add_argument(
        "--dimensions",
        type=_parse_dimensions,
        default=KnowledgeBuildSpec.dimensions,
        help=(
            "comma-separated KB dimensions (default: "
            + ",".join(KnowledgeBuildSpec.dimensions)
            + "). A restricted set writes to size-<N>-<sorted dimensions>."
        ),
    )
    args = parser.parse_args()
    if args.freeze_split_identity:
        return freeze_split_identity()
    if args.size is None:
        parser.error("pass --size <N|full> or --freeze-split-identity")
    return build_one(_parse_size(args.size), tuple(args.dimensions))


if __name__ == "__main__":
    raise SystemExit(main())
