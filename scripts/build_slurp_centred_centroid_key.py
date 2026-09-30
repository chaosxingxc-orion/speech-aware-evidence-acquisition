#!/usr/bin/env python3
"""Build the CENTRED centroid key file (K6p's key side): one key per released intent, the
intent's raw construction-pool member mean minus the construction-pool mean, re-normalised,
at zero encoder contacts.

WHAT IT IS. ``docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md`` (read
SAEA-SLURP-RETRIEVAL-KEY-RECALL-OFFLINE-V1) found one key family that changes rank quality: K6p,
the centred centroid + agreement key under PRODUCTION admission (a facet is recalled only at a
positive cosine). Its key is ``centre_keys(raw_means, mu_p)`` and its query is
``centre_queries(q, mu_q)``, mu_q the mean of the pinned R01C construction-roster speech
queries. This script cuts the KEY file a Perception branch's ``key_source.facet_source`` pins;
``scripts/build_slurp_centred_query_vectors.py`` cuts the per-roster QUERY file.

THE ARITHMETIC IS THE READ'S, LITERALLY: this script imports
``scripts/analysis/slurp_retrieval_key_recall.py`` and calls its ``key_construction`` (the same
pinned store, the same R01-excluded pool minus Fold A / Fold B / R01 / R01C, the same unit member
vectors, the same raw member means and pool mean; the pinned centroid key reproduced as a custody
check) and its ``centre_keys``. Nothing is re-derived here.

ZERO CONTACTS. Arithmetic over already-pinned vectors only: no model, server, encoder, embedder,
scorer, tokenizer, network or GPU contact. The labels are the pool values' frozen build-time
``task_target`` (a store property); no gold label, transcript or future turn enters the key. The
R01C speech queries enter only through their mean, which the key does NOT use (it is recorded in
the receipt so the key and query artifacts provably share one centring statistic set).

The file is an ordinary ``sealed-vectors`` file (``{"id", "vectors"}`` per line), read back
through ``rails.phase_supply.load_sealed_vectors`` before the receipt is written.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python scripts/build_slurp_centred_centroid_key.py \\
        --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

ARTIFACT_ID = "SAEA-SLURP-CENTRED-CENTROID-KEY-V1"
BUILDER_ID = "saea-slurp-centred-centroid-key-builder-v1"
LEDGER_ROW = "SAEA-SLURP-CENTRED-CENTROID-KEY-BUILD-V1"
RECEIPT_SCHEMA = "saea-centred-centroid-key-receipt-v1"
RECEIPT_KIND = "centred-centroid-over-pinned-utterance-vectors-v1"
OUT_DIR = Path("prepared") / ARTIFACT_ID
KEY_NAME = "key-v1.jsonl"
RECEIPT_NAME = "receipt.json"
RECALL = Path("scripts/analysis/slurp_retrieval_key_recall.py")
NOTE = Path("docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md")
#: The pinned (uncentred) centroid key the construction pool must reproduce (COMP-1b's facet_source).
CENTROID_PIN = {
    "relpath": "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl",
    "sha256": "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532",
}
CENTRING_ROSTER = "docs/receipts/rosters/slurp-stage3-construction-r01c.json"


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


def vector_sha(vector) -> str:
    """sha256 of a float64 vector's little-endian bytes (for the receipt's statistic pins)."""

    return hashlib.sha256(np.asarray(vector, dtype="<f8").tobytes()).hexdigest()


def import_module(repo: Path, relpath: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, repo / relpath)
    if spec is None or spec.loader is None:
        raise BuildError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def recall_modules(repo: Path):
    """The recall read and the two modules it builds on, imported from their committed paths."""

    recall = import_module(repo, RECALL, "slurp_retrieval_key_recall")
    diag = import_module(repo, Path(recall.DIAG), "_rk_boundary_key_diagnostic")
    cbuild = import_module(repo, Path(recall.CENTROID_BUILDER), "_rk_centroid_builder")
    return recall, diag, cbuild


def facet_ids(store: dict, intents: list) -> list:
    by_intent = {store["to_intent"][fid]: fid for fid in store["facet_vectors"]}
    return [by_intent[intent] for intent in intents]


def key_lines(ids: list, keys: np.ndarray, dimension: str) -> list:
    return [
        json.dumps({"id": fid, "vectors": {dimension: [float(x) for x in row]}}, separators=(",", ":"))
        for fid, row in zip(ids, keys)
    ]


def build(repo: Path, root: Path, out_root: Path) -> dict:
    from speech_aware_evidence_acquisition.rails import kb_policy, phase_supply
    from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors

    recall, diag, cbuild = recall_modules(repo)
    kc = recall.key_construction(root, diag, cbuild, centroid_pin=CENTROID_PIN)
    intents = kc["intents"]
    keys = recall.centre_keys(kc["raw_means"], kc["mu_p"])
    ids = facet_ids(kc["store"], intents)
    if [fid.split(recall.IB_FACET_MARK, 1)[-1] for fid in ids] != intents:
        raise BuildError("store facet ids are not intent-boundary:<intent> in intent order")
    lines = key_lines(ids, keys, recall.IB_DIM)
    text = "\n".join(lines) + "\n"

    out_dir = out_root / OUT_DIR
    key_path, receipt_path = out_dir / KEY_NAME, out_dir / RECEIPT_NAME
    if key_path.exists() or receipt_path.exists():
        raise BuildError(f"refusing to overwrite an existing artifact under {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(text.encode("utf-8"))
    key_sha = digest_file(key_path)
    loaded = load_sealed_vectors(key_path, expected_sha256=key_sha, dimensions=(recall.IB_DIM,))
    if set(loaded) != set(ids):
        raise BuildError("the emitted key file does not cover the released facet ids exactly")
    for fid, row in zip(ids, keys):
        if not np.array_equal(np.asarray(loaded[fid][recall.IB_DIM], dtype=np.float64), row):
            raise BuildError(f"{fid}: the production loader does not read back the emitted floats")

    per_intent = kc["per_intent"]
    gram = keys @ keys.T
    off = gram[~np.eye(len(keys), dtype=bool)]
    receipt = {
        "schema": RECEIPT_SCHEMA, "kind": RECEIPT_KIND, "artifact_id": ARTIFACT_ID, "builder_id": BUILDER_ID,
        "builder_sha256": digest_file(Path(__file__)), "exposure_ledger_row": LEDGER_ROW,
        "generated_at": datetime.now(timezone.utc).isoformat(), "contact_class": "model-free",
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0, "tokenizer": 0,
                     "network": 0, "gpu": 0, "paid_api": 0},
        "artifact": {
            "relpath": str(OUT_DIR / KEY_NAME).replace("\\", "/"), "sha256": key_sha, "rows": len(lines),
            "line_schema": "sealed-vectors: one object per line with exactly 'id' and 'vectors'",
            "dimension": recall.IB_DIM, "width": int(keys.shape[1]),
            "loader": "speech_aware_evidence_acquisition.rails.phase_supply.load_sealed_vectors",
            "read_back_through_the_production_loader": True,
        },
        "construction": {
            "rule": ("for each released intent: the arithmetic mean of its unit-normalised construction-pool member "
                     "vectors (the written key when it has no member), minus the arithmetic mean of every "
                     "construction-pool member vector, unit-normalised (row-wise L2, float64)"),
            "arithmetic_source": {
                "relpath": str(RECALL), "sha256": digest_file(repo / RECALL),
                "functions_used": ["key_construction", "centre_keys"],
                "note": "imported, never re-derived; the read's own --check reproduces its outputs with these functions",
            },
            "construction_pool": kc["pool_info"],
            "pool_mean_sha256_f8le": vector_sha(kc["mu_p"]),
            "label_is": "the pool value's frozen build-time task_target, a released-store property; no gold label enters",
        },
        "centring_statistics": {
            "role": ("the K6p QUERY side subtracts mu_q, the mean of these pinned R01C speech queries "
                     "(scripts/build_slurp_centred_query_vectors.py); recorded here so both artifacts name one "
                     "statistic set. The key side uses the pool mean only."),
            "query_file": {"relpath": recall.STATS_QUERY[0], "sha256": recall.STATS_QUERY[1]},
            "centring_roster": {"relpath": CENTRING_ROSTER, "sha256": digest_file(repo / CENTRING_ROSTER)},
            "rows": len(kc["stats_ids"]), "overlap": kc["stats_overlap"],
            "query_mean_sha256_f8le": vector_sha(kc["mu_q"]),
        },
        "inputs": {k: v for k, v in sorted(kc["files"].items())},
        "measured": {
            "intents": len(intents),
            "centred_from_members": sum(1 for j in range(len(intents)) if per_intent.get(j)),
            "centred_from_written_fallback": [intents[j] for j in range(len(intents)) if not per_intent.get(j)],
            "key_to_key_cosine_mean": round(float(off.mean()), 4),
            "key_to_key_cosine_max": round(float(off.max()), 4),
        },
        "facets": [
            {"id": fid, "members": int(per_intent.get(j, 0)),
             "vector_sha256": digest_text(json.dumps([float(x) for x in keys[j]], separators=(",", ":")))}
            for j, fid in enumerate(ids)
        ],
        "implementation": {
            "speech_aware_evidence_acquisition.rails.kb_policy": digest_file(Path(kb_policy.__file__)),
            "speech_aware_evidence_acquisition.rails.phase_supply": digest_file(Path(phase_supply.__file__)),
        },
        "boundary": ("A pre-computed model-free input, never an authorization: it opens no attempt, reserves no "
                     "contact, admits no mechanism, releases or rebuilds no store and states no effectiveness "
                     "claim. The released store, its facet ids and its delivered bodies are unchanged."),
    }
    receipt_path.write_bytes((json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return {"key": str(key_path), "key_sha256": key_sha, "receipt": str(receipt_path),
            "receipt_sha256": digest_file(receipt_path), "rows": len(lines), "measured": receipt["measured"],
            "pool_mean_sha256_f8le": receipt["construction"]["pool_mean_sha256_f8le"],
            "query_mean_sha256_f8le": receipt["centring_statistics"]["query_mean_sha256_f8le"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--output-root", default=None, help="where prepared/<id>/ is created; default --data-root")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        print(json.dumps({"error": "PYTHONDONTWRITEBYTECODE=1 is required"}), file=sys.stderr)
        return 1
    root = Path(args.data_root).resolve()
    out_root = Path(args.output_root).resolve() if args.output_root else root
    print(json.dumps(build(Path(args.repo_root).resolve(), root, out_root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
