#!/usr/bin/env python3
"""Write the SLOTFILL registration package from the committed configs.

Item SLOTFILL -- the dispatcher keeps every serving slot loaded (owner decision 159, a
row-127 engineering-base no-harm item). Reads the three derived fragments and the model-free
proof summary, recomposes every cell's own hashes, PROVES the composed-config diff against the
locked PLAN cells is the ONE key (``dispatch``) plus per-flight bookkeeping for the arm and the
smoke and bookkeeping alone for the in-chain A/A, and writes the package documents, a draft
decision receipt for root, and (with ``--append-ledger``) the seven DRAFT exposure rows. Config
alone: no adapter, no split load, no lock, no contact; it flips nothing and mints nothing.

    python scripts/flights/write_slurp_slotfill_registration.py \\
        --study-commit <sha> --registered-at 2026-09-27T20:00:00.000000+00:00 [--append-ledger]
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

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (  # noqa: E402
    parse_dispatch_slot_fill,
)

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
PROOF_DIR = "docs/checks/speech-aware-evidence-acquisition/2026-09-27-dispatch-slot-fill-byte-identity-v1"
PROOF_SUMMARY = PROOF_DIR + "/proof-summary-v1.json"
LEDGER = "docs/exposure-ledger.md"

PARENT_ARM = "slurp-native-default-plan-lock-v1"
PARENT_SMOKE = "slurp-native-default-plan-lock-smoke-4-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 63.6304, "intent_accuracy": 82.2222}
PLANR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1"
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
PLAN_CALLS_USED = 4424
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

CELLS = {
    "arm": "slurp-native-stage3-slotfill-fold-a-v1",
    "smoke": "slurp-native-stage3-slotfill-fold-a-smoke-4-v1",
    "aa": "slurp-native-stage3-slotfill-aa-fold-a-v1",
}
PARENTS = {"arm": PARENT_ARM, "smoke": PARENT_SMOKE, "aa": PARENT_ARM}
PREFIX = {"arm": "", "smoke": "smoke-", "aa": "aa-"}
FLIGHT_PROSE = {
    "arm": "Cell SLOTFILL",
    "smoke": "Four-row form smoke of cell SLOTFILL",
    "aa": "The in-chain A/A replicate of cell SLOTFILL",
}
DECISION_ID = "slurp-stage3-slotfill-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json"
MEASUREMENT_ROW = "SAEA-SLURP-SLOTFILL-MODEL-FREE-PROOF-V1"

THE_KEY = "dispatch"
BOOKKEEPING_PREFIXES = ("native_contact_fit.", "prepared_phase_supply", "what_this_is")

H_SLU, H_INTENT = 1.2485, 0.9943

THROUGHPUT_NOTE = "docs/results/2026-09-27-slurp-throughput-baseline-and-levers.md"
THROUGHPUT_RECEIPT = "docs/receipts/slurp-throughput-baseline-and-levers-v1.json"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
HARNESS_RECEIPT = "docs/receipts/harness-admission.json"
G5_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1"
DERIVE_SCRIPT = "scripts/flights/derive_slurp_slotfill_cells.py"
HARNESS_SCRIPT = "scripts/analysis/slotfill_fake_server_harness.py"
GAP_SCRIPT = "scripts/analysis/slotfill_gap_decomposition.py"
CONFIG_TEST = "tests/unit/test_slotfill_config.py"
UNIT_TEST = "tests/unit/test_dispatch_slot_fill.py"
READ_DRIVER_FAMILY = "scripts/analysis/plan_cell_read.py"
GATE = "scripts/checks/stage3_effect_floor_check.py"


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
    overlap = sorted(experiment_keys & baseline_keys)
    if overlap:
        raise SystemExit(f"the experiment fragment overrides baseline keys: {overlap}")
    a, b = flatten(parent_values), flatten(mine)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    one_key = [k for k in changed if k == THE_KEY or k.startswith(THE_KEY + ".")]
    bookkeeping = [k for k in changed if k.startswith(BOOKKEEPING_PREFIXES)]
    experiment_block = [k for k in changed if k.split(".", 1)[0] in experiment_keys and k not in one_key and k not in bookkeeping]
    other = [k for k in changed if k not in one_key and k not in bookkeeping and k not in experiment_block]
    return {"the_one_key": one_key, "baseline_bookkeeping_only": bookkeeping,
            "experiment_fragment_own_block": experiment_block, "anything_else": other}


def identities() -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(rd(f"configs/experiment/{experiment}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], experiment)
        parent_doc = json.loads(rd(f"configs/experiment/{PARENTS[key]}.json"))
        parent_cell = parent_doc["cells"][0]
        parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"], parent_cell["baseline_fragment"], PARENTS[key])
        baseline_keys = set(json.loads(rd(f"configs/baseline/{parent_cell['baseline_fragment']}.json")))
        diff = composed_diff(parent.values, composed.values, set(document) | set(parent_doc), baseline_keys)
        if diff["anything_else"]:
            raise SystemExit(f"{key}: composed config differs from its locked PLAN parent beyond the key and bookkeeping: {diff['anything_else']}")
        switches = parse_dispatch_slot_fill(composed.values)
        if key == "aa":
            if diff["the_one_key"] or switches is not None:
                raise SystemExit("the A/A must carry no dispatch key")
        elif switches is None or not diff["the_one_key"]:
            raise SystemExit(f"{key}: the dispatch key is not armed")
        if "prepared_phase_supply" in composed.values:
            raise SystemExit(f"{key}: the derived cell must carry no committed prepared_phase_supply")
        if "phase_tools" in composed.values:
            raise SystemExit(f"{key}: phase_tools present; the Reviewer toolkit is RETIRED")
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENTS[key],
            "parent_baseline_fragment": parent_cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
            "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"],
            "dispatch": None if switches is None else switches.as_json(),
            "native_episode_policies": {k: composed.values["native_episode"].get(k) for k in ("finite_completion_policy", "react_exhaustion_policy")},
            "composed_config_diff_against_the_locked_plan_cell": diff,
            "readiness": cell["readiness"],
            "allowed_execution_stages": cell["allowed_execution_stages"],
            "generation_budget_target": document.get("generation_budget", {}).get("target"),
        }
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/slotfill")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-slotfill")
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    summary = json.loads(rd(PROOF_SUMMARY))
    if summary.get("schema") != "saea-slotfill-proof-summary-v1":
        raise SystemExit("the proof summary is not the expected schema")
    if not summary["byte_identity"]["all_identical"]:
        raise SystemExit("the byte-identity proof did not pass; refusing to register")
    summary_sha = sha_file(PROOF_SUMMARY)
    repro = summary["reproduction"]
    tput = summary["throughput"]

    ids = identities()
    arm, aa, smoke = ids["arm"], ids["aa"], ids["smoke"]
    caps, smoke_caps = arm["family_budget"], smoke["family_budget"]
    if aa["family_budget"] != caps:
        raise SystemExit("the A/A caps are not the arm's")
    g5_caps = json.loads(rd("configs/experiment/slurp-native-stage3-g5-fold-a-v1.json"))["family_budget"]
    if g5_caps != caps:
        raise SystemExit("the arm caps are not the locked family's (G5 / AGREE) arithmetic")

    no_harm_rule = (
        "NO-HARM ADMITTED (owner decisions 127 and 159): against the IN-CHAIN A/A arm flown in the same "
        f"chain, the paired CI95 lower bound of the intent-accuracy delta (primary, decision 133) is not "
        f"below -{H_INTENT} pp AND the paired CI95 lower bound of the official pooled SLU-F1 delta (the "
        f"guard) is not below -{H_SLU} pp -- each metric read at its own Fold A own-null half-width "
        f"(PLAN vs PLANr, {INSTRUMENT} section 2d). HARMFUL: a measured loss on either metric (CI95 "
        "upper bound below zero, decision 25). NEUTRAL-BY-WIDTH IS THE ADMISSION (decision 127). The "
        "item is NEVER reported as a gain on either metric. Beside the no-harm read, and as the item's "
        "declared ceiling, the THROUGHPUT read: contacts per GPU-hour over each arm's contact window and "
        "empty slot-seconds from the server's own per-slot task log joined one-to-one to each arm's sealed "
        f"trace ({GAP_SCRIPT}, the note's accounting), arm against A/A. Every verdict carries the "
        "per-scenario table in both weightings, the frontier row (decision 75), the delivered-answer "
        "agreement rate of arm and A/A, and the request-byte comparison of step 2."
    )
    ceiling = (
        "What the item unlocks (row 127 asks for the ceiling, not a gain): throughput -- the same contacts in "
        "less wall. ROLL-2's slot capacity was 27.3 % empty (8,997 of 32,909 slot-seconds; "
        f"{THROUGHPUT_NOTE}), reproduced here to the tenth of a second; the first Solver visit alone waited "
        f"{repro['solver1_turnaround_mean_s']} s per row on the client. The model-free bench on the locked PLAN "
        f"cell measured the empty share {tput['offline_empty_share_off_pct']} % -> {tput['offline_empty_share_on_pct']} % "
        f"and {tput['offline_contacts_per_hour_off']:,.0f} -> {tput['offline_contacts_per_hour_on']:,.0f} contacts per "
        f"hour of contact window (+{tput['offline_gain_pct']} %) under the sealed ROLL-2 per-role service times; the "
        f"honest bound for a flown cell is {tput['flown_bound_statement']}"
    )

    measurement = {
        arm["run_id"]: {
            "admission": "no-harm",
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "harm_margin_pp": H_SLU,
            "harm_margin_pp_by_metric": {"intent_accuracy": H_INTENT, "slu_f1": H_SLU},
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
            "replicate_run_id": aa["run_id"],
            "rows": 1080,
            "throughput_ceiling": {
                "metric": "contacts per GPU-hour over the contact window, and empty slot-seconds (server per-slot task log joined to the sealed trace)",
                "read_against": aa["run_id"],
                "offline_estimate_gain_pct": tput["offline_gain_pct"],
                "claims_gain": False,
                "note": "a declared CEILING, measured and reported; not an admission criterion and never a quality claim",
            },
            "note": (
                "A row-127 ENGINEERING-BASE item under owner decision 159, admitted on NO HARM and never reported as a "
                "gain: expected_effect_pp is 0.0 because the item changes no byte a node sees, claims_benefit is false, and "
                "the harm margin is the measured floor of this design at n = 1,080 -- the Fold A own-null half-width of PLAN "
                "vs PLANr, SLU 1.2485 (the gate's single harm_margin_pp field) and intent 0.9943 (the primary metric's own "
                "half-width, applied by the read; harm_margin_pp_by_metric). The delta is read against the in-chain A/A "
                "replicate flown in the same chain (rule 3). The throughput read is the declared ceiling (throughput_ceiling)."
            ),
        },
        aa["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
            "replicate_run_id": arm["run_id"],
            "rows": 1080,
            "note": (
                "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own form without the "
                "dispatch key, so the SLOTFILL deltas -- quality and throughput -- are read against a within-chain twin."
            ),
        },
        smoke["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": "none (structural form only)",
            "rows": 4,
            "note": (
                "Four rows prove FORM and nothing else: that the dispatch key parses and arms on the resident geometry, "
                "that every request fits and that the episode completes and seals. Scored by no one, read by no one."
            ),
        },
    }

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the CANONICAL stage3_measurement block "
            f"{GATE} resolves (keyed by run id; the arm's block is the no-harm declaration). The same block is repeated "
            "in the preregistration's fenced json for readability; this copy has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "77": "GPU flights only through the batch driver from the queue; the coordinator enqueues",
            "127": "the ENGINEERING-BASE admission: sound logic, a stated ceiling, a no-harm reading at a preregistered margin equal to the design's measured floor; never reported as a gain",
            "140": "sampling throughput (contacts per GPU-hour) is a first-class objective of the engineering base",
            "159": "the dispatcher slot fill is unfinished Stage-2 base and a PRIORITY engineering item: keep every slot loaded, proven byte-identical in every request body and every sealed per-row state, admitted on no harm plus the measured contacts per GPU-hour; it enters the base for cells flipped after it lands and never alters a pinned flight commit",
        },
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_item": summary["mechanism"],
        "reproduced_accounting": repro,
        "byte_identity": summary["byte_identity"],
        "throughput_estimate": tput,
        "proof_receipt": {"directory": PROOF_DIR, "summary": {"relpath": PROOF_SUMMARY, "sha256": summary_sha},
                          "harness": {"relpath": HARNESS_SCRIPT, "sha256": sha_file(HARNESS_SCRIPT)},
                          "gap_decomposition": {"relpath": GAP_SCRIPT, "sha256": sha_file(GAP_SCRIPT)},
                          "unit_tests": {"relpath": UNIT_TEST, "sha256": sha_file(UNIT_TEST)}},
        "identity": {key: {k: v for k, v in ids[key].items() if k not in ("composed_config_diff_against_the_locked_plan_cell", "readiness")} for key in CELLS},
        "composed_config_diff_against_the_locked_plan_cell": {
            key: {**ids[key]["composed_config_diff_against_the_locked_plan_cell"], "parent_experiment": PARENTS[key]}
            for key in CELLS
        } | {
            "note": (
                "computed by flattening both composed configs (core.config.compose) and listing every path whose value "
                "differs: the one key (arm and smoke; none on the A/A), the baseline's per-flight bookkeeping (this cell's "
                "FIT identities and cap, the dropped prepared_phase_supply, what_this_is) and the experiment fragment's own "
                f"block. The unit test {CONFIG_TEST} re-proves it."
            ),
        },
        "comparator": {
            "run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "official": COMPARATOR_OFFICIAL,
            "never_reflown": True,
            "in_chain_replicate": {"run_id": aa["run_id"], "why": "rule 4 refuses a cross-flight contrast with no in-chain replicate; the A/A is the locked plan's own form without the key, re-flown in the SAME campaign chain"},
            "margins": {"h_slu": H_SLU, "h_intent": H_INTENT, "source": f"the plan's own null on this roster, PLAN vs PLANr ({PLANR_RUN}); {INSTRUMENT} section 2d"},
        },
        "no_harm_rule": no_harm_rule,
        "ceiling_unlocked": ceiling,
        "byte_identity_expectation": {
            "sealed_plan_supply_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
            "claim": "the dispatch key enters the first-phase supply's identity (the composed config) but not its computation, so every supply the flip mints for this family must carry this output digest on all 1,080 rows (the smoke on its four); a different digest means the knowledge channel moved -- stop and report. The model-free bench minted the key-on and key-off supplies of the same tree and they agree on the output bytes.",
        },
        "pinned_flights_untouched": (
            "Every pinned flight commit keeps its code: this item lands on master for cells flipped after it, the 211 "
            "committed configs declare no dispatch key (tests/unit/test_dispatch_slot_fill.py), and the runtime reads the "
            "key only where it is declared. Because the prepared-supply identity binds the implementation files it names "
            "(item E16), a cell flipped at a commit before this item keeps its own pin and its own code; a cell flipped "
            "after it mints its own supply at its flip, as every cell does."
        ),
        "budget_arithmetic": {
            "caps_are_the_locked_family_arithmetic": True,
            "arm_and_aa_family_budget": caps,
            "smoke_family_budget": smoke_caps,
            "derivation": [
                "generation_calls_cap = 1,080 rows x 11 contacts per row (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)) = 11,880; the A/A the same; the smoke 4 x 11 = 44",
                "fit_endpoint_calls_cap = 4 x generation = 47,520 (smoke 176); native_task_contract_calls_cap = 1,080 x 6 = 6,480 (smoke 24); repeated_speech_audio_seconds_cap 33,930 (smoke 117); gpu_hours_fit_inclusive 12.0 (smoke 1.0), the locked family's own ceilings (G5 and AGREE carry the same)",
                f"expected spend per 1,080-row cell at the sealed PLAN arm's own realized rate: about {PLAN_CALLS_USED:,} contacts ({PLAN_CALLS_USED / 1080:.3f} per row) and about 3.7 GPU hours on the A/A; the arm moves no contact and no token, only wall time",
                "official_complete_scoring_jobs = 1 per 1,080-row cell, one job over the complete manifest through core.scoring_batch, never sharded; the smoke is never scored",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id, so the one permitted recovery re-registration spends from the same ceiling",
        },
        "committed_artifacts": {
            "prepared_phase_supply": (
                "NONE COMMITTED, by design: the flip mints each cell's own under its own run id (item E16), the readiness "
                "requirements list is empty, and --allow-output-change must never be passed."
            ),
        },
        "prohibitions": [
            "Never reported as a gain on intent or SLU: a no-harm item is admitted on the reading and two base items are never assumed to add (decision 127).",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed comparator.",
            "No second factor: no template, knob, store, release, snapshot, roster, geometry or session change; the committed configs are NOT re-pinned to the key.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cells are flipped.",
        ],
        "authority_relpaths": [THROUGHPUT_NOTE, THROUGHPUT_RECEIPT, INSTRUMENT, OWNER_DECISIONS, HARNESS_RECEIPT, G5_PACKAGE + "/README.md", GATE, PROOF_DIR + "/README.md"],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-slotfill-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "With the dispatcher keeping the resident slots loaded and nothing a node sees changed, do the official intent "
            "accuracy and pooled SLU-F1 on TRAIN Fold A 1,080 stay within the plan's own null, read against an in-chain A/A, "
            "and how many contacts per GPU-hour does the same work take? (A no-harm question plus a throughput reading; "
            "the item's value is the throughput, stated as a ceiling, never as a quality gain.)"
        ),
        "one_factor": f"Composed key {THE_KEY}: absent -> {json.dumps(arm['dispatch'], sort_keys=True)}.",
        "unchanged": (
            "everything but that key and per-flight bookkeeping: the roster (TRAIN Fold A 1,080, split identity "
            f"{arm['split_identity_hash']}), the model fragment and serving geometry (np4 x 24,576), the session {SESSION}, "
            "the phase program and its 11-contact ceiling, all three knowledge stores and their release/snapshot pins, the "
            "exemplar k of 20, the role graph, the response formats, every instruction template, the task contract, the "
            "deliver normaliser, the scorers and every budget"
        ),
        "cells": {key: {k: ids[key][k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "dispatch")} | {"fit_run_id": ids[key]["fit"]["run_id"], "fit_attempt_id": ids[key]["fit"]["attempt_id"]} for key in CELLS},
        "comparator": facts["comparator"],
        "decision_rule_fixed_here": no_harm_rule,
        "ceiling_unlocked": ceiling,
        "what_a_harmful_read_would_mean": (
            "That something the proof bench does not see moved the answers -- most plausibly the llama.cpp batch "
            "composition, which a fuller slot occupancy changes and which the 2026-09-27 determinism read showed can move "
            "bytes at np4 -- reported with the delivered-answer agreement rate beside the A/A's own; the key is then not "
            "carried into any plan and the switch that moved batch composition most is withdrawn first. A NEUTRAL read is "
            "the admission, not a failure."
        ),
        "model_free_proofs_landed_before_contact": {
            "reproduced_accounting": repro,
            "byte_identity": summary["byte_identity"],
            "throughput_estimate": tput,
            "composed_config_diff": facts["composed_config_diff_against_the_locked_plan_cell"],
        },
        "development_numbers_only": "Every number this family will produce is a TRAIN Fold A construction-fold development number (owner decisions 28 and 86) and is never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts.",
        "authority": (
            f"owner decisions 127, 140 and 159 ({OWNER_DECISIONS}); the throughput note {THROUGHPUT_NOTE} and receipt "
            f"{THROUGHPUT_RECEIPT}; the measurement instrument {INSTRUMENT} (rules 3 and 4, section 2d); the G5 chain shape "
            f"{G5_PACKAGE}; owner decisions 25 (measured loss), 28 and 86 (development numbers), 77 (batch driver), 101 "
            "(the Stage-3 algorithm label), 133 (intent primary)"
        ),
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for key in ("arm", "aa", "smoke"):
        identity = ids[key]
        budget = identity["family_budget"]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            plan_doc = {
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
                    "carrier_lock_key": identity["carrier_lock_key"],
                    "run_id": run_id,
                    "attempt_id": identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"],
                    "execution_profile": identity["execution_profile"],
                    "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"],
                    "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                    "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                    if is_fit else
                    "Shared core.flight.cli campaign over the committed campaign plan configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json, which carries the A/A replicate AND the SLOTFILL arm so the two fly in ONE chain on the same resident session; one official score per generation cell at finalize."
                    if key != "smoke" else
                    "Shared core.flight.cli worker on this cell alone; the smoke is deliberately outside the campaign plan and is never scored."
                ),
                "prepared_phase_supply": {
                    "relpath": f"prepared/{identity['run_id']}/phase-supply-v1.json",
                    "sha256": "MINTED_AT_THE_FLIP",
                    "expected_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                    "note": facts["committed_artifacts"]["prepared_phase_supply"] + " " + facts["byte_identity_expectation"]["claim"],
                },
                "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
                "one_factor": protocol["one_factor"],
                "purpose": (
                    f"{run_id}: {FLIGHT_PROSE[key]}. "
                    + ("It measures request envelopes only and reads nothing." if is_fit
                       else no_harm_rule if key == "arm"
                       else "It supplies the within-chain null and throughput baseline the SLOTFILL reads are taken at and makes no claim of its own." if key == "aa"
                       else "Structural form proof only: no score and no read.")
                ),
                "quality_read_gate": (
                    "No task-quality or throughput read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for BOTH the SLOTFILL arm and its in-chain A/A replicate. A verdict computed against the sealed comparator alone is refused."
                ),
            }
            name = f"{PREFIX[key]}{kind}-plan-registered-v1.json"
            plan_shas[run_id] = wjson(f"{PACKAGE}/{name}", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-slotfill-fold-a-paired-analysis-v1",
        "title": "Cell SLOTFILL -- the standard paired roster read on intent + SLU at the in-chain A/A under the no-harm rule, and the throughput read of both arms",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": arm["run_id"], "attempt_id": arm["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": aa["run_id"], "attempt_id": aa["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL", "role": "the within-chain null and throughput baseline"},
            "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT, "role": "gating comparator, sealed, never re-flown"},
        },
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": no_harm_rule,
        "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "steps": [
            "1. Refuse unless BOTH the SLOTFILL arm and the in-chain A/A carry a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids, each with one successful complete official TRAIN score, and their config hashes are this package's (the arm's dispatch receipt carries slot_fill with all three switches, the A/A's carries none).",
            "2. Structural stage: per (row, node, contact index) compare the two arms' sealed MODEL_REQUEST payloads with the request-id counter renamed to its (row, contact) identity and id_slot masked (the proof bench's own Normaliser, scripts/analysis/slotfill_fake_server_harness.py); report how many rows walked the same trajectory and, where a response differed (batch composition), how many request bytes then differ downstream of it. Counts only.",
            "3. Score once per arm over the complete manifest with the dataset's standard scorer (slurp-slu-official-train through core.scoring_batch, never sharded); take per row scenario_action_exact and the per-row SLU-F1 contributions.",
            "4. Paired row bootstrap (10,000 draws, seed 20260927) of the arm minus in-chain A/A delta on intent accuracy and on official pooled SLU-F1; report the point estimate and CI95 of each; report the same paired delta against the sealed PLAN comparator BESIDE it, never instead of it.",
            f"5. Apply the no-harm rule: ADMITTED iff the intent lower bound >= -{H_INTENT} and the SLU lower bound >= -{H_SLU}; HARMFUL iff either upper bound < 0 (decision 25); otherwise NOT ADMITTED (width). Never write 'gain' or 'no gain' about quality.",
            f"6. Throughput read (the declared ceiling): run {GAP_SCRIPT} --run-id/--attempt-id/--fit-run-id/--fit-attempt-id for each arm over the resident session's server log; report contacts per GPU-hour over each contact window, empty slot-seconds and their share, all-slots-empty seconds, mean busy slots, and the per-role client turnaround, arm beside A/A.",
            "7. Report beside every number: the per-scenario table in the natural-mixture and equal-stratum weightings; the frontier row (decision 75); the delivered-answer agreement rate of arm and A/A; the A/A's own delta against the sealed comparator as the instrument's reading.",
        ],
        "read_driver_family": READ_DRIVER_FAMILY,
        "output": {"analysis_root": "analysis/SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-PAIRED-ANALYSIS-V1"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim, never a generalisation claim, and it admits nothing beyond the no-harm entry it is registered for. No utterance text, transcript, gold label or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [arm["run_id"], arm["fit"]["run_id"], aa["run_id"], aa["fit"]["run_id"], smoke["run_id"], smoke["fit"]["run_id"]]
    draft = {
        "_draft_note": (
            "A DRAFT written by the registration agent, in the repository, for root to mint on the data root with "
            "scripts/flights/slotfill/slotfill_mint_receipt.py, which sets status 'decided', stamps recorded_at_utc, "
            "re-hashes every antecedent path at mint time and refuses to overwrite. It authorises nothing while its status "
            "is not 'decided' (core.flight.campaign.declared_readiness refuses it)."
        ),
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 engineering-base no-harm item (label none). One arm on TRAIN Fold A 1,080, its in-chain A/A replicate in the same chain, and a four-row form smoke outside the chain.",
        "decision": (
            "Fly the SLOTFILL family: the locked PLAN plan with the dispatcher slot-fill key armed (recall prefetch, role "
            "input off the event loop, frozen static heap), against the sealed PLAN arm read at the in-chain A/A flown in the "
            f"same chain. Admission is NO HARM at the plan's own Fold A half-widths (intent {H_INTENT}, SLU {H_SLU}); the "
            "throughput read is the declared ceiling; the item is never reported as a quality gain."
        ),
        "authorization_basis": (
            f"Owner decision 159 (the dispatcher slot fill is unfinished Stage-2 base and a priority engineering item), 127 "
            f"(the engineering-base admission) and 140 (throughput is first-class); the throughput note {THROUGHPUT_NOTE}; "
            f"standing: 25, 28, 86, 101, 133, 77, and the binding instrument note {INSTRUMENT}."
        ),
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "throughput_note": {"path": THROUGHPUT_NOTE, "sha256": sha_file(THROUGHPUT_NOTE)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "harness_admission": {"path": HARNESS_RECEIPT, "sha256": sha_file(HARNESS_RECEIPT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "proof_summary": {"path": PROOF_SUMMARY, "sha256": summary_sha},
            "config_proof": {"path": CONFIG_TEST, "sha256": sha_file(CONFIG_TEST) if Path(CONFIG_TEST).is_file() else None},
            "unit_proof": {"path": UNIT_TEST, "sha256": sha_file(UNIT_TEST)},
            "base_cell": f"the LOCKED default plan, cell PLAN ({COMPARATOR_RUN}, v2.0 lock 2026-09-22): SLOTFILL is that fragment with one key added",
            "clause_comparator": f"the sealed PLAN arm {COMPARATOR_RUN}, never re-flown, read at the in-chain A/A {aa['run_id']}",
            "registration_base_commit": args.study_commit,
        },
        "budget": {
            **{k: caps[k] for k in sorted(caps)},
            "smoke": smoke_caps,
            "paid_api_calls": 0,
            "expected_contacts_per_1080_row_cell": PLAN_CALLS_USED,
            "ceiling_note": "11 contacts per row = 1 + 2 x (1 + 3 + 1) at max_revisions 1; 12.0 GPU-h per 1,080-row cell is a ceiling (the sealed PLAN arm realized about 3.7 h); the key moves wall time only",
            "plan_budget_is_run_cumulative": True,
        },
        "claim_boundary": "No superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim of any kind; a no-harm admission of one engineering-base item plus a measured throughput ceiling, never reported as a quality gain.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the one registered key; re-pinning the committed configs to the key",
            "reporting the item as a quality gain",
        ],
        "population": {"count": 1080, "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080, the locked roster", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": "minted by scripts/flights/repin_cell.py at the flip (each cell's own, item E16); not pinned by this receipt; expected output digest " + PLAN_SUPPLY_OUTPUT_SHA},
        "registered_hashes": {"note": f"the values of the fragments exactly as committed at {args.study_commit} (readiness held, no decision requirement); repin_cell.py recomputes them at the flip.",
                              **{key: {"composed_config": ids[key]["composed_config_hash"], "protocol": ids[key]["protocol_hash"]} for key in CELLS}},
        "service": {"expected_session_id": SESSION, "model_fragment": arm["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "mmproj": "absent", "no_child_start_stop": True, "note": "the resident SLURP np4 session; the flight attaches only, never spawns or stops"},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    by = summary["byte_identity"]
    readme = f"""# Cell SLOTFILL: the dispatcher keeps every serving slot loaded

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decision 159, a
row-127 engineering-base no-harm item; throughput first-class under decision 140); all three cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The gap.** [`{THROUGHPUT_NOTE}`](../../results/{Path(THROUGHPUT_NOTE).name}): 27.3 % of ROLL-2's slot capacity
(8,997 of 32,909 slot-seconds) sat empty while the client prepared the next contact; 1,055 s with every slot empty;
2.67 s before every first Solver contact. Reproduced exactly on the sealed ROLL-2 trace and the ROLL-2 lifetime of the
session's server log ([`{PROOF_DIR}/README.md`](../../../{PROOF_DIR}/README.md)).

