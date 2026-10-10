#!/usr/bin/env python3
"""Write the readiness package of cell VER-1b (the three-sample greedy-first Solver pool on TRAIN Fold A, the confirmation pool of the
rule fixed on TRAIN Fold B) and its DRAFT exposure-ledger rows, from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing, countersigns nothing. Re-running replaces the package files and the ledger section in place (the hashes move at
the flip; the flip loop rewrites them).

Writes under ``docs/readiness/2026-10-10-slurp-ver1b-samples-fold-a-v1/``: ``registered-facts-v1.json`` (with the CANONICAL
``stage3_measurement`` block keyed by run id), ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``; beside it the preregistration; and the five DRAFT ledger rows (arm, arm FIT, smoke, smoke FIT, READ),
appended in their own heading block at the END of ``docs/exposure-ledger.md``. The package README is hand-written.

    python -B scripts/flights/ver/ver1b_write_registration.py --study-commit <sha> \\
        --registered-at 2026-10-10T12:00:00.000000+00:00 [--no-ledger]

When the cell baseline already carries the minted ``prepared_phase_supply`` pin (after the flip), the registered plans copy it verbatim
(``flight_registration_check`` "registered-supply-binding"); before the flip the plans carry the MINTED_AT_THE_FLIP marker.

The sample count, the support threshold, the roster and every id come from ``ver1b_family``; the prose below is built from them.
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

REPO_ROOT = vf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
ROLL2_RECIPE = "docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1/analysis-recipe-v1.json"
VER1A_PACKAGE = "docs/readiness/2026-10-10-slurp-ver1a-samples-fold-b-v1"

#: the offline composer invocation that is the READ (the c3 column of cell VER-1c is the verdict source)
COMPOSER_COMMAND = (
    f"python -B {vf.COMPOSER} --mode read --run-id {vf.ARM['run_id']} --attempt {vf.ARM['attempt_id']} --split train --rows {vf.ROWS} "
    f"--n {vf.RULE_N} --s {vf.RULE_S} --thetas {vf.RULE_THETA:g} "
    f"--verdict-run {cf.ARM['run_id']}:{cf.ARM['attempt_id']}:{cf.VERDICT_ARM} --label VER1B-FOLD-A-V1 --sealed-scorer {vf.SCORER}"
)

FIXED_RULE = (
    f"THE FIXED RULE (fixed on {vf.TUNING_ROSTER} by the VER-1a pool read, {VER1A_PACKAGE}; NOT re-tuned on this roster): the support "
    f"filter over the first n = {vf.RULE_N} samples at s = {vf.RULE_S} (an entity is kept iff supported by >= {vf.RULE_S} of the "
    f"{vf.RULE_N} samples; same type, normalised-filler character F1 >= {vf.SOLVER_COMMIT['similarity_threshold']}), the base answer = "
    f"sample 0 (the greedy sample) with its own labels, the c3 presence verdict (cell VER-1c's {cf.VERDICT_ARM} column answered no entity "
    f"after the registered v4g normaliser) gated by the pre-Solver signature N1 >= theta = {vf.RULE_THETA:g}, delivered through the lock's v4g "
    "normaliser"
)

DECISION_RULE = (
    f"OFFLINE SEALED-POOL CONFIRMATION READ ({vf.CELL_LABEL}; owner decision 257, decision 258 option A proposed 2026-10-10; claim ceiling "
    "'descriptive' for the pool; the pool cell claims NO benefit). "
    f"One flight, one Perception visit and one grouped Solver visit per row of {vf.FOLD_TITLE}: sample 0 greedy, {vf.DRAWN_TEXT} at "
    f"temperature {vf.SAMPLE_TEMPERATURE:g}, all over the SAME state and evidence, committed in flight by saea-commit-plurality-support-v1 at "
    f"min_support {vf.MIN_SUPPORT}. {FIXED_RULE}. "
    "THE READS, all from sealed bytes, model-free: (1) CUSTODY (row accounting): "
    f"{vf.ROWS:,} in, {vf.ROWS:,} out; every row's solver_group carries exactly {vf.SAMPLES} samples in custody (invariant I7g) with "
    f"temperatures {vf.TEMPERATURES_TEXT} and the pinned seeds {vf.SEEDS_TEXT}; the replay of the commit reproduces the sealed delivered text "
    "on every row; zero tool calls. (2) PER-SAMPLE scores: each custodied raw sample rendered to one outputs COPY "
    f"(scripts/analysis/stage3_rollout_score.py --stage render, {vf.SAMPLES} samples auto-detected) and scored ONCE with the registered scorer, "
    "both as sealed (unprojected) and through the lock's delivery rule v4g applied OFFLINE (scripts/analysis/slurp_nx_postproc_v4_apply.py "
    "--apply v4g; the in-flight cell delivers the unnormalised commit because the loader refuses a deliver_normaliser beside a grouped "
    "visit); sample 0 is read against the VER-1c lock column on the same rows as the byte-identity audit of the greedy first sample "
    "(llama.cpp greedy decoding is not bitwise reproducible across batch shapes, so equality is measured, not assumed). "
    f"(3) THE CONFIRMATION: the fixed rule applied to the sealed pool and the VER-1c c3 column by the offline composer ({COMPOSER_COMMAND}); "
    f"reported with the whole-utterance paired bootstrap CI95 (10,000 draws, seed 20260915) against the lock column of VER-1c (the "
    f"delivering arm, request-identical to today's delivery), against the pool's own sample 0 and against the sealed delivered commit "
    f"(re-scored), pooled SLU-F1 and intent, false fills removed, non-empty exact rows lost / gained, per-scenario natural and "
    f"equal-stratum tables. CRITERION, on file BEFORE the flight (owner decision 258 may only tighten it): the rule is CONFIRMED iff its "
    f"pooled SLU-F1 delta against the VER-1c lock column is at or above the {vf.FLOOR_SLU_PP} pp offline sealed-pool floor of the instrument "
    f"note (section 2d) AND its CI95 lower bound is above zero AND the intent moves by no more than the {vf.FLOOR_INTENT_PP} pp floor; "
    "anything else is reported as NOT CONFIRMED with the numbers, never softened. NOTHING IS TUNED OR SELECTED HERE: n, s and theta are the "
    f"fixed rule's; the read roster is {vf.READ_ROSTER}, the tuning roster {vf.TUNING_ROSTER}; a confirmed rule is admitted, if at all, "
    "by the owner under its own registration."
)

ONE_FACTOR = (
    f"none -- a pool cell: the base is the NX R5 composed arm / R6-P1 / VER-1a base (COMP-1b components, lock {vf.LOCK} compiled blocks, "
    f"review loop off) unchanged, and the single registered departure is the grouped Solver visit (samples {vf.SAMPLES}: sample 0 "
    f"greedy, {vf.DRAWN_TEXT} at temperature {vf.SAMPLE_TEMPERATURE:g}, plurality-support commit at min_support {vf.MIN_SUPPORT}), which exists to "
    "produce the sample pool and not to move a delivered metric"
)

PROHIBITIONS = [
    f"No test-split, DEV or {vf.TUNING_TITLE} contact or read (the pool is {vf.FOLD_TITLE}; the rule was fixed on {vf.TUNING_TITLE} by the VER-1a read).",
    "No second factor: one departure from the R5 composed arm, the grouped greedy-first Solver visit.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No deliver_normaliser in flight (refused beside a grouped Solver visit); v4g is applied OFFLINE to the custodied samples.",
    f"No re-tuning of the fixed rule (n = {vf.RULE_N}, s = {vf.RULE_S}, theta {vf.RULE_THETA:g}) and no rule selection on this roster.",
    "No verification rule is wired or flown by this cell: the application of the rule is an OFFLINE read.",
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
            "roster_receipt": document["population"].get("roster_receipt", vf.ROSTER[kind]),
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
                f"{vf.CELL_LABEL} makes no effectiveness claim of its own: it seals a {vf.ROWS:,}-row x {vf.SAMPLES}-sample pool on "
                f"{vf.FOLD_TITLE} ({vf.SCORING_TEXT}) so that the VER-1 rule -- scoring and selection over the frozen core's own sampled "
                f"answers -- can be CONFIRMED OFFLINE over sealed bytes, together with the c3 column of cell VER-1c on the same rows, at the "
                f"{vf.FLOOR_SLU_PP} pp floor of {INSTRUMENT_NOTE} section 2d. THE FIXED RULE: n = {vf.RULE_N}, s = {vf.RULE_S}, theta "
                f"{vf.RULE_THETA:g} (support filter over the {vf.RULE_N} samples at s = {vf.RULE_S}, c3 verdict x N1 >= {vf.RULE_THETA:g} gate, v4g) "
                f"was FIXED on the tuning roster {vf.TUNING_ROSTER} by the VER-1a pool read and is not re-tuned on the read roster "
                f"{vf.READ_ROSTER}. Any benefit claim belongs to a later flown cell, each of which declares its own block. Owner decisions "
                "139 and 192: the expectation is on file before flight and it is zero because the cell is an asset."
            ),
            "primary_metric": "slu_f1",
            "read_roster": vf.READ_ROSTER,
            "rows": vf.ROWS,
            "tuning_roster": vf.TUNING_ROSTER,
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "note": (
                f"Four {vf.FOLD_TITLE} rows (the COMP-1b Fold A smoke prefix) prove FORM and nothing else: the {vf.PROGRAM} program loads, "
                f"the Solver visit fans out to {vf.SAMPLES} custodied samples (sample 0 at temperature 0, {vf.DRAWN_TEXT} at "
                f"{vf.SAMPLE_TEMPERATURE:g}), the plurality-support commit at min_support {vf.MIN_SUPPORT} seals and replays, every request "
                "fits, and the episode completes. Scored by no one, read by no one."
            ),
            "primary_metric": "none (structural form only)", "read_roster": vf.READ_ROSTER, "rows": vf.SMOKE_ROWS, "tuning_roster": "none",
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
            "note": (f"the {vf.FOLD_TITLE} first-phase supply at w_agree 1.0 with the centroid key on this roster; the flip mints it under "
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
            f"scripts/flights/ver/{vf.SHORT}_batch_chain.sh and the batch driver."
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
        "note": (f"The ceiling is exact and also the expected spend: every row makes one Perception and {vf.SAMPLES_WORD} Solver contacts (no "
                 "early exit). The FIT cap is structural and never run-cumulative; the generation budget is run-cumulative across attempts."),
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
        "development_numbers_only": f"Every number is a {vf.FOLD_TITLE} development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": ("Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second "
                           "failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative "
                           "across attempts."),
        "fixed_rule": {"n": vf.RULE_N, "s": vf.RULE_S, "theta": vf.RULE_THETA, "tuning_roster": vf.TUNING_ROSTER,
                       "read_roster": vf.READ_ROSTER, "fixed_by": f"{VER1A_PACKAGE} (the VER-1a pool read)",
                       "statement": FIXED_RULE},
        "one_factor": ONE_FACTOR, "prohibitions": PROHIBITIONS,
        "protocol_id": f"slurp-{vf.SLUG}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1",
        "source_tree": vf.SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "study_commit_at_registration": commit,
        "the_question": (
            f"Does the VER-1 rule fixed on {vf.TUNING_TITLE} (the n = {vf.RULE_N}, s = {vf.RULE_S} support filter over the lock's own sampled "
            f"answers, the c3 verdict x N1 >= {vf.RULE_THETA:g} gate, v4g at delivery) raise the official pooled SLU-F1 over today's delivery on "
            f"{vf.FOLD_TITLE}, a roster it was not fixed on? The cell seals the {vf.SAMPLES_WORD}-sample greedy-first pool that question is "
            "answered on, offline. (Pool cell: no benefit is claimed.)"
        ),
    }
    protocol_sha = wjson(f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(ids, commit, at, protocol_sha, pkg)
    shas = {name: wjson(f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": (f"{INSTRUMENT_NOTE} (the {vf.FLOOR_SLU_PP} pp offline sealed-pool instrument); owner decision 257 (2026-10-10), decision "
                      f"258 option A (proposed); the ROLL-2 recipe pattern {ROLL2_RECIPE}; the VER-1a recipe {VER1A_PACKAGE}/analysis-recipe-v1.json; "
                      "the stage-3 algorithm label inference-time-verification-v1."),
        "cell_kind": f"POOL -- a sealed {vf.SAMPLES_WORD}-sample greedy-first Solver pool on {vf.FOLD_TITLE}. DESCRIPTIVE: no comparator block, no gate, no admission.",
        "claim_boundary": ("DESCRIPTIVE for the pool; a confirmation or non-confirmation of the fixed rule on a development fold. No "
                           "system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim."),
        "composer_command": COMPOSER_COMMAND,
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "decision_rule": DECISION_RULE,
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flight itself)",
        "fixed_rule": protocol["fixed_rule"],
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
            f"temperatures {vf.TEMPERATURES_TEXT} and seeds {vf.SEEDS_TEXT}; the commit replay of saea-commit-plurality-support-v1 at "
            f"min_support {vf.MIN_SUPPORT} / similarity {vf.SOLVER_COMMIT['similarity_threshold']} reproduces the sealed delivered answer for "
            "every row; zero native task-contract tool calls."),
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": vf.READ_RUN_ID, "smoke": smoke["run_id"],
                    "smoke_fit": smoke["fit_run_id"], "verdict_column": cf.ARM["run_id"]},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_render": f"scripts/analysis/stage3_rollout_score.py --stage render: one outputs COPY per Solver sample index (0..{vf.LAST_SAMPLE}), each row's solver_group.samples[index].parsed_answer rendered through the canonical analysis path; the sample count is detected from the sealed pool.",
            "2_score": f"scripts/analysis/stage3_rollout_score.py --stage score: each of the {vf.SAMPLES} copies scored ONCE through the registered scorer (never core.scoring_batch: every copy is a derived read).",
            "3_v4g": f"scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g over each custodied sample and the replayed commit ({vf.V4G_LOCK_RECORD}): lock v2.2's delivery rule applied OFFLINE, because the in-flight cell delivers the unnormalised commit.",
            "4_pairs": f"scripts/analysis/stage3_rollout_score.py --stage pairs: per-row best / worst / delivered; the oracle best-of-{vf.SAMPLES} ceiling stated as an UPPER BOUND, never as a result; sample 0 against the VER-1c lock column on these rows (greedy byte-identity audit).",
            "5_confirmation": f"{vf.COMPOSER} --mode read over the sealed pool with the VER-1c c3 column as the verdict source (--verdict-run {cf.ARM['run_id']}:{cf.ARM['attempt_id']}:{cf.VERDICT_ARM}), n = {vf.RULE_N}, s = {vf.RULE_S}, theta {vf.RULE_THETA:g}: the fixed rule is applied, not selected; the criterion of the decision rule is evaluated and quoted verbatim.",
        },
        "what_is_not_here": ("No comparator block, no margins block and no gate: VER-1b is a pool. The same-flight and cross-flight floors "
                             "are CONTEXT, never this cell's bar; the bar is the confirmation criterion of the decision rule."),
    }
    shas["analysis-recipe-v1.json"] = wjson(f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": contact_arithmetic(ids),
        "budget_arithmetic": {"arm_family_budget": arm["family_budget"], "smoke_family_budget": smoke["family_budget"]},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "decision_rule": DECISION_RULE,
        "fit": {"status": "PENDING_CHECK"},
        "fixed_rule": protocol["fixed_rule"],
        "identity": ids,
        "owner_decisions": {
            "257": "the verification layer (VER-1) of the training-free RL round; VER-1b seals the Fold A confirmation pool",
            "258": f"option A proposed 2026-10-10: the Fold A confirmation of the rule fixed on {vf.TUNING_TITLE} at n = {vf.RULE_N} (not yet ratified)",
            "139": "no prior: the expectation is declared before flight (zero: an asset)",
            "192": "the declared effect is on file BEFORE flight (claims_benefit false)",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "prohibitions": PROHIBITIONS,
        "registered_at_utc": at,
        "registration_basis": (f"engineering brief 2026-10-10: register {vf.CELL_LABEL} from owner decision 257's execution plan "
                               f"(VER-1b Fold A confirmation pool), {vf.ROLL_READ} and {vf.AGGREGATION_READ}. HELD: the owner / root admission "
                               "is still required; nothing here authorises a flip or a flight."),
        "rows": vf.ROWS,
        "schema": "saea-registered-facts-v1",
        "stage3_measurement": blocks,
        "study_commit_at_registration": commit,
        "the_cell": {
            "base": "the NX R5 composed arm / R6-P1 / VER-1a base: COMP-1b components on lock v2.2, review loop OFF, as a hand-written fragment (no consumption_module block)",
            "program": vf.PROGRAM, "ceiling": vf.CEILING,
            "solver": {"samples": vf.SAMPLES, "decoding_overrides": vf.SOLVER_OVERRIDES, "commit": vf.SOLVER_COMMIT},
            "deliver_normaliser": f"none in flight (refused beside samples >= 2); v4g applied offline",
        },
    }
    shas["registered-facts-v1.json"] = wjson(f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": (f"A DRAFT for root to mint on the data root with scripts/flights/ver/{vf.SHORT}_mint_receipt.py (status decided, "
                        "recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'."),
        "antecedents": {
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "derive_script": {"path": f"scripts/flights/ver/{vf.SHORT}_derive_cells.py", "sha256": sha_file(f"scripts/flights/ver/{vf.SHORT}_derive_cells.py")},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": vf.PREREG, "sha256": None},
            "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None},
            "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit,
        },
        "authorization_basis": f"Owner decisions 257 (2026-10-10), 258 option A (proposed), 139, 192, 28/86; {INSTRUMENT_NOTE}; {vf.ROLL_READ}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "cell_kind": (f"Stage-3 sealed-sample-pool cell (label inference-time-verification-v1), a POOL (claims_benefit false). One arm on "
                      f"{vf.FOLD_TITLE} {vf.ROWS:,} with a {vf.SAMPLES_WORD}-sample greedy-first Solver visit, and a four-row form smoke."),
        "claim_boundary": ("No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; "
                           "a sealed pool on a development fold."),
        "coordinator": "Fable5.1",
        "decision": (f"Fly cell {vf.CELL_LABEL}: the R5 composed arm (COMP-1b on lock {vf.LOCK}, review loop off) on {vf.FOLD_TITLE} under "
                     f"{vf.PROGRAM} with the Solver visit grouped at samples {vf.SAMPLES} ({vf.SCORING_TEXT}, plurality commit at "
                     f"min_support {vf.MIN_SUPPORT}); seal the pool; apply the rule fixed on {vf.TUNING_TITLE} offline."),
        "decision_id": vf.DECISION_ID,
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the registered grouped greedy-first Solver visit and the Fold A re-target",
            "re-tuning the fixed rule or selecting a rule on this roster",
            "wiring or flying a verification rule (the application is an offline read)",
            "opening a sample column before the READ row is countersigned",
        ],
        "owner": "root",
        "population": {"count": vf.ROWS, "fold_b_contact_authorized": False,
                       "partition": f"{vf.FOLD_TITLE} {vf.ROWS:,}, unchanged; the smoke flies its first {vf.SMOKE_ROWS} rows",
                       "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None,
        "registered_hashes": {k: {"composed_config": v["composed_config_hash"], "protocol": v["protocol_hash"]} for k, v in ids.items()},
        "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": vf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True,
                    "slot_tokens": 24576, "slots": 4},
        "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(f"{pkg}/root-admission-draft-v1.json", draft)
    prereg = (
        f"# Cell {vf.CELL_LABEL} (verification layer, Fold A confirmation sample pool): preregistration\n\n"
        f"Registered {at[:10]} at study commit `{commit}`, before any contact, by script (decision 58) from the committed COMP-1b Fold A "
        "fragments and the consumption-module compiler under owner decision 257 (decision 258 option A, proposed). Development numbers only.\n\n"
        "| item | value |\n| --- | --- |\n"
        "| base | the NX R5 composed arm / R6-P1 / VER-1a base: COMP-1b (agree-vote-seed + centroid-boundary-key ON), lock v2.2 compiled blocks, Reviewer loop OFF, no tool schema on any role |\n"
        f"| the one departure | Solver visit grouped at samples {vf.SAMPLES}: sample 0 greedy (`decoding_overrides.greedy_first`), {vf.DRAWN_TEXT} at temperature {vf.SAMPLE_TEMPERATURE:g}, seed_offset 0; commit `saea-commit-plurality-support-v1` at min_support {vf.MIN_SUPPORT}, similarity {vf.SOLVER_COMMIT['similarity_threshold']} |\n"
        f"| program | `{vf.PROGRAM}` (ceiling {vf.CEILING} = 1 + 1 x {vf.SAMPLES}); a registered member of the review-off module family |\n"
        "| delivery | the unnormalised commit (the loader refuses a deliver_normaliser beside a grouped visit); v4g is applied offline |\n"
        "| design / claim | `offline-sealed-pool` / descriptive; a POOL cell, `claims_benefit` false, expected effect 0.0 pp |\n"
        f"| the fixed rule | n = {vf.RULE_N}, s = {vf.RULE_S}, theta {vf.RULE_THETA:g}; FIXED on `{vf.TUNING_ROSTER}`, confirmed (not re-tuned) on `{vf.READ_ROSTER}` |\n"
        f"| rosters | tuning `{vf.TUNING_ROSTER}`; read `{vf.READ_ROSTER}` |\n"
        f"| runs | `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{vf.READ_RUN_ID}`; verdict column `{cf.ARM['run_id']}` |\n"
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
             f"the NX R5 composed arm (COMP-1b on lock {vf.LOCK}, Reviewer loop off) with the Solver visit grouped at samples {vf.SAMPLES} "
             f"({vf.SCORING_TEXT}, plurality-support commit at min_support {vf.MIN_SUPPORT}, no in-flight delivery normaliser)")
    inherited = (f"{vf.FOLD_TITLE} discovery rows already exposed by the sealed dual-store anchor, the released direct anchor, cells B0/B0r, "
                 "B1 and its twin, B4b, B4b-rep, B5e, B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr, ROLL-2, CONV, KPROBE, COMP-1 (arm, "
                 "in-chain A/A and smoke), COMP-1b (arm and smoke), the model-free COMP-2 stage-column rehearsal and the model-free VER-1 "
                 "composer / aggregation reads over the ROLL-2 pool; the rule applied here was fixed on TRAIN Fold B; this cell opens no "
                 "split. Prior exposure is inherited in full.")
    note_common = (
        f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {at[:10]} at study commit {commit} by the {vf.ROUND_LABEL} "
        f"engineering agent (worktree {vf.WORKTREE}, branch {vf.BRANCH}); owner decision 257 (decision 258 option A, proposed). "
        "HELD: this registration performs no contact and authorises none. READINESS HELD: root countersigns the five DRAFT rows, mints "
        f"{vf.DECISION_RELPATH} (decision id {vf.DECISION_ID}) from the package's root-admission-draft-v1.json with scripts/flights/ver/{vf.SHORT}_mint_receipt.py "
        f"(four eligible run ids), then scripts/flights/ver/{vf.SHORT}_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each "
        "cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
        "Measurement declaration: offline-sealed-pool, expected_effect_pp 0.0, claims_benefit false (a pool cell); the rule is FIXED "
        f"(n = {vf.RULE_N}, s = {vf.RULE_S}, theta {vf.RULE_THETA:g}; tuning roster {vf.TUNING_ROSTER}, read roster {vf.READ_ROSTER}). "
        f"Read: {vf.READ_RUN_ID} by the recipe in the package. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery "
        "re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
    )

    def row(date, rid, profile, what, model, carrier, split, consumed, calls, audio, gpu, artifacts, notes):
        cells = [date, rid, profile, what, model, carrier, "discovery", split, consumed, str(calls), str(audio), str(gpu), inherited, artifacts, notes]
        return "| " + " | ".join(cells) + " |"

    def plan_row(kind, fit):
        i = ids[kind]
        prefix = vf.names(kind)["prefix"]
        what = (f"{vf.ROUND_LABEL}: the {vf.SAMPLES_WORD}-sample greedy-first Solver pool on {vf.FOLD_TITLE} (confirmation pool of the rule fixed on "
                f"{vf.TUNING_TITLE})" if kind == "arm" else "Four-row form smoke of " + vf.ROUND_LABEL)
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
                   f"slurp {vf.FOLD_TITLE} {i['rows']}", i["split_identity_hash"], "no", calls,
                   i["family_budget"]["repeated_speech_audio_seconds_cap"], i["family_budget"]["gpu_hours_fit_inclusive"], plan, notes)

    read = row(
        at[:10], vf.READ_RUN_ID, "model-free-check",
        (f"The offline sealed-pool CONFIRMATION read of {vf.ROUND_LABEL}: render one outputs copy per custodied Solver sample (0..{vf.LAST_SAMPLE}), "
         "score each ONCE with the registered scorer, apply the v4g delivery rule offline, pair per row (best / worst / delivered, the "
         f"oracle best-of-{vf.SAMPLES} as an upper bound, sample 0 against the VER-1c lock column), and apply the FIXED rule "
         f"(n = {vf.RULE_N}, s = {vf.RULE_S}, c3 verdict x N1 >= {vf.RULE_THETA:g}, v4g) together with the VER-1c c3 column on this roster by the recipe "
         f"{pkg}/analysis-recipe-v1.json (offline composer, --verdict-run). Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
        f"slurp {vf.FOLD_TITLE} {vf.ROWS}, the sealed {vf.ROUND_LABEL} flight's sample pool and the sealed VER-1c c3 column (after the seals)",
        ids["arm"]["split_identity_hash"], "no", 0, 0, 0, f"{pkg}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any sample column is "
         f"opened) {at[:10]} at study commit {commit}. Recipe {vf.RECIPE_ID}; output analysis/{vf.READ_RUN_ID}. The rule is applied, not "
         "selected; the confirmation criterion is in the recipe. Its ceiling is descriptive; it admits nothing."),
    )
    lines = [
        vf.LEDGER_MARK + " (owner decision 257, decision 258 option A proposed) -- the arm, its four-row smoke and the READ row (DRAFT, root countersignature pending)",
        "",
        "Four unconsumed flight rows and one READ row registered with the flight. A pool cell: no comparator and no A/A cell. None of "
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
    args = parser.parse_args(argv)
    ids = identities()
    result = write_package(ids, args.study_commit, args.registered_at)
    if not args.no_ledger:
        write_ledger(ledger_rows(ids, args.study_commit, args.registered_at, result["shas"]))
    print(json.dumps({"package": vf.PACKAGE, "files": sorted(result["shas"]),
                      "composed": {k: v["composed_config_hash"] for k, v in ids.items()},
                      "protocol": {k: v["protocol_hash"] for k, v in ids.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
