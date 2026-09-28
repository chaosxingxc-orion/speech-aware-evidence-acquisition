#!/usr/bin/env python3
"""Write cell W5's readiness package (knowledge-wave item W5, slot-side retrieval; owner
decision 170) from the derived fragments, the model-free build receipt and the offline Fold A
estimate -- config and receipt-pinned bytes only: no adapter contact, no server, no lock, no
model, tokenizer, encoder, embedder or scorer contact. It flips nothing and mints nothing.

Package ``docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1/`` and the preregistration beside
it. ``--append-ledger`` writes the DRAFT exposure rows (four flight rows, the READ row, and the two
model-free rows for the build and the estimate), replacing in place on re-run. ``--check-dir``
folds the per-phase prompt-budget receipts of an already-run ``core.flight.cli check`` (it
attaches to nothing) into the facts.

    python scripts/flights/w5/write_slurp_w5_registration.py --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-27T20:00:00.000000+00:00 \\
        [--check-dir /home/chao/saea-worktrees/.w5-checks] [--append-ledger]
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

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
CELLS = {"arm": "slurp-native-stage3-w5-fold-a-v1", "smoke": "slurp-native-stage3-w5-fold-a-smoke-4-v1"}
PARENTS = {"arm": "slurp-native-stage3-agree-w1-fold-a-v1", "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1"}
PREFIX = {"arm": "", "smoke": "smoke-"}
COMPARATOR_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 65.1575, "intent_accuracy": 85.8333}
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
READ_RUN = "SAEA-SLURP-STAGE3-W5-FOLD-A-PAIRED-READ-V1"
BUILD_ROW = "SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
ESTIMATE_ROW = "SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-stage3-w5-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-w5-fold-a-v1/root-admission-v1.json"
AGREE_SUPPLY_OUTPUT = {"arm": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
                       "smoke": "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9"}
H_SLU, H_INTENT = 1.2485, 0.9943
BENEFIT_FLOOR = 2.5
THE_STORE = "knowledge_stores.slot-exemplars"
ALLOWED_PREFIXES = ("preparation_source_receipts", "native_contact_fit.", "prepared_phase_supply", "what_this_is")
LIVE_SLOT, RESERVE, COMPLETION = 24576, 3072, 512

PREP = "prepared/SAEA-SLURP-W5-SLOT-EXEMPLAR-SCOPE-FOLD-A-V1"
ESTIMATE = "analysis/SAEA-SLURP-W5-FOLD-A-OFFLINE-ESTIMATE-V1/estimate-v1.json"
BUILD_SCRIPT = "scripts/build_slurp_slot_exemplar_scope_w5.py"
ESTIMATE_SCRIPT = "scripts/analysis/slurp_w5_fold_a_offline_estimate.py"
DERIVE_SCRIPT = "scripts/flights/w5/derive_slurp_w5_cells.py"
CONFIG_TEST = "tests/unit/test_w5_config.py"
AUDIT = "docs/results/2026-09-27-slurp-knowledge-content-audit.md"
ERRSRC = "docs/results/2026-09-27-slurp-agree-arm-error-sources.md"
SYNTHESIS = "docs/results/2026-09-27-slurp-mechanism-synthesis.md"
M1C = "docs/results/2026-09-19-slurp-m1-exemplar-compression-analysis-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
VIEWS_V4 = "docs/readiness/2026-09-26-task-specific-knowledge-stores-and-views-v4.md"
GATE = "scripts/checks/stage3_effect_floor_check.py"
READ_DRIVER = "scripts/analysis/stage3_paired_read.py or scripts/analysis/plan_cell_read.py (the wave read wrapper of branch fable/waveaa)"


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


def sha_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"],
                         parent_cell["baseline_fragment"], PARENTS[key])
        baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
        experiment_keys = set(document) | set(parent_doc)
        if experiment_keys & baseline_keys:
            raise SystemExit("an experiment fragment overrides a baseline key")
        a, b = flatten(parent.values), flatten(composed.values)
        changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
        store = [k for k in changed if k.startswith(THE_STORE + ".")]
        bookkeeping = [k for k in changed if k.startswith(ALLOWED_PREFIXES) and k not in store]
        block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in store and k not in bookkeeping]
        other = [k for k in changed if k not in store and k not in bookkeeping and k not in block]
        if other:
            raise SystemExit(f"{key}: composed config differs from its AGREE parent beyond the added store and bookkeeping: {other}")
        if not store or any(k in a for k in store):
            raise SystemExit(f"{key}: the added store is not purely an addition: {store}")
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"],
            "added_store": composed.values["knowledge_stores"]["slot-exemplars"],
            "composed_config_diff_against_the_agree_cell": {"the_added_store": store, "bookkeeping": bookkeeping,
                                                            "experiment_fragment_own_block": block, "anything_else": other},
        }
    return out


def fold_check(check_dir: str | None) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    out = {"status": "MEASURED_BY_CHECK", "cells": {}}
    for key, cell_id in CELLS.items():
        path = Path(check_dir) / f"check-{cell_id}.json"
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            out["cells"][key] = {"status": "MISSING", "path": str(path)}
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        preflight = report.get("preflight") or {}
        phases = []
        for receipt in preflight.get("prompt_budget") or ():
            entry = {"phase": receipt.get("phase"), "decision": receipt.get("decision")}
            breakdown = receipt.get("breakdown") if isinstance(receipt.get("breakdown"), dict) else {}
            for name in ("physical_margin_tokens", "operational_margin_tokens", "rendered_text_tokens",
                         "required_window_tokens", "completion_token_ceiling", "speech_feature_tokens"):
                if name in receipt:
                    entry[name] = receipt[name]
                elif name in breakdown:
                    entry[name] = breakdown[name]
            phases.append(entry)
        out["cells"][key] = {"check_path": str(path), "blockers": report.get("blockers"),
                             "scientific_readiness": report.get("scientific_readiness"),
                             "config_hash": preflight.get("config_hash"), "protocol_hash": preflight.get("protocol_hash"),
                             "prompt_budget_per_phase": phases}
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/w5")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-w5")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    data = Path(args.data_root)

    receipt = json.loads((data / PREP / "receipt.json").read_text(encoding="utf-8"))
    estimate = json.loads((data / ESTIMATE).read_text(encoding="utf-8"))
    if receipt["builder_sha256"] != sha_file(BUILD_SCRIPT):
        raise SystemExit("the build script changed after the build; rebuild into a new namespace")
    if estimate["inputs"]["build_receipt_sha256"] != sha_file(data / PREP / "receipt.json"):
        raise SystemExit("the estimate was not computed on this build")

    ids = identities()
    arm, smoke = ids["arm"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    added = arm["added_store"]
    if receipt["table_pin"]["sha256"] != added["phase_supply"]["solver"]["agreement_source"]["sha256"]:
        raise SystemExit("the configs do not pin the table this build wrote")
    store = {
        "store_id": "slot-exemplars", "store_role": added["store_role"],
        "release": added["release"], "snapshot": added["snapshot"],
        "phase_supply_solver": added["phase_supply"]["solver"],
        "scope_table": receipt["table_pin"], "scope_receipt": {"relpath": PREP + "/receipt.json", "sha256": sha_file(data / PREP / "receipt.json")},
        "selection_ids": receipt["selection"], "build_measure": receipt["measure"],
        "verification": receipt["verification"], "roster_exclusion_proof": receipt["roster_exclusion_proof"],
        "contacts": receipt["contacts"],
        "source": ("the R01-excluded TRAIN exemplar pool size-pool-annotated-exemplars-minus-r01 (8,554 utterances, content hash "
                   "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63), ALREADY RELEASED; the new release only binds it "
                   "under the store id slot-exemplars. No Fold A, Fold B, DEV or test byte, no flight output and no score was read to "
                   "build the order; the Fold A side is each row's own sealed speech vector and the deterministic AGREE boundary ranking over it."),
    }
    exp = estimate["expected"]
    newly = estimate["newly_printed_by_w5_not_m1"]
    risk = estimate["risk"]
    cost = estimate["cost"]
    fit = fold_check(args.check_dir)
    budget = LIVE_SLOT - RESERVE - COMPLETION

    primary_why = (
        "SLU-F1 is PRIMARY because W5 acts on SLOTS: it adds row-matched slot-bearing TRAIN exemplars to the node that "
        "fills slots (the M1 mechanism, whose admitted gains were slot-only: 213 of 277 B1 saves changed only slots), and owner "
        "decision 133 makes intent primary only for intent-acting mechanisms. Among the wave's cells W1 (card selection) and W3 "
        "(intent contrast) read intent primary; W4 (slot conventions) and W5 read SLU primary -- W5 is the wave's one "
        "slot-RETRIEVAL cell (row-matched content keyed by the row's own speech), W4 a card-content cell."
    )
    rule = (
        "NO-HARM ADMITTED: against the knowledge wave's SHARED in-chain A/A " + SHARED_AA_RUN + " flown in the same "
        f"chain, the paired CI95 lower bound of the official pooled SLU-F1 delta (PRIMARY -- {primary_why}) is not below "
        f"-{H_SLU} pp AND the paired CI95 lower bound of the intent-accuracy delta (the guard) is not below -{H_INTENT} pp "
        f"-- each at its own Fold A own-null half-width ({INSTRUMENT} section 2d). HARMFUL: a measured loss on either metric "
        "(CI95 upper bound below zero, decision 25). A SLU-F1 CI95 lower bound above zero is REPORTED as a development-fold "
        f"effect beside the no-harm verdict, never as an admission of benefit (the design's benefit floor is {BENEFIT_FLOOR} pp "
        "and the measured expectation sits far below it). Every verdict carries the per-scenario table in both weightings, "
        "the frontier row (decision 75), the entity item classes of the error-source read (MISSING, SPURIOUS, WRONG-TYPE, "
        "BOUNDARY, WRONG-VALUE, NEAR, FORMAT) arm vs A/A, the SPURIOUS count on empty-gold rows, and the realised "
        "prompt-token delta per Solver/Reviewer/Planner contact and per row."
    )
    note = (
        "W5 acts on SLOTS, so SLU-F1 is primary and intent the guard (owner decision 133 scopes intent-primary to intent-acting "
        "mechanisms). The expectation is declared from MEASURED numbers only (row 139). The entity taxonomy is the 2026-09-27 "
        "error-source read's (MISSING / SPURIOUS / WRONG-TYPE / BOUNDARY / WRONG-VALUE / NEAR / FORMAT, its entity_items function "
        "imported unchanged). On the sealed AGREE rows the W5 block prints the gold (type, value) of "
        f"{estimate['gold_pair_printed_by_w5'].get('MISSING', 0)} MISSING items, but the row's own M1 block already prints "
        f"{estimate['gold_pair_already_printed_by_m1'].get('MISSING', 0)} MISSING items' values and was not converted; W5 NEWLY prints "
        f"{newly.get('MISSING', 0)} MISSING and {newly.get('BOUNDARY', 0)} BOUNDARY items (of 173 / 75; of the audit's 157 in-list "
        "items at most these). At M1's measured delivered-filler conversion (133 newly correct printed fillers over 0.5719 x 941 "
        f"printed gold fillers = {estimate['conversion']['m1_delivered_filler_conversion']}, a lower bound) and the error-source "
        f"read's isolated pp per repaired item (MISSING 9.80 / 173), the expectation is {exp['expected_pp']} pp (oracle, every newly "
        f"printed item converted: {exp['oracle_pp_if_every_newly_printed_item_converted']} pp). The directly measured analogue of more "
        "speech-keyed exemplars on a system that already has M1 agrees: VAR-1 on R01C 625, exemplar budget 30 vs 20 read +0.09 "
        f"[-1.47, +1.60] SLU vs PLANR. Both sit far below the design's {BENEFIT_FLOOR} pp benefit floor at n = 1,080, so a benefit "
        f"declaration would be refused (effect-below-floor) and the cell is declared NO-HARM: expected_effect_pp 0.0, claims_benefit "
        f"false, harm_margin_pp {H_SLU} (SLU, primary) with intent {H_INTENT} as the guard. Named harm risks: every one of the "
        f"{risk['empty_gold_rows']} empty-gold rows receives nine slot-bearing exemplars (SPURIOUS is the largest error class, 253 "
        f"items), and on {risk['rows_gold_intent_outside_shortlist']} rows the gold intent is outside the shortlist that scopes the "
        f"block ({risk['intent_correct_rows_gold_outside_shortlist']} of them intent-correct on AGREE). Read against the shared in-chain "
        "A/A flown in the same chain (rule 3)."
    )
    measurement = {
        arm["run_id"]: {
            "admission": "no-harm", "claims_benefit": False, "expected_effect_pp": 0.0,
            "harm_margin_pp": H_SLU, "harm_margin_pp_by_metric": {"slu_f1": H_SLU, "intent_accuracy": H_INTENT},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "official pooled SLU-F1 (primary: a slot-acting mechanism -- slot-side retrieval of row-matched TRAIN exemplars to the Solver -- owner decision 133's scope), intent accuracy the non-inferiority guard",
            "replicate_run_id": SHARED_AA_RUN, "rows": 1080, "note": note,
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)", "rows": 4,
            "note": "Four rows prove FORM and nothing else: the slot-exemplars store loads by its pins, the scope table loads, the Solver receives the nine W5 exemplars beside the M1 twenty, every request fits and the episode completes. Scored by no one, read by no one.",
        },
    }
    token_cost = {
        "chars_per_token": cost["chars_per_token"], "chars_per_token_source": cost["chars_per_token_source"],
        "block": {"exemplars_per_row": 9, "chars_per_row": cost["block_chars_per_row"], "tokens_per_contact": cost["block_tokens_per_contact"]},
        "per_phase": cost["per_phase"], "per_row": cost["per_row"],
        "flight_total_added_tokens": cost["total_added_tokens"],
        "flight_total_prompt_tokens_realised_agree": cost["total_prompt_tokens_realised_agree"],
        "added_share_of_prompt_volume": cost["added_share_of_prompt_volume"],
        "live_slot": {"serving_slot_tokens": LIVE_SLOT, "reserve": RESERVE, "completion": COMPLETION, "operational_budget": budget},
        "compaction_projection": (
            f"the widest realised request per phase on the sealed AGREE trace plus that contact's W5 block (every Solver, Reviewer "
            f"and Planner contact carries the M1 block and would carry the W5 block the same way) stays below the live operational "
            f"budget ({LIVE_SLOT} slot - {RESERVE} reserve - {COMPLETION} completion = {budget}): Solver "
            f"{cost['per_phase']['solver']['realised_prompt_tokens_max']} -> {cost['per_phase']['solver']['projected_prompt_tokens_max']}, Reviewer "
            f"{cost['per_phase']['reviewer']['realised_prompt_tokens_max']} -> {cost['per_phase']['reviewer']['projected_prompt_tokens_max']}, Planner "
            f"{cost['per_phase']['planner']['realised_prompt_tokens_max']} -> {cost['per_phase']['planner']['projected_prompt_tokens_max']}; no realised request is projected to compact"
        ),
    }
    fit_statement = (
        "W5 is registered to fly ALONE on the AGREE form, like W4; it composes with W1 and W4 later without change (it adds a "
        "store, it edits none). The binding facts are (a) the physical margin the runtime's own pre-flight "
        "(core.flight.cli check, placeholder 4 bytes per token on the widest representative request) reports after W5 -- a "
        "COMPACT_REQUIRED preflight with a non-negative PHYSICAL margin proceeds under the armed compact-or-abstain policy "
        "(the AGREE, COMP-1 and W4 cells already read COMPACT_REQUIRED on the Solver), a negative one refuses -- and (b) the "
        "realised requests projected from the sealed AGREE trace (token_cost.compaction_projection)."
    )
    fold_a = {
        "taxonomy": estimate["taxonomy"],
        "error_items_by_kind": estimate["error_items_by_kind"],
        "gold_pair_printed_by_w5": estimate["gold_pair_printed_by_w5"],
        "gold_pair_already_printed_by_m1": estimate["gold_pair_already_printed_by_m1"],
        "newly_printed_by_w5_not_m1": newly, "newly_printed_by_type": estimate["newly_printed_by_type"],
        "rows_touched": estimate["rows_touched"], "risk": risk,
        "estimate": {"relpath": ESTIMATE, "sha256": sha_file(data / ESTIMATE), "script": {"relpath": ESTIMATE_SCRIPT, "sha256": sha_file(ESTIMATE_SCRIPT)}},
        "boundary": "gold read offline; counts only; development numbers (owner decisions 28 and 86)",
    }
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {GATE} resolves (keyed by run id).",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "170": "W5, slot-side retrieval, is the fifth cell of knowledge wave 1, read against the wave's shared in-chain A/A; one change from the AGREE arm bytes; knowledge from TRAIN rows outside Fold A only (the R01-excluded exemplar pool)",
            "164": "the knowledge wave: every W cell derives from the retained AGREE arm with ONE change, TRAIN-only construction, expectation from measured numbers, one shared in-chain A/A",
            "133": "intent is primary only for intent-acting mechanisms; a slot-acting mechanism keeps decision 115's shape (SLU primary, intent guard)",
            "139": "no prior: the expectation is declared from measured numbers only",
            "127": "the no-harm admission form and its margins at the design's measured floor",
            "125/126": "the candidate-conditioned slot view native-candidate-slot-view-v1 exists and is disabled; it projects the whole store and never retrieves -- W5 does NOT enable it (see the_item.what_w5_is_not)",
            "47": "the staged fetch of slot-filler exemplars keyed by speech plus the drafted intent -- the design W5 realises pre-flight, with the retrieval shortlist standing in for the drafted intent",
            "28/86": "TRAIN Fold A numbers are development numbers, never a test claim",
        },
        "rows": 1080, "stage3_measurement": measurement,
        "primary_metric_why": primary_why,
        "the_item": {
            "evidence": [
                f"{SYNTHESIS} section 5 rank 3 (slot-side retrieval; ENTITY-MIXED oracle +17.4 / +16.5 SLU) and section 2.7",
                f"{ERRSRC} section 3-4: MISSING 173 (9.80), SPURIOUS 253 (8.46), WRONG-TYPE 51 (4.63), BOUNDARY 75 (2.88); the type card delivered on 644 of 660 error items",
                f"{AUDIT} K2/K3/K4 (9.29 / 9.30 / 5.33; 157 missed or wrong gold values are in TRAIN's list)",
                f"{M1C} section 3.2: M1 is convention transfer (133 of 154 newly correct fillers printed in the block)",
            ],
            "the_change": "ONE store added: knowledge_stores.slot-exemplars, phase_supply.solver, nine slot-bearing TRAIN exemplars per row from the R01-excluded pool, three per intent of the row's retrieval shortlist, nearest first by the row's own speech, never one M1 already delivers",
            "what_w5_is_not": (
                "It does NOT enable native-candidate-slot-view-v1 (decisions 125/126): that view scopes the intent-role rows of the "
                "slot-contract cards a row already receives and performs no retrieval, selection or filtering (its own docstring: 'No "
                "selection, retrieval, answer generation, or tokenization occurs here'); card selection is W1's factor and card "
                "content W4's. Enabling it here would be a second factor. It does NOT change the M1 route or read Perception's "
                "live candidates (no code path conditions a phase supply on them; the pre-flight retrieval shortlist stands in)."),
            "entity_taxonomy": "the error-source read's classes (MISSING, SPURIOUS, WRONG-TYPE, BOUNDARY, WRONG-VALUE, NEAR, FORMAT)",
        },
        "store": store,
        "token_cost": token_cost,
        "fit_statement": fit_statement,
        "fit": fit,
        "fold_a_offline": fold_a,
        "expectation_basis": {
            "measured_conversion": estimate["conversion"], "per_kind": exp["per_kind"],
            "expected_pp": exp["expected_pp"], "oracle_pp": exp["oracle_pp_if_every_newly_printed_item_converted"],
            "var1_analogue": {"source": SYNTHESIS + " row C7", "k30_vs_k20_slu_pp": 0.09, "ci95": [-1.47, 1.60], "roster": "R01C 625"},
            "m1_replicate": {"slu_pp": 13.70, "why_not_the_declared_basis": "M1 was read against a system WITHOUT exemplars; W5 adds to a system that already carries M1's twenty, so only the residual the W5 block newly prints can convert"},
            "benefit_floor_pp": BENEFIT_FLOOR, "declared": "no-harm (the measured expectation is below the floor)",
        },
        "identity": {key: {k2: v for k2, v in ids[key].items() if k2 != "composed_config_diff_against_the_agree_cell"} for key in CELLS},
        "composed_config_diff_against_the_agree_cell": {key: ids[key]["composed_config_diff_against_the_agree_cell"] for key in CELLS},
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL, "never_reflown": True,
                       "in_chain_replicate": {"run_id": SHARED_AA_RUN, "registered_by": "the coordinator (knowledge wave shared A/A, branch fable/waveaa)",
                                              "why": "rule 4 refuses a cross-flight contrast with no in-chain replicate"},
                       "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"{INSTRUMENT} section 2d"}},
        "decision_rule": rule,
        "byte_identity_expectation": {
            "agree_first_phase_supply_output_sha256": AGREE_SUPPLY_OUTPUT,
            "claim": "the added store serves the Solver only and is not an input to the first-phase (Perception boundary) supply, so the supply the flip mints for the arm must carry the AGREE arm's output digest and the smoke's the AGREE smoke's; a different digest means the boundary channel moved -- stop and report",
        },
        "wave_chain": ("Append W5 to the knowledge-wave chain (scripts/flights/wave/batch_chain_wave.sh, branch fable/waveaa) as one more step "
                       "after W4: add a catalogue entry 'w5' with experiment/cell slurp-native-stage3-w5-fold-a-v1, smoke slurp-native-stage3-w5-fold-a-smoke-4-v1, "
                       "campaign_plan configs/campaign/slurp-native-stage3-w5-fold-a-v1.json, run ids SAEA-SLURP-STAGE3-W5-FOLD-A-V1 / -FIT-V1 / -SMOKE-4-V1, "
                       "owner root-slurp-native-stage3-w5-fold-a-v1, and accept step lists ending in 'w4 w5'."),
        "budget_arithmetic": {"arm_family_budget": caps, "smoke_family_budget": smoke_caps,
                              "note": "the AGREE arithmetic (1,080 x 11 contacts, run-cumulative); W5 adds prompt tokens, never contacts"},
        "prohibitions": [
            "No test-split, Fold B or DEV contact or read.", "No re-flying of the sealed AGREE comparator.",
            "No second factor: no other template, knob, store, view, roster, geometry or session change.",
            "No paper-scale profile.", "No flight before root mints the decision receipt, the coordinator registers the shared A/A and the cells are flipped.",
            "A SLU gain is never reported as an admitted benefit under this no-harm declaration.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-stage3-w5-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at, "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": "With nine row-matched, slot-bearing TRAIN exemplars added to the Solver (three per intent of the row's retrieval shortlist, keyed by the row's own speech, never one M1 already delivers) and nothing else changed, does the official pooled SLU-F1 on TRAIN Fold A 1,080 stay within the design's null -- and where does it move -- read against the knowledge wave's shared in-chain A/A?",
        "one_factor": f"{THE_STORE} added (release {added['release']['sha256']}, snapshot content {added['snapshot']['sha256']}, scope table {receipt['table_pin']['sha256']}) and its two receipts appended to preparation_source_receipts",
        "cells": {key: {k2: ids[key][k2] for k2 in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"], "decision_rule_fixed_here": rule,
        "development_numbers_only": "Every number is a TRAIN Fold A development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in CELLS:
        identity = ids[key]
        fam = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            plan_doc = {
                "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind, "cell": identity["cell"],
                "experiment": identity["experiment"], "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at, "status": protocol["status"], "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit, "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": identity["carrier_lock_key"], "run_id": run_id,
                    "attempt_id": identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": identity["execution_profile"], "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"], "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": fam["fit_endpoint_calls_cap"] if is_fit else fam["generation_calls_cap"],
                    "planned_speech_audio_seconds": fam["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": fam["gpu_hours_fit_inclusive"],
                },
                "family_budget": fam,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation." if is_fit else
                    f"Shared core.flight.cli campaign over configs/campaign/slurp-native-stage3-w5-fold-a-v1.json as one step of the knowledge wave's chain, after the shared in-chain A/A {SHARED_AA_RUN} has flown in that chain." if key == "arm" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is outside any campaign plan and never scored."
                ),
                "prepared_phase_supply": {"relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "expected_output_sha256": AGREE_SUPPLY_OUTPUT[key],
                                          "note": facts["byte_identity_expectation"]["claim"]},
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"],
                "purpose": f"{run_id}: " + ("request envelopes only; reads nothing." if is_fit else rule if key == "arm" else "structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before the complete sealed manifest, the ordered outputs, the phase summary and the single complete official TRAIN score exist for BOTH this arm and the shared in-chain A/A; a verdict against the sealed comparator alone is refused.",
            }
            plan_shas[run_id] = wjson(f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1", "recipe_id": "slurp-stage3-w5-fold-a-paired-analysis-v1",
        "title": "Cell W5 -- the standard paired roster read on SLU (primary) + intent (guard) against the knowledge wave's shared in-chain A/A, sealed AGREE beside it, under the no-harm rule",
        "registered_at_utc": args.registered_at, "read_run_id": READ_RUN,
        "run_ids": {"read": READ_RUN, "arm": arm["run_id"], "in_chain_replicate": SHARED_AA_RUN, "comparator": COMPARATOR_RUN},
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": SHARED_AA_RUN, "attempt_id": "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1", "role": "the within-chain null (registered by the coordinator)", "run_manifest_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "context, sealed, never re-flown"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["slu_f1_f1", "scenario_action_exact"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": rule, "margins": {"h_slu": H_SLU, "h_intent": H_INTENT},
        "steps": [
            "1. Refuse unless the W5 arm and the shared A/A each carry a COMPLETE sealed 1,080-row manifest with one successful complete official TRAIN score and this package's / the A/A package's config hashes.",
            "2. Structural stage: every W5 Solver request carries nine slot-exemplars:: items and the twenty train-exemplars:: items; the delivered W5 ids equal the registered selection (selection-v1.jsonl) row by row; realised prompt tokens per Solver/Reviewer/Planner contact, arm minus A/A, against the registered token_cost; compacted contacts on each arm (expected 0).",
            "3. Score once per arm with slurp-slu-official-train through core.scoring_batch, never sharded.",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of arm minus shared A/A on official pooled SLU-F1 (primary) and intent accuracy (guard); the same delta against the sealed AGREE arm BESIDE it, never instead.",
            f"5. Apply the rule: ADMITTED (no harm) iff SLU lower bound >= -{H_SLU} and intent lower bound >= -{H_INTENT}; HARMFUL iff either upper bound < 0; otherwise NOT ADMITTED (width). A SLU lower bound above zero is reported as a development-fold effect, never as an admitted benefit.",
            "6. Mechanism read (model-free, counts only), in the error-source read's taxonomy: MISSING / SPURIOUS / WRONG-TYPE / BOUNDARY / WRONG-VALUE / NEAR / FORMAT arm vs A/A; the registered newly-printed items (registered-facts-v1.json fold_a_offline) re-read -- converted, unchanged, broken; SPURIOUS on the empty-gold rows; intent flips on the rows whose gold intent is outside the shortlist.",
            "7. Report the per-scenario table in both weightings and the frontier row (decision 75).",
        ],
        "read_driver_family": READ_DRIVER,
        "output": {"analysis_root": f"analysis/{READ_RUN}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/w5/w5_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None, "owner": "root", "coordinator": "Fable5.1", "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 knowledge-wave item (label none), no-harm declaration. One arm on TRAIN Fold A 1,080 read at the knowledge wave's shared in-chain A/A, and a four-row form smoke.",
        "decision": "Fly cell W5: the retained AGREE arm with ONE store added (knowledge_stores.slot-exemplars: nine slot-bearing TRAIN exemplars per row to the Solver, scoped by the row's retrieval shortlist), read at the shared in-chain A/A " + SHARED_AA_RUN + " flown in the same chain; SLU-F1 primary, intent guard; no-harm at the Fold A half-widths.",
        "authorization_basis": f"Owner decision 170 (W5 in knowledge wave 1); 164 (the wave), 133 (scope of intent-primary), 139 (expectation from measured numbers), 127 (no-harm form), 28/86; the synthesis {SYNTHESIS}; the instrument {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "build_script": {"path": BUILD_SCRIPT, "sha256": sha_file(BUILD_SCRIPT)},
            "estimate_script": {"path": ESTIMATE_SCRIPT, "sha256": sha_file(ESTIMATE_SCRIPT)},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "base_cell": f"the retained AGREE arm {COMPARATOR_RUN} (owner decision 161): W5 is that fragment with one store added",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k2: caps[k2] for k2 in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a no-harm reading of one knowledge-retrieval change on a development fold.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": ["any flight before the cells are flipped, the receipt is minted and the shared A/A is registered", "touching the resident np4 session by anyone but the coordinator", "any ASR, transcript, encoder or paid-API contact", "re-flying or re-scoring any sealed cell", "--allow-output-change on the re-pin tool", "any change beyond the registered store"],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": LIVE_SLOT, "no_child_start_stop": True},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme, prereg = render_docs(args, ids, store, token_cost, fold_a, facts, fit, rule, fence, caps, smoke_caps, fit_statement, primary_why)
    readme_sha = wr(PACKAGE + "/README.md", readme)
    prereg_sha = wr(PREREG, prereg)

    ledger = "not-requested"
    if args.append_ledger:
        ledger = append_ledger(args, ids, plan_shas, store, data)
    print(json.dumps({"package": PACKAGE, "ledger": ledger,
                      "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol": protocol_sha,
                                  "analysis-recipe": recipe_sha, "root-admission-draft": draft_sha, "prereg": prereg_sha, **plan_shas},
                      "identity": {key: {"run_id": ids[key]["run_id"], "composed": ids[key]["composed_config_hash"],
                                         "protocol": ids[key]["protocol_hash"]} for key in CELLS},
                      "fit": fit.get("status")}, indent=2))
    return 0


def _fit_lines(fit: dict) -> str:
    if fit.get("status") != "MEASURED_BY_CHECK":
        return "PENDING: core.flight.cli check not yet folded in."
    lines = ["| cell | phase | decision | rendered (4 B/token) | operational margin | physical margin |", "| --- | --- | --- | ---: | ---: | ---: |"]
    for key, cell in fit["cells"].items():
        for p in cell.get("prompt_budget_per_phase", []):
            lines.append(f"| {key} | {p.get('phase')} | {p.get('decision')} | {p.get('rendered_text_tokens')} | {p.get('operational_margin_tokens')} | {p.get('physical_margin_tokens')} |")
    return "\n".join(lines)


def render_docs(args, ids, store, token_cost, fold_a, facts, fit, rule, fence, caps, smoke_caps, fit_statement, primary_why):
    arm, smoke = ids["arm"], ids["smoke"]
    exp = facts["expectation_basis"]
    m = store["build_measure"]
    risk = fold_a["risk"]
    cost_lines = ["| phase | contacts (carrying the M1 block) | added tokens mean / max | realised prompt max (AGREE) | projected max |", "| --- | ---: | --- | ---: | ---: |"]
    for phase, p in token_cost["per_phase"].items():
        cost_lines.append(f"| {phase} | {p['contacts']} ({p['contacts_carrying_the_m1_block']}) | {p['added_tokens_mean']} / {p['added_tokens_max']} | {p['realised_prompt_tokens_max']} | {p['projected_prompt_tokens_max']} |")
    kinds = ["MISSING", "SPURIOUS", "WRONG-TYPE", "BOUNDARY", "WRONG-VALUE", "NEAR", "FORMAT"]
    item_lines = ["| kind (error-source taxonomy) | AGREE items | gold value printed by W5 | already printed by M1 | NEWLY printed by W5 | expected pp |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for k in kinds:
        per = exp["per_kind"].get(k, {})
        item_lines.append(f"| {k} | {fold_a['error_items_by_kind'].get(k, 0)} | {fold_a['gold_pair_printed_by_w5'].get(k, 0)} | "
                          f"{fold_a['gold_pair_already_printed_by_m1'].get(k, 0)} | {fold_a['newly_printed_by_w5_not_m1'].get(k, 0)} | "
                          f"{per.get('expected_pp', '--')} |")
    ex = store["roster_exclusion_proof"]
    readme = f"""# Cell W5: slot-side retrieval (knowledge wave, owner decision 170)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; both cells **held**.
