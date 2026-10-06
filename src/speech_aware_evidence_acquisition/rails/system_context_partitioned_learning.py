"""Configuration-driven multi-source input for the shared context update compiler.

Keep historical cohorts separate. Preparation freshly qualifies every source;
reservation and response storage reuse the existing one-shot archive lifecycle.
No function here invokes an actor, a scorer, or an experiment executor.
"""
from copy import deepcopy
import json
import math
import re
from pathlib import Path

from ..analysis.abstract_population_projection import project_registered_population
from ..analysis.abstract_population_sources import read_registered_population_sources
from ..analysis.abstract_node_feedback import abstract_partitioned_population_feedback, FEEDBACK_SCHEMA
from .experiment_population import load_population_config, population_accounting
from .hashing import content_hash
from .system_text_policy import _read_pin, require

SCHEMA = "saea-partitioned-context-optimizer-input-v1"


def _plan(plan, config):
    ids = [cid for c in config["cohorts"] for cid in c["candidate_ids"]]
    require(isinstance(plan, dict) and set(plan) == {"schema", "batch_id", "model", "reasoning_effort",
            "semantic_batches", "proposal_slots"}
            and plan["schema"] == "saea-context-population-update-plan-v1"
            and isinstance(plan["batch_id"], str)
            and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", plan["batch_id"])
            and type(plan["proposal_slots"]) is int and plan["proposal_slots"] == len(ids)
            and all(type(plan[k]) is type(config["proposer"][k]) and plan[k] == config["proposer"][k]
                    for k in ("model", "reasoning_effort", "semantic_batches")),
            "exact configured partitioned update plan required")
    return ids


