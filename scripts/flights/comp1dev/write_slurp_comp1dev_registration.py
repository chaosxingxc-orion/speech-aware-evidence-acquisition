#!/usr/bin/env python3
"""Write cell COMP-1 DEV-2000-ADDED's registration package -- the replication of the
first composed Stage-3 arm on the fresh evaluation roster (owner decision 161) -- from
the committed configs.

Reads the three derived fragments, recomposes every hash, PROVES from the composed
configs that (a) the arm differs from the sealed DEV-2000-ADDED plan cell by exactly the
three composed factors, the recall width and per-flight bookkeeping, the A/A by the
recall width and bookkeeping alone, and the arm from the A/A by the three factors alone;
and (b) the arm differs from cell COMP-1's Fold A arm ONLY where the sealed DEV plan arm
differs from the locked Fold A plan (the roster re-point), plus this roster's own
agreement-table pin and per-flight bookkeeping -- i.e. the plan bytes are COMP-1's. It
reads the three prepared first-phase supplies (the A/A's output digest must be the sealed
DEV comparator's ``d57ee9d6...``), writes the package documents, six plan documents, the
analysis recipe (read driver ``scripts/flights/read_paired_cell.sh``, DEV scorer
``slurp-slu-official``), a draft decision receipt, the README, the preregistration and
(with ``--append-ledger``) eight DRAFT exposure rows: six flight/FIT rows, the model-free
agreement-table build row and the READ row.

THE EXPECTATION IS NOT DECLARED HERE. ``expected_effect_pp`` of the arm is the literal
string ``TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ`` in both places the gate
reads (owner decision 139: no if-then on unread results; the Fold A arm has not flown).
``scripts/checks/stage3_effect_floor_check.py`` refuses the arm as ``unparsable-declaration``
until the coordinator replaces it -- exactly the state COMP-1 Fold A was registered in.

Config and receipt-pinned bytes alone: no contact of any kind; flips nothing, mints nothing.

    python scripts/flights/comp1dev/write_slurp_comp1dev_registration.py \\
        --package-dir docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1 \\
        --data-root "$SPEECHRL_DATA_DIR" --study-commit <sha> \\
        --registered-at 2026-09-27T23:59:00.000000+00:00 [--check-dir <dir>] [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PARENT_EXPERIMENT = "slurp-native-default-plan-dev2000-added-v1"
FOLD_A_LOCK_EXPERIMENT = "slurp-native-default-plan-lock-v1"
FOLD_A_COMP1_EXPERIMENT = "slurp-native-stage3-comp1-fold-a-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-dev2000-added-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 65.40, "intent_accuracy": 76.6}
REPLICATE_OF_COMPARATOR = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DEV_PLAN_SUPPLY_OUTPUT_SHA = "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"
PLACEHOLDER = "TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
ROSTER_ID = "SLURP-DEV-2000-ADDED-V1"
SCORER = "slurp-slu-official"

CELLS = {
    "arm": "slurp-native-stage3-comp1-dev2000-added-v1",
    "aa": "slurp-native-stage3-comp1-aa-dev2000-added-v1",
    "smoke": "slurp-native-stage3-comp1-dev2000-added-smoke-4-v1",
}
PACKAGE_NAME = "slurp-stage3-comp1-dev2000-added-v1"
DECISION_ID = "slurp-stage3-comp1-dev2000-added-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1-dev2000-added-v1.json"
READ_RUN = "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
ANALYSIS_ROOT = f"analysis/{READ_RUN}"
READ_DRIVER = "scripts/flights/read_paired_cell.sh"

FOLD_A_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
ROLL3_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1"
B6_PACKAGE = "docs/readiness/2026-09-22-slurp-b6-dev2000-added-v1"
B6_READ = "docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md"
RECLASSIFICATION = "docs/results/2026-09-27-verdict-reclassification.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
AGREEMENT_ROW = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1"
AGREEMENT_RECEIPT = f"prepared/{AGREEMENT_ROW}/receipt.json"
AGREEMENT_BUILDER = "scripts/build_slurp_intent_exemplar_agreement.py"
CENTROID_RECEIPT = "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json"
DERIVE_SCRIPT = "scripts/flights/comp1dev/derive_slurp_comp1dev_cells.py"
LEDGER = "docs/exposure-ledger.md"

#: The own null of the plan on THIS roster (instrument note section 2d, row
#: "cross-flight A/A, DEV-2000-ADDED": the B6 pair PLAN vs PLANr-DEV2000).
OWN_NULL = {"h_intent": 1.1520, "h_slu": 1.2525, "n": 1000, "measured_offset_slu_pp": -0.25,
            "source": INSTRUMENT + " section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"}
BAR_PP_N1000 = 2.60

BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
FACTOR_PATHS = {
    "factor_1_agreement_term": (f"{BOUNDARY}.rank_weights.w_agree", f"{BOUNDARY}.agreement_source."),
    "factor_2_centroid_key": (f"{BOUNDARY}.facet_source.",),
    "factor_3_citation_contract": (
        "policy", "phase_material.solver.instruction_template", "phase_material.solver.response_format_id",
        "native_episode.deliver_normaliser.normaliser",
    ),
}
RECALL_WIDTH_PATH = f"{BOUNDARY}.k"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")
#: Roster-bound pins of the agreement factor (the table is this roster's own).
AGREEMENT_PIN_PATHS = (f"{BOUNDARY}.agreement_source.relpath", f"{BOUNDARY}.agreement_source.sha256",
                       f"{BOUNDARY}.agreement_source.tool_contact_ledger_row")


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def changed_paths(a: dict, b: dict) -> list[str]:
    fa, fb = flatten(a), flatten(b)
    return sorted(k for k in set(fa) | set(fb) if fa.get(k, "<absent>") != fb.get(k, "<absent>"))


def classify_diff(parent_values, mine, experiment_keys, baseline_keys, *, allowed) -> dict:
    changed = changed_paths(parent_values, mine)

    def matches(key: str, path: str) -> bool:
        return key == path or (path.endswith(".") and key.startswith(path))

    factor = [k for k in changed if any(matches(k, p) for p in allowed)]
    bookkeeping = [k for k in changed if k not in factor and k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k not in factor and k not in bookkeeping and k.split(".", 1)[0] in experiment_keys]
    other = [k for k in changed if k not in factor and k not in bookkeeping and k not in experiment_block]
    return {"factor_paths": factor, "bookkeeping": bookkeeping, "experiment_fragment_own_block": experiment_block, "anything_else": other}


def composed_of(experiment: str):
    document = json.loads(rd(f"configs/experiment/{experiment}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def supply_facts(data_root: Path, relpath: str) -> dict:
    path = data_root / relpath
    document = json.loads(path.read_text(encoding="utf-8"))
    values = document["output"]["values"]
    rows = {sid: ids for phase in values.values() for sid, ids in phase.items()}
    return {
        "relpath": relpath, "file_sha256": sha_file(path), "output_sha256": document["output_sha256"],
        "kind": document["kind"], "contact_class": document["contact_class"],
        "rows_seeded": len(rows), "selected_value_ids": sum(len(ids) for ids in rows.values()),
        "supply_spec_rank_weights": document["inputs"]["sources"]["supply_spec"].get("rank_weights"),
        "supply_spec_facet_source_sha256": document["inputs"]["sources"]["supply_spec"]["facet_source"]["sha256"],
        "supply_spec_declares_agreement_source": "agreement_source" in document["inputs"]["sources"]["supply_spec"],
        "_rows": rows,
    }


def delivery_change(arm: dict, aa: dict) -> dict:
    """Gold-free: how the composed first-phase selection differs from the A/A's per row."""

    rows = sorted(set(arm) | set(aa))
    same_set = sum(1 for r in rows if set(arm.get(r, ())) == set(aa.get(r, ())))
    same_order = sum(1 for r in rows if list(arm.get(r, ())) == list(aa.get(r, ())))
    overlap = [len(set(arm.get(r, ())) & set(aa.get(r, ()))) for r in rows]
    histogram: dict[str, int] = {}
    for value in overlap:
        histogram[str(value)] = histogram.get(str(value), 0) + 1
    return {
        "rows": len(rows),
        "rows_seeded_by_arm": len(arm), "rows_seeded_by_aa": len(aa),
        "rows_seeded_by_arm_only": sorted(set(arm) - set(aa)), "rows_seeded_by_aa_only": sorted(set(aa) - set(arm)),
        "rows_with_identical_selected_set": same_set, "rows_with_identical_ordered_selection": same_order,
        "rows_with_a_changed_selected_set": len(rows) - same_set,
        "overlap_histogram_selected_ids": dict(sorted(histogram.items(), key=lambda kv: int(kv[0]))),
        "what_this_is": "gold-free delivery change of the first-phase boundary selection, arm vs in-chain A/A; no gold, no label and no outcome enters it, so it is NOT the per-class attribution membership (see open_items)",
    }


