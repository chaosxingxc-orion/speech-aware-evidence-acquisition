#!/usr/bin/env python3
"""Derive the evidence-consumption module's first end-to-end cell -- COMP-1b as a MODULE BLOCK on
DEV-2000-ADDED, on lock v2.1 -- with its four-row smoke and its in-chain A/A (the module's OFF arm).

WHY. Migration step 6 of the consumption module (design
``docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md`` section 4; owner decisions 195,
196, 204; coordinator rulings R1-R5) re-expresses new registrations as module blocks. Today's reads name
the first composed component list: COMP-1b = ``agree-vote-seed`` + ``centroid-boundary-key``, REPLICATED
and ADMITTED on DEV-2000-ADDED (``docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md``). Lock v2.1
(``docs/results/2026-09-30-slurp-v2-1-lock-v1.md``: v2.0 + the G5 Reviewer template) is the base of every
cell registered after A2 sealed.

WHAT EACH CELL IS. Every policy-owned block (``policy``, ``knowledge_stores``, ``native_episode``,
``phase_material``) is WRITTEN BY THE COMPILER (``rails.consumption_module.compile_module``) from the
cell's declared ``native_episode.consumption_module`` block; nothing policy-side is hand-edited. Every
other key -- roster, geometry, scorers, fit ids, preparation receipts, and the roster pins inside the
policy blocks (the sealed DEV-2000-ADDED speech-query vectors, ``CarrierHooks.roster_pin_paths``) -- is
the parent cell's own, with the cell ids rewritten:

* arm / smoke: parents are cell A2's own committed arm and smoke fragments (the flown COMP-1b DEV bytes);
  the block arms ``agree-vote-seed`` (A2's own params: w_agree 1.0, k 60, THIS roster's agreement table)
  and ``centroid-boundary-key`` (A2's own facet pin) on ``lock: v2.1``; everything else ``off``;
* A/A: parent is A2's in-chain A/A fragment; the block is the module's OFF arm on ``lock: v2.1`` (every
  component ``off``), which compiles to the lock-v2.1 bytes (so recall k is the lock's 8, not the A2
  A/A's 60 -- the A2 A/A's k 60 at w_agree 0 was a proven supply no-op, output digest d57ee9d6...).

The byte proofs (arm == A2's arm except the lock-v2.1 Reviewer pin and bookkeeping; A/A == lock v2.1) are
made by ``write_slurp_module_comp1bdev_registration.py`` and ``scripts/analysis/module_equivalence_proof.py
--at m6``. Config only: three baselines, three experiment fragments and one campaign plan. No contact,
no ledger row, no receipt, no flip; every cell is HELD.

    python scripts/flights/module/derive_slurp_module_comp1bdev_cells.py --date 2026-09-30
"""

from __future__ import annotations

import argparse
import copy
import io
import json
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    CURRENT_LOCK, DECISION_SUPPLY_PATH, carrier_module_hooks,
)

A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"
LOCK_NOTE = "docs/results/2026-09-30-slurp-v2-1-lock-v1.md"
A2_ARM = "slurp-native-stage3-comp1b-dev2000-added-v1"
A2_SMOKE = "slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1"
A2_AA = "slurp-native-stage3-comp1-aa-dev2000-added-v1"

ARM_CELL = "slurp-native-stage3-module-comp1b-dev2000-added-v1"
SMOKE_CELL = "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1"
AA_CELL = "slurp-native-stage3-module-comp1b-aa-dev2000-added-v1"
CAMPAIGN_PLAN = "configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json"
AGREEMENT_RELPATH = "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1/agreement.jsonl"

