#!/usr/bin/env python3
"""CLI: build the EMPTY-CONTRACT ``train-exemplars`` knowledge store.

Release name ``train-exemplars-with-empty-v1``; store path
``knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-empty-contract-v1``.

WHY THIS EXISTS, and what it is NOT.

The 2026-09-24 bad-case bank (``docs/results/2026-09-24-slurp-plan-bad-case-bank.md``
section 1e) reports that the released ``train-exemplars`` pool holds "0
entity-free values out of 9,354" while 38.3 % (TRAIN Fold A) / 31.4 %
(DEV-2000-ADDED) of roster rows carry no gold entity, and that 41.5 % / 48.4 %
of those empty-gold rows emit an entity anyway (the ENTITY-FP-ONLY mass, worth
+4.76 / +3.47 pp of pooled official SLU).

THE HEADROOM IS REAL; THE COMPOSITION NUMBER IS NOT. The released snapshot
carries 2,949 entity-free values of 9,354 (31.5 %). The bank's own parser
(``scripts/analysis/slurp_plan_bad_case_bank.py::load_exemplar_labels``)
splits the raw line's third field on ``;`` and keeps the text before ``=``, so
an entity-free line -- rendered ``<utterance> | <scenario>_<action> | none`` --
yields one "entity type" named ``none`` and lands in the 1-entity bucket. That
is why the bank's spread starts at 1 and its 0-bucket is empty. This builder
re-measures the real composition and records it.

So the supply is NOT missing the empty CASE. What it never shows is the
correct empty ANSWER: ``none`` is an English word that occurs in no legal
Solver response, while the Solver's own contract
(``configs/probes/slurp_native_role_solver_v2.txt``) requires
``{"scenario":"...","action":"...","entities":[]}`` and says so in words
("If no entity is expressed, return an empty entities array"). Module M1's
admitted gain was convention transfer from the raw line; this store extends
exactly that mechanism to the empty case by rendering those 2,949 lines'
third field as the literal ``"entities":[]`` the Solver would itself emit.

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
encoder, tokenizer, scorer, GPU or network contact. Every byte read was
produced by an earlier, already-paid pass. The selection is IDENTICAL to the
released parent store -- same three exclusion rosters, same 9,354 utterances,
same ``source_split_identity_hash`` -- and the script asserts all three
against the parent before it writes anything.

The relation to the parent is asserted, not asserted-and-hoped:

* every facet is byte-identical (id, dimension, representation kind and text,
  source sample ids, parent facet ids) -- the RETRIEVAL KEY SIDE DOES NOT
  MOVE, so the sealed KU-S3 facet vectors keep binding by id;
* every value keeps its id, ``prior_score``, ``task_target``, associated
  facet ids and provenance refs;
* every ENTITY-BEARING value's content is byte-identical;
* exactly the ENTITY-FREE values' content differs, in the third field alone.

Artifacts::

    <out-root>/knowledge/slurp/saea-kb-distmodel-v1/
        size-pool-annotated-exemplars-empty-contract-v1/snapshot.json
    <out-root>/knowledge/slurp/saea-kb-distmodel-v1/
        size-pool-annotated-exemplars-empty-contract-v1/release.json
    docs/receipts/knowledge/
        slurp-kb-size-pool-annotated-exemplars-empty-contract-v1.json

``--out-root`` defaults to ``$SPEECHRL_DATA_DIR``; a scratch directory makes
the run a rehearsal that can never touch the controlled data root.

Deterministic: re-running against an unchanged TRAIN corpus and unchanged
roster receipts reproduces every byte.

Usage::

    python scripts/build_slurp_train_exemplars_with_empty_store.py
    python scripts/build_slurp_train_exemplars_with_empty_store.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
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
    SOLVER_EMPTY_ENTITY_LIST_FORM,
    VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
    coverage_report,
    slurp_kb_rows,
)

AUTHORITY = (
    "docs/results/2026-09-24-slurp-plan-bad-case-bank.md section 1e (the ENTITY-FP-ONLY "
    "mass on empty-gold rows); configs/probes/slurp_native_role_solver_v2.txt (the "
    "Solver output contract whose empty form this store demonstrates); "
    "docs/readiness/2026-09-24-slurp-train-exemplars-with-empty-v1/README.md"
)
SEED = 20260823
TIER = "pool-annotated-exemplars-empty-contract-v1"
PARENT_TIER = "pool-annotated-exemplars"
SNAPSHOT_RELDIR = Path("knowledge") / "slurp" / KB_BUILD_POLICY_ID / f"size-{TIER}"
PARENT_SNAPSHOT_RELDIR = Path("knowledge") / "slurp" / KB_BUILD_POLICY_ID / f"size-{PARENT_TIER}"
RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "knowledge" / f"slurp-kb-size-{TIER}.json"
PARENT_RECEIPT_RELPATH = f"docs/receipts/knowledge/slurp-kb-size-{PARENT_TIER}.json"

# The 2026-09-13 pool exclusion, byte-for-byte the tuple
# scripts/build_slurp_exemplar_pool_assets.py uses: every utterance with a
# recording in TRAIN Fold A, TRAIN Fold B or the DEV-1000 probe roster is
# dropped from the construction pool BEFORE selection. Nothing is added and
# nothing is removed here -- a changed exclusion would make this a different
# store rather than a different RENDERING of the same one.
EXCLUDE_ROSTER_RELPATHS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
)
EXPECTED_UTTERANCE_COUNT = 9354
EXPECTED_SOURCE_SPLIT_IDENTITY_HASH = (
    "22f6092dfdb4a160376e529d8e59e9215bc7701e274620d35feb1c4d82f309e9"
)
PARENT_SNAPSHOT_SHA256 = "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"

FACET_VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
FACET_VECTORS_SHA256 = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"

TRAIN_METADATA_RELPATH = "datasets/slurp/metadata/train.jsonl"
#: The config key and the release identity stay ``train-exemplars``. A variant
#: cell RE-PINS the existing block rather than adding a second store, because
#: ``rails.knowledge_stores.load_knowledge_store_binding`` requires
#: ``release.store_id`` to equal the ``knowledge_stores`` key, and every
#: exemplar evidence id in the harness is prefixed ``train-exemplars::value:``
#: (``rails.knowledge_index.EXEMPLAR_EVIDENCE_PREFIX``). A distinct id would
#: change every one of those strings and turn a one-factor construction
#: variant into a wiring change.
STORE_ID = "train-exemplars"
STORE_ROLE = "train-exemplars"
RELEASE_NAME = "train-exemplars-with-empty-v1"
RELEASE_SCHEMA = "saea-knowledge-store-release-v1"

LEDGER_ROW = "SAEA-SLURP-TRAIN-EXEMPLARS-WITH-EMPTY-BUILD-V1"

#: The raw line's field separator, and the index of the entity field.
FIELD_SEPARATOR = " | "
ENTITY_FIELD_INDEX = 2
PARENT_EMPTY_FORM = "none"


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _excluded_sample_ids() -> tuple[frozenset[str], list[dict[str, object]]]:
    """The union of the three pool-exclusion rosters, with a receipt row each.

    Roster item shapes differ: the construction folds carry ``sample_id``, the
    DEV-1000 probe roster carries ``id`` only.
    """

    excluded: set[str] = set()
    records: list[dict[str, object]] = []
    for relpath in EXCLUDE_ROSTER_RELPATHS:
        path = REPO_ROOT / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        ids = {
            str(item["sample_id"] if "sample_id" in item else item["id"])
            for item in document["items"]
        }
        before = len(excluded)
        excluded |= ids
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


def _load_parent_snapshot(root: Path) -> dict[str, object]:
    path = root / PARENT_SNAPSHOT_RELDIR / "snapshot.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    declared = document.get("snapshot_sha256")
    if declared != PARENT_SNAPSHOT_SHA256:
        raise SystemExit(
            f"parent snapshot declares {declared}, not the pinned {PARENT_SNAPSHOT_SHA256}"
        )
    return document


def entity_free_value_ids(rows) -> frozenset[str]:
    """The value ids of the utterances that carry NO entity annotation.

    Taken from the governed rows, never from parsing a rendered line: a
    filler is arbitrary speech surface and must never be trusted to tell a
    field boundary apart from its own content.
    """

    return frozenset(f"value:{row.utterance_id}" for row in rows if not row.entity_fillers)


def assert_parent_relation(snapshot, parent, *, empty_ids) -> dict[str, object]:
    """Every difference from the released parent, enumerated and bounded.

    Returns the difference report. Raises if anything moves that must not: a
    facet, an id, a prior score, a provenance ref, an association, or the
    content of an entity-BEARING value; or if an entity-free value changed by
    anything other than its trailing empty-form field.
    """

    parent_facets = {facet["facet_id"]: facet for facet in parent["facets"]}
    if set(parent_facets) != {facet.facet_id for facet in snapshot.facets}:
        raise SystemExit("facet id sets differ from the released parent store")
    for facet in snapshot.facets:
        other = parent_facets[facet.facet_id]
        if (
            other.get("dimension") != facet.dimension
            or other.get("representation_kind") != facet.representation_kind
            or other.get("representation") != facet.representation
            or tuple(other.get("source_sample_ids", ())) != facet.source_sample_ids
            or tuple(other.get("parent_facet_ids", ())) != facet.parent_facet_ids
        ):
            raise SystemExit(
                f"facet {facet.facet_id} is not byte-identical to the released parent"
            )

    parent_values = {value["value_id"]: value for value in parent["values"]}
    if set(parent_values) != {value.value_id for value in snapshot.values}:
        raise SystemExit("value id sets differ from the released parent store")
    if not empty_ids <= set(parent_values):
        raise SystemExit("an entity-free value id is absent from the released parent")

    identical = 0
    changed = 0
    parent_suffix = FIELD_SEPARATOR + PARENT_EMPTY_FORM
    own_suffix = FIELD_SEPARATOR + SOLVER_EMPTY_ENTITY_LIST_FORM
    for value in snapshot.values:
        other = parent_values[value.value_id]
        if (
            other.get("prior_score") != value.prior_score
            or other.get("task_target") != value.task_target
            or tuple(other.get("associated_facet_ids", ())) != value.associated_facet_ids
            or tuple(other.get("source_sample_ids", ())) != value.source_sample_ids
            or tuple(other.get("provenance_refs", ())) != value.provenance_refs
        ):
            raise SystemExit(
                f"value {value.value_id} moved an id, a prior score or a provenance ref"
            )
        parent_content = other.get("content")
        if value.value_id not in empty_ids:
            if parent_content != value.content:
                raise SystemExit(
                    f"value {value.value_id} carries entities and its content changed"
                )
            identical += 1
            continue
        if not parent_content.endswith(parent_suffix):
            raise SystemExit(
                f"value {value.value_id} is entity-free but the parent line does not end "
                f"in the parent empty form"
            )
        expected = parent_content[: -len(PARENT_EMPTY_FORM)] + SOLVER_EMPTY_ENTITY_LIST_FORM
        if value.content != expected or not value.content.endswith(own_suffix):
            raise SystemExit(
                f"value {value.value_id} changed more than its trailing empty-form field"
            )
        changed += 1

    if changed != len(empty_ids):
        raise SystemExit(
            f"{changed} values changed but {len(empty_ids)} utterances are entity-free"
        )
    return {
        "parent_snapshot_sha256": PARENT_SNAPSHOT_SHA256,
        "facets_byte_identical": len(snapshot.facets),
        "facets_changed": 0,
        "values_total": len(snapshot.values),
        "values_byte_identical": identical,
        "values_changed": changed,
        "change_shape": (
            "the trailing field of the raw line only, from the bare word "
            f"{PARENT_EMPTY_FORM!r} to the Solver contract's own empty form "
            f"{SOLVER_EMPTY_ENTITY_LIST_FORM!r}; nothing else on the line moves"
        ),
        "superset_statement": (
            "NOT a byte superset of the parent's value contents: the entity-bearing "
            "values are byte-identical, the entity-free values differ in that trailing "
            "field alone. Facets, value ids, prior scores, task targets, associations "
            "and provenance refs are identical on every selected utterance, and the "
            "source split identity hash is the parent's."
        ),
    }


def composition(rows) -> dict[str, object]:
    """Entity-bearing / entity-free counts of the pool, overall and per scenario.

    Labels, counts and shares only -- no utterance text and no filler.
    """

    per_scenario: dict[str, Counter] = {}
    bearing = 0
    free = 0
    for row in rows:
        bucket = per_scenario.setdefault(row.scenario, Counter())
        if row.entity_fillers:
            bearing += 1
            bucket["entity_bearing"] += 1
        else:
            free += 1
            bucket["entity_free"] += 1
    by_scenario = {}
    for scenario in sorted(per_scenario):
        bucket = per_scenario[scenario]
        total = bucket["entity_bearing"] + bucket["entity_free"]
        by_scenario[scenario] = {
            "entity_bearing": bucket["entity_bearing"],
            "entity_free": bucket["entity_free"],
            "total": total,
            "entity_free_share": round(bucket["entity_free"] / total, 6) if total else 0.0,
        }
    total = bearing + free
    return {
        "entity_bearing": bearing,
        "entity_free": free,
        "total": total,
        "entity_free_share": round(free / total, 6) if total else 0.0,
        "by_scenario": by_scenario,
    }


def build_store(*, check: bool, out_root: Path) -> dict[str, object]:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start

    excluded_ids, excluded_records = _excluded_sample_ids()
    before = len(rows)
    kept = tuple(row for row in rows if not (set(row.sample_ids) & excluded_ids))
    print(
        f"loaded {before} governed TRAIN utterances in {load_seconds:.2f}s; "
        f"excluded {before - len(kept)} named by {len(excluded_records)} roster(s); "
        f"{len(kept)} remain"
    )
    if len(kept) != EXPECTED_UTTERANCE_COUNT:
        raise SystemExit(
            f"construction pool carries {len(kept)} utterances, not the registered "
            f"{EXPECTED_UTTERANCE_COUNT} ({PARENT_RECEIPT_RELPATH})"
        )

    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=None,
        seed=SEED,
        dimensions=("content",),
        view=VIEW_ANNOTATED_EXEMPLARS_EMPTY_CONTRACT,
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

    if snapshot.source_split_identity_hash != EXPECTED_SOURCE_SPLIT_IDENTITY_HASH:
        raise SystemExit(
            f"source_split_identity_hash {snapshot.source_split_identity_hash} does not "
            f"match the released parent pool identity {EXPECTED_SOURCE_SPLIT_IDENTITY_HASH}; "
            "the selection moved, which this store must never do"
        )

    parent = _load_parent_snapshot(root)
    empty_ids = entity_free_value_ids(kept)
    relation = assert_parent_relation(snapshot, parent, empty_ids=empty_ids)
    pool = composition(kept)
    if relation["values_changed"] != pool["entity_free"]:
        raise SystemExit(
            f"{relation['values_changed']} values changed but the pool carries "
            f"{pool['entity_free']} entity-free utterances"
        )
    print(
        f"parent relation: {relation['facets_byte_identical']} facets byte-identical, "
        f"{relation['values_byte_identical']} values byte-identical, "
        f"{relation['values_changed']} entity-free values re-rendered"
    )
    print(
        f"pool composition: entity-bearing {pool['entity_bearing']}, entity-free "
        f"{pool['entity_free']} ({pool['entity_free_share']:.1%}), total {pool['total']}"
    )

    report_start = time.monotonic()
    report = coverage_report(snapshot, kept)
    report_seconds = time.monotonic() - report_start

    frozen = snapshot.frozen_json()
    snapshot_sha256 = frozen["snapshot_sha256"]
    snapshot_path = out_root / SNAPSHOT_RELDIR / "snapshot.json"

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
    release_path = out_root / SNAPSHOT_RELDIR / "release.json"

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
        "generator": "scripts/build_slurp_train_exemplars_with_empty_store.py",
        "authority": AUTHORITY,
        "builder_policy_id": KB_BUILD_POLICY_ID,
        "release_name": RELEASE_NAME,
        "spec": {
            "carrier_lock_key": spec.carrier_lock_key,
            "datastore_size": spec.datastore_size,
            "seed": spec.seed,
            "dimensions": list(spec.dimensions),
            "view": spec.view,
        },
        "solver_empty_entity_list_form": SOLVER_EMPTY_ENTITY_LIST_FORM,
        "solver_output_contract": "configs/probes/slurp_native_role_solver_v2.txt",
        "snapshot_sha256": snapshot_sha256,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_artifact_relpath": str(snapshot_path.relative_to(out_root)),
        "release_artifact_relpath": str(release_path.relative_to(out_root)),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "coverage_report": report,
        "pool_composition": pool,
        "parent_store": {
            "receipt_relpath": PARENT_RECEIPT_RELPATH,
            "receipt_sha256": _sha256_path(REPO_ROOT / PARENT_RECEIPT_RELPATH),
            "snapshot_relpath": (PARENT_SNAPSHOT_RELDIR / "snapshot.json").as_posix(),
            "source_split_identity_hash": EXPECTED_SOURCE_SPLIT_IDENTITY_HASH,
            "utterance_count": EXPECTED_UTTERANCE_COUNT,
            "relation": relation,
        },
        "decontamination": {
            "verdict": "clean",
            "checked_sample_count": len(snapshot.source_sample_ids),
            "excluded_rosters": excluded_records,
            "excluded_sample_count": len(excluded_ids),
            "exclusion_authority": (
                "docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json"
            ),
            "selection_unchanged": (
                "the source split identity hash equals the released parent store's, so "
                "the exclusion and the selection are the same ones already registered"
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
            "network": 0,
        },
    }
    if snapshot_file_sha256 is not None:
        receipt["snapshot_file_sha256"] = snapshot_file_sha256
        receipt["release_file_sha256"] = release_file_sha256
    if not check:
        receipt_sha256 = write_json_artifact(RECEIPT_PATH, receipt)
        print(
            f"wrote {RECEIPT_PATH.relative_to(REPO_ROOT)}  sha256={receipt_sha256[:16]}..."
        )
    return {
        "snapshot": snapshot,
        "snapshot_sha256": snapshot_sha256,
        "snapshot_file_sha256": snapshot_file_sha256,
        "release": release,
        "release_file_sha256": release_file_sha256,
        "snapshot_relpath": str(snapshot_path.relative_to(out_root)),
        "release_relpath": str(release_path.relative_to(out_root)),
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "utterance_count": len(kept),
        "pool_composition": pool,
        "parent_relation": relation,
    }


def check_facet_vector_coverage(root: Path, snapshot) -> None:
    """The sealed KU-S3 facet vectors still cover every facet id, BY MEMBERSHIP.

    No derivative is written and no encoder is contacted: this store's facet
    ids are the parent's facet ids, so the sealed file is a strict superset
    exactly as it already was.
    """

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
        "NO facet-vector derivative is needed and NO encoder is contacted: the facet "
        "ids are the released parent's, so facet_source stays "
        f"{FACET_VECTORS_RELPATH} (sha256 {FACET_VECTORS_SHA256}) unchanged."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    parser.add_argument(
        "--out-root",
        default=None,
        help="directory the store is written under (default: $SPEECHRL_DATA_DIR)",
    )
    args = parser.parse_args()

    root = data_root()
    out_root = Path(args.out_root).resolve() if args.out_root else root
    if out_root != root:
        print(f"REHEARSAL: writing under {out_root}, not the controlled data root")
    result = build_store(check=args.check, out_root=out_root)
    check_facet_vector_coverage(root, result["snapshot"])

    print("---")
    print(f"release_name={RELEASE_NAME}")
    print(f"utterance_count={result['utterance_count']}")
    print(f"snapshot_relpath={result['snapshot_relpath']}")
    print(f"snapshot_sha256={result['snapshot_sha256']}")
    print(f"snapshot_file_sha256={result['snapshot_file_sha256']}")
    print(f"release_relpath={result['release_relpath']}")
    print(f"release_file_sha256={result['release_file_sha256']}")
    print(f"facet_count={result['facet_count']} value_count={result['value_count']}")
    pool = result["pool_composition"]
    print(
        f"entity_bearing={pool['entity_bearing']} entity_free={pool['entity_free']} "
        f"entity_free_share={pool['entity_free_share']:.6f}"
    )
    print("execution_profile=model-free-check contacts=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
