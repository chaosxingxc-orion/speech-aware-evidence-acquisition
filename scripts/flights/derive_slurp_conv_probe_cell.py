#!/usr/bin/env python3
"""Derive cell CONV -- the conversion probe -- from the registered AGREE arm's
own fragments (decision 58: script-derived registrations).

WHAT THIS PROBE IS FOR. The AGREE arm's declared expectation is a product:
a MEASURED delivery gain (70 newly delivered INTENT-UNCOVERED rows of TRAIN
Fold A) times an UNMEASURED persuasion factor stated at the midpoint of [0, 1].
Its ceiling at a perfect conversion is 2.9131 pp SLU-F1 against a 2.5 pp
admission bar at n = 1,080, so the arm needs a conversion of at least 0.8582 to
clear its own bar and the declared 0.4679 does not. Flying the arm and its
in-chain A/A costs about 7 GPU-hours to learn that one number. This cell
measures it directly on the 70 rows the gain lands on, for about 0.4 GPU-hours.

NO NEW MECHANISM. Every byte of the treatment is the registered AGREE arm's:
the same baseline fragment content, the same one factor (w_agree 1.0 over the
pinned self-excluded exemplar-intent vote, recall k 60, delivered width 8), the
same model fragment, geometry, session, program, stores, role graph, templates,
normaliser and scorers. Exactly two things change, and both are roster
arithmetic: the population is restricted to the 70 derived ids, and every
ceiling is rescaled to 70 rows.

NO COMPARATOR IS FLOWN. The sealed PLAN arm
``SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`` already holds these 70 rows'
answers, and every one of them is intent-WRONG there -- INTENT-UNCOVERED
collapses to INTENT-WRONG in the bad-case bank's own convention -- so the
probe flies the treatment alone and the contrast is per-row and offline.

WHY A PER-ROW INTENT READ IS LEGIBLE AT n = 70. The within-flight null
``docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md``
measured 0 intent flips in 200 request-identical rows, so an intent flip is
attributable rather than noise. Pooled SLU-F1 at n = 70 is not legible and is
not read: the official SLU-F1 is entity-only and this mechanism acts on the
intent.

THE ROSTER IS SELECTED USING GOLD, OFFLINE, and the consequence is absolute:
NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its
population was chosen by the mechanism's own effect. See
``docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json``.

``prepared_phase_supply`` is absent and the readiness requirements list is
EMPTY on purpose. The agreement merge moved the implementation sha256 of
``rails.kb_policy``, ``rails.knowledge_provider`` and ``rails.phase_supply``,
which ``FlightRuntime._phase_seed_inputs`` binds, so every
``prepared_phase_supply`` pin in the repository is invalidated; this cell's flip
mints its own under its own run id (item E16) and
``core.flight.repin._set_preparation_requirement`` appends the requirement then.
``--allow-output-change`` must never be passed. An empty list is also the only
safe shape: that function rewrites EVERY ``kind == "preparation"`` entry to the
freshly minted supply pin, so a second preparation requirement would be
silently clobbered at the flip. The agreement table stays pinned where the
loader actually verifies it -- ``agreement_source.sha256`` in the baseline, plus
its build receipt in ``preparation_source_receipts``.

This script writes CONFIG ONLY: one baseline, one experiment fragment and one
campaign plan. It performs no contact, writes no ledger row, mints no decision
receipt and flips nothing.

    python scripts/flights/derive_slurp_conv_probe_cell.py --date 2026-09-26
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

PARENT_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
PARENT_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
ROSTER_DERIVATION = (
    "docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1/roster-derivation-v1.json"
)

OUT_BASELINE = "configs/baseline/slurp-native-stage3-conv-fold-a-70-baseline-v1.json"
OUT_EXPERIMENT = "configs/experiment/slurp-native-stage3-conv-fold-a-70-v1.json"
OUT_CAMPAIGN = "configs/campaign/slurp-native-stage3-conv-fold-a-70-v1.json"

SEALED_COMPARATOR = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
ARM_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"

#: The program's own per-row contact ceiling, from the parent's registered
#: generation budget: perception 1, solver 1, reviewer 3, planner 1,
#: max_revisions 1 -> 1 + 2 * (3 + 1 + 1) = 11.
CONTACTS_PER_ROW = 11
#: The parent family's own ratios, reproduced rather than re-invented:
#: fit endpoints = 4 x generation contacts, native task-contract calls = 6 per
#: row, repeated speech seconds = roster audio x the contact ceiling.
FIT_MULTIPLIER = 4
NATIVE_CONTRACT_PER_ROW = 6
#: The parent's realized rate on the whole roster, 5,425 contacts / 1,080 rows.
PARENT_REALIZED_PER_ROW = 5425 / 1080
#: The parent's realized GPU cost per contact, 3.6819 h / 5,425 contacts.
PARENT_GPU_HOURS_PER_CONTACT = 3.6819 / 5425

ONE_FACTOR = (
    "The intent-boundary Perception channel reads its own registered w_agree term "
    "over a pre-computed, self-excluded exemplar-intent vote: w_agree 1.0, w_cos "
    "unchanged at 1.0, w_prior unchanged at 0.0, and the DELIVERED width unchanged "
    "at 8 entries (fuse_coverage m 8 / c 1 / top_l 8). The RECALL width k is the "
    "store's full 60, because k is the provider's top_k_per_dimension and truncates "
    "by cosine BEFORE the ranker runs -- at 8 the agreement term is inert, measured. "
    "Not one byte of the treatment differs from the registered AGREE arm's: the same "
    "baseline content, model fragment, geometry, session, program, stores, exemplar "
    "k of 20, role graph, templates, normaliser and scorers. Only the roster and the "
    "ceilings differ, and both are arithmetic on 70 rows."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly, for the "
    "same reason its parent does: it is the registered one-factor retrieval change "
    "flown on a smaller roster -- one rank weight and one pre-computed model-free "
    "input, chosen by an offline diagnostic over sealed bytes, with no rollout, no "
    "per-sample scoring, no credit assignment, no update operator and no evolving "
    "store. The family whose description covers a typed construction/consumption "
    "action of this shape is sealed-credit-system-policy-v1, and this cell is "
    "deliberately NOT labelled with it: that id's first instance is reserved for the "
    "composed system policy, and a single weight is not a policy search. A "
    "measurement of a factor is even less of one."
)

SUBSTITUTIONS = [
    (
        "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1",
        "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1",
    ),
    ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1"),
    (
        "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1",
        "attempt-slurp-native-stage3-conv-fold-a-70-generation-v1",
    ),
    (
        "attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1",
        "attempt-slurp-native-stage3-conv-fold-a-70-fit-v1",
    ),
    (
        "slurp-native-stage3-agree-w1-fold-a-baseline-v1",
        "slurp-native-stage3-conv-fold-a-70-baseline-v1",
    ),
    ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-conv-fold-a-70-v1"),
]


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
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


def budgets(rows: int, audio_seconds: float) -> dict:
    """Every ceiling, by the parent family's own arithmetic on this roster."""

    generation = rows * CONTACTS_PER_ROW
    return {
        "rows": rows,
        "audio_seconds": audio_seconds,
        "generation_calls_cap": generation,
        "fit_endpoint_calls_cap": generation * FIT_MULTIPLIER,
        "native_task_contract_calls_cap": rows * NATIVE_CONTRACT_PER_ROW,
        "repeated_speech_audio_seconds_cap": math.ceil(
            audio_seconds * CONTACTS_PER_ROW
        ),
        "gpu_hours_fit_inclusive": 1.0,
        "expected_contacts": round(rows * PARENT_REALIZED_PER_ROW),
        "expected_gpu_hours": round(
            generation * PARENT_GPU_HOURS_PER_CONTACT, 4
        ),
    }