def validate_partitioned_packet(archive, packet):
    """Reject changed membership, policies or normalized feedback before contact."""
    if packet.get("schema") == "saea-partitioned-context-optimizer-input-v2":
        from .system_context_continuation import validate_continuation_packet
        return validate_continuation_packet(archive, packet)
    fields = {"schema", "algorithm", "iteration", "registration", "source_population", "source_commitment",
              "population_update_plan", "policies", "feedback_sample_ids", "experience", "learner_view",
              "budget", "runtime_admission", "contacts_added", "input_sha256"}
    require(set(packet) == fields and packet["schema"] == SCHEMA
            and packet["algorithm"] == "tf-grpo-context-diversity"
            and type(packet["iteration"]) is int and packet["iteration"] > 0
            and packet["runtime_admission"] is False and packet["experience"] == {}
            and content_hash({k: v for k, v in packet.items() if k != "input_sha256"}) == packet["input_sha256"],
            "immutable partitioned optimizer packet required")
    config = load_population_config(packet["source_population"], repo_root=archive.root)
    ids = _plan(packet["population_update_plan"], config)
    require(list(packet["policies"]) == ids and packet["budget"] == population_accounting(config),
            "complete configured historical accounting required")
    require(isinstance(packet["feedback_sample_ids"], list) and packet["feedback_sample_ids"]
            and packet["feedback_sample_ids"] == sorted(set(packet["feedback_sample_ids"]))
            and all(s.startswith("slurp:train:") for s in packet["feedback_sample_ids"])
            and all(s in packet["feedback_sample_ids"] for c in config["cohorts"] for s in c["sample_ids"]),
            "retain complete TRAIN feedback exposure")
    for entry in packet["policies"].values():
        require(archive.load_policy(entry["bundle_id"]).as_json() == entry["policy"],
                "immutable observed policy bytes differ")
    view = packet["learner_view"]
    require(set(view) == {"schema", "representation", "population", "business_measurements", "templates"}
            and view["schema"] == "saea-abstract-population-learning-view-v1"
            and view["representation"] == FEEDBACK_SCHEMA, "exact abstract representation required")
    cohorts = view["population"]["cohorts"]
    tags = [c["cohort_id"] for c in config["cohorts"]]
    require(list(cohorts) == tags and list(view["templates"]) == tags
            and list(view["business_measurements"]) == tags, "all separate source cohorts required")
    sources, contracts = {}, {}
    for c in config["cohorts"]:
        tag, members = c["cohort_id"], c["candidate_ids"]
        cohort = cohorts[tag]
        expected = {cid: packet["policies"][cid]["bundle_id"] for cid in members}
        require(list(view["templates"][tag]) == members, "all complete templates required")
        templates = []
        for position, cid in enumerate(members):
            policy = packet["policies"][cid]["policy"]
            require(view["templates"][tag][cid] == {"bundle_id": expected[cid],
                    **{k: policy[k] for k in ("role_text", "context_layout", "node_context")}},
                    "actor template differs from evaluated policy")
            summary = cohort["templates"][position]
            samples = []
            for group in cohort["groups"]:
                require([m["candidate_id"] for m in group["members"]] == members,
                        "preserve each original relative-return group")
                member = group["members"][position]
                samples.append({"input_index": group["input_index"],
                    **{k: member[k] for k in ("nodes", "missing_roles", "terminal")}})
            templates.append({**summary, "samples": samples})
        sources[tag] = {"source_batch": cohort["source_batch"], "family_id": cohort["family_id"],
            "reference_f1": cohort["reference_f1"], "sample_order_sha256": cohort["sample_order_sha256"],
            "templates": templates}
        contracts[tag] = {"expected_bundles": expected, "expected_family_id": cohort["family_id"],
            "expected_source_batch": cohort["source_batch"], "reference_f1": cohort["reference_f1"],
            "sample_order_sha256": cohort["sample_order_sha256"]}
        require([row["candidate_id"] for row in view["business_measurements"][tag]] == members + c["control_ids"],
                "retain each source's candidate and control measurements")
        numeric = ("slu_f1", "intent", "reliable_completion_rate", "mean_sample_seconds",
                   "non_first_mean_seconds", "first_sample_seconds", "model_calls", "tool_calls")
        for row in view["business_measurements"][tag]:
            cid = row["candidate_id"]
            require(set(row) == {"candidate_id", "bundle_id", "eligible", "is_control", *numeric}
                    and type(row["eligible"]) is bool and type(row["is_control"]) is bool
                    and row["is_control"] == (cid in c["control_ids"])
                    and all(type(row[k]) in (int, float) and math.isfinite(row[k]) and row[k] >= 0 for k in numeric)
                    and all(row[k] <= 1 for k in ("slu_f1", "intent", "reliable_completion_rate")),
                    "only finite allowlisted business measurements permitted")
            if cid not in members:
                continue
            index = members.index(cid)
            summary = cohort["templates"][index]["official_summary"]
            episodes = [g["members"][index] for g in cohort["groups"]]
            seconds = [e["terminal"]["sample_seconds"] for e in episodes]
            require(row["bundle_id"] == expected[cid] and row["slu_f1"] == summary["slu_f1"]
                    and row["intent"] == summary["intent"]
                    and row["model_calls"] == sum(len(e["nodes"]) for e in episodes)
                    and math.isclose(row["reliable_completion_rate"],
                        sum(e["terminal"]["reliable"] for e in episodes) / len(episodes), abs_tol=1e-12)
                    and math.isclose(row["mean_sample_seconds"], math.fsum(seconds)/len(seconds), abs_tol=1e-10)
                    and any(math.isclose(row["first_sample_seconds"], s, abs_tol=1e-10) for s in seconds)
                    and len(seconds) > 1
                    and math.isclose(row["non_first_mean_seconds"],
                        (math.fsum(seconds)-row["first_sample_seconds"])/(len(seconds)-1), abs_tol=1e-10),
                    "measured objectives differ from complete anonymous episodes")
    rebuilt = abstract_partitioned_population_feedback(sources, expected_partitions=contracts, population_config=config)
    require(rebuilt == view["population"], "partitioned feedback or relative returns differ")
    return packet, packet["population_update_plan"], ids