#: ``(parent experiment, new experiment, [(old id fragment, new id fragment)])``.
DERIVATIONS = {
    "arm": (A2_ARM, ARM_CELL, [("COMP1B-DEV2000-ADDED", "MODULE-COMP1B-DEV2000-ADDED"),
                               ("comp1b-dev2000-added", "module-comp1b-dev2000-added")]),
    "smoke": (A2_SMOKE, SMOKE_CELL, [("COMP1B-DEV2000-ADDED", "MODULE-COMP1B-DEV2000-ADDED"),
                                     ("comp1b-dev2000-added", "module-comp1b-dev2000-added")]),
    "aa": (A2_AA, AA_CELL, [("COMP1-AA-DEV2000-ADDED", "MODULE-COMP1B-AA-DEV2000-ADDED"),
                            ("comp1-aa-dev2000-added", "module-comp1b-aa-dev2000-added")]),
}

THE_COMPOSITION = (
    "The evidence-consumption module saea-evidence-consumption-module-v1 (profile slurp) on lock v2.1 (owner "
    "decision 204: the v2.0 lock with the Reviewer instruction template moved to the G5 bytes "
    "probes/slurp_native_role_reviewer_v1_g5_v1.txt, sha256 724a437d...) with COMP-1b's two components ON -- "
    "agree-vote-seed (w_agree 1.0, recall k 60, THIS roster's vote table "
    "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) and centroid-boundary-key (facet_source "
    "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1) -- and every other catalogued component OFF (no citation "
    "contract, no scope rule, no re-listen, no Perception column). Every policy block is written by the "
    "module's compiler; the roster pins are DEV-2000-ADDED's own."
)
AA_COMPOSITION = (
    "The module's OFF arm on lock v2.1: saea-evidence-consumption-module-v1 with EVERY component off, which "
    "compiles byte for byte to the lock-v2.1 policy blocks (the v2.0 lock with the G5 Reviewer template; "
    "recall k 8, w_agree 0.0, the written boundary key, no citation contract), on DEV-2000-ADDED's own "
    "roster pins."
)


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


def substitute(text: str, pairs) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _node(document: dict, path) -> dict:
    for key in path:
        document = document[key]
    return document


def module_block(key: str) -> dict:
    """The declared block of each cell: A2's own params for the two components (arm, smoke), or the
    all-off block (A/A); ``lock`` is the carrier's CURRENT lock (v2.1)."""

    armed: dict[str, dict] = {}
    if key in ("arm", "smoke"):
        parent = json.loads(rd(f"configs/baseline/{json.loads(rd(f'configs/experiment/{DERIVATIONS[key][0]}.json'))['cells'][0]['baseline_fragment']}.json"))
        seed = _node(parent, DECISION_SUPPLY_PATH)
        if seed["agreement_source"]["relpath"] != AGREEMENT_RELPATH:
            raise SystemExit(f"{key}: the parent does not pin THIS roster's agreement table")
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
        "lock": CURRENT_LOCK,
        "components": [armed.get(spec.component_id, {"component_id": spec.component_id, "state": "off"})
                       for spec in cm.COMPONENT_CATALOGUE],
        "columns": [],
    }


def derive_baseline(key: str, parent_experiment: str, pairs, *, what_this_is: str) -> str:
    parent_cell = json.loads(rd(f"configs/experiment/{parent_experiment}.json"))["cells"][0]
    parent_path = f"configs/baseline/{parent_cell['baseline_fragment']}.json"
    raw = rd(parent_path)
    parent = json.loads(substitute(raw, pairs))
    block = module_block(key)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=REPO_ROOT), repo_root=REPO_ROOT)
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    document.pop("prepared_phase_supply", None)  # E16: the flip mints this cell's own supply
    document["what_this_is"] = what_this_is
    # The loader's own check, before anything is written: the declared block compiles to exactly
    # the fragment's policy blocks (roster pins aside).
    cm.verify_declared_module(block, document, repo_root=REPO_ROOT)
    out = f"configs/baseline/{substitute(parent_cell['baseline_fragment'], pairs)}.json"
    wr(out, dump_like(raw, document))
    return out


