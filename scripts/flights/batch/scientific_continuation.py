"""Plan a bounded unstarted suffix after a failed outer owner; never dispatch.

Callers must bind the supplied observations to native process identities and pinned
operational files. This pure check grants neither runtime admission nor scientific
READ. It does not replace complete-family seal and official-score verification.
"""
from datetime import datetime


def require(condition, message):
    if not condition:
        raise ValueError(message)


def moment(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "An explicit observation timezone is required")
    return result


def plan_unstarted_continuation(*, registration, observation, members, now,
                               max_age_seconds):
    """Preserve a completed prefix and identify only an entirely untouched suffix."""
    configured = registration["members"]
    labels = [item["label"] for item in configured]
    require(labels and len(set(labels)) == len(labels)
            and set(members) == set(labels), "Configured member set differs")
    for key in ("run_id", "attempt_id"):
        require(len({item[key] for item in configured}) == len(labels),
                "Configured execution identities are duplicated")
    require(observation["task_state"] == "Ready"
            and type(observation["task_result"]) is int
            and observation["task_result"] not in (0, 267009),
            "The original outer owner is not a terminal failed task")
    require(observation["original_owner_live"] is False
            and observation["bound_windows_processes"] == []
            and observation["bound_wsl_processes"] == [],
            "Original processes have not settled")
    require(observation["stop_present"] is False
            and observation["flight_lock_present"] is False,
            "Existing controls require separate disposition")
    age = (moment(now) - moment(observation["observed_at"])).total_seconds()
    require(max_age_seconds > 0 and 0 <= age <= max_age_seconds,
            "Native observation is stale or future dated")
    preserved, unstarted = [], []
    for expected in configured:
        label = expected["label"]
        member = members[label]
        require(all(member[key] == expected[key]
                    for key in ("label", "run_id", "attempt_id")),
                "Member execution identity differs")
        require(member["failure_present"] is False,
                "Member failure requires its own disposition")
        require(all(type(member[key]) is int for key in
                    ("successful_scores", "prepared_scores", "failed_scores")),
                "Score counts must be integers")
        require(all(member[key] is None or type(member[key]) is int for key in
                    ("finished_exit", "campaign_exit", "inspection_exit")),
                "Exit evidence must be an integer or absent")
        if member["attempt_present"] is True:
            require(not unstarted, "Completed members do not form the original prefix")
            require(member["run_present"] is True and member["unit_present"] is True
                    and member["started"] is True
                    and member["attempt_state"] == "FINALIZED",
                    "Original member is not finalized")
            require(all(member[key] == 0 for key in
                        ("finished_exit", "campaign_exit", "inspection_exit")),
                    "Original member lacks successful terminal evidence")
            require(member["successful_scores"] == member["prepared_scores"] == 1
                    and member["failed_scores"] == 0,
                    "Original member lacks one unique successful score")
            preserved.append(label)
        else:
            require(member["attempt_present"] is False
                    and member["run_present"] is False
                    and member["unit_present"] is False
                    and member["started"] is False,
                    "Unstarted member already has execution artifacts")
            require(all(member[key] is None for key in
                        ("attempt_state", "finished_exit", "campaign_exit", "inspection_exit"))
                    and all(member[key] == 0 for key in
                            ("successful_scores", "prepared_scores", "failed_scores")),
                    "Unstarted member has attempt or scoring evidence")
            unstarted.append(label)
    require(preserved and unstarted, "Continuation requires both preserved and unstarted members")
    return {"schema": "saea-unstarted-scientific-continuation-partition-v1",
            "preserved_members": preserved, "unstarted_members": unstarted,
            "original_task_result": observation["task_result"],
            "dispatch_authorized": False, "read_authorized": False,
            "model_contacts_added": 0, "scorer_contacts_added": 0}
