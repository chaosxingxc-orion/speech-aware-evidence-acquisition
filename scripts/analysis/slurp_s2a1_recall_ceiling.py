#!/usr/bin/env python3
"""S2a.1: the offline recall ceiling T of the missing-slot proposal tool (model-free; DESCRIPTIVE).

Design: ``docs/superpowers/specs/2026-09-30-slurp-s2a-missing-slot-proposal-probe-design.md`` (section 1.2, the
tool contract; section 2, "S2a.1 precondition").  The tool ``saea-tool-missing-slot-proposal-v1`` is built here
deterministically and run OFFLINE with the gold slot type supplied on the scoring side.  For one call
``(row, slot_type t)`` it returns at most ``K`` spans of at most ``MAX_TOKENS`` tokens of the row's pinned E5-0
Whisper large-v3 transcript that

1. are contiguous token runs of the canonical transcript (``rails.relisten.canonical_value`` of the whole
   transcript, split -- the canonicaliser E5's 0.7513 containment uses);
2. overlap no transcript position covered by a canonical occurrence of an entity value of the row's delivered
   (draft) column; and
3. score at or above the abstain threshold ``theta`` under the frozen TRAIN type lexicon of ``t``: the maximum
   character-trigram Jaccard similarity between the span and any distinct canonical TRAIN value of type ``t``.

Candidates are ranked by score (descending), then earlier start, then shorter span; identical span strings are
returned once.  Nothing pads the list; an empty result is legal (decision 199).

Choices this driver makes where the spec is under-specified (each is stated in the note):

* **Lexicon source.**  Primary: the TRAIN gold values of slot store v2's own source samples
  (``knowledge/slurp/semantic/slot-contracts-v2`` snapshot ``source_sample_ids``; the spec's "slot store v2's
  train-only build"), minus every utterance (``slurp_id``) that occurs on the Fold A or Fold B roster, so neither
  evaluation fold can look up its own gold.  Sensitivity: all TRAIN minus the Fold A and Fold B utterances.
  Both are asserted to hold no devel or test record.
* **Threshold fitting (Fold B only).**  Target calls: every MISSING gold item (``gold_kinds`` of the E5 driver)
  of the Fold B tuning column (the E5 tuning arm, P-SV-2 AGREE on Fold B) called with its gold type.  Negative
  calls: every (row, type) pair of the closed TRAIN type set that carries no MISSING item of that type on that
  row.  ``theta`` maximises TPR - FPR (Youden J; TPR = gold among the candidates, FPR = a non-empty result),
  over a 0.05 grid; ties go to the lowest theta.  The caps (3 spans, 5 tokens) are the contract's, not fitted.
* **Draft.**  The delivered column of the arm (the Solver's delivered answer), per the brief.
* **Match.**  The gold value counts as returned when its canonical token tuple equals a candidate's.

Read (Fold A): the 70 not-in-supply MISSING items of COMP-1b Fold A are re-derived with S1's own helpers
(``scripts/analysis/slurp_s1_slu_error_taxonomy.py`` and its imports, unchanged) and the run stops unless S1's
counts reproduce (MISSING 189 on 172 rows; not-in-supply 70).  DEV-2000-ADDED has no E5-0 catalog, so A2's 80
items are NOT measured (the driver refuses to create one).

Gold and text discipline: gold enters offline on the scoring side only, through the governed SLURP loader
(``train``).  The test and devel splits are not read.  No utterance text, transcript, gold value, span or model
output is printed or persisted: only ids, counts, rates, slot TYPE names and hashes.  Zero model, server,
tokenizer, encoder, embedder, scorer-subprocess, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -B scripts/analysis/slurp_s2a1_recall_ceiling.py \\
        --data-root "$SPEECHRL_DATA_DIR" --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

READ_ID = "SAEA-SLURP-S2A1-RECALL-CEILING-V1"
RECIPE = "slurp-s2a1-missing-slot-recall-ceiling-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data"
SLOT_STORE_V2 = "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json"
DEV_CATALOG = "prepared/SAEA-SLURP-ASR-TRANSCRIPTS-V1/dev2000-added"

K = 3                 # contract: at most three spans
MAX_TOKENS = 5        # contract: at most five tokens per span
THETA_GRID = tuple(round(0.05 * i, 2) for i in range(20))
UPTAKE_CONV = 32 / 70          # CONV P(correct | newly delivered) = 0.4571 (spec section 2)
UPTAKE_M1 = 133 / (0.5719 * 941)   # M1 delivered-filler conversion 0.2471 (S1 section 3)
NET_BAR = 0.33                 # spec: measured conversion needed for 1.5 pp
NET_BAR_ITEMS = 27 / 80        # spec reading (a): c >= 27 / 80
T_BAR = 0.72                   # spec: T below ~0.72 (0.33 / 0.457) puts (a) out of reach

FOLD_A_ARM = {"label": "comp1b_fold_a", "run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
              "attempt": "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1",
              "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080, "trace": False,
              "title": "COMP-1b on TRAIN Fold A (arm)"}
FOLD_B_ARM = "SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1/attempt-slurp-native-stage3-psv2-fold-b-generation-v1"
S1_EXPECT = {"missing_items": 189, "missing_rows": 172, "not_in_supply": 70}

MISS_KINDS = ("hit", "not_in_transcript", "too_long", "overlaps_draft", "below_threshold", "not_ranked_top_k")


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


# ---------------------------------------------------------------------------- pure parts (unit-tested)


def utterance_of(sample_id: str) -> str:
    """``slurp:<split>:<slurp_id>:<recording>`` -> ``<split>:<slurp_id>`` (the utterance, across recordings)."""
    parts = sample_id.split(":")
    if len(parts) < 4 or parts[0] != "slurp":
        raise ReadError(f"unexpected sample id form {sample_id!r}")
    return f"{parts[1]}:{parts[2]}"


def split_of(sample_id: str) -> str:
    return utterance_of(sample_id).split(":")[0]


def trigrams(text: str) -> frozenset:
    padded = f"  {text} "
    return frozenset(padded[i:i + 3] for i in range(len(padded) - 2))


def jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


class Lexicon:
    """Frozen per-type value lexicon; ``score(t, span)`` = max trigram Jaccard over the type's distinct values."""

    def __init__(self, values_by_type: dict):
        self.values = {t: sorted(set(v for v in vs if v)) for t, vs in values_by_type.items()}
        self.grams = {t: [trigrams(v) for v in vs] for t, vs in self.values.items()}
        self.index = {}
        for t, grams in self.grams.items():
            inv = defaultdict(list)
            for vi, g in enumerate(grams):
                for x in g:
                    inv[x].append(vi)
            self.index[t] = inv
        self._cache: dict = {}

    def types(self) -> list:
        return sorted(self.values)

    def size(self) -> dict:
        return {"types": len(self.values), "distinct_values": sum(len(v) for v in self.values.values())}

    def prime(self, spans, chunk: int = 2000) -> None:
        """Vectorised pre-computation of ``score`` for every type over ``spans`` (scipy sparse; identical
        arithmetic: |A & B| / (|A| + |B| - |A & B|), maximised over the type's values)."""
        import numpy as np
        from scipy import sparse

        spans = sorted(set(spans) - set(getattr(self, "_idx", {})))
        if not spans:
            return
        vocab: dict = {}

        def matrix(gram_sets):
            indptr, indices = [0], []
            for g in gram_sets:
                indices.extend(vocab.setdefault(x, len(vocab)) for x in sorted(g))
                indptr.append(len(indices))
            return indptr, indices

        span_grams = [trigrams(s) for s in spans]
        s_ptr, s_ind = matrix(span_grams)
        type_mats = {}
        for t in self.types():
            v_ptr, v_ind = matrix(self.grams[t])
            type_mats[t] = (v_ptr, v_ind, np.array([len(g) for g in self.grams[t]], dtype=np.float64))
        n_vocab = len(vocab)
        S = sparse.csr_matrix((np.ones(len(s_ind), dtype=np.float64), s_ind, s_ptr), shape=(len(spans), n_vocab))
        s_size = np.array([len(g) for g in span_grams], dtype=np.float64)
        base = len(getattr(self, "_idx", {}))
        self._idx = getattr(self, "_idx", {})
        for i, s in enumerate(spans):
            self._idx[s] = base + i
        self._table = getattr(self, "_table", {})
        for t, (v_ptr, v_ind, v_size) in type_mats.items():
            V = sparse.csr_matrix((np.ones(len(v_ind), dtype=np.float64), v_ind, v_ptr),
                                  shape=(len(v_size), n_vocab)).T.tocsc()
            best = np.zeros(len(spans), dtype=np.float64)
            for lo in range(0, len(spans), chunk):
                inter = (S[lo:lo + chunk] @ V).tocoo()
                if inter.nnz == 0:
                    continue
                j = inter.data / (s_size[lo + inter.row] + v_size[inter.col] - inter.data)
                np.maximum.at(best, lo + inter.row, j)
            self._table[t] = np.concatenate([self._table.get(t, np.zeros(0)), best])
        for t in self.values:
            if t not in self._table:
                self._table[t] = np.zeros(len(self._idx))

    def score(self, t: str, span: str) -> float:
        idx = getattr(self, "_idx", None)
        if idx is not None and span in idx and t in self._table:
            return float(self._table[t][idx[span]])
        key = (t, span)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        grams = self.grams.get(t)
        if not grams:
            self._cache[key] = 0.0
            return 0.0
        s = trigrams(span)
        counts = Counter()
        inv = self.index[t]
        for x in s:
            for vi in inv.get(x, ()):
                counts[vi] += 1
        best = 0.0
        for vi, inter in counts.items():
            j = inter / (len(s) + len(grams[vi]) - inter)
            if j > best:
                best = j
        self._cache[key] = best
        return best


