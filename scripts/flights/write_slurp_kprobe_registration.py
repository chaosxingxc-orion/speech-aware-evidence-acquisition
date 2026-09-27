#!/usr/bin/env python3
"""Write cell KPROBE's registration package from the committed configs.

Reads the derived fragments and the roster-derivation receipt, recomposes the
cell's own hashes, PROVES the composed-config diff against the locked PLAN cell
is the one facet-source pin plus per-flight bookkeeping, and writes the package
documents, a repository copy of the key file's receipt, a draft decision receipt
for root, and (with ``--append-ledger``) the three exposure rows. Config alone:
no adapter, no split load, no lock, no contact; it flips nothing and mints
nothing.

    python scripts/flights/write_slurp_kprobe_registration.py \\
        --package-dir docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-<N>-v1 \\
        --data-root "$SPEECHRL_DATA_DIR" \\
        --study-commit <sha> --registered-at 2026-09-27T06:00:00.000000+00:00 [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

PARENT_EXPERIMENT = "slurp-native-default-plan-lock-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
CENTROID_ARTIFACT = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
CENTROID_RECEIPT_RELPATH = f"prepared/{CENTROID_ARTIFACT}/receipt.json"
CENTROID_FACETS_RELPATH = f"prepared/{CENTROID_ARTIFACT}/facets.jsonl"

DIAGNOSTIC = "docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md"
DIAGNOSTIC_RECIPE = "scripts/analysis/slurp_boundary_key_construction_diagnostic.py"
CONV_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1"
CONV_READ = "docs/results/2026-09-27-slurp-conv-probe-read.md"
WITHIN_FLIGHT_NULL = "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
BAD_CASE_BANK_DOC = "docs/results/2026-09-24-slurp-plan-bad-case-bank.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
BUILDER = "scripts/build_slurp_intent_boundary_centroid_keys.py"
ROSTER_SCRIPT = "scripts/analysis/slurp_boundary_centroid_conversion_roster.py"
READ_DRIVER = "scripts/analysis/slurp_kprobe_read.py"
CONFIG_TEST = "tests/unit/test_kprobe_config.py"
LEDGER = "docs/exposure-ledger.md"

HEADROOM_SLU = 5.41 / 130.0
HEADROOM_INTENT = 12.04 / 130.0
ARM_ROWS = 1080
ARM_BAR_PP = 2.5

#: Beyond the ONE pin, the composed-config paths that may differ from the
#: locked PLAN cell: this cell's own identities and caps, the dropped supply
#: pin, the appended receipt, the prose fields and the experiment's own
#: population/budget/readiness block.
BOOKKEEPING_PREFIXES = (
    "native_contact_fit.",
    "prepared_phase_supply",
    "preparation_source_receipts",
    "what_this_is",
)
THE_ONE_PIN = "knowledge_stores.intent-boundaries.phase_supply.perception.facet_source"

GOLD_SELECTION = (
    "THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class and each "
    "row's gold intent were read on the scoring side only, in the committed roster "
    "derivation, before this cell existed. That is legitimate for a CONDITIONAL estimate on "
    "a TRAIN roster and it is legitimate for nothing else: NO POOLED OR ROSTER-LEVEL CLAIM "
    "MAY EVER BE MADE FROM THIS CELL, because its population was chosen by the mechanism's "
    "own effect. Gold reaches no query, no key, no weight, no selector and no runtime -- the "
    "key itself is built from each pool value's frozen build-time task_target, a store "
    "property -- and no gold label, intent name as content, transcript or utterance text is "
    "printed or persisted anywhere in this package."
)
NO_POOLED_CLAIM = (
    "This cell reads ONE quantity: the per-row intent verdict on a gold-selected subset. It "
    "may never be reported as a pooled SLU-F1 or intent-accuracy effect, as an admission, as "
    "a replication, or as evidence about any roster. Its population is the mechanism's own "
    "beneficiaries; a pooled number computed over it would be a selection artefact by "
    "construction. The cell also cannot see harm: every row here is already intent-wrong in "
    "the comparator, so the rows where the key could COST a correct intent -- including the "
    "rows that LOSE their gold entry under the centroid key, counted in the roster derivation "
    "-- are outside this roster and remain a construction cell's own question."
)
WHY_INTENT_NOT_SLU = (
    "The within-flight null (" + WITHIN_FLIGHT_NULL + ") measured 0 intent flips out of 200 "
    "request-identical rows, so an intent flip is ATTRIBUTABLE rather than noise and a per-row "
    "intent read is legible at this size; cell CONV read the same quantity the same way at "
    "n = 70 (" + CONV_READ + "). Pooled SLU-F1 is not legible here: its own measured noise "
    "would swamp the roster, and the official SLU-F1 is entity-only while this mechanism acts "
    "on the intent. The official scorer still produces the number -- the read takes its "
    "per-sample scenario_action_exact field and nothing else -- so the standard-scoring rule "
    "is intact."
)


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


def sha_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def composed_diff(parent_values: dict, mine: dict, experiment_keys: set, baseline_keys: set) -> dict:
    """Every composed path that differs, classified: the one pin, baseline
    bookkeeping, or the experiment fragment's own block (the cell's population,
    budgets, purpose and label -- its registration, never a knowledge key; an
    experiment key that is also a baseline key is refused outright). Anything
    else is a refusal."""

    overlap = sorted(experiment_keys & baseline_keys)
    if overlap:
        raise SystemExit(f"the experiment fragment overrides baseline keys: {overlap}")
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(set(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>")))
    one_pin = [k for k in changed if k.startswith(THE_ONE_PIN + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING_PREFIXES) and not k.startswith(THE_ONE_PIN)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_pin and k not in bookkeeping]
    other = [k for k in changed if k not in one_pin and k not in bookkeeping and k not in experiment_block]
    return {"one_pin": one_pin, "bookkeeping": bookkeeping, "experiment_fragment_own_block": experiment_block,
            "other": other, "all": changed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True, help="repo-relative readiness package directory")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/kprobe")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-kprobe")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)

    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    derivation_relpath = package + "/roster-derivation-v1.json"
    derivation = json.loads(rd(derivation_relpath))
    roster = derivation["roster"]
    rows = int(roster["count"])
    tag = f"kprobe-fold-a-{rows}"
    experiment = f"slurp-native-stage3-{tag}-v1"
    package_name = f"slurp-stage3-{tag}-v1"
    decision_id = f"slurp-stage3-{tag}-admission-v1"
    decision_relpath = f"coordination/{package_name}/root-admission-v1.json"

    document = json.loads(rd(f"configs/experiment/{experiment}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    parent_doc = json.loads(rd(f"configs/experiment/{PARENT_EXPERIMENT}.json"))
    parent_cell = parent_doc["cells"][0]
    parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"], parent_cell["baseline_fragment"], PARENT_EXPERIMENT)
    split = document["population"]["split_identity_hash"]
    phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
    caps = document["family_budget"]
    fit = composed.values["native_contact_fit"]
    run_id = cell["run_id"]
    fit_run = fit["run_id"]
    rows_needed_intent = math.ceil(ARM_BAR_PP / HEADROOM_INTENT)
    rows_needed_slu = math.ceil(ARM_BAR_PP / HEADROOM_SLU)

    # ---- the one-pin proof, from the composed configs ----------------------
    baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
    diff = composed_diff(parent.values, composed.values, set(document) | set(parent_doc), baseline_keys)
    if diff["other"]:
        raise SystemExit("composed config differs from the locked PLAN cell beyond the one pin and bookkeeping: " + ", ".join(diff["other"]))
    if not diff["one_pin"]:
        raise SystemExit("the composed config does not move the boundary facet_source pin at all")
    mine_p = composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    parent_p = parent.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if {k: v for k, v in mine_p.items() if k != "facet_source"} != {k: v for k, v in parent_p.items() if k != "facet_source"}:
        raise SystemExit("the boundary perception spec differs beyond facet_source")
    my_receipts = list(composed.values["preparation_source_receipts"])
    parent_receipts = list(parent.values["preparation_source_receipts"])
    if my_receipts[:-1] != parent_receipts or my_receipts[-1]["relpath"] != CENTROID_RECEIPT_RELPATH:
        raise SystemExit("preparation_source_receipts is not the parent's list plus the centroid receipt")
    if "prepared_phase_supply" in composed.values:
        raise SystemExit("the derived cell must carry no committed prepared_phase_supply")

    # ---- the key file's receipt, verified and copied into the package -------
    receipt_path = Path(args.data_root) / CENTROID_RECEIPT_RELPATH
    receipt_sha = sha_file(str(receipt_path))
    if receipt_sha != my_receipts[-1]["sha256"] or receipt_sha != derivation["treatment"]["receipt_sha256"]:
        raise SystemExit("the centroid receipt on the data root does not hash to the pinned sha256")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt["artifact"]["sha256"] != mine_p["facet_source"]["sha256"]:
        raise SystemExit("the receipt's artifact sha256 is not the baseline's facet_source pin")
    facets_sha = sha_file(str(Path(args.data_root) / CENTROID_FACETS_RELPATH))
    if facets_sha != mine_p["facet_source"]["sha256"]:
        raise SystemExit("the centroid facets file on the data root does not hash to the baseline's pin")
    receipt_copy_sha = wr(package + "/centroid-keys-receipt-v1.json", receipt_path.read_text(encoding="utf-8"))
    if receipt_copy_sha != receipt_sha:
        raise SystemExit("the repository copy of the receipt does not hash to the data-root receipt")

    pa = derivation["proof_a_diagnostic_reproduced"]
    pb = derivation["proof_b_treatment_file_through_production_recall"]
    pc = derivation["proof_c_population_through_production_constructor"]
    fold_a_cells = pb["arms"]["train-fold-a-plan"]["cells"]
    fold_a_wrong = pb["arms"]["train-fold-a-plan"]["per_class"]["INTENT-WRONG"]
    fold_a_correct = pb["arms"]["train-fold-a-plan"]["per_class"].get("CORRECT", {})

    measurement = {
        run_id: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": (
                "per-row intent correctness (official scorer's scenario_action_exact), reported "
                "as the conditional rate P(correct | newly delivered) with a binomial CI95"
            ),
            "rows": rows,
            "note": (
                "The cell measures a CONDITIONAL RATE and makes NO effectiveness claim. Its "
                + str(rows)
                + " rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 "
                "this is a form proof by size and claims_benefit is false; expected_effect_pp is "
                "0.0 because the cell registers no effect to look for. What it delivers is the "
                "centroid boundary key's conversion from delivery to correctness, measured: of the "
                "rows whose gold intent's boundary entry the key newly delivers, the proportion m/"
                + str(rows)
                + " that move from a wrong intent to the gold intent. RE-DECLARATION RULE: a later "
                "1,080-row construction cell that flies this key declares expected_effect_pp = "
                "m x 0.092615 pp intent accuracy (intent primary under owner decision 133, official "
                "SLU-F1 the non-inferiority guard; m x 0.041615 pp SLU-F1 for the guard), never a "
                "midpoint. It is NOT an admission request: no admission mode is declared, no harm "
                "margin is claimed, and no pooled or roster-level number may ever be read off this "
                "cell, whose population was selected with gold, offline."
            ),
        }
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL "
            "stage3_measurement block scripts/checks/stage3_effect_floor_check.py resolves. The "
            "same block is repeated in the preregistration's fenced json for readability; this "
            "copy has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decision": 145,
        "rows": rows,
        "stage3_measurement": measurement,
        "the_unmeasured_quantity": {
            "name": "P(correct | newly delivered) -- the centroid key's conversion from delivery to correctness",
            "what_the_diagnostic_measured": (
                "DELIVERY only: on the intent-wrong rows the written key delivers gold within eight on "
                "45.0 / 44.6 / 35.8 % (Fold A / ROLL-1 / DEV-2000, held-out pools) and the centroid key "
                "on 71.2 / 64.7 / 66.8 %, at zero token cost. Whether the Solver then answers correctly "
                "with the entry present is mode (iv) of that note, unmeasured because it needs the answer "
                "the row would give, which needs contacts."
            ),
            "conv_precedent": (
                "cell CONV measured the agreement term's conversion on its own 70 newly delivered rows: "
                "m = 32 of 70 (45.71 %, Wilson [34.57, 57.30]); the arm was then re-declared from that m "
                "(decision 143). This probe repeats the design for the key, not the weight."
            ),
            "the_only_directly_observable_prior": (
                "86 of the 191 intent-wrong Fold A rows already receive the gold intent's boundary entry "
                "under the written key and are wrong anyway. Neither that zero nor CONV's 32/70 is a "
                "prediction for this key; the cell is registered without a predicted value on purpose."
            ),
        },
        "headroom_registered_by_the_class": {
            "intent_pp_per_row": round(HEADROOM_INTENT, 6),
            "slu_pp_per_row": round(HEADROOM_SLU, 6),
            "source": (
                "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/registered-facts-v1.json, "
                "expected_effect_derivation: INTENT-UNCOVERED perfect-repair headroom 5.41 pp SLU-F1 "
                "and 12.04 pp intent accuracy over 130 rows. Not re-derived here. This roster is the "
                "intent-wrong rows the key newly reaches (bank classes INTENT-UNCOVERED and INTENT-COVERED, "
                "split in the derivation); the per-row figure is applied as the task's re-declaration rule "
                "states it and the class split is reported beside m."
            ),
            "re_declaration_rule": (
                "a later 1,080-row construction cell's expected_effect_pp = (rows of this roster that "
                f"move from a wrong intent to the gold intent) x {HEADROOM_INTENT:.6f} pp intent accuracy "
                f"(primary, owner decision 133) and x {HEADROOM_SLU:.6f} pp SLU-F1 (the guard)."
            ),
            "rows_needed_to_clear_the_2_5_pp_intent_bar_at_n_1080": rows_needed_intent,
            "rows_needed_under_the_retired_slu_framing": rows_needed_slu,
            "ceiling_intent_pp_at_perfect_conversion": round(rows * HEADROOM_INTENT, 4),
        },
        "treatment_key_file": {
            "artifact_id": CENTROID_ARTIFACT,
            "facets": {"relpath": CENTROID_FACETS_RELPATH, "sha256": facets_sha, "rows": receipt["artifact"]["rows"]},
            "receipt": {"relpath": CENTROID_RECEIPT_RELPATH, "sha256": receipt_sha,
                        "repository_copy": package + "/centroid-keys-receipt-v1.json",
                        "schema": receipt["schema"], "kind": receipt["kind"]},
            "why_a_new_receipt_kind": receipt["why_a_new_receipt_kind"],
            "construction": receipt["construction"],
            "inputs": receipt["inputs"],
            "measured": receipt["measured"],
            "builder": {"relpath": BUILDER, "sha256": sha_file(BUILDER)},
            "tool_contact_ledger_row": CENTROID_ARTIFACT,
            "not_re_pinned": (
                "only this cell's derived baseline pins the centroid file; the 211 committed configs "
                "that pin the written key are untouched (owner decision 145), and the store rebuild "
                "waits on this cell's m"
            ),
        },
        "delivery_proofs": {
            "derivation": {"relpath": derivation_relpath, "sha256": sha_file(derivation_relpath),
                           "script": {"relpath": ROSTER_SCRIPT, "sha256": sha_file(ROSTER_SCRIPT)}},
            "proof_a_the_diagnostics_arithmetic_reproduces_its_note": {
                "differences": pa["differences"],
                "note": derivation["authority"]["diagnostic_note"],
                "recipe": derivation["authority"]["diagnostic_recipe"],
                "cells_compared": pa["note_cells_compared"],
                "r01_excluded_centroid_geometry": pa["r01_excluded_centroid_geometry"],
                "written_key_recall_reproduces_every_sealed_delivered_set": {
                    label: arm["validation"] for label, arm in pa["arms"].items()
                },
            },
            "proof_b_the_pinned_file_reproduces_through_the_production_recall": {
                "differences": pb["differences"],
                "max_abs_diff_to_diagnostic_r01_excluded_centroid": pb["max_abs_diff_to_diagnostic_r01_excluded_centroid"],
                "fallback_equals_written_key_exactly": pb["fallback_equals_written_key_exactly"],
                "fallback_facet_ids": pb["fallback_facet_ids"],
                "roll1_equals_the_note": {"note": pa["note_cells_compared"]["roll1"]["centroid"], "file": pb["arms"]["roll1"]["cells"]},
                "fold_a_under_the_treatment_file": fold_a_cells,
                "fold_a_under_the_full_pool_centroid_the_note_reports": pa["note_cells_compared"]["train-fold-a-plan"]["centroid"],
                "dev2000_under_the_treatment_file": pb["arms"]["dev2000-added-plan"]["cells"],
                "per_class_fold_a": pb["arms"]["train-fold-a-plan"]["per_class"],
                "production_recall_agreements": {
                    label: {k: v for k, v in arm.items() if k.startswith("production_recall")} | {"rows": arm["rows"]}
                    for label, arm in pb["arms"].items()
                },
            },
            "proof_c_the_production_constructor_agrees": {
                "sealed_boundary_agreement": pc["delivery"]["sealed_boundary_agreement"],
                "fusion_vs_rank_disagreements": pc["delivery"]["fusion_vs_rank_disagreements"],
                "plan_class_split": pc["delivery"]["plan_class_split"],
                "newly_lost_by_class_all_rows": pc["newly_lost_by_class_all_rows"],
                "production_constructor_equals_production_recall_on_the_population": pc["production_constructor_equals_production_recall_on_the_population"],
                "written_boundary_channel": pc["written_boundary_channel"],
                "treatment_boundary_channel": pc["treatment_boundary_channel"],
            },
        },
        "roster": {
            "count": rows,
            "dataset_fragment": roster["dataset_fragment"],
            "derivation": {"relpath": derivation_relpath, "sha256": sha_file(derivation_relpath)},
            "id_list_sha256": roster["id_list_sha256"],
            "split_identity_hash": roster["split_identity_hash"],
            "audio_seconds_total": roster["audio_seconds_total"],
            "intent_wrong_rows_fold_a": fold_a_wrong["rows"],
            "delivered_written": fold_a_wrong["delivered_written"],
            "delivered_centroid": fold_a_wrong["delivered_centroid"],
            "newly_delivered": fold_a_wrong["newly_delivered"],
            "newly_lost_intent_wrong": fold_a_wrong["newly_lost"],
            "newly_lost_correct_rows": fold_a_correct.get("newly_lost"),
            "by_bank_plan_class": pc["population_by_plan_class"],
            "expected_order_of_magnitude": derivation["population"]["expected_order_of_magnitude"],
        },
        "gold_selection": GOLD_SELECTION,
        "no_pooled_claim": NO_POOLED_CLAIM,
        "why_intent_and_not_slu_f1": WHY_INTENT_NOT_SLU,
        "comparator": {
            "run_id": COMPARATOR_RUN,
            "attempt_id": COMPARATOR_ATTEMPT,
            "role": (
                "sealed, already flown, never re-flown and not part of this campaign. It holds these "
                + str(rows)
                + " rows' comparator answers, and every one of them is intent-WRONG there: "
                "the bank's INTENT-UNCOVERED and INTENT-COVERED classes both collapse to INTENT-WRONG in "
                "its own convention. The probe therefore flies the TREATMENT ONLY and the contrast is per-row and offline."
            ),
            "per_row_intent_verdict_authority": {
                "relpath": "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl",
                "sha256": pc["bad_case_bank_sha256"],
                "note": (
                    "the read re-derives the comparator's per-row verdict from the sealed PLAN arm's "
                    "own official score as well and refuses on any disagreement."
                ),
            },
        },
        "identity": {
            "cell": cell["cell_id"],
            "experiment": experiment,
            "run_id": run_id,
            "attempt_id": cell["attempt_id"],
            "fit_run_id": fit_run,
            "fit_attempt_id": fit["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"],
            "parent_baseline_fragment": parent_cell["baseline_fragment"],
            "parent_experiment": PARENT_EXPERIMENT,
            "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"],
            "composed_config_hash": composed.config_hash,
            "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": phash,
            "split_identity_hash": split,
            "service_session": SESSION,
            "declares_prepared_phase_supply": "prepared_phase_supply" in composed.values,
            "boundary_channel": {
                "facet_source": mine_p["facet_source"],
                "parent_facet_source": parent_p["facet_source"],
                "fuse_coverage": mine_p["fuse_coverage"],
                "k": mine_p["k"],
                "tau": mine_p["tau"],
                "rank_weights": mine_p["rank_weights"],
                "declares_agreement_source": "agreement_source" in mine_p,
            },
            "native_episode_policies": {
                key: composed.values["native_episode"].get(key)
                for key in ("finite_completion_policy", "react_exhaustion_policy")
            },
        },
        "composed_config_diff_against_the_locked_plan_cell": {
            "the_one_pin": diff["one_pin"],
            "baseline_bookkeeping_only": diff["bookkeeping"],
            "experiment_fragment_own_block": diff["experiment_fragment_own_block"],
            "anything_else": diff["other"],
            "preparation_source_receipts": "the parent's list plus one appended entry: " + CENTROID_RECEIPT_RELPATH,
            "perception_spec_equal_except_facet_source": True,
            "note": (
                "computed by flattening both composed configs (core.config.compose) and listing every "
                "path whose value differs: the one pin, the baseline's per-flight bookkeeping (this cell's "
                "FIT identities and cap, the dropped prepared_phase_supply, the appended receipt, "
                "what_this_is) and the experiment fragment's own block (population, budgets, purpose, "
                "readiness, the Stage-3 label -- the cell's registration, never a knowledge key; an "
                "experiment key overlapping a baseline key is refused). The unit test " + CONFIG_TEST + " re-proves it"
            ),
        },
        "budget_arithmetic": {
            "contacts_per_row_program_ceiling": 11,
            "derivation": [
                f"generation_calls_cap = {rows} rows x 11 contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)) = {caps['generation_calls_cap']}",
                f"fit_endpoint_calls_cap = 4 x {caps['generation_calls_cap']} = {caps['fit_endpoint_calls_cap']}, the PLAN family's own ratio",
                f"native_task_contract_calls_cap = {rows} x 6 = {caps['native_task_contract_calls_cap']}, the family's own per-row figure",
                f"repeated_speech_audio_seconds_cap = ceil({roster['audio_seconds_total']} roster seconds x 11) = {caps['repeated_speech_audio_seconds_cap']}",
                f"gpu_hours_fit_inclusive = {caps['gpu_hours_fit_inclusive']}, a ceiling: the sealed PLAN arm's own 3.6819 h per 5,425 contacts puts the whole {caps['generation_calls_cap']}-contact ceiling at about {caps['generation_calls_cap'] * 3.6819 / 5425:.2f} h and the expected {document['generation_budget']['target']} contacts at about {document['generation_budget']['target'] * 3.6819 / 5425:.2f} h (CONV realized 0.12 h for 70 rows)",
                f"official_complete_scoring_jobs = 1, one job over the complete {rows}-row manifest through core.scoring_batch, never sharded",
            ],
            "expected_contacts": document["generation_budget"]["target"],
            "family_budget": caps,
            "run_cumulative": "every cap binds across ALL attempts of this run id, so the one permitted recovery re-registration spends from the same ceiling",
        },
        "authority_relpaths": [
            DIAGNOSTIC, DIAGNOSTIC_RECIPE, CONV_PACKAGE + "/README.md", CONV_READ, INSTRUMENT,
            BAD_CASE_BANK_DOC, WITHIN_FLIGHT_NULL, OWNER_DECISIONS,
        ],
        "committed_artifacts": {
            "centroid_key_file": mine_p["facet_source"],
            "centroid_key_receipt": my_receipts[-1],
            "note": (
                "The key file is pinned where the loader verifies it -- facet_source.sha256 in the "
                "baseline -- and its receipt in preparation_source_receipts, which "
                "core.preparation.verify_source_receipts checks at prepare time. It is deliberately "
                "NOT a readiness 'preparation' requirement: core.flight.repin._set_preparation_requirement "
                "rewrites EVERY such entry to the freshly minted first-phase supply pin at the flip. "
                "This cell's requirements list is empty and the flip appends exactly one."
            ),
            "prepared_phase_supply": (
                "NONE COMMITTED, by design: the flip mints this cell's own under its own run id "
                "(item E16) and --allow-output-change must never be passed. This cell has no earlier "
                "supply to compare against; a CHANGED output on a later re-pin means the knowledge "
                "channel moved -- stop and report."
            ),
        },
        "prohibitions": [
            "No pooled, roster-level, effectiveness, superiority or generalisation claim from this cell, ever -- its population was selected with gold.",
            "No admission entry and no admission mode: the cell claims nothing and asks for nothing.",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed comparator.",
            "No second factor: no k, tau, fuse_coverage, rank-weight, store, release or snapshot change; no store rebuild or release; no re-pin of the 211 committed configs.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cell is flipped.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": f"slurp-stage3-{tag}-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            f"Of the {rows} TRAIN Fold A rows whose own gold intent's boundary entry the centroid key "
            "newly delivers, how many move from a WRONG intent to the GOLD intent? That proportion is "
            "P(correct | newly delivered) -- the conversion from delivery to correctness, the one "
            "quantity the boundary-key diagnostic could not measure."
        ),
        "one_factor": (
            "ONE PIN. The locked PLAN baseline's intent-boundary Perception facet_source moves from the "
            "written-key file to the centroid-key file; k 8, fuse_coverage 8-1-8, rank weights, tau, "
            "store snapshot/release, delivered bodies, every other store, the model fragment, geometry, "
            "session, program, role graph, templates, normaliser and scorers are byte-identical. The "
            "composed-config diff is recorded in registered-facts-v1.json and re-proven by the unit test."
        ),
        "unchanged": (
            "everything but that pin and per-flight bookkeeping: the model fragment and serving geometry "
            f"(np4 x 24,576), the session {SESSION}, the phase program and its 11-contact ceiling, all "
            "three knowledge stores and their release/snapshot pins, the exemplar k of 20, the role graph, "
            "the response formats, the instruction templates, the deliver normaliser and the scorers"
        ),
        "comparator": facts["comparator"],
        "cells": {
            "probe": {
                "cell": cell["cell_id"], "experiment": experiment, "run_id": run_id,
                "attempt_id": cell["attempt_id"], "fit_run_id": fit_run, "fit_attempt_id": fit["attempt_id"],
                "composed_config_hash": composed.config_hash, "protocol_hash": phash,
                "split_identity_hash": split, "rows": rows,
                "boundary_facet_source_sha256": mine_p["facet_source"]["sha256"],
                "boundary_k": mine_p["k"], "boundary_rank_weights": mine_p["rank_weights"],
            }
        },
        "decision_rule_fixed_here": (
            f"There is no verdict and no admission. The deliverable is a NUMBER: m, the count of the {rows} "
            f"rows whose intent verdict moves from wrong to gold, reported as m / {rows} with a binomial CI95 "
            "(Wilson score interval, the exact Clopper-Pearson interval reported beside it), plus the "
            "reverse count -- zero by construction on this population, because every row is already "
            "intent-wrong in the comparator, reported as a LIMIT of the cell rather than as a result -- "
            "and the FOUR-WAY transition split: wrong to gold, gold to wrong, the same wrong intent, a "
            "different wrong intent, with the stay-wrong rows further split into byte-identical answer, "
            "same wrong intent in different bytes and different wrong intent. THE DELIVERY GATE: the read "
            f"refuses to produce a conversion number unless the flown Perception consumption delivered the "
            f"row's own gold intent boundary value id on ALL {rows} rows, as the offline derivation predicts; "
            "anything less is an engineering defect, not a measurement."
        ),
        "what_the_number_does": (
            f"It fixes the expectation a later 1,080-row construction cell would declare: expected_effect_pp = "
            f"m x {HEADROOM_INTENT:.6f} pp intent accuracy (primary, owner decision 133) and m x {HEADROOM_SLU:.6f} pp "
            f"SLU-F1 (the guard); such a cell clears the 2.5 pp intent bar at n = 1,080 only if m >= {rows_needed_intent}. "
            "That is the decision this probe informs, and the probe itself decides nothing. Decision 145 also "
            "records that the key competes with the agreement term for the same INTENT-UNCOVERED rows; whether "
            "they add is decision 138's composed round, not this cell."
        ),
        "why_intent_and_not_slu_f1": WHY_INTENT_NOT_SLU,
        "gold_selection": GOLD_SELECTION,
        "no_pooled_claim": NO_POOLED_CLAIM,
        "why_no_in_chain_replicate": (
            "Rule 4 of the measurement instrument refuses a cross-flight CONTRAST with no in-chain replicate. "
            "This cell computes no cross-flight contrast: its measurement_design is form-proof, it claims no "
            "benefit, and the quantity it reports is a rate within its own flight, not a delta between flights. "
            f"The comparator's contribution is a per-row verdict that is CONSTANT on this population -- wrong on all "
            f"{rows} rows -- so there is no between-flight offset for a replicate to null."
        ),
        "development_numbers_only": "Every number this cell will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "model_free_proofs_landed_before_contact": {
            "roster_derivation": facts["roster"]["derivation"],
            "delivery_proofs": {k: v for k, v in facts["delivery_proofs"].items() if k != "derivation"},
            "centroid_key_file": facts["treatment_key_file"]["facets"],
            "centroid_key_receipt": facts["treatment_key_file"]["receipt"],
            "composed_config_diff": facts["composed_config_diff_against_the_locked_plan_cell"],
        },
        "authority": (
            f"owner decision 145 ({OWNER_DECISIONS}), on the finding of {DIAGNOSTIC}; the CONV precedent "
            f"{CONV_PACKAGE} and its read {CONV_READ}; the measurement instrument {INSTRUMENT} (rule 5, the "
            f"form-proof row); the within-flight null {WITHIN_FLIGHT_NULL}; the class headroom of {BAD_CASE_BANK_DOC}; "
            "owner decisions 28 and 86 (development numbers), 101 (the Stage-3 algorithm label), 133 (intent primary) and 134 (probe before arm)"
        ),
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    def plan_document(kind: str) -> dict:
        generation = kind == "generation"
        return {
            "schema": f"saea-registered-{kind}-plan-v1",
            "plan_kind": kind,
            "cell": cell["cell_id"],
            "experiment": experiment,
            "composed_config_hash": composed.config_hash,
            "execution_plan": {
                "attempt_id": cell["attempt_id"] if generation else fit["attempt_id"],
                "carrier_lock_key": composed.values["carrier_lock_key"],
                "execution_profile": document["execution_profile"],
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
                "planned_model_calls": caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"],
                "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
                "protocol_hash": phash,
                "run_id": run_id if generation else fit_run,
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": split,
                "split_role": "discovery",
                "study": "speech-aware-evidence-acquisition",
            },
            "execution_route": (
                f"Shared core.flight.cli campaign over the committed campaign plan configs/campaign/{experiment}.json, "
                "a single-cell chain; the campaign acquires its own GenerationLease against the resident session and "
                "schedules one official score over the complete manifest at finalize."
                if generation
                else "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
            ),
            "expected_session_id": SESSION,
            "family_budget": caps,
            "one_factor": protocol["one_factor"],
            "preparation_base_commit": args.study_commit,
            "prepared_phase_supply": {
                "note": facts["committed_artifacts"]["prepared_phase_supply"],
                "relpath": f"prepared/{run_id}/phase-supply-v1.json",
                "sha256": "MINTED_AT_THE_FLIP",
            },
            "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "purpose": (
                f"{run_id}: cell KPROBE, the centroid-key conversion probe. " + protocol["decision_rule_fixed_here"]
                if generation
                else f"{run_id}: cell KPROBE. It measures request envelopes only and reads nothing."
            ),
            "quality_read_gate": (
                "No read before the complete sealed manifest, the exact ordered outputs, the native phase summary "
                "and the single successful complete official TRAIN score all exist for this cell, and before the "
                f"flown delivery check agrees with the offline derivation on all {rows} rows. A partial manifest is "
                "never scored and never read."
            ),
            "registered_at_utc": args.registered_at,
            "source_tree": protocol["source_tree"],
            "status": protocol["status"],
            "unused_budget_is_not_attempt_authority": True,
        }

    gen_sha = wjson(package + "/generation-plan-registered-v1.json", plan_document("generation"))
    fit_sha = wjson(package + "/fit-plan-registered-v1.json", plan_document("fit"))

    recipe = {
        "schema": "saea-slurp-conditional-rate-recipe-v1",
        "recipe_id": f"slurp-stage3-{tag}-conditional-rate-v1",
        "title": "Cell KPROBE -- P(correct | newly delivered), the centroid key's conversion from delivery to correctness, measured",
        "registered_at_utc": args.registered_at,
        "arms": {
            "probe": {"run_id": run_id, "attempt_id": cell["attempt_id"], "fit_run_id": fit_run,
                      "outputs_sha256": "PENDING_SEAL", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL"},
            "comparator": facts["comparator"],
        },
        "roster": {"relpath": derivation_relpath, "sha256": sha_file(derivation_relpath), "count": rows, "id_list_sha256": roster["id_list_sha256"]},
        "treatment_key_file": facts["treatment_key_file"]["facets"],
        "steps": [
            f"1. Refuse unless the sealed manifest is COMPLETE at {rows} rows and its ids equal the committed roster's ids exactly (compare the id-list sha256, not a count), and the manifest's config hash is this cell's (the centroid file is what flew).",
            f"2. THE DELIVERY GATE: refuse unless the flown Perception consumption delivered the row's own gold intent boundary value id on all {rows} rows. The offline derivation predicts {rows}; anything less is an engineering defect and closes the read with no conversion number (a refusal receipt is written instead).",
            "3. Score once over the complete manifest with the dataset's standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded) and take ONE field per row: scenario_action_exact.",
            "4. Establish the comparator's per-row intent verdict two ways and refuse on any disagreement: from the bad-case bank (plan_class INTENT-UNCOVERED or INTENT-COVERED, both intent-wrong, digest pinned above) and from the sealed PLAN arm's own official score for the same sample ids.",
            "5. m = the count of rows whose probe verdict is exact and whose comparator verdict is not. r = the reverse count, which must be 0 because every comparator verdict on this roster is wrong; a non-zero r means the roster or the comparator was misread and closes the read.",
            f"6. Report P(correct | newly delivered) = m / {rows} with a Wilson score CI95 and the exact Clopper-Pearson CI95 beside it. No bootstrap: the quantity is a single binomial proportion.",
            "7. Report the FOUR-WAY transition split (wrong to gold; gold to wrong; the same wrong intent; a different wrong intent) and the stay-wrong split (byte-identical answer; same wrong intent in different bytes; different wrong intent), with the within-pair byte identity on rows whose intent did not change as context beside the ROLL-AA null, never against it.",
            f"8. State the re-declaration arithmetic and do not apply it: a later construction cell's expected_effect_pp = m x {HEADROOM_INTENT:.6f} pp intent accuracy (owner decision 133) and m x {HEADROOM_SLU:.6f} pp SLU-F1 for the guard; state whether m >= {rows_needed_intent} (the 2.5 pp intent bar at n = 1,080); and state in the same paragraph that this is a CONDITIONAL rate on a gold-selected roster and not a pooled effect.",
        ],
        "metrics": ["scenario_action_exact"],
        "interval": {"kind": "binomial", "primary": "Wilson score CI95", "reported_beside": "exact Clopper-Pearson CI95",
                     "no_bootstrap_because": "the estimand is one binomial proportion over independent rows, not a paired difference of pooled metrics"},
        "output": {"analysis_root": f"analysis/SAEA-SLURP-STAGE3-{tag.upper()}-CONDITIONAL-RATE-V1"},
        "read_driver": READ_DRIVER,
        "reported_beside_every_number": [
            f"the flown delivery check against the offline derivation's {rows} (the gate)",
            "the reverse count and the statement that it is zero by construction",
            "the four-way transition split and the stay-wrong split",
            f"the re-declaration arithmetic and the {rows_needed_intent}-row threshold, stated and not applied",
            "GOLD-SELECTED ROSTER: conditional rate only, no pooled or roster-level claim, and this cell cannot see harm on already-correct rows or on rows that lose their gold entry",
        ],
        "boundary": (
            "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a "
            "generalisation claim, and it admits nothing by itself. No utterance text, transcript, gold label string, "
            "intent name as content or model output is printed or persisted: ids, counts, rates and hashes only."
        ),
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    draft = {
        "_draft_note": (
            "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with "
            "scripts/flights/kprobe/kprobe_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, "
            "re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its "
            "status is not 'decided' (core.flight.campaign.declared_readiness refuses it)."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": decision_id,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": [run_id, fit_run],
        "cell_kind": (
            "Stage-3 conditional-rate probe (label none: no rollout, no scoring, no credit, no update). One arm, "
            f"{rows} rows, no smoke and no comparator flight. It measures the conversion from delivery to correctness "
            "of the centroid boundary key the 2026-09-27 diagnostic put forward."
        ),
        "decision": (
            f"Fly cell KPROBE: the {rows}-row centroid-key conversion probe (owner decision 145). It runs the locked PLAN "
            "plan with exactly one pin moved -- the intent-boundary Perception facet_source, from the written-key file "
            "to the centroid-key file -- on exactly the TRAIN Fold A rows whose gold intent boundary entry is NEWLY "
            "delivered under that key, and on nothing else. The comparator needs no contacts: the sealed PLAN arm on "
            f"Fold A already holds these rows' answers. The read is P(correct given newly delivered) -- m of {rows} -- as a "
            "Wilson interval with an exact Clopper-Pearson beside it, on INTENT correctness per row, gated on delivery "
            "having held on every row."
        ),
        "authorization_basis": (
            "Owner decision 145 (register a CONV-style probe for the centroid boundary key; the probe pins its own derived "
            "baseline and does NOT re-pin the 211 committed configs) and owner decision 133 (a mechanism acting on intent "
            "is reported on intent-recognition accuracy, with official SLU-F1 kept as the non-inferiority guard). Standing: "
            "decision 134 (probe before arm), 115 closure rule, 116 (the complete agentic system is the unit), 101 (every "
            "Stage-3 cell carries its algorithm label; this cell's label is honestly none), 77 (flights only through the "
            f"batch driver scheduled task), and the binding instrument note {INSTRUMENT}. The population was selected "
            "using gold OFFLINE, which is legitimate for a conditional estimate on a TRAIN roster and is why the cell may "
            "never support a pooled claim."
        ),
        "antecedents": {
            "owner_decision_145": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "diagnostic_note": {"path": DIAGNOSTIC, "sha256": sha_file(DIAGNOSTIC)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "roster_derivation": {"path": derivation_relpath, "sha256": sha_file(derivation_relpath)},
            "centroid_key_receipt_copy": {"path": package + "/centroid-keys-receipt-v1.json", "sha256": receipt_copy_sha},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "read_driver": {"path": READ_DRIVER, "sha256": sha_file(READ_DRIVER) if Path(READ_DRIVER).is_file() else None},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "conv_precedent_read": {"path": CONV_READ, "sha256": sha_file(CONV_READ)},
            "base_cell": f"the LOCKED default plan, cell PLAN ({COMPARATOR_RUN}, v2.0 lock 2026-09-22): KPROBE is that fragment with one pin moved",
            "clause_comparator": f"the sealed PLAN arm {COMPARATOR_RUN} on the same rows, never re-flown; no admission read",
            "registration_base_commit": args.study_commit,
        },
        "budget": {
            **{k: caps[k] for k in sorted(caps)},
            "paid_api_calls": 0,
            "expected_contacts": document["generation_budget"]["target"],
            "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; 1.0 GPU-h is a ceiling (CONV realized 0.12 h for 70 rows)",
            "plan_budget_is_run_cumulative": True,
        },
        "claim_boundary": (
            "No superiority, generalisation, component-causal, bar, admission, held-out, confirmatory or paper-scale "
            "claim of any kind. A conditional rate on a gold-selected roster measures one factor of a later cell's "
            "expectation; it is never a pooled or roster-level number."
        ),
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cell is flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any k, tau, fuse-policy, rank-weight, store, release, snapshot, roster, prompt or geometry change beyond the one registered pin",
            "re-pinning the 211 committed configs to the centroid file (decision 145: that waits on m)",
            "a pooled, roster-level or admission read from this cell",
        ],
        "population": {
            "count": rows, "split_identity_hash": split, "split_role": "discovery",
            "partition": f"the {rows} intent-wrong TRAIN Fold A rows whose gold boundary entry the centroid key newly delivers ({derivation_relpath})",
            "fold_b_contact_authorized": False, "test_contact_authorized": False,
        },
        "prepared_phase_supply": {"note": "minted by scripts/flights/repin_cell.py at the flip (this cell's own, item E16); not pinned by this receipt"},
        "registered_hashes": {
            "note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip.",
            "composed_config": composed.config_hash, "protocol": phash,
        },
        "service": {"expected_session_id": SESSION, "model_fragment": cell["model_fragment"], "slots": 4, "slot_tokens": 24576,
                    "decoder_only": True, "mmproj": "absent", "no_child_start_stop": True,
                    "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    by_class = pc["population_by_plan_class"]
    lost_prose = ", ".join(f"{v} {k}" for k, v in sorted(pc["newly_lost_by_class_all_rows"].items()))
    readme = f"""# Cell KPROBE: the centroid key's conversion from delivery to correctness

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decision 145);
the cell is **held**. Nothing here authorises a flight, a flip or an admission entry.

