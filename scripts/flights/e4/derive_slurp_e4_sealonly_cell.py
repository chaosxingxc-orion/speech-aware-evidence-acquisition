#!/usr/bin/env python3
"""Derive the HELD seal-only completion cell of the aborted E4-1 arm (decision 58: script-derived).

The E4-1 arm ``SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1`` (attempt
``attempt-slurp-native-stage3-relisten-fold-a-generation-v1``, flight commit ``e9777e18``) flew all
1,080 rows (6,304 contacts, 18,730.5 s repeated speech; run_phases complete) and ABORTED AT THE SEAL
with ``FlightRuntimeError: finite source is not the last actual sample contact``: on 8 of the 10
finite-completion rows (deliver-latest-or-abstain, item E13) the post-accept relisten stage (owner
decision 185) spent its blind / forced-choice contacts AFTER the interrupted source contact, and the
seal compared the source with the sample's last recorded contact. Fixed on ``fable/e4sealfix``
(``b286d8974``, merged to master): the finite source must be the last contact that can move delivery,
and only the row's own ``saea-relisten-v1`` receipt contacts may follow it; the resume replay
re-derives the relisten receipt from the trace.

Every row is COMPLETE in the aborted attempt's trace (sha256 ``966613e4...``), so the recovery is a
SEAL-ONLY completion exactly as the COMP-1 precedent (owner decision 189 option A; its files are
``configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json`` and
``docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/``): the SAME run id under the
new attempt ``attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only`` whose
``resume_from`` names the aborted attempt and its trace; the union covers the roster, so
``core.flight.runtime`` sets ``is_seal_only`` -- zero model contacts, no server, no slot, no lease.
Whether it is admitted is owner decision 194 (pending); the cell is written HELD.

Writes CONFIG and PACKAGE files only: ``configs/baseline/slurp-native-stage3-relisten-fold-a-baseline-v1-resume.json``,
``configs/experiment/slurp-native-stage3-relisten-fold-a-v1-resume.json``, the package
``docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/`` and its preregistration
note. It performs no contact, prepares no supply, mints no decision receipt, writes no ledger row and
flips nothing. Model-free: it composes the fragments with ``core.flight.repin.compute_cell_identity``
exactly as ``core.flight.cli`` does, to quote the pre-flip composed / protocol hashes the re-pin tool
rewrites.

    PYTHONPATH=<tree>/src python -B scripts/flights/e4/derive_slurp_e4_sealonly_cell.py \\
        --replay-json /tmp/e4_replay_master.json --replay-commit <commit>
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
REGISTERED_AT = "2026-09-29T12:30:00.000000+00:00"
SOURCE_TREE = "studies/speech-aware-evidence-acquisition, master (single master writer, after the fable/e4sealfix merge)"
STATUS = "REGISTERED_BEFORE_CONTACT_SEAL_ONLY_HELD_AWAITING_OWNER_DECISION_194"

PARENT_RD = "docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1"
PARENT_EXP = "slurp-native-stage3-relisten-fold-a-v1"
PARENT_BASE = "slurp-native-stage3-relisten-fold-a-baseline-v1"

RD = "docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1"
PREREG = RD + "-preregistration.md"
EXP = "slurp-native-stage3-relisten-fold-a-v1-resume"
CELL = EXP
BASE = "slurp-native-stage3-relisten-fold-a-baseline-v1-resume"

RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1"
FIT_RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1"
READ_RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1"
PROOF_RUN = "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SEALONLY-REPLAY-PROOF-V1"
ABORTED = "attempt-slurp-native-stage3-relisten-fold-a-generation-v1"
TRACE_SHA256 = "966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6"
SO = "attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only"
FSO = "attempt-slurp-native-stage3-relisten-fold-a-fit-v1-seal-only"
RESUME_FROM = {"attempt_id": ABORTED, "trace_sha256": TRACE_SHA256}
DEC_RELPATH = "coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json"
DEC_ID = "slurp-stage3-relisten-fold-a-sealonly-admission-v1"

FLIGHT_COMMIT = "e9777e182dce466c9c05a1e5651569dd833e8666"
FIX_COMMIT = "b286d8974"
ERROR = "FlightRuntimeError: finite source is not the last actual sample contact"
ABORT = {
    "calls": 6304, "audio_seconds": 18730.52300000018, "samples_started": 1080, "complete_rows": 1080,
    "incomplete_rows": 0, "finite_completion_rows": 10, "finite_rows_with_relisten_after_source": 8,
    "run_phases": "complete 2026-09-29T09:47:07Z - 11:40:06Z", "failing_stage":
        "FlightRuntime.seal -> _merged_canonical_rows -> _canonical_output_rows",
}
REHEARSAL = {
    "where": "scratch copy of the attempt (/home/chao/scratch-e4-seal; receipt rehearsal.json), fable/e4sealfix code",
    "rows_sealed": 1080, "rows_abstained": 0, "rows_with_relisten_receipt": 1080,
    "relisten_contacts_used": 1889, "result_contact_count_total": 6304, "trace_contacts_total": 6304,
    "delivered_text_vs_live_runtime_use_mismatch": 0,
    "delivered_column_sha256_sealed": "81e977169486cd157e24280a7a65cd338c01217fb8ec9658a4eac0aa25277263",
    "delivered_column_sha256_live_trace": "81e977169486cd157e24280a7a65cd338c01217fb8ec9658a4eac0aa25277263",
    "note": "the delivered column rendered by the fixed seal stage is byte-identical to the live runtime-use custody of the flight",
}
CAP_CALLS = 18360


def _load(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _dump(relpath: str, document) -> str:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_text(relpath: str, text: str) -> str:
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
        "Cell E4-1 SEAL-ONLY COMPLETION (owner decision 194, PENDING; the COMP-1 seal-only shape of owner decision "
        f"189), HELD. The arm attempt {ABORTED} of run {RUN} (flight commit {FLIGHT_COMMIT[:8]}) flew all 1,080 rows "
        "(6,304 contacts, 18,730.5 s repeated speech; run_phases complete 09:47:07Z-11:40:06Z) and ABORTED AT THE SEAL "
        f"with {ERROR} (FlightRuntime.seal -> _merged_canonical_rows -> _canonical_output_rows); no run manifest, "
        f"nothing read. Root cause (fable/e4sealfix, {FIX_COMMIT}, merged): on 8 of the 10 finite-completion rows "
        "(deliver-latest-or-abstain, item E13) the post-accept relisten stage (owner decision 185) spent its blind / "
        "forced-choice contacts after the interrupted source contact, and the seal compared the source with the sample's "
        "last recorded contact instead of the last contact that can move delivery; the fix admits exactly the row's own "
        "saea-relisten-v1 receipt contacts after the source, and the resume replay re-derives the relisten receipt from "
        f"the trace. Every row is COMPLETE in the aborted attempt's trace (sha256 {TRACE_SHA256}), so this attempt "
        f"({SO}, FIT identity {FSO}) declares resume_from that attempt and its trace; the union covers the 1,080-row "
        "roster, so core.flight.runtime sets is_seal_only: zero new model contacts, no server, no slot, no lease; "
        "core.flight.cli seal-only seals the manifest (I7r binds every kept row to the predecessor trace) and runs the "
        "one official finalize job. THIS IS E4-1's ONE root-diagnosed recovery re-registration; a second failure "
        "closes the cell."
    )


def _failure_policy() -> str:
    return (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, role-graph, "
        "prompt, knowledge, geometry or cap change, and no silent recovery. THIS registration IS the ONE "
        f"root-diagnosed recovery re-registration of run {RUN}, taken as a SEAL-ONLY completion of the aborted attempt "
        f"{ABORTED} (every row complete in its trace; zero model contacts) IF the owner admits it (decision 194). A "
        "second failure CLOSES cell E4-1: no third registration. A partial manifest is never scored and never read."
    )


def derive_baseline() -> None:
    doc = _load(f"configs/baseline/{PARENT_BASE}.json")
    assert doc["native_contact_fit"]["run_id"] == FIT_RUN
    doc["native_contact_fit"]["attempt_id"] = FSO
    doc["what_this_is"] = (
        f"{_note()} This baseline is configs/baseline/{PARENT_BASE}.json byte for byte except "
        "native_contact_fit.attempt_id (a fresh seal-only FIT identity that records no contact) and this note. "
        "The parent's own note, verbatim: " + doc["what_this_is"]
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
        f"INHERITED from the E4-1 arm {RUN} (its own model-free first-phase Perception supply, minted at the E4-1 flip "
        "with zero model, tokenizer, encoder, scorer or server contacts; output digest "
        "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae, the AGREE arm's). EXPECT THIS PIN TO BE "
        "REBUILT rather than to verify as it stands: core.preparation.artifact_inputs binds the composed configuration, "
        "the cell and attempt identities and runtime.py's whole-file hash (changed by the seal fix), so "
        "scripts/flights/repin_cell.py rebuilds it model-free into the next phase-supply-v<N>.json under the same run id, "
        "ASSERTS the output unchanged and re-pins it in the same cycle. --allow-output-change must NEVER be passed. The "
        "seal-only path never reads the supply (no contact is made); the pin is kept so the cell's identity stays the arm's."
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
                    f"{_note()} Registered before contact by the E4-1 seal-only registration agent (Claude Opus 5.5) on "
                    f"{DATE}; HELD pending owner decision 194. The coordinator, once the owner admits the seal-only "
                    "completion, countersigns the DRAFT seal-only clauses on the arm's generation and FIT rows and the "
                    f"DRAFT row {PROOF_RUN}, mints {DEC_RELPATH} (decision id {DEC_ID}) with "
                    "scripts/flights/e4/e4_sealonly_mint_receipt.py and flips with scripts/flights/e4/e4_sealonly_flip.sh. "
                    "Nothing here authorises a seal, a readiness flip or an admission entry."
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
        f"that sum against planned_model_calls {CAP_CALLS:,} (invariants I3/I6). The predecessor durably spent 6,304 "
        "contacts and 18,730.5 s of repeated speech; this attempt flies 0 rows (seal-only), so the run-cumulative "
        f"total stays 6,304 of {CAP_CALLS:,}. " + doc["generation_budget"]["definition"]
    )
    _dump(f"configs/experiment/{EXP}.json", doc)


def _replay_proof(replay: dict, replay_commit: str) -> dict:
    attempts = replay["attempts"]
    assert len(attempts) == 1 and attempts[0]["attempt_id"] == ABORTED and attempts[0]["trace_sha256"] == TRACE_SHA256
    a = attempts[0]
    return {
        "schema": "saea-resume-replay-proof-v1",
        "tool": f"scripts/analysis/replay_seal_consistency.py --experiment {PARENT_EXP} --run-id {RUN} "
                f"--predecessor {ABORTED}:{TRACE_SHA256}",
        "gate": "scripts/checks/resume_prelaunch_gate_check.py (via scripts/flights/batch/resume_prelaunch_gate.sh) on "
                "this cell: re-run at registration, see the package README",
        "run_at_utc": "2026-09-29T12:25:14Z",
        "predecessor_attempts": [{
            "attempt_id": ABORTED, "trace_sha256": TRACE_SHA256, "samples_started": a["samples_started"],
            "complete": a["complete"], "incomplete": a["incomplete"], "rows_checked": a["rows_checked"],
            "rows_failing": a["rows_failing"], "rows_with_relisten_receipt": a.get("rows_with_relisten_receipt"),
            "rows_with_deliver_normaliser": a.get("rows_with_deliver_normaliser"),
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
                "FlightRuntime._canonical_output_rows seal stage (the fixed finite-source rule) and re-checked against "
                "I7 / I7n / I7g / I7l one row at a time; no row fails and no sample is sealed twice. The driver's "
                "prelaunch replay gate re-runs the same check at launch on the flight commit.",
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
    doc["prepared_phase_supply"] = {
        "note": "INHERITED pin; the flip rebuilds it under the same run id and asserts the output unchanged "
                "(never --allow-output-change). The seal-only path never reads it.",
        "relpath": identity.prepared_phase_supply.relpath,
        "sha256": identity.prepared_phase_supply.sha256,
        "output_sha256": "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae",
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
        "owner_decision": "194 (pending; the same shape as 189 option A)",
        "decision_receipt": DEC_RELPATH, "decision_id": DEC_ID,
    }


def derive_package(replay: dict, replay_commit: str) -> None:
    ident = _identity(EXP, CELL)
    proof = _replay_proof(replay, replay_commit)
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
        "protocol_id": "slurp-stage3-relisten-fold-a-sealonly-protocol-v1",
        "status": STATUS,
        "registered_at_utc": REGISTERED_AT,
        "source_tree": SOURCE_TREE,
        "study_commit_at_registration": _head(),
        "parent_protocol": {"relpath": parent_protocol, "sha256": _sha(parent_protocol),
                            "rule": "Everything the parent fixes -- the question, the one factor, the two shadow columns, "
                                    "the decision rule, the bar, the prohibitions -- stands unchanged and is not "
                                    "re-litigated."},
        "abort": {"run_id": RUN, "attempt_id": ABORTED, "flight_commit": FLIGHT_COMMIT, "error": ERROR,
                  "trace_sha256": TRACE_SHA256, "counts": ABORT,
                  "root_cause": "the seal's finite-completion rule compared the interrupted source contact with the "
                                "sample's LAST recorded contact; on 8 of the 10 finite rows the post-accept relisten "
                                "stage (shadow; it never moves delivery) had spent its contacts after the source, so "
                                "the rule refused a legal row",
                  "fix": {"commit": FIX_COMMIT, "merge": "fable/e4sealfix merged to master",
                          "files": ["src/speech_aware_evidence_acquisition/core/flight/runtime.py",
                                    "src/speech_aware_evidence_acquisition/rails/relisten.py",
                                    "src/speech_aware_evidence_acquisition/core/flight/resume.py",
                                    "scripts/analysis/replay_seal_consistency.py"],
                          "rule": "the finite source must be the last contact that can move delivery; exactly the row's "
                                  "own saea-relisten-v1 receipt contacts, and nothing else, may follow it, and every one "
                                  "of them must follow it; without a receipt the pre-fix check is unchanged"}},
        "rehearsal": REHEARSAL,
        "seal_only_completion": {
            "mechanism": "resume_from the aborted attempt; every row complete in its trace, so is_seal_only; "
                         "core.flight.cli seal-only seals the 1,080-row manifest under I7r and runs the one official "
                         "finalize job; zero model contacts, no server, no slot, no lease",
            "resume_replay_proof": proof,
        },
        "recovery_counter": "E4-1's ONE root-diagnosed recovery re-registration; a second failure closes the cell.",
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
             "as a kind=seal-only step (scripts/flights/e4/batch_chain_e4_sealonly.sh): preflight's gates, then zero-work "
             "preprocess / serve / run_phases (no packet promotion, no server, no slot, no lease), the seal of the "
             "1,080-row manifest and the one official finalize job. E4-1 has no A/A cell.")
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
    recipe["recipe_id"] = "slurp-stage3-relisten-fold-a-sealonly-column-analysis-v1"
    recipe["registered_at_utc"] = REGISTERED_AT
    for arm in ("delivered", "shadow_a", "shadow_b"):
        recipe["arms"][arm]["attempt_id"] = SO
    recipe["parent_recipe"] = {"relpath": f"{PARENT_RD}/analysis-recipe-v1.json",
                               "sha256": _sha(f"{PARENT_RD}/analysis-recipe-v1.json"),
                               "rule": "unchanged except the sealed attempt id and the reading rule below"}
    recipe["recovery_reading_rule"] = (
        f"The delivered column and both shadow columns are read from the seal-only attempt {SO}'s sealed manifest: all "
        f"1,080 rows kept from {ABORTED} under I7r custody, 0 flown. The manifest's predecessor_attempt block must name "
        f"trace {TRACE_SHA256}; refuse otherwise. The relisten receipts are the ones the fixed resume replay re-derives "
        "from that trace; the read is paired over all 1,080 rows exactly as the parent recipe fixes it."
    )
    recipe["read_run_id_note"] = (f"The READ run id {READ_RUN} and its exposure-ledger row are the parent's, UNCHANGED: "
                                  "the E4-1 column read is one read whichever attempt seals the arm.")
    recipe_sha = _dump(f"{RD}/analysis-recipe-v1.json", recipe)
    parent_facts = _load(f"{PARENT_RD}/registered-facts-v1.json")
    facts = {
        "schema": "saea-registered-facts-v1",
        "registered_at_utc": REGISTERED_AT,
        "study_commit_at_registration": _head(),
        "parent_registered_facts": f"{PARENT_RD}/registered-facts-v1.json",
        "_note": "The E4-1 arm's stage3_measurement block, copied verbatim (same run id); the seal-only completion "
                 "changes no measurement fact. Claim ceiling nominated.",
        "stage3_measurement": {RUN: copy.deepcopy(parent_facts["stage3_measurement"][RUN])},
        "seal_only": {"cell": CELL, "attempt_id": SO, "fit_attempt_id": FSO, "resume_from": RESUME_FROM,
                      "abort": ABORT, "rehearsal": REHEARSAL, "resume_replay_proof": proof,
                      "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash},
    }
    facts_sha = _dump(f"{RD}/registered-facts-v1.json", facts)
    parent_draft = _load(f"{PARENT_RD}/root-admission-draft-v1.json")
    draft = copy.deepcopy(parent_draft)
    draft["_draft_note"] = ("A DRAFT for root to mint on the data root with scripts/flights/e4/e4_sealonly_mint_receipt.py "
                            "(status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites) ONLY after "
                            "owner decision 194 admits the seal-only completion. It authorises nothing while its status is "
                            "not 'decided'.")
    draft["decision_id"] = DEC_ID
    draft["eligible_run_ids"] = [RUN, FIT_RUN]
    draft["eligible_attempt_ids"] = [SO]
    draft["fit_attempt_ids"] = {FIT_RUN: FSO}
    draft["resume_from"] = dict(RESUME_FROM)
    draft["resume_replay_proof"] = proof
    draft["decision"] = (
        f"Seal the E4-1 arm {RUN} as the SEAL-ONLY completion of its one recovery: attempt {SO} keeps all 1,080 rows of "
        f"the aborted attempt {ABORTED} (trace {TRACE_SHA256[:8]}...) with ZERO new model contacts through core.flight.cli "
        f"seal-only, finalizes it with the one official score job, and reads it by the unchanged READ row {READ_RUN}.")
    draft["cell_kind"] = (
        f"E4-1 SEAL-ONLY COMPLETION: a new attempt {SO} (FIT attempt {FSO}, records no contact) under the SAME run id "
        f"{RUN}, resume_from [{ABORTED}]; the union covers the 1,080-row roster, so nothing is flown. Claim ceiling "
        "'nominated', unchanged.")
    draft["authorization_basis"] = (
        "Owner decision 194 (PENDING): seal-only completion of the aborted E4-1 arm under the merged seal fix "
        f"({FIX_COMMIT}), on the offline replay proof recorded as resume_replay_proof (1,080 rows checked, 0 failing, 0 "
        "sealed twice), the same shape as owner decision 189 option A. Owner decision 22 (resume-recovery) stands; the "
        "parent authorization basis stands: " + parent_draft["authorization_basis"])
    draft["retry_basis"] = (
        f"The E4-1 arm flew all 1,080 rows (6,304 calls, 18,730.5 s audio) and ABORTED at the seal on {ERROR}; root "
        "cause named to a component (the seal's finite-completion rule vs post-accept relisten shadow contacts on 8 of "
        f"10 finite rows) and fixed at {FIX_COMMIT}. Its 1,080 rows are complete in its trace; the seal-only completion "
        "keeps them and flies nothing. The aborted attempt stays charged run-cumulatively (6,304 calls of 18,360).")
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
        "relpath": "coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json",
        "decision_id": "slurp-stage3-relisten-fold-a-admission-v1",
        "status": "stands; it admitted the original attempt, which aborted at the seal"}
    antecedents["sealonly_protocol"] = {"path": f"{RD}/protocol-registered-v1.json", "sha256": protocol_sha}
    antecedents["sealonly_analysis_recipe"] = {"path": f"{RD}/analysis-recipe-v1.json", "sha256": recipe_sha}
    antecedents["sealonly_registered_facts"] = {"path": f"{RD}/registered-facts-v1.json", "sha256": facts_sha}
    antecedents["sealonly_preregistration"] = {"path": PREREG, "sha256": None}
    antecedents["sealonly_readme"] = {"path": f"{RD}/README.md", "sha256": None}
    antecedents["derive_script"] = {"path": "scripts/flights/e4/derive_slurp_e4_sealonly_cell.py",
                                    "sha256": _sha("scripts/flights/e4/derive_slurp_e4_sealonly_cell.py")}
    antecedents["registration_base_commit"] = _head()
    draft["registered_hashes"] = {"seal-only": {"composed_config": ident.config_hash, "protocol": ident.protocol_hash}}
    population = draft.setdefault("population", {})
    population["partition"] = "TRAIN Fold A 1,080, unchanged; 1,080 kept from the aborted attempt, 0 flown"
    draft["status"] = "DRAFT-NOT-MINTED"
    draft["recorded_at_utc"] = None
    _dump(f"{RD}/root-admission-sealonly-draft-v1.json", draft)
    print(json.dumps({"cell": CELL, "experiment": EXP, "attempt_id": SO, "fit_attempt_id": FSO,
                      "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
                      "prepared_phase_supply": ident.prepared_phase_supply.relpath,
                      "protocol_sha": protocol_sha, "replay": [proof["rows_checked"], proof["rows_failing"],
                                                               proof["sealed_twice"]]}, indent=1))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-json", required=True, type=Path)
    parser.add_argument("--replay-commit", required=True)
    args = parser.parse_args(argv)
    replay = json.loads(args.replay_json.read_text(encoding="utf-8"))
    derive_baseline()
    derive_experiment()
    derive_package(replay, args.replay_commit)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
