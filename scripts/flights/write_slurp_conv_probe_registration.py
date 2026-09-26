#!/usr/bin/env python3
"""Write cell CONV's registration package from the committed configs.

Reads the derived fragments and the roster-derivation receipt, recomposes the
cell's own hashes, and writes the package documents. Config alone: no adapter,
no split load, no lock, no contact, and it flips nothing and mints nothing.

    python scripts/flights/write_slurp_conv_probe_registration.py \
        --study-commit c6ced983 --registered-at 2026-09-26T18:00:00.000000+00:00
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
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

PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1"
PREREG = "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1-preregistration.md"
EXPERIMENT = "slurp-native-stage3-conv-fold-a-70-v1"
ROSTER_DERIVATION = PACKAGE + "/roster-derivation-v1.json"

PARENT_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
PARENT_ARM_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
PARENT_AA_RUN = "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1"
PARENT_SMOKE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

WITHIN_FLIGHT_NULL = (
    "docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md"
)
RANK_DIAGNOSTIC = "docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
BAD_CASE_BANK_DOC = "docs/results/2026-09-24-slurp-plan-bad-case-bank.md"

#: The registered per-row headroom of the class the whole gain lands on, from
#: the parent package's own expected_effect_derivation. Not re-derived here.
HEADROOM_SLU = 5.41 / 130.0
HEADROOM_INTENT = 12.04 / 130.0
ARM_ROWS = 1080
ARM_BAR_PP = 2.5
ARM_CEILING_PP = 2.9131
ARM_DECLARED_PP = 1.363
ARM_DECLARED_CONVERSION = 0.467895
ARM_PERSUASION = 0.5
ARM_P_CORRECT_GIVEN_COVERED = 0.935789

GOLD_SELECTION = (
    "THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class and "
    "each row's gold intent were read on the scoring side only, in the committed "
    "roster derivation, before this cell existed. That is legitimate for a "
    "CONDITIONAL estimate on a TRAIN roster and it is legitimate for nothing else: "
    "NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its "
    "population was chosen by the mechanism's own effect. Gold reaches no query, no "
    "key, no weight, no selector and no runtime, and no gold label, intent name, "
    "transcript or utterance text is printed or persisted anywhere in this package."
)

NO_POOLED_CLAIM = (
    "This cell reads ONE quantity: the per-row intent verdict on a gold-selected "
    "subset. It may never be reported as a pooled SLU-F1 or intent-accuracy effect, "
    "as an admission, as a replication, or as evidence about any roster. Its "
    "population is the mechanism's own beneficiaries; a pooled number computed over "
    "it would be a selection artefact by construction. The cell also cannot see "
    "harm: every row here is already intent-wrong in the comparator, so the rows "
    "where the mechanism could COST a correct intent are outside this roster and "
    "remain the AGREE arm's own question."
)

WHY_INTENT_NOT_SLU = (
    "The within-flight null (" + WITHIN_FLIGHT_NULL + ") measured 0 intent flips out "
    "of 200 request-identical rows, so an intent flip is ATTRIBUTABLE rather than "
    "noise and a per-row intent read is legible at n = 70. Pooled SLU-F1 is not: its "
    "own measured noise would swamp 70 rows, and the official SLU-F1 is entity-only "
    "while this mechanism acts on the intent. The official scorer still produces the "
    "number -- the read takes its per-sample scenario_action_exact field and nothing "
    "else -- so the standard-scoring rule is intact."
)


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


LEDGER = "docs/exposure-ledger.md"

MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech "
    "packets; NO native tool authority on any role; prompt bytes otherwise the "
    "registered AGREE arm's, which are otherwise the sealed PLAN arm's"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, the "
    "released direct anchor, cells B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, B7a, "
    "B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr and ROLL-2; this cell adds no new row "
    "to the fold, re-flies a strict subset of it and opens no split. Prior exposure is "
    "inherited in full."
)


def append_ledger(
    args: argparse.Namespace,
    *,
    rows: int,
    run_id: str,
    fit_run: str,
    cell: dict,
    fit: dict,
    caps: dict,
    composed_hash: str,
    phash: str,
    split: str,
    roster: dict,
    plan_shas: dict,
    expected_contacts: int,
    rows_needed: int,
) -> str:
    """Append cell CONV's two unconsumed exposure rows. Idempotent: refuses to
    append a second time rather than duplicating a run id."""

    text = rd(LEDGER)
    if run_id in text:
        return "already-present"

    def notes(kind: str) -> str:
        attempt = cell["attempt_id"] if kind == "generation" else fit["attempt_id"]
        return (
            "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) "
            + args.registered_at[:10]
            + " at study commit "
            + args.study_commit
            + " by the CONV registration agent (worktree "
            + args.worktree
            + ", branch "
            + args.branch
            + "). This registration performs no contact and authorises none. Plan SHA256 "
            + plan_shas[kind]
            + "; attempt "
            + attempt
            + ". Protocol hash "
            + phash
            + "; composed config "
            + composed_hash
            + "; expected session "
            + SESSION
            + " (attach only, never spawn or stop). READINESS HELD: root mints "
            "coordination/slurp-stage3-conv-fold-a-70-v1/root-admission-v1.json "
            "(decision id slurp-stage3-conv-fold-a-70-admission-v1) with the two "
            "eligible run ids "
            + run_id
            + ", "
            + fit_run
            + " and this cell's caps, then re-pins with "
            "scripts/flights/repin_cell.py --set-ready, which mints this cell's OWN "
            "first-phase supply under its own run id (item E16); the cell carries NO "
            "committed prepared_phase_supply and an EMPTY readiness requirements list, "
            "and --allow-output-change must never be passed. The agreement merge moved "
            "the implementation sha256 of rails.kb_policy, rails.knowledge_provider and "
            "rails.phase_supply, which FlightRuntime._phase_seed_inputs binds, so every "
            "prepared_phase_supply pin in the repository is invalidated; this cell has "
            "none to invalidate. Every hash in this row moves at the flip and the "
            "re-pin tool rewrites it. Measurement declaration "
            "(scripts/checks/stage3_effect_floor_check.py): measurement_design "
            "form-proof, expected_effect_pp 0.0, claims_benefit false, rows "
            + str(rows)
            + ", no admission mode -- declared at the top level of "
            + PACKAGE
            + "/registered-facts-v1.json and repeated in the preregistration fence. "
            "THE ROSTER WAS SELECTED USING GOLD, OFFLINE (roster derivation "
            + PACKAGE
            + "/roster-derivation-v1.json, id-list sha256 "
            + roster["id_list_sha256"]
            + ", proven against the committed replication receipt with zero "
            "differences): a CONDITIONAL rate on a TRAIN roster only, and NO pooled, "
            "roster-level, effectiveness or generalisation claim may ever be made from "
            "this cell. It also cannot see harm: every row is already intent-wrong in "
            "the sealed comparator. Ceiling "
            + str(caps["generation_calls_cap"])
            + " = "
            + str(rows)
            + " rows x 11 contacts per row; expected about "
            + str(expected_contacts)
            + " contacts and about 0.24 GPU hours at the sealed PLAN arm's own realized "
            "rate -- a ceiling is a BOUND, never a target, and budgets are "
            "run-cumulative across every attempt of a run id. Shared core.flight.cli "
            "campaign over the committed single-cell campaign plan "
            "configs/campaign/slurp-native-stage3-conv-fold-a-70-v1.json; ONE official "
            "complete score at finalize over the complete "
            + str(rows)
            + "-row manifest, never sharded, and the read takes one field per row "
            "(scenario_action_exact). The deliverable is P(correct given newly "
            "delivered) = m / "
            + str(rows)
            + " with a binomial CI95; the AGREE arm clears its own 2.5 pp bar at "
            "n = 1,080 only if m >= "
            + str(rows_needed)
            + ". The comparator "
            + COMPARATOR_RUN
            + " is sealed and never re-flown. Stop and preserve on the first failure; "
            "AT MOST ONE root-diagnosed recovery re-registration. No paper-scale "
            "profile, no confirmatory split, no test-split contact, no comparator "
            "flight and no admission entry from this cell."
        )

    def row(kind: str) -> str:
        generation = kind == "generation"
        return " | ".join(
            [
                "",
                args.registered_at,
                run_id if generation else fit_run,
                "bounded-discovery-probe",
                (
                    "Cell CONV, the conversion probe of cell AGREE: the registered "
                    "AGREE treatment unchanged, flown on the "
                    + str(rows)
                    + " TRAIN Fold A rows whose gold intent's boundary entry it newly "
                    "delivers, to measure P(correct given newly delivered) -- the arm's "
                    "one unmeasured term. Treatment only; the comparator is sealed."
                    if generation
                    else "Cell CONV -- FIT spend identity, request envelopes only, no "
                    "generation: the registered AGREE treatment unchanged on the same "
                    + str(rows)
                    + " derived TRAIN Fold A rows."
                ),
                MODEL_TOOL,
                "slurp TRAIN Fold A conversion subset " + str(rows),
                "discovery",
                split,
                "no",
                str(
                    caps["generation_calls_cap"]
                    if generation
                    else caps["fit_endpoint_calls_cap"]
                ),
                str(caps["repeated_speech_audio_seconds_cap"]),
                str(caps["gpu_hours_fit_inclusive"]),
                INHERITED,
                PACKAGE
                + ("/generation-plan-registered-v1.json" if generation else "/fit-plan-registered-v1.json"),
                notes(kind),
                "",
            ]
        ).strip()

    header = (
        "\n## Cell CONV: the conversion from delivery to correctness on the AGREE arm's own "
        "newly delivered rows (DRAFT, root countersignature pending)\n\n"
        "Two unconsumed flight rows -- the CONV probe and its FIT spend identity -- for the "
        + str(rows)
        + "-row TRAIN Fold A subset the AGREE arm's expected-effect arithmetic charges its whole "
        "gain against. The roster is reconstructed from the committed production-replication "
        "receipt's own recipe and proven against every count that receipt committed ("
        + PACKAGE
        + "/roster-derivation-v1.json). Authority "
        + PARENT_PACKAGE
        + "/production-replication-v1.json and "
        + RANK_DIAGNOSTIC
        + ". Neither row is countersigned and neither authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + "
        "split | split role | split identity hash | consumed | calls | speech audio seconds | gpu "
        "hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + row("generation") + "\n" + row("fit") + "\n")
    return "appended"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/conv")
    parser.add_argument(
        "--worktree", default="/home/chao/saea-worktrees/fable-conv"
    )
    parser.add_argument(
        "--append-ledger",
        action="store_true",
        help=(
            "also append the two unconsumed exposure rows; idempotent, it refuses to "
            "append a second time rather than duplicating a run id"
        ),
    )
    args = parser.parse_args(argv)

    derivation = json.loads(rd(ROSTER_DERIVATION))
    roster = derivation["roster"]
    rows = int(roster["count"])
    document = json.loads(rd(f"configs/experiment/{EXPERIMENT}.json"))
    cell = document["cells"][0]
    composed = compose(
        REPO_ROOT,
        cell["model_fragment"],
        cell["dataset_fragment"],
        cell["baseline_fragment"],
        EXPERIMENT,
    )
    split = document["population"]["split_identity_hash"]
    phash = protocol_hash(composed.config_hash, composed.values["arm"], split)
    caps = document["family_budget"]
    fit = composed.values["native_contact_fit"]
    run_id = cell["run_id"]
    fit_run = fit["run_id"]
    rows_needed = math.ceil(ARM_BAR_PP / HEADROOM_SLU)

    # ---- the measurement declaration ------------------------------------
    measurement = {
        run_id: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "form-proof",
            "primary_metric": (
                "per-row intent correctness (official scorer's "
                "scenario_action_exact), reported as the conditional rate "
                "P(correct | newly delivered) with a binomial CI95"
            ),
            "rows": rows,
            "note": (
                "The cell measures a CONDITIONAL RATE and makes NO effectiveness "
                "claim. Its "
                + str(rows)
                + " rows are under the measurement instrument's MIN_BENEFIT_ROWS, so "
                "under rule 5 this is a form proof by size and claims_benefit is "
                "false; expected_effect_pp is 0.0 because the cell registers no "
                "effect to look for. What it delivers is the AGREE arm's unmeasured "
                "persuasion factor, measured: of the rows whose gold intent's "
                "boundary entry the agreement term newly delivers, the proportion "
                "that move from a wrong intent to the gold intent. Multiplying that "
                "proportion by the registered per-row headroom of the class the gain "
                "lands on gives the AGREE arm's re-declared expectation. It is NOT an "
                "admission request: no admission mode is declared, no harm margin is "
                "claimed, and no pooled or roster-level number may ever be read off "
                "this cell, whose population was selected with gold, offline."
            ),
        }
    }

    # ---- registered facts ------------------------------------------------
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the "
            "CANONICAL stage3_measurement block "
            "scripts/checks/stage3_effect_floor_check.py resolves. The same block is "
            "repeated in the preregistration's fenced json for readability; this copy "
            "has precedence."
        ),
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "rows": rows,
        "stage3_measurement": measurement,
        "the_unmeasured_quantity": {
            "name": "P(correct | newly delivered) -- the persuasion factor",
            "arm_declared_conversion": ARM_DECLARED_CONVERSION,
            "arm_declared_conversion_is": (
                "the product of a MEASURED P(correct | covered) of "
                + str(ARM_P_CORRECT_GIVEN_COVERED)
                + " (889 of 950 covered Fold A rows, itself an upper bound) and an "
                "UNMEASURED persuasion factor of "
                + str(ARM_PERSUASION)
                + ", which is the midpoint of [0, 1] and nothing more."
            ),
            "arm_declared_expectation_pp": ARM_DECLARED_PP,
            "arm_ceiling_at_perfect_conversion_pp": ARM_CEILING_PP,
            "arm_admission_bar_pp_at_n_1080": ARM_BAR_PP,
            "conversion_the_arm_needs": round(ARM_BAR_PP / ARM_CEILING_PP, 4),
            "rows_of_this_roster_that_would_clear_the_arm_bar": rows_needed,
            "why_measure_it_first": (
                "The AGREE arm plus its in-chain A/A costs about 7 GPU hours (2 x "
                "about 3.7) to learn this one number as a by-product of a read its own "
                "declaration does not expect to clear. This cell measures it directly "
                "for about "
                + format(4 * 0.1306, ".2f")
                + " GPU hours at the expected spend and at most "
                + str(caps["gpu_hours_fit_inclusive"])
                + " at the registered ceiling. The parent package names this option "
                "itself: 'measure the conversion first on a smaller probe and "
                "re-declare'."
            ),
            "the_only_directly_observable_prior": (
                "86 of the 191 intent-wrong Fold A rows ALREADY receive the gold "
                "intent's boundary entry in the sealed comparator and are intent-wrong "
                "anyway (the parent package's own measured_inputs), so the only "
                "directly observable conversion evidence on this population is zero. "
                "That is a reason to measure the factor, not a prediction of it, and "
                "this cell is registered without a predicted value on purpose."
            ),
        },
        "headroom_registered_by_the_parent": {
            "intent_pp_per_row": round(HEADROOM_INTENT, 6),
            "slu_pp_per_row": round(HEADROOM_SLU, 6),
            "source": (
                PARENT_PACKAGE
                + "/registered-facts-v1.json, expected_effect_derivation: "
                "INTENT-UNCOVERED perfect-repair headroom 5.41 pp SLU-F1 and 12.04 pp "
                "intent accuracy over 130 rows. Not re-derived here."
            ),
            "re_declaration_rule": (
                "the AGREE arm's re-declared expected_effect_pp = (rows of this roster "
                "that move from a wrong intent to the gold intent) x "
                + format(HEADROOM_SLU, ".6f")
                + " pp SLU-F1, and x "
                + format(HEADROOM_INTENT, ".6f")
                + " pp intent accuracy. Equivalently, "
                + str(ARM_CEILING_PP)
                + " pp x the measured conversion."
            ),
        },
        "roster": {
            "count": rows,
            "dataset_fragment": roster["dataset_fragment"],
            "derivation": {
                "relpath": ROSTER_DERIVATION,
                "sha256": hashlib.sha256(
                    Path(ROSTER_DERIVATION).read_bytes()
                ).hexdigest(),
            },
            "id_list_sha256": roster["id_list_sha256"],
            "split_identity_hash": roster["split_identity_hash"],
            "audio_seconds_total": roster["audio_seconds_total"],
            "proven_against": {
                "receipt_relpath": derivation["proof"]["receipt_relpath"],
                "receipt_sha256": derivation["proof"]["receipt_sha256"],
                "recipe_relpath": derivation["proof"]["recipe_relpath"],
                "recipe_sha256": derivation["proof"]["recipe_sha256"],
                "committed_plan_class_split": derivation["proof"][
                    "committed_plan_class_split"
                ],
                "reconstructed_plan_class_split": derivation["proof"][
                    "reconstructed_plan_class_split"
                ],
                "differences": derivation["proof"]["differences"],
                "note": (
                    "The committed receipt records the COUNT (70 newly delivered of 130 "
                    "INTENT-UNCOVERED, 0 lost) and carries NO row ids -- its own text "
                    "discipline chose counts. The roster is therefore RECONSTRUCTED from "
                    "that receipt's own recipe, imported byte-unchanged, and the "
                    "reconstruction is proven by reproducing every cell the receipt "
                    "committed for this arm at this width before a single id is taken."
                ),
            },
        },
        "gold_selection": GOLD_SELECTION,
        "no_pooled_claim": NO_POOLED_CLAIM,
        "why_intent_and_not_slu_f1": WHY_INTENT_NOT_SLU,
        "comparator": {
            "run_id": COMPARATOR_RUN,
            "attempt_id": COMPARATOR_ATTEMPT,
            "role": (
                "sealed, already flown, never re-flown and not part of this campaign. "
                "It holds these 70 rows' comparator answers, and every one of them is "
                "intent-WRONG there: INTENT-UNCOVERED collapses to INTENT-WRONG in the "
                "bad-case bank's own convention. The probe therefore flies the "
                "TREATMENT ONLY and the contrast is per-row and offline."
            ),
            "per_row_intent_verdict_authority": {
                "relpath": "analysis/SLURP-PLAN-BAD-CASE-BANK-V1/bank.jsonl",
                "sha256": derivation["population"]["sha256"],
                "note": (
                    "the same digest the committed replication receipt pinned as "
                    "bad_case_bank_sha256; the read re-derives the comparator's per-row "
                    "verdict from the sealed PLAN arm's own official score as well and "
                    "refuses on any disagreement."
                ),
            },
        },
        "identity": {
            "cell": cell["cell_id"],
            "experiment": EXPERIMENT,
            "run_id": run_id,
            "attempt_id": cell["attempt_id"],
            "fit_run_id": fit_run,
            "fit_attempt_id": fit["attempt_id"],
            "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"],
            "arm": composed.values["arm"],
            "composed_config_hash": composed.config_hash,
            "protocol_hash": phash,
            "split_identity_hash": split,
            "service_session": SESSION,
            "declares_prepared_phase_supply": "prepared_phase_supply"
            in composed.values,
            "boundary_channel": {
                "fuse_coverage": composed.values["knowledge_stores"][
                    "intent-boundaries"
                ]["phase_supply"]["perception"]["fuse_coverage"],
                "k": composed.values["knowledge_stores"]["intent-boundaries"][
                    "phase_supply"
                ]["perception"]["k"],
                "rank_weights": composed.values["knowledge_stores"][
                    "intent-boundaries"
                ]["phase_supply"]["perception"]["rank_weights"],
            },
            "native_episode_policies": {
                key: composed.values["native_episode"].get(key)
                for key in ("finite_completion_policy", "react_exhaustion_policy")
            },
        },
        "budget_arithmetic": {
            "contacts_per_row_program_ceiling": 11,
            "derivation": [
                "generation_calls_cap = "
                + str(rows)
                + " rows x 11 contacts per row (perception 1, solver 1, reviewer 3, "
                "planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1)) = "
                + str(caps["generation_calls_cap"]),
                "fit_endpoint_calls_cap = 4 x "
                + str(caps["generation_calls_cap"])
                + " = "
                + str(caps["fit_endpoint_calls_cap"])
                + ", the parent family's own ratio",
                "native_task_contract_calls_cap = "
                + str(rows)
                + " x 6 = "
                + str(caps["native_task_contract_calls_cap"])
                + ", the parent family's own per-row figure",
                "repeated_speech_audio_seconds_cap = ceil("
                + str(roster["audio_seconds_total"])
                + " roster seconds x 11) = "
                + str(caps["repeated_speech_audio_seconds_cap"]),
                "gpu_hours_fit_inclusive = "
                + str(caps["gpu_hours_fit_inclusive"])
                + ", a ceiling: the sealed PLAN arm's own 3.6819 h per 5,425 contacts "
                "puts the whole "
                + str(caps["generation_calls_cap"])
                + "-contact ceiling at about 0.52 h and the expected "
                + str(document["generation_budget"]["target"])
                + " contacts at about 0.24 h",
                "official_complete_scoring_jobs = 1, one job over the complete "
                + str(rows)
                + "-row manifest through core.scoring_batch, never sharded",
            ],
            "expected_contacts": document["generation_budget"]["target"],
            "family_budget": caps,
            "run_cumulative": (
                "every cap binds across ALL attempts of this run id, so the one "
                "permitted recovery re-registration spends from the same ceiling"
            ),
        },
        "authority_relpaths": [
            RANK_DIAGNOSTIC,
            INSTRUMENT,
            BAD_CASE_BANK_DOC,
            WITHIN_FLIGHT_NULL,
            PARENT_PACKAGE + "/README.md",
            PARENT_PACKAGE + "/production-replication-v1.json",
        ],
        "committed_artifacts": {
            "agreement_table": composed.values["knowledge_stores"][
                "intent-boundaries"
            ]["phase_supply"]["perception"]["agreement_source"],
            "note": (
                "The agreement table is pinned where the loader verifies it -- "
                "agreement_source.sha256 in the baseline -- plus its build receipt in "
                "preparation_source_receipts. It is deliberately NOT repeated as a "
                "readiness 'preparation' requirement: "
                "core.flight.repin._set_preparation_requirement rewrites EVERY such "
                "entry to the freshly minted first-phase supply pin at the flip, so a "
                "second preparation requirement would be silently clobbered. This "
                "cell's requirements list is empty and the flip appends exactly one."
            ),
            "prepared_phase_supply": (
                "NONE COMMITTED, by design. The agreement merge moved the "
                "implementation sha256 of rails.kb_policy, rails.knowledge_provider "
                "and rails.phase_supply, which FlightRuntime._phase_seed_inputs binds, "
                "so every prepared_phase_supply pin in the repository is invalidated "
                "and any cell awaiting a flip must be re-pinned. This cell carries no "
                "pin at all: the flip mints its own under its own run id (item E16) and "
                "--allow-output-change must never be passed."
            ),
        },
        "prohibitions": [
            "No pooled, roster-level, effectiveness, superiority or generalisation "
            "claim from this cell, ever -- its population was selected with gold.",
            "No admission entry and no admission mode: the cell claims nothing and "
            "asks for nothing.",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed comparator.",
            "No second factor, no w_agree, w_cos, w_prior, k, tau or fuse_coverage "
            "change, no store rebuild or release.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cell is flipped.",
        ],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    # ---- protocol --------------------------------------------------------
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-conv-fold-a-70-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": (
            "studies/speech-aware-evidence-acquisition, worktree "
            + args.worktree
            + ", branch "
            + args.branch
        ),
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": (
            "Of the "
            + str(rows)
            + " TRAIN Fold A rows whose own gold intent's boundary entry the agreement "
            "term newly delivers, how many move from a WRONG intent to the GOLD intent? "
            "That proportion is P(correct | newly delivered) -- the persuasion factor, "
            "the one term of the AGREE arm's declared expectation that is not measured."
        ),
        "one_factor": (
            "None. This cell changes NO factor: it is the registered AGREE treatment, "
            "byte-for-byte in every knob, flown on a smaller roster. The only "
            "differences from "
            + PARENT_ARM_RUN
            + " are the population (70 derived ids instead of 1,080) and the ceilings "
            "rescaled to it."
        ),
        "unchanged": (
            "the treatment (w_agree 1.0, w_cos 1.0, w_prior 0.0, k 60, tau 0.0, "
            "fuse_coverage m 8 / c 1 / top_l 8, the same pinned agreement table), the "
            "model fragment and serving geometry (np4 x 24,576), the session "
            + SESSION
            + ", the phase program and its 11-contact ceiling, all three knowledge "
            "stores and their release/snapshot pins, the exemplar k of 20, the role "
            "graph, the response formats, the instruction templates, the deliver "
            "normaliser and the scorers"
        ),
        "comparator": facts["comparator"],
        "cells": {
            "probe": {
                "cell": cell["cell_id"],
                "experiment": EXPERIMENT,
                "run_id": run_id,
                "attempt_id": cell["attempt_id"],
                "fit_run_id": fit_run,
                "fit_attempt_id": fit["attempt_id"],
                "composed_config_hash": composed.config_hash,
                "protocol_hash": phash,
                "split_identity_hash": split,
                "rows": rows,
                "declares_agreement_source": True,
                "boundary_rank_weights": facts["identity"]["boundary_channel"][
                    "rank_weights"
                ],
            }
        },
        "decision_rule_fixed_here": (
            "There is no verdict and no admission. The deliverable is a NUMBER: m, the "
            "count of the "
            + str(rows)
            + " rows whose intent verdict moves from wrong to gold, reported as m / "
            + str(rows)
            + " with a binomial CI95 (Wilson score interval, the exact Clopper-Pearson "
            "interval reported beside it), plus the reverse count -- which is zero by "
            "construction on this population, because every row is already intent-wrong "
            "in the comparator, and that structural zero is reported as a LIMIT of the "
            "cell rather than as a result. Beside it: how many rows stay wrong with a "
            "byte-identical answer versus a different wrong intent, and the flown "
            "delivery check (did the arm actually deliver the gold intent's boundary "
            "entry on all "
            + str(rows)
            + " rows the offline derivation says it would?). A delivery rate the "
            "derivation did not predict is an engineering defect, not a conversion "
            "measurement, and closes the read."
        ),
        "what_the_number_does": (
            "It re-declares the AGREE arm's expectation as arithmetic instead of a "
            "midpoint: expected_effect_pp = m x "
            + format(HEADROOM_SLU, ".6f")
            + " pp SLU-F1 (equivalently "
            + str(ARM_CEILING_PP)
            + " pp x m / "
            + str(rows)
            + "), and m x "
            + format(HEADROOM_INTENT, ".6f")
            + " pp intent accuracy. The arm clears its own 2.5 pp bar at n = 1,080 only "
            "if m >= "
            + str(rows_needed)
            + ". That is the decision this probe informs, and the probe itself decides "
            "nothing."
        ),
        "why_intent_and_not_slu_f1": WHY_INTENT_NOT_SLU,
        "gold_selection": GOLD_SELECTION,
        "no_pooled_claim": NO_POOLED_CLAIM,
        "why_no_in_chain_replicate": (
            "Rule 4 of the measurement instrument refuses a cross-flight CONTRAST with "
            "no in-chain replicate. This cell computes no cross-flight contrast: its "
            "measurement_design is form-proof, it claims no benefit, and the quantity "
            "it reports is a rate within its own flight, not a delta between flights. "
            "The comparator's contribution is a per-row verdict that is CONSTANT on "
            "this population -- wrong on all "
            + str(rows)
            + " rows -- so there is no between-flight offset for a replicate to null. "
            "An A/A at n = 70 would cost the same GPU hours again and measure nothing "
            "this read uses."
        ),
        "development_numbers_only": (
            "Every number this cell will produce is a TRAIN Fold A construction-fold "
            "development number (owner decisions 28 and 86) and is never a test claim."
        ),
        "failure_policy": (
            "Stop and preserve on the first failure. AT MOST ONE root-diagnosed "
            "recovery re-registration; a second failure closes the cell and the fix is "
            "proven on a four-row dry run. The budget is run-cumulative across attempts."
        ),
        "model_free_proofs_landed_before_contact": {
            "roster_derivation": facts["roster"]["derivation"],
            "roster_proof": facts["roster"]["proven_against"],
            "agreement_table": facts["committed_artifacts"]["agreement_table"],
        },
        "authority": (
            "the committed production-replication receipt "
            + PARENT_PACKAGE
            + "/production-replication-v1.json (sha256 "
            + derivation["proof"]["receipt_sha256"]
            + "), whose own expected-effect arithmetic names this conversion as the "
            "primary unknown and names measuring it on a smaller probe as the honest "
            "option; the model-free read "
            + RANK_DIAGNOSTIC
            + "; the measurement instrument "
            + INSTRUMENT
            + " (rule 5, the form-proof row); the within-flight null "
            + WITHIN_FLIGHT_NULL
            + " (0 intent flips in 200 request-identical rows); the class headroom of "
            + BAD_CASE_BANK_DOC
            + "; owner decisions 28 and 86 (development numbers) and 101 (the Stage-3 "
            "algorithm label)"
        ),
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    # ---- the two plan documents -----------------------------------------
    def plan_document(kind: str) -> dict:
        generation = kind == "generation"
        return {
            "schema": "saea-registered-" + kind + "-plan-v1",
            "plan_kind": kind,
            "cell": cell["cell_id"],
            "experiment": EXPERIMENT,
            "composed_config_hash": composed.config_hash,
            "execution_plan": {
                "attempt_id": cell["attempt_id"] if generation else fit["attempt_id"],
                "carrier_lock_key": composed.values["carrier_lock_key"],
                "execution_profile": document["execution_profile"],
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
                "planned_model_calls": caps["generation_calls_cap"]
                if generation
                else caps["fit_endpoint_calls_cap"],
                "planned_speech_audio_seconds": caps[
                    "repeated_speech_audio_seconds_cap"
                ],
                "protocol_hash": phash,
                "run_id": run_id if generation else fit_run,
                "schema": "saea-execution-plan-v1",
                "split_identity_hash": split,
                "split_role": "discovery",
                "study": "speech-aware-evidence-acquisition",
            },
            "execution_route": (
                "Shared core.flight.cli campaign over the committed campaign plan "
                "configs/campaign/slurp-native-stage3-conv-fold-a-70-v1.json, a "
                "single-cell chain; the campaign acquires its own GenerationLease "
                "against the resident session and schedules one official score over "
                "the complete manifest at finalize."
                if generation
                else "The shared core.flight.cli FIT path under this cell's own "
                "native_contact_fit ids; it measures request envelopes and produces "
                "no generation."
            ),
            "expected_session_id": SESSION,
            "family_budget": caps,
            "one_factor": protocol["one_factor"],
            "preparation_base_commit": args.study_commit,
            "prepared_phase_supply": {
                "note": facts["committed_artifacts"]["prepared_phase_supply"],
                "relpath": "prepared/" + run_id + "/phase-supply-v1.json",
                "sha256": "MINTED_AT_THE_FLIP",
            },
            "protocol_document": {
                "relpath": PACKAGE + "/protocol-registered-v1.json",
                "sha256": protocol_sha,
            },
            "purpose": (
                run_id
                + ": cell CONV, the conversion probe. "
                + protocol["decision_rule_fixed_here"]
                if generation
                else run_id + ": cell CONV. It measures request envelopes only and "
                "reads nothing."
            ),
            "quality_read_gate": (
                "No read before the complete sealed manifest, the exact ordered "
                "outputs, the native phase summary and the single successful complete "
                "official TRAIN score all exist for this cell, and before the flown "
                "delivery check agrees with the offline derivation on all "
                + str(rows)
                + " rows. A partial manifest is never scored and never read."
            ),
            "registered_at_utc": args.registered_at,
            "source_tree": protocol["source_tree"],
            "status": protocol["status"],
            "unused_budget_is_not_attempt_authority": True,
        }

    gen_sha = wjson(PACKAGE + "/generation-plan-registered-v1.json", plan_document("generation"))
    fit_sha = wjson(PACKAGE + "/fit-plan-registered-v1.json", plan_document("fit"))

    # ---- the analysis recipe --------------------------------------------
    recipe = {
        "schema": "saea-slurp-conditional-rate-recipe-v1",
        "recipe_id": "slurp-stage3-conv-fold-a-70-conditional-rate-v1",
        "title": (
            "Cell CONV -- P(correct | newly delivered), the AGREE arm's persuasion "
            "factor, measured"
        ),
        "registered_at_utc": args.registered_at,
        "arms": {
            "probe": {
                "run_id": run_id,
                "attempt_id": cell["attempt_id"],
                "outputs_sha256": "PENDING_SEAL",
                "run_manifest_sha256": "PENDING_SEAL",
                "scores_sha256": "PENDING_SEAL",
            },
            "comparator": facts["comparator"],
        },
        "roster": {
            "relpath": ROSTER_DERIVATION,
            "sha256": facts["roster"]["derivation"]["sha256"],
            "count": rows,
            "id_list_sha256": roster["id_list_sha256"],
        },
        "steps": [
            "1. Refuse unless the sealed manifest is COMPLETE at "
            + str(rows)
            + " rows and its ids equal the committed roster's ids exactly (compare the "
            "id-list sha256, not a count).",
            "2. Refuse unless the flown Perception consumption delivered the row's own "
            "gold intent boundary value id on all "
            + str(rows)
            + " rows -- the delivery check. The offline derivation predicts "
            + str(rows)
            + "; anything less is an engineering defect and closes the read with no "
            "conversion number.",
            "3. Score once over the complete manifest with the dataset's standard "
            "scorer (slurp-slu-official-train through core.scoring_batch, never "
            "sharded) and take ONE field per row: scenario_action_exact.",
            "4. Establish the comparator's per-row intent verdict two ways and refuse "
            "on any disagreement: from the bad-case bank (plan_class INTENT-UNCOVERED "
            "implies intent-wrong, digest pinned above) and from the sealed PLAN arm's "
            "own official score for the same sample ids.",
            "5. m = the count of rows whose probe verdict is exact and whose comparator "
            "verdict is not. r = the reverse count, which must be 0 because every "
            "comparator verdict on this roster is wrong; a non-zero r means the roster "
            "or the comparator was misread and closes the read.",
            "6. Report P(correct | newly delivered) = m / "
            + str(rows)
            + " with a Wilson score CI95 and the exact Clopper-Pearson CI95 beside it. "
            "No bootstrap: the quantity is a single binomial proportion.",
            "7. Report the companion split of the "
            + str(rows)
            + " - m rows that stay wrong: byte-identical answer versus a different "
            "wrong intent.",
            "8. Re-declare the AGREE arm's expectation as m x "
            + format(HEADROOM_SLU, ".6f")
            + " pp SLU-F1 and m x "
            + format(HEADROOM_INTENT, ".6f")
            + " pp intent accuracy, state whether m >= "
            + str(rows_needed)
            + " (the arm's own 2.5 pp bar at n = 1,080), and state in the same "
            "paragraph that this is a CONDITIONAL rate on a gold-selected roster and "
            "not a pooled effect.",
        ],
        "metrics": ["scenario_action_exact"],
        "interval": {
            "kind": "binomial",
            "primary": "Wilson score CI95",
            "reported_beside": "exact Clopper-Pearson CI95",
            "no_bootstrap_because": (
                "the estimand is one binomial proportion over independent rows, not a "
                "paired difference of pooled metrics"
            ),
        },
        "output": {
            "analysis_root": "analysis/SAEA-SLURP-STAGE3-CONV-FOLD-A-70-CONDITIONAL-RATE-V1"
        },
        "reported_beside_every_number": [
            "the flown delivery check against the offline derivation's " + str(rows),
            "the reverse count and the statement that it is zero by construction",
            "the stay-wrong split (byte-identical versus a different wrong intent)",
            "the re-declared AGREE expectation and the "
            + str(rows_needed)
            + "-row threshold",
            "GOLD-SELECTED ROSTER: conditional rate only, no pooled or roster-level "
            "claim, and this cell cannot see harm on already-correct rows",
        ],
        "boundary": (
            "A development read on a TRAIN construction fold (owner decisions 28 and "
            "86); never a test claim, never a generalisation claim, and it admits "
            "nothing by itself. No utterance text, transcript, gold label string, "
            "intent name as content or model output is printed or persisted: ids, "
            "counts, rates and hashes only."
        ),
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    # ---- README ----------------------------------------------------------
    readme = f"""# Cell CONV: the conversion from delivery to correctness

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; the cell is **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The one unmeasured quantity.** Cell AGREE's declared expectation of
{ARM_DECLARED_PP} pp SLU-F1 is a product: a **measured** delivery gain -- 70 newly delivered
`INTENT-UNCOVERED` rows of TRAIN Fold A, 0 lost -- times a conversion of {ARM_DECLARED_CONVERSION}, which is
itself a measured `P(correct | covered)` of {ARM_P_CORRECT_GIVEN_COVERED} times an **unmeasured persuasion
factor of {ARM_PERSUASION}**, the midpoint of `[0, 1]` and nothing more. Even at a perfect conversion the
arm's ceiling is {ARM_CEILING_PP} pp against a {ARM_BAR_PP} pp admission bar at n = 1,080, so it needs a
conversion of at least {round(ARM_BAR_PP / ARM_CEILING_PP, 4)}. This cell measures that factor directly, on exactly the
rows the gain lands on, for about a quarter of a GPU hour instead of the roughly seven the arm
plus its in-chain A/A would spend learning it as a by-product. The parent package names this
option itself.

