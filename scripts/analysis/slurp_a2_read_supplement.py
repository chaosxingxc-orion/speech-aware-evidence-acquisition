#!/usr/bin/env python3
"""Supplement to the cell A2 paired read (COMP-1b on DEV-2000-ADDED): entities, zero-gold emission, supply digests.

Model-free, from sealed bytes only: zero model, server, tokenizer, encoder, embedder, scorer and GPU contacts.
It reads the sealed per-sample official slurp-slu-official scores of the A2 arm, its in-chain A/A and the sealed
DEV plan arm (context), and writes entity exact-match TP / FP / FN per arm summed from the per-sample
``slot_f1_exact_*`` counts, the zero-gold rows (gold entity count tp + fn = 0, identical on every arm or the
script refuses), FP on those rows, the zero-gold rows that emit any entity, paired row bootstraps (10,000 draws,
seed 20260929) of the deltas A2 minus A/A and A2 minus the plan arm, and the prepared first-phase supply output
digests of the arm and the A/A against the registered values (recipe step 2).

No utterance text, gold label string, filler, intent name or model output is printed or persisted; counts only.

    python -B scripts/analysis/slurp_a2_read_supplement.py "$SPEECHRL_DATA_DIR" \
        "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1/supplement-v1.json"
"""
import hashlib, json, random, sys
from pathlib import Path
DATA = Path(sys.argv[1]); OUT = Path(sys.argv[2])
SCORER = "slurp-slu-official"; SEED, DRAWS = 20260929, 10000
ARMS = {
 "aa": ("SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1", "attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1"),
 "a2": ("SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1", "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1"),
 "plan": ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1", "attempt-slurp-native-default-plan-dev2000-added-generation-v1"),
}
SUPPLY = {"aa": "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19",
          "a2": "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"}
if OUT.exists(): raise SystemExit("refusing to overwrite")
per, shas = {}, {}
for k, (run, att) in ARMS.items():
    p = DATA / "runs" / run / att / f"{run}.scores.json"
    shas[k] = hashlib.sha256(p.read_bytes()).hexdigest()
    per[k] = {r["sample_id"]: r for r in json.loads(p.read_text(encoding="utf-8"))[SCORER]["per_sample"]}
ids = sorted(per["aa"])
assert all(sorted(per[k]) == ids for k in per), "row sets differ"
gold = {i: per["aa"][i]["slot_f1_exact_tp"] + per["aa"][i]["slot_f1_exact_fn"] for i in ids}
for k in per:
    assert all(per[k][i]["slot_f1_exact_tp"] + per[k][i]["slot_f1_exact_fn"] == gold[i] for i in ids), k
zero = [i for i in ids if gold[i] == 0]
ent = {}
for k, rows in per.items():
    tp = sum(rows[i]["slot_f1_exact_tp"] for i in ids); fp = sum(rows[i]["slot_f1_exact_fp"] for i in ids)
    fn = sum(rows[i]["slot_f1_exact_fn"] for i in ids); zfp = sum(rows[i]["slot_f1_exact_fp"] for i in zero)
    ent[k] = {"tp": tp, "fp": fp, "fn": fn, "emitted": tp + fp, "fp_on_zero_gold_rows": zfp,
              "zero_gold_rows_emitting": sum(1 for i in zero if rows[i]["slot_f1_exact_fp"] > 0)}
rng = random.Random(SEED)
def boot(v):
    n = len(v); s = sorted(sum(v[rng.randrange(n)] for _ in range(n)) for _ in range(DRAWS))
    return {"point": sum(v), "ci95": [s[int(0.025 * DRAWS) - 1], s[int(0.975 * DRAWS) - 1]]}
con = {}
for r, l in (("a2", "aa"), ("a2", "plan")):
    a, b = per[l], per[r]
    con[f"{r}_minus_{l}"] = {
        "d_tp": boot([b[i]["slot_f1_exact_tp"] - a[i]["slot_f1_exact_tp"] for i in ids]),
        "d_fp_all_rows": boot([b[i]["slot_f1_exact_fp"] - a[i]["slot_f1_exact_fp"] for i in ids]),
        "d_fp_zero_gold_rows": boot([(b[i]["slot_f1_exact_fp"] - a[i]["slot_f1_exact_fp"]) if gold[i] == 0 else 0 for i in ids]),
        "d_zero_gold_rows_emitting": boot([((b[i]["slot_f1_exact_fp"] > 0) - (a[i]["slot_f1_exact_fp"] > 0)) if gold[i] == 0 else 0 for i in ids]),
    }
sup = {}
for k, exp in SUPPLY.items():
    p = DATA / "prepared" / ARMS[k][0] / "phase-supply-v1.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    sup[k] = {"file_sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "output_sha256": d.get("output_sha256"),
              "matches_registered": d.get("output_sha256") == exp}
rec = {"schema": "saea-slurp-a2-read-supplement-v1", "scores_sha256": shas, "rows": len(ids), "zero_gold_rows": len(zero),
       "entities": ent, "contrasts": con, "supply": sup, "bootstrap": {"seed": SEED, "draws": DRAWS, "unit": "row (paired)"},
       "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0}}
OUT.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: rec[k] for k in ("zero_gold_rows", "entities", "contrasts", "supply", "scores_sha256")}, indent=1))
print("out_sha256", hashlib.sha256(OUT.read_bytes()).hexdigest())