def derive_baseline(rows: int, caps: dict) -> None:
    raw = rd(PARENT_BASELINE)
    document = json.loads(substitute(raw))
    if "prepared_phase_supply" in document:
        raise SystemExit("the parent baseline must carry no prepared_phase_supply")
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"][
        "perception"
    ]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 1.0}:
        raise SystemExit("the parent's boundary rank weights are not the AGREE arm's")
    if perception["k"] != 60 or perception["tau"] != 0.0:
        raise SystemExit("the parent's boundary k/tau are not the AGREE arm's 60 / 0.0")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the parent's boundary fuse coverage is not the flown 8/1/8")
    if "agreement_source" not in perception:
        raise SystemExit("the parent baseline declares no agreement_source")
    document["native_contact_fit"]["contact_cap"] = caps["fit_endpoint_calls_cap"]
    document["what_this_is"] = (
        "Cell CONV, the CONVERSION PROBE of cell AGREE: the registered AGREE "
        "treatment, unchanged, flown on the "
        + str(rows)
        + " TRAIN Fold A rows whose gold intent's boundary entry it newly delivers, to "
        "measure the one term of the arm's declared expectation that is not measured -- "
        "P(correct | newly delivered), the persuasion factor. The sealed PLAN arm "
        + SEALED_COMPARATOR
        + " already holds these rows' answers and is intent-WRONG on every one of them, "
        "so no comparator is flown and the contrast is per-row and offline. "
        + ONE_FACTOR
        + " THE ROSTER WAS SELECTED USING GOLD, OFFLINE: no pooled or roster-level "
        "claim may ever be made from this cell, because its population was chosen by "
        "the mechanism's own effect. Gold reaches no query, no key, no weight, no "
        "selector and no runtime."
    )
    wr(OUT_BASELINE, dump_like(raw, document))


