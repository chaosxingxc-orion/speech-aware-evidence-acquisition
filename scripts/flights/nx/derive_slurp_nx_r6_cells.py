#!/usr/bin/env python3
"""Derive the NX round R6-P1 cell (the Perception instruction-template column on TRAIN Fold B) and its four-row smoke.

WHAT THE CELL IS. The COMP-1b composition (``agree-vote-seed`` + ``centroid-boundary-key``, the replicated and admitted
bundle) as a consumption-module block on lock ``v2.2`` (lock v2.1 with the v4g delivery normaliser, module step 7: the R5 arm's
base), with the Reviewer loop OFF (``review_loop: off``: Perception then Solver, no Reviewer or Planner visit, ``phase_tools``
empty so no role renders a tool schema), plus ONE module column per Perception instruction-template candidate (kind ``template``
at node ``perception``): three hand-written candidates p1, p2, p3 (``configs/probes/nx/perception/r6/``, hash-pinned, the pinned
tag grammar beside them), the in-chain twin ``aa`` (``replicate_of`` the delivering arm) and the delivering arm ``lock`` (the
locked Perception template, untemplated, last). Each non-delivering arm is one Perception contact AND one level-2 Solver contact
over that arm's own note (``rails.supply_variants.parse_perception_template_variants``), so the compiled program is
``phase-native-module-v1-c10`` (ceiling 2 + 2 (5 - 1) = 10). Every policy block is WRITTEN BY THE COMPILER
(``rails.consumption_module.compile_module``) from the declared block; nothing policy-side is hand-edited, and the loader refuses a
fragment whose blocks differ from the compiled ones.

THE PARENT. As R1: the Fold B pins (dataset view, roster, the two speech-query pins, the Fold B agreement table, the preparation
receipts) are the P-SV-4 fragments' own; the centroid facet pin is COMP-1b Fold A's (roster independent). Everything else a P-SV
cell carries (the Perception branch block, the 15-ceiling program, the Reviewer loop) is dropped by the compiler.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells are HELD.

    python -B scripts/flights/nx/derive_slurp_nx_r6_cells.py
"""

from __future__ import annotations

import copy
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

import nx_r6_family as nf  # noqa: E402

REPO_ROOT = nf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    DECISION_SUPPLY_PATH, carrier_module_hooks,
)

A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"


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


