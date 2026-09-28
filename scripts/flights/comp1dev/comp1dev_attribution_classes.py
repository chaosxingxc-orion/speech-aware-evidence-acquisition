#!/usr/bin/env python3
"""Derive cell COMP-1 DEV-2000-ADDED's PER-CLASS ATTRIBUTION membership, model-free, before contact.

Owner decision 138: a composed round carries the per-class attribution table the
bad-case bank defines, so that "no improvement" reads as "these two elements
conflict on this class". Decision 152 names COMP-1's classes; the Fold A
membership is ``scripts/flights/comp1/comp1_attribution_classes.py``. That script
reads two Fold A-only rosters (cell CONV's 70 and cell KPROBE's 55), which do not
exist on DEV-2000-ADDED. This script derives the SAME five classes on the DEV
roster from what exists there, using the SAME predicates those two rosters used:

* the bad-case bank (``analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl``, roster
  ``dev2000-added``): each row's ``plan_class`` under the sealed DEV plan arm
  ``SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1`` (intent-wrong =
  ``INTENT-UNCOVERED`` or ``INTENT-COVERED``, i.e. ``scenario_action_exact`` < 0.5
  in that arm's sealed official ``slurp-slu-official`` per-sample scores) and the
  row's gold intent. Gold is read on the scoring side only, through the bank,
  EXACTLY the access pattern of the Fold A script (``load_bank`` over the same
  file, another roster key) and of the replication recipe's ``load_bank`` /
  ``load_population`` (imported byte-unchanged, which also asserts the bank's
  169 / 63 DEV class counts);
* the sealed DEV plan arm's own channels, rebuilt the way a flight builds them
  (``scripts/analysis/slurp_intent_agreement_production_replication.py``,
  ``arm_channels`` + ``boundary_decisions``, imported byte-unchanged -- the
  same constructor cells CONV and KPROBE were derived through), and four
  boundary decisions per row through the production constructor:

    - ``plan``      written key, w_agree 0.0, recall 8   (must equal the A/A's
                    prepared supply, output d57ee9d6..., on every row)
    - ``agree``     written key, w_agree 1.0 over this roster's pinned agreement
                    table, recall 60   (CONV's treatment)
    - ``centroid``  centroid key, w_agree 0.0, recall 8   (KPROBE's treatment)
    - ``composed``  centroid key, w_agree 1.0, recall 60  (must equal the COMP-1
                    DEV arm's prepared supply, output ecca16a2..., on every row)

  The two equality proofs are what make the single-factor counterfactuals
  believable: the constructor reproduces both flown selections byte-for-byte.

Classes, exclusive and attributed in this order over the DEV intent-wrong rows
(the Fold A order and the Fold A predicates):

  ``delivered-but-wrong``   gold delivered under the plan selection
  ``newly-by-both``         in the agree set AND the centroid set
  ``newly-by-agree``        in the agree set only
  ``newly-by-centroid``     in the centroid set only
  ``catch-all``             none of the above

where the AGREE set is CONV's predicate (bank ``INTENT-UNCOVERED`` rows whose
gold boundary id is in the agree fusion and not in the plan fusion) and the
CENTROID set is KPROBE's predicate (bank ``INTENT-UNCOVERED`` or
``INTENT-COVERED`` rows whose gold boundary id is in the centroid fusion and not
in the plan fusion). ``INTENT-COVERED`` rows the agreement term newly delivers
are therefore NOT in the agree set, exactly as on Fold A (2 such rows there);
they are counted beside the table as ``agree_newly_delivered_intent_covered``.

COUNTS AND HASHES ONLY. The membership is persisted as per-class row counts and
the sha256 of each class's LF-joined sorted sample-id list, so it is fixed before
contact; the read re-runs this script and must reproduce every hash. No
utterance text, transcript, gold label string, intent name, knowledge body or
model output is printed or persisted. ZERO model, server, encoder, embedder,
scorer, tokenizer, network, GPU and paid-API contacts.

    PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 python \\
        scripts/flights/comp1dev/comp1dev_attribution_classes.py \\
        --repo-root . --data-root "$SPEECHRL_DATA_DIR" \\
        --lock-path /mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json \\
        --output docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/attribution-classes-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails.kb_policy import (  # noqa: E402
    EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
)
from speech_aware_evidence_acquisition.rails.phase_supply import (  # noqa: E402
    load_sealed_agreement,
)

SCHEMA = "saea-comp1-attribution-classes-v1"
DERIVATION_ID = "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-ATTRIBUTION-CLASSES-V1"
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1"
FACTS = f"{PACKAGE}/registered-facts-v1.json"
REPLICATION_RECIPE = Path("scripts/analysis/slurp_intent_agreement_production_replication.py")
FOLD_A_CLASSES = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json"
ARM_LABEL = "dev2000-added-plan"
BANK_ROSTER = "dev2000-added"
AA_SUPPLY = "prepared/SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1/phase-supply-v1.json"
ARM_SUPPLY = "prepared/SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1/phase-supply-v1.json"
AA_OUTPUT_SHA = "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"
ARM_OUTPUT_SHA = "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"
PHASE = "perception"
ROWS = 1000
FLOWN_K = 8
RECALL_WIDTH = 60
INTENT_WRONG = ("INTENT-UNCOVERED", "INTENT-COVERED")
AGREE_POPULATION = ("INTENT-UNCOVERED",)  # CONV's predicate, verbatim
CENTROID_POPULATION = INTENT_WRONG  # KPROBE's predicate, verbatim
CLASSES = ("delivered-but-wrong", "newly-by-both", "newly-by-agree", "newly-by-centroid", "catch-all")


class DeriveError(RuntimeError):
    pass


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def id_list_sha256(ids) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def bare(value_id: str) -> str:
    return value_id.split("::", 1)[1] if "::" in value_id else value_id


def import_module(repo: Path, relpath: Path, name: str):
    path = repo / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DeriveError(f"cannot import {relpath}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sha_file(path)


def load_supply(path: Path, expected_output: str) -> tuple[dict, dict[str, frozenset]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("kind") != "phase-supply" or set(document["output"]["values"]) != {PHASE}:
        raise DeriveError(f"{path} is not a {PHASE} phase-supply artifact")
    if document["output_sha256"] != expected_output:
        raise DeriveError(f"{path} output digest is not the registered {expected_output[:8]}")
    values = document["output"]["values"][PHASE]
    return document, {str(k): frozenset(bare(str(x)) for x in v) for k, v in values.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--lock-path", required=True)
    parser.add_argument("--output", required=True, help="repo-relative output path")
    args = parser.parse_args(argv)
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
    repo = Path(args.repo_root).resolve()
    data = Path(args.data_root).resolve()
    lock_path = Path(args.lock_path).resolve()

    recipe, recipe_sha = import_module(repo, REPLICATION_RECIPE, "_saea_agreement_replication")
    facts = json.loads((repo / FACTS).read_text(encoding="utf-8"))
    composition = facts["the_composition"]
    agreement_pin = dict(composition["factor_1_agreement_term"]["agreement_source"])
    centroid_pin = dict(composition["factor_2_centroid_key"]["facet_source"])

    # --- gold, scoring side only: the bank, exactly as the Fold A script reads it
    arm = next(a for a in recipe.ARMS if a["label"] == ARM_LABEL)
    bank = recipe.load_bank(data)
    population = recipe.load_population(data, arm, bank, {})  # asserts 169 / 63
    rows = population["rows"]
    if len(rows) != ROWS:
        raise DeriveError(f"the bank's {BANK_ROSTER} roster has {len(rows)} rows, not {ROWS}")

    # --- the flown selections
    aa_doc, aa_values = load_supply(data / AA_SUPPLY, AA_OUTPUT_SHA)
    arm_doc, arm_values = load_supply(data / ARM_SUPPLY, ARM_OUTPUT_SHA)
    if not set(aa_values) <= set(rows) or not set(arm_values) <= set(rows):
        raise DeriveError("a prepared supply seeds a row outside the DEV roster")

    # --- the production constructor, four decisions per row
    channels = recipe.arm_channels(repo, data, lock_path, arm)
    if set(channels["packets"]) != set(rows):
        raise DeriveError("the sealed DEV plan cell's roster is not the bank's DEV roster")
    spec = channels["specs"][recipe.BOUNDARY_STORE]
    if spec.k != FLOWN_K or dict(spec.fuse_coverage or {}) != {"m": 8, "c": 1, "top_l": 8}:
        raise DeriveError("the sealed DEV plan arm's boundary channel is not the flown k 8 / 8-1-8")
    if dict(spec.rank_weights or {}).get("w_agree", 0.0) != 0.0:
        raise DeriveError("the sealed DEV plan arm's boundary channel is not at w_agree 0.0")
    snapshot = channels["snapshots"][recipe.BOUNDARY_STORE]
    table = load_sealed_agreement(
        data / str(agreement_pin["relpath"]),
        expected_sha256=str(agreement_pin["sha256"]),
        dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
        facet_ids=sorted(facet.facet_id for facet in snapshot.facets),
    )
    centroid_channels = dict(channels)
    centroid_channels["specs"] = dict(channels["specs"])
    centroid_channels["specs"][recipe.BOUNDARY_STORE] = replace(spec, facet_source=centroid_pin)

    plan = recipe.boundary_decisions(data, arm, channels, None, 0.0, FLOWN_K)
    agree = recipe.boundary_decisions(data, arm, channels, table, 1.0, RECALL_WIDTH)
    centroid = recipe.boundary_decisions(data, arm, centroid_channels, None, 0.0, FLOWN_K)
    composed = recipe.boundary_decisions(data, arm, centroid_channels, table, 1.0, RECALL_WIDTH)

    def fused(decision: dict, sid: str) -> frozenset:
        return frozenset(decision["rows"][sid]["fused"])

    plan_mismatch = sorted(s for s in rows if fused(plan, s) != aa_values.get(s, frozenset()))
    composed_mismatch = sorted(s for s in rows if fused(composed, s) != arm_values.get(s, frozenset()))
    if plan_mismatch:
        raise DeriveError(f"the plan recomputation differs from the A/A supply on {len(plan_mismatch)} rows")
    if composed_mismatch:
        raise DeriveError(f"the composed recomputation differs from the arm supply on {len(composed_mismatch)} rows")

    def has_gold(selection: frozenset, sid: str) -> bool:
        return f"{recipe.BOUNDARY_DIM}:{rows[sid]['gold_intent']}" in selection

    wrong = sorted(s for s, r in rows.items() if r["plan_class"] in INTENT_WRONG)
    per_row: dict[str, dict] = {}
    for sid in rows:
        pc = rows[sid]["plan_class"]
        d_plan = has_gold(aa_values.get(sid, frozenset()), sid)
        d_agree = has_gold(fused(agree, sid), sid)
        d_centroid = has_gold(fused(centroid, sid), sid)
        d_comp = has_gold(arm_values.get(sid, frozenset()), sid)
        per_row[sid] = {
            "plan_class": pc,
            "d_plan": d_plan, "d_agree": d_agree, "d_centroid": d_centroid, "d_comp1": d_comp,
            "in_agree_set": pc in AGREE_POPULATION and d_agree and not d_plan,
            "in_centroid_set": pc in CENTROID_POPULATION and d_centroid and not d_plan,
            "agree_new_covered": pc == "INTENT-COVERED" and d_agree and not d_plan,
            "seeded_comp1": sid in arm_values,
            "seeded_aa": sid in aa_values,
        }
    for sid in wrong:
        r = per_row[sid]
        if r["d_plan"]:
            klass = "delivered-but-wrong"
        elif r["in_agree_set"] and r["in_centroid_set"]:
            klass = "newly-by-both"
        elif r["in_agree_set"]:
            klass = "newly-by-agree"
        elif r["in_centroid_set"]:
            klass = "newly-by-centroid"
        else:
            klass = "catch-all"
        r["class"] = klass

    classes = {}
    for klass in CLASSES:
        members = sorted(s for s in wrong if per_row[s]["class"] == klass)
        classes[klass] = {
            "rows": len(members),
            "id_list_sha256": id_list_sha256(members),
            "by_plan_class": dict(sorted(Counter(per_row[s]["plan_class"] for s in members).items())),
            "delivered_under_comp1": sum(per_row[s]["d_comp1"] for s in members),
            "not_delivered_under_comp1": sum(not per_row[s]["d_comp1"] for s in members),
            "delivered_under_agree_alone": sum(per_row[s]["d_agree"] for s in members),
            "delivered_under_centroid_alone": sum(per_row[s]["d_centroid"] for s in members),
            "outcome_under_comp1": "READ AFTER THE SEAL: per row, intent exact under COMP-1 / under the in-chain A/A / under the sealed DEV plan arm (official slurp-slu-official scenario_action_exact)",
        }

    agree_set = {s for s in wrong if per_row[s]["in_agree_set"]}
    centroid_set = {s for s in wrong if per_row[s]["in_centroid_set"]}
    lost = sorted(s for s in wrong if (per_row[s]["d_plan"] or s in agree_set or s in centroid_set) and not per_row[s]["d_comp1"])
    gained_beyond = sorted(s for s in wrong if per_row[s]["class"] == "catch-all" and per_row[s]["d_comp1"])
    covered_agree = sorted(s for s in wrong if per_row[s]["agree_new_covered"])

    by_class_all = {}
    for pc in sorted({r["plan_class"] for r in per_row.values()}):
        members = [r for r in per_row.values() if r["plan_class"] == pc]
        by_class_all[pc] = {
            "rows": len(members),
            "delivered_plan": sum(r["d_plan"] for r in members),
            "delivered_comp1": sum(r["d_comp1"] for r in members),
            "lost_under_comp1": sum(r["d_plan"] and not r["d_comp1"] for r in members),
            "gained_under_comp1": sum(r["d_comp1"] and not r["d_plan"] for r in members),
        }

    fold_a = json.loads((repo / FOLD_A_CLASSES).read_text(encoding="utf-8"))
    result = {
        "schema": SCHEMA,
        "derivation_id": DERIVATION_ID,
        "contact_class": "model-free",
        "contacts": {k: 0 for k in ("model", "server", "encoder", "embedder", "scorer", "tokenizer", "network", "gpu", "paid_api")},
        "script": {"relpath": "scripts/flights/comp1dev/comp1dev_attribution_classes.py"},
        "inputs": {
            "bad_case_bank": {"relpath": recipe.BANK, "sha256": bank["sha256"], "roster": BANK_ROSTER,
                              "raw_classes": population["raw_classes"]},
            "replication_recipe": {"relpath": str(REPLICATION_RECIPE), "sha256": recipe_sha, "imported_unchanged": True,
                                   "functions_used": ["load_bank", "load_population", "arm_channels", "boundary_decisions"]},
            "comparator_cell": {"run_id": arm["run_id"], "experiment": arm["experiment"], "attempt_id": channels["attempt_id"],
                                "split_identity_hash": channels["split_identity_hash"]},
            "aa_supply": {"relpath": AA_SUPPLY, "sha256": sha_file(data / AA_SUPPLY), "output_sha256": aa_doc["output_sha256"]},
            "arm_supply": {"relpath": ARM_SUPPLY, "sha256": sha_file(data / ARM_SUPPLY), "output_sha256": arm_doc["output_sha256"]},
            "agreement_source": {"relpath": agreement_pin["relpath"], "sha256": agreement_pin["sha256"]},
            "centroid_facet_source": {"relpath": centroid_pin["relpath"], "sha256": centroid_pin["sha256"]},
            "registered_facts": {"relpath": FACTS, "sha256": sha_file(repo / FACTS)},
        },
        "constructor_proofs": {
            "plan_recomputation_equals_aa_supply_rows": ROWS - len(plan_mismatch),
            "composed_recomputation_equals_arm_supply_rows": ROWS - len(composed_mismatch),
            "rows": ROWS,
            "decisions": {
                "plan": plan["pins"]["rank_weights_used"] | {"recall": FLOWN_K, "key": "written"},
                "agree": agree["pins"]["rank_weights_used"] | {"recall": RECALL_WIDTH, "key": "written"},
                "centroid": centroid["pins"]["rank_weights_used"] | {"recall": FLOWN_K, "key": "centroid"},
                "composed": composed["pins"]["rank_weights_used"] | {"recall": RECALL_WIDTH, "key": "centroid"},
            },
        },
        "delivery_definition": (
            "a row's gold intent's boundary value id (intent-boundary:<gold intent>) is among the value ids the "
            "selection seeds for that row -- the eight (or fewer) entries the Perception phase is shown"
        ),
        "set_predicates": {
            "agree_set": "bank plan_class INTENT-UNCOVERED and gold delivered under agree and not under plan (cell CONV's predicate)",
            "centroid_set": "bank plan_class INTENT-UNCOVERED or INTENT-COVERED and gold delivered under centroid and not under plan (cell KPROBE's predicate)",
        },
        "class_order": list(CLASSES),
        "intent_wrong_rows": len(wrong),
        "classes": classes,
        "summary": {
            "delivered_under_plan": classes["delivered-but-wrong"]["rows"],
            "agree_set": len(agree_set),
            "centroid_set": len(centroid_set),
            "newly_by_both": classes["newly-by-both"]["rows"],
            "union_newly_delivered": len(agree_set | centroid_set),
            "delivered_under_comp1": sum(per_row[s]["d_comp1"] for s in wrong),
            "delivered_under_comp1_pct_of_intent_wrong": round(100.0 * sum(per_row[s]["d_comp1"] for s in wrong) / len(wrong), 1),
            "rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1": len(lost),
            "rows_delivered_by_plan_or_a_single_factor_but_not_under_comp1_id_list_sha256": id_list_sha256(lost),
            "catch_all_rows_delivered_only_under_the_composition": len(gained_beyond),
            "catch_all_rows_delivered_only_under_the_composition_id_list_sha256": id_list_sha256(gained_beyond),
            "agree_newly_delivered_intent_covered": len(covered_agree),
            "agree_newly_delivered_intent_covered_id_list_sha256": id_list_sha256(covered_agree),
        },
        "all_rows_by_bank_class": by_class_all,
        "rows_unseeded_under_comp1": sum(not r["seeded_comp1"] for r in per_row.values()),
        "rows_unseeded_under_aa": sum(not r["seeded_aa"] for r in per_row.values()),
        "fold_a_beside": {
            "relpath": FOLD_A_CLASSES,
            "sha256": sha_file(repo / FOLD_A_CLASSES),
            "intent_wrong_rows": fold_a["intent_wrong_rows"],
            "counts": {k: v["rows"] for k, v in fold_a["classes"].items()},
        },
        "gold_use": (
            "Gold is read on the SCORING side only -- the bad-case bank's plan_class (itself derived from the "
            "sealed DEV plan arm's official per-sample scenario_action_exact) and gold_intent, read from "
            "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl by the replication recipe's load_bank exactly as "
            "the Fold A script reads the same file -- to define the read's classes before contact. Gold reaches "
            "no query, no key, no weight, no selector and no runtime."
        ),
        "persistence": (
            "Counts and per-class id-list hashes only; the read re-runs this script and must reproduce every "
            "id_list_sha256 before a class outcome is tabulated."
        ),
        "what_this_is_not": (
            "Not a verdict, not a claim and not a prediction: membership only. A delivery count is never a "
            "correctness count; every number is a DEV-2000-ADDED development number, never a test claim."
        ),
    }
    out_path = repo / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"written": args.output, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "summary": result["summary"], "proofs": result["constructor_proofs"],
                      "classes": {k: {kk: vv for kk, vv in v.items() if kk not in ("outcome_under_comp1", "id_list_sha256")} for k, v in classes.items()},
                      "all_rows": by_class_all}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DeriveError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        raise SystemExit(1)