**The finding this probe follows.** [`{DIAGNOSTIC}`](../../results/{Path(DIAGNOSTIC).name}) found the
boundary channel's written one-line descriptions to be its weak link: a key built as the intent's mean
construction-TRAIN utterance vector -- the same 2048-d space as the flown keys, zero encoder contacts --
puts the gold intent inside the delivered eight on **71.2 / 64.7 / 66.8 %** of the intent-wrong rows
(Fold A / ROLL-1 / DEV-2000, held-out pools) against **45.0 / 44.6 / 35.8 %** for the written key, at zero
token cost, because the delivered body is unchanged. That is DELIVERY. Whether the Solver then answers
correctly with the entry in front of it is the missing quantity, and this cell measures it exactly as
cell CONV measured the agreement term's ([`{CONV_PACKAGE}`](../{Path(CONV_PACKAGE).name}/README.md), read
[`{CONV_READ}`](../../results/{Path(CONV_READ).name}): m = 32 of 70).

**The treatment key file.** `{CENTROID_FACETS_RELPATH}` (sha256 `{facets_sha}`, 60 rows), cut by
`{BUILDER}` from the pinned pool key vectors (`vectors/slurp-kus3/facet-vectors.jsonl`) and the
R01-excluded pool snapshot (`size-pool-annotated-exemplars-minus-r01`, 8,554 utterances), so that ONE file is
held out on Fold A, ROLL-1 and DEV-2000 alike. The arithmetic is the diagnostic's own (`unit_rows`, imported
byte-unchanged): unit-normalise each member, mean, unit-normalise; the label is each pool value's frozen
build-time `task_target`, a store property. `{receipt['measured']['written_fallback_ids'][0]}` has no
utterance in that pool and keeps its written key byte for byte. A centroid has no text source, so the file
carries a new receipt kind, `{receipt['schema']}` / `{receipt['kind']}` (sha256 `{receipt_sha}`; repository copy
`centroid-keys-receipt-v1.json`), which pins per facet the construction, the member count, the member-id
digest and the vector digest. Only this cell's derived baseline pins the file; **the 211 committed configs
are not re-pinned** (decision 145).

