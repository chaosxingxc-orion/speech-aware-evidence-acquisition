#!/usr/bin/env python3
"""CLI: contact-free Solver-request size estimate for the E3 exemplar supply
(SLURP v2 base program item E3, deliverable 6).

MODEL-FREE. Zero frozen-core, tool, tokenizer, encoder, GPU, server or
network contact. ``core.flight.cli`` modes ``wire-check``/``prompt-fit``
require a registered ``configs/experiment/`` cell plus a root-issued worker
lease (``core.flight.lease.WorkerExecutionPolicy``) -- real campaign
infrastructure this model-free engineering item does not stand up. This
script instead computes, with plain numpy over the REAL sealed vectors and
REAL sealed snapshot this program's E3 items 1-2 produced, exactly what the
flight's own retrieval stack (``rails.knowledge_provider.KbFacetProvider``
-> ``rails.kb_policy.multidim_recall`` -> ``saea-rank-wcos-prior-agree-v1``
-> ``saea-fuse-supplyfilter-v1``) computes for this store's exact knobs
(``w_cos=1, w_prior=0, w_agree=0`` makes rank score equal cosine;
``m=c=top_l=k, tau=0.0`` makes the fuse policy select exactly the top-k
facets by cosine -- 'k in, k out', the same identity
``configs/baseline/slurp-phase-slots-supplied-fillers-speech-v1.json``'s own
``why_the_knobs_are_not_the_blend_lock_s`` note establishes, and this
program's own content snapshot carries exactly one value per content facet,
so 'top-k facets' and 'top-k values' are the same set): for every one of the
1,080 TRAIN Fold A rows, the top-k content facets by cosine against that
row's sealed query vector, mapped to their one associated value each and
rendered through the EXACT
``rails.knowledge_stores.KnowledgeStore.model_evidence_block`` string. It
reports the per-row combined block-text character distribution and a
chars/4 token proxy (the same proxy
``docs/results/2026-09-17-slurp-a2-exemplar-headroom-audit-v1.md`` reports),
never a tokenizer count. A byte-level cross-check against a slow, row-by-row
call into the REAL ``KbFacetProvider``/``multidim_recall``/fuse pipeline for
a random subset of rows is run first and must match exactly before the fast
path's numbers are trusted (see ``verify_against_real_provider``).

Usage::

    python scripts/estimate_slurp_exemplar_prompt_fit.py
    python scripts/estimate_slurp_exemplar_prompt_fit.py --verify-rows 5
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
    QueryState,
)

SNAPSHOT_RELPATH = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
QUERY_VECTORS_RELPATH = "vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl"
FACET_VECTORS_RELPATH = "vectors/slurp-kus3/facet-vectors.jsonl"
DIMENSION = "content"
STORE_ID = "train-exemplars"
STORE_ROLE = "train-exemplars"
SERVING_SLOT_TOKENS = 24576


def _load_flat_vectors(path: Path, *, dimension: str) -> dict[str, list[float]]:
    table: dict[str, list[float]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            document = json.loads(line)
            table[str(document["id"])] = [float(v) for v in document["vectors"][dimension]]
    return table


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct * (len(ordered) - 1))))
    return ordered[index]


def verify_against_real_provider(
    snapshot: KnowledgeSnapshot,
    queries: dict[str, list[float]],
    facet_vectors: dict[str, list[float]],
    facet_id_by_value: dict[str, str],
    k: int,
    sample_ids: list[str],
) -> None:
    """Byte-for-byte cross-check of the fast numpy path against the REAL
    ``KbFacetProvider``/``multidim_recall``/fuse code for a few rows."""

    from speech_aware_evidence_acquisition.rails.kb_policy import FuseKnobs, RankWeights
    from speech_aware_evidence_acquisition.rails.knowledge_provider import KbFacetProvider

    facet_vectors_by_dim = {fid: {DIMENSION: vec} for fid, vec in facet_vectors.items()}
    for sample_id in sample_ids:
        provider = KbFacetProvider(
            build_spec=None,
            rank_policy_id="saea-rank-wcos-prior-agree-v1",
            rank_weights=RankWeights(w_cos=1.0, w_prior=0.0, w_agree=0.0).validate(),
            fuse_knobs=FuseKnobs(tau=0.0, m=k, c=k, top_l=k).validate(),
            top_k_per_dimension=k,
            facet_vectors=lambda facet_id: facet_vectors_by_dim.get(facet_id, {}),
        )
        provider.adopt(
            snapshot, policy_id=f"prompt-fit-verify:k={k}", source_ids=(),
            snapshot_sha256=snapshot.content_hash(),
        )
        query_state = QueryState(
            query_id=f"prompt-fit-verify:k={k}:{sample_id}",
            query_sample_id=sample_id,
            speech_packet_id=f"speech/{sample_id}",
            speech_packet_sha256="0" * 64,
            use_split_identity_hash="0" * 64,
            query_source="speech_features",
        ).validate()
        ranking = provider.candidates(
            {"query_state": query_state, "query_vectors": {DIMENSION: queries[sample_id]}}, k=k
        )
        decision = provider.fuse([ranking], k=k, policy_id="saea-fuse-supplyfilter-v1")
        real_facet_ids = {facet_id_by_value[vid] for vid in decision.selected_value_ids}

        query_vec = np.asarray(queries[sample_id], dtype=np.float64)
        query_vec = query_vec / np.linalg.norm(query_vec)
        facet_ids_sorted = sorted(facet_vectors)
        matrix = np.asarray([facet_vectors[fid] for fid in facet_ids_sorted], dtype=np.float64)
        norms = np.linalg.norm(matrix, axis=1)
        norms[norms == 0] = 1.0
        cosines = (matrix @ query_vec) / norms
        top_indices = np.argsort(-cosines, kind="stable")[:k]
        fast_facet_ids = {facet_ids_sorted[i] for i in top_indices}

        if fast_facet_ids != real_facet_ids:
            raise SystemExit(
                f"verification FAILED for {sample_id} at k={k}: fast path facets "
                f"{sorted(fast_facet_ids)} != real provider facets {sorted(real_facet_ids)}"
            )
    print(f"verified {len(sample_ids)} row(s) at k={k}: fast numpy path matches the real provider exactly")


def estimate_for_k(
    snapshot: KnowledgeSnapshot,
    queries: dict[str, list[float]],
    facet_vectors: dict[str, list[float]],
    value_content_by_facet: dict[str, str],
    k: int,
) -> dict[str, object]:
    facet_ids_sorted = sorted(facet_vectors)
    facet_matrix = np.asarray([facet_vectors[fid] for fid in facet_ids_sorted], dtype=np.float64)
    facet_norms = np.linalg.norm(facet_matrix, axis=1)
    facet_norms[facet_norms == 0] = 1.0
    normalized_facets = facet_matrix / facet_norms[:, None]

    sample_ids = sorted(queries)
    query_matrix = np.asarray([queries[sid] for sid in sample_ids], dtype=np.float64)
    query_norms = np.linalg.norm(query_matrix, axis=1)
    query_norms[query_norms == 0] = 1.0
    normalized_queries = query_matrix / query_norms[:, None]

    # (rows, facets) cosine matrix in one matmul.
    cosines = normalized_queries @ normalized_facets.T

    per_row_chars: list[int] = []
    per_row_block_counts: list[int] = []
    for row_index in range(cosines.shape[0]):
        row_scores = cosines[row_index]
        top_indices = np.argsort(-row_scores, kind="stable")[:k]
        total_chars = 0
        blocks = 0
        for idx in top_indices:
            facet_id = facet_ids_sorted[idx]
            content = value_content_by_facet.get(facet_id)
            if content is None:
                continue
            block_text = f"[knowledge store={STORE_ID} role={STORE_ROLE}] {content}"
            total_chars += len(block_text)
            blocks += 1
        per_row_chars.append(total_chars)
        per_row_block_counts.append(blocks)

    mean_chars = statistics.mean(per_row_chars)
    return {
        "k": k,
        "rows": len(per_row_chars),
        "mean_blocks_per_row": round(statistics.mean(per_row_block_counts), 3),
        "chars": {
            "mean": round(mean_chars, 1),
            "p50": _percentile(per_row_chars, 0.50),
            "p95": _percentile(per_row_chars, 0.95),
            "max": max(per_row_chars),
        },
        "tokens_chars_over_4_proxy": {
            "mean": round(mean_chars / 4, 1),
            "p95": round(_percentile(per_row_chars, 0.95) / 4, 1),
            "max": round(max(per_row_chars) / 4, 1),
        },
        "serving_slot_tokens": SERVING_SLOT_TOKENS,
        "max_over_serving_slot": (max(per_row_chars) / 4) > SERVING_SLOT_TOKENS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify-rows", type=int, default=3,
        help="rows to cross-check against the real provider per k (0 disables)",
    )
    args = parser.parse_args()

    root = data_root()
    snapshot = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / SNAPSHOT_RELPATH).read_text(encoding="utf-8"))
    )
    queries = _load_flat_vectors(root / QUERY_VECTORS_RELPATH, dimension=DIMENSION)
    facet_vectors_all = _load_flat_vectors(root / FACET_VECTORS_RELPATH, dimension=DIMENSION)
    # The sealed facet-vector file is a SUPERSET (11,514 governed TRAIN
    # utterances); the real KbFacetProvider/multidim_recall only ever
    # recalls among facets the SNAPSHOT itself declares (9,354, after the
    # Fold A/B/DEV-1000 exclusion) -- candidates outside that set must never
    # enter the top-k competition, or the fast path silently recalls
    # EXCLUDED rows the flight itself can never select.
    snapshot_content_facet_ids = {
        facet.facet_id for facet in snapshot.facets if facet.dimension == "content"
    }
    facet_vectors = {
        fid: vec for fid, vec in facet_vectors_all.items() if fid in snapshot_content_facet_ids
    }
    missing = snapshot_content_facet_ids - set(facet_vectors)
    if missing:
        raise SystemExit(f"{len(missing)} snapshot facet(s) have no sealed vector")

    # facet_id -> value content, and facet_id -> value_id (one value per
    # content facet in this snapshot; asserted, not assumed).
    facet_id_by_value: dict[str, str] = {}
    value_content_by_facet: dict[str, str] = {}
    for value in snapshot.values:
        content_facets = [
            fid for fid in value.associated_facet_ids if fid.startswith("facet:content:")
        ]
        if len(content_facets) != 1:
            raise SystemExit(
                f"value {value.value_id} carries {len(content_facets)} content facets, "
                "expected exactly 1"
            )
        facet_id_by_value[value.value_id] = content_facets[0]
        value_content_by_facet[content_facets[0]] = value.content

    results = []
    for k in (20, 12):
        if args.verify_rows:
            import random

            sample = random.Random(20260917).sample(sorted(queries), args.verify_rows)
            verify_against_real_provider(
                snapshot, queries, facet_vectors, facet_id_by_value, k, sample
            )
        results.append(estimate_for_k(snapshot, queries, facet_vectors, value_content_by_facet, k))

    report = {
        "schema": "saea-e3-exemplar-prompt-fit-estimate-v1",
        "method": (
            "numpy top-k cosine over the sealed snapshot and sealed vectors (verified "
            "against the real KbFacetProvider/rank/fuse pipeline for a random row "
            "subset); block text is the exact model_evidence_block rendering; token "
            "counts are the chars/4 proxy, never a tokenizer contact"
        ),
        "snapshot_relpath": SNAPSHOT_RELPATH,
        "snapshot_sha256": snapshot.content_hash(),
        "query_vectors_relpath": QUERY_VECTORS_RELPATH,
        "results": results,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
