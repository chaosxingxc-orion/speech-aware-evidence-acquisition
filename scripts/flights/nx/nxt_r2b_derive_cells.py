#!/usr/bin/env python3
"""Derive the two cells of NX-T R2b (config only): the Solver REASONING-BUDGET raise on the Thinking core, TRAIN Fold B.

WHAT THE CELLS ARE. The 268-B Thinking lock cell -- the loop's plain lock (lock v2.2 + the v4g post-processing, the review-off COMP-1b module graph, no
supply arm) on the Thinking core -- with exactly TWO additions: (1) the Perception role's ``thinking_variants`` block, compiled by the consumption module's
``thinking`` column kind from the data-driven arm table ``nxt_r2b_arms.json`` (ONE candidate arm ``solver-6144`` -- Solver budget 6,144, answer reserve 1,024, cap
7,168 -- then the delivering arm ``budget-3072`` LAST; NO twin, owner decisions 313 A and 325 A); (2) a CELL-LEVEL ``thinking_policy`` that states the lock form (budget
3,072 + reserve 1,024 = cap 4,096) on BOTH nodes, because the serving fragment ``...-budget3072-max7168-v1`` carries the geometry cap 7,168 as its default. The program
grows from ``phase-native-module-v1-c2`` to ``phase-native-module-v1-c<2 + 2 (K - 1)>`` (c4). The Thinking packets and their promotion receipt, the knowledge supply, the
sealed Fold B speech-query vectors, the agreement table, the centroid keys and the roster are the 268-B cell's, byte for byte. Nothing is hand-edited: every baseline is
the 268-B parent plus the compiler's output plus the registered diff, and the script refuses a leaf that moved beyond :data:`ALLOWED_DIFFS`. The result carries
``moved_leaves`` per cell: the proof that only the ``thinking_variants`` block (and its declaration in ``consumption_module``), the cell-level thinking policy, the program
id and ceiling leaves, the live-fit ids and the cell text moved.

The derive REFUSES unless the live 24,576-token slot holds the Solver prompt plus the 7,168-token cap (``nxt_r2b_family.fit_proof``), proves that the new serving fragment
differs from the resident np4 fragment ONLY in the geometry-cap leaves (the server arguments, runtime receipt and speech packet root are identical), and EMITS the machine
sign-off conditions for this arm table inside the package.

Cells: ``smoke`` (the loop's own four Fold B rows) and ``arm`` (the 1,080-row column flight). CONFIG ONLY: no contact, no ledger row, no receipt, no
flip. Both cells are HELD.

    python -B scripts/flights/nx/nxt_r2b_derive_cells.py [--dry-run]
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

import nxt_r2b_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks  # noqa: E402

ALLOWED_DIFFS = (
    "policy", "native_episode.consumption_module", "native_episode.roles.perception.thinking_variants", "native_contact_fit",
    "prepared_phase_supply", "what_this_is", "thinking_policy",
)
#: The STRICT registered diff against the 268-B parent: every moved leaf of a baseline must match exactly one of these rules, so the derive proves that only the
#: ``thinking_variants`` block (and its declaration), the cell-level thinking policy, the program id (the ceiling is its ``-c<N>`` suffix), the live-fit ids/cap, the
#: cell's own first-phase supply pin and the cell text move. A leaf outside the rules refuses the derive (``stray``).
MOVED_LEAF_RULES = (
    ("the thinking_variants block", re.compile(r"native_episode\.roles\.perception\.thinking_variants(\..+)?")),
    ("its declaration in consumption_module", re.compile(r"native_episode\.consumption_module\.(columns|thinking_frame(\..+)?)")),
    ("the cell-level thinking policy (the lock form on both nodes)", re.compile(r"thinking_policy(\..+)?")),
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


def setting_text(setting: Mapping[str, int]) -> str:
    return f"reasoning budget {setting['budget_tokens']} (answer reserve {setting['completion_cap'] - setting['budget_tokens']}, cap {setting['completion_cap']})"


def arm_table_text() -> str:
    """One clause per declared candidate arm, from the arm table (so the cell text follows the data)."""

    parts = []
    for arm in fam.ARM_SPECS:
        nodes = []
        for node in fam.NODES:
            if arm[node] == fam.DELIVERING_SETTING:
                nodes.append(f"{node} thinking at the locked budget {fam.DELIVERING_BUDGET}")
            else:
                nodes.append(f"{node} {setting_text(arm[node])}")
        parts.append(f"{arm['arm_id']} ({', '.join(nodes)})")
    return "; ".join(parts)


WHAT_THIS_IS = (
    "Cell NXT-R2B (owner rulings 323 and 325 A: raise the Solver's reasoning budget and completion cap so Solver reasoning is no longer truncated): the 268-B Thinking "
    "system -- the locked SLURP system (lock v2.2 + v4g, review-off module graph, program phase-native-module-v1-c2 as the base) on the Thinking core -- with a same-flight "
    "COLUMN over the PER-NODE REASONING BUDGET AND COMPLETION CAP. The Perception role carries roles.perception.thinking_variants: arm " + arm_table_text() + "; and "
    + fam.DELIVERING + " (the delivering arm = the 268-B lock form on both nodes, budget 3072 + reserve 1024 = cap 4096, reasoning_context_policy drop-reasoning-v1; its "
    "requests are the lock's byte for byte). The serving fragment carries the geometry cap " + str(fam.FRAGMENT_CAP) + ", so a cell-level thinking_policy states the lock "
    "form on both nodes and the candidate arm overrides only its Solver. There is NO twin arm (owner decision 313 A) and ONE candidate arm (owner ruling 325 A). Every arm "
    "renders the delivering arm's evidence, template and QueryState; the arms differ only in the Solver's reasoning budget and cap, and an arm's Solver prompt is built from "
    "THAT arm's own Perception note (independent chains, no note sharing). Program " + fam.PROGRAM + f": 2 + 2 ({fam.K} - 1) = {fam.CONTACTS_PER_ROW} contacts per row. "
    "Every policy block is the module compiler's output."
)

ROLE_TEXT = {
    "smoke": ("Four-row form smoke of the Solver reasoning-budget raise: it proves that the " + fam.PROGRAM + " module program with " + str(fam.K) + " arms loads on the "
              "raised-cap Thinking session, that the delivering arm's requests carry the lock form (budget 3072, cap 4096) on both nodes, that the candidate arm's Solver "
              "request carries thinking_budget_tokens " + str(max(a['solver']['budget_tokens'] for a in fam.ARM_SPECS)) + " with max_tokens "
              + str(fam.FRAGMENT_CAP) + " and its Perception request is unchanged, that the live phase fit passes at the raised cap, that no node hits its cap, and what a "
              "contact costs per arm and per node (completion tokens, finish reasons, forced closes, seconds) against the registered cost."),
    "arm": "The Solver reasoning-budget raise column flight of NX-T R2b: " + str(fam.K) + " arms over the same 1,080 Fold B rows in one flight.",
}

HELD = (
    " HELD: root countersigns the DRAFT rows, mints the admission receipt (scripts/flights/nx/nxt_r2b_mint_receipt.py), swaps the serving geometry to the "
    "raised-cap Thinking session (scripts/flights/batch/serving_swap.sh " + fam.SWAP_TARGET + ") and flips the cells with scripts/flights/batch/flip_package_ext4.sh through "
    "scripts/flights/nx/nxt_r2b_flip.sh, which also mints each cell's own first-phase supply under its own run id (item E16); --allow-output-change must "
    "never be passed. Nothing here authorises a flight, a readiness flip or an admission entry."
)


def rd(path: str, root: Path = REPO_ROOT) -> str:
    return dv.rd(path, root)


def fragment_proof(repo_root: Path = REPO_ROOT) -> dict:
    """Prove that the raised-cap serving fragment moves ONLY the geometry-cap leaves against the resident np4 fragment, and that the np4 x 24,576 server geometry is
    unchanged (``max_tokens`` is a request parameter). Raises ``SystemExit`` on a stray leaf or a broken fragment invariant; returns the registered proof."""

    root = Path(repo_root)
    new = json.loads((root / "configs" / "model" / f"{fam.THINK_MODEL}.json").read_text(encoding="utf-8"))
    old = json.loads((root / "configs" / "model" / f"{fam.CONTROL_FRAGMENT}.json").read_text(encoding="utf-8"))
    left, right = dv._leaves(old), dv._leaves(new)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    stray = [k for k in moved if not any(k == p or k.startswith(p) for p in fam.GEOMETRY_LEAVES)]
    if stray:
        raise SystemExit(f"the raised-cap fragment differs from the resident np4 fragment beyond the geometry-cap leaves: {stray[:12]}")
    if new["server_args"] != old["server_args"] or new.get("runtime_receipt") != old.get("runtime_receipt") or new.get("server_env") != old.get("server_env"):
        raise SystemExit("the raised-cap fragment changed the server arguments, the runtime receipt or the server environment (the GPU geometry must not move)")
    if new["decoding_params"]["max_tokens"] != fam.FRAGMENT_CAP:
        raise SystemExit(f"fragment decoding max_tokens {new['decoding_params']['max_tokens']} is not the arm table's fragment cap {fam.FRAGMENT_CAP}")
    if new["reasoning_budget_tokens"] != fam.DELIVERING_BUDGET or new["answer_reserve_tokens"] != fam.FRAGMENT_CAP - fam.DELIVERING_BUDGET:
        raise SystemExit("the fragment invariant max_tokens = reasoning_budget_tokens + answer_reserve_tokens (3072 + cap - 3072) does not hold")
    args = new["server_args"]
    total, slots = int(args[args.index("-c") + 1]), int(args[args.index("-np") + 1])
    return {"target": fam.SWAP_TARGET, "session": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "reference_fragment": fam.CONTROL_FRAGMENT,
            "resolution": fam.ACTIVE_GEOMETRY["source"], "slots": slots, "slot_tokens": total // slots, "server_args_equal": True, "runtime_receipt": new.get("runtime_receipt"),
            "runtime_receipt_equal": True, "server_env_equal": True, "allowed_leaves": list(fam.GEOMETRY_LEAVES), "moved_leaves": moved, "stray_leaves": [], "ok": True,
            "note": ("max_tokens is a request parameter: the np4 / c98304 server geometry (four 24,576-token slots), its server arguments and its runtime receipt are the resident "
                     "Thinking session's, unchanged; the new session id exists only because the fragment's geometry cap (and with it the fragment hash) changed. Precedent: the "
                     "266-E direct flights served max_tokens 8,192 at this geometry (scripts/flights/direct/direct_fb_family.py THINK_MAX_TOKENS).")}


def same_json(path: str, document: Mapping[str, Any], root: Path = REPO_ROOT) -> bool:
    """True when the file on disk already holds exactly this document (key order aside): an unchanged cell is not rewritten, so a recovery of one cell
    leaves the other cell's committed bytes alone."""

    target = Path(root) / path
    return target.is_file() and json.loads(target.read_text(encoding="utf-8")) == document