**Three proofs before an id was taken** ([`roster-derivation-v1.json`](roster-derivation-v1.json), by
`{ROSTER_SCRIPT}`): (A) the diagnostic's own arithmetic, imported byte-unchanged, reproduces every
`written` / `centroid` cell of its committed note on all three rosters and the written-key recall equals every
sealed delivered set (0 differences); (B) the pinned FILE, read through `rails.phase_supply.load_sealed_vectors`
and run through `rails.kb_policy.multidim_segment_recall`, equals the diagnostic's R01-excluded centroid
(max abs diff {pb['max_abs_diff_to_diagnostic_r01_excluded_centroid']:.1e}) and reproduces the note's
ROLL-1 centroid cells exactly ({pb['arms']['roll1']['cells']['deliv_wrong']} % wrong-row delivery); on Fold A the
file delivers gold on **{fold_a_wrong['delivered_centroid']} of {fold_a_wrong['rows']}** intent-wrong rows
({fold_a_cells['deliv_wrong']} %) against {fold_a_wrong['delivered_written']} ({pa['note_cells_compared']['train-fold-a-plan']['written']['deliv_wrong']} %) for the written key;
(C) the production constructor (`provider.candidates` + `provider.fuse` at the flown k 8 / 8-1-8) reproduces the
sealed delivered set on 1,080 / 1,080 rows under the written key and derives the same population under the
centroid pin as the recall does.

