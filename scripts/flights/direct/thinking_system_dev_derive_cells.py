#!/usr/bin/env python3
"""Derive the three cells of the P3.1 replicate (config only): the locked SLURP system on the Thinking core, DEV-2000-ADDED, with its twin.

WHAT THE CELLS ARE. The plain lock -- the review-off COMP-1b module graph on lock v2.2 with the v4g post-processing, NO columns and NO supply
arms, program ``phase-native-module-v1-c2`` (Perception 1 + Solver 1) -- derived from the SEALED Instruct cell of the same graph on the same
roster, NX R5 composed on DEV-2000-ADDED (``SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1``), with exactly ONE factor moved: the core. The
Instruct model fragment and its speech-packet promotion receipt are replaced by the Thinking core's (the Fold B family's budget3072-max4096
fragment, the existing Thinking packet root and the NEW ``DEV-2000-ADDED-promotion.json`` receipt). The knowledge supply (the full-TRAIN pools the
parent pins), the sealed DEV speech-query vectors, the agreement table, the centroid keys and the roster are the parent's, byte for byte.

Before anything is written the script PROVES the parent reproduces: the parent's module block, recompiled by the module compiler, gives back the
parent baseline apart from the registered diff (:data:`ALLOWED_DIFFS`). A leaf that moves beyond it refuses the derivation.

THE RECEIPT. While ``DEV-2000-ADDED-promotion.json`` is absent the baselines carry the zero sentinel (never a fabricated hash) and the package says so
in its blockers; ``--require-receipt`` makes the absence a refusal. After the coordinator's packet window re-run with ``--require-receipt``, then
the package writer, and commit: the composed config hashes move with the pinned sha.

CONFIG ONLY: no contact, no ledger row, no receipt, no flip. All cells are HELD.

    python -B scripts/flights/direct/thinking_system_dev_derive_cells.py [--dry-run] [--require-receipt]
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

import thinking_system_dev_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

ALLOWED_DIFFS = (
    "native_contact_fit", "preflight_budget_mode", "prepared_phase_supply", "what_this_is",
    "speech_packet_promotion_receipt", "speech_packet_promotion_receipt_sha256",
)

WHAT_THIS_IS = (
    "Cell P3.1 (registry 'P3 programme under decision 299 A', 2026-10-13): the LOCKED SLURP system on the Thinking core, DEV-2000-ADDED replicate. "
    "THE SYSTEM is the plain lock of the sealed Instruct cell NX R5 composed on this roster -- the review-off COMP-1b module graph "
    "(agree-vote-seed, centroid-boundary-key; lock v2.2 with the v4g post-processing) with NO columns and NO supply arms: Perception 1 + Solver 1 = 2 "
    "contacts per row under program phase-native-module-v1-c2, the same full-TRAIN knowledge supply, DEV-2000-ADDED sealed speech-query vectors and "
    "agreement table as that Instruct column. THE ONE FACTOR is the core: the Instruct model fragment and its speech packets are replaced by the "
    "Thinking core (reasoning budget 3072 + answer reserve 1024 = completion cap 4096, --reasoning-format deepseek so reasoning never enters "
    "message.content, its own packet root with the NEW DEV-2000-ADDED promotion receipt). The delivered answers are the content channel only."
)

ROLE_TEXT = {
    "smoke": ("Four-row form smoke of the Thinking system on DEV-2000-ADDED: it proves that the module program loads on the Thinking session, that the "
              "DEV Thinking packets resolve under the native module graph, that the live phase fit and the seal work, and what a Thinking contact costs per "
              "node (completion tokens, seconds, cap hits, empty completions, compaction)."),
    "lock": "The Thinking system arm of the P3.1 replicate.",
    "aa": ("The in-chain request-identical TWIN of the Thinking system arm (measurement instrument rule 3): the same fragment bytes, session and "
           "1,000 rows flown a second time, so the cross-flight contrast with the Instruct lock column is read against a measured same-core offset. "
           "Between the arm and its twin only the run identities and this prose differ; none of them enters a request."),
}

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/direct/thinking_system_dev_mint_receipt.py), swaps the "
    "serving geometry to the Thinking session (scripts/flights/batch/serving_swap.sh think-budget-np4) and flips the cells with "
    "scripts/flights/batch/flip_package_ext4.sh through scripts/flights/direct/thinking_system_dev_flip.sh, which also mints each cell's own first-phase "
    "supply under its own run id (item E16); --allow-output-change must never be passed. The flip refuses while the DEV Thinking promotion receipt is absent. "
    "Nothing here authorises a flight, a readiness flip or an admission entry."
)


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return dv.rd(path, root)


def substitution_pairs(slug: str) -> list[tuple[str, str]]:
    parent = fam.PARENT_SLUG
    return [(f"slurp-stage3-{parent}", f"slurp-stage3-{slug}"), (parent.upper(), slug.upper()), (parent, slug)]


def substitute(text: str, slug: str) -> str:
    for old, new in substitution_pairs(slug):
        text = text.replace(old, new)
    return text


def module_block(parent: Mapping[str, Any]) -> dict:
    """The parent's COMP-1b review-off block (already the plain lock: no columns, no template frame, no supply frame)."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (fam.LOCK, "off"):
        raise SystemExit(f"the parent's module block is not review-off lock {fam.LOCK}: {block.get('lock')!r} / {block.get('review_loop')!r}")
    if block.get("columns"):
        raise SystemExit("the parent's module block carries columns; the plain lock has none")
    for key in ("template_frame", "supply_frame"):
        if key in block:
            raise SystemExit(f"the parent's module block carries a {key}; the plain lock has none")
    return block


