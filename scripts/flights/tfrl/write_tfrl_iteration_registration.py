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


#: The instruction templates whose bytes the text-only rows pin (resolved at write time, never "pending").
PROMPT_RELPATHS = {"typed": "configs/probes/tfrl/typed-proposer-v1.txt", "ace": "configs/probes/tfrl/ace-reflector-v1.txt"}
NOT_BOUND = "not bound by this writer call (see the cell pins in its experiment fragment)"


def proposers_read_run_id(iteration: int) -> str:
    """The model-free validation / archive step of the proposer cells (the driver's ``open --stage cell``) is the proposers' READ."""

    return f"SAEA-SLURP-STAGE3-TFRL-PROPOSERS-I{iteration}-READ-V1"


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


def recovery_budget(iteration: int, i: Mapping) -> dict:
    """The recovered smoke's run-cumulative budget statement: the original plan, the failed attempts' recorded spend, their sum."""

    spent_calls, spent_audio = tf.smoke_predecessor_spend(iteration)
    cumulative_calls = int(i["execution_plan"]["planned_model_calls"])
    cumulative_audio = int(i["execution_plan"]["planned_speech_audio_seconds"])
    original_calls, original_audio = cumulative_calls - spent_calls, cumulative_audio - int(spent_audio + 0.999999999)
    return {
        "original_plan": {"planned_model_calls": original_calls, "planned_speech_audio_seconds": original_audio},
        "failed_attempt_spend": {"model_calls": spent_calls, "speech_audio_seconds": spent_audio,
                                 "attempt_ids": [p["attempt_id"] for p in tf.smoke_recovery(iteration)["predecessors"]]},
        "cumulative_plan": {"planned_model_calls": cumulative_calls, "planned_speech_audio_seconds": cumulative_audio},
        "rule": "The adapter budget is run-cumulative across the attempts of a run id; the FIT cap is structural and never scaled.",
    }


def recovery_section(iteration: int, smoke: Mapping) -> str:
    """The smoke-recovery (rec1) text of the README and the preregistration: failed attempt, root cause, rec1 ids, cumulative budget."""

    rec = tf.smoke_recovery(iteration)
    budget = recovery_budget(iteration, smoke)
    return (
        "\n## Smoke recovery (the cell's single recovery re-registration, rec1)\n\n"
        f"{rec['reason']}\n\n{rec['amendment']}\n\n"
        f"- Failed attempt: `{rec['predecessor_attempt_id']}` ({rec['predecessor_state']})\n"
        f"- Root cause: {rec['root_cause']}.\n"
        f"- Re-flown whole under generation attempt `{smoke['attempt_id']}` and FIT attempt `{smoke['fit_attempt_id']}`; the arm cell is "
        "untouched (its attempt never opened); the run ids and the minted decision receipt are unchanged.\n"
        f"- Run-cumulative plan budget: {budget['original_plan']['planned_model_calls']} + "
        f"{budget['failed_attempt_spend']['model_calls']} = {budget['cumulative_plan']['planned_model_calls']} calls; "
        f"{budget['original_plan']['planned_speech_audio_seconds']} + {budget['failed_attempt_spend']['speech_audio_seconds']:g} = "
        f"{budget['cumulative_plan']['planned_speech_audio_seconds']} speech-seconds; the FIT cap stays structural.\n"
        f"- Plans: `{tf.plan_file_name(iteration, 'smoke', 'generation')}`, `{tf.plan_file_name(iteration, 'smoke', 'fit')}` (the first-attempt "
        "smoke plan files are superseded and removed from the package; the git history keeps them).\n"
        f"- {rec['rule']}\n")


