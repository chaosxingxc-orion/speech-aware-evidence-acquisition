#!/usr/bin/env python3
"""Derive the SUCCESSOR-3 cell (the locked system on the Thinking core, flown ONCE on the signed test sample) from the P3.1 lock cell (config only).

SOURCE. The P3.1 lock arm on DEV-2000-ADDED, ``slurp-native-stage3-thinking-system-dev2000-added-lock-v1`` (sealed at flight commit 37b0ed0aa, read NOMINATED).
TARGET. ``slurp-milestone-successor3-thinking-system-v1`` (+ baseline, + one-cell campaign plan) on ``SLURP-TEST-SAMPLE-3010-V1``.

THE LEAF MOVES are exactly the ones successor 2 made from its DEV source (``write_slurp_milestone_successor2_registration.py``, which imports the successor-1
mapping): the dataset view, roster receipt, this roster's speech-query vectors / alias / agreement table (REUSED BY PIN from successor 2's baseline, never rebuilt),
the packet promotion receipt (here the NEW Thinking sample receipt ``TEST-SAMPLE-3010-promotion.json``, pinned by path; its sha256 is pinned at
``--require-receipt`` time and is the zero sentinel while the receipt is absent), the row-scaled budgets, the final-report split role, the TEST scorer sibling
``slurp-slu-official-test``, the one-attempt failure policy, the allowance pin (the signed successor-3 receipt path + sha256) and the run / attempt / FIT ids.
NO smoke cell exists: the allowance forbids a test-sample smoke; the form proof is the flown P3.1 DEV chain (smoke, lock, twin).

THE PROOF (``--prove``; also run by the package writer): from ``core.config.compose``, the successor-3 cell differs from the P3.1 lock cell by roster-bound,
role-bound, bookkeeping and experiment-block leaves alone; every shared roster- and role-bound leaf equals successor 2's value; and the delta successor 2 ->
successor 3 equals the delta R5-composed-DEV -> P3.1-lock-DEV, path for path.

    python -B scripts/flights/nx/successor3_thinking_derive_cells.py [--dry-run] [--require-receipt] [--prove]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import successor3_thinking_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
for extra in (REPO_ROOT / "src", REPO_ROOT / "scripts" / "flights" / "comp1"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import derive_slurp_comp1b_testsample_cells as D  # noqa: E402
import write_slurp_comp1b_testsample_registration as W  # noqa: E402

ZERO = fam.ZERO
#: Leaves of the experiment fragment that are identity text only (no request effect): successor 3 sets them, the proof classifies them as the experiment block.
EXPERIMENT_BLOCK = tuple(W.EXPERIMENT_BLOCK) + ("fragment_kind", "core_read_design.", "populations")
COMPONENTS = "native_episode.consumption_module.components"

WHAT_THIS_IS = (
    "SUCCESSOR-3 of the test-sample milestone reads (owner ruling 301 A, 2026-10-13): the SLURP lock candidate v3.0 -- the locked system on the Thinking core, EXACTLY as "
    "flown and sealed on DEV-2000-ADDED by the P3.1 lock arm (slurp-native-stage3-thinking-system-dev2000-added-lock-v1: the review-off COMP-1b module graph on lock v2.2 "
    "with the v4g post-processing, program phase-native-module-v1-c2, 2 contacts per row, the Thinking model fragment with reasoning budget 3072 + answer reserve 1024 = "
    "completion cap 4096) re-targeted to the signed test sample SLURP-TEST-SAMPLE-3010-V1 by roster-bound pins alone (dataset view, roster receipt, the Thinking packet "
    "promotion receipt of the sample, this roster's speech-query vectors, alias and agreement table REUSED BY PIN from successor 2, row-scaled budgets) plus the "
    "final-report role's own changes (the TEST scorer sibling slurp-slu-official-test and the owner-allowance pin), exactly the mapping that took the R5 composed cell "
    "to successor 2. Lock arm only; no twin, no smoke; one attempt."
)

COMPOSITION = (
    "The locked system on the Thinking core on the signed test sample: COMP-1b's two components ON (agree-vote-seed, w_agree 1.0, recall k 60, with THIS roster's vote "
    "table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-TEST-SAMPLE-3010-V1; centroid-boundary-key) on lock v2.2 (v4g at delivery) with the Reviewer loop OFF (Perception then "
    "Solver, 2 contacts per row), the locked Solver template, every node thinking at budget 3072 -- the P3.1 lock arm's bytes with only the roster moved."
)


def sample_pins() -> dict[str, str]:
    """The sample-preparation pins successor 2's baseline carries (reused by pin, never rebuilt). Refuses if any pending artifact is not pinned."""

    pins: dict[str, str] = {}

    def walk(node):
        if isinstance(node, dict):
            relpath = node.get("relpath")
            if isinstance(relpath, str) and "sha256" in node and relpath in D.PENDING_ARTIFACTS and node["sha256"] != ZERO:
                pins[relpath] = node["sha256"]
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(json.loads(D.rd(f"configs/baseline/{fam.S2_BASELINE}.json")))
    missing = sorted(set(D.PENDING_ARTIFACTS) - set(pins))
    if missing:
        raise SystemExit(f"successor 2 does not pin: {missing}")
    return pins


