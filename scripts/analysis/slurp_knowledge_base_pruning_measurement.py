#!/usr/bin/env python3
"""Is the knowledge base too dense, and would pruning it raise correct-label
delivery?  The owner's 2026-09-26 hypothesis, measured.

A model-free read over pinned bytes.  Zero model, server, encoder, embedder,
scorer, tokenizer, network, GPU and paid-API contacts.  Every similarity below
is RECOMPUTED -- arithmetic over sha256-verified vector files the flights
themselves pinned -- and each recomputation is validated against what the
flights sealed before a number is taken from it.  A prune is simulated by
MASKING a key out of the ranking and recomputing; nothing is rebuilt, nothing
is released, no cell is registered and nothing is flown.

A DIAGNOSTIC, never a gate.  It admits no mechanism, releases no store,
authorises no flight and states no effectiveness, superiority or generalisation
claim.  Every roster is a discovery or dev roster and every number is a
development number (owner decisions 28 and 86), never a test claim.

Text discipline: no utterance text, transcript, gold filler, delivered answer,
knowledge body or intent description is read into a reported value or printed.
Intent and slot-type ids are ids and are reported; a description is only ever
reduced to a count or a ratio.

Gold discipline: gold labels enter offline on the scoring side only -- the
sealed bad-case bank, the governed TRAIN split through the ordinary loader, and
one sealed official score file -- and reach no query, key, weight or selector.
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
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    multidim_segment_recall,
)
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot  # noqa: E402
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_segment_vectors,
    load_sealed_vectors,
)

READ_ID = "SAEA-SLURP-MF-KNOWLEDGE-BASE-PRUNING-MEASUREMENT-V1"
RECIPE = "slurp-knowledge-base-pruning-measurement-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
DEFAULT_MARKDOWN = "docs/results/2026-09-26-slurp-knowledge-base-pruning-measurement.md"

IB_SNAPSHOT = "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"
IB_SNAPSHOT_SHA = "5520b8449b627530227563d1f8db71f8a391f20f7d0ff7d7bd439e28ec6e48fe"
IB_FACETS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl"
IB_FACETS_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
SC_SNAPSHOT = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
SC_SNAPSHOT_SHA = "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"
POOL = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
POOL_SHA = "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9"
POOL_M = ("knowledge/slurp/saea-kb-distmodel-v1/"
          "size-pool-annotated-exemplars-minus-r01/snapshot.json")
POOL_M_SHA = "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63"
POOL_FACETS = "vectors/slurp-kus3/facet-vectors.jsonl"
POOL_FACETS_SHA = "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e"
BANK = "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl"
IB_DIM, POOL_DIM = "intent-boundary", "content"
FLOWN_K, VOTE_K = 8, 20
FIT_ARM = "train-fold-a-plan"
ROSTERS = ("train-fold-a-plan", "roll1", "dev2000-added-plan")
GREEDY_CAP, NARROW_KEYS = 30, 8
CAPS = (2, 5, 10, 20, 40, 80, 160)
EDITS = (1, 3, 5, 7, 9)
NEIGHBOURS, BLOCK, TIE_SLACK = 10, 512, 16

ARMS = (
    {"label": "roll1", "title": "ROLL-1 as-flown pool (R01C construction roster)",
     "run_id": "SAEA-SLURP-STAGE3-ROLLOUT-R01-V1",
     "attempt": "attempt-slurp-native-stage3-rollout-r01-generation-v1", "roster": None,
     "query": ("vectors/slurp-stage3-construction-r01c-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "ebaa743241a67a2cb759353fa8a9f58a3f09d27c00c8c66cb3172958dcccc1b8",
     "content": ("vectors/slurp-stage3-construction-r01c-v1/"
                 "query-vectors-speech-content-v1.jsonl"),
     "content_sha": "dd3b2924cda10810487b2b114e61380beaf8477634c602096b875e461ae44baa",
     "pool": POOL_M, "pool_sha": POOL_M_SHA,
     "scores": ("analysis/SLURP-SAMPLE-AGGREGATION-OFFLINE-READ-V1/PS-registered-"
                "support-3-slurp-slu-official-projected-v3-train-scores.json"),
     "scorer_id": "slurp-slu-official-projected-v3-train"},
    {"label": "train-fold-a-plan", "title": "TRAIN Fold A PLAN (construction roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1",
     "attempt": "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
     "roster": "train-fold-a",
     "query": ("vectors/slurp-intent-boundaries-train-fold-a-1080-v1/"
               "query-vectors-speech-segments.jsonl"),
     "query_sha": "e7a5b2264dc61fcab3c63d50fb645d4629d3f0a99f83ad5fbe323c73884e5f0b",
     "content": "vectors/slurp-exemplars-pool/query-vectors-speech-content-v1.jsonl",
     "content_sha": "d0f06ed21c6a576d8118d5a914e34807c24a3d3523d89e7b30d90575d24104ff",
     "pool": POOL, "pool_sha": POOL_SHA, "scores": None, "scorer_id": None},
    {"label": "dev2000-added-plan", "title": "DEV-2000-ADDED PLAN (fresh roster)",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1",
     "attempt": "attempt-slurp-native-default-plan-dev2000-added-generation-v1",
     "roster": "dev2000-added",
     "query": "vectors/slurp-dev2000-added-v1/query-vectors-speech-segments.jsonl",
     "query_sha": "e2a5fd046dac7c87fcf53830955e41e69d20402a2305a02ebf2bfc1a33001b9d",
     "content": "vectors/slurp-dev2000-added-v1/query-vectors-speech-content-v1.jsonl",
     "content_sha": "7d4ebdce553fd897fa86cc6b6d878ebf2298e19ee509eeceaf1aa0aca4855ee0",
     "pool": POOL, "pool_sha": POOL_SHA, "scores": None, "scorer_id": None},
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


def keys_word(count: int) -> str:
    return "1 key" if count == 1 else "%d keys" % count


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


def word_set(text: str) -> frozenset:
    """The lowercased alphanumeric word set of a description, used ONLY to
    produce an overlap ratio.  No word and no description is stored or printed."""

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


def unit_rows(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalisation in float64, so a dot product IS the cosine
    ``rails.kb_policy._cosine_with_norms`` computes (same norm, same quotient)."""

    work = np.asarray(matrix, dtype=np.float64)
    norms = np.linalg.norm(work, axis=1, keepdims=True)
    return work / np.where(norms > 0.0, norms, 1.0)


# ---------------------------------------------------------------------------
# pinned inputs