def occurrences(short: tuple, long: list) -> list:
    n = len(short)
    if not n or n > len(long):
        return []
    return [i for i in range(len(long) - n + 1) if tuple(long[i:i + n]) == short]


def covered_positions(canon: list, draft_values: list) -> set:
    """Transcript positions covered by any canonical occurrence of a draft entity value."""
    covered = set()
    for value in draft_values:
        v = tuple(value)
        for i in occurrences(v, canon):
            covered.update(range(i, i + len(v)))
    return covered


def candidate_spans(canon: list, covered: set, max_tokens: int = MAX_TOKENS) -> list:
    """Distinct canonical spans (token tuples) of <= max_tokens tokens not touching a covered position;
    each kept at its earliest start."""
    seen, out = set(), []
    for i in range(len(canon)):
        for n in range(1, max_tokens + 1):
            if i + n > len(canon):
                break
            if any(p in covered for p in range(i, i + n)):
                continue
            span = tuple(canon[i:i + n])
            if span in seen:
                continue
            seen.add(span)
            out.append((i, span))
    return out


def propose(canon: list, covered: set, lexicon: Lexicon, t: str, theta: float, k: int = K,
            max_tokens: int = MAX_TOKENS) -> list:
    """The tool's result: at most k span tuples, ranked by (score desc, start asc, length asc), score >= theta."""
    scored = []
    for start, span in candidate_spans(canon, covered, max_tokens):
        s = lexicon.score(t, " ".join(span))
        if s >= theta and s > 0.0:
            scored.append((-s, start, len(span), span))
    scored.sort()
    return [row[3] for row in scored[:k]]


