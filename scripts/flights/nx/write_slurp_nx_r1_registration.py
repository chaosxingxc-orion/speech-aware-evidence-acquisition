#!/usr/bin/env python3
"""Write the readiness package of NX round R1 (the Solver instruction-template column, TRAIN Fold B) and its DRAFT
exposure-ledger rows, from the derived fragments, the measured fit numbers and the pinned candidate templates.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer
contact. Flips nothing, mints nothing, countersigns nothing. Re-running replaces the package files and the ledger
section in place (the hashes move at the flip; the flip loop rewrites them).

Writes under ``docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/``: ``registered-facts-v1.json`` (with the
CANONICAL ``stage3_measurement`` block keyed by run id), ``protocol-registered-v1.json``, the four plan files,
``analysis-recipe-v1.json``, ``root-admission-draft-v1.json``; beside it the preregistration; and the five DRAFT
ledger rows (arm, arm FIT, smoke, smoke FIT, READ). The README is hand-written.

    python -B scripts/flights/nx/write_slurp_nx_r1_registration.py --study-commit <sha> \\
        --registered-at 2026-10-09T12:00:00.000000+00:00 [--iteration 1|2] [--no-ledger]

``--iteration 2`` writes the iteration-2 package (nx_r1_family.configure): its own candidates r1-i2-c1 .. r1-i2-c5, no smoke
recovery, the cross-iteration descriptive contrast in the recipe and its own ledger section. The iteration-1 ledger rows are
never touched: a section is replaced only between its own heading and the next ``## `` heading.
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

import nx_r1_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
for _p in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "checks"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
SPEC = "docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md"
PROGRAMME = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md"
EXCHANGE = "docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md"
PSV3_READ = "docs/results/2026-09-30-slurp-psv3-fold-b-branch-read.md"
V4_READ = "docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md"
V4_ATTR = "docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"

_DECISION_RULE_BASE = (
    "SAME-FLIGHT NODE-TEMPLATE COLUMN READ (NX programme C0.2/C2 R1; instrument E1/E2; claim ceiling 'nominated'). One "
    "flight, one Solver visit per row, seven arms over the SAME QueryState and evidence: r1-c1 .. r1-c5 (hand-written "
    "candidates), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last). Each arm's RAW "
    "first answer is read through the E2 reader (scripts/analysis/slurp_nx_solver_column_read.py): node-local primary = "
    "raw first-answer entity exact-set per row, paired per row against lock, with the whole-utterance cluster bootstrap "
    "CI95 (10,000 draws, seed 20260915) and the paired Wilson share of the discordant rows; secondaries parse_valid, "
    "empty_gold_false_fill, nonempty_exact and per-slot-type counts. Each arm's column is also rendered through the "
    "delivered row's normaliser and projection and scored ONCE with slurp-slu-official-train (never sharded); official "
    "contrasts are paired ROW bootstraps (cluster key sample_id, the stage3_paired_read constraint for column arms, "
    "10,000 draws, seed 20260915), the whole-utterance number beside. (1) THE TWIN NULL: aa minus lock on every metric; "
    "the bar = |aa - lock offset| + its CI95 half-width, reported beside the design's provisional floor (SLU-F1 1.49 pp, "
    "intent 0.65 pp at n = 1,080; borrowed from same-flight-supply-variant until this cell measures its own null). "
    "(2) THE CONTRAST per candidate X: NOMINATED iff (a) the node-local exact-set CI95 lower bound > 0, AND (b) no "
    "secondary loss (parse_valid or nonempty_exact lower, or empty_gold_false_fill higher, with a CI95 excluding zero), "
    "AND (c) the intent guard holds: rows whose official intent correctness differs from lock <= 7 (0.65 pp of 1,080) "
    "or the official intent delta CI95 contains zero, AND (d) the official pooled SLU-F1 point delta exceeds the twin's "
    "SLU bar. HARM iff (a') the exact-set CI95 upper bound < 0. Among several NOMINATED arms the best node-local point "
    "estimate wins (ties: fewer words). PLATEAU RULE (programme C0.4): two evaluated rounds without a NOMINATED arm lock "
    "the delivering template and close the node. A nomination is confirmed once on TRAIN Fold A as a two-arm column "
    "before any lock; it admits nothing by itself. The delivering lock arm's own offline post-processing columns v4 and "
    "v4g are read beside (analysis recipe, offline_columns)."
)

def norm_text(iteration1_text: str, iteration2_text: str) -> str:
    """Iteration 1 keeps its registered (flown) wording byte for byte; iteration 2 declares the node-local primary as
    ``exact_set_normalised`` (the exact-set of the answer AFTER the cell's own delivery normaliser), the raw exact-set being
    a diagnostic. Why: iteration 1's r1-c5 read +2.50 raw yet -0.15 on the official column -- formatting the delivery
    normaliser already repairs (E2 reader schema v2)."""
    return iteration2_text if nf.ITERATION >= 2 else iteration1_text


ITER2_OFFICIAL_RULE = (
    "SAME-FLIGHT NODE-TEMPLATE COLUMN READ (NX programme C0.2/C2 R1 iteration 2; instrument E1/E2; claim ceiling 'nominated'). "
    "One flight, one Solver visit per row, seven arms over the SAME QueryState and evidence: r1-i2-c1 .. r1-i2-c5 "
    "(hand-written candidates), aa (the twin, replicate_of lock) and lock (the locked template, delivering, last). "
    "NOMINATION IS DECIDED ON THE OFFICIAL COLUMN. Each arm's first-visit Solver answer is rendered through the delivered "
    "row's normaliser and projection and scored ONCE with slurp-slu-official-train (never sharded); every contrast is the "
    "paired ROW bootstrap of that arm's column against the delivering lock arm (cluster key sample_id, 10,000 draws, seed "
    "20260915; scripts/analysis/stage3_rollout_score.py then stage3_paired_read.py), all read within this one flight. "
    "NOMINATION RULE: candidate X is NOMINATED iff (a) the official pooled SLU-F1 delta X minus lock has a CI95 lower bound "
    "> 0, AND (b) that delta is above the aa twin's official pooled SLU-F1 delta (aa minus lock, same flight), AND (c) the "
    "intent guard holds: rows whose official intent correctness differs from lock <= 7 (the floor 0.65 pp of 1,080). "
    "HARM iff the official pooled SLU-F1 delta CI95 upper bound < 0. The twin null (aa minus lock) is read first and "
    "reported beside the design's provisional floor (SLU-F1 1.49 pp, intent 0.65 pp at n = 1,080; borrowed from "
    "same-flight-supply-variant until this cell measures its own null). Among several NOMINATED arms the largest official "
    "SLU-F1 delta wins (ties: fewer words). THE NODE-LOCAL READ IS DIAGNOSTIC AND GATES NOTHING: the E2 reader (schema v2; "
    "scripts/analysis/slurp_nx_solver_column_read.py) reports exact_set_normalised (the entity exact-set per row of the "
    "answer after the delivered row's own normaliser), parse_valid, empty_gold_false_fill, nonempty_exact, per-slot-type "
    "counts and the raw-vs-normalised flip table, paired per row against lock, to localise where an official delta comes "
    "from; a node-local gain without an official gain is not a nomination, and a nomination needs no node-local screen. "
    "(Why: in iteration 1 the node-local screen and the official column disagreed: normalised node-local c5 +1.30 [-0.19, "
    "+2.78] vs official -0.15 [-1.23, +0.89]; c3 +4.63 [+2.87, +6.39] vs official +0.96 [-0.16, +2.09].) PLATEAU RULE "
    "(programme C0.4): two evaluated rounds without a NOMINATED arm lock the delivering template and close the node. A "
    "nomination is confirmed once on TRAIN Fold A as a two-arm column before any lock; it admits nothing by itself. The "
    "delivering lock arm's own offline post-processing columns v4 and v4g are read beside (analysis recipe, offline_columns)."
)

ITER2_RULE_TAIL = (
    " THIS IS THE SECOND AND LAST EVALUATED ROUND of R1 under the plateau rule: if no arm is NOMINATED here the delivering "
    "template is locked and the node closes. The iteration-1 arm r1-c5 does NOT fly in this column; each iteration-2 arm is "
    "also set beside iteration-1 r1-c5 in a cross-iteration table that is DESCRIPTIVE only (different flights, different "
    "offsets: no claim, no nomination, no input to the rule above). Iteration 1's registered rule and verdict stand as written."
)


NOMINATION_BLOCK = {
    "rule": "official-column",
    "metric": "official pooled SLU-F1 (slurp-slu-official-train) of the arm's column",
    "contrast": "candidate minus the delivering lock arm, paired per row, same flight",
    "nominated_iff": [
        "the official pooled SLU-F1 delta (candidate minus lock) has a CI95 lower bound > 0",
        "that delta is above the aa twin's official pooled SLU-F1 delta (aa minus lock, same flight)",
        "the intent guard holds: rows whose official intent correctness differs from lock <= 7 (floor 0.65 pp of 1,080)",
    ],
    "harm_iff": "the official pooled SLU-F1 delta CI95 upper bound < 0",
    "ci95_lower_bound_above": 0.0,
    "above_twin_delta": True,
    "intent_guard_floor_pp": 0.65,
    "intent_guard_rows": 7,
    "within_flight": True,
    "tie_break": "largest official SLU-F1 delta, then fewer words",
    "official_delta_source": "scripts/analysis/stage3_rollout_score.py --mode supply-variants, then scripts/analysis/stage3_paired_read.py (column arms)",
    "node_local_role": "diagnostic only; gates nothing",
}


def decision_rule() -> str:
    if nf.ITERATION >= 2:
        return ITER2_OFFICIAL_RULE + ITER2_RULE_TAIL
    return nf.localize(_DECISION_RULE_BASE)


ONE_FACTOR = (
    "the Solver instruction template (phase_material.solver.instruction_template) of each non-delivering arm: ONE "
    "hash-pinned path per arm under probes/nx/solver/r1/, nothing else (no supply knob, decoding, response format or "
    "tool authority); the base, the Fold B pins, the review-off program and the module block are the instrument's carrier, "
    "shared by every arm"
)

PROHIBITIONS = [
    "No test-split, DEV or Fold A contact or read (Fold A confirms only a later two-arm column, under its own registration).",
    "No second factor: one axis (the Solver instruction template), none on aa or lock.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No v4 or v4g normaliser wired into the cell: the runtime delivery normaliser is the COMP-1b module cell's (v3); v4 and v4g are OFFLINE read columns only.",
    "No paper-scale profile.",
    "No flight before root countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "No arm score opened before the READ row is root countersigned.",
    "No system-level claim: a column effect may only nominate.",
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


ITER2_BASIS = (
    "Declared round effect +1.54 pp official pooled SLU-F1 (class-split, the conservative figure; +2.69 pp at the uniform node "
    "rate 0.056 pp per raw-exact row) = candidate r1-i2-c3 alone: +48 predicted raw-exact rows on Fold B (candidates README "
    "sections 3 and 4), built from the MEASURED iteration-1 paired discordant counts (c3: empty-gold stratum +62, non-empty "
    "-12; plus two thirds of c5's +15 carried by the conventions block; less a winner's-curse shrink of about 5 rows). "
    "Class-split conversion: an empty-gold row made exact is an emptied false-fill row, worth 0.0333 pp; a non-empty row "
    "0.0563 pp (exchange-rate note). Iteration-1 declared vs measured raw-exact rows were c1 +32 vs -20, c3 +35 gross vs +50, "
    "c5 +5 vs +27, c2 +11 vs +12, so conversion-based priors were poorly calibrated and iteration 2 predicts from measured "
    "discordant counts instead; the roster is reused (shaped on Fold B tables, read on Fold B again), so the Fold A two-arm "
    "confirmation (programme C0.6) is the real guard. The other candidates declare +1.51 (i2-c1), +1.31 (i2-c2), +1.27 (i2-c4), "
    "+0.72 (i2-c5) class-split (+2.13, +1.74, +1.57, +0.90 uniform). claims_benefit is true for the ROUND only, carried by "
    "i2-c3. The declaration is a registered expectation, never a claim."
)
ITER2_CEILING_WHAT = (
    "the predicted +48 raw-exact rows of r1-i2-c3 on Fold B (range [+38, +65]) at the class-split conversion (empty-gold "
    "0.0333 pp, non-empty 0.0563 pp) = +1.54 pp; +2.69 pp at the uniform 0.056 pp per row"
)


def measurement_blocks(ids: dict, measure: dict, pins: dict) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    extra_audio = round((nf.CEILING - 2) * arm["audio_seconds"], 2)
    tokens = measure["template_tokens"]
    basis = ITER2_BASIS if nf.ITERATION == 2 else (
        "Declared round effect +1.80 pp official pooled SLU-F1 = candidate r1-c1 alone (the value-in-supply extraction "
        f"arm): {EXCHANGE} section 6 counts 117 MISSING entities whose value is in the Solver's view on Fold A (108 on "
        "DEV-2000-ADDED), recovered at the measured M1 delivered-filler conversion 0.2471 (docs/results/2026-09-28-"
        "slurp-w5-slot-exemplar-offline-estimate.md) = 28.9 entities x 0.0621 pp per recovered MISSING entity = +1.80 pp, "
        "about 32 raw-exact row equivalents at the node rate 0.0563 pp per raw-exact row (Fold A; DEV sensitivity +1.53 pp, "
        "27 rows). Fold B has no sealed table, so the Fold A counts are its proxy. Harm netting (candidates README section "
        "3): break-even precision of the new emissions 0.318; at the E5-1 precision 0.25 the arm is -0.72 pp. The other "
        "candidates declare +0.63 (c2), +0.89 (c3), +0.6 (c4, author prior), +0.28 (c5) and are below the floor alone; "
        "claims_benefit is true for the ROUND only, carried by c1. The declaration is a registered expectation, never a claim."
    )
    return {
        arm["run_id"]: {
            "aa_arm_id": nf.TWIN,
            "ceiling": {
                "pp": nf.EXPECTED_EFFECT_PP, "roster": nf.READ_ROSTER, "rows": 48 if nf.ITERATION == 2 else 32,
                "what": ITER2_CEILING_WHAT if nf.ITERATION == 2 else (
                    "the 117 Fold A MISSING entities with the value in the Solver's view (proxy for Fold B), ~32 raw-exact "
                    "row equivalents at 0.0563 pp per row; the range for c1 is [-0.72, +1.80] pp depending on the precision "
                    "of its new emissions"
                ),
            },
            "claim": "nominated",
            "claims_benefit": True,
            "conversion_basis": basis,
            "expected_effect_pp": nf.EXPECTED_EFFECT_PP,
            "measurement_design": "same-flight-node-column",
            "note": (
                nf.ROUND_LABEL + " (level: node column, K = 7 Solver template arms). Expected effect declared from measured "
                f"numbers ({EXCHANGE}; {nf.CANDIDATES_README} section 4), "
                f"{basis} Provisional floor SLU {nf.FLOOR_SLU_PP} pp (1.49 x sqrt(1080/1080), borrowed from "
                + ("same-flight-supply-variant, programme/instrument README: iteration 1 has flown but the official-score "
                   "twin null is read only after this flight, so the borrowed floor stands until the READ measures it)"
                   if nf.ITERATION == 2 else
                   "same-flight-supply-variant, programme/instrument README: no node-column cell has flown yet)")
                + f", so expected_effect_pp {nf.EXPECTED_EFFECT_PP} sits at about {nf.EXPECTED_EFFECT_PP / nf.FLOOR_SLU_PP:.{2 if nf.ITERATION == 2 else 1}f} x the floor, "
                + ("knowingly at it" if nf.ITERATION == 2 else "knowingly near it")
                + "; the read's "
                "bar is the aa twin null measured in this flight, |aa - lock offset| + its CI95 half-width. The delivered "
                "row is the lock arm: delivered intent and SLU are identical by construction at the request level (invariant "
                "I7; reported, never contrasted). Tuning roster TRAIN Fold A (the contrast tables that shaped the "
                "candidates), read roster TRAIN Fold B."
            ),
            "primary_metric": norm_text(
                "node-local: raw first-answer entity exact-set per row (E2 reader, per arm minus lock, paired per row); "
                "official: pooled SLU-F1 of the arm's column (slurp-slu-official-train) is the quoted effect through the "
                "E3 exchange rate (+0.056 pp per raw-exact row); guard: official intent (rows differing <= floor 0.65 pp = 7 rows)",
                "official: pooled SLU-F1 of the arm's column (slurp-slu-official-train), delta vs the delivering lock arm "
                "(paired row bootstrap, CI95 lower bound > 0) and above the aa twin's delta, within the flight (nomination_rule "
                "official-column); guard: official intent (rows differing <= floor 0.65 pp = 7 rows); node-local exact_set_normalised "
                "(E2 reader schema v2) is diagnostic and gates nothing",
            ),
            "primary_metric_key": "slu",
            **({"nomination_rule": "official-column"} if nf.ITERATION >= 2 else {}),
            "provisional_floor_pp": {
                "arithmetic": "SLU 1.49 * sqrt(1080 / 1080) = 1.4900 pp (primary), intent 0.65 * sqrt(1080 / 1080) = 0.6500 pp (guard)",
                "intent_accuracy": nf.FLOOR_INTENT_PP, "slu_f1": nf.FLOOR_SLU_PP,
            },
            "read_bar": "|aa twin offset| + twin CI95 half-width, per metric, measured in this flight",
            "read_roster": nf.READ_ROSTER,
            "rows": nf.ROWS,
            "template_variants": {"node": "solver", "candidate_arms": len(nf.ARMS), "twin": True},
            "tuning_roster": nf.TUNING_ROSTER,
            "variant_cost": {
                "extra_audio_seconds": extra_audio,
                "extra_audio_seconds_per_row_mean": round(arm["audio_seconds"] / arm["rows"] * (nf.CEILING - 2), 4),
                "extra_contacts_per_row": nf.CEILING - 2,
                "extra_perception_contacts_per_row": 0,
                "extra_solver_contacts_per_row": nf.CEILING - 2,
                "note": (
                    f"K - 1 = {len(nf.ARM_ORDER) - 1} non-delivering Solver arms (five candidates and the twin), each one "
                    f"Solver contact at the one Solver visit; every contact re-sends the row's speech packet, so "
                    f"{nf.CEILING - 2} x the Fold B total {arm['audio_seconds']} s per flight (review-off base: 2 contacts per "
                    f"row, ceiling {nf.CEILING})"
                ),
            },
        },
        smoke["run_id"]: {
            "claims_benefit": False, "expected_effect_pp": 0.0, "measurement_design": "form-proof",
            "note": (
                f"Four Fold B rows (the committed prefix receipt) prove FORM and nothing else: the {nf.PROGRAM} program "
                "loads, the seven Solver template arms fan out at the one Solver visit, every arm fits its estimated bound, "
                "the arm receipt (saea-supply-variant-arms-v4) and I7v seal, and the episode completes. Scored by no one, "
                "read by no one."
            ),
            "primary_metric": "none (structural form only)", "read_roster": nf.READ_ROSTER, "rows": 4, "tuning_roster": "none",
        },
    }


def plan_docs(ids: dict, commit: str, at: str, protocol_sha: str, pkg: str) -> dict:
    docs = {}
    source_tree = nf.SOURCE_TREE
    for kind in ("arm", "smoke"):
        i = ids[kind]
        n = nf.names(kind)
        prefix = n["prefix"]
        supply = {
            "note": ("the first Fold B first-phase supply at w_agree 1.0 with the centroid key on this roster; the "
                     "flip mints it under this cell's own run id (item E16), there is no earlier digest to reproduce"),
            "relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
        }
        # After the flip the cell baseline carries the minted pin; the registered plan must declare EXACTLY that
        # (scripts/checks/flight_registration_check.py "registered-supply-binding", 2026-10-03): copy it verbatim.
        exp_path = Path("configs/experiment") / f"{i['experiment']}.json"
        baseline_name = ""
        if exp_path.exists():
            cells = json.loads(exp_path.read_text(encoding="utf-8")).get("cells", {})
            entry = cells.get(i["cell"], {}) if isinstance(cells, dict) else next((c for c in cells if c.get("cell_id", c.get("cell")) == i["cell"]), {})
            baseline_name = entry.get("baseline", "") or entry.get("baseline_fragment", "")
        baseline_path = Path("configs/baseline") / f"{baseline_name}.json"
        if baseline_name and baseline_path.exists():
            pinned = json.loads(baseline_path.read_text(encoding="utf-8")).get("prepared_phase_supply")
            if isinstance(pinned, dict) and pinned.get("sha256") not in (None, "", "MINTED_AT_THE_FLIP"):
                supply = dict(pinned)
        base = {
            "cell": i["cell"], "composed_config_hash": i["composed_config_hash"],
            "expected_session_id": nf.SESSION, "experiment": i["experiment"], "family_budget": i["family_budget"],
            "one_factor": ONE_FACTOR, "preparation_base_commit": commit,
            "prepared_phase_supply": supply,
            "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_at_utc": at, "source_tree": source_tree,
            "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
            "unused_budget_is_not_attempt_authority": True,
        }
        gen_plan = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"],
                        protocol_hash=i["protocol_hash"], run_id=i["run_id"], schema="saea-execution-plan-v1",
                        split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        if kind == "smoke" and nf.SMOKE_RECOVERY:
            gen_plan["recovery"] = nf.SMOKE_RECOVERY
        fit_plan = dict(gen_plan, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"],
                        planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        route_gen = (
            f"Shared core.flight.cli campaign over {nf.CAMPAIGN} (this arm alone; no A/A cell -- the twin arm aa flies inside "
            "every row) through scripts/flights/nx/batch_chain_nx_r1.sh and the batch driver."
            if kind == "arm" else
            "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."
        )
        gen_purpose = (
            f"{i['run_id']}: " + (decision_rule() if kind == "arm" else "structural form proof only: no score and no read.")
        )
        docs[f"{prefix}generation-plan-registered-v1.json"] = {
            **base, "execution_plan": gen_plan, "execution_route": route_gen, "plan_kind": "generation",
            "purpose": gen_purpose, "schema": "saea-registered-generation-plan-v1",
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


def cross_iteration_block() -> dict:
    """Iteration 2 only: the DESCRIPTIVE contrast of each iteration-2 arm with iteration 1's r1-c5 (different flights)."""

    if nf.ITERATION != 2:
        return {}
    return {
        "iteration": 2,
        "cross_iteration_contrast": {
            "status": "DESCRIPTIVE ONLY: no claim, no nomination, no input to the decision rule",
            "contrast": f"each iteration-2 arm X ({', '.join(nf.ARMS)}) minus iteration-1 {nf.ITER1_COMPARATOR_ARM}, the iteration-1 arm that cleared the node screen; plus iteration-2 lock minus iteration-1 lock as the flight-offset descriptor of the unchanged locked template",
            "comparator": {
                "run_id": nf.ITER1_RUN_ID, "attempt_id": nf.ITER1_ATTEMPT_ID, "column": nf.ITER1_COMPARATOR_ARM,
                "lock_column": nf.DELIVERING, "read_run_id": nf.ITER1_READ_RUN_ID,
                "recipe": f"{nf.ITER1_PACKAGE}/analysis-recipe-v1.json",
            },
            "same_roster": nf.READ_ROSTER, "same_row_set": "the 1,080 TRAIN Fold B sample ids of both flights",
            "official_pass": {
                "driver": "scripts/analysis/stage3_paired_read.py (column arms, left run = iteration 1, right run = iteration 2; non-gating; skipped with a notice when iteration 1's official column scoring is absent)",
                "left": {"run_id": nf.ITER1_RUN_ID, "attempt_id": nf.ITER1_ATTEMPT_ID, "column": nf.ITER1_COMPARATOR_ARM},
                "right": "each iteration-2 arm, and lock against iteration-1 lock",
                "bootstrap": {"cluster_key": "sample_id", "draws": 10000, "seed": 20260915},
                "output": "analysis/" + nf.READ_RUN_ID + "/cross-iteration/<arm>-vs-i1-" + nf.ITER1_COMPARATOR_ARM,
            },
            "node_local_pass": "read by hand from the two node-local reports on file (iteration 1: analysis/" + nf.ITER1_READ_RUN_ID + "/node-local; iteration 2: analysis/" + nf.READ_RUN_ID + "/node-local); no new driver",
            "caveats": [
                "Different flights have different request-level offsets; the same-flight twin null of either flight does not bound a cross-flight difference (the lock-minus-lock row is the descriptor).",
                "r1-c5 was the best of five arms on this same roster in iteration 1 (winner's curse); a positive difference is not evidence of superiority and a negative one is not evidence of harm.",
                "Iteration 1's r1-c5 does not fly in iteration 2: this table is the only place the two rounds meet, and it gates nothing.",
            ],
        },
    }


def carrier() -> str:
    """The arm that carries the declared round effect."""
    return nf.ARMS[0] if nf.ITERATION == 1 else nf.ARMS[2]


def smoke_section() -> str:
    if nf.SMOKE_RECOVERY:
        return (
            f"## Smoke recovery (the cell's single recovery re-registration)\n\n{nf.SMOKE_RECOVERY['reason']}\n\n"
            f"{nf.SMOKE_RECOVERY['amendment']} The smoke plans therefore carry run-cumulative budgets of 64 model calls / 164 "
            "speech-seconds; the FIT endpoint cap is structural, not run-cumulative (128 = 4 rows x 8 contacts x 4 endpoints): the failed attempt spent 32 / 81.453, rec1 and rec2 spent 0, rec3 is budgeted 32 / 82. "
            "The arm's budgets are unchanged.\n\n"
        )
    return (
        "## Attempt state (no recovery)\n\nThe smoke and the arm are FIRST attempts of their run ids. Budgets are therefore "
        "single-attempt: smoke 32 model calls / 82 speech-seconds, FIT endpoint cap 128 (structural: 4 rows x 8 contacts x 4 "
        "endpoints); arm 8,640 / 25,239 speech-seconds, FIT cap 34,560. A recovery re-registration, if one is ever needed, "
        "must re-derive the run-cumulative generation budget (earlier attempts' spend plus the new attempt's worst case) and "
        "keep the FIT cap structural. At most one recovery re-registration per cell.\n\n"
    )


def write_package(ids: dict, commit: str, at: str) -> dict:
    pkg = nf.PACKAGE
    measure = nf.fit_measure()
    pins = nf.candidate_pins()
    arm, smoke = ids["arm"], ids["smoke"]
    blocks = measurement_blocks(ids, measure, pins)
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id",
                                           "fit_run_id", "protocol_hash", "rows", "run_id", "split_identity_hash")}
                  for k, v in ids.items()},
        "decision_rule_fixed_here": decision_rule(),
        "development_numbers_only": "Every number is a TRAIN Fold B development number (owner decisions 28 and 86), never a test claim.",
        "failure_policy": ("Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a "
                           "second failure closes the cell and the fix is proven on a four-row dry run. The budget is "
                           "run-cumulative across attempts."),
        "one_factor": ONE_FACTOR, "prohibitions": PROHIBITIONS,
        **({"recovery": {"smoke": nf.SMOKE_RECOVERY}} if nf.SMOKE_RECOVERY else {}),
        "protocol_id": f"slurp-{nf.SLUG}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1",
        "source_tree": nf.SOURCE_TREE,
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "study_commit_at_registration": commit,
        "the_question": (
            norm_text(
                "At the one Solver visit of every TRAIN Fold B row of the review-off COMP-1b module graph, does any of five "
                "hand-written Solver instruction templates raise the Solver's raw first-answer entity exact-set per row over the "
                "locked template, paired per row inside one flight, beyond the in-flight twin's null, without a secondary or "
                "intent loss?",
                "At the one Solver visit of every TRAIN Fold B row of the review-off COMP-1b module graph, does any of five "
                "hand-written Solver instruction templates raise the OFFICIAL pooled SLU-F1 of the delivered column over the locked "
                "template (paired per row inside one flight, CI95 lower bound above zero), by more than the in-flight twin's "
                "delta, without an intent loss beyond the floor? (The node-local exact-set read is diagnostic.)",
            )
        ),
    }
    protocol_sha = wjson(f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(ids, commit, at, protocol_sha, pkg)
    shas = {name: wjson(f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "arms": {
            "arm": {"attempt_id": arm["attempt_id"], "role": "the sealed flight: every arm below is a column of it",
                    "run_id": arm["run_id"]},
            "columns": {
                **{a: {"role": "candidate Solver instruction template (hash-pinned)", **pins[a]} for a in nf.ARMS},
                nf.TWIN: {"role": "the in-flight twin: replicate_of lock, the null of every contrast"},
                nf.DELIVERING: {"role": "the delivering arm: LEFT of every contrast (the locked template, untemplated)",
                                "relpath": nf.LOCKED_TEMPLATE, "sha256": nf.LOCKED_TEMPLATE_SHA},
            },
        },
        "boundary": ("A development read on a TRAIN fold (owner decisions 28 and 86); never a test claim; node-local, never a "
                     "system-level claim. No utterance text, transcript, gold label or model output is printed or persisted."),
        "decision_rule": decision_rule(),
        **({"nomination": NOMINATION_BLOCK} if nf.ITERATION >= 2 else {}),
        "node_local": {
            **({"role": "diagnostic: localises where an official delta comes from; gates nothing"} if nf.ITERATION >= 2 else {}),
            "driver": "scripts/analysis/slurp_nx_solver_column_read.py",
            **norm_text(
                {"primary": "exact_set", "secondaries": ["parse_valid", "empty_gold_false_fill", "nonempty_exact"]},
                {"primary": "exact_set_normalised", "primary_view": "normalised",
                 "primary_definition": "the entity exact-set per row of the answer AFTER the cell's own delivery normaliser, derived by stage3_rollout_score.normalise_arm_answer (the official column scorer's function)",
                 "secondaries": ["parse_valid", "empty_gold_false_fill", "nonempty_exact"], "secondaries_view": "normalised",
                 "diagnostic": {"view": "raw", "metric": "exact_set", "also": ["raw-vs-normalised flip table per arm"]},
                 "report_schema": "saea-nx-solver-column-read-v2"}),
            "bootstrap": {"cluster": "whole utterance", "draws": 10000, "seed": 20260915},
            "output": "analysis/" + nf.READ_RUN_ID + "/node-local",
        },
        "offline_columns": {
            "note": ("0 GPU, zero model contacts. Two deterministic delivery-normaliser variants applied OFFLINE to every arm's "
                     "delivered column; the cell's runtime delivery normaliser stays the COMP-1b module cell's "
                     "(saea-deliver-normalise-v3) and neither variant is wired into the cell."),
            "driver": "scripts/analysis/slurp_nx_postproc_v4_apply.py",
            "rule_driver": "scripts/analysis/slurp_nx_postproc_v4_search.py",
            "driver_interface_status": (
                "the rule definitions and their offline selection live in scripts/analysis/slurp_nx_postproc_v4_search.py (the "
                "separate agent's driver); the application of the REGISTERED normalisers saea-deliver-normalise-v4 / -v4g to a sealed "
                "column is scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4|v4g --pool <run>/<attempt> [--column <arm id>] "
                "(on master since merge 7bfc09b3b). KNOWN BLOCKER: that driver refuses any run whose roster intersects TRAIN Fold B "
                "('Fold B is not read by this script'); the R1 run IS Fold B, so the refusal must be lifted for this one recipe before "
                "the offline step can run (nx_r1_read.sh reports it and exits 10 rather than skipping silently)"),
            "columns": {
                "v4": {"normaliser": "saea-deliver-normalise-v4", "rules": nf.V4_RULES,
                       "definition": f"the five-rule set of {V4_READ} section 6, in the registered order"},
                "v4g": {"normaliser": "saea-deliver-normalise-v4g", "rules": nf.V4_RULES, "guards": nf.V4G_GUARDS,
                        "definition": f"v4 with the two TRAIN-only guards ee-wilson and ti-expressible of {V4_ATTR} section 4"},
            },
            "statistics": {"artifact_id": nf.V4_STATS_ARTIFACT_ID, "sha256": nf.V4_STATS_SHA256},
            "applied_to": list(nf.ARM_ORDER),
            "contrasts": ["v4(X) - X", "v4g(X) - X", "v4g(X) - lock (candidates; composition)"],
            "bootstrap": {"cluster": "whole utterance", "draws": 10000, "seed": 20260915},
            "lock_rule_row": {
                "contrast": "v4g(lock) - lock",
                "rule": ("The R1 delivering-arm (lock) column on TRAIN Fold B is the FRESH CONFIRMATION roster for v4g (the "
                         "guards were derived from Fold A and A2 attribution, so neither can confirm them): lock v4g iff the "
                         "CI95 lower bound of the paired pooled SLU-F1 delta is above 0 here."),
            },
            "output": "analysis/" + nf.READ_RUN_ID + "/offline-v4",
        },
        "official_columns": {
            "scorer": "slurp-slu-official-train", "scoring_jobs": len(nf.ARM_ORDER),
            "render": "scripts/analysis/stage3_rollout_score.py --mode supply-variants",
            "paired_driver": "scripts/analysis/stage3_paired_read.py (column arms; --cluster-key sample_id)",
            "bootstrap": {"cluster_key": "sample_id", "draws": 10000, "seed": 20260915,
                          "unit": "row (paired); the whole-utterance number is the node-local and offline reads' own"},
            "passes": {
                **{f"{a}-vs-lock": {"left": nf.DELIVERING, "right": a, "gating": True} for a in nf.ARMS},
                "aa-vs-lock": {"left": nf.DELIVERING, "right": nf.TWIN, "gating": "sets the bar"},
            },
            "output": "analysis/" + nf.READ_RUN_ID + "/<pass>",
        },
        "output": {"analysis_root": "analysis/" + nf.READ_RUN_ID},
        "read_driver": "scripts/analysis/nx_r1_read.sh",
        "read_run_id": nf.READ_RUN_ID,
        "recipe_id": nf.RECIPE_ID,
        "registered_at_utc": at,
        "resampling": {"bootstrap_draws": 10000, "seed": 20260915},
        "review_off_vs_full_graph": {
            "contrast": "the delivering lock arm of this flight (review-off, Fold B) vs the P-SV-3 a-agree DELIVERED column on the same Fold B",
            "comparator": {"read": PSV3_READ, "column": "a-agree (delivered)", "official_slu_columns": "on file"},
            "offset_bound": "the P-SV-3 t-twin offset (flight offset between two identical-request flights)",
            "bar_pp": 2.5, "extra_flight": False,
            "rule": ("If the lock arm minus the P-SV-3 a-agree delivered column is within the bar (2.5 pp; the P-SV-3 t-twin "
                     "offset reported beside as the flight-offset bound), review-off is locked (owner decision 232 / "
                     "programme F2); if the full graph wins by more than 1.49 pp SLU with CI95 lower bound > 0 the drop is "
                     "revisited. Cross-flight and therefore never a gating number of this flight's column read."),
        },
        "run_ids": {"arm": arm["run_id"], "read": nf.READ_RUN_ID,
                    "context_comparator": "SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1"},
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "steps": [
            f"0. Refuse unless the READ row {nf.READ_RUN_ID} is root countersigned.",
            "1. Refuse unless the flight carries a COMPLETE sealed 1,080-row manifest with one complete official TRAIN score and the saea-supply-variant-arms-v4 receipt on every row, verified by the bundle (invariant I7v).",
            norm_text("2. Node-local (E2): per arm raw parse validity, entity exact-set, empty-gold false fill, non-empty exact and per-slot-type counts, paired per row against lock, whole-utterance bootstrap and paired Wilson.",
                      "2. Node-local (E2, schema v2; DIAGNOSTIC, gates nothing): per arm, on the answer after the cell's own delivery normaliser (primary exact_set_normalised) and on the raw answer (diagnostic), parse validity, entity exact-set, empty-gold false fill, non-empty exact and per-slot-type counts, paired per row against lock, whole-utterance bootstrap and paired Wilson; plus the per-arm raw-vs-normalised flip table."),
            "3. Official: render each arm's first-visit Solver answer through the delivered row's normaliser and projection and score it ONCE with slurp-slu-official-train (seven jobs, never sharded).",
            norm_text("4. Twin null (aa vs lock) first, then each candidate vs lock under the rule; per-scenario tables.",
                      "4. Twin null (aa vs lock) first, then each candidate vs lock on the OFFICIAL pooled SLU-F1 column (nomination rule: CI95 lower bound > 0, above the aa delta, intent guard 0.65 pp, within the flight); per-scenario tables."),
            "5. Offline v4 / v4g columns over every arm's delivered column (0 GPU), the lock row v4g(lock) - lock being the v4g confirmation.",
            "6. The review-off vs full-graph comparison against the P-SV-3 a-agree delivered column (cross-flight; no extra flight).",
        ] + ([
            "7. Iteration 2 only, DESCRIPTIVE: each iteration-2 arm and lock against iteration-1 r1-c5 / lock (cross-flight; gates nothing; recipe cross_iteration_contrast).",
        ] if nf.ITERATION == 2 else []),
        **cross_iteration_block(),
        "title": nf.localize("Cell NX-R1-SOLVER -- the same-flight Solver instruction-template column read: five candidates and the twin, each against the delivering lock arm"),
    }
    shas["analysis-recipe-v1.json"] = wjson(f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "budget_arithmetic": {
            "arm_family_budget": arm["family_budget"], "smoke_family_budget": smoke["family_budget"],
            "note": (f"review-off graph: perception 1 + solver 1 + (K - 1) = {nf.CEILING} contacts per row (K = 7 arms); generation rows x "
                     f"{nf.CEILING}, FIT rows x {nf.CEILING} x 4, speech ceil(audio x {nf.CEILING}), planned GPU hours {nf.PLANNED_GPU_HOURS_ARM} "
                     f"(arm; at the measured 50 contacts per minute {nf.ROWS * nf.CEILING} contacts need about 2.9 h, the programme's ~2.5 GPU-h per round) "
                     "and 1.0 (smoke); native task-contract calls = every contact; run-cumulative"),
        },
        "candidates": {a: {"author": "hand (Opus 5.5 from aggregate tables)", **pins[a], "template_tokens_estimated": measure["template_tokens"][a]}
                       for a in nf.ARMS},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "decision_rule": decision_rule(),
        "delivering_template": {"relpath": nf.LOCKED_TEMPLATE, "sha256": nf.LOCKED_TEMPLATE_SHA,
                                "template_tokens_estimated": measure["template_tokens"]["lock"]},
        "fit": {"status": "PENDING_CHECK"},
        "fit_measure": {"relpath": nf.FIT_MEASURE, "sha256": sha_file(nf.FIT_MEASURE),
                        "tool": "scripts/flights/nx/nx_r1_fit_measure.py",
                        "summary": {k: measure[k] for k in ("chars_per_token_least_squares", "first_solver_visits", "items",
                                                            "prompt_tokens", "prompt_limit_tokens", "template_frame",
                                                            "arm_prompt_estimates", "source")}},
        "identity": ids,
        "owner_decisions": {
            "139": "no prior: the expectation is declared from measured numbers (the E3 exchange rates and the candidates README)",
            "192": "the declared effect is on file BEFORE flight",
            "228-234": "NX programme: base = the COMP-1b lock; one registration, countersign and read per round; n >= 1,080 same-flight paired",
            "229-232": f"as ruled in {OWNER_DECISIONS} section Decisions 228-236; the Reviewer loop is off (F2)",
            "28/86": "TRAIN numbers are development numbers, never a test claim",
        },
        "prohibitions": PROHIBITIONS,
        "registered_at_utc": at,
        "registration_basis": (f"coordinator brief 2026-10-09: register {nf.ROUND_LABEL} from {PROGRAMME} (C0, C1 E1/E2/E5, C2 R1, C4, F2). "
                               "HELD: the owner / root admission is still required; nothing here authorises a flip or a flight."),
        "rows": nf.ROWS,
        "schema": "saea-registered-facts-v1",
        "stage3_measurement": blocks,
        "study_commit_at_registration": commit,
        "the_cell": {
            "base": "the COMP-1b composition (agree-vote-seed + centroid-boundary-key) as a consumption-module block on lock v2.1, review loop OFF",
            "program": nf.PROGRAM, "ceiling": nf.CEILING,
            "template_variants": json.loads(rd(f"configs/baseline/{arm['baseline_fragment']}.json"))[
                "native_episode"]["roles"]["solver"]["template_variants"],
        },
    }
    shas["registered-facts-v1.json"] = wjson(f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for root to mint on the data root with scripts/flights/nx/nx_r1_mint_receipt.py (status decided, "
                        "recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'."),
        "antecedents": {
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "candidates_readme": {"path": nf.CANDIDATES_README, "sha256": sha_file(nf.CANDIDATES_README)},
            "derive_script": {"path": "scripts/flights/nx/derive_slurp_nx_r1_cells.py", "sha256": sha_file("scripts/flights/nx/derive_slurp_nx_r1_cells.py")},
            "exchange_rates": {"path": EXCHANGE, "sha256": sha_file(EXCHANGE)},
            "instrument_design": {"path": SPEC, "sha256": sha_file(SPEC)},
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "preregistration": {"path": nf.PREREG, "sha256": None},
            "programme": {"path": PROGRAMME, "sha256": sha_file(PROGRAMME)},
            "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None},
            "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit,
        },
        "authorization_basis": ("Owner decisions 228-234 (programme approved 2026-10-09), 139, 192, 28/86; the node-template instrument "
                                f"({SPEC}); {OWNER_DECISIONS} section Decisions 228-236."),
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "smoke": smoke["family_budget"]},
        "cell_kind": ("Stage-3 same-flight NODE-TEMPLATE column cell (NX instrument E1, label none), claim ceiling 'nominated'. One arm on "
                      f"TRAIN Fold B 1,080 with seven Solver template arms (five candidates, aa twin, lock delivering), and a four-row form smoke."),
        "claim_boundary": ("No system-level, superiority, generalisation, component-causal, held-out, confirmatory or paper-scale claim; a "
                           "node column read on a development fold whose ceiling is 'nominated'."),
        "coordinator": "Fable5.1",
        "decision": (f"Fly cell {nf.CELL_LABEL}: the COMP-1b module composition with the Reviewer loop off on TRAIN Fold B under "
                     f"{nf.PROGRAM} with a Solver template column; read {nf.ARMS[0]} .. {nf.ARMS[-1]} and aa against lock in the same flight; nominate or not at the twin bar."),
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
            "wiring the v4 or v4g normaliser into the cell",
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
        f"# Cell {nf.CELL_LABEL} (node-extreme programme {nf.ROUND_LABEL.replace('NX ', '')}, Solver template column): preregistration\n\n"
        f"Registered {at[:10]} at study commit `{commit}`, before any contact, by script (decision 58) from the P-SV-4 Fold B fragments "
        f"and the consumption-module compiler under the NX programme (owner decisions 228-234). Development numbers only.\n\n"
        "| item | value |\n| --- | --- |\n"
        "| base | the COMP-1b composition as a module block on lock v2.1 (agree-vote-seed + centroid-boundary-key ON), Reviewer loop OFF, no tool schema on any role |\n"
        f"| program | `{nf.PROGRAM}` (ceiling {nf.CEILING} = 2 + (7 - 1)) |\n"
        f"| arms | `{nf.ARMS[0]}` .. `{nf.ARMS[-1]}` (candidates, pinned under `configs/probes/nx/solver/r1/`), `aa` (twin of `lock`), `lock` (delivering, `{nf.LOCKED_TEMPLATE}`) |\n"
        "| design / claim | `same-flight-node-column` / `nominated` |\n"
        + norm_text("| primary | node-local raw first-answer entity exact-set per row (E2), quoted on official pooled SLU-F1 through the E3 exchange rate; guard official intent (rows differing <= 7) |\n",
                    "| primary | official pooled SLU-F1 delta of the arm column vs lock (nomination_rule official-column: CI95 lower bound > 0, above the aa twin delta, intent rows differing <= 7 = 0.65 pp, within the flight); node-local exact_set_normalised (E2 v2) and the raw exact-set are diagnostic |\n") +
        f"| expected effect | {nf.EXPECTED_EFFECT_PP} pp (the ROUND, carried by {carrier()}), `claims_benefit` true; provisional floor SLU {nf.FLOOR_SLU_PP} pp |\n"
        f"| rosters | tuning `{nf.TUNING_ROSTER}`; read `{nf.READ_ROSTER}` |\n"
        f"| runs | `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{nf.READ_RUN_ID}` |\n"
        f"| composed config hashes | arm `{arm['composed_config_hash']}`; smoke `{smoke['composed_config_hash']}` |\n"
        f"| protocol hashes | arm `{arm['protocol_hash']}`; smoke `{smoke['protocol_hash']}` |\n"
        f"| split identity | arm `{arm['split_identity_hash']}`; smoke `{smoke['split_identity_hash']}` |\n\n"
        + smoke_section() +
        f"## Decision rule (fixed here)\n\n{decision_rule()}\n\n## The measurement declaration\n\n```json\n"
        + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True)
        + "\n```\n"
    )
    shas["__prereg__"] = wr(nf.PREREG, prereg)
    return {"shas": shas, "blocks": blocks, "protocol_sha": protocol_sha}