def substitution_pairs() -> list[tuple[str, str]]:
    """Longest-first id rewrites from the P-SV-4 fragments to this cell's own."""

    return [
        ("slurp-stage3-psv4-fold-b", nf.PKG_NAME[: -len("-v1")]),
        ("PSV4-FOLD-B", nf.SLUG.upper()),
        ("psv4-fold-b", nf.SLUG),
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
    tokens = nf.template_tokens()
    pins = nf.candidate_pins()
    return [
        {"column_id": a, "kind": "template", "node": nf.NODE,
         "template": {"relpath": pins[a]["relpath"], "sha256": pins[a]["sha256"]},
         "template_tokens": tokens[a]}
        for a in nf.ARMS
    ]


def module_block(parent: dict, comp1b: dict) -> dict:
    """COMP-1b's two components ON (this roster's agreement table, COMP-1b's centroid facet), lock v2.2, review loop OFF,
    three Perception template columns, the twin and the delivering lock arm."""

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
    return {
        "module_id": cm.CONSUMPTION_MODULE_ID,
        "profile": "slurp",
        "lock": nf.LOCK,
        "review_loop": "off",
        "components": [armed.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
        "columns": template_columns(),
        "template_frame": nf.template_frame(),
    }


WHAT_THIS_IS = (
    "NX round R6-P1 (node-extreme programme; owner decisions 245-248; design "
    "docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md section 2.2): the first Perception "
    "NODE-TEMPLATE column and the node-local measurement of the Perception node's own entity-presence verdict and heard-mention "
    "list. THE BASE is the COMP-1b composition as a module block on lock v2.2 (lock v2.1 with the v4g delivery normaliser) -- "
    "agree-vote-seed (w_agree 1.0, k 60, the Fold B vote table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1) and "
    "centroid-boundary-key (SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) ON, every other component OFF -- with the Reviewer loop "
    "OFF (Perception then Solver; no Reviewer or Planner visit; no tool schema on any role). THE COLUMN: at the one Perception "
    "visit the Perception node is contacted K = 5 times over the SAME state and the SAME evidence, once per instruction template, "
    "and each non-delivering arm is followed by ITS OWN first-visit Solver contact over that arm's own note (level 2): three "
    "hand-written candidates p1 (presence tag), p2 (presence tag + heard mentions), p3 (presence tag with an unsure hedge + heard "
    "mentions) (configs/probes/nx/perception/r6/, hash-pinned, the pinned tag grammar TAG-GRAMMAR-v1.md beside them), the in-chain "
    "twin aa (replicate_of lock) and the delivering arm lock (the locked Perception template "
    "configs/probes/slurp_native_role_perception_v3.txt, untemplated, last). Only the delivering arm's answer is carried forward; "
    "its requests are the locked plan's requests byte for byte (invariant I7), so the delivered answer is unchanged: this is a "
    f"MEASUREMENT cell. The program is {nf.PROGRAM} (ceiling {nf.CEILING} = 2 + 2 (5 - 1)). Every policy block is the module "
    "compiler's output."
)

STAGE3_ALGORITHM_NOTE = (
    "This cell carries NO training-free RL operator and says so explicitly: it is a same-flight node-template column of the NX "
    "instrument (E1, Perception node) -- three hand-written candidate Perception instruction templates and an in-flight twin read as "
    "columns against the delivering locked-template arm -- with no rollout pool, no per-sample credit, no update operator and no "
    "evolving store. The two composed COMP-1b actions and the v4g delivery normaliser are the base, already admitted by the A2 read "
    "and the v4g lock, and are not exercised as learning operators here."
)

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt "
    "(scripts/flights/nx/nx_r6_mint_receipt.py) and re-pins with scripts/flights/repin_cell.py --set-ready "
    "(through scripts/flights/nx/nx_r6_flip.sh), which also mints this cell's own first-phase supply under its own "
    "run id (item E16; the first Fold B supply at w_agree 1.0 with the centroid key is the R1 cells' own, so the output digest is "
    "expected to equal the R1 cells' and a different digest means the knowledge channel moved -- stop and report); "
    "--allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def derive_baseline(kind: str, comp1b: dict) -> str:
    parent_exp = json.loads(rd(f"configs/experiment/slurp-native-stage3-{nf.PARENT_SLUG}{'-smoke-4' if kind == 'smoke' else ''}-v1.json"))
    parent_name = parent_exp["cells"][0]["baseline_fragment"]
    raw = rd(f"configs/baseline/{parent_name}.json")
    parent = json.loads(substitute(raw, substitution_pairs()))
    block = module_block(parent, comp1b)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    if composed.program_id != nf.PROGRAM or composed.program_ceiling != nf.CEILING:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {nf.PROGRAM} / {nf.CEILING}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own
    rows = nf.SMOKE_ROWS if kind == "smoke" else nf.ROWS
    fit = document["native_contact_fit"]
    names = nf.names(kind)
    fit.update(run_id=names["fit_run_id"], attempt_id=names["fit_attempt_id"], contact_cap=nf.fit_contact_cap(rows))
    # The K6p receipts belong to P-SV-4's key_source branch; the centroid key's receipts are COMP-1b's.
    receipts = [e for e in document["preparation_source_receipts"] if "CENTRED" not in e["relpath"]]
    have = {e["relpath"] for e in receipts}
    for entry in comp1b["preparation_source_receipts"]:
        if "CENTROID" in entry["relpath"] and entry["relpath"] not in have:
            receipts.append(dict(entry))
    document["preparation_source_receipts"] = receipts
    document["what_this_is"] = ("Four-row form smoke of cell " if kind == "smoke" else "Cell ") + nf.CELL_LABEL + ". " + WHAT_THIS_IS
    cm.verify_declared_module(block, document, repo_root=REPO_ROOT)
    ne = document["native_episode"]
    if (ne["review_loop"], ne["max_revisions"], document.get("phase_tools"), ne["deliver_normaliser"]["normaliser"]) != (
            "off", 0, {}, "saea-deliver-normalise-v4g"):
        raise SystemExit("the compiled review-off / v4g leaves are not as expected")
    if ne.get("finite_completion_policy") != "deliver-latest-or-abstain" or ne.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    for key in parent:
        if key in ("policy", "native_episode", "prepared_phase_supply", "what_this_is", "native_contact_fit",
                   "knowledge_stores", "preparation_source_receipts", "phase_material", "phase_tools"):
            continue
        if json.dumps(parent[key], sort_keys=True) != json.dumps(document[key], sort_keys=True):
            raise SystemExit(f"baseline key {key!r} moved beyond the compiled blocks")
    out = f"configs/baseline/{names['baseline']}.json"
    wr(out, dump_like(raw, document))
    return out


def roster_audio(kind: str) -> float:
    doc = json.loads(rd(nf.ROSTER[kind]))
    return sum(float(i["audio_seconds"]) for i in doc["items"])


def budgets(kind: str) -> tuple[dict, dict]:
    rows = nf.SMOKE_ROWS if kind == "smoke" else nf.ROWS
    cap_audio = math.ceil(roster_audio(kind) * nf.CEILING - 1e-9)
    calls = rows * nf.CEILING
    if kind == "smoke":
        # The adapter's budget is run-cumulative across the attempts of a run id: the smoke recovery (SMOKE_RECOVERY) carries the
        # original plan plus the failed attempt's realised spend. The FIT cap below is structural and is NEVER scaled.
        calls, cap_audio = nf.smoke_cumulative_budget(calls, cap_audio)
    gpu = nf.PLANNED_GPU_HOURS_SMOKE if kind == "smoke" else nf.PLANNED_GPU_HOURS_ARM
    fam = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0,
        "fit_endpoint_calls_cap": nf.fit_contact_cap(rows),
        "generation_calls_cap": calls,
        "gpu_hours_fit_inclusive": gpu,
        "native_task_contract_calls_cap": calls,
        "official_complete_scoring_jobs": 0 if kind == "smoke" else 1,
        "repeated_speech_audio_seconds_cap": cap_audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu,
            "planned_model_calls": fam["generation_calls_cap"], "planned_speech_audio_seconds": cap_audio,
            "split_role": "discovery"}
    return fam, plan


def derive_experiment(kind: str) -> str:
    parent_name = f"slurp-native-stage3-{nf.PARENT_SLUG}{'-smoke-4' if kind == 'smoke' else ''}-v1"
    raw = rd(f"configs/experiment/{parent_name}.json")
    document = json.loads(substitute(raw, substitution_pairs()))
    names = nf.names(kind)
    document["date"] = nf.DATE
    document["family_budget"], document["execution_plan"] = budgets(kind)
    document["stage3_algorithm"] = {"id": "none", "operators_used": [], "note": STAGE3_ALGORITHM_NOTE}
    rows = nf.SMOKE_ROWS if kind == "smoke" else nf.ROWS
    if "generation_budget" in document:
        document["generation_budget"] = {
            "cap": rows * nf.CEILING,
            "definition": (
                f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program "
                f"{nf.PROGRAM}: a Perception template group of K = 5 arms (three candidates, the twin aa and the delivering lock) "
                f"raises the bounded graph ceiling by 2 (K - 1) = 8 to {nf.CEILING} contacts per row (rails.native_episode_config: one "
                f"Perception and one level-2 Solver contact per non-delivering arm), so {rows:,} x {nf.CEILING} = {rows * nf.CEILING:,} "
                "is the exact program maximum and the expected spend (five Perception and five Solver contacts per row). The budget is "
                "RUN-CUMULATIVE across every attempt of this run id."
            ),
            "target": rows * nf.CEILING,
        }
    cell = document["cells"][0]
    if cell["cell_id"] != names["experiment"] or cell["run_id"] != names["run_id"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r}")
    cell["attempt_id"] = names["attempt_id"]      # the smoke's rec1 attempt id (SMOKE_RECOVERY); the arm's is unchanged
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
            f"composition on lock v2.2 with the Reviewer loop off and a Perception template column of three candidates, an "
            f"in-chain twin and the locked delivering arm (programme round R6-P1; owner decisions 245-248)." + HELD
        ),
        "requirements": [decision, agreement, supply],
        "state": "held",
    }
    if kind == "smoke":
        document["purpose"] = (
            "Four-row structural form smoke of " + nf.ROUND_LABEL + ": that the declared consumption_module block loads and verifies "
            f"against the fragment's policy blocks, that {nf.PROGRAM} (ceiling {nf.CEILING}) is the bound, that the five "
            "Perception template arms fan out at the one Perception visit with the delivering lock arm last and each non-delivering "
            "arm takes its own level-2 Solver contact, that every arm fits its estimated bound, that the arm receipt "
            "(saea-perception-branch-arms-v4) seals and invariant I7v holds, and that the episode completes. Scored by no one and "
            "read by no one: four rows are never evidence of benefit or harm."
        )
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed "
            "smoke stops cell " + nf.CELL_LABEL + " and the arm does not open. The resume-recovery clause of owner decision 22 "
            "applies to the arm, not to a four-row form smoke, which is re-flown whole if it is re-flown at all. This smoke has "
            "used the cell's single root-diagnosed recovery re-registration (rec1, 2026-10-10; the level-2 note source-hash binding "
            "fix): a second failure closes the cell and the fix is proven on a four-row dry run."
        )
    else:
        document["purpose"] = (
            nf.ROUND_LABEL + " on TRAIN Fold B 1,080 (design docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md "
            "section 2.2; owner decisions 245-248): at the one Perception visit of every row, can the Perception node itself judge "
            "whether the speech expresses an entity value (the E= presence tag) and offer the spoken words of each mention (the M= "
            "options) in the 128-character distinction channel of its note, beyond what the downstream node already has from the supply "
            "(N1 and the intent prior)? Three hand-written Perception instruction templates (p1, p2, p3, "
            "docs/readiness/2026-10-10-slurp-nx-r6-perception-candidates-v1/) are read paired per row against the delivering locked "
            "template inside one flight, with the in-chain twin aa as the null. Primary (node-local): E=none against empty gold on the "
            "rank-1 candidate (AUC, precision, recall) and heard-mention containment, by scripts/analysis/slurp_nx_perception_column_read.py; "
            "information gain and the delivered-metric gate estimate offline from the same columns by "
            "scripts/analysis/slurp_nx_r6_upstream_empty.py --verdict-source perception-arm:<arm>; the intent guards (gold on list, "
            "rank-1 share, candidate count, prompt tokens, note parse status) are paired against lock. The cell is a MEASUREMENT cell "
            "(it claims no benefit: the declared expectation sits under the 1.49 pp same-flight floor and under the 1.5 pp registration "
            "bar); the claim ceiling is 'nominated'. Tuning roster TRAIN Fold A, read roster TRAIN Fold B (a selection read: Fold A "
            "confirms). Development numbers only (owner decisions 28 and 86); never a test claim. Nothing here authorises a flight, a "
            "readiness flip or an admission entry."
        )
        document["failure_policy"] = document["failure_policy"].replace("cell P-SV-4", "cell " + nf.CELL_LABEL).replace(
            "P-SV-4", nf.CELL_LABEL)
    out = f"configs/experiment/{names['experiment']}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv=None) -> int:
    # ``--kinds smoke`` re-derives ONLY the smoke fragments: after the arm was flipped (readiness pins, minted supply) its fragments
    # are the flipped bytes and must not be regenerated; the smoke recovery (SMOKE_RECOVERY, rec1) leaves the arm untouched.
    kinds = ("arm", "smoke")
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        if len(args) != 2 or args[0] != "--kinds" or args[1] not in ("arm", "smoke", "arm,smoke", "smoke,arm"):
            raise SystemExit("usage: derive_slurp_nx_r6_cells.py [--kinds smoke|arm|arm,smoke]")
        kinds = tuple(k for k in ("arm", "smoke") if k in args[1].split(","))
    comp1b_exp = json.loads(rd(f"configs/experiment/{nf.COMP1B_EXPERIMENT}.json"))
    comp1b = json.loads(rd(f"configs/baseline/{comp1b_exp['cells'][0]['baseline_fragment']}.json"))
    written = []
    for kind in kinds:
        written.append(derive_baseline(kind, comp1b))
        written.append(derive_experiment(kind))
    if "arm" in kinds:
        arm = nf.names("arm")
        plan = {"cells": [{"cell": arm["experiment"], "experiment": arm["experiment"]}], "schema": "saea-campaign-plan-v1"}
        wr(nf.CAMPAIGN, json.dumps(plan, indent=2) + "\n")
        written.append(nf.CAMPAIGN)
    print(json.dumps({"written": written, "program": nf.PROGRAM, "ceiling": nf.CEILING}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
