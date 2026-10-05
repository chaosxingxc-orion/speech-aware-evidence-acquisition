"""Pinned population configuration shared by experiment stages; grants no admission."""
from __future__ import annotations

import json
from copy import deepcopy
from .system_text_policy import _read_pin, require


def _fields(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), label)


def _positive(value):
    return type(value) is int and value > 0


def _names(value):
    return (isinstance(value, list) and bool(value)
            and all(isinstance(x, str) and x and x.isascii() for x in value)
            and len(set(value)) == len(value))


def validate_population_config(document):
    """Validate structure and implemented capabilities, not an experiment allowance.

    Candidate counts, cohort counts, sample counts and budgets have no defaults.
    Their single source is this document. The supported role set and deterministic
    sampling are executor/research constraints, not proposed population sizes.
    """
    require(isinstance(document, dict), "population config must be an object")
    version = document.get("schema")
    fields = ("schema", "experiment_id", "nodes", "sampling", "execution",
              "proposer", "contact_limits", "cohorts")
    if version == "saea-experiment-population-config-v2":
        fields += ("boundary_maintenance",)
    _fields(document, fields, "population config fields differ")
    require(version in ("saea-experiment-population-config-v1", "saea-experiment-population-config-v2")
            and isinstance(document["experiment_id"], str) and document["experiment_id"]
            and document["experiment_id"].isascii(), "population config identity differs")
    if version == "saea-experiment-population-config-v2":
        maintenance = document["boundary_maintenance"]
        required = {
            "mode": "root-coordinated-clean-page-cache",
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
    return deepcopy(document)


def load_population_config(pin, *, repo_root):
    """Read the exact registered file bytes; never infer or repair missing values."""
    return validate_population_config(json.loads(_read_pin(pin, repo_root)))


def population_accounting(document, cohort_id=None):
    """Derive K/N and all family budgets from declared members, inputs and caps."""
    config = validate_population_config(document)
    cohorts = config["cohorts"]
    if cohort_id is not None:
        cohorts = [c for c in cohorts if c["cohort_id"] == cohort_id]
        require(len(cohorts) == 1, "unknown configured cohort")
    candidates = sum(len(c["candidate_ids"])*len(c["sample_ids"]) for c in cohorts)
    controls = sum(len(c["control_ids"])*len(c["sample_ids"]) for c in cohorts)
    generation = (candidates+controls)*config["contact_limits"]["model_per_trajectory"]
    result = {"candidate_trajectories": candidates, "control_trajectories": controls,
              "family_trajectories": candidates+controls, "generation_contacts_cap": generation,
              "fit_endpoints_cap": generation*config["contact_limits"]["fit_endpoints_per_model_contact"]}
    if cohort_id is not None:
        result.update(K=len(cohorts[0]["candidate_ids"]), N=len(cohorts[0]["sample_ids"]), M=len(config["nodes"]))
    return result


def require_population_binding(document, pin, cohort_id, *artifacts):
    """Reject stage drift against one exact file pin and configured cohort.

    The caller loads and hashes the file with load_population_config first. This
    function compares the binding in proposal/compiler/runtime/scoring/feedback
    documents; it cannot substitute for their existing admission and READ gates.
    """
    config = validate_population_config(document)
    cohorts = [c for c in config["cohorts"] if c["cohort_id"] == cohort_id]
    require(len(cohorts) == 1, "unknown configured cohort")
    require(artifacts and all(isinstance(a, dict) and a.get("experiment_population") == pin
                             and a.get("population_cohort") == cohort_id for a in artifacts),
            "experiment population binding differs between stages")
    return cohorts[0]


def population_stage_spec(pin, *, repo_root, cohort_id):
    """Compile stage inputs from a file, without writing or authorizing a run."""
    config = load_population_config(pin, repo_root=repo_root)
    binding = {"experiment_population": deepcopy(pin), "population_cohort": cohort_id}
    cohort = require_population_binding(config, pin, cohort_id, binding)
    budget = population_accounting(config, cohort_id)
    model_cap = budget["N"] * config["contact_limits"]["model_per_trajectory"]
    maintenance = ({"boundary_maintenance": deepcopy(config["boundary_maintenance"])}
                   if "boundary_maintenance" in config else {})
    return {**binding, **maintenance, "population_budget": budget,
            "candidate_members": cohort["candidate_ids"], "control_members": cohort["control_ids"],
            "sample_ids": cohort["sample_ids"], "K": budget["K"], "N": budget["N"],
            "M": config["nodes"], "sampling": config["sampling"],
            "execution": config["execution"], "proposer": config["proposer"],
            "member_generation_contacts_cap": model_cap,
            "member_fit_endpoints_cap": model_cap * config["contact_limits"]["fit_endpoints_per_model_contact"],
            "runtime_admission": False}