def derive_experiment(args: argparse.Namespace, roster: dict, caps: dict) -> None:
    raw = rd(PARENT_EXPERIMENT)
    document = json.loads(substitute(raw))
    rows = roster["count"]
    document["date"] = args.date
    document["purpose"] = (
        "Cell CONV on the "
        + str(rows)
        + " TRAIN Fold A rows cell AGREE newly delivers: of the rows that receive their "
        "own gold intent's boundary entry only because of the agreement term, what "
        "proportion move from a wrong intent to the gold intent? That proportion IS the "
        "persuasion factor -- the one unmeasured term of the AGREE arm's declared "
        "expectation, which the arm states at the midpoint of [0, 1] and nothing more. "
        "The deliverable is P(correct | newly delivered) with a binomial CI95 plus the "
        "reverse count; multiplying it by the registered per-row headroom of the class "
        "the gain lands on (5.41 / 130 = 0.041615 pp SLU-F1, 12.04 / 130 = 0.092615 pp "
        "intent accuracy) gives the AGREE arm's re-declared expectation. The arm needs a "
        "conversion of at least 0.8582 -- 61 of these "
        + str(rows)
        + " rows -- to clear its own 2.5 pp bar at n = 1,080; it declares 0.4679. "
        + ONE_FACTOR
        + " THE ROSTER WAS SELECTED USING GOLD, OFFLINE, which is legitimate for a "
        "CONDITIONAL estimate on a TRAIN roster and for nothing else: NO POOLED OR "
        "ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its population was "
        "chosen by the mechanism's own effect. This cell claims NO benefit and asks for "
        "NO admission: under the measurement instrument's rule 5 a batch of "
        + str(rows)
        + " rows is a form proof by size, never evidence of benefit. Development numbers "
        "only (owner decisions 28 and 86); never a test claim. Nothing here authorises a "
        "flight, a readiness flip or an admission entry."
    )
    document["population"] = {
        "count": rows,
        "dataset_fragment": roster["dataset_fragment"],
        "decision_population": (
            "The "
            + str(rows)
            + " rows of TRAIN Fold A whose plan_class in the sealed PLAN arm's bad-case "
            "bank is INTENT-UNCOVERED and whose own gold intent's intent-boundary value "
            "id enters the fused Perception selection at w_agree 1.0 and not at "
            "w_agree 0.0 -- the exact population the AGREE arm's expected-effect "
            "arithmetic charges its gain against, reconstructed from the committed "
            "production-replication receipt's own recipe and proven against every count "
            "that receipt committed (" + ROSTER_DERIVATION + "). Every row is "
            "intent-WRONG in the sealed comparator, so the conditional rate is the whole "
            "estimate. SELECTED USING GOLD, OFFLINE: conditional estimate only, no "
            "pooled or roster-level claim, ever."
        ),
        "split_identity_hash": roster["split_identity_hash"],
    }
    document["populations"] = [
        {"dataset_fragment": roster["dataset_fragment"], "ids": list(roster["ids"])}
    ]
    document["family_budget"] = {
        "asr_calls": 0,
        "ceilings_are_not_targets": True,
        "encoder_calls": 0,
        "fit_endpoint_calls_cap": caps["fit_endpoint_calls_cap"],
        "generation_calls_cap": caps["generation_calls_cap"],
        "gpu_hours_fit_inclusive": caps["gpu_hours_fit_inclusive"],
        "native_task_contract_calls_cap": caps["native_task_contract_calls_cap"],
        "official_complete_scoring_jobs": 1,
        "repeated_speech_audio_seconds_cap": caps["repeated_speech_audio_seconds_cap"],
    }
    document["generation_budget"] = {
        "cap": caps["generation_calls_cap"],
        "definition": (
            "The AGREE arm's role graph is unchanged: perception 1, solver 1, reviewer 3, "
            "planner 1, max_revisions 1, so "
            "rails.native_episode_config.load_native_episode_config resolves the program "
            "ceiling 1 + 2 * (3 + 1 + 1) = "
            + str(CONTACTS_PER_ROW)
            + " contacts per row and "
            + str(rows)
            + " * "
            + str(CONTACTS_PER_ROW)
            + " = "
            + str(caps["generation_calls_cap"])
            + " is the exact program maximum rather than a conservative safety bound. The "
            "sealed PLAN arm's realized rate on the whole roster was 5,425 contacts over "
            "1,080 rows (5.023 per row), which on these "
            + str(rows)
            + " rows would be about "
            + str(caps["expected_contacts"])
            + " contacts; every row here is an intent-error row and so likelier than "
            "average to spend its revision budget, which is why the ceiling and not the "
            "average is registered. At the sealed arm's own 3.6819 GPU hours per 5,425 "
            "contacts the whole ceiling costs about "
            + format(caps["expected_gpu_hours"], ".2f")
            + " GPU hours. The train-exemplars store supplies the Solver phase and adds "
            "prompt tokens, never contacts. The budget is RUN-CUMULATIVE across every "
            "attempt of this run id, which is what makes the resume-recovery clause safe."
        ),
        "target": caps["expected_contacts"],
    }
    plan = document["execution_plan"]
    plan["planned_gpu_hours"] = caps["gpu_hours_fit_inclusive"]
    plan["planned_model_calls"] = caps["generation_calls_cap"]
    plan["planned_speech_audio_seconds"] = caps["repeated_speech_audio_seconds_cap"]
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker", "campaign"]
    # HELD, and the requirements list is EMPTY ON PURPOSE -- see the module
    # docstring: the flip mints this cell's own first-phase supply (item E16) and
    # core.flight.repin appends the requirement, and that same function rewrites
    # EVERY preparation entry, so a second one would be clobbered.
    cell["readiness"] = {
        "reason": (
            "Cell CONV, the conversion probe of cell AGREE, registered before contact on "
            + args.date
            + " from the registered AGREE arm's own fragments by script (decision 58). "
            "Treatment only: the sealed PLAN arm "
            + SEALED_COMPARATOR
            + " holds these rows' comparator answers and is never re-flown. HELD: root "
            "mints the admission receipt and re-pins with scripts/flights/repin_cell.py "
            "--set-ready, which also mints this cell's own first-phase supply under its "
            "own run id (item E16) and appends the preparation requirement. The "
            "requirements list is empty by design and --allow-output-change must never be "
            "passed. Nothing here authorises a flight, a readiness flip or an admission "
            "entry."
        ),
        "requirements": [],
        "state": "held",
    }
    document["stage3_algorithm"] = {
        "id": "none",
        "operators_used": [],
        "note": STAGE3_ALGORITHM_NOTE,
    }
    wr(OUT_EXPERIMENT, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)

    derivation = json.loads(rd(ROSTER_DERIVATION))
    if derivation["schema"] != "saea-agreement-conversion-roster-v1":
        raise SystemExit("the roster derivation receipt is not the expected schema")
    if derivation["proof"]["differences"]:
        raise SystemExit("the roster derivation did not reproduce its receipt")
    roster = derivation["roster"]
    rows = int(roster["count"])
    if rows != len(roster["ids"]) or rows != len(set(roster["ids"])):
        raise SystemExit("the derived roster count and ids disagree")
    caps = budgets(rows, float(roster["audio_seconds_total"]))

    derive_baseline(rows, caps)
    derive_experiment(args, roster, caps)
    wr(
        OUT_CAMPAIGN,
        json.dumps(
            {
                "cells": [
                    {
                        "cell": "slurp-native-stage3-conv-fold-a-70-v1",
                        "experiment": "slurp-native-stage3-conv-fold-a-70-v1",
                    }
                ],
                "schema": "saea-campaign-plan-v1",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    print(
        json.dumps(
            {
                "written": [OUT_BASELINE, OUT_EXPERIMENT, OUT_CAMPAIGN],
                "rows": rows,
                "caps": caps,
                "split_identity_hash": roster["split_identity_hash"],
                "id_list_sha256": roster["id_list_sha256"],
                "parent_arm_run": ARM_RUN,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
