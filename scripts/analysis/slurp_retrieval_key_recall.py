#!/usr/bin/env python3
"""SLURP Perception boundary block: a NEW retrieval key for off-block intent recall (offline, DESCRIPTIVE).

Read id ``SAEA-SLURP-RETRIEVAL-KEY-RECALL-OFFLINE-V1``. Model-free: zero model, server, tokenizer,
encoder, embedder, GPU, network and paid-API contacts; no official-scorer subprocess (per-row
official scores are read from sealed score files); ``core.flight.cli`` and ``lease_cli`` are never
invoked. Every key is arithmetic over ALREADY-PINNED vectors and tables:

* the Perception boundary query vectors of TRAIN Fold A and Fold B (sealed segment vectors, the
  ``intent-boundary`` dimension);
* the construction pool's pinned per-utterance vectors (``vectors/slurp-kus3/facet-vectors.jsonl``,
  ``content`` dimension) restricted to the R01-excluded pool snapshot, MINUS every utterance of
  TRAIN Fold A, TRAIN Fold B, R01 and R01C (roster receipts under ``docs/receipts/rosters/``);
  each member's intent is the pool value's frozen build-time ``task_target`` (a store property);
* the flown written-description key, the pinned centroid key and the pinned agreement tables.

Gold enters ONLY through the governed TRAIN loader (``data.slurp.load_slurp_split``) and ONLY to
score recall on the two read rosters -- never in key construction. Utterance text, transcripts,
slot fillers, note text and model output are never read into a printed or persisted value: ids,
closed-set intent labels in aggregate counts, counts, ranks, rates, cosines, pp and hashes only.

Keys (depth-8 block, the production ``saea-rank-wcos-prior-agree-v1`` arithmetic
``w_cos * cos + w_agree * share`` and the ``saea-fuse-associated-values-v1`` first-m block):

* baselines ``desc_agree`` (flown in AGREE and P-SV) and ``cent_agree`` (COMP-1b; the confirmed
  boundary key), plus ``cent_cos`` and ``vote`` for the diagnosis;
* K1 multi-prototype centroids (spherical k-means, P = 2/3/4 per intent; score = max prototype
  cosine), alone and with the pinned agreement;
* K2 construction-pool kNN vote (m = 10/20/40, count or cosine weighted) replacing or adding to
  the pinned agreement, and ``nn1`` (the intent's nearest construction utterance);
* K3 the centroid + agreement key with a catch-all floor (``general_quirky`` [and
  ``qa_factoid``] inserted at block position 8 when the row's best centroid cosine is low;
  threshold cross-fitted);
* K4 scenario-first (soft: + lambda * scenario-centroid cosine; hard: top-s scenarios first);
* K5 reciprocal-rank fusion of ``cent_agree`` with K1 / K2 / nn1.

Every tuned parameter is cross-fitted by sha256(utterance id) halves (chosen on one half, applied
to the other). ``--check`` re-derives both outputs and compares them apart from ``generated_at``.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import numpy as np  # noqa: E402

READ_ID = "SAEA-SLURP-RETRIEVAL-KEY-RECALL-OFFLINE-V1"
RECIPE = "slurp-retrieval-key-recall-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080
D = 8
IB_DIM = "intent-boundary"
IB_FACET_MARK = "intent-boundary:"
RRF_C = 60
KMEANS_ITERS = 60
PROTOS = (2, 3, 4)
KNN_M = (10, 20, 40)
LAMBDAS = (0.25, 0.5, 1.0, 2.0)
HARD_S = (2, 3, 4)
SHARE_W = (0.5, 1.0, 2.0)
THETA_Q = tuple(round(0.05 * i, 2) for i in range(1, 11))  # 0.05 .. 0.50
CATCH_SETS = {"gq": ("general_quirky",), "gq+qaf": ("general_quirky", "qa_factoid")}
FAR_QUANTILE = 0.25
CSLS_K = (10, 50)
AGREE_W = (0.5, 1.0, 2.0)
#: The hub statistics (K6-K8) come from the pinned R01C construction-roster speech queries: a
#: TRAIN construction roster with no utterance in Fold A, Fold B or the construction pool.
STATS_QUERY = ("vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-segments.jsonl",
               "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8")

CFG_AGREE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
CFG_COMP1B = "configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json"
CFG_PSV1 = "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1-resume.json"
RUN_AGREE = ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1")
RUN_COMP1B = ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1", "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1")
RUN_PSV1 = ("SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1", "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only")
RUN_PSV3 = ("SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1", "attempt-slurp-native-stage3-psv3-fold-b-generation-v1")
ROSTERS = {
    "fold_a": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "fold_b": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "r01": "docs/receipts/rosters/slurp-stage3-construction-r01.json",
    "r01c": "docs/receipts/rosters/slurp-stage3-construction-r01c.json",
}
DIAG = "scripts/analysis/slurp_boundary_key_construction_diagnostic.py"
CENTROID_BUILDER = "scripts/build_slurp_intent_boundary_centroid_keys.py"
BRANCH_READ = "scripts/analysis/slurp_perception_branch_read.py"


class ReadError(RuntimeError):
    pass


def import_path(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# pure functions (unit-tested on fakes)


def split_half(utterance_id: str) -> int:
    """The supply-abstention / block-depth reads' utterance half (sha256 of the utterance id, mod 2)."""
    return int(hashlib.sha256(str(utterance_id).encode("utf-8")).hexdigest(), 16) % 2


def scenario_of(intent: str) -> str:
    return str(intent).split("_", 1)[0]


def is_catch_all(intent: str) -> bool:
    """The brief's catch-all set: ``general_*`` and ``qa_*``."""
    return scenario_of(intent) in ("general", "qa")


def unit_rows(matrix) -> np.ndarray:
    work = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(work, axis=1, keepdims=True)
    return work / np.where(norms > 0.0, norms, 1.0)


def order_from_scores(scores: np.ndarray, intents: list, admitted: np.ndarray | None = None) -> list:
    """Per row: intents by score descending, intent (= facet id) ascending; non-admitted dropped."""
    n, k = scores.shape
    tie = np.arange(k)  # intents are sorted, so column order IS facet-id order
    out = []
    for i in range(n):
        cols = np.arange(k) if admitted is None else np.flatnonzero(admitted[i])
        cols = cols[np.lexsort((tie[cols], -scores[i, cols]))]
        out.append([intents[c] for c in cols])
    return out


def block_of(order: list, has_cos: set | None = None, d: int = D) -> list:
    """The associated-values fuser's block: the first ``d`` ranked facets, a facet without a
    recalled cosine skipped (one value per facet, c = 1)."""
    return [x for x in order[:d] if has_cos is None or x in has_cos]


