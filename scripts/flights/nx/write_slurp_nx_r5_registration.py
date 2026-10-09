#!/usr/bin/env python3
"""Write the registration package of NX Stage J round R5 -- the composed read (review-off COMP-1b + v4g, lock v2.2) on
DEV-2000-ADDED, in ONE chain beside the HELD module OFF-arm replicate -- from the committed configs
``derive_slurp_nx_r5_cells.py`` wrote.

Reads the composed arm and smoke, recomposes every hash, re-runs the module byte proof (``scripts/analysis/module_equivalence_proof.py``,
cases m0 and m6) and PROVES from the composed configs (``core.config.compose``):

* ``arm_vs_module_arm`` / ``smoke_vs_module_smoke``: the composed cell differs from the HELD module COMP-1b cell by EXACTLY the
  lock / review-off / v4g leaves (``LEAVES``), plus the module declaration, per-flight bookkeeping and the experiment fragment's own
  block;
* ``arm_vs_a2_arm``: the same plus the lock-v2.1 Reviewer pin (the module cell's own distance from the sealed A2 arm);
* ``replicate_vs_a2_aa``: the reused replicate (the module OFF arm) differs from the sealed A2 in-chain A/A by exactly the lock-v2.1
  Reviewer template and the recall k (60 -> 8, a proven supply no-op at w_agree 0) -- the replicate is NOT byte-identical to the
  sealed A2 A/A and the package says so;
* ``replicate_reuse``: the replicate's composed config and protocol hashes equal what the HELD module package registered.

It writes the package documents (registered facts with the CANONICAL ``stage3_measurement``, protocol, four plan documents, the analysis
recipe, a draft decision receipt, README and preregistration) and, with ``--append-ledger``, five DRAFT exposure rows (arm, arm FIT,
smoke, smoke FIT, READ). The replicate keeps the two DRAFT rows the module package registered.

Config and receipt-pinned bytes alone: no contact of any kind; flips nothing, mints nothing.

    python -B scripts/flights/nx/write_slurp_nx_r5_registration.py --study-commit <sha> --registered-at <iso> [--append-ledger]
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
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nx_r5_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "analysis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
DERIVE_SCRIPT = "scripts/flights/nx/derive_slurp_nx_r5_cells.py"
PROOF_SCRIPT = "scripts/analysis/module_equivalence_proof.py"
READ_DRIVER = "scripts/flights/nx/nx_r5_read.sh"
V4G_REGISTRATION = "docs/readiness/2026-10-09-slurp-nx-postprocessing-v4g-registration-v1.md"
N100_REVIEW_OFF = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md section F2"
REVIEWER = "phase_material.reviewer.instruction_template"
RECALL_K = "knowledge_stores.intent-boundaries.phase_supply.perception.k"
MODULE_BLOCK = "native_episode.consumption_module."
#: The policy leaves the composed cell moves from the HELD module COMP-1b cell: lock layer v2.1 -> v2.2 (v4g at delivery) and the
#: review-off profile (module compiler output). Nothing else policy-side differs.
LEAVES = (
    "native_episode.consumption_module.lock", "native_episode.consumption_module.review_loop",
    "native_episode.deliver_normaliser.normaliser", "native_episode.max_revisions", "native_episode.review_loop",
    "native_episode.roles.planner.max_iterations", "native_episode.roles.reviewer.max_iterations", "phase_tools", "policy",
)
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "preparation_source_receipts", "what_this_is",
                        "fragment_kind")


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
    if isinstance(node, dict) and node:
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    else:
        out[prefix[:-1]] = node
    return out


def classify_diff(left: dict, right: dict, experiment_keys: set, *, allowed: tuple[str, ...]) -> dict:
    a, b = flatten(left), flatten(right)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))

    def matches(key: str, path: str) -> bool:
        return key == path or (path.endswith(".") and key.startswith(path))

    factor = [k for k in changed if any(matches(k, p) for p in allowed)]
    declaration = [k for k in changed if k not in factor and k.startswith(MODULE_BLOCK)]
    bookkeeping = [k for k in changed if k not in factor and k not in declaration and k.startswith(BOOKKEEPING_PREFIXES)]
    rest = [k for k in changed if k not in factor and k not in declaration and k not in bookkeeping]
    experiment_block = [k for k in rest if k.split(".", 1)[0] in experiment_keys]
    other = [k for k in rest if k not in experiment_block]
    return {"factor_paths": factor, "module_declaration": declaration, "bookkeeping": bookkeeping,
            "experiment_fragment_own_block": experiment_block, "anything_else": other}


def composed_of(experiment: str):
    document = json.loads(rd(f"configs/experiment/{experiment}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
    return document, cell, composed


def ledger_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package, prereg = nf.PACKAGE, nf.PREREG
    expected = nf.EXPECTED_EFFECT_PP

    # ---- identities --------------------------------------------------------
    cells = {"arm": nf.ARM["experiment"], "smoke": nf.SMOKE["experiment"], "replicate": nf.REPLICATE["experiment"]}
    ids: dict[str, dict] = {}
    composed: dict[str, object] = {}
    documents: dict[str, dict] = {}
    for key, experiment in cells.items():
        document, cell, comp = composed_of(experiment)
        documents[key], composed[key] = document, comp
        split = document["population"]["split_identity_hash"]
        fit = comp.values["native_contact_fit"]
        own_supply = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json"))
        block = comp.values["native_episode"]["consumption_module"]
        ids[key] = {
            "cell": cell["cell_id"], "experiment": experiment, "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": fit["run_id"], "fit_attempt_id": fit["attempt_id"], "fit_contact_cap": fit["contact_cap"],
            "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": comp.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "split_role": document["execution_plan"]["split_role"],
            "composed_config_hash": comp.config_hash, "protocol_hash": protocol_hash(comp.config_hash, comp.values["arm"], split),
            "family_budget": document["family_budget"], "readiness_state": cell["readiness"]["state"],
            "own_supply_requirement": own_supply,
            "module": {"module_id": block["module_id"], "lock": block["lock"], "review_loop": block.get("review_loop", "on"),
                       "armed": [c["component_id"] for c in block["components"] if c["state"] != "off"]},
            "policy": comp.values["policy"],
            "deliver_normaliser": comp.values["native_episode"]["deliver_normaliser"]["normaliser"],
            "solver_template": comp.values["phase_material"]["solver"]["instruction_template"],
            "scorers": comp.values["scorers"],
        }
    for key in cells:
        if ids[key]["readiness_state"] != "held":
            raise SystemExit(f"{key} is not held")
        if ids[key]["scorers"] != [nf.SCORER, "cost"]:
            raise SystemExit(f"{key} does not score with the DEV sibling {nf.SCORER}")
        if ids[key]["split_role"] != "dev":
            raise SystemExit(f"{key} is not split role dev")
    arm, smoke, rep = ids["arm"], ids["smoke"], ids["replicate"]
    if (arm["run_id"], smoke["run_id"], arm["fit_run_id"], smoke["fit_run_id"]) != (
            nf.ARM["run_id"], nf.SMOKE["run_id"], nf.ARM["fit_run_id"], nf.SMOKE["fit_run_id"]):
        raise SystemExit("composed identities differ from nx_r5_family")
    if (rep["run_id"], rep["attempt_id"], rep["fit_run_id"]) != (nf.REPLICATE["run_id"], nf.REPLICATE["attempt_id"], nf.REPLICATE["fit_run_id"]):
        raise SystemExit("the replicate identities differ from nx_r5_family")
    if (arm["policy"], arm["module"]["lock"], arm["module"]["review_loop"], arm["deliver_normaliser"]) != (
            nf.PROGRAM, nf.LOCK, "off", nf.NORMALISER):
        raise SystemExit("the composed arm is not the review-off lock-v2.2 program")
    if (rep["module"]["lock"], rep["deliver_normaliser"], rep["module"]["armed"]) != ("v2.1", "saea-deliver-normalise-v3", []):
        raise SystemExit("the replicate is not the module OFF arm on lock v2.1 / v3")
    if arm["solver_template"] != nf.SOLVER_TEMPLATE_PIN[len("configs/"):] or hashlib.sha256(Path(nf.SOLVER_TEMPLATE_PIN).read_bytes()).hexdigest() != nf.SOLVER_TEMPLATE_SHA:
        raise SystemExit("the Solver template is not the locked one")
    if arm["split_identity_hash"] != rep["split_identity_hash"]:
        raise SystemExit("the arm and the replicate are not on one split identity")
    if arm["fit_contact_cap"] != nf.fit_contact_cap(nf.ROWS) or smoke["fit_contact_cap"] != nf.fit_contact_cap(nf.SMOKE_ROWS):
        raise SystemExit("a FIT cap is not structural")
    plan_cells = [c["cell"] for c in json.loads(rd(nf.CAMPAIGN_PLAN))["cells"]]
    if plan_cells != [nf.REPLICATE["experiment"], nf.ARM["experiment"]]:
        raise SystemExit(f"the campaign plan must fly the replicate then the composed arm: {plan_cells}")

    # ---- the replicate is reused AS REGISTERED -----------------------------------
    parent_facts = json.loads(rd(f"{nf.PARENT_PACKAGE}/registered-facts-v1.json"))
    parent_cell = parent_facts["cells"]["aa"]
    reuse = {
        "package": nf.PARENT_PACKAGE,
        "registered_composed_config_hash": parent_cell["composed_config_hash"],
        "recomposed_composed_config_hash": rep["composed_config_hash"],
        "registered_protocol_hash": parent_cell["protocol_hash"],
        "recomposed_protocol_hash": rep["protocol_hash"],
    }
    reuse["hashes_equal"] = (reuse["registered_composed_config_hash"] == reuse["recomposed_composed_config_hash"]
                             and reuse["registered_protocol_hash"] == reuse["recomposed_protocol_hash"])
    if not reuse["hashes_equal"]:
        raise SystemExit("the replicate's recomposed hashes differ from the module package's registered ones: it needs a re-pin "
                         f"before this package can pin it: {reuse}")

    # ---- the byte proofs --------------------------------------------------------
    m6 = proof.run_m6(REPO_ROOT)
    m0 = proof.run_case("m0", REPO_ROOT)
    if not (m6["ok"] and m0["ok"]):
        raise SystemExit("the module byte proof (m0 / m6) does not hold; refusing to register")
    diffs: dict[str, dict] = {}
    module_cells = {"arm": "slurp-native-stage3-module-comp1b-dev2000-added-v1", "smoke": "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1"}
    for key, other in module_cells.items():
        other_doc, _, other_comp = composed_of(other)
        diff = classify_diff(other_comp.values, composed[key].values, set(documents[key]) | set(other_doc), allowed=LEAVES)
        if diff["anything_else"]:
            raise SystemExit(f"{key}_vs_module: differs beyond the lock / review-off / v4g leaves: {diff['anything_else']}")
        if sorted(diff["factor_paths"]) != sorted(LEAVES):
            raise SystemExit(f"{key}_vs_module: unexpected leaves {diff['factor_paths']}")
        diffs[f"{key}_vs_module_{key}"] = diff
    a2_arm_doc, _, a2_arm = composed_of(nf.A2_ARM["experiment"])
    diff = classify_diff(a2_arm.values, composed["arm"].values, set(documents["arm"]) | set(a2_arm_doc), allowed=LEAVES + (REVIEWER,))
    if diff["anything_else"]:
        raise SystemExit(f"arm_vs_a2_arm: differs beyond the declared leaves: {diff['anything_else']}")
    diffs["arm_vs_a2_arm"] = diff
    a2_aa_doc, _, a2_aa = composed_of(nf.A2_AA["experiment"])
    diff = classify_diff(a2_aa.values, composed["replicate"].values, set(documents["replicate"]) | set(a2_aa_doc), allowed=(REVIEWER, RECALL_K))
    if diff["anything_else"] or sorted(diff["factor_paths"]) != sorted([REVIEWER, RECALL_K]):
        raise SystemExit(f"replicate_vs_a2_aa: not exactly the Reviewer template and recall k: {diff}")
    diffs["replicate_vs_a2_aa"] = diff
    for field in ("population", "split_id"):
        if documents["arm"].get(field) != documents["replicate"].get(field):
            raise SystemExit(f"the arm's {field} is not the replicate's")

    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    replicate_caps = documents["replicate"]["family_budget"]

    # ---- the declaration -------------------------------------------------------
    expectation_basis = {
        "primary": "official pooled SLU-F1 (slurp-slu-official, DEV sibling), composed minus the sealed A2 arm",
        "review_off_vs_full_graph_pp": nf.REVIEW_OFF_VS_FULL_PP,
        "review_off_vs_full_graph_source": (
            f"{N100_REVIEW_OFF}: the N100 read, review-off minus full graph -1.48 [-5.33, +2.72] (unresolved; n = 100); a "
            "descriptive number, not a prior (owner decision 139), and the only measured one"),
        "v4g_delivery_gain_pp": nf.V4G_LOCK_COLUMN_PP,
        "v4g_delivery_gain_source": (
            f"{nf.V4G_LOCK_RECORD} section 2 step 5: v4g(lock) minus lock on the TRAIN Fold B R1 delivering column "
            "+1.55 [+0.81, +2.33] (offline; the A2 DEV pool read is +0.98 [+0.21, +1.74] and is the roster the rules were selected on, "
            "so descriptive only). In the delivered cross-flight contrast it accrues to the composed side only."),
        "sum_pp": expected,
        "reading": (
            f"{expected:+.2f} pp is the sum of an unresolved loss and a confirmed gain and sits far under the {nf.BAR_PP_N1000} pp "
            "rule-3 bar a cross-flight read at n = 1,000 can resolve; the cell therefore claims NO benefit. Its claim is NO LOSS at "
            "about half the contacts (2.0 per row against 4.05 for the sealed A2 arm) plus the v4g delivered gain."),
    }
    measurement = {
        arm["run_id"]: {
            "admission": "no-harm",
            "bar_pp": nf.BAR_PP_N1000,
            "claim": "no-harm",
            "claims_benefit": False,
            "comparator_attempt_id": nf.A2_ARM["attempt_id"],
            "comparator_run_id": nf.A2_ARM["run_id"],
            "expected_effect_basis": expectation_basis,
            "expected_effect_pp": expected,
            "harm_margin_pp": nf.HARM_MARGIN_PP,
            "harm_margin_pp_by_metric": {"intent_accuracy": nf.HARM_MARGIN_PP, "slu_f1": nf.HARM_MARGIN_PP},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "note": (
                "NX Stage J round R5: the composed system -- COMP-1b on lock v2.2 (v4g at delivery), Reviewer loop off, locked Solver "
                "template -- read cross-flight against the sealed A2 arm (COMP-1b, full graph, lock v2.0 + v3) with the module OFF-arm "
                "replicate flown in the SAME chain (instrument rule 3). Primary: official pooled SLU-F1; intent the guard (owner "
                "decision 133 scopes intent-primary to intent-acting mechanisms; this round's mechanism acts on delivery and the "
                "graph, so SLU-F1 is primary). The claim is NO LOSS at about half the contacts plus the v4g delivered gain; "
                f"expected_effect_pp {expected:+.2f} is declared from measured numbers (expected_effect_basis) and is far under the "
                f"{nf.BAR_PP_N1000} pp bar, so claims_benefit is false and the cell is admitted on a no-harm reading "
                f"(harm_margin_pp {nf.HARM_MARGIN_PP}, not tighter than the cross-flight sampling floor {nf.OWN_NULL['h_slu']} at n = 1,000). "
                "The replicate is the module OFF arm: it is request-identical to the sealed A2 in-chain A/A except the lock-v2.1 Reviewer "
                "template and the recall k (a proven supply no-op), so replicate-minus-A2-A/A is the flight-to-flight OFFSET the "
                "composed-minus-A2 contrast is read beyond. The v4 rule selection on this very roster is declared in tuning_exception."),
            "offset_pair": {"left_run_id": nf.A2_AA["run_id"], "left_attempt_id": nf.A2_AA["attempt_id"],
                            "right_run_id": rep["run_id"], "right_attempt_id": rep["attempt_id"]},
            "own_null": nf.OWN_NULL,
            "primary_metric": "official pooled SLU-F1 (slurp-slu-official, DEV sibling), composed minus the sealed A2 arm beyond the replicate offset; intent accuracy (scenario_action exact) the non-inferiority guard",
            "primary_metric_key": "slu",
            "read_roster": nf.ROSTER_ID,
            "replicate_run_id": rep["run_id"],
            "roster": f"DEV-2000-ADDED ({nf.ROSTER_ID}, split identity {arm['split_identity_hash']})",
            "rows": nf.ROWS,
            "tuning_exception": nf.TUNING_EXCEPTION,
            "tuning_roster": nf.TUNING_ROSTER,
        },
        smoke["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "note": "Four rows prove FORM only: the lock-v2.2 review-off program loads, no Reviewer or Planner is visited, the delivery node renders v4g, every request fits and the episode completes. Scored by no one, read by no one (instrument rule 5).",
            "primary_metric": "none (structural form only)",
            "read_roster": nf.ROSTER_ID,
            "rows": nf.SMOKE_ROWS,
            "tuning_roster": "none",
        },
    }
    the_composition = (
        "The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.2 (module step 7: "
        "lock v2.1 with the delivery normaliser saea-deliver-normalise-v4g, version 1) with the Reviewer loop OFF (review_loop off: "
        f"Perception then Solver, Planner and Reviewer iterations 0, max_revisions 0, no tool schema on any role; the compiled program "
        f"{nf.PROGRAM}, ceiling {nf.CEILING}) and COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, recall k 60, THIS "
        "roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key "
        "(SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- every other catalogued component OFF (no citation contract, no scope-rule "
        "stage, no re-listen, no Perception column, no template column). The Solver instruction template is the locked "
        f"{nf.SOLVER_TEMPLATE_PIN} (sha256 {nf.SOLVER_TEMPLATE_SHA[:8]}...). Every policy block is the module compiler's output; the "
        "roster pins are DEV-2000-ADDED's own."
    )
    swap_point = (
        f"The ONE-LINE swap point is `SOLVER_TEMPLATE_PIN` in `scripts/flights/nx/nx_r5_family.py` (today `{nf.SOLVER_TEMPLATE_PIN}`). "
        "If the R1 iteration-2 pick (`r1-i2-c*`, pinned under `configs/probes/nx/solver/r1/`) is NOMINATED and confirmed on Fold A, "
        "the coordinator changes that one line (and `SOLVER_TEMPLATE_SHA`) and re-runs `derive_slurp_nx_r5_cells.py` and "
        "`write_slurp_nx_r5_registration.py`. CAUTION, stated honestly: the module has NO registered composition today that "
        "delivers a non-locked Solver instruction template (the only components that write the Solver template are "
        "`solver-citation-contract`, refused on lock v2.2, and the slot-lookup opportunity, which is a tool path); the derive "
        "script therefore REFUSES any other value, by design. The swap needs a registered module step first (a lock layer or a "
        "`solver-template` leaf, like step 7), which is a code change outside this registration."
    )
    needs = (
        "HELD. Decision 238 (close Stage S at the Solver node, compose Stage J = R5) is PROPOSED, not ruled, and the R1 iteration-2 "
        "verdict (does the Solver template enter the composition?) is pending. This package registers the composition decision "
        "A names WITHOUT a new Solver template; if the iteration-2 pick is delivered it is a swap (see the README), not a new cell."
    )
    offset_text = (
        "THE OFFSET. The replicate (module OFF arm, lock v2.1 + v3, full graph) is flown in the same chain as the composed arm. "
        "Replicate-minus-sealed-A2-A/A (same roster, same rows) measures what a re-flight of the same base drifts by "
        "cross-flight; it is reported beside every cross-flight number and the composed-minus-A2 contrast is read beyond it."
    )
    decision_rule = (
        "Read in ONE chain: the replicate then the composed arm (campaign plan "
        f"{nf.CAMPAIGN_PLAN}). PRIMARY: official pooled SLU-F1 (slurp-slu-official), paired per utterance cluster (10,000 draws, seed "
        "20260915), composed minus the sealed A2 arm "
        f"({nf.A2_ARM['run_id']}). GUARD: intent (scenario_action exact), same contrast. OFFSET o: replicate minus the sealed A2 in-chain A/A "
        f"({nf.A2_AA['run_id']}), same metrics. THE BAR: {nf.BAR_PP_N1000} pp at n = 1,000 (instrument rule 3). "
        "NOMINATED iff the CI95 lower bound of (composed minus A2) on SLU-F1 is above |o| (beyond the replicate offset) AND the point "
        f"estimate is at or above the {nf.BAR_PP_N1000} pp bar AND the intent guard shows no HARM; this is NOT expected (declared "
        f"effect {expected:+.2f} pp) and would be a surprise to replicate before any use. NEUTRAL iff the CI95 lower bound of "
        f"(composed minus A2) on SLU-F1 and on intent is at or above -{nf.HARM_MARGIN_PP} pp (the preregistered harm margin) and the "
        "read is neither NOMINATED nor HARM: the composition keeps the full-graph accuracy within what a cross-flight read can see "
        "at about half the contacts -- still an efficiency result, never reported as a gain. HARM iff the CI95 upper bound of "
        "(composed minus A2) on SLU-F1 or on intent is below -|o| (a resolved loss beyond the flight offset, owner decision 25). A "
        f"read whose lower bound is under -{nf.HARM_MARGIN_PP} pp while neither HARM nor NOMINATED is UNRESOLVED (the design cannot "
        "rule out a margin loss) and is reported as such, not as NEUTRAL. Reported beside, CONTEXT ONLY and never the bar: "
        "composed minus the in-chain replicate (the whole composition against its same-chain base, intent and SLU-F1, with no offset "
        "correction needed); composed minus the sealed A2 in-chain A/A; the same contrasts with the v4g normaliser applied offline "
        "to the A2 and replicate columns so all columns are compared under v4g (isolating graph and supply from the normaliser); "
        "per-scenario tables in natural-mixture and equal-stratum weightings; the cost table. The verdict word is the coordinator's "
        "(owner decision 139)."
    )
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": ("Every model-free fact the NX R5 registration rests on, and the CANONICAL stage3_measurement block (keyed by run id) "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve."),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "status": "HELD (decision 238 PROPOSED; R1 iteration-2 verdict pending)",
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "28/86": "development numbers only; never a test claim",
            "133": "intent primary for intent-acting mechanisms; SLU-F1 primary for slot/delivery mechanisms",
            "139": "no prior; a number derived from a measured read is not a prior",
            "169": "the module-all-off lock layer is the in-chain A/A comparator of every composed read",
            "190": "primary_metric_key and the tuning_roster / read_roster split (item D3)",
            "228-234": "the NX node-extreme programme; the Reviewer loop is removed from the NX base (F2)",
            "238": "PROPOSED: close Stage S at the Solver node, compose Stage J = R5",
        },
        "rows": nf.ROWS,
        "the_composition": the_composition,
        "the_swap_point": swap_point,
        "does_this_cell_need_to_wait": needs,
        "stage3_measurement": measurement,
        "decision_rule": decision_rule,
        "offset": offset_text,
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget")} for key in cells},
        "replicate_reuse": {
            **reuse,
            "note": ("The replicate is the HELD module OFF-arm cell reused AS REGISTERED: its own package, its own two DRAFT ledger rows "
                     "(run and FIT), its own receipt coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json "
                     "(eligible run ids already list it). This package re-pins nothing of it; the flip (nx_r5_flip.sh) re-pins it through "
                     "its own module_comp1bdev_repin_aa.sh exactly as the module flip does. Its stage3_measurement block there names the "
                     "module arm as its replicate (the pairing of that package); in THIS chain it plays the replicate of the composed arm."),
            "registered_budget": replicate_caps,
        },
        "module_byte_proof": {
            "script": {"relpath": PROOF_SCRIPT, "sha256": sha_file(PROOF_SCRIPT)},
            "command": f"python -B {PROOF_SCRIPT} --at m0 m6",
            "ok": True,
            "m0": [{k: r[k] for k in ("experiment", "lock", "module_composed_hash", "composed_identical")} for r in m0["results"]],
            "m6": [{k: r[k] for k in ("cell", "experiment", "lock", "armed", "module_block_sha256", "own_composed_hash",
                                      "module_composed_hash", "composed_identical",
                                      "module_policy_on_a2_roster_differing_paths", "reviewer_template")}
                   for r in m6["results"]],
            "note": ("AT-M6 holds for the three HELD module cells, among them the replicate: its block compiles to its own composed "
                     "hash and, compiled onto A2's in-chain A/A fragment, differs from A2's policy blocks at exactly the Reviewer "
                     "template and the recall k. THE REPLICATE IS THEREFORE NOT BYTE-IDENTICAL TO THE SEALED A2 A/A: it carries the "
                     "lock-v2.1 Reviewer pin (a measured no-harm / no-gain move) and k 8 against k 60 at w_agree 0 (a proven supply "
                     "no-op, output digest d57ee9d6...). The offset it measures includes those two named leaves."),
        },
        "composed_config_diffs": {
            **diffs,
            "note": ("Each entry flattens two composed configs (core.config.compose). The composed cell vs the HELD module COMP-1b cell = "
                     "the lock-v2.2 / review-off / v4g leaves alone (factor_paths) plus the module declaration, bookkeeping and the "
                     "experiment fragment; vs the sealed A2 arm the same plus the lock-v2.1 Reviewer pin; the replicate vs the sealed A2 "
                     "A/A = the Reviewer template and the recall k. anything_else is empty or this writer refuses."),
            "derive_script": {"relpath": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
        },
        "prepared_supplies": {
            "note": "each cell's own, minted model-free at the flip (item E16); never inherited",
            "expected_output_digests": {"arm": "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08",
                                        "smoke": "d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083",
                                        "replicate": "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"},
            "why": ("the lock pins, the review-off graph and the delivery normaliser act downstream of the first-phase Perception "
                    "supply; the arm's and smoke's sources are the HELD module cells' own (cell A2's), the replicate's the sealed DEV "
                    "plan arm's. A different digest at the flip means the knowledge channel moved: stop and report."),
        },
        "budget_arithmetic": {
            "family_budget": caps, "smoke_family_budget": smoke_caps, "replicate_registered_family_budget": replicate_caps,
            "derivation": [
                f"generation_calls_cap = {nf.ROWS:,} rows x {nf.CEILING} contacts per row (perception 1 + solver 1; the compiled review-off program "
                f"{nf.PROGRAM}) = {nf.ROWS * nf.CEILING:,}, run-cumulative; the smoke {nf.SMOKE_ROWS} x {nf.CEILING} = {nf.SMOKE_ROWS * nf.CEILING}",
                f"fit_endpoint_calls_cap = rows x {nf.CEILING} x (max_speech_packets 1 + 3) = {nf.fit_contact_cap(nf.ROWS):,} (smoke {nf.fit_contact_cap(nf.SMOKE_ROWS)}), structural, never run-cumulative",
                f"repeated_speech_audio_seconds_cap = ceil(roster audio x {nf.CEILING}) = {caps['repeated_speech_audio_seconds_cap']:,} (smoke {smoke_caps['repeated_speech_audio_seconds_cap']}); the audio source is proven against the parent module cell's own cap at ceiling 11",
                f"planned GPU hours {nf.PLANNED_GPU_HOURS_ARM} (arm; {nf.ROWS * nf.CEILING:,} contacts at the measured ~50 contacts per minute need about 0.7 h plus the FIT and load) and {nf.PLANNED_GPU_HOURS_SMOKE} (smoke)",
                "the replicate keeps the budget the module package registered (11,000 generation calls cap, 12.0 GPU-h, the full-graph ceiling); the CHAIN total is the sum of both cells' caps",
                "one official complete slurp-slu-official score per generation cell over the complete 1,000-row manifest, never sharded",
            ],
        },
        "cost_expectation": {
            "composed_contacts_per_row": 2.0,
            "sealed_a2_arm_contacts_per_row": 4.05, "sealed_a2_aa_contacts_per_row": 4.068,
            "source": f"{nf.A2_READ} section 1 (4,050 and 4,068 contacts per 1,000 rows)",
            "note": "the composed arm's contacts are exact (no revision loop); the comparison is descriptive and measured at the read",
        },
        "reported_beside": {"note": "CONTEXT ONLY. None of these is this cell's bar.",
                            "a2": {"arm": nf.A2_ARM["run_id"], "aa": nf.A2_AA["run_id"], "read": nf.A2_READ},
                            "own_null": nf.OWN_NULL},
        "authority_relpaths": [nf.OWNER_DECISIONS, nf.PROGRAMME, nf.STEP7, nf.V4G_LOCK_RECORD, nf.A2_READ, nf.LOCK_NOTE_V2_1, nf.INSTRUMENT],
        "prohibitions": [
            "No flight before decision 238 is ruled and the coordinator decides it flies, root countersigns the rows of BOTH packages, mints BOTH receipts, and the three cells are flipped in one converged cycle.",
            "No re-flying of any sealed cell; no test, DEV-1000, Fold A or Fold B contact.",
            "No component beyond the declared block; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster, template or geometry change outside the compiler.",
            "No scope-rule stage and no solver-citation-contract on this block (refused on lock v2.2); no template column.",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": f"slurp-{nf.SLUG}-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {nf.WORKTREE}, branch {nf.BRANCH}",
        "status": "REGISTERED_BEFORE_CONTACT_HELD_AWAITING_DECISION_238_AND_THE_R1_ITERATION_2_VERDICT",
        "the_question": ("Does the composed system -- COMP-1b on lock v2.2 (v4g at delivery) with the Reviewer loop off -- keep the sealed "
                         "A2 arm's official pooled SLU-F1 and intent (no loss beyond the flight offset) at about half the contacts, "
                         "and does v4g deliver its offline gain at delivery?"),
        "the_composition": the_composition,
        "the_swap_point": swap_point,
        "does_this_cell_need_to_wait": needs,
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "policy", "module")} for key in cells},
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"],
                                                    "module_byte_proof": facts["module_byte_proof"],
                                                    "replicate_reuse": facts["replicate_reuse"]},
        "development_numbers_only": "Every number this cell produces is a DEV-2000-ADDED development number (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": f"owner decisions 228-234 and 238 (PROPOSED) ({nf.OWNER_DECISIONS}); the programme {nf.PROGRAMME}; module step 7 {nf.STEP7}; the v4g lock {nf.V4G_LOCK_RECORD}; the A2 read {nf.A2_READ}; the instrument {nf.INSTRUMENT}; decisions 25, 133, 139, 169, 190",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(package + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "smoke"):
        identity = ids[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            if is_fit:
                route = "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
            elif key == "smoke":
                route = "Shared core.flight.cli worker on this cell alone; outside the campaign plan and never scored."
            else:
                route = (f"Shared core.flight.cli campaign over {nf.CAMPAIGN_PLAN}, which flies the module OFF-arm replicate and then the composed arm "
                         "in ONE campaign (instrument rule 3), one official score per generation cell at finalize.")
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
                "expected_session_id": nf.SESSION,
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
                    "expected_output_sha256": facts["prepared_supplies"]["expected_output_digests"][key],
                    "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip (item E16); --allow-output-change must never be passed.",
                },
                "protocol_document": {"relpath": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "purpose": f"{identity['run_id']}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule if key == "arm" else "Structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before BOTH the composed arm and the replicate manifests are complete and sealed with one successful complete official slurp-slu-official score each, and the READ row is root countersigned.",
            }
            prefix = {"arm": "", "smoke": "smoke-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": nf.RECIPE_ID,
        "read_run_id": nf.READ_RUN_ID,
        "title": "NX Stage J round R5 -- the composed system (COMP-1b, lock v2.2 with v4g, review-off) on DEV-2000-ADDED against the sealed A2 flight, with the module OFF-arm replicate in the same chain",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "fit_run_id": arm["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": rep["run_id"], "attempt_id": rep["attempt_id"], "fit_run_id": rep["fit_run_id"],
                                   "role": "the module OFF arm (lock v2.1 + v3, full graph) flown in the SAME chain: the flight-to-flight offset instrument and the composed arm's same-chain base (vs-aa pass)",
                                   "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": nf.A2_ARM["run_id"], "attempt_id": nf.A2_ARM["attempt_id"],
                           "role": "the sealed A2 arm (COMP-1b, full graph, lock v2.0 + v3): the cross-flight comparator the registered claim is read against (vs-comparator pass); read beyond the replicate offset"},
            "offset_pair": {"left": {"run_id": nf.A2_AA["run_id"], "attempt_id": nf.A2_AA["attempt_id"], "role": "the sealed A2 in-chain A/A"},
                            "right": {"run_id": rep["run_id"], "attempt_id": rep["attempt_id"], "role": "the replicate"},
                            "pass": "offset-replicate-vs-a2aa"},
            "a2_aa": {"run_id": nf.A2_AA["run_id"], "attempt_id": nf.A2_AA["attempt_id"]},
        },
        "read_driver": {
            "command": f"bash {READ_DRIVER}",
            "passes": ["vs-aa (composed minus the in-chain replicate; same chain; CONTEXT, the whole composition against its base)",
                       "vs-comparator (composed minus the sealed A2 arm; cross-flight; THE REGISTERED CLAIM, read beyond the offset)",
                       "offset-replicate-vs-a2aa (replicate minus the sealed A2 A/A; the flight-to-flight offset)",
                       "composed-vs-a2aa (composed minus the sealed A2 A/A; cross-flight; context)"],
            "scorer": nf.SCORER,
            "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned",
        },
        "offline_columns": {
            "columns": {"v4g": {"normaliser": nf.NORMALISER, "guards": nf.V4G_GUARDS}},
            "applied_to": [],
            "applied_to_pools": [f"{nf.A2_ARM['run_id']}/{nf.A2_ARM['attempt_id']}", f"{nf.A2_AA['run_id']}/{nf.A2_AA['attempt_id']}",
                                 f"{rep['run_id']}/{rep['attempt_id']}"],
            "statistics": {"artifact_id": nf.V4_STATS_ARTIFACT_ID, "sha256": nf.V4_STATS_SHA256},
            "note": ("v4g (scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g) applied to the DELIVERED column of each v3 pool so the "
                     "composed arm (v4g at delivery) is compared with v4g(A2 arm), v4g(A2 A/A) and v4g(replicate) under ONE normaliser; "
                     "the contrasts are computed by scripts/analysis/nx_r5_v4g_contrast.py over the same scored vectors the apply script uses."),
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260915, "unit": "utterance cluster (paired)"},
        "steps": [
            "1. Refuse unless BOTH the composed-arm and the replicate manifests are COMPLETE at 1,000 rows with this registration's composed config hashes (the replicate's the module package's), sealed, each with one successful complete official slurp-slu-official score, and unless the READ row is root countersigned.",
            f"2. THE DELIVERY CHECK (gold-free): each cell's flown first-phase boundary selections must equal its own prepared supply (arm {facts['prepared_supplies']['expected_output_digests']['arm']}; replicate {facts['prepared_supplies']['expected_output_digests']['replicate']}). A mismatch is an engineering defect and closes the read.",
            "3. The structural check (gold-free): the composed arm made exactly 2 contacts per row (perception, solver), no Reviewer or Planner row, and delivered through saea-deliver-normalise-v4g on every row; the replicate's contacts per row against the A2 flight's.",
            "4. Passes vs-aa and vs-comparator through scripts/flights/read_paired_cell.sh (whole-utterance cluster, 10,000 draws, seed 20260915); passes offset-replicate-vs-a2aa and composed-vs-a2aa through stage3_paired_read.py in pair mode.",
            "5. Apply the offline v4g column to the A2 arm, the A2 A/A and the replicate; compare all columns under v4g (nx_r5_v4g_contrast.py) with per-scenario tables in natural-mixture and equal-stratum weightings.",
            "6. Cost table: contacts per row, prompt and completion tokens per row, GPU hours per 1,000 rows, per cell, with composed-minus-A2 and composed-minus-replicate.",
            "7. Apply the decision rule (protocol decision_rule_fixed_here) to the composed-minus-A2 SLU-F1 and intent contrasts beyond the replicate offset; every verdict carries the per-stratum table.",
            "8. Write the read under its own id; every number is a DEV-2000-ADDED development number, never a test claim.",
        ],
        "output": {"analysis_root": nf.ANALYSIS_ROOT},
        "boundary": "A development read on the DEV-2000-ADDED evaluation roster (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]
    draft = {
        "_draft_note": ("A DRAFT for root to mint on the data root with scripts/flights/nx/nx_r5_mint_receipt.py, which sets status 'decided', "
                        "stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing "
                        "while its status is not 'decided'. The replicate's receipt is the module package's own (mint it too)."),
        "schema": "saea-campaign-decision-v1",
        "decision_id": nf.DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm expressed as a consumption-module block (sealed-credit-system-policy-v1, operator context_application): COMP-1b on lock v2.2 (v4g at delivery), review-off, on DEV-2000-ADDED, with its four-row smoke; its in-chain replicate is the module OFF arm under the module package's own receipt.",
        "decision": (f"Fly the smoke, then the replicate and the composed arm in one campaign on DEV-2000-ADDED 1,000, ONLY after decision 238 is ruled and the R1 "
                     f"iteration-2 verdict is on file; read at official pooled SLU-F1 against the sealed A2 arm beyond the replicate offset, intent the guard, "
                     f"declared effect {expected:+.2f} pp, claims_benefit false, harm margin {nf.HARM_MARGIN_PP} pp."),
        "authorization_basis": f"Owner decisions 228-234 and, once ruled, 238; the programme {nf.PROGRAMME}; module step 7; decisions 25, 133, 139, 169, 190.",
        "antecedents": {
            "programme": {"path": nf.PROGRAMME, "sha256": sha_file(nf.PROGRAMME)},
            "step7": {"path": nf.STEP7, "sha256": sha_file(nf.STEP7)},
            "v4g_lock": {"path": nf.V4G_LOCK_RECORD, "sha256": sha_file(nf.V4G_LOCK_RECORD)},
            "a2_read": {"path": nf.A2_READ, "sha256": sha_file(nf.A2_READ)},
            "owner_decisions": {"path": nf.OWNER_DECISIONS, "sha256": sha_file(nf.OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. Development numbers only. No benefit is claimed (claims_benefit false).",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before decision 238 is ruled, the coordinator decides it, BOTH receipts are minted and the three cells are flipped",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any policy change outside the declared module block",
        ],
        "population": {"count": nf.ROWS, "split_identity_hash": arm["split_identity_hash"], "split_role": "dev", "roster": nf.ROSTER_ID, "test_contact_authorized": False, "fold_b_contact_authorized": False},
        "prepared_phase_supply": {"note": "each cell's own, minted at the flip (item E16); not pinned by this receipt"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in ("arm", "smoke")} | {"note": f"the values of the fragments exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": nf.SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    runs_line = "; ".join(f"`{ids[k]['run_id']}` / `{ids[k]['fit_run_id']}`" for k in ("arm", "smoke"))
    leaves_lines = "\n".join(f"- `{p}`" for p in diffs["arm_vs_module_arm"]["factor_paths"])
    readme = f"""# NX Stage J round R5: the composed read (review-off COMP-1b + v4g, lock v2.2) on DEV-2000-ADDED

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (programme `{nf.PROGRAMME}` C2 R5 and F1
Stage J; decision 238 PROPOSED in `{nf.OWNER_DECISIONS}`; module step 7 `{nf.STEP7}`); both new cells **held**. Nothing here
authorises a flight, a flip or an admission entry.