Nothing here authorises a flight, a flip or an admission entry. Development numbers only (owner decisions 28 and 86).

**What W5 is.** The retained AGREE arm (`{COMPARATOR_RUN}`, official SLU-F1 65.16 / intent 85.83 on TRAIN Fold A)
with ONE store ADDED: `knowledge_stores.slot-exemplars`, a second speech-keyed TRAIN exemplar route delivered to
the **Solver**, the node that fills slots -- the M1 mechanism (row-matched content keyed by the row's own speech),
now scoped by the row's intent shortlist. Per row it delivers **nine slot-bearing TRAIN exemplars**: three for each of
the first three intents of the row's AGREE boundary ranking (written-key cosine + 1.0 x the pinned exemplar vote -- the
retrieval-side analogue of Perception's three candidates), nearest first by the row's own sealed speech vector, never
an utterance the M1 route already delivers on that row, filled by the nearest other slot-bearing exemplars where a
shortlist intent has fewer than three inside the recall ({m['delivered_tier_a_share'] * 100:.2f} % of delivered items come from the shortlist tier;
{m['fill_items_per_row_histogram'].get('0', 0)} of 1,080 rows need no fill).

| item | value |
| --- | --- |
| store | `slot-exemplars`, role `train-exemplars`; release `{store['release']['sha256']}` binding the ALREADY RELEASED R01-excluded pool snapshot (content `{store['snapshot']['sha256']}`, 8,554 utterances) |
| route | `phase_supply.solver`: the M1 route's own speech query and TRAIN key vectors; recall k 300; `saea-rank-wcos-prior-agree-v1` at w_cos 0 / w_prior 0 / w_agree 1; `saea-fuse-associated-values-v1` m 300 / c 1 / top_l 9 |
| the per-row order | `{store['scope_table']['relpath']}` (sha256 `{store['scope_table']['sha256']}`), a sealed-agreement table carrying a strictly decreasing share per listed facet |
| verification | the replayed boundary order reproduces the AGREE delivered eight on {store['verification']['replayed_boundary_order_reproduces_delivered_eight']} / 1,080 rows; the route as it will fly selects exactly the intended nine on {store['verification']['flown_route_reproduces_intended_selection']} / 1,080 rows |
| construction | `{BUILD_SCRIPT}` (model-free; contacts model 0 / tokenizer 0 / encoder 0 / embedder 0 / scorer 0 / GPU 0); NO encoder pass is needed (the M1 query and key vector files already cover every row and every pool utterance) |
| unchanged | the M1 route, the boundary channel and its agreement term, the slot-contract cards and their candidate supply, roster, geometry, session, program, templates, normaliser, scorers |

**Roster exclusion proof** (in the build receipt): {ex['roster_rows']} Fold A rows / {ex['roster_utterances']} utterances against {ex['pool_values']} pool values /
{ex['pool_utterances']} utterances / {ex['pool_recordings']:,} recordings: **{ex['fold_a_utterances_in_pool']} Fold A utterances in the pool** (utterance identity = first three
sample-id fields, any recording refuses the build). The pool is a strict subset of the flown M1 pool ({ex['m1_pool_utterances_outside_this_pool']} M1 utterances -- the R01 rows -- are
outside it). No Fold A gold, flight output or score entered the construction.

**What W5 is not.** It does not enable `native-candidate-slot-view-v1` (decisions 125/126): that view scopes the
intent-role rows of cards a row already receives and performs no retrieval or filtering; card selection is W1's factor
and card content W4's, so enabling it would be a second factor. It reads no live Perception output: no code path
conditions a phase supply on Perception's candidates, so the pre-flight retrieval shortlist stands in (decision 47's
"speech plus the drafted intent", realised pre-flight).