**No new mechanism, no comparator flown.** Every knob is the registered AGREE arm's
(`w_agree` 1.0, `w_cos` 1.0, `w_prior` 0.0, `k` 60, `tau` 0.0, `fuse_coverage` m 8 / c 1 / top_l 8,
the same pinned agreement table, the same model fragment, geometry, session, program, stores,
role graph, templates, normaliser and scorers). Exactly two things differ, and both are roster
arithmetic: the population is the 70 derived ids, and every ceiling is rescaled to 70 rows. The
sealed PLAN arm `{COMPARATOR_RUN}` already holds these rows' answers and is
intent-**wrong** on every one of them, so the probe flies the **treatment only**.

**The roster, and the one thing that had to be checked first.** The committed replication receipt
`{PARENT_PACKAGE}/production-replication-v1.json`
(sha256 `{derivation["proof"]["receipt_sha256"]}`) records the **count** -- 70 newly delivered of 130
`INTENT-UNCOVERED`, 0 lost -- and carries **no row ids**: its own text discipline emits "an id, a
count, a rate or a hash" and it chose counts. The roster therefore cannot be read off the receipt.
It is **reconstructed** by importing that receipt's own recipe byte-unchanged
(`scripts/analysis/slurp_intent_agreement_production_replication.py`, sha256
`{derivation["proof"]["recipe_sha256"]}`)
and calling its own functions with its own parameters, and the reconstruction is **proven** before a
single id is taken: the whole delivery block, both boundary-channel pin blocks, the bank digest, the
builder digest, the sealed phase-artefact digest, the split identity and the roster row count all
reproduce **exactly** ({len(derivation["proof"]["differences"])} differences). Receipt:
[`roster-derivation-v1.json`](readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json) --
70 ids, id-list sha256 `{roster["id_list_sha256"]}`,
split identity `{split}`.