**The roster.** {rows} ids, id-list sha256 `{roster['id_list_sha256']}`, split identity
`{split}`: the intent-wrong Fold A rows whose gold entry the centroid key newly delivers --
{by_class['INTENT-UNCOVERED']['newly_delivered']} of the bank's `INTENT-UNCOVERED` rows and
{by_class['INTENT-COVERED']['newly_delivered']} of its `INTENT-COVERED` rows, both intent-wrong in the sealed comparator. Net
delivery on the {fold_a_wrong['rows']} intent-wrong rows is +{fold_a_wrong['delivered_centroid'] - fold_a_wrong['delivered_written']}
= {fold_a_wrong['newly_delivered']} newly delivered - {fold_a_wrong['newly_lost']} newly lost, the note's 191 x (0.712 - 0.450) = 50. **Selected using gold, offline** -- legitimate for a
*conditional* estimate on a TRAIN roster and for nothing else. **No pooled or roster-level claim may ever be
made from this cell.** It also cannot see harm: rows the comparator already gets right, and rows that LOSE
their gold entry under the centroid key ({lost_prose} over all 1,080 rows), are
outside this roster and remain a construction cell's question.

**One pin, proven.** The derived baseline is `{parent_cell['baseline_fragment']}` with
`knowledge_stores.intent-boundaries.phase_supply.perception.facet_source` moved to the centroid file; the
composed-config diff against the locked PLAN cell (`registered-facts-v1.json`,
`composed_config_diff_against_the_locked_plan_cell`) is that pin plus bookkeeping only: this cell's own FIT
identities and cap, no committed `prepared_phase_supply`, the receipt appended to
`preparation_source_receipts`, and `what_this_is`. `k` 8, `fuse_coverage` 8-1-8, the rank weights, the store
snapshot and release, every other store, the model fragment, geometry, session, program, templates,
normaliser and scorers are byte-identical. `{CONFIG_TEST}` re-proves it.