**The cause, located.** The first Solver visit's role input runs the train-exemplars recall -- a pure-Python cosine
over every exemplar key vector, a function of the row's own sealed speech query alone -- synchronously on the ONE event
loop every row shares (measured {repro.get('solver_role_input_s_offline', 'about 1.4')} s per row offline), and full
garbage collections over the loaded key vectors freeze every thread; rows-in-flight already exceed the slots
(queue depth 16 over 4 slots), but each row is pinned to its slot for its KV prefix (88.9 % of prompt tokens are served
from it), so releasing slots between contacts would cost more prefill than it saves.

**The mechanism: one key, three switches, scheduling only.** `{THE_KEY}` = `{json.dumps(arm['dispatch'], sort_keys=True)}`
(`rails.dispatch_slot_fill`): the recall is computed ahead while the row's Perception contact is in flight (lever 1b --
the candidate-bound slot-contract selection DOES depend on Perception and stays where it is); the role-input builder
runs on one dedicated worker instead of the shared loop (lever 1a); the loaded heap is frozen out of the collector.
Absent -- every committed configuration -- the dispatch is byte-for-byte what it was.

**Proven byte-identical.** On the REAL locked PLAN cell through the REAL flight dispatch against a recording fake
server ({by['rows']} rows, {by['contacts']} contacts per run, three runs OFF/ON/OFF): every request body the server
received, every client payload, every sealed row, every canonical output row and the multiset of trace records are
identical ON vs OFF and OFF vs OFF, once the two facts today's dispatcher already assigns by arrival -- the request-id
counter and the slot number -- are named by content. The minted first-phase supplies agree on their output bytes.
Crash plus resume-recovery with the key on keeps E10/I7r semantics (`{UNIT_TEST}`).

