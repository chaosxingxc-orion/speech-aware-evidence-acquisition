#!/usr/bin/env python3
"""Supplement to the COMP-1b Fold A paired read: entity over-emission and the attribution classes.

Model-free, from sealed bytes only: zero model, server, tokenizer, encoder, embedder, scorer and GPU
contacts. It reads the sealed per-sample official scores of three arms -- the COMP-1b arm, the shared
in-chain A/A and cell COMP-1's cited arm (seal-only attempt) -- and writes:

* entity exact-match TP / FP / FN per arm, summed from the sealed per-sample ``slot_f1_exact_*``
  counts; the zero-gold rows (gold entity count ``tp + fn`` = 0, identical on every arm or the script
  refuses); FP on those rows and the number of zero-gold rows that emit any entity; paired row
  bootstraps (10,000 draws, seed 20260929) of the FP deltas COMP-1b minus A/A and COMP-1b minus COMP-1;
* the per-class attribution table over the 191 PLAN intent-wrong rows, with membership fixed before
  contact in ``docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json``
  (the COMP-1b first-phase supply equals COMP-1's, output digest ``ce68bebc...``, so the membership
  applies unchanged), reusing the loaders of ``slurp_comp1_sealonly_read_supplement.py``.

No utterance text, gold label string, filler, intent name or model output is printed or persisted:
ids never leave the process; counts only.

    PYTHONPATH=src python -B scripts/analysis/slurp_comp1b_read_supplement.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" --output <path>.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
from pathlib import Path

ARMS = {
    "aa": ("SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1", "attempt-slurp-native-stage3-comp1-aa-fold-a-generation-v1"),
    "comp1b": ("SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1", "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1"),
    "comp1": ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1", "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only"),
}
SCORER = "slurp-slu-official-train"
SEED, DRAWS = 20260929, 10000


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    repo, data, out_path = Path(ns.repo_root).resolve(), Path(ns.data_root), Path(ns.output)
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite {out_path}")

    per = {}
    shas = {}
    for key, (run, attempt) in ARMS.items():
        path = data / "runs" / run / attempt / f"{run}.scores.json"
        shas[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        doc = json.loads(path.read_text(encoding="utf-8"))[SCORER]
        per[key] = {row["sample_id"]: row for row in doc["per_sample"]}
    ids = sorted(per["aa"])
    if any(sorted(per[k]) != ids for k in per):
        raise SystemExit("the three arms do not cover the same rows")
    gold = {i: per["aa"][i]["slot_f1_exact_tp"] + per["aa"][i]["slot_f1_exact_fn"] for i in ids}
    for key in per:
        if any(per[key][i]["slot_f1_exact_tp"] + per[key][i]["slot_f1_exact_fn"] != gold[i] for i in ids):
            raise SystemExit(f"{key}: gold entity counts differ from the A/A's")
    zero = [i for i in ids if gold[i] == 0]

    entities = {}
    for key, rows in per.items():
        tp = sum(rows[i]["slot_f1_exact_tp"] for i in ids)
        fp = sum(rows[i]["slot_f1_exact_fp"] for i in ids)
        fn = sum(rows[i]["slot_f1_exact_fn"] for i in ids)
        zfp = sum(rows[i]["slot_f1_exact_fp"] for i in zero)
        entities[key] = {"tp": tp, "fp": fp, "fn": fn, "emitted": tp + fp, "fp_on_zero_gold_rows": zfp,
                         "fp_on_gold_entity_rows": fp - zfp,
                         "zero_gold_rows_emitting": sum(1 for i in zero if rows[i]["slot_f1_exact_fp"] > 0)}

    rng = random.Random(SEED)

    def boot(values: list[float]) -> dict:
        n = len(values)
        sums = sorted(sum(values[rng.randrange(n)] for _ in range(n)) for _ in range(DRAWS))
        return {"point": sum(values), "ci95": [sums[int(0.025 * DRAWS) - 1], sums[int(0.975 * DRAWS) - 1]]}

    contrasts = {}
    for right, left in (("comp1b", "aa"), ("comp1b", "comp1")):
        a, b = per[left], per[right]
        contrasts[f"{right}_minus_{left}"] = {
            "d_fp_all_rows": boot([b[i]["slot_f1_exact_fp"] - a[i]["slot_f1_exact_fp"] for i in ids]),
            "d_fp_zero_gold_rows": boot([(b[i]["slot_f1_exact_fp"] - a[i]["slot_f1_exact_fp"]) if gold[i] == 0 else 0 for i in ids]),
            "d_zero_gold_rows_emitting": boot([((b[i]["slot_f1_exact_fp"] > 0) - (a[i]["slot_f1_exact_fp"] > 0)) if gold[i] == 0 else 0 for i in ids]),
        }

    spec = importlib.util.spec_from_file_location("supp", repo / "scripts/analysis/slurp_comp1_sealonly_read_supplement.py")
    supp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(supp)
    classes_doc = json.loads((repo / supp.CLASSES).read_text(encoding="utf-8"))
    run, attempt = ARMS["comp1b"]
    arm_s, _ = supp.load_scores(data, run, attempt)
    aa_s, _ = supp.load_scores(data, supp.AA_RUN, supp.AA_ATTEMPT)
    plan_s, _ = supp.load_scores(data, supp.PLAN_RUN, supp.PLAN_ATTEMPT)
    c1_s, _ = supp.load_scores(data, supp.RUN, supp.ARM_ATTEMPT)
    arm_o, _ = supp.load_outputs(data, run, attempt)
    aa_o, _ = supp.load_outputs(data, supp.AA_RUN, supp.AA_ATTEMPT)

    def ok(scores: dict, sid: str) -> int:
        return int(scores[sid]["scenario_action_exact"] == 1.0)

    per_row = classes_doc["per_row"]
    table = {}
    for cls in classes_doc["class_order"]:
        members = [s for s, r in per_row.items() if r["class"] == cls]
        both_wrong = [s for s in members if not ok(aa_s, s) and not ok(arm_s, s)]
        same = sum(1 for s in both_wrong if arm_o[s]["intent_key"] == aa_o[s]["intent_key"])
        table[cls] = {
            "rows": len(members), "delivered_prepared": sum(1 for s in members if per_row[s]["delivered_comp1"]),
            "intent_exact_plan": sum(ok(plan_s, s) for s in members), "intent_exact_aa": sum(ok(aa_s, s) for s in members),
            "intent_exact_comp1": sum(ok(c1_s, s) for s in members), "intent_exact_comp1b": sum(ok(arm_s, s) for s in members),
            "wrong_to_gold_vs_aa": sum(1 for s in members if not ok(aa_s, s) and ok(arm_s, s)),
            "gold_aa_to_wrong": sum(1 for s in members if ok(aa_s, s) and not ok(arm_s, s)),
            "both_wrong_same_intent": same, "both_wrong_different_intent": len(both_wrong) - same,
        }
    newly = [s for s, r in per_row.items() if r["class"] in ("newly-by-both", "newly-by-agree", "newly-by-centroid")]
    record = {
        "schema": "saea-slurp-comp1b-read-supplement-v1",
        "scores_sha256": shas,
        "zero_gold_rows": len(zero),
        "entities": entities,
        "contrasts": contrasts,
        "bootstrap": {"seed": SEED, "draws": DRAWS, "unit": "row (paired)"},
        "attribution_classes": {
            "membership_file": supp.CLASSES,
            "membership_sha256": hashlib.sha256((repo / supp.CLASSES).read_bytes()).hexdigest(),
            "table": table,
            "total": {k: sum(t[k] for t in table.values()) for k in next(iter(table.values()))},
            "newly_delivered": {"rows": len(newly), "converted_comp1b": sum(ok(arm_s, s) for s in newly),
                                "converted_comp1": sum(ok(c1_s, s) for s in newly)},
        },
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer": 0},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out_path), "entities": entities,
                      "contrasts": contrasts, "newly_delivered": record["attribution_classes"]["newly_delivered"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