**Status.** {needs}

## 1. The design

Two cells fly in ONE campaign chain on DEV-2000-ADDED (1,000 rows each, one official score each) after a four-row smoke:

1. the in-chain REPLICATE `{nf.REPLICATE['experiment']}` (run `{rep['run_id']}`) -- the HELD module OFF-arm cell, reused AS
   REGISTERED (its own package `{nf.PARENT_PACKAGE}`, its own two DRAFT ledger rows, its own receipt). Module profile slurp, lock
   v2.1, every component off, full graph, delivery normaliser v3. Its recomposed config and protocol hashes equal the module
   package's registered ones (`registered-facts-v1.json`, `replicate_reuse`).
2. the COMPOSED arm `{arm['experiment']}` (run `{arm['run_id']}`, FIT `{arm['fit_run_id']}`; smoke `{smoke['experiment']}`, run
   `{smoke['run_id']}`): {the_composition}

The composed cell is the HELD module COMP-1b cell with exactly these policy leaves moved (compiler output, proven in
`registered-facts-v1.json` `composed_config_diffs`, `anything_else` empty):

{leaves_lines}

Decoding, knowledge stores, geometry (slurp-np4, session `{nf.SESSION}`) and the roster pins are the module cell's own.

## 2. The swap point (the R1 iteration-2 pick)

