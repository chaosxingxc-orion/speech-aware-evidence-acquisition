#!/usr/bin/env python3
"""Write the registration package of the consumption module's first end-to-end cell -- COMP-1b as a module
block on lock v2.1, on DEV-2000-ADDED (migration step 6; owner decisions 195, 196, 204) -- from the committed
configs ``derive_slurp_module_comp1bdev_cells.py`` wrote.

Reads the arm, the smoke and the in-chain A/A (the module's OFF arm), recomposes every hash, re-runs the
module byte proof (``scripts/analysis/module_equivalence_proof.py``, case ``m6``) and PROVES from the composed
configs (``core.config.compose``):

* ``arm_vs_a2_arm`` / ``smoke_vs_a2_smoke``: the module cell differs from cell A2's flown arm / smoke by
  EXACTLY the lock-v2.1 Reviewer template leaf, plus the module's own declaration block, per-flight
  bookkeeping and the experiment fragment's own block;
* ``aa_vs_a2_aa``: the module's OFF arm differs from A2's in-chain A/A by exactly the Reviewer template and
  the recall k (A2's A/A flew k 60 at w_agree 0, a proven supply no-op; the lock is k 8), plus the same;
* ``arm_vs_aa``: the module arm differs from its own A/A by the two armed components' leaves ALONE
  (w_agree, k, the agreement table pin, the centroid key pin) plus the declaration's component states.

The expectation is DECLARED from the A2 read (``--expected-effect-pp``, its intent point; owner decision 139).
It writes the package documents (registered facts with the CANONICAL ``stage3_measurement``, protocol, six plan
documents, the analysis recipe, a draft decision receipt, README and preregistration) and, with
``--append-ledger``, seven DRAFT exposure rows (arm, arm FIT, A/A, A/A FIT, smoke, smoke FIT, READ).

Config and receipt-pinned bytes alone: no contact of any kind; flips nothing, mints nothing.

    python scripts/flights/module/write_slurp_module_comp1bdev_registration.py \\
        --package-dir docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1 \\
        --study-commit <sha> --registered-at <iso> --expected-effect-pp 4.60 [--append-ledger]
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
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "analysis"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import module_equivalence_proof as proof  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

CELLS = {
    "arm": "slurp-native-stage3-module-comp1b-dev2000-added-v1",
    "aa": "slurp-native-stage3-module-comp1b-aa-dev2000-added-v1",
    "smoke": "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1",
}
A2_CELLS = {
    "arm": "slurp-native-stage3-comp1b-dev2000-added-v1",
    "aa": "slurp-native-stage3-comp1-aa-dev2000-added-v1",
    "smoke": "slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1",
}
A2_PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1"
A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"
A2_READ_LINE = "intent +4.60 pp CI95 [+2.58, +6.73], official SLU-F1 +0.53 pp [-1.04, +2.09] against the in-chain A/A (A2 REPLICATED and ADMITTED, lock v2.0 bytes)"
LOCK_NOTE = "docs/results/2026-09-30-slurp-v2-1-lock-v1.md"
DESIGN = "docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-dev2000-added-generation-v1"
A2_RUNS = {"arm": "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1", "aa": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1"}
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official"
ROSTER_ID = "SLURP-DEV-2000-ADDED-V1"
PACKAGE_NAME = "slurp-stage3-module-comp1b-dev2000-added-v1"
DECISION_ID = "slurp-stage3-module-comp1b-dev2000-added-admission-v1"
DECISION_RELPATH = f"coordination/{PACKAGE_NAME}/root-admission-v1.json"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json"
READ_RUN = "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
ANALYSIS_ROOT = f"analysis/{READ_RUN}"
READ_DRIVER = "scripts/flights/read_paired_cell.sh"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
DERIVE_SCRIPT = "scripts/flights/module/derive_slurp_module_comp1bdev_cells.py"
PROOF_SCRIPT = "scripts/analysis/module_equivalence_proof.py"
LEDGER = "docs/exposure-ledger.md"
AA_SUPPLY_OUTPUT = "d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19"
ARM_SUPPLY_OUTPUT = "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"
SMOKE_SUPPLY_OUTPUT = "d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083"
OWN_NULL = {"h_intent": 1.1520, "h_slu": 1.2525, "n": 1000, "measured_offset_slu_pp": -0.25,
            "source": INSTRUMENT + " section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"}
BAR_PP_N1000 = 2.60
TUNING_ROSTER = "slurp-train-construction-pool-agree-kprobe-r01-excluded"

BOUNDARY = "knowledge_stores.intent-boundaries.phase_supply.perception"
REVIEWER = "phase_material.reviewer.instruction_template"
MODULE_BLOCK = "native_episode.consumption_module."
COMPONENT_PATHS = (f"{BOUNDARY}.rank_weights.w_agree", f"{BOUNDARY}.k", f"{BOUNDARY}.agreement_source.",
                   f"{BOUNDARY}.facet_source.")
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
    parser.add_argument("--package-dir", required=True)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--expected-effect-pp", required=True, type=float)
    parser.add_argument("--branch", default="fable/module6")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-module6")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    package = args.package_dir.rstrip("/").replace("\\", "/")
    prereg = package + "-preregistration.md"
    expected = round(args.expected_effect_pp, 2)
    if expected < BAR_PP_N1000:
        raise SystemExit(f"expected_effect_pp {expected} is under the {BAR_PP_N1000} pp cross-flight bar at n = 1,000")

    # ---- identities --------------------------------------------------------
    ids: dict[str, dict] = {}
    composed: dict[str, object] = {}
    documents: dict[str, dict] = {}
    for key, experiment in CELLS.items():
        document, cell, comp = composed_of(experiment)
        documents[key], composed[key] = document, comp
        split = document["population"]["split_identity_hash"]
        fit = comp.values["native_contact_fit"]
        own_supply = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("phase-supply-v1.json"))
        perception = comp.values["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
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
            "module": {"module_id": block["module_id"], "lock": block["lock"],
                       "armed": [c["component_id"] for c in block["components"] if c["state"] != "off"]},
            "boundary": {k: perception.get(k) for k in ("k", "tau", "rank_weights", "fuse_coverage")},
            "policy": comp.values["policy"], "reviewer_template": comp.values["phase_material"]["reviewer"]["instruction_template"],
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

    # ---- the byte proofs --------------------------------------------------------
    m6 = proof.run_m6(REPO_ROOT)
    m0 = proof.run_case("m0", REPO_ROOT)
    if not (m6["ok"] and m0["ok"]):
        raise SystemExit("the module byte proof (m0 / m6) does not hold; refusing to register")
    diffs: dict[str, dict] = {}
    for key, allowed in (("arm", (REVIEWER,)), ("smoke", (REVIEWER,)), ("aa", (REVIEWER, f"{BOUNDARY}.k"))):
        a2_doc, _, a2 = composed_of(A2_CELLS[key])
        diff = classify_diff(a2.values, composed[key].values, set(documents[key]) | set(a2_doc), allowed=allowed)
        if diff["anything_else"]:
            raise SystemExit(f"{key}_vs_a2: differs beyond the lock-v2.1 pin, the declaration and bookkeeping: {diff['anything_else']}")
        if sorted(diff["factor_paths"]) != sorted(allowed):
            raise SystemExit(f"{key}_vs_a2: the expected leaves did not move exactly: {diff['factor_paths']}")
        diffs[f"{key}_vs_a2_{key}"] = diff
    arm_vs_aa = classify_diff(composed["aa"].values, composed["arm"].values, set(documents["arm"]) | set(documents["aa"]),
                              allowed=COMPONENT_PATHS)
    if arm_vs_aa["anything_else"]:
        raise SystemExit(f"arm_vs_aa: differs beyond the two components: {arm_vs_aa['anything_else']}")
    for path in COMPONENT_PATHS:
        if not [k for k in arm_vs_aa["factor_paths"] if k == path or (path.endswith(".") and k.startswith(path))]:
            raise SystemExit(f"arm_vs_aa: {path} did not move")
    diffs["arm_vs_aa"] = arm_vs_aa
    for field in ("population", "split_id"):
        if documents["arm"].get(field) != documents["aa"].get(field):
            raise SystemExit(f"the arm's {field} is not the A/A's")

    caps, smoke_caps = ids["arm"]["family_budget"], ids["smoke"]["family_budget"]
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
            "slu_guard_h": OWN_NULL["h_slu"],
            "roster": f"DEV-2000-ADDED ({ROSTER_ID}, split identity {ids['arm']['split_identity_hash']})",
            "tuning_roster": TUNING_ROSTER,
            "read_roster": ROSTER_ID,
            "note": (
                f"Migration step 6: COMP-1b as a module block on lock v2.1. expected_effect_pp {expected} is the A2 read's "
                f"intent point estimate ({A2_READ}: {A2_READ_LINE}); owner decision 139: a number measured on a sealed read "
                "is not a prior. It was measured on lock v2.0 bytes; this cell's base is lock v2.1, whose one moved pin "
                f"(the G5 Reviewer template) read no harm and no gain ({LOCK_NOTE}), and its in-chain A/A is the module's "
                "OFF arm on the same lock, so the contrast is the two components alone. The SLU-F1 guard is this roster's "
                f"own null h_SLU {OWN_NULL['h_slu']} (h_intent {OWN_NULL['h_intent']}). The expectation comes from a read "
                "on THIS roster (A2), so a flight of this cell is a same-roster re-flight of admitted bytes under the "
                "module, not an independent replication; nothing in the cell was tuned on DEV-2000-ADDED (the vote pool and "
                "the centroid key are TRAIN construction-pool artifacts)."
            ),
        },
        ids["aa"]["run_id"]: {
            "claim": "nominated",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
            "primary_metric_key": "intent",
            "replicate_run_id": ids["arm"]["run_id"],
            "rows": 1000,
            "tuning_roster": "none",
            "read_roster": ROSTER_ID,
            "note": (
                "The in-chain A/A is the INSTRUMENT, not a claim: the module's OFF arm (every component off) on lock v2.1, "
                "which compiles byte for byte to the lock-v2.1 policy blocks on this roster. It is also the first measured "
                "lock-v2.1 A/A. Its expected effect is zero by construction."
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
        "The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) compiled onto lock v2.1 "
        "(owner decision 204: the v2.0 lock with ONE pin moved, the Reviewer template "
        "probes/slurp_native_role_reviewer_v1_g5_v1.txt) with COMP-1b's two components ON -- agree-vote-seed (w_agree 1.0, "
        "recall k 60, delivered 8-1-8, THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and "
        "centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- and every other catalogued component OFF. "
        "Every policy block is the compiler's output; the roster pins are DEV-2000-ADDED's own."
    )
    needs_to_fly = (
        "This cell does NOT need to fly for the module's end-to-end proof: the byte proof (m6) shows its composed "
        "policy blocks equal cell A2's flown arm bytes except the one lock-v2.1 Reviewer pin, and its A/A equals the "
        "lock-v2.1 bytes. What a flight would add is (a) the first measured lock-v2.1 A/A on DEV-2000-ADDED and (b) a "
        "same-roster re-flight of the admitted COMP-1b bytes under the module on lock v2.1. Whether that is worth about "
        "3.4 GPU-h is the coordinator's decision."
    )
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": ("Every model-free fact the module cell's registration rests on, and the CANONICAL stage3_measurement "
                  "block for the arm, the in-chain A/A and the smoke."),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "28/86": "development numbers only; never a test claim",
            "133": "intent primary, official SLU-F1 the guard",
            "139": "no prior; a number derived from a measured read is not a prior",
            "169": "the module-all-off lock layer is the in-chain A/A comparator of every composed read",
            "190": "primary_metric_key and the tuning_roster / read_roster split (item D3)",
            "195/196": "one module carries every component; carrier-agnostic",
            "198": "A2 = COMP-1b on DEV-2000-ADDED (the admitting read of the two components)",
            "204": "lock v2.1 = v2.0 + the G5 Reviewer template; the base of every cell registered after A2 seals",
        },
        "rows": 1000,
        "the_basis": f"The A2 read ({A2_READ}): {A2_READ_LINE}.",
        "the_composition": the_composition,
        "does_this_cell_need_to_fly": needs_to_fly,
        "stage3_measurement": measurement,
        "cells": {key: {k: v for k, v in ids[key].items() if k not in ("own_supply_requirement", "family_budget")} for key in CELLS},
        "module_byte_proof": {
            "script": {"relpath": PROOF_SCRIPT, "sha256": sha_file(PROOF_SCRIPT)},
            "command": f"python -B {PROOF_SCRIPT} --at m0 m6",
            "m0": [{k: r[k] for k in ("experiment", "lock", "module_composed_hash", "composed_identical")} for r in m0["results"]],
            "m6": [{k: r[k] for k in ("cell", "experiment", "lock", "armed", "module_block_sha256", "own_composed_hash",
                                      "module_composed_hash", "composed_identical",
                                      "module_policy_on_a2_roster_differing_paths", "reviewer_template")}
                   for r in m6["results"]],
            "note": ("m0: the all-off block on lock v2.1 composes to cell G5's flown hashes (the v2.1 bytes), and with no "
                     "lock key to the v2.0 lock's. m6: each module cell's own block compiles to its own composed hash; "
                     "compiled onto A2's own fragments it differs from A2's policy blocks at exactly "
                     "phase_material.reviewer.instruction_template (the A/A also at the recall k, 60 -> 8)."),
        },
        "composed_config_diffs": {
            **diffs,
            "note": ("Each entry flattens two composed configs (core.config.compose). The module cell vs cell A2 = the "
                     "lock-v2.1 Reviewer pin alone (the A/A also the recall k) plus the module declaration, bookkeeping "
                     "and the experiment fragment; the module arm vs its A/A = the two components' leaves alone. "
                     "anything_else is empty or this writer refuses."),
            "derive_script": {"relpath": DERIVE_SCRIPT, "sha256": sha_file(DERIVE_SCRIPT)},
        },
        "prepared_supplies": {
            "note": "each cell's own, minted model-free at the flip (item E16); never inherited",
            "expected_output_digests": {"arm": ARM_SUPPLY_OUTPUT, "aa": AA_SUPPLY_OUTPUT, "smoke": SMOKE_SUPPLY_OUTPUT},
            "why": ("the lock-v2.1 pin acts only on the Reviewer; the arm's and smoke's first-phase sources are A2's own, "
                    "and the A/A's are the sealed DEV plan arm's (A2's A/A reproduced d57ee9d6... at k 60 / w_agree 0)"),
        },
        "budget_arithmetic": {
            "family_budget": caps, "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,000 rows x 11 contacts per row (1 + 2 x (1 + 3 + 1) at max_revisions 1), run-cumulative",
                "the lock-v2.1 Reviewer template removes tokens, never contacts",
                "one official complete slurp-slu-official score per generation cell over the complete 1,000-row manifest, never sharded",
            ],
        },
        "reported_beside": {"note": "CONTEXT ONLY. None of these is this cell's bar.",
                            "a2": {"arm": A2_RUNS["arm"], "aa": A2_RUNS["aa"], "read": A2_READ},
                            "dev_plan_arm": COMPARATOR_RUN, "own_null": OWN_NULL},
        "authority_relpaths": [OWNER_DECISIONS, DESIGN, A2_READ, LOCK_NOTE, A2_PACKAGE + "/README.md", INSTRUMENT],
        "prohibitions": [
            "No flight before the coordinator decides it is needed, root countersigns the rows, mints the decision receipt and the three cells are flipped in one converged cycle.",
            "No re-flying of any sealed cell; no test, DEV-1000 or Fold B contact.",
            "No component beyond the declared block; no k, tau, fuse_coverage, w_prior, store, release, snapshot, roster or geometry change outside the compiler.",
            "No paper-scale profile. --allow-output-change is never passed.",
        ],
    }
    facts_sha = wjson(package + "/registered-facts-v1.json", facts)

    decision_rule = (
        "Read against the in-chain A/A (the module's OFF arm on lock v2.1) flown in the same campaign. PRIMARY: intent "
        "accuracy (scenario_action exact), paired per utterance, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 "
        f"(slurp-slu-official) non-inferior at this roster's own null (h_SLU {OWN_NULL['h_slu']}). REPLICATED: the intent CI95 "
        f"lower bound above zero, the point at or above the {BAR_PP_N1000} pp cross-flight bar at n = 1,000, AND the guard "
        f"holds. NEUTRAL: both guards non-inferior at the own null (h_intent {OWN_NULL['h_intent']} / h_SLU {OWN_NULL['h_slu']}) "
        "without a replicated gain. HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the "
        "per-stratum tables in both weightings. The A/A vs the sealed A2 A/A is reported beside, CONTEXT ONLY (the lock-v2.1 "
        "pin plus the recall-k no-op)."
    )
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-module-comp1b-dev2000-added-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_HELD_AWAITING_COORDINATOR_DECISION",
        "the_question": ("Does the consumption module, carrying COMP-1b on lock v2.1, deliver the intent gain the A2 read "
                         "admitted, against its own OFF arm in the same chain, with official SLU-F1 non-inferior?"),
        "the_composition": the_composition,
        "does_this_cell_need_to_fly": needs_to_fly,
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "policy", "module")} for key in CELLS},
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"],
                                                    "module_byte_proof": facts["module_byte_proof"]},
        "development_numbers_only": "Every number this cell produces is a DEV-2000-ADDED development number (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.",
        "authority": f"owner decisions 195, 196, 204 ({OWNER_DECISIONS}); the design {DESIGN} section 4 step 6; the A2 read {A2_READ}; the lock record {LOCK_NOTE}; the instrument {INSTRUMENT}; decisions 25, 133, 139, 169, 190",
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
                route = f"Shared core.flight.cli campaign over {CAMPAIGN_PLAN}, which flies the in-chain A/A and then the module arm in ONE campaign (instrument rule 3), one official score per generation cell at finalize."
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
                "purpose": f"{identity['run_id']}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule if key == "arm" else "The in-chain A/A (the module's OFF arm on lock v2.1): the within-chain null the arm is read at." if key == "aa" else "Structural form proof only: no score and no read."),
                "quality_read_gate": "No task-quality read before BOTH the arm and the A/A manifests are complete and sealed with one successful complete official slurp-slu-official score each, and the READ row is root countersigned.",
            }
            prefix = {"arm": "", "aa": "aa-", "smoke": "smoke-"}[key]
            plan_shas[f"{key}:{kind}"] = wjson(f"{package}/{prefix}{kind}-plan-registered-v1.json", plan)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-module-comp1b-dev2000-added-paired-analysis-v1",
        "read_run_id": READ_RUN,
        "title": "The consumption module's first end-to-end cell -- COMP-1b as a module block on lock v2.1, DEV-2000-ADDED, against its in-chain A/A (the module's OFF arm)",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": ids["arm"]["run_id"], "attempt_id": ids["arm"]["attempt_id"], "fit_run_id": ids["arm"]["fit_run_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": ids["aa"]["run_id"], "attempt_id": ids["aa"]["attempt_id"], "fit_run_id": ids["aa"]["fit_run_id"], "role": "the within-chain null the delta is read at (the module's OFF arm on lock v2.1)", "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "the sealed DEV plan arm (lock v2.0 bytes), context beside the A/A, never the bar"},
        },
        "read_driver": {
            "command": f"bash {READ_DRIVER} {package}",
            "passes": ["vs-aa (gating)", "vs-comparator (context only)"],
            "scorer": SCORER,
            "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned",
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260930, "unit": "utterance cluster (paired)"},
        "steps": [
            "1. Refuse unless BOTH the arm and the A/A manifests are COMPLETE at 1,000 rows with this registration's composed config hashes, sealed, each with one successful complete official slurp-slu-official score, and unless the READ row is root countersigned.",
            f"2. THE DELIVERY CHECK (gold-free): each cell's flown first-phase boundary selections must equal its own prepared supply (A/A output {AA_SUPPLY_OUTPUT}; arm {ARM_SUPPLY_OUTPUT}). A mismatch is an engineering defect and closes the read.",
            f"3. Primary: intent accuracy paired per utterance against the in-chain A/A, 10,000 draws, seed 20260930. Guard: official pooled SLU-F1. Apply the protocol's rule at h_intent {OWN_NULL['h_intent']} / h_SLU {OWN_NULL['h_slu']} against the declared expected_effect_pp {expected} and the {BAR_PP_N1000} pp bar.",
            "4. Entity FP / TP / FN against the A/A, with the zero-gold-row emission count.",
            f"5. CONTEXT ONLY: the module arm vs the sealed A2 arm ({A2_RUNS['arm']}) and the module A/A vs the sealed A2 A/A ({A2_RUNS['aa']}) -- the lock-v2.1 pin's cross-flight footprint on this roster; never a gate.",
            "6. Per-scenario tables in both weightings (natural-mixture and equal-stratum) and the recording-channel split.",
            "7. Write the read under its own id; every number is a DEV-2000-ADDED development number, never a test claim.",
        ],
        "output": {"analysis_root": ANALYSIS_ROOT},
        "boundary": "A development read on the DEV-2000-ADDED evaluation roster (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(package + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["arm"]["run_id"], ids["arm"]["fit_run_id"], ids["aa"]["run_id"], ids["aa"]["fit_run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit_run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/module/module_comp1bdev_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 composed system-policy arm expressed as a consumption-module block (sealed-credit-system-policy-v1, operator context_application): COMP-1b on lock v2.1 on DEV-2000-ADDED, with the module's OFF arm as its in-chain A/A and a four-row smoke.",
        "decision": f"Fly the module cell only if the coordinator decides the byte proof is not enough: the smoke, then the in-chain A/A and the module arm in one campaign on DEV-2000-ADDED 1,000; read at intent primary against the declared {expected} pp with official SLU-F1 the guard at h_SLU {OWN_NULL['h_slu']}.",
        "authorization_basis": f"Owner decisions 195, 196, 204; the A2 read {A2_READ}; decisions 25, 133, 139, 169, 190.",
        "antecedents": {
            "a2_read": {"path": A2_READ, "sha256": sha_file(A2_READ)},
            "lock_record": {"path": LOCK_NOTE, "sha256": sha_file(LOCK_NOTE)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": prereg, "sha256": None},
            "readiness_readme": {"path": package + "/README.md", "sha256": None},
            "protocol": {"path": package + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": package + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": package + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "smoke": smoke_caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim. Development numbers only. claim: nominated.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the coordinator decides it, the receipt is minted and the three cells are flipped",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any policy change outside the declared module block",
        ],
        "population": {"count": 1000, "split_identity_hash": ids["arm"]["split_identity_hash"], "split_role": "dev", "roster": ROSTER_ID, "test_contact_authorized": False, "fold_b_contact_authorized": False},
        "prepared_phase_supply": {"note": "each cell's own, minted at the flip (item E16); not pinned by this receipt"},
        "registered_hashes": {key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS} | {"note": f"the values of the fragments exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["arm"]["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_sha = wjson(package + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    runs_line = "; ".join(f"`{ids[k]['run_id']}` / `{ids[k]['fit_run_id']}`" for k in CELLS)
    m6_lines = "\n".join(
        f"| {r['cell']} | `{r['experiment']}` | `{r['module_composed_hash'][:16]}...` | {r['composed_identical']} | "
        f"{', '.join('`' + p + '`' for p in r['module_policy_on_a2_roster_differing_paths'])} |"
        for r in m6["results"]
    )
    readme = f"""# The consumption module's first end-to-end cell: COMP-1b as a module block on lock v2.1 (DEV-2000-ADDED)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (migration step 6 of
