#!/usr/bin/env python3
"""Attribution-class outcome table for the cell A2 read (COMP-1b on DEV-2000-ADDED), model-free.

The A2 recipe (``docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1/analysis-recipe-v1.json``,
step 5) requires the attribution classes with reproduced hashes. Membership was fixed before contact in
``docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/attribution-classes-v1.json`` by
``scripts/flights/comp1dev/comp1dev_attribution_classes.py``. It applies to A2 unchanged because the A2 arm's
prepared first-phase supply has the same output digest (``ecca16a2...``) as the one that script proves.

This script:

1. re-runs the registered derivation byte-unchanged (imported, ``main`` called with an output path OUTSIDE the
   repository), capturing each class's sorted id list by wrapping the module's ``id_list_sha256``; the lists
   never leave the process;
2. refuses unless the re-derived document equals the registered file byte-for-byte and every persisted
   ``id_list_sha256`` (five classes and three summary lists) is reproduced;
3. tabulates, per class, intent exact (official ``slurp-slu-official`` ``scenario_action_exact``) under the
   sealed DEV plan arm, the in-chain A/A and the A2 arm, plus the transitions against the A/A and the plan arm,
   and the same / different wrong-intent split (intent keys are compared as sha256 digests, never printed).

No utterance text, gold label string, filler, intent name or model output is printed or persisted: counts and
hashes only. Zero model, server, encoder, embedder, scorer, tokenizer, network and GPU contacts.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 PYTHONPATH=src python -B \\
        scripts/analysis/slurp_a2_attribution_read.py --repo-root . --data-root "$SPEECHRL_DATA_DIR" \\
        --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \\
        --scratch <dir outside the repo> --output docs/results/2026-09-30-slurp-a2-attribution-classes-read-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

DERIVER = "scripts/flights/comp1dev/comp1dev_attribution_classes.py"
REGISTERED = "docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/attribution-classes-v1.json"
REGISTERED_SHA = "4f129ef4cb3578815a5c3b6965069c2c1d0b91dbf247afc09244376bb1ef9493"
LOADERS = "scripts/analysis/slurp_comp1_sealonly_read_supplement.py"
SCORER = "slurp-slu-official"
ARMS = {
    "plan": ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1", "attempt-slurp-native-default-plan-dev2000-added-generation-v1"),
    "aa": ("SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1", "attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1"),
    "a2": ("SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1", "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1"),
}
NEWLY = ("newly-by-both", "newly-by-agree", "newly-by-centroid")
SUMMARY_LISTS = (
    "rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1",
    "catch_all_rows_delivered_only_under_the_composition",
    "agree_newly_delivered_intent_covered",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(repo: Path, relpath: str, name: str):
    spec = importlib.util.spec_from_file_location(name, repo / relpath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--lock-path", required=True)
    ap.add_argument("--scratch", required=True, help="directory outside the repo for the re-derived membership")
    ap.add_argument("--output", required=True, help="repo-relative counts-only receipt")
    ns = ap.parse_args()
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    repo, data = Path(ns.repo_root).resolve(), Path(ns.data_root).resolve()
    scratch = Path(ns.scratch).resolve()
    if scratch == repo or repo in scratch.parents:
        raise SystemExit("--scratch must lie outside the repository")
    out_path = repo / ns.output
    if out_path.exists():
        raise SystemExit(f"refusing to overwrite {out_path}")

    # 1. re-derive membership through the registered script, capturing id lists by hash
    if sha(repo / REGISTERED) != REGISTERED_SHA:
        raise SystemExit("the registered membership file is not the recipe's 4f129ef4...")
    deriver = load(repo, DERIVER, "_comp1dev_attribution")
    captured: dict[str, list[str]] = {}
    original = deriver.id_list_sha256

    def capture(ids):
        members = sorted(ids)
        digest = original(members)
        captured[digest] = members
        return digest

    deriver.id_list_sha256 = capture
    rederived = scratch / "attribution-classes-rederived-v1.json"
    if rederived.exists():
        rederived.unlink()
    rc = deriver.main(["--repo-root", str(repo), "--data-root", str(data), "--lock-path", ns.lock_path,
                       "--output", str(rederived)])
    if rc != 0:
        raise SystemExit(f"the registered derivation exited {rc}")

    # 2. byte and hash reproduction
    registered = json.loads((repo / REGISTERED).read_text(encoding="utf-8"))
    again = json.loads(rederived.read_text(encoding="utf-8"))
    byte_identical = sha(rederived) == REGISTERED_SHA
    hashes = {}
    for cls in registered["class_order"]:
        want = registered["classes"][cls]["id_list_sha256"]
        got = again["classes"][cls]["id_list_sha256"]
        hashes[cls] = {"registered": want, "reproduced": got, "match": want == got, "rows": registered["classes"][cls]["rows"]}
    for key in SUMMARY_LISTS:
        want = registered["summary"][f"{key}_id_list_sha256"]
        got = again["summary"][f"{key}_id_list_sha256"]
        hashes[key] = {"registered": want, "reproduced": got, "match": want == got, "rows": registered["summary"][key]}
    if not all(h["match"] for h in hashes.values()):
        raise SystemExit("an id-list hash is not reproduced; no class outcome is tabulated")
    members = {cls: captured[registered["classes"][cls]["id_list_sha256"]] for cls in registered["class_order"]}
    for cls, ids in members.items():
        if len(ids) != registered["classes"][cls]["rows"]:
            raise SystemExit(f"{cls}: captured list length differs from the registered count")

    # 3. outcomes from sealed per-sample scores and outputs
    loaders = load(repo, LOADERS, "_sealonly_loaders")
    loaders.SCORER = SCORER
    scores, score_sha, outputs, output_sha = {}, {}, {}, {}
    for key, (run, attempt) in ARMS.items():
        scores[key], score_sha[key] = loaders.load_scores(data, run, attempt)
        outputs[key], output_sha[key] = loaders.load_outputs(data, run, attempt)
    ids_all = sorted(scores["aa"])
    if any(sorted(scores[k]) != ids_all for k in scores) or len(ids_all) != 1000:
        raise SystemExit("the three arms do not cover the same 1,000 rows")

    def ok(key: str, sid: str) -> int:
        return int(scores[key][sid]["scenario_action_exact"] == 1.0)

    per_class = {}
    arm_supply = json.loads((data / deriver.ARM_SUPPLY).read_text(encoding="utf-8"))
    if arm_supply["output_sha256"] != deriver.ARM_OUTPUT_SHA:
        raise SystemExit("the A2 arm supply digest is not ecca16a2...")
    for cls, ids in members.items():
        both_wrong = [s for s in ids if not ok("aa", s) and not ok("a2", s)]
        same = sum(1 for s in both_wrong if outputs["a2"][s]["intent_key"] == outputs["aa"][s]["intent_key"])
        per_class[cls] = {
            "rows": len(ids),
            "delivered_prepared_a2": registered["classes"][cls]["delivered_under_comp1"],
            "intent_exact_plan": sum(ok("plan", s) for s in ids),
            "intent_exact_aa": sum(ok("aa", s) for s in ids),
            "intent_exact_a2": sum(ok("a2", s) for s in ids),
            "wrong_to_gold_vs_aa": sum(1 for s in ids if not ok("aa", s) and ok("a2", s)),
            "gold_aa_to_wrong": sum(1 for s in ids if ok("aa", s) and not ok("a2", s)),
            "both_wrong_same_intent": same,
            "both_wrong_different_intent": len(both_wrong) - same,
        }
    total = {k: sum(t[k] for t in per_class.values()) for k in next(iter(per_class.values()))}
    newly = [s for cls in NEWLY for s in members[cls]]
    wrong_set = {s for ids in members.values() for s in ids}
    plan_right = [s for s in ids_all if ok("plan", s)]
    aa_right = [s for s in ids_all if ok("aa", s)]
    # 4. entity over-emission by entity type on the zero-gold rows (every emitted entity there is an FP).
    #    Gold enters only as the per-sample tp + fn count of the sealed official scores; types are the closed
    #    SLURP slot-type labels of the emitted entities (no filler is read into the record).
    gold_n = {s: scores["aa"][s]["slot_f1_exact_tp"] + scores["aa"][s]["slot_f1_exact_fn"] for s in ids_all}
    for key in scores:
        if any(scores[key][s]["slot_f1_exact_tp"] + scores[key][s]["slot_f1_exact_fn"] != gold_n[s] for s in ids_all):
            raise SystemExit(f"{key}: gold entity counts differ from the A/A's")
    zero = {s for s in ids_all if gold_n[s] == 0}
    by_type: dict[str, dict[str, dict[str, int]]] = {}
    zero_totals = {}
    for key, (run, attempt) in ARMS.items():
        path = data / "runs" / run / attempt / f"{run}.outputs.jsonl"
        emitted, rows_emitting = 0, 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row["sample_id"] not in zero:
                    continue
                try:
                    parsed = json.loads(row.get("text") or "")
                except (TypeError, ValueError):
                    parsed = None
                ents = parsed.get("entities") if isinstance(parsed, dict) else None
                ents = [e for e in ents if isinstance(e, dict)] if isinstance(ents, list) else []
                seen = set()
                for ent in ents:
                    t = str(ent.get("type"))
                    slot = by_type.setdefault(t, {}).setdefault(key, {"emitted": 0, "rows": 0})
                    slot["emitted"] += 1
                    if t not in seen:
                        slot["rows"] += 1
                        seen.add(t)
                emitted += len(ents)
                rows_emitting += bool(ents)
        zero_totals[key] = {"emitted_on_zero_gold_rows": emitted, "zero_gold_rows_emitting": rows_emitting,
                            "fp_on_zero_gold_rows_scores": sum(scores[key][s]["slot_f1_exact_fp"] for s in zero)}
    for t in by_type:
        for key in ARMS:
            by_type[t].setdefault(key, {"emitted": 0, "rows": 0})

    record = {
        "schema": "saea-slurp-a2-attribution-read-v1",
        "entity_over_emission_zero_gold": {"zero_gold_rows": len(zero), "totals": zero_totals,
                                           "by_entity_type": dict(sorted(by_type.items()))},
        "contacts": {k: 0 for k in ("model", "server", "encoder", "embedder", "scorer", "tokenizer", "network", "gpu")},
        "membership": {"file": REGISTERED, "sha256": REGISTERED_SHA, "deriver": DERIVER,
                       "deriver_sha256": sha(repo / DERIVER),
                       "rederived_byte_identical": byte_identical, "id_list_hashes": hashes},
        "scores_sha256": score_sha,
        "outputs_sha256": output_sha,
        "intent_wrong_rows_under_plan": len(wrong_set),
        "classes": per_class,
        "total": total,
        "newly_delivered": {"rows": len(newly), "converted_a2": sum(ok("a2", s) for s in newly),
                            "converted_aa": sum(ok("aa", s) for s in newly),
                            "stay_wrong_a2": sum(1 for s in newly if not ok("a2", s))},
        "plan_right_rows": {"rows": len(plan_right),
                            "now_wrong_under_a2": sum(1 for s in plan_right if not ok("a2", s)),
                            "now_wrong_under_aa": sum(1 for s in plan_right if not ok("aa", s))},
        "aa_right_rows": {"rows": len(aa_right),
                          "now_wrong_under_a2": sum(1 for s in aa_right if not ok("a2", s))},
        "boundary": "DEV-2000-ADDED development numbers (owner decisions 28 and 86); never a test claim",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2, sort_keys=True) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({k: record[k] for k in ("classes", "total", "newly_delivered", "plan_right_rows", "aa_right_rows")}, indent=1))
    print("rederived_byte_identical", byte_identical)
    print("out_sha256", hashlib.sha256(text.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
