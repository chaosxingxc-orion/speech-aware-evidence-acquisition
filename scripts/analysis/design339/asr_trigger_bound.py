#!/usr/bin/env python3
"""Owner ruling 339 design bound: a triggered (model-initiated) ASR tool at the Solver slot-value step of the v3.0 lock.

Model-free, read-only, CPU. Population: TRAIN Fold B, NX-T R2b delivering arm budget-3072 (the v3.0 lock form, n = 1,080;
train gold, scoring side only). Transcripts: the sealed E5-0 Whisper large-v3 Fold B catalog (re-hashed against its
receipt) and, as the perfect-ASR bound, the SLURP TRAIN reference sentence (governed train-material loader, in memory only).

Prints / persists only aggregates: counts, rates, pp, AUCs, slot TYPE names. No utterance, transcript, filler, model
output or reasoning text is printed or written. Never reads devel/test.

    python -B asr_trigger_bound.py --out bound339.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
GAP = Path(__file__).resolve().parent.parent / "gap_to_sota" / "gap_decomposition.py"
sys.path.insert(0, str(REPO / "src"))
sys.dont_write_bytecode = True


def imp(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


G = imp(GAP, "gapdec")
E5 = imp(REPO / "scripts/analysis/e5_transcript_consistency_read.py", "e5read")
S2 = imp(REPO / "scripts/analysis/slurp_s2a1_recall_ceiling.py", "s2a1")
from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items  # noqa: E402

VALUE_KINDS = ("FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE")
NAME_TYPES = {"business_name", "person", "place_name", "artist_name", "song_name", "audiobook_name", "podcast_name",
              "movie_name", "game_name", "playlist_name", "radio_name", "event_name", "relation"}
RATES = (0.05, 0.10, 0.20, 0.30, 0.50, 1.00)
UPTAKE = (0.457, 1.0)  # CONV measured P(correct | newly delivered) and perfect


def contained(value: str, canon: list) -> bool:
    return E5.contiguous(E5.canon_tokens(value), canon)


def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return None
    w = 0.0
    for p in pos:
        for q in neg:
            w += 1.0 if p > q else 0.5 if p == q else 0.0
    return round(w / (len(pos) * len(neg)), 4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--asr", type=Path, default=None, help="transcripts.jsonl of another pinned ASR (saea-asr339-transcript-row-v1); replaces the Whisper tokens")
    ap.add_argument("--union", action="store_true", help="with --asr: containment over Whisper OR the other ASR (two-tool ceiling)")
    args = ap.parse_args()
    lock = G.load_lock(G.LOCK)
    spec = G.POPS["FOLDB"]
    train = G.load_slurp_split(lock, G.DATA, "train", workers=4)
    gold_all = {}
    for r in train:
        G.guard(r.sample_id)
        gold_all[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                                 "ents": tuple(G.SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
    pop = G.load_pop("FOLDB", spec, gold_all)
    rows = pop["rows"]
    ids = sorted(rows)
    # completion tokens per node (trace COST stats only)
    d = G.DATA / "runs" / spec["run"] / spec["attempt"]
    toks, role_of = {}, {}
    with (d / f"{spec['run']}.trace.jsonl").open("rb") as fh:
        for raw in fh:
            head = raw[:40]
            if b'"USE"' not in head and b'"COST"' not in head:
                continue
            rec = json.loads(raw)
            key = str(rec.get("record_id", "")).split("/", 1)[0]
            pl = rec.get("payload") or {}
            if rec.get("channel") == "USE" and "use_agent_contact_id" in pl:
                role_of[key] = str(pl["use_agent_contact_id"])
            elif rec.get("channel") == "COST":
                toks[key] = int(pl.get("completion_tokens") or 0)
    bidx_of = {}
    with (d / f"{spec['run']}.outputs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                br = next(x for x in rec["native_episode_receipt"]["perception_branches"]["branches"] if x["branch_id"] == spec["branch"])
                bidx_of[str(rec["sample_id"])] = int(br["branch_index"])
    per = defaultdict(dict)
    for key, cid in role_of.items():
        _, role, bidx, sid = cid.split(":", 3)
        per[sid][(role, int(bidx))] = toks.get(key, 0)
    # transcripts: Whisper (E5-0 Fold B) and reference (perfect ASR)
    wtx, wfacts = E5.load_catalog(G.DATA, "fold-b")
    if set(wtx) != set(ids):
        raise SystemExit(f"roster mismatch: catalog {len(wtx)} vs run {len(ids)}; overlap {len(set(wtx) & set(ids))}")
    if args.asr is not None:
        alt = {}
        for ln in args.asr.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                r = json.loads(ln)
                alt[str(r["sample_id"])] = E5.canon_tokens(r.get("transcript") or "") if r.get("status") == "ok" else []
        if set(alt) != set(ids):
            raise SystemExit(f"--asr roster mismatch: {len(alt)} vs {len(ids)}")
        wfacts = {"whisper": wfacts, "asr": str(args.asr), "union": bool(args.union)}
        for s in ids:
            wtx[s] = {"canon": (wtx[s]["canon"] + ["<SEP>"] + alt[s]) if args.union else alt[s]}
    sent, _ = S2.load_reference_sentences(G.LOCK, G.DATA)
    rtx = {s: {"canon": E5.canon_tokens(sent[s])} for s in ids}
    del sent
    # TRAIN slot-type prior P(type present | intent), excluding Fold A and Fold B utterances
    fa, _ = E5.load_catalog(G.DATA, "fold-a")
    excl = {gold_all[s]["utt"] for s in list(fa) + ids}
    del fa
    n_int, n_type = Counter(), defaultdict(Counter)
    seen = set()
    for r in train:
        if r.utterance_id in excl or r.utterance_id in seen:
            continue
        seen.add(r.utterance_id)
        it = f"{r.scenario}_{r.action}"
        n_int[it] += 1
        for t in {e.type for e in r.entities}:
            n_type[it][t] += 1
    del train
    prior = {it: {t: c / n_int[it] for t, c in n_type[it].items()} for it in n_int}

    # per-row items, labels, repaired counts
    feats, lab = {}, {}
    rep = {k: {} for k in ("miss_W", "val_W", "any_W", "miss_R", "val_R", "any_R", "miss_all", "val_all", "valdisc_W", "missval_disc_W")}
    item_tab = Counter()
    type_tab = defaultdict(Counter)
    for s in ids:
        r = rows[s]
        its = entity_items(r["gold"], r["pred"])
        b = bidx_of[s]
        groups = {k: [] for k in rep}
        for it in its:
            k = it["kind"]
            if k not in ("MISSING",) + VALUE_KINDS:
                continue
            gval = r["gold"][it["gold_index"]].filler
            inW, inR = contained(gval, wtx[s]["canon"]), contained(gval, rtx[s]["canon"])
            cls = "miss" if k == "MISSING" else "val"
            groups[f"{cls}_all"].append(it)
            item_tab[(cls, "items")] += 1
            item_tab[(cls, "in_whisper")] += int(inW)
            item_tab[(cls, "in_reference")] += int(inR)
            type_tab[it["type"]][f"{cls}_items"] += 1
            type_tab[it["type"]][f"{cls}_in_whisper"] += int(inW)
            if inW:
                groups[f"{cls}_W"].append(it); groups["any_W"].append(it)
            if inR:
                groups[f"{cls}_R"].append(it); groups["any_R"].append(it)
            if inW and cls == "val":
                dW = contained(r["pred"][it["pred_index"]].filler, wtx[s]["canon"])
                item_tab[("val", "in_whisper_and_delivered_also_in_whisper")] += int(dW)
                if not dW:
                    groups["valdisc_W"].append(it)
            if inW and (cls == "miss" or not contained(r["pred"][it["pred_index"]].filler, wtx[s]["canon"])):
                groups["missval_disc_W"].append(it)
        for k, g in groups.items():
            rep[k][s] = G.counts(r["gold"], G.repaired(r["gold"], r["pred"], g)) if g else r["c"]
        lab[s] = {k: bool(g) for k, g in groups.items()}
        pi = r["pred_intent"] or ""
        pr = prior.get(pi, {})
        dtypes = {e.type for e in r["pred"]}
        miss_mass = [p for t, p in pr.items() if t not in dtypes]
        feats[s] = {
            "pred_empty": float(not r["pred"]),
            "n_delivered": float(len(r["pred"])),
            "expected_missing_mass": float(sum(miss_mass)),
            "expected_missing_max": float(max(miss_mass) if miss_mass else 0.0),
            "expected_type_count_gap": float(sum(pr.values()) - len(r["pred"])),
            "solver_forced_close": float(r["sfc"]),
            "perception_forced_close": float(r["pfc"]),
            "solver_tokens": float(per[s].get(("solver", b), 0)),
            "perception_tokens": float(per[s].get(("perception", b), 0)),
            "shortlist_len": float(len(r["cands"])),
            "name_type_delivered": float(bool(dtypes & NAME_TYPES)),
            "delivered_value_tokens": float(sum(len(e.filler.split()) for e in r["pred"])),
        }
    base = G.pooled(rows, ids)[0]

    def f1_of(counts_map, sel=None, u=1.0):
        tp = fp = fn = 0.0
        for s in ids:
            c0 = rows[s]["c"]
            c1 = counts_map[s] if (sel is None or s in sel) else c0
            tp += c0[0] + u * (c1[0] - c0[0]); fp += c0[1] + u * (c1[1] - c0[1]); fn += c0[2] + u * (c1[2] - c0[2])
        return G.f1(tp, fp, fn)

    out = {"schema": "saea-339-asr-trigger-bound-v1", "population": {"run": spec["run"], "branch": spec["branch"], "n": len(ids),
           "slu_f1": base, "checks": pop["checks"]}, "whisper_catalog": wfacts,
           "items": {f"{a}:{b}": v for (a, b), v in sorted(item_tab.items())},
           "by_type": {t: dict(c) for t, c in sorted(type_tab.items(), key=lambda kv: -sum(v for k, v in kv[1].items() if k.endswith("_items")))[:14]},
           "label_rows": {k: sum(lab[s][k] for s in ids) for k in rep}}
    out["ceilings_pp_perfect_conversion"] = {k: round(f1_of(rep[k]) - base, 3) for k in rep}
    out["ceilings_pp_at_uptake_0457"] = {k: round(f1_of(rep[k], u=0.457) - base, 3) for k in rep}
    # pp per broken EXACT item (harm unit): drop one EXACT gold-matched item on a random row -> mean pp
    exact_rows = [s for s in ids if any(p in rows[s]["gold"] for p in rows[s]["pred"])]
    rng = random.Random(339)
    samp = rng.sample(exact_rows, 200)
    deltas = []
    for s in samp:
        r = rows[s]
        k = next(i for i, p in enumerate(r["pred"]) if p in r["gold"])
        c1 = G.counts(r["gold"], [p for i, p in enumerate(r["pred"]) if i != k])
        deltas.append(f1_of({**{x: rows[x]["c"] for x in ids}, s: c1}) - base)
    out["harm_unit_pp_per_broken_exact_item"] = round(sum(deltas) / len(deltas), 4)
    # bootstrap CI for any_W and any_R ceilings (utterance clusters)
    cl = defaultdict(list)
    for s in ids:
        cl[rows[s]["utt"]].append(s)
    keys = sorted(cl)
    rng = random.Random(20261019)
    dr = {"any_W": [], "any_R": [], "miss_W": [], "missval_disc_W": []}
    for _ in range(2000):
        sm = [s for k in (keys[rng.randrange(len(keys))] for _ in keys) for s in cl[k]]
        b0 = [0.0] * 3
        acc = {k: [0.0] * 3 for k in dr}
        for s in sm:
            for j in range(3):
                b0[j] += rows[s]["c"][j]
                for k in dr:
                    acc[k][j] += rep[k][s][j]
        bf = G.f1(*b0)
        for k in dr:
            dr[k].append(G.f1(*acc[k]) - bf)
    out["ceiling_ci95"] = {k: [round(sorted(v)[50], 3), round(sorted(v)[1949], 3)] for k, v in dr.items()}
    # signal AUCs
    names = list(next(iter(feats.values())).keys())
    out["signal_auc"] = {}
    for lk in ("any_W", "miss_W", "val_W", "missval_disc_W", "any_R"):
        y = [lab[s][lk] for s in ids]
        out["signal_auc"][lk] = {n: auc([feats[s][n] for s in ids], y) for n in names}
    # cross-fit logistic trigger (5 folds by utterance), all signals + predicted-scenario one-hot
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    scen = sorted({(rows[s]["pred_intent"] or "none_none").split("_", 1)[0] for s in ids})
    X = np.array([[feats[s][n] for n in names] + [float((rows[s]["pred_intent"] or "none_none").split("_", 1)[0] == c) for c in scen]
                  for s in ids])
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    ukeys = sorted({rows[s]["utt"] for s in ids})
    rng = random.Random(20261019)
    rng.shuffle(ukeys)
    fold_of = {u: i % 5 for i, u in enumerate(ukeys)}
    folds = np.array([fold_of[rows[s]["utt"]] for s in ids])
    out["trigger"] = {}
    for lk in ("any_W", "miss_W", "missval_disc_W", "any_R"):
        y = np.array([lab[s][lk] for s in ids], dtype=int)
        score = np.zeros(len(ids))
        for f in range(5):
            tr, te = folds != f, folds == f
            m = LogisticRegression(C=0.3, max_iter=2000).fit(X[tr], y[tr])
            score[te] = m.predict_proba(X[te])[:, 1]
        res = {"base_rate": round(float(y.mean()), 4), "oof_auc": auc(list(score), list(y)), "by_rate": {}}
        order = np.argsort(-score, kind="stable")
        ceil = f1_of(rep[lk]) - base
        for q in RATES:
            k = int(round(q * len(ids)))
            sel = {ids[i] for i in order[:k]}
            hits = int(y[order[:k]].sum())
            g1 = f1_of(rep[lk], sel) - base
            g0 = f1_of(rep[lk], sel, u=0.457) - base
            res["by_rate"][str(q)] = {"calls": k, "helpful_called": hits, "precision": round(hits / k, 4),
                                      "recall_rows": round(hits / max(1, int(y.sum())), 4),
                                      "yield_pp_perfect": round(g1, 3), "yield_share_of_ceiling": round(g1 / ceil, 3) if ceil else None,
                                      "yield_pp_uptake_0457": round(g0, 3),
                                      "breakeven_broken_exact_items_per_100_calls_at_0457": round(
                                          100 * g0 / (-out["harm_unit_pp_per_broken_exact_item"]) / k, 2) if k else None}
        out["trigger"][lk] = res
    # simple model-visible rules (no fit)
    rules = {"pred_empty": lambda s: feats[s]["pred_empty"] > 0,
             "expected_missing_max>=0.5": lambda s: feats[s]["expected_missing_max"] >= 0.5,
             "solver_forced_close": lambda s: feats[s]["solver_forced_close"] > 0,
             "name_type_delivered": lambda s: feats[s]["name_type_delivered"] > 0,
             "expected_missing_max>=0.5_or_name_type": lambda s: feats[s]["expected_missing_max"] >= 0.5 or feats[s]["name_type_delivered"] > 0}
    out["rules"] = {}
    for rn, fn_ in rules.items():
        sel = {s for s in ids if fn_(s)}
        out["rules"][rn] = {"calls": len(sel), "precision_any_W": round(sum(lab[s]["any_W"] for s in sel) / max(1, len(sel)), 4),
                            "recall_any_W": round(sum(lab[s]["any_W"] for s in sel) / max(1, sum(lab[s]["any_W"] for s in ids)), 4),
                            "yield_any_W_perfect": round(f1_of(rep["any_W"], sel) - base, 3),
                            "yield_any_W_0457": round(f1_of(rep["any_W"], sel, u=0.457) - base, 3),
                            "yield_any_R_perfect": round(f1_of(rep["any_R"], sel) - base, 3)}
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"n": len(ids), "base": round(base, 2), "ceil": out["ceilings_pp_perfect_conversion"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
