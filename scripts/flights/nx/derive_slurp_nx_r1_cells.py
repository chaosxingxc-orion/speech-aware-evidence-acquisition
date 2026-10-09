#!/usr/bin/env python3
"""Derive the NX round R1 cell (the Solver instruction-template column on TRAIN Fold B) and its four-row smoke.

WHAT THE CELL IS. The COMP-1b composition (``agree-vote-seed`` + ``centroid-boundary-key``, the replicated and
admitted bundle) as a consumption-module block on lock v2.1, with the Reviewer loop OFF (``review_loop: off``:
Perception then Solver, no Reviewer or Planner visit, ``phase_tools`` empty so no role renders a tool schema --
``docs/results/2026-10-09-slurp-nx-solver-parse-root-cause.md``), plus ONE module column per Solver instruction-template
candidate (kind ``template`` at node ``solver``): five hand-written candidates r1-c1 .. r1-c5, the in-chain twin ``aa``
(``replicate_of`` the delivering arm) and the delivering arm ``lock`` (the locked Solver template, untemplated, last).
Every policy block is WRITTEN BY THE COMPILER (``rails.consumption_module.compile_module``) from the declared block
(``native_episode.consumption_module``); nothing policy-side is hand-edited, and the loader refuses a fragment whose
blocks differ from the compiled ones.

THE PARENT. The Fold B pins (dataset view, roster, the two speech-query pins, the Fold B agreement table, the
preparation receipts) are the P-SV-4 fragments' own (which are the filler family's re-target of the AGREE arm to TRAIN
Fold B). The centroid facet pin is COMP-1b Fold A's (roster independent). Everything else a P-SV cell carries is
dropped by the compiler (the Perception branch block, the 15-ceiling program, the Reviewer loop).

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD.

    python -B scripts/flights/nx/derive_slurp_nx_r1_cells.py [--iteration 1|2]

ITERATION 2 (the second and last evaluated round) derives the same cell from the same parent with its own five candidates
r1-i2-c1 .. r1-i2-c5 (nx_r1_family.configure); iteration 1's outputs are unchanged by the parameterisation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nx_r1_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    CURRENT_LOCK, DECISION_SUPPLY_PATH, carrier_module_hooks,
)

A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"
REVIEW_OFF_RECORD = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md"


def rd(path: str) -> str:
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def substitution_pairs(kind: str) -> list[tuple[str, str]]:
    """Longest-first id rewrites from the P-SV-4 fragments to this cell's own."""

    up_old, up_new = "PSV4-FOLD-B", nf.SLUG.upper()
    lo_old, lo_new = "psv4-fold-b", nf.SLUG
    return [
        ("slurp-stage3-psv4-fold-b", nf.PKG_NAME[: -len("-v1")]),
        (up_old, up_new),
        (lo_old, lo_new),
    ]


def substitute(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _node(document: dict, path) -> dict:
    for key in path:
        document = document[key]
    return document


def template_columns() -> list[dict]:
    measure = nf.fit_measure()
    tokens = measure["template_tokens"]
    pins = nf.candidate_pins()
    return [
        {"column_id": a, "kind": "template", "node": "solver",
         "template": {"relpath": pins[a]["relpath"], "sha256": pins[a]["sha256"]},
         "template_tokens": tokens[a]}
        for a in nf.ARMS
    ]


def module_block(parent: dict, comp1b: dict) -> dict:
    """COMP-1b's two components ON (this roster's agreement table, COMP-1b's centroid facet), review loop OFF,
    five template columns, the twin and the delivering lock arm."""

    seed = _node(parent, DECISION_SUPPLY_PATH)
    comp_seed = _node(comp1b, DECISION_SUPPLY_PATH)
    if "FOLD-B" not in seed["agreement_source"]["relpath"]:
        raise SystemExit("the parent does not pin the Fold B agreement table")
    armed = {
        cm.AGREE_VOTE_SEED: {
            "component_id": cm.AGREE_VOTE_SEED, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"w_agree": seed["rank_weights"]["w_agree"], "k": seed["k"],
                       "agreement_source": copy.deepcopy(seed["agreement_source"])},
        },
        cm.CENTROID_BOUNDARY_KEY: {
            "component_id": cm.CENTROID_BOUNDARY_KEY, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"facet_source": copy.deepcopy(comp_seed["facet_source"])},
        },
    }
    frame = copy.deepcopy(nf.fit_measure()["template_frame"])
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID,
        "profile": "slurp",
        "lock": CURRENT_LOCK,
        "review_loop": "off",
        "components": [armed.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
        "columns": template_columns(),
        "template_frame": frame,
    }


