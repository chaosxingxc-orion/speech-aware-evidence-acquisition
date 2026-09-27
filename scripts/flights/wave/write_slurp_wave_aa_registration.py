#!/usr/bin/env python3
"""Write the knowledge wave's shared in-chain A/A registration package from the committed configs.

Owner decision 164 reads the wave arms W1, W3 and W4 against ONE shared in-chain A/A of the retained
AGREE arm's own bytes (row 160's precedent). This writer reads the derived A/A fragments
(``scripts/flights/wave/derive_slurp_wave_aa_cell.py``), recomposes the cell's own hashes, PROVES the
composed-config diff against the AGREE arm is bookkeeping plus the dropped supply pin ONLY (the
classifier of ``wave_shared_aa_proof.py``), and writes the package documents, a draft decision
receipt for root and (with ``--append-ledger``) three DRAFT exposure rows: the A/A generation run, its
FIT spend identity and the A/A's own READ row. With ``--check-dir`` it folds in the pre-flight prompt
budget ``core.flight.cli check`` measured for the cell; with ``--proof`` the byte-identity proof's
verdict. Config alone: no contact, no flip, no mint.

    python scripts/flights/wave/write_slurp_wave_aa_registration.py --study-commit <sha> \\
        --registered-at 2026-09-27T23:50:00.000000+00:00 [--check-dir DIR] [--append-ledger]
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1"
PREREG = PACKAGE + "-preregistration.md"
PROOF = PACKAGE + "/shared-aa-proof-v1.json"
LEDGER = "docs/exposure-ledger.md"

CELL = "slurp-native-stage3-wave1-aa-fold-a-v1"
PARENT = "slurp-native-stage3-agree-w1-fold-a-v1"
AA_RUN = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1"
READ_ROW = "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1"
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
AGREE_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
AGREE_OFFICIAL = {"intent_accuracy": 85.8333, "slu_f1": 65.1575, "span_f1": 54.4343, "calls_used": 4385}
SUPPLY_OUTPUT_SHA = "eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
DECISION_ID = "slurp-stage3-wave1-aa-fold-a-admission-v1"
DECISION_RELPATH = "coordination/slurp-stage3-wave1-aa-fold-a-v1/root-admission-v1.json"
WAVE_CAMPAIGN = "configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json"
H_SLU, H_INTENT = 1.2485, 0.9943

WAVE_ARMS = {
    "W1": {"run_id": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1",
           "package": "docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1",
           "read": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1"},
    "W3": {"run_id": "SAEA-SLURP-STAGE3-W3-FOLD-A-V1",
           "package": "docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1",
           "read": "SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1"},
    "W4": {"run_id": "SAEA-SLURP-STAGE3-W4-FOLD-A-V1",
           "package": "docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1",
           "read": "SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1"},
}

INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
COMP1_PACKAGE = "docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1"
DERIVE_SCRIPT = "scripts/flights/wave/derive_slurp_wave_aa_cell.py"
PROOF_SCRIPT = "scripts/flights/wave/wave_shared_aa_proof.py"
GATE = "scripts/checks/stage3_effect_floor_check.py"


def rd(path: str) -> str:
    return io.open(path, encoding="utf-8", newline="").read()


def wr(path: str, text: str) -> str:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    io.open(path, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(path: str, obj: object) -> str:
    return wr(path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _proof_module():
    spec = importlib.util.spec_from_file_location("wave_shared_aa_proof", REPO_ROOT / PROOF_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def identity() -> dict:
    proof_module = _proof_module()
    document = json.loads(rd(f"configs/experiment/{CELL}.json"))
    cell = document["cells"][0]
    composed = compose(REPO_ROOT, cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], CELL)
    parent_doc = json.loads(rd(f"configs/experiment/{PARENT}.json"))
    parent_cell = parent_doc["cells"][0]
    parent = compose(REPO_ROOT, parent_cell["model_fragment"], parent_cell["dataset_fragment"],
                     parent_cell["baseline_fragment"], PARENT)
    diff = proof_module.config_diff(composed.values, parent.values)
    unclassified = [row["leaf"] for row in diff if row["class"] == "unclassified"]
    if unclassified:
        raise SystemExit(f"the A/A's composed config differs from the AGREE arm beyond bookkeeping: {unclassified}")
    if "prepared_phase_supply" in composed.values:
        raise SystemExit("the A/A must carry no committed prepared_phase_supply")
    split = document["population"]["split_identity_hash"]
    return {
        "experiment": CELL, "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
        "baseline_fragment": cell["baseline_fragment"], "parent_experiment": PARENT,
        "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"],
        "arm": composed.values["arm"], "rows": document["population"]["count"], "split_identity_hash": split,
        "composed_config_hash": composed.config_hash, "parent_composed_config_hash": parent.config_hash,
        "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
        "fit": dict(composed.values["native_contact_fit"]), "family_budget": document["family_budget"],
        "execution_profile": document["execution_profile"], "carrier_lock_key": composed.values["carrier_lock_key"],
        "composed_config_diff_against_the_agree_arm": {
            "by_class": {k: sum(1 for row in diff if row["class"] == k) for k in sorted({row["class"] for row in diff})},
            "leaves": [{"leaf": row["leaf"], "class": row["class"]} for row in diff],
            "request_affecting": unclassified,
        },
    }


def fold_check(check_dir: str | None) -> dict:
    if not check_dir:
        return {"status": "PENDING_CHECK"}
    path = Path(check_dir) / f"check-{CELL}.json"
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    report = json.loads(path.read_text(encoding="utf-8"))
    preflight = report.get("preflight") or {}
    phases = []
    for receipt in preflight.get("prompt_budget") or ():
        breakdown = receipt.get("breakdown") or {}
        phases.append({
            "phase": receipt.get("phase"), "decision": receipt.get("decision"),
            "rendered_text_tokens": breakdown.get("rendered_text_tokens"),
            "required_window_tokens": breakdown.get("required_window_tokens"),
            "physical_margin_tokens": receipt.get("physical_margin_tokens"),
            "operational_margin_tokens": receipt.get("operational_margin_tokens"),
        })
    return {"status": "MEASURED_BY_CHECK", "scientific_readiness": report.get("scientific_readiness"),
            "blockers": report.get("blockers"), "prompt_budget_per_phase": phases}


def fold_proof() -> dict:
    if not Path(PROOF).is_file():
        return {"status": "PENDING_PROOF", "tool": PROOF_SCRIPT}
    proof = json.loads(rd(PROOF))
    request = proof["request_bytes"]
    return {
        "status": "PROVEN" if proof["verdict"] == "IDENTICAL" else "REFUTED",
        "relpath": PROOF, "verdict": proof["verdict"], "study_commit": proof["study_commit"],
        "config_classes": proof["composed_config_diff"]["by_class"],
        "supply_output_sha256": {k: proof["prepared_supply"][k]["output_sha256"] for k in ("wave_aa", "agree_arm")},
        "supply_equal_registered_and_committed": proof["prepared_supply"]["equal_registered_and_committed"],
        "rows_dispatched": request["common_run_id"]["wave_aa"]["rows_dispatched"],
        "contacts_compared": request["common_run_id"]["comparison"]["contacts_wave_aa"],
        "common_run_id_payload_and_body_identical": request["common_run_id"]["comparison"]["payload_bytes_identical"]
        and request["common_run_id"]["comparison"]["post_body_bytes_identical"],
        "own_run_ids_body_identical": request["own_run_ids"]["comparison"]["post_body_bytes_identical"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--branch", default="fable/waveaa")
    parser.add_argument("--worktree", default="/home/chao/saea-worktrees/fable-waveaa")
    parser.add_argument("--check-dir", default=None)
    parser.add_argument("--append-ledger", action="store_true")
    args = parser.parse_args(argv)
    os.chdir(REPO_ROOT)

    ids = identity()
    caps = ids["family_budget"]
    fit = fold_check(args.check_dir)
    proof = fold_proof()

    measurement = {
        AA_RUN: {
            "claims_benefit": False,
            "expected_effect_pp": 0.0,
            "measurement_design": "cross-flight-with-in-chain-replicate",
            "primary_metric": "intent accuracy (scenario_action exact) and official pooled SLU-F1, as the instrument",
            "replicate_run_id": AGREE_RUN,
            "rows": 1080,
            "note": (
                "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the retained AGREE arm's own bytes so the "
                "knowledge wave's arms W1, W3 and W4 (owner decision 164) are each read against a within-chain null "
                "flown in the same chain on the same resident session (rule 3; the decision-160 precedent of one "
                "shared A/A). Its expected effect against the sealed AGREE arm (" + AGREE_RUN + ", the request-identical "
                "source of its bytes, proven by shared-aa-proof-v1.json) is exactly zero by construction; a non-zero "
                "read on that pair is a measurement of the cross-flight offset, which is what it is for."
            ),
        },
    }
    arms_line = "; ".join(f"{name} {arm['run_id']} (read {arm['read']})" for name, arm in WAVE_ARMS.items())
    read_rule = (
        "The A/A carries no admission of its own. Its own READ (" + READ_ROW + ") reports the pair (sealed AGREE arm, "
        "wave A/A) on intent accuracy and official pooled SLU-F1 with a paired row bootstrap -- the cross-flight "
        "offset of the resident session at the wave's flight time -- beside the Fold A own-null half-widths (intent "
        f"{H_INTENT} / SLU {H_SLU}; {INSTRUMENT} section 2d), as CONTEXT for the three arm reads, never as a gate on "
        "them and never as a claim. Each wave arm's no-harm verdict is its own package's rule, read at THIS A/A."
    )

    facts = {
        "schema": "saea-registered-facts-v1",
        "_note": f"Every model-free fact this registration rests on, and the CANONICAL stage3_measurement block {GATE} resolves (keyed by run id). The preregistration's fence repeats it; this copy has precedence.",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "owner_decisions": {
            "160": "COMP-1 and G5 fly in ONE campaign with ONE shared in-chain A/A, on the condition that the shared A/A is byte-identical to what each arm is read against (the precedent)",
            "161": "AGREE retained; later items derive from the retained AGREE arm",
            "164": "the knowledge wave W1 -> W2 -> W3 -> W4, each W cell derived from the retained AGREE arm with ONE change, the arms read against ONE shared in-chain A/A of the AGREE arm's own bytes (row 160's precedent)",
        },
        "rows": 1080,
        "stage3_measurement": measurement,
        "the_cell": {
            "what": "the retained AGREE arm's own bytes re-flown under the A/A's own run, attempt and FIT ids; nothing in any request moves",
            "readers": {name: {"run_id": arm["run_id"], "package": arm["package"], "read_run_id": arm["read"]} for name, arm in WAVE_ARMS.items()},
            "readers_note": arms_line,
            "where_it_flies": f"step 1 of scripts/flights/wave/batch_chain_wave.sh, inside the wave campaign plan {WAVE_CAMPAIGN} = [this A/A, the W1 arm], after the W1 four-row smoke; W3 and W4 fly as steps 2 and 3 of the same chain on the same resident session {SESSION}",
            "why_no_smoke": "the AGREE and COMP-1 A/A cells carried none: the A/A is the AGREE arm's already-flown form, and the chain smokes W1 before anything is spent",
        },
        "byte_identity": {
            "claim": "the A/A's composed config differs from the AGREE arm's only in bookkeeping and the dropped supply pin; its prepared first-phase supply must carry the AGREE arm's output digest; its request bytes must equal the AGREE arm's",
            "expected_supply_output_sha256": SUPPLY_OUTPUT_SHA,
            "proof": proof,
        },
        "fit": {"rule": "the pre-flight prompt budget binds to the LIVE slot (24,576 tokens, np4) with a reserve of one eighth; the A/A is the AGREE arm's form, whose Solver phase reads COMPACT_REQUIRED with a positive physical margin and proceeds under context_fit_policy compact-or-abstain", "measured": fit},
        "identity": {k: v for k, v in ids.items() if k != "composed_config_diff_against_the_agree_arm"},
        "composed_config_diff_against_the_agree_arm": ids["composed_config_diff_against_the_agree_arm"],
        "comparator": {"run_id": AGREE_RUN, "attempt_id": AGREE_ATTEMPT, "official": AGREE_OFFICIAL, "never_reflown": True,
                       "role": "the sealed source of the A/A's bytes; context for the offset read"},
        "read_rule": read_rule,
        "budget_arithmetic": {
            "family_budget": caps,
            "derivation": [
                "generation_calls_cap = 1,080 x 11 (perception 1, solver 1, reviewer 3, planner 1, max_revisions 1 -> 1 + 2 x (3 + 1 + 1)) = 11,880",
                "fit_endpoint_calls_cap = 4 x generation = 47,520; native_task_contract_calls_cap 6,480; repeated_speech_audio_seconds_cap 33,930; gpu_hours_fit_inclusive 12.0: the AGREE family's own ceilings",
                "expected spend at the sealed AGREE arm's own rate: about 4,385 contacts, about 1.9 GPU hours",
                "official_complete_scoring_jobs = 1 through core.scoring_batch, never sharded",
            ],
            "run_cumulative": "every cap binds across ALL attempts of a run id",
        },
        "prohibitions": [
            "Never reported as a gain or as a result of its own: it is the instrument.",
            "No test-split, Fold B or DEV contact or read.",
            "No re-flying of the sealed AGREE arm under its own run id.",
            "No change of any kind against the AGREE arm's bytes.",
            "No paper-scale profile.",
            "No flight before root mints the decision receipt and the cell is flipped, and never outside the wave chain.",
        ],
        "authority_relpaths": [OWNER_DECISIONS, INSTRUMENT, AGREE_PACKAGE + "/README.md", COMP1_PACKAGE + "/README.md", GATE],
    }
    facts_sha = wjson(PACKAGE + "/registered-facts-v1.json", facts)

    protocol = {
        "schema": "saea-registered-protocol-v1",
        "protocol_id": "slurp-stage3-wave1-aa-fold-a-protocol-v1",
        "registered_at_utc": args.registered_at,
        "study_commit_at_registration": args.study_commit,
        "source_tree": f"studies/speech-aware-evidence-acquisition, worktree {args.worktree}, branch {args.branch}",
        "status": "REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_READINESS_FLIP",
        "the_question": "None of its own: the A/A is the within-chain null the knowledge wave's arms are read at (owner decision 164).",
        "one_factor": "none: the retained AGREE arm's bytes, re-flown",
        "unchanged": (
            f"everything: the roster (TRAIN Fold A 1,080, split identity {ids['split_identity_hash']}), the model fragment and "
            f"serving geometry (np4 x 24,576), the session {SESSION}, the program and its 11-contact ceiling, all three stores "
            "and their pins, the agreement term (w_agree 1.0, recall k 60, delivered width 8), the exemplar k of 20, the card "
            "route's caps (3 / 16 / 28), the role graph, every template, the deliver normaliser, the scorers and every budget"
        ),
        "cells": {"aa": {k: ids[k] for k in ("cell", "experiment", "run_id", "attempt_id", "rows", "composed_config_hash", "protocol_hash", "split_identity_hash")}
                  | {"fit_run_id": ids["fit"]["run_id"], "fit_attempt_id": ids["fit"]["attempt_id"]}},
        "comparator": facts["comparator"],
        "readers": facts["the_cell"]["readers"],
        "read_rule_fixed_here": read_rule,
        "development_numbers_only": "TRAIN Fold A construction-fold development numbers (owner decisions 28 and 86); never a test claim.",
        "failure_policy": "Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. The budget is run-cumulative across attempts. A failed A/A stops the wave chain: no wave arm is read without it.",
        "prohibitions": facts["prohibitions"],
    }
    protocol_sha = wjson(PACKAGE + "/protocol-registered-v1.json", protocol)

    plan_shas: dict[str, str] = {}
    for kind in ("generation", "fit"):
        is_fit = kind == "fit"
        run_id = ids["fit"]["run_id"] if is_fit else ids["run_id"]
        plan_doc = {
            "schema": f"saea-registered-{kind}-plan-v1",
            "plan_kind": kind,
            "cell": ids["cell"],
            "experiment": ids["experiment"],
            "composed_config_hash": ids["composed_config_hash"],
            "registered_at_utc": args.registered_at,
            "status": protocol["status"],
            "source_tree": protocol["source_tree"],
            "preparation_base_commit": args.study_commit,
            "expected_session_id": SESSION,
            "unused_budget_is_not_attempt_authority": True,
            "execution_plan": {
                "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
                "carrier_lock_key": ids["carrier_lock_key"], "run_id": run_id,
                "attempt_id": ids["fit"]["attempt_id"] if is_fit else ids["attempt_id"],
                "execution_profile": ids["execution_profile"], "split_role": "discovery",
                "split_identity_hash": ids["split_identity_hash"], "protocol_hash": ids["protocol_hash"],
                "planned_model_calls": caps["fit_endpoint_calls_cap"] if is_fit else caps["generation_calls_cap"],
                "planned_speech_audio_seconds": caps["repeated_speech_audio_seconds_cap"],
                "planned_gpu_hours": caps["gpu_hours_fit_inclusive"],
            },
            "family_budget": caps,
            "execution_route": (
                "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; it measures request envelopes and produces no generation."
                if is_fit else
                f"Shared core.flight.cli campaign: {WAVE_CAMPAIGN} carries [this A/A, the W1 arm]; W3 and W4 fly as the later steps of the same chain (scripts/flights/wave/batch_chain_wave.sh); one official score at finalize."
            ),
            "prepared_phase_supply": {
                "relpath": f"prepared/{ids['run_id']}/phase-supply-v1.json",
                "sha256": "MINTED_AT_THE_FLIP",
                "expected_output_sha256": SUPPLY_OUTPUT_SHA,
                "note": "the flip mints this cell's own supply under its own run id (item E16); a different output digest means the Perception channel moved -- stop and report",
            },
            "protocol_document": {"relpath": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "one_factor": protocol["one_factor"],
            "purpose": f"{run_id}: the knowledge wave's shared in-chain A/A. " + (
                "It measures request envelopes only and reads nothing." if is_fit else read_rule),
            "quality_read_gate": "No task-quality read before the complete sealed manifest, the exact ordered outputs, the native phase summary and the single successful complete official TRAIN score all exist for this A/A and for the arm being read.",
        }
        plan_shas[run_id] = wjson(f"{PACKAGE}/{kind}-plan-registered-v1.json", plan_doc)

    recipe = {
        "schema": "saea-slurp-paired-analysis-recipe-v1",
        "recipe_id": "slurp-stage3-wave1-aa-fold-a-paired-read-v1",
        "title": "The knowledge wave's shared A/A -- the cross-flight offset read (sealed AGREE arm vs the wave A/A), context for W1, W3 and W4",
        "registered_at_utc": args.registered_at,
        "read_run_id": READ_ROW,
        "run_ids": {"read": READ_ROW, "arm": AA_RUN, "in_chain_replicate": AGREE_RUN},
        "arms": {
            "arm": {"run_id": AA_RUN, "attempt_id": ids["attempt_id"], "run_manifest_sha256": "PENDING_SEAL", "scores_sha256": "PENDING_SEAL", "outputs_sha256": "PENDING_SEAL"},
            "in_chain_replicate": {"run_id": AGREE_RUN, "attempt_id": AGREE_ATTEMPT,
                                   "role": "the SEALED request-identical source of the A/A's bytes (not flown in this chain): the pass vs-aa of scripts/flights/read_paired_cell.sh then reads the A/A minus AGREE delta, which is the cross-flight offset"},
        },
        "readers": facts["the_cell"]["readers"],
        "resampling": {"bootstrap_draws": 10000, "metrics": ["scenario_action_exact", "slu_f1_f1"], "seed": 20260927, "unit": "row (paired)"},
        "decision_rule": read_rule,
        "margins": {"h_intent": H_INTENT, "h_slu": H_SLU},
        "steps": [
            "1. Refuse unless the A/A carries a COMPLETE sealed manifest at 1,080 rows with the committed roster's ids and one successful complete official TRAIN score.",
            "2. Structural stage: the A/A's prepared first-phase supply output digest equals " + SUPPLY_OUTPUT_SHA + "; the per-phase contact counts against the sealed AGREE arm.",
            "3. Paired row bootstrap (10,000 draws, seed 20260927) of the A/A minus AGREE delta on intent accuracy and official pooled SLU-F1, point and CI95, both weightings: the cross-flight offset, reported beside the own-null half-widths.",
            "4. Report only; no admission, no gain, no gate on the arm reads. Each arm read (W1, W3, W4) uses THIS A/A as its in-chain replicate.",
        ],
        "read_driver": "scripts/flights/wave/wave_read.sh (a thin wrapper over scripts/flights/read_paired_cell.sh)",
        "output": {"analysis_root": f"analysis/{READ_ROW}"},
        "boundary": "A development read on a TRAIN construction fold (owner decisions 28 and 86); never a test claim. No utterance text, transcript, gold filler or model output is printed or persisted.",
    }
    recipe_sha = wjson(PACKAGE + "/analysis-recipe-v1.json", recipe)

    eligible = [ids["run_id"], ids["fit"]["run_id"]]
    draft = {
        "_draft_note": "A DRAFT for root to mint on the data root with scripts/flights/wave/wave_mint_receipt.py (status decided, recorded_at_utc stamped, antecedents re-hashed, never overwrites). It authorises nothing while its status is not 'decided'.",
        "schema": "saea-campaign-decision-v1",
        "decision_id": DECISION_ID,
        "status": "DRAFT-NOT-MINTED",
        "recorded_at_utc": None,
        "owner": "root",
        "coordinator": "Fable5.1",
        "eligible_run_ids": eligible,
        "cell_kind": "Stage-3 in-chain A/A replicate (label none): the retained AGREE arm's own bytes, the shared within-chain null of the knowledge wave's arms W1, W3 and W4.",
        "decision": "Fly the knowledge wave's shared in-chain A/A in step 1 of the wave chain beside the W1 arm, W3 and W4 following in the same chain, each arm read at it.",
        "authorization_basis": f"Owner decision 164 (the knowledge wave, one shared in-chain A/A of the AGREE arm's own bytes), 160 (the shared-A/A precedent), 161 (AGREE retained); standing: 25, 28, 77, 86, 101, and {INSTRUMENT}.",
        "antecedents": {
            "owner_decisions": {"path": OWNER_DECISIONS, "sha256": sha_file(OWNER_DECISIONS)},
            "instrument_note": {"path": INSTRUMENT, "sha256": sha_file(INSTRUMENT)},
            "preregistration": {"path": PREREG, "sha256": None},
            "readiness_readme": {"path": PACKAGE + "/README.md", "sha256": None},
            "protocol": {"path": PACKAGE + "/protocol-registered-v1.json", "sha256": protocol_sha},
            "registered_facts": {"path": PACKAGE + "/registered-facts-v1.json", "sha256": facts_sha},
            "analysis_recipe": {"path": PACKAGE + "/analysis-recipe-v1.json", "sha256": recipe_sha},
            "shared_aa_proof": {"path": PROOF, "sha256": sha_file(PROOF) if Path(PROOF).is_file() else None},
            "base_cell": f"the retained AGREE arm ({AGREE_RUN}, decision 161): the A/A is that fragment re-flown",
            "registration_base_commit": args.study_commit,
        },
        "budget": {**{k: caps[k] for k in sorted(caps)}, "paid_api_calls": 0, "expected_contacts_per_1080_row_cell": AGREE_OFFICIAL["calls_used"], "plan_budget_is_run_cumulative": True},
        "claim_boundary": "No claim of any kind: an instrument cell.",
        "failure_policy": protocol["failure_policy"],
        "not_authorized": [
            "any flight before the cell is flipped and the receipt is minted",
            "flying the A/A outside the wave chain",
            "touching the resident np4 session by anyone but the coordinator",
            "any ASR, transcript, encoder or paid-API contact",
            "re-flying or re-scoring any sealed cell",
            "--allow-output-change on the re-pin tool",
            "any change against the AGREE arm's bytes",
        ],
        "population": {"count": 1080, "split_identity_hash": ids["split_identity_hash"], "split_role": "discovery", "partition": "TRAIN Fold A 1,080", "fold_b_contact_authorized": False, "test_contact_authorized": False},
        "prepared_phase_supply": {"note": f"minted by scripts/flights/repin_cell.py at the flip (item E16); expected output digest {SUPPLY_OUTPUT_SHA}"},
        "registered_hashes": {"aa": {"composed_config": ids["composed_config_hash"], "protocol": ids["protocol_hash"]}},
        "service": {"expected_session_id": SESSION, "model_fragment": ids["model_fragment"], "slots": 4, "slot_tokens": 24576, "note": "the resident SLURP np4 session; the flight attaches only"},
    }
    draft_sha = wjson(PACKAGE + "/root-admission-draft-v1.json", draft)

    fit_line = "PENDING (run core.flight.cli check, then re-run this writer with --check-dir)"
    if fit["status"] == "MEASURED_BY_CHECK":
        fit_line = "; ".join(
            f"{p['phase']} {p['decision']} rendered {p['rendered_text_tokens']:,} physical margin {p['physical_margin_tokens']:,}"
            for p in fit["prompt_budget_per_phase"]
        ) + f" (readiness {(fit['scientific_readiness'] or {}).get('state')}, blockers {fit['blockers']})"
    proof_line = "PENDING (run " + PROOF_SCRIPT + ")"
    if proof["status"] != "PENDING_PROOF":
        proof_line = (
            f"**{proof['verdict']}** at study commit `{proof['study_commit'][:8]}` -- composed-config classes "
            f"{json.dumps(proof['config_classes'], sort_keys=True)}; prepared supply output digests A/A `{proof['supply_output_sha256']['wave_aa'][:8]}` "
            f"and AGREE `{proof['supply_output_sha256']['agree_arm'][:8]}` (equal to the registered digest and to the AGREE arm's committed "
            f"artifact: {proof['supply_equal_registered_and_committed']}); request bytes over the first {proof['rows_dispatched']} rows, "
            f"{proof['contacts_compared']} contacts: payload and POST body identical under one run id {proof['common_run_id_payload_and_body_identical']}, "
            f"POST body identical under own run ids {proof['own_run_ids_body_identical']}"
        )
    fence = json.dumps({"stage3_measurement": measurement}, indent=2, ensure_ascii=False, sort_keys=True)
    readers_table = "\n".join(
        f"| {name} | `{arm['run_id']}` | `{Path(arm['package']).name}` | `{arm['read']}` |" for name, arm in WAVE_ARMS.items()
    )
    readme = f"""# The knowledge wave's shared in-chain A/A (owner decision 164)