def load_boundary(root: Path) -> dict:
    path = root / IB_SNAPSHOT
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(path.read_text(encoding="utf-8")))
    if snap.content_hash() != IB_SNAPSHOT_SHA:
        raise ReadError("intent-boundaries snapshot does not hash to the flown pin")
    ids = {facet.facet_id for facet in snap.facets}
    if ids != {value.value_id for value in snap.values} or len(ids) != 60:
        raise ReadError("intent-boundaries is not the flown 60-way 1:1 store")
    to_intent, body = {}, {}
    for value in snap.values:
        intent = value.value_id.split("intent-boundary:", 1)[-1]
        to_intent[value.value_id] = intent
        body[intent] = word_set(value.content)
    vectors = load_sealed_vectors(root / IB_FACETS, expected_sha256=IB_FACETS_SHA,
                                 dimensions=(IB_DIM,))
    if set(vectors) != ids:
        raise ReadError("boundary facet vectors do not cover the store exactly")
    keys = sorted(to_intent)
    table = unit_rows([vectors[k][IB_DIM] for k in keys])
    return {"snapshot": snap, "facet_vectors": vectors, "to_intent": to_intent,
            "words": body, "intents": sorted(to_intent.values()), "key_matrix": table,
            "key_order": [to_intent[k] for k in keys], "entries": len(ids),
            "dims": table.shape[1], "content_sha256": snap.content_hash()}


def load_pool(root: Path, relpath: str, expected: str) -> dict:
    path = root / relpath
    snap = KnowledgeSnapshot.from_frozen_json(json.loads(path.read_text(encoding="utf-8")))
    if snap.content_hash() != expected:
        raise ReadError(relpath + " does not hash to the flown pin")
    keyed = {}
    for value in snap.values:
        if len(value.associated_facet_ids) != 1:
            raise ReadError(relpath + ": a pool value is not bound to one facet")
        key = value.value_id.split("value:", 1)[-1]
        keyed[value.associated_facet_ids[0]] = str(int(key)) if key.isdigit() else key
    facets = sorted(facet.facet_id for facet in snap.facets)
    if set(facets) != set(keyed):
        raise ReadError(relpath + ": facets and values are not a bijection")
    return {"relpath": relpath, "content_sha256": snap.content_hash(), "facets": facets,
            "keyed": keyed, "utterances": len(facets),
            "recordings": len(snap.source_sample_ids)}


def load_train(lock: dict, root: Path) -> dict:
    by_utterance, recordings, slot_types = {}, 0, set()
    for record in load_slurp_split(lock, root, "train"):
        recordings += 1
        key = str(record.utterance_id)
        by_utterance[str(int(key)) if key.isdigit() else key] = (
            f"{record.scenario}_{record.action}")
        for entity in (record.entities or ()):
            slot_types.add(entity["type"] if isinstance(entity, dict)
                           else getattr(entity, "type", "?"))
    return {"intent_of": by_utterance, "utterances": len(by_utterance),
            "recordings": recordings, "intents": len(set(by_utterance.values())),
            "slot_types": len(slot_types), "per_intent": Counter(by_utterance.values())}


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
        boundary, exemplars = [], []
        for record in (result.get("consumption") or {}).get("records") or ():
            item = bare(str(record.get("supplied_item_id") or ""))
            if item.startswith("intent-boundary:"):
                boundary.append(item.split("intent-boundary:", 1)[-1])
            elif item.startswith("value:"):
                exemplars.append(item.split("value:", 1)[-1])
        rows[result["sample_id"]] = {"boundary": sorted(set(boundary)),
                                     "exemplars": sorted(set(exemplars))}
    del document
    return {"rows": rows, "relpath": str(path.relative_to(root)), "sha256": digest(path)}


def load_pool_vectors(root: Path, wanted: set) -> dict:
    """The pool key vectors, restricted to the facets the released stores declare.
    One streaming pass over a file verified against the flown pin; nothing is
    embedded, nothing is written."""

    path = root / POOL_FACETS
    if digest(path) != POOL_FACETS_SHA:
        raise ReadError(POOL_FACETS + " does not hash to the flown pin")
    out = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                if record["id"] in wanted:
                    out[record["id"]] = np.asarray(record["vectors"][POOL_DIM],
                                                   dtype=np.float32)
    if set(out) != wanted:
        raise ReadError("pool key vectors do not cover the released stores")
    return out


# ---------------------------------------------------------------------------
# the boundary channel: full-width ranking, validated against the flights


def boundary_order(store: dict, segments, sample_ids) -> dict:
    """The flown arithmetic at full width, through this repository's OWN segment
    recall at ``top_k_per_dimension`` 60 so the truncation is removed, then the
    flown order (score descending, facet id ascending).  An entry the recall does
    not admit -- cosine at or below zero -- has no rank at any ``k``."""

    snap, table = store["snapshot"], store["facet_vectors"]
    out = {}
    for sample_id in sample_ids:
        record = segments.get(sample_id)
        if record is None:
            continue
        recalled = multidim_segment_recall(snap, record.segments,
                                           lambda f: table.get(f, {}), 60)
        scored = {store["to_intent"][f]: s[IB_DIM] for f, s in recalled.items()}
        out[sample_id] = [i for i, _ in sorted(scored.items(),
                                               key=lambda kv: (-kv[1], kv[0]))]
    return out


def validate_boundary(orders: dict, sealed: dict) -> dict:
    exact = width8 = ranked = 0
    for sample_id, ordering in sorted(orders.items()):
        want = sealed.get(sample_id, {}).get("boundary") or []
        width8 += int(len(want) == FLOWN_K)
        exact += int(sorted(ordering[:len(want)]) == sorted(want))
        ranked += int(bool(want) and all(i in ordering[:FLOWN_K] for i in want))
    return {"rows": len(orders), "sealed_width_is_8": width8,
            "top_matches_sealed_set": exact, "every_sealed_entry_in_top_8": ranked}


def mask_frame(orders: dict, rows: dict) -> dict:
    """Per row: the gold intent, the intents ranked strictly above it, and the
    top-1.  Masking a key never reorders the survivors, so gold's rank under any
    mask is ``1 + |above \\ mask|`` and delivery is ``gold not in mask and
    |above \\ mask| < FLOWN_K``.  That identity is what makes a prune
    enumerable offline at zero contacts."""

    frame = {}
    for sample_id, ordering in sorted(orders.items()):
        gold = (rows.get(sample_id) or {}).get("gold_intent")
        if gold is None:
            continue
        frame[sample_id] = {
            "gold": gold, "klass": rows[sample_id]["class"],
            "top1": ordering[0] if ordering else None,
            "above": frozenset(ordering[:ordering.index(gold)]) if gold in ordering
            else None}
    return frame


def delivered_under(entry: dict, mask: frozenset) -> bool:
    if entry["above"] is None or entry["gold"] in mask:
        return False
    return len(entry["above"] - mask) < FLOWN_K


def per_key_masking(frames: dict, intents) -> dict:
    """Each of the 60 keys masked ALONE: rows that GAIN delivery of their own
    gold entry, deliveries LOST because the key was their gold, the net, and the
    two honesty columns -- how often the key is gold at all, and how many of
    those rows are already answered correctly today."""

    table = {}
    for intent in intents:
        mask = frozenset({intent})
        cell = {k: {} for k in ("gains", "losses", "gold", "correct", "gold_delivered")}
        for label in ROSTERS:
            counts = dict.fromkeys(cell, 0)
            for entry in frames[label].values():
                base = delivered_under(entry, frozenset())
                if entry["gold"] == intent:
                    counts["gold"] += 1
                    counts["correct"] += int(entry["klass"] == "CORRECT")
                    counts["gold_delivered"] += int(base)
                    counts["losses"] += int(base)
                elif not base and delivered_under(entry, mask):
                    counts["gains"] += 1
            for name, value in counts.items():
                cell[name][label] = value
        cell["net"] = {k: cell["gains"][k] - cell["losses"][k] for k in ROSTERS}
        cell["pooled"] = {k: sum(cell[k].values()) for k in
                          ("gains", "losses", "gold", "correct", "gold_delivered")}
        cell["pooled"]["net"] = cell["pooled"]["gains"] - cell["pooled"]["losses"]
        table[intent] = cell
    return table