def prepare_partitioned_context_optimizer_input(archive, *, registration_pin, repo_root, data_root):
    """Freshly qualify complete sources and freeze one private learning packet.

    Full source evaluation and cumulative exposure stay private. The resulting
    historical accounting confers no new runtime allowance. All proposal slots
    still require the shared reservation before any actor contact.
    """
    root = Path(repo_root).resolve()
    registration = json.loads(_read_pin(registration_pin, root))
    require(set(registration) == {"schema", "status", "algorithm", "iteration", "projection",
            "source_population", "population_update_plan"}
            and registration["schema"] == "saea-partitioned-context-update-registration-v1"
            and registration["status"] == "ROOT_REGISTERED"
            and registration["algorithm"] == "tf-grpo-context-diversity"
            and type(registration["iteration"]) is int and registration["iteration"] > 0,
            "prospective partitioned TF update registration required")
    pin = registration["source_population"]
    config = load_population_config(pin, repo_root=root)
    ids = _plan(registration["population_update_plan"], config)
    destination = f"context-learning/inputs/partitioned-{registration['population_update_plan']['batch_id']}.json"
    require(not (archive.root / destination).exists(), "partitioned input already prepared")
    projected = project_registered_population(projection_pin=registration["projection"],
        repo_root=root, data_root=data_root, policy_archive=archive)
    joined = read_registered_population_sources(source_registration_pin=projected["private_custody"]["source_join"],
        repo_root=root, data_root=data_root)
    require(joined["projection_config"] == pin, "source projection configuration differs")
    feedback_ids, policies = set(), {}
    for cohort in config["cohorts"]:
        tag = cohort["cohort_id"]
        reference = joined["private_families"][tag][-1]
        require(isinstance(reference.get("sample_ids"), list) and reference["sample_ids"],
                "complete frozen reference exposure required")
        feedback_ids.update(reference["sample_ids"])
        feedback_ids.update(cohort["sample_ids"])
        for cid in cohort["candidate_ids"]:
            bundle = projected["learner_view"]["templates"][tag][cid]["bundle_id"]
            policies[cid] = {"bundle_id": bundle, "policy": archive.load_policy(bundle).as_json()}
    require(list(policies) == ids, "complete policy membership required")
    packet = {"schema": SCHEMA, "algorithm": registration["algorithm"], "iteration": registration["iteration"],
        "registration": registration_pin, "source_population": pin,
        "source_commitment": content_hash(projected["private_custody"]),
        "population_update_plan": registration["population_update_plan"], "policies": policies,
        "feedback_sample_ids": sorted(feedback_ids), "experience": {}, "learner_view": projected["learner_view"],
        "budget": population_accounting(config), "runtime_admission": False,
        "contacts_added": {"model": 0, "scorer": 0}}
    packet["input_sha256"] = content_hash(packet)
    require(json.loads(_read_pin(registration_pin, root)) == registration, "registration changed during preparation")
    raw = _read_pin(pin, root)
    config_path = archive.root / pin["relpath"]
    require(config_path.resolve().is_relative_to(archive.root.resolve()), "config escapes archive")
    if config_path.exists():
        require(config_path.read_bytes() == raw, "archived source config differs")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("xb") as stream:
            stream.write(raw)
    validate_partitioned_packet(archive, packet)
    archive._write(destination, packet)
    return packet


def partitioned_context_actor_view(archive, *, input_sha256):
    """Expose only templates, anonymous structure and measured complete outcomes."""
    from .system_context_learning import _population_update_input
    packet, plan, ids = _population_update_input(archive, input_sha256)
    require(packet["schema"] in (SCHEMA, "saea-partitioned-context-optimizer-input-v2"), "partitioned input required")
    return _partitioned_actor_view(archive, packet, plan, ids)


def _partitioned_actor_view(archive, packet, plan, ids):
    input_sha256 = packet["input_sha256"]
    view = packet["learner_view"]
    result = {"schema": "saea-partitioned-context-actor-view-v1", "optimizer_input_sha256": input_sha256,
        "algorithm": packet["algorithm"], "iteration": packet["iteration"],
        "model": plan["model"], "reasoning_effort": plan["reasoning_effort"],
        "candidate_order": ids, "templates": deepcopy(view["templates"]),
        "representation": deepcopy(view["representation"]), "feedback": deepcopy(view["population"]),
        "business_measurements": deepcopy(view["business_measurements"]),
        "source_budget": deepcopy(packet["budget"]), "runtime_admission": False,
        "instructions": "Propose one original ordered batch of full-node template and supported assembly edits. "
            "Use every source cohort, its own control/A/A, and within-cohort relative returns. Never pool "
            "standardized rewards or frontiers across cohorts. Optimize terminal quality, intent, reliability "
            "and mean/non-first sample latency; retain adverse and no-change evidence. Keep knowledge, sources, "
            "tools, scoring, sampling and runtime authority fixed. Do not request concrete cases or source rosters. "
            "Node correctness and causal credit are unmeasured. This is template-batch context-diversity learning, "
            "not original stochastic GRPO or a GEPA comparison. No proposal establishes positive gain or adoption."}

    if packet["schema"] == "saea-partitioned-context-optimizer-input-v2":
        from .system_context_continuation import continuation_actor_additions
        result.update(continuation_actor_additions(archive, packet))
        result["schema"] = "saea-partitioned-context-actor-view-v2"
        result["instructions"] += (
            " Retain the original active parents. Rejected history remains evidence, never an adopted policy. "
            "Use process statistics to prioritize selective review, safe revision and supported candidate extraction. "
            "Do not optimize alarm frequency or latency in place of official quality and reliability. "
            "Separate raw model effects from deterministic postprocessing; missing observations stay unknown. "
            "Criticism semantic accuracy and causal credit remain unmeasured.")
    if packet["schema"] == "saea-partitioned-context-optimizer-input-v2":
        from .system_context_continuation import continuation_profile
        registration = json.loads(_read_pin(packet["registration"], archive.root))
        if continuation_profile(registration) == "aggregate-template-records-v1":
            from ..analysis.aggregate_template_learning import aggregate_actor_view
            return aggregate_actor_view(result)
    return result
