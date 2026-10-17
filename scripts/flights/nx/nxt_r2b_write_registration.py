#!/usr/bin/env python3
"""Write the DRAFT readiness package of NX-T R2b (the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md`` and the derive's ``signoff-conditions-v1.json``) and, beside it, the
preregistration.

    python -B scripts/flights/nx/nxt_r2b_write_registration.py --study-commit <sha> [--registered-at 2026-10-17T12:00:00.000000+00:00]
        [--root DIR] [--append-ledger] [--no-derive]
        [--recovery-registered-at <UTC>] [--recovery-base-commit <sha>] [--append-recovery-ledger]

The arm set is DATA (``nxt_r2b_arms.json``): change it, re-run the derive and then this writer; every number in the package follows (program id, contacts, plan
ceilings, per-arm costs, the GPU-hour ceiling, the sign-off conditions, the texts).

RECOVERY rec1 (generic mechanism, ``scripts/flights/lib/recovery.py``): ``nxt_r2b_family.RECOVERIES`` is EMPTY on the first registration. Once the coordinator
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

import nxt_r2b_derive_cells as dc  # noqa: E402
import nxt_r2b_family as fam  # noqa: E402

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
#: The node words, fixed here and implemented by the reader (``slurp_nxt_thinking_budget_column_read.node_words`` in raise mode): |o| is the DECLARED same-core A/A width
#: (no twin flies, owner decision 313 A), the floors are the decision-190 node-column floors. For an arm whose budget is ABOVE the delivering one the R2 "cheaper" words
#: invert; the rules apply in this order (the first that applies wins).
WORD_RULES = {
    "GAIN": "SLU CI95 lower bound above +|o| (the raised Solver budget RAISES the score beyond the declared A/A width)",
    "HARM": "SLU CI95 upper bound below -|o| (the raised budget loses more than the declared A/A width)",
    "NEEDS-NO-MORE-BUDGET": (f"SLU CI95 upper bound <= +{fam.FLOOR_SLU_PP} pp and intent CI95 upper bound <= +{fam.FLOOR_INTENT_PP} pp (decision 190 floors): any gain is inside "
                             "the design's own resolution, so the raise buys no resolved gain and the delivering budget is enough"),
    "UNRESOLVED": "none of the above (the interval is too wide to call the raise a gain, a harm or no resolved gain)",
}
PROHIBITIONS = [
    "No test-split, DEV or Fold A contact (TRAIN Fold B only).",
    "No supply arm, no template column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "The system is the 268-B Thinking lock: the knowledge supply, the module graph, the post-processing and the roster are not changed. The Solver's reasoning budget and completion cap in the candidate arm are the ONLY varied factor.",
    f"The delivering arm's form (budget {fam.DELIVERING_BUDGET}, reserve {fam.COMPLETION_CAP - fam.DELIVERING_BUDGET}, cap {fam.COMPLETION_CAP}), the Perception node of every arm and drop-reasoning-v1 never move; a raised node states its answer reserve (cap - budget >= {fam.ANSWER_RESERVE_FLOOR}).",
    "No arm may set any knob other than enable_thinking / reasoning_budget_tokens / answer_reserve_tokens (rails.supply_variants.parse_perception_thinking_variants refuses the rest by name).",
    "No twin arm and exactly one candidate arm (owner decision 313 A and ruling 325 A).",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false; the read attributes the effect of untruncated Solver reasoning to the Solver and reports its cost.",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the harness commit is on master, NX-T R2 has sealed, the raised-cap serving session's Windows tasks are registered and the cells are flipped.",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]
FINDINGS = [
    {"id": "solver-reasoning-is-truncated-at-the-delivering-budget",
     "finding": (f"NX-T R1 read the Solver NEEDS-THINKING and measured, on its both-on arm, {fam.R1['solver_forced_closes_at_3072']} of {fam.R1['solver_contacts']} Solver contacts closed by the "
                 f"{fam.DELIVERING_BUDGET}-token budget (completion p90 {fam.R1['solver_completion_tokens_p90']:.0f}): the Solver's reasoning is truncated. Owner rulings 323 and 325 A raise the "
                 "Solver's budget and cap in ONE candidate arm so the reasoning can finish. The question is whether the finished reasoning moves the score; it is not assumed to."),
     "remedy": "none; the read reports the forced-close share per budget beside the contrast."},
    {"id": "no-twin-the-declared-offset-is-the-null",
     "finding": (f"Owner decision 313 A: no twin arm. The in-flight A/A offset on this core was measured twice (268-B SLU +{fam.TWIN_OFFSET_268B_SLU_PP} / intent "
                 f"{fam.TWIN_OFFSET_268B_INTENT_PP}; P3.1 SLU {fam.TWIN_OFFSET_P31_SLU_PP} / intent +{fam.TWIN_OFFSET_P31_INTENT_PP}), so the read judges the arm against the "
                 f"DECLARED offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets) and the paired floor {fam.PAIRED_FLOOR_PP} pp; both are fixed "
                 "here, before contact. A single-flight paired contrast cannot separate a real budget effect from np4 batching jitter below |o|: such an arm reads UNRESOLVED "
                 "or NEEDS-NO-MORE-BUDGET, never a gain."),
     "remedy": "none; the stage3_effect_floor_check design is same-flight-node-column with twin false (it accepts it)."},
    {"id": "fit-bound-52-not-55-at-the-raised-cap",
     "finding": (f"The live slot is {fam.SLOT_TOKENS:,} tokens; the operational reserve is {fam.RESERVE_TOKENS:,} and the special reserve {fam.SPECIAL_RESERVE}. At the {fam.FRAGMENT_CAP:,}-token geometry cap the "
                 f"prompt limit of EVERY contact of the cell is {fam.PROMPT_LIMIT:,} tokens (the fit gate's ceiling is the fragment's cap, not a node's). The registered FIT_ESTIMATE form "
                 f"(base {fam.FIT_ESTIMATE['base_prompt_tokens']:,} + {fam.FIT_ESTIMATE['tokens_per_supplied_item']} per supplied item) at the lock's bound of {fam.LOCK_MAX_SUPPLIED_ITEMS} items is "
                 f"{fam.estimated_prompt_tokens(fam.LOCK_MAX_SUPPLIED_ITEMS):,} tokens, ABOVE that limit, so the thinking_variants parser would refuse the block; the bound is the largest count "
                 f"the estimate admits, {fam.MAX_SUPPLIED_ITEMS} ({fam.estimated_prompt_tokens(fam.MAX_SUPPLIED_ITEMS):,} tokens). The bound only parameterises that estimate and a runtime refusal of a "
                 f"branch that supplies more items than it; the sealed Fold B flights supplied at most {fam.OBSERVED_SUPPLIED_COUNT_MAX} items on 5,400 branch rows, and their Solver prompt maximum "
                 f"({fam.OBSERVED_SOLVER_PROMPT_MAX:,} tokens over 5,400 Solver contacts; the 268-B lock arm 13,465 over 1,080) is {fam.PROMPT_LIMIT - fam.OBSERVED_SOLVER_PROMPT_MAX} tokens under the limit. "
                 "The Instruct-lock maximum of fit-measure-v1 (14,641 tokens) would NOT fit; it is not a Thinking-system prompt. The context-fit policy is compact-or-abstain."),
     "remedy": ("none needed on the observed data (the derive refuses if the estimate, the observed prompt maximum or the observed supplied count stops fitting); a later roster with a longer "
                "Solver prompt would compact or abstain at the gate, not stop the flight.")},
    {"id": "cell-level-thinking-policy-states-the-lock-form",
     "finding": (f"The serving fragment's own defaults carry the geometry cap (budget {fam.DELIVERING_BUDGET}, reserve {fam.FRAGMENT_CAP - fam.DELIVERING_BUDGET}, max_tokens {fam.FRAGMENT_CAP}); they are NOT the "
                 "delivering form. The baseline therefore carries a CELL-LEVEL thinking_policy that states the lock form (budget 3,072 + reserve 1,024 = cap 4,096) on both nodes, and the "
                 "candidate arm's policy overrides only its Solver. The delivering arm's wire form is the 268-B lock's (unit-tested)."),
     "remedy": "none."},
    {"id": "new-session-same-geometry",
     "finding": (f"A raised cap is a new serving fragment and session id ({fam.THINK_MODEL}, {fam.THINK_SESSION}, swap target {fam.SWAP_TARGET}); the resident session encodes max4096. "
                 f"max_tokens is a request parameter: the server arguments (-c 98304 -np 4: four {fam.ACTIVE_GEOMETRY['slot_tokens']:,}-token slots), the runtime receipt "
                 "(receipts/runtime-q4km-thinking-mmproj-free.json) and the np4 geometry row are the resident Thinking session's, unchanged (the derive proves that only three fragment leaves differ). "
                 "The swap target names two Windows scheduled tasks, SAEA-Serving-THINKB7 and SAEA-Monitor-THINKB7, which the coordinator registers (saea_task.ps1 pattern) before the first swap, "
                 "as for SAEA-Serving-THINKB."),
     "remedy": "register the two tasks and SAEA-Chain-NXT2B; the entry scripts are scripts/flights/direct/serving_task_entry_think_budget7168.sh and serving_monitor_start_think_budget7168.sh."},
    {"id": "cost-is-a-conservative-envelope",
     "finding": (f"The cost of the candidate arm scales the Solver's measured contact seconds (R1 both-on: {fam.NODE_SECONDS['solver']:.2f} s) by the budget ratio "
                 f"{max(a['solver']['budget_tokens'] for a in fam.ARM_SPECS)}/{fam.DELIVERING_BUDGET}; only the contacts that hit the forced close ({fam.R1['solver_forced_closes_at_3072']} of {fam.R1['solver_contacts']}) can "
                 "grow, so the model over-states the expected cost. The registered ceiling carries the 1.3 margin on top."),
     "remedy": "the smoke measures the real mix; the machine sign-off refuses unless it is within 1.3x of the registered one."},
    {"id": "serial-gpu-and-the-resident-session",
     "finding": ("Ruling 303 A: one experiment in flight. NX-T R2 occupies the Thinking session; this package is DRAFT / HELD until R2 has sealed (the queue hook "
                 "scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh waits for CHAIN_NXT2_EXIT rc=0, then flips and starts the chain; owner ruling 327 A). The chain swaps to the raised-cap session itself."),
     "remedy": "the coordinator registers (derive .. commit) while R2 flies; the hook does flip .. chain."},
    {"id": "preflight-defers-to-the-exact-gate",
     "finding": ("As in the 268-B cells the model-free preflight counts the payload at 4 bytes per token (a placeholder) and would refuse the Solver render at the cap; the cells defer to "
                 "the registered exact per-contact context-fit gate (preflight_budget_mode defer-to-native-contact-fit), which runs on every arm's REAL request."),
     "remedy": "none."},
    {"id": "flight-registration-check-does-not-yet-read-the-thinking-block",
     "finding": ("scripts/checks/flight_registration_check.py's node-column findings (aa-arm-missing, variant-cost-mismatch, template-summary-mismatch) read only the "
                 "Solver's template_variants block and are a no-op for a Perception-node group; the declaration is nevertheless complete (variant_cost, template_variants "
                 "summary with twin false) and stage3_effect_floor_check validates its shape."),
     "remedy": "widen NODE_COLUMN_PATH when the checker is next touched (not part of this package)."},
    {"id": "machine-signoff-with-a-veto-window",
     "finding": ("The chain waits for the smoke's sign-off with chain_lib.sh wait_or_machine_signoff (reader nxt_r2b_read.sh smoke, the conditions file the derive emits INSIDE this package, "
                 "marker /home/chao/nxt2b-decode-signoff.marker, veto window 20 minutes). A refused machine sign-off falls back to waiting for a coordinator marker (12 h)."),
     "remedy": "the coordinator may veto by deleting the marker or creating /home/chao/batch-STOP during the window."},
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


def setting_text(value: Mapping[str, int]) -> str:
    form = "the lock form: " if value == fam.DELIVERING_SETTING else ""
    return f"{form}thinking, budget {value['budget_tokens']} / reserve {value['completion_cap'] - value['budget_tokens']} / cap {value['completion_cap']}"


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
            "note": ("A per-node attribution, not a benefit claim: the question is whether untruncated Solver reasoning moves the score, so no effect is assumed "
                     f"({fam.EXPECTED_EFFECT_PP} pp SLU-F1) and the deliverable is the contrast with its cost (the throughput table). NO twin flies (owner decision 313 A): "
                     f"the null is the DECLARED same-core A/A offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets, 268-B +{fam.TWIN_OFFSET_268B_SLU_PP} "
                     f"and P3.1 {fam.TWIN_OFFSET_P31_SLU_PP}) with the paired floor {fam.PAIRED_FLOOR_PP} pp; the design resolves a per-arm contrast of {fam.FLOOR_SLU_PP} pp SLU / "
                     f"{fam.FLOOR_INTENT_PP} pp intent at n = 1,080 (decision 190 node-column floors), which are also the no-resolved-effect margins.")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form, per-arm per-node decode cost and the forced-close behaviour only)", "read_roster": fam.READ_ROSTER,
            "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"Four Fold B rows prove FORM only: the {fam.PROGRAM} module program with {fam.K} arms loads on the raised-cap Thinking session, each arm's requests carry their own "
                     "reasoning budget and cap, no node hits its cap, the live phase fit passes at the raised cap and the v5 receipt seals. "
                     "Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_inputs_seconds() -> dict:
    r1 = fam.R1
    return {"both_on_seconds_per_row": r1["seconds_per_row_both_on"], "perception_seconds_per_contact": fam.NODE_SECONDS["perception"],
            "solver_seconds_per_contact": fam.NODE_SECONDS["solver"], "gpu_hours_per_1080_row_pass": r1["gpu_hours_per_1080_row_pass"], "slots": r1["slots"]}


def cost_estimate() -> dict:
    expected = fam.expected_gpu_hours(fam.ROWS)
    return {
        "formula": (f"expected = rows x arm mix / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 with the arm mix {fam.ARM_MIX_ROWS} delivering-row equivalents per row "
                    f"({' + '.join(f'{a} {c}' for a, c in fam.ROW_COST.items())}); ceiling = ceil_0.1(expected x {fam.GPU_MARGIN}); each candidate cost is the predicted seconds per row "
                    "relative to the delivering arm's measured seconds per row, rounded UP to 0.01; rows per minute = 4 slots x 60 / the R1 both-on seconds per row, rounded DOWN to 0.01"),
        "cost_model": {
            "module": "scripts/flights/nx/nxt_r2b_family.py (relative_cost)",
            "inputs": (f"scripts/flights/nx/nxt_r2b_cost_inputs.json (the NX-T R1 both-on arm of TRAIN Fold B: Perception {fam.NODE_SECONDS['perception']:.2f} s and Solver "
                       f"{fam.NODE_SECONDS['solver']:.2f} s per contact, {fam.SECONDS_PER_ROW_BOTH_ON:.2f} s per row, {fam.R1['gpu_hours_per_1080_row_pass']:.2f} GPU-h per "
                       "1,080-row pass at 4 slots; source sha256 recorded there; numbers only)"),
            "form": "seconds(arm) = sum over nodes of node_seconds x (node budget / delivering budget); the delivering arm is the measured both-on seconds",
            "node_seconds": {k: round(v, 4) for k, v in fam.NODE_SECONDS.items()},
            "limits": ("covers only raised budgets (a node below the delivering budget is refused by name); the budget-ratio scaling is an upper envelope because only the contacts that hit "
                       "the forced close can grow"),
        },
        "inputs": {"row_cost_in_delivering_rows": fam.ROW_COST, "linear_reference_cost": fam.LINEAR_REFERENCE, "rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL,
                   "margin": fam.GPU_MARGIN, "r1_measured": cost_inputs_seconds()},
        "arm_mix_rows": fam.ARM_MIX_ROWS,
        "arm_table": arm_table_rows(),
        "column_flight": {"contacts": fam.program_calls("arm"), "plan_ceiling_calls": fam.original_generation_calls("arm"), "expected_gpu_hours": round(expected, 2),
                          "planned_ceiling_gpu_hours": fam.CELLS["arm"]["gpu_hours"],
                          "run_cumulative_plan_calls": fam.generation_calls("arm"), "run_cumulative_speech_audio_seconds": fam.cell_audio_cap("arm")},
        "smoke": {"contacts": fam.program_calls("smoke"), "planned_ceiling_gpu_hours": fam.CELLS["smoke"]["gpu_hours"]},
        "registered_total_gpu_hours": round(fam.CELLS["arm"]["gpu_hours"] + fam.CELLS["smoke"]["gpu_hours"], 1),
        "projected_lock_flight_gpu_hours": {a: round(fam.lock_flight_gpu_hours(a), 2) for a in fam.ARM_ORDER},
        "reference_r1": (f"one NX-T R1 both-on pass: 1,080 rows, {fam.R1['gpu_hours_per_1080_row_pass']:.2f} GPU-h at 4 slots ({fam.SECONDS_PER_ROW_BOTH_ON:.1f} s per row); the 268-B lock arm "
                         "spent about 9.4 GPU-h against an 8.4 ceiling (the lesson of the measured-throughput rule)"),
        "fallback_note": (f"The answer-only fallback adds at most one contact per budgeted-thinking contact: {fam.THINKING_CONTACTS_PER_ROW} per row (the delivering arm's 2 plus one per "
                          f"candidate node); planned_model_calls is rows x ({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = "
                          f"{fam.original_generation_calls('arm')} (program maximum {fam.program_calls('arm')}). The runner requires only rows x ({fam.CONTACTS_PER_ROW} + 2). "
                          f"The FIT cap stays structural (rows x program contacts x endpoints = {fam.fit_contact_cap(fam.ROWS)})."),
    }


def context_fit() -> dict:
    """The context-fit proof of the raised cap, registered in the fit plans and the facts (the derive refuses when it is not ok)."""

    return fam.fit_proof()


def existing_plan(root: Path, pkg: str, key: str) -> dict | None:
    """The cell's committed generation plan (rec1 name first, then the first-attempt name), or ``None`` on a first registration."""

    spec = fam.CELLS[key]
    for name in (fam.plan_file_name(key, "generation"), rcv.plan_file_name(spec["prefix"], "generation", False)):
        path = Path(root) / pkg / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str, recov: Mapping[str, Mapping] | None = None) -> dict:
    docs = {}
    arms_doc = {arm: ({"thinking_policy": fam.POLICIES[arm], "settings": dict(zip(fam.NODES, fam.SETTINGS[arm]))} if arm in fam.POLICIES else
                      {"thinking_policy": None, "role": "delivering", "settings": dict(zip(fam.NODES, fam.SETTINGS[arm]))}) for arm in fam.ARM_ORDER}
    fit_block = fam.fit_proof()
    for key in fam.ALL_KEYS:
        i = ids[key]
        spec = fam.CELLS[key]
        base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": spec["session"], "experiment": i["experiment"],
                "family_budget": i["family_budget"], "preparation_base_commit": commit,
                "prepared_phase_supply": {"relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "note": "the flip mints this cell's own first-phase supply under its own run id (item E16)"},
                "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha}, "registered_at_utc": at, "status": STATUS,
                "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": None,
                "thinking_arms": json.loads(json.dumps(arms_doc)), "arm_order": list(fam.ARM_ORDER), "unused_budget_is_not_attempt_authority": True,
                "budget_node": json.loads(json.dumps(fam.BUDGET_NODE_KNOBS)), "no_twin": True,
                "cell_thinking_policy": json.loads(json.dumps(fam.DELIVERING_NODE_POLICY)),
                "serving": {"swap_target": fam.SWAP_TARGET, "session": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "geometry_cap": fam.FRAGMENT_CAP,
                            "server_geometry": f"-c {fam.ACTIVE_GEOMETRY['slots'] * fam.ACTIVE_GEOMETRY['slot_tokens']} -np {fam.ACTIVE_GEOMETRY['slots']} (unchanged)"},
                "one_factor": ("The Solver's reasoning budget and completion cap in the candidate arm (reasoning_budget_tokens b with answer_reserve_tokens cap - b at the Solver). The "
                               f"delivering arm is the 268-B lock form (budget {fam.tsf.THINK_BUDGET_TOKENS} + reserve {fam.tsf.THINK_ANSWER_RESERVE_TOKENS} = cap "
                               f"{fam.tsf.THINK_MAX_TOKENS}) on both nodes; the system, the knowledge supply, the sealed query vectors and the roster are the 268-B lock's.")}
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
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"],
                   run_id=i["run_id"], schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        route = ("Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored." if key == "smoke" else
                 f"Shared core.flight.cli campaign over {spec['campaign']} on the raised-cap Thinking session ({fam.THINK_SESSION}); one official score per arm column "
                 "(stage3_rollout_score --mode perception-branches) after the seal. Flown by scripts/flights/nx/batch_chain_nxt_r2b.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of NX-T R2b.",
            "scoring": "Per-arm official column scoring after a successful seal; no partial score." if key != "smoke" else "None: the smoke is never scored."}
        fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        docs[fam.plan_file_name(key, "fit")] = {
            **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "context_fit": json.loads(json.dumps(fit_block)),
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."}
    return docs


LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = reg.LEDGER_INHERITED
RECOVERY_LEDGER_MARK = "## Cell NXT-R2B recovery rec1: "
RECOVERY_AUTHORITY = f"{fam.OWNER_RULINGS} (the Solver reasoning-budget raise) and the generic recovery re-registration (owner decision 309 A)"
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
                 (f"The offline read of NX-T R2b: score the {fam.K} arm columns of the sealed column flight once each with the official scorer (stage3_rollout_score "
                  f"--mode perception-branches); the paired contrast of the candidate arm against the delivering {fam.DELIVERING} arm, the node words against the declared A/A offset, the per-scenario table and the "
                  f"per-arm per-node completion / finish-reason / cap-hit / empty / forced-close / throughput tables by the recipe {pkg}/analysis-recipe-v1.json. "
                  "Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp TRAIN Fold B {arm['rows']}, the sealed column flight (after the seal)", "discovery", arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the column flight is sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 323 and 325 A of 2026-10-17 "
            "and 313 A of 2026-10-14 (does untruncated Solver reasoning move the score: the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/nx/nxt_r2b_mint_receipt.py after this countersignature; the READ row "
            "stays a draft until the column flight is sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        if fam.recovery(key):
            spec = fam.CELLS[key]
            clause = (f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator "
                      f"(nxt_r2b_mint_receipt.py --supersede) so that its eligible_run_ids list the new FIT run id {i['fit_run_id']}")
            for run, label in ((i["run_id"], f"the {spec['role']}"), (i["fit_run_id"], f"live phase-fit identity of the {spec['role']}")):
                rows[run] = rcv.countersign_text(
                    fam.RECOVERIES, key, authority=RECOVERY_AUTHORITY, role=spec["role"], label=label, attempt=i["attempt_id"], fit_run=i["fit_run_id"],
                    fit_attempt=i["fit_attempt_id"], receipt_clause=clause, tail="the READ row stays a draft until the column flight is sealed")
            continue
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 323 and 325 A of "
                             "2026-10-17 and 313 A of 2026-10-14; the column flight is sealed at its flight commit and the sealed run was not opened for any number before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any]) -> str:
    arm, smoke = ids["arm"], ids["smoke"]
    cf = cost["column_flight"]
    fit = fam.fit_proof()
    arm_rows = "\n".join(
        f"| `{r['arm']}` | {setting_text(r['perception'])} | {setting_text(r['solver'])} | {r['role']}{' (= the 268-B lock form)' if r['role'] == 'delivering' else ''} | "
        f"{r['cost_in_delivering_rows']} | {r['linear_reference_cost'] if r['linear_reference_cost'] is not None else 1.0} |" for r in cost["arm_table"])
    lock_rows = "\n".join(f"| `{a}` | {h} |" for a, h in cost["projected_lock_flight_gpu_hours"].items())
    r1 = fam.R1
    return (
        "# NX-T R2b: the Solver reasoning-budget raise on the Thinking core, TRAIN Fold B (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/nx/nxt_r2b_write_registration.py` from the fragments `nxt_r2b_derive_cells.py` wrote, from the arm table `scripts/flights/nx/nxt_r2b_arms.json`. "
        "The NX-T R2 package (`docs/readiness/2026-10-15-slurp-nxt-r2-thinking-budget-fold-b-v1/`) is the worked example and is unchanged.\n\n"
        "## The question (owner rulings 323 and 325 A)\n\n"
        f"NX-T R1 read the Solver NEEDS-THINKING and measured {r1['solver_forced_closes_at_3072']} of {r1['solver_contacts']} Solver contacts closed by the {fam.DELIVERING_BUDGET}-token budget "
        f"(completion p90 {r1['solver_completion_tokens_p90']:.0f}): its reasoning is truncated. NX-T R2b raises the Solver's reasoning budget and completion cap so that Solver reasoning is "
        "no longer truncated, in ONE candidate arm beside the delivering arm, one flight, one roster, a same-flight COLUMN. Every arm contacts Perception and the Solver; the arms "
        "differ ONLY in the reasoning budget and completion cap of the Solver contact (the Perception node, the completion cap 4,096 of every other node and `drop-reasoning-v1` stay).\n\n"
        "## Arms (declared order; the delivering arm LAST; no twin)\n\n"
        "| arm | Perception | Solver | role | cost in delivering rows | linear reference |\n| --- | --- | --- | --- | ---: | ---: |\n"
        f"{arm_rows}\n\n"
        "The arm kind is `roles.perception.thinking_variants` (rails.supply_variants.parse_perception_thinking_variants; receipt `saea-perception-branch-arms-v5`, UNCHANGED; "
        "the consumption module's `thinking` column kind compiles it). The candidate arm states `reasoning_budget_tokens` b and `answer_reserve_tokens` cap - b at its Solver, "
        f"so the wire form is `thinking_budget_tokens` {max(a['solver']['budget_tokens'] for a in fam.ARM_SPECS)} / `max_tokens` {fam.FRAGMENT_CAP} on the Solver ONLY. "
        "**The arm table carries a completion cap per node setting** (R2's table had one global cap): a budget above the delivering one is accepted only with a cap >= budget + 1,024; "
        "a node at or below the delivering budget keeps the cap 4,096; no cap exceeds the serving fragment's geometry cap (the largest cap of the table, which names the fragment).\n\n"
        "### Thinking-control knobs (one place: `thinking_system_family.THINKING_KNOBS`, re-used unchanged)\n\n"
        f"* the delivering form: `thinking_budget_tokens` {fam.THINKING_KNOBS['thinking_budget_tokens']} + answer reserve {fam.THINKING_KNOBS['answer_reserve_tokens']} = "
        f"completion cap {fam.THINKING_KNOBS['completion_cap']}, `reasoning_context_policy` `{fam.THINKING_KNOBS['reasoning_context_policy']}`, temperature 0, seed 20260913, "
        f"forced-close message (`--reasoning-budget-message`): \"{fam.THINKING_KNOBS['budget_message']}\";\n"
        "* because the serving fragment's own defaults carry the geometry cap (budget 3,072, reserve 4,096, max_tokens 7,168), the baseline states the delivering form as a "
        "**cell-level `thinking_policy`** on both nodes ({perception, solver}: reasoning_budget_tokens 3072, answer_reserve_tokens 1024); the candidate arm's policy overrides only its Solver "
        "(`reasoning_budget_tokens` 6144, `answer_reserve_tokens` 1024). The delivering arm's request is the lock's, byte for byte (unit-tested through the real request composer);\n"
        f"* model fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}`, swap target `{fam.SWAP_TARGET}`.\n\n"
        "## Serving: a new session, the same server geometry\n\n"
        f"`max_tokens` is a request parameter, so the raised cap changes no GPU allocation. The fragment `{fam.THINK_MODEL}` is the resident np4 Thinking fragment "
        f"(`{fam.CONTROL_FRAGMENT}`) with three leaves changed (`decoding_params.max_tokens` 4096 -> {fam.FRAGMENT_CAP}, `answer_reserve_tokens` 1024 -> {fam.FRAGMENT_CAP - fam.DELIVERING_BUDGET}, "
        "`geometry_basis`); `server_args` (`-c 98304 -np 4`, q8_0 KV, `--reasoning-format deepseek`, the same `--reasoning-budget-message`), `runtime_receipt` "
        "(`receipts/runtime-q4km-thinking-mmproj-free.json`, the Thinking runtime receipt the np4 geometry row reads), `speech_feature_root` and `server_env` are identical (the derive proves it: "
        f"`fragment` in `registered-facts-v1.json`). The geometry row is `scripts/flights/batch/serving_lib.sh` target `{fam.SWAP_TARGET}` (resolved through "
        f"`nxt_r2b_family.ACTIVE_GEOMETRY`: {fam.ACTIVE_GEOMETRY['slots']} slots x {fam.ACTIVE_GEOMETRY['slot_tokens']:,} tokens, the np4 geometry of NX-T R2), wired exactly as `think-budget-np4` "
        "(entry scripts `serving_task_entry_think_budget7168.sh` / `serving_monitor_start_think_budget7168.sh`, Windows tasks `SAEA-Serving-THINKB7` / `SAEA-Monitor-THINKB7`, "
        "which the coordinator registers before the first swap). The smoke and the column flight both run on this session.\n\n"
        "## Context fit at the raised cap (refused at derive if it does not hold)\n\n"
        "| quantity | tokens |\n| --- | ---: |\n"
        f"| live slot | {fit['slot_tokens']:,} |\n| operational reserve | {fit['reserve_tokens']:,} |\n| special reserve | {fit['special_reserve_tokens']} |\n"
        f"| completion cap of the cell (the fit gate's ceiling) | {fit['completion_cap']:,} |\n| prompt limit of every contact | {fit['prompt_limit_tokens']:,} |\n"
        f"| registered estimate at the lock's {fit['lock_max_supplied_items']} items (base 2,000 + 235 per item) | {fit['lock_bound_estimate_tokens']:,} (does NOT fit) |\n"
        f"| registered estimate at the bound {fit['max_supplied_items']} items | {fit['estimate_at_bound_tokens']:,} (headroom {fit['estimate_headroom_tokens']}) |\n"
        f"| observed Solver prompt maximum, sealed Fold B flights (268-B lock 1,080 contacts: 13,465; NX-T R1 five arms 5,400 contacts: {fit['observed_solver_prompt_tokens_max']:,}) | {fit['observed_solver_prompt_tokens_max']:,} (headroom {fit['observed_headroom_tokens']}) |\n"
        f"| observed supplied items, 5,400 branch rows | at most {fit['observed_supplied_count_max']} |\n\n"
        "The registered estimate cannot hold the lock's 55-item bound at the 7,168 cap, so the `thinking_variants` bound is 52 (see finding `fit-bound-52-not-55-at-the-raised-cap`); the "
        "observed prompts and supplied counts fit. The Instruct-lock maximum of fit-measure-v1 (14,641) does not fit and is not a Thinking-system prompt.\n\n"
        "## What the arms share, and what they do not (coordinator rulings 1 and 2)\n\n"
        "* Shared by every arm: the evidence blocks, the instruction templates, the QueryState, the speech packet, the module program, the knowledge supply, the "
        "roster, the model fragment and the serving session.\n"
        "* NOT shared: independent chains, no note sharing. The candidate arm's Solver prompt carries THAT arm's own Perception note (its Perception is the lock form, so the notes should agree, but they are separate contacts).\n\n"
        "## Registered cells\n\n"
        "| cell | role | rows | program contacts | plan calls | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.program_calls(k):,} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | "
                    f"`{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |" for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the 268-B Thinking lock cell, derived by `nxt_r2b_derive_cells.py` with exactly two additions (the Perception `thinking_variants` block, compiled by the "
        f"module compiler, and the cell-level thinking policy): lock `{fam.LOCK}`, program `{fam.PROGRAM}` ({fam.CONTACTS_PER_ROW} = 2 + 2 ({fam.K} - 1) contacts per row), the Thinking model "
        f"fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}` (swap target `{fam.SWAP_TARGET}`), the Thinking packets and their promotion receipt "
        f"(`{fam.THINK_PROMOTION_RECEIPT}`), the fold-excluded knowledge supply and the roster `{fam.ROSTER['arm']}` (1,080 rows); the smoke is the loop's own four "
        f"Fold B rows (`{fam.ROSTER['smoke']}`). `preflight_budget_mode` is `defer-to-native-contact-fit`; the finite-completion policy is "
        "`deliver-latest-or-abstain` and the ReAct-exhaustion policy `continue-without-answer`. The derive proves the leaves that moved against the 268-B parent "
        "(`moved_by_rule`): the `thinking_variants` block and its declaration, the cell-level thinking policy, the program id (the ceiling is its suffix), the live-fit ids and cap, the "
        "cell's own supply pin and the cell text; nothing else.\n\n"
        "## GPU ceiling (from measured throughput)\n\n"
        f"{cost['formula']}.\n\n"
        f"* Cost model: `{cost['cost_model']['module']}`, from {cost['cost_model']['inputs']}. Form: {cost['cost_model']['form']}. Limits: {cost['cost_model']['limits']}.\n"
        f"* Arm mix {cost['arm_mix_rows']} delivering-row equivalents per row ({' + '.join(f'{a} {c}' for a, c in fam.ROW_COST.items())}); 1,080 rows at {fam.ROWS_PER_MINUTE_FULL} rows per minute: "
        f"expected {cf['expected_gpu_hours']} GPU-h, registered ceiling {cf['planned_ceiling_gpu_hours']} GPU-h = ceil_0.1({cf['expected_gpu_hours']} x {fam.GPU_MARGIN}) "
        f"({cf['contacts']:,} program contacts, plan ceiling {cf['plan_ceiling_calls']:,} calls including at most {fam.THINKING_CONTACTS_PER_ROW} fallback re-asks per row).\n"
        f"* Smoke: {cost['smoke']['contacts']} program contacts, ceiling {cost['smoke']['planned_ceiling_gpu_hours']} GPU-h. Registered total {cost['registered_total_gpu_hours']} GPU-h.\n"
        f"* {cost['reference_r1']}.\n\n"
        "Projected GPU-h of a 1,080-row LOCK flight that ran one arm's setting on both nodes, at the registered rate (the model's prediction; the read replaces it "
        "with the flight's measured seconds):\n\n| arm | projected GPU-h per 1,080-row lock flight |\n| --- | ---: |\n"
        f"{lock_rows}\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        "## Chain sequence (the coordinator's; flip and chain are the queue hook's)\n\n"
        "1. Register while R2 flies (model-free, master clean): `bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r2b_launch_spec.json --root-countersign --until commit` "
        "(derive, write, countersign the five DRAFT rows, mint the receipt with `scripts/flights/nx/nxt_r2b_mint_receipt.py`, commit). Register the Windows tasks `SAEA-Serving-THINKB7`, "
        "`SAEA-Monitor-THINKB7` and `SAEA-Chain-NXT2B` (wrapper `/home/chao/saea-queue/chain_nxt2b.sh`, source `scripts/flights/batch/queue/chain_nxt2b.sh`).\n"
        "2. Install the queue hook: `cp scripts/flights/batch/queue/queue_nxt2b_after_nxt2.sh /home/chao/saea-queue/` and start it with the R2 start stamp as its first argument. It waits "
        "(poll 60 s, at most 30 h) for a `CHAIN_NXT2_EXIT rc=0` line in `/home/chao/nxt2-chain.out` stamped after that start, then runs `bash scripts/flights/batch/package_launch.sh "
        "scripts/flights/nx/nxt_r2b_launch_spec.json --from flip --until chain` from the master checkout and logs to `/home/chao/nxt2b-queue.out`; on an R2 exit with rc != 0 it logs and "
        "exits 9 without launching.\n"
        "3. The flip (`bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r2b_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {ids['smoke']['experiment']},{ids['arm']['experiment']} --pins-commit-msg /home/chao/nxt2b-pins-commit.txt`, `NXT2B_KINDS=\"smoke arm\"`) records the "
        "flight commit in `/home/chao/nxt2b-flight-commit.txt`; the pins message is `/home/chao/nxt2b-pins-commit.txt` (written from the spec).\n"
        f"4. The chain `bash scripts/flights/nx/batch_chain_nxt_r2b.sh all` swaps to `{fam.SWAP_TARGET}` when that session is not resident (hold the idle watchdog), flies the smoke, "
        "waits for the sign-off with `wait_or_machine_signoff` (reader `bash scripts/flights/nx/nxt_r2b_read.sh smoke`, conditions "
        f"`{fam.SIGNOFF_CONDITIONS}`, marker `/home/chao/nxt2b-decode-signoff.marker`, veto window 20 minutes), flies the column and closes the exposure rows with `close_rows_after_seal`. "
        "`arm-only` is the rec1 re-fly segment (smoke sealed, marker present).\n"
        "5. `bash scripts/flights/nx/nxt_r2b_read.sh columns` (the official per-arm scoring; prints no number), countersign the READ row, then `bash scripts/flights/nx/nxt_r2b_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}` (the NX-T R2 reader, parameterised by this family): every arm's first Solver answer is scored once, complete, by the official scorer; the candidate arm minus the delivering "
        f"`{fam.DELIVERING}` arm, SLU-F1 and intent, paired per row, utterance-cluster bootstrap (10,000 draws, seed 20261015). NO twin flies, so the null is the DECLARED "
        f"same-core A/A offset |o| = {fam.DECLARED_OFFSET_SLU_PP} pp SLU (the larger of the two measured offsets: 268-B +{fam.TWIN_OFFSET_268B_SLU_PP} / intent {fam.TWIN_OFFSET_268B_INTENT_PP}; "
        f"P3.1 {fam.TWIN_OFFSET_P31_SLU_PP} / intent +{fam.TWIN_OFFSET_P31_INTENT_PP}) and the paired floor is {fam.PAIRED_FLOOR_PP} pp (decisions 172/231/313). The R2 words (GAIN / "
        "NEEDS-FULL-BUDGET / CHEAPER-AT-NO-RESOLVED-LOSS / UNRESOLVED) describe a budget BELOW the delivering one; for an arm whose budget is ABOVE it the wording inverts, and R2b "
        "uses these words (fixed here, in the reader; the first that applies):\n\n"
        + "\n".join(f"* **{w}**: {t}." for w, t in WORD_RULES.items()) + "\n\n"
        "The read also reports, per arm and node: completion tokens (mean / p50 / p90 / p99 / max), the finish-reason table, cap hits against each node's own cap, empty completions, FORCED CLOSES (contacts "
        "that hit the budget), reasoning-character and think-marker counts, seconds per contact, and the THROUGHPUT table (seconds per row, rows per minute at 4 slots, GPU-h per "
        "1,080-row lock flight at each budget, each arm's measured cost in delivering rows beside the registered cost). claims_benefit is false; development numbers only "
        "(owner decisions 28 and 86).\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate and model, context-fit proof, serving-fragment proof, knobs, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the four plans (smoke, column flight; each generation and FIT; the FIT plans carry the context-fit proof) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `signoff-conditions-v1.json` | the machine sign-off conditions, EMITTED BY THE DERIVE from the arm table (regenerated whenever the table changes) |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `nxt_r2b_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the five DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md` by `--append-ledger`) |\n\n"
        "## Registration check of a HELD package\n\n"
        "`python -B scripts/checks/flight_registration_check.py --cell <cell> [--cell <cell>]` on the two cells reports the held state and the missing countersignatures; it is run before the "
        "countersign and read by the coordinator (its node-column findings do not yet read the Perception thinking block, finding `flight-registration-check-does-not-yet-read-the-thinking-block`).\n")


def original_registered_at(root: Path) -> str:
    """The first registration's stamp (kept by a recovery: the plans, protocol and facts keep their original ``registered_at_utc``; the recovery
    carries its own stamp in its ``recovery`` block)."""

    return json.loads((Path(root) / fam.package_file("registered-facts-v1.json")).read_text(encoding="utf-8"))["registered_at_utc"]


def verify_snapshots(root: Path, data_root: str | None) -> dict:
    """Re-read each predecessor's attempt record on the data root and compare it with the committed snapshot receipt (skipped, and said so, when the
    data root or the record is absent: a CI checkout has no data root). A disagreement raises."""

    out = {}
    for key in fam.ALL_KEYS:
        if not fam.recovery(key):
            continue
        snap = rcv.load_snapshot(Path(root) / fam.PREDECESSOR_SNAPSHOT[key])
        record = Path(data_root or "/nonexistent") / "attempts" / snap["run_id"] / f"{snap['attempt_id']}.json"
        if data_root and record.is_file():
            fresh = rcv.verify_predecessor_snapshot(snap, data_root)
            out[key] = {"verified": True, "state_now": fresh["state"], "actual_calls": fresh["actual_calls"],
                        "actual_audio_seconds": fresh["actual_audio_seconds"]}
        else:
            out[key] = {"verified": False, "reason": "no attempt record on the data root (snapshot receipt used as committed)"}
    return out


def recovery_blocks(root: Path, ids: Mapping[str, Mapping], at: str, recovery_at: str, recovery_base: str, worktree: str, branch: str) -> dict:
    """The recovery ledger block (two DRAFT rows) of every recovered cell, keyed by cell key."""

    out = {}
    for key in fam.ALL_KEYS:
        if not fam.recovery(key):
            continue
        i, spec = ids[key], fam.CELLS[key]
        scope = f"Cell NXT-R2B {spec['role']} -- RECOVERY rec1: {SCOPE}; re-flown whole after the host restart that killed the first attempt"
        out[key] = rcv.recovery_ledger_block(
            fam.RECOVERIES, key, mark=RECOVERY_LEDGER_MARK, authority=RECOVERY_AUTHORITY, package=fam.PACKAGE, role=spec["role"], run=i["run_id"],
            fit_run=i["fit_run_id"], attempt=i["attempt_id"], fit_attempt=i["fit_attempt_id"], session=fam.THINK_SESSION, scope=scope,
            fit_scope=f"Cell NXT-R2B {spec['role']} -- RECOVERY rec1 live phase-fit spend identity, request envelopes only, no generation.",
            model_tool=fam.think_model_text(key), carrier=f"slurp TRAIN Fold B {i['rows']:,}", split_hash=i["split_identity_hash"], caps=i["family_budget"],
            config_hash=i["composed_config_hash"], protocol_hash=i["protocol_hash"], registered_at=recovery_at, base_commit=recovery_base,
            worktree=worktree, branch=branch, plan_names=(fam.plan_file_name(key, "generation"), fam.plan_file_name(key, "fit")), inherited=INHERITED)
    return out


def recovery_markdown(ids: Mapping[str, Mapping]) -> str:
    """The README / preregistration recovery text: one section per recovered cell."""

    out = ""
    for key in fam.ALL_KEYS:
        if not fam.recovery(key):
            continue
        i, spec = ids[key], fam.CELLS[key]
        out += rcv.recovery_section(
            fam.RECOVERIES, key, role=spec["role"], run=i["run_id"], attempt=i["attempt_id"], fit_run=i["fit_run_id"], fit_attempt=i["fit_attempt_id"],
            caps=i["family_budget"], plan_names=(fam.plan_file_name(key, "generation"), fam.plan_file_name(key, "fit")))
    return out


def recovery_sequence_text(ids: Mapping[str, Mapping]) -> str:
    """The coordinator's recovery sequence (README only)."""

    arm = ids["arm"]
    return (
        "\n### Recovery sequence (the coordinator's; it replaces steps 1 to 4 above for the recovered column flight)\n\n"
        "0. (Before the writer.) Snapshot the failed attempt and commit the diagnosis: `python -B scripts/flights/lib/recovery.py snapshot --data-root $SPEECHRL_DATA_DIR "
        f"--run-id {arm['run_id']} --attempt-id <failed attempt id> --fit-run-id <fit run id> --fit-attempt-id <fit attempt id> --out {fam.PREDECESSOR_SNAPSHOT['arm']}`, and write "
        f"`{fam.RECOVERY_INPUT['arm']}` with the keys {', '.join(fam.RECOVERY_INPUT_KEYS)} (the family builds the recovery from these two files; no other edit).\n"
        "1. Re-run the writer on master with the recovery ledger block: `python -B scripts/flights/nx/nxt_r2b_write_registration.py --study-commit <sha> "
        "--recovery-registered-at <UTC> --append-recovery-ledger`.\n"
        f"2. Countersign the two new rows (`{arm['run_id']}` recovery row, `{arm['fit_run_id']}`) with `countersign-row-texts-v1.json`; fold the first-attempt "
        "generation row of the same run id into the recovery row.\n"
        "3. `python scripts/flights/nx/nxt_r2b_mint_receipt.py --supersede` (the old receipt is renamed to a dated backup first; the new receipt lists the "
        "rec1 FIT run id and carries the recovery block and the new plan sha256).\n"
        "4. The flip converges the arm cell (its readiness block pins the decision receipt, whose sha256 changed); the sealed smoke is NOT flipped again: "
        f"`NXT2B_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r2b_flip.sh\" --package {fam.PACKAGE} --cells "
        f"{arm['experiment']} --pins-commit-msg /home/chao/nxt2b-pins-commit.txt`; then re-run the writer once at the flipped bytes.\n"
        "5. Hold the idle watchdog; `bash scripts/flights/nx/batch_chain_nxt_r2b.sh arm-only` (refuses unless the smoke is sealed and the sign-off marker exists; `all` refuses "
        "because it would re-fly the sealed smoke; it swaps to the raised-cap session itself when it is not resident).\n"
        "6. Optional hygiene: mark the OPENED predecessor attempt aborted (`AttemptStore.abort_if_opened`); its realised spend counts either way.\n")


def file_sha256(root: Path, relpath: str) -> str:
    return hashlib.sha256((Path(root) / relpath).read_bytes()).hexdigest()


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
    if not derived:
        dc.write_signoff_conditions(repo_root=root)             # the conditions follow the arm table even without a full re-derive
    loader = {k: (derived["cells"][k]["loader_verification"] if derived else {"ok": True}) for k in fam.ALL_KEYS}
    pkg = fam.PACKAGE
    ids = identities(root)
    arm, smoke = ids["arm"], ids["smoke"]
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {a: (fam.POLICIES[a] if a in fam.POLICIES else "the delivering arm = the 268-B lock form (budget 3,072 / cap 4,096 on both nodes)")
                 for a in fam.ARM_ORDER},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The node words and their thresholds are fixed in {fam.READER_IMPL} (raise mode) and in this package's README: GAIN, HARM, "
                                     "NEEDS-NO-MORE-BUDGET, UNRESOLVED against the declared A/A offset and the decision-190 node-column floors (no twin flies)."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the Solver's reasoning budget and completion cap in the candidate arm; the system is the 268-B Thinking lock on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-nxt-r2b-solver-budget-fold-b-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": ("Does raising the Solver's reasoning budget and completion cap, so that its reasoning is no longer truncated, move the score of the locked Thinking system "
                         f"(owner rulings 323 and 325 A)? The candidate arm is read PAIRED per row against the delivering {fam.DELIVERING} arm on the same 1,080 Fold B rows in one "
                         "flight, against the declared A/A offset (no twin).")}
    snapshot_refs = {k: {"path": fam.PREDECESSOR_SNAPSHOT[k], "sha256": file_sha256(root, fam.PREDECESSOR_SNAPSHOT[k])} for k in recov}
    if recov:
        protocol["recovery"] = json.loads(json.dumps(recov))
        protocol["predecessor_snapshots"] = snapshot_refs
        protocol["superseded_attempt_ids"] = [a for k in recov for a in (fam.recovery(k)["predecessor_attempt_id"], fam.recovery(k)["predecessor_fit_attempt_id"])]
        protocol["recovery_note"] = " ".join(f"[{fam.CELLS[k]['role']}] {fam.recovery(k)['reason']}" for k in recov)
        protocol["failure_policy"] += " Recovery rec1 is spent for a recovered cell: a second failure closes it."
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, recov)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    for key in recov:
        for stale in fam.superseded_plan_file_names(key):       # the first-attempt plans are superseded: removed from the package (git keeps them)
            if (root / pkg / stale).is_file():
                (root / pkg / stale).unlink()
    shas["protocol-registered-v1.json"] = protocol_sha
    shas["signoff-conditions-v1.json"] = file_sha256(root, f"{pkg}/signoff-conditions-v1.json")
    recipe = {
        "authority": f"{DECISIONS} ({fam.OWNER_RULINGS}); {SPEC}; {INSTRUMENT}",
        "cell_kind": f"SAME-FLIGHT NODE COLUMN over the Solver reasoning budget and completion cap -- {fam.K} arms (no twin) paired per row against the delivering {fam.DELIVERING} arm; claim ceiling nominated",
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
            "1_columns": "bash scripts/flights/nx/nxt_r2b_read.sh columns  (stage3_rollout_score --mode perception-branches: one complete official scoring per arm; no number printed)",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/nx/nxt_r2b_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-arm per-node decode cost; no countersignature; the machine sign-off input for the column flight)"},
        "verdict_words": list(WORD_RULES), "word_rules": WORD_RULES, "word_mode": fam.WORD_MODE,
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
        "fragment": dc.fragment_proof(root),
        "findings": FINDINGS, "identity": ids,
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET,
                 "reference_fragment": fam.CONTROL_FRAGMENT,
                 "speech_packet_root": fam.THINK_PACKET_ROOT, "speech_packet_promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                 "speech_packet_promotion_receipt_sha256": fam.thinking_promotion_sha256(),
                 "signoff_conditions": {"path": f"{pkg}/signoff-conditions-v1.json", "sha256": shas["signoff-conditions-v1.json"]}},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{fam.OWNER_RULINGS}; {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "read_rule": {"reader": fam.READER, "reader_impl": fam.READER_IMPL, "words": WORD_RULES, "word_order": list(WORD_RULES), "word_mode": fam.WORD_MODE,
                      "declared_offset_slu_pp": fam.DECLARED_OFFSET_SLU_PP,
                      "paired_floor_pp": fam.PAIRED_FLOOR_PP, "floors_pp": {"slu": fam.FLOOR_SLU_PP, "intent": fam.FLOOR_INTENT_PP}, "twin": None,
                      "delivering": fam.DELIVERING},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": arm["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": None,
        "cell_thinking_policy": json.loads(json.dumps(fam.DELIVERING_NODE_POLICY)),
        "thinking_arms": {a: (fam.POLICIES.get(a)) for a in fam.ARM_ORDER}, "status": "DRAFT-HELD"}
    if recov:
        facts["recovery"] = json.loads(json.dumps(recov))
        facts["predecessor_snapshots"] = snapshot_refs
        facts["recovery_budget"] = {k: rcv.recovery_budget(fam.RECOVERIES, k, ids[k]["family_budget"]) for k in recov}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/nx/nxt_r2b_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"{fam.OWNER_RULINGS}; {INSTRUMENT}; {SPEC}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": f"Fly the Solver reasoning-budget raise on the Thinking core on TRAIN Fold B: four-row smoke, then the {fam.K}-arm column flight (no twin).",
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
        draft["supersedes_receipt"] = {"path": fam.DECISION_RELPATH, "note": ("the first-registration receipt lists the first four run ids; this one appends the rec1 FIT "
                                                                           "run id. nxt_r2b_mint_receipt.py --supersede renames the old receipt to a dated backup first.")}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(row_cells)} unconsumed rows -- the cells still on their first attempt (generation row and live-phase-fit identity each) and the READ row; a "
             f"recovered cell's two rows follow this table as a recovery block -- for NX-T R2b of the owner rulings in {fam.OWNER_RULINGS}. "
             f"Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: the raised-cap Thinking session is the np4 geometry's new session "
             f"(swap target {fam.SWAP_TARGET}); its serving row is the coordinator's at the swap.",
             "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(cells) for cells in row_cells]
    rows_text = "\n".join(lines) + "\n"
    blocks = recovery_blocks(root, ids, at, recovery_at, recovery_base, recovery_worktree, recovery_branch)
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text + "".join(blocks.values()))
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    recovery_md = recovery_markdown(ids)
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost) + recovery_md + (recovery_sequence_text(ids) if recov else ""))
    prereg = (f"# NX-T R2b: the Solver reasoning-budget raise, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
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
                        help="append ONLY the recovered cell's two DRAFT rows (rec1) as a new ledger block; idempotent on the rec1 attempt id")
    parser.add_argument("--recovery-registered-at", default=None,
                        help="UTC timestamp of the recovery re-registration (default: now); recorded in the recovery plan and ledger rows")
    parser.add_argument("--recovery-base-commit", default=None, help="the commit the recovery was registered on top of (default: --study-commit)")
    parser.add_argument("--recovery-branch", default="sonnet/nxt2b-rec1")
    parser.add_argument("--recovery-worktree", default="/home/chao/saea-worktrees/sonnet-nxt2b-rec1")
    parser.add_argument("--data-root", default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR"),
                        help="re-verify the predecessor snapshot against this data root when its attempt record is present")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive,
                           recovery_at=args.recovery_registered_at, recovery_base=args.recovery_base_commit,
                           append_recovery_ledger=args.append_recovery_ledger, recovery_worktree=args.recovery_worktree,
                           recovery_branch=args.recovery_branch, data_root=args.data_root)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
