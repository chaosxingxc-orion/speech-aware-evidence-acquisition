#!/usr/bin/env python3
"""Write the DRAFT readiness packages of one loop iteration (design section 5, 6 and 7), from the derived fragments.

Config and receipt-pinned bytes only: no adapter contact, no server, no model, tokenizer, encoder, embedder or scorer contact. Flips
nothing, mints nothing, countersigns nothing, and writes NO row into ``docs/exposure-ledger.md`` unless ``--append-ledger`` is passed
(the coordinator's act). The DRAFT ledger rows are written beside the package as ``draft-ledger-rows.md``.

TWO PACKAGES per iteration (siblings under ``docs/readiness/``, because the effect-floor and flight-registration gates glob one level):

* ``<date>-slurp-tfrl-loop-i<t>-fold-b-v1/`` -- the column cell and its smoke: ``registered-facts-v1.json`` (with the CANONICAL
  ``stage3_measurement`` block keyed by run id: ``same-flight-supply-variant``, ``primary_metric_key slu``, ``nomination_rule
  official-column``), ``protocol-registered-v1.json``, the four plan files, ``analysis-recipe-v1.json``,
  ``root-admission-draft-v1.json`` and ``README.md``; beside it the preregistration;
* ``<date>-slurp-tfrl-loop-i<t>-proposers-v1/`` -- the typed proposer and ACE reflector text-only cells (form-proof, claims_benefit
  false: fewer than 200 rows).

Re-running replaces the package files in place. Every file says DRAFT / HELD.

    python -B scripts/flights/tfrl/write_tfrl_iteration_registration.py --iteration 1 --study-commit <sha> \\
        --registered-at 2026-10-11T12:00:00.000000+00:00 [--spec FILE] [--append-ledger]
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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

import derive_tfrl_iteration_cells as dv  # noqa: E402
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402

LEDGER = "docs/exposure-ledger.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT_NOTE = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
DESIGN = "docs/superpowers/specs/2026-10-11-slurp-autonomous-typed-loop-with-ace-comparator-design.md"
STATUS = "DRAFT-HELD-REGISTERED_BEFORE_CONTACT_AWAITING_COORDINATOR_COUNTERSIGN_AND_READINESS_FLIP"

PROHIBITIONS = [
    "No test-split, DEV or Fold A contact (Fold B only; Fold A confirmation and the DEV composed read are later registrations).",
    "No candidate substitution by hand; only the labelled hand-author fallback, which needs an owner order.",
    "No tool schema on any role; no Reviewer or Planner visit; max_revisions 0.",
    "No change of the delivering arm: lock carries no override and no release swap (invariants I7, I7v).",
    "The ACE column is a non-delivering comparator and can never be locked (decision 245).",
    "No flight before the coordinator countersigns the DRAFT rows, mints the decision receipt and the cells are flipped.",
    "No paper-scale profile. No system-level claim.",
]


def package_names(iteration: int) -> dict:
    stem = f"{tf.DATE}-slurp-tfrl-loop-i{iteration}"
    return {"column": f"docs/readiness/{stem}-fold-b-v1", "proposers": f"docs/readiness/{stem}-proposers-v1",
            "prereg": f"docs/readiness/{stem}-fold-b-v1-preregistration.md",
            "prereg_proposers": f"docs/readiness/{stem}-proposers-v1-preregistration.md"}


def wr(root: Path, path: str, text: str) -> str:
    target = Path(root) / path
    os.makedirs(target.parent, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="").write(text)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wjson(root: Path, path: str, obj: object) -> str:
    return wr(root, path, json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha_file(root: Path, path: str) -> str:
    return hashlib.sha256((Path(root) / path).read_bytes()).hexdigest()


def identities(root: Path, iteration: int, kinds: tuple[str, ...]) -> dict:
    out = {}
    for kind in kinds:
        n = tf.names(iteration, kind)
        document = json.loads((Path(root) / "configs" / "experiment" / f"{n['experiment']}.json").read_text(encoding="utf-8"))
        cell = document["cells"][0]
        composed = compose(Path(root), cell["model_fragment"], cell["dataset_fragment"], cell["baseline_fragment"], n["experiment"])
        split = document["population"]["split_identity_hash"]
        out[kind] = {
            "experiment": n["experiment"], "cell": cell["cell_id"], "run_id": cell["run_id"], "attempt_id": cell["attempt_id"],
            "fit_run_id": n["fit_run_id"], "fit_attempt_id": n["fit_attempt_id"], "baseline_fragment": cell["baseline_fragment"],
            "dataset_fragment": cell["dataset_fragment"], "model_fragment": cell["model_fragment"], "arm": composed.values["arm"],
            "rows": document["population"]["count"], "split_identity_hash": split,
            "roster_receipt": document["population"].get("roster_receipt"),
            "composed_config_hash": composed.config_hash,
            "protocol_hash": protocol_hash(composed.config_hash, composed.values["arm"], split),
            "fit": dict(composed.values.get("native_contact_fit") or {}), "family_budget": document["family_budget"],
            "execution_plan": document["execution_plan"], "execution_profile": document["execution_profile"],
            "carrier_lock_key": composed.values["carrier_lock_key"], "program": composed.values["policy"],
        }
    return out


def measurement_blocks(ids: Mapping[str, Mapping], iteration: int, predicted_effect_pp: float, arms: list[str],
                       mean_row_audio_seconds: float) -> dict:
    """The canonical ``stage3_measurement`` blocks keyed by run id (same-flight supply-variant design, design section 6)."""

    arm, smoke = ids["arm"], ids["smoke"]
    claims = predicted_effect_pp >= tf.PREDICTED_BAR_PP
    return {
        arm["run_id"]: {
            "measurement_design": "same-flight-supply-variant",
            "primary_metric_key": "slu",
            "primary_metric": "official SLURP pooled SLU-F1 (micro), paired per row",
            "expected_effect_pp": float(predicted_effect_pp) if claims else 0.0,
            "claims_benefit": bool(claims),
            "claim": "nominated",
            "nomination_rule": "official-column",
            "aa_arm_id": tf.TWIN,
            "rows": tf.ROWS,
            "tuning_roster": tf.TUNING_ROSTER,
            "read_roster": tf.READ_ROSTER,
            "variant_cost": {"extra_contacts_per_row": len(arms) - 1,
                             "extra_audio_seconds": round((len(arms) - 1) * mean_row_audio_seconds, 6)},
            "note": (f"Loop iteration {iteration}: arms {', '.join(arms)} over the delivering lock arm, paired per row inside one flight, "
                     "preregistered selection rule in " + tf.PROTOCOL_RELPATH + ". The expected effect is the typed arm's predicted "
                     "effect when one flies (at least 1.5 pp, decision 192) and is 0.0 with claims_benefit false when the typed arm is "
                     "empty (the iteration then measures the ACE comparator, the twin null and the offline delivery reads)."),
        },
        smoke["run_id"]: {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": tf.SMOKE_ROWS,
            "primary_metric": "none (structural form only)", "read_roster": tf.READ_ROSTER, "tuning_roster": "none",
            "note": (f"Four Fold B rows prove FORM only: the {arm['program']} program loads, the supply arms fan out with the delivering "
                     "arm last, the empty ace-playbook-i0 route renders zero bytes on the non-ace arms, every swap resolves its alternate "
                     "and the episode completes. Scored by no one, read by no one."),
        },
    }


def text_only_blocks(ids: Mapping[str, Mapping]) -> dict:
    out = {}
    for kind, i in ids.items():
        out[i["run_id"]] = {
            "measurement_design": "form-proof", "expected_effect_pp": 0.0, "claims_benefit": False, "rows": i["rows"],
            "primary_metric": "none (text-only proposal contacts; validated offline)", "read_roster": tf.READ_ROSTER,
            "tuning_roster": "none",
            "note": "Fewer than 200 rows: a form proof by size (instrument rule 5). The proposal is validated and curated offline.",
        }
    return out


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str, route: Mapping[str, str],
              purpose: Mapping[str, str]) -> dict:
    docs = {}
    for kind, i in ids.items():
        prefix = "smoke-" if kind == "smoke" else (f"{kind}-" if kind in ("typed", "ace") else "")
        supply = {"relpath": f"prepared/{i['run_id']}/phase-supply-v1.json", "sha256": "MINTED_AT_THE_FLIP",
                  "note": "the flip mints this cell's own first-phase supply under its own run id (item E16)"}
        base = {"cell": i["cell"], "composed_config_hash": i["composed_config_hash"], "expected_session_id": tf.SESSION,
                "experiment": i["experiment"], "family_budget": i["family_budget"], "preparation_base_commit": commit,
                "protocol_document": {"relpath": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                "registered_at_utc": at, "status": STATUS, "unused_budget_is_not_attempt_authority": True,
                "loop_protocol": {"relpath": tf.PROTOCOL_RELPATH, "status": "DRAFT-HELD"}}
        if kind in ("arm", "smoke"):
            base["prepared_phase_supply"] = supply
        gen = dict(i["execution_plan"], attempt_id=i["attempt_id"], carrier_lock_key=i["carrier_lock_key"],
                   protocol_hash=i["protocol_hash"], run_id=i["run_id"], schema="saea-execution-plan-v1",
                   split_identity_hash=i["split_identity_hash"], study="speech-aware-evidence-acquisition")
        docs[f"{prefix}generation-plan-registered-v1.json"] = {
            **base, "execution_plan": gen, "execution_route": route[kind], "plan_kind": "generation", "purpose": purpose[kind],
            "schema": "saea-registered-generation-plan-v1"}
        if kind in ("arm", "smoke"):
            fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
            docs[f"{prefix}fit-plan-registered-v1.json"] = {
                **base, "execution_plan": fit, "plan_kind": "fit", "schema": "saea-registered-fit-plan-v1",
                "execution_route": "The shared core.flight.cli FIT path under this cell's own native_contact_fit ids; request envelopes only, no generation.",
                "purpose": f"{i['fit_run_id']}: request envelopes only; reads nothing."}
    return docs


def column_package(root: Path, iteration: int, spec: Mapping[str, Any], commit: str, at: str, *, predicted_effect_pp: float,
                   loader: Mapping[str, Any]) -> dict:
    pkgs = package_names(iteration)
    pkg = pkgs["column"]
    ids = identities(root, iteration, ("arm", "smoke"))
    arms = list(dv.iteration_arms(spec, iteration))
    arm, smoke = ids["arm"], ids["smoke"]
    names = tf.names(iteration, "arm")
    mean_audio = dv.roster_audio("arm", root) / tf.ROWS
    blocks = measurement_blocks(ids, iteration, predicted_effect_pp, arms, mean_audio)
    blockers = []
    if not loader.get("ok", False):
        blockers.append({"id": "ace-playbook-store-not-in-lock-layer", "detail": loader.get("refusal"),
                         "remedy": "the lock layer (or a v2.2 successor in rails/adapters/slurp_module_hooks.py) must declare the "
                                   "ace-playbook store with the empty release i0 before the loader's verify_declared_module accepts "
                                   "the ace column; this package derives through a hooks wrapper that adds the store"})
    if any(p["sha256"] == dv.ZERO for p in [dv.ace_alternate(spec["ace"])["release"], dv.ace_alternate(spec["ace"])["snapshot"]]):
        blockers.append({"id": "ace-release-pins-pending",
                         "detail": "the ace-playbook i0/i<t> release and snapshot pins are zeros until the releases are prepared "
                                   "(prepare_semantic_knowledge_store over the driver's registration); re-run open --stage cell"})
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id",
                                           "protocol_hash", "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "decision_rule_fixed_here": (f"The selection rule, parent choice, edit budget, stop rule and curve are fixed in {tf.PROTOCOL_RELPATH} "
                                     "(sha256 pinned by the driver); this cell reads its own flight under that rule."),
        "arms": arms, "one_factor": "the supply arms of the iteration over the unchanged lock v2.2 base on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": f"slurp-tfrl-loop-i{iteration}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": (f"Which supply arm of iteration {iteration} ({', '.join(arms)}) raises official pooled SLU-F1 over the delivering "
                         "lock arm on TRAIN Fold B, paired per row, with the in-flight twin as the null?"),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration; run-cumulative budgets.",
        "blockers": blockers,
    }
    protocol_sha = wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    route = {
        "arm": (f"Shared core.flight.cli campaign over {names['campaign']} (this arm alone; the in-flight twin aa is the null) through "
                "scripts/flights/tfrl/batch_chain_tfrl_i1.sh and the batch driver."),
        "smoke": "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."}
    purpose = {"arm": f"{arm['run_id']}: Loop iteration {iteration} Fold B supply column under the preregistered selection rule.",
               "smoke": f"{smoke['run_id']}: structural form proof only: no score and no read."}
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, route, purpose)
    shas = {name: wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    recipe = {
        "authority": f"{DESIGN} sections 5-7; {tf.PROTOCOL_RELPATH}; {INSTRUMENT_NOTE}",
        "cell_kind": "SUPPLY-VARIANT COLUMN -- same-flight, claim ceiling nominated",
        "claim_boundary": "No system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": "CPU official scorer jobs over derived copies only", "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the read); bounded-discovery-probe (the flight itself)",
        "measurement_design": "same-flight-supply-variant", "read_run_id": names["read_run_id"], "recipe_id": names["recipe_id"],
        "registered_at_utc": at, "roster": {"relpath": tf.ROSTER["arm"], "roster_id": tf.READ_ROSTER, "rows": tf.ROWS,
                                           "split_identity_hash": arm["split_identity_hash"]},
        "run_ids": {"arm": arm["run_id"], "fit": arm["fit_run_id"], "read": names["read_run_id"], "smoke": smoke["run_id"],
                    "smoke_fit": smoke["fit_run_id"]},
        "arms": {"order": arms, "delivering": tf.DELIVERING, "twin": tf.TWIN, "columns": {a: {} for a in arms if a not in (tf.DELIVERING, tf.TWIN)}},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_score": "scripts/analysis/stage3_rollout_score.py --mode supply-variants (one complete official scoring per arm, never sharded)",
            "2_node_local": "scripts/analysis/slurp_nx_solver_column_read.py (supply stats, empty-gold false fill, non-empty exact)",
            "3_paired": "scripts/analysis/stage3_paired_read.py --per-scenario: aa-vs-lock then each column-vs-lock (cluster key sample_id, 10,000 draws, seed 20260915)",
            "4_loop": "scripts/flights/tfrl/tfrl_loop_driver.py close --iter %d: credit vectors, the preregistered selection rule, archive, curve" % iteration,
        },
        "what_is_not_here": "No margins block and no admission: the loop driver applies the preregistered rule; nothing is locked here.",
    }
    shas["analysis-recipe-v1.json"] = wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    facts = {
        "_note": ("Every model-free fact this DRAFT registration rests on, and the CANONICAL stage3_measurement block "
                  "scripts/checks/stage3_effect_floor_check.py and scripts/checks/flight_registration_check.py resolve (keyed by run id)."),
        "accounting": {"program": arm["program"], "arms": arms, "contacts_per_row": len(arms) + 1,
                       "arm_generation_calls": arm["family_budget"]["generation_calls_cap"],
                       "smoke_generation_calls": smoke["family_budget"]["generation_calls_cap"]},
        "composed_config_hashes": {k: v["composed_config_hash"] for k, v in ids.items()},
        "fit": {"status": "PENDING_CHECK", "frame": dict(tf.FIT_ESTIMATE)},
        "identity": ids, "prohibitions": PROHIBITIONS, "registered_at_utc": at,
        "registration_basis": f"{DESIGN}; owner decision 263-A. DRAFT: nothing here authorises a flip or a flight.",
        "rows": tf.ROWS, "schema": "saea-registered-facts-v1", "stage3_measurement": blocks, "study_commit_at_registration": commit,
        "blockers": blockers, "status": "DRAFT-HELD",
    }
    shas["registered-facts-v1.json"] = wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    draft = {
        "_draft_note": ("A DRAFT for the coordinator to mint on the data root with scripts/flights/tfrl/tfrl_mint_receipt.py. It "
                        "authorises nothing while its status is not 'decided'."),
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "loop_protocol": {"path": tf.PROTOCOL_RELPATH, "sha256": sha_file(root, tf.PROTOCOL_RELPATH) if (Path(root) / tf.PROTOCOL_RELPATH).is_file() else None},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"Owner decisions 263-A / 264-A / 265 (2026-10-11); {INSTRUMENT_NOTE}.",
        "budget": {**arm["family_budget"], "paid_api_calls": 0, "plan_budget_is_run_cumulative": True, "smoke": smoke["family_budget"]},
        "claim_boundary": "No system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "decision": f"Fly the loop iteration {iteration} Fold B supply column ({', '.join(arms)}).",
        "decision_id": f"slurp-tfrl-loop-i{iteration}-admission-v1",
        "eligible_run_ids": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]],
        "not_authorized": ["any flight before the cells are flipped and the receipt is minted", "touching the resident session",
                           "any ASR, transcript, encoder or paid-API contact", "--allow-output-change on the re-pin tool",
                           "any change beyond the registered arms", "substituting a candidate by hand"],
        "owner": "root", "population": {"count": tf.ROWS, "fold_a_contact_authorized": False,
                                        "split_identity_hash": arm["split_identity_hash"], "split_role": "discovery",
                                        "test_contact_authorized": False},
        "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": tf.SESSION, "model_fragment": arm["model_fragment"], "no_child_start_stop": True},
        "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    readme = (f"# Loop iteration {iteration}: Fold B supply column (DRAFT / HELD)\n\n"
              "Status: DRAFT / HELD. No exposure-ledger row, no countersignature, no flip. Generated by "
              "`scripts/flights/tfrl/write_tfrl_iteration_registration.py` from the derived fragments.\n\n"
              f"Arms: {', '.join(arms)} (program `{arm['program']}`). Loop protocol: `{tf.PROTOCOL_RELPATH}`.\n\n"
              + ("## Blockers\n\n" + "\n".join(f"- `{b['id']}`: {b['detail']}" for b in blockers) + "\n" if blockers else ""))
    shas["README.md"] = wr(root, f"{pkg}/README.md", readme)
    prereg = (f"# Loop iteration {iteration} (supply column): preregistration (DRAFT / HELD)\n\n"
              f"Registered {at[:10]} at study commit `{commit}` by script. Development numbers only.\n\n"
              f"Runs: `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{names['read_run_id']}`.\n\n"
              "## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = wr(root, pkgs["prereg"], prereg)
    return {"ids": ids, "shas": shas, "blocks": blocks, "arms": arms, "blockers": blockers, "package": pkg}


def proposers_package(root: Path, iteration: int, commit: str, at: str) -> dict:
    pkgs = package_names(iteration)
    pkg = pkgs["proposers"]
    kinds = ("typed", "ace")
    ids = identities(root, iteration, kinds)
    blocks = text_only_blocks(ids)
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id",
                                           "protocol_hash", "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "prohibitions": PROHIBITIONS, "protocol_id": f"slurp-tfrl-loop-i{iteration}-proposers-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": "Text-only proposer / reflector contacts: aggregate tables in, closed-schema proposals out; validated offline.",
        "failure_policy": "Stop and preserve on the first failure; the registered retries are the only re-asks; no best-of-N.",
    }
    protocol_sha = wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    route = {k: "Shared core.flight.cli worker/campaign on this cell alone through the batch driver (text-only, no audio part)." for k in kinds}
    purpose = {k: f"{ids[k]['run_id']}: text-only {'typed proposer' if k == 'typed' else 'ACE reflector'} contacts (form proof)." for k in kinds}
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, route, purpose)
    shas = {name: wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    facts = {"_note": "DRAFT facts for the two text-only cells.", "identity": ids, "registered_at_utc": at,
             "schema": "saea-registered-facts-v1", "stage3_measurement": blocks, "study_commit_at_registration": commit,
             "status": "DRAFT-HELD", "rows": {k: v["rows"] for k, v in ids.items()}}
    shas["registered-facts-v1.json"] = wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    shas["README.md"] = wr(root, f"{pkg}/README.md", (
        f"# Loop iteration {iteration}: typed proposer and ACE reflector cells (DRAFT / HELD)\n\nStatus: DRAFT / HELD. No ledger row, "
        "no countersignature, no flip. Text-only contacts (construction-proposer-text), form proof, claims_benefit false.\n"))
    draft = {
        "_draft_note": "A DRAFT for the coordinator to mint with scripts/flights/tfrl/tfrl_mint_receipt.py --kind proposers. Authorises nothing "
                       "while its status is not 'decided'.",
        "antecedents": {"protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
                        "registered_facts": {"path": f"{pkg}/registered-facts-v1.json", "sha256": shas["registered-facts-v1.json"]},
                        "registration_base_commit": commit},
        "authorization_basis": f"Owner decisions 263-A / 264-A / 265 (2026-10-11); {DESIGN} section 3.",
        "budget": {k: ids[k]["family_budget"] for k in kinds}, "paid_api_calls": 0,
        "claim_boundary": "Text-only proposal contacts; no benefit claim.",
        "decision": f"Fly the loop iteration {iteration} typed proposer and ACE reflector cells (text-only).",
        "decision_id": f"slurp-tfrl-proposers-i{iteration}-admission-v1",
        "eligible_run_ids": [ids["typed"]["run_id"], ids["ace"]["run_id"]],
        "not_authorized": ["any audio part", "any best-of-N or re-sampling beyond the registered retries", "--allow-output-change"],
        "owner": "root", "recorded_at_utc": None, "schema": "saea-campaign-decision-v1",
        "service": {"expected_session_id": tf.SESSION, "no_child_start_stop": True}, "status": "DRAFT-NOT-MINTED",
    }
    shas["root-admission-draft-v1.json"] = wjson(root, f"{pkg}/root-admission-draft-v1.json", draft)
    prereg = (f"# Loop iteration {iteration} (proposer and reflector cells): preregistration (DRAFT / HELD)\n\nRegistered {at[:10]} at study "
              f"commit `{commit}` by script. Text-only form proof.\n\n## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n")
    shas["__prereg__"] = wr(root, pkgs["prereg_proposers"], prereg)
    return {"ids": ids, "shas": shas, "blocks": blocks, "package": pkg}


def runtime_identity(root: Path, model_fragment: str) -> dict:
    """Model file hashes and the llama.cpp build commit from the model fragment's runtime receipt (read, never run)."""

    fragment = json.loads((Path(root) / "configs" / "model" / f"{model_fragment}.json").read_text(encoding="utf-8"))
    relpath = fragment.get("runtime_receipt", "receipts/runtime.json")
    path = Path(root) / "docs" / relpath
    if not path.is_file():
        return {"files": {"unavailable": "0" * 64}, "build": "unavailable"}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return {"files": {Path(f["path"]).name: f["sha256"] for f in receipt.get("gguf_files", [])},
            "build": receipt.get("llama_cpp", {}).get("build_commit", "unavailable")}