def ledger_rows(ids: dict, commit: str, at: str, shas: dict) -> str:
    pkg = nf.PACKAGE
    arm, smoke = ids["arm"], ids["smoke"]
    scope = ("Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any "
             "role; the COMP-1b module composition on lock v2.1 with the Reviewer loop off; Solver instruction-template column of "
             "seven arms (five hand-written candidates, the aa twin, the locked delivering lock arm) at the one Solver visit")
    inherited = ("TRAIN Fold B discovery rows already exposed by SAEA-SLURP-EVO-FOLD-PACKETS-V2, SAEA-SLURP-EVO-S1-INTENT-FOLDS-V2, the "
                 "EVO-S1 confirmation fold SAEA-SLURP-EVO-S1-FOLD-B-V2 (8,640 contacts, 2026-09-06), the encoder pass "
                 "SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1, the model-free W2 offline guard read against Fold B gold and the "
                 "P-SV-1..P-SV-4 Fold B cells registered on these rows; this cell opens no split. Prior exposure is inherited in full.")
    note_common = (
        f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {at[:10]} at study commit {commit} by the {nf.ROUND_LABEL} registration agent "
        f"(worktree {nf.WORKTREE}, branch {nf.BRANCH}); NX programme owner decisions 228-234. "
        "HELD: this registration performs no contact and authorises none. READINESS HELD: root countersigns the five DRAFT rows, mints "
        f"{nf.DECISION_RELPATH} (decision id {nf.DECISION_ID}) from the package's root-admission-draft-v1.json with scripts/flights/nx/nx_r1_mint_receipt.py "
        "(four eligible run ids), then scripts/flights/nx/nx_r1_flip.sh re-pins with scripts/flights/repin_cell.py --set-ready, re-minting each "
        "cell's OWN first-phase supply (item E16); --allow-output-change must never be passed; every hash in this row moves at the flip. "
        f"Measurement declaration: same-flight-node-column, expected_effect_pp {nf.EXPECTED_EFFECT_PP}, claims_benefit true (the round, carried by {carrier()}), "
        "primary_metric_key slu, floor SLU 1.49 / intent 0.65 (provisional, borrowed), claim nominated, aa twin. "
        f"Read: {nf.READ_RUN_ID} by scripts/analysis/nx_r1_read.sh. Stop and preserve on the first failure; AT MOST ONE root-diagnosed "
        "recovery re-registration. No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
    )

    def row(date, rid, profile, what, model, carrier, split, consumed, calls, audio, gpu, artifacts, notes):
        cells = [date, rid, profile, what, model, carrier, "discovery", split, consumed, str(calls), str(audio), str(gpu), inherited, artifacts, notes]
        return "| " + " | ".join(cells) + " |"

    def plan_row(kind, fit):
        i = ids[kind]
        n = nf.names(kind)
        prefix = n["prefix"]
        rows = i["rows"]
        what = (nf.ROUND_LABEL + ": the Solver instruction-template column on TRAIN Fold B" if kind == "arm" else
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
        return row(at, i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], what, scope,
                   f"slurp TRAIN Fold B {rows}", i["split_identity_hash"], "no", calls,
                   i["family_budget"]["repeated_speech_audio_seconds_cap"], i["family_budget"]["gpu_hours_fit_inclusive"], plan, notes)

    read = row(
        at[:10], nf.READ_RUN_ID, "model-free-check",
        (f"The same-flight Solver template-column read of {nf.ROUND_LABEL}: per arm ({nf.ARMS[0]} .. {nf.ARMS[-1]}, aa; lock the delivering reference) the "
         + norm_text("node-local raw entity exact-set and secondaries (E2 reader), ",
                     "node-local normalised entity exact-set and secondaries (E2 reader v2; DIAGNOSTIC, gates nothing), ") +
         "the official pooled SLU-F1 and intent of each arm's column scored ONCE with "
         "slurp-slu-official-train (seven column scorings, never sharded), paired bootstraps against lock with the aa twin as the bar"
         + norm_text(", ", " (NOMINATION on the official column: CI95 lower bound of the SLU-F1 delta > 0, above the aa delta, intent guard 0.65 pp, within the flight), ") +
         "and the "
         "OFFLINE v4 / v4g delivery-normaliser columns over every arm's delivered column; by the recipe "
         f"{pkg}/analysis-recipe-v1.json through scripts/analysis/nx_r1_read.sh. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "no model or tool contact; read of sealed bytes and seven official column scorings plus the offline v4/v4g scorings",
        f"slurp TRAIN Fold B {nf.ROWS}, the sealed {nf.ROUND_LABEL} flight's Solver template columns (after the seal)", ids["arm"]["split_identity_hash"], "no", 0, 0, 0,
        f"{pkg}/analysis-recipe-v1.json",
        (f"REGISTERED WITH THE FLIGHT (DRAFT, root countersignature pending; countersigned after the seal and before any arm column is opened) "
         f"{at[:10]} at study commit {commit}. Recipe {nf.RECIPE_ID}; output analysis/{nf.READ_RUN_ID}. One READ row covers the candidate "
         "contrasts, the twin null and the offline v4/v4g columns. Its ceiling is a nomination; it admits nothing."),
    )
    lines = [
        nf.LEDGER_MARK + " (owner decisions 228-234) -- the arm, its four-row smoke and the READ row (DRAFT, root countersignature pending)",
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
    """Replace this iteration's section (its heading up to the next ``## `` heading, or the end); append when absent.
    Other sections, including the other iteration's rows, are never touched."""
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
    parser.add_argument("--iteration", type=int, default=nf.ITERATION, choices=(1, 2))
    args = parser.parse_args(argv)
    nf.configure(args.iteration)
    ids = identities()
    result = write_package(ids, args.study_commit, args.registered_at)
    if not args.no_ledger:
        write_ledger(ledger_rows(ids, args.study_commit, args.registered_at, result["shas"]))
    print(json.dumps({"package": nf.PACKAGE, "files": sorted(result["shas"]),
                      "composed": {k: v["composed_config_hash"] for k, v in ids.items()},
                      "protocol": {k: v["protocol_hash"] for k, v in ids.items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
