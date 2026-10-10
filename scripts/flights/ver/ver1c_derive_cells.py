#!/usr/bin/env python3
"""Derive cell VER-1c (the R1 c3 Solver template column on TRAIN Fold A) and its four-row smoke.

WHAT THE CELL IS. The review-off COMP-1b module graph at lock ``v2.2`` (``agree-vote-seed`` + ``centroid-boundary-key`` ON, Reviewer
loop OFF, no tool schema on any role; the NX R5 composed arm / R6-P1 / VER-1a base) on TRAIN Fold A, plus ONE module column: the R1 ``r1-c3``
Solver instruction template (kind ``template`` at node ``solver``, the SAME pinned bytes the R1 iteration-1 cell flew), the in-chain twin
``aa`` (``replicate_of`` the delivering arm) and the delivering arm ``lock`` (the locked Solver template, untemplated, last): three
arms at the one Solver visit. Every policy block is WRITTEN BY THE COMPILER (``rails.consumption_module.compile_module``) from the
declared block (``native_episode.consumption_module``); nothing policy-side is hand-edited, and the loader refuses a fragment whose
blocks differ from the compiled ones. The program is ``vf.PROGRAM`` (ceiling ``2 + (K - 1)`` with K = 3 arms).

THE PARENT. The committed COMP-1b Fold A baselines (arm / smoke): their Fold A pins (the agreement table, both speech-query pins, the
centroid facet pin, the preparation receipts) are the ones the COMP-1b / A2 cells flew. This is the R1 derive
(``derive_slurp_nx_r1_cells.py``) re-targeted to Fold A, at lock v2.2, one candidate.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD.

    python -B scripts/flights/ver/ver1c_derive_cells.py
"""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ver1c_family as cf  # noqa: E402

REPO_ROOT = cf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    DECISION_SUPPLY_PATH, carrier_module_hooks,
)

A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"


def rd(path: str) -> str:
    import io
    return io.open(REPO_ROOT / path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> None:
    import io
    import os
    target = REPO_ROOT / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)


def dump_like(raw: str, obj: object) -> str:
    match = re.search(r"\n( +)\"", raw)
    indent = len(match.group(1)) if match else 2
    return json.dumps(obj, indent=indent, ensure_ascii=False, sort_keys=True) + ("\n" if raw.endswith("\n") else "")


def substitute(text: str) -> str:
    for old, new in ((f"slurp-stage3-{cf.PARENT_SLUG}", f"slurp-stage3-{cf.SLUG}"), (cf.PARENT_SLUG.upper(), cf.SLUG.upper()),
                     (cf.PARENT_SLUG, cf.SLUG)):
        text = text.replace(old, new)
    return text


def _node(document: dict, path) -> dict:
    for key in path:
        document = document[key]
    return document


def template_columns() -> list[dict]:
    tokens = cf.fit_measure()["template_tokens"]
    pins = cf.candidate_pins()
    return [
        {"column_id": a, "kind": "template", "node": cf.NODE,
         "template": {"relpath": pins[a]["relpath"], "sha256": pins[a]["sha256"]}, "template_tokens": tokens[a]}
        for a in cf.ARMS
    ]


def module_block(parent: dict) -> dict:
    """COMP-1b's two components ON (the parent's own Fold A agreement table and centroid facet), review loop OFF, lock v2.2,
    the template column(s), the twin and the delivering lock arm."""

    seed = _node(parent, DECISION_SUPPLY_PATH)
    if cf.FOLD_TOKEN not in seed["agreement_source"]["relpath"]:
        raise SystemExit(f"the parent does not pin the {cf.FOLD_TOKEN} agreement table")
    armed = {
        cm.AGREE_VOTE_SEED: {
            "component_id": cm.AGREE_VOTE_SEED, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"w_agree": seed["rank_weights"]["w_agree"], "k": seed["k"],
                       "agreement_source": copy.deepcopy(seed["agreement_source"])},
        },
        cm.CENTROID_BOUNDARY_KEY: {
            "component_id": cm.CENTROID_BOUNDARY_KEY, "state": "on", "admitted_by": A2_READ, "record": A2_READ,
            "params": {"facet_source": copy.deepcopy(seed["facet_source"])},
        },
    }
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID,
        "profile": "slurp",
        "lock": cf.LOCK,
        "review_loop": "off",
        "components": [armed.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
        "columns": template_columns(),
        "template_frame": copy.deepcopy(cf.fit_measure()["template_frame"]),
    }


