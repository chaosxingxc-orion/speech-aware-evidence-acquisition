#!/usr/bin/env python3
"""Write the DRAFT readiness package of the CONSTRUCTION-SOURCE lock column, from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed
(the coordinator's act, or the DRAFT block the registering agent appends at the END of the ledger). Every file says DRAFT / HELD.

ONE package ``docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/`` (README, ``registered-facts-v1.json`` with the CANONICAL
``stage3_measurement`` blocks keyed by run id, ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
``root-admission-draft-v1.json``, ``draft-ledger-rows.md``) and, beside it, the preregistration. The column is the proposer / reflector
MATERIAL SOURCE for iterations 1-3 of the typed loop: ``measurement_design`` ``material-source``, ``claims_benefit`` false.

    python -B scripts/flights/tfrl/write_tfrl_construction_registration.py --study-commit <sha> --registered-at 2026-10-11T12:00:00.000000+00:00
        [--root DIR] [--data-root DIR] [--append-ledger]
"""

from __future__ import annotations
import os

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import derive_tfrl_construction_cells as dc  # noqa: E402
import derive_tfrl_iteration_cells as dv  # noqa: E402
import tfrl_family as tf  # noqa: E402
import write_tfrl_iteration_registration as reg  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters import slurp_module_construction as vc  # noqa: E402

DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
STATUS = reg.STATUS
POOL_REMEDY = {
    "release": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/release.json",
    "release_sha256": "83620eb0b02f12424a00cd5572904f4df48a49c329b1b0e1a9321d4b9ec14fd0",
    "snapshot": "knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json",
    "snapshot_sha256": "6eaa03aea96a1928dd1ac29ecc71c3955c136498c9f8114266eaa830d1207c63",
    "source_ids": 34474, "shared_with_r01c": 0,
}
PROHIBITIONS = [
    "No Fold B, Fold A, DEV or test contact: the column flies the construction roster R01C only.",
    "No supply arm, no template column, no tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No benefit claim and no admission: the column is the loop's material source (measurement design material-source).",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "The construction variant of the lock (consumption_module.construction_roster r01c) exists only to flow this column without "
    "self-leakage; it never delivers a benefit claim.",
    "No paper-scale profile. No system-level claim.",
]


def identities(root: Path) -> dict:
    out = {}
    for kind in ("arm", "smoke"):
        n = tf.const_names(kind)
        document = json.loads((Path(root) / "configs" / "experiment" / f"{n['experiment']}.json").read_text(encoding="utf-8"))
        cell = document["cells"][0]
        composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], n["experiment"])
        split = document["population"]["split_identity_hash"]
        out[kind] = {
            "experiment": n["experiment"], "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": n["fit_run_id"], "fit_attempt_id": n["fit_attempt_id"], "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"], "arm": composed.values["arm"],
            "rows": document["population"]["count"], "split_identity_hash": split,
            "roster_receipt": document["population"].get("roster_receipt"), "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values.get("native_contact_fit") or {}), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"],
        }
    return out


def measurement_blocks(ids: Mapping[str, Mapping]) -> dict:
    arm, smoke = ids["arm"], ids["smoke"]
    return {
        arm["run_id"]: {
            "measurement_design": "material-source", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": tf.CONST_ROWS,
            "primary_metric": "none (collection column; read offline as the typed loop's proposer and reflector material)",
            "read_roster": tf.CONST_ROSTER_ID, "tuning_roster": "none",
            "note": ("The plain lock on the construction roster R01C: the column's per-row official scores feed the contrast tables the typed "
                     "proposer and the ACE reflector read in iterations 1-3. No contrast, twin or benefit claim; re-flown only if the lock "
                     "changes."),
        },
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": tf.SMOKE_ROWS,
            "primary_metric": "none (structural form only)", "read_roster": tf.CONST_ROSTER_ID, "tuning_roster": "none",
            "note": (f"Four R01C rows prove FORM only: the {arm['program']} program loads on R01C rows, the sealed speech vectors and packets "
                     "resolve and the episode completes. Scored by no one, read by no one."),
        },
    }


