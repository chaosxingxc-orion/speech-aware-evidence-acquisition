"""Pinned population configuration shared by experiment stages; grants no admission."""
from __future__ import annotations

import json
from copy import deepcopy
from .system_text_policy import _pin, _read_pin, require, sha
from .hashing import content_hash


ARCHITECTURE_VERSION = "saea-experiment-population-config-v4"


def _fields(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), label)


def _positive(value):
    return type(value) is int and value > 0


def _names(value):
    return (isinstance(value, list) and bool(value)
            and all(isinstance(x, str) and x and x.isascii() for x in value)
            and len(set(value)) == len(value))


def validate_population_config(document, *, allow_architecture=False):
    """Validate structure and implemented capabilities, not an experiment allowance.

    Candidate counts, cohort counts, sample counts and budgets have no defaults.
    Version 3 records boundary resources without cache writes or restarts.
    Version 4 explicitly represents manually specified execution architectures,
    with no semantic proposals or learner export and heterogeneous active roles.
    Historical version 2 retains its exact maintenance contract.
    Their single source is this document. The supported role set and deterministic
    sampling are executor/research constraints, not proposed population sizes.
    """
    require(isinstance(document, dict), "population config must be an object")
    version = document.get("schema")
    require(version != ARCHITECTURE_VERSION or allow_architecture is True,
            "manual profile requires explicit architecture opt-in; not a template-learning population")
    fields = ("schema", "experiment_id", "nodes", "sampling", "execution",
              "proposer", "contact_limits", "cohorts")
    if version in ("saea-experiment-population-config-v2", "saea-experiment-population-config-v3", ARCHITECTURE_VERSION):
        fields += ("boundary_maintenance",)
    if version == ARCHITECTURE_VERSION:
        fields += ("architecture",)
    _fields(document, fields, "population config fields differ")
    require(version in ("saea-experiment-population-config-v1", "saea-experiment-population-config-v2",
                        "saea-experiment-population-config-v3", ARCHITECTURE_VERSION)
            and isinstance(document["experiment_id"], str) and document["experiment_id"]
            and document["experiment_id"].isascii(), "population config identity differs")
    if version in ("saea-experiment-population-config-v2", "saea-experiment-population-config-v3", ARCHITECTURE_VERSION):
        maintenance = document["boundary_maintenance"]
        required = {
            "mode": ("observe-only" if version != "saea-experiment-population-config-v2"
                     else "root-coordinated-clean-page-cache"),
            "when": "after-complete-cohort",
            "require_generation_scoring_preprocessing_idle": True,
            "preserve_model_service": True,
            "global_sync": False,
            "record_before_after": True,
        }
        _fields(maintenance, required, "boundary maintenance fields differ")
        require(all(type(maintenance[k]) is type(v) and maintenance[k] == v
                    for k, v in required.items()), "unsupported boundary maintenance policy")
    require(_names(document["nodes"])
            and set(document["nodes"]) == {"perception", "solver", "reviewer", "planner"},
            "configured nodes must resolve to the implemented complete system")
    sampling = document["sampling"]
    _fields(sampling, ("temperature", "seed"), "explicit sampling required")
    require(type(sampling["temperature"]) in (int, float) and sampling["temperature"] == 0
            and type(sampling["seed"]) is int and sampling["seed"] >= 0,
            "deterministic sampling and an explicit seed required")
    execution = document["execution"]
    _fields(execution, ("slot_count", "queue_depth", "schedule"), "explicit execution geometry required")
    require(_positive(execution["slot_count"]) and _positive(execution["queue_depth"])
            and execution["schedule"] == "sequential-trajectory", "unsupported execution geometry")
    proposer = document["proposer"]
    if version == ARCHITECTURE_VERSION:
        require(proposer is None, "manual architecture comparisons have no proposer")
    else:
        _fields(proposer, ("model", "reasoning_effort", "semantic_batches"), "explicit proposer configuration required")
        require(all(isinstance(proposer[k], str) and proposer[k] and proposer[k].isascii()
                    for k in ("model", "reasoning_effort")) and _positive(proposer["semantic_batches"]),
                "invalid proposer configuration")
    limits = document["contact_limits"]
    _fields(limits, ("model_per_trajectory", "fit_endpoints_per_model_contact"), "explicit contact limits required")
    require(all(_positive(v) for v in limits.values()), "positive contact limits required")
    cohorts = document["cohorts"]
    require(isinstance(cohorts, list) and cohorts, "explicit population cohorts required")
    seen_cohorts, seen_candidates = set(), set()
    for cohort in cohorts:
        _fields(cohort, ("cohort_id", "candidate_ids", "control_ids", "sample_ids"), "cohort fields differ")
        identity = cohort["cohort_id"]
        require(isinstance(identity, str) and identity and identity.isascii()
                and identity not in seen_cohorts, "unique cohort identity required")
        require(_names(cohort["candidate_ids"]) and _names(cohort["control_ids"])
                and _names(cohort["sample_ids"]), "nonempty unique members and ordered samples required")
        require(len(cohort["candidate_ids"]) >= 2 and len(cohort["control_ids"]) == 2,
                "relative feedback needs multiple candidates and the shared measurement needs a control/A/A pair")
        require(all(s.startswith("slurp:train:") for s in cohort["sample_ids"]), "only current SLURP TRAIN scope supported")
        candidates = set(cohort["candidate_ids"])
        require(not candidates.intersection(cohort["control_ids"])
                and not candidates.intersection(seen_candidates), "candidate partitions must be disjoint from controls and each other")
        seen_cohorts.add(identity)
        seen_candidates.update(candidates)
    if version == ARCHITECTURE_VERSION:
        _validate_architecture(document)
    return deepcopy(document)


