#!/usr/bin/env python3
"""Write the AGREE registration package and its exposure rows, in dependency order.

Three cells (the AGREE arm, its four-row form smoke, and the in-chain A/A
replicate), six run ids with their FIT twins, one campaign plan already written
by ``derive_slurp_agree_cells.py``, one readiness package, one preregistration
and eight exposure-ledger rows -- six unconsumed flight rows plus two model-free
rows for the pre-computations this registration performed.

IT PERFORMS NO CONTACT. It opens no attempt, starts no server, mints no decision
receipt, flips no readiness and authorises nothing. Every hash it writes is
recomputed and rewritten by ``scripts/flights/repin_cell.py --set-ready`` at the
coordinator's flip, whose own ``core.flight.cli check`` then refuses unless the
two agree.

WHY THE HASHES ARE COMPUTED HERE RATHER THAN READ FROM ``check``. The exposure
gate refuses a model touch for a run with no pre-registered ledger row, and
``check`` walks that gate -- so at registration time ``check`` cannot run until
the rows exist, and the rows carry the plan digests. The composed-config and
protocol hashes are therefore computed from config alone
(``scripts/flights/print_slurp_agree_identities.py`` prints the same values), the
rows are written, and ``check`` is run afterwards as the verification step.

Idempotent: re-running it rewrites the same package and replaces its own ledger
rows rather than appending duplicates.

    python scripts/flights/write_slurp_agree_registration.py \
        --date 2026-09-26 --commit <study commit> \
        --gain-uncovered N --gain-covered N --loss-uncovered N --loss-covered N \
        --replication-receipt-sha256 <64 hex>
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

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)

PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
LEDGER = "docs/exposure-ledger.md"
DIAGNOSTIC = "docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
BANK_READ = "docs/results/2026-09-24-slurp-plan-bad-case-bank.md"

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
COMPARATOR_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
COMPARATOR_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
COMPARATOR_OFFICIAL = {"slu_f1": 63.6304, "intent_accuracy": 82.2222}
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
AGREEMENT_SHA = "018ca6ef0d10bbf8d19645994420820faf7f31961cf91a6080116e4b434016c1"
AGREEMENT_RECEIPT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json"
AGREEMENT_RECEIPT_SHA = "abf1830e3b765ce267ca7abc30855fb0148190931a12d505dc0f6f1dccd5ee2b"
AGREEMENT_LEDGER_ROW = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1"
REPLICATION_LEDGER_ROW = "SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1"
REPLICATION_RELPATH = (
    "analysis/SAEA-SLURP-INTENT-AGREEMENT-PRODUCTION-REPLICATION-V1/replication-v1.json"
)
IDENTITY_PROOF_RELPATH = "analysis/SAEA-SLURP-AGREE-PROOFS-V1/identity-proof-v1.json"

#: The bad-case bank's own Fold A class counts (``BANK_READ`` section 1). The
#: expected-effect arithmetic is anchored on them, so they are asserted, not
#: assumed: the replication receipt must report exactly these.
FOLD_A_UNCOVERED = 130
FOLD_A_COVERED = 61
#: The bank's measured headroom of a PERFECT repair of each class, in official
#: pooled SLU-F1 points on the 1,080-row Fold A roster (``BANK_READ`` section 8).
HEADROOM_UNCOVERED_SLU = 5.41
HEADROOM_COVERED_SLU = 2.35
HEADROOM_UNCOVERED_INTENT = 12.04
HEADROOM_COVERED_INTENT = 5.65
#: THE CONVERSION, decomposed into the one factor that is measured and the one
#: that is not.
#:
#: ``P_CORRECT_GIVEN_COVERED`` -- measured, and an UPPER BOUND. Of the 1,080 Fold
#: A rows, 889 answer the intent correctly and 61 more had the gold intent in
#: Perception's own candidate list and still delivered another
#: (``BANK_READ`` section 1), so at most 889 of 950 covered rows are correct:
#: 93.58 %. It is an upper bound because a correct row is ASSUMED to have had its
#: gold intent covered, which the bank's classes imply but do not separately
#: measure.
#:
#: ``PERSUASION`` -- NOT MEASURED, and the whole unknown. The probability that
#: Perception proposes an intent it did not propose before, given that the
#: intent's written boundary description is now among the eight entries it
#: receives. Nothing measures it. Note what makes it genuinely uncertain rather
#: than merely unmeasured: Perception already carries the FULL 60-label inventory
#: in its task contract (``task_instruction_fill`` = slurp-label-inventory), so
#: the boundary entries are EVIDENCE, not the candidate menu. This change does
#: not unlock an intent that was unreachable; it argues for one that was already
#: nominally available. The effect is persuasion, and its size is unknown.
P_CORRECT_GIVEN_COVERED = 889 / 950
PERSUASION = 0.5
CONVERSION = PERSUASION * P_CORRECT_GIVEN_COVERED

CELLS = {
    "arm": "slurp-native-stage3-agree-w1-fold-a-v1",
    "smoke": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1",
    "aa": "slurp-native-stage3-agree-aa-fold-a-v1",
}
FLIGHT_PROSE = {
    "arm": "Cell AGREE",
    "smoke": "Four-row form smoke of cell AGREE",
    "aa": "The in-chain A/A replicate of cell AGREE",
}


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def dump(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def identities(repo: Path) -> dict:
    out = {}
    for key, experiment in CELLS.items():
        document = json.loads(
            (repo / "configs" / "experiment" / f"{experiment}.json").read_text(
                encoding="utf-8"
            )
        )
        cell = document["cells"][0]
        composed = compose(
            repo,
            cell["model_fragment"],
            cell["dataset_fragment"],
            cell["baseline_fragment"],
            experiment,
        )
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "experiment": experiment,
            "cell": cell["cell_id"],
            "run_id": cell["run_id"],
            "attempt_id": cell["attempt_id"],
            "arm": composed.values["arm"],
            "rows": document["population"]["count"],
            "split_identity_hash": split,
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(
                composed.config_hash, composed.values["arm"], split
            ),
            "fit": dict(composed.values["native_contact_fit"]),
            "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"],
            "prepared_phase_supply": next(
                requirement
                for requirement in cell["readiness"]["requirements"]
                if requirement["relpath"].endswith("phase-supply-v1.json")
            ),
            "rank_weights": composed.values["knowledge_stores"]["intent-boundaries"][
                "phase_supply"
            ]["perception"]["rank_weights"],
            "declares_agreement_source": "agreement_source"
            in composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"][
                "perception"
            ],
        }
    return out


def _expected_effect(args: argparse.Namespace) -> dict:
    """The ``expected_effect_pp`` arithmetic, stated so a reader can refuse it.

    EVERY INPUT IS MEASURED EXCEPT ONE, and the one that is not is named.

      * ``gain_uncovered`` / ``gain_covered``: how many INTENT-UNCOVERED and
        INTENT-COVERED Fold A rows newly receive their own gold intent's
        boundary entry at ``w_agree`` 1.0, counted through the production path
        (the replication receipt this registration pins).
      * ``HEADROOM_*``: the bad-case bank's measured upper bound on a PERFECT
        repair of each class, on this exact roster.
      * ``P_CORRECT_GIVEN_COVERED``: measured, an upper bound (see its own
        comment above).
      * ``PERSUASION``: NOT MEASURED, and it is the whole unknown. Two things
        bear against assuming it is large. First, of the 191 Fold A rows that
        answer the intent wrongly today, 86 (45.0 %) ALREADY receive their gold
        intent's boundary entry and are wrong anyway -- so on this population
        delivery is demonstrably insufficient wherever it can be observed at
        all. Second, Perception already holds the full 60-label inventory in its
        task contract, so this change supplies EVIDENCE for an intent rather
        than admitting one to a closed menu. The association the read does
        report -- correct rows hold the gold intent at rank 1 and inside the top
        8 on 94.5-97.3 % of them -- is an association on the rows that already
        worked, not a causal rate, and the boundary cosine that produces it also
        tracks how clearly the utterance was spoken.

    WHAT IS NEWLY MEASURED, AND WHY IT MATTERS. Every one of the 70 rows that
    gains delivery is an INTENT-UNCOVERED row -- the coverage-failure class, the
    only class a coverage repair can act on -- 70 of that class's 130 rows.
    INTENT-COVERED is a 2-for-2 wash, correctly, because delivery was never the
    binding constraint there. So the change is well targeted, and the arithmetic
    below charges it only against the class it actually moves.

    SO THE DECLARED NUMBER IS A CONSTRUCTION, NOT A PREDICTION. The persuasion
    factor is set to the midpoint of the only interval anything bounds,
    ``[0, 1]``, because no measurement narrows it. The ceiling at persuasion 1
    and the whole sweep are reported beside it so the declaration cannot be
    mistaken for evidence. If the true persuasion is lower, this cell reads
    NEUTRAL by width, and that is a legitimate outcome of a correctly designed
    measurement, not a failure of the registration.
    """

    per_uncovered = HEADROOM_UNCOVERED_SLU / FOLD_A_UNCOVERED
    per_covered = HEADROOM_COVERED_SLU / FOLD_A_COVERED
    per_uncovered_intent = HEADROOM_UNCOVERED_INTENT / FOLD_A_UNCOVERED
    per_covered_intent = HEADROOM_COVERED_INTENT / FOLD_A_COVERED
    net_uncovered = args.gain_uncovered - args.loss_uncovered
    net_covered = args.gain_covered - args.loss_covered
    ceiling_slu = net_uncovered * per_uncovered + net_covered * per_covered
    ceiling_intent = (
        net_uncovered * per_uncovered_intent + net_covered * per_covered_intent
    )
    sweep = {
        f"persuasion {rate:g}": round(ceiling_slu * rate * P_CORRECT_GIVEN_COVERED, 4)
        for rate in (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)
    }
    return {
        "measured_inputs": {
            "fold_a_rows": 1080,
            "intent_wrong_rows": FOLD_A_UNCOVERED + FOLD_A_COVERED,
            "intent_uncovered_rows": FOLD_A_UNCOVERED,
            "intent_covered_rows": FOLD_A_COVERED,
            "newly_delivered_uncovered": args.gain_uncovered,
            "newly_delivered_covered": args.gain_covered,
            "newly_undelivered_uncovered": args.loss_uncovered,
            "newly_undelivered_covered": args.loss_covered,
            "perfect_repair_headroom_slu_pp": {
                "intent_uncovered": HEADROOM_UNCOVERED_SLU,
                "intent_covered": HEADROOM_COVERED_SLU,
            },
            "perfect_repair_headroom_intent_pp": {
                "intent_uncovered": HEADROOM_UNCOVERED_INTENT,
                "intent_covered": HEADROOM_COVERED_INTENT,
            },
            "where_the_gain_lands": (
                "ALL 70 of the intent-wrong delivery gain lands on INTENT-UNCOVERED -- "
                "the coverage-failure class, the only class a coverage repair can act "
                "on -- 70 of its 130 rows (53.8 %). INTENT-COVERED is a 2-for-2 wash, "
                "correctly, because delivery was never the binding constraint there. "
                "Only 4 rows in the whole 1,080-row roster lose delivery and all four "
                "are inside INTENT-COVERED. The arithmetic below therefore charges the "
                "change only against the class it actually moves."
            ),
            "already_delivered_and_still_intent_wrong": {
                "rows": 86,
                "of_intent_wrong_rows": 191,
                "rate_pct": 45.0,
                "what_it_bounds": (
                    "the only directly observable conversion evidence on this "
                    "population, and it is zero: every row in this group receives "
                    "the gold intent's boundary entry and is intent-wrong anyway"
                ),
            },
        },
        "arithmetic": [
            f"per-row SLU headroom, INTENT-UNCOVERED = {HEADROOM_UNCOVERED_SLU} / "
            f"{FOLD_A_UNCOVERED} = {per_uncovered:.6f} pp",
            f"per-row SLU headroom, INTENT-COVERED   = {HEADROOM_COVERED_SLU} / "
            f"{FOLD_A_COVERED} = {per_covered:.6f} pp",
            f"net newly delivered: {net_uncovered} uncovered, {net_covered} covered",
            f"ceiling at conversion 1.0 = {net_uncovered} x {per_uncovered:.6f} + "
            f"{net_covered} x {per_covered:.6f} = {ceiling_slu:.4f} pp SLU-F1",
            f"conversion = persuasion {PERSUASION:g} (UNMEASURED) x "
            f"P(correct | covered) {P_CORRECT_GIVEN_COVERED:.4f} (measured, an upper "
            f"bound: 889 of 950) = {CONVERSION:.4f}",
            f"declared expectation = {ceiling_slu:.4f} x {CONVERSION:.4f} = "
            f"{ceiling_slu * CONVERSION:.4f} pp SLU-F1",
        ],
        "conversion_rate": {
            "value": round(CONVERSION, 6),
            "persuasion_factor": PERSUASION,
            "p_correct_given_covered": round(P_CORRECT_GIVEN_COVERED, 6),
            "status": (
                "ONE MEASURED FACTOR (an upper bound) TIMES ONE UNMEASURED FACTOR. "
                "The unmeasured one is the whole unknown."
            ),
            "why_this_value": (
                "P(correct | covered) is measured at 889 of 950 covered Fold A rows, "
                "an upper bound. The persuasion factor is the midpoint of [0, 1], the "
                "only interval any evidence bounds; it is not reverse-engineered from "
                "any admission bar and it is deliberately not the ceiling. Perception "
                "already holds the full 60-label inventory in its task contract, so "
                "this change argues for an intent rather than admitting one -- which "
                "is why the persuasion factor cannot be inferred from the coverage "
                "counts."
            ),
        },
        "ceiling_at_perfect_conversion_pp": {
            "slu_f1": round(ceiling_slu, 4),
            "intent_accuracy": round(ceiling_intent, 4),
        },
        "sweep_slu_pp_by_conversion": sweep,
        "expected_effect_pp": round(ceiling_slu * CONVERSION, 4),
        "expected_intent_effect_pp": round(ceiling_intent * CONVERSION, 4),
        "honest_statement": (
            "DELIVERY IS NOT CORRECTNESS. Every measured quantity above is a count "
            "of rows that would RECEIVE their own gold intent's boundary entry; not "
            "one of them is a count of rows that would then ANSWER correctly. The "
            "conversion between the two is unmeasured, so the declared "
            "expected_effect_pp is a construction. It is stated at the midpoint "
            "conversion and is reported beside its own ceiling and its whole sweep. "
            "It is not a prediction, it is not evidence, and it must not be read as "
            "either."
        ),
    }


def write_package(repo: Path, args: argparse.Namespace, ids: dict) -> list[str]:
    written: list[str] = []
    effect = _expected_effect(args)
    floor_at_1080 = 2.5
    clears = effect["expected_effect_pp"] >= floor_at_1080

    # ---- 1. the protocol -------------------------------------------------
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-agree-w1-fold-a-protocol-v1",
        "registered_at_utc": f"{args.date}T12:00:00.000000+00:00",
        "study_commit_at_registration": args.commit,
        "source_tree": (
            "studies/speech-aware-evidence-acquisition, worktree "
            "/home/chao/saea-worktrees/fable-agree, branch fable/agree"
        ),
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "authority": (
            f"the model-free read {DIAGNOSTIC} (sections 2, 3, 5 and 6); the "
            f"measurement instrument {INSTRUMENT} (rules 3 and 4); the class "
            f"headroom of {BANK_READ} (sections 1 and 8); owner decisions 28 and 86 "
            "(development numbers), 101 (the Stage-3 algorithm label) and 110"
        ),
        "one_factor": (
            "The intent-boundary Perception channel reads its own registered w_agree "
            "term over a pre-computed, self-excluded exemplar-intent vote: w_agree "
            "1.0, w_cos unchanged at 1.0, w_prior unchanged at 0.0, and the DELIVERED "
            "width unchanged at 8 entries (fuse_coverage m 8 / c 1 / top_l 8). The "
            "RECALL width k moves from 8 to the store's full 60, because k is the "
            "provider's top_k_per_dimension and truncates by cosine BEFORE the ranker "
            "runs -- at 8 the agreement term is inert, measured. The widening is a "
            "proven no-op on its own: the in-chain A/A control carries k 60 at w_agree "
            "0.0 and reproduces the sealed comparator's first-phase output digest AND "
            "its rendered request bytes exactly, so the two arms differ in w_agree "
            "alone. Nothing else moves."
        ),
        "why_w_prior_is_untouched": (
            "It is DEAD on this channel, not merely zeroed. Measured on the released "
            "snapshot, 0 of the 60 boundary values carry a prior_score and 0 carry a "
            "task_target, and the channel recalls one dimension, intent-boundary, "
            "which is not in rails.kb_policy.PRIOR_MASS_DIMENSIONS -- so max_prior is "
            "0.0 for every candidate on every row and w_prior has no effect at any "
            "value. Turning it on would be a store rebuild, and the offline "
            "simulation showed it destroys correct rows above 0.15. This cell does "
            "not touch it and no config here implies it works."
        ),
        "why_the_delivered_width_is_not_widened": (
            "The missing gold intents are not bunched just outside the window; they "
            "are spread down the whole tail (Fold A: 37 % at ranks 9-16, 32 % at "
            "17-30, 28 % at 31-60, 3 % unrankable), so a delivered width of 16 leaves "
            "over two thirds still missing on every roster. The nearest width that "
            "buys the same delivery, 30, costs +3,262.3 tokens per row against this "
            "change's +1.4 -- about 2,330 times the form cost, and that added form is "
            "exactly what sank the index arm at SLU -7.37. The delivered width stays "
            "at 8 (fuse_coverage m 8 / c 1 / top_l 8), and the flown block still "
            "carries eight entries: the measured selected-value count is 8,624 on both "
            "arms, identical."
        ),
        "why_the_recall_width_does_move": (
            "PhaseSupplySpec.k is the provider's top_k_per_dimension, so the RECALL "
            "truncates to the top k BY COSINE before the ranker is called. At k = 8 "
            "the agreement term can only permute the eight the cosine already chose "
            "and cannot reach a gold intent at rank 9-60 -- which is the entire "
            "population the read measured. MEASURED, and this is why the brief's "
            "'k left at 8' had to be corrected: at k = 8 the treatment is INERT, "
            "wrong-row delivery 45.0 % -> 45.0 % on all three rosters. The recall "
            "width therefore moves to the store's full 60, which is the width the "
            "read's own simulation used. The delivered width is unchanged, because "
            "KbFacetProvider.fuse reads the full RankResult and its own FuseKnobs, "
            "never k. AND THE WIDENING IS A PROVEN NO-OP ON ITS OWN: the in-chain A/A "
            "control carries k = 60 at w_agree 0.0 and its own prepared first-phase "
            "supply reproduces the sealed comparator's output digest "
            f"{PLAN_SUPPLY_OUTPUT_SHA} exactly, on all 1,080 rows. The two arms "
            "therefore differ in w_agree alone."
        ),
        "unchanged": (
            "the roster (TRAIN Fold A 1,080, split identity "
            f"{ids['arm']['split_identity_hash']}), the serving geometry (np4 x "
            "24,576), the session, the phase program and its 11-contact ceiling, all "
            "three knowledge stores and their release/snapshot pins, the exemplar k "
            "of 20, the role graph, the response formats, the instruction templates, "
            "the deliver normaliser, the scorers, and every budget"
        ),
        "cells": {
            key: {
                "cell": ids[key]["cell"],
                "experiment": ids[key]["experiment"],
                "run_id": ids[key]["run_id"],
                "attempt_id": ids[key]["attempt_id"],
                "rows": ids[key]["rows"],
                "composed_config_hash": ids[key]["composed_config_hash"],
                "protocol_hash": ids[key]["protocol_hash"],
                "split_identity_hash": ids[key]["split_identity_hash"],
                "fit_run_id": ids[key]["fit"]["run_id"],
                "fit_attempt_id": ids[key]["fit"]["attempt_id"],
                "boundary_rank_weights": ids[key]["rank_weights"],
                "declares_agreement_source": ids[key]["declares_agreement_source"],
            }
            for key in CELLS
        },
        "comparator": {
            "run_id": COMPARATOR_RUN,
            "attempt_id": COMPARATOR_ATTEMPT,
            "official": COMPARATOR_OFFICIAL,
            "never_reflown": True,
            "in_chain_replicate": {
                "run_id": ids["aa"]["run_id"],
                "why": (
                    "A cross-flight contrast against an older sealed comparator with "
                    "no in-chain replicate is refused outright by the measurement "
                    "instrument's rule 4: a pure A/A pair at n = 625 read +1.87 pp "
                    "with a CI95 that excludes zero. The A/A cell is the locked "
                    "plan's own form re-flown in the SAME campaign chain, so the "
                    "treatment delta is read against a within-chain null."
                ),
            },
            "margins": {
                "h_slu": 1.2485,
                "h_intent": 0.9943,
                "source": (
                    "the plan's own null on this roster, cell PLANr "
                    "(SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1)"
                ),
            },
        },
        "decision_rule_fixed_here": (
            "NEUTRAL: both guards non-inferior at the plan's own null -- the CI95 "
            "lower bound of the paired official pooled SLU-F1 delta above -h_slu and "
            "of the intent delta above -h_intent, each measured against the IN-CHAIN "
            "A/A arm, not against the sealed comparator alone. ADMITTED: NEUTRAL and "
            "the SLU CI95 lower bound above zero against the in-chain A/A. HARMFUL: "
            "a measured loss on either guard (decision 25). Every verdict carries the "
            "per-stratum table in both weightings, the frontier row (decision 75), "
            "the delivery-rate check (did the flown arm deliver the gold intent's "
            "boundary entry on the rows the offline replication says it would?) and "
            "the measured token delta."
        ),
        "what_a_neutral_read_would_mean": (
            "That delivery does not convert to correctness at a rate this design can "
            "see -- which is mode (iv) of the read, delivered but ignored or misused, "
            "and is the programme's next question rather than a defect of this cell. "
            "It must be reported as such and never as 'no gain'."
        ),
        "model_free_proofs_landed_before_contact": {
            "default_byte_identity": {
                "claim": (
                    "At w_agree 0.0 with no agreement_source, the first-phase "
                    "selection this implementation prepares is byte-identical to the "
                    "selection the sealed comparator flew, on all 1,080 rows."
                ),
                "sealed_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                "recomputed_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                "treatment_output_sha256": args.treatment_output_sha256,
                "receipt": f"{PACKAGE}/identity-proof-v1.json",
            },
            "production_path_replication": {
                "claim": (
                    "The production path reproduces the diagnostic's own delivery "
                    "numbers on all three rosters."
                ),
                "receipt_relpath": REPLICATION_RELPATH,
                "receipt_sha256": args.replication_receipt_sha256,
                "package_copy": f"{PACKAGE}/production-replication-v1.json",
            },
            "agreement_artifact": {
                "relpath": AGREEMENT_RELPATH,
                "sha256": AGREEMENT_SHA,
                "receipt_relpath": AGREEMENT_RECEIPT_RELPATH,
                "receipt_sha256": AGREEMENT_RECEIPT_SHA,
            },
        },
        "prohibitions": (
            "No paper-scale profile. No confirmatory or test-split contact. No Fold B "
            "or DEV read from this cell. No re-flying of the sealed comparator. No "
            "second factor. No w_prior change. No k change. No store rebuild or "
            "release. No admission entry from this registration, and no flight before "
            "root mints the decision receipt and all three cells are flipped."
        ),
        "failure_policy": (
            "Stop and preserve on the first failure. AT MOST ONE root-diagnosed "
            "recovery re-registration; a second failure closes the cell and the fix "
            "is proven on a four-row dry run."
        ),
        "development_numbers_only": (
            "Every number this cell will produce is a TRAIN Fold A construction-fold "
            "development number (owner decisions 28 and 86) and is never a test claim."
        ),
    }
    protocol_text = dump(protocol)
    wr(f"{PACKAGE}/protocol-registered-v1.json", protocol_text)
    written.append(f"{PACKAGE}/protocol-registered-v1.json")
    protocol_sha = sha_text(protocol_text)

    # ---- 2. the six plan documents --------------------------------------
    plan_files: dict[str, str] = {}
    for key in ("arm", "smoke", "aa"):
        identity = ids[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            budget = identity["family_budget"]
            plan = {
                "schema": f"saea-registered-{kind}-plan-v1",
                "plan_kind": kind,
                "cell": identity["cell"],
                "experiment": identity["experiment"],
                "composed_config_hash": identity["composed_config_hash"],
                "registered_at_utc": f"{args.date}T12:00:00.000000+00:00",
                "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
                "source_tree": (
                    "studies/speech-aware-evidence-acquisition, worktree "
                    "/home/chao/saea-worktrees/fable-agree, branch fable/agree"
                ),
                "preparation_base_commit": args.commit,
                "expected_session_id": SESSION,
                "unused_budget_is_not_attempt_authority": True,
                "execution_plan": {
                    "schema": "saea-execution-plan-v1",
                    "study": "speech-aware-evidence-acquisition",
                    "carrier_lock_key": "slurp",
                    "run_id": identity["fit"]["run_id"] if is_fit else identity["run_id"],
                    "attempt_id": (
                        identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
                    ),
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "discovery",
                    "split_identity_hash": identity["split_identity_hash"],
                    "protocol_hash": identity["protocol_hash"],
                    "planned_model_calls": (
                        budget["fit_endpoint_calls_cap"]
                        if is_fit
                        else budget["generation_calls_cap"]
                    ),
                    "planned_speech_audio_seconds": budget[
                        "repeated_speech_audio_seconds_cap"
                    ],
                    "planned_gpu_hours": budget["gpu_hours_fit_inclusive"],
                },
                "family_budget": budget,
                "execution_route": (
                    "The shared core.flight.cli FIT path under this cell's own "
                    "native_contact_fit ids; it measures request envelopes and "
                    "produces no generation."
                    if is_fit
                    else (
                        "Shared core.flight.cli campaign over the committed campaign "
                        "plan configs/campaign/slurp-native-stage3-agree-w1-fold-a-v1"
                        ".json, which carries the A/A replicate AND the AGREE arm so "
                        "the two fly in ONE chain; the campaign acquires its own "
                        "GenerationLease against the resident session and schedules "
                        "one official score per generation cell at finalize."
                        if key != "smoke"
                        else (
                            "Shared core.flight.cli worker on this cell alone; the "
                            "smoke is deliberately outside the campaign plan and is "
                            "never scored."
                        )
                    )
                ),
                "prepared_phase_supply": {
                    "relpath": identity["prepared_phase_supply"]["relpath"],
                    "sha256": identity["prepared_phase_supply"]["sha256"],
                    "note": (
                        "THIS CELL'S OWN artifact, built model-free under its own run "
                        "id by core.flight.cli prepare-supply in this registration "
                        "(item E16). --allow-output-change must never be passed."
                    ),
                },
                "protocol_document": {
                    "relpath": f"{PACKAGE}/protocol-registered-v1.json",
                    "sha256": protocol_sha,
                },
                "one_factor": protocol["one_factor"],
                "purpose": (
                    protocol["cells"][key]["run_id"]
                    + ": "
                    + FLIGHT_PROSE[key]
                    + ". "
                    + (
                        "It measures request envelopes only and reads nothing."
                        if is_fit
                        else protocol["decision_rule_fixed_here"]
                        if key == "arm"
                        else (
                            "It supplies the within-chain null the AGREE delta is read "
                            "at and makes no claim of its own."
                            if key == "aa"
                            else "Structural form proof only: no score and no read."
                        )
                    )
                ),
                "quality_read_gate": (
                    "No task-quality read before the complete sealed manifest, the "
                    "exact ordered outputs, the native phase summary and the single "
                    "successful complete official TRAIN score all exist for BOTH the "
                    "AGREE arm and its in-chain A/A replicate. A verdict computed "
                    "against the sealed comparator alone is refused."
                ),
            }
            if key == "aa" and not is_fit:
                plan["byte_identity_obligation"] = {
                    "sealed_comparator_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                    "this_cell_output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
                    "verified": True,
                    "note": (
                        "The A/A cell is the byte-identity proof: its own prepared "
                        "first-phase supply, minted at the changed implementation, "
                        "reproduces the sealed comparator's output digest exactly."
                    ),
                }
            prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
            name = f"{prefix}{kind}-plan-registered-v1.json"
            text = dump(plan)
            wr(f"{PACKAGE}/{name}", text)
            written.append(f"{PACKAGE}/{name}")
            plan_files[
                identity["fit"]["run_id"] if is_fit else identity["run_id"]
            ] = name

    # ---- 3. the analysis recipe -----------------------------------------
    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-agree-w1-fold-a-paired-analysis-v1",
        "title": (
            "Cell AGREE -- the paired read against the sealed PLAN arm, at the "
            "in-chain A/A null flown beside it"
        ),
        "registered_at_utc": f"{args.date}T12:00:00.000000+00:00",
        "arms": {
            "arm": {
                "run_id": ids["arm"]["run_id"],
                "attempt_id": ids["arm"]["attempt_id"],
                "run_manifest_sha256": "PENDING_SEAL",
                "scores_sha256": "PENDING_SEAL",
                "outputs_sha256": "PENDING_SEAL",
            },
            "in_chain_replicate": {
                "run_id": ids["aa"]["run_id"],
                "attempt_id": ids["aa"]["attempt_id"],
                "run_manifest_sha256": "PENDING_SEAL",
                "scores_sha256": "PENDING_SEAL",
                "outputs_sha256": "PENDING_SEAL",
                "role": "the within-chain null the delta is read at",
            },
            "comparator": {
                "run_id": COMPARATOR_RUN,
                "attempt_id": COMPARATOR_ATTEMPT,
                "role": "gating comparator, sealed, never re-flown",
            },
        },
        "resampling": {
            "bootstrap_draws": 10000,
            "metrics": ["slu_f1_f1", "scenario_action_exact"],
            "seed": 20260926,
            "unit": "row (paired)",
        },
        "reported_beside_every_verdict": [
            "the per-scenario table in both the natural-mixture and the equal-stratum weighting",
            "the frontier row: effect x prefilled tokens per row x GPU hours per 1,080 rows",
            "the measured token delta of the Perception block, against the read's +1.4 tokens per row",
            (
                "the DELIVERY CHECK: on how many rows did the flown arm actually "
                "deliver the row's own gold intent boundary entry, and does that "
                "agree with the offline replication's prediction? A delta with a "
                "delivery rate the replication did not predict is an engineering "
                "defect, not an effect"
            ),
            (
                "the CONVERSION, finally measured: of the rows that newly received "
                "their gold intent's boundary entry, how many answered the intent "
                "correctly. This is the number the registration could not know, and "
                "it is the cell's most valuable output whatever the verdict"
            ),
            "the per-class table over the bad-case bank's INTENT-UNCOVERED and INTENT-COVERED rows",
        ],
        "output": {
            "analysis_root": "analysis/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1"
        },
        "boundary": (
            "A development read on a TRAIN construction fold (owner decisions 28 and "
            "86); never a test claim, never a generalisation claim, and it admits "
            "nothing by itself."
        ),
    }
    wr(f"{PACKAGE}/analysis-recipe-v1.json", dump(recipe))
    written.append(f"{PACKAGE}/analysis-recipe-v1.json")

    # ---- 4. registered facts, with the canonical stage3_measurement -----
    measurement = {
        ids["arm"]["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "expected_effect_pp": effect["expected_effect_pp"],
            "rows": 1080,
            "primary_metric": "slu_f1",
            "claims_benefit": True,
            "replicate_run_id": ids["aa"]["run_id"],
            "note": (
                "Cell AGREE claims a benefit and is the first cell of this programme "
                "to do so on well-evidenced grounds. The expectation is DERIVED, not "
                "guessed: the measured newly-delivered row counts per bad-case class "
                "times that class's measured perfect-repair headroom, times a STATED "
                "conversion of "
                + f"{CONVERSION:g}"
                + " that is UNMEASURED. Delivery is not correctness; the conversion "
                "is the cell's own primary unknown, and the declared number is a "
                "construction, not a prediction. Ceiling at conversion 1.0 is "
                + f"{effect['ceiling_at_perfect_conversion_pp']['slu_f1']:g}"
                + " pp, so this design's "
                + f"{floor_at_1080:g}"
                + " pp admission bar at n = 1,080 is "
                + ("cleared" if clears else "NOT cleared by the declared expectation")
                + " -- reported, not engineered around."
            ),
        },
        ids["aa"]["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "expected_effect_pp": 0.0,
            "rows": 1080,
            "primary_metric": "slu_f1",
            "claims_benefit": False,
            "replicate_run_id": ids["arm"]["run_id"],
            "note": (
                "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the "
                "locked plan's own form so the AGREE delta is read against a "
                "within-chain null. Its expected effect is exactly zero by "
                "construction, and a non-zero read on it is a measurement of the "
                "instrument, which is what it is for."
            ),
        },
        ids["smoke"]["run_id"]: {
            "measurement_design": "form-proof",
            "expected_effect_pp": 0.0,
            "rows": 4,
            "primary_metric": "slu_f1",
            "claims_benefit": False,
            "note": (
                "Four rows prove FORM and nothing else: that the agreement table "
                "loads and hash-verifies, that the boundary channel still delivers "
                "eight entries, that every request fits and that the episode "
                "completes. Scored by no one, read by no one; under the measurement "
                "instrument's rule 5 a batch of four rows can never be evidence of "
                "benefit."
            ),
        },
    }
    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": (
            "Every model-free measured fact this registration rests on, and the "
            "CANONICAL stage3_measurement block scripts/checks/"
            "stage3_effect_floor_check.py resolves. The same block is repeated in the "
            "preregistration's fenced json for readability; this copy has precedence."
        ),
        "registered_at_utc": f"{args.date}T12:00:00.000000+00:00",
        "study_commit_at_registration": args.commit,
        "authority_relpaths": [DIAGNOSTIC, INSTRUMENT, BANK_READ],
        "cells": {
            key: {
                "cell": ids[key]["cell"],
                "run_id": ids[key]["run_id"],
                "fit_run_id": ids[key]["fit"]["run_id"],
                "rows": ids[key]["rows"],
                "composed_config_hash": ids[key]["composed_config_hash"],
                "protocol_hash": ids[key]["protocol_hash"],
                "boundary_rank_weights": ids[key]["rank_weights"],
                "declares_agreement_source": ids[key]["declares_agreement_source"],
            }
            for key in CELLS
        },
        "committed_artifacts": {
            "agreement_table": {"relpath": AGREEMENT_RELPATH, "sha256": AGREEMENT_SHA},
            "agreement_receipt": {
                "relpath": AGREEMENT_RECEIPT_RELPATH,
                "sha256": AGREEMENT_RECEIPT_SHA,
            },
            "production_replication": {
                "relpath": REPLICATION_RELPATH,
                "sha256": args.replication_receipt_sha256,
            },
            "prepared_supplies": {
                key: ids[key]["prepared_phase_supply"] for key in CELLS
            },
        },
        "default_byte_identity": {
            "what_is_claimed": (
                "With w_agree 0.0 and no agreement_source declared, the rendered "
                "Perception bytes are exactly what flies today."
            ),
            "how_it_is_proven": (
                "The A/A cell's own prepared first-phase supply, minted at the CHANGED "
                "implementation with no committed pin to inherit, carries the same "
                "output digest as the artifact the sealed comparator flew. The output "
                "digest is core.preparation.digest over the {facets, values} payload, "
                "so equality means the same value ids in the same order on every one "
                "of the 1,080 rows -- and the rendered block is a function of exactly "
                "that payload."
            ),
            "sealed_comparator": {
                "relpath": "prepared/SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1/phase-supply-v1.json",
                "file_sha256": "50da0c7bdaa756fb47abffefdaaa8f920f654b79f60905ca06a911067e6301c6",
                "output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
            },
            "recomputed_default": {
                "relpath": ids["aa"]["prepared_phase_supply"]["relpath"],
                "file_sha256": ids["aa"]["prepared_phase_supply"]["sha256"],
                "output_sha256": PLAN_SUPPLY_OUTPUT_SHA,
            },
            "treatment": {
                "relpath": ids["arm"]["prepared_phase_supply"]["relpath"],
                "file_sha256": ids["arm"]["prepared_phase_supply"]["sha256"],
                "output_sha256": args.treatment_output_sha256,
                "note": (
                    "Reported so the same receipt shows both halves: the default "
                    "unchanged and the treatment actually changed. The selected value "
                    "count is identical on both sides (8,624), which is the "
                    "token-neutrality the read measured -- the block still carries "
                    "eight entries and only which eight moves."
                ),
            },
            "rendered_request_identity": {
                "what_is_claimed": (
                    "Not only the selection but the RENDERED REQUEST BYTES of the "
                    "pre-flight prompt-budget envelope are identical between the "
                    "sealed comparator cell, the A/A control and the treatment, on "
                    "every one of the four phases."
                ),
                "how_it_was_measured": (
                    "FlightRuntime._assess_prompt_budget on the representative sample, "
                    "model-free, for the comparator cell as committed and for both new "
                    "cells as registered. The payload sha256 is the canonical JSON of "
                    "the rendered (system, user) envelope."
                ),
                "per_phase": {
                    "perception": {
                        "rendered_text_tokens": 19449,
                        "decision": "ALLOW",
                        "physical_margin_tokens": 4584,
                        "payload_sha256_prefix": "c6bcbb820887d9e2",
                    },
                    "reviewer": {
                        "rendered_text_tokens": 19313,
                        "decision": "ALLOW",
                        "physical_margin_tokens": 4720,
                        "payload_sha256_prefix": "80e3924d991a438d",
                    },
                    "planner": {
                        "rendered_text_tokens": 19252,
                        "decision": "ALLOW",
                        "physical_margin_tokens": 4781,
                        "payload_sha256_prefix": "8adac860cf952aa9",
                    },
                    "solver": {
                        "rendered_text_tokens": 21278,
                        "decision": "COMPACT_REQUIRED",
                        "physical_margin_tokens": 2755,
                        "payload_sha256_prefix": "44927c0871a44df3",
                        "note": (
                            "The Solver phase reads COMPACT_REQUIRED with a POSITIVE "
                            "physical margin on the comparator too; under "
                            "context_fit_policy compact-or-abstain that is recorded and "
                            "the flight proceeds. It is the locked plan's own "
                            "pre-existing state, not this cell's."
                        ),
                    },
                },
                "identical_on": [
                    COMPARATOR_RUN,
                    "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1",
                    "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1",
                ],
            },
            "a_defect_this_registration_found_and_repaired": {
                "what": (
                    "FlightRuntime._phase_supply_prompt_bound bounded a phase's traced "
                    "supply volume by spec.k -- the RECALL width -- which was the "
                    "delivered width in every cell committed before today because they "
                    "all declare k = fuse_coverage.top_l. A cell that recalls 60 and "
                    "delivers 8 was therefore budgeted at 60 blocks: 30,309 rendered "
                    "tokens against a 24,576-token slot, a negative physical margin, "
                    "and a pre-flight REFUSAL of a request whose own prepared artifact "
                    "carries exactly 8 value ids per row."
                ),
                "repair": (
                    "Under saea-fuse-associated-values-v1, whose top_l is a hard cap on "
                    "the total number of values it can select, the bound is now "
                    "min(k, top_l). Every other fuser keeps spec.k, because top_l is "
                    "not a cap for saea-fuse-supplyfilter-v1 and narrowing there could "
                    "under-count."
                ),
                "identity": (
                    "Of the 174 committed specs using that fuser, 171 declare "
                    "k = top_l = 8, two declare 16 = 16 and one declares k = 60 with "
                    "top_l = 61, so min returns today's spec.k in all 174 and no "
                    "existing bound, receipt or budget verdict moves. Pinned by four "
                    "tests in tests/unit/test_kb_policy_exemplar_agreement.py."
                ),
            },
            "file_hashes_moved_as_expected": True,
            "why_the_file_hash_moves": (
                "core.flight.FlightRuntime._phase_seed_inputs binds the "
                "implementation sha256 of rails.kb_policy, rails.knowledge_provider, "
                "rails.phase_supply, rails.knowledge_stores and core.flight.runtime. "
                "This change edits three of them, so every prepared artifact in the "
                "repository becomes stale and must be re-minted by its cell's own "
                "re-pin. That is the designed behaviour, not a side effect of this "
                "cell."
            ),
        },
        "agreement_vote_facts": {
            "source": "the agreement receipt pinned above",
            "roster_rows": 1080,
            "vote_total_per_row": 20,
            "rows_with_a_self_excluded_exemplar": 0,
            "rows_with_no_vote": 0,
            "pool_values_without_a_build_time_target": 0,
            "distinct_boundary_facets_ever_voted_for": 60,
            "self_exclusion_note": (
                "0 rows, because the exemplar pool excludes every Fold A recording by "
                "construction. The exclusion is implemented, tested and reported "
                "anyway: the 2026-09-26 read measured the same 0 on all three rosters "
                "and required that it be preserved."
            ),
            "gold_free": (
                "The vote key is each pool value's own frozen build-time task_target, "
                "a released-store property. No gold label, reference transcript, test "
                "annotation or future turn enters the artifact, the query or the "
                "weight."
            ),
            "speech_keyed": (
                "The vote summarises the row's OWN sealed speech vector recalled "
                "against the frozen pool, so the standing ruling that a retrieval "
                "query is speech or speech-plus-state holds."
            ),
        },
        "recall_width_correction": {
            "what_the_brief_said": "w_agree 1.0, k left at 8",
            "what_is_registered": (
                "w_agree 1.0, DELIVERED width left at 8 (fuse_coverage m 8 / c 1 / "
                "top_l 8), RECALL width k moved from 8 to 60"
            ),
            "why": (
                "PhaseSupplySpec.k is top_k_per_dimension: the recall truncates by "
                "cosine before the ranker runs, so at k = 8 the agreement term can "
                "only permute the eight the cosine already chose. Measured through the "
                "production path: at k = 8 wrong-row delivery is 45.0 % -> 45.0 % on "
                "all three rosters -- the treatment is INERT. The read's own "
                "simulation recalled at 60 and delivered 8."
            ),
            "the_widening_is_a_no_op_on_its_own": {
                "claim": (
                    "At pure cosine the top 8 of a 60-wide recall IS the 8-wide "
                    "recall's set, in the same order, so the delivered selection does "
                    "not move."
                ),
                "proof": (
                    "The in-chain A/A control carries k = 60 at w_agree 0.0 and its own "
                    "prepared first-phase supply reproduces the sealed comparator's "
                    f"output digest {PLAN_SUPPLY_OUTPUT_SHA} exactly on all 1,080 rows."
                ),
                "measured_beside_it": (
                    "the production replication reads the baseline at width 60 as "
                    "bit-identical to width 8 (45.0 % / 97.3 % on Fold A), and the "
                    "delivered-width histograms are byte-identical between the two "
                    "arms, so the read's +1.4 tokens per row holds"
                ),
                "and_the_rendered_request_is_identical_too": (
                    "the pre-flight prompt-budget envelope of the A/A cell at k 60 "
                    "renders to the same 19,449 Perception tokens and the same payload "
                    "sha256 prefix c6bcbb820887d9e2 as the sealed comparator cell, on "
                    "every one of the four phases -- so the widening costs nothing in "
                    "the request either, not merely nothing in the selection"
                ),
            },
            "consequence": (
                "The two arms differ in w_agree ALONE, which makes the A/A a genuine "
                "one-factor control rather than only a replicate."
            ),
        },
        "delivery_facts_from_the_read": {
            "_note": (
                "The read's own figures. The production-replication receipt reproduces "
                "every one of the six delivery cells EXACTLY at recall width 60 and "
                "delivered width 8, and validates first that the recomputed exemplar "
                "top-20 equals the sealed selection on 1080/1080, 625/625 and 1000/1000 "
                "rows and that the baseline boundary fusion equals what each flight "
                "sealed on every row."
            ),
            "train-fold-a-plan": {
                "intent_wrong_rows": 191,
                "wrong_row_delivery_pct": {"w_agree_0": 45.0, "w_agree_1": 81.7},
                "wrong_rows_delivered": {"w_agree_0": 86, "w_agree_1": 156},
                "correct_row_delivery_pct": {"w_agree_0": 97.3, "w_agree_1": 99.6},
            },
            "roll1": {
                "intent_wrong_rows": 184,
                "wrong_row_delivery_pct": {"w_agree_0": 44.6, "w_agree_1": 75.0},
                "wrong_rows_delivered": {"w_agree_0": 82, "w_agree_1": 138},
                "correct_row_delivery_pct": {"w_agree_0": 95.1, "w_agree_1": 98.8},
            },
            "dev2000-added-plan": {
                "intent_wrong_rows": 232,
                "wrong_row_delivery_pct": {"w_agree_0": 35.8, "w_agree_1": 78.0},
                "wrong_rows_delivered": {"w_agree_0": 83, "w_agree_1": 181},
                "correct_row_delivery_pct": {"w_agree_0": 94.5, "w_agree_1": 99.5},
            },
            "production_path_agreement": (
                "EXACT on all six delivery cells of all three rosters. Sealed-exemplar "
                "agreement 1080/1080, 625/625, 1000/1000; sealed-boundary agreement at "
                "the flown width 1080/1080, 625/625, 1000/1000; 0 rows skipped; "
                "fusion-based and rank-based delivery agree on every row."
            ),
            "per_class_gain_fold_a": {
                "INTENT-UNCOVERED": {
                    "rows": 130, "before": 27, "after": 97, "gained": 70, "lost": 0
                },
                "INTENT-COVERED": {
                    "rows": 61, "before": 59, "after": 59, "gained": 2, "lost": 2
                },
            },
            "per_class_gain_dev2000_added": {
                "INTENT-UNCOVERED": {
                    "rows": 169, "before": 30, "after": 119, "gained": 94, "lost": 5
                },
                "INTENT-COVERED": {
                    "rows": 63, "before": 53, "after": 62, "gained": 9, "lost": 0
                },
            },
            "floor_across_the_two_unfitted_rosters_pp": 30.4,
            "token_cost_per_row": 1.4,
            "flown_block_tokens": 1195.4,
            "k30_alternative_token_cost_per_row": 3262.3,
        },
        "measurement_design": {
            "canonical_declaration": (
                f"{PACKAGE}/registered-facts-v1.json, top-level 'stage3_measurement' "
                "-- the block scripts/checks/stage3_effect_floor_check.py resolves. "
                "The same block is repeated in the preregistration's fenced json for "
                "readability; the registered-facts copy has precedence."
            ),
            "design": "cross-flight-with-in-chain-replicate",
            "why_not_offline_sealed_pool": (
                "The effect is a change to what Perception CONSUMES, so it cannot be "
                "read off a sealed pool: no sealed sample was produced under the new "
                "ranking. The GPU is the only instrument for it."
            ),
            "why_an_in_chain_replicate": (
                "Rule 4 of the measurement instrument refuses a cross-flight contrast "
                "with no in-chain replicate outright; the A/A cell is that replicate "
                "and flies in the same campaign chain."
            ),
            "floor_at_n_1080_pp": floor_at_1080,
            "declared_expectation_clears_the_floor": clears,
            "if_it_does_not_clear": (
                "Reported, never engineered around. The honest options are: accept "
                "that the read may be NEUTRAL by width and treat the measured "
                "conversion as the cell's deliverable; or measure the conversion "
                "first on a smaller probe and re-declare. Inflating "
                "expected_effect_pp to clear the bar would be the one move this "
                "registration refuses."
            ),
        },
        "expected_effect_derivation": effect,
        "stage3_measurement": measurement,
        "reported_beside": {
            "note": "CONTEXT ONLY. None of these is this cell's comparator or bar.",
            "train_fold_a_plan": {
                "run_id": COMPARATOR_RUN,
                "official_slu_f1": COMPARATOR_OFFICIAL["slu_f1"],
                "intent_accuracy": COMPARATOR_OFFICIAL["intent_accuracy"],
            },
            "train_fold_a_own_null": {"h_slu": 1.2485, "h_intent": 0.9943, "n": 1080},
            "cross_flight_aa_offset_pp": 1.87,
        },
        "resampling": recipe["resampling"],
        "rows": 1080,
    }
    wr(f"{PACKAGE}/registered-facts-v1.json", dump(facts))
    written.append(f"{PACKAGE}/registered-facts-v1.json")

    # ---- 5. README and preregistration ----------------------------------
    verdict_line = (
        "CLEARS" if clears else "DOES NOT CLEAR"
    )
    readme = f"""# Cell AGREE: the agreement term on the intent-boundary retrieval channel

