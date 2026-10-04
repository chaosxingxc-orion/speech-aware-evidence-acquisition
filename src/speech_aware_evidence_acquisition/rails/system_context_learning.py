"""Offline deterministic context-diversity learner seams on the shared base.

No callback, sampling, execution, scoring, scaling or adoption happens here.
Public input construction freshly verifies registered READ and complete custody;
synthetic unit packets are not scientific-read authority.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

from ..analysis.system_text_panel import _job_metadata
from ..analysis.system_text_pilot import _read_complete_evidence
from .hashing import content_hash
from .system_search_measurement import measured_rows, validate_profile
from .system_text_feedback import CompleteSystemFeedback, feedback_utility
from .system_text_policy import (
    CONTEXT_COMPONENTS, CONTEXT_LEARNING_ALGORITHMS, NODE_BUNDLE_SCHEMA,
    SystemTextPolicyBundle, TextPolicyUpdateProposal, _read_pin, _text, apply_text_proposal,
    require, sha,
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


def _validate_scope(recipe, registration, protocol, *, root):
    require(recipe.get("schema") == "saea-context-learning-analysis-v1"
            and registration.get("schema") == REGISTRATION_SCHEMA
            and protocol.get("schema") == "saea-context-learning-protocol-v1"
            and recipe.get("family_id") == registration.get("family_id") == protocol.get("family_id"),
            "registered context learning scope differs")
    require(registration.get("registration_sha256") == content_hash(
        {k: v for k, v in registration.items() if k != "registration_sha256"}),
        "context registration hash differs")
    owner = _load(protocol["owner"], root)
    contract = owner.get("resolved_contract", {})
    require(owner.get("schema") == "saea-owner-deterministic-context-rollouts-v1"
            and contract.get("initial_N") == protocol.get("N") == 20
            and contract.get("initial_K") == protocol.get("K") == 4
            and contract.get("M") == protocol.get("M") == ROLES
            and contract.get("temperature") == protocol.get("sampling", {}).get("temperature") == 0
            and type(protocol["sampling"]["temperature"]) in (int, float)
            and contract.get("seed") == protocol.get("sampling", {}).get("seed") == 20260913
            and type(protocol["sampling"]["seed"]) is int,
            "exact deterministic N20/K4/four-role owner scope required")
    require(protocol.get("algorithms") == list(CONTEXT_LEARNING_ALGORITHMS)
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
    require(isinstance(candidates, list) and len(candidates) == len(set(candidates)) == 4
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
    require(len({bindings[c]["bundle_id"] for c in candidates}) == 4,
            "K requires distinct complete-system bundles")
    if controls:
        require(bindings["seed"]["bundle_id"] == bindings["seed-aa"]["bundle_id"], "control seed/A/A differs")
    require(recipe["run_ids"]["read"] == registration["read_id"], "context READ identity differs")
    profile = protocol.get("measurement_profile")
    validate_profile(profile)
    require(recipe.get("measurement_profile") == registration.get("measurement_profile") == profile
            and profile["slot_count"] == profile["queue_depth"] == 4, "registered measurement profile differs")
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
                                    candidate_id=None, component=None):
    """Freshly qualify a whole family and save an immutable offline reflection task.

    GEPA's caller chooses a parent among the per-example front and one legal
    component. TF-GRPO receives individual-summary and semantic-comparison tasks.
    No callback is invoked; packet production itself adds zero contacts.
    """
    require(algorithm in CONTEXT_LEARNING_ALGORITHMS and type(iteration) is int and iteration > 0,
            "unknown context baseline/iteration")
    evidence, recipe, registration, protocol, candidates, controls, reference = _qualified_feedback(
        bindings, recipe_pin=recipe_pin, repo_root=repo_root)
    require(iteration == protocol["iteration"] and set(policies) == set(candidates), "registered iteration/policies differ")
    for cid, policy in policies.items():
        SystemTextPolicyBundle.from_json(policy.as_json(), parents=[archive.load_policy(p)
            for p in policy.as_json()["parent_ids"]])
        require(policy.as_json()["schema"] == NODE_BUNDLE_SCHEMA
                and policy.bundle_id == registration["member_bindings"][cid]["bundle_id"],
                "complete four-role policy binding differs")
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
    packet["input_sha256"] = content_hash(packet)
    for policy in policies.values():
        archive.store_policy(policy)
    archive._write(f"context-learning/inputs/{algorithm}-{iteration}.json", packet)
    return packet


def record_context_update(archive, *, input_sha256, update_id, proposal_document, experience_operations=None):
    """Retain one attempted update, including invalid/no-change, with no admission."""
    sha(input_sha256)
    require(isinstance(update_id, str) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,95}", update_id), "invalid update identity")
    packets = [json.loads(p.read_text()) for p in (archive.root / "context-learning/inputs").glob("*.json")]
    matching = [p for p in packets if p.get("input_sha256") == input_sha256]
    require(len(matching) == 1, "exact immutable optimizer input required")
    packet = matching[0]
    require(content_hash({k: v for k, v in packet.items() if k != "input_sha256"}) == input_sha256,
            "optimizer input hash differs")
    path = f"context-learning/updates/{packet['algorithm']}-{packet['iteration']}-{update_id}.json"
    require(not (archive.root / path).exists(), "update record already exists")
    record = {"schema": "saea-context-learning-update-record-v1", "input_sha256": input_sha256,
        "algorithm": packet["algorithm"], "iteration": packet["iteration"], "update_id": update_id,
        "raw_proposal": proposal_document, "experience_operations": experience_operations,
        "status": "invalid", "error": None, "runtime_admission": False}
    try:
        proposal = TextPolicyUpdateProposal.from_context_json(proposal_document)
        p = proposal.as_json()
        require(p["algorithm"] == packet["algorithm"] and p["iteration"] == packet["iteration"]
                and p["candidate_id"] in packet["policies"] and p["evidence"] == [input_sha256],
                "update differs from optimizer input/evidence commitment")
        parent_id = packet["policies"][p["candidate_id"]]["bundle_id"]
        require(p["parent_ids"] == [parent_id], "update parent differs from evaluated complete system")
        if packet["algorithm"] == "tf-grpo-context-diversity":
            require(p["component"] == "joint-system", "TF update must bind the joint-system task")
            operations = [] if experience_operations is None else experience_operations
            require(any(g["semantic_advantage"] != "skip-zero-variation" for g in packet["groups"])
                    or (not p["changes"] and not operations), "zero variation gives no semantic advantage")
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
        exposed_ids = sorted(set(packet["reference"]["sample_ids"]) |
                             {g["sample_id"] for g in packet["groups"]})
        sources = [{"kind": "feedback", "sha256": input_sha256,
                    "sample_ids": exposed_ids},
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