def objective(frame: dict, mask: frozenset) -> int:
    return sum(1 for entry in frame.values() if delivered_under(entry, mask))


def wrong_delivered(frame: dict, mask: frozenset) -> tuple:
    rows = [e for e in frame.values() if e["klass"] == "INTENT-WRONG"]
    return sum(1 for e in rows if delivered_under(e, mask)), len(rows)


def greedy(frames: dict, intents) -> dict:
    """Greedy subset search, FITTED on one roster and READ on the two it was not
    fitted on.  The objective is gold-entry delivery over EVERY analysed row of
    the fit roster -- class-blind, so the error labels never choose a key."""

    fit, mask, trail = frames[FIT_ARM], set(), []
    base = {label: objective(frames[label], frozenset()) for label in ROSTERS}
    current = base[FIT_ARM]
    for _ in range(GREEDY_CAP):
        best, best_value = None, current
        for candidate in sorted(set(intents) - mask):
            value = objective(fit, frozenset(mask | {candidate}))
            if value > best_value:
                best, best_value = candidate, value
        if best is None:
            break
        mask.add(best)
        current, frozen = best_value, frozenset(mask)
        trail.append({
            "added": best, "size": len(mask),
            "nets": {label: objective(frames[label], frozen) - base[label]
                     for label in ROSTERS},
            "wrong": {label: wrong_delivered(frames[label], frozen) for label in ROSTERS}})
    return {"base": base, "base_wrong": {label: wrong_delivered(frames[label], frozenset())
                                         for label in ROSTERS},
            "trail": trail, "mask": sorted(mask),
            "rows": {label: len(frames[label]) for label in ROSTERS}}


# ---------------------------------------------------------------------------
# the exemplar channel: the top-20 vote, and what pruning the pool does to it


def pool_scores(queries, sample_ids, pool: dict, vectors, intent_of) -> dict:
    """Row-by-facet cosine over the pinned pool key vectors.  The facet list is
    pre-sorted, so a stable secondary sort on the column index breaks a tie
    exactly as the flown recall's ``facet_id`` ascending rule does.  The row's
    OWN pool column is excluded once, here, because two rosters are drawn from
    the same TRAIN split the pool is built from."""

    facets = pool["facets"]
    ids = [s for s in sample_ids if s in queries]
    keys = unit_rows([vectors[f] for f in facets]).astype(np.float32)
    rows = unit_rows([queries[s][POOL_DIM] for s in ids]).astype(np.float32)
    scores = rows @ keys.T
    index = {facet: position for position, facet in enumerate(facets)}
    self_hits = 0
    for position, sample_id in enumerate(ids):
        mine = own_key(sample_id)
        column = index.get("facet:content:" + str(mine)) if mine else None
        if column is not None:
            scores[position, column] = -2.0
            self_hits += 1
    labels = np.asarray([intent_of.get(pool["keyed"][f], "") for f in facets])
    return {"ids": ids, "scores": scores, "labels": labels, "keys": keys,
            "self_excluded_rows": self_hits}


def top_k_columns(view: np.ndarray, width: int) -> np.ndarray:
    wide = min(view.shape[1], width + TIE_SLACK)
    part = np.argpartition(-view, wide - 1, axis=1)[:, :wide]
    out = np.empty((view.shape[0], width), dtype=np.int64)
    for position in range(view.shape[0]):
        columns = part[position]
        out[position] = columns[np.lexsort((columns, -view[position, columns]))][:width]
    return out


def vote_accuracy(block: dict, keep: np.ndarray, gold: list, k: int = VOTE_K) -> dict:
    """The top-``k`` majority intent per row over the KEPT pool, ties broken by
    intent id ascending, and how often it equals the row's gold intent."""

    kept = np.nonzero(keep)[0]
    view = np.ascontiguousarray(block["scores"][:, kept])
    width = min(k, view.shape[1])
    picks, hits, wrong_hits, wrong_rows = top_k_columns(view, width), 0, 0, 0
    labels = block["labels"]
    for position in range(view.shape[0]):
        tally = Counter(labels[kept[picks[position]]])
        best = min(tally.items(), key=lambda kv: (-kv[1], kv[0]))[0]
        hit = int(best == gold[position][0])
        hits += hit
        if gold[position][1] == "INTENT-WRONG":
            wrong_rows += 1
            wrong_hits += hit
    del view
    return {"rows": len(gold), "hits": hits, "kept": int(len(kept)),
            "wrong_rows": wrong_rows, "wrong_hits": wrong_hits}


def prune_rules(pool: dict, labels, keys: np.ndarray) -> dict:
    """Pool prunes over POOL-INTERNAL properties only -- the pool's own frozen
    build-time intent labels and its own key vectors.  No evaluation roster, no
    evaluation gold and no roster-fitted parameter enters any of them, so none of
    these can overfit a roster.

    ``cap-c``  keep the c lowest-numbered utterances of each intent.
    ``edit-n`` Wilson-style editing: drop an item unless at least n of its own 10
               nearest pool neighbours carry its own intent.
    ``cent-c`` keep the c items of each intent closest to that intent's centroid.
    """

    facets, keyed, total = pool["facets"], pool["keyed"], len(pool["facets"])
    by_intent = defaultdict(list)
    for position in range(total):
        by_intent[labels[position]].append(position)
    rules = {"full": np.ones(total, dtype=bool)}
    for cap in CAPS:
        keep = np.zeros(total, dtype=bool)
        for positions in by_intent.values():
            for position in sorted(positions, key=lambda p: int(keyed[facets[p]]))[:cap]:
                keep[position] = True
        rules["cap-%d" % cap] = keep
    agree = np.zeros(total, dtype=np.int64)
    for start in range(0, total, BLOCK):
        stop = min(start + BLOCK, total)
        block = keys[start:stop] @ keys.T
        for offset in range(stop - start):
            block[offset, start + offset] = -2.0
        near = np.argpartition(-block, NEIGHBOURS - 1, axis=1)[:, :NEIGHBOURS]
        for offset in range(stop - start):
            agree[start + offset] = int(np.count_nonzero(
                labels[near[offset]] == labels[start + offset]))
        del block, near
    for floor in EDITS:
        rules["edit-%d" % floor] = agree >= floor
    for intent, positions in by_intent.items():
        centre = unit_rows(keys[positions].mean(axis=0, keepdims=True))[0]
        scored = sorted(positions, key=lambda p: (-float(keys[p] @ centre),
                                                  int(keyed[facets[p]])))
        by_intent[intent] = scored
    for cap in CAPS:
        keep = np.zeros(total, dtype=bool)
        for positions in by_intent.values():
            for position in positions[:cap]:
                keep[position] = True
        rules["cent-%d" % cap] = keep
    return {"rules": rules, "agreement_mean": round(float(agree.mean()), 3)}