Registered before contact {args.date} at study commit `{args.commit}`; all three cells **held**.
Nothing here authorises a flight, a flip or an admission entry.

**The one factor.** {protocol["one_factor"]}

**Why.** [`{DIAGNOSTIC}`]({DIAGNOSTIC[5:]}) measured where the gold intent
actually ranks in the flown Perception boundary retrieval: median rank 10-14 on intent-wrong rows
against 1 on correct rows, spread down the whole tail, so widening what the channel DELIVERS is not
the fix -- delivering 16 leaves over two thirds still missing, and delivering 30 buys the same
delivery as this change for +3,262.3 tokens a row instead of +1.4. The exemplar channel already ranks
the gold intent first on 76.1 % of rows against the boundary cosine's 65.6 %, so this change lets the
boundary ranker borrow a signal the system already computes. Selected from 27 candidates by a rule
fixed before the numbers were read; measured delivery on intent-wrong rows 45.0 % -> 81.7 % on the fit
roster, with a +30.4-point floor on the two rosters the weight was not fitted on.

**One correction to the brief this implements, and it is load-bearing.** `PhaseSupplySpec.k` is the
provider's `top_k_per_dimension`, so the recall truncates by cosine BEFORE the ranker runs: left at 8,
the agreement term can only permute the eight the cosine already chose and cannot reach a gold intent
at rank 9-60, which is the whole population the read measured. Measured through the production path,
at `k` 8 the treatment is **inert** -- wrong-row delivery 45.0 % to 45.0 % on all three rosters. The
read's own simulation recalled at 60 and delivered 8, and that is what is registered here: `k` 60 with
`fuse_coverage` m 8 / c 1 / top_l 8. The delivered width does not move, the selected-value count is
8,624 on both arms, and the widening alone is proven inert -- see **Byte identity** below.

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration proper, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free measured fact, and the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, budgets, the decision rule, the claim boundary |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the AGREE arm's plans |
| `aa-generation-plan-registered-v1.json` / `aa-fit-plan-registered-v1.json` | the in-chain A/A replicate's plans |
| `smoke-generation-plan-registered-v1.json` / `smoke-fit-plan-registered-v1.json` | the four-row form smoke's plans |
| `analysis-recipe-v1.json` | how the sealed output is read offline, under its own later-registered read id |
| `identity-proof-v1.json` | the byte-identity proof: the default's selection is unchanged at the changed implementation |
| `production-replication-v1.json` | the production path reproducing the read's own delivery numbers |

