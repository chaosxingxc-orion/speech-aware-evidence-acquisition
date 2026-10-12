#!/usr/bin/env python3
"""Decision 265 coverage pre-read, TRAIN Fold B, offline (spec 2026-10-11 section 2.1).

Question. Would credit-driven selective knowledge augmentation from TRAIN (outside the evaluation
folds) put the gold knowledge entry in front of the model on more Fold B bad-case rows, and what
delivered SLU-F1 / intent effect does that predict through the exchange rates on file? The spec
(``docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md``
section 2.1) makes this read a precondition of registering the iteration-1 column: the composite must
predict at least +1.5 pp SLU-F1 (decision 192).

Source column. The delivering ``lock`` column of the sealed R6-P1 flight
(``SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1``): the review-off COMP-1b module graph on lock v2.2
(v4g delivery), TRAIN Fold B ``SLURP-EVO-FOLD-B-V2`` (1,080 rows), official scorer
``slurp-slu-official-train``. Its delivered answer is the run-level ``outputs.jsonl`` (rule I7), and the
in-process scoring must reproduce every sealed per-sample official field or the read stops.

What it computes.

1. Bad-case inventory. Every gold-side entity error item (official exact matcher, then the node-ledger
   kinds) and every intent-wrong row, by failure class x slot type x scenario x coverage mode:
   (a) in the row's delivered supply (exemplars print the (type, value), the value under another type,
   or a delivered slot card names it; for intent, the gold intent's boundary entry is in the delivered
   block of 8); (b) in a released store but not delivered to the row; (c) in TRAIN outside the
   evaluation folds but in no store; (d) nowhere. The coverage note's five modes map onto these
   ((i) absent = (c)+(d), (ii) not retrieved = (b), (iii) budget-excluded = 0 by construction, (iv)+(v)
   residual = (a)). Each item also carries whether its gold span is contained in the row's E5-0
   transcript (the S2a.1 reachability test); unreachable items are excluded from every operator gain.
2. Operator (a), slot-card value-list supply: cells (gold scenario x slot type) chosen on one half of
   Fold B by the count of reachable (b)+(c) MISSING items; on the other half the cell's top-N TRAIN
   values (TRAIN minus Fold A, Fold B, R01, R01C) are appended to the delivered card of that type on rows
   whose Perception note names an intent of that scenario. Counts newly supplied MISSING items, the
   extra tokens per row (chars / 3.634, the measured M1 exemplar-block ratio) against the realised
   Solver prompt, and the predicted SLU-F1 at conversion 30 / 45 / 60 % and at the two measured
   analogues (W4 list form 0.052, M1 printing 0.2471).
3. Operator (b), exemplar re-weighting: the speech-keyed exemplar top-20 recall and the COMP-1b
   Perception block (centroid cosine + 1.0 x self-excluded exemplar-intent vote, top 8) are recomputed
   exactly from the pinned vectors and checked against the sealed ranking and the sealed agreement table.
   Variants are pool SELECTIONS (keep-quota per intent, attractor thinning chosen from the fit half),
   because TRAIN minus the two folds is already inside the pool (proved here: expansion material = 0).
   For each variant: intent-wrong rows whose gold boundary newly enters the block, currently-correct rows
   whose gold boundary leaves it, MISSING items newly printed, exact items losing their print; predicted
   intent via the CONV conversion 32 / 70 and SLU via the M1 printing rate x the exchange rate.
4. Operator (c), per-scenario anti-pattern guards over the delivered (post-v4g) column: type-by-intent,
   type-by-scenario and entity-rate guards from TRAIN statistics (the v4g statistics pool), the rule per
   scenario chosen on one half and applied to the other (both ways), scored EXACTLY with the official
   arithmetic and a paired whole-utterance cluster bootstrap (10,000 draws, seed 20260915).
5. The composite with overlap removed, against the 1.5 pp bar, and a per-scenario table.

Gold discipline. Gold enters only offline, on the scoring side, through the governed TRAIN loader
(``data.slurp.load_slurp_split``), for Fold B rows and for the construction statistics of TRAIN outside
the folds. The devel and test splits are not read. Bad cases choose only WHICH cells / strata are
edited, as aggregate counts; content comes from TRAIN outside the folds. No utterance text, transcript,
gold value, filler, card body or model output is printed or persisted: ids, slot TYPE names, scenario
and intent names, counts, rates, pp and hashes only.

Contacts: zero model, server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU. Cosines
are arithmetic over pinned, sha256-verified vector files.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_tfrl_coverage_preread.py \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --lock /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
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

READ_ID = "SAEA-SLURP-TFRL-COVERAGE-PREREAD-V1"
RECIPE = "slurp-tfrl-coverage-preread-fold-b-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")

COLUMN = {"label": "r6-lock", "title": "R6-P1 delivering lock column (lock v2.2, review-off COMP-1b, v4g)",
          "run_id": "SAEA-SLURP-STAGE3-NX-R6-PERCEPTION-FOLD-B-V1",
          "attempt": "attempt-slurp-native-stage3-nx-r6-perception-fold-b-generation-v1",
          "scorer": "slurp-slu-official-train", "split": "train", "rows": 1080}
FOLD_B_SPLIT = "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a"
ROSTERS = {"fold-a": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
           "fold-b": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
           "r01": "docs/receipts/rosters/slurp-stage3-construction-r01.json",
           "r01c": "docs/receipts/rosters/slurp-stage3-construction-r01c.json"}
#: the lock's train-exemplars pin (content hash) and the legal construction population
#: (TRAIN minus Fold A, Fold B, R01, R01C: the v4g statistics pool)
POOL = ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json",
        "4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9")
LEGAL = ("knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
         "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63")
EX_FACETS = ("vectors/slurp-kus3/facet-vectors.jsonl",
             "5dfe75231c12f2624913988e4643c51b74856465bdbd108358b4f371dacffc1e")
EX_QUERY = ("vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.jsonl",
            "573a8a37a63d790d6b849c11676b9463de28c92eeb92ab3e99177181a947c67f")
IB_QUERY = ("vectors/slurp-intent-boundaries-train-fold-b-1080-v1/query-vectors-speech-segments.jsonl",
            "83c5da6190fb2a65edf98a8f9ef35ff2cb310eb4e4b94eba9e04f9eedce9f299")
CENTROID = ("prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl",
            "16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532")
AGREEMENT = ("prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl",
             "06990a86d20469c668ac4231990b49e5926d4771c9af8fbb13ae634b3ec21911")
EX_K, IB_K, W_AGREE = 20, 8, 1.0
EX_DIM, IB_DIM = "content", "intent-boundary"
SLOT_TOKENS, COMPLETION_CEILING = 24576, 512

BOOT_DRAWS, BOOT_SEED = 10_000, 20260915
TARGET_PP = 1.5                      # decision 192
CONV_INTENT = (32, 70)               # CONV probe: newly delivered gold boundary -> gold intent
CONV_GRID = (0.30, 0.45, 0.60)       # brief: 45 % with 30 / 60 % sensitivity
W4_LIST_RATE = 0.052                 # W4 card list form: 5 of 97 listed items moved (headroom note section 2)
M1_PRINT_RATE = 0.2471               # M1 printing conversion (W5 note)
CHARS_PER_TOKEN = 3.634              # measured on the flown M1 exemplar block (W5 driver constant)
LIST_OVERHEAD_TOKENS = 8             # a "values:" label and separators per appended list (estimate)
A_LIST_N = (8, 16, 32)
A_PRIMARY_N = 16
A_MIN_CELL_CREDIT = 2
B_THIN_C = (2, 3, 5)
B_THIN_F = (0.75, 0.5, 0.25)
B_QUOTA = (60, 120, 240)
C_TI = (0.02, 0.05, 0.10, 0.20)
C_ST = (0.02, 0.05, 0.10)
C_EE = (0.15, 0.20, 0.30, 0.40, 0.50)
C_MIN_EDITED_ROWS = 2
GOLD_SIDE_KINDS = ("MISSING", "WRONG-TYPE", "BOUNDARY", "NEAR", "WRONG-VALUE", "FORMAT")
MODES = ("a", "b", "c", "d")
MODE_NAMES = {"a": "(a) in the delivered supply", "b": "(b) in a store, not delivered",
              "c": "(c) in TRAIN outside the folds, in no store", "d": "(d) nowhere"}


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
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def utt(sample_id: str) -> str:
    return ":".join(str(sample_id).split(":")[:3])


def half_of(utterance_id: str) -> int:
    """Fixed utterance-hash half (0 / 1): both recordings of an utterance land in one half."""
    return int(hashlib.sha256(str(utterance_id).encode("utf-8")).hexdigest(), 16) % 2


def pct(num, den):
    return None if not den else round(100.0 * num / den, 2)


def scen(intent):
    return None if intent is None else str(intent).split("_", 1)[0]


def wilson(k: int, n: int, z: float = 1.959964) -> list:
    if n == 0:
        return [None, None]
    p = k / n
    centre = p + z * z / (2 * n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    den = 1 + z * z / n
    return [round((centre - half) / den, 4), round((centre + half) / den, 4)]


# ---------------------------------------------------------------------------
# pooled arithmetic over the official count fields (word tp/fp/fn, char tp/fp/fn, span, intent)


def totals_of(matrix):
    s = matrix.sum(axis=0)
    return float(s[0] + s[3]), float(s[1] + s[4]), float(s[2] + s[5])


def f1(tp, fp, fn):
    den = 2 * tp + fp + fn
    return 0.0 if den == 0 else 100.0 * 2 * tp / den


def rate_missing(T) -> float:
    """pp of pooled SLU-F1 for one recovered MISSING entity (one word + one char unit)."""
    tp, fp, fn = T
    return f1(tp + 2, fp, fn - 2) - f1(tp, fp, fn)


def rate_exact_lost(T) -> float:
    tp, fp, fn = T
    return f1(tp - 2, fp, fn + 2) - f1(tp, fp, fn)


# ---------------------------------------------------------------------------
# loaders


def load_roster_utts(relpath: str) -> set:
    document = json.loads((REPO_ROOT / relpath).read_text(encoding="utf-8"))
    return {utt(item["sample_id"]) for item in document["items"]}


def load_matrix(path: Path, sha: str, dim: str):
    import numpy as np
    if digest(path) != sha:
        raise ReadError(f"{path.name}: sha256 differs from its pin")
    ids, rows = [], []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            ids.append(str(record["id"]))
            rows.append(np.asarray(record["vectors"][dim], dtype=np.float64))
    return ids, np.vstack(rows)


def load_agreement(path: Path, sha: str) -> dict:
    if digest(path) != sha:
        raise ReadError("the sealed agreement table differs from its pin")
    out = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                record = json.loads(line)
                out[str(record["id"])] = {k.split("intent-boundary:", 1)[-1]: float(v)
                                          for k, v in record["scores"].items()}
    return out


def solver_prompt_tokens(trace: Path, ids: set) -> dict:
    """sample id -> max realised Solver prompt tokens over the row's Solver contacts (server usage
    fields; no text kept)."""
    role_of, out = {}, defaultdict(int)
    with trace.open("r", encoding="utf-8") as handle:
        for line in handle:
            head = line[:160]
            if '"MODEL_REQUEST"' in head:
                record = json.loads(line)
                payload = (record.get("payload") or {}).get("payload") or {}
                role = str(payload.get("key_representation_id") or "").rsplit(":", 1)[-1]
                sid = payload.get("sample_id")
                if role == "solver" and sid in ids:
                    role_of[record["record_id"].split("/")[0]] = sid
            elif '"MODEL_RESPONSE"' in head:
                record = json.loads(line)
                if record.get("channel") != "MODEL_RESPONSE":
                    continue
                sid = role_of.get(record["record_id"].split("/")[0])
                if sid is None:
                    continue
                usage = (record.get("payload") or {}).get("usage") or {}
                out[sid] = max(out[sid], int(usage.get("prompt_tokens") or 0))
    return dict(out)


# ---------------------------------------------------------------------------
# retrieval replay


class Retrieval:
    """The exemplar recall (top-20, pure cosine, facet id ascending tie-break) and the COMP-1b
    Perception block (centroid cosine + w_agree x exemplar-intent vote share, top 8)."""

    def __init__(self, ids, qmat, pool_keys, fmat, task_target, ib_cos):
        import numpy as np
        qn = qmat / np.linalg.norm(qmat, axis=1, keepdims=True)
        fn = fmat / np.linalg.norm(fmat, axis=1, keepdims=True)
        self.cos = qn @ fn.T                       # rows x pool values
        self.ids = ids
        self.keys = pool_keys                      # sorted lexicographically (the tie-break order)
        self.target = task_target                  # per pool column: intent
        self.ib_cos = ib_cos                       # sid -> {intent: centroid cosine}

    def topk(self, keep_mask=None, k: int = EX_K):
        import numpy as np
        scores = self.cos if keep_mask is None else np.where(keep_mask[None, :], self.cos, -np.inf)
        part = np.argpartition(-scores, k + 5, axis=1)[:, :k + 5]
        out = []
        for r in range(scores.shape[0]):
            cand = part[r]
            cand = sorted(cand.tolist(), key=lambda j: (-scores[r, j], j))
            # exact boundary: include every column tied with the k-th score that argpartition may have cut
            kth = scores[r, cand[k - 1]]
            ties = np.nonzero(scores[r] == kth)[0].tolist()
            cand = sorted(set(cand) | set(ties), key=lambda j: (-scores[r, j], j))
            out.append(cand[:k])
        return out

    def shares(self, cols) -> dict:
        votes = Counter(self.target[j] for j in cols)
        total = sum(votes.values())
        return {i: votes[i] / total for i in votes} if total else {}

    def block(self, sid, share, RD) -> list:
        return RD.blend(self.ib_cos[sid], share, W_AGREE)


# ---------------------------------------------------------------------------
# build


def build(args) -> dict:
    import numpy as np
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items, fold
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_segment_vectors, load_sealed_vectors)
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    V4S = import_path(REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py", "slurp_nx_postproc_v4_search")
    E5 = import_path(REPO_ROOT / "scripts/analysis/e5_transcript_consistency_read.py",
                     "e5_transcript_consistency_read")
    ES, GP, W5 = NG.ES, NG.GP, NG.W5
    RD = ES.RD
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    checks: dict = {}

    # ---- rosters, gold, the legal construction population -----------------
    roster_utts = {k: load_roster_utts(v) for k, v in ROSTERS.items()}
    gold = V4S.load_gold(lock, data_root, "train")
    delivered = V4S.load_delivered(data_root, COLUMN)
    ids = sorted(delivered["rows"])
    if len(ids) != COLUMN["rows"] or any(s not in gold for s in ids):
        raise ReadError("the column is not the complete 1,080-row TRAIN roster")
    if {utt(s) for s in ids} != roster_utts["fold-b"]:
        raise ReadError("the column's utterances are not the Fold B roster")
    run_manifest = json.loads((data_root / "runs" / COLUMN["run_id"] / COLUMN["attempt"]
                               / f"{COLUMN['run_id']}.run-manifest.json").read_text(encoding="utf-8"))
    if run_manifest["split"]["identity_hash"] != FOLD_B_SPLIT:
        raise ReadError("the column's split identity is not Fold B v2")
    forbidden = roster_utts["fold-a"] | roster_utts["fold-b"] | roster_utts["r01"] | roster_utts["r01c"]
    train_utts = {utt(s) for s in gold}
    legal_utts = train_utts - forbidden
    if legal_utts & roster_utts["fold-b"] or len(train_utts) != 11514:
        raise ReadError("the legal construction population is not disjoint from Fold B")
    first_rec = {}
    for sid in sorted(gold):
        first_rec.setdefault(utt(sid), sid)
    legal_type = defaultdict(Counter)            # type -> folded value -> utterances
    legal_cell = defaultdict(Counter)            # (scenario, type) -> folded value -> utterances
    for u in sorted(legal_utts):
        g = gold[first_rec[u]]
        for t, v in sorted({(e.type, fold(e.filler)) for e in g["entities"]}):
            legal_type[t][v] += 1
            legal_cell[(g["scenario"], t)][v] += 1

    # ---- the base matrix, proved against the sealed official per-sample fields -------
    base = np.zeros((len(ids), 10), dtype=np.float64)
    mismatches = 0
    for k, sid in enumerate(ids):
        row = delivered["rows"][sid]
        vec = V4S.score_vector(gold[sid], row["scenario"], row["action"], row["entities"])
        if any(abs(a - b) > 1e-9 for a, b in zip(vec, V4S.sealed_vector(delivered["sealed"][sid]))):
            mismatches += 1
        base[k] = np.array(vec)
    if mismatches:
        raise ReadError(f"{mismatches} rows: in-process scoring does not reproduce the sealed official fields")
    base_pooled = V4S.pooled(base)
    if abs(base_pooled["slu_f1_pp"] - delivered["official"]["slu_f1_pp"]) > 1e-6:
        raise ReadError("in-process pooled SLU-F1 does not reproduce the official aggregate")
    T = totals_of(base)
    r_miss, r_exact = rate_missing(T), rate_exact_lost(T)
    checks["rows_reproduced_exactly"] = len(ids)
    index = {sid: k for k, sid in enumerate(ids)}

    # ---- the sealed supply of every row ------------------------------------
    phases = GP.load_phases(data_root, COLUMN)
    if sorted(phases["rows"]) != ids:
        raise ReadError("the phase artefact does not cover the roster")
    m1 = W5.snapshot_values(data_root, W5.M1_SNAPSHOT)
    m1_snap_ok = W5.M1_SNAPSHOT["sha256"] == POOL[1]
    if not m1_snap_ok:
        raise ReadError("the W5 M1 pin is not the lock's train-exemplars pin")
    printed_of = {vid.split("value:", 1)[-1]: frozenset(W5.printed_pairs(v.content)) for vid, v in m1.items()}
    target_of = {vid.split("value:", 1)[-1]: v.task_target for vid, v in m1.items()}
    chars_of = {vid.split("value:", 1)[-1]: len(v.content or "") for vid, v in m1.items()}
    value_utts = {vid.split("value:", 1)[-1]: {utt(s) for s in v.source_sample_ids} for vid, v in m1.items()}
    facet_of = {}
    for vid, v in m1.items():
        if len(v.associated_facet_ids) != 1:
            raise ReadError("an exemplar value is not bound to exactly one facet")
        facet_of[vid.split("value:", 1)[-1]] = v.associated_facet_ids[0]
    pool_utts = set().union(*value_utts.values())
    legal_keys = {k for k, us in value_utts.items() if not (us & (roster_utts["r01"] | roster_utts["r01c"]))}
    expansion = {
        "train_utterances": len(train_utts), "lock_pool_utterances": len(pool_utts),
        "fold_a_utterances": len(roster_utts["fold-a"]), "fold_b_utterances": len(roster_utts["fold-b"]),
        "pool_overlap_fold_a": len(pool_utts & roster_utts["fold-a"]),
        "pool_overlap_fold_b": len(pool_utts & roster_utts["fold-b"]),
        "train_minus_pool_minus_folds": len(train_utts - pool_utts - roster_utts["fold-a"] - roster_utts["fold-b"]),
        "legal_utterances": len(legal_utts), "legal_utterances_outside_pool": len(legal_utts - pool_utts),
        "pool_values_from_r01_or_r01c": len(m1) - len(legal_keys),
    }
    if expansion["pool_overlap_fold_b"] or expansion["pool_overlap_fold_a"]:
        raise ReadError("the lock pool intersects an evaluation fold")
    store_pairs = set().union(*printed_of.values())
    legal_store_pairs = set().union(*(printed_of[k] for k in legal_keys))
    cards = GP.load_contract_bodies(data_root)
    card_bodies = cards["bodies"]
    _card_re = {}

    def card_names(body: str, value: str) -> bool:
        if len(value) < 3:
            return False
        pattern = _card_re.get(value)
        if pattern is None:
            pattern = _card_re[value] = re.compile(r"(?<![a-z0-9])" + re.escape(value) + r"(?![a-z0-9])")
        return bool(pattern.search(body))

    any_card_value = {}

    def in_any_card(value: str) -> bool:
        if value not in any_card_value:
            any_card_value[value] = any(card_names(b, value) for b in card_bodies.values())
        return any_card_value[value]

    # ---- transcript reachability (E5-0 catalog, re-hashed by its loader) -----
    transcripts, catalog_facts = E5.load_catalog(data_root, "fold-b")

    def reachable(sid, filler) -> str:
        tx = transcripts.get(sid)
        if not (tx and tx["status"] == "ok"):
            return "no-transcript"
        return "contained" if E5.contiguous(E5.canon_tokens(filler), tx["canon"]) else "not-contained"

    # ---- per-row facts and the item inventory ------------------------------
    rows, items = {}, []
    for sid in ids:
        g, d, ph = gold[sid], delivered["rows"][sid], phases["rows"][sid]
        gi = f"{g['scenario']}_{g['action']}"
        d_intent = f"{d['scenario']}_{d['action']}" if d["parsed"] and d["scenario"] is not None else None
        intent_ok = bool(base[index[sid], 9] >= 1.0)
        printed = set().union(*(printed_of.get(k, frozenset()) for k in ph["ex_rendered"]))
        row_cards = [card_bodies.get(c, "") for c in ph["contracts"]]
        its = entity_items(tuple(g["entities"]), tuple(d["entities"]) if d["parsed"] else ())
        kinds = Counter(it["kind"] for it in its)
        if not intent_ok:
            rclass = "INTENT-WRONG"
        elif not its:
            rclass = "CORRECT"
        elif all(it["kind"] == "SPURIOUS" for it in its):
            rclass = "EMPTY-GOLD-FILL" if not g["entities"] else "ENTITY-FP-ONLY"
        elif all(it["kind"] == "MISSING" for it in its):
            rclass = "ENTITY-FN-ONLY"
        else:
            rclass = "ENTITY-MIXED"
        rows[sid] = {
            "utt": utt(sid), "half": half_of(utt(sid)), "scenario": g["scenario"],
            "gold_intent": gi, "d_intent": d_intent, "intent_ok": intent_ok, "class": rclass,
            "block": list(ph["boundary"]), "gold_in_block": gi in ph["boundary"],
            "block_rank": ph["boundary"].index(gi) + 1 if gi in ph["boundary"] else None,
            "perception": list(ph["perception"]), "contracts": list(ph["contracts"]),
            "ex": list(ph["ex_rendered"]), "printed": printed,
            "gold_intent_exemplars": sum(1 for k in ph["ex_rendered"] if target_of.get(k) == gi),
            "kinds": dict(kinds), "gold_empty": not g["entities"],
        }
        exact_gold = set(range(len(g["entities"]))) - {it["gold_index"] for it in its if it["gold_index"] is not None}
        for gidx in sorted(exact_gold):
            e = g["entities"][gidx]
            items.append({"sid": sid, "kind": "EXACT", "type": e.type, "value": fold(e.filler),
                          "filler": e.filler, "gold_index": gidx})
        for it in its:
            if it["gold_index"] is None:
                e = d["entities"][it["pred_index"]]
                items.append({"sid": sid, "kind": "SPURIOUS", "type": e.type, "pred_index": it["pred_index"]})
                continue
            e = g["entities"][it["gold_index"]]
            items.append({"sid": sid, "kind": it["kind"], "type": e.type, "value": fold(e.filler),
                          "filler": e.filler, "gold_index": it["gold_index"]})
    for it in items:
        if "value" not in it:
            continue
        r = rows[it["sid"]]
        t, v = it["type"], it["value"]
        e1 = (t, v) in r["printed"]
        e2 = any(pv == v for _pt, pv in r["printed"])
        e3 = any(card_names(b, v) for b in (card_bodies.get(c, "") for c in r["contracts"]))
        if e1 or e2 or e3:
            mode = "a"
            sub = "E1" if e1 else "E2" if e2 else "E3"
        elif (t, v) in store_pairs or in_any_card(v):
            mode = "b"
            sub = ("legal-exemplar" if (t, v) in legal_store_pairs else
                   "r01-exemplar-only" if (t, v) in store_pairs else "card-only")
        elif v in legal_type.get(t, ()):
            mode, sub = "c", "legal-list"
        else:
            mode, sub = "d", "none"
        it["mode"], it["sub"] = mode, sub
        it["reach"] = reachable(it["sid"], it.pop("filler"))
        it["card_delivered"] = t in r["contracts"]
    checks["items"] = dict(Counter(i["kind"] for i in items))

    # ---- inventory tables --------------------------------------------------
    gold_side = [i for i in items if i["kind"] in GOLD_SIDE_KINDS]

    def mode_counts(sub):
        c = Counter(i["mode"] for i in sub)
        return {m: c.get(m, 0) for m in MODES}

    inv_class = {}
    for kind in GOLD_SIDE_KINDS:
        sub = [i for i in gold_side if i["kind"] == kind]
        inv_class[kind] = {"items": len(sub), "modes": mode_counts(sub),
                           "reachable_in_transcript": sum(i["reach"] == "contained" for i in sub),
                           "reachable_by_mode": {m: sum(i["reach"] == "contained" and i["mode"] == m for i in sub)
                                                 for m in MODES},
                           "on_intent_wrong_rows": sum(not rows[i["sid"]]["intent_ok"] for i in sub),
                           "sub": dict(Counter(f"{i['mode']}:{i['sub']}" for i in sub))}
    inv_type = {}
    for t in sorted({i["type"] for i in gold_side}):
        sub = [i for i in gold_side if i["type"] == t]
        miss = [i for i in sub if i["kind"] == "MISSING"]
        inv_type[t] = {"items": len(sub), "modes": mode_counts(sub), "missing": len(miss),
                       "missing_modes": mode_counts(miss),
                       "missing_bc_reachable": sum(i["mode"] in ("b", "c") and i["reach"] == "contained" for i in miss),
                       "spurious": sum(1 for i in items if i["kind"] == "SPURIOUS" and i["type"] == t)}
    inv_scen = {}
    for s in sorted({r["scenario"] for r in rows.values()}):
        srows = [sid for sid in ids if rows[sid]["scenario"] == s]
        sub = [i for i in gold_side if rows[i["sid"]]["scenario"] == s]
        miss = [i for i in sub if i["kind"] == "MISSING"]
        wrong = [sid for sid in srows if not rows[sid]["intent_ok"]]
        inv_scen[s] = {"rows": len(srows), "intent_wrong": len(wrong),
                       "intent_wrong_gold_in_block": sum(rows[x]["gold_in_block"] for x in wrong),
                       "classes": dict(Counter(rows[x]["class"] for x in srows)),
                       "gold_side_items": len(sub), "modes": mode_counts(sub), "missing": len(miss),
                       "missing_modes": mode_counts(miss),
                       "spurious": sum(1 for i in items if i["kind"] == "SPURIOUS" and rows[i["sid"]]["scenario"] == s)}
    wrong_rows = [sid for sid in ids if not rows[sid]["intent_ok"]]
    right_rows = [sid for sid in ids if rows[sid]["intent_ok"]]
    inv_intent = {
        "intent_wrong_rows": len(wrong_rows),
        "a_gold_boundary_in_block": sum(rows[s]["gold_in_block"] for s in wrong_rows),
        "b_in_store_not_in_block": sum(not rows[s]["gold_in_block"] for s in wrong_rows),
        "c_or_d": 0,
        "gold_intent_exemplar_in_top20": sum(rows[s]["gold_intent_exemplars"] > 0 for s in wrong_rows),
        "correct_rows": len(right_rows),
        "correct_rows_gold_in_block": sum(rows[s]["gold_in_block"] for s in right_rows),
        "p_correct_given_in_block": pct(sum(rows[s]["intent_ok"] for s in ids if rows[s]["gold_in_block"]),
                                        sum(rows[s]["gold_in_block"] for s in ids)),
        "p_correct_given_off_block": pct(sum(rows[s]["intent_ok"] for s in ids if not rows[s]["gold_in_block"]),
                                         sum(not rows[s]["gold_in_block"] for s in ids)),
        "confusions_top": Counter(f"{rows[s]['gold_intent']} -> {rows[s]['d_intent']}" for s in wrong_rows).most_common(15),
    }
    p_in = sum(rows[s]["intent_ok"] for s in ids if rows[s]["gold_in_block"]) / max(1, sum(rows[s]["gold_in_block"] for s in ids))
    p_off = sum(rows[s]["intent_ok"] for s in ids if not rows[s]["gold_in_block"]) / max(1, sum(not rows[s]["gold_in_block"] for s in ids))
    loss_rate = p_in - p_off
    pp_row = 100.0 / len(ids)

    # ---- retrieval replay ---------------------------------------------------
    pool_keys = sorted(m1.keys(), key=lambda vid: vid)    # value ids "value:<n>"
    pool_keys = [vid.split("value:", 1)[-1] for vid in pool_keys]
    pool_keys.sort()                                      # string order == the flown facet-id tie-break
    fac_ids, fmat_all = load_matrix(data_root / EX_FACETS[0], EX_FACETS[1], EX_DIM)
    frow = {f: k for k, f in enumerate(fac_ids)}
    missing_facets = [k for k in pool_keys if facet_of[k] not in frow]
    if missing_facets:
        raise ReadError(f"{len(missing_facets)} pool facets have no vector")
    fmat = fmat_all[[frow[facet_of[k]] for k in pool_keys]]
    del fmat_all
    q_ids, qmat_all = load_matrix(data_root / EX_QUERY[0], EX_QUERY[1], EX_DIM)
    qrow = {q: k for k, q in enumerate(q_ids)}
    if any(s not in qrow for s in ids):
        raise ReadError("a roster row has no exemplar query vector")
    qmat = qmat_all[[qrow[s] for s in ids]]
    del qmat_all
    store = RD.load_store(data_root)
    centroid = load_sealed_vectors(data_root / CENTROID[0], expected_sha256=CENTROID[1], dimensions=(IB_DIM,))
    if set(centroid) != set(store["facet_vectors"]):
        raise ReadError("centroid key file does not cover the boundary store's facets")
    ib_queries = load_sealed_segment_vectors(data_root / IB_QUERY[0], expected_sha256=IB_QUERY[1],
                                             dimensions=(IB_DIM,))
    ib_cos = RD.recompute(dict(store, facet_vectors=centroid), ib_queries, ids)
    if set(ib_cos) != set(ids):
        raise ReadError("a roster row has no boundary query vector")
    targets = [target_of[k] for k in pool_keys]
    R = Retrieval(ids, qmat, pool_keys, fmat, targets, ib_cos)
    del fmat, qmat
    agreement = load_agreement(data_root / AGREEMENT[0], AGREEMENT[1])
    base_top = R.topk()
    rep = Counter()
    base_share, base_block = {}, {}
    for r_i, sid in enumerate(ids):
        cols = base_top[r_i]
        keys = [pool_keys[j] for j in cols]
        rep["exemplar_top20_order_equals_sealed_rank"] += int(keys == phases["rows"][sid]["ex_rank"])
        rep["exemplar_top20_set_equals_sealed_set"] += int(set(keys) == set(phases["rows"][sid]["ex_rendered"]))
        rep["self_excluded_values"] += sum(1 for k in keys if rows[sid]["utt"] in value_utts[k])
        share = R.shares(cols)
        rep["vote_equals_sealed_agreement"] += int(
            set(share) == set(agreement.get(sid, {})) and all(abs(share[i] - agreement[sid][i]) < 1e-12 for i in share))
        full = R.block(sid, share, RD)
        blk = full[:IB_K]
        rows[sid]["full_rank"] = full.index(rows[sid]["gold_intent"]) + 1 if rows[sid]["gold_intent"] in full else None
        rep["block_order_equals_sealed_block"] += int(blk == rows[sid]["block"])
        rep["block_set_equals_sealed_block"] += int(set(blk) == set(rows[sid]["block"]))
        base_share[sid], base_block[sid] = share, blk
    checks["replay"] = dict(sorted(rep.items()))
    if rep["exemplar_top20_set_equals_sealed_set"] < len(ids) or rep["block_set_equals_sealed_block"] < len(ids):
        raise ReadError(f"the retrieval replay does not reproduce the sealed supply: {dict(rep)}")
    off = sorted(rows[s]["full_rank"] or 999 for s in wrong_rows if not rows[s]["gold_in_block"])
    inv_intent["off_block_gold_rank"] = {
        "rows": len(off), "median": off[len(off) // 2] if off else None,
        "9-16": sum(9 <= x <= 16 for x in off), "17-30": sum(17 <= x <= 30 for x in off),
        "31-60": sum(31 <= x <= 60 for x in off), "unranked": sum(x == 999 for x in off)}
    inv_intent["off_block_by_gold_intent"] = Counter(
        rows[s]["gold_intent"] for s in wrong_rows if not rows[s]["gold_in_block"]).most_common(10)

    # ---- operator (a): slot-card value-list supply ---------------------------
    def a_cells(fit_ids, gran="scenario-type") -> dict:
        """Credit table cells: (gold scenario, slot type) or ("*", slot type), kept at credit >= 2."""
        credit = Counter()
        for i in gold_side:
            if i["kind"] == "MISSING" and i["sid"] in fit_ids and i["mode"] in ("b", "c") and i["reach"] == "contained":
                credit[(rows[i["sid"]]["scenario"] if gran == "scenario-type" else "*", i["type"])] += 1
        return {cell: n for cell, n in credit.items() if n >= A_MIN_CELL_CREDIT}

    def a_lists(cells, n_values) -> dict:
        out = {}
        for cell in cells:
            source = legal_type.get(cell[1], Counter()) if cell[0] == "*" else legal_cell.get(cell, Counter())
            ranked = sorted(source.items(), key=lambda kv: (-kv[1], kv[0]))
            out[cell] = [v for v, _ in ranked[:n_values]]
        return out

    def a_apply(cells, lists, apply_ids) -> dict:
        """Newly supplied items on ``apply_ids`` and the supply cost; gold-free trigger."""
        trig = defaultdict(list)        # sid -> [cells triggered]
        for sid in apply_ids:
            r = rows[sid]
            pscen = {scen(i) for i in r["perception"]}
            for (s, t) in cells:
                if t in r["contracts"] and (s == "*" or s in pscen):
                    trig[sid].append((s, t))
        new_missing, new_other, new_unreach, fail_trigger, exposure, empty_exposure = [], [], 0, 0, 0, 0
        for i in gold_side:
            if i["sid"] not in apply_ids or i["mode"] not in ("b", "c"):
                continue
            cand = [c for c in trig.get(i["sid"], ()) if c[1] == i["type"]]
            hit = any(i["value"] in lists[c] for c in cand)
            if not hit:
                if i["kind"] == "MISSING" and i["reach"] == "contained" and any(c[1] == i["type"] for c in cells) \
                        and not cand:
                    fail_trigger += 1
                continue
            if i["reach"] != "contained":
                new_unreach += 1
            elif i["kind"] == "MISSING":
                new_missing.append(i)
            else:
                new_other.append(i)
        tokens = {}
        for sid, cs in trig.items():
            tok = 0
            gtypes = {e.type for e in gold[sid]["entities"]}
            for c in cs:
                chars = sum(len(v) + 2 for v in lists[c])
                tok += math.ceil(chars / CHARS_PER_TOKEN) + LIST_OVERHEAD_TOKENS
                exposure += int(c[1] not in gtypes)
                empty_exposure += int(not gtypes)
            tokens[sid] = tok
        return {"new_missing": new_missing, "new_other": new_other, "new_unreachable": new_unreach,
                "trigger_failed_reachable_missing": fail_trigger, "rows_triggered": len(trig),
                "cell_triggers": sum(len(v) for v in trig.values()), "exposure_type_absent_from_gold": exposure,
                "exposure_on_empty_gold_rows": empty_exposure, "tokens": tokens}

    halves = {h: {sid for sid in ids if rows[sid]["half"] == h} for h in (0, 1)}
    all_ids = set(ids)

    def summarise_a(res, n_rows) -> dict:
        nm = len(res["new_missing"])
        toks = list(res["tokens"].values())
        return {
            "newly_supplied_missing": nm, "newly_supplied_other_kinds": len(res["new_other"]),
            "other_kinds": dict(Counter(i["kind"] for i in res["new_other"])),
            "newly_supplied_unreachable_excluded": res["new_unreachable"],
            "reachable_missing_in_selected_types_not_triggered": res["trigger_failed_reachable_missing"],
            "rows_triggered": res["rows_triggered"], "cell_triggers": res["cell_triggers"],
            "exposure_type_absent_from_gold": res["exposure_type_absent_from_gold"],
            "exposure_on_empty_gold_rows": res["exposure_on_empty_gold_rows"],
            "extra_tokens_per_triggered_row_mean": round(sum(toks) / len(toks), 1) if toks else 0.0,
            "extra_tokens_per_triggered_row_max": max(toks) if toks else 0,
            "extra_tokens_per_row_over_roster": round(sum(toks) / n_rows, 2),
            "predicted_pp": {**{f"conv_{c:.2f}": round(nm * c * r_miss, 4) for c in CONV_GRID},
                             "conv_w4_list_0.052": round(nm * W4_LIST_RATE * r_miss, 4),
                             "conv_m1_print_0.2471": round(nm * M1_PRINT_RATE * r_miss, 4)},
            "predicted_pp_other_kinds_at_045_repair_rate": round(
                len(res["new_other"]) * 0.45 * (f1(T[0] + 2, T[1] - 2, T[2] - 2) - f1(*T)), 4),
        }

    op_a = {"cell_min_credit": A_MIN_CELL_CREDIT, "list_sizes": list(A_LIST_N), "primary_n": A_PRIMARY_N,
            "granularities": ["scenario-type", "type"]}
    a_new_items, a_best = set(), None     # the larger cross-fitted granularity at N = 16 feeds the composite
    for gran in ("scenario-type", "type"):
        for n_values in A_LIST_N:
            entry = {}
            cross = {"new_missing": [], "new_other": [], "new_unreachable": 0, "trigger_failed_reachable_missing": 0,
                     "rows_triggered": 0, "cell_triggers": 0, "exposure_type_absent_from_gold": 0,
                     "exposure_on_empty_gold_rows": 0, "tokens": {}}
            for fit_h in (0, 1):
                cells = a_cells(halves[fit_h], gran)
                res = a_apply(cells, a_lists(cells, n_values), halves[1 - fit_h])
                entry[f"fit_half{fit_h}_apply_half{1 - fit_h}"] = {
                    "cells": len(cells), "cells_by_type": dict(Counter(t for (_s, t) in cells)),
                    **summarise_a(res, len(halves[1 - fit_h]))}
                for k in ("new_missing", "new_other"):
                    cross[k] += res[k]
                for k in ("new_unreachable", "trigger_failed_reachable_missing", "rows_triggered", "cell_triggers",
                          "exposure_type_absent_from_gold", "exposure_on_empty_gold_rows"):
                    cross[k] += res[k]
                cross["tokens"].update(res["tokens"])
            entry["cross_fitted"] = summarise_a(cross, len(ids))
            entry["cross_fitted"]["new_missing_by_type"] = dict(Counter(i["type"] for i in cross["new_missing"]))
            cells_all = a_cells(all_ids, gran)
            res_in = a_apply(cells_all, a_lists(cells_all, n_values), all_ids)
            entry["in_sample_reference"] = {"cells": len(cells_all), **summarise_a(res_in, len(ids))}
            op_a[f"{gran}-n{n_values}"] = entry
            if n_values == A_PRIMARY_N and (a_best is None or len(cross["new_missing"]) > len(a_new_items)):
                a_new_items = {(i["sid"], i["gold_index"]) for i in cross["new_missing"]}
                a_best = gran
                op_a["composite_input"] = {"granularity": gran, "n": n_values,
                                           "new_missing_by_scenario": dict(Counter(
                                               rows[i["sid"]]["scenario"] for i in cross["new_missing"]))}
    # reference without credit selection: every slot type's card carries its top-N TRAIN values
    every = {("*", t) for t in legal_type}
    for n_values in A_LIST_N:
        res = a_apply(every, a_lists(every, n_values), all_ids)
        op_a[f"every-card-n{n_values}"] = summarise_a(res, len(ids))
    bc_miss = [i for i in gold_side if i["kind"] == "MISSING" and i["mode"] in ("b", "c")]
    op_a["ceiling"] = {
        "missing_bc": len(bc_miss),
        "missing_bc_reachable": sum(i["reach"] == "contained" for i in bc_miss),
        "missing_bc_reachable_card_delivered": sum(i["reach"] == "contained" and i["card_delivered"] for i in bc_miss),
        "missing_bc_reachable_in_legal_cell_list_any_n": sum(
            i["reach"] == "contained" and i["value"] in legal_cell.get((rows[i["sid"]]["scenario"], i["type"]), ())
            for i in bc_miss),
        "oracle_all_reachable_bc_missing_pp_at_045": round(
            sum(i["reach"] == "contained" for i in bc_miss) * 0.45 * r_miss, 4),
    }
    prompt = solver_prompt_tokens(data_root / "runs" / COLUMN["run_id"] / COLUMN["attempt"]
                                  / f"{COLUMN['run_id']}.trace.jsonl", set(ids))
    pt = sorted(prompt.values())
    op_a["budget"] = {
        "slot_tokens": SLOT_TOKENS, "completion_ceiling": COMPLETION_CEILING,
        "rows_with_solver_usage": len(pt),
        "solver_prompt_tokens_max_per_row": {"median": pt[len(pt) // 2] if pt else None, "max": pt[-1] if pt else None},
        "headroom_tokens_min": SLOT_TOKENS - COMPLETION_CEILING - (pt[-1] if pt else 0),
    }

    # ---- operator (b): exemplar re-weighting by pool selection ----------------
    rank_of_key = {k: h for h, k in enumerate(sorted(pool_keys, key=lambda k: hashlib.sha256(
        f"value:{k}".encode("utf-8")).hexdigest()))}
    by_intent = defaultdict(list)
    for j, k in enumerate(pool_keys):
        by_intent[targets[j]].append(j)
    for intent in by_intent:
        by_intent[intent].sort(key=lambda j: rank_of_key[pool_keys[j]])

    def mask_thin(intents, frac) -> "np.ndarray":
        keep = np.ones(len(pool_keys), dtype=bool)
        for intent in intents:
            js = by_intent.get(intent, [])
            n_keep = int(math.floor(frac * len(js) + 1e-9))
            for j in js[n_keep:]:
                keep[j] = False
        return keep

    def mask_quota(q) -> "np.ndarray":
        keep = np.ones(len(pool_keys), dtype=bool)
        for intent, js in by_intent.items():
            for j in js[q:]:
                keep[j] = False
        return keep

    miss_items = defaultdict(list)
    exact_items = defaultdict(list)
    for i in gold_side:
        if i["kind"] == "MISSING" and i["reach"] == "contained":
            miss_items[i["sid"]].append(i)
    for i in items:
        if i["kind"] == "EXACT":
            exact_items[i["sid"]].append(i)

    def b_eval(keep) -> dict:
        top = R.topk(keep)
        per = {}
        for r_i, sid in enumerate(ids):
            cols = top[r_i]
            share = R.shares(cols)
            blk = R.block(sid, share, RD)[:IB_K]
            gi = rows[sid]["gold_intent"]
            keys = [pool_keys[j] for j in cols]
            printed = set().union(*(printed_of[k] for k in keys))
            old = rows[sid]["printed"]
            per[sid] = {
                "in_block": gi in blk, "rank": blk.index(gi) + 1 if gi in blk else None,
                "new_print_missing": [(x["sid"], x["gold_index"]) for x in miss_items.get(sid, ())
                                      if (x["type"], x["value"]) in printed and (x["type"], x["value"]) not in old],
                "lost_print_exact": sum(1 for x in exact_items.get(sid, ())
                                        if (x["type"], x["value"]) in old and (x["type"], x["value"]) not in printed),
                "chars_delta": sum(chars_of[k] for k in keys) - sum(chars_of[k] for k in rows[sid]["ex"]),
                "changed": set(keys) != set(rows[sid]["ex"]),
            }
        return per

    def b_score(per, apply_ids) -> dict:
        gain = sum(1 for s in apply_ids if not rows[s]["intent_ok"] and not rows[s]["gold_in_block"] and per[s]["in_block"])
        lost_correct = sum(1 for s in apply_ids if rows[s]["intent_ok"] and rows[s]["gold_in_block"] and not per[s]["in_block"])
        lost_wrong = sum(1 for s in apply_ids if not rows[s]["intent_ok"] and rows[s]["gold_in_block"] and not per[s]["in_block"])
        demoted_rank1 = sum(1 for s in apply_ids if rows[s]["intent_ok"] and rows[s]["block_rank"] == 1
                            and per[s]["in_block"] and per[s]["rank"] != 1)
        newp = sum(len(per[s]["new_print_missing"]) for s in apply_ids)
        lostp = sum(per[s]["lost_print_exact"] for s in apply_ids)
        k, n = CONV_INTENT
        intent_pp = (gain * k / n - lost_correct * loss_rate) * pp_row
        slu_pp = newp * M1_PRINT_RATE * r_miss + lostp * M1_PRINT_RATE * r_exact
        return {"gold_newly_in_block_on_intent_wrong": gain, "gold_lost_from_block_on_correct": lost_correct,
                "gold_lost_from_block_on_intent_wrong": lost_wrong,
                "correct_rank1_demoted_inside_block": demoted_rank1,
                "rows_supply_changed": sum(per[s]["changed"] for s in apply_ids),
                "missing_newly_printed_reachable": newp, "exact_items_losing_print": lostp,
                "exemplar_tokens_delta_per_row_mean": round(
                    sum(per[s]["chars_delta"] for s in apply_ids) / CHARS_PER_TOKEN / max(1, len(apply_ids)), 2),
                "predicted_intent_pp": round(intent_pp, 4),
                "predicted_intent_pp_conv_ci": [round((gain * w - lost_correct * loss_rate) * pp_row, 4)
                                                for w in wilson(k, n)],
                "predicted_slu_pp_m1_print": round(slu_pp, 4)}

    def attractors(fit_ids, c) -> list:
        cnt = Counter(rows[s]["d_intent"] for s in fit_ids if not rows[s]["intent_ok"] and rows[s]["d_intent"])
        return sorted(i for i, n in cnt.items() if n >= c)

    variants = {}
    per_cache = {}
    for q in B_QUOTA:
        per_cache[f"quota{q}"] = b_eval(mask_quota(q))
    for c in B_THIN_C:
        for fit_h in (0, 1, "all"):
            fit_ids = all_ids if fit_h == "all" else halves[fit_h]
            att = attractors(fit_ids, c)
            for f in B_THIN_F:
                per_cache[f"thin-c{c}-f{f}-fit{fit_h}"] = (att, b_eval(mask_thin(att, f)))
    # selection: on each half, the variant with the highest predicted intent pp on that half
    def b_candidates(fit_h):
        out = {}
        for q in B_QUOTA:
            out[f"quota{q}"] = per_cache[f"quota{q}"]
        for c in B_THIN_C:
            for f in B_THIN_F:
                out[f"thin-c{c}-f{f}"] = per_cache[f"thin-c{c}-f{f}-fit{fit_h}"][1]
        return out

    op_b = {"expansion_material": expansion, "loss_rate_off_block": round(loss_rate, 4),
            "p_correct_in_block": round(p_in, 4), "p_correct_off_block": round(p_off, 4),
            "conv_intent": CONV_INTENT, "conv_intent_wilson95": wilson(*CONV_INTENT),
            "grid_in_sample": {}, "cross_fit": {}}
    for name, per in b_candidates("all").items():
        op_b["grid_in_sample"][name] = b_score(per, all_ids)
    for q in B_QUOTA:
        pass
    for c in B_THIN_C:
        op_b.setdefault("attractors_in_sample", {})[f"c{c}"] = per_cache[f"thin-c{c}-f0.5-fitall"][0]
    b_cross_per = {}
    b_chosen = {}
    for fit_h in (0, 1):
        cands = b_candidates(fit_h)
        scored = {name: b_score(per, halves[fit_h]) for name, per in cands.items()}
        best = max(sorted(scored), key=lambda nm: scored[nm]["predicted_intent_pp"])
        if scored[best]["predicted_intent_pp"] <= 0:
            best = None
        b_chosen[fit_h] = best
        apply_ids = halves[1 - fit_h]
        if best is None:
            op_b["cross_fit"][f"fit_half{fit_h}"] = {"chosen": None}
            continue
        op_b["cross_fit"][f"fit_half{fit_h}"] = {"chosen": best, "fit_score": scored[best],
                                                  "apply_score": b_score(cands[best], apply_ids)}
        for s in apply_ids:
            b_cross_per[s] = cands[best][s]
    if b_cross_per:
        cf_ids = set(b_cross_per)
        op_b["cross_fit"]["combined"] = b_score({**{s: {"in_block": rows[s]["gold_in_block"], "rank": rows[s]["block_rank"],
                                                        "new_print_missing": [], "lost_print_exact": 0, "chars_delta": 0,
                                                        "changed": False} for s in ids}, **b_cross_per}, all_ids)
        op_b["cross_fit"]["combined"]["rows_with_a_chosen_variant"] = len(cf_ids)
    b_new_print = {x for s, p in b_cross_per.items() for x in p["new_print_missing"]}
    b_gain_rows = {s for s, p in b_cross_per.items()
                   if not rows[s]["intent_ok"] and not rows[s]["gold_in_block"] and p["in_block"]}
    b_loss_rows = {s for s, p in b_cross_per.items()
                   if rows[s]["intent_ok"] and rows[s]["gold_in_block"] and not p["in_block"]}

    # ---- operator (c): per-scenario anti-pattern guards (exact, cross-fitted) ----
    legal_pool = GP.load_exemplar_pool(data_root, LEGAL[0])
    if legal_pool["content_sha256"] != LEGAL[1]:
        raise ReadError("the TRAIN statistics pool is not the pinned v4g pool")
    stats = V4S.TrainStats(legal_pool["values"])
    scen_n, scen_type = Counter(), defaultdict(Counter)
    for value in legal_pool["values"].values():
        s = scen(value["intent"])
        scen_n[s] += 1
        for t in value["fillers"]:
            scen_type[s][t] += 1
    del legal_pool

    def guard(rule, intent, entities):
        if intent is None or stats.intent_n.get(intent, 0) == 0 or not entities:
            return list(entities)
        fam, theta = rule
        if fam == "ti":
            return [e for e in entities if stats.type_share(intent, e.type) >= theta]
        if fam == "st":
            s = scen(intent)
            return [e for e in entities if scen_type[s][e.type] / max(1, scen_n[s]) >= theta]
        if fam == "ee":
            return [] if stats.entity_rate(intent) < theta else list(entities)
        raise ReadError(rule)

    rules = [("ti", t) for t in C_TI] + [("st", t) for t in C_ST] + [("ee", t) for t in C_EE]
    edited_cache = {}

    def edited_rows(rule, row_ids) -> dict:
        out = {}
        for sid in row_ids:
            key = (rule, sid)
            if key not in edited_cache:
                d = delivered["rows"][sid]
                if not d["parsed"] or not d["entities"]:
                    edited_cache[key] = None
                else:
                    new = guard(rule, rows[sid]["d_intent"], d["entities"])
                    edited_cache[key] = None if new == list(d["entities"]) else new
            if edited_cache[key] is not None:
                out[sid] = edited_cache[key]
        return out

    def matrix_with(edits: dict):
        m = base.copy()
        for sid, ents in edits.items():
            d = delivered["rows"][sid]
            m[index[sid]] = np.array(V4S.score_vector(gold[sid], d["scenario"], d["action"], ents))
        return m

    def delta_of(edits) -> float:
        return V4S.pooled(matrix_with(edits))["slu_f1_pp"] - base_pooled["slu_f1_pp"]

    def fit_scenario_rules(fit_ids) -> dict:
        chosen = {}
        for s in sorted({scen(rows[x]["d_intent"]) for x in fit_ids if rows[x]["d_intent"]}):
            srows = [x for x in fit_ids if scen(rows[x]["d_intent"]) == s]
            best, best_val, best_n = None, 0.0, 0
            for rule in rules:
                ed = edited_rows(rule, srows)
                if len(ed) < C_MIN_EDITED_ROWS:
                    continue
                val = delta_of(ed)
                if val > best_val + 1e-12 or (best is not None and abs(val - best_val) <= 1e-12 and len(ed) < best_n):
                    best, best_val, best_n = rule, val, len(ed)
            if best is not None:
                chosen[s] = {"rule": f"{best[0]}<{best[1]}", "fit_pp": round(best_val, 4), "fit_rows_edited": best_n,
                             "_rule": best}
        return chosen

    def edit_diag(edits) -> dict:
        diag = Counter()
        for sid, new in edits.items():
            old = delivered["rows"][sid]["entities"]
            cls = V4S.entity_class(gold[sid]["entities"], old)
            remaining = list(new)
            for idx, e in enumerate(old):
                if e in remaining:
                    remaining.remove(e)
                else:
                    diag[f"dropped_{cls[idx]}"] += 1
            diag["rows_edited"] += 1
        return dict(sorted(diag.items()))

    boot = V4S.Bootstrap(ids, {sid: gold[sid]["utterance_id"] for sid in ids})
    op_c = {"rules_grid": [f"{f}<{t}" for f, t in rules], "min_edited_rows": C_MIN_EDITED_ROWS,
            "stats_pool": {"relpath": LEGAL[0], "content_sha256": LEGAL[1],
                           "exemplars": sum(stats.intent_n.values())}}
    c_edits = {}
    for fit_h in (0, 1):
        chosen = fit_scenario_rules(halves[fit_h])
        apply_ids = halves[1 - fit_h]
        applied = {}
        for s, ch in chosen.items():
            srows = [x for x in apply_ids if scen(rows[x]["d_intent"]) == s]
            applied.update(edited_rows(ch["_rule"], srows))
        op_c[f"fit_half{fit_h}"] = {"chosen": {s: {k: v for k, v in ch.items() if k != "_rule"} for s, ch in chosen.items()},
                                    "apply_rows_edited": len(applied), "apply_delta_pp_full_roster": round(delta_of(applied), 4),
                                    "apply_diag": edit_diag(applied)}
        c_edits.update(applied)
    c_matrix = matrix_with(c_edits)
    op_c["cross_fitted"] = {**boot.contrast(base, c_matrix), "diag": edit_diag(c_edits)}
    chosen_all = fit_scenario_rules(all_ids)
    ins = {}
    for s, ch in chosen_all.items():
        ins.update(edited_rows(ch["_rule"], [x for x in ids if scen(rows[x]["d_intent"]) == s]))
    op_c["in_sample_reference"] = {"chosen": {s: {k: v for k, v in ch.items() if k != "_rule"} for s, ch in chosen_all.items()},
                                   **boot.contrast(base, matrix_with(ins)), "diag": edit_diag(ins)}
    op_c["per_scenario_cross_fitted"] = V4S.per_scenario(ids, gold, base, c_matrix)
    # single global rules (no per-scenario choice), for context
    op_c["global_rules"] = {f"{f}<{t}": {"rows_edited": len(ed := edited_rows((f, t), ids)),
                                         "delta_pp": round(delta_of(ed), 4)} for f, t in rules}

    # ---- composite --------------------------------------------------------------
    def c_drops_type(sid, slot_type) -> bool:
        if sid not in c_edits:
            return False
        return slot_type not in {e.type for e in c_edits[sid]}

    item_by_key = {(i["sid"], i["gold_index"]): i for i in gold_side}
    a_keep = {x for x in a_new_items if not c_drops_type(x[0], item_by_key[x]["type"])}
    b_keep = {x for x in b_new_print - a_new_items if not c_drops_type(x[0], item_by_key[x]["type"])}
    c_delta = op_c["cross_fitted"]["delta_slu_pp"]
    comp = {"a_new_missing_after_c_overlap": len(a_keep), "a_removed_by_c": len(a_new_items) - len(a_keep),
            "b_new_print_missing_not_in_a_after_c": len(b_keep), "b_overlap_with_a": len(b_new_print & a_new_items),
            "b_exact_items_losing_print": op_b["cross_fit"].get("combined", {}).get("exact_items_losing_print", 0),
            "c_measured_pp": c_delta, "c_ci95": op_c["cross_fitted"]["ci95_slu_pp"]}
    for label, ca in (("conv_0.45", 0.45), ("conv_0.30", 0.30), ("conv_0.60", 0.60), ("w4_list_0.052", W4_LIST_RATE)):
        a_pp = len(a_keep) * ca * r_miss
        b_pp = len(b_keep) * M1_PRINT_RATE * r_miss + comp["b_exact_items_losing_print"] * M1_PRINT_RATE * r_exact
        comp[label] = {"a_pp": round(a_pp, 4), "b_slu_pp": round(b_pp, 4), "c_pp": round(c_delta, 4),
                       "composite_slu_pp": round(a_pp + b_pp + c_delta, 4),
                       "clears_1_5": a_pp + b_pp + c_delta >= TARGET_PP}
        # an upper reading: an operator enters only where its own cross-fitted SLU point is positive
        # (itself a selection, so it overstates; reported as the ceiling of an honest composite)
        pos = max(a_pp, 0.0) + max(b_pp, 0.0) + max(c_delta, 0.0)
        comp[label]["positive_parts_only_slu_pp"] = round(pos, 4)
    comp["intent_pp_b"] = op_b["cross_fit"].get("combined", {}).get("predicted_intent_pp", 0.0)
    comp["intent_pp_b_conv_ci"] = op_b["cross_fit"].get("combined", {}).get("predicted_intent_pp_conv_ci")
    comp["a_granularity"] = a_best
    # per scenario (gold scenario of the row)
    per_s = {}
    for s in sorted(inv_scen):
        sids = {x for x in ids if rows[x]["scenario"] == s}
        a_n = sum(1 for x in a_keep if x[0] in sids)
        b_n = sum(1 for x in b_keep if x[0] in sids)
        c_s = op_c["per_scenario_cross_fitted"]["per_scenario"].get(s, {}).get("delta_pp", 0.0)
        gain = len(b_gain_rows & sids)
        loss = len(b_loss_rows & sids)
        lostp = sum(b_cross_per[x]["lost_print_exact"] for x in sids if x in b_cross_per)
        k, n = CONV_INTENT
        b_slu = b_n * M1_PRINT_RATE * r_miss + lostp * M1_PRINT_RATE * r_exact
        per_s[s] = {"rows": len(sids), "a_new_missing": a_n, "a_pp_full_roster_045": round(a_n * 0.45 * r_miss, 4),
                    "b_new_print_missing": b_n, "b_exact_losing_print": lostp,
                    "b_slu_pp_full_roster": round(b_slu, 4), "b_gain_rows": gain, "b_loss_rows": loss,
                    "b_intent_pp_full_roster": round((gain * k / n - loss * loss_rate) * pp_row, 4),
                    "c_delta_pp_within_scenario": c_s,
                    "c_rows_edited": op_c["per_scenario_cross_fitted"]["per_scenario"].get(s, {}).get("rows_edited", 0)}
    comp["per_scenario"] = per_s

    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "column": {**COLUMN, "split_identity": FOLD_B_SPLIT,
                   "official": {k: round(v, 4) for k, v in delivered["official"].items()},
                   "in_process": {k: round(v, 4) for k, v in base_pooled.items()},
                   "outputs": delivered["outputs"], "scores": delivered["scores"],
                   "phases": [phases["relpath"], phases["sha256"]], "study_commit": run_manifest.get("study_commit"),
                   "totals_tp_fp_fn": [round(x, 4) for x in T],
                   "rate_recovered_missing_pp": round(r_miss, 4), "rate_exact_lost_pp": round(r_exact, 4),
                   "pp_intent_per_row": round(pp_row, 4)},
        "inputs": {"pool": list(POOL), "legal_pool": list(LEGAL), "exemplar_facets": list(EX_FACETS),
                   "exemplar_query": list(EX_QUERY), "boundary_query": list(IB_QUERY), "centroid": list(CENTROID),
                   "agreement": list(AGREEMENT), "slot_contracts": [cards["relpath"], cards["sha256"]],
                   "boundary_store_file_sha256": store["snapshot_file_sha256"],
                   "transcripts": {k: v for k, v in catalog_facts.items() if k in ("relpath", "sha256")},
                   "rosters": {k: [v, digest(REPO_ROOT / v)] for k, v in ROSTERS.items()}},
        "drivers": {n: [str(p.relative_to(REPO_ROOT)), digest(p)] for n, p in (
            ("this", Path(__file__).resolve()),
            ("v4_search", REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py"),
            ("node_gain_ledger", REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py"),
            ("error_sources", REPO_ROOT / "scripts/analysis/slurp_agree_arm_error_sources.py"),
            ("rank_diagnostic", REPO_ROOT / "scripts/analysis/slurp_intent_retrieval_rank_diagnostic.py"),
            ("gold_position", REPO_ROOT / "scripts/analysis/slurp_gold_position_and_solver_freedom_read.py"),
            ("w5_estimate", REPO_ROOT / "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"),
            ("e5_read", REPO_ROOT / "scripts/analysis/e5_transcript_consistency_read.py"))},
        "checks": checks, "halves": {str(h): len(v) for h, v in halves.items()},
        "inventory": {"row_classes": dict(Counter(r["class"] for r in rows.values())),
                      "by_class": inv_class, "by_type": inv_type, "by_scenario": inv_scen, "intent": inv_intent,
                      "spurious_items": sum(1 for i in items if i["kind"] == "SPURIOUS"),
                      "empty_gold_rows": sum(r["gold_empty"] for r in rows.values()),
                      "empty_gold_false_fill_rows": sum(r["class"] == "EMPTY-GOLD-FILL" for r in rows.values())},
        "operator_a": op_a, "operator_b": op_b, "operator_c": op_c, "composite": comp,
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header, body) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return "\n".join(out)


def render(r) -> str:
    inv, a, b, c, comp = r["inventory"], r["operator_a"], r["operator_b"], r["operator_c"], r["composite"]
    L = [f"# {READ_ID} tables", "", f"generated_at {r['generated_at']}", "",
         "## Column", "", "```", json.dumps(r["column"], indent=1, sort_keys=True), "```", "",
         "## Checks", "", "```", json.dumps(r["checks"], indent=1, sort_keys=True), "```", "",
         "## Inventory by class", "",
         md_table(["kind", "items", "(a)", "(b)", "(c)", "(d)", "reachable", "reachable (a)/(b)/(c)/(d)",
                   "on intent-wrong rows", "sub"],
                  [[k, v["items"], *[v["modes"][m] for m in MODES], v["reachable_in_transcript"],
                    "/".join(str(v["reachable_by_mode"][m]) for m in MODES),
                    v["on_intent_wrong_rows"], json.dumps(v["sub"], sort_keys=True)] for k, v in inv["by_class"].items()]),
         "", "row classes " + json.dumps(inv["row_classes"], sort_keys=True),
         f"spurious items {inv['spurious_items']}; empty-gold rows {inv['empty_gold_rows']}; false-fill rows "
         f"{inv['empty_gold_false_fill_rows']}", "",
         "## Inventory by slot type", "",
         md_table(["type", "items", "(a)", "(b)", "(c)", "(d)", "MISSING", "MISSING (a)/(b)/(c)/(d)",
                   "MISSING (b)+(c) reachable", "SPURIOUS"],
                  [[t, v["items"], *[v["modes"][m] for m in MODES], v["missing"],
                    "/".join(str(v["missing_modes"][m]) for m in MODES), v["missing_bc_reachable"], v["spurious"]]
                   for t, v in sorted(inv["by_type"].items(), key=lambda kv: -kv[1]["items"])]),
         "", "## Inventory by scenario", "",
         md_table(["scenario", "rows", "intent wrong", "of which gold in block", "gold-side items", "(a)", "(b)",
                   "(c)", "(d)", "MISSING", "SPURIOUS"],
                  [[s, v["rows"], v["intent_wrong"], v["intent_wrong_gold_in_block"], v["gold_side_items"],
                    *[v["modes"][m] for m in MODES], v["missing"], v["spurious"]] for s, v in inv["by_scenario"].items()]),
         "", "## Intent", "", "```", json.dumps(inv["intent"], indent=1), "```", "",
         "## Operator (a)", "", "```", json.dumps(a, indent=1, sort_keys=True), "```", "",
         "## Operator (b)", "", "```", json.dumps({k: v for k, v in b.items() if k != "grid_in_sample"}, indent=1,
                                                  sort_keys=True), "```", "",
         md_table(["variant (in-sample)", "gold newly in block (wrong rows)", "gold lost (correct rows)",
                   "rank-1 demoted", "rows changed", "MISSING newly printed", "exact losing print", "intent pp",
                   "SLU pp (M1 print)"],
                  [[n, v["gold_newly_in_block_on_intent_wrong"], v["gold_lost_from_block_on_correct"],
                    v["correct_rank1_demoted_inside_block"], v["rows_supply_changed"],
                    v["missing_newly_printed_reachable"], v["exact_items_losing_print"], v["predicted_intent_pp"],
                    v["predicted_slu_pp_m1_print"]] for n, v in b["grid_in_sample"].items()]),
         "", "## Operator (c)", "", "```", json.dumps(c, indent=1, sort_keys=True), "```", "",
         "## Composite", "", "```", json.dumps({k: v for k, v in comp.items() if k != "per_scenario"}, indent=1,
                                               sort_keys=True), "```", "",
         md_table(["scenario", "rows", "(a) new MISSING", "(a) pp @0.45", "(b) new print", "(b) exact losing print",
                   "(b) SLU pp", "(b) gain rows", "(b) loss rows", "(b) intent pp", "(c) delta within scenario",
                   "(c) rows edited"],
                  [[s, v["rows"], v["a_new_missing"], v["a_pp_full_roster_045"], v["b_new_print_missing"],
                    v["b_exact_losing_print"], v["b_slu_pp_full_roster"], v["b_gain_rows"], v["b_loss_rows"],
                    v["b_intent_pp_full_roster"], v["c_delta_pp_within_scenario"], v["c_rows_edited"]]
                   for s, v in comp["per_scenario"].items()]),
         ""]
    return "\n".join(L)


def strip_time(text: str) -> str:
    return re.sub(r'"generated_at": "[^"]*"', '"generated_at": ""', text)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    report = build(args)
    out = Path(args.data_root) / ANALYSIS_DIR
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=1, sort_keys=True, default=list)
    (out / "report.json").write_text(text + "\n", encoding="utf-8")
    tables = render(report)
    (out / "tables.md").write_text(tables, encoding="utf-8")
    content = {"report.json": hashlib.sha256(strip_time(text).encode("utf-8")).hexdigest(),
               "tables.md": hashlib.sha256(re.sub(r"generated_at \S+", "generated_at", tables).encode("utf-8")).hexdigest()}
    (out / "content-sha256.json").write_text(json.dumps(content, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), **content,
                      "composite": {k: v for k, v in report["composite"].items() if k != "per_scenario"}}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