**The roster is selected using gold, offline.** That is legitimate for a *conditional* estimate on a
TRAIN roster and for nothing else. **No pooled or roster-level claim may ever be made from this
cell**, because its population was chosen by the mechanism's own effect. Gold reaches no query, no
key, no weight, no selector and no runtime. The cell also **cannot see harm**: every row here is
already intent-wrong in the comparator, so the rows where the mechanism could cost a correct intent
are outside this roster and remain the AGREE arm's own question.

**Why it reads intent, not SLU-F1.** The within-flight null
[`{WITHIN_FLIGHT_NULL}`](results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md)
measured **0 intent flips out of 200** request-identical rows, so an intent flip is attributable
rather than noise. Pooled SLU-F1's own noise would swamp 70 rows, and the official SLU-F1 is
entity-only while this mechanism acts on the intent. The official scorer still produces the number;
the read takes its per-sample `scenario_action_exact` and nothing else.

**The deliverable.** `P(correct | newly delivered)` = m / 70 with a binomial CI95, plus the reverse
count -- which is **zero by construction** on this population, reported as a limit of the cell and
not as a result. Multiplying the rate by the class's registered per-row headroom gives the AGREE
arm's re-declared expectation: m x {HEADROOM_SLU:.6f} pp SLU-F1 and m x {HEADROOM_INTENT:.6f} pp intent
accuracy. The arm clears its own bar only if **m >= {rows_needed}**.

