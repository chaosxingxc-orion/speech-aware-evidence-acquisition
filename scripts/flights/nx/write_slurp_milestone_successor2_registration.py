#!/usr/bin/env python3
"""Register the SLURP test-sample SUCCESSOR-2 milestone (the NX R5 composed arm on the signed sample).

Owner decisions 233 and 241 (2026-10-10): the second test-sample allowance is drafted once R5 reads
NOMINATED or NEUTRAL; "the composed arm flies once on the signed sample against the sealed PLAN and COMP-1b
columns". R5 read NEUTRAL on DEV-2000-ADDED, so this script registers, MODEL-FREE and HELD:

* ``derive``  -- the composed arm re-targeted from DEV-2000-ADDED to SLURP-TEST-SAMPLE-3010-V1, by the SAME
  fixed roster-bound / role-bound substitutions ``scripts/flights/comp1/derive_slurp_comp1b_testsample_cells.py``
  applied to cell A2's arm (it is imported, not forked): configs/experiment, configs/baseline, one campaign plan;
* ``register`` -- the package ``docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/`` (registered
  facts with the canonical ``stage3_measurement`` block, protocol, generation and FIT plans, analysis recipe,
  population counts, root-admission DRAFT, successor identity map), the preregistration, and with
  ``--append-ledger`` three DRAFT exposure rows (run, FIT, READ) at the END of the ledger.

PROOFS (all model-free, from ``core.config.compose``): the successor-2 cell differs from the R5 DEV cell by
roster-bound, role-bound and bookkeeping leaves alone; every roster-bound and role-bound leaf equals the
SEALED successor-1 COMP-1b cell's value; and the composition delta (successor-1 COMP-1b to successor-2) equals
the R5 delta on DEV (A2 arm to R5 composed), path for path. ``anything_else`` empty or this script refuses.

Nothing here flies, mints, flips, re-pins or countersigns. The allowance pin of the cell is written as 64 zeros
(the held form) until the owner signs; ``sign`` (owner decisions 250 A / 251 A, 2026-10-10) then pins the signed bytes.

    python -B scripts/flights/nx/write_slurp_milestone_successor2_registration.py derive
    python -B scripts/flights/nx/write_slurp_milestone_successor2_registration.py register \
        --study-commit <sha> --registered-at 2026-10-10T..Z [--append-ledger]
    python -B scripts/flights/nx/write_slurp_milestone_successor2_registration.py sign
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "flights" / "comp1"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import derive_slurp_comp1b_testsample_cells as D  # noqa: E402
import write_slurp_comp1b_testsample_registration as W  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

ZERO = "0" * 64

# ---- sources (the sealed R5 DEV cell, A2's DEV arm, and the sealed successor-1 sample cell) --------------
R5_CELL = "slurp-native-stage3-nx-r5-composed-dev2000-added-v1"
R5_BASELINE = "slurp-native-stage3-nx-r5-composed-dev2000-added-baseline-v1"
R5_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1"
R5_FIT_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-FIT-V1"
R5_FIT_ATTEMPT = "attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-fit-v1"
R5_PACKAGE = "docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1"
R5_READ_RUN = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
A2_DEV_CELL = "slurp-native-stage3-comp1b-dev2000-added-v1"
A2_TEST_CELL = "slurp-native-stage3-comp1b-testsample-v1"
S1_PACKAGE = "docs/readiness/2026-10-01-slurp-milestone-successor1-v1"
S1_COMP1B_CELL = "slurp-milestone-successor1-comp1b-v1"
S1_PLAN_CELL = "slurp-milestone-successor1-plan-v1"
S1_ALLOWANCE = "docs/receipts/owner/2026-10-01-slurp-test-sample-successor1-allowance-v1.json"
S1_COMP1B_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1"
S1_COMP1B_ATTEMPT = "attempt-slurp-milestone-successor1-comp1b-generation-v1"
S1_PLAN_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-PLAN-V1"
S1_PLAN_ATTEMPT = "attempt-slurp-milestone-successor1-plan-generation-v1"
S1_READ_NOTE = "docs/results/2026-10-01-slurp-milestone-successor1-read.md"

# ---- the successor-2 identities (used exactly) ----------------------------------------------------------
CELL = "slurp-milestone-successor2-composed-v1"
BASELINE = "slurp-milestone-successor2-composed-baseline-v1"
RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1"
ATTEMPT = "attempt-slurp-milestone-successor2-composed-generation-v1"
FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1"
FIT_ATTEMPT = "attempt-slurp-milestone-successor2-composed-fit-v1"
READ_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-PAIRED-ANALYSIS-V1"
RECIPE_ID = "slurp-milestone-successor2-composed-paired-analysis-v1"
PACKAGE = "docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1"
PREREG = PACKAGE + "-preregistration.md"
ALLOWANCE = "docs/receipts/owner/2026-10-10-slurp-test-sample-successor2-allowance-v1.json"
CAMPAIGN_PLAN = f"configs/campaign/{CELL}.json"
DECISION_ID = "slurp-milestone-successor2-admission-v1"
DECISION_RELPATH = "coordination/slurp-milestone-successor2-composed-v1/root-admission-v1.json"
READ_DRIVER = "scripts/flights/nx/milestone_successor2_read.sh"
ANALYSIS_ROOT = "analysis/" + READ_RUN
OWNER_DECISIONS = W.OWNER_DECISIONS
LEDGER = "docs/exposure-ledger.md"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

ROWS = D.ROWS
CONTACTS_PER_ROW = 2  # policy phase-native-module-v1-c2: Perception 1 + Solver 1, Reviewer and Planner never visited
SEED = 20260915
DRAWS = 10000
# the R5 read (aggregate report.json under the data root, v4g-contrast): flight offset a2_aa -> replicate, DEV n 1,000
DEV_OFFSET = {"slu_pp": 0.7274, "intent_pp": 0.2,
              "source": "analysis/" + R5_READ_RUN + "/v4g-contrast/report.json decision_rule_arithmetic.delivered "
                        "(offset_abs_slu_pp 0.7274, offset_abs_intent_pp 0.2): replicate minus the sealed A2 in-chain A/A, DEV-2000-ADDED, n 1,000"}
DEV_CLAIM = {"slu_pp": 1.2429, "slu_ci95": [-0.2904, 2.8036], "intent_pp": 0.5, "intent_ci95": [-0.5056, 1.5167],
             "source": "same report, delivered 'claim: a2_arm -> composed' (composed minus the sealed A2 arm); satisfies NEUTRAL"}
S1_TEST = {"intent_pp": 5.8030, "intent_ci95": [4.0389, 7.4243], "slu_pp": 0.7945, "slu_ci95": [-0.4448, 2.0180],
           "source": S1_READ_NOTE + " (post-stratified natural mixture, COMP-1b minus PLAN, sealed)"}
HARM_MARGIN = 2.5


# ---- small helpers ---------------------------------------------------------------------------------------
def sha_file(path: str) -> str:
    return hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()


def wjson(path: str, obj: object) -> str:
    return W.wjson(path, obj)


def load(path: str) -> dict:
    return json.loads(D.rd(path))


def sample_pins() -> dict[str, str]:
    """Every sample-preparation pin successor 1 carries (reused by pin, never rebuilt)."""

    pins: dict[str, str] = {}

    def walk(node):
        if isinstance(node, dict):
            relpath = node.get("relpath")
            if isinstance(relpath, str) and "sha256" in node and relpath in D.PENDING_ARTIFACTS and node["sha256"] != ZERO:
                pins[relpath] = node["sha256"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(load(f"configs/baseline/{S1_COMP1B_CELL.replace('-v1', '-baseline-v1')}.json"))
    missing = sorted(set(D.PENDING_ARTIFACTS) - set(pins))
    if missing:
        raise SystemExit(f"successor 1 does not pin: {missing}")
    return pins


def retarget_text(text: str) -> str:
    return D.substitute(text, D.ROSTER_SUBSTITUTIONS + [(R5_FIT_RUN, FIT_RUN), (R5_FIT_ATTEMPT, FIT_ATTEMPT)])


# ---- derive ------------------------------------------------------------------------------------------------
WHAT_THIS_IS = (
    "SUCCESSOR-2 of the test-sample milestone reads (owner decisions 233 and 241): the NX R5 composed arm EXACTLY as "
    "flown and sealed on DEV-2000-ADDED (slurp-native-stage3-nx-r5-composed-dev2000-added-v1: COMP-1b on module lock "
    "v2.2 = v2.1 with the delivery normaliser saea-deliver-normalise-v4g, review-off module graph, program "
    "phase-native-module-v1-c2, ceiling 2 contacts per row) re-targeted to the signed test sample "
    "SLURP-TEST-SAMPLE-3010-V1 by roster-bound pins alone (dataset view, roster receipt, packet promotion receipt, "
    "this roster's speech-query vectors, alias and agreement table, row-scaled budgets) plus the final-report role's "
    "own changes (the TEST scorer sibling slurp-slu-official-test and the owner-allowance pin), exactly the mapping "
    "that took cell A2's arm to the successor-1 COMP-1b cell. The sample preparations are successor 1's, reused by pin."
)

COMPOSITION = (
    "The NX R5 composed arm on the signed test sample: COMP-1b's two components ON (agree-vote-seed, w_agree 1.0, recall "
    "k 60, with THIS roster's vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1; centroid-boundary-key) "
    "on lock v2.2 (v4g at delivery) with the Reviewer loop OFF (Perception then Solver, 2 contacts per row), the locked "
    "Solver template, nothing else -- the R5 DEV cell's bytes with only the roster moved."
)


def retarget_baseline(pins: dict[str, str]) -> dict:
    raw = D.rd(f"configs/baseline/{R5_BASELINE}.json")
    document = json.loads(retarget_text(raw))
    document.pop("prepared_phase_supply", None)  # item E16: the flip mints this cell's own supply
    document["what_this_is"] = WHAT_THIS_IS
    document["scorers"] = [D.SCORER, "cost"]
    document["speech_packet_promotion_receipt_sha256"] = D.PROMOTION_RECEIPT_SHA256
    if not str(document.get("speech_packet_promotion_receipt", "")).endswith("TEST-SAMPLE-3010-promotion.json"):
        raise SystemExit("the packet promotion receipt did not re-target")
    fit = document["native_contact_fit"]
    per_row = fit["contact_cap"] // 1000
    if per_row * 1000 != fit["contact_cap"]:
        raise SystemExit("the FIT cap is not an exact per-row law at 1,000 rows")
    document["native_contact_fit"] = {**fit, "run_id": FIT_RUN, "attempt_id": FIT_ATTEMPT, "contact_cap": per_row * ROWS}

    def walk(node):
        if isinstance(node, dict):
            relpath = node.get("relpath")
            if isinstance(relpath, str) and "sha256" in node:
                if relpath in D.PENDING_ARTIFACTS:
                    node["sha256"] = pins[relpath]
                elif relpath == D.ROSTER_RECEIPT:
                    node["sha256"] = D.ROSTER_RECEIPT_SHA256
            for key, value in node.items():
                if isinstance(value, str) and key == "embedded_signal":
                    node[key] = value.replace(*D.TEXT_RETARGET)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    if isinstance(document.get("what_the_train_exemplars_store_is"), str):
        document["what_the_train_exemplars_store_is"] = document["what_the_train_exemplars_store_is"].replace(*D.TEXT_RETARGET)
    # DEV-2000-ADDED identifiers must not survive, except the NAME of the sealed DEV read document that admitted
    # a component (provenance, not a roster identifier) and this script's own what_this_is prose.
    probe = {k: v for k, v in document.items() if k != "what_this_is"}
    text = json.dumps(probe)
    text = re.sub(r"docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read\.md", "", text)
    leftover = re.findall(r"[^\"]{0,40}(?:DEV2000|dev2000|DEV-2000|dev-2000)[^\"]{0,40}", text)
    if leftover:
        raise SystemExit(f"DEV-2000-ADDED identifiers survived the re-target: {leftover[:5]}")
    D.wr(f"configs/baseline/{BASELINE}.json", D.dump_like(raw, document))
    return document


def budget_for(source: dict) -> dict:
    return D.scaled_budget({**source["family_budget"], "_rows": source["population"]["count"]})


def retarget_experiment(pins: dict[str, str]) -> dict:
    raw = D.rd(f"configs/experiment/{R5_CELL}.json")
    document = json.loads(raw)
    budget = budget_for(document)
    if budget["generation_calls_cap"] != ROWS * CONTACTS_PER_ROW:
        raise SystemExit(f"generation cap {budget['generation_calls_cap']} is not {ROWS} x {CONTACTS_PER_ROW}")
    s1 = load(f"configs/experiment/{S1_COMP1B_CELL}.json")
    carried = [r for r in s1["cells"][0]["readiness"]["requirements"] if r["kind"] == "preparation" and not r["relpath"].endswith("phase-supply-v1.json")]
    own_supply = {
        "kind": "preparation",
        "reason": ("This cell's OWN prepared first-phase Perception supply, minted model-free under its own run id with "
                   "core.flight.cli prepare-supply at the flip from the sample's segment vectors, the centroid key file "
                   "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this roster's agreement table (item E16). PENDING until "
                   "the flip: 64 zeros. The review-off graph and the lock-v2.2 normaliser never touch the first-phase supply, so "
                   "its selection output is expected to equal successor 1's COMP-1b supply selection output (same vectors, key file "
                   "and table); the flip's re-derivation checks this and a different digest means the knowledge channel moved -- stop "
                   "and report. --allow-output-change must never be passed."),
        "relpath": f"prepared/{RUN}/phase-supply-v1.json",
        "sha256": ZERO,
    }
    cell = document["cells"][0]
    cell.update({
        "allowed_execution_stages": ["check", "prepare-supply", "worker", "campaign"],
        "attempt_id": ATTEMPT,
        "baseline_fragment": BASELINE,
        "cell_id": CELL,
        "dataset_fragment": D.DATASET_FRAGMENT,
        "run_id": RUN,
        "readiness": {
            "reason": ("Cell SUCCESSOR2-COMPOSED registered before contact on 2026-10-10 by script (decision 58) from the sealed "
                       "R5 composed cell (read NEUTRAL on DEV-2000-ADDED 2026-10-10) under owner decisions 233 and 241. HELD: "
                       "(1) the owner has not signed the successor-2 allowance DRAFT; this fragment's owner_allowance sha256 is 64 "
                       "zeros until the coordinator sets the draft's status to authorised, records its sha256 and re-pins; (2) root "
                       "countersigns the DRAFT rows and mints the admission receipt; (3) scripts/flights/repin_cell.py --set-ready "
                       "mints this cell's own supply (item E16). --allow-output-change must never be passed. Nothing here authorises "
                       "a flight, a flip, a mint or a countersignature."),
            "requirements": carried + [own_supply],
            "state": "held",
        },
    })
    document["cells"] = [cell]
    document["date"] = "2026-10-10"
    document["experiment_id"] = RUN
    document["execution_plan"] = {
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
        "planned_model_calls": budget["generation_calls_cap"],
        "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
        "split_role": D.SPLIT_ROLE,
    }
    document["owner_allowance"] = {"path": ALLOWANCE, "sha256": ZERO}
    document["family_budget"] = budget
    document["generation_budget"] = {
        "cap": budget["generation_calls_cap"],
        "definition": (
            "The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited, max_revisions 0) under "
            "program phase-native-module-v1-c2: the bounded graph ceiling is 2 contacts per row "
            f"(rails.native_episode_config), so {ROWS} x 2 = {budget['generation_calls_cap']} is the exact program maximum and "
            "the expected spend. The budget is RUN-CUMULATIVE across every attempt of this run id (there is exactly one)."),
        "target": budget["generation_calls_cap"],
    }
    document["population"] = {
        "count": ROWS,
        "dataset_fragment": D.DATASET_FRAGMENT,
        "decision_population": (
            f"The signed SLURP test SAMPLE {D.ROSTER_ID} (3,010 recordings, 682 prompts; roster receipt {D.ROSTER_RECEIPT}). It is "
            "NOT an unexposed sample: the label-free preparations (owner decision 156), the failed original PLAN generation "
            "(3,010 output records, 12,343 contacts, unread) and the SEALED, SCORED and READ successor-1 pair (PLAN and COMP-1b, "
            "6,020 trajectories, read 2026-10-01 under owner decision 213; aggregate and per-intent results published in "
            f"{S1_READ_NOTE}) are inherited exposure in full. The closure roster SLURP-TEST-CLOSURE-10068-V1 stays untouched."),
        "roster_receipt": D.ROSTER_RECEIPT,
        "split_identity_hash": D.SPLIT_IDENTITY,
    }
    document["purpose"] = (
        "SUCCESSOR-2 test-sample milestone (owner decisions 233 and 241; allowance DRAFT " + ALLOWANCE + "): does the NX R5 composed "
        "arm (COMP-1b on lock v2.2 with v4g at delivery, review-off, 2 contacts per row), which read NEUTRAL on DEV-2000-ADDED, keep "
        "the sealed successor-1 COMP-1b column's accuracy on the signed test sample at about a third of the contacts, with official "
        "pooled SLU-F1 (slurp-slu-official-test) primary and intent the guard? ONE attempt, ever; the milestone is consumed whether "
        "the arm gains, loses or is neutral. Cross-flight against the SEALED successor-1 COMP-1b and PLAN columns "
        "(nothing re-flown). Development evidence under owner decision 28; never a test claim and never the final read. Nothing "
        "here authorises a flight, a readiness flip or an admission entry.")
    document["failure_policy"] = D.FAILURE_POLICY
    document["split_id"] = D.SPLIT_ID
    document["service_session"] = SESSION
    document["stage3_algorithm"] = {
        "id": document["stage3_algorithm"]["id"],
        "note": ("SUCCESSOR-2 composes the SAME two typed, executable consumption actions the R5 composed arm composed on "
                 "DEV-2000-ADDED -- a rank weight over a pre-computed vote and a retrieval key file -- each chosen and credited OFFLINE over "
                 "sealed TRAIN bytes, removes the Reviewer and Planner visits (review-off) and delivers through the registered v4g "
                 "normaliser (selected offline on the A2 DEV pool and confirmed on TRAIN Fold A and Fold B); nothing is chosen, tuned or "
                 "credited on the sample. Operator context_application. No rollout, per-sample scoring, credit assignment or update of "
                 "its own."),
        "operators_used": list(document["stage3_algorithm"]["operators_used"]),
    }
    D.wr(f"configs/experiment/{CELL}.json", D.dump_like(raw, document))
    return document


def derive() -> None:
    os.chdir(REPO_ROOT)
    pins = sample_pins()
    retarget_baseline(pins)
    retarget_experiment(pins)
    plan = {"cells": [{"cell": CELL, "experiment": CELL}], "schema": "saea-campaign-plan-v1"}
    D.wr(CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"written": [f"configs/experiment/{CELL}.json", f"configs/baseline/{BASELINE}.json", CAMPAIGN_PLAN],
                      "reused_sample_preparation_pins": pins}, indent=2, sort_keys=True))


# ---- the allowance DRAFT -----------------------------------------------------------------------------------
def write_allowance() -> None:
    """Write the unsigned successor-2 allowance DRAFT (schema saea-owner-split-allowance-v1) from successor 1's signed bytes."""

    s1 = load(S1_ALLOWANCE)
    if s1.get("status") != "authorised":
        raise SystemExit("successor 1's allowance is not authorised; refusing to supersede it")
    a = copy.deepcopy(s1)
    gen, fit, audio, gpu = ROWS * CONTACTS_PER_ROW, ROWS * CONTACTS_PER_ROW * 4, math.ceil(CONTACTS_PER_ROW * s1["split"]["audio_seconds_total"]), 4.6
    a["attempt_budget"] = {
        "preparation_run_ids": 1, "read_run_ids": 1,
        "statement": "No automatic retry. The generation identity is consumed by its sole attempt; any failure stops this successor comparison.",
    }
    a["budgets"] = {
        "contacts_per_row": CONTACTS_PER_ROW,
        "fit_endpoint_cap_per_arm": fit, "fit_endpoint_cap_total": fit,
        "generation_cap_per_arm": gen, "generation_cap_total": gen,
        "gpu_hour_cap_per_arm_fit_inclusive": gpu,
        "official_score_jobs_total": 1,
        "repeated_speech_audio_seconds_cap": audio,
    }
    a["date"] = "2026-10-10"
    a["dated_owner_decision"] = (
        "Owner decision 241, 2026-10-10 UTC (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, row 241; the second test-sample "
        "allowance was agreed in principle as decision 233). The owner's words, in English: \"As you suggest.\" Recorded ruling, quoted from row 241: "
        "\"the second test-sample allowance (233) is drafted once R5 reads NOMINATED or NEUTRAL; same terms as v2; the composed arm flies once on the "
        "signed sample against the sealed PLAN and COMP-1b columns.\" THIS FILE IS THE DRAFT: the owner has not signed it, and nothing here "
        "authorises a contact until the owner's confirmation in conversation is recorded in the signature block and the status is set to authorised.")
    a["first_contact_gate"] = {
        "basis": "R5 read NEUTRAL on DEV-2000-ADDED 2026-10-10: efficiency result, no harm, intent gain replicated a third time",
        "r5_read": ("Owner decision 240 flew R5 (the composed arm, COMP-1b on lock v2.2 with v4g, review-off) on DEV-2000-ADDED. Composed minus the sealed A2 arm: "
                    "official SLU-F1 +1.24 pp CI95 [-0.29, +2.80], intent +0.50 pp CI95 [-0.51, +1.52]; flight offset 0.73 pp SLU / 0.20 intent; verdict NEUTRAL "
                    "(an efficiency result at about half the contacts; no benefit is claimed)."),
        "status": "to be reported by the coordinator to the owner in conversation before the owner signs; the report is named (date, arm) in the root countersignature of the first consumed exposure row",
    }
    a["milestone_rule"] = (
        "This allowance authorizes only the fresh NX R5 composed arm, flown ONCE on the unchanged 3010-row sample and read cross-flight against the SEALED "
        "successor-1 PLAN and COMP-1b columns. Keep original scientific settings and registered thresholds. Never use milestone outcomes for tuning. One "
        "complete official score for the sealed arm; read only after the arm finalizes with one score. No reseal, retry or rescore of the new arm, and no "
        "re-flight, rescore or re-read of the sealed successor-1 columns.")
    a["not_authorized"] = [
        "new encoding", "old attempt reads or scoring",
        "re-flight, rescore or re-read of the sealed successor-1 columns", "additional milestone arms",
        "test-sample smoke", "closure or complementary test contacts", "P-SV-4 release", "other carrier GPU flights",
    ]
    a["permitted_run_ids"] = [RUN, FIT_RUN]
    a["read_run_ids"] = [RUN]
    a["preparation_run_ids"] = [FIT_RUN]
    a["run_ids"] = {
        FIT_RUN: {"core_contacts": 0, "execution_profile": "bounded-discovery-probe", "kind": "preparation", "reads_labels": False,
                  "serves_read_run_id": RUN, "subkind": "native_contact_fit"},
        RUN: {"execution_profile": "bounded-discovery-probe", "kind": "read",
              "reads_labels": "Official scoring only after complete delivery. No labels, transcripts or future state enter runtime.",
              "rows": ROWS, "what": "NX R5 composed arm (COMP-1b on module lock v2.2 with v4g, review-off), one attempt"},
    }
    a["analysis_read_run_id_not_a_permission"] = {
        "run_id": READ_RUN,
        "statement": "The model-free paired analysis identity (ledger kind model-free-check). It reads sealed outputs only and, as in successor 1, is not a permitted run id.",
    }
    a["prior_exposure"] = (
        "Existing label-free sample preparations, the failed original PLAN generation (3010 output records, 12343 model contacts, unread) and the SEALED, SCORED "
        "and READ successor-1 PLAN and COMP-1b columns (6020 trajectories, read 2026-10-01 under owner decision 213) are inherited exposure. This is not an unexposed sample.")
    a["signature"] = {"coordinator": None, "decision": 241, "form": "explicit confirmation in conversation",
                      "owner_words_english": None, "signed_at": None, "signed_by": None}
    a["status"] = "draft-awaiting-owner-signature"
    a["supersedes"] = {
        "path": S1_ALLOWANCE, "sha256": sha_file(S1_ALLOWANCE),
        "scope": "New successor run identities only; old bytes and their historical permissions are preserved, not reactivated.",
    }
    wjson(ALLOWANCE, a)
    print(json.dumps({"written": ALLOWANCE, "sha256": sha_file(ALLOWANCE), "supersedes_sha256": a["supersedes"]["sha256"]}, indent=2))


