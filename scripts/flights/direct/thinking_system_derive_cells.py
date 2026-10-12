#!/usr/bin/env python3
"""Derive the three cells of the 268-B read (config only): the locked SLURP system on the Thinking core, TRAIN Fold B, with its twin.

WHAT THE CELLS ARE. The loop's plain lock -- the review-off COMP-1b module graph on lock v2.2 with the v4g post-processing, NO columns and NO
supply arms, program ``phase-native-module-v1-c2`` (Perception 1 + Solver 1) -- derived by the SAME module compiler call the construction-source
column uses (``derive_tfrl_construction_cells.module_block``'s shape) from the SAME committed parent the loop derives from (the NX R6-P1 Fold B
cell), with exactly ONE factor moved: the core. The Instruct model fragment and its speech-packet promotion receipt are replaced by the Thinking
core.s (``q4km-thinking-...-budget3072-max4096-v1``, the packet root ``slurp-q4km-packets-thinking-gpu-afdaeff6`` and the receipt sha256 the 266-E Thinking
baseline pins). The knowledge supply (the loop's Fold B pools, which exclude Fold A and Fold B by construction), the sealed Fold B speech-query
vectors, the agreement table, the centroid keys and the roster are the parent's, byte for byte.

Cells: ``smoke`` (the loop's own four Fold B rows), ``lock`` (the Thinking system arm) and ``aa`` (its request-identical twin: the A/A replicate of
a cross-flight contrast). Nothing is hand-edited: every baseline is the parent plus the compiler's output plus the registered diff, and the
script refuses a leaf that moved beyond :data:`ALLOWED_DIFFS`.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. All cells are HELD.

    python -B scripts/flights/direct/thinking_system_derive_cells.py [--dry-run]
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import thinking_system_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

ALLOWED_DIFFS = (
    "policy", "native_episode.consumption_module", "native_episode.roles.perception.template_variants", "native_contact_fit",
    "preflight_budget_mode",
    "prepared_phase_supply", "what_this_is", "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256",
)

WHAT_THIS_IS = (
    "Cell 268-B (owner decision 268 B, 2026-10-12): the LOCKED SLURP system on the Thinking core. THE SYSTEM is the loop's plain lock -- the "
    "review-off COMP-1b module graph (agree-vote-seed, centroid-boundary-key; lock v2.2 with the v4g post-processing) with NO columns and NO supply "
    "arms: Perception 1 + Solver 1 = 2 contacts per row under program phase-native-module-v1-c2, the same knowledge supply and sealed Fold B "
    "speech-query vectors as the Instruct lock column of loop iteration 3. THE ONE FACTOR is the core: the Instruct model fragment and its speech "
    "packets are replaced by the Thinking core (reasoning budget 3072 + answer reserve 1024 = completion cap 4096, --reasoning-format deepseek so reasoning never enters message.content, its own "
    "speech-packet root). The delivered answers are the content channel only. Every policy block is the module compiler's output."
)

ROLE_TEXT = {
    "smoke": ("Four-row form smoke of the Thinking system: it proves that the module program loads on the Thinking session, that the Thinking "
              "packet plane and the reasoning-format option work under the native module graph, that the live phase fit and the seal work, and what a "
              "Thinking contact costs per node (completion tokens, seconds, cap hits, empty completions, compaction)."),
    "lock": "The Thinking system arm of the 268-B read.",
    "aa": ("The in-chain request-identical TWIN of the Thinking system arm (measurement instrument rule 3): the same fragment bytes, session and "
           "1,080 rows flown a second time, so the cross-flight contrast with the Instruct lock column is read against a measured same-core offset. "
           "Between the arm and its twin only the run identities and this prose differ; none of them enters a request."),
}

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/direct/thinking_system_mint_receipt.py), swaps the "
    "serving geometry to the Thinking session (scripts/flights/batch/serving_swap.sh think-budget-np4) and flips the cells with "
    "scripts/flights/batch/flip_package_ext4.sh through scripts/flights/direct/thinking_system_flip.sh, which also mints each cell's own first-phase "
    "supply under its own run id (item E16); --allow-output-change must never be passed. Nothing here authorises a flight, a readiness flip or an "
    "admission entry."
)


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return dv.rd(path, root)


def parent_names(parent_kind: str) -> dict:
    return dv.parent_names(parent_kind)


def substitution_pairs(slug: str) -> list[tuple[str, str]]:
    parent = fam.PARENT_SLUG
    return [(f"slurp-stage3-{parent}", f"slurp-stage3-{slug}"), (parent.upper(), slug.upper()), (parent, slug)]


def substitute(text: str, slug: str) -> str:
    for old, new in substitution_pairs(slug):
        text = text.replace(old, new)
    return text


def module_block(parent: Mapping[str, Any]) -> dict:
    """The parent's COMP-1b review-off block with the columns and the template frame removed (the plain lock)."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (tf.PARENT_LOCK, "off"):
        raise SystemExit(f"the parent's module block is not review-off lock {tf.PARENT_LOCK}")
    block["lock"] = fam.LOCK
    block["columns"] = []
    block.pop("template_frame", None)
    block.pop("supply_frame", None)
    return block


