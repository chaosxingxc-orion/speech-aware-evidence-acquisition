#!/usr/bin/env python3
"""Derive the two COMP-1b cells -- COMP-1 MINUS the citation contract -- from cell
COMP-1's OWN committed fragments (decision 58: script-derived registrations).

WHY. The attribution note on branch ``fable/comp1slu``
(``docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md``) names the Solver
cited-answer contract ``saea-solver-cited-answer-v1`` as the cause of COMP-1's
official SLU-F1 guard loss (-2.24 [-3.97, -0.47]): it makes the Solver emit +102
false-positive entities on the 414 zero-gold rows. The I7n unwrap normaliser adds
0 entities (byte-proven) and the AGREE supply is not the cause (AGREE vs its own
A/A is FP -5, SLU +1.85). The note recommends the smallest next cell: COMP-1 minus
the citation contract, i.e. the agreement term (AGREE) plus the centroid boundary
key (KPROBE) alone, read against the SAME in-chain A/A COMP-1 used.

WHAT COMP-1b IS. Cell COMP-1's own committed arm (``configs/baseline/
slurp-native-stage3-comp1-fold-a-baseline-v1.json`` /
``configs/experiment/slurp-native-stage3-comp1-fold-a-v1.json``, both already
FLOWN and SEALED) with exactly ONE change: the citation-contract factor is
REVERTED to the locked v2.0 plan's own non-cited program. Four leaf JSON paths
move, one arming across three JSON locations (``rails.native_episode_config``
refuses the contract without the unwrapping normaliser and the normaliser without
the contract, fail-closed):

    policy:                                       phase-native-candidates-review-revise-cited-v1  -> phase-native-candidates-review-revise-v1
    phase_material.solver.instruction_template:    probes/slurp_native_role_solver_cited_v1.txt     -> probes/slurp_native_role_solver_v2.txt
    phase_material.solver.response_format_id:      saea-solver-cited-answer-v1                      -> null
    native_episode.deliver_normaliser.normaliser:  saea-deliver-cited-answer-normalise-v3-v1         -> saea-deliver-normalise-v3

Nothing else moves: the agreement term (``rank_weights.w_agree`` 1.0, the
self-excluded exemplar-intent vote, recall ``k`` 60) and the centroid boundary key
(``facet_source`` the released centroid vectors) are COMP-1's own committed bytes,
untouched. The roster, geometry, session, phase-program contact ceiling, the three
stores' pins, exemplar k of 20, role graph and scorers are therefore also COMP-1's
own, untouched.

TWO CELLS, not three: the arm and its four-row structural form smoke. NO new
in-chain A/A is registered. Owner decision 160 (and its reuse by cell G5) already
establishes the pattern of ONE shared, already-sealed in-chain A/A serving more
than one composed family in the same chain; COMP-1b goes one step further and
reuses that A/A as a CROSS-FLIGHT comparator without flying it again at all (it is
sealed and consumed, never re-flown). The campaign plan therefore carries the
COMP-1b arm ALONE, exactly as cell G5's campaign plan carried its arm alone after
decision 160 dropped its own A/A.

This script writes CONFIG ONLY: two baselines, two experiment fragments and one
campaign plan. It performs no contact, writes no ledger row, mints no decision
receipt and flips nothing.

    python scripts/flights/comp1/derive_slurp_comp1b_cell.py --date 2026-09-29
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

COMP1_ARM_BASELINE = "configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json"
COMP1_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-comp1-fold-a-smoke-4-baseline-v1.json"
COMP1_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-comp1-fold-a-v1.json"
COMP1_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-comp1-fold-a-smoke-4-v1.json"

COMP1_ARM_RUN = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
COMP1_AA_RUN = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"

#: The citation contract: four keys, one arming (``rails.solver_citation``).
CITED_POLICY = "phase-native-candidates-review-revise-cited-v1"
CITED_RESPONSE_FORMAT = "saea-solver-cited-answer-v1"
CITED_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_cited_v1.txt"
CITED_NORMALISER = "saea-deliver-cited-answer-normalise-v3-v1"
PLAN_POLICY = "phase-native-candidates-review-revise-v1"
PLAN_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_v2.txt"
PLAN_NORMALISER = "saea-deliver-normalise-v3"

PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1"

THE_COMPOSITION = (
    "COMP-1b is cell COMP-1 minus the citation contract, and nothing else. It composes the SAME two "
    "registered changes COMP-1 composed on the locked v2.0 plan: (1) the agreement term exactly as "
    "cell AGREE and cell COMP-1 carry it: the intent-boundary Perception channel ranks with w_agree "
    "1.0 over the pre-computed, self-excluded exemplar-intent vote, w_cos 1.0, w_prior 0.0, recall k "
    "60, delivered width unchanged at 8 (fuse_coverage m 8 / c 1 / top_l 8). (2) The centroid boundary "
    "key exactly as cell KPROBE and cell COMP-1 pin it: that channel's facet_source is the "
    "unit-normalised mean construction-TRAIN utterance vector per released intent (zero encoder "
    "contacts) instead of the written one-line description; the delivered body is unchanged. (3) "
    "REVERTED: the citation contract's four keys return to the locked plan's own non-cited program -- "
    "policy phase-native-candidates-review-revise-v1, Solver instruction "
    "probes/slurp_native_role_solver_v2.txt, no response format, deliver_normaliser "
    "saea-deliver-normalise-v3. (4) Nothing else: the roster, the geometry, the session, the phase "
    "program's 11-contact ceiling, the three stores' snapshots and releases, the exemplar k of 20, the "
    "role graph, the Perception / Reviewer / Planner templates and the scorers are COMP-1's own "
    "committed bytes, byte for byte."
)

ARM_ALGORITHM_NOTE = (
    "COMP-1b composes the SAME two typed, executable consumption actions COMP-1 composed -- a rank "
    "weight over a pre-computed vote and a retrieval key file -- each already chosen and credited "
    "OFFLINE over sealed bytes (the 2026-09-26 rank diagnostic and the 2026-09-27 key diagnostic, the "
    "CONV and KPROBE conversion probes); the third action COMP-1 composed (the Solver's citation "
    "answer contract) is REMOVED after the 2026-09-29 SLU-harm attribution named it as the cause of "
    "COMP-1's guard loss. The GPU is re-entered once for the two-factor composed policy, read against "
    "the SAME sealed in-chain A/A COMP-1 used (cross-flight, never re-flown). The operator this cell "
    "exercises is context_application: the composed actions are written into every row's Perception "
    "supply. It performs no rollout, no per-sample scoring, no credit assignment and no update of its "
    "own."
)
SMOKE_ALGORITHM_NOTE = (
    "The four-row structural form smoke of the composed COMP-1b arm: the same two composed actions "
    "(agreement term, centroid key) on the first four rows of the unchanged roster, under the "
    "locked plan's own non-cited Solver program; scored by no one and read by no one, it exercises "
    "context_application only in the sense that the composed actions reach four rows' contexts."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    """Serialise ``obj`` with the indentation the parent file used, so a derived
    fragment diffs against its parent line for line."""

    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from cell COMP-1's own committed ids to COMP-1b's."""

    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-comp1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-comp1b-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-comp1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-comp1b-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-comp1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-comp1b-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-stage3-comp1-fold-a-smoke-4-v1", "slurp-native-stage3-comp1b-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1", "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-comp1-fold-a-generation-v1", "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-comp1-fold-a-fit-v1", "attempt-slurp-native-stage3-comp1b-fold-a-fit-v1"),
        ("slurp-native-stage3-comp1-fold-a-baseline-v1", "slurp-native-stage3-comp1b-fold-a-baseline-v1"),
        ("slurp-native-stage3-comp1-fold-a-v1", "slurp-native-stage3-comp1b-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent_path: str, out_path: str, pairs: list[tuple[str, str]], *, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    # E16: the flip mints this cell's OWN supply under its own run id. Never
    # inherit the parent's (COMP-1's), and never pass --allow-output-change.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is

    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0} or perception["k"] != 60:
        raise SystemExit("the parent (COMP-1) is not at w_agree 1.0 / k 60 as flown")
    if "agreement_source" not in perception:
        raise SystemExit("the parent (COMP-1) does not declare an agreement_source")
    if perception["facet_source"]["relpath"] != "prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl":
        raise SystemExit("the parent (COMP-1) is not pinned to the centroid key")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8} or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary delivered width or tau moved")

    if document["policy"] != CITED_POLICY:
        raise SystemExit("the parent (COMP-1) is not on the cited policy; refusing to derive from it")
    solver = document["phase_material"]["solver"]
    if solver["instruction_template"] != CITED_SOLVER_TEMPLATE or solver["response_format_id"] != CITED_RESPONSE_FORMAT:
        raise SystemExit("the parent's Solver material is not the cited-answer contract")
    if document["native_episode"]["deliver_normaliser"] != {"normaliser": CITED_NORMALISER}:
        raise SystemExit("the parent's deliver_normaliser is not the cited-answer unwrap")

    # THE ONE CHANGE: revert the citation contract's four keys to the locked
    # plan's own non-cited program. Nothing else in this baseline is touched --
    # the agreement term, the centroid key, the three stores' pins and every
    # other byte are COMP-1's own, carried over unchanged by the substitution.
    document["policy"] = PLAN_POLICY
    solver["instruction_template"] = PLAN_SOLVER_TEMPLATE
    solver["response_format_id"] = None
    document["native_episode"]["deliver_normaliser"] = {"normaliser": PLAN_NORMALISER}

    wr(out_path, dump_like(raw, document))