def plan_docs(root: Path, ids: Mapping[str, Mapping], commit: str, at: str, protocol_sha: str, pkg: str, route: Mapping[str, str],
              purpose: Mapping[str, str], iteration: int | None = None) -> dict:
    """Registered plan documents. ``iteration`` selects the loop iteration whose smoke recovery applies; ``None`` (the construction-source
    package, which shares this builder) means no recovery and the historical plan file names."""

    docs = {}
    for kind, i in ids.items():
        recovered = iteration is not None and kind == "smoke" and tf.smoke_recovery(iteration) is not None
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
        extra = {}
        if recovered:
            # the smoke's single recovery (rec1): the plan carries the original plan plus the failed attempt's recorded spend (nx_r6 pattern)
            gen["recovery"] = tf.smoke_recovery(iteration)
            extra = {"recovery_budget": recovery_budget(iteration, i)}
        docs[tf.plan_file_name(iteration, kind, "generation")] = {
            **base, **extra, "execution_plan": gen, "execution_route": route[kind], "plan_kind": "generation", "purpose": purpose[kind],
            "schema": "saea-registered-generation-plan-v1"}
        if kind in ("arm", "smoke"):
            fit = dict(gen, attempt_id=i["fit_attempt_id"], run_id=i["fit_run_id"], planned_model_calls=i["family_budget"]["fit_endpoint_calls_cap"])
            docs[tf.plan_file_name(iteration, kind, "fit")] = {
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
        blockers.append({"id": "loader-refuses-the-derived-cell", "detail": loader.get("refusal"),
                         "remedy": "the derived cell does not verify under the real carrier hooks (lock v2.3); fix the cell or the lock "
                                   "before any countersign"})
    if any(p["sha256"] == dv.ZERO for p in [dv.ace_alternate(spec["ace"])["release"], dv.ace_alternate(spec["ace"])["snapshot"]]):
        blockers.append({"id": "ace-release-pins-pending",
                         "detail": "the ace-playbook i0/i<t> release and snapshot pins are zeros until the releases are prepared "
                                   "(prepare_semantic_knowledge_store over the driver's registration); re-run open --stage cell"})
    protocol = {
        "cells": {k: {kk: v[kk] for kk in ("attempt_id", "cell", "composed_config_hash", "experiment", "fit_attempt_id", "fit_run_id",
                                           "protocol_hash", "rows", "run_id", "split_identity_hash")} for k, v in ids.items()},
        "decision_rule_fixed_here": (f"The selection rule, parent choice, edit budget, stop rule and curve are fixed in {tf.PROTOCOL_RELPATH} "
                                     "(sha256 pinned by the driver); this cell reads its own flight under that rule."),
        "arms": arms, "one_factor": "the supply arms of the iteration over the unchanged lock v2.3 base (v2.2 plus the empty ace-playbook-i0 declaration) on TRAIN Fold B",
        "prohibitions": PROHIBITIONS, "protocol_id": f"slurp-tfrl-loop-i{iteration}-protocol-v1", "registered_at_utc": at,
        "schema": "saea-registered-protocol-v1", "status": STATUS, "study_commit_at_registration": commit,
        "the_question": (f"Which supply arm of iteration {iteration} ({', '.join(arms)}) raises official pooled SLU-F1 over the delivering "
                         "lock arm on TRAIN Fold B, paired per row, with the in-flight twin as the null?"),
        "failure_policy": "Stop and preserve on the first failure; at most one root-diagnosed recovery re-registration; run-cumulative budgets.",
        "blockers": blockers,
    }
    recovery = tf.smoke_recovery(iteration)
    if recovery:
        protocol["recovery"] = {"smoke": recovery}
    protocol_sha = wjson(root, f"{pkg}/protocol-registered-v1.json", protocol)
    route = {
        "arm": (f"Shared core.flight.cli campaign over {names['campaign']} (this arm alone; the in-flight twin aa is the null) through "
                "scripts/flights/tfrl/batch_chain_tfrl_i1.sh and the batch driver."),
        "smoke": "Shared core.flight.cli worker on this cell alone (the batch driver's smoke step); never scored."}
    purpose = {"arm": f"{arm['run_id']}: Loop iteration {iteration} Fold B supply column under the preregistered selection rule.",
               "smoke": f"{smoke['run_id']}: structural form proof only: no score and no read."}
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, route, purpose, iteration)
    for stale in tf.superseded_plan_file_names(iteration):      # the failed first-attempt smoke plans are superseded by the rec1 plans
        (Path(root) / pkg / stale).unlink(missing_ok=True)
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
        **({"recovery": {"smoke": recovery,
                         "smoke_plans": [tf.plan_file_name(iteration, "smoke", "generation"), tf.plan_file_name(iteration, "smoke", "fit")],
                         "smoke_budget": recovery_budget(iteration, smoke)}} if recovery else {}),
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
        "eligible_attempt_ids": [arm["attempt_id"], arm["fit_attempt_id"], smoke["attempt_id"], smoke["fit_attempt_id"]],
        **({"superseded_attempt_ids": [recovery["predecessor_attempt_id"], recovery["predecessor_fit_attempt_id"]],
            "recovery_note": recovery["reason"]} if recovery else {}),
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
              + ("## Blockers\n\n" + "\n".join(f"- `{b['id']}`: {b['detail']}" for b in blockers) + "\n" if blockers else "")
              + (recovery_section(iteration, smoke) if recovery else ""))
    shas["README.md"] = wr(root, f"{pkg}/README.md", readme)
    prereg = (f"# Loop iteration {iteration} (supply column): preregistration (DRAFT / HELD)\n\n"
              f"Registered {at[:10]} at study commit `{commit}` by script. Development numbers only.\n\n"
              f"Runs: `{arm['run_id']}` / `{arm['fit_run_id']}`; `{smoke['run_id']}` / `{smoke['fit_run_id']}`; read `{names['read_run_id']}`.\n\n"
              "## The measurement declaration\n\n```json\n"
              + json.dumps({"stage3_measurement": blocks}, indent=2, ensure_ascii=False, sort_keys=True) + "\n```\n"
              + (recovery_section(iteration, smoke) if recovery else ""))
    shas["__prereg__"] = wr(root, pkgs["prereg"], prereg)
    return {"ids": ids, "shas": shas, "blocks": blocks, "arms": arms, "blockers": blockers, "package": pkg}


