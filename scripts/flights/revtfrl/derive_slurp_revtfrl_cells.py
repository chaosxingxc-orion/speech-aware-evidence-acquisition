#!/usr/bin/env python3
"""Derive the three REV-TFRL-1 cells -- the first training-free RL optimisation of the Reviewer node
(owner decision 165) -- from the AGREE arm's committed fragments (decision 58: script-derived
registrations).

THE BASE. Owner decision 165's brief names the base: the retained AGREE arm (decision 161: the agreement
term w_agree 1.0, recall k 60, fuse 8-1-8 over the self-excluded exemplar-intent vote) with G5's repaired
Reviewer instruction (``probes/slurp_native_role_reviewer_v1_g5_v1.txt``, the retired-tool order deleted,
decision 153). The in-chain A/A is exactly that base.

THE ONE PIN (the arm and the smoke). ``phase_material.reviewer.instruction_template`` moves to
``probes/slurp_native_role_reviewer_contrastive_v1.txt``: the contrastive review form the offline inner
loop selected over sealed TRAIN R01C pools (``scripts/analysis/slurp_reviewer_credit_table.py``; the
package README gives the numbers). It is the Reviewer text the sealed candidate-recovery control arm flew
(``probes/slurp_native_role_reviewer_candidate_recovery_v1.txt``), adapted to this plan by four edits and
nothing else -- the words that name a structure this plan does not carry (the "candidate proposal" and its
"exemplar-supported additions") are renamed to the structures it does carry (Perception's candidates and
the retrieved examples), the clause about tools "actually exposed in this turn" is deleted (no tool is
exposed to any role of this plan; item E25), and the locked Reviewer's own "do not request a transcript"
boundary is kept. The registration writer proves the edit list word by word.

Nothing else moves: the roster, the geometry, the session, the phase program and its 11-contact ceiling,
the three stores and their pins, the agreement term, the exemplar k of 20, the role graph, the Perception /
Solver / Planner templates, the deliver normaliser and the scorers are the AGREE arm's, byte for byte.
The Planner and the Solver are deliberately NOT touched: the brief scopes the optimisation to the Reviewer
node, and the confound this leaves against the measured selection is stated in the package.

THREE CELLS (the AGREE / G5 chain shape; measurement instrument rules 3 and 4): the arm on TRAIN Fold A
1,080, its four-row structural form smoke (outside the campaign plan, never scored), and the in-chain A/A
(the base: AGREE + the G5 instruction) flown in the SAME campaign chain.

Every cell drops ``prepared_phase_supply`` so the coordinator's flip mints each cell's OWN first-phase
supply under its own run id (item E16); the agreement-table preparation requirement is kept, exactly as
AGREE registered it. The Reviewer instruction is not an input to the first-phase supply, so every minted
supply must reproduce the sealed AGREE arm preparation's output digest -- that equality is the flip's
byte-identity check. ``--allow-output-change`` must never be passed.

CONFIG ONLY: three baselines, three experiment fragments and one campaign plan. No contact, no ledger
row, no decision receipt, no flip.

    python scripts/flights/revtfrl/derive_slurp_revtfrl_cells.py --date 2026-09-27
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

AGREE_ARM_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"

AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
#: The sealed AGREE arm preparation's OUTPUT digest (``prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/
#: phase-supply-v2.json``, field ``output_sha256``). Every 1,080-row supply this family mints must carry it.
AGREE_SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"

LOCKED_TEMPLATE = "probes/slurp_native_role_reviewer_v1.txt"
G5_TEMPLATE = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"
NEW_TEMPLATE = "probes/slurp_native_role_reviewer_contrastive_v1.txt"
SOURCE_TEMPLATE = "probes/slurp_native_role_reviewer_candidate_recovery_v1.txt"
THE_ONE_PIN = "phase_material.reviewer.instruction_template"

CAMPAIGN = "configs/campaign/slurp-native-stage3-revtfrl-fold-a-v1.json"
PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1"
ALGORITHM_ID = "sealed-credit-system-policy-v1"

THE_POLICY = (
    "The Reviewer node's instruction moves from the G5 text (the locked Reviewer instruction with the "
    "retired-tool order deleted) to the CONTRASTIVE review form: identify the strongest plausible competing "
    "intent and the spoken cue that would distinguish it from the draft, check each proposed entity for a "
    "spoken mention, type and span, and return concise findings that separate a speech-supported correction "
    "from an unresolved possibility, without assuming the draft is wrong. The form was SELECTED OFFLINE by "
    "the node's own credit over sealed TRAIN R01C trajectories (rows outside Fold A): in the one sealed arm "
    "that flew it, its review loop moved intent by +2.56 pp over the arm's own first drafts, against +0.74 pp "
    "for the locked form's loop averaged over eleven sealed R01C pools; paired on the same 625 rows the "
    "difference is +1.70 pp [+0.26, +3.17]. No gate or revision-scope rule over the sealed revisions beat "
    "honouring every revision (package README). Nothing else moves: the Planner and Solver templates, the "
    "agreement term, the stores, the program and its ceiling, the roster, the geometry and the scorers are "
    "the AGREE arm's."
)

ARM_ALGORITHM_NOTE = (
    "sealed-credit-system-policy-v1 applied NODE-SCOPED to the Reviewer, as owner decision 165 rules (per-node "
    "credit; the Reviewer's revise/keep decisions and their outcomes in the sealed pools are the reward signal): the "
    "node's policy -- its instruction -- was proposed reflectively over a per-visit credit table built from sealed trajectories "
    "and SELECTED OFFLINE over sealed TRAIN R01C pools (rows outside Fold A) by the node's own within-"
    "trajectory loop value; this flight is the context_application step on Fold A, and its sealed Reviewer "
    "visits are the next round's credit input."
)
SMOKE_ALGORITHM_NOTE = (
    "The four-row structural form smoke of the REV-TFRL-1 arm: the selected contrastive Reviewer instruction "
    "on the first four rows of the unchanged roster, labelled as the arm is because it flies the arm's form; "
    "scored by no one and read by no one."
)
AA_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the base -- the AGREE arm "
    "with G5's repaired Reviewer instruction -- re-flown in the same chain as the in-chain null and "
    "instrument of the REV-TFRL-1 arm. Its prepared first-phase supply must reproduce the sealed AGREE arm's "
    "output digest exactly."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def substitutions(tag: str, slug: str, *, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the AGREE arm's fragments to this cell's own."""

    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1",
             f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1",
             f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1",
             f"slurp-native-stage3-{slug}-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", f"slurp-native-stage3-{slug}-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
         f"attempt-slurp-native-stage3-{slug}-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", f"attempt-slurp-native-stage3-{slug}-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", f"slurp-native-stage3-{slug}-fold-a-baseline-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", f"slurp-native-stage3-{slug}-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent_path: str, out_path: str, pairs, *, template: str, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    document["what_this_is"] = what_this_is
    reviewer = document["phase_material"]["reviewer"]
    if reviewer["instruction_template"] != LOCKED_TEMPLATE:
        raise SystemExit(f"the AGREE parent's Reviewer template is {reviewer['instruction_template']!r}")
    if "phase_tools" in document:
        raise SystemExit("the parent carries phase_tools; the Reviewer toolkit is RETIRED (item E25)")
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0} or perception["k"] != 60:
        raise SystemExit("the parent is not the AGREE arm at w_agree 1.0 / k 60")
    if perception["agreement_source"]["relpath"] != AGREEMENT_RELPATH:
        raise SystemExit("the parent's agreement_source is not the registered agreement table")
    reviewer["instruction_template"] = template
    wr(out_path, dump_like(raw, document))


