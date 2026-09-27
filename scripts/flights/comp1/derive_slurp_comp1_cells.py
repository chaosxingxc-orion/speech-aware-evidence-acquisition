#!/usr/bin/env python3
"""Derive the three COMP-1 cells -- the FIRST COMPOSED Stage-3 arm (owner decisions
138 and 152) -- from the LOCKED PLAN baseline's own fragments (decision 58:
script-derived registrations).

WHAT COMP-1 IS. The locked v2.0 plan (the sealed PLAN arm
``SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1``; the cell the AGREE and KPROBE packages
derive from) with FOUR changes composed, each already registered and measured
separately, and nothing else:

  1. the AGREEMENT TERM exactly as the AGREE arm carries it
     (``configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json``):
     ``knowledge_stores.intent-boundaries.phase_supply.perception`` at
     ``rank_weights.w_agree`` 1.0 over the pre-computed, self-excluded
     exemplar-intent vote (``agreement_source``), recall ``k`` 60, delivered
     ``fuse_coverage`` m 8 / c 1 / top_l 8, and the agreement table's receipt in
     ``preparation_source_receipts``;
  2. the CENTROID BOUNDARY KEY exactly as KPROBE pins it
     (``configs/baseline/slurp-native-stage3-kprobe-fold-a-55-baseline-v1.json``):
     the same channel's ``facet_source`` moved to
     ``prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl`` and the
     key file's receipt appended to ``preparation_source_receipts``;
  3. the CITATION CONTRACT as a row-127 no-harm base item (decision 152):
     ``policy`` ``phase-native-candidates-review-revise-cited-v1``, the Solver's
     ``response_format_id`` ``saea-solver-cited-answer-v1``, its instruction
     ``probes/slurp_native_role_solver_cited_v1.txt`` and
     ``native_episode.deliver_normaliser`` ``saea-deliver-cited-answer-normalise-v3-v1``
     (``rails.solver_citation``; ``rails.native_episode_config`` refuses the
     contract without the unwrapping normaliser and the normaliser without the
     contract, so the four keys are ONE arming);
  4. nothing else. The registration writer proves the composed-config diff
     against the locked PLAN cell from the composed configs and
     ``tests/unit/test_comp1_config.py`` re-proves it.

The two factors 1 and 2 act on the same retrieval channel and are read here as
ONE composed policy: the ranker fuses ``w_cos`` x cosine-to-the-centroid-key +
``w_agree`` x the exemplar vote and the fuser delivers eight, exactly as each
package flew its own factor alone.

THREE CELLS, because a cross-flight contrast against a sealed comparator needs an
in-chain replicate (``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``
rules 3 and 4):

  * the COMP-1 arm on TRAIN Fold A 1,080;
  * its four-row structural form smoke;
  * the IN-CHAIN A/A: the PLAN lock's own bytes re-flown in the SAME campaign
    chain -- ``w_agree`` 0.0 with no ``agreement_source``, the WRITTEN boundary
    key, the un-armed citation default -- carrying the same widened recall
    ``k`` 60 the AGREE A/A carried, which is a proven no-op (its prepared
    first-phase supply reproduces the sealed comparator's output digest
    ``ba5e1faa...`` and its rendered request bytes are the comparator's on all
    four phases). The A/A therefore differs from the arm in the three composed
    factors ALONE, and its prepared-output digest must again equal
    ``ba5e1faa...`` -- the registration refuses otherwise.

Every cell drops ``prepared_phase_supply`` so the coordinator's flip mints each
cell's OWN first-phase supply under its own run id (item E16); each cell pins its
own ``native_contact_fit`` ids; ``--allow-output-change`` must never be passed.
The caps are the PLAN family's own (AGREE arithmetic): the citation contract adds
instruction and output TOKENS per Solver contact, never contacts.

This script writes CONFIG ONLY: three baselines, three experiment fragments and
one campaign plan. It performs no contact, writes no ledger row, mints no
decision receipt and flips nothing.

Two passes, converging in exactly two (the AGREE derivation's rule): pass 1 at
the placeholder supply digests, then ``core.flight.cli prepare-supply`` for each
cell, then pass 2 with the measured digests. ``core.preparation.artifact_inputs``
strips every cell's ``readiness`` block out of ``config_sha256``, so pass 2 cannot
move the artifacts it just pinned.

    python scripts/flights/comp1/derive_slurp_comp1_cells.py --date 2026-09-27 \\
        [--arm-supply-sha256 <64 hex> --aa-supply-sha256 <64 hex> --smoke-supply-sha256 <64 hex>]
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PLAN_ARM_BASELINE = "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json"
PLAN_SMOKE_BASELINE = "configs/baseline/slurp-native-default-plan-lock-smoke-4-baseline-v1.json"
PLAN_ARM_EXPERIMENT = "configs/experiment/slurp-native-default-plan-lock-v1.json"
PLAN_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-default-plan-lock-smoke-4-v1.json"

#: The two registered factor sources, read rather than restated: the agreement
#: term is taken from the AGREE arm's committed baseline and the centroid key
#: from KPROBE's, byte for byte.
AGREE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
KPROBE_BASELINE = "configs/baseline/slurp-native-stage3-kprobe-fold-a-55-baseline-v1.json"

PLAN_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
#: The sealed PLAN preparation's OUTPUT digest. The A/A cell's own prepared
#: supply must reproduce it exactly (the AGREE A/A already did at k 60).
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
WRITTEN_KEY_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"

AGREEMENT_LEDGER_ROW = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1"
AGREEMENT_RECEIPT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json"
CENTROID_ARTIFACT = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
CENTROID_FACETS_RELPATH = f"prepared/{CENTROID_ARTIFACT}/facets.jsonl"
CENTROID_RECEIPT_RELPATH = f"prepared/{CENTROID_ARTIFACT}/receipt.json"

#: The citation contract: four keys, one arming (``rails.solver_citation``).
CITED_POLICY = "phase-native-candidates-review-revise-cited-v1"
CITED_RESPONSE_FORMAT = "saea-solver-cited-answer-v1"
CITED_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_cited_v1.txt"
CITED_NORMALISER = "saea-deliver-cited-answer-normalise-v3-v1"
PLAN_POLICY = "phase-native-candidates-review-revise-v1"
PLAN_SOLVER_TEMPLATE = "probes/slurp_native_role_solver_v2.txt"
PLAN_NORMALISER = "saea-deliver-normalise-v3"

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"

THE_COMPOSITION = (
    "COMP-1 composes FOUR registered changes on the locked v2.0 plan and nothing else. "
    "(1) The agreement term exactly as cell AGREE carries it: the intent-boundary Perception "
    "channel ranks with w_agree 1.0 over the pre-computed, self-excluded exemplar-intent vote, "
    "w_cos 1.0, w_prior 0.0, recall k 60 (at 8 the term is inert, measured), delivered width "
    "unchanged at 8 (fuse_coverage m 8 / c 1 / top_l 8). (2) The centroid boundary key exactly as "
    "cell KPROBE pins it: that channel's facet_source is the unit-normalised mean "
    "construction-TRAIN utterance vector per released intent (zero encoder contacts; the one "
    "intent with no pool member keeps its written key) instead of the written one-line "
    "description; the delivered body is unchanged. (3) The citation contract as a row-127 "
    "no-harm base item (owner decision 152): the Solver answers under "
    "saea-solver-cited-answer-v1 -- the task answer's own bytes plus the supplied evidence ids it "
    "relied on for the intent and for each entity -- under the cited Solver instruction, with the "
    "registered unwrapping normaliser saea-deliver-cited-answer-normalise-v3-v1 (the unwrap, then "
    "the locked plan's own v3 projection) so the delivered text is the answer's own bytes "
    "(invariant I7n); its per-entry credit table is the reward signal every later construction "
    "round reads. (4) Nothing else: the roster, the geometry, the session, the phase program's "
    "11-contact ceiling, the three stores' snapshots and releases, the exemplar k of 20, the "
    "role graph, the Perception / Reviewer / Planner templates and the scorers are the locked "
    "plan's, byte for byte. Factors 1 and 2 act on the SAME retrieval channel and are composed "
    "as one ranker: w_cos x cosine-to-the-centroid-key + w_agree x the exemplar vote, eight "
    "delivered."
)

ARM_ALGORITHM_NOTE = (
    "The FIRST instance of sealed-credit-system-policy-v1 (owner decision 138: every "
    "optimisation round's composed read against the lock IS the cumulative check; decision 152: "
    "COMP-1 is that first composed arm). This cell is the family's step (iv), the re-execution: "
    "three typed, executable consumption actions -- a rank weight over a pre-computed vote, a "
    "retrieval key file, and the Solver's answer contract -- were each chosen and credited "
    "OFFLINE over sealed bytes (the 2026-09-26 rank diagnostic and the 2026-09-27 key "
    "diagnostic, the CONV and KPROBE conversion probes), and the GPU is re-entered once for the "
    "composed policy beside its in-chain replicate. The operator this cell exercises is "
    "context_application: the composed actions are written into every row's Perception supply "
    "and Solver contract. It performs no rollout, no per-sample scoring, no credit assignment "
    "and no update of its own; the citation credit table it seals is the INPUT to the next "
    "round's credit assignment, not this cell's use of that operator."
)
AA_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the locked "
    "plan's own form re-flown in the same chain as the in-chain null and instrument of the "
    "composed COMP-1 arm -- w_agree 0.0, no agreement_source, the written boundary key, the "
    "un-armed citation default. Its prepared first-phase supply reproduces the sealed "
    "comparator's output digest exactly, which is what makes it the instrument."
)
SMOKE_ALGORITHM_NOTE = (
    "The four-row structural form smoke of the composed COMP-1 arm: the same three composed "
    "actions on the first four rows of the unchanged roster, labelled as the arm is because it "
    "flies the arm's form; scored by no one and read by no one, it exercises context_application "
    "only in the sense that the composed actions reach four rows' contexts."
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


def substitutions(tag: str, slug: str, *, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the PLAN fragment to this cell's own."""

    if smoke:
        return [
            ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-FIT-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-default-plan-lock-smoke-4-generation-v1", f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-default-plan-lock-smoke-4-fit-v1", f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-fit-v1"),
            ("slurp-native-default-plan-lock-smoke-4-baseline-v1", f"slurp-native-stage3-{slug}-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-default-plan-lock-smoke-4-v1", f"slurp-native-stage3-{slug}-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-V1"),
        ("attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1", f"attempt-slurp-native-stage3-{slug}-fold-a-generation-v1"),
        ("attempt-slurp-native-default-plan-lock-train-fold-a-fit-v1", f"attempt-slurp-native-stage3-{slug}-fold-a-fit-v1"),
        ("slurp-native-default-plan-lock-baseline-v1", f"slurp-native-stage3-{slug}-fold-a-baseline-v1"),
        ("slurp-native-default-plan-lock-v1", f"slurp-native-stage3-{slug}-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def registered_factors() -> tuple[dict, dict, dict, dict]:
    """``(agreement_source, agreement receipt entry, facet_source, centroid receipt entry)``
    read from the two committed factor baselines, each checked for the identity it
    was registered under before it is composed."""

    agree = json.loads(rd(AGREE_BASELINE))
    agree_p = agree["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if agree_p["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0} or agree_p["k"] != 60:
        raise SystemExit("the AGREE baseline is not at w_agree 1.0 / k 60 as registered")
    if agree_p["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the AGREE baseline's delivered width is not 8-1-8")
    agreement_source = dict(agree_p["agreement_source"])
    if agreement_source["kind"] != "sealed-agreement" or agreement_source["tool_contact_ledger_row"] != AGREEMENT_LEDGER_ROW:
        raise SystemExit("the AGREE baseline's agreement_source is not the registered sealed-agreement pin")
    agreement_receipt = next(
        dict(r) for r in agree["preparation_source_receipts"] if r["relpath"] == AGREEMENT_RECEIPT_RELPATH
    )

    kprobe = json.loads(rd(KPROBE_BASELINE))
    kprobe_p = kprobe["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if kprobe_p["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0} or kprobe_p["k"] != 8:
        raise SystemExit("the KPROBE baseline is not at w_agree 0.0 / k 8 as registered")
    facet_source = dict(kprobe_p["facet_source"])
    if facet_source["relpath"] != CENTROID_FACETS_RELPATH or facet_source["kind"] != "sealed-vectors":
        raise SystemExit("the KPROBE baseline's facet_source is not the centroid key pin")
    if facet_source["tool_contact_ledger_row"] != CENTROID_ARTIFACT:
        raise SystemExit("the KPROBE baseline's facet_source names another ledger row")
    centroid_receipt = next(
        dict(r) for r in kprobe["preparation_source_receipts"] if r["relpath"] == CENTROID_RECEIPT_RELPATH
    )
    return agreement_source, agreement_receipt, facet_source, centroid_receipt


def derive_baseline(
    parent_path: str,
    out_path: str,
    pairs: list[tuple[str, str]],
    *,
    composed: bool,
    factors: tuple[dict, dict, dict, dict],
    what_this_is: str,
) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    # E16: the flip mints this cell's OWN supply under its own run id. Never
    # inherit the parent's, and never pass --allow-output-change.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}:
        raise SystemExit("the parent's boundary rank weights are not the flown identity")
    if perception["k"] != 8 or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary k/tau are not the flown 8 / 0.0")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the parent's boundary fuse coverage is not the flown 8/1/8")
    if perception["facet_source"]["sha256"] != WRITTEN_KEY_SHA:
        raise SystemExit("the parent's boundary facet_source is not the flown written-key pin")
    if "agreement_source" in perception:
        raise SystemExit("the parent declares an agreement_source; refusing")
    if document["policy"] != PLAN_POLICY:
        raise SystemExit("the parent's policy is not the locked phase program")
    solver = document["phase_material"]["solver"]
    if solver["instruction_template"] != PLAN_SOLVER_TEMPLATE or solver["response_format_id"] is not None:
        raise SystemExit("the parent's Solver material is not the locked plan's")
    if document["native_episode"]["deliver_normaliser"] != {"normaliser": PLAN_NORMALISER}:
        raise SystemExit("the parent's deliver_normaliser is not the locked v3 projection")
    # The RECALL width, on BOTH arms. ``PhaseSupplySpec.k`` is the provider's
    # top_k_per_dimension: the recall truncates by cosine BEFORE the ranker runs,
    # so the agreement term needs k 60 to reach a gold intent at rank 9-60. The
    # A/A carries k 60 too, so that it differs from the arm in the composed
    # factors alone; at pure cosine the top 8 of a 60-wide recall IS the 8-wide
    # recall's set in the same order, which the AGREE A/A proved by digest and
    # this cell's A/A must prove again (its prepared output digest must equal
    # the sealed comparator's).
    perception["k"] = 60
    if composed:
        agreement_source, agreement_receipt, facet_source, centroid_receipt = factors
        # Factor 1: the agreement term as AGREE carries it.
        perception["rank_weights"] = {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0}
        perception["agreement_source"] = dict(agreement_source)
        # Factor 2: the centroid key as KPROBE pins it.
        perception["facet_source"] = dict(facet_source)
        receipts = document.setdefault("preparation_source_receipts", [])
        for entry in (agreement_receipt, centroid_receipt):
            if any(r["relpath"] == entry["relpath"] for r in receipts):
                raise SystemExit(f"the parent already pins {entry['relpath']}")
            receipts.append(dict(entry))
        document["preparation_source_receipts"] = sorted(
            receipts, key=lambda entry: (entry["root"], entry["relpath"])
        )
        # Factor 3: the citation contract, four keys, one arming.
        document["policy"] = CITED_POLICY
        solver["instruction_template"] = CITED_SOLVER_TEMPLATE
        solver["response_format_id"] = CITED_RESPONSE_FORMAT
        document["native_episode"]["deliver_normaliser"] = {"normaliser": CITED_NORMALISER}
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
    # HELD, with the cell's own preparation requirements only. The decision
    # requirement is inserted by scripts/flights/repin_cell.py --set-ready once
    # root has minted the admission receipt.
    cell["readiness"] = {
        "reason": readiness_reason,
        "requirements": preparation_requirements,
        "state": "held",
    }
    document["failure_policy"] = document["failure_policy"].replace("closes cell PLAN", "closes this cell").replace(
        "stops cell PLAN", "stops cell COMP-1"
    )
    document["stage3_algorithm"] = algorithm
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    for name in ("arm", "smoke", "aa"):
        parser.add_argument(f"--{name}-supply-sha256", default="0" * 64)
    args = parser.parse_args(argv)
    for value in (args.arm_supply_sha256, args.smoke_supply_sha256, args.aa_supply_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("every supply digest must be a lowercase sha256")

    factors = registered_factors()
    agreement_source = factors[0]
    written: list[str] = []

    agreement_requirement = {
        "kind": "preparation",
        "reason": (
            "The pre-computed exemplar-intent AGREEMENT table this cell's boundary channel ranks "
            "with, exactly the artifact cell AGREE registered: built model-free by "
            "scripts/build_slurp_intent_exemplar_agreement.py from the pinned exemplar snapshot, "
            "the pinned pool key vectors and this roster's own pinned speech query vectors -- zero "
            "model, server, encoder, embedder, scorer, network and GPU contacts. Measured: 1,080 "
            "rows, every row 20 votes, 0 self-excluded rows, 0 rows with no vote, all 60 boundary "
            "facets reachable. The centroid key file is deliberately NOT a readiness requirement: "
            "it is pinned where the loader verifies it (facet_source.sha256) and its receipt in "
            "preparation_source_receipts, as cell KPROBE registered it."
        ),
        "relpath": agreement_source["relpath"],
        "sha256": agreement_source["sha256"],
    }
    supply_reason_composed = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this "
        "cell's own run id with core.flight.cli prepare-supply from the same sealed Fold A "
        "speech-query segment vectors, the CENTROID key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-"
        "KEYS-V1 and the sealed agreement table, with zero model, tokenizer, encoder, scorer or "
        "server contacts. E16: a prepared artifact is evidence only for the implementation that "
        "produced it, so this cell pins its own. --allow-output-change must never be passed."
    )
    supply_reason_aa = (
        "This cell's OWN prepared first-phase Perception supply, built model-free under this "
        "cell's own run id with core.flight.cli prepare-supply from the same sealed Fold A "
        "speech-query segment vectors and the same sealed SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1 "
        "facet vectors the sealed PLAN arm used, with zero model, tokenizer, encoder, scorer or "
        "server contacts. Its output digest must equal the sealed PLAN preparation's "
        + PLAN_SUPPLY_OUTPUT_SHA
        + " (the byte-identity proof that the A/A flies the locked plan's own bytes). E16: this "
        "cell pins its own rather than inheriting the PLAN arm's. --allow-output-change must never "
        "be passed."
    )

    # ---- the COMP-1 arm ----------------------------------------------------
    arm_pairs = substitutions("COMP1", "comp1", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE,
        "configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json",
        arm_pairs,
        composed=True,
        factors=factors,
        what_this_is=(
            "Cell COMP-1, the FIRST COMPOSED Stage-3 arm (owner decisions 138 and 152): the locked "
            "v2.0 plan with the agreement term, the centroid boundary key and the citation contract "
            "composed. " + THE_COMPOSITION
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-comp1-fold-a-v1.json",
        arm_pairs,
        args,
        purpose=(
            "Cell COMP-1 on TRAIN Fold A 1,080: does the COMPOSITION of the agreement term, the "
            "centroid boundary key and the citation contract raise intent-recognition accuracy "
            "(primary, owner decision 133) against the sealed PLAN arm, read at the in-chain A/A "
            "null flown beside it, with official pooled SLU-F1 the non-inferiority guard? Owner "
            "decision 138: every composed round's read against the lock IS the cumulative "
            "no-harm check, and a round that fails to improve is read as a CONFLICT DIAGNOSIS "
            "between its elements, never as a null -- which is why every verdict carries the "
            "per-class attribution table over the 191 PLAN intent-wrong rows (newly delivered "
            "by the agreement term, by the centroid key, by both, already delivered but wrong, "
            "and the catch-all) with each row's outcome under COMP-1. Owner decision 152: the "
            "citation part is admitted on no harm and its credit table is the reward signal every "
            "later construction round reads. " + THE_COMPOSITION + " The declared expected effect "
            "is COMPOSED BY THE COORDINATOR from the AGREE and KPROBE reads' measured m values "
            "(decision 139 forbids a prior); until it is declared the effect-floor gate refuses "
            "this cell, which is intended. Development numbers only (owner decisions 28 and 86); "
            "never a test claim. Nothing here authorises a flight, a readiness flip or an "
            "admission entry."
        ),
        readiness_reason=(
            "Cell COMP-1 registered before contact on "
            + args.date
            + " from the sealed cell PLAN fragments by script (decision 58) with the agreement "
            "term (as AGREE), the centroid key (as KPROBE) and the citation contract composed. "
            "Comparator: the sealed PLAN arm "
            + PLAN_RUN
            + ", never re-flown, read at the in-chain A/A replicate "
            "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 flown in the same campaign chain. HELD: the "
            "coordinator declares expected_effect_pp from the AGREE and KPROBE reads, root mints "
            "the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready, "
            "which also mints this cell's own first-phase supply under its own run id (item E16). "
            "--allow-output-change must never be passed. Nothing here authorises a flight, a "
            "readiness flip or an admission entry."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_reason_composed,
                "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1/phase-supply-v1.json",
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
    written.append("configs/experiment/slurp-native-stage3-comp1-fold-a-v1.json")

    # ---- the four-row form smoke ------------------------------------------
    smoke_pairs = substitutions("COMP1", "comp1", smoke=True)
    derive_baseline(
        PLAN_SMOKE_BASELINE,
        "configs/baseline/slurp-native-stage3-comp1-fold-a-smoke-4-baseline-v1.json",
        smoke_pairs,
        composed=True,
        factors=factors,
        what_this_is=(
            "Four-row structural form smoke of cell COMP-1: the same three composed actions on the "
            "first four rows of the unchanged TRAIN Fold A roster. " + THE_COMPOSITION
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-comp1-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        PLAN_SMOKE_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-comp1-fold-a-smoke-4-v1.json",
        smoke_pairs,
        args,
        purpose=(
            "Four-row structural form smoke of cell COMP-1: that the agreement table and the "
            "centroid key file load and hash-verify, that the boundary channel still delivers "
            "eight entries, that the Solver answers under the cited-answer contract and the "
            "unwrapping normaliser delivers the answer's own bytes, that every request fits and "
            "that the episode completes. It is scored by no one and read by no one: four rows can "
            "never be evidence of benefit. " + THE_COMPOSITION
        ),
        readiness_reason=(
            "Four-row form smoke of cell COMP-1, registered before contact on "
            + args.date
            + " from the sealed cell PLAN smoke fragments by script (decision 58). HELD until root "
            "mints the admission receipt and re-pins with --set-ready, which re-mints this cell's own "
            "first-phase supply (item E16); --allow-output-change must never be passed. Structural "
            "form proof only: no score, no read, no claim."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_reason_composed,
                "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1/phase-supply-v1.json",
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
    written.append("configs/experiment/slurp-native-stage3-comp1-fold-a-smoke-4-v1.json")

    # ---- the in-chain A/A replicate ---------------------------------------
    aa_pairs = substitutions("COMP1-AA", "comp1-aa", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE,
        "configs/baseline/slurp-native-stage3-comp1-aa-fold-a-baseline-v1.json",
        aa_pairs,
        composed=False,
        factors=factors,
        what_this_is=(
            "The IN-CHAIN A/A REPLICATE and control of cell COMP-1: the locked v2.0 plan's own "
            "bytes -- w_agree 0.0 with no agreement_source, the WRITTEN boundary key, the un-armed "
            "citation default (policy phase-native-candidates-review-revise-v1, Solver template "
            "slurp_native_role_solver_v2.txt, no response format, deliver normaliser "
            "saea-deliver-normalise-v3) -- carrying the SAME widened recall (k 60, delivered width "
            "8) as the arm so the two differ in the three composed factors alone, re-flown in the "
            "same campaign chain as cell COMP-1 so the composed delta is read against a "
            "within-chain null instead of a between-flight offset (measurement instrument rules 3 "
            "and 4). Its own prepared first-phase supply must reproduce the sealed PLAN "
            "preparation's output digest "
            + PLAN_SUPPLY_OUTPUT_SHA
            + " exactly, as the AGREE A/A did at the same k 60; that equality is the byte-identity "
            "proof that the A/A flies the lock's own bytes."
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-comp1-aa-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-comp1-aa-fold-a-v1.json",
        aa_pairs,
        args,
        purpose=(
            "The in-chain A/A replicate of cell COMP-1: the locked plan's own form, unchanged, "
            "re-flown in the same campaign chain, to supply the within-chain null the composed "
            "delta is read at. It makes no claim of its own and admits nothing; it is the "
            "instrument. Development numbers only (owner decisions 28 and 86)."
        ),
        readiness_reason=(
            "The in-chain A/A replicate of cell COMP-1, registered before contact on "
            + args.date
            + " from the sealed cell PLAN fragments by script (decision 58): the same baseline "
            "bytes at k 60, w_agree 0.0, no agreement_source, the written key, the un-armed "
            "citation default, its own run, attempt and fit ids. HELD until root mints the "
            "admission receipt and re-pins with --set-ready, which re-mints this cell's own "
            "first-phase supply (item E16); --allow-output-change must never be passed. Its prepared "
            "supply must reproduce the sealed PLAN output digest " + PLAN_SUPPLY_OUTPUT_SHA + "."
        ),
        preparation_requirements=[
            {
                "kind": "preparation",
                "reason": supply_reason_aa,
                "relpath": "prepared/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/phase-supply-v1.json",
                "sha256": args.aa_supply_sha256,
            }
        ],
        campaign=True,
        algorithm={"id": "none", "operators_used": [], "note": AA_ALGORITHM_NOTE},
    )
    written.append("configs/experiment/slurp-native-stage3-comp1-aa-fold-a-v1.json")

    # ---- the campaign plan: the A/A first, then the arm, in ONE chain ------
    plan = {
        "cells": [
            {"cell": "slurp-native-stage3-comp1-aa-fold-a-v1", "experiment": "slurp-native-stage3-comp1-aa-fold-a-v1"},
            {"cell": "slurp-native-stage3-comp1-fold-a-v1", "experiment": "slurp-native-stage3-comp1-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }
    wr("configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json", json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append("configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json")

    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
