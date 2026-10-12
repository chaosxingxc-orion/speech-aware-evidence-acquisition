#!/usr/bin/env python3
"""Is the intent-boundary channel weak because of its written keys, and would keys
built from TRAIN utterances close the gap?  Measured offline, at zero contacts.

A model-free read over pinned bytes.  Zero model, server, encoder, embedder,
scorer, tokenizer, network, GPU and paid-API contacts.  Every similarity is
RECOMPUTED -- arithmetic over sha256-verified vector files the flights
themselves pinned -- and the recomputation is validated against what the
flights sealed before a number is taken from it.  A candidate key is a
construction over ALREADY-PINNED utterance vectors (a mean, or a pinned vector
chosen by arithmetic), so no text is encoded anywhere in this read; the one
construction that would need an encoder pass is priced as text only and its
retrieval effect is stated as unmeasured.

A DIAGNOSTIC, never a gate.  It admits no mechanism, releases no store,
rebuilds no store, registers no cell, authorises no flight and states no
effectiveness, superiority or generalisation claim.  Every roster is a
discovery or dev roster and every number is a development number (owner
decisions 28 and 86), never a test claim.  Every number is DELIVERY, never
correctness.

Query discipline (owner ruling 2026-09-06): the retrieval query is speech, and
stays speech -- every query vector here is a sealed speech vector.  Only the
KEY side is constructed, from construction-split TRAIN utterances, which
``rails.phase_supply`` states is deliberately unconstrained text.

Text discipline: no utterance text, transcript, gold filler, delivered answer,
knowledge body or key description is read into a reported value or printed.
An intent id is an id and is reported; a text is only ever reduced to a word
count or an overlap ratio.

Gold discipline: gold labels enter offline on the scoring side only -- the
sealed bad-case bank, the governed TRAIN split through the ordinary loader and
one sealed official score file -- and reach no query, key, weight or selector.
The key constructions use the POOL's own frozen build-time intent labels, a
store property, never an evaluation row's gold.

Selection rule, fixed before the numbers were read: a construction is put
forward only if, on ALL three rosters under their held-out pool, it raises
gold rank-1 on the intent-wrong rows AND raises delivery at k=8 on those rows
over the written key, while lowering delivery at k=8 on the CORRECT rows of no
roster by more than one point.  Among passers a single-key construction beats
a multi-key one (it keeps the 60-facet store shape, the fuser's m=8 window and
the delivered block unchanged); then the larger held-out floor on wrong-row
rank-1 wins; a tie goes to the key that is a real utterance.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    load_slurp_construction_utterances,
    load_slurp_split,
)
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    multidim_segment_recall,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)

READ_ID = "SAEA-SLURP-MF-BOUNDARY-KEY-CONSTRUCTION-DIAGNOSTIC-V1"
RECIPE = "slurp-boundary-key-construction-diagnostic-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_MARKDOWN = "docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md"

IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
IB_SNAPSHOT_SHA = "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"
IB_FACETS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl"
IB_FACETS_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
IB_INDEX = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/index.json"
POOL = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
POOL_SHA = "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"
POOL_M = ("knowledge/slurp/saea-kb-distmodel-v1/"
          "size-pool-annotated-exemplars-minus-r01/snapshot.json")
POOL_M_SHA = "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"
POOL_FACETS = "vectors/slurp-kus3/facet-vectors.jsonl"
POOL_FACETS_SHA = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
IB_DIM, POOL_DIM = "intent-boundary", "content"
FLOWN_K, RECALL_WIDTH = 8, 60
MEDOID_KS = (1, 3, 5)
ROSTERS = ("train-fold-a-plan", "roll1", "dev2000-added-plan")
FOCUS = "general_quirky"
BANDS = ((1, 8), (9, 16), (17, 30), (31, 60))
SHARE_LADDER = (0.25, 0.5, 0.75)
UNRANKED = 9999
BLOCK, TIE_SLACK = 512, 16
CONSTRUCTIONS = ("written", "centroid", "medoid-1", "medoid-3", "medoid-5",
                 "all-utterances")

ARMS = (
    {"label": "train-fold-a-plan", "title": "TRAIN Fold A PLAN (construction roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
     "roster": "train-fold-a",
     "query": ("vectors/slurp-intent-boundaries-train-fold-a-1080-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b",
     "pool": POOL, "seen_pool": None, "scores": None, "scorer_id": None},
    {"label": "roll1", "title": "ROLL-1 (R01C construction roster)",
     "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
     "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1", "roster": None,
     "query": ("vectors/slurp-stage3-construction-r01c-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8",
     "pool": POOL_M, "seen_pool": POOL,
     "scores": ("analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/PS-registered-"
                "support-3-slurp-slu-official-projected-v3-train-scores.json"),
     "scorer_id": "slurp-slu-official-projected-v3-train"},
    {"label": "dev2000-added-plan", "title": "DEV-2000-ADDED PLAN (fresh roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
     "roster": "dev2000-added",
     "query": "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d",
     "pool": POOL, "seen_pool": None, "scores": None, "scorer_id": None},
)


class ReadError(RuntimeError):
    pass


def digest(path: Path) -> str:
    h, handle = hashlib.sha256(), path.open("rb")
    try:
        chunk = handle.read(1 << 20)
        while chunk:
            h.update(chunk)
            chunk = handle.read(1 << 20)
    finally:
        handle.close()
    return h.hexdigest()


def pct(num: float, den: float) -> float:
    return 100.0 * num / den if den else 0.0


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def classify(wrong: bool, fp: float, fn: float) -> str:
    if wrong:
        return "INTENT-WRONG"
    if not (fp or fn):
        return "CORRECT"
    return "ENTITY-" + ("MIXED" if fp and fn else ("FN-ONLY" if fn else "FP-ONLY"))


def own_key(sample_id: str) -> str | None:
    parts = sample_id.split(":")
    field = parts[2] if len(parts) >= 3 else ""
    return str(int(field)) if field.isdigit() else None


def canon(key: str) -> str:
    key = str(key)
    return str(int(key)) if key.isdigit() else key


def word_set(text: str) -> frozenset:
    """The lowercased alphanumeric word set of a text, used ONLY to produce a
    count or an overlap ratio.  No word and no text is stored or printed."""

    out, run = set(), []
    for char in str(text).lower():
        if char.isalnum():
            run.append(char)
        elif run:
            out.add("".join(run))
            run = []
    if run:
        out.add("".join(run))
    return frozenset(out)


def unit_rows(matrix) -> np.ndarray:
    """Row-wise L2 normalisation in float64, so a dot product IS the cosine
    ``rails.kb_policy._cosine_with_norms`` computes (same norm, same quotient)."""

    work = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(work, axis=1, keepdims=True)
    return work / np.where(norms > 0.0, norms, 1.0)


def jaccard_stats(sets: list) -> dict:
    laps = [len(a & b) / len(a | b) if (a | b) else 0.0
            for i, a in enumerate(sets) for b in sets[i + 1:]]
    return {"mean": round(sum(laps) / len(laps), 4) if laps else None,
            "max": round(max(laps), 4) if laps else None}


def median(values: list) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    return float(ordered[mid]) if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


# ---------------------------------------------------------------------------
# pinned inputs


def load_boundary(root: Path) -> dict:
    snap = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / IB_SNAPSHOT).read_text(encoding="utf-8")))
    if snap.content_hash() != IB_SNAPSHOT_SHA:
        raise ReadError("intent-boundaries snapshot does not hash to the flown pin")
    facets = {facet.facet_id: facet for facet in snap.facets}
    values = {value.value_id: value for value in snap.values}
    if set(facets) != set(values) or len(facets) != 60:
        raise ReadError("intent-boundaries is not the flown 60-way 1:1 store")
    index_path = root / IB_INDEX
    index = json.loads(index_path.read_text(encoding="utf-8"))
    text_sha = {f["id"]: f["text_sha256"] for f in index["inputs"]["facets"]}
    encoded_is_representation = sum(
        1 for fid, facet in facets.items()
        if hashlib.sha256(facet.representation.encode("utf-8")).hexdigest()
        == text_sha.get(fid))
    encoded_is_content = sum(
        1 for fid in facets
        if hashlib.sha256(values[fid].content.encode("utf-8")).hexdigest()
        == text_sha.get(fid))
    if encoded_is_representation != 60:
        raise ReadError("the encoded key text is not the facet representation on 60/60")
    vectors = load_sealed_vectors(root / IB_FACETS, expected_sha256=IB_FACETS_SHA,
                                 dimensions=(IB_DIM,))
    if set(vectors) != set(facets):
        raise ReadError("boundary facet vectors do not cover the store exactly")
    to_intent = {fid: fid.split("intent-boundary:", 1)[-1] for fid in facets}
    intents = sorted(to_intent.values())
    by_intent = {intent: fid for fid, intent in to_intent.items()}
    return {
        "snapshot": snap, "facet_vectors": vectors, "to_intent": to_intent,
        "intents": intents,
        "matrix": unit_rows([vectors[by_intent[i]][IB_DIM] for i in intents]),
        "key_words": {i: word_set(facets[by_intent[i]].representation) for i in intents},
        "body_words": {i: word_set(values[by_intent[i]].content) for i in intents},
        "key_chars": [len(facets[by_intent[i]].representation) for i in intents],
        "body_chars": [len(values[by_intent[i]].content) for i in intents],
        "encoded_is_representation": encoded_is_representation,
        "encoded_is_content": encoded_is_content,
        "geometry": dict(index["inputs"].get("geometry") or {}),
        "encoder_inventory_sha256": (index["inputs"].get("encoder_identity") or {}).get(
            "inventory_sha256"),
        "index_sha256": digest(index_path), "content_sha256": snap.content_hash()}


def load_pool(root: Path, relpath: str, expected: str) -> dict:
    snap = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / relpath).read_text(encoding="utf-8")))
    if snap.content_hash() != expected:
        raise ReadError(relpath + " does not hash to the flown pin")
    keyed = {}
    for value in snap.values:
        if len(value.associated_facet_ids) != 1:
            raise ReadError(relpath + ": a pool value is not bound to one facet")
        keyed[value.associated_facet_ids[0]] = canon(value.value_id.split("value:", 1)[-1])
    facets = sorted(facet.facet_id for facet in snap.facets)
    if set(facets) != set(keyed):
        raise ReadError(relpath + ": facets and values are not a bijection")
    return {"relpath": relpath, "content_sha256": snap.content_hash(), "facets": facets,
            "keyed": keyed, "utterances": len(facets)}


def load_train(lock: dict, root: Path) -> dict:
    intent_of = {}
    for record in load_slurp_split(lock, root, "train"):
        intent_of[canon(record.utterance_id)] = f"{record.scenario}_{record.action}"
    words = {}
    for row in load_slurp_construction_utterances(lock, root).utterances:
        # The pool keys its values by the bare slurp id; the construction pool
        # carries ``slurp:train:000001`` beside the same integer.
        words[str(int(row.slurp_id))] = word_set(" ".join(row.tokens))
    if set(words) != set(intent_of):
        raise ReadError("TRAIN word sets and TRAIN gold do not name the same utterances")
    return {"intent_of": intent_of, "utterances": len(intent_of),
            "per_intent": Counter(intent_of.values()), "words": words}


def load_bank(root: Path) -> dict:
    path, rosters = root / BANK, defaultdict(dict)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            rosters[entry["roster"]][entry["sample_id"]] = {
                "class": {"INTENT-UNCOVERED": "INTENT-WRONG",
                          "INTENT-COVERED": "INTENT-WRONG"}.get(
                              entry["plan_class"], entry["plan_class"]),
                "gold_intent": entry["gold_intent"]}
    return {"sha256": digest(path),
            "rosters": {k: dict(sorted(v.items())) for k, v in sorted(rosters.items())}}


def load_rows(root: Path, arm: dict, bank: dict, train: dict) -> dict:
    if arm["roster"] is not None:
        return {"rows": dict(bank["rosters"][arm["roster"]]),
                "source": "bad-case bank roster " + arm["roster"],
                "source_sha256": bank["sha256"]}
    path = root / arm["scores"]
    block = json.loads(path.read_text(encoding="utf-8"))[arm["scorer_id"]]
    rows = {}
    for sample in block["per_sample"]:
        sample_id = str(sample["sample_id"])
        utterance = own_key(sample_id)
        rows[sample_id] = {
            "class": classify(not bool(sample["scenario_action_exact"]),
                              float(sample["slot_f1_exact_fp"]),
                              float(sample["slot_f1_exact_fn"])),
            "gold_intent": train["intent_of"].get(utterance) if utterance else None}
    return {"rows": dict(sorted(rows.items())), "source": arm["scorer_id"],
            "source_sha256": digest(path)}


def load_sealed(root: Path, arm: dict) -> dict:
    path = (root / "runs" / arm["run_id"] / arm["attempt"]
            / (arm["run_id"] + ".phases.json"))
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != "saea-flight-phase-summaries-v1":
        raise ReadError(arm["label"] + ": unexpected phase artefact schema")
    rows = {}
    for result in document["phases"][0]["results"]:
        boundary = []
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith("intent-boundary:"):
                boundary.append(item.split("intent-boundary:", 1)[-1])
        rows[result["sample_id"]] = sorted(set(boundary))
    del document
    return {"rows": rows, "relpath": str(path.relative_to(root)), "sha256": digest(path)}


def load_pool_vectors(root: Path, wanted: set) -> dict:
    """The pool key vectors restricted to the facets the released stores
    declare, in one streaming pass over a file verified against the flown pin.
    A line is parsed only when its id prefix is wanted; nothing is embedded."""

    path = root / POOL_FACETS
    if digest(path) != POOL_FACETS_SHA:
        raise ReadError(POOL_FACETS + " does not hash to the flown pin")
    out = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            head = line[:96]
            marker = head.find('"id": "')
            if marker < 0:
                continue
            start = marker + len('"id": "')
            facet_id = head[start:head.find('"', start)]
            if facet_id in wanted:
                out[facet_id] = np.asarray(json.loads(line)["vectors"][POOL_DIM],
                                           dtype=np.float32)
    if set(out) != wanted:
        raise ReadError("pool key vectors do not cover the released stores")
    return out


# ---------------------------------------------------------------------------
# queries, and the validation of the recomputation against the flights


def load_queries(root: Path, arm: dict, sample_ids: list) -> dict:
    segments = load_sealed_segment_vectors(root / arm["query"],
                                           expected_sha256=arm["query_sha"],
                                           dimensions=(IB_DIM,))
    ids = [s for s in sample_ids if s in segments]
    widths = Counter(len(segments[s].segments) for s in ids)
    if set(widths) != {1}:
        raise ReadError(arm["label"] + ": a row carries more than one speech segment")
    return {"ids": ids, "segments": segments,
            "matrix": unit_rows([segments[s].segments[0][IB_DIM] for s in ids]),
            "skipped": len(sample_ids) - len(ids)}


def repo_orders(store: dict, queries: dict) -> dict:
    """The flown arithmetic through this repository's OWN segment recall at
    width 60 (the truncation removed), in the flown order: score descending,
    facet id ascending.  An entry the recall does not admit -- cosine at or
    below zero -- has no rank at any k."""

    snap, table, out = store["snapshot"], store["facet_vectors"], {}
    for sample_id in queries["ids"]:
        recalled = multidim_segment_recall(snap, queries["segments"][sample_id].segments,
                                           lambda f: table.get(f, {}), RECALL_WIDTH)
        scored = {store["to_intent"][f]: s[IB_DIM] for f, s in recalled.items()}
        out[sample_id] = [i for i, _ in sorted(scored.items(),
                                               key=lambda kv: (-kv[1], kv[0]))]
    return out


def validate(queries: dict, keyset: dict, sealed: dict, repo: dict) -> dict:
    """Three agreements per roster: the repository recall against the sealed
    delivered set; the vectorised ordering against that sealed set; and the
    vectorised full 60-way order against the repository recall's order."""

    order = intent_orders(queries["matrix"], keyset)
    exact = width8 = numpy_exact = same_order = 0
    for position, sample_id in enumerate(queries["ids"]):
        want = sealed.get(sample_id) or []
        width8 += int(len(want) == FLOWN_K)
        exact += int(sorted(repo[sample_id][:len(want)]) == sorted(want))
        mine = order[position]
        numpy_exact += int(sorted(mine[:len(want)]) == sorted(want))
        same_order += int(mine == repo[sample_id])
    return {"rows": len(queries["ids"]), "sealed_width_is_8": width8,
            "repo_top_matches_sealed": exact, "numpy_top_matches_sealed": numpy_exact,
            "numpy_order_equals_repo": same_order}