def rank_of(order, item):
    for i, x in enumerate(order):
        if x == item:
            return i + 1
    return None


def in_block(rank, d: int = D) -> bool:
    return rank is not None and rank <= d


def spherical_kmeans(x: np.ndarray, p: int, seed: int, iters: int = KMEANS_ITERS) -> np.ndarray:
    """Deterministic spherical k-means (k-means++ init from ``seed``) over unit rows; returns up to
    ``p`` unit prototypes (fewer when there are fewer rows or an empty cluster collapses)."""
    x = unit_rows(x)
    n = len(x)
    if n == 0:
        return np.zeros((0, x.shape[1] if x.ndim == 2 else 0))
    p = max(1, min(p, n))
    rng = np.random.default_rng(seed)
    centres = [x[int(rng.integers(n))]]
    while len(centres) < p:
        sims = x @ np.asarray(centres).T
        dist = np.clip(1.0 - sims.max(axis=1), 0.0, None)
        tot = dist.sum()
        if tot <= 0:
            break
        centres.append(x[int(rng.choice(n, p=dist / tot))])
    c = unit_rows(np.asarray(centres))
    assign = None
    for _ in range(iters):
        new = np.argmax(x @ c.T, axis=1)
        if assign is not None and np.array_equal(new, assign):
            break
        assign = new
        rows = []
        for j in range(len(c)):
            members = x[assign == j]
            if len(members):
                rows.append(members.mean(axis=0))
        c = unit_rows(np.asarray(rows))
    return c


def knn_shares(sims: np.ndarray, labels: np.ndarray, n_labels: int, m: int, weighted: bool) -> np.ndarray:
    """Per row: the share of the top-``m`` most similar pool members voting for each label
    (ties by pool position); ``weighted`` weights each vote by its (positive) cosine."""
    n = sims.shape[0]
    out = np.zeros((n, n_labels))
    part = np.argpartition(-sims, m - 1, axis=1)[:, :m] if m < sims.shape[1] else np.tile(np.arange(sims.shape[1]), (n, 1))
    for i in range(n):
        cols = part[i]
        cols = cols[np.lexsort((cols, -sims[i, cols]))][:m]
        w = np.clip(sims[i, cols], 0.0, None) if weighted else np.ones(len(cols))
        np.add.at(out[i], labels[cols], w)
        tot = out[i].sum()
        if tot > 0:
            out[i] /= tot
    return out


def group_max(sims: np.ndarray, labels: np.ndarray, n_labels: int, fill: float = -1.0) -> np.ndarray:
    """Per row and label: the max similarity over the label's pool members (``fill`` if none)."""
    out = np.full((sims.shape[0], n_labels), fill)
    for j in range(n_labels):
        cols = np.flatnonzero(labels == j)
        if len(cols):
            out[:, j] = sims[:, cols].max(axis=1)
    return out


def rrf(orders: list, intents: list, c: int = RRF_C) -> list:
    """Reciprocal-rank fusion of several per-row orders; ties by intent ascending."""
    out = []
    n = len(orders[0])
    for i in range(n):
        score = defaultdict(float)
        for od in orders:
            for r, x in enumerate(od[i]):
                score[x] += 1.0 / (c + r + 1)
        out.append(sorted(intents, key=lambda x: (-score.get(x, 0.0), x)))
    return out


def csls_penalty(keys: np.ndarray, stats_queries: np.ndarray, k: int) -> np.ndarray:
    """Per key: the mean cosine to its ``k`` most similar statistics queries (the CSLS hubness term)."""
    sims = stats_queries @ keys.T
    k = min(k, sims.shape[0])
    top = -np.sort(-sims, axis=0)[:k]
    return top.mean(axis=0)


def key_bias(keys: np.ndarray, stats_queries: np.ndarray) -> tuple:
    """Per key: mean and standard deviation of its cosine over the statistics queries."""
    sims = stats_queries @ keys.T
    return sims.mean(axis=0), sims.std(axis=0)


def catch_all_floor(order: list, top_cos: float, theta: float, catch: tuple, d: int = D) -> list:
    """If the row's best centroid cosine is below ``theta``, move each catch-all intent absent from
    the first ``d`` into the block's last slot(s), displacing the lowest-ranked block items."""
    if top_cos >= theta:
        return list(order)
    head = list(order[:d])
    missing = [c for c in catch if c not in head and c in order]
    if not missing:
        return list(order)
    keep = head[:d - len(missing)]
    rest = [x for x in order if x not in keep and x not in missing]
    return keep + missing + rest


def scenario_first(order: list, scen_rank: list, s: int) -> list:
    """Intents of the row's top-``s`` scenarios first (in ``order``), then the rest (in ``order``)."""
    top = set(scen_rank[:s])
    return [x for x in order if scenario_of(x) in top] + [x for x in order if scenario_of(x) not in top]


def implied(ranks: dict, table: dict, ids) -> float:
    """Sum over rows of a per-block-rank rate (rank 1..8, else 'off')."""
    return float(sum(table[str(ranks[s])] if in_block(ranks[s]) else table["off"] for s in ids))


def rate_table(block_rank: dict, outcome: dict, ids) -> dict:
    """P(outcome | gold at sealed block rank r), r = 1..8 and 'off'."""
    out = {}
    for r in [str(i) for i in range(1, D + 1)] + ["off"]:
        sel = [s for s in ids if (str(block_rank[s]) == r if r != "off" else block_rank[s] is None)]
        out[r] = (sum(1 for s in sel if outcome[s]) / len(sel)) if sel else 0.0
    return out