def retarget_text(text: str) -> str:
    return D.substitute(text, D.ROSTER_SUBSTITUTIONS + [(fam.SRC["fit_run"], fam.FIT_RUN), (fam.SRC["fit_attempt"], fam.FIT_ATTEMPT)])


def derive_baseline(pins: dict[str, str], *, write: bool, require_receipt: bool) -> dict:
    out = f"configs/baseline/{fam.BASELINE}.json"
    raw = D.rd(f"configs/baseline/{fam.SRC['baseline']}.json")
    document = json.loads(retarget_text(raw))
    existing_supply = json.loads(D.rd(out)).get("prepared_phase_supply") if os.path.isfile(out) else None
    document.pop("prepared_phase_supply", None)               # item E16: the flip mints this cell's own supply
    if existing_supply is not None:
        document["prepared_phase_supply"] = existing_supply   # a re-derivation after the flip keeps the minted pin
    document["what_this_is"] = WHAT_THIS_IS
    document["scorers"] = [D.SCORER, "cost"]
    if document.get("speech_packet_promotion_receipt") != fam.THINK_PROMOTION_RECEIPT:
        raise SystemExit(f"the packet promotion receipt did not re-target to the Thinking sample receipt: {document.get('speech_packet_promotion_receipt')!r}")
    document["speech_packet_promotion_receipt_sha256"] = fam.pinned_promotion_sha256(require=require_receipt)
    fit = document["native_contact_fit"]
    per_row = fit["contact_cap"] // 1000
    if per_row * 1000 != fit["contact_cap"] or per_row * fam.ROWS != fam.fit_contact_cap():
        raise SystemExit("the FIT cap is not the exact per-row law at 1,000 rows")
    document["native_contact_fit"] = {**fit, "run_id": fam.FIT_RUN, "attempt_id": fam.FIT_ATTEMPT, "contact_cap": per_row * fam.ROWS}

    def walk(node):
        if isinstance(node, dict):
            relpath = node.get("relpath")
            if isinstance(relpath, str) and "sha256" in node:
                if relpath in D.PENDING_ARTIFACTS:
                    node["sha256"] = pins[relpath]
                elif relpath == D.ROSTER_RECEIPT:
                    node["sha256"] = D.ROSTER_RECEIPT_SHA256
            for key, value in node.items():
                if isinstance(value, str) and key == "embedded_signal":
                    node[key] = value.replace(*D.TEXT_RETARGET)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(document)
    if isinstance(document.get("what_the_train_exemplars_store_is"), str):
        document["what_the_train_exemplars_store_is"] = document["what_the_train_exemplars_store_is"].replace(*D.TEXT_RETARGET)
    probe = {k: v for k, v in document.items() if k != "what_this_is"}
    text = re.sub(r"docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read\.md", "", json.dumps(probe))
    leftover = re.findall(r"[^\"]{0,40}(?:DEV2000|dev2000|DEV-2000|dev-2000)[^\"]{0,40}", text)
    if leftover:
        raise SystemExit(f"DEV-2000-ADDED identifiers survived the re-target: {leftover[:5]}")
    if write:
        D.wr(out, D.dump_like(raw, document))
    return document