def classify(gold: tuple, canon: list, covered: set, lexicon: Lexicon, t: str, theta: float, k: int = K,
             max_tokens: int = MAX_TOKENS) -> dict:
    """Outcome of one target call with the gold type: ``hit`` or the first failing stage.

    Stages, in order: not_in_transcript (no canonical occurrence) / too_long (> max_tokens) / overlaps_draft
    (every occurrence touches a draft-covered position) / below_threshold (score < theta) / not_ranked_top_k."""
    occ = occurrences(gold, canon) if gold else []
    if not occ:
        return {"outcome": "not_in_transcript", "rank": None}
    if len(gold) > max_tokens:
        return {"outcome": "too_long", "rank": None}
    if all(any(p in covered for p in range(i, i + len(gold))) for i in occ):
        return {"outcome": "overlaps_draft", "rank": None}
    if lexicon.score(t, " ".join(gold)) < theta or lexicon.score(t, " ".join(gold)) == 0.0:
        return {"outcome": "below_threshold", "rank": None}
    ranked = propose(canon, covered, lexicon, t, theta, k=10 ** 6, max_tokens=max_tokens)
    rank = ranked.index(gold) + 1 if gold in ranked else None
    if rank is None:
        raise ReadError("an eligible gold span is absent from the full ranking")
    return {"outcome": "hit" if rank <= k else "not_ranked_top_k", "rank": rank}


def youden(tp: int, pos: int, fp: int, neg: int) -> float:
    return (tp / pos if pos else 0.0) - (fp / neg if neg else 0.0)


def pick_theta(grid_rows: list) -> dict:
    """Highest Youden J; ties to the lowest theta."""
    best = None
    for row in grid_rows:
        if best is None or row["youden_j"] > best["youden_j"] + 1e-12:
            best = row
    return best


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(centre - half, 4), round(centre + half, 4)]


# ---------------------------------------------------------------------------- loaders


def load_train(lock_path: Path, data_root: Path) -> list:
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split

    return load_slurp_split(load_lock(lock_path), data_root, "train", workers=4)


def build_lexicon(records: list, source_ids: set | None, exclude_utts: set, canon) -> tuple:
    values, used, dropped = defaultdict(list), 0, 0
    for r in records:
        if source_ids is not None and r.sample_id not in source_ids:
            continue
        if split_of(r.sample_id) != "train":
            raise ReadError("a lexicon record is not a TRAIN record")
        if utterance_of(r.sample_id) in exclude_utts:
            dropped += 1
            continue
        used += 1
        for e in r.entities:
            values[e.type].append(" ".join(canon(e.filler)))
    lex = Lexicon(values)
    return lex, {"records_used": used, "records_dropped_fold_overlap": dropped, **lex.size()}