def parent_stem(key: str) -> str:
    """The parent cell's id stem (``thinking-system-fold-b-lock`` / ``...-smoke-4``) the experiment text is rewritten from."""

    cell = fam.CELLS[key]["parent_cell"]
    return cell[len("slurp-native-stage3-"):-len("-v1")]


def own_stem(key: str) -> str:
    cell = fam.CELLS[key]["cell"]
    return cell[len("slurp-native-stage3-"):-len("-v1")]


def substitute(text: str, key: str) -> str:
    old, new = parent_stem(key), own_stem(key)
    return text.replace(old, new).replace(old.upper(), new.upper())


def thinking_columns() -> list[dict]:
    return [{"column_id": arm, "kind": "thinking", "node": "perception", "thinking_policy": json.loads(json.dumps(fam.POLICIES[arm]))}
            for arm in fam.CANDIDATE_ARMS]


def module_block(parent: Mapping[str, Any]) -> dict:
    """The 268-B plain-lock block with the arm table's thinking columns and the thinking frame added (NO twin; the frame names the delivering arm). The frame's fit estimate
    carries the 7,168 completion ceiling and the item bound the registered estimate admits at it (``fam.MAX_SUPPLIED_ITEMS``)."""

    block = copy.deepcopy(dict(parent["native_episode"][cm.CONSUMPTION_MODULE_CONFIG_KEY]))
    if (block.get("lock"), block.get("review_loop")) != (fam.LOCK, "off") or block.get("columns") != []:
        raise SystemExit(f"the parent's module block is not the plain review-off lock {fam.LOCK} with no columns")
    block["columns"] = thinking_columns()
    block["thinking_frame"] = {"max_supplied_items": fam.MAX_SUPPLIED_ITEMS, "twin": False, "fit_estimate": dict(fam.FIT_ESTIMATE),
                               "delivering_arm_id": fam.DELIVERING}
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
    # The lock form on BOTH nodes is the CELL-LEVEL thinking policy (the fragment's defaults carry the geometry cap); the arm columns compose on top of it.
    if "thinking_policy" in parent:
        raise SystemExit("the 268-B parent declares a cell-level thinking_policy; the R2b derive owns it")
    document["thinking_policy"] = json.loads(json.dumps(fam.DELIVERING_NODE_POLICY))
    document["what_this_is"] = f"{ROLE_TEXT[key]} " + WHAT_THIS_IS
    rec = fam.recovery(key)
    if rec:
        document["what_this_is"] += f" Recovery rec1 ({rec['recovered_at']}): {rec['root_cause']}."
    episode = document["native_episode"]
    if episode.get("finite_completion_policy") != "deliver-latest-or-abstain" or episode.get("react_exhaustion_policy") != "continue-without-answer":
        raise SystemExit("the native_episode finite-completion / ReAct-exhaustion policies are not the registered ones")
    if (episode.get("review_loop"), episode.get("max_revisions")) != ("off", 0):
        raise SystemExit("the reasoning-budget cell must run the Reviewer loop off")
    if document.get("preflight_budget_mode") != "defer-to-native-contact-fit":
        raise SystemExit("preflight_budget_mode must stay defer-to-native-contact-fit (the exact per-contact gate decides the fit)")
    if "supply_variants" in json.dumps(episode["roles"]) or "template_variants" in json.dumps(episode["roles"]):
        raise SystemExit("the reasoning-budget cell carries no supply or template arms")
    left, right = dv._leaves(parent), dv._leaves(document)
    missing = object()
    moved = sorted(k for k in set(left) | set(right) if left.get(k, missing) != right.get(k, missing))
    moved_by_rule, stray = classify_moved(moved)
    stray += [k for k in moved if not any(k == p or k.startswith(p + ".") for p in ALLOWED_DIFFS) and k not in stray]
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
    solver_arm = max(fam.ARM_SPECS, key=lambda a: a["solver"]["completion_cap"])
    document["date"] = fam.DATE
    document["experiment_id"] = spec["run"]
    document["execution_plan"], document["family_budget"] = plan, family
    document["fragment_kind"] = f"saea-{cell['cell_id']}"
    document["service_session"] = spec["session"]
    document["preserve_wire_responses"] = True
    document["stage3_algorithm"] = {
        "id": "none", "operators_used": [],
        "note": ("This cell carries NO training-free RL operator and says so explicitly: it is a same-flight node column over the per-node reasoning budget and completion cap "
                 f"(NX-T R2b) -- {len(fam.CANDIDATE_ARMS)} candidate arm, no twin, read as a column against the delivering {fam.DELIVERING} arm (the "
                 "268-B lock form) -- with no rollout pool, no per-sample credit, no update operator and no evolving store.")}
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
    document["generation_budget"] = {
        "cap": plan["planned_model_calls"], "target": plan["planned_model_calls"],
        "definition": (
            f"The review-off module graph (perception 1, solver 1; Reviewer and Planner never visited) under program {fam.PROGRAM} with the {fam.K}-arm "
            f"reasoning-budget column at the Perception node: {rows:,} x {fam.CONTACTS_PER_ROW} = {rows * fam.CONTACTS_PER_ROW:,} is the exact program "
            f"maximum (2 + 2 (K - 1), K = {fam.K}); the plan ceiling adds {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only fallback contacts per row (one per "
            f"budgeted-thinking contact of the arms: the delivering arm's 2 plus one per candidate node that still thinks, core.reasoning_knobs): {calls:,} = {rows:,} x "
            f"{fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}. The live phase fit makes {rows} x {fam.CONTACTS_PER_ROW} x "
            f"{tf.FIT_ENDPOINTS_PER_CONTACT} = {fam.fit_contact_cap(rows):,} tokenizer endpoint calls under its own run id {spec['fit_run']}. The GPU-hour "
            f"ceiling is a BOUND (rows x {fam.ARM_MIX_ROWS} full-row equivalents / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 x {fam.GPU_MARGIN}, "
            "ceil 0.1), never a target. The budget is RUN-CUMULATIVE across every attempt of this run id.")}
    rec = fam.recovery(key)
    if rec:
        # prose only: the cap above is the cumulative one (the original ceiling plus the failed attempt's realised spend)
        spent_calls, spent_audio = fam.predecessor_spend(key)
        document["generation_budget"]["definition"] += (
            f" Recovery rec1 (the cell's single one; a second failure closes the cell): the failed predecessor attempt {rec['predecessor_attempt_id']} spent "
            f"{spent_calls:,} contacts and {spent_audio:g} speech-seconds, so the run-cumulative budget is the original plan plus that spend: "
            f"{plan['planned_model_calls']:,} calls, {plan['planned_speech_audio_seconds']:,} speech-seconds.")
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
            f"Four-row structural form smoke of NX-T R2b: that {fam.PROGRAM} (ceiling {fam.CONTACTS_PER_ROW}) with the {fam.K}-arm Solver reasoning-budget column loads "
            f"on the raised-cap Thinking session ({spec['session']}), that the delivering arm's Perception and Solver requests carry the lock form (budget "
            f"{fam.DELIVERING_BUDGET}, cap {fam.COMPLETION_CAP}) and the candidate arm's Solver request carries budget {solver_arm['solver']['budget_tokens']} with "
            f"max_tokens {solver_arm['solver']['completion_cap']} while its Perception request is unchanged, that no node hits its own cap, that no delivered content carries a "
            "think marker, that the live phase fit passes at the raised cap, that the v5 arm receipt seals and that the episode completes, and what a contact costs per "
            "arm and per node (completion tokens, finish reasons, forced closes, seconds) against the registered cost. Scored by no one and read by no "
            "one: four rows are never evidence of benefit or harm.")
        document["failure_policy"] = (
            "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A failed smoke stops the cell and the "
            "column flight does not open. The smoke is re-flown whole at most once under one root-diagnosed recovery re-registration; a second failure closes "
            "the cell and the fix is proven on a four-row dry run.")
    else:
        document["purpose"] = (
            f"{spec['run']}: does raising the Solver's reasoning budget and completion cap, so that its reasoning is no longer truncated, move the score of the locked Thinking "
            f"system (owner rulings 323 and 325 A)? One flight, {fam.K} arms over TRAIN Fold B 1,080: the delivering {fam.DELIVERING} arm (the 268-B lock form) and the candidate "
            + ", ".join(fam.CANDIDATE_ARMS) + ". The candidate arm is read PAIRED per row against "
            f"{fam.DELIVERING} (official SLU-F1 primary, intent secondary; utterance-cluster bootstrap CI95) against the DECLARED A/A offset "
            f"|o| = {fam.DECLARED_OFFSET_SLU_PP} pp (no twin flies), beside the per-node reasoning statistics, the forced-close / cap-hit / empty-completion table "
            "and the throughput table (the projected GPU-h of a 1,080-row lock flight at each budget is the cost of the raise). claims_benefit is false: "
            "a per-node attribution, not an admission; development numbers only (owner decisions 28 and 86); never a test claim. Nothing here "
            "authorises a flight, a readiness flip or an admission entry.")
        document["failure_policy"] = (
            "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, prompt, knowledge, geometry or cap "
            "change. AT MOST ONE root-diagnosed recovery re-registration per run id (a new generation attempt id AND a new native_contact_fit run and attempt "
            "id); a second failure closes the cell and the fix is proven on a four-row dry run. A response whose delivered content carries a reasoning "
            "marker is a failure of the read, not of a row: it stops the flight (reasoning_content_guard). A partial manifest is never scored and never read.")
    document["core_read_design"] = {
        "arms": {arm: spec["run"] for arm in fam.ARM_ORDER},
        "chain": "swap to the raised-cap Thinking session -> smoke -> machine sign-off (coordinator veto window) -> the column flight",
        "reading": (f"official SLU-F1 and intent paired per row: {', '.join(fam.CANDIDATE_ARMS)} minus the delivering {fam.DELIVERING} arm, judged "
                    f"against the declared A/A offset {fam.DECLARED_OFFSET_SLU_PP} pp (no twin), beside the per-arm per-node reasoning, cap-hit, empty, "
                    "forced-close, finish-reason and seconds-per-contact tables and the throughput table"),
        "this_cell": spec["role"],
    }
    # the resident np4 fragment and session names live nowhere in this experiment: the model_fragment and service_session leaves hold the raised-cap ones
    old = [name for name in (fam.CONTROL_FRAGMENT, fam.tsf.THINK_SESSION) if name in json.dumps(document)]
    if old:
        raise SystemExit(f"the experiment still names the resident np4 fragment / session: {old}")
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
        raise SystemExit(f"the live {fit['slot_tokens']}-token slot does not hold the Solver prompt plus the {fit['completion_cap']}-token cap: failed {failed} "
                         f"(prompt limit {fit['prompt_limit_tokens']}, observed Solver prompt maximum {fit['observed_solver_prompt_tokens_max']}, bound {fit['max_supplied_items']})")
    out: dict[str, Any] = {"cells": {}, "_documents": {}}
    for key in fam.ALL_KEYS:
        baseline = derive_baseline(key, repo_root=repo_root, write=write)
        experiment = derive_experiment(key, repo_root=repo_root, write=write)
        out["cells"][key] = {"baseline": baseline["path"], "experiment": experiment["path"], "moved_leaves": baseline["moved_leaves"],
                             "moved_by_rule": baseline["moved_by_rule"],
                             "loader_verification": baseline["loader_verification"]}
        out["_documents"][key] = {"baseline": baseline["document"], "experiment": experiment["document"], "block": baseline["block"]}
        out["program"], out["ceiling"] = baseline["program"], baseline["ceiling"]
    out["campaigns"] = [write_campaign(key, repo_root=repo_root, write=write) for key in fam.ARM_KEYS]
    out["fit"] = fit
    out["fragment"] = fragment_proof(repo_root)
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