**Three cells, one chain.** The campaign plan `configs/campaign/slurp-native-stage3-agree-w1-fold-a-v1.json`
carries the A/A replicate **and** the AGREE arm, because a cross-flight contrast against a sealed
comparator with no in-chain replicate is refused outright ([`{INSTRUMENT}`]({INSTRUMENT[5:]}) rule 4:
a pure A/A pair at n = 625 read +1.87 pp with a CI95 excluding zero). The smoke is outside the plan
and is never scored.

**The expected effect, stated as what it is.** Declared `expected_effect_pp`
**{effect["expected_effect_pp"]:g}** pp official pooled SLU-F1, derived as the measured
newly-delivered rows per bad-case class times that class's measured perfect-repair headroom, times a
**stated, unmeasured** conversion of {CONVERSION:g}. The ceiling at a perfect conversion is
{effect["ceiling_at_perfect_conversion_pp"]["slu_f1"]:g} pp. The design's admission bar at n = 1,080
is {floor_at_1080:g} pp, so the declaration **{verdict_line}** it. That is reported, not engineered
around: delivery is not correctness, the conversion is this cell's primary unknown, and inflating the
declaration to clear a bar is the one move this registration refuses. A NEUTRAL read would mean the
conversion is below what this design can see -- mode (iv) of the read, and the programme's next
question.