def draft_text_only_rows(root: Path, iteration: int, ids: Mapping[str, Mapping], shas: Mapping[str, str], at: str,
                         artefacts: Mapping[str, Mapping[str, str]] | None = None) -> str:
    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    artefacts = artefacts or {}
    lines = [f"## Loop iteration {iteration}: typed proposer and ACE reflector cells (DRAFT, coordinator countersignature pending)", "",
             "| " + " | ".join(tp.LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in tp.LEDGER_COLUMNS) + " |"]
    for kind, i in ids.items():
        rt = runtime_identity(root, i["model_fragment"])
        art = artefacts.get(kind, {})
        row = tp.draft_exposure_row(
            date=at[:10], run_id=i["run_id"], carrier_roster_id=Path(str(i["experiment"])).stem, split_identity_hash=i["split_identity_hash"],
            carriers=i["rows"], model_files_sha256=rt["files"], llama_cpp_build_commit=rt["build"],
            prompt_sha256=art.get("prompt_sha256", "pending"), tables_sha256=art.get("tables_sha256", "pending"),
            archive_sha256=art.get("archive_sha256", "pending"), geometry=tf.SESSION, kind=kind)
        row["scope"] = "DRAFT -- " + row["scope"]
        lines.append(tp.ledger_markdown_row(row))
    return "\n".join(lines) + "\n"


