#!/usr/bin/env python3
"""SLURP Solver intent-decision oracle (offline, DESCRIPTIVE).

Read id ``SAEA-SLURP-SOLVER-DECISION-ORACLE-OFFLINE-V1``. Model-free: zero model, server, tokenizer,
encoder, embedder, GPU, network and paid-API contacts; no official-scorer subprocess (per-row
official column scores are read from the sealed score files and used only as a parse cross-check);
``core.flight.cli`` and ``lease_cli`` are never invoked. Gold enters only offline through the
governed TRAIN loader (``data.slurp.load_slurp_split``), on the scoring side. Utterance text, note
text, exemplar bodies, gold values and model output are never printed or persisted: only ids,
counts, rates, AUCs, pp and hashes.

The question (coordinator brief 2026-09-30, the second blank between ~86 % and the 95 % intent
target): the Solver converts gold at Perception rank 1 at ~97.6 %, at rank 2 at ~27 % and at rank 3
at ~12 %. Among the rows where the Solver KEPT the note's rank-1 candidate (note of two or more
candidates), which model-visible signals separate "rank 1 was wrong and gold sat at note rank 2 or
3" (the decision oracle's positives: a re-decision over the top candidates could flip them) from
"rank 1 was right" (negatives: a re-decision can only cost)? Rows with gold off the note are the
third class (a re-decision over the note cannot reach gold); they are counted as call cost only.

Signals (per row, from sealed bytes and pinned tables):

* ``note_n`` -- note candidate count (2 or 3);
* ``margin_b`` -- boundary-score margin s(note r1) - s(note r2), the fused rank score recomputed
  from the pinned vectors and agreement table through the production constructor, exactly as the
  block-depth read did (the depth-8 prefix of the recomputed order must equal the sealed block);
* ``r1_off_block_top`` -- 1 when the note's rank 1 is not the block's rank 1 (Perception re-ranked);
* ``agr_diff`` -- agreement-table share of r1 minus that of r2;
* ``ex_diff`` / ``ex_r1`` / ``ex_r2`` -- exemplar votes among the 20 delivered exemplars;
* ``ex_top_is_r2`` -- 1 when the exemplar-vote winner is r2 (strictly);
* ``same_scenario`` -- r1 and r2 share the scenario;
* ``scen_r1_te`` -- the r1 scenario's positive rate, cross-fitted by utterance halves;
* ``efs`` -- entity-free share of the 20 delivered exemplars (the decision-199 trigger);
* ``twin_dis`` -- the same-flight twin picked a different intent (where a twin exists).

Per pool: the gold-rank x pick table; the oracle ceiling (rows with gold at note rank 2/3 and a
wrong Solver pick) in pp; AUC with a row-bootstrap CI95 per signal; the best two-signal rule under
cross-fit (sha256(utterance id) halves: pair selected and logistic fitted on one half, applied to
the other); its out-of-half operating points; the twin's measured re-sample conversion (P(twin
right | positive)) and harm (P(twin wrong | negative)); and the expected flips at those measured
rates.

``--check`` re-derives both outputs and compares them with the written files apart from
``generated_at``.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import importlib.util
import itertools
import json
import math
import re
import sys
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

READ_ID = "SAEA-SLURP-SOLVER-DECISION-ORACLE-OFFLINE-V1"
RECIPE = "slurp-solver-decision-oracle-offline-v1"
ANALYSIS_DIR = "analysis/" + READ_ID
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
SCORER = "slurp-slu-official-train"
ROWS = 1080
IB_FACET_MARK = "intent-boundary:"
EX_PREFIX = "train-exemplars::value:"
EX_SNAPSHOT = None  # resolved from the error-source read (ES.EX_SNAPSHOT) at build time
BOOT_DRAWS = 10_000
BOOT_SEED = 20260930
#: same-flight intent floor at n = 1,080 (owner decision 190) and the cross-flight bar
INTENT_FLOOR_PP = 0.65
CROSS_FLIGHT_BAR_PP = 2.5
CALL_RATES = (0.05, 0.10, 0.20)
#: measured second-contact anchor quoted (not recomputed) from the REV-TFRL-1 read
#: (docs/results/2026-09-28-slurp-revtfrl-1-fold-a-read.md section 4, credit table, arm column):
#: a Reviewer-routed second Solver contact repaired intent on 10 of 54 revised INT-SHORTLIST visits
#: and broke it on 8 of 164 revised CORRECT visits.
REVTFRL_CONVERSION = (10, 54)
REVTFRL_HARM = (8, 164)

CFG = {
    "A": "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json",
    "A_cent": "configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json",
    "B": "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1-resume.json",
}

#: pool -> (fold, retrieval key, run id, attempt, kind, A arm, T arm or twin run)
POOLS = {
    "agree": ("A", "desc_agree", "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
              "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "phases", None,
              ("SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1")),
    "comp1b": ("A", "cent_agree", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
               "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1", "phases", None, None),
    "wsv1": ("A", "desc_agree", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1",
             "attempt-slurp-native-stage3-wsv1-fold-a-generation-v1", "columns", "a-base", "t-twin"),
    "w4sv": ("A", "desc_agree", "SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1",
             "attempt-slurp-native-stage3-w4sv-fold-a-generation-v1", "columns", "a-agree", "t-twin"),
    "psv1": ("B", "desc_agree", "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1",
             "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only", "branches", "a-agree", "t-twin"),
    "psv2": ("B", "desc_agree", "SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1",
             "attempt-slurp-native-stage3-psv2-fold-b-generation-v1", "branches", "a-agree", "t-twin"),
    "psv3": ("B", "desc_agree", "SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1",
             "attempt-slurp-native-stage3-psv3-fold-b-generation-v1", "branches", "a-agree", "t-twin"),
}
TWIN_KIND = {"phases": "cross-flight replicate (own Perception note)", "columns": "same-flight Solver twin (same note, same supply)",
             "branches": "same-flight Perception+Solver twin (own note)"}

SIGNALS = ("note_n", "margin_b", "r1_off_block_top", "agr_diff", "ex_diff", "ex_r1", "ex_r2", "ex_top_is_r2",
           "same_scenario", "scen_r1_te", "efs", "twin_dis")
SIGNAL_TITLES = {
    "note_n": "note candidate count (2 or 3)",
    "margin_b": "boundary-score margin s(r1) - s(r2), recomputed",
    "r1_off_block_top": "note r1 is not the block's rank 1",
    "agr_diff": "agreement share r1 - r2",
    "ex_diff": "exemplar votes r1 - r2 (20 delivered)",
    "ex_r1": "exemplar votes for r1",
    "ex_r2": "exemplar votes for r2",
    "ex_top_is_r2": "exemplar-vote winner is r2",
    "same_scenario": "r1 and r2 share the scenario",
    "scen_r1_te": "r1 scenario positive rate (cross-fitted)",
    "efs": "entity-free share of the 20 exemplars",
    "twin_dis": "twin picked a different intent",
}
#: model-visible today = the Solver's request carries it (note, block order, exemplars with labels)
MODEL_VISIBLE = {"note_n": "yes", "margin_b": "no (order only)", "r1_off_block_top": "yes (block order)",
                 "agr_diff": "no (pinned table)", "ex_diff": "yes", "ex_r1": "yes", "ex_r2": "yes",
                 "ex_top_is_r2": "yes", "same_scenario": "yes", "scen_r1_te": "yes (label)", "efs": "yes",
                 "twin_dis": "no (needs a second sample)"}


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


# ---------------------------------------------------------------------------
# pure functions (unit-tested on fakes)


def dedupe(ids) -> list:
    return list(dict.fromkeys(i for i in ids if isinstance(i, str) and i))


def rank_of(order, item):
    for i, x in enumerate(order):
        if x == item:
            return i + 1
    return None


def scenario_of(intent):
    return None if not intent else str(intent).split("_", 1)[0]


def split_half(utterance_id: str) -> int:
    """The supply-abstention / block-depth reads' utterance half (sha256 of the utterance id, mod 2)."""
    return int(hashlib.sha256(str(utterance_id).encode("utf-8")).hexdigest(), 16) % 2