**Why intent, not SLU-F1.** {WHY_INTENT_NOT_SLU}

**The deliverable.** `P(correct | newly delivered)` = m / {rows} with a Wilson CI95 and the exact
Clopper-Pearson beside it; the reverse count (zero by construction, a limit not a result); the four-way
transition split (wrong to gold, gold to wrong, same wrong intent, different wrong intent) and the stay-wrong
split; and **the delivery gate**: the read refuses to produce a number unless the gold entry was delivered on
all {rows} rows. Re-declaration rule, stated and not applied: a later 1,080-row construction cell declares
m x {HEADROOM_INTENT:.6f} pp intent accuracy (owner decision 133; m x {HEADROOM_SLU:.6f} pp SLU-F1 for the guard),
clearing the 2.5 pp intent bar only if **m >= {rows_needed_intent}**.

**`stage3_measurement`.** {rows} rows is under the instrument's `MIN_BENEFIT_ROWS`, so the design is
`form-proof`, `claims_benefit` **false**, `expected_effect_pp` **0.0**; the note states the conditional-rate
purpose and the re-declaration rule. **No `admission` mode is declared.**

**`stage3_algorithm`.** `none`: no rollout, no per-sample scoring, no credit assignment, no update
operator, no evolving store; a single key file is not a policy search.

