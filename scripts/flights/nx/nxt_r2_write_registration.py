#!/usr/bin/env python3
"""Write the DRAFT readiness package of NX-T R2 (the per-node reasoning-budget column on the Thinking core, TRAIN Fold B), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration.

    python -B scripts/flights/nx/nxt_r2_write_registration.py --study-commit <sha> [--registered-at 2026-10-15T12:00:00.000000+00:00]
        [--root DIR] [--append-ledger] [--no-derive]
        [--recovery-registered-at <UTC>] [--recovery-base-commit <sha>] [--append-recovery-ledger]

RECOVERY rec2 (owner ruling 328, 2026-10-17): the SECOND recovery of the run id, under an explicit owner exception to the one-recovery rule, is a RESUME of the
stopped rec1 attempt (mode B, its row checkpoint, or mode A, its trace; the mode is computed by ``nxt_r2_rec2_mode.py`` into the committed rec2 recovery input):
``resume_from`` (the pin read from the data root into the committed rec2 snapshot) keeps the complete rows and flies the rest. The same flags drive it; the
generation plan then carries ``resume_from``, ``resume_budget`` and (when ``resume-replay-proof-rec2-v1.json`` is committed) the ``resume_replay_proof`` block.
``--append-recovery-ledger`` appends the rec2 generation row and the FIT-REC2 row; the coordinator folds the rec1 row.

The arm set is DATA (``nxt_r2_arms.json``): change it, re-run the derive and then this writer; every number in the package follows (program id, contacts, plan
ceilings, per-arm costs, the GPU-hour ceiling, the texts).

RECOVERY rec1 (generic mechanism, ``scripts/flights/lib/recovery.py``): ``nxt_r2_family.RECOVERIES`` is EMPTY on the first registration. Once the coordinator
commits ``predecessor-snapshot-arm-rec1-v1.json`` (``recovery.py snapshot``) and ``recovery-input-arm-v1.json`` (the diagnosis text) the family builds the arm
cell's recovery, and this writer supersedes the first-attempt plans, writes the ``-rec1`` plans with the recovery block, re-verifies the committed predecessor
snapshot against the data root when present, and puts the recovery ledger block (two DRAFT rows) in ``draft-ledger-rows.md``; ``--append-recovery-ledger`` also
appends that block to ``docs/exposure-ledger.md`` (idempotent). ``--registered-at`` defaults to the first registration's stamp.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import nxt_r2_derive_cells as dc  # noqa: E402
import nxt_r2_family as fam  # noqa: E402

rcv = fam.rcv                                       # scripts/flights/lib/recovery.py (the generic recovery mechanism)
REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import tfrl_family as tf  # noqa: E402
import write_tfrl_iteration_registration as reg  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

STATUS = reg.STATUS
SPEC = "docs/superpowers/specs/2026-10-12-thinking-core-engineering-base-design.md"
DECISIONS = reg.OWNER_DECISIONS
INSTRUMENT = reg.INSTRUMENT_NOTE
PRIMARY_METRIC = ("official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official-train, the pinned official evaluate.py), natural-mixture weighting, "
                  "with intent accuracy (scenario_action) beside it")
#: The node words, fixed here and implemented by the reader (``slurp_nxt_thinking_budget_column_read.node_words``): |o| is the DECLARED same-core A/A width
#: (no twin flies, owner decision 313 A), the floors are the decision-190 node-column floors.
WORD_RULES = {
    "GAIN": "SLU CI95 lower bound above +|o| (the cheaper budget RAISES the score beyond the declared A/A width)",
    "NEEDS-FULL-BUDGET": "SLU CI95 upper bound below -|o| (the cheaper budget loses more than the declared A/A width)",
    "CHEAPER-AT-NO-RESOLVED-LOSS": (f"SLU CI95 lower bound >= -{fam.FLOOR_SLU_PP} pp and intent CI95 lower bound >= -{fam.FLOOR_INTENT_PP} pp (decision 190 floors): any loss is "
                                    "inside the design's own resolution, so the cheaper budget may replace the locked one"),
    "UNRESOLVED": "none of the above (the interval is too wide to call the budget cheaper at no loss, and the loss is not beyond |o|)",
}
PROHIBITIONS = [
    "No test-split, DEV or Fold A contact (TRAIN Fold B only).",
    "No supply arm, no template column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "The system is the 268-B Thinking lock: the knowledge supply, the module graph, the post-processing and the roster are not changed. The per-node reasoning budget of the non-delivering arms is the ONLY varied factor.",
    "The completion cap (4,096), the delivering arm's budget (3,072) and drop-reasoning-v1 never move; a candidate budget states its answer reserve (cap - budget).",
    "No arm may set any knob other than enable_thinking / reasoning_budget_tokens / answer_reserve_tokens (rails.supply_variants.parse_perception_thinking_variants refuses the rest by name).",
    "No twin arm and at most two candidate arms (owner decision 313 A).",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false; the read attributes a reasoning-budget cost to a node and reports the saving.",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the harness commit is on master, NX-T R1 has sealed and been read, and the cells are flipped.",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]
FINDINGS = [
    {"id": "r1-answer-decides-the-arm-table",
     "finding": ("NX-T R1 (which nodes need thinking at all) is still flying when this package is built, so the arm table is a DEFAULT: both nodes at 1,536 and both "
                 "nodes at 2,048. R1's answer reshapes it: a node that reads NOT-NEEDED-AT-THE-FLOOR needs no budget scan, a node that reads NEEDS-THINKING is where "
                 "the budget scan matters, and a one-node scan (e.g. Perception at 1,536 with the Solver at 3,072, or a node OFF) halves the round's question."),
     "remedy": ("the coordinator edits scripts/flights/nx/nxt_r2_arms.json after reading R1, re-runs nxt_r2_derive_cells.py and nxt_r2_write_registration.py; the derive proves "
                "only the thinking_variants block, the program id and the live-fit ids moved; everything else (ceiling, ids, texts, tests) follows the data.")},
    {"id": "no-twin-the-declared-offset-is-the-null",
     "finding": (f"Owner decision 313 A: no twin arm. The in-flight A/A offset on this core was measured twice (268-B SLU +{fam.TWIN_OFFSET_268B_SLU_PP} / intent "
                 f"{fam.TWIN_OFFSET_268B_INTENT_PP}; P3.1 SLU {fam.TWIN_OFFSET_P31_SLU_PP} / intent +{fam.TWIN_OFFSET_P31_INTENT_PP}), so the read judges every arm against the "
                 f"DECLARED offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets) and the paired floor {fam.PAIRED_FLOOR_PP} pp; both are fixed "
                 "here, before contact. A single-flight paired contrast cannot separate a real budget effect from np4 batching jitter below |o|: such an arm reads UNRESOLVED "
                 "or CHEAPER-AT-NO-RESOLVED-LOSS, never a gain."),
     "remedy": "none; the stage3_effect_floor_check design is same-flight-node-column with twin false (it accepts it)."},
    {"id": "solver-prompt-differs-by-the-arms-own-note",
     "finding": ("Independent chains, no note sharing (coordinator ruling 2): the evidence, the instruction template and the QueryState are identical in every arm, but a "
                 "non-delivering arm's Solver prompt carries THAT arm's Perception note, which a shorter Perception reasoning may write differently. A both-nodes arm "
                 "therefore measures the budget of both nodes together with the downstream effect of the Perception note on the Solver; a one-node scan separates the two."),
     "remedy": "none; stated so the attribution is not over-read."},
    {"id": "cost-model-is-fitted-on-four-smoke-rows",
     "finding": ("The per-arm costs and the GPU-hour ceiling come from nxt_r2_cost.py, fitted on the 40 per-contact records of the NX-T R1 four-row smoke (12 thinking "
                 "contacts per node). The model is the clipped-reasoning one (cost of a contact = intercept + slope x (min(natural reasoning, budget) + answer + forced-close "
                 "message)); costs are rounded UP to 0.01 and the ceiling carries the registered 1.3 margin. The linear-in-budget guess is reported beside it as a LOWER "
                 "reference (it under-states the cost of a lower budget)."),
     "remedy": ("the R2 smoke measures the real mix; the reader's smoke stage compares it with the registered one and the coordinator signs off only when it is "
                "within 1.3x (decision 314 A condition).")},
    {"id": "serial-gpu-and-the-resident-session",
     "finding": ("Ruling 303 A: one experiment in flight. NX-T R1 occupies the Thinking session; this package is DRAFT / HELD until it has sealed and been read. The session "
                 "is the 268-B think-budget-np4 session (budget 3072, cap 4096, same model fragment): no per-arm session, the per-request fields carry the arm."),
     "remedy": "the coordinator flips the cells only after the R1 column flight has sealed."},
    {"id": "preflight-defers-to-the-exact-gate",
     "finding": ("As in the 268-B cells the model-free preflight counts the payload at 4 bytes per token (a placeholder) and would refuse the Solver render at the 4,096 "
                 "cap; the cells defer to the registered exact per-contact context-fit gate (preflight_budget_mode defer-to-native-contact-fit), which runs on every "
                 "arm's REAL request. A lower budget never lengthens a prompt: the cap stays 4,096 for every arm."),
     "remedy": "none."},
    {"id": "harness-addition-is-one-optional-frame-key",
     "finding": ("reasoning_budget_tokens and answer_reserve_tokens were already legal keys of a thinking_policy (receipt schema v5 unchanged). The one harness addition is the "
                 "OPTIONAL thinking_frame.delivering_arm_id of the consumption module (rails/consumption_module.py), so the delivering arm is named budget-3072 instead of the "
                 "carrier hook's both-on. Absent, the compiled block is byte-identical to NX-T R1's (unit-tested). consumption_module.py is not among the modules the prepared-"
                 "artifact identity hashes (runtime, kb_policy, knowledge_provider, phase_supply, knowledge_stores), so merging it re-pins nothing by itself."),
     "remedy": "merge the harness commit before the flip (the flip re-pins at the flight commit anyway)."},
    {"id": "flight-registration-check-does-not-yet-read-the-thinking-block",
     "finding": ("scripts/checks/flight_registration_check.py's node-column findings (aa-arm-missing, variant-cost-mismatch, template-summary-mismatch) read only the "
                 "Solver's template_variants block and are a no-op for a Perception-node group; the declaration is nevertheless complete (variant_cost, template_variants "
                 "summary with twin false) and stage3_effect_floor_check validates its shape."),
     "remedy": "widen NODE_COLUMN_PATH when the checker is next touched (not part of this package)."},
]


def identities(root: Path) -> dict:
    out = {}
    for key in fam.ALL_KEYS:
        spec = fam.CELLS[key]
        document = json.loads((Path(root) / "configs" / "experiment" / f"{spec['cell']}.json").read_text(encoding="utf-8"))
        cell = document["cells"][0]
        composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], spec["cell"])
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "key": key, "experiment": spec["cell"], "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": spec["fit_run"], "fit_attempt_id": spec["fit_attempt"], "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"], "arm": composed.values["arm"],
            "rows": document["population"]["count"], "split_identity_hash": split, "roster_receipt": document["population"].get("roster_receipt"),
            "composed_config_hash": composed.config_hash, "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values.get("native_contact_fit") or {}), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"], "session": document["service_session"],
        }
    return out


def arm_table_rows() -> list[dict]:
    """One row per arm in declared order: its setting per node, its policy and its registered cost (the table the README prints)."""

    rows = []
    for arm in fam.ARM_ORDER:
        perception, solver = fam.SETTINGS[arm]
        rows.append({"arm": arm, "perception": perception, "solver": solver, "role": "delivering" if arm == fam.DELIVERING else "candidate",
                     "thinking_policy": fam.POLICIES.get(arm), "cost_in_delivering_rows": fam.ROW_COST[arm],
                     "linear_reference_cost": fam.LINEAR_REFERENCE.get(arm)})
    return rows


def setting_text(value) -> str:
    if value == fam.OFF:
        return f"enable_thinking false (max_tokens {fam.tsf.THINK_ANSWER_RESERVE_TOKENS})"
    if value == fam.DELIVERING_BUDGET:
        return f"thinking, budget {fam.DELIVERING_BUDGET} / reserve {fam.COMPLETION_CAP - fam.DELIVERING_BUDGET} / cap {fam.COMPLETION_CAP}"
    return f"thinking, budget {value} / reserve {fam.COMPLETION_CAP - value} / cap {fam.COMPLETION_CAP}"


def measurement_blocks(ids: Mapping[str, Mapping]) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        arm["run_id"]: {
            "measurement_design": "same-flight-node-column", "expected_effect_pp": fam.EXPECTED_EFFECT_PP, "claims_benefit": False, "claim": "nominated",
            "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "variant_cost": {"extra_contacts_per_row": fam.CONTACTS_PER_ROW - 2, "extra_audio_seconds": round(fam.extra_audio_seconds("arm"), 2)},
            "template_variants": {"node": "perception", "candidate_arms": len(fam.CANDIDATE_ARMS), "twin": False},
            "variant_kind": "thinking-budget",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("A per-node cost attribution, not a benefit claim: the question is how much reasoning each node needs, so the expected effect of a cheaper budget is "
                     f"{fam.EXPECTED_EFFECT_PP} pp SLU-F1 (no resolvable loss) and the deliverable is the saving (the throughput table). NO twin flies (owner decision 313 A): "
                     f"the null is the DECLARED same-core A/A offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets, 268-B +{fam.TWIN_OFFSET_268B_SLU_PP} "
                     f"and P3.1 {fam.TWIN_OFFSET_P31_SLU_PP}) with the paired floor {fam.PAIRED_FLOOR_PP} pp; the design resolves a per-arm contrast of {fam.FLOOR_SLU_PP} pp SLU / "
                     f"{fam.FLOOR_INTENT_PP} pp intent at n = 1,080 (decision 190 node-column floors), which are also the no-resolved-loss margins.")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form, per-arm per-node decode cost and the forced-close behaviour only)", "read_roster": fam.READ_ROSTER,
            "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"Four Fold B rows prove FORM only: the {fam.PROGRAM} module program with {fam.K} arms loads on the Thinking session, each arm's requests carry their own "
                     "reasoning budget and reserve at the unchanged cap, the forced close fires earlier at a lower budget, the live phase fit passes and the v5 receipt seals. "
                     "Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_estimate() -> dict:
    expected = fam.expected_gpu_hours(fam.ROWS)
    model = fam.COST_MODEL
    return {
        "formula": (f"expected = rows x arm mix / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 with the arm mix {fam.ARM_MIX_ROWS} delivering-row equivalents per row "
                    f"({' + '.join(f'{a} {c}' for a, c in fam.ROW_COST.items())}); ceiling = ceil_0.1(expected x {fam.GPU_MARGIN}); each candidate cost is the clipped-reasoning "
                    "model's predicted seconds per row relative to the delivering arm, rounded UP to 0.01"),
        "cost_model": {
            "module": "scripts/flights/nx/nxt_r2_cost.py", "inputs": "scripts/flights/nx/nxt_r2_cost_inputs.json (40 per-contact records of the NX-T R1 smoke: token counts, seconds, forced flag; no text)",
            "form": "seconds(b) = a_node + c * (min(R, b) + A + m * [R > b]); no-think contact = the node's measured no-think mean seconds",
            "seconds_per_token": round(model["seconds_per_token"], 6),
            "nodes": {n: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in info.items() if k != "natural_reasoning_tokens"} for n, info in model["nodes"].items()},
            "limits": "four smoke rows, 12 thinking contacts per node; np4 batching jitter is inside the residual; defined for budgets up to the R1 budget 3,072",
        },
        "inputs": {"row_cost_in_delivering_rows": fam.ROW_COST, "linear_reference_cost": fam.LINEAR_REFERENCE, "rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL,
                   "margin": fam.GPU_MARGIN,
                   "r1_measured_seconds_per_row": cost_inputs_seconds()},
        "arm_mix_rows": fam.ARM_MIX_ROWS,
        "arm_table": arm_table_rows(),
        "column_flight": {"contacts": fam.program_calls("arm"), "plan_ceiling_calls": fam.original_generation_calls("arm"), "expected_gpu_hours": round(expected, 2),
                          "planned_ceiling_gpu_hours": fam.CELLS["arm"]["gpu_hours"],
                          "run_cumulative_plan_calls": fam.generation_calls("arm"), "run_cumulative_speech_audio_seconds": fam.cell_audio_cap("arm")},
        "smoke": {"contacts": fam.program_calls("smoke"), "planned_ceiling_gpu_hours": fam.CELLS["smoke"]["gpu_hours"]},
        "registered_total_gpu_hours": round(fam.CELLS["arm"]["gpu_hours"] + fam.CELLS["smoke"]["gpu_hours"], 1),
        "projected_lock_flight_gpu_hours": {a: round(fam.lock_flight_gpu_hours(a), 2) for a in fam.ARM_ORDER},
        "reference_268b": "one 268-B arm pass: 1,080 rows, 2,160 contacts, 9.78 GPU-h at 1.84 rows/min (spent about 9.4 against the 8.4 ceiling: the lesson of the measured-throughput rule)",
        "fallback_note": (f"The answer-only fallback adds at most one contact per budgeted-thinking contact: {fam.THINKING_CONTACTS_PER_ROW} per row (the delivering arm's 2 plus one per "
                          f"candidate node that still thinks); planned_model_calls is rows x ({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = "
                          f"{fam.original_generation_calls('arm')} (program maximum {fam.program_calls('arm')}). The runner requires only rows x ({fam.CONTACTS_PER_ROW} + 2). "
                          f"The FIT cap stays structural (rows x program contacts x endpoints = {fam.fit_contact_cap(fam.ROWS)})."),
    }


def cost_inputs_seconds() -> dict:
    return json.loads((fam.HERE / "nxt_r2_cost_inputs.json").read_text(encoding="utf-8")).get("r1_measured_seconds_per_row", {})


def context_fit() -> dict:
    """The arm's context fit on the selected geometry. The control reads the registered 268-B numbers (slot 24,576, prompt limit 17,406). A smaller slot
    (np6 x 20k, np8 x 16k) lowers the prompt limit by the same amount; ``solver_prompt_fits_measured_max`` says whether the measured Solver prompt maximum
    still fits (the exact per-contact gate decides on the live /props geometry; a row that cannot fit is refused there, not here)."""

    slot = fam.ACTIVE_GEOMETRY["slot_tokens"]
    limit = slot - fam.tsf.RESERVE_TOKENS - fam.tsf.THINK_MAX_TOKENS - fam.tsf.SPECIAL_RESERVE
    return {"slot_tokens": slot, "slots": fam.ACTIVE_GEOMETRY["slots"], "reserve_tokens": fam.tsf.RESERVE_TOKENS, "completion_cap": fam.tsf.THINK_MAX_TOKENS,
            "prompt_limit_tokens": limit, "solver_prompt_tokens_max_measured": fam.SOLVER_PROMPT_TOKENS_MAX,
            "solver_prompt_fits_measured_max": fam.SOLVER_PROMPT_TOKENS_MAX <= limit, "control_prompt_limit_tokens": fam.PROMPT_LIMIT_THINKING,
            "fit_estimate": dict(fam.FIT_ESTIMATE), "max_supplied_items": fam.MAX_SUPPLIED_ITEMS}


def existing_plan(root: Path, pkg: str, key: str) -> dict | None:
    """The cell's committed generation plan (rec1 name first, then the first-attempt name), or ``None`` on a first registration."""

    spec = fam.CELLS[key]
    for name in [rcv.plan_file_name(spec["prefix"], "generation", index) for index in range(fam.recovery_index(key), -1, -1)]:
        path = Path(root) / pkg / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