def _validate_architecture(document):
    """Bind whole execution configurations without inventing new text policies.

    This checks declared identities and ceilings, not that a runtime implements
    those declarations. The normal compiler, actual request/trace verification,
    capacity, structural and complete-family gates remain mandatory.
    """
    architecture = document["architecture"]
    _fields(architecture, ("profile", "semantic_proposals", "learner_export", "members"),
            "architecture fields differ")
    require(architecture["profile"] == "manually-specified-architecture-v1"
            and type(architecture["semantic_proposals"]) is int
            and architecture["semantic_proposals"] == 0
            and architecture["learner_export"] is False,
            "manual architecture comparisons cannot allocate proposals or export feedback")
    members = architecture["members"]
    require(isinstance(members, list), "architecture members must be an ordered list")
    expected = [(c["cohort_id"], member) for c in document["cohorts"]
                for member in c["control_ids"] + c["candidate_ids"]]
    observed = []
    for member in members:
        _fields(member, ("cohort_id", "member_id", "base_bundle_id", "execution_config",
                         "active_roles", "model_per_trajectory"), "architecture member fields differ")
        observed.append((member["cohort_id"], member["member_id"]))
        sha(member["base_bundle_id"])
        _pin(member["execution_config"])
        require(member["active_roles"] in (["perception", "solver"],
                                           ["perception", "solver", "reviewer", "planner"]),
                "unsupported ordered active role set")
        require(_positive(member["model_per_trajectory"])
                and member["model_per_trajectory"] <= document["contact_limits"]["model_per_trajectory"],
                "member contact ceiling must fit the declared family maximum")
    require(observed == expected, "architecture members differ from complete ordered cohorts")


def load_population_config(pin, *, repo_root, allow_architecture=False):
    """Read the exact registered file bytes; never infer or repair missing values."""
    return validate_population_config(json.loads(_read_pin(pin, repo_root)),
                                      allow_architecture=allow_architecture)


def population_accounting(document, cohort_id=None):
    """Derive K/N and all family budgets from declared members, inputs and caps."""
    config = validate_population_config(document, allow_architecture=True)
    cohorts = config["cohorts"]
    if cohort_id is not None:
        cohorts = [c for c in cohorts if c["cohort_id"] == cohort_id]
        require(len(cohorts) == 1, "unknown configured cohort")
    candidates = sum(len(c["candidate_ids"])*len(c["sample_ids"]) for c in cohorts)
    controls = sum(len(c["control_ids"])*len(c["sample_ids"]) for c in cohorts)
    architecture = config.get("architecture")
    if architecture is not None:
        sizes = {c["cohort_id"]: len(c["sample_ids"]) for c in cohorts}
        members = [m for m in architecture["members"] if m["cohort_id"] in sizes]
        generation = sum(sizes[m["cohort_id"]]*m["model_per_trajectory"] for m in members)
    else:
        generation = (candidates+controls)*config["contact_limits"]["model_per_trajectory"]
    result = {"candidate_trajectories": candidates, "control_trajectories": controls,
              "family_trajectories": candidates+controls, "generation_contacts_cap": generation,
              "fit_endpoints_cap": generation*config["contact_limits"]["fit_endpoints_per_model_contact"]}
    if cohort_id is not None:
        result.update(K=len(cohorts[0]["candidate_ids"]), N=len(cohorts[0]["sample_ids"]))
        if architecture is not None:
            result["active_node_counts"] = {m["member_id"]: len(m["active_roles"]) for m in members}
        else:
            result["M"] = len(config["nodes"])
    return result


