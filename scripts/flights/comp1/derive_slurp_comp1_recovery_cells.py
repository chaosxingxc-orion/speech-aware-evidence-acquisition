#!/usr/bin/env python3
"""Derive BOTH held recovery variants of the aborted COMP-1 arm (decision 58: script-derived).

The COMP-1 arm ``SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1`` ABORTED at contact ``flight-1854`` on
2026-09-28 at flight commit ``cb628f59`` (471 rows settled, 1 incomplete, 608 never started,
1,913 contacts; trace SHA-256 ``029a2dbb...61997``) on a harness defect: the Solver citation parser
refused a repeated id (``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``). The
owner rules between two recovery forms. This script writes BOTH, each HELD, so either can be
flipped the moment the ruling lands. The one that is not chosen is superseded unflown.

**VARIANT ``resume``** (owner decision 22, harness item E10): the SAME run id under the new attempt
``attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume`` with ``resume_from`` naming the
aborted attempt and its trace SHA-256. Every COMPLETE row is kept without selection; every other
row is flown. Configs: ``configs/baseline/slurp-native-stage3-comp1-fold-a-baseline-v1-resume.json``,
``configs/experiment/slurp-native-stage3-comp1-fold-a-v1-resume.json``,
``configs/campaign/slurp-native-stage3-comp1-fold-a-v1-resume.json``. Package:
``docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1/``.

**VARIANT ``rec``** (the ordinary recovery re-registration; precedent B5e recovery): the fresh run
id ``SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1`` over all 1,080 rows, plus its four-row form smoke
``SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1``, each with its own FIT spend identity. The bytes
are the arm's (and the smoke's) except the identities and the recovery note. Configs:
``configs/{baseline,experiment,campaign}/slurp-native-stage3-comp1-fold-a-rec-*``. Package:
``docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1/``.

In BOTH variants the shared in-chain A/A ``SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`` is FINALIZED and
scored and is NEVER re-flown; it is the comparator the recovered arm is read at.

Each derived cell INHERITS its parent's prepared first-phase supply pin (the arm's
``phase-supply-v3.json``, the smoke's ``phase-supply-v3.json``). ``core.preparation.artifact_inputs``
binds the cell and attempt identities, so the pin will NOT verify for the derived cell: the
coordinator's flip (``scripts/flights/repin_cell.py``) rebuilds it model-free into the derived
run id's next ``phase-supply-v<N>.json`` and ASSERTS its output equals the inherited artifact's
output. ``--allow-output-change`` must never be passed: an output that moved means the knowledge
channel moved and the recovery would no longer be the arm.

This script writes CONFIG and PACKAGE files only. It performs no contact, prepares no supply,
mints no decision receipt, writes no ledger row and flips nothing. Model-free: it composes the
fragments with ``core.config.compose`` exactly as ``core.flight.cli`` does to quote the pre-flip
composed/protocol hashes the re-pin tool rewrites.

    PYTHONPATH=<tree>/src python scripts/flights/comp1/derive_slurp_comp1_recovery_cells.py \\
        --variant resume|rec|both [--proof-receipt-sha256 <64 hex>]
"""

from __future__ import annotations
import os

import argparse
import copy
import hashlib
import io
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATE = "2026-09-28"
REGISTERED_AT = "2026-09-28T12:00:00.000000+00:00"
SOURCE_TREE = (
    "studies/speech-aware-evidence-acquisition, worktree /home/chao/saea-worktrees/fable-comp1res, "
    "branch fable/comp1res (from fable/comp1rec at a451f942)"
)
STATUS = "REGISTERED_BEFORE_CONTACT_HELD_AWAITING_OWNER_RECOVERY_RULING"

PARENT_RD = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
DIAGNOSIS = "docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md"
ARM_EXP = "slurp-native-stage3-comp1-fold-a-v1"
SMOKE_EXP = "slurp-native-stage3-comp1-fold-a-smoke-4-v1"
ARM_BASE = "slurp-native-stage3-comp1-fold-a-baseline-v1"
SMOKE_BASE = "slurp-native-stage3-comp1-fold-a-smoke-4-baseline-v1"

RUN_ID = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1"
AA_RUN_ID = "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
READ_RUN_ID = "SAEA-SLURP-STAGE3-COMP1-FOLD-A-PAIRED-ANALYSIS-V1"
ABORTED_ATTEMPT = "attempt-slurp-native-stage3-comp1-fold-a-generation-v1"
TRACE_SHA256 = "029a2dbbd62bc8752ff9e7d6a53dfee0cb49872f48b11267e49c4022c9561997"
FLIGHT_COMMIT = "cb628f592934921a48102a5451ce1dd2f5c0fc98"
CITATION_FIX_COMMIT = "a451f942"
PROOF_RELPATH = "coordination/slurp-stage3-comp1-fold-a-v1/resume-byte-identity-proof-v1.json"
PROOF_SCRIPT = "scripts/flights/comp1/comp1_resume_byte_identity_proof.py"

PREDECESSOR = {
    "calls": 1913, "audio_seconds": 5171.3779375, "complete_rows": 471, "incomplete_rows": 1,
    "unstarted_rows": 608, "trace_records": 10035, "trace_bytes": 132650912,
}
CAP_CALLS, CAP_AUDIO, PER_ROW = 11880, 33930, 11

