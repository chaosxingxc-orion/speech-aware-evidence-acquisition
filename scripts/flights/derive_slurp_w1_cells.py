#!/usr/bin/env python3
"""Derive the two W1 cells -- slot-card selection (owner decision 164, knowledge wave item W1,
a row-127 no-harm FORM item) -- from the RETAINED AGREE arm fragments (owner decision 161;
decision 58: script-derived registrations).

THE ONE CHANGE. ``knowledge_stores.slot-contracts.candidate_supply.solver`` gains
``candidate_legality_source``: the pinned intent -> slot-type legality table
``prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json``, built model-free by
``scripts/build_slurp_intent_slot_legality.py`` from the released TRAIN exemplar store the
Solver already consumes (9,354 utterances, Fold A-free by construction and checked). The
route's authored index -- exactly the 402 (intent, slot type) pairs that store carries at
least once -- is NARROWED to the 286 pairs it carries in at least two distinct utterances,
so the Solver receives only the slot-contract cards for slot types legal under the row's
shortlisted intents. Nothing else moves: the roster, the geometry, the session, the program
and its 11-contact ceiling, the three stores and their pins, the agreement term, the
exemplar k of 20, the caps of the card route (3 candidates, 16 per candidate, 28 in all),
the role graph, every template, the deliver normaliser and the scorers are the AGREE arm's,
byte for byte. The legality table's receipt joins ``preparation_source_receipts``
(bookkeeping, the way AGREE and KPROBE pinned theirs).

TWO CELLS. The W1 arm on TRAIN Fold A 1,080 and its four-row structural form smoke. The
no-harm read is taken at the SHARED in-chain A/A of the AGREE arm's own bytes,
``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1``, which the coordinator registers separately for
wave items W1-W4; this script registers no A/A. The campaign plan carries the arm alone.

Every cell drops ``prepared_phase_supply`` so the coordinator's flip mints each cell's OWN
first-phase supply under its own run id (item E16); the card route is not an input to the
first-phase (Perception) supply, so the minted supplies must reproduce the AGREE
preparations' output digests (arm ``eab5c61e...``, smoke ``308601c5...``) -- the flip's
byte-identity check. The readiness requirements carry the agreement table exactly as the
AGREE cell pins it; the decision requirement is inserted by ``repin_cell.py --set-ready``.

Config only: no contact, no ledger row, no receipt, no flip.

    python scripts/flights/derive_slurp_w1_cells.py --date 2026-09-27 \\
        --legality-sha256 <sha> --legality-receipt-sha256 <sha>
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
SHARED_AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
AGREE_ARM_SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
AGREE_SMOKE_SUPPLY_OUTPUT_SHA = "308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9"

LEGALITY_RELPATH = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/legality.json"
LEGALITY_RECEIPT_RELPATH = "prepared/SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1/receipt.json"
LEGALITY_LEDGER_ROW = "SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1"
CAMPAIGN = "configs/campaign/slurp-native-stage3-w1-cardsel-fold-a-v1.json"
THE_ONE_KEY = "knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source"

ONE_FACTOR = (
    "The slot-contract card route (knowledge_stores.slot-contracts.candidate_supply.solver) gains "
    "candidate_legality_source, the pinned intent -> slot-type legality table "
    + LEGALITY_RELPATH
    + ": the route's authored index -- exactly the 402 (intent, slot type) pairs the released "
    "9,354-utterance TRAIN exemplar store carries at least once -- is narrowed to the 286 pairs that "
    "store carries in at least two distinct utterances (rule pool-utterance-support-at-least-2-v1), so "
    "the Solver receives only the slot-contract cards for slot types legal under the row's shortlisted "
    "intents. The table can only remove an authored binding, never add one (enforced at load). "
    "Measured offline on the sealed AGREE arm: 12.90 -> 9.87 cards per row, 1,186 fewer prompt tokens "
    "per Solver contact on average (3,630 per row over the Solver, Reviewer and Planner contacts that "
    "render the block); 5 of 1,080 rows lose a card for a gold slot type (5 gold items, 1 of which the "
    "AGREE arm delivered exactly right). Nothing else moves: roster, geometry, session, program and its "
    "11-contact ceiling, the three stores and their pins, the agreement term, the exemplar k of 20, the "
    "card route's caps, the role graph, every template, the deliver normaliser and the scorers are the "
    "retained AGREE arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a one-key knowledge "
    "SELECTION change (which slot cards reach the Solver), chosen by a model-free content audit over "
    "sealed bytes and flown as a row-127 no-harm FORM item, with no rollout, no per-sample scoring, no "
    "credit assignment, no update operator and no evolving store. It is deliberately NOT labelled "
    "sealed-credit-system-policy-v1: that id's first instance is reserved for the composed system "
    "policy, and a card filter is not a policy search."
)


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + (
        "\n" if raw.endswith("\n") else ""
    )


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the AGREE fragment to this cell's own."""

    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-w1-cardsel-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-w1-cardsel-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-baseline-v1"),
            ("saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "saea-slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-w1-cardsel-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-w1-cardsel-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", "slurp-native-stage3-w1-cardsel-fold-a-baseline-v1"),
        ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-w1-cardsel-fold-a-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-w1-cardsel-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent_path: str, out_path: str, pairs, args, *, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(raw)
    # E16: the flip mints this cell's OWN supply under its own run id; drop the
    # parent's pin BEFORE the id rewrite so its relpath never turns into ours.
    document.pop("prepared_phase_supply", None)
    document = json.loads(substitute(json.dumps(document, ensure_ascii=False), pairs))
    document["what_this_is"] = what_this_is
    route = document["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    if "candidate_legality_source" in route:
        raise SystemExit("the parent already narrows its card route; refusing")
    if (route["max_candidates"], route["max_values_per_candidate"], route["max_total_values"]) != (3, 16, 28):
        raise SystemExit("the parent's card-route caps are not the AGREE arm's 3 / 16 / 28")
    # THE ONE CHANGE.
    route["candidate_legality_source"] = {
        "kind": "sealed-intent-slot-legality",
        "relpath": LEGALITY_RELPATH,
        "sha256": args.legality_sha256,
        "tool_contact_ledger_row": LEGALITY_LEDGER_ROW,
        "embedded_signal": (
            "derived: the (intent, slot type) pairs the released TRAIN exemplar store the Solver "
            "already consumes (size-pool-annotated-exemplars, 9,354 utterances, content hash "
            "4c498dc0...) carries in at least two distinct utterances, read from the store's own "
            "annotation text (type names only). A released-store property, never a label of an "
            "evaluated row: the store holds no Fold A utterance (checked at build), and no governed "
            "label, transcript, devel or test file is read. Built model-free by "
            "scripts/build_slurp_intent_slot_legality.py with zero model, server, tokenizer, "
            "encoder, embedder, scorer, network and GPU contacts; receipt beside the artifact."
        ),
    }
    receipts = document.setdefault("preparation_source_receipts", [])
    receipts.append({"root": "data", "relpath": LEGALITY_RECEIPT_RELPATH, "sha256": args.legality_receipt_sha256})
    document["preparation_source_receipts"] = sorted(receipts, key=lambda entry: (entry["root"], entry["relpath"]))
    wr(out_path, dump_like(raw, document))


def derive_experiment(parent_path: str, out_path: str, pairs, args, *, purpose: str,
                      readiness_reason: str, campaign: bool) -> None:
    raw = rd(parent_path)
    parent = json.loads(raw)
    agreement = [
        requirement for requirement in parent["cells"][0]["readiness"]["requirements"]
        if requirement.get("kind") == "preparation"
        and requirement.get("relpath") == "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
    ]
    if len(agreement) != 1:
        raise SystemExit("the parent does not pin exactly one agreement-table preparation requirement")
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    document["failure_policy"] = (
        document["failure_policy"]
        .replace("closes cell PLAN", "closes this cell")
        .replace("stops cell PLAN", "stops this cell")
    )
    if "generation_budget" in document:
        document["generation_budget"]["definition"] = (
            "The retained AGREE arm's role graph is unchanged: perception 1, solver 1, reviewer 3, planner 1, "
            "max_revisions 1, so rails.native_episode_config.load_native_episode_config resolves the program "
            "ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and 1,080 * 11 = 11,880 is the exact program "
            "maximum rather than a conservative safety bound. The sealed AGREE arm realized 4,385 contacts "
            "(4.060 per row), so the expected spend is about 4,400 contacts; W1 removes about 1,186 prompt "
            "tokens per Solver contact and adds none, and no cap is denominated in tokens. The budget is "
            "RUN-CUMULATIVE across every attempt of this run id, which is what makes the resume-recovery "
            "clause safe."
        )
        document["generation_budget"]["target"] = 4385
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    # HELD, with the agreement table exactly as the AGREE cell pins it. The decision
    # requirement is inserted by scripts/flights/repin_cell.py --set-ready once root has
    # minted the admission receipt; the first-phase supply is minted at the flip (E16).
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement, "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--legality-sha256", required=True)
    parser.add_argument("--legality-receipt-sha256", required=True)
    args = parser.parse_args(argv)
    for value in (args.legality_sha256, args.legality_receipt_sha256):
        if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise SystemExit("every digest must be a lowercase sha256")

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
        "--set-ready, which also mints this cell's own first-phase supply under its own run id (item "
        "E16) and inserts the decision requirement; --allow-output-change must never be passed, and the "
        "minted supply must reproduce the AGREE preparation's output digest (the card route is not an "
        "input to the first-phase supply). Nothing here authorises a flight, a readiness flip or an "
        "admission entry."
    )
    written = []

    arm_pairs = substitutions(smoke=False)
    derive_baseline(
        AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-w1-cardsel-fold-a-baseline-v1.json", arm_pairs, args,
        what_this_is=(
            "Cell W1 (knowledge wave item W1, slot-card selection): the retained AGREE arm with ONE key "
            "added -- the slot-contract card route's candidate_legality_source. " + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-w1-cardsel-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-w1-cardsel-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell W1 on TRAIN Fold A 1,080: with the Solver's slot-contract cards narrowed to the slot types "
            "legal under the row's shortlisted intents, do the official intent accuracy (primary, owner "
            "decision 133) and the official pooled SLU-F1 (guard) stay within the plan's own null, read "
            "against the shared in-chain A/A of the AGREE arm's own bytes (" + SHARED_AA_RUN + ") flown in "
            "the same chain? A row-127 FORM item: admitted on NO HARM (each metric's CI95 lower bound "
            "against the in-chain A/A not below the negative of its own Fold A half-width, intent 0.9943 / "
            "SLU 1.2485), never reported as a gain; the ceiling it unlocks is the prompt room it frees -- "
            "about 1,186 tokens per Solver contact on average and 7,816 bytes of the pre-flight Solver "
            "envelope -- that later content items (K1, K2, K4) must be paid from. " + ONE_FACTOR
            + " Development numbers only (owner decisions 28 and 86); never a test claim. Nothing here "
            "authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell W1 registered before contact on " + args.date + " from the retained AGREE arm fragments "
            "by script (decisions 58, 161 and 164) with one key added. Comparator: the sealed AGREE arm "
            + AGREE_RUN + ", never re-flown, read at the shared in-chain A/A " + SHARED_AA_RUN
            + " (the AGREE arm's own bytes) flown in the same campaign chain." + held
        ),
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-w1-cardsel-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(
        AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-w1-cardsel-fold-a-smoke-4-baseline-v1.json", smoke_pairs, args,
        what_this_is=(
            "Four-row structural form smoke of cell W1: the same one key on the first four rows of the "
            "unchanged TRAIN Fold A roster. " + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-w1-cardsel-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell W1: that the legality table loads and verifies, that "
            "the card route narrows without error, that every request fits and that the episode completes. "
            "It is scored by no one and read by no one: four rows can never be evidence of benefit or of "
            "harm. " + ONE_FACTOR
        ),
        readiness_reason=(
            "Four-row form smoke of cell W1, registered before contact on " + args.date + " from the "
            "retained AGREE smoke fragments by script (decision 58). Structural form proof only: no score, "
            "no read, no claim." + held
        ),
        campaign=False,
    )
    written.append("configs/experiment/slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1.json")

    wr(CAMPAIGN, json.dumps({
        "cells": [
            {"cell": "slurp-native-stage3-w1-cardsel-fold-a-v1", "experiment": "slurp-native-stage3-w1-cardsel-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN)
    print(json.dumps({"written": written, "the_one_key": THE_ONE_KEY, "legality_sha256": args.legality_sha256}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
