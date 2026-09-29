#!/usr/bin/env python3
"""Derive cell W-SV-1 -- the FIRST real same-flight supply-variant cell (owner decision 172;
docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-design.md, including the
coordinator amendment of 2026-09-28) -- from the RETAINED AGREE arm fragments (decision 58:
script-derived registrations).

THE BASE CHANGES, AND NOTHING ELSE MOVES.

1. ``policy``: ``phase-native-candidates-review-revise-v1`` (ceiling 11) ->
   ``phase-native-candidates-review-revise-variants3first-v1`` (ceiling 13, UNCITED: the Solver
   phase keeps ``response_format_id: null``). The two fragments differ ONLY in ``program_id`` and
   ``max_contacts`` (the loader asserts ``max_contacts`` equals the bounded graph ceiling, which
   a three-arm group under ``arm_visits: "first"`` raises by K - 1 = 2). Verified here by a
   leaf-by-leaf diff of the two fragment files; any other difference refuses.
2. ``native_episode.roles.solver.supply_variants``: three arms at the Solver under
   ``arm_visits: "first"``, delivering arm LAST and override-free --
   ``b-exk30`` (B: the train-exemplar Solver supply re-capped k 20 -> 30 with
   ``fuse_coverage`` m / c / top_l 20 -> 30, the VAR-1 ``exk30`` knob path and values,
   ``scripts/flights/batch/var1_repin_exk30.sh`` / ``configs/baseline/slurp-native-stage3-var1-
   ex-k30-r01c-baseline-v1.json``), ``t-twin`` (T: ``replicate_of: a-base``, no overrides, the
   delivering arm's greedy repeat in the same contact batch) and ``a-base`` (A: ``deliver: true``,
   no overrides, the AGREE arm's own supply at k 20). ``fit_estimate`` and every
   ``max_supplied_items`` are MEASURED on the sealed AGREE arm by
   ``scripts/flights/wsv1/wsv1_fit_measure.py`` (read from its output file and hash-checked).

Bookkeeping that follows from (1)/(2): the run / attempt / FIT ids, ``native_contact_fit.
contact_cap`` (rows x 13 x 4, the AGREE arithmetic at the new ceiling), the family budget and
execution plan (rows x 13 generation contacts, rows x 13 x audio speech seconds, GPU hours
scaled by 13 / 11), ``what_this_is``/``purpose``/readiness prose, and ``prepared_phase_supply``
DROPPED so the flip mints this cell's own first-phase supply under its own run id (item E16); the
minted output must carry the AGREE arm's / smoke's digest (the Perception supply is upstream of
the Solver arm group and of the program id).

TWO CELLS: the arm on TRAIN Fold A 1,080 and its four-row form smoke, plus the arm's one-cell
campaign plan. No A/A is derived: the in-flight twin arm T is the read's own null (Q3 ruling).

This script writes CONFIG ONLY. It performs no contact, writes no ledger row, mints no receipt and
flips nothing.

    python scripts/flights/wsv1/derive_slurp_wsv1_cells.py --date 2026-09-28 --data-root "$SPEECHRL_DATA_DIR"
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
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
DATASET_FRAGMENT = "configs/dataset/slurp-speech-native-evo-fold-a-1080.json"

BASE_PROGRAM = "phase-native-candidates-review-revise-v1"
NEW_PROGRAM = "phase-native-candidates-review-revise-variants3first-v1"
BASE_CEILING, NEW_CEILING = 11, 13
FIT_ENDPOINTS_PER_CONTACT = 4  # the AGREE arithmetic: contact_cap = rows x ceiling x 4

FIT_MEASURE = "analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-FIT-MEASURE-V1/fit-measure-v1.json"
FIT_MEASURE_SHA256 = "f992545afd275964d190b57c37a36886a7cef53fe1ecd298fe4d305ce0b8fe9f"

EXK30_PREFIX = "knowledge_stores.train-exemplars.phase_supply.solver."
EXK30_OVERRIDES = {
    EXK30_PREFIX + "fuse_coverage.c": 30,
    EXK30_PREFIX + "fuse_coverage.m": 30,
    EXK30_PREFIX + "fuse_coverage.top_l": 30,
    EXK30_PREFIX + "k": 30,
}
VAR1_EXK30_BASELINE = "configs/baseline/slurp-native-stage3-var1-ex-k30-r01c-baseline-v1.json"
ARM_A, ARM_B, ARM_T = "a-base", "b-exk30", "t-twin"

THE_CHANGE = (
    "THE BASE CHANGE (the only one besides the supply_variants block): policy " + BASE_PROGRAM + " (ceiling 11) -> "
    + NEW_PROGRAM + " (ceiling 13, UNCITED -- the Solver keeps response_format_id null; the two program fragments "
    "differ only in program_id and max_contacts). THE VARIANTS BLOCK: native_episode.roles.solver.supply_variants "
    "with arm_visits 'first' and three arms, delivering arm last -- " + ARM_B + " (B: train-exemplar Solver supply "
    "k 20 -> 30 with fuse_coverage m/c/top_l 20 -> 30, the VAR-1 exk30 knob path and values), " + ARM_T + " (T: "
    "replicate_of " + ARM_A + ", the in-flight twin, no overrides) and " + ARM_A + " (A: deliver true, no overrides, "
    "the AGREE arm's own k-20 supply; its request bytes are the AGREE arm's EXCEPT the two program-identity fields "
    "the switch moves -- the program id inside quoted prior contact ids and remaining_model_contacts, +2 -- proven by "
    "scripts/flights/wsv1/wsv1_arm_a_proof.py). Arms fan out only at the first "
    "Solver visit; revisits contact A alone; B and T never reach the Reviewer, the Planner or the delivered text. "
    "Nothing else moves: roster, geometry, session, role graph, max_revisions 1, the agreement term and its sealed "
    "table, every knowledge store and pin, every template, the deliver normaliser and the scorers are the AGREE "
    "arm's, byte for byte."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is the first real cell of the "
    "same-flight supply-variant INSTRUMENT (owner decision 172) -- one knob-tail arm (the VAR-1 exk30 construction) "
    "and an in-flight twin read as Solver-local columns against the delivering arm -- with no rollout pool, no "
    "per-sample credit, no update operator and no evolving store. It is deliberately NOT labelled "
    "sealed-credit-system-policy-v1 (the inner-loop use (b) of the instrument is a separate, later cell) and it is "
    "not a VAR-2 mechanism: no delivered answer or downstream node depends on more than the delivering arm."
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


def flatten(node, prefix: str = "") -> dict:
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}{key}."))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.update(flatten(value, f"{prefix}[{index}]."))
    else:
        out[prefix[:-1]] = node
    return out


def check_program_fragments() -> None:
    base = flatten(json.loads(rd(f"configs/policy/{BASE_PROGRAM}.json")))
    new = flatten(json.loads(rd(f"configs/policy/{NEW_PROGRAM}.json")))
    moved = sorted(k for k in set(base) | set(new) if base.get(k, "<absent>") != new.get(k, "<absent>"))
    if moved != ["max_contacts", "program_id"]:
        raise SystemExit(f"{NEW_PROGRAM} differs from {BASE_PROGRAM} beyond program_id/max_contacts: {moved}")
    if (base["max_contacts"], new["max_contacts"]) != (BASE_CEILING, NEW_CEILING):
        raise SystemExit("unexpected program ceilings")


def check_exk30_path() -> None:
    """The B arm's four overrides are the VAR-1 exk30 cell's own moved knob leaves and values."""
    var1 = json.loads(rd(VAR1_EXK30_BASELINE))["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]
    got = {EXK30_PREFIX + "k": var1["k"], **{EXK30_PREFIX + "fuse_coverage." + t: var1["fuse_coverage"][t]
                                             for t in ("c", "m", "top_l")}}
    if got != EXK30_OVERRIDES:
        raise SystemExit(f"the VAR-1 exk30 construction is not {EXK30_OVERRIDES}: {got}")


def supply_variants_block(measure: dict) -> dict:
    bounds = measure["max_supplied_items"]
    return {
        "arm_visits": "first",
        "arms": [
            {"arm_id": ARM_B, "max_supplied_items": bounds["b_exk30"], "overrides": dict(EXK30_OVERRIDES)},
            {"arm_id": ARM_T, "max_supplied_items": bounds["a_and_twin"], "replicate_of": ARM_A},
            {"arm_id": ARM_A, "deliver": True, "max_supplied_items": bounds["a_and_twin"]},
        ],
        "fit_estimate": dict(measure["fit_estimate"]),
    }


def substitutions(*, smoke: bool) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the AGREE fragment to this cell's own."""
    if smoke:
        return [
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-FIT-V1", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-SMOKE-4-FIT-V1"),
            ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-SMOKE-4-V1", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-SMOKE-4-V1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-generation-v1", "attempt-slurp-native-stage3-wsv1-fold-a-smoke-4-generation-v1"),
            ("attempt-slurp-native-stage3-agree-w1-fold-a-smoke-4-fit-v1", "attempt-slurp-native-stage3-wsv1-fold-a-smoke-4-fit-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1", "slurp-native-stage3-wsv1-fold-a-smoke-4-baseline-v1"),
            ("slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "slurp-native-stage3-wsv1-fold-a-smoke-4-v1"),
            ("saea-slurp-native-stage3-agree-w1-fold-a-smoke-4-v1", "saea-slurp-native-stage3-wsv1-fold-a-smoke-4-v1"),
        ]
    return [
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-FIT-V1"),
        ("SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1", "SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1", "attempt-slurp-native-stage3-wsv1-fold-a-generation-v1"),
        ("attempt-slurp-native-stage3-agree-w1-fold-a-fit-v1", "attempt-slurp-native-stage3-wsv1-fold-a-fit-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-baseline-v1", "slurp-native-stage3-wsv1-fold-a-baseline-v1"),
        ("slurp-native-stage3-agree-w1-fold-a-v1", "slurp-native-stage3-wsv1-fold-a-v1"),
        ("saea-slurp-native-stage3-agree-w1-fold-a-v1", "saea-slurp-native-stage3-wsv1-fold-a-v1"),
    ]


