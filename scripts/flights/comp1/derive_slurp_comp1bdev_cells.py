#!/usr/bin/env python3
"""Derive cell A2 -- COMP-1b on DEV-2000-ADDED (owner decision 198) -- from the committed
COMP-1 DEV-2000-ADDED placeholder fragments (decision 58: script-derived registrations).

WHY. Owner decision 198 defines A2 as COMP-1b on the fresh DEV-2000-ADDED roster. The
placeholder package ``docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1``
registered COMP-1 (WITH the citation contract) on that roster with its expectation left
as the literal ``TO-BE-DECLARED-...`` string; COMP-1b (COMP-1 minus the citation contract)
replaced COMP-1 on Fold A after the 2026-09-29 SLU-harm attribution note. A2 therefore
supersedes the placeholder arm and smoke.

WHAT A2 IS. The placeholder's own committed DEV arm and smoke with exactly the change
COMP-1b made on Fold A: the citation contract's four leaf JSON paths revert to the locked
plan's own non-cited program (one arming across three JSON locations). This is a
commuting square, and ``write_slurp_comp1bdev_registration.py`` proves both edges from the
composed configs:

    COMP-1 Fold A  --(citation reverted)-->  COMP-1b Fold A   (the flown COMP-1b arm)
         |                                         |
    (roster re-target)                       (roster re-target)
         v                                         v
    COMP-1 DEV (placeholder)  --(citation reverted)-->  A2 = COMP-1b DEV (this cell)

i.e. A2 differs from the placeholder arm by exactly the four citation leaves plus
bookkeeping, and from the flown COMP-1b Fold A arm by exactly the paths the placeholder
arm differs from the flown COMP-1 Fold A arm (the roster re-target plus this roster's own
agreement-table pin) plus bookkeeping.

THE IN-CHAIN A/A is the placeholder chain's own A/A cell
``slurp-native-stage3-comp1-aa-dev2000-added-v1`` (the sealed DEV plan arm's bytes at recall
k 60), unchanged and not re-derived: the citation contract never touched it. The new
campaign plan carries that A/A and then the A2 arm, exactly as the placeholder chain
declared (instrument rule 3).

Config only: two baselines, two experiment fragments and one campaign plan. No contact,
no ledger row, no receipt, no flip.

    python scripts/flights/comp1/derive_slurp_comp1bdev_cells.py --date 2026-09-29
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PARENT_ARM_BASELINE = "configs/baseline/slurp-native-stage3-comp1-dev2000-added-baseline-v1.json"
PARENT_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-comp1-dev2000-added-smoke-4-baseline-v1.json"
PARENT_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-comp1-dev2000-added-v1.json"
PARENT_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-comp1-dev2000-added-smoke-4-v1.json"

AA_CELL = "slurp-native-stage3-comp1-aa-dev2000-added-v1"
AA_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1"
ARM_CELL = "slurp-native-stage3-comp1b-dev2000-added-v1"
SMOKE_CELL = "slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-comp1b-dev2000-added-v1.json"

CITED_POLICY = "phase-native-candidates-review-revise-cited-v1"
CITED_RESPONSE_FORMAT = "saea-solver-cited-answer-v1"
CITED_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_cited_v1.txt"
CITED_NORMALISER = "saea-deliver-cited-answer-normalise-v3-v1"
PLAN_POLICY = "phase-native-candidates-review-revise-v1"
PLAN_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_v2.txt"
PLAN_NORMALISER = "saea-deliver-normalise-v3"

DEV_AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1/agreement.jsonl"
CENTROID_RELPATH = "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl"
#: The placeholder arm's own prepared supply OUTPUT digest (its README): A2's own supply,
#: minted at the flip, is expected to reproduce it, since the citation contract never
#: touches the first-phase Perception supply.
PLACEHOLDER_ARM_SUPPLY_OUTPUT = "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"
PLACEHOLDER_SMOKE_SUPPLY_OUTPUT = "d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083"

THE_COMPOSITION = (
    "A2 is cell COMP-1b (COMP-1 minus the citation contract) on the DEV-2000-ADDED roster (owner "
    "decision 198), derived from the committed COMP-1 DEV-2000-ADDED placeholder by reverting the "
    "citation contract alone -- the same one change COMP-1b made on Fold A. It composes on the sealed "
    "DEV-2000-ADDED plan arm: (1) the agreement term exactly as AGREE / COMP-1 / COMP-1b carry it "
    "(w_agree 1.0 over the pre-computed, self-excluded exemplar-intent vote, w_cos 1.0, w_prior 0.0, "
    "recall k 60, delivered width 8 -- fuse_coverage m 8 / c 1 / top_l 8), with THIS roster's own vote "
    "table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1; (2) the centroid boundary key exactly "
    "as KPROBE pins it; (3) REVERTED: the citation contract's four keys are the locked plan's own "
    "non-cited program -- policy phase-native-candidates-review-revise-v1, Solver instruction "
    "probes/slurp_native_role_solver_v2.txt, no response format, deliver_normaliser "
    "saea-deliver-normalise-v3. (4) Nothing else: roster, geometry, session, the 11-contact ceiling, "
    "the three stores' pins, exemplar k 20, role graph, templates and the DEV scorer are the "
    "placeholder's own committed bytes."
)

ARM_ALGORITHM_NOTE = (
    "A2 composes the SAME two typed, executable consumption actions COMP-1b composed on Fold A -- a "
    "rank weight over a pre-computed vote and a retrieval key file -- each chosen and credited OFFLINE "
    "over sealed bytes (CONV, KPROBE), the citation contract removed after the 2026-09-29 SLU-harm "
    "attribution. It is the fresh-roster replication of the COMP-1b Fold A read, read against its own "
    "in-chain A/A. Operator context_application: the composed actions are written into every row's "
    "Perception supply. No rollout, per-sample scoring, credit assignment or update of its own."
)
SMOKE_ALGORITHM_NOTE = (
    "The four-row structural form smoke of A2: the same two composed actions (agreement term with this "
    "roster's table, centroid key) on four DEV-2000-ADDED rows under the locked plan's own non-cited "
    "Solver program; scored by no one and read by no one."
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


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the placeholder's committed ids to A2's."""

    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-V1", "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-comp1-dev2000-added-smoke-4-generation-v1", "attempt-slurp-native-stage3-comp1b-dev2000-added-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-comp1-dev2000-added-smoke-4-fit-v1", "attempt-slurp-native-stage3-comp1b-dev2000-added-smoke-4-fit-v1"),
            ("slurp-native-stage3-comp1-dev2000-added-smoke-4-baseline-v1", "slurp-native-stage3-comp1b-dev2000-added-smoke-4-baseline-v1"),
            ("slurp-native-stage3-comp1-dev2000-added-smoke-4-v1", SMOKE_CELL),
        ]
    return [
        ("SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-FIT-V1", "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-FIT-V1"),
        ("SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1", "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1"),
        ("attempt-slurp-native-stage3-comp1-dev2000-added-generation-v1", "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1"),
        ("attempt-slurp-native-stage3-comp1-dev2000-added-fit-v1", "attempt-slurp-native-stage3-comp1b-dev2000-added-fit-v1"),
        ("slurp-native-stage3-comp1-dev2000-added-baseline-v1", "slurp-native-stage3-comp1b-dev2000-added-baseline-v1"),
        ("slurp-native-stage3-comp1-dev2000-added-v1", ARM_CELL),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent_path: str, out_path: str, pairs: list[tuple[str, str]], *, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own supply
    document["what_this_is"] = what_this_is

    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0} or perception["k"] != 60:
        raise SystemExit("the parent (COMP-1 DEV placeholder) is not at w_agree 1.0 / k 60")
    if perception.get("agreement_source", {}).get("relpath") != DEV_AGREEMENT_RELPATH:
        raise SystemExit("the parent does not pin THIS roster's agreement table")
    if perception["facet_source"]["relpath"] != CENTROID_RELPATH:
        raise SystemExit("the parent is not pinned to the centroid key")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8} or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary delivered width or tau moved")
    if document["policy"] != CITED_POLICY:
        raise SystemExit("the parent is not on the cited policy; refusing to derive from it")
    solver = document["phase_material"]["solver"]
    if solver["instruction_template"] != CITED_SOLVER_TEMPLATE or solver["response_format_id"] != CITED_RESPONSE_FORMAT:
        raise SystemExit("the parent's Solver material is not the cited-answer contract")
    if document["native_episode"]["deliver_normaliser"] != {"normaliser": CITED_NORMALISER}:
        raise SystemExit("the parent's deliver_normaliser is not the cited-answer unwrap")

    # THE ONE CHANGE (COMP-1b's): revert the citation contract's four keys.
    document["policy"] = PLAN_POLICY
    solver["instruction_template"] = PLAN_SOLVER_TEMPLATE
    solver["response_format_id"] = None
    document["native_episode"]["deliver_normaliser"] = {"normaliser": PLAN_NORMALISER}
    wr(out_path, dump_like(raw, document))