def compare(base: dict, alt: dict, ids, correct: dict, targets: set, pnote: dict, pcorr: dict) -> dict:
    """Net rows at depth 8, target recovery, rank movement and implied note / intent effects."""
    ids = list(ids)
    enters = [s for s in ids if not in_block(base[s]) and in_block(alt[s])]
    leaves = [s for s in ids if in_block(base[s]) and not in_block(alt[s])]
    base_in = [s for s in ids if in_block(base[s])]
    new_rank = [alt[s] if in_block(alt[s]) else D + 1 for s in base_in]
    return {
        "rows": len(ids),
        "gold_in_block": sum(1 for s in ids if in_block(alt[s])),
        "gold_in_block_base": len(base_in),
        "enters": len(enters), "leaves": len(leaves), "net": len(enters) - len(leaves),
        "enters_intent_wrong": sum(1 for s in enters if not correct[s]),
        "leaves_delivered_correct": sum(1 for s in leaves if correct[s]),
        "targets": len(targets & set(ids)),
        "targets_recovered": sum(1 for s in targets if s in set(ids) and in_block(alt[s])),
        "rank1": sum(1 for s in ids if alt[s] == 1),
        "rank1_base": sum(1 for s in ids if base[s] == 1),
        "base_in_block_mean_rank_base": round(sum(base[s] for s in base_in) / len(base_in), 4) if base_in else None,
        "base_in_block_mean_rank_alt": round(sum(new_rank) / len(new_rank), 4) if new_rank else None,
        "moved_to_rank1": sum(1 for s in ids if alt[s] == 1 and base[s] != 1),
        "moved_off_rank1": sum(1 for s in ids if base[s] == 1 and alt[s] != 1),
        "moved_off_rank1_delivered_correct": sum(1 for s in ids if base[s] == 1 and alt[s] != 1 and correct[s]),
        "implied_note_base": round(implied(base, pnote, ids), 3),
        "implied_note_alt": round(implied(alt, pnote, ids), 3),
        "implied_note_delta": round(implied(alt, pnote, ids) - implied(base, pnote, ids), 3),
        "implied_intent_delta": round(implied(alt, pcorr, ids) - implied(base, pcorr, ids), 3),
    }


def crossfit_choose(candidates: dict, half: dict, criterion) -> dict:
    """``candidates``: label -> {sid: rank}. On each half pick the label maximising
    ``criterion(ranks, ids)`` (first label wins ties); apply it to the OTHER half."""
    labels = list(candidates)
    chosen = {}
    for h in (0, 1):
        own = [s for s in half if half[s] == h]
        best = max(labels, key=lambda lab: (criterion(candidates[lab], own), -labels.index(lab)))
        chosen[h] = best
    composite = {}
    for s, h in half.items():
        composite[s] = candidates[chosen[1 - h]][s]
    return {"chosen_on_half": {str(h): chosen[h] for h in (0, 1)}, "ranks": composite}


def top_counts(counter: Counter, n: int) -> list:
    """The ``n`` largest counts, ties by label ascending (hash-order free)."""
    return [[k, v] for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def classify_miss(row: dict, far_cut: float) -> str:
    """Exclusive taxonomy, in the brief's order: (a) catch-all gold whose speech is far from every
    centroid; (b) sibling confusion (delivered top-1 shares gold's scenario); (c) multi-modal (gold's
    nearest construction utterance ranks it in the top 8 while its centroid does not); (d) other."""
    if row["catch_all"] and row["top1_cent_cos"] < far_cut:
        return "a"
    if row["rival_same_scenario"]:
        return "b"
    if in_block(row["rank_nn1"]) and not in_block(row["rank_cent_cos"]):
        return "c"
    return "d"


# ---------------------------------------------------------------------------
# I/O and computation


def roster_ids(path: Path) -> list:
    doc = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for item in doc["items"]:
        sid = item.get("sample_id") or item.get("id")
        if not isinstance(sid, str):
            raise ReadError(f"{path}: roster item without a sample id")
        out.append(sid)
    return out


# ---------------------------------------------------------------------------
# K6p construction (shared with scripts/build_slurp_centred_centroid_key.py and
# scripts/build_slurp_centred_query_vectors.py: the builders call THESE functions)


def centre_keys(raw_means, mu_p) -> np.ndarray:
    """The K6/K6p key: each intent's raw member mean minus the construction-pool mean, re-normalised."""

    return unit_rows(np.asarray(raw_means, dtype=np.float64) - np.asarray(mu_p, dtype=np.float64))


def centre_queries(q, mu_q) -> np.ndarray:
    """The K6/K6p query: each (unit) speech query minus the R01C speech-query mean, re-normalised."""

    return unit_rows(np.asarray(q, dtype=np.float64) - np.asarray(mu_q, dtype=np.float64))


def key_construction(root: Path, diag, cbuild, centroid_pin: dict | None = None) -> dict:
    """Everything the keys are built from, read from pinned bytes only (zero contacts, gold-free):
    the released 60-way boundary store and its written key; the pinned centroid key (when
    ``centroid_pin`` is given); the R01-excluded construction pool minus every utterance of TRAIN
    Fold A, Fold B, R01 and R01C (unit member vectors ``P``, store-property ``labels``); the raw
    per-intent member means and the pool mean ``mu_p``; and the pinned R01C speech queries ``SQ``
    with their mean ``mu_q`` (the hub statistics). ``files`` pins every input read."""

    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_segment_vectors, load_sealed_vectors)

    files = {}
    store = diag.load_boundary(root)
    intents = list(store["intents"])
    if len(intents) != 60:
        raise ReadError("boundary store is not 60-way")
    idx = {x: i for i, x in enumerate(intents)}
    written = store["matrix"]
    centroid = None
    if centroid_pin is not None:
        cent_vecs = load_sealed_vectors(root / centroid_pin["relpath"], expected_sha256=centroid_pin["sha256"], dimensions=(IB_DIM,))
        centroid = unit_rows([cent_vecs[IB_FACET_MARK + x][IB_DIM] for x in intents])
        files[centroid_pin["relpath"]] = centroid_pin["sha256"]

    # ---- construction pool: R01-excluded pool snapshot minus Fold A / Fold B / R01 / R01C
    pool = cbuild.pool_labels(root, diag.POOL_M, cbuild.POOL_M_SHA)
    pool_keyed = diag.load_pool(root, diag.POOL_M, cbuild.POOL_M_SHA)["keyed"]
    files[diag.POOL_M] = cbuild.POOL_M_SHA
    excl = {}
    roster_members = {}
    for name, rel in ROSTERS.items():
        ids_r = roster_ids(REPO_ROOT / rel)
        files["repo:" + rel] = digest(REPO_ROOT / rel)
        roster_members[name] = {diag.own_key(s) for s in ids_r}
        excl[name] = sum(1 for f in pool["facets"] if pool_keyed[f] in roster_members[name])
    all_excl = set().union(*roster_members.values())
    members = [f for f in pool["facets"] if pool_keyed[f] not in all_excl]
    vecs = diag.load_pool_vectors(root, set(pool["facets"]))
    files[diag.POOL_FACETS] = diag.POOL_FACETS_SHA
    P = unit_rows([vecs[f] for f in members])
    del vecs
    labels = np.asarray([idx[pool["labels"][f]] for f in members], dtype=np.int64)
    per_intent = Counter(labels.tolist())
    no_member = [intents[j] for j in range(60) if per_intent.get(j, 0) == 0]
    pool_info = {"snapshot": diag.POOL_M, "snapshot_sha256": cbuild.POOL_M_SHA, "snapshot_utterances": len(pool["facets"]),
                 "excluded_by_roster": excl, "construction_members": len(members),
                 "intents_without_member": no_member, "members_min": min(per_intent.values()),
                 "members_max": max(per_intent.values())}
    if centroid is not None:
        # the pinned centroid key must be reproduced from this pool (exact when nothing extra is excluded)
        recomputed = np.asarray([unit_rows(P[labels == j].mean(axis=0, keepdims=True))[0] if per_intent.get(j) else written[j]
                                 for j in range(60)])
        cent_diff = float(np.abs(recomputed - centroid).max())
        pool_info["recomputed_centroid_max_abs_diff_vs_pinned"] = cent_diff
        if cent_diff > 1e-9 and sum(excl.values()) == 0:
            raise ReadError("the construction pool does not reproduce the pinned centroid key")
    # hub statistics: pinned R01C construction-roster speech queries (gold-free, disjoint from both folds)
    stats_q = load_sealed_segment_vectors(root / STATS_QUERY[0], expected_sha256=STATS_QUERY[1], dimensions=(IB_DIM,))
    files[STATS_QUERY[0]] = STATS_QUERY[1]
    if any(len(v.segments) != 1 for v in stats_q.values()):
        raise ReadError("a statistics query carries more than one segment")
    stats_ids = sorted(stats_q)
    SQ = unit_rows([stats_q[s].segments[0][IB_DIM] for s in stats_ids])
    del stats_q
    stats_overlap = {name: sum(1 for s in stats_ids if diag.own_key(s) in roster_members[name]) for name in ("fold_a", "fold_b")}
    stats_overlap["pool"] = sum(1 for s in stats_ids if diag.own_key(s) in {pool_keyed[f] for f in members})
    mu_p = P.mean(axis=0)
    mu_q = SQ.mean(axis=0)
    raw_means = np.asarray([P[labels == j].mean(axis=0) if per_intent.get(j) else written[j] for j in range(60)])
    return {
        "store": store, "intents": intents, "idx": idx, "written": written, "centroid": centroid,
        "pool": pool, "members": members, "P": P, "labels": labels, "per_intent": per_intent,
        "roster_members": roster_members, "pool_info": pool_info, "stats_ids": stats_ids, "SQ": SQ,
        "stats_overlap": stats_overlap, "mu_p": mu_p, "mu_q": mu_q, "raw_means": raw_means, "files": files,
    }


