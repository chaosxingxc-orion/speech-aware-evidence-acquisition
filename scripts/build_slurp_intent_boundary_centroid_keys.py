#!/usr/bin/env python3
"""Build the intent-boundary CENTROID key file: one key per released intent,
the unit-normalised mean of the intent's pinned construction-TRAIN utterance
vectors, at zero encoder contacts.

WHAT IT IS. ``docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md``
found that the boundary channel's written one-line descriptions are its weak
link: a key built as the intent's mean construction-TRAIN utterance vector puts
the gold intent inside the delivered eight on 71.2 / 64.7 / 66.8 % of the
intent-wrong rows (Fold A / ROLL-1 / DEV-2000) against 45.0 / 44.6 / 35.8 %
for the written key, at zero token cost, because the DELIVERED body is
unchanged -- only the retrieval key moves. Owner decision 145 registers a
CONV-style probe of that key. This script cuts the key file that probe pins.

ZERO CONTACTS. A centroid is arithmetic over ALREADY-PINNED vectors: every
member vector was cut by the frozen encoder before, under its own ledger row,
and is read here from the receipt-pinned ``vectors/slurp-kus3/facet-vectors.jsonl``
after its sha256 is verified. No text is encoded, no model, server, encoder,
embedder, scorer, tokenizer, network or GPU is touched.

THE CONSTRUCTION POOL IS THE R01-EXCLUDED POOL
(``size-pool-annotated-exemplars-minus-r01``, 8,554 utterances), not the full
9,354-utterance pool, so that ONE key file is held out on every roster the
program evaluates on: TRAIN Fold A and DEV-2000-ADDED have no utterance in
either pool, and the R01C construction roster (ROLL-1) is excluded from this
one. The price is one intent with no construction utterance in this pool; it
keeps the flown written key, byte for byte, and the receipt names it.

THE LABEL IS A STORE PROPERTY. Each pool value's frozen build-time
``task_target`` -- the same key the agreement builder votes with -- says which
intent a member vector belongs to. No gold label, reference transcript or
future turn enters the construction. (The diagnostic labelled the pool through
the governed TRAIN split instead; the derivation that consumes this file proves
the two labellings yield the same 60 vectors.)

THE ARITHMETIC IS THE DIAGNOSTIC'S, LITERALLY: this script imports
``scripts/analysis/slurp_boundary_key_construction_diagnostic.py`` byte-unchanged
and uses its ``unit_rows`` (row-wise L2 in float64, the quotient
``rails.kb_policy._cosine_with_norms`` computes), its verified loaders for the
released store and the pool vectors, and the same member order (pool facet ids
ascending), so the mean is bitwise the diagnostic's ``centroid`` construction.

A NEW RECEIPT KIND. The text-facet kind
(``saea-text-facet-preparation-receipt-v1`` / ``text-facet-vectors-v1``) pins a
``text_sha256`` per facet, because each key WAS a text. A centroid has no text
source, so ``saea-centroid-key-receipt-v1`` pins, per facet, the construction
(``centroid`` or ``written-fallback``), the member count, the sha256 of the
sorted member facet-id list and the sha256 of the emitted vector, plus every
input pin and the loader implementation hashes. The file itself is an ordinary
``sealed-vectors`` file (``{"id", "vectors"}`` per line), so the flight loads it
through ``rails.phase_supply.load_sealed_vectors`` unchanged.

TEXT DISCIPLINE. Facet ids, counts, cosines and hashes only. No utterance text,
transcript, gold label, knowledge body or key description is read into a
printed or persisted value.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python \\
        scripts/build_slurp_intent_boundary_centroid_keys.py \\
        --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

from speech_aware_evidence_acquisition.rails import kb_policy, phase_supply  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors  # noqa: E402

ARTIFACT_ID = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
BUILDER_ID = "saea-slurp-intent-boundary-centroid-keys-builder-v1"
RECEIPT_SCHEMA = "saea-centroid-key-receipt-v1"
RECEIPT_KIND = "centroid-over-pinned-utterance-vectors-v1"
OUT_DIR = Path("prepared") / ARTIFACT_ID
FACETS_NAME = "facets.jsonl"
RECEIPT_NAME = "receipt.json"

DIAGNOSTIC_RECIPE = Path("scripts/analysis/slurp_boundary_key_construction_diagnostic.py")
DIAGNOSTIC_NOTE = Path("docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md")

#: The diagnostic's own pins, repeated here so a mismatch is refused by name
#: BEFORE its loaders run; the loaders verify the same digests again.
IB_SNAPSHOT_SHA = "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"
IB_FACETS_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
POOL_M_SHA = "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"
POOL_FACETS_SHA = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"
LABEL_KEY = "task_target"


class BuildError(RuntimeError):
    """Refuse a build whose inputs are not the pinned bytes."""


def digest_file(path: Path) -> str:
    measured = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1 << 20):
            measured.update(chunk)
    return measured.hexdigest()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def import_diagnostic(repo: Path):
    """The diagnostic module, imported from its committed path, unchanged."""

    path = repo / DIAGNOSTIC_RECIPE
    spec = importlib.util.spec_from_file_location("_saea_boundary_key_diagnostic", path)
    if spec is None or spec.loader is None:
        raise BuildError("cannot import the boundary-key diagnostic module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, expected in (
        ("IB_SNAPSHOT_SHA", IB_SNAPSHOT_SHA),
        ("IB_FACETS_SHA", IB_FACETS_SHA),
        ("POOL_M_SHA", POOL_M_SHA),
        ("POOL_FACETS_SHA", POOL_FACETS_SHA),
    ):
        if getattr(module, name) != expected:
            raise BuildError(f"the diagnostic's {name} is not the pin this builder was written against")
    return module, digest_file(path)


def pool_labels(root: Path, relpath: str, expected_sha: str) -> dict:
    """``{pool facet id: task_target}`` from the pinned pool snapshot -- the
    store's own frozen build-time label, never a gold label."""

    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / relpath).read_text(encoding="utf-8"))
    )
    if snapshot.content_hash() != expected_sha:
        raise BuildError(f"{relpath} does not hash to the pinned {expected_sha}")
    labels: dict[str, str] = {}
    missing = 0
    for value in snapshot.values:
        if len(value.associated_facet_ids) != 1:
            raise BuildError(f"{relpath}: a pool value is not bound to exactly one facet")
        facet_id = value.associated_facet_ids[0]
        if facet_id in labels:
            raise BuildError(f"{relpath}: two pool values bind one facet")
        if not value.task_target:
            missing += 1
            continue
        labels[facet_id] = str(value.task_target)
    facet_ids = sorted(facet.facet_id for facet in snapshot.facets)
    if set(facet_ids) != set(labels) or missing:
        raise BuildError(f"{relpath}: {missing} pool values carry no {LABEL_KEY}")
    return {"labels": labels, "facets": facet_ids, "content_sha256": snapshot.content_hash()}


