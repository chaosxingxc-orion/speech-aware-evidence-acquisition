#!/usr/bin/env python3
"""Write the readiness package of NX round R6-P1 (the Perception instruction-template column, TRAIN Fold B) and its DRAFT
exposure-ledger rows, from the derived fragments, the pinned candidate templates and the fit numbers.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer
contact. Flips nothing, mints nothing, countersigns nothing. Re-running replaces the package files and the ledger section in
place (the hashes move at the flip; the flip loop rewrites them).

Writes under ``docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1/``: ``registered-facts-v1.json`` (with the CANONICAL
``stage3_measurement`` block keyed by run id), ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``fit-measure-v1.json`` (ESTIMATE-labelled template tokens), ``root-admission-draft-v1.json``; beside it the preregistration;
and the five DRAFT ledger rows (arm, arm FIT, smoke, smoke FIT, READ). The package README is hand-written.

    python -B scripts/flights/nx/write_slurp_nx_r6_registration.py --study-commit <sha> \\
        --registered-at 2026-10-10T12:00:00.000000+00:00 [--no-ledger | --amend-smoke-ledger]

SMOKE RECOVERY (rec1, 2026-10-10; ``nf.SMOKE_RECOVERY``): the smoke plans, the protocol document and the preregistration carry the
recovery, the smoke plans the run-cumulative budget and the rec1 attempt ids; ``--amend-smoke-ledger`` amends the two smoke ledger rows
in place (calls, audio, plan SHA / attempt / hashes, recovery text) and leaves every other row, including the countersigned arm rows,
byte for byte. Use it (never the full-section rewrite) once the cell's rows are countersigned.

When the cell baseline already carries the minted ``prepared_phase_supply`` pin (after the flip), the registered plans copy it
verbatim (``flight_registration_check`` "registered-supply-binding"); before the flip the plans carry the MINTED_AT_THE_FLIP marker.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nx_r6_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
for _p in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "checks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
SPEC = "docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md"
PROGRAMME = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md"
EXCHANGE = "docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"
GAIN_READ_ID = "SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1"
GAIN_BASELINES = ("n1", "n1+prior", "n1+prior+lock")
NODE_ACCEPT = {"none_recall_min": 0.80, "none_precision_min": 0.75, "parse_rate_min": 0.90}

DECISION_RULE = (
    "SAME-FLIGHT PERCEPTION TEMPLATE COLUMN READ (NX programme round R6-P1; owner decisions 245-248; instrument E1/E2 at the "
    "Perception node; claim ceiling 'nominated'; a MEASUREMENT cell that claims no benefit). One flight, one Perception visit per "
    "row, five arms over the SAME QueryState and evidence: p1 (E= presence tag), p2 (E= tag + up to three M= heard mentions), p3 "
    "(E= tag with an unsure hedge + mentions), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last); "
    "each non-delivering arm is followed by its own first-visit Solver contact (the LOCKED Solver template) over its own note. "
    "THE READS, all from this one flight's sealed columns, model-free (scripts/analysis/nx_r6_read.sh): (1) NODE-LOCAL (reader E2b, "
    "scripts/analysis/slurp_nx_perception_column_read.py, tag grammar configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md, p3 read with "
    "--tag-set p3=none,some,unsure): per arm, on the rank-1 candidate and on the list majority, the parse classes (ok / absent / invalid), "
    "E=none AUC / precision / recall against empty gold, E=some precision / recall against non-empty gold, the unsure rate by gold class, "
    "heard-mention containment (share of gold entities whose normalised surface equals an offered M= surface, per slot type) and option "
    "precision; the paired intent guards against lock (gold on list, rank-1 share, candidate count, prompt tokens, note parse status); "
    "whole-utterance cluster bootstrap CI95, 10,000 draws, seed 20260915. (2) INFORMATION GAIN and the GATE ESTIMATE per candidate arm "
    "(scripts/analysis/slurp_nx_r6_upstream_empty.py --verdict-source perception-arm:<arm> --gain-baseline {n1,n1+prior,n1+prior+lock}): "
    "the cross-fitted AUC increment of the rank-1 E=none verdict over the baseline for 'gold empty' with a whole-utterance cluster "
    "bootstrap CI95 (2,000 draws, seed 20261010), and the delivered-metric estimate of the c3verdict-style gate (verdict E=none AND "
    "N1 >= 0.2, plus the fixed N1 grid) on the lock Solver column of the v4g base (10,000 draws, seed 20260915): pp with CI95, false "
    "fills removed, non-empty exact lost, intent rows moved. (3) LOCKED-CONSUMER read: each arm's own level-2 Solver column against "
    "lock's (the E2 Solver reader inside the node-local pass, and the official pooled SLU-F1 of each column scored once with "
    "slurp-slu-official-train and read paired per row). (4) THE TWIN NULL: aa minus lock on every metric, read first. ACCEPTANCE "
    "(design sections 2.2 and 4, decision 247): NODE-LOCAL acceptance of an arm = rank-1 E=none recall >= 0.80 and precision >= 0.75 on "
    "empty-gold rows, with a rank-1 tag parse rate (ok) >= 0.90 (below that the arm is reported as a FORM FAILURE, not a verdict), and "
    "no intent guard moving by more than the twin's own movement plus 0.65 pp; INFORMATION GAIN = the CI95 lower bound of the "
    "cross-fitted AUC increment over {N1, intent prior} above zero (additional) -- stability (the same sign and CI-LB > 0 on TRAIN "
    "Fold A with the rule fixed on Fold B) is R6-A's term, not this cell's; the delivered-metric estimate is reported through the "
    "measured exchange rates (+0.033 pp per false fill removed, -0.070 pp per non-empty exact row lost), with intent rows moved = 0. "
    "NOTHING IS LOCKED HERE: this is a selection read on the selection roster. PLATEAU RULE: two evaluated Perception-entity rounds "
    "without an arm clearing node-local acceptance close the node; the next lever is then the v2 note contract (decision 248) or the "
    "supply-side presence prior, in that order."
)

ONE_FACTOR = (
    "the Perception instruction template (phase_material.perception.instruction_template) of each non-delivering arm: ONE "
    "hash-pinned path per arm under probes/nx/perception/r6/, nothing else (no supply knob, decoding, response format or tool "
    "authority; the distinction channel of the registered slurp-intent-hypotheses-v1 note is the only free channel); the base, the "
    "Fold B pins, the review-off program and the module block are the instrument's carrier, shared by every arm; each non-delivering "
    "arm's level-2 Solver contact renders the LOCKED Solver template over that arm's own note"
)

PROHIBITIONS = [
    "No test-split, DEV or Fold A contact or read (Fold A confirms only a later R6-A column, under its own registration).",
    "No second factor: one axis (the Perception instruction template), none on aa or lock.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No change of the Perception response format or note schema (slurp-intent-hypotheses-v1 stays; a v2 contract is decision 248's conditional engineering).",
    "No Perception verdict is delivered: the delivering arm is the locked path (invariant I7); the gate estimate is an OFFLINE read, not a wired component.",
    "No paper-scale profile.",
    "No flight before root countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "No arm column is opened before the READ row is root countersigned.",
    "No system-level claim: a column effect may only nominate, and this cell claims no benefit.",
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
        n = nf.names(kind)
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
            "audio_seconds": sum(float(i["audio_seconds"]) for i in json.loads(rd(document["population"]["roster_receipt"]))["items"]),
        }
    return out


def measurement_blocks(ids: dict) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    extra_contacts = nf.CEILING - nf.BASE_CONTACTS
    extra_audio = round(extra_contacts * arm["audio_seconds"], 2)
    basis = (
        "Declared expectation +0.75 pp official pooled SLU-F1 (range +0.75 .. +0.98) = the design's gate estimate "
        f"({nf.DESIGN_NOTE} section 2.2): the c3verdict rule with the verdict source swapped from the Solver-side aggressive arm to the "
        "Perception arm's rank-1 E=none, gated by N1 >= 0.2, on the lock Solver column of the v4g base. It is measured only for the "
        f"Solver-side verdict ({nf.OFFLINE_NOTE} section 4: +0.75 [+0.27, +1.24] on iteration 1 and +0.98 [+0.50, +1.48] on iteration 2, "
        "0 intent rows moved, false fill 91 -> 64 and 93 -> 60, 3 non-empty exact rows lost per flight; recall 0.81-0.83 and precision "
        "0.74-0.76 on empty-gold rows) and is conditional on the Perception verdict matching that quality; if it only mirrors N1 the "
        "gain is about +0.13 pp (the deterministic gate alone). Exchange arithmetic on the iteration-1 point: 27 false fills x 0.033 = "
        "+0.89 and 3 exact rows x -0.070 = -0.21, +0.68 predicted against +0.75 measured. THIS IS A MEASUREMENT CELL under decisions "
        "245/247: it claims NO benefit (claims_benefit false), because +0.75 sits under both the 1.49 pp same-flight floor and the 1.5 "
        "pp registration bar of decision 192; it is judged on its node metric and its information gain, and its delivered-metric "
        "effect is estimated offline from its own sealed columns before any cascade cell is registered."
    )
    return {
        arm["run_id"]: {
            "aa_arm_id": nf.TWIN,
            "ceiling": {
                "pp": nf.EXPECTED_EFFECT_PP, "roster": nf.READ_ROSTER, "rows": 27,
                "what": ("the 27 false fills the N1-gated Solver-side verdict removes on Fold B iteration 1 at 0.033 pp each, less 3 "
                         "non-empty exact rows at 0.070 pp each (+0.68 predicted, +0.75 measured); range +0.75 .. +0.98 pp"),
            },
            "claim": "nominated",
            "claims_benefit": False,
            "conversion_basis": basis,
            "expected_effect_pp": nf.EXPECTED_EFFECT_PP,
            "measurement_design": "same-flight-node-column",
            "note": (
                nf.ROUND_LABEL + " (level: Perception node column, K = 5 Perception template arms, level-2 Solver columns). A "
                "MEASUREMENT cell under decisions 245/247 (design " + nf.DESIGN_NOTE + " section 2.2). " + basis + " Provisional "
                f"floor SLU {nf.FLOOR_SLU_PP} pp (1.49 x sqrt(1080/1080), borrowed from same-flight-supply-variant per the instrument "
                "README until a node-column cell measures its own twin null; the R1 flights have flown but their official-score twin "
                "null is a Solver-node null), so expected_effect_pp 0.75 sits at about 0.5 x the floor, knowingly under it: the "
                "cell looks for a NODE metric and an information gain, not for a delivered effect. The delivered row is the lock arm: "
                "delivered intent and SLU are identical by construction at the request level (invariant I7; reported, never contrasted). "
                "Tuning roster TRAIN Fold A; read roster TRAIN Fold B (a selection read). DISCLOSURE: " + nf.TUNING_DISCLOSURE
            ),
            "primary_metric": (
                "node-local: rank-1 E=none against empty gold on the arm's sealed Perception notes (AUC, precision, recall; reader E2b), "
                "with the cross-fitted AUC increment over {N1, intent prior} (information gain) and the gate estimate of the delivered "
                "SLU-F1 (offline, lock Solver column, v4g base); guards: gold-on-list, rank-1 share, candidate count, prompt tokens, note "
                "parse status and the level-2 Solver column's official intent paired against lock (rows differing <= 7 = 0.65 pp of 1,080)"
            ),
            "primary_metric_key": "slu",
            "provisional_floor_pp": {
                "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp, intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
                "intent_accuracy": nf.FLOOR_INTENT_PP, "slu_f1": nf.FLOOR_SLU_PP,
            },
            "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight",
            "read_roster": nf.READ_ROSTER,
            "rows": nf.ROWS,
            "template_variants": {"node": nf.NODE, "candidate_arms": len(nf.ARMS), "twin": True},
            "tuning_roster": nf.TUNING_ROSTER,
            "variant_cost": {
                "extra_audio_seconds": extra_audio,
                "extra_audio_seconds_per_row_mean": round(arm["audio_seconds"] / arm["rows"] * extra_contacts, 4),
                "extra_contacts_per_row": len(nf.ARM_ORDER) - 1,
                "extra_perception_contacts_per_row": len(nf.ARM_ORDER) - 1,
                "extra_solver_contacts_per_row": len(nf.ARM_ORDER) - 1,
                "note": (
                    f"K - 1 = {len(nf.ARM_ORDER) - 1} non-delivering arms (three candidates and the twin), each one Perception contact "
                    f"AND one level-2 Solver contact at the one Perception visit; every contact re-sends the row's speech packet, so "
                    f"{extra_contacts} x the Fold B total {arm['audio_seconds']} s per flight (review-off base: 2 contacts per row, "
                    f"ceiling {nf.CEILING} = 2 + 2 (K - 1))"
                ),
            },
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "note": (
                f"Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the {nf.PROGRAM} program loads, the five "
                "Perception template arms fan out at the one Perception visit, each non-delivering arm takes its own level-2 Solver "
                "contact, every arm fits its estimated bound, the arm receipt (saea-perception-branch-arms-v4) and I7v seal, and the "
                "episode completes. Scored by no one, read by no one."
            ),
            "primary_metric": "none (structural form only)", "read_roster": nf.READ_ROSTER, "rows": 4, "tuning_roster": "none",
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
        n = nf.names(kind)
        prefix = n["prefix"]
        supply = {
            "note": ("the first Fold B first-phase supply at w_agree 1.0 with the centroid key on this roster; the flip mints it under "
                     "this cell's own run id (item E16); it is expected to equal the NX R1 cells' digest (same knowledge channel)"),
            "relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
        }
        # After the flip the cell baseline carries the minted pin; the registered plan must declare EXACTLY that
        # (scripts/checks/flight_registration_check.py "registered-supply-binding"): copy it verbatim.
        pinned = minted_supply(i["experiment"], i["cell"])
        annotations = None
        if pinned is not None:
            # the placeholder's note moves to the sibling key, exactly as scripts/flights/refresh_registered_plan_pins.py does
            annotations = {"note": supply["note"]}
            supply = pinned
        base = {
            "cell": i["cell"], "composed_config_hash": i["composed_config_hash"],
            "expected_session_id": nf.SESSION, "experiment": i["experiment"], "family_budget": i["family_budget"],
            "one_factor": ONE_FACTOR, "preparation_base_commit": commit,
            "prepared_phase_supply": supply,
            "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": at, "source_tree": nf.SOURCE_TREE,
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
            "unused_budget_is_not_attempt_authority": True,
            **({"prepared_phase_supply_annotations": annotations} if annotations else {}),
        }
        gen_plan = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"],
                        protocol_hash=i["protocol_hash"], run_id=i["run_id"], schema="saea-execution-plan-v1",
                        split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        if kind == "smoke" and nf.SMOKE_RECOVERY:
            gen_plan["recovery"] = nf.SMOKE_RECOVERY
        fit_plan = dict(gen_plan, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"],
                        planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        route_gen = (
            f"Shared core.flight.cli campaign over {nf.CAMPAIGN} (this arm alone; no A/A cell -- the twin arm aa flies inside every "
            "row) through scripts/flights/nx/batch_chain_nx_r6.sh and the batch driver."
            if kind == "arm" else
            "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
        )
        docs[f"{prefix}generation-plan-registered-v1.json"] = {
            **base, "execution_plan": gen_plan, "execution_route": route_gen, "plan_kind": "generation",
            "purpose": f"{i['run_id']}: " + (DECISION_RULE if kind == "arm" else "structural form proof only: no score and no read."),
            "schema": "saea-registered-generation-plan-v1",
            **({"quality_read_gate": (
                f"No arm column is opened before the complete sealed manifest, the ordered outputs, the phase summary and the "
                f"single complete official TRAIN score of the flight exist AND the READ row {nf.READ_RUN_ID} is root "
                "countersigned.")} if kind == "arm" else {}),
        }
        docs[f"{prefix}fit-plan-registered-v1.json"] = {
            **base, "execution_plan": fit_plan, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing.",
        }
    return docs


def smoke_section(ids: dict) -> str:
    """The preregistration's attempt-state section: the smoke recovery (rec1) or, absent one, the first-attempt statement."""

    if nf.SMOKE_RECOVERY:
        original_audio = math.ceil(ids["smoke"]["audio_seconds"] * nf.CEILING - 1e-9)
        calls, audio = nf.smoke_cumulative_budget(nf.SMOKE_ROWS * nf.CEILING, original_audio)
        return (
            f"## Smoke recovery (the cell's single recovery re-registration)\n\n{nf.SMOKE_RECOVERY['reason']}\n\n"
            f"{nf.SMOKE_RECOVERY['amendment']} The smoke plans therefore carry run-cumulative budgets of {calls} model calls / {audio} "
            f"speech-seconds (the failed attempt spent {nf.SMOKE_PREDECESSOR_CONTACTS_SPENT} / "
            f"{nf.SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT:g}; the rec1 attempt is budgeted {nf.SMOKE_ROWS * nf.CEILING} / {original_audio}); the FIT "
            f"endpoint cap is structural, not run-cumulative ({nf.fit_contact_cap(nf.SMOKE_ROWS)} = {nf.SMOKE_ROWS} rows x {nf.CEILING} "
            "contacts x 4 endpoints). The arm's budgets and attempt ids are unchanged: "
            f"arm {nf.ROWS * nf.CEILING:,} model calls, FIT cap {nf.fit_contact_cap(nf.ROWS):,}. At most one recovery re-registration per "
            "cell: a second failure closes the cell.\n\n"
        )
    return (
        "## Attempt state (no recovery)\n\nThe smoke and the arm are FIRST attempts of their run ids. Budgets are single-attempt: smoke "
        f"{nf.SMOKE_ROWS * nf.CEILING} model calls, FIT endpoint cap {nf.fit_contact_cap(nf.SMOKE_ROWS)} (structural: 4 rows x {nf.CEILING} contacts x 4 "
        f"endpoints); arm {nf.ROWS * nf.CEILING:,} model calls, FIT cap {nf.fit_contact_cap(nf.ROWS):,}. A recovery re-registration, if one is ever needed, "
        "must re-derive the run-cumulative generation budget (earlier attempts' spend plus the new attempt's worst case) and keep the FIT "
        "cap structural. At most one recovery re-registration per cell.\n\n"
    )