def draft_rows(ids: Mapping[str, Mapping], commit: str, at: str, pkg: str, shas: Mapping[str, str]) -> str:
    cols = ["date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split", "split role",
            "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes"]
    scope = (f"DRAFT -- REGISTERED. Frozen core, np4 session; the plain review-off COMP-1b module graph on lock {tf.CONST_LOCK} "
             f"(program {ids['arm']['program']}, 2 contacts per row, no supply arm, no column) on the CONSTRUCTION roster R01C; the typed "
             "loop's proposer / reflector material source; no tool authority on any role")
    inherited = ("TRAIN construction rows (R01C) already exposed by earlier SLURP cells (ROLL-1, VAR-1, VAR-2, ADV-1 and their smokes); this "
                 "cell opens no split. Prior exposure is inherited in full.")
    lines = [f"## Loop construction-source lock column (DRAFT, coordinator countersignature pending) -- {pkg}", "",
             "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for kind in ("arm", "smoke"):
        i = ids[kind]
        for fit in (False, True):
            plan = f"{pkg}/{'smoke-' if kind == 'smoke' else ''}{'fit' if fit else 'generation'}-plan-registered-v1.json"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            cells = [at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], scope + (" -- FIT spend identity" if fit else ""),
                     "frozen core (attach only)", f"slurp TRAIN R01C construction {i['rows']}", "discovery", i["split_identity_hash"], "no",
                     str(calls), str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]),
                     inherited, plan, f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."]
            lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    arm = ids["arm"]
    names = tf.const_names("arm")
    read = [at[:10], names["read_run_id"], "model-free-check",
            ("The offline read of the construction-source column: score the column once with the official scorer, then the loop's contrast "
             f"tables by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
            "no model or tool contact; read of sealed bytes and one CPU official scoring over derived copies",
            f"slurp TRAIN R01C construction {arm['rows']}, the sealed column (after the seal)", "discovery", arm["split_identity_hash"], "no",
            "0", "0", "0", inherited, f"{pkg}/analysis-recipe-v1.json",
            f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the seal and before any column is opened) "
            f"{at[:10]} at study commit {commit}. It admits nothing and claims no benefit."]
    lines.append("| " + " | ".join(c.replace("|", "/") for c in read) + " |")
    agree = [at[:10], dc.AGREEMENT_ID, "model-free-check",
             ("BUILT (model-free). The pre-computed, self-excluded exemplar-intent AGREEMENT table for the construction roster R01C, the vote table the "
              f"construction-source column's boundary channel ranks with (baseline {arm['baseline_fragment']}, agreement_source "
              "tool_contact_ledger_row = this row id): arithmetic over the pinned MINUS-R01 exemplar snapshot (consumption_module.construction_roster "
              "r01c; snapshot sha256 " + vc.MINUS_R01_POOL_SNAPSHOT["sha256"] + "), the pinned pool key vectors and the roster's "
              "pinned speech query vectors (content dimension, vectors/slurp-stage3-construction-r01c-v1/query-vectors-speech-content-v1.jsonl), "
              "through the repository's own recall/rank/fuse, exactly as SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1 was built "
              "(comparator cell slurp-native-stage3-var2-supply-variants-r01c-v1, which pins the same pool and declares no agreement_source). "
              "Measured: 625 rows, every row 20 votes, 0 self-excluded exemplars, 0 rows without a vote, 59 facets voted for; its 400 rows "
              "shared with SAEA-SLURP-KNOWLEDGE-OPPORTUNITY-R01C-AGREEMENT-V1 are byte-identical. reads_labels "
              "false. Zero model, server, encoder, embedder, scorer, network, GPU and paid-API contacts."),
             "no model or tool contact; local arithmetic over receipt-pinned files (scripts/build_slurp_intent_exemplar_agreement.py)",
             "slurp TRAIN R01C construction 625", "discovery", arm["split_identity_hash"], "no", "0", "0", "0.0",
             "No new speech exposure: every vector read was sealed by SAEA-SLURP-STAGE3-CONSTRUCTION-R01-SPEECH-QUERY-ENCODING-V1 and its model-free "
             "selection. No gold label, annotation or reference transcript of any R01C row is opened.",
             f"prepared/{dc.AGREEMENT_ID}/agreement.jsonl (sha256 {vc.R01C_AGREEMENT['sha256']}); prepared/{dc.AGREEMENT_ID}/receipt.json "
             f"(sha256 {vc.R01C_AGREEMENT_RECEIPT_SHA256})",
             f"DRAFT. BUILT by an agent 2026-10-12 (root countersignature pending). Write-once; authorises no flight, no "
             f"scoring and no readiness flip. Registered {at[:10]} at study commit {commit}."]
    lines.append("| " + " | ".join(c.replace("|", "/") for c in agree) + " |")
    return "\n".join(lines) + "\n"