# ---- register ----------------------------------------------------------------------------------------------
def composed_of(experiment: str):
    return W.composed_of(experiment)


def components_neutral(values: dict, side: str, pins: dict[str, str]) -> str:
    """The module components list as text with the roster-bound strings and pins neutralised (a list leaf)."""

    comps = copy.deepcopy(values["native_episode"]["consumption_module"]["components"])
    text = json.dumps(comps, sort_keys=True)
    if side == "dev":
        text = retarget_text(text)

    def walk(node):
        if isinstance(node, dict):
            if "sha256" in node and isinstance(node.get("relpath"), str) and "AGREEMENT" in node["relpath"]:
                node["sha256"] = "<sample-pin>"
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    parsed = json.loads(text)
    walk(parsed)
    return json.dumps(parsed, sort_keys=True)


def prove(pins: dict[str, str]) -> dict:
    r5 = composed_of(R5_CELL)[2]
    a2d = composed_of(A2_DEV_CELL)[2]
    a2t = composed_of(A2_TEST_CELL)[2]
    s1 = composed_of(S1_COMP1B_CELL)[2]
    s2 = composed_of(CELL)[2]
    fr5, fa2d, fa2t, fs1, fs2 = (W.flatten(c.values) for c in (r5, a2d, a2t, s1, s2))
    comps = "native_episode.consumption_module.components"

    def values_without_lists(c):
        v = copy.deepcopy(c.values)
        v["native_episode"].get("consumption_module", {}).pop("components", None)
        return v

    # 1. S2 vs the R5 DEV cell: roster-bound / role-bound / bookkeeping / experiment block alone.
    if components_neutral(r5.values, "dev", pins) != components_neutral(s2.values, "test", pins):
        raise SystemExit("the module components moved beyond the roster-bound pins")
    vs_r5 = W.classify(values_without_lists(r5), values_without_lists(s2))
    if vs_r5["anything_else"] or vs_r5["composition_factor"]:
        raise SystemExit(f"S2 vs R5: moved beyond the roster re-target: {vs_r5['anything_else'] + vs_r5['composition_factor']}")
    before, after = r5.values["preparation_source_receipts"], s2.values["preparation_source_receipts"]
    if len(before) != len(after):
        raise SystemExit("preparation_source_receipts changed length")
    for b, a in zip(before, after):
        if a["relpath"] == b["relpath"]:
            if a["sha256"] != b["sha256"] or a.get("root") != b.get("root"):
                raise SystemExit(f"an unchanged preparation receipt moved its pin: {a['relpath']}")
        elif not (a["sha256"] != ZERO and (a["relpath"] == D.ROSTER_RECEIPT or W._is_sample_preparation(a["relpath"]))):
            raise SystemExit(f"a re-targeted preparation receipt is not a sample pin: {a['relpath']}")

    # 2. the SAME mapping as A2 DEV -> successor-1 COMP-1b: every roster-bound / role-bound leaf equals successor 1's.
    vs_a2 = W.classify(values_without_lists(a2d), values_without_lists(a2t))
    moved_a2 = set(vs_a2["roster_bound"]) | set(vs_a2["role_bound"])
    moved_s2 = set(vs_r5["roster_bound"]) | set(vs_r5["role_bound"])
    exempt = ("execution_plan.", "family_budget.", "generation_budget.", "native_contact_fit.", "population.decision_population",
              "owner_allowance.", "what_the_train_exemplars_store_is", "preparation_source_receipts")
    unequal = [k for k in sorted(moved_a2 & moved_s2)
               if not any(k == e or (e.endswith(".") and k.startswith(e)) for e in exempt) and fs2.get(k, "<absent>") != fs1.get(k, "<absent>")]
    if unequal:
        raise SystemExit(f"roster/role-bound leaves differ from the sealed successor-1 cell: {unequal}")
    only_a2 = sorted(moved_a2 - moved_s2)
    only_s2 = sorted(moved_s2 - moved_a2)
    if "what_the_train_exemplars_store_is" not in fs1 or fs1.get("what_the_train_exemplars_store_is") != fs2.get("what_the_train_exemplars_store_is"):
        raise SystemExit("what_the_train_exemplars_store_is differs from successor 1")

    # 3. the composition delta commutes: successor-1 COMP-1b -> S2 equals A2 DEV arm -> R5 composed, path for path.
    graph_keys = sorted(k for k in set(fr5) | set(fa2d)
                        if fr5.get(k, "<absent>") != fa2d.get(k, "<absent>")
                        and not any(W._matches(k, g) for g in (W.ROSTER_BOUND, W.ROLE_BOUND, W.BOOKKEEPING, W.EXPERIMENT_BLOCK)) and k != comps)
    bad = [k for k in graph_keys if fs2.get(k, "<absent>") != fr5.get(k, "<absent>") or fs1.get(k, "<absent>") != fa2d.get(k, "<absent>")]
    if bad:
        raise SystemExit(f"the composition delta does not commute at {bad}")
    delta_s = sorted(k for k in set(fs1) | set(fs2) if fs1.get(k, "<absent>") != fs2.get(k, "<absent>")
                     and not any(W._matches(k, g) for g in (W.ROSTER_BOUND, W.ROLE_BOUND, W.BOOKKEEPING, W.EXPERIMENT_BLOCK)) and k != comps)
    if delta_s != graph_keys:
        raise SystemExit(f"successor-1 COMP-1b to S2 moves {delta_s}, A2 DEV to R5 moves {graph_keys}")
    vs_s1 = W.classify(values_without_lists(s1), values_without_lists(s2))
    return {
        "s2_vs_r5_dev": vs_r5,
        "a2_dev_to_a2_test_mapping": {"roster_bound": vs_a2["roster_bound"], "role_bound": vs_a2["role_bound"]},
        "mapping_square": {
            "every_roster_and_role_leaf_shared_with_a2_mapping_equals_successor1": True,
            "leaves_only_in_the_a2_mapping": only_a2,
            "leaves_only_in_the_r5_mapping": only_s2,
            "note": "the A2 DEV -> A2 test mapping and the R5 DEV -> successor-2 mapping move the SAME roster- and role-bound leaves (both difference lists are empty); each shared leaf equals the sealed successor-1 COMP-1b cell's value, except the exempt run-specific leaves (budgets, ids, allowance pin, decision_population)",
        },
        "composition_delta_commutes": {
            "graph_leaves_moved_by_r5_on_dev": graph_keys,
            "successor1_comp1b_to_s2_moves_exactly_these": delta_s,
            "components_list": "compared after neutralising roster-bound strings and pins: equal",
            "commutes": True,
        },
        "s2_vs_successor1_comp1b": {("composition_delta_graph_leaves" if k == "anything_else" else k): v for k, v in vs_s1.items() if v},
    }, s2


