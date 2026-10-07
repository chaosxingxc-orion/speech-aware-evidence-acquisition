"""Offline deterministic context-diversity learner seams on the shared base.

Input construction performs no contact. The opt-in bounded iteration invokes
only explicitly supplied callbacks after immutable reservation; callbacks own
their separate contact/runtime authorization. There is no executor or auto-loop.
Public input construction freshly verifies registered READ and complete custody.
"""
from __future__ import annotations

import importlib.util
import json
import math
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from ..analysis.system_text_panel import _job_metadata
from ..analysis.system_text_pilot import _read_complete_evidence
from .hashing import content_hash
from .system_search_measurement import measured_rows, validate_profile
from .system_context_template_feedback import validate_template_profile, template_feedback, proposer_view
from .system_text_feedback import CompleteSystemFeedback, feedback_utility
from .system_text_policy import (
    CONTEXT_COMPONENTS, CONTEXT_LEARNING_ALGORITHMS, NODE_BUNDLE_SCHEMA,
    SystemTextPolicyBundle, TextPolicyUpdateProposal, _read_pin, _text, apply_text_proposal,
    canonical, require, sha,
)

REGISTRATION_SCHEMA = "saea-context-learning-registration-v1"
FEEDBACK_SCHEMA = "saea-context-learning-feedback-v1"
ROLES = ["perception", "solver", "reviewer", "planner"]


