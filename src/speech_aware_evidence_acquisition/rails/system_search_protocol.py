"""Prospective allocation for the owner's bounded system-text search sequence."""
import hashlib
from .hashing import content_hash
from .system_text_policy import require


def stage_for(protocol, name):
    stages = [stage for stage in protocol["stages"] if stage["stage"] == name]
    require(len(stages) == 1, "stage is missing or duplicated in the frozen protocol")
    return stages[0]


def require_stage_feedback(protocol, name, feedback):
    stage = stage_for(protocol, name)
    d = feedback.as_json()
    require(d.get("schema") != "saea-exploratory-system-feedback-v1",
            "exploratory learning feedback is not a formal registered-stage result")
    require(d.get("schema") != "saea-complete-system-pilot-evidence-v1",
            "pilot evidence is not optimizer feedback")
    require([g["sample_id"] for g in d["feedback"]["groups"]] == stage["sample_ids"],
            "feedback does not use the exact preceding registered cohort")
    expected = set(stage["member_slots"])
    registration = d.get("read_authority", {}).get("stage_registration")
    if registration is not None:
        from .system_search_stage import validate_stage_registration
        validate_stage_registration(registration, protocol=protocol)
        require(registration["stage"] == name, "feedback stage registration differs")
        expected = set(registration["expected_members"])
    require(set(d["summaries"]) == expected,
            "feedback does not contain the registered complete preceding family")


def stable_slice(sample_ids, start, count, *, seed=20261001):
    require(type(start) is int and start >= 0 and type(count) is int and count > 0
            and len(set(sample_ids)) == len(sample_ids) and start + count <= len(sample_ids),
            "invalid or undersized registered roster")
    return sorted(sample_ids, key=lambda s: (hashlib.sha256(f"{seed}:{s}".encode()).hexdigest(), s))[start:start+count]


def build_protocol(rosters):
    require(set(rosters) == {"r01c", "fold_a", "fold_b", "dev"}, "registered roster sources differ")
    observed = set()
    for key, expected in (("r01c", 625), ("fold_a", 1080), ("fold_b", 1080), ("dev", 1000)):
        ids = rosters[key]
        require(len(ids) == expected and len(set(ids)) == expected, "source roster size differs")
        prefix = "slurp:devel:" if key == "dev" else "slurp:train:"
        require(all(s.startswith(prefix) for s in ids), "source partition differs")
        utterances = {":".join(s.split(":")[:3]) for s in ids}
        require(not observed.intersection(utterances), "source rosters overlap at utterance level")
        observed.update(utterances)
    stage_specs = [("initial", "r01c", 0, 400, ["seed", "seed-aa"])]
    search_members = [f"{b}-{m}" for b in ("L", "B") for m in ("parent", "parent-aa", "candidate-1", "candidate-2")]
    stage_specs.extend((f"update-{r}", cohort, offset, 400, search_members)
                       for r, cohort, offset in ((1, "fold_a", 0), (2, "fold_a", 400), (3, "fold_b", 0)))
    stage_specs.extend([
        ("selection", "fold_b", 400, 400, ["seed", "seed-aa", "L-1", "L-2", "B-1", "B-2"]),
        ("dev", "dev", 0, 1000, ["seed", "seed-aa", "L-frozen", "B-frozen"]),
    ])
    stages = []
    for stage, source, offset, count, members in stage_specs:
        # DEV preserves the existing registered order rather than drawing another view.
        ids = list(rosters[source]) if source == "dev" else stable_slice(rosters[source], offset, count)
        stages.append({"stage": stage, "source_roster": source, "sample_ids": ids,
                       "roster_sha256": content_hash(ids), "member_slots": members,
                       "trajectory_cap": count * len(members), "official_score_jobs_cap": len(members),
                       "full_family_read_required": True, "status": "registration-pending-runtime-admission"})
    return {"schema": "saea-system-text-search-protocol-v1", "seed": 20261001,
            "stages": stages, "trajectory_cap": sum(s["trajectory_cap"] for s in stages),
            "candidate_opportunities": 12, "updates": 3, "active_candidates_per_branch": 2,
            "proposer_family": "GPT6", "proposer_exact_version": None,
            "proposal_input_token_cap": 32768, "proposal_output_token_cap": 4096,
            "primary_comparison": "L-frozen minus B-frozen", "secondary_comparison": "L-frozen minus seed",
            "model_call_cap_per_system_trajectory": 13, "tool_call_cap_per_system_trajectory": 1,
            "separately_registered": ["FIT", "engineering-four-row-proof", "knowledge-construction", "proposal"],
            "read_boundary": "All registered members of a stage must finalize and have one official score; no partial read.",
            "claim_scope": "One historically exposed search sequence, not three independent replications or general recursive improvement.",
            "no_automatic_extra_sampling": True, "no_runtime_authority": True}
