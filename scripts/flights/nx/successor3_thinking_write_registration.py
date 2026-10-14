#!/usr/bin/env python3
"""Write the DRAFT readiness package of SUCCESSOR 3 (the Thinking system on the signed test sample), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact; the data root is read only for the
DEV P3.1 read.json aggregate (the declared twin offset). Flips nothing, mints nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md``
unless ``--append-ledger`` is passed. Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` block and the ``composed_config_diffs`` proof, ``protocol-registered-v1.json``, ``generation-`` and ``fit-plan-registered-v1.json``,
``analysis-recipe-v1.json``, ``population-counts-v1.json``, ``read-qualification-v1.md``, ``successor-identity-map.json``, ``root-admission-draft-v1.json``,
``countersign-row-texts-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration page.

    python -B scripts/flights/nx/successor3_thinking_write_registration.py --study-commit <sha> --registered-at 2026-10-14T12:00:00+00:00
        [--root DIR] [--append-ledger] [--no-derive] [--require-receipt]
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import successor3_thinking_derive_cells as dc  # noqa: E402
import successor3_thinking_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
import write_tfrl_iteration_registration as reg  # noqa: E402

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

STATUS = "REGISTERED_BEFORE_CONTACT_HELD_BLOCKED_ON_PACKETS_AND_V2_ALLOWANCE"
DECISIONS = reg.OWNER_DECISIONS
INSTRUMENT = reg.INSTRUMENT_NOTE
V2_ALLOWANCE = "docs/receipts/owner/2026-10-14-slurp-test-sample-allowance-successor-3-v2.json"
DATA_ROOT = Path(os.environ.get("SPEECHRL_DATA_DIR") or os.environ.get("SAEA_DATA_ROOT") or "/home/chao/saea-data/speechrl-data")
LEDGER_COLUMNS = reg.LEDGER_COLUMNS
INHERITED = ("The SLURP test SAMPLE SLURP-TEST-SAMPLE-3010-V1 is not an unexposed sample: the label-free sample preparations (owner decision 156), the failed original PLAN "
             "generation, the SEALED successor-1 pair and the SEALED successor-2 composed column (read 2026-10-10) are inherited exposure in full. The closure roster "
             "SLURP-TEST-CLOSURE-10068-V1 stays untouched.")
THINK_MODEL_TEXT = ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M (qwen3-omni-30b-a3b-thinking-gguf-q4km), decoder-only build 04ccc72a, c98304 np4 x 24,576 max4096 "
                    f"(reasoning budget 3072), q8_0 KV, --reasoning-format deepseek (model fragment {fam.MODEL}); its own promoted sample speech packets; module program "
                    f"{fam.PROGRAM}; no tool authority")
PROHIBITIONS = [
    "No contact before every prerequisite in the README is cleared, root countersigns the rows, mints the decision receipt and the cell is flipped.",
    "ONE attempt per run id, ever: no re-fly, no recovery, no resume, no re-score, no re-projection, no best-of, no tuning on the sample.",
    "No smoke on the sample (the allowance lists a test-sample smoke as not authorised; the form proof is the flown P3.1 DEV chain); no twin; no re-flight, re-score or re-read of the sealed successor-2 run; no closure-roster or FULL-test contact.",
    "No k, tau, fuse_coverage, w_prior, store, release, snapshot, roster, role-graph, thinking-knob or geometry change. --allow-output-change is never passed.",
    "No utterance text, gold label, transcript, model output or reasoning text is printed or persisted by any read; aggregates, counts and hashes only.",
    "The packets encoder pass is a final-report preparation: it runs only under a countersigned exposure row AND an authorised allowance that lists its run id (the v2 DRAFT, owner decision 308).",
]


def read_dev_basis() -> dict:
    """The aggregate DEV P3.1 read (data root): the declared twin offset and the DEV point. Aggregates only."""

    path = DATA_ROOT / fam.SRC_READ_JSON_RELPATH
    document = json.loads(path.read_text(encoding="utf-8"))
    slu, intent = document["contrast"]["slu_f1"], document["contrast"]["intent"]
    r4 = lambda x: round(float(x), 4)  # noqa: E731
    d_slu, d_int = slu["d_system_lock_vs_inst"], intent["d_system_lock_vs_inst"]
    return {
        "source": f"{fam.SRC_READ_JSON_RELPATH} (data root); sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}",
        "verdict": document["verdict"], "n": document["contrast"]["n"],
        "twin_offset": {"slu_pp_signed": r4(slu["o_twin_aa_vs_lock"]["point_pp"]), "slu_pp": r4(abs(slu["o_twin_aa_vs_lock"]["point_pp"])),
                        "intent_pp_signed": r4(intent["o_twin_aa_vs_lock"]["point_pp"]), "intent_pp": r4(abs(intent["o_twin_aa_vs_lock"]["point_pp"])),
                        "slu_ci95": [r4(slu["o_twin_aa_vs_lock"]["ci95_lo_pp"]), r4(slu["o_twin_aa_vs_lock"]["ci95_hi_pp"])],
                        "intent_ci95": [r4(intent["o_twin_aa_vs_lock"]["ci95_lo_pp"]), r4(intent["o_twin_aa_vs_lock"]["ci95_hi_pp"])]},
        "d_system": {"slu_pp": r4(d_slu["point_pp"]), "slu_ci95": [r4(d_slu["ci95_lo_pp"]), r4(d_slu["ci95_hi_pp"])],
                     "intent_pp": r4(d_int["point_pp"]), "intent_ci95": [r4(d_int["ci95_lo_pp"]), r4(d_int["ci95_hi_pp"])]},
        "seed_of_the_dev_read": document["interval"]["seed"],
    }


def identity(root: Path) -> dict:
    document = json.loads((Path(root) / "configs" / "experiment" / f"{fam.CELL}.json").read_text(encoding="utf-8"))
    cell = document["cells"][0]
    composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], fam.CELL)
    split = document["population"]["split_identity_hash"]
    return {
        "experiment": fam.CELL, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"], "fit_run_id": composed.values["native_contact_fit"]["run_id"],
        "fit_attempt_id": composed.values["native_contact_fit"]["attempt_id"], "baseline_fragment": cell["baseline_fragment"], "dataset_fragment": cell["dataset_fragment"],
        "model_fragment": cell["model_fragment"], "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
        "split_role": document["execution_plan"]["split_role"], "roster_receipt": document["population"]["roster_receipt"], "composed_config_hash": composed.config_hash,
        "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split), "fit": dict(composed.values["native_contact_fit"]),
        "family_budget": document["family_budget"], "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
        "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"], "session": document["service_session"],
        "owner_allowance": document["owner_allowance"], "scorers": composed.values["scorers"], "packet_receipt": composed.values["speech_packet_promotion_receipt"],
        "packet_receipt_sha256": composed.values["speech_packet_promotion_receipt_sha256"], "readiness_state": cell["readiness"]["state"],
    }, document, composed


def measurement_block(i: Mapping, basis: Mapping, pins: Mapping) -> dict:
    off, dsys = basis["twin_offset"], basis["d_system"]
    return {
        fam.RUN: {
            "admission": "no-harm", "bar_pp": fam.HARM_MARGIN, "claim": "no-harm", "claims_benefit": False,
            "comparator_run_id": fam.S2_RUN, "comparator_attempt_id": fam.S2_ATTEMPT,
            "declared_flight_offset": {
                "slu_pp": off["slu_pp"], "intent_pp": off["intent_pp"],
                "signed": {"slu_pp": off["slu_pp_signed"], "intent_pp": off["intent_pp_signed"]},
                "scope": ("DECLARED, borrowed from the DEV P3.1 read (the in-chain twin aa minus the lock arm, DEV-2000-ADDED, n 1,000): the sample has NO in-chain "
                          "replicate by design. LIMITATION: the DEV twin offset is a different roster and a different n; it is the null this read uses, not a measured "
                          "null of the sample. The intent offset (1.6 pp) is large against the intent guard (0.65 pp) and is carried as read."),
                "source": basis["source"]},
            "design_statement": ("CROSS-FLIGHT AGAINST A SEALED COLUMN, NO IN-CHAIN REPLICATE, BY DESIGN: the allowance permits one generation run id (lock arm only), the "
                                 "sealed successor-2 run must not be re-flown, and a second flight would consume a second attempt. Instrument rule 4 refuses 'a single cross-flight "
                                 "contrast against an older sealed comparator with no in-chain replicate' (stage3_effect_floor_check.py scopes cells by a 'stage3' token in the "
                                 "fragment stem or experiment id, which this cell, like successors 1 and 2, does not carry, so the refusal is not mechanically enforced); the "
                                 "exception is the owner's: ruling 301 A fixes the declared DEV twin offset with the no-in-chain-replicate limitation stated in the read, "
                                 "the same exception decision 250 A made for successor 2."),
            "expected_effect_basis": {
                "primary": "official pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture, Thinking system minus the SEALED successor-2 column",
                "dev_point": dsys,
                "reading": (f"+{dsys['slu_pp']} pp is the DEV point of the Thinking lock arm minus the sealed Instruct NX R5 composed column (CI95 {dsys['slu_ci95']}); it is the "
                            "measured number of the P3.1 read (owner decision 139: a measured number, not a prior), declared at registration. claims_benefit stays false "
                            "in the sense of successor 2's read-qualification: a point above the bar is REPORTED, never claimed.")},
            "expected_effect_pp": dsys["slu_pp"],
            "expected_effect_status": "the P3.1 DEV point (owner decision 139), declared at registration",
            "harm_margin_pp": fam.HARM_MARGIN, "harm_margin_pp_by_metric": {"intent_accuracy": fam.HARM_MARGIN, "slu_f1": fam.HARM_MARGIN},
            "measurement_design": "cross-flight-no-replicate",
            "note": ("SUCCESSOR-3 = the SLURP lock candidate v3.0 (the locked system on the Thinking core) on the signed test sample (owner ruling 301 A). Primary: official "
                     "pooled SLU-F1 (post-stratified natural mixture; equal-stratum beside it); guard: intent (scenario_action exact). Contrast: Thinking arm minus the SEALED "
                     "successor-2 column. No claim of benefit. tuning_roster / read_roster (item D3): the vote pool and the centroid key are TRAIN construction artifacts, the v4 "
                     "rule set behind v4g was selected on the A2 DEV pool and confirmed on TRAIN Fold A and Fold B, COMP-1b on DEV-2000-ADDED; the Thinking transfer was read on "
                     "TRAIN Fold B (268-B) and DEV-2000-ADDED (P3.1) without tuning; all are disjoint from the sample by its disjointness proof "
                     "(docs/checks/speech-aware-evidence-acquisition/2026-09-27-slurp-test-sample-roster/disjointness.json, CLEAN); nothing was chosen or tuned on the sample."),
            "own_null": {"kind": "DECLARED-DEV-TWIN-OFFSET-NOT-MEASURED-ON-THE-SAMPLE", "slu_pp": off["slu_pp"], "intent_pp": off["intent_pp"],
                         "flag": "NO OWN NULL EXISTS FOR SLURP-TEST-SAMPLE-3010-V1 for the Thinking core (no A/A pair flew on it); the DEV twin offset is declared in its place.",
                         "scaled_fallback_for_context": dict(dc.W.scaled_null())},
            "primary_metric": ("official pooled SLU-F1 (slurp-slu-official-test), Thinking arm minus the sealed successor-2 column beyond the declared DEV twin offset; "
                               "intent accuracy (scenario_action exact) the non-inferiority guard"),
            "primary_metric_key": "slu", "read_roster": fam.ROSTER_ID,
            "roster": f"TEST-SAMPLE ({fam.ROSTER_ID}, split identity {i['split_identity_hash']}), 3,010 recordings / 682 prompts",
            "rows": fam.ROWS, "tuning_roster": ["slurp-train-construction-pool-agree-kprobe-r01-excluded", "SLURP-EVO-FOLD-A-V2", "SLURP-DEV-2000-ADDED-V1"],
            "owner_ruling_301_a": {"date": "2026-10-13", "ruling": ("Sign the successor-3 allowance now (same terms as v2: one attempt per id, aggregate-only, no smoke, no re-fly); only the lock "
                                                                     "arm flies on the sample; the comparator is the sealed successor-2 read; the declared twin offset is the DEV twin offset, "
                                                                     "with the no-in-chain-replicate limitation stated in the read."),
                                   "source": fam.ALLOWANCE}}}


DECISION_RULE = (
    "Read the Thinking arm (SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1) against the SEALED successor-2 column "
    "(SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1) on the same 3,010 rows, CROSS-FLIGHT (nothing is re-flown; no in-chain replicate by design). PRIMARY: official "
    "pooled SLU-F1 (slurp-slu-official-test), post-stratified natural mixture (equal-stratum beside it), paired per recording with a prompt-clustered bootstrap, "
    f"{fam.DRAWS:,} draws, seed {fam.SEED}. GUARD: intent accuracy (scenario_action exact), same contrast. DECLARED NULL: |o| = the DEV P3.1 twin offset (SLU {{slu}} pp / intent {{intent}} pp), "
    f"borrowed, not measured on the sample. HARM MARGIN {fam.HARM_MARGIN} pp. Verdict words are successor 2's: NEUTRAL iff the CI95 lower bound of (Thinking minus successor 2) on SLU-F1 and "
    f"on intent is at or above -{fam.HARM_MARGIN} pp and the read is not HARM; HARM iff the CI95 upper bound on SLU-F1 or on intent is below -|o| (a resolved loss beyond the declared offset, "
    f"owner decision 25); UNRESOLVED iff the lower bound is under -{fam.HARM_MARGIN} pp while neither HARM nor NEUTRAL. NOMINATED is NOT a registered outcome (claims_benefit false): a point above "
    "the bar and a CI95 lower bound above |o| are REPORTED beside the word as 'gain reported, not claimed' and would need their own replicated read. Reported beside, CONTEXT ONLY: per-intent "
    "and per-scenario tables in the post-stratified natural-mixture and equal-stratum weightings (58 intents), the recording-channel split, the cost table, per-node cap-hit / empty / "
    "forced-close counts. The verdict word is the coordinator's (owner decision 139). A milestone development read (owner decisions 28, 151, 301), never a test claim.")


def prerequisites(basis: Mapping) -> list[dict]:
    off = basis["twin_offset"]
    return [
        {"id": "packets-need-the-v2-allowance", "finding": (
            f"The signed successor-3 allowance ({fam.ALLOWANCE}) permits only the generation id and the FIT id. The Thinking packets of the sample are an encoder pass over slurp:test: "
            f"rows under the final-report role, so contracts.plan.require_owner_split_allowance refuses it unless a pinned, authorised allowance lists {fam.PACKETS_RUN} in "
            f"preparation_run_ids (successor 1's packets pass SAEA-SN-TEST-SAMPLE-3010-PREPROCESS cleared the guard exactly that way through the 2026-09-27 allowance). The signed bytes are NOT edited: "
            f"{V2_ALLOWANCE} is a DRAFT v2 successor that supersedes the signed receipt by sha, adds the packets id (encoder contact only, no answers, one attempt, its own countersigned "
            "exposure row, a GPU swap window) and carries the Thinking ceilings. The packets experiment fragment pins its path with 64 zeros: the driver (dry-run, --run, --promote-only) and "
            "the chain refuse while the pin is zero. The guard is unmodified."),
         "remedy": "owner decision 308 (proposed): the owner signs v2; the coordinator sets status 'authorised', commits, runs successor3_thinking_packets_fragments.py pin-allowance and commits the pin."},
        {"id": "packets-window-before-the-cells", "finding": (
            "The cell's baseline pins the Thinking sample promotion receipt TEST-SAMPLE-3010-promotion.json by path; its sha256 is the zero sentinel until the swap window writes it. "
            "Mint, flip and chain fail closed on the sentinel."),
         "remedy": "run the packets window (README step 5), then successor3_thinking_derive_cells.py --require-receipt and the package writer, and commit."},
        {"id": "ceilings-exceed-the-allowance-budget-block", "finding": (
            f"The signed allowance's budgets block (6,020 generation calls, 4.6 GPU-h, 16,413 audio seconds) is successor 2's. The Thinking ceilings from the P3.1 rule are "
            f"{fam.generation_calls():,} plan calls ({fam.program_calls():,} program contacts), {fam.planned_gpu_hours()} GPU-h and {fam.audio_cap():,} audio seconds (FIT cap {fam.fit_contact_cap():,} equals the allowance's). "
            "No code enforces the block (the gate reads status, split, permitted ids and the attempt budget), but the owner should know; the v2 draft carries the Thinking ceilings."),
         "remedy": "none beyond the v2 signature; the registered plans carry the Thinking ceilings."},
        {"id": "allowance-run-ids-block-names-successor-2", "finding": ("The signed allowance's run_ids block still describes the successor-2 ids. Documentation only: the gate uses permitted_run_ids, "
                                                                        "read_run_ids and preparation_run_ids, which are correct. The v2 draft corrects the block."),
         "remedy": "none."},
        {"id": "no-in-chain-replicate-the-twin-offset-is-declared", "finding": (
            f"The read has no in-chain twin: the null is the DEV twin offset (SLU {off['slu_pp']} pp, intent {off['intent_pp']} pp; the intent offset exceeds the 0.65 pp guard), borrowed from "
            "a 1,000-row DEV roster. A resolved SLU gain over successor 2 is reported against it; it is not a measured null of the sample."),
         "remedy": "the limitation is stated in the recipe, the read output and the README; do not describe the result as replicated."},
        {"id": "one-experiment-in-flight", "finding": "Ruling 303 A: one experiment in flight. The Thinking session think-budget-np4 is shared with other Thinking packages; the chain refuses while any flight is alive.",
         "remedy": "fly after the NX-T R1 chain has sealed (or as the coordinator orders)."},
    ]


def plan_docs(i: Mapping, commit: str, at: str, protocol_sha: str, rule: str) -> dict:
    base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": fam.SESSION, "experiment": i["experiment"],
            "family_budget": i["family_budget"], "preparation_base_commit": commit, "registered_at_utc": at, "status": STATUS,
            "prepared_phase_supply": {"relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": fam.ZERO,
                                      "note": "THIS CELL'S OWN artifact, minted model-free under its own run id at the flip (item E16); 64 zeros until then; --allow-output-change must never be passed."},
            "protocol_document": {"relpath": f"{fam.PACKAGE}/protocol-registered-v1.json", "sha256": protocol_sha}, "unused_budget_is_not_attempt_authority": True,
            "quality_read_gate": ("No task-quality read before the manifest is complete and sealed with one successful complete official slurp-slu-official-test score and the READ row is root countersigned.")}
    gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"], protocol_hash=i["protocol_hash"], run_id=i["run_id"],
               schema="saea-execution-plan-v1", split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition", owner_allowance=i["owner_allowance"])
    fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
    return {
        fam.plan_file_name("generation"): {**base, "execution_plan": gen, "plan_kind": "generation", "schema": "saea-registered-generation-plan-v1",
                                           "execution_route": f"Shared core.flight.cli campaign over {fam.CAMPAIGN_PLAN} (one cell) on the resident Thinking session ({fam.SESSION}), one official slurp-slu-official-test score at finalize. No smoke step.",
                                           "purpose": f"{i['run_id']}: " + rule},
        fam.plan_file_name("fit"): {**base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
                                    "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
                                    "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."},
    }


def draft_rows(i: Mapping, commit: str, at: str, shas: Mapping[str, str]) -> list[list[str]]:
    pkg, d = fam.PACKAGE, at[:10]
    split = i["split_identity_hash"]
    carrier = "slurp TEST-SAMPLE 3010"
    rows = [[d, fam.PACKETS_RUN, "bounded-discovery-probe",
             ("DRAFT -- REGISTERED. Thinking-core speech-packet preparation for the signed SLURP test SAMPLE (successor 3; GPU encoder pass, ONE window): one contact per row at "
              "max_tokens 1 over the 3,010 sample recordings, then ADDITIVE promotion into the existing Thinking packet root under the new receipt TEST-SAMPLE-3010-promotion.json. "
              "Label-free: no answer is read, no gold, transcript or model output is opened. Needs the v2 allowance (owner decision 308) to be signed and pinned before it can run."),
             ("Frozen Qwen3-Omni-30B-A3B-Thinking Q4_K_M encoder pass (qwen3-omni-30b-a3b-thinking-gguf-q4km, GPU, -np 1 -ngl 999, sidecar fragment "
              f"{fam.PACKETS_SIDECAR_FRAGMENT}); fixed one-token response never read"), carrier, "final-report", split, "no", str(fam.PACKETS_ROW_CALLS),
             str(fam.PACKETS_ROW_SPEECH_SECONDS), str(fam.PACKETS_ROW_GPU_HOURS), INHERITED,
             f"scripts/slurp_fold_preprocess_thinking.py --roster {fam.PACKETS_ROSTER_KIND}; configs/experiment/{fam.PACKETS_EXPERIMENT_FRAGMENT}.json; {V2_ALLOWANCE}",
             f"DRAFT at study commit {commit}; packets row of {pkg}; nothing authorised."]]
    for fit in (False, True):
        plan = f"{pkg}/{fam.plan_file_name('fit' if fit else 'generation')}"
        fb = i["family_budget"]
        rows.append([d, i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
                     "DRAFT -- REGISTERED. Thinking system arm (lock) on the signed test sample, the SLURP lock candidate v3.0 (the plain review-off COMP-1b module graph on lock "
                     f"{fam.LOCK}, program {fam.PROGRAM}, 2 contacts per row, no supply arm, no column), ONE attempt, no smoke (owner ruling 301 A)" + (" -- FIT spend identity" if fit else ""),
                     THINK_MODEL_TEXT, carrier, "final-report", split, "no", str(fb["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]),
                     str(fb["repeated_speech_audio_seconds_cap"]), str(fb["gpu_hours_fit_inclusive"]), INHERITED, plan,
                     f"DRAFT at study commit {commit}; plan SHA256 {shas.get(fam.plan_file_name('fit' if fit else 'generation'), 'pending')}; nothing authorised."])
    rows.append([d, fam.READ_RUN, "model-free-check",
                 ("The offline paired read of successor 3: score the Thinking arm once with the official scorer (core.scoring_batch, slurp-slu-official-test, complete, never sharded), "
                  "read it against the SEALED successor-2 column (post-stratified and equal-stratum, scorer-side strata, aggregate-only) and apply the registered rule against the "
                  f"declared DEV twin offset, by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
                 "no model or tool contact; read of sealed bytes and CPU official scoring", f"{carrier}, the sealed successor-3 arm (after the seal) and the sealed successor-2 run",
                 "final-report", split, "no", "0", "0", "0", INHERITED, f"{pkg}/analysis-recipe-v1.json",
                 f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the arm is sealed and before any number is read) {d} at study commit {commit}. Claims no benefit."])
    return rows


def countersign_texts(i: Mapping) -> dict:
    head = (f"REGISTERED BEFORE CONTACT (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: {fam.OWNER_RULINGS}; ")
    tail = f"; the decision receipt {fam.DECISION_RELPATH} is minted by scripts/flights/nx/successor3_thinking_mint_receipt.py after this countersignature; the READ row stays a draft until the arm is sealed)"
    rows = {
        fam.PACKETS_RUN: (head + f"the Thinking packets encoder pass over the signed test sample under the v2 allowance {V2_ALLOWANCE}, signed by the owner (decision 308) and pinned in "
                          "the packets fragment; label-free, one-token responses never read; GPU swap window via direct_fb_packets_gpu.sh --stage test-sample-3010)"),
        i["run_id"]: head + "the Thinking system arm (lock), one attempt, no smoke" + tail,
        i["fit_run_id"]: head + "live phase-fit identity of the Thinking system arm" + tail,
        fam.READ_RUN: (f"REGISTERED BEFORE READ (root countersigned <UTC timestamp> by root flight operations on the coordinator's brief: {fam.OWNER_RULINGS}; the arm is sealed at its "
                       "flight commit with one successful official score and the sealed run was not opened for any number before this countersignature)"),
    }
    return {"_note": ("Replace the leading 'DRAFT -- REGISTERED' scope marker and the 'DRAFT' note prefix of each row (keep the rest unchanged) with the text below, then mint the receipt. "
                      "The ledger table is read by contracts._parse_ledger_tables. The packets row is countersigned FIRST and separately (it gates the packets window)."),
            "decision_id": fam.DECISION_ID, "decision_receipt": fam.DECISION_RELPATH, "rows": rows}


def qualification_text() -> str:
    return (
        "# Successor 3: read qualification procedure (pre-registered; nothing has been read)\n\n"
        "Carried from successor 2's `read-qualification-v1.md` (`docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/read-qualification-v1.md`). Root qualifies the "
        "Thinking run BEFORE reading any scientific output:\n\n"
        "1. The Thinking attempt is FINALIZED at 3,010 rows with a verified seal and exactly one successful official `slurp-slu-official-test` score; no failed jobs.\n"
        "2. Fresh streamed hashes revalidate the final manifest and every referenced output, trace, trace manifest, score, serving receipt, generation manifest, phase summary and "
        "score-ledger artifact. Hashing does not interpret task content.\n"
        f"3. The SEALED successor-2 run (`{fam.S2_RUN}`) is revalidated against its sealed manifest; it is NOT re-flown, re-scored or re-read beyond the paired aggregate contrast.\n"
        "4. The delivery check compares the arm's flown boundary sets with its own prepared supply (aggregate row equality and mismatch counts only; a mismatch is an engineering "
        "defect, never permission to rerun).\n"
        f"5. Root countersigns the READ row `{fam.READ_RUN}` only for the registered comparison; `{fam.READ_DRIVER}` refuses before any score is opened otherwise.\n\n"
        "claims_benefit is false in successor 2's sense: a point above the bar is reported, never claimed. The twin offset is DECLARED (no in-chain replicate on the sample); the "
        "limitation is printed with every verdict. No test evidence may enter the system-text optimizer, proposer inputs, candidate selection or tuning. No allowance or scientific threshold changes.\n")


def readme_text(i: Mapping, basis: Mapping, proofs: Mapping, pins: Mapping, reqs: list[dict]) -> str:
    off, dsys = basis["twin_offset"], basis["d_system"]
    commute = proofs["composition_delta_commutes"]["graph_leaves_moved_by_the_core_swap_on_dev"]
    fb = i["family_budget"]
    return (
        "# SLURP test-sample successor 3: the Thinking system (SLURP lock candidate v3.0) on SLURP-TEST-SAMPLE-3010-V1 (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown, no session is started, and the allowance v2 is an unsigned DRAFT. "
        "Generated by `scripts/flights/nx/successor3_thinking_write_registration.py` from the fragments `successor3_thinking_derive_cells.py` wrote.\n\n"
        "**What it is.** The locked SLURP system on the Thinking core, flown ONCE on the signed 3,010-row test sample (owner ruling 301 A, 2026-10-13; P3.1 read NOMINATED on "
        "DEV-2000-ADDED: SLU +" + str(dsys["slu_pp"]) + " pp CI95 " + str(dsys["slu_ci95"]) + ", intent +" + str(dsys["intent_pp"]) + " pp CI95 " + str(dsys["intent_ci95"]) + "). "
        f"It is the P3.1 lock cell (`{fam.SRC['cell']}`, sealed at flight commit {fam.SRC_FLIGHT_COMMIT}) with the leaves moved that moved the R5 composed DEV cell to successor 2: the dataset view, "
        "roster receipt, packet promotion receipt (the NEW Thinking sample receipt `TEST-SAMPLE-3010-promotion.json`, pinned by path), the sample's speech-query vectors, alias and "
        "agreement table (successor 2's pins, reused by pin, never rebuilt), the row-scaled budgets, the final-report split role, the TEST scorer sibling `slurp-slu-official-test`, "
        "the one-attempt failure policy, the allowance pin (the signed successor-3 receipt, sha256 `" + i["owner_allowance"]["sha256"] + "`) and the run / attempt / FIT ids. "
        "`successor-identity-map.json` lists the replacements; `registered-facts-v1.json` (`composed_config_diffs`) PROVES from `core.config.compose` that nothing else moved.\n\n"
        "**No smoke cell.** The allowance forbids a test-sample smoke (a smoke under the read id would consume its one attempt). The form proof is the flown P3.1 DEV chain "
        "(smoke, lock and twin on DEV-2000-ADDED).\n\n"
        "## Identities\n\n"
        f"Cell `{fam.CELL}`, baseline `{fam.BASELINE}`, run `{fam.RUN}` (attempt `{fam.ATTEMPT}`), FIT `{fam.FIT_RUN}` (attempt `{fam.FIT_ATTEMPT}`), READ `{fam.READ_RUN}`, recipe "
        f"`{fam.RECIPE_ID}`, packets `{fam.PACKETS_RUN}` (attempt `{fam.PACKETS_ATTEMPT}`), decision `{fam.DECISION_ID}`. Roster `{fam.ROSTER_ID}` (3,010 recordings / 682 prompts; split "
        f"identity `{i['split_identity_hash']}`). Composed config hash `{i['composed_config_hash']}`; protocol hash `{i['protocol_hash']}`. Session `{fam.SESSION}` (swap target `{fam.SWAP_TARGET}`), "
        f"model fragment `{fam.MODEL}`, program `{fam.PROGRAM}`, lock `{fam.LOCK}`.\n\n"
        "## One-shot terms (ruling 301 A, carried from decisions 151 / 207 / 213)\n\nONE attempt per id, aggregate-only, no smoke, no recovery, no re-read, no selection, lock arm only. "
        f"The comparator is the SEALED successor-2 run `{fam.S2_RUN}` (the Instruct NX R5 composed arm on this sample); nothing is re-flown.\n\n"
        "## Measurement\n\n`cross-flight-no-replicate`. There is NO in-chain replicate on the sample, by design; the null is the DEV P3.1 twin offset, DECLARED: "
        f"SLU {off['slu_pp']} pp (signed {off['slu_pp_signed']}, CI95 {off['slu_ci95']}) and intent {off['intent_pp']} pp (signed {off['intent_pp_signed']}, CI95 {off['intent_ci95']}) "
        f"from `{basis['source']}`. LIMITATION: a different roster and n; borrowed, not measured on the sample; the intent offset exceeds the 0.65 pp guard. n = 3,010 (682 prompts). "
        "Primary: official pooled SLU-F1, post-stratified natural mixture (equal-stratum beside it); guard: intent. `admission: no-harm`, `claims_benefit: false`, `harm_margin_pp 2.5`, "
        f"`expected_effect_pp {dsys['slu_pp']}` (the P3.1 DEV point, a measured number under decision 139). Resampling: prompt-cluster paired bootstrap, {fam.DRAWS:,} draws, seed "
        f"{fam.SEED} (new; successor 2 used 20260915). Verdict words are successor 2's: HARM / NEUTRAL / UNRESOLVED (see `protocol-registered-v1.json`); a resolved gain is "
        "reported beside the word, never claimed.\n\n"
        "## Budgets and the GPU ceiling\n\n| item | value |\n| --- | ---: |\n| rows | 3,010 |\n| program contacts per row (policy c2) | 2 |\n"
        f"| program contacts | {fam.program_calls():,} |\n| generation plan cap (rows x (2 + 2 answer-only fallbacks)) | {fb['generation_calls_cap']:,} |\n"
        f"| FIT endpoint cap (rows x 2 x 4) | {fb['fit_endpoint_calls_cap']:,} |\n| repeated speech-audio seconds cap ceil(8,206.436875 x 4) | {fb['repeated_speech_audio_seconds_cap']:,} |\n"
        f"| planned GPU hours (FIT inclusive) | {fb['gpu_hours_fit_inclusive']} |\n| official complete scoring jobs | 1 |\n| packets pass | 3,010 contacts, 8,207 s, 1.0 GPU-h |\n\n"
        f"GPU ceiling = ceil_0.1(rows / {fam.MEASURED_ROWS_PER_MINUTE} rows per minute / 60 x {fam.GPU_MARGIN}) = ceil_0.1({fam.expected_wall_hours(fam.ROWS):.2f} h x {fam.GPU_MARGIN}) = {fam.planned_gpu_hours()} GPU-h "
        "(the P3.1 rule, `thinking_system_dev_family.planned_gpu_hours`; the P3.1 lock arm ran 1,000 rows / 2,000 program contacts in 9 h 10 min wall at 4 slots per the coordinator's brief, "
        "about 1.82 rows per minute, inside the 1.3 margin). The expected wall time is about 27.3 h; a ceiling is not a target.\n\n"
        "## The composed-diff proof (model-free, `core.config.compose`)\n\n"
        "* Successor 3 vs the P3.1 lock cell: `anything_else` and `composition_factor` are EMPTY; only roster-bound, role-bound, bookkeeping and experiment-block leaves moved.\n"
        "* Every roster- and role-bound leaf shared with the R5 DEV -> successor-2 mapping equals successor 2's value (run-specific leaves and the two packet-receipt leaves exempt: successor 2 "
        "pins the Instruct sample receipt, successor 3 the Thinking one); the two mappings move the SAME leaves.\n"
        f"* The composition delta commutes: the {len(commute)} graph leaves the core swap moved on DEV (R5 composed -> P3.1 lock) are the SAME {len(commute)} leaves successor 2 -> successor 3 moves, "
        "with identical values on both sides: " + ", ".join(f"`{k}`" for k in commute) + ".\n\n"
        "## Prerequisites the coordinator must clear BEFORE the countersign\n\n"
        + "\n".join(f"{n}. **{r['id']}.** {r['finding']} Remedy: {r['remedy']}" for n, r in enumerate(reqs, 1)) + "\n\n"
        "## Command sequence (the coordinator's)\n\n"
        "1. Owner decision 308: sign the v2 allowance; set its `status` to `authorised`, fill the signature, commit; `python -B scripts/flights/nx/successor3_thinking_packets_fragments.py pin-allowance`; commit.\n"
        f"2. Registration: `python -B scripts/flights/nx/successor3_thinking_write_registration.py --study-commit <sha> --registered-at <UTC> --append-ledger`; commit.\n"
        "3. Countersign the packets row (alone) with `countersign-row-texts-v1.json`; then `bash scripts/flights/direct/direct_fb_packets_gpu.sh --check --stage test-sample-3010`.\n"
        "4. The packets swap window: `bash scripts/flights/direct/direct_fb_packets_gpu.sh --run --stage test-sample-3010` (or `--task`); then `python -B scripts/slurp_fold_preprocess_thinking.py --roster thinking-test-sample-3010 --pin-receipt`; close the packets row (`ledger_mark_consumed.py --apply`).\n"
        "5. `python -B scripts/flights/nx/successor3_thinking_derive_cells.py --require-receipt`, re-run the package writer (step 2 without `--append-ledger`), commit.\n"
        "6. Countersign the generation, FIT and (draft until the seal) READ rows; `python scripts/flights/nx/successor3_thinking_mint_receipt.py --report-date <YYYY-MM-DD> --report-arm \"P3.1 NOMINATED\"`.\n"
        f"7. `bash scripts/flights/batch/flip_package_ext4.sh --flip \"scripts/flights/nx/successor3_thinking_flip.sh\" --package {fam.PACKAGE} --cells {fam.CELL} --pins-commit-msg /home/chao/{fam.SHORT}-pins-commit.txt`.\n"
        "8. Hold the idle watchdog (the packets window already left the Thinking session resident); `bash scripts/flights/nx/batch_chain_successor3_thinking.sh`.\n"
        "9. `bash scripts/flights/batch/serving_swap.sh slurp-np4` (swap back); countersign the READ row; `bash scripts/flights/nx/successor3_thinking_read.sh`.\n\n"
        "## Read rule (preregistered)\n\n"
        f"`{fam.READ_DRIVER}` scores the arm ONCE, complete, through `core.scoring_batch` (via `stage3_paired_read.py` pair mode with `--strata-source scorer`), then "
        f"`{fam.READER}` applies the rule in `protocol-registered-v1.json` to the aggregate output and prints the limitation with the word. It refuses before any score is opened unless "
        "the READ row is root countersigned, and prints no number from the sample before the aggregate read.\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, pins, the composed-diff proof, the `stage3_measurement` block |\n"
        "| `protocol-registered-v1.json`, `generation-plan-registered-v1.json`, `fit-plan-registered-v1.json` | the registered protocol and plans |\n"
        "| `analysis-recipe-v1.json`, `population-counts-v1.json`, `read-qualification-v1.md` | the offline read |\n"
        "| `successor-identity-map.json` | the leaf replacements from the P3.1 lock cell |\n"
        "| `root-admission-draft-v1.json`, `countersign-row-texts-v1.json`, `draft-ledger-rows.md` | the mint draft, the countersign texts and the four DRAFT rows (packets, generation, FIT, READ) |\n")


def write_package(root: Path, commit: str, at: str, *, append_ledger: bool = False, derive: bool = True, require_receipt: bool = False) -> dict:
    root = Path(root)
    if derive:
        dc.derive(write=True, require_receipt=require_receipt)
    os.chdir(root)
    i, document, composed = identity(root)
    proofs = dc.prove()
    pins = dc.sample_pins()
    basis = read_dev_basis()
    pkg = fam.PACKAGE
    reqs = prerequisites(basis)
    block = measurement_block(i, basis, pins)
    shas: dict[str, str] = {}
    rule = DECISION_RULE.format(slu=basis["twin_offset"]["slu_pp"], intent=basis["twin_offset"]["intent_pp"])
    protocol = {
        "schema": "saea-registered-protocol-v1", "protocol_id": "slurp-milestone-successor3-thinking-system-protocol-v1", "registered_at_utc": at,
        "study_commit_at_registration": commit, "status": STATUS,
        "the_question": ("Does the locked system on the Thinking core (SLURP lock candidate v3.0, NOMINATED on DEV-2000-ADDED), flown once on the signed test sample, keep the sealed "
                         "successor-2 column's accuracy and by how much does it differ, with official SLU-F1 primary and intent the guard, against the declared DEV twin offset?"),
        "the_composition": dc.COMPOSITION,
        "cells": {"thinking": {k: i[k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash", "program")}},
        "decision_rule_fixed_here": rule, "verdict_words": ["NEUTRAL", "HARM", "UNRESOLVED"], "stage3_measurement": block,
        "one_shot_semantics": "ONE per run id, ever; no recovery, no resume, no re-score, no re-read (allowance attempt_budget and milestone_rule)",
        "model_free_proofs_landed_before_contact": {"composed_config_diffs": proofs},
        "blockers_before_the_flip": [r["id"] + ": " + r["finding"] for r in reqs],
        "development_numbers_only": "Every number is a milestone development number (owner decisions 28, 86, 151, 301); never a test claim and never the final read.",
        "failure_policy": document["failure_policy"], "authority": f"{fam.OWNER_RULINGS} ({DECISIONS}); allowance {fam.ALLOWANCE}; the instrument {INSTRUMENT}",
        "prohibitions": PROHIBITIONS}
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    shas["protocol-registered-v1.json"] = protocol_sha
    for name, doc in plan_docs(i, commit, at, protocol_sha, rule).items():
        shas[name] = reg.wjson(root, f"{pkg}/{name}", doc)
    counts_text = io.open(root / fam.S1_PACKAGE / "population-counts-v1.json", encoding="utf-8", newline="").read()
    shas["population-counts-v1.json"] = reg.wr(root, f"{pkg}/population-counts-v1.json", counts_text)
    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1", "recipe_id": fam.RECIPE_ID, "read_run_id": fam.READ_RUN, "registered_at_utc": at,
        "title": "Test-sample SUCCESSOR3-THINKING-SYSTEM -- the locked system on the Thinking core against the sealed successor-2 column on SLURP-TEST-SAMPLE-3010-V1",
        "arms": {"arm": {"run_id": fam.RUN, "attempt_id": fam.ATTEMPT, "fit_run_id": fam.FIT_RUN, "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
                 "comparator": {"run_id": fam.S2_RUN, "attempt_id": fam.S2_ATTEMPT, "role": "the SEALED successor-2 column (the Instruct NX R5 composed arm on this sample): the cross-flight comparator the registered claim is read against; never re-flown"}},
        "no_in_chain_replicate": "By design: one new generation run id, lock arm only. The DEV P3.1 twin offset is declared, not measured (declared_flight_offset).",
        "declared_flight_offset": block[fam.RUN]["declared_flight_offset"],
        "verdict_rule": {"words": ["NEUTRAL", "HARM", "UNRESOLVED"], "harm_margin_pp": fam.HARM_MARGIN, "text": rule,
                         "reported_beside": ["gain_reported_not_claimed: SLU CI95 lower bound above the declared SLU offset", "point against the 2.5 pp bar"]},
        "read_driver": {"command": f"bash {fam.READ_DRIVER}", "reader": fam.READER, "scorer": fam.SCORER,
                        "passes": ["vs-comparator (Thinking arm minus the sealed successor-2 column; cross-flight; THE REGISTERED CLAIM, read beyond the declared offset)"],
                        "refusal": "the driver refuses before any score is opened unless this READ row is root countersigned and both sealed run manifests exist",
                        "strata_source": "scorer: post-stratification by gold intent INSIDE the official-scoring step (--strata-source scorer), aggregates only"},
        "resampling": {"bootstrap_draws": fam.DRAWS, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": fam.SEED, "unit": "prompt cluster (paired)"},
        "weightings": {"natural_mixture": "POST-STRATIFIED (PRIMARY weighting): per-intent values weighted by the full-test per-intent shares in population-counts-v1.json; the raw roster mean is NOT the natural-mixture number",
                       "equal_stratum": "1/58 over the intents present in the sample (reported beside the primary weighting)",
                       "post_stratification": "58 strata carried of 59 counted; computed and bootstrapped inside the scorer process; aggregates only"},
        "steps": [
            "1. Refuse unless the Thinking manifest is COMPLETE at 3,010 rows with this registration's composed config hash (as re-pinned at the flip), sealed, with one successful complete official slurp-slu-official-test score, the sealed successor-2 manifest is present, and the READ row is root countersigned.",
            "2. THE DELIVERY CHECK (gold-free): the arm's flown first-phase boundary selections equal its own prepared supply. A mismatch is an engineering defect, is reported, and consumes the milestone (no re-fly).",
            "3. THE STRUCTURAL CHECK (gold-free): exactly 2 program contacts per row (perception, solver) plus at most 2 answer-only fallbacks, no Reviewer or Planner row, every row delivered through saea-deliver-normalise-v4g, zero reasoning markers delivered.",
            f"4. Primary: official pooled SLU-F1 post-stratified, Thinking minus the sealed successor-2 column, paired per recording, prompt-clustered, {fam.DRAWS:,} draws, seed {fam.SEED}. Guard: intent accuracy. Equal-stratum beside it. Apply the protocol's rule against the declared offset and the harm margin {fam.HARM_MARGIN}; print the no-in-chain-replicate limitation with the word.",
            "5. Context: per-intent and per-scenario tables in both weightings; recording-channel split; per-node cap-hit / empty / forced-close counts; the cost table.",
            "6. Write the read under its own id; every number is a MILESTONE development number (owner decisions 28, 151, 301), never a test claim."],
        "output": {"analysis_root": fam.ANALYSIS_ROOT},
        "boundary": "A milestone read on the signed test sample. No utterance text, transcript, gold label string, model output or reasoning text is printed or persisted: ids, counts, rates and hashes only."}
    shas["analysis-recipe-v1.json"] = reg.wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    shas["read-qualification-v1.md"] = reg.wr(root, f"{pkg}/read-qualification-v1.md", qualification_text())
    identity_map = {
        "source_cell": fam.SRC["cell"], "source_baseline": fam.SRC["baseline"], "contacts_per_row": fam.CONTACTS_PER_ROW, "generation_rows": fam.ROWS, "dispatch_authority": False,
        "p31_dev_to_successor3_replacements": {
            "cell": [fam.SRC["cell"], fam.CELL], "baseline": [fam.SRC["baseline"], fam.BASELINE], "run_id": [fam.SRC["run"], fam.RUN], "attempt_id": [fam.SRC["attempt"], fam.ATTEMPT],
            "fit_run_id": [fam.SRC["fit_run"], fam.FIT_RUN], "fit_attempt_id": [fam.SRC["fit_attempt"], fam.FIT_ATTEMPT],
            "dataset_fragment": ["slurp-speech-native-dev2000-added", fam.DATASET], "scorer": ["slurp-slu-official", fam.SCORER], "split_role": ["dev", fam.SPLIT_ROLE],
            "roster_receipt": ["docs/receipts/rosters/slurp-dev-2000-added-v1.json", fam.ROSTER_RECEIPT],
            "speech_packet_promotion_receipt": [f"{fam.THINK_PACKET_ROOT}/DEV-2000-ADDED-promotion.json", i["packet_receipt"]],
            "owner_allowance": [None, i["owner_allowance"]]},
        "leaves_changed_from_the_p31_dev_cell": {k: v for k, v in proofs["s3_vs_p31_lock_dev"].items() if v},
        "reused_from_successor2": {"pins": [{"relpath": k, "sha256": pins[k]} for k in sorted(pins)], "note": "the sample's speech-query vectors, alias, encode receipt and agreement table; never rebuilt"},
        "leaves_unchanged": "every other composed leaf equals the P3.1 lock cell's value (the proof in registered-facts-v1.json composed_config_diffs)",
        "owner_decisions": ["25", "28/86", "139", "141", "151", "207/213", "250 A (successor-2 exception)", "299 A", "301 A", "308 (proposed)"]}
    shas["successor-identity-map.json"] = reg.wjson(root, f"{pkg}/successor-identity-map.json", identity_map)
    post = json.loads(io.open(root / fam.S1_PACKAGE / "registered-facts-v1.json", encoding="utf-8").read())["post_stratification_read"]
    facts = {
        "schema": "saea-registered-facts-v1", "_note": "Every model-free fact the SUCCESSOR-3 test-sample milestone registration rests on, and the CANONICAL stage3_measurement block.",
        "registered_at_utc": at, "study_commit_at_registration": commit, "status": STATUS, "rows": fam.ROWS, "the_composition": dc.COMPOSITION,
        "allowance": {"path": fam.ALLOWANCE, "sha256_pinned_in_the_fragment": i["owner_allowance"]["sha256"], "status": "authorised (signed 2026-10-13, ruling 301 A)",
                      "read_run_ids_used": [fam.RUN], "preparation_run_ids_used": [fam.FIT_RUN], "v2_draft": V2_ALLOWANCE,
                      "v2_draft_sha256_at_registration": fam.sha_file(V2_ALLOWANCE), "packets_run_id": fam.PACKETS_RUN,
                      "smoke": "NOT REGISTERED: the allowance lists a test-sample smoke as not authorised; the form proof is the flown P3.1 DEV chain.",
                      "attempts": "ONE per run id, ever; no recovery, no resume, no re-score, no re-read"},
        "owner_decisions": {"25": "a measured loss on either guard is HARMFUL", "28/86": "development numbers only; never a test claim", "139": "no prior; a number derived from a measured read is not a prior",
                            "151/207/213": "one-shot terms", "250 A": "the cross-flight-no-replicate exception (successor 2)", "299 A": "rebuild the base on Thinking",
                            "301 A": "sign the successor-3 allowance; lock arm only; comparator = sealed successor 2; declared DEV twin offset", "308 (proposed)": "the v2 allowance adding the packets pass"},
        "p31_read_basis": basis, "stage3_measurement": block,
        "cells": {"thinking": {k: i[k] for k in ("cell", "experiment", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id", "baseline_fragment", "dataset_fragment", "model_fragment", "arm", "rows",
                                                  "split_identity_hash", "split_role", "composed_config_hash", "protocol_hash", "program", "scorers", "owner_allowance", "readiness_state",
                                                  "packet_receipt", "packet_receipt_sha256", "session")}},
        "comparators_sealed": {"primary": {"run_id": fam.S2_RUN, "attempt_id": fam.S2_ATTEMPT, "package": fam.S2_PACKAGE, "role": "the Instruct NX R5 composed arm on this sample"}, "re_flown": False},
        "sample_preparation_pins": {"pins": [{"relpath": k, "sha256": pins[k]} for k in sorted(pins)], "note": "Reused BY PIN from successor 2's baseline; never rebuilt, never re-encoded. The cell's own first-phase supply is minted at the flip (item E16): 64 zeros until then."},
        "packets": {"run_id": fam.PACKETS_RUN, "attempt_id": fam.PACKETS_ATTEMPT, "roster": fam.PACKETS_ROSTER_KIND, "stage": fam.PACKETS_STAGE, "promotion_receipt": fam.THINK_PROMOTION_RECEIPT,
                    "sidecar_fragment": fam.PACKETS_SIDECAR_FRAGMENT, "experiment_fragment": fam.PACKETS_EXPERIMENT_FRAGMENT, "legacy_cache": fam.PACKETS_LEGACY_CACHE,
                    "row": {"calls": fam.PACKETS_ROW_CALLS, "speech_audio_seconds": fam.PACKETS_ROW_SPEECH_SECONDS, "gpu_hours": fam.PACKETS_ROW_GPU_HOURS},
                    "guard": "contracts.plan.require_owner_split_allowance, unmodified; the fragment pins the v2 DRAFT path with 64 zeros until the owner signs"},
        "composed_config_diffs": {**proofs, "derive_script": {"relpath": "scripts/flights/nx/successor3_thinking_derive_cells.py", "sha256": fam.sha_file("scripts/flights/nx/successor3_thinking_derive_cells.py")}},
        "budget_arithmetic": {"family_budget": i["family_budget"], "derivation": [
            f"generation_calls_cap = {fam.ROWS:,} x ({fam.CONTACTS_PER_ROW} program + {fam.FALLBACK_CONTACTS_PER_ROW_CEILING} answer-only fallback) = {fam.generation_calls():,} (program maximum {fam.program_calls():,}), run-cumulative",
            f"fit_endpoint_calls_cap = {fam.ROWS:,} x {fam.CONTACTS_PER_ROW} x 4 = {fam.fit_contact_cap():,}",
            f"repeated_speech_audio_seconds_cap = ceil(8,206.436875 x {fam.CONTACTS_PER_ROW + fam.FALLBACK_CONTACTS_PER_ROW_CEILING}) = {fam.audio_cap():,}",
            f"gpu_hours_fit_inclusive = ceil_0.1({fam.ROWS} / {fam.MEASURED_ROWS_PER_MINUTE} / 60 x {fam.GPU_MARGIN}) = ceil_0.1({fam.expected_wall_hours(fam.ROWS):.4f} x {fam.GPU_MARGIN}) = {fam.planned_gpu_hours()}",
            "one official complete slurp-slu-official-test score over the complete 3,010-row manifest, never sharded"]},
        "post_stratification_read": post, "authority_relpaths": [DECISIONS, fam.ALLOWANCE, V2_ALLOWANCE, fam.S2_PACKAGE + "/README.md", fam.SRC_PACKAGE + "/README.md", INSTRUMENT],
        "blockers_before_the_flip": [r["id"] + ": " + r["finding"] for r in reqs], "prohibitions": PROHIBITIONS}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    admission = {
        "_draft_note": "A DRAFT for root. It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1", "decision_id": fam.DECISION_ID, "status": "DRAFT-NOT-MINTED", "recorded_at_utc": None, "owner": "root", "coordinator": None,
        "eligible_run_ids": fam.eligible_run_ids(), "eligible_attempt_ids": fam.eligible_attempt_ids(),
        "cell_kind": "Test-sample SUCCESSOR-3 milestone read (owner ruling 301 A): the Thinking system lock arm, one attempt, ever.",
        "decision": "Fly SUCCESSOR3-THINKING-SYSTEM once on SLURP-TEST-SAMPLE-3010-V1; read cross-flight against the sealed successor-2 column, SLU-F1 primary, intent guard, no-harm.",
        "authorization_basis": f"{fam.OWNER_RULINGS}; the owner's signature of the successor-3 allowance; the coordinator's conversational report of the P3.1 read.",
        "first_contact_report": {"date": None, "arm": None, "note": "root fills this with the conversational report before minting"},
        "antecedents": {
            "allowance": {"path": fam.ALLOWANCE, "sha256": i["owner_allowance"]["sha256"], "note": "signed 2026-10-13, ruling 301 A"},
            "analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
            "owner_decisions": {"path": DECISIONS, "sha256": fam.sha_file(DECISIONS)},
            "packets_promotion_receipt": {"path": i["packet_receipt"], "sha256": i["packet_receipt_sha256"]},
            "preregistration": {"path": fam.PREREG, "sha256": None}, "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
            "readiness_readme": {"path": f"{pkg}/README.md", "sha256": None}, "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
            "registration_base_commit": commit},
        "budget": {**i["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True},
        "claim_boundary": "A milestone development read (owner decisions 28, 151, 301). No test claim, no superiority, generalisation, confirmatory or paper-scale claim. claim: no-harm.",
        "failure_policy": document["failure_policy"],
        "not_authorized": ["any contact before every prerequisite is cleared and the cell is flipped", "a second attempt of the run id, a recovery, a resume, a re-score or a re-read",
                           "a smoke, a twin, a re-flight of the sealed successor-2 run, the closure roster or the FULL test split", "--allow-output-change on the re-pin tool"],
        "population": {"closure_contact_authorized": False, "count": fam.ROWS, "roster": fam.ROSTER_ID, "split_identity_hash": i["split_identity_hash"], "split_role": fam.SPLIT_ROLE},
        "service": {"decoder_only": True, "expected_session_id": fam.SESSION, "model_fragment": fam.MODEL, "no_child_start_stop": True, "slots": 4, "slot_tokens": 24576},
        "registered_hashes": {"composed": {"composed_config": i["composed_config_hash"], "protocol": i["protocol_hash"]}, "note": "repin_cell.py recomputes them at the flip"}}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", admission)
    row_cells = draft_rows(i, commit, at, shas)
    lines = [fam.LEDGER_MARK + " (DRAFT, root countersignature pending)", "",
             f"Four unconsumed rows -- the Thinking packets pass (countersigned first, alone), the generation row, its live-phase-fit identity and the READ row -- for successor 3 of owner ruling 301 A. Package {pkg}. "
             "No row is countersigned and no row authorises a contact. No serving row: the Thinking session is the registered swap target think-budget-np4; its serving row is the coordinator's at the swap.",
             "", "| " + " | ".join(LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in LEDGER_COLUMNS) + " |"] + [reg.table_row(c) for c in row_cells]
    rows_text = "\n".join(lines) + "\n"
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows_text)
    shas["countersign-row-texts-v1.json"] = reg.wjson(root, f"{pkg}/countersign-row-texts-v1.json", countersign_texts(i))
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme_text(i, basis, proofs, pins, reqs))
    prereg = (f"# Successor 3: the Thinking system on the signed test sample, preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by script. Development numbers only.\n\n"
              f"Runs: `{fam.RUN}` / `{fam.FIT_RUN}`; packets `{fam.PACKETS_RUN}`; read `{fam.READ_RUN}`.\n\nThe decision rule, the declared DEV twin offset and its limitation are in `{pkg}/README.md` and "
              f"`{pkg}/protocol-registered-v1.json`.\n\n## The measurement declaration\n\n```json\n" + json.dumps({"stage3_measurement": block}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, fam.PREREG, prereg)
    result = {"package": pkg, "ids": i, "shas": shas}
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
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root to read and write")
    parser.add_argument("--append-ledger", action="store_true", help="append the DRAFT rows at the END of docs/exposure-ledger.md (idempotent)")
    parser.add_argument("--no-derive", action="store_true", help="do not re-derive the fragments first")
    parser.add_argument("--require-receipt", action="store_true", help="with derive: refuse unless the sample Thinking promotion receipt exists")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, append_ledger=args.append_ledger, derive=not args.no_derive, require_receipt=args.require_receipt)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
