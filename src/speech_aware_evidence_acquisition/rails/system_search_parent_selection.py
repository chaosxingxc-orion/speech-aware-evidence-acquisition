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
