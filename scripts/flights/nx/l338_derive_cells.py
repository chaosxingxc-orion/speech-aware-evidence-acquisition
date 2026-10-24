#!/usr/bin/env python3
"""Derive the two cells of L338 (config only): the decision-338 LEVER column (L1 false-fill suppression, L2 Perception candidate union) on the Thinking core, TRAIN Fold B.

WHAT THE CELLS ARE. The 268-B Thinking lock cell -- the loop's plain lock (lock v2.2 + the v4g post-processing, the review-off COMP-1b module graph, no supply arm) on
the Thinking core -- with exactly ONE addition: the Perception role's ``sampling_variants`` block (a level-2 Perception-branch group), compiled by the consumption module's
``sampling`` column kind from the data-driven arm table ``l338_arms.json`` (candidate arms ``l1-support`` = ``solver_samples`` and ``l2-union`` = ``perception_samples``, the
twin ``aa`` and the delivering arm ``lock`` LAST). The program grows from ``phase-native-module-v1-c2`` to ``phase-native-module-v1-c<2 + 2 (K - 1) + (k - 1) + (n - 1)>``
(c15). The serving fragment is the RESIDENT np4 Thinking fragment (budget 3,072 / cap 4,096): there is no new fragment and no cell-level thinking policy, because the
fragment's own defaults are the lock form. The Thinking packets and their promotion receipt, the knowledge supply, the sealed Fold B speech-query vectors, the agreement table,
the centroid keys and the roster are the 268-B cell's, byte for byte. Nothing is hand-edited: every baseline is the 268-B parent plus the compiler's output plus the registered
diff, and the script refuses a leaf that moved beyond :data:`MOVED_LEAF_RULES`. The result carries ``moved_leaves`` per cell.

The derive REFUSES unless the live 24,576-token slot holds the lock's Solver prompt plus the 4,096-token cap (``l338_family.fit_proof``) and EMITS the
machine sign-off conditions for this arm table inside the package.

Cells: ``smoke`` (the loop's own four Fold B rows) and ``arm`` (the 1,080-row column flight). CONFIG ONLY: no contact, no ledger row, no receipt, no flip. Both cells
are HELD.

    python -B scripts/flights/nx/l338_derive_cells.py [--dry-run]
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

import l338_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

#: The STRICT registered diff against the 268-B parent: every moved leaf of a baseline must match exactly one of these rules, so the derive proves that only the Solver
#: ``decoding_variants`` block (and its declaration), the program id (the ceiling is its ``-c<N>`` suffix), the live-fit ids/cap, the cell's own first-phase supply pin
#: and the cell text move. A leaf outside the rules refuses the derive (``stray``).
MOVED_LEAF_RULES = (
    ("the Perception sampling_variants block", re.compile(r"native_episode\.roles\.perception\.sampling_variants(\..+)?")),
    ("its declaration in consumption_module", re.compile(r"native_episode\.consumption_module\.(columns|sampling_frame(\..+)?)")),
    ("the program id and ceiling", re.compile(r"policy")),
    ("the live-fit ids and cap", re.compile(r"native_contact_fit\.(run_id|attempt_id|contact_cap)")),
    ("the cell's own first-phase supply pin", re.compile(r"prepared_phase_supply(\..+)?")),
    ("the cell text", re.compile(r"what_this_is")),
)


def classify_moved(moved: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    """Group the moved leaves by the registered rule that admits them; the second value lists the stray ones."""

    grouped: dict[str, list[str]] = {name: [] for name, _ in MOVED_LEAF_RULES}
    stray: list[str] = []
    for leaf in moved:
        for name, pattern in MOVED_LEAF_RULES:
            if pattern.fullmatch(leaf):
                grouped[name].append(leaf)
                break
        else:
            stray.append(leaf)
    return grouped, stray


WHAT_THIS_IS = (
    "Cell L338 (owner rulings 338 and 341 A: the lever column): the 268-B Thinking system -- the locked SLURP system (lock v2.2 + v4g, review-off module graph, program "
    "phase-native-module-v1-c2 as the base) on the Thinking core -- with a same-flight COLUMN of two sampling levers. The Perception role carries "
    "roles.perception.sampling_variants (a level-2 Perception-branch group: each branch is its own Perception and first-visit Solver visit): candidate arms "
    + ", ".join(fam.CANDIDATE_ARMS) + " (l1-support fans out solver_samples: n = 5 Solver contacts, sample 0 greedy at the lock seed, samples 1-4 at temperature 0.6 / top_p 0.95 / top_k 20 with "
    "seed = lock seed + offset, committed by saea-commit-first-support-v1; l2-union fans out perception_samples: k = 4 Perception contacts merged by "
    "saea-perception-candidate-union-v1 into the Solver's shortlist, capped at 3), the in-chain twin " + fam.TWIN + " (replicate_of " + fam.DELIVERING + ") and the delivering arm "
    + fam.DELIVERING + " (no axis, LAST; its requests are the lock's byte for byte). Every arm renders the lock's templates, evidence and "
    "QueryState and carries the lock's per-node thinking fields (budget 3072, cap 4096; the serving fragment's defaults are that form, so there is no cell-level "
    "thinking_policy); arm_visits is first. Program " + fam.PROGRAM + f": 2 + 2 ({fam.K} - 1) + sampling extras = {fam.CONTACTS_PER_ROW} contacts per row ({fam.PERCEPTION_CONTACTS_PER_ROW} Perception + "
    f"{fam.SOLVER_CONTACTS_PER_ROW} Solver). Every policy block is the module compiler's output."
)

ROLE_TEXT = {
    "smoke": ("Four-row form smoke of the lever column: it proves that the " + fam.PROGRAM + " module program with " + str(fam.K) + " sampling arms loads on the resident "
              "np4 Thinking session, that every sampled contact carries the lock's thinking budget 3072 and max_tokens 4096, its sample index, its derived seed and the arm's "
              "decoding, that the merge and commit results land in the v6 receipt, that the live phase fit passes, that no node hits its cap, and what a contact costs per "
              "arm (completion tokens, finish reasons, forced closes, seconds) against the registered cost."),
    "arm": "The lever-column flight of L338: " + str(fam.K) + " arms over the same 1,080 Fold B rows in one flight.",
}

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/nx/l338_mint_receipt.py), the chain swaps to the resident np4 Thinking session "
    "(scripts/flights/batch/serving_swap.sh " + fam.SWAP_TARGET + ", a no-op when it is resident) and the cells are flipped with scripts/flights/batch/flip_package_ext4.sh "
    "through scripts/flights/nx/l338_flip.sh, which also mints each cell's own first-phase supply under its own run id (item E16); --allow-output-change must "
    "never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return dv.rd(path, root)


def same_json(path: str, document: Mapping[str, Any], root: Path = REPO_ROOT) -> bool:
    """True when the file on disk already holds exactly this document (key order aside): an unchanged cell is not rewritten, so a recovery of one cell
    leaves the other cell's committed bytes alone."""

    target = Path(root) / path
    return target.is_file() and json.loads(target.read_text(encoding="utf-8")) == document


