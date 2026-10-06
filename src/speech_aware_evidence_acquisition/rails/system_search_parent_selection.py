"""Prospective bounded search parents, separate from adoption and contact authority.

Reuse qualified-feedback measurement rows and the existing create-only archive.
The caller must qualify source custody before use. This pure planner does not
qualify feedback, allocate proposals, alter active runtime policies or export to
an actor. Current registered algorithms do not call this experimental interface.
"""
from __future__ import annotations

import copy

from .hashing import content_hash
from .system_search_measurement import measured_frontier
from .system_text_policy import require, sha

SCHEMA = "saea-search-parent-selection-config-v1"
CONFIG_KEYS = {"schema", "frontier_capacity", "exploration_capacity",
               "selection_seed", "iteration"}


def _configuration(config):
    require(isinstance(config, dict) and set(config) == CONFIG_KEYS,
            "parent selection configuration fields differ")
    require(config["schema"] == SCHEMA, "unknown parent selection algorithm")
    for key in CONFIG_KEYS - {"schema"}:
        require(type(config[key]) is int and config[key] >= 0,
                "parent capacities, seed and iteration require nonnegative integers")
    require(config["frontier_capacity"] > 0 and config["iteration"] > 0,
            "positive frontier capacity and iteration are required")


def select_search_parents(rows, *, profile, selection_config, usage_counts):
    """Select a bounded point-estimate search set without scientific promotion.

    Always retain one quality-first frontier anchor. Rotate additional frontier
    parents by least prior use with a configured reproducible hash tie break.
    Reserve the separate exploration capacity for eligible dominated policies,
    then unused frontier members. Lower-quality exploration never replaces the
    formal incumbent. Preserve the full frontier and every exclusion reason.
    Neither this heuristic nor its tie break proves behavioral novelty or escape
    from local optima. Capacity is not a proposer allowance.
    """
    _configuration(selection_config)
    require(isinstance(rows, (list, tuple)) and bool(rows), "measured parent rows required")
    fields = {"candidate_id", "bundle_id", "cohort_id", "measurement_id",
              "measurement_profile_sha256", "slu_f1", "intent",
              "reliable_completion_rate", "mean_sample_seconds",
              "non_first_mean_seconds", "eligible"}
    for row in rows:
        require(isinstance(row, dict) and fields <= set(row)
                and set(row) <= fields | {"model_calls", "tool_calls", "timing_report_sha256"},
                "measured parent row fields differ; raw content is not an input")
        require(isinstance(row["candidate_id"], str) and bool(row["candidate_id"]),
                "explicit candidate identity required")
        for key in ("bundle_id", "cohort_id", "measurement_id", "measurement_profile_sha256"):
            sha(row[key])
    require(len({r["candidate_id"] for r in rows}) == len(rows), "duplicate candidate identity")
    frontier = measured_frontier(rows, profile=profile)
    require(bool(frontier), "no eligible measured parent")
    ids = {r["bundle_id"] for r in rows}
    require(isinstance(usage_counts, dict) and set(usage_counts) == ids,
            "usage counts must bind every measured policy exactly")
    require(all(type(v) is int and v >= 0 for v in usage_counts.values()),
            "usage counts require nonnegative integers")
    ordered = sorted(copy.deepcopy(rows), key=lambda r: r["bundle_id"])
    config = copy.deepcopy(selection_config)
    frontier_ids = {r["bundle_id"] for r in frontier}
    eligible = [r for r in ordered if r["eligible"] and r["reliable_completion_rate"]
                >= profile["minimum_reliable_completion_rate"]]
    eligible_ids = {r["bundle_id"] for r in eligible}

    def tie(bundle):
        return content_hash({"seed": config["selection_seed"],
                             "iteration": config["iteration"], "bundle_id": bundle})

    def rotated(row):
        bundle = row["bundle_id"]
        return usage_counts[bundle], tie(bundle)

    anchor = min(frontier, key=lambda r: (-r["slu_f1"], -r["intent"],
        -r["reliable_completion_rate"], r["mean_sample_seconds"],
        r["non_first_mean_seconds"], tie(r["bundle_id"])))
    selected = [anchor["bundle_id"]]
    remaining = sorted((r for r in frontier if r["bundle_id"] not in selected), key=rotated)
    selected.extend(r["bundle_id"] for r in remaining[:config["frontier_capacity"] - 1])
    exploration = sorted((r for r in eligible if r["bundle_id"] not in selected),
                         key=lambda r: (r["bundle_id"] in frontier_ids, *rotated(r)))
    explored = [r["bundle_id"] for r in exploration[:config["exploration_capacity"]]]
    dispositions = {}
    for bundle in sorted(ids):
        if bundle not in eligible_ids:
            reason = "ineligible"
        elif bundle in selected:
            reason = "frontier-parent"
        elif bundle in explored:
            reason = "exploration-parent"
        elif bundle in frontier_ids:
            reason = "frontier-capacity"
        else:
            reason = "dominated-not-explored"
        dispositions[bundle] = reason
    result = {"schema": "saea-search-parent-selection-v1",
        "configuration": config, "configuration_sha256": content_hash(config),
        "input_sha256": content_hash({"rows": ordered, "profile": profile,
                                      "usage_counts": usage_counts}),
        "measurement_id": ordered[0]["measurement_id"],
        "cohort_id": ordered[0]["cohort_id"],
        "frontier_ids": sorted(frontier_ids), "frontier_parent_ids": selected,
        "exploration_parent_ids": explored, "dispositions": dispositions,
        "usage_counts_after": {k: usage_counts[k] + int(k in selected or k in explored)
                               for k in sorted(ids)},
        "unfilled_capacity": {"frontier": config["frontier_capacity"] - len(selected),
                              "exploration": config["exploration_capacity"] - len(explored)},
        "history_deleted": False, "formal_adoption": False, "runtime_admission": False,
        "learner_exported": False, "proposal_allocation_granted": False,
        "scope": "Prospective point-estimate search planning; source qualification and exact admission remain external."}
    result["selection_sha256"] = content_hash(result)
    return result


