#!/usr/bin/env python3
"""Cell W4: the recipe's mechanism read (step 6), counts only, on the sealed arm and the shared A/A.

Imports ``scripts/analysis/slurp_w4_fold_a_offline_estimate.py`` by path (unmodified) and applies its own
functions -- the governed TRAIN gold loader, the official exact matcher with the bad-case bank's
same-type / type-swap / over / omission attribution (``entity_items``), and the K2 / K3 / K4 / risk class
counter (``estimate``) -- to each sealed arm in turn by re-pointing the module's ``ARM`` constant (the
offline estimate was written against the AGREE arm). ``contact_cost`` is not re-run (the paired read's
frontier and the per-role token table carry the realised cost).

Per arm: the K2 / K3 / K4 / risk counts and rows touched, the per-type counters on the revised types, and
a per-type exact TP / FP / FN table (FP = predicted entities of the type not exactly matched, FN = gold
entities of the type not exactly matched), with arm minus A/A beside. Written to ``--out`` (refused if it
exists). MODEL-FREE: zero model, tokenizer, encoder, scorer, server and network contacts. Gold and the
delivered answers are compared in memory; only slot TYPE names and counts are printed or persisted.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARMS = {
    "aa": {"run_id": "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1",
           "attempt": "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1"},
    "arm": {"run_id": "SAEA-SLURP-STAGE3-W4-FOLD-A-V1",
            "attempt": "attempt-slurp-native-stage3-w4-fold-a-generation-v1"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--arm", default=None, help="RUN/ATTEMPT override of the right arm (dry runs only)")
    a = ap.parse_args()
    if a.arm:
        run, attempt = a.arm.split("/", 1)
        ARMS["arm"] = {"run_id": run, "attempt": attempt}
    if a.out.exists():
        raise SystemExit(f"REFUSED: {a.out} exists")
    spec = importlib.util.spec_from_file_location("w4off", REPO / "scripts/analysis/slurp_w4_fold_a_offline_estimate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.contact_cost = lambda *args, **kwargs: None
    root = a.data_root
    lock = m.load_lock(Path(a.lock))
    gold = m.load_gold(lock, root)
    changes = json.loads((root / m.PREP / "CHANGES.json").read_text(encoding="utf-8"))
    revised = sorted(changes["changed_cards"])
    doc = {"schema": "saea-slurp-w4-mechanism-read-v1", "revised_types": revised, "arms": {}}
    for key, arm in ARMS.items():
        m.ARM = dict(arm)
        est = m.estimate(Path(a.lock), root)
        loaded = m.load_arm(root)
        per_type = defaultdict(Counter)
        for sid, predicted in loaded["delivered"].items():
            items = m.entity_items(gold[sid]["entities"], predicted)
            for e in items["exact"]:
                per_type[e.type]["tp"] += 1
            for pe, ge in items["same"] + items["swap"]:
                per_type[pe.type]["fp"] += 1
                per_type[ge.type]["fn"] += 1
            for e in items["over"]:
                per_type[e.type]["fp"] += 1
            for e in items["omitted"]:
                per_type[e.type]["fn"] += 1
        doc["arms"][key] = {
            **arm,
            "exact_tp_fp_fn": est["arm"]["exact_tp_fp_fn"],
            "pooled_span_f1": est["arm"]["pooled_span_f1"],
            "k_counts": est["counts"],
            "rows_touched": est["rows_touched"],
            "per_type_classes": est["per_type"],
            "per_type_exact": {t: dict(per_type[t]) for t in revised},
        }
    delta = {}
    for t in revised:
        L = doc["arms"]["aa"]["per_type_exact"][t]
        R = doc["arms"]["arm"]["per_type_exact"][t]
        delta[t] = {f: R.get(f, 0) - L.get(f, 0) for f in ("tp", "fp", "fn")}
    doc["per_type_exact_delta_arm_minus_aa"] = delta
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("per_type_classes",)}
                      for k, v in doc["arms"].items()}, sort_keys=True))
    print(json.dumps(delta, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
