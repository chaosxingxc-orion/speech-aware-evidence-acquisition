#!/usr/bin/env python3
"""Derive the P-SV-1 SEAL-ONLY completion cell of the aborted P-SV-1 arm (decision 58: script-derived).

The P-SV-1 arm ``SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1`` (attempt
``attempt-slurp-native-stage3-psv1-fold-b-generation-v1``, flight commit ``b9af3e58``) flew all 1,080 rows of TRAIN
Fold B (8,709 contacts, 25,428.7 s repeated speech; run_phases complete) and ABORTED AT THE SEAL at 14:19:36Z on the
seal invariant I7v: ``BundleError: ... perception-branch receipt is invalid: perception branch candidate_intent_ids
must be a non-empty ordered list of distinct non-empty strings (I7v)``. The runner sealed each branch note's intent
list verbatim, and 61 notes over 49 rows listed one intent twice (a-agree 21, b-top2contrast 17, t-twin 23). Fixed on
``fable/psvsealfix`` (``6fb31f8d3``, merged to master at ``0177f83fc``): receipt schema
``saea-perception-branch-arms-v2`` collapses duplicates (first occurrence kept) and records
``candidate_intent_ids_raw_count`` and ``note_parse_status`` (ok / duplicates-collapsed / empty / malformed); one
shared parser; the level-2 fold carries the presentation fields through; the resume replay re-derives the branch
block from the trace (``replay_perception_branch_block``); the bundle's I7v re-derives the note fields.

Every row is COMPLETE in the aborted attempt's trace (sha256 ``0c1edb20...``), so the recovery is a SEAL-ONLY
completion exactly as the E4-1 precedent (owner decision 194; ``scripts/flights/e4/derive_slurp_e4_sealonly_cell.py``,
``docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/``): the SAME run id under the new attempt
``attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only`` whose ``resume_from`` names the aborted attempt and
its trace; the union covers the roster, so ``core.flight.runtime`` sets ``is_seal_only`` -- zero model contacts, no
server, no slot, no lease. Owner decision 197 admits it.

Writes CONFIG and PACKAGE files only: ``configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1-resume.json``,
``configs/experiment/slurp-native-stage3-psv1-fold-b-v1-resume.json`` and the package
``docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/`` (its README and the preregistration note are
written by hand). It performs no contact, prepares no supply, mints no decision receipt, writes no ledger row and flips
nothing. Model-free: it composes the fragments with ``core.flight.repin.compute_cell_identity`` exactly as
``core.flight.cli`` does, to quote the pre-flip composed / protocol hashes the re-pin tool rewrites.

    PYTHONPATH=<tree>/src python -B scripts/flights/psv/derive_slurp_psv1_sealonly_cell.py \\
        --replay-json /tmp/psv1_replay_master.json --replay-commit <commit> --replay-at <utc>
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATE = "2026-09-29"
REGISTERED_AT = "2026-09-29T15:30:00.000000+00:00"
SOURCE_TREE = "studies/speech-aware-evidence-acquisition, master (single master writer, after the fable/psvsealfix merge)"
STATUS = "REGISTERED_BEFORE_CONTACT_SEAL_ONLY_OWNER_DECISION_197"

PARENT_RD = "docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1"
PARENT_EXP = "slurp-native-stage3-psv1-fold-b-v1"
PARENT_BASE = "slurp-native-stage3-psv1-fold-b-baseline-v1"

RD = "docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1"
PREREG = RD + "-preregistration.md"
EXP = "slurp-native-stage3-psv1-fold-b-v1-resume"
CELL = EXP
BASE = "slurp-native-stage3-psv1-fold-b-baseline-v1-resume"

RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1"
FIT_RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-FIT-V1"
READ_RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-BRANCH-READ-V1"
PROOF_RUN = "SAEA-SLURP-STAGE3-PSV1-FOLD-B-SEALONLY-REPLAY-PROOF-V1"
ABORTED = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1"
TRACE_SHA256 = "0c1edb20c37756ec8567fbba8edc56d8ff24ce3ea32b94bccad8c3667285d20a"
SO = "attempt-slurp-native-stage3-psv1-fold-b-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-psv1-fold-b-fit-v1-seal-only"
RESUME_FROM = {"attempt_id": ABORTED, "trace_sha256": TRACE_SHA256}
DEC_RELPATH = "coordination/slurp-stage3-psv1-fold-b-v1/root-admission-sealonly-v1.json"
DEC_ID = "slurp-stage3-psv1-fold-b-sealonly-admission-v1"

FLIGHT_COMMIT = "b9af3e58cbd9d4113d1bd92c3fff9e1bb88448f2"
FIX_COMMIT = "6fb31f8d3"
FIX_MERGE = "0177f83fc"
SUPPLY_OUTPUT_SHA256 = "81d6a712110882b70859778080d8d094483c67344da12f5aa69c97f961631dca"
ERROR = ("BundleError: outputs row <row id> (request flight-0183): perception-branch receipt is invalid: perception "
         "branch candidate_intent_ids must be a non-empty ordered list of distinct non-empty strings (I7v)")
ABORT = {
    "calls": 8709, "audio_seconds": 25428.697624999728, "samples_started": 1080, "complete_rows": 1080,
    "incomplete_rows": 0, "abort_at_utc": "2026-09-29T14:19:36Z",
    "notes_with_a_repeated_intent": 61, "rows_with_a_repeated_intent": 49,
    "notes_with_a_repeated_intent_by_branch": {"a-agree": 21, "b-top2contrast": 17, "t-twin": 23},
    "failing_stage": "FlightRuntime.seal -> bundle outputs validation (I7v, perception-branch receipt)",
    "lease_reconciliation": "coordination/slurp-stage3-psv1-fold-b-v1/flight-lock-reconciliation-20260929T143300Z.json",
}
REHEARSAL = {
    "where": "scratch copy of the attempt (/home/chao/scratch-psv-seal; replay-report.json), fable/psvsealfix code",
    "rows_complete": 1080, "rows_incomplete": 0, "rows_failing": 0,
    "delivered_column_sha256_prefix": "1f05aee5",
    "delivered_columns_identical_to_live_outputs": True,
    "b_top2contrast_presentation_outcome": {"rendered": 1035, "insufficient-pool-support": 42,
                                            "fewer-than-two-candidates": 3},
    "note": "the delivered columns rendered by the fixed seal stage are identical to the live outputs of the flight "
            "(delivered-column hash 1f05aee5..., identical on both sides); the presentation outcome of the "
            "b-top2contrast branch is a measured outcome, carried through the level-2 fold by the fix",
}
CAP_CALLS = 16200


def _load(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _dump(relpath: str, document) -> str:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha(relpath: str) -> str:
    return hashlib.sha256((REPO / relpath).read_bytes()).hexdigest()


def _head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short=9", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def _identity(experiment: str, cell_id: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.repin import compute_cell_identity  # noqa: PLC0415

    cells = [c for c in load_campaign_cells(REPO, experiment) if c.document["cell_id"] == cell_id]
    assert len(cells) == 1, (experiment, cell_id)
    return compute_cell_identity(REPO, experiment, cells[0])


def _note() -> str:
    return (
        "Cell P-SV-1 SEAL-ONLY COMPLETION (owner decision 197; the E4-1 seal-only shape of owner decision 194). The "
        f"arm attempt {ABORTED} of run {RUN} (flight commit {FLIGHT_COMMIT[:8]}) flew all 1,080 rows of TRAIN Fold B "
        "(8,709 contacts, 25,428.7 s repeated speech; run_phases complete) and ABORTED AT THE SEAL at 14:19:36Z on the "
        "seal invariant I7v (perception-branch receipt: candidate_intent_ids must be a non-empty ordered list of distinct "
        "non-empty strings); no run manifest, nothing read. Root cause (fable/psvsealfix, "
        f"{FIX_COMMIT}, merged at {FIX_MERGE}): the runner sealed each branch note's intent list verbatim, and 61 notes "
        "over 49 rows listed one intent twice (a-agree 21, b-top2contrast 17, t-twin 23); receipt schema "
        "saea-perception-branch-arms-v2 collapses duplicates (first occurrence kept) and records the raw count and a "
        "note_parse_status, and the resume replay re-derives the branch block from the trace. Every row is COMPLETE in "
        f"the aborted attempt's trace (sha256 {TRACE_SHA256}), so this attempt ({SO}, FIT identity {FSO}) declares "
        "resume_from that attempt and its trace; the union covers the 1,080-row roster, so core.flight.runtime sets "
        "is_seal_only: zero new model contacts, no server, no slot, no lease; core.flight.cli seal-only seals the "
        "manifest (I7r binds every kept row to the predecessor trace) and runs the one official finalize job. THIS IS "
        "P-SV-1's ONE root-diagnosed recovery re-registration; a second failure closes the cell."
    )


def _failure_policy() -> str:
    return (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, "
        "prompt, knowledge, branch, geometry or cap change, and no silent recovery. THIS registration IS the ONE "
        f"root-diagnosed recovery re-registration of run {RUN}, taken as a SEAL-ONLY completion of the aborted attempt "
        f"{ABORTED} (every row complete in its trace; zero model contacts), admitted by owner decision 197. A second "
        "failure CLOSES cell P-SV-1: no third registration. A partial manifest is never scored and never read."
    )


def derive_baseline() -> None:
    doc = _load(f"configs/baseline/{PARENT_BASE}.json")
    assert doc["native_contact_fit"]["run_id"] == FIT_RUN
    doc["native_contact_fit"]["attempt_id"] = FSO
    doc["what_this_is"] = (
        f"{_note()} This baseline is configs/baseline/{PARENT_BASE}.json byte for byte except "
        "native_contact_fit.attempt_id (a fresh seal-only FIT identity that records no contact) and this note. "
        "The parent's own note, verbatim: " + str(doc.get("what_this_is", ""))
    )
    _dump(f"configs/baseline/{BASE}.json", doc)


def _supply_requirement(requirements) -> dict:
    own = [r for r in requirements if r.get("kind") == "preparation"
           and r.get("relpath", "").startswith(f"prepared/{RUN}/phase-supply-v")]
    assert len(own) == 1
    return own[0]


def _agreement_requirement(requirements) -> dict:
    found = [r for r in requirements if r.get("kind") == "preparation" and "EXEMPLAR-AGREEMENT" in r.get("relpath", "")]
    assert len(found) == 1
    return found[0]


def derive_experiment() -> None:
    doc = _load(f"configs/experiment/{PARENT_EXP}.json")
    cell = doc["cells"][0]
    assert cell["run_id"] == RUN and cell["attempt_id"] == ABORTED
    requirements = cell["readiness"]["requirements"]
    supply = copy.deepcopy(_supply_requirement(requirements))
    supply["reason"] = (
        f"INHERITED from the P-SV-1 arm {RUN} (its own model-free first-phase Perception supply, minted at the P-SV-1 "
        f"flip with zero model, tokenizer, encoder, scorer or server contacts; output digest {SUPPLY_OUTPUT_SHA256}). "
        "EXPECT THIS PIN TO BE REBUILT rather than to verify as it stands: core.preparation.artifact_inputs binds the "
        "composed configuration, the cell and attempt identities and the rails implementation hashes (changed by the I7v "
        "fix), so scripts/flights/repin_cell.py rebuilds it model-free into the next phase-supply-v<N>.json under the same "
        "run id, ASSERTS the output unchanged and re-pins it in the same cycle; the branch-seed pin is verified or rebuilt "
        "the same way. --allow-output-change must NEVER be passed. The seal-only path never reads the supply (no contact "
        "is made); the pins are kept so the cell's identity stays the arm's."
    )
    new_cell = {}
    for key, value in cell.items():
        if key == "allowed_execution_stages":
            new_cell[key] = ["check", "prepare-supply", "seal-only"]
        elif key == "attempt_id":
            new_cell[key] = SO
        elif key == "baseline_fragment":
            new_cell[key] = BASE
        elif key == "cell_id":
            new_cell[key] = CELL
        elif key == "readiness":
            new_cell[key] = {
                "reason": (
                    f"{_note()} Registered before contact by the ops agent (Claude Opus 5.5, single master writer) on "
                    f"{DATE} under owner decision 197; root (act delegated by decision 197) countersigns the seal-only "
                    f"clauses on the arm's generation and FIT rows and the row {PROOF_RUN}, mints {DEC_RELPATH} "
                    f"(decision id {DEC_ID}) with scripts/flights/psv/psv1_sealonly_mint_receipt.py and flips with "
                    "scripts/flights/psv/psv1_sealonly_flip.sh."
                ),
                "requirements": [copy.deepcopy(_agreement_requirement(requirements)), supply],
                "state": "held",
            }
        elif key == "run_id":
            new_cell["resume_from"] = dict(RESUME_FROM)
            new_cell[key] = RUN
        else:
            new_cell[key] = copy.deepcopy(value)
    doc["cells"] = [new_cell]
    doc["date"] = DATE
    doc["failure_policy"] = _failure_policy()
    doc["fragment_kind"] = f"saea-{EXP}"
    doc["purpose"] = f"{_note()} THE PARENT'S PURPOSE, UNCHANGED: {doc['purpose']}"
    doc["generation_budget"]["definition"] = (
        "RUN-CUMULATIVE (owner decision 22): the seal-only attempt and its predecessor share one run id, so "
        "core.attempts.AttemptStore.prior_actual_usage sums every attempt file under the run id and the gate holds "
        f"that sum against planned_model_calls {CAP_CALLS:,} (invariants I3/I6). The predecessor durably spent 8,709 "
        "contacts and 25,428.7 s of repeated speech; this attempt flies 0 rows (seal-only), so the run-cumulative "
        f"total stays 8,709 of {CAP_CALLS:,}. " + doc["generation_budget"]["definition"]
    )
    _dump(f"configs/experiment/{EXP}.json", doc)


def _replay_proof(replay: dict, replay_commit: str, replay_at: str) -> dict:
    attempts = replay["attempts"]
    assert len(attempts) == 1 and attempts[0]["attempt_id"] == ABORTED and attempts[0]["trace_sha256"] == TRACE_SHA256
    a = attempts[0]
    return {
        "schema": "saea-resume-replay-proof-v1",
        "tool": f"scripts/analysis/replay_seal_consistency.py --experiment {PARENT_EXP} --run-id {RUN} "
                f"--predecessor {ABORTED}:{TRACE_SHA256}",
        "gate": "scripts/checks/resume_prelaunch_gate_check.py (via scripts/flights/batch/resume_prelaunch_gate.sh) on "
                "this cell, re-run by the chain and by the driver's prelaunch on the flight commit",
        "run_at_utc": replay_at,
        "predecessor_attempts": [{
            "attempt_id": ABORTED, "trace_sha256": TRACE_SHA256, "samples_started": a["samples_started"],
            "complete": a["complete"], "incomplete": a["incomplete"], "rows_checked": a["rows_checked"],
            "rows_failing": a["rows_failing"],
            "rows_with_perception_branches": a.get("rows_with_perception_branches"),
            "rows_with_deliver_normaliser": a.get("rows_with_deliver_normaliser"),
            "perception_branch_note_parse_status": a.get("perception_branch_note_parse_status"),
        }],
        "rows_checked": replay["rows_checked_total"],
        "rows_failing": replay["rows_failing_total"],
        "sealed_twice": replay["union"]["sealed_twice"],
        "union_complete_rows": replay["union"]["complete_rows"],
        "checker_sha256": _sha("scripts/analysis/replay_seal_consistency.py"),
        "resume_py_sha256": replay["resume_py_sha256"],
        "code_commit": replay_commit,
        "model_contacts": replay["model_contacts"],
        "note": "Model-free and read-only over the REAL attempt trace: every complete row rendered through the real "
                "seal stage under the merged I7v fix (receipt schema saea-perception-branch-arms-v2) and re-checked "
                "against I7 / I7n / I7g / I7v one row at a time; no row fails and no sample is sealed twice. The "
                "driver's prelaunch replay gate re-runs the same check at launch on the flight commit.",
    }


def _plan(parent_plan: str, identity, *, kind: str, protocol_sha: str, route: str, extra: dict) -> dict:
    doc = _load(f"{PARENT_RD}/{parent_plan}")
    doc["cell"] = CELL
    doc["experiment"] = EXP
    doc["composed_config_hash"] = identity.config_hash
    doc["execution_plan"]["protocol_hash"] = identity.protocol_hash
    doc["execution_plan"]["run_id"] = RUN if kind == "generation" else FIT_RUN
    doc["execution_plan"]["attempt_id"] = SO if kind == "generation" else FSO
    doc["protocol_document"] = {"relpath": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha}
    pin = identity.prepared_phase_supply
    doc["prepared_phase_supply"] = {
        "note": "INHERITED pin; the flip rebuilds it under the same run id and asserts the output unchanged "
                "(never --allow-output-change). The seal-only path never reads it.",
        "relpath": pin.relpath if pin else None,
        "sha256": pin.sha256 if pin else None,
        "output_sha256": SUPPLY_OUTPUT_SHA256,
    }
    doc["execution_route"] = route
    doc["preparation_base_commit"] = _head()
    doc["registered_at_utc"] = REGISTERED_AT
    doc["source_tree"] = SOURCE_TREE
    doc["status"] = STATUS
    doc.update(extra)
    return doc


def _registration() -> dict:
    return {
        "registered_at_utc": REGISTERED_AT, "source_tree": SOURCE_TREE,
        "owner_decision": "197 (given 2026-09-29: seal-only completion of P-SV-1 after the I7v fix)",
        "decision_receipt": DEC_RELPATH, "decision_id": DEC_ID,
    }


def derive_package(replay: dict, replay_commit: str, replay_at: str) -> None:
    ident = _identity(EXP, CELL)
    proof = _replay_proof(replay, replay_commit, replay_at)
    assert (proof["rows_checked"], proof["rows_failing"], proof["sealed_twice"]) == (1080, 0, 0), proof
    budget = {
        "kept_rows": 1080, "flown_rows": 0, "kept_from": {ABORTED: 1080}, "seal_only": True,
        "flown_worst_case_calls": 0, "run_cumulative_actual_calls": ABORT["calls"],
        "run_cumulative_actual_audio_seconds": round(ABORT["audio_seconds"], 1),
        "run_cumulative_actual_breakdown_calls": {ABORTED: ABORT["calls"]},
        "run_cumulative_worst_case_calls": ABORT["calls"], "cap_calls": CAP_CALLS,
        "headroom_calls": CAP_CALLS - ABORT["calls"],
    }
    parent_protocol = f"{PARENT_RD}/protocol-registered-v1.json"
    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-psv1-fold-b-sealonly-protocol-v1",
        "status": STATUS,
        "registered_at_utc": REGISTERED_AT,
        "source_tree": SOURCE_TREE,
        "study_commit_at_registration": _head(),
        "parent_protocol": {"relpath": parent_protocol, "sha256": _sha(parent_protocol),
                            "rule": "Everything the parent fixes -- the question, the branches, the level, the read, "
                                    "the bar (the twin null), the prohibitions -- stands unchanged and is not "
                                    "re-litigated."},
        "abort": {"run_id": RUN, "attempt_id": ABORTED, "flight_commit": FLIGHT_COMMIT, "error": ERROR,
                  "trace_sha256": TRACE_SHA256, "counts": ABORT,
                  "root_cause": "the runner sealed each Perception branch note's candidate intent list verbatim; 61 "
                                "notes over 49 rows listed one intent twice, and I7v requires a list of distinct "
                                "intents, so the seal refused rows whose branch notes were legal measured outcomes",
                  "fix": {"commit": FIX_COMMIT, "merge": f"fable/psvsealfix merged to master at {FIX_MERGE}",
                          "files": ["src/speech_aware_evidence_acquisition/rails/native_episode_receipt.py",
                                    "src/speech_aware_evidence_acquisition/rails/runner.py",
                                    "src/speech_aware_evidence_acquisition/rails/supply_variants.py",
                                    "src/speech_aware_evidence_acquisition/core/bundle/outputs.py",
                                    "src/speech_aware_evidence_acquisition/core/flight/resume.py",
                                    "scripts/analysis/replay_seal_consistency.py",
                                    "scripts/analysis/slurp_perception_branch_read.py"],
                          "rule": "receipt schema saea-perception-branch-arms-v2: candidate_intent_ids collapses "
                                  "duplicates (first occurrence kept), candidate_intent_ids_raw_count records the raw "
                                  "length, note_parse_status is ok / duplicates-collapsed / empty / malformed; one "
                                  "shared parser for runner, resume replay and bundle; the level-2 fold carries "
                                  "presentation_skip_reason, contrast_block_sha256 and min_candidates_met; the read "
                                  "treats empty / malformed as gold-absent"}},
        "rehearsal": REHEARSAL,
        "seal_only_completion": {
            "mechanism": "resume_from the aborted attempt; every row complete in its trace, so is_seal_only; "
                         "core.flight.cli seal-only seals the 1,080-row manifest under I7r and runs the one official "
                         "finalize job; zero model contacts, no server, no slot, no lease",
            "resume_replay_proof": proof,
        },
        "recovery_counter": "P-SV-1's ONE root-diagnosed recovery re-registration; a second failure closes the cell.",
        "cells": {"seal-only": {
            "cell": CELL, "experiment": EXP, "run_id": RUN, "attempt_id": SO, "fit_run_id": FIT_RUN,
            "fit_attempt_id": FSO, "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
            "resume_from": RESUME_FROM}},
        "claim_ceiling": "nominated (unchanged)",
        "rows": {"kept": 1080, "flown": 0},
        "budget": budget,
    }
    protocol_sha = _dump(f"{RD}/protocol-registered-v1.json", protocol)
    route = (f"core.flight.cli seal-only on the resume cell (--experiment {EXP} --cell {CELL}), through the batch driver "
             "as a kind=seal-only step (scripts/flights/psv/batch_chain_psv1_sealonly.sh): preflight's gates, then "
             "zero-work preprocess / serve / run_phases (no packet promotion, no server, no slot, no lease), the seal of "
             "the 1,080-row manifest and the one official finalize job. P-SV-1 has no A/A cell (the twin branch is the "
             "null, inside every row).")
    _dump(f"{RD}/generation-plan-registered-v1.json", _plan(
        "generation-plan-registered-v1.json", ident, kind="generation", protocol_sha=protocol_sha, route=route,
        extra={"resume_from": dict(RESUME_FROM), "resume_budget": budget, "resume_replay_proof": proof,
               "seal_only_registration": _registration()}))
    _dump(f"{RD}/fit-plan-registered-v1.json", _plan(
        "fit-plan-registered-v1.json", ident, kind="fit", protocol_sha=protocol_sha,
        route=("The shared core.flight.cli FIT path under this cell's own native_contact_fit ids (the SAME FIT run id, a "
               "new attempt). SEAL-ONLY: the seal-only attempt never builds the native contact FIT gate (run_phases is a "
               f"zero-work receipt), so this FIT identity records no contact; it is fresh ({FSO}, unused on the data "
               "root at registration) because validate_native_contact_fit_config requires the block and no FIT attempt "
               "id that already holds evidence is ever reused."),
        extra={"seal_only_registration": _registration()}))
    recipe = _load(f"{PARENT_RD}/analysis-recipe-v1.json")
    recipe["recipe_id"] = "slurp-stage3-psv1-fold-b-sealonly-branch-analysis-v1"
    recipe["registered_at_utc"] = REGISTERED_AT
    for arm in recipe["arms"].values():
        if isinstance(arm, dict) and arm.get("attempt_id") == ABORTED:
            arm["attempt_id"] = SO
    recipe["parent_recipe"] = {"relpath": f"{PARENT_RD}/analysis-recipe-v1.json",
                               "sha256": _sha(f"{PARENT_RD}/analysis-recipe-v1.json"),
                               "rule": "unchanged except the sealed attempt id and the reading rule below"}
    recipe["recovery_reading_rule"] = (
        f"Every branch column (a-agree delivering, b-top2contrast, t-twin) is read from the seal-only attempt {SO}'s "
        f"sealed manifest: all 1,080 rows kept from {ABORTED} under I7r custody, 0 flown. The manifest's "
        f"predecessor_attempt block must name trace {TRACE_SHA256}; refuse otherwise. The perception-branch receipts "
        "are the schema-v2 ones the fixed resume replay re-derives from that trace; a note whose note_parse_status is "
        "empty or malformed counts as gold-absent; the read is otherwise exactly as the parent recipe fixes it."
    )
    recipe["read_run_id_note"] = (f"The READ run id {READ_RUN} and its exposure-ledger row are the parent's, UNCHANGED: "
                                  "the P-SV-1 branch read is one read whichever attempt seals the arm.")
    recipe_sha = _dump(f"{RD}/analysis-recipe-v1.json", recipe)
    parent_facts = _load(f"{PARENT_RD}/registered-facts-v1.json")
    measurement = copy.deepcopy(parent_facts["stage3_measurement"][RUN])
    measurement["primary_metric_key"] = "intent"
    facts = {
        "schema": "saea-registered-facts-v1",
        "registered_at_utc": REGISTERED_AT,
        "study_commit_at_registration": _head(),
        "parent_registered_facts": f"{PARENT_RD}/registered-facts-v1.json",
        "_note": "The P-SV-1 arm's stage3_measurement block, copied from the parent package (same run id) with "
                 "primary_metric_key 'intent' added (owner decision 190); the seal-only completion changes no other "
                 "measurement fact. Claim ceiling nominated.",
        "stage3_measurement": {RUN: measurement},
        "seal_only": {"cell": CELL, "attempt_id": SO, "fit_attempt_id": FSO, "resume_from": RESUME_FROM,
                      "abort": ABORT, "rehearsal": REHEARSAL, "resume_replay_proof": proof,
                      "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash},
    }
    facts_sha = _dump(f"{RD}/registered-facts-v1.json", facts)
    parent_draft = _load(f"{PARENT_RD}/root-admission-draft-v1.json")
    draft = copy.deepcopy(parent_draft)
    draft["_draft_note"] = ("A DRAFT for root to mint on the data root with "
                            "scripts/flights/psv/psv1_sealonly_mint_receipt.py (status decided, recorded_at_utc stamped, "
                            "antecedents re-hashed, never overwrites) under owner decision 197.")
    draft["decision_id"] = DEC_ID
    draft["eligible_run_ids"] = [RUN, FIT_RUN]
    draft["eligible_attempt_ids"] = [SO]
    draft["fit_attempt_ids"] = {FIT_RUN: FSO}
    draft["resume_from"] = dict(RESUME_FROM)
    draft["resume_replay_proof"] = proof
    draft["decision"] = (
        f"Seal the P-SV-1 arm {RUN} as the SEAL-ONLY completion of its one recovery: attempt {SO} keeps all 1,080 rows "
        f"of the aborted attempt {ABORTED} (trace {TRACE_SHA256[:8]}...) with ZERO new model contacts through "
        f"core.flight.cli seal-only, finalizes it with the one official score job, and reads it by the unchanged READ "
        f"row {READ_RUN}.")
    draft["cell_kind"] = (
        f"P-SV-1 SEAL-ONLY COMPLETION: a new attempt {SO} (FIT attempt {FSO}, records no contact) under the SAME run id "
        f"{RUN}, resume_from [{ABORTED}]; the union covers the 1,080-row roster, so nothing is flown. Claim ceiling "
        "'nominated', unchanged.")
    draft["authorization_basis"] = (
        "Owner decision 197 (2026-09-29, verbatim: agreed): seal-only completion of the aborted P-SV-1 arm after the "
        f"I7v fix ({FIX_COMMIT}, merged at {FIX_MERGE}), on the offline replay proof recorded as resume_replay_proof "
        "(1,080 rows checked, 0 failing, 0 sealed twice), the same shape as owner decision 194 (E4-1). Owner decision 22 "
        "(resume-recovery) stands; the parent authorization basis stands: " + str(parent_draft["authorization_basis"]))
    draft["retry_basis"] = (
        f"The P-SV-1 arm flew all 1,080 rows (8,709 calls, 25,428.7 s audio) and ABORTED at the seal on I7v; root "
        "cause named to a component (the runner sealed branch-note intent lists verbatim; 61 notes over 49 rows repeated "
        f"an intent) and fixed at {FIX_COMMIT}. Its 1,080 rows are complete in its trace; the seal-only completion keeps "
        "them and flies nothing. The aborted attempt stays charged run-cumulatively (8,709 calls of 16,200).")
    budget_block = draft.setdefault("budget", {})
    budget_block.pop("smoke", None)
    budget_block["resume"] = dict(budget, note="plan budgets are run-cumulative; the seal-only completion adds none")
    draft["not_authorized"] = [item for item in draft.get("not_authorized", [])] + [
        f"flying any row of {RUN} again (the seal-only completion makes zero model contacts)",
        "any core.flight.cli worker or campaign run of the resume cell (it allows check, prepare-supply and seal-only only)",
        f"writing, moving or compressing anything under the aborted attempt's directory {ABORTED}",
    ]
    antecedents = draft.setdefault("antecedents", {})
    antecedents["parent_registration_draft"] = {"path": f"{PARENT_RD}/root-admission-draft-v1.json",
                                                "sha256": _sha(f"{PARENT_RD}/root-admission-draft-v1.json")}
    antecedents["parent_decision_receipt"] = {
        "relpath": "coordination/slurp-stage3-psv1-fold-b-v1/root-admission-v1.json",
        "decision_id": "slurp-stage3-psv1-fold-b-admission-v1",
        "status": "stands; it admitted the original attempt, which aborted at the seal"}
    antecedents["sealonly_protocol"] = {"path": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha}
    antecedents["sealonly_analysis_recipe"] = {"path": f"{RD}/analysis-recipe-v1.json", "sha256": recipe_sha}
    antecedents["sealonly_registered_facts"] = {"path": f"{RD}/registered-facts-v1.json", "sha256": facts_sha}
    antecedents["sealonly_preregistration"] = {"path": PREREG, "sha256": None}
    antecedents["sealonly_readme"] = {"path": f"{RD}/README.md", "sha256": None}
    antecedents["derive_script"] = {"path": "scripts/flights/psv/derive_slurp_psv1_sealonly_cell.py",
                                    "sha256": _sha("scripts/flights/psv/derive_slurp_psv1_sealonly_cell.py")}
    antecedents["registration_base_commit"] = _head()
    draft["registered_hashes"] = {"seal-only": {"composed_config": ident.config_hash, "protocol": ident.protocol_hash}}
    population = draft.setdefault("population", {})
    if isinstance(population, dict):
        population["partition"] = "TRAIN Fold B 1,080, unchanged; 1,080 kept from the aborted attempt, 0 flown"
    draft["status"] = "DRAFT-NOT-MINTED"
    draft["recorded_at_utc"] = None
    _dump(f"{RD}/root-admission-sealonly-draft-v1.json", draft)
    print(json.dumps({"cell": CELL, "experiment": EXP, "attempt_id": SO, "fit_attempt_id": FSO,
                      "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
                      "prepared_phase_supply": ident.prepared_phase_supply.relpath if ident.prepared_phase_supply else None,
                      "protocol_sha": protocol_sha, "replay": [proof["rows_checked"], proof["rows_failing"],
                                                               proof["sealed_twice"]]}, indent=1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-json", required=True, type=Path)
    parser.add_argument("--replay-commit", required=True)
    parser.add_argument("--replay-at", required=True)
    args = parser.parse_args(argv)
    replay = json.loads(args.replay_json.read_text(encoding="utf-8"))
    derive_baseline()
    derive_experiment()
    derive_package(replay, args.replay_commit, args.replay_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
