#!/usr/bin/env python3
"""Write the DRAFT readiness package of the carrier base on the Thinking core (P3.3: A2T, E21, E22; smoke, all-off and direct each), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints nothing,
countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-18-carrier-base-thinking-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL ``stage3_measurement`` blocks keyed by run
id, ``protocol-registered-v1.json``, one generation plan per cell and one FIT plan per A2T cell, ``analysis-recipe-v1.json``, ``root-admission-draft-v1.json``,
``countersign-row-texts-v1.json``, ``draft-ledger-rows.md`` and the derive's three ``signoff-conditions-<carrier>-v1.json``) and, beside it, the preregistration.

    python -B scripts/flights/carriers/carrier_think_write_registration.py --study-commit <sha> [--registered-at 2026-10-18T12:00:00.000000+00:00]
        [--root DIR] [--append-ledger] [--no-derive] [--require-receipts]

``--registered-at`` defaults to the stamp already in ``registered-facts-v1.json`` (a re-write after the packets pin keeps the first registration's stamp is NOT wanted:
P3.3 is registered AFTER P3.2, so the launch spec passes ``--registered-at {utc}``).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_derive_cells as dc  # noqa: E402
import carrier_think_family as fam  # noqa: E402

rcv = fam.rcv
REPO_ROOT = fam.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import write_tfrl_iteration_registration as reg  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

STATUS = reg.STATUS
SPEC = "docs/superpowers/specs/2026-10-12-thinking-core-engineering-base-design.md"
DECISIONS = reg.OWNER_DECISIONS
INSTRUMENT = reg.INSTRUMENT_NOTE
LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = ("Audio2Tool paired-400 / Earnings-21 discovery / Earnings-22 dev rows already exposed by prior Instruct cells (the A2T-AA passes, the E35 native-window arms, the "
             "SAEA-A2T-NATIVE-ROLE-DIRECT-UNION4000 flight); these cells open no split. Prior exposure is inherited in full.")
PROHIBITIONS = [
    "No test-split contact (A2T paired-400, Earnings-21 discovery and Earnings-22 dev only).",
    "No supply arm, no knowledge supply, no analytical tool, no native tool authority, no Reviewer or Planner visit on any carrier cell.",
    f"The Thinking knobs (reasoning budget {fam.BUDGET}, answer reserve {fam.RESERVE}, cap {fam.CAP}, {fam.tsf.REASONING_CONTEXT_POLICY}) are the SLURP lock's and never move in this package; a "
    "carrier smoke may only recommend a change, which would be a new registration.",
    "The all-off arm and the direct arm of a carrier are REQUEST-IDENTICAL; nothing may be added to one that the other lacks (proved by carrier_think_derive_cells --prove).",
    "The direct arm is the direct-only phase program of the shared controller through the same FlightRuntime and OpenJiuwen executor; a separate code path for a baseline is a defect.",
    "No reasoning text is ever delivered, scored or carried to another node (drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false; development numbers only (owner decisions 28 and 86).",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the Thinking packets of EVERY carrier are promoted and pinned (the flip refuses a zero "
    "sentinel), the harness commit is on master and no other experiment is in flight (ruling 303 A).",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]


def findings() -> list[dict]:
    a2t_fit, e21_fit, e22_fit = (fam.fit_proof(c) for c in fam.CARRIERS)
    return [
        {"id": "same-session-as-the-slurp-lock",
         "finding": (f"All nine cells use the SLURP lock's Thinking model fragment {fam.THINK_MODEL} and its resident session {fam.THINK_SESSION} (swap target {fam.THINK_SWAP_TARGET}): the "
                     "np4 x 24,576 server geometry, the knobs and the speech-feature root are the lock's. No new serving geometry, fragment or Windows task exists; the carrier packets are "
                     "promoted ADDITIVELY into the lock's Thinking packet root under their own receipts (the Fold B / DEV / test-sample precedent)."),
         "remedy": "none; the chain swaps to the target when the session is not resident."},
        {"id": "packets-first-then-register-then-flip",
         "finding": ("A baseline carries the SHA-256 of its Thinking packet artifact (A2T: the promotion receipt; Earnings: the window-packet artifact and the Thinking-identity window "
                     "inventory). Those exist only after the P3.2 packets chain has run, so this package is DERIVED with --require-receipts AFTER that chain and registered, "
                     "countersigned, minted and flipped then (the 266-E / P3.1 order: pack, pin, register, flip). The zero sentinel is refused by the flip."),
         "remedy": "run the P3.2 packets chain first (docs/readiness/2026-10-18-carrier-packets-thinking-v1); then the P3.3 launch spec."},
        {"id": "alloff-and-direct-are-an-in-chain-aa",
         "finding": ("The Instruct byte proof (module_equivalence_proof --at a2t0 / e210 / e220) shows the all-off arm compiles to the carrier's direct layer. The Thinking derivation moves "
                     "the same leaves in both, so the two arms of a carrier are request-identical (carrier_think_derive_cells --prove, recorded in the facts). Flown back to back on ONE "
                     "session they measure the carrier's own null on the Thinking core and give the baseline of record; if they do not seal on one session the null is not read."),
         "remedy": "none."},
        {"id": "context-fit-at-the-thinking-cap",
         "finding": (f"The live prompt limit of every contact is {fam.PROMPT_LIMIT:,} tokens (slot {fam.SLOT_TOKENS:,} - reserve {fam.tsf.RESERVE_TOKENS:,} - cap {fam.CAP:,} - special "
                     f"{fam.tsf.SPECIAL_RESERVE}). Sealed Instruct prompts: A2T maximum {a2t_fit['observed']['prompt_tokens_max']:,} (the 654.6 s synthesis-defect row included; headroom "
                     f"{a2t_fit['observed_headroom_tokens']:,}), Earnings-21 native window {e21_fit['observed']['prompt_tokens_max']:,} (headroom {e21_fit['observed_headroom_tokens']:,}); "
                     f"Earnings-22 has no sealed run and uses the Earnings-21 maximum as its proxy ({e22_fit['observed']['prompt_tokens_max']:,}; same 90 s window form and instruction). "
                     "A2T therefore moves from np3 x 32,768 to np4 x 24,576 without a carrier-specific fragment."),
         "remedy": "the live phase fit (A2T) and the exact per-contact fit gate re-derive the worst request before any contact; the E22 proxy is checked by its smoke."},
        {"id": "earnings-workflow-timeout-raised",
         "finding": ("The Instruct Earnings baselines carry ojw_workflow_timeout_seconds 21600 (6 h). One Thinking Earnings-21 arm is registered at about 7.1 GPU-h expected (9.3 ceiling), so a "
                     "6 h workflow timeout would abort it; the Earnings baselines carry 43200 s (12 h). It bounds one arm's workflow, not a target."),
         "remedy": "none."},
        {"id": "cost-is-the-slurp-measured-envelope",
         "finding": ("Cost per contact is the SLURP Thinking measured figure (A2T 59 s, Earnings 64 s at np4). The Instruct sealed contacts are far cheaper (A2T 0.94 s, Earnings 11.85 s) "
                     "and the all-contacts-reason-to-the-budget envelope is 71.5 s (A2T) / 82.4 s (Earnings): the registered ceilings are 1.3 x the SLURP-measured expectation, BELOW that "
                     "envelope, so a smoke that shows every contact running to the budget will fail the 1.3x machine sign-off and wait for the coordinator."),
         "remedy": "the smoke measures the real mean; the machine sign-off refuses above 1.3x the registered seconds per contact."},
        {"id": "earnings22-has-no-instruct-comparator",
         "finding": ("Earnings-22 has no sealed run on the native-window form (its Instruct all-off cell was never flown; its Instruct window packets were never encoded). The Thinking "
                     "pair is its first measurement and its own A/A; the Whisper-normalised WER is on the PLAIN window form, NOT the ESB short-form tail-2 s variant."),
         "remedy": "none; ruling 306 A keeps E22 in scope in the E21 form, last among the carriers."},
        {"id": "four-red-registration-packages-are-instruct-packages",
         "finding": ("The 'four red registration packages' of the P3.3 row are the four registered-hash tests that stayed red after the data-root placeholder sweep: "
                     "test_e21_native_window_fit_registration, test_e21_native_window_registration_prepare, test_e22_alloff_cell_registration and test_e41_bounded_perception_note. They "
                     "pin INSTRUCT cells (the E41 one is a flown package and must not be regenerated). This package derives NEW Thinking cells and does not re-pin them."),
         "remedy": "owner/coordinator decision: re-pin the three unflown Instruct packages at their next flip, or retire them (no carrier flies on the Instruct core any more)."},
        {"id": "machine-signoff-with-a-veto-window",
         "finding": ("Each carrier's smoke is followed by wait_or_machine_signoff (reader carrier_think_read.sh smoke <carrier>, the conditions file the derive emits INSIDE this package, "
                     "marker /home/chao/carrierthink-<carrier>-decode-signoff.marker, veto window 20 minutes). A refused machine sign-off falls back to waiting for a coordinator marker (12 h) "
                     "and the chain does not open the arms."),
         "remedy": "the coordinator may veto by deleting the marker or creating /home/chao/batch-STOP during the window."},
        {"id": "e21-seal-path-gap-carried-from-the-instruct-proof",
         "finding": ("The 2026-10-10 carrier end-to-end proof recorded for Earnings-21 a wire-check seal refusal ('unit-stitch has no matching trace record') on the stock base, passing "
                     "with a driver-side one-line equivalent. This package does not change the seal path; the E21 smoke is the first real exercise of it on the Thinking core."),
         "remedy": "if the E21 smoke refuses at the seal, stop and report; do not fly the arms."},
    ]


def identities(root: Path) -> dict:
    out = {}
    for key in fam.ALL_KEYS:
        s = fam.CELLS[key]
        document = json.loads((Path(root) / "configs" / "experiment" / f"{s['cell']}.json").read_text(encoding="utf-8"))
        cell = document["cells"][0]
        composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], s["cell"])
        split = document["population"]["split_identity_hash"]
        out[key] = {
            "key": key, "carrier": s["carrier"], "kind": s["kind"], "experiment": s["cell"], "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": s["fit_run"], "fit_attempt_id": s["fit_attempt"], "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"],
            "model_fragment": cell["model_fragment"], "arm": composed.values["arm"], "units": s["units"], "split_identity_hash": split,
            "roster_receipt": document["population"].get("roster_receipt"), "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values.get("live_phase_fit") or {}), "family_budget": document["family_budget"], "execution_plan": document["execution_plan"],
            "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"],
            "session": document["service_session"], "split_role": document["execution_plan"]["split_role"],
        }
    return out


def cost_estimate() -> dict:
    per = {}
    total_planned = total_expected = total_envelope = 0.0
    for carrier in fam.CARRIERS:
        smoke, alloff, direct = (fam.CELLS[fam.cell_key(carrier, k)] for k in fam.KINDS)
        units = alloff["units"]
        expected, envelope = fam.expected_gpu_hours(carrier, units), fam.envelope_gpu_hours(carrier, units)
        planned_carrier = round(smoke["gpu_hours"] + alloff["gpu_hours"] + direct["gpu_hours"], 1)
        per[carrier] = {
            "label": fam.CARRIER_SPEC[carrier]["label"], "units_per_arm": units, "unit_kind": fam.CARRIER_SPEC[carrier]["unit_kind"],
            "seconds_per_contact_registered": fam.seconds_per_contact(carrier), "expected_gpu_hours_per_arm": round(expected, 2),
            "planned_ceiling_gpu_hours_per_arm": alloff["gpu_hours"], "envelope_gpu_hours_per_arm": round(envelope, 2),
            "smoke_ceiling_gpu_hours": smoke["gpu_hours"], "carrier_expected_gpu_hours": round(2 * expected + fam.SMOKE_GPU_HOURS * 0.0, 2),
            "carrier_ceiling_gpu_hours": planned_carrier, "carrier_envelope_gpu_hours": round(2 * envelope, 2),
            "instruct_estimate_gpu_hours": {"a2t": "about 2 x 1 h", "e21": "about 4 h", "e22": "about 4 h"}[carrier],
            "generation_calls_cap_per_arm": alloff["units"] * (fam.CONTACTS_PER_UNIT + fam.FALLBACK_PER_CONTACT),
        }
        total_planned += planned_carrier
        total_expected += 2 * expected
        total_envelope += 2 * envelope
    return {
        "formula": (f"expected = units x 1 contact x seconds per contact / {fam.COST['slots']} slots / 3600; ceiling = ceil_{fam.GPU_ROUND_H:g}(expected x {fam.GPU_MARGIN:g}); smoke = the "
                    f"{fam.SMOKE_GPU_HOURS:g} GPU-h form allowance; envelope = units x (Instruct contact seconds + {fam.COST['envelope_decode_s_per_token']} x {fam.COST['envelope_budget_tokens']}) / "
                    f"{fam.COST['slots']} / 3600"),
        "basis": fam.COST["basis"], "per_carrier": per,
        "totals": {"two_arms_expected_gpu_hours": round(total_expected, 1), "registered_ceiling_gpu_hours": round(total_planned, 1),
                   "two_arms_envelope_gpu_hours": round(total_envelope, 1)},
        "note": "Ceilings are bounds, never targets. GPU-hours here exclude the P3.2 packets window, the serving swap and the machine sign-off veto windows.",
    }


def measurement_blocks(ids: Mapping[str, Mapping], root: Path) -> dict:
    blocks = {}
    for key in fam.ALL_KEYS:
        s, i = fam.CELLS[key], ids[key]
        exp = json.loads((Path(root) / "configs" / "experiment" / f"{s['cell']}.json").read_text(encoding="utf-8"))
        m = dict(exp["stage3_measurement"])
        m.update({"measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": m.get("rows", s["units"])})
        blocks[i["run_id"]] = m
    return blocks


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str, recov: Mapping[str, Mapping] | None = None) -> dict:
    docs = {}
    for key in fam.ALL_KEYS:
        i, s = ids[key], fam.CELLS[key]
        base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": s["session"], "experiment": i["experiment"],
                "family_budget": i["family_budget"], "preparation_base_commit": commit, "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                "registered_at_utc": at, "status": STATUS, "unused_budget_is_not_attempt_authority": True,
                "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)),
                "serving": {"swap_target": fam.THINK_SWAP_TARGET, "session": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL,
                            "server_geometry": f"-c {fam.SLOTS * fam.SLOT_TOKENS} -np {fam.SLOTS} (the SLURP lock's, unchanged)"},
                "source_cell": s["source_experiment"]}
        if recov and key in recov:
            base["recovery"] = json.loads(json.dumps(recov[key]))
            base["recovery_budget"] = rcv.recovery_budget(fam.RECOVERIES, key, i["family_budget"])
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"], run_id=i["run_id"],
                   schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        route = ("Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored." if s["kind"] == "smoke" else
                 f"Shared core.flight.cli campaign over {s['campaign']} on the resident Thinking session ({fam.THINK_SESSION}); one official complete score after the seal. "
                 "Flown by scripts/flights/carriers/batch_chain_carrier_think.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {s['role']}.",
            "scoring": "None: the smoke is never scored." if s["kind"] == "smoke" else "One complete official score after a successful seal; no partial score."}
        if s["fit_run"]:
            fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
            docs[fam.plan_file_name(key, "fit")] = {
                **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1", "attached_generation_run_id": i["run_id"],
                "contact_cap": i["family_budget"]["fit_endpoint_calls_cap"], "max_speech_packets": 1, "context_fit": fam.fit_proof(s["carrier"]),
                "execution_route": "The shared core.flight.cli FIT path under this cell's own live_phase_fit ids; request envelopes only, no generation.",
                "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing.", "scoring": "No fit score."}
    return docs


def draft_rows(ids: Mapping[str, Mapping], commit: str, at: str, pkg: str, shas: Mapping[str, str]) -> list[list[str]]:
    rows = []
    for key in fam.ALL_KEYS:
        if fam.recovery(key):
            continue
        i, s = ids[key], fam.CELLS[key]
        for fit in (False, True):
            if fit and not s["fit_run"]:
                continue
            plan = f"{pkg}/{fam.plan_file_name(key, 'fit' if fit else 'generation')}"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            rows.append([at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
                         f"DRAFT -- REGISTERED. {s['role'].capitalize()} (carrier base on the Thinking core; owner rulings 302 A / 306 A / 333 B)" + (" -- FIT spend identity" if fit else ""),
                         fam.think_model_text(), fam.roster_label(s["carrier"], s["kind"]), i["split_role"], i["split_identity_hash"], "no", str(calls),
                         str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]), INHERITED, plan,
                         f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."])
    for carrier in fam.CARRIERS:
        arm = ids[fam.cell_key(carrier, "alloff")]
        rows.append([at[:10], fam.read_run_id(carrier), "model-free-check",
                     (f"The offline read of the {fam.CARRIER_SPEC[carrier]['label']} carrier base on the Thinking core: score the sealed all-off and direct arms once each with the standard scorer "
                      f"({fam.CARRIER_SPEC[carrier]['primary_metric']}), their difference as the in-chain A/A, the per-stratum table"
                      + (" with the paper column" if fam.CARRIER_SPEC[carrier]["paper_column"] else "") + f", by the recipe {pkg}/analysis-recipe-{carrier}-v1.json. Zero model, server, encoder, embedder, "
                      "tokenizer and GPU contacts."),
                     "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                     f"{fam.CARRIER_SPEC[carrier]['label']}, the sealed arms (after the seal)", arm["split_role"], arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                     f"{pkg}/analysis-recipe-{carrier}-v1.json",
                     f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the carrier's arms are sealed and before any number is read) {at[:10]} at "
                     f"study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 302 A, 306 A and 333 B of 2026-10-17 "
            "(the carrier all-off and direct baselines on the Thinking core, after the P3.2 Thinking packets); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/carriers/carrier_think_mint_receipt.py after this countersignature; the READ rows stay drafts "
            "until the carrier's arms are sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        s, i = fam.CELLS[key], ids[key]
        if fam.recovery(key):
            clause = (f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator "
                      "(carrier_think_mint_receipt.py --supersede) so that its eligible_run_ids list the new FIT run id" if s["fit_run"] else
                      f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator (--supersede)")
            for run, label in ((i["run_id"], f"the {s['role']}"), (i["fit_run_id"], f"live phase-fit identity of the {s['role']}")):
                if run is None:
                    continue
                rows[run] = rcv.countersign_text(fam.RECOVERIES, key, authority=fam.OWNER_RULINGS, role=s["role"], label=label, attempt=i["attempt_id"], fit_run=i["fit_run_id"] or "none",
                                                 fit_attempt=i["fit_attempt_id"] or "none", receipt_clause=clause, tail="the READ rows stay drafts until the arms are sealed")
            continue
        rows[i["run_id"]] = head + f"{s['role']}" + tail
        if s["fit_run"]:
            rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {s['role']}" + tail
    for carrier in fam.CARRIERS:
        rows[fam.read_run_id(carrier)] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner rulings 302 A, 306 A and "
                                          f"333 B; the {fam.CARRIER_SPEC[carrier]['label']} arms are sealed at their flight commit and the sealed runs were not opened for any number before "
                                          "this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text below, then mint the "
                      "receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any], proof: Mapping[str, Any]) -> str:
    cell_rows = "\n".join(
        f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['units']:,} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | "
        + (f"`{ids[k]['fit_run_id']}`" if ids[k]['fit_run_id'] else "none") + f" | {fam.CELLS[k]['gpu_hours']} |" for k in fam.ALL_KEYS)
    cost_rows = "\n".join(
        f"| {v['label']} | {v['units_per_arm']:,} {v['unit_kind']} | {v['seconds_per_contact_registered']:g} s | {v['expected_gpu_hours_per_arm']} | {v['planned_ceiling_gpu_hours_per_arm']} | "
        f"{v['envelope_gpu_hours_per_arm']} | {v['carrier_ceiling_gpu_hours']} | {v['instruct_estimate_gpu_hours']} |" for v in cost["per_carrier"].values())
    moved = "\n".join(f"* {c}: all-off vs direct differ by {len(p['alloff_vs_direct_moved_identity_leaves'])} identity leaves only; vs the Instruct source the all-off arm moves "
                      f"{len(p['alloff_vs_instruct_source']['moved'])} leaves, all inside the declared Thinking set." for c, p in proof.items())
    return (
        "# Carrier base on the Thinking core: A2T, E21, E22 all-off + direct baselines (P3.3) (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/carriers/carrier_think_write_registration.py` from the fragments `carrier_think_derive_cells.py` wrote, from `scripts/flights/carriers/carrier_think_spec.json`. "
        "The NX-T R2b package (`docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/`) is the worked example of the launch form and is unchanged.\n\n"
        "## What it is (owner rulings 302 A, 306 A, 333 B; registry P3.3)\n\n"
        "The carrier base runs on the Thinking core after NX-T R3 and before the decoding column. Carriers in the owner's order A2T -> E21 -> E22 (E22 in the E21 form, last). For each "
        "carrier three HELD cells, all derived from the registered Instruct all-off cells by config alone:\n\n"
        "| cell | role | units | plan calls (incl. fallback) | run id | FIT run id | GPU-h ceiling |\n| --- | --- | ---: | ---: | --- | --- | ---: |\n"
        f"{cell_rows}\n\n"
        "`alloff` and `direct` of a carrier are REQUEST-IDENTICAL (the all-off module block compiles to the carrier's direct layer, the Instruct byte proof), so flown back to back on one "
        "session they are the carrier's in-chain A/A on the Thinking core and the baseline of record. The direct arm is the `direct-only` phase program of the shared controller through "
        "the same FlightRuntime and OpenJiuwen executor (engineering rule: same harness for every arm).\n\n"
        f"{moved}\n\n"
        "## The Thinking core\n\n"
        f"The SLURP lock's fragment `{fam.THINK_MODEL}`, resident session `{fam.THINK_SESSION}` (swap target `{fam.THINK_SWAP_TARGET}`): np4 x {fam.SLOT_TOKENS:,}, reasoning budget {fam.BUDGET} + "
        f"answer reserve {fam.RESERVE} = cap {fam.CAP}, `{fam.tsf.REASONING_CONTEXT_POLICY}`, `--reasoning-format deepseek`. The knobs are fixed at the SLURP lock values until a carrier smoke "
        "says otherwise. The plan ceiling adds ONE answer-only fallback contact per contact (`core.reasoning_knobs`, direct program).\n\n"
        "## Order of work (P3.2 first)\n\n"
        "1. P3.2 (package `docs/readiness/2026-10-18-carrier-packets-thinking-v1`): the Thinking speech packets of every carrier, GPU encode in swap windows, promotion receipts per root.\n"
        "2. This package is then derived with `--require-receipts` (the packet pins), registered, countersigned, minted, committed, flipped and chained by the launch spec "
        "`scripts/flights/carriers/carrier_think_base_launch_spec.json`.\n"
        "3. The chain `scripts/flights/carriers/batch_chain_carrier_think.sh` flies, per carrier: smoke -> machine sign-off (+ veto window) -> all-off arm -> direct arm -> close the "
        "ledger rows; the carriers run back to back on the one resident session.\n\n"
        "## GPU cost (from the Thinking SLURP measured throughput)\n\n"
        f"{cost['formula']}.\n\n"
        "| carrier | units per arm | s per contact | expected GPU-h per arm | ceiling per arm | upper envelope per arm | carrier ceiling (smoke + 2 arms) | Instruct estimate (P3.3) |\n"
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |\n"
        f"{cost_rows}\n\n"
        f"Totals: two arms per carrier expected {cost['totals']['two_arms_expected_gpu_hours']} GPU-h, registered ceilings {cost['totals']['registered_ceiling_gpu_hours']} GPU-h, upper "
        f"envelope {cost['totals']['two_arms_envelope_gpu_hours']} GPU-h. {cost['basis']}\n\n"
        "## Findings and prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(findings(), 1)) + "\n\n"
        "## Chain sequence (the coordinator's; flip and chain are the queue hook's)\n\n"
        "1. After the P3.2 packets chain exits rc 0: `bash scripts/flights/batch/package_launch.sh scripts/flights/carriers/carrier_think_base_launch_spec.json --root-countersign "
        "--until commit` (derive with the packet pins, write, countersign, mint, commit), then `--from flip --until chain` (the queue hook `scripts/flights/batch/queue/"
        "queue_carriers_after.sh` does both when installed with `--auto-countersign`).\n"
        f"2. The flip (`bash scripts/flights/batch/flip_package_ext4.sh --flip scripts/flights/carriers/carrier_think_flip.sh --package {fam.PACKAGE} --cells <the nine cells> "
        "--pins-commit-msg /home/chao/carrierthink-pins-commit.txt`) records the flight commit in `/home/chao/carrierthink-flight-commit.txt`.\n"
        "3. The chain `bash scripts/flights/carriers/batch_chain_carrier_think.sh all` (or one carrier: `a2t`, `e21`, `e22`; segments `<carrier>:smoke`, `<carrier>:arms`).\n"
        "4. `bash scripts/flights/carriers/carrier_think_read.sh columns <carrier>` (official scoring), countersign the carrier's READ row, then `bash "
        "scripts/flights/carriers/carrier_think_read.sh read <carrier>`.\n\n"
        "## Read rule (preregistered)\n\n"
        "Per carrier, the standard scorer once per complete manifest through `core.scoring_batch`, never sharded: A2T `a2t-toolcall-official` (calibrated to arXiv:2604.22821 Table 3, the "
        "PAPER COLUMN beside the repo column) with `a2t-toolcall-v2` / `a2t-toolcall` / cost; Earnings `asr-wer-whisper` (corpus-level Whisper English-normalizer WER) beside the "
        "`saea-scoring-v1` numerics (`conec-entity-wer-official`, `numeric-value-accuracy-v1`, `semantic-high-impact-error-rate-v1`; Earnings-22 has the WER only). The reader reports "
        "each arm's level, the all-off minus direct difference (the A/A offset of this core on this carrier), the per-stratum table, and the decode-cost table (completion tokens, "
        "forced closes, cap hits, empty answers, seconds per contact). claims_benefit is false; development numbers only.\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate, context-fit proofs, the composed-config proof, serving and packet pins, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the plans (one generation plan per cell; one FIT plan per A2T cell) |\n"
        "| `analysis-recipe-<carrier>-v1.json` | the offline read of each carrier (its READ run id) |\n"
        "| `signoff-conditions-<carrier>-v1.json` | the machine sign-off conditions, EMITTED BY THE DERIVE |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `carrier_think_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md` by `--append-ledger`) |\n")


def file_sha256(root: Path, relpath: str) -> str:
    return hashlib.sha256((Path(root) / relpath).read_bytes()).hexdigest()


def write_package(root: Path, commit: str, at: str | None, *, append_ledger: bool = False, derive: bool = True, require_receipts: bool = False) -> dict:
    root = Path(root)
    at = at or datetime.now(timezone.utc).isoformat()
    if derive:
        dc.derive(write=True, require_receipts=require_receipts, root=root)
    proof = dc.prove(root)
    pkg = fam.PACKAGE
    ids = identities(root)
    recov = {k: rcv.persisted_recovery(fam.RECOVERIES, k, at, commit) for k in fam.ALL_KEYS if fam.recovery(k)}
    cost = cost_estimate()
    unpinned = {c: dc.receipt_pins(c, "alloff", require=False, root=root) for c in fam.CARRIERS}
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash", "run_id", "split_identity_hash", "units")}
                  for k, v in ids.items()},
        "findings": findings(), "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "decision_rule_fixed_here": "None: form-proof cells; the reader reports levels, the in-chain A/A difference and the decode-cost table; no node word and no admission.",
        "one_factor": "None: the carriers' direct baseline on the Thinking core (the all-off module block compiles to it).",
        "prohibitions": PROHIBITIONS, "protocol_id": f"{fam.SLUG}-protocol-v1", "registered_at_utc": at, "schema": "saea-registered-protocol-v1", "status": STATUS,
        "study_commit_at_registration": commit,
        "the_question": ("What are the A2T, Earnings-21 and Earnings-22 baselines of the Thinking core (all-off and direct, request-identical), and what is each carrier's own A/A offset on "
                         "that core? (P3.3; owner rulings 302 A, 306 A, 333 B.)")}
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, recov)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    for key in recov:
        for stale in fam.superseded_plan_file_names(key):
            if (root / pkg / stale).is_file():
                (root / pkg / stale).unlink()
    shas["protocol-registered-v1.json"] = protocol_sha
    for carrier in fam.CARRIERS:
        shas[f"signoff-conditions-{carrier}-v1.json"] = file_sha256(root, fam.signoff_conditions_path(carrier))
    recipe = {
        "authority": f"{DECISIONS} ({fam.OWNER_RULINGS}); {SPEC}; {INSTRUMENT}",
        "cell_kind": "CARRIER BASELINES on the Thinking core -- per carrier an all-off arm and a request-identical direct arm (in-chain A/A); claim ceiling none",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)", "measurement_design": "form-proof",
        "recipe_id": f"{fam.SLUG}-read-v1", "registered_at_utc": at,
        "carriers": {c: {"read_run_id": fam.read_run_id(c), "label": fam.CARRIER_SPEC[c]["label"], "primary_metric": fam.CARRIER_SPEC[c]["primary_metric"],
                         "paper_column": fam.CARRIER_SPEC[c]["paper_column"], "alloff_run": ids[fam.cell_key(c, "alloff")]["run_id"], "direct_run": ids[fam.cell_key(c, "direct")]["run_id"],
                         "smoke_run": ids[fam.cell_key(c, "smoke")]["run_id"], "instruct_comparator": fam.CARRIER_SPEC[c]["instruct_comparator"]} for c in fam.CARRIERS},
        "schema": "saea-analysis-recipe-v1",
        "stages": {"columns": "bash scripts/flights/carriers/carrier_think_read.sh columns <carrier>  (the standard scorer, one complete scoring per arm; prints no number)",
                   "read": "bash scripts/flights/carriers/carrier_think_read.sh read <carrier>  (refuses unless the carrier's READ row is root countersigned)",
                   "smoke": "bash scripts/flights/carriers/carrier_think_read.sh smoke <carrier>  (decode cost of the sealed smoke; the machine sign-off input)"},
        "what_is_not_here": "No margins block and no admission: nothing is locked here."}
    for carrier in fam.CARRIERS:        # one recipe per carrier: the registration gate wants ONE read run id per recipe
        per = dict({k: v for k, v in recipe.items() if k != "carriers"}, carriers={carrier: recipe["carriers"][carrier]},
                   read_run_id=fam.read_run_id(carrier), recipe_id=f"{fam.SLUG}-{carrier}-read-v1", carrier=carrier,
                   run_ids={"read": fam.read_run_id(carrier), **{k: ids[fam.cell_key(carrier, k)]["run_id"] for k in fam.KINDS}})
        shas[f"analysis-recipe-{carrier}-v1.json"] = reg.wjson(root, f"{pkg}/analysis-recipe-{carrier}-v1.json", per)
    facts = {
        "_note": ("Every model-free fact this DRAFT registration rests on, and the CANONICAL stage3_measurement blocks scripts/checks/stage3_effect_floor_check.py and "
                  "scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": {"cells": {k: {"units": v["units"], "generation_calls_cap": v["family_budget"]["generation_calls_cap"],
                                      "fit_endpoint_calls_cap": v["family_budget"]["fit_endpoint_calls_cap"],
                                      "speech_audio_seconds_cap": v["family_budget"]["repeated_speech_audio_seconds_cap"],
                                      "gpu_hours": v["family_budget"]["gpu_hours_fit_inclusive"]} for k, v in ids.items()}, "cost_estimate": cost},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "composed_config_proof": proof,
        "context_fit": {c: fam.fit_proof(c) for c in fam.CARRIERS},
        "findings": findings(), "identity": ids,
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET, "speech_packet_root": fam.THINK_PACKET_ROOT,
                 "a2t_promotion_receipt": fam.A2T_PROMOTION_RECEIPT,
                 "packet_pins_at_registration": {c: unpinned[c] for c in fam.CARRIERS},
                 "signoff_conditions": {c: {"path": fam.signoff_conditions_path(c), "sha256": shas[f"signoff-conditions-{c}-v1.json"]} for c in fam.CARRIERS}},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{fam.OWNER_RULINGS}; {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "rows": {k: v["units"] for k, v in ids.items()}, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids, root),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "status": "DRAFT-HELD"}
    if recov:
        facts["recovery"] = json.loads(json.dumps(recov))
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    totals = {"generation_calls_cap": sum(v["family_budget"]["generation_calls_cap"] for v in ids.values()),
              "fit_endpoint_calls_cap": sum(v["family_budget"]["fit_endpoint_calls_cap"] for v in ids.values()),
              "gpu_hours_fit_inclusive": round(sum(float(v["family_budget"]["gpu_hours_fit_inclusive"]) for v in ids.values()), 1)}
    draft = {
        "_draft_note": "A DRAFT for the coordinator to mint on the data root with scripts/flights/carriers/carrier_think_mint_receipt.py. It authorises nothing while its status is not 'decided'.",
        "antecedents": {"analysis_recipes": {c: {"path": f"{pkg}/analysis-recipe-{c}-v1.json", "sha256": shas[f"analysis-recipe-{c}-v1.json"]} for c in fam.CARRIERS},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]}, "registration_base_commit": commit},
        "authorization_basis": f"{fam.OWNER_RULINGS}; {INSTRUMENT}; {SPEC}.",
        "budget": {**totals, "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "cells": {k: v["family_budget"] for k, v in ids.items()}},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": "Fly the carrier base on the Thinking core, carriers A2T -> E21 -> E22: per carrier a four-unit smoke, the machine sign-off, the all-off arm and the direct arm.",
        "decision_id": fam.DECISION_ID, "eligible_attempt_ids": fam.eligible_attempt_ids(), "eligible_run_ids": fam.eligible_run_ids(),
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "starting or touching any serving session outside the registered swap",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool", "any change of the Thinking knobs",
                           "a test-split contact on any carrier"],
        "owner": "root", "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL, "no_child_start_stop": True}, "status": "DRAFT-NOT-MINTED"}
    if recov:
        draft["recovery"] = json.loads(json.dumps(recov))
        draft["supersedes_receipt"] = {"path": fam.DECISION_RELPATH, "note": "carrier_think_mint_receipt.py --supersede renames the old receipt to a dated backup first."}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(row_cells)} unconsumed rows -- the cells still on their first attempt (generation row, plus the live-phase-fit identity for A2T) and the three READ rows -- for the "
             f"carrier base on the Thinking core of the owner rulings in {fam.OWNER_RULINGS}. Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: "
             f"the resident Thinking session ({fam.THINK_SESSION}) is the SLURP lock's.", "",
             "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(cells) for cells in row_cells]
    rows_text = "\n".join(lines) + "\n"
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text)
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost, proof))
    prereg = (f"# Carrier base on the Thinking core, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. Development numbers only.\n\n"
              + "".join(f"Runs ({c}): `{ids[fam.cell_key(c, 'alloff')]['run_id']}`, `{ids[fam.cell_key(c, 'direct')]['run_id']}`, smoke `{ids[fam.cell_key(c, 'smoke')]['run_id']}`; read "
                        f"`{fam.read_run_id(c)}`.\n\n" for c in fam.CARRIERS)
              + f"The read rule and the cost are in `{pkg}/README.md`.\n\n## The measurement declarations\n\n```json\n"
              + json.dumps({"stage3_measurement": measurement_blocks(ids, root)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, fam.PREREG, prereg)
    result = {"package": pkg, "shas": shas, "cells": list(ids), "rows": len(row_cells)}
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
    parser.add_argument("--registered-at", default=None)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root to read and write")
    parser.add_argument("--append-ledger", action="store_true", help="append the DRAFT rows at the END of docs/exposure-ledger.md (idempotent)")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    parser.add_argument("--require-receipts", action="store_true", help="pin the real Thinking packet artifacts when deriving (refuses when one is absent)")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive,
                           require_receipts=args.require_receipts)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