Registered before contact {args.registered_at[:10]} at study commit `{args.study_commit}`; the cell is **held**.
Nothing here authorises a flight, a flip or an admission entry.

**What it is.** `{AA_RUN}`: the retained AGREE arm `{AGREE_RUN}` (intent {AGREE_OFFICIAL['intent_accuracy']} /
SLU {AGREE_OFFICIAL['slu_f1']}, decision 161) re-flown byte for byte under its own run, attempt and FIT ids. Decision 164
reads the knowledge wave's arms "against ONE shared in-chain A/A of the AGREE arm's own bytes (row 160's
precedent)"; this is that cell. Derived by `{DERIVE_SCRIPT}` (decision 58): the only differences from the AGREE
fragments are per-flight bookkeeping and the dropped `prepared_phase_supply` pin (item E16: the flip mints this
cell's own, which must carry the AGREE output digest `{SUPPLY_OUTPUT_SHA[:8]}...`).

**Byte identity** (`{PROOF_SCRIPT}`, the decision-160 proof pointed at the pair (wave A/A, AGREE arm), model-free):
{proof_line}. Receipt: [`shared-aa-proof-v1.json`](shared-aa-proof-v1.json).

**Who reads at it.**

| arm | run id | package | READ row |
| --- | --- | --- | --- |
{readers_table}

**Where it flies.** Step 1 of `scripts/flights/wave/batch_chain_wave.sh`: the W1 four-row smoke, then the wave
campaign plan `{WAVE_CAMPAIGN}` = [this A/A, the W1 arm]; W3 (step 2) and W4 (step 3) follow in the same chain on
the same resident session `{SESSION}` -- the COMP-1 + G5 shape of decision 160. No smoke of its own (the AGREE and
COMP-1 A/As carried none).

**Fit.** {fit_line}.

**`stage3_measurement`.** `cross-flight-with-in-chain-replicate`, `expected_effect_pp` 0.0, `claims_benefit` false,
`replicate_run_id` `{AGREE_RUN}` (the sealed request-identical source of its bytes). It is the instrument.
Its own READ `{READ_ROW}` reports the cross-flight offset (A/A minus AGREE) as context only.

| file | what it holds |
| --- | --- |
| `../{Path(PREREG).name}` | the preregistration, including the `stage3_measurement` fence |
| `registered-facts-v1.json` | every model-free fact, the composed diff, the CANONICAL `stage3_measurement` |
| `protocol-registered-v1.json` | identities, hashes, the read rule |
| `generation-plan-registered-v1.json` / `fit-plan-registered-v1.json` | the A/A's plans |
| `analysis-recipe-v1.json` | the offset read, READ run id `{READ_ROW}` |
| `shared-aa-proof-v1.json` | the byte-identity proof against the AGREE arm |
| `root-admission-draft-v1.json` | the receipt root mints with `scripts/flights/wave/wave_mint_receipt.py` |

**Mint, flip, queue.** Root countersigns the A/A's two DRAFT flight rows (`{AA_RUN}`, `{ids['fit']['run_id']}`; the READ
row `{READ_ROW}` may stay DRAFT until the seal) together with the W1, W3 and W4 rows, mints `{DECISION_RELPATH}` (id
`{DECISION_ID}`, two eligible run ids) with `scripts/flights/wave/wave_mint_receipt.py` and the three arm receipts
with their own mint scripts, flips everything with `scripts/flights/wave/wave_flip.sh` (converged at ONE HEAD, which
becomes the flight commit), and queues `scripts/flights/wave/batch_chain_wave.sh`. `--allow-output-change` is never
passed.
"""
    readme_sha = wr(PACKAGE + "/README.md", readme)

    prereg = f"""# The knowledge wave's shared in-chain A/A: preregistration

