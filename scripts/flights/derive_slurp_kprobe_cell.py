#!/usr/bin/env python3
"""Derive cell KPROBE -- the centroid-key conversion probe (owner decision 145)
-- from the LOCKED PLAN baseline's own fragments (decision 58: script-derived
registrations).

WHAT THIS PROBE IS FOR. ``docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md``
found that a boundary key built as the intent's mean construction-TRAIN
utterance vector puts the gold intent inside the delivered eight on
71.2 / 64.7 / 66.8 % of the intent-wrong rows (Fold A / ROLL-1 / DEV-2000)
against 45.0 / 44.6 / 35.8 % for the written key, with the delivered body --
and so the token cost -- unchanged. That is DELIVERY. Whether the Solver then
answers correctly with the entry in front of it is the missing quantity, and
this probe measures it exactly as cell CONV measured the agreement term's: the
treatment flies ONLY on the Fold A rows whose gold entry the new key newly
delivers, against the already-sealed PLAN answers, and reads
P(correct | newly delivered) on intent per row.

ONE PIN. The derived baseline is the locked PLAN baseline
(``slurp-native-default-plan-lock-baseline-v1``) with exactly one knowledge
change: the intent-boundary Perception channel's ``facet_source`` pin moves
from the written-key file to the centroid-key file
``prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl``. ``k``
stays 8, ``fuse_coverage`` stays m 8 / c 1 / top_l 8, the rank weights stay
``w_cos`` 1.0 / ``w_prior`` 0.0 / ``w_agree`` 0.0, the store snapshot, release
and delivered bodies are the same bytes, and every other store, role, template,
normaliser, scorer, geometry and session is byte-identical. The only other
differences are per-flight bookkeeping: this cell's own FIT identities and cap,
no committed ``prepared_phase_supply`` (the flip mints this cell's own, item
E16), the centroid file's receipt appended to ``preparation_source_receipts``,
and ``what_this_is``. The registration writer proves that diff from the
composed configs and the unit tests re-prove it.

NO RE-PIN OF THE 211 COMMITTED CONFIGS (decision 145): only this probe's own
derived baseline pins the centroid file; the store rebuild waits on its m.

NO COMPARATOR IS FLOWN. The sealed PLAN arm
``SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`` already holds these rows' answers
and is intent-WRONG on every one of them (the bank's INTENT-UNCOVERED and
INTENT-COVERED classes both collapse to INTENT-WRONG in its own convention).

THE ROSTER IS SELECTED USING GOLD, OFFLINE, and the consequence is absolute:
NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its
population was chosen by the mechanism's own effect. See the committed
``roster-derivation-v1.json`` this script reads.

``prepared_phase_supply`` is absent and the readiness requirements list is
EMPTY on purpose: the flip mints this cell's own first-phase supply under its
own run id (item E16) and ``core.flight.repin._set_preparation_requirement``
appends the requirement; that function rewrites EVERY ``kind == "preparation"``
entry, so a second one would be silently clobbered. ``--allow-output-change``
must never be passed: this cell has no committed supply to compare against,
and a CHANGED output on a later re-pin means the knowledge channel moved.

This script writes CONFIG ONLY: one baseline, one experiment fragment and one
campaign plan. It performs no contact, writes no ledger row, mints no decision
receipt and flips nothing.

    python scripts/flights/derive_slurp_kprobe_cell.py --date 2026-09-27 \\
        --roster-derivation docs/readiness/<package>/roster-derivation-v1.json
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

PARENT_BASELINE = "configs/baseline/slurp-native-default-plan-lock-baseline-v1.json"
PARENT_EXPERIMENT = "configs/experiment/slurp-native-default-plan-lock-v1.json"
PARENT_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1"
PARENT_FIT_RUN = "SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1"
PARENT_GEN_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1"
PARENT_FIT_ATTEMPT = "attempt-slurp-native-default-plan-lock-train-fold-a-fit-v1"
PARENT_BASELINE_NAME = "slurp-native-default-plan-lock-baseline-v1"
PARENT_CELL = "slurp-native-default-plan-lock-v1"

WRITTEN_KEY_SHA = "76e8d16a067ebfc5d67a4ecef2966636310815b950a7d9790ec7c0136f01ecd2"
CENTROID_ARTIFACT = "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1"
CENTROID_RECEIPT_RELPATH = f"prepared/{CENTROID_ARTIFACT}/receipt.json"
DIAGNOSTIC = "docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md"

#: The program's own per-row contact ceiling (perception 1, solver 1,
#: reviewer 3, planner 1, max_revisions 1 -> 1 + 2 * (3 + 1 + 1) = 11) and the
#: PLAN family's own ratios, reproduced rather than re-invented -- cell CONV's
#: arithmetic exactly.
CONTACTS_PER_ROW = 11
FIT_MULTIPLIER = 4
NATIVE_CONTRACT_PER_ROW = 6
PARENT_REALIZED_PER_ROW = 5425 / 1080
PARENT_GPU_HOURS_PER_CONTACT = 3.6819 / 5425

ONE_FACTOR = (
    "The intent-boundary Perception channel's facet_source pin moves from the written-key "
    "file (prepared/SAEA-SLURP-INTENT-BOUNDARY-KEY-ENCODING-V1/facets.jsonl, one encoded "
    "one-line description per intent) to the centroid-key file (prepared/"
    + CENTROID_ARTIFACT
    + "/facets.jsonl, one unit-normalised mean construction-TRAIN utterance vector per "
    "intent from the R01-excluded pool, zero encoder contacts; the one intent with no pool "
    "member keeps its written key). Nothing else moves: k stays 8, fuse_coverage stays "
    "m 8 / c 1 / top_l 8, the rank weights stay w_cos 1.0 / w_prior 0.0 / w_agree 0.0, the "
    "intent-boundaries store snapshot, release and delivered bodies are the same bytes, and "
    "every other store, role, template, normaliser, scorer, geometry and session is the "
    "locked PLAN baseline's, byte for byte. The delivered block is unchanged, so the token "
    "cost is zero; only the retrieval key moves."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a "
    "one-pin retrieval-key change chosen by an offline diagnostic over sealed bytes and "
    "flown on a gold-selected subset to measure one conditional rate -- no rollout, no "
    "per-sample scoring, no credit assignment, no update operator and no evolving store. "
    "The family whose description covers a typed construction/consumption action of this "
    "shape is sealed-credit-system-policy-v1, and this cell is deliberately NOT labelled "
    "with it: that id's first instance is reserved for the composed system policy, and a "
    "single key file is not a policy search. A measurement of a factor is even less of one."
)


def names(rows: int) -> dict:
    tag = f"kprobe-fold-a-{rows}"
    return {
        "rows": rows,
        "cell": f"slurp-native-stage3-{tag}-v1",
        "baseline": f"slurp-native-stage3-{tag}-baseline-v1",
        "run": f"SAEA-SLURP-STAGE3-{tag.upper()}-V1",
        "fit_run": f"SAEA-SLURP-STAGE3-{tag.upper()}-FIT-V1",
        "gen_attempt": f"attempt-slurp-native-stage3-{tag}-generation-v1",
        "fit_attempt": f"attempt-slurp-native-stage3-{tag}-fit-v1",
        "decision_id": f"slurp-stage3-{tag}-admission-v1",
        "decision_relpath": f"coordination/slurp-stage3-{tag}-v1/root-admission-v1.json",
        "package": f"slurp-stage3-{tag}-v1",
        "out_baseline": f"configs/baseline/slurp-native-stage3-{tag}-baseline-v1.json",
        "out_experiment": f"configs/experiment/slurp-native-stage3-{tag}-v1.json",
        "out_campaign": f"configs/campaign/slurp-native-stage3-{tag}-v1.json",
    }


def substitutions(n: dict) -> list[tuple[str, str]]:
    return [
        (PARENT_FIT_RUN, n["fit_run"]),
        (PARENT_RUN, n["run"]),
        (PARENT_GEN_ATTEMPT, n["gen_attempt"]),
        (PARENT_FIT_ATTEMPT, n["fit_attempt"]),
        (PARENT_BASELINE_NAME, n["baseline"]),
        (PARENT_CELL, n["cell"]),
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


def substitute(text: str, n: dict) -> str:
    for old, new in substitutions(n):
        text = text.replace(old, new)
    return text


def budgets(rows: int, audio_seconds: float) -> dict:
    generation = rows * CONTACTS_PER_ROW
    return {
        "rows": rows,
        "audio_seconds": audio_seconds,
        "generation_calls_cap": generation,
        "fit_endpoint_calls_cap": generation * FIT_MULTIPLIER,
        "native_task_contract_calls_cap": rows * NATIVE_CONTRACT_PER_ROW,
        "repeated_speech_audio_seconds_cap": math.ceil(audio_seconds * CONTACTS_PER_ROW),
        "gpu_hours_fit_inclusive": 1.0,
        "expected_contacts": round(rows * PARENT_REALIZED_PER_ROW),
        "expected_gpu_hours": round(generation * PARENT_GPU_HOURS_PER_CONTACT, 4),
    }


def derive_baseline(n: dict, caps: dict, derivation: dict) -> None:
    raw = rd(PARENT_BASELINE)
    document = json.loads(substitute(raw, n))
    if "prepared_phase_supply" not in document:
        raise SystemExit("the locked PLAN baseline is expected to carry its own prepared_phase_supply pin")
    perception = document["knowledge_stores"]["intent-boundaries"]["phase_supply"]["perception"]
    if perception["rank_weights"] != {"w_cos": 1.0, "w_prior": 0.0, "w_agree": 0.0}:
        raise SystemExit("the locked PLAN boundary rank weights are not the flown identity weights")
    if perception["k"] != 8 or perception["tau"] != 0.0:
        raise SystemExit("the locked PLAN boundary k/tau are not the flown 8 / 0.0")
    if perception["fuse_coverage"] != {"m": 8, "c": 1, "top_l": 8}:
        raise SystemExit("the locked PLAN boundary fuse coverage is not the flown 8/1/8")
    if "agreement_source" in perception:
        raise SystemExit("the locked PLAN baseline declares an agreement_source; refusing")
    if perception["facet_source"]["sha256"] != WRITTEN_KEY_SHA:
        raise SystemExit("the locked PLAN boundary facet_source is not the flown written-key pin")
    pin = dict(derivation["treatment"]["facet_source_pin"])
    if pin["sha256"] != derivation["treatment"]["sha256"] or pin["kind"] != "sealed-vectors":
        raise SystemExit("the roster derivation's treatment pin is inconsistent")
    # THE ONE PIN.
    perception["facet_source"] = pin
    receipts = document["preparation_source_receipts"]
    receipt_pin = {
        "relpath": CENTROID_RECEIPT_RELPATH,
        "root": "data",
        "sha256": derivation["treatment"]["receipt_sha256"],
    }
    if any(r["relpath"] == CENTROID_RECEIPT_RELPATH for r in receipts):
        raise SystemExit("the parent already pins the centroid receipt")
    receipts.append(receipt_pin)
    # No committed prepared_phase_supply: the flip mints this cell's own (item E16).
    del document["prepared_phase_supply"]
    document["native_contact_fit"]["contact_cap"] = caps["fit_endpoint_calls_cap"]
    document["what_this_is"] = (
        "Cell KPROBE, the CENTROID-KEY CONVERSION PROBE (owner decision 145): the locked PLAN "
        "baseline with exactly one pin moved, flown on the "
        + str(n["rows"])
        + " TRAIN Fold A rows whose gold intent's boundary entry the centroid key newly "
        "delivers, to measure the quantity the boundary-key diagnostic could not -- "
        "P(correct | newly delivered), the conversion from delivery to correctness. The "
        "sealed PLAN arm "
        + PARENT_RUN
        + " already holds these rows' answers and is intent-WRONG on every one of them, so no "
        "comparator is flown and the contrast is per-row and offline. "
        + ONE_FACTOR
        + " Only this derived baseline pins the centroid file; the 211 committed configs that "
        "pin the written key are untouched (decision 145). THE ROSTER WAS SELECTED USING GOLD, "
        "OFFLINE: no pooled or roster-level claim may ever be made from this cell, because its "
        "population was chosen by the mechanism's own effect. Gold reaches no query, no key, "
        "no weight, no selector and no runtime."
    )
    wr(n["out_baseline"], dump_like(raw, document))


def derive_experiment(args: argparse.Namespace, n: dict, roster: dict, caps: dict, derivation_relpath: str) -> None:
    raw = rd(PARENT_EXPERIMENT)
    document = json.loads(substitute(raw, n))
    rows = n["rows"]
    document["date"] = args.date
    document["purpose"] = (
        "Cell KPROBE on the "
        + str(rows)
        + " TRAIN Fold A rows the centroid boundary key newly delivers: of the rows that "
        "receive their own gold intent's boundary entry only because the retrieval key is the "
        "intent's mean construction-TRAIN utterance vector instead of its written description, "
        "what proportion move from a wrong intent to the gold intent? That proportion IS the "
        "conversion from delivery to correctness -- the quantity the boundary-key diagnostic "
        "(" + DIAGNOSTIC + ") measured delivery for and could not measure. The deliverable is "
        "P(correct | newly delivered) with a binomial CI95 plus the reverse count and the "
        "four-way transition split; multiplying it by the registered per-row headroom of the "
        "class the gain lands on (12.04 / 130 = 0.092615 pp intent accuracy, primary under owner "
        "decision 133; 5.41 / 130 = 0.041615 pp SLU-F1 for the guard) gives the expectation a "
        "later 1,080-row construction cell would declare. "
        + ONE_FACTOR
        + " THE ROSTER WAS SELECTED USING GOLD, OFFLINE, which is legitimate for a CONDITIONAL "
        "estimate on a TRAIN roster and for nothing else: NO POOLED OR ROSTER-LEVEL CLAIM MAY "
        "EVER BE MADE FROM THIS CELL, because its population was chosen by the mechanism's own "
        "effect. This cell claims NO benefit and asks for NO admission: under the measurement "
        "instrument's rule 5 a batch of "
        + str(rows)
        + " rows is a form proof by size, never evidence of benefit. Development numbers only "
        "(owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a "
        "readiness flip or an admission entry."
    )
    document["population"] = {
        "count": rows,
        "dataset_fragment": roster["dataset_fragment"],
        "decision_population": (
            "The "
            + str(rows)
            + " rows of TRAIN Fold A that are intent-WRONG in the sealed PLAN arm (bad-case bank "
            "plan_class INTENT-UNCOVERED or INTENT-COVERED) and whose own gold intent's "
            "intent-boundary value id enters the "
            "fused Perception selection under the centroid key file and not under the written "
            "key file, both at the flown k 8 / fuse_coverage 8-1-8 / w_agree 0.0 through the "
            "production constructor -- derived from the pinned key file after the diagnostic's "
            "arithmetic, the file's production recall and the production constructor were each "
            "proven to agree (" + derivation_relpath + "). Every row is intent-WRONG in the "
            "sealed comparator, so the conditional rate is the whole estimate. SELECTED USING "
            "GOLD, OFFLINE: conditional estimate only, no pooled or roster-level claim, ever."
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
            "The locked PLAN role graph is unchanged: perception 1, solver 1, reviewer 3, "
            "planner 1, max_revisions 1, so rails.native_episode_config.load_native_episode_config "
            "resolves the program ceiling 1 + 2 * (3 + 1 + 1) = "
            + str(CONTACTS_PER_ROW)
            + " contacts per row and "
            + str(rows)
            + " * "
            + str(CONTACTS_PER_ROW)
            + " = "
            + str(caps["generation_calls_cap"])
            + " is the exact program maximum rather than a conservative safety bound. The sealed "
            "PLAN arm's realized rate on the whole roster was 5,425 contacts over 1,080 rows "
            "(5.023 per row), which on these "
            + str(rows)
            + " rows would be about "
            + str(caps["expected_contacts"])
            + " contacts (cell CONV realized 4.13 per row on the same kind of roster); every row "
            "here is an intent-error row and so likelier than average to spend its revision "
            "budget, which is why the ceiling and not the average is registered. At the sealed "
            "arm's own 3.6819 GPU hours per 5,425 contacts the whole ceiling costs about "
            + format(caps["expected_gpu_hours"], ".2f")
            + " GPU hours. The train-exemplars store supplies the Solver phase and adds prompt "
            "tokens, never contacts. The budget is RUN-CUMULATIVE across every attempt of this "
            "run id, which is what makes the resume-recovery clause safe."
        ),
        "target": caps["expected_contacts"],
    }
    plan = document["execution_plan"]
    plan["planned_gpu_hours"] = caps["gpu_hours_fit_inclusive"]
    plan["planned_model_calls"] = caps["generation_calls_cap"]
    plan["planned_speech_audio_seconds"] = caps["repeated_speech_audio_seconds_cap"]
    document["failure_policy"] = document["failure_policy"].replace(
        "closes cell PLAN", "closes this cell"
    )
    cell = document["cells"][0]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker", "campaign"]
    cell["readiness"] = {
        "reason": (
            "Cell KPROBE, the centroid-key conversion probe (owner decision 145), registered "
            "before contact on "
            + args.date
            + " from the locked PLAN baseline's own fragments by script (decision 58) with one "
            "pin moved. Treatment only: the sealed PLAN arm "
            + PARENT_RUN
            + " holds these rows' comparator answers and is never re-flown. HELD: root mints "
            "the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready, "
            "which also mints this cell's own first-phase supply under its own run id (item "
            "E16) and appends the preparation requirement. The requirements list is empty by "
            "design and --allow-output-change must never be passed. Nothing here authorises a "
            "flight, a readiness flip or an admission entry."
        ),
        "requirements": [],
        "state": "held",
    }
    document["stage3_algorithm"] = {
        "id": "none",
        "operators_used": [],
        "note": STAGE3_ALGORITHM_NOTE,
    }
    wr(n["out_experiment"], dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--roster-derivation", required=True, help="repo-relative path of roster-derivation-v1.json")
    args = parser.parse_args(argv)

    derivation = json.loads(rd(args.roster_derivation))
    if derivation["schema"] != "saea-centroid-key-conversion-roster-v1":
        raise SystemExit("the roster derivation receipt is not the expected schema")
    for proof in ("proof_a_diagnostic_reproduced", "proof_b_treatment_file_through_production_recall"):
        if derivation[proof]["differences"]:
            raise SystemExit(f"the roster derivation's {proof} recorded differences")
    if not derivation["proof_c_population_through_production_constructor"][
        "production_constructor_equals_production_recall_on_the_population"
    ]:
        raise SystemExit("the production constructor and the production recall disagree")
    roster = derivation["roster"]
    rows = int(roster["count"])
    if rows != len(roster["ids"]) or rows != len(set(roster["ids"])):
        raise SystemExit("the derived roster count and ids disagree")
    n = names(rows)
    caps = budgets(rows, float(roster["audio_seconds_total"]))

    derive_baseline(n, caps, derivation)
    derive_experiment(args, n, roster, caps, args.roster_derivation.replace("\\", "/"))
    wr(
        n["out_campaign"],
        json.dumps(
            {"cells": [{"cell": n["cell"], "experiment": n["cell"]}], "schema": "saea-campaign-plan-v1"},
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    print(json.dumps({"names": n, "caps": caps, "split_identity_hash": roster["split_identity_hash"],
                      "id_list_sha256": roster["id_list_sha256"], "parent_run": PARENT_RUN},
                     indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