def auc(scores, labels):
    """P(score of a positive > score of a negative), ties one half. ``None`` if degenerate."""
    import numpy as np

    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=bool)
    pos, neg = s[y], np.sort(s[~y])
    if len(pos) == 0 or len(neg) == 0:
        return None
    lo = np.searchsorted(neg, pos, side="left")
    hi = np.searchsorted(neg, pos, side="right")
    return float((lo + 0.5 * (hi - lo)).sum() / (len(pos) * len(neg)))


def boot_auc(scores, labels, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> list:
    """Row-bootstrap percentile CI95 of the AUC (draws with a degenerate class are skipped)."""
    import numpy as np

    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=bool)
    n = len(s)
    if n == 0 or y.all() or (~y).all():
        return [None, None]
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        a = auc(s[idx], y[idx])
        if a is not None:
            vals.append(a)
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


def classify(note: list, pick, gold: str) -> dict:
    """Decision classes of ONE row.

    ``gold_rank``: gold's rank on the note (None if absent). ``pick_rank``: the pick's rank on the
    note (None if off the note or unparsed). ``decision``: True when the row is in the decision
    population (note of >= 2 candidates and the Solver kept note rank 1). ``label``: 1 = positive
    (gold at note rank 2 or 3: a re-decision could flip it), 0 = negative (gold at rank 1: a
    re-decision can only cost), None = gold off the note or deeper (cost only).
    ``ceiling``: gold at note rank 2/3 and the pick is wrong (the oracle's flippable rows).
    """
    gr = rank_of(note, gold)
    pr = rank_of(note, pick) if pick is not None else None
    decision = len(note) >= 2 and pr == 1
    label = None
    if decision:
        label = 1 if gr in (2, 3) else 0 if gr == 1 else None
    return {"gold_rank": gr, "pick_rank": pr, "decision": decision, "label": label,
            "correct": pick is not None and pick == gold,
            "ceiling": gr in (2, 3) and not (pick is not None and pick == gold)}


def score_margin(order: list, scores: list, a: str, b: str):
    """Fused-score margin s(a) - s(b); an intent outside the recalled list takes the last score."""
    if not order:
        return None
    floor = scores[-1]
    sa = scores[order.index(a)] if a in order else floor
    sb = scores[order.index(b)] if b in order else floor
    return sa - sb


def target_encode(rows: list, key: str, half_key: str = "half", label_key: str = "label", prior_n: float = 5.0) -> list:
    """Cross-fitted target encoding: each row gets the smoothed positive rate of its ``key`` value
    measured on the OTHER half only."""
    out = []
    stats = {h: Counter() for h in (0, 1)}
    tot = {h: Counter() for h in (0, 1)}
    for r in rows:
        stats[r[half_key]][r[key]] += int(r[label_key] == 1)
        tot[r[half_key]][r[key]] += 1
    base = {h: (sum(stats[h].values()) / max(1, sum(tot[h].values()))) for h in (0, 1)}
    for r in rows:
        o = 1 - r[half_key]
        k, n = stats[o][r[key]], tot[o][r[key]]
        out.append((k + prior_n * base[o]) / (n + prior_n))
    return out


def target_encode_apply(train_rows: list, rows: list, key: str, prior_n: float = 5.0) -> list:
    """Encoding for rows outside the labelled set: the smoothed positive rate of ``key`` on the
    OTHER utterance half of ``train_rows`` (the same cross-fit as :func:`target_encode`)."""
    stats = {h: Counter() for h in (0, 1)}
    tot = {h: Counter() for h in (0, 1)}
    for r in train_rows:
        stats[r["half"]][r[key]] += int(r["label"] == 1)
        tot[r["half"]][r[key]] += 1
    base = {h: (sum(stats[h].values()) / max(1, sum(tot[h].values()))) for h in (0, 1)}
    out = []
    for r in rows:
        o = 1 - r["half"]
        out.append((stats[o][r[key]] + prior_n * base[o]) / (tot[o][r[key]] + prior_n))
    return out