def proposers_recipe(iteration: int, ids: Mapping[str, Mapping], at: str) -> dict:
    """The proposers package analysis recipe (the offline validation / archive step is the READ)."""

    read_id = proposers_read_run_id(iteration)
    return {
        "authority": f"{DESIGN} sections 3 and 7; {tf.PROTOCOL_RELPATH}; {INSTRUMENT_NOTE}",
        "cell_kind": "TEXT-ONLY PROPOSER / REFLECTOR -- form proof; the offline step validates and archives the sealed proposals",
        "claim_boundary": "No benefit, system-level, superiority, generalisation, held-out, confirmatory or paper-scale claim.",
        "contacts": {"asr": 0, "encoder": 0, "model": 0, "scorer": 0, "server": 0, "tokenizer": 0},
        "execution_profile": "model-free-check (the offline step); bounded-discovery-probe (the two text-only flights)",
        "measurement_design": "form-proof",
        "read_run_id": read_id,
        "recipe_id": f"slurp-tfrl-proposers-i{iteration}-validation-analysis-v1",
        "registered_at_utc": at,
        "run_ids": {"typed": ids["typed"]["run_id"], "typed_fit": ids["typed"]["fit_run_id"], "ace": ids["ace"]["run_id"],
                    "ace_fit": ids["ace"]["fit_run_id"], "read": read_id},
        "schema": "saea-stage3-rollout-analysis-recipe-v1",
        "stages": {
            "1_validate_and_curate": (f"python -B scripts/flights/tfrl/tfrl_loop_driver.py --execute open --iter {iteration} --stage cell "
                                      "(validates the sealed typed candidates through speech_aware_evidence_acquisition.rails.tfrl_typed_proposer "
                                      "and curates the ACE deltas through speech_aware_evidence_acquisition.rails.tfrl_ace_material; "
                                      "reads only sealed receipts, no row gold and no utterance text)"),
            "2_archive": ("the same step writes the candidate states through speech_aware_evidence_acquisition.analysis.sealed_credit.archive "
                          "(write-once receipts under the loop package); no score is computed and nothing is selected here"),
        },
        "what_is_not_here": "No score, no paired read, no margins block and no admission: the column cells and the loop's close step read effects.",
    }


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
    plans = plan_docs(root, ids, commit, at, protocol_sha, pkg, route, purpose, iteration)
    shas = {name: wjson(root, f"{pkg}/{name}", doc) for name, doc in plans.items()}
    shas["protocol-registered-v1.json"] = protocol_sha
    facts = {"_note": "DRAFT facts for the two text-only cells.", "identity": ids, "registered_at_utc": at,
             "schema": "saea-registered-facts-v1", "stage3_measurement": blocks, "study_commit_at_registration": commit,
             "status": "DRAFT-HELD", "rows": {k: v["rows"] for k, v in ids.items()}}
    shas["registered-facts-v1.json"] = wjson(root, f"{pkg}/registered-facts-v1.json", facts)
    shas["README.md"] = wr(root, f"{pkg}/README.md", (
        f"# Loop iteration {iteration}: typed proposer and ACE reflector cells (DRAFT / HELD)\n\nStatus: DRAFT / HELD. No ledger row, "
        "no countersignature, no flip. Text-only contacts (construction-proposer-text), form proof, claims_benefit false.\n"))
    recipe = proposers_recipe(iteration, ids, at)
    shas["analysis-recipe-v1.json"] = wjson(root, f"{pkg}/analysis-recipe-v1.json", recipe)
    draft = {
        "_draft_note": "A DRAFT for the coordinator to mint with scripts/flights/tfrl/tfrl_mint_receipt.py --kind proposers. Authorises nothing "
                       "while its status is not 'decided'.",
        "antecedents": {"analysis_recipe": {"path": f"{pkg}/analysis-recipe-v1.json", "sha256": shas["analysis-recipe-v1.json"]},
                        "protocol": {"path": f"{pkg}/protocol-registered-v1.json", "sha256": protocol_sha},
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
                         artefacts: Mapping[str, Mapping[str, str]] | None = None, commit: str | None = None) -> str:
    """DRAFT rows of the two text-only cells plus their offline READ row.

    The ``artifacts`` cell of a generation row is the REGISTERED PLAN PATH (the flip tool and the exposure gate resolve it as a repository
    path). The prompt / tables / archive / output pins live in the notes beside ``Plan SHA256``; the prompt hash is read from the
    instruction template at write time.
    """

    from speech_aware_evidence_acquisition.rails import tfrl_typed_proposer as tp  # noqa: PLC0415

    artefacts = artefacts or {}
    pkg = package_names(iteration)["proposers"]
    lines = [f"## Loop iteration {iteration}: typed proposer and ACE reflector cells (DRAFT, coordinator countersignature pending)", "",
             "| " + " | ".join(tp.LEDGER_COLUMNS) + " |", "| " + " | ".join("---" for _ in tp.LEDGER_COLUMNS) + " |"]
    for kind, i in ids.items():
        rt = runtime_identity(root, i["model_fragment"])
        art = artefacts.get(kind, {})
        prompt = art.get("prompt_sha256")
        if not prompt or prompt == "pending":
            prompt = sha_file(root, PROMPT_RELPATHS[kind])
        tables = art.get("tables_sha256") or NOT_BOUND
        archive = art.get("archive_sha256") or NOT_BOUND
        row = tp.draft_exposure_row(
            date=at[:10], run_id=i["run_id"], carrier_roster_id=Path(str(i["experiment"])).stem, split_identity_hash=i["split_identity_hash"],
            carriers=i["rows"], model_files_sha256=rt["files"], llama_cpp_build_commit=rt["build"],
            prompt_sha256=prompt, tables_sha256=tables, archive_sha256=archive, geometry=tf.SESSION, kind=kind)
        plan = f"{pkg}/{kind}-generation-plan-registered-v1.json"
        row["scope"] = "DRAFT -- " + row["scope"]
        row["artifacts"] = plan
        row["notes"] = (row["notes"] + f" Artefact pins: prompt sha256 {prompt} ({PROMPT_RELPATHS[kind]}); tables sha256 {tables}; "
                        f"archive sha256 {archive}; output sha256 recorded at the seal. DRAFT at study commit {commit or 'unrecorded'}; "
                        f"Plan SHA256 {shas.get(Path(plan).name, '0' * 64)}; nothing authorised.")
        lines.append(tp.ledger_markdown_row(row))
    lines.append(tp.ledger_markdown_row(draft_read_row(iteration, ids, at, pkg, commit)))
    return "\n".join(lines) + "\n"


def draft_read_row(iteration: int, ids: Mapping[str, Mapping], at: str, pkg: str, commit: str | None) -> dict:
    """The proposers' offline READ row (zero contacts), named by ``analysis-recipe-v1.json``."""

    typed = ids["typed"]
    return {
        "date": at[:10], "run/experiment id": proposers_read_run_id(iteration), "execution profile": "model-free-check",
        "scope": (f"DRAFT -- The offline validation / archive step of the loop iteration {iteration} proposer and reflector cells "
                  f"(tfrl_loop_driver.py --execute open --iter {iteration} --stage cell) by the recipe {pkg}/analysis-recipe-v1.json. "
                  "Zero model, server, encoder, embedder, tokenizer and GPU contacts."),
        "model/tool": "no model or tool contact; read of sealed bytes and CPU validation",
        "speech carrier + split": "slurp TRAIN construction, the sealed proposer and reflector cells (after the seal)",
        "split role": "discovery", "split identity hash": typed["split_identity_hash"], "consumed": "no", "calls": "0",
        "speech audio seconds": "0", "gpu hours": "0", "inherited exposure": "All prior SLURP exposure carried forward unchanged.",
        "artifacts": f"{pkg}/analysis-recipe-v1.json",
        "notes": (f"DRAFT. REGISTERED WITH THE FLIGHT (root countersignature pending; countersigned after the seal and before any proposal "
                  f"is read) {at[:10]} at study commit {commit or 'unrecorded'}. Claims no benefit."),
    }


LEDGER_COLUMNS = ["date", "run/experiment id", "execution profile", "scope", "model/tool", "speech carrier + split", "split role",
                  "split identity hash", "consumed", "calls", "speech audio seconds", "gpu hours", "inherited exposure", "artifacts", "notes"]
LEDGER_INHERITED = "TRAIN Fold B discovery rows already exposed by prior SLURP cells; this cell opens no split. Prior exposure is inherited in full."


def iteration_of(ids: Mapping[str, Mapping]) -> int:
    return int(ids["arm"]["experiment"].split("-i")[1].split("-")[0])


def recovery_ledger_text(iteration: int, ids: Mapping[str, Mapping], fit: bool) -> str:
    """The recovery wording of a recovered smoke's row notes: the failed attempt, its cause, the rec1 ids, the cumulative budget."""

    rec, smoke = tf.smoke_recovery(iteration), ids["smoke"]
    budget = recovery_budget(iteration, smoke)
    what = "FIT attempt" if fit else "attempt"
    predecessor = rec["predecessor_fit_attempt_id"] if fit else rec["predecessor_attempt_id"]
    state = ("never opened; request envelopes only, no model contact" if fit else
             f"OPENED, {budget['failed_attempt_spend']['model_calls']} contacts / {budget['failed_attempt_spend']['speech_audio_seconds']:g} "
             "speech-seconds spent, refused at preflight 2026-10-11T13:22Z at flight commit 6cbd9c707 on \"supply action 'ace' is invalid: "
             "knowledge store ace-playbook snapshot SHA-256 mismatch\"; the failed attempt is preserved unread")
    return (
        "RECOVERY RE-REGISTRATION (root-diagnosed, the cell's single one, 2026-10-11): this row SUPERSEDES the first-attempt row of the same "
        f"run id (a run id carries exactly one ledger row at launch; the coordinator folds the earlier row into this one when countersigning). "
        f"{what} {predecessor} {state}. Root cause: {rec['root_cause']}. The smoke is re-flown whole under the rec1 attempt ids "
        f"(generation {smoke['attempt_id']}; FIT {smoke['fit_attempt_id']}), a (run_id, attempt_id) pair being a one-time key; the plan budget "
        f"is run-cumulative across the attempts of the run id: the original plan plus the failed attempt's recorded spend, "
        f"{budget['original_plan']['planned_model_calls']} + {budget['failed_attempt_spend']['model_calls']} = "
        f"{budget['cumulative_plan']['planned_model_calls']} calls and {budget['original_plan']['planned_speech_audio_seconds']} + "
        f"{budget['failed_attempt_spend']['speech_audio_seconds']:g} = {budget['cumulative_plan']['planned_speech_audio_seconds']} "
        f"speech-seconds; the FIT cap stays structural ({smoke['family_budget']['fit_endpoint_calls_cap']}, not scaled); the arm is untouched. "
        "A second failure closes the cell.")


def column_row_cells(iteration: int, ids: Mapping[str, Mapping], kind: str, fit: bool, commit: str, at: str, arms: list[str], pkg: str,
                     shas: Mapping[str, str]) -> list[str]:
    scope = (f"DRAFT -- REGISTERED. Frozen core, np4 session; the review-off COMP-1b module graph at lock v2.3 (v2.2 plus the empty ace-playbook-i0 declaration) with the Solver supply "
             f"arms {', '.join(arms)} (program {ids['arm']['program']}); no tool authority on any role")
    i = ids[kind]
    recovered = kind == "smoke" and tf.smoke_recovery(iteration) is not None
    plan = f"{pkg}/{tf.plan_file_name(iteration, kind, 'fit' if fit else 'generation')}"
    calls = i["family_budget"]["fit_endpoint_calls_cap" if fit else "generation_calls_cap"]
    notes = f"DRAFT at study commit {commit}; Plan SHA256 {shas.get(Path(plan).name, 'pending')}; nothing authorised."
    if recovered:
        notes += " " + recovery_ledger_text(iteration, ids, fit)
    return [at[:10], i["fit_run_id"] if fit else i["run_id"], i["execution_profile"],
            scope + (" -- FIT spend identity" if fit else "") + (" -- SMOKE RECOVERY rec1" if recovered else ""),
            "frozen core (attach only)", f"slurp TRAIN Fold B {i['rows']}", "discovery", i["split_identity_hash"], "no", str(calls),
            str(i["family_budget"]["repeated_speech_audio_seconds_cap"]), str(i["family_budget"]["gpu_hours_fit_inclusive"]),
            LEDGER_INHERITED, plan, notes]


def table_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.replace("|", "/") for c in cells) + " |"


