#!/usr/bin/env python3
"""Derive the knowledge wave's ONE shared in-chain A/A -- ``SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1`` --
from the RETAINED AGREE arm fragments (owner decisions 161 and 164; decision 58: script-derived
registrations; the decision-160 precedent of one shared in-chain A/A).

THE ZERO CHANGE. The A/A is the retained AGREE arm (``SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1``: w_agree
1.0 over the self-excluded exemplar-intent vote, recall k 60, delivered width 8, the released
intent-boundaries / slot-contracts / train-exemplars stores and every template) re-flown under its
OWN run, attempt and FIT ids. No knowledge, rank, cap, template, role-graph, roster, geometry or
session key moves; the only differences from the AGREE fragments are per-flight bookkeeping (ids,
prose, the FIT spend identity, the readiness block) and the dropped ``prepared_phase_supply`` pin
(item E16: the flip mints this cell's own first-phase supply under its own run id, and that supply
must reproduce the AGREE arm's output digest ``eab5c61e...`` -- the flip's byte-identity check).
``scripts/flights/wave/wave_shared_aa_proof.py`` proves the composed config, the prepared supply and
the request bytes identical to the AGREE arm's, model-free.

ONE CELL, NO SMOKE. The AGREE and COMP-1 A/A cells carried no smoke of their own either: the A/A is
the AGREE arm's own already-flown form, and the chain smokes W1 (the first arm) before anything is
spent. The A/A flies in the FIRST step of ``scripts/flights/wave/batch_chain_wave.sh`` inside the
wave campaign plan ``configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json`` = [the wave A/A,
the W1 arm] -- the COMP-1 shape of decision 160 -- and W3 and W4 fly as the later steps of the same
chain, on the same resident session, each read against this A/A.

The readiness requirements carry the agreement table exactly as the AGREE cell pins it; the decision
requirement is inserted by ``repin_cell.py --set-ready`` once root has minted the A/A's receipt.
Config only: no contact, no ledger row, no receipt, no flip.

    python scripts/flights/wave/derive_slurp_wave_aa_cell.py --date 2026-09-27
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
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
AA_CELL = "slurp-native-stage3-wave1-aa-fold-a-v1"
AA_BASELINE = "slurp-native-stage3-wave1-aa-fold-a-baseline-v1"
W1_CELL = "slurp-native-stage3-w1-cardsel-fold-a-v1"
AGREE_ARM_SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
WAVE_CAMPAIGN = "configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json"

SUBSTITUTIONS: list[tuple[str, str]] = [
    ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-FIT-V1"),
    ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", AA_RUN),
    ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-wave1-aa-fold-a-generation-v1"),
    ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-wave1-aa-fold-a-fit-v1"),
    ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", AA_BASELINE),
    ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-wave1-aa-fold-a-v1"),
    ("slurp-native-stage3-agree-w1-fold-a-v1", AA_CELL),
]

ZERO_FACTOR = (
    "The knowledge wave's shared in-chain A/A (owner decision 164): the retained AGREE arm "
    + AGREE_RUN
    + " byte for byte -- w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, delivered "
    "width 8 (fuse_coverage 8 / 1 / 8), the released intent-boundaries, slot-contracts and train-exemplars "
    "stores and their pins, the exemplar k of 20, the card route's caps (3 / 16 / 28), the role graph and its "
    "11-contact ceiling, every template, the deliver normaliser, the scorers, the roster, the geometry and the "
    "session -- re-flown under its own run, attempt and FIT ids. NOTHING moves: it is the within-chain null "
    "each wave arm (W1, W3, W4) is read at, flown in the same chain on the same resident session."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is an A/A replicate -- the "
    "INSTRUMENT, not a mechanism -- re-flying the retained AGREE arm's own bytes so the wave arms' deltas are "
    "read against a within-chain null (measurement instrument rule 3). No rollout, no per-sample scoring, no "
    "credit assignment, no update operator and no evolving store."
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


def substitute(text: str) -> str:
    for old, new in SUBSTITUTIONS:
        text = text.replace(old, new)
    return text


def derive_baseline(out_path: str) -> None:
    raw = rd(AGREE_ARM_BASELINE)
    document = json.loads(raw)
    # E16: the flip mints this cell's OWN supply under its own run id; drop the parent's pin
    # BEFORE the id rewrite so its relpath never turns into ours.
    if "prepared_phase_supply" not in document:
        raise SystemExit("the AGREE baseline carries no prepared_phase_supply pin; is this the retained AGREE arm?")
    document.pop("prepared_phase_supply")
    boundary = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if boundary.get("k") != 60:
        raise SystemExit(f"the AGREE baseline's boundary recall k is {boundary.get('k')!r}, not 60")
    document = json.loads(substitute(json.dumps(document, ensure_ascii=False)))
    document["what_this_is"] = ZERO_FACTOR
    wr(out_path, dump_like(raw, document))


def derive_experiment(out_path: str, date: str) -> None:
    raw = rd(AGREE_ARM_EXPERIMENT)
    parent = json.loads(raw)
    agreement = [
        requirement for requirement in parent["cells"][0]["readiness"]["requirements"]
        if requirement.get("kind") == "preparation" and requirement.get("relpath") == AGREEMENT_RELPATH
    ]
    if len(agreement) != 1:
        raise SystemExit("the AGREE cell does not pin exactly one agreement-table preparation requirement")
    document = json.loads(substitute(raw))
    document["date"] = date
    document["purpose"] = (
        "The knowledge wave's ONE shared in-chain A/A on TRAIN Fold A 1,080 (owner decision 164, the decision-160 "
        "precedent): the retained AGREE arm's own bytes re-flown in the same chain as the wave arms W1 (slot-card "
        "selection), W3 (intent contrast cards) and W4 (slot conventions), so each arm's paired delta is read at a "
        "within-chain null rather than against the sealed AGREE arm alone (measurement instrument rules 3 and 4). "
        "Its expected effect against the sealed AGREE arm is exactly zero by construction; a non-zero read on it is a "
        "measurement of the instrument, which is what it is for. " + ZERO_FACTOR + " Development numbers only (owner "
        "decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission "
        "entry."
    )
    document["failure_policy"] = (
        document["failure_policy"]
        .replace("closes cell PLAN", "closes this cell")
        .replace("stops cell PLAN", "stops this cell")
    )
    if "generation_budget" in document:
        document["generation_budget"]["definition"] = (
            "The retained AGREE arm's role graph is unchanged: perception 1, solver 1, reviewer 3, planner 1, "
            "max_revisions 1, so rails.native_episode_config.load_native_episode_config resolves the program ceiling "
            "1 + 2 * (3 + 1 + 1) = 11 contacts per row and 1,080 * 11 = 11,880 is the exact program maximum rather "
            "than a conservative safety bound. The sealed AGREE arm realized 4,385 contacts (4.060 per row), so the "
            "expected spend of this A/A is about 4,400 contacts; nothing in the request moves. The budget is "
            "RUN-CUMULATIVE across every attempt of this run id, which is what makes the resume-recovery clause safe."
        )
        document["generation_budget"]["target"] = 4385
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker", "campaign"]
    held = (
        " HELD: root mints the A/A's admission receipt (scripts/flights/wave/wave_mint_receipt.py) and re-pins with "
        "scripts/flights/repin_cell.py --set-ready (through scripts/flights/wave/wave_flip.sh), which mints this "
        "cell's own first-phase supply under its own run id (item E16) and inserts the decision requirement; "
        "--allow-output-change must never be passed, and the minted supply must reproduce the AGREE arm's own output "
        "digest " + AGREE_ARM_SUPPLY_OUTPUT_SHA + ". Nothing here authorises a flight, a readiness flip or an "
        "admission entry."
    )
    cell["readiness"] = {
        "reason": (
            "The knowledge wave's shared in-chain A/A, registered before contact on " + date + " from the retained "
            "AGREE arm fragments by script (decisions 58, 161 and 164; the decision-160 precedent) with nothing "
            "changed but per-flight bookkeeping. It flies in the wave campaign plan " + WAVE_CAMPAIGN + " beside the "
            "W1 arm, and W3 and W4 are read at it from the later steps of the same chain." + held
        ),
        "requirements": agreement,
        "state": "held",
    }
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)
    written = []
    out = f"configs/baseline/{AA_BASELINE}.json"
    derive_baseline(out)
    written.append(out)
    out = f"configs/experiment/{AA_CELL}.json"
    derive_experiment(out, args.date)
    written.append(out)
    wr(WAVE_CAMPAIGN, json.dumps({
        "cells": [
            {"cell": AA_CELL, "experiment": AA_CELL},
            {"cell": W1_CELL, "experiment": W1_CELL},
        ],
        "schema": "saea-campaign-plan-v1",
    }, indent=2, sort_keys=True) + "\n")
    written.append(WAVE_CAMPAIGN)
    print(json.dumps({"written": written, "run_id": AA_RUN, "expected_supply_output_sha256": AGREE_ARM_SUPPLY_OUTPUT_SHA}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