def derive_experiment(
    parent_path: str,
    out_path: str,
    pairs: list[tuple[str, str]],
    args: argparse.Namespace,
    *,
    purpose: str,
    readiness_reason: str,
    preparation_requirements: list[dict],
    campaign: bool,
    algorithm: dict,
) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    # HELD: back to a fresh registration. Drop whatever readiness COMP-1's own
    # committed fragment carries (it is "ready", flown and sealed) and start
    # this cell with the cell's own preparation requirements only; the decision
    # requirement is inserted by scripts/flights/repin_cell.py --set-ready once
    # root has minted the admission receipt.
    cell["readiness"] = {
        "reason": readiness_reason,
        "requirements": preparation_requirements,
        "state": "held",
    }
    document["stage3_algorithm"] = algorithm
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    for name in ("arm", "smoke"):
        parser.add_argument(f"--{name}-supply-sha256", default="0" * 64)
    args = parser.parse_args(argv)
    for value in (args.arm_supply_sha256, args.smoke_supply_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("every supply digest must be a lowercase sha256")

    written: list[str] = []

    agreement_requirement = {
        "kind": "preparation",
        "reason": (
            "The pre-computed exemplar-intent AGREEMENT table this cell's boundary channel ranks with, "
            "exactly the artifact cells AGREE and COMP-1 registered and flew: built model-free by "
            "scripts/build_slurp_intent_exemplar_agreement.py from the pinned exemplar snapshot, the "
            "pinned pool key vectors and this roster's own pinned speech query vectors -- zero model, "
            "server, encoder, embedder, scorer, network and GPU contacts. The centroid key file is "
            "deliberately NOT a readiness requirement: it is pinned where the loader verifies it "
            "(facet_source.sha256) and its receipt in preparation_source_receipts, as cells KPROBE and "
            "COMP-1 registered it."
        ),
        "relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl",
        "sha256": "018ca6ef0d10bbf8d19645994420820faf7f31961cf91a6080116e4b434016c1",
    }
    supply_reason = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this cell's own "
        "run id with core.flight.cli prepare-supply from the same sealed Fold A speech-query segment "
        "vectors, the CENTROID key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the sealed "
        "agreement table -- the SAME two sources cell COMP-1's own first-phase supply was built from -- "
        "with zero model, tokenizer, encoder, scorer or server contacts. Because the citation contract "
        "acts only on the Solver phase and never on Perception's first-phase supply, this cell's output "
        "digest is expected to equal COMP-1's own arm supply digest "
        "ce68bebcf2bbf5502b081221a92c3fde1095da3979106bcdddb6eeeca9e9c41a exactly; the flip's re-derivation "
        "checks this. E16: a prepared artifact is evidence only for the implementation that produced it, "
        "so this cell pins its own rather than inheriting COMP-1's. --allow-output-change must never be "
        "passed."
    )

    # ---- the COMP-1b arm ---------------------------------------------------
    arm_pairs = substitutions(smoke=False)
    derive_baseline(
        COMP1_ARM_BASELINE,
        "configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json",
        arm_pairs,
        what_this_is=(
            "Cell COMP-1b: cell COMP-1 minus the citation contract (2026-09-29 SLU-harm attribution, "
            "branch fable/comp1slu). " + THE_COMPOSITION
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-comp1b-fold-a-baseline-v1.json")
    derive_experiment(
        COMP1_ARM_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-comp1b-fold-a-v1.json",
        arm_pairs,
        args,
        purpose=(
            "Cell COMP-1b on TRAIN Fold A 1,080: with the Solver cited-answer contract removed (named as "
            "the cause of COMP-1's official SLU-F1 guard loss by the 2026-09-29 attribution note on "
            "branch fable/comp1slu), does the two-factor composition of the agreement term and the "
            "centroid boundary key alone raise intent-recognition accuracy (primary, owner decision 133) "
            "against the SAME sealed in-chain A/A cell COMP-1 used, with official pooled SLU-F1 the "
            "non-inferiority guard, without the guard loss the citation contract caused? " + THE_COMPOSITION
            + " The declared expected effect (4.26 pp intent, the measured COMP-1-vs-A/A read minus "
            "nothing attributable to the citation contract on the intent side) and the SLU guard "
            "(-1.2485 pp, the Fold A own null) are declared here from measured numbers, never a prior "
            "(owner decision 139). Development numbers only (owner decisions 28 and 86); never a test "
            "claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell COMP-1b registered before contact on "
            + args.date
            + " from cell COMP-1's OWN committed, flown and sealed fragments (decision 58: script-derived "
            "registrations) by reverting the citation contract's four keys to the locked plan's own "
            "non-cited program; the agreement term and the centroid key are COMP-1's own committed bytes, "
            "untouched. Comparator: the EXISTING SEALED in-chain A/A " + COMP1_AA_RUN + ", cross-flight, "
            "never re-flown (owner decision 160's shared-A/A pattern, as cell G5 reused it). HELD: root "
            "mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready, which "
            "also mints this cell's own first-phase supply under its own run id (item E16). "
            "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness "
            "flip or an admission entry."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_reason,
                "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1/phase-supply-v1.json",
                "sha256": args.arm_supply_sha256,
            },
        ],
        campaign=True,
        algorithm={
            "id": "sealed-credit-system-policy-v1",
            "operators_used": ["context_application"],
            "note": ARM_ALGORITHM_NOTE,
        },
    )
    written.append("configs/experiment/slurp-native-stage3-comp1b-fold-a-v1.json")

    # ---- the four-row form smoke -------------------------------------------
    smoke_pairs = substitutions(smoke=True)
    derive_baseline(
        COMP1_SMOKE_BASELINE,
        "configs/baseline/slurp-native-stage3-comp1b-fold-a-smoke-4-baseline-v1.json",
        smoke_pairs,
        what_this_is=(
            "Four-row structural form smoke of cell COMP-1b: the same two composed actions (agreement "
            "term, centroid key) on the first four rows of the unchanged TRAIN Fold A roster, under the "
            "locked plan's own non-cited Solver program. " + THE_COMPOSITION
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-comp1b-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        COMP1_SMOKE_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-comp1b-fold-a-smoke-4-v1.json",
        smoke_pairs,
        args,
        purpose=(
            "Four-row structural form smoke of cell COMP-1b: that the agreement table and the centroid "
            "key file load and hash-verify, that the boundary channel still delivers eight entries, that "
            "the Solver answers under the locked plan's own non-cited program and that every request fits "
            "and the episode completes. It is scored by no one and read by no one: four rows can never be "
            "evidence of benefit. " + THE_COMPOSITION
        ),
        readiness_reason=(
            "Four-row form smoke of cell COMP-1b, registered before contact on "
            + args.date
            + " from cell COMP-1's own committed smoke fragments (decision 58) by reverting the citation "
            "contract alone. HELD until root mints the admission receipt and re-pins with --set-ready, "
            "which re-mints this cell's own first-phase supply (item E16); --allow-output-change must "
            "never be passed. Structural form proof only: no score, no read, no claim."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_reason,
                "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1/phase-supply-v1.json",
                "sha256": args.smoke_supply_sha256,
            },
        ],
        campaign=False,
        algorithm={
            "id": "sealed-credit-system-policy-v1",
            "operators_used": ["context_application"],
            "note": SMOKE_ALGORITHM_NOTE,
        },
    )
    written.append("configs/experiment/slurp-native-stage3-comp1b-fold-a-smoke-4-v1.json")

    # ---- the campaign plan: the arm ALONE, the comparator reused unflown ---
    plan = {
        "cells": [
            {"cell": "slurp-native-stage3-comp1b-fold-a-v1", "experiment": "slurp-native-stage3-comp1b-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }
    wr("configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json", json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append("configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json")

    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
