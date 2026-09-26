#!/usr/bin/env python3
"""Derive the three AGREE cells from the sealed cell PLAN fragments (decision 58:
script-derived registrations).

THE ONE FACTOR. ``knowledge_stores['intent-boundaries'].phase_supply.perception``
gains ``rank_weights.w_agree = 1.0`` and an ``agreement_source`` pin naming the
pre-computed, self-excluded exemplar-intent vote. ``k`` stays 8, ``tau`` stays
0.0, ``w_cos`` stays 1.0, ``w_prior`` stays 0.0 (it is DEAD on this channel, not
merely zeroed -- 0 of 60 boundary values carry a ``prior_score``, none a
``task_target``, and ``intent-boundary`` is not in
``kb_policy.PRIOR_MASS_DIMENSIONS``, so ``max_prior`` is 0.0 at every weight;
turning it on would be a store rebuild and is NOT attempted here). Nothing else
moves: the roster, the geometry, the session, the program, the three stores, the
exemplar ``k`` of 20, the role graph, the contact ceiling and the scorers are the
locked plan's.

THREE CELLS, because a cross-flight contrast against a sealed comparator needs
an in-chain replicate (``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md``
rules 3 and 4, and the measured +1.87 pp A/A offset):

  * the AGREE arm on TRAIN Fold A 1,080;
  * its four-row structural form smoke;
  * an A/A replicate -- the locked PLAN form, ``w_agree`` 0.0, no
    ``agreement_source``, flown in the SAME campaign chain, so the treatment
    delta is read against a within-chain null rather than against a
    between-flight offset. The campaign plan therefore carries the arm AND the
    A/A; the smoke is deliberately outside it, exactly as every other cell's
    smoke is.

Every cell drops ``prepared_phase_supply`` so the coordinator's flip mints each
cell's OWN first-phase supply under its own run id (item E16); each cell pins its
own ``native_contact_fit`` ids. ``--allow-output-change`` must never be passed.

This script writes CONFIG ONLY: three baselines, three experiment fragments and
one campaign plan. It performs no contact, writes no ledger row, mints no
decision receipt and flips nothing.

Windows or WSL Python; run from the study root.

    python scripts/flights/derive_slurp_agree_cells.py \
        --agreement-relpath prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl \
        --agreement-sha256 <64 hex> \
        --agreement-receipt-relpath prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json \
        --agreement-receipt-sha256 <64 hex> --date 2026-09-26
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

PLAN_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PLAN_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
#: The sealed PLAN preparation's OUTPUT digest, recorded in that cell's own
#: readiness note. The A/A cell's own prepared supply must reproduce it exactly,
#: which is the byte-identity proof that ``w_agree`` 0.0 still flies today's
#: bytes (``scripts/slurp_agreement_default_identity_proof.py``).
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"

AGREEMENT_LEDGER_ROW = "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1"

ONE_FACTOR = (
    "The intent-boundary Perception channel's rank policy reads its own w_agree "
    "term over a pre-computed, self-excluded exemplar-intent vote: w_agree 1.0, "
    "the DELIVERED width unchanged at 8 entries (fuse_coverage m 8 / c 1 / "
    "top_l 8). The RECALL width moves from 8 to the store's full 60, because "
    "PhaseSupplySpec.k is the provider's top_k_per_dimension and truncates by "
    "cosine BEFORE the ranker runs -- left at 8 the agreement term can only "
    "permute the eight the cosine already chose and the change is inert "
    "(measured: 45.0 % -> 45.0 % wrong-row delivery on all three rosters). "
    "Widening the recall alone is a proven no-op: the in-chain A/A control "
    "carries k 60 at w_agree 0.0 and reproduces the sealed comparator's own "
    "first-phase output digest exactly, so the two arms differ in w_agree alone. "
    "Authority: the model-free read "
    "docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md, whose "
    "section 6 selection rule picked this candidate out of 27 by a rule fixed "
    "before the numbers were read (a gain on all three rosters, correct-row "
    "delivery loss at most one point, token-neutral, smallest weight). Measured "
    "delivery of the row's own gold-intent boundary entry on intent-wrong rows: "
    "TRAIN Fold A 45.0 % to 81.7 %, with a floor of +30.4 points on the two "
    "rosters the weight was not fitted on, and correct-row delivery rising to "
    "98.2-99.6 %. Measured token cost +1.4 tokens per row against the flown "
    "1,195.4-token block; the k=30 alternative buys the same delivery for "
    "+3,262.3, about 2,330 times the form cost that sank the index arm at SLU "
    "-7.37. DELIVERY IS NOT CORRECTNESS: the conversion rate is unmeasured."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly. It "
    "is a one-factor retrieval change on the locked plan: one rank weight and "
    "one pre-computed model-free input, chosen by an offline diagnostic over "
    "sealed bytes, with no rollout, no per-sample scoring, no credit "
    "assignment, no update operator and no evolving store. The family whose "
    "description covers a typed construction/consumption action of this shape "
    "is sealed-credit-system-policy-v1, and this cell is deliberately NOT "
    "labelled with it: that id's first instance is reserved for the composed "
    "system policy, and a single weight is not a policy search."
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
            (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-FIT-V1",
                f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-FIT-V1",
            ),
            (
                "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-SMOKE-4-V1",
                f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-SMOKE-4-V1",
            ),
            (
                "attempt-slurp-native-default-plan-lock-smoke-4-generation-v1",
                f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-generation-v1",
            ),
            (
                "attempt-slurp-native-default-plan-lock-smoke-4-fit-v1",
                f"attempt-slurp-native-stage3-{slug}-fold-a-smoke-4-fit-v1",
            ),
            (
                "slurp-native-default-plan-lock-smoke-4-baseline-v1",
                f"slurp-native-stage3-{slug}-fold-a-smoke-4-baseline-v1",
            ),
            (
                "slurp-native-default-plan-lock-smoke-4-v1",
                f"slurp-native-stage3-{slug}-fold-a-smoke-4-v1",
            ),
        ]
    return [
        (
            "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1",
            f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-FIT-V1",
        ),
        ("SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1", f"SAEA-SLURP-STAGE3-{tag}-FOLD-A-V1"),
        (
            "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1",
            f"attempt-slurp-native-stage3-{slug}-fold-a-generation-v1",
        ),
        (
            "attempt-slurp-native-default-plan-lock-train-fold-a-fit-v1",
            f"attempt-slurp-native-stage3-{slug}-fold-a-fit-v1",
        ),
        (
            "slurp-native-default-plan-lock-baseline-v1",
            f"slurp-native-stage3-{slug}-fold-a-baseline-v1",
        ),
        ("slurp-native-default-plan-lock-v1", f"slurp-native-stage3-{slug}-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(
    parent_path: str,
    out_path: str,
    pairs: list[tuple[str, str]],
    args: argparse.Namespace,
    *,
    agreement: bool,
    what_this_is: str,
) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    # E16: the flip mints this cell's OWN supply under its own run id. Never
    # inherit the parent's, and never pass --allow-output-change.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}:
        raise SystemExit("the parent's boundary rank weights are not the flown identity")
    if perception["k"] != 8 or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary k/tau are not the flown 8 / 0.0")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the parent's boundary fuse coverage is not the flown 8/1/8")
    # THE RECALL WIDTH, AND WHY IT MOVES WHILE THE DELIVERED WIDTH DOES NOT.
    #
    # ``PhaseSupplySpec.k`` is the provider's ``top_k_per_dimension``: the recall
    # truncates to the top ``k`` BY COSINE before the ranker is ever called, so at
    # k = 8 the agreement term can only permute the eight entries the cosine
    # already chose -- it cannot reach the gold intent at rank 9-60, which is
    # exactly the population the 2026-09-26 read measured. Left at 8 the
    # treatment is INERT: measured wrong-row delivery 45.0 % -> 45.0 % on all
    # three rosters (the production replication receipt).
    #
    # The delivered width is NOT k. ``KbFacetProvider.fuse`` reads the full
    # ``RankResult`` and its own ``FuseKnobs``, so the block still carries
    # ``fuse_coverage`` = m 8 / c 1 / top_l 8 entries. Widening the recall to the
    # store's full 60 therefore reproduces the read's own arithmetic -- which
    # recalled at 60 and delivered 8 -- at zero token cost.
    #
    # AND IT IS A NO-OP ON ITS OWN, proven rather than asserted. At pure cosine
    # the top-8 of a 60-wide recall IS the 8-wide recall's set, in the same
    # order, so the A/A cell below carries k = 60 TOO and its own prepared
    # first-phase supply must reproduce the sealed comparator's output digest
    # exactly. That makes the A/A a genuine ONE-FACTOR control -- it differs from
    # the treatment in w_agree alone -- and makes the no-op a measured fact.
    perception["k"] = 60
    if agreement:
        perception["rank_weights"] = {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0}
        perception["agreement_source"] = {
            "kind": "sealed-agreement",
            "relpath": args.agreement_relpath,
            "sha256": args.agreement_sha256,
            "tool_contact_ledger_row": AGREEMENT_LEDGER_ROW,
            "embedded_signal": (
                "derived: the share of this row's own top-20 sealed TRAIN-exemplar "
                "recall whose frozen build-time task_target equals each boundary "
                "intent, self-excluded by the row's utterance identity and "
                "normalised to 1. Speech-keyed by construction -- the recall it "
                "summarises is the row's own sealed speech vector against the "
                "frozen pool -- and gold-free: the key is a released store "
                "property, never a label, transcript or future turn. Built "
                "model-free by scripts/build_slurp_intent_exemplar_agreement.py "
                "with zero model, server, encoder, embedder, scorer, network and "
                "GPU contacts; receipt beside the artifact."
            ),
        }
        document.setdefault("preparation_source_receipts", []).append(
            {
                "root": "data",
                "relpath": args.agreement_receipt_relpath,
                "sha256": args.agreement_receipt_sha256,
            }
        )
        document["preparation_source_receipts"] = sorted(
            document["preparation_source_receipts"],
            key=lambda entry: (entry["root"], entry["relpath"]),
        )
    else:
        if "agreement_source" in perception:
            raise SystemExit("the A/A cell must declare no agreement_source")
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
) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    cell = document["cells"][0]
    stages = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["allowed_execution_stages"] = stages
    # HELD, with the cell's own preparation requirements only. The decision
    # requirement is inserted by scripts/flights/repin_cell.py --set-ready once
    # root has minted the admission receipt; writing one here would claim a
    # receipt that does not exist.
    cell["readiness"] = {
        "reason": readiness_reason,
        "requirements": preparation_requirements,
        "state": "held",
    }
    document["stage3_algorithm"] = {
        "id": "none",
        "operators_used": [],
        "note": STAGE3_ALGORITHM_NOTE,
    }
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agreement-relpath", required=True)
    parser.add_argument("--agreement-sha256", required=True)
    parser.add_argument("--agreement-receipt-relpath", required=True)
    parser.add_argument("--agreement-receipt-sha256", required=True)
    parser.add_argument("--date", required=True)
    # TWO PASSES, and they converge in exactly two.
    #
    # A cell's readiness requirement names its own prepared first-phase supply by
    # sha256, and that artifact cannot exist until the config it is prepared from
    # is final -- so pass 1 leaves these at the placeholder, pass 2 fills the
    # measured digests. The second pass cannot move the artifacts it just pinned,
    # because ``core.preparation.artifact_inputs`` strips every cell's
    # ``readiness`` block out of ``config_sha256`` for exactly this reason. The
    # coordinator's ``repin_cell.py --set-ready`` rewrites them a third time and
    # must find them unchanged.
    for name in ("arm", "smoke", "aa"):
        parser.add_argument(f"--{name}-supply-sha256", default="0" * 64)
    args = parser.parse_args(argv)
    for value in (args.agreement_sha256, args.agreement_receipt_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("every agreement digest must be a lowercase sha256")

    written: list[str] = []
    agreement_requirement = {
        "kind": "preparation",
        "reason": (
            "The pre-computed exemplar-intent AGREEMENT table this cell's boundary "
            "channel ranks with, built model-free by "
            "scripts/build_slurp_intent_exemplar_agreement.py from the pinned "
            "exemplar snapshot, the pinned pool key vectors and this roster's own "
            "pinned speech query vectors, through the same "
            "rails.phase_supply.build_bootstrap_selection recall/rank/fuse the "
            "flight runs at the Solver -- zero model, server, encoder, embedder, "
            "scorer, network and GPU contacts. Measured: 1,080 rows, every row 20 "
            "votes, 0 rows with a self-excluded exemplar (the pool excludes every "
            "Fold A recording by construction, and the exclusion is implemented and "
            "tested anyway), 0 rows with no vote, 0 pool values without a "
            "build-time target, all 60 boundary facets reachable."
        ),
        "relpath": args.agreement_relpath,
        "sha256": args.agreement_sha256,
    }
    supply_requirement_reason = (
        "This cell's OWN prepared first-phase Perception supply, built model-free "
        "under this cell's own run id with core.flight.cli prepare-supply from the "
        "same sealed Fold A speech-query segment vectors and the same sealed "
        "SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1 facet vectors the sealed PLAN "
        "arm used, with zero model, tokenizer, encoder, scorer or server contacts. "
        "E16: a prepared artifact is evidence only for the implementation that "
        "produced it, so this cell pins its own rather than inheriting the PLAN "
        "arm's. --allow-output-change must never be passed."
    )

    # ---- the AGREE arm ---------------------------------------------------
    arm_pairs = substitutions("AGREE-W1", "agree-w1", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE,
        "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json",
        arm_pairs,
        args,
        agreement=True,
        what_this_is=(
            "Cell AGREE: the locked v2.0 plan with ONE factor changed -- the "
            "intent-boundary Perception channel's own w_agree term set to 1.0 over "
            "the pre-computed, self-excluded exemplar-intent vote, k left at 8. "
            + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json",
        arm_pairs,
        args,
        purpose=(
            "Cell AGREE on TRAIN Fold A 1,080: does the intent-boundary channel's "
            "own agreement term, read over the pre-computed self-excluded "
            "exemplar-intent vote at w_agree 1.0, raise the official SLURP pooled "
            "SLU-F1 and intent accuracy against the sealed PLAN arm, read at the "
            "in-chain A/A null flown beside it? " + ONE_FACTOR + " Development "
            "numbers only (owner decisions 28 and 86); never a test claim. Nothing "
            "here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell AGREE registered before contact on "
            + args.date
            + " from the sealed cell PLAN fragments by script (decision 58). "
            "Comparator: the sealed PLAN arm "
            + PLAN_RUN
            + ", never re-flown, read at the in-chain A/A replicate "
            "SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1 flown in the same campaign chain. "
            "HELD: root mints the admission receipt and re-pins with "
            "scripts/flights/repin_cell.py --set-ready, which also mints this "
            "cell's own first-phase supply under its own run id (item E16). "
            "Nothing here authorises a flight, a readiness flip or an admission "
            "entry."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_requirement_reason,
                "relpath": "prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1/phase-supply-v1.json",
                "sha256": args.arm_supply_sha256,
            },
        ],
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json")

    # ---- the four-row form smoke ----------------------------------------
    smoke_pairs = substitutions("AGREE-W1", "agree-w1", smoke=True)
    derive_baseline(
        PLAN_SMOKE_BASELINE,
        "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json",
        smoke_pairs,
        args,
        agreement=True,
        what_this_is=(
            "Four-row structural form smoke of cell AGREE: the same one factor on "
            "the first four rows of the unchanged TRAIN Fold A roster. " + ONE_FACTOR
        ),
    )
    written.append(
        "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
    )
    derive_experiment(
        PLAN_SMOKE_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json",
        smoke_pairs,
        args,
        purpose=(
            "Four-row structural form smoke of cell AGREE: that the agreement "
            "signal loads, that the boundary channel still delivers eight entries, "
            "that every request fits and that the episode completes. It is scored "
            "by no one and read by no one: four rows can never be evidence of "
            "benefit. " + ONE_FACTOR
        ),
        readiness_reason=(
            "Four-row form smoke of cell AGREE, registered before contact on "
            + args.date
            + " from the sealed cell PLAN smoke fragments by script (decision 58). "
            "HELD until root mints the admission receipt and re-pins with "
            "--set-ready. Structural form proof only: no score, no read, no claim."
        ),
        preparation_requirements=[
            agreement_requirement,
            {
                "kind": "preparation",
                "reason": supply_requirement_reason,
                "relpath": "prepared/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1/phase-supply-v1.json",
                "sha256": args.smoke_supply_sha256,
            },
        ],
        campaign=False,
    )
    written.append("configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json")

    # ---- the in-chain A/A replicate -------------------------------------
    aa_pairs = substitutions("AGREE-AA", "agree-aa", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE,
        "configs/baseline/slurp-native-stage3-agree-aa-fold-a-baseline-v1.json",
        aa_pairs,
        args,
        agreement=False,
        what_this_is=(
            "The IN-CHAIN A/A REPLICATE and ONE-FACTOR CONTROL of cell AGREE: the "
            "locked v2.0 plan at w_agree 0.0 with no agreement_source, carrying the "
            "SAME widened recall (k 60, delivered width 8) as the treatment so the "
            "two arms differ in w_agree alone -- re-flown in the same campaign chain "
            "as cell AGREE so the treatment delta is read against a within-chain "
            "null instead of a between-flight offset. Authority: "
            "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md "
            "rules 3 and 4 (a pure A/A pair at n = 625 read +1.87 pp with a CI95 "
            "that excludes zero, so a cross-flight contrast with no in-chain "
            "replicate is refused outright). Its own prepared first-phase supply "
            "must reproduce the sealed PLAN preparation's output digest "
            + PLAN_SUPPLY_OUTPUT_SHA
            + " exactly; that equality is the byte-identity proof that the "
            "agreement-term implementation leaves the default's rendered bytes "
            "unchanged."
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-agree-aa-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT,
        "configs/experiment/slurp-native-stage3-agree-aa-fold-a-v1.json",
        aa_pairs,
        args,
        purpose=(
            "The in-chain A/A replicate of cell AGREE: the locked plan's own form, "
            "unchanged, re-flown in the same campaign chain, to supply the "
            "within-chain null the treatment delta is read at. It makes no claim of "
            "its own and admits nothing; it is the instrument. Development numbers "
            "only (owner decisions 28 and 86)."
        ),
        readiness_reason=(
            "The in-chain A/A replicate of cell AGREE, registered before contact on "
            + args.date
            + " from the sealed cell PLAN fragments by script (decision 58): the "
            "same baseline bytes, w_agree 0.0, no agreement_source, its own run, "
            "attempt and fit ids. HELD until root mints the admission receipt and "
            "re-pins with --set-ready. Its prepared supply must reproduce the "
            "sealed PLAN output digest " + PLAN_SUPPLY_OUTPUT_SHA + "."
        ),
        preparation_requirements=[
            {
                "kind": "preparation",
                "reason": supply_requirement_reason,
                "relpath": "prepared/SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1/phase-supply-v1.json",
                "sha256": args.aa_supply_sha256,
            }
        ],
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-agree-aa-fold-a-v1.json")

    # ---- the campaign plan: the arm AND its in-chain replicate ----------
    plan = {
        "cells": [
            {
                "cell": "slurp-native-stage3-agree-aa-fold-a-v1",
                "experiment": "slurp-native-stage3-agree-aa-fold-a-v1",
            },
            {
                "cell": "slurp-native-stage3-agree-w1-fold-a-v1",
                "experiment": "slurp-native-stage3-agree-w1-fold-a-v1",
            },
        ],
        "schema": "saea-campaign-plan-v1",
    }
    wr(
        "configs/campaign/slurp-native-stage3-agree-w1-fold-a-v1.json",
        json.dumps(plan, indent=2, sort_keys=True) + "\n",
    )
    written.append("configs/campaign/slurp-native-stage3-agree-w1-fold-a-v1.json")

    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