def build(args) -> dict:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_agreement, load_sealed_segment_vectors, load_sealed_vectors)

    diag = import_path(REPO_ROOT / DIAG, "_rk_boundary_key_diagnostic")
    cbuild = import_path(REPO_ROOT / CENTROID_BUILDER, "_rk_centroid_builder")
    BR = import_path(REPO_ROOT / BRANCH_READ, "slurp_perception_branch_read")
    root = Path(args.data_root)
    files = {}
    checks = Counter()
    for rel in (DIAG, CENTROID_BUILDER, BRANCH_READ, CFG_AGREE, CFG_COMP1B, CFG_PSV1):
        files["repo:" + rel] = digest(REPO_ROOT / rel)

    # ---- gold (scoring only)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, root, "train", workers=4)
    gold = {r.sample_id: r.intent for r in records}
    utt = {r.sample_id: r.utterance_id for r in records}
    del records

    # ---- specs
    def spec(cfg_rel):
        cfg = json.loads((REPO_ROOT / cfg_rel).read_text(encoding="utf-8"))
        return cfg["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]

    sa, sc, sb = spec(CFG_AGREE), spec(CFG_COMP1B), spec(CFG_PSV1)
    for s_ in (sc, sb):
        for fld in ("k", "tau", "rank_weights", "fuse_coverage", "fuse_policy", "rank_policy"):
            checks[f"spec_equal_{fld}"] += int(s_[fld] == sa[fld])
    if sa["rank_weights"] != {"w_agree": 1.0, "w_cos": 1.0, "w_prior": 0.0} or sa["fuse_coverage"] != {"c": 1, "m": 8, "top_l": 8}:
        raise ReadError("the flown boundary spec is not w_cos/w_agree 1/1, m/c/top_l 8/1/8")

    # ---- boundary store, written and centroid keys; construction pool; hub statistics
    kc = key_construction(root, diag, cbuild, centroid_pin=sc["facet_source"])
    store, intents, idx, written = kc["store"], kc["intents"], kc["idx"], kc["written"]
    centroid = kc["centroid"]
    files.update(kc["files"])
    files[sa["facet_source"]["relpath"]] = sa["facet_source"]["sha256"]
    pool, members, P, labels = kc["pool"], kc["members"], kc["P"], kc["labels"]
    per_intent, roster_members, pool_info = kc["per_intent"], kc["roster_members"], kc["pool_info"]
    stats_ids, SQ, stats_overlap = kc["stats_ids"], kc["SQ"], kc["stats_overlap"]
    mu_p, mu_q, raw_means = kc["mu_p"], kc["mu_q"], kc["raw_means"]
    cent_centred = centre_keys(raw_means, mu_p)
    csls = {k: csls_penalty(centroid, SQ, k) for k in CSLS_K}
    kb_mu, kb_sd = key_bias(centroid, SQ)
    stats_info = {"relpath": STATS_QUERY[0], "sha256": STATS_QUERY[1], "rows": len(stats_ids), "overlap": stats_overlap,
                  "key_bias_mean_range": [round(float(kb_mu.min()), 4), round(float(kb_mu.max()), 4)],
                  "key_bias_sd_mean": round(float(kb_sd.mean()), 4)}
    scen_names = sorted({scenario_of(x) for x in intents})
    scen_idx = {x: i for i, x in enumerate(scen_names)}
    scen_labels = np.asarray([scen_idx[scenario_of(intents[j])] for j in labels], dtype=np.int64)
    scen_cent = unit_rows([P[scen_labels == k].mean(axis=0) for k in range(len(scen_names))])

    # K1 prototypes
    protos = {}
    for p in PROTOS:
        rows, owner = [], []
        for j in range(60):
            if per_intent.get(j):
                seed = int(hashlib.sha256(intents[j].encode("utf-8")).hexdigest()[:8], 16)
                c = spherical_kmeans(P[labels == j], p, seed)
            else:
                c = written[j:j + 1]
            rows.extend(c)
            owner.extend([j] * len(c))
        protos[p] = (np.asarray(rows), np.asarray(owner))

    # ---- sealed pools
    def run_dir(run):
        return root / "runs" / run[0] / run[1]

    def load_phases(run):
        path = run_dir(run) / f"{run[0]}.phases.json"
        files[str(path.relative_to(root))] = digest(path)
        doc = json.loads(path.read_text(encoding="utf-8"))
        out = {}
        for res in doc["phases"][0]["results"]:
            note = []
            for st in res.get("agent_states") or ():
                if st.get("state_kind") == "phase:perception":
                    try:
                        payload = json.loads(st.get("content") or "")
                        note = list(dict.fromkeys(str(c.get("intent_id")) for c in payload.get("candidates") or ()))
                    except (ValueError, AttributeError, TypeError):
                        note = []
                    break
            block = [v.split(IB_FACET_MARK, 1)[-1] for v in res["initial_query_state"]["retrieved_value_ids"] if IB_FACET_MARK in v]
            out[res["sample_id"]] = {"note": note, "block": block}
        return out

    def load_scores(path):
        files[str(path.relative_to(root))] = digest(path)
        block = json.loads(path.read_text(encoding="utf-8"))[SCORER]
        return {str(s["sample_id"]): bool(s["scenario_action_exact"] >= 1.0) for s in block["per_sample"]}

    def load_branch(run, arm):
        path = run_dir(run) / f"{run[0]}.outputs.jsonl"
        files[str(path.relative_to(root))] = digest(path)
        out = {}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                row = json.loads(line)
                for item in row["native_episode_receipt"]["perception_branches"]["branches"]:
                    if item["branch_id"] == arm:
                        out[row["sample_id"]] = {
                            "note": list(BR.branch_candidates(item)),
                            "block": [v.split(IB_FACET_MARK, 1)[-1] for v in item.get("supplied_value_ids") or ()]}
        return out

    agree_ph, comp_ph = load_phases(RUN_AGREE), load_phases(RUN_COMP1B)
    agree_ok = load_scores(run_dir(RUN_AGREE) / f"{RUN_AGREE[0]}.scores.json")
    comp_ok = load_scores(run_dir(RUN_COMP1B) / f"{RUN_COMP1B[0]}.scores.json")
    psv1 = load_branch(RUN_PSV1, "a-agree")
    psv3 = load_branch(RUN_PSV3, "a-agree")
    psv1_ok = load_scores(run_dir(RUN_PSV1) / "supply-variants" / f"arm-a-agree-{SCORER}-scores.json")
    ids = {"A": sorted(agree_ph), "B": sorted(psv1)}
    if sorted(comp_ph) != ids["A"] or sorted(psv3) != ids["B"] or any(len(v) != ROWS for v in ids.values()):
        raise ReadError("rosters differ")
    for fold, name in (("A", "fold_a"), ("B", "fold_b")):
        checks[f"{fold}_rows_in_roster_receipt"] = sum(1 for s in ids[fold] if diag.own_key(s) in roster_members[name])

    # ---- queries and pinned agreement
    def fold_inputs(sp, fold_ids):
        q = load_sealed_segment_vectors(root / sp["query_source"]["relpath"], expected_sha256=sp["query_source"]["sha256"], dimensions=(IB_DIM,))
        agr = load_sealed_agreement(root / sp["agreement_source"]["relpath"], expected_sha256=sp["agreement_source"]["sha256"],
                                    dimension="agreement:exemplar-intent", facet_ids=[IB_FACET_MARK + x for x in intents])
        files[sp["query_source"]["relpath"]] = sp["query_source"]["sha256"]
        files[sp["agreement_source"]["relpath"]] = sp["agreement_source"]["sha256"]
        segs = Counter(len(q[s].segments) for s in fold_ids)
        mats = [unit_rows([q[s].segments[k][IB_DIM] for s in fold_ids]) for k in range(max(segs))] if set(segs) == {1} else None
        if mats is None:
            raise ReadError("a row carries more than one speech segment; this read handles one")
        share = np.zeros((len(fold_ids), 60))
        for i, s in enumerate(fold_ids):
            for f, v in agr.get(s, {}).items():
                share[i, idx[f.split(IB_FACET_MARK, 1)[-1]]] = v
        return mats[0], share, dict(segs)

    Q, SH, segs = {}, {}, {}
    Q["A"], SH["A"], segs["A"] = fold_inputs(sa, ids["A"])
    Q["B"], SH["B"], segs["B"] = fold_inputs(sb, ids["B"])

    # ---- per-fold key orders
    orders, top_cos, diag_rows_all, k6p_admitted = {}, {}, {}, {}
    for fold in ("A", "B"):
        q, share = Q[fold], SH[fold]
        cos_w = q @ written.T
        cos_c = q @ centroid.T
        sims = q @ P.T
        o = {}
        adm_w, adm_c = cos_w > 0.0, cos_c > 0.0
        o["desc_cos"] = order_from_scores(cos_w, intents, adm_w)
        o["desc_agree"] = order_from_scores(cos_w + share, intents, adm_w)
        o["cent_cos"] = order_from_scores(cos_c, intents, adm_c)
        o["cent_agree"] = order_from_scores(cos_c + share, intents, adm_c)
        o["vote"] = order_from_scores(share, intents, share > 0)
        has_cos = {k: [set(intents[j] for j in np.flatnonzero(a[i])) for i in range(len(q))] for k, a in (("w", adm_w), ("c", adm_c))}
        nn1 = group_max(sims, labels, 60)
        o["nn1"] = order_from_scores(nn1, intents, nn1 > 0.0)
        o["nn1_agree"] = order_from_scores(nn1 + share, intents, nn1 > 0.0)
        for p in PROTOS:
            pm, owner = protos[p]
            pc = group_max(q @ pm.T, owner, 60)
            o[f"K1_p{p}"] = order_from_scores(pc, intents, pc > 0.0)
            o[f"K1_p{p}_agree"] = order_from_scores(pc + share, intents, pc > 0.0)
        for m in KNN_M:
            for wt in (False, True):
                tag = f"m{m}{'w' if wt else ''}"
                kn = knn_shares(sims, labels, 60, m, wt)
                o[f"K2_{tag}_cent"] = order_from_scores(cos_c + kn, intents, adm_c)
                for w in SHARE_W:
                    o[f"K2_{tag}_cent_agree_w{w}"] = order_from_scores(cos_c + share + w * kn, intents, adm_c)
        scos = q @ scen_cent.T
        scen_score = scos[:, [scen_idx[scenario_of(x)] for x in intents]]
        for lam in LAMBDAS:
            o[f"K4_soft_l{lam}"] = order_from_scores(cos_c + share + lam * scen_score, intents, adm_c)
        scen_rank = [[scen_names[k] for k in np.lexsort((np.arange(len(scen_names)), -scos[i]))] for i in range(len(q))]
        for s_ in HARD_S:
            o[f"K4_hard_s{s_}"] = [scenario_first(o["cent_agree"][i], scen_rank[i], s_) for i in range(len(q))]
        tc = cos_c.max(axis=1)
        top_cos[fold] = {sid: float(tc[i]) for i, sid in enumerate(ids[fold])}
        for cname, catch in CATCH_SETS.items():
            for qv in THETA_Q:
                theta = float(np.quantile(tc, qv))
                o[f"K3_{cname}_q{qv}"] = [catch_all_floor(o["cent_agree"][i], float(tc[i]), theta, catch) for i in range(len(q))]
        o["K5_rrf_cent_agree+K1_p3_agree"] = rrf([o["cent_agree"], o["K1_p3_agree"]], intents)
        o["K5_rrf_cent_agree+K2_m20_cent"] = rrf([o["cent_agree"], o["K2_m20_cent"]], intents)
        o["K5_rrf_cent_agree+nn1"] = rrf([o["cent_agree"], o["nn1"]], intents)
        o["K5_rrf_cent_agree+nn1+K1_p3"] = rrf([o["cent_agree"], o["nn1"], o["K1_p3"]], intents)
        # K6: centred cosine (pool mean off the keys, construction-speech mean off the query)
        cc = centre_queries(q, mu_q) @ cent_centred.T
        o["K6_centred"] = order_from_scores(cc, intents, adm_c)
        for w in AGREE_W:
            o[f"K6_centred_agree_w{w}"] = order_from_scores(cc + w * share, intents, adm_c)
        # K6p: the same key under PRODUCTION admission -- the recall admits a facet only at a
        # positive cosine, and the centred cosine is negative for many facets
        adm_cc = cc > 0.0
        for w in AGREE_W:
            o[f"K6p_centred_agree_w{w}"] = order_from_scores(cc + w * share, intents, adm_cc)
        k6p_admitted[fold] = {"mean_admitted": round(float(adm_cc.sum(axis=1).mean()), 3),
                              "rows_under_8_admitted": int((adm_cc.sum(axis=1) < D).sum()),
                              "rows_gold_not_admitted": None}
        base_k6 = o["K6_centred_agree_w1.0"]
        for qv in THETA_Q:
            theta = float(np.quantile(tc, qv))
            o[f"K6+K3_gqqaf_q{qv}"] = [catch_all_floor(base_k6[i], float(tc[i]), theta, CATCH_SETS["gq+qaf"]) for i in range(len(q))]
        # K7: CSLS hub penalty on the centroid key
        for k_ in CSLS_K:
            cs = 2.0 * cos_c - csls[k_][None, :]
            for w in AGREE_W:
                o[f"K7_csls{k_}_agree_w{w}"] = order_from_scores(cs + 2.0 * w * share, intents, adm_c)
        # K8: per-key bias removal (mean) and z-score rescaled to the mean spread
        o["K8_bias_agree"] = order_from_scores(cos_c - kb_mu[None, :] + share, intents, adm_c)
        z = (cos_c - kb_mu[None, :]) / np.where(kb_sd > 0, kb_sd, 1.0)[None, :] * float(kb_sd.mean())
        for w in AGREE_W:
            o[f"K8_z_agree_w{w}"] = order_from_scores(z + w * share, intents, adm_c)
        # K8 + the catch-all floor (theta from this fold's own top centroid cosine quantiles, cross-fitted below)
        base_z = order_from_scores(z + share, intents, adm_c)
        for qv in THETA_Q:
            theta = float(np.quantile(tc, qv))
            o[f"K8z+K3_gq_q{qv}"] = [catch_all_floor(base_z[i], float(tc[i]), theta, CATCH_SETS["gq"]) for i in range(len(q))]
        orders[fold] = {k: {sid: v[i] for i, sid in enumerate(ids[fold])} for k, v in o.items()}
        orders[fold]["_has_cos_w"] = {sid: has_cos["w"][i] for i, sid in enumerate(ids[fold])}
        orders[fold]["_has_cos_c"] = {sid: has_cos["c"][i] for i, sid in enumerate(ids[fold])}
        diag_rows_all[fold] = {"cos_c": cos_c, "sims_nn1": nn1}

    # ---- custody: recomputed baseline blocks equal the sealed blocks
    for sid in ids["A"]:
        checks["A_desc_agree_block_equals_sealed_AGREE"] += int(block_of(orders["A"]["desc_agree"][sid], orders["A"]["_has_cos_w"][sid]) == agree_ph[sid]["block"])
        checks["A_cent_agree_block_equals_sealed_COMP1B"] += int(block_of(orders["A"]["cent_agree"][sid], orders["A"]["_has_cos_c"][sid]) == comp_ph[sid]["block"])
    for sid in ids["B"]:
        checks["B_desc_agree_block_equals_sealed_PSV1_a"] += int(block_of(orders["B"]["desc_agree"][sid], orders["B"]["_has_cos_w"][sid]) == psv1[sid]["block"])
        checks["B_desc_agree_block_equals_sealed_PSV3_a"] += int(block_of(orders["B"]["desc_agree"][sid], orders["B"]["_has_cos_w"][sid]) == psv3[sid]["block"])
    for k in ("A_desc_agree_block_equals_sealed_AGREE", "A_cent_agree_block_equals_sealed_COMP1B", "B_desc_agree_block_equals_sealed_PSV1_a"):
        if checks[k] < ROWS - 4:
            raise ReadError(f"recomputed block does not reproduce the sealed block: {k}={checks[k]}")

    ranks = {f: {k: {s: rank_of(v[s], gold[s]) for s in ids[f]} for k, v in orders[f].items() if not k.startswith("_")} for f in ("A", "B")}
    half = {f: {s: split_half(utt[s]) for s in ids[f]} for f in ("A", "B")}

    # ---- sealed conversion tables (block rank -> note / delivered intent)
    def sealed_tables(ph, ok, fold_ids):
        br = {s: rank_of(ph[s]["block"], gold[s]) for s in fold_ids}
        on_note = {s: gold[s] in ph[s]["note"] for s in fold_ids}
        return rate_table(br, on_note, fold_ids), rate_table(br, ok, fold_ids), on_note

    tabs = {}
    tabs["A_cent_agree"] = sealed_tables(comp_ph, comp_ok, ids["A"])
    tabs["A_desc_agree"] = sealed_tables(agree_ph, agree_ok, ids["A"])
    tabs["B_desc_agree"] = sealed_tables(psv1, psv1_ok, ids["B"])
    correct = {"A_cent_agree": comp_ok, "A_desc_agree": agree_ok, "B_cent_agree": psv1_ok, "B_desc_agree": psv1_ok}
    table_for = {"A_cent_agree": "A_cent_agree", "A_desc_agree": "A_desc_agree", "B_cent_agree": "B_desc_agree", "B_desc_agree": "B_desc_agree"}

    # ---- the brief's target sets (defined under the flown desc_agree key)
    agree_on_note = tabs["A_desc_agree"][2]
    targets = {
        "A": {s for s in ids["A"] if not agree_ok[s] and not agree_on_note[s] and not in_block(ranks["A"]["desc_agree"][s])},
        "B": {s for s in ids["B"] if gold[s] not in psv3[s]["note"] and not in_block(ranks["B"]["desc_agree"][s])},
    }
    target_repro = {"A_agree_intent_wrong_off_note_off_block": len(targets["A"]),
                    "B_psv3_a_note_absent": sum(1 for s in ids["B"] if gold[s] not in psv3[s]["note"]),
                    "B_psv3_a_note_absent_off_block": len(targets["B"])}

    # ---- taxonomy of the target rows
    taxonomy = {}
    for fold in ("A", "B"):
        far_cut = float(np.quantile(list(top_cos[fold].values()), FAR_QUANTILE))
        cos_c = diag_rows_all[fold]["cos_c"]
        pos = {s: i for i, s in enumerate(ids[fold])}
        rows = []
        for s in sorted(targets[fold]):
            g = gold[s]
            rival = orders[fold]["desc_agree"][s][0]
            i = pos[s]
            gcos, tcos = float(cos_c[i, idx[g]]), float(cos_c[i].max())
            nb = centroid[idx[g]] @ centroid.T
            nb_order = [intents[j] for j in np.lexsort((np.arange(60), -nb)) if j != idx[g]]
            row = {
                "sample_id": s, "half": half[fold][s],
                "catch_all": is_catch_all(g), "general_quirky": g == "general_quirky",
                "gold_cent_cos": round(gcos, 4), "top1_cent_cos": round(tcos, 4), "gap_top1_minus_gold": round(tcos - gcos, 4),
                "rival_same_scenario": scenario_of(rival) == scenario_of(g),
                "rival_centroid_cos_to_gold": round(float(nb[idx[rival]]), 4),
                "rival_rank_among_gold_centroid_neighbours": (nb_order.index(rival) + 1) if rival in nb_order else None,
                "gold_members_in_pool": int(per_intent.get(idx[g], 0)),
            }
            for k in ("desc_cos", "desc_agree", "cent_cos", "cent_agree", "vote", "nn1", "K1_p3", "K2_m20_cent"):
                row["rank_" + k] = ranks[fold][k][s]
            row["class"] = classify_miss(row, far_cut)
            rows.append(row)
        cls = Counter(r["class"] for r in rows)
        flags = {
            "catch_all": sum(r["catch_all"] for r in rows),
            "general_quirky": sum(r["general_quirky"] for r in rows),
            "catch_all_far": sum(1 for r in rows if r["catch_all"] and r["top1_cent_cos"] < far_cut),
            "far_any_gold": sum(1 for r in rows if r["top1_cent_cos"] < far_cut),
            "rival_same_scenario": sum(r["rival_same_scenario"] for r in rows),
            "rival_is_gold_nearest_centroid": sum(1 for r in rows if r["rival_rank_among_gold_centroid_neighbours"] == 1),
            "rival_in_gold_top3_centroid_neighbours": sum(1 for r in rows if (r["rival_rank_among_gold_centroid_neighbours"] or 99) <= 3),
            "nn1_in_top8": sum(1 for r in rows if in_block(r["rank_nn1"])),
            "cent_cos_in_top8": sum(1 for r in rows if in_block(r["rank_cent_cos"])),
            "cent_agree_in_top8": sum(1 for r in rows if in_block(r["rank_cent_agree"])),
            "nn1_top8_and_cent_cos_off": sum(1 for r in rows if in_block(r["rank_nn1"]) and not in_block(r["rank_cent_cos"])),
        }
        by_class = {}
        for c in "abcd":
            sel = [r for r in rows if r["class"] == c]
            by_class[c] = {
                "rows": len(sel),
                "general_quirky": sum(r["general_quirky"] for r in sel),
                "median_gap_top1_minus_gold": round(float(np.median([r["gap_top1_minus_gold"] for r in sel])), 4) if sel else None,
                "median_rank_cent_agree": float(np.median([r["rank_cent_agree"] or 61 for r in sel])) if sel else None,
                "median_rank_nn1": float(np.median([r["rank_nn1"] or 61 for r in sel])) if sel else None,
                "nn1_in_top8": sum(1 for r in sel if in_block(r["rank_nn1"])),
            }
        taxonomy[fold] = {"far_cut_top1_cent_cos_q25": round(far_cut, 4), "rows": len(rows), "classes": dict(sorted(cls.items())),
                          "by_class": by_class, "flags": flags,
                          "median_gold_cent_cos": round(float(np.median([r["gold_cent_cos"] for r in rows])), 4),
                          "median_top1_cent_cos": round(float(np.median([r["top1_cent_cos"] for r in rows])), 4),
                          "fold_median_top1_cent_cos": round(float(np.median(list(top_cos[fold].values()))), 4),
                          "gold_intent_counts_top": top_counts(Counter(gold[s] for s in targets[fold]), 10),
                          "rival_intent_counts_top": top_counts(Counter(orders[fold]["desc_agree"][s][0] for s in targets[fold]), 8),
                          "rival_distinct": len({orders[fold]["desc_agree"][s][0] for s in targets[fold]}),
                          "per_row": rows}

    # ---- key comparison
    def criterion_for(fold, base):
        pnote = tabs[table_for[f"{fold}_{base}"]][0]
        return lambda rk, own: implied(rk, pnote, own)

    fixed_keys = [k for k in ranks["A"] if not k.startswith(("K3_", "K4_", "K8z+K3_", "K6+K3_")) and "_w0.5" not in k and "_w2.0" not in k]
    families = {
        "K1*": [f"K1_p{p}_agree" for p in PROTOS],
        "K2*_cent": [f"K2_m{m}{w}_cent" for m in KNN_M for w in ("", "w")],
        "K2*_cent_agree": [f"K2_m{m}{w}_cent_agree_w{sw}" for m in KNN_M for w in ("", "w") for sw in SHARE_W],
        "K3*_gq": [f"K3_gq_q{qv}" for qv in THETA_Q],
        "K3*_gq+qaf": [f"K3_gq+qaf_q{qv}" for qv in THETA_Q],
        "K4*_soft": [f"K4_soft_l{lam}" for lam in LAMBDAS],
        "K4*_hard": [f"K4_hard_s{s_}" for s_ in HARD_S],
        "K6*": [f"K6_centred_agree_w{w}" for w in AGREE_W],
        "K6p*": [f"K6p_centred_agree_w{w}" for w in AGREE_W],
        "K7*": [f"K7_csls{k_}_agree_w{w}" for k_ in CSLS_K for w in AGREE_W],
        "K8z*": [f"K8_z_agree_w{w}" for w in AGREE_W],
        "K8z+K3*": [f"K8z+K3_gq_q{qv}" for qv in THETA_Q],
        "K6+K3*": [f"K6+K3_gqqaf_q{qv}" for qv in THETA_Q],
    }
    comparison = {}
    crossfit = {}
    for fold in ("A", "B"):
        comparison[fold] = {}
        crossfit[fold] = {}
        for base in ("cent_agree", "desc_agree"):
            tb = tabs[table_for[f"{fold}_{base}"]]
            ok = correct[f"{fold}_{base}"]
            res = {}
            keyset = dict((k, ranks[fold][k]) for k in fixed_keys)
            cf = {}
            for fam, members_ in families.items():
                ch = crossfit_choose({m: ranks[fold][m] for m in members_}, half[fold], criterion_for(fold, base))
                keyset[fam] = ch["ranks"]
                cf[fam] = ch["chosen_on_half"]
            for k, rk in keyset.items():
                entry = compare(ranks[fold][base], rk, ids[fold], ok, targets[fold], tb[0], tb[1])
                entry["by_half"] = {str(h): compare(ranks[fold][base], rk, [s for s in ids[fold] if half[fold][s] == h], ok,
                                                    targets[fold], tb[0], tb[1]) for h in (0, 1)}
                res[k] = entry
            comparison[fold][base] = res
            crossfit[fold][base] = cf

    tables_out = {k: {r: round(v, 4) for r, v in tabs[k][0].items()} for k in tabs}
    tables_corr = {k: {r: round(v, 4) for r, v in tabs[k][1].items()} for k in tabs}
    return {
        "read_id": READ_ID, "recipe": RECIPE,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "gpu": 0, "network": 0,
                     "paid_api": 0, "official_scorer_subprocess": 0},
        "inputs": dict(sorted(files.items())),
        "checks": dict(sorted(checks.items())),
        "query_segments_per_row": {f: {str(k): v for k, v in segs[f].items()} for f in segs},
        "construction_pool": pool_info,
        "prototypes": {str(p): int(len(protos[p][0])) for p in PROTOS},
        "scenarios": len(scen_names),
        "hub_statistics": stats_info,
        "k6p_admission": {f: dict(v, rows_gold_not_admitted=sum(1 for s in ids[f] if ranks[f]["K6p_centred_agree_w1.0"][s] is None))
                          for f, v in k6p_admitted.items()},
        "target_reproduction": target_repro,
        "p_note_given_sealed_block_rank": tables_out,
        "p_intent_correct_given_sealed_block_rank": tables_corr,
        "taxonomy": taxonomy,
        "crossfit_choices": crossfit,
        "comparison": comparison,
    }