def derive_baseline(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    spec = fam.CELLS[key]
    parent_name = parent_names(spec["parent_kind"])["baseline"]
    raw = rd(f"configs/baseline/{parent_name}.json", repo_root)
    parent = json.loads(raw)
    block = module_block(parent)
    composed = cm.compile_module(block, carrier_module_hooks(repo_root=repo_root), repo_root=repo_root)
    if composed.program_id != fam.PROGRAM or composed.program_ceiling != fam.CONTACTS_PER_ROW:
        raise SystemExit(f"compiled program {composed.program_id} / {composed.program_ceiling}, expected {fam.PROGRAM} / {fam.CONTACTS_PER_ROW}")
    document = composed.apply_to(parent)
    document["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY] = block
    out = f"configs/baseline/{spec['baseline']}.json"
    existing_supply = None
    if (repo_root / out).is_file():
        # Re-derivation after the flip keeps the cell's minted first-phase supply pin: resetting it here would silently un-flip the cell.
        existing_supply = json.loads(rd(out, repo_root)).get("prepared_phase_supply")
    document.pop("prepared_phase_supply", None)                       # E16: the flip mints this cell's own
    if existing_supply is not None:
        document["prepared_phase_supply"] = existing_supply
    document["native_contact_fit"] = {**parent["native_contact_fit"], "run_id": spec["fit_run"], "attempt_id": spec["fit_attempt"],
                                      "contact_cap": fam.fit_contact_cap(spec["rows"])}
    # The one factor: the Thinking core's own speech packets (the audio-encoder tensors of the two mmproj files differ, so the Instruct packets
    # are not valid input to the Thinking decoder).
    document["speech_packet_promotion_receipt"] = fam.THINK_PROMOTION_RECEIPT
    document["speech_packet_promotion_receipt_sha256"] = fam.thinking_promotion_sha256()
    # The Thinking knobs are the model fragment's own keys (core.reasoning_knobs); the all-nodes-think arm declares NO per-node thinking_policy.
    if "thinking_policy" in document:
        raise SystemExit("the all-nodes-think arm declares no thinking_policy")
    document["what_this_is"] = f"{ROLE_TEXT[key]} " + WHAT_THIS_IS
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode.get("review_loop"), episode.get("max_revisions")) != ("off", 0):
        raise SystemExit("the Thinking system cell must run the Reviewer loop off")
    # Preflight fit (coordinator finding, 2026-10-12 19:40Z). The model-free preflight counts the JSON payload at 4 bytes per token
    # (core.flight.runtime._default_token_counter, a placeholder): 21,269 "tokens" for the widest Solver render, where the exact
    # native per-contact gate measured 14,641 on the same requests of the Instruct lock column (iteration 3: zero compactions in
    # 1,080 rows, every context_compaction null). At the registered 4,096 cap the heuristic exceeds the physical 24,576 slot and
    # the check refuses a fit the wire has. The cell therefore defers the preflight estimate to the registered exact per-contact
    # gate (the mechanism the R01C recovery cells use). The lock's own context_fit_policy "compact-or-abstain" is kept (it is part
    # of the compiled module block): at the wire the exact gate compacts or abstains a row that does not fit, and the Instruct lock
    # column never compacted, so the two arms stay request-identical.
    document["preflight_budget_mode"] = "defer-to-native-contact-fit"
    if "supply_variants" in json.dumps(episode["roles"]):
        raise SystemExit("the Thinking system cell carries no supply arms")
    left, right = dv._leaves(parent), dv._leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    stray = [k for k in moved if not any(k == p or k.startswith(p + ".") for p in ALLOWED_DIFFS)]
    if stray:
        raise SystemExit(f"leaves moved beyond the registered diff: {stray[:12]}")
    if write:
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document, "block": block, "program": composed.program_id, "ceiling": composed.program_ceiling,
            "loader_verification": dv.loader_verification(block, document, repo_root)}


def budgets(key: str, repo_root: Path = REPO_ROOT) -> tuple[dict, dict]:
    spec = fam.CELLS[key]
    rows = spec["rows"]
    calls = fam.generation_calls(key)
    audio = fam.audio_cap(spec["roster"])
    family = {
        "asr_calls": 0, "ceilings_are_not_targets": True, "encoder_calls": 0, "fit_endpoint_calls_cap": fam.fit_contact_cap(rows),
        "generation_calls_cap": calls, "gpu_hours_fit_inclusive": spec["gpu_hours"], "native_task_contract_calls_cap": calls,
        "official_complete_scoring_jobs": spec["scoring_jobs"], "repeated_speech_audio_seconds_cap": audio,
    }
    plan = {"execution_profile": "bounded-discovery-probe", "planned_gpu_hours": spec["gpu_hours"], "planned_model_calls": calls,
            "planned_speech_audio_seconds": audio, "split_role": "discovery"}
    return family, plan


