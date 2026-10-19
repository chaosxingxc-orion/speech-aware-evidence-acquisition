#!/usr/bin/env python3
"""Gap decomposition of the SLURP v3.0 lock candidate (Thinking core, Perception + Solver thinking, budget 3,072 / cap 4,096).

Model-free, read-only. Populations (sealed, never test):
  DEV   P3.1 lock arm  SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1 (DEV-2000-ADDED, n = 1,000; devel gold)
  FOLDB NX-T R2b       SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1, delivering arm budget-3072 (Fold B, n = 1,080; train gold)
Prints and persists only ids-free aggregates: counts, rates, pp, label names (intent/scenario/slot TYPE names).
No transcript, utterance, filler, model output or reasoning text is printed or written.

    python -B gap_decomposition.py --out gap-numbers.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(REPO / "src"))
sys.dont_write_bytecode = True

from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: E402
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, parse_slu_response, score_slu  # noqa: E402
from speech_aware_evidence_acquisition.analysis.sealed_credit.entity_states import entity_items  # noqa: E402

DATA = Path("/home/chao/saea-data/speechrl-data")
LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
IB_PREFIX = "intent-boundaries::intent-boundary:"
POPS = {
    "DEV": {"run": "SAEA-SLURP-STAGE3-THINKING-SYSTEM-DEV2000-ADDED-LOCK-V1",
            "attempt": "attempt-slurp-native-stage3-thinking-system-dev2000-added-lock-generation-v1",
            "split": "devel", "scorer": "slurp-slu-official", "branch": None, "n": 1000},
    "FOLDB": {"run": "SAEA-SLURP-STAGE3-NXT-R2B-SOLVER-BUDGET-FOLD-B-V1",
              "attempt": "attempt-slurp-native-stage3-nxt-r2b-solver-budget-fold-b-generation-v1",
              "split": "train", "scorer": "slurp-slu-official-train", "branch": "budget-3072", "n": 1080},
}
# test-side comparators (aggregate numbers from docs/readiness/2026-10-12-sota-comparator-table-v1.md and the successor-3 read; no test rows read)
OURS_TEST = {"slu": 73.05, "intent": 86.33}
TIERS = {"LauraGPT": {"intent": 87.87, "slu": 73.45}, "SFT-Qwen2-Audio-7B": {"intent": 88.13, "slu": 76.75},
         "UniverSLU-14": {"intent": 90.3, "slu": 79.5}}
VALUE_KINDS = ("FORMAT", "BOUNDARY", "NEAR", "WRONG-VALUE")


class Refused(RuntimeError):
    pass


def guard(sid: str) -> None:
    if ":test:" in sid or sid.startswith("slurp:test"):
        raise Refused("test row encountered; refusing")


def counts(gold, pred):
    s = score_slu(gold_scenario="s", gold_action="a", gold_entities=list(gold), predicted_scenario="s", predicted_action="a",
                  predicted_entities=list(pred))
    return (s.slu_f1_word_tp + s.slu_f1_char_tp, s.slu_f1_word_fp + s.slu_f1_char_fp, s.slu_f1_word_fn + s.slu_f1_char_fn)


def f1(tp, fp, fn):
    if tp == 0:
        return 0.0
    p, r = tp / (tp + fp), tp / (tp + fn)
    return 100.0 * 2 * p * r / (p + r)


def pooled(rows, ids, key="c"):
    tp = fp = fn = 0.0
    for i in ids:
        a, b, c = rows[i][key]
        tp, fp, fn = tp + a, fp + b, fn + c
    return f1(tp, fp, fn), (tp, fp, fn)


def repaired(gold, pred, items):
    out = list(pred)
    drop, append = set(), []
    for it in items:
        if it["kind"] == "MISSING":
            append.append(gold[it["gold_index"]])
        elif it["kind"] == "SPURIOUS":
            drop.add(it["pred_index"])
        else:
            out[it["pred_index"]] = gold[it["gold_index"]]
    return [e for k, e in enumerate(out) if k not in drop] + append


def load_pop(name: str, spec: dict, gold_all: dict) -> dict:
    d = DATA / "runs" / spec["run"] / spec["attempt"]
    scores = json.loads((d / f"{spec['run']}.scores.json").read_text(encoding="utf-8"))[spec["scorer"]]["per_sample"]
    sealed = {}
    for r in scores:
        sid = str(r["sample_id"]); guard(sid)
        sealed[sid] = r
    out = {}
    with (d / f"{spec['run']}.outputs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            sid = str(rec["sample_id"]); guard(sid)
            sc, ac, ents, ok = parse_slu_response(rec.get("text") or "")
            out[sid] = {"parsed": bool(ok), "intent": f"{sc}_{ac}" if ok and sc is not None and ac is not None else None,
                        "ents": tuple(SlotEntity(type=e.type, filler=e.filler) for e in ents)}
            if spec["branch"]:
                br = next(b for b in rec["native_episode_receipt"]["perception_branches"]["branches"] if b["branch_id"] == spec["branch"])
                if not br.get("deliver"):
                    raise Refused(f"{name}: branch {spec['branch']} is not the delivering branch")
                out[sid]["cands"] = [str(x) for x in br.get("candidate_intent_ids") or []]
                out[sid]["block"] = [v.split(IB_PREFIX, 1)[-1] for v in br.get("supplied_value_ids") or [] if str(v).startswith(IB_PREFIX)]
                out[sid]["branch_index"] = br["branch_index"]
            rec.clear()
    doc = json.loads((d / f"{spec['run']}.phases.json").read_text(encoding="utf-8"))
    for res in doc["phases"][0]["results"]:
        sid = res["sample_id"]; guard(sid)
        row = out[sid]
        perc = next((s for s in res.get("agent_states") or () if s.get("state_kind") == "phase:perception"), None)
        pc = [str(c.get("intent_id")) for c in (json.loads(perc["content"]).get("candidates") or [])] if perc else []
        row["cands_state"] = pc
        if "cands" not in row:
            row["cands"] = pc
            row["block"] = [v.split(IB_PREFIX, 1)[-1] for v in res["initial_query_state"]["retrieved_value_ids"] if v.startswith(IB_PREFIX)]
    del doc
    # forced closes per (role, branch index) from the trace COST + USE channels (stats only)
    fc, role_of = {}, {}
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
                fc[key] = (bool(pl.get("forced_close")), int(pl.get("completion_tokens") or 0))
    per = defaultdict(dict)
    for key, cid in role_of.items():
        parts = cid.split(":", 3)
        role, bidx, sid = parts[1], int(parts[2]), parts[3]
        guard(sid)
        per[sid][(role, bidx)] = fc.get(key, (None, None))
    bidx_default = 0
    checks = Counter()
    rows = {}
    for sid, row in out.items():
        g = gold_all[sid]
        b = row.get("branch_index", bidx_default)
        pf = per[sid].get(("perception", b), (None, None))[0]
        sf = per[sid].get(("solver", b), (None, None))[0]
        c = counts(g["ents"], row["ents"])
        s = sealed[sid]
        sealed_c = (s["slu_f1_word_tp"] + s["slu_f1_char_tp"], s["slu_f1_word_fp"] + s["slu_f1_char_fp"], s["slu_f1_word_fn"] + s["slu_f1_char_fn"])
        checks["rescore_matches_sealed"] += int(all(abs(x - y) < 1e-9 for x, y in zip(c, sealed_c)))
        ok = bool(s["scenario_action_exact"])
        checks["intent_parse_agrees_sealed"] += int((row["intent"] == g["intent"]) == ok)
        checks["cands_receipt_equals_state"] += int(row["cands"] == row["cands_state"])
        checks["forced_close_known"] += int(pf is not None and sf is not None)
        rows[sid] = {"gold_intent": g["intent"], "scenario": g["scenario"], "utt": g["utt"], "gold": g["ents"], "pred": row["ents"],
                     "pred_intent": row["intent"], "parsed": row["parsed"], "ok": ok, "c": sealed_c,
                     "cands": row["cands"], "block": row["block"], "pfc": bool(pf), "sfc": bool(sf)}
    checks["rows"] = len(rows)
    if len(rows) != spec["n"]:
        raise Refused(f"{name}: {len(rows)} rows, expected {spec['n']}")
    return {"rows": rows, "checks": dict(checks)}


def intent_class(r) -> str:
    if r["ok"]:
        return "correct"
    if not r["parsed"] or r["pred_intent"] is None:
        return "unparsed"
    if r["gold_intent"] in r["cands"]:
        return "b_in_shortlist_solver_wrong"
    if r["gold_intent"] in r["block"]:
        return "a1_absent_from_shortlist_in_block"
    return "a2_absent_from_shortlist_and_block"


def analyse(rows: dict) -> dict:
    ids = sorted(rows)
    n = len(ids)
    slu, tot = pooled(rows, ids)
    intent = 100.0 * sum(rows[i]["ok"] for i in ids) / n
    res = {"n": n, "slu_f1": slu, "intent": intent, "slu_totals": tot}
    # ---------------- intent error classes
    ic = Counter(intent_class(rows[i]) for i in ids)
    res["intent_classes"] = dict(ic)
    sub = Counter()
    for i in ids:
        r = rows[i]
        k = intent_class(r)
        if k == "b_in_shortlist_solver_wrong":
            sub["solver_pick_in_shortlist"] += int(r["pred_intent"] in r["cands"])
            sub["solver_pick_outside_shortlist"] += int(r["pred_intent"] not in r["cands"])
            sub[f"gold_rank_{r['cands'].index(r['gold_intent']) + 1}"] += 1
        if k != "correct":
            gs, ps = r["gold_intent"].split("_", 1)[0], (r["pred_intent"] or "_").split("_", 1)[0]
            sub[f"{k}::same_scenario" if gs == ps else f"{k}::cross_scenario"] += 1
    res["intent_subclasses"] = dict(sub)
    res["shortlist"] = {"gold_in_shortlist": sum(rows[i]["gold_intent"] in rows[i]["cands"] for i in ids),
                        "gold_in_block": sum(rows[i]["gold_intent"] in rows[i]["block"] for i in ids),
                        "shortlist_size": dict(Counter(len(rows[i]["cands"]) for i in ids)),
                        "acc_given_gold_in_shortlist": None}
    ins = [i for i in ids if rows[i]["gold_intent"] in rows[i]["cands"]]
    outs = [i for i in ids if i not in set(ins)]
    res["shortlist"]["acc_given_gold_in_shortlist"] = 100.0 * sum(rows[i]["ok"] for i in ins) / len(ins)
    res["shortlist"]["acc_given_gold_absent"] = 100.0 * sum(rows[i]["ok"] for i in outs) / len(outs) if outs else None
    res["shortlist"]["acc_size1_gold_top1"] = None
    # forced close splits
    fc = {}
    for label, sel in (("solver_fc", lambda r: r["sfc"]), ("perception_fc", lambda r: r["pfc"]), ("any_fc", lambda r: r["sfc"] or r["pfc"]),
                       ("no_fc", lambda r: not (r["sfc"] or r["pfc"]))):
        sid = [i for i in ids if sel(rows[i])]
        fc[label] = {"n": len(sid), "intent": 100.0 * sum(rows[i]["ok"] for i in sid) / len(sid) if sid else None,
                     "slu_f1": pooled(rows, sid)[0] if sid else None,
                     "intent_errors": sum(not rows[i]["ok"] for i in sid),
                     "intent_classes": dict(Counter(intent_class(rows[i]) for i in sid if not rows[i]["ok"]))}
    res["forced_close"] = fc
    # ---------------- slot items
    items_by_row = {i: entity_items(rows[i]["gold"], rows[i]["pred"]) for i in ids}
    kinds = Counter()
    kinds_fc = Counter()
    kinds_wrong_intent = Counter()
    for i in ids:
        r = rows[i]
        for it in items_by_row[i]:
            k = it["kind"]
            if k == "SPURIOUS":
                k = "FP_EMPTY_GOLD" if not r["gold"] else "FP_NONEMPTY_GOLD"
            kinds[k] += 1
            if r["sfc"] or r["pfc"]:
                kinds_fc[k] += 1
            if not r["ok"]:
                kinds_wrong_intent[k] += 1
    res["slot_items"] = {"all": dict(kinds), "on_forced_close_rows": dict(kinds_fc), "on_wrong_intent_rows": dict(kinds_wrong_intent),
                         "gold_entities": sum(len(rows[i]["gold"]) for i in ids), "pred_entities": sum(len(rows[i]["pred"]) for i in ids),
                         "empty_gold_rows": sum(not rows[i]["gold"] for i in ids),
                         "empty_gold_rows_with_false_fill": sum((not rows[i]["gold"]) and bool(rows[i]["pred"]) for i in ids),
                         "nonempty_gold_rows_predicted_empty": sum(bool(rows[i]["gold"]) and not rows[i]["pred"] for i in ids)}
    wt = Counter(it.get("sub") for i in ids for it in items_by_row[i] if it["kind"] == "WRONG-TYPE")
    res["slot_items"]["wrong_type_sub"] = dict(wt)

    # per-class repair oracles: SLU gain from repairing exactly the items of one class (alone)
    def oracle_repair(pred_filter):
        tp = fp = fn = 0.0
        for i in ids:
            r = rows[i]
            its = [it for it in items_by_row[i] if pred_filter(r, it)]
            c = counts(r["gold"], repaired(r["gold"], r["pred"], its)) if its else r["c"]
            tp, fp, fn = tp + c[0], fp + c[1], fn + c[2]
        return f1(tp, fp, fn)

    classes = {
        "FP_EMPTY_GOLD (false fill, gold empty)": lambda r, it: it["kind"] == "SPURIOUS" and not r["gold"],
        "FP_NONEMPTY_GOLD (extra slot)": lambda r, it: it["kind"] == "SPURIOUS" and bool(r["gold"]),
        "FN (MISSING)": lambda r, it: it["kind"] == "MISSING",
        "WRONG-TYPE": lambda r, it: it["kind"] == "WRONG-TYPE",
        "VALUE FORMAT": lambda r, it: it["kind"] == "FORMAT",
        "VALUE BOUNDARY": lambda r, it: it["kind"] == "BOUNDARY",
        "VALUE NEAR": lambda r, it: it["kind"] == "NEAR",
        "VALUE WRONG-VALUE": lambda r, it: it["kind"] == "WRONG-VALUE",
        "ORACLE iv: value normalised where type+span overlap (FORMAT+BOUNDARY+NEAR)": lambda r, it: it["kind"] in ("FORMAT", "BOUNDARY", "NEAR"),
        "ALL slot items": lambda r, it: True,
        "slot items on wrong-intent rows": lambda r, it: not r["ok"],
        "slot items on forced-close rows": lambda r, it: r["sfc"] or r["pfc"],
    }
    res["slu_repair_oracles"] = {k: {"slu_f1": v, "gain_pp": v - slu} for k, v in ((k, oracle_repair(f)) for k, f in classes.items())}

    # ---------------- oracles (i), (ii), (v)
    ok_ids = [i for i in ids if rows[i]["ok"]]
    o = {}
    o["i_intent_perfect"] = {"intent": 100.0, "intent_gain_pp": 100.0 - intent,
                             "slu_lower_unchanged": slu,
                             "slu_if_wrong_intent_rows_at_correct_row_rate": pooled(rows, ok_ids)[0],
                             "slu_if_wrong_intent_rows_slots_repaired": res["slu_repair_oracles"]["slot items on wrong-intent rows"]["slu_f1"]}
    o["i_intent_perfect"]["slu_gain_pp_central"] = o["i_intent_perfect"]["slu_if_wrong_intent_rows_at_correct_row_rate"] - slu
    o["ii_gold_always_in_shortlist"] = {"intent": res["shortlist"]["acc_given_gold_in_shortlist"],
                                        "intent_gain_pp": res["shortlist"]["acc_given_gold_in_shortlist"] - intent,
                                        "slu": pooled(rows, ins)[0], "slu_gain_pp": pooled(rows, ins)[0] - slu,
                                        "rows_gold_in_shortlist": len(ins)}
    # (ii-b) shortlist contains gold AND Solver then behaves as on gold-in-shortlist rows: same as above (rescaled). Also gold in boundary block:
    inb = [i for i in ids if rows[i]["gold_intent"] in rows[i]["block"]]
    o["ii_b_gold_always_in_boundary_block"] = {"intent": 100.0 * sum(rows[i]["ok"] for i in inb) / len(inb),
                                               "intent_gain_pp": 100.0 * sum(rows[i]["ok"] for i in inb) / len(inb) - intent, "rows": len(inb)}
    o["iii_empty_gold_false_fills_removed"] = res["slu_repair_oracles"]["FP_EMPTY_GOLD (false fill, gold empty)"]
    o["iv_values_normalised_where_type_and_span_overlap"] = res["slu_repair_oracles"]["ORACLE iv: value normalised where type+span overlap (FORMAT+BOUNDARY+NEAR)"]
    # (v) forced-close rows at natural-row error rates
    nat = [i for i in ids if not (rows[i]["sfc"] or rows[i]["pfc"])]
    fcr = [i for i in ids if rows[i]["sfc"] or rows[i]["pfc"]]
    acc_nat = sum(rows[i]["ok"] for i in nat) / len(nat)
    _, (ntp, nfp, nfn) = pooled(rows, nat)
    P, R = ntp / (ntp + nfp), ntp / (ntp + nfn)
    tp = fp = fn = 0.0
    for i in nat:
        a, b, c = rows[i]["c"]; tp, fp, fn = tp + a, fp + b, fn + c
    _, (ftp, ffp, ffn) = pooled(rows, fcr)
    G = ftp + ffn
    tp2 = R * G
    tp, fp, fn = tp + tp2, fp + tp2 * (1 - P) / P, fn + (G - tp2)
    o["v_forced_close_rows_at_natural_rates"] = {"intent": 100.0 * (sum(rows[i]["ok"] for i in nat) + acc_nat * len(fcr)) / n,
                                                 "slu": f1(tp, fp, fn), "rows_forced": len(fcr)}
    o["v_forced_close_rows_at_natural_rates"]["intent_gain_pp"] = o["v_forced_close_rows_at_natural_rates"]["intent"] - intent
    o["v_forced_close_rows_at_natural_rates"]["slu_gain_pp"] = o["v_forced_close_rows_at_natural_rates"]["slu"] - slu
    # solver-only forced close variant
    nat2 = [i for i in ids if not rows[i]["sfc"]]
    fc2 = [i for i in ids if rows[i]["sfc"]]
    acc2 = sum(rows[i]["ok"] for i in nat2) / len(nat2)
    o["v_b_solver_forced_rows_at_natural_rates"] = {"intent_gain_pp": 100.0 * (sum(rows[i]["ok"] for i in nat2) + acc2 * len(fc2)) / n - intent,
                                                   "rows_forced": len(fc2)}
    # combined optimistic oracle: (ii) intent + (iii)+(iv) slots
    o["combo_ii_iii_iv"] = {"intent": o["ii_gold_always_in_shortlist"]["intent"],
                            "slu_additive_estimate": slu + o["iii_empty_gold_false_fills_removed"]["gain_pp"] + o["iv_values_normalised_where_type_and_span_overlap"]["gain_pp"]}
    both = oracle_repair(lambda r, it: (it["kind"] == "SPURIOUS" and not r["gold"]) or it["kind"] in ("FORMAT", "BOUNDARY", "NEAR"))
    o["combo_ii_iii_iv"]["slu_iii_iv_joint"] = both
    res["oracles"] = o

    # ---------------- strata
    scen = defaultdict(lambda: {"n": 0, "intent_err": 0, "a": 0, "b": 0, "slot_items": Counter()})
    for i in ids:
        r = rows[i]
        s = scen[r["scenario"]]
        s["n"] += 1
        k = intent_class(r)
        if k != "correct":
            s["intent_err"] += 1
            s["a" if k.startswith("a") else "b"] += int(k != "unparsed")
        for it in items_by_row[i]:
            kk = it["kind"]
            if kk == "SPURIOUS":
                kk = "FP_EMPTY_GOLD" if not r["gold"] else "FP_NONEMPTY_GOLD"
            s["slot_items"][kk] += 1
    res["per_scenario"] = {}
    for name, s in sorted(scen.items()):
        sid = [i for i in ids if rows[i]["scenario"] == name]
        res["per_scenario"][name] = {"n": s["n"], "intent": 100.0 * (s["n"] - s["intent_err"]) / s["n"], "slu_f1": pooled(rows, sid)[0],
                                     "intent_errors": s["intent_err"], "absent_from_shortlist": s["a"], "solver_wrong_in_shortlist": s["b"],
                                     "slot_items": dict(s["slot_items"])}
    # SLU-loss share by scenario: gain from repairing all slot items inside that scenario
    for name in res["per_scenario"]:
        res["per_scenario"][name]["slu_gain_if_scenario_slots_perfect_pp"] = oracle_repair(lambda r, it, nm=name: r["scenario"] == nm) - slu
    # top error-owning gold intents
    ie = Counter(rows[i]["gold_intent"] for i in ids if not rows[i]["ok"])
    res["top_intent_error_owners"] = [{"gold_intent": k, "errors": v, "n": sum(rows[i]["gold_intent"] == k for i in ids),
                                       "absent_from_shortlist": sum(1 for i in ids if rows[i]["gold_intent"] == k and not rows[i]["ok"]
                                                                    and rows[i]["gold_intent"] not in rows[i]["cands"])}
                                      for k, v in sorted(ie.items(), key=lambda kv: (-kv[1], kv[0]))[:12]]
    conf = Counter((rows[i]["gold_intent"], rows[i]["pred_intent"]) for i in ids if not rows[i]["ok"])
    res["top_confusions"] = [{"gold": a, "pred": b, "count": c} for (a, b), c in sorted(conf.items(), key=lambda kv: (-kv[1], str(kv[0])))[:10]]
    res["top_error_slot_types"] = {}
    for kind in ("MISSING", "SPURIOUS", "WRONG-TYPE", "BOUNDARY", "WRONG-VALUE", "FORMAT", "NEAR"):
        cnt = Counter(it["type"] for i in ids for it in items_by_row[i] if it["kind"] == kind)
        res["top_error_slot_types"][kind] = cnt.most_common(6)
    # ---------------- bootstrap CIs (utterance clusters) for the main oracle gains
    clusters = defaultdict(list)
    for i in ids:
        clusters[rows[i]["utt"]].append(i)
    keys = sorted(clusters)
    rng = random.Random(20261019)
    draws = {"ii_intent": [], "ii_slu": [], "iii_slu": [], "iv_slu": [], "v_intent": [], "v_slu_naive_gap": []}
    # per-row repaired counts for iii / iv
    rep3, rep4 = {}, {}
    for i in ids:
        r = rows[i]
        its3 = [it for it in items_by_row[i] if it["kind"] == "SPURIOUS" and not r["gold"]]
        its4 = [it for it in items_by_row[i] if it["kind"] in ("FORMAT", "BOUNDARY", "NEAR")]
        rep3[i] = counts(r["gold"], repaired(r["gold"], r["pred"], its3)) if its3 else r["c"]
        rep4[i] = counts(r["gold"], repaired(r["gold"], r["pred"], its4)) if its4 else r["c"]
    for _ in range(2000):
        samp = [i for k in (keys[rng.randrange(len(keys))] for _ in keys) for i in clusters[k]]
        base_tp = [0.0, 0.0, 0.0]; t3 = [0.0, 0.0, 0.0]; t4 = [0.0, 0.0, 0.0]; ti = [0.0, 0.0, 0.0]
        okc = 0; nin = 0; okin = 0; nnat = 0; oknat = 0
        for i in samp:
            r = rows[i]
            for j in range(3):
                base_tp[j] += r["c"][j]; t3[j] += rep3[i][j]; t4[j] += rep4[i][j]
            okc += r["ok"]
            if r["gold_intent"] in r["cands"]:
                nin += 1; okin += r["ok"]
                for j in range(3):
                    ti[j] += r["c"][j]
            if not (r["sfc"] or r["pfc"]):
                nnat += 1; oknat += r["ok"]
        b = f1(*base_tp)
        draws["ii_intent"].append(100.0 * okin / nin - 100.0 * okc / len(samp))
        draws["ii_slu"].append(f1(*ti) - b)
        draws["iii_slu"].append(f1(*t3) - b)
        draws["iv_slu"].append(f1(*t4) - b)
        draws["v_intent"].append(100.0 * oknat / nnat - 100.0 * okc / len(samp))
    res["bootstrap_ci95"] = {k: [sorted(v)[int(0.025 * len(v))], sorted(v)[int(0.975 * len(v)) - 1]] for k, v in draws.items() if v}
    res["bootstrap_note"] = "utterance-cluster bootstrap, 2,000 draws, seed 20261019; v_intent is the natural-row minus pooled accuracy (upper bound of oracle v, scaled by the forced share in the point estimate)"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    lock = load_lock(LOCK)
    result = {"schema": "saea-slurp-v30-gap-decomposition-v1", "populations": {}, "tiers": TIERS, "ours_test_aggregate": OURS_TEST}
    for name, spec in POPS.items():
        if spec["split"] not in ("train", "devel"):
            raise Refused("only train/devel gold is read")
        gold_all = {}
        for r in load_slurp_split(lock, DATA, spec["split"], workers=4):
            guard(r.sample_id)
            gold_all[r.sample_id] = {"intent": f"{r.scenario}_{r.action}", "scenario": r.scenario, "utt": r.utterance_id,
                                     "ents": tuple(SlotEntity(type=e.type, filler=e.filler) for e in r.entities)}
        pop = load_pop(name, spec, gold_all)
        del gold_all
        a = analyse(pop["rows"])
        a["checks"] = pop["checks"]
        a["run"] = spec["run"]; a["branch"] = spec["branch"]
        result["populations"][name] = a
        print(json.dumps({name: {"n": a["n"], "slu": round(a["slu_f1"], 2), "intent": round(a["intent"], 2), "checks": a["checks"]}}), flush=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=True, default=list) + "\n", encoding="utf-8")
    print("written", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