def evidence_follow(rows: list, source: str) -> dict:
    """Counterfactual (NOT a runtime rule; directive 206 bars a system-applied swap): on the rows
    where the evidence's favourite among the note candidates is not the kept r1 (``ex``: exemplar
    votes; ``agr``: agreement share; ties keep r1), how often is the evidence's pick gold versus r1?
    This is the upper bound of what the top-2 evidence pack could convey if followed blindly."""
    out = Counter()
    for r in rows:
        cands = r.get("cand_" + source)
        if not cands:
            continue
        best = max(cands, key=lambda t: (t[1], -t[2]))
        if best[2] == 1:
            continue
        out["evidence_disagrees_with_r1"] += 1
        out["evidence_pick_is_gold"] += int(best[0] == r["gold"])
        out["r1_is_gold"] += int(r["gold_rank"] == 1)
        out["neither"] += int(best[0] != r["gold"] and r["gold_rank"] != 1)
    out["net_rows_if_followed"] = out["evidence_pick_is_gold"] - out["r1_is_gold"]
    return dict(sorted(out.items()))


def fit_logistic(X, y, ridge: float = 1e-3, iters: int = 50):
    """Newton-Raphson logistic regression with a small ridge; returns (w, mu, sd) with standardising."""
    import numpy as np

    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-Z @ w))
        g = Z.T @ (p - y) + ridge * np.r_[0.0, w[1:]]
        H = (Z * (p * (1 - p))[:, None]).T @ Z + ridge * np.eye(len(w))
        step = np.linalg.solve(H, g)
        w = w - step
        if np.max(np.abs(step)) < 1e-9:
            break
    return w, mu, sd


def predict_logistic(model, X):
    import numpy as np

    w, mu, sd = model
    X = np.asarray(X, dtype=float)
    Z = np.hstack([np.ones((len(X), 1)), (X - mu) / sd])
    return 1.0 / (1.0 + np.exp(-Z @ w))


def f1_threshold(p, y):
    """Threshold on scores ``p`` maximising F1 of the positive class (ties: the higher threshold)."""
    best = (None, -1.0)
    for t in sorted(set(p), reverse=True):
        tp = sum(1 for a, b in zip(p, y) if a >= t and b == 1)
        fp = sum(1 for a, b in zip(p, y) if a >= t and b == 0)
        fn = sum(1 for a, b in zip(p, y) if a < t and b == 1)
        f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
        if f1 > best[1] + 1e-12:
            best = (t, f1)
    return best[0]


def crossfit_pair_rule(rows: list, signals: list, cost_rows: list = ()) -> dict:
    """Best two-signal logistic rule under cross-fit by utterance halves.

    For each half h: every pair of ``signals`` is fitted on h and ranked by its in-half AUC; the best
    pair's model and its in-half F1 threshold are applied to the other half. Out-of-half scores of
    both halves are pooled for the operating points (TP / FP at the F1 threshold and at fixed call
    rates, the call-rate threshold also set in-half)."""
    out = {"halves": {}, "operating": {}}
    oo_scores, oo_labels, oo_trig = [], [], []
    rate_trig = {r: [] for r in CALL_RATES}
    cost_trig = {"f1_threshold": 0, **{f"call_rate_{r:.2f}": 0 for r in CALL_RATES}}
    for h in (0, 1):
        own = [r for r in rows if r["half"] == h]
        other = [r for r in rows if r["half"] != h]
        if not own or not other or len({r["label"] for r in own}) < 2:
            return {"error": "degenerate half"}
        best = None
        for a, b in itertools.combinations(signals, 2):
            X = [[r[a], r[b]] for r in own]
            y = [r["label"] for r in own]
            model = fit_logistic(X, y)
            ain = auc(list(predict_logistic(model, X)), y)
            if ain is not None and (best is None or ain > best[0] + 1e-12):
                best = (ain, (a, b), model)
        ain, pair, model = best
        p_own = list(predict_logistic(model, [[r[pair[0]], r[pair[1]]] for r in own]))
        t = f1_threshold(p_own, [r["label"] for r in own])
        p_oth = list(predict_logistic(model, [[r[pair[0]], r[pair[1]]] for r in other]))
        y_oth = [r["label"] for r in other]
        out["halves"][str(h)] = {"pair": list(pair), "in_half_auc": round(ain, 4),
                                  "applied_to_half": 1 - h, "out_of_half_auc": None if auc(p_oth, y_oth) is None else round(auc(p_oth, y_oth), 4),
                                  "coef_standardised": [round(float(x), 4) for x in model[0]]}
        oo_scores += p_oth
        oo_labels += y_oth
        oo_trig += [p >= t for p in p_oth]
        cost_oth = [r for r in cost_rows if r["half"] != h]
        p_cost = list(predict_logistic(model, [[r[pair[0]], r[pair[1]]] for r in cost_oth])) if cost_oth else []
        cost_trig["f1_threshold"] += sum(1 for p in p_cost if p >= t)
        srt = sorted(p_own, reverse=True)
        for rate in CALL_RATES:
            k = max(1, int(round(rate * len(srt))))
            thr = srt[k - 1]
            rate_trig[rate] += [p >= thr for p in p_oth]
            cost_trig[f"call_rate_{rate:.2f}"] += sum(1 for p in p_cost if p >= thr)
    out["out_of_half_auc_pooled_scores"] = None if auc(oo_scores, oo_labels) is None else round(auc(oo_scores, oo_labels), 4)

    def op(trig, cost):
        tp = sum(1 for t, y in zip(trig, oo_labels) if t and y == 1)
        fp = sum(1 for t, y in zip(trig, oo_labels) if t and y == 0)
        called = tp + fp + cost
        return {"called": called, "tp": tp, "fp": fp, "called_cost_rows": cost,
                "precision": round(tp / called, 4) if called else None,
                "precision_excl_cost_rows": round(tp / (tp + fp), 4) if tp + fp else None,
                "recall": round(tp / max(1, sum(1 for y in oo_labels if y == 1)), 4)}
    out["operating"]["f1_threshold"] = op(oo_trig, cost_trig["f1_threshold"])
    for rate in CALL_RATES:
        out["operating"][f"call_rate_{rate:.2f}"] = op(rate_trig[rate], cost_trig[f"call_rate_{rate:.2f}"])
    out["rows"] = len(oo_labels)
    out["positives"] = sum(1 for y in oo_labels if y == 1)
    return out


