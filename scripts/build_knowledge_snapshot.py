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
    python scripts/build_knowledge_snapshot.py --size full --dimensions content --view slot-fillers

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

Why a second RENDERING exists (2026-09-07, cell KU-S3). Dropping ``content``
is only available to a cell that binds the snapshot without consuming it. A
cell that RECALLS on per-utterance content facets must bind them, and then the
same raw-utterance representations refuse its prompts -- measured on KU-S3's
own instruction, the exemplar view collides with 1,000 of 1,000 rows while its
VALUES collide with 0 of 1,000. ``--view slot-fillers`` quotes the utterance
inside a key descriptor (so the leakage rule tests a descriptor, never a bare
English phrase) and renders each value as that utterance's slot ``type=filler``
pairs alone. Same selection, same facet and value ids, same prior scores, same
provenance; two rendered strings differ, and the tier label says so.

Deterministic: re-running the same ``--size``/``--dimensions``/``--view`` against an
unchanged TRAIN corpus and unchanged decontamination receipts produces a
byte-identical governance receipt (sorted ids, fixed canonical JSON formatting
via ``e0.artifacts.write_json_artifact``, explicit UTF-8).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Sequence

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
    VIEW_EXEMPLAR,
    VIEW_SLOT_FILLERS,
    VIEW_ANNOTATED_EXEMPLARS,
    VALUE_FORMATS,
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


def _tier_label(
    size: int | None, dimensions: tuple[str, ...], view: str = VIEW_EXEMPLAR,
    value_format: str = "historical",
) -> str:
    """The artifact and receipt label for one build.

    The DEFAULT dimension set keeps the historical ``size-<N>`` label, so the
    three committed snapshots and their receipts are untouched. A restricted
    set gets its dimensions appended in sorted order
    (``size-full-label-prior-speaker``), because two snapshots over the same
    TRAIN rows with different dimensions are different artifacts and must
    never share a path. A non-default ``--view`` appends its own name last,
    for exactly the same reason: same rows, same dimensions, different
    rendered strings, different artifact.
    """

    label = _size_label(size)
    if tuple(dimensions) != tuple(KnowledgeBuildSpec.dimensions):
        label = "-".join((label, *sorted(dimensions)))
    if view != VIEW_EXEMPLAR:
        label = f"{label}-{view}"
    if value_format != "historical":
        label = f"{label}-{value_format}"
    return label


def freeze_split_identity(lock_path: Path | None = None) -> int:
    lock = load_lock(lock_path if lock_path is not None else umbrella_lock_path(REPO_ROOT))
    root = data_root()
    document = freeze_slurp_split_identity(lock, root)
    path = REPO_ROOT / SPLIT_IDENTITY_RECEIPT_RELPATH
    digest = write_json_artifact(path, document)
    print(f"wrote {path.relative_to(REPO_ROOT)}  sha256={digest[:16]}...")
    for split, block in document["splits"].items():
        print(f"  {split}: count={block['count']} identity_hash={block['identity_hash'][:16]}...")
    return 0


def _excluded_sample_ids(relpaths: Sequence[str]) -> tuple[frozenset[str], list[dict[str, object]]]:
    """The sample ids named by committed roster receipts, and their provenance.

    Used by ``--exclude-rosters``. Every excluded roster is recorded in the build
    receipt by relpath, file sha256 and count, so a reader can recompute exactly
    which TRAIN rows the snapshot was built WITHOUT.
    """

    excluded: set[str] = set()
    records: list[dict[str, object]] = []
    for relpath in relpaths:
        path = REPO_ROOT / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        ids = {str(item["sample_id"]) for item in document["items"]}
        excluded |= ids
        records.append(
            {
                "relpath": relpath,
                "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "roster_id": document.get("roster_id"),
                "split_identity_hash": document.get("split_identity_hash"),
                "count": len(ids),
            }
        )
    return frozenset(excluded), records


