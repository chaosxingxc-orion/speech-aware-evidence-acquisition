#!/usr/bin/env python3
"""Write cell A2's registration package -- COMP-1b on DEV-2000-ADDED (owner decision 198) --
from the committed configs ``derive_slurp_comp1bdev_cells.py`` wrote.

Reads the arm, the smoke and the placeholder chain's own in-chain A/A, recomposes every hash
and PROVES from the composed configs (``core.config.compose``) the commuting square:

* ``arm_vs_placeholder_arm`` / ``smoke_vs_placeholder_smoke``: A2 differs from the superseded
  COMP-1 DEV-2000-ADDED placeholder by EXACTLY the citation contract's four leaf paths plus
  per-flight bookkeeping and the experiment fragment's own block;
* ``arm_vs_comp1b_fold_a``: A2 differs from the flown COMP-1b Fold A arm by EXACTLY the
  composed-config paths the placeholder differs from the flown COMP-1 Fold A arm (the roster
  re-target and this roster's own agreement-table pin), plus bookkeeping and the fragment
  block -- i.e. A2 is COMP-1b's bytes with only the roster moved;
* ``arm_vs_aa``: A2 differs from its in-chain A/A by the agreement term and the centroid key
  ALONE (no citation path, no recall-width path).

The expectation is DECLARED here from the COMP-1b Fold A read (``--expected-effect-pp``, the
read's intent point estimate; owner decision 139: a measured number is not a prior). The SLU
guard is this roster's own null h_SLU 1.2525 (h_intent 1.1520).

It writes the package documents (registered facts with the CANONICAL ``stage3_measurement``,
protocol, six plan documents -- arm, A/A, smoke; generation and FIT --, the analysis recipe,
a draft decision receipt, README and preregistration) and, with ``--append-ledger``, five
DRAFT exposure rows (arm, arm FIT, smoke, smoke FIT, READ) and the supersession notes on the
placeholder's rows (the A/A's two rows are re-pointed at this package's A/A plans).

Config and receipt-pinned bytes alone: no contact of any kind; flips nothing, mints nothing.

    python scripts/flights/comp1/write_slurp_comp1bdev_registration.py \\
        --package-dir docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1 \\
        --study-commit <sha> --registered-at <iso> --expected-effect-pp <x> \\
        --comp1b-read "<intent line>" --comp1b-read-note <path> [--append-ledger]
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

CELLS = {
    "arm": "slurp-native-stage3-comp1b-dev2000-added-v1",
    "aa": "slurp-native-stage3-comp1-aa-dev2000-added-v1",
    "smoke": "slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1",
}
PLACEHOLDER_ARM = "slurp-native-stage3-comp1-dev2000-added-v1"
PLACEHOLDER_SMOKE = "slurp-native-stage3-comp1-dev2000-added-smoke-4-v1"
COMP1_FOLD_A = "slurp-native-stage3-comp1-fold-a-v1"
COMP1B_FOLD_A = "slurp-native-stage3-comp1b-fold-a-v1"
PLACEHOLDER_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1"
PLACEHOLDER_RUNS = {
    "arm": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1",
    "arm_fit": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-FIT-V1",
    "smoke": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-V1",
    "smoke_fit": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-FIT-V1",
    "read": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1",
}
COMP1B_PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-dev2000-added-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 65.40, "intent_accuracy": 76.6}
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official"
ROSTER_RECEIPT = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
ROSTER_ID = "SLURP-DEV-2000-ADDED-V1"
PACKAGE_NAME = "slurp-stage3-comp1b-dev2000-added-v1"
DECISION_ID = "slurp-stage3-comp1b-dev2000-added-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1b-dev2000-added-v1.json"
READ_RUN = "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
ANALYSIS_ROOT = f"analysis/{READ_RUN}"
READ_DRIVER = "scripts/flights/read_paired_cell.sh"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
HEADROOM_NOTE = "docs/results/2026-09-29-slurp-supply-abstention-headroom-offline.md"
DERIVE_SCRIPT = "scripts/flights/comp1/derive_slurp_comp1bdev_cells.py"
LEDGER = "docs/exposure-ledger.md"
AA_SUPPLY_OUTPUT = "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"
ARM_SUPPLY_OUTPUT = "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"
SMOKE_SUPPLY_OUTPUT = "d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083"

#: This roster's own null (instrument note section 2d, row "cross-flight A/A, DEV-2000-ADDED",
#: the B6 pair PLAN vs PLANr-DEV2000); the placeholder registration carries the same numbers.
OWN_NULL = {"h_intent": 1.1520, "h_slu": 1.2525, "n": 1000, "measured_offset_slu_pp": -0.25,
            "source": INSTRUMENT + " section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"}
BAR_PP_N1000 = 2.60
TUNING_ROSTER = "slurp-train-construction-pool-agree-kprobe-r01-excluded"

BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
CITATION_FACTOR_PATHS = (
    "policy", "phase_material.solver.instruction_template", "phase_material.solver.response_format_id",
    "native_episode.deliver_normaliser.normaliser",
)
SUPPLY_FACTOR_PATHS = (f"{BOUNDARY}.rank_weights.w_agree", f"{BOUNDARY}.agreement_source.", f"{BOUNDARY}.facet_source.")
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is")


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


def classify_diff(parent_values: dict, mine: dict, experiment_keys: set, *, allowed: tuple[str, ...]) -> dict:
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))

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


def ledger_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--expected-effect-pp", required=True, type=float)
    parser.add_argument("--comp1b-read", required=True, help="the COMP-1b Fold A read's intent / SLU line, quoted into the basis")
    parser.add_argument("--comp1b-read-note", required=True)
    parser.add_argument("--branch", default="fable/a2reg")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-a2reg")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    expected = round(args.expected_effect_pp, 2)
    if expected < BAR_PP_N1000:
        raise SystemExit(f"expected_effect_pp {expected} is under the {BAR_PP_N1000} pp cross-flight bar at n = 1,000; A2 is not registrable")

    # ---- identities --------------------------------------------------------
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
            "agreement_source_sha256": (perception.get("agreement_source") or {}).get("sha256"),
            "policy": comp.values["policy"], "deliver_normaliser": comp.values["native_episode"]["deliver_normaliser"],
            "solver_response_format_id": comp.values["phase_material"]["solver"].get("response_format_id"),
            "scorers": comp.values["scorers"],
        }
    for key in CELLS:
        if ids[key]["readiness_state"] != "held":
            raise SystemExit(f"{key} is not held")
        if ids[key]["scorers"] != [SCORER, "cost"]:
            raise SystemExit(f"{key} does not score with the DEV sibling {SCORER}")
        if ids[key]["split_role"] != "dev":
            raise SystemExit(f"{key} is not split role dev")
    plan_cells = [c["cell"] for c in json.loads(rd(CAMPAIGN_PLAN))["cells"]]
    if plan_cells != [CELLS["aa"], CELLS["arm"]]:
        raise SystemExit(f"the campaign plan must fly the A/A then the arm: {plan_cells}")

    # ---- the commuting-square proofs ----------------------------------------
    ph_doc, _, ph = composed_of(PLACEHOLDER_ARM)
    phs_doc, _, phs = composed_of(PLACEHOLDER_SMOKE)
    c1_doc, _, c1 = composed_of(COMP1_FOLD_A)
    c1b_doc, _, c1b = composed_of(COMP1B_FOLD_A)
    diffs = {
        "arm_vs_placeholder_arm": classify_diff(ph.values, composed["arm"].values, set(documents["arm"]) | set(ph_doc), allowed=CITATION_FACTOR_PATHS),
        "smoke_vs_placeholder_smoke": classify_diff(phs.values, composed["smoke"].values, set(documents["smoke"]) | set(phs_doc), allowed=CITATION_FACTOR_PATHS),
        "arm_vs_aa": classify_diff(composed["aa"].values, composed["arm"].values, set(documents["arm"]) | set(documents["aa"]), allowed=SUPPLY_FACTOR_PATHS),
    }
    for name in ("arm_vs_placeholder_arm", "smoke_vs_placeholder_smoke"):
        diff = diffs[name]
        if diff["anything_else"]:
            raise SystemExit(f"{name}: differs beyond the citation contract and bookkeeping: {diff['anything_else']}")
        if sorted(diff["factor_paths"]) != sorted(CITATION_FACTOR_PATHS):
            raise SystemExit(f"{name}: the citation contract did not move exactly: {diff['factor_paths']}")
    if diffs["arm_vs_aa"]["anything_else"]:
        raise SystemExit(f"arm_vs_aa: differs beyond the agreement term, the centroid key and bookkeeping: {diffs['arm_vs_aa']['anything_else']}")
    for path in SUPPLY_FACTOR_PATHS:
        if not [k for k in diffs["arm_vs_aa"]["factor_paths"] if k == path or (path.endswith(".") and k.startswith(path))]:
            raise SystemExit(f"arm_vs_aa: {path} did not move")

    # Roster re-target edge: the non-bookkeeping, non-fragment-block paths on which the
    # placeholder differs from COMP-1 Fold A must be exactly those on which A2 differs from
    # COMP-1b Fold A -- and the VALUES on both sides must agree pairwise.
    ret_c1 = classify_diff(c1.values, ph.values, set(c1_doc) | set(ph_doc), allowed=())
    ret_c1b = classify_diff(c1b.values, composed["arm"].values, set(c1b_doc) | set(documents["arm"]), allowed=())
    if ret_c1["anything_else"] != ret_c1b["anything_else"]:
        raise SystemExit(
            "the roster re-target edge does not commute: COMP-1 Fold A -> placeholder moves "
            f"{sorted(set(ret_c1['anything_else']) ^ set(ret_c1b['anything_else']))} differently from COMP-1b Fold A -> A2"
        )
    fa_c1, fa_ph, fa_c1b, fa_a2 = (flatten(v) for v in (c1.values, ph.values, c1b.values, composed["arm"].values))
    for key in ret_c1["anything_else"]:
        if fa_c1.get(key, "<absent>") != fa_c1b.get(key, "<absent>") or fa_ph.get(key, "<absent>") != fa_a2.get(key, "<absent>"):
            raise SystemExit(f"the roster re-target edge moves {key} to different values on the two sides")
    for field in ("population", "split_id"):
        if documents["arm"].get(field) != ph_doc.get(field) or documents["arm"].get(field) != documents["aa"].get(field):
            raise SystemExit(f"the arm's {field} is not the placeholder's / the A/A's")
    diffs["arm_vs_comp1b_fold_a_roster_retarget"] = {
        "retarget_paths": ret_c1b["anything_else"],
        "equals_comp1_fold_a_to_placeholder": True,
        "values_commute": True,
        "bookkeeping": ret_c1b["bookkeeping"],
        "experiment_fragment_own_block": ret_c1b["experiment_fragment_own_block"],
    }
    arm_p = composed["arm"].values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    ph_p = ph.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if arm_p != ph_p:
        raise SystemExit("the arm's boundary channel is not the placeholder's, byte for byte")

    caps = ids["arm"]["family_budget"]
    smoke_caps = ids["smoke"]["family_budget"]
    comp1b_read_note = args.comp1b_read_note

    measurement = {
        ids["arm"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": True,
            "expected_effect_pp": expected,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official, DEV sibling) the non-inferiority guard (owner decision 133)",
            "primary_metric_key": "intent",
            "replicate_run_id": ids["aa"]["run_id"],
            "rows": 1000,
            "own_null": OWN_NULL,
            "roster": f"DEV-2000-ADDED ({ROSTER_ID}, split identity {ids['arm']['split_identity_hash']})",
            "tuning_roster": TUNING_ROSTER,
            "read_roster": ROSTER_ID,
            "note": (
                f"A2 = COMP-1b on DEV-2000-ADDED (owner decision 198). expected_effect_pp {expected} is the COMP-1b "
                f"TRAIN Fold A read's intent point estimate ({comp1b_read_note}: {args.comp1b_read}); owner decision "
                "139: a number measured on a sealed read is not a prior. The SLU-F1 guard is THIS roster's own null "
                f"h_SLU {OWN_NULL['h_slu']} (h_intent {OWN_NULL['h_intent']}), {OWN_NULL['source']}. The cross-flight bar "
                f"at n = 1,000 is about {BAR_PP_N1000} pp. tuning_roster / read_roster (item D3, owner decision 190): the "
                "agreement vote pool and the centroid key are TRAIN construction-pool artifacts disjoint from "
                "DEV-2000-ADDED by the roster receipt's disjointness_proof, and the vote table on this roster is its "
                "own (0 self-excluded exemplars measured); nothing in this cell was tuned on DEV-2000-ADDED."
            ),
        },
        ids["smoke"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "intent accuracy (scenario_action exact)",
            "primary_metric_key": "intent",
            "rows": 4,
            "tuning_roster": "none",
            "read_roster": ROSTER_ID,
            "note": "Four rows prove FORM only; scored by no one, read by no one (instrument rule 5).",
        },
    }

    the_composition = (
        "A2 is COMP-1b's composed plan with only the roster moved, equivalently the superseded COMP-1 "
        "DEV-2000-ADDED placeholder with the citation contract reverted: the locked v2.0 plan as the sealed "
        "DEV-2000-ADDED plan arm flew it + (1) the agreement term (w_agree 1.0 over the exemplar-intent vote, "
        "recall k 60, delivered 8-1-8; this roster's own vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) "
        "+ (2) the centroid boundary key (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) "
        "+ (3) NO citation contract: policy phase-native-candidates-review-revise-v1, Solver "
        "probes/slurp_native_role_solver_v2.txt, no response format, deliver_normaliser saea-deliver-normalise-v3 "
        "+ (4) nothing else."
    )
    none_hint_column = {
        "status": "NOT INCLUDED",
        "what_was_asked": (
            "a DESCRIPTIVE Solver supply-variant column beside the arm (claims_benefit false): the entity-free-share "
            f"'none hint' of owner decision 199, trigger share >= 0.6 ({HEADROOM_NOTE}, mechanism N1)."
        ),
        "why_not": (
            "The same-flight machinery (src/speech_aware_evidence_acquisition/rails/supply_variants.py) admits an arm "
            "that re-caps ONLY the supply-selection knobs of SUPPLY_VARIANT_KNOB_TAILS (phase_supply k, "
            "fuse_coverage m / c / top_l; candidate_supply max_candidates) or swaps ONE pinned alternate release; it "
            "refuses any other path by name before contact. N1 is neither: it is a per-row GATE on the exemplar "
            "supply's entity-free share that adds an explicit empty-entity instruction, i.e. new Solver content "
            "conditioned on a supply statistic -- no knob tail expresses it, and no pinned alternate release "
            "carries it. Expressing it would need new rails code. Separately, an arm group adds one non-delivering "
            "Solver contact per row at the first visit, which raises the run-cumulative contact ceiling (11 per "
            "row) and the fit envelope of the arm's own flight; the registration cannot prove that neutral for the "
            "delivered arm without a FIT measurement. A2 is therefore registered WITHOUT the column; N1 stays a "
            "candidate for its own registration once a rails variant kind exists for it."
        ),
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free fact cell A2's registration rests on, and the CANONICAL stage3_measurement block for "
            "the arm and the smoke. The in-chain A/A's own declaration stays in the placeholder package's "
            "registered facts (the cell, its bytes and its run ids are unchanged)."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "28/86": "development numbers only; never a test claim",
            "133": "intent primary, official SLU-F1 the guard",
            "139": "no prior; a number derived from a measured read is not a prior",
            "161": "the COMP-1 DEV-2000-ADDED replication (the placeholder this cell supersedes)",
            "169": "A2 on the card: the COMP-1 replication on DEV-2000-ADDED with an in-chain A/A",
            "190": "primary_metric_key and the tuning_roster / read_roster split (item D3)",
            "198": "A2 = COMP-1b on DEV-2000-ADDED",
            "199": "the supply 'none' signal (the none-hint column; not included, see none_hint_column)",
        },
        "rows": 1000,
        "the_basis": f"The COMP-1b TRAIN Fold A read ({comp1b_read_note}): {args.comp1b_read}.",
        "the_composition": the_composition,
        "stage3_measurement": measurement,
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget")} for key in CELLS},
        "composed_config_diffs": {
            **diffs,
            "note": (
                "Each entry flattens two composed configs (core.config.compose). The commuting square: A2 vs the "
                "superseded placeholder = the citation contract's four leaves alone; A2 vs the flown COMP-1b Fold A "
                "arm = exactly the paths (and values) by which the placeholder differs from the flown COMP-1 Fold A "
                "arm -- the roster re-target and this roster's agreement-table pin; A2 vs its in-chain A/A = the "
                "agreement term and the centroid key alone. anything_else is empty or this writer refuses."
            ),
            "derive_script": {"relpath": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
        },
        "in_chain_aa": {
            "cell": CELLS["aa"], "run_id": ids["aa"]["run_id"], "fit_run_id": ids["aa"]["fit_run_id"],
            "registered_by": PLACEHOLDER_PACKAGE,
            "note": (
                "The placeholder chain's own in-chain A/A (the sealed DEV plan arm's bytes at recall k 60), carried "
                "into this chain unchanged: its config, run ids and prepared-supply expectation (output digest "
                f"{AA_SUPPLY_OUTPUT}) are the placeholder's. Its two exposure rows are re-pointed at this package's "
                "A/A plan documents so the flip and the pre-launch gate resolve one package."
            ),
        },
        "supersedes": {
            "package": PLACEHOLDER_PACKAGE,
            "cells": [PLACEHOLDER_ARM, PLACEHOLDER_SMOKE],
            "run_ids": sorted(PLACEHOLDER_RUNS.values()),
            "how": "readiness.state 'superseded' on both fragments and a SUPERSEDED note on their five exposure rows; no file deleted; the placeholder never flew",
        },
        "prepared_supplies": {
            "note": "each cell's own, minted model-free at the flip (item E16); never inherited",
            "expected_output_digests": {"arm": ARM_SUPPLY_OUTPUT, "aa": AA_SUPPLY_OUTPUT, "smoke": SMOKE_SUPPLY_OUTPUT},
            "why": "the citation contract acts only on the Solver phase, so A2's first-phase supplies must reproduce the placeholder's own",
        },
        "attribution_classes": {
            "file": PLACEHOLDER_PACKAGE + "/attribution-classes-v1.json",
            "sha256": sha_file(PLACEHOLDER_PACKAGE + "/attribution-classes-v1.json"),
            "note": "membership is a function of the first-phase supply (identical by the digest check above), so the placeholder's classes apply unchanged; the read re-derives and must reproduce every hash",
        },
        "none_hint_column": none_hint_column,
        "budget_arithmetic": {
            "family_budget": caps, "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,000 rows x 11 contacts per row (1 + 2 x (1 + 3 + 1) at max_revisions 1), run-cumulative",
                "removing the citation contract removes tokens, never contacts",
                "one official complete slurp-slu-official score per generation cell over the complete 1,000-row manifest, never sharded",
            ],
        },
        "reported_beside": {
            "note": "CONTEXT ONLY. None of these is this cell's bar.",
            "dev_plan_arm": {"run_id": COMPARATOR_RUN, **COMPARATOR_OFFICIAL},
            "own_null": OWN_NULL,
        },
        "authority_relpaths": [OWNER_DECISIONS, COMP1B_PACKAGE + "/README.md", comp1b_read_note, PLACEHOLDER_PACKAGE + "/README.md", INSTRUMENT, HEADROOM_NOTE],
        "prohibitions": [
            "No flight before root countersigns the rows, mints the decision receipt and the three cells are flipped in one converged cycle.",
            "No re-flying of the sealed DEV plan arm; no test, DEV-1000 or Fold B contact.",
            "No citation contract; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change.",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read against the in-chain A/A flown in the same campaign. PRIMARY: intent accuracy (scenario_action "
        "exact), paired per utterance, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 (slurp-slu-official) "
        f"non-inferior at this roster's own null (h_SLU {OWN_NULL['h_slu']}). REPLICATED: the intent CI95 lower "
        f"bound above zero, the point at or above the {BAR_PP_N1000} pp cross-flight bar at n = 1,000, AND the guard "
        f"holds. NEUTRAL: both guards non-inferior at the own null (h_intent {OWN_NULL['h_intent']} / h_SLU "
        f"{OWN_NULL['h_slu']}) without a replicated gain. HARMFUL: a measured loss on either guard (decision 25). "
        "Every verdict carries the per-stratum tables in both weightings and the attribution classes."
    )
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-comp1b-dev2000-added-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_ROOT_ADMISSION_AND_READINESS_FLIP",
        "the_question": (
            "Does COMP-1b (the agreement term + the centroid key, no citation contract) replicate its TRAIN Fold A "
            "intent gain on the fresh DEV-2000-ADDED roster against its own in-chain A/A, with official SLU-F1 "
            "non-inferior?"
        ),
        "the_composition": the_composition,
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "policy")} for key in CELLS},
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"]},
        "development_numbers_only": "Every number this cell produces is a DEV-2000-ADDED development number (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": f"owner decision 198 ({OWNER_DECISIONS}); the COMP-1b registration {COMP1B_PACKAGE} and its read {comp1b_read_note}; the placeholder {PLACEHOLDER_PACKAGE}; the instrument {INSTRUMENT}; decisions 25, 133, 139, 169, 190",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            if is_fit:
                route = "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
            elif key == "smoke":
                route = "Shared core.flight.cli worker on this cell alone; outside the campaign plan and never scored."
            else:
                route = f"Shared core.flight.cli campaign over {CAMPAIGN_PLAN}, which flies the in-chain A/A and then the A2 arm in ONE campaign (instrument rule 3), one official score per generation cell at finalize."
            plan = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": identity["cell"],
                "experiment": identity["experiment"],
                "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": args.registered_at,
                "status": protocol["status"],
                "source_tree": protocol["source_tree"],
                "preparation_base_commit": args.study_commit,
                "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1",
                    "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": "slurp",
                    "run_id": identity["fit_run_id"] if is_fit else identity["run_id"],
                    "attempt_id": identity["fit_attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "dev",
                    "split_identity_hash": identity["split_identity_hash"],
                    "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": route,
                "prepared_phase_supply": {
                    "relpath": identity["own_supply_requirement"]["relpath"],
                    "sha256": identity["own_supply_requirement"]["sha256"],
                    "expected_output_sha256": {"arm": ARM_SUPPLY_OUTPUT, "aa": AA_SUPPLY_OUTPUT, "smoke": SMOKE_SUPPLY_OUTPUT}[key],
                    "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip (item E16); --allow-output-change must never be passed.",
                },
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": f"{identity['run_id']}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule if key == "arm" else "The in-chain A/A: the within-chain null the arm is read at." if key == "aa" else "Structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before BOTH the arm and the A/A manifests are complete and sealed with one successful complete official slurp-slu-official score each, and the READ row is root countersigned.",
            }
            prefix = {"arm": "", "aa": "aa-", "smoke": "smoke-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-comp1b-dev2000-added-paired-analysis-v1",
        "read_run_id": READ_RUN,
        "title": "Cell A2 -- COMP-1b on DEV-2000-ADDED against its in-chain A/A",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "attempt_id": ids["aa"]["attempt_id"], "fit_run_id": ids["aa"]["fit_run_id"], "role": "the within-chain null the delta is read at", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the sealed DEV plan arm, context beside the A/A, never the bar"},
        },
        "attribution_classes": facts["attribution_classes"],
        "read_driver": {
            "command": f"bash {READ_DRIVER} {package}",
            "passes": ["vs-aa (gating)", "vs-comparator (context only)"],
            "scorer": SCORER,
            "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned",
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260929, "unit": "utterance cluster (paired)"},
        "steps": [
            "1. Refuse unless BOTH the arm and the A/A manifests are COMPLETE at 1,000 rows with this registration's composed config hashes, sealed, each with one successful complete official slurp-slu-official score, and unless the READ row is root countersigned.",
            f"2. THE DELIVERY CHECK (gold-free): each cell's flown first-phase boundary selections must equal its own prepared supply (A/A output {AA_SUPPLY_OUTPUT}; arm {ARM_SUPPLY_OUTPUT}). A mismatch is an engineering defect and closes the read.",
            f"3. Primary: intent accuracy paired per utterance against the in-chain A/A, 10,000 draws, seed 20260929. Guard: official pooled SLU-F1. Apply the protocol's rule at h_intent {OWN_NULL['h_intent']} / h_SLU {OWN_NULL['h_slu']} against the declared expected_effect_pp {expected} and the {BAR_PP_N1000} pp bar.",
            "4. Entity FP / TP / FN against the A/A, with the zero-gold-row emission count (the COMP-1 harm mechanism).",
            "5. The attribution classes (placeholder file, reproduced hashes) with the COMP-1b Fold A conversion rates beside each class.",
            "6. Per-scenario tables in both weightings (natural-mixture and equal-stratum) and the recording-channel split.",
            "7. Write the read under its own id; every number is a DEV-2000-ADDED development number, never a test claim.",
        ],
        "output": {"analysis_root": ANALYSIS_ROOT},
        "boundary": "A development read on the DEV-2000-ADDED evaluation roster (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["arm"]["run_id"], ids["arm"]["fit_run_id"], ids["aa"]["run_id"], ids["aa"]["fit_run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/comp1/comp1bdev_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm (sealed-credit-system-policy-v1, operator context_application): COMP-1b on DEV-2000-ADDED with its in-chain A/A and four-row smoke.",
        "decision": f"Fly cell A2 (owner decision 198): the smoke, then the in-chain A/A and the A2 arm in one campaign on DEV-2000-ADDED 1,000; read at intent primary against the declared {expected} pp with official SLU-F1 the guard at h_SLU {OWN_NULL['h_slu']}.",
        "authorization_basis": f"Owner decision 198 (A2 = COMP-1b on DEV-2000-ADDED); the COMP-1b Fold A read {comp1b_read_note}; decisions 25, 133, 139, 169, 190.",
        "antecedents": {
            "comp1b_read": {"path": comp1b_read_note, "sha256": sha_file(comp1b_read_note)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "placeholder_registration": {"path": PLACEHOLDER_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(PLACEHOLDER_PACKAGE + "/registered-facts-v1.json")},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. Development numbers only. claim: nominated.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the receipt is minted and the three cells are flipped",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "the citation contract, or any k, tau, fuse-policy, w_prior, store, release, snapshot, roster or geometry change",
        ],
        "population": {"count": 1000, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "dev", "roster": ROSTER_ID, "test_contact_authorized": False, "fold_b_contact_authorized": False},
        "prepared_phase_supply": {"note": "each cell's own, minted at the flip (item E16); not pinned by this receipt"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS} | {"note": f"the values of the fragments exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    runs_line = "; ".join(f"`{ids[k]['run_id']}` / `{ids[k]['fit_run_id']}`" for k in CELLS)
    readme = f"""# Cell A2: COMP-1b on DEV-2000-ADDED

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decision 198);
all three cells **held**. Nothing here authorises a flight, a flip or an admission entry.