def load_slot_store_sources(data_root: Path) -> tuple:
    path = data_root / SLOT_STORE_V2
    snap = json.loads(path.read_text(encoding="utf-8"))
    ids = set(snap["source_sample_ids"])
    bad = [s for s in ids if split_of(s) != "train"]
    if bad:
        raise ReadError(f"slot store v2 names {len(bad)} non-TRAIN source samples")
    return ids, {"relpath": SLOT_STORE_V2, "sha256": digest(path), "snapshot_sha256": snap.get("snapshot_sha256"),
                 "source_partition_role": snap.get("source_partition_role"), "source_samples": len(ids)}


# ---------------------------------------------------------------------------- Fold A items (S1 helpers)


def fold_a_items(data_root: Path, gold: dict, S1, NG, HR) -> tuple:
    """COMP-1b Fold A MISSING items with S1's supply class, re-derived with S1's own imported helpers."""
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import fold

    ES, GP, W5 = NG.ES, NG.GP, NG.W5
    spec = FOLD_A_ARM
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    m1_values = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    cards = GP.load_contract_bodies(data_root)
    phases = GP.load_phases(data_root, spec)
    directory = phases["directory"]
    outputs = ES.load_outputs(directory, spec["run_id"])
    scores = S1.load_scores(directory, spec["run_id"], spec["scorer"])
    nodes = NG.load_node_states(data_root, spec)
    ids = sorted(scores["rows"])
    pred = {s: outputs["rows"][s]["entities"] for s in ids}
    gold_e = {s: gold[s]["entities"] for s in ids}
    rescorer = HR.Rescorer(gold_e, pred, ES.slu_counts, ids)
    if any(abs(a - b) > 1e-6 for a, b in zip(rescorer.base, scores["totals"])):
        raise ReadError("Fold A in-process totals do not reproduce the sealed official totals")
    arm = {"label": spec["label"], "phases": phases["rows"], "outputs": outputs["rows"], "scores": scores["rows"],
           "nodes": nodes["rows"]}
    derived = NG.derive_arm(arm, gold, ids, pool, m1_values)
    NG.slot_ledger(derived["rows"], derived["items"], ids)   # attaches each item's origin, as in S1 derive()

    def in_cards(sid, value) -> bool:   # S1 derive(), unchanged
        if len(value) < 3:
            return False
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
        return any(pattern.search(cards["bodies"].get(cid, "")) for cid in phases["rows"][sid]["contracts"])

    items = []
    for li in derived["items"]:
        if li["d"] != "MISSING":
            continue
        sid = li["sample_id"]
        value = fold(gold_e[sid][li["gold_index"]].filler)
        ev = HR.evidence_class(li["k_value_printed"], li["k_value_printed_any_type"], in_cards(sid, value), False)
        items.append({"sample_id": sid, "gold_index": li["gold_index"], "type": li["type"],
                      "scenario": gold[sid]["scenario"], "supply": S1.supply_class(ev),
                      "origin": S1.origin_short(li["origin"])})
    got = {"missing_items": len(items), "missing_rows": len({i["sample_id"] for i in items}),
           "not_in_supply": sum(i["supply"] == "none" for i in items)}
    if got != S1_EXPECT:
        raise ReadError(f"S1 Fold A counts do not reproduce: {got} vs {S1_EXPECT}")
    inputs = {"run_id": spec["run_id"], "attempt": spec["attempt"],
              "outputs": [str((directory / outputs["relpath"]).relative_to(data_root)), outputs["sha256"]],
              "scores_sha256": scores["sha256"], "phases_sha256": phases["sha256"]}
    return items, pred, ids, got, inputs


# ---------------------------------------------------------------------------- measurement


def outcome_table(items: list, rows: dict, lex: Lexicon, theta: float, k: int, canon) -> list:
    out = []
    for it in items:
        row = rows[it["sample_id"]]
        g = tuple(canon(it["filler"]))
        res = classify(g, row["canon"], row["covered"], lex, it["type"], theta, k)
        out.append({**{x: it[x] for x in ("sample_id", "gold_index", "type")}, **res})
    return out


def summarise(outcomes: list) -> dict:
    n = len(outcomes)
    c = Counter(o["outcome"] for o in outcomes)
    hits = c.get("hit", 0)
    return {"items": n, "hits": hits, "T": round(hits / n, 4) if n else None, "wilson95": wilson(hits, n),
            "outcomes": {k: c.get(k, 0) for k in MISS_KINDS}}