def substitute(text: str, pairs: list[tuple[str, str]]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def derive_baseline(parent: str, out: str, pairs, *, block: dict, rows: int, what_this_is: str) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    if document.get("policy") != BASE_PROGRAM:
        raise SystemExit(f"the AGREE parent's policy is {document.get('policy')!r}, not {BASE_PROGRAM}")
    document["policy"] = NEW_PROGRAM  # THE ONE BASE CHANGE
    solver = document["native_episode"]["roles"]["solver"]
    if "supply_variants" in solver or solver.get("phase_id") != "solver":
        raise SystemExit("the AGREE parent's Solver role already carries supply_variants")
    solver["supply_variants"] = block  # THE VARIANTS BLOCK
    document["native_contact_fit"]["contact_cap"] = rows * NEW_CEILING * FIT_ENDPOINTS_PER_CONTACT
    if parent_doc["native_contact_fit"]["contact_cap"] != rows * BASE_CEILING * FIT_ENDPOINTS_PER_CONTACT:
        raise SystemExit("the AGREE parent's FIT cap is not rows x 11 x 4")
    document["what_this_is"] = what_this_is
    for key in parent_doc:
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit"):
            continue
        if json.dumps(parent_doc[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the registered change")
    parent_episode = json.loads(json.dumps(parent_doc["native_episode"]))
    episode = json.loads(json.dumps(document["native_episode"]))
    episode["roles"]["solver"].pop("supply_variants")
    if parent_episode != episode:
        raise SystemExit("native_episode moved beyond the Solver supply_variants block")
    wr(out, dump_like(raw, document))


def audio_seconds(ids: list[str] | None) -> float:
    items = json.loads(rd(DATASET_FRAGMENT))["items"]
    if ids is None:
        return sum(float(i["audio_seconds"]) for i in items)
    by_id = {i["sample_id"]: float(i["audio_seconds"]) for i in items}
    return sum(by_id[s] for s in ids)


def budgets(rows: int, audio: float, parent: dict) -> tuple[dict, dict]:
    fam = dict(parent["family_budget"])
    if fam["generation_calls_cap"] != rows * BASE_CEILING:
        raise SystemExit("the AGREE parent's generation cap is not rows x 11")
    if fam["repeated_speech_audio_seconds_cap"] != math.ceil(audio * BASE_CEILING - 1e-9):
        raise SystemExit("the AGREE parent's speech cap is not ceil(audio x 11)")
    gpu = round(fam["gpu_hours_fit_inclusive"] * NEW_CEILING / BASE_CEILING, 1) if rows > 4 else fam["gpu_hours_fit_inclusive"]
    fam.update({
        "generation_calls_cap": rows * NEW_CEILING,
        "fit_endpoint_calls_cap": rows * NEW_CEILING * FIT_ENDPOINTS_PER_CONTACT,
        "repeated_speech_audio_seconds_cap": math.ceil(audio * NEW_CEILING - 1e-9),
        "native_task_contract_calls_cap": fam["native_task_contract_calls_cap"] + rows * (NEW_CEILING - BASE_CEILING),
        "gpu_hours_fit_inclusive": gpu,
    })
    plan = dict(parent["execution_plan"])
    plan.update({"planned_model_calls": fam["generation_calls_cap"], "planned_gpu_hours": gpu,
                 "planned_speech_audio_seconds": fam["repeated_speech_audio_seconds_cap"]})
    return fam, plan


def derive_experiment(parent: str, out: str, pairs, args, *, purpose: str, readiness_reason: str,
                      campaign: bool, audio: float, failure_policy: str | None = None) -> None:
    raw = rd(parent)
    parent_doc = json.loads(raw)
    document = json.loads(substitute(raw, pairs))
    rows = int(document["population"]["count"])
    document["date"] = args.date
    document["purpose"] = purpose
    if failure_policy is not None:
        document["failure_policy"] = failure_policy
    else:
        document["failure_policy"] = document["failure_policy"].replace(
            "closes cell PLAN", "closes this cell").replace("stops cell PLAN", "stops this cell")
    family, plan = budgets(rows, audio, parent_doc)
    document["family_budget"] = family
    document["execution_plan"] = plan
    if "generation_budget" in document:
        target = document["generation_budget"].get("target")
        document["generation_budget"] = {
            "cap": rows * NEW_CEILING,
            "definition": (
                f"The AGREE role graph (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1) under program "
                f"{NEW_PROGRAM}: a three-arm Solver supply_variants group with arm_visits 'first' raises the bounded "
                f"graph ceiling by K - 1 = 2 to 13 contacts per row (rails.native_episode_config, item E42b), so "
                f"{rows:,} x 13 = {rows * NEW_CEILING:,} is the exact program maximum. The sealed AGREE arm realised "
                "4.060 contacts per row; the two extra first-visit Solver arm contacts (B and the twin T) add exactly "
                "2 per row, so the expected spend is about 6.06 x rows contacts. The budget is RUN-CUMULATIVE across "
                "every attempt of this run id."
            ),
            "target": (round(4.060 * rows) + 2 * rows) if isinstance(target, int) else target,
        }
    cell = document["cells"][0]
    agreement = [r for r in cell["readiness"]["requirements"]
                 if r.get("kind") == "preparation" and "AGREEMENT" in str(r.get("relpath"))]
    if len(agreement) != 1:
        raise SystemExit("the AGREE parent does not carry exactly one agreement-table requirement")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": readiness_reason, "requirements": agreement, "state": "held"}
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    wr(out, dump_like(raw, document))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    parser.add_argument("--data-root", required=True)
    args = parser.parse_args(argv)
    check_program_fragments()
    check_exk30_path()
    measure_path = os.path.join(args.data_root, FIT_MEASURE)
    raw = io.open(measure_path, "rb").read()
    if hashlib.sha256(raw).hexdigest() != FIT_MEASURE_SHA256:
        raise SystemExit(f"{FIT_MEASURE} does not hash to its registered sha256; re-run wsv1_fit_measure.py and re-pin")
    measure = json.loads(raw)
    block = supply_variants_block(measure)

    held = (
        " HELD: root mints the admission receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(through scripts/flights/wsv1/wsv1_flip.sh), which also mints this cell's own first-phase supply under its "
        "own run id (item E16); --allow-output-change must never be passed, and the minted supply must reproduce "
        "the AGREE arm's own first-phase output digest (the Perception supply is upstream of the Solver arm group "
        "and of the program id). Nothing here authorises a flight, a readiness flip or an admission entry."
    )
    written = []
    smoke_ids = json.loads(rd(AGREE_SMOKE_EXPERIMENT))["populations"][0]["ids"]
    arm_audio, smoke_audio = audio_seconds(None), audio_seconds(smoke_ids)

    arm_pairs = substitutions(smoke=False)
    derive_baseline(AGREE_ARM_BASELINE, "configs/baseline/slurp-native-stage3-wsv1-fold-a-baseline-v1.json", arm_pairs,
                    block=block, rows=1080,
                    what_this_is="Cell W-SV-1 (owner decision 172): the first real same-flight supply-variant cell -- the "
                                 "retained AGREE arm with a Solver supply_variants group. " + THE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-wsv1-fold-a-baseline-v1.json")
    derive_experiment(
        AGREE_ARM_EXPERIMENT, "configs/experiment/slurp-native-stage3-wsv1-fold-a-v1.json", arm_pairs, args,
        purpose=(
            "Cell W-SV-1 on TRAIN Fold A 1,080 (owner decision 172, the first real same-flight supply-variant cell): "
            "at the FIRST Solver visit of every row, three arms answer the SAME QueryState in ONE contact batch -- "
            "B with the train-exemplar Solver supply at k 30 (the VAR-1 exk30 construction), T the delivering arm's "
            "twin, A the delivering arm at the AGREE k 20 -- and the Solver-local official pooled SLU-F1 (primary; "
            "intent accuracy the guard) of the B column is read against the A column at the bar the T-vs-A twin "
            "null sets. The estimand is the Solver-local answer at the first Solver visit, never the delivered "
            "full-system answer; the claim ceiling is 'nominated' (Q6 ruling). " + THE_CHANGE + " Development numbers "
            "only (owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip "
            "or an admission entry."
        ),
        readiness_reason=(
            "Cell W-SV-1 registered before contact on " + args.date + " from the retained AGREE arm fragments by script "
            "(decision 58) with the program switched to its 13-ceiling uncited 'first' twin and a Solver supply_variants "
            "block (owner decision 172). No cross-flight comparator: the paired read is within this flight (B and T "
            "columns against the delivering A column); the sealed AGREE arm " + AGREE_RUN + " is context only." + held
        ),
        campaign=True, audio=arm_audio,
    )
    written.append("configs/experiment/slurp-native-stage3-wsv1-fold-a-v1.json")

    smoke_pairs = substitutions(smoke=True)
    derive_baseline(AGREE_SMOKE_BASELINE, "configs/baseline/slurp-native-stage3-wsv1-fold-a-smoke-4-baseline-v1.json",
                    smoke_pairs, block=block, rows=4,
                    what_this_is="Four-row structural form smoke of cell W-SV-1: the same program switch and the same "
                                 "Solver supply_variants block on the first four rows of the unchanged TRAIN Fold A "
                                 "roster. " + THE_CHANGE)
    written.append("configs/baseline/slurp-native-stage3-wsv1-fold-a-smoke-4-baseline-v1.json")
    derive_experiment(
        AGREE_SMOKE_EXPERIMENT, "configs/experiment/slurp-native-stage3-wsv1-fold-a-smoke-4-v1.json", smoke_pairs, args,
        purpose=(
            "Four-row structural form smoke of cell W-SV-1: that the 13-ceiling uncited program loads, that the three "
            "Solver arms fan out at the first visit only (revisits contact A alone), that every arm fits its measured "
            "bound, that the supply-variant receipt (saea-supply-variant-arms-v3) and invariant I7v seal, and that the "
            "episode completes. It is scored by no one and read by no one: four rows can never be evidence of benefit "
            "or of harm. " + THE_CHANGE
        ),
        readiness_reason=(
            "Four-row form smoke of cell W-SV-1, registered before contact on " + args.date + " from the AGREE smoke "
            "fragments by script (decision 58). Structural form proof only: no score, no read, no claim." + held
        ),
        campaign=False, audio=smoke_audio,
        failure_policy=(
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. "
            "A failed smoke stops cell W-SV-1 and the arm does not open. The resume-recovery clause of owner decision "
            "22 applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        ),
    )
    written.append("configs/experiment/slurp-native-stage3-wsv1-fold-a-smoke-4-v1.json")
    campaign = {"cells": [{"cell": "slurp-native-stage3-wsv1-fold-a-v1",
                           "experiment": "slurp-native-stage3-wsv1-fold-a-v1"}],
                "schema": "saea-campaign-plan-v1"}
    wr("configs/campaign/slurp-native-stage3-wsv1-fold-a-v1.json", json.dumps(campaign, indent=2) + "\n")
    written.append("configs/campaign/slurp-native-stage3-wsv1-fold-a-v1.json")
    print(json.dumps({"written": written, "supply_variants": block,
                      "audio_seconds": {"arm": arm_audio, "smoke": smoke_audio}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