def draft_column_rows(ids: Mapping[str, Mapping], commit: str, at: str, arms: list[str], pkg: str, shas: Mapping[str, str]) -> str:
    cols = ["date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split", "split role",
            "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes"]
    scope = (f"DRAFT -- REGISTERED. Frozen core, np4 session; the review-off COMP-1b module graph at lock v2.2 with the Solver supply "
             f"arms {', '.join(arms)} (program {ids['arm']['program']}); no tool authority on any role")
    inherited = "TRAIN Fold B discovery rows already exposed by prior SLURP cells; this cell opens no split. Prior exposure is inherited in full."
    lines = [f"## Loop iteration column cell (DRAFT, coordinator countersignature pending) -- {pkg}", "",
             "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for kind in ("arm", "smoke"):
        i = ids[kind]
        for fit in (False, True):
            plan = f"{pkg}/{'smoke-' if kind == 'smoke' else ''}{'fit' if fit else 'generation'}-plan-registered-v1.json"
            calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
            cells = [at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"], scope + (" -- FIT spend identity" if fit else ""),
                     "frozen core (attach only)", f"slurp TRAIN Fold B {i['rows']}", "discovery", i["split_identity_hash"], "no", str(calls),
                     str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]),
                     inherited, plan, f"DRAFT at study commit {commit}; plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."]
            lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    arm = ids["arm"]
    read_id = tf.names(int(arm["experiment"].split("-i")[1].split("-")[0]), "arm")["read_run_id"]
    read = [at[:10], read_id, "model-free-check",
            (f"The offline read of the loop iteration column: score the supply columns once each, node-local and paired reads, the "
             f"preregistered selection rule, by the recipe {pkg}/analysis-recipe-v1.json. Zero model, server, encoder, embedder, tokenizer "
             "and GPU contacts."),
            "no model or tool contact; read of sealed bytes and CPU official scorings over derived copies",
            f"slurp TRAIN Fold B {arm['rows']}, the sealed iteration flight (after the seal)", "discovery", arm["split_identity_hash"], "no",
            "0", "0", "0", inherited, f"{pkg}/analysis-recipe-v1.json",
            f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the seal and before any column is opened) "
            f"{at[:10]} at study commit {commit}. Its ceiling is a nomination; it admits nothing."]
    lines.append("| " + " | ".join(c.replace("|", "/") for c in read) + " |")
    return "\n".join(lines) + "\n"