# Variant identities.
RESUME = {
    "tag": "resume",
    "rd": "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1",
    "experiment": "slurp-native-stage3-comp1-fold-a-v1-resume",
    "cell": "slurp-native-stage3-comp1-fold-a-v1-resume",
    "baseline": "slurp-native-stage3-comp1-fold-a-baseline-v1-resume",
    "campaign": "configs/campaign/slurp-native-stage3-comp1-fold-a-v1-resume.json",
    "run_id": RUN_ID,
    # attempt 3 (2026-09-29): attempt 1 aborted on a server CUDA abort; attempt 2 aborted at 00:20:43Z on a
    # FIT-identity collision because its registration reused attempt 1's FIT attempt id. Both ids are fresh.
    "attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3",
    "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1",
    "fit_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3",
    "decision_relpath": "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json",
    "decision_id": "slurp-stage3-comp1-fold-a-resume-admission-v1",
}
# The four-row DRY RUN of resume attempt 3 (owner decision 181: fix, prove on a 4-row dry run, then resume).
# core.flight.cli has no bounded-resume mode (no row cap or dry-run flag for a resume), so the dry run is a
# four-row SMOKE of the arm's form (the parent COMP-1 smoke's bytes) under fresh run, attempt and FIT ids. It
# flies through the same worker path and the same per-contact native FIT identity gate
# (core.preparation_fit.build_native_contact_fit_gate) that refused attempt 2, and it is flown as the smoke of the
# resume step: the batch driver stops before the resume opens unless the dry run passes its structural check.
RESUME3_SMOKE = {
    "rd": "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1",
    "experiment": "slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1",
    "cell": "slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1",
    "baseline": "slurp-native-stage3-comp1-fold-a-resume3-smoke-4-baseline-v1",
    "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1",
    "attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-3-smoke",
    "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-FIT-V1",
    "fit_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume-3-smoke",
    "decision_relpath": "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json",
    "decision_id": "slurp-stage3-comp1-fold-a-resume-admission-v1",
}
REC = {
    "tag": "rec",
    "rd": "docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-rec-v1",
    "experiment": "slurp-native-stage3-comp1-fold-a-rec-v1",
    "cell": "slurp-native-stage3-comp1-fold-a-rec-v1",
    "baseline": "slurp-native-stage3-comp1-fold-a-rec-baseline-v1",
    "campaign": "configs/campaign/slurp-native-stage3-comp1-fold-a-rec-v1.json",
    "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-V1",
    "attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-generation-v1",
    "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-FIT-V1",
    "fit_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-fit-v1",
    "decision_relpath": "coordination/slurp-stage3-comp1-fold-a-v1/root-admission-rec-v1.json",
    "decision_id": "slurp-stage3-comp1-fold-a-rec-admission-v1",
    "smoke": {
        "experiment": "slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1",
        "cell": "slurp-native-stage3-comp1-fold-a-rec-smoke-4-v1",
        "baseline": "slurp-native-stage3-comp1-fold-a-rec-smoke-4-baseline-v1",
        "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-V1",
        "attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-smoke-4-generation-v1",
        "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-REC-SMOKE-4-FIT-V1",
        "fit_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-rec-smoke-4-fit-v1",
    },
}


def _load(relpath: str):
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _dump(relpath: str, document) -> str:
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_text(relpath: str, text: str) -> None:
    path = REPO / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)


def _head() -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short=8", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def _identity(experiment: str, cell_id: str):
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells  # noqa: PLC0415
    from speech_aware_evidence_acquisition.core.flight.repin import compute_cell_identity  # noqa: PLC0415

    cells = [c for c in load_campaign_cells(REPO, experiment) if c.document["cell_id"] == cell_id]
    assert len(cells) == 1, (experiment, cell_id)
    return compute_cell_identity(REPO, experiment, cells[0])


def _supply_requirement(requirements, run_id: str) -> dict:
    own = [r for r in requirements if r.get("kind") == "preparation"
           and r.get("relpath", "").startswith(f"prepared/{run_id}/phase-supply-v")]
    assert len(own) == 1, run_id
    return own[0]


def _agreement_requirement(requirements) -> dict:
    found = [r for r in requirements if r.get("kind") == "preparation"
             and "EXEMPLAR-AGREEMENT" in r.get("relpath", "")]
    assert len(found) == 1
    return found[0]


def _inherited_supply_reason(parent_run: str, derived_run: str, output_sha: str | None) -> str:
    return (
        f"INHERITED from {parent_run}: that cell's own model-free first-phase Perception supply "
        "(built by core.flight.cli prepare-supply with zero model, tokenizer, encoder, scorer or "
        "server contacts). EXPECT THIS PIN TO BE REBUILT rather than to verify as it stands: "
        "core.preparation.artifact_inputs binds the composed configuration, cell and attempt "
        "identities included, so scripts/flights/repin_cell.py rebuilds it model-free into "
        f"prepared/{derived_run}/phase-supply-v<N>.json, ASSERTS the new output equals this "
        "artifact's output"
        + (f" ({output_sha})" if output_sha else "")
        + " and re-pins it in the same cycle. --allow-output-change must NEVER be passed: an output "
        "that moved means the knowledge channel moved and the recovery is no longer the arm."
    )