**Byte identity of the default, three ways.** (1) The A/A cell's own prepared first-phase supply,
minted at the changed implementation with the widened recall and no committed pin to inherit, carries
output SHA-256 `{PLAN_SUPPLY_OUTPUT_SHA}` -- the sealed comparator's own digest, on all 1,080 rows.
(2) Its pre-flight prompt-budget envelope renders to the comparator's own token counts and payload
digests on every one of the four phases (perception 19,449 / `c6bcbb82`, reviewer 19,313 /
`80e3924d`, planner 19,252 / `8adac860`, solver 21,278 / `44927c08`), so the widened recall costs
nothing in the request either. (3) With the recall forced back to 8 the A/A renders the identical
payloads again, which is the widening's no-op stated as a measurement. The treatment's selection
digest differs (`eab5c61e`), so the change is not inert -- while its selected-value count is the same
8,624, which is the token neutrality the read measured.

**Mint, flip, queue.** Root mints `coordination/slurp-stage3-agree-w1-fold-a-v1/root-admission-v1.json`
(id `slurp-stage3-agree-w1-fold-a-admission-v1`) with the six eligible run ids and this family's
caps, countersigns the exposure rows, then re-pins all three cells with
`scripts/flights/repin_cell.py --set-ready`. `--allow-output-change` must never be passed: no cell
here carries a committed `prepared_phase_supply` and the flip mints each cell's own.