def derive_experiment(parent_path: str, out_path: str, pairs, args, *, purpose: str, readiness_reason: str,
                      preparation_requirements: list[dict], campaign: bool, algorithm: dict) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": preparation_requirements, "state": "held"}
    document["stage3_algorithm"] = algorithm
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    for name in ("arm", "smoke"):
        parser.add_argument(f"--{name}-supply-sha256", default="0" * 64)
    args = parser.parse_args(argv)

    parent_arm = json.loads(rd(PARENT_ARM_EXPERIMENT))
    agreement_requirement = next(
        r for r in parent_arm["cells"][0]["readiness"]["requirements"] if r["relpath"] == DEV_AGREEMENT_RELPATH
    )
    supply_reason = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this cell's own run "
        "id with core.flight.cli prepare-supply at the flip from the sealed DEV-2000-ADDED speech-query "
        "segment vectors, the CENTROID key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this "
        "roster's sealed agreement table -- the same sources the superseded COMP-1 DEV placeholder arm's "
        "supply was built from -- with zero model, tokenizer, encoder, scorer or server contacts. The "
        "citation contract acts only on the Solver phase, so the output digest is expected to equal the "
        "placeholder's own (arm " + PLACEHOLDER_ARM_SUPPLY_OUTPUT + ", smoke "
        + PLACEHOLDER_SMOKE_SUPPLY_OUTPUT + "); the flip's re-derivation checks this. E16: this cell pins "
        "its own. --allow-output-change must never be passed."
    )
    written: list[str] = []

    arm_pairs = substitutions(smoke=False)
    derive_baseline(PARENT_ARM_BASELINE, "configs/baseline/slurp-native-stage3-comp1b-dev2000-added-baseline-v1.json", arm_pairs,
                    what_this_is="Cell A2: COMP-1b on DEV-2000-ADDED (owner decision 198). " + THE_COMPOSITION)
    written.append("configs/baseline/slurp-native-stage3-comp1b-dev2000-added-baseline-v1.json")
    derive_experiment(
        PARENT_ARM_EXPERIMENT, f"configs/experiment/{ARM_CELL}.json", arm_pairs, args,
        purpose=(
            "Cell A2 (owner decision 198) on DEV-2000-ADDED 1,000: does COMP-1b -- the agreement term and "
            "the centroid boundary key with the citation contract removed -- replicate on a fresh roster "
            "the intent gain the COMP-1b TRAIN Fold A read measured, against its own in-chain A/A "
            + AA_RUN + " (the sealed DEV plan arm's bytes at recall k 60), with official pooled SLU-F1 "
            "(slurp-slu-official, the DEV sibling) the non-inferiority guard at this roster's own null "
            "(h_SLU 1.2525)? " + THE_COMPOSITION + " expected_effect_pp is the COMP-1b Fold A read's intent "
            "point estimate (owner decision 139: a measured number, not a prior). Development numbers only "
            "(owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness "
            "flip or an admission entry."
        ),
        readiness_reason=(
            "Cell A2 registered before contact on " + args.date + " from the committed COMP-1 DEV-2000-ADDED "
            "placeholder arm (decision 58: script-derived) by reverting the citation contract alone, the "
            "one change COMP-1b made on Fold A; it SUPERSEDES the placeholder arm. In-chain A/A: "
            + AA_RUN + " (the placeholder chain's own A/A cell, unchanged), flown in the same campaign "
            "before this arm. HELD: root mints the admission receipt and re-pins with "
            "scripts/flights/repin_cell.py --set-ready, which also mints this cell's own first-phase supply "
            "(item E16). --allow-output-change must never be passed."
        ),
        preparation_requirements=[
            agreement_requirement,
            {"kind": "preparation", "reason": supply_reason,
             "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1/phase-supply-v1.json",
             "sha256": args.arm_supply_sha256},
        ],
        campaign=True,
        algorithm={"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"], "note": ARM_ALGORITHM_NOTE},
    )
    written.append(f"configs/experiment/{ARM_CELL}.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(PARENT_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-comp1b-dev2000-added-smoke-4-baseline-v1.json", smoke_pairs,
                    what_this_is="Four-row structural form smoke of cell A2 (COMP-1b on DEV-2000-ADDED). " + THE_COMPOSITION)
    written.append("configs/baseline/slurp-native-stage3-comp1b-dev2000-added-smoke-4-baseline-v1.json")
    derive_experiment(
        PARENT_SMOKE_EXPERIMENT, f"configs/experiment/{SMOKE_CELL}.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell A2: that this roster's agreement table and the centroid "
            "key file load and hash-verify, that the boundary channel delivers eight entries, that the "
            "Solver answers under the locked plan's own non-cited program and that every request fits and "
            "the episode completes. Scored by no one and read by no one. " + THE_COMPOSITION
        ),
        readiness_reason=(
            "Four-row form smoke of cell A2, registered before contact on " + args.date + " from the "
            "placeholder's own committed smoke fragments (decision 58) by reverting the citation contract "
            "alone; supersedes the placeholder smoke. HELD until root mints the admission receipt and "
            "re-pins with --set-ready (item E16); --allow-output-change must never be passed."
        ),
        preparation_requirements=[
            agreement_requirement,
            {"kind": "preparation", "reason": supply_reason,
             "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-SMOKE-4-V1/phase-supply-v1.json",
             "sha256": args.smoke_supply_sha256},
        ],
        campaign=False,
        algorithm={"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"], "note": SMOKE_ALGORITHM_NOTE},
    )
    written.append(f"configs/experiment/{SMOKE_CELL}.json")

    plan = {"cells": [{"cell": AA_CELL, "experiment": AA_CELL}, {"cell": ARM_CELL, "experiment": ARM_CELL}],
            "schema": "saea-campaign-plan-v1"}
    wr(CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN_PLAN)
    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