def record_parent_selection(archive, *, rows, profile, selection_config,
                            usage_counts, source_feedback_sha256):
    """Save an immutable search decision in the shared archive without activation."""
    from .system_search_archive import SystemSearchArchive
    require(isinstance(archive, SystemSearchArchive), "shared SystemSearchArchive required")
    sha(source_feedback_sha256)
    result = select_search_parents(rows, profile=profile, selection_config=selection_config,
                                   usage_counts=usage_counts)
    archive._write(f"context-learning/parent-selection/iteration-{selection_config['iteration']}.json",
        {"schema": "saea-search-parent-selection-record-v1",
         "source_feedback_sha256": source_feedback_sha256,
         "inputs": {"rows": rows, "profile": profile, "usage_counts": usage_counts},
         "selection": result})
    return result



def plan_parent_proposals(configuration, *, selection):
    """Map every configured candidate to parents without reserving a proposal.

    This prospective envelope embeds the complete existing population config.
    A later registered lifecycle must carry its exact file pin through all stages.
    Source qualification, proposer isolation and spent-slot enforcement remain
    prerequisites at the existing reservation boundary. Never use this planner
    as a substitute for them. No hidden fallback or replacement slot is created.
    """
    from .experiment_population import validate_population_config, population_accounting

    require(isinstance(configuration, dict) and set(configuration) == {
        "schema", "experiment_population", "parent_selection_sha256", "modes"}
        and configuration["schema"] == "saea-parent-proposal-plan-config-v1",
        "proposal planning configuration fields differ")
    population = validate_population_config(configuration["experiment_population"])
    require(isinstance(selection, dict)
        and selection.get("schema") == "saea-search-parent-selection-v1"
        and selection.get("selection_sha256") == content_hash({
            k: v for k, v in selection.items() if k != "selection_sha256"})
        and configuration["parent_selection_sha256"] == selection["selection_sha256"],
        "parent selection identity differs")
    candidates = [cid for cohort in population["cohorts"] for cid in cohort["candidate_ids"]]
    modes = configuration["modes"]
    require(isinstance(modes, dict) and set(modes) == set(candidates)
            and all(isinstance(v, str) and v in {"local", "recombine", "explore"}
                    for v in modes.values()), "every configured proposal needs one supported mode")
    require("explore" in modes.values(), "this exploration protocol requires a reserved exploration slot")
    frontier, exploration = selection["frontier_parent_ids"], selection["exploration_parent_ids"]
    require(isinstance(frontier, list) and isinstance(exploration, list)
            and len(set(frontier + exploration)) == len(frontier + exploration),
            "selected parent pools must be disjoint and unique")
    for pool, disposition in ((frontier, "frontier-parent"), (exploration, "exploration-parent")):
        require(all(selection["dispositions"].get(p) == disposition for p in pool),
                "selected parent disposition differs")
        for parent in pool:
            sha(parent)
    require(frontier and exploration and ("recombine" not in modes.values() or len(frontier) >= 2),
            "configured proposal mode lacks selected parents; no silent fallback")
    counters = dict.fromkeys(("local", "recombine", "explore"), 0)
    slots = []
    for cohort in population["cohorts"]:
        for candidate in cohort["candidate_ids"]:
            mode = modes[candidate]; index = counters[mode]
            pool = exploration if mode == "explore" else frontier
            parents = [pool[index % len(pool)]]
            if mode == "recombine":
                parents.append(pool[(index + 1) % len(pool)])
            counters[mode] += 1
            slots.append({"cohort_id": cohort["cohort_id"], "candidate_id": candidate,
                          "mode": mode, "parent_bundle_ids": parents})
    result = {"schema": "saea-parent-proposal-plan-v1",
        "configuration_sha256": content_hash(configuration),
        "experiment_population_sha256": content_hash(population),
        "parent_selection_sha256": selection["selection_sha256"],
        "slots": slots, "mode_counts": counters,
        "population_budget": population_accounting(population),
        "proposal_allocation_granted": False, "runtime_admission": False,
        "learner_exported": False,
        "scope": "Prospective planning only; registered source custody and reservation remain required."}
    result["plan_sha256"] = content_hash(result)
    return result



