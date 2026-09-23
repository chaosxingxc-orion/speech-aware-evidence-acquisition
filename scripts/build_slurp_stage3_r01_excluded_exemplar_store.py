#!/usr/bin/env python3
"""CLI: build the R01-excluded ``train-exemplars`` knowledge store (Stage-3 S3-2).

Why this exists. Cell ROLL-1 flies the 800-row TRAIN construction roster
``SLURP-STAGE3-CONSTRUCTION-R01`` as its AgentLoop QUERY population, and
``rails.runner.run_speech_native_agent_loop`` refuses any run whose query
samples intersect the bound snapshot's own ``source_sample_ids``::

    AgentLoop query samples overlap the TRAIN knowledge source roster: [...]

The released ``train-exemplars`` store
(``knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars``) is
built over the whole 9,354-utterance construction pool, and R01 was drawn
from exactly that pool, so all 800 query rows are also knowledge source
rows. This script rebuilds the same store over the same pool MINUS every
utterance that has a recording in R01 -- the ``--exclude-rosters``
mechanism of ``scripts/build_knowledge_snapshot.py``, applied at the fixed
store path scheme of ``scripts/build_slurp_exemplar_pool_assets.py``.

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
encoder, tokenizer, scorer, GPU or network contact. The build is a pure
SELECTION over TRAIN metadata already sealed on the data root; every facet,
value, prior score and provenance ref of a surviving utterance is
bit-identical to the parent store's. The sealed KU-S3 content facet-vector
file stays pinned unchanged, and this script proves by membership that it is
still a strict superset of the smaller snapshot's facet ids (no filtered
derivative is needed either way, because ``rails.kb_policy.multidim_recall``
looks a facet's vector up with ``.get(...)`` and skips a miss).

Artifacts::

    $SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/
        size-pool-annotated-exemplars-minus-r01/snapshot.json
    $SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/
        size-pool-annotated-exemplars-minus-r01/release.json
    docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars-minus-r01.json

Deterministic: re-running against an unchanged TRAIN corpus and unchanged
roster receipts reproduces every byte.

Usage::

    python scripts/build_slurp_stage3_r01_excluded_exemplar_store.py
    python scripts/build_slurp_stage3_r01_excluded_exemplar_store.py --check
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

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_build import (  # noqa: E402
    KB_BUILD_POLICY_ID,
    VIEW_ANNOTATED_EXEMPLARS,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
    coverage_report,
    slurp_kb_rows,
)

AUTHORITY = (
    "docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md item S3-2 "
    "(cell ROLL-1); rails.runner.run_speech_native_agent_loop BUILD/USE disjointness rule"
)
SEED = 20260823
TIER = "pool-annotated-exemplars-minus-r01"
PARENT_TIER = "pool-annotated-exemplars"
SNAPSHOT_RELDIR = Path("knowledge") / "slurp" / KB_BUILD_POLICY_ID / f"size-{TIER}"
PARENT_SNAPSHOT_RELDIR = Path("knowledge") / "slurp" / KB_BUILD_POLICY_ID / f"size-{PARENT_TIER}"
RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "knowledge" / f"slurp-kb-size-{TIER}.json"
PARENT_RECEIPT_RELPATH = f"docs/receipts/knowledge/slurp-kb-size-{PARENT_TIER}.json"

# The 2026-09-13 pool exclusion (Fold A, Fold B, DEV-1000 -- identical to
# scripts/build_slurp_exemplar_pool_assets.py, so the surviving rows stay a
# strict subset of the released parent store), PLUS the S3-1 construction
# roster whose 800 recordings are cell ROLL-1's own query population.
EXCLUDE_ROSTER_RELPATHS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
    "docs/receipts/rosters/slurp-stage3-construction-r01.json",
)
R01_ROSTER_RELPATH = "docs/receipts/rosters/slurp-stage3-construction-r01.json"

#: The parent pool (before the R01 exclusion) and its identity, asserted so a
#: drifted corpus or a rewritten roster cannot silently publish a different
#: store under this name.
PARENT_UTTERANCE_COUNT = 9354
PARENT_SOURCE_SPLIT_IDENTITY_HASH = (
    "22f6092dfdb4a160376e529d8e59e9215bc7701e274620d35feb1c4d82f309e9"
)
EXPECTED_UTTERANCE_COUNT = 8554

FACET_VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
FACET_VECTORS_SHA256 = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"

TRAIN_METADATA_RELPATH = "datasets/slurp/metadata/train.jsonl"
STORE_ID = "train-exemplars"
STORE_ROLE = "train-exemplars"
RELEASE_SCHEMA = "saea-knowledge-store-release-v1"

LEDGER_ROW = "SAEA-SLURP-STAGE3-R01-EXCLUDED-EXEMPLAR-STORE-V1"


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _roster_sample_ids(relpath: str) -> frozenset[str]:
    """Every sample id a committed roster receipt claims.

    Roster item shapes differ: construction rosters carry ``sample_id``, the
    DEV-1000 probe roster carries ``id`` only.
    """

    document = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    return frozenset(
        str(item["sample_id"] if "sample_id" in item else item["id"])
        for item in document["items"]
    )


def _excluded_sample_ids() -> tuple[frozenset[str], list[dict[str, object]]]:
    excluded: set[str] = set()
    records: list[dict[str, object]] = []
    for relpath in EXCLUDE_ROSTER_RELPATHS:
        path = REPO_ROOT / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        ids = _roster_sample_ids(relpath)
        before = len(excluded)
        excluded |= set(ids)
        records.append(
            {
                "relpath": relpath,
                "file_sha256": _sha256_path(path),
                "roster_id": document.get("roster_id"),
                "split_identity_hash": document.get("split_identity_hash"),
                "count": len(ids),
                "new_exclusions": len(excluded) - before,
            }
        )
    return frozenset(excluded), records


def _parent_source_sample_ids(root: Path) -> frozenset[str]:
    path = root / PARENT_SNAPSHOT_RELDIR / "snapshot.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    return frozenset(str(item) for item in document["source_sample_ids"])


def build_store(*, check: bool) -> dict[str, object]:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start

    excluded_ids, excluded_records = _excluded_sample_ids()
    r01_ids = _roster_sample_ids(R01_ROSTER_RELPATH)
    pool_only = excluded_ids - r01_ids
    parent_rows = tuple(row for row in rows if not (set(row.sample_ids) & pool_only))
    kept = tuple(row for row in rows if not (set(row.sample_ids) & excluded_ids))
    print(
        f"loaded {len(rows)} governed TRAIN utterances in {load_seconds:.2f}s; "
        f"parent pool {len(parent_rows)}; R01 removes {len(parent_rows) - len(kept)} "
        f"utterance(s); {len(kept)} remain"
    )
    if len(parent_rows) != PARENT_UTTERANCE_COUNT:
        raise SystemExit(
            f"parent construction pool carries {len(parent_rows)} utterances, not the "
            f"registered {PARENT_UTTERANCE_COUNT} ({PARENT_RECEIPT_RELPATH})"
        )
    if len(kept) != EXPECTED_UTTERANCE_COUNT:
        raise SystemExit(
            f"R01-excluded pool carries {len(kept)} utterances, not the expected "
            f"{EXPECTED_UTTERANCE_COUNT}"
        )

    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=None,
        seed=SEED,
        dimensions=("content",),
        view=VIEW_ANNOTATED_EXEMPLARS,
    ).validate()

    build_start = time.monotonic()
    snapshot = build_knowledge_snapshot(
        spec, lock=lock, root=root, rows=kept, repo_root=REPO_ROOT
    )
    build_seconds = time.monotonic() - build_start
    print(
        f"built snapshot {snapshot.snapshot_id} facets={len(snapshot.facets)} "
        f"values={len(snapshot.values)} in {build_seconds:.2f}s"
    )

    source_ids = frozenset(snapshot.source_sample_ids)
    overlap = source_ids & r01_ids
    if overlap:
        raise SystemExit(
            f"{len(overlap)} R01 recording(s) survived the exclusion, e.g. "
            f"{sorted(overlap)[:3]}"
        )
    if not source_ids < _parent_source_sample_ids(root):
        raise SystemExit(
            "the R01-excluded source roster is not a strict subset of the released "
            "parent store source roster"
        )
    if snapshot.source_split_identity_hash == PARENT_SOURCE_SPLIT_IDENTITY_HASH:
        raise SystemExit(
            "the R01-excluded store reproduces the parent source split identity; "
            "the exclusion did not take effect"
        )

    report_start = time.monotonic()
    report = coverage_report(snapshot, kept)
    report_seconds = time.monotonic() - report_start

    frozen = snapshot.frozen_json()
    snapshot_sha256 = frozen["snapshot_sha256"]
    snapshot_path = root / SNAPSHOT_RELDIR / "snapshot.json"

    release = {
        "schema": RELEASE_SCHEMA,
        "store_id": STORE_ID,
        "store_role": STORE_ROLE,
        "snapshot_sha256": snapshot_sha256,
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "builder_policy_id": snapshot.builder_policy_id,
        "source": {
            "relpath": TRAIN_METADATA_RELPATH,
            "sha256": _sha256_path(root / TRAIN_METADATA_RELPATH),
        },
    }
    release_path = root / SNAPSHOT_RELDIR / "release.json"

    if not check:
        snapshot_file_sha256 = write_json_artifact(snapshot_path, frozen)
        print(
            f"wrote {snapshot_path}  snapshot_sha256={snapshot_sha256[:16]}...  "
            f"file_sha256={snapshot_file_sha256[:16]}..."
        )
        release_file_sha256 = write_json_artifact(release_path, release)
        print(f"wrote {release_path}  file_sha256={release_file_sha256[:16]}...")
    else:
        snapshot_file_sha256 = None
        release_file_sha256 = None
        print(
            f"(check) snapshot would be {snapshot_path}  "
            f"snapshot_sha256={snapshot_sha256[:16]}..."
        )

    receipt = {
        "schema": "saea-kb-build-receipt-v1",
        "generator": "scripts/build_slurp_stage3_r01_excluded_exemplar_store.py",
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
        "release_artifact_relpath": str(release_path.relative_to(root)),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "coverage_report": report,
        "parent_store": {
            "receipt_relpath": PARENT_RECEIPT_RELPATH,
            "receipt_sha256": _sha256_path(REPO_ROOT / PARENT_RECEIPT_RELPATH),
            "snapshot_relpath": (PARENT_SNAPSHOT_RELDIR / "snapshot.json").as_posix(),
            "source_split_identity_hash": PARENT_SOURCE_SPLIT_IDENTITY_HASH,
            "utterance_count": PARENT_UTTERANCE_COUNT,
            "relation": (
                "strict subset: every surviving facet, value, prior score and "
                "provenance ref is bit-identical to the parent; only the R01 "
                "utterances are absent"
            ),
        },
        "decontamination": {
            "verdict": "clean",
            "checked_sample_count": len(snapshot.source_sample_ids),
            "excluded_rosters": excluded_records,
            "excluded_sample_count": len(excluded_ids),
            "query_roster_overlap": 0,
            "exclusion_authority": (
                "docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json "
                "(pool exclusion) plus docs/receipts/rosters/"
                "slurp-stage3-construction-r01.json (cell ROLL-1 query population)"
            ),
        },
        "timing_seconds": {
            "load_train_rows": round(load_seconds, 3),
            "build_snapshot": round(build_seconds, 3),
            "coverage_report": round(report_seconds, 3),
        },
        "exposure_ledger_row": LEDGER_ROW,
        "execution_profile": "model-free-check",
        "contacts": {
            "model": 0,
            "tool": 0,
            "scorer": 0,
            "encoder": 0,
            "tokenizer": 0,
            "gpu": 0,
        },
    }
    if snapshot_file_sha256 is not None:
        receipt["snapshot_file_sha256"] = snapshot_file_sha256
        receipt["release_file_sha256"] = release_file_sha256
    if not check:
        receipt_sha256 = write_json_artifact(RECEIPT_PATH, receipt)
        print(
            f"wrote {RECEIPT_PATH.relative_to(REPO_ROOT)}  "
            f"sha256={receipt_sha256[:16]}..."
        )
    return {
        "snapshot": snapshot,
        "snapshot_sha256": snapshot_sha256,
        "snapshot_file_sha256": snapshot_file_sha256,
        "release": release,
        "release_file_sha256": release_file_sha256,
        "snapshot_relpath": str(snapshot_path.relative_to(root)),
        "release_relpath": str(release_path.relative_to(root)),
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "utterance_count": len(kept),
    }


def check_facet_vector_coverage(root: Path, snapshot) -> None:
    """The sealed KU-S3 facet vectors still cover every surviving facet id."""

    path = root / FACET_VECTORS_RELPATH
    measured = _sha256_path(path)
    if measured != FACET_VECTORS_SHA256:
        raise SystemExit(
            f"{path} hashes to {measured}, not the pinned {FACET_VECTORS_SHA256}"
        )
    vector_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            vector_ids.add(json.loads(line)["id"])
    facet_ids = {facet.facet_id for facet in snapshot.facets}
    missing = facet_ids - vector_ids
    print(
        f"facet-vector coverage: sealed file carries {len(vector_ids)} ids "
        f"({FACET_VECTORS_RELPATH}); snapshot needs {len(facet_ids)}; "
        f"missing={len(missing)}"
    )
    if missing:
        raise SystemExit(
            f"{len(missing)} snapshot facet id(s) have no sealed vector, e.g. "
            f"{sorted(missing)[:3]}"
        )
    print(
        "NO facet-vector derivative is needed: the sealed file stays a strict superset "
        f"of this snapshot content facets, so facet_source stays "
        f"{FACET_VECTORS_RELPATH} unchanged."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args()

    root = data_root()
    result = build_store(check=args.check)
    check_facet_vector_coverage(root, result["snapshot"])

    print("---")
    print(f"utterance_count={result['utterance_count']}")
    print(f"snapshot_relpath={result['snapshot_relpath']}")
    print(f"snapshot_sha256={result['snapshot_sha256']}")
    print(f"snapshot_file_sha256={result['snapshot_file_sha256']}")
    print(f"release_relpath={result['release_relpath']}")
    print(f"release_file_sha256={result['release_file_sha256']}")
    print(f"facet_count={result['facet_count']} value_count={result['value_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