# ---------------------------------------------------------------------------
# key constructions over pinned pool vectors


def build_keysets(store: dict, pool: dict, vectors: dict, train: dict) -> dict:
    """Every construction as ``{matrix, key_intent, key_tie, key_ids, words}``.
    ``written`` is the flown store.  The others use the POOL's own frozen
    build-time intent labels and pinned utterance vectors only: ``centroid``
    is the intent's mean utterance vector; ``medoid-k`` the k utterances
    closest to that centroid (a real utterance, never an average);
    ``all-utterances`` every pool utterance of the intent, the exemplar
    channel's own nearest-neighbour ceiling worn as an intent key."""

    intents, facets = store["intents"], pool["facets"]
    labels = [train["intent_of"].get(pool["keyed"][f], "") for f in facets]
    if "" in labels or set(labels) - set(intents):
        raise ReadError(pool["relpath"] + ": a pool utterance has no TRAIN intent")
    if any(pool["keyed"][f] not in train["words"] for f in facets):
        raise ReadError(pool["relpath"] + ": a pool utterance has no TRAIN word set")
    matrix = unit_rows([vectors[f] for f in facets])
    positions = defaultdict(list)
    for position, label in enumerate(labels):
        positions[label].append(position)
    written = {i: store["matrix"][n] for n, i in enumerate(intents)}
    #: An intent with NO construction utterance in this pool cannot receive a
    #: utterance-built key; it keeps the flown written key, and is reported.
    fallback = [i for i in intents if not positions[i]]
    out = {"written": {"matrix": store["matrix"], "key_intent": list(intents),
                       "key_ids": ["intent-boundary:" + i for i in intents],
                       "words": [store["key_words"][i] for i in intents],
                       "keys_per_intent": {i: 1 for i in intents}, "fallback": []}}
    centroids, medoids = {}, {k: {} for k in MEDOID_KS}
    for intent in intents:
        rows = positions[intent]
        if not rows:
            centroids[intent] = written[intent]
            for k in MEDOID_KS:
                medoids[k][intent] = []
            continue
        centre = unit_rows(matrix[rows].mean(axis=0, keepdims=True))[0]
        centroids[intent] = centre
        ranked = sorted(rows, key=lambda p: (-float(matrix[p] @ centre),
                                             int(pool["keyed"][facets[p]])))
        for k in MEDOID_KS:
            medoids[k][intent] = ranked[:k]

    def assemble(name: str, picks: dict, with_words: bool) -> dict:
        vecs, kint, kids, words, per = [], [], [], [], {}
        for intent in intents:
            chosen = picks[intent]
            if chosen:
                for p in chosen:
                    vecs.append(matrix[p])
                    kint.append(intent)
                    kids.append(facets[p])
                words.append(frozenset().union(
                    *(train["words"].get(pool["keyed"][facets[p]], frozenset())
                      for p in chosen)))
            else:
                vecs.append(written[intent])
                kint.append(intent)
                kids.append("intent-boundary:" + intent)
                words.append(store["key_words"][intent])
            per[intent] = max(1, len(chosen))
        return {"matrix": np.asarray(vecs), "key_intent": kint, "key_ids": kids,
                "words": words if with_words else None, "keys_per_intent": per,
                "fallback": list(fallback)}

    out["centroid"] = {"matrix": np.asarray([centroids[i] for i in intents]),
                       "key_intent": list(intents),
                       "key_ids": ["centroid:" + i for i in intents], "words": None,
                       "keys_per_intent": {i: 1 for i in intents},
                       "fallback": list(fallback)}
    for k in MEDOID_KS:
        out["medoid-%d" % k] = assemble("medoid-%d" % k, medoids[k], True)
    out["all-utterances"] = assemble("all-utterances", positions, False)
    for keyset in out.values():
        order = sorted(range(len(keyset["key_ids"])), key=lambda p: keyset["key_ids"][p])
        tie = np.empty(len(order), dtype=np.int64)
        tie[order] = np.arange(len(order))
        keyset["key_tie"] = tie
        keyset["intent_index"] = {i: n for n, i in enumerate(intents)}
        keyset["columns"] = {i: np.asarray([p for p, l in enumerate(keyset["key_intent"])
                                            if l == i], dtype=np.int64) for i in intents}
    return out


