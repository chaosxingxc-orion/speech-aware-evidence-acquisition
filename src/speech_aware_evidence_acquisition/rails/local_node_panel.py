"""Strict source and policy custody for the opt-in local node panel.

This is configuration preparation, never a node executor or admission authority.
Reuse the existing complete native runtime, capacity, structural and scoring paths.
"""
from copy import deepcopy
import json
import re
from pathlib import Path

from ..core.config import drop_null_arms, compose
from .system_text_policy import _pin, _read_pin, require
from .experiment_population import load_population_config

SELECTOR = "local-solver-panel-v1"
REVIEWER_SELECTOR = "local-reviewer-panel-v1"
SELECTORS = (SELECTOR, REVIEWER_SELECTOR)
MAP_SCHEMA = "saea-local-node-panel-execution-identity-map-v1"
SOURCE_RECEIPT = {
    "relpath": "docs/readiness/2026-10-08-slurp-simple-consumption-n100-audio-recovery1-entry2-v1/registered-v1/review-off-preparation-receipt-final-v1.json",
    "sha256": "7ea5e10254f4c74282cd799500bb8b8c03dd3475f23703756386e983d6651f97",
}
REVIEWER_SOURCE_RECEIPT = {
    "relpath": "docs/readiness/2026-10-08-slurp-simple-consumption-n100-audio-recovery1-entry2-v1/registered-v1/seed-preparation-receipt-final-v1.json",
    "sha256": "fa1763cc40fb4f7f47851b755c5cbdaaad1a398bbfc9e50412f2bd8a5be91450",
}

SOURCE_POPULATION = {
    "relpath": "configs/experiments/slurp-simple-consumption-architecture-n100-v1.json",
    "sha256": "de6bf4b06433f04b16b10bda04d6691d9db93705b92a48f280dc948ce73c4c9d",
}


def require_local_role_policy(source, candidate, *, repo_root, target_role, control=False):
    """Permit only the named role text change, including content-addressed relocation."""
    require(target_role in {"solver", "reviewer"}, "unknown local target role")
    normalized = []
    texts = []
    for policy in (source, candidate):
        value = drop_null_arms(deepcopy(policy))
        value.pop("what_this_is", None)
        material = value.get("phase_material", {})
        params = [c["params"] for c in value["native_episode"]["consumption_module"]["components"]
                  if c["component_id"] == "knowledge-consumption-opportunity"]
        require(len(params) == 1, "local node requires one existing knowledge opportunity")
        role_texts = {}
        for role in ("perception", "solver", "reviewer", "planner"):
            relative = material[role]["instruction_template"]
            path = (Path(repo_root) / "configs" / relative).resolve()
            require(path.is_relative_to(Path(repo_root).resolve() / "configs"),
                    "local node template escapes configs")
            role_texts[role] = path.read_bytes()
            require(params[0].get(role + "_template") == relative,
                    "local node module and material template binding differ")
            material[role]["instruction_template"] = "<bound-" + role + "-template>"
            params[0][role + "_template"] = material[role]["instruction_template"]
        normalized.append(value)
        texts.append(role_texts)
    require(normalized[0] == normalized[1], "local node policy has non-target configuration drift")
    for role in ("perception", "solver", "reviewer", "planner"):
        if role == target_role:
            continue
        require(texts[0][role] == texts[1][role], "local node policy has non-target role text drift")
    if control:
        require(texts[0][target_role] == texts[1][target_role],
                "local control/A/A must preserve the source target-role request text")
    return {"target_text_changed": texts[0][target_role] != texts[1][target_role]}