**`stage3_measurement`.** 70 rows is under the measurement instrument's `MIN_BENEFIT_ROWS`, so the
design is `form-proof`, `claims_benefit` is **false** and `expected_effect_pp` is **0.0**; the note
says the cell measures a conditional rate and makes no effectiveness claim. **No `admission` mode is
declared**: that field is for a base item being admitted, and this cell is not asking for admission.

**`stage3_algorithm`.** `none`, with the parent's own reason: no rollout, no per-sample scoring, no
credit assignment, no update operator, no evolving store. A measurement of a factor is even less of
a policy search than the one-weight change it measures.

| file | what it holds |
| --- | --- |
| `../2026-09-26-slurp-stage3-conv-fold-a-70-v1-preregistration.md` | the preregistration proper, including the `stage3_measurement` fence |
| `roster-derivation-v1.json` | the 70 ids, and the proof they reproduce the committed receipt |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the read rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the cell's two plans |
| `analysis-recipe-v1.json` | how the conditional rate is read offline, step by step |

**Budgets, as arithmetic.** {caps["generation_calls_cap"]} generation contacts (70 x the program's own
11-contact ceiling, run-cumulative), {caps["fit_endpoint_calls_cap"]} FIT endpoints (4 x),
{caps["native_task_contract_calls_cap"]} native task-contract calls (70 x 6),
{caps["repeated_speech_audio_seconds_cap"]} repeated speech seconds
(ceil({roster["audio_seconds_total"]} x 11)), {caps["gpu_hours_fit_inclusive"]} GPU hour, one official
complete score. Expected spend: about {document["generation_budget"]["target"]} contacts and about
0.24 GPU hours at the sealed arm's own realized rate.

