#!/usr/bin/env python3
"""Offline bounds for the decision-338 lever column (L1 false-fill suppression, L2 Perception candidate union).

Model-free, read-only. TRAIN Fold B (SLURP-EVO-FOLD-B-V2, n = 1,080), Thinking core, the sealed NX-T R1 rec2 and NX-T R2b
flights (7 perception branches per row in total, each with its own Perception contact and its own first-visit Solver
contact). No test row is read (guard). Only aggregates are printed or written: counts, rates, pp, CIs.

L1: support filter over a pool of sealed Solver decodes (base = the R2b delivering arm budget-3072), first-first form
    (base labels kept; a base entity kept iff >= s pool members support it: same type, normalised-filler char F1 >= 0.8,
    the registered commit policy's similarity), plus the gate "empty the row if N1 >= 0.2 AND >= v of the other pool
    members answered no entity" (N1 = entity-free share of the 20 supplied exemplars, the R6 / VER-1 statistic).
    v4g is applied to every arm text before parsing (the lock delivers through v4g).
L2: union of the Perception candidate lists across branches = an empirical recall bound for a k-decode union, with the
    ordering rule (sample-0 list verbatim first, then appended by support count desc, best rank asc) and caps K.

    python -B l338_bounds.py --out l338-bounds.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts/analysis"))
sys.dont_write_bytecode = True

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response, score_slu  # noqa: E402
from speech_aware_evidence_acquisition.core.base import DELIVERY_NORMALISERS  # noqa: E402
from speech_aware_evidence_acquisition.rails import delivery_normalisers  # noqa: E402,F401
from speech_aware_evidence_acquisition.rails.commit_policies import character_level_f1  # noqa: E402
from speech_aware_evidence_acquisition.scoring.normalize import normalize_text_v1  # noqa: E402

DATA = Path("/home/chao/saea-data/speechrl-data")
LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
R1 = ("SAEA-SLURP-STAGE3-NXT-R1-THINKING-POLICY-FOLD-B-V1", "attempt-slurp-native-stage3-nxt-r1-thinking-policy-fold-b-generation-rec2-v1",
      "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1")
R2B = ("SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1", "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1",
       "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1")
ARMS = {"r2b.budget-3072": R2B, "r2b.solver-6144": R2B, "r1.both-on": R1, "r1.both-on-twin": R1, "r1.solver-off": R1,
        "r1.perception-off": R1, "r1.both-off": R1}
BASE = "r2b.budget-3072"
THINK_P = ["r2b.budget-3072", "r2b.solver-6144", "r1.both-on", "r1.both-on-twin", "r1.solver-off"]  # Perception thinking ON
ALL_P = THINK_P + ["r1.perception-off", "r1.both-off"]
L1_POOLS = {"P3": ["r2b.budget-3072", "r1.both-on", "r1.both-on-twin"],
            "P5": ["r2b.budget-3072", "r1.both-on", "r1.both-on-twin", "r2b.solver-6144", "r1.perception-off"]}
V4G = "saea-deliver-normalise-v4g"
SIM = 0.8
GATE_N1 = 0.2
EX_SNAPSHOT = "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars/snapshot.json"
EX_PREFIX = "train-exemplars::value:"
DRAWS, SEED = 2000, 20261019


def guard(sid):
    if ":test:" in sid or sid.startswith("slurp:test"):
        raise SystemExit("test row encountered; refusing")


def counts(gold, pred):
    s = score_slu(gold_scenario="s", gold_action="a", gold_entities=list(gold), predicted_scenario="s", predicted_action="a",
                  predicted_entities=list(pred))
    return (s.slu_f1_word_tp + s.slu_f1_char_tp, s.slu_f1_word_fp + s.slu_f1_char_fp, s.slu_f1_word_fn + s.slu_f1_char_fn)


def f1(t):
    tp, fp, fn = t
    return 0.0 if tp == 0 else 100.0 * 2 * tp / (2 * tp + fp + fn)


def tot(cs, ids):
    a = b = c = 0.0
    for i in ids:
        x, y, z = cs[i]; a += x; b += y; c += z
    return (a, b, c)


def iter_jsonl(p):
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); args = ap.parse_args()
    norm = DELIVERY_NORMALISERS.resolve(V4G)
    # ---- arms: texts (v4g), candidate lists
    texts, cands, v4g_changed = {}, {}, {}
    for arm, (run, att, read) in ARMS.items():
        name = arm.split(".", 1)[1]
        t = {}
        for rec in iter_jsonl(DATA / "analysis" / read / "columns" / f"arm-{name}-first-visit-outputs.jsonl"):
            sid = str(rec["sample_id"]); guard(sid); t[sid] = rec.get("text") or ""
        ch = 0
        for sid in t:
            out = norm(t[sid]).text
            ch += int(out != t[sid]); t[sid] = out
        texts[arm], v4g_changed[arm] = t, ch
    for run, att, read in (R1, R2B):
        for rec in iter_jsonl(DATA / "runs" / run / att / f"{run}.outputs.jsonl"):
            sid = str(rec["sample_id"]); guard(sid)
            for b in rec["native_episode_receipt"]["perception_branches"]["branches"]:
                key = ("r1." if run == R1[0] else "r2b.") + b["branch_id"]
                if key in ARMS:
                    cands.setdefault(key, {})[sid] = [str(x) for x in b.get("candidate_intent_ids") or []]
            rec.clear()
    ids = sorted(texts[BASE])
    assert len(ids) == 1080 and all(set(texts[a]) == set(ids) and set(cands[a]) == set(ids) for a in ARMS)
    # ---- gold
    lock = load_lock(LOCK); idset = set(ids); gold = {}
    for r in load_slurp_split(lock, DATA, "train", workers=4):
        if r.sample_id in idset:
            gold[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "utt": r.utterance_id,
                                 "ents": tuple(SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
    assert set(gold) == idset
    # ---- N1 from the R2b phases.json (row-level first-phase supply; Solver exemplars)
    doc = json.loads((DATA / "runs" / R2B[0] / R2B[1] / f"{R2B[0]}.phases.json").read_text(encoding="utf-8"))
    ex = {}
    for res in doc["phases"][0]["results"]:
        sid = res["sample_id"]; guard(sid)
        for wave in res.get("waves") or ():
            sel = (wave.get("fusion_decision") or {}).get("selected_value_ids") or []
            if any(v.startswith(EX_PREFIX) for v in sel):
                ex[sid] = [v.split(EX_PREFIX, 1)[-1] for v in sel if v.startswith(EX_PREFIX)]
                break
    del doc
    snap = json.loads((DATA / EX_SNAPSHOT).read_text(encoding="utf-8"))
    pool_ann = {}
    for v in snap["values"]:
        parts = [p.strip() for p in (v.get("content") or "").split(" | ")]
        pool_ann[v["value_id"].split("value:", 1)[-1]] = bool(parts[2]) and parts[2] != "none" if len(parts) == 3 else None
    del snap
    n1, n1_missing = {}, 0
    for sid in ids:
        xs = [pool_ann.get(e) for e in ex.get(sid, [])]
        xs = [x for x in xs if x is not None]
        if not xs:
            n1_missing += 1; n1[sid] = None
        else:
            n1[sid] = sum(1 for x in xs if not x) / len(xs)
    med = sorted(v for v in n1.values() if v is not None)[len([v for v in n1.values() if v is not None]) // 2]
    n1 = {k: (med if v is None else v) for k, v in n1.items()}
    ex20 = sum(len(ex.get(s, [])) == 20 for s in ids)

    # ---- parse
    parsed = {a: {} for a in ARMS}
    for a in ARMS:
        for sid in ids:
            sc, ac, ents, ok = parse_slu_response(texts[a][sid])
            parsed[a][sid] = {"ok_parse": bool(ok), "intent": f"{sc}_{ac}" if ok and sc and ac else None,
                              "ents": tuple(SlotEntity(type=e.type, filler=e.filler) for e in ents) if ok else ()}
    rows_c = {a: {sid: counts(gold[sid]["ents"], parsed[a][sid]["ents"]) for sid in ids} for a in ARMS}
    out = {"n": len(ids), "population": "TRAIN Fold B (SLURP-EVO-FOLD-B-V2)", "v4g_rows_changed_by_reapply": v4g_changed,
           "n1": {"exemplars_20_rows": ex20, "missing_filled_median": n1_missing, "median": med,
                  "rows_n1_ge_0.2": sum(n1[s] >= GATE_N1 for s in ids)},
           "arms": {a: {"slu": f1(tot(rows_c[a], ids)), "intent": 100.0 * sum(parsed[a][s]["intent"] == gold[s]["intent"] for s in ids) / len(ids)}
                    for a in ARMS}}

    rng = random.Random(SEED)
    utts = sorted({gold[s]["utt"] for s in ids}); by_utt = {}
    for s in ids:
        by_utt.setdefault(gold[s]["utt"], []).append(s)
    boots = [[s for u in (rng.choice(utts) for _ in utts) for s in by_utt[u]] for _ in range(DRAWS)]

    def delta_ci(new_c, base_c):
        pt = f1(tot(new_c, ids)) - f1(tot(base_c, ids))
        ds = sorted(f1(tot(new_c, b)) - f1(tot(base_c, b)) for b in boots)
        return [round(pt, 3), round(ds[int(0.025 * DRAWS)], 3), round(ds[int(0.975 * DRAWS) - 1], 3)]

    def supported(e, answers):
        tgt = normalize_text_v1(e.filler); k = 0
        for ans in answers:
            if any(o.type == e.type and character_level_f1(tgt, normalize_text_v1(o.filler)) >= SIM for o in ans):
                k += 1
        return k

    def exact_hit(e, g):
        return any(x.type == e.type and normalize_text_v1(x.filler) == normalize_text_v1(e.filler) for x in g)

    base_c = rows_c[BASE]
    l1 = {}
    for pname, pool in L1_POOLS.items():
        others = [a for a in pool if a != BASE]
        for s in (2, 3):
            if s > len(pool):
                continue
            for gate_v in (None, len(others) - 1, len(others)):
                new_c, ff_removed, ne_lost, ne_gained, dropped, dropped_wrong, base_wrong = {}, 0, 0, 0, 0, 0, 0
                for sid in ids:
                    be = parsed[BASE][sid]["ents"]; g = gold[sid]["ents"]
                    answers = [parsed[a][sid]["ents"] for a in pool]
                    kept = [e for e in be if supported(e, answers) >= s]
                    if gate_v is not None and n1[sid] >= GATE_N1 and sum(not parsed[a][sid]["ents"] for a in others) >= gate_v:
                        kept = []
                    for e in be:
                        w = not exact_hit(e, g); base_wrong += int(w)
                        if e not in kept:
                            dropped += 1; dropped_wrong += int(w)
                    c = counts(g, kept); new_c[sid] = c
                    if not g and be and not kept:
                        ff_removed += 1
                    if g:
                        was = base_c[sid][1] == 0 and base_c[sid][2] == 0
                        now = c[1] == 0 and c[2] == 0
                        ne_lost += int(was and not now); ne_gained += int(now and not was)
                key = f"{pname}-n{len(pool)}-s{s}" + ("" if gate_v is None else f"+gate(N1>={GATE_N1},others_empty>={gate_v})")
                l1[key] = {"slu": round(f1(tot(new_c, ids)), 3), "delta_vs_base": delta_ci(new_c, base_c),
                           "empty_gold_false_fills_removed": ff_removed, "nonempty_exact_lost": ne_lost, "nonempty_exact_gained": ne_gained,
                           "entities_dropped": dropped, "dropped_that_were_wrong": dropped_wrong,
                           "drop_precision": round(dropped_wrong / dropped, 3) if dropped else None,
                           "drop_recall_of_wrong_base_entities": round(dropped_wrong / base_wrong, 3) if base_wrong else None}
        # gate alone
        for gate_v in (len(others) - 1, len(others)):
            new_c = {}
            for sid in ids:
                be = parsed[BASE][sid]["ents"]
                fire = n1[sid] >= GATE_N1 and sum(not parsed[a][sid]["ents"] for a in others) >= gate_v
                new_c[sid] = counts(gold[sid]["ents"], () if fire else be)
            l1[f"{pname}-gate-only(N1>={GATE_N1},others_empty>={gate_v})"] = {"slu": round(f1(tot(new_c, ids)), 3), "delta_vs_base": delta_ci(new_c, base_c)}
    out["L1_support_filter_vs_base"] = l1
    out["L1_twin_reference"] = {"r1.both-on-twin_minus_r1.both-on": delta_ci(rows_c["r1.both-on-twin"], rows_c["r1.both-on"])}
    out["empty_gold_rows"] = sum(not gold[s]["ents"] for s in ids)
    out["base_empty_gold_false_fill_rows"] = sum((not gold[s]["ents"]) and bool(parsed[BASE][s]["ents"]) for s in ids)

    # ---- L2
    g_int = {s: gold[s]["intent"] for s in ids}
    base_ok = {s: parsed[BASE][s]["intent"] == g_int[s] for s in ids}

    def pos_class(lst, gi):
        if gi not in lst:
            return "absent"
        r = lst.index(gi)
        return "sole" if len(lst) == 1 else ("rank1_of_many" if r == 0 else "rank2plus")

    conv_n, conv_k = Counter(), Counter()
    for s in ids:
        k = pos_class(cands[BASE][s], g_int[s]); conv_n[k] += 1; conv_k[k] += int(base_ok[s])
    conv = {k: conv_k[k] / conv_n[k] for k in conv_n}

    def ordered_union(s, arms, m=1):
        base_list = cands[arms[0]][s]
        cnt, best = Counter(), {}
        for a in arms:
            for r, c in enumerate(cands[a][s]):
                cnt[c] += 1; best[c] = min(best.get(c, 99), r)
        keep = [c for c in cnt if c in base_list or cnt[c] >= m]
        # registered ordering: the sample-0 (greedy) list verbatim first, then appended candidates by support count desc,
        # best rank asc, intent id asc
        return sorted(keep, key=lambda c: (0, base_list.index(c), 0, 0, c) if c in base_list else (1, 0, -cnt[c], best[c], c))

    def l2_block(arms, m=1):
        res = {"arms": arms, "append_min_support": m}
        res["recall_base_list"] = 100.0 * sum(g_int[s] in cands[arms[0]][s] for s in ids) / len(ids)
        un = {s: ordered_union(s, arms, m) for s in ids}
        res["recall_full_union"] = 100.0 * sum(g_int[s] in un[s] for s in ids) / len(ids)
        res["union_size_hist"] = dict(sorted(Counter(len(un[s]) for s in ids).items()))
        res["rows_union_differs_from_base_list"] = sum(un[s][:len(cands[arms[0]][s])] != cands[arms[0]][s] or len(un[s]) != len(cands[arms[0]][s]) for s in ids)
        for K in (1, 2, 3, 4, 5):
            lst = {s: un[s][:K] for s in ids}
            rec = 100.0 * sum(g_int[s] in lst[s] for s in ids) / len(ids)
            # intent estimate: unchanged lists keep the sealed outcome; changed lists take the base arm's class conversion
            est = 0.0; changed = 0; dil_rows = 0
            for s in ids:
                if lst[s] == cands[arms[0]][s]:
                    est += base_ok[s]
                else:
                    changed += 1
                    k = pos_class(lst[s], g_int[s]); est += conv.get(k, 0.0)
                    dil_rows += int(pos_class(cands[arms[0]][s], g_int[s]) == "sole" and k != "sole")
            res[f"cap{K}"] = {"recall": round(rec, 2), "rows_list_changed": changed, "est_intent": round(100.0 * est / len(ids), 2),
                              "gold_sole_rows_diluted": dil_rows,
                              "newly_listed_gold_rows": sum(g_int[s] in lst[s] and g_int[s] not in cands[arms[0]][s] for s in ids),
                              "gold_lost_from_list_rows": sum(g_int[s] not in lst[s] and g_int[s] in cands[arms[0]][s] for s in ids)}
        curve = {}
        others = arms[1:]
        for k in range(0, len(others) + 1):
            vals = [100.0 * sum(g_int[s] in set(itertools.chain(cands[arms[0]][s], *(cands[a][s] for a in sub))) for s in ids) / len(ids)
                    for sub in itertools.combinations(others, k)]
            curve[k + 1] = round(sum(vals) / len(vals), 2)
        res["recall_full_union_by_decodes_k"] = curve
        return res

    out["L2_conversion_by_gold_position_base"] = {k: {"n": conv_n[k], "acc": round(100.0 * conv[k], 2)} for k in conv_n}
    out["L2_union_thinking_5"] = l2_block(THINK_P)
    out["L2_union_all_7"] = l2_block(ALL_P)
    out["L2_union_base_plus_twinlike_2"] = l2_block([BASE, "r2b.solver-6144"])
    out["L2_union_thinking_5_m2"] = l2_block(THINK_P, 2)
    out["L2_union_all_7_m2"] = l2_block(ALL_P, 2)
    per = {}
    for a in ALL_P:
        cn, ck = Counter(), Counter()
        for s in ids:
            k = pos_class(cands[a][s], g_int[s]); cn[k] += 1; ck[k] += int(parsed[a][s]["intent"] == g_int[s])
        per[a] = {"recall": round(100.0 * sum(g_int[s] in cands[a][s] for s in ids) / len(ids), 2),
                  "conversion": {k: [cn[k], round(100.0 * ck[k] / cn[k], 1)] for k in sorted(cn)}}
    out["L2_per_arm_recall_and_conversion"] = per
    out["L2_list_discordance"] = {f"{a} vs {b}": sum(cands[a][s] != cands[b][s] for s in ids)
                                  for a, b in (("r1.both-on", "r1.both-on-twin"), (BASE, "r2b.solver-6144"), (BASE, "r1.both-on"),
                                               (BASE, "r1.perception-off"))}
    out["L2_size_by_arm"] = {a: dict(sorted(Counter(len(cands[a][s]) for s in ids).items())) for a in ALL_P}
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