def _budget_resume() -> dict:
    flown = 1080 - PREDECESSOR["complete_rows"]
    worst = flown * PER_ROW
    return {
        "kept_rows": PREDECESSOR["complete_rows"],
        "flown_rows": flown,
        "predecessor_calls": PREDECESSOR["calls"],
        "predecessor_audio_seconds": PREDECESSOR["audio_seconds"],
        "flown_worst_case_calls": worst,
        "run_cumulative_worst_case_calls": PREDECESSOR["calls"] + worst,
        "cap_calls": CAP_CALLS,
        "headroom_calls": CAP_CALLS - PREDECESSOR["calls"] - worst,
    }


# --------------------------------------------------------------------------------------------
# Notes.
# --------------------------------------------------------------------------------------------

def _resume_note() -> str:
    b = _budget_resume()
    return (
        "Cell COMP-1 RESUME-RECOVERY (owner decision 22, harness item E10), HELD pending the owner's "
        f"recovery ruling. The arm attempt {ABORTED_ATTEMPT} of run {RUN_ID} ABORTED on 2026-09-28 at "
        f"contact flight-1854 at flight commit {FLIGHT_COMMIT[:8]}: 471 rows settled, 1 incomplete, "
        f"608 never started, 1,913 contacts, trace SHA-256 {TRACE_SHA256}. Root cause named to a "
        "component (" + DIAGNOSIS + "): rails.solver_citation.parse_cited_answer refused a repeated "
        "intent citation id that the per-contact grammar legally admits; fixed at "
        f"{CITATION_FIX_COMMIT} (rails/solver_citation.py only, outside the prepared identity set). "
        "The resume replay itself needed one harness repair to read this cell's receipts "
        "(core.flight.resume.NON_WIRE_CONTACT_BLOCKS: the context_fit and solver_citations annotation "
        "blocks are no longer claimed as wire contacts; before it, 0 of 471 settled rows classified "
        "COMPLETE). THE LETTER OF DECISION 22 IS BROKEN: it admits a resume only when code and request "
        "bytes are unchanged, and two harness files changed. Its PURPOSE is proven model-free by "
        f"{PROOF_SCRIPT} (receipt {PROOF_RELPATH}): every cited grammar re-renders byte-identically, "
        "481 of 481 kept citation records are identical under the fixed code, and the one changed "
        "disposition (flight-1854) lies in the one INCOMPLETE row, which is re-flown. The owner rules "
        f"whether that admits a resume. THIS IS COMP-1's ONE recovery re-registration: {b['kept_rows']} "
        f"rows kept under I7r custody without selection, {b['flown_rows']} rows flown under the SAME "
        "run id; a second failure CLOSES cell COMP-1. The shared in-chain A/A "
        f"{AA_RUN_ID} is FINALIZED and scored and is never re-flown."
    )


def _rec_note() -> str:
    return (
        "Cell COMP-1 RECOVERY RE-REGISTRATION (-REC), HELD pending the owner's recovery ruling. The "
        f"arm attempt {ABORTED_ATTEMPT} of run {RUN_ID} ABORTED on 2026-09-28 at contact flight-1854 "
        f"at flight commit {FLIGHT_COMMIT[:8]} (1,913 contacts, trace SHA-256 {TRACE_SHA256}) on a "
        "harness defect named to a component (" + DIAGNOSIS + "): "
        "rails.solver_citation.parse_cited_answer refused a repeated intent citation id the "
        f"per-contact grammar legally admits; fixed at {CITATION_FIX_COMMIT} (rails/solver_citation.py "
        "only). This is COMP-1's ONE root-diagnosed recovery re-registration, taken as a FULL re-fly "
        "under a fresh run id over all 1,080 rows (precedent: the B5e recovery run "
        "SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1). The "
        "aborted run's 1,913 contacts stay charged to it and its exposure row is marked consumed = yes "
        "at countersignature; nothing of it is kept or read. The bytes are the arm's except the run, "
        "attempt and FIT identities and this note; the shared in-chain A/A "
        f"{AA_RUN_ID} is FINALIZED and scored and is never re-flown. A second failure CLOSES cell "
        "COMP-1: no third registration."
    )


def _resume_failure_policy() -> str:
    return (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, "
        "role-graph, prompt, knowledge, geometry or cap change, and no silent recovery. THIS "
        "registration IS the ONE root-diagnosed recovery re-registration of run " + RUN_ID + ", taken in "
        "the resume-recovery form of owner decision 22 (harness item E10) IF the owner rules that the "
        "byte-identity proof admits it (the arm's own resume clause names an infrastructure failure; "
        "this abort was a harness defect). A second failure CLOSES cell COMP-1: no third registration, "
        "and the fix must be proven on a four-row dry run before another mechanism is admitted. A "
        "partial manifest is never scored and never read."
    )