WHAT_THIS_IS = (
    "NX round R1 (node-extreme programme, docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md; owner "
    "decisions 228-234): the first same-flight NODE-TEMPLATE column. THE BASE is the COMP-1b composition as a module "
    "block on lock v2.1 -- agree-vote-seed (w_agree 1.0, k 60, the Fold B vote table "
    "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) "
    "ON, every other component OFF -- with the Reviewer loop OFF (Perception then Solver; no Reviewer or Planner visit; "
    "no tool schema on any role). THE COLUMN: at the one Solver visit the Solver is contacted K = 7 times over the SAME "
    "state and the SAME evidence, once per instruction template: five hand-written candidates r1-c1 .. r1-c5 "
    "(configs/probes/nx/solver/r1/, hash-pinned), the in-chain twin aa (replicate_of lock) and the delivering arm lock "
    "(the locked Solver template configs/probes/slurp_native_role_solver_v2.txt, untemplated, last). Only the delivering "
    "arm's answer is carried forward; its request is the locked plan's request byte for byte (invariant I7). The program "
    f"is {nf.PROGRAM} (ceiling {nf.CEILING} = 2 + (7 - 1)). Every policy block is the module compiler's output."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a same-flight node-template column of "
    "the NX instrument (E1) -- five hand-written candidate Solver instruction templates and an in-flight twin read "
    "as columns against the delivering locked-template arm -- with no rollout pool, no per-sample credit, no update "
    "operator and no evolving store. The two composed COMP-1b actions are the base, already admitted by the A2 read, "
    "and are not exercised as learning operators here."
)


