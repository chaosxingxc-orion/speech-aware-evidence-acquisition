"""Bind one manual natural four-row plan pair; grant neither contacts nor READ."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path

from ..contracts import ExecutionPlan
from ..core.config import _canonical_hash, compose, drop_null_arms, protocol_hash
from ..core.flight.campaign import load_campaign_cells
from ..data.splits import prefixed, split_identity_hash
from .controllers import default_phase_program
from .experiment_population import ARCHITECTURE_VERSION, load_population_config, require_population_binding
from .hashing import content_hash
from .native_episode_config import load_native_episode_config
from .system_context_structural_entry import qualify_architecture_capacity_family
from .system_text_policy import _read_pin, require


def _qualified_capacity(population, pin, prerequisite, *, repo_root, data_root):
    """Recompute the existing qualifier from its pinned original evidence."""
    require(data_root is not None and isinstance(prerequisite, dict)
            and set(prerequisite) == {"registration", "qualification"}, "exact capacity prerequisite required")
    root = Path(data_root).resolve()
    registration = json.loads(_read_pin(prerequisite["registration"], root))
    qualification = json.loads(_read_pin(prerequisite["qualification"], root))
    entry = Path(registration["new_receipt_root"]).resolve()
    require(entry.is_relative_to(root)
            and (root / prerequisite["registration"]["relpath"]).resolve() == entry / "registration-v1.json"
            and (root / prerequisite["qualification"]["relpath"]).resolve() == entry / "capacity-qualified-v1.json",
            "capacity prerequisite differs from its original entry")
    require(qualification["schema"] == "saea-simple-consumption-capacity-root-qualification-v1"
            and qualification["runtime_admission"] is False, "completed capacity qualification required")
    evidence = {}
    for item in qualification["evidence"]:
        path = Path(item["path"]).resolve()
        require(path.is_relative_to(root) and path not in evidence, "capacity evidence escapes or repeats")
        evidence[path] = json.loads(_read_pin(
            {"relpath": path.relative_to(root).as_posix(), "sha256": item["sha256"]}, root))
    require(content_hash(evidence[entry / "registration-v1.json"]) == content_hash(registration),
            "qualification registration differs from the independently pinned original")
    source_pin, = registration["frozen_preflight_receipts"]
    source = json.loads(_read_pin({"relpath": Path(source_pin["path"]).resolve().relative_to(root).as_posix(),
                                  "sha256": source_pin["sha256"]}, root))
    require(content_hash(source) == content_hash(evidence[Path(source_pin["path"]).resolve()]) and source["passed"] is True
            and source["commit"] == source["source_commit"] == registration["worker_commit"],
            "capacity source check is not bound to the original worker")
    members = registration["members"]
    graph_hashes = {}
    for member in members:
        graph, = load_campaign_cells(repo_root, member["graph"])
        g = graph.document
        config = compose(repo_root, g["model_fragment"], g["dataset_fragment"], g["baseline_fragment"], member["graph"])
        require(config.config_hash == member["graph_config_hash"]
                and config.values["populations"][0]["ids"] == member["graph_sample_ids"],
                "capacity member graph differs from its independently composed source")
        graph_hashes[member["label"]] = config.config_hash
    result = qualify_architecture_capacity_family(
        population, pin, registration, evidence[entry / "capacity-finished.json"],
        evidence[entry / "capacity-task-exit.json"],
        {m["label"]: evidence[entry / m["label"] / "request-fit-v1.json"] for m in members},
        original_registration=evidence[entry / "registration-v1.json"],
        member_terminals={m["label"]: evidence[entry / (m["label"] + "-capacity-finished.json")] for m in members},
        policy_config_bytes={m["label"]: _read_pin(m["execution_config"], repo_root) for m in members},
        source_check=source, output_reserve=512, structural_reserve=2048, slot_tokens=24576,
        graph_config_hashes=graph_hashes)
    require(content_hash(qualification["result"]) == content_hash(result),
            "capacity qualification differs from its original evidence")
    return registration, result


def require_architecture_natural_registration(values, cell, registered_plans, *, repo_root, data_root=None):
    """Validate exactly one generation/FIT pair for the qualified four-row roster.

    Both ordinary registered plan schemas add architecture_proof='natural-four-row-v1',
    plan_role ('generation' or 'fit'), member/cohort/sample_ids, policy/supply pins,
    zero official_score_jobs, false scientific_feedback/learner_export, and identical
    capacity_prerequisite {registration, qualification} DATA-relative SHA256 pins.
    The latter points to the existing original capacity entry and root qualification;
    its actual result/evidence/source_commit keys are verified, not reinterpreted.
    Historical and nongenerative capacity admission are separate and unchanged.
    """
    from ..analysis.native_graph_rehearsal import rehearsal_profile
    from ..core.preparation_fit import validate_native_contact_fit_config

    require(isinstance(registered_plans, list) and len(registered_plans) == 2
            and all(isinstance(p, dict) for p in registered_plans)
            and {p.get("plan_role") for p in registered_plans} == {"generation", "fit"},
            "natural proof requires exactly one generation and one FIT plan")
    plans = {p["plan_role"]: p for p in registered_plans}
    require(cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker"],
            "natural proof permits only check/prepare-supply/worker")
    require(not any(k in values for k in ("system_context_learning", "system_search_learning", "system_optimization"))
            and values.get("stage3_algorithm", {}).get("id") == "none"
            and values["stage3_algorithm"].get("operators_used") == []
            and values.get("stage3_measurement", {}).get("claims_benefit") is False,
            "natural proof cannot admit learning or scientific feedback")
    pin = values["experiment_population"]
    population = load_population_config(pin, repo_root=repo_root, allow_architecture=True)
    require(population["schema"] == ARCHITECTURE_VERSION, "natural proof requires explicit V4 architecture")
    identity, = [m for m in population["architecture"]["members"]
                if m["member_id"] == values["architecture_member"] and m["cohort_id"] == values["population_cohort"]]
    cohort = require_population_binding(population, pin, identity["cohort_id"], values, *registered_plans)
    require(plans["generation"]["capacity_prerequisite"] == plans["fit"]["capacity_prerequisite"],
            "natural plan pair has different capacity prerequisites")
    capacity, qualified = _qualified_capacity(population, pin, plans["generation"]["capacity_prerequisite"],
                                              repo_root=repo_root, data_root=data_root)
    member, = [m for m in capacity["members"] if m["member_id"] == identity["member_id"]]
    graph, = load_campaign_cells(repo_root, member["graph"])
    g = graph.document
    graph_config = compose(repo_root, g["model_fragment"], g["dataset_fragment"], g["baseline_fragment"], member["graph"])
    roster = values["populations"][0]["ids"]
    require(len(values["populations"]) == 1 and type(values["population"]["count"]) is int
            and values["population"]["count"] == len(roster) == 4 and len(set(roster)) == 4
            and set(roster) <= set(cohort["sample_ids"])
            and roster == member["graph_sample_ids"] == graph_config.values["populations"][0]["ids"]
            and graph_config.config_hash == member["graph_config_hash"], "natural four-row graph binding differs")
    policy = drop_null_arms(json.loads(_read_pin(identity["execution_config"], repo_root)))
    require(all(values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
            "natural effective policy differs from its pinned member")
    program = default_phase_program(values["policy"])
    native = load_native_episode_config(values, program)
    require(native is not None and native.max_contacts == identity["model_per_trajectory"]
            and [r for r in population["nodes"] if native.role(r).max_iterations > 0] == identity["active_roles"],
            "natural role/contact identity differs")
    require(values["native_graph_capacity_profile"] == member["rehearsal_profile"], "natural profile differs")
    rehearsal_profile(values, member["rehearsal_profile"])
    require(all(values.get("decoding_params", {}).get(k) == v for k, v in population["sampling"].items())
            and all(values["system_search_measurement"].get(k) == v for k, v in population["execution"].items())
            and values["serving_slots"] == population["execution"]["slot_count"]
            and values["serving_slot_tokens"] == 24576, "natural sampling/execution geometry differs")
    fit = validate_native_contact_fit_config(values, program)
    generation_cap = 4 * native.max_contacts
    fit_cap = generation_cap * population["contact_limits"]["fit_endpoints_per_model_contact"]
    require(fit is not None and fit.get("max_speech_packets", 1) == 1 and type(fit["contact_cap"]) is int
            and fit["contact_cap"] == fit_cap and fit["run_id"] != cell["run_id"]
            and fit["attempt_id"] != cell["attempt_id"], "natural FIT identity or ceiling differs")
    expected_budget = dict(complete_system_trajectories=4, generation_calls_cap=generation_cap,
                           actual_request_fit_endpoint_cap=fit_cap, official_complete_scoring_jobs=0)
    require(content_hash(values["family_budget"]) == content_hash(expected_budget), "natural family budget differs")
    config_hash = _canonical_hash(values)
    split = split_identity_hash(prefixed("slurp", roster))
    require(values["population"]["split_identity_hash"] == split, "natural split identity differs")
    expected = ExecutionPlan(**values["execution_plan"], run_id=cell["run_id"], attempt_id=cell["attempt_id"],
                            carrier_lock_key="slurp", split_identity_hash=split,
                            protocol_hash=protocol_hash(config_hash, values["arm"], split)).validate()
    require(expected.planned_model_calls == generation_cap and type(expected.planned_model_calls) is int
            and expected.execution_profile == "bounded-discovery-probe" and expected.split_role == "discovery",
            "natural generation plan differs")
    for role, document in plans.items():
        bound_plan = expected if role == "generation" else replace(expected, run_id=fit["run_id"],
                                                                  attempt_id=fit["attempt_id"], planned_model_calls=fit_cap)
        require(document.get("schema") == f"saea-registered-{role}-plan-v1"
                and document.get("architecture_proof") == "natural-four-row-v1"
                and str(document.get("status", "")).upper().startswith("ROOT COUNTERSIGNED BEFORE CONTACT")
                and document.get("architecture_member") == identity["member_id"]
                and document.get("cell") == cell["cell_id"] and document.get("experiment") == cell["cell_id"]
                and document.get("composed_config_hash") == config_hash and document.get("sample_ids") == roster
                and document.get("policy_binding") == cell["system_text_policy_binding"]
                and cell["system_text_policy_binding"]["bundle_id"] == identity["base_bundle_id"]
                and document.get("prepared_phase_supply") == values["prepared_phase_supply"]
                and document.get("run_id", bound_plan.run_id) == bound_plan.run_id
                and document.get("attempt_id", bound_plan.attempt_id) == bound_plan.attempt_id
                and content_hash(document["execution_plan"]) == content_hash(asdict(bound_plan))
                and type(document.get("official_score_jobs")) is int and document["official_score_jobs"] == 0
                and document.get("scientific_feedback") is False and document.get("learner_export") is False,
                "natural registered plan differs from its exact configuration, scope or identity")
    return dict(member_id=identity["member_id"], sample_ids=deepcopy(roster), generation_cap=generation_cap,
                fit_cap=fit_cap, capacity_registration_sha256=qualified["registration_sha256"],
                capacity_source_commit=capacity["worker_commit"], runtime_admission=False, read_authorized=False)
