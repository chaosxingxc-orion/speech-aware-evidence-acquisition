#!/usr/bin/env python3
"""Write the DRAFT readiness package of the P3.1 replicate (the locked SLURP system on the Thinking core, DEV-2000-ADDED), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the six plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration.

THE LEDGER IS APPENDED IN TWO STEPS because the composed config hashes (and therefore the plan files the rows cite) move when the packet receipt is
pinned: ``--append-ledger packets`` appends the one packets row BEFORE the GPU window (the driver's ``--check-ledger`` needs it countersigned), and
``--append-ledger flights`` appends the seven flight / fit / read rows AFTER the receipt is pinned and the package is re-written. ``all`` is both.

    python -B scripts/flights/direct/thinking_system_dev_write_registration.py --study-commit <sha> --registered-at 2026-10-13T12:00:00.000000+00:00
        [--root DIR] [--append-ledger none|packets|flights|all] [--no-derive] [--require-receipt]
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

import thinking_system_dev_derive_cells as dc  # noqa: E402
import thinking_system_dev_family as fam  # noqa: E402

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
REGISTRY_SECTION = "'P3 programme under decision 299 A' (coordinator, 2026-10-13 16:20Z), step P3.1"
PRIMARY_METRIC = ("official SLURP pooled SLU-F1 (micro; scorer slurp-slu-official, the pinned official evaluate.py), natural-mixture weighting, "
                  "with intent accuracy (scenario_action) beside it")
VERDICT_WORDS = ["NOMINATED", "NOT-NOMINATED", "HARM"]
PACKETS_LEDGER_MARK = "## Cell P3.1 packets: the Thinking speech packets of DEV-2000-ADDED (one GPU encoder window)"
PROHIBITIONS = [
    "No test-split, TRAIN Fold A/B, DEV-1000 or DEV-500 contact (DEV-2000-ADDED only).",
    "No supply arm, no template column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "The system is the sealed Instruct NX R5 composed cell's plain lock: the knowledge supply, the module graph, the post-processing and the roster are not changed. The core is the ONE factor.",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false for every cell; a NOMINATED verdict makes the Thinking system the SLURP lock CANDIDATE v3.0 only.",
    "No flight before the Thinking promotion receipt for DEV-2000-ADDED exists and is pinned, the coordinator countersigns the DRAFT rows, mints the decision receipt and flips the cells.",
    "No session is started by this registration. No paper-scale profile. No system-level claim. No test-sample read (P3.6 needs a new owner-signed allowance).",
]
FINDINGS = [
    {"id": "dev-thinking-packets-required",
     "finding": ("The DEV-2000-ADDED rows have Instruct speech packets only; 748 of 860 mmproj tensors differ in the Thinking model, so the Thinking cells need their "
                 f"own packets for these 1,000 rows, promoted additively into the existing Thinking packet root under the NEW receipt {fam.THINK_PROMOTION_RECEIPT}. "
                 "The cells pin that receipt's sha256; until it exists the baselines carry the zero sentinel and the mint, the flip and the chain refuse."),
     "remedy": ("coordinator: countersign the packets row, then bash scripts/flights/direct/direct_fb_packets_gpu.sh --check --stage dev2000-added and "
                "--run --stage dev2000-added; then re-derive with --require-receipt and re-write this package.")},
    {"id": "instruct-parent-is-nx-r5-composed",
     "finding": ("The brief's module-comp1b cells on DEV-2000-ADDED carry lock v2.1, program phase-native-candidates-review-revise-v1 (Reviewer loop on, 11 contacts "
                 "per row) and all components off; only the -aa twin sealed (study commit 9a0a3384b) and the main cell is held with no run. The cell request-"
                 f"identical to the 268-B Thinking cells apart from roster and core is {fam.PARENT_RUN} (lock v2.2 + v4g, review off, program {fam.PROGRAM}, sealed "
                 f"COMPLETED at study commit {fam.PARENT_STUDY_COMMIT[:9]}); it is both the derivation parent and the comparator column."),
     "remedy": "none; the derive script proves the parent's block recompiles to the parent baseline apart from the registered diff."},
    {"id": "twin-is-a-separate-cell",
     "finding": ("The c3 shape (Perception + lock + in-row twin in one flight) cannot be compiled today (rails.consumption_module refuses a supply frame with no "
                 "supply column); the twin is a second whole-pipeline cell flown in the same chain, as in 268-B."),
     "remedy": "none."},
    {"id": "ceilings-from-measured-throughput",
     "finding": (f"GPU ceilings come from the measured 4-slot throughput ({fam.MEASURED_ROWS_PER_MINUTE} rows per minute at np4 x 24,576, budget 3,072; "
                 f"source: {fam.MEASURED_SOURCE}): ceil_0.1(rows / {fam.MEASURED_ROWS_PER_MINUTE} / 60 x {fam.GPU_MARGIN}) = {fam.planned_gpu_hours(fam.ROWS)} per 1,000-row arm, "
                 f"{fam.SMOKE_GPU_HOURS} for the smoke."),
     "remedy": "none; a smoke or arm that projects above its ceiling stops for the coordinator."},
    {"id": "context-fit-at-the-registered-cap",
     "finding": (f"At the registered completion cap {fam.THINK_MAX_TOKENS} the live prompt limit is {fam.PROMPT_LIMIT_THINKING} tokens (24,576 - 3,072 reserve - "
                 f"{fam.THINK_MAX_TOKENS} - 2); the measured Solver prompt maximum on the Instruct lock is {fam.SOLVER_PROMPT_TOKENS_MAX}. DEV rows carry the full-TRAIN "
                 "knowledge view the parent pins; the live phase FIT re-measures on the real supply and compact-or-abstain handles an overflow."),
     "remedy": "none needed unless the FIT refuses; then stop for the coordinator."},
    {"id": "no-bare-thinking-core-on-dev",
     "finding": ("There is no bare Thinking core run on DEV-2000-ADDED (carrier and bare baselines on Thinking are step P3.3). The read therefore orients with the "
                 f"bare INSTRUCT core ({fam.BARE_RUN}, split identity equal to the roster's) and says so; the nomination rests on the Instruct lock column and the twin only."),
     "remedy": "none."},
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
    contrast = (f"cross-flight against the sealed Instruct lock column {fam.COMPARATOR_COLUMN} (same roster, same system) "
                "with the in-chain request-identical twin as the A/A replicate")
    return {
        lock["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate", "expected_effect_pp": fam.EXPECTED_EFFECT_PP, "claims_benefit": False,
            "replicate_run_id": aa["run_id"], "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"Replicate, not an admission: the declared prior is the 268-B Fold B contrast (+{fam.FOLD_B_DELTA_SLU_PP} pp SLU-F1, +{fam.FOLD_B_DELTA_INTENT_PP} intent) "
                     f"and claims_benefit is false. The Thinking system arm is read {contrast}.")},
        aa["run_id"]: {
            "measurement_design": "cross-flight-with-in-chain-replicate", "expected_effect_pp": 0.0, "claims_benefit": False,
            "replicate_run_id": lock["run_id"], "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("The request-identical twin of the Thinking system arm: it measures the same-core offset the cross-flight contrast is judged "
                     "against; expected_effect_pp is 0.0 because a request-identical pair is registered to look for no effect.")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form and per-node decode cost only)", "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("Four DEV-2000-ADDED rows prove FORM only: the module program loads on the Thinking session, the DEV Thinking packets resolve, reasoning stays "
                     "out of the delivered content, the live phase fit passes at the cap and the episode completes; the per-node decode cost is "
                     "reported. Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_estimate() -> dict:
    rows = fam.ROWS
    arm_h = fam.planned_gpu_hours(rows)
    return {
        "formula": (f"planned_gpu_hours(rows) = ceil_0.1( rows / {fam.MEASURED_ROWS_PER_MINUTE} rows per minute / 60 x {fam.GPU_MARGIN} ); the four-row smoke keeps "
                    f"{fam.SMOKE_GPU_HOURS}"),
        "measured_source": fam.MEASURED_SOURCE,
        "inputs": {"rows_per_minute": fam.MEASURED_ROWS_PER_MINUTE, "margin": fam.GPU_MARGIN, "round_h": fam.GPU_ROUND_H, "slots": fam.THINK_SLOTS,
                   "budget_tokens": fam.THINK_BUDGET_TOKENS},
        "per_arm_pass": {"rows": rows, "contacts": rows * fam.CONTACTS_PER_ROW, "expected_wall_hours": round(fam.expected_wall_hours(rows), 2),
                         "planned_ceiling_gpu_hours": arm_h},
        "registered_total": {"contacts": 2 * rows * fam.CONTACTS_PER_ROW + fam.SMOKE_ROWS * fam.CONTACTS_PER_ROW,
                             "expected_wall_hours": round(2 * fam.expected_wall_hours(rows), 2),
                             "planned_ceiling_gpu_hours": round(fam.CELLS["lock"]["gpu_hours"] + fam.CELLS["aa"]["gpu_hours"] + fam.SMOKE_GPU_HOURS, 1)},
        "fallback_note": ("The answer-only fallback adds at most 2 contacts per row: planned_model_calls is rows x "
                          f"({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = {fam.generation_calls('lock')} per arm (program maximum "
                          f"{fam.program_calls('lock')}), and the speech-audio cap scales the same way. The FIT cap stays structural "
                          f"(rows x program contacts x endpoints = {fam.fit_contact_cap(rows)})."),
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
                               "The system, the knowledge supply, the sealed query vectors and the roster are the sealed Instruct NX R5 composed cell's on DEV-2000-ADDED.")}
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"],
                   run_id=i["run_id"], schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        route = ("Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored." if key == "smoke" else
                 f"Shared core.flight.cli campaign over {spec['campaign']} on the resident Thinking session ({fam.THINK_SESSION}); one official score over "
                 "the complete manifest at finalize. Flown by scripts/flights/direct/batch_chain_thinking_system_dev.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of the P3.1 replicate.",
            "scoring": "One first complete official score after a successful seal; no partial score." if key != "smoke" else "None: the smoke is never scored."}
        fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
        docs[fam.plan_file_name(key, "fit")] = {
            **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
            "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
            "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."}
    return docs


LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = ("DEV-2000-ADDED dev rows already exposed by the model-free speech-query encoding pass, the sealed B6 direct and plan arms, PLANr-DEV2000, "
             "CELL-3 and its twin, ROLL-3, cell A2 (arm and A/A), the NX R5 composed cell and the offline v4 / v4g reads; this cell adds no new row and "
             "opens no split. Prior exposure is inherited in full.")
THINK_MODEL_TEXT = ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, c98304 np4 x 24,576 "
                    f"max{fam.THINK_MAX_TOKENS} (reasoning budget {fam.THINK_BUDGET_TOKENS}), q8_0 KV, --reasoning-format deepseek (model fragment {fam.THINK_MODEL}); "
                    "its own promoted DEV-2000-ADDED speech packets; module program " + fam.PROGRAM + "; no tool authority")
SCOPE = (f"the locked SLURP system (the plain review-off COMP-1b module graph on lock {fam.LOCK}, program {fam.PROGRAM}, {fam.CONTACTS_PER_ROW} contacts per "
         "row, no supply arm, no column) on the Thinking core, DEV-2000-ADDED (registry P3.1: DEV replicate before any lock)")


def packets_row(at: str, commit: str, pkg: str) -> list[str]:
    roster = fam.roster_doc("arm")
    seconds = int(-(-float(roster.get("audio_seconds_total", fam.roster_audio("arm"))) // 1))
    return [at[:10], fam.PACKETS_ROW_ID, "bounded-discovery-probe",
            ("DRAFT -- REGISTERED. Thinking-core speech-packet preparation for SLURP DEV-2000-ADDED (registry P3.1 / P3.2 step: GPU encoder pass, ONE window): one "
             "contact per row at max_tokens 1 over the 1,000 DEV-2000-ADDED recordings, then ADDITIVE promotion into the existing Thinking packet root under the new "
             "receipt DEV-2000-ADDED-promotion.json. Label-free: no gold, transcript or model output is opened."),
            ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M encoder pass (qwen3-omni-30b-a3b-thinking-gguf-q4km, GPU, -np 1 -ngl 999, sidecar fragment "
             "q4km-thinking-feature-preprocess-gpu-np1-dev2000-added-v1); fixed one-token response never read"),
            "slurp DEV-2000-ADDED 1000", fam.SPLIT_ROLE, roster["split_identity_hash"], "no", str(fam.ROWS), str(seconds), "1.0", INHERITED,
            "scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added; configs/experiment/slurp-dev2000-added-thinking-preprocess-gpu-v1.json",
            f"DRAFT at study commit {commit}; packets row of {pkg}; nothing authorised."]


def draft_rows(ids: Mapping[str, Mapping], commit: str, at: str, pkg: str, shas: Mapping[str, str]) -> list[list[str]]:
    rows = []
    for key in fam.ALL_KEYS:
        i = ids[key]
        for fit in (False, True):
            plan = f"{pkg}/{fam.plan_file_name(key, 'fit' if fit else 'generation')}"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            rows.append([at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
                         f"DRAFT -- REGISTERED. {fam.CELLS[key]['role'].capitalize()}: {SCOPE}" + (" -- FIT spend identity" if fit else ""), THINK_MODEL_TEXT,
                         f"slurp DEV-2000-ADDED {i['rows']}", fam.SPLIT_ROLE, i["split_identity_hash"], "no", str(calls),
                         str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]), INHERITED, plan,
                         f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."])
    arm = ids["lock"]
    rows.append([at[:10], fam.READ_RUN_ID, "model-free-check",
                 ("The offline read of the P3.1 replicate: score the Thinking system arm, its twin, the sealed Instruct NX R5 composed column and the bare Instruct "
                  f"core (B6 direct) once each; paired contrasts, twin offset, per-scenario table and the per-node cap-hit / empty / parse-failure / "
                  f"cost tables by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp DEV-2000-ADDED {arm['rows']}, the sealed P3.1 arms (after the seal)", fam.SPLIT_ROLE, arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after BOTH arms are sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: registry P3.1 of "
            "2026-10-13 (the locked system on the Thinking core, DEV-2000-ADDED replicate); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/direct/thinking_system_dev_mint_receipt.py after this "
            "countersignature; the READ row stays a draft until both arms are sealed)")
    rows = {fam.PACKETS_ROW_ID: head + "the Thinking speech-packet preparation of DEV-2000-ADDED, one GPU encoder window" + tail.replace(
        f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/direct/thinking_system_dev_mint_receipt.py after this countersignature; "
        "the READ row stays a draft until both arms are sealed)", "; the window is scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage dev2000-added)")}
    for key in fam.ALL_KEYS:
        i = ids[key]
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: registry P3.1 of "
                             "2026-10-13; both arms (lock and the twin aa) are sealed at the one flight commit and the sealed runs were not opened "
                             "before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables. The packets row is countersigned BEFORE the "
                      "GPU window; the six flight rows after the receipt is pinned and the package re-written; the READ row after both arms are sealed."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any], receipt: Mapping[str, Any]) -> str:
    lock, aa, smoke = ids["lock"], ids["aa"], ids["smoke"]
    pa, rt = cost["per_arm_pass"], cost["registered_total"]
    knobs = fam.THINKING_KNOBS
    state = "PRESENT and pinned" if receipt["present"] else "ABSENT (the baselines carry the zero sentinel; the mint, the flip and the chain refuse)"
    return (
        "# P3.1: the locked SLURP system on the Thinking core, DEV-2000-ADDED replicate (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/direct/thinking_system_dev_write_registration.py` from the fragments `thinking_system_dev_derive_cells.py` wrote.\n\n"
        f"## Registry step P3.1 ({REGISTRY_SECTION})\n\n"
        "The 268-B read found the locked system on the Thinking core TRANSFERS-ABOVE-BAR on TRAIN Fold B (SLU +7.15 pp [+5.08, +9.26], intent +2.31 pp "
        "[+0.56, +4.07] over the Instruct system; decision 299 A trigger 3 of 3). Fold B numbers are development numbers (decision 28), so the Thinking system "
        "is replicated on DEV-2000-ADDED, a roster the Thinking core has never seen, as one column with a twin BEFORE any lock. NOMINATED iff the SLU CI95 lower "
        "bound of the contrast with the Instruct lock column on the same roster exceeds the twin offset and the intent guard holds; a NOMINATED verdict makes "
        "the Thinking system (budget 3,072 / cap 4,096 / `drop-reasoning-v1`) the SLURP lock CANDIDATE v3.0, nothing more.\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        f"Receipt state at generation: `{fam.THINK_PROMOTION_RECEIPT}` is {state}.\n\n"
        "## What is registered\n\n"
        "| cell | role | rows | contacts | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | `{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |"
                    for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the sealed Instruct NX R5 composed cell on DEV-2000-ADDED (`{fam.PARENT_RUN}`, study commit `{fam.PARENT_STUDY_COMMIT[:9]}`), byte for byte, "
        "except the model fragment, the speech-packet promotion receipt (and its sha256), the preflight deferral to the exact native contact gate, the FIT "
        f"identities and the cell's own first-phase supply: lock `{fam.LOCK}`, program `{fam.PROGRAM}`. The roster is the DEV-2000-ADDED runtime view "
        f"`{fam.ROSTER['arm']}` (1,000 rows, split `{ids['lock']['split_identity_hash'][:12]}...`); the smoke is its first four rows (the parent smoke's own). "
        "The knowledge view is the parent's full-TRAIN pools (DEV rows are disjoint from TRAIN by construction).\n\n"
        "### Thinking-control knobs (the Fold B family's single place: `thinking_system_family.THINKING_KNOBS`, re-exported)\n\n"
        f"* `thinking_budget_tokens` {knobs['thinking_budget_tokens']} + answer reserve {knobs['answer_reserve_tokens']} = completion cap {knobs['completion_cap']};\n"
        f"* forced-close message (`--reasoning-budget-message`): \"{knobs['budget_message']}\";\n"
        f"* `reasoning_context_policy` `{knobs['reasoning_context_policy']}`; every node thinks, budgeted ({knobs['node_modes']}); temperature 0, seed 20260913;\n"
        f"* answer-only fallback `{knobs['answer_fallback']['id']}` (one per node);\n"
        f"* model fragment `{fam.THINK_MODEL}` and session `{fam.THINK_SESSION}` (reused unchanged from 268-B: they pin the packet ROOT, never a receipt), swap target `{fam.THINK_SWAP_TARGET}`.\n\n"
        "## GPU plan (measured throughput, not per-contact seconds)\n\n"
        f"{cost['formula']}. Source: {cost['measured_source']}.\n\n"
        f"* One pass (lock or twin): {pa['contacts']:,} contacts, expected {pa['expected_wall_hours']} h wall at the measured rate, registered ceiling {pa['planned_ceiling_gpu_hours']} GPU-h.\n"
        f"* Registered total (smoke + lock + twin): {rt['contacts']:,} contacts, expected {rt['expected_wall_hours']} h, ceilings {rt['planned_ceiling_gpu_hours']} GPU-h.\n\n"
        "## Chain sequence (the coordinator's)\n\n"
        f"1. Append the packets row: `python -B scripts/flights/direct/thinking_system_dev_write_registration.py --study-commit <sha> --registered-at <UTC> --append-ledger packets` "
        f"(or by hand from `draft-ledger-rows.md`), commit, and countersign it (`{fam.PACKETS_ROW_ID}`) with `countersign-row-texts-v1.json`.\n"
        f"2. The packet window: `bash scripts/flights/direct/direct_fb_packets_gpu.sh --check --stage {fam.PACKETS_STAGE}` then "
        f"`bash scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage {fam.PACKETS_STAGE}` (stops Instruct, encodes the 1,000 rows on the GPU, promotes additively "
        f"into the Thinking root, writes `{fam.THINK_PROMOTION_RECEIPT}`, starts the `{fam.THINK_SWAP_TARGET}` session; the watchdog hold stays).\n"
        "3. Pin the receipt: `python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-dev2000-added --pin-receipt` (verification only), then "
        "`python -B scripts/flights/direct/thinking_system_dev_derive_cells.py --require-receipt` and "
        "`python -B scripts/flights/direct/thinking_system_dev_write_registration.py --study-commit <sha> --registered-at <UTC> --append-ledger flights`; commit.\n"
        "4. Loop iteration closed / one experiment in flight. Countersign the six flight rows.\n"
        "5. `python scripts/flights/direct/thinking_system_dev_mint_receipt.py`.\n"
        "6. `bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/direct/thinking_system_dev_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {smoke['experiment']},{lock['experiment']},{aa['experiment']} --pins-commit-msg /home/chao/{fam.SHORT}-pins-commit.txt`.\n"
        f"7. Hold the idle watchdog; the Thinking session is already resident from step 2 (else `bash scripts/flights/batch/serving_swap.sh {fam.THINK_SWAP_TARGET}`).\n"
        f"8. `bash scripts/flights/direct/batch_chain_thinking_system_dev.sh all` (smoke, the sign-off wait on `/home/chao/{fam.SHORT}-decode-signoff.marker` after "
        "`bash scripts/flights/direct/thinking_system_dev_read.sh smoke`, then lock, then the twin).\n"
        "9. `bash scripts/flights/batch/serving_swap.sh slurp-np4` (swap back).\n"
        "10. Countersign the READ row, then `bash scripts/flights/direct/thinking_system_dev_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}`: d_system = SLU(Thinking system lock) minus SLU(sealed Instruct lock column `{fam.COMPARATOR_COLUMN}`), "
        "utterance-cluster bootstrap (10,000 draws, seed 20261011); the twin offset o = SLU(aa) - SLU(lock); orientation: the system minus the bare Instruct core "
        f"(`{fam.BARE_RUN}`; no bare Thinking core exists on this roster); per-scenario table (natural and equal weightings; scenario from the governed devel loader at "
        "read time, in memory); the cap-hit / empty-completion / parse-failure / forced-close table and the cost per contact PER NODE. Verdict words: "
        "NOMINATED (CI95 lo of d_system > |o|, intent CI95 lo >= -0.65 pp, no delivered reasoning marker); HARM (d <= -2.5 pp and CI95 hi < -|o|); "
        "NOT-NOMINATED otherwise. The decision-299 completion rate (>= 0.99) and the point against 2.5 pp are reported beside it, not part of the word. "
        "claims_benefit is false; development numbers only.\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate, context fit, knobs, findings, blockers, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the six plans (smoke, lock, aa; each generation and FIT) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `thinking_system_dev_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the eight DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (packets row first; appended with `--append-ledger`) |\n")


def write_package(root: Path, commit: str, at: str, *, append_ledger: str = "none", derive: bool = True, require_receipt: bool = False) -> dict:
    root = Path(root)
    derived = dc.derive(repo_root=root, require_receipt=require_receipt) if derive else None
    loader = {k: (derived["cells"][k]["loader_verification"] if derived else {"ok": True}) for k in fam.ALL_KEYS}
    pkg = fam.PACKAGE
    ids = identities(root)
    lock, aa, smoke = ids["lock"], ids["aa"], ids["smoke"]
    receipt = fam.receipt_state()
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    if not receipt["present"]:
        blockers.append({"id": "thinking-dev-promotion-receipt-absent", "detail": f"{receipt['path']} does not exist; the baselines carry the zero sentinel",
                         "clears_with": f"direct_fb_packets_gpu.sh --run --stage {fam.PACKETS_STAGE}, then derive --require-receipt and re-write this package"})
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {"lock": "the Thinking system arm", "aa": "its request-identical twin (separate cell, same chain)"},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The verdict words and their thresholds are fixed in {fam.READER} and in this package's README: NOMINATED, NOT-NOMINATED, "
                                     "HARM; NOMINATED iff the SLU CI95 lower bound of the cross-flight contrast exceeds the in-chain twin offset and the intent guard holds."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the core (Thinking model fragment with a reasoning budget, its own speech packets); the system is the sealed Instruct NX R5 composed cell's plain lock on DEV-2000-ADDED",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-system-thinking-core-dev2000-added-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": (f"Does the Fold B transfer (+{fam.FOLD_B_DELTA_SLU_PP} pp SLU-F1 / +{fam.FOLD_B_DELTA_INTENT_PP} intent over the Instruct system) replicate on DEV-2000-ADDED? The Thinking "
                         f"system arm is read against the sealed Instruct column {fam.COMPARATOR_COLUMN} on the same 1,000 rows, with the in-chain twin as the null.")}
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": f"{DECISIONS} ({REGISTRY_SECTION}); {SPEC}; {INSTRUMENT}",
        "cell_kind": "CROSS-FLIGHT REPLICATE READ -- Thinking system arm vs the sealed Instruct lock column on DEV-2000-ADDED, with an in-chain twin; claim ceiling none",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)",
        "measurement_design": "cross-flight-with-in-chain-replicate", "read_run_id": fam.READ_RUN_ID, "recipe_id": fam.RECIPE_ID, "registered_at_utc": at,
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": fam.READ_ROSTER, "rows": fam.ROWS, "split_identity_hash": lock["split_identity_hash"],
                   "roster_receipt": fam.ROSTER_RECEIPT},
        "run_ids": {"arm": lock["run_id"], "fit": lock["fit_run_id"], "twin": aa["run_id"], "twin_fit": aa["fit_run_id"], "read": fam.READ_RUN_ID,
                    "smoke": smoke["run_id"], "smoke_fit": smoke["fit_run_id"]},
        "comparators": {
            "instruct_lock_column": {"run_id": fam.COMPARATOR_COLUMN, "attempt_id": fam.COMPARATOR_ATTEMPT, "arm": fam.COMPARATOR_ARM,
                                     "study_commit": fam.PARENT_STUDY_COMMIT, "roster_identity": "split identity hash equal to this roster's (asserted by the reader)"},
            "bare_instruct_core": {"run_id": fam.BARE_RUN, "attempt_id": fam.BARE_ATTEMPT, "kind": fam.BARE_KIND,
                                   "roster_identity": "split identity hash equal to this roster's (ledger row and reader assertion)"},
            "bare_thinking_core": "none: no bare Thinking core run exists on DEV-2000-ADDED"},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_score": "one complete official scoring per arm (core.scoring_batch; never sharded); the two comparators are already scored at their seals",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/direct/thinking_system_dev_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-node decode cost; no countersignature; the sign-off for the arms)"},
        "verdict_words": VERDICT_WORDS,
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
                        "prompt_limit_tokens": fam.PROMPT_LIMIT_THINKING, "solver_prompt_tokens_max_measured": fam.SOLVER_PROMPT_TOKENS_MAX},
        "findings": FINDINGS, "identity": ids,
        "instruct_parent": {"run_id": fam.PARENT_RUN, "attempt_id": fam.PARENT_ATTEMPT, "smoke_run_id": fam.PARENT_SMOKE_RUN, "study_commit": fam.PARENT_STUDY_COMMIT,
                            "lock": fam.LOCK, "program": fam.PROGRAM, "review_loop": "off",
                            "rejected_module_comp1b_cells": ("lock v2.1, program phase-native-candidates-review-revise-v1, Reviewer loop on, 11 contacts per row; only the "
                                                             "-aa twin sealed (SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1, study commit 9a0a3384b)")},
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET,
                 "speech_packet_root": fam.THINK_PACKET_ROOT, "speech_packet_promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                 "speech_packet_promotion_receipt_present": receipt["present"], "speech_packet_promotion_receipt_sha256": receipt["sha256"] or fam.UNPINNED_SHA,
                 "fold_b_promotion_receipt_not_used": fam.FOLD_B_PROMOTION_RECEIPT},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{DECISIONS} ({REGISTRY_SECTION}); {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "read_rule": {"reader": fam.READER, "verdict_words": VERDICT_WORDS, "bar_pp": 2.5, "intent_guard_pp": 0.65,
                      "comparator": fam.COMPARATOR_COLUMN, "bare_instruct": fam.BARE_RUN},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": lock["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "status": "DRAFT-HELD"}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/direct/thinking_system_dev_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'. The mint refuses while the DEV Thinking promotion receipt is absent."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"Registry {REGISTRY_SECTION} (decision 299 A); {INSTRUMENT}; {SPEC}.",
        "budget": {**lock["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True,
                   "twin": aa["family_budget"], "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": "Fly the locked SLURP system on the Thinking core on DEV-2000-ADDED: four-row smoke, the lock arm and its request-identical twin.",
        "decision_id": fam.DECISION_ID, "eligible_attempt_ids": fam.eligible_attempt_ids(), "eligible_run_ids": fam.eligible_run_ids(),
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "starting or touching any serving session outside the registered swap",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool",
                           "any change beyond the registered core swap and Thinking knobs", "TRAIN Fold A/B, DEV-1000 or test-split contact"],
        "owner": "root", "population": {"count": fam.ROWS, "fold_a_contact_authorized": False, "split_identity_hash": lock["split_identity_hash"],
                                        "split_role": fam.SPLIT_ROLE, "test_contact_authorized": False},
        "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "no_child_start_stop": True},
        "status": "DRAFT-NOT-MINTED"}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = [packets_row(at, commit, pkg)] + draft_rows(ids, commit, at, pkg, shas)
    pk_lines = [PACKETS_LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
                f"One unconsumed row for the GPU packet window that precedes the P3.1 replicate (package {pkg}). It is countersigned BEFORE "
                "`direct_fb_packets_gpu.sh --run --stage dev2000-added`; it authorises that window only.", "",
                "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |", reg.table_row(row_cells[0])]
    fl_lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
                "Seven unconsumed rows -- three generation rows, their three live-phase-fit identities and the READ row -- for the P3.1 replicate of registry "
                f"step P3.1. Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: the Thinking session is started by "
                f"the packet window or the registered swap target {fam.THINK_SWAP_TARGET}; its serving row is the coordinator's at the swap.",
                "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    fl_lines += [reg.table_row(cells) for cells in row_cells[1:]]
    packets_text = "\n".join(pk_lines) + "\n"
    flights_text = "\n".join(fl_lines) + "\n"
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", packets_text + "\n" + flights_text)
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost, receipt))
    prereg = (f"# P3.1: the locked system on the Thinking core, DEV-2000-ADDED replicate, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
              "Development numbers only.\n\n"
              f"Runs: `{lock['run_id']}` / `{lock['fit_run_id']}`; twin `{aa['run_id']}` / `{aa['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; "
              f"read `{fam.READ_RUN_ID}`; packets `{fam.PACKETS_ROW_ID}`.\n\nThe verdict words and the read rule are in `{pkg}/README.md`.\n\n## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": measurement_blocks(ids)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, fam.PREREG, prereg)
    result = {"package": pkg, "ids": ids, "shas": shas, "blockers": blockers, "loader_verification": loader, "ledger_appended": {}}
    if append_ledger not in ("none", "packets", "flights", "all"):
        raise SystemExit(f"--append-ledger {append_ledger!r} (none | packets | flights | all)")
    ledger = root / reg.LEDGER
    for name, mark, text in (("packets", PACKETS_LEDGER_MARK, packets_text), ("flights", fam.LEDGER_MARK, flights_text)):
        if append_ledger not in (name, "all"):
            continue
        current = io.open(ledger, encoding="utf-8", newline="").read()
        if mark in current:
            result["ledger_appended"][name] = False
        else:
            io.open(ledger, "w", encoding="utf-8", newline="").write(current.rstrip("\n") + "\n\n" + text)
            result["ledger_appended"][name] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository (or overlay) root to read and write")
    parser.add_argument("--append-ledger", default="none", choices=("none", "packets", "flights", "all"),
                        help="append the DRAFT rows at the END of docs/exposure-ledger.md (idempotent per block)")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    parser.add_argument("--require-receipt", action="store_true", help="refuse unless DEV-2000-ADDED-promotion.json exists")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive,
                           require_receipt=args.require_receipt)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