def derive_baseline(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True, require_receipt: bool = False) -> dict:
    spec = fam.CELLS[key]
    parent_name = fam.parent_names(spec["parent_kind"])["baseline"]
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
    # The one factor: the Thinking core's own speech packets for this roster (the audio-encoder tensors of the two mmproj files differ).
    document["speech_packet_promotion_receipt"] = fam.THINK_PROMOTION_RECEIPT
    document["speech_packet_promotion_receipt_sha256"] = fam.pinned_promotion_sha256(require=require_receipt)
    if "thinking_policy" in document:
        raise SystemExit("the all-nodes-think arm declares no thinking_policy")
    document["what_this_is"] = f"{ROLE_TEXT[key]} " + WHAT_THIS_IS
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode.get("review_loop"), episode.get("max_revisions")) != ("off", 0):
        raise SystemExit("the Thinking system cell must run the Reviewer loop off")
    # Preflight fit: the model-free preflight counts the JSON payload at 4 bytes per token (a placeholder) and refuses a fit the wire has at the
    # 4,096 cap; the cell defers to the registered exact per-contact gate, exactly as the 268-B cells do (coordinator finding 2026-10-12).
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
            "moved_leaves": moved, "loader_verification": dv.loader_verification(block, document, repo_root)}


def budgets(key: str) -> tuple[dict, dict]:
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
            "planned_speech_audio_seconds": audio, "split_role": fam.SPLIT_ROLE}
    return family, plan


def readiness_requirements(key: str, parent_cell: Mapping[str, Any]) -> list[dict]:
    """The decision receipt, the parent's DEV agreement-table requirement (byte for byte) and the cell's OWN first-phase supply (zero sha)."""

    spec = fam.CELLS[key]
    decision = {"kind": "decision", "expected_decision_id": fam.DECISION_ID, "relpath": fam.DECISION_RELPATH, "sha256": "0" * 64,
                "reason": f"Decision {fam.DECISION_ID} pinned by scripts/flights/repin_cell.py."}
    agreement = next(r for r in parent_cell["readiness"]["requirements"] if r["relpath"].endswith("DEV2000-ADDED-V1/agreement.jsonl"))
    supply = {"kind": "preparation", "relpath": f"prepared/{spec['run']}/phase-supply-v1.json", "sha256": "0" * 64,
              "reason": ("This cell's OWN prepared first-phase Perception supply, built model-free under its own run id with core.flight.cli "
                         "prepare-supply at the flip from the sealed DEV-2000-ADDED speech-query segment vectors, the centroid key file "
                         "SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1 and the DEV-2000-ADDED agreement table (item E16). --allow-output-change must "
                         "never be passed.")}
    return [decision, agreement, supply]


