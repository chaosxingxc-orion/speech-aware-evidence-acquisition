"""Join verified whole-policy decisions to complete official terminal feedback.

This produces a candidate numeric update. Admission of executable action assets,
capacity and a future experiment remains the flight's separate responsibility.
"""
from __future__ import annotations

from .system_feedback import SystemFeedbackError, load_system_feedback
from ..rails.finite_action_policy import RoundDescriptor, TerminalFeedback, update_complete_round
from ..rails.hashing import content_hash
from ..rails.system_episode_policy import SystemEpisodePolicy


def _require(condition, message):
    if not condition:
        raise SystemFeedbackError(message)


def _credit_feedback(feedback, policy):
    """Internal arithmetic join; the public entry always invokes source verification."""
    unsigned = dict(feedback)
    claimed = unsigned.pop("content_sha256", None)
    _require(claimed == content_hash(unsigned), "complete feedback fingerprint differs")
    _require(feedback.get("schema") == "saea-slurp-system-feedback-v1"
             and feedback.get("feedback_role") == "construction",
             "only complete construction feedback can update system policies")
    _require(policy.schedule.mode == "construction", "evaluation cannot update system policies")
    _require(feedback.get("policy_supply_receipt") is None,
             "nested optimized supply decisions need separately registered credit semantics")
    schedule = policy.schedule
    _require(feedback["split_identity_hash"] == schedule.split_identity_hash,
             "policy schedule and feedback split differ")
    trajectories = feedback["system_trajectories"]
    ids = trajectories["sample_ids"]
    _require(tuple(ids) == schedule.roster_ids, "policy update must cover the complete ordered roster")
    episodes = trajectories["trajectories"]
    terminal = feedback["terminal_feedback"]
    _require([r["sample_id"] for r in episodes] == ids
             and [r["sample_id"] for r in terminal] == ids,
             "terminal and trajectory populations differ")
    choices = feedback.get("policy_episode_decisions")
    _require(isinstance(choices, dict) and set(choices) == set(ids),
             "historical or incomplete decisions cannot be credited")
    rows = []
    for episode, final in zip(episodes, terminal):
        sid = episode["sample_id"]
        choice = choices[sid]
        _require(choice == episode.get("system_policy_decision"),
                 "decision does not belong to this complete episode")
        record = choice["record"]
        decision = policy.validate_record(record)
        _require(record["sample_id"] == sid
                 and final["trajectory_sha256"] == episode["trajectory_sha256"]
                 and final["delivered_output_sha256"] == episode["final_output"]["record_sha256"],
                 "policy credit belongs to a different terminal output")
        hashes = {
            **feedback["source_sha256"],
            "complete_feedback": claimed,
            "system_action_space": record["action_space_sha256"],
            "system_action_definition": record["selected_definition_sha256"],
            "system_policy_decision": record["decision_receipt_sha256"],
            "system_policy_snapshot": policy.snapshot.sha256,
            "system_policy_schedule": schedule.sha256,
        }
        rows.append(TerminalFeedback(
            sample_id=sid, trajectory_sha256=episode["trajectory_sha256"],
            source_hashes=tuple(sorted(hashes.items())), decision=decision,
            action=decision.action, logged_propensity=decision.propensity,
            tp=final["tp"], fp=final["fp"], fn=final["fn"],
            intent_exact=final["intent_exact"], format_ok=final["format_ok"],
            fallback_flags=tuple(final["fallback_flags"]),
        ))
    descriptor = RoundDescriptor(
        round_id=schedule.round_id, roster_ids=schedule.roster_ids,
        roster_sha256=schedule.roster_identity_sha256, snapshot_sha256=policy.snapshot.sha256,
        epsilon=schedule.epsilon, allocation_kind=schedule.allocation_kind,
        initial_quotas=schedule.initial_quotas,
    )
    updated = update_complete_round(policy.snapshot, descriptor, rows)
    receipt = {
        "schema": "saea-system-policy-credit-v1",
        "algorithm_id": "finite-system-policy-bandit-v1",
        "round_descriptor": descriptor.as_json(),
        "complete_feedback_sha256": claimed,
        "source_run_id": feedback["run_id"], "source_attempt_id": feedback["attempt_id"],
        "before_snapshot_sha256": policy.snapshot.sha256,
        "after_snapshot_sha256": updated.sha256,
        "newly_credited_episodes": len(rows),
        "fallback_episodes_retained": sum(bool(row.fallback_flags) for row in rows),
        "credit_scope": "selected complete policy; no node or unexecuted tool credit",
        "runtime_application_authorized": False,
        "remaining_boundary": "scientific action qualification and a separately registered next flight",
    }
    receipt["content_sha256"] = content_hash(receipt)
    return updated, receipt


def candidate_update_from_source(*, data_root, repo_root, binding, policy):
    """Verify a complete source before arithmetic; never mutate or apply the policy.

    A caller-supplied policy contains resolved bindings and asset assertions.
    The source verifier requires the pinned action catalog and per-row native
    configuration. Scientific action qualification and admission of the next
    flight remain separate; this output is not runtime authorization.
    """
    if not isinstance(policy, SystemEpisodePolicy):
        raise SystemFeedbackError("a frozen complete-system policy is required")
    if policy.schedule.mode != "construction":
        raise SystemFeedbackError("evaluation cannot read feedback for a policy update")
    feedback = load_system_feedback(data_root=data_root, repo_root=repo_root, binding=binding)
    return _credit_feedback(feedback, policy)