def write_package(root: Path, commit: str, at: str, *, data_root: Path | None = None, append_ledger: bool = False,
                  derive: bool = True) -> dict:
    root = Path(root)
    derived = dc.derive(repo_root=root) if derive else {"cells": {"arm": {"loader_verification": {"ok": True}}}}
    loader = derived["cells"]["arm"]["loader_verification"]
    pkg = tf.CONST_PACKAGE_DIR
    ids = identities(root)
    arm, smoke = ids["arm"], ids["smoke"]
    names = tf.const_names("arm")
    guard = dc.knowledge_source_guard(data_root, root)
    blockers: list[dict[str, Any]] = []
    if not loader.get("ok", False):
        blockers.append({"id": "loader-refuses-the-derived-cell", "detail": loader.get("refusal"),
                         "remedy": "the derived cell does not verify under the real carrier hooks; fix the cell or the lock before any countersign"})
    if guard.get("measured") and guard.get("cell_conflict_rows", 0):
        blockers.append({
            "id": "knowledge-source-guard",
            "detail": ("rails/runner.py (run_speech_native_agent_loop) refuses a query sample inside the composite knowledge source roster, and "
                       "the cell's declared stores still share R01C rows. Measured: " + json.dumps(guard, sort_keys=True)),
            "remedy": "the construction variant must pin the minus-r01 pool (rails/adapters/slurp_module_construction.py)"})
    resolved = [
        {"id": "knowledge-source-guard",
         "was": ("the lock's train-exemplars pool release (size-pool-annotated-exemplars, 37,407 source ids) contained ALL 625 R01C rows, so the "
                 "runner's knowledge-source guard refused the cell before it dispatched one row (the committed VAR-2 R01C cell avoided it with "
                 "the minus-r01 pool)."),
         "resolution": ("a CONSTRUCTION VARIANT of the lock, not a new lock: the block names consumption_module.construction_roster r01c and "
                        "rails/adapters/slurp_module_construction.py moves the train-exemplars release and snapshot to the minus-r01 twins "
                        f"({POOL_REMEDY['source_ids']:,} source ids, {POOL_REMEDY['shared_with_r01c']} shared with R01C); the loader accepts it "
                        "only on R01C and the plain lock is refused on R01C with the guard's own message"),
         "measured_now": guard if guard.get("measured") else "data root unavailable at registration",
         "pool_remedy": POOL_REMEDY},
        {"id": "agreement-table-owed",
         "was": f"{dc.AGREEMENT_RELPATH} was a model-free preparation not yet built",
         "resolution": (f"built model-free by scripts/build_slurp_intent_exemplar_agreement.py against the minus-r01 pool snapshot "
                        f"({vc.R01C_AGREEMENT['relpath']}, sha256 {vc.R01C_AGREEMENT['sha256']}, receipt sha256 "
                        f"{vc.R01C_AGREEMENT_RECEIPT_SHA256}; 625 rows, 20 votes each, 0 self-excluded); its 400 rows shared with "
                        "SAEA-SLURP-KNOWLEDGE-OPPORTUNITY-R01C-AGREEMENT-V1 are byte-identical")},
        {"id": "ace-i0-anchor-sources-inside-r01c",
         "was": "the lock v2.3 ace-playbook i0 anchor row names 50 R01C source ids, so the guard would refuse the construction column on v2.3",
         "resolution": ("the column stays on lock v2.2: the preparer takes carriers from the permitted roster, a subset of the construction "
                        "scope, and the committed stage3-deltas-v1r scope IS R01C, so no anchor can be re-homed outside R01C; P-ACE-0 makes the "
                        "v2.2 and v2.3 requests byte-identical, and the construction variant refuses v2.3")},
        {"id": "ace-prior-score-outside-unit-interval",
         "was": "playbook_release_rows wrote prior_score = float(total - rank), which KnowledgeSnapshot.frozen_json refuses",
         "resolution": "rails/tfrl_ace_material.py now writes (total - rank) / total; the preparer accepts an i1 release with R01C carriers"}]
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id",
                                           "protocol_hash", "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "decision_rule_fixed_here": ("None: the column makes no decision. It is the material source of the typed loop; the selection rule, "
                                     f"parent choice, edit budget and stop rule are fixed in {tf.PROTOCOL_RELPATH}."),
        "arms": [tf.DELIVERING], "one_factor": f"none (the plain lock {tf.CONST_LOCK}, review-off, on the construction roster R01C)",
        "prohibitions": PROHIBITIONS, "protocol_id": "slurp-tfrl-construction-source-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": ("None: this column estimates nothing. Its official per-row scores are the sealed material the contrast tables are read "
                         "from (failure cube by slot type and scenario, empty-gold false fill, intent rank, supply structure)."),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration; run-cumulative budgets.",
        "blockers": blockers, "resolved_blockers": resolved}
    protocol_sha = reg.wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    route = {"arm": (f"Shared core.flight.cli campaign over {names['campaign']} through scripts/flights/tfrl/batch_chain_tfrl_const.sh and the "
                     "batch driver."),
             "smoke": "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."}
    purpose = {"arm": f"{arm['run_id']}: construction-source lock column (the typed loop's material source); no benefit claim.",
               "smoke": f"{smoke['run_id']}: structural form proof only: no score and no read."}
    plans = reg.plan_docs(root, ids, commit, at, protocol_sha, pkg, route, purpose)
    shas = {name: reg.wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": f"{reg.DESIGN} sections 3.3 and 5; the coordinator resolution of 2026-10-11 (construction source); {tf.PROTOCOL_RELPATH}",
        "cell_kind": "CONSTRUCTION-SOURCE COLUMN -- a collection column read offline; no contrast, no claim",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer job over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flight itself)",
        "measurement_design": "material-source", "read_run_id": names["read_run_id"], "recipe_id": names["recipe_id"], "registered_at_utc": at,
        "roster": {"relpath": tf.CONST_ROSTER["arm"], "roster_id": tf.CONST_ROSTER_ID, "rows": tf.CONST_ROWS,
                   "split_identity_hash": arm["split_identity_hash"]},
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": names["read_run_id"], "smoke": smoke["run_id"],
                    "smoke_fit": smoke["fit_run_id"]},
        "arms": {"order": [tf.DELIVERING], "delivering": tf.DELIVERING, "twin": None, "columns": {}},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_score": "one complete official scoring of the lock column (stage3_rollout_score.py or core.scoring_batch; never sharded) with "
                       "per-row official scores on disk",
            "2_tables": ("python -B scripts/analysis/tfrl_contrast_tables.py --run-id %s --attempt %s --arm lock --scorer %s --split train "
                         "--rows %d --data-root $SPEECHRL_DATA_DIR --lock $SAEA_DATASETS_LOCK --out-dir <analysis>/tables"
                         % (arm["run_id"], arm["attempt_id"], tf.CONST_SCORER, tf.CONST_ROWS)),
            "3_loop": "the loop driver's open --iter t reads these tables (propose stage) for t = 1, 2 and 3 (the lock does not change)"},
        "what_is_not_here": "No margins block, no paired read and no admission: nothing is selected or locked here."}
    shas["analysis-recipe-v1.json"] = reg.wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this DRAFT registration rests on, and the CANONICAL stage3_measurement blocks "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": {"program": arm["program"], "contacts_per_row": tf.CONST_CONTACTS, "lock": tf.CONST_LOCK, "rows": tf.CONST_ROWS,
                       "arm_generation_calls": arm["family_budget"]["generation_calls_cap"],
                       "smoke_generation_calls": smoke["family_budget"]["generation_calls_cap"],
                       "cost_estimate": {
                           "contacts": tf.CONST_ROWS * tf.CONST_CONTACTS,
                           "gpu_hours_expected": round(tf.CONST_MEASURED_GPU_H_PER_1000_ROWS * tf.CONST_ROWS / 1000.0, 3),
                           "gpu_hours_planned_cap": tf.CONST_PLANNED_GPU_HOURS_ARM,
                           "basis": ("review-off composed arm measured 1.38 GPU-h per 1,000 rows at 2.00 contacts per row "
                                     "(docs/results/2026-10-10-slurp-nx-r5-composed-dev2000-added-read.md); 0.285 GPU-h per contact-per-row at "
                                     "1,080 rows from the R1 i1 flight (design 5.2) gives 0.33 GPU-h as a lower bound")}},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "fit": {"status": "PENDING_CHECK", "frame": dict(tf.FIT_ESTIMATE)},
        "identity": ids, "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": (f"{reg.DESIGN}; owner decision 263-A; the coordinator resolution of 2026-10-11. DRAFT: nothing here authorises a "
                               "flip or a flight."),
        "roster_evidence": {
            "roster": tf.CONST_ROSTER["arm"], "roster_id": tf.CONST_ROSTER_ID, "split_identity_hash": arm["split_identity_hash"],
            "rows": tf.CONST_ROWS, "roster_role": "construction",
            "disjoint_from": {"SLURP-EVO-FOLD-A-V2": "61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6",
                              "SLURP-EVO-FOLD-B-V2": "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a"},
            "proof": "the roster receipt's disjointness_proof block (0 shared recordings, 0 shared utterances) and tests/unit/"
                     "test_tfrl_construction_source_cell.py (id-level intersections)",
            "delta_store_scope": {"outer_construction_scope": "R01C (this roster)",
                                  "permitted_roster": "SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1 (split identity 7c603857..., a subset of R01C)"}},
        "knowledge_source_guard": guard,
        "rows": tf.CONST_ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": measurement_blocks(ids),
        "study_commit_at_registration": commit, "blockers": blockers, "resolved_blockers": resolved, "status": "DRAFT-HELD"}
    shas["registered-facts-v1.json"] = reg.wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/tfrl/tfrl_mint_receipt.py --kind construction. "
                        "It authorises nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "loop_protocol": {"path": tf.PROTOCOL_RELPATH,
                                          "sha256": reg.sha_file(root, tf.PROTOCOL_RELPATH) if (root / tf.PROTOCOL_RELPATH).is_file() else None},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"Owner decision 263-A (2026-10-11), the coordinator resolution of 2026-10-11; {reg.INSTRUMENT_NOTE}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": "Fly the construction-source lock column (the plain lock on R01C) as the typed loop's proposer / reflector material source.",
        "decision_id": names["decision_id"],
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted",
                           "touching the resident session", "any ASR, transcript, encoder or paid-API contact",
                           "--allow-output-change on the re-pin tool", "any change beyond the registered plain lock"],
        "owner": "root", "population": {"count": tf.CONST_ROWS, "fold_a_contact_authorized": False, "fold_b_contact_authorized": False,
                                        "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery", "test_contact_authorized": False},
        "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": tf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True},
        "status": "DRAFT-NOT-MINTED"}
    shas["root-admission-draft-v1.json"] = reg.wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    rows = draft_rows(ids, commit, at, pkg, shas)
    shas["draft-ledger-rows.md"] = reg.wr(root, f"{pkg}/draft-ledger-rows.md", rows)
    readme = readme_text(ids, blockers, guard, resolved)
    shas["README.md"] = reg.wr(root, f"{pkg}/README.md", readme)
    prereg = (f"# Loop construction-source lock column: preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study commit `{commit}` by "
              "script. Development numbers only.\n\n"
              "This column is the proposer / reflector material source for iterations 1-3 of the typed loop; no benefit claim; it is re-flown "
              "only if the lock changes.\n\n"
              f"Runs: `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{names['read_run_id']}`.\n\n"
              "## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": measurement_blocks(ids)}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = reg.wr(root, tf.CONST_PREREG_RELPATH, prereg)
    result = {"package": pkg, "ids": ids, "shas": shas, "blockers": blockers, "guard": guard, "loader_verification": loader}
    if append_ledger:
        ledger = root / reg.LEDGER
        current = ledger.read_text(encoding="utf-8")
        ledger.write_text(current.rstrip("\n") + "\n\n" + rows, encoding="utf-8", newline="\n")
        result["ledger_appended"] = True
    return result