def derive_baseline(kind: str, comp1b: dict) -> str:
    parent_exp = json.loads(rd(f"configs/experiment/slurp-native-stage3-{nf.PARENT_SLUG}{'-smoke-4' if kind == 'smoke' else ''}-v1.json"))
    parent_name = parent_exp["cells"][0]["baseline_fragment"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    pairs = substitution_pairs(kind)
    parent = json.loads(substitute(raw, pairs))
    block = module_block(parent, comp1b)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    if composed.program_id != nf.PROGRAM or composed.program_ceiling != nf.CEILING:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {nf.PROGRAM} / {nf.CEILING}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    rows = 4 if kind == "smoke" else nf.ROWS
    fit = document["native_contact_fit"]
    names = nf.names(kind)
    fit.update(run_id=names["fit_run_id"], attempt_id=names["fit_attempt_id"],
               contact_cap=nf.fit_contact_cap(rows))
    # The K6p receipts belong to P-SV-4's key_source branch; the centroid key's receipts are COMP-1b's.
    receipts = [e for e in document["preparation_source_receipts"] if "CENTRED" not in e["relpath"]]
    have = {e["relpath"] for e in receipts}
    for entry in comp1b["preparation_source_receipts"]:
        if "CENTROID" in entry["relpath"] and entry["relpath"] not in have:
            receipts.append(dict(entry))
    document["preparation_source_receipts"] = receipts
    document["what_this_is"] = nf.localize(
        ("Four-row form smoke of cell " if kind == "smoke" else "Cell ") + "NX-R1-SOLVER. " + WHAT_THIS_IS)
    cm.verify_declared_module(block, document, repo_root=REPO_ROOT)
    for key in parent:
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit",
                   "knowledge_stores", "preparation_source_receipts", "phase_material", "phase_tools"):
            continue
        if json.dumps(parent[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the compiled blocks")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


def smoke_audio() -> float:
    doc = json.loads(rd(nf.ROSTER["smoke"]))
    return sum(float(i["audio_seconds"]) for i in doc["items"])


def arm_audio() -> float:
    doc = json.loads(rd(nf.ROSTER["arm"]))
    return sum(float(i["audio_seconds"]) for i in doc["items"])


def attempts_budgeted(kind: str) -> int:
    """The adapter's budget is run-cumulative: iteration 1's smoke covers its failed first attempt plus the recovery;
    iteration 2's smoke is a first attempt (multiplier 1)."""
    return nf.SMOKE_ATTEMPTS_BUDGETED if kind == "smoke" else 1


def budgets(kind: str) -> tuple[dict, dict]:
    rows = 4 if kind == "smoke" else nf.ROWS
    mult = attempts_budgeted(kind)
    audio = smoke_audio() if kind == "smoke" else arm_audio()
    cap_audio = math.ceil(audio * nf.CEILING - 1e-9) * mult
    gpu = nf.PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else nf.PLANNED_GPU_HOURS_ARM
    fam = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": nf.fit_contact_cap(rows),
        "generation_calls_cap": rows * nf.CEILING * mult,
        "gpu_hours_fit_inclusive": gpu,
        "native_task_contract_calls_cap": rows * nf.CEILING * mult,
        "official_complete_scoring_jobs": 0 if kind == "smoke" else 1,
        "repeated_speech_audio_seconds_cap": cap_audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu,
            "planned_model_calls": fam["generation_calls_cap"], "planned_speech_audio_seconds": cap_audio,
            "split_role": "discovery"}
    return fam, plan


HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt "
    "(scripts/flights/nx/nx_r1_mint_receipt.py) and re-pins with scripts/flights/repin_cell.py --set-ready "
    "(through scripts/flights/nx/nx_r1_flip.sh), which also mints this cell's own first-phase supply under its own "
    "run id (item E16; the first Fold B supply at w_agree 1.0 with the centroid key, so there is no earlier digest to "
    "reproduce); --allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an "
    "admission entry."
)


