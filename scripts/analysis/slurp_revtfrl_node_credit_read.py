#!/usr/bin/env python3
"""REV-TFRL-1 recipe steps 2 and 4: the Reviewer node's credit on the arm and on the in-chain A/A.

Applies ``scripts/analysis/slurp_reviewer_credit_table.py``'s own functions UNMODIFIED (``load_pool``,
``visit_records``, ``credit_table``, ``stance_route_table``, ``revision_events``, ``policy_answers``,
``per_row_scores``, ``paired_delta``) to the two sealed Fold A runs of the cell, and adds:

- per arm: Reviewer contacts per row, Planner routes (ACCEPT / REVISE / other), revisions executed, the
  model-free count of Reviewer responses narrating a tool call, the per-class credit table, and the loop
  value (delivered answer minus the same trajectory's first Solver draft, intent and pooled SLU-F1, the
  credit driver's whole-utterance cluster bootstrap, 2000 draws, seed 20260927);
- the arm-minus-A/A difference of loop values, paired per row, same cluster bootstrap, beside the declared
  expectation +0.80 pp.

Written to a NEW directory ``<data root>/analysis/SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1/node-credit/``
(refused if it already holds files). MODEL-FREE: zero model, server, tokenizer, encoder, scorer-subprocess,
network and GPU contacts. Gold is read OFFLINE on the scoring side and compared in memory; counts, ids and
hashes only -- no utterance text, gold string, Reviewer text or model output is printed or persisted.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

READ_ID = "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1"
ARM = "SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-V1"
AA = "SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1"
EXPECTED_PP = 0.80


def load_credit_module(repo_root: Path):
    path = repo_root / "scripts" / "analysis" / "slurp_reviewer_credit_table.py"
    spec = importlib.util.spec_from_file_location("slurp_reviewer_credit_table", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def loop_diff(ct, first_a, built_a, first_b, built_b, ids, rng, draws):
    """(built_b - first_b) - (built_a - first_a), paired per row, whole-utterance cluster bootstrap."""
    def lv(first, built, pick):
        fi, fs = ct.aggregate(first, pick)
        bi, bs = ct.aggregate(built, pick)
        return bi - fi, bs - fs

    def diff(pick):
        ai, as_ = lv(first_a, built_a, pick)
        bi, bs = lv(first_b, built_b, pick)
        return bi - ai, bs - as_

    point = diff(ids)
    clusters = defaultdict(list)
    for s in ids:
        clusters[ct.utterance_of(s)].append(s)
    keys = sorted(clusters)
    di, ds = [], []
    for _ in range(draws):
        pick = [s for k in (rng.choice(keys) for _ in keys) for s in clusters[k]]
        x = diff(pick)
        di.append(x[0])
        ds.append(x[1])
    di.sort()
    ds.sort()
    lo, hi = int(0.025 * draws), int(0.975 * draws) - 1
    return {"intent_pp": round(point[0], 3), "intent_ci95": [round(di[lo], 3), round(di[hi], 3)],
            "slu_pp": round(point[1], 3), "slu_ci95": [round(ds[lo], 3), round(ds[hi], 3)]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--repo-root", required=True, type=Path)
    ap.add_argument("--data-root", required=True, type=Path)
    ap.add_argument("--lock", default="/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
    ap.add_argument("--arm", default=ARM)
    ap.add_argument("--aa", default=AA)
    ap.add_argument("--out-dir", type=Path, default=None, help="default <data root>/analysis/<READ_ID>/node-credit")
    args = ap.parse_args(argv)
    ct, ct_sha = load_credit_module(args.repo_root)
    out_dir = args.out_dir or (args.data_root / "analysis" / READ_ID / "node-credit")
    if out_dir.exists() and any(out_dir.iterdir()):
        print(f"REFUSED: {out_dir} already holds files")
        return 3
    lock = ct.load_lock(Path(args.lock))
    rc = ct.roster_checks()
    gold = ct.load_gold(lock, args.data_root, ["train"], None)
    inventory = ct.load_legal_intent_inventory(lock, args.data_root)
    ex_intents = ct.load_exemplar_intents(args.data_root)
    pools, report_pools, credit, stance, loop_value, first_built = {}, {}, {}, {}, {}, {}
    for label, run_id in (("aa", args.aa), ("arm", args.arm)):
        pool = ct.load_pool(args.data_root, (label, run_id, "fold-a", label, "fold-a"), gold, inventory,
                            ex_intents)
        pool["checks"]["rows_equal_roster"] = int(set(pool["rows"]) == rc["ids"]["fold-a"])
        visits = ct.visit_records(pool, gold)
        rows = pool["rows"]
        routes = Counter(a for r in rows.values() for a in r["routes"])
        reviews_per_row = Counter(len(r["reviews"]) for r in rows.values())
        events = ct.revision_events(pool)
        ids = sorted(rows)
        built = {s: rows[s]["final_out"] for s in ids}
        first = ct.per_row_scores(ct.policy_answers(pool, events, ct.GATES[ct.NONE_GATE], "full"), gold)
        first_built[label] = (first, built)
        lv = ct.paired_delta(first, built, ids, random.Random(ct.BOOT_SEED))
        first_agg, built_agg = ct.aggregate(first, ids), ct.aggregate(built, ids)
        credit[label] = ct.credit_table(visits)
        stance[label] = ct.stance_route_table(visits)
        loop_value[label] = {"rows": len(ids), "revision_events_first_visit": len(events),
                             "first_draft_intent": round(first_agg[0], 3), "first_draft_slu": round(first_agg[1], 3),
                             "delivered_intent_port": round(built_agg[0], 3),
                             "delivered_slu_port": round(built_agg[1], 3),
                             "first_draft_intent_wrong_rows": sum(1 for s in ids if not first[s]["intent_ok"]),
                             "as_built_vs_first_draft": lv}
        report_pools[label] = {
            "run_id": run_id, "directory": pool["directory"], "phases_sha256": pool["phases_sha256"],
            "outputs_sha256": pool["outputs_sha256"], "scores_sha256": pool["scores_sha256"],
            "scorer": pool["scorer"], "manifest_status": pool["manifest_status"], "checks": pool["checks"],
            "rows": len(ids), "reviewer_visits": len(visits),
            "reviewer_visits_per_row_histogram": {str(k): v for k, v in sorted(reviews_per_row.items())},
            "planner_routes": dict(sorted(routes.items())),
            "revisions_executed": sum(1 for v in visits if v["revised"]),
            "reviewer_tool_narration_visits": sum(1 for v in visits if v["narration"]),
            "rows_with_any_revise": sum(1 for r in rows.values() if "REVISE" in r["routes"]),
        }
        pools[label] = pool
        print(f"loaded {label}: visits {len(visits)} checks {pool['checks']}", flush=True)
    ids = sorted(set(pools["arm"]["rows"]) & set(pools["aa"]["rows"]))
    diff = loop_diff(ct, *first_built["aa"], *first_built["arm"], ids, random.Random(ct.BOOT_SEED), ct.BOOT_DRAWS)
    report = {
        "read_id": READ_ID, "part": "node-credit (recipe steps 2 and 4)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "credit_module_sha256": ct_sha, "bootstrap": {"draws": ct.BOOT_DRAWS, "seed": ct.BOOT_SEED,
                                                      "unit": "whole utterance (cluster)"},
        "contacts": {"model": 0, "server": 0, "tokenizer": 0, "encoder": 0, "scorer_subprocess": 0, "gpu": 0},
        "pools": report_pools, "credit": credit, "stance_route": stance, "loop_value": loop_value,
        "loop_value_arm_minus_aa": diff, "paired_rows": len(ids), "declared_expectation_pp": EXPECTED_PP,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "node-credit-v1.json"
    path.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "path": str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