**Throughput, estimated honestly.** {tput['statement']}

**One key, proven.** Arm and smoke: `{THE_KEY}` added; the composed-config diff against the locked PLAN cells
(`registered-facts-v1.json`) is that key plus bookkeeping only. The in-chain A/A is the locked form WITHOUT the key.
`{CONFIG_TEST}` re-proves it.

**Three cells, one chain.** `configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json` carries the A/A and the
arm (instrument rule 4); the four-row smoke is outside the plan and never scored.

**`stage3_measurement`.** The arm declares `admission` **`no-harm`**, `harm_margin_pp` **{H_SLU}**, by metric intent
**{H_INTENT}** / SLU **{H_SLU}**, `claims_benefit` false, `expected_effect_pp` 0.0, `measurement_design`
`cross-flight-with-in-chain-replicate`, `replicate_run_id` `{aa['run_id']}`, primary metric intent accuracy, and a
`throughput_ceiling` block naming the contacts-per-GPU-hour read. `stage3_algorithm`: `none`.

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the one-key diffs, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the no-harm rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the arm's two plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row smoke's plans |
| `analysis-recipe-v1.json` | the paired no-harm read and the throughput read |
| `root-admission-draft-v1.json` | the decision receipt root mints with `scripts/flights/slotfill/slotfill_mint_receipt.py` |