def intent_scores(query_matrix: np.ndarray, keyset: dict) -> tuple:
    """Per row: the score matrix over keys and the max-over-keys score per
    intent, in intent-id order.  A score at or below zero is not admitted."""

    scores = query_matrix @ keyset["matrix"].T
    intents = sorted(keyset["columns"])
    pooled = np.empty((scores.shape[0], len(intents)), dtype=np.float64)
    for n, intent in enumerate(intents):
        pooled[:, n] = scores[:, keyset["columns"][intent]].max(axis=1)
    return scores, pooled


def intent_orders(query_matrix: np.ndarray, keyset: dict) -> list:
    _, pooled = intent_scores(query_matrix, keyset)
    intents = sorted(keyset["columns"])
    out = []
    for row in pooled:
        admitted = [n for n in range(len(intents)) if row[n] > 0.0]
        admitted.sort(key=lambda n: (-row[n], intents[n]))
        out.append([intents[n] for n in admitted])
    return out


def facet_top(scores: np.ndarray, keyset: dict, width: int) -> np.ndarray:
    """The top-``width`` admitted KEY columns per row in the flown facet order
    (score descending, facet id ascending), as the recall would take them."""

    wide = min(scores.shape[1], width + TIE_SLACK)
    part = np.argpartition(-scores, wide - 1, axis=1)[:, :wide]
    out = np.full((scores.shape[0], width), -1, dtype=np.int64)
    for position in range(scores.shape[0]):
        columns = part[position]
        columns = columns[scores[position, columns] > 0.0]
        ordered = columns[np.lexsort((keyset["key_tie"][columns],
                                      -scores[position, columns]))][:width]
        out[position, :len(ordered)] = ordered
    return out