def require_population_binding(document, pin, cohort_id, *artifacts):
    """Reject stage drift against one exact file pin and configured cohort.

    The caller loads and hashes the file with load_population_config first. This
    function compares the binding in proposal/compiler/runtime/scoring/feedback
    documents; it cannot substitute for their existing admission and READ gates.
    """
    config = validate_population_config(document, allow_architecture=True)
    cohorts = [c for c in config["cohorts"] if c["cohort_id"] == cohort_id]
    require(len(cohorts) == 1, "unknown configured cohort")
    require(artifacts and all(isinstance(a, dict) and a.get("experiment_population") == pin
                             and a.get("population_cohort") == cohort_id for a in artifacts),
            "experiment population binding differs between stages")
    return cohorts[0]


def population_stage_spec(pin, *, repo_root, cohort_id, allow_architecture=False):
    """Compile stage inputs from a file, without writing or authorizing a run."""
    config = load_population_config(pin, repo_root=repo_root, allow_architecture=allow_architecture)
    binding = {"experiment_population": deepcopy(pin), "population_cohort": cohort_id}
    cohort = require_population_binding(config, pin, cohort_id, binding)
    budget = population_accounting(config, cohort_id)
    model_cap = budget["N"] * config["contact_limits"]["model_per_trajectory"]
    maintenance = ({"boundary_maintenance": deepcopy(config["boundary_maintenance"])}
                   if "boundary_maintenance" in config else {})
    result = {**binding, **maintenance, "population_budget": budget,
            "candidate_members": cohort["candidate_ids"], "control_members": cohort["control_ids"],
            "sample_ids": cohort["sample_ids"], "K": budget["K"], "N": budget["N"],
            "M": config["nodes"], "sampling": config["sampling"],
            "execution": config["execution"], "proposer": config["proposer"],
            "member_generation_contacts_cap": model_cap,
            "member_fit_endpoints_cap": model_cap * config["contact_limits"]["fit_endpoints_per_model_contact"],
            "runtime_admission": False}
    if config.get("architecture") is not None:
        members = [m for m in config["architecture"]["members"] if m["cohort_id"] == cohort_id]
        # File bytes must still match before any downstream stage uses the identity.
        # This grants neither runtime admission nor execution-graph qualification.
        for member in members:
            _read_pin(member["execution_config"], repo_root)
        result.pop("M")
        result.pop("member_generation_contacts_cap")
        result.pop("member_fit_endpoints_cap")
        result.update(
            role_universe=config["nodes"], architecture_members=members,
            semantic_proposals=0, learner_export=False,
            execution_identity_sha256={m["member_id"]: content_hash(m) for m in members},
            member_generation_contacts_caps={m["member_id"]: budget["N"]*m["model_per_trajectory"] for m in members},
            member_fit_endpoints_caps={m["member_id"]: budget["N"]*m["model_per_trajectory"]
                                      *config["contact_limits"]["fit_endpoints_per_model_contact"] for m in members},
        )
    return result