def require_local_node_basis(basis, population, *, repo_root, data_root=None):
    """Anchor the complete original N100 roster without inheriting old template proof."""
    require(isinstance(basis, dict) and set(basis) == {
        "schema", "target_role", "source_preparation_receipt", "source_population", "proposal_custody"}
        and basis["schema"] == "saea-local-node-panel-basis-v1"
        and basis["target_role"] in {"solver", "reviewer"}
        and basis["source_preparation_receipt"] == (SOURCE_RECEIPT if basis["target_role"] == "solver" else REVIEWER_SOURCE_RECEIPT)
        and basis["source_population"] == SOURCE_POPULATION, "local node original basis pin differs")
    custody = basis["proposal_custody"]
    require(isinstance(custody, dict) and set(custody) == {"registration", "validation"},
            "local node original proposal custody is required")
    for value in custody.values():
        _pin(value)
    old = load_population_config(SOURCE_POPULATION, repo_root=repo_root, allow_architecture=True)
    receipt = json.loads(_read_pin(basis["source_preparation_receipt"], repo_root))
    source = drop_null_arms(json.loads(_read_pin(receipt["source_policy"], repo_root)))
    require(len(population["cohorts"]) == 1, "local node requires one complete configured cohort")
    cohort = population["cohorts"][0]
    ids = old["cohorts"][0]["sample_ids"]
    require(cohort["sample_ids"] == ids == receipt["configured_sample_ids"]
            and len(ids) == len(set(ids)) == 100
            and population["sampling"] == old["sampling"]
            and population["execution"] == old["execution"]
            and population["contact_limits"]["fit_endpoints_per_model_contact"]
            == old["contact_limits"]["fit_endpoints_per_model_contact"],
            "local node original roster, sampling, geometry or FIT accounting drift")
    require(receipt.get("contacts") == 0 and type(receipt["contacts"]) is int
            and receipt.get("output_equal") is True and receipt.get("warm_verified") is True
            and receipt.get("runtime_admission") is False, "local node original preparation custody differs")
    for member in population["architecture"]["members"]:
        require(member["active_roles"] == (["perception", "solver"] if basis["target_role"] == "solver"
                                                   else ["perception", "solver", "reviewer", "planner"]),
                "local node active roles differ from the pinned source topology")
        candidate = drop_null_arms(json.loads(_read_pin(member["execution_config"], repo_root)))
        require_local_role_policy(source, candidate, repo_root=repo_root, target_role=basis["target_role"],
                                   control=member["member_id"] in cohort["control_ids"])
        from .controllers import default_phase_program
        from .native_episode_config import load_native_episode_config
        native = load_native_episode_config({**candidate, "carrier_lock_key": "slurp"}, default_phase_program(candidate["policy"]))
        require(native.review_loop_enabled == (basis["target_role"] == "reviewer")
                and native.max_contacts == member["model_per_trajectory"]
                == population["contact_limits"]["model_per_trajectory"],
                "local node topology or configured contact bound differs")
    if data_root is not None:
        registration = json.loads(_read_pin(custody["registration"], data_root))
        require(registration.get("schema") == "saea-local-" + basis["target_role"] + "-proposer-contact-plan-v1"
                and registration.get("status") == "ROOT_COUNTERSIGNED_AND_POSITIONS_RESERVED_BEFORE_CONTACT"
                and registration.get("runtime_admission") is False
                and isinstance(registration.get("design_slots"), list)
                and len(registration["design_slots"]) == len(cohort["candidate_ids"])
                and all(isinstance(slot, str) and bool(slot) for slot in registration["design_slots"])
                and len(set(registration["design_slots"])) == len(registration["design_slots"]),
                "local node original actor allocation scope differs")
        validation = json.loads(_read_pin(custody["validation"], data_root))
        require(validation.get("schema") == "saea-local-node-original-proposal-validation-v1"
                and validation.get("status") == "ROOT_VALIDATED_ORIGINAL_PROPOSALS"
                and validation.get("target_role") == basis["target_role"]
                and validation.get("proposal_registration") == custody["registration"]
                and validation.get("candidate_ids") == cohort["candidate_ids"]
                and validation.get("runtime_admission") is False
                and isinstance(validation.get("members"), dict)
                and set(validation["members"]) == set(cohort["candidate_ids"])
                and isinstance(validation.get("original_design_slot"), dict)
                and set(validation["original_design_slot"]) == set(cohort["candidate_ids"])
                and [validation["original_design_slot"][candidate] for candidate in cohort["candidate_ids"]]
                == registration["design_slots"],
                "local node original proposal validation scope or allocation mapping differs")
        for member in population["architecture"]["members"]:
            if member["member_id"] in cohort["candidate_ids"]:
                proposal = validation["members"][member["member_id"]]
                require(proposal.get("execution_config") == member["execution_config"]
                        and proposal.get("base_bundle_id") == member["base_bundle_id"],
                        "local node original allocation or compiled policy binding differs")
        from ..core.preparation import digest
        original = json.loads(_read_pin(receipt["prepared_phase_supply"], data_root))
        parent = json.loads(_read_pin(receipt["source_prepared_phase_supply"], data_root))
        output = parent["output"]
        require(parent["output_sha256"] == digest(output)
                and set(output) == {"facets", "values"} and output["facets"] == {}
                and set(output["values"]) == {"perception"}
                and set(ids) <= set(output["values"]["perception"]), "local node parent supply seal differs")
        selected = {"facets": {}, "values": {"perception": {
            sid: output["values"]["perception"][sid] for sid in ids}}}
        require(original["output"] == selected
                and original["output_sha256"] == receipt["output_sha256"] == digest(selected),
                "local node original N100 supply output differs")
    return receipt