| file | what it holds |
| --- | --- |
| `../{Path(prereg).name}` | the preregistration proper, including the `stage3_measurement` fence |
| `roster-derivation-v1.json` | the {rows} ids and the three proofs |
| `centroid-keys-receipt-v1.json` | the repository copy of the key file's receipt (new kind) |
| `registered-facts-v1.json` | every model-free fact, the one-pin diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the cell's two plans |
| `analysis-recipe-v1.json` | how the conditional rate is read offline, step by step (`{READ_DRIVER}`) |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/kprobe/kprobe_mint_receipt.py` |

**Budgets, as arithmetic (CONV's).** {caps['generation_calls_cap']} generation contacts ({rows} x 11,
run-cumulative), {caps['fit_endpoint_calls_cap']} FIT endpoints (4 x), {caps['native_task_contract_calls_cap']} native
task-contract calls ({rows} x 6), {caps['repeated_speech_audio_seconds_cap']} repeated speech seconds
(ceil({roster['audio_seconds_total']} x 11)), {caps['gpu_hours_fit_inclusive']} GPU hour, one official complete score.
Expected spend: about {document['generation_budget']['target']} contacts and about
{document['generation_budget']['target'] * 3.6819 / 5425:.2f} GPU hours at the sealed arm's own realized rate.

**No committed `prepared_phase_supply`, and an empty requirements list.** The flip mints this cell's own
first-phase supply under its own run id (item E16); `core.flight.repin._set_preparation_requirement` rewrites
every `kind == "preparation"` entry, so a second requirement would be silently clobbered, and
`--allow-output-change` must never be passed. The key file stays pinned where the loader verifies it:
`facet_source.sha256` in the baseline, plus its receipt in `preparation_source_receipts`.

**Mint, flip, queue (CONV's sequence with names changed).** Root countersigns the three DRAFT exposure rows
(`{run_id}`, `{fit_run}`, `{CENTROID_ARTIFACT}`), mints
`{decision_relpath}` from the draft with `scripts/flights/kprobe/kprobe_mint_receipt.py`
(decision id `{decision_id}`, the two eligible run ids and this cell's caps), flips with
`scripts/flights/kprobe/kprobe_flip.sh` (the generic re-pin loop over `kprobe_repin_arm.sh`; one cell, no
smoke -- {rows} rows is itself a form proof and the treatment form is the locked plan's), then queues
`scripts/flights/kprobe/batch_chain_kprobe.sh` behind whatever occupies the np4 session (decision 77).
After the seal: `python {READ_DRIVER} --data-root "$SPEECHRL_DATA_DIR"`.

**Not authorised by this package.** No flight before the receipt is minted and the cell is flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no store
rebuild or release; no re-pin of the committed configs; no pooled claim; no admission entry.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Cell KPROBE: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the locked
PLAN baseline's own fragments by script (decision 58) with one pin moved, under owner decision 145.
Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | Of the {rows} TRAIN Fold A rows whose own gold intent's boundary entry the centroid key newly delivers, how many move from a wrong intent to the gold intent? |
| treatment | the locked PLAN plan with ONE pin moved: the intent-boundary Perception `facet_source` is `{CENTROID_FACETS_RELPATH}` (sha256 `{facets_sha}`) instead of the written-key file; `k` 8, `fuse_coverage` m 8 / c 1 / top_l 8, `w_cos` 1.0 / `w_prior` 0.0 / `w_agree` 0.0, `tau` 0.0, the same store snapshot and release |
| changed | that pin, the population ({rows} derived ids instead of 1,080) and the ceilings rescaled to it. Nothing else; the composed diff is in `registered-facts-v1.json`. |
| comparator | `{COMPARATOR_RUN}`, sealed, already flown, never re-flown, not in this campaign. Intent-**wrong** on all {rows} rows. |
| in-chain replicate | none, and none is owed: the design is `form-proof`, no cross-flight contrast is computed, and the comparator's per-row verdict is constant on this population |
| runs | `{run_id}` / `{fit_run}` |
| rows | {rows} |
| composed config hash | `{composed.config_hash}` |
| protocol hash | `{phash}` |
| split identity | `{split}` |
| id-list sha256 | `{roster['id_list_sha256']}` |
| key file | `{CENTROID_FACETS_RELPATH}` sha256 `{facets_sha}`; receipt `{CENTROID_RECEIPT_RELPATH}` sha256 `{receipt_sha}` |
| authority | owner decision 145 ({OWNER_DECISIONS}); {DIAGNOSTIC}; the CONV precedent {CONV_PACKAGE} and {CONV_READ}; {INSTRUMENT} (rule 5); {WITHIN_FLIGHT_NULL}; {BAD_CASE_BANK_DOC}; owner decisions 28, 86, 101, 133 and 134 |

## The read rule (fixed here)

There is no verdict and no admission. **The delivery gate comes first:** the read refuses to produce a
conversion number unless the flown Perception consumption delivered the row's own gold intent boundary value
id on all {rows} rows, as the offline derivation predicts; anything less is an engineering defect. Then m = the
count of the {rows} rows whose official `scenario_action_exact` is true and whose comparator verdict is not. The
deliverable is `P(correct | newly delivered)` = m / {rows} with a Wilson score CI95 and the exact Clopper-Pearson
interval beside it, plus the reverse count -- **zero by construction**, because every comparator verdict on this
roster is wrong; a non-zero reverse count means the roster or the comparator was misread and closes the read.
Reported beside it: the four-way transition split (wrong to gold; gold to wrong; the same wrong intent; a
different wrong intent) and the stay-wrong split (byte-identical answer; same wrong intent in different bytes;
different wrong intent).

Re-declaration rule, stated and not applied: a later 1,080-row construction cell that flies this key declares
`expected_effect_pp` = m x {HEADROOM_INTENT:.6f} pp intent accuracy (intent primary, owner decision 133; m x
{HEADROOM_SLU:.6f} pp SLU-F1 for the guard), and clears the 2.5 pp intent bar at n = 1,080 only if
**m >= {rows_needed_intent}**.

## The measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)}
```

