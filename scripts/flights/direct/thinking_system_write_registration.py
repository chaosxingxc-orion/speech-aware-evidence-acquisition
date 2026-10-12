#!/usr/bin/env python3
"""Write the DRAFT readiness package of the 268-B read (the locked SLURP system on the Thinking core, TRAIN Fold B), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the six plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration.

    python -B scripts/flights/direct/thinking_system_write_registration.py --study-commit <sha> --registered-at 2026-10-12T12:00:00.000000+00:00
        [--root DIR] [--append-ledger] [--no-derive]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import thinking_system_derive_cells as dc  # noqa: E402
import thinking_system_family as fam  # noqa: E402

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
    "The system is the loop's plain lock as it flies on the Instruct core: the knowledge supply, the module graph, the post-processing and the roster are not changed. The core is the ONE factor.",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false for every cell; the read measures transfer of a core lever.",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the harness of design decision 282 is merged, the package is re-derived and the cells are flipped.",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]
FINDINGS = [
    {"id": "twin-is-a-separate-cell",
     "finding": ("The engineering design's c3 shape (Perception + lock + in-row twin aa in one flight) cannot be compiled today: "
                 "rails.consumption_module refuses a supply frame with no supply column (\"consumption_module.supply_frame is declared but no supply "
                 "column is\") and rails.supply_variants admits only 1 to 6 candidate arms. The twin is therefore a second cell, request-identical to the "
                 "arm, flown in the same chain (the 266-E replicate and the cell1 / gepacell twins are the precedent). Two c2 passes cost 4 contacts per "
                 "row; the in-row c3 costs 3."),
     "remedy": "decision 282 may admit a candidate-less twin group; the package is then re-derived with fam.TWIN_SHAPE = in-row."},
    {"id": "native-roles-require-preserved-wire",
     "finding": ("Native role contacts require preserved wire metadata (reproduction.ojw.native_roles._wire_turn: \"metered completion requires "
                 "preserved wire metadata\"), so preserve_wire_responses must be true on the module graph. On the Thinking core the preserved wire bytes "
                 "carry message.reasoning_content, which therefore lands in the sealed trace on the data root (never in Git, never delivered, never "
                 "scored). Owner constraint (iii) of 266-E (reasoning text never persisted beyond hashes) cannot hold for a native cell."),
     "remedy": "owner acknowledgement, or an engineering change that strips reasoning_content before the wire bytes are sealed (hash semantics change)."},
    {"id": "context-fit-at-the-registered-cap",
     "finding": (f"At the registered completion cap {fam.THINK_MAX_TOKENS} the live prompt limit is {fam.PROMPT_LIMIT_THINKING} tokens "
                 f"(24,576 - 3,072 reserve - {fam.THINK_MAX_TOKENS} - 2); the measured Solver prompt maximum on the Instruct lock is "
                 f"{fam.SOLVER_PROMPT_TOKENS_MAX}, so no row is compacted or abstained by compact-or-abstain. At the superseded cap 8,192 the limit would "
                 f"be {fam.PROMPT_LIMIT_SUPERSEDED_8192} and the heaviest rows would be."),
     "remedy": "none needed at 4,096; the live phase FIT re-measures on the real supply."},
    {"id": "harness-pass-through-merged",
     "finding": ("Resolved: the Thinking harness knobs are merged (decision 283 A, master 0e6ffbfd3). The model fragment carries the real keys "
                 "reasoning_budget_tokens, answer_reserve_tokens, enable_thinking, reasoning_context_policy and forced_close_message_sha256 (pinned to the "
                 "--reasoning-budget-message value in its server_args); they fold into decoding_params at composition; the baselines declare no thinking_policy "
                 "(every node thinks); the plan ceiling is rows x (contacts + 2 fallback contacts)."),
     "remedy": "none."},
    {"id": "budget-message-wording-unverified",
     "finding": ("The forced-close sentence is the design's wording of the Qwen3 technical report's stop sentence, flagged unverified in the design "
                 "(section 1.2 / 6 (d))."),
     "remedy": "verify verbatim against arXiv:2505.09388 before a flight pins the fragment; change fam.THINK_BUDGET_MESSAGE and the model fragment together."},
    {"id": "smoke-size", "finding": ("The design recommends a 32-row smoke (the 266-E four-row smoke overstated cost 1.8x with one runaway in four); "
                                      "this registration keeps the loop's own four Fold B rows as ordered."),
     "remedy": "a larger smoke needs a prefix roster receipt and a SMOKE_ROWS change in the family."},
    {"id": "swap-target-needs-scheduled-tasks",
     "finding": ("The new geometry target think-budget-np4 (scripts/flights/batch/serving_lib.sh) names the Windows scheduled tasks "
                 "SAEA-Serving-THINKB and SAEA-Monitor-THINKB, which the coordinator registers (saea_task.ps1 pattern) before the first swap."),
     "remedy": "register the two tasks; the entry scripts are scripts/flights/direct/serving_task_entry_think_budget.sh and serving_monitor_start_think_budget.sh."},
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
    lock, aa, smoke = ids["lock"], ids["aa"], ids["smoke"]
    contrast = (f"cross-flight against the Instruct lock column of loop iteration 3 ({fam.COMPARATOR_COLUMN}, same roster, same system) "
                "with the in-chain request-identical twin as the A/A replicate")
    return {
        lock["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate", "expected_effect_pp": fam.BARE_DELTA_SLU_PP, "claims_benefit": False,
            "replicate_run_id": aa["run_id"], "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"Transfer of a core lever, not an admission: the declared prior is the bare-core delta of 266-E (+{fam.BARE_DELTA_SLU_PP} pp SLU-F1, "
                     f"+{fam.BARE_DELTA_INTENT_PP} intent) and claims_benefit is false. The Thinking system arm is read {contrast}.")},
        aa["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate", "expected_effect_pp": 0.0, "claims_benefit": False,
            "replicate_run_id": lock["run_id"], "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("The request-identical twin of the Thinking system arm: it measures the same-core offset the cross-flight contrast is judged "
                     "against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect.")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form and per-node decode cost only)", "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("Four Fold B rows prove FORM only: the module program loads on the Thinking session, the Thinking packets resolve, reasoning stays "
                     "out of the delivered content, the live phase fit passes at the cap and the episode completes; the per-node decode cost is "
                     "reported. Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_estimate() -> dict:
    arm_expected = fam.expected_gpu_hours(fam.ROWS, 1)
    return {
        "formula": ("expected = rows x [ (P_inst + d x E_B) + n_solver x (S_inst + d x E_B) ] / slots / 3600 with P_inst = 5.48 s and S_inst = 7.45 s "
                    "(Instruct module column, i2), d = 0.02298 s per generated token (266-E fit), E_B = E[min(reasoning, B)] = 848 tokens at B = 3,072; "
                    "ceiling = ceil_0.1(expected x 1.3)"),
        "inputs": {"instruct_module_s": fam.INSTRUCT_MODULE_S, "decode_s_per_token": fam.DECODE_S_PER_TOKEN, "e_min_reasoning_tokens": fam.E_MIN_REASONING_TOKENS[fam.THINK_BUDGET_TOKENS],
                   "budget_tokens": fam.THINK_BUDGET_TOKENS, "slots": fam.THINK_SLOTS, "margin": fam.GPU_MARGIN},
        "row_slot_seconds_c2": round(fam.row_seconds(1), 2),
        "per_arm_pass_c2": {"contacts": fam.ROWS * fam.CONTACTS_PER_ROW, "expected_gpu_hours": round(arm_expected, 2), "planned_ceiling_gpu_hours": fam.CELLS["lock"]["gpu_hours"],
                            "wall_hours_range": list(fam.wall_hours(fam.ROWS, 1))},
        "registered_total": {"contacts": 2 * fam.ROWS * fam.CONTACTS_PER_ROW + fam.SMOKE_ROWS * fam.CONTACTS_PER_ROW,
                             "expected_gpu_hours": round(2 * arm_expected, 2),
                             "planned_ceiling_gpu_hours": round(fam.CELLS["lock"]["gpu_hours"] + fam.CELLS["aa"]["gpu_hours"] + fam.SMOKE_GPU_HOURS, 1)},
        "design_c3_reference": {"shape": "Perception + lock + in-row twin, one pass", "expected_gpu_hours": round(fam.C3_EXPECTED_GPU_H, 2),
                                "planned_ceiling_gpu_hours": fam.C3_PLANNED_GPU_H, "wall_hours_range": list(fam.wall_hours(fam.ROWS, 2, modelled=True)),
                                "design_table": "5.91 GPU-h, 6.6-8.5 h wall (section 4.3)"},
        "superseded_estimate": "the registry's 14 GPU-h counted 8,640 contacts at 22.8 s on the bare prompt; the design's model gives 18.4 GPU-h for two unbounded c4 passes",
        "fallback_note": ("The answer-only fallback (decisions 277 A and 283 A) adds at most 2 contacts per row: planned_model_calls is rows x "
                          f"({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = {fam.generation_calls('lock')} per arm (program maximum "
                          f"{fam.program_calls('lock')}), and the speech-audio cap scales the same way. The FIT cap stays structural "
                          f"(rows x program contacts x endpoints = {fam.fit_contact_cap(fam.ROWS)}). The GPU ceiling is unchanged: fallbacks are rare "
                          "(answer-only, at most 1,024 tokens) and the budget closes every think block."),
    }


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str) -> dict:
    docs = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        spec = fam.CELLS[key]
        base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": fam.THINK_SESSION, "experiment": i["experiment"],
                "family_budget": i["family_budget"], "preparation_base_commit": commit,
                "prepared_phase_supply": {"relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                                          "note": "the flip mints this cell's own first-phase supply under its own run id (item E16)"},
                "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha}, "registered_at_utc": at, "status": STATUS,
                "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "unused_budget_is_not_attempt_authority": True,
                "one_factor": ("The core: the Instruct model fragment and its speech packets are replaced by the Thinking core "
                               f"({fam.THINK_MODEL}, budget {fam.THINK_BUDGET_TOKENS} + reserve {fam.THINK_ANSWER_RESERVE_TOKENS} = cap {fam.THINK_MAX_TOKENS}). "
                               "The system, the knowledge supply, the sealed query vectors and the roster are the loop's plain lock on TRAIN Fold B.")}
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"],
                   run_id=i["run_id"], schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        route = ("Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored." if key == "smoke" else
                 f"Shared core.flight.cli campaign over {spec['campaign']} on the resident Thinking session ({fam.THINK_SESSION}); one official score over "
                 "the complete manifest at finalize. Flown by scripts/flights/direct/batch_chain_thinking_system.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of the 268-B read.",
            "scoring": "One first complete official score after a successful seal; no partial score." if key != "smoke" else "None: the smoke is never scored."}
        fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        docs[fam.plan_file_name(key, "fit")] = {
            **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."}
    return docs


LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = reg.LEDGER_INHERITED
THINK_MODEL_TEXT = ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, c98304 np4 x 24,576 "
                    f"max{fam.THINK_MAX_TOKENS} (reasoning budget {fam.THINK_BUDGET_TOKENS}), q8_0 KV, --reasoning-format deepseek (model fragment {fam.THINK_MODEL}); "
                    "its own promoted speech packets; module program " + fam.PROGRAM + "; no tool authority")
SCOPE = (f"the locked SLURP system (the plain review-off COMP-1b module graph on lock {fam.LOCK}, program {fam.PROGRAM}, {fam.CONTACTS_PER_ROW} contacts per "
         "row, no supply arm, no column) on the Thinking core, TRAIN Fold B (owner decision 268 B)")


def draft_rows(ids: Mapping[str, Mapping], commit: str, at: str, pkg: str, shas: Mapping[str, str]) -> list[list[str]]:
    rows = []
    for key in fam.ALL_KEYS:
        i = ids[key]
        for fit in (False, True):
            plan = f"{pkg}/{fam.plan_file_name(key, 'fit' if fit else 'generation')}"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            rows.append([at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
                         f"DRAFT -- REGISTERED. {fam.CELLS[key]['role'].capitalize()}: {SCOPE}" + (" -- FIT spend identity" if fit else ""), THINK_MODEL_TEXT,
                         f"slurp TRAIN Fold B {i['rows']}", "discovery", i["split_identity_hash"], "no", str(calls),
                         str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]), INHERITED, plan,
                         f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."])
    arm = ids["lock"]
    rows.append([at[:10], fam.READ_RUN_ID, "model-free-check",
                 ("The offline read of the 268-B read: score the Thinking system arm, its twin, the Instruct lock column of loop iteration 3 and the bare "
                  f"Thinking core of 266-E once each; paired contrasts, twin offset, per-scenario table and the per-node cap-hit / empty / parse-failure / "
                  f"cost tables by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp TRAIN Fold B {arm['rows']}, the sealed 268-B arms (after the seal)", "discovery", arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after BOTH arms are sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner decision 268 B of "
            "2026-10-12 (the locked system on the Thinking core, TRAIN Fold B); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/direct/thinking_system_mint_receipt.py after this "
            "countersignature; the READ row stays a draft until both arms are sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner decision "
                             "268 B of 2026-10-12; both arms (lock and the twin aa) are sealed at the one flight commit and the sealed runs were not opened "
                             "before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any]) -> str:
    lock, aa, smoke = ids["lock"], ids["aa"], ids["smoke"]
    pa, rt, c3 = cost["per_arm_pass_c2"], cost["registered_total"], cost["design_c3_reference"]
    knobs = fam.THINKING_KNOBS
    return (
        "# 268-B: the locked SLURP system on the Thinking core, TRAIN Fold B (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/direct/thinking_system_write_registration.py` from the fragments `thinking_system_derive_cells.py` wrote.\n\n"
        "## Owner decision 268 B (2026-10-12)\n\n"
        "The 266-E read found the bare Thinking core +11.90 pp SLU-F1 / +4.35 intent over the bare Instruct core. Decision 268 B: fly the locked system "
        "(lock v2.2 + v4g, the loop's plain lock, program `" + fam.PROGRAM + "`, the same knowledge supply) on the Thinking core on TRAIN Fold B as one column "
        "with a twin, AFTER loop iteration 3 closes. The owner directive: if the Thinking effect stacks on the system and is better, re-base the engineering "
        "on Thinking, and Thinking must FINISH every task (never an empty answer at the cap). Coordinator update (same day): register with the engineering "
        f"design's no-truncation knobs (`{SPEC}`).\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        "## What is registered\n\n"
        "| cell | role | rows | contacts | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | `{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |"
                    for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the loop's Instruct lock arm, byte for byte, except: the ace-playbook store and the supply group are absent (the plain lock is "
        f"request-identical to the loop's lock arm, proof P-ACE-0), the lock is `{fam.LOCK}`, the program is `{fam.PROGRAM}`, and the model fragment, the "
        "speech-packet promotion receipt and the FIT identities are the Thinking core's. The roster is `" + fam.ROSTER["arm"] + "` (1,080 rows); the smoke is "
        "the loop's own four Fold B rows (`" + fam.ROSTER["smoke"] + "`). The knowledge view is the loop's Fold B pools (they exclude Fold A and Fold B by "
        f"construction; the 266-E fold-excluded snapshot `...tfrl-folds-v1` `{fam.KNOWLEDGE_SNAPSHOT_SHA256[:8]}...` is the same family; the full-TRAIN "
        f"`{fam.FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256[:8]}...` is nowhere).\n\n"
        "### Thinking-control knobs (one place: `thinking_system_family.THINKING_KNOBS`)\n\n"
        f"* `thinking_budget_tokens` {knobs['thinking_budget_tokens']} + answer reserve {knobs['answer_reserve_tokens']} = completion cap {knobs['completion_cap']} "
        f"(the cap 8,192 is superseded: at 8,192 the module Solver prompt no longer fits the 24,576-token slot beside the cap);\n"
        f"* forced-close message (`--reasoning-budget-message`): \"{knobs['budget_message']}\";\n"
        f"* `reasoning_context_policy` `{knobs['reasoning_context_policy']}`; every node thinks, budgeted ({knobs['node_modes']}); temperature 0, seed 20260913;\n"
        f"* answer-only fallback `{knobs['answer_fallback']['id']}` (one per node; lands with the harness);\n"
        f"* model fragment `{fam.THINK_MODEL}`, session `{fam.THINK_SESSION}`, swap target `{fam.THINK_SWAP_TARGET}` (derived from the max8192 definitions, which stay on disk unedited).\n\n"
        "## Why the twin is a separate cell\n\n" + FINDINGS[0]["finding"] + "\n\n"
        "## GPU estimate (the design's formula)\n\n"
        f"{cost['formula']}.\n\n"
        f"* One c2 pass (lock or twin): {pa['contacts']:,} contacts, expected {pa['expected_gpu_hours']} GPU-h, registered ceiling {pa['planned_ceiling_gpu_hours']} GPU-h, "
        f"wall {pa['wall_hours_range'][0]}-{pa['wall_hours_range'][1]} h.\n"
        f"* Registered total (smoke + lock + twin): {rt['contacts']:,} contacts, expected {rt['expected_gpu_hours']} GPU-h, ceilings {rt['planned_ceiling_gpu_hours']} GPU-h.\n"
        f"* The design's c3 reference under the same formula: expected {c3['expected_gpu_hours']} GPU-h, ceiling {c3['planned_ceiling_gpu_hours']}, wall "
        f"{c3['wall_hours_range'][0]}-{c3['wall_hours_range'][1]} h (design table: {c3['design_table']}).\n"
        f"* {cost['superseded_estimate']}.\n\n"
        "## Chain sequence (the coordinator's)\n\n"
        "1. Prerequisites above cleared; harness of decision 282 merged; this package re-derived (`thinking_system_derive_cells.py`, then "
        "`thinking_system_write_registration.py`).\n"
        "2. Loop iteration 3 closed (one experiment in flight). Countersign the seven DRAFT rows with `countersign-row-texts-v1.json`.\n"
        "3. `python scripts/flights/direct/thinking_system_mint_receipt.py`.\n"
        "4. `bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/direct/thinking_system_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {smoke['experiment']},{lock['experiment']},{aa['experiment']} --pins-commit-msg /home/chao/tsys-pins-commit.txt`.\n"
        f"5. Hold the idle watchdog; `bash scripts/flights/batch/serving_swap.sh {fam.THINK_SWAP_TARGET}`.\n"
        "6. `bash scripts/flights/direct/batch_chain_thinking_system.sh all` (smoke, the sign-off wait on `/home/chao/tsys-decode-signoff.marker` after "
        "`bash scripts/flights/direct/thinking_system_read.sh smoke`, then lock, then the twin).\n"
        "7. `bash scripts/flights/batch/serving_swap.sh slurp-np4` (swap back).\n"
        "8. Countersign the READ row, then `bash scripts/flights/direct/thinking_system_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}`: d_system = SLU(Thinking system lock) minus SLU(Instruct lock column of iteration 3, run `{fam.COMPARATOR_COLUMN}`), "
        "utterance-cluster bootstrap (10,000 draws, seed 20261011); the twin offset o = SLU(aa) - SLU(lock); the system minus the bare Thinking core "
        f"(`{fam.BARE_THINKING_RUN}`); the transfer share d_system / {fam.BARE_DELTA_SLU_PP}; per-scenario table (natural and equal weightings); the "
        "cap-hit / empty-completion / parse-failure / forced-close table and the cost per contact PER NODE (Perception vs Solver). Verdict words: "
        "HARM (d <= -2.5 pp and CI95 hi < -|o|); TRANSFERS-ABOVE-BAR (d >= 2.5 pp, CI95 lo > |o|, intent CI95 lo >= -0.65 pp, no delivered reasoning marker); "
        "PARTIAL (CI95 lo > |o| but below the bar or the intent guard fails); NO-TRANSFER otherwise. claims_benefit is false; development numbers only.\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate, context fit, knobs, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the six plans (smoke, lock, aa; each generation and FIT) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `thinking_system_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the seven DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md`) |\n")


def write_package(root: Path, commit: str, at: str, *, append_ledger: bool = False, derive: bool = True) -> dict:
    root = Path(root)
    derived = dc.derive(repo_root=root) if derive else None
    loader = {k: (derived["cells"][k]["loader_verification"] if derived else {"ok": True}) for k in fam.ALL_KEYS}
    pkg = fam.PACKAGE
    ids = identities(root)
    lock, aa, smoke = ids["lock"], ids["aa"], ids["smoke"]
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {"lock": "the Thinking system arm", "aa": "its request-identical twin (separate cell, same chain)"},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The verdict words and their thresholds are fixed in {fam.READER} and in this package's README: HARM, "
                                     "TRANSFERS-ABOVE-BAR, PARTIAL, NO-TRANSFER at the 2.5 pp cross-flight bar with the in-chain twin offset."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the core (Thinking model fragment with a reasoning budget, its own speech packets); the system is the loop's plain lock on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-system-thinking-core-fold-b-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": (f"Does the +{fam.BARE_DELTA_SLU_PP} pp SLU-F1 / +{fam.BARE_DELTA_INTENT_PP} intent lever of the bare Thinking core (266-E) stack on the "
                         f"locked system? The Thinking system arm is read against the Instruct lock column of loop iteration 3 ({fam.INSTRUCT_LOCK_SLU} / "
                         f"{fam.INSTRUCT_LOCK_INTENT}) on the same 1,080 Fold B rows, with the in-chain twin as the null.")}
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": f"{DECISIONS} (decision 268 B); {SPEC}; {INSTRUMENT}",
        "cell_kind": "CROSS-FLIGHT TRANSFER READ -- Thinking system arm vs the Instruct lock column, with an in-chain twin; claim ceiling none",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)",
        "measurement_design": "cross-flight-with-in-chain-replicate", "read_run_id": fam.READ_RUN_ID, "recipe_id": fam.RECIPE_ID, "registered_at_utc": at,
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": fam.READ_ROSTER, "rows": fam.ROWS, "split_identity_hash": lock["split_identity_hash"]},
        "run_ids": {"arm": lock["run_id"], "fit": lock["fit_run_id"], "twin": aa["run_id"], "twin_fit": aa["fit_run_id"], "read": fam.READ_RUN_ID,
                    "smoke": smoke["run_id"], "smoke_fit": smoke["fit_run_id"]},
        "comparators": {"instruct_lock_column": {"run_id": fam.COMPARATOR_COLUMN, "attempt_id": fam.COMPARATOR_ATTEMPT, "arm": fam.COMPARATOR_ARM},
                        "bare_thinking_core": {"run_id": fam.BARE_THINKING_RUN, "attempt_id": fam.BARE_THINKING_ATTEMPT}},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_score": "one complete official scoring per arm (core.scoring_batch; never sharded); the two comparators are already scored at their seals",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/direct/thinking_system_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-node decode cost; no countersignature; the sign-off for the arms)"},
        "verdict_words": ["TRANSFERS-ABOVE-BAR", "PARTIAL", "NO-TRANSFER", "HARM"],
        "what_is_not_here": "No margins block and no admission: nothing is locked here."}
    shas["analysis-recipe-v1.json"] = reg.wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this DRAFT registration rests on, and the CANONICAL stage3_measurement blocks "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": {"program": fam.PROGRAM, "lock": fam.LOCK, "contacts_per_row": fam.CONTACTS_PER_ROW, "rows": fam.ROWS, "twin_shape": fam.TWIN_SHAPE,
                       "arm_generation_calls": lock["family_budget"]["generation_calls_cap"], "twin_generation_calls": aa["family_budget"]["generation_calls_cap"],
                       "smoke_generation_calls": smoke["family_budget"]["generation_calls_cap"],
                       "arm_fit_endpoint_calls_cap": lock["family_budget"]["fit_endpoint_calls_cap"],
                       "arm_speech_audio_seconds_cap": lock["family_budget"]["repeated_speech_audio_seconds_cap"],
                       "smoke_speech_audio_seconds_cap": smoke["family_budget"]["repeated_speech_audio_seconds_cap"],
                       "cost_estimate": cost},
        "blockers": blockers, "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "context_fit": {"slot_tokens": fam.SLOT_TOKENS, "reserve_tokens": fam.RESERVE_TOKENS, "completion_cap": fam.THINK_MAX_TOKENS,
                        "prompt_limit_tokens": fam.PROMPT_LIMIT_THINKING, "solver_prompt_tokens_max_measured": fam.SOLVER_PROMPT_TOKENS_MAX,
                        "instruct_prompt_limit_tokens": fam.PROMPT_LIMIT_INSTRUCT, "superseded_cap_8192_prompt_limit_tokens": fam.PROMPT_LIMIT_SUPERSEDED_8192},
        "findings": FINDINGS, "identity": ids,
        "knowledge_snapshot": {"module_cells_pin_stores_through": "knowledge_stores (the loop's Fold B pools)",
                               "fold_excluded_view_sha256": fam.KNOWLEDGE_SNAPSHOT_SHA256, "full_train_view_sha256_must_be_absent": fam.FULL_TRAIN_KNOWLEDGE_SNAPSHOT_SHA256},
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET,
                 "speech_packet_root": fam.THINK_PACKET_ROOT, "speech_packet_promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                 "speech_packet_promotion_receipt_sha256": fam.thinking_promotion_sha256(),
                 "superseded": {"model_fragment": fam.SUPERSEDED_THINK_MODEL, "serving_session": fam.SUPERSEDED_THINK_SESSION, "cap": 8192}},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{DECISIONS} (decision 268 B); {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "read_rule": {"reader": fam.READER, "verdict_words": ["TRANSFERS-ABOVE-BAR", "PARTIAL", "NO-TRANSFER", "HARM"], "bar_pp": 2.5, "intent_guard_pp": 0.65,
                      "comparator": fam.COMPARATOR_COLUMN, "bare": fam.BARE_THINKING_RUN},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": lock["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "status": "DRAFT-HELD"}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/direct/thinking_system_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"Owner decision 268 B (2026-10-12); {INSTRUMENT}; {SPEC}.",
        "budget": {**lock["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "twin": aa["family_budget"], "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": "Fly the locked SLURP system on the Thinking core on TRAIN Fold B: four-row smoke, the lock arm and its request-identical twin.",
        "decision_id": fam.DECISION_ID, "eligible_attempt_ids": fam.eligible_attempt_ids(), "eligible_run_ids": fam.eligible_run_ids(),
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "starting or touching any serving session outside the registered swap",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool",
                           "any change beyond the registered core swap and Thinking knobs", "Fold A, DEV or test-split contact"],
        "owner": "root", "population": {"count": fam.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": lock["split_identity_hash"],
                                        "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "no_child_start_stop": True},
        "status": "DRAFT-NOT-MINTED"}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             "Seven unconsumed rows -- three generation rows, their three live-phase-fit identities and the READ row -- for the 268-B read of owner "
             f"decision 268 B. Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: the Thinking session is started by "
             f"the registered swap target {fam.THINK_SWAP_TARGET} (the session is new: {fam.THINK_SESSION}); its serving row is the coordinator's at the swap.",
             "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(cells) for cells in row_cells]
    rows_text = "\n".join(lines) + "\n"
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text)
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost))
    prereg = (f"# 268-B: the locked system on the Thinking core, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
              "Development numbers only.\n\n"
              f"Runs: `{lock['run_id']}` / `{lock['fit_run_id']}`; twin `{aa['run_id']}` / `{aa['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; "
              f"read `{fam.READ_RUN_ID}`.\n\nThe verdict words and the read rule are in `{pkg}/README.md`.\n\n## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": measurement_blocks(ids)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, fam.PREREG, prereg)
    result = {"package": pkg, "ids": ids, "shas": shas, "blockers": blockers, "loader_verification": loader}
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
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository (or overlay) root to read and write")
    parser.add_argument("--append-ledger", action="store_true", help="append the DRAFT rows at the END of docs/exposure-ledger.md (idempotent)")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
