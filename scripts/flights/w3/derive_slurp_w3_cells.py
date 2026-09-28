#!/usr/bin/env python3
"""Derive the W3 cells -- W3a ALONE, the intent contrast cards (owner decision 164, knowledge-wave
item W3; coordinator ruling 2026-09-27 under decision 164's one-change rule) -- from the RETAINED
AGREE arm fragments (decision 58: script-derived registrations).

ONE PIN, CONTENT the deciding nodes read (the 2026-09-27 mechanism synthesis: every gain so far
was row-matched content to the deciding node, every harm a form change without content):

  W3a  ``knowledge_stores.intent-boundaries.{snapshot,release}`` move from
       ``intent-boundaries-v1`` to ``intent-boundaries-contrast-v1``
       (``scripts/build_slurp_intent_contrast_cards.py``): each card keeps its header,
       activation boundary, authored exclusion and card-specific limitations verbatim,
       loses the shared boilerplate, and carries contrast lines against its nearest
       TRAIN-centroid rivals, never costing more tokens than the flown card. Facets,
       keys and value ids are unchanged, so the Perception delivery is AGREE's own.

The first registration also carried W3b, a per-intent cap on the Solver's exemplar block
(``saea-fuse-supplyfilter-target-cap-v1``). The re-registration drops it: the Solver's
``knowledge_stores.train-exemplars.phase_supply.solver`` stays the AGREE arm's flown supply
filter (``k`` 20, ``m``/``c``/``top_l`` 20), exactly the ``attribution_split.how_to_derive``
recipe of the package's ``registered-facts-v1.json``. The reasons are in the package README's
re-registration note.

Everything else is the retained AGREE arm's, byte for byte: the roster, geometry, session,
program and its 11-contact ceiling, the agreement term, the Solver exemplar supply, the
slot-contracts store, the role graph, every template, the deliver normaliser and the scorers.
The frozen source receipts gain the contrast release's two receipts.

Two cells: the W3 arm on TRAIN Fold A 1,080 and its four-row form smoke. The in-chain A/A is
the SHARED wave-1 A/A ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`` the coordinator registers;
this script registers none. Every cell drops ``prepared_phase_supply`` so the flip mints its
own (item E16); the requirements lists are EMPTY and ``--allow-output-change`` must never be
passed. The first-phase (Perception) supply reads keys and value ids only, so each minted
supply must reproduce the AGREE arm's own output digest
``eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae``.

Config only: no contact, no ledger row, no receipt, no flip.

    python scripts/flights/w3/derive_slurp_w3_cells.py --date 2026-09-27 \\
        --cards docs/receipts/knowledge/slurp-intent-contrast-cards-v1.json
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
AGREE_SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
SHARED_AA = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
CAMPAIGN = "configs/campaign/slurp-native-stage3-w3-fold-a-v1.json"

OLD_IB = {"release": "knowledge/slurp/semantic/intent-boundaries-v1/release.json",
          "snapshot": "knowledge/slurp/semantic/intent-boundaries-v1/snapshot.json"}
FLOWN_SOLVER = {"fuse_policy": "saea-fuse-supplyfilter-v1", "k": 20,
                "fuse_coverage": {"c": 20, "m": 20, "top_l": 20}}

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a knowledge "
    "CONTENT change -- a rebuilt intent-boundary store whose cards carry TRAIN-derived contrast "
    "lines in place of boilerplate -- chosen by model-free audits over sealed bytes, with no rollout, "
    "no per-sample scoring, no credit assignment, no update operator and no evolving store."
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
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-w3-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-w3-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-w3-fold-a-smoke-4-baseline-v1"),
            ("saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "saea-slurp-native-stage3-w3-fold-a-smoke-4-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "slurp-native-stage3-w3-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-W3-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-w3-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-w3-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", "slurp-native-stage3-w3-fold-a-baseline-v1"),
        ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-w3-fold-a-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-w3-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent_path: str, out_path: str, pairs, *, cards: dict, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own supply
    document["what_this_is"] = what_this_is
    stores = document["knowledge_stores"]
    ib = stores["intent-boundaries"]
    if ib["release"]["relpath"] != OLD_IB["release"] or ib["snapshot"]["relpath"] != OLD_IB["snapshot"]:
        raise SystemExit("the parent's intent-boundaries store is not intent-boundaries-v1")
    solver = stores["train-exemplars"]["phase_supply"]["solver"]
    if {k: solver[k] for k in FLOWN_SOLVER} != FLOWN_SOLVER:
        raise SystemExit("the parent's Solver exemplar supply is not the flown k 20 supply filter")
    if solver["rank_weights"] != {"w_agree": 0.0, "w_cos": 1.0, "w_prior": 0.0} or solver["tau"] != 0.0:
        raise SystemExit("the parent's Solver exemplar ranker is not pure cosine at tau 0")
    # ---- W3a: the contrast-card release -------------------------------------
    release = cards["release"]
    ib["release"] = {"relpath": release["release"]["relpath"], "sha256": release["release"]["sha256"]}
    ib["snapshot"] = {"relpath": release["snapshot"]["relpath"], "sha256": release["snapshot"]["content_sha256"]}
    receipts = document["preparation_source_receipts"]
    for entry in (release["completion"], release["release"]):
        pin = {"relpath": entry["relpath"], "root": "data", "sha256": entry["sha256"]}
        if pin not in receipts:
            receipts.append(pin)
    # ---- the Solver exemplar supply stays the AGREE arm's (W3b dropped, 2026-09-27) ----
    wr(out_path, dump_like(raw, document))


def derive_experiment(parent_path: str, out_path: str, pairs, args, *, purpose: str,
                      readiness_reason: str, campaign: bool, arm_rows: bool) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    document["failure_policy"] = (
        document["failure_policy"].replace("closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    )
    if arm_rows:
        document["generation_budget"] = {
            "cap": 11880,
            "definition": (
                "The retained AGREE arm's role graph is unchanged: perception 1, solver 1, reviewer 3, "
                "planner 1, max_revisions 1, so rails.native_episode_config.load_native_episode_config "
                "resolves the program ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and "
                "1,080 * 11 = 11,880 is the exact program maximum rather than a conservative safety "
                "bound. The sealed AGREE arm's own realized cost was 4,385 contacts (4.060 per row) and "
                "about 1.9 GPU hours per 1,080 rows at the np4 rate, so the expected spend is about that; "
                "the contrast cards cost no more tokens than the cards they replace and the Solver "
                "exemplar block is the AGREE arm's own, so no cap is denominated in anything this cell moves. The "
                "budget is RUN-CUMULATIVE across every attempt of this run id, which is what makes the "
                "resume-recovery clause safe."
            ),
            "target": 4385,
        }
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": [], "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--cards", required=True, help="repo-relative contrast-card receipt")
    args = parser.parse_args(argv)

    cards = json.loads(rd(args.cards))
    if cards.get("schema") != "saea-slurp-intent-contrast-cards-receipt-v1" or not cards["release"]["reloaded_through_load_knowledge_store_binding"]:
        raise SystemExit("the contrast-card receipt is not a released, re-loaded store")

    one_factor = (
        "ONE PIN, knowledge CONTENT (owner decision 164; W3a alone by the coordinator ruling of 2026-09-27): "
        "the intent-boundaries store moves from "
        "intent-boundaries-v1 to intent-boundaries-contrast-v1 -- each card keeps its header, activation "
        "boundary, authored exclusion and card-specific limitations verbatim, drops the shared boilerplate "
        "and carries contrast lines against its nearest TRAIN-centroid rivals (typical TRAIN words and "
        "slot types on each side), never costing more tokens than the flown card; facets, keys and value "
        "ids are unchanged, so Perception's delivery is the AGREE arm's own. The per-intent exemplar cap "
        "(W3b) of the first registration is dropped. Nothing else moves: roster, geometry, session, program "
        "and its 11-contact ceiling, the agreement term, the Solver exemplar supply (the supply filter at "
        "k 20), the slot-contracts store, the role graph, every template, the deliver normaliser and the "
        "scorers are the retained AGREE arm's, byte for byte."
    )
    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
        "--set-ready, which also mints this cell's own first-phase supply under its own run id "
        "(item E16) and appends the preparation requirement; the requirements list is empty by "
        "design, --allow-output-change must never be passed, and the minted supply must reproduce "
        "the AGREE arm's output digest " + AGREE_SUPPLY_OUTPUT_SHA + " (the Perception supply reads "
        "keys and value ids, which W3 does not move). Nothing here authorises a flight, a readiness "
        "flip or an admission entry."
    )
    written = []

    arm_pairs = substitutions(smoke=False)
    derive_baseline(
        AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-w3-fold-a-baseline-v1.json", arm_pairs,
        cards=cards,
        what_this_is="Cell W3 (W3a alone): the retained AGREE arm with one knowledge-content pin. " + one_factor,
    )
    written.append("configs/baseline/slurp-native-stage3-w3-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-w3-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell W3 (W3a alone) on TRAIN Fold A 1,080: with the intent cards carrying TRAIN-derived "
            "contrast lines instead of boilerplate, do the official "
            "intent accuracy (primary, owner decision 133) and the official pooled SLU-F1 (guard) stay "
            "within the design's own null of the retained AGREE arm, read at the SHARED wave-1 in-chain "
            f"A/A {SHARED_AA} flown in the same chain? Registered as a NO-HARM read (no measured "
            "conversion applies to contrast text, owner decision 139): admitted "
            "iff each metric's CI95 lower bound against the in-chain A/A is not below the negative of its "
            "Fold A own-null half-width (intent 0.9943, SLU 1.2485), HARMFUL on a measured loss, never "
            "reported as a gain. " + one_factor + " Development numbers only (owner decisions 28 and 86); "
            "never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell W3 registered before contact on " + args.date + " from the retained AGREE arm "
            "fragments by script (decision 58) with one knowledge-content pin (owner decision 164; W3a "
            "alone, re-registered in place of the first W3a + W3b registration by the coordinator ruling "
            "of 2026-09-27). "
            "Comparator: the sealed AGREE arm " + AGREE_RUN + ", never re-flown, read at the shared "
            "wave-1 in-chain A/A " + SHARED_AA + " (registered by the coordinator) flown in the same "
            "campaign chain." + held
        ),
        campaign=True, arm_rows=True,
    )
    written.append("configs/experiment/slurp-native-stage3-w3-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(
        AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-w3-fold-a-smoke-4-baseline-v1.json", smoke_pairs,
        cards=cards,
        what_this_is=(
            "Four-row structural form smoke of cell W3 (W3a alone): the same pin on the first four rows of the "
            "unchanged TRAIN Fold A roster. " + one_factor
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-w3-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-w3-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell W3 (W3a alone): that the contrast-card release loads, "
            "that every request fits and that the episode completes. It is scored by no one and read by no one: four rows can never be "
            "evidence of benefit or of harm. " + one_factor
        ),
        readiness_reason=(
            "Four-row form smoke of cell W3, registered before contact on " + args.date + " from the "
            "retained AGREE smoke fragments by script (decision 58). Structural form proof only: no "
            "score, no read, no claim." + held
        ),
        campaign=False, arm_rows=False,
    )
    written.append("configs/experiment/slurp-native-stage3-w3-fold-a-smoke-4-v1.json")

    wr(CAMPAIGN, json.dumps({
        "cells": [
            {"cell": "slurp-native-stage3-w3-fold-a-v1", "experiment": "slurp-native-stage3-w3-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN)
    print(json.dumps({"written": written, "variant": "W3a alone",
                      "contrast_snapshot": cards["release"]["snapshot"]["content_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