def derive_experiment(pins: dict[str, str], *, write: bool) -> dict:
    out = f"configs/experiment/{fam.CELL}.json"
    raw = D.rd(f"configs/experiment/{fam.SRC['cell']}.json")
    document = json.loads(raw)
    s2 = json.loads(D.rd(f"configs/experiment/{fam.S2_CELL}.json"))
    allowance_sha = fam.sha_file(fam.ALLOWANCE)
    allowance = json.loads(D.rd(fam.ALLOWANCE))
    if allowance.get("status") != "authorised" or fam.RUN not in allowance["read_run_ids"] or fam.FIT_RUN not in allowance["preparation_run_ids"]:
        raise SystemExit("the successor-3 allowance is not authorised for exactly the generation and FIT ids")
    rows, calls, audio = fam.ROWS, fam.generation_calls(), fam.audio_cap()
    gpu = fam.planned_gpu_hours()
    family = {"asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0, "fit_endpoint_calls_cap": fam.fit_contact_cap(),
              "generation_calls_cap": calls, "gpu_hours_fit_inclusive": gpu, "native_task_contract_calls_cap": calls,
              "official_complete_scoring_jobs": 1, "repeated_speech_audio_seconds_cap": audio}
    carried = [r for r in s2["cells"][0]["readiness"]["requirements"]
               if r["kind"] == "preparation" and not r["relpath"].endswith("phase-supply-v1.json")]
    if len(carried) != 3:
        raise SystemExit(f"successor 2 carries {len(carried)} sample preparation requirements, expected 3 (agreement table, segment vectors, content vectors)")
    decision = {"kind": "decision", "expected_decision_id": fam.DECISION_ID, "relpath": fam.DECISION_RELPATH, "sha256": ZERO,
                "reason": f"Decision {fam.DECISION_ID} pinned by scripts/flights/repin_cell.py."}
    supply = {"kind": "preparation", "relpath": f"prepared/{fam.RUN}/phase-supply-v1.json", "sha256": ZERO,
              "reason": ("This cell's OWN prepared first-phase Perception supply, minted model-free under its own run id with core.flight.cli prepare-supply at the flip "
                         "from the sample's segment vectors, the centroid key file SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and this roster's agreement table (item E16). "
                         "PENDING until the flip: 64 zeros. The review-off graph and the lock-v2.2 normaliser never touch the first-phase supply, so its selection output is "
                         "expected to equal successor 2's supply selection output (same vectors, key file and table); the flip's re-derivation checks this and a different "
                         "digest means the knowledge channel moved -- stop and report. --allow-output-change must never be passed.")}
    cell = document["cells"][0]
    cell.update({
        "allowed_execution_stages": ["check", "prepare-supply", "worker", "campaign"],
        "attempt_id": fam.ATTEMPT, "baseline_fragment": fam.BASELINE, "cell_id": fam.CELL, "dataset_fragment": fam.DATASET, "run_id": fam.RUN,
        "readiness": {
            "reason": ("Cell SUCCESSOR3-THINKING-SYSTEM registered before contact on 2026-10-14 by script (decision 58) from the P3.1 lock cell (read NOMINATED on "
                       "DEV-2000-ADDED 2026-10-13) under owner ruling 301 A. HELD: (1) the Thinking packets of the sample are produced in the coordinator's GPU swap window "
                       "under their own countersigned exposure row (which itself needs the v2 allowance, owner decision 308) and this baseline's packet-receipt pin is 64 zeros "
                       "until then; (2) root countersigns the DRAFT rows and mints the admission receipt; (3) the flip (successor3_thinking_flip.sh) mints this cell's own supply "
                       "(item E16). --allow-output-change must never be passed. Nothing here authorises a flight, a flip, a mint or a countersignature."),
            "requirements": [decision] + carried + [supply], "state": "held"},
    })
    document["cells"] = [cell]
    document.pop("populations", None)
    document["date"] = fam.DATE
    document["experiment_id"] = fam.RUN
    document["execution_plan"] = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": gpu, "planned_model_calls": calls,
                                  "planned_speech_audio_seconds": audio, "split_role": fam.SPLIT_ROLE}
    document["owner_allowance"] = {"path": fam.ALLOWANCE, "sha256": allowance_sha}
    document["family_budget"] = family
    document["generation_budget"] = {
        "cap": calls, "target": calls,
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {fam.PROGRAM}: {rows:,} x {fam.CONTACTS_PER_ROW} = "
            f"{fam.program_calls():,} is the exact program maximum; the plan ceiling adds {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only fallback contacts per row "
            f"(core.reasoning_knobs): {calls:,} = {rows:,} x {fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}. The live phase fit makes {rows} x {fam.CONTACTS_PER_ROW} x 4 = "
            f"{fam.fit_contact_cap():,} tokenizer endpoint calls under its own run id {fam.FIT_RUN}. The GPU-hour ceiling is a BOUND (rows / {fam.MEASURED_ROWS_PER_MINUTE} rows per "
            f"minute measured at np4 / 60 x {fam.GPU_MARGIN}, ceil 0.1 = {gpu}), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id (there is exactly one).")}
    document["population"] = {
        "count": rows, "dataset_fragment": fam.DATASET, "roster_receipt": D.ROSTER_RECEIPT, "split_identity_hash": D.SPLIT_IDENTITY,
        "decision_population": (
            f"The signed SLURP test SAMPLE {D.ROSTER_ID} (3,010 recordings, 682 prompts; roster receipt {D.ROSTER_RECEIPT}). It is NOT an unexposed sample: the label-free "
            "preparations (owner decision 156), the failed original PLAN generation, the SEALED successor-1 pair and the SEALED successor-2 composed column are inherited "
            "exposure in full. The closure roster SLURP-TEST-CLOSURE-10068-V1 stays untouched.")}
    document["purpose"] = (
        "SUCCESSOR-3 test-sample milestone (owner ruling 301 A; allowance " + fam.ALLOWANCE + "): does the locked system on the Thinking core (SLURP lock candidate v3.0, "
        "NOMINATED on DEV-2000-ADDED by P3.1) keep the sealed successor-2 column's accuracy -- and by how much does it differ -- on the signed test sample, with official pooled "
        "SLU-F1 (slurp-slu-official-test) primary and intent the guard? ONE attempt, ever; the milestone is consumed whether the arm gains, loses or is neutral. Cross-flight "
        "against the SEALED successor-2 run (nothing re-flown); NO in-chain replicate, so the DEV twin offset is declared. claims_benefit is false. Development evidence under "
        "owner decision 28; never a test claim and never the final read. Nothing here authorises a flight, a readiness flip or an admission entry.")
    document["failure_policy"] = D.FAILURE_POLICY
    document["split_id"] = fam.SPLIT_ID
    document["service_session"] = fam.SESSION
    document["fragment_kind"] = f"saea-{fam.CELL}"
    document["stage3_algorithm"] = {
        "id": document["stage3_algorithm"]["id"],
        "note": ("SUCCESSOR-3: ONE rollout of the locked system on the Thinking core on the signed test sample, scored once with the official scorer. No update operator, "
                 "no selection, no tuning on the sample and no benefit claim of its own: it replicates the P3.1 DEV transfer on a fresh test sample as a milestone."),
        "operators_used": list(document["stage3_algorithm"]["operators_used"])}
    document["core_read_design"] = {
        "arms": {"lock": fam.RUN},
        "chain": "swap to the Thinking session (think-budget-np4) -> lock arm (one cell, no smoke, no twin) -> swap back",
        "reading": ("official SLU-F1 paired per recording, prompt-clustered: the Thinking system arm minus the SEALED successor-2 column (cross-flight), against the DECLARED DEV "
                    "twin offset (no in-chain replicate on the sample)"),
        "this_cell": "Thinking system arm (lock) on the signed test sample"}
    if (REPO_ROOT / out).is_file():
        # Re-derivation after the flip keeps the cell's readiness block (state, reason, pinned receipts): the flip's re-pin owns it.
        document["cells"][0]["readiness"] = json.loads(D.rd(out))["cells"][0]["readiness"]
    if write:
        D.wr(out, D.dump_like(raw, document))
    return document