def write_package(ids: dict, commit: str, at: str) -> dict:
    pkg = nf.PACKAGE
    pins = nf.candidate_pins()
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
        "one_factor": ONE_FACTOR, "prohibitions": PROHIBITIONS,
        **({"recovery": {"smoke": nf.SMOKE_RECOVERY}} if nf.SMOKE_RECOVERY else {}),
        "protocol_id": f"slurp-{nf.SLUG}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1",
        "source_tree": nf.SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "study_commit_at_registration": commit,
        "the_question": (
            "At the one Perception visit of every TRAIN Fold B row of the review-off COMP-1b module graph on lock v2.2, can the Perception "
            "node judge from the speech whether an entity value was expressed (the E= tag) and offer the spoken words of each mention "
            "(the M= options) in its note's distinction channel, with a rank-1 E=none verdict whose recall and precision on empty-gold "
            "rows reach the node-local acceptance and whose cross-fitted AUC increment over {N1, intent prior} has a CI95 lower bound "
            "above zero, without moving the intent guards beyond the in-flight twin's null? (Measurement cell: no benefit is claimed.)"
        ),
    }
    protocol_sha = wjson(f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(ids, commit, at, protocol_sha, pkg)
    shas = {name: wjson(f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    shas["fit-measure-v1.json"] = wr(f"{pkg}/fit-measure-v1.json", nf.fit_measure_json())
    recipe = {
        "acceptance": {
            "node_local": {
                "verdict": "rank-1 candidate E=none against empty gold (reader E2b)",
                **NODE_ACCEPT,
                "form_failure": "an arm whose rank-1 tag parse rate (ok) is below parse_rate_min is a FORM FAILURE, not a verdict",
                "intent_guard": "a guard moving by more than the twin's own movement plus 0.65 pp fails the arm",
            },
            "information_gain": {
                "rule": "CI95 lower bound of the cross-fitted AUC increment of the rank-1 verdict over the baseline for 'gold empty' > 0",
                "baselines": list(GAIN_BASELINES),
                "bootstrap": {"unit": "whole utterance", "draws": 2000, "seed": 20261010},
                "stability": "the same sign and CI-LB > 0 on TRAIN Fold A with the rule fixed on Fold B: R6-A's term, not this cell's",
            },
            "delivered_estimate": {
                "rule": "empty the lock Solver row where the rank-1 verdict is E=none AND N1 >= 0.2 (and the fixed N1 grid), v4g base",
                "bootstrap": {"unit": "whole utterance", "draws": 10000, "seed": 20260915},
                "exchange_rates_pp_per_row": {"false_fill_removed": 0.033, "nonempty_exact_lost": -0.070},
                "intent_rows_moved_must_be": 0,
            },
            "plateau": "two evaluated Perception-entity rounds without an arm clearing node-local acceptance close the node",
        },
        "arms": {
            "arm": {"attempt_id": arm["attempt_id"], "role": "the sealed flight: every arm below is a column of it",
                    "run_id": arm["run_id"]},
            "columns": {
                **{a: {"role": "candidate Perception instruction template (hash-pinned)", **pins[a]} for a in nf.ARMS},
                nf.TWIN: {"role": "the in-flight twin: replicate_of lock, the null of every contrast"},
                nf.DELIVERING: {"role": "the delivering arm: LEFT of every contrast (the locked template, untemplated)",
                                "relpath": nf.LOCKED_TEMPLATE, "sha256": nf.LOCKED_TEMPLATE_SHA},
            },
        },
        "boundary": ("A development read on a TRAIN fold (owner decisions 28 and 86); node-local, never a system-level claim. No "
                     "utterance text, transcript, gold value, note body, mention text or model output is printed or persisted."),
        "decision_rule": DECISION_RULE,
        "information_gain": {
            "driver": "scripts/analysis/slurp_nx_r6_upstream_empty.py",
            "verdict_source": "perception-arm:<arm>",
            "baselines": list(GAIN_BASELINES),
            "output": f"analysis/{GAIN_READ_ID}/<arm>/<baseline>",
        },
        "node_local": {
            "driver": "scripts/analysis/slurp_nx_perception_column_read.py",
            "report_schema": "saea-nx-perception-column-read-v1",
            "tag_grammar": {"relpath": nf.TAG_GRAMMAR, "sha256": sha_file(nf.TAG_GRAMMAR)},
            "bootstrap": {"cluster": "whole utterance", "draws": 10000, "seed": 20260915},
            "output": "analysis/" + nf.READ_RUN_ID + "/node-local",
        },
        "official_columns": {
            "scorer": nf.SCORER, "scoring_jobs": len(nf.ARM_ORDER),
            "render": "scripts/analysis/stage3_rollout_score.py --mode perception-branches",
            "paired_driver": "scripts/analysis/stage3_paired_read.py (column arms; --cluster-key sample_id)",
            "status": ("UNEXERCISED on a v4 Perception template run (instrument README section 7 item 7); the read driver runs it last "
                       "and it never gates the node-local acceptance"),
            "bootstrap": {"cluster_key": "sample_id", "draws": 10000, "seed": 20260915,
                          "unit": "row (paired); the whole-utterance numbers are the node-local and information-gain reads' own"},
            "passes": {
                **{f"{a}-vs-lock": {"left": nf.DELIVERING, "right": a, "gating": False} for a in nf.ARMS},
                "aa-vs-lock": {"left": nf.DELIVERING, "right": nf.TWIN, "gating": "sets the bar"},
            },
            "output": "analysis/" + nf.READ_RUN_ID + "/<pass>",
        },
        "output": {"analysis_root": "analysis/" + nf.READ_RUN_ID},
        "read_driver": "scripts/analysis/nx_r6_read.sh",
        "read_run_id": nf.READ_RUN_ID,
        "recipe_id": nf.RECIPE_ID,
        "registered_at_utc": at,
        "resampling": {"bootstrap_draws": 10000, "seed": 20260915},
        "run_ids": {"arm": arm["run_id"], "read": nf.READ_RUN_ID},
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "steps": [
            f"0. Refuse unless the READ row {nf.READ_RUN_ID} is root countersigned.",
            "1. Refuse unless the flight carries a COMPLETE sealed 1,080-row manifest with the saea-perception-branch-arms-v4 receipt on every row, verified by the bundle (invariant I7v).",
            "2. Node-local (E2b): per arm the tag parse classes, the rank-1 and list-majority presence verdict metrics, the heard-mention containment and option precision, the paired intent guards against lock and the level-2 Solver column's exact-set read (tag sets: p3 admits unsure).",
            "3. Information gain and the gate estimate per candidate arm and per baseline (n1, n1+prior, n1+prior+lock), 0 GPU.",
            "4. Twin null (aa vs lock) first, then each candidate vs lock under the acceptance block; per-scenario tables from the official columns when they exist.",
            "5. Official: render each arm's level-2 first-visit Solver answer through the delivered row's normaliser and projection and score it ONCE with slurp-slu-official-train (five jobs, never sharded).",
        ],
        "tag_sets": {a: list(v) for a, v in nf.TAG_SETS.items()},
        "title": "Cell " + nf.CELL_LABEL + " -- the same-flight Perception instruction-template column read: three candidates and the twin, each against the delivering lock arm",
    }
    shas["analysis-recipe-v1.json"] = wjson(f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "budget_arithmetic": {
            "arm_family_budget": arm["family_budget"], "smoke_family_budget": smoke["family_budget"],
            "note": (f"review-off graph: perception 1 + solver 1 + 2 (K - 1) = {nf.CEILING} contacts per row (K = 5 arms); generation rows x "
                     f"{nf.CEILING} = {nf.ROWS * nf.CEILING:,}, FIT rows x {nf.CEILING} x 4 = {nf.fit_contact_cap(nf.ROWS):,}, speech "
                     f"ceil(audio x {nf.CEILING}), planned GPU hours {nf.PLANNED_GPU_HOURS_ARM} (arm; {nf.ROWS * nf.CEILING:,} contacts at the "
                     "measured 44 requests per minute on np4) and 1.0 (smoke); native task-contract calls = every contact; run-cumulative"),
        },
        "candidates": {a: {"author": "hand (Fable 5.1 from aggregate tables)", **pins[a],
                           "template_tokens_ESTIMATE": nf.template_tokens()[a], "words": nf.word_count(nf.CANDIDATE_PATHS[a]),
                           "tag_set": list(nf.TAG_SETS[a])} for a in nf.ARMS},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "decision_rule": DECISION_RULE,
        "delivering_template": {"relpath": nf.LOCKED_TEMPLATE, "sha256": nf.LOCKED_TEMPLATE_SHA,
                                "template_tokens_ESTIMATE": nf.template_tokens()[nf.DELIVERING]},
        "fit": {"status": "PENDING_CHECK"},
        "fit_measure": {"relpath": f"{pkg}/fit-measure-v1.json", "sha256": shas["fit-measure-v1.json"],
                        "status": "ESTIMATE: template tokens are word-count estimates (TODO: the registered tokenizer pass, see the README)",
                        "summary": {k: nf.fit_measure()[k] for k in ("template_tokens", "template_frame", "arm_prompt_estimates",
                                                                     "prompt_limit_tokens")}},
        "identity": ids,
        "owner_decisions": {
            "139": "no prior: the expectation is declared from measured numbers (the offline R6 note)",
            "192": "the declared effect is on file BEFORE flight (a measurement cell: claims_benefit false)",
            "239": "move the empty-entity decision to the PRECEDING node and adjust the knowledge supply if useful",
            "245": "node-local first, then the cascade; information gain is the object",
            "246-248": "R6-P1 flies after the R5 read; the information-gain acceptance rule; the v2 note contract only on its trigger",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "prohibitions": PROHIBITIONS,
        "registered_at_utc": at,
        "registration_basis": (f"engineering brief 2026-10-10: register {nf.ROUND_LABEL} from {nf.DESIGN_NOTE} (sections 2.2, 4, 6) and "
                               f"{nf.CANDIDATES_README}. HELD: the owner / root admission is still required; nothing here authorises a flip or a flight."),
        "rows": nf.ROWS,
        "schema": "saea-registered-facts-v1",
        "stage3_measurement": blocks,
        "study_commit_at_registration": commit,
        "the_cell": {
            "base": "the COMP-1b composition (agree-vote-seed + centroid-boundary-key) as a consumption-module block on lock v2.2 (v4g at delivery), review loop OFF",
            "program": nf.PROGRAM, "ceiling": nf.CEILING,
            "template_variants": json.loads(rd(f"configs/baseline/{arm['baseline_fragment']}.json"))[
                "native_episode"]["roles"][nf.NODE]["template_variants"],
        },
        "tuning_disclosure": nf.TUNING_DISCLOSURE,
    }
    shas["registered-facts-v1.json"] = wjson(f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for root to mint on the data root with scripts/flights/nx/nx_r6_mint_receipt.py (status decided, "
                        "recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'."),
        "antecedents": {
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "candidates_readme": {"path": nf.CANDIDATES_README, "sha256": sha_file(nf.CANDIDATES_README)},
            "derive_script": {"path": "scripts/flights/nx/derive_slurp_nx_r6_cells.py", "sha256": sha_file("scripts/flights/nx/derive_slurp_nx_r6_cells.py")},
            "design_note": {"path": nf.DESIGN_NOTE, "sha256": sha_file(nf.DESIGN_NOTE)},
            "instrument_readme": {"path": nf.INSTRUMENT_README, "sha256": sha_file(nf.INSTRUMENT_README)},
            "offline_note": {"path": nf.OFFLINE_NOTE, "sha256": sha_file(nf.OFFLINE_NOTE)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": nf.PREREG, "sha256": None},
            "programme": {"path": PROGRAMME, "sha256": sha_file(PROGRAMME)},
            "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None},
            "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit,
            "tag_grammar": {"path": nf.TAG_GRAMMAR, "sha256": sha_file(nf.TAG_GRAMMAR)},
        },
        "authorization_basis": ("Owner decisions 245-248 (2026-10-10), 239, 139, 192, 28/86; the node-template instrument "
                                f"({SPEC}) and its Perception form ({nf.INSTRUMENT_README}); {nf.DESIGN_NOTE}."),
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "smoke": smoke["family_budget"]},
        "cell_kind": ("Stage-3 same-flight NODE-TEMPLATE column cell at the PERCEPTION node (NX instrument E1, level-2 Solver columns, label none), "
                      "claim ceiling 'nominated', a MEASUREMENT cell (claims_benefit false). One arm on TRAIN Fold B 1,080 with five "
                      "Perception template arms (three candidates, aa twin, lock delivering), and a four-row form smoke."),
        "claim_boundary": ("No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a "
                           "node column read on a development fold whose ceiling is 'nominated'."),
        "coordinator": "Fable5.1",
        "decision": (f"Fly cell {nf.CELL_LABEL}: the COMP-1b module composition on lock v2.2 with the Reviewer loop off on TRAIN Fold B under "
                     f"{nf.PROGRAM} with a Perception template column; read p1, p2, p3 and aa against lock in the same flight; judge "
                     "the node metric and the information gain at the twin bar."),
        "decision_id": nf.DECISION_ID,
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cells are flipped and the receipt is minted",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change beyond the registered module block, Fold B re-target and template column",
            "delivering a Perception verdict (the gate estimate is an offline read)",
            "opening an arm column before the READ row is countersigned",
        ],
        "owner": "root",
        "population": {"count": nf.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": arm["split_identity_hash"],
                       "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None,
        "registered_hashes": {k: {"composed_config": v["composed_config_hash"], "protocol": v["protocol_hash"]} for k, v in ids.items()},
        "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": nf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True,
                    "slot_tokens": 24576, "slots": 4},
        "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(f"{pkg}/root-admission-draft-v1.json", draft)
    prereg = (
        f"# Cell {nf.CELL_LABEL} (node-extreme programme {nf.ROUND_LABEL.replace('NX ', '')}, Perception template column): preregistration\n\n"
        f"Registered {at[:10]} at study commit `{commit}`, before any contact, by script (decision 58) from the P-SV-4 Fold B fragments "
        f"and the consumption-module compiler under the NX programme (owner decisions 245-248). Development numbers only.\n\n"
        "| item | value |\n| --- | --- |\n"
        "| base | the COMP-1b composition as a module block on lock v2.2 (agree-vote-seed + centroid-boundary-key ON; v4g at delivery), Reviewer loop OFF, no tool schema on any role |\n"
        f"| program | `{nf.PROGRAM}` (ceiling {nf.CEILING} = 2 + 2 x (5 - 1)) |\n"
        f"| arms | `p1`, `p2`, `p3` (candidates, pinned under `{nf.CANDIDATES_DIR}/`), `aa` (twin of `lock`), `lock` (delivering, `{nf.LOCKED_TEMPLATE}`) |\n"
        "| design / claim | `same-flight-node-column` / `nominated`; a MEASUREMENT cell, `claims_benefit` false |\n"
        "| primary | node-local: rank-1 E=none against empty gold (AUC, precision, recall) and the information gain over {N1, intent prior}; guards: the paired Perception note metrics and the level-2 Solver column |\n"
        f"| expected effect | {nf.EXPECTED_EFFECT_PP} pp (the design's gate estimate, range {nf.EXPECTED_EFFECT_RANGE_PP[0]} .. {nf.EXPECTED_EFFECT_RANGE_PP[1]}), `claims_benefit` false; provisional floor SLU {nf.FLOOR_SLU_PP} pp |\n"
        f"| rosters | tuning `{nf.TUNING_ROSTER}`; read `{nf.READ_ROSTER}` (selection read; see the disclosure) |\n"
        f"| runs | `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{nf.READ_RUN_ID}` |\n"
        f"| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |\n"
        f"| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |\n"
        f"| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |\n\n"
        + smoke_section(ids) +
        f"## Decision rule (fixed here)\n\n{DECISION_RULE}\n\n## Tuning disclosure\n\n{nf.TUNING_DISCLOSURE}\n\n"
        "## The measurement declaration\n\n```json\n"
        + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    shas["__prereg__"] = wr(nf.PREREG, prereg)
    return {"shas": shas, "blocks": blocks, "protocol_sha": protocol_sha}


RECOVERY_MARK = " RECOVERY RE-REGISTRATION (root-diagnosed, the cell's single one, "


def recovery_ledger_text(ids: dict, fit: bool) -> str:
    """The recovery wording appended to a smoke row's notes (the R1 wording: the original row stays, the text names the failed
    attempt and the rec1 ids)."""

    smoke, rec = ids["smoke"], nf.SMOKE_RECOVERY
    original_audio = math.ceil(smoke["audio_seconds"] * nf.CEILING - 1e-9)
    calls, audio = nf.smoke_cumulative_budget(nf.SMOKE_ROWS * nf.CEILING, original_audio)
    what = "FIT attempt" if fit else "attempt"
    predecessor = rec["predecessor_fit_attempt_id"] if fit else rec["predecessor_attempt_id"]
    state = ("OPENED; request envelopes only, no model contact; preserved" if fit else
             f"OPENED, {nf.SMOKE_PREDECESSOR_CONTACTS_SPENT} contacts / {nf.SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT:g} speech-seconds spent "
             "(4 rows x 5 Perception arms), stopped 2026-10-10T08:11:08Z at flight commit 58c546b54 on SlurpIntentHypothesisError "
             "('hypothesis content does not match its source response SHA-256') in the first level-2 Solver input; the failed attempt is "
             "preserved unread")
    return (
        RECOVERY_MARK.lstrip(" ") + "2026-10-10): " + f"{what} {predecessor} {state}. Root cause: the level-2 branch view in "
        "rails/runner.py swapped the Perception state's content for the branch's note without rebinding source_response_sha256; fixed by "
        "the level-2 note source-hash binding fix (rails/runner.py; commit named at merge). The smoke is re-flown whole under the rec1 "
        f"attempt ids (generation {smoke['attempt_id']}; FIT {smoke['fit_attempt_id']}), a (run_id, attempt_id) pair being a one-time key; "
        f"the plan budget is run-cumulative across the attempts of the run id: the original plan plus the failed attempt's realised "
        f"spend, {nf.SMOKE_ROWS * nf.CEILING} + {nf.SMOKE_PREDECESSOR_CONTACTS_SPENT} = {calls} calls and ceil({original_audio} + "
        f"{nf.SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT:g}) = {audio} speech-seconds; the FIT cap stays structural "
        f"({nf.fit_contact_cap(nf.SMOKE_ROWS)} = {nf.SMOKE_ROWS} rows x {nf.CEILING} contacts x 4 endpoints, not scaled); the arm is "
        "untouched. A second failure closes the cell."
    )


def amend_smoke_ledger_rows(ids: dict, shas: dict) -> list[str]:
    """Amend the two smoke rows IN PLACE (the R1 way): the original rows and their countersignature text stay; the calls and audio
    columns, the plan SHA256 / attempt / protocol hash / composed config of the notes move to the rec1 registration and the
    recovery text is appended. Idempotent. Returns the amended run ids."""

    smoke = ids["smoke"]
    lines = rd(LEDGER).split("\n")
    amended = []
    for fit in (False, True):
        run_id = smoke["fit_run_id"] if fit else smoke["run_id"]
        hits = [k for k, line in enumerate(lines) if line.startswith("| ") and f" | {run_id} | " in line]
        if len(hits) != 1:
            raise SystemExit(f"ledger: {len(hits)} rows for {run_id}, expected exactly one")
        cells = lines[hits[0]][2:-2].split(" | ")
        if len(cells) != 15:
            raise SystemExit(f"ledger: row {run_id} has {len(cells)} cells, expected 15")
        plan_name = f"smoke-{'fit' if fit else 'generation'}-plan-registered-v1.json"
        calls = smoke["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
        cells[9], cells[10] = str(calls), str(smoke["family_budget"]["repeated_speech_audio_seconds_cap"])
        notes = cells[14].split(RECOVERY_MARK)[0].rstrip()
        pattern = (r"Plan SHA256 [0-9a-f]{64}; attempt [\w-]+\. Protocol hash [0-9a-f]{64}; composed config [0-9a-f]{64};")
        if len(re.findall(pattern, notes)) != 1:
            raise SystemExit(f"ledger: row {run_id} notes carry no unique plan/attempt/hash stanza to amend")
        attempt = smoke["fit_attempt_id"] if fit else smoke["attempt_id"]
        stanza = (f"Plan SHA256 {shas[plan_name]}; attempt {attempt}. Protocol hash {smoke['protocol_hash']}; "
                  f"composed config {smoke['composed_config_hash']};")
        notes = re.sub(pattern, lambda _m: stanza, notes)
        cells[14] = notes + " " + recovery_ledger_text(ids, fit)
        lines[hits[0]] = "| " + " | ".join(cells) + " |"
        amended.append(run_id)
    io.open(REPO_ROOT / LEDGER, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return amended


def ledger_rows(ids: dict, commit: str, at: str, shas: dict) -> str:
    pkg = nf.PACKAGE
    arm, smoke = ids["arm"], ids["smoke"]
    scope = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any role; "
             "the COMP-1b module composition on lock v2.2 with the Reviewer loop off; Perception instruction-template column of five arms "
             "(three hand-written candidates, the aa twin, the locked delivering lock arm) at the one Perception visit, each non-delivering "
             "arm followed by its own level-2 Solver contact under the locked Solver template")
    inherited = ("TRAIN Fold B discovery rows already exposed by SAEA-SLURP-EVO-FOLD-PACKETS-V2, SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2, the EVO-S1 "
                 "confirmation fold SAEA-SLURP-EVO-S1-FOLD-B-V2 (8,640 contacts, 2026-09-06), the encoder pass "
                 "SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1, the model-free W2 offline guard read against Fold B gold, the P-SV-1..P-SV-4 "
                 "Fold B cells registered on these rows, the NX R1 Solver template columns (iterations 1 and 2) on these rows and the "
                 "model-free R6 offline read (SAEA-SLURP-NX-R6-UPSTREAM-EMPTY-OFFLINE-V1) against Fold B gold; this cell opens no split. "
                 "Prior exposure is inherited in full.")
    note_common = (
        f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {at[:10]} at study commit {commit} by the {nf.ROUND_LABEL} "
        f"engineering agent (worktree {nf.WORKTREE}, branch {nf.BRANCH}); NX programme owner decisions 245-248. "
        "HELD: this registration performs no contact and authorises none. READINESS HELD: root countersigns the five DRAFT rows, mints "
        f"{nf.DECISION_RELPATH} (decision id {nf.DECISION_ID}) from the package's root-admission-draft-v1.json with scripts/flights/nx/nx_r6_mint_receipt.py "
        "(four eligible run ids), then scripts/flights/nx/nx_r6_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each "
        "cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
        f"Measurement declaration: same-flight-node-column, expected_effect_pp {nf.EXPECTED_EFFECT_PP}, claims_benefit false (a measurement cell), "
        "primary_metric_key slu, floor SLU 1.49 / intent 0.65 (provisional, borrowed), claim nominated, aa twin. "
        f"Read: {nf.READ_RUN_ID} by scripts/analysis/nx_r6_read.sh. template_tokens are an ESTIMATE (word counts) until the registered tokenizer "
        "pass lands (package README). Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. No "
        "paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
    )

    def row(date, rid, profile, what, model, carrier, split, consumed, calls, audio, gpu, artifacts, notes):
        cells = [date, rid, profile, what, model, carrier, "discovery", split, consumed, str(calls), str(audio), str(gpu), inherited, artifacts, notes]
        return "| " + " | ".join(cells) + " |"

    def plan_row(kind, fit):
        i = ids[kind]
        n = nf.names(kind)
        prefix = n["prefix"]
        what = (nf.ROUND_LABEL + ": the Perception instruction-template column on TRAIN Fold B" if kind == "arm" else
                "Four-row form smoke of " + nf.ROUND_LABEL)
        if fit:
            what += " -- FIT spend identity, request envelopes only, no generation"
        plan = f"{pkg}/{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"
        calls = i["family_budget"]["fit_endpoint_calls_cap"] if fit else i["family_budget"]["generation_calls_cap"]
        plan_sha = shas[f"{prefix}{'fit' if fit else 'generation'}-plan-registered-v1.json"]
        attempt = i["fit_attempt_id"] if fit else i["attempt_id"]
        notes = (note_common.replace("Measurement declaration: same-flight-node-column",
                                     "Measurement declaration: " + ("same-flight-node-column" if kind == "arm" else "form-proof"))
                 + f" Plan SHA256 {plan_sha}; attempt {attempt}. Protocol hash {i['protocol_hash']}; composed config {i['composed_config_hash']}; expected session {nf.SESSION} (attach only).")
        if kind == "smoke" and nf.SMOKE_RECOVERY:
            notes += " " + recovery_ledger_text(ids, fit)
        return row(at, i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], what, scope,
                   f"slurp TRAIN Fold B {i['rows']}", i["split_identity_hash"], "no", calls,
                   i["family_budget"]["repeated_speech_audio_seconds_cap"], i["family_budget"]["gpu_hours_fit_inclusive"], plan, notes)

    read = row(
        at[:10], nf.READ_RUN_ID, "model-free-check",
        (f"The same-flight Perception template-column read of {nf.ROUND_LABEL}: per arm (p1, p2, p3, aa; lock the delivering reference) the "
         "node-local E2b read (tag parse classes, rank-1 and list-majority presence verdict metrics, heard-mention containment and option "
         "precision, the paired intent guards, the level-2 Solver column), the information gain and the gate estimate of each candidate's "
         "rank-1 E=none verdict over the N1 / intent-prior / lock baselines, and the official pooled SLU-F1 of each arm's level-2 Solver column "
         "scored ONCE with slurp-slu-official-train with paired bootstraps against lock and the aa twin as the bar; by the recipe "
         f"{pkg}/analysis-recipe-v1.json through scripts/analysis/nx_r6_read.sh. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and five official column scorings",
        f"slurp TRAIN Fold B {nf.ROWS}, the sealed {nf.ROUND_LABEL} flight's Perception template columns (after the seal)",
        ids["arm"]["split_identity_hash"], "no", 0, 0, 0, f"{pkg}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any arm column is opened) "
         f"{at[:10]} at study commit {commit}. Recipe {nf.RECIPE_ID}; output analysis/{nf.READ_RUN_ID}. One READ row covers the candidate "
         "contrasts, the twin null, the information-gain reads and the official columns. Its ceiling is a nomination; it admits nothing."),
    )
    lines = [
        nf.LEDGER_MARK + " (owner decisions 245-248) -- the arm, its four-row smoke and the READ row (DRAFT, root countersignature pending)",
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
    """Replace this cell's section (its heading up to the next ``## `` heading, or the end); append when absent."""

    current = rd(LEDGER)
    tail = ""
    if nf.LEDGER_MARK in current:
        start = current.index(nf.LEDGER_MARK)
        following = current.find("\n## ", start + len(nf.LEDGER_MARK))
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
    parser.add_argument("--amend-smoke-ledger", action="store_true",
                        help="amend ONLY the two smoke ledger rows in place (the smoke recovery, rec1); the countersigned rows of "
                             "the arm and the READ row stay as they are. Implies --no-ledger for the section rewrite.")
    args = parser.parse_args(argv)
    ids = identities()
    result = write_package(ids, args.study_commit, args.registered_at)
    amended: list[str] = []
    if args.amend_smoke_ledger:
        if not nf.SMOKE_RECOVERY:
            raise SystemExit("--amend-smoke-ledger needs nf.SMOKE_RECOVERY")
        amended = amend_smoke_ledger_rows(ids, result["shas"])
    elif not args.no_ledger:
        write_ledger(ledger_rows(ids, args.study_commit, args.registered_at, result["shas"]))
    print(json.dumps({"package": nf.PACKAGE, "files": sorted(result["shas"]), "amended_ledger_rows": amended,
                      "composed": {k: v["composed_config_hash"] for k, v in ids.items()},
                      "protocol": {k: v["protocol_hash"] for k, v in ids.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