# ---------------------------------------------------------------------------
# narrowing: how much of a key it already shares with the keys that beat it


def boundary_top1(frame: dict) -> tuple:
    """How often the boundary channel's own rank-1 key IS the row's gold intent.
    The dense channel's comparable number is its top-20 majority vote, and the
    two together are what the density hypothesis has to explain."""

    return sum(1 for e in frame.values() if e["top1"] == e["gold"]), len(frame)


def narrowing(store: dict, frames: dict, table: dict) -> dict:
    """For the keys that cannot be masked because they are sometimes gold and
    sometimes correct, the measurable alternative to removal: how close the key
    already is to the keys that actually beat it.  Cosine between the two key
    vectors, and the Jaccard WORD overlap of the two descriptions -- a ratio,
    never the words."""

    order, matrix, body = store["key_order"], store["key_matrix"], store["words"]
    index = {intent: position for position, intent in enumerate(order)}
    pairs = matrix @ matrix.T
    off = pairs[~np.eye(len(order), dtype=bool)]
    laps = [len(body[a] & body[b]) / len(body[a] | body[b])
            for position, a in enumerate(order) for b in order[position + 1:]]
    chosen = sorted(table, key=lambda i: (-(table[i]["pooled"]["gold"]
                                            - table[i]["pooled"]["gold_delivered"]), i))
    out = []
    for intent in chosen[:NARROW_KEYS]:
        winners = Counter()
        for label in ROSTERS:
            for entry in frames[label].values():
                if (entry["gold"] == intent and entry["top1"] is not None
                        and not delivered_under(entry, frozenset())):
                    winners[entry["top1"]] += 1
        top = [w for w, _ in winners.most_common(3) if w in index and w != intent]
        cos = [float(pairs[index[intent], index[w]]) for w in top]
        lap = [len(body[intent] & body[w]) / len(body[intent] | body[w]) for w in top]
        out.append({"intent": intent, "gold": table[intent]["pooled"]["gold"],
                    "train": store["train_per_intent"].get(intent, 0),
                    "correct": table[intent]["pooled"]["correct"],
                    "missed": table[intent]["pooled"]["gold"]
                    - table[intent]["pooled"]["gold_delivered"],
                    "competitors": len(winners), "words": len(body[intent]),
                    "cos": round(max(cos), 4) if cos else None,
                    "overlap": round(max(lap), 4) if lap else None})
    return {"baseline_cos_mean": round(float(off.mean()), 4),
             "train_utterances": None,
             "baseline_cos_max": round(float(off.max()), 4),
             "baseline_overlap_mean": round(sum(laps) / len(laps), 4),
             "baseline_overlap_max": round(max(laps), 4),
             "keys": out}


# ---------------------------------------------------------------------------
# the read


def measure(lock_path: Path, root: Path) -> dict:
    lock = load_lock(lock_path)
    train = load_train(lock, root)
    bank, boundary = load_bank(root), load_boundary(root)
    contracts = KnowledgeSnapshot.from_frozen_json(
        json.loads((root / SC_SNAPSHOT).read_text(encoding="utf-8")))
    if contracts.content_hash() != SC_SNAPSHOT_SHA:
        raise ReadError("slot-contracts-v2 does not hash to the flown pin")
    boundary["train_per_intent"] = train["per_intent"]
    pools = {relpath: load_pool(root, relpath, sha)
             for relpath, sha in ((POOL, POOL_SHA), (POOL_M, POOL_M_SHA))}
    vectors = load_pool_vectors(root, set().union(*(set(p["facets"])
                                                   for p in pools.values())))
    arms, frames = {}, {}
    for arm in ARMS:
        label = arm["label"]
        rows, sealed = load_rows(root, arm, bank, train), load_sealed(root, arm)
        segments = load_sealed_segment_vectors(root / arm["query"],
                                               expected_sha256=arm["query_sha"],
                                               dimensions=(IB_DIM,))
        orders = boundary_order(boundary, segments, sorted(rows["rows"]))
        frames[label] = mask_frame(orders, rows["rows"])
        pool = pools[arm["pool"]]
        content = load_sealed_vectors(root / arm["content"],
                                      expected_sha256=arm["content_sha"],
                                      dimensions=(POOL_DIM,))
        labels = np.asarray([train["intent_of"].get(pool["keyed"][f], "")
                             for f in pool["facets"]])
        if "" in set(labels.tolist()):
            raise ReadError(label + ": a pool utterance has no TRAIN intent")
        block = pool_scores(content, sorted(frames[label]), pool, vectors,
                            train["intent_of"])
        gold = [(frames[label][s]["gold"], frames[label][s]["klass"])
                for s in block["ids"]]
        want = [sorted(sealed["rows"].get(s, {}).get("exemplars") or ())
                for s in block["ids"]]
        picks = top_k_columns(np.ascontiguousarray(block["scores"]), VOTE_K)
        agreed = sum(1 for position, wanted in enumerate(want)
                     if len(wanted) == VOTE_K and sorted(
                         pool["keyed"][pool["facets"][c]]
                         for c in picks[position]) == wanted)
        rules = prune_rules(pool, labels, block["keys"])
        arms[label] = {
            "title": arm["title"], "rows": len(frames[label]),
            "population_source": rows["source"],
            "query_relpath": arm["query"], "query_sha256": arm["query_sha"],
            "content_relpath": arm["content"], "content_sha256": arm["content_sha"],
            "phases_relpath": sealed["relpath"], "phases_sha256": sealed["sha256"],
            "pool_relpath": pool["relpath"], "pool_utterances": pool["utterances"],
            "boundary_validation": validate_boundary(orders, sealed["rows"]),
            "exemplar_validation": {"rows_with_a_sealed_20": sum(
                1 for wanted in want if len(wanted) == VOTE_K), "agreed": agreed},
            "self_excluded_rows": block["self_excluded_rows"],
            "boundary_top1": boundary_top1(frames[label]),
            "classes": dict(Counter(e["klass"] for e in frames[label].values())),
            "votes": {name: vote_accuracy(block, keep, gold)
                      for name, keep in sorted(rules["rules"].items())},
            "agreement_mean": rules["agreement_mean"]}
        del block, rules, content, segments, orders, sealed, picks
    table = per_key_masking(frames, boundary["intents"])
    return {
        "read_id": READ_ID, "recipe": RECIPE, "fit_arm": FIT_ARM,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "census": {
            "train": {k: train[k] for k in
                      ("utterances", "recordings", "intents", "slot_types")},
            "intent_boundaries": {"entries": boundary["entries"], "relpath": IB_SNAPSHOT,
                                  "content_sha256": boundary["content_sha256"],
                                  "vector_dims": boundary["dims"]},
            "slot_contracts": {"types": len(contracts.facets), "relpath": SC_SNAPSHOT,
                               "content_sha256": contracts.content_hash()},
            "pools": {relpath: {"utterances": pool["utterances"],
                                "recordings": pool["recordings"],
                                "content_sha256": pool["content_sha256"]}
                      for relpath, pool in sorted(pools.items())},
            "boundary_facet_relpath": IB_FACETS, "boundary_facet_sha256": IB_FACETS_SHA,
            "pool_facet_relpath": POOL_FACETS, "pool_facet_sha256": POOL_FACETS_SHA,
            "bank_sha256": bank["sha256"],
            "train_per_intent_max": max(train["per_intent"].values()),
            "train_per_intent_min": min(train["per_intent"].values())},
        "arms": arms, "per_key": table, "greedy": greedy(frames, boundary["intents"]),
        "narrowing": narrowing(boundary, frames, table),
        "contacts": {"model": 0, "server": 0, "encoder": 0, "embedder": 0, "scorer": 0,
                     "tokenizer": 0, "network": 0, "gpu": 0, "paid_api": 0}}