Registered {args.registered_at[:10]} at study commit `{args.study_commit}`, before any contact, from the retained AGREE
fragments by script (`{DERIVE_SCRIPT}`, decision 58), under owner decisions 160, 161 and 164. Development numbers only
(owner decisions 28 and 86); never a test claim.

| item | value |
| --- | --- |
| base | the retained AGREE arm `{AGREE_RUN}` (intent {AGREE_OFFICIAL['intent_accuracy']} / SLU {AGREE_OFFICIAL['slu_f1']}), sealed, never re-flown |
| factor | none: the AGREE arm's own bytes |
| readers | {arms_line} |
| runs | `{ids['run_id']}` / `{ids['fit']['run_id']}`; READ `{READ_ROW}` |
| composed config hash | `{ids['composed_config_hash']}` |
| protocol hash | `{ids['protocol_hash']}` |
| split identity | `{ids['split_identity_hash']}` |
| expected first-phase supply output | `{SUPPLY_OUTPUT_SHA}` |

## Read rule (fixed here)

{read_rule}

## The measurement declaration

```json
{fence}
```

## Budgets and failure rule

{caps['generation_calls_cap']:,} generation contacts (run-cumulative), {caps['fit_endpoint_calls_cap']:,} FIT endpoints, {caps['repeated_speech_audio_seconds_cap']:,}
repeated speech seconds, {caps['gpu_hours_fit_inclusive']} GPU hours, one official complete score. Expected about 4,385 contacts at the AGREE
arm's rate. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. A failed A/A
stops the wave chain.

