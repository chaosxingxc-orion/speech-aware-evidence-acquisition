"""Adapt complete cohort diagnostics to the existing registered continuation input.

Callers must verify the pinned registration, trial qualification, complete source
families and exact root READ before supplying private reports. This pure adapter
reuses the full numeric validator and grants no READ, actor or runtime authority.
"""
from copy import deepcopy
from .complete_process_feedback import join_complete_process_feedback
from ..rails.system_text_policy import require, sha


def build_continuation_process_backfill(*, config, reports, qualifications, read_ids,
                                       process_registration, registration_sha256,
                                       trial_qualification):
    """Retain all private rows while exposing numbers only through the shared learner."""
    sha(registration_sha256)
    reg, trial = process_registration, trial_qualification
    tags = [c["cohort_id"] for c in config["cohorts"]]
    require(reg.get("schema") == "saea-slurp-process-backfill-v1"
            and reg.get("status") == "ROOT_REGISTERED"
            and [c["cohort_id"] for c in reg["cohorts"]] == tags,
            "exact registered complete process bridge required")
    require(trial.get("schema") == "saea-partitioned-context-qualified-trial-v1"
            and trial["trial_sources"] == reg["source_registration"]
            and set(trial["cohorts"]) == set(tags)
            and trial["candidate_trajectories"] == sum(
                len(c["candidate_ids"])*len(c["sample_ids"]) for c in config["cohorts"])
            and trial["root_review_required"] is True
            and trial["formal_adoption"] is False and trial["runtime_admission"] is False
            and trial["contacts_added"] == {"model":0,"scorer":0},
            "same complete qualified trial required before continuation preparation")
    bindings = {}
    for cohort, registered in zip(config["cohorts"], reg["cohorts"], strict=True):
        members = registered["members"]
        expected = cohort["candidate_ids"] + cohort["control_ids"]
        require(len(members) == len(expected)
                and {m["member_id"] for m in members} == set(expected),
                "each candidate and comparator must occur exactly once")
        bindings[cohort["cohort_id"]] = {m["member_id"]:m for m in members}
    join_complete_process_feedback(config=config, reports=reports,
        qualifications=qualifications, read_ids=read_ids, score_bindings=bindings)
    return {"schema":"saea-complete-slurp-process-backfill-v1",
            "registration_sha256":registration_sha256,
            "families":deepcopy({tag:reports[tag]["members"] for tag in tags}),
            "contacts_added":{"model":0,"official_scorer":0},
            "learner_exported":False,"runtime_admission":False}