def derive(*, write: bool = True, require_receipt: bool = False) -> dict:
    os.chdir(REPO_ROOT)
    pins = sample_pins()
    baseline = derive_baseline(pins, write=write, require_receipt=require_receipt)
    experiment = derive_experiment(pins, write=write)
    plan = {"cells": [{"cell": fam.CELL, "experiment": fam.CELL}], "schema": "saea-campaign-plan-v1"}
    if write:
        D.wr(fam.CAMPAIGN_PLAN, json.dumps(plan, indent=2, sort_keys=True) + "\n")
    return {"written": [f"configs/experiment/{fam.CELL}.json", f"configs/baseline/{fam.BASELINE}.json", fam.CAMPAIGN_PLAN] if write else [],
            "reused_sample_preparation_pins": pins, "receipt": fam.receipt_state(), "baseline": baseline, "experiment": experiment}


# ---- the composed-diff proof -------------------------------------------------------------------------------------------------------------------------
def classify(a_values: dict, b_values: dict) -> dict:
    a, b = W.flatten(a_values), W.flatten(b_values)
    changed = sorted(k for k in set(a) | set(b) if a.get(k, "<absent>") != b.get(k, "<absent>"))
    out = {"roster_bound": [], "role_bound": [], "bookkeeping": [], "experiment_fragment_own_block": [], "composition_factor": [], "anything_else": []}
    for key in changed:
        if W._matches(key, W.ROSTER_BOUND):
            out["roster_bound"].append(key)
        elif W._matches(key, W.ROLE_BOUND):
            out["role_bound"].append(key)
        elif W._matches(key, W.BOOKKEEPING):
            out["bookkeeping"].append(key)
        elif W._matches(key, EXPERIMENT_BLOCK):
            out["experiment_fragment_own_block"].append(key)
        elif W._matches(key, W.COMPOSITION_FACTORS):
            out["composition_factor"].append(key)
        else:
            out["anything_else"].append(key)
    return out


