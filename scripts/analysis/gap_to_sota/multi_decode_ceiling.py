#!/usr/bin/env python3
"""Selection / vote ceiling across sealed Fold B decodes of the v3.0 lock form (NX-T R1 + R2b column files; TRAIN Fold B, n = 1,080).

Model-free. Aggregates only (no text printed or written). Per row: official exact-intent flags and SLU counts per arm, plus the parsed
predicted intent label (in memory) for plurality voting.

    python -B multi_decode_ceiling.py --out multi-decode.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(REPO / "src"))
sys.dont_write_bytecode = True
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response  # noqa: E402

A = Path("/home/chao/saea-data/speechrl-data/analysis")
SC = "slurp-slu-official-train"
ARMS = {
    "r1.both-on": A / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/columns", "r1.both-on-twin": A / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/columns",
    "r1.perception-off": A / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/columns", "r1.solver-off": A / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/columns",
    "r1.both-off": A / "SAEA-SLURP-NXT-R1-THINKING-POLICY-FOLD-B-READ-V1/columns",
    "r2b.budget-3072": A / "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1/columns", "r2b.solver-6144": A / "SAEA-SLURP-NXT-R2B-SOLVER-BUDGET-FOLD-B-READ-V1/columns",
}
LOCKLIKE = ["r1.both-on", "r1.both-on-twin", "r2b.budget-3072", "r2b.solver-6144", "r1.perception-off"]


def f1(tp, fp, fn):
    return 0.0 if tp == 0 else 100.0 * 2 * tp / (2 * tp + fp + fn)


def load(arm, d):
    name = arm.split(".", 1)[1]
    sc = json.loads((d / f"arm-{name}-{SC}-scores.json").read_text(encoding="utf-8"))[SC]["per_sample"]
    rows = {}
    for r in sc:
        sid = str(r["sample_id"])
        if ":test:" in sid:
            raise SystemExit("test row; refusing")
        rows[sid] = {"ok": bool(r["scenario_action_exact"]),
                     "c": (r["slu_f1_word_tp"] + r["slu_f1_char_tp"], r["slu_f1_word_fp"] + r["slu_f1_char_fp"], r["slu_f1_word_fn"] + r["slu_f1_char_fn"])}
    with (d / f"arm-{name}-first-visit-outputs.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            sid = str(rec["sample_id"])
            s, a, _, ok = parse_slu_response(rec.get("text") or "")
            rows[sid]["pred"] = f"{s}_{a}" if ok and s is not None and a is not None else None
            rec.clear()
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", type=Path, required=True); args = ap.parse_args()
    arms = {k: load(k, d) for k, d in ARMS.items()}
    ids = sorted(arms["r2b.budget-3072"])
    assert all(set(v) == set(ids) for v in arms.values())
    n = len(ids)
    out = {"n": n, "population": "TRAIN Fold B (SLURP-EVO-FOLD-B-V2)", "arms": {}}
    for k, v in arms.items():
        tp = sum(v[i]["c"][0] for i in ids); fp = sum(v[i]["c"][1] for i in ids); fn = sum(v[i]["c"][2] for i in ids)
        out["arms"][k] = {"intent": 100.0 * sum(v[i]["ok"] for i in ids) / n, "slu": f1(tp, fp, fn)}

    def block(names):
        res = {}
        res["intent_any_correct_oracle"] = 100.0 * sum(any(arms[a][i]["ok"] for a in names) for i in ids) / n
        res["intent_all_correct"] = 100.0 * sum(all(arms[a][i]["ok"] for a in names) for i in ids) / n
        # plurality vote over predicted intents; tie -> the first arm in the list (the delivering arm leads)
        okv, agree, agree_ok = 0, 0, 0
        for i in ids:
            preds = [arms[a][i]["pred"] for a in names]
            cnt = Counter(p for p in preds if p is not None)
            if not cnt:
                continue
            top = max(cnt.values())
            choice = next(p for p in preds if p is not None and cnt[p] == top)
            idx = preds.index(choice)
            okv += arms[names[idx]][i]["ok"]
            if top == len(names):
                agree += 1; agree_ok += arms[names[0]][i]["ok"]
        res["intent_plurality_vote"] = 100.0 * okv / n
        res["unanimous_rows"] = agree
        res["acc_on_unanimous_rows"] = 100.0 * agree_ok / agree if agree else None
        res["acc_on_split_rows_delivering"] = (100.0 * (sum(arms[names[0]][i]["ok"] for i in ids) - agree_ok) / (n - agree)) if n > agree else None
        # SLU per-row oracle selection: per row pick the arm minimising fp + fn (then max tp)
        tp = fp = fn = 0.0
        for i in ids:
            best = min((arms[a][i]["c"] for a in names), key=lambda c: (c[1] + c[2], -c[0]))
            tp, fp, fn = tp + best[0], fp + best[1], fn + best[2]
        res["slu_best_of_arms_oracle"] = f1(tp, fp, fn)
        return res

    out["lock_like_5"] = {"arms": LOCKLIKE, **block(LOCKLIKE)}
    out["all_7"] = {"arms": list(ARMS), **block(["r2b.budget-3072"] + [a for a in ARMS if a != "r2b.budget-3072"])}
    out["pairs_twin"] = {"arms": ["r1.both-on", "r1.both-on-twin"], **block(["r1.both-on", "r1.both-on-twin"])}
    # expected pass@k curve over lock-like arms (mean over subsets of size k, delivering-first not required)
    curve = {}
    for k in range(1, len(LOCKLIKE) + 1):
        vals = [100.0 * sum(any(arms[a][i]["ok"] for a in sub) for i in ids) / n for sub in itertools.combinations(LOCKLIKE, k)]
        curve[k] = sum(vals) / len(vals)
    out["intent_pass_at_k_lock_like"] = curve
    args.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
