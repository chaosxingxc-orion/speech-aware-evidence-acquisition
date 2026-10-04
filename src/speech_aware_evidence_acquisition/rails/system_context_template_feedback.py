"""Bounded template-level feedback for prospectively versioned study iterations.

All numeric rows contribute. Semantic cases are sampled without model calls;
complete source pointers and omissions remain in the immutable optimizer input.
This projection grants no READ, contact, runtime, or stage-transition authority.
"""
from __future__ import annotations

from collections import Counter
import math

from .hashing import content_hash
from .system_text_policy import require

SCHEMA = "saea-template-feedback-profile-v1"
CATEGORIES = ("unreliable", "abstained", "above-peer-mean", "below-peer-mean", "same-peer-mean")


def validate_template_profile(profile):
    """Require explicit small semantic budgets and fixed content-stage scope."""
    require(isinstance(profile, dict) and set(profile) == {
        "schema", "phase", "examples_per_template", "selection_seed", "example_sampling",
        "semantic_summaries", "semantic_comparisons"}, "template feedback profile fields differ")
    require(profile["schema"] == SCHEMA and profile["phase"] == "template-only"
            and profile["example_sampling"] == "stratified-stable-hash-v1"
            and profile["semantic_summaries"] is False and profile["semantic_comparisons"] is False
            and type(profile["selection_seed"]) is int
            and type(profile["examples_per_template"]) is int
            and 0 <= profile["examples_per_template"] <= 8,
            "bounded template-only feedback profile required")
    return profile


def template_feedback(packet, profile):
    """Project an already qualified packet; never estimate official F1 from utilities."""
    validate_template_profile(profile)
    groups, candidates = packet["groups"], list(packet["policies"])
    require(groups and len({g["sample_id"] for g in groups}) == len(groups)
            and all(len(g["members"]) == len(candidates)
                    and {m["candidate_id"] for m in g["members"]} == set(candidates) for g in groups),
            "complete template feedback cohort required")
    measurements = {r["candidate_id"]: r for r in packet["business_measurements"]}
    require(set(measurements) == set(candidates), "complete template measurements required")
    buckets = {c: [] for c in candidates}
    for group in groups:
        values = [m["utility"] for m in group["members"]]
        require(all(type(v) in (int, float) and math.isfinite(v) for v in values),
                "finite complete utilities required")
        mean = math.fsum(values) / len(values)
        for row in group["members"]:
            execution = row["execution"]
            delta = row["utility"] - mean
            category = ("unreliable" if not execution["reliable_completion"] else
                        "abstained" if execution["abstained"] else
                        "above-peer-mean" if delta > 0 else
                        "below-peer-mean" if delta < 0 else "same-peer-mean")
            buckets[row["candidate_id"]].append({"sample_id": group["sample_id"], **row,
                "category": category, "peer_centered_utility": delta})
    templates = []
    for cid, rows in buckets.items():
        def order(row):
            return content_hash({"seed": profile["selection_seed"], "iteration": packet["iteration"],
                                 "candidate": cid, "sample": row["sample_id"]})
        queues = {category: sorted((r for r in rows if r["category"] == category), key=order)
                  for category in CATEGORIES}
        selected = []
        # Round-robin strata, with a stable rotated category order when the
        # number of populated categories exceeds the case budget.
        categories = sorted(CATEGORIES, key=lambda c: content_hash({
            "seed": profile["selection_seed"], "iteration": packet["iteration"], "category": c}))
        while len(selected) < min(len(rows), profile["examples_per_template"]):
            for category in categories:
                if queues[category] and len(selected) < profile["examples_per_template"]:
                    selected.append(queues[category].pop(0))
        used = {r["sample_id"] for r in selected}
        first = packet["official_summaries"][cid]["sample_timing"]["first_admitted_sample"]
        templates.append({"candidate_id": cid, "bundle_id": packet["policies"][cid]["bundle_id"],
            "rows": len(rows), "utility_sum": math.fsum(r["utility"] for r in rows),
            "utility_mean": math.fsum(r["utility"] for r in rows) / len(rows),
            "peer_centered_utility_sum": math.fsum(r["peer_centered_utility"] for r in rows),
            "category_counts": dict(Counter(r["category"] for r in rows)),
            "selected_category_counts": dict(Counter(r["category"] for r in selected)),
            "measurements": measurements[cid],
            "first_sample_seconds": first["elapsed_seconds"],
            "examples": selected,
            "unsampled_sample_ids": [r["sample_id"] for r in rows if r["sample_id"] not in used]})
    n = len(groups) * len(candidates)
    return {"schema": "saea-template-feedback-v1", "profile": profile,
        "family_id": packet["family_id"], "family_commitment": packet["family_commitment"],
        "numeric_source_sha256": content_hash(groups), "rows_scored": n, "templates": templates,
        "omissions": {"numeric_rows_omitted": 0, "unsampled_trajectories":
            n - sum(len(t["examples"]) for t in templates),
            "reason": "Semantic evidence is bounded; every numeric row remains scored and source-addressable."},
        "interpretation": "Peer-centered utility is descriptive, not a causal node contribution or policy gradient. Official quality remains separate; no promise of positive gain.",
        "runtime_admission": False, "semantic_model_calls": 0}


def _policy_view(policy):
    """Expose only the template edit surface; retain full provenance in the archive."""
    return {"schema": "saea-template-policy-view-v1", "source_policy_sha256": content_hash(policy),
            **{key: policy[key] for key in ("role_text", "context_layout", "node_context")}}


def proposer_view(packet):
    """Keep complete editable templates and statistics, not per-input record trees."""
    if "template_feedback" not in packet:
        return packet
    feedback = packet["template_feedback"]
    feedback = {**feedback, "templates": [{k: v for k, v in row.items() if k != "unsampled_sample_ids"}
                                         for row in feedback["templates"]]}
    policies = {c: {**p, "policy": _policy_view(p["policy"])} for c, p in packet["policies"].items()}
    keys = ("algorithm", "iteration", "family_id", "recipe", "protocol", "read_authority",
            "sampling", "measurement_profile", "family_commitment", "budget",
            "feedback_profile", "reflection_task", "experience", "runtime_admission", "rejected_trial_feedback")
    return {"schema": "saea-template-proposer-view-v1", "source_input_sha256": packet["input_sha256"],
            **{k: packet[k] for k in keys if k in packet}, "policies": policies, "template_feedback": feedback}
