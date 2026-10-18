#!/usr/bin/env python3
"""Write the DRAFT readiness package of NX-T R3 (the Solver instruction-template column on the Thinking core, TRAIN Fold B), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips nothing, mints
nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``countersign-row-texts-v1.json``, ``draft-ledger-rows.md`` and the derive's ``signoff-conditions-v1.json``) and, beside it, the
preregistration.

    python -B scripts/flights/nx/nxt_r3_write_registration.py --study-commit <sha> [--registered-at 2026-10-18T12:00:00.000000+00:00]
        [--root DIR] [--append-ledger] [--no-derive]
        [--recovery-registered-at <UTC>] [--recovery-base-commit <sha>] [--append-recovery-ledger]

The arm set is DATA (``nxt_r3_arms.json``): change it, re-run the derive and then this writer; every number in the package follows (program id, contacts, plan
ceilings, the GPU-hour ceiling, the sign-off conditions, the texts).

RECOVERY hooks (generic mechanism, ``scripts/flights/lib/recovery.py``): ``nxt_r3_family.RECOVERIES`` is EMPTY on the first registration.
* rec1: once the coordinator commits ``predecessor-snapshot-arm-rec1-v1.json`` (``recovery.py snapshot``) and ``recovery-input-arm-v1.json`` (the diagnosis text) the
  family builds the arm cell's recovery, and this writer supersedes the first-attempt plans, writes the ``-rec1`` plans with the recovery block, re-verifies the committed
  predecessor snapshot against the data root when present, and puts the recovery ledger block (two DRAFT rows) in ``draft-ledger-rows.md``.
* rec2 (a RESUME of the stopped rec1 attempt, under an explicit owner exception; mode B = row checkpoint, mode A = trace, computed by ``nxt_r3_rec2_mode.py``): the
  generation plan then carries ``resume_from``, ``resume_budget`` and (when ``resume-replay-proof-rec2-v1.json`` is committed) the ``resume_replay_proof`` block.
``--append-recovery-ledger`` appends the recovery block to ``docs/exposure-ledger.md`` (idempotent). ``--registered-at`` defaults to the first registration's stamp.
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

import nxt_r3_derive_cells as dc  # noqa: E402
import nxt_r3_family as fam  # noqa: E402

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
#: The arm words, fixed here and implemented by the reader (``slurp_nxt_r3_solver_template_column_read.arm_words``). The twin ``aa`` is the in-flight A/A: its SLU delta
#: against ``lock`` is the offset o, and |o| is the bar. The rules apply in this order (the first that applies wins).
WORD_RULES = {
    "NOMINATED": (f"SLU delta CI95 lower bound > 0 AND intent delta point >= {fam.INTENT_GUARD_PP} pp AND the SLU delta point is not below the twin bar (the SLU delta "
                  "point is >= |o|, the absolute SLU delta point of the twin aa against lock)"),
    "EFFICIENT-NO-LOSS": (f"neither the SLU nor the intent delta shows a resolved loss (the NX-T R1 NO-RESOLVED-LOSS rule: SLU delta CI95 upper bound >= -|o|; intent delta CI95 "
                          f"upper bound >= -{fam.FLOOR_INTENT_PP} pp, the decision-190 intent floor) AND the Solver seconds per contact of the arm <= {fam.EFFICIENT_SECONDS_RATIO} x the "
                          "lock arm's"),
    "HARM": "SLU delta CI95 upper bound < 0",
    "NEUTRAL": "none of the above",
}
PROHIBITIONS = [
    "No test-split, DEV or Fold A contact (TRAIN Fold B only).",
    "No supply arm, no thinking column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "The system is the 268-B Thinking lock: the knowledge supply, the module graph, the post-processing, the decoding, the per-node thinking budget and cap and the roster "
    "are not changed. The Solver instruction template is the ONLY varied factor, and each candidate is the locked template plus one short paragraph (t4: two).",
    f"Every Solver arm contact carries the lock's thinking fields (budget {fam.DELIVERING_BUDGET}, cap {fam.COMPLETION_CAP}); no arm may set a decoding knob, a response format or a tool.",
    "arm_visits is first: the fan-out happens at the one Solver visit; the delivering arm's request is the locked plan's request, byte for byte (invariant I7v).",
    "No reasoning text is ever delivered, scored or carried to another node (reasoning_context_policy drop-reasoning-v1); a delivered reasoning marker stops the flight.",
    "No benefit claim and no admission: claims_benefit is false; a NOMINATED or EFFICIENT-NO-LOSS arm goes to a 2-arm Fold A confirm (not built here).",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt, the harness commit is on master, NX-T R2 (rec2) has sealed and the cells are flipped.",
    "No session is started by this registration. No paper-scale profile. No system-level claim.",
]
FINDINGS = [
    {"id": "why-the-use-node",
     "finding": ("Owner ruling 326 A opens the USE node on the Thinking core. The candidate templates are minimal deltas of the locked Solver template, each aimed at one measured "
                 "symptom: " + "; ".join(f"{a['arm_id']}: {a['evidence']}" for a in fam.ARM_SPECS)),
     "remedy": "none; the read reports the forced-close share (split by supplied-item bin) and the empty-gold false-fill rows (split by forced status) per arm."},
    {"id": "arm-contacts-carry-the-lock-thinking-fields",
     "finding": (f"The per-node thinking fields are composed at request time, keyed by the contact's ROLE ID, so a Solver template-arm contact resolves to the same budget "
                 f"{fam.DELIVERING_BUDGET} / max_tokens {fam.COMPLETION_CAP} / enable_thinking as the delivering contact. Proven at the request level over a fixture by "
                 "tests/unit/test_nxt_r3_registration.py and, for the cell, by the dry run (node_decoding per arm)."),
     "remedy": "none."},
    {"id": "in-flight-aa-twin",
     "finding": (f"The twin {fam.TWIN} (replicate_of {fam.DELIVERING}) is the in-flight A/A; its SLU delta against {fam.DELIVERING} is the offset o of the read. "
                 f"The 268-B cross-flight offsets (SLU +{fam.TWIN_OFFSET_268B_SLU_PP}, P3.1 {fam.TWIN_OFFSET_P31_SLU_PP}) are reported beside, never used in a word."),
     "remedy": "none."},
    {"id": "context-fit-with-the-template-addition",
     "finding": (f"The live slot is {fam.SLOT_TOKENS:,} tokens; the prompt limit of every contact at the {fam.COMPLETION_CAP:,}-token cap is {fam.PROMPT_LIMIT:,}. The longest candidate "
                 f"template adds {fam.fit_proof()['longest_added_tokens_over_lock']} estimated tokens over the lock's (template tokens are ESTIMATED from bytes at 3.5 per token, the method of "
                 f"the NX R1 packages; no tokenizer contact). The registered estimate (base 2,000 + longest template + {fam.MAX_SUPPLIED_ITEMS} items x 235) is "
                 f"{fam.fit_proof()['estimate_at_bound_tokens']:,} tokens and the sealed Fold B Solver prompt maximum ({fam.OBSERVED_SOLVER_PROMPT_MAX:,}) plus that addition still fits "
                 "(the derive refuses otherwise). The context-fit policy is compact-or-abstain."),
     "remedy": "none needed on the observed data."},
    {"id": "resident-session-no-new-fragment",
     "finding": (f"The target is the resident think-budget-np4 session ({fam.THINK_SESSION}, fragment {fam.THINK_MODEL}); the fragment's defaults ARE the lock form, so there is no "
                 "cell-level thinking policy and no serving change. The chain keeps the swap call, which is a no-op while that session is recorded resident (NX-T R2 rec2 flies on it)."),
     "remedy": "none."},
    {"id": "cost-is-a-conservative-envelope",
     "finding": (f"A row costs one Perception contact plus {fam.K} Solver contacts; every Solver contact is costed at the lock's measured Solver seconds ({fam.NODE_SECONDS['solver']:.2f} s), "
                 f"so the arm mix is {fam.ARM_MIX_ROWS} lock-row equivalents and the expected cost {fam.expected_gpu_hours(fam.ROWS):.1f} GPU-h against the lock flight's "
                 f"{fam.LOCK_FLIGHT_GPU_HOURS_MEASURED} GPU-h. t1 and t4 are meant to shorten the reasoning, so the model over-states them. Runs of 24 GPU-h or more are intended (owner)."),
     "remedy": "the smoke measures the real mix; the machine sign-off refuses unless it is within 1.3x of the registered one."},
    {"id": "serial-gpu-and-the-resident-session",
     "finding": ("Ruling 303 A: one experiment in flight. NX-T R2 (rec2) occupies the Thinking session; this package is DRAFT / HELD until R2 has sealed (the queue hook "
                 "scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh waits for CHAIN_NXT2_EXIT rc=0, then flips and starts the chain)."),
     "remedy": "the coordinator registers (derive .. commit) while R2 flies; the hook does flip .. chain."},
    {"id": "preflight-defers-to-the-exact-gate",
     "finding": ("As in the 268-B cells the model-free preflight counts the payload at 4 bytes per token (a placeholder); the cells defer to the registered exact per-contact "
                 "context-fit gate (preflight_budget_mode defer-to-native-contact-fit), which runs on every arm's REAL request."),
     "remedy": "none."},
    {"id": "machine-signoff-with-a-veto-window",
     "finding": ("The chain waits for the smoke's sign-off with chain_lib.sh wait_or_machine_signoff (reader nxt_r3_read.sh smoke, the conditions file the derive emits INSIDE this "
                 "package, marker /home/chao/nxt3-decode-signoff.marker, veto window 20 minutes). A refused machine sign-off falls back to waiting for a coordinator marker (12 h)."),
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
    """One row per arm in declared order: its template, token estimate and added paragraph(s) (the table the README prints)."""

    rows = []
    for spec in fam.ARM_SPECS:
        rows.append({"arm": spec["arm_id"], "role": "candidate", "template": spec["relpath"], "sha256": spec["sha256"], "template_tokens": spec["template_tokens"],
                     "added_paragraphs": spec["added_paragraphs"], "evidence": spec["evidence"]})
    rows.append({"arm": fam.TWIN, "role": "twin (replicate_of lock)", "template": fam.LOCKED_TEMPLATE, "sha256": fam.LOCKED_TEMPLATE_SHA,
                 "template_tokens": fam.DELIVERING_TEMPLATE_TOKENS, "added_paragraphs": [], "evidence": "the in-flight A/A"})
    rows.append({"arm": fam.DELIVERING, "role": "delivering", "template": fam.LOCKED_TEMPLATE, "sha256": fam.LOCKED_TEMPLATE_SHA,
                 "template_tokens": fam.DELIVERING_TEMPLATE_TOKENS, "added_paragraphs": [], "evidence": "the 268-B lock form; its requests are the lock's byte for byte"})
    return rows


def measurement_blocks(ids: Mapping[str, Mapping]) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        arm["run_id"]: {
            "measurement_design": "same-flight-node-column", "expected_effect_pp": fam.EXPECTED_EFFECT_PP, "claims_benefit": False, "claim": "nominated",
            "rows": fam.ROWS, "primary_metric": PRIMARY_METRIC, "primary_metric_key": "slu",
            "variant_cost": {"extra_contacts_per_row": fam.CONTACTS_PER_ROW - 2, "extra_audio_seconds": round(fam.extra_audio_seconds("arm"), 2)},
            "template_variants": {"node": "solver", "candidate_arms": len(fam.CANDIDATE_ARMS), "twin": True},
            "variant_kind": "solver-template", "aa_arm_id": fam.TWIN,
            "read_roster": fam.READ_ROSTER, "tuning_roster": fam.TUNING_ROSTER,
            "note": ("A per-arm nomination, not a benefit claim: the round maps four minimal Solver instruction-template changes on the Thinking core, so no effect is assumed "
                     f"({fam.EXPECTED_EFFECT_PP} pp SLU-F1) and the deliverable is the paired contrast with its cost. The null is the in-flight twin {fam.TWIN}; the design resolves a "
                     f"per-arm contrast of {fam.FLOOR_SLU_PP} pp SLU / {fam.FLOOR_INTENT_PP} pp intent at n = 1,080 (decision 190 node-column floors).")},
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": fam.SMOKE_ROWS,
            "primary_metric": "none (structural form, per-arm Solver decode cost and the forced-close behaviour only)", "read_roster": fam.READ_ROSTER,
            "tuning_roster": fam.TUNING_ROSTER,
            "note": (f"Four Fold B rows prove FORM only: the {fam.PROGRAM} module program with {fam.K} Solver arms loads on the resident Thinking session, each arm's request "
                     "carries the lock's thinking fields and its own pinned template, no node hits its cap, the live phase fit passes and the v4 receipt seals. "
                     "Scored by no one; four rows claim nothing under instrument rule 5.")},
    }


def cost_inputs_seconds() -> dict:
    m = fam.M
    return {"lock_seconds_per_row": m["seconds_per_row_lock"], "perception_seconds_per_contact": fam.NODE_SECONDS["perception"],
            "solver_seconds_per_contact": fam.NODE_SECONDS["solver"], "gpu_hours_per_1080_row_lock_flight": m["gpu_hours_per_1080_row_lock_flight"], "slots": m["slots"]}


def cost_estimate() -> dict:
    expected = fam.expected_gpu_hours(fam.ROWS)
    return {
        "formula": (f"expected = rows x arm mix / {fam.ROWS_PER_MINUTE_FULL} rows per minute / 60 with the arm mix {fam.ARM_MIX_ROWS} lock-row equivalents per row = "
                    f"(Perception {fam.NODE_SECONDS['perception']:.2f} s + {fam.K} x Solver {fam.NODE_SECONDS['solver']:.2f} s) / the lock row {fam.SECONDS_PER_ROW_LOCK:.2f} s, "
                    f"rounded UP to 0.01; ceiling = ceil_0.1(expected x {fam.GPU_MARGIN}); rows per minute = {fam.R2B_SLOTS} slots x 60 / the lock row seconds, rounded DOWN to 0.01"),
        "cost_model": {
            "module": "scripts/flights/nx/nxt_r3_family.py (ARM_MIX_ROWS, expected_gpu_hours)",
            "inputs": ("scripts/flights/nx/nxt_r3_cost_inputs.json (the NX-T R2b column flight of TRAIN Fold B, delivering arm: 9.23 GPU-h per 1,080-row lock flight, Perception 59 s "
                       "and Solver 64.07 s per contact at 4 slots; numbers only)"),
            "limits": "every Solver contact is costed at the lock's Solver seconds (an upper envelope for t1 / t4, which aim to shorten the reasoning)",
        },
        "inputs": {"arm_mix_rows": fam.ARM_MIX_ROWS, "rows_per_minute_full": fam.ROWS_PER_MINUTE_FULL, "margin": fam.GPU_MARGIN, "r2b_measured": cost_inputs_seconds()},
        "arm_mix_rows": fam.ARM_MIX_ROWS,
        "arm_table": arm_table_rows(),
        "column_flight": {"contacts": fam.program_calls("arm"), "plan_ceiling_calls": fam.original_generation_calls("arm"), "expected_gpu_hours": round(expected, 2),
                          "planned_ceiling_gpu_hours": fam.CELLS["arm"]["gpu_hours"],
                          "run_cumulative_plan_calls": fam.generation_calls("arm"), "run_cumulative_speech_audio_seconds": fam.cell_audio_cap("arm")},
        "smoke": {"contacts": fam.program_calls("smoke"), "planned_ceiling_gpu_hours": fam.CELLS["smoke"]["gpu_hours"]},
        "registered_total_gpu_hours": round(fam.CELLS["arm"]["gpu_hours"] + fam.CELLS["smoke"]["gpu_hours"], 1),
        "lock_only_flight_gpu_hours": round(fam.lock_flight_gpu_hours(), 2),
        "reference_r2b": f"one NX-T R2b delivering pass: 1,080 rows, {fam.LOCK_FLIGHT_GPU_HOURS_MEASURED} GPU-h at 4 slots ({fam.SECONDS_PER_ROW_LOCK:.1f} s per row)",
        "fallback_note": (f"The answer-only fallback adds at most one contact per budgeted-thinking contact: {fam.THINKING_CONTACTS_PER_ROW} per row (Perception 1 + {fam.K} Solver contacts); "
                          f"planned_model_calls is rows x ({fam.CONTACTS_PER_ROW} + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = {fam.original_generation_calls('arm')} "
                          f"(program maximum {fam.program_calls('arm')}). The FIT cap stays structural (rows x program contacts x endpoints = {fam.fit_contact_cap(fam.ROWS)})."),
    }


def context_fit() -> dict:
    """The context-fit proof, registered in the fit plans and the facts (the derive refuses when it is not ok)."""

    return fam.fit_proof()


def existing_plan(root: Path, pkg: str, key: str) -> dict | None:
    """The cell's committed generation plan (latest recovery name first, then back to the first-attempt name), or ``None`` on a first registration."""

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
            "mode": "checkpoint" if "checkpoint_sha256" in rec["resume_from"] else "trace", "kept_rows": counts["kept"], "flown_rows": counts["flown"],
            "partial_rows": counts["partial"], "unstarted_rows": counts["unstarted"],
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
    arms_doc = {row["arm"]: {k: row[k] for k in ("role", "template", "sha256", "template_tokens", "added_paragraphs")} for row in arm_table_rows()}
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
                "template_arms": json.loads(json.dumps(arms_doc)), "arm_order": list(fam.ARM_ORDER), "unused_budget_is_not_attempt_authority": True,
                "arm_visits": "first",
                "serving": {"swap_target": fam.SWAP_TARGET, "session": fam.THINK_SESSION, "model_fragment": fam.THINK_MODEL,
                            "server_geometry": f"-c {fam.ACTIVE_GEOMETRY['slots'] * fam.ACTIVE_GEOMETRY['slot_tokens']} -np {fam.ACTIVE_GEOMETRY['slots']} (the resident session, unchanged)"},
                "one_factor": ("The Solver's instruction template (roles.solver.template_variants): each candidate is the locked template configs/probes/slurp_native_role_solver_v2.txt plus "
                               "one short paragraph. The system, the knowledge supply, the sealed query vectors, the decoding, the per-node thinking budget and cap and the roster are "
                               "the 268-B lock's.")}
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
                 "(stage3_rollout_score --mode supply-variants) after the seal. Flown by scripts/flights/nx/batch_chain_nxt_r3.sh.")
        docs[fam.plan_file_name(key, "generation")] = {
            **base, **resume_extra, "execution_plan": gen, "execution_route": route, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
            "purpose": f"{i['run_id']}: {spec['role']} of NX-T R3.",
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


def recovery_ledger_mark(key: str = "arm") -> str:
    return f"## Cell NXT-R3 recovery rec{fam.recovery_index(key)}: "


RECOVERY_AUTHORITY_REC1 = f"{fam.OWNER_RULINGS} (the Solver instruction-template column) and the generic recovery re-registration (owner decision 309 A)"


def resume_mode_letter(rec: Mapping | None) -> str:
    """``B`` (row checkpoint) or ``A`` (trace) for a resume record; the pin key in ``resume_from`` decides."""

    return "B" if rec and "checkpoint_sha256" in (rec.get("resume_from") or {}) else "A"


_REC_ARM = fam.recovery("arm") or {}
RECOVERY_AUTHORITY = RECOVERY_AUTHORITY_REC1 + (
    f" and {_REC_ARM['owner_exception']} (the explicit exception to the one-recovery rule for the rec{_REC_ARM['recovery_index']} mode-{resume_mode_letter(_REC_ARM)} resume)"
    if _REC_ARM.get("owner_exception") else "")
SCOPE = (f"the 268-B Thinking lock system (plain review-off COMP-1b module graph on lock {fam.LOCK}) with the {fam.K}-arm Solver instruction-template column ("
         + ", ".join(fam.ARM_ORDER) + f") at the Solver node (program {fam.PROGRAM}, {fam.CONTACTS_PER_ROW} contacts per row), TRAIN Fold B ({fam.OWNER_RULINGS})")


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
                 (f"The offline read of NX-T R3: score the {fam.K} arm columns of the sealed column flight once each with the official scorer (stage3_rollout_score "
                  f"--mode supply-variants); the paired contrast of each candidate arm and the twin {fam.TWIN} against the delivering {fam.DELIVERING} arm, the arm words, the per-scenario "
                  f"table and the per-arm Solver completion / finish-reason / forced-close / supply-bin / empty-gold tables by the recipe {pkg}/analysis-recipe-v1.json. "
                  "Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
                 f"slurp TRAIN Fold B {arm['rows']}, the sealed column flight (after the seal)", "discovery", arm["split_identity_hash"], "no", "0", "0", "0", INHERITED,
                 f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the column flight is sealed and before any number is read) "
                 f"{at[:10]} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(ids: Mapping[str, Mapping]) -> dict:
    head = ("REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner ruling 326 A of 2026-10-17 "
            "(the USE-node round: the Solver instruction-template column on the Thinking core, TRAIN Fold B); ")
    tail = (f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/nx/nxt_r3_mint_receipt.py after this countersignature; the READ row "
            "stays a draft until the column flight is sealed)")
    rows = {}
    for key in fam.ALL_KEYS:
        i = ids[key]
        if fam.recovery(key):
            spec = fam.CELLS[key]
            clause = (f"the generation run id {i['run_id']} is unchanged; the decision receipt {fam.DECISION_RELPATH} is re-minted by the coordinator "
                      f"(nxt_r3_mint_receipt.py --supersede) so that its eligible_run_ids list the new FIT run id {i['fit_run_id']}")
            for run, label in ((i["run_id"], f"the {spec['role']}"), (i["fit_run_id"], f"live phase-fit identity of the {spec['role']}")):
                rows[run] = rcv.countersign_text(
                    fam.RECOVERIES, key, authority=RECOVERY_AUTHORITY, role=spec["role"], label=label, attempt=i["attempt_id"], fit_run=i["fit_run_id"],
                    fit_attempt=i["fit_attempt_id"], receipt_clause=clause, tail="the READ row stays a draft until the column flight is sealed")
            continue
        rows[i["run_id"]] = head + f"{fam.CELLS[key]['role']}" + tail
        rows[i["fit_run_id"]] = head + f"live phase-fit identity of the {fam.CELLS[key]['role']}" + tail
    rows[fam.READ_RUN_ID] = ("REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: owner ruling 326 A of "
                             "2026-10-17; the column flight is sealed at its flight commit and the sealed run was not opened for any number before this countersignature)")
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text "
                      "below, then mint the receipt. The ledger table is read by contracts._parse_ledger_tables."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def readme_text(ids: Mapping[str, Mapping], cost: Mapping[str, Any]) -> str:
    arm, smoke = ids["arm"], ids["smoke"]
    cf = cost["column_flight"]
    fit = fam.fit_proof()
    arm_rows = "\n".join(
        f"| `{r['arm']}` | {r['role']} | `{r['template']}` | `{r['sha256'][:12]}` | {r['template_tokens']} | "
        + (" / ".join(f'"{p}"' for p in r["added_paragraphs"]) if r["added_paragraphs"] else "(none: the locked template)") + " |" for r in cost["arm_table"])
    return (
        "# NX-T R3: the Solver instruction-template column on the Thinking core, TRAIN Fold B (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, and no session is started. Generated by "
        "`scripts/flights/nx/nxt_r3_write_registration.py` from the fragments `nxt_r3_derive_cells.py` wrote, from the arm table `scripts/flights/nx/nxt_r3_arms.json`. "
        "The NX-T R2b package (`docs/readiness/2026-10-17-slurp-nxt-r2b-solver-budget-fold-b-v1/`) is the worked example and is unchanged.\n\n"
        "## The question (owner ruling 326 A, the USE node)\n\n"
        "Does a minimal change of the Solver's instruction template move the score of the locked Thinking system? The Solver is contacted "
        f"{fam.K} times at its one visit over the SAME Perception note, evidence and QueryState, once per template, in ONE flight over the same 1,080 Fold B rows: "
        "four candidates, the in-chain twin and the delivering arm (the node-template instrument, `docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md`; "
        "`rails.supply_variants.parse_template_variants`; receipt `saea-supply-variant-arms-v4`; `arm_visits` first).\n\n"
        "## Arms (declared order; the twin, then the delivering arm LAST)\n\n"
        "| arm | role | template | sha256 | est. tokens | added paragraph(s) |\n| --- | --- | --- | --- | ---: | --- |\n"
        f"{arm_rows}\n\n"
        "Each candidate is the locked template with the paragraph(s) inserted before the revision paragraph, everything else byte-identical (the arm table validator checks this "
        "against the locked bytes). Template tokens are ESTIMATED as ceil(bytes / 3.5), the method of the NX R1 packages (no tokenizer contact).\n\n"
        "### Evidence per candidate\n\n" + "\n".join(f"* `{a['arm_id']}`: {a['evidence']}" for a in fam.ARM_SPECS) + "\n\n"
        "### Thinking fields of an arm contact\n\n"
        f"The delivering form is `thinking_budget_tokens` {fam.THINKING_KNOBS['thinking_budget_tokens']} + answer reserve {fam.THINKING_KNOBS['answer_reserve_tokens']} = completion cap "
        f"{fam.THINKING_KNOBS['completion_cap']}, `reasoning_context_policy` `{fam.THINKING_KNOBS['reasoning_context_policy']}`, temperature 0, seed 20260913, forced-close message "
        f"(`--reasoning-budget-message`): \"{fam.THINKING_KNOBS['budget_message']}\". These are the resident fragment's defaults and are composed per ROLE at request time, so every "
        "Solver arm contact carries them; `tests/unit/test_nxt_r3_registration.py` proves it over a request-level fixture. No cell-level `thinking_policy` exists.\n\n"
        "## Serving: the resident session\n\n"
        f"Swap target `{fam.SWAP_TARGET}`, session `{fam.THINK_SESSION}`, model fragment `{fam.THINK_MODEL}` ({fam.ACTIVE_GEOMETRY['slots']} slots x {fam.ACTIVE_GEOMETRY['slot_tokens']:,} tokens). "
        "NX-T R2 (rec2) flies on it, so the chain's swap call is a no-op at launch time. No new fragment, task or serving row.\n\n"
        "## Context fit (refused at derive if it does not hold)\n\n"
        "| quantity | tokens |\n| --- | ---: |\n"
        f"| live slot | {fit['slot_tokens']:,} |\n| operational reserve | {fit['reserve_tokens']:,} |\n| special reserve | {fit['special_reserve_tokens']} |\n"
        f"| completion cap | {fit['completion_cap']:,} |\n| prompt limit of every contact | {fit['prompt_limit_tokens']:,} |\n"
        f"| longest template over the lock's (estimate) | +{fit['longest_added_tokens_over_lock']} |\n"
        f"| registered estimate at {fit['max_supplied_items']} items (base 2,000 + longest template + 235 per item) | {fit['estimate_at_bound_tokens']:,} (headroom {fit['estimate_headroom_tokens']}) |\n"
        f"| observed Solver prompt maximum, sealed Fold B flights | {fit['observed_solver_prompt_tokens_max']:,} (headroom after the longest addition {fit['observed_headroom_tokens']}) |\n\n"
        "The Solver prompt mean is about 8,500 tokens.\n\n"
        "## Registered cells\n\n"
        "| cell | role | rows | program contacts | plan calls | run id | FIT run id | attempt id |\n| --- | --- | ---: | ---: | ---: | --- | --- | --- |\n"
        + "\n".join(f"| `{ids[k]['cell']}` | {fam.CELLS[k]['role']} | {ids[k]['rows']} | {fam.program_calls(k):,} | {fam.generation_calls(k):,} | `{ids[k]['run_id']}` | "
                    f"`{ids[k]['fit_run_id']}` | `{ids[k]['attempt_id']}` |" for k in fam.ALL_KEYS) + "\n\n"
        f"The system is the 268-B Thinking lock cell, derived by `nxt_r3_derive_cells.py` with exactly ONE addition (the Solver `template_variants` block, compiled by the module "
        f"compiler): lock `{fam.LOCK}`, program `{fam.PROGRAM}` ({fam.CONTACTS_PER_ROW} = 2 + ({fam.K} - 1) contacts per row), the Thinking model fragment `{fam.THINK_MODEL}`, "
        f"session `{fam.THINK_SESSION}`, the Thinking packets and their promotion receipt (`{fam.THINK_PROMOTION_RECEIPT}`), the fold-excluded knowledge supply and the roster "
        f"`{fam.ROSTER['arm']}` (1,080 rows); the smoke is the loop's own four Fold B rows (`{fam.ROSTER['smoke']}`). `preflight_budget_mode` is `defer-to-native-contact-fit`; "
        "the finite-completion policy is `deliver-latest-or-abstain` and the ReAct-exhaustion policy `continue-without-answer`. The derive proves the leaves that moved against the "
        "268-B parent (`moved_by_rule`): the Solver `template_variants` block and its declaration, the program id, the live-fit ids and cap, the cell's own supply pin and the cell text.\n\n"
        "## GPU ceiling (from measured throughput)\n\n"
        f"{cost['formula']}.\n\n"
        f"* Cost model: `{cost['cost_model']['module']}`, from {cost['cost_model']['inputs']}. Limits: {cost['cost_model']['limits']}.\n"
        f"* Arm mix {cost['arm_mix_rows']} lock-row equivalents per row; 1,080 rows at {fam.ROWS_PER_MINUTE_FULL} rows per minute: expected {cf['expected_gpu_hours']} GPU-h, registered "
        f"ceiling {cf['planned_ceiling_gpu_hours']} GPU-h = ceil_0.1({cf['expected_gpu_hours']} x {fam.GPU_MARGIN}) ({cf['contacts']:,} program contacts, plan ceiling "
        f"{cf['plan_ceiling_calls']:,} calls including at most {fam.THINKING_CONTACTS_PER_ROW} fallback re-asks per row).\n"
        f"* Smoke: {cost['smoke']['contacts']} program contacts, ceiling {cost['smoke']['planned_ceiling_gpu_hours']} GPU-h. Registered total {cost['registered_total_gpu_hours']} GPU-h.\n"
        f"* {cost['reference_r2b']}; a lock-only flight at the registered rate is {cost['lock_only_flight_gpu_hours']} GPU-h. The long run is intended (owner: GPU runs of 24 GPU-h or more).\n\n"
        "## Prerequisites and findings the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{f['id']}.** {f['finding']} Remedy: {f['remedy']}" for n, f in enumerate(FINDINGS, 1)) + "\n\n"
        "## Chain sequence (the coordinator's; flip and chain are the queue hook's)\n\n"
        "1. Register while R2 flies (model-free, master clean): `bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r3_launch_spec.json --root-countersign --until commit` "
        "(derive, write, countersign the five DRAFT rows, mint the receipt with `scripts/flights/nx/nxt_r3_mint_receipt.py`, commit). Register the Windows task `SAEA-Chain-NXT3` "
        "(wrapper `/home/chao/saea-queue/chain_nxt3.sh`, source `scripts/flights/batch/queue/chain_nxt3.sh`).\n"
        "2. Install the queue hook: `cp scripts/flights/batch/queue/queue_nxt3_after_nxt2.sh /home/chao/saea-queue/` and start it with the R2 rec2 start stamp as its first argument. It waits "
        "(poll 60 s, at most 30 h) for a `CHAIN_NXT2_EXIT rc=0` line in `/home/chao/nxt2-chain.out` stamped after that start, then runs `bash scripts/flights/batch/package_launch.sh "
        "scripts/flights/nx/nxt_r3_launch_spec.json --from flip --until chain` from the master checkout and logs to `/home/chao/nxt3-queue.out`; on an R2 exit with rc != 0 it logs and "
        "exits 9 without launching. Its flip-log refusal scan ignores the informational line `repin exit N (1 = its internal check refused the dirty tree, expected)`.\n"
        "3. The flip (`bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r3_flip.sh\" --package "
        f"{fam.PACKAGE} --cells {ids['smoke']['experiment']},{ids['arm']['experiment']} --pins-commit-msg /home/chao/nxt3-pins-commit.txt`, `NXT3_KINDS=\"smoke arm\"`) records the "
        "flight commit in `/home/chao/nxt3-flight-commit.txt`.\n"
        f"4. The chain `bash scripts/flights/nx/batch_chain_nxt_r3.sh all` swaps to `{fam.SWAP_TARGET}` only when that session is not resident (hold the idle watchdog), flies the smoke, "
        "waits for the sign-off with `wait_or_machine_signoff` (reader `bash scripts/flights/nx/nxt_r3_read.sh smoke`, conditions "
        f"`{fam.SIGNOFF_CONDITIONS}`, marker `/home/chao/nxt3-decode-signoff.marker`, veto window 20 minutes), flies the column and closes the exposure rows with `close_rows_after_seal`. "
        "`arm-only` is the recovery segment (smoke sealed, marker present).\n"
        "5. `bash scripts/flights/nx/nxt_r3_read.sh columns` (the official per-arm scoring; prints no number), countersign the READ row, then `bash scripts/flights/nx/nxt_r3_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READER}`: every arm's first-visit Solver answer is scored once, complete, by the official scorer (`slurp-slu-official-train`, `stage3_rollout_score --mode supply-variants`); "
        f"each candidate arm and the twin minus the delivering `{fam.DELIVERING}` arm, SLU-F1 (primary) and intent accuracy (guard), paired per row, utterance-cluster bootstrap "
        "CI95 (10,000 draws, seed 20261018). The twin is the in-flight A/A: its SLU delta is the offset o and |o| the bar. Words per candidate arm (fixed here and in the reader; "
        "the first that applies):\n\n"
        + "\n".join(f"* **{w}**: {t}." for w, t in WORD_RULES.items()) + "\n\n"
        "Secondaries per arm: the Solver forced-close share (overall and split by supplied-item bin, < 40 and >= 40 supplied items), completion tokens (mean / p50 / p90 / p99 / max), "
        "seconds per contact, the empty-gold false-fill share (overall and split by forced status), the non-empty exact-set rate, and the per-scenario table (natural mixture and equal "
        "scenario). claims_benefit is false; development numbers only (owner decisions 28 and 86).\n\n"
        "**Next step for a NOMINATED or EFFICIENT-NO-LOSS arm: a 2-arm Fold A confirm** (the arm against the lock on TRAIN Fold A). It is stated here and NOT built.\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate and model, context-fit proof, knobs, findings, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*-plan-registered-v1.json` | the registered protocol and the four plans (smoke, column flight; each generation and FIT; the FIT plans carry the context-fit proof) |\n"
        "| `analysis-recipe-v1.json` | the offline read |\n"
        "| `signoff-conditions-v1.json` | the machine sign-off conditions, EMITTED BY THE DERIVE from the arm table |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `nxt_r3_mint_receipt.py`) |\n"
        "| `countersign-row-texts-v1.json` | the countersign texts of the five DRAFT rows |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md` by `--append-ledger`) |\n\n"
        "## Registration check of a HELD package\n\n"
        "`python -B scripts/checks/flight_registration_check.py --cell <cell> [--cell <cell>]` on the two cells reports the held state and the missing countersignatures; it is run before the "
        "countersign and read by the coordinator.\n")


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
                             "moves the protocol hash); record resume_mode 'trace' in the rec2 recovery input (nxt_r3_rec2_mode.py computes it)")


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
        flown_text = ("re-flown whole after the failure of the first attempt" if rec["recovery_index"] == 1
                      else f"{rec['flown_phrase']} (explicit owner exception, {rec['owner_exception']})")
        scope = f"Cell NXT-R3 {spec['role']} -- RECOVERY rec{rec['recovery_index']}: {SCOPE}; {flown_text}"
        out[key] = rcv.recovery_ledger_block(
            fam.RECOVERIES, key, mark=recovery_ledger_mark(key), authority=RECOVERY_AUTHORITY, package=fam.PACKAGE, role=spec["role"], run=i["run_id"],
            fit_run=i["fit_run_id"], attempt=i["attempt_id"], fit_attempt=i["fit_attempt_id"], session=fam.THINK_SESSION, scope=scope,
            fit_scope=f"Cell NXT-R3 {spec['role']} -- RECOVERY rec{rec['recovery_index']} live phase-fit spend identity, request envelopes only, no generation.",
            model_tool=fam.think_model_text(key), carrier=f"slurp TRAIN Fold B {i['rows']:,}", split_hash=i["split_identity_hash"], caps=i["family_budget"],
            config_hash=i["composed_config_hash"], protocol_hash=i["protocol_hash"], registered_at=recovery_at, base_commit=recovery_base,
            worktree=worktree, branch=branch, plan_names=(fam.plan_file_name(key, "generation"), fam.plan_file_name(key, "fit")), inherited=INHERITED)
    return out