**Budgets (the locked family's).** Arm and A/A each: {caps['generation_calls_cap']:,} generation contacts,
{caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['native_task_contract_calls_cap']:,} native task-contract calls,
{caps['repeated_speech_audio_seconds_cap']:,} repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one
official complete score. Smoke: {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']} /
{smoke_caps['native_task_contract_calls_cap']} / {smoke_caps['repeated_speech_audio_seconds_cap']} /
{smoke_caps['gpu_hours_fit_inclusive']}, never scored.

**No committed `prepared_phase_supply`.** The flip mints each cell's own (item E16); `--allow-output-change` must never
be passed; every minted supply must carry the sealed PLAN output digest `{PLAN_SUPPLY_OUTPUT_SHA}`.

**Mint, flip, queue.** Root countersigns the seven DRAFT exposure rows (six flight rows and `{MEASUREMENT_ROW}`),
mints `{DECISION_RELPATH}` (id `{DECISION_ID}`, six eligible run ids) with
`scripts/flights/slotfill/slotfill_mint_receipt.py`, flips with `scripts/flights/slotfill/slotfill_flip.sh` (the
generic re-pin loop over the three per-cell scripts), then queues `scripts/flights/slotfill/batch_chain_slotfill.sh`
behind whatever occupies the np4 session (decision 77).

**Not authorised by this package.** No flight before the receipt is minted and the cells are flipped; no contact by
this registration; no re-flying of the comparator; no test-split, Fold B or DEV read; no second factor; no re-pin of
the committed configs; no report of a quality gain; no admission entry.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    prereg_text = f"""# Cell SLOTFILL: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the locked PLAN
fragments by script (decision 58) with one key added, under owner decisions 127, 140 and 159. Development numbers only
(owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `{COMPARATOR_RUN}` ({COMPARATOR_OFFICIAL['slu_f1']} / {COMPARATOR_OFFICIAL['intent_accuracy']}) |
| factor | `{THE_KEY}` = `{json.dumps(arm['dispatch'], sort_keys=True)}` -- scheduling only, proven byte-identical on the model-free bench |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, every template, normaliser, scorers, budgets |
| comparator | `{COMPARATOR_RUN}`, sealed, never re-flown |
| in-chain replicate | `{aa['run_id']}`, the locked form without the key, re-flown in the SAME campaign chain |
| admission | NO HARM (owner decision 127): intent CI95 lower bound against the in-chain A/A not below -{H_INTENT}, SLU lower bound not below -{H_SLU}; never reported as a gain |
| ceiling | contacts per GPU-hour and empty slot-seconds against the A/A; offline estimate +{tput['offline_gain_pct']} % on the bench |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `{arm['run_id']}` / `{arm['fit']['run_id']}`; `{aa['run_id']}` / `{aa['fit']['run_id']}`; `{smoke['run_id']}` / `{smoke['fit']['run_id']}` |
| composed config hashes | arm `{arm['composed_config_hash']}`; A/A `{aa['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |
| protocol hashes | arm `{arm['protocol_hash']}`; A/A `{aa['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |
| split identity | arm and A/A `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |

## Decision rule (fixed here)

{no_harm_rule}

## The measurement declaration

```json
{fence}
```

## What the item is, and what it is not

{ceiling}

It is not a mechanism any node can observe, not a quality gain and not a component-causal claim. Two base items are
never assumed to add.

## Budgets and failure rule

Arm and A/A each {caps['generation_calls_cap']:,} generation contacts (run-cumulative), {caps['fit_endpoint_calls_cap']:,}
FIT endpoints, {caps['repeated_speech_audio_seconds_cap']:,} repeated speech seconds, {caps['gpu_hours_fit_inclusive']}
GPU hours, one official complete score; smoke {smoke_caps['generation_calls_cap']} / {smoke_caps['fit_endpoint_calls_cap']}
/ {smoke_caps['repeated_speech_audio_seconds_cap']} / {smoke_caps['gpu_hours_fit_inclusive']}, never scored. Stop and
preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and
the fix is proven on a four-row dry run.

## Prohibitions

Never reported as a quality gain. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read.
No re-flying of the sealed comparator. No second factor; the committed configs are not re-pinned. No flight before root
mints the decision receipt and the cells are flipped, and `--allow-output-change` is never passed.
"""
    prereg_sha = wr(PREREG, prereg_text)

    ledger_state = "not-requested"
    if args.append_ledger:
        ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas, summary=summary, summary_sha=summary_sha)

    print(json.dumps({
        "package": PACKAGE,
        "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol-registered-v1.json": protocol_sha,
                    "analysis-recipe-v1.json": recipe_sha, "root-admission-draft-v1.json": draft_sha,
                    Path(PREREG).name: prereg_sha, **{f"plan[{run}]": sha for run, sha in plan_shas.items()}},
        "exposure_ledger": ledger_state,
        "identity": {key: {"run_id": ids[key]["run_id"], "fit_run_id": ids[key]["fit"]["run_id"], "composed_config_hash": ids[key]["composed_config_hash"],
                           "protocol_hash": ids[key]["protocol_hash"], "parent_composed_config_hash": ids[key]["parent_composed_config_hash"],
                           "diff": ids[key]["composed_config_diff_against_the_locked_plan_cell"]} for key in CELLS},
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL_ARM = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool "
    "authority on any role; prompt bytes the locked PLAN arm's, byte for byte; the dispatcher slot-fill key armed "
    "(scheduling only)"
)
MODEL_TOOL_AA = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool "
    "authority on any role; prompt bytes the locked PLAN arm's, byte for byte; no dispatch key"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells "
    "B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, the "
    "AGREE family, KPROBE and G5 (flown or registered at registration); this cell adds no new row to the fold and opens "
    "no split. Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, plan_shas, summary, summary_sha) -> str:
    """Six DRAFT flight rows and one model-free proof row. Idempotent: replace-or-append by run id.
    No cell may contain a literal '|'."""

    text = rd(LEDGER)
    eligible = [ids["arm"]["run_id"], ids["arm"]["fit"]["run_id"], ids["aa"]["run_id"], ids["aa"]["fit"]["run_id"], ids["smoke"]["run_id"], ids["smoke"]["fit"]["run_id"]]
    tput = summary["throughput"]
    by = summary["byte_identity"]

    def notes(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        attempt = identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
        declaration = (
            f"admission no-harm, harm_margin_pp {H_SLU} (by metric: intent {H_INTENT}, SLU {H_SLU}), claims_benefit false, expected_effect_pp 0.0, measurement_design cross-flight-with-in-chain-replicate, replicate_run_id {ids['aa']['run_id']}, rows 1080, throughput ceiling read against the A/A"
            if key == "arm" else
            f"measurement_design cross-flight-with-in-chain-replicate, claims_benefit false, expected_effect_pp 0.0, replicate_run_id {ids['arm']['run_id']}, rows 1080 (the instrument)"
            if key == "aa" else
            "measurement_design form-proof, claims_benefit false, expected_effect_pp 0.0, rows 4"
        )
        return (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit "
            f"{args.study_commit} by the SLOTFILL registration agent (worktree {args.worktree}, branch {args.branch}). This "
            f"registration performs no contact and authorises none. Plan SHA256 {plan_shas[run_id]}; attempt {attempt}. "
            f"Protocol hash {identity['protocol_hash']}; composed config {identity['composed_config_hash']}; expected session "
            f"{SESSION} (attach only, never spawn or stop). READINESS HELD: root mints {DECISION_RELPATH} (decision id "
            f"{DECISION_ID}) from the package's root-admission-draft-v1.json with the six eligible run ids {', '.join(eligible)} "
            f"and this family's caps, then re-pins with scripts/flights/repin_cell.py --set-ready, which mints each cell's OWN "
            f"first-phase supply under its own run id (item E16; expected output digest {PLAN_SUPPLY_OUTPUT_SHA}); the "
            f"requirements lists are EMPTY and --allow-output-change must never be passed. Every hash in this row moves at the "
            f"flip and the re-pin tool rewrites it. ONE KEY (owner decision 159): {THE_KEY} absent on the A/A, "
            f"{json.dumps(ids['arm']['dispatch'], sort_keys=True).replace('|', '/')} on the arm and the smoke; scheduling only, "
            f"proven byte-identical on the model-free bench ({by['rows']} rows, {by['contacts']} contacts per run) in "
            f"{PROOF_DIR}. Measurement declaration ({GATE}): {declaration} -- declared at the top level of "
            f"{PACKAGE}/registered-facts-v1.json and repeated in the preregistration fence. THE RULE (owner decision 127): "
            f"admitted on NO HARM against the in-chain A/A at the plan's own Fold A half-widths, HARMFUL on a measured loss "
            f"(decision 25), NEVER reported as a quality gain; the throughput read is the declared ceiling (offline estimate "
            f"+{tput['offline_gain_pct']} % contacts per hour of window on the bench). Caps are the locked family's; no cap "
            f"is denominated in tokens. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
            f"re-registration. No paper-scale profile, no confirmatory split, no test-split contact, no comparator "
            f"re-flight and no admission entry from this row."
        )

    def row(key: str, kind: str) -> str:
        identity = ids[key]
        is_fit = kind == "fit"
        budget = identity["family_budget"]
        run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
        scope = FLIGHT_PROSE[key] + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + ": " + (
            "the locked PLAN plan with the dispatcher slot-fill key armed (scheduling only), read on no harm and throughput against the in-chain A/A"
            if key == "arm" else
            "the locked PLAN plan's own form without the dispatch key, re-flown in the same chain as the within-chain null and throughput baseline"
            if key == "aa" else
            "the dispatch key on the first four rows of the unchanged roster; structural form only, never scored"
        )
        cells = [
            "", args.registered_at, run_id, "bounded-discovery-probe", scope,
            MODEL_TOOL_AA if key == "aa" else MODEL_TOOL_ARM,
            f"slurp TRAIN Fold A {identity['rows']}", "discovery", identity["split_identity_hash"], "no",
            str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
            str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
            f"{PACKAGE}/{PREFIX[key]}{kind}-plan-registered-v1.json", notes(key, kind), "",
        ]
        return " | ".join(cells).strip()

    measurement_row = " | ".join([
        "", args.registered_at[:10], MEASUREMENT_ROW, "model-free-check",
        (
            "Reproduce the 2026-09-27 throughput note's empty-slot accounting on the sealed ROLL-2 trace and the ROLL-2 "
            "lifetime of the resident session's server log, place the per-contact fit gate on the same clock from the "
            "sealed fit receipts' file times, and prove the dispatcher slot-fill key byte-identical and estimate its "
            "throughput on the locked PLAN cell through the real flight dispatch against a recording fake server. Zero "
            "model, server, encoder, embedder, scorer, network, GPU and paid-API contacts; ports 8080 and 8081 untouched."
        ),
        "no model or tool contact; the real flight dispatch against an in-process fake server that never opens a socket; read-only sealed ROLL-2 trace, fit receipts and server log",
        "slurp TRAIN Fold A 1080 (sealed ROLL-2 trace, ids and counts only; the first rows of the locked roster on the proof bench, digests only)",
        "discovery", ids["arm"]["split_identity_hash"], "no", "0", "0", "0",
        "No new speech exposure: the proof bench reads promoted packets already exposed by the sealed PLAN and ROLL-2 arms and sends them to no model. Prior exposure inherited in full.",
        PROOF_DIR,
        (
            f"REGISTERED AFTER THE MODEL-FREE MEASUREMENT (DRAFT, root countersignature pending) {args.registered_at[:10]} at "
            f"study commit {args.study_commit}: a zero-contact reproduction and proof, recorded here because a pre-computation "
            f"belongs in the ledger even when it is model-free; it constructs no ExecutionPlan for a model, reserves no "
            f"contact and authorises nothing. Summary {PROOF_SUMMARY} SHA256 {summary_sha}; scripts {GAP_SCRIPT} and "
            f"{HARNESS_SCRIPT}. Reproduced: ROLL-2 empty slot-seconds {summary['reproduction']['empty_slot_s']}, all-slots-"
            f"empty {summary['reproduction']['all_idle_s']} s, the note's figures exactly. Proven: request bodies, payloads, "
            f"sealed rows, outputs and trace records identical ON vs OFF and OFF vs OFF on {by['rows']} rows modulo the "
            f"request-id counter and the slot number. Estimated: {tput['statement'].replace('|', '/')}"
        ),
        "",
    ]).strip()

    fresh = {}
    for key in ("arm", "aa", "smoke"):
        for kind in ("generation", "fit"):
            run_id = ids[key]["fit"]["run_id"] if kind == "fit" else ids[key]["run_id"]
            fresh[run_id] = row(key, kind)
    fresh[MEASUREMENT_ROW] = measurement_row
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
        raise SystemExit("the ledger carries some but not all SLOTFILL rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## Cell SLOTFILL: the dispatcher keeps every serving slot loaded -- the arm, its in-chain A/A replicate, its "
        "four-row smoke and the model-free proof (DRAFT, root countersignature pending)\n\n"
        "Six unconsumed flight rows -- the SLOTFILL arm, the in-chain A/A replicate, the four-row form smoke and their three "
        "FIT spend identities -- plus one model-free row for the reproduced accounting, the byte-identity proof and the "
        f"throughput estimate. Owner decisions 127, 140 and 159; authority {THROUGHPUT_NOTE}. None of these rows is "
        "countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[run_id] for run_id in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