WHAT_THIS_IS = (
    f"{cf.CELL_LABEL} (owner decision 257, 2026-10-10; decision 258 option A: the Fold A confirmation of the verification layer): the "
    f"Fold A c3 COLUMN that is the verdict source of the VER-1 rule. THE BASE is the COMP-1b composition as a module block on lock "
    f"{cf.LOCK} -- agree-vote-seed (w_agree 1.0, k 60, the Fold A vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-{cf.FOLD_TOKEN}-V1) and "
    "centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) ON, every other component OFF -- with the Reviewer loop OFF "
    f"(Perception then Solver; no Reviewer or Planner visit; no tool schema on any role), on {cf.FOLD_TITLE} {cf.ROWS:,}. THE COLUMN: at the one "
    f"Solver visit the Solver is contacted K = {cf.K} times over the SAME state and the SAME evidence, once per instruction template: the "
    f"R1 candidate {cf.ARMS[0]} (configs/probes/nx/solver/r1/, the SAME hash-pinned bytes the NX R1 iteration-1 cell flew), the "
    f"in-chain twin {cf.TWIN} (replicate_of {cf.DELIVERING}) and the delivering arm {cf.DELIVERING} (the locked Solver template "
    f"{cf.LOCKED_TEMPLATE}, untemplated, last). Only the delivering arm's answer is carried forward; its request is the locked plan's "
    f"request byte for byte (invariant I7). The program is {cf.PROGRAM} (ceiling {cf.CEILING} = {cf.BASE_CONTACTS} + ({cf.K} - 1)). The "
    "arm is the VERDICT SOURCE of the VER-1 rule (the Solver answered no entity under r1-c3, after v4g), not a nomination: "
    "claims_benefit false. Every policy block is the module compiler's output."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a same-flight node-template column of the NX "
    f"instrument (E1) -- the R1 candidate Solver instruction template {cf.ARMS[0]} and an in-flight twin read as columns against the "
    "delivering locked-template arm -- with no rollout pool, no per-sample credit, no update operator and no evolving store. Its column "
    "is the c3 verdict source that the inference-time verification rule (VER-1b's sample pool) is read with, offline."
)

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt "
    f"(scripts/flights/ver/{cf.SHORT}_mint_receipt.py) and re-pins with scripts/flights/repin_cell.py --set-ready "
    f"(through scripts/flights/ver/{cf.SHORT}_flip.sh), which also mints this cell's own first-phase supply under its own "
    f"run id (item E16; the {cf.FOLD_TITLE} supply at w_agree 1.0 with the centroid key is the COMP-1b / A2 cells' own, so the output digest is "
    "expected to equal COMP-1b's and a different digest means the knowledge channel moved -- stop and report); "
    "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def derive_baseline(kind: str) -> str:
    parent_name = cf.parent_names(kind)["baseline"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    parent = json.loads(raw)
    block = module_block(parent)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    if composed.program_id != cf.PROGRAM or composed.program_ceiling != cf.CEILING:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {cf.PROGRAM} / {cf.CEILING}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)                # E16: the flip mints this cell's own
    rows = cf.SMOKE_ROWS if kind == "smoke" else cf.ROWS
    names = cf.names(kind)
    document["native_contact_fit"] = {**parent["native_contact_fit"], "run_id": names["fit_run_id"],
                                      "attempt_id": names["fit_attempt_id"], "contact_cap": cf.fit_contact_cap(rows)}
    document["what_this_is"] = ("Four-row form smoke of cell " if kind == "smoke" else "Cell ") + cf.CELL_LABEL + ". " + WHAT_THIS_IS
    cm.verify_declared_module(block, document, repo_root=REPO_ROOT)
    ne = document["native_episode"]
    if (ne["review_loop"], ne["max_revisions"], document.get("phase_tools"), ne["deliver_normaliser"]["normaliser"]) != (
            "off", 0, {}, "saea-deliver-normalise-v4g"):
        raise SystemExit("the compiled review-off / v4g leaves are not as expected")
    if ne.get("finite_completion_policy") != "deliver-latest-or-abstain" or ne.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    for key in parent:                                         # outside the compiled blocks nothing of the parent moved
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit",
                   "knowledge_stores", "preparation_source_receipts", "phase_material", "phase_tools"):
            continue
        if json.dumps(parent[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the compiled blocks")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


def budgets(kind: str) -> tuple[dict, dict]:
    rows = cf.SMOKE_ROWS if kind == "smoke" else cf.ROWS
    calls = rows * cf.CEILING
    audio = cf.audio_cap(kind)
    gpu = cf.PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else cf.PLANNED_GPU_HOURS_ARM
    fam = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": cf.fit_contact_cap(rows),
        "generation_calls_cap": calls,
        "gpu_hours_fit_inclusive": gpu,
        "native_task_contract_calls_cap": calls,
        "official_complete_scoring_jobs": 0 if kind == "smoke" else 1,
        "repeated_speech_audio_seconds_cap": audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu, "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return fam, plan


def derive_experiment(kind: str) -> str:
    parent = cf.parent_names(kind)["experiment"]
    raw = rd(f"configs/experiment/{parent}.json")
    document = json.loads(substitute(raw))
    names = cf.names(kind)
    rows = cf.SMOKE_ROWS if kind == "smoke" else cf.ROWS
    document["date"] = cf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind)
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    population = document["population"]
    if population["count"] != rows or population["dataset_fragment"] != "slurp-speech-native-evo-fold-a-1080":
        raise SystemExit("the parent population is not the Fold A roster")
    population["decision_population"] = (
        f"{cf.FOLD_TITLE}, the rule-confirmation roster ({cf.ROWS:,} rows of {cf.ROSTER['arm']}, {cf.READ_ROSTER}; the unchanged "
        "roster the sealed COMP-1b / A2 Fold A cells flew, so the column is paired row for row with the Fold A sample pool of cell VER-1b): "
        + (f"{cf.SMOKE_ROWS} rows, the first {cf.SMOKE_ROWS} Fold A rows (the COMP-1b Fold A smoke fragment's own prefix); structural form "
           "proof only, no score and no read." if kind == "smoke" else
           f"the rule was FIXED on {cf.TUNING_ROSTER} and nothing is chosen on this roster."))
    if kind == "arm":
        population["roster_receipt"] = cf.ROSTER["arm"]
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * cf.CEILING,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program "
                f"{cf.PROGRAM}: a Solver template group of K = {cf.K} arms (the candidate {cf.ARMS[0]}, the twin {cf.TWIN} and the "
                f"delivering {cf.DELIVERING}) raises the bounded graph ceiling by K - 1 = {cf.K - 1} to {cf.CEILING} contacts per row "
                f"(rails.native_episode_config), so {rows:,} x {cf.CEILING} = {rows * cf.CEILING:,} is the exact program maximum and the "
                f"expected spend (one Perception and {cf.K} Solver contacts per row). The budget is RUN-CUMULATIVE across every attempt "
                "of this run id."
            ),
            "target": rows * cf.CEILING,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["attempt_id"] = names["attempt_id"]
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if kind == "arm" else [])
    agreement = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith(f"{cf.FOLD_TOKEN}-V1/agreement.jsonl"))
    supply = {
        "kind": "preparation",
        "reason": (
            "This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
            f"core.flight.cli prepare-supply at the flip from the sealed {cf.FOLD_TITLE} speech-query segment vectors, the "
            f"centroid key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the {cf.FOLD_TITLE} agreement table, with zero "
            "model, tokenizer, encoder, scorer or server contacts. E16: this cell pins its own. --allow-output-change "
            "must never be passed."
        ),
        "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json",
        "sha256": "0" * 64,
    }
    decision = {
        "kind": "decision", "expected_decision_id": cf.DECISION_ID, "relpath": cf.DECISION_RELPATH, "sha256": "0" * 64,
        "reason": f"Decision {cf.DECISION_ID} pinned by scripts/flights/repin_cell.py.",
    }
    cell["readiness"] = {
        "reason": (
            f"{'Four-row form smoke of cell' if kind == 'smoke' else 'Cell'} {cf.CELL_LABEL} registered before contact on {cf.DATE} by "
            f"script (decision 58) from the committed COMP-1b {cf.FOLD_TITLE} fragments and the module compiler: the COMP-1b composition on "
            f"lock {cf.LOCK} with the Reviewer loop off and a Solver template column of {len(cf.ARMS)} candidate ({cf.ARMS[0]}), an "
            "in-chain twin and the locked delivering arm (owner decision 257; decision 258 option A, the Fold A c3 verdict column)." + HELD
        ),
        "requirements": [decision, agreement, supply],
        "state": "held",
    }
    if kind == "smoke":
        document["purpose"] = (
            f"Four-row structural form smoke of {cf.CELL_LABEL}: that the declared consumption_module block loads and verifies "
            f"against the fragment's policy blocks, that {cf.PROGRAM} (ceiling {cf.CEILING}) is the bound, that the {cf.K} Solver "
            "template arms fan out at the one Solver visit with the delivering lock arm last, that every arm fits its estimated bound, "
            "that the arm receipt (saea-supply-variant-arms-v4) seals and invariant I7v holds, and that the episode completes. Scored by "
            "no one and read by no one: four rows are never evidence of benefit or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops "
            f"cell {cf.CELL_LABEL} and the arm does not open. A form smoke is re-flown whole if it is re-flown at all, under at most "
            "one root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run."
        )
    else:
        document["purpose"] = (
            f"{cf.CELL_LABEL} on {cf.FOLD_TITLE} {cf.ROWS:,} (owner decision 257, decision 258 option A): the Fold A c3 COLUMN. At the one "
            f"Solver visit of every row the R1 candidate {cf.ARMS[0]} (the same hash-pinned template the NX R1 iteration-1 cell flew), "
            f"the in-chain twin {cf.TWIN} and the delivering lock arm answer over the SAME state and evidence, so that the VER-1 rule "
            f"FIXED on {cf.TUNING_TITLE} (the c3 verdict = {cf.VERDICT_ARM} answered no entity after v4g, gated by N1 >= 0.2, with the "
            "n = 3, s = 2 support filter over the VER-1b sample pool) can be CONFIRMED OFFLINE with "
            f"{cf.COMPOSER} --verdict-run. The arm is the verdict source of the rule, not a nomination: claims_benefit false, expected "
            "effect 0.0 pp. Development numbers only (owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, "
            "a readiness flip or an admission entry."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact; at most one root-diagnosed recovery re-registration; a second failure "
            "closes the cell and the fix is proven on a four-row dry run. No retry, no partial quality read."
        )
    out = f"configs/experiment/{names['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv=None) -> int:
    written = []
    for kind in ("arm", "smoke"):
        written.append(derive_baseline(kind))
        written.append(derive_experiment(kind))
    plan = {"cells": [{"cell": cf.ARM["experiment"], "experiment": cf.ARM["experiment"]}], "schema": "saea-campaign-plan-v1"}
    wr(cf.CAMPAIGN, json.dumps(plan, indent=2) + "\n")
    written.append(cf.CAMPAIGN)
    for path in written:
        if re.search(r"comp1b-fold-a|COMP1B-FOLD-A", rd(path)):
            raise SystemExit(f"{path}: carries inherited COMP-1b Fold A identity text")
    print(json.dumps({"written": written, "program": cf.PROGRAM, "ceiling": cf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
