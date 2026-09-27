#!/usr/bin/env python3
"""Derive the three G5 cells -- the Reviewer-instruction repair (owner decisions
135 and 153, a row-127 no-harm item) -- from the LOCKED PLAN fragments
(decision 58: script-derived registrations).

THE ONE PIN. ``phase_material.reviewer.instruction_template`` moves from
``probes/slurp_native_role_reviewer_v1.txt`` to
``probes/slurp_native_role_reviewer_v1_g5_v1.txt``: the same instruction with
the two sentences that order the Reviewer to call a task-contract tool RETIRED
as item E25 deleted, and NOTHING added (the deletion-only proof is in the
package receipt ``instruction-token-measurement-v1.json`` and re-proven by
``tests/unit/test_g5_config.py``). Nothing else moves: the roster, the
geometry, the session, the program and its 11-contact ceiling, the three
stores and their pins, the exemplar k of 20, the role graph, every other
template, the deliver normaliser and the scorers are the locked plan's, byte
for byte. The pin costs NEGATIVE tokens: 52 fewer per Reviewer contact.

THREE CELLS, because a cross-flight contrast against a sealed comparator needs
an in-chain replicate (``docs/readiness/2026-09-26-slurp-stage3-measurement-
instrument-v1.md`` rules 3 and 4), exactly as the AGREE family was cut:

  * the G5 arm on TRAIN Fold A 1,080;
  * its four-row structural form smoke (outside the campaign plan);
  * an A/A replicate -- the locked PLAN form unchanged, the OLD instruction,
    flown in the SAME campaign chain, so the no-harm read is taken against a
    within-chain null rather than a between-flight offset. If round 3 flies
    several consumption-form items in one chain, ONE A/A can serve them all:
    drop this family's A/A from the campaign plan before the flip and
    re-point ``replicate_run_id`` at the shared one.

Every cell drops ``prepared_phase_supply`` so the coordinator's flip mints
each cell's OWN first-phase supply under its own run id (item E16) and
appends the preparation requirement itself; the requirements list is EMPTY
here and ``--allow-output-change`` must never be passed. The Reviewer
instruction is not an input to the first-phase supply, so every minted
supply must reproduce the sealed PLAN preparation's output digest
``ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`` -- that
equality is the flip's byte-identity check.

This script writes CONFIG ONLY: three baselines, three experiment fragments
and one campaign plan. It performs no contact, writes no ledger row, mints no
decision receipt and flips nothing.

    python scripts/flights/derive_slurp_g5_cells.py --date 2026-09-27 \\
        --measurement docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/instruction-token-measurement-v1.json
"""

from __future__ import annotations

import argparse
import hashlib
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

OLD_TEMPLATE = "probes/slurp_native_role_reviewer_v1.txt"
NEW_TEMPLATE = "probes/slurp_native_role_reviewer_v1_g5_v1.txt"

CAMPAIGN = "configs/campaign/slurp-native-stage3-g5-fold-a-v1.json"