REPLAY_PROOF_FILE = "resume-replay-proof-rec2-v1.json"


def resume_plan_blocks(root: Path, pkg: str, key: str) -> dict:
    """The generation plan blocks of a RESUME recovery: the declaration, the run-cumulative accounting of what this attempt flies, and (once the
    offline replay ran and its receipt is committed) the ``resume_replay_proof`` the registration check requires of a cell that declares ``resume_from``."""

    rec = fam.recovery(key)
    if not rec or not rec.get("resume_from"):
        return {}
    counts = rec["resume_counts"]
    spent_calls, spent_audio = fam.predecessor_spend(key)
    cap_calls, cap_audio = fam.generation_calls(key), fam.cell_audio_cap(key)
    flown_contacts = counts["flown"] * fam.CONTACTS_PER_ROW
    out = {
        "resume_from": dict(rec["resume_from"]),
        "resume_budget": {
            "mode": "checkpoint" if "checkpoint_sha256" in rec["resume_from"] else "trace", "kept_rows": counts["kept"], "flown_rows": counts["flown"], "partial_rows": counts["partial"], "unstarted_rows": counts["unstarted"],
            "flown_worst_case_program_contacts": flown_contacts, "contacts_per_row": fam.CONTACTS_PER_ROW,
            "earlier_attempts_actual_calls": spent_calls, "earlier_attempts_actual_audio_seconds": round(spent_audio, 1),
            "run_cumulative_worst_case_calls": spent_calls + flown_contacts, "cap_calls": cap_calls, "cap_audio_seconds": cap_audio,
            "headroom_calls": cap_calls - spent_calls - flown_contacts,
            "gpu_hours_expected": round(fam.expected_gpu_hours(counts["flown"]), 2), "gpu_hours_ceiling": fam.CELLS[key]["gpu_hours"],
            "note": (f"This attempt flies {counts['flown']} rows x {fam.CONTACTS_PER_ROW} program contacts = {flown_contacts} contacts and nothing else; the cumulative cap "
                     "is a bound, not a target; the registered GPU-hour ceiling stands."),
        },
    }
    proof_path = Path(root) / pkg / REPLAY_PROOF_FILE
    if proof_path.is_file():
        out["resume_replay_proof"] = json.loads(proof_path.read_text(encoding="utf-8"))
    return out


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str, recov: Mapping[str, Mapping] | None = None) -> dict:
    docs = {}
    arms_doc = {arm: ({"thinking_policy": fam.POLICIES[arm], "settings": dict(zip(fam.NODES, fam.SETTINGS[arm]))} if arm in fam.POLICIES else
                      {"thinking_policy": None, "role": "delivering", "settings": dict(zip(fam.NODES, fam.SETTINGS[arm]))}) for arm in fam.ARM_ORDER}
    for key in fam.ALL_KEYS:
        i = ids[key]
        spec = fam.CELLS[key]
        base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": spec["session"], "experiment": i["experiment"],
                "family_budget": i["family_budget"], "preparation_base_commit": commit,
                "prepared_phase_supply": {"relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "note": "the flip mints this cell's own first-phase supply under its own run id (item E16)"},
                "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha}, "registered_at_utc": at, "status": STATUS,
                "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": json.loads(json.dumps(fam.NO_THINK_KNOBS)),
                "thinking_arms": json.loads(json.dumps(arms_doc)), "arm_order": list(fam.ARM_ORDER), "unused_budget_is_not_attempt_authority": True,
                "budget_node": json.loads(json.dumps(fam.BUDGET_NODE_KNOBS)), "no_twin": True,
                "one_factor": ("The per-node reasoning budget of the non-delivering arms (reasoning_budget_tokens b with answer_reserve_tokens cap - b at the named node). The delivering arm is the 268-B lock form "
                               f"(budget {fam.tsf.THINK_BUDGET_TOKENS} + reserve {fam.tsf.THINK_ANSWER_RESERVE_TOKENS} = cap {fam.tsf.THINK_MAX_TOKENS}); the system, the "
                               "knowledge supply, the sealed query vectors and the roster are the 268-B lock's.")}
        prior = existing_plan(root, pkg, key)
        if prior and prior.get("preparation_base_commit"):
            base["preparation_base_commit"] = prior["preparation_base_commit"]      # the commit the supply was prepared on does not move with a recovery
        pin = json.loads((Path(root) / "configs" / "baseline" / f"{i['baseline_fragment']}.json").read_text(encoding="utf-8")).get("prepared_phase_supply")
        if isinstance(pin, dict) and re.fullmatch(r"[0-9a-f]{64}", str(pin.get("sha256"))) and set(pin["sha256"]) != {"0"}:
            # the cell's own first-phase supply is already minted (same run id): the plan carries the baseline's pin, as refresh_registered_plan_pins.py leaves it
            base["prepared_phase_supply"] = dict(pin)
            base["prepared_phase_supply_annotations"] = {"note": "the flip mints this cell's own first-phase supply under its own run id (item E16)"}
        if recov and key in recov:
            base["recovery"] = json.loads(json.dumps(recov[key]))
            base["recovery_budget"] = rcv.recovery_budget(fam.RECOVERIES, key, i["family_budget"])
        resume_extra = resume_plan_blocks(root, pkg, key) if recov and key in recov else {}
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"],
                   run_id=i["run_id"], schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        route = ("Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored." if key == "smoke" else
                 f"Shared core.flight.cli campaign over {spec['campaign']} on the resident Thinking session ({fam.THINK_SESSION}); one official score per arm column "
                 "(stage3_rollout_score --mode perception-branches) after the seal. Flown by scripts/flights/nx/batch_chain_nxt_r2.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, **resume_extra, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of NX-T R2.",
            "scoring": "Per-arm official column scoring after a successful seal; no partial score." if key != "smoke" else "None: the smoke is never scored."}
        fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        docs[fam.plan_file_name(key, "fit")] = {
            **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."}
    return docs


LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = reg.LEDGER_INHERITED
def recovery_ledger_mark(key: str = "arm") -> str:
    return f"## Cell NXT-R2 recovery rec{fam.recovery_index(key)}: "


RECOVERY_AUTHORITY_REC1 = f"{fam.OWNER_RULINGS} (the per-node reasoning-budget column) and the generic recovery re-registration (owner decision 309 A)"
def resume_mode_letter(rec: Mapping | None) -> str:
    """``B`` (row checkpoint) or ``A`` (trace) for a resume record; the pin key in ``resume_from`` decides."""

    return "B" if rec and "checkpoint_sha256" in (rec.get("resume_from") or {}) else "A"


_REC_ARM = fam.recovery("arm") or {}
RECOVERY_AUTHORITY = RECOVERY_AUTHORITY_REC1 + (
    f" and {_REC_ARM['owner_exception']} (the explicit exception to the one-recovery rule for the rec{_REC_ARM['recovery_index']} mode-{resume_mode_letter(_REC_ARM)} resume)"
    if _REC_ARM.get("owner_exception") else "")
SCOPE = (f"the 268-B Thinking lock system (plain review-off COMP-1b module graph on lock {fam.LOCK}) with the {fam.K}-arm per-node reasoning-budget column ("
         + ", ".join(fam.ARM_ORDER) + f", no twin) at the Perception node (program {fam.PROGRAM}, {fam.CONTACTS_PER_ROW} contacts per row), TRAIN Fold B ({fam.OWNER_RULINGS})")


def draft_rows(ids: Mapping[str, Mapping], commit: str, at: str, pkg: str, shas: Mapping[str, str]) -> list[list[str]]:
    rows = []
    for key in fam.ALL_KEYS:
        if fam.recovery(key):
            continue                    # a recovered cell's two rows are the recovery block (rcv.recovery_ledger_block), written beside this table
        i = ids[key]
        for fit in (False, True):
            plan = f"{pkg}/{fam.plan_file_name(key, 'fit' if fit else 'generation')}"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            rows.append([at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
                         f"DRAFT -- REGISTERED. {fam.CELLS[key]['role'].capitalize()}: {SCOPE}" + (" -- FIT spend identity" if fit else ""), fam.think_model_text(key),
                         f"slurp TRAIN Fold B {i['rows']}", "discovery", i["split_identity_hash"], "no", str(calls),
                         str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]), INHERITED, plan,
                         f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."])
    arm = ids["arm"]
    rows.append([at[:10], fam.READ_RUN_ID, "model-free-check",
                 (f"The offline read of NX-T R2: score the {fam.K} arm columns of the sealed column flight once each with the official scorer (stage3_rollout_score "
                  f"--mode perception-branches); paired contrasts of every arm against the delivering {fam.DELIVERING} arm, the node words against the declared A/A offset, the per-scenario table and the "
                  f"per-arm per-node completion / finish-reason / cap-hit / empty / forced-close / throughput tables by the recipe {pkg}/analysis-recipe-v1.json. "
                  "Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp TRAIN Fold B {arm['rows']}, the sealed column flight (after the seal)", "discovery", arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the column flight is sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 304/307 of 2026-10-13, "
            "313 A and 318 A of 2026-10-14 (how much reasoning does each node need: the per-node reasoning-budget column on the Thinking core, TRAIN Fold B); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/nx/nxt_r2_mint_receipt.py after this countersignature; the READ row "
            "stays a draft until the column flight is sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        if fam.recovery(key):
            spec = fam.CELLS[key]
            clause = (f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator "
                      f"(nxt_r2_mint_receipt.py --supersede) so that its eligible_run_ids list the new FIT run id {i['fit_run_id']}")
            for run, label in ((i["run_id"], f"the {spec['role']}"), (i["fit_run_id"], f"live phase-fit identity of the {spec['role']}")):
                rows[run] = rcv.countersign_text(
                    fam.RECOVERIES, key, authority=RECOVERY_AUTHORITY, role=spec["role"], label=label, attempt=i["attempt_id"], fit_run=i["fit_run_id"],
                    fit_attempt=i["fit_attempt_id"], receipt_clause=clause, tail="the READ row stays a draft until the column flight is sealed")
            continue
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 304/307 of "
                             "2026-10-13, 313 A and 318 A of 2026-10-14; the column flight is sealed at its flight commit and the sealed run was not opened for any number before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any]) -> str:
    arm, smoke = ids["arm"], ids["smoke"]
    cf = cost["column_flight"]
    arm_rows = "\n".join(
        f"| `{r['arm']}` | {setting_text(r['perception'])} | {setting_text(r['solver'])} | {r['role']}{' (= the 268-B lock form)' if r['role'] == 'delivering' else ''} | "
        f"{r['cost_in_delivering_rows']} | {r['linear_reference_cost'] if r['linear_reference_cost'] is not None else 1.0} |" for r in cost["arm_table"])
    lock_rows = "\n".join(f"| `{a}` | {h} |" for a, h in cost["projected_lock_flight_gpu_hours"].items())
    return (
        "# NX-T R2: the per-node reasoning-budget column on the Thinking core, TRAIN Fold B (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/nx/nxt_r2_write_registration.py` from the fragments `nxt_r2_derive_cells.py` wrote, from the arm table `scripts/flights/nx/nxt_r2_arms.json`.\n\n"
        "## The question (owner rulings 304/307, 313 A, 318 A)\n\n"
        "NX-T R1 asks which nodes of the locked Thinking system need thinking at all. NX-T R2 asks how MUCH reasoning each node needs: the SECOND node-level round on the "
        "Thinking base, one flight, one roster, a same-flight COLUMN over the per-node reasoning BUDGET. Every arm contacts Perception and the Solver; the arms differ ONLY in "
        "the reasoning budget of their own two contacts (the completion cap 4,096 and `drop-reasoning-v1` stay). If the Solver reads CHEAPER-AT-NO-RESOLVED-LOSS at a lower "
        "budget, the lock row gets cheaper by the throughput table's factor: that saving is the efficiency deliverable of the round.\n\n"
        "**Prerequisite: R1's answer decides the arm table.** NX-T R1 is still flying; the table below is the default (both nodes at 1,536 and at 2,048). Edit "
        "`scripts/flights/nx/nxt_r2_arms.json` (a candidate node is an integer budget or `\"off\"`; a node left at 3072 keeps the locked form), re-run the derive and the "
        "writer, and every id, ceiling and text follows. At most two candidate arms and no twin (owner decision 313 A).\n\n"
        "## Arms (declared order; the delivering arm LAST; no twin)\n\n"
        "| arm | Perception | Solver | role | cost in delivering rows | linear reference |\n| --- | --- | --- | --- | ---: | ---: |\n"
        f"{arm_rows}\n\n"
        "The arm kind is `roles.perception.thinking_variants` (rails.supply_variants.parse_perception_thinking_variants; receipt `saea-perception-branch-arms-v5`, UNCHANGED; "
        "the consumption module's `thinking` column kind compiles it): a level-2 Perception branch group whose non-delivering arms carry a `thinking_policy` "
        "({perception | solver: enable_thinking | reasoning_budget_tokens | answer_reserve_tokens}) and nothing else. A budget arm states `reasoning_budget_tokens` b and "
        f"`answer_reserve_tokens` {fam.COMPLETION_CAP} - b, so the cap stays {fam.COMPLETION_CAP}. The delivering arm declares no policy, so its requests are the 268-B lock's, "
        "byte for byte (unit-tested). Harness addition: the OPTIONAL `thinking_frame.delivering_arm_id` of the consumption module names the delivering arm "
        "`budget-3072`; absent, the compiled block is NX-T R1's byte for byte.\n\n"
        "### Thinking-control knobs (one place: `thinking_system_family.THINKING_KNOBS`, re-used unchanged)\n\n"
        f"* the delivering form: `thinking_budget_tokens` {fam.THINKING_KNOBS['thinking_budget_tokens']} + answer reserve {fam.THINKING_KNOBS['answer_reserve_tokens']} = "
        f"completion cap {fam.THINKING_KNOBS['completion_cap']}, `reasoning_context_policy` `{fam.THINKING_KNOBS['reasoning_context_policy']}`, temperature 0, seed 20260913, "
        f"forced-close message (`--reasoning-budget-message`): \"{fam.THINKING_KNOBS['budget_message']}\";\n"
        "* a budget arm's node: `thinking_budget_tokens` b, `max_tokens` unchanged, the same forced-close message (the server closes the reasoning at b tokens and the model "
        "answers); the answer-only fallback exists only for a budgeted thinking request and its reserve is cap - b;\n"
        f"* model fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}`, swap target `{fam.THINK_SWAP_TARGET}` (the 268-B session, unchanged).\n\n"
        "## What the arms share, and what they do not (coordinator rulings 1 and 2)\n\n"
        "* Shared by every arm: the evidence blocks, the instruction templates, the QueryState, the speech packet, the module program, the knowledge supply, the "
        "roster, the model fragment and the serving session.\n"
        "* NOT shared: independent chains, no note sharing. A non-delivering arm's Solver prompt carries THAT arm's own Perception note.\n\n"
        "## Registered cells\n\n"
        "| cell | role | rows | program contacts | plan calls | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.program_calls(k):,} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | "
                    f"`{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |" for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the 268-B Thinking lock cell, derived by `nxt_r2_derive_cells.py` with exactly one addition (the Perception `thinking_variants` block, "
        f"compiled by the module compiler): lock `{fam.LOCK}`, program `{fam.PROGRAM}` ({fam.CONTACTS_PER_ROW} = 2 + 2 ({fam.K} - 1) contacts per row), the Thinking model "
        f"fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}` (swap target `{fam.THINK_SWAP_TARGET}`), the Thinking packets and their promotion receipt "
        f"(`{fam.THINK_PROMOTION_RECEIPT}`), the fold-excluded knowledge supply and the roster `{fam.ROSTER['arm']}` (1,080 rows); the smoke is the loop's own four "
        f"Fold B rows (`{fam.ROSTER['smoke']}`). `preflight_budget_mode` is `defer-to-native-contact-fit`; the finite-completion policy is "
        "`deliver-latest-or-abstain` and the ReAct-exhaustion policy `continue-without-answer`. The derive proves the leaves that moved against the 268-B parent "
        "(`moved_by_rule`): the `thinking_variants` block and its declaration, the program id (the ceiling is its suffix), the live-fit ids and cap, the cell's own supply "
        "pin and the cell text; nothing else.\n\n"
        "## GPU ceiling (from measured throughput)\n\n"
        f"{cost['formula']}.\n\n"
        f"* Cost model: `{cost['cost_model']['module']}`, fitted on {cost['cost_model']['inputs']}. Form: {cost['cost_model']['form']}. Limits: {cost['cost_model']['limits']}.\n"
        f"* Arm mix {cost['arm_mix_rows']} delivering-row equivalents per row; 1,080 rows: expected {cf['expected_gpu_hours']} GPU-h, registered ceiling "
        f"{cf['planned_ceiling_gpu_hours']} GPU-h ({cf['contacts']:,} program contacts, plan ceiling {cf['plan_ceiling_calls']:,} calls including at most "
        f"{fam.THINKING_CONTACTS_PER_ROW} fallback re-asks per row).\n"
        f"* Smoke: {cost['smoke']['contacts']} program contacts, ceiling {cost['smoke']['planned_ceiling_gpu_hours']} GPU-h. Registered total {cost['registered_total_gpu_hours']} GPU-h.\n"
        f"* {cost['reference_268b']}.\n\n"
        "Projected GPU-h of a 1,080-row LOCK flight that ran one arm's setting on both nodes, at the registered 1.84 rows/min reference (the model's prediction; the read replaces it "
        "with the flight's measured seconds):\n\n| arm | projected GPU-h per 1,080-row lock flight |\n| --- | ---: |\n"
        f"{lock_rows}\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        "## Chain sequence (the coordinator's)\n\n"
        "1. NX-T R1 has sealed and been read; the arm table `nxt_r2_arms.json` is decided; the harness commit (the optional `thinking_frame.delivering_arm_id`) is on master; "
        "this package is re-derived (`nxt_r2_derive_cells.py`, then `nxt_r2_write_registration.py --study-commit <sha> --registered-at <UTC> --append-ledger`).\n"
        "2. Countersign the five DRAFT rows with `countersign-row-texts-v1.json`.\n"
        "3. `python scripts/flights/nx/nxt_r2_mint_receipt.py`.\n"
        "4. `bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r2_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {smoke['experiment']},{arm['experiment']} --pins-commit-msg /home/chao/nxt2-pins-commit.txt` (`NXT2_KINDS` selects the cells; default `smoke arm`); "
        "then re-run the writer once at the flipped bytes so the draft rows carry the pinned plan shas (the R1 lesson).\n"
        f"5. Hold the idle watchdog; `bash scripts/flights/batch/serving_swap.sh {fam.THINK_SWAP_TARGET}`.\n"
        "6. `bash scripts/flights/nx/batch_chain_nxt_r2.sh all` (smoke, the sign-off wait on `/home/chao/nxt2-decode-signoff.marker` after "
        "`bash scripts/flights/nx/nxt_r2_read.sh smoke`, then the column flight).\n"
        "7. `bash scripts/flights/batch/serving_swap.sh slurp-np4` (swap back).\n"
        "8. `bash scripts/flights/nx/nxt_r2_read.sh columns` (the official per-arm scoring; prints no number), countersign the READ row, then "
        "`bash scripts/flights/nx/nxt_r2_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}`: every arm's first Solver answer is scored once, complete, by the official scorer; each candidate arm minus the delivering "
        f"`{fam.DELIVERING}` arm, SLU-F1 and intent, paired per row, utterance-cluster bootstrap (10,000 draws, seed 20261015). NO twin flies, so the null is the DECLARED "
        f"same-core A/A offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets: 268-B +{fam.TWIN_OFFSET_268B_SLU_PP} / intent {fam.TWIN_OFFSET_268B_INTENT_PP}; "
        f"P3.1 {fam.TWIN_OFFSET_P31_SLU_PP} / intent +{fam.TWIN_OFFSET_P31_INTENT_PP}) and the paired floor is {fam.PAIRED_FLOOR_PP} pp (decisions 172/231/313). Words (fixed here, in the reader; the "
        "first that applies):\n\n"
        + "\n".join(f"* **{w}**: {t}." for w, t in WORD_RULES.items()) + "\n\n"
        "The read also reports, per arm and node: completion tokens (mean / p50 / p90 / p99 / max), the finish-reason table, cap hits, empty completions, FORCED CLOSES (contacts "
        "that hit the budget), reasoning-character and think-marker counts, seconds per contact, and the THROUGHPUT table (seconds per row, rows per minute at 4 slots, GPU-h per "
        "1,080-row lock flight at each budget, each arm's measured cost in delivering rows beside the registered cost). claims_benefit is false; development numbers only "
        "(owner decisions 28 and 86).\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate and model, knobs, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the four plans (smoke, column flight; each generation and FIT) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `nxt_r2_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the five DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md` by `--append-ledger`) |\n")


def original_registered_at(root: Path) -> str:
    """The first registration's stamp (kept by a recovery: the plans, protocol and facts keep their original ``registered_at_utc``; the recovery
    carries its own stamp in its ``recovery`` block)."""

    return json.loads((Path(root) / fam.package_file("registered-facts-v1.json")).read_text(encoding="utf-8"))["registered_at_utc"]


def assert_resume_mode_is_launchable(root: Path, ids: Mapping[str, Mapping]) -> None:
    """A mode-B declaration (``resume_from`` = checkpoint pin) is refused at launch unless the checkpoint header's protocol hash and split identity hash equal this
    registration's; fail here, offline, from the committed rec2 snapshot's header copy, instead of at the driver's gate. Mode A has no such binding."""

    rec = fam.recovery("arm")
    if not rec or "checkpoint_sha256" not in (rec.get("resume_from") or {}):
        return
    header = rcv.load_snapshot(Path(root) / fam.PREDECESSOR_SNAPSHOTS["arm"][-1])["resume"]["checkpoint_header"]
    for name in ("protocol_hash", "split_identity_hash"):
        if header[name] != ids["arm"][name]:
            raise SystemExit(f"mode B refused: the checkpoint header's {name} {header[name]} differs from this registration's {ids['arm'][name]} (a new attempt id "
                             "moves the protocol hash); record resume_mode 'trace' in the rec2 recovery input (nxt_r2_rec2_mode.py computes it)")


def verify_snapshots(root: Path, data_root: str | None) -> dict:
    """Re-read each predecessor's attempt record on the data root and compare it with the committed snapshot receipt (skipped, and said so, when the
    data root or the record is absent: a CI checkout has no data root). A snapshot that pins a trace is re-hashed too. A disagreement raises."""

    out = {}
    for key in fam.ALL_KEYS:
        if not fam.recovery(key):
            continue
        entries = []
        for rel in fam.PREDECESSOR_SNAPSHOTS[key]:
            if not (Path(root) / rel).is_file():
                continue
            snap = rcv.load_snapshot(Path(root) / rel)
            record = Path(data_root or "/nonexistent") / "attempts" / snap["run_id"] / f"{snap['attempt_id']}.json"
            if data_root and record.is_file():
                fresh = rcv.verify_predecessor_snapshot(snap, data_root)
                entry = {"attempt_id": snap["attempt_id"], "verified": True, "state_now": fresh["state"], "actual_calls": fresh["actual_calls"],
                         "actual_audio_seconds": fresh["actual_audio_seconds"]}
                if snap.get("trace"):
                    entry["trace_sha256_verified"] = rcv.verify_trace_pin(snap, data_root)["trace_sha256"]
                    if snap["trace"].get("checkpoint_sha256"):
                        entry["checkpoint_sha256_verified"] = rcv.read_trace_pin(data_root, snap["run_id"], snap["attempt_id"])["checkpoint_sha256"]
                        if entry["checkpoint_sha256_verified"] != snap["trace"]["checkpoint_sha256"]:
                            raise rcv.RecoveryError(f"the row checkpoint of {snap['attempt_id']} moved since its snapshot")
            else:
                entry = {"attempt_id": snap["attempt_id"], "verified": False, "reason": "no attempt record on the data root (snapshot receipt used as committed)"}
            entries.append(entry)
        out[key] = entries
    return out


def recovery_blocks(root: Path, ids: Mapping[str, Mapping], at: str, recovery_at: str, recovery_base: str, worktree: str, branch: str) -> dict:
    """The recovery ledger block (two DRAFT rows) of every recovered cell, keyed by cell key."""

    out = {}
    for key in fam.ALL_KEYS:
        if not fam.recovery(key):
            continue
        i, spec = ids[key], fam.CELLS[key]
        rec = fam.recovery(key)
        flown_text = ("re-flown whole after the host restart that killed the first attempt" if rec["recovery_index"] == 1
                      else f"{rec['flown_phrase']} (explicit owner exception, {rec['owner_exception']})")
        scope = f"Cell NXT-R2 {spec['role']} -- RECOVERY rec{rec['recovery_index']}: {SCOPE}; {flown_text}"
        out[key] = rcv.recovery_ledger_block(
            fam.RECOVERIES, key, mark=recovery_ledger_mark(key), authority=RECOVERY_AUTHORITY, package=fam.PACKAGE, role=spec["role"], run=i["run_id"],
            fit_run=i["fit_run_id"], attempt=i["attempt_id"], fit_attempt=i["fit_attempt_id"], session=fam.THINK_SESSION, scope=scope,
            fit_scope=f"Cell NXT-R2 {spec['role']} -- RECOVERY rec{rec['recovery_index']} live phase-fit spend identity, request envelopes only, no generation.",
            model_tool=fam.think_model_text(key), carrier=f"slurp TRAIN Fold B {i['rows']:,}", split_hash=i["split_identity_hash"], caps=i["family_budget"],
            config_hash=i["composed_config_hash"], protocol_hash=i["protocol_hash"], registered_at=recovery_at, base_commit=recovery_base,
            worktree=worktree, branch=branch, plan_names=(fam.plan_file_name(key, "generation"), fam.plan_file_name(key, "fit")), inherited=INHERITED)
    return out


def recovery_markdown(ids: Mapping[str, Mapping]) -> str:
    """The README / preregistration recovery text: one section per recovery of each recovered cell, oldest first (rec1 keeps its own numbers)."""

    out = ""
    for key in fam.ALL_KEYS:
        history = fam.RECOVERY_HISTORY.get(key, [])
        i, spec = ids[key], fam.CELLS[key]
        for position, rec in enumerate(history):
            later = history[position + 1] if position + 1 < len(history) else None
            attempt, fit_attempt, fit_run = ((later["predecessor_attempt_id"], later["predecessor_fit_attempt_id"], later["predecessor_fit_run_id"]) if later
                                             else (i["attempt_id"], i["fit_attempt_id"], i["fit_run_id"]))
            caps = i["family_budget"] if later is None else fam.history_caps(key, rec["recovery_index"], i["family_budget"])
            names = tuple(rcv.plan_file_name(spec["prefix"], kind, rec["recovery_index"]) for kind in ("generation", "fit"))
            out += rcv.recovery_section({key: rec}, key, role=spec["role"], run=i["run_id"], attempt=attempt, fit_run=fit_run, fit_attempt=fit_attempt, caps=caps,
                                        plan_names=names)
    return out


def geometry_markdown() -> str:
    """README / preregistration text for a non-control serving geometry (owner decision 315 A); empty for the control."""

    g = fam.ACTIVE_GEOMETRY
    if g["target"] == fam.DEFAULT_GEOMETRY:
        return ""
    fit = context_fit()
    return (
        f"\n## Serving geometry of the column flight: {g['target']} (coordinator selection; owner decision 315 A is void on the 24 GB card)\n\n"
        f"The rec1 re-fly runs on the geometry a throughput receipt picked: {g['slots']} slots x {g['slot_tokens']:,} tokens, session `{g['session']}`, model "
        f"fragment `{g['model_fragment']}` (resolved from {g['source']}). ONLY the geometry leaves move against the np4 x 24k control (`service_session`, the cell's "
        "model-fragment reference and, inside the fragment, `server_args` / `profile_slot_count` / `geometry_basis`); every other leaf is the control's byte for byte "
        "(the proof is `geometry` in `registered-facts-v1.json`). The decoding knobs (budget 3,072 / cap 4,096 / drop-reasoning-v1) do not move with geometry. The "
        f"prompt limit on this slot is {fit['prompt_limit_tokens']:,} tokens against the measured Solver prompt maximum {fit['solver_prompt_tokens_max_measured']:,} "
        f"(fits: {fit['solver_prompt_fits_measured_max']}); the exact per-contact gate decides on the live geometry. The smoke stays on the control geometry (sealed there).\n"
        f"The chain swaps to `{g['target']}` (`serving_swap.sh {g['target']}`) before the arm segment.\n")


def recovery_sequence_text(ids: Mapping[str, Mapping]) -> str:
    """The coordinator's recovery sequence (README only)."""

    arm, smoke = ids["arm"], ids["smoke"]
    if fam.recovery_index("arm") >= 2:
        counts = fam.RECOVERIES["arm"]["resume_counts"]
        return (
            "\n### Recovery rec2 sequence (the coordinator's; it replaces steps 2 to 6 above)\n\n"
            f"1. Run the writer on master WITH the recovery ledger block: `python -B scripts/flights/nx/nxt_r2_write_registration.py --study-commit <sha> "
            "--recovery-registered-at <UTC> --append-recovery-ledger` (appends the rec2 generation row and the FIT-REC2 row; idempotent).\n"
            f"2. Fold the rec1 generation row of `{arm['run_id']}` into the rec2 row (one run id, one row; the notes name BOTH earlier attempts) and countersign the two "
            f"new rows (`{arm['run_id']}`, `{arm['fit_run_id']}`) with `countersign-row-texts-v1.json`; the READ row stays a draft until the seal.\n"
            "3. `python scripts/flights/nx/nxt_r2_mint_receipt.py --supersede` (the current receipt is renamed to a dated backup; the new one lists the rec2 FIT run id "
            "after the rec1 one and carries the rec2 plan sha256s and the snapshots).\n"
            "4. After the NX-T R2b column seal (serial GPU): `NXT2_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r2_flip.sh\" --package "
            f"{fam.PACKAGE} --cells {arm['experiment']} --pins-commit-msg /home/chao/nxt2-pins-commit.txt` (the arm cell only; the sealed smoke is not touched; "
            "`--allow-output-change` is never passed).\n"
            "5. Hold the idle watchdog; `bash scripts/flights/nx/batch_chain_nxt_r2.sh arm-only` (checks the predecessor pin, runs the resume prelaunch gate through the driver, "
            f"swaps to `{fam.THINK_SWAP_TARGET}` when it is not resident, and flies {counts['flown']} rows; the merged manifest is {counts['roster']:,} rows).\n"
            "6. `bash scripts/flights/nx/nxt_r2_read.sh columns`, countersign the READ row, then `bash scripts/flights/nx/nxt_r2_read.sh` (the reader reads the merged "
            "manifest: the kept and the flown rows of the one run id)."+"\n")
    return (
        "\n### Recovery sequence (the coordinator's; it replaces steps 2 to 6 above for the recovered column flight)\n\n"
        "0. (Before the writer.) Snapshot the failed attempt and commit the diagnosis: `python -B scripts/flights/lib/recovery.py snapshot --data-root $SPEECHRL_DATA_DIR "
        f"--run-id {arm['run_id']} --attempt-id <failed attempt id> --fit-run-id <fit run id> --fit-attempt-id <fit attempt id> --out {fam.PREDECESSOR_SNAPSHOT['arm']}`, and write "
        f"`{fam.RECOVERY_INPUT['arm']}` with the keys {', '.join(fam.RECOVERY_INPUT_KEYS)} (the family builds the recovery from these two files; no other edit).\n"
        "1. Re-run the writer on master with the recovery ledger block: `python -B scripts/flights/nx/nxt_r2_write_registration.py --study-commit <sha> "
        "--recovery-registered-at <UTC> --append-recovery-ledger`.\n"
        f"2. Countersign the two new rows (`{arm['run_id']}` recovery row, `{arm['fit_run_id']}`) with `countersign-row-texts-v1.json`; fold the first-attempt "
        "generation row of the same run id into the recovery row.\n"
        "3. `python scripts/flights/nx/nxt_r2_mint_receipt.py --supersede` (the old receipt is renamed to a dated backup first; the new receipt lists the "
        "rec1 FIT run id and carries the recovery block and the new plan sha256).\n"
        "4. The flip converges the arm cell (its readiness block pins the decision receipt, whose sha256 changed); the sealed smoke is NOT flipped again: "
        f"`NXT2_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r2_flip.sh\" --package {fam.PACKAGE} --cells "
        f"{arm['experiment']} --pins-commit-msg /home/chao/nxt2-pins-commit.txt`; then re-run the writer once at the flipped bytes (the first-attempt row of the run id is folded, "
        "never left beside the rec1 row).\n"
        "5. Hold the idle watchdog; `bash scripts/flights/batch/serving_swap.sh " + fam.THINK_SWAP_TARGET + "`.\n"
        "6. `bash scripts/flights/nx/batch_chain_nxt_r2.sh arm-only` (refuses unless the smoke is sealed and the sign-off marker exists; `all` refuses "
        "because it would re-fly the sealed smoke).\n"
        "7. Optional hygiene: mark the OPENED predecessor attempt aborted (`AttemptStore.abort_if_opened`); its realised spend counts either way.\n")


def write_package(root: Path, commit: str, at: str | None, *, append_ledger: bool = False, derive: bool = True, recovery_at: str | None = None,
                  recovery_base: str | None = None, append_recovery_ledger: bool = False, recovery_worktree: str = "", recovery_branch: str = "",
                  data_root: str | None = None) -> dict:
    root = Path(root)
    at = at or original_registered_at(root)
    recovery_at = recovery_at or datetime.now(timezone.utc).isoformat()
    recovery_base = recovery_base or commit
    snapshot_check = verify_snapshots(root, data_root)
    recov = {k: rcv.persisted_recovery(fam.RECOVERIES, k, recovery_at, recovery_base) for k in fam.ALL_KEYS if fam.recovery(k)}
    derived = dc.derive(repo_root=root) if derive else None
    loader = {k: (derived["cells"][k]["loader_verification"] if derived else {"ok": True}) for k in fam.ALL_KEYS}
    pkg = fam.PACKAGE
    ids = identities(root)
    arm, smoke = ids["arm"], ids["smoke"]
    assert_resume_mode_is_launchable(root, ids)
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {a: (fam.POLICIES[a] if a in fam.POLICIES else "the delivering arm = the 268-B lock form (budget 3,072 on both nodes)")
                 for a in fam.ARM_ORDER},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The node words and their thresholds are fixed in {fam.READER} and in this package's README: NEEDS-THINKING, NO-RESOLVED-LOSS, "
                                     "GAIN, UNRESOLVED against the declared A/A offset and the decision-190 node-column floors (no twin flies)."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the per-node thinking decoding of the non-delivering arms; the system is the 268-B Thinking lock on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-nxt-r2-thinking-budget-fold-b-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": ("How much reasoning does each node of the locked Thinking system need (owner rulings 304/307, 313 A, 318 A)? Each candidate arm is read PAIRED per "
                         f"row against the delivering {fam.DELIVERING} arm on the same 1,080 Fold B rows in one flight, against the declared A/A offset (no twin).")}
    snapshot_refs = {k: [{"path": rel, "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()}
                         for rel in fam.PREDECESSOR_SNAPSHOTS[k] if (root / rel).is_file()] for k in recov}
    if recov:
        protocol["recovery"] = json.loads(json.dumps(recov))
        protocol["predecessor_snapshots"] = snapshot_refs
        protocol["superseded_attempt_ids"] = [a for k in recov for rec in fam.RECOVERY_HISTORY[k]
                                              for a in (rec["predecessor_attempt_id"], rec["predecessor_fit_attempt_id"])]
        protocol["recovery_note"] = " ".join(f"[{fam.CELLS[k]['role']}] {fam.recovery(k)['reason']}" for k in recov)
        if any(fam.recovery(k).get("owner_exception") for k in recov):
            protocol["failure_policy"] += (f" Recovery rec1 is spent; rec2 stands under an explicit owner exception ({fam.recovery('arm')['owner_exception']}) to the rule of one "
                                           "recovery per run id and covers that one re-registration only: a failure of it closes the cell.")
        else:
            protocol["failure_policy"] += " Recovery rec1 is spent for a recovered cell: a second failure closes it."
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, recov)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    for key in recov:
        for stale in fam.superseded_plan_file_names(key):       # the first-attempt plans are superseded: removed from the package (git keeps them)
            if (root / pkg / stale).is_file():
                (root / pkg / stale).unlink()
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": f"{DECISIONS} ({fam.OWNER_RULINGS}); {SPEC}; {INSTRUMENT}",
        "cell_kind": f"SAME-FLIGHT NODE COLUMN over the per-node reasoning budget -- {fam.K} arms (no twin) paired per row against the delivering {fam.DELIVERING} arm; claim ceiling nominated",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)",
        "measurement_design": "same-flight-node-column", "read_run_id": fam.READ_RUN_ID, "recipe_id": fam.RECIPE_ID, "registered_at_utc": at,
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": fam.READ_ROSTER, "rows": fam.ROWS, "split_identity_hash": arm["split_identity_hash"]},
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": fam.READ_RUN_ID, "smoke": smoke["run_id"], "smoke_fit": smoke["fit_run_id"]},
        "arms": list(fam.ARM_ORDER), "delivering": fam.DELIVERING, "twin": None, "arm_settings": {a: dict(zip(fam.NODES, fam.SETTINGS[a])) for a in fam.ARM_ORDER},
        "declared_offset": {"slu_pp": fam.DECLARED_OFFSET_SLU_PP, "paired_floor_pp": fam.PAIRED_FLOOR_PP, "basis": "owner decision 313 A: the larger of the two measured same-core A/A offsets"},
        "external_references": {"twin_offset_268b_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_268b_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                "twin_offset_p31_slu_pp": fam.TWIN_OFFSET_P31_SLU_PP, "twin_offset_p31_intent_pp": fam.TWIN_OFFSET_P31_INTENT_PP,
                                "thinking_system_slu": fam.THINKING_SYSTEM_SLU},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_columns": "bash scripts/flights/nx/nxt_r2_read.sh columns  (stage3_rollout_score --mode perception-branches: one complete official scoring per arm; no number printed)",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/nx/nxt_r2_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-arm per-node decode cost; no countersignature; the sign-off for the column flight)"},
        "verdict_words": list(WORD_RULES), "word_rules": WORD_RULES,
        "what_is_not_here": "No margins block and no admission: nothing is locked here."}
    shas["analysis-recipe-v1.json"] = reg.wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this DRAFT registration rests on, and the CANONICAL stage3_measurement blocks "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": {"program": fam.PROGRAM, "lock": fam.LOCK, "contacts_per_row": fam.CONTACTS_PER_ROW, "arms": list(fam.ARM_ORDER), "rows": fam.ROWS,
                       "arm_generation_calls": arm["family_budget"]["generation_calls_cap"], "smoke_generation_calls": smoke["family_budget"]["generation_calls_cap"],
                       "arm_fit_endpoint_calls_cap": arm["family_budget"]["fit_endpoint_calls_cap"],
                       "arm_speech_audio_seconds_cap": arm["family_budget"]["repeated_speech_audio_seconds_cap"],
                       "smoke_speech_audio_seconds_cap": smoke["family_budget"]["repeated_speech_audio_seconds_cap"], "cost_estimate": cost},
        "blockers": blockers, "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "context_fit": context_fit(),
        "geometry": dc.geometry_proof(root),
        "findings": FINDINGS, "identity": ids,
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET,
                 "speech_packet_root": fam.THINK_PACKET_ROOT, "speech_packet_promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                 "speech_packet_promotion_receipt_sha256": fam.thinking_promotion_sha256()},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{fam.OWNER_RULINGS}; {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "read_rule": {"reader": fam.READER, "words": WORD_RULES, "word_order": list(WORD_RULES), "declared_offset_slu_pp": fam.DECLARED_OFFSET_SLU_PP,
                      "paired_floor_pp": fam.PAIRED_FLOOR_PP, "floors_pp": {"slu": fam.FLOOR_SLU_PP, "intent": fam.FLOOR_INTENT_PP}, "twin": None,
                      "delivering": fam.DELIVERING},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": arm["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": json.loads(json.dumps(fam.NO_THINK_KNOBS)),
        "thinking_arms": {a: (fam.POLICIES.get(a)) for a in fam.ARM_ORDER}, "status": "DRAFT-HELD"}
    if recov:
        facts["recovery"] = json.loads(json.dumps(recov))
        facts["predecessor_snapshots"] = snapshot_refs
        facts["recovery_budget"] = {k: rcv.recovery_budget(fam.RECOVERIES, k, ids[k]["family_budget"]) for k in recov}
        facts["resume"] = {k: {"resume_from": fam.recovery(k)["resume_from"], "counts": fam.recovery(k)["resume_counts"], "mode": fam.recovery(k)["resume_mode"],
                               "owner_exception": fam.recovery(k)["owner_exception"], "fix_commit": fam.recovery(k).get("fix_commit")}
                           for k in recov if fam.recovery(k).get("resume_from")}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/nx/nxt_r2_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"{fam.OWNER_RULINGS}; {INSTRUMENT}; {SPEC}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": f"Fly the per-node reasoning-budget column on the Thinking core on TRAIN Fold B: four-row smoke, then the {fam.K}-arm column flight (no twin).",
        "decision_id": fam.DECISION_ID, "eligible_attempt_ids": fam.eligible_attempt_ids(), "eligible_run_ids": fam.eligible_run_ids(),
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "starting or touching any serving session outside the registered swap",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool",
                           "any change beyond the registered per-node thinking policies", "Fold A, DEV or test-split contact"],
        "owner": "root", "population": {"count": fam.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": arm["split_identity_hash"],
                                        "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "no_child_start_stop": True},
        "status": "DRAFT-NOT-MINTED"}
    if recov:
        draft["recovery"] = json.loads(json.dumps(recov))
        draft["recovery_budget"] = {k: rcv.recovery_budget(fam.RECOVERIES, k, ids[k]["family_budget"]) for k in recov}
        draft["antecedents"]["predecessor_snapshots"] = snapshot_refs
        draft["antecedents"]["recovery_plans"] = {
            k: {kind: {"path": f"{pkg}/{fam.plan_file_name(k, kind)}", "sha256": shas[fam.plan_file_name(k, kind)]} for kind in ("generation", "fit")}
            for k in recov}
        draft["supersedes_receipt"] = {"path": fam.DECISION_RELPATH, "note": ("the current receipt's run ids are a strict prefix of this list; this one appends the latest "
                                                                           "recovery's FIT run id. nxt_r2_mint_receipt.py --supersede renames the old receipt to a dated backup first.")}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(row_cells)} unconsumed rows -- the cells still on their first attempt (generation row and live-phase-fit identity each) and the READ row; a "
             f"recovered cell's two rows follow this table as a recovery block -- for NX-T R2 of the owner rulings in {fam.OWNER_RULINGS}. "
             f"Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: the Thinking session is the 268-B think-budget-np4 session "
             "(the same registered swap target); its serving row is the coordinator's at the swap.",
             "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(cells) for cells in row_cells]
    rows_text = "\n".join(lines) + "\n"
    blocks = recovery_blocks(root, ids, at, recovery_at, recovery_base, recovery_worktree, recovery_branch)
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text + "".join(blocks.values()))
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    recovery_md = recovery_markdown(ids) + (geometry_markdown() if recov else "")
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost) + recovery_md + (recovery_sequence_text(ids) if recov else ""))
    prereg = (f"# NX-T R2: the per-node reasoning-budget column, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
              "Development numbers only.\n\n"
              f"Runs: `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{fam.READ_RUN_ID}`.\n\n"
              f"The node words and the read rule are in `{pkg}/README.md`.\n\n## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": measurement_blocks(ids)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, fam.PREREG, prereg + recovery_md)
    result = {"package": pkg, "ids": ids, "shas": shas, "blockers": blockers, "loader_verification": loader, "predecessor_snapshot_check": snapshot_check}
    if append_recovery_ledger:
        result["recovery_ledger_appended"] = {k: rcv.append_recovery_ledger_block(root / reg.LEDGER, blocks[k], ids[k]["attempt_id"]) for k in blocks}
    if append_ledger:
        ledger = root / reg.LEDGER
        current = io.open(ledger, encoding="utf-8", newline="").read()
        if fam.LEDGER_MARK in current:
            result["ledger_appended"] = False
        else:
            io.open(ledger, "w", encoding="utf-8", newline="").write(current.rstrip("\n") + "\n\n" + rows_text)
            result["ledger_appended"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", default=None,
                        help="the first registration's stamp; default: the one already in registered-facts-v1.json (a recovery keeps it)")
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository (or overlay) root to read and write")
    parser.add_argument("--append-ledger", action="store_true", help="append the DRAFT rows at the END of docs/exposure-ledger.md (idempotent)")
    parser.add_argument("--append-recovery-ledger", action="store_true",
                        help="append ONLY the recovered cell's two DRAFT rows (rec1) as a new ledger block; idempotent on the latest recovery's generation attempt id")
    parser.add_argument("--recovery-registered-at", default=None,
                        help="UTC timestamp of the recovery re-registration (default: now); recorded in the recovery plan and ledger rows")
    parser.add_argument("--recovery-base-commit", default=None, help="the commit the recovery was registered on top of (default: --study-commit)")
    parser.add_argument("--recovery-branch", default="sonnet/nxt2-rec2")
    parser.add_argument("--recovery-worktree", default="/home/chao/saea-worktrees/sonnet-nxt2-rec2")
    parser.add_argument("--data-root", default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR"),
                        help="re-verify the predecessor snapshot against this data root when its attempt record is present")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    parser.add_argument("--geometry", default=None,
                        help=f"serving geometry of the arm cell (owner decision 315 A): {fam.DEFAULT_GEOMETRY} (default; byte-identical to the control), "
                             "think-budget-np6 or think-budget-np8 (untested until their model fragments land); omitted = the committed selection")
    args = parser.parse_args(argv)
    dc.apply_geometry_arg(args.geometry, Path(args.root))
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive,
                           recovery_at=args.recovery_registered_at, recovery_base=args.recovery_base_commit,
                           append_recovery_ledger=args.append_recovery_ledger, recovery_worktree=args.recovery_worktree,
                           recovery_branch=args.recovery_branch, data_root=args.data_root)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
