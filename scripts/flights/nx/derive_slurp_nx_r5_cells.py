#!/usr/bin/env python3
"""Derive the NX Stage J round R5 composed cell (review-off COMP-1b + v4g on DEV-2000-ADDED) and its four-row smoke.

WHAT THE CELL IS. The COMP-1b composition (``agree-vote-seed`` + ``centroid-boundary-key``, replicated and admitted by the A2
read) as a consumption-module block on lock ``v2.2`` (module step 7: lock v2.1 with the delivery normaliser moved to
``saea-deliver-normalise-v4g``), with the Reviewer loop OFF (``review_loop: off``: Perception then Solver, Planner and Reviewer
iterations 0, ``phase_tools`` empty so no role renders a tool schema), no template column, no scope-rule stage and no
citation contract (both are refused on a lock whose normaliser is not the carrier's default). The Solver instruction template is
the LOCKED ``configs/probes/slurp_native_role_solver_v2.txt``; ``nf.SOLVER_TEMPLATE_PIN`` is the one-line swap point the R1
iteration-2 pick would replace (this script refuses any other value today: the module has no registered composition that
delivers a non-locked Solver template).

Every policy block is WRITTEN BY THE COMPILER (``rails.consumption_module.compile_module``) from the declared block; nothing
policy-side is hand-edited and the loader refuses a fragment whose blocks differ from the compiled ones. Everything else
(roster, geometry, scorers, fit ids, preparation receipts, the roster pins inside the policy blocks) is the HELD module COMP-1b
cell's own (the DEV-2000-ADDED pins), with the cell ids rewritten.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD (decision 238 is PROPOSED and the R1
iteration-2 verdict is pending).

    python -B scripts/flights/nx/derive_slurp_nx_r5_cells.py
"""

from __future__ import annotations

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

import nx_r5_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

PAIRS = [("MODULE-COMP1B-DEV2000-ADDED", "NX-R5-COMPOSED-DEV2000-ADDED"),
         ("module-comp1b-dev2000-added", "nx-r5-composed-dev2000-added")]
#: The first-phase supply digests the HELD module cells expect (the lock pin, the review-off graph and the delivery normaliser
#: never touch the first-phase Perception supply); the flip's re-derivation checks them.
ARM_SUPPLY_OUTPUT = "ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08"
SMOKE_SUPPLY_OUTPUT = "d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083"


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


def substitute(text: str) -> str:
    for old, new in PAIRS:
        text = text.replace(old, new)
    return text


def check_solver_template_pin() -> str:
    """The one-line swap point: today only the locked Solver template is deliverable."""

    if nf.SOLVER_TEMPLATE_PIN != "configs/probes/slurp_native_role_solver_v2.txt":
        raise SystemExit(
            f"nf.SOLVER_TEMPLATE_PIN is {nf.SOLVER_TEMPLATE_PIN!r}: the consumption module has no registered composition that "
            "delivers a non-locked Solver instruction template (a registered module step, like step 7, must land first)")
    if hashlib.sha256((REPO_ROOT / nf.SOLVER_TEMPLATE_PIN).read_bytes()).hexdigest() != nf.SOLVER_TEMPLATE_SHA:
        raise SystemExit("the locked Solver template bytes moved")
    return nf.SOLVER_TEMPLATE_PIN[len("configs/"):]


def module_block(parent: dict) -> dict:
    """The parent's COMP-1b block (this roster's agreement table, the centroid facet) with the lock and the review loop moved."""

    block = copy.deepcopy(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY])
    armed = sorted(c["component_id"] for c in block["components"] if c["state"] != "off")
    if armed != sorted([cm.AGREE_VOTE_SEED, cm.CENTROID_BOUNDARY_KEY]):
        raise SystemExit(f"the parent arms {armed}, expected exactly COMP-1b")
    if block.get("columns"):
        raise SystemExit("the parent declares columns")
    block["lock"] = nf.LOCK
    block["review_loop"] = "off"
    return block


def roster_audio(ids: list[str] | None) -> float:
    doc = json.loads(rd(nf.ROSTER))
    items = doc["items"]
    if ids is not None:
        by_id = {i["sample_id"]: i for i in items}
        return sum(float(by_id[s]["audio_seconds"]) for s in ids)
    return sum(float(i["audio_seconds"]) for i in items)