def derive_experiment(key: str, parent_experiment: str, new_experiment: str, pairs, args, *, purpose: str,
                      reason: str, requirements: list[dict], campaign: bool, algorithm: dict) -> str:
    raw = rd(f"configs/experiment/{parent_experiment}.json")
    document = json.loads(substitute(raw, pairs))
    document["date"] = args.date
    document["purpose"] = purpose
    cell = document["cells"][0]
    if cell["cell_id"] != new_experiment:
        raise SystemExit(f"{key}: id rewrite produced {cell['cell_id']!r}, expected {new_experiment!r}")
    cell["allowed_execution_stages"] = ["check", "prepare-supply", "worker"] + (["campaign"] if campaign else [])
    cell["readiness"] = {"reason": reason, "requirements": requirements, "state": "held"}
    document["stage3_algorithm"] = algorithm
    out = f"configs/experiment/{new_experiment}.json"
    wr(out, dump_like(raw, document))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--date", required=True)
    args = parser.parse_args(argv)

    a2_arm = json.loads(rd(f"configs/experiment/{A2_ARM}.json"))
    agreement_requirement = next(
        r for r in a2_arm["cells"][0]["readiness"]["requirements"] if r.get("relpath") == AGREEMENT_RELPATH
    )
    held = (
        "HELD (migration step 6): this cell is the consumption module's first end-to-end proof -- its policy "
        "blocks are the compiler's output and are proven equal to cell A2's flown bytes except the lock-v2.1 "
        "Reviewer pin -- and the first lock-v2.1 in-chain A/A. It needs to fly only if the coordinator decides "
        "the byte proof is not enough. If it flies: root countersigns the DRAFT rows, mints the admission "
        "receipt and re-pins with scripts/flights/repin_cell.py --set-ready "
        "(scripts/flights/module/module_comp1bdev_flip.sh), which mints this cell's own first-phase supply "
        "(item E16). --allow-output-change must never be passed."
    )

    def supply_requirement(run_id: str, expected: str, what: str) -> dict:
        return {
            "kind": "preparation",
            "reason": (
                f"This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with "
                f"core.flight.cli prepare-supply at the flip from {what}, with zero model, tokenizer, encoder, scorer "
                f"or server contacts. The lock-v2.1 Reviewer pin never touches the first-phase supply, so the output "
                f"digest is expected to equal {expected}; the flip's re-derivation checks this. E16: this cell pins "
                "its own. --allow-output-change must never be passed."
            ),
            "relpath": f"prepared/{run_id}/phase-supply-v1.json",
            "sha256": "0" * 64,
        }

    arm_sources = ("the sealed DEV-2000-ADDED speech-query segment vectors, the CENTROID key file "
                   "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this roster's sealed agreement table -- the "
                   "sources cell A2's arm supply was built from")
    written: list[str] = []
    for key in ("arm", "smoke", "aa"):
        parent, new, pairs = DERIVATIONS[key]
        run_id = json.loads(substitute(rd(f"configs/experiment/{parent}.json"), pairs))["cells"][0]["run_id"]
        if key == "arm":
            what = "Cell MODULE-COMP1B-DEV2000 (migration step 6): COMP-1b as a module block on lock v2.1. " + THE_COMPOSITION
            purpose = (
                "Migration step 6 of the evidence-consumption module (owner decisions 195/196/204) on DEV-2000-ADDED "
                "1,000: the module's first end-to-end cell -- COMP-1b (agree-vote-seed + centroid-boundary-key, "
                f"REPLICATED and ADMITTED on this roster by {A2_READ}: intent +4.60 [+2.58, +6.73], SLU-F1 +0.53 "
                "[-1.04, +2.09]) expressed as a module block and compiled onto lock v2.1 -- read against its own "
                f"in-chain A/A {AA_CELL} (the module's OFF arm on lock v2.1), intent primary, official pooled SLU-F1 "
                "(slurp-slu-official, DEV sibling) the non-inferiority guard at h_SLU 1.2525. " + THE_COMPOSITION
                + " expected_effect_pp is the A2 read's intent point (owner decision 139: a measured number, not a "
                "prior), measured on lock v2.0 bytes; this cell's base is v2.1, whose one moved pin read no harm "
                f"({LOCK_NOTE}). Development numbers only (owner decisions 28 and 86); never a test claim. Nothing "
                "here authorises a flight, a readiness flip or an admission entry."
            )
            requirements = [agreement_requirement, supply_requirement(run_id, "cell A2's arm output ecca16a276a9a4a35b6b5e0a765d30ab2b3ee893e3bc617c5ae2c3e7c51b7d08", arm_sources)]
            algorithm = {"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"],
                         "note": ("The module composes the SAME two typed, executable consumption actions A2 flew -- a rank "
                                  "weight over a pre-computed vote and a retrieval key file -- each chosen and credited "
                                  "OFFLINE over sealed bytes (CONV, KPROBE) and admitted by the A2 read; the compiler "
                                  "writes them into every row's Perception supply. Operator context_application. No "
                                  "rollout, per-sample scoring, credit assignment or update of its own.")}
        elif key == "smoke":
            what = "Four-row structural form smoke of cell MODULE-COMP1B-DEV2000 (migration step 6). " + THE_COMPOSITION
            purpose = (
                "Four-row structural form smoke of the module's first end-to-end cell: that the declared "
                "consumption_module block loads and verifies against the fragment's policy blocks, that this "
                "roster's agreement table and the centroid key file hash-verify, that the boundary channel delivers "
                "eight entries, that the Reviewer renders the lock-v2.1 template and that every request fits and "
                "the episode completes. Scored by no one and read by no one. " + THE_COMPOSITION
            )
            requirements = [agreement_requirement, supply_requirement(run_id, "cell A2's smoke output d5ec9b1516cb6b389d39aebec32b2b700b663ff21d15303a4789893415e3e083", arm_sources)]
            algorithm = {"id": "sealed-credit-system-policy-v1", "operators_used": ["context_application"],
                         "note": "The four-row structural form smoke of the module cell: the same two composed actions on four DEV-2000-ADDED rows; scored by no one and read by no one."}
        else:
            what = ("The IN-CHAIN A/A of cell MODULE-COMP1B-DEV2000 and the FIRST lock-v2.1 A/A (owner decision 204). "
                    + AA_COMPOSITION)
            purpose = (
                "The in-chain A/A of the module's first end-to-end cell on DEV-2000-ADDED: the module's OFF arm (every "
                "component off) on lock v2.1, re-flown in the same campaign chain to supply the within-chain null the "
                "module arm is read at, and the first measured lock-v2.1 A/A. It makes no claim of its own and admits "
                "nothing. " + AA_COMPOSITION + " Development numbers only (owner decisions 28 and 86)."
            )
            requirements = [supply_requirement(run_id, "the sealed DEV plan arm's d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19 (as cell A2's A/A did)",
                                               "the same sealed DEV-2000-ADDED speech-query segment vectors and the same written-key facet vectors the sealed DEV plan arm used")]
            algorithm = {"id": "none", "operators_used": [],
                         "note": ("This cell carries NO training-free RL operator: it is the module's OFF arm, which "
                                  "compiles to the lock-v2.1 bytes, re-flown in the same chain as the in-chain null "
                                  "and instrument of the module arm.")}
        written.append(derive_baseline(key, parent, pairs, what_this_is=what))
        written.append(derive_experiment(key, parent, new, pairs, args, purpose=purpose, reason=held,
                                         requirements=requirements, campaign=key != "smoke", algorithm=algorithm))

    plan = {"cells": [{"cell": AA_CELL, "experiment": AA_CELL}, {"cell": ARM_CELL, "experiment": ARM_CELL}],
            "schema": "saea-campaign-plan-v1"}
    wr(CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    written.append(CAMPAIGN_PLAN)
    print(json.dumps({"written": written}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
