#!/usr/bin/env python3
"""Write the DRAFT readiness package of NX-T R1 (the per-node thinking-policy column on the Thinking core, TRAIN Fold B), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration.

    python -B scripts/flights/nx/nxt_r1_write_registration.py --study-commit <sha> [--registered-at 2026-10-13T12:00:00.000000+00:00]
        [--root DIR] [--append-ledger] [--no-derive]
        [--recovery-registered-at <UTC>] [--recovery-base-commit <sha>] [--append-recovery-ledger]

RECOVERY rec2 (owner ruling 320 B, 2026-10-16): the SECOND recovery of the run id, under an explicit owner exception to the one-recovery rule, is a mode-A
RESUME of the stopped rec1 attempt: ``resume_from`` (trace sha256 read from the data root into the committed rec2 snapshot) keeps the complete rows and flies the
rest. The same flags drive it; the generation plan then carries ``resume_from``, ``resume_budget`` and (when ``resume-replay-proof-rec2-v1.json`` is committed) the
``resume_replay_proof`` block. ``--append-recovery-ledger`` appends the rec2 generation row and the FIT-REC2 row; the coordinator folds the rec1 row.

RECOVERY rec1 (owner decision 309 A, 2026-10-14): ``nxt_r1_family.RECOVERIES`` re-registers the column flight under new attempt ids, a new FIT run and
attempt, and run-cumulative caps (scripts/flights/lib/recovery.py). The writer then supersedes the first-attempt plans, writes the ``-rec1`` plans with the
recovery block, re-verifies the committed predecessor snapshot against the data root when present, and puts the recovery ledger block (two DRAFT rows) in
``draft-ledger-rows.md``; ``--append-recovery-ledger`` also appends that block to ``docs/exposure-ledger.md`` (idempotent). ``--registered-at`` defaults to the
first registration's stamp.
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

import nxt_r1_derive_cells as dc  # noqa: E402
import nxt_r1_family as fam  # noqa: E402

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
PROHIBITIONS = [
    "No test-split, DEV or Fold A contact (TRAIN Fold B only).",
    "No supply arm, no template column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "The system is the 268-B Thinking lock: the knowledge supply, the module graph, the post-processing and the roster are not changed. The per-node thinking decoding of the non-delivering arms is the ONLY varied factor.",
    "No arm may set any knob other than enable_thinking / reasoning_budget_tokens / answer_reserve_tokens (rails.supply_variants.parse_perception_thinking_variants refuses the rest by name).",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false; the read attributes a thinking cost or gain to a node.",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the harness commit is on master, the P3.1 chain has finished and the cells are flipped.",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]
FINDINGS = [
    {"id": "no-think-on-a-thinking-only-checkpoint-is-unmeasured",
     "finding": ("The Thinking GGUF's chat template carries an enable_thinking branch that pre-fills an empty think block, but the model card calls the "
                 "checkpoint thinking-only: a no-think answer from it is out of distribution and UNMEASURED (design section 1.3). The smoke-4 cell settles "
                 "whether enable_thinking false answers with no reasoning bytes and no think marker, and the read reports per arm and node the completion-token "
                 "and finish-reason table, the reasoning-character and marker counts, so a no-think arm that still reasons is visible."),
     "remedy": "the coordinator reads `nxt_r1_read.sh smoke` before the sign-off marker; a no-think arm that emits markers or empty answers stops the column flight."},
    {"id": "solver-prompt-differs-by-the-arms-own-note",
     "finding": ("Independent chains, no note sharing (coordinator ruling 2): the evidence, the instruction template and the QueryState are identical in every "
                 "arm, but a non-delivering arm's Solver prompt carries THAT arm's Perception note, which a no-think Perception writes differently. The "
                 "perception-off and both-off contrasts therefore measure the node together with its downstream effect on the Solver, and solver-off "
                 "re-contacts Perception (a request-identical contact whose note may differ by np4 batching jitter), which the in-flight twin both-on-twin measures."),
     "remedy": "none; stated so the attribution is not over-read."},
    {"id": "in-flight-twin-and-the-external-reference",
     "finding": ("The column carries its own A/A null, both-on-twin (a request-identical copy of the delivering both-on arm; same policy, same bytes). The 268-B "
                 f"cross-flight twin offset (+{fam.TWIN_OFFSET_268B_SLU_PP} SLU, {fam.TWIN_OFFSET_268B_INTENT_PP} intent) is the external reference, reported "
                 "beside the in-flight offset and never used in a node word. The receipt schema v5 makes the twin optional, so a later budget round may fly without one."),
     "remedy": "none."},
    {"id": "serial-gpu-and-the-resident-session",
     "finding": ("Ruling 303 A: one experiment in flight. The P3.1 chain (SAEA-Chain-TSYSD) occupies the Thinking session; this package is DRAFT / HELD until it "
                 "has finished. The session is the 268-B think-budget-np4 session (budget 3072, cap 4096, same model fragment): no per-arm session, the per-request "
                 "fields carry the arm."),
     "remedy": "the coordinator flips the cells only after the P3.1 chain has sealed."},
    {"id": "preflight-defers-to-the-exact-gate",
     "finding": ("As in the 268-B cells the model-free preflight counts the payload at 4 bytes per token (a placeholder) and would refuse the Solver render at the 4,096 "
                 "cap; the cells defer to the registered exact per-contact context-fit gate (preflight_budget_mode defer-to-native-contact-fit), which runs on every "
                 "arm's REAL request. A no-think arm's smaller cap (1,024) only widens its prompt limit."),
     "remedy": "none."},
    {"id": "flight-registration-check-does-not-yet-read-the-thinking-block",
     "finding": ("scripts/checks/flight_registration_check.py's node-column findings (aa-arm-missing, variant-cost-mismatch, template-summary-mismatch) read only the "
                 "Solver's template_variants block and are a no-op for a Perception-node group; the declaration is nevertheless complete (aa_arm_id, variant_cost, "
                 "template_variants summary) and stage3_effect_floor_check validates its shape."),
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


def measurement_blocks(ids: Mapping[str, Mapping]) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        arm["run_id"]: {
            "measurement_design": "same-flight-node-column", "expected_effect_pp": fam.SYSTEM_DELTA_SLU_PP, "claims_benefit": False, "claim": "nominated",
            "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "aa_arm_id": fam.TWIN,
            "variant_cost": {"extra_contacts_per_row": fam.CONTACTS_PER_ROW - 2, "extra_audio_seconds": round(fam.extra_audio_seconds("arm"), 2)},
            "template_variants": {"node": "perception", "candidate_arms": len(fam.CANDIDATE_ARMS), "twin": True},
            "variant_kind": "thinking-policy",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"A per-node attribution, not a benefit claim: the largest contrast the column can show is both-off against both-on, expected at about "
                     f"{fam.SYSTEM_DELTA_SLU_PP} pp SLU-F1 (the 268-B read: the Thinking system {fam.THINKING_SYSTEM_SLU} against the Instruct system "
                     f"{fam.INSTRUCT_SYSTEM_SLU}; the no-think core on the same weights is expected near the Instruct system). The two single-node arms split that "
                     f"gap in an unknown way; the design resolves a per-node contrast of {fam.FLOOR_SLU_PP} pp SLU / {fam.FLOOR_INTENT_PP} pp intent at n = 1,080 "
                     "(decision 190 node-column floors), so the column's resolving power is the per-node attribution. The in-flight twin both-on-twin is the A/A "
                     f"null; the 268-B cross-flight twin offset (+{fam.TWIN_OFFSET_268B_SLU_PP}) is the external reference.")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form, per-arm per-node decode cost and the no-think behaviour only)", "read_roster": fam.READ_ROSTER,
            "tuning_roster": fam.TUNING_ROSTER,
            "note": ("Four Fold B rows prove FORM only: the c10 module program with five arms loads on the Thinking session, each arm's requests carry their own thinking "
                     "fields, enable_thinking false answers without reasoning bytes or a think marker (or does not: the table says), the live phase fit passes and the "
                     "v5 receipt seals. Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_estimate() -> dict:
    expected = fam.expected_gpu_hours(fam.ROWS)
    return {
        "formula": (f"expected = rows x arm mix / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 with the arm mix {fam.ARM_MIX_ROWS} full 268-B rows per row "
                    f"({' + '.join(f'{a} {c}' for a, c in fam.ROW_COST.items())}); ceiling = ceil_0.1(expected x {fam.GPU_MARGIN})"),
        "inputs": {"row_cost_in_full_rows": fam.ROW_COST, "rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "margin": fam.GPU_MARGIN,
                   "perception_share_of_a_row": round(fam.PERCEPTION_SHARE_OF_ROW, 3),
                   "single_node_off_cost_note": "0.6 is the larger of the Perception share (0.588) and the Solver share (0.412), rounded up: a no-think contact costs a few hundred tokens, not zero"},
        "arm_mix_rows": fam.ARM_MIX_ROWS,
        "column_flight": {"contacts": fam.program_calls("arm"), "plan_ceiling_calls": fam.original_generation_calls("arm"), "expected_gpu_hours": round(expected, 2),
                          "planned_ceiling_gpu_hours": fam.CELLS["arm"]["gpu_hours"],
                          "run_cumulative_plan_calls": fam.generation_calls("arm"), "run_cumulative_speech_audio_seconds": fam.cell_audio_cap("arm")},
        "smoke": {"contacts": fam.program_calls("smoke"), "planned_ceiling_gpu_hours": fam.CELLS["smoke"]["gpu_hours"]},
        "registered_total_gpu_hours": round(fam.CELLS["arm"]["gpu_hours"] + fam.CELLS["smoke"]["gpu_hours"], 1),
        "reference_268b": "one 268-B arm pass: 1,080 rows, 2,160 contacts, 9.78 GPU-h at 1.84 rows/min (spent about 9.4 against the 8.4 ceiling: the lesson of the measured-throughput rule)",
        "fallback_note": (f"The answer-only fallback adds at most one contact per budgeted-thinking contact: {fam.THINKING_CONTACTS_PER_ROW} per row (both-on 2 + twin 2 + "
                          f"perception-off 1 + solver-off 1 + both-off 0); planned_model_calls is rows x ({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = "
                          f"{fam.original_generation_calls('arm')} (program maximum {fam.program_calls('arm')}). The runner requires only rows x ({fam.CONTACTS_PER_ROW} + 2). "
                          f"The FIT cap stays structural (rows x program contacts x endpoints = {fam.fit_contact_cap(fam.ROWS)})."),
    }


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
            "mode": "trace", "kept_rows": counts["kept"], "flown_rows": counts["flown"], "partial_rows": counts["partial"], "unstarted_rows": counts["unstarted"],
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
    arms_doc = {arm: ({"thinking_policy": fam.POLICIES[arm]} if arm in fam.POLICIES else {"thinking_policy": None, "role": "twin" if arm == fam.TWIN else "delivering"})
                for arm in fam.ARM_ORDER}
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
                "one_factor": ("The per-node thinking decoding of the non-delivering arms (enable_thinking false at the named node). The delivering arm is the 268-B lock form "
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
                 "(stage3_rollout_score --mode perception-branches) after the seal. Flown by scripts/flights/nx/batch_chain_nxt_r1.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, **resume_extra, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of NX-T R1.",
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
    return f"## Cell NXT-R1 recovery rec{fam.recovery_index(key)}: "


RECOVERY_AUTHORITY_REC1 = "owner ruling 304 of 2026-10-13 (the per-node thinking-policy column) and owner decision 309 A of 2026-10-14 (recovery re-registration)"
RECOVERY_AUTHORITY = RECOVERY_AUTHORITY_REC1 + (f" and {fam.OWNER_EXCEPTION_REC2} (the explicit exception to the one-recovery rule for the rec2 mode-A resume)"
                                                 if fam.recovery_index("arm") >= 2 else "")
SCOPE = (f"the 268-B Thinking lock system (plain review-off COMP-1b module graph on lock {fam.LOCK}) with the five-arm per-node thinking-policy column at the Perception "
         f"node (program {fam.PROGRAM}, {fam.CONTACTS_PER_ROW} contacts per row), TRAIN Fold B (owner ruling 304)")


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
                 ("The offline read of NX-T R1: score the five arm columns of the sealed column flight once each with the official scorer (stage3_rollout_score "
                  "--mode perception-branches); paired contrasts of every arm against the delivering both-on arm, the in-flight twin offset, the per-scenario table and the "
                  f"per-arm per-node completion / finish-reason / cap-hit / empty / forced-close / throughput tables by the recipe {pkg}/analysis-recipe-v1.json. "
                  "Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp TRAIN Fold B {arm['rows']}, the sealed column flight (after the seal)", "discovery", arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the column flight is sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner ruling 304 of 2026-10-13 "
            "(which nodes do not need thinking: the per-node thinking-policy column on the Thinking core, TRAIN Fold B); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/nx/nxt_r1_mint_receipt.py after this countersignature; the READ row "
            "stays a draft until the column flight is sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        if fam.recovery(key):
            spec = fam.CELLS[key]
            clause = (f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator "
                      f"(nxt_r1_mint_receipt.py --supersede) so that its eligible_run_ids list the new FIT run id {i['fit_run_id']}")
            for run, label in ((i["run_id"], f"the {spec['role']}"), (i["fit_run_id"], f"live phase-fit identity of the {spec['role']}")):
                rows[run] = rcv.countersign_text(
                    fam.RECOVERIES, key, authority=RECOVERY_AUTHORITY, role=spec["role"], label=label, attempt=i["attempt_id"], fit_run=i["fit_run_id"],
                    fit_attempt=i["fit_attempt_id"], receipt_clause=clause, tail="the READ row stays a draft until the column flight is sealed")
            continue
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner ruling 304 of "
                             "2026-10-13; the column flight is sealed at its flight commit and the sealed run was not opened for any number before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any]) -> str:
    arm, smoke = ids["arm"], ids["smoke"]
    cf, mix = cost["column_flight"], cost["inputs"]["row_cost_in_full_rows"]
    return (
        "# NX-T R1: the per-node thinking-policy column on the Thinking core, TRAIN Fold B (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/nx/nxt_r1_write_registration.py` from the fragments `nxt_r1_derive_cells.py` wrote.\n\n"
        "## The question (owner ruling 304, 2026-10-13)\n\n"
        "The 268-B read found the locked system +7.15 pp SLU-F1 / +2.31 intent better on the Thinking core than on the Instruct core, with every node thinking at "
        "budget 3,072. Ruling 304: \"are there nodes that do not need thinking mode at all?\" This is the FIRST node-level round on the Thinking base: one flight, "
        "one roster, a same-flight COLUMN over the per-node thinking policy. Every arm contacts Perception and the Solver; the arms differ ONLY in the thinking "
        "decoding of their own two contacts.\n\n"
        "## Arms (declared order; the delivering arm LAST)\n\n"
        "| arm | Perception | Solver | role | cost in 268-B rows |\n| --- | --- | --- | --- | ---: |\n"
        f"| `perception-off` | enable_thinking false (max_tokens {fam.tsf.THINK_ANSWER_RESERVE_TOKENS}) | thinking, budget {fam.tsf.THINK_BUDGET_TOKENS} / cap {fam.tsf.THINK_MAX_TOKENS} | candidate | {mix['perception-off']} |\n"
        f"| `solver-off` | thinking | enable_thinking false | candidate | {mix['solver-off']} |\n"
        f"| `both-off` | enable_thinking false | enable_thinking false | candidate (the no-think core on the same weights) | {mix['both-off']} |\n"
        f"| `both-on-twin` | thinking | thinking | in-flight A/A null (request-identical copy of `both-on`) | {mix['both-on-twin']} |\n"
        f"| `both-on` | thinking | thinking | DELIVERING = the 268-B lock form | {mix['both-on']} |\n\n"
        "The arm kind is `roles.perception.thinking_variants` (rails.supply_variants.parse_perception_thinking_variants; receipt `saea-perception-branch-arms-v5`; "
        "the consumption module's `thinking` column kind compiles it): a level-2 Perception branch group whose non-delivering arms carry a `thinking_policy` "
        "({perception | solver: enable_thinking | reasoning_budget_tokens | answer_reserve_tokens}) and nothing else. Any other knob is refused by name. The "
        "delivering arm and the twin declare no policy, so their requests are the 268-B lock's, byte for byte (unit-tested against the unarmed adapter).\n\n"
        "### Thinking-control knobs (one place: `thinking_system_family.THINKING_KNOBS`, re-used unchanged)\n\n"
        f"* the delivering form: `thinking_budget_tokens` {fam.THINKING_KNOBS['thinking_budget_tokens']} + answer reserve {fam.THINKING_KNOBS['answer_reserve_tokens']} = "
        f"completion cap {fam.THINKING_KNOBS['completion_cap']}, `reasoning_context_policy` `{fam.THINKING_KNOBS['reasoning_context_policy']}`, temperature 0, seed 20260913, "
        f"forced-close message (`--reasoning-budget-message`): \"{fam.THINKING_KNOBS['budget_message']}\";\n"
        f"* the no-think form of a non-delivering arm's node: `chat_template_kwargs` `{{\"enable_thinking\": false}}`, no `thinking_budget_tokens`, `max_tokens` "
        f"{fam.NO_THINK_KNOBS['max_tokens']} (the answer reserve); an answer-only fallback exists only for a budgeted thinking request;\n"
        f"* model fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}`, swap target `{fam.THINK_SWAP_TARGET}` (the 268-B session, unchanged).\n\n"
        "## What the arms share, and what they do not (coordinator rulings 1 and 2)\n\n"
        "* Shared by every arm: the evidence blocks, the instruction templates, the QueryState, the speech packet, the module program, the knowledge supply, the "
        "roster, the model fragment and the serving session.\n"
        "* NOT shared: independent chains, no note sharing. A non-delivering arm's Solver prompt carries THAT arm's own Perception note; `solver-off` re-contacts "
        "Perception (a request-identical contact whose note may differ by np4 batching jitter), which the twin `both-on-twin` measures.\n\n"
        "## Registered cells\n\n"
        "| cell | role | rows | program contacts | plan calls | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.program_calls(k):,} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | "
                    f"`{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |" for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the 268-B Thinking lock cell, derived by `nxt_r1_derive_cells.py` with exactly one addition (the Perception `thinking_variants` block, "
        f"compiled by the module compiler): lock `{fam.LOCK}`, program `{fam.PROGRAM}` ({fam.CONTACTS_PER_ROW} = 2 + 2 (5 - 1) contacts per row), the Thinking model "
        f"fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}` (swap target `{fam.THINK_SWAP_TARGET}`), the Thinking packets and their promotion receipt "
        f"(`{fam.THINK_PROMOTION_RECEIPT}`), the fold-excluded knowledge supply and the roster `{fam.ROSTER['arm']}` (1,080 rows); the smoke is the loop's own four "
        f"Fold B rows (`{fam.ROSTER['smoke']}`). `preflight_budget_mode` is `defer-to-native-contact-fit`; the finite-completion policy is "
        "`deliver-latest-or-abstain` and the ReAct-exhaustion policy `continue-without-answer`.\n\n"
        "## GPU ceiling (coordinator ruling 4)\n\n"
        f"{cost['formula']}.\n\n"
        f"* Arm mix {cost['arm_mix_rows']} full 268-B rows per row; 1,080 rows: expected {cf['expected_gpu_hours']} GPU-h, registered ceiling "
        f"{cf['planned_ceiling_gpu_hours']} GPU-h ({cf['contacts']:,} program contacts, plan ceiling {cf['plan_ceiling_calls']:,} calls including at most "
        f"{fam.THINKING_CONTACTS_PER_ROW} fallback re-asks per row).\n"
        f"* Smoke: {cost['smoke']['contacts']} program contacts, ceiling {cost['smoke']['planned_ceiling_gpu_hours']} GPU-h. Registered total {cost['registered_total_gpu_hours']} GPU-h.\n"
        f"* {cost['reference_268b']}.\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        "## Chain sequence (the coordinator's)\n\n"
        "1. The thinking-policy harness commit is on master; the P3.1 chain (SAEA-Chain-TSYSD) has finished; this package is re-derived "
        "(`nxt_r1_derive_cells.py`, then `nxt_r1_write_registration.py`).\n"
        "2. Countersign the five DRAFT rows with `countersign-row-texts-v1.json`.\n"
        "3. `python scripts/flights/nx/nxt_r1_mint_receipt.py`.\n"
        "4. `bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r1_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {smoke['experiment']},{arm['experiment']} --pins-commit-msg /home/chao/nxt1-pins-commit.txt`.\n"
        f"5. Hold the idle watchdog; `bash scripts/flights/batch/serving_swap.sh {fam.THINK_SWAP_TARGET}`.\n"
        "6. `bash scripts/flights/nx/batch_chain_nxt_r1.sh all` (smoke, the sign-off wait on `/home/chao/nxt1-decode-signoff.marker` after "
        "`bash scripts/flights/nx/nxt_r1_read.sh smoke`, then the column flight).\n"
        "7. `bash scripts/flights/batch/serving_swap.sh slurp-np4` (swap back).\n"
        "8. `bash scripts/flights/nx/nxt_r1_read.sh columns` (the official per-arm scoring; prints no number), countersign the READ row, then "
        "`bash scripts/flights/nx/nxt_r1_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}`: every arm's first Solver answer is scored once, complete, by the official scorer; each candidate arm and the twin minus the delivering "
        "`both-on` arm, SLU-F1 and intent, paired per row, utterance-cluster bootstrap (10,000 draws, seed 20261013). Node words (fixed here, in the reader): with the in-flight "
        "twin offset |o| = |both-on-twin - both-on| (SLU), an arm is NEEDS-THINKING when its SLU CI95 upper bound is below -|o|, GAIN when its CI95 lower bound is "
        f"above |o|, otherwise NO-RESOLVED-LOSS (plus NOT-NEEDED-AT-THE-FLOOR when the SLU CI95 lower bound is >= -{fam.FLOOR_SLU_PP} pp and the intent CI95 lower bound is "
        f">= -{fam.FLOOR_INTENT_PP} pp). The read also reports, per arm and node: completion tokens (mean / p50 / p90 / p99 / max), the finish-reason table, cap "
        "hits, empty completions, forced closes, reasoning-character and think-marker counts (a no-think node that still reasons is visible), seconds per "
        "contact, and the THROUGHPUT table (seconds per row, rows per minute at 4 slots, GPU-h per pass, each arm's measured cost in both-on rows beside the "
        "registered mix). claims_benefit is false; development numbers only (owner decisions 28 and 86).\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate, knobs, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the four plans (smoke, column flight; each generation and FIT) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `nxt_r1_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the five DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md`) |\n")


def original_registered_at(root: Path) -> str:
    """The first registration's stamp (kept by a recovery: the plans, protocol and facts keep their original ``registered_at_utc``; the recovery
    carries its own stamp in its ``recovery`` block)."""

    return json.loads((Path(root) / fam.package_file("registered-facts-v1.json")).read_text(encoding="utf-8"))["registered_at_utc"]


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
        scope = f"Cell NXT-R1 {spec['role']} -- RECOVERY rec{rec['recovery_index']}: {SCOPE}; {flown_text}"
        out[key] = rcv.recovery_ledger_block(
            fam.RECOVERIES, key, mark=recovery_ledger_mark(key), authority=RECOVERY_AUTHORITY, package=fam.PACKAGE, role=spec["role"], run=i["run_id"],
            fit_run=i["fit_run_id"], attempt=i["attempt_id"], fit_attempt=i["fit_attempt_id"], session=fam.THINK_SESSION, scope=scope,
            fit_scope=f"Cell NXT-R1 {spec['role']} -- RECOVERY rec{rec['recovery_index']} live phase-fit spend identity, request envelopes only, no generation.",
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
        f"\n## Serving geometry of the re-flown column flight: {g['target']} (owner decision 315 A, 2026-10-14)\n\n"
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
            f"1. Run the writer on master WITH the recovery ledger block: `python -B scripts/flights/nx/nxt_r1_write_registration.py --study-commit <sha> "
            "--recovery-registered-at <UTC> --append-recovery-ledger` (appends the rec2 generation row and the FIT-REC2 row; idempotent).\n"
            f"2. Fold the rec1 generation row of `{arm['run_id']}` into the rec2 row (one run id, one row; the notes name BOTH earlier attempts) and countersign the two "
            f"new rows (`{arm['run_id']}`, `{arm['fit_run_id']}`) with `countersign-row-texts-v1.json`; the READ row stays a draft until the seal.\n"
            "3. `python scripts/flights/nx/nxt_r1_mint_receipt.py --supersede` (the current receipt is renamed to a dated backup; the new one lists the rec2 FIT run id "
            "after the rec1 one and carries the rec2 plan sha256s and both snapshots).\n"
            "4. After the successor-3 seal: `NXT1_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r1_flip.sh\" --package "
            f"{fam.PACKAGE} --cells {arm['experiment']} --pins-commit-msg /home/chao/nxt1-pins-commit.txt` (the arm cell only; the sealed smoke is not touched; "
            "`--allow-output-change` is never passed).\n"
            "5. Hold the idle watchdog; `bash scripts/flights/nx/batch_chain_nxt_r1.sh arm-only` (checks the predecessor trace sha256, runs the resume prelaunch replay gate, "
            f"swaps to `{fam.THINK_SWAP_TARGET}` when it is not resident, and flies {counts['flown']} rows; the merged manifest is {counts['roster']:,} rows).\n"
            "6. `bash scripts/flights/nx/nxt_r1_read.sh columns`, countersign the READ row, then `bash scripts/flights/nx/nxt_r1_read.sh` (the reader reports kept / flown / "
            "absent counts per arm).\n")
    return (
        "\n### Recovery sequence (the coordinator's; it replaces steps 2 to 6 above for the recovered column flight)\n\n"
        "1. Re-run the writer on master with the recovery ledger block: `python -B scripts/flights/nx/nxt_r1_write_registration.py --study-commit <sha> "
        "--recovery-registered-at <UTC> --append-recovery-ledger`.\n"
        f"2. Countersign the two new rows (`{arm['run_id']}` recovery row, `{arm['fit_run_id']}`) with `countersign-row-texts-v1.json`; fold the first-attempt "
        "generation row of the same run id into the recovery row.\n"
        "3. `python scripts/flights/nx/nxt_r1_mint_receipt.py --supersede` (the old receipt is renamed to a dated backup first; the new receipt lists the "
        "rec1 FIT run id and carries the recovery block and the new plan sha256).\n"
        "4. The flip converges both cells (both readiness blocks pin the decision receipt, whose sha256 changed): "
        f"`bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r1_flip.sh\" --package {fam.PACKAGE} --cells "
        f"{smoke['experiment']},{arm['experiment']} --pins-commit-msg /home/chao/nxt1-pins-commit.txt`. The smoke is flipped, never re-flown.\n"
        "5. Hold the idle watchdog; `bash scripts/flights/batch/serving_swap.sh " + fam.THINK_SWAP_TARGET + "`.\n"
        "6. `bash scripts/flights/nx/batch_chain_nxt_r1.sh arm-only` (refuses unless the smoke is sealed and the sign-off marker exists; `all` refuses "
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
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {a: (fam.POLICIES[a] if a in fam.POLICIES else ("the request-identical twin (in-flight A/A)" if a == fam.TWIN else "the delivering arm = the 268-B lock form"))
                 for a in fam.ARM_ORDER},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The node words and their thresholds are fixed in {fam.READER} and in this package's README: NEEDS-THINKING, NO-RESOLVED-LOSS, "
                                     "GAIN (plus NOT-NEEDED-AT-THE-FLOOR) against the in-flight twin offset and the decision-190 node-column floors."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the per-node thinking decoding of the non-delivering arms; the system is the 268-B Thinking lock on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-nxt-r1-thinking-policy-fold-b-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": ("Which nodes of the locked Thinking system do not need thinking (owner ruling 304)? Each non-delivering arm is read PAIRED per row against "
                         "the delivering both-on arm on the same 1,080 Fold B rows in one flight, with the in-flight twin as the null.")}
    snapshot_refs = {k: [{"path": rel, "sha256": hashlib.sha256((root / rel).read_bytes()).hexdigest()}
                         for rel in fam.PREDECESSOR_SNAPSHOTS[k] if (root / rel).is_file()] for k in recov}
    if recov:
        protocol["recovery"] = json.loads(json.dumps(recov))
        protocol["predecessor_snapshots"] = snapshot_refs
        protocol["superseded_attempt_ids"] = [a for k in recov for rec in fam.RECOVERY_HISTORY[k]
                                              for a in (rec["predecessor_attempt_id"], rec["predecessor_fit_attempt_id"])]
        protocol["recovery_note"] = " ".join(f"[{fam.CELLS[k]['role']}] {fam.recovery(k)['reason']}" for k in recov)
        if any(fam.recovery(k).get("owner_exception") for k in recov):
            protocol["failure_policy"] += (f" Recovery rec1 is spent; rec2 stands under an explicit owner exception ({fam.OWNER_EXCEPTION_REC2}) to the rule of one "
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
        "cell_kind": "SAME-FLIGHT NODE COLUMN over the per-node thinking policy -- five arms paired per row against the delivering both-on arm; claim ceiling nominated",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)",
        "measurement_design": "same-flight-node-column", "read_run_id": fam.READ_RUN_ID, "recipe_id": fam.RECIPE_ID, "registered_at_utc": at,
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": fam.READ_ROSTER, "rows": fam.ROWS, "split_identity_hash": arm["split_identity_hash"]},
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": fam.READ_RUN_ID, "smoke": smoke["run_id"], "smoke_fit": smoke["fit_run_id"]},
        "arms": list(fam.ARM_ORDER), "delivering": fam.DELIVERING, "twin": fam.TWIN,
        "external_references": {"twin_offset_268b_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_268b_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                "thinking_system_slu": fam.THINKING_SYSTEM_SLU, "instruct_system_slu": fam.INSTRUCT_SYSTEM_SLU},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_columns": "bash scripts/flights/nx/nxt_r1_read.sh columns  (stage3_rollout_score --mode perception-branches: one complete official scoring per arm; no number printed)",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/nx/nxt_r1_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-arm per-node decode cost; no countersignature; the sign-off for the column flight)"},
        "verdict_words": ["NEEDS-THINKING", "NO-RESOLVED-LOSS", "GAIN", "NOT-NEEDED-AT-THE-FLOOR"],
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
        "read_rule": {"reader": fam.READER, "node_words": ["NEEDS-THINKING", "NO-RESOLVED-LOSS", "GAIN"], "extra_word": "NOT-NEEDED-AT-THE-FLOOR",
                      "floors_pp": {"slu": fam.FLOOR_SLU_PP, "intent": fam.FLOOR_INTENT_PP}, "twin": fam.TWIN, "delivering": fam.DELIVERING},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": arm["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": json.loads(json.dumps(fam.NO_THINK_KNOBS)),
        "thinking_arms": {a: (fam.POLICIES.get(a)) for a in fam.ARM_ORDER}, "status": "DRAFT-HELD"}
    if recov:
        facts["recovery"] = json.loads(json.dumps(recov))
        facts["predecessor_snapshots"] = snapshot_refs
        facts["recovery_budget"] = {k: rcv.recovery_budget(fam.RECOVERIES, k, ids[k]["family_budget"]) for k in recov}
        facts["resume"] = {k: {"resume_from": fam.recovery(k)["resume_from"], "counts": fam.recovery(k)["resume_counts"], "mode": fam.recovery(k)["resume_mode"],
                               "owner_exception": fam.recovery(k)["owner_exception"], "fix_commit": fam.recovery(k)["fix_commit"]}
                           for k in recov if fam.recovery(k).get("resume_from")}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/nx/nxt_r1_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"{fam.OWNER_RULINGS}; {INSTRUMENT}; {SPEC}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": "Fly the per-node thinking-policy column on the Thinking core on TRAIN Fold B: four-row smoke, then the five-arm column flight.",
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
                                                                           "recovery's FIT run id. nxt_r1_mint_receipt.py --supersede renames the old receipt to a dated backup first.")}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(row_cells)} unconsumed rows -- the cells still on their first attempt (generation row and live-phase-fit identity each) and the READ row; a "
             "recovered cell's two rows follow this table as a recovery block -- for NX-T R1 of owner ruling 304. "
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
    prereg = (f"# NX-T R1: the per-node thinking-policy column, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
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
    parser.add_argument("--recovery-branch", default="sonnet/nxt1-rec2")
    parser.add_argument("--recovery-worktree", default="/home/chao/saea-worktrees/sonnet-nxt1-rec2")
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