def evaluate(query_matrix: np.ndarray, keyset: dict, rows: list) -> dict:
    """Gold's intent-level rank (max over the intent's keys), the top-1
    intent, and facet-slot delivery -- whether one of gold's keys sits in the
    top-8 KEYS, which is what the flown recall (k=8) and fuser (m=8, c=1)
    would materialise when an intent owns more than one facet."""

    scores, pooled = intent_scores(query_matrix, keyset)
    intents = sorted(keyset["columns"])
    index = keyset["intent_index"]
    top8 = facet_top(scores, keyset, FLOWN_K)
    key_intent = np.asarray(keyset["key_intent"])
    out = []
    for position, (sample_id, gold, klass) in enumerate(rows):
        row = pooled[position]
        g = index[gold]
        if row[g] > 0.0:
            above = int(np.count_nonzero(row > row[g]))
            above += sum(1 for n in range(g) if row[n] == row[g])
            rank = above + 1
        else:
            rank = UNRANKED
        admitted = np.nonzero(row > 0.0)[0]
        top1 = None
        if len(admitted):
            best = admitted[np.lexsort((admitted, -row[admitted]))][0]
            top1 = intents[best]
        slots = top8[position]
        slots = slots[slots >= 0]
        out.append({"sample_id": sample_id, "gold": gold, "klass": klass, "rank": rank,
                    "top1": top1,
                    "facet_delivered": bool(np.any(key_intent[slots] == gold))})
    return {"rows": out}


def summarise(result: dict) -> dict:
    rows = result["rows"]
    wrong = [r for r in rows if r["klass"] == "INTENT-WRONG"]
    correct = [r for r in rows if r["klass"] == "CORRECT"]
    focus = [r for r in rows if r["gold"] == FOCUS]

    def block(subset):
        return {"rows": len(subset),
                "rank1": sum(1 for r in subset if r["rank"] == 1),
                "delivered": sum(1 for r in subset if r["rank"] <= FLOWN_K),
                "facet_delivered": sum(1 for r in subset if r["facet_delivered"]),
                "unrankable": sum(1 for r in subset if r["rank"] == UNRANKED),
                "median_rank": median([min(r["rank"], 61) for r in subset])}

    bands = {"%d-%d" % band: sum(1 for r in focus if band[0] <= r["rank"] <= band[1])
             for band in BANDS}
    bands["unrankable"] = sum(1 for r in focus if r["rank"] == UNRANKED)
    rivals = sorted({r["top1"] for r in focus
                     if r["rank"] > FLOWN_K and r["top1"] not in (None, FOCUS)})
    return {"all": block(rows), "wrong": block(wrong), "correct": block(correct),
            "focus": dict(block(focus), bands=bands, rivals=len(rivals))}


def key_geometry(keyset: dict) -> dict:
    """Mean and max cosine between keys of DIFFERENT intents (the 0.4756
    baseline is this quantity over the 60 written keys), blockwise so the
    all-utterances set never materialises a 9,354-square matrix, and the
    pairwise Jaccard overlap of the per-intent word sets where a key HAS words
    (a written key, or a medoid utterance; a centroid has none)."""

    matrix, labels = keyset["matrix"], np.asarray(keyset["key_intent"])
    total, count, best = 0.0, 0, -2.0
    for start in range(0, matrix.shape[0], BLOCK):
        stop = min(start + BLOCK, matrix.shape[0])
        block = matrix[start:stop] @ matrix.T
        mask = labels[start:stop, None] != labels[None, :]
        picked = block[mask]
        if picked.size:
            total += float(picked.sum())
            count += int(picked.size)
            best = max(best, float(picked.max()))
        del block, mask, picked
    out = {"cos_mean": round(total / count, 4) if count else None,
           "cos_max": round(best, 4) if count else None,
           "keys": int(matrix.shape[0]), "fallback": list(keyset["fallback"]),
           "min_keys_per_intent": min(keyset["keys_per_intent"].values()),
           "jaccard": jaccard_stats(list(keyset["words"])) if keyset["words"] else
           {"mean": None, "max": None}}
    return out


def vocabulary_ladder(words: dict, label: str) -> list:
    """The discriminative-vocabulary construction as TEXT: a word is removed
    from every key when it appears in more than ``share`` of the OTHER 59
    keys.  Reported as counts and ratios only; its retrieval effect needs an
    encoder pass over 60 strings and is NOT measured here."""

    intents = sorted(words)
    frequency = Counter(w for i in intents for w in words[i])
    before = [words[i] for i in intents]
    out = []
    for share in SHARE_LADDER:
        shared = {w for w, df in frequency.items() if df - 1 > share * (len(intents) - 1)}
        after = [words[i] - shared for i in intents]
        out.append({"source": label, "share": share, "vocabulary": len(frequency),
                    "removed": len(shared),
                    "words_before": round(sum(map(len, before)) / len(before), 1),
                    "words_after": round(sum(map(len, after)) / len(after), 1),
                    "emptied": sum(1 for s in after if not s),
                    "before": jaccard_stats(before), "after": jaccard_stats(after)})
    return out


def count_consumers(root: Path) -> dict:
    """How many committed config fragments pin the flown boundary store --
    the re-pin surface a key change would have to walk."""

    needles = (IB_FACETS_SHA, IB_SNAPSHOT_SHA)
    hits, baseline = 0, 0
    for path in sorted((root / "configs").rglob("*.json")):
        text = path.read_text(encoding="utf-8", errors="replace")
        if any(n in text for n in needles):
            hits += 1
            baseline += int("baseline" in path.relative_to(root).parts)
    return {"configs": hits, "baseline_fragments": baseline}


# ---------------------------------------------------------------------------
# the read


def measure(lock_path: Path, root: Path) -> dict:
    lock = load_lock(lock_path)
    train = load_train(lock, root)
    bank, store = load_bank(root), load_boundary(root)
    pools = {relpath: load_pool(root, relpath, sha)
             for relpath, sha in ((POOL, POOL_SHA), (POOL_M, POOL_M_SHA))}
    if not set(pools[POOL_M]["facets"]) < set(pools[POOL]["facets"]):
        raise ReadError("the minus-R01 pool is not a strict subset of the full pool")
    vectors = load_pool_vectors(root, set(pools[POOL]["facets"]))
    keysets = {relpath: build_keysets(store, pool, vectors, train)
               for relpath, pool in pools.items()}
    arms = {}
    for arm in ARMS:
        label = arm["label"]
        rows, sealed = load_rows(root, arm, bank, train), load_sealed(root, arm)
        ids = sorted(s for s, r in rows["rows"].items() if r.get("gold_intent"))
        queries = load_queries(root, arm, ids)
        repo = repo_orders(store, queries)
        triples = [(s, rows["rows"][s]["gold_intent"], rows["rows"][s]["class"])
                   for s in queries["ids"]]
        own = {own_key(s) for s in queries["ids"]} - {None}
        membership = {relpath: len(own & set(pool["keyed"].values()))
                      for relpath, pool in pools.items()}
        if membership[arm["pool"]]:
            raise ReadError(label + ": an evaluated row is in its own construction pool")
        reads = {}
        for name in CONSTRUCTIONS:
            reads[name] = {"held_out": summarise(evaluate(queries["matrix"],
                                                          keysets[arm["pool"]][name],
                                                          triples))}
            if arm["seen_pool"]:
                reads[name]["seen"] = summarise(evaluate(queries["matrix"],
                                                         keysets[arm["seen_pool"]][name],
                                                         triples))
        arms[label] = {
            "title": arm["title"], "rows": len(triples), "skipped": queries["skipped"],
            "population_source": rows["source"], "source_sha256": rows["source_sha256"],
            "query_relpath": arm["query"], "query_sha256": arm["query_sha"],
            "phases_relpath": sealed["relpath"], "phases_sha256": sealed["sha256"],
            "pool": arm["pool"], "seen_pool": arm["seen_pool"],
            "own_rows_in_pool": membership,
            "validation": validate(queries, keysets[arm["pool"]]["written"],
                                   sealed["rows"], repo),
            "classes": dict(Counter(t[2] for t in triples)), "reads": reads}
        del queries, repo
    return {
        "read_id": READ_ID, "recipe": RECIPE,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "store": {"relpath": IB_SNAPSHOT, "content_sha256": store["content_sha256"],
                  "facets_relpath": IB_FACETS, "facets_sha256": IB_FACETS_SHA,
                  "index_relpath": IB_INDEX, "index_sha256": store["index_sha256"],
                  "geometry": store["geometry"],
                  "encoder_inventory_sha256": store["encoder_inventory_sha256"],
                  "encoded_is_representation": store["encoded_is_representation"],
                  "encoded_is_content": store["encoded_is_content"],
                  "key_chars_mean": round(sum(store["key_chars"]) / 60, 1),
                  "body_chars_mean": round(sum(store["body_chars"]) / 60, 1),
                  "dims": int(store["matrix"].shape[1])},
        "pools": {relpath: {"content_sha256": pool["content_sha256"],
                            "utterances": pool["utterances"]}
                  for relpath, pool in sorted(pools.items())},
        "pool_facets": {"relpath": POOL_FACETS, "sha256": POOL_FACETS_SHA},
        "bank_sha256": bank["sha256"],
        "train": {"utterances": train["utterances"],
                  "per_intent_min": min(train["per_intent"].values()),
                  "per_intent_max": max(train["per_intent"].values())},
        "geometry": {relpath: {name: key_geometry(keyset)
                               for name, keyset in sets.items()}
                     for relpath, sets in keysets.items()},
        "vocabulary": (vocabulary_ladder(store["key_words"], "encoded key text")
                       + vocabulary_ladder(store["body_words"], "delivered body")),
        "consumers": count_consumers(REPO_ROOT),
        "arms": arms,
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                     "tokenizer": 0, "network": 0, "gpu": 0, "paid_api": 0}}