## Prohibitions

Never reported as a gain or as a result of its own. No paper-scale profile, no test-split, Fold B or DEV contact, no
comparator re-flight, no change against the AGREE arm's bytes, no flight before root mints the receipt and the cell is
flipped, and `--allow-output-change` is never passed.
"""
    prereg_sha = wr(PREREG, prereg)

    ledger_state = append_ledger(args, ids=ids, plan_shas=plan_shas) if args.append_ledger else "not-requested"
    print(json.dumps({
        "package": PACKAGE, "exposure_ledger": ledger_state, "fit": fit["status"], "proof": proof["status"],
        "written": {"README.md": readme_sha, "registered-facts-v1.json": facts_sha, "protocol-registered-v1.json": protocol_sha,
                    "analysis-recipe-v1.json": recipe_sha, "root-admission-draft-v1.json": draft_sha, Path(PREREG).name: prereg_sha,
                    **{f"plan[{run}]": sha for run, sha in plan_shas.items()}},
        "identity": {"run_id": ids["run_id"], "composed_config_hash": ids["composed_config_hash"], "protocol_hash": ids["protocol_hash"],
                     "diff": ids["composed_config_diff_against_the_agree_arm"]["by_class"]},
    }, indent=2, sort_keys=True))
    return 0


MODEL_TOOL = (
    "Frozen Q4_K_M decoder-only c98304 np4 max512; promoted EVO-FOLDS-V2 speech packets; NO native tool authority on any "
    "role; prompt bytes the retained AGREE arm's, unchanged"
)
INHERITED = (
    "TRAIN Fold A discovery rows already exposed by the sealed anchor, cells B0 through PLANr, ROLL-2, CONV, the AGREE family, "
    "KPROBE, COMP-1 and G5 (flown or in flight at registration); this cell adds no new row to the fold and opens no split. "
    "Prior exposure is inherited in full."
)


def append_ledger(args, *, ids, plan_shas) -> str:
    """Three DRAFT rows. Idempotent: replace-or-append by run id. No cell may contain a literal '|'."""

    text = rd(LEDGER)
    eligible = [ids["run_id"], ids["fit"]["run_id"]]
    arms = ", ".join(f"{name} {arm['run_id']}" for name, arm in WAVE_ARMS.items())

    def flight_row(kind: str) -> str:
        is_fit = kind == "fit"
        budget = ids["family_budget"]
        run_id = ids["fit"]["run_id"] if is_fit else ids["run_id"]
        attempt = ids["fit"]["attempt_id"] if is_fit else ids["attempt_id"]
        notes = (
            f"REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending) {args.registered_at[:10]} at study commit {args.study_commit} "
            f"by the wave A/A registration agent (worktree {args.worktree}, branch {args.branch}). This registration performs no contact and "
            f"authorises none. Plan SHA256 {plan_shas[run_id]}; attempt {attempt}. Protocol hash {ids['protocol_hash']}; composed config "
            f"{ids['composed_config_hash']}; expected session {SESSION} (attach only). READINESS HELD: root mints {DECISION_RELPATH} "
            f"(decision id {DECISION_ID}) from the package's root-admission-draft-v1.json with the two eligible run ids {', '.join(eligible)}, "
            "then re-pins with scripts/flights/repin_cell.py --set-ready through scripts/flights/wave/wave_flip.sh, which mints the cell's "
            f"OWN first-phase supply (item E16; expected output digest {SUPPLY_OUTPUT_SHA}); --allow-output-change must never be passed. "
            "Every hash in this row moves at the flip and the re-pin tool rewrites it. ZERO CHANGE (owner decision 164): the retained AGREE "
            f"arm's own bytes, the shared in-chain A/A the wave arms are read at ({arms}); byte identity proven model-free by "
            f"{PROOF_SCRIPT}. Measurement declaration ({GATE}): measurement_design cross-flight-with-in-chain-replicate, expected_effect_pp "
            f"0.0, claims_benefit false, replicate_run_id {AGREE_RUN}, rows 1080 -- canonical in {PACKAGE}/registered-facts-v1.json. "
            "Caps are the AGREE arithmetic. Stop and preserve on the first failure; AT MOST ONE root-diagnosed recovery re-registration. "
            "No paper-scale profile, no test-split contact, no comparator re-flight and no admission entry from this row."
        )
        scope = "The knowledge wave's shared in-chain A/A" + (" -- FIT spend identity, request envelopes only, no generation" if is_fit else "") + (
            ": the retained AGREE arm's own bytes re-flown in the wave chain as the within-chain null of W1, W3 and W4 (owner decision 164)")
        cells = ["", args.registered_at, run_id, "bounded-discovery-probe", scope, MODEL_TOOL,
                 f"slurp TRAIN Fold A {ids['rows']}", "discovery", ids["split_identity_hash"], "no",
                 str(budget["fit_endpoint_calls_cap"] if is_fit else budget["generation_calls_cap"]),
                 str(budget["repeated_speech_audio_seconds_cap"]), str(budget["gpu_hours_fit_inclusive"]), INHERITED,
                 f"{PACKAGE}/{kind}-plan-registered-v1.json", notes, ""]
        return " | ".join(cells).strip()

    read_row = " | ".join([
        "", args.registered_at, READ_ROW, "model-free-check",
        f"The wave A/A's own read: the cross-flight offset of {AA_RUN} against the sealed AGREE arm {AGREE_RUN} (its request-identical source) on intent accuracy and official pooled SLU-F1, paired row bootstrap, both weightings, beside the own-null half-widths (intent {H_INTENT} / SLU {H_SLU}); context for the W1, W3 and W4 reads, never a gate and never a claim.",
        "No model, tokenizer, encoder or server contact: scripts/flights/wave/wave_read.sh -> scripts/flights/read_paired_cell.sh over the sealed per-sample official scores.",
        "slurp TRAIN Fold A 1080", "discovery", ids["split_identity_hash"], "no", "0", "0", "0.0",
        "Reads only sealed manifests of this package and the sealed AGREE arm; no new audio, gold or reference exposure.",
        f"{PACKAGE}/analysis-recipe-v1.json",
        "REGISTERED BEFORE CONTACT (DRAFT, root countersignature pending; countersigned after the seal and before any number is read). No utterance text, gold, transcript or model output is printed or persisted.",
        "",
    ]).strip()

    fresh = {ids["run_id"]: flight_row("generation"), ids["fit"]["run_id"]: flight_row("fit"), READ_ROW: read_row}
    for run_id, line in fresh.items():
        if len(line.split("|")) != 17:
            raise SystemExit(f"ledger row {run_id} does not have exactly fifteen cells; a literal '|' slipped into a cell")
    order = list(fresh)
    lines = text.split("\n")
    replaced = 0
    for index, line in enumerate(lines):
        if line.startswith("|") and len(line.split("|")) > 3 and line.split("|")[2].strip() in fresh:
            lines[index] = fresh.pop(line.split("|")[2].strip())
            replaced += 1
    if replaced and fresh:
        raise SystemExit("the ledger carries some but not all wave A/A rows; refusing to guess")
    if replaced:
        wr(LEDGER, "\n".join(lines))
        return f"replaced-{replaced}"
    header = (
        "\n## The knowledge wave's shared in-chain A/A (owner decision 164) -- the A/A, its FIT identity and its READ row "
        "(DRAFT, root countersignature pending)\n\n"
        "Two unconsumed flight rows -- the shared in-chain A/A of the retained AGREE arm's own bytes and its FIT spend identity -- "
        f"and the A/A's own READ row. The wave arms W1, W3 and W4 are each read at {AA_RUN} (decision 164; the decision-160 "
        "precedent). None of these rows is countersigned and none authorises a contact.\n\n"
        "| date | run/experiment id | execution profile | scope | model/tool | speech carrier + split | split role | "
        "split identity hash | consumed | calls | speech audio seconds | gpu hours | inherited exposure | artifacts | notes |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
    )
    suffix = "" if text.endswith("\n") else "\n"
    wr(LEDGER, text + suffix + header + "\n".join(fresh[run_id] for run_id in order) + "\n")
    return "appended"


if __name__ == "__main__":
    raise SystemExit(main())