{swap_point}

## 3. Is the replicate request-identical to the sealed A2 flight? NO, in two named leaves

`python -B {PROOF_SCRIPT} --at m0 m6` holds (`ok: true`). The replicate differs from the sealed A2 in-chain A/A
(`{nf.A2_AA['run_id']}`) by exactly `{REVIEWER}` (the lock-v2.1 G5 Reviewer template, read no-harm / no-gain by `{nf.LOCK_NOTE_V2_1}`) and
`{RECALL_K}` (60 -> 8, a proven supply no-op at w_agree 0, output digest `d57ee9d6...`); it is not the sealed A2 ARM either (that arm
has COMP-1b on). So the replicate is the instrument of the sealed A2 flight's BASE arm, and replicate-minus-A2-A/A is the flight-to-flight
offset measured on the same roster and rows, including those two leaves. The composed arm is review-off, so the Reviewer template
never renders on it; the composed-minus-A2-arm contrast is read beyond that offset (`{nf.INSTRUMENT}` rule 3).

## 4. Budgets (by analogy with the review-off cells)

| item | composed arm | composed smoke | replicate (as registered) |
| --- | ---: | ---: | ---: |
| rows | {nf.ROWS:,} | {nf.SMOKE_ROWS} | {nf.ROWS:,} |
| contacts per row (exact) | {nf.CEILING} | {nf.CEILING} | 11 ceiling (A2 flew 4.07) |
| generation calls cap | {caps['generation_calls_cap']:,} | {smoke_caps['generation_calls_cap']} | {replicate_caps['generation_calls_cap']:,} |
| FIT endpoint cap (structural: rows x {nf.CEILING} x 4) | {caps['fit_endpoint_calls_cap']:,} | {smoke_caps['fit_endpoint_calls_cap']} | {replicate_caps['fit_endpoint_calls_cap']:,} |
| repeated speech-audio seconds cap | {caps['repeated_speech_audio_seconds_cap']:,} | {smoke_caps['repeated_speech_audio_seconds_cap']} | {replicate_caps['repeated_speech_audio_seconds_cap']:,} |
| planned GPU hours (FIT inclusive) | {caps['gpu_hours_fit_inclusive']} | {smoke_caps['gpu_hours_fit_inclusive']} | {replicate_caps['gpu_hours_fit_inclusive']} |

