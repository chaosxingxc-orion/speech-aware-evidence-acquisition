#!/usr/bin/env python3
"""Derive cell W4-SV -- the W4 slot conventions re-registered as the FIRST cell of the same-flight
supply-variant instrument (owner decision 172; coordinator verdict on W4 in
docs/results/2026-09-28-slurp-w4-fold-a-read.md) -- from the RETAINED AGREE arm fragments
(decision 58: script-derived registrations).

THE BASE is the AGREE arm's bytes with four declarations added and nothing else moved:

1. ``policy`` -> ``phase-native-candidates-review-revise-variants3first-v1`` -- the UNCITED copy of the
   AGREE program with ``max_contacts`` 13 = 11 + (K - 1) at K = 3 arms under ``arm_visits: "first"``
   (rails/native_episode_config.py; the loader asserts the program ceiling equals the graph ceiling).
   The Solver phase keeps ``response_format_id`` null: the AGREE answer contract is unchanged.
2. ``knowledge_stores.slot-contracts.alternates`` -> ONE alternate: the ``slot-contracts-w4-v1``
   release and snapshot exactly as cell W4 registered them (hash-pinned; the release-swap route of the
   coordinator amendment 2026-09-28). The PRIMARY pins stay ``slot-contracts-v2``: every contact that
   is not arm B's first Solver contact renders the AGREE arm's cards.
3. ``native_episode.roles.solver.supply_variants`` -> three arms at the FIRST Solver visit only:
   ``b-w4`` (``release_swap`` to the W4 release), ``t-twin`` (``replicate_of: a-agree``), and the
   delivering ``a-agree`` (no overrides, last). Every revisit contacts the delivering arm alone.
   ``fit_estimate`` is the measured envelope of ``measure_w4sv_fit.py`` (pinned by sha256 below).
4. The two W4 release receipts (completion, release) appended to ``preparation_source_receipts``, as
   cell W4 carried them, so the alternate pin carries its provenance.

Bookkeeping moves too: run/attempt ids, the FIT identity and its contact cap (rows x 13 x 4), the
budget caps at the 13-contact ceiling, prose. ``prepared_phase_supply`` is dropped so the flip mints
this cell's own first-phase supply under its own run id (item E16); neither the alternate nor the arm
group is an input to the Perception boundary supply, so the minted supply must carry the AGREE arm's
output digest ``eab5c61e...`` (the smoke's: ``308601c5...``).

TWO CELLS: the arm on TRAIN Fold A 1,080 and its four-row form smoke, plus the one-cell campaign plan.
No separate A/A is derived: the twin arm ``t-twin`` is the read's in-flight null.

This script writes CONFIG ONLY. It performs no contact, writes no ledger row, mints no receipt and
flips nothing.

    python scripts/flights/w4sv/derive_slurp_w4sv_cells.py --date 2026-09-28 --data-root "$SPEECHRL_DATA_DIR"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

AGREE_ARM_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json"
AGREE_SMOKE_BASELINE = "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json"
AGREE_ARM_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json"
AGREE_SMOKE_EXPERIMENT = "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json"
DATASET = "configs/dataset/slurp-speech-native-evo-fold-a-1080.json"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
W4_RUN = "SAEA-SLURP-STAGE3-W4-FOLD-A-V1"

BASE_POLICY = "phase-native-candidates-review-revise-v1"
POLICY = "phase-native-candidates-review-revise-variants3first-v1"
BASE_CEILING, CEILING = 11, 13
FIT_ENDPOINTS_PER_CONTACT = 4  # the AGREE arithmetic: 47,520 = 1,080 x 11 x 4

V2_STORE = {
    "release": {"relpath": "knowledge/slurp/semantic/slot-contracts-v2/release.json",
                "sha256": "f8e42d4ff1b220f45b26397340149566544cf5b13d7453fbc46a2b5c3400d11b"},
    "snapshot": {"relpath": "knowledge/slurp/semantic/slot-contracts-v2/snapshot.json",
                 "sha256": "d5992bd12687cbd0204c14fc4e29f987697b8751321d524d7707229032f5bdec"},
}
W4_ALTERNATE = {
    "release": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json",
                "sha256": "c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0"},
    "snapshot": {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/snapshot.json",
                 "sha256": "51d634cfcb398038377feca89d2783f59a705546390839e7cf4dd7d15ad3b9d6"},
}
W4_RECEIPTS = [
    {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/completion.json", "root": "data",
     "sha256": "1e71784e1af305dee8ead126449d44081fc3740e32d912a131625ece3897d834"},
    {"relpath": "knowledge/slurp/semantic/slot-contracts-w4-v1/release.json", "root": "data",
     "sha256": "c7bdeee6e0859fbba6bce79cd3d42347a5b74770f7564094e3d3a0edfe003fb0"},
]
FIT_MEASURE = {"relpath": "analysis/SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1/fit-measure-v1.json",
               "sha256": "7ee35419838b9fe708730d982407d5d5f37768930cf5a184bd9a7841fcbb18a0"}
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl"
ARM_IDS = {"b": "b-w4", "t": "t-twin", "a": "a-agree"}

ONE_CHANGE = (
    "The base is the retained AGREE arm's bytes; the ONLY variation is arm b-w4's FIRST Solver request, which "
    "renders the slot-contract cards from the slot-contracts-w4-v1 release (TRAIN-mined value vocabulary, "
    "annotation scope and span-extent conventions appended to 19 of the v2 cards; release sha256 "
    + W4_ALTERNATE["release"]["sha256"] + ", snapshot content " + W4_ALTERNATE["snapshot"]["sha256"]
    + ") through the release-swap route, declared as the ONE alternate of knowledge_stores.slot-contracts. "
    "Arm a-agree (delivering, last, no overrides) and its twin t-twin (replicate_of a-agree) render the AGREE "
    "arm's v2 cards; arms fan out at the first Solver visit only (arm_visits first), every revisit contacts the "
    "delivering arm alone, and no arm output reaches the Reviewer, the Planner or the delivered answer. The "
    "program moves to its uncited 13-contact copy (phase-native-candidates-review-revise-variants3first-v1); "
    "roster, geometry, session, Perception, the agreement term (w_agree 1.0, k 60, fuse 8-1-8) and its sealed "
    "table, the boundary and exemplar stores, every template, the deliver normaliser and the scorers are the "
    "AGREE arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the first real read of the "
    "same-flight supply-variant INSTRUMENT (owner decision 172) -- one knowledge-content alternative (the W4 slot "
    "conventions, mined model-free from TRAIN annotations outside Fold A) offered to the Solver as a sealed, "
    "never-delivered arm beside the delivering arm and its twin -- with no rollout-driven selection, no per-sample "
    "credit, no update operator and no evolving store. It is not a VAR-2 mechanism: the delivered answer and every "
    "downstream node depend on the delivering arm alone."
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
    s = "-smoke-4" if smoke else ""
    S = "-SMOKE-4" if smoke else ""
    return [
        (f"SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A{S}-FIT-V1", f"SAEA-SLURP-STAGE3-W4SV-FOLD-A{S}-FIT-V1"),
        (f"SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A{S}-V1", f"SAEA-SLURP-STAGE3-W4SV-FOLD-A{S}-V1"),
        (f"attempt-slurp-native-stage3-agree-w1-fold-a{s}-generation-v1", f"attempt-slurp-native-stage3-w4sv-fold-a{s}-generation-v1"),
        (f"attempt-slurp-native-stage3-agree-w1-fold-a{s}-fit-v1", f"attempt-slurp-native-stage3-w4sv-fold-a{s}-fit-v1"),
        (f"slurp-native-stage3-agree-w1-fold-a{s}-baseline-v1", f"slurp-native-stage3-w4sv-fold-a{s}-baseline-v1"),
        (f"saea-slurp-native-stage3-agree-w1-fold-a{s}-v1", f"saea-slurp-native-stage3-w4sv-fold-a{s}-v1"),
        (f"slurp-native-stage3-agree-w1-fold-a{s}-v1", f"slurp-native-stage3-w4sv-fold-a{s}-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def fit_measure(data_root: str) -> dict:
    path = os.path.join(data_root, FIT_MEASURE["relpath"])
    raw = io.open(path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != FIT_MEASURE["sha256"]:
        raise SystemExit(f"{FIT_MEASURE['relpath']} does not hash to its pin")
    return json.loads(raw.decode("utf-8"))


def supply_variants_block(measure: dict) -> dict:
    bound = int(measure["max_supplied_items"])
    return {
        "arm_visits": "first",
        "arms": [
            {"arm_id": ARM_IDS["b"], "max_supplied_items": bound,
             "release_swap": {"store_id": "slot-contracts", "release": W4_ALTERNATE["release"]["relpath"]}},
            {"arm_id": ARM_IDS["t"], "max_supplied_items": bound, "replicate_of": ARM_IDS["a"]},
            {"arm_id": ARM_IDS["a"], "deliver": True, "max_supplied_items": bound},
        ],
        "fit_estimate": dict(measure["fit_estimate"]),
    }


def audio_seconds(sample_ids: list[str]) -> float:
    items = {row["sample_id"]: float(row["audio_seconds"]) for row in json.loads(rd(DATASET))["items"]}
    return sum(items[s] for s in sample_ids)


def derive_baseline(parent: str, out: str, pairs, measure: dict, rows: int, *, what_this_is: str) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    if document["policy"] != BASE_POLICY:
        raise SystemExit(f"the AGREE parent flies {document['policy']!r}, not {BASE_POLICY!r}; refusing")
    document["policy"] = POLICY  # 1
    store = document["knowledge_stores"]["slot-contracts"]
    if {"release": store["release"], "snapshot": store["snapshot"]} != V2_STORE or "alternates" in store:
        raise SystemExit("the AGREE parent does not pin slot-contracts-v2 with no alternates; refusing")
    store["alternates"] = [json.loads(json.dumps(W4_ALTERNATE))]  # 2
    solver = document["native_episode"]["roles"]["solver"]
    if set(solver) != {"max_iterations", "phase_id"} or solver["max_iterations"] != 1:
        raise SystemExit(f"the AGREE Solver role is not the plain one-iteration role: {sorted(solver)}")
    solver["supply_variants"] = supply_variants_block(measure)  # 3
    receipts = list(document["preparation_source_receipts"])
    if any(r["relpath"] in {x["relpath"] for x in W4_RECEIPTS} for r in receipts):
        raise SystemExit("the parent already carries a W4 receipt")
    document["preparation_source_receipts"] = receipts + [dict(r) for r in W4_RECEIPTS]  # 4
    fit = document["native_contact_fit"]
    if fit["contact_cap"] != rows * BASE_CEILING * FIT_ENDPOINTS_PER_CONTACT:
        raise SystemExit(f"unexpected parent FIT contact cap {fit['contact_cap']}")
    fit["contact_cap"] = rows * CEILING * FIT_ENDPOINTS_PER_CONTACT
    document["what_this_is"] = what_this_is
    for key in parent_doc:
        if key in ("knowledge_stores", "preparation_source_receipts", "prepared_phase_supply", "what_this_is",
                   "native_contact_fit", "policy", "native_episode"):
            continue
        if json.dumps(parent_doc[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the declared four")
    parent_episode = json.loads(json.dumps(parent_doc["native_episode"]))
    episode = json.loads(json.dumps(document["native_episode"]))
    episode["roles"]["solver"].pop("supply_variants")
    if parent_episode != episode:
        raise SystemExit("native_episode moved beyond roles.solver.supply_variants")
    wr(out, dump_like(raw, document))


def derive_experiment(parent: str, out: str, pairs, args, *, rows: int, audio: float, purpose: str,
                      readiness_reason: str, campaign: bool, failure_policy: str | None = None) -> dict:
    raw = rd(parent)
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    if failure_policy is not None:
        document["failure_policy"] = failure_policy
    else:
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    calls = rows * CEILING
    audio_cap = int(math.ceil(CEILING * audio))
    fit_cap = rows * CEILING * FIT_ENDPOINTS_PER_CONTACT
    budget = document["family_budget"]
    if budget["generation_calls_cap"] != rows * BASE_CEILING:
        raise SystemExit(f"unexpected parent generation cap {budget['generation_calls_cap']}")
    budget.update({"generation_calls_cap": calls, "fit_endpoint_calls_cap": fit_cap,
                   "repeated_speech_audio_seconds_cap": audio_cap})
    plan = document["execution_plan"]
    plan.update({"planned_model_calls": calls, "planned_speech_audio_seconds": audio_cap})
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": calls,
            "definition": (
                "The AGREE role graph (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1) with a "
                "three-arm Solver supply-variant group fanned out at the FIRST Solver visit only: "
                "rails.native_episode_config.load_native_episode_config resolves the program ceiling "
                f"{BASE_CEILING} + (3 - 1) = {CEILING} contacts per row, the "
                f"phase-native-candidates-review-revise-variants3first-v1 program's max_contacts, and {rows:,} x "
                f"{CEILING} = {calls:,} is the exact program maximum. The retained AGREE bytes realised 4,393 "
                "contacts on this roster (the shared wave A/A), and the arm group adds exactly 2 Solver contacts "
                f"per row ({2 * rows:,}), so the expected spend is about {4393 + 2 * rows:,} contacts. The speech cap "
                f"is {CEILING} x the roster's {audio:.3f} audio seconds, rounded up. The budget is RUN-CUMULATIVE "
                "across every attempt of this run id."
            ),
            "target": 4393 + 2 * rows,
        }
    cell = document["cells"][0]
    agreement = [r for r in cell["readiness"]["requirements"]
                 if r.get("kind") == "preparation" and r.get("relpath") == AGREEMENT_RELPATH]
    if len(agreement) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table requirement")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement, "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out, dump_like(raw, document))
    return {"calls": calls, "audio_cap": audio_cap, "fit_cap": fit_cap, "audio_seconds": audio}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR"))
    args = parser.parse_args(argv)
    if not args.data_root:
        raise SystemExit("--data-root (or SPEECHRL_DATA_DIR) is required: the fit measurement is pinned there")
    for pin in (W4_ALTERNATE["release"], *W4_RECEIPTS):
        path = os.path.join(args.data_root, pin["relpath"])
        if hashlib.sha256(io.open(path, "rb").read()).hexdigest() != pin["sha256"]:
            raise SystemExit(f"{pin['relpath']} does not hash to its pin")
    measure = fit_measure(args.data_root)

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(through scripts/flights/w4sv/w4sv_flip.sh), which also mints this cell's own first-phase supply under its "
        "own run id (item E16); --allow-output-change must never be passed, and the minted supply must reproduce "
        "the AGREE arm's own first-phase output digest (neither the alternate nor the arm group is an input to it). "
        "Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    written, budgets = [], {}
    arm_pairs = substitutions(smoke=False)
    arm_ids = json.loads(rd(AGREE_ARM_EXPERIMENT))["populations"][0]["ids"]
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-w4sv-fold-a-baseline-v1.json",
                    arm_pairs, measure, len(arm_ids),
                    what_this_is="Cell W4-SV (owner decision 172; the coordinator's W4 verdict): the first real cell of "
                                 "the same-flight supply-variant instrument, reading the W4 slot conventions as a "
                                 "Solver-local column beside the AGREE Solver supply and its twin. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w4sv-fold-a-baseline-v1.json")
    budgets["arm"] = derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-w4sv-fold-a-v1.json", arm_pairs, args,
        rows=len(arm_ids), audio=audio_seconds(arm_ids),
        purpose=(
            "Cell W4-SV on TRAIN Fold A 1,080 (owner decision 172; the coordinator re-registered W4 as the first "
            "cell of the same-flight supply-variant instrument): at the FIRST Solver visit, does the Solver's "
            "official pooled SLU-F1 (primary; intent accuracy the guard) move when its slot-contract cards come from "
            "the slot-contracts-w4-v1 release (arm b-w4) instead of the AGREE arm's slot-contracts-v2 (arm a-agree, "
            "delivering), read as paired first-visit columns b-w4 vs a-agree against the in-flight twin t-twin vs "
            "a-agree? " + ONE_CHANGE + " A Solver-local first-visit column is a DIFFERENT estimand from cell W4's "
            "cross-flight full-system read, whose cards also reached the Reviewer and Planner. The claim ceiling is "
            "'nominated' (Q6 ruling). Development numbers only (owner decisions 28 and 86); never a test claim. "
            "Nothing here authorises a flight, a readiness flip or an admission entry."
        ),
        readiness_reason=(
            "Cell W4-SV registered before contact on " + args.date + " from the retained AGREE arm fragments by script "
            "(decision 58) under owner decision 172 and the release-swap amendment (coordinator, 2026-09-28). The null "
            "is the in-flight twin arm t-twin; there is no separate A/A and no comparator is re-flown." + held
        ),
        campaign=True,
    )
    written.append("configs/experiment/slurp-native-stage3-w4sv-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    smoke_ids = json.loads(rd(AGREE_SMOKE_EXPERIMENT))["populations"][0]["ids"]
    derive_baseline(AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-w4sv-fold-a-smoke-4-baseline-v1.json",
                    smoke_pairs, measure, len(smoke_ids),
                    what_this_is="Four-row structural form smoke of cell W4-SV: the same base and arm group on the first "
                                 "four rows of the unchanged TRAIN Fold A roster. " + ONE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-w4sv-fold-a-smoke-4-baseline-v1.json")
    budgets["smoke"] = derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-w4sv-fold-a-smoke-4-v1.json", smoke_pairs, args,
        rows=len(smoke_ids), audio=audio_seconds(smoke_ids),
        purpose=(
            "Four-row structural form smoke of cell W4-SV: that the slot-contracts-w4-v1 alternate loads by its pins "
            "when arm b-w4 selects it, that the three arms fan out at the first Solver visit only, that the twin's "
            "wire bytes equal the delivering arm's, that every request fits under the 13-contact ceiling and that the "
            "episode completes and seals (I7, I7n, I7v). It is scored by no one and read by no one: four rows can "
            "never be evidence of benefit or of harm. " + ONE_CHANGE
        ),
        readiness_reason=(
            "Four-row form smoke of cell W4-SV, registered before contact on " + args.date + " from the AGREE smoke "
            "fragments by script (decision 58). Structural form proof only: no score, no read, no claim." + held
        ),
        campaign=False,
        failure_policy=(
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell W4-SV and the arm does not open. The resume-recovery clause of owner decision "
            "22 applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        ),
    )
    written.append("configs/experiment/slurp-native-stage3-w4sv-fold-a-smoke-4-v1.json")
    campaign = {"cells": [{"cell": "slurp-native-stage3-w4sv-fold-a-v1",
                           "experiment": "slurp-native-stage3-w4sv-fold-a-v1"}],
                "schema": "saea-campaign-plan-v1"}
    wr("configs/campaign/slurp-native-stage3-w4sv-fold-a-v1.json",
       json.dumps(campaign, indent=2, sort_keys=True) + "\n")
    written.append("configs/campaign/slurp-native-stage3-w4sv-fold-a-v1.json")
    print(json.dumps({"written": written, "budgets": budgets,
                      "supply_variants": supply_variants_block(measure)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
