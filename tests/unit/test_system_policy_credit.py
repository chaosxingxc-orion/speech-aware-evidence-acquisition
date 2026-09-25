"""Candidate updates from whole-episode feedback; all counts here are synthetic."""
import copy
from dataclasses import replace
import pytest

from test_system_trajectory import _source_with_policy_decision, _terminal_fixture
from test_system_episode_policy import _policy
from test_native_episode_runner import _config, _program
from speech_aware_evidence_acquisition.analysis import system_policy_credit as module
from speech_aware_evidence_acquisition.analysis.system_trajectory import export_system_trajectories
from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
from speech_aware_evidence_acquisition.rails.system_episode_policy import SystemEpisodePolicy
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def _rehash(document):
    document.pop("content_sha256", None)
    document["content_sha256"] = content_hash(document)
    return document


@pytest.fixture
def case():
    noop = lambda *args: None
    binding = NativeEpisodeRunBinding(
        config=_config(max_revisions=1, max_contacts=7), program=_program(max_contacts=7),
        material_for_phase=noop, render_request=noop, request_gate=noop,
    )
    policy = _policy({"complete-policy": binding})
    source, old = _source_with_policy_decision(_terminal_fixture)
    record = policy.expected_record(
        "s1", query_sha256=old["pre_action_query_sha256"],
        speech_packet_sha256=old["speech_packet_sha256"],
    )
    for row in (source.phase_results["s1"], source.output_rows["s1"]):
        row["native_episode_receipt"]["system_policy_decision"] = copy.deepcopy(record)
    source.bundle.trace_records["s1/system-policy/initial"]["org_system_policy_decision"] = copy.deepcopy(record)
    exported = export_system_trajectories(source)
    episode = exported["trajectories"][0]
    feedback = _rehash({
        "schema": "saea-slurp-system-feedback-v1", "feedback_role": "construction",
        "split_identity_hash": policy.schedule.split_identity_hash,
        "source_sha256": {"manifest": "a"*64, "phases": "b"*64, "scores": "c"*64},
        "run_id": "synthetic-run", "attempt_id": "synthetic-attempt",
        "system_trajectories": exported, "policy_supply_receipt": None,
        "policy_episode_decisions": {"s1": episode["system_policy_decision"]},
        "terminal_feedback": [{
            "sample_id": "s1", "trajectory_sha256": episode["trajectory_sha256"],
            "delivered_output_sha256": episode["final_output"]["record_sha256"],
            "tp": 0, "fp": 2, "fn": 0, "intent_exact": 1, "format_ok": False,
            "fallback_flags": ["terminal:episode-exhausted"],
        }],
    })
    return policy, feedback


def test_complete_fallback_and_empty_entity_false_positives_receive_terminal_credit(case):
    policy, feedback = case
    before = policy.snapshot.sha256
    updated, receipt = module._credit_feedback(feedback, policy)
    assert updated.credited[0].utility == pytest.approx(-1.16)
    assert updated.credited[0].fp == 2
    assert updated.credited[0].format_ok is False
    assert updated.credited[0].fallback_flags == ("terminal:episode-exhausted",)
    assert receipt["fallback_episodes_retained"] == receipt["newly_credited_episodes"] == 1
    assert receipt["runtime_application_authorized"] is False
    assert policy.snapshot.sha256 == before and policy.decisions == {}
    again, _ = module._credit_feedback(feedback, policy)
    assert again.sha256 == updated.sha256


@pytest.mark.parametrize("mutation", [
    "historical", "partial", "evaluation", "different-split", "different-output",
    "different-propensity", "different-action-definition", "nested-decision", "bad-fingerprint",
])
def test_source_or_allocation_mismatch_cannot_create_credit(case, mutation):
    policy, feedback = case
    if mutation == "historical":
        feedback.pop("policy_episode_decisions")
    elif mutation == "partial":
        feedback["terminal_feedback"] = []
    elif mutation == "evaluation":
        feedback["feedback_role"] = "evaluation"
    elif mutation == "different-split":
        feedback["split_identity_hash"] = "f"*64
    elif mutation == "different-output":
        feedback["terminal_feedback"][0]["delivered_output_sha256"] = "f"*64
    elif mutation == "nested-decision":
        feedback["policy_supply_receipt"] = {"present": True}
    elif mutation != "bad-fingerprint":
        record = feedback["policy_episode_decisions"]["s1"]["record"]
        if mutation == "different-propensity":
            record["decision"]["draw"] = .99999
        else:
            record["selected_definition_sha256"] = "f"*64
        record.pop("decision_receipt_sha256")
        record["decision_receipt_sha256"] = content_hash(record)
    _rehash(feedback)
    if mutation == "bad-fingerprint":
        feedback["terminal_feedback"][0]["fp"] = 100
    with pytest.raises(ValueError):
        module._credit_feedback(feedback, policy)


def test_public_entry_verifies_full_source_once_before_any_candidate_update(case, monkeypatch):
    policy, feedback = case
    reads = []
    def read(**kwargs):
        reads.append(kwargs)
        return feedback
    monkeypatch.setattr(module, "load_system_feedback", read)
    updated, _ = module.candidate_update_from_source(
        data_root="synthetic-data", repo_root="synthetic-repo", binding={"pinned": True}, policy=policy)
    assert len(reads) == 1 and len(updated.credited) == 1
    def fail(**kwargs):
        raise ValueError("source not sealed")
    monkeypatch.setattr(module, "load_system_feedback", fail)
    with pytest.raises(ValueError, match="not sealed"):
        module.candidate_update_from_source(data_root="", repo_root="", binding={}, policy=policy)


def test_evaluation_policy_is_rejected_before_loading_any_feedback(case, monkeypatch):
    policy, feedback = case
    schedule = replace(policy.schedule, mode="evaluation", allocation_kind="epsilon-greedy",
                       epsilon=0.0, initial_quotas=())
    evaluation = SystemEpisodePolicy(
        snapshot=policy.snapshot, schedule=schedule, actions=policy.actions,
        source_hashes={"complete-policy": {"config": "f"*64}})
    def forbidden(**kwargs):
        raise AssertionError("evaluation feedback must not be read")
    monkeypatch.setattr(module, "load_system_feedback", forbidden)
    with pytest.raises(ValueError, match="evaluation"):
        module.candidate_update_from_source(data_root="",repo_root="",binding={},policy=evaluation)