def budgets(kind: str, parent_experiment: dict) -> tuple[dict, dict]:
    smoke = kind == "smoke"
    rows = nf.SMOKE_ROWS if smoke else nf.ROWS
    ids = parent_experiment["populations"][0]["ids"] if smoke else None
    audio = roster_audio(ids)
    # The audio source is proven against the parent's own registered cap (ceiling 11).
    parent_cap = parent_experiment["family_budget"]["repeated_speech_audio_seconds_cap"]
    if math.ceil(audio * 11 - 1e-9) != parent_cap:
        raise SystemExit(f"{kind}: ceil(audio x 11) = {math.ceil(audio * 11 - 1e-9)} != the parent's cap {parent_cap}")
    cap_audio = math.ceil(audio * nf.CEILING - 1e-9)
    gpu = nf.PLANNED_GPU_HOURS_SMOKE if smoke else nf.PLANNED_GPU_HOURS_ARM
    fam = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": nf.fit_contact_cap(rows),
        "generation_calls_cap": rows * nf.CEILING,
        "gpu_hours_fit_inclusive": gpu,
        "native_task_contract_calls_cap": rows * nf.CEILING,
        "official_complete_scoring_jobs": 0 if smoke else 1,
        "repeated_speech_audio_seconds_cap": cap_audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu,
            "planned_model_calls": fam["generation_calls_cap"], "planned_speech_audio_seconds": cap_audio,
            "split_role": "dev"}
    return fam, plan


WHAT_THIS_IS = (
    "NX Stage J round R5 (node-extreme programme C2 R5; decision 238 PROPOSED): the composed system. THE COMPOSITION is the "
    "COMP-1b module block -- agree-vote-seed (w_agree 1.0, k 60, THIS roster's vote table "
    "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) "
    "ON, every other component OFF -- on lock v2.2 (lock v2.1 with the delivery normaliser saea-deliver-normalise-v4g, module "
    "step 7) with the Reviewer loop OFF (Perception then Solver, Planner and Reviewer iterations 0, max_revisions 0, no tool "
    f"schema on any role; the compiled program {nf.PROGRAM}, ceiling {nf.CEILING}). The Solver instruction template is the "
    "locked configs/probes/slurp_native_role_solver_v2.txt. Every policy block is the module compiler's output; the roster pins "
    "are DEV-2000-ADDED's own."
)

STAGE3_ALGORITHM_NOTE = (
    "The module composes the SAME two typed, executable consumption actions A2 flew -- a rank weight over a pre-computed vote "
    "and a retrieval key file -- each chosen and credited OFFLINE over sealed bytes (CONV, KPROBE) and admitted by the A2 read, "
    "removes the Reviewer and Planner visits (review-off) and delivers through the registered v4g normaliser (a "
    "deterministic stage selected offline on the A2 DEV pool and confirmed on Fold A). Operator context_application. No "
    "rollout, per-sample scoring, credit assignment or update of its own."
)