**Primary metric.** {primary_why}

**Entity taxonomy.** W5 is read against the 2026-09-27 error-source read's classes (MISSING / SPURIOUS / WRONG-TYPE /
BOUNDARY / WRONG-VALUE / NEAR / FORMAT; `entity_items` imported unchanged by the estimate).

## Declared expectation: NO-HARM (from measured numbers only, row 139)

{chr(10).join(item_lines)}

The W5 block prints the gold value of {fold_a['gold_pair_printed_by_w5'].get('MISSING', 0)} MISSING items, but the row's own M1 block already prints
{fold_a['gold_pair_already_printed_by_m1'].get('MISSING', 0)} MISSING items' values without converting them: the missed values are mostly already in front of the
Solver. W5 NEWLY prints **{fold_a['newly_printed_by_w5_not_m1'].get('MISSING', 0)} MISSING + {fold_a['newly_printed_by_w5_not_m1'].get('BOUNDARY', 0)} BOUNDARY items on {fold_a['rows_touched']} rows** (of the audit's 157 in-list
items, at most these). At M1's measured delivered-filler conversion ({exp['measured_conversion']['m1_delivered_filler_conversion']}: 133 newly correct fillers printed in the
block over 0.5719 x 941 printed gold fillers, {M1C} sections 2.1 and 3.2; a lower bound) times the error-source read's
isolated pp per repaired item, the expectation is **{exp['expected_pp']} pp** (oracle {exp['oracle_pp']} pp if every newly printed item
converted). The direct analogue agrees: VAR-1 (R01C 625) exemplar budget 30 vs 20 read **+0.09 [-1.47, +1.60]** SLU. M1's
own +13.70 SLU (replicate) is not the basis: it was read against a system without exemplars. Both measured figures sit
far below the {BENEFIT_FLOOR} pp benefit floor at n = 1,080, so the arm is declared `admission` `no-harm`, `harm_margin_pp`
{H_SLU} (SLU) with intent {H_INTENT} the guard, `expected_effect_pp` 0.0, `claims_benefit` false, `replicate_run_id`
`{SHARED_AA_RUN}`.