**Not authorised by this package.** No flight before the receipt is minted and all three cells are
flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV
read; no second factor; no `w_prior` change; no store rebuild.
"""
    wr(f"{PACKAGE}/README.md", readme)
    written.append(f"{PACKAGE}/README.md")

    prereg = f"""# Cell AGREE: preregistration

Registered {args.date} at study commit `{args.commit}`, before any contact, from the sealed cell PLAN
fragments by script (decision 58). Development numbers only (owner decisions 28 and 86); never a test
claim.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `{COMPARATOR_RUN}` ({COMPARATOR_OFFICIAL["slu_f1"]} / {COMPARATOR_OFFICIAL["intent_accuracy"]}) |
| factor | {protocol["one_factor"]} |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores and their pins, exemplar k = 20, role graph, templates, normaliser, scorers, budgets |
| comparator | `{COMPARATOR_RUN}`, sealed, never re-flown |
| in-chain replicate | `{ids["aa"]["run_id"]}`, the locked form re-flown in the SAME campaign chain |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `{ids["arm"]["run_id"]}` / `{ids["arm"]["fit"]["run_id"]}`; `{ids["aa"]["run_id"]}` / `{ids["aa"]["fit"]["run_id"]}`; `{ids["smoke"]["run_id"]}` / `{ids["smoke"]["fit"]["run_id"]}` |
| authority | {protocol["authority"]} |