def default_spec(iteration: int) -> dict:
    return {"typed": None, "parent": None, "ace": {"iteration": iteration}}


def write_iteration(root: Path, iteration: int, spec: Mapping[str, Any], commit: str, at: str, *, predicted_effect_pp: float = 0.0,
                    with_proposers: bool = True, append_ledger: bool = False,
                    pins: Mapping[str, Mapping[str, Any]] | None = None) -> dict:
    """Derive (into ``root``) and register an iteration's cells. ``pins``: ``{"typed": {...}, "ace": {...}}`` for the text-only cells."""

    root = Path(root)
    derived = dv.derive_iteration(iteration, spec, repo_root=root)
    result: dict[str, Any] = {"iteration": iteration, "column": None, "proposers": None}
    loader = derived["cells"]["arm"]["loader_verification"]
    column = column_package(root, iteration, spec, commit, at, predicted_effect_pp=predicted_effect_pp, loader=loader)
    column_rows = draft_column_rows(column["ids"], commit, at, column["arms"], column["package"], column["shas"])
    column["shas"]["draft-ledger-rows.md"] = wr(root, f"{column['package']}/draft-ledger-rows.md", column_rows)
    result["column"] = {k: column[k] for k in ("package", "arms", "blockers")} | {"shas": column["shas"]}
    ledger_text = column_rows
    if with_proposers and pins:
        for kind in ("typed", "ace"):
            if kind in pins:
                dv.derive_text_only(iteration, kind, pins[kind], repo_root=root)
        proposers = proposers_package(root, iteration, commit, at)
        rows = draft_text_only_rows(root, iteration, proposers["ids"], proposers["shas"], at)
        proposers["shas"]["draft-ledger-rows.md"] = wr(root, f"{proposers['package']}/draft-ledger-rows.md", rows)
        result["proposers"] = {"package": proposers["package"], "shas": proposers["shas"]}
        ledger_text += "\n" + rows
    if append_ledger:
        ledger = Path(root) / LEDGER
        current = ledger.read_text(encoding="utf-8")
        ledger.write_text(current.rstrip("\n") + "\n\n" + ledger_text, encoding="utf-8", newline="\n")
        result["ledger_appended"] = True
    result["loader_verification"] = loader
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--iteration", type=int, required=True, choices=tf.ITERATIONS)
    parser.add_argument("--study-commit", required=True)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--spec", default=None)
    parser.add_argument("--predicted-effect-pp", type=float, default=0.0)
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository (or overlay) root to read and write")
    parser.add_argument("--append-ledger", action="store_true", help="coordinator's act: append the DRAFT rows to docs/exposure-ledger.md")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else default_spec(args.iteration)
    result = write_iteration(Path(args.root), args.iteration, spec, args.study_commit, args.registered_at,
                             predicted_effect_pp=args.predicted_effect_pp, with_proposers=False, append_ledger=args.append_ledger)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