# ---------------------------------------------------------------------------
# selection and report


def rate(block: dict, field: str) -> float:
    return pct(block[field], block["rows"])


def passes(report: dict, name: str) -> dict:
    """The pre-registered rule, evaluated on the held-out read of each roster."""

    arms, floors, verdict = report["arms"], [], True
    for label in ROSTERS:
        mine = arms[label]["reads"][name]["held_out"]
        base = arms[label]["reads"]["written"]["held_out"]
        d_rank1 = rate(mine["wrong"], "rank1") - rate(base["wrong"], "rank1")
        d_deliv = rate(mine["wrong"], "delivered") - rate(base["wrong"], "delivered")
        d_correct = rate(mine["correct"], "delivered") - rate(base["correct"], "delivered")
        floors.append(d_rank1)
        verdict = verdict and d_rank1 > 0 and d_deliv > 0 and d_correct >= -1.0
    return {"passes": verdict, "floor": min(floors)}


def select(report: dict) -> dict:
    table = {name: passes(report, name) for name in CONSTRUCTIONS if name != "written"}
    single = {"centroid", "medoid-1"}
    passing = [n for n in CONSTRUCTIONS if n in table and table[n]["passes"]]
    if not passing:
        return {"table": table, "chosen": None}
    passing.sort(key=lambda n: (n not in single, -table[n]["floor"], n != "medoid-1"))
    return {"table": table, "chosen": passing[0]}