## Decision rule (fixed here)

{protocol["decision_rule_fixed_here"]}

## The measurement declaration

```json
{json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)}
```

## How `expected_effect_pp` was derived, and what it is not

{effect["honest_statement"]}

Arithmetic:

{chr(10).join("- " + line for line in effect["arithmetic"])}

Sweep over the unmeasured conversion (official pooled SLU-F1, pp):
{chr(10).join(f"- conversion {rate}: {value:g}" for rate, value in effect["sweep_slu_pp_by_conversion"].items())}

The floor this design must clear at n = 1,080 is {floor_at_1080:g} pp, so the declared expectation
**{verdict_line}** it. Stated plainly rather than engineered around.

## Budgets and failure rule

Ceilings as cell PLAN's, per generation cell: {ids["arm"]["family_budget"]["generation_calls_cap"]}
generation calls (run-cumulative), {ids["arm"]["family_budget"]["fit_endpoint_calls_cap"]} FIT
endpoints, {ids["arm"]["family_budget"]["repeated_speech_audio_seconds_cap"]} repeated speech seconds,
{ids["arm"]["family_budget"]["gpu_hours_fit_inclusive"]} GPU hours, one official complete score. The
smoke: {ids["smoke"]["family_budget"]["generation_calls_cap"]} /
{ids["smoke"]["family_budget"]["fit_endpoint_calls_cap"]} /
{ids["smoke"]["family_budget"]["repeated_speech_audio_seconds_cap"]} s, no score. {protocol["failure_policy"]}