def expected_rows(tp: int, fp: int, conversion, harm) -> float | None:
    """Expected net intent rows of re-deciding on the called rows at a MEASURED conversion (share of
    called positives flipped to gold) and harm (share of called negatives flipped away)."""
    if conversion is None or harm is None:
        return None
    return tp * conversion - fp * harm


def rows_for_pp(pp: float, n: int = ROWS) -> float:
    return pp * n / 100.0


def precision_needed(positives: int, recall: float, conversion: float, harm: float, need_rows: float):
    """Smallest decision precision at which calling on ``recall`` of the ``positives`` yields
    ``need_rows`` net rows at the given conversion and harm; ``None`` when unreachable even at
    precision 1 (TP x conversion < need)."""
    tp = positives * recall
    gain = tp * conversion
    if gain < need_rows:
        return None
    if harm <= 0:
        return 0.0
    fp_max = (gain - need_rows) / harm
    return tp / (tp + fp_max)


# ---------------------------------------------------------------------------
# I/O


def build(args) -> dict:
    import numpy as np

    from speech_aware_evidence_acquisition.data.lock import load_lock
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot, QueryState
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        _provider_factory, load_phase_supply_specs, load_sealed_agreement, load_sealed_segment_vectors,
        load_sealed_vectors)
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

    BR = import_path(REPO_ROOT / "scripts/analysis/slurp_perception_branch_read.py", "slurp_perception_branch_read")
    NG = import_path(REPO_ROOT / "scripts/analysis/slurp_node_gain_ledger.py", "slurp_node_gain_ledger")
    ES, GP = NG.ES, NG.GP
    data_root = Path(args.data_root)
    lock = load_lock(Path(args.lock))
    records = load_slurp_split(lock, data_root, "train", workers=4)
    gold = {r.sample_id: r.intent for r in records}
    utt = {r.sample_id: r.utterance_id for r in records}
    del records
    files = {}
    checks = Counter()

    def parse_pick(text):
        sc, ac, _e, ok = parse_slu_response(text or "")
        return f"{sc}_{ac}" if ok and sc is not None and ac is not None else None

    # ---- exemplar pool (intent label + entity-free flag only)
    pool = GP.load_exemplar_pool(data_root, ES.EX_SNAPSHOT)
    files[pool["relpath"]] = pool["sha256"]
    ex_intent = {k: v["intent"] for k, v in pool["values"].items()}
    ex_empty = {k: not v["fillers"] for k, v in pool["values"].items()}
    del pool

    def load_phases(run_id, attempt):
        path = data_root / "runs" / run_id / attempt / f"{run_id}.phases.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        files[str(path.relative_to(data_root))] = digest(path)
        rows = {}
        for res in doc["phases"][0]["results"]:
            note, s1 = [], None
            for st in res.get("agent_states") or ():
                kind = st.get("state_kind")
                if kind == "phase:perception" and not note:
                    try:
                        payload = json.loads(st.get("content") or "")
                        note = dedupe(str(c.get("intent_id")) for c in payload.get("candidates") or ())
                    except (ValueError, AttributeError, TypeError):
                        note = []
                elif kind == "phase:solver" and s1 is None:
                    s1 = parse_pick(st.get("content"))
                    s1 = s1 if s1 is not None else "__unparsed__"
            ex = []
            for w in res.get("waves") or ():
                sel = (w.get("fusion_decision") or {}).get("selected_value_ids") or []
                if any(v.startswith(EX_PREFIX) for v in sel):
                    ex = [v.split(EX_PREFIX, 1)[-1] for v in sel if v.startswith(EX_PREFIX)]
                    break
            block = [v.split(IB_FACET_MARK, 1)[-1] for v in (res.get("initial_query_state") or {}).get("retrieved_value_ids") or ()
                     if IB_FACET_MARK in v]
            rows[res["sample_id"]] = {"note": note, "s1": None if s1 == "__unparsed__" else s1, "ex": ex, "block": block}
        del doc
        return rows

    def load_first_visit(run_id, attempt, arm):
        path = data_root / "runs" / run_id / attempt / "supply-variants" / f"arm-{arm}-first-visit-outputs.jsonl"
        files[str(path.relative_to(data_root))] = digest(path)
        picks = {}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    picks[r["sample_id"]] = parse_pick(r.get("text"))
        return picks

    def load_col_scores(run_id, attempt, arm):
        path = data_root / "runs" / run_id / attempt / "supply-variants" / f"arm-{arm}-{SCORER}-scores.json"
        files[str(path.relative_to(data_root))] = digest(path)
        block = json.loads(path.read_text(encoding="utf-8"))[SCORER]
        return {str(s["sample_id"]): bool(s["scenario_action_exact"] >= 1.0) for s in block["per_sample"]}

    def load_branch_notes(run_id, attempt):
        path = data_root / "runs" / run_id / attempt / f"{run_id}.outputs.jsonl"
        files[str(path.relative_to(data_root))] = digest(path)
        out = {}
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    row = json.loads(line)
                    rec = row["native_episode_receipt"]["perception_branches"]
                    out[row["sample_id"]] = {b["branch_id"]: {
                        "note": list(BR.branch_candidates(b)),
                        "ex": [v.split(EX_PREFIX, 1)[-1] for v in b.get("candidate_supply_value_ids") or () if v.startswith(EX_PREFIX)],
                        "block": [v.split(IB_FACET_MARK, 1)[-1] for v in b.get("supplied_value_ids") or () if IB_FACET_MARK in v],
                    } for b in rec["branches"]}
        return out

    # ---- retrieval: fused scores through the production constructor
    def base_spec(cfg_rel):
        cfg = json.loads((REPO_ROOT / cfg_rel).read_text(encoding="utf-8"))
        files["repo:" + cfg_rel] = digest(REPO_ROOT / cfg_rel)
        store = cfg["knowledge_stores"]["intent-boundaries"]
        spec = load_phase_supply_specs({"phase_supply": store["phase_supply"]}, default_phase_program(cfg["policy"]))["perception"]
        return spec, store

    spec_a, store_a = base_spec(CFG["A"])
    spec_c, _ = base_spec(CFG["A_cent"])
    spec_b, _ = base_spec(CFG["B"])
    snap = KnowledgeSnapshot.from_frozen_json(json.loads((data_root / store_a["snapshot"]["relpath"]).read_text(encoding="utf-8")))
    if snap.content_hash() != store_a["snapshot"]["sha256"]:
        raise ReadError("boundary snapshot pin mismatch")
    files[store_a["snapshot"]["relpath"]] = store_a["snapshot"]["sha256"]
    facet_ids = sorted(f.facet_id for f in snap.facets)

    def fold_inputs(spec):
        q = load_sealed_segment_vectors(data_root / spec.query_source["relpath"], expected_sha256=spec.query_source["sha256"],
                                        dimensions=spec.dimensions)
        agr = load_sealed_agreement(data_root / spec.agreement_source["relpath"], expected_sha256=spec.agreement_source["sha256"],
                                    dimension="agreement:exemplar-intent", facet_ids=facet_ids)
        files[spec.query_source["relpath"]] = spec.query_source["sha256"]
        files[spec.agreement_source["relpath"]] = spec.agreement_source["sha256"]
        return q, agr

    def fused(spec, facet_src, qvec, agr, ids):
        s = replace(spec, facet_source=facet_src)
        fvec = load_sealed_vectors(data_root / facet_src["relpath"], expected_sha256=facet_src["sha256"], dimensions=s.dimensions)
        files[facet_src["relpath"]] = facet_src["sha256"]
        factory = _provider_factory(s, snapshot=snap, snapshot_sha256=snap.content_hash(), facet_vectors=fvec,
                                    provider_for_phase=None, agreement_scores=agr)
        out = {}
        for sid in ids:
            state = QueryState(query_id=f"solver-decision-oracle:perception:{sid}", query_sample_id=sid,
                               speech_packet_id=f"solver-decision-oracle:{sid}", speech_packet_sha256="0" * 64,
                               use_split_identity_hash="0" * 64).validate()
            provider = factory()
            rk = provider.candidates({"query_state": state, "query_segments": qvec[sid].segments}, k=s.k)
            rr = provider.last_rank_result()
            dec = provider.fuse([rk], k=s.k, policy_id=s.fuse_policy)
            out[sid] = {"order": [str(c.facet_id).split(IB_FACET_MARK, 1)[-1] for c in rr.candidates],
                        "scores": [float(c.score) for c in rr.candidates],
                        "block": [str(v).split(IB_FACET_MARK, 1)[-1] for v in dec.selected_value_ids]}
        return out

    qa, agr_a = fold_inputs(spec_a)
    qb, agr_b = fold_inputs(spec_b)
    if spec_c.query_source["sha256"] != spec_a.query_source["sha256"] or spec_c.agreement_source["sha256"] != spec_a.agreement_source["sha256"]:
        raise ReadError("COMP-1b query / agreement inputs differ from AGREE's")

    # ---- per pool rows
    pools_rows = {}
    fused_cache = {}
    for name, (fold, key, run_id, attempt, kind, a_arm, t_arm) in POOLS.items():
        ph = load_phases(run_id, attempt)
        ids = sorted(ph)
        if len(ids) != ROWS:
            raise ReadError(f"{name}: roster is not 1,080 rows")
        ck = (fold, key)
        if ck not in fused_cache:
            spec, src = {("A", "desc_agree"): (spec_a, spec_a.facet_source), ("A", "cent_agree"): (spec_a, spec_c.facet_source),
                         ("B", "desc_agree"): (spec_b, spec_b.facet_source)}[ck]
            q, agr = (qa, agr_a) if fold == "A" else (qb, agr_b)
            fused_cache[ck] = fused(spec, src, q, agr, ids)
        F = fused_cache[ck]
        agr = agr_a if fold == "A" else agr_b
        if sorted(F) != ids:
            raise ReadError(f"{name}: fused roster differs")
        notes, picks, twin_picks, twin_notes = {}, {}, {}, {}
        if kind == "phases":
            for s in ids:
                notes[s], picks[s] = ph[s]["note"], ph[s]["s1"]
            if t_arm is not None:
                tw = load_phases(*t_arm)
                for s in ids:
                    twin_picks[s], twin_notes[s] = tw[s]["s1"], tw[s]["note"]
                del tw
        elif kind == "columns":
            pa = load_first_visit(run_id, attempt, a_arm)
            pt = load_first_visit(run_id, attempt, t_arm)
            sa = load_col_scores(run_id, attempt, a_arm)
            st = load_col_scores(run_id, attempt, t_arm)
            for s in ids:
                notes[s], picks[s], twin_picks[s], twin_notes[s] = ph[s]["note"], pa.get(s), pt.get(s), ph[s]["note"]
                checks[f"{name}_a_pick_parse_agrees_with_column_score"] += int((pa.get(s) == gold[s]) == sa[s])
                checks[f"{name}_t_pick_parse_agrees_with_column_score"] += int((pt.get(s) == gold[s]) == st[s])
                checks[f"{name}_a_first_visit_equals_sealed_s1"] += int(pa.get(s) == ph[s]["s1"])
        else:
            bn = load_branch_notes(run_id, attempt)
            pa = load_first_visit(run_id, attempt, a_arm)
            pt = load_first_visit(run_id, attempt, t_arm)
            sa = load_col_scores(run_id, attempt, a_arm)
            st = load_col_scores(run_id, attempt, t_arm)
            for s in ids:
                notes[s], picks[s] = bn[s][a_arm]["note"], pa.get(s)
                twin_picks[s], twin_notes[s] = pt.get(s), bn[s][t_arm]["note"]
                checks[f"{name}_a_pick_parse_agrees_with_column_score"] += int((pa.get(s) == gold[s]) == sa[s])
                checks[f"{name}_t_pick_parse_agrees_with_column_score"] += int((pt.get(s) == gold[s]) == st[s])
                if ph[s]["note"]:
                    checks[f"{name}_a_branch_note_equals_sealed_perception_note"] += int(bn[s][a_arm]["note"] == ph[s]["note"])
                if ph[s]["ex"]:
                    checks[f"{name}_a_branch_exemplars_equal_sealed_wave"] += int(sorted(bn[s][a_arm]["ex"]) == sorted(ph[s]["ex"]))
                # the branch receipt is the Solver's own supply: it replaces the (possibly absent) phase copy
                ph[s]["ex"], ph[s]["block"] = bn[s][a_arm]["ex"], bn[s][a_arm]["block"]
        rows = []
        for s in ids:
            note, pick, g = notes[s], picks[s], gold[s]
            checks[f"{name}_recomputed_block_equals_sealed_block"] += int(F[s]["block"] == ph[s]["block"])
            c = classify(note, pick, g)
            ex = ph[s]["ex"]
            votes = Counter(ex_intent[k] for k in ex if k in ex_intent)
            checks[f"{name}_exemplar_keys_unresolved"] += sum(1 for k in ex if k not in ex_intent)
            checks[f"{name}_exemplar_width_20"] += int(len(ex) == 20)
            shares = {str(f).split(IB_FACET_MARK, 1)[-1]: float(v) for f, v in (agr.get(s) or {}).items()}
            if note and ex:
                checks[f"{name}_note_rows_agreement_argmax_equals_vote_argmax"] += int(
                    max(note[:3], key=lambda c_: (shares.get(c_, 0.0), -note.index(c_)))
                    == max(note[:3], key=lambda c_: (votes.get(c_, 0), -note.index(c_))))
                checks[f"{name}_note_rows"] += 1
            r = {"sid": s, "half": split_half(utt[s]), **c, "note_n": len(note), "pick_parsed": pick is not None,
                 "twin": s in twin_picks}
            if len(note) >= 2:
                r1, r2 = note[0], note[1]
                top = votes.most_common()
                r.update({
                    "margin_b": score_margin(F[s]["order"], F[s]["scores"], r1, r2),
                    "r1_off_block_top": int(bool(F[s]["block"]) and r1 != F[s]["block"][0]),
                    "agr_diff": shares.get(r1, 0.0) - shares.get(r2, 0.0),
                    "ex_r1": votes.get(r1, 0), "ex_r2": votes.get(r2, 0),
                    "ex_diff": votes.get(r1, 0) - votes.get(r2, 0),
                    "ex_top_is_r2": int(bool(top) and votes.get(r2, 0) > 0 and all(votes.get(r2, 0) > v for i, v in top if i != r2)),
                    "same_scenario": int(scenario_of(r1) == scenario_of(r2)),
                    "scen_r1": scenario_of(r1),
                    "efs": (sum(1 for k in ex if ex_empty.get(k)) / len(ex)) if ex else 0.0,
                    "r1_missing_from_fused": int(r1 not in F[s]["order"]), "r2_missing_from_fused": int(r2 not in F[s]["order"]),
                    "gold": g,
                    "cand_ex": [(c_, votes.get(c_, 0), i + 1) for i, c_ in enumerate(note[:3])],
                    "cand_agr": [(c_, shares.get(c_, 0.0), i + 1) for i, c_ in enumerate(note[:3])],
                })
            if s in twin_picks:
                tp_ = twin_picks[s]
                r.update({"twin_dis": int(tp_ != pick), "twin_correct": tp_ is not None and tp_ == g,
                          "twin_pick_rank_on_a_note": rank_of(note, tp_) if tp_ is not None else None,
                          "twin_note_equal": int(twin_notes[s] == note)})
            rows.append(r)
        pools_rows[name] = {"rows": rows, "kind": kind, "fold": fold, "key": key, "twin": t_arm is not None}
        del ph

    # ---- analysis per pool
    report_pools = {}
    for name, P in pools_rows.items():
        rows = P["rows"]
        tab = Counter()
        for r in rows:
            gk = "absent" if r["gold_rank"] is None else str(r["gold_rank"]) if r["gold_rank"] <= 3 else "4+"
            pk = "unparsed" if not r["pick_parsed"] else ("off note" if r["pick_rank"] is None else f"r{r['pick_rank']}")
            tab[(gk, pk)] += 1
        conv = {}
        for gk in ("1", "2", "3", "absent"):
            sel = [r for r in rows if (("absent" if r["gold_rank"] is None else str(r["gold_rank"])) == gk)]
            conv[gk] = {"rows": len(sel), "correct": sum(r["correct"] for r in sel),
                        "pct": round(100.0 * sum(r["correct"] for r in sel) / len(sel), 2) if sel else None}
        ceiling = [r for r in rows if r["ceiling"]]
        dec = [r for r in rows if r["decision"] and r["label"] is not None]
        dec_absent = [r for r in rows if r["decision"] and r["label"] is None]
        # cross-fitted scenario encoding
        te = target_encode(dec, "scen_r1")
        for r, v in zip(dec, te):
            r["scen_r1_te"] = v
        sigs = [s for s in SIGNALS if s != "twin_dis" or P["twin"]]
        none_counts = {sgn: sum(1 for r in dec if r.get(sgn) is None) for sgn in sigs}
        for sgn in sigs:
            present = [r[sgn] for r in dec if r.get(sgn) is not None]
            fill = float(np.median(present)) if present else 0.0
            for r in dec:
                if r.get(sgn) is None:
                    r[sgn] = fill
        labels = [r["label"] for r in dec]
        auc_tab = {}
        for sgn in sigs:
            x = [r[sgn] for r in dec]
            a = auc(x, labels)
            auc_tab[sgn] = {"auc": None if a is None else round(a, 4), "ci95": boot_auc(x, labels),
                            "median_pos": round(float(np.median([v for v, y in zip(x, labels) if y == 1])), 4) if any(labels) else None,
                            "median_neg": round(float(np.median([v for v, y in zip(x, labels) if y == 0])), 4)}
        # binary signal rates by class
        bin_rates = {}
        for sgn in ("r1_off_block_top", "ex_top_is_r2", "same_scenario", "twin_dis"):
            if sgn not in sigs:
                continue
            bin_rates[sgn] = {"pos_rate": round(sum(r[sgn] for r in dec if r["label"] == 1) / max(1, sum(labels)), 4),
                              "neg_rate": round(sum(r[sgn] for r in dec if r["label"] == 0) / max(1, len(labels) - sum(labels)), 4),
                              "absent_rate": round(sum(r.get(sgn, 0) for r in dec_absent) / max(1, len(dec_absent)), 4)}
        for sgn in sigs:
            present = [r[sgn] for r in dec_absent if r.get(sgn) is not None]
            fill = float(np.median(present)) if present else 0.0
            for r in dec_absent:
                if r.get(sgn) is None:
                    r[sgn] = fill
        te_cost = target_encode_apply(dec, dec_absent, "scen_r1")
        for r, v in zip(dec_absent, te_cost):
            r["scen_r1_te"] = v
        rule_all = crossfit_pair_rule(dec, sigs, dec_absent)
        rule_visible = crossfit_pair_rule(dec, [s for s in sigs if MODEL_VISIBLE[s].startswith("yes")], dec_absent)
        follow = {"exemplar_votes": evidence_follow(dec + dec_absent, "ex"), "agreement_share": evidence_follow(dec + dec_absent, "agr")}
        # twin measured rates
        tw = None
        if P["twin"]:
            pos = [r for r in dec if r["label"] == 1]
            neg = [r for r in dec if r["label"] == 0]
            dis = [r for r in dec + dec_absent if r["twin_dis"]]
            tw = {"kind": TWIN_KIND[P["kind"]],
                  "conversion_twin_right_given_positive": round(sum(r["twin_correct"] for r in pos) / max(1, len(pos)), 4),
                  "conversion_rows": [sum(r["twin_correct"] for r in pos), len(pos)],
                  "harm_twin_wrong_given_negative": round(sum(not r["twin_correct"] for r in neg) / max(1, len(neg)), 4),
                  "harm_rows": [sum(not r["twin_correct"] for r in neg), len(neg)],
                  "twin_disagrees_rows": len(dis),
                  "twin_disagrees_on_positive": sum(1 for r in pos if r["twin_dis"]),
                  "twin_disagrees_on_positive_and_twin_right": sum(1 for r in pos if r["twin_dis"] and r["twin_correct"]),
                  "twin_disagrees_on_positive_twin_picked_a_note_rank2": sum(1 for r in pos if r["twin_dis"] and r["twin_pick_rank_on_a_note"] == 2),
                  "twin_disagrees_on_negative": sum(1 for r in neg if r["twin_dis"]),
                  "twin_disagrees_on_absent": sum(1 for r in dec_absent if r["twin_dis"]),
                  "twin_note_equal_rows": sum(r.get("twin_note_equal", 0) for r in rows),
                  "p_twin_right_given_disagree_in_decision_set": round(sum(1 for r in dec if r["twin_dis"] and r["twin_correct"]) / max(1, sum(1 for r in dec if r["twin_dis"])), 4)}
        report_pools[name] = {
            "fold": P["fold"], "key": P["key"], "kind": P["kind"], "twin": TWIN_KIND[P["kind"]] if P["twin"] else None,
            "gold_rank_x_pick": {f"{g} / {p}": n for (g, p), n in sorted(tab.items())},
            "conversion_by_gold_note_rank": conv,
            "note_size_hist": dict(sorted(Counter(str(r["note_n"]) for r in rows).items())),
            "ceiling_rows": len(ceiling), "ceiling_pp": round(100.0 * len(ceiling) / ROWS, 3),
            "ceiling_rows_by_gold_rank": dict(sorted(Counter(str(r["gold_rank"]) for r in ceiling).items())),
            "ceiling_rows_solver_kept_r1": sum(1 for r in ceiling if r["pick_rank"] == 1),
            "decision_set": {"rows": len(dec), "positives": sum(labels), "negatives": len(labels) - sum(labels),
                             "absent_or_deep_cost_rows": len(dec_absent),
                             "base_rate_b": round(sum(labels) / max(1, len(dec) + len(dec_absent)), 4)},
            "auc": auc_tab, "binary_rates": bin_rates, "evidence_follow_counterfactual": follow,
            "rule_all_signals": rule_all, "rule_model_visible_signals": rule_visible,
            "twin": tw,
            "signal_none_rows_filled_with_median": none_counts,
            "fused_missing": {"r1": sum(r.get("r1_missing_from_fused", 0) for r in dec), "r2": sum(r.get("r2_missing_from_fused", 0) for r in dec)},
        }
    # expected flips at measured rates: each pool's own twin where present, else the Fold-A same-flight Solver twins pooled
    solver_twin = [report_pools[p]["twin"] for p in ("wsv1", "w4sv")]
    pooled_c = sum(t["conversion_rows"][0] for t in solver_twin) / max(1, sum(t["conversion_rows"][1] for t in solver_twin))
    pooled_h = sum(t["harm_rows"][0] for t in solver_twin) / max(1, sum(t["harm_rows"][1] for t in solver_twin))
    need = rows_for_pp(INTENT_FLOOR_PP)
    agree_tw = report_pools["agree"]["twin"]
    anchors = {
        "same_flight_solver_twin_pooled": (pooled_c, pooled_h),
        "cross_flight_replicate_agree_vs_wave_aa": (agree_tw["conversion_twin_right_given_positive"], agree_tw["harm_twin_wrong_given_negative"]),
        "revtfrl_reviewer_routed_second_solver": (REVTFRL_CONVERSION[0] / REVTFRL_CONVERSION[1], REVTFRL_HARM[0] / REVTFRL_HARM[1]),
    }
    for name, rp in report_pools.items():
        pos = rp["ceiling_rows"]
        rp["anchored"] = {}
        for an, (c_, h_) in anchors.items():
            ops = rp["rule_all_signals"].get("operating", {})
            rp["anchored"][an] = {
                "conversion": round(c_, 4), "harm": round(h_, 4),
                "perfect_decision_rows": round(pos * c_, 2), "perfect_decision_pp": round(100.0 * pos * c_ / ROWS, 3),
                "best_rule_rows": {k: round(expected_rows(v["tp"], v["fp"], c_, h_), 2) for k, v in ops.items()},
                "precision_needed_for_floor": {f"recall_{r_:.1f}": (None if precision_needed(pos, r_, c_, h_, need) is None
                                                                    else round(precision_needed(pos, r_, c_, h_, need), 3))
                                               for r_ in (0.5, 0.7, 1.0)},
            }
    for name, rp in report_pools.items():
        c, h = (rp["twin"]["conversion_twin_right_given_positive"], rp["twin"]["harm_twin_wrong_given_negative"]) if rp["twin"] else (pooled_c, pooled_h)
        ev = {"conversion_used": round(c, 4), "harm_used": round(h, 4),
              "source": "own twin" if rp["twin"] else "Fold A same-flight Solver twins pooled (W-SV-1 + W4-SV)",
              "rows_needed_for_intent_floor": round(need, 2), "rows_needed_for_cross_flight_bar": round(rows_for_pp(CROSS_FLIGHT_BAR_PP), 2),
              "perfect_decision": {"flips_at_conversion_1": rp["ceiling_rows"],
                                   "expected_rows_at_measured_conversion": round(rp["ceiling_rows"] * c, 2)}}
        for rk in ("rule_all_signals", "rule_model_visible_signals"):
            rule = rp[rk]
            if "operating" not in rule:
                continue
            ev[rk] = {}
            for opk, opv in rule["operating"].items():
                e = expected_rows(opv["tp"], opv["fp"], c, h)
                ev[rk][opk] = {"tp": opv["tp"], "fp": opv["fp"], "precision": opv["precision"],
                               "expected_net_rows": None if e is None else round(e, 2),
                               "expected_net_pp": None if e is None else round(100.0 * e / ROWS, 3),
                               "conversion_needed_for_floor_at_zero_harm": round(need / opv["tp"], 4) if opv["tp"] else None}
        rp["expected"] = ev
    return {"read_id": READ_ID, "recipe": RECIPE, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "DESCRIPTIVE", "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "embedder": 0,
                                                  "gpu": 0, "network": 0, "official_scorer_subprocess": 0},
            "driver_sha256": digest(Path(__file__)), "boot": {"draws": BOOT_DRAWS, "seed": BOOT_SEED},
            "signals": {s: {"title": SIGNAL_TITLES[s], "model_visible_today": MODEL_VISIBLE[s]} for s in SIGNALS},
            "floors": {"intent_same_flight_pp": INTENT_FLOOR_PP, "cross_flight_bar_pp": CROSS_FLIGHT_BAR_PP},
            "pooled_solver_twin_rates": {"conversion": round(pooled_c, 4), "harm": round(pooled_h, 4)},
            "anchors": {k: [round(a, 4), round(b, 4)] for k, (a, b) in anchors.items()},
            "revtfrl_anchor_source": "docs/results/2026-09-28-slurp-revtfrl-1-fold-a-read.md section 4 (arm: INT-SHORTLIST 10/54 repairs, CORRECT 8/164 breaks)",
            "inputs": dict(sorted(files.items())), "checks": dict(sorted(checks.items())), "pools": report_pools}