def ablations(items: list, rows: dict, lex: Lexicon, theta: float, canon) -> dict:
    """T under the contract (top-3 at theta), top-1 at theta, top-3 at theta 0, and no ranker
    (every <= 5-token span: containment within the length limit, with and without the draft filter)."""
    n = len(items)
    contained, contained_len, free_len = 0, 0, 0
    for it in items:
        row = rows[it["sample_id"]]
        g = tuple(canon(it["filler"]))
        occ = occurrences(g, row["canon"]) if g else []
        contained += bool(occ)
        if occ and len(g) <= MAX_TOKENS:
            contained_len += 1
            if any(not any(p in row["covered"] for p in range(i, i + len(g))) for i in occ):
                free_len += 1
    res = {
        "contract_top3_at_theta": summarise(outcome_table(items, rows, lex, theta, K, canon)),
        "top1_at_theta": summarise(outcome_table(items, rows, lex, theta, 1, canon)),
        "top3_no_threshold": summarise(outcome_table(items, rows, lex, 0.0, K, canon)),
        "containment_any_length": {"hits": contained, "T": round(contained / n, 4) if n else None,
                                   "wilson95": wilson(contained, n)},
        "no_ranker_containment_within_5_tokens": {"hits": contained_len, "T": round(contained_len / n, 4) if n else None,
                                                  "wilson95": wilson(contained_len, n)},
        "no_ranker_within_5_tokens_draft_filtered": {"hits": free_len, "T": round(free_len / n, 4) if n else None,
                                                     "wilson95": wilson(free_len, n)},
    }
    return res


def by_type(items: list, outcomes: list) -> list:
    groups = defaultdict(list)
    for o in outcomes:
        groups[o["type"]].append(o)
    rows = []
    for t, os_ in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        s = summarise(os_)
        rows.append({"type": t, **s})
    return rows


def false_candidates(ids: list, rows: dict, lex: Lexicon, theta: float, missing_rows: set, types: list) -> dict:
    """Calls with every closed type on Fold A rows carrying no MISSING item: every returned span is false."""
    calls, nonempty, spans = 0, 0, 0
    per_type = Counter()
    for sid in ids:
        if sid in missing_rows:
            continue
        row = rows[sid]
        for t in types:
            res = propose(row["canon"], row["covered"], lex, t, theta)
            calls += 1
            nonempty += bool(res)
            spans += len(res)
            per_type[t] += bool(res)
    return {"rows": sum(1 for s in ids if s not in missing_rows), "calls": calls,
            "nonempty_rate": round(nonempty / calls, 4) if calls else None,
            "mean_candidates_per_call": round(spans / calls, 4) if calls else None,
            "nonempty_rate_by_type_top10": [[t, round(v / (calls / len(types)), 4)]
                                            for t, v in per_type.most_common(10)]}


def tune(ids_b: list, gold_b: dict, pred_b: dict, rows_b: dict, lex: Lexicon, types: list, canon, E5) -> dict:
    """Youden-J threshold on Fold B (targets = MISSING items with their gold type; negatives = the other
    closed-type calls).  Candidates are computed once per call at theta 0 with scores, then thresholded."""
    targets, negatives = [], []
    for sid in ids_b:
        states, _ = E5.gold_kinds(gold_b[sid], pred_b[sid])
        miss_types = set()
        for gi, g in enumerate(gold_b[sid]):
            if states.get(gi, ("MISSING", None))[0] == "MISSING":
                targets.append((sid, tuple(canon(g.filler)), g.type))
                miss_types.add(g.type)
        for t in types:
            if t not in miss_types:
                negatives.append((sid, t))
    grid = []
    # negative calls: result non-empty at theta iff the best eligible span scores >= theta
    neg_best = []
    for sid, t in negatives:
        row = rows_b[sid]
        best = 0.0
        for _start, span in candidate_spans(row["canon"], row["covered"]):
            s = lex.score(t, " ".join(span))
            if s > best:
                best = s
        neg_best.append(best)
    for theta in THETA_GRID:
        tp = 0
        for sid, g, t in targets:
            row = rows_b[sid]
            if classify(g, row["canon"], row["covered"], lex, t, theta)["outcome"] == "hit":
                tp += 1
        fp = sum(1 for b in neg_best if b > 0.0 and b >= theta)
        grid.append({"theta": theta, "tp": tp, "targets": len(targets), "tpr": round(tp / len(targets), 4),
                     "fp_nonempty": fp, "negatives": len(negatives), "fpr": round(fp / len(negatives), 4),
                     "youden_j": round(youden(tp, len(targets), fp, len(negatives)), 6)})
    chosen = pick_theta(grid)
    return {"targets": len(targets), "negatives": len(negatives), "grid": grid, "chosen": chosen}


def rows_from(ids: list, transcripts: dict, pred: dict, canon) -> dict:
    rows = {}
    for sid in ids:
        tx = transcripts[sid]
        c = tx["canon"] if tx["status"] == "ok" else []
        rows[sid] = {"canon": c, "covered": covered_positions(c, [canon(e.filler) for e in pred[sid]])}
    return rows