def _qualified_parent_selection(archive, *, request_pin, repo_root, data_root):
    """Requalify an entire population before private, cohort-local parent planning.

    Preserve every replicate; the declared first control then candidate order
    fixes each policy's representative before seeing scores. This root artifact
    neither exports learner input nor rewrites an earlier trial acceptance rule.
    """
    import json
    from pathlib import Path
    from ..analysis.abstract_population_sources import read_registered_population_sources
    from .experiment_population import load_population_config
    from .system_context_partitioned_trial import _source_identity
    from .system_search_archive import SystemSearchArchive
    from .system_search_measurement import measured_rows
    from .system_text_policy import _read_pin

    require(isinstance(archive, SystemSearchArchive), "shared SystemSearchArchive required")
    root = Path(repo_root).resolve()
    request = json.loads(_read_pin(request_pin, root))
    require(set(request) == {"schema", "status", "source_registration", "cohort_id",
                            "selection_config", "usage_counts", "replicate_rule"}
            and request["schema"] == "saea-qualified-parent-selection-request-v1"
            and request["status"] == "ROOT_REGISTERED"
            and request["replicate_rule"] == "designated-control-then-registered-order",
            "exact registered root selection request required")
    _configuration(request["selection_config"])
    manifest = json.loads(_read_pin(request["source_registration"], root))
    population = load_population_config(manifest["projection_config"], repo_root=root)
    require(request["cohort_id"] in [c["cohort_id"] for c in population["cohorts"]],
            "selected cohort is outside the complete registered population")
    options = dict(source_registration_pin=request["source_registration"],
                   repo_root=root, data_root=data_root)
    source = read_registered_population_sources(**options)
    doc, _, registration, protocol, candidates, controls, _ = source["private_families"][request["cohort_id"]]
    profile = protocol["measurement_profile"]
    all_rows = measured_rows(doc, [controls[0], *candidates, *controls[1:]],
                             registration["member_bindings"], profile=profile)
    # Equal input rosters and serving sessions do not identify one evaluation batch.
    domain = {"timing_measurement_id": all_rows[0]["measurement_id"],
              "source_registration": request["source_registration"],
              "cohort_id": request["cohort_id"]}
    for row in all_rows:
        row["measurement_id"] = content_hash(domain)
    measurements, repeats, seen = [], [], set()
    for row in all_rows:
        (repeats if row["bundle_id"] in seen else measurements).append(row)
        seen.add(row["bundle_id"])
    result = select_search_parents(measurements, profile=profile,
        selection_config=request["selection_config"], usage_counts=request["usage_counts"])
    fresh = read_registered_population_sources(**options)
    require(_source_identity(source) == _source_identity(fresh),
            "complete population source changed during parent selection")
    require(json.loads(_read_pin(request_pin, root)) == request,
            "selection request changed during preparation")
    record = {"schema": "saea-qualified-parent-selection-record-v2",
        "measurement_domain": domain, "request": request_pin, "source_registration": request["source_registration"],
        "source_identity_sha256": content_hash(_source_identity(source)),
        "projection_config": source["projection_config"], "cohort_id": request["cohort_id"],
        "replicate_rule": request["replicate_rule"], "control_ids": controls,
        "measurements": measurements, "duplicate_bundle_replicates": repeats,
        "selection": result, "learner_exported": False, "runtime_admission": False,
        "formal_adoption": False, "proposal_allocation_granted": False,
        "scope": "Qualified private root planning only; no historical acceptance change or actor input."}
    # The declared A/A remains a replicate even when it has the best observed score.
    record["record_sha256"] = content_hash(record)
    return record