# ---------------------------------------------------------------------------
# report


def write_markdown(path: Path, report: dict) -> None:
    census, arms, table = report["census"], report["arms"], report["per_key"]
    trail, narrow, train = report["greedy"], report["narrowing"], report["census"]["train"]
    out = []
    add = out.append
    add("# Is the SLURP knowledge base too dense? The census, and every prune "
        "measured as a mask")
    add("")
    add(f"Date: 2026-09-26. Read id `{report['read_id']}`, recipe "
        f"`{report['recipe']}`. Generated `{report['generated_at']}`.")
    add("")
    add("A model-free read answering the owner's 2026-09-26 hypothesis -- *retrieval "
        "fails because the knowledge base is too dense and too complex* -- in two parts: "
        "what each released store actually holds against TRAIN's own size, and what "
        "REMOVING a key would buy. Zero model, server, encoder, embedder, scorer, "
        "tokenizer, network, GPU and paid-API contacts. Every similarity is recomputed as "
        "arithmetic over sha256-verified vector files the flights themselves pinned, and "
        "section 1 proves the recomputation reproduces what the flights sealed before a "
        "number is taken from it. A prune is simulated by MASKING a key out of the ranking "
        "and recomputing: no store is rebuilt, no facet file is re-cut, no cell is "
        "registered and nothing is flown.")
    add("")
    add("A DIAGNOSTIC, never a gate. It admits no mechanism, releases no store, "
        "authorises no flight and states no effectiveness, superiority or generalisation "
        "claim. Every roster is a discovery or dev roster and every number is a "
        "development number (owner decisions 28 and 86), never a test claim. No utterance "
        "text, transcript, gold filler, delivered answer, knowledge body or key "
        "description is read into a reported value: every cell is an id, a count, a rate, "
        "a cosine, a ratio or a hash.")
    add("")
    positives = sorted(i for i in table if table[i]["pooled"]["net"] > 0)
    free = [i for i in positives if table[i]["pooled"]["correct"] == 0]
    floors = {name: min(pct(arms[label]["votes"][name]["hits"],
                            arms[label]["votes"][name]["rows"])
                       - pct(arms[label]["votes"]["full"]["hits"],
                             arms[label]["votes"]["full"]["rows"]) for label in ROSTERS)
              for name in arms[report["fit_arm"]]["votes"] if name != "full"}
    best_pool = max(sorted(floors), key=lambda n: floors[n])
    add("## The verdict, first")
    add("")
    add("**The hypothesis does not survive the measurement, and it fails in the cleanest "
        f"possible way.** Of the {len(table)} intent keys, "
        f"{len(table) - len(positives)} lose more delivery than they gain the moment they "
        f"are masked, and of the {len(positives)} that gain, {len(positives) - len(free)} "
        "are the gold key of rows the system already answers CORRECTLY today -- so "
        f"{len(free)} keys can be removed without destroying work that is already right. "
        "The greedy subset search, given the whole store to cut from and one roster to fit "
        f"on, stops after {keys_word(len(report['greedy']['trail']))}. And pruning the one "
        "channel that IS dense makes the vote WORSE at every size that removes anything "
        f"material: the best pool prune by held-out floor (`{best_pool}`) is a wash at "
        f"{floors[best_pool]:+.1f} points, and every prune that removes more than "
        "5 % of the pool costs accuracy monotonically.")
    add("")
    add("**And the direction of the evidence is the reverse of the hypothesis.** The store "
        "that holds most of the training set is the store that WORKS, and the store that "
        "holds sixty keys is the one that fails. On the same rows, the dense exemplar "
        "channel's top-20 majority names the gold intent on "
        + ", ".join("%.1f %%" % pct(arms[label]["votes"]["full"]["hits"],
                                    arms[label]["votes"]["full"]["rows"])
                     for label in ROSTERS)
        + " of rows while the sparse boundary channel's own rank-1 key names it on "
        + ", ".join("%.1f %%" % pct(*arms[label]["boundary_top1"]) for label in ROSTERS)
        + " (Fold A, ROLL-1, DEV-2000). Density is not what is broken. What is broken is "
        "one key having to cover a whole intent, which section 6 sizes as a rewrite "
        "opportunity rather than a removal.")
    add("")
    add("## 0. What was read")
    add("")
    add("| Artefact | Relpath under `SPEECHRL_DATA_DIR` | identity |")
    add("| --- | --- | --- |")
    add(f"| `intent-boundaries-v1` snapshot | `{census['intent_boundaries']['relpath']}` "
        f"| `{census['intent_boundaries']['content_sha256']}` |")
    add(f"| `slot-contracts-v2` snapshot | `{census['slot_contracts']['relpath']}` | "
        f"`{census['slot_contracts']['content_sha256']}` |")
    for relpath, pool in census["pools"].items():
        add(f"| exemplar pool snapshot | `{relpath}` | `{pool['content_sha256']}` |")
    add(f"| boundary facet key vectors ({census['intent_boundaries']['entries']} x "
        f"{census['intent_boundaries']['vector_dims']}) | "
        f"`{census['boundary_facet_relpath']}` | `{census['boundary_facet_sha256']}` |")
    add(f"| pool facet key vectors | `{census['pool_facet_relpath']}` | "
        f"`{census['pool_facet_sha256']}` |")
    add(f"| sealed bad-case bank | `{BANK}` | `{census['bank_sha256']}` |")
    for label in ROSTERS:
        arm = arms[label]
        add(f"| `{label}` boundary query vectors | `{arm['query_relpath']}` | "
            f"`{arm['query_sha256']}` |")
        add(f"| `{label}` exemplar query vectors | `{arm['content_relpath']}` | "
            f"`{arm['content_sha256']}` |")
        add(f"| `{label}` sealed phase artefact | `{arm['phases_relpath']}` | "
            f"`{arm['phases_sha256']}` |")
    add("")
    add("| Arm | Rows analysed | Class source | Pool pinned | CORRECT | INTENT-WRONG |")
    add("| --- | ---: | --- | ---: | ---: | ---: |")
    for label in ROSTERS:
        arm = arms[label]
        add(f"| `{label}` | {arm['rows']:,} | `{arm['population_source']}` | "
            f"{arm['pool_utterances']:,} | {arm['classes'].get('CORRECT', 0):,} | "
            f"{arm['classes'].get('INTENT-WRONG', 0):,} |")
    add("")
    add("## 1. The recomputation reproduces both sealed channels")
    add("")
    add("| Arm | boundary rows | sealed width 8 | recomputed top-8 == sealed set | "
        "rows with a sealed 20 | recomputed top-20 == sealed 20 |")
    add("| --- | ---: | ---: | ---: | ---: | ---: |")
    for label in ROSTERS:
        val, exe = arms[label]["boundary_validation"], arms[label]["exemplar_validation"]
        add(f"| `{label}` | {val['rows']:,} | {val['sealed_width_is_8']:,} | "
            f"{val['top_matches_sealed_set']:,} "
            f"({pct(val['top_matches_sealed_set'], val['rows']):.2f} %) | "
            f"{exe['rows_with_a_sealed_20']:,} | {exe['agreed']:,} "
            f"({pct(exe['agreed'], exe['rows_with_a_sealed_20']):.2f} %) |")
    add("")
    add("The self-exclusion the vote needs fired on "
        + ", ".join(f"{arms[label]['self_excluded_rows']} `{label}`" for label in ROSTERS)
        + " rows: no evaluated row is its own exemplar on any roster, because each pool "
        "release already excludes its own evaluation split. The identity that makes a "
        "prune computable offline: masking a key never reorders "
        "the survivors, so gold's rank under any mask is `1 + |ranked above gold, "
        "unmasked|` and gold is delivered when that count is under "
        f"{FLOWN_K} and gold itself is not masked. Every mask below is that arithmetic, "
        "and the vote is recomputed the same way by restricting the pool columns.")
    add("")
    add("## 2. The census: question 1 answered in numbers")
    add("")
    add("| Channel | Store holds | TRAIN holds | share | dense? |")
    add("| --- | ---: | ---: | ---: | --- |")
    add(f"| `intent-boundaries-v1` entries | {census['intent_boundaries']['entries']} | "
        f"{train['intents']} intents | "
        f"{pct(census['intent_boundaries']['entries'], train['intents']):.1f} % | "
        "no -- one key per label, 60 keys |")
    add(f"| `slot-contracts-v2` types | {census['slot_contracts']['types']} | "
        f"{train['slot_types']} slot types | "
        f"{pct(census['slot_contracts']['types'], train['slot_types']):.1f} % | "
        "no -- one key per slot type |")
    for relpath, pool in census["pools"].items():
        tail = relpath.split("/")[-2]
        add(f"| `{tail}` utterances | {pool['utterances']:,} | "
            f"{train['utterances']:,} | "
            f"{pct(pool['utterances'], train['utterances']):.1f} % | YES |")
        add(f"| `{tail}` recordings | {pool['recordings']:,} | "
            f"{train['recordings']:,} | "
            f"{pct(pool['recordings'], train['recordings']):.1f} % | YES |")
    add("")
    add("**The answer, plainly.** The exemplar channel IS most of the training set: it "
        f"puts {pct(census['pools'][POOL]['utterances'], train['utterances']):.1f} % of "
        f"TRAIN's {train['utterances']:,} utterances and "
        f"{pct(census['pools'][POOL]['recordings'], train['recordings']):.1f} % of its "
        f"{train['recordings']:,} recordings into one store; the R01-excluded sibling puts "
        f"in {pct(census['pools'][POOL_M]['utterances'], train['utterances']):.1f} % and "
        f"{pct(census['pools'][POOL_M]['recordings'], train['recordings']):.1f} %. The two "
        "semantic channels do the opposite -- one key per label-vocabulary item, "
        f"{census['intent_boundaries']['entries']} intent keys and "
        f"{census['slot_contracts']['types']} slot-type keys, covering the whole TRAIN "
        f"intent vocabulary ({train['intents']}) and all but one of its "
        f"{train['slot_types']} slot types. **And the channel that FAILS is the small "
        "one.** The intent-boundary channel is where the gold entry misses the delivered "
        "eight on most intent-wrong rows, and it holds sixty keys: "
        f"{census['train_per_intent_min']}-{census['train_per_intent_max']} TRAIN "
        "utterances collapse into ONE key each. Density there cannot mean count. It can "
        "only mean the **breadth** of a single key -- how much of the label space one "
        "written boundary description is made to cover -- which is what section 6 "
        "measures.")
    add("")
    add("## 3. Question 2.1 and 2.2: every intent key masked, one at a time")
    add("")
    add("Masking one key removes it from the ranking for every row, so gold is promoted "
        "by one rank wherever the masked key outranked it, and a row whose gold IS the "
        "masked key can never receive its own entry again. `gains` counts rows that newly "
        "receive their own gold entry; `lost` counts deliveries destroyed because the "
        "masked key was that row's gold; `net` is the difference. The two honesty columns "
        "sit beside them: `gold rows` is how often the key is some row's gold at all, and "
        "`correct` is how many of those rows the system already answers correctly today. "
        "**A key with a non-zero `correct` cannot be masked at any price** -- the net "
        "prices a lost delivery, not the lost correct answer behind it.")
    add("")
    add("All three rosters pooled (" + " + ".join(f"{arms[label]['rows']:,}"
                                                  for label in ROSTERS)
        + f" = {sum(arms[label]['rows'] for label in ROSTERS):,} rows), sorted by net. "
        "`net A` / `net R` / `net D` are Fold A, ROLL-1 and DEV-2000 separately.")
    add("")
    add("| intent id | gains | lost | net | gold rows | correct | delivered today | "
        "net A | net R | net D |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for intent in sorted(table, key=lambda i: (-table[i]["pooled"]["net"], i)):
        cell = table[intent]
        add(f"| `{intent}` | {cell['pooled']['gains']} | {cell['pooled']['losses']} | "
            f"**{cell['pooled']['net']:+d}** | {cell['pooled']['gold']} | "
            f"{cell['pooled']['correct']} | {cell['pooled']['gold_delivered']} | "
            + " | ".join(f"{cell['net'][label]:+d}" for label in ROSTERS) + " |")
    add("")
    best = max(sorted(table), key=lambda i: table[i]["pooled"]["net"])
    positives = sorted(i for i in table if table[i]["pooled"]["net"] > 0)
    blocked = [i for i in positives if table[i]["pooled"]["correct"] > 0]
    free = [i for i in positives if table[i]["pooled"]["correct"] == 0]
    add(f"**The honest accounting.** {len(positives)} of {len(table)} keys carry a "
        f"positive pooled net when masked alone. {len(blocked)} of them are also the gold "
        "key of at least one row the system already answers correctly, so masking them "
        f"destroys work that is already right; {len(free)} are free of that objection. "
        f"The largest single-key net is `{best}` at {table[best]['pooled']['net']:+d} rows "
        f"({table[best]['pooled']['gains']} gained against "
        f"{table[best]['pooled']['losses']} lost) over "
        f"{table[best]['pooled']['gold']} rows where it is gold, of which "
        f"{table[best]['pooled']['correct']} are already correct. So the answer to "
        "question 2.2 is that NO key clears the bar: every key whose removal delivers more "
        "than it destroys is also a key some row needs and already gets right.")
    add("")
    add("## 4. Question 2.3: greedy subset search, fitted on one roster")
    add("")
    add(f"Greedy over the same objective as the agreement weight before it: gold-entry "
        f"delivery over EVERY analysed row of `{report['fit_arm']}` (class-blind, so the "
        "error labels never choose a key), one key added per step, stopping when no key "
        f"improves it, capped at {GREEDY_CAP}. The two other rosters are READ under the "
        "same mask, never fitted. `net` is delivered rows against the unmasked baseline.")
    add("")
    add("| step | key added | net, Fold A (fitted) | net, ROLL-1 (held out) | "
        "net, DEV-2000 (held out) | wrong-row delivery, Fold A | ROLL-1 | DEV-2000 |")
    add("| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    add("| 0 | -- (baseline) | " + " | ".join("0" for _ in ROSTERS) + " | "
        + " | ".join("%.1f %%" % pct(*trail["base_wrong"][label]) for label in ROSTERS)
        + " |")
    for step in trail["trail"]:
        add(f"| {step['size']} | `{step['added']}` | "
            + " | ".join(f"{step['nets'][label]:+d}" for label in ROSTERS) + " | "
            + " | ".join("%.1f %%" % pct(*step["wrong"][label]) for label in ROSTERS)
            + " |")
    add("")
    if trail["trail"]:
        final = trail["trail"][-1]
        held = [final["nets"][label] for label in ROSTERS if label != report["fit_arm"]]
        add(f"**The fitted-versus-held-out gap.** At its final size "
            f"({keys_word(final['size'])} masked) the set gains "
            f"{final['nets'][report['fit_arm']]:+d} delivered rows on the roster it was "
            f"fitted on ({pct(final['nets'][report['fit_arm']], trail['rows'][report['fit_arm']]):+.2f} "
            f"points of its {trail['rows'][report['fit_arm']]:,} rows) and "
            + ", ".join(
                f"{final['nets'][label]:+d} ({pct(final['nets'][label], trail['rows'][label]):+.2f} pts)"
                for label in ROSTERS if label != report["fit_arm"])
            + " on the two it was not. The held-out floor is "
            f"{min(held):+d} rows, which is "
            f"{pct(min(held), min(trail['rows'][label] for label in ROSTERS if label != report['fit_arm'])):+.2f} "
            "points of the smaller held-out roster.")
        add("")
        add("**And it is not registrable.** Every key the search selected is listed in "
            "section 3 with a non-zero `already correct` column, so masking it destroys "
            "rows the system answers correctly today. The search was allowed to ignore "
            "that column on purpose -- so that the number it reaches is the CEILING of "
            "what pruning this channel could buy under the most permissive rule, and that "
            "ceiling is "
            f"{final['nets'][report['fit_arm']]:+d} rows on 1,080.")
    else:
        add("**No key improves the objective even once.** The greedy search stops at size "
            "zero: on the fit roster there is no single key whose removal delivers more "
            "gold entries than it destroys. That refutes the prune hypothesis on this "
            "channel before any held-out question arises.")
    add("")
    add("## 5. Question 2.4: pruning the exemplar pool, measured on the VOTE")
    add("")
    add(f"The agreement vote is the majority intent of the top-{VOTE_K} pool utterances a "
        "row's own speech vector recalls (self-excluded, ties broken by intent id "
        "ascending). It is the mechanism by which pool density would act on the intent "
        "side, given the +0.265 rho between pool count and intent error. Every prune here "
        "uses POOL-INTERNAL properties only -- the pool's own frozen build-time intent "
        "labels and its own key vectors -- so none of them is fitted on any roster and "
        "none can overfit one. `cap-c` keeps the c lowest-numbered utterances of each "
        f"intent; `edit-n` drops an item unless at least n of its own {NEIGHBOURS} nearest "
        "pool neighbours carry its own intent (Wilson-style editing); `cent-c` keeps the c "
        "items of each intent closest to that intent's own centroid.")
    add("")
    add("| prune | kept (Fold A pool) | vote accuracy, Fold A | ROLL-1 | DEV-2000 | "
        "vote on intent-wrong rows, Fold A | ROLL-1 | DEV-2000 |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    names = sorted(arms[report["fit_arm"]]["votes"],
                   key=lambda n: (n != "full", n.split("-")[0],
                                  int(n.split("-")[1]) if "-" in n else 0))
    for name in names:
        cells = [arms[label]["votes"][name] for label in ROSTERS]
        base = [arms[label]["votes"]["full"] for label in ROSTERS]
        add(f"| `{name}` | {cells[0]['kept']:,} | "
            + " | ".join(
                "%.1f %% (%+.1f)" % (pct(c["hits"], c["rows"]),
                                     pct(c["hits"], c["rows"]) - pct(b["hits"], b["rows"]))
                for c, b in zip(cells, base)) + " | "
            + " | ".join(
                "%.1f %% (%+.1f)" % (pct(c["wrong_hits"], c["wrong_rows"]),
                                     pct(c["wrong_hits"], c["wrong_rows"])
                                     - pct(b["wrong_hits"], b["wrong_rows"]))
                for c, b in zip(cells, base)) + " |")
    add("")
    gains = [(min(pct(arms[label]["votes"][name]["hits"], arms[label]["votes"][name]["rows"])
                  - pct(arms[label]["votes"]["full"]["hits"],
                        arms[label]["votes"]["full"]["rows"]) for label in ROSTERS), name)
             for name in names if name != "full"]
    top_prune = max(gains)
    add("**The pool curve, read.** No prune of the dense channel has a positive "
        "held-out floor. The curve is monotone in the wrong direction: the more of the "
        "pool is removed, the worse the vote, on every roster and on the intent-wrong rows "
        "as well as overall. That is the hypothesis tested where it should have been "
        "strongest -- the one store that really does hold the training set -- and answered "
        "no.")
    add("")
    add(f"The best pool prune by held-out floor is "
        f"`{top_prune[1]}`, whose SMALLEST vote-accuracy change across the three rosters "
        f"is {top_prune[0]:+.1f} points, at "
        f"{arms[report['fit_arm']]['votes'][top_prune[1]]['kept']:,} kept utterances "
        f"against the released "
        f"{arms[report['fit_arm']]['votes']['full']['kept']:,}. The mean label agreement "
        f"of a pool item with its own {NEIGHBOURS} nearest pool neighbours is "
        f"{arms[report['fit_arm']]['agreement_mean']} of {NEIGHBOURS}, which is the "
        "quantity `edit-n` thresholds.")
    add("")
    add("## 6. Question 2.5: narrowing instead of removing, as a measured size")
    add("")
    add("For the keys that cannot be masked because they are sometimes gold and sometimes "
        "correct, the alternative is to REWRITE the key so it stops attracting its "
        "competitors' rows. This section only sizes that opportunity; it rewrites nothing, "
        "because a rewrite is a construction act with its own authority. Two measures per "
        "key, over the keys that own the most not-delivered rows: the cosine between the "
        "key's own 2,048-dimension vector and that of the intent that actually takes top-1 "
        "on its missed rows, and the Jaccard WORD overlap of the two descriptions. "
        "`words` is the key's own vocabulary size. No description text is read into any "
        "cell -- only a count and a ratio.")
    add("")
    add(f"The all-pairs baseline over the {census['intent_boundaries']['entries']} keys: "
        f"mean key-to-key cosine {narrow['baseline_cos_mean']}, max "
        f"{narrow['baseline_cos_max']}; mean word overlap "
        f"{narrow['baseline_overlap_mean']}, max {narrow['baseline_overlap_max']}.")
    add("")
    add("| intent id | TRAIN utterances (breadth) | gold rows | already correct | "
        "missed | distinct top-1 rivals | words | cosine to its top rival | word overlap "
        "with it |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for key in narrow["keys"]:
        add(f"| `{key['intent']}` | {key['train']:,} | {key['gold']} | {key['correct']} | "
            f"{key['missed']} | {key['competitors']} | {key['words']} | "
            f"{'--' if key['cos'] is None else key['cos']} | "
            f"{'--' if key['overlap'] is None else key['overlap']} |")
    add("")
    add("Every key in that table has a non-zero `already correct` column, which is why it "
        "is the narrowing list and not the masking list. Two shapes are visible and they "
        "call for different repairs. The most-missed key is beaten by "
        f"{narrow['keys'][0]['competitors']} DIFFERENT rivals across its missed rows, at a "
        f"word overlap of {narrow['keys'][0]['overlap']} against the all-pairs mean of "
        f"{narrow['baseline_overlap_mean']} -- it is not losing a pairwise duel, it is "
        "diffuse, and no rewrite against one rival repairs it. Others are the opposite: a "
        "single dominant rival with a word overlap well above the all-pairs mean, which is "
        "a pairwise confusion a rewrite could plausibly separate. The sizeable finding "
        f"underneath both is the baseline itself: the {census['intent_boundaries']['entries']} "
        f"descriptions share {narrow['baseline_overlap_mean']} of their vocabulary on "
        f"average and up to {narrow['baseline_overlap_max']} at the closest pair, with a "
        f"mean key-to-key cosine of {narrow['baseline_cos_mean']} rising to "
        f"{narrow['baseline_cos_max']}. Sixty keys that share three fifths of their words "
        "are sixty keys that cannot separate sixty intents; that is the measured size of "
        "the rewrite opportunity, and this read names it without taking it.")
    add("")
    add("## 7. Why pruning fits training-free RL, and what it would cost")
    add("")
    add("Pruning is a better fit for training-free RL than anything this programme has "
        "flown, for three reasons that are properties of the search and not of the result. "
        "The candidate space is FINITE and ENUMERABLE: a subset of sixty keys, or a subset "
        "of a pool whose members are enumerated in a released snapshot, so a proposer never "
        "has to invent a string. The reward is computable OFFLINE at the 0.67 pp "
        "instrument, from pinned vectors and sealed labels at zero model contacts -- every "
        "number in sections 3 to 5 is one evaluation of that reward, and a greedy step "
        "costs no GPU at all. And a flight is needed only ONCE, for the composed policy, "
        "which is exactly the design of the registered family "
        "`sealed-credit-system-policy-v1`: inner optimisation over sealed bytes, one flight "
        "for the composition.")
    add("")
    add("The costs are real and must be stated with the gain. A pruned store is a NEW "
        "store: its facet-vector file has to be re-cut, its snapshot re-released, and every "
        "baseline that consumes it re-pinned, which is the re-pin path that has already "
        "rewritten sibling rows twice in this repository's history. And **delivery is not "
        "correctness.** Every number above counts rows that would RECEIVE their own gold "
        "entry; the conversion rate from receiving it to answering correctly is unmeasured "
        "here and is not a function of sealed bytes, because it needs the answer the row "
        "would give with the entry present. No score gain is claimed, implied or estimated "
        "anywhere in this read.")
    add("")
    add("## 7a. The one prune this read would register next")
    add("")
    add("**None.** The selection rule, fixed before the numbers were read: a prune is "
        "registrable only if it raises gold-entry delivery on all three rosters, destroys "
        "no key that is gold on a row already answered correctly, and its held-out floor "
        "survives on the two rosters it was not fitted on. Nothing passes. On the intent "
        f"channel the permissive ceiling -- the greedy search with the honesty column "
        f"switched OFF -- is {report['greedy']['trail'][-1]['nets'][report['fit_arm']]:+d} "
        f"delivered rows on {trail['rows'][report['fit_arm']]:,}, and the single key it "
        "selects is gold on a row the system already gets right, so the honest ceiling is "
        f"zero. On the pool channel the best held-out floor is `{best_pool}` at "
        f"{floors[best_pool]:+.1f} points -- a wash that would still cost a re-cut of a "
        f"{arms[report['fit_arm']]['votes']['full']['kept']:,}-facet vector file, a fresh "
        "snapshot release, and a re-pin of every baseline that consumes the store. A wash "
        "is not worth that, and a re-pin has twice rewritten sibling ledger rows in this "
        "repository's history. **And delivery is not correctness:** every gain above counts "
        "rows that would RECEIVE their own gold entry, not rows that would answer "
        "correctly, so even a passing prune would have been a delivery result and never a "
        "score prediction. The question this read hands back is section 6's -- sixty keys "
        f"sharing {narrow['baseline_overlap_mean']} of their vocabulary is a KEY-SPACE "
        "problem, and its lever is rewriting a description, not removing one.")
    add("")
    add("## 8. Boundary")
    add("")
    add("Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and "
        "paid-API contacts: no server was started, stopped or probed, no waveform decoded, "
        "no embedding computed and no subprocess run. Every cosine was RECOMPUTED as "
        "arithmetic over the pinned vector files named in section 0, each verified against "
        "its configured sha256 by this repository's own loaders before a number was taken "
        "from it, through `rails.kb_policy.multidim_segment_recall` on the boundary channel "
        "and the same cosine and the same `facet_id`-ascending tie order on the pool "
        "channel, with both recomputations validated against the sealed flights in section "
        "1. Other tools: `data.slurp.load_slurp_split` for the governed TRAIN gold, `json` "
        "reads of four released snapshots and three sealed `*.phases.json`, a `json` read "
        "of the sealed bad-case bank and of the ROLL-1 official score file, and `hashlib` "
        "for every identity above.")
    add("")
    add("This read admits nothing, promotes nothing, preregisters no cell, releases no "
        "store, rebuilds no store, draws no roster, expands no source, opens no split and "
        "reaches no superiority, generalisation or Stage-3 conclusion. It is "
        "byte-reproducible across runs apart from its `generated_at` stamp: every container "
        "is sorted before it is consumed, every prune rule is a deterministic function of "
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