def history_caps(key: str, index: int, caps: dict) -> dict:
    """The run-cumulative caps AS OF recovery ``index`` (the original plan plus the spend of the attempts that recovery names); used to print an earlier
    recovery section of the README with its own cumulative numbers."""

    history = fam.RECOVERY_HISTORY[key]
    calls, audio = rcv.cumulative_budget({key: history[index - 1]}, key, fam.original_generation_calls(key), fam.audio_cap(fam.CELLS[key]["roster"]))
    return {**caps, "generation_calls_cap": calls, "repeated_speech_audio_seconds_cap": audio}


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
            caps = i["family_budget"] if later is None else history_caps(key, rec["recovery_index"], i["family_budget"])
            names = tuple(rcv.plan_file_name(spec["prefix"], kind, rec["recovery_index"]) for kind in ("generation", "fit"))
            out += rcv.recovery_section({key: rec}, key, role=spec["role"], run=i["run_id"], attempt=attempt, fit_run=fit_run, fit_attempt=fit_attempt, caps=caps,
                                        plan_names=names)
    return out


def recovery_sequence_text(ids: Mapping[str, Mapping]) -> str:
    """The coordinator's recovery sequence (README only)."""

    arm = ids["arm"]
    if fam.recovery_index("arm") >= 2:
        counts = fam.RECOVERIES["arm"]["resume_counts"]
        return (
            "\n### Recovery rec2 sequence (the coordinator's; it replaces steps 2 to 5 above)\n\n"
            "0. Snapshot the stopped rec1 attempt with `python -B scripts/flights/nx/nxt_r3_rec2_snapshot.py` (trace and checkpoint pins, both replay classifications), compute the "
            "resume mode with `python -B scripts/flights/nx/nxt_r3_rec2_mode.py`, commit `recovery-input-arm-rec2-v1.json` and, once run, `resume-replay-proof-rec2-v1.json` "
            "(`nxt_r3_rec2_replay_proof.py`).\n"
            "1. Run the writer on master WITH the recovery ledger block: `python -B scripts/flights/nx/nxt_r3_write_registration.py --study-commit <sha> "
            "--recovery-registered-at <UTC> --append-recovery-ledger`.\n"
            f"2. Fold the rec1 generation row of `{arm['run_id']}` into the rec2 row and countersign the two new rows (`{arm['run_id']}`, `{arm['fit_run_id']}`) with "
            "`countersign-row-texts-v1.json`; the READ row stays a draft until the seal.\n"
            "3. `python scripts/flights/nx/nxt_r3_mint_receipt.py --supersede` (the current receipt is renamed to a dated backup).\n"
            "4. `NXT3_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r3_flip.sh\" --package "
            f"{fam.PACKAGE} --cells {arm['experiment']} --pins-commit-msg /home/chao/nxt3-pins-commit.txt` (the arm cell only; `--allow-output-change` is never passed).\n"
            f"5. Hold the idle watchdog; `bash scripts/flights/nx/batch_chain_nxt_r3.sh arm-only` (flies {counts['flown']} rows; the merged manifest is {counts['roster']:,} rows).\n")
    return (
        "\n### Recovery rec1 sequence (the coordinator's; it replaces steps 2 to 4 above for the recovered column flight)\n\n"
        "0. (Before the writer.) Snapshot the failed attempt and commit the diagnosis: `python -B scripts/flights/lib/recovery.py snapshot --data-root $SPEECHRL_DATA_DIR "
        f"--run-id {arm['run_id']} --attempt-id <failed attempt id> --fit-run-id <fit run id> --fit-attempt-id <fit attempt id> --out {fam.PREDECESSOR_SNAPSHOT['arm']}`, and write "
        f"`{fam.RECOVERY_INPUT['arm']}` with the keys {', '.join(fam.RECOVERY_INPUT_KEYS)} (the family builds the recovery from these two files; no other edit).\n"
        "1. Re-run the writer on master with the recovery ledger block: `python -B scripts/flights/nx/nxt_r3_write_registration.py --study-commit <sha> "
        "--recovery-registered-at <UTC> --append-recovery-ledger`.\n"
        f"2. Countersign the two new rows (`{arm['run_id']}` recovery row, `{arm['fit_run_id']}`); fold the first-attempt generation row of the same run id into the recovery row.\n"
        "3. `python scripts/flights/nx/nxt_r3_mint_receipt.py --supersede`.\n"
        "4. The flip converges the arm cell; the sealed smoke is NOT flipped again: "
        f"`NXT3_KINDS=arm bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/nxt_r3_flip.sh\" --package {fam.PACKAGE} --cells "
        f"{arm['experiment']} --pins-commit-msg /home/chao/nxt3-pins-commit.txt`; then re-run the writer once at the flipped bytes.\n"
        "5. Hold the idle watchdog; `bash scripts/flights/nx/batch_chain_nxt_r3.sh arm-only` (refuses unless the smoke is sealed and the sign-off marker exists).\n")


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
    assert_resume_mode_is_launchable(root, ids)
    blockers = [{"id": "loader-refuses-the-derived-cell", "cell": k, "detail": v.get("refusal")} for k, v in loader.items() if not v.get("ok", False)]
    cost = cost_estimate()
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id", "protocol_hash",
                                           "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "arms": {row["arm"]: {"role": row["role"], "template": row["template"], "sha256": row["sha256"], "added_paragraphs": row["added_paragraphs"]} for row in arm_table_rows()},
        "blockers": blockers, "findings": FINDINGS,
        "decision_rule_fixed_here": (f"The arm words and their thresholds are fixed in {fam.READER} and in this package's README: NOMINATED, EFFICIENT-NO-LOSS, HARM, NEUTRAL "
                                     f"against the in-flight twin {fam.TWIN} (the A/A offset) and the decision-190 intent floor."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration per run id; run-cumulative budgets.",
        "one_factor": "the Solver instruction template (the locked template plus one short paragraph per candidate); the system is the 268-B Thinking lock on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-nxt-r3-solver-template-fold-b-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": ("Does a minimal change of the Solver's instruction template move the score of the locked Thinking system (owner ruling 326 A, the USE node)? Each candidate "
                         f"arm and the twin {fam.TWIN} are read PAIRED per row against the delivering {fam.DELIVERING} arm on the same 1,080 Fold B rows in one flight.")}
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
    shas["signoff-conditions-v1.json"] = file_sha256(root, f"{pkg}/signoff-conditions-v1.json")
    recipe = {
        "authority": f"{DECISIONS} ({fam.OWNER_RULINGS}); {SPEC}; {INSTRUMENT}; {fam.SPEC_DESIGN}",
        "cell_kind": (f"SAME-FLIGHT NODE COLUMN over the Solver instruction template -- {len(fam.CANDIDATE_ARMS)} candidate templates + the twin {fam.TWIN} paired per row against the "
                      f"delivering {fam.DELIVERING} arm; claim ceiling nominated"),
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flights themselves)",
        "measurement_design": "same-flight-node-column", "read_run_id": fam.READ_RUN_ID, "recipe_id": fam.RECIPE_ID, "registered_at_utc": at,
        "roster": {"relpath": fam.ROSTER["arm"], "roster_id": fam.READ_ROSTER, "rows": fam.ROWS, "split_identity_hash": arm["split_identity_hash"]},
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": fam.READ_RUN_ID, "smoke": smoke["run_id"], "smoke_fit": smoke["fit_run_id"]},
        "arms": list(fam.ARM_ORDER), "delivering": fam.DELIVERING, "twin": fam.TWIN, "candidates": list(fam.CANDIDATE_ARMS),
        "templates": {row["arm"]: {"relpath": row["template"], "sha256": row["sha256"], "template_tokens": row["template_tokens"]} for row in arm_table_rows()},
        "primary": {"metric": "official SLURP SLU-F1 per arm column (one complete scoring per column, slurp-slu-official-train)", "contrast": "arm minus lock, paired per row",
                    "interval": "utterance-cluster bootstrap CI95", "draws": 10000, "seed": 20261018},
        "guard": {"metric": "intent accuracy (scenario_action exact)", "nominated_point_floor_pp": fam.INTENT_GUARD_PP, "no_resolved_loss_floor_pp": -fam.FLOOR_INTENT_PP},
        "efficiency": {"solver_seconds_per_contact_ratio_max": fam.EFFICIENT_SECONDS_RATIO},
        "secondaries": ["solver_forced_close_share", "solver_forced_close_share_by_supplied_items_bin_lt40_ge40", "completion_tokens", "seconds_per_contact",
                        "empty_gold_false_fill", "empty_gold_false_fill_split_by_forced_status", "nonempty_exact_set", "per_scenario_natural_mixture_and_equal_scenario"],
        "next_step": "a NOMINATED or EFFICIENT-NO-LOSS arm goes to a 2-arm Fold A confirm (stated, not built)",
        "external_references": {"twin_offset_268b_slu_pp": fam.TWIN_OFFSET_268B_SLU_PP, "twin_offset_268b_intent_pp": fam.TWIN_OFFSET_268B_INTENT_PP,
                                "twin_offset_p31_slu_pp": fam.TWIN_OFFSET_P31_SLU_PP, "twin_offset_p31_intent_pp": fam.TWIN_OFFSET_P31_INTENT_PP,
                                "thinking_system_slu": fam.THINKING_SYSTEM_SLU},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_columns": "bash scripts/flights/nx/nxt_r3_read.sh columns  (stage3_rollout_score --mode supply-variants: one complete official scoring per arm; no number printed)",
            "2_read": f"python -B {fam.READER} --stage read --data-root $SPEECHRL_DATA_DIR (through scripts/flights/nx/nxt_r3_read.sh)",
            "smoke": f"python -B {fam.READER} --stage smoke (per-arm Solver decode cost; no countersignature; the machine sign-off input for the column flight)"},
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
        "findings": FINDINGS, "identity": ids,
        "pins": {"model_fragment": fam.THINK_MODEL, "serving_session": fam.THINK_SESSION, "swap_target": fam.THINK_SWAP_TARGET,
                 "speech_packet_root": fam.THINK_PACKET_ROOT, "speech_packet_promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                 "speech_packet_promotion_receipt_sha256": fam.thinking_promotion_sha256(),
                 "locked_template": {"relpath": fam.LOCKED_TEMPLATE, "sha256": fam.LOCKED_TEMPLATE_SHA},
                 "signoff_conditions": {"path": f"{pkg}/signoff-conditions-v1.json", "sha256": shas["signoff-conditions-v1.json"]}},
        "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{fam.OWNER_RULINGS}; {SPEC}. DRAFT: nothing here authorises a flip or a flight.",
        "read_rule": {"reader": fam.READER, "words": WORD_RULES, "word_order": list(WORD_RULES), "twin": fam.TWIN, "floors_pp": {"slu": fam.FLOOR_SLU_PP, "intent": fam.FLOOR_INTENT_PP},
                      "intent_guard_pp": fam.INTENT_GUARD_PP, "efficient_seconds_ratio": fam.EFFICIENT_SECONDS_RATIO, "delivering": fam.DELIVERING},
        "roster": {"arm": fam.ROSTER["arm"], "smoke": fam.ROSTER["smoke"], "roster_id": fam.READ_ROSTER, "split_identity_hash": arm["split_identity_hash"]},
        "rows": fam.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "thinking_knobs": json.loads(json.dumps(fam.THINKING_KNOBS)), "no_think_node": None,
        "template_arms": {row["arm"]: {"relpath": row["template"], "sha256": row["sha256"], "template_tokens": row["template_tokens"]} for row in arm_table_rows()},
        "status": "DRAFT-HELD"}
    if recov:
        facts["recovery"] = json.loads(json.dumps(recov))
        facts["predecessor_snapshots"] = snapshot_refs
        facts["recovery_budget"] = {k: rcv.recovery_budget(fam.RECOVERIES, k, ids[k]["family_budget"]) for k in recov}
        facts["resume"] = {k: {"resume_from": fam.recovery(k)["resume_from"], "counts": fam.recovery(k)["resume_counts"], "mode": fam.recovery(k)["resume_mode"],
                               "owner_exception": fam.recovery(k)["owner_exception"], "fix_commit": fam.recovery(k).get("fix_commit")}
                           for k in recov if fam.recovery(k).get("resume_from")}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/nx/nxt_r3_mint_receipt.py. It authorises "
                        "nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"{fam.OWNER_RULINGS}; {INSTRUMENT}; {SPEC}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": f"Fly the Solver instruction-template column on the Thinking core on TRAIN Fold B: four-row smoke, then the {fam.K}-arm column flight (with the twin).",
        "decision_id": fam.DECISION_ID, "eligible_attempt_ids": fam.eligible_attempt_ids(), "eligible_run_ids": fam.eligible_run_ids(),
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "starting or touching any serving session outside the registered swap",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool",
                           "any change beyond the registered Solver templates", "Fold A, DEV or test-split contact"],
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
                                                                           "recovery's FIT run id. nxt_r3_mint_receipt.py --supersede renames the old receipt to a dated backup first.")}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    row_cells = draft_rows(ids, commit, at, pkg, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"{len(row_cells)} unconsumed rows -- the cells still on their first attempt (generation row and live-phase-fit identity each) and the READ row; a "
             f"recovered cell's two rows follow this table as a recovery block -- for NX-T R3 of the owner rulings in {fam.OWNER_RULINGS}. "
             f"Package {pkg}. No row is countersigned and no row authorises a contact. No serving row: the Thinking session is the 268-B think-budget-np4 session "
             "(the same registered swap target); its serving row is the coordinator's at the swap.",
             "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"]
    lines += [reg.table_row(cells) for cells in row_cells]
    rows_text = "\n".join(lines) + "\n"
    blocks = recovery_blocks(root, ids, at, recovery_at, recovery_base, recovery_worktree, recovery_branch)
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text + "".join(blocks.values()))
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(ids))
    recovery_md = recovery_markdown(ids)
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(ids, cost) + recovery_md + (recovery_sequence_text(ids) if recov else ""))
    prereg = (f"# NX-T R3: the Solver instruction-template column, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. "
              "Development numbers only.\n\n"
              f"Runs: `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{fam.READ_RUN_ID}`.\n\n"
              f"The arm words and the read rule are in `{pkg}/README.md`.\n\n## The measurement declaration\n\n```json\n"
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
                        help="append ONLY the recovered cell's two DRAFT rows as a new ledger block; idempotent on the recovery attempt id")
    parser.add_argument("--recovery-registered-at", default=None,
                        help="UTC timestamp of the recovery re-registration (default: now); recorded in the recovery plan and ledger rows")
    parser.add_argument("--recovery-base-commit", default=None, help="the commit the recovery was registered on top of (default: --study-commit)")
    parser.add_argument("--recovery-branch", default="sonnet/nxt3-rec")
    parser.add_argument("--recovery-worktree", default="/home/chao/saea-worktrees/sonnet-nxt3-rec")
    parser.add_argument("--data-root", default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR"),
                        help="re-verify the predecessor snapshots against this data root when their attempt records are present")
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