def prepare_qualified_parent_selection(archive, *, request_pin, repo_root, data_root):
    """Persist one fully qualified parent decision without contact authority."""
    record = _qualified_parent_selection(archive, request_pin=request_pin,
        repo_root=repo_root, data_root=data_root)
    archive._write("context-learning/qualified-parent-selection/"
        + f"{record['selection']['configuration']['iteration']}-{content_hash(record['cohort_id'])}.json", record)
    return record


def prepare_qualified_parent_proposal_plan(archive, *, configuration_pin, repo_root, data_root):
    """Bind the immutable experiment config to freshly requalified selected parents.

    This root planning artifact grants no proposal reservation or actor access.
    Preserve the existing reservation and exact algorithm registration boundaries.
    A copied self-hashed selection cannot bypass original complete-family sources.
    """
    import json
    from pathlib import Path
    from ..analysis.abstract_population_sources import _external
    from .experiment_population import load_population_config
    from .system_search_archive import SystemSearchArchive
    from .system_text_policy import _read_pin

    require(isinstance(archive, SystemSearchArchive), "shared SystemSearchArchive required")
    root, data = Path(repo_root).resolve(), Path(data_root).resolve()
    configuration = json.loads(_read_pin(configuration_pin, root))
    require(set(configuration) == {"schema", "status", "experiment_population", "selection_record", "modes"}
        and configuration["schema"] == "saea-qualified-parent-proposal-config-v1"
        and configuration["status"] == "ROOT_REGISTERED",
        "exact registered qualified proposal configuration required")
    population = load_population_config(configuration["experiment_population"], repo_root=root)
    saved = _external(configuration["selection_record"], data)
    require(saved.get("schema") == "saea-qualified-parent-selection-record-v2"
        and saved.get("record_sha256") == content_hash({k: v for k, v in saved.items() if k != "record_sha256"}),
        "qualified parent selection record identity differs")
    expected_path = archive.root / "context-learning/qualified-parent-selection" / (
        f"{saved['selection']['configuration']['iteration']}-{content_hash(saved['cohort_id'])}.json")
    require(Path(configuration["selection_record"]["path"]).resolve() == expected_path.resolve(),
        "selection must come from the declared shared archive")
    fresh = _qualified_parent_selection(archive, request_pin=saved["request"],
        repo_root=root, data_root=data)
    require(saved == fresh, "parent record differs from requalified complete source")
    plan = plan_parent_proposals({"schema": "saea-parent-proposal-plan-config-v1",
        "experiment_population": population, "parent_selection_sha256": saved["selection"]["selection_sha256"],
        "modes": configuration["modes"]}, selection=fresh["selection"])
    require(json.loads(_read_pin(configuration_pin, root)) == configuration
        and load_population_config(configuration["experiment_population"], repo_root=root) == population
        and _external(configuration["selection_record"], data) == saved,
        "qualified proposal inputs changed during planning")
    require(_qualified_parent_selection(archive, request_pin=saved["request"],
        repo_root=root, data_root=data) == saved,
        "parent authority or complete source changed during planning")
    result = {"schema": "saea-qualified-parent-proposal-plan-v1",
        "configuration": configuration_pin, "experiment_population": configuration["experiment_population"],
        "selection_record": configuration["selection_record"],
        "source_identity_sha256": saved["source_identity_sha256"], "plan": plan,
        "proposal_allocation_granted": False, "learner_exported": False, "runtime_admission": False,
        "scope": "Source-qualified root planning only; exact algorithm and reservation admission remain required."}
    result["record_sha256"] = content_hash(result)
    archive._write("context-learning/qualified-parent-proposals/" + content_hash(configuration_pin) + ".json", result)
    return result
