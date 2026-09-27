#!/usr/bin/env python3
"""Derive the three SLOTFILL cells -- the dispatcher slot-fill engineering-base item (owner
decision 159) -- from the LOCKED PLAN fragments (decision 58: script-derived registrations).

THE ONE KEY. The arm and its smoke add ONE top-level baseline key, ``dispatch`` (schema
``saea-dispatch-slot-fill-v1``, ``rails.dispatch_slot_fill``): the runtime keeps the slots loaded
by moving the first Solver visit's Perception-independent exemplar recall off the critical path
(``recall_prefetch``), by running the episode graph's role-input builder off the shared event
loop (``role_input_offload``) and by freezing the loaded static heap out of the garbage
collector's generations (``gc_freeze``). Scheduling only: the model-free proof bench
(``scripts/analysis/slotfill_fake_server_harness.py``) shows every request body, every sealed row
and every trace record identical with the key on and off, modulo the two facts the dispatcher
already assigns by arrival (the request-id counter and the slot number). Nothing else moves:
the roster, the geometry, the session, the program and its 11-contact ceiling, the three
stores and their pins, the exemplar k of 20, the role graph, every template, the deliver
normaliser and the scorers are the locked plan's, byte for byte.

THREE CELLS, because a cross-flight contrast against a sealed comparator needs an in-chain
replicate (``docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md`` rules 3 and
4), exactly as the AGREE and G5 families were cut: the SLOTFILL arm on TRAIN Fold A 1,080; its
four-row structural smoke (outside the campaign plan); and an A/A replicate -- the locked PLAN
form WITHOUT the key, flown in the SAME campaign chain -- so both the no-harm read and the
throughput read are taken against a within-chain twin.

Every cell drops ``prepared_phase_supply`` so the flip mints each cell's OWN first-phase supply
under its own run id (item E16); the requirements list is EMPTY and ``--allow-output-change``
must never be passed. The ``dispatch`` key enters the supply's identity (the composed config)
but not its computation, so every minted supply must reproduce the sealed PLAN preparation's
output digest ``ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f``.

This script writes CONFIG ONLY: three baselines, three experiment fragments and one campaign
plan. It performs no contact, writes no ledger row, mints no decision receipt and flips nothing.

    python scripts/flights/derive_slurp_slotfill_cells.py --date 2026-09-27
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
PLAN_SUPPLY_OUTPUT_SHA = "ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f"
PLAN_CALLS_USED = 4424

THE_KEY = "dispatch"
DISPATCH_BLOCK = {
    "schema": "saea-dispatch-slot-fill-v1",
    "recall_prefetch": True,
    "role_input_offload": True,
    "gc_freeze": True,
}

CAMPAIGN = "configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json"

ONE_FACTOR = (
    "ONE top-level baseline key, dispatch = {schema saea-dispatch-slot-fill-v1, recall_prefetch true, "
    "role_input_offload true, gc_freeze true} (rails.dispatch_slot_fill; owner decision 159). It changes "
    "SCHEDULING only: the first Solver visit's exemplar recall -- a function of the row's own sealed "
    "speech query alone, measured at 1.4 s of pure-Python CPU per row on the shared event loop -- is "
    "computed ahead on one background worker while the row's Perception contact is in flight; the "
    "episode graph's role-input builder runs on one dedicated worker instead of the event loop every "
    "row shares, so one row's hand-over no longer blocks every other row's dispatch; and the loaded "
    "static heap is frozen out of the collector's generations. The model-free proof bench shows every "
    "request body, sealed row and trace record identical with the key on and off, modulo the request-id "
    "counter and the slot number, which today's dispatcher already assigns by arrival. Nothing else "
    "moves: roster, geometry, session, program and its 11-contact ceiling, the three stores and their "
    "pins, the exemplar k of 20, the role graph, every template, the deliver normaliser and the "
    "scorers are the locked PLAN plan's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a runtime "
    "scheduling change -- the dispatcher keeps the resident slots loaded -- flown as a row-127 "
    "engineering-base no-harm item under owner decision 159, with no rollout, no per-sample scoring, "
    "no credit assignment, no update operator and no evolving store. It changes no byte any node sees, "
    "so it is not a policy search of any kind."
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


def substitutions(tag: str, slug: str, *, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the PLAN fragment to this cell's own (AGREE's shape)."""

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




