#!/usr/bin/env python3
"""Supply-side abstention headroom on TRAIN Fold A (owner decision 199), offline.

Owner decision 199 (2026-09-29): a slot may be none, and retrieval must be
allowed to return EMPTY instead of always padding to a fixed k; otherwise the
downstream model cannot decide.  Every supply node pads today: 20 TRAIN
exemplars to the Solver, 8 intent-boundary entries to Perception, and the
slot-contract view.  This read measures, model-free, how much official SLU-F1
(and what intent risk) a SUPPLY-SIDE abstention rule could address.

What it computes:

1. Score availability.  The per-item exemplar retrieval score is persisted in
   the sealed phase artefact (``waves[].rank_result.candidates[].score`` of the
   Perception wave, one entry per delivered exemplar).  The Perception boundary
   block is persisted as ids only; its per-item score (``w_cos * max_cosine +
   w_agree * agreement``) is recomputed through the production constructor
   ``rails.phase_supply._provider_factory`` from the pinned sealed vectors and
   the pinned agreement table, and the recomputed top-8 must equal the sealed
   block on every row.  Slot contracts carry ordinal scores only.
2. Separability.  Per row: exemplar top-1 score, mean of the top 5, margin
   top-1 minus top-2, spread top-1 minus top-20, and (a content signal, not a
   score) the share of the 20 exemplars that carry no entity.  AUC (bootstrap
   2,000) for "row has no gold entity" and "row emitted a SPURIOUS entity";
   boundary top-1 / margin / 8th score / 8-9 gap for "gold intent off the block".
3. Abstention rules on the exemplar supply, fixed grids declared in code:
   R1 row-abstain (top-1 < tau), R1m (mean top-5 < tau), R2 item threshold
   (keep items >= tau), R3 top-m when the top-1/top-2 margin is small.  A
   delivered prediction LOSES SUPPORT when some delivered exemplar contains its
   phrase and no retained exemplar does.  Oracle = every support-losing
   prediction vanishes (exact in-process re-score); expected = oracle x the M1
   delivered-filler conversion 0.2471.  Thresholds are cross-fitted over two
   utterance-hash halves.
4. Answer-side none: zero-gold emission across the sealed arms and the pp of
   reaching the A/A's zero-gold emission rate or halving it.

Gold discipline: gold enters only offline through the governed TRAIN loader
``data.slurp.load_slurp_split``, on the scoring side.  Text discipline: no
utterance text, transcript, gold value, filler, exemplar text or model output is
printed or persisted -- only ids, counts, rates, AUCs, pp, slot TYPE names,
scenario names and hashes.  Zero model, server, tokenizer, encoder, embedder,
scorer-subprocess, network and GPU contacts.

Deterministic apart from ``generated_at``.  ``--check`` re-derives and compares.

    PYTHONDONTWRITEBYTECODE=1 python scripts/analysis/slurp_supply_abstention_headroom.py \\
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

READ_ID = "SAEA-SLURP-SUPPLY-ABSTENTION-HEADROOM-OFFLINE-V1"
RECIPE = "slurp-supply-abstention-headroom-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080
BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SUPPLY = "prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v2.json"
EX_FACET_PREFIX = "train-exemplars::facet:content:"
EX_PREFIX = "train-exemplars::value:"
SC_PREFIX = "slot-contracts::slot-contract:"
IB_PREFIX = "intent-boundaries::intent-boundary:"
BOUNDARY_K = 8

BOOT_DRAWS = 2000
BOOT_SEED = 20260929
M1_RATE = 133 / (0.5719 * 941)  # docs/results/2026-09-28-slurp-w5-slot-exemplar-offline-estimate.md:51
TARGET_PP = 1.5
# fixed grids (declared before the first run; quantile levels of gold-free score distributions)
R1_Q = (0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
R2_Q = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90)
R3_Q = (0.0, 0.10, 0.20, 0.30, 0.40, 0.50)
R3_M = (1, 5)
# none-share gate (R4 supply-side, N1 answer-side). Added after the first run's AUC table showed the
# entity-free exemplar share separates zero-gold rows (0.846) while no score does; cross-fitted below.
NONE_T = (1.01, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3)
SUPPORT_DEFS = ("anywhere", "tagged", "untagged")
PRIMARY_SUPPORT = "anywhere"

#: label -> (run id, attempt holding outputs/scores, attempt holding phases or None)
ARMS = {
    "agree": ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", True),
    "agree_aa": ("SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1", "attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1", True),
    "wave_aa": ("SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1", True),
    "comp1_aa": ("SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1", True),
    "comp1": ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1", "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only", False),
}
FOLD_B_POOLS = {
    "filler_c01": ("SAEA-SLURP-STAGE3-FILLER-FOLD-B-C01-V1", "attempt-slurp-native-stage3-filler-fold-b-c01-generation-v1"),
    "filler_c02": ("SAEA-SLURP-STAGE3-FILLER-FOLD-B-C02-V1", "attempt-slurp-native-stage3-filler-fold-b-c02-generation-v1"),
}


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


HR = import_path(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py", "slurp_slu_consumption_headroom")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# pure functions (unit-tested on fakes)


def auc(scores, labels) -> float | None:
    """P(score of a positive > score of a negative), ties counted one half (Mann-Whitney)."""
    import numpy as np

    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=bool)
    npos, nneg = int(y.sum()), int((~y).sum())
    if npos == 0 or nneg == 0:
        return None
    _, inverse, counts = np.unique(s, return_inverse=True, return_counts=True)
    upper = np.cumsum(counts)
    average_rank = upper - (counts - 1) / 2.0  # 1-based average rank of each distinct value
    ranks = average_rank[inverse]
    return float((ranks[y].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def boot_auc(scores, labels, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> list:
    import numpy as np

    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=bool)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        idx = rng.integers(0, len(s), len(s))
        a = auc(s[idx], y[idx])
        if a is not None:
            vals.append(a)
    vals.sort()
    return [round(vals[int(0.025 * len(vals))], 4), round(vals[min(len(vals) - 1, int(0.975 * len(vals)))], 4)]


def row_features(scores: list, none_flags: list) -> dict:
    """Exemplar-supply features of one row. ``scores`` in rank order (descending)."""
    return {"top1": scores[0], "mean_top5": sum(scores[:5]) / len(scores[:5]),
            "margin_1_2": scores[0] - (scores[1] if len(scores) > 1 else 0.0),
            "spread_1_20": scores[0] - scores[-1],
            "none_share": sum(none_flags) / len(none_flags) if none_flags else 0.0}


def boundary_features(scores: list, k: int = BOUNDARY_K) -> dict:
    """A facet the recall did not admit has no score; it is read as 0.0 (below every admitted score)."""
    scores = list(scores) + [0.0] * max(0, k + 1 - len(scores))
    return {"top1": scores[0], "margin_1_2": scores[0] - scores[1], "score_at_k": scores[k - 1],
            "gap_k_k1": scores[k - 1] - scores[k]}


def quantile(values: list, q: float) -> float:
    xs = sorted(values)
    if q <= 0:
        return -math.inf
    pos = q * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def retained(ranked: list, rule: str, tau: float, m: int = 0, none_ids: frozenset = frozenset()) -> list:
    """Retained exemplar ids of one row. ``ranked``: [(id, score)] in rank order.
    R4 (content gate, not a score): when the share of entity-free exemplars is >= tau, keep only the
    entity-free ones (``none_ids``), i.e. the supply says "none" instead of padding with slot-bearing items."""
    if rule == "R4":
        share = sum(i in none_ids for i, _ in ranked) / len(ranked)
        return [i for i, _ in ranked if i in none_ids] if share >= tau else [i for i, _ in ranked]
    if rule in ("R1", "R1m"):
        feature = ranked[0][1] if rule == "R1" else sum(s for _, s in ranked[:5]) / len(ranked[:5])
        return [] if feature < tau else [i for i, _ in ranked]
    if rule == "R2":
        return [i for i, s in ranked if s >= tau]
    if rule == "R3":
        margin = ranked[0][1] - ranked[1][1]
        return [i for i, _ in ranked[:m]] if margin < tau else [i for i, _ in ranked]
    raise ValueError(rule)


def supporters(phrase: tuple, exemplars: dict, definition: str) -> set:
    """Exemplar ids whose text carries ``phrase``. ``exemplars``: id -> (utterance ngram set, filler ngram set)."""
    if not phrase:
        return set()
    out = set()
    for eid, (utt, fill) in exemplars.items():
        in_utt, in_fill = phrase in utt, phrase in fill
        if definition == "anywhere" and (in_utt or in_fill):
            out.add(eid)
        elif definition == "tagged" and in_fill:
            out.add(eid)
        elif definition == "untagged" and in_utt and not in_fill:
            out.add(eid)
    return out


def support_lost(support: set, kept: set) -> bool:
    return bool(support) and not (support & kept)


def split_half(utterance_id: str) -> int:
    return int(hashlib.sha256(str(utterance_id).encode("utf-8")).hexdigest(), 16) % 2


def pooled_delta(base_rows: dict, edited_rows: dict, ids) -> float:
    tb = [sum(base_rows[s][k] for s in ids) for k in range(3)]
    te = [sum(edited_rows[s][k] for s in ids) for k in range(3)]
    return HR.pooled_f1(te) - HR.pooled_f1(tb)


def boot_pp(base_rows: dict, edited_rows: dict, ids: list, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> list:
    import numpy as np

    b = np.array([base_rows[s] for s in ids], dtype=float)
    e = np.array([edited_rows[s] for s in ids], dtype=float)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        idx = rng.integers(0, len(ids), len(ids))
        out.append(HR.pooled_f1(e[idx].sum(0)) - HR.pooled_f1(b[idx].sum(0)))
    out.sort()
    return [round(out[int(0.025 * draws)], 3), round(out[min(draws - 1, int(0.975 * draws))], 3)]


def best_setting(results: list, key: str = "oracle_net_pp"):
    """Deterministic argmax: highest value, ties to the earlier grid entry (less abstention)."""
    best = None
    for r in results:
        if best is None or r[key] > best[key] + 1e-12:
            best = r
    return best


# ---------------------------------------------------------------------------
# derivation


def build(args) -> dict:
    import numpy as np  # noqa: F401  (bootstrap)
    from speech_aware_evidence_acquisition.analysis.sealed_credit import row_states as RS
    from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items, fold
    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot, QueryState
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        _provider_factory, load_phase_supply_specs, load_sealed_agreement, load_sealed_segment_vectors,
        load_sealed_vectors)

    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP = NG.ES, NG.GP
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario,
                          "entities": tuple(ES.SlotEntity(e.type, e.filler) for e in r.entities)} for r in records}
    utt_of = {r.sample_id: r.utterance_id for r in records}
    del records

    # ---- sealed phases: exemplar ranks + scores, boundary block, contract ordinal scores
    def read_phases(label):
        run_id, attempt, _ = ARMS[label]
        path = data_root / "runs" / run_id / attempt / f"{run_id}.phases.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        rows, checks = {}, Counter()
        for res in doc["phases"][0]["results"]:
            sid = res["sample_id"]
            boundary = [v.split("::", 1)[-1] for v in res["initial_query_state"]["retrieved_value_ids"]]
            ranked, rendered, contract_scores = [], [], []
            for w in res.get("waves") or ():
                cands = (w.get("rank_result") or {}).get("candidates") or []
                ex = [(str(c["facet_id"]).split(EX_FACET_PREFIX, 1)[-1], float(c["score"])) for c in cands
                      if str(c["facet_id"]).startswith(EX_FACET_PREFIX)]
                if not ex:
                    continue
                ranked = ex
                contract_scores = [float(c["score"]) for c in cands if str(c["facet_id"]).startswith(SC_PREFIX)]
                rendered = [v.split(EX_PREFIX, 1)[-1] for v in (w.get("fusion_decision") or {}).get("selected_value_ids") or []
                            if v.startswith(EX_PREFIX)]
                break
            checks["rows"] += 1
            checks["exemplar_scores_descending"] += int([s for _, s in ranked] == sorted((s for _, s in ranked), reverse=True))
            checks["exemplar_rank_set_equals_rendered_set"] += int({i for i, _ in ranked} == set(rendered))
            checks["exemplar_width_20"] += int(len(ranked) == 20)
            checks["contract_scores_are_ordinal_integers"] += int(all(float(s).is_integer() for s in contract_scores)
                                                                   and sorted(contract_scores, reverse=True)
                                                                   == [float(x) for x in range(len(contract_scores), 0, -1)])
            rows[sid] = {"ranked": ranked, "boundary": boundary, "contracts_n": len(contract_scores)}
        del doc
        return {"rows": rows, "checks": dict(sorted(checks.items())), "relpath": str(path.relative_to(data_root)),
                "sha256": digest(path)}

    phases = {label: read_phases(label) for label, spec in ARMS.items() if spec[2]}
    ids = sorted(phases["agree"]["rows"])
    if len(ids) != ROWS:
        raise ReadError("AGREE phases are not the 1,080-row roster")
    ranked = {sid: phases["agree"]["rows"][sid]["ranked"] for sid in ids}
    identity = {}
    for label, ph in phases.items():
        identity[label] = sum(ph["rows"][sid]["ranked"] == ranked[sid] for sid in ids)
    fold_b = {}
    for label, (run_id, attempt) in FOLD_B_POOLS.items():
        path = data_root / "runs" / run_id / attempt / f"{run_id}.phases.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        c = Counter()
        for ph in doc["phases"]:
            for res in ph["results"]:
                c["rows"] += 1
                for w in res.get("waves") or ():
                    cands = (w.get("rank_result") or {}).get("candidates") or []
                    n = sum(str(x["facet_id"]).startswith(EX_FACET_PREFIX) for x in cands)
                    if n:
                        c["rows_with_exemplar_scores"] += 1
                        c[f"exemplar_width_{n}"] += 1
                        break
        fold_b[label] = {"run_id": run_id, "phases_sha256": digest(path), **dict(sorted(c.items()))}
        del doc

    # ---- sealed outputs and per-sample official counts
    arms = {}
    for label, (run_id, attempt, _) in ARMS.items():
        directory = data_root / "runs" / run_id / attempt
        out = ES.load_outputs(directory, run_id)
        sealed = RS.load_scores(directory, run_id, SCORER)
        pred = {sid: out["rows"][sid]["entities"] for sid in ids}
        rs = HR.Rescorer({s: gold[s]["entities"] for s in ids}, pred, ES.slu_counts, ids)
        totals = tuple(sum(sealed["rows"][s][k] for s in ids) for k in ("tp", "fp", "fn"))
        if any(abs(a - b) > 1e-6 for a, b in zip(rs.base, totals)):
            raise ReadError(f"{label}: in-process totals do not reproduce the sealed official totals")
        arms[label] = {"run_id": run_id, "attempt": attempt, "pred": pred, "rs": rs,
                       "intent": {sid: out["rows"][sid]["intent"] for sid in ids},
                       "outputs": [out["relpath"], out["sha256"]], "scores": [sealed["relpath"], sealed["sha256"]],
                       "slu_f1": round(HR.pooled_f1(totals), 4)}

    # ---- exemplar pool (texts stay in-process as n-gram sets)
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    ex_cache = {}

    def ex_view(eid):
        if eid not in ex_cache:
            v = pool["values"][eid]
            fill = set()
            for fl in v["fillers"].values():
                for f in fl:
                    fill |= HR.ngrams(f.split())
            ex_cache[eid] = (HR.ngrams(v["utterance"].split()), fill, v["intent"], not v["fillers"])
        return ex_cache[eid]

    zero_gold = {sid: not gold[sid]["entities"] for sid in ids}

    # per arm, per prediction: class and support sets per definition
    def prediction_rows(label):
        pred = arms[label]["pred"]
        out = {}
        for sid in ids:
            its = entity_items(gold[sid]["entities"], pred[sid])
            spur = {it["pred_index"] for it in its if it["gold_index"] is None}
            matched = {it["pred_index"] for it in its if it["pred_index"] is not None}
            exs = {eid: ex_view(eid)[:2] for eid, _ in ranked[sid]}
            preds = []
            for pi, e in enumerate(pred[sid]):
                phrase = tuple(fold(e.filler).split())
                preds.append({"pred_index": pi, "spurious": pi in spur, "exact": pi not in matched,
                              "support": {d: supporters(phrase, exs, d) for d in SUPPORT_DEFS}})
            out[sid] = preds
        return out

    preds_by_arm = {label: prediction_rows(label) for label in arms}

    # ---- 1b. support recount (the headroom note's 89 / 81 are the untagged definition)
    recount = {}
    for label in arms:
        c = Counter()
        for sid in ids:
            for p in preds_by_arm[label][sid]:
                cls = "spurious" if p["spurious"] else "exact" if p["exact"] else "partial"
                c[f"{cls}_total"] += 1
                for d in SUPPORT_DEFS:
                    c[f"{cls}_supported_{d}"] += int(bool(p["support"][d]))
                if p["spurious"] and zero_gold[sid]:
                    c["spurious_on_zero_gold_rows"] += 1
                    c["spurious_on_zero_gold_rows_supported_anywhere"] += int(bool(p["support"]["anywhere"]))
        recount[label] = dict(sorted(c.items()))
    if (recount["agree"]["spurious_supported_untagged"], recount["agree"]["exact_supported_untagged"]) != (89, 81):
        raise ReadError("the headroom note's 89 / 81 (row-shown untagged) do not reproduce")

    # ---- 2. separability
    feats = {}
    for sid in ids:
        feats[sid] = row_features([s for _, s in ranked[sid]], [ex_view(eid)[3] for eid, _ in ranked[sid]])
    feat_names = ("top1", "mean_top5", "margin_1_2", "spread_1_20", "none_share")
    spur_row = {label: {sid: any(p["spurious"] for p in preds_by_arm[label][sid]) for sid in ids} for label in arms}
    separability = {}
    outcomes = {"row has no gold entity": [zero_gold[s] for s in ids]}
    for label in arms:
        outcomes[f"row emitted a SPURIOUS entity ({label})"] = [spur_row[label][s] for s in ids]
    outcomes["zero-gold row emitted a SPURIOUS entity (agree; within the 414)"] = None
    for oname, labels in outcomes.items():
        block = {}
        if labels is None:
            sub = [s for s in ids if zero_gold[s]]
            y = [spur_row["agree"][s] for s in sub]
        else:
            sub, y = ids, labels
        for f in feat_names:
            xs = [feats[s][f] for s in sub]
            a = auc(xs, y)
            block[f] = {"auc": round(a, 4), "ci95": boot_auc(xs, y), "positives": int(sum(y)), "n": len(sub)}
        separability[oname] = block
    feature_summary = {f: {"median_zero_gold": round(quantile([feats[s][f] for s in ids if zero_gold[s]], 0.5), 4),
                           "median_gold": round(quantile([feats[s][f] for s in ids if not zero_gold[s]], 0.5), 4)}
                       for f in feat_names}
    intent_support_check = Counter()
    for sid in ids:
        di = arms["agree"]["intent"][sid]
        intent_support_check["rows"] += 1
        intent_support_check["delivered_intent_has_exemplar_support"] += int(any(ex_view(e)[2] == di for e, _ in ranked[sid]))
        intent_support_check["gold_intent_has_exemplar_support"] += int(any(ex_view(e)[2] == gold[sid]["intent"] for e, _ in ranked[sid]))
    feature_summary["intent_support_check"] = dict(sorted(intent_support_check.items()))

    # ---- 2b. boundary scores (recomputed through the production constructor)
    base_cfg = json.loads((REPO_ROOT / BASELINE).read_text(encoding="utf-8"))
    store = base_cfg["knowledge_stores"]["intent-boundaries"]
    bspec = load_phase_supply_specs({"phase_supply": store["phase_supply"]}, default_phase_program(base_cfg["policy"]))["perception"]
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / store["snapshot"]["relpath"]).read_text(encoding="utf-8")))
    if snap.content_hash() != store["snapshot"]["sha256"]:
        raise ReadError("boundary snapshot does not hash to its pin")
    fvec = load_sealed_vectors(data_root / bspec.facet_source["relpath"], expected_sha256=bspec.facet_source["sha256"],
                               dimensions=bspec.dimensions)
    qvec = load_sealed_segment_vectors(data_root / bspec.query_source["relpath"],
                                       expected_sha256=bspec.query_source["sha256"], dimensions=bspec.dimensions)
    agr = load_sealed_agreement(data_root / bspec.agreement_source["relpath"],
                                expected_sha256=bspec.agreement_source["sha256"], dimension="agreement:exemplar-intent",
                                facet_ids=sorted(f.facet_id for f in snap.facets))
    factory = _provider_factory(bspec, snapshot=snap, snapshot_sha256=snap.content_hash(), facet_vectors=fvec,
                                provider_for_phase=None, agreement_scores=agr)
    prepared = json.loads((data_root / AGREE_SUPPLY).read_text(encoding="utf-8"))
    packets = prepared["inputs"]["sources"]["packets"]
    bchecks = Counter()
    bscores, border = {}, {}
    for sid in ids:
        state = QueryState(query_id=f"abstention-read:perception:{sid}", query_sample_id=sid,
                           speech_packet_id=packets[sid]["packet_id"], speech_packet_sha256=packets[sid]["sha256"],
                           use_split_identity_hash=prepared["inputs"]["split_identity_hash"]).validate()
        provider = factory()
        rk = provider.candidates({"query_state": state, "query_segments": qvec[sid].segments}, k=bspec.k)
        dec = provider.fuse([rk], k=bspec.k, policy_id=bspec.fuse_policy)
        rr = provider.last_rank_result()
        fused = [v.split("::", 1)[-1] for v in dec.selected_value_ids]
        bchecks["rows"] += 1
        bchecks["recomputed_block_equals_prepared_supply"] += int(fused == [v.split("::", 1)[-1] for v in prepared["output"]["values"]["perception"][sid]])
        bchecks["recomputed_block_equals_sealed_phases_block"] += int(fused == phases["agree"]["rows"][sid]["boundary"])
        bchecks["candidates_ranked_60"] += int(len(rr.candidates) == 60)
        bchecks[f"candidates_ranked_{'ge9' if len(rr.candidates) > BOUNDARY_K else 'le8'}"] += 1
        bchecks[f"block_width_{len(fused)}"] += 1
        bscores[sid] = [float(c.score) for c in rr.candidates]
        border[sid] = [str(c.facet_id).split("intent-boundary:", 1)[-1] for c in rr.candidates]
    if bchecks["recomputed_block_equals_sealed_phases_block"] != ROWS:
        raise ReadError("recomputed boundary block does not reproduce the sealed block")
    bfeat = {sid: boundary_features(bscores[sid]) for sid in ids}
    off_block = {sid: gold[sid]["intent"] not in border[sid][:BOUNDARY_K] for sid in ids}
    intent_wrong = {sid: arms["agree"]["intent"][sid] != gold[sid]["intent"] for sid in ids}
    gold_rank = {sid: (border[sid].index(gold[sid]["intent"]) + 1 if gold[sid]["intent"] in border[sid] else None) for sid in ids}
    bsep = {}
    for oname, sub in (("gold intent off the block (all rows)", ids),
                       ("gold intent off the block (AGREE intent-wrong rows)", [s for s in ids if intent_wrong[s]]),
                       ("AGREE delivered intent wrong (all rows)", ids)):
        y = [intent_wrong[s] if oname.startswith("AGREE delivered") else off_block[s] for s in sub]
        block = {}
        for f in ("top1", "margin_1_2", "score_at_k", "gap_k_k1"):
            xs = [bfeat[s][f] for s in sub]
            block[f] = {"auc": round(auc(xs, y), 4), "ci95": boot_auc(xs, y), "positives": int(sum(y)), "n": len(sub)}
        bsep[oname] = block
    boundary = {"checks": dict(sorted(bchecks.items())),
                "rows_gold_off_block": sum(off_block.values()),
                "intent_wrong_rows": sum(intent_wrong.values()),
                "intent_wrong_and_gold_off_block": sum(1 for s in ids if intent_wrong[s] and off_block[s]),
                "gold_rank_histogram_off_block": dict(sorted(Counter(
                    ("not recalled" if r is None else "9-12" if r <= 12 else "13-20" if r <= 20 else "21-60")
                    for s in ids if off_block[s]
                    for r in [gold_rank[s]]).items())),
                "separability": bsep,
                "rank_weights": dict(bspec.rank_weights or {}), "tau": bspec.tau, "recall_k": bspec.k,
                "fuse_coverage": dict(bspec.fuse_coverage or {}),
                "inputs": {"snapshot_sha256": store["snapshot"]["sha256"], "facet_vectors": bspec.facet_source["sha256"],
                           "query_vectors": bspec.query_source["sha256"], "agreement": bspec.agreement_source["sha256"],
                           "prepared_supply_sha256": digest(data_root / AGREE_SUPPLY)}}

    # ---- 3. abstention rules
    top1_all = [ranked[s][0][1] for s in ids]
    mean5_all = [feats[s]["mean_top5"] for s in ids]
    items_all = [sc for s in ids for _, sc in ranked[s]]
    margin_all = [feats[s]["margin_1_2"] for s in ids]
    grid = []
    for q in R1_Q:
        grid.append({"rule": "R1", "q": q, "tau": quantile(top1_all, q), "m": 0})
    for q in R1_Q:
        grid.append({"rule": "R1m", "q": q, "tau": quantile(mean5_all, q), "m": 0})
    for q in R2_Q:
        grid.append({"rule": "R2", "q": q, "tau": quantile(items_all, q), "m": 0})
    for m in R3_M:
        for q in R3_Q:
            grid.append({"rule": "R3", "q": q, "tau": quantile(margin_all, q), "m": m})
    for t in NONE_T:
        grid.append({"rule": "R4", "q": t, "tau": t, "m": 0})
    none_ids = frozenset(e for s in ids for e, _ in ranked[s] if ex_view(e)[3])
    half = {s: split_half(utt_of[s]) for s in ids}

    def evaluate(label, setting, definition, rows_subset=None):
        """Edited predictions for rows in ``rows_subset`` (default all) under ``setting``."""
        arm = arms[label]
        subset = ids if rows_subset is None else rows_subset
        drops, drops_sp, drops_harm, c = {}, {}, {}, Counter()
        intent_c = Counter()
        for sid in subset:
            kept = set(retained(ranked[sid], setting["rule"], setting["tau"], setting["m"], none_ids))
            n_kept = len(kept)
            if n_kept == 0:
                c["rows_abstained"] += 1
                c["rows_abstained_zero_gold" if zero_gold[sid] else "rows_abstained_gold"] += 1
            c["exemplars_withheld"] += len(ranked[sid]) - n_kept
            lost = set()
            for p in preds_by_arm[label][sid]:
                if support_lost(p["support"][definition], kept):
                    lost.add(p["pred_index"])
                    cls = "spurious" if p["spurious"] else "exact" if p["exact"] else "partial"
                    c[f"{cls}_losing_support"] += 1
                    if cls == "spurious" and zero_gold[sid]:
                        c["spurious_losing_support_on_zero_gold_rows"] += 1
                    (drops_sp if cls == "spurious" else drops_harm).setdefault(sid, set()).add(p["pred_index"])
            if lost:
                drops[sid] = lost
            di = arm["intent"][sid]
            before = sum(ex_view(e)[2] == di for e, _ in ranked[sid])
            after = sum(ex_view(e)[2] == di for e in kept)
            if after < before:
                key = "correct" if di == gold[sid]["intent"] else "wrong"
                intent_c[f"delivered_intent_support_drops_{key}_rows"] += 1
                if after == 0 and before > 0:
                    intent_c[f"delivered_intent_support_to_zero_{key}_rows"] += 1
        new = HR.drop_preds(drops, arm["pred"])
        evaluate.last_parts = (HR.drop_preds(drops_sp, arm["pred"]), HR.drop_preds(drops_harm, arm["pred"]))
        return new, dict(sorted(c.items())), dict(sorted(intent_c.items()))

    sweeps = {}
    for label in ("agree",):
        for definition in SUPPORT_DEFS:
            res = []
            for g in grid:
                new, c, ic = evaluate(label, g, definition)
                rs = arms[label]["rs"]
                edited = rs.edited_rows(new)
                oracle = pooled_delta(rs.base_rows, edited, ids)
                # one-sided parts: spurious-only drops (gross gain) and exact/partial-only drops (harm)
                sp_new, harm_new = evaluate.last_parts
                gross = pooled_delta(rs.base_rows, rs.edited_rows(sp_new), ids)
                harm = pooled_delta(rs.base_rows, rs.edited_rows(harm_new), ids)
                res.append({**{k: (round(v, 6) if isinstance(v, float) and math.isfinite(v) else v if isinstance(v, (int, str)) else None)
                               for k, v in g.items()}, **c, **ic,
                            "oracle_gross_pp": round(gross, 4), "oracle_harm_pp": round(harm, 4),
                            "oracle_net_pp": round(oracle, 4), "expected_net_pp_at_m1": round(oracle * M1_RATE, 4)})
            sweeps[f"{label}/{definition}"] = res

    # cross-fit on the primary definition: tau chosen on one half, evaluated on the other
    crossfit = {}
    for rule_family in ("R1", "R1m", "R2", "R3", "R4"):
        fam = [g for g in grid if g["rule"] == rule_family]
        chosen = {}
        for h in (0, 1):
            rows_h = [s for s in ids if half[s] == h]
            scored = []
            for g in fam:
                new, _, _ = evaluate("agree", g, PRIMARY_SUPPORT, rows_h)
                rs = arms["agree"]["rs"]
                scored.append({**g, "oracle_net_pp": pooled_delta(rs.base_rows, rs.edited_rows(new), rows_h)})
            chosen[h] = best_setting(scored)
        # apply half-0's choice to half 1 and vice versa, evaluate on all rows
        rs = arms["agree"]["rs"]
        new_all, counts = {}, Counter()
        for h in (0, 1):
            other = chosen[1 - h]
            rows_h = [s for s in ids if half[s] == h]
            new, c, _ = evaluate("agree", other, PRIMARY_SUPPORT, rows_h)
            new_all.update(new)
            counts.update(c)
        edited = rs.edited_rows(new_all)
        net = pooled_delta(rs.base_rows, edited, ids)
        crossfit[rule_family] = {
            "chosen_on_half_0": {"q": chosen[0]["q"], "m": chosen[0]["m"], "in_half_net_pp": round(chosen[0]["oracle_net_pp"], 4)},
            "chosen_on_half_1": {"q": chosen[1]["q"], "m": chosen[1]["m"], "in_half_net_pp": round(chosen[1]["oracle_net_pp"], 4)},
            "rows_half_0": sum(1 for s in ids if half[s] == 0),
            "cross_fitted_oracle_net_pp": round(net, 4), "ci95": boot_pp(rs.base_rows, edited, ids),
            "cross_fitted_expected_net_pp_at_m1": round(net * M1_RATE, 4), **dict(sorted(counts.items()))}

    # best in-sample setting (primary definition) with CI, strata and replicates
    prim = sweeps[f"agree/{PRIMARY_SUPPORT}"]
    best = best_setting(prim)
    best_g = next(g for g in grid if g["rule"] == best["rule"] and g["q"] == best["q"] and g["m"] == best["m"])
    new_best, _, _ = evaluate("agree", best_g, PRIMARY_SUPPORT)
    rs = arms["agree"]["rs"]
    edited_best = rs.edited_rows(new_best)
    best_block = {**best, "ci95": boot_pp(rs.base_rows, edited_best, ids)}
    strata = {}
    for scen in sorted({gold[s]["scenario"] for s in ids}):
        sub = [s for s in ids if gold[s]["scenario"] == scen]
        _, c, _ = evaluate("agree", best_g, PRIMARY_SUPPORT, sub)
        strata[scen] = {"rows": len(sub), "zero_gold_rows": sum(zero_gold[s] for s in sub), **c,
                        "within_stratum_pp": round(pooled_delta(rs.base_rows, edited_best, sub), 4)}
    by_gold = {}
    for name, sub in (("zero-gold rows (414)", [s for s in ids if zero_gold[s]]),
                      ("gold-entity rows (666)", [s for s in ids if not zero_gold[s]])):
        _, c, _ = evaluate("agree", best_g, PRIMARY_SUPPORT, sub)
        by_gold[name] = {"rows": len(sub), **c}
    replicates = {}
    for label in arms:
        if label == "agree":
            continue
        new, c, ic = evaluate(label, best_g, PRIMARY_SUPPORT)
        rs_l = arms[label]["rs"]
        ed = rs_l.edited_rows(new)
        replicates[label] = {"oracle_net_pp": round(pooled_delta(rs_l.base_rows, ed, ids), 4),
                             "ci95": boot_pp(rs_l.base_rows, ed, ids), **c}
    # best per rule family (in-sample, primary) for the summary table
    best_per_family = {}
    for fam in ("R1", "R1m", "R2", "R3", "R4"):
        b = best_setting([r for r in prim if r["rule"] == fam])
        best_per_family[fam] = b
    # upper bound of row abstention on zero-gold rows: every zero-gold abstained row's spurious vanish
    zg_bound = {}
    for g in [x for x in grid if x["rule"] == "R1"]:
        drops = {}
        for s in ids:
            if zero_gold[s] and not retained(ranked[s], "R1", g["tau"]):
                sp = {p["pred_index"] for p in preds_by_arm["agree"][s] if p["spurious"]}
                if sp:
                    drops[s] = sp
        zg_bound[str(g["q"])] = {"zero_gold_rows_abstained_emitting": len(drops),
                                 "spurious_removed": sum(len(v) for v in drops.values()),
                                 "pp_if_all_vanish": round(rs.gain(HR.drop_preds(drops, arms["agree"]["pred"])), 4)}

    # ---- 3b. N1: answer-side none gated by the supply's none-share (oracle: the Solver answers no
    # entity on every gated row). A bound for a "none" contract that the supply signal triggers.
    def n1_new(label, t, rows_subset=None):
        subset = ids if rows_subset is None else rows_subset
        return {s: [] for s in subset if feats[s]["none_share"] >= t and arms[label]["pred"][s]}

    def n1_counts(label, t):
        c = Counter()
        for s in ids:
            if feats[s]["none_share"] < t:
                continue
            c["rows_gated"] += 1
            c["rows_gated_zero_gold" if zero_gold[s] else "rows_gated_gold"] += 1
            for p in preds_by_arm[label][s]:
                c["spurious_removed" if p["spurious"] else "exact_removed" if p["exact"] else "partial_removed"] += 1
        return dict(sorted(c.items()))

    n1 = {"sweep": [], "crossfit": {}, "replicates": {}}
    rs = arms["agree"]["rs"]
    for t in NONE_T:
        ed = rs.edited_rows(n1_new("agree", t))
        net = pooled_delta(rs.base_rows, ed, ids)
        n1["sweep"].append({"theta": t, **n1_counts("agree", t), "oracle_net_pp": round(net, 4),
                            "expected_net_pp_at_m1": round(net * M1_RATE, 4)})
    n1_chosen = {}
    for h in (0, 1):
        rows_h = [s for s in ids if half[s] == h]
        n1_chosen[h] = best_setting([{"theta": t, "oracle_net_pp": pooled_delta(
            rs.base_rows, rs.edited_rows(n1_new("agree", t, rows_h)), rows_h)} for t in NONE_T])
    new_cf = {}
    for h in (0, 1):
        new_cf.update(n1_new("agree", n1_chosen[1 - h]["theta"], [s for s in ids if half[s] == h]))
    ed_cf = rs.edited_rows(new_cf)
    net_cf = pooled_delta(rs.base_rows, ed_cf, ids)
    n1["crossfit"] = {"theta_chosen_on_half_0": n1_chosen[0]["theta"], "theta_chosen_on_half_1": n1_chosen[1]["theta"],
                      "cross_fitted_oracle_net_pp": round(net_cf, 4), "ci95": boot_pp(rs.base_rows, ed_cf, ids),
                      "cross_fitted_expected_net_pp_at_m1": round(net_cf * M1_RATE, 4)}
    n1_best = best_setting(n1["sweep"])
    ed_b = rs.edited_rows(n1_new("agree", n1_best["theta"]))
    n1["best_in_sample"] = {**n1_best, "ci95": boot_pp(rs.base_rows, ed_b, ids)}
    n1_strata = {}
    for scen in sorted({gold[s]["scenario"] for s in ids}):
        sub = [s for s in ids if gold[s]["scenario"] == scen]
        c = Counter()
        for s in sub:
            if feats[s]["none_share"] >= n1_best["theta"]:
                c["rows_gated"] += 1
                c["rows_gated_zero_gold"] += int(zero_gold[s])
                for p in preds_by_arm["agree"][s]:
                    c["spurious_removed" if p["spurious"] else "exact_removed" if p["exact"] else "partial_removed"] += 1
        n1_strata[scen] = {"rows": len(sub), "zero_gold_rows": sum(zero_gold[s] for s in sub), **dict(sorted(c.items())),
                           "within_stratum_pp": round(pooled_delta(rs.base_rows, ed_b, sub), 4)}
    n1["best_strata_by_scenario"] = n1_strata
    for label in arms:
        if label == "agree":
            continue
        rs_l = arms[label]["rs"]
        ed = rs_l.edited_rows(n1_new(label, n1_best["theta"]))
        n1["replicates"][label] = {"oracle_net_pp": round(pooled_delta(rs_l.base_rows, ed, ids), 4),
                                   "ci95": boot_pp(rs_l.base_rows, ed, ids), **n1_counts(label, n1_best["theta"])}

    # ---- 4. answer-side none
    ans = {}
    for label in arms:
        zg = [s for s in ids if zero_gold[s]]
        ans[label] = {"zero_gold_rows_emitting": sum(1 for s in zg if arms[label]["pred"][s]),
                      "spurious_on_zero_gold_rows": sum(len(arms[label]["pred"][s]) for s in zg),
                      "slu_f1": arms[label]["slu_f1"]}
    flips = {}
    for a, b in (("comp1", "comp1_aa"), ("agree", "agree_aa"), ("comp1_aa", "agree_aa"), ("agree", "wave_aa"),
                 ("wave_aa", "agree_aa")):
        zg = [s for s in ids if zero_gold[s]]
        ea = {s: bool(arms[a]["pred"][s]) for s in zg}
        eb = {s: bool(arms[b]["pred"][s]) for s in zg}
        flips[f"{a} vs {b}"] = {"emit_only_left": sum(ea[s] and not eb[s] for s in zg),
                                "emit_only_right": sum(eb[s] and not ea[s] for s in zg)}
    # headroom: COMP-1 -> COMP-1 A/A zero-gold rows (row swap of sealed counts), AGREE halving
    zg = [s for s in ids if zero_gold[s]]
    swap = {s: arms["comp1_aa"]["rs"].base_rows[s] for s in zg}
    comp1_rows = dict(arms["comp1"]["rs"].base_rows)
    swapped = {**comp1_rows, **swap}
    comp1_swap_pp = pooled_delta(comp1_rows, swapped, ids)
    agree_totals = arms["agree"]["rs"].base
    sp_zg = ans["agree"]["spurious_on_zero_gold_rows"]
    f10_fn_per_fp = 13 / 22  # docs/results/2026-09-25-slurp-f10-complete-verdict.md:18-21 (FP 142 -> 120, FN 384 -> 397)
    halving = {"fp_removed": sp_zg / 2,
               "gross_pp": round(HR.gain_pp(agree_totals, fp_removed=sp_zg / 2), 4),
               "net_pp_with_f10_harm": round(HR.trade_pp(agree_totals, fp_removed=sp_zg / 2,
                                                          exact_lost=sp_zg / 2 * f10_fn_per_fp), 4)}
    contract_shift_rows = ans["comp1"]["zero_gold_rows_emitting"] - ans["comp1_aa"]["zero_gold_rows_emitting"]
    contract_shift_fp = ans["comp1"]["spurious_on_zero_gold_rows"] - ans["comp1_aa"]["spurious_on_zero_gold_rows"]
    fp_per_row = sp_zg / ans["agree"]["zero_gold_rows_emitting"]
    reverse = {"rows": contract_shift_rows, "fp_removed": round(contract_shift_rows * fp_per_row, 2),
               "gross_pp": round(HR.gain_pp(agree_totals, fp_removed=contract_shift_rows * fp_per_row), 4),
               "net_pp_with_f10_harm": round(HR.trade_pp(agree_totals, fp_removed=contract_shift_rows * fp_per_row,
                                                          exact_lost=contract_shift_rows * fp_per_row * f10_fn_per_fp), 4)}
    answer_side = {
        "per_arm": ans, "zero_gold_emission_flips": flips,
        "comp1_to_its_aa_zero_gold_rate_row_swap_pp": round(comp1_swap_pp, 4),
        "contract_shift": {"zero_gold_rows": contract_shift_rows, "spurious": contract_shift_fp,
                           "share_of_414": round(contract_shift_rows / len(zg), 4)},
        "agree_halving_zero_gold_emission": halving,
        "agree_reverse_shift_of_the_contract_size": reverse,
        "agree_oracle_empty_every_zero_gold_emitting_row_pp": round(arms["agree"]["rs"].gain({s: [] for s in zg if arms["agree"]["pred"][s]}), 4),
        "fp_marginal_pp_at_agree_totals": round(HR.gain_pp(agree_totals, fp_removed=1), 5),
        "fn_marginal_pp_at_agree_totals": round(HR.gain_pp(agree_totals, fn_recovered=1), 5),
        "f10_fn_per_fp": round(f10_fn_per_fp, 4),
    }

    return {
        "read_id": READ_ID, "recipe": RECIPE, "status": "DESCRIPTIVE",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                     "official_scorer_subprocess": 0, "network": 0, "gpu": 0, "paid_api": 0},
        "arms": {label: {"run_id": a["run_id"], "attempt": a["attempt"], "outputs": a["outputs"], "scores": a["scores"],
                         "slu_f1": a["slu_f1"]} for label, a in arms.items()},
        "phases": {label: {"relpath": p["relpath"], "sha256": p["sha256"], "checks": p["checks"]} for label, p in phases.items()},
        "exemplar_ranked_list_identical_to_agree_rows": identity,
        "fold_b_pools_score_availability": fold_b,
        "exemplar_pool": [pool["relpath"], pool["sha256"]],
        "driver_sha256": {"headroom": digest(REPO_ROOT / "scripts/analysis/slurp_slu_consumption_headroom.py"),
                          "node_gain_ledger": digest(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py")},
        "m1_rate": round(M1_RATE, 4), "target_pp": TARGET_PP,
        "exemplar_score_distribution": {"top1_quantiles": {str(q): round(quantile(top1_all, q), 4) for q in (0.05, 0.25, 0.5, 0.75, 0.95)},
                                        "item_quantiles": {str(q): round(quantile(items_all, q), 4) for q in (0.05, 0.25, 0.5, 0.75, 0.95)}},
        "feature_medians": feature_summary,
        "support_recount": recount,
        "separability_exemplar": separability,
        "boundary": boundary,
        "sweeps": sweeps,
        "best_per_family_in_sample_primary": best_per_family,
        "best_in_sample_primary": best_block,
        "best_strata_by_scenario": strata,
        "best_by_gold_presence": by_gold,
        "best_replicates": replicates,
        "crossfit_primary": crossfit,
        "row_abstention_zero_gold_upper_bound": zg_bound,
        "answer_side": answer_side,
        "n1_none_share_gated_empty_answer": n1,
        "halves": {"rule": "sha256(utterance_id) mod 2", "rows_half_0": sum(1 for s in ids if half[s] == 0)},
    }


# ---------------------------------------------------------------------------
# rendering


def md_table(header: list, rows: list) -> str:
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def render(r: dict) -> str:
    parts = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", ""]
    parts += ["## Arms", "", md_table(["arm", "run", "SLU-F1"], [[k, v["run_id"], v["slu_f1"]] for k, v in r["arms"].items()]), ""]
    parts += ["## Phase checks", "", "```json", json.dumps({"phases": r["phases"], "identity": r["exemplar_ranked_list_identical_to_agree_rows"],
                                                             "fold_b": r["fold_b_pools_score_availability"]}, indent=2, sort_keys=True), "```", ""]
    parts += ["## Support recount", "", "```json", json.dumps(r["support_recount"], indent=2, sort_keys=True), "```", ""]
    parts += ["## Exemplar separability", ""]
    for o, block in r["separability_exemplar"].items():
        parts.append(f"### {o}")
        parts.append("")
        parts.append(md_table(["feature", "AUC", "CI95", "positives", "n"],
                              [[f, v["auc"], v["ci95"], v["positives"], v["n"]] for f, v in block.items()]))
        parts.append("")
    parts += ["## Boundary", "", "```json", json.dumps(r["boundary"], indent=2, sort_keys=True), "```", ""]
    for key, rows in r["sweeps"].items():
        parts += [f"## Sweep {key}", "",
                  md_table(["rule", "q", "m", "tau", "abstained", "abst zero-gold", "abst gold", "spurious lost", "exact lost",
                            "partial lost", "intent drop to 0 correct", "intent drop to 0 wrong", "gross pp", "harm pp", "net pp", "net at M1"],
                           [[x["rule"], x["q"], x["m"], x["tau"], x.get("rows_abstained", 0), x.get("rows_abstained_zero_gold", 0),
                             x.get("rows_abstained_gold", 0), x.get("spurious_losing_support", 0), x.get("exact_losing_support", 0),
                             x.get("partial_losing_support", 0), x.get("delivered_intent_support_to_zero_correct_rows", 0),
                             x.get("delivered_intent_support_to_zero_wrong_rows", 0), x["oracle_gross_pp"], x["oracle_harm_pp"],
                             x["oracle_net_pp"], x["expected_net_pp_at_m1"]] for x in rows]), ""]
    for key in ("best_per_family_in_sample_primary", "best_in_sample_primary", "best_strata_by_scenario", "best_by_gold_presence",
                "best_replicates", "crossfit_primary", "row_abstention_zero_gold_upper_bound", "answer_side",
                "n1_none_share_gated_empty_answer",
                "exemplar_score_distribution", "feature_medians"):
        parts += [f"## {key}", "", "```json", json.dumps(r[key], indent=2, sort_keys=True), "```", ""]
    return "\n".join(parts)


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