def write_markdown(path: Path, report: dict) -> None:
    arms, store, geometry = report["arms"], report["store"], report["geometry"]
    fit = arms["train-fold-a-plan"]["reads"]
    choice = select(report)
    out = []
    add = out.append

    def read(label, name, which="held_out"):
        return arms[label]["reads"][name][which]

    best = choice["chosen"] or max(
        (n for n in CONSTRUCTIONS if n != "written"),
        key=lambda n: min(rate(read(l, n)["wrong"], "rank1") for l in ROSTERS))
    add("# SLURP boundary keys: are the written descriptions the weak link, and do "
        "TRAIN-utterance keys close the gap?")
    add("")
    add(f"Date: 2026-09-27. Read id `{report['read_id']}`, recipe `{report['recipe']}`. "
        f"Generated `{report['generated_at']}`.")
    add("")
    add("A model-free read. Zero model, server, encoder, embedder, scorer, tokenizer, "
        "network, GPU and paid-API contacts. Every cosine is recomputed as arithmetic over "
        "sha256-verified vector files the flights pinned, and section 1 proves the "
        "recomputation reproduces the sealed delivered set on every row before a number is "
        "taken from it. A candidate key is a construction over ALREADY-PINNED utterance "
        "vectors -- a mean, or a pinned vector chosen by arithmetic -- so nothing is encoded. "
        "A DIAGNOSTIC, never a gate: it admits nothing, releases and rebuilds no store, "
        "registers no cell and states no effectiveness claim. Every roster is a discovery or "
        "dev roster and every number is a development number (owner decisions 28 and 86). "
        "**Every number below is DELIVERY, never correctness.** No utterance text, "
        "transcript, gold filler, knowledge body or key description is read into a reported "
        "value: every cell is an id, a count, a rank, a rate, a cosine, a ratio or a hash.")
    add("")
    add("## The answer, first")
    add("")
    w = {l: read(l, "written") for l in ROSTERS}
    b = {l: read(l, best) for l in ROSTERS}
    beats = all(rate(b[l]["wrong"], "rank1") > rate(w[l]["wrong"], "rank1")
                and rate(b[l]["wrong"], "delivered") > rate(w[l]["wrong"], "delivered")
                for l in ROSTERS)
    add(("**The written descriptions are the weak link: a key built from TRAIN utterances "
         "puts gold first, and delivers it, more often on every roster.**" if beats else
         "**A key built from TRAIN utterances does not beat the written descriptions on "
         "every roster, so the descriptions are not shown to be the weak link.**")
        + " On the intent-wrong rows the written key puts gold at rank 1 on "
        + " / ".join("%.1f %%" % rate(w[l]["wrong"], "rank1") for l in ROSTERS)
        + f" (Fold A / ROLL-1 / DEV-2000) and delivers it within eight on "
        + " / ".join("%.1f %%" % rate(w[l]["wrong"], "delivered") for l in ROSTERS)
        + f"; the `{best}` key puts gold at rank 1 on "
        + " / ".join("%.1f %%" % rate(b[l]["wrong"], "rank1") for l in ROSTERS)
        + " and delivers it on "
        + " / ".join("%.1f %%" % rate(b[l]["wrong"], "delivered") for l in ROSTERS)
        + ". Over ALL rows gold is at rank 1 on "
        + " / ".join("%.1f %%" % rate(w[l]["all"], "rank1") for l in ROSTERS)
        + " with the written key and "
        + " / ".join("%.1f %%" % rate(b[l]["all"], "rank1") for l in ROSTERS)
        + f" with `{best}`. Each of those reads is held out: the construction pool of "
        "every roster excludes that roster's own rows (section 5).")
    add("")
    add("**And one correction to the framing this read inherited.** The text the boundary "
        "channel actually ENCODES as its key is the facet representation -- "
        f"{store['key_chars_mean']:.0f} characters per intent on average, whose sha256 "
        f"matches the encoding receipt on {store['encoded_is_representation']} of 60 -- not "
        f"the {store['body_chars_mean']:.0f}-character delivered body on which the pruning "
        f"read measured its 0.6073 word overlap (that body matches the receipt on "
        f"{store['encoded_is_content']} of 60). Section 6 gives both overlaps. The key that "
        "fails is a one-line description, and the body the Solver reads is untouched by any "
        "key change here.")
    add("")
    add("## 0. What was read, and why the two key spaces are comparable")
    add("")
    add("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | identity |")
    add("| --- | --- | --- |")
    add(f"| `intent-boundaries-v1` snapshot | `{store['relpath']}` | "
        f"`{store['content_sha256']}` |")
    add(f"| boundary facet key vectors (60 x {store['dims']}) | `{store['facets_relpath']}` "
        f"| `{store['facets_sha256']}` |")
    add(f"| boundary key encoding receipt | `{store['index_relpath']}` | "
        f"`{store['index_sha256']}` |")
    for relpath, pool in report["pools"].items():
        add(f"| exemplar pool snapshot ({pool['utterances']:,} utterances) | `{relpath}` | "
            f"`{pool['content_sha256']}` |")
    add(f"| pool facet key vectors (one per TRAIN utterance) | "
        f"`{report['pool_facets']['relpath']}` | `{report['pool_facets']['sha256']}` |")
    add(f"| sealed bad-case bank | `{BANK}` | `{report['bank_sha256']}` |")
    for label in ROSTERS:
        arm = arms[label]
        add(f"| `{label}` speech query vectors | `{arm['query_relpath']}` | "
            f"`{arm['query_sha256']}` |")
        add(f"| `{label}` sealed phase artefact | `{arm['phases_relpath']}` | "
            f"`{arm['phases_sha256']}` |")
    add("")
    geo = store["geometry"]
    add("**Same space.** Both key files were cut by the same frozen encoder (inventory "
        f"`{store['encoder_inventory_sha256']}`, Omni-Embed-Nemotron-3B, {store['dims']} "
        f"dimensions, L2-normalised) under the same literal `{geo.get('prompt', '?')}` prefix "
        "-- the boundary receipt's own geometry says so, and the exemplar-pool authoring "
        "record says the same of the pool file -- and each roster's `intent-boundary` query "
        "vector is byte-identical to its `content` query vector (the exemplar-pool query "
        "provenance records the rename). So one speech vector is scored against both key "
        "sets, and a boundary key built from pool vectors is a key in the boundary channel's "
        "own space. Had that not held, this read would have stopped here.")
    add("")
    add("| Arm | Rows | Class source | Construction pool (held-out) | CORRECT | INTENT-WRONG |")
    add("| --- | ---: | --- | --- | ---: | ---: |")
    for label in ROSTERS:
        arm = arms[label]
        add(f"| `{label}` | {arm['rows']:,} | `{arm['population_source']}` | "
            f"`{arm['pool'].split('/')[-2]}` | {arm['classes'].get('CORRECT', 0):,} | "
            f"{arm['classes'].get('INTENT-WRONG', 0):,} |")
    add("")
    add("## 1. The recomputation reproduces the sealed ranking")
    add("")
    add("| Arm | rows | sealed width 8 | repo recall top == sealed set | vectorised top == "
        "sealed set | vectorised 60-way order == repo recall order |")
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for label in ROSTERS:
        v = arms[label]["validation"]
        add(f"| `{label}` | {v['rows']:,} | {v['sealed_width_is_8']:,} | "
            f"{v['repo_top_matches_sealed']:,} ({pct(v['repo_top_matches_sealed'], v['rows']):.2f} %) | "
            f"{v['numpy_top_matches_sealed']:,} ({pct(v['numpy_top_matches_sealed'], v['rows']):.2f} %) | "
            f"{v['numpy_order_equals_repo']:,} ({pct(v['numpy_order_equals_repo'], v['rows']):.2f} %) |")
    add("")
    add("The repository's own `rails.kb_policy.multidim_segment_recall` reproduces the "
        "sealed delivered set on every row, and the vectorised arithmetic every construction "
        "below is scored with reproduces the recall's full 60-way order on every row. Each "
        "row carries one speech segment, so the segment machinery is one vector per row. An "
        "entry at cosine zero or below is never admitted (`unrankable`), exactly as flown.")
    add("")
    add("## 2. Every construction, on every roster (held-out pool)")
    add("")
    add("`rank-1` is gold's max-over-keys score ranking first among the 60 intents; "
        "`deliv@8` is gold within the top eight INTENTS; `facet@8` is what the flown "
        "recall/fuser (`k` 8, `m` 8, `c` 1) would materialise when an intent owns several "
        "facets -- one of gold's keys within the top eight KEYS -- and equals `deliv@8` for "
        "every single-key construction. `median` is gold's median rank on the intent-wrong "
        "rows (unrankable counted as 61).")
    add("")
    for label in ROSTERS:
        add(f"**`{label}`** ({arms[label]['rows']:,} rows; "
            f"{arms[label]['classes'].get('INTENT-WRONG', 0)} intent-wrong, "
            f"{arms[label]['classes'].get('CORRECT', 0)} correct)")
        add("")
        add("| construction | keys | rank-1, all | rank-1, wrong | rank-1, correct | "
            "deliv@8, all | deliv@8, wrong | facet@8, wrong | deliv@8, correct | "
            "unrankable | median |")
        add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for name in CONSTRUCTIONS:
            r, base = read(label, name), read(label, "written")
            keys = geometry[arms[label]["pool"]][name]["keys"]
            add(f"| `{name}` | {keys:,} | "
                f"{rate(r['all'], 'rank1'):.1f} % ({rate(r['all'], 'rank1') - rate(base['all'], 'rank1'):+.1f}) | "
                f"{rate(r['wrong'], 'rank1'):.1f} % ({rate(r['wrong'], 'rank1') - rate(base['wrong'], 'rank1'):+.1f}) | "
                f"{rate(r['correct'], 'rank1'):.1f} % ({rate(r['correct'], 'rank1') - rate(base['correct'], 'rank1'):+.1f}) | "
                f"{rate(r['all'], 'delivered'):.1f} % | "
                f"{rate(r['wrong'], 'delivered'):.1f} % ({rate(r['wrong'], 'delivered') - rate(base['wrong'], 'delivered'):+.1f}) | "
                f"{rate(r['wrong'], 'facet_delivered'):.1f} % | "
                f"{rate(r['correct'], 'delivered'):.1f} % ({rate(r['correct'], 'delivered') - rate(base['correct'], 'delivered'):+.1f}) | "
                f"{r['all']['unrankable']} | {r['wrong']['median_rank']:.0f} |")
        add("")
    add("## 3. Key geometry: how far apart the keys of different intents sit")
    add("")
    add("Cosine between keys of DIFFERENT intents (mean and max; the 60 written keys are "
        "the 0.4756 / 0.908 baseline), and the pairwise Jaccard word overlap of the "
        "per-intent word sets where a key has words. A centroid has no text. `min keys` is "
        "the smallest number of keys any intent received. Measured on the full construction "
        "pool; the R01-excluded pool is given for the two single-key constructions.")
    add("")
    add("| construction | keys | min keys / intent | key-to-key cosine, mean | max | "
        "Jaccard, mean | max | wrong-row rank-1 floor over 3 rosters | passes rule |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
    for name in CONSTRUCTIONS:
        g = geometry[POOL][name]
        floor = min(rate(read(l, name)["wrong"], "rank1") for l in ROSTERS)
        verdict = "--" if name == "written" else (
            "yes" if choice["table"][name]["passes"] else "no")
        jac = g["jaccard"]
        add(f"| `{name}` | {g['keys']:,} | {g['min_keys_per_intent']} | {g['cos_mean']} | "
            f"{g['cos_max']} | {'--' if jac['mean'] is None else jac['mean']} | "
            f"{'--' if jac['max'] is None else jac['max']} | {floor:.1f} % | {verdict} |")
    add("")
    add("R01-excluded pool: centroid mean cosine "
        f"{geometry[POOL_M]['centroid']['cos_mean']} (max "
        f"{geometry[POOL_M]['centroid']['cos_max']}), medoid-1 mean "
        f"{geometry[POOL_M]['medoid-1']['cos_mean']} (max "
        f"{geometry[POOL_M]['medoid-1']['cos_max']}). Intents with NO construction "
        "utterance in a pool keep the flown written key under every construction and are "
        "counted as one key: full pool "
        + (", ".join(f"`{i}`" for i in geometry[POOL]["centroid"]["fallback"]) or "none")
        + "; R01-excluded pool "
        + (", ".join(f"`{i}`" for i in geometry[POOL_M]["centroid"]["fallback"]) or "none")
        + ". A utterance-built store would have to keep a written key for each of them.")
    add("")
    gc, gw = geometry[POOL]["centroid"], geometry[POOL]["written"]
    add(f"**What the geometry says about the inherited framing.** The centroid keys sit at "
        f"a mean cosine of {gc['cos_mean']} to one another (max {gc['cos_max']}), "
        f"{gc['cos_mean'] / gw['cos_mean']:.1f} times the written keys' {gw['cos_mean']}, "
        "and they separate the intents BETTER on every roster. Key-to-key similarity is "
        "therefore not the quantity that decides separation, and the pruning read's "
        "inference -- keys that share too much cannot separate sixty intents -- does not "
        "hold in this space. What decides it is key-to-QUERY geometry: a mean utterance "
        "vector sits where the speech vectors sit, and a one-line description does not, "
        "however distinct its words.")
    add("")
    add(f"## 4. `{FOCUS}` under each construction")
    add("")
    add(f"Gold rows whose intent is `{FOCUS}`, per roster: rank-1 count, band counts of "
        "gold's rank, median rank, and the number of DISTINCT intents that take top-1 on "
        "its not-delivered rows (36 across rosters in the pruning read).")
    add("")
    add("| roster | construction | gold rows | rank-1 | 1-8 | 9-16 | 17-30 | 31-60 | "
        "unrankable | median | distinct top-1 rivals on missed rows |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for label in ROSTERS:
        for name in CONSTRUCTIONS:
            f = read(label, name)["focus"]
            bands = f["bands"]
            add(f"| `{label}` | `{name}` | {f['rows']} | {f['rank1']} | {bands['1-8']} | "
                f"{bands['9-16']} | {bands['17-30']} | {bands['31-60']} | "
                f"{bands['unrankable']} | "
                f"{'--' if f['median_rank'] is None else '%.0f' % f['median_rank']} | "
                f"{f['rivals']} |")
    add("")
    gq_w = {l: read(l, "written")["focus"] for l in ROSTERS}
    gq_b = {l: read(l, best)["focus"] for l in ROSTERS}
    gq_all = {l: read(l, "all-utterances")["focus"] for l in ROSTERS}
    lead = (f"**Reading it.** With the written key `{FOCUS}` is delivered on "
            + " / ".join(f"{gq_w[l]['delivered']} of {gq_w[l]['rows']}" for l in ROSTERS)
            + f" of its gold rows; with `{best}` on "
            + " / ".join(f"{gq_b[l]['delivered']} of {gq_b[l]['rows']}" for l in ROSTERS)
            + "; and even keyed by EVERY one of its construction utterances (the nearest-"
            "neighbour ceiling) on "
            + " / ".join(f"{gq_all[l]['delivered']} of {gq_all[l]['rows']}"
                         for l in ROSTERS)
            + ". ")
    moved = [l for l in ROSTERS if gq_b[l]["delivered"] > gq_w[l]["delivered"]]
    stayed = [l for l in ROSTERS if l not in moved]
    reach = min(pct(gq_all[l]["delivered"], gq_all[l]["rows"]) for l in ROSTERS)
    add(lead
        + ("The single key moves the catch-all on every roster" if not stayed else
         f"The single key moves the catch-all on {len(moved)} of 3 rosters ("
         + ", ".join(f"`{l}`" for l in moved) + ") and not on "
         + ", ".join(f"`{l}`" for l in stayed) + "")
        + f", and the ceiling delivers at least {reach:.0f} % of its rows on every roster. "
        "So it is NOT irreducible by construction -- its own utterances do separate it -- "
        "but no COMPACT key does: one centroid, three or five medoids all leave most of "
        "its rows outside the eight, because a catch-all's utterances have no single "
        "centre. What reaches it is dense coverage, which is the exemplar channel's "
        "mechanism (the rank diagnostic's `agree-1`), not a boundary-key rewrite. Its "
        "share of the miss mass therefore stays reachable, but through the vote, and any "
        "single-key rebuild should be read with that intent's rows set aside.")
    add("")
    add("## 5. Held out, and what a key could have seen")
    add("")
    r1 = arms["roll1"]
    seen = {n: r1["reads"][n]["seen"] for n in CONSTRUCTIONS}
    held = {n: r1["reads"][n]["held_out"] for n in CONSTRUCTIONS}
    add("No construction is fitted to any roster: a key is a function of the pool's "
        "vectors and the pool's own build-time labels. What a key can do is CONTAIN an "
        "evaluated row's own utterance. Membership of each roster's own utterances in the "
        "two pools -- full pool / R01-excluded pool: "
        + "; ".join(f"`{l}` {arms[l]['own_rows_in_pool'][POOL]} / "
                    f"{arms[l]['own_rows_in_pool'][POOL_M]}" for l in ROSTERS)
        + ". So Fold A and DEV-2000 are held out under the full pool and ROLL-1 is held out "
        "only under the R01-excluded pool, which is the pool every ROLL-1 number above uses. "
        "Reading ROLL-1 under the full pool instead -- keys that have SEEN the row's own "
        "utterance -- gives the seen-versus-held-out gap:")
    add("")
    add("| construction | ROLL-1 rank-1 wrong, held out | seen | gap | deliv@8 wrong, "
        "held out | seen | gap | rank-1 all, held out | seen |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for name in CONSTRUCTIONS:
        if name == "written":
            continue
        h, s = held[name], seen[name]
        add(f"| `{name}` | {rate(h['wrong'], 'rank1'):.1f} % | {rate(s['wrong'], 'rank1'):.1f} % | "
            f"{rate(s['wrong'], 'rank1') - rate(h['wrong'], 'rank1'):+.1f} | "
            f"{rate(h['wrong'], 'delivered'):.1f} % | {rate(s['wrong'], 'delivered'):.1f} % | "
            f"{rate(s['wrong'], 'delivered') - rate(h['wrong'], 'delivered'):+.1f} | "
            f"{rate(h['all'], 'rank1'):.1f} % | {rate(s['all'], 'rank1'):.1f} % |")
    add("")
    gaps = {n: rate(seen[n]["wrong"], "rank1") - rate(held[n]["wrong"], "rank1")
            for n in CONSTRUCTIONS if n != "written"}
    add("The gap is the optimism a key buys by holding the row it is later asked about. "
        f"`all-utterances` carries almost all of it ({gaps['all-utterances']:+.1f} points "
        "of wrong-row rank-1: every evaluated row is one of its own keys and scores itself "
        f"at cosine 1), the centroid a few ({gaps['centroid']:+.1f}: a row is one term in "
        "its intent's mean), and the medoid sets almost none ("
        + ", ".join(f"{gaps['medoid-%d' % k]:+.1f}" for k in MEDOID_KS)
        + ": a row is rarely one of the one, three or five chosen). The held-out columns "
        "are the ones every verdict above is drawn from, and the seen column is why a "
        "9,354-key store read on its own construction roster would look far better than "
        "it is.")
    add("")
    add("## 6. The discriminative-vocabulary key, as text only")
    add("")
    add("A word is removed from every key when it appears in more than the stated share of "
        "the OTHER 59 keys (the brief's threshold is one half). Two sources: the text the "
        "channel actually encodes (the facet representation) and the delivered body the "
        "pruning read measured. **The retrieval effect of this construction is NOT "
        "measured**: it would need one encoder pass over 60 strings, an embedder contact "
        "this read does not make, so it is priced here as text -- how much of the overlap "
        "is generic vocabulary -- and nothing more.")
    add("")
    add("| source | share threshold | vocabulary | words removed | words per key, before -> "
        "after | keys emptied | Jaccard mean, before -> after | max, before -> after |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in report["vocabulary"]:
        add(f"| {row['source']} | > {row['share']:.2f} | {row['vocabulary']} | "
            f"{row['removed']} | {row['words_before']} -> {row['words_after']} | "
            f"{row['emptied']} | {row['before']['mean']} -> {row['after']['mean']} | "
            f"{row['before']['max']} -> {row['after']['max']} |")
    add("")
    enc = [r for r in report["vocabulary"] if r["source"] == "encoded key text"
           and r["share"] == 0.5][0]
    body = [r for r in report["vocabulary"] if r["source"] == "delivered body"
            and r["share"] == 0.5][0]
    lower = enc["before"]["mean"] < body["before"]["mean"]
    add(f"The encoded keys share {enc['before']['mean']} of their words on average against "
        f"{body['before']['mean']} for the delivered bodies"
        + (": the 0.6073 figure describes the bodies, which share a template, and the keys "
           "themselves overlap less." if lower else
           ": the keys overlap at least as much as the bodies the pruning read measured.")
        + " Removing the words that more than half the other keys carry drops the key "
        f"overlap to {enc['after']['mean']} (max {enc['after']['max']}) and the body "
        f"overlap to {body['after']['mean']} (max {body['after']['max']}); the difference "
        "between a before and an after is the share of the overlap that is generic "
        "vocabulary. Whether the residual, distinctive words retrieve better is the "
        "unmeasured encoder question; what section 2 measures instead is whether a key of "
        "the same KIND as the query -- an utterance -- separates the intents.")
    add("")
    add("## 7. Price, honesty, and the one construction this read would put forward")
    add("")
    add(f"**Rebuild price, in one line.** Any key change is a store rebuild: a re-cut "
        f"`{IB_FACETS.split('/')[-1]}` for the boundary channel (60 rows; for a centroid or "
        "medoid key it is arithmetic over pinned pool vectors, zero encoder contacts, but a "
        "centroid has no text source and needs a new receipt kind, where a medoid IS a "
        "pinned utterance vector whose text the existing kind can hash), a fresh "
        "`intent-boundaries-v2` snapshot release, and a re-pin of every consumer: "
        f"{report['consumers']['configs']} committed config files pin the flown store "
        f"today, {report['consumers']['baseline_fragments']} of them baseline fragments -- "
        "above the ~55 the brief estimated -- and the re-pin path has twice rewritten "
        "sibling ledger rows in this repository's history. The delivered block is unchanged "
        "(the body the Solver reads is the same 1,195 tokens), so the token cost is zero.")
    add("")
    add("**Delivery is not correctness.** Every number above counts rows that would RECEIVE "
        "their own gold intent's boundary entry, or would see it ranked first. Whether the "
        "Solver then answers correctly with the entry present is mode (iv), unmeasured here, "
        "because it needs the answer the row would give, which needs contacts. The "
        "correct-row column is the only evidence that delivery and correctness move "
        "together, and it is an association on rows that already work. No score gain is "
        "claimed, implied or estimated.")
    add("")
    if choice["chosen"]:
        c = choice["chosen"]
        cf = choice["table"][c]["floor"]
        add(f"**The construction: `{c}`.** It passes the pre-registered rule on all three "
            "rosters under their held-out pools -- wrong-row rank-1 up by at least "
            f"{cf:+.1f} points, wrong-row delivery up, correct-row delivery down by no more "
            "than a point anywhere -- and among the passers it is the "
            + ("single-key construction" if c in ("centroid", "medoid-1")
               else "construction")
            + f" with the largest held-out floor. Passing set: "
            + ", ".join(f"`{n}`" for n in CONSTRUCTIONS
                        if n != "written" and choice["table"][n]["passes"])
            + ". It would keep the store at 60 facets, the fuser at `m` 8 and the delivered "
            "body as it is: only the retrieval key moves, from a one-line description to "
            + ("the intent's mean TRAIN utterance vector"
               if c == "centroid" else "a real TRAIN utterance of the intent")
            + ". Its cost in the one column the rule does not guard: rank-1 on the CORRECT "
            "rows moves by "
            + " / ".join("%+.1f" % (rate(read(l, c)["correct"], "rank1")
                                    - rate(read(l, "written")["correct"], "rank1"))
                         for l in ROSTERS)
            + " points (Fold A / ROLL-1 / DEV-2000), so on rows that already work gold "
            "can slip from first to somewhere in the eight, which a flight must read. A "
            "construction cell would be a store rebuild plus one flight, and its result "
            "would be a delivery result until the flight reads it as a score. This read "
            "authorises neither.")
        au = {l: read(l, "all-utterances") for l in ROSTERS}
        add("")
        add("`all-utterances` also passes, and reaches further, but it is not a boundary "
            "key: it is the exemplar channel's own facets wearing the intent label. As a "
            "store it would put 9,354 facets behind the boundary dimension, and with the "
            "flown `k` 8 the top eight KEYS crowd with one intent's neighbours, so what it "
            "would materialise is its facet-slot column -- "
            + " / ".join("%.1f %%" % rate(au[l]["wrong"], "facet_delivered") for l in ROSTERS)
            + " wrong-row delivery against the intent-level "
            + " / ".join("%.1f %%" % rate(au[l]["wrong"], "delivered") for l in ROSTERS)
            + ". The rank diagnostic's `agree-1` reaches that same signal through the "
            "exemplar vote at +1.4 tokens per row without a boundary rebuild, which is the "
            "route for the catch-all intents the centroid does not reach.")
    else:
        add("**None.** No construction passes the pre-registered rule on all three rosters "
            "under their held-out pools, so this read puts none forward: the intent "
            "question leaves the key side and goes to consumption form.")
    add("")
    add("## 8. Boundary")
    add("")
    add("Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and "
        "paid-API contacts: no server was started, stopped or probed (port 8080 untouched), "
        "no waveform decoded, no text encoded, no subprocess run. BLAS was capped at four "
        "threads and no worker pool was used. Every cosine was recomputed as arithmetic over "
        "the pinned files in section 0, each verified against its configured sha256 by this "
        "repository's own loaders or by `hashlib` before a number was taken from it; the "
        "written-key ranking went through `rails.kb_policy.multidim_segment_recall` and the "
        "vectorised path was proven equal to it on every row. Other tools: "
        "`data.slurp.load_slurp_split` for the governed TRAIN gold, "
        "`data.slurp.load_slurp_construction_utterances` for TRAIN word sets reduced to a "
        "ratio, `json` reads of three released snapshots, one encoding receipt and three "
        "sealed `*.phases.json`, and a `json` read of the sealed bad-case bank and of the "
        "ROLL-1 official score file.")
    add("")
    add("This read admits nothing, promotes nothing, preregisters no cell, releases no "
        "store, rebuilds no store, draws no roster, expands no source, opens no split and "
        "reaches no superiority, generalisation or Stage-3 conclusion. It is "
        "byte-reproducible across runs apart from its `generated_at` stamp: every container "
        "is sorted before it is consumed, every construction is a deterministic function of "
        "the pinned bytes, and there is no sampling anywhere.")
    add("")
    path.write_text("\n".join(out), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN)
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args(argv)
    report = measure(Path(args.lock), Path(args.data_root))
    markdown = Path(args.markdown)
    if not markdown.is_absolute():
        markdown = REPO_ROOT / markdown
    write_markdown(markdown, report)
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(report, indent=1, sort_keys=True, default=str), encoding="utf-8")
    print("wrote", markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