The chain total is the sum of the replicate's and the composed arm's caps. Measured A2 rates: the sealed arm 4,050 and the A/A 4,068
contacts per 1,000 rows (1.70 and 1.65 GPU-h); the composed arm's 2,000 contacts are exact.

## 5. The measurement and the three verdict meanings

`cross-flight-with-in-chain-replicate`, n = 1,000, primary official pooled SLU-F1 (`primary_metric_key: slu`), intent the guard,
`admission: no-harm`, `claims_benefit: false`, `harm_margin_pp {nf.HARM_MARGIN_PP}` (not tighter than the cross-flight sampling floor
{nf.OWN_NULL['h_slu']}), bar {nf.BAR_PP_N1000} pp. Declared `expected_effect_pp` **{expected:+.2f}**, honestly from the record:
review-off minus full graph {nf.REVIEW_OFF_VS_FULL_PP} [-5.33, +2.72] (N100 read, unresolved) plus the v4g delivered gain
{nf.V4G_LOCK_COLUMN_PP:+.2f} [+0.81, +2.33] (offline, TRAIN Fold B lock column; applies to the composed side only in the delivered
contrast). That is far under the bar, so the cell claims NO benefit: its claim is **no loss at about half the contacts plus the v4g
delivered gain**.

{decision_rule}