`{rows}` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof by size:
`form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. **No `admission` mode is declared.**

## What the roster is, and what selecting it with gold costs

{GOLD_SELECTION}

{NO_POOLED_CLAIM}

The roster is derived from the pinned key FILE through the production path, after three proofs
(`roster-derivation-v1.json`, by `{ROSTER_SCRIPT}`): the diagnostic's own arithmetic reproduces its committed
note (0 differences); the file reproduces the diagnostic's R01-excluded centroid through the production recall
and the note's ROLL-1 cells exactly; the production constructor reproduces the sealed delivered set under the
written key on 1,080 / 1,080 rows and derives the same population under the centroid pin as the recall.

## Why intent, not SLU-F1

{WHY_INTENT_NOT_SLU}

## Budgets and failure rule

{caps['generation_calls_cap']} generation contacts (run-cumulative; {rows} x the program's own 11-contact ceiling),
{caps['fit_endpoint_calls_cap']} FIT endpoints, {caps['repeated_speech_audio_seconds_cap']} repeated speech seconds,
{caps['gpu_hours_fit_inclusive']} GPU hour, one official complete score. Expected spend about
{document['generation_budget']['target']} contacts and about {document['generation_budget']['target'] * 3.6819 / 5425:.2f} GPU hours at the
sealed arm's own realized rate. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery
re-registration; a second failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No pooled, roster-level, effectiveness, superiority or generalisation claim from this cell, ever. No admission
entry and no admission mode. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read.
No re-flying of the sealed comparator. No second factor and no knob change. No store rebuild or release; no re-pin
of the 211 committed configs. No flight before root mints the decision receipt and the cell is flipped, and
`--allow-output-change` is never passed.
"""
    prereg_sha = wr(prereg, prereg_text)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(
            args, rows=rows, run_id=run_id, fit_run=fit_run, cell=cell, fit=fit, caps=caps,
            composed_hash=composed.config_hash, phash=phash, split=split, roster=roster,
            plan_shas={"generation": gen_sha, "fit": fit_sha}, expected=document["generation_budget"]["target"],
            rows_needed=rows_needed_intent, package=package, package_name=package_name, decision_id=decision_id,
            decision_relpath=decision_relpath, facets_sha=facets_sha, receipt_sha=receipt_sha,
            receipt=receipt, fold_a_wrong=fold_a_wrong, derivation_relpath=derivation_relpath,
            parent_split=pc["comparator"]["split_identity_hash"],
        )

    print(json.dumps({
        "package": package,
        "written": {
            package + "/README.md": readme_sha, package + "/analysis-recipe-v1.json": recipe_sha,
            package + "/fit-plan-registered-v1.json": fit_sha, package + "/generation-plan-registered-v1.json": gen_sha,
            package + "/protocol-registered-v1.json": protocol_sha, package + "/registered-facts-v1.json": facts_sha,
            package + "/root-admission-draft-v1.json": draft_sha, package + "/centroid-keys-receipt-v1.json": receipt_copy_sha,
            prereg: prereg_sha,
        },
        "exposure_ledger": ledger_state,
        "composed_config_diff": diff,
        "identity": {
            "run_id": run_id, "fit_run_id": fit_run, "attempt_id": cell["attempt_id"], "fit_attempt_id": fit["attempt_id"],
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": phash, "split_identity_hash": split, "rows": rows,
            "facets_sha256": facets_sha, "receipt_sha256": receipt_sha,
            "rows_needed_to_clear_the_intent_bar": rows_needed_intent,
        },
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native "
    "tool authority on any role; prompt bytes the locked PLAN arm's (the delivered boundary body is "
    "unchanged; only the retrieval key file differs)"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct "
    "anchor, cells B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, "
    "PLANr, ROLL-2 and CONV; this cell adds no new row to the fold, re-flies a strict subset of it and "
    "opens no split. Prior exposure is inherited in full."
)


def append_ledger(args, *, rows, run_id, fit_run, cell, fit, caps, composed_hash, phash, split, roster,
                  plan_shas, expected, rows_needed, package, package_name, decision_id, decision_relpath,
                  facets_sha, receipt_sha, receipt, fold_a_wrong, derivation_relpath, parent_split) -> str:
    """Append the two DRAFT flight rows and the one model-free key-file row.
    Idempotent: refuses to append a second time rather than duplicating a run id.
    No cell may contain a literal '|'."""

    text = rd(LEDGER)

    def notes(kind: str) -> str:
        attempt = cell["attempt_id"] if kind == "generation" else fit["attempt_id"]
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study "
            f"commit {args.study_commit} by the KPROBE registration agent (worktree {args.worktree}, branch "
            f"{args.branch}). This registration performs no contact and authorises none. Plan SHA256 "
            f"{plan_shas[kind]}; attempt {attempt}. Protocol hash {phash}; composed config {composed_hash}; "
            f"expected session {SESSION} (attach only, never spawn or stop). READINESS HELD: root mints "
            f"{decision_relpath} (decision id {decision_id}) from the package's root-admission-draft-v1.json with "
            f"the two eligible run ids {run_id}, {fit_run} and this cell's caps, then re-pins with "
            f"scripts/flights/repin_cell.py --set-ready, which mints this cell's OWN first-phase supply under its "
            f"own run id (item E16); the cell carries NO committed prepared_phase_supply and an EMPTY readiness "
            f"requirements list, and --allow-output-change must never be passed. Every hash in this row moves at "
            f"the flip and the re-pin tool rewrites it. ONE PIN (owner decision 145): the locked PLAN baseline "
            f"with the intent-boundary Perception facet_source moved to {CENTROID_FACETS_RELPATH} (SHA256 "
            f"{facets_sha}; receipt SHA256 {receipt_sha}, a new receipt kind because a centroid has no text "
            f"source); k 8, fuse 8-1-8, weights, stores and everything else byte-identical; the 211 committed "
            f"configs are NOT re-pinned. Measurement declaration (scripts/checks/stage3_effect_floor_check.py): "
            f"measurement_design form-proof, expected_effect_pp 0.0, claims_benefit false, rows {rows}, no "
            f"admission mode -- declared at the top level of {package}/registered-facts-v1.json and repeated in "
            f"the preregistration fence. THE ROSTER WAS SELECTED USING GOLD, OFFLINE (roster derivation "
            f"{derivation_relpath}, id-list sha256 {roster['id_list_sha256']}; three proofs with zero differences: "
            f"the diagnostic's arithmetic reproduces its note, the pinned file reproduces through the production "
            f"recall, the production constructor agrees): a CONDITIONAL rate on a TRAIN roster only, and NO pooled, "
            f"roster-level, effectiveness or generalisation claim may ever be made from this cell. It also cannot "
            f"see harm: every row is already intent-wrong in the sealed comparator, and the {fold_a_wrong['newly_lost']} "
            f"intent-wrong rows that lose their gold entry lie outside it. Ceiling {caps['generation_calls_cap']} = "
            f"{rows} rows x 11 contacts per row; expected about {expected} contacts and about "
            f"{expected * 3.6819 / 5425:.2f} GPU hours at the sealed PLAN arm's own realized rate -- a ceiling is a BOUND, "
            f"never a target, and budgets are run-cumulative across every attempt of a run id. Shared core.flight.cli "
            f"campaign over the committed single-cell campaign plan configs/campaign/{cell['cell_id']}.json; ONE "
            f"official complete score at finalize over the complete {rows}-row manifest, never sharded, and the read "
            f"takes one field per row (scenario_action_exact) AFTER the delivery gate (gold entry delivered on all "
            f"{rows} rows, else no number). The deliverable is P(correct given newly delivered) = m / {rows} with a "
            f"binomial CI95 and the four-way transition split; a later construction cell clears the 2.5 pp intent bar "
            f"at n = 1,080 only if m >= {rows_needed} (m x 0.092615 pp intent, owner decision 133). The comparator "
            f"{COMPARATOR_RUN} is sealed and never re-flown. Stop and preserve on the first failure; AT MOST ONE "
            f"root-diagnosed recovery re-registration. No paper-scale profile, no confirmatory split, no test-split "
            f"contact, no comparator flight and no admission entry from this cell."
        )

    def row(kind: str) -> str:
        generation = kind == "generation"
        cells = [
            "", args.registered_at, run_id if generation else fit_run, "bounded-discovery-probe",
            (
                f"Cell KPROBE, the centroid-key conversion probe (owner decision 145): the locked PLAN plan with ONE "
                f"pin moved (intent-boundary facet_source to the centroid key file), flown on the {rows} TRAIN Fold A "
                f"rows whose gold intent's boundary entry that key newly delivers, to measure P(correct given newly "
                f"delivered). Treatment only; the comparator is sealed."
                if generation
                else f"Cell KPROBE -- FIT spend identity, request envelopes only, no generation: the one-pin centroid-key "
                f"treatment on the same {rows} derived TRAIN Fold A rows."
            ),
            MODEL_TOOL, f"slurp TRAIN Fold A conversion subset {rows}", "discovery", split, "no",
            str(caps["generation_calls_cap"] if generation else caps["fit_endpoint_calls_cap"]),
            str(caps["repeated_speech_audio_seconds_cap"]), str(caps["gpu_hours_fit_inclusive"]), INHERITED,
            package + ("/generation-plan-registered-v1.json" if generation else "/fit-plan-registered-v1.json"),
            notes(kind), "",
        ]
        return " | ".join(cells).strip()

    key_row = " | ".join([
        "", args.registered_at[:10], CENTROID_ARTIFACT, "model-free-check",
        (
            "Build the intent-boundary CENTROID key file cell KPROBE pins: one unit-normalised mean "
            "construction-TRAIN utterance vector per released intent, arithmetic over the pinned pool key vectors "
            "and the R01-excluded pool snapshot's frozen task_target labels, at zero encoder contacts; the one intent "
            "with no pool member keeps its written key. Then the three-proof roster derivation over already-sealed "
            "vectors. Zero model, server, encoder, embedder, scorer, tokenizer, network, GPU and paid-API contacts."
        ),
        "no model or tool contact; local arithmetic over receipt-pinned files",
        "slurp TRAIN construction pool (R01-excluded), key side only; the derivation re-reads the sealed Fold A, ROLL-1 and DEV-2000-ADDED speech query vectors",
        "discovery", parent_split, "no", "0", "0", "0",
        "No new speech exposure: the builder reads no speech byte at all, and every vector the derivation read was already exposed by the cells that sealed it. Prior exposure inherited in full.",
        CENTROID_RECEIPT_RELPATH,
        (
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) {args.registered_at[:10]} at study "
            f"commit {args.study_commit}. Artifact {CENTROID_FACETS_RELPATH} SHA256 {facets_sha}; receipt SHA256 "
            f"{receipt_sha} (schema {receipt['schema']}, kind {receipt['kind']} -- a new receipt kind because a centroid "
            f"has no text source; repository copy {package}/centroid-keys-receipt-v1.json). Builder {BUILDER}; "
            f"derivation {ROSTER_SCRIPT} -> {derivation_relpath}. Measured: 60 facets, "
            f"{receipt['measured']['centroid_facets']} centroids over {receipt['measured']['members_total']} members, "
            f"{receipt['measured']['written_fallback_facets']} written fallback, key-to-key cosine mean "
            f"{receipt['measured']['key_to_key_cosine_mean']} / max {receipt['measured']['key_to_key_cosine_max']} (the note's "
            f"own R01-excluded figures). It constructs no ExecutionPlan, reserves no contact, releases or rebuilds no "
            f"store, re-pins no committed config and authorises nothing; it exists because a pre-computation is "
            f"registered before its result is read, even when it is model-free."
        ),
        "",
    ]).strip()

    for line in (row("generation"), row("fit"), key_row):
        if len(line.split("|")) != 17:
            raise SystemExit("a ledger row does not have exactly fifteen cells; a literal '|' slipped into a cell")

    header = (
        f"\n## Cell KPROBE: the centroid boundary key's conversion from delivery to correctness on its own newly "
        f"delivered rows (DRAFT, root countersignature pending)\n\n"
        f"Two unconsumed flight rows -- the KPROBE probe and its FIT spend identity -- for the {rows}-row TRAIN Fold A "
        f"subset whose gold boundary entry the centroid key newly delivers, plus one model-free row for the key file "
        f"itself. Owner decision 145; authority {DIAGNOSTIC} and the CONV precedent {CONV_PACKAGE}. None of these "
        f"rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    # replace-or-append, so re-running this registration never duplicates a row
    fresh = {run_id: row("generation"), fit_run: row("fit"), CENTROID_ARTIFACT: key_row}
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all KPROBE rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + fresh[run_id] + "\n" + fresh[fit_run] + "\n" + fresh[CENTROID_ARTIFACT] + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