**Named risks (counts, AGREE rows).** All {risk['empty_gold_rows']} empty-gold rows receive nine slot-bearing exemplars
(SPURIOUS is the largest error class, 253 items; K3); {risk['w5_printed_pairs_of_types_absent_from_gold']:,} of {risk['w5_printed_pairs']:,} printed (type, value) pairs are of types the
row's gold does not carry. On {risk['rows_gold_intent_outside_shortlist']} rows the gold intent is outside the shortlist that scopes the block
({risk['intent_correct_rows_gold_outside_shortlist']} of them intent-correct on AGREE); {risk['rows_w5_block_without_gold_intent']} rows receive no gold-intent exemplar from W5 (M1's twenty are unchanged).

## Token cost and Fit

{chr(10).join(cost_lines)}

The W5 block is {token_cost['block']['tokens_per_contact']['mean']} tokens per contact on average (max {token_cost['block']['tokens_per_contact']['max']}) at {token_cost['chars_per_token']}
characters per token (measured on the flown M1 exemplar block; same line form); per row +{token_cost['per_row']['added_tokens_mean']} tokens mean (max
{token_cost['per_row']['added_tokens_max']}), {token_cost['added_share_of_prompt_volume'] * 100:.2f} % of the AGREE prompt volume. {token_cost['compaction_projection']}.

{fit_statement}

{_fit_lines(fit)}

## Files

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, with the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact; the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the smoke's plans |
| `analysis-recipe-v1.json` | the paired read; `run_ids.read` = `{READ_RUN}` |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/w5/w5_mint_receipt.py` |

**Sequence.** (1) The coordinator registers the shared A/A `{SHARED_AA_RUN}` and the wave chain. (2) Root countersigns
the DRAFT rows (four flight rows and two model-free rows; the READ row stays draft until the seal), mints
`{DECISION_RELPATH}` with `scripts/flights/w5/w5_mint_receipt.py`. (3) Flip with `scripts/flights/w5/w5_flip.sh` (smoke,
then arm; minted first-phase supplies must reproduce the AGREE digests). (4) Chain: {facts['wave_chain']}

**Budgets.** Arm {caps['generation_calls_cap']:,} generation contacts, {caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['repeated_speech_audio_seconds_cap']:,} speech seconds,
{caps['gpu_hours_fit_inclusive']} GPU hours; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']} -- the AGREE arithmetic.
"""
    prereg = f"""# Cell W5 (slot-side retrieval): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
arm fragments by script (decision 58) with one store added, under owner decision 170. Development numbers only.

## The cell

| item | value |
| --- | --- |
| base | the retained AGREE arm `{COMPARATOR_RUN}` (65.1575 / 85.8333), owner decision 161 |
| factor | `{THE_STORE}` ADDED: nine slot-bearing TRAIN exemplars per row to the Solver from the R01-excluded pool (release `{store['release']['sha256']}`, snapshot content `{store['snapshot']['sha256']}`), three per intent of the row's retrieval shortlist, nearest by the row's own speech, never one M1 delivers; order table `{store['scope_table']['sha256']}` |
| in-chain replicate | `{SHARED_AA_RUN}` (the knowledge wave's shared A/A, registered by the coordinator) |
| primary / guard | official pooled SLU-F1 / intent accuracy (decision 133 scopes intent-primary to intent-acting mechanisms) |
| entity taxonomy | the error-source read's MISSING / SPURIOUS / WRONG-TYPE / BOUNDARY / WRONG-VALUE / NEAR / FORMAT |
| admission | NO HARM: SLU lower bound >= -{H_SLU}, intent lower bound >= -{H_INTENT} |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}`; read `{READ_RUN}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Decision rule (fixed here)

{rule}

## The measurement declaration

```json
{fence}
```

## Prohibitions

No test-split, Fold B or DEV contact; no re-flying of the comparator; no second factor; no paper-scale profile; no
flight before the receipt is minted, the shared A/A registered and the cells flipped; `--allow-output-change` never passed.
"""
    return readme, prereg


MODEL_TOOL = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
              "prompt bytes the retained AGREE arm's plus nine slot-bearing TRAIN exemplars per Solver/Reviewer/Planner contact from the added slot-exemplars store")
INHERITED = ("TRAIN Fold A discovery rows already exposed by the sealed anchors and every Stage-2/3 Fold A cell (B-series, PLAN, PLANr, ROLL-2, CONV, "
             "the AGREE family, KPROBE, COMP-1, G5, the knowledge wave W1/W3/W4, flown or in flight at registration); this cell adds no new row to the fold and opens no split. Prior exposure is inherited in full.")


def append_ledger(args, ids, plan_shas, store, data) -> str:
    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]

    def flight_notes(key: str, kind: str) -> str:
        identity = ids[key]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if kind == "fit" else identity["attempt_id"]
        declaration = (f"admission no-harm, harm_margin_pp {H_SLU} (SLU primary; intent guard {H_INTENT}), claims_benefit false, expected_effect_pp 0.0, "
                       f"measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {SHARED_AA_RUN}, rows 1080"
                       if key == "arm" else "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4")
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the W5 "
            f"registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and authorises none. Plan SHA256 "
            f"{plan_shas[run_id]}; attempt {attempt}. Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected "
            f"session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) with the four eligible run ids "
            f"{', '.join(eligible)}, the coordinator registers the shared A/A {SHARED_AA_RUN}, then scripts/flights/w5/w5_flip.sh re-pins with "
            f"scripts/flights/repin_cell.py --set-ready, minting each cell's own first-phase supply (item E16; expected output digest "
            f"{AGREE_SUPPLY_OUTPUT[key]}, the AGREE {key}'s); --allow-output-change must never be passed. Every hash in this row moves at the flip. ONE STORE "
            f"ADDED (owner decision 170): {THE_STORE} (release {store['release']['sha256']}, snapshot content {store['snapshot']['sha256']}, order table "
            f"{store['scope_table']['sha256']}), nine slot-bearing TRAIN exemplars per row to the Solver from the R01-excluded pool. "
            f"Measurement declaration ({GATE}): {declaration} -- canonical in {PACKAGE}/registered-facts-v1.json. Caps are the AGREE arithmetic. Stop and "
            f"preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No test-split, Fold B or DEV contact, no comparator re-flight."
        )

    def flight_row(key: str, kind: str) -> str:
        identity = ids[key]
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if kind == "fit" else identity["run_id"]
        scope = (("Cell W5 (slot-side retrieval)" if key == "arm" else "Four-row form smoke of cell W5") + (" -- FIT spend identity, request envelopes only, no generation" if kind == "fit" else "")
                 + ": the retained AGREE arm with nine shortlist-scoped, speech-keyed, slot-bearing TRAIN exemplars added to the Solver" + (", read on no harm against the knowledge wave's shared in-chain A/A" if key == "arm" else ", structural form only, never scored"))
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL, f"slurp TRAIN Fold A {identity['rows']}", "discovery",
                 identity["split_identity_hash"], "no", str(budget["fit_endpoint_calls_cap"] if kind == "fit" else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", flight_notes(key, kind), ""]
        return " | ".join(cells).strip()

    read_row = " | ".join(["", args.registered_at[:10], READ_RUN, "model-free-check",
        f"The paired read of cell W5 against the knowledge wave's shared in-chain A/A {SHARED_AA_RUN} (SLU-F1 primary, intent guard), the sealed AGREE arm beside it, by the recipe {PACKAGE}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts; one official score per arm is the flights' own.",
        "no model or tool contact; read of sealed bytes only", "slurp TRAIN Fold A 1080, sealed W5 arm and shared A/A (after the seal)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure; reads sealed outputs and official scores only. Prior exposure inherited in full.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any number is read) {args.registered_at[:10]} at study commit {args.study_commit}. Recipe slurp-stage3-w5-fold-a-paired-analysis-v1; output analysis/{READ_RUN}. It admits nothing beyond the no-harm entry it is registered for.",
        ""]).strip()
    build_row = " | ".join(["", args.registered_at[:10], BUILD_ROW, "model-free-check",
        "Build cell W5's per-row exemplar order (the sealed-agreement table the added slot-exemplars route ranks with) and the release that binds the already released R01-excluded TRAIN exemplar pool under the store id slot-exemplars, through the flight's own build_supply_for_phase / KbFacetProvider recall, ranker and fuser over pinned vectors; prove that no Fold A utterance is in the pool and that the route as it will fly selects the intended nine per row. Zero model, tokenizer, encoder, embedder, scorer, server, network and GPU contacts.",
        "no model or tool contact; local reads of pinned vector files, the pinned agreement table and two released snapshots", "slurp TRAIN Fold A 1080 (sealed speech query vectors and deterministic retrieval rankings only; no gold) + the R01-excluded TRAIN construction pool (8,554 utterances)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No speech exposure: sealed vectors already pinned by the flown AGREE arm; pool annotations are the already-released exemplar knowledge.",
        f"{PREP}/receipt.json",
        f"MODEL-FREE BUILD, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]} by the W5 registration agent; script {BUILD_SCRIPT}; receipt sha256 {store['scope_receipt']['sha256']}; order table {store['scope_table']['sha256']}; release {store['release']['sha256']}; verification boundary order 1080/1080, flown-route selection 1080/1080; Fold A utterances in the pool 0; no encoder pass. It authorises nothing.",
        ""]).strip()
    estimate_row = " | ".join(["", args.registered_at[:10], ESTIMATE_ROW, "model-free-check",
        "Offline Fold A estimate for cell W5: on the sealed AGREE arm, classify the entity error items with the error-source read's taxonomy, count those whose gold (type, value) the W5 block newly prints (not printed by the row's M1 block), apply M1's measured delivered-filler conversion and the error-source isolated pp per item, count the named risks (empty-gold rows, gold intent outside the shortlist), and measure the per-contact token cost against the sealed trace. Gold read offline, counts only. Zero model, server, tokenizer, encoder, embedder, scorer and GPU contacts.",
        "no model or tool contact; read-only sealed AGREE outputs and trace; governed train gold offline", "slurp TRAIN Fold A 1080 (sealed AGREE arm, ids and counts only)", "discovery",
        ids["arm"]["split_identity_hash"], "no", "0", "0", "0", "No new speech exposure: sealed bytes already exposed by the AGREE arm. Prior exposure inherited in full.",
        ESTIMATE,
        f"MODEL-FREE READ OF SEALED BYTES, RUN BEFORE THIS ROW WAS WRITTEN (disclosed; DRAFT, root countersignature pending) {args.registered_at[:10]}; script {ESTIMATE_SCRIPT}; output sha256 {sha_file(data / ESTIMATE)}. Development numbers (owner decisions 28 and 86); it authorises nothing.",
        ""]).strip()

    fresh = {}
    for key in CELLS:
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = flight_row(key, kind)
    fresh[READ_RUN] = read_row
    fresh[BUILD_ROW] = build_row
    fresh[ESTIMATE_ROW] = estimate_row
    for run_id, line in fresh.items():
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")
    order = list(fresh)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all W5 rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = ("\n## Cell W5: slot-side retrieval (knowledge wave, owner decision 170) -- the arm, its four-row smoke, the READ row, the model-free "
              "build and the offline estimate (DRAFT, root countersignature pending)\n\nFour unconsumed flight rows, one READ row registered with the "
              "flight, and two model-free rows. The in-chain A/A is the knowledge wave's shared one, registered by the coordinator. None of these rows "
              "is countersigned and none authorises a contact.\n\n"
              "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[r] for r in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