What the words mean here:

- **NOMINATED** -- composed minus the sealed A2 arm has an SLU-F1 CI95 lower bound above the replicate offset and a point at or above the
  bar, with intent unharmed. Not expected; it would be a surprise to replicate, and it is the only word that authorises talking about a gain.
- **NEUTRAL** -- both contrasts' CI95 lower bounds are within the {nf.HARM_MARGIN_PP} pp margin and nothing is resolved either way: the
  composition keeps the full graph's accuracy within what a cross-flight read can see at about half the calls. Still an efficiency result.
- **HARM** -- the CI95 upper bound of composed minus A2 (SLU-F1 or intent) is below -|offset|: a resolved loss beyond the flight offset.
  A read that is neither but whose lower bound is under -{nf.HARM_MARGIN_PP} pp is UNRESOLVED and is reported as such.

Declared exception to item D3, not hidden: {nf.TUNING_EXCEPTION} `tuning_roster` lists the rosters the composition's own constants were chosen on
(the construction pool, Fold A) and the `tuning_exception` field of the measurement block carries the v4 selection, because naming the read roster
in `tuning_roster` would make the launch gate report a blocking `tuning-read-overlap` that no registration can clear. The coordinator may rule
otherwise.

## 6. The read

`bash {READ_DRIVER}` (after both seals and the READ row's countersignature): passes `vs-aa` (composed minus the in-chain replicate;
context), `vs-comparator` (composed minus the sealed A2 arm; the registered claim), `offset-replicate-vs-a2aa` and `composed-vs-a2aa`;
the offline v4g columns on the A2 arm, the A2 A/A and the replicate; `scripts/analysis/nx_r5_v4g_contrast.py` for every cross-flight
contrast under v4g with per-scenario tables (natural-mixture and equal-stratum) and the cost table. Whole-utterance clusters, 10,000
draws, seed 20260915. The verdict word is the coordinator's.