def derive_experiment(kind: str, comp1b_exp: dict) -> str:
    parent_name = f"slurp-native-stage3-{nf.PARENT_SLUG}{'-smoke-4' if kind == 'smoke' else ''}-v1"
    raw = rd(f"configs/experiment/{parent_name}.json")
    document = json.loads(substitute(raw, substitution_pairs(kind)))
    names = nf.names(kind)
    document["date"] = nf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind)
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": nf.localize(STAGE3_ALGORITHM_NOTE)}
    if "generation_budget" in document:
        rows = nf.ROWS
        document["generation_budget"] = {
            "cap": rows * nf.CEILING,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program "
                f"{nf.PROGRAM}: a Solver template group of K = 7 arms (five candidates, the twin aa and the delivering lock) "
                f"raises the bounded graph ceiling by K - 1 = 6 to {nf.CEILING} contacts per row (rails.native_episode_config), "
                f"so {rows:,} x {nf.CEILING} = {rows * nf.CEILING:,} is the exact program maximum and the expected spend "
                f"(one Perception and seven Solver contacts per row). The budget is RUN-CUMULATIVE across every attempt "
                "of this run id."
            ),
            "target": rows * nf.CEILING,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    agreement = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("FOLD-B-V1/agreement.jsonl"))
    supply = {
        "kind": "preparation",
        "reason": (
            "This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
            "core.flight.cli prepare-supply at the flip from the sealed TRAIN Fold B speech-query segment vectors, the "
            "centroid key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the Fold B agreement table, with zero "
            "model, tokenizer, encoder, scorer or server contacts. E16: this cell pins its own. --allow-output-change "
            "must never be passed."
        ),
        "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json",
        "sha256": "0" * 64,
    }
    decision = {
        "kind": "decision", "expected_decision_id": nf.DECISION_ID, "relpath": nf.DECISION_RELPATH,
        "sha256": "0" * 64,
        "reason": f"Decision {nf.DECISION_ID} pinned by scripts/flights/repin_cell.py.",
    }
    cell["readiness"] = {
        "reason": (
            f"{'Four-row form smoke of cell' if kind == 'smoke' else 'Cell'} {nf.CELL_LABEL} registered before contact on "
            f"{nf.DATE} by script (decision 58) from the P-SV-4 Fold B fragments and the module compiler: the COMP-1b "
            f"composition on lock v2.1 with the Reviewer loop off and a Solver template column of five candidates, an "
            f"in-chain twin and the locked delivering arm (programme rounds R1; owner decisions 228-234)." + nf.localize(HELD)
        ),
        "requirements": [decision, agreement, supply],
        "state": "held",
    }
    if kind == "smoke":
        document["purpose"] = (
            "Four-row structural form smoke of " + nf.ROUND_LABEL + ": that the declared consumption_module block loads and verifies "
            f"against the fragment's policy blocks, that {nf.PROGRAM} (ceiling {nf.CEILING}) is the bound, that the seven "
            "Solver template arms fan out at the one Solver visit with the delivering lock arm last, that every arm fits "
            "its estimated bound, that the arm receipt (saea-supply-variant-arms-v4) seals and invariant I7v holds, and "
            "that the episode completes. Scored by no one and read by no one: four rows are never evidence of benefit "
            "or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed "
            "smoke stops cell " + nf.CELL_LABEL + " and the arm does not open. The resume-recovery clause of owner decision 22 "
            "applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all."
        )
    else:
        document["purpose"] = (
            nf.ROUND_LABEL + " on TRAIN Fold B 1,080 (programme docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md, "
            "owner decisions 228-234): at the one Solver visit of every row, which of five hand-written Solver "
            f"instruction templates ({nf.ARMS[0]} .. {nf.ARMS[-1]}, {nf.CANDIDATES_README.rsplit('/', 1)[0]}) raises the "
            "Solver's raw first-answer entity exact-set per row over the delivering locked template, paired per row inside "
            "one flight, with the in-chain twin aa as the null? Primary: node-local raw entity exact-set per row "
            "(scripts/analysis/slurp_nx_solver_column_read.py), effect quoted on official pooled SLU-F1 through the E3 "
            "exchange rate; intent is the guard. The claim ceiling is 'nominated'. Tuning roster TRAIN Fold A (the contrast "
            "tables that shaped the candidates), read roster TRAIN Fold B. Development numbers only (owner decisions 28 and "
            "86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry."
        )
        document["failure_policy"] = document["failure_policy"].replace("cell P-SV-4", "cell " + nf.CELL_LABEL).replace(
            "P-SV-4", nf.CELL_LABEL)
    out = f"configs/experiment/{names['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--iteration", type=int, default=nf.ITERATION, choices=(1, 2))
    nf.configure(parser.parse_args(argv).iteration)
    comp1b_exp = json.loads(rd(f"configs/experiment/{nf.COMP1B_EXPERIMENT}.json"))
    comp1b = json.loads(rd(f"configs/baseline/{comp1b_exp['cells'][0]['baseline_fragment']}.json"))
    written = []
    for kind in ("arm", "smoke"):
        written.append(derive_baseline(kind, comp1b))
        written.append(derive_experiment(kind, comp1b_exp))
    arm = nf.names("arm")
    plan = {"cells": [{"cell": arm["experiment"], "experiment": arm["experiment"]}], "schema": "saea-campaign-plan-v1"}
    wr(nf.CAMPAIGN, json.dumps(plan, indent=2) + "\n")
    written.append(nf.CAMPAIGN)
    print(json.dumps({"written": written, "program": nf.PROGRAM, "ceiling": nf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
