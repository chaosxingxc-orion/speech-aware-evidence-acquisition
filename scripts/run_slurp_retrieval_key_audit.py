#!/usr/bin/env python3
"""CLI: MF-7, the SLURP retrieval-key audit (model-free, zero core contacts).

Authority: owner GO 2026-09-06 plus the owner rule of 2026-09-06 that the
retrieval query must CONTAIN THE SPEECH SIGNAL. Exposure rows
``SAEA-SLURP-MF-RETRIEVAL-KEY-AUDIT-V1`` and ``SAEA-SLURP-MF7-EMBEDDING-CPU-V1``,
both registered before the first read.

I/O ONLY: every measurement, table and receipt field lives in
``analysis.slurp_retrieval_key_audit``. This script resolves the vector
artifacts the ledgered producer passes left under
``$SPEECHRL_DATA_DIR/vectors/slurp-mf7/``, assembles the query sets, prints
the decision block and writes the receipt directory with its ``MANIFEST.sha256``.
No model, tokenizer, embedder, network, GPU or audio contact happens here.

Adding a GPU query set needs no change to this file: drop its
``<set>-query-vectors.jsonl`` / ``<set>-key-vectors.jsonl`` pair into the same
directory in the same schema and name it with ``--query-set``.

Usage (WSL2)::

    python scripts/run_slurp_retrieval_key_audit.py
    python scripts/run_slurp_retrieval_key_audit.py --write
    python scripts/run_slurp_retrieval_key_audit.py --query-set q-speech-lco --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import slurp_retrieval_key_audit as audit  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-slurp-retrieval-key-audit"
)
VECTORS = Path(data_root()) / "vectors/slurp-mf7"
SNAPSHOT_SHA = "e27b274516604ffc0e21319758aea99dc027f459d480a32a74a715b023a51b57"
KEY_NPZ = Path(data_root()) / "knowledge/slurp/saea-kb-distmodel-v1/size-full/vectors-content-facets.npz"
BASELINE_RUN = "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1"
DRAFT_RUN = "SAEA-SLURP-KU-S1C-DRAFT-REVISE-DEV1000-V1"

#: ``query_set_id -> (query jsonl, key source, encoder, contains_speech, fuses_state)``.
#: ``None`` as the key source means the sealed Qwen3 ``.npz``.
CATALOGUE: dict[str, tuple[str, str | None, str, bool, bool]] = {
    "q-draft": ("qwen3emb-q-draft-query-vectors.jsonl", None, "qwen3-embedding-0.6b-q8_0", False, False),
    "q-gold-text": ("qwen3emb-q-gold-text-query-vectors.jsonl", None, "qwen3-embedding-0.6b-q8_0", False, False),
    "q-speech-glap": ("glap-q-speech-query-vectors.jsonl", "glap-key-vectors.jsonl", "glap", True, False),
    "q-speech-glap+state": ("glap-q-speech-query-vectors.jsonl", "glap-key-vectors.jsonl", "glap", True, True),
    "q-speech-lco": ("lco-q-speech-query-vectors.jsonl", "lco-key-vectors.jsonl", "lco-embedding-omni-3b", True, False),
    "q-speech-lco+state": ("lco-q-speech-query-vectors.jsonl", "lco-key-vectors.jsonl", "lco-embedding-omni-3b", True, True),
    "q-speech-nemotron": ("nemotron-q-speech-query-vectors.jsonl", "nemotron-key-vectors.jsonl", "omni-embed-nemotron-3b", True, False),
    "q-speech-nemotron+state": ("nemotron-q-speech-query-vectors.jsonl", "nemotron-key-vectors.jsonl", "omni-embed-nemotron-3b", True, True),
}
DEFAULT_SETS = ("q-draft", "q-gold-text", "q-speech-glap", "q-speech-glap+state")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path) -> None:
    lines = [
        f"{sha256_file(path)} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_query_set(set_id: str, sealed) -> audit.QuerySet:
    query_file, key_file, encoder, speech, state = CATALOGUE[set_id]
    query_path = VECTORS / query_file
    if not query_path.is_file():
        raise SystemExit(f"missing query vectors for {set_id}: {query_path}")
    query_ids, query_vectors = audit.load_vectors_jsonl(query_path)
    if key_file is None:
        key_ids, key_vectors = sealed
        key_source = {"file": KEY_NPZ.name, "sha256": sha256_file(KEY_NPZ), "sealed": True}
    else:
        key_path = VECTORS / key_file
        if not key_path.is_file():
            raise SystemExit(f"missing key vectors for {set_id}: {key_path}")
        key_ids, key_vectors = audit.load_vectors_jsonl(key_path)
        key_source = {"file": key_file, "sha256": sha256_file(key_path), "sealed": False}
    return audit.QuerySet(
        query_set_id=set_id,
        query_ids=query_ids,
        query_vectors=query_vectors,
        key_ids=key_ids,
        key_vectors=key_vectors,
        encoder=encoder,
        contains_speech=speech,
        fuses_state=state,
        provenance={
            "query_vectors": {"file": query_file, "sha256": sha256_file(query_path)},
            "key_vectors": key_source,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    parser.add_argument(
        "--query-set", action="append", choices=sorted(CATALOGUE), default=None,
        help="query sets to measure (repeatable); default: the CPU four",
    )
    parser.add_argument("--decision-k", type=int, default=5)
    args = parser.parse_args()
    set_ids = tuple(args.query_set) if args.query_set else DEFAULT_SETS

    dev_rows = audit.load_dev_rows(VECTORS / "dev-rows.jsonl")
    key_rows = audit.load_key_rows(VECTORS / "train-facets.jsonl")
    weights = audit.RankWeights.from_policy_config(REPO_ROOT / "configs/policy/kb-policy-v1.json")
    sealed = audit.load_sealed_key_npz(KEY_NPZ)

    query_sets = {set_id: build_query_set(set_id, sealed) for set_id in set_ids}
    per_set = {
        set_id: audit.run_query_set(query_set, dev_rows, key_rows, weights)
        for set_id, query_set in query_sets.items()
    }

    accounting = {
        "frozen_core_contacts": 0,
        "gpu_hours": 0.0,
        "model_contacts_by_this_script": 0,
        "producer_receipts": sorted(
            path.name for path in VECTORS.glob("*.receipt.json")
        ),
    }
    summary = audit.build_summary(
        per_set, query_sets, weights, decision_k=args.decision_k,
        baseline_run_id=BASELINE_RUN, draft_run_id=DRAFT_RUN,
        snapshot_sha256=SNAPSHOT_SHA, key_npz_sha256=sha256_file(KEY_NPZ),
        accounting=accounting,
    )
    scenarios = audit.build_scenario_tables(per_set, decision_k=args.decision_k)
    decontamination = audit.decontamination_report(dev_rows, key_rows, query_sets.values())

    print(json.dumps(summary["decision"], indent=1))
    for set_id in set_ids:
        row = summary["query_sets"][set_id]["by_k"][str(args.decision_k)]["NEW500"]
        print(f"{set_id:26s} NEW500 k={args.decision_k} "
              f"recall {row['intent_recall_at_k']:6.2f} vote {row['vote_accuracy_at_k']:6.2f} "
              f"saves {row['saves']:3d} harms {row['harms']:3d} net {row['net_pp']:+6.2f}pp "
              f"filler {row['filler_recall_at_k']:6.2f} echo {row['echo_rate']:6.2f}")
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", summary)
    write_json_artifact(OUT_DIR / "per-query-set-table.json", {
        "schema": audit.AUDIT_SCHEMA,
        "tables": {set_id: summary["query_sets"][set_id]["by_k"] for set_id in set_ids},
    })
    write_json_artifact(OUT_DIR / "per-scenario-table.json", scenarios)
    write_json_artifact(OUT_DIR / "decontamination.json", decontamination)
    write_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