def derive_experiment(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    spec = fam.CELLS[key]
    smoke = key == "smoke"
    parent_exp = fam.parent_names(spec["parent_kind"])["experiment"]
    raw = rd(f"configs/experiment/{parent_exp}.json", repo_root)
    document = json.loads(substitute(raw, spec["slug"]))
    parent_doc = json.loads(raw)
    parent_cell = parent_doc["cells"][0]
    cell = document["cells"][0]
    if cell["cell_id"] != spec["cell"] or cell["run_id"] != spec["run"] or cell["baseline_fragment"] != spec["baseline"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r} / {cell['baseline_fragment']!r}")
    roster = fam.roster_doc(spec["roster"])
    ids = [str(item["sample_id"]) for item in roster["items"]]
    if parent_doc.get("populations") and ids != [str(i) for i in parent_doc["populations"][0]["ids"]]:
        raise SystemExit(f"the {key} roster ids are not the parent cell's population ids, in order")
    if len(ids) != spec["rows"]:
        raise SystemExit(f"{fam.ROSTER[spec['roster']]} has {len(ids)} rows, expected {spec['rows']}")
    split_hash = roster["split_identity_hash"]
    if split_hash != parent_doc["population"]["split_identity_hash"]:
        raise SystemExit(f"the {key} split identity differs from the parent's")
    rows = spec["rows"]
    calls = fam.generation_calls(key)
    family, plan = budgets(key)
    document["date"] = fam.DATE
    document["experiment_id"] = spec["run"]
    document["execution_plan"], document["family_budget"] = plan, family
    document["fragment_kind"] = f"saea-{cell['cell_id']}"
    document["service_session"] = spec["session"]
    # Native role contacts REQUIRE preserved wire metadata (reproduction.ojw.native_roles._wire_turn): the module graph cannot run with False.
    document["preserve_wire_responses"] = True
    document["stage3_algorithm"] = {
        "id": "shared-rollout", "operators_used": ["rollout", "scoring"],
        "note": ("The P3.1 replicate: ONE rollout of the locked system on the Thinking core (and its twin) on DEV-2000-ADDED, scored once with the "
                 "official scorer. No update operator, no selection and no benefit claim of its own: it replicates the 268-B Fold B transfer on a "
                 "fresh dev roster before any lock.")}
    document["split_id"] = fam.SPLIT_ID
    document["population"] = {
        "count": rows, "dataset_fragment": fam.DATASET, "roster_receipt": parent_doc["population"].get("roster_receipt"),
        "split_identity_hash": split_hash,
        "decision_population": (
            f"DEV-2000-ADDED ({fam.READ_ROSTER}): the first {rows} rows of {fam.ROSTER[spec['roster']]} (split identity {split_hash}); "
            + ("structural form proof only, no score and no read: exactly the four rows the sealed Instruct column's own smoke flew." if smoke else
               "dev role, rollout-exposed, never a test claim (owner decisions 28 and 86); the roster the sealed Instruct NX R5 composed cell flew, "
               "so the contrast is paired per row. TRAIN Fold A/B, DEV-1000 and the test split stay untouched and unread."))}
    document["populations"] = [{"dataset_fragment": fam.DATASET, "ids": ids}]
    cell.update(attempt_id=spec["attempt"], model_fragment=spec["model"],
                allowed_execution_stages=["check", "prepare-supply", "worker"] + ([] if smoke else ["campaign"]))
    document["generation_budget"] = {
        "cap": calls, "target": calls,
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {fam.PROGRAM}: {rows:,} x "
            f"{fam.CONTACTS_PER_ROW} = {rows * fam.CONTACTS_PER_ROW:,} is the exact program maximum; the plan ceiling adds {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only "
            f"fallback contacts per row (core.reasoning_knobs): {calls:,} = {rows:,} x {fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}. The live phase fit makes {rows} x "
            f"{fam.CONTACTS_PER_ROW} x {tf.FIT_ENDPOINTS_PER_CONTACT} = {fam.fit_contact_cap(rows):,} tokenizer endpoint calls under its own run id "
            f"{spec['fit_run']}. The GPU-hour ceiling is a BOUND (rows / {fam.MEASURED_ROWS_PER_MINUTE} rows per minute measured at np4 / 60 x "
            f"{fam.GPU_MARGIN}, ceil 0.1), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id.")}
    out = f"configs/experiment/{spec['cell']}.json"
    cell["readiness"] = {
        "reason": (f"{ROLE_TEXT[key]} Registered before contact on {fam.DATE} by script (decision 58) from the sealed Instruct NX R5 composed cell on "
                   "DEV-2000-ADDED and the module compiler (registry P3.1)." + HELD),
        "requirements": readiness_requirements(key, parent_cell), "state": "held"}
    if (repo_root / out).is_file():
        # Re-derivation after the flip keeps the cell's readiness block (state, reason, pinned receipts): the flip's re-pin owns it.
        cell["readiness"] = json.loads(rd(out, repo_root))["cells"][0]["readiness"]
    if smoke:
        document["purpose"] = (
            f"Four-row structural form smoke of the P3.1 replicate: that {fam.PROGRAM} (ceiling {fam.CONTACTS_PER_ROW}) loads on the Thinking session "
            f"({fam.THINK_SESSION}), that the DEV Thinking speech packets resolve under the native module graph, that --reasoning-format deepseek keeps "
            "reasoning out of the delivered content, that the live phase fit passes at the 4,096-token completion cap, that the seal works and that "
            "the episode completes, and what a Thinking contact costs per node (completion tokens, seconds, cap hits, empty completions, "
            "compaction). Scored by no one and read by no one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops the cell "
            "and the arms do not open. The smoke is re-flown whole at most once under one root-diagnosed recovery re-registration; a second "
            "failure closes the cell and the fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"{spec['run']}: the {spec['role']} of the P3.1 replicate on DEV-2000-ADDED 1,000 (registry 'P3 programme under decision 299 A'): does the "
            f"268-B Fold B transfer (SLU +{fam.FOLD_B_DELTA_SLU_PP} pp, intent +{fam.FOLD_B_DELTA_INTENT_PP} pp over the Instruct system) replicate on a fresh dev roster? "
            "The Thinking system arm is read against the sealed Instruct NX R5 composed column (same roster, same system, a different core) at "
            "the cross-flight contrast, with the in-chain twin as the A/A replicate. claims_benefit is false: a replicate that may NOMINATE the "
            "Thinking system as the SLURP lock candidate v3.0, not an admission. Development numbers only (owner decisions 28 and 86); never a "
            "test claim. Nothing here authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, "
            "geometry or cap change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation attempt id AND a new "
            "native_contact_fit run and attempt id); a second failure closes the cell and the fix is proven on a four-row dry run. A response "
            "whose delivered content carries a reasoning marker is a failure of the read, not of a row: it stops the flight "
            "(reasoning_content_guard). A partial manifest is never scored and never read.")
    document["core_read_design"] = {
        "arms": {k: fam.CELLS[k]["run"] for k in fam.ARM_KEYS},
        "chain": "swap to the Thinking session -> smoke -> coordinator sign-off -> lock arm -> twin aa -> swap back to the Instruct session",
        "reading": ("official SLU-F1 paired per row: Thinking system arm minus the sealed Instruct NX R5 composed column (cross-flight), the "
                    "twin offset as the A/A, and the Thinking system arm minus the bare Instruct core (B6 direct arm) for orientation"),
        "this_cell": spec["role"],
    }
    leftovers = [m.group(0) for m in re.finditer(r".{40}(?:nx-r5|NX-R5|NX_R5|NX R5 composed cell|r5-composed).{20}", json.dumps(document))]
    leftovers = [text for text in leftovers if "sealed Instruct" not in text and "NX R5 composed" not in text]
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