## 7. What the coordinator does next

1. Rule decision 238 and wait for the R1 iteration-2 verdict; if the Solver template is delivered, take the swap in section 2 (needs a module step).
2. Root countersigns the DRAFT rows of THIS package (arm, arm FIT, smoke, smoke FIT) and of the module package for the replicate (run and FIT);
   the READ row after both seals.
3. Mint BOTH receipts: `python scripts/flights/nx/nx_r5_mint_receipt.py` (this package) and
   `python scripts/flights/module/module_comp1bdev_mint_receipt.py` (the replicate's, whose eligible list already names it).
4. `bash scripts/flights/nx/nx_r5_flip.sh` (loop form; re-pins smoke, replicate, composed arm to ONE converged HEAD; expected first-phase
   supply digests in `registered-facts-v1.json` `prepared_supplies`; the replicate re-pin may rewrite the module package's hashes if the
   instrument merges moved them -- it is the coordinator's flip).
5. `bash scripts/flights/nx/batch_chain_nx_r5.sh` (smoke, then the two-cell campaign, decision 77). Dry run before: `python -B scripts/flights/nx/nx_r5_dry_run.py`.
6. After both seals: countersign the READ row and run the read.

## 8. Open items

1. The replicate is the base-arm instrument of the sealed A2 flight (section 3), not an A2-ARM twin; the registered claim compares the composed
   arm with the A2 ARM beyond that offset. If the coordinator wants an A2-arm twin as the replicate, that is a different (COMP-1b ON, review-on)
   cell and a different chain.
2. Module step 7 left `CURRENT_LOCK` at v2.1. This package names `lock: v2.2` explicitly, so `CURRENT_LOCK` need not move. WHAT
   `scripts/checks/harness_admission_check.py` REPORTS (it reads `docs/receipts/harness-admission.json`, never experiment fragments): on the
   tree as registered, PASS (19 modules; no R5 entry exists, so the pair is not tested). Probed on a scratch copy of the receipt (nothing
   committed): the existing `module` entry with its ON arm replaced by the composed block (lock v2.2, review off) is REFUSED -- "switch.on
   composes onto lock 'v2.2'; the two arms of one module entry sit on ONE lock"; with the OFF arm ALSO on v2.2 it is refused twice -- the OFF
   arm "names lock 'v2.2'; the OFF arm of a 'module' entry names its carrier's CURRENT lock ('v2.1')" and the falsifier must name the OFF arm's
   lock -- so an R5 `module`-class admission entry needs `CURRENT_LOCK` moved to v2.2 (its OFF arm and falsifier cells then on v2.2, and the
   existing entry's v2.1 falsifier cells re-derived), a registration decision for the coordinator. The same composed block on lock v2.1
   (review off, v3) is ACCEPTED as an ON arm. Nothing in this package depends on that entry: it only matters if R5 NOMINATES.
3. The Solver-template swap needs a registered module step first (README section 2).
4. The v4 tuning exception above.
5. The replicate's two DRAFT ledger rows and its receipt live in the module package: both packages are countersigned and minted.
6. The structural contacts-per-row claim (2.0 against about 4.05) is arithmetic from the program and the A2 read, confirmed only at the read.

**Not authorised.** No flight before decision 238 is ruled and steps 1-4 hold; no re-flying of any sealed cell; no test, DEV-1000, Fold A or
Fold B contact; no policy change outside the declared block; no scope-rule or citation-contract on this block.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# NX Stage J round R5 (the composed read on DEV-2000-ADDED): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact (programme `{nf.PROGRAMME}` C2 R5;
decision 238 PROPOSED; module step 7). Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | {the_composition} |
| roster | DEV-2000-ADDED ({nf.ROSTER_ID}), 1,000 rows, split role dev, scorer {nf.SCORER} |
| in-chain replicate | `{rep['run_id']}` (the module OFF arm, lock v2.1 + v3), flown in the same campaign before the composed arm; registered in `{nf.PARENT_PACKAGE}` |
| comparator | the sealed A2 arm `{nf.A2_ARM['run_id']}`; offset instrument: the sealed A2 A/A `{nf.A2_AA['run_id']}` |
| margins | harm margin {nf.HARM_MARGIN_PP} pp; bar {nf.BAR_PP_N1000} pp; this roster's own null: h_intent {nf.OWN_NULL['h_intent']}, h_SLU {nf.OWN_NULL['h_slu']} |
| smoke | four rows, structural acceptance, never scored |
| runs | {runs_line} |
| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}`; replicate `{rep['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}`; replicate `{rep['protocol_hash']}` |
| status | {needs} |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Where the declared {expected:+.2f} pp comes from

Review-off minus full graph {nf.REVIEW_OFF_VS_FULL_PP} pp [-5.33, +2.72] (N100 read, unresolved, descriptive) plus the v4g delivered gain
{nf.V4G_LOCK_COLUMN_PP:+.2f} pp [+0.81, +2.33] (TRAIN Fold B lock column, offline; {nf.V4G_LOCK_RECORD}). Neither is a prior (owner
decision 139) and their sum is under the {nf.BAR_PP_N1000} pp bar, so no benefit is claimed.

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    appended = 0
    if args.append_ledger:
        ledger = rd(LEDGER)
        model_tool = (
            "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; NO native tool authority on any role; every "
            "policy block compiled by the consumption module from the declared block on lock v2.2 (delivery normaliser saea-deliver-normalise-v4g) "
            "with the Reviewer loop off; the Solver on the locked template"
        )
        inherited = (
            "DEV-2000-ADDED dev rows already exposed by the model-free speech-query encoding pass, the sealed B6 direct and plan arms, PLANr-DEV2000, "
            "CELL-3 and its twin, ROLL-3, cell A2 (arm and A/A) and the offline v4/v4g reads over the A2 pool; this cell adds no new row and opens "
            "no split. Prior exposure is inherited in full."
        )
        common = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by "
            f"the NX R5 registration (worktree {nf.WORKTREE}, branch {nf.BRANCH}); programme C2 R5; decision 238 PROPOSED. HELD until decision 238 "
            "is ruled and the R1 iteration-2 verdict is on file. This registration performs no contact and authorises none."
        )
        rows = []
        for key, fit_flag in (("arm", False), ("arm", True), ("smoke", False), ("smoke", True)):
            identity = ids[key]
            prefix = {"arm": "", "smoke": "smoke-"}[key]
            plan_name = f"{prefix}{'fit' if fit_flag else 'generation'}-plan-registered-v1.json"
            run_id = identity["fit_run_id"] if fit_flag else identity["run_id"]
            attempt = identity["fit_attempt_id"] if fit_flag else identity["attempt_id"]
            budget = identity["family_budget"]
            calls = budget["fit_endpoint_calls_cap"] if fit_flag else budget["generation_calls_cap"]
            what = {"arm": "NX Stage J round R5: the composed system (COMP-1b, lock v2.2 with v4g, Reviewer loop off), DEV-2000-ADDED",
                    "smoke": "Four-row form smoke of the NX R5 composed cell"}[key] + (
                " -- FIT spend identity, request envelopes only, no generation" if fit_flag else "")
            notes = (
                f"{common} Plan SHA256 {plan_shas[f'{key}:' + ('fit' if fit_flag else 'generation')]}; attempt {attempt}. Protocol hash "
                f"{identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session {nf.SESSION} (attach only). "
                f"READINESS HELD: root mints {nf.DECISION_RELPATH} (decision id {nf.DECISION_ID}) from the package's root-admission-draft-v1.json "
                "AND the module package's receipt for the replicate, then scripts/flights/nx/nx_r5_flip.sh re-pins with scripts/flights/repin_cell.py "
                "--set-ready, re-minting each cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this "
                f"row moves at the flip. THE COMPOSITION: {the_composition} Measurement declaration: "
                f"{measurement[identity['run_id']]['measurement_design']}, expected_effect_pp {measurement[identity['run_id']]['expected_effect_pp']}, "
                f"claims_benefit false, admission {'no-harm' if key == 'arm' else 'n/a (form proof)'}, primary_metric_key {'slu' if key == 'arm' else 'n/a'}. "
                f"Read: {nf.READ_RUN_ID} by {READ_DRIVER}. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
                "re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
            )
            rows.append(ledger_row([
                args.registered_at, run_id, "bounded-discovery-probe", what, model_tool,
                f"slurp DEV-2000-ADDED {identity['rows']}", "dev", identity["split_identity_hash"], "no", str(calls),
                str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), inherited,
                f"{package}/{plan_name}", notes,
            ]))
        rows.append(ledger_row([
            args.registered_at, nf.READ_RUN_ID, "model-free-check",
            ("The NX R5 composed read: the composed system against the sealed A2 arm beyond the in-chain replicate's offset (SLU-F1 primary, intent the guard, "
             "no-harm), against its same-chain replicate and the sealed A2 A/A as context, the offline v4g columns on the A2 and replicate pools, "
             "per-scenario tables in both weightings and the cost table."),
            "No model, tokenizer, encoder or server contact: scripts/flights/nx/nx_r5_read.sh over the sealed per-sample official slurp-slu-official scores and sealed receipts; offline v4g applied through the registered normaliser.",
            "slurp DEV-2000-ADDED 1000", "dev", arm["split_identity_hash"], "no", "0", "0", "0.0",
            "Reads only sealed manifests of this package, of the module package's replicate and of the sealed A2 flight; no new audio, gold or reference exposure beyond the inherited DEV-2000-ADDED reads.",
            f"{package}/analysis-recipe-v1.json",
            (f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package, so the pre-launch gate "
             f"scripts/checks/flight_registration_check.py finds it. Analysis root $SPEECHRL_DATA_DIR/{nf.ANALYSIS_ROOT}/<pass>/; recipe "
             f"{package}/analysis-recipe-v1.json (recipe_id {nf.RECIPE_ID}); driver {READ_DRIVER} refuses before any score is opened until root "
             "countersigns this row (after both seals). No utterance text, gold, transcript or model output is printed or persisted."),
        ]))
        header = (
            f"\n{nf.LEDGER_MARK} (programme C2 R5; decision 238 PROPOSED) -- the composed arm, its four-row smoke, their FIT identities and the READ row "
            "(DRAFT, root countersignature pending; HELD)\n\n"
            "Five unconsumed rows registered with the package. The replicate keeps the two DRAFT rows of the module package "
            "(SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1 and -FIT-V1). None of these rows is countersigned and none authorises a contact.\n\n"
            "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        )
        if nf.READ_RUN_ID in ledger:
            raise SystemExit(f"{LEDGER} already carries {nf.READ_RUN_ID}; refusing to append twice")
        io.open(LEDGER, "w", encoding="utf-8", newline="").write(ledger.rstrip("\n") + "\n" + header + "\n".join(rows) + "\n")
        appended = len(rows)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha,
                    **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in cells},
        "composed_config_diffs": {k: {kk: (vv if isinstance(vv, list) and len(vv) < 12 else len(vv)) for kk, vv in v.items()} for k, v in diffs.items()},
        "replicate_reuse": reuse,
        "ledger_rows_appended": appended,
        "expected_effect_pp": expected,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