def require_local_identities(rows, *, source_cell, source_fit):
    """Refuse duplicates, path injection and any reuse of original spend identities."""
    keys = {"member_id", "experiment", "cell_id", "run_id", "attempt_id", "fit_run_id", "fit_attempt_id"}
    require(isinstance(rows, list) and bool(rows), "local node identities must be an ordered nonempty list")
    for row in rows:
        require(isinstance(row, dict) and set(row) == keys
                and all(isinstance(row[k], str) and row[k] for k in keys)
                and row["experiment"] == row["cell_id"]
                and re.fullmatch(r"[a-z0-9][a-z0-9-]*", row["experiment"]),
                "local node execution identity fields differ")
    runs = [v for row in rows for v in (row["run_id"], row["fit_run_id"])]
    attempts = [v for row in rows for v in (row["attempt_id"], row["fit_attempt_id"])]
    require(len({r["member_id"] for r in rows}) == len(rows)
            and len({r["experiment"] for r in rows}) == len(rows)
            and len(set(runs)) == len(runs) and len(set(attempts)) == len(attempts)
            and not set(runs).intersection((source_cell["run_id"], source_fit["run_id"]))
            and not set(attempts).intersection((source_cell["attempt_id"], source_fit["attempt_id"])),
            "local node identities duplicate or reuse the source attempt")
    require(all(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", v) for v in runs + attempts),
            "local node spend identity is not path-safe")


def local_node_documents(source_experiment, source_baseline, policy, identity, *,
                           policy_binding, population_pin, cohort_id, stage, basis, report):
    """Build held native configs with exact configuration-derived complete-path budgets."""
    ep, bp = deepcopy(source_experiment), deepcopy(source_baseline)
    bp.update({k: deepcopy(v) for k, v in drop_null_arms(policy).items() if k != "what_this_is"})
    bp.pop("prepared_phase_supply", None)
    bp.pop("architecture_extent", None)
    bp.update(experiment_population=deepcopy(population_pin), population_cohort=cohort_id,
              population_budget=deepcopy(stage["population_budget"]), local_node_basis=deepcopy(basis))
    label = identity["member_id"]
    calls = stage["member_generation_contacts_caps"][label]
    endpoints = stage["member_fit_endpoints_caps"][label]
    require(calls == stage["N"] * report["max_contacts_per_sample"],
            "local node configured model bound differs from parsed topology")
    bp["native_contact_fit"].update(run_id=identity["fit_run_id"], attempt_id=identity["fit_attempt_id"],
                                     contact_cap=endpoints)
    ep.update(experiment_id=identity["run_id"], architecture_member=label)
    ep["execution_plan"].update(planned_model_calls=calls,
                               planned_speech_audio_seconds=report["required_integer_audio_seconds"])
    ep["family_budget"] = {"complete_system_trajectories": stage["N"], "generation_calls_cap": calls,
                           "actual_request_fit_endpoint_cap": endpoints, "official_complete_scoring_jobs": 1}
    ep["stage3_measurement"]["claims_benefit"] = False
    cell = ep["cells"][0]
    cell.update(cell_id=identity["cell_id"], baseline_fragment=identity["experiment"],
                run_id=identity["run_id"], attempt_id=identity["attempt_id"],
                system_text_policy_binding=deepcopy(policy_binding),
                readiness={"state": "held", "reason": "Local node preparation; fresh capacity, structural proof and exact root admission pending.",
                           "requirements": []})
    return ep, bp


def mapped_local_node_cells(mapping, population, population_pin, *, repo_root):
    """Resolve the named opt-in map without accepting the old successor projection."""
    require(isinstance(mapping, dict) and set(mapping) == {
        "schema", "experiment_population", "architecture_extent", "local_node_basis", "members"}
        and mapping["schema"] == MAP_SCHEMA and mapping["experiment_population"] == population_pin
        and mapping["architecture_extent"] is None, "local node execution map scope differs")
    receipt = require_local_node_basis(mapping["local_node_basis"], population, repo_root=repo_root)
    from ..core.flight.campaign import load_campaign_cells
    source_cell, = load_campaign_cells(repo_root, receipt["experiment"])
    source = compose(repo_root, source_cell.document["model_fragment"], source_cell.document["dataset_fragment"],
                     source_cell.document["baseline_fragment"], receipt["experiment"])
    rows = mapping["members"]
    identities = [{k: v for k, v in row.items() if k != "planned_speech_audio_seconds"} for row in rows]
    require_local_identities(identities, source_cell=source_cell.document, source_fit=source.values["native_contact_fit"])
    require([r["member_id"] for r in rows] == [m["member_id"] for m in population["architecture"]["members"]],
            "local node ordered map membership differs")
    result = []
    for row in rows:
        require(set(row) == set(identities[0]) | {"planned_speech_audio_seconds"}
                and type(row["planned_speech_audio_seconds"]) is int and row["planned_speech_audio_seconds"] > 0,
                "local node mapped audio bound differs")
        cell, = load_campaign_cells(repo_root, row["experiment"])
        c = cell.document
        require(c["cell_id"] == row["cell_id"] and c["run_id"] == row["run_id"]
                and c["attempt_id"] == row["attempt_id"] and c["baseline_fragment"] == row["experiment"]
                and c["model_fragment"] == source_cell.document["model_fragment"]
                and c["dataset_fragment"] == source_cell.document["dataset_fragment"],
                "local node mapped native cell differs")
        configured = compose(repo_root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], row["experiment"])
        require(configured.values.get("local_node_basis") == mapping["local_node_basis"]
                and configured.values.get("architecture_extent") is None
                and configured.values["experiment_population"] == population_pin
                and configured.values["architecture_member"] == row["member_id"]
                and configured.values["native_contact_fit"]["run_id"] == row["fit_run_id"]
                and configured.values["native_contact_fit"]["attempt_id"] == row["fit_attempt_id"]
                and configured.values["execution_plan"]["planned_speech_audio_seconds"]
                == row["planned_speech_audio_seconds"], "local node mapped configuration differs")
        from .experiment_population import population_stage_spec
        from .architecture_audio_budget import derive_manual_architecture_audio_budget
        member, = [m for m in population["architecture"]["members"] if m["member_id"] == row["member_id"]]
        stage = population_stage_spec(population_pin, repo_root=repo_root, cohort_id=member["cohort_id"], allow_architecture=True)
        policy = json.loads(_read_pin(member["execution_config"], repo_root))
        source_exp = json.loads((Path(repo_root) / "configs/experiment" / (receipt["experiment"] + ".json")).read_bytes())
        source_base = json.loads((Path(repo_root) / "configs/baseline" / (source_cell.document["baseline_fragment"] + ".json")).read_bytes())
        report = derive_manual_architecture_audio_budget(configured.values)
        expected_exp, expected_base = local_node_documents(source_exp, source_base, policy, identities[len(result)],
            policy_binding=c["system_text_policy_binding"], population_pin=population_pin, cohort_id=member["cohort_id"],
            stage=stage, basis=mapping["local_node_basis"], report=report)
        actual_exp = json.loads((Path(repo_root) / "configs/experiment" / (row["experiment"] + ".json")).read_bytes())
        actual_base = json.loads((Path(repo_root) / "configs/baseline" / (row["experiment"] + ".json")).read_bytes())
        for exp in (expected_exp, actual_exp):
            exp["cells"][0].pop("readiness", None)
        actual_base.pop("prepared_phase_supply", None)
        require(expected_exp == actual_exp and expected_base == actual_base,
                "local node mapped configuration has drift outside the exact prepared projection")
        result.append((row["member_id"], cell, configured))
    return result