def derive(*, repo_root: Path = REPO_ROOT, write: bool = True, require_receipt: bool = False) -> dict:
    out: dict[str, Any] = {"cells": {}, "_documents": {}}
    for key in fam.ALL_KEYS:
        baseline = derive_baseline(key, repo_root=repo_root, write=write, require_receipt=require_receipt)
        experiment = derive_experiment(key, repo_root=repo_root, write=write)
        out["cells"][key] = {"baseline": baseline["path"], "experiment": experiment["path"], "loader_verification": baseline["loader_verification"],
                             "moved_leaves": baseline["moved_leaves"]}
        out["_documents"][key] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
        out["program"], out["ceiling"] = baseline["program"], baseline["ceiling"]
    out["campaigns"] = [write_campaign(key, repo_root=repo_root, write=write) for key in fam.ARM_KEYS]
    out["receipt"] = fam.receipt_state()
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="derive and verify in memory; write nothing")
    parser.add_argument("--require-receipt", action="store_true", help="refuse unless DEV-2000-ADDED-promotion.json exists (pins its real sha256)")
    args = parser.parse_args(argv)
    result = derive(write=not args.dry_run, require_receipt=args.require_receipt)
    result.pop("_documents", None)
    if not result["receipt"]["present"]:
        print("WARNING: the DEV Thinking promotion receipt is absent; the baselines carry the zero sentinel and every consumer fails closed", file=sys.stderr)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