def readiness_requirements(key: str, parent_cell: Mapping[str, Any]) -> list[dict]:
    """The decision receipt, the parent's Fold B agreement-table requirement (byte for byte) and the cell's OWN first-phase supply (zero sha)."""

    spec = fam.CELLS[key]
    decision = {"kind": "decision", "expected_decision_id": fam.DECISION_ID, "relpath": fam.DECISION_RELPATH, "sha256": "0" * 64,
                "reason": f"Decision {fam.DECISION_ID} pinned by scripts/flights/repin_cell.py."}
    agreement = next(r for r in parent_cell["readiness"]["requirements"] if r["relpath"].endswith("FOLD-B-V1/agreement.jsonl"))
    supply = {"kind": "preparation", "relpath": f"prepared/{spec['run']}/phase-supply-v1.json", "sha256": "0" * 64,
              "reason": ("This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with core.flight.cli "
                         "prepare-supply at the flip from the sealed TRAIN Fold B speech-query segment vectors, the centroid key file "
                         "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the Fold B agreement table (item E16). --allow-output-change must "
                         "never be passed.")}
    return [decision, agreement, supply]


def derive_experiment(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    spec = fam.CELLS[key]
    smoke = key == "smoke"
    parent_exp = parent_names(spec["parent_kind"])["experiment"]
    raw = rd(f"configs/experiment/{parent_exp}.json", repo_root)
    document = json.loads(substitute(raw, spec["slug"]))
    parent_cell = json.loads(raw)["cells"][0]
    cell = document["cells"][0]
    if cell["cell_id"] != spec["cell"] or cell["run_id"] != spec["run"] or cell["baseline_fragment"] != spec["baseline"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r} / {cell['baseline_fragment']!r}")
    roster = fam.roster_doc(spec["roster"])
    ids = [str(item["sample_id"]) for item in roster["items"]]
    if len(ids) != spec["rows"]:
        raise SystemExit(f"{fam.ROSTER[spec['roster']]} has {len(ids)} rows, expected {spec['rows']}")
    rows = spec["rows"]
    calls = fam.generation_calls(key)
    family, plan = budgets(key, repo_root)
    document["date"] = fam.DATE
    document["experiment_id"] = spec["run"]
    document["execution_plan"], document["family_budget"] = plan, family
    document["fragment_kind"] = f"saea-{cell['cell_id']}"
    document["service_session"] = spec["session"]
    # Native role contacts REQUIRE preserved wire metadata (reproduction.ojw.native_roles._wire_turn): the module graph cannot run with False.
    document["preserve_wire_responses"] = True
    document["stage3_algorithm"] = {
        "id": "shared-rollout", "operators_used": ["rollout", "scoring"],
        "note": ("The 268-B read: ONE rollout of the locked system on the Thinking core (and its twin), scored once with the official scorer. No "
                 "update operator, no selection and no benefit claim of its own: it measures whether a core lever (+11.90 pp SLU-F1 bare, 266-E) "
                 "transfers to the locked system.")}
    document["split_id"] = fam.SPLIT_ID
    document["population"] = {
        "count": rows, "dataset_fragment": fam.DATASET, "roster_receipt": fam.ROSTER[spec["roster"]],
        "split_identity_hash": roster["split_identity_hash"],
        "decision_population": (
            f"TRAIN Fold B ({roster['roster_id']}): {rows} rows of {fam.ROSTER[spec['roster']]}"
            + ("; four of its rows, structural form proof only, no score and no read." if smoke else
               "; discovery role, rollout-exposed, never a test claim (owner decisions 28 and 86); the roster the Instruct lock column "
               "of loop iteration 3 flies, so the contrast is paired per row."))}
    document["populations"] = [{"dataset_fragment": fam.DATASET, "ids": ids}]
    cell.update(attempt_id=spec["attempt"], model_fragment=spec["model"],
                allowed_execution_stages=["check", "prepare-supply", "worker"] + ([] if smoke else ["campaign"]))
    document["generation_budget"] = {
        "cap": calls, "target": calls,
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {fam.PROGRAM}: {rows:,} x "
            f"{fam.CONTACTS_PER_ROW} = {rows * fam.CONTACTS_PER_ROW:,} is the exact program maximum; the plan ceiling adds {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only fallback contacts per row (core.reasoning_knobs): {calls:,} = {rows:,} x {fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}. The live phase fit makes {rows} x "
            f"{fam.CONTACTS_PER_ROW} x {tf.FIT_ENDPOINTS_PER_CONTACT} = {fam.fit_contact_cap(rows):,} tokenizer endpoint calls under its own run id "
            f"{spec['fit_run']}. The GPU-hour ceiling is a BOUND (rows x row-seconds of the design throughput model / {fam.THINK_SLOTS} slots x "
            f"{fam.GPU_MARGIN}), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id.")}
    out = f"configs/experiment/{spec['cell']}.json"
    cell["readiness"] = {
        "reason": (f"{ROLE_TEXT[key]} Registered before contact on {fam.DATE} by script (decision 58) from the loop's committed Fold B module "
                   "parent and the module compiler (owner decision 268 B)." + HELD),
        "requirements": readiness_requirements(key, parent_cell), "state": "held"}
    if (repo_root / out).is_file():
        # Re-derivation after the flip keeps the cell's readiness block (state, reason, pinned receipts): the flip's re-pin owns it.
        cell["readiness"] = json.loads(rd(out, repo_root))["cells"][0]["readiness"]
    if smoke:
        document["purpose"] = (
            f"Four-row structural form smoke of the 268-B read: that {fam.PROGRAM} (ceiling {fam.CONTACTS_PER_ROW}) loads on the Thinking session "
            f"({fam.THINK_SESSION}), that the Thinking speech packets resolve under the native module graph, that --reasoning-format deepseek keeps "
            "reasoning out of the delivered content, that the live phase fit passes at the 8,192-token completion cap, that the seal works and that "
            "the episode completes, and what a Thinking contact costs per node (completion tokens, seconds, cap hits, empty completions, "
            "compaction). Scored by no one and read by no one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops the cell "
            "and the arms do not open. The smoke is re-flown whole at most once under one root-diagnosed recovery re-registration; a second "
            "failure closes the cell and the fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"{spec['run']}: the {spec['role']} of the 268-B read on TRAIN Fold B 1,080 (owner decision 268 B): does the +11.90 pp SLU-F1 / +4.35 "
            "intent core lever of the bare Thinking core (266-E) stack on the locked system? The Thinking system arm is read against the Instruct "
            "lock column of loop iteration 3 (same roster, same system, a different core) at the cross-flight bar, with the in-chain twin as the "
            "A/A replicate. claims_benefit is false: a measurement of transfer, not an admission. Development numbers only (owner decisions 28 "
            "and 86); never a test claim. Nothing here authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation attempt id AND a new "
            "native_contact_fit run and attempt id); a second failure closes the cell and the fix is proven on a four-row dry run. A response "
            "whose delivered content carries a reasoning marker is a failure of the read, not of a row: it stops the flight "
            "(reasoning_content_guard). A partial manifest is never scored and never read.")
    document["core_read_design"] = {
        "arms": {k: fam.CELLS[k]["run"] for k in fam.ARM_KEYS},
        "chain": "swap to the Thinking session -> smoke -> coordinator sign-off -> lock arm -> twin aa -> swap back to the Instruct session",
        "reading": ("official SLU-F1 paired per row: Thinking system arm minus the Instruct lock column of loop iteration 3 (cross-flight), the "
                    "twin offset as the A/A, and the Thinking system arm minus the bare Thinking core (266-E)"),
        "this_cell": spec["role"],
    }
    leftovers = [m.group(0) for m in re.finditer(r".{40}(?:nx-r6|NX-R6|NX_R6|R6-P1|perception-fold-b).{20}", json.dumps(document))]
    if leftovers:
        raise SystemExit(f"inherited parent identity text survived the rewrite ({key}): {leftovers[:3]}")
    if write:
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document}


def write_campaign(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> str:
    spec = fam.CELLS[key]
    plan = {"cells": [{"cell": spec["cell"], "experiment": spec["cell"]}], "schema": "saea-campaign-plan-v1"}
    if write:
        dv.wr(spec["campaign"], json.dumps(plan, indent=2, sort_keys=True) + "\n", repo_root)
    return spec["campaign"]


def derive(*, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    out: dict[str, Any] = {"cells": {}, "_documents": {}}
    for key in fam.ALL_KEYS:
        baseline = derive_baseline(key, repo_root=repo_root, write=write)
        experiment = derive_experiment(key, repo_root=repo_root, write=write)
        out["cells"][key] = {"baseline": baseline["path"], "experiment": experiment["path"], "loader_verification": baseline["loader_verification"]}
        out["_documents"][key] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
        out["program"], out["ceiling"] = baseline["program"], baseline["ceiling"]
    out["campaigns"] = [write_campaign(key, repo_root=repo_root, write=write) for key in fam.ARM_KEYS]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="derive and verify in memory; write nothing")
    args = parser.parse_args(argv)
    result = derive(write=not args.dry_run)
    result.pop("_documents", None)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