def recovery_ledger_rows(ids: Mapping[str, Mapping], commit: str, at: str, arms: list[str], pkg: str, shas: Mapping[str, str]) -> str:
    """ONLY the recovered smoke's two DRAFT rows (generation, FIT), as continuing rows for the existing column block of the ledger."""

    iteration = iteration_of(ids)
    if not tf.smoke_recovery(iteration):
        raise SystemExit(f"iteration {iteration} has no smoke recovery")
    return "\n".join(table_row(column_row_cells(iteration, ids, "smoke", fit, commit, at, arms, pkg, shas)) for fit in (False, True)) + "\n"


def draft_column_rows(ids: Mapping[str, Mapping], commit: str, at: str, arms: list[str], pkg: str, shas: Mapping[str, str]) -> str:
    cols, inherited = LEDGER_COLUMNS, LEDGER_INHERITED
    iteration = iteration_of(ids)
    lines = [f"## Loop iteration column cell (DRAFT, coordinator countersignature pending) -- {pkg}", "",
             "| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for kind in ("arm", "smoke"):
        for fit in (False, True):
            lines.append(table_row(column_row_cells(iteration, ids, kind, fit, commit, at, arms, pkg, shas)))
    arm = ids["arm"]
    read_id = tf.names(iteration, "arm")["read_run_id"]
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


def append_recovery_rows(root: Path, pkg: str, rows_text: str, marker: str) -> bool:
    """Insert the recovery rows right after the package's last ledger row (continuing the existing column table); idempotent on ``marker``
    (the rec1 attempt id, which only the recovery rows carry). Returns whether the ledger changed."""

    path = Path(root) / LEDGER
    text = io.open(path, encoding="utf-8", newline="").read()
    if marker in text:
        return False
    lines = text.split("\n")
    hits = [k for k, line in enumerate(lines) if line.startswith("| ") and f"{pkg}/" in line]
    if not hits:
        raise SystemExit(f"ledger: no row of {pkg} to append the recovery rows beside")
    lines[hits[-1] + 1:hits[-1] + 1] = rows_text.rstrip("\n").split("\n")
    io.open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return True


def write_iteration(root: Path, iteration: int, spec: Mapping[str, Any], commit: str, at: str, *, predicted_effect_pp: float = 0.0,
                    with_proposers: bool = True, append_ledger: bool = False, append_recovery_ledger: bool = False,
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
        artefacts = {k: {"tables_sha256": (pins[k].get("tables") or {}).get("sha256", "")} for k in ("typed", "ace") if k in pins}
        rows = draft_text_only_rows(root, iteration, proposers["ids"], proposers["shas"], at, artefacts, commit)
        proposers["shas"]["draft-ledger-rows.md"] = wr(root, f"{proposers['package']}/draft-ledger-rows.md", rows)
        result["proposers"] = {"package": proposers["package"], "shas": proposers["shas"]}
        ledger_text += "\n" + rows
    if append_ledger:
        ledger = Path(root) / LEDGER
        current = ledger.read_text(encoding="utf-8")
        ledger.write_text(current.rstrip("\n") + "\n\n" + ledger_text, encoding="utf-8", newline="\n")
        result["ledger_appended"] = True
    if append_recovery_ledger:
        ids = column["ids"]
        rows_text = recovery_ledger_rows(ids, commit, at, column["arms"], column["package"], column["shas"])
        result["recovery_ledger_appended"] = append_recovery_rows(root, column["package"], rows_text, ids["smoke"]["attempt_id"])
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
    parser.add_argument("--append-recovery-ledger", action="store_true",
                        help="coordinator's act: insert ONLY the recovered smoke's two DRAFT rows (rec1) beside the package's existing ledger rows "
                             "(idempotent; the countersigned rows are not edited)")
    args = parser.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8")) if args.spec else default_spec(args.iteration)
    result = write_iteration(Path(args.root), args.iteration, spec, args.study_commit, args.registered_at,
                             predicted_effect_pp=args.predicted_effect_pp, with_proposers=False, append_ledger=args.append_ledger,
                             append_recovery_ledger=args.append_recovery_ledger)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