def build_one(
    size: int | None,
    dimensions: tuple[str, ...],
    *,
    view: str = VIEW_EXEMPLAR,
    value_format: str = "historical",
    exclude_rosters: Sequence[str] = (),
    tier_suffix: str = "",
    lock_path: Path | None = None,
) -> int:
    lock = load_lock(lock_path if lock_path is not None else umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start
    print(f"loaded {len(rows)} TRAIN utterances in {load_seconds:.2f}s")

    # ``--exclude-rosters``: drop the TRAIN utterances a committed roster claims
    # as its QUERY population. ``rails.runner.run_speech_native_agent_loop``
    # refuses any agent-loop run whose query samples overlap the snapshot's own
    # ``source_sample_ids`` -- the leakage rule that makes a snapshot worth
    # binding at all -- so a cell whose queries ARE train rows (every EVO fold)
    # needs a snapshot built without them. The dropped rows are recorded in the
    # receipt by roster relpath, file sha256 and count.
    excluded_ids, excluded_records = _excluded_sample_ids(exclude_rosters)
    if excluded_ids:
        before = len(rows)
        rows = tuple(
            row for row in rows if not (set(row.sample_ids) & excluded_ids)
        )
        print(
            f"excluded {before - len(rows)} TRAIN utterances named by "
            f"{len(excluded_records)} roster receipt(s); {len(rows)} remain"
        )

    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=size,
        seed=SEED,
        dimensions=tuple(dimensions),
        view=view,
        value_format=value_format,
    ).validate()
    tier = _tier_label(size, tuple(dimensions), view, value_format) + tier_suffix
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
            "view": spec.view,
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
            "excluded_rosters": excluded_records,
            "excluded_sample_count": len(excluded_ids),
        },
        "timing_seconds": {
            "load_train_rows": round(load_seconds, 3),
            "build_snapshot": round(build_seconds, 3),
            "coverage_report": round(report_seconds, 3),
        },
    }
    if value_format != "historical":
        receipt["spec"]["value_format"] = value_format
        receipt["value_format_authority"] = (
            "docs/superpowers/plans/experiment-handoff/OWNER-KNOWLEDGE-VALUE-DESIGN-018.md"
        )
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
        "--lock-path", type=Path,
        help="explicit umbrella datasets lock for an isolated worktree; default uses adjacent layout",
    )
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
    parser.add_argument(
        "--view",
        choices=(VIEW_EXEMPLAR, VIEW_SLOT_FILLERS, VIEW_ANNOTATED_EXEMPLARS),
        default=VIEW_EXEMPLAR,
        help=(
            "how content facets and values RENDER. 'exemplar' (default) is what every "
            "committed snapshot carries. 'slot-fillers' quotes the utterance inside a "
            "key descriptor and renders each value as that utterance's slot type=filler "
            "pairs alone; it requires the 'content' dimension and writes to "
            "size-<...>-slot-fillers. 'annotated-exemplars' quotes the utterance the same "
            "way and renders each value as '<utterance> | <scenario>_<action> | "
            "type=filler; ...' (or '| none'); it also requires 'content' and writes to "
            "size-<...>-annotated-exemplars"
        ),
    )
    parser.add_argument(
        "--value-format", choices=VALUE_FORMATS, default="historical",
        help="value-only representation; nonhistorical modes require --view slot-fillers",
    )
    parser.add_argument(
        "--exclude-rosters",
        default=None,
        help=(
            "comma-separated committed roster receipt relpaths whose sample ids are "
            "DROPPED from the TRAIN source before the snapshot is built. Needed by any "
            "cell whose agent-loop QUERIES are train rows: rails.runner refuses a run "
            "whose query samples overlap the snapshot's source_sample_ids"
        ),
    )
    parser.add_argument(
        "--tier-suffix",
        default=None,
        help="appended to the tier label, so a restricted source never shares a path",
    )
    args = parser.parse_args()
    if args.freeze_split_identity:
        return freeze_split_identity(lock_path=args.lock_path)
    if args.size is None:
        parser.error("pass --size <N|full> or --freeze-split-identity")
    return build_one(
        _parse_size(args.size),
        tuple(args.dimensions),
        view=str(args.view),
        value_format=str(args.value_format),
        exclude_rosters=tuple(
            item.strip() for item in str(args.exclude_rosters or "").split(",") if item.strip()
        ),
        tier_suffix=str(args.tier_suffix or ""),
        lock_path=args.lock_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