def fold_check(check_dir: str | None, cells: dict) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK", "note": "run core.flight.cli check on the three cells after the exposure rows exist and re-run this writer with --check-dir"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in cells.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            entry = {"phase": receipt.get("phase"), "decision": receipt.get("decision")}
            for name in ("physical_margin_tokens", "operational_margin_tokens", "serving_slot_limit_tokens", "operational_limit_tokens"):
                if name in receipt:
                    entry[name] = receipt[name]
            breakdown = receipt.get("breakdown") if isinstance(receipt.get("breakdown"), dict) else {}
            for name in ("rendered_text_tokens", "required_window_tokens", "completion_token_ceiling", "speech_feature_tokens"):
                if name in breakdown:
                    entry[name] = breakdown[name]
                elif name in receipt:
                    entry[name] = receipt[name]
            phases.append(entry)
        out["cells"][key] = {
            "check_path": str(path), "scientific_readiness": report.get("scientific_readiness"),
            "blockers": report.get("blockers"), "config_hash": preflight.get("config_hash"),
            "protocol_hash": preflight.get("protocol_hash"), "prompt_budget_per_phase": phases,
        }
    return out


THE_COMPOSITION_SHORT = (
    "cell COMP-1's composed plan with only the roster moved: the locked v2.0 plan as the sealed DEV-2000-ADDED plan arm "
    "flew it + (1) the agreement term as AGREE carries it (w_agree 1.0 over the exemplar-intent vote, recall k 60, "
    "delivered 8-1-8; the vote table is this roster's own SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + "
    "(2) the centroid boundary key as KPROBE pins it (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/"
    "facets.jsonl) + (3) the citation contract (policy phase-native-candidates-review-revise-cited-v1, Solver "
    "response_format_id saea-solver-cited-answer-v1, instruction probes/slurp_native_role_solver_cited_v1.txt, "
    "deliver_normaliser saea-deliver-cited-answer-normalise-v3-v1) + (4) nothing else"
)
MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; NO native tool authority on "
    "any role; Perception / Reviewer / Planner prompt bytes the sealed DEV-2000-ADDED plan arm's; the Solver under the "
    "cited-answer contract (+134 instruction tokens) on the arm and the smoke, the locked plan's on the A/A"
)
INHERITED = (
    "DEV-2000-ADDED dev rows already exposed by the model-free speech-query encoding pass, the sealed B6 direct and plan "
    "arms, PLANr-DEV2000, CELL-3 and its twin, and ROLL-3 (whose smoke flew the same four smoke rows); this cell adds "
    "no new row and opens no split. Prior exposure is inherited in full."
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/comp1dev")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-comp1dev")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    data_root = Path(args.data_root).resolve()

    # ---- identities ------------------------------------------------------
    ids: dict[str, dict] = {}
    composed: dict[str, object] = {}
    documents: dict[str, dict] = {}
    for key, experiment in CELLS.items():
        document, cell, comp = composed_of(experiment)
        documents[key] = document
        composed[key] = comp
        split = document["population"]["split_identity_hash"]
        fit = comp.values["native_contact_fit"]
        own_supply = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json"))
        perception = comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
        ids[key] = {
            "cell": cell["cell_id"], "experiment": experiment, "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": fit["run_id"], "fit_attempt_id": fit["attempt_id"], "fit_contact_cap": fit["contact_cap"],
            "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": comp.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "split_role": document["execution_plan"]["split_role"],
            "composed_config_hash": comp.config_hash, "protocol_hash": protocol_hash(comp.config_hash, comp.values["arm"], split),
            "family_budget": document["family_budget"], "readiness_state": cell["readiness"]["state"],
            "own_supply_requirement": own_supply,
            "boundary": {k: perception.get(k) for k in ("k", "tau", "rank_weights", "fuse_coverage")},
            "boundary_facet_source_sha256": perception["facet_source"]["sha256"],
            "declares_agreement_source": "agreement_source" in perception,
            "agreement_source_sha256": (perception.get("agreement_source") or {}).get("sha256"),
            "policy": comp.values["policy"], "solver_material": comp.values["phase_material"]["solver"],
            "deliver_normaliser": comp.values["native_episode"]["deliver_normaliser"],
            "scorers": comp.values["scorers"], "stage3_algorithm": document["stage3_algorithm"],
        }
    for key in CELLS:
        if ids[key]["readiness_state"] != "held":
            raise SystemExit(f"{key} is not held")
        if ids[key]["scorers"] != [SCORER, "cost"]:
            raise SystemExit(f"{key} does not score with the DEV sibling {SCORER}")
        if ids[key]["split_role"] != "dev":
            raise SystemExit(f"{key} is not split role dev")

    # ---- proof (a): against the sealed DEV plan cell ---------------------
    parent_doc, parent_cell, parent = composed_of(PARENT_EXPERIMENT)
    baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
    all_factor_paths = tuple(p for paths in FACTOR_PATHS.values() for p in paths)
    diffs = {
        "arm_vs_dev_plan": classify_diff(parent.values, composed["arm"].values, set(documents["arm"]) | set(parent_doc), baseline_keys, allowed=all_factor_paths + (RECALL_WIDTH_PATH,)),
        "aa_vs_dev_plan": classify_diff(parent.values, composed["aa"].values, set(documents["aa"]) | set(parent_doc), baseline_keys, allowed=(RECALL_WIDTH_PATH,)),
        "arm_vs_aa": classify_diff(composed["aa"].values, composed["arm"].values, set(documents["arm"]) | set(documents["aa"]), baseline_keys, allowed=all_factor_paths),
        "smoke_vs_arm": classify_diff(composed["arm"].values, composed["smoke"].values, set(documents["smoke"]) | set(documents["arm"]), baseline_keys, allowed=()),
    }
    for name, diff in diffs.items():
        if diff["anything_else"]:
            raise SystemExit(f"{name}: the composed config differs beyond the registered factors and bookkeeping: {diff['anything_else']}")
    for factor, paths in FACTOR_PATHS.items():
        for path in paths:
            if not [k for k in diffs["arm_vs_aa"]["factor_paths"] if k == path or (path.endswith(".") and k.startswith(path))]:
                raise SystemExit(f"{factor}: {path} did not move between the A/A and the arm")
    if diffs["aa_vs_dev_plan"]["factor_paths"] != [RECALL_WIDTH_PATH]:
        raise SystemExit("the A/A must differ from the DEV plan by the recall width alone (plus bookkeeping)")
    if RECALL_WIDTH_PATH in diffs["arm_vs_aa"]["factor_paths"]:
        raise SystemExit("the arm and the A/A must share the recall width")

    # ---- proof (b): the plan bytes are COMP-1 Fold A's -------------------
    lock_doc, _lock_cell, lock = composed_of(FOLD_A_LOCK_EXPERIMENT)
    fa_doc, _fa_cell, fold_a = composed_of(FOLD_A_COMP1_EXPERIMENT)
    roster_repoint = set(changed_paths(lock.values, parent.values))
    comp1_vs_fold_a = changed_paths(fold_a.values, composed["arm"].values)
    unexplained = [k for k in comp1_vs_fold_a if k not in roster_repoint and k not in AGREEMENT_PIN_PATHS
                   and not k.startswith(BOOKKEEPING_PREFIXES) and k.split(".", 1)[0] not in (set(documents["arm"]) | set(fa_doc))]
    if unexplained:
        raise SystemExit(f"the DEV arm differs from COMP-1 Fold A beyond the roster re-point: {unexplained}")
    plan_bytes_proof = {
        "claim": "the DEV arm is cell COMP-1's Fold A arm with ONLY the roster moved: every composed-config path on which they differ is either a path on which the sealed DEV plan arm differs from the locked Fold A plan (the roster re-point B6 made), this roster's own agreement-table pin, per-flight bookkeeping, or the experiment fragment's own block",
        "roster_repoint_paths_dev_plan_vs_fold_a_lock": sorted(roster_repoint),
        "dev_arm_vs_fold_a_arm_paths": comp1_vs_fold_a,
        "agreement_pin_paths": list(AGREEMENT_PIN_PATHS),
        "unexplained": unexplained,
    }
    arm_p = composed["arm"].values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    fa_p = fold_a.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    for key in ("rank_weights", "k", "fuse_coverage", "tau", "rank_policy", "fuse_policy", "facet_source"):
        if arm_p[key] != fa_p[key]:
            raise SystemExit(f"the DEV arm's boundary {key} is not COMP-1 Fold A's")
    for key in ("policy",):
        if composed["arm"].values[key] != fold_a.values[key]:
            raise SystemExit("the DEV arm's policy is not COMP-1 Fold A's")
    if composed["arm"].values["phase_material"]["solver"] != fold_a.values["phase_material"]["solver"] or composed["arm"].values["native_episode"] != fold_a.values["native_episode"]:
        raise SystemExit("the DEV arm's Solver material or native episode is not COMP-1 Fold A's")

    # ---- supplies ----------------------------------------------------------
    supplies_full = {key: supply_facts(data_root, ids[key]["own_supply_requirement"]["relpath"]) for key in CELLS}
    for key in CELLS:
        if supplies_full[key]["file_sha256"] != ids[key]["own_supply_requirement"]["sha256"]:
            raise SystemExit(f"{key}: the committed supply requirement does not hash to the artifact on the data root")
    if supplies_full["aa"]["output_sha256"] != DEV_PLAN_SUPPLY_OUTPUT_SHA:
        raise SystemExit("the A/A's prepared output digest is not the sealed DEV comparator's d57ee9d6...")
    if supplies_full["arm"]["output_sha256"] == DEV_PLAN_SUPPLY_OUTPUT_SHA:
        raise SystemExit("the composed arm's prepared output digest equals the default's; the composition is inert")
    change = delivery_change(supplies_full["arm"]["_rows"], supplies_full["aa"]["_rows"])
    supplies = {key: {k: v for k, v in value.items() if k != "_rows"} for key, value in supplies_full.items()}

    agreement_receipt = json.loads((data_root / AGREEMENT_RECEIPT).read_text(encoding="utf-8"))
    agreement_facts = {
        "artifact_id": AGREEMENT_ROW, "relpath": agreement_receipt["artifact"]["relpath"], "sha256": agreement_receipt["artifact"]["sha256"],
        "receipt_relpath": AGREEMENT_RECEIPT, "receipt_sha256": sha_file(data_root / AGREEMENT_RECEIPT),
        "builder": AGREEMENT_BUILDER, "builder_sha256": agreement_receipt["builder_sha256"],
        "derived_from": {k: v for k, v in agreement_receipt["derived_from"].items() if k != "vote_spec"},
        "measured": agreement_receipt["measured"], "contacts": agreement_receipt["contacts"],
    }

    fit = fold_check(args.check_dir, CELLS)
    caps = ids["arm"]["family_budget"]
    smoke_caps = ids["smoke"]["family_budget"]

    exclusion = {
        "claim": "No knowledge the arm or the A/A reads was constructed from a DEV-2000-ADDED row.",
        "roster_receipt": {"relpath": ROSTER_RECEIPT, "sha256": sha_file(ROSTER_RECEIPT),
                            "disjointness_proof": json.loads(rd(ROSTER_RECEIPT))["disjointness_proof"]},
        "train_exemplars_store": "size-pool-annotated-exemplars, the PARENT TRAIN-built pool the sealed DEV plan arm, PLANr-DEV2000, CELL-3 and ROLL-3 all read (" + ROLL3_PACKAGE + "/registered-facts-v1.json train_exemplars_store): disjoint from every DEV-2000-ADDED recording by the roster receipt's disjointness_proof (shared_with_train_construction_recordings = 0, non_devel_ids_added = 0)",
        "agreement_table": "its vote pool is the same train-exemplars snapshot (vote_snapshot_sha256 " + agreement_receipt["derived_from"]["vote_snapshot_sha256"] + "); the builder's utterance-identity self-exclusion MEASURED self_excluded_exemplars = " + str(agreement_receipt["measured"]["self_excluded_exemplars"]) + " and rows_with_a_self_excluded_exemplar = " + str(agreement_receipt["measured"]["rows_with_a_self_excluded_exemplar"]) + " over all 1,000 rows (" + AGREEMENT_RECEIPT + ")",
        "centroid_keys": "built from the R01-excluded construction-TRAIN pool (knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json, 8,554 TRAIN utterances), whose receipt states the one file is held out on TRAIN Fold A, ROLL-1 (R01C) and DEV-2000-ADDED alike (" + CENTROID_RECEIPT + " construction.construction_pool); a subset of the TRAIN pool above, so the same disjointness proof covers it",
        "stores_and_releases": "intent-boundaries-v1 and slot-contracts-v1 snapshots and releases unchanged from the sealed DEV plan arm (proof (a): no store path moves)",
    }

    measurement = {
        ids["arm"]["run_id"]: {
            "claims_benefit": True,
            "expected_effect_pp": PLACEHOLDER,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official, DEV sibling) the non-inferiority guard (owner decision 133)",
            "replicate_run_id": ids["aa"]["run_id"],
            "rows": 1000,
            "roster": "DEV-2000-ADDED (" + ROSTER_ID + ", split identity " + ids["arm"]["split_identity_hash"] + ")",
            "own_null": {"h_intent": OWN_NULL["h_intent"], "h_slu": OWN_NULL["h_slu"], "n": 1000, "source": OWN_NULL["source"]},
            "note": (
                "The DEV-2000-ADDED replication of cell COMP-1 (owner decision 161; " + RECLASSIFICATION + " -- this round "
                "settles AGREE's KEEP-PROVISIONAL), read against the in-chain A/A at intent primary with official SLU-F1 the "
                "guard, at the plan's own null on this roster (h_intent 1.1520, h_SLU 1.2525; " + INSTRUMENT + " section 2d). "
                "expected_effect_pp is DELIBERATELY the literal string " + PLACEHOLDER + ": owner decision 139 forbids an if-then "
                "on unread results and the COMP-1 Fold A arm has not flown. Until the coordinator replaces the string with a "
                "number here AND in the preregistration fence, scripts/checks/stage3_effect_floor_check.py refuses this cell as "
                "unparsable-declaration -- the intended state, exactly as COMP-1 Fold A was registered. Delivery is not correctness."
            ),
        },
        ids["aa"]["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
            "replicate_run_id": ids["arm"]["run_id"], "rows": 1000,
            "note": "The A/A replicate is the INSTRUMENT, not a claim: the sealed DEV plan arm's own bytes (w_agree 0.0, the written key, the un-armed citation default, recall k 60, a proven no-op: its prepared output digest is the sealed comparator's d57ee9d6...) re-flown in the same chain. Its expected effect is zero by construction.",
        },
        ids["smoke"]["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "primary_metric": "intent accuracy (scenario_action exact)", "rows": 4,
            "note": "Four rows prove FORM and nothing else. Scored by no one, read by no one; under the instrument's rule 5 a batch of four rows can never be evidence of benefit.",
        },
    }
    where_to_fill = [
        {"file": package + "/registered-facts-v1.json", "json_path": f"stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp", "currently": PLACEHOLDER},
        {"file": prereg, "location": f"the fenced json block under '## The measurement declaration', key stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp", "currently": PLACEHOLDER},
    ]
    cost_estimate = {
        "caps_per_generation_cell": {"generation_calls": caps["generation_calls_cap"], "gpu_hours_fit_inclusive": caps["gpu_hours_fit_inclusive"]},
        "caps_total_gpu_hours": caps["gpu_hours_fit_inclusive"] * 2 + smoke_caps["gpu_hours_fit_inclusive"],
        "expected_from_sealed_flights": "the sealed DEV plan arm realised 4,071 contacts (4.07 per row) and 1.655 GPU hours on this roster (" + B6_READ + "); the citation contract adds about +134 instruction and +26..+353 output tokens per Solver contact and no contacts, and cell AGREE's k 60 recall is output-neutral in contacts; ESTIMATE about 1.7 to 2.0 GPU hours per 1,000-row cell, about 3.5 to 4.0 GPU hours for the A/A + arm chain plus a negligible smoke -- never a target",
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": "Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block scripts/checks/stage3_effect_floor_check.py resolves. The arm's expected_effect_pp is a placeholder string BY DESIGN.",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {"161": "AGREE enters COMP-1 pending the DEV replication", "138": "the composed round is the cumulative check; no improvement = conflict diagnosis", "152": "COMP-1 = PLAN lock + agreement term + centroid key + citation contract", "133": "intent primary, official SLU-F1 the guard", "139": "no prior, no pre-committed if-then on unread results", "127": "the citation part is a no-harm base item", "77": "flights only through the batch driver"},
        "rows": 1000,
        "stage3_measurement": measurement,
        "the_expectation_the_coordinator_declares": {
            "placeholder": PLACEHOLDER, "where_to_fill": where_to_fill,
            "gate_state_until_then": "scripts/checks/stage3_effect_floor_check.py: FAIL [unparsable-declaration] on the arm (expected_effect_pp must be a number) -- INTENDED, exactly the state COMP-1 Fold A was registered in (its commits 3667e01d..d9cef3e7 carried the same one expected FAIL until 43027f59 declared 3.23 pp); the A/A and the smoke parse.",
            "what_composes_it": "the COMP-1 Fold A read (its measured intent delta against its in-chain A/A and its per-class conversions), declared by the coordinator only after that read is on the record (decision 139)",
            "bar_at_n_1000_pp": BAR_PP_N1000, "own_null_on_this_roster": OWN_NULL,
        },
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget", "solver_material")} for key in CELLS},
        "the_composition": {
            "is_comp1_fold_a": plan_bytes_proof,
            "factor_1_agreement_term": {"rank_weights": arm_p["rank_weights"], "k": arm_p["k"], "fuse_coverage": arm_p["fuse_coverage"], "tau": arm_p["tau"], "agreement_source": arm_p["agreement_source"], "this_roster_table": agreement_facts},
            "factor_2_centroid_key": {"facet_source": arm_p["facet_source"], "as_registered_by": "docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1"},
            "factor_3_citation_contract": {"policy": ids["arm"]["policy"], "solver": ids["arm"]["solver_material"], "deliver_normaliser": ids["arm"]["deliver_normaliser"]},
        },
        "composed_config_diffs": {**diffs, "note": "arm_vs_dev_plan: the three factor groups + k 8 -> 60 + bookkeeping + the fragment's own block; aa_vs_dev_plan: k alone + bookkeeping; arm_vs_aa: the three factor groups ALONE; smoke_vs_arm: population, budgets and FIT bookkeeping only. anything_else is empty in every entry or the writer refuses."},
        "prepared_supplies": supplies,
        "default_byte_identity": {"sealed_comparator_output_sha256": DEV_PLAN_SUPPLY_OUTPUT_SHA, "aa_output_sha256": supplies["aa"]["output_sha256"], "verified": True,
                                  "note": "the sealed DEV plan preparation seeds 999 of 1,000 rows (7,970 ids): one row admits no written-key boundary entry at the tau 0.0 cosine floor; the A/A reproduces that exactly"},
        "delivery_change_arm_vs_aa_gold_free": change,
        "knowledge_exclusion": exclusion,
        "fit": {"rule": "the pre-flight prompt budget binds to the LIVE slot (24,576 tokens on the SLURP np4 session) with a one-eighth reserve; the Solver phase proceeds under compact-or-abstain", "measured": fit},
        "budget_arithmetic": {
            "family_budget": caps, "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,000 rows x 11 contacts per row (1 + 2 x (3 + 1 + 1)) = 11,000, the sealed DEV plan arm's own; the citation contract adds tokens per Solver contact, never contacts",
                "fit_endpoint_calls_cap 44,000 = 4 x 11,000; native_task_contract_calls_cap 6,000; repeated_speech_audio_seconds_cap 32,819; gpu_hours_fit_inclusive 12.0 per generation cell (the DEV plan arm's caps, unchanged)",
                "the smoke: 44 / 176 / 24 / ceil(8.1276875 s x 11) = 90 s / 1.0 GPU hour, no score",
                "one official complete score per generation cell (" + SCORER + ") over the complete 1,000-row manifest through core.scoring_batch, never sharded",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
            "cost_estimate": cost_estimate,
        },
        "reported_beside": {"note": "CONTEXT ONLY. None of these is this cell's bar.", "dev_plan": {"run_id": COMPARATOR_RUN, **COMPARATOR_OFFICIAL, "source": B6_READ}, "own_null": OWN_NULL},
        "open_items_for_the_coordinator": [
            "expected_effect_pp: the placeholder, declared from the COMP-1 Fold A read (decision 139).",
            "Per-class attribution membership (decision 138) is NOT fixed here: the Fold A classes are defined by CONV's and KPROBE's Fold A rosters and the Fold A bad-case bank, none of which exists on DEV-2000-ADDED; fixing a DEV membership needs scoring-side gold over the sealed DEV plan arm plus single-factor supplies, and must land model-free BEFORE contact if the read is to carry it. Only the gold-free delivery change (delivery_change_arm_vs_aa_gold_free) is registered.",
            "The agreement table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1 was built model-free in this registration (its DRAFT model-free ledger row is part of this package).",
        ],
        "authority_relpaths": [OWNER_DECISIONS, RECLASSIFICATION, FOLD_A_PACKAGE + "/README.md", ROLL3_PACKAGE + "/README.md", B6_PACKAGE, INSTRUMENT, ROSTER_RECEIPT],
        "prohibitions": [
            "No flight before the coordinator declares expected_effect_pp in both places, root countersigns the rows, mints the decision receipt and all three cells are flipped.",
            "No re-flying of the sealed DEV plan arm; no test-split, DEV-1000 or Fold B contact or read.",
            "No fourth factor; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change beyond the registered roster move.",
            "The citation part may never be reported as a gain (decision 127).",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read against the IN-CHAIN A/A, never against the sealed DEV plan arm alone (instrument rules 3 and 4). PRIMARY: "
        "intent accuracy (scenario_action exact), paired, utterance-clustered (913 utterances), 10,000 bootstrap draws. "
        "GUARD: official pooled SLU-F1 (" + SCORER + ") non-inferior at the plan's own null on this roster (h_SLU 1.2525). "
        "REPLICATED: the intent CI95 lower bound above zero AND the guard holds AND the declared expected_effect_pp was on "
        "the record before the seal. NEUTRAL: both metrics inside the own null (h_intent 1.1520 / h_SLU 1.2525) without a "
        "replicated gain -- read under decision 138 as a conflict diagnosis, never 'no gain'. HARMFUL: a measured loss on "
        "either metric (decision 25). The citation part is never reported as a gain."
    )
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-comp1-dev2000-added-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_EXPECTATION_AND_READINESS_FLIP",
        "the_question": "Does cell COMP-1's composition (the agreement term, the centroid boundary key and the citation contract on the locked plan) raise intent-recognition accuracy on the fresh evaluation roster DEV-2000-ADDED 1,000, read at its in-chain A/A, with official SLU-F1 non-inferior?",
        "the_composition": THE_COMPOSITION_SHORT,
        "unchanged": "the roster re-point of the sealed DEV plan arm, the geometry (np4 x 24,576), the session " + SESSION + ", the 11-contact ceiling, all stores' pins, the exemplar k of 20, the role graph, the Perception / Reviewer / Planner templates, the DEV scorer and every budget",
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "declares_agreement_source", "boundary_facet_source_sha256", "policy")} for key in CELLS},
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
                       "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "why": "rule 4: a cross-flight contrast with no in-chain replicate is refused outright"},
                       "margins": OWN_NULL},
        "decision_rule_fixed_here": decision_rule,
        "expectation": facts["the_expectation_the_coordinator_declares"],
        "knowledge_exclusion": exclusion,
        "development_numbers_only": "Every number this cell produces is a DEV-2000-ADDED development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": f"owner decisions 161, 138, 152 ({OWNER_DECISIONS}); {RECLASSIFICATION}; the COMP-1 Fold A registration {FOLD_A_PACKAGE}; the roster moves of {B6_PACKAGE} and {ROLL3_PACKAGE}; the instrument {INSTRUMENT}",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            plan = {
                "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind,
                "cell": identity["cell"], "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": protocol["status"], "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit, "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition", "carrier_lock_key": "slurp",
                    "run_id": identity["fit_run_id"] if is_fit else identity["run_id"],
                    "attempt_id": identity["fit_attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": "bounded-discovery-probe", "split_role": "dev",
                    "split_identity_hash": identity["split_identity_hash"], "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                    if is_fit else (
                        f"Shared core.flight.cli campaign over the committed campaign plan {CAMPAIGN_PLAN} (the A/A, then the arm, in ONE chain) through scripts/flights/batch/batch_driver.sh (scripts/flights/comp1dev/batch_chain_comp1dev.sh); one official score per generation cell at finalize."
                        if key != "smoke" else "Shared core.flight.cli worker on this cell alone, flown by the batch driver before the campaign; never scored."
                    )
                ),
                "prepared_phase_supply": {"relpath": identity["own_supply_requirement"]["relpath"], "sha256": identity["own_supply_requirement"]["sha256"], "output_sha256": supplies[key]["output_sha256"],
                                          "note": "THIS CELL'S OWN artifact, built model-free under its own run id by core.flight.cli prepare-supply (item E16). --allow-output-change must never be passed."},
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "the_composition": THE_COMPOSITION_SHORT,
                "purpose": f"{identity['run_id']}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule if key == "arm" else "It supplies the within-chain null and makes no claim of its own." if key == "aa" else "Structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the exact ordered outputs and the single successful complete official " + SCORER + " score exist for BOTH the arm and its in-chain A/A, before the coordinator's declared expected_effect_pp is on the record, and before the READ row " + READ_RUN + " is root countersigned (read_paired_cell.sh refuses otherwise).",
            }
            if key == "aa" and not is_fit:
                plan["byte_identity_obligation"] = {"sealed_comparator_output_sha256": DEV_PLAN_SUPPLY_OUTPUT_SHA, "this_cell_output_sha256": supplies["aa"]["output_sha256"], "verified": True}
            prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-comp1-dev2000-added-paired-analysis-v1",
        "title": "Cell COMP-1 on DEV-2000-ADDED -- the composed replication against its in-chain A/A",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_RUN,
        "read_driver": {"command": f"bash {READ_DRIVER} {package}", "passes": ["vs-aa (gating)", "vs-comparator (context only)"],
                        "scorer": SCORER, "scorer_note": "read_paired_cell.sh -> scripts/analysis/stage3_paired_read.py --package selects the scorer from the sealed arm manifest's roster receipt: split_role 'dev' (" + ROSTER_RECEIPT + ") selects slurp-slu-official, the DEV sibling ROLL-3 and B6 were read with; the -train sibling is never used on this roster",
                        "cluster_key": "utterance_id (resampling.unit names no row)", "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned"},
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "attempt_id": ids["aa"]["attempt_id"], "fit_run_id": ids["aa"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL", "role": "the within-chain null the delta is read at"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the sealed DEV plan arm, context beside the A/A, never the bar"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "utterance cluster (paired)"},
        "steps": [
            "1. Refuse unless BOTH the arm and the A/A manifests are COMPLETE at 1,000 rows with this registration's composed config hashes, sealed, each with one successful complete official " + SCORER + " score, unless the declared expected_effect_pp is a number on the record, and unless the READ row is root countersigned.",
            "2. THE DELIVERY CHECK (gold-free): the flown first-phase boundary selections must equal each cell's own prepared supply (the A/A's must reproduce output digest " + DEV_PLAN_SUPPLY_OUTPUT_SHA + "; the arm's " + supplies["arm"]["output_sha256"] + "). A mismatch is an engineering defect and closes the read.",
            f"3. Run bash {READ_DRIVER} {package}: pass vs-aa (GATING) and pass vs-comparator (context), each with the per-scenario tables in both weightings, delivery / conversion counts and the frontier row, under $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/. Primary intent accuracy; guard official pooled SLU-F1; paired by utterance cluster, 10,000 draws, seed 20260927.",
            "4. Apply the decision rule fixed in the protocol at the own null h_intent 1.1520 / h_SLU 1.2525 against the declared expected_effect_pp; state the COMP-1 Fold A read beside it (AGREE's KEEP-PROVISIONAL is settled here, decision 161).",
            "5. The citation credit table over the arm's sealed Solver states (analysis/citation_credit.py, saea-citation-credit-table-v1) and the per-contact token delta against the A/A.",
            "6. The realized spend against the caps; every number is a DEV-2000-ADDED development number, never a test claim; never write 'no gain'.",
        ],
        "output": {"analysis_root": ANALYSIS_ROOT},
        "boundary": "A development read on the DEV-2000-ADDED evaluation roster (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["arm"]["run_id"], ids["arm"]["fit_run_id"], ids["aa"]["run_id"], ids["aa"]["fit_run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT written by the registration agent for root to mint on the data root with scripts/flights/comp1dev/comp1dev_mint_receipt.py (status 'decided', recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided', and root mints it ONLY after the coordinator has declared expected_effect_pp in both places.",
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED", "recorded_at_utc": None,
        "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm replicated on DEV-2000-ADDED (label sealed-credit-system-policy-v1, operator context_application) with its four-row smoke and its in-chain A/A: three cells, six run ids, one chain for the A/A and the arm.",
        "decision": "Fly cell COMP-1 on DEV-2000-ADDED 1,000 beside its in-chain A/A in one campaign chain after its four-row smoke; read at intent primary with official SLU-F1 (" + SCORER + ") the guard against the coordinator's declared expected_effect_pp.",
        "authorization_basis": f"Owner decision 161 (AGREE enters COMP-1 pending the DEV replication) with 138 and 152; {RECLASSIFICATION}; standing 133, 139, 127, 101, 77; the instrument note {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "reclassification": {"path": RECLASSIFICATION, "sha256": sha_file(RECLASSIFICATION)},
            "preregistration": {"path": prereg, "sha256": None}, "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "fold_a_registration": {"path": FOLD_A_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(FOLD_A_PACKAGE + "/registered-facts-v1.json")},
            "roster_receipt": {"path": ROSTER_RECEIPT, "sha256": sha_file(ROSTER_RECEIPT)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "base_cell": f"the sealed DEV-2000-ADDED plan arm ({COMPARATOR_RUN})",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. The citation part is never reported as a gain. Development numbers only.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight before expected_effect_pp is declared, the rows are countersigned, the receipt is minted and all three cells are flipped", "any ASR, transcript, encoder or paid-API contact", "re-flying or re-scoring any sealed cell", "--allow-output-change on the re-pin tool", "any fourth factor or any k, tau, fuse-policy, w_prior, store, release, snapshot, roster or geometry change"],
        "population": {"count": 1000, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "dev", "partition": "DEV-2000-ADDED 1,000, unchanged; the smoke flies its first four rows", "test_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    ex = exclusion
    readme = f"""# Cell COMP-1 on DEV-2000-ADDED: the composed arm's fresh-roster replication

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decision 161, with 138 and
152); all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**Why.** Owner decision 161 admits AGREE into COMP-1 pending the DEV replication, and
`{RECLASSIFICATION}` (row D3, KEEP-PROVISIONAL) says the COMP-1 DEV-2000-ADDED round settles it.

**THE EXPECTATION IS NOT DECLARED, ON PURPOSE.** `stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp` is the
literal string `{PLACEHOLDER}` in both places the gate reads (`registered-facts-v1.json`, canonical, and the fence of
`../{Path(prereg).name}`). Owner decision 139 forbids an if-then on unread results and the COMP-1 Fold A arm has not
flown. Until the coordinator replaces the string in both places, `scripts/checks/stage3_effect_floor_check.py` refuses
the arm as `unparsable-declaration`; that is the intended state, exactly the state COMP-1 Fold A was registered in.

**What it is.** Cell COMP-1's plan bytes (`{FOLD_A_PACKAGE}`) with only the roster moved, exactly as the sealed
DEV-2000-ADDED plan arm `{COMPARATOR_RUN}` (cell B6) moved the locked plan: {THE_COMPOSITION_SHORT}. Proven in
`registered-facts-v1.json` (`the_composition.is_comp1_fold_a`): every composed-config path on which this arm differs
from the COMP-1 Fold A arm is a path on which the DEV plan arm differs from the locked Fold A plan, this roster's own
agreement-table pin, bookkeeping, or the fragment's own block; `composed_config_diffs` proves arm vs A/A = the three
factor groups alone and A/A vs DEV plan = `k` 8 -> 60 alone.

**One roster-bound artifact is new.** The agreement table is a function of the roster's own sealed speech vectors, so
the Fold A table cannot be reused: `{AGREEMENT_ROW}` was built model-free in this registration by
`{AGREEMENT_BUILDER}` against the sealed DEV plan cell (same builder, vote store, vote phase and target store as the
Fold A table): 1,000 rows, 20 votes each, 0 self-excluded exemplars, 0 rows with no vote, 59 facets ever voted for;
artifact sha256 `{agreement_facts['sha256']}`, receipt `{agreement_facts['receipt_sha256']}`. Its DRAFT model-free
ledger row is part of this package.

**Reused exactly as ROLL-3 / CELL-3 / B6 reuse them.** Roster `{ROSTER_RECEIPT}` (`{ROSTER_ID}`), split identity
`{ids['arm']['split_identity_hash']}`, split role `dev`; the DEV-2000-ADDED speech query vectors, alias and promoted packets
(`DEV-2000-ADDED-promotion.json`) as the sealed DEV plan arm pins them; scorer `{SCORER}` (the DEV sibling, never
`-train`); the smoke's four rows and split identity `{ids['smoke']['split_identity_hash']}` are cell ROLL-3's smoke's.

**Knowledge exclusion (no knowledge read here was built from a DEV-2000-ADDED row).** Proof file: the roster receipt
`{ROSTER_RECEIPT}` `disjointness_proof` (`shared_with_train_construction_recordings` 0, `non_devel_ids_added` 0,
`shared_with_test_recordings` 0). The train-exemplars store is the TRAIN-built parent pool every DEV package read; the
agreement table's vote pool is that store and its self-exclusion MEASURED 0 excluded exemplars on all 1,000 rows
(`{AGREEMENT_RECEIPT}`); the centroid keys come from the R01-excluded construction-TRAIN pool (8,554 TRAIN utterances,
`{CENTROID_RECEIPT}`), a subset of the same pool. Stores and releases are the DEV plan arm's, unchanged.

**Three cells, one chain.** `{CAMPAIGN_PLAN}` carries the A/A **and** the arm (instrument rule 4); the four-row smoke is
outside the plan and never scored. The A/A's own prepared supply **reproduces the sealed DEV comparator's output
digest `{DEV_PLAN_SUPPLY_OUTPUT_SHA}`** ({supplies['aa']['rows_seeded']} rows seeded, {supplies['aa']['selected_value_ids']} ids -- one row admits no
written-key entry at tau 0.0, as in the sealed arm). The arm's supply: output `{supplies['arm']['output_sha256']}`
({supplies['arm']['rows_seeded']} rows, {supplies['arm']['selected_value_ids']} ids); the smoke's `{supplies['smoke']['output_sha256']}`. Gold-free delivery change: the
arm's boundary selection differs from the A/A's on {change['rows_with_a_changed_selected_set']} of {change['rows']} rows.

**Measurement.** `cross-flight-with-in-chain-replicate`, roster DEV-2000-ADDED, n = 1,000, own null h_intent 1.1520 /
h_SLU 1.2525 (`{INSTRUMENT}` section 2d, the B6 pair), intent primary, official SLU-F1 the guard, bar about
{BAR_PP_N1000} pp at n = 1,000 ({RECLASSIFICATION}).

**Budgets and cost.** Per generation cell {caps['generation_calls_cap']} contacts (1,000 x 11), {caps['fit_endpoint_calls_cap']} FIT endpoints,
{caps['native_task_contract_calls_cap']} native task-contract calls, {caps['repeated_speech_audio_seconds_cap']} s repeated speech, {caps['gpu_hours_fit_inclusive']} GPU hours (fit-inclusive cap), one
official score; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s / {smoke_caps['gpu_hours_fit_inclusive']} GPU hour. Caps total
{cost_estimate['caps_total_gpu_hours']} GPU hours; ESTIMATE about 3.5-4.0 GPU hours for the chain (the sealed DEV plan arm realised
1.655 GPU hours at 4.07 contacts per row).

| file | what it holds |
| --- | --- |
| `../{Path(prereg).name}` | the preregistration, with the `stage3_measurement` fence (placeholder) |
| `registered-facts-v1.json` | every model-free fact, the proofs, the CANONICAL `stage3_measurement`, open items |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the read (`{READ_DRIVER}`, READ run `{READ_RUN}`, analysis root `{ANALYSIS_ROOT}`) |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/comp1dev/comp1dev_mint_receipt.py` |

**Declare, mint, flip, queue.** (1) The coordinator declares `expected_effect_pp` from the COMP-1 Fold A read in both
places and commits. (2) Root countersigns the eight DRAFT exposure rows and mints `{DECISION_RELPATH}` (decision id
`{DECISION_ID}`, six eligible run ids) with `scripts/flights/comp1dev/comp1dev_mint_receipt.py`. (3)
`scripts/flights/comp1dev/comp1dev_flip.sh` re-pins smoke, A/A and arm until the package converges at one HEAD (it
refuses while the placeholder stands; the A/A's re-minted supply must again be `d57ee9d6...`). (4)
`scripts/flights/comp1dev/batch_chain_comp1dev.sh` queues the smoke, then the A/A + arm campaign, on the np4 session
(decision 77). (5) After both seals, the READ row is countersigned and `bash {READ_DRIVER} {package}` reads it.

**Not authorised.** No flight before steps 1-3; no re-flying of the DEV plan arm; no test, DEV-1000 or Fold B contact;
no fourth factor; the citation part is never reported as a gain.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Cell COMP-1 on DEV-2000-ADDED: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the sealed DEV-2000-ADDED
plan arm fragments by script (decision 58) with cell COMP-1's three composed factors, under owner decision 161 (with 138
and 152). Development numbers only (owner decisions 28 and 86); never a test claim.

**The declared expectation is a placeholder until the coordinator fills it** from the COMP-1 Fold A read (decision 139:
no if-then on unread results). The two places: `{package}/registered-facts-v1.json`
(`stage3_measurement.{ids['arm']['run_id']}.expected_effect_pp`) and the fence below.

## The cell

| item | value |
| --- | --- |
| base | the sealed DEV-2000-ADDED plan arm `{COMPARATOR_RUN}` ({COMPARATOR_OFFICIAL['slu_f1']} / {COMPARATOR_OFFICIAL['intent_accuracy']}, {B6_READ}) |
| composition | {THE_COMPOSITION_SHORT} |
| roster | `{ROSTER_RECEIPT}`, split identity `{ids['arm']['split_identity_hash']}`, split role dev, 1,000 rows / 913 utterances |
| in-chain replicate | `{ids['aa']['run_id']}`: the DEV plan arm's own bytes at recall k 60 in the SAME chain; prepared output digest `{DEV_PLAN_SUPPLY_OUTPUT_SHA}` verified |
| margins | the plan's own null on this roster: h_intent 1.1520, h_SLU 1.2525 ({INSTRUMENT} section 2d) |
| scorer | `{SCORER}` (DEV sibling) |
| smoke | the roster's first four rows (ROLL-3's smoke rows), split identity `{ids['smoke']['split_identity_hash']}`, never scored |
| runs | `{ids['arm']['run_id']}` / `{ids['arm']['fit_run_id']}`; `{ids['aa']['run_id']}` / `{ids['aa']['fit_run_id']}`; `{ids['smoke']['run_id']}` / `{ids['smoke']['fit_run_id']}` |
| composed config hashes | arm `{ids['arm']['composed_config_hash']}`; A/A `{ids['aa']['composed_config_hash']}`; smoke `{ids['smoke']['composed_config_hash']}` |
| protocol hashes | arm `{ids['arm']['protocol_hash']}`; A/A `{ids['aa']['protocol_hash']}`; smoke `{ids['smoke']['protocol_hash']}` |
| read | `{READ_RUN}` via `{READ_DRIVER}`, analysis root `{ANALYSIS_ROOT}` |

## Knowledge exclusion

{ex['train_exemplars_store']}. Agreement table: {ex['agreement_table']}. Centroid keys: {ex['centroid_keys']}.

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Budgets and failure rule

Per generation cell: {caps['generation_calls_cap']} generation calls (run-cumulative), {caps['fit_endpoint_calls_cap']} FIT endpoints,
{caps['repeated_speech_audio_seconds_cap']} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score. The smoke:
{smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} s, no score. {protocol['failure_policy']}

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, supplies=supplies, plan_shas=plan_shas, package=package, agreement=agreement_facts)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "exposure_ledger": ledger_state,
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "prepared_supplies": {key: {k: supplies[key][k] for k in ("output_sha256", "file_sha256", "rows_seeded", "selected_value_ids")} for key in CELLS},
        "composed_config_diffs": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in diffs.items()},
        "plan_bytes_unexplained": unexplained, "delivery_change_rows": change["rows_with_a_changed_selected_set"],
        "fit": fit["status"],
    }, indent=2, sort_keys=True))
    return 0


def append_ledger(args, *, ids, supplies, plan_shas, package, agreement) -> str:
    """Eight DRAFT rows: six unconsumed flight/FIT rows, the model-free agreement-table build row
    and the READ row. Idempotent: replaces its own rows in place, refuses a partial set."""

    text = rd(LEDGER)
    stamp = args.registered_at
    draft_tag = "DRAFT, root countersignature pending"
    prose = {
        "arm": "Cell COMP-1 on DEV-2000-ADDED, the fresh-roster replication of the first composed Stage-3 arm (owner decision 161): the sealed DEV plan arm's bytes + the agreement term (as AGREE: w_agree 1.0, k 60, 8-1-8; this roster's own vote table) + the centroid boundary key (as KPROBE) + the citation contract, nothing else",
        "aa": "The in-chain A/A replicate of cell COMP-1 on DEV-2000-ADDED: the sealed DEV plan arm's own bytes at recall k 60, re-flown in the same chain; its prepared supply reproduces the sealed comparator's output digest exactly",
        "smoke": "Four-row form smoke of cell COMP-1 on DEV-2000-ADDED: the same three composed actions on the roster's first four rows",
    }
    rows: list[tuple[str, str]] = []
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        budget = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit_run_id"] if is_fit else identity["run_id"]
            attempt = identity["fit_attempt_id"] if is_fit else identity["attempt_id"]
            prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
            artifact = f"{package}/{prefix}{kind}-plan-registered-v1.json"
            notes = (
                f"REGISTERED BEFORE CONTACT ({draft_tag}; the arm's expected_effect_pp is the placeholder {PLACEHOLDER} until the "
                f"coordinator declares it from the COMP-1 Fold A read, decision 139) {stamp[:10]} at study commit {args.study_commit} by the "
                f"COMP-1 DEV registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and "
                f"authorises none. Plan SHA256 {plan_shas[f'{key}:{kind}']}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; "
                f"composed config {identity['composed_config_hash']}; expected session {SESSION} (attach only). READINESS HELD: root mints "
                f"{DECISION_RELPATH} (decision id {DECISION_ID}) from the package's root-admission-draft-v1.json with the six eligible run ids, "
                f"then scripts/flights/comp1dev/comp1dev_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each cell's "
                f"OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
                f"THE COMPOSITION: {THE_COMPOSITION_SHORT}; proven in {package}/registered-facts-v1.json. Prepared supplies minted model-free: "
                f"arm output {supplies['arm']['output_sha256']}, A/A output {supplies['aa']['output_sha256']} (the sealed DEV comparator's own, "
                f"verified), smoke output {supplies['smoke']['output_sha256']}. Measurement declaration: measurement_design "
                f"{'form-proof' if key == 'smoke' else 'cross-flight-with-in-chain-replicate'}, expected_effect_pp {PLACEHOLDER if key == 'arm' else '0.0'}, "
                f"claims_benefit {'true' if key == 'arm' else 'false'}, rows {identity['rows']}, replicate_run_id "
                f"{ids['aa']['run_id'] if key == 'arm' else ids['arm']['run_id'] if key == 'aa' else 'n/a (form proof)'}, own null h_intent 1.1520 / "
                f"h_SLU 1.2525, intent primary with official SLU-F1 ({SCORER}) the guard; the gate refuses the arm as unparsable-declaration until the "
                f"number is declared, which is intended. Read: {READ_RUN} by {READ_DRIVER}. Ceiling {budget['generation_calls_cap']} = {identity['rows']} rows x 11. "
                f"Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No paper-scale profile, no test-split "
                f"contact, no comparator re-flight and no admission entry from this row."
            )
            scope = prose[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "")
            cells = ["", stamp, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp DEV-2000-ADDED {identity['rows']}", "dev",
                     identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                     str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED, artifact, notes, ""]
            rows.append((run_id, " | ".join(cells).strip()))

    rows.append((AGREEMENT_ROW, " | ".join([
        "", stamp[:10], AGREEMENT_ROW, "model-free-check",
        "Build the pre-computed, self-excluded exemplar-intent AGREEMENT table cell COMP-1 DEV-2000-ADDED's boundary channel ranks with: arithmetic over the pinned exemplar snapshot, the pinned pool key vectors and the pinned DEV-2000-ADDED speech query vectors, through the repository's own recall/rank/fuse, against the sealed DEV plan cell (the comparator, which declares no agreement_source). Zero model, server, encoder, embedder, scorer, network, GPU and paid-API contacts.",
        "no model or tool contact; local arithmetic over receipt-pinned files", "slurp DEV-2000-ADDED 1000", "dev", ids["arm"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: every byte read was already exposed by the cells that sealed it. Prior exposure inherited in full.",
        AGREEMENT_RECEIPT,
        (f"REGISTERED BEFORE RESULT READING ({draft_tag}) {stamp[:10]} at study commit {args.study_commit}. Artifact {agreement['relpath']} SHA256 "
         f"{agreement['sha256']}; receipt SHA256 {agreement['receipt_sha256']}. Builder {AGREEMENT_BUILDER} (sha256 {agreement['builder_sha256']}), "
         f"4 workers, the same vote store, vote phase and target store as SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1. Measured: 1,000 rows, 20 votes "
         f"each, {agreement['measured']['self_excluded_exemplars']} self-excluded exemplars, {agreement['measured']['rows_with_no_vote']} rows with no vote, "
         f"{agreement['measured']['pool_values_without_a_build_time_target']} pool values without a build-time target, "
         f"{agreement['measured']['distinct_facets_ever_voted_for']} boundary facets ever voted for. It constructs no ExecutionPlan, reserves no contact and "
         f"authorises nothing."),
        "",
    ]).strip()))

    rows.append((READ_RUN, " | ".join([
        "", stamp, READ_RUN, "model-free-check",
        "The cell COMP-1 DEV-2000-ADDED read: the composed arm against its in-chain A/A (gating; intent primary, official SLU-F1 the guard, at the own null h_intent 1.1520 / h_SLU 1.2525 against the declared expected_effect_pp), per-scenario tables in both weightings, delivery and conversion, the frontier row and the citation credit table; the sealed DEV plan arm as context only.",
        f"No model, tokenizer, encoder or server contact: {READ_DRIVER} over the sealed per-sample official {SCORER} scores and sealed receipts.",
        "slurp DEV-2000-ADDED 1000", "dev", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
        "Reads only sealed manifests of this package and its registered comparator; no new audio, gold or reference exposure.",
        package + "/analysis-recipe-v1.json",
        (f"REGISTERED BEFORE CONTACT ({draft_tag}) {stamp[:10]} with the package, so the pre-launch gate scripts/checks/flight_registration_check.py finds it. "
         f"Analysis root $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/; recipe {package}/analysis-recipe-v1.json (recipe_id slurp-stage3-comp1-dev2000-added-paired-analysis-v1); "
         f"driver {READ_DRIVER} refuses before any score is opened until root countersigns this row (after both seals). No utterance text, gold, transcript or "
         f"model output is printed or persisted."),
        "",
    ]).strip()))

    for run_id, line in rows:
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")
        if "root countersigned" in line.lower():
            raise SystemExit(f"ledger row {run_id} would read as countersigned")

    header = (
        "\n## Cell COMP-1 on DEV-2000-ADDED: the composed arm's fresh-roster replication, with its in-chain A/A, its four-row smoke, "
        "this roster's agreement table and the READ row (DRAFT, root countersignature pending)\n\n"
        f"Six unconsumed flight rows (the arm, the in-chain A/A, the four-row smoke and their three FIT spend identities), one model-free row for "
        f"this roster's agreement table and the READ row. Owner decision 161; package {package}. The arm's expected_effect_pp is a placeholder until "
        "the coordinator declares it from the COMP-1 Fold A read (decision 139). None of these rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | "
        "calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    fresh = dict(rows)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all COMP-1 DEV rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(line for _run, line in rows) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