def all_windows(rows: dict, max_tokens: int = MAX_TOKENS) -> set:
    return {" ".join(span) for row in rows.values() for _i, span in candidate_spans(row["canon"], set(), max_tokens)}


def verdict(T: float, T_ci: list, T_free: float | None = None) -> dict:
    """c <= T x uptake (spec section 2).  ``T_free`` is the no-ranker ceiling (every <= 5-token span not
    touching the draft), the bound on T for ANY ranker under this contract and this transcript."""
    at_conv = T * UPTAKE_CONV
    at_m1 = T * UPTAKE_M1
    free = {} if T_free is None else {
        "T_perfect_ranker": T_free,
        "c_ceiling_perfect_ranker_at_conv_uptake": round(T_free * UPTAKE_CONV, 4),
        "c_ceiling_perfect_ranker_at_perfect_uptake": T_free,
        "reading_a_reachable_perfect_ranker_at_conv_uptake": T_free * UPTAKE_CONV >= NET_BAR_ITEMS}
    return {**free, "T": T, "T_wilson95": T_ci, "T_bar": T_BAR, "net_bar": NET_BAR, "net_bar_items_27_of_80": round(NET_BAR_ITEMS, 4),
            "uptake_conv": round(UPTAKE_CONV, 4), "uptake_m1": round(UPTAKE_M1, 4),
            "c_ceiling_at_conv_uptake": round(at_conv, 4), "c_ceiling_at_m1_uptake": round(at_m1, 4),
            "items_of_80_at_conv_uptake": round(80 * at_conv, 2),
            "T_needed_at_conv_uptake_for_0_33": round(NET_BAR / UPTAKE_CONV, 4),
            "T_needed_at_conv_uptake_for_27_of_80": round(NET_BAR_ITEMS / UPTAKE_CONV, 4),
            "uptake_needed_at_T_for_27_of_80": round(NET_BAR_ITEMS / T, 4) if T else None,
            "reading_a_reachable_at_conv_uptake": at_conv >= NET_BAR_ITEMS,
            "reading_a_reachable_at_perfect_uptake": T >= NET_BAR_ITEMS}