def require_architecture_capacity_registration(values, cell, registered_plan, *, repo_root, data_root=None):
    """Validate an explicitly declared manual, nongenerative capacity registration.

    This opt-in is restricted to check/prepare-supply/prompt-fit cells. It neither
    admits a natural generation graph nor changes generic population loaders,
    text-learning accounting, execution-plan exposure or live runtime gates.
    Only pinned configuration/registration bytes are read; no task adapter is built.
    """
    from ..core.config import _canonical_hash, drop_null_arms
    from .controllers import default_phase_program
    from .native_episode_config import load_native_episode_config
    from ..analysis.native_graph_rehearsal import rehearsal_profile

    require(isinstance(registered_plan, dict)
            and registered_plan.get("schema") == "saea-registered-fit-plan-v1"
            and str(registered_plan.get("status", "")).upper().startswith("ROOT COUNTERSIGNED BEFORE CONTACT"),
            "manual capacity requires its countersigned FIT plan")
    require(cell.get("allowed_execution_stages") == ["check", "prepare-supply", "prompt-fit"],
            "manual capacity permits only check/prepare-supply/prompt-fit")
    require(not any(k in values for k in ("system_context_learning", "system_search_learning", "system_optimization"))
            and values.get("stage3_algorithm", {}).get("id") == "none"
            and values["stage3_algorithm"].get("operators_used") == []
            and values.get("stage3_measurement", {}).get("claims_benefit") is False,
            "manual capacity cannot admit learning or scientific feedback")
    budget = values["family_budget"]
    require(all(type(budget.get(k)) is int and budget[k] == 0 for k in
                ("complete_system_trajectories", "generation_calls_cap", "official_complete_scoring_jobs"))
            and _positive(budget.get("tokenizer_endpoint_cap")),
            "manual capacity requires zero generation/scoring and a positive tokenizer cap")
    pin = values["experiment_population"]
    population = load_population_config(pin, repo_root=repo_root, allow_architecture=True)
    require(population["schema"] == ARCHITECTURE_VERSION, "manual capacity requires the explicit V4 profile")
    matches = [m for m in population["architecture"]["members"]
               if m["member_id"] == values.get("architecture_member")
               and m["cohort_id"] == values.get("population_cohort")]
    require(len(matches) == 1, "manual capacity has no exact configured architecture member")
    member = matches[0]
    cohort = require_population_binding(population, pin, member["cohort_id"], values)
    require(registered_plan.get("experiment_population") == pin
            and values["populations"][0]["ids"] == cohort["sample_ids"]
            and values["population"]["count"] == len(cohort["sample_ids"]),
            "manual capacity population/roster binding differs")
    policy = drop_null_arms(json.loads(_read_pin(member["execution_config"], repo_root)))
    require(all(values.get(k) == v for k, v in policy.items() if k != "what_this_is"),
            "manual capacity effective policy differs from its pinned execution config")
    native = load_native_episode_config(values, default_phase_program(values["policy"]))
    require(native is not None and native.max_contacts == member["model_per_trajectory"]
            and [r for r in population["nodes"] if native.role(r).max_iterations > 0] == member["active_roles"],
            "manual capacity role/contact identity differs")
    profile = values["native_graph_capacity_profile"]
    require(profile == ("review-off-v1" if member["active_roles"] == ["perception", "solver"]
                        else "legacy-four-path-v1"), "manual capacity profile differs from active roles")
    rehearsal_profile(values, profile)
    require(all(values.get("decoding_params", {}).get(k) == v for k, v in population["sampling"].items()),
            "manual capacity sampling differs")
    binding = cell["system_text_policy_binding"]
    require(binding["bundle_id"] == member["base_bundle_id"]
            and registered_plan.get("policy_binding") == binding,
            "manual capacity base text bundle differs")
    plan = registered_plan["execution_plan"]
    require(registered_plan.get("composed_config_hash") == _canonical_hash(values)
            and registered_plan.get("cell") == cell["cell_id"]
            and plan.get("run_id") == cell["run_id"] and plan.get("attempt_id") == cell["attempt_id"],
            "manual capacity registered configuration/run/attempt differs")
    require(type(plan.get("planned_model_calls")) is int
            and plan["planned_model_calls"] == budget["tokenizer_endpoint_cap"]
            == values["execution_plan"]["planned_model_calls"]
            and type(registered_plan.get("official_score_jobs")) is int
            and registered_plan["official_score_jobs"] == 0
            and registered_plan.get("scientific_feedback") is False,
            "manual capacity registered cap or read scope differs")
    if values.get("joint_role_basis") is not None:
        from .architecture_natural_registration import require_joint_proof_registration
        require_joint_proof_registration(values,cell,[registered_plan],population,
                repo_root=repo_root,data_root=data_root,stage="capacity")
    else:
        require(registered_plan.get("joint_role_basis") is None, "unsolicited joint capacity basis refused")
    return dict(member_id=member["member_id"], execution_config=deepcopy(member["execution_config"]),
                execution_identity_sha256=content_hash(member), model_per_trajectory=native.max_contacts,
                rehearsal_profile=profile, contact_cap=plan["planned_model_calls"], runtime_admission=False)