def _rec_failure_policy() -> str:
    return (
        "Stop and preserve on the first failure. No automatic restart, replay, row filtering, roster, "
        "role-graph, prompt, knowledge, geometry or cap change. THIS registration IS the ONE "
        "root-diagnosed recovery re-registration of cell COMP-1 (the aborted run " + RUN_ID + "), taken "
        "as a full re-fly under a fresh run id. A second failure CLOSES cell COMP-1: no third "
        "registration, and the fix must be proven on a four-row dry run before another mechanism is "
        "admitted. A partial manifest is never scored and never read."
    )


# --------------------------------------------------------------------------------------------
# Config fragments.
# --------------------------------------------------------------------------------------------

def _derive_baseline(parent: str, name: str, fit_run: str, fit_attempt: str, note: str) -> None:
    doc = _load(f"configs/baseline/{parent}.json")
    doc["native_contact_fit"]["run_id"] = fit_run
    doc["native_contact_fit"]["attempt_id"] = fit_attempt
    doc["what_this_is"] = (
        f"{note} This baseline is configs/baseline/{parent}.json byte for byte except "
        "native_contact_fit.run_id / attempt_id and this note. The parent's own note, verbatim: "
        + doc["what_this_is"]
    )
    _dump(f"configs/baseline/{name}.json", doc)


def _derive_experiment(parent: str, v: dict, *, note: str, failure_policy: str,
                       resume: bool, smoke: bool = False) -> None:
    doc = _load(f"configs/experiment/{parent}.json")
    cell = doc["cells"][0]
    requirements = cell["readiness"]["requirements"]
    parent_run = cell["run_id"]
    supply = copy.deepcopy(_supply_requirement(requirements, parent_run))
    output_sha = None
    try:
        artifact = json.loads(Path(_data_root(), supply["relpath"]).read_text(encoding="utf-8"))
        output_sha = artifact.get("output_sha256")
    except (OSError, ValueError):
        output_sha = None
    supply["reason"] = _inherited_supply_reason(parent_run, v["run_id"], output_sha)
    new_cell = {}
    for key, value in cell.items():
        if key == "attempt_id":
            new_cell[key] = v["attempt_id"]
        elif key == "baseline_fragment":
            new_cell[key] = v["baseline"]
        elif key == "cell_id":
            new_cell[key] = v["cell"]
        elif key == "readiness":
            new_cell[key] = {
                "reason": (
                    f"{note} Registered before contact by the COMP-1 recovery registration agent "
                    f"(Claude Opus 5.5) on {DATE}; HELD. The coordinator, once the owner rules for "
                    f"this variant, countersigns its DRAFT rows, mints {v['decision_relpath']} "
                    f"(decision id {v['decision_id']}) and flips with scripts/flights/repin_cell.py "
                    "--set-ready, which rebuilds the inherited supply pin under this cell's own run "
                    "id and asserts its output unchanged. Nothing here authorises a flight, a "
                    "readiness flip or an admission entry."
                ),
                "requirements": [copy.deepcopy(_agreement_requirement(requirements)), supply],
                "state": "held",
            }
        elif key == "run_id":
            if resume:
                new_cell["resume_from"] = {"attempt_id": ABORTED_ATTEMPT, "trace_sha256": TRACE_SHA256}
            new_cell[key] = v["run_id"]
        else:
            new_cell[key] = copy.deepcopy(value)
    doc["cells"] = [new_cell]
    doc["date"] = DATE
    doc["experiment_id"] = v["run_id"]
    doc["failure_policy"] = failure_policy
    doc["fragment_kind"] = f"saea-{v['experiment']}"
    doc["purpose"] = f"{note} THE PARENT'S PURPOSE, UNCHANGED: {doc['purpose']}"
    if resume:
        b = _budget_resume()
        doc["generation_budget"]["definition"] = (
            "RUN-CUMULATIVE, which is what owner decision 22 requires of a resume: the resumed attempt "
            "and its predecessor share one run id, so core.attempts.AttemptStore.prior_actual_usage sums "
            "every attempt file under the run id and the gate holds that sum against "
            f"planned_model_calls {CAP_CALLS} (invariants I3/I6). The predecessor durably spent "
            f"{b['predecessor_calls']:,} contacts and {b['predecessor_audio_seconds']} s of repeated "
            f"speech. This attempt flies {b['flown_rows']} rows (1 partial + 608 never started) whose "
            f"worst case is {b['flown_rows']} x {PER_ROW} = {b['flown_worst_case_calls']:,}, so the "
            f"run-cumulative worst case is {b['run_cumulative_worst_case_calls']:,} within "
            f"{CAP_CALLS:,}, with {b['headroom_calls']:,} of headroom. Expect about 2,500 realized "
            "contacts (the PLAN family realises about 4.1 per row). Ceilings are bounds, never targets."
        )
    elif not smoke:
        doc["generation_budget"]["definition"] = (
            "A fresh run id: its own caps, unchanged from the arm's (1,080 x 11 = 11,880, the exact "
            "program maximum). The aborted run's 1,913 contacts stay charged to "
            f"{RUN_ID} and are never counted here or kept. " + doc["generation_budget"]["definition"]
        )
    _dump(f"configs/experiment/{v['experiment']}.json", doc)