def parent_stem(key: str) -> str:
    cell = fam.CELLS[key]["parent_cell"]
    return cell[len("slurp-native-stage3-"):-len("-v1")]


def own_stem(key: str) -> str:
    cell = fam.CELLS[key]["cell"]
    return cell[len("slurp-native-stage3-"):-len("-v1")]


def substitute(text: str, key: str) -> str:
    old, new = parent_stem(key), own_stem(key)
    return text.replace(old, new).replace(old.upper(), new.upper())


def sampling_columns() -> list[dict]:
    return [{"column_id": a["arm_id"], "kind": "sampling", "node": "perception", a["axis"]: json.loads(json.dumps(a[a["axis"]]))} for a in fam.ARM_SPECS]


def module_block(parent: Mapping[str, Any]) -> dict:
    """The 268-B plain-lock block with the arm table's sampling columns and the sampling frame added (the twin, then the delivering arm, are added by the compiler)."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (fam.LOCK, "off") or block.get("columns") != []:
        raise SystemExit(f"the parent's module block is not the plain review-off lock {fam.LOCK} with no columns")
    block["columns"] = sampling_columns()
    block["sampling_frame"] = {"max_supplied_items": fam.MAX_SUPPLIED_ITEMS, "twin": True, "fit_estimate": dict(fam.SAMPLING_FIT_ESTIMATE)}
    return block


def derive_baseline(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    spec = fam.CELLS[key]
    raw = rd(f"configs/baseline/{spec['parent_baseline']}.json", repo_root)
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
    if document.get("speech_packet_promotion_receipt") != fam.THINK_PROMOTION_RECEIPT:
        raise SystemExit("the parent does not pin the Thinking packet root's promotion receipt")
    if document.get("speech_packet_promotion_receipt_sha256") != fam.thinking_promotion_sha256():
        raise SystemExit("the parent's promotion receipt sha256 is not the Thinking baseline's pin")
    if "thinking_policy" in parent or "thinking_policy" in document:
        raise SystemExit("the R4 cell carries no thinking_policy: the resident fragment's defaults are the lock form")
    document["what_this_is"] = f"{ROLE_TEXT[key]} " + WHAT_THIS_IS
    rec = fam.recovery(key)
    if rec:
        document["what_this_is"] += f" Recovery rec{rec['recovery_index']} ({rec['recovered_at']}): {rec['root_cause']}."
        if rec.get("owner_exception"):
            document["what_this_is"] += (f" The rec{rec['recovery_index']} re-registration stands under an explicit owner exception ({rec['owner_exception']}) to the "
                                         f"one-recovery rule and is a {rec['resume_mode']} resume of {rec['predecessor_attempt_id']}.")
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode.get("review_loop"), episode.get("max_revisions")) != ("off", 0):
        raise SystemExit("the lever-column cell must run the Reviewer loop off")
    if document.get("preflight_budget_mode") != "defer-to-native-contact-fit":
        raise SystemExit("preflight_budget_mode must stay defer-to-native-contact-fit (the exact per-contact gate decides the fit)")
    roles = episode["roles"]
    if ("sampling_variants" not in roles.get("perception", {}) or "supply_variants" in json.dumps(roles) or "thinking_variants" in json.dumps(roles)
            or "template_variants" in json.dumps(roles) or "decoding_variants" in json.dumps(roles)):
        raise SystemExit("the cell carries exactly the Perception sampling_variants block (no supply, template, thinking or decoding arms)")
    if sorted(arm["arm_id"] for arm in roles["perception"]["sampling_variants"]["arms"]) != sorted(fam.ARM_ORDER):
        raise SystemExit("the compiled sampling_variants arms are not the arm table's arms")
    fragment = json.loads(rd(f"configs/model/{spec['model']}.json", repo_root))
    lock_decoding = {k: v for k, v in fragment.get("decoding_params", {}).items() if k in fam.LOCKED_DECODING}
    if lock_decoding != fam.LOCKED_DECODING:
        raise SystemExit(f"the Thinking fragment's request decoding {lock_decoding} is not the arm table's locked_decoding {fam.LOCKED_DECODING}")
    left, right = dv._leaves(parent), dv._leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    moved_by_rule, stray = classify_moved(moved)
    if stray:
        raise SystemExit(f"leaves moved beyond the registered diff: {stray[:12]}")
    if write and not same_json(out, document, repo_root):
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document, "block": block, "program": composed.program_id, "ceiling": composed.program_ceiling,
            "moved_leaves": moved, "moved_by_rule": moved_by_rule, "loader_verification": dv.loader_verification(block, document, repo_root)}


def budgets(key: str, repo_root: Path = REPO_ROOT) -> tuple[dict, dict]:
    spec = fam.CELLS[key]
    rows = spec["rows"]
    calls = fam.generation_calls(key)               # a recovered cell: the original plan plus the failed attempts' realised spend (run-cumulative)
    audio = fam.cell_audio_cap(key)
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
    raw = rd(f"configs/experiment/{spec['parent_cell']}.json", repo_root)
    document = json.loads(substitute(raw, key))
    parent_cell = json.loads(raw)["cells"][0]
    cell = document["cells"][0]
    if cell["cell_id"] != spec["cell"] or cell["run_id"] != spec["run"] or cell["baseline_fragment"] != spec["baseline"]:
        raise SystemExit(f"id rewrite produced {cell['cell_id']!r} / {cell['run_id']!r} / {cell['baseline_fragment']!r}")
    roster = fam.roster_doc(spec["roster"])
    ids = [str(item["sample_id"]) for item in roster["items"]]
    if len(ids) != spec["rows"]:
        raise SystemExit(f"{fam.ROSTER[spec['roster']]} has {len(ids)} rows, expected {spec['rows']}")
    rows = spec["rows"]
    calls = fam.original_generation_calls(key)      # the first-attempt arithmetic below; the cap itself is cumulative for a recovered cell
    family, plan = budgets(key, repo_root)
    document["date"] = fam.DATE
    document["experiment_id"] = spec["run"]
    document["execution_plan"], document["family_budget"] = plan, family
    document["fragment_kind"] = f"saea-{cell['cell_id']}"
    document["service_session"] = spec["session"]
    document["preserve_wire_responses"] = True
    document["stage3_algorithm"] = {
        "id": "none", "operators_used": [],
        "note": ("This cell carries NO training-free RL operator and says so explicitly: it is a same-flight node column of the NX instrument "
                 f"(L338) -- {len(fam.CANDIDATE_ARMS)} hand-written candidate sampling levers (a Solver sample-and-commit and a Perception sample-and-merge) and an in-flight twin read as columns against the delivering "
                 f"{fam.DELIVERING} arm (the 268-B lock form) -- with no rollout pool, no per-sample credit, no update operator and no evolving store.")}
    document["split_id"] = fam.SPLIT_ID
    document["population"] = {
        "count": rows, "dataset_fragment": fam.DATASET, "roster_receipt": fam.ROSTER[spec["roster"]],
        "split_identity_hash": roster["split_identity_hash"],
        "decision_population": (
            f"TRAIN Fold B ({roster['roster_id']}): {rows} rows of {fam.ROSTER[spec['roster']]}"
            + ("; four of its rows, structural form proof only, no score and no read." if smoke else
               "; discovery role, rollout-exposed, never a test claim (owner decisions 28 and 86); the roster of the 268-B read, so the delivering arm "
               "is also comparable cross-flight to the 268-B lock arm."))}
    document["populations"] = [{"dataset_fragment": fam.DATASET, "ids": ids}]
    cell.update(attempt_id=spec["attempt"], model_fragment=spec["model"],
                allowed_execution_stages=["check", "prepare-supply", "worker"] + ([] if smoke else ["campaign"]))
    recovery_record = fam.recovery(key)
    if recovery_record and recovery_record.get("resume_from"):
        # rec2: a resume of the stopped rec1 attempt; the pin (checkpoint sha256 = mode B, trace sha256 = mode A) is read from the data root into the snapshot receipt
        cell["resume_from"] = dict(recovery_record["resume_from"])
    else:
        cell.pop("resume_from", None)
    document["generation_budget"] = {
        "cap": plan["planned_model_calls"], "target": plan["planned_model_calls"],
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {fam.PROGRAM} with the {fam.K}-arm "
            f"sampling column: {rows:,} x {fam.CONTACTS_PER_ROW} = {rows * fam.CONTACTS_PER_ROW:,} is the exact program maximum (2 + 2 (K - 1) + (k - 1) + (n - 1), K = {fam.K}); "
            f"the plan ceiling adds {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only fallback contacts per row (one per budgeted-thinking contact: {fam.PERCEPTION_CONTACTS_PER_ROW} Perception + "
            f"{fam.SOLVER_CONTACTS_PER_ROW} Solver contacts, core.reasoning_knobs): {calls:,} = {rows:,} x {fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}. The live phase fit "
            f"makes {rows} x {fam.CONTACTS_PER_ROW} x {tf.FIT_ENDPOINTS_PER_CONTACT} = {fam.fit_contact_cap(rows):,} tokenizer endpoint calls under its own run id "
            f"{spec['fit_run']}. The GPU-hour ceiling is a BOUND (rows x {fam.ARM_MIX_ROWS} lock-row equivalents / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 x "
            f"{fam.GPU_MARGIN}, ceil 0.1), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id.")}
    rec = fam.recovery(key)
    if rec:
        # prose only: the cap above is the cumulative one (the original ceiling plus the failed attempts' realised spend)
        spent_calls, spent_audio = fam.predecessor_spend(key)
        if rec["recovery_index"] == 1:
            document["generation_budget"]["definition"] += (
                f" Recovery rec1 (the cell's single one; a second failure closes the cell): the failed predecessor attempt {rec['predecessor_attempt_id']} spent "
                f"{spent_calls:,} contacts and {spent_audio:g} speech-seconds, so the run-cumulative budget is the original plan plus that spend: "
                f"{plan['planned_model_calls']:,} calls, {plan['planned_speech_audio_seconds']:,} speech-seconds.")
        else:
            counts = rec["resume_counts"]
            document["generation_budget"]["definition"] += (
                f" Recovery rec{rec['recovery_index']} ({rec['owner_exception']}, an explicit exception to the one-recovery rule; a second failure closes the cell): the "
                f"earlier attempts spent {spent_calls:,} contacts and {spent_audio:g} speech-seconds, so the run-cumulative budget is {plan['planned_model_calls']:,} calls, "
                f"{plan['planned_speech_audio_seconds']:,} speech-seconds. THIS ATTEMPT keeps {counts['kept']:,} complete rows of the stopped attempt and flies {counts['flown']:,}.")
    out = f"configs/experiment/{spec['cell']}.json"
    cell["readiness"] = {
        "reason": (f"{ROLE_TEXT[key]} Registered before contact on {fam.DATE} by script (decision 58) from the 268-B Thinking lock cell and the module "
                   f"compiler ({fam.OWNER_RULINGS})." + HELD),
        "requirements": readiness_requirements(key, parent_cell), "state": "held"}
    if (repo_root / out).is_file():
        # Re-derivation after the flip keeps the cell's readiness block (state, reason, pinned receipts): the flip's re-pin owns it.
        cell["readiness"] = json.loads(rd(out, repo_root))["cells"][0]["readiness"]
    if smoke:
        document["purpose"] = (
            f"Four-row structural form smoke of L338: that {fam.PROGRAM} (ceiling {fam.CONTACTS_PER_ROW}) with the {fam.K}-arm sampling column loads on the "
            f"resident np4 Thinking session ({spec['session']}), that every sampled Perception and Solver contact carries the lock's thinking budget {fam.DELIVERING_BUDGET} with max_tokens "
            f"{fam.COMPLETION_CAP}, its sample index, its derived seed and the arm's decoding while the delivering arm's request is the lock's, that no node hits its own cap, that no delivered content "
            "carries a think marker, that the live phase fit passes, that the v6 arm receipt seals and that the episode completes, and what a contact costs per arm "
            "(completion tokens, finish reasons, forced closes, seconds) against the registered cost. Scored by no one and read by no one: four rows are never evidence "
            "of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops the cell and the "
            "column flight does not open. The smoke is re-flown whole at most once under one root-diagnosed recovery re-registration; a second failure closes "
            "the cell and the fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"{spec['run']}: do the two sampling levers move the score of the locked Thinking system -- L1 false-fill suppression (n = 5 Solver samples, first-first support filter, N1-gated empty decision) judged on SLU with an intent guard, and L2 the Perception candidate union (k = 4 samples, cap 3) judged on intent with an SLU guard (owner rulings 338 and 341 A)? "
            f"One flight, {fam.K} arms over TRAIN Fold B 1,080: the delivering {fam.DELIVERING} arm (the 268-B lock form), the in-chain twin {fam.TWIN} and the candidate arms "
            + ", ".join(fam.CANDIDATE_ARMS) + f". Each candidate is read PAIRED per row against {fam.DELIVERING} (official SLU-F1 primary, intent guard; utterance-cluster bootstrap CI95), "
            f"beside the twin {fam.TWIN} (the in-flight A/A), the support-count and union-size tables, the per-stream discordance against the twin, empty-gold false fill and the per-scenario "
            "table. claims_benefit is false: a per-arm nomination, not an admission; development numbers only (owner decisions 28 and 86); never a test claim. A NOMINATED "
            "arm goes to the 335 B Fold A column (not built here). Nothing here authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, geometry or cap "
            "change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation attempt id AND a new native_contact_fit run and attempt "
            "id); a second failure closes the cell and the fix is proven on a four-row dry run. A response whose delivered content carries a reasoning "
            "marker is a failure of the read, not of a row: it stops the flight (reasoning_content_guard). A partial manifest is never scored and never read.")
        if recovery_record and recovery_record.get("owner_exception"):
            document["failure_policy"] += (f" EXPLICIT OWNER EXCEPTION ({recovery_record['owner_exception']}): this cell carries a SECOND recovery re-registration "
                                           f"(rec{recovery_record['recovery_index']}); the exception covers that one re-registration only, and a failure of it closes the cell.")
    document["core_read_design"] = {
        "arms": {arm: spec["run"] for arm in fam.ARM_ORDER},
        "chain": "resident np4 Thinking session (swap is a no-op) -> smoke -> machine sign-off (coordinator veto window) -> the column flight",
        "reading": (f"official SLU-F1 and intent paired per row: {', '.join(fam.CANDIDATE_ARMS)} and the twin {fam.TWIN} minus the delivering {fam.DELIVERING} arm, beside "
                    "the per-stream discordance, support-count, union-size, empty-gold false-fill, seconds-per-contact and per-scenario tables"),
        "this_cell": spec["role"],
    }
    leftovers = [m.group(0) for m in re.finditer(r".{40}(?:thinking-system|THINKING-SYSTEM|owner decision 268|Thinking system arm).{20}", json.dumps(document))]
    if leftovers:
        raise SystemExit(f"inherited parent identity text survived the rewrite ({key}): {leftovers[:3]}")
    if write and not same_json(out, document, repo_root):
        dv.wr(out, dv.dump_like(raw, document), repo_root)
    return {"path": out, "document": document}


def write_campaign(key: str, *, repo_root: Path = REPO_ROOT, write: bool = True) -> str:
    spec = fam.CELLS[key]
    plan = {"cells": [{"cell": spec["cell"], "experiment": spec["cell"]}], "schema": "saea-campaign-plan-v1"}
    if write:
        dv.wr(spec["campaign"], json.dumps(plan, indent=2, sort_keys=True) + "\n", repo_root)
    return spec["campaign"]


def signoff_conditions_text() -> str:
    return json.dumps(fam.signoff_conditions(), indent=2, sort_keys=True) + "\n"


def write_signoff_conditions(*, repo_root: Path = REPO_ROOT, write: bool = True) -> str:
    """Emit the machine sign-off conditions for THIS arm table inside the package directory (regenerated whenever the table changes; idempotent)."""

    path = Path(repo_root) / fam.SIGNOFF_CONDITIONS
    text = signoff_conditions_text()
    if write and (not path.is_file() or path.read_text(encoding="utf-8") != text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return fam.SIGNOFF_CONDITIONS


def derive(*, repo_root: Path = REPO_ROOT, write: bool = True) -> dict:
    fit = fam.fit_proof()
    if not fit["ok"]:
        failed = [name for name, ok in fit["checks"].items() if not ok]
        raise SystemExit(f"the live {fit['slot_tokens']}-token slot does not hold the lock's Solver prompt plus the {fit['completion_cap']}-token cap: failed "
                         f"{failed} (prompt limit {fit['prompt_limit_tokens']}, observed Solver prompt maximum {fit['observed_solver_prompt_tokens_max']})")
    out: dict[str, Any] = {"cells": {}, "_documents": {}}
    for key in fam.ALL_KEYS:
        baseline = derive_baseline(key, repo_root=repo_root, write=write)
        experiment = derive_experiment(key, repo_root=repo_root, write=write)
        out["cells"][key] = {"baseline": baseline["path"], "experiment": experiment["path"], "moved_leaves": baseline["moved_leaves"],
                             "moved_by_rule": baseline["moved_by_rule"], "loader_verification": baseline["loader_verification"]}
        out["_documents"][key] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
        out["program"], out["ceiling"] = baseline["program"], baseline["ceiling"]
    out["campaigns"] = [write_campaign(key, repo_root=repo_root, write=write) for key in fam.ARM_KEYS]
    out["fit"] = fit
    out["signoff_conditions"] = write_signoff_conditions(repo_root=repo_root, write=write)
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
