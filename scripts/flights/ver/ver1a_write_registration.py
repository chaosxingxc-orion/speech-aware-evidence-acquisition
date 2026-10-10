#!/usr/bin/env python3
"""Write the readiness package of cell VER-1a (the five-sample greedy-first Solver pool on TRAIN Fold B) and its DRAFT
exposure-ledger rows, from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing, countersigns nothing. Re-running replaces the package files and the ledger section in place (the hashes move at
the flip; the flip loop rewrites them).

Writes under ``docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1/``: ``registered-facts-v1.json`` (with the CANONICAL
``stage3_measurement`` block keyed by run id), ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``; beside it the preregistration; and the five DRAFT ledger rows (arm, arm FIT, smoke, smoke FIT, READ),
appended in their own heading block at the END of ``docs/exposure-ledger.md``. The package README is hand-written.

AMENDMENT (3 -> 5 samples, before any contact). Once the four flight rows are root-countersigned, never rewrite the section: pass
``--amend-ledger`` and the five rows are amended IN PLACE (scope / calls / audio / gpu columns and the plan SHA / protocol hash /
composed config stanza move; the countersignature text stays verbatim and ``vf.AMENDMENT_MARK`` plus the new arithmetic is appended).

    python -B scripts/flights/ver/ver1a_write_registration.py --study-commit <sha> \\
        --registered-at 2026-10-10T12:00:00.000000+00:00 [--no-ledger]

When the cell baseline already carries the minted ``prepared_phase_supply`` pin (after the flip), the registered plans copy it verbatim
(``flight_registration_check`` "registered-supply-binding"); before the flip the plans carry the MINTED_AT_THE_FLIP marker.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ver1a_family as vf  # noqa: E402

REPO_ROOT = vf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
ROLL2_RECIPE = "docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/analysis-recipe-v1.json"

DECISION_RULE = (
    "OFFLINE SEALED-POOL READ (VER-1a; owner decision 257, 2026-10-10; claim ceiling 'descriptive' for the pool, 'nominated' for any "
    "rule selected on it; the pool cell claims NO benefit). One flight, one Perception visit and one grouped Solver visit per row of "
    "TRAIN Fold B: sample 0 greedy, samples 1-4 at temperature 0.7, all over the SAME state and evidence, committed in flight by "
    "saea-commit-plurality-support-v1 at min_support 3. THE READS, all from this one flight's sealed bytes, model-free: (1) CUSTODY "
    "(row accounting): 1,080 in, 1,080 out; every row's solver_group carries exactly 5 samples in custody (invariant I7g) with "
    "temperatures 0, 0.7, 0.7, 0.7, 0.7 and the pinned seeds fragment_seed + seed_offset + index; the replay of the commit reproduces the sealed "
    "delivered text on every row; zero tool calls. (2) PER-SAMPLE scores: each custodied raw sample rendered to one outputs COPY "
    "(scripts/analysis/stage3_rollout_score.py --stage render, five samples auto-detected) and scored ONCE with the registered scorer, "
    "both as sealed (unprojected) and through the lock's delivery rule v4g applied OFFLINE (scripts/analysis/slurp_nx_postproc_v4_apply.py "
    "--apply v4g; the in-flight cell delivers the unnormalised commit because the loader refuses a deliver_normaliser beside a grouped "
    "visit); sample 0 is read against the NX R1 / R6 lock column on the same rows as the byte-identity audit of the greedy first sample "
    "(llama.cpp greedy decoding is not bitwise reproducible across batch shapes, so equality is measured, not assumed). (3) SELECTION "
    "AND SUPPORT: the offline aggregation rules (scripts/analysis/slurp_sample_aggregation_offline_read.py: plurality-support commit at "
    "min_support 2 and 3 (s = 2 and 3-of-5 both read offline), greedy-sample-0 default, oracle best-of-5 as an UPPER BOUND) and the candidate-support read "
    "(scripts/analysis/slurp_candidate_support_read.py), together with the existing c3 verdict columns of the NX R1 / R6 flights on this "
    "roster (grouping: scripts/analysis/group_system_rollouts.py), from which the VER-1 verification rule is SELECTED. Bar: the 0.67 pp "
    "offline sealed-pool floor of the instrument note (section 2d). NOTHING IS LOCKED HERE: the pool read selects; a selected rule is "
    "flown, if at all, under its own registration (VER-1b) and confirmed on a roster it was not selected on."
)

AMENDMENT = (
    vf.AMENDMENT_MARK + ": the cell was registered at three Solver samples (program phase-native-module-v1-c4, min_support 2, 4 contacts per row, "
    "4,320 generation calls); the offline composer read (scripts/analysis/slurp_ver1_offline.py, docs/readiness/2026-10-10-slurp-ver1-offline-composer-v1/README.md) "
    "resolves the support filter's gain over v4g only at n = 5, s = 2, so the pool carries five samples (sample 0 greedy, samples 1-4 at "
    "temperature 0.7, seed offsets 0..4), program phase-native-module-v1-c6, min_support 3, 6 contacts per row; every plan, hash and cap below is the amended one."
)

ONE_FACTOR = (
    "none -- a pool cell: the base is the NX R5 composed arm / R6-P1 base (COMP-1b components, lock v2.2 compiled blocks, review loop off) "
    "unchanged, and the single registered departure is the grouped Solver visit (samples 5: sample 0 greedy, samples 1-4 at temperature "
    "0.7, plurality-support commit at min_support 3), which exists to produce the sample pool and not to move a delivered metric"
)

PROHIBITIONS = [
    "No test-split, DEV or Fold A contact or read (the pool is TRAIN Fold B; any Fold A confirmation is a later registration).",
    "No second factor: one departure from the R5 composed arm, the grouped greedy-first Solver visit.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No deliver_normaliser in flight (refused beside a grouped Solver visit); v4g is applied OFFLINE to the custodied samples.",
    "No verification rule is wired or flown by this cell: selection among the samples is an OFFLINE read.",
    "No benefit claim: expected_effect_pp 0.0, claims_benefit false.",
    "No paper-scale profile.",
    "No flight before root countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "No sample column is opened before the READ row is root countersigned.",
    "No system-level claim.",
]


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str) -> str:
    return hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest()


def identities() -> dict:
    out = {}
    for kind in ("arm", "smoke"):
        n = vf.names(kind)
        document = json.loads(rd(f"configs/experiment/{n['experiment']}.json"))
        cell = document["cells"][0]
        composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], n["experiment"])
        split = document["population"]["split_identity_hash"]
        out[kind] = {
            "experiment": n["experiment"], "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": n["fit_run_id"], "fit_attempt_id": n["fit_attempt_id"],
            "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"], "arm": composed.values["arm"],
            "rows": document["population"]["count"], "split_identity_hash": split,
            "roster_receipt": document["population"]["roster_receipt"],
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"],
            "audio_seconds": vf.roster_audio(kind),
        }
    return out


def measurement_blocks(ids: dict) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        arm["run_id"]: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "offline-sealed-pool",
            "note": (
                "VER-1a makes no effectiveness claim of its own: it seals a 1,080-row x 5-sample pool on TRAIN Fold B (sample 0 greedy, "
                "samples 1-4 at temperature 0.7) so that the VER-1 verification rule -- scoring and selection over the frozen core's own "
                "sampled answers -- can be selected OFFLINE over sealed bytes, together with the existing c3 verdict columns of the NX "
                "R1 / R6 flights on the same roster, at the 0.67 pp floor of " + INSTRUMENT_NOTE + " section 2d. Any benefit claim "
                "belongs to a later flown cell or to the read over this pool, each of which declares its own block. Owner decisions 139 "
                "and 192: the expectation is on file before flight and it is zero because the cell is an asset."
            ),
            "primary_metric": "slu_f1",
            "read_roster": vf.READ_ROSTER,
            "rows": vf.ROWS,
            "tuning_roster": vf.TUNING_ROSTER,
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "note": (
                f"Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the {vf.PROGRAM} program loads, the Solver "
                f"visit fans out to {vf.SAMPLES} custodied samples (sample 0 at temperature 0, samples 1-4 at 0.7), the plurality-support "
                "commit at min_support 3 seals and replays, every request fits, and the episode completes. Scored by no one, read by no one."
            ),
            "primary_metric": "none (structural form only)", "read_roster": vf.READ_ROSTER, "rows": 4, "tuning_roster": "none",
        },
    }


def minted_supply(experiment: str, cell_id: str) -> dict | None:
    path = REPO_ROOT / "configs" / "experiment" / f"{experiment}.json"
    if not path.exists():
        return None
    cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
    entry = next((c for c in cells if c.get("cell_id") == cell_id), {})
    name = entry.get("baseline_fragment", "")
    baseline = REPO_ROOT / "configs" / "baseline" / f"{name}.json"
    if not name or not baseline.exists():
        return None
    pinned = json.loads(baseline.read_text(encoding="utf-8")).get("prepared_phase_supply")
    if isinstance(pinned, dict) and pinned.get("sha256") not in (None, "", "MINTED_AT_THE_FLIP"):
        return dict(pinned)
    return None


def plan_docs(ids: dict, commit: str, at: str, protocol_sha: str, pkg: str) -> dict:
    docs = {}
    for kind in ("arm", "smoke"):
        i = ids[kind]
        prefix = vf.names(kind)["prefix"]
        supply = {
            "note": ("the first Fold B first-phase supply at w_agree 1.0 with the centroid key on this roster; the flip mints it under "
                     "this cell's own run id (item E16); it is expected to equal the NX R1 / R6 cells' digest (same knowledge channel)"),
            "relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
        }
        pinned = minted_supply(i["experiment"], i["cell"])
        annotations = None
        if pinned is not None:
            annotations = {"note": supply["note"]}
            supply = pinned
        base = {
            "cell": i["cell"], "composed_config_hash": i["composed_config_hash"],
            "expected_session_id": vf.SESSION, "experiment": i["experiment"], "family_budget": i["family_budget"],
            "one_factor": ONE_FACTOR, "preparation_base_commit": commit,
            "prepared_phase_supply": supply,
            "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": at, "source_tree": vf.SOURCE_TREE,
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
            "unused_budget_is_not_attempt_authority": True,
            **({"prepared_phase_supply_annotations": annotations} if annotations else {}),
        }
        gen_plan = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"],
                        protocol_hash=i["protocol_hash"], run_id=i["run_id"], schema="saea-execution-plan-v1",
                        split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        fit_plan = dict(gen_plan, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"],
                        planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        route_gen = (
            f"Shared core.flight.cli campaign over {vf.CAMPAIGN} (this arm alone; a pool cell has no comparator and no A/A cell) through "
            "scripts/flights/ver/ver1a_batch_chain.sh and the batch driver."
            if kind == "arm" else
            "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
        )
        docs[f"{prefix}generation-plan-registered-v1.json"] = {
            **base, "execution_plan": gen_plan, "execution_route": route_gen, "plan_kind": "generation",
            "purpose": f"{i['run_id']}: " + (DECISION_RULE if kind == "arm" else "structural form proof only: no score and no read."),
            "schema": "saea-registered-generation-plan-v1",
            **({"quality_read_gate": (
                f"No sample column is opened before the complete sealed manifest, the ordered outputs and the phase summary of the flight "
                f"exist AND the READ row {vf.READ_RUN_ID} is root countersigned.")} if kind == "arm" else {}),
        }
        docs[f"{prefix}fit-plan-registered-v1.json"] = {
            **base, "execution_plan": fit_plan, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing.",
        }
    return docs


def contact_arithmetic(ids: dict) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        "contacts_per_row": {"perception": 1, "solver": vf.SAMPLES, "reviewer": 0, "planner": 0, "total": vf.CEILING},
        "program": vf.PROGRAM,
        "arm": {"rows": vf.ROWS, "generation_calls": vf.ROWS * vf.CEILING, "fit_endpoint_calls": vf.fit_contact_cap(vf.ROWS),
                "speech_audio_seconds_cap": arm["family_budget"]["repeated_speech_audio_seconds_cap"],
                "roster_audio_seconds": round(arm["audio_seconds"], 6),
                "arithmetic": (f"{vf.ROWS:,} x {vf.CEILING} = {vf.ROWS * vf.CEILING:,}; FIT {vf.ROWS:,} x {vf.CEILING} x "
                               f"{vf.FIT_ENDPOINTS_PER_CONTACT} = {vf.fit_contact_cap(vf.ROWS):,}; audio ceil({arm['audio_seconds']:.6f} x "
                               f"{vf.CEILING}) = {arm['family_budget']['repeated_speech_audio_seconds_cap']:,}")},
        "smoke": {"rows": vf.SMOKE_ROWS, "generation_calls": vf.SMOKE_ROWS * vf.CEILING, "fit_endpoint_calls": vf.fit_contact_cap(vf.SMOKE_ROWS),
                  "speech_audio_seconds_cap": smoke["family_budget"]["repeated_speech_audio_seconds_cap"]},
        "note": ("The ceiling is exact and also the expected spend: every row makes one Perception and five Solver contacts (no early "
                 "exit). The FIT cap is structural and never run-cumulative; the generation budget is run-cumulative across attempts."),
    }


def write_package(ids: dict, commit: str, at: str) -> dict:
    pkg = vf.PACKAGE
    arm, smoke = ids["arm"], ids["smoke"]
    blocks = measurement_blocks(ids)
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id",
                                           "fit_run_id", "protocol_hash", "rows", "run_id", "split_identity_hash")}
                  for k, v in ids.items()},
        "decision_rule_fixed_here": DECISION_RULE,
        "development_numbers_only": "Every number is a TRAIN Fold B development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": ("Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second "
                           "failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative "
                           "across attempts."),
        "amendment": AMENDMENT, "one_factor": ONE_FACTOR, "prohibitions": PROHIBITIONS,
        "protocol_id": f"slurp-{vf.SLUG}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1",
        "source_tree": vf.SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "study_commit_at_registration": commit,
        "the_question": (
            "Can a five-sample pool of the lock v2.2 Solver on TRAIN Fold B -- the greedy single-sample answer plus four temperature-0.7 "
            "draws over the same state and evidence -- be sealed with full custody, so that a verification rule (scoring and selection "
            "over the core's own sampled answers) can be selected offline together with the existing c3 verdict columns? (Pool cell: no "
            "benefit is claimed.)"
        ),
    }
    protocol_sha = wjson(f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(ids, commit, at, protocol_sha, pkg)
    shas = {name: wjson(f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": (f"{INSTRUMENT_NOTE} (the 0.67 pp offline sealed-pool instrument); owner decision 257 (2026-10-10); the ROLL-2 "
                      f"recipe pattern {ROLL2_RECIPE}; the stage-3 algorithm label inference-time-verification-v1."),
        "cell_kind": "POOL -- a sealed five-sample greedy-first Solver pool on TRAIN Fold B. DESCRIPTIVE: no comparator, no gate, no admission.",
        "claim_boundary": ("DESCRIPTIVE for the pool; 'nominated' at most for a rule selected on it. No system-level, superiority, "
                           "generalisation, component-causal, held-out, confirmatory or paper-scale claim."),
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "decision_rule": DECISION_RULE,
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flight itself)",
        "measurement_design": "offline-sealed-pool",
        "output": {"analysis_root": "analysis/" + vf.READ_RUN_ID,
                   "note": "ids, indices, scores, flags and hashes only; no utterance text, transcript, gold string or model output is printed or persisted"},
        "read_run_id": vf.READ_RUN_ID,
        "recipe_id": vf.RECIPE_ID,
        "registered_at_utc": at,
        "roster": {"relpath": vf.ROSTER["arm"], "roster_id": vf.READ_ROSTER, "rows": vf.ROWS,
                   "split_identity_hash": arm["split_identity_hash"]},
        "row_accounting_required": (
            f"{vf.ROWS:,} in, {vf.ROWS:,} out; every row's solver_group carries exactly {vf.SAMPLES} samples in custody (I7g) with "
            "temperatures 0, 0.7, 0.7, 0.7, 0.7 and seeds fragment_seed + 0 + index; the commit replay of saea-commit-plurality-support-v1 at "
            "min_support 3 / similarity 0.8 reproduces the sealed delivered answer for every row; zero native task-contract tool calls."),
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": vf.READ_RUN_ID, "smoke": smoke["run_id"],
                    "smoke_fit": smoke["fit_run_id"]},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_render": "scripts/analysis/stage3_rollout_score.py --stage render: one outputs COPY per Solver sample index (0..4), each row's solver_group.samples[index].parsed_answer rendered through the canonical analysis path; the sample count is detected from the sealed pool.",
            "2_score": "scripts/analysis/stage3_rollout_score.py --stage score: each of the five copies scored ONCE through the registered scorer (never core.scoring_batch: every copy is a derived read).",
            "3_v4g": f"scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g over each custodied sample and the replayed commit ({vf.V4G_LOCK_RECORD}): lock v2.2's delivery rule applied OFFLINE, because the in-flight cell delivers the unnormalised commit.",
            "4_pairs": "scripts/analysis/stage3_rollout_score.py --stage pairs: per-row best / worst / delivered; the oracle best-of-5 ceiling stated as an UPPER BOUND, never as a result; sample 0 against the NX R1 / R6 lock column on these rows (greedy byte-identity audit).",
            "5_selection": f"scripts/analysis/slurp_sample_aggregation_offline_read.py and scripts/analysis/slurp_candidate_support_read.py over the sealed pool ({vf.AGGREGATION_READ} pattern), grouped with the existing c3 verdict columns by scripts/analysis/group_system_rollouts.py: the VER-1 rule is selected here at the 0.67 pp offline floor.",
        },
        "what_is_not_here": ("No comparator block, no margins block and no gate: VER-1a is a pool. The same-flight and cross-flight floors "
                             "are CONTEXT, never this cell's bar."),
    }
    shas["analysis-recipe-v1.json"] = wjson(f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": contact_arithmetic(ids),
        "amendment": AMENDMENT,
        "budget_arithmetic": {"arm_family_budget": arm["family_budget"], "smoke_family_budget": smoke["family_budget"]},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "decision_rule": DECISION_RULE,
        "fit": {"status": "PENDING_CHECK"},
        "identity": ids,
        "owner_decisions": {
            "257": "the verification layer (VER-1) of the training-free RL round; VER-1a seals the sample pool it is selected on",
            "139": "no prior: the expectation is declared before flight (zero: an asset)",
            "192": "the declared effect is on file BEFORE flight (claims_benefit false)",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "prohibitions": PROHIBITIONS,
        "registered_at_utc": at,
        "registration_basis": (f"engineering brief 2026-10-10: register {vf.CELL_LABEL} from owner decision 257, {vf.ROLL_READ} and "
                               f"{vf.AGGREGATION_READ}. HELD: the owner / root admission is still required; nothing here authorises a flip or a flight."),
        "rows": vf.ROWS,
        "schema": "saea-registered-facts-v1",
        "stage3_measurement": blocks,
        "study_commit_at_registration": commit,
        "the_cell": {
            "base": "the NX R5 composed arm / R6-P1 base: COMP-1b components on lock v2.2, review loop OFF, as a hand-written fragment (no consumption_module block)",
            "program": vf.PROGRAM, "ceiling": vf.CEILING,
            "solver": {"samples": vf.SAMPLES, "decoding_overrides": vf.SOLVER_OVERRIDES, "commit": vf.SOLVER_COMMIT},
            "deliver_normaliser": "none in flight (refused beside samples >= 2); v4g applied offline",
        },
    }
    shas["registered-facts-v1.json"] = wjson(f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for root to mint on the data root with scripts/flights/ver/ver1a_mint_receipt.py (status decided, "
                        "recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'."),
        "antecedents": {
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "derive_script": {"path": "scripts/flights/ver/ver1a_derive_cells.py", "sha256": sha_file("scripts/flights/ver/ver1a_derive_cells.py")},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": vf.PREREG, "sha256": None},
            "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None},
            "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit,
        },
        "authorization_basis": f"Owner decisions 257 (2026-10-10), 139, 192, 28/86; {INSTRUMENT_NOTE}; {vf.ROLL_READ}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "cell_kind": ("Stage-3 sealed-sample-pool cell (label inference-time-verification-v1), a POOL (claims_benefit false). One arm on "
                      "TRAIN Fold B 1,080 with a five-sample greedy-first Solver visit, and a four-row form smoke."),
        "claim_boundary": ("No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; "
                           "a sealed pool on a development fold."),
        "coordinator": "Fable5.1",
        "decision": (f"Fly cell {vf.CELL_LABEL}: the R5 composed arm (COMP-1b on lock v2.2, review loop off) on TRAIN Fold B under "
                     f"{vf.PROGRAM} with the Solver visit grouped at samples {vf.SAMPLES} (sample 0 greedy, samples 1-4 at 0.7, plurality "
                     "commit at min_support 3); seal the pool; select the VER-1 rule offline."),
        "decision_id": vf.DECISION_ID,
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the registered grouped greedy-first Solver visit and the Fold B re-target",
            "wiring or flying a verification rule (the selection is an offline read)",
            "opening a sample column before the READ row is countersigned",
        ],
        "owner": "root",
        "population": {"count": vf.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": arm["split_identity_hash"],
                       "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None,
        "registered_hashes": {k: {"composed_config": v["composed_config_hash"], "protocol": v["protocol_hash"]} for k, v in ids.items()},
        "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": vf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True,
                    "slot_tokens": 24576, "slots": 4},
        "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(f"{pkg}/root-admission-draft-v1.json", draft)
    prereg = (
        f"# Cell {vf.CELL_LABEL} (verification layer, sample pool): preregistration\n\n"
        f"Registered {at[:10]} at study commit `{commit}`, before any contact, by script (decision 58) from the committed R6-P1 Fold B "
        "fragments and the consumption-module compiler under owner decision 257. Development numbers only.\n\n"
        "| item | value |\n| --- | --- |\n"
        "| base | the NX R5 composed arm / R6-P1 base: COMP-1b (agree-vote-seed + centroid-boundary-key ON), lock v2.2 compiled blocks, Reviewer loop OFF, no tool schema on any role |\n"
        f"| the one departure | Solver visit grouped at samples {vf.SAMPLES}: sample 0 greedy (`decoding_overrides.greedy_first`), samples 1-4 at temperature 0.7, seed_offset 0; commit `saea-commit-plurality-support-v1` at min_support 3, similarity 0.8 |\n"
        f"| program | `{vf.PROGRAM}` (ceiling {vf.CEILING} = 1 + 1 x {vf.SAMPLES}); a registered member of the review-off module family |\n"
        "| delivery | the unnormalised commit (the loader refuses a deliver_normaliser beside a grouped visit); v4g is applied offline |\n"
        "| design / claim | `offline-sealed-pool` / descriptive; a POOL cell, `claims_benefit` false, expected effect 0.0 pp |\n"
        f"| rosters | tuning `{vf.TUNING_ROSTER}`; read `{vf.READ_ROSTER}` |\n"
        f"| runs | `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{vf.READ_RUN_ID}` |\n"
        f"| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |\n"
        f"| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |\n"
        f"| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |\n\n"
        "## Attempt state (no recovery)\n\nThe smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke "
        f"{vf.SMOKE_ROWS * vf.CEILING} model calls, FIT endpoint cap {vf.fit_contact_cap(vf.SMOKE_ROWS)} (structural: {vf.SMOKE_ROWS} rows x "
        f"{vf.CEILING} contacts x {vf.FIT_ENDPOINTS_PER_CONTACT} endpoints); arm {vf.ROWS * vf.CEILING:,} model calls, FIT cap "
        f"{vf.fit_contact_cap(vf.ROWS):,}. At most one recovery re-registration per cell.\n\n"
        f"## Decision rule (fixed here)\n\n{DECISION_RULE}\n\n"
        "## The measurement declaration\n\n```json\n"
        + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    shas["__prereg__"] = wr(vf.PREREG, prereg)
    return {"shas": shas, "blocks": blocks, "protocol_sha": protocol_sha}


def ledger_rows(ids: dict, commit: str, at: str, shas: dict) -> str:
    pkg = vf.PACKAGE
    scope = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
             "the NX R5 composed arm (COMP-1b on lock v2.2, Reviewer loop off) with the Solver visit grouped at samples 5 (sample 0 greedy, "
             "samples 1-4 at temperature 0.7, plurality-support commit at min_support 3, no in-flight delivery normaliser)")
    inherited = ("TRAIN Fold B discovery rows already exposed by SAEA-SLURP-EVO-FOLD-PACKETS-V2, SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2, the EVO-S1 "
                 "confirmation fold SAEA-SLURP-EVO-S1-FOLD-B-V2 (8,640 contacts, 2026-09-06), the encoder pass "
                 "SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1, the P-SV-1..P-SV-4 Fold B cells, the NX R1 Solver template columns and the "
                 "NX R6-P1 Perception template column registered on these rows; this cell opens no split. Prior exposure is inherited in full.")
    note_common = (
        f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {at[:10]} at study commit {commit} by the {vf.ROUND_LABEL} "
        f"engineering agent (worktree {vf.WORKTREE}, branch {vf.BRANCH}); owner decision 257. "
        "HELD: this registration performs no contact and authorises none. READINESS HELD: root countersigns the five DRAFT rows, mints "
        f"{vf.DECISION_RELPATH} (decision id {vf.DECISION_ID}) from the package's root-admission-draft-v1.json with scripts/flights/ver/ver1a_mint_receipt.py "
        "(four eligible run ids), then scripts/flights/ver/ver1a_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each "
        "cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
        "Measurement declaration: offline-sealed-pool, expected_effect_pp 0.0, claims_benefit false (a pool cell). "
        f"Read: {vf.READ_RUN_ID} by the recipe in the package. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
        "re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
    )

    def row(date, rid, profile, what, model, carrier, split, consumed, calls, audio, gpu, artifacts, notes):
        cells = [date, rid, profile, what, model, carrier, "discovery", split, consumed, str(calls), str(audio), str(gpu), inherited, artifacts, notes]
        return "| " + " | ".join(cells) + " |"

    def plan_row(kind, fit):
        i = ids[kind]
        prefix = vf.names(kind)["prefix"]
        what = (vf.ROUND_LABEL + ": the five-sample greedy-first Solver pool on TRAIN Fold B" if kind == "arm" else
                "Four-row form smoke of " + vf.ROUND_LABEL)
        if fit:
            what += " -- FIT spend identity, request envelopes only, no generation"
        plan = f"{pkg}/{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"
        calls = i["family_budget"]["fit_endpoint_calls_cap"] if fit else i["family_budget"]["generation_calls_cap"]
        plan_sha = shas[f"{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"]
        attempt = i["fit_attempt_id"] if fit else i["attempt_id"]
        notes = (note_common.replace("Measurement declaration: offline-sealed-pool",
                                     "Measurement declaration: " + ("offline-sealed-pool" if kind == "arm" else "form-proof"))
                 + f" Plan SHA256 {plan_sha}; attempt {attempt}. Protocol hash {i['protocol_hash']}; composed config {i['composed_config_hash']}; expected session {vf.SESSION} (attach only).")
        return row(at, i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], what, scope,
                   f"slurp TRAIN Fold B {i['rows']}", i["split_identity_hash"], "no", calls,
                   i["family_budget"]["repeated_speech_audio_seconds_cap"], i["family_budget"]["gpu_hours_fit_inclusive"], plan, notes)

    read = row(
        at[:10], vf.READ_RUN_ID, "model-free-check",
        (f"The offline sealed-pool read of {vf.ROUND_LABEL}: render one outputs copy per custodied Solver sample (0..4), score each ONCE with "
         "the registered scorer, apply the v4g delivery rule offline, pair per row (best / worst / delivered, the oracle best-of-5 as an upper "
         "bound, sample 0 against the NX R1 / R6 lock column), and read the aggregation / candidate-support rules together with the existing c3 "
         f"verdict columns on this roster, from which the VER-1 rule is selected, by the recipe {pkg}/analysis-recipe-v1.json. Zero model, "
         "server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
        f"slurp TRAIN Fold B {vf.ROWS}, the sealed {vf.ROUND_LABEL} flight's sample pool (after the seal)",
        ids["arm"]["split_identity_hash"], "no", 0, 0, 0, f"{pkg}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any sample column is "
         f"opened) {at[:10]} at study commit {commit}. Recipe {vf.RECIPE_ID}; output analysis/{vf.READ_RUN_ID}. Its ceiling is a "
         "nomination; it admits nothing."),
    )
    lines = [
        vf.LEDGER_MARK + " (owner decision 257) -- the arm, its four-row smoke and the READ row (DRAFT, root countersignature pending)",
        "",
        "Four unconsumed flight rows and one READ row registered with the flight. A pool cell: no comparator and no A/A cell. None of "
        "these rows is countersigned and none authorises a contact.",
        "",
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        plan_row("arm", False), plan_row("arm", True), plan_row("smoke", False), plan_row("smoke", True), read, "",
    ]
    return "\n".join(lines)


def amend_ledger_rows(ids: dict, shas: dict) -> list[str]:
    """Amend the five VER-1a rows IN PLACE for the 3 -> 5 sample change (the R1 / R6 way): countersignature text verbatim, the
    scope columns, calls, audio, gpu and the plan / protocol / composed stanza moved, the amendment sentence appended. Idempotent."""

    arm, smoke = ids["arm"], ids["smoke"]
    text = rd(LEDGER)
    if vf.LEDGER_MARK_THREE_SAMPLE in text:
        text = text.replace(vf.LEDGER_MARK_THREE_SAMPLE, vf.LEDGER_MARK)
    lines = text.split("\n")
    last = vf.SAMPLES - 1
    min_support = vf.SOLVER_COMMIT["min_support"]
    scope_pairs = [
        ("the three-sample greedy-first", "the five-sample greedy-first"),
        ("grouped at samples 3 (sample 0 greedy, samples 1-2 at temperature 0.7, plurality-support commit at min_support 2,",
         f"grouped at samples {vf.SAMPLES} (sample 0 greedy, samples 1-{last} at temperature 0.7, plurality-support commit at min_support {min_support},"),
        ("(0..2)", f"(0..{last})"),
        ("best-of-3", f"best-of-{vf.SAMPLES}"),
    ]
    pattern = r"Plan SHA256 [0-9a-f]{64}; attempt [\w-]+\. Protocol hash [0-9a-f]{64}; composed config [0-9a-f]{64};"
    amended = []
    targets = [
        (arm["run_id"], arm, "generation-plan-registered-v1.json", "generation_calls_cap", arm["attempt_id"]),
        (arm["fit_run_id"], arm, "fit-plan-registered-v1.json", "fit_endpoint_calls_cap", arm["fit_attempt_id"]),
        (smoke["run_id"], smoke, "smoke-generation-plan-registered-v1.json", "generation_calls_cap", smoke["attempt_id"]),
        (smoke["fit_run_id"], smoke, "smoke-fit-plan-registered-v1.json", "fit_endpoint_calls_cap", smoke["fit_attempt_id"]),
    ]
    for run_id, cellids, plan_name, cap_key, attempt in targets + [(vf.READ_RUN_ID, None, None, None, None)]:
        hits = [k for k, line in enumerate(lines) if line.startswith("| ") and f" | {run_id} | " in line]
        if len(hits) != 1:
            raise SystemExit(f"ledger: {len(hits)} rows for {run_id}, expected exactly one")
        cells = lines[hits[0]][2:-2].split(" | ")
        if len(cells) != 15:
            raise SystemExit(f"ledger: row {run_id} has {len(cells)} cells, expected 15")
        for column in (3, 4):
            for old, new in scope_pairs:
                cells[column] = cells[column].replace(old, new)
        notes = cells[14].split(" " + vf.AMENDMENT_MARK)[0].rstrip()
        if cellids is None:
            cells[14] = notes + " " + vf.AMENDMENT_MARK + (
                f": the recipe renders and scores the {vf.SAMPLES} custodied samples (0..{last}); the support filter is read at "
                "s = 2 and 3-of-5, with the gate combination, over the same sealed pool.")
        else:
            family = cellids["family_budget"]
            calls, audio = family[cap_key], family["repeated_speech_audio_seconds_cap"]
            cells[9], cells[10], cells[11] = str(calls), str(audio), str(family["gpu_hours_fit_inclusive"])
            if len(re.findall(pattern, notes)) != 1:
                raise SystemExit(f"ledger: row {run_id} notes carry no unique plan/attempt/hash stanza to amend")
            stanza = (f"Plan SHA256 {shas[plan_name]}; attempt {attempt}. Protocol hash {cellids['protocol_hash']}; "
                      f"composed config {cellids['composed_config_hash']};")
            notes = re.sub(pattern, lambda _m: stanza, notes)
            cells[14] = notes + " " + vf.AMENDMENT_MARK + (
                f": samples {vf.SAMPLES} (sample 0 greedy, samples 1-{last} at temperature 0.7), plurality-support commit at "
                f"min_support {min_support}, program {vf.PROGRAM}, {vf.CEILING} contacts per row (the 3-sample text above "
                f"is the superseded form), calls {calls}, speech-seconds {audio}, gpu hours {family['gpu_hours_fit_inclusive']}; plan SHA256, "
                "protocol hash and composed config above are the amended registration's.")
        lines[hits[0]] = "| " + " | ".join(cells) + " |"
        amended.append(run_id)
    io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return amended


def write_ledger(text: str) -> None:
    """Replace this cell's section (its heading up to the next ``## `` heading, or the end); append at the END when absent."""

    current = rd(LEDGER)
    tail = ""
    if vf.LEDGER_MARK in current:
        start = current.index(vf.LEDGER_MARK)
        following = current.find("\n## ", start + len(vf.LEDGER_MARK))
        if following != -1:
            tail = current[following + 1:]
        current = current[:start].rstrip("\n") + "\n"
    if not current.endswith("\n"):
        current += "\n"
    out = current + "\n" + text.rstrip("\n") + "\n"
    if tail:
        out += "\n" + tail
    io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--no-ledger", action="store_true")
    parser.add_argument("--amend-ledger", action="store_true",
                        help="amend the five existing (countersigned / draft) rows in place for the 3 -> 5 sample change; "
                             "never rewrites the section")
    args = parser.parse_args(argv)
    ids = identities()
    result = write_package(ids, args.study_commit, args.registered_at)
    amended: list[str] = []
    if args.amend_ledger:
        amended = amend_ledger_rows(ids, result["shas"])
    elif not args.no_ledger:
        write_ledger(ledger_rows(ids, args.study_commit, args.registered_at, result["shas"]))
    print(json.dumps({"package": vf.PACKAGE, "files": sorted(result["shas"]), "amended_ledger_rows": amended,
                      "composed": {k: v["composed_config_hash"] for k, v in ids.items()},
                      "protocol": {k: v["protocol_hash"] for k, v in ids.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