def _data_root() -> str:
    import os  # noqa: PLC0415

    return (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")


# --------------------------------------------------------------------------------------------
# Package documents.
# --------------------------------------------------------------------------------------------

def _plan(parent_plan: str, v: dict, identity, *, kind: str, protocol_sha: str, rd: str,
          execution_route: str, extra: dict) -> dict:
    doc = _load(f"{PARENT_RD}/{parent_plan}")
    doc["cell"] = v["cell"]
    doc["experiment"] = v["experiment"]
    doc["composed_config_hash"] = identity.config_hash
    doc["execution_plan"]["protocol_hash"] = identity.protocol_hash
    if kind == "generation":
        doc["execution_plan"]["run_id"] = v["run_id"]
        doc["execution_plan"]["attempt_id"] = v["attempt_id"]
    else:
        doc["execution_plan"]["run_id"] = v["fit_run_id"]
        doc["execution_plan"]["attempt_id"] = v["fit_attempt_id"]
    doc["protocol_document"] = {"relpath": f"{rd}/protocol-registered-v1.json", "sha256": protocol_sha}
    doc["prepared_phase_supply"] = {
        "note": (
            "INHERITED pin; the flip rebuilds it under this cell's own run id and asserts the output "
            "unchanged (never --allow-output-change)."
        ),
        "relpath": identity.prepared_phase_supply.relpath,
        "sha256": identity.prepared_phase_supply.sha256,
        "output_sha256": doc.get("prepared_phase_supply", {}).get("output_sha256"),
    }
    doc["execution_route"] = execution_route
    doc["preparation_base_commit"] = _head()
    doc["registered_at_utc"] = REGISTERED_AT
    doc["source_tree"] = SOURCE_TREE
    doc["status"] = STATUS
    doc.update(extra)
    return doc


def _protocol(v: dict, cells: dict, *, variant: str, extra: dict) -> dict:
    parent_sha = hashlib.sha256((REPO / f"{PARENT_RD}/protocol-registered-v1.json").read_bytes()).hexdigest()
    return {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": f"slurp-stage3-comp1-fold-a-{variant}-protocol-v1",
        "status": STATUS,
        "registered_at_utc": REGISTERED_AT,
        "source_tree": SOURCE_TREE,
        "study_commit_at_registration": _head(),
        "parent_protocol": {"relpath": f"{PARENT_RD}/protocol-registered-v1.json", "sha256": parent_sha,
                            "rule": "Everything the parent fixes -- the question, the composition, the "
                                    "comparator, the decision rule, the margins, the attribution table, "
                                    "the prohibitions -- stands unchanged and is not re-litigated."},
        "abort": {
            "run_id": RUN_ID, "attempt_id": ABORTED_ATTEMPT, "flight_commit": FLIGHT_COMMIT,
            "failing_contact": "flight-1854", "trace_sha256": TRACE_SHA256, "counts": PREDECESSOR,
            "diagnosis": DIAGNOSIS,
            "root_cause": "rails.solver_citation.parse_cited_answer refused a repeated intent citation "
                          "id that the per-contact grammar admits (no uniqueItems); the error had no "
                          "per-row disposition, so native_episode.invoke_direct aborted the arm.",
            "fix": {"commit": CITATION_FIX_COMMIT, "files": ["src/speech_aware_evidence_acquisition/rails/solver_citation.py"],
                    "identity_set": "outside the prepared-supply identity set (runtime.py _phase_seed_inputs)"},
        },
        "recovery_counter": "COMP-1's ONE root-diagnosed recovery re-registration; a second failure "
                            "closes the cell (no third registration).",
        "shared_in_chain_replicate": {
            "run_id": AA_RUN_ID, "state": "FINALIZED, COMPLETED at cb628f59, scored",
            "rule": "never re-flown; the recovered arm is read at it. It flew in the aborted chain on "
                    "2026-09-28; the recovered arm flies in a LATER chain, so the replicate is no "
                    "longer strictly in-chain for this arm -- disclosed, not re-declared.",
        },
        "cells": cells,
        **extra,
    }


def _recipe(v: dict, *, variant: str, extra_rule: str) -> dict:
    doc = _load(f"{PARENT_RD}/analysis-recipe-v1.json")
    doc["recipe_id"] = f"slurp-stage3-comp1-fold-a-{variant}-paired-analysis-v1"
    doc["registered_at_utc"] = REGISTERED_AT
    doc["arms"]["arm"]["run_id"] = v["run_id"]
    doc["arms"]["arm"]["attempt_id"] = v["attempt_id"]
    doc["arms"]["arm"]["fit_run_id"] = v["fit_run_id"]
    doc["parent_recipe"] = {
        "relpath": f"{PARENT_RD}/analysis-recipe-v1.json",
        "sha256": hashlib.sha256((REPO / f"{PARENT_RD}/analysis-recipe-v1.json").read_bytes()).hexdigest(),
        "rule": "unchanged except the arm's identities and the recovery reading rule below",
    }
    doc["recovery_reading_rule"] = extra_rule
    doc["read_run_id_note"] = (
        "The READ run id and its exposure-ledger row are the parent's, UNCHANGED: the COMP-1 read is "
        "one read whichever recovery form carries the arm."
    )
    return doc


def derive_resume(proof_sha: str | None) -> None:
    v = RESUME
    note = _resume_note()
    _derive_baseline(ARM_BASE, v["baseline"], v["fit_run_id"], v["fit_attempt_id"], note)
    _derive_experiment(ARM_EXP, v, note=note, failure_policy=_resume_failure_policy(), resume=True)
    _dump(v["campaign"], {"cells": [{"cell": v["cell"], "experiment": v["experiment"]}],
                          "schema": "saea-campaign-plan-v1"})
    ident = _identity(v["experiment"], v["cell"])
    b = _budget_resume()
    rd = v["rd"]
    protocol = _protocol(v, {"resume": {
        "cell": v["cell"], "experiment": v["experiment"], "run_id": v["run_id"],
        "attempt_id": v["attempt_id"], "fit_run_id": v["fit_run_id"], "fit_attempt_id": v["fit_attempt_id"],
        "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
        "resume_from": {"attempt_id": ABORTED_ATTEMPT, "trace_sha256": TRACE_SHA256},
    }}, variant="resume", extra={
        "recovery_form": "resume-recovery (owner decision 22, harness item E10)",
        "decision_22_precondition": {
            "letter": "code and request bytes unchanged -- an infrastructure failure, never a harness "
                      "defect (core/flight/resume.py module docstring)",
            "status": "BROKEN BY THE LETTER: a harness defect, and two harness files changed "
                      f"(rails/solver_citation.py at {CITATION_FIX_COMMIT}; core/flight/resume.py "
                      "NON_WIRE_CONTACT_BLOCKS, which lets the replay read this cell's receipts)",
            "purpose_proof": {"script": PROOF_SCRIPT, "receipt": PROOF_RELPATH,
                              "receipt_sha256_at_registration": proof_sha,
                              "verdict": "PASS: 482 cited contacts; 481/481 captures identical; "
                                         "481/481 kept-row sealed citation records identical under "
                                         "the fixed code; 1 refused-then-sealed contact (flight-1854) "
                                         "in the 1 INCOMPLETE row; 0 regressions; 0 grammar "
                                         "re-render mismatches"},
            "ruling": "the OWNER rules whether the proof admits a resume",
        },
        "rows": {"kept": b["kept_rows"], "flown": b["flown_rows"], "partial": 1, "unstarted": 608},
        "budget": b,
        "no_commit_equality_rule": "Neither core.flight.resume, the runtime's resume path nor "
                                   "core.bundle.verify_bundle compares the recovery's flight commit "
                                   "with the aborted attempt's; the merged manifest's study_commit is "
                                   "the recovery flight commit, and I7r verifies the kept rows against "
                                   "the predecessor trace by sample id and bytes.",
    })
    protocol_sha = _dump(f"{rd}/protocol-registered-v1.json", protocol)
    route = (f"Shared core.flight.cli campaign over the committed single-cell campaign plan {v['campaign']} "
             f"(the resume cell only; the shared A/A {AA_RUN_ID} is FINALIZED and never re-flown), "
             "through the batch driver as a kind=resume step (scripts/flights/comp1/batch_chain_comp1_resume.sh).")
    extra = {"resume_from": {"attempt_id": ABORTED_ATTEMPT, "trace_sha256": TRACE_SHA256}, "resume_budget": b}
    _dump(f"{rd}/generation-plan-registered-v1.json",
          _plan("generation-plan-registered-v1.json", v, ident, kind="generation", protocol_sha=protocol_sha,
                rd=rd, execution_route=route, extra=extra))
    _dump(f"{rd}/fit-plan-registered-v1.json",
          _plan("fit-plan-registered-v1.json", v, ident, kind="fit", protocol_sha=protocol_sha, rd=rd,
                execution_route="The shared core.flight.cli FIT path under this cell's own native_contact_fit "
                                "ids (the SAME FIT run id, a new attempt); it measures request envelopes and "
                                "produces no generation.", extra={}))
    _dump(f"{rd}/analysis-recipe-v1.json", _recipe(v, variant="resume", extra_rule=(
        "The arm's manifest is the MERGED resume manifest under the resume attempt: 471 rows kept from "
        f"{ABORTED_ATTEMPT} under I7r custody plus 609 flown. Kept and flown rows are never separated, "
        "compared or reported as strata; the read is paired over all 1,080 rows exactly as the parent "
        "recipe fixes it. The manifest's predecessor_attempt block must name trace "
        f"{TRACE_SHA256}; refuse otherwise.")))


def derive_rec() -> None:
    v = REC
    s = v["smoke"]
    note = _rec_note()
    _derive_baseline(ARM_BASE, v["baseline"], v["fit_run_id"], v["fit_attempt_id"], note)
    _derive_baseline(SMOKE_BASE, s["baseline"], s["fit_run_id"], s["fit_attempt_id"], note)
    _derive_experiment(ARM_EXP, v, note=note, failure_policy=_rec_failure_policy(), resume=False)
    smoke_policy = (
        "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality "
        "read. A failed smoke stops the -REC arm and it does not open; it is the FORM proof of the fixed "
        "tree (the four-row dry run the abort diagnosis requires), recorded beside the model-free replay "
        "of the fix, never as a proof on its own."
    )
    sv = dict(s, decision_relpath=v["decision_relpath"], decision_id=v["decision_id"])
    _derive_experiment(SMOKE_EXP, sv, note=note, failure_policy=smoke_policy, resume=False, smoke=True)
    _dump(v["campaign"], {"cells": [{"cell": v["cell"], "experiment": v["experiment"]}],
                          "schema": "saea-campaign-plan-v1"})
    arm_id = _identity(v["experiment"], v["cell"])
    smoke_id = _identity(s["experiment"], s["cell"])
    rd = v["rd"]
    protocol = _protocol(v, {
        "arm": {"cell": v["cell"], "experiment": v["experiment"], "run_id": v["run_id"],
                "attempt_id": v["attempt_id"], "fit_run_id": v["fit_run_id"],
                "fit_attempt_id": v["fit_attempt_id"],
                "composed_config_hash": arm_id.config_hash, "protocol_hash": arm_id.protocol_hash},
        "smoke": {"cell": s["cell"], "experiment": s["experiment"], "run_id": s["run_id"],
                  "attempt_id": s["attempt_id"], "fit_run_id": s["fit_run_id"],
                  "fit_attempt_id": s["fit_attempt_id"],
                  "composed_config_hash": smoke_id.config_hash, "protocol_hash": smoke_id.protocol_hash},
    }, variant="rec", extra={
        "recovery_form": "ordinary recovery re-registration under a fresh -REC run id (precedent B5e recovery)",
        "aborted_run_disposition": f"{RUN_ID}'s exposure row is marked consumed = yes at countersignature; its "
                                   "1,913 contacts stay charged to it; nothing of it is kept or read.",
        "rows": {"flown": 1080, "kept": 0},
        "stage3_measurement_rule": "identical to the arm's declared block (expected_effect_pp 3.23, "
                                   f"cross-flight-with-in-chain-replicate at {AA_RUN_ID}); the recovery "
                                   "does NOT re-declare.",
    })
    protocol_sha = _dump(f"{rd}/protocol-registered-v1.json", protocol)
    route = (f"Shared core.flight.cli campaign over the committed single-cell campaign plan {v['campaign']} "
             f"(the -REC arm only; the shared A/A {AA_RUN_ID} is FINALIZED and never re-flown), through the "
             "batch driver with the -REC four-row smoke first (scripts/flights/comp1/batch_chain_comp1_rec.sh).")
    _dump(f"{rd}/generation-plan-registered-v1.json",
          _plan("generation-plan-registered-v1.json", v, arm_id, kind="generation", protocol_sha=protocol_sha,
                rd=rd, execution_route=route, extra={}))
    _dump(f"{rd}/fit-plan-registered-v1.json",
          _plan("fit-plan-registered-v1.json", v, arm_id, kind="fit", protocol_sha=protocol_sha, rd=rd,
                execution_route="The shared core.flight.cli FIT path under this cell's own native_contact_fit "
                                "ids; it measures request envelopes and produces no generation.", extra={}))
    _dump(f"{rd}/smoke-generation-plan-registered-v1.json",
          _plan("smoke-generation-plan-registered-v1.json", s, smoke_id, kind="generation",
                protocol_sha=protocol_sha, rd=rd,
                execution_route="core.flight.cli worker on the four-row roster, flown by the batch driver "
                                "before the -REC arm.", extra={}))
    _dump(f"{rd}/smoke-fit-plan-registered-v1.json",
          _plan("smoke-fit-plan-registered-v1.json", s, smoke_id, kind="fit", protocol_sha=protocol_sha, rd=rd,
                execution_route="The shared core.flight.cli FIT path under the smoke's own native_contact_fit "
                                "ids.", extra={}))
    _dump(f"{rd}/analysis-recipe-v1.json", _recipe(v, variant="rec", extra_rule=(
        f"The arm is the -REC run {v['run_id']}, a full 1,080-row re-fly; the aborted run {RUN_ID} is "
        "never opened, scored or read, and no row of it enters the read.")))
    facts = _load(f"{PARENT_RD}/registered-facts-v1.json")["stage3_measurement"]
    arm_block = copy.deepcopy(facts[RUN_ID])
    smoke_block = copy.deepcopy(facts["SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1"])
    arm_block["recovery_note"] = (
        f"Identical to the arm {RUN_ID}'s declared block (expected_effect_pp 3.23, the same declared "
        "basis, the same replicate). The recovery does NOT re-declare: no number here moved."
    )
    smoke_block["recovery_note"] = "Identical to the COMP-1 smoke's declared block; form only."
    _dump(f"{rd}/registered-facts-v1.json", {
        "schema": "saea-registered-facts-v1",
        "registered_at_utc": REGISTERED_AT,
        "study_commit_at_registration": _head(),
        "parent_registered_facts": f"{PARENT_RD}/registered-facts-v1.json",
        "stage3_measurement": {v["run_id"]: arm_block, s["run_id"]: smoke_block},
    })


def _resume3_note() -> str:
    return (
        "COMP-1 RESUME ATTEMPT 3 DRY RUN (owner decision 181: fix, prove on a 4-row dry run, then resume). "
        "Resume attempt 2 attempt-slurp-native-stage3-comp1-fold-a-generation-v1-resume-2 aborted at "
        "2026-09-29T00:20:43Z before sealing a row (48 calls, 119.3 s audio) on a FIT-identity collision "
        "(core/preparation_fit.py: 'native contact fit identity already has contact or result evidence') caused "
        "by a coordinator-side registration error: it reused resume attempt 1's FIT attempt id "
        "attempt-slurp-native-stage3-comp1-fold-a-fit-v1-resume, whose per-contact evidence already sat under "
        "prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1/. Resume attempt 3 uses fresh generation and FIT attempt "
        "ids. This four-row smoke is the parent COMP-1 smoke's bytes under fresh run, attempt and FIT ids; it "
        "proves the FORM of the fixed registration (a fresh FIT identity root, every request fits, every "
        "episode completes) through the same worker and native FIT gate before the resume opens. Form only; "
        "never scored or read."
    )


def derive_resume3_smoke() -> None:
    v = RESUME3_SMOKE
    note = _resume3_note()
    _derive_baseline(SMOKE_BASE, v["baseline"], v["fit_run_id"], v["fit_attempt_id"], note)
    policy = (
        "Stop on the first failure and preserve every contact. No retry, no scoring, no partial quality read. A "
        "failed dry run stops the chain before resume attempt 3 opens (the batch driver flies it as the resume "
        "step's smoke and stops on a failed structural check); the resume is then not flown and root reports."
    )
    _derive_experiment(SMOKE_EXP, v, note=note, failure_policy=policy, resume=False, smoke=True)
    doc = _load(f"configs/experiment/{v['experiment']}.json")
    cell = doc["cells"][0]
    cell["readiness"]["reason"] = (
        f"{note} Registered before contact 2026-09-29 by root flight operations (Claude Opus 5.5) on the "
        f"coordinator's brief; HELD until root mints {v['decision_relpath']} (decision id {v['decision_id']}) "
        "and flips this cell with scripts/flights/repin_cell.py (it inherits the parent smoke's prepared supply "
        "pin and must reproduce its output; --allow-output-change is never passed)."
    )
    doc["date"] = "2026-09-29"
    _dump(f"configs/experiment/{v['experiment']}.json", doc)
    ident = _identity(v["experiment"], v["cell"])
    rd = v["rd"]
    protocol_path = f"{rd}/protocol-registered-v1.json"
    protocol = _load(protocol_path)
    protocol["cells"]["resume3_dry_run"] = {
        "cell": v["cell"], "experiment": v["experiment"], "run_id": v["run_id"],
        "attempt_id": v["attempt_id"], "fit_run_id": v["fit_run_id"], "fit_attempt_id": v["fit_attempt_id"],
        "composed_config_hash": ident.config_hash, "protocol_hash": ident.protocol_hash,
        "rows": 4, "role": "the four-row dry run of resume attempt 3 (owner decision 181), flown as the smoke of "
                          "the resume step; form only",
    }
    protocol_sha = _dump(protocol_path, protocol)
    for name in ("generation-plan-registered-v1.json", "fit-plan-registered-v1.json"):
        plan = _load(f"{rd}/{name}")
        plan["protocol_document"]["sha256"] = protocol_sha
        _dump(f"{rd}/{name}", plan)
    for kind, name in (("generation", "smoke-generation-plan-registered-v1.json"),
                       ("fit", "smoke-fit-plan-registered-v1.json")):
        route = ("core.flight.cli worker on the parent smoke's four-row roster, flown by the batch driver as the "
                 "smoke of the resume step (scripts/flights/comp1/batch_chain_comp1_resume.sh) before resume "
                 "attempt 3 opens." if kind == "generation" else
                 "The shared core.flight.cli FIT path under the dry run's own fresh native_contact_fit ids.")
        plan = _plan(name, v, ident, kind=kind, protocol_sha=protocol_sha, rd=rd, execution_route=route, extra={})
        plan["registered_at_utc"] = "2026-09-29T00:45:00.000000+00:00"
        plan["source_tree"] = ("studies/speech-aware-evidence-acquisition, worktree "
                               "/home/chao/saea-worktrees/fable-comp1res3, branch fable/comp1res3")
        plan["status"] = "REGISTERED_BEFORE_CONTACT_HELD_AWAITING_ROOT_RECEIPT"
        _dump(f"{rd}/{name}", plan)
    facts = _load(f"{PARENT_RD}/registered-facts-v1.json")["stage3_measurement"]
    block = copy.deepcopy(facts["SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1"])
    block["recovery_note"] = "Identical to the COMP-1 smoke declared block; the dry run of resume attempt 3; form only."
    _dump(f"{rd}/registered-facts-v1.json", {
        "schema": "saea-registered-facts-v1",
        "registered_at_utc": "2026-09-29T00:45:00.000000+00:00",
        "study_commit_at_registration": _head(),
        "parent_registered_facts": f"{PARENT_RD}/registered-facts-v1.json",
        "stage3_measurement": {v["run_id"]: block},
    })


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variant", choices=("resume", "rec", "both", "resume3-smoke"), default="both")
    parser.add_argument("--proof-receipt-sha256", default=None)
    args = parser.parse_args(argv)
    if args.variant == "resume3-smoke":
        derive_resume3_smoke()
        print("derived:", args.variant)
        return 0
    if args.variant in ("resume", "both"):
        derive_resume(args.proof_receipt_sha256)
    if args.variant in ("rec", "both"):
        derive_rec()
    print("derived:", args.variant)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