HELD = (
    " HELD: decision 238 is PROPOSED (not ruled) and the R1 iteration-2 verdict is pending; this cell registers the composition "
    "that decision A names. If it flies: root countersigns the DRAFT rows (this package AND the replicate's two rows in the "
    "module package), mints both admission receipts and re-pins with scripts/flights/repin_cell.py --set-ready (through "
    "scripts/flights/nx/nx_r5_flip.sh), which mints this cell's own first-phase supply under its own run id (item E16); "
    "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def derive_baseline(kind: str) -> str:
    template_rel = check_solver_template_pin()
    parent_exp = json.loads(rd(f"configs/experiment/{nf.PARENT_SMOKE if kind == 'smoke' else nf.PARENT_ARM}.json"))
    parent_name = parent_exp["cells"][0]["baseline_fragment"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    parent = json.loads(substitute(raw))
    block = module_block(parent)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    if composed.program_id != nf.PROGRAM or composed.program_ceiling != nf.CEILING:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {nf.PROGRAM} / {nf.CEILING}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    names = nf.names(kind)
    fit = document["native_contact_fit"]
    rows = nf.SMOKE_ROWS if kind == "smoke" else nf.ROWS
    fit.update(run_id=names["fit_run_id"], attempt_id=names["fit_attempt_id"], contact_cap=nf.fit_contact_cap(rows))
    document["what_this_is"] = ("Four-row form smoke of cell " if kind == "smoke" else "Cell ") + "NX-R5-COMPOSED. " + WHAT_THIS_IS
    cm.verify_declared_module(block, document, repo_root=REPO_ROOT)
    ne = document["native_episode"]
    if (ne["review_loop"], ne["max_revisions"], document.get("phase_tools"), ne["deliver_normaliser"]["normaliser"]) != (
            "off", 0, {}, nf.NORMALISER):
        raise SystemExit("the compiled review-off / v4g leaves are not as expected")
    if document["phase_material"]["solver"]["instruction_template"] != template_rel:
        raise SystemExit("the compiled Solver instruction template is not the pinned locked one")
    for key in parent:
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit",
                   "knowledge_stores", "preparation_source_receipts", "phase_material", "phase_tools"):
            continue
        if json.dumps(parent[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the compiled blocks")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


def derive_experiment(kind: str) -> str:
    smoke = kind == "smoke"
    parent_name = nf.PARENT_SMOKE if smoke else nf.PARENT_ARM
    raw = rd(f"configs/experiment/{parent_name}.json")
    document = json.loads(substitute(raw))
    parent_experiment = json.loads(raw)
    names = nf.names(kind)
    document["date"] = nf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind, parent_experiment)
    document["stage3_algorithm"] = {"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"],
                                    "note": STAGE3_ALGORITHM_NOTE}
    rows = nf.SMOKE_ROWS if smoke else nf.ROWS
    document["generation_budget"] = {
        "cap": rows * nf.CEILING,
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited, max_revisions 0) under "
            f"program {nf.PROGRAM}: the bounded graph ceiling is {nf.CEILING} contacts per row "
            f"(rails.native_episode_config), so {rows:,} x {nf.CEILING} = {rows * nf.CEILING:,} is the exact program maximum and "
            f"the expected spend (one Perception and one Solver contact per row). The budget is RUN-CUMULATIVE across every "
            "attempt of this run id."),
        "target": rows * nf.CEILING,
    }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + ([] if smoke else ["campaign"])
    agreement = next(r for r in cell["readiness"]["requirements"] if r["relpath"].endswith("DEV2000-ADDED-V1/agreement.jsonl"))
    supply = {
        "kind": "preparation",
        "reason": (
            "This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
            "core.flight.cli prepare-supply at the flip from the sealed DEV-2000-ADDED speech-query segment vectors, the centroid "
            "key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this roster's sealed agreement table, with zero model, "
            "tokenizer, encoder, scorer or server contacts. The review-off graph, the lock-v2.2 normaliser and the lock-v2.1 "
            f"Reviewer pin never touch the first-phase supply, so the output digest is expected to equal "
            f"{SMOKE_SUPPLY_OUTPUT if smoke else ARM_SUPPLY_OUTPUT} (the HELD module cell's); the flip's re-derivation checks "
            "this and a different digest means the knowledge channel moved -- stop and report. E16: this cell pins its own. "
            "--allow-output-change must never be passed."),
        "relpath": f"prepared/{names['run_id']}/phase-supply-v1.json",
        "sha256": "0" * 64,
    }
    cell["readiness"] = {
        "reason": (
            f"{'Four-row form smoke of cell' if smoke else 'Cell'} NX-R5-COMPOSED registered before contact on {nf.DATE} by script "
            "(decision 58) from the HELD module COMP-1b fragments and the module compiler: the COMP-1b composition on lock v2.2 "
            "(v4g at delivery) with the Reviewer loop off (programme R5, Stage J; decision 238 PROPOSED)." + HELD),
        "requirements": [agreement, supply],
        "state": "held",
    }
    if smoke:
        document["purpose"] = (
            "Four-row structural form smoke of the NX R5 composed cell: that the declared consumption_module block (lock v2.2, "
            f"review_loop off) loads and verifies against the fragment's policy blocks, that {nf.PROGRAM} (ceiling {nf.CEILING}) is "
            "the bound, that the delivery node renders saea-deliver-normalise-v4g, that no Reviewer or Planner is visited and no "
            "tool schema is rendered, that every request fits and that the episode completes. Scored by no one and read by no "
            "one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke "
            "stops cell NX-R5-COMPOSED and the arm does not open. The resume-recovery clause of owner decision 22 applies to the "
            "arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all.")
    else:
        document["purpose"] = (
            "NX Stage J round R5 on DEV-2000-ADDED 1,000 (programme C2 R5; decision 238 PROPOSED): the composed system -- COMP-1b "
            "on lock v2.2 (v4g at delivery) with the Reviewer loop off and the locked Solver template -- read in ONE chain beside "
            f"its request-identical in-chain replicate {nf.REPLICATE['run_id']} (instrument rule 3), cross-flight against the "
            f"sealed A2 arm {nf.A2_ARM['run_id']}. Primary: official pooled SLU-F1; guard: intent (scenario_action exact). The "
            "claim is NO LOSS at about half the contacts plus the v4g delivered gain; no benefit is claimed (the declared "
            f"expectation {nf.EXPECTED_EFFECT_PP:+.2f} pp sits under the 2.5 pp bar). Development numbers only (owner decisions "
            "28 and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = document["failure_policy"].replace("cell COMP-1 DEV-2000-ADDED", "cell NX-R5-COMPOSED")
    out = f"configs/experiment/{names['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main() -> int:
    written = []
    for kind in ("arm", "smoke"):
        written.append(derive_baseline(kind))
        written.append(derive_experiment(kind))
    plan = {"cells": [{"cell": nf.REPLICATE["experiment"], "experiment": nf.REPLICATE["experiment"]},
                      {"cell": nf.ARM["experiment"], "experiment": nf.ARM["experiment"]}],
            "schema": "saea-campaign-plan-v1"}
    wr(nf.CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(nf.CAMPAIGN_PLAN)
    print(json.dumps({"written": written, "program": nf.PROGRAM, "ceiling": nf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