def _without_components(values: dict) -> dict:
    v = copy.deepcopy(values)
    v.get("native_episode", {}).get("consumption_module", {}).pop("components", None)
    return v


def _components_neutral(values: dict, dev_side: bool) -> str:
    comps = copy.deepcopy(values["native_episode"]["consumption_module"]["components"])
    text = json.dumps(comps, sort_keys=True)
    if dev_side:
        text = retarget_text(text)
    parsed = json.loads(text)

    def walk(node):
        if isinstance(node, dict):
            if "sha256" in node and isinstance(node.get("relpath"), str) and "AGREEMENT" in node["relpath"]:
                node["sha256"] = "<sample-pin>"
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(parsed)
    return json.dumps(parsed, sort_keys=True)


def prove() -> dict:
    """The composed-config proof. Raises SystemExit on any leaf beyond the expected set; returns the proof document."""

    os.chdir(REPO_ROOT)
    r5, p31 = W.composed_of(fam.R5_CELL)[2], W.composed_of(fam.SRC["cell"])[2]
    s2, s3 = W.composed_of(fam.S2_CELL)[2], W.composed_of(fam.CELL)[2]
    fr5, fp31, fs2, fs3 = (W.flatten(c.values) for c in (r5, p31, s2, s3))
    if _components_neutral(p31.values, True) != _components_neutral(s3.values, False):
        raise SystemExit("the module components moved beyond the roster-bound pins")
    vs_p31 = classify(_without_components(p31.values), _without_components(s3.values))
    if vs_p31["anything_else"] or vs_p31["composition_factor"]:
        raise SystemExit(f"S3 vs the P3.1 lock cell: moved beyond the roster re-target: {vs_p31['anything_else'] + vs_p31['composition_factor']}")
    vs_r5_s2 = classify(_without_components(r5.values), _without_components(s2.values))
    # preparation_source_receipts: an unchanged receipt keeps its pin; a re-targeted one is a sample pin
    before, after = p31.values["preparation_source_receipts"], s3.values["preparation_source_receipts"]
    if len(before) != len(after):
        raise SystemExit("preparation_source_receipts changed length")
    for b, a in zip(before, after):
        if a["relpath"] == b["relpath"]:
            if a["sha256"] != b["sha256"] or a.get("root") != b.get("root"):
                raise SystemExit(f"an unchanged preparation receipt moved its pin: {a['relpath']}")
        elif not (a["sha256"] != ZERO and (a["relpath"] == D.ROSTER_RECEIPT or W._is_sample_preparation(a["relpath"]))):
            raise SystemExit(f"a re-targeted preparation receipt is not a sample pin: {a['relpath']}")
    # the explicit Thinking-core receipt leaves (the roster-bound pair that differs from successor 2's Instruct root by design)
    receipt_keys = ("speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256")
    if fs3["speech_packet_promotion_receipt"] != fam.THINK_PROMOTION_RECEIPT:
        raise SystemExit("S3 does not pin the Thinking sample promotion receipt path")
    # every shared roster- and role-bound leaf equals successor 2's value (run-specific leaves exempt)
    moved_s3 = set(vs_p31["roster_bound"]) | set(vs_p31["role_bound"])
    moved_s2 = set(vs_r5_s2["roster_bound"]) | set(vs_r5_s2["role_bound"])
    exempt = ("execution_plan.", "family_budget.", "generation_budget.", "native_contact_fit.", "population.decision_population", "owner_allowance.",
              "what_the_train_exemplars_store_is", "preparation_source_receipts") + receipt_keys
    unequal = [k for k in sorted(moved_s3 & moved_s2)
               if not any(k == e or (e.endswith(".") and k.startswith(e)) for e in exempt) and fs3.get(k, "<absent>") != fs2.get(k, "<absent>")]
    if unequal:
        raise SystemExit(f"roster/role-bound leaves differ from successor 2: {unequal}")
    only_s3, only_s2 = sorted(moved_s3 - moved_s2), sorted(moved_s2 - moved_s3)
    # the composition delta commutes: R5 DEV -> P3.1 lock DEV equals successor 2 -> successor 3, path for path
    categories = (W.ROSTER_BOUND, W.ROLE_BOUND, W.BOOKKEEPING, EXPERIMENT_BLOCK)
    graph_keys = sorted(k for k in set(fr5) | set(fp31) if fr5.get(k, "<absent>") != fp31.get(k, "<absent>")
                        and not any(W._matches(k, g) for g in categories) and k != COMPONENTS)
    bad = [k for k in graph_keys if fs3.get(k, "<absent>") != fp31.get(k, "<absent>") or fs2.get(k, "<absent>") != fr5.get(k, "<absent>")]
    if bad:
        raise SystemExit(f"the composition delta does not commute at {bad}")
    delta_s = sorted(k for k in set(fs2) | set(fs3) if fs2.get(k, "<absent>") != fs3.get(k, "<absent>")
                     and not any(W._matches(k, g) for g in categories) and k != COMPONENTS)
    if delta_s != graph_keys:
        raise SystemExit(f"successor 2 -> successor 3 moves {delta_s}, R5 DEV -> P3.1 lock DEV moves {graph_keys}")
    vs_s2 = classify(_without_components(s2.values), _without_components(s3.values))
    return {
        "s3_vs_p31_lock_dev": vs_p31,
        "r5_dev_to_s2_mapping": {"roster_bound": vs_r5_s2["roster_bound"], "role_bound": vs_r5_s2["role_bound"]},
        "mapping_square": {
            "every_shared_roster_and_role_leaf_equals_successor2": True,
            "leaves_only_in_the_p31_to_s3_mapping": only_s3, "leaves_only_in_the_r5_to_s2_mapping": only_s2,
            "exempt_run_specific_leaves": list(exempt),
            "thinking_receipt_leaves": {k: fs3[k] for k in receipt_keys},
            "note": ("the R5 DEV -> successor-2 mapping and the P3.1 DEV -> successor-3 mapping move the SAME roster- and role-bound leaves; each shared leaf equals successor 2's "
                     "value except the exempt run-specific leaves (budgets, ids, allowance pin, decision_population) and the two packet-receipt leaves, which differ by design "
                     "(successor 2 pins the Instruct sample receipt, successor 3 the Thinking sample receipt)")},
        "composition_delta_commutes": {
            "graph_leaves_moved_by_the_core_swap_on_dev": graph_keys, "successor2_to_successor3_moves_exactly_these": delta_s,
            "components_list": "compared after neutralising roster-bound strings and pins: equal", "commutes": True},
        "s3_vs_successor2": {("composition_delta_graph_leaves" if k == "anything_else" else k): v for k, v in vs_s2.items() if v},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="derive and verify in memory; write nothing")
    parser.add_argument("--require-receipt", action="store_true", help="refuse unless TEST-SAMPLE-3010-promotion.json exists (pins its real sha256)")
    parser.add_argument("--prove", action="store_true", help="print the composed-diff proof of the committed cell")
    args = parser.parse_args(argv)
    if args.prove:
        print(json.dumps(prove(), indent=2, sort_keys=True))
        return 0
    result = derive(write=not args.dry_run, require_receipt=args.require_receipt)
    result.pop("baseline"), result.pop("experiment")
    if not result["receipt"]["present"]:
        print("WARNING: the sample Thinking promotion receipt is absent; the baseline carries the zero sentinel and every consumer fails closed", file=sys.stderr)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