def derive_experiment(parent_path: str, out_path: str, pairs, args, *, purpose: str, readiness_reason: str,
                      campaign: bool, algorithm: dict, arm_rows: bool) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    document["failure_policy"] = document["failure_policy"].replace("closes cell PLAN", "closes this cell")
    cell = document["cells"][0]
    requirements = [r for r in cell["readiness"]["requirements"]
                    if r.get("kind") == "preparation" and r.get("relpath") == AGREEMENT_RELPATH]
    if len(requirements) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table preparation requirement")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": requirements, "state": "held"}
    if arm_rows:
        document["generation_budget"] = {
            "cap": 11880,
            "definition": (
                "The AGREE role graph is unchanged: perception 1, solver 1, reviewer 3, planner 1, max_revisions 1, "
                "so rails.native_episode_config.load_native_episode_config resolves the program ceiling "
                "1 + 2 * (3 + 1 + 1) = 11 contacts per row and 1,080 * 11 = 11,880 is the exact program maximum. "
                "Expected spend: the in-chain A/A at the sealed AGREE arm's own rate (4,385 contacts, 4.06 per row); "
                "the arm at the sealed contrastive-review rate on R01C (the candidate-recovery control arm: 3,657 "
                "contacts on 625 rows, 5.85 per row, because the contrastive Reviewer's findings route REVISE on "
                "about 62 % of rows) -- about 6,320 contacts. Both sit far under the ceiling. The budget is "
                "RUN-CUMULATIVE across every attempt of this run id, which is what makes the resume-recovery clause "
                "safe."
            ),
            "target": 6320 if "AA" not in cell["run_id"] else 4385,
        }
    document["stage3_algorithm"] = algorithm
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    for path in ("configs/" + NEW_TEMPLATE, "configs/" + G5_TEMPLATE, "configs/" + SOURCE_TEMPLATE):
        if not os.path.isfile(path):
            raise SystemExit(f"missing {path}")
    written: list[str] = []
    label = {"id": ALGORITHM_ID, "operators_used": ["context_application"], "note": ARM_ALGORITHM_NOTE}

    # ---- the arm ----------------------------------------------------------------------------------
    pairs = substitutions("REVTFRL", "revtfrl", smoke=False)
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-revtfrl-fold-a-baseline-v1.json", pairs,
                    template=NEW_TEMPLATE,
                    what_this_is=("Cell REV-TFRL-1, the first training-free RL optimisation of the Reviewer node "
                                  "(owner decision 165): the AGREE arm with the Reviewer instruction selected "
                                  "offline over sealed TRAIN R01C trajectories. " + THE_POLICY))
    written.append("configs/baseline/slurp-native-stage3-revtfrl-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-revtfrl-fold-a-v1.json", pairs, args,
        purpose=(
            "Cell REV-TFRL-1 on TRAIN Fold A 1,080: with the Reviewer node's instruction moved to the contrastive "
            "review form selected offline over sealed TRAIN R01C trajectories, does the system stay within its "
            "own null against the in-chain A/A (the AGREE arm with G5's Reviewer instruction), and what is the "
            "node's own within-trajectory credit -- its loop value over its own first drafts, per error class of "
            "the pre-review draft -- beside the A/A's? " + THE_POLICY + " Admitted on NO HARM (owner decision "
            "127), never reported as a gain; the declared expectation is a measured transfer below the design's "
            "benefit bar (decision 139). Development numbers only (owner decisions 28 and 86); never a test "
            "claim. Nothing here authorises a flight, a readiness flip or an admission entry."),
        readiness_reason=(
            "Cell REV-TFRL-1 registered before contact on " + args.date + " from the committed AGREE arm fragments "
            "by script (decision 58) with the Reviewer instruction moved to the offline-selected contrastive form. "
            "Comparator: the in-chain A/A SAEA-SLURP-STAGE3-REVTFRL-AA-FOLD-A-V1 (the AGREE arm with G5's Reviewer "
            "instruction) flown in the same campaign chain; the sealed AGREE arm " + AGREE_RUN + " is context, "
            "never re-flown. HELD: root countersigns the DRAFT exposure rows, mints the admission receipt and "
            "re-pins with scripts/flights/repin_cell.py --set-ready, which mints this cell's own first-phase supply "
            "under its own run id (item E16; expected output digest " + AGREE_SUPPLY_OUTPUT_SHA + "). "
            "--allow-output-change must never be passed."),
        campaign=True, algorithm=label, arm_rows=True)
    written.append("configs/experiment/slurp-native-stage3-revtfrl-fold-a-v1.json")

    # ---- the four-row smoke -----------------------------------------------------------------------
    pairs = substitutions("REVTFRL", "revtfrl", smoke=True)
    derive_baseline(AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-revtfrl-fold-a-smoke-4-baseline-v1.json",
                    pairs, template=NEW_TEMPLATE,
                    what_this_is=("Four-row structural form smoke of cell REV-TFRL-1: the offline-selected "
                                  "contrastive Reviewer instruction on the first four rows of the unchanged TRAIN "
                                  "Fold A roster. " + THE_POLICY))
    written.append("configs/baseline/slurp-native-stage3-revtfrl-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-revtfrl-fold-a-smoke-4-v1.json", pairs, args,
        purpose=("Four-row structural form smoke of cell REV-TFRL-1: that the contrastive Reviewer instruction loads "
                 "by its relpath, that every request fits, that the Reviewer answers with findings and no tool call "
                 "and that the episode completes. Scored by no one and read by no one. " + THE_POLICY),
        readiness_reason=("Four-row form smoke of cell REV-TFRL-1, registered before contact on " + args.date +
                          " from the AGREE smoke fragments by script (decision 58). HELD until root mints the "
                          "admission receipt and re-pins with --set-ready (item E16); --allow-output-change must "
                          "never be passed. Structural form proof only: no score, no read, no claim."),
        campaign=False,
        algorithm={"id": ALGORITHM_ID, "operators_used": ["context_application"], "note": SMOKE_ALGORITHM_NOTE},
        arm_rows=False)
    written.append("configs/experiment/slurp-native-stage3-revtfrl-fold-a-smoke-4-v1.json")

    # ---- the in-chain A/A: the base (AGREE + G5) ---------------------------------------------------
    pairs = substitutions("REVTFRL-AA", "revtfrl-aa", smoke=False)
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-revtfrl-aa-fold-a-baseline-v1.json", pairs,
                    template=G5_TEMPLATE,
                    what_this_is=("The IN-CHAIN A/A REPLICATE and control of cell REV-TFRL-1: the BASE the brief "
                                  "names -- the AGREE arm (w_agree 1.0, k 60, fuse 8-1-8) with G5's repaired "
                                  "Reviewer instruction " + G5_TEMPLATE + " -- re-flown in the same campaign chain "
                                  "so the Reviewer-policy delta is read against a within-chain null (measurement "
                                  "instrument rules 3 and 4). Its own prepared first-phase supply must reproduce the "
                                  "sealed AGREE arm's output digest " + AGREE_SUPPLY_OUTPUT_SHA + "."))
    written.append("configs/baseline/slurp-native-stage3-revtfrl-aa-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-revtfrl-aa-fold-a-v1.json", pairs, args,
        purpose=("The in-chain A/A replicate of cell REV-TFRL-1: the base (the AGREE arm with G5's Reviewer "
                 "instruction), re-flown in the same campaign chain, to supply the within-chain null the "
                 "Reviewer-policy delta is read at and the base Reviewer's own credit beside the arm's. It makes no "
                 "claim of its own and admits nothing; it is the instrument. Development numbers only (owner "
                 "decisions 28 and 86)."),
        readiness_reason=("The in-chain A/A replicate of cell REV-TFRL-1, registered before contact on " + args.date +
                          " from the committed AGREE arm fragments by script (decision 58) with G5's Reviewer "
                          "instruction pinned, its own run, attempt and fit ids. HELD until root mints the admission "
                          "receipt and re-pins with --set-ready (item E16); --allow-output-change must never be "
                          "passed. Its prepared supply must reproduce the sealed AGREE output digest "
                          + AGREE_SUPPLY_OUTPUT_SHA + "."),
        campaign=True, algorithm={"id": "none", "operators_used": [], "note": AA_ALGORITHM_NOTE}, arm_rows=True)
    written.append("configs/experiment/slurp-native-stage3-revtfrl-aa-fold-a-v1.json")

    plan = {
        "cells": [
            {"cell": "slurp-native-stage3-revtfrl-aa-fold-a-v1", "experiment": "slurp-native-stage3-revtfrl-aa-fold-a-v1"},
            {"cell": "slurp-native-stage3-revtfrl-fold-a-v1", "experiment": "slurp-native-stage3-revtfrl-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }
    wr(CAMPAIGN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN)
    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
