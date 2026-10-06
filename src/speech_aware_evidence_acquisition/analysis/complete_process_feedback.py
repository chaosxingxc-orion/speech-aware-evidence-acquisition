"""Join complete source-bound process reports before abstract feedback preparation.

The caller must requalify all registered sources and verify their root READ and
file hashes first. This pure adapter grants no READ, actor or runtime authority.
"""
from .abstract_process_feedback import project_process_feedback
from ..rails.system_text_policy import require


def join_complete_process_feedback(*, config, reports, qualifications, read_ids, score_bindings):
    """Preserve separate cohorts, all controls and unchanged statistical definitions."""
    cohorts = config["cohorts"]
    tags = [c["cohort_id"] for c in cohorts]
    require(tags and len(tags) == len(set(tags))
            and set(tags) == set(reports) == set(qualifications) == set(read_ids)
            == set(score_bindings), "every configured complete process cohort required")
    families = {}
    for cohort in cohorts:
        tag = cohort["cohort_id"]
        report, qualified = reports[tag], qualifications[tag]
        expected = cohort["candidate_ids"] + cohort["control_ids"]
        members = qualified["members"]
        require(report.get("schema") == "saea-complete-cohort-process-metrics-v1"
                and report["cohort"] == tag
                and report["read_id"] == qualified["read_id"] == read_ids[tag]
                and qualified["status"] == "ALL_MEMBERS_OPERATIONALLY_QUALIFIED",
                "exact qualified cohort and root READ required")
        require(report["contacts_added"] == {"model": 0, "official_scorer": 0}
                and report["learner_exported"] is False and report["runtime_changed"] is False,
                "root-only offline diagnostics required")
        require(len(members) == len(expected) == len(set(expected))
                and {m["member"] for m in members} == set(expected) == set(report["members"]),
                "all unique candidates and comparators required")
        for member in members:
            require(member["state"] == "FINALIZED" and member["verified_seal"] is True
                    and member["official_successful_jobs"] == 1 and member["failed_jobs"] == 0
                    and member["rows"] == len(cohort["sample_ids"]),
                    "every process source needs complete seal and unique successful score")
            source = report["members"][member["member"]]["source"]
            require(source["run_id"] == member["run_id"]
                    and source["attempt_id"] == member["attempt_id"],
                    "process source run or attempt differs from qualification")
        families[tag] = report["members"]
    # This existing projection checks exact input IDs, official-score identity,
    # arithmetic, missingness and delivery-stage links, then removes private data.
    return project_process_feedback({"families": families}, config=config, bindings=score_bindings)