`{DESIGN}`; owner decisions 195, 196 and 204); all three cells **held**. Nothing here authorises a flight, a flip or an
admission entry.

**Does it need to fly?** {needs_to_fly}

**Why.** Migration step 6 re-expresses new registrations as module blocks. The first composed component list is COMP-1b
(`agree-vote-seed` + `centroid-boundary-key`), admitted by the A2 read ([`{A2_READ}`](../../../{A2_READ})):
{A2_READ_LINE}. Lock v2.1 ([`{LOCK_NOTE}`](../../../{LOCK_NOTE})) is the base of every cell registered after A2 sealed.

**What it is.** {the_composition} Each cell's baseline fragment DECLARES `native_episode.consumption_module`; the loader
(`rails.native_episode_config`) refuses the config unless its policy blocks are exactly what the block compiles to.
Derived by `{DERIVE_SCRIPT}`.

**The byte proof (AT-M6, `python -B {PROOF_SCRIPT} --at m0 m6`).** Each cell's own block compiles to its own composed
hash; compiled onto cell A2's own fragments, it differs from A2's policy blocks at exactly these leaves:

| cell | experiment | composed hash | rebuilt == own | policy leaves differing from the A2 counterpart |
| --- | --- | --- | --- | --- |
{m6_lines}

The full composed-config diffs against A2 (`registered-facts-v1.json`, `composed_config_diffs`) add only the module
declaration block, bookkeeping (`native_contact_fit` ids, `prepared_phase_supply`, `what_this_is`, the smoke's
`fragment_kind`) and the experiment fragment's own block. The A/A's recall k moves 60 -> 8 because A2's A/A carried k 60
at w_agree 0 (a proven supply no-op, digest `d57ee9d6...`) and the module's OFF arm is the lock (k 8). AT-M0 now targets
lock v2.1 (cell G5's flown hashes) and keeps the v2.0 case beside it.

**In-chain A/A.** `{CELLS['aa']}` = the module's OFF arm (every component off) on lock v2.1 -- the first lock-v2.1 A/A;
the campaign plan `{CAMPAIGN_PLAN}` flies it and then the arm (instrument rule 3).

**Measurement.** `cross-flight-with-in-chain-replicate`, n = 1,000, intent primary (`primary_metric_key: intent`),
`claims_benefit: true`, claim `nominated`, `expected_effect_pp` **{expected}** (the A2 read's intent point, measured on
lock v2.0 bytes), official SLU-F1 the guard at this roster's own null h_SLU {OWN_NULL['h_slu']} (h_intent
{OWN_NULL['h_intent']}); bar about {BAR_PP_N1000} pp at n = 1,000.

