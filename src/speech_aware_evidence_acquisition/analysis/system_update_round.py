"""Bind a semantic update to registered complete actors and their actual frozen memory."""
from pathlib import Path
from collections.abc import Mapping

from ..rails.prepared_feedback import PreparedFeedbackError, _read_pinned_json
from ..rails.hashing import content_hash
from ..rails.controllers import default_phase_program
from ..rails.candidate_experience_memory import load_candidate_experience_memory
from ..rails import system_comparison_context as comparison_sources
from ..rails.system_summary_context import _source_path


def _require(ok, message):
    if not ok:
        raise PreparedFeedbackError(message)


def verify_system_update_round(policy_pin, comparison, *, base_memory_pin, base_snapshot,
                               sample_ids, round_id, data_root):
    """Verify registered actor membership and availability, not semantic use or on-policy credit."""
    data = Path(data_root)
    policy, policy_sha = _read_pinned_json(policy_pin, data_root=data, field="update round policy")
    _require(isinstance(policy, Mapping) and set(policy) == {
        "schema", "round_id", "actors", "base_memory_snapshot_sha256"
    } and policy["schema"] == "saea-system-update-round-policy-v1"
             and policy["round_id"] == round_id, "update round policy fields or round differ")
    expected_base = None if base_memory_pin is None else base_snapshot["content_sha256"]
    _require(policy["base_memory_snapshot_sha256"] == expected_base, "round policy names another frozen memory")
    members = comparison.source_binding["members"]
    registered = policy["actors"]
    _require(isinstance(registered, list) and len(registered) == len(members) and len(members) >= 2,
             "registered actor population differs")
    observed, seen = [], set()
    for expected, member in zip(registered, members):
        summary = comparison_sources.verify_system_summaries(
            member["summary_manifest"], repo_root=member["summary_repo_root"], data_root=data)
        actor = summary.actor_binding
        manifest, manifest_sha = _source_path(actor["manifest"], data, "round actor manifest")
        phases, phases_sha = _source_path(actor["phases"], data, "round actor phases")
        source = comparison_sources.verify_native_episode_source(
            manifest_path=manifest, expected_manifest_sha256=manifest_sha,
            phase_artifact_path=phases, expected_phase_sha256=phases_sha,
            repo_root=Path(actor["source_repo_root"]), data_root=data)
        actual = {"label": member["label"], "run_id": source.plan.run_id,
                  "attempt_id": source.plan.attempt_id, "config_hash": source.composed.config_hash,
                  "study_commit": source.bundle.manifest["study_commit"],
                  "protocol_hash": source.plan.protocol_hash}
        _require(expected == actual, "sampled actor differs from registered round policy")
        identity = (actual["run_id"], actual["attempt_id"])
        _require(identity not in seen, "round repeats an actor")
        seen.add(identity)
        _require(actor["round_id"] == round_id and set(source.sample_ids) == set(sample_ids),
                 "round actor input population differs")
        values = source.composed.values
        _require(values.get("experience_memory") is None and values.get("system_episode_policy") is None,
                 "round requires explicit candidate-memory credit, not another memory or policy selector")
        memory_config = values.get("candidate_experience_memory")
        if base_memory_pin is None:
            _require(memory_config is None, "initial round actor unexpectedly used memory")
            memory = None
        else:
            _require(isinstance(memory_config, Mapping), "round actor did not bind the frozen memory")
            _require(memory_config["artifact"]["sha256"] == base_memory_pin["candidate_artifact"]["sha256"],
                     "round actor used another candidate artifact")
            memory = load_candidate_experience_memory(
                values, repo_root=Path(actor["source_repo_root"]), data_root=data,
                carrier_lock_key=source.plan.carrier_lock_key, plan=source.plan,
                sample_ids=source.sample_ids, program=default_phase_program(values["policy"]),
                tool_specs=values.get("phase_tools", {}))
            _require(memory is not None and [r.record_sha256 for r in memory.records]
                     == [r["record_sha256"] for r in base_snapshot["records"]],
                     "round actor memory pack/order differs from frozen updater base")
        observed.append({**actual, "manifest_sha256": manifest_sha,
                         "base_snapshot_sha256": expected_base,
                         "memory_record_sha256s": [] if memory is None else [r.record_sha256 for r in memory.records]})
    receipt = {"schema": "saea-system-update-round-verification-v1", "round_id": round_id,
               "policy_sha256": policy_sha, "actors": observed, "base_snapshot_sha256": expected_base,
               "interpretation": "Registered actor/config membership and frozen memory availability; not proof of semantic consumption, causal credit or a common stochastic policy."}
    return {**receipt, "content_sha256": content_hash(receipt)}