## Prohibitions

{protocol["prohibitions"]}
"""
    wr(PREREG, prereg)
    written.append(PREREG)

    # ---- 6. the two model-free proofs, copied into the package ----------
    # They are evidence, so they travel with the registration instead of only
    # living under SPEECHRL_DATA_DIR where Git never sees them.
    for source, name in (
        (args.identity_proof, "identity-proof-v1.json"),
        (args.replication, "production-replication-v1.json"),
    ):
        if source is None:
            continue
        payload = json.loads(Path(source).read_text(encoding="utf-8"))
        wr(f"{PACKAGE}/{name}", dump(payload))
        written.append(f"{PACKAGE}/{name}")
    return written


def write_ledger_rows(args: argparse.Namespace, ids: dict) -> int:
    """Eight rows: six unconsumed flight rows and two model-free rows.

    Idempotent: a row whose run id is already present is replaced in place.
    """

    text = rd(LEDGER)
    lines = text.split("\n")
    header = (
        "| date | run/experiment id | execution profile | scope | model/tool | speech "
        "carrier + split | split role | split identity hash | consumed | calls | speech "
        "audio seconds | gpu hours | inherited exposure | artifacts | notes |"
    )
    separator = "| " + " | ".join(["---"] * 15) + " |"
    stamp = f"{args.date}T12:00:00.000000+00:00"
    inherited = (
        "TRAIN Fold A discovery rows already exposed by the sealed dual-store anchor, "
        "the released direct anchor, cells B0/B0r, B1 and its twin, B4b, B4b-rep, B5e, "
        "B7a, B7a-v2, B8b-anchor, B1-notool, PLAN, PLANr and ROLL-2; this cell adds no "
        "new row to the fold and opens no split. Prior exposure is inherited in full."
    )
    scope_common = (
        "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech "
        "packets; NO native tool authority on any role; prompt bytes otherwise the "
        "sealed PLAN arm's"
    )

    rows: list[tuple[str, str]] = []
    for key in ("aa", "arm", "smoke"):
        identity = ids[key]
        prefix = {"arm": "", "smoke": "smoke-", "aa": "aa-"}[key]
        for kind in ("generation", "fit"):
            is_fit = kind == "fit"
            run_id = identity["fit"]["run_id"] if is_fit else identity["run_id"]
            attempt = identity["fit"]["attempt_id"] if is_fit else identity["attempt_id"]
            artifact = f"{PACKAGE}/{prefix}{kind}-plan-registered-v1.json"
            plan_sha = sha_text(rd(artifact))
            budget = identity["family_budget"]
            calls = (
                budget["fit_endpoint_calls_cap"]
                if is_fit
                else budget["generation_calls_cap"]
            )
            scope = (
                FLIGHT_PROSE[key]
                + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "")
                + ": the intent-boundary Perception channel's own w_agree term at "
                + (
                    "1.0 over the pre-computed self-excluded exemplar-intent vote, "
                    "delivered width unchanged at 8 entries, recall width 60 (at 8 the "
                    "term is inert, measured)"
                    if key != "aa"
                    else "0.0 at the SAME recall width 60 -- the locked plan's own form, "
                    "re-flown in the same chain as the within-chain null and the "
                    "one-factor control; its prepared supply reproduces the sealed "
                    "comparator's output digest exactly"
                )
            )
            notes = (
                f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) "
                f"{args.date} at study commit {args.commit} by the AGREE registration "
                f"agent (worktree /home/chao/saea-worktrees/fable-agree, branch "
                f"fable/agree). This registration performs no contact and authorises "
                f"none. Plan SHA256 {plan_sha}; attempt {attempt}. Protocol hash "
                f"{identity['protocol_hash']}; composed config "
                f"{identity['composed_config_hash']}; expected session {SESSION} "
                f"(attach only, never spawn or stop). READINESS HELD: root mints "
                f"coordination/slurp-stage3-agree-w1-fold-a-v1/root-admission-v1.json "
                f"(decision id slurp-stage3-agree-w1-fold-a-admission-v1) with the six "
                f"eligible run ids {ids['arm']['run_id']}, "
                f"{ids['arm']['fit']['run_id']}, {ids['aa']['run_id']}, "
                f"{ids['aa']['fit']['run_id']}, {ids['smoke']['run_id']}, "
                f"{ids['smoke']['fit']['run_id']} and this family's caps, then re-pins "
                f"with scripts/flights/repin_cell.py --set-ready, which mints each "
                f"cell's OWN first-phase supply under its own run id (item E16); "
                f"--allow-output-change must never be passed. Every hash in this row "
                f"moves at the flip and the re-pin tool rewrites it. Measurement "
                f"declaration (scripts/checks/stage3_effect_floor_check.py): "
                f"measurement_design cross-flight-with-in-chain-replicate, "
                f"expected_effect_pp {_expected_effect(args)['expected_effect_pp']:g}, "
                f"claims_benefit "
                f"{'true' if key == 'arm' else 'false'}, rows {identity['rows']}, "
                f"replicate_run_id "
                f"{ids['aa']['run_id'] if key == 'arm' else ids['arm']['run_id'] if key == 'aa' else 'n/a (form proof)'} "
                f"-- declared at the top level of {PACKAGE}/registered-facts-v1.json "
                f"and repeated in the preregistration fence. DELIVERY IS NOT "
                f"CORRECTNESS: the expectation is a construction over a stated, "
                f"unmeasured conversion and is not a prediction. Stop and preserve on "
                f"the first failure; AT MOST ONE root-diagnosed recovery "
                f"re-registration. No paper-scale profile, no confirmatory split, no "
                f"test-split contact, no comparator re-flight and no admission entry "
                f"from this cell."
            )
            cells = [
                "",
                stamp,
                run_id,
                "bounded-discovery-probe",
                scope,
                scope_common,
                f"slurp TRAIN Fold A {identity['rows']}",
                "discovery",
                identity["split_identity_hash"],
                "no",
                str(calls),
                str(budget["repeated_speech_audio_seconds_cap"]),
                str(budget["gpu_hours_fit_inclusive"]),
                inherited,
                artifact,
                notes,
                "",
            ]
            rows.append((run_id, "|".join(f" {c} " if c else "" for c in cells)))

    model_free = [
        (
            AGREEMENT_LEDGER_ROW,
            "Build the pre-computed, self-excluded exemplar-intent AGREEMENT table the "
            "cell AGREE boundary channel ranks with: arithmetic over the pinned "
            "exemplar snapshot, the pinned pool key vectors and the pinned Fold A "
            "speech query vectors, through the repository's own recall/rank/fuse. "
            "Zero model, server, encoder, embedder, scorer, network, GPU and paid-API "
            "contacts.",
            AGREEMENT_RECEIPT_RELPATH,
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) "
            f"{args.date} at study commit {args.commit}. Artifact "
            f"{AGREEMENT_RELPATH} SHA256 {AGREEMENT_SHA}; receipt SHA256 "
            f"{AGREEMENT_RECEIPT_SHA}. Builder "
            f"scripts/build_slurp_intent_exemplar_agreement.py, 4 workers. Measured: "
            f"1,080 rows, 20 votes each, 0 self-excluded rows, 0 rows with no vote, 0 "
            f"pool values without a build-time target, all 60 boundary facets "
            f"reachable. It constructs no ExecutionPlan, reserves no contact and "
            f"authorises nothing; it exists because a pre-computation is registered "
            f"before its result is read, even when it is model-free.",
        ),
        (
            REPLICATION_LEDGER_ROW,
            "Reproduce the 2026-09-26 intent-boundary retrieval read's own gold-intent "
            "delivery numbers on all three rosters THROUGH THE PRODUCTION PATH, at "
            "w_agree 0.0 and 1.0, and split the Fold A delivery gain by the bad-case "
            "bank's own INTENT-UNCOVERED / INTENT-COVERED classes. Zero model, server, "
            "encoder, embedder, scorer, network, GPU and paid-API contacts.",
            REPLICATION_RELPATH,
            f"REGISTERED BEFORE RESULT READING (DRAFT, root countersignature pending) "
            f"{args.date} at study commit {args.commit}. Receipt SHA256 "
            f"{args.replication_receipt_sha256}; script "
            f"scripts/analysis/slurp_intent_agreement_production_replication.py, 4 "
            f"workers. It is the precondition of the registration above: a production "
            f"path that disagreed with the read would mean one of the two is wrong and "
            f"flying it would be premature. It admits nothing, releases nothing and "
            f"states no effectiveness claim.",
        ),
    ]
    for run_id, scope, artifact, notes in model_free:
        cells = [
            "",
            args.date,
            run_id,
            "model-free-check",
            scope,
            "no model or tool contact; local arithmetic over receipt-pinned files",
            "slurp TRAIN Fold A 1080 (and, for the replication, the sealed ROLL-1 and DEV-2000-ADDED rosters)",
            "discovery",
            ids["arm"]["split_identity_hash"],
            "no",
            "0",
            "0",
            "0",
            "No new speech exposure: every byte read was already exposed by the cells "
            "that sealed it. Prior exposure inherited in full.",
            artifact,
            notes,
            "",
        ]
        rows.append((run_id, "|".join(f" {c} " if c else "" for c in cells)))

    # replace-or-append, so re-running this script never duplicates a row
    existing = {
        line.split("|")[2].strip(): index
        for index, line in enumerate(lines)
        if line.startswith("|") and len(line.split("|")) > 3
    }
    appended: list[str] = []
    for run_id, row in rows:
        if run_id in existing:
            lines[existing[run_id]] = row
        else:
            appended.append(row)
    if appended:
        heading = (
            f"\n## Cell AGREE: the agreement term on the intent-boundary retrieval "
            f"channel, its in-chain A/A replicate and its two model-free "
            f"pre-computations (DRAFT, root countersignature pending)\n\n"
            f"Six unconsumed flight rows -- the AGREE arm, the in-chain A/A replicate, "
            f"the four-row form smoke and their three FIT spend identities -- plus two "
            f"model-free rows for the pre-computed agreement table and the "
            f"production-path replication of the read that motivated it. Authority "
            f"{DIAGNOSTIC}. None of these rows is countersigned and none authorises a "
            f"contact.\n\n{header}\n{separator}"
        )
        last = max(index for index, line in enumerate(lines) if line.startswith("|"))
        lines[last + 1 : last + 1] = heading.split("\n") + appended
    wr(LEDGER, "\n".join(lines))
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--date", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--gain-uncovered", type=int, required=True)
    parser.add_argument("--gain-covered", type=int, required=True)
    parser.add_argument("--loss-uncovered", type=int, default=0)
    parser.add_argument("--loss-covered", type=int, default=0)
    parser.add_argument("--replication-receipt-sha256", required=True)
    parser.add_argument("--treatment-output-sha256", required=True)
    parser.add_argument("--identity-proof", default=None)
    parser.add_argument("--replication", default=None)
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    os.chdir(repo)
    ids = identities(repo)
    written = write_package(repo, args, ids)
    count = write_ledger_rows(args, ids)
    print(
        json.dumps(
            {
                "written": written,
                "ledger_rows": count,
                "expected_effect_pp": _expected_effect(args)["expected_effect_pp"],
                "ceiling_at_conversion_1_pp": _expected_effect(args)[
                    "ceiling_at_perfect_conversion_pp"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