# ---------------------------------------------------------------------------
# outputs

TABLE_KEYS = ("K6_centred", "K6_centred_agree_w1.0", "K6*", "K6p_centred_agree_w1.0", "K6p*", "K6+K3*", "K7*", "K8_bias_agree", "K8_z_agree_w1.0", "K8z*", "K8z+K3*", "desc_agree", "cent_agree", "cent_cos", "vote", "nn1", "nn1_agree", "K1_p2_agree", "K1_p3_agree",
              "K1_p4_agree", "K1*", "K2_m10_cent", "K2_m20_cent", "K2_m40_cent", "K2_m20w_cent", "K2*_cent",
              "K2_m20_cent_agree_w1.0", "K2_m40_cent_agree_w1.0", "K2*_cent_agree", "K3*_gq", "K3*_gq+qaf",
              "K4*_soft", "K4*_hard", "K5_rrf_cent_agree+K1_p3_agree", "K5_rrf_cent_agree+K2_m20_cent",
              "K5_rrf_cent_agree+nn1", "K5_rrf_cent_agree+nn1+K1_p3")


def render(r: dict) -> str:
    out = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", ""]
    out.append("## Checks")
    out += [f"- {k}: {v}" for k, v in r["checks"].items()]
    out.append("")
    out.append("## Taxonomy")
    for fold, t in r["taxonomy"].items():
        out.append(f"- {fold}: rows {t['rows']}, classes {t['classes']}, flags {t['flags']}")
    for fold in ("A", "B"):
        for base in ("cent_agree", "desc_agree"):
            out += ["", f"## Fold {fold} vs {base}", "",
                    "| key | in block | net | enters | leaves | leaves correct | targets rec. | rank-1 | mean rank (base in-block) | implied note delta | implied intent delta | half 0 net / note | half 1 net / note |",
                    "| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | --- | --- |"]
            for k in TABLE_KEYS:
                e = r["comparison"][fold][base].get(k)
                if e is None:
                    continue
                h0, h1 = e["by_half"]["0"], e["by_half"]["1"]
                out.append(f"| {k} | {e['gold_in_block']} | {e['net']:+d} | {e['enters']} | {e['leaves']} | {e['leaves_delivered_correct']} | "
                           f"{e['targets_recovered']}/{e['targets']} | {e['rank1']} ({e['rank1_base']}) | "
                           f"{e['base_in_block_mean_rank_base']} -> {e['base_in_block_mean_rank_alt']} | {e['implied_note_delta']:+.2f} | "
                           f"{e['implied_intent_delta']:+.2f} | {h0['net']:+d} / {h0['implied_note_delta']:+.2f} | {h1['net']:+d} / {h1['implied_note_delta']:+.2f} |")
    return "\n".join(out) + "\n"


def strip_generated(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    rj = json.dumps(report, indent=2, sort_keys=True) + "\n"
    md = render(report)
    if args.check:
        bad = [name for name, text in (("report.json", rj), ("tables.md", md))
               if strip_generated((out_dir / name).read_text(encoding="utf-8")) != strip_generated(text)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.json").write_text(rj, encoding="utf-8", newline="\n")
    (out_dir / "tables.md").write_text(md, encoding="utf-8", newline="\n")
    manifest = {name: hashlib.sha256(strip_generated(text).encode("utf-8")).hexdigest()
                for name, text in (("report.json", rj), ("tables.md", md))}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out_dir), "content_sha256": manifest, "checks": report["checks"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