def ledger_row(cells: list[str]) -> str:
    return W.ledger_row(cells)


# ---- sign: pin the SIGNED allowance bytes (owner decisions 250 A / 251 A, 2026-10-10) ---------------------------------
SIGNED_AT_NOTE = "signed 2026-10-10, owner decision 251 (option A)"
DRAFT_BYTES_SHA = "295a570e184589e65104e0d47f09e9393cf8b525cac7a01a221b9b7f48089e6b"
DECISION_250_RULING = {
    "decision": 250,
    "option": "A",
    "date": "2026-10-10",
    "ruling": ("The successor-2 test read carries the documented exception to instrument rule 4: design cross-flight-no-replicate, declared DEV "
               "flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; no in-chain "
               "replicate on the sample."),
    "source": "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md, section 'Decisions 249-252 ruled by the owner, 2026-10-10'",
}


def _read_text(path: str) -> str:
    return (REPO_ROOT / path).read_bytes().decode("utf-8")


def _write_text(path: str, text: str) -> None:
    (REPO_ROOT / path).write_bytes(text.encode("utf-8"))


def sign() -> int:
    """Pin the signed allowance bytes into the held cell and propagate every hash that depends on the pin (model-free).

    Reads the committed signed allowance, rewrites the four ``owner_allowance`` pins (fragment, both plan documents, facts), records the
    decision-250 ruling in the measurement block, updates the prose that said "unsigned", and then propagates the composed config hash,
    the protocol hash and every package file sha256 to a fixed point. Nothing here flies, mints, flips, re-pins or countersigns.
    """

    import re

    allowance = load(ALLOWANCE)
    if allowance.get("status") != "authorised":
        raise SystemExit("the successor-2 allowance is not authorised; nothing to pin")
    if allowance["permitted_run_ids"] != [RUN, FIT_RUN] or allowance["read_run_ids"] != [RUN] or allowance["preparation_run_ids"] != [FIT_RUN]:
        raise SystemExit("the signed allowance does not permit exactly the run and FIT ids")
    signed = sha_file(ALLOWANCE)
    fragment = f"configs/experiment/{CELL}.json"
    plan_paths = [f"{PACKAGE}/generation-plan-registered-v1.json", f"{PACKAGE}/fit-plan-registered-v1.json"]
    facts_path, protocol_path = f"{PACKAGE}/registered-facts-v1.json", f"{PACKAGE}/protocol-registered-v1.json"
    readme_path, draft_path = f"{PACKAGE}/README.md", f"{PACKAGE}/root-admission-draft-v1.json"
    package_files = sorted(str(p.relative_to(REPO_ROOT)).replace(os.sep, "/") for p in (REPO_ROOT / PACKAGE).iterdir() if p.is_file())
    tracked = [fragment, PREREG, LEDGER, *package_files]
    latest = {p: sha_file(p) for p in tracked}
    old_composed = composed_of(CELL)[2]
    old_cfg = old_composed.config_hash
    old_proto = protocol_hash(old_cfg, old_composed.values["arm"], old_composed.values["split_identity_hash"])
    if json.loads(_read_text(fragment))["owner_allowance"] != {"path": ALLOWANCE, "sha256": ZERO}:
        raise SystemExit("the fragment is not in the held (64-zero) form; already signed?")

    pin_re = re.compile(r'("owner_allowance": \{\s*"path": "' + re.escape(ALLOWANCE) + r'",\s*"sha256": ")' + ZERO + '"')
    n_pins = 0
    for path in (fragment, *plan_paths, facts_path):
        text, n = pin_re.subn(lambda m: m.group(1) + signed + '"', _read_text(path))
        n_pins += n
        _write_text(path, text)
    if n_pins != 4:
        raise SystemExit(f"expected 4 owner_allowance pins (fragment, two plans, facts), rewrote {n_pins}")

    text = _read_text(fragment)
    old_reason = ("(1) the owner has not signed the successor-2 allowance DRAFT; this fragment's owner_allowance sha256 is 64 zeros until the "
                  "coordinator sets the draft's status to authorised, records its sha256 and re-pins;")
    if old_reason not in text:
        raise SystemExit("fragment reason text not found")
    _write_text(fragment, text.replace(
        old_reason, f"(1) the owner SIGNED the successor-2 allowance ({SIGNED_AT_NOTE}); this fragment's owner_allowance pins the signed bytes, sha256 {signed};"))

    new_composed = composed_of(CELL)[2]
    new_cfg = new_composed.config_hash
    new_proto = protocol_hash(new_cfg, new_composed.values["arm"], new_composed.values["split_identity_hash"])
    if new_composed.values["owner_allowance"] != {"path": ALLOWANCE, "sha256": signed}:
        raise SystemExit("the composed config does not carry the signed pin")

    def edit_json(path: str, fn) -> None:
        raw = _read_text(path)
        doc = json.loads(raw)
        if json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n" != raw:
            raise SystemExit(f"{path} does not round-trip through the registration serialiser")
        fn(doc)
        _write_text(path, json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n")

    def amend_measurement(block: dict) -> None:
        block["owner_ruling_decision_250"] = DECISION_250_RULING
        block["design_statement"] += (
            " RULED 2026-10-10: owner decision 250 (option A) accepts the documented exception to rule 4 -- design cross-flight-no-replicate, "
            "declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence under decision 28; "
            "no in-chain replicate on the sample.")

    def facts_fn(doc: dict) -> None:
        a = doc["allowance"]
        a["sha256_pinned_in_the_fragment"] = signed
        a["status_signed"] = "authorised"
        a["sha256_of_signed_bytes"] = signed
        a["signed_note"] = (f"{SIGNED_AT_NOTE}; committed at master 951de831b; the fragment, both plan documents and these facts pin these bytes. "
                            "The cell stays HELD and the ledger rows stay DRAFT until root countersigns.")
        a["signing"] = (f"SIGNED 2026-10-10 (owner decision 251, option A): status 'authorised', sha256 {signed}; the fragment's owner_allowance pins "
                        "those bytes (write_slurp_milestone_successor2_registration.py sign); contracts.plan.require_owner_split_allowance accepts "
                        "exactly the two permitted run ids.")
        a["decision_250_ruling"] = DECISION_250_RULING
        amend_measurement(doc["stage3_measurement"][RUN])

    edit_json(facts_path, facts_fn)
    edit_json(protocol_path, lambda doc: amend_measurement(doc["stage3_measurement"][RUN]))

    measurement = {"stage3_measurement": json.loads(_read_text(facts_path))["stage3_measurement"]}
    new_block = json.dumps(measurement, indent=2, ensure_ascii=False, sort_keys=True)
    block_re = re.compile(r"```json\n(\{\n  \"stage3_measurement\".*?\n\})\n```", re.S)
    for path in (readme_path, PREREG):
        text = _read_text(path)
        if len(block_re.findall(text)) != 1:
            raise SystemExit(f"{path}: expected exactly one stage3_measurement json block")
        _write_text(path, block_re.sub(lambda m: "```json\n" + new_block + "\n```", text))

    b1_new = (f"OWNER SIGNATURE: RESOLVED. The owner signed the successor-2 allowance on 2026-10-10 (decision 251, option A): status authorised, "
              f"sha256 {signed}, pinned by this cell's owner_allowance.")
    b2_new = ("MEASUREMENT RULE: RULED. Owner decision 250 (option A, 2026-10-10) accepts the documented exception to instrument rule 4: design "
              "cross-flight-no-replicate, declared DEV flight offset 0.7274 pp SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, development evidence "
              "under decision 28; no in-chain replicate on the sample.")
    signed_para = (
        f"**Signed 2026-10-10 (decision 251, option A; decisions 249-252 in `docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md`).** "
        f"Status `authorised`, the owner's words recorded in the signature block; the committed bytes (master `951de831b`) hash to `{signed}`. "
        "`write_slurp_milestone_successor2_registration.py sign` pinned the fragment's `owner_allowance`, both plan documents and the facts to that "
        "sha256 and propagated the hashes that depend on the pin (composed config hash, protocol hash, protocol and plan file sha256s) through the "
        "package, the preregistration, the root-admission draft and the three DRAFT ledger rows. The cell stays HELD and the rows stay DRAFT: root "
        "countersigns, mints, flips (`milestone_successor2_flip.sh`) and re-pins the cell's own supply after the running flight. Held form, reproduced "
        "from `contracts.plan.require_owner_split_allowance`: the plan pins the path and the 64-hex sha256 of the committed bytes and refuses on any "
        "drift, any status other than `authorised`, any run id outside the permitted list (exactly the two new ids), another carrier, profile or split "
        "identity. Decision 250 (option A, same day) rules the documented rule-4 exception: `cross-flight-no-replicate`, declared DEV offset 0.7274 pp "
        "SLU-F1 / 0.20 pp intent, no-harm claim, margin 2.5, no in-chain replicate.")
    subs = [
        (r"OWNER SIGNATURE: the successor-2 allowance is an unsigned DRAFT.*?re-pins the fragment\.", b1_new),
        (r"MEASUREMENT RULE: measurement_design cross-flight-no-replicate is refused outright by instrument rule 4.*?before root countersigns\.", b2_new),
        (r"allowance DRAFT " + re.escape(ALLOWANCE) + r"; successor-1 package", "signed allowance " + ALLOWANCE + f" (sha256 {signed}); successor-1 package"),
        (r"\*\*blocked on the owner's signature\*\* of the allowance DRAFT",
         f"**held** (the allowance was SIGNED 2026-10-10, decision 251 A, sha256 `{signed}`; root countersigns, mints and flips)"),
        (r"## The allowance DRAFT and how signing works", "## The allowance (signed 2026-10-10) and how it was pinned"),
        (r"\(schema `saea-owner-split-allowance-v1`, status `draft-awaiting-owner-signature`\)",
         "(schema `saea-owner-split-allowance-v1`, status `authorised` since 2026-10-10; `draft-awaiting-owner-signature` at registration)"),
        (r"\*\*Signing = the owner's confirmation in conversation\.\*\*.*?\(commit 074e0cfb3\)\.", signed_para),
        (r"1\. \*\*Rule 4 \(needs a ruling\)\.\*\*", "1. **Rule 4 (RULED: decision 250, option A, 2026-10-10).**"),
        (r"which this brief forbids\) before countersigning\.",
         "which this brief forbids) before countersigning. RULED A by the owner on 2026-10-10 (decision 250): the documented exception stands."),
        (r"BLOCKED: allowance DRAFT " + re.escape(ALLOWANCE) + r" unsigned \(status draft-awaiting-owner-signature; the fragment pins 64 zeros until the re-pin\); "
         r"measurement design cross-flight-no-replicate awaits a rule-4 ruling;",
         f"allowance SIGNED 2026-10-10 (decision 251 A; status authorised; sha256 {signed}; pinned by the fragment); measurement design "
         "cross-flight-no-replicate carries the documented exception (decision 250 A);"),
        (r"\(DRAFT; sha256 of the draft bytes at registration ",
         f"(authorised, {SIGNED_AT_NOTE}; sha256 of the signed bytes {signed}; draft bytes at registration "),
        (r"a preparation-kind id of the successor-2 allowance DRAFT", "a preparation-kind id of the signed successor-2 allowance"),
        (r"a READ run id of the successor-2 allowance DRAFT", "a READ run id of the signed successor-2 allowance"),
        (r"named by the successor-2 allowance DRAFT " + re.escape(ALLOWANCE) + r", unsigned\)", "named by the signed successor-2 allowance " + ALLOWANCE + ")"),
    ]
    counts: dict[str, int] = {}
    for path in (readme_path, PREREG, protocol_path, facts_path, LEDGER):
        text = _read_text(path)
        for pattern, replacement in subs:
            text, n = re.subn(pattern, lambda m, r=replacement: r, text, flags=re.S if pattern.startswith(r"\*\*Signing") else 0)
            counts[pattern[:48]] = counts.get(pattern[:48], 0) + n
        _write_text(path, text)

    def draft_fn(doc: dict) -> None:
        doc["_draft_note"] = ("A DRAFT for root. It authorises nothing while its status is not 'decided'; the allowance it pins is SIGNED "
                              "(2026-10-10, decision 251 A).")
        doc["antecedents"]["allowance"] = {
            "path": ALLOWANCE, "sha256": signed,
            "note": f"{SIGNED_AT_NOTE}; status authorised; the committed draft's sha256 at registration was {DRAFT_BYTES_SHA}",
        }
        doc["registered_hashes"]["note"] = ("the fragment re-pinned to the signed allowance bytes (sign mode, 2026-10-10); "
                                            "repin_cell.py recomputes them at the flip")
        doc["decision_250_ruling"] = DECISION_250_RULING

    edit_json(draft_path, draft_fn)

    rename = {old_cfg: new_cfg, old_proto: new_proto}
    for _ in range(10):
        for path in tracked:
            text = _read_text(path)
            for old, new in rename.items():
                text = text.replace(old, new)
            _write_text(path, text)
        changed = False
        for path in tracked:
            now = sha_file(path)
            if now != latest[path]:
                rename[latest[path]] = now
                latest[path] = now
                changed = True
        if not changed:
            break
    else:
        raise SystemExit("hash propagation did not converge")
    print(json.dumps({"signed_allowance_sha256": signed, "old_composed_config_hash": old_cfg, "new_composed_config_hash": new_cfg,
                      "old_protocol_hash": old_proto, "new_protocol_hash": new_proto, "owner_allowance_pins_rewritten": n_pins,
                      "prose_replacements": counts, "file_hash_renames": len(rename) - 2}, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("mode", choices=("allowance", "derive", "register", "sign"))
    parser.add_argument("--study-commit", default=None)
    parser.add_argument("--registered-at", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    parser.add_argument("--branch", default="sonnet/testsample-successor2")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/sonnet-testsample-s2")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)
    if args.mode == "allowance":
        write_allowance()
        return 0
    if args.mode == "derive":
        derive()
        return 0
    if args.mode == "sign":
        return sign()
    if not args.study_commit or not args.registered_at:
        raise SystemExit("register needs --study-commit and --registered-at")
    return register(args)


def register(args) -> int:
    pins = sample_pins()
    s1_allowance = load(S1_ALLOWANCE)
    draft = load(ALLOWANCE)
    if draft.get("status") != "draft-awaiting-owner-signature":
        raise SystemExit("the successor-2 allowance is not the unsigned DRAFT")
    draft_sha = sha_file(ALLOWANCE)
    if draft["supersedes"]["sha256"] != sha_file(S1_ALLOWANCE):
        raise SystemExit("the draft does not supersede the committed successor-1 allowance bytes")
    if draft["permitted_run_ids"] != [RUN, FIT_RUN] or draft["read_run_ids"] != [RUN] or draft["preparation_run_ids"] != [FIT_RUN]:
        raise SystemExit("the draft does not permit exactly the run and FIT ids")
    proofs, s2 = prove(pins)
    document, cell, _ = composed_of(CELL)
    split = document["population"]["split_identity_hash"]
    fit = s2.values["native_contact_fit"]
    budget = document["family_budget"]
    config_hash = s2.config_hash
    proto_hash = protocol_hash(config_hash, s2.values["arm"], split)
    if cell["readiness"]["state"] != "held" or document["owner_allowance"] != {"path": ALLOWANCE, "sha256": ZERO}:
        raise SystemExit("the cell is not in the held form")
    if s2.values["scorers"] != [D.SCORER, "cost"] or split != s1_allowance["split"]["split_identity_hash"] or document["population"]["count"] != ROWS:
        raise SystemExit("the cell does not score the signed sample with the TEST sibling")
    if [c["cell"] for c in load(CAMPAIGN_PLAN)["cells"]] != [CELL]:
        raise SystemExit("the campaign plan must fly the one cell")
    own_null = {**W.scaled_null(), "note": "reused from successor 1 unchanged (no own null exists for the sample; fallback scaled, flagged)"}
    offset = DEV_OFFSET
    expected_slu = DEV_CLAIM["slu_pp"]
    plan_expect = {
        "intent_sum_pp": round(S1_TEST["intent_pp"] + DEV_CLAIM["intent_pp"], 2),
        "intent_less_declared_offset_pp": round(S1_TEST["intent_pp"] + DEV_CLAIM["intent_pp"] - offset["intent_pp"], 2),
        "slu_sum_pp": round(S1_TEST["slu_pp"] + DEV_CLAIM["slu_pp"], 2),
        "slu_less_declared_offset_pp": round(S1_TEST["slu_pp"] + DEV_CLAIM["slu_pp"] - offset["slu_pp"], 2),
        "coordinator_brief_stated_pp": {"intent": 5.3, "slu": 2.0},
        "note": ("CONTEXT only, never the bar. Components are all published: successor-1 test COMP-1b minus PLAN (intent +5.80, SLU +0.79, "
                 "post-stratified) plus the R5 DEV composed minus COMP-1b (intent +0.50, SLU +1.24). The brief said intent 'about +5.3'; "
                 "5.80 + 0.50 is 6.30, 6.10 after the 0.20 intent offset, so the brief's 5.3 is not reproduced by the stated components "
                 "(see open question 2 in the README). SLU (about +2.0) = 0.7945 + 1.2429 = 2.04 before any offset. The coordinator may re-declare."),
    }
    measurement = {
        RUN: {
            "admission": "no-harm",
            "bar_pp": HARM_MARGIN,
            "claim": "no-harm",
            "claims_benefit": False,
            "comparator_attempt_id": S1_COMP1B_ATTEMPT,
            "comparator_run_id": S1_COMP1B_RUN,
            "plan_comparator_attempt_id": S1_PLAN_ATTEMPT,
            "plan_comparator_run_id": S1_PLAN_RUN,
            "declared_flight_offset": {**offset, "scope": "DECLARED, borrowed from the DEV R5 read: the sample has NO in-chain replicate by design"},
            "expected_effect_basis": {
                "primary": "official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture, composed minus the SEALED successor-1 COMP-1b column",
                "dev_point": DEV_CLAIM,
                "reading": ("+1.24 pp is the DEV point of composed minus COMP-1b (CI95 [-0.29, +2.80], NEUTRAL). It sits under the 2.5 pp bar a "
                            "cross-flight read can resolve, so the cell claims NO benefit: its registered claim is the EFFICIENCY RESULT (2 contacts "
                            "per row against about 4 for COMP-1b, so about half the contacts) plus the v4g delivered gain. Under ONE normaliser the "
                            "DEV graph-and-supply effect is only +0.27 pp (v4g(A2 arm) -> composed), so most of the +1.24 is the v4g delivered gain, "
                            "which the DEV rule selection makes in-sample there and a fresh sample tests honestly."),
                "vs_plan_context": plan_expect,
            },
            "expected_effect_pp": expected_slu,
            "expected_effect_status": "the R5 DEV point (owner decision 139: a measured number, not a prior), declared at registration",
            "harm_margin_pp": HARM_MARGIN,
            "harm_margin_pp_by_metric": {"intent_accuracy": HARM_MARGIN, "slu_f1": HARM_MARGIN},
            "measurement_design": "cross-flight-no-replicate",
            "design_statement": ("CROSS-FLIGHT AGAINST SEALED COLUMNS, NO IN-CHAIN REPLICATE, BY DESIGN: the allowance permits exactly one new generation "
                                 "run id, the sample's successor-1 PLAN and COMP-1b columns are sealed and must not be re-flown, and a second composed "
                                 "flight would consume a second attempt. Instrument rule 4 (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md "
                                 "section 3) refuses 'a single cross-flight contrast against an older sealed comparator with no in-chain replicate' "
                                 "outright (stage3_effect_floor_check.py would report this declaration as a blocking cross-flight-no-replicate finding; the gate's "
                                 "scope test is the 'stage3' token in the fragment stem or experiment id, which this cell, like successor 1, does not carry, so "
                                 "today the gate does not see the cell and the refusal is NOT mechanically enforced). "
                                 "It is declared in this honest form rather than relabelled; the owner/coordinator must rule on the exception before the "
                                 "flip (README open question 1). The DEV flight offset (0.73 pp SLU / 0.20 intent) is carried as the declared offset."),
            "note": ("SUCCESSOR-2 = the NX R5 composed arm on the signed test sample (owner decisions 233 and 241). Primary: official pooled SLU-F1 "
                     "(post-stratified natural mixture; equal-stratum beside it); guard: intent (scenario_action exact). Contrast: composed minus the SEALED "
                     "successor-1 COMP-1b column (primary comparator, same components minus review-off and v4g); beside it composed minus the SEALED "
                     "successor-1 PLAN column. No claim of benefit. tuning_roster / read_roster (item D3): the vote pool and the centroid key are TRAIN "
                     "construction artifacts, the v4 rule set behind v4g was selected on the A2 DEV pool and confirmed on TRAIN Fold A and Fold B, and COMP-1b was "
                     "selected on DEV-2000-ADDED; all are disjoint from the sample by its disjointness proof (docs/checks/speech-aware-evidence-acquisition/"
                     "2026-09-27-slurp-test-sample-roster/disjointness.json, CLEAN); nothing was chosen or tuned on the sample."),
            "own_null": own_null,
            "primary_metric": "official pooled SLU-F1 (slurp-slu-official-test), composed minus the sealed successor-1 COMP-1b column beyond the declared DEV flight offset; intent accuracy (scenario_action exact) the non-inferiority guard",
            "primary_metric_key": "slu",
            "read_roster": D.ROSTER_ID,
            "roster": f"TEST-SAMPLE ({D.ROSTER_ID}, split identity {split}), 3,010 recordings / 682 prompts",
            "rows": ROWS,
            "tuning_roster": ["slurp-train-construction-pool-agree-kprobe-r01-excluded", "SLURP-EVO-FOLD-A-V2", "SLURP-DEV-2000-ADDED-V1"],
        }
    }
    gpu_est_h = round(ROWS * CONTACTS_PER_ROW / 24 / 60, 2)
    caps = {k: budget[k] for k in sorted(budget)}
    decision_rule = (
        "Read SUCCESSOR2-COMPOSED against the SEALED successor-1 COMP-1b column (SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR1-COMP1B-V1) on the same "
        "3,010 rows, CROSS-FLIGHT (the columns flew 2026-10-01; nothing is re-flown; there is no in-chain replicate on the sample by design). PRIMARY: "
        "official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture (equal-stratum beside it), paired per recording with a "
        f"prompt-clustered bootstrap, {DRAWS:,} draws, seed {SEED}. GUARD: intent accuracy (scenario_action exact), same contrast. DECLARED FLIGHT OFFSET o "
        f"(borrowed from the DEV R5 read, not measured on the sample): |o| = {offset['slu_pp']} pp SLU-F1 / {offset['intent_pp']} pp intent. HARM MARGIN {HARM_MARGIN} pp "
        f"(not tighter than the cross-flight sampling floor). NEUTRAL iff the CI95 lower bound of (composed minus COMP-1b) on SLU-F1 and on intent is at or above "
        f"-{HARM_MARGIN} pp and the read is not HARM: an EFFICIENCY RESULT -- the composition keeps COMP-1b's accuracy within what a cross-flight read can see at "
        "about half the contacts; never reported as a gain. HARM iff the CI95 upper bound of (composed minus COMP-1b) on SLU-F1 or on intent is below -|o| (a resolved "
        f"loss beyond the declared offset, owner decision 25). UNRESOLVED iff the lower bound is under -{HARM_MARGIN} pp while neither HARM nor NEUTRAL. NOMINATED "
        "is NOT a registered outcome of this cell (claims_benefit false): a point above the bar would be REPORTED, never claimed, and would need its own replicated read. "
        "Reported beside, CONTEXT ONLY: composed minus the sealed successor-1 PLAN column (intent and SLU-F1; expectation in the facts), per-intent and per-scenario "
        "tables in the post-stratified natural-mixture and equal-stratum weightings (58 intents), the recording-channel split, entity TP/FP/FN, and the cost table (contacts "
        "and tokens per row against COMP-1b's 12,214 contacts). The verdict word is the coordinator's (owner decision 139). A milestone development read (owner decisions 28, 151), never a test claim."
    )
    allowance_block = {
        "path": ALLOWANCE, "status_at_registration": draft["status"], "sha256_of_draft_bytes_at_registration": draft_sha,
        "sha256_pinned_in_the_fragment": ZERO,
        "read_run_ids_used": [RUN],
        "preparation_run_ids_used": [FIT_RUN],
        "supersedes": draft["supersedes"],
        "smoke": "NOT REGISTERED: the allowance names no smoke run id and a smoke under the read run id would consume its one attempt (decisions 151 / 207 / 213). The form proof is the R5 composed arm's own four-row DEV smoke (SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-SMOKE-4-V1) plus the model-free core.flight.cli check at the flip.",
        "attempts": "ONE per run id, ever; no recovery, no resume, no re-score, no re-read (allowance attempt_budget and milestone_rule)",
        "signing": ("SIGNING = the owner's confirmation in conversation. The coordinator then sets the draft's status to 'authorised' and fills the signature block, "
                    "records the sha256 of those committed bytes, and re-pins the fragment's owner_allowance to them (scripts/flights/repin_cell.py). Until then the "
                    "fragment pins 64 zeros and contracts.plan.require_owner_split_allowance refuses the plan (no 64-hex match to the bytes, then status)."),
    }
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": "Every model-free fact the SUCCESSOR-2 test-sample milestone registration rests on, and the CANONICAL stage3_measurement block.",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "status": "REGISTERED_BEFORE_CONTACT_HELD_BLOCKED_ON_OWNER_SIGNATURE",
        "owner_decisions": {
            "25": "a measured loss on either guard is HARMFUL",
            "28/86": "development numbers only; never a test claim",
            "139": "no prior; a number derived from a measured read is not a prior",
            "141": "a coverage-guaranteed test sample is permitted for milestone comparison",
            "151": "the sample allowance (v1); first contact gated on a reported dev-admitted composed arm",
            "207/213": "one-shot terms: one attempt per run id, no smoke, no recovery, no re-read",
            "233": "a second test-sample allowance (same terms as v2) for the R5 composed read",
            "238/240": "R5 flies; the composed arm is COMP-1b on lock v2.2 (v4g), review-off, no-harm claim at about half the contacts",
            "241": "\"As you suggest.\" -- the second test-sample allowance is drafted once R5 reads NOMINATED or NEUTRAL; the composed arm flies once on the signed sample against the sealed PLAN and COMP-1b columns",
        },
        "r5_read_basis": {"result": "NEUTRAL on DEV-2000-ADDED, 2026-10-10", "claim": DEV_CLAIM, "offset": DEV_OFFSET,
                          "package": R5_PACKAGE, "read_run_id": R5_READ_RUN},
        "allowance": allowance_block,
        "rows": ROWS,
        "the_composition": COMPOSITION,
        "stage3_measurement": measurement,
        "cells": {"composed": {
            "cell": CELL, "experiment": CELL, "run_id": RUN, "attempt_id": ATTEMPT, "fit_run_id": fit["run_id"],
            "fit_attempt_id": fit["attempt_id"], "fit_contact_cap": fit["contact_cap"], "baseline_fragment": BASELINE,
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"], "arm": s2.values["arm"], "rows": ROWS,
            "split_identity_hash": split, "split_role": document["execution_plan"]["split_role"], "composed_config_hash": config_hash,
            "protocol_hash": proto_hash, "policy": s2.values["policy"], "scorers": s2.values["scorers"],
            "owner_allowance": s2.values.get("owner_allowance"), "readiness_state": cell["readiness"]["state"],
        }},
        "comparators_sealed": {
            "primary": {"run_id": S1_COMP1B_RUN, "attempt_id": S1_COMP1B_ATTEMPT, "package": S1_PACKAGE,
                        "role": "same components minus review-off and v4g; the contrast the registered claim is read against"},
            "plan": {"run_id": S1_PLAN_RUN, "attempt_id": S1_PLAN_ATTEMPT, "package": S1_PACKAGE, "role": "the direct-call-era locked plan; context"},
            "read_note": S1_READ_NOTE, "re_flown": False,
        },
        "sample_preparation_pins": {
            "pins": [{"relpath": k, "sha256": pins[k]} for k in sorted(pins)],
            "note": "Reused BY PIN from successor 1 (its registered-facts sample_preparation_pins); never rebuilt, never re-encoded. The cell's own first-phase supply is minted at the flip (item E16): 64 zeros until then.",
        },
        "composed_config_diffs": {**proofs, "derive_script": {"relpath": "scripts/flights/nx/write_slurp_milestone_successor2_registration.py",
                                                              "sha256": sha_file("scripts/flights/nx/write_slurp_milestone_successor2_registration.py")}},
        "budget_arithmetic": {
            "family_budget": caps,
            "derivation": [
                f"generation_calls_cap = {ROWS:,} rows x {CONTACTS_PER_ROW} contacts per row (policy phase-native-module-v1-c2: Perception 1 + Solver 1; Reviewer and Planner never visited, max_revisions 0) = {ROWS * CONTACTS_PER_ROW:,}, run-cumulative; also the expected spend",
                f"fit_endpoint_calls_cap = {ROWS:,} x {CONTACTS_PER_ROW} x (max_speech_packets 1 + 3 endpoints) = {ROWS * CONTACTS_PER_ROW * 4:,} (structural, as the R5 DEV cell's 1,000 x 2 x 4 = 8,000)",
                f"native_task_contract_calls_cap = {budget['native_task_contract_calls_cap']:,} (as R5: equal to the generation cap)",
                f"repeated_speech_audio_seconds_cap = ceil({CONTACTS_PER_ROW} x 8,206.436875) = {budget['repeated_speech_audio_seconds_cap']:,}",
                f"gpu_hours_fit_inclusive = the R5 DEV cell's 1.5 per 1,000 rows scaled to 3,010 and rounded up to 0.1 = {budget['gpu_hours_fit_inclusive']}; the realised-rate estimate is {ROWS * CONTACTS_PER_ROW:,} contacts / 24 per minute (R5's realised rate) = {gpu_est_h} h, a ceiling is not a target",
                "one official complete slurp-slu-official-test score over the complete 3,010-row manifest, never sharded",
            ],
        },
        "report_form": {
            "headline": "official pooled SLU-F1 primary and intent accuracy guard, reported SEPARATELY, composed minus the sealed successor-1 COMP-1b column (and beside it minus the sealed PLAN column) on the same rows",
            "weightings": "natural mixture = post-stratified to full-test per-intent shares (population-counts-v1.json, scorer-side strata); equal stratum = 1/58 over the intents present (general_greet is closure-only)",
            "per_stratum": "per-intent and per-scenario tables in both weightings",
            "claim_wording": "a MILESTONE read: development evidence under owner decision 28, never a test claim, never the final read; it may say whether the composed arm kept COMP-1b's accuracy on a test sample at about half the contacts",
        },
        "post_stratification_read": load(S1_PACKAGE + "/registered-facts-v1.json")["post_stratification_read"],
        "authority_relpaths": [OWNER_DECISIONS, ALLOWANCE, S1_ALLOWANCE, S1_PACKAGE + "/README.md", R5_PACKAGE + "/README.md", W.INSTRUMENT],
        "blockers_before_the_flip": [
            "OWNER SIGNATURE: the successor-2 allowance is an unsigned DRAFT (status draft-awaiting-owner-signature). Signing is the owner's confirmation in conversation; the coordinator then flips the status, records the sha256 and re-pins the fragment.",
            "MEASUREMENT RULE: measurement_design cross-flight-no-replicate is refused outright by instrument rule 4 (stage3_effect_floor_check.py would block it were the cell in its scope; it is not, by stem naming, so nothing enforces it mechanically); the coordinator/owner must rule on the exception (or register a different design) before root countersigns.",
            "READER: stage3_paired_read.py --package requires arms.in_chain_replicate and checks both arms against the allowance; this design has none, so the registered driver is the pair-mode wrapper " + READ_DRIVER + " (see README open question 3).",
            "ROOT: countersigns the three DRAFT ledger rows (naming the conversational report of R5's NEUTRAL read to the owner), mints the admission receipt, then repin_cell.py --set-ready mints the cell's own first-phase supply.",
            "SERVING/LAUNCH: standard four-slot decoder-only service, clean frozen code, registered FIT, launch gates (as successor 1).",
        ],
        "prohibitions": [
            "No contact before every blocker above is cleared, root countersigns the rows, mints the decision receipt and the cell is flipped.",
            "ONE attempt per run id, ever: no re-fly, no recovery, no resume, no re-score, no re-projection, no best-of, no tuning on the sample.",
            "No smoke on the sample; no re-flight, re-score or re-read of the sealed successor-1 columns; no closure-roster or FULL-test contact.",
            "No k, tau, fuse_coverage, w_prior, store, release, snapshot, roster, role-graph or geometry change. --allow-output-change is never passed.",
            "No utterance text, gold label, transcript or model output is printed or persisted by any read.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)
    ids = facts["cells"]["composed"]
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-milestone-successor2-composed-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_HELD_BLOCKED_ON_OWNER_SIGNATURE",
        "the_question": ("Does the NX R5 composed arm, NEUTRAL on DEV-2000-ADDED, keep the sealed successor-1 COMP-1b column's accuracy on the signed test "
                         "sample at about half the contacts, with official SLU-F1 primary and intent the guard?"),
        "the_composition": COMPOSITION,
        "cells": {"composed": {k: ids[k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "policy")}},
        "decision_rule_fixed_here": decision_rule,
        "stage3_measurement": measurement,
        "one_shot_semantics": allowance_block["attempts"],
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": facts["composed_config_diffs"]},
        "blockers_before_the_flip": facts["blockers_before_the_flip"],
        "development_numbers_only": "Every number is a milestone development number (owner decisions 28, 86, 151); never a test claim and never the final read.",
        "failure_policy": document["failure_policy"],
        "authority": f"owner decisions 233 and 241 ({OWNER_DECISIONS}); allowance DRAFT {ALLOWANCE}; successor-1 package {S1_PACKAGE}; R5 package {R5_PACKAGE}; the instrument {W.INSTRUMENT}",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)
    plan_shas = {}
    for kind in ("generation", "fit"):
        is_fit = kind == "fit"
        route = ("The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                 if is_fit else
                 f"Shared core.flight.cli campaign over {CAMPAIGN_PLAN} (one cell), one official slurp-slu-official-test score at finalize. No smoke step.")
        plan = {
            "schema": f"saea-registered-{kind}-plan-v1", "plan_kind": kind, "cell": CELL, "experiment": CELL,
            "composed_config_hash": config_hash, "registered_at_utc": args.registered_at, "status": protocol["status"],
            "source_tree": protocol["source_tree"], "preparation_base_commit": args.study_commit, "expected_session_id": SESSION,
            "unused_budget_is_not_attempt_authority": True,
            "execution_plan": {
                "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition", "carrier_lock_key": "slurp",
                "run_id": FIT_RUN if is_fit else RUN, "attempt_id": FIT_ATTEMPT if is_fit else ATTEMPT,
                "execution_profile": "bounded-discovery-probe", "split_role": "final-report", "split_identity_hash": split,
                "protocol_hash": proto_hash,
                "planned_model_calls": budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"],
                "planned_speech_audio_seconds": budget["repeated_speech_audio_seconds_cap"],
                "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                "owner_allowance": {"path": ALLOWANCE, "sha256": ZERO},
            },
            "family_budget": budget, "execution_route": route,
            "prepared_phase_supply": {"relpath": f"prepared/{RUN}/phase-supply-v1.json", "sha256": ZERO,
                                       "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip (item E16); 64 zeros until then; --allow-output-change must never be passed."},
            "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "purpose": f"{FIT_RUN if is_fit else RUN}: " + ("It measures request envelopes only and reads nothing." if is_fit else decision_rule),
            "quality_read_gate": "No task-quality read before the manifest is complete and sealed with one successful complete official slurp-slu-official-test score and the READ row is root countersigned.",
        }
        plan_shas[kind] = wjson(f"{PACKAGE}/{kind}-plan-registered-v1.json", plan)
    # population counts: successor 1's committed bytes (the roster is the same), copied verbatim
    counts_text = D.rd(S1_PACKAGE + "/population-counts-v1.json")
    counts_sha = W.wr(PACKAGE + "/population-counts-v1.json", counts_text)
    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": RECIPE_ID,
        "read_run_id": READ_RUN,
        "title": "Test-sample SUCCESSOR2-COMPOSED -- the NX R5 composed arm against the sealed successor-1 COMP-1b and PLAN columns on SLURP-TEST-SAMPLE-3010-V1",
        "registered_at_utc": args.registered_at,
        "arms": {
            "arm": {"run_id": RUN, "attempt_id": ATTEMPT, "fit_run_id": FIT_RUN, "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "comparator": {"run_id": S1_COMP1B_RUN, "attempt_id": S1_COMP1B_ATTEMPT, "role": "the SEALED successor-1 COMP-1b column: the cross-flight primary comparator the registered claim is read against (sealed 2026-10-01; never re-flown)"},
            "plan_comparator": {"run_id": S1_PLAN_RUN, "attempt_id": S1_PLAN_ATTEMPT, "role": "the SEALED successor-1 PLAN column (the direct-call-era locked plan); context"},
        },
        "no_in_chain_replicate": "By design: one new generation run id only. The DEV flight offset is declared, not measured (declared_flight_offset).",
        "declared_flight_offset": DEV_OFFSET,
        "read_driver": {
            "command": f"bash {READ_DRIVER}",
            "passes": [
                "vs-comparator (composed minus the sealed successor-1 COMP-1b column; cross-flight; THE REGISTERED CLAIM, read beyond the declared offset)",
                "vs-plan (composed minus the sealed successor-1 PLAN column; cross-flight; context)",
            ],
            "scorer": D.SCORER,
            "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned and all three sealed run manifests exist",
            "strata_source": "scorer: post-stratification by gold intent INSIDE the official-scoring step (--strata-source scorer), aggregates only; see registered-facts-v1.json post_stratification_read",
        },
        "resampling": {"bootstrap_draws": DRAWS, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": SEED, "unit": "prompt cluster (paired)"},
        "weightings": {
            "natural_mixture": f"POST-STRATIFIED (PRIMARY weighting): per-intent values weighted by the full-test per-intent shares in population-counts-v1.json (roster receipt {D.ROSTER_RECEIPT}); the raw roster mean is NOT the natural-mixture number",
            "equal_stratum": "1/58 over the intents present in the sample (reported beside the primary weighting)",
            "post_stratification": "58 strata carried of 59 counted; computed and bootstrapped inside the scorer process exactly as in successor 1 (registered-facts-v1.json post_stratification_read); aggregates only",
        },
        "steps": [
            "1. Refuse unless the composed manifest is COMPLETE at 3,010 rows with this registration's composed config hash (as re-pinned at the flip), sealed, with one successful complete official slurp-slu-official-test score, the two sealed successor-1 manifests are present, and the READ row is root countersigned.",
            "2. THE DELIVERY CHECK (gold-free): the composed cell's flown first-phase boundary selections equal its own prepared supply. A mismatch is an engineering defect, is reported, and consumes the milestone (no re-fly).",
            "3. THE STRUCTURAL CHECK (gold-free): exactly 2 contacts per row (perception, solver), no Reviewer or Planner row, every row delivered through saea-deliver-normalise-v4g.",
            f"4. Primary: official pooled SLU-F1 post-stratified, composed minus the sealed COMP-1b column, paired per recording, prompt-clustered, {DRAWS:,} draws, seed {SEED}. Guard: intent accuracy. Equal-stratum beside it. Apply the protocol's rule against the declared offset {DEV_OFFSET['slu_pp']} / {DEV_OFFSET['intent_pp']} and the harm margin {HARM_MARGIN}.",
            "5. Context: composed minus the sealed PLAN column; per-intent and per-scenario tables in both weightings; recording-channel split; entity TP/FP/FN with the zero-gold-row emission count; the cost table.",
            "6. Write the read under its own id; every number is a MILESTONE development number (owner decisions 28 and 151), never a test claim.",
        ],
        "output": {"analysis_root": ANALYSIS_ROOT},
        "boundary": "A milestone read on the signed test sample. No utterance text, transcript, gold label string or model output is printed or persisted: ids, counts, rates and hashes only.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)
    eligible = [RUN, FIT_RUN]
    draft_doc = {
        "_draft_note": "A DRAFT for root. It authorises nothing while its status is not 'decided' and the allowance it pins is unsigned.",
        "schema": "saea-campaign-decision-v1", "decision_id": DECISION_ID, "status": "DRAFT-NOT-MINTED", "recorded_at_utc": None,
        "owner": "root", "coordinator": None, "eligible_run_ids": eligible,
        "cell_kind": "Test-sample SUCCESSOR-2 milestone read (owner decisions 233 and 241): the NX R5 composed arm, one attempt, ever.",
        "decision": "Fly SUCCESSOR2-COMPOSED once on SLURP-TEST-SAMPLE-3010-V1; read cross-flight against the sealed successor-1 COMP-1b and PLAN columns, SLU-F1 primary, intent guard, no-harm.",
        "authorization_basis": "Owner decisions 233 and 241; R5 read NEUTRAL on DEV-2000-ADDED 2026-10-10; the owner's signature of the successor-2 allowance; the coordinator's conversational report.",
        "first_contact_report": {"date": None, "arm": None, "note": "root fills this with the conversational report before minting"},
        "antecedents": {
            "allowance": {"path": ALLOWANCE, "sha256": None, "note": "filled with the SIGNED bytes' sha256 at the re-pin; the committed draft's sha256 at registration was " + draft_sha},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "r5_registration": {"path": R5_PACKAGE + "/registered-facts-v1.json", "sha256": sha_file(R5_PACKAGE + "/registered-facts-v1.json")},
            "registration_base_commit": args.study_commit,
        },
        "budget": {**caps, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "A milestone development read (owner decisions 28, 151). No test claim, no superiority, generalisation, confirmatory or paper-scale claim. claim: no-harm.",
        "failure_policy": document["failure_policy"],
        "not_authorized": ["any contact before every blocker is cleared and the cell is flipped",
                           "a second attempt of the run id, a recovery, a resume, a re-score or a re-read",
                           "a smoke, a re-flight of the sealed successor-1 columns, the closure roster or the FULL test split",
                           "--allow-output-change on the re-pin tool"],
        "population": {"count": ROWS, "split_identity_hash": split, "split_role": "final-report", "roster": D.ROSTER_ID, "closure_contact_authorized": False},
        "registered_hashes": {"composed": {"composed_config": config_hash, "protocol": proto_hash},
                              "note": f"the fragment exactly as committed at {args.study_commit}; repin_cell.py recomputes them at the flip"},
        "service": {"expected_session_id": SESSION, "model_fragment": cell["model_fragment"], "slots": 4, "slot_tokens": 24576, "decoder_only": True, "no_child_start_stop": True},
    }
    draft_doc_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft_doc)
    identity_map = {
        "owner_decisions": [233, 241],
        "dispatch_authority": False,
        "generation_rows": ROWS,
        "contacts_per_row": CONTACTS_PER_ROW,
        "r5_dev_to_successor2_replacements": {
            R5_RUN: RUN, R5_FIT_RUN: FIT_RUN,
            "attempt-slurp-native-stage3-nx-r5-composed-dev2000-added-generation-v1": ATTEMPT, R5_FIT_ATTEMPT: FIT_ATTEMPT,
            R5_CELL: CELL, R5_BASELINE: BASELINE, R5_PACKAGE: PACKAGE,
            **{a: b for a, b in D.ROSTER_SUBSTITUTIONS},
        },
        "leaves_changed_from_the_r5_dev_cell": {k: v for k, v in proofs["s2_vs_r5_dev"].items() if v},
        "leaves_unchanged": "every other leaf of the composed config: module block (lock v2.2, review off, components), policy phase-native-module-v1-c2, native_episode, phase_material, phase_tools, delivery normaliser, decoding, geometry, knowledge stores except their roster-bound query and agreement pins",
        "reused_from_successor1": {"sample_preparation_pins": sorted(pins), "package": S1_PACKAGE},
    }
    map_sha = wjson(PACKAGE + "/successor-identity-map.json", identity_map)
    qualification = f"""# Successor 2: read qualification procedure (pre-registered; nothing has been read)

Pre-registered {args.registered_at[:10]} in the form of successor 1's `read-qualification-v1.md`
(`{S1_PACKAGE}/read-qualification-v1.md`). Root qualifies the composed run BEFORE reading any scientific output:

1. The composed attempt is FINALIZED at 3,010 rows with a verified seal and exactly one successful official `{D.SCORER}` score; no failed jobs.
2. Fresh streamed hashes revalidate the final manifest and every referenced output, trace, trace manifest, score, serving receipt, generation manifest, phase summary and score-ledger artifact. Hashing does not interpret task content.
3. The two SEALED successor-1 columns (`{S1_COMP1B_RUN}`, `{S1_PLAN_RUN}`) are revalidated against `docs/receipts/continuation/2026-10-01-milestone-successor1-pair-complete.json`; they are NOT re-flown, re-scored or re-read.
4. The shared reader's delivery check compares the arm's flown boundary sets with its own prepared supply (aggregate row equality and mismatch counts only; a mismatch is an engineering defect, never permission to rerun).
5. Root countersigns the READ row `{READ_RUN}` only for the registered comparison; the driver `{READ_DRIVER}` refuses before any score is opened otherwise.

No test evidence may enter the system-text optimizer, proposer inputs, candidate selection or tuning. No allowance or scientific threshold changes.
"""
    qual_sha = W.wr(PACKAGE + "/read-qualification-v1.md", qualification)
    blockers_md = "\n".join(f"{i}. {b}" for i, b in enumerate(facts["blockers_before_the_flip"], 1))
    s1_readme = D.rd(S1_PACKAGE + "/README.md").strip().split("\n")
    quote_custody = "\n".join("> " + line for line in s1_readme[2:6] if line.strip())
    quote_analysis = "\n".join("> " + line for line in s1_readme[13:18] if line.strip())
    rule_quote = s1_allowance["milestone_rule"]
    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readme = f"""# SLURP test-sample successor 2: the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}` (owner decisions 233 and 241). The cell is **held** and
**blocked on the owner's signature** of the allowance DRAFT. Nothing here flies, mints, flips, re-pins or countersigns.

**What it is.** {COMPOSITION} It is the sealed R5 DEV cell (`{R5_CELL}`, COMP-1b on module lock v2.2, review-off, policy
`phase-native-module-v1-c2`, ceiling 2) with the leaves moved that moved A2's arm to the successor-1 COMP-1b cell: the dataset view,
roster receipt, packet promotion receipt, the sample's speech-query vectors, alias and agreement table, the row-scaled budgets, the
final-report split role, the TEST scorer sibling `{D.SCORER}`, the one-attempt failure policy, the allowance pin and the run / attempt /
FIT ids. `successor-identity-map.json` lists the replacements and `registered-facts-v1.json` (`composed_config_diffs`) PROVES, from
`core.config.compose`, that nothing else moved: every roster- and role-bound leaf equals the sealed successor-1 COMP-1b cell's value, and
the composition delta (successor-1 COMP-1b to this cell) equals the R5 delta on DEV (A2 arm to R5 composed), path for path. Derived by
`scripts/flights/nx/write_slurp_milestone_successor2_registration.py`.

**Identities.** Cell `{CELL}`, baseline `{BASELINE}`, run `{RUN}` (attempt `{ATTEMPT}`), FIT `{FIT_RUN}` (attempt `{FIT_ATTEMPT}`), READ
`{READ_RUN}`, recipe `{RECIPE_ID}`. Roster `{D.ROSTER_ID}` (3,010 recordings / 682 prompts; split identity `{split}`). Sample preparations
(packets, query vectors, alias, agreement table) are successor 1's, reused by pin (`sample_preparation_pins`), never rebuilt.

**One-shot terms (decisions 151 / 207 / 213), carried unchanged.** ONE attempt per id, no smoke on the sample, no recovery, no re-read, no
selection. The two comparators are the SEALED successor-1 columns `{S1_COMP1B_RUN}` (primary; same components minus review-off and v4g) and
`{S1_PLAN_RUN}` (the direct-call-era baseline); nothing is re-flown.

## Cloned from successor 1 (quoted, not redesigned)

From `{S1_PACKAGE}/README.md` (custody and execution):

{quote_custody}

From the same README (analysis, fixed before contact):

{quote_analysis}

From the successor-1 allowance `milestone_rule`: "{rule_quote}"

Cloned files: `registered-facts-v1.json`, `protocol-registered-v1.json`, `generation-plan-registered-v1.json`, `fit-plan-registered-v1.json`,
`analysis-recipe-v1.json`, `population-counts-v1.json` (successor 1's bytes, the same roster), `root-admission-draft-v1.json`,
`read-qualification-v1.md`, `successor-identity-map.json`, the preregistration `{PREREG}`, fragments
`configs/experiment/{CELL}.json` and `configs/baseline/{BASELINE}.json`, the one-cell campaign plan `{CAMPAIGN_PLAN}`, and the read wrapper
`{READ_DRIVER}`. Not cloned, because it records a post-hoc defect: `sparse-supply-reader-correction.md`. Not cloned, because it has no
counterpart: successor 1's PLAN plan documents (no new comparator is flown).

## Measurement

`cross-flight-no-replicate` (stated plainly: there is NO in-chain replicate on the test sample, by design -- one new generation id, sealed
comparators that must not be re-flown). n = 3,010 (682 prompts). Primary: official pooled SLU-F1 (`primary_metric_key: slu`),
post-stratified natural mixture (primary weighting) with equal-stratum beside it; guard: intent. `admission: no-harm`, `claims_benefit:
false`, `harm_margin_pp {HARM_MARGIN}`, `expected_effect_pp {expected_slu}` (the DEV point of composed minus COMP-1b). The claim is the
EFFICIENCY RESULT (2 contacts per row; successor 1's COMP-1b flew 12,214 contacts on 3,010 rows, about 4.06 per row) plus the v4g delivered
gain. Declared flight offset (DEV, from the R5 read): {DEV_OFFSET['slu_pp']} pp SLU-F1 / {DEV_OFFSET['intent_pp']} pp intent. Guard null: successor 1's FALLBACK
(h_SLU {own_null['h_slu']}, h_intent {own_null['h_intent']}; recording-scaled {own_null['h_slu_recording_scaled']} / {own_null['h_intent_recording_scaled']}), flagged.
Resampling: prompt-cluster paired bootstrap, {DRAWS:,} draws, seed {SEED}. Declared effects vs the sealed PLAN column (context):
{json.dumps(plan_expect['intent_sum_pp'])} pp intent / {json.dumps(plan_expect['slu_sum_pp'])} pp SLU-F1 before offsets (see open question 2).

## Budgets

| item | value |
| --- | ---: |
| rows | {ROWS:,} |
| contacts per row (exact, policy c2) | {CONTACTS_PER_ROW} |
| generation calls cap | {budget['generation_calls_cap']:,} |
| FIT endpoint cap (structural: rows x 2 x (1 + 3)) | {budget['fit_endpoint_calls_cap']:,} |
| native task-contract calls cap | {budget['native_task_contract_calls_cap']:,} |
| repeated speech-audio seconds cap | {budget['repeated_speech_audio_seconds_cap']:,} |
| planned GPU hours (FIT inclusive) | {budget['gpu_hours_fit_inclusive']} (realised-rate estimate {gpu_est_h} h at R5's 24 contacts/min) |
| official complete scoring jobs | 1 |

## The allowance DRAFT and how signing works

`{ALLOWANCE}` (schema `saea-owner-split-allowance-v1`, status `draft-awaiting-owner-signature`) supersedes the successor-1 allowance
(`{S1_ALLOWANCE}`, sha256 `{draft['supersedes']['sha256']}`) by scope "new successor run identities only"; it permits EXACTLY `{RUN}` (read)
and `{FIT_RUN}` (preparation). Its `dated_owner_decision` quotes decision 241 and its `first_contact_gate.basis` quotes the R5 result. The
READ id `{READ_RUN}` is a model-free analysis identity, not a permission (as in successor 1). Draft bytes at registration: sha256 `{draft_sha}`.

**Signing = the owner's confirmation in conversation.** The coordinator then (1) sets `status` to `authorised` and fills the `signature`
block, (2) commits those bytes and records their sha256, (3) re-pins the fragment's `owner_allowance` to them (`scripts/flights/repin_cell.py`,
never `--allow-output-change`). Held form, reproduced from `contracts.plan.require_owner_split_allowance`: the plan pins the path and the
64-hex sha256 of the committed bytes and refuses on any drift or any status other than `authorised`; until signing the fragment and both plan
documents therefore carry the path with **64 zeros** (the repository's pending-pin convention) as the TODO-sha placeholder, and the gate
refuses the plan -- as it refused the unsigned v2 draft of decision 207 (commit 074e0cfb3).

## Blockers before the flip

{blockers_md}

## Open questions (everything successor 1 required that this package could not reproduce without a contact or a ruling)

1. **Rule 4 (needs a ruling).** Instrument rule 4 refuses `cross-flight-no-replicate` outright (`stage3_effect_floor_check.py --explain` prints
   the refusal for that design; the gate does not scope this cell in by name, exactly as it does not scope successor 1, so its run passes
   without seeing the cell). Successor 1 satisfied rule 3 because its PLAN replicate flew in the same chain. Here the allowance gives one new generation id, so no replicate can fly. The declaration is honest, not relabelled; the
   coordinator/owner must rule an exception (or change the design, e.g. a second composed id, which this brief forbids) before countersigning.
2. **Declared PLAN-contrast numbers.** The brief states composed-minus-PLAN intent "about +5.3 = 5.80 + 0.50 minus the offset". The stated
   components give 6.30 (6.10 after the 0.20 intent offset); +5.3 needs a 1.0 pp discount that no published number supplies. SLU "about +2.0" is
   0.7945 + 1.2429 = 2.04 undiscounted. Both are recorded with their arithmetic and flagged; they are context only and gate nothing.
3. **Reader.** `stage3_paired_read.py --package` requires `arms.in_chain_replicate` and checks BOTH arm ids against the allowance
   (`_require_final_report_conditions`), and the successor-1 columns are not in this allowance by the "EXACTLY" instruction. The registered driver
   `{READ_DRIVER}` therefore uses the reader's pair mode with the final-report conditions re-stated in the wrapper (TEST scorer, scorer-side
   strata, post-stratified weighting, countersigned READ row, sealed manifests). It is syntax-checked only; it has not been run. A reader change
   (accept sealed comparators by recipe) is the cleaner fix and is out of scope here.
4. **Own supply digest.** The selection-output digest the flip should expect for this cell's own first-phase supply is not recorded in a committed
   receipt for successor 1's COMP-1b (the receipt gives row counts and the pin only); the flip's re-derivation will compare against that supply.
5. **Admission mint / flip / queue wrappers.** Successor 1 had none of its own (it used the shared re-pin entry point); none is written here. Root's
   mint of `{DECISION_RELPATH}` follows successor 1's route.
6. **READ id in the allowance.** Read as "the run id in the read list, the FIT id in the preparation list"; the analysis READ id is not listed as a
   permission. If the owner wants it listed, that is a one-line change to the draft.

## Ledger and checks

Three DRAFT rows (run, FIT, READ) are appended at the END of `docs/exposure-ledger.md`, root countersignature pending. Preflight:
`tests/unit/test_milestone_successor2_cell_registration.py` (model-free).

```json
{fence}
```
"""
    readme_sha = W.wr(PACKAGE + "/README.md", readme)
    prereg_text = f"""# Preregistration: SLURP test-sample successor 2 -- the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact (owner decisions 233 and 241). A MILESTONE
read: development evidence under owner decision 28; never a test claim and never the final read. Package `{PACKAGE}`.

## One-shot semantics

ONE attempt per run id, ever; no smoke on the sample; no recovery; no resume; no re-score; no re-read; no re-projection; no best-of; no
tuning on the sample (decisions 151 / 207 / 213; `contracts.gate_exposure._ExposureAndCarrierMixin._require_final_report_attempt_budget`).
A failed or aborted attempt consumes the milestone; a further milestone needs a fresh run id in a successor allowance under a fresh
coordinator report to the owner. The sealed successor-1 columns are never re-flown, re-scored or re-read.

## The cell

| item | value |
| --- | --- |
| composition | {COMPOSITION} |
| roster | {D.ROSTER_ID}, 3,010 recordings / 682 prompts, split role final-report, scorer {D.SCORER} |
| comparators (SEALED, cross-flight) | `{S1_COMP1B_RUN}` (primary), `{S1_PLAN_RUN}` (context) |
| in-chain replicate | NONE, by design (declared DEV flight offset {DEV_OFFSET['slu_pp']} pp SLU-F1 / {DEV_OFFSET['intent_pp']} pp intent) |
| runs | `{RUN}` / `{FIT_RUN}`; READ `{READ_RUN}` |
| composed config hash | `{config_hash}` |
| protocol hash | `{proto_hash}` |
| budgets | {budget['generation_calls_cap']:,} generation calls, {budget['fit_endpoint_calls_cap']:,} FIT calls, {budget['repeated_speech_audio_seconds_cap']:,} audio seconds, {budget['gpu_hours_fit_inclusive']} GPU h |

## Decision rule (fixed here)

{decision_rule}

## The measurement declaration

```json
{fence}
```

## Blockers before the flip

{blockers_md}

## Prohibitions

{chr(10).join('- ' + line for line in facts['prohibitions'])}
"""
    prereg_sha = W.wr(PREREG, prereg_text)
    appended = 0
    if args.append_ledger:
        ledger = D.rd(LEDGER)
        if READ_RUN in ledger or RUN in ledger:
            raise SystemExit("the successor-2 rows are already in the ledger")
        model_tool = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted TEST-SAMPLE-3010 speech packets (TEST-SAMPLE-3010-promotion.json, sha256 d0a827b6...); "
                      "NO native tool authority on any role; the NX R5 composed program (module lock v2.2, review-off, 2 contacts per row, v4g at delivery); "
                      "the official scorer slurp-slu-official-test after delivery only")
        inherited = ("The 3,010 sample recordings carry the label-free packet ENCODE+PROMOTE and speech-query encoding exposure (owner decision 156), the old failed PLAN "
                     "generation (3,010 rows / 12,343 contacts, unread) and the SEALED, SCORED and READ successor-1 pair (6,020 trajectories; aggregate and per-intent "
                     "results published 2026-10-01). Every prior SLURP exposure is inherited in full; the closure roster stays unread.")
        common = (f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} by the successor-2 "
                  f"registration (worktree {args.worktree}, branch {args.branch}); owner decisions 233 and 241. This registration performs no contact and authorises none. "
                  f"BLOCKED: allowance DRAFT {ALLOWANCE} unsigned (status draft-awaiting-owner-signature; the fragment pins 64 zeros until the re-pin); measurement design "
                  f"cross-flight-no-replicate awaits a rule-4 ruling; see {PACKAGE}/README.md.")
        rows = []
        for fit_flag in (False, True):
            run_id = FIT_RUN if fit_flag else RUN
            attempt = FIT_ATTEMPT if fit_flag else ATTEMPT
            plan_name = "fit-plan-registered-v1.json" if fit_flag else "generation-plan-registered-v1.json"
            calls = budget["fit_endpoint_calls_cap"] if fit_flag else budget["generation_calls_cap"]
            what = ("SUCCESSOR2-COMPOSED: the NX R5 composed arm on the test sample" +
                    (" -- FIT spend identity, request envelopes only, no generation; a preparation-kind id of the successor-2 allowance DRAFT" if fit_flag else
                     " -- a READ run id of the successor-2 allowance DRAFT, ONE attempt, ever"))
            notes = (f"{common} Plan SHA256 {plan_shas['fit' if fit_flag else 'generation']}; attempt {attempt}. Protocol hash {proto_hash}; composed config {config_hash}; "
                     f"allowance {ALLOWANCE} (DRAFT; sha256 of the draft bytes at registration {draft_sha}; supersedes {S1_ALLOWANCE} by scope new successor run identities only). "
                     f"Expected session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} (decision id {DECISION_ID}) with the two eligible run ids, then repin_cell.py "
                     "--set-ready (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. Measurement: cross-flight-no-replicate (declared DEV flight offset "
                     f"{DEV_OFFSET['slu_pp']} pp SLU / {DEV_OFFSET['intent_pp']} pp intent), n 3010, SLU-F1 primary (post-stratified natural mixture), intent guard, expected_effect_pp {expected_slu} "
                     f"(claims_benefit false, no-harm margin {HARM_MARGIN}), comparators the SEALED successor-1 COMP-1b and PLAN columns (not re-flown). Read: {READ_RUN}. ONE attempt; no recovery; no smoke; no test claim (owner decision 28).")
            rows.append(ledger_row([args.registered_at[:10], run_id, "bounded-discovery-probe", what, model_tool, f"slurp {D.ROSTER_ID} TEST sample 3010", "final-report", split, "no",
                                    str(calls), str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), inherited, f"{PACKAGE}/{plan_name}", notes]))
        rows.append(ledger_row([
            args.registered_at[:10], READ_RUN, "model-free-check",
            "The test-sample SUCCESSOR2-COMPOSED read: the NX R5 composed arm minus the SEALED successor-1 COMP-1b column (gating; official pooled SLU-F1 primary, intent the guard, no-harm) and minus the SEALED successor-1 PLAN column (context) on the same 3,010 rows, post-stratified natural mixture and equal-stratum weightings, per-intent and per-scenario tables, entity FP/TP/FN, cost table.",
            f"No model, tokenizer, encoder or server contact: {READ_DRIVER} over the sealed per-sample official slurp-slu-official-test scores and sealed receipts.",
            f"slurp {D.ROSTER_ID} TEST sample 3010", "final-report", split, "no", "0", "0", "0.0",
            "Reads only the composed manifest and the two sealed successor-1 manifests with their one official score each; no new audio exposure.",
            f"{PACKAGE}/analysis-recipe-v1.json",
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} with the package, so the pre-launch gate scripts/checks/flight_registration_check.py finds it. Analysis root $SPEECHRL_DATA_DIR/{ANALYSIS_ROOT}/<pass>/; recipe {PACKAGE}/analysis-recipe-v1.json (recipe_id {RECIPE_ID}); the driver refuses before any score is opened until root countersigns this row (after the seal). A MILESTONE read under owner decisions 233 and 241: development evidence (decision 28), never a test claim. No utterance text, gold, transcript or model output is printed or persisted."]))
        header = (f"\n## Test-sample successor 2: the NX R5 composed arm on SLURP-TEST-SAMPLE-3010-V1 (owner decisions 233 and 241; DRAFT, root countersignature pending; BLOCKED)\n\n"
                  f"Three unconsumed DRAFT rows registered before contact: the read run id and its FIT spend identity (both named by the successor-2 allowance DRAFT {ALLOWANCE}, unsigned) and the model-free READ row. "
                  f"Package {PACKAGE}; preregistration {PREREG}. No smoke row: the allowance names no smoke run id. None of these rows is countersigned and none authorises a contact.\n\n"
                  "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")
        io.open(LEDGER, "w", encoding="utf-8", newline="").write(ledger.rstrip("\n") + "\n" + header + "\n".join(rows) + "\n")
        appended = len(rows)
    print(json.dumps({
        "package": PACKAGE,
        "written": {PACKAGE + "/README.md": readme_sha, PACKAGE + "/registered-facts-v1.json": facts_sha, PACKAGE + "/protocol-registered-v1.json": protocol_sha,
                    PACKAGE + "/analysis-recipe-v1.json": recipe_sha, PACKAGE + "/root-admission-draft-v1.json": draft_doc_sha, PACKAGE + "/population-counts-v1.json": counts_sha,
                    PACKAGE + "/successor-identity-map.json": map_sha, PACKAGE + "/read-qualification-v1.md": qual_sha, PREREG: prereg_sha,
                    **{f"{PACKAGE}/{k}-plan-registered-v1.json": v for k, v in plan_shas.items()}},
        "composed_config_hash": config_hash, "protocol_hash": proto_hash, "draft_allowance_sha256": draft_sha,
        "budget": caps, "ledger_rows_appended": appended,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
