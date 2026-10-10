#!/usr/bin/env python3
"""Write the readiness package of cell VER-1c (the R1 c3 Solver template column on TRAIN Fold A, the verdict source of the VER-1 rule) and
its DRAFT exposure-ledger rows, from the derived fragments, the measured fit numbers and the pinned candidate template.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing, countersigns nothing. Re-running replaces the package files and the ledger section in place (the hashes move at
the flip; the flip loop rewrites them).

Writes under ``docs/readiness/2026-10-10-slurp-ver1c-c3-column-fold-a-v1/``: ``registered-facts-v1.json`` (with the CANONICAL
``stage3_measurement`` block keyed by run id), ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``; beside it the preregistration; and the five DRAFT ledger rows (arm, arm FIT, smoke, smoke FIT, READ),
appended in their own heading block at the END of ``docs/exposure-ledger.md``. The package README is hand-written.

    python -B scripts/flights/ver/ver1c_write_registration.py --study-commit <sha> \\
        --registered-at 2026-10-10T12:00:00.000000+00:00 [--no-ledger]

The candidate list, the roster and every id come from ``ver1c_family``; the prose below is built from them.
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

import ver1b_family as vf  # noqa: E402
import ver1c_family as cf  # noqa: E402

REPO_ROOT = cf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
VER1A_PACKAGE = "docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1"

ARM_LIST = ", ".join(cf.ARMS)

DECISION_RULE = (
    f"SAME-FLIGHT NODE-TEMPLATE COLUMN READ AS THE VERDICT SOURCE OF THE VER-1 RULE ({cf.CELL_LABEL}; NX instrument E1/E2; owner decision "
    "257, decision 258 option A proposed 2026-10-10; claim ceiling 'descriptive': the arm is NOT a nomination). "
    f"One flight, one Solver visit per row of {cf.FOLD_TITLE}, {cf.K} arms over the SAME QueryState and evidence: {ARM_LIST} (the R1 c3 "
    f"template, the same hash-pinned bytes the NX R1 iteration-1 cell flew), {cf.TWIN} (the twin, replicate_of {cf.DELIVERING}) and "
    f"{cf.DELIVERING} (the locked template, delivering, last). Each arm's first-visit Solver answer is rendered through the delivered row's "
    "normaliser and projection and scored ONCE with slurp-slu-official-train per arm (never sharded; scripts/analysis/stage3_rollout_score.py "
    "--mode supply-variants writes the per-arm first-visit outputs and scores the composer reads). READS: (1) THE TWIN NULL first: aa minus "
    "lock on every metric, paired per row, whole-utterance cluster bootstrap (10,000 draws, seed 20260915), reported beside the E1 "
    f"provisional floor (SLU-F1 {cf.FLOOR_SLU_PP} pp, intent {cf.FLOOR_INTENT_PP} pp at n = 1,080; borrowed until a node-column cell measures "
    f"its own null). (2) THE c3 COLUMN: {cf.VERDICT_ARM} minus lock, pooled SLU-F1 and intent, quoted DESCRIPTIVELY with its CI95 (it gates "
    "nothing and nominates nothing; a Fold A c3 loss or gain is information about the verdict source, not a result of this cell). "
    f"(3) THE VERDICT SOURCE: the c3 presence verdict is the flag 'the {cf.VERDICT_ARM} answer carried no entity after the registered v4g "
    "normaliser' (slurp_ver1_offline.verdict_flags); the number of verdict-empty rows and of verdict-empty rows on empty-gold rows is "
    "reported beside the TRAIN Fold B figures of the NX R1 flights so that a drift of the verdict between rosters is visible. (4) THE "
    f"VER-1 RULE FIXED ON {cf.TUNING_ROSTER} (support filter n = {vf.RULE_N}, s = {vf.RULE_S}; c3 verdict x N1 >= {vf.RULE_THETA:g}; v4g) is "
    f"applied offline to the VER-1b sample pool on these rows with {cf.COMPOSER} --verdict-run; the confirmation criterion is the "
    f"VER-1b READ row's ({vf.READ_RUN_ID}). NOTHING IS TUNED OR SELECTED HERE. The delivering arm is the lock: the delivered answer is "
    "unchanged by construction at the request level (invariant I7)."
)

ONE_FACTOR = (
    "the Solver instruction template (phase_material.solver.instruction_template) of the one non-delivering candidate arm: ONE "
    f"hash-pinned path ({cf.CANDIDATE_PATHS[cf.ARMS[0]]}, the R1 c3 template) and nothing else (no supply knob, decoding, response format or "
    f"tool authority); the base, the {cf.FOLD_TITLE} pins, the review-off program and the module block are the instrument's carrier, "
    "shared by every arm"
)

PROHIBITIONS = [
    f"No test-split, DEV or {cf.TUNING_TITLE} contact or read (the column is {cf.FOLD_TITLE}; the rule was fixed on {cf.TUNING_TITLE}).",
    "No second factor: one axis (the Solver instruction template), none on aa or lock.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No second candidate and no re-authored template: the arm is the R1 c3 template, byte for byte.",
    "No v4 or v4g normaliser wired differently from lock v2.2's module cell (v4g at delivery); no other normaliser variant.",
    "No benefit claim and no nomination: expected_effect_pp 0.0, claims_benefit false.",
    "No paper-scale profile.",
    "No flight before root countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "No arm score opened before the READ row is root countersigned.",
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
        n = cf.names(kind)
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
            "roster_receipt": document["population"].get("roster_receipt", cf.ROSTER[kind]),
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"],
            "audio_seconds": cf.roster_audio(kind),
        }
    return out


def measurement_blocks(ids: dict, measure: dict) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    extra = cf.CEILING - cf.BASE_CONTACTS
    return {
        arm["run_id"]: {
            "aa_arm_id": cf.TWIN,
            "claim": "nominated",                       # the design's ceiling (flight_registration_check: a node column may claim only this); never reached here
            "claims_benefit": False,
            "expected_effect_pp": cf.EXPECTED_EFFECT_PP,
            "measurement_design": "same-flight-node-column",
            "note": (
                f"{cf.CELL_LABEL} (level: node column, K = {cf.K} Solver template arms: the R1 candidate {ARM_LIST}, the aa twin, the lock). "
                f"Its role is the VERDICT SOURCE of the VER-1 rule on {cf.FOLD_TITLE} (the c3 presence verdict feeds the offline composer's "
                f"--verdict-run); it claims no benefit and nominates nothing, so expected_effect_pp is {cf.EXPECTED_EFFECT_PP:g} and "
                "claims_benefit is false (the claim field carries the design's ceiling 'nominated', the only value the registration gate "
                f"admits for a node column; this cell's reading is descriptive). The provisional floor SLU {cf.FLOOR_SLU_PP} pp is borrowed from same-flight-supply-variant "
                "(the NX R1 iteration 1 and 2 flights have flown, but their official-score twin nulls are read, not re-used here). The rule "
                f"that the column feeds was FIXED on {cf.TUNING_ROSTER}; the read roster is {cf.READ_ROSTER}. {cf.TUNING_DISCLOSURE} The "
                "delivered row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant I7; "
                "reported, never contrasted)."
            ),
            "primary_metric": (
                f"official: pooled SLU-F1 of the arm's column (slurp-slu-official-train), {cf.VERDICT_ARM} and {cf.TWIN} minus the "
                "delivering lock arm (paired row bootstrap), quoted descriptively; the c3 presence verdict flags are the column's product"
            ),
            "primary_metric_key": "slu",
            "provisional_floor_pp": {
                "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp (primary), intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
                "intent_accuracy": cf.FLOOR_INTENT_PP, "slu_f1": cf.FLOOR_SLU_PP,
            },
            "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight (descriptive: nothing is nominated)",
            "read_roster": cf.READ_ROSTER,
            "rows": cf.ROWS,
            "template_variants": {"node": cf.NODE, "candidate_arms": len(cf.ARMS), "twin": True},
            "tuning_roster": cf.TUNING_ROSTER,
            "variant_cost": {
                "extra_audio_seconds": round(extra * arm["audio_seconds"], 2),
                "extra_audio_seconds_per_row_mean": round(arm["audio_seconds"] / arm["rows"] * extra, 4),
                "extra_contacts_per_row": extra,
                "extra_perception_contacts_per_row": 0,
                "extra_solver_contacts_per_row": extra,
                "note": (
                    f"K - 1 = {cf.K - 1} non-delivering Solver arms (the candidate and the twin), each one Solver contact at the one "
                    f"Solver visit; every contact re-sends the row's speech packet, so {extra} x the {cf.FOLD_TITLE} total "
                    f"{arm['audio_seconds']} s per flight (review-off base: {cf.BASE_CONTACTS} contacts per row, ceiling {cf.CEILING})"
                ),
            },
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "note": (
                f"Four {cf.FOLD_TITLE} rows (the COMP-1b Fold A smoke prefix) prove FORM and nothing else: the {cf.PROGRAM} program "
                f"loads, the {cf.K} Solver template arms fan out at the one Solver visit, every arm fits its estimated bound, the arm "
                "receipt (saea-supply-variant-arms-v4) and I7v seal, and the episode completes. Scored by no one, read by no one."
            ),
            "primary_metric": "none (structural form only)", "read_roster": cf.READ_ROSTER, "rows": cf.SMOKE_ROWS, "tuning_roster": "none",
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
        prefix = cf.names(kind)["prefix"]
        supply = {
            "note": (f"the {cf.FOLD_TITLE} first-phase supply at w_agree 1.0 with the centroid key on this roster; the flip mints it under "
                     "this cell's own run id (item E16); it is expected to equal the COMP-1b Fold A cells' digest (same knowledge channel)"),
            "relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
        }
        pinned = minted_supply(i["experiment"], i["cell"])
        annotations = None
        if pinned is not None:
            annotations = {"note": supply["note"]}
            supply = pinned
        base = {
            "cell": i["cell"], "composed_config_hash": i["composed_config_hash"],
            "expected_session_id": cf.SESSION, "experiment": i["experiment"], "family_budget": i["family_budget"],
            "one_factor": ONE_FACTOR, "preparation_base_commit": commit,
            "prepared_phase_supply": supply,
            "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": at, "source_tree": cf.SOURCE_TREE,
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
            f"Shared core.flight.cli campaign over {cf.CAMPAIGN} (this arm alone; no A/A cell -- the twin arm {cf.TWIN} flies inside "
            f"every row) through scripts/flights/ver/{cf.SHORT}_batch_chain.sh and the batch driver."
            if kind == "arm" else
            "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
        )
        docs[f"{prefix}generation-plan-registered-v1.json"] = {
            **base, "execution_plan": gen_plan, "execution_route": route_gen, "plan_kind": "generation",
            "purpose": f"{i['run_id']}: " + (DECISION_RULE if kind == "arm" else "structural form proof only: no score and no read."),
            "schema": "saea-registered-generation-plan-v1",
            **({"quality_read_gate": (
                f"No arm column is opened before the complete sealed manifest, the ordered outputs, the phase summary and the "
                f"single complete official TRAIN score of the flight exist AND the READ row {cf.READ_RUN_ID} is root "
                "countersigned.")} if kind == "arm" else {}),
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
        "contacts_per_row": {"perception": 1, "solver": cf.K, "reviewer": 0, "planner": 0, "total": cf.CEILING},
        "program": cf.PROGRAM,
        "derivation": f"E1: ceiling = base {cf.BASE_CONTACTS} + (K - 1) with K = {cf.K} arms ({ARM_LIST}, {cf.TWIN}, {cf.DELIVERING}) = {cf.CEILING}",
        "arm": {"rows": cf.ROWS, "generation_calls": cf.ROWS * cf.CEILING, "fit_endpoint_calls": cf.fit_contact_cap(cf.ROWS),
                "speech_audio_seconds_cap": arm["family_budget"]["repeated_speech_audio_seconds_cap"],
                "roster_audio_seconds": round(arm["audio_seconds"], 6),
                "arithmetic": (f"{cf.ROWS:,} x {cf.CEILING} = {cf.ROWS * cf.CEILING:,}; FIT {cf.ROWS:,} x {cf.CEILING} x "
                               f"{cf.FIT_ENDPOINTS_PER_CONTACT} = {cf.fit_contact_cap(cf.ROWS):,}; audio ceil({arm['audio_seconds']:.6f} x "
                               f"{cf.CEILING}) = {arm['family_budget']['repeated_speech_audio_seconds_cap']:,}")},
        "smoke": {"rows": cf.SMOKE_ROWS, "generation_calls": cf.SMOKE_ROWS * cf.CEILING, "fit_endpoint_calls": cf.fit_contact_cap(cf.SMOKE_ROWS),
                  "speech_audio_seconds_cap": smoke["family_budget"]["repeated_speech_audio_seconds_cap"]},
        "note": ("The ceiling is exact and also the expected spend (no early exit). The FIT cap is structural and never run-cumulative; "
                 "the generation budget is run-cumulative across attempts."),
    }


def write_package(ids: dict, commit: str, at: str) -> dict:
    pkg = cf.PACKAGE
    measure = cf.fit_measure()
    pins = cf.candidate_pins()
    arm, smoke = ids["arm"], ids["smoke"]
    blocks = measurement_blocks(ids, measure)
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id",
                                           "fit_run_id", "protocol_hash", "rows", "run_id", "split_identity_hash")}
                  for k, v in ids.items()},
        "decision_rule_fixed_here": DECISION_RULE,
        "development_numbers_only": f"Every number is a {cf.FOLD_TITLE} development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": ("Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second "
                           "failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative "
                           "across attempts."),
        "one_factor": ONE_FACTOR, "prohibitions": PROHIBITIONS,
        "protocol_id": f"slurp-{cf.SLUG}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1",
        "source_tree": cf.SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "study_commit_at_registration": commit,
        "the_question": (
            f"What does the R1 c3 Solver template answer on {cf.FOLD_TITLE} -- per row, does the Solver carry an entity after v4g? -- so that "
            f"the c3 presence verdict of the VER-1 rule fixed on {cf.TUNING_TITLE} can be applied to the VER-1b sample pool on the same "
            "rows? (Verdict-source column: nothing is nominated and no benefit is claimed.)"
        ),
    }
    protocol_sha = wjson(f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(ids, commit, at, protocol_sha, pkg)
    shas = {name: wjson(f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "arms": {
            "arm": {"attempt_id": arm["attempt_id"], "role": "the sealed flight: every arm below is a column of it", "run_id": arm["run_id"]},
            "columns": {
                **{a: {"role": "candidate Solver instruction template (hash-pinned; the R1 c3 bytes)", **pins[a]} for a in cf.ARMS},
                cf.TWIN: {"role": "the in-flight twin: replicate_of lock, the null of every contrast"},
                cf.DELIVERING: {"role": "the delivering arm: LEFT of every contrast (the locked template, untemplated)",
                                "relpath": cf.LOCKED_TEMPLATE, "sha256": cf.LOCKED_TEMPLATE_SHA},
            },
        },
        "boundary": (f"A development read on a TRAIN fold (owner decisions 28 and 86); never a test claim; node-local, never a "
                     "system-level claim. No utterance text, transcript, gold label or model output is printed or persisted."),
        "decision_rule": DECISION_RULE,
        "fixed_rule_consumer": {
            "driver": cf.COMPOSER, "flag": "--verdict-run",
            "value": f"{arm['run_id']}:{arm['attempt_id']}:{cf.VERDICT_ARM}",
            "reads": f"runs/{arm['run_id']}/{arm['attempt_id']}/supply-variants/arm-<arm>-first-visit-outputs.jsonl and arm-<arm>-{cf.SCORER}-scores.json for the arms {cf.DELIVERING}, {cf.TWIN}, {cf.VERDICT_ARM}",
            "n1_signature": "the verdict run's own phases.json (the pre-Solver exemplar entity-free share), as for the R1 iterations",
        },
        "node_local": {
            "role": "diagnostic: localises where an official delta comes from; gates nothing",
            "driver": "scripts/analysis/slurp_nx_solver_column_read.py",
            "primary": "exact_set_normalised", "primary_view": "normalised",
            "secondaries": ["parse_valid", "empty_gold_false_fill", "nonempty_exact"], "secondaries_view": "normalised",
            "diagnostic": {"view": "raw", "metric": "exact_set", "also": ["raw-vs-normalised flip table per arm"]},
            "report_schema": "saea-nx-solver-column-read-v2",
            "bootstrap": {"cluster": "whole utterance", "draws": 10000, "seed": 20260915},
            "output": "analysis/" + cf.READ_RUN_ID + "/node-local",
        },
        "official_columns": {
            "scorer": cf.SCORER, "scoring_jobs": len(cf.ARM_ORDER),
            "render": "scripts/analysis/stage3_rollout_score.py --mode supply-variants",
            "paired_driver": "scripts/analysis/stage3_paired_read.py (column arms; --cluster-key sample_id)",
            "bootstrap": {"cluster_key": "sample_id", "draws": 10000, "seed": 20260915,
                          "unit": "row (paired); the whole-utterance number is the node-local read's own"},
            "passes": {
                **{f"{a}-vs-lock": {"left": cf.DELIVERING, "right": a, "gating": False} for a in cf.ARMS},
                "aa-vs-lock": {"left": cf.DELIVERING, "right": cf.TWIN, "gating": "sets the descriptive bar"},
            },
            "output": "analysis/" + cf.READ_RUN_ID + "/<pass>",
        },
        "output": {"analysis_root": "analysis/" + cf.READ_RUN_ID},
        "read_run_id": cf.READ_RUN_ID,
        "recipe_id": cf.RECIPE_ID,
        "registered_at_utc": at,
        "resampling": {"bootstrap_draws": 10000, "seed": 20260915},
        "run_ids": {"arm": arm["run_id"], "read": cf.READ_RUN_ID, "pool_read": vf.READ_RUN_ID, "pool": vf.ARM["run_id"]},
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "steps": [
            f"0. Refuse unless the READ row {cf.READ_RUN_ID} is root countersigned.",
            "1. Refuse unless the flight carries a COMPLETE sealed 1,080-row manifest with one complete official TRAIN score and the saea-supply-variant-arms-v4 receipt on every row, verified by the bundle (invariant I7v).",
            f"2. Official: render each arm's first-visit Solver answer through the delivered row's normaliser and projection and score it ONCE with {cf.SCORER} ({len(cf.ARM_ORDER)} jobs, never sharded); this writes the supply-variants files the composer reads.",
            "3. Twin null (aa vs lock) first, then the c3 column vs lock, both DESCRIPTIVE; per-scenario tables.",
            "4. Node-local (E2 reader schema v2; DIAGNOSTIC, gates nothing).",
            f"5. Hand the column to the VER-1b confirmation read (recipe {vf.PACKAGE}/analysis-recipe-v1.json, --verdict-run); the verdict-empty row counts are reported beside the TRAIN Fold B figures of the NX R1 flights.",
        ],
        "title": f"Cell {cf.CELL_LABEL} -- the Fold A Solver instruction-template column read as the VER-1 verdict source: the R1 c3 template and the twin, each against the delivering lock arm",
    }
    shas["analysis-recipe-v1.json"] = wjson(f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": contact_arithmetic(ids),
        "budget_arithmetic": {"arm_family_budget": arm["family_budget"], "smoke_family_budget": smoke["family_budget"]},
        "candidates": {a: {"author": "hand (the NX R1 candidate; unchanged bytes)", **pins[a],
                           "template_tokens_estimated": measure["template_tokens"][a]} for a in cf.ARMS},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "decision_rule": DECISION_RULE,
        "delivering_template": {"relpath": cf.LOCKED_TEMPLATE, "sha256": cf.LOCKED_TEMPLATE_SHA,
                                "template_tokens_estimated": measure["template_tokens"]["lock"]},
        "fit": {"status": "PENDING_CHECK"},
        "fit_measure": {"relpath": cf.R1_FIT_MEASURE, "sha256": sha_file(cf.R1_FIT_MEASURE),
                        "note": "the NX R1 iteration-1 measure, taken on the COMP-1b Fold A first Solver visits: its template_frame and token counts are the ones used here",
                        "summary": {k: measure[k] for k in ("chars_per_token_least_squares", "first_solver_visits", "items",
                                                            "prompt_tokens", "prompt_limit_tokens", "template_frame",
                                                            "arm_prompt_estimates", "source")}},
        "identity": ids,
        "owner_decisions": {
            "257": "the verification layer (VER-1) of the training-free RL round; VER-1c is the Fold A c3 verdict column",
            "258": f"option A proposed 2026-10-10: the Fold A confirmation of the rule fixed on {cf.TUNING_TITLE} (not yet ratified)",
            "139": "no prior: the expectation is declared before flight (zero: a verdict source)",
            "192": "the declared effect is on file BEFORE flight (claims_benefit false)",
            "228-234": "NX programme: the node-template column instrument (E1/E2), base = the COMP-1b lock",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "prohibitions": PROHIBITIONS,
        "registered_at_utc": at,
        "registration_basis": (f"engineering brief 2026-10-10: register {cf.CELL_LABEL} from owner decision 257's execution plan "
                               f"(a c3 column on Fold A beside the VER-1b pool) and {cf.PROGRAMME}. HELD: the owner / root admission is still "
                               "required; nothing here authorises a flip or a flight."),
        "rows": cf.ROWS,
        "schema": "saea-registered-facts-v1",
        "stage3_measurement": blocks,
        "study_commit_at_registration": commit,
        "the_cell": {
            "base": f"the COMP-1b composition (agree-vote-seed + centroid-boundary-key) as a consumption-module block on lock {cf.LOCK}, review loop OFF",
            "program": cf.PROGRAM, "ceiling": cf.CEILING,
            "consumption_module": json.loads(rd(f"configs/baseline/{arm['baseline_fragment']}.json"))["native_episode"]["consumption_module"],
        },
    }
    shas["registered-facts-v1.json"] = wjson(f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": (f"A DRAFT for root to mint on the data root with scripts/flights/ver/{cf.SHORT}_mint_receipt.py (status decided, "
                        "recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'."),
        "antecedents": {
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "candidates_readme": {"path": cf.R1_CANDIDATES_README, "sha256": sha_file(cf.R1_CANDIDATES_README)},
            "derive_script": {"path": f"scripts/flights/ver/{cf.SHORT}_derive_cells.py", "sha256": sha_file(f"scripts/flights/ver/{cf.SHORT}_derive_cells.py")},
            "exchange_rates": {"path": cf.EXCHANGE, "sha256": sha_file(cf.EXCHANGE)},
            "instrument_design": {"path": cf.SPEC, "sha256": sha_file(cf.SPEC)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": cf.PREREG, "sha256": None},
            "programme": {"path": cf.PROGRAMME, "sha256": sha_file(cf.PROGRAMME)},
            "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None},
            "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit,
        },
        "authorization_basis": (f"Owner decisions 257 (2026-10-10), 258 option A (proposed), 228-234, 139, 192, 28/86; the node-template instrument "
                                f"({cf.SPEC}); {OWNER_DECISIONS} section Decisions 228-236."),
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "cell_kind": (f"Stage-3 same-flight NODE-TEMPLATE column cell (NX instrument E1, label none), the Fold A c3 verdict source of the "
                      f"VER-1 rule (claims_benefit false). One arm on {cf.FOLD_TITLE} {cf.ROWS:,} with {cf.K} Solver template arms "
                      f"({ARM_LIST}, {cf.TWIN} twin, {cf.DELIVERING} delivering), and a four-row form smoke."),
        "claim_boundary": ("No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a "
                           "node column read on a development fold, descriptive."),
        "coordinator": "Fable5.1",
        "decision": (f"Fly cell {cf.CELL_LABEL}: the COMP-1b module composition with the Reviewer loop off on {cf.FOLD_TITLE} under "
                     f"{cf.PROGRAM} with a one-candidate Solver template column ({ARM_LIST}); read {ARM_LIST} and {cf.TWIN} against {cf.DELIVERING} "
                     "in the same flight, descriptively; hand the c3 column to the VER-1b confirmation read."),
        "decision_id": cf.DECISION_ID,
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the registered module block, Fold A re-target and the one-candidate template column",
            "a nomination or a benefit claim from this column",
            "opening an arm column before the READ row is countersigned",
        ],
        "owner": "root",
        "population": {"count": cf.ROWS, "fold_b_contact_authorized": False,
                       "partition": f"{cf.FOLD_TITLE} {cf.ROWS:,}, unchanged; the smoke flies its first {cf.SMOKE_ROWS} rows",
                       "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None,
        "registered_hashes": {k: {"composed_config": v["composed_config_hash"], "protocol": v["protocol_hash"]} for k, v in ids.items()},
        "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": cf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True,
                    "slot_tokens": 24576, "slots": 4},
        "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(f"{pkg}/root-admission-draft-v1.json", draft)
    prereg = (
        f"# Cell {cf.CELL_LABEL} (verification layer, Fold A c3 verdict column): preregistration\n\n"
        f"Registered {at[:10]} at study commit `{commit}`, before any contact, by script (decision 58) from the committed COMP-1b Fold A "
        "fragments and the consumption-module compiler under owner decision 257 (decision 258 option A, proposed). Development numbers only.\n\n"
        "| item | value |\n| --- | --- |\n"
        f"| base | the COMP-1b composition as a module block on lock {cf.LOCK} (agree-vote-seed + centroid-boundary-key ON), Reviewer loop OFF, no tool schema on any role |\n"
        f"| program | `{cf.PROGRAM}` (ceiling {cf.CEILING} = {cf.BASE_CONTACTS} + ({cf.K} - 1)) |\n"
        f"| arms | `{ARM_LIST}` (the R1 c3 template, pinned `{cf.CANDIDATE_PATHS[cf.ARMS[0]]}`, sha256 `{pins[cf.ARMS[0]]['sha256']}`), `{cf.TWIN}` (twin of `{cf.DELIVERING}`), `{cf.DELIVERING}` (delivering, `{cf.LOCKED_TEMPLATE}`) |\n"
        "| design / claim | `same-flight-node-column` / descriptive; the verdict source of the VER-1 rule, `claims_benefit` false, expected effect 0.0 pp |\n"
        f"| rosters | tuning `{cf.TUNING_ROSTER}`; read `{cf.READ_ROSTER}` |\n"
        f"| runs | `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{cf.READ_RUN_ID}`; pool `{vf.ARM['run_id']}` |\n"
        f"| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |\n"
        f"| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |\n"
        f"| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |\n\n"
        "## Attempt state (no recovery)\n\nThe smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke "
        f"{cf.SMOKE_ROWS * cf.CEILING} model calls, FIT endpoint cap {cf.fit_contact_cap(cf.SMOKE_ROWS)} (structural: {cf.SMOKE_ROWS} rows x "
        f"{cf.CEILING} contacts x {cf.FIT_ENDPOINTS_PER_CONTACT} endpoints); arm {cf.ROWS * cf.CEILING:,} model calls, FIT cap "
        f"{cf.fit_contact_cap(cf.ROWS):,}. At most one recovery re-registration per cell.\n\n"
        f"## Exposure disclosure\n\n{cf.TUNING_DISCLOSURE}\n\n"
        f"## Decision rule (fixed here)\n\n{DECISION_RULE}\n\n## The measurement declaration\n\n```json\n"
        + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    shas["__prereg__"] = wr(cf.PREREG, prereg)
    return {"shas": shas, "blocks": blocks, "protocol_sha": protocol_sha}


def ledger_rows(ids: dict, commit: str, at: str, shas: dict) -> str:
    pkg = cf.PACKAGE
    scope = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any "
             f"role; the COMP-1b module composition on lock {cf.LOCK} with the Reviewer loop off; Solver instruction-template column of "
             f"{cf.K} arms (the R1 candidate {ARM_LIST} with its pinned bytes, the {cf.TWIN} twin, the locked delivering {cf.DELIVERING} arm) "
             "at the one Solver visit")
    inherited = (f"{cf.FOLD_TITLE} discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells B0/B0r, "
                 "B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, KPROBE, COMP-1 (arm, "
                 "in-chain A/A and smoke), COMP-1b (arm and smoke), the model-free COMP-2 stage-column rehearsal and the model-free R1 "
                 "candidate-authoring contrast tables (aggregate counts, computed on this fold); the rule fed by this column was fixed on "
                 "TRAIN Fold B; this cell opens no split. Prior exposure is inherited in full.")
    note_common = (
        f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {at[:10]} at study commit {commit} by the {cf.ROUND_LABEL} "
        f"engineering agent (worktree {cf.WORKTREE}, branch {cf.BRANCH}); owner decision 257 (decision 258 option A, proposed). "
        "HELD: this registration performs no contact and authorises none. READINESS HELD: root countersigns the five DRAFT rows, mints "
        f"{cf.DECISION_RELPATH} (decision id {cf.DECISION_ID}) from the package's root-admission-draft-v1.json with scripts/flights/ver/{cf.SHORT}_mint_receipt.py "
        f"(four eligible run ids), then scripts/flights/ver/{cf.SHORT}_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each "
        "cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
        f"Measurement declaration: same-flight-node-column, expected_effect_pp 0.0, claims_benefit false (the verdict source of the VER-1 rule, "
        f"not a nomination), primary_metric_key slu, floor SLU {cf.FLOOR_SLU_PP} / intent {cf.FLOOR_INTENT_PP} (provisional, borrowed), aa twin; "
        f"tuning roster {cf.TUNING_ROSTER}, read roster {cf.READ_ROSTER}. Read: {cf.READ_RUN_ID} by the recipe in the package. Stop and "
        "preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No paper-scale profile, no test-split contact, "
        "no comparator re-flight and no admission entry from this row."
    )

    def row(date, rid, profile, what, model, carrier, split, consumed, calls, audio, gpu, artifacts, notes):
        cells = [date, rid, profile, what, model, carrier, "discovery", split, consumed, str(calls), str(audio), str(gpu), inherited, artifacts, notes]
        return "| " + " | ".join(cells) + " |"

    def plan_row(kind, fit):
        i = ids[kind]
        prefix = cf.names(kind)["prefix"]
        what = (f"{cf.ROUND_LABEL}: the R1 c3 Solver template column on {cf.FOLD_TITLE} (verdict source of the rule fixed on {cf.TUNING_TITLE})"
                if kind == "arm" else "Four-row form smoke of " + cf.ROUND_LABEL)
        if fit:
            what += " -- FIT spend identity, request envelopes only, no generation"
        plan = f"{pkg}/{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"
        calls = i["family_budget"]["fit_endpoint_calls_cap"] if fit else i["family_budget"]["generation_calls_cap"]
        plan_sha = shas[f"{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"]
        attempt = i["fit_attempt_id"] if fit else i["attempt_id"]
        notes = (note_common.replace("Measurement declaration: same-flight-node-column",
                                     "Measurement declaration: " + ("same-flight-node-column" if kind == "arm" else "form-proof"))
                 + f" Plan SHA256 {plan_sha}; attempt {attempt}. Protocol hash {i['protocol_hash']}; composed config {i['composed_config_hash']}; expected session {cf.SESSION} (attach only).")
        return row(at, i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], what, scope,
                   f"slurp {cf.FOLD_TITLE} {i['rows']}", i["split_identity_hash"], "no", calls,
                   i["family_budget"]["repeated_speech_audio_seconds_cap"], i["family_budget"]["gpu_hours_fit_inclusive"], plan, notes)

    read = row(
        at[:10], cf.READ_RUN_ID, "model-free-check",
        (f"The same-flight Solver template-column read of {cf.ROUND_LABEL}: per arm ({ARM_LIST}, {cf.TWIN}; {cf.DELIVERING} the delivering "
         f"reference) the official pooled SLU-F1 and intent of each arm's column scored ONCE with {cf.SCORER} ({len(cf.ARM_ORDER)} column "
         "scorings, never sharded), paired bootstraps against lock with the aa twin as the descriptive bar, the node-local normalised "
         "exact-set diagnostics (E2 reader v2, gates nothing), and the c3 presence verdict flags handed to the VER-1b confirmation read; "
         f"by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and three official column scorings",
        f"slurp {cf.FOLD_TITLE} {cf.ROWS}, the sealed {cf.ROUND_LABEL} flight's Solver template columns (after the seal)",
        ids["arm"]["split_identity_hash"], "no", 0, 0, 0, f"{pkg}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any arm column is "
         f"opened) {at[:10]} at study commit {commit}. Recipe {cf.RECIPE_ID}; output analysis/{cf.READ_RUN_ID}. One READ row covers the "
         "descriptive contrasts, the twin null and the verdict-source hand-off. Its ceiling is descriptive; it nominates and admits nothing."),
    )
    lines = [
        cf.LEDGER_MARK + " (owner decision 257, decision 258 option A proposed) -- the arm, its four-row smoke and the READ row (DRAFT, root countersignature pending)",
        "",
        "Four unconsumed flight rows and one READ row registered with the flight. No A/A cell: the twin arm aa flies inside every row. None of "
        "these rows is countersigned and none authorises a contact.",
        "",
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        plan_row("arm", False), plan_row("arm", True), plan_row("smoke", False), plan_row("smoke", True), read, "",
    ]
    return "\n".join(lines)


def write_ledger(text: str) -> None:
    """Replace this cell's section (its heading up to the next ``## `` heading, or the end); append at the END when absent."""

    current = rd(LEDGER)
    tail = ""
    if cf.LEDGER_MARK in current:
        start = current.index(cf.LEDGER_MARK)
        following = current.find("\n## ", start + len(cf.LEDGER_MARK))
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
    args = parser.parse_args(argv)
    ids = identities()
    result = write_package(ids, args.study_commit, args.registered_at)
    if not args.no_ledger:
        write_ledger(ledger_rows(ids, args.study_commit, args.registered_at, result["shas"]))
    print(json.dumps({"package": cf.PACKAGE, "files": sorted(result["shas"]),
                      "composed": {k: v["composed_config_hash"] for k, v in ids.items()},
                      "protocol": {k: v["protocol_hash"] for k, v in ids.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