ONE_FACTOR = (
    "The Reviewer node's instruction template moves from probes/slurp_native_role_reviewer_v1.txt "
    "to probes/slurp_native_role_reviewer_v1_g5_v1.txt: the same instruction with the two "
    "sentences that order the Reviewer to call the task-contract tool 'exactly once through its "
    "native function schema' and to 'use only its returned source-bound result' DELETED, and "
    "nothing added -- no new guidance, no rephrasing of the surviving clauses (deletion-only, "
    "proven word by word). That toolkit was RETIRED as item E25 after the B1-notool read (owner "
    "decisions 55, 56 and 61); the locked plan renders 0 tool schemas in every contact, so the "
    "deleted sentences ordered an action the node cannot perform and the 2026-09-26 system-summary "
    "diagnostic recorded the consequence: summaries treating a Reviewer's textual tool-result "
    "claims as real execution while the tool event list is empty. Measured with the audit's own "
    "vocab-only tokenizer: the deleted order is 52 of the instruction's 82 tokens (63 %), so the "
    "pin costs -52 prompt tokens per Reviewer contact. Nothing else moves: roster, geometry, "
    "session, program and its 11-contact ceiling, the three stores and their pins, the exemplar k "
    "of 20, the role graph, every other template, the deliver normaliser and the scorers are the "
    "locked PLAN plan's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a one-pin "
    "instruction repair -- the deletion of an order to use a retired tool -- chosen by a "
    "model-free audit over sealed bytes and flown as a row-127 engineering-base no-harm item, "
    "with no rollout, no per-sample scoring, no credit assignment, no update operator and no "
    "evolving store. It is deliberately NOT labelled sealed-credit-system-policy-v1: that id's "
    "first instance is reserved for the composed system policy, and a deletion is not a policy "
    "search."
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


def derive_baseline(parent_path: str, out_path: str, pairs, *, repaired: bool, what_this_is: str) -> None:
    raw = rd(parent_path)
    document = json.loads(substitute(raw, pairs))
    # E16: the flip mints this cell's OWN supply under its own run id.
    document.pop("prepared_phase_supply", None)
    document["what_this_is"] = what_this_is
    reviewer = document["phase_material"]["reviewer"]
    if reviewer["instruction_template"] != OLD_TEMPLATE:
        raise SystemExit(f"the parent's Reviewer template is {reviewer['instruction_template']!r}, not the v1 file")
    if "phase_tools" in document:
        raise SystemExit("the parent carries phase_tools; the Reviewer toolkit is RETIRED and the lock must not arm it")
    if repaired:
        # THE ONE PIN.
        reviewer["instruction_template"] = NEW_TEMPLATE
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
                "The locked PLAN role graph is unchanged: perception 1, solver 1, reviewer 3, "
                "planner 1, max_revisions 1, so rails.native_episode_config.load_native_episode_config "
                "resolves the program ceiling 1 + 2 * (3 + 1 + 1) = 11 contacts per row and "
                "1,080 * 11 = 11,880 is the exact program maximum rather than a conservative safety "
                "bound. The sealed PLAN arm's own realized cost was "
                + f"{args.plan_calls_used:,}"
                + " contacts ("
                + f"{args.plan_calls_used / 1080:.3f}"
                + " per row, of which "
                + f"{args.plan_reviewer_contacts:,}"
                + " Reviewer contacts) and about 3.7 GPU hours, so the expected spend is about "
                + f"{args.plan_calls_used:,}"
                + " contacts and about 3.7 GPU hours -- less "
                + f"{args.saved_tokens_per_contact}"
                + " prefill tokens per Reviewer contact, which no cap is denominated in. The "
                "train-exemplars store supplies the Solver phase and adds prompt tokens, never "
                "contacts. The budget is RUN-CUMULATIVE across every attempt of this run id, which "
                "is what makes the resume-recovery clause safe."
            ),
            "target": args.plan_calls_used,
        }
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": [], "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out_path, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--measurement", required=True, help="repo-relative instruction-token-measurement-v1.json")
    args = parser.parse_args(argv)

    receipt = json.loads(rd(args.measurement))
    if receipt["schema"] != "saea-g5-reviewer-instruction-token-measurement-v1":
        raise SystemExit("the measurement receipt is not the expected schema")
    new_relpath = receipt["instruction"]["new"]["relpath"]
    if new_relpath != "configs/" + NEW_TEMPLATE:
        raise SystemExit(f"the receipt names {new_relpath}, expected configs/{NEW_TEMPLATE}")
    on_disk = hashlib.sha256(io.open(new_relpath, "rb").read()).hexdigest()
    if on_disk != receipt["instruction"]["new"]["sha256"]:
        raise SystemExit("the repaired instruction on disk does not hash to the measurement receipt's sha256")
    proof = receipt["deletion_only_proof"]
    if not (proof["word_level"]["only_equal_and_delete"] and proof["byte_level"]["old_equals_deleted_head_plus_new"]):
        raise SystemExit("the receipt does not prove a deletion-only edit; refusing to derive")
    args.plan_calls_used = int(receipt["sealed_reviewer_contact_rate"]["plan"]["run_manifest_cost"]["calls_used"])
    args.plan_reviewer_contacts = int(receipt["sealed_reviewer_contact_rate"]["plan"]["reviewer_contacts"])
    args.saved_tokens_per_contact = int(receipt["saving"]["tokens_per_reviewer_contact"])

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
        "--set-ready, which also mints this cell's own first-phase supply under its own run id "
        "(item E16) and appends the preparation requirement; the requirements list is empty by "
        "design, --allow-output-change must never be passed, and the minted supply must reproduce "
        "the sealed PLAN output digest " + PLAN_SUPPLY_OUTPUT_SHA + " (the Reviewer instruction is "
        "not an input to it). Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    written = []

    # ---- the G5 arm -----------------------------------------------------
    arm_pairs = substitutions("G5", "g5", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE, "configs/baseline/slurp-native-stage3-g5-fold-a-baseline-v1.json", arm_pairs,
        repaired=True,
        what_this_is=(
            "Cell G5: the locked v2.0 plan with ONE pin moved -- the Reviewer node's instruction "
            "template, from the v1 file to the g5_v1 file that deletes the retired-tool order. "
            + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-g5-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-g5-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell G5 on TRAIN Fold A 1,080: with the Reviewer's retired-tool order deleted from its "
            "instruction, do the official intent accuracy (primary, owner decision 133) and the "
            "official pooled SLU-F1 (guard) stay within the plan's own null of the sealed PLAN arm, "
            "read at the in-chain A/A null flown beside it? A row-127 ENGINEERING-BASE item: admitted "
            "on NO HARM (each metric's CI95 lower bound against the in-chain A/A not below the "
            "negative of its own Fold A half-width, intent 0.9943 / SLU 1.2485), never reported as a "
            "gain; the ceiling it unlocks is a Reviewer that is no longer instructed to fabricate a "
            "tool result, at -52 prompt tokens per Reviewer contact. " + ONE_FACTOR
            + " Development numbers only (owner decisions 28 and 86); never a test claim. Nothing "
            "here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell G5 registered before contact on " + args.date + " from the locked cell PLAN fragments "
            "by script (decision 58) with one pin moved (owner decisions 135 and 153). Comparator: the "
            "sealed PLAN arm " + PLAN_RUN + ", never re-flown, read at the in-chain A/A replicate "
            "SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1 flown in the same campaign chain." + held
        ),
        campaign=True, arm_rows=True,
    )
    written.append("configs/experiment/slurp-native-stage3-g5-fold-a-v1.json")

    # ---- the four-row form smoke ----------------------------------------
    smoke_pairs = substitutions("G5", "g5", smoke=True)
    derive_baseline(
        PLAN_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-g5-fold-a-smoke-4-baseline-v1.json", smoke_pairs,
        repaired=True,
        what_this_is=(
            "Four-row structural form smoke of cell G5: the same one pin on the first four rows of "
            "the unchanged TRAIN Fold A roster. " + ONE_FACTOR
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-g5-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        PLAN_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-g5-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell G5: that the repaired Reviewer instruction loads "
            "by its new relpath, that every request fits, that the Reviewer still answers on its "
            "first contact with no tool call and that the episode completes. It is scored by no one "
            "and read by no one: four rows can never be evidence of benefit or of harm. " + ONE_FACTOR
        ),
        readiness_reason=(
            "Four-row form smoke of cell G5, registered before contact on " + args.date + " from the "
            "locked cell PLAN smoke fragments by script (decision 58). Structural form proof only: no "
            "score, no read, no claim." + held
        ),
        campaign=False, arm_rows=False,
    )
    written.append("configs/experiment/slurp-native-stage3-g5-fold-a-smoke-4-v1.json")

    # ---- the in-chain A/A replicate -------------------------------------
    aa_pairs = substitutions("G5-AA", "g5-aa", smoke=False)
    derive_baseline(
        PLAN_ARM_BASELINE, "configs/baseline/slurp-native-stage3-g5-aa-fold-a-baseline-v1.json", aa_pairs,
        repaired=False,
        what_this_is=(
            "The IN-CHAIN A/A REPLICATE of cell G5: the locked v2.0 plan's own form, the OLD Reviewer "
            "instruction (probes/slurp_native_role_reviewer_v1.txt) and every other byte unchanged, "
            "re-flown in the same campaign chain as cell G5 so the no-harm read is taken against a "
            "within-chain null instead of a between-flight offset. Authority: "
            "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md rules 3 and 4. Its "
            "own prepared first-phase supply must reproduce the sealed PLAN preparation's output "
            "digest " + PLAN_SUPPLY_OUTPUT_SHA + " exactly. If round 3 flies several consumption-form "
            "items in one chain, one A/A serves them all and this cell is dropped from the campaign "
            "plan before the flip."
        ),
    )
    written.append("configs/baseline/slurp-native-stage3-g5-aa-fold-a-baseline-v1.json")
    derive_experiment(
        PLAN_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-g5-aa-fold-a-v1.json", aa_pairs, args,
        purpose=(
            "The in-chain A/A replicate of cell G5: the locked plan's own form, unchanged, re-flown "
            "in the same campaign chain, to supply the within-chain null the G5 no-harm read is taken "
            "at. It makes no claim of its own and admits nothing; it is the instrument. Development "
            "numbers only (owner decisions 28 and 86)."
        ),
        readiness_reason=(
            "The in-chain A/A replicate of cell G5, registered before contact on " + args.date + " from "
            "the locked cell PLAN fragments by script (decision 58): the same baseline bytes, the OLD "
            "Reviewer instruction, its own run, attempt and fit ids." + held
        ),
        campaign=True, arm_rows=True,
    )
    written.append("configs/experiment/slurp-native-stage3-g5-aa-fold-a-v1.json")

    wr(CAMPAIGN, json.dumps({
        "cells": [
            {"cell": "slurp-native-stage3-g5-aa-fold-a-v1", "experiment": "slurp-native-stage3-g5-aa-fold-a-v1"},
            {"cell": "slurp-native-stage3-g5-fold-a-v1", "experiment": "slurp-native-stage3-g5-fold-a-v1"},
        ],
        "schema": "saea-campaign-plan-v1",
    }, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN)
    print(json.dumps({"written": written, "new_template": NEW_TEMPLATE, "new_template_sha256": on_disk,
                      "plan_calls_used": args.plan_calls_used, "plan_reviewer_contacts": args.plan_reviewer_contacts},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
