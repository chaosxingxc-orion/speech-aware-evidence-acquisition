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



def qualify_continued_terminal(*, registration, settlement, plan, current_members,
                               original_windows, suffix_terminal,
                               actual_missing_native_exit_members, now,
                               max_age_seconds):
    """Join an unchanged completed prefix to a separately verified suffix terminal.

    The caller must verify pinned evidence, the suffix's native terminal through
    the standard verifier, and the complete original family's seals and scores.
    Missing native exits remain explicit exceptions; they are never synthesized.
    """
    require(plan["status"] == "ROOT-ADMITTED" and plan["authority"] == "owner227",
            "A separately admitted root continuation is required")
    prior = plan_unstarted_continuation(
        registration=registration, observation=settlement["observation"],
        members=settlement["members"], now=settlement["at_utc"],
        max_age_seconds=max_age_seconds)
    require(prior == settlement["result"], "Settlement partition changed")
    for key in ("preserved_members", "unstarted_members", "original_task_result"):
        require(plan[key] == prior[key], "Continuation scope changed")
    preserved, suffix = prior["preserved_members"], prior["unstarted_members"]
    require(set(current_members) == {m["label"] for m in registration["members"]},
            "Current member set differs")
    require(all(current_members[label] == settlement["members"][label]
                for label in preserved), "Preserved member evidence changed")
    missing = plan["missing_native_exit_members"]
    require(len(missing) == len(set(missing)) and set(missing) <= set(preserved)
            and missing == actual_missing_native_exit_members,
            "Missing native exits differ from the exact disposition")
    require(original_windows["task_state"] == "Ready"
            and original_windows["task_result"] == prior["original_task_result"]
            and original_windows["original_owner_live"] is False
            and original_windows["bound_windows_processes"] == []
            and original_windows["bound_wsl_processes"] == [],
            "Original failed epoch is not preserved and settled")
    age = (moment(now) - moment(original_windows["observed_at"])).total_seconds()
    require(0 <= age <= max_age_seconds, "Original terminal observation is stale")
    require(suffix_terminal["status"] == "EXACT_SCIENTIFIC_JOB_TERMINAL"
            and suffix_terminal["member_count"] == len(suffix),
            "Suffix lacks exact native terminal qualification")
    require(moment(settlement["at_utc"]) <= moment(suffix_terminal["launch_epoch"])
            <= moment(suffix_terminal["terminal_epoch"]) <= moment(now),
            "Execution epochs overlap or are out of order")
    return {"status": "CONTINUED_SCIENTIFIC_OWNER_CHAIN_VERIFIED",
            "member_count": len(preserved) + len(suffix),
            "preserved_members": preserved, "continued_members": suffix,
            "original_task_result": prior["original_task_result"],
            "missing_original_native_exits": missing,
            "suffix_terminal": suffix_terminal, "read_authorized": False}



def observe_members(*, registration, data_root, job_root):
    """Read operational metadata only and bind every observed byte hash."""
    from pathlib import Path
    import hashlib
    import json
    import re
    data_root, job_root = Path(data_root), Path(job_root)
    pins, members = [], {}
    def read(path):
        raw = path.read_bytes()
        pins.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
        return json.loads(raw)
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    for member in registration["members"]:
        for key in ("label", "run_id", "attempt_id"):
            require(re.fullmatch(r"[A-Za-z0-9_-]+", member[key]) is not None,
                    "Unsafe registered execution identity")
        label = member["label"]
        unit = job_root / label
        attempt_path = data_root / "attempts" / member["run_id"] / (member["attempt_id"] + ".json")
        run = data_root / "runs" / member["run_id"] / member["attempt_id"]
        attempt = read(attempt_path) if attempt_path.exists() else {}
        op_path = unit / "operational-complete.json"
        op = read(op_path) if op_path.exists() else {}
        if op:
            summary_path = run / "score-batch/batch-summary.json"
            require(digest(attempt_path) == op["attempt_sha256"]
                    and digest(summary_path) == op["score_batch_sha256"],
                    "Operational completion pins changed")
            summary = read(summary_path)
            jobs_path = run / "score-jobs.jsonl"
            raw = jobs_path.read_bytes()
            jobs = [json.loads(line) for line in raw.splitlines() if line.strip()]
            pins.append({"path": str(jobs_path), "sha256": hashlib.sha256(raw).hexdigest()})
            require(summary["succeeded"] == op["successful_score_jobs"]
                    and summary["failed"] == op["failed_score_jobs"]
                    and len(jobs) == op["prepared_score_jobs"] == 1
                    and jobs[0]["job_id"] == member["attempt_id"]
                    and op["quality_read"] is False,
                    "Official score metadata differs")
        item = {key: member[key] for key in ("label", "run_id", "attempt_id")}
        item.update(attempt_present=attempt_path.exists(), run_present=run.parent.exists(),
                    unit_present=unit.exists(), attempt_state=attempt.get("state"),
                    started=(unit / "scientific-started.json").exists(),
                    failure_present=(unit / "scientific-failure.json").exists(),
                    successful_scores=op.get("successful_score_jobs", 0),
                    prepared_scores=op.get("prepared_score_jobs", 0),
                    failed_scores=op.get("failed_score_jobs", 0))
        for key, filename in (("finished_exit", "scientific-finished.json"),
                              ("campaign_exit", "campaign-exit.json"),
                              ("inspection_exit", "inspect-exit.json")):
            path = unit / filename
            item[key] = read(path)["exit_code"] if path.exists() else None
        members[label] = item
    require(all(digest(Path(item["path"])) == item["sha256"] for item in pins),
            "Operational metadata changed during observation")
    return members, pins


def verify_full_owner_capture(*, receipt, registration_sha):
    """Require the independent native exit in addition to complete-family gates.

    The caller must pin and read the exact admitted job's capture file. Success
    grants no READ and does not replace live process or seal/score qualification.
    """
    require(isinstance(receipt, dict), "Independent native owner receipt is absent")
    require(receipt.get("schema") == "saea-scientific-owner-native-exit-v1",
            "Independent native owner receipt schema differs")
    require(type(receipt.get("exit_code")) is int and receipt["exit_code"] == 0,
            "Independent native owner did not succeed")
    require(receipt.get("registration_sha256") == registration_sha,
            "Independent native exit belongs to another registration")
    return {"status": "NATIVE_OWNER_SUCCESS_BOUND",
            "registration_sha256": registration_sha, "read_authorized": False}