def build(args) -> dict:
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    data_root = Path(args.data_root)
    E5 = import_path(REPO_ROOT / "scripts/analysis/e5_transcript_consistency_read.py", "e5_transcript_consistency_read")
    S1 = import_path(REPO_ROOT / "scripts/analysis/slurp_s1_slu_error_taxonomy.py", "slurp_s1_slu_error_taxonomy")
    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")
    canon = E5.canon_tokens

    dev_catalog = (data_root / DEV_CATALOG).exists()

    tx_a, cat_a = E5.load_catalog(data_root, "fold-a")
    tx_b, cat_b = E5.load_catalog(data_root, "fold-b")
    ids_a_cat, ids_b_cat = set(tx_a), set(tx_b)
    exclude = {utterance_of(s) for s in ids_a_cat | ids_b_cat}

    records = load_train(Path(args.lock), data_root)
    gold_all = {r.sample_id: {"intent": r.intent, "scenario": r.scenario, "action": r.action,
                              "entities": tuple(NG.ES.SlotEntity(e.type, e.filler) for e in r.entities)}
                for r in records}
    types = sorted({e.type for r in records for e in r.entities})

    store_ids, store_facts = load_slot_store_sources(data_root)
    missing_store = sorted(store_ids - set(gold_all))
    if missing_store:
        raise ReadError(f"{len(missing_store)} slot store v2 source samples are absent from the TRAIN loader")
    store_facts["source_samples_on_fold_a_or_b_utterances"] = sum(utterance_of(s) in exclude for s in store_ids)
    lex_primary, lex_primary_facts = build_lexicon(records, store_ids, exclude, canon)
    lex_full, lex_full_facts = build_lexicon(records, None, exclude, canon)

    # containment stop checks (E5 section 1): Fold A 707 / 941, Fold B 718 / 944
    gold_tuple = {s: tuple(SlotEntity(e.type, e.filler) for e in gold_all[s]["entities"]) for s in gold_all}
    cont_a = E5.gold_span_containment(sorted(ids_a_cat), gold_tuple, tx_a)
    cont_b = E5.gold_span_containment(sorted(ids_b_cat), gold_tuple, tx_b)
    if (cont_a["contained"], cont_a["items"]) != (707, 941) or (cont_b["contained"], cont_b["items"]) != (718, 944):
        raise ReadError("E5 containment does not reproduce (Fold A 707/941, Fold B 718/944)")

    # Fold B tuning column (the E5 tuning arm)
    arm_b = E5.load_arm(data_root, FOLD_B_ARM, ids_b_cat)
    ids_b = sorted(ids_b_cat)
    rows_b = rows_from(ids_b, tx_b, arm_b["pred"], canon)
    tuning = {}
    for name, lex in (("primary", lex_primary), ("full_train", lex_full)):
        lex.prime(all_windows(rows_b))
        tuning[name] = tune(ids_b, gold_tuple, arm_b["pred"], rows_b, lex, types, canon, E5)

    # Fold A read
    items, pred_a, ids_a, s1_counts, fold_a_inputs = fold_a_items(data_root, gold_all, S1, NG, HR)
    if set(ids_a) != ids_a_cat:
        raise ReadError("COMP-1b Fold A roster is not the transcript catalog roster")
    for it in items:
        it["filler"] = gold_all[it["sample_id"]]["entities"][it["gold_index"]].filler   # held in memory only
    pred_a_tuple = {s: tuple(SlotEntity(e.type, e.filler) for e in pred_a[s]) for s in ids_a}
    rows_a = rows_from(ids_a, tx_a, pred_a_tuple, canon)
    nis = [i for i in items if i["supply"] == "none"]
    missing_rows = {i["sample_id"] for i in items}

    reads = {}
    for name, lex in (("primary", lex_primary), ("full_train", lex_full)):
        lex.prime(all_windows(rows_a))
        theta = tuning[name]["chosen"]["theta"]
        abl_nis = ablations(nis, rows_a, lex, theta, canon)
        abl_all = ablations(items, rows_a, lex, theta, canon)
        contract = outcome_table(nis, rows_a, lex, theta, K, canon)
        reads[name] = {
            "theta": theta,
            "not_in_supply_70": abl_nis,
            "all_missing_189": abl_all,
            "by_type_not_in_supply": by_type(nis, contract),
            "by_type_no_threshold_not_in_supply": by_type(nis, outcome_table(nis, rows_a, lex, 0.0, K, canon)),
            "rank_histogram_not_in_supply": dict(sorted(Counter(
                str(o["rank"]) if o["rank"] is not None and o["rank"] <= 10 else (">10" if o["rank"] else "none")
                for o in outcome_table(nis, rows_a, lex, theta, K, canon)).items())),
            "false_candidates_rows_without_missing": false_candidates(ids_a, rows_a, lex, theta, missing_rows, types),
            "items": [{k: o[k] for k in ("sample_id", "gold_index", "type", "outcome", "rank")} for o in contract],
        }
        t = abl_nis["contract_top3_at_theta"]
        reads[name]["verdict"] = verdict(t["T"], t["wilson95"],
                                         abl_nis["no_ranker_within_5_tokens_draft_filtered"]["T"])
    for it in items:
        it.pop("filler", None)

    # cross-check with E5 section 4: comp1b MISSING-and-contained items = 130
    contained_missing = reads["primary"]["all_missing_189"]["containment_any_length"]["hits"]

    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0, "whisper": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "splits_read": ["train"],
        "dev2000_added_catalog_exists": dev_catalog,
        "dev2000_added_note": ("no E5-0 catalog exists for DEV-2000-ADDED; A2's 80 items are not measured "
                               "and no catalog was created" if not dev_catalog else "catalog present (not read)"),
        "contract": {"k": K, "max_tokens": MAX_TOKENS, "theta_grid": list(THETA_GRID),
                     "score": "max character-trigram Jaccard to the distinct canonical TRAIN values of the type",
                     "rank": "score desc, start asc, length asc; identical spans once",
                     "draft": "delivered column; spans touching a canonical occurrence of a delivered value are excluded",
                     "match": "canonical token tuple equality (rails.relisten.canonical_value)"},
        "catalogs": {"fold-a": cat_a, "fold-b": cat_b},
        "containment_check": {"fold_a": [cont_a["contained"], cont_a["items"], cont_a["rate"]],
                              "fold_b": [cont_b["contained"], cont_b["items"], cont_b["rate"]]},
        "slot_store_v2": store_facts,
        "lexicons": {"primary": lex_primary_facts, "full_train": lex_full_facts,
                     "excluded_utterances_fold_a_or_b": len(exclude), "closed_type_set": len(types)},
        "fold_b_tuning_arm": {"spec": FOLD_B_ARM, "outputs": arm_b["outputs"]},
        "tuning": tuning,
        "fold_a_arm": fold_a_inputs, "s1_reproduction": s1_counts,
        "s1_not_in_supply_by_type": dict(Counter(i["type"] for i in nis).most_common()),
        "e5_crosscheck_missing_contained": {"this_read": contained_missing, "e5_section_4_comp1b": 130},
        "reads": reads,
        "drivers": {name: [str(p.relative_to(REPO_ROOT)), digest(p)] for name, p in (
            ("e5_read", REPO_ROOT / "scripts/analysis/e5_transcript_consistency_read.py"),
            ("s1", REPO_ROOT / "scripts/analysis/slurp_s1_slu_error_taxonomy.py"),
            ("node_gain_ledger", REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py"),
            ("consumption_headroom", REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py"))},
    }


# ---------------------------------------------------------------------------- rendering


def md_table(header: list, rows: list) -> str:
    out = ["| " + " | ".join(str(h) for h in header) + " |",
           "| " + " | ".join("---" if i == 0 else "---:" for i in range(len(header))) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(r: dict) -> str:
    out = [f"# {READ_ID} tables", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers "
           "(decisions 28, 86). Counts, rates and slot TYPE names only.", ""]
    out += [f"DEV-2000-ADDED: {r['dev2000_added_note']}.", ""]
    out += ["## Lexicons", "", md_table(["lexicon", "records used", "dropped (fold overlap)", "types", "distinct values"],
                                         [[k, v["records_used"], v["records_dropped_fold_overlap"], v["types"],
                                           v["distinct_values"]] for k, v in r["lexicons"].items() if isinstance(v, dict)]), ""]
    for name, tu in r["tuning"].items():
        out += [f"## Fold B tuning ({name}; chosen theta {tu['chosen']['theta']})", "",
                md_table(["theta", "TP", "targets", "TPR", "FP non-empty", "negatives", "FPR", "J"],
                         [[g["theta"], g["tp"], g["targets"], g["tpr"], g["fp_nonempty"], g["negatives"], g["fpr"],
                           g["youden_j"]] for g in tu["grid"]]), ""]
    for name, rd in r["reads"].items():
        for pop in ("not_in_supply_70", "all_missing_189"):
            a = rd[pop]
            rows = []
            for k in ("contract_top3_at_theta", "top1_at_theta", "top3_no_threshold"):
                rows.append([k, a[k]["hits"], a[k]["items"], a[k]["T"], a[k]["wilson95"]]
                            + [a[k]["outcomes"][m] for m in MISS_KINDS[1:]])
            for k in ("containment_any_length", "no_ranker_containment_within_5_tokens",
                      "no_ranker_within_5_tokens_draft_filtered"):
                rows.append([k, a[k]["hits"], a["contract_top3_at_theta"]["items"], a[k]["T"], a[k]["wilson95"]]
                            + ["" for _ in MISS_KINDS[1:]])
            out += [f"## T, Fold A {pop} ({name} lexicon, theta {rd['theta']})", "",
                    md_table(["setting", "hits", "items", "T", "Wilson95"] + list(MISS_KINDS[1:]), rows), ""]
        out += [f"### Per slot type, not-in-supply, contract ({name})", "",
                md_table(["type", "items", "hits", "T"] + list(MISS_KINDS[1:]),
                         [[t["type"], t["items"], t["hits"], t["T"]] + [t["outcomes"][m] for m in MISS_KINDS[1:]]
                          for t in rd["by_type_not_in_supply"]]), ""]
        out += [f"### Rank of the gold span, not-in-supply ({name})", "",
                md_table(["rank", "items"], [[k, v] for k, v in rd["rank_histogram_not_in_supply"].items()]), ""]
        fc = rd["false_candidates_rows_without_missing"]
        out += [f"### False candidates on Fold A rows without a MISSING item ({name})", "",
                md_table(["rows", "calls", "non-empty rate", "mean candidates per call"],
                         [[fc["rows"], fc["calls"], fc["nonempty_rate"], fc["mean_candidates_per_call"]]]), ""]
        v = rd["verdict"]
        out += [f"### Verdict arithmetic ({name})", "",
                md_table(["quantity", "value"], [[k, json.dumps(val)] for k, val in v.items()]), ""]
    out += ["## Checks", "", f"S1 reproduction: `{json.dumps(r['s1_reproduction'])}`; containment "
            f"`{json.dumps(r['containment_check'])}`; E5 cross-check `{json.dumps(r['e5_crosscheck_missing_contained'])}`", ""]
    return "\n".join(out) + "\n"


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"|Generated `[^`]*`', "", text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--check", action="store_true", help="re-derive and compare with the written outputs")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.data_root) / ANALYSIS_DIR
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n", "tables.md": render(report)}
    if args.check:
        bad = [n for n, t in texts.items() if strip_time((out_dir / n).read_text(encoding="utf-8")) != strip_time(t)]
        print("check:", "IDENTICAL apart from generated_at" if not bad else f"DIFFERS in {bad}")
        return 1 if bad else 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    manifest = {n: hashlib.sha256(strip_time(t).encode("utf-8")).hexdigest() for n, t in sorted(texts.items())}
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                                 encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
