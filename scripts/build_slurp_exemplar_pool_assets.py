#!/usr/bin/env python3
"""CLI: build the SLURP v2 base program E3 exemplar-pool assets.

MODEL-FREE. Profile ``model-free-check``: zero frozen-core, tool, embedding,
GPU or network contacts. Three artifacts, all pure re-derivations of bytes
already sealed by earlier passes:

1. The ``annotated-exemplars`` KB view over the TRAIN construction pool (every
   governed utterance EXCLUDING one with a recording in TRAIN Fold A, Fold B
   or DEV-1000 -- the 2026-09-13 exclusion, expected 9,354 facets), at the
   exact path the E3 baseline fragments pin:
   ``$SPEECHRL_DATA_DIR/knowledge/slurp/saea-kb-distmodel-v1/
   size-pool-annotated-exemplars/snapshot.json`` plus
   ``docs/receipts/knowledge/slurp-kb-size-pool-annotated-exemplars.json``.
   ``scripts/build_knowledge_snapshot.py`` writes the historical
   ``size-<tier>`` path scheme; this script writes the fixed
   ``size-pool-annotated-exemplars`` name the E3 spec pins, by calling the
   same ``rails.knowledge_build`` functions directly.

2. A facet-vector coverage check (NOT a derivative -- see the printed note):
   the sealed KU-S3 content facet-vector file
   (``vectors/slurp-kus3/facet-vectors.jsonl``, sha256 5dfe7523...) is a
   STRICT SUPERSET of this snapshot's 9,354 content facets (it carries a
   vector for every one of the 11,514 governed TRAIN utterances), and
   ``rails.kb_policy.multidim_recall`` looks a facet's vector up by id with
   ``.get(...)`` (a miss is skipped, never an error) -- so no filtered
   derivative is needed and this script proves that by membership check
   before printing the sealed file's own hash unchanged.

3. The QUERY-side dimension-rekeyed derivative of the anchor's own sealed
   Fold A speech-SEGMENT file
   (``vectors/slurp-intent-boundaries-train-fold-a-1080-v1/
   query-vectors-speech-segments.jsonl``, sha256 e7a5b226...): that file's
   only declared dimension is ``intent-boundary`` (the SAME embedding space
   as the KU-S3 ``content`` facet side -- see ``docs/results/
   2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md``, "the file's
   `intent-boundary` dimension is an alias of the `content` dimension"), but
   ``rails.phase_supply.load_sealed_segment_vectors`` refuses a spec whose
   declared ``dimensions`` do not EXACTLY match a segment's own vector keys.
   The B1 store declares ``dimensions: ["content"]`` (module docstring of
   ``knowledge_stores.py``'s train-exemplars store), so this script writes a
   byte-for-byte re-keyed copy -- same floats, same segment order, one JSON
   key renamed -- under
   ``$SPEECHRL_DATA_DIR/vectors/slurp-exemplars-pool/
   query-vectors-speech-segments-content-v1.jsonl`` plus a provenance JSON
   naming the parent sha256. No number is recomputed anywhere in this file.

Usage::

    python scripts/build_slurp_exemplar_pool_assets.py
    python scripts/build_slurp_exemplar_pool_assets.py --check   # verify only
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
    "docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md section 4 item E3; "
    "docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md"
)
SEED = 20260823
TIER = "pool-annotated-exemplars"
SNAPSHOT_RELDIR = Path("knowledge") / "slurp" / KB_BUILD_POLICY_ID / f"size-{TIER}"
RECEIPT_PATH = REPO_ROOT / "docs" / "receipts" / "knowledge" / f"slurp-kb-size-{TIER}.json"

# The 2026-09-13 exclusion (docs/readiness/2026-09-13-slurp-semantic-authoring-
# registration-v1.json "forbidden_rosters"): every utterance with a recording
# in TRAIN Fold A, Fold B, or the DEV-1000 probe roster is dropped from the
# construction pool BEFORE selection. DEV-1000 contributes zero additional
# exclusions on top of Fold A + Fold B (it names no TRAIN sample id), which is
# why the sibling snapshot 'size-full-content-slot-fillers-intent-slot-frame-
# tfrl-folds-v1' already reaches the expected 9,354 utterances with only the
# two fold rosters -- both are listed here anyway, so this script excludes
# exactly the registered set rather than the subset that happens to matter.
EXCLUDE_ROSTER_RELPATHS = (
    "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "docs/receipts/probe-samples/DEV-1000.json",
)
EXPECTED_UTTERANCE_COUNT = 9354
EXPECTED_SOURCE_SPLIT_IDENTITY_HASH = (
    "22f6092dfdb4a160376e529d8e59e9215bc7701e274620d35feb1c4d82f309e9"
)

FACET_VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
FACET_VECTORS_SHA256 = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"

QUERY_SEGMENTS_RELPATH = (
    "vectors/slurp-intent-boundaries-train-fold-a-1080-v1/"
    "query-vectors-speech-segments.jsonl"
)
QUERY_SEGMENTS_SHA256 = "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b"
QUERY_SOURCE_DIMENSION = "intent-boundary"
QUERY_TARGET_DIMENSION = "content"
QUERY_OUT_DIR_RELPATH = "vectors/slurp-exemplars-pool"
QUERY_OUT_NAME = "query-vectors-speech-content-v1.jsonl"
QUERY_PROVENANCE_NAME = "query-vectors-speech-content-v1.provenance.json"

LEDGER_ROW = "SAEA-SLURP-E3-EXEMPLAR-POOL-ASSETS-V1"


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _excluded_sample_ids(root: Path) -> tuple[frozenset[str], list[dict[str, object]]]:
    excluded: set[str] = set()
    records: list[dict[str, object]] = []
    for relpath in EXCLUDE_ROSTER_RELPATHS:
        path = REPO_ROOT / relpath
        document = json.loads(path.read_text(encoding="utf-8"))
        # Roster item shapes differ: the construction folds carry an explicit
        # 'sample_id' field, the DEV-1000 probe roster carries only 'id'
        # (and its ids are 'slurp:devel:...', disjoint from TRAIN by
        # construction, which is why it contributes zero new exclusions).
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


def build_snapshot(*, check: bool) -> dict[str, object]:
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows = slurp_kb_rows(lock, root)
    load_seconds = time.monotonic() - load_start

    excluded_ids, excluded_records = _excluded_sample_ids(root)
    before = len(rows)
    rows = tuple(row for row in rows if not (set(row.sample_ids) & excluded_ids))
    print(
        f"loaded {before} governed TRAIN utterances in {load_seconds:.2f}s; "
        f"excluded {before - len(rows)} named by {len(excluded_records)} roster(s); "
        f"{len(rows)} remain"
    )

    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        datastore_size=None,
        seed=SEED,
        dimensions=("content",),
        view=VIEW_ANNOTATED_EXEMPLARS,
    ).validate()

    build_start = time.monotonic()
    snapshot = build_knowledge_snapshot(spec, lock=lock, root=root, rows=rows, repo_root=REPO_ROOT)
    build_seconds = time.monotonic() - build_start
    print(
        f"built snapshot {snapshot.snapshot_id} facets={len(snapshot.facets)} "
        f"values={len(snapshot.values)} in {build_seconds:.2f}s"
    )

    if len(rows) != EXPECTED_UTTERANCE_COUNT:
        raise SystemExit(
            f"construction pool carries {len(rows)} utterances, not the registered "
            f"{EXPECTED_UTTERANCE_COUNT} (docs/readiness/"
            "2026-09-13-slurp-semantic-authoring-registration-v1.json)"
        )
    if snapshot.source_split_identity_hash != EXPECTED_SOURCE_SPLIT_IDENTITY_HASH:
        raise SystemExit(
            f"source_split_identity_hash {snapshot.source_split_identity_hash} does not "
            f"match the registered pool identity {EXPECTED_SOURCE_SPLIT_IDENTITY_HASH}"
        )

    report_start = time.monotonic()
    report = coverage_report(snapshot, rows)
    report_seconds = time.monotonic() - report_start

    frozen = snapshot.frozen_json()
    snapshot_sha256 = frozen["snapshot_sha256"]
    snapshot_path = root / SNAPSHOT_RELDIR / "snapshot.json"
    if not check:
        write_json_artifact(snapshot_path, frozen)
        print(f"wrote {snapshot_path}  snapshot_sha256={snapshot_sha256[:16]}...")
    else:
        print(f"(check) snapshot would be {snapshot_path}  snapshot_sha256={snapshot_sha256[:16]}...")

    receipt = {
        "schema": "saea-kb-build-receipt-v1",
        "generator": "scripts/build_slurp_exemplar_pool_assets.py",
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
            "excluded_rosters": excluded_records,
            "excluded_sample_count": len(excluded_ids),
            "exclusion_authority": (
                "docs/readiness/2026-09-13-slurp-semantic-authoring-registration-v1.json"
            ),
        },
        "timing_seconds": {
            "load_train_rows": round(load_seconds, 3),
            "build_snapshot": round(build_seconds, 3),
            "coverage_report": round(report_seconds, 3),
        },
        "exposure_ledger_row": LEDGER_ROW,
        "execution_profile": "model-free-check",
    }
    if not check:
        receipt_sha256 = write_json_artifact(RECEIPT_PATH, receipt)
        print(f"wrote {RECEIPT_PATH.relative_to(REPO_ROOT)}  sha256={receipt_sha256[:16]}...")
    return {
        "snapshot_sha256": snapshot_sha256,
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "snapshot": snapshot,
    }


def check_facet_vector_coverage(root: Path, snapshot) -> None:
    path = root / FACET_VECTORS_RELPATH
    measured = _sha256_path(path)
    if measured != FACET_VECTORS_SHA256:
        raise SystemExit(f"{path} hashes to {measured}, not the pinned {FACET_VECTORS_SHA256}")
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
        f"({FACET_VECTORS_RELPATH}, sha256 {FACET_VECTORS_SHA256[:16]}...); "
        f"snapshot needs {len(facet_ids)}; missing={len(missing)}"
    )
    if missing:
        preview = sorted(missing)[:5]
        raise SystemExit(
            f"{len(missing)} snapshot facet id(s) have no sealed vector, e.g. {preview}; "
            "a filtered derivative would be required (module docstring), which this run "
            "did NOT need to produce"
        )
    print(
        "NO facet-vector derivative is needed: the sealed file is a strict superset of "
        "this snapshot's content facets and rails.kb_policy.multidim_recall looks a "
        "facet's vector up with .get(...) (a miss is skipped, never an error). "
        f"facet_source stays {FACET_VECTORS_RELPATH} (sha256 {FACET_VECTORS_SHA256}) unchanged."
    )


def build_query_derivative(root: Path, *, check: bool) -> dict[str, object]:
    """Flatten the anchor's sealed Fold A speech-SEGMENT file into a flat
    ``sealed-vectors`` file (module docstring, item 3): one ``content``
    vector per sample id, byte-identical to that sample's single segment.

    Why flat and not a re-keyed segment file (a design correction made while
    implementing the twin generator, item 4): ``rails.phase_supply.
    _assert_segment_query_binding`` cross-checks a ``sealed-segment-vectors``
    row's ``audio_sha256`` against the QueryState's OWN
    ``speech_packet_sha256`` -- the recipient's real, independently-computed
    packet hash -- so a row cannot legally carry another sample's audio
    identity. A derangement twin needs EXACTLY that (another sample's
    vector, filed under this sample's id), which only the flat
    ``sealed-vectors`` schema (KU-S3's own schema, with no audio-identity
    binding at all) permits. Every Fold A row carries EXACTLY ONE segment
    (asserted below), so flattening loses no information: the single
    segment's vector IS the sample's whole-utterance embedding.
    """

    source_path = root / QUERY_SEGMENTS_RELPATH
    raw = source_path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != QUERY_SEGMENTS_SHA256:
        raise SystemExit(
            f"{source_path} hashes to {measured}, not the pinned {QUERY_SEGMENTS_SHA256}"
        )
    rows: list[tuple[str, list[float]]] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        document = json.loads(line)
        segments = document["segments"]
        if len(segments) != 1:
            raise SystemExit(
                f"{source_path} id={document.get('id')!r} carries {len(segments)} segments; "
                "flattening to one vector per sample requires exactly one"
            )
        vectors = segments[0]["vectors"]
        if set(vectors) != {QUERY_SOURCE_DIMENSION}:
            raise SystemExit(
                f"{source_path} id={document.get('id')!r} carries dimensions "
                f"{sorted(vectors)}, expected exactly {{{QUERY_SOURCE_DIMENSION!r}}}"
            )
        rows.append((str(document["id"]), list(vectors[QUERY_SOURCE_DIMENSION])))

    out_lines = [
        json.dumps(
            {"id": entry_id, "vectors": {QUERY_TARGET_DIMENSION: vector}},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        )
        for entry_id, vector in rows
    ]
    out_dir = root / QUERY_OUT_DIR_RELPATH
    out_path = out_dir / QUERY_OUT_NAME
    out_bytes = ("\n".join(out_lines) + "\n").encode("utf-8")
    out_sha256 = _sha256_bytes(out_bytes)
    if not check:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(out_bytes)
        print(f"wrote {out_path}  sha256={out_sha256[:16]}...  rows={len(rows)}")
    else:
        print(
            f"(check) query derivative would be {out_path}  sha256={out_sha256[:16]}...  "
            f"rows={len(rows)}"
        )

    provenance = {
        "schema": "saea-slurp-exemplar-query-vectors-provenance-v1",
        "generator": "scripts/build_slurp_exemplar_pool_assets.py",
        "transform": (
            "flatten one-segment-per-sample sealed-segment-vectors into flat "
            "sealed-vectors, dimension renamed intent-boundary -> content; every float "
            "is byte-identical to the parent's single segment vector; zero model or "
            "encoder contact"
        ),
        "parent_relpath": QUERY_SEGMENTS_RELPATH,
        "parent_sha256": QUERY_SEGMENTS_SHA256,
        "parent_kind": "sealed-segment-vectors",
        "output_kind": "sealed-vectors",
        "source_dimension": QUERY_SOURCE_DIMENSION,
        "target_dimension": QUERY_TARGET_DIMENSION,
        "why": (
            "(1) the parent's only declared dimension is 'intent-boundary', which "
            "docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md establishes is "
            "an alias of the 'content' embedding space, and the E3 train-exemplars store "
            "declares dimensions=['content'] so its query and facet sides share one "
            "dimension name; (2) flat sealed-vectors (not sealed-segment-vectors) is "
            "required so the B1 twin (item 4) can legally file another sample's vector "
            "under this sample's id -- rails.phase_supply._assert_segment_query_binding "
            "would refuse that for a segment-kind row, whose audio_sha256 must match the "
            "QueryState's own bound packet"
        ),
        "row_count": len(rows),
        "sha256": out_sha256,
        "exposure_ledger_row": LEDGER_ROW,
        "execution_profile": "model-free-check",
    }
    provenance_path = out_dir / QUERY_PROVENANCE_NAME
    if not check:
        write_json_artifact(provenance_path, provenance)
        print(f"wrote {provenance_path}")
    return {"sha256": out_sha256, "row_count": len(rows)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = parser.parse_args()

    root = data_root()
    snapshot_result = build_snapshot(check=args.check)
    check_facet_vector_coverage(root, snapshot_result["snapshot"])
    query_result = build_query_derivative(root, check=args.check)

    print("---")
    print(f"snapshot_sha256={snapshot_result['snapshot_sha256']}")
    print(f"facet_count={snapshot_result['facet_count']} value_count={snapshot_result['value_count']}")
    print(f"query_derivative_sha256={query_result['sha256']} rows={query_result['row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