def derive_baseline(parent_path: str, out_path: str, pairs, *, armed: bool, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    # E16: the flip mints this cell's OWN supply under its own run id.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is
    if THE_KEY in document:
        raise SystemExit("the parent already declares a dispatch key; the lock must not carry one")
    if "phase_tools" in document:
        raise SystemExit("the parent carries phase_tools; the Reviewer toolkit is RETIRED and the lock must not arm it")
    if armed:
        # THE ONE KEY.
        document[THE_KEY] = dict(DISPATCH_BLOCK)
    wr(out_path, dump_like(raw, document))


def derive_experiment(parent_path: str, out_path: str, pairs, args, *, purpose: str,
                      readiness_reason: str, campaign: bool, arm_rows: bool) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    document["failure_policy"] = document["failure_policy"].replace("closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    if arm_rows:
        document["generation_budget"] = {
            "cap": 11880,
            "definition": (
                "The locked PLAN role graph is unchanged: perception 1, solver 1, reviewer 3, planner 1, "
                "max_revisions 1, so rails.native_episode_config.load_native_episode_config resolves the "
                "program ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and 1,080 * 11 = 11,880 is the "
                "exact program maximum rather than a conservative safety bound. The sealed PLAN arm's own "
                f"realized cost was {PLAN_CALLS_USED:,} contacts ({PLAN_CALLS_USED / 1080:.3f} per row) and about "
                "3.7 GPU hours; the dispatch key moves no contact, no token and no request, so the expected "
                f"spend is about {PLAN_CALLS_USED:,} contacts, and the item's own ceiling is the WALL time those "
                "contacts take. The budget is RUN-CUMULATIVE across every attempt of this run id, which is "
                "what makes the resume-recovery clause safe."
            ),
            "target": PLAN_CALLS_USED,
        }
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": [], "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
        "--set-ready, which also mints this cell's own first-phase supply under its own run id "
        "(item E16) and appends the preparation requirement; the requirements list is empty by "
        "design, --allow-output-change must never be passed, and the minted supply must reproduce "
        "the sealed PLAN output digest " + PLAN_SUPPLY_OUTPUT_SHA + " (the dispatch key is not an "
        "input to its computation). Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    written = []

    arm_pairs = substitutions("SLOTFILL", "slotfill", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE, "configs/baseline/slurp-native-stage3-slotfill-fold-a-baseline-v1.json", arm_pairs,
        armed=True,
        what_this_is="Cell SLOTFILL: the locked v2.0 plan with ONE key added, the dispatcher slot-fill switches. " + ONE_FACTOR,
    )
    written.append("configs/baseline/slurp-native-stage3-slotfill-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-slotfill-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell SLOTFILL on TRAIN Fold A 1,080: with the dispatcher keeping the resident slots loaded, do "
            "the official intent accuracy (primary, owner decision 133) and the official pooled SLU-F1 "
            "(guard) stay within the plan's own null, read at the in-chain A/A flown beside it, and how many "
            "contacts per GPU-hour does the same work take? A row-127 ENGINEERING-BASE item under owner "
            "decision 159: admitted on NO HARM (each metric's CI95 lower bound against the in-chain A/A not "
            "below the negative of its own Fold A half-width, intent 0.9943 / SLU 1.2485), never reported as "
            "a gain; the ceiling it unlocks is throughput, read as contacts per GPU-hour and empty "
            "slot-seconds against the A/A. " + ONE_FACTOR + " Development numbers only (owner decisions 28 "
            "and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell SLOTFILL registered before contact on " + args.date + " from the locked cell PLAN fragments "
            "by script (decision 58) with one key added (owner decision 159). Comparator: the sealed PLAN arm "
            + PLAN_RUN + ", never re-flown, read at the in-chain A/A replicate "
            "SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1 flown in the same campaign chain." + held
        ),
        campaign=True, arm_rows=True,
    )
    written.append("configs/experiment/slurp-native-stage3-slotfill-fold-a-v1.json")

    smoke_pairs = substitutions("SLOTFILL", "slotfill", smoke=True)
    derive_baseline(
        PLAN_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-slotfill-fold-a-smoke-4-baseline-v1.json", smoke_pairs,
        armed=True,
        what_this_is=(
            "Four-row structural form smoke of cell SLOTFILL: the same one key on the first four rows of the "
            "unchanged TRAIN Fold A roster. " + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-slotfill-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        PLAN_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-slotfill-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell SLOTFILL: that the dispatch key parses, that the three "
            "switches arm on the resident geometry, that every request fits and that the episode completes and "
            "seals. It is scored by no one and read by no one: four rows can never be evidence of benefit, of "
            "harm or of throughput. " + ONE_FACTOR
        ),
        readiness_reason=(
            "Four-row form smoke of cell SLOTFILL, registered before contact on " + args.date + " from the locked "
            "cell PLAN smoke fragments by script (decision 58). Structural form proof only: no score, no read, "
            "no claim." + held
        ),
        campaign=False, arm_rows=False,
    )
    written.append("configs/experiment/slurp-native-stage3-slotfill-fold-a-smoke-4-v1.json")

    aa_pairs = substitutions("SLOTFILL-AA", "slotfill-aa", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE, "configs/baseline/slurp-native-stage3-slotfill-aa-fold-a-baseline-v1.json", aa_pairs,
        armed=False,
        what_this_is=(
            "The IN-CHAIN A/A REPLICATE of cell SLOTFILL: the locked v2.0 plan's own form WITHOUT the dispatch "
            "key and every other byte unchanged, re-flown in the same campaign chain as cell SLOTFILL so both "
            "the no-harm read and the throughput read are taken against a within-chain twin instead of a "
            "between-flight offset. Authority: docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md "
            "rules 3 and 4. Its own prepared first-phase supply must reproduce the sealed PLAN preparation's "
            "output digest " + PLAN_SUPPLY_OUTPUT_SHA + " exactly. If a round flies several base items in one "
            "chain, one A/A serves them all and this cell is dropped from the campaign plan before the flip."
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-slotfill-aa-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-slotfill-aa-fold-a-v1.json", aa_pairs, args,
        purpose=(
            "The in-chain A/A replicate of cell SLOTFILL: the locked plan's own form, unchanged and without the "
            "dispatch key, re-flown in the same campaign chain, to supply the within-chain null the SLOTFILL "
            "no-harm read and the within-chain baseline the throughput read are taken at. It makes no claim of "
            "its own and admits nothing; it is the instrument. Development numbers only (owner decisions 28 and 86)."
        ),
        readiness_reason=(
            "The in-chain A/A replicate of cell SLOTFILL, registered before contact on " + args.date + " from the "
            "locked cell PLAN fragments by script (decision 58): the same baseline bytes, no dispatch key, its own "
            "run, attempt and fit ids." + held
        ),
        campaign=True, arm_rows=True,
    )
    written.append("configs/experiment/slurp-native-stage3-slotfill-aa-fold-a-v1.json")

    wr(CAMPAIGN, json.dumps({
        "cells": [
            {"cell": "slurp-native-stage3-slotfill-aa-fold-a-v1", "experiment": "slurp-native-stage3-slotfill-aa-fold-a-v1"},
            {"cell": "slurp-native-stage3-slotfill-fold-a-v1", "experiment": "slurp-native-stage3-slotfill-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN)
    print(json.dumps({"written": written, "dispatch": DISPATCH_BLOCK}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