def readme_text(ids: Mapping[str, Mapping], blockers: list[Mapping[str, Any]], guard: Mapping[str, Any], resolved: list[Mapping[str, Any]]) -> str:
    arm, smoke = ids["arm"], ids["smoke"]
    cost = round(tf.CONST_MEASURED_GPU_H_PER_1000_ROWS * tf.CONST_ROWS / 1000.0, 2)
    return (
        "# Loop construction-source lock column (DRAFT / HELD)\n\n"
        "Status: DRAFT / HELD. No exposure-ledger row is countersigned, nothing is minted, flipped or flown. Generated by "
        "`scripts/flights/tfrl/write_tfrl_construction_registration.py` from the fragments `derive_tfrl_construction_cells.py` wrote.\n\n"
        "## What this is\n\n"
        "The proposer's tables and the ACE reflector's material come from ONE lock column flown on the CONSTRUCTION roster "
        f"`{tf.CONST_ROSTER_ID}` (R01C, {tf.CONST_ROWS} TRAIN rows outside Fold A and Fold B), never from Fold B. Fold B is the held-out "
        "selection split; Fold A confirms. The reason is the construction-roster vs knowledge guard of 2026-09-23: the semantic-knowledge "
        "preparer forbids Fold B rows as carrier ids of a delta-store registration, so ACE playbook releases staged from a Fold B column are "
        "refused.\n\n"
        f"The cell `{arm['cell']}` (+ `{smoke['cell']}`, four rows) is the review-off COMP-1b module graph with NO columns and NO supply arms: "
        f"the plain lock, program `{arm['program']}`, 2 contacts per row, lock `{tf.CONST_LOCK}` plus the CONSTRUCTION VARIANT `r01c` (requests "
        "byte-identical to lock v2.3 apart from the inert ace-playbook store, proof P-ACE-0; v2.2 because the ace i0 anchor cannot be re-homed, "
        "see the resolved blockers). Scorer `slurp-slu-official-train` (per-row official scores on disk), `stage3_algorithm` `shared-rollout`, "
        "measurement design `material-source` with `claims_benefit` false. It is the material source for iterations 1-3 of the typed loop; no "
        "benefit claim; it is re-flown only if the lock changes.\n\n"
        "## How the loop uses it\n\n"
        "* `open --iter t` takes the tables (and so the ACE reflector materials) from THIS column for t = 1, 2 and 3, because the lock does "
        "not change between iterations.\n"
        "* Iterations 2-3 additionally read the previous iteration's Fold B read, ONLY for (a) the refused-candidate buffer and (b) the ACE "
        "counters. Counters are credit (helpful / harmful / scoped_rows) computed by script over the Fold B `ace` column versus `lock`; they "
        "are numbers, not knowledge, so they may flow from the evaluation fold. No Fold B row, table cell or text is a knowledge source.\n"
        "* The ACE playbook releases i1+ are staged with R01C as the construction scope and the committed `stage3-deltas-v1r` registration's "
        "permitted and forbidden rosters (permitted: SLURP-STAGE3-ADVANTAGE-R01C-DISAGREEING-V1, a subset of R01C; forbidden: Fold A, Fold B, "
        "DEV-1000), so the preparer accepts them.\n\n"
        f"## Cost\n\n{tf.CONST_ROWS * tf.CONST_CONTACTS:,} contacts ({tf.CONST_ROWS} rows x 2). Measured throughput of the review-off composed arm: "
        f"1.38 GPU-h per 1,000 rows at 2.00 contacts per row (NX R5 read), so about {cost} GPU-h for the column plus FIT and the four-row smoke; "
        f"planned cap {tf.CONST_PLANNED_GPU_HOURS_ARM} GPU-h (smoke {tf.CONST_PLANNED_GPU_HOURS_SMOKE}). Audio ceiling "
        f"{arm['family_budget']['repeated_speech_audio_seconds_cap']} s.\n\n"
        "## Blockers (named, measured)\n\n" + ("\n".join(f"- `{b['id']}`: {b['detail']}\n  Remedy: {b['remedy']}" for b in blockers) or "None open.") + "\n\n"
        "## Resolved blockers\n\n" + "\n".join(f"- `{r['id']}`: was: {r['was']}. Resolution: {r['resolution']}." for r in resolved) + "\n\n"
        "## Files\n\n| file | what it is |\n| --- | --- |\n"
        "| `registered-facts-v1.json` | identities, accounting, cost estimate, roster evidence, the measured guard, the `stage3_measurement` blocks |\n"
        "| `protocol-registered-v1.json`, `*plan-registered-v1.json` | the registered protocol and the four plans (arm, arm FIT, smoke, smoke FIT) |\n"
        "| `analysis-recipe-v1.json` | the offline read: one official scoring, then the contrast tables |\n"
        "| `root-admission-draft-v1.json` | the DRAFT decision receipt (mint with `tfrl_mint_receipt.py --kind construction`) |\n"
        "| `draft-ledger-rows.md` | the DRAFT exposure rows (also appended at the end of `docs/exposure-ledger.md`) |\n\n"
        "Wrappers: `scripts/flights/tfrl/tfrl_const_flip.sh`, `tfrl_const_repin_arm.sh`, `tfrl_const_repin_smoke.sh`, `tfrl_const_read.sh`, "
        "`batch_chain_tfrl_const.sh`. Preregistration: `" + tf.CONST_PREREG_RELPATH + "`.\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository (or overlay) root to read and write")
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--append-ledger", action="store_true", help="append the DRAFT rows at the END of docs/exposure-ledger.md")
    args = parser.parse_args(argv)
    result = write_package(Path(args.root), args.study_commit, args.registered_at, data_root=Path(args.data_root), append_ledger=args.append_ledger)
    print(json.dumps({k: v for k, v in result.items() if k != "ids"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