**No committed `prepared_phase_supply`, and an empty requirements list.** The agreement merge moved
the implementation sha256 of `rails.kb_policy`, `rails.knowledge_provider` and `rails.phase_supply`,
which `FlightRuntime._phase_seed_inputs` binds, so **every `prepared_phase_supply` pin in the
repository is invalidated** and any cell awaiting a flip must be re-pinned. This cell carries no pin:
the flip mints its own under its own run id (item E16) and `--allow-output-change` must never be
passed. The requirements list is empty for a second reason --
`core.flight.repin._set_preparation_requirement` rewrites **every** `kind == "preparation"` entry to
the freshly minted supply pin, so a second requirement would be silently clobbered. The agreement
table stays pinned where the loader verifies it: `agreement_source.sha256` in the baseline, plus its
build receipt in `preparation_source_receipts`.

**Mint, flip, queue.** Root mints the admission receipt with this cell's two eligible run ids
(`{run_id}`, `{fit_run}`) and this cell's caps, countersigns both
exposure rows, then re-pins with `scripts/flights/repin_cell.py --set-ready`.

**Not authorised by this package.** No flight before the receipt is minted and the cell is flipped;
no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV read;
no second factor; no pooled claim; no admission entry.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    # ---- the preregistration --------------------------------------------
    prereg = f"""# Cell CONV: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the
registered AGREE arm's own fragments by script (decision 58). Development numbers only (owner
decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | Of the {rows} TRAIN Fold A rows whose own gold intent's boundary entry cell AGREE newly delivers, how many move from a wrong intent to the gold intent? |
| treatment | the registered AGREE arm's, unchanged in every knob: `w_agree` 1.0, `w_cos` 1.0, `w_prior` 0.0, `k` 60, `tau` 0.0, `fuse_coverage` m 8 / c 1 / top_l 8, the same pinned agreement table |
| changed | the population ({rows} derived ids instead of 1,080) and the ceilings rescaled to it. Nothing else. |
| comparator | `{COMPARATOR_RUN}`, sealed, already flown, never re-flown, not in this campaign. Intent-**wrong** on all {rows} rows. |
| in-chain replicate | none, and none is owed: the design is `form-proof`, no cross-flight contrast is computed, and the comparator's per-row verdict is constant on this population |
| runs | `{run_id}` / `{fit_run}` |
| rows | {rows} |
| composed config hash | `{composed.config_hash}` |
| protocol hash | `{phash}` |
| split identity | `{split}` |
| id-list sha256 | `{roster["id_list_sha256"]}` |
| authority | the committed replication receipt `{PARENT_PACKAGE}/production-replication-v1.json` (sha256 `{derivation["proof"]["receipt_sha256"]}`); {RANK_DIAGNOSTIC}; {INSTRUMENT} (rule 5); {WITHIN_FLIGHT_NULL}; {BAD_CASE_BANK_DOC}; owner decisions 28, 86 and 101 |

## The read rule (fixed here)

There is no verdict and no admission. m = the count of the {rows} rows whose official
`scenario_action_exact` is true and whose comparator verdict is not. The deliverable is
`P(correct | newly delivered)` = m / {rows} with a Wilson score CI95 and the exact Clopper-Pearson
interval beside it, plus the reverse count -- **zero by construction**, because every comparator
verdict on this roster is wrong; a non-zero reverse count means the roster or the comparator was
misread and closes the read. Reported beside it: the flown delivery check against the offline
derivation's {rows}, and the split of the stay-wrong rows into byte-identical versus a different
wrong intent.

Multiplying the rate by the class's registered per-row headroom re-declares the AGREE arm's
expectation: m x {HEADROOM_SLU:.6f} pp SLU-F1 and m x {HEADROOM_INTENT:.6f} pp intent accuracy, equivalently
{ARM_CEILING_PP} pp x m / {rows}. The arm clears its own {ARM_BAR_PP} pp bar at n = 1,080 only if **m >= {rows_needed}**.

## The measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)}
```

`{rows}` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof
by size: `form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. **No `admission` mode is
declared** -- `no-harm` is owner decision 127's mode for a base item being admitted, and this cell
asks for no admission at all.

## What the roster is, and what selecting it with gold costs

{GOLD_SELECTION}

{NO_POOLED_CLAIM}

The roster is reconstructed, not read off the receipt: the committed replication receipt carries the
count and no ids, so `scripts/analysis/slurp_intent_agreement_conversion_roster.py` imports that
receipt's own recipe byte-unchanged and proves the reconstruction by reproducing every count,
histogram and digest the receipt committed for this arm at this width -- {len(derivation["proof"]["differences"])} differences -- before a
single id is taken.

## Why intent, not SLU-F1

{WHY_INTENT_NOT_SLU}

## Budgets and failure rule

{caps["generation_calls_cap"]} generation contacts (run-cumulative; {rows} x the program's own 11-contact
ceiling), {caps["fit_endpoint_calls_cap"]} FIT endpoints, {caps["repeated_speech_audio_seconds_cap"]} repeated
speech seconds, {caps["gpu_hours_fit_inclusive"]} GPU hour, one official complete score. Expected spend about
{document["generation_budget"]["target"]} contacts and about 0.24 GPU hours at the sealed arm's own realized
rate. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a
second failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No pooled, roster-level, effectiveness, superiority or generalisation claim from this cell, ever. No
admission entry and no admission mode. No paper-scale profile. No confirmatory or test-split
contact. No Fold B or DEV read. No re-flying of the sealed comparator. No second factor and no knob
change. No store rebuild or release. No flight before root mints the decision receipt and the cell
is flipped, and `--allow-output-change` is never passed.
"""
    prereg_sha = wr(PREREG, prereg)

    # ---- the two exposure rows ------------------------------------------
    ledger_state = "already-present"
    if args.append_ledger:
        ledger_state = append_ledger(
            args,
            rows=rows,
            run_id=run_id,
            fit_run=fit_run,
            cell=cell,
            fit=fit,
            caps=caps,
            composed_hash=composed.config_hash,
            phash=phash,
            split=split,
            roster=roster,
            plan_shas={"generation": gen_sha, "fit": fit_sha},
            expected_contacts=document["generation_budget"]["target"],
            rows_needed=rows_needed,
        )

    print(
        json.dumps(
            {
                "package": PACKAGE,
                "written": {
                    PACKAGE + "/README.md": readme_sha,
                    PACKAGE + "/analysis-recipe-v1.json": recipe_sha,
                    PACKAGE + "/fit-plan-registered-v1.json": fit_sha,
                    PACKAGE + "/generation-plan-registered-v1.json": gen_sha,
                    PACKAGE + "/protocol-registered-v1.json": protocol_sha,
                    PACKAGE + "/registered-facts-v1.json": facts_sha,
                    PREREG: prereg_sha,
                },
                "exposure_ledger": ledger_state,
                "identity": {
                    "run_id": run_id,
                    "fit_run_id": fit_run,
                    "attempt_id": cell["attempt_id"],
                    "fit_attempt_id": fit["attempt_id"],
                    "composed_config_hash": composed.config_hash,
                    "protocol_hash": phash,
                    "split_identity_hash": split,
                    "rows": rows,
                    "rows_needed_to_clear_the_arm_bar": rows_needed,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