def _read_cli(root):
    """Reuse the exact shared ledger/countersignature and reference-family gates."""
    path = Path(root) / "scripts/system_text_search.py"
    spec = importlib.util.spec_from_file_location("_context_learning_read_cli", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load(pin, root):
    return json.loads(_read_pin(pin, root))


def population_candidates(protocol):
    """Return the exact prospective population or explicitly partitioned half.

    This structural gate does not grant read authority. The caller must verify
    owner and parent-registration pins before accessing any result evidence.
    """
    if "experiment_population" in protocol:
        candidates = protocol.get("candidate_members")
        require(isinstance(candidates, list) and candidates and len(candidates) == len(set(candidates)),
                "configured candidate identities required")
        return list(candidates)
    part = protocol.get("population_partition")
    if part is None:
        return [f"branch-{i:02d}" for i in range(1, 17)]
    require(isinstance(part, dict)
            and part.get("schema") == "saea-template-population-partition-v1"
            and part.get("panel") in ("a", "b")
            and protocol.get("population_authorization") is not None,
            "exact prospective K8 partition required")
    for key in ("authorization", "parent_registration"):
        value = part.get(key)
        require(isinstance(value, dict) and isinstance(value.get("relpath"), str)
                and bool(value["relpath"]), "partition owner and parent pins required")
        sha(value.get("sha256"))
    start = 1 if part["panel"] == "a" else 9
    return [f"branch-{i:02d}" for i in range(start, start + 8)]


def _validate_scope(recipe, registration, protocol, *, root):
    require(recipe.get("schema") == "saea-context-learning-analysis-v1"
            and registration.get("schema") == REGISTRATION_SCHEMA
            and protocol.get("schema") == "saea-context-learning-protocol-v1"
            and recipe.get("family_id") == registration.get("family_id") == protocol.get("family_id"),
            "registered context learning scope differs")
    require(registration.get("registration_sha256") == content_hash(
        {k: v for k, v in registration.items() if k != "registration_sha256"}),
        "context registration hash differs")
    if any("experiment_population" in d for d in (recipe, registration, protocol)):
        return _validate_configured_scope(recipe, registration, protocol, root=root)
    # A prospective population amendment does not resize historical K4 protocols.
    population = protocol.get("population_authorization")
    require(protocol.get("population_partition") is None or population is not None,
            "partition requires original population authorization")
    expected_k, algorithms = 4, list(CONTEXT_LEARNING_ALGORITHMS)
    if population is not None:
        amendment = _load(population, root)
        resolution = amendment.get("resolution", {})
        expected = {"K": 16, "M": 4, "N": 20, "temperature": 0, "seed": 20260913,
                    "candidate_trajectories": 320, "control_trajectories": 40,
                    "total_scientific_trajectories": 360, "semantic_agents": 1,
                    "semantic_batch_requests": 1, "fixed_knowledge": True, "case_free_learner": True}
        require(amendment.get("schema") == "saea-owner-template-population-k16-v1"
                and all(type(resolution.get(k)) is type(v) and resolution[k] == v
                        for k, v in expected.items()), "exact prospective K16 owner scope required")
        candidates = population_candidates(protocol)
        require(protocol.get("candidate_members") == candidates
                and protocol.get("control_members") == ["seed", "seed-aa"],
                "population requires all ordered registered branches and both controls")
        expected_k, algorithms = len(candidates), ["tf-grpo-context-diversity"]
        if expected_k == 8:
            part = protocol["population_partition"]
            split = _load(part["authorization"], root)
            expected_split = {"K": 8, "N": 20, "panels": 2,
                              "candidate_trajectories": 320, "control_trajectories": 80,
                              "total_scientific_trajectories": 400,
                              "preserve_all_original_templates": True,
                              "independent_panel_controls": True,
                              "no_between_panel_policy_update": True}
            resolution = split.get("resolution", {})
            require(split.get("schema") == "saea-owner-template-k8-partition-v1"
                    and all(type(resolution.get(k)) is type(v) and resolution[k] == v
                            for k, v in expected_split.items()),
                    "exact prospective two-panel K8 owner scope required")
            parent = _load(part["parent_registration"], root)
            require(parent.get("schema") == REGISTRATION_SCHEMA
                    and parent.get("registration_sha256") == content_hash(
                        {k: v for k, v in parent.items() if k != "registration_sha256"})
                    and set(parent.get("member_bindings", {})) ==
                        {"seed", "seed-aa", *[f"branch-{i:02d}" for i in range(1, 17)]},
                    "complete original K16 registration required")
            require(all(registration["member_bindings"][c]["bundle_id"] ==
                        parent["member_bindings"][c]["bundle_id"]
                        for c in candidates + ["seed", "seed-aa"]),
                    "partition must preserve original templates and controls")
    owner = _load(protocol["owner"], root)
    contract = owner.get("resolved_contract", {})
    require(owner.get("schema") == "saea-owner-deterministic-context-rollouts-v1"
            and contract.get("initial_N") == protocol.get("N") == 20
            and contract.get("initial_K") == 4
            and type(protocol.get("K")) is int and protocol["K"] == expected_k
            and contract.get("M") == protocol.get("M") == ROLES
            and contract.get("temperature") == protocol.get("sampling", {}).get("temperature") == 0
            and type(protocol["sampling"]["temperature"]) in (int, float)
            and contract.get("seed") == protocol.get("sampling", {}).get("seed") == 20260913
            and type(protocol["sampling"]["seed"]) is int,
            "exact deterministic N20/registered-K/four-role owner scope required")
    require(protocol.get("algorithms") == algorithms
            and protocol.get("automatic_expansion") is False
            and protocol.get("independent_validation") is False
            and type(protocol.get("iteration")) is int and protocol["iteration"] > 0,
            "separate baseline algorithms and bounded iteration scope required")
    pool = _load(protocol["fixed_roster"], root).get("sample_ids", [])
    ids = recipe.get("sample_ids", [])
    require(len(pool) == len(set(pool)) == 400
            and all(isinstance(s, str) and s.startswith("slurp:train:") for s in pool)
            and ids == pool[:20] and recipe.get("required_rows_per_member") == 20,
            "exact ordered same400 TRAIN prefix required")
    candidates, controls = protocol["candidate_members"], protocol["control_members"]
    require(isinstance(candidates, list) and len(candidates) == len(set(candidates)) == expected_k
            and controls in ([], ["seed", "seed-aa"]) and not set(candidates).intersection(controls),
            "exact candidate K and separately declared controls required")
    bindings = registration["member_bindings"]
    members = registration["expected_members"]
    require(set(bindings) == set(members) == set(candidates + controls)
            and recipe.get("expected_members") == members
            and len(set(members.values())) == len(members), "all declared family members required")
    for cid, binding in bindings.items():
        require(binding.get("run_id") == members[cid] and binding.get("attempt_id"),
                "registered member identity differs")
        sha(binding["config_hash"])
        sha(binding["bundle_id"])
    require(len({bindings[c]["bundle_id"] for c in candidates}) == expected_k,
            "K requires distinct complete-system bundles")
    if controls:
        require(bindings["seed"]["bundle_id"] == bindings["seed-aa"]["bundle_id"], "control seed/A/A differs")
    require(recipe["run_ids"]["read"] == registration["read_id"], "context READ identity differs")
    profile = protocol.get("measurement_profile")
    validate_profile(profile)
    require(recipe.get("measurement_profile") == registration.get("measurement_profile") == profile
            and profile["slot_count"] == profile["queue_depth"] == 4, "registered measurement profile differs")
    return candidates, controls


def _validate_configured_scope(recipe, registration, protocol, *, root):
    """Use one pinned config for every prospective stage; retain old scope readers."""
    from .experiment_population import load_population_config, require_population_binding, population_accounting
    pin = protocol.get("experiment_population")
    config = load_population_config(pin, repo_root=root)
    cohort_id = protocol.get("population_cohort")
    cohort = require_population_binding(config, pin, cohort_id, recipe, registration, protocol)
    budget = population_accounting(config, cohort_id)
    require(all(d.get("population_budget") == budget for d in (recipe, registration, protocol)),
            "configured population budget differs between stages")
    candidates, controls, ids = (cohort[k] for k in ("candidate_ids", "control_ids", "sample_ids"))
    require(protocol.get("candidate_members") == candidates and protocol.get("control_members") == controls
            and protocol.get("K") == budget["K"] and type(protocol["K"]) is int
            and protocol.get("N") == budget["N"] and type(protocol["N"]) is int
            and protocol.get("M") == config["nodes"] and protocol.get("sampling") == config["sampling"],
            "protocol differs from configured population, nodes or sampling")
    # Configuration is not owner authority or permission to expand the dataset.
    owner = _load(protocol["owner"], root)
    require(owner.get("schema") == "saea-owner-deterministic-context-rollouts-v1",
            "registered context owner source required")
    algorithms = set(CONTEXT_LEARNING_ALGORITHMS)
    if any("search_evaluation" in d for d in (recipe, registration, protocol)):
        from .system_search_learning import require_search_evaluation_binding
        algorithms = {require_search_evaluation_binding(recipe, registration, protocol, root=root, config=config)}
    require(protocol.get("automatic_expansion") is False and protocol.get("independent_validation") is False
            and type(protocol.get("iteration")) is int and protocol["iteration"] > 0
            and isinstance(protocol.get("algorithms"), list) and protocol["algorithms"]
            and set(protocol["algorithms"]) <= algorithms,
            "bounded registered algorithms required")
    pool = _load(protocol["fixed_roster"], root).get("sample_ids", [])
    require(len(pool) == len(set(pool)) and all(s in pool for s in ids)
            and recipe.get("sample_ids") == ids and recipe.get("required_rows_per_member") == len(ids),
            "exact configured inputs from the registered pool required")
    bindings = registration["member_bindings"]
    members = registration["expected_members"]
    require(set(bindings) == set(members) == set(candidates + controls)
            and recipe.get("expected_members") == members
            and len(set(members.values())) == len(members), "complete configured family required")
    for cid, binding in bindings.items():
        require(binding.get("run_id") == members[cid] and binding.get("attempt_id"), "member identity differs")
        sha(binding["config_hash"])
        sha(binding["bundle_id"])
    require(len({bindings[c]["bundle_id"] for c in candidates}) == len(candidates), "distinct candidate policies required")
    require(len({bindings[c]["bundle_id"] for c in controls}) == 1, "same-policy controls required")
    require(recipe["run_ids"]["read"] == registration["read_id"], "configured READ differs")
    profile = protocol.get("measurement_profile")
    validate_profile(profile)
    require(recipe.get("measurement_profile") == registration.get("measurement_profile") == profile
            and all(profile.get(k) == config["execution"][k] for k in ("slot_count", "queue_depth", "schedule")),
            "configured execution profile differs")
    return candidates, controls


def _qualified_feedback(bindings, *, recipe_pin, repo_root):
    """No task result is reached before READ, scope and complete-family custody."""
    root = Path(repo_root).resolve()
    recipe = _load(recipe_pin, root)
    registration = _load(recipe["context_learning_registration"], root)
    protocol = _load(registration["protocol"], root)
    candidates, controls = _validate_scope(recipe, registration, protocol, root=root)
    supplied = [b.get("candidate_id") for b in bindings]
    require(len(supplied) == len(set(supplied)) and set(supplied) == set(registration["expected_members"]),
            "all declared family members required before any result read")
    cli = _read_cli(root)
    spec = {"family_id": recipe["family_id"], "expected_members": recipe["expected_members"],
            "read_registration": recipe_pin}
    authority = cli.require_read_registration(spec, repo_root=root)
    reference_spec = _load(protocol["frozen_reference"], root)
    require(reference_spec.get("family_id") == "initial"
            and set(reference_spec.get("expected_members", {})) == {"seed", "seed-aa"}
            and reference_spec.get("initial_reference_member") in {"seed", "seed-aa"}
            and reference_spec.get("reference_family") is None,
            "only the registered original TRAIN reference source is permitted")
    cli.require_read_registration(reference_spec, repo_root=root)
    jobs = _job_metadata(bindings)
    evidence = _read_complete_evidence(bindings, recipe=recipe,
        registration=registration,
        authority=authority, family=recipe["family_id"], schema=FEEDBACK_SCHEMA,
        evidence_type=CompleteSystemFeedback).as_json()
    # The complete current family has passed all seal/count/timing checks.
    reference = cli.read_family(root / protocol["frozen_reference"]["relpath"], repo_root=root).as_json()["reference"]
    require(reference.get("family_id") == "initial" and reference.get("candidate_id") in {"seed", "seed-aa"}
            and len(reference.get("sample_ids", [])) >= 400
            and len(set(reference["sample_ids"])) == len(reference["sample_ids"])
            and all(s.startswith("slurp:train:") for s in reference["sample_ids"]),
            "preserve the original complete TRAIN reference")
    sha(reference["source_sha256"])
    feedback_utility(dict.fromkeys((f"slu_f1_{a}_{k}" for a in ("word", "char") for k in ("tp", "fp", "fn")), 0), reference["f1"])
    require(_job_metadata(bindings) == jobs
            and cli.require_read_registration(spec, repo_root=root) == authority,
            "READ or official job metadata changed during export")
    # Reverify all prospective scope bytes after the shared reader finishes.
    require(_load(recipe_pin, root) == recipe
            and _load(recipe["context_learning_registration"], root) == registration
            and _load(registration["protocol"], root) == protocol
            and _load(protocol["frozen_reference"], root) == reference_spec,
            "context scope changed during export")
    _validate_scope(recipe, registration, protocol, root=root)
    require(evidence.get("schema") == FEEDBACK_SCHEMA and evidence.get("family_id") == recipe["family_id"]
            and evidence.get("read_authority") == authority
            and evidence.get("registration_sha256") == registration["registration_sha256"],
            "shared feedback qualification identity differs")
    return evidence, recipe, registration, protocol, candidates, controls, reference


def _candidate_groups(evidence, recipe, registration, candidates, reference):
    members = registration["member_bindings"]
    feedback = evidence["feedback"]
    sources = feedback["sources"]
    require(set(evidence["summaries"]) == set(members) and len(sources) == len(members)
            and {s["candidate_id"] for s in sources} == set(members), "complete source family differs")
    for source in sources:
        require(all(source[k] == members[source["candidate_id"]][k] for k in ("run_id", "attempt_id", "config_hash")),
                "complete source identity differs")
    require([g["sample_id"] for g in feedback["groups"]] == recipe["sample_ids"], "exact ordered cohort differs")
    groups = []
    for group in feedback["groups"]:
        rows = group["members"]
        require(len(rows) == len(members) and {r["candidate_id"] for r in rows} == set(members),
                "each input requires every declared family member")
        indexed = {r["candidate_id"]: r for r in rows}
        selected = []
        for cid in candidates:
            row = indexed[cid]
            execution = row["execution"]
            require(execution.get("sample_timing") is not None and execution.get("wall_time_seconds") is not None,
                    "retain all measured sample costs and terminal dispositions")
            selected.append({"candidate_id": cid, "rollout_id": content_hash({"sample_id": group["sample_id"],
                "candidate_id": cid, **members[cid]}), "native_counts": row["native_counts"],
                "utility": feedback_utility(row["native_counts"], reference["f1"]), "execution": execution})
        groups.append({"sample_id": group["sample_id"], "members": selected})
    return groups


def prepare_context_optimizer_input(archive, *, bindings, recipe_pin, repo_root,
                                    algorithm, iteration, policies, experiences=None,
                                    candidate_id=None, component=None, feedback_profile=None):
    """Freshly qualify a whole family and save an immutable offline reflection task.

    GEPA's caller chooses a parent among the per-example front and one legal
    component. TF-GRPO receives individual-summary and semantic-comparison tasks.
    A prospectively pinned template profile replaces per-row reflection tasks
    with complete numeric aggregates and bounded example pointers. No callback
    is invoked; packet production itself adds zero contacts.
    """
    require(algorithm in CONTEXT_LEARNING_ALGORITHMS and type(iteration) is int and iteration > 0,
            "unknown context baseline/iteration")
    evidence, recipe, registration, protocol, candidates, controls, reference = _qualified_feedback(
        bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    require(algorithm in protocol["algorithms"], "optimizer algorithm is not registered for this family")
    require(iteration == protocol["iteration"] and set(policies) == set(candidates), "registered iteration/policies differ")
    for cid, policy in policies.items():
        SystemTextPolicyBundle.from_json(policy.as_json(), parents=[archive.load_policy(p)
            for p in policy.as_json()["parent_ids"]])
        require(policy.as_json()["schema"] == NODE_BUNDLE_SCHEMA
                and policy.bundle_id == registration["member_bindings"][cid]["bundle_id"],
                "complete four-role policy binding differs")
    if feedback_profile is not None:
        validate_template_profile(feedback_profile)
        _, registered_plan = _iteration_plan(protocol, recipe, Path(repo_root), algorithm, iteration, controls)
        require(registered_plan.get("feedback_profile") == feedback_profile,
                "template profile must be prospectively registered")
    fixed = ("seed_config_sha256", "construction_instruction", "supply", "knowledge", "construction_receipt")
    require(len({content_hash({k: p.as_json()[k] for k in fixed}) for p in policies.values()}) == 1,
            "all context candidates must preserve the same fixed knowledge/supply/base")
    business = measured_rows(evidence, candidates, registration["member_bindings"],
                             profile=protocol["measurement_profile"])
    groups = _candidate_groups(evidence, recipe, registration, candidates, reference)
    packet = {"schema": "saea-context-optimizer-input-v1", "algorithm": algorithm, "iteration": iteration,
        "family_id": recipe["family_id"], "read_authority": evidence.get("read_authority"),
        "recipe": recipe_pin, "protocol": registration["protocol"], "reference": reference,
        "frozen_reference": protocol["frozen_reference"], "sampling": protocol["sampling"],
        "groups": groups, "measurement_profile": protocol["measurement_profile"],
        "business_measurements": business,
        "official_summaries": {c: evidence["summaries"][c] for c in candidates},
        "family_commitment": {"sha256": content_hash(evidence), "registration_sha256": registration["registration_sha256"],
            "member_ids": list(registration["member_bindings"]), "control_members": controls},
        "policies": {c: {"bundle_id": policies[c].bundle_id, "policy": policies[c].as_json()} for c in candidates},
        "budget": {"N": len(groups), "K": len(candidates), "M": 4, "candidate_trajectories": len(groups) * len(candidates),
            "control_trajectories": len(groups) * len(controls), "family_trajectories": len(groups) * (len(candidates) + len(controls)),
            "minimum_initial_node_visits_if_complete": 4 * len(groups) * len(candidates)},
        "runtime_admission": False, "contacts_added": {"model": 0, "scorer": 0}}
    if "experiment_population" in protocol:
        from .experiment_population import load_population_config, population_accounting
        config_pin = protocol["experiment_population"]
        config = load_population_config(config_pin, repo_root=repo_root)
        packet.update(experiment_population=config_pin, population_cohort=protocol["population_cohort"])
        packet["budget"] = population_accounting(config, protocol["population_cohort"])
    if algorithm == "tf-grpo-context-diversity":
        require(candidate_id is None and component is None, "TF task uses the complete context-diversity group")
        packet["experience"] = apply_experience_operations({} if experiences is None else experiences, [])
        for group in groups:
            values = [m["utility"] for m in group["members"]]
            group["semantic_advantage"] = "skip-zero-variation" if max(values) == min(values) else "individual-summary-then-semantic-comparison"
            group["summary_tasks"] = [] if max(values) == min(values) else [m["rollout_id"] for m in group["members"]]
        packet["reflection_task"] = {"experience_operations": ["add", "delete", "modify", "keep"],
            "instructions": "Summarize each retained rollout; compare supported winners and losers within each nonconstant input group. Produce semantic advantage, then propose bounded experience operations and explicit full-role/assembly edits. Do not turn numeric utility normalization into a learner. No ground-truth answers enter runtime.",
            "fidelity": "Deterministic distinct-context adaptation; not original same-policy stochastic TF-GRPO.",
            "experience_runtime_renderer": "not-implemented; materialize explicit role-text edits instead"}
    else:
        require(experiences is None, "GEPA reflection is separate from TF experience updates")
        front = {g["sample_id"]: [m["candidate_id"] for m in g["members"]
                 if m["utility"] == max(r["utility"] for r in g["members"])] for g in groups}
        require(candidate_id in {c for cs in front.values() for c in cs} and component in CONTEXT_COMPONENTS,
                "GEPA parent must be on the per-example front with a legal component")
        packet["per_example_front"] = front
        packet["reflection_task"] = {"candidate_id": candidate_id, "component": component,
            "parent_bundle_id": policies[candidate_id].bundle_id,
            "instructions": "Reflect on this component using all retained per-input feedback and source-addressed trajectories. Propose one component mutation. Preserve tied per-example best programs; keep selection separate from pooled official quality/cost assessment.",
            "fidelity": "Offline GEPA component-reflection and per-example selection seam; no search engine or reflection call executed."}
    if feedback_profile is not None:
        packet["feedback_profile"] = feedback_profile
        for group in groups:
            group.pop("summary_tasks", None)
            if group.get("semantic_advantage") != "skip-zero-variation" and algorithm == "tf-grpo-context-diversity":
                group["semantic_advantage"] = "template-batch-reflection"
        packet["template_feedback"] = template_feedback(packet, feedback_profile)
        packet["reflection_task"]["instructions"] = (
            "Optimize complete node template text and supported context assembly, not individual sample answers. "
            "Use all-template measured outcomes and bounded stratified cases. Keep knowledge, retrieval, "
            "construction, runtime interfaces and decoding fixed. Do not request a semantic summary for every row. "
            "Retain failed, negative and no-change evidence; changes remain hypotheses until full-system evaluation.")
        if feedback_profile["examples_per_template"] == 0:
            packet["reflection_task"]["instructions"] = (
                "Optimize complete node templates and supported context assembly using aggregate system feedback. "
                "Treat adequate existing knowledge supply as the working hypothesis; keep knowledge, retrieval, "
                "construction, runtime interfaces and decoding fixed. Prioritize Solver/Reviewer evidence use "
                "and justified revision, then context organization and handoffs, then Planner revision/stop/delivery "
                "decisions, then Perception presentation. Follow the registered component selector when applicable. "
                "Do not request individual cases or source rosters. Retain failed, negative and no-change evidence. "
                "Evaluate complete-system quality, intent, reliability and mean/non-first sample latency; "
                "do not infer causal node credit or promise positive gains from these aggregates.")
        packet["reflection_task"]["fidelity"] = "Prospective template-batch reflection study adaptation; not unchanged upstream reproduction."
    if feedback_profile is not None and "rejected_trial_feedback" in registered_plan:
        packet["rejected_trial_feedback"] = _rejected_template_history(archive,
            registered_plan["rejected_trial_feedback"], root=Path(repo_root), algorithm=algorithm,
            iteration=iteration, initial=(evidence, recipe, registration, protocol, candidates, controls, reference),
            policies=policies, profile=feedback_profile)
    packet["input_sha256"] = content_hash(packet)
    if "experiment_population" in packet:
        # Retain identical file bytes and the same relative pin in the private
        # archive. Do not reserialize a config and silently change its identity.
        config_pin = packet["experiment_population"]
        raw = _read_pin(config_pin, repo_root)
        destination = archive.root / config_pin["relpath"]
        require(destination.resolve().is_relative_to(archive.root.resolve()),
                "archived config escapes archive root")
        if destination.exists():
            require(destination.read_bytes() == raw, "archived experiment config differs")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(raw)
    for policy in policies.values():
        archive.store_policy(policy)
    archive._write(f"context-learning/inputs/{algorithm}-{iteration}.json", packet)
    return packet


def record_context_update(archive, *, input_sha256, update_id, proposal_document, experience_operations=None,
                          expected_candidate_id=None):
    """Retain one attempted update, including invalid/no-change, with no admission."""
    sha(input_sha256)
    require(isinstance(update_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", update_id), "invalid update identity")
    packets = [json.loads(p.read_text()) for p in (archive.root / "context-learning/inputs").glob("*.json")]
    matching = [p for p in packets if p.get("input_sha256") == input_sha256]
    require(len(matching) == 1, "exact immutable optimizer input required")
    packet = matching[0]
    require(content_hash({k: v for k, v in packet.items() if k != "input_sha256"}) == input_sha256,
            "optimizer input hash differs")
    partitioned = packet.get("schema") in ("saea-partitioned-context-optimizer-input-v1", "saea-partitioned-context-optimizer-input-v2")
    if partitioned:
        from .system_context_partitioned_learning import validate_partitioned_packet
        validate_partitioned_packet(archive, packet)
    path = f"context-learning/updates/{packet['algorithm']}-{packet['iteration']}-{update_id}.json"
    require(not (archive.root / path).exists(), "update record already exists")
    record = {"schema": "saea-context-learning-update-record-v1", "input_sha256": input_sha256,
        "algorithm": packet["algorithm"], "iteration": packet["iteration"], "update_id": update_id,
        "raw_proposal": proposal_document, "experience_operations": experience_operations,
        "status": "invalid", "error": None, "runtime_admission": False}
    if partitioned:
        record["source_population"] = packet["source_population"]
    if "experiment_population" in packet:
        from .experiment_population import load_population_config, require_population_binding
        population = load_population_config(packet["experiment_population"], repo_root=archive.root)
        require_population_binding(population, packet["experiment_population"], packet.get("population_cohort"), packet)
        record.update({k: packet[k] for k in ("experiment_population", "population_cohort")})
    try:
        proposal = TextPolicyUpdateProposal.from_context_json(proposal_document)
        p = proposal.as_json()
        require(p["algorithm"] == packet["algorithm"] and p["iteration"] == packet["iteration"]
                and p["candidate_id"] in packet["policies"] and p["evidence"] == [input_sha256],
                "update differs from optimizer input/evidence commitment")
        require(expected_candidate_id is None or p["candidate_id"] == expected_candidate_id,
                "update differs from reserved system task")
        parent_id = packet["policies"][p["candidate_id"]]["bundle_id"]
        require(p["parent_ids"] == [parent_id], "update parent differs from evaluated complete system")
        if packet["algorithm"] == "tf-grpo-context-diversity":
            require(p["component"] == "joint-system", "TF update must bind the joint-system task")
            operations = [] if experience_operations is None else experience_operations
            if partitioned:
                cohorts = packet["learner_view"]["population"]["cohorts"].values()
                own = [c for c in cohorts if p["candidate_id"] in {t["candidate_id"] for t in c["templates"]}]
                require(len(own) == 1, "one original source cohort per update required")
                variation = any(len({m["terminal"]["utility"] for m in g["members"]}) > 1
                                for g in own[0]["groups"])
            else:
                variation = any(g["semantic_advantage"] != "skip-zero-variation" for g in packet["groups"])
            require(variation or (not p["changes"] and not operations), "zero variation gives no semantic advantage")
            record.update(experience_before=packet["experience"],
                          experience_after=apply_experience_operations(packet["experience"], operations))
        if packet["algorithm"] == "gepa":
            require(experience_operations is None, "GEPA cannot consume TF experience operations")
            task = packet["reflection_task"]
            require(p["candidate_id"] == task["candidate_id"] and p["component"] == task["component"], "GEPA task binding differs")
            field, _, role = p["component"].partition(".")
            require(set(p["changes"]) <= {field} and (not role or set(p["changes"].get(field, {})) <= {role}),
                    "GEPA update changes another component")
        parent = archive.load_policy(parent_id)
        # Every policy visible to the learner contributes cumulative exposure,
        # even when the original proposal names only one parent.
        observed_sources = []
        for entry in packet["policies"].values():
            observed = archive.load_policy(entry["bundle_id"])
            require(observed.as_json() == entry["policy"], "observed policy bytes differ")
            observed_sources.extend(observed.as_json()["cumulative_sources"])
        feedback_ids = (packet["feedback_sample_ids"] if partitioned else
                        sorted(set(packet["reference"]["sample_ids"]) |
                               {g["sample_id"] for g in packet["groups"]}))
        exposed_ids = sorted(set(feedback_ids) |
                             {sid for source in observed_sources for sid in source["sample_ids"]})
        sources = observed_sources + [{"kind": "feedback", "sha256": input_sha256,
                    "sample_ids": feedback_ids},
                   {"kind": "proposal", "sha256": content_hash(p),
                    "sample_ids": exposed_ids}]
        child = apply_text_proposal(proposal, parents=[parent], added_sources=sources)
        # Semantic no-change compares runtime fields, not newly retained ancestry.
        editable = ("role_text", "context_layout", "node_context")
        unchanged = all(parent.as_json()[k] == child.as_json()[k] for k in editable)
        archive.store_policy(child)
        record.update(status="no-change" if unchanged else "provisional", bundle_id=child.bundle_id,
                      proposal=p, change_sha256=content_hash({"parent_ids": p["parent_ids"], "changes": p["changes"]}))
    except (ValueError, TypeError, KeyError) as error:
        record["error"] = str(error)
    archive._write(path, record)
    return record


def apply_experience_operations(experiences, operations):
    """Apply supplied semantic operations only; never infer them from rewards."""
    require(isinstance(experiences, dict) and isinstance(operations, list), "experience state/operations differ")
    result = dict(experiences)
    for identity, text in result.items():
        _text(identity)
        _text(text)
    for operation in operations:
        require(isinstance(operation, dict) and operation.get("operation") in {"add", "delete", "modify", "keep"},
                "unknown semantic experience operation")
        kind, identity = operation["operation"], operation["id"]
        _text(identity)
        require(set(operation) == ({"operation", "id", "text"} if kind in {"add", "modify"} else {"operation", "id"}),
                "semantic operation fields differ")
        require((identity not in result) if kind == "add" else (identity in result), "experience identity differs")
        if kind in {"add", "modify"}:
            _text(operation["text"])
            result[identity] = operation["text"]
        elif kind == "delete":
            del result[identity]
    return result


def select_gepa_task(programs, *, sample_ids, selection_seed=0, state=None):
    """Pure pinned GEPA instance-front draw and per-program round-robin schedule.

    Match gepa_utils.py at fb1ed589: ascending aggregate tie-cover removal,
    frequency-weighted RNG choice, then component_selector.py cursor advance.
    Metrics supplied here are not scientific-read authority; the runner derives
    them only from qualified family inputs and immutable prior decisions.
    """
    require(programs and sample_ids and len(set(sample_ids)) == len(sample_ids)
            and type(selection_seed) is int, "GEPA program/roster/seed differs")
    require(len({p["bundle_id"] for p in programs}) == len(programs), "duplicate GEPA program")
    for p in programs:
        sha(p["bundle_id"])
        require(set(p["scores"]) == set(sample_ids)
                and all(type(v) in (int, float) and math.isfinite(v) for v in p["scores"].values()),
                "GEPA needs complete finite per-example scores")
    front = {sid: {i for i, p in enumerate(programs)
                  if p["scores"][sid] == max(q["scores"][sid] for q in programs)} for sid in sample_ids}
    frequency = {}
    for winners in front.values():
        for i in winners:
            frequency[i] = frequency.get(i, 0) + 1
    aggregate = [sum(p["scores"][s] for s in sample_ids) / len(sample_ids) for p in programs]
    ordered = sorted(frequency, key=lambda i: aggregate[i])
    dominated = set()
    changed = True
    while changed:
        changed = False
        for i in ordered:
            if i in dominated:
                continue
            others = set(ordered) - {i} - dominated
            if all(winners & others for winners in front.values() if i in winners):
                dominated.add(i)
                changed = True
                break
    surviving = {sid: {i for i in winners if i not in dominated} for sid, winners in front.items()}
    frequency = {}
    for winners in surviving.values():
        for i in winners:
            frequency[i] = frequency.get(i, 0) + 1
    sampling = [i for i, count in frequency.items() for _ in range(count)]
    require(sampling, "GEPA front has no surviving program")
    previous = {} if state is None else json.loads(canonical(state))
    require(previous.get("selection_seed", selection_seed) == selection_seed, "selector seed changed")
    rng = random.Random(selection_seed)
    if previous.get("rng_state") is not None:
        def tuples(value):
            return tuple(tuples(v) for v in value) if isinstance(value, list) else value
        rng.setstate(tuples(previous["rng_state"]))
    selected = rng.choice(sampling)
    bundle = programs[selected]["bundle_id"]
    cursors = dict(previous.get("component_cursors", {}))
    cursor = cursors.get(bundle, 0)
    require(type(cursor) is int and 0 <= cursor < len(CONTEXT_COMPONENTS), "invalid GEPA component cursor")
    cursors[bundle] = (cursor + 1) % len(CONTEXT_COMPONENTS)
    return {"parent_bundle_id": bundle, "component": CONTEXT_COMPONENTS[cursor],
            "per_example_front": {sid: [programs[i]["bundle_id"] for i in sorted(winners)] for sid, winners in front.items()},
            "state_after": {"selection_seed": selection_seed, "rng_state": json.loads(canonical(rng.getstate())),
                            "component_cursors": cursors}}


@dataclass(frozen=True)
class ContextLearningCallbacks:
    """Injected seams; each real callback must enforce its own admitted contacts.

    Return {value, provenance, usage}. Callback invocation count is not provider
    contact count. No missing usage is replaced by zero and no retry is made.
    """
    summarize: object = None
    compare: object = None
    update_experience: object = None
    propose: object = None
    evaluate: object = None


def _iteration_plan(protocol, recipe, root, algorithm, iteration, controls):
    plans = protocol.get("iteration_plans")
    require(plans is None or (isinstance(plans, dict) and set(plans) == set(CONTEXT_LEARNING_ALGORITHMS)
                             and "iteration_plan" not in protocol), "ambiguous common iteration plans")
    pin = protocol.get("iteration_plan") if plans is None else plans[algorithm]
    require(isinstance(pin, dict), "exact prospective iteration plan required")
    plan = _load(pin, root)
    require(plan.get("schema") == "saea-context-learning-iteration-plan-v1"
            and plan.get("algorithm") == algorithm and plan.get("iteration") == iteration
            and plan.get("input_family_id") == recipe["family_id"]
            and plan.get("sample_ids_sha256") == content_hash(recipe["sample_ids"])
            and type(plan.get("selection_seed")) is int
            and plan.get("acceptance") == "strict-registered-utility-sum"
            and plan.get("automatic_next_iteration") is False,
            "registered iteration identity/acceptance differs")
    caps = plan.get("callback_caps", {})
    require(set(caps) == {"summarize", "compare", "update_experience", "propose", "evaluate"}
            and all(type(v) is int and v >= 0 for v in caps.values())
            and caps["propose"] == (4 if algorithm == "tf-grpo-context-diversity" else 1)
            and caps["evaluate"] == 1
            and plan.get("evaluation_candidate_trajectories_cap") == 80
            and plan.get("evaluation_control_trajectories_cap") == 20 * len(controls),
            "exact bounded callback and full-family evaluation caps required")
    if "feedback_profile" in plan:
        validate_template_profile(plan["feedback_profile"])
        require(caps["summarize"] == caps["compare"] == 0
                and caps["update_experience"] == (1 if algorithm == "tf-grpo-context-diversity" else 0),
                "template feedback forbids per-sample semantic callbacks")
    if "experience_transition" in plan:
        transition = plan["experience_transition"]
        require(algorithm == "tf-grpo-context-diversity" and iteration > 1
                and plan.get("feedback_profile", {}).get("examples_per_template") == 0
                and isinstance(transition, dict)
                and set(transition) == {"mode", "previous_decision_sha256"}
                and transition["mode"] == "empty-template-phase-v1",
                "explicit template-only phase transition required")
        sha(transition["previous_decision_sha256"])
    if "rejected_trial_feedback" in plan:
        history = plan["rejected_trial_feedback"]
        require(algorithm == "tf-grpo-context-diversity" and iteration > 1
                and plan.get("feedback_profile", {}).get("examples_per_template") == 0
                and isinstance(history, dict)
                and set(history) == {"mode", "previous_decision_sha256", "source"}
                and history["mode"] == "previous-rejected-trial-aggregate-v1"
                and isinstance(history["source"], dict)
                and set(history["source"]) == {"bindings", "recipe_pin"},
                "exact own rejected-trial aggregate scope required")
        sha(history["previous_decision_sha256"])
    return pin, plan


def _rejected_template_history(archive, spec, *, root, algorithm, iteration, initial, policies, profile):
    """Requalify the immediately preceding rejected trial under a new exact READ.

    This is conditioning evidence only. Never change accepted parents or import
    the previous semantic experience/case payload. Original records stay intact.
    """
    previous_sha = spec["previous_decision_sha256"]
    decisions = [json.loads(p.read_text()) for p in
                 (archive.root / "context-learning/iterations").glob("*/decision.json")]
    matches = [d for d in decisions if d.get("decision_sha256") == previous_sha]
    require(len(matches) == 1, "exact rejected prior decision required")
    d = matches[0]
    _, base_recipe, _, base_protocol, candidates, controls, reference = initial
    require(content_hash({k: v for k, v in d.items() if k != "decision_sha256"}) == previous_sha
            and d["algorithm"] == algorithm and d["iteration"] == iteration - 1
            and d["status"] == "rejected" and d["sample_ids"] == base_recipe["sample_ids"]
            and d["reference_sha256"] == content_hash(reference), "rejected history decision scope differs")
    source = spec["source"]
    fresh = _qualified_feedback(source["bindings"], recipe_pin=source["recipe_pin"], repo_root=root)
    e, recipe, registration, protocol, cs, ctl, frozen = fresh
    require(protocol.get("rejected_trial_use") == {
                "algorithm": algorithm, "iteration": iteration, "previous_decision_sha256": previous_sha}
            and protocol["iteration"] == iteration
            and cs == candidates and ctl == controls and recipe["sample_ids"] == base_recipe["sample_ids"]
            and frozen == reference and protocol["sampling"] == base_protocol["sampling"]
            and protocol["measurement_profile"] == base_protocol["measurement_profile"],
            "prospective rejected-trial READ scope differs")
    evaluations = [event for event in d["events"] if event["stage"] == "evaluate" and event["status"] == "completed"]
    require(len(evaluations) == 1, "unique original complete evaluation required")
    original_request = evaluations[0]["response"]["value"]
    require(original_request["recipe_pin"] == d["trial_commitment"]["recipe"], "original trial recipe differs")
    original = _qualified_feedback(original_request["bindings"],
        recipe_pin=original_request["recipe_pin"], repo_root=root)
    old_e, old_recipe, old_registration, _, _, _, _ = original
    require(content_hash(old_e) == d["trial_commitment"]["family_sha256"]
            and old_registration["registration_sha256"] == d["trial_commitment"]["registration_sha256"]
            and recipe["run_ids"]["read"] != old_recipe["run_ids"]["read"]
            and registration["member_bindings"] == old_registration["member_bindings"],
            "rejected trial source changed or new READ missing")
    trial_policies = {c: archive.load_policy(registration["member_bindings"][c]["bundle_id"]).as_json()
                      for c in candidates}
    fixed = ("seed_config_sha256", "construction_instruction", "supply", "knowledge", "construction_receipt")
    require(all({k: trial_policies[c][k] for k in fixed} == {k: policies[c].as_json()[k] for k in fixed}
                for c in candidates), "rejected history changed fixed supply/base")
    groups = _candidate_groups(e, recipe, registration, candidates, reference)
    packet = {"algorithm": algorithm, "iteration": iteration, "family_id": recipe["family_id"],
        "family_commitment": {"sha256": content_hash(e), "registration_sha256": registration["registration_sha256"]},
        "groups": groups, "business_measurements": measured_rows(e, candidates, registration["member_bindings"],
            profile=protocol["measurement_profile"]), "official_summaries": e["summaries"],
        "policies": {c: {"bundle_id": registration["member_bindings"][c]["bundle_id"], "policy": p}
                     for c, p in trial_policies.items()}, "feedback_profile": profile}
    packet["template_feedback"] = template_feedback(packet, profile)
    packet["input_sha256"] = content_hash(packet)
    view = proposer_view(packet)
    return {"schema": "saea-rejected-template-history-v1", "previous_decision_sha256": previous_sha,
        "status": "rejected", "promoted_to_parent": False, "source_recipe": source["recipe_pin"],
        "family_commitment": packet["family_commitment"], "policies": view["policies"],
        "template_feedback": view["template_feedback"]}


def _load_iteration_state(archive, previous_sha, *, algorithm, iteration, ids, reference, repo_root):
    if previous_sha is None:
        return None
    sha(previous_sha)
    decisions = [json.loads(p.read_text()) for p in (archive.root / "context-learning/iterations").glob("*/decision.json")]
    matching = [d for d in decisions if d.get("decision_sha256") == previous_sha]
    require(len(matching) == 1, "exact prior decision required")
    d = matching[0]
    require(content_hash({k: v for k, v in d.items() if k != "decision_sha256"}) == previous_sha
            and d["algorithm"] == algorithm and d["iteration"] == iteration - 1
            and d["sample_ids"] == ids and d["reference_sha256"] == content_hash(reference),
            "prior iteration custody/scope differs")
    state = d["state_after"]
    sources = {}
    for program in state["programs"]:
        identity = content_hash({"recipe": program["source_recipe"], "bindings": program["source_bindings"]})
        if identity not in sources:
            source = _qualified_feedback(program["source_bindings"], recipe_pin=program["source_recipe"], repo_root=repo_root)
            e, recipe, registration, protocol, candidates, _, frozen = source
            require(recipe["sample_ids"] == ids and frozen == reference, "historical feedback cohort/reference differs")
            measured_rows(e, candidates, registration["member_bindings"], profile=protocol["measurement_profile"])
            sources[identity] = (e, registration, _candidate_groups(e, recipe, registration, candidates, frozen), candidates)
        e, registration, groups, candidates = sources[identity]
        require(content_hash(e) == program["source_family_sha256"], "historical complete-family commitment differs")
        own = [c for c in candidates if registration["member_bindings"][c]["bundle_id"] == program["bundle_id"]]
        require(len(own) == 1 and program["scores"] == {g["sample_id"]:
            next(m["utility"] for m in g["members"] if m["candidate_id"] == own[0]) for g in groups},
            "historical program scores/bundle differ from qualified source")
    return state


def _trial_feedback(request, *, root, initial, expected, changed):
    require(isinstance(request, dict) and set(request) == {"bindings", "recipe_pin"},
            "evaluation must return source bindings, never caller-entered reward")
    trial = _qualified_feedback(request["bindings"], recipe_pin=request["recipe_pin"], repo_root=root)
    e, recipe, registration, protocol, candidates, controls, reference = trial
    old_e, old_recipe, old_registration, old_protocol, old_candidates, old_controls, old_reference = initial
    require(recipe["family_id"] != old_recipe["family_id"] and candidates == old_candidates
            and controls == old_controls and recipe["sample_ids"] == old_recipe["sample_ids"]
            and reference == old_reference and protocol["frozen_reference"] == old_protocol["frozen_reference"]
            and protocol["sampling"] == old_protocol["sampling"]
            and protocol["measurement_profile"] == old_protocol["measurement_profile"],
            "prospective trial roster/reference/envelope differs")
    for cid, binding in registration["member_bindings"].items():
        old = old_registration["member_bindings"][cid]
        require(binding["bundle_id"] == (expected[cid] if cid in expected else old["bundle_id"])
                and binding["run_id"] != old["run_id"] and binding["attempt_id"] != old["attempt_id"],
                "trial must contain exact child/unchanged systems and fresh attempts")
    business = measured_rows(e, candidates, registration["member_bindings"], profile=protocol["measurement_profile"])
    groups = _candidate_groups(e, recipe, registration, candidates, reference)
    require(changed and len(groups) * len(candidates) == 80, "trial must retain complete N by K exposure")
    return groups, business, {"recipe": request["recipe_pin"], "family_sha256": content_hash(e),
                             "registration_sha256": registration["registration_sha256"]}


def run_context_learning_iteration(archive, *, bindings, recipe_pin, repo_root,
                                   algorithm, iteration, policies, callbacks,
                                   previous_decision_sha256=None):
    """Run one bounded learning iteration through externally authorized callables.

    Default GEPA selection/RR/strict-sum rules follow pinned upstream source.
    Full N20 TRAIN replacement-cohort evaluation and quality-gated TF retention
    are explicit study adaptations. Retention never grants scientific adoption.
    """
    require(algorithm in CONTEXT_LEARNING_ALGORITHMS and isinstance(callbacks, ContextLearningCallbacks),
            "explicit baseline/callback seams required")
    root = Path(repo_root).resolve()
    initial = _qualified_feedback(bindings, recipe_pin=recipe_pin, repo_root=root)
    evidence, recipe, registration, protocol, candidates, controls, reference = initial
    plan_pin, plan = _iteration_plan(protocol, recipe, root, algorithm, iteration, controls)
    if "rejected_trial_feedback" in plan:
        require(plan["rejected_trial_feedback"]["previous_decision_sha256"] == previous_decision_sha256,
                "rejected-trial plan must bind the exact previous state")
    groups = _candidate_groups(evidence, recipe, registration, candidates, reference)
    active = {c: policies[c].bundle_id for c in candidates}
    previous = _load_iteration_state(archive, previous_decision_sha256, algorithm=algorithm,
        iteration=iteration, ids=recipe["sample_ids"], reference=reference, repo_root=root)
    state = {"active_bundle_ids": active, "experience": {}, "component_cursors": {}, "programs": []} if previous is None else previous
    state = json.loads(canonical(state))
    experience_transition = None
    if "experience_transition" in plan:
        require(previous is not None and plan["experience_transition"]["previous_decision_sha256"]
                == previous_decision_sha256, "phase transition must bind the exact prior decision")
        experience_transition = {**plan["experience_transition"],
            "prior_experience_sha256": content_hash(state["experience"]),
            "prior_experience_entries": len(state["experience"]),
            "original_archive_preserved": True, "new_phase_experience_sha256": content_hash({})}
        state["experience"] = {}
    if previous is not None:
        require(set(active.values()) <= {p["bundle_id"] for p in state["programs"]},
                "a rejected/unregistered program cannot silently become the next parent")
    for c in candidates:
        scores = {g["sample_id"]: next(m["utility"] for m in g["members"] if m["candidate_id"] == c) for g in groups}
        old = next((p for p in state["programs"] if p["bundle_id"] == active[c]), None)
        if old is None:
            state["programs"].append({"bundle_id": active[c], "scores": scores, "source_recipe": recipe_pin,
                "source_bindings": bindings, "source_family_sha256": content_hash(evidence)})
        else:
            old.update(scores=scores, source_recipe=recipe_pin, source_bindings=bindings,
                       source_family_sha256=content_hash(evidence))
    state["active_bundle_ids"] = active
    schedule = None
    if algorithm == "gepa":
        schedule = select_gepa_task(state["programs"], sample_ids=recipe["sample_ids"],
                                    selection_seed=plan["selection_seed"], state=state)
        require(schedule["parent_bundle_id"] in active.values(),
                "selected historical parent requires a prospectively registered K-family")
        state.update(schedule["state_after"])
        selected = next(c for c in candidates if active[c] == schedule["parent_bundle_id"])
        packet = prepare_context_optimizer_input(archive, bindings=bindings, recipe_pin=recipe_pin,
            repo_root=root, algorithm=algorithm, iteration=iteration, policies=policies,
            candidate_id=selected, component=schedule["component"], feedback_profile=plan.get("feedback_profile"))
    else:
        packet = prepare_context_optimizer_input(archive, bindings=bindings, recipe_pin=recipe_pin,
            repo_root=root, algorithm=algorithm, iteration=iteration, policies=policies, experiences=state["experience"], feedback_profile=plan.get("feedback_profile"))
    directory = f"context-learning/iterations/{algorithm}-{iteration}"
    archive._write(directory + "/reservation.json", {"plan": plan_pin, "input_sha256": packet["input_sha256"],
        "previous_decision_sha256": previous_decision_sha256, "callbacks_do_not_grant_contact_authority": True})
    counts = dict.fromkeys(plan["callback_caps"], 0)
    events, updates = [], []
    decision = {"schema": "saea-context-learning-iteration-decision-v1", "algorithm": algorithm,
        "iteration": iteration, "input_sha256": packet["input_sha256"], "plan": plan_pin,
        "sample_ids": recipe["sample_ids"], "reference_sha256": content_hash(reference),
        "qualified_input_family_budget": packet["budget"],
        "input_family_is_reused_qualified_evidence": True,
        "qualified_input_family_sha256": packet["family_commitment"]["sha256"],
        "sampling": packet["sampling"], "selection_seed": plan["selection_seed"], "schedule": schedule,
        "formal_adoption": False, "runtime_admission": False, "automatic_next_iteration": False,
        "fidelity": {"gepa_selector": "pinned-default-instance-pareto-frequency", "gepa_component": "pinned-per-program-round-robin",
            "gepa_acceptance": "pinned-strict-sum-improvement", "evaluation": "full-registered-N20-TRAIN-study-adaptation",
            "tf_sampling": "deterministic-distinct-context-study-adaptation", "tf_retention": "quality-gated-study-adaptation"},
        "business_before": packet["business_measurements"], "business_after": None,
        "updates": updates, "status": "failed", "error": None}
    if "feedback_profile" in packet:
        decision["feedback_profile"] = packet["feedback_profile"]
        decision["fidelity"]["reflection"] = "template-batch-study-adaptation-v1"
    if "rejected_trial_feedback" in packet:
        decision["rejected_trial_feedback_sha256"] = content_hash(packet["rejected_trial_feedback"])
        decision["fidelity"]["rejected_trial_feedback"] = "prospective-own-rejected-trial-aggregate-v1"
    if experience_transition is not None:
        decision["experience_transition"] = experience_transition
        decision["fidelity"]["experience_transition"] = "prospective-template-only-phase-reset"
    reserved_candidate = reserved_control = 0

    def invoke(stage, task):
        nonlocal reserved_candidate, reserved_control
        require(counts[stage] < plan["callback_caps"][stage], "callback stage cap exhausted; no retry")
        callback = getattr(callbacks, stage)
        require(callable(callback), f"explicit {stage} callback required")
        counts[stage] += 1
        if stage == "evaluate":
            reserved_candidate = 80
            reserved_control = 20 * len(controls)
        identity = f"{len(events):04d}-{stage}"
        archive._write(directory + f"/events/{identity}-reserved.json", {"stage": stage, "task": task,
            "task_sha256": content_hash(task), "opportunity_consumed": True})
        started = time.perf_counter()
        unknown = dict.fromkeys(("provider_contacts", "input_tokens", "output_tokens"), None)
        event = {"stage": stage, "identity": identity, "usage": unknown,
                 "provenance": None, "response": None, "status": "failed"}
        events.append(event)
        try:
            response = callback(task)
            # Invalid Python objects cannot enter JSON custody or erase the
            # consumed opportunity. The external callback owns its raw source.
            event["response"] = {"invalid_response_type": type(response).__name__}
            canonical(response)
            event["response"] = response
            require(isinstance(response, dict) and set(response) == {"value", "provenance", "usage"}
                    and isinstance(response["provenance"], dict) and response["provenance"], "callback provenance envelope required")
            usage = response["usage"]
            require(isinstance(usage, dict) and set(usage) == set(unknown)
                    and all(v is None or type(v) is int and v >= 0 for v in usage.values()), "invalid callback usage")
            event.update(provenance=response["provenance"], usage=usage)
            from .prepared_feedback import reject_non_latin_scripts
            reject_non_latin_scripts(response)
            event["status"] = "completed"
            return response["value"]
        except Exception as error:
            event["error_type"] = type(error).__name__
            raise
        finally:
            event["callback_elapsed_seconds"] = time.perf_counter() - started
            archive._write(directory + f"/events/{identity}-{event['status']}.json", event)

    try:
        operations, experience_after = None, state["experience"]
        if algorithm == "tf-grpo-context-diversity":
            comparisons = []
            for group in ([] if "template_feedback" in packet else packet["groups"]):
                if group["semantic_advantage"] == "skip-zero-variation":
                    continue
                summaries = []
                for member in group["members"]:
                    summary = invoke("summarize", {"input_sha256": packet["input_sha256"],
                        "sample_id": group["sample_id"], "rollout": member})
                    _text(summary)
                    summaries.append({"rollout_id": member["rollout_id"], "utility": member["utility"], "summary": summary})
                comparison = invoke("compare", {"input_sha256": packet["input_sha256"], "sample_id": group["sample_id"],
                    "summaries": summaries, "experience": state["experience"]})
                _text(comparison)
                comparisons.append({"sample_id": group["sample_id"], "semantic_advantage": comparison})
            varying = any(g["semantic_advantage"] != "skip-zero-variation" for g in packet["groups"])
            if not varying:
                decision["status"] = "skip-zero-variation"
            else:
                task = {"input_sha256": packet["input_sha256"], "experience": state["experience"]}
                if "template_feedback" in packet:
                    view = proposer_view(packet)
                    task["template_feedback"] = view["template_feedback"]
                    if packet["feedback_profile"]["examples_per_template"] == 0:
                        task.update(policies=view["policies"], reflection_task=view["reflection_task"])
                        if "rejected_trial_feedback" in view:
                            task["rejected_trial_feedback"] = view["rejected_trial_feedback"]
                else:
                    task["comparisons"] = comparisons
                operations = invoke("update_experience", task)
                experience_after = apply_experience_operations(state["experience"], operations)
        task_candidates = [selected] if algorithm == "gepa" else candidates if decision["status"] != "skip-zero-variation" else []
        trial_policies = dict(active)
        changed = []
        actor_input = proposer_view(packet)
        for c in task_candidates:
            response = invoke("propose", {"input_sha256": packet["input_sha256"], "candidate_id": c,
                "algorithm": algorithm, "iteration": iteration,
                "parent_bundle_id": active[c], "component": schedule["component"] if schedule else "joint-system",
                "policy": actor_input["policies"][c]["policy"], "experience": experience_after,
                "qualified_input": actor_input})
            update = record_context_update(archive, input_sha256=packet["input_sha256"], update_id=f"system-{candidates.index(c)}",
                proposal_document=response, experience_operations=operations, expected_candidate_id=c)
            updates.append(update)
            if update["status"] == "provisional":
                trial_policies[c] = update["bundle_id"]
                changed.append(c)
        if task_candidates and not changed:
            decision["status"] = "invalid" if any(u["status"] == "invalid" for u in updates) else "no-change"
        if changed:
            require(len({content_hash({k: archive.load_policy(b).as_json()[k]
                for k in ("role_text", "context_layout", "node_context")}) for b in trial_policies.values()}) == 4,
                "trial K must retain four distinct prompt-and-assembly systems")
            request = invoke("evaluate", {"input_sha256": packet["input_sha256"], "policies": trial_policies,
                "changed_members": changed, "control_members": controls, "sample_ids": recipe["sample_ids"],
                "sampling": packet["sampling"], "measurement_profile": packet["measurement_profile"]})
            trial_groups, business, trial_commitment = _trial_feedback(request, root=root, initial=initial,
                expected=trial_policies, changed=changed)
            before = sum(m["utility"] for g in groups for m in g["members"]
                         if algorithm != "gepa" or m["candidate_id"] == selected)
            after = sum(m["utility"] for g in trial_groups for m in g["members"]
                        if algorithm != "gepa" or m["candidate_id"] == selected)
            decision.update(utility_before=before, utility_after=after, trial_commitment=trial_commitment,
                            business_after=business, status="retained-for-optimization" if after > before else "rejected")
            if after > before:
                state["active_bundle_ids"] = trial_policies
                state["experience"] = experience_after
                for c in changed:
                    scores = {g["sample_id"]: next(m["utility"] for m in g["members"] if m["candidate_id"] == c) for g in trial_groups}
                    state["programs"].append({"bundle_id": trial_policies[c], "scores": scores, "source_recipe": request["recipe_pin"],
                        "source_bindings": request["bindings"], "source_family_sha256": trial_commitment["family_sha256"]})
                    if algorithm == "gepa":
                        state["component_cursors"][trial_policies[c]] = state["component_cursors"][active[c]]
    except Exception as error:
        message = str(error)
        try:
            _text(message)
        except ValueError:
            message = "External callback must preserve and translate the original exception source."
        decision.update(status="failed", error={"type": type(error).__name__, "message": message})
    decision["state_after"] = state
    decision["events"] = events
    accounting = {"callback_counts": counts, "evaluation_candidate_trajectories_reserved": reserved_candidate,
                  "evaluation_control_trajectories_reserved": reserved_control}
    for k in ("provider_contacts", "input_tokens", "output_tokens"):
        values = [e["usage"][k] for e in events]
        accounting[k] = None if None in values else sum(values)
    accounting["callback_elapsed_seconds"] = sum(e["callback_elapsed_seconds"] for e in events)
    decision["accounting"] = accounting
    decision["decision_sha256"] = content_hash(decision)
    archive._write(directory + "/decision.json", decision)
    return decision


def _population_update_input(archive, input_sha256):
    """Load a private, prospectively prepared packet; do not grant READ authority."""
    sha(input_sha256)
    matches = [json.loads(p.read_text()) for p in (archive.root / "context-learning/inputs").glob("*.json")]
    matches = [p for p in matches if p.get("input_sha256") == input_sha256]
    require(len(matches) == 1, "exact immutable optimizer input required")
    packet = matches[0]
    require(content_hash({k: v for k, v in packet.items() if k != "input_sha256"}) == input_sha256,
            "optimizer input hash differs")
    if packet.get("schema") in ("saea-partitioned-context-optimizer-input-v1", "saea-partitioned-context-optimizer-input-v2"):
        from .system_context_partitioned_learning import validate_partitioned_packet
        return validate_partitioned_packet(archive, packet)
    require(packet.get("schema") == "saea-context-optimizer-input-v1"
            and packet.get("algorithm") == "tf-grpo-context-diversity"
            and type(packet.get("iteration")) is int and packet["iteration"] > 0,
            "prospective TF population input required")
    plan = packet.get("population_update_plan")
    require(isinstance(packet.get("policies"), dict) and packet["policies"], "configured policies required")
    ids = list(packet["policies"])
    require(all(isinstance(c, str) and c and c.isascii() for c in ids), "candidate identities required")
    require(isinstance(plan, dict) and set(plan) == {"schema", "batch_id", "model", "reasoning_effort",
            "semantic_batches", "proposal_slots"}
            and plan["schema"] == "saea-context-population-update-plan-v1"
            and isinstance(plan["batch_id"], str)
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", plan["batch_id"])
            and isinstance(plan["model"], str) and plan["model"]
            and isinstance(plan["reasoning_effort"], str) and plan["reasoning_effort"]
            and type(plan["semantic_batches"]) is int and plan["semantic_batches"] > 0
            and type(plan["proposal_slots"]) is int and plan["proposal_slots"] == len(ids),
            "exact configured population plan required")
    budget = packet.get("budget", {})
    n = budget.get("N")
    require(type(n) is int and n > 0 and type(budget.get("K")) is int and budget["K"] == len(ids)
            and budget.get("candidate_trajectories") == len(ids)*n
            and type(budget.get("control_trajectories")) is int and budget["control_trajectories"] >= n
            and budget["control_trajectories"] % n == 0
            and budget.get("family_trajectories") == len(ids)*n + budget["control_trajectories"],
            "exact population evaluation accounting required")
    if "experiment_population" in packet:
        from .experiment_population import load_population_config, require_population_binding, population_accounting
        config = load_population_config(packet["experiment_population"], repo_root=archive.root)
        cohort = require_population_binding(config, packet["experiment_population"], packet.get("population_cohort"), packet)
        require(ids == cohort["candidate_ids"]
                and budget == population_accounting(config, cohort["cohort_id"])
                and [g["sample_id"] for g in packet["groups"]] == cohort["sample_ids"]
                and all(plan[k] == config["proposer"][k] for k in ("model", "reasoning_effort", "semantic_batches")),
                "optimizer input differs from pinned population config")
    groups = packet.get("groups")
    require(isinstance(groups, list) and len(groups) == n
            and len({g["sample_id"] for g in groups}) == n
            and all([m["candidate_id"] for m in g["members"]] == ids for g in groups),
            "complete paired population input required")
    for entry in packet["policies"].values():
        require(archive.load_policy(entry["bundle_id"]).as_json() == entry["policy"],
                "immutable input policy bytes differ")
    return packet, plan, ids


def reserve_context_population_update(archive, *, input_sha256, actor_input_sha256):
    """Consume the configured semantic batches and all slots before actor contact.

    The caller separately owns source qualification, prospective model admission
    and enforceable actor isolation. This reservation invokes no model or runtime.
    """
    packet, plan, ids = _population_update_input(archive, input_sha256)
    # Hash the isolated actor capsule after the private packet has its identity;
    # binding it in the reservation avoids a circular pair of content hashes.
    sha(actor_input_sha256)
    record = {"schema": "saea-context-population-reservation-v1", "input_sha256": input_sha256,
              "actor_input_sha256": actor_input_sha256,
              "plan": plan, "candidate_ids": ids, "algorithm": packet["algorithm"],
              "iteration": packet["iteration"], "proposal_slots": len(ids),
              "semantic_batches": plan["semantic_batches"], "runtime_admission": False}
    record.update({k: packet[k] for k in ("experiment_population", "population_cohort", "source_population") if k in packet})
    archive._write(f"context-learning/populations/{plan['batch_id']}/reservation.json", record)
    return record


def record_context_population_update(archive, *, input_sha256, response_document):
    """Preserve one original batch, then reuse the shared per-slot compiler.

    Invalid and no-change slots remain spent; no repair, callback, scoring or
    activation occurs. An unexpected archival failure preserves the response
    and refuses reentry until an explicit incident disposition is implemented.
    """
    packet, plan, ids = _population_update_input(archive, input_sha256)
    base = f"context-learning/populations/{plan['batch_id']}"
    reservation_path = archive.root / base / "reservation.json"
    require(reservation_path.is_file(), "population must be reserved before contact")
    reservation = json.loads(reservation_path.read_text())
    require(reservation.get("input_sha256") == input_sha256 and reservation.get("plan") == plan
            and reservation.get("candidate_ids") == ids and reservation.get("proposal_slots") == len(ids)
            and all(reservation.get(k) == packet.get(k) for k in ("experiment_population", "population_cohort", "source_population")),
            "exact population reservation required")
    sha(reservation.get("actor_input_sha256"))
    raw = {"schema": "saea-context-population-original-response-v1", "input_sha256": input_sha256,
           "response_sha256": content_hash(response_document), "response_document": response_document}
    raw.update({k: packet[k] for k in ("experiment_population", "population_cohort", "source_population") if k in packet})
    archive._write(base + "/response.json", raw)
    result = {"schema": "saea-context-population-update-record-v1", "input_sha256": input_sha256,
              "response_sha256": raw["response_sha256"], "status": "recorded", "records": [],
              "usage": None, "runtime_admission": False}
    result.update({k: packet[k] for k in ("experiment_population", "population_cohort", "source_population") if k in packet})
    try:
        r = response_document
        require(isinstance(r, dict) and set(r) == {"schema", "input_sha256", "actor_input_sha256",
                "model", "reasoning_effort", "usage", "branches"}
                and r["schema"] == "saea-context-population-update-response-v1"
                and r["input_sha256"] == input_sha256
                and r["actor_input_sha256"] == reservation["actor_input_sha256"]
                and all(r[k] == plan[k] for k in ("model", "reasoning_effort")),
                "original population envelope differs")
        require(isinstance(r["usage"], dict)
                and set(r["usage"]) == {"provider_contacts", "input_tokens", "output_tokens"}
                and all(v is None or type(v) is int and v >= 0 for v in r["usage"].values()),
                "original provider usage differs")
        require(isinstance(r["branches"], list) and len(r["branches"]) == len(ids),
                "all configured original response positions required")
    except ValueError as error:
        result.update(status="invalid-envelope", error=str(error),
                      records=[{"candidate_id": cid, "status": "invalid"} for cid in ids])
    else:
        result["usage"] = dict(r["usage"])
        for cid, row in zip(ids, r["branches"], strict=True):
            try:
                require(isinstance(row, dict) and set(row) == {"candidate_id", "proposal", "experience_operations"}
                        and row["candidate_id"] == cid, "original branch position or shape differs")
            except ValueError as error:
                result["records"].append({"candidate_id": cid, "status": "invalid", "error": str(error)})
                continue
            update = record_context_update(archive, input_sha256=input_sha256,
                update_id=f"{plan['batch_id']}-{cid}", proposal_document=row["proposal"],
                experience_operations=row["experience_operations"], expected_candidate_id=cid)
            result["records"].append({"candidate_id": cid, **update})
    archive._write(base + "/result.json", result)
    return result


def context_population_actor_view(archive, *, input_sha256, source):
    """Build a template-only actor view from a pinned abstract source.

    The caller owns full-family/source READ and isolation admission. No raw
    trajectory, source roster, runtime knowledge or private source ID is copied.
    This builds no per-sample semantic task and invokes no model.
    """
    from copy import deepcopy
    from ..analysis.abstract_node_feedback import abstract_population_feedback, FEEDBACK_SCHEMA

    packet, plan, ids = _population_update_input(archive, input_sha256)
    binding = packet.get("abstract_source")
    require(isinstance(binding, dict) and set(binding) == {"source_sha256", "source_batch"},
            "exact abstract source admission required")
    sha(binding["source_sha256"])
    require(content_hash(source) == binding["source_sha256"], "pinned abstract source differs")
    feedback = abstract_population_feedback(source,
        expected_bundles={cid: packet["policies"][cid]["bundle_id"] for cid in ids},
        expected_family_id=packet["family_id"], expected_source_batch=binding["source_batch"],
        sample_count=packet["budget"]["N"], reference_f1=packet["reference"]["f1"])
    for abstract_group, original_group in zip(feedback["groups"], packet["groups"], strict=True):
        for abstract, original in zip(abstract_group["members"], original_group["members"], strict=True):
            terminal, execution = abstract["terminal"], original["execution"]
            require(abstract["candidate_id"] == original["candidate_id"]
                    and terminal["official_counts"] == original["native_counts"]
                    and terminal["utility"] == original["utility"],
                    "abstract terminal feedback differs from private qualified source")
            require(terminal["reliable"] == execution["reliable_completion"]
                    and terminal["abstained"] == execution["abstained"]
                    and terminal["sample_seconds"] == execution["wall_time_seconds"]
                    and len(abstract["nodes"]) == execution["model_calls"],
                    "abstract operational feedback differs from private qualified source")
    measured = packet.get("business_measurements")
    require(isinstance(measured, list) and len(measured) == len(ids),
            "complete measured business objectives required")
    business = []
    numeric_fields = ("slu_f1", "intent", "reliable_completion_rate", "mean_sample_seconds",
                      "non_first_mean_seconds", "model_calls", "tool_calls")
    for position, (cid, row) in enumerate(zip(ids, measured, strict=True)):
        require(isinstance(row, dict) and row.get("candidate_id") == cid
                and row.get("bundle_id") == packet["policies"][cid]["bundle_id"],
                "measured objective policy identity differs")
        sha(row.get("timing_report_sha256"))
        require(all(type(row.get(k)) in (int, float) and math.isfinite(row[k]) and row[k] >= 0
                    for k in numeric_fields) and type(row.get("eligible")) is bool,
                "finite measured objectives and eligibility required")
        terminals = [g["members"][position]["terminal"] for g in feedback["groups"]]
        seconds = [t["sample_seconds"] for t in terminals]
        require(math.isclose(row["mean_sample_seconds"], math.fsum(seconds)/len(seconds),
                             abs_tol=1e-10, rel_tol=1e-12)
                and math.isclose(row["reliable_completion_rate"],
                                 sum(t["reliable"] for t in terminals)/len(terminals), abs_tol=1e-12)
                and row["model_calls"] == sum(len(g["members"][position]["nodes"]) for g in feedback["groups"]),
                "measured aggregate differs from complete abstract episodes")
        # Actual admission order was verified by measured_rows upstream. Never
        # treat anonymous roster index zero as the first admitted sample.
        first_cost = math.fsum(seconds) - row["non_first_mean_seconds"] * (len(seconds)-1)
        require(any(math.isclose(first_cost, value, abs_tol=1e-8, rel_tol=1e-10) for value in seconds),
                "non-first timing cannot exclude a recorded sample")
        summary = feedback["templates"][position]["official_summary"]
        require(row["slu_f1"] == summary["slu_f1"] and row["intent"] == summary["intent"]
                and all(row[k] <= 1 for k in ("slu_f1", "intent", "reliable_completion_rate")),
                "official quality units or summary differ")
        business.append({"candidate_id": cid, **{k: row[k] for k in numeric_fields}, "eligible": row["eligible"]})
    templates = {cid: {"bundle_id": packet["policies"][cid]["bundle_id"],
                      **{k: deepcopy(packet["policies"][cid]["policy"][k])
                         for k in ("role_text", "context_layout", "node_context")}} for cid in ids}
    return {"schema": "saea-context-population-actor-view-v1",
            **{k: packet[k] for k in ("experiment_population", "population_cohort", "source_population") if k in packet},
            "optimizer_input_sha256": input_sha256, "algorithm": packet["algorithm"],
            "iteration": packet["iteration"], "model": plan["model"],
            "reasoning_effort": plan["reasoning_effort"], "templates": templates,
            "representation": deepcopy(FEEDBACK_SCHEMA), "feedback": feedback,
            "business_measurements": business,
            "budget": {"M": packet["budget"].get("M", len(ROLES)), **{k: packet["budget"][k] for k in
                ("N", "K", "candidate_trajectories", "control_trajectories", "family_trajectories")}},
            "runtime_admission": False,
            "instructions": f"Produce one original response containing all {len(ids)} reserved template updates in order. "
                "Optimize complete node instructions and supported assembly using abstract behavior and complete-system "
                "quality, intent, reliability and measured sample latency. Keep knowledge, retrieval, data, interfaces "
                "and decoding fixed. Never request concrete cases, source rosters or per-sample semantic summaries. "
                "Unknown node correctness remains unknown; terminal reward is not causal node credit. "
                "Preserve no-change and failed hypotheses instead of fabricating positive gains. "
                "Archived free-form experience is not included in this template-only view; materialize proposed "
                "improvements as explicit template/assembly edits. Any proposed experience operations remain offline "
                "and require evaluated retention. No candidate is adopted merely because it is proposed."}


def qualify_context_population_trial(archive, *, input_sha256, request, repo_root, data_root):
    """Qualify one complete configured successor and describe its retention signal.

    Reuse complete-family READ/seal/score and measured-cost gates. This does
    not adopt a policy, dispatch a run, write optimizer state or resize the
    historical K4 iterator. A root business review remains mandatory.
    """
    packet, plan, ids = _population_update_input(archive, input_sha256)
    require(packet["schema"] == "saea-context-optimizer-input-v1",
            "a partitioned update requires its own prospectively registered complete trial")
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    require(isinstance(request, dict) and set(request) == {"bindings", "recipe_pin"},
            "evaluation requires source bindings, never caller-entered reward")
    base = archive.root / "context-learning" / "populations" / plan["batch_id"]
    result = json.loads((base / "result.json").read_text())
    raw = json.loads((base / "response.json").read_text())
    require(result.get("status") == "recorded" and result.get("input_sha256") == input_sha256
            and result.get("response_sha256") == raw.get("response_sha256")
            == content_hash(raw.get("response_document"))
            and [x.get("candidate_id") for x in result.get("records", [])] == ids
            and all(x.get("status") == "provisional" for x in result["records"]),
            "all configured provisional updates required; other dispositions remain held")
    expected = {row["candidate_id"]: row["bundle_id"] for row in result["records"]}
    old_recipe = _load(packet["recipe"], root)
    old_registration = _load(old_recipe["context_learning_registration"], root)
    require(old_registration["registration_sha256"] == packet["family_commitment"]["registration_sha256"],
            "original qualified registration differs")
    qualified = _qualified_feedback(request["bindings"], recipe_pin=request["recipe_pin"], repo_root=root)
    evidence, recipe, registration, protocol, candidates, controls, reference = qualified
    if "experiment_population" in packet:
        from .experiment_population import load_population_config, require_population_binding
        population = load_population_config(packet["experiment_population"], repo_root=root)
        cohort_config = require_population_binding(population, packet["experiment_population"],
            packet["population_cohort"], protocol, recipe, registration, result, raw)
        expected_controls = cohort_config["control_ids"]
    else:
        expected_controls = list(old_registration["member_bindings"].keys() - set(ids))
    update = protocol.get("learning_update")
    require(isinstance(update, dict) and update.get("algorithm") == packet["algorithm"]
            and update.get("iteration") == protocol.get("iteration") == packet["iteration"],
            "prospective population update identity differs")
    require(_load(update["source_packet"], data) == packet
            and _load(update["original_update_record"], data) == result,
            "registered trial must pin the exact optimizer input and original update record")
    require(recipe["family_id"] != packet["family_id"] and candidates == ids
            and set(controls) == set(expected_controls)
            and recipe["sample_ids"] == [g["sample_id"] for g in packet["groups"]]
            and reference == packet["reference"]
            and protocol["frozen_reference"] == packet["frozen_reference"]
            and protocol["sampling"] == packet["sampling"]
            and protocol["measurement_profile"] == packet["measurement_profile"],
            "successor family roster, reference, sampling or measurement envelope differs")
    require(set(registration["member_bindings"]) == set(ids + controls)
            == set(old_registration["member_bindings"]),
            "both complete candidate/control families required")
    for cid, binding in registration["member_bindings"].items():
        previous = old_registration["member_bindings"][cid]
        require(binding["bundle_id"] == expected.get(cid, previous["bundle_id"])
                and binding["run_id"] != previous["run_id"]
                and binding["attempt_id"] != previous["attempt_id"],
                "trial must use exact original children, unchanged controls and fresh attempts")
        if cid in ids:
            require(previous["bundle_id"] == packet["policies"][cid]["bundle_id"],
                    "source policy ancestry differs")
    groups = _candidate_groups(evidence, recipe, registration, candidates, reference)
    totals = []
    for cohort in (packet["groups"], groups):
        require(len(cohort) == packet["budget"]["N"]
                and [g["sample_id"] for g in cohort] == recipe["sample_ids"]
                and all([m["candidate_id"] for m in g["members"]] == ids for g in cohort),
                "retain every configured candidate trajectory in roster order")
        values = [m["utility"] for g in cohort for m in g["members"]]
        require(all(type(v) in (int, float) and math.isfinite(v) for v in values),
                "finite qualified terminal utilities required")
        totals.append(math.fsum(values))
    business = measured_rows(evidence, candidates, registration["member_bindings"],
                             profile=protocol["measurement_profile"])
    return {"schema": "saea-context-population-qualified-trial-v1",
            **{k: packet[k] for k in ("experiment_population", "population_cohort", "source_population") if k in packet},
            "input_sha256": input_sha256, "response_sha256": result["response_sha256"],
            "trial_commitment": {"recipe": request["recipe_pin"], "family_sha256": content_hash(evidence),
                                 "registration_sha256": registration["registration_sha256"]},
            "before_groups": packet["groups"], "after_groups": groups,
            "business_before": packet["business_measurements"], "business_after": business,
            "utility_before": totals[0], "utility_after": totals[1],
            "utility_increased": totals[1] > totals[0], "criterion": "strict-population-utility-sum",
            "root_review_required": True, "formal_adoption": False, "runtime_admission": False,
            "automatic_next_iteration": False, "contacts_added": {"model": 0, "scorer": 0},
            "interpretation": "Optimization retention signal across separate complete batches on the same "
                              "roster; no common scientific frontier, causal node credit or efficacy claim."}