**Runs.** {runs_line}. READ `{READ_RUN}`.

**If the coordinator decides to fly it.** (1) Root countersigns the seven DRAFT rows (arm, arm FIT, A/A, A/A FIT, smoke,
smoke FIT, READ) and mints `{DECISION_RELPATH}` with `scripts/flights/module/module_comp1bdev_mint_receipt.py` (six
eligible run ids). (2) `scripts/flights/module/module_comp1bdev_flip.sh` re-pins smoke, A/A and arm until the package
converges at one HEAD; each re-minted supply must reproduce its expected output digest. (3)
`scripts/flights/module/batch_chain_module_comp1bdev.sh` queues the smoke then the A/A + arm campaign on the np4 session
(decision 77). (4) After both seals the READ row is countersigned and `bash scripts/flights/module/module_comp1bdev_read.sh`
reads it.

**Not authorised.** No flight before the coordinator's decision and steps 1-2; no re-flying of any sealed cell; no test,
DEV-1000 or Fold B contact; no policy change outside the declared block.
"""
    readme_sha = wr(package + "/README.md", readme)

    prereg_text = f"""# The consumption module's first end-to-end cell (COMP-1b as a module block on lock v2.1, DEV-2000-ADDED): preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact (migration step 6; owner
decisions 195, 196, 204). Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| composition | {the_composition} |
| roster | DEV-2000-ADDED ({ROSTER_ID}), 1,000 rows, split role dev, scorer {SCORER} |
| in-chain A/A | `{ids['aa']['run_id']}` (the module's OFF arm on lock v2.1), flown in the same campaign before the arm |
| margins | this roster's own null: h_intent {OWN_NULL['h_intent']}, h_SLU {OWN_NULL['h_slu']} |
| smoke | four rows, structural acceptance, never scored |
| runs | {runs_line} |
| composed config hashes | arm `{ids['arm']['composed_config_hash']}`; A/A `{ids['aa']['composed_config_hash']}`; smoke `{ids['smoke']['composed_config_hash']}` |
| protocol hashes | arm `{ids['arm']['protocol_hash']}`; A/A `{ids['aa']['protocol_hash']}`; smoke `{ids['smoke']['protocol_hash']}` |
| does it need to fly | {needs_to_fly} |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Where the declared {expected} pp comes from

The A2 read, {A2_READ}: {A2_READ_LINE}. It was measured on this roster and on lock v2.0 bytes; a flight of this cell is a
same-roster re-flight of those bytes under the module on lock v2.1, not an independent replication.

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = wr(prereg, prereg_text)

    appended = 0
    if args.append_ledger:
        ledger = rd(LEDGER)
        model_tool = (
            "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted DEV-2000-ADDED speech packets; NO native tool authority on "
            "any role; every policy block compiled by the consumption module from the declared block on lock v2.1 (the "
            "Reviewer on the G5 template); the Solver on the locked plan's non-cited program on every cell"
        )
        inherited = (
            "DEV-2000-ADDED dev rows already exposed by the model-free speech-query encoding pass, the sealed B6 direct and plan "
            "arms, PLANr-DEV2000, CELL-3 and its twin, ROLL-3 and cell A2 (arm and A/A); this cell adds no new row and opens no "
            "split. Prior exposure is inherited in full."
        )
        common = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the module step-6 registration (worktree {args.worktree}, branch {args.branch}); owner "
            "decisions 195, 196, 204. HELD: the cell need not fly if the byte proof holds (the coordinator decides). This "
            "registration performs no contact and authorises none."
        )
        rows = []
        for key, fit_flag in (("arm", False), ("arm", True), ("aa", False), ("aa", True), ("smoke", False), ("smoke", True)):
            identity = ids[key]
            prefix = {"arm": "", "aa": "aa-", "smoke": "smoke-"}[key]
            plan_name = f"{prefix}{'fit' if fit_flag else 'generation'}-plan-registered-v1.json"
            run_id = identity["fit_run_id"] if fit_flag else identity["run_id"]
            attempt = identity["fit_attempt_id"] if fit_flag else identity["attempt_id"]
            budget = identity["family_budget"]
            calls = budget["fit_endpoint_calls_cap"] if fit_flag else budget["generation_calls_cap"]
            what = {"arm": "The consumption module's first end-to-end cell: COMP-1b as a module block on lock v2.1, DEV-2000-ADDED",
                    "aa": "The in-chain A/A of the module cell: the module's OFF arm on lock v2.1 (the first lock-v2.1 A/A), DEV-2000-ADDED",
                    "smoke": "Four-row form smoke of the module cell"}[key] + (
                " -- FIT spend identity, request envelopes only, no generation" if fit_flag else "")
            notes = (
                f"{common} Plan SHA256 {plan_shas[f'{key}:' + ('fit' if fit_flag else 'generation')]}; attempt {attempt}. Protocol hash "
                f"{identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session {SESSION} (attach only). "
                f"READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) from the package's root-admission-draft-v1.json "
                "with the six eligible run ids, then scripts/flights/module/module_comp1bdev_flip.sh re-pins with scripts/flights/repin_cell.py "
                "--set-ready, re-minting each cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every "
                f"hash in this row moves at the flip. THE COMPOSITION: {the_composition if key != 'aa' else 'the module OFF arm (every component off) on lock v2.1, compiling to the lock-v2.1 bytes.'} "
                f"Measurement declaration: {measurement[identity['run_id']]['measurement_design']}, expected_effect_pp "
                f"{measurement[identity['run_id']]['expected_effect_pp']}, claims_benefit {'true' if key == 'arm' else 'false'}, "
                f"primary_metric_key intent, own null h_intent {OWN_NULL['h_intent']} / h_SLU {OWN_NULL['h_slu']}, official SLU-F1 ({SCORER}) the guard. "
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
            "The module cell's read: COMP-1b as a module block on lock v2.1 against its in-chain A/A (the module's OFF arm; gating; intent primary, official SLU-F1 the guard, at the own null h_intent 1.1520 / h_SLU 1.2525 against the declared expected_effect_pp), entity FP/TP/FN and zero-gold emission, per-scenario tables in both weightings; the sealed A2 cells and the DEV plan arm as context only.",
            "No model, tokenizer, encoder or server contact: scripts/flights/read_paired_cell.sh over the sealed per-sample official slurp-slu-official scores and sealed receipts.",
            "slurp DEV-2000-ADDED 1000", "dev", ids["arm"]["split_identity_hash"], "no", "0", "0", "0.0",
            "Reads only sealed manifests of this package and its registered comparators; no new audio, gold or reference exposure.",
            f"{package}/analysis-recipe-v1.json",
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package, so the pre-launch gate scripts/checks/flight_registration_check.py finds it. Analysis root $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/; recipe {package}/analysis-recipe-v1.json (recipe_id {recipe['recipe_id']}); driver {READ_DRIVER} refuses before any score is opened until root countersigns this row (after both seals). No utterance text, gold, transcript or model output is printed or persisted.",
        ]))
        header = (
            "\n## The consumption module's first end-to-end cell: COMP-1b as a module block on lock v2.1, DEV-2000-ADDED "
            "(migration step 6; owner decisions 195, 196, 204) -- the arm, its in-chain A/A (the module's OFF arm), the "
            "four-row smoke, their FIT identities and the READ row (DRAFT, root countersignature pending; HELD)\n\n"
            "Seven unconsumed rows registered with the package. The cell need not fly if the module byte proof holds; the "
            "coordinator decides. None of these rows is countersigned and none authorises a contact.\n\n"
            "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
        )
        if READ_RUN in ledger:
            raise SystemExit(f"{LEDGER} already carries {READ_RUN}; refusing to append twice")
        io.open(LEDGER, "w", encoding="utf-8", newline="").write(ledger.rstrip("\n") + "\n" + header + "\n".join(rows) + "\n")
        appended = len(rows)

    print(json.dumps({
        "package": package,
        "written": {package + "/README.md": readme_sha, package + "/registered-facts-v1.json": facts_sha, package + "/protocol-registered-v1.json": protocol_sha,
                    package + "/analysis-recipe-v1.json": recipe_sha, package + "/root-admission-draft-v1.json": draft_sha, prereg: prereg_sha, **{f"{package}/{k}": v for k, v in plan_shas.items()}},
        "identities": {key: {k: ids[key][k] for k in ("run_id", "fit_run_id", "composed_config_hash", "protocol_hash", "rows")} for key in CELLS},
        "composed_config_diffs": {k: {kk: (vv if isinstance(vv, list) and len(vv) < 6 else len(vv)) for kk, vv in v.items()} for k, v in diffs.items()},
        "ledger_rows_appended": appended,
        "expected_effect_pp": expected,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