**Why.** Owner decision 198 defines A2 as COMP-1b on the fresh DEV-2000-ADDED roster. The COMP-1b TRAIN Fold A read
([`{comp1b_read_note}`](../../../{comp1b_read_note})): {args.comp1b_read}.

**Supersedes.** The COMP-1 DEV-2000-ADDED placeholder (`{PLACEHOLDER_PACKAGE}`), whose arm carried the citation
contract and the literal `TO-BE-DECLARED-...` expectation. Its arm and smoke fragments are now `superseded`; their
exposure rows carry a SUPERSEDED note; no file is deleted. The placeholder never flew.

**What it is.** {the_composition} Proven by `registered-facts-v1.json` (`composed_config_diffs`), a commuting square:
A2 vs the placeholder = the citation contract's four leaves alone; A2 vs the flown COMP-1b Fold A arm = exactly the
paths and values by which the placeholder differs from the flown COMP-1 Fold A arm (the roster re-target and this
roster's agreement-table pin); A2 vs its A/A = the agreement term and the centroid key alone. Derived by
`{DERIVE_SCRIPT}`.

**In-chain A/A.** `{CELLS['aa']}` (the sealed DEV plan arm's bytes at recall k 60), the placeholder chain's own A/A,
carried in unchanged; the campaign plan `{CAMPAIGN_PLAN}` flies it and then the arm (instrument rule 3).

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 1,000, intent primary, `expected_effect_pp` **{expected}**
(the COMP-1b Fold A intent point), official SLU-F1 the guard at this roster's own null h_SLU {OWN_NULL['h_slu']}
(h_intent {OWN_NULL['h_intent']}; {OWN_NULL['source']}); bar about {BAR_PP_N1000} pp at n = 1,000.

**The none-hint column (decision 199) is NOT included.** {none_hint_column['why_not']}

**Runs.** {runs_line}. READ `{READ_RUN}`.

**Declare, mint, flip, queue.** (1) Root countersigns the DRAFT rows (arm, arm FIT, smoke, smoke FIT, READ; the A/A's
two rows) and mints `{DECISION_RELPATH}` with `scripts/flights/comp1/comp1bdev_mint_receipt.py` (six eligible run
ids). (2) `scripts/flights/comp1/comp1bdev_flip.sh` re-pins smoke, A/A and arm until the package converges at one
HEAD; each re-minted supply must reproduce its expected output digest. (3) `scripts/flights/comp1/batch_chain_comp1bdev.sh`
queues the smoke then the A/A + arm campaign on the np4 session (decision 77). (4) After both seals the READ row is
countersigned and `bash scripts/flights/comp1/comp1bdev_read.sh` reads it.

**Not authorised.** No flight before steps 1-2; no re-flying of the DEV plan arm; no test, DEV-1000 or Fold B contact;
no citation contract.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# Cell A2 (COMP-1b on DEV-2000-ADDED): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact (owner decision 198).
Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | {the_composition} |
| roster | DEV-2000-ADDED ({ROSTER_ID}), 1,000 rows, split role dev, scorer {SCORER} |
| in-chain A/A | `{ids['aa']['run_id']}`, flown in the same campaign before the arm |
| margins | this roster's own null: h_intent {OWN_NULL['h_intent']}, h_SLU {OWN_NULL['h_slu']} |
| smoke | four rows, structural acceptance, never scored |
| runs | {runs_line} |
| composed config hashes | arm `{ids['arm']['composed_config_hash']}`; A/A `{ids['aa']['composed_config_hash']}`; smoke `{ids['smoke']['composed_config_hash']}` |
| protocol hashes | arm `{ids['arm']['protocol_hash']}`; A/A `{ids['aa']['protocol_hash']}`; smoke `{ids['smoke']['protocol_hash']}` |
| supersedes | `{PLACEHOLDER_PACKAGE}` (arm and smoke) |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Where the declared {expected} pp comes from

The COMP-1b TRAIN Fold A read, {comp1b_read_note}: {args.comp1b_read}. It is a prediction to be tested on a fresh
roster, not a foregone conclusion.

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    appended = 0
    if args.append_ledger:
        ledger = rd(LEDGER)
        model_tool = (
            "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; NO native tool authority on "
            "any role; Perception / Reviewer / Planner prompt bytes the sealed DEV-2000-ADDED plan arm's; the Solver on the "
            "locked plan's non-cited program on every cell"
        )
        inherited = (
            "DEV-2000-ADDED dev rows already exposed by the model-free speech-query encoding pass, the sealed B6 direct and plan "
            "arms, PLANr-DEV2000, CELL-3 and its twin, and ROLL-3 (whose smoke flew the same four smoke rows); this cell adds "
            "no new row and opens no split. Prior exposure is inherited in full."
        )
        common = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the A2 registration (worktree {args.worktree}, branch {args.branch}); owner decision 198. "
            "This registration performs no contact and authorises none."
        )
        rows = []
        for key, fit_flag in (("arm", False), ("arm", True), ("smoke", False), ("smoke", True)):
            identity = ids[key]
            prefix = "" if key == "arm" else "smoke-"
            plan_name = f"{prefix}{'fit' if fit_flag else 'generation'}-plan-registered-v1.json"
            run_id = identity["fit_run_id"] if fit_flag else identity["run_id"]
            attempt = identity["fit_attempt_id"] if fit_flag else identity["attempt_id"]
            budget = identity["family_budget"]
            calls = budget["fit_endpoint_calls_cap"] if fit_flag else budget["generation_calls_cap"]
            what = ("Cell A2, COMP-1b on DEV-2000-ADDED (owner decision 198)" if key == "arm" else "Four-row form smoke of cell A2") + (
                " -- FIT spend identity, request envelopes only, no generation" if fit_flag else "")
            notes = (
                f"{common} Plan SHA256 {plan_shas[f'{key}:' + ('fit' if fit_flag else 'generation')]}; attempt {attempt}. Protocol hash "
                f"{identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session {SESSION} (attach only). "
                f"READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) from the package's root-admission-draft-v1.json "
                "with the six eligible run ids, then scripts/flights/comp1/comp1bdev_flip.sh re-pins with scripts/flights/repin_cell.py "
                "--set-ready, re-minting each cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every "
                f"hash in this row moves at the flip. THE COMPOSITION: {the_composition} Supersedes the COMP-1 DEV-2000-ADDED placeholder "
                f"({PLACEHOLDER_PACKAGE}). Measurement declaration: cross-flight-with-in-chain-replicate, expected_effect_pp {expected} "
                f"(the COMP-1b Fold A intent point), claims_benefit {'true' if key == 'arm' else 'false'}, replicate_run_id {ids['aa']['run_id']}, "
                f"own null h_intent {OWN_NULL['h_intent']} / h_SLU {OWN_NULL['h_slu']}, intent primary with official SLU-F1 ({SCORER}) the guard. "
                f"Read: {READ_RUN} by {READ_DRIVER}. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
                "re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
            )
            rows.append(ledger_row([
                args.registered_at, run_id, "bounded-discovery-probe", what, model_tool,
                f"slurp DEV-2000-ADDED {identity['rows']}", "dev", identity["split_identity_hash"], "no", str(calls),
                str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), inherited,
                f"{package}/{plan_name}", notes,
            ]))
        rows.append(ledger_row([
            args.registered_at, READ_RUN, "model-free-check",
            "The cell A2 read: COMP-1b on DEV-2000-ADDED against its in-chain A/A (gating; intent primary, official SLU-F1 the guard, at the own null h_intent 1.1520 / h_SLU 1.2525 against the declared expected_effect_pp), entity FP/TP/FN and zero-gold emission, attribution classes, per-scenario tables in both weightings; the sealed DEV plan arm as context only.",
            "No model, tokenizer, encoder or server contact: scripts/flights/read_paired_cell.sh over the sealed per-sample official slurp-slu-official scores and sealed receipts.",
            "slurp DEV-2000-ADDED 1000", "dev", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
            "Reads only sealed manifests of this package and its registered comparator; no new audio, gold or reference exposure.",
            f"{package}/analysis-recipe-v1.json",
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package, so the pre-launch gate scripts/checks/flight_registration_check.py finds it. Analysis root $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/; recipe {package}/analysis-recipe-v1.json (recipe_id {recipe['recipe_id']}); driver {READ_DRIVER} refuses before any score is opened until root countersigns this row (after both seals). No utterance text, gold, transcript or model output is printed or persisted.",
        ]))
        lines = ledger.split("\n")
        anchor = max(i for i, line in enumerate(lines) if line.startswith(f"| ") and PLACEHOLDER_RUNS["read"] in line.split("|")[2])
        # Supersession notes and the A/A re-point, in place.
        superseded_note = (
            f" SUPERSEDED {args.registered_at[:10]} by cell A2 ({package}, owner decision 198: A2 = COMP-1b on DEV-2000-ADDED); "
            "this cell never flew and never will in this form; its fragment readiness is 'superseded'; no file deleted."
        )
        aa_note = (
            f" CARRIED INTO cell A2 {args.registered_at[:10]} ({package}, decision id {DECISION_ID}): this in-chain A/A, unchanged, "
            f"is flown in A2's campaign {CAMPAIGN_PLAN} before the A2 arm; artifacts re-pointed at A2's A/A plan; the placeholder arm it "
            "was registered beside is superseded."
        )
        superseded_runs = set(PLACEHOLDER_RUNS.values())
        aa_plan = {ids["aa"]["run_id"]: f"{package}/aa-generation-plan-registered-v1.json", ids["aa"]["fit_run_id"]: f"{package}/aa-fit-plan-registered-v1.json"}
        for i, line in enumerate(lines):
            if not line.startswith("| "):
                continue
            parts = line.split("|")
            if len(parts) < 17:
                continue
            run = parts[2].strip()
            if run in superseded_runs and "SUPERSEDED" not in parts[-2]:
                parts[-2] = parts[-2].rstrip() + superseded_note + " "
                lines[i] = "|".join(parts)
            elif run in aa_plan and "CARRIED INTO cell A2" not in parts[-2]:
                parts[-3] = f" {aa_plan[run]} "
                parts[-2] = parts[-2].rstrip() + aa_note + " "
                lines[i] = "|".join(parts)
        lines[anchor + 1:anchor + 1] = rows
        io.open(LEDGER, "w", encoding="utf-8", newline="").write("\n".join(lines))
        appended = len(rows)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "composed_config_diffs": {k: {kk: (len(vv) if isinstance(vv, list) else vv) for kk, vv in v.items()} for k, v in diffs.items()},
        "retarget_paths": diffs["arm_vs_comp1b_fold_a_roster_retarget"]["retarget_paths"],
        "ledger_rows_appended": appended,
        "expected_effect_pp": expected,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
