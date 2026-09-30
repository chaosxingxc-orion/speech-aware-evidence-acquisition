#!/usr/bin/env python3
"""E5-1 supplement: the cross-fit two-signal TOOL-CALL DECISION rule, the perfect-repair ceiling and the
proposed E5-2 gate arithmetic (read row ``SAEA-SLURP-E5-TRANSCRIPT-CONSISTENCY-READ-V1``; owner decisions
201 and 206: instrument / oracle only; model-free).

The E5-1 driver (``e5_transcript_consistency_read.py``) reports one AUC per model-visible signal. This
supplement answers the coordinator's follow-up questions on the SAME inputs and the SAME definitions
(it imports the driver's functions; nothing is re-defined):

1. the perfect-repair ceiling: the official pooled SLU-F1 delta if every helpful entity (delivered value
   unsupported by the transcript, matched gold span contained) were replaced by its matched gold value
   -- an upper bound on what any verifying call could add on the delivered column (gold is used ONLY to
   bound, offline, scoring side);
2. the best two-signal rule under K-fold cross-fitting: inside each training fold every pair of
   model-visible features is fitted (two-feature L2 logistic regression, standardised) and the pair with
   the best training AUC is chosen; the held-out rows are scored by that fold's model; the pooled
   out-of-fold AUC and the precision at fixed call rates (top share of each held-out fold) are reported;
3. the same decision oracle under a wider label (helpful, or a MISSING gold span the transcript contains);
4. the proposed E5-2 gate (decision 206): base rate b of positive rows, call-rate band
   [max(0.01, 0.5 b), min(0.50, 4 b)], precision bars b + 0.10 and 2 b, evaluated at the band ends and
   at 10 % / 20 %.

Text discipline: ids never printed; only counts, rates, AUCs, pp, feature NAMES (signal and slot type
names) and hashes. Zero model, server, tokenizer, encoder, embedder, scorer-subprocess, network and GPU
contacts.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/e5_decision_oracle_supplement.py \\
        --params <tune out>/params.json --params-sha256 <sha> \\
        --arm SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1 \\
        --e4 SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1/attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA = "saea-slurp-e5-decision-oracle-supplement-v1"
FOLDS = 5
SEED = 20260929
RATES = (0.10, 0.20)
L2 = 1.0


def load_driver():
    name = "e5_transcript_consistency_read"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts/analysis/e5_transcript_consistency_read.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------- features


def feature_matrix(ids: list, signals: dict) -> tuple:
    """(names, {sid: [floats]}). Categorical signals become one-hot levels; a missing numeric value is
    imputed by the roster median and gets no indicator (the rows lacking a signal are counted)."""
    names, cols, missing = [], [], {}
    for name, values in sorted(signals.items()):
        sample = [values.get(s) for s in ids]
        present = [v for v in sample if v is not None]
        missing[name] = len(sample) - len(present)
        if present and all(isinstance(v, str) for v in present):
            for level in sorted(set(present)):
                names.append(f"{name}={level}")
                cols.append([1.0 if v == level else 0.0 for v in sample])
        else:
            fl = sorted(float(v) for v in present) or [0.0]
            med = fl[len(fl) // 2]
            names.append(name)
            cols.append([med if v is None else float(v) for v in sample])
    keep = [i for i, c in enumerate(cols) if len(set(c)) > 1]
    names = [names[i] for i in keep]
    rows = {sid: [cols[i][r] for i in keep] for r, sid in enumerate(ids)}
    return names, rows, missing


def fit_logit(x, y, iters: int = 25) -> tuple:
    """Two-feature L2 logistic regression by Newton steps on standardised inputs -> (mu, sd, w)."""
    import numpy as np

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mu = x.mean(axis=0)
    sd = np.maximum(x.std(axis=0), 1e-9)
    z = np.hstack([np.ones((len(x), 1)), (x - mu) / sd])
    w = np.zeros(z.shape[1])
    reg = np.eye(z.shape[1]) * L2
    reg[0, 0] = 0.0
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-np.clip(z @ w, -30, 30)))
        g = z.T @ (p - y) + reg @ w
        h = (z * (p * (1 - p))[:, None]).T @ z + reg + np.eye(z.shape[1]) * 1e-9
        w = w - np.linalg.solve(h, g)
    return mu, sd, w


def score(model: tuple, x) -> float:
    import numpy as np

    mu, sd, w = model
    return float(w[0] + np.dot(w[1:], (np.asarray(x, dtype=float) - mu) / sd))


def score_many(model: tuple, x) -> list:
    import numpy as np

    mu, sd, w = model
    return list(w[0] + ((np.asarray(x, dtype=float) - mu) / sd) @ w[1:])


def fast_auc(scores: list, labels: list) -> float | None:
    pairs = sorted(zip(scores, labels))
    pos = sum(labels)
    neg = len(labels) - pos
    if not pos or not neg:
        return None
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        avg = (i + j + 1) / 2.0
        rank_sum += avg * sum(1 for t in range(i, j) if pairs[t][1])
        i = j
    return (rank_sum - pos * (pos + 1) / 2.0) / (pos * neg)


def top_share(scores: list, labels: list, rate: float) -> tuple:
    """(called, helpful among called) for the top ceil(rate * n) scores; ties broken by list order."""
    n_call = max(1, math.ceil(rate * len(scores)))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:n_call]
    return n_call, sum(labels[i] for i in order)


def crossfit(ids: list, names: list, x: dict, labels: dict, rates: list) -> dict:
    rng = random.Random(SEED)
    pos = [s for s in ids if labels[s]]
    neg = [s for s in ids if not labels[s]]
    rng.shuffle(pos)
    rng.shuffle(neg)
    fold_of = {s: i % FOLDS for i, s in enumerate(pos)}
    fold_of.update({s: i % FOLDS for i, s in enumerate(neg)})
    oof, chosen, per_rate = {}, [], {r: [0, 0] for r in rates}
    for f in range(FOLDS):
        train = [s for s in ids if fold_of[s] != f]
        test = [s for s in ids if fold_of[s] == f]
        ytr = [int(labels[s]) for s in train]
        # screen pairs by the training AUC of the fitted two-feature model
        best = None
        for a, b in combinations(range(len(names)), 2):
            xtr = [[x[s][a], x[s][b]] for s in train]
            model = fit_logit(xtr, ytr, iters=8)
            auc_tr = fast_auc(score_many(model, xtr), ytr)
            if auc_tr is not None and (best is None or auc_tr > best[0]):
                best = (auc_tr, a, b, model)
        _, a, b, _ = best
        model = fit_logit([[x[s][a], x[s][b]] for s in train], ytr)
        chosen.append({"fold": f, "pair": [names[a], names[b]], "train_auc": round(best[0], 4)})
        sc = score_many(model, [[x[s][a], x[s][b]] for s in test])
        yt = [int(labels[s]) for s in test]
        for s, v in zip(test, sc):
            oof[s] = v
        for r in rates:
            n_call, hits = top_share(sc, yt, r)
            per_rate[r][0] += n_call
            per_rate[r][1] += hits
    ys = [int(labels[s]) for s in ids]
    return {"folds": FOLDS, "seed": SEED, "chosen": chosen,
            "oof_auc": round(fast_auc([oof[s] for s in ids], ys), 4),
            "precision_at_rate": {f"{r:.4f}": {"called": c, "helpful": h, "precision": round(h / c, 4) if c else None}
                                  for r, (c, h) in per_rate.items()}}


def single_signal_precision(ids: list, names: list, x: dict, labels: dict, rates: list) -> dict:
    """In-sample, orientation chosen by the full-roster AUC (an optimistic bound for one signal)."""
    ys = [int(labels[s]) for s in ids]
    out = {}
    for j, name in enumerate(names):
        sc = [x[s][j] for s in ids]
        a = fast_auc(sc, ys)
        if a is None:
            continue
        sign = 1.0 if a >= 0.5 else -1.0
        sc = [sign * v for v in sc]
        prec = {}
        for r in rates:
            c, h = top_share(sc, ys, r)
            prec[f"{r:.4f}"] = round(h / c, 4)
        out[name] = {"auc": round(a, 4), "oriented_auc": round(max(a, 1 - a), 4), "precision_at_rate": prec}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["oriented_auc"]))


# ---------------------------------------------------------------------------- ceiling


def perfect_repair(E5, ids, gold, pred, transcripts, near) -> tuple:
    """(column, repaired entity count, repaired missing count) where every helpful entity takes its
    matched gold value; a second column also adds every MISSING gold span the transcript contains."""
    fixed, both, n_fix, n_add = {}, {}, 0, 0
    for sid in ids:
        tx = transcripts.get(sid)
        usable = bool(tx and tx["status"] == "ok")
        states, _ = E5.gold_kinds(gold[sid], pred[sid])
        pred_to_gold = {pi: (gi, kind) for gi, (kind, pi) in states.items() if pi is not None}
        row = list(pred[sid])
        for pi, ent in enumerate(pred[sid]):
            verdict = E5.consistent(ent.filler, tx["canon"], near) if usable else None
            gk = pred_to_gold.get(pi)
            if verdict is False and gk and gk[1] != "EXACT" and \
                    E5.contiguous(E5.canon_tokens(gold[sid][gk[0]].filler), tx["canon"]):
                row[pi] = gold[sid][gk[0]]
                n_fix += 1
        fixed[sid] = tuple(row)
        extra = [g for gi, g in enumerate(gold[sid]) if usable and states.get(gi, ("MISSING", None))[0] == "MISSING"
                 and E5.contiguous(E5.canon_tokens(g.filler), tx["canon"])]
        n_add += len(extra)
        both[sid] = tuple(row) + tuple(extra)
    return fixed, both, n_fix, n_add


# ---------------------------------------------------------------------------- main


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--arm", required=True, help="RUN_ID/ATTEMPT of the primary Fold A arm")
    parser.add_argument("--e4", help="RUN_ID/ATTEMPT of E4-1 (its relisten disagreement signal)")
    parser.add_argument("--params", required=True)
    parser.add_argument("--params-sha256", required=True)
    parser.add_argument("--roster", default="fold-a", choices=("fold-a",))
    parser.add_argument("--draws", type=int, default=10_000)
    parser.add_argument("--label", default="read-fold-a-decision-supplement")
    parser.add_argument("--lock", default=None)
    parser.add_argument("--data-root", default=None)
    args = parser.parse_args(argv)
    E5 = load_driver()
    data_root = Path(args.data_root or E5.DEFAULT_DATA_ROOT)
    out = data_root / "analysis" / E5.READ_ID / args.label
    if out.exists() and any(out.iterdir()):
        print(f"REFUSED: {out} already holds files", file=sys.stderr)
        return 5
    raw = Path(args.params).read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.params_sha256:
        print("REFUSED: params.json differs from its pinned sha256", file=sys.stderr)
        return 1
    params = json.loads(raw)
    near = params.get("near_drop", False)
    transcripts, catalog = E5.load_catalog(data_root, args.roster)
    ids = sorted(transcripts)
    idset = set(ids)
    arm = E5.load_arm(data_root, args.arm, idset)
    gold = E5.load_gold(Path(args.lock or E5.DEFAULT_LOCK), data_root, idset)
    pred = arm["pred"]
    oracle = E5.decision_oracle(ids, gold, pred, transcripts, near=near)
    labels = {s: oracle["rows"][s]["helpful"] for s in ids}
    # the driver's signal set, built the same way
    signals = {"delivered_entity_count": {sid: len(pred[sid]) for sid in ids}}
    perception = E5.perception_signals(arm["directory"], arm["run_id"])
    if perception:
        signals["perception_candidate_list_length"] = {s: v[1] for s, v in perception.items() if s in idset}
        signals["note_parse_status"] = {s: v[0] for s, v in perception.items() if s in idset}
    for t in sorted({e.type for sid in ids for e in pred[sid]}):
        signals[f"delivered_type:{t}"] = {sid: float(any(e.type == t for e in pred[sid])) for sid in ids}
    share = E5.entity_free_share(arm["directory"], arm["run_id"], data_root)
    if share:
        signals["entity_free_exemplar_share"] = {s: v for s, v in share.items() if s in idset}
    if args.e4:
        d, rid = E5.run_dir(data_root, args.e4)
        signals["e4_relisten_disagreement"] = {
            s: v for s, v in E5.relisten_disagreement(d / f"{rid}.outputs.jsonl").items() if s in idset}
    names, x, missing = feature_matrix(ids, signals)
    n = len(ids)
    # ceiling
    base_counts = {s: E5.slu_counts(gold[s], pred[s]) for s in ids}
    fixed, both, n_fix, n_add = perfect_repair(E5, ids, gold, pred, transcripts, near)
    fixed_counts = {s: E5.slu_counts(gold[s], fixed[s]) for s in ids}
    both_counts = {s: E5.slu_counts(gold[s], both[s]) for s in ids}
    ceiling = {"delivered_slu_f1": round(E5.pooled_f1(E5.totals(ids, base_counts)), 4),
               "repair_helpful_entities": {"entities": n_fix,
                                           "delta_vs_delivered": E5.paired_delta(ids, base_counts, fixed_counts, draws=args.draws)},
               "repair_plus_add_contained_missing": {"entities": n_fix, "added": n_add,
                                                     "delta_vs_delivered": E5.paired_delta(ids, base_counts, both_counts, draws=args.draws)}}
    # the decision oracle under two labels: the driver's (a wrong delivered value a verifying call could repair)
    # and the wider one (that, or a MISSING gold span the transcript contains)
    label_sets = {"helpful": {s: bool(oracle["rows"][s]["helpful"]) for s in ids},
                  "helpful_or_contained_missing": {s: bool(oracle["rows"][s]["helpful"] or oracle["rows"][s]["helpful_missing"])
                                                   for s in ids}}
    decisions = {}
    for lname, labels in label_sets.items():
        b = sum(labels.values()) / n
        lo, hi = round(max(0.01, 0.5 * b), 4), round(min(0.50, 4 * b), 4)
        rates = sorted({lo, hi, *RATES})
        cf = crossfit(ids, names, x, labels, rates)
        single = single_signal_precision(ids, names, x, labels, rates)
        bars = {"b_plus_0.10": round(b + 0.10, 4), "2b": round(2 * b, 4)}
        gate = {"base_rate_b": round(b, 4), "positive_rows": sum(labels.values()), "rows": n,
                "call_rate_band": [lo, hi], "precision_bars": bars, "crossfit_two_signal": {}}
        for r in rates:
            p = cf["precision_at_rate"][f"{r:.4f}"]["precision"]
            gate["crossfit_two_signal"][f"{r:.4f}"] = {
                "in_band": lo <= r <= hi, "precision": p,
                "meets_b_plus_0.10": p is not None and p >= b + 0.10, "meets_2b": p is not None and p >= 2 * b}
        top = next(iter(single.items())) if single else None
        decisions[lname] = {"crossfit_two_signal_rule": cf, "single_signal_in_sample": single,
                            "best_single_signal": {"name": top[0], **top[1]} if top else None,
                            "e5_2_gate_proposed_206": gate}
    report = {"schema": SCHEMA, "read_id": E5.READ_ID, "generated_at": datetime.now(timezone.utc).isoformat(),
              "role": "INSTRUMENT / ORACLE (owner decisions 201 and 206): the ceiling and the decision rule bound a "
                      "core-initiated verifying call; neither is a runtime candidate",
              "catalog": catalog, "arm": {"run_id": arm["run_id"], "outputs": arm["outputs"]},
              "params": {**params, "sha256": args.params_sha256}, "oracle_counts": oracle["counts"],
              "features": {"count": len(names), "names": names, "rows_missing_by_signal": missing},
              "perfect_repair_ceiling": ceiling, "decision_oracle_by_label": decisions}
    out.mkdir(parents=True, exist_ok=True)
    (out / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
                                     encoding="utf-8", newline="\n")
    content = {"report.json": E5.sha256_file(out / "report.json")}
    (out / "content-sha256.json").write_text(json.dumps(content, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8", newline="\n")
    print(json.dumps({"out": str(out), "content_sha256": content, "ceiling": ceiling,
                      "decisions": {k: {"gate": v["e5_2_gate_proposed_206"], "crossfit": v["crossfit_two_signal_rule"],
                                        "best_single_signal": v["best_single_signal"]} for k, v in decisions.items()}},
                     sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