def build(repo: Path, root: Path, out_root: Path) -> dict:
    diag, diag_sha = import_diagnostic(repo)
    store = diag.load_boundary(root)
    pool = pool_labels(root, diag.POOL_M, POOL_M_SHA)
    unknown = sorted(set(pool["labels"].values()) - set(store["intents"]))
    if unknown:
        raise BuildError(f"{len(unknown)} pool {LABEL_KEY} values name no released intent")
    vectors = diag.load_pool_vectors(root, set(pool["facets"]))

    #: Member order is the diagnostic's: pool facet ids ascending.
    members: dict[str, list[str]] = defaultdict(list)
    for facet_id in pool["facets"]:
        members[pool["labels"][facet_id]].append(facet_id)

    by_intent = {store["to_intent"][fid]: fid for fid in store["facet_vectors"]}
    lines: list[str] = []
    facet_records: list[dict] = []
    matrix_rows: list[np.ndarray] = []
    fallback: list[str] = []
    for intent in store["intents"]:
        facet_id = by_intent[intent]
        chosen = members.get(intent, [])
        if chosen:
            block = diag.unit_rows([vectors[f] for f in chosen])
            centre = diag.unit_rows(block.mean(axis=0, keepdims=True))[0]
            values = [float(x) for x in centre]
            construction = "centroid"
        else:
            # No construction utterance in this pool: the flown written key,
            # byte for byte (the same floats the flown file carries).
            values = [float(x) for x in store["facet_vectors"][facet_id][diag.IB_DIM]]
            construction = "written-fallback"
            fallback.append(facet_id)
        line = json.dumps(
            {"id": facet_id, "vectors": {diag.IB_DIM: values}}, separators=(",", ":")
        )
        lines.append(line)
        matrix_rows.append(np.asarray(values, dtype=np.float64))
        facet_records.append(
            {
                "id": facet_id,
                "construction": construction,
                "members": len(chosen),
                "member_ids_sha256": digest_text("\n".join(sorted(chosen))),
                "vector_sha256": digest_text(json.dumps(values, separators=(",", ":"))),
                "l2_norm": round(float(np.linalg.norm(matrix_rows[-1])), 12),
            }
        )
    facets_text = "\n".join(lines) + "\n"

    # Key-to-key geometry, for the record (the diagnostic's section 3 quantity).
    matrix = np.asarray(matrix_rows)
    gram = matrix @ matrix.T
    off = gram[~np.eye(len(matrix), dtype=bool)]
    widths = {len(row) for row in matrix_rows}
    if widths != {store["matrix"].shape[1]}:
        raise BuildError("emitted keys do not all carry the store's own width")

    out_dir = out_root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    facets_path = out_dir / FACETS_NAME
    receipt_path = out_dir / RECEIPT_NAME
    if facets_path.exists() or receipt_path.exists():
        raise BuildError(f"refusing to overwrite an existing artifact under {out_dir}")
    facets_path.write_bytes(facets_text.encode("utf-8"))
    facets_sha = digest_file(facets_path)

    # Read the file back through the PRODUCTION loader, exactly as a flight will.
    loaded = load_sealed_vectors(facets_path, expected_sha256=facets_sha, dimensions=(diag.IB_DIM,))
    if set(loaded) != set(store["facet_vectors"]):
        raise BuildError("the emitted file does not cover the released store's facet ids exactly")
    for record, row in zip(facet_records, matrix_rows):
        back = np.asarray(loaded[record["id"]][diag.IB_DIM], dtype=np.float64)
        if back.shape != row.shape or not np.array_equal(back, row):
            raise BuildError(f"{record['id']}: the production loader does not read back the emitted floats")

    receipt = {
        "schema": RECEIPT_SCHEMA,
        "kind": RECEIPT_KIND,
        "artifact_id": ARTIFACT_ID,
        "builder_id": BUILDER_ID,
        "builder_sha256": digest_file(Path(__file__)),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "contact_class": "model-free",
        "contacts": {
            "model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0,
            "tokenizer": 0, "network": 0, "gpu": 0, "paid_api": 0,
        },
        "artifact": {
            "relpath": str(OUT_DIR / FACETS_NAME).replace("\\", "/"),
            "sha256": facets_sha,
            "rows": len(lines),
            "line_schema": "sealed-vectors: one object per line with exactly 'id' and 'vectors'",
            "dimension": diag.IB_DIM,
            "width": int(store["matrix"].shape[1]),
            "loader": "speech_aware_evidence_acquisition.rails.phase_supply.load_sealed_vectors",
            "read_back_through_the_production_loader": True,
        },
        "why_a_new_receipt_kind": (
            "The text-facet kind pins a text_sha256 per facet because each written key WAS a "
            "text run through the encoder. A centroid has no text source and no encoder pass: "
            "it is arithmetic over already-pinned utterance vectors. This kind therefore pins, "
            "per facet, the construction, the member count, the sha256 of the sorted member "
            "facet-id list and the sha256 of the emitted vector, plus every input pin and the "
            "loader implementation hashes, so the file is reproducible from the pins alone."
        ),
        "construction": {
            "rule": (
                "for each released intent, take every construction-pool facet whose frozen "
                "build-time task_target names that intent, in pool facet-id order; unit-normalise "
                "each member vector in float64 (rails.kb_policy._cosine_with_norms' own quotient); "
                "take the arithmetic mean over the members; unit-normalise the mean. An intent with "
                "no member in this pool keeps the flown written key vector, byte for byte."
            ),
            "arithmetic_source": {
                "relpath": str(DIAGNOSTIC_RECIPE).replace("\\", "/"),
                "sha256": diag_sha,
                "functions_used": ["load_boundary", "load_pool_vectors", "unit_rows"],
                "note": "imported byte-unchanged; the mean is bitwise the diagnostic's 'centroid' construction",
            },
            "label_key": LABEL_KEY,
            "label_is": "the pool value's frozen build-time task_target, a released-store property; no gold label enters",
            "member_order": "pool facet ids ascending (the diagnostic's order)",
            "construction_pool": "the R01-excluded pool, so one file is held out on TRAIN Fold A, ROLL-1 (R01C) and DEV-2000-ADDED alike",
        },
        "inputs": {
            "target_store_snapshot": {
                "relpath": diag.IB_SNAPSHOT, "sha256": store["content_sha256"],
                "facets": 60, "role": "the released intent-boundaries-v1 store; its facet ids and delivered bodies are unchanged",
            },
            "written_key_vectors": {
                "relpath": diag.IB_FACETS, "sha256": IB_FACETS_SHA,
                "role": "the flown keys; the fallback source for an intent with no pool member",
            },
            "written_key_encoding_index": {
                "relpath": diag.IB_INDEX, "sha256": store["index_sha256"],
                "encoded_is_representation": store["encoded_is_representation"],
            },
            "construction_pool_snapshot": {
                "relpath": diag.POOL_M, "sha256": pool["content_sha256"], "utterances": len(pool["facets"]),
            },
            "pool_facet_vectors": {
                "relpath": diag.POOL_FACETS, "sha256": POOL_FACETS_SHA,
                "role": "one pinned vector per construction-TRAIN utterance; the members",
                "tool_contact_ledger_row": "SAEA-SLURP-MF7B-NEMOTRON-EMBEDDING-V1",
            },
            "same_space": {
                "encoder_inventory_sha256": store["encoder_inventory_sha256"],
                "geometry": store["geometry"],
                "note": "both the written keys and the pool vectors were cut by the same frozen encoder under the same prefix; the diagnostic's section 0 proves the spaces comparable",
            },
        },
        "measured": {
            "intents": len(store["intents"]),
            "centroid_facets": sum(1 for r in facet_records if r["construction"] == "centroid"),
            "written_fallback_facets": len(fallback),
            "written_fallback_ids": fallback,
            "members_total": sum(r["members"] for r in facet_records),
            "members_min_over_centroid_facets": min(r["members"] for r in facet_records if r["members"]),
            "members_max": max(r["members"] for r in facet_records),
            "key_to_key_cosine_mean": round(float(off.mean()), 4),
            "key_to_key_cosine_max": round(float(off.max()), 4),
            "distinct_pool_labels": len(members),
        },
        "facets": facet_records,
        "implementation": {
            "speech_aware_evidence_acquisition.rails.kb_policy": digest_file(Path(kb_policy.__file__)),
            "speech_aware_evidence_acquisition.rails.phase_supply": digest_file(Path(phase_supply.__file__)),
        },
        "boundary": (
            "A pre-computed model-free input, never an authorization: it opens no attempt, "
            "reserves no contact, admits no mechanism, releases or rebuilds no store and states "
            "no effectiveness claim. The released store, its facet ids and its delivered bodies "
            "are unchanged; only a retrieval key file exists beside them, to be pinned by one "
            "derived baseline. No gold label, reference transcript or future turn enters it."
        ),
    }
    receipt_text = json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    receipt_path.write_bytes(receipt_text.encode("utf-8"))
    return {
        "facets": str(facets_path),
        "facets_sha256": facets_sha,
        "receipt": str(receipt_path),
        "receipt_sha256": digest_file(receipt_path),
        "rows": len(lines),
        "written_fallback_ids": fallback,
        "key_to_key_cosine_mean": receipt["measured"]["key_to_key_cosine_mean"],
        "key_to_key_cosine_max": receipt["measured"]["key_to_key_cosine_max"],
        "diagnostic_sha256": diag_sha,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--output-root",
        default=None,
        help="where prepared/<artifact id>/ is created; defaults to --data-root",
    )
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    repo = Path(args.repo_root).resolve()
    root = Path(args.data_root).resolve()
    out_root = Path(args.output_root).resolve() if args.output_root else root
    print(json.dumps(build(repo, root, out_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