def render(r: dict) -> str:
    parts = [f"# {READ_ID}", "", f"Generated `{r['generated_at']}`. DESCRIPTIVE; development numbers (decisions 28, 86).", "",
             "## checks", "", "```json", json.dumps(r["checks"], indent=2, sort_keys=True), "```", ""]
    parts += ["## Oracle ceiling and decision set", "",
              "| pool | fold | twin | ceiling rows | ceiling pp | kept r1 | decision rows | pos | neg | absent/deep | b |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for n, p in r["pools"].items():
        d = p["decision_set"]
        parts.append(f"| {n} | {p['fold']} | {p['twin'] or '-'} | {p['ceiling_rows']} | {p['ceiling_pp']} | {p['ceiling_rows_solver_kept_r1']} | "
                     f"{d['rows']} | {d['positives']} | {d['negatives']} | {d['absent_or_deep_cost_rows']} | {d['base_rate_b']} |")
    parts += ["", "## AUC (positive = gold at note rank 2/3 with the Solver keeping r1; negative = r1 right)", ""]
    sig = list(r["signals"])
    parts += ["| signal | " + " | ".join(r["pools"]) + " |", "| --- | " + " | ".join("---" for _ in r["pools"]) + " |"]
    for s in sig:
        cells = []
        for p in r["pools"].values():
            a = p["auc"].get(s)
            cells.append("-" if a is None or a["auc"] is None else f"{a['auc']:.3f} [{a['ci95'][0]:.2f}, {a['ci95'][1]:.2f}]")
        parts.append(f"| {s} | " + " | ".join(cells) + " |")
    parts += ["", "## Cross-fitted two-signal rules and expected rows", ""]
    for n, p in r["pools"].items():
        parts += [f"### {n}", "", "```json", json.dumps({"rule_all_signals": p["rule_all_signals"], "rule_model_visible_signals": p["rule_model_visible_signals"],
                                                          "twin": p["twin"], "expected": p["expected"], "anchored": p["anchored"],
                                                          "evidence_follow_counterfactual": p["evidence_follow_counterfactual"],
                                                          "binary_rates": p["binary_rates"],
                                                          "conversion_by_gold_note_rank": p["conversion_by_gold_note_rank"],
                                                          "gold_rank_x_pick": p["gold_rank_x_pick"]}, indent=2, sort_keys=True), "```", ""]
    return "\n".join(parts) + "\n"


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
    (out_dir / "content-sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
