from __future__ import annotations

import copy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from test_native_episode_diagnostics import _fixture, _terminal_fixture, _finite_fixture
from speech_aware_evidence_acquisition.analysis.native_episode_source import VerifiedNativeEpisodeSource
from speech_aware_evidence_acquisition.analysis.system_trajectory import (
    SystemTrajectoryError, export_system_trajectories,
)


def _source(fixture=_fixture):
    policy, phase, output, trace = fixture()
    return VerifiedNativeEpisodeSource(
        bundle=SimpleNamespace(trace_records=trace, manifest={"run_id": "run", "outputs": {"sha256": "a" * 64}}),
        composed=SimpleNamespace(config_hash="c" * 64, values={"policy": policy}),
        plan=SimpleNamespace(run_id="run", attempt_id="attempt"),
        sample_ids=("s1",), phase_results={"s1": phase}, output_rows={"s1": output},
        phase_artifact_sha256="b" * 64, diagnostics={},
    )


def _row(source):
    return export_system_trajectories(source)["trajectories"][0]


def test_exports_whole_accepted_episode_with_source_references():
    row = _row(_source())
    assert row["delivery"]["kind"] == "accepted"
    assert [visit["stage"] for visit in row["role_visits"]] == [
        "perception", "solver", "review", "planner"
    ]
    assert len(row["role_visits"][2]["contacts"]) == 2
    assert row["role_visits"][2]["contacts"][0]["request_record_id"] == "request-reviewer-1/request"
    assert row["planner_routes"][0]["action"] == "ACCEPT"
    assert len(row["tool_events"]) == 2
    assert '{"answer":"accepted"}' not in str(row)


def test_reviewer_evidence_and_tool_changes_affect_fingerprint():
    initial = _source()
    base = _row(initial)["trajectory_sha256"]
    reviewer = copy.deepcopy(initial)
    reviewer.bundle.trace_records["request-reviewer-2/request"]["payload"]["history"].append("changed")
    assert _row(reviewer)["trajectory_sha256"] != base
    evidence = copy.deepcopy(initial)
    evidence.bundle.trace_records["request-solver-1/request"]["payload"]["supplied_evidence"][0]["evidence_id"] = "other"
    assert _row(evidence)["trajectory_sha256"] != base
    tool = copy.deepcopy(initial)
    tool_id = next(key for key in tool.bundle.trace_records if "/tool-result/" in key)
    tool.bundle.trace_records[tool_id]["extra_metadata"] = {"changed": True}
    assert _row(tool)["trajectory_sha256"] != base


def test_terminal_and_interrupted_roles_are_preserved():
    terminal = _row(_source(_terminal_fixture))
    assert terminal["delivery"]["kind"] == "terminal"
    assert terminal["planner_routes"][0]["action"] == "REVISE"
    finite = _row(_source(lambda: _finite_fixture(with_solver=True)))
    assert finite["role_visits"][-1]["interrupted"] is True
    assert finite["delivery"]["kind"] == "finite"


def test_missing_or_misbound_contact_is_rejected():
    missing = _source()
    del missing.bundle.trace_records["request-reviewer-2/response"]
    with pytest.raises(SystemTrajectoryError):
        export_system_trajectories(missing)
    wrong = _source()
    wrong.bundle.trace_records["request-planner-1/native-role-contact"]["use_role_id"] = "solver"
    with pytest.raises(SystemTrajectoryError):
        export_system_trajectories(wrong)


def test_unrecorded_phase_fields_are_unknown_and_recorded_empty_is_present():
    source = _source()
    row = _row(source)
    assert row["phase_fields"]["agent_states"]["status"] == "unavailable_in_source"
    source.phase_results["s1"]["agent_states"] = []
    row = _row(source)
    assert row["phase_fields"]["agent_states"]["status"] == "recorded"
    assert row["phase_fields"]["agent_states"]["count"] == 0



def test_trajectory_fingerprint_binds_source_identity_and_is_deterministic():
    source = _source()
    original = _row(source)["trajectory_sha256"]
    assert _row(source)["trajectory_sha256"] == original
    for field in ("run_id", "attempt_id"):
        changed = copy.deepcopy(source)
        setattr(changed.plan, field, "other")
        assert _row(changed)["trajectory_sha256"] != original
    changed = copy.deepcopy(source)
    changed.composed.config_hash = "d" * 64
    assert _row(changed)["trajectory_sha256"] != original
    changed = copy.deepcopy(source)
    changed = replace(changed, phase_artifact_sha256="e" * 64)
    assert _row(changed)["trajectory_sha256"] != original


def test_state_and_transition_items_are_individually_addressable():
    source = _source()
    source.phase_results["s1"]["agent_states"] = [{"state_kind": "phase:perception", "content": "one"}]
    source.phase_results["s1"]["transitions"] = [{"phase": "supply", "value_ids": ["value-1"]}]
    first = _row(source)
    assert first["phase_fields"]["agent_states"]["items"][0]["index"] == 0
    assert len(first["phase_fields"]["transitions"]["items"][0]["content_sha256"]) == 64
    source.phase_results["s1"]["transitions"][0]["value_ids"].append("value-2")
    assert _row(source)["trajectory_sha256"] != first["trajectory_sha256"]


def test_known_exception_events_remain_addressable_with_unknown_distinct_from_empty():
    from speech_aware_evidence_acquisition.analysis.system_trajectory import _episode_events
    absent = _episode_events({})
    assert absent["truncation_events"] == {"status": "unavailable_in_source"}
    block = {"schema": "saea-native-length-truncation-v1", "count": 1,
             "events": [{"role_id": "reviewer", "finish_reason": "length"}]}
    result = _episode_events({"truncation_events": block})
    assert result["truncation_events"]["count"] == 1
    assert len(result["truncation_events"]["items"]) == 1
    assert result["truncation_events"]["items"][0]["index"] == 0
    assert len(result["truncation_events"]["content_sha256"]) == 64
    empty = _episode_events({"truncation_events": []})
    assert empty["truncation_events"]["status"] == "recorded"
    assert empty["truncation_events"]["count"] == 0


def _source_with_policy_decision(fixture=_fixture):
    from speech_aware_evidence_acquisition.rails.finite_action_policy import PolicySnapshot, sample_action
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    from speech_aware_evidence_acquisition.rails.knowledge import QueryState
    source = _source(fixture)
    source.output_rows["s1"]["native_episode_receipt"] = copy.deepcopy(
        source.output_rows["s1"]["native_episode_receipt"])
    query = QueryState(query_id="q", query_sample_id="s1", speech_packet_id="packet",
                       speech_packet_sha256="a"*64, use_split_identity_hash="b"*64)
    snapshot = PolicySnapshot.create(actions=("complete-policy",), states=("episode-start",), f0=.58)
    record = {
        "schema": "saea-system-episode-policy-decision-v1",
        "algorithm_id": "finite-system-policy-bandit-v1",
        "selection_scope": "complete-episode-policy", "sample_id": "s1", "sequence_index": 0,
        "pre_action_query_sha256": query.content_hash(), "speech_packet_sha256": "a"*64,
        "schedule_sha256": "c"*64, "action_space_sha256": "d"*64,
        "selected_definition_sha256": "e"*64, "selected_source_hashes": {"config": "f"*64},
        "decision": sample_action(snapshot,state_id="episode-start",epsilon=0,draw=.2).as_json(),
    }
    record["decision_receipt_sha256"] = content_hash(record)
    source.phase_results["s1"]["initial_query_state"] = query.as_json()
    source.phase_results["s1"]["native_episode_receipt"]["system_policy_decision"] = copy.deepcopy(record)
    source.output_rows["s1"]["native_episode_receipt"]["system_policy_decision"] = copy.deepcopy(record)
    key = "s1/system-policy/initial"
    source.bundle.trace_records = {key: {"org_system_policy_decision": copy.deepcopy(record)},
                                   **source.bundle.trace_records}
    first = source.bundle.trace_records["request-perception-1/request"]["payload"]
    first["speech_packet_sha256"] = "a"*64
    return source, record


def test_system_policy_choice_is_joined_to_initial_state_and_complete_trajectory():
    source, record = _source_with_policy_decision()
    row = _row(source)
    assert row["system_policy_decision"]["record"] == record
    assert row["system_policy_decision"]["trace_record_id"] == "s1/system-policy/initial"
    assert row["system_policy_decision"]["claim_scope"] == "recorded-choice-not-learning-admission"
    assert "system_policy_decision" not in _row(_source())


@pytest.mark.parametrize("mutation", [
    "missing-trace", "late-trace", "another-query", "another-audio", "hidden-decision",
    "duplicate-decision", "unknown-field", "future-state",
])
def test_system_policy_source_disagreement_cannot_be_erased(mutation):
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    source, record = _source_with_policy_decision()
    key = "s1/system-policy/initial"
    if mutation == "missing-trace":
        del source.bundle.trace_records[key]
    elif mutation == "late-trace":
        item = source.bundle.trace_records.pop(key)
        source.bundle.trace_records[key] = item
    elif mutation == "duplicate-decision":
        source.bundle.trace_records["another-choice"] = copy.deepcopy(source.bundle.trace_records[key])
    elif mutation == "hidden-decision":
        del source.phase_results["s1"]["native_episode_receipt"]["system_policy_decision"]
        del source.output_rows["s1"]["native_episode_receipt"]["system_policy_decision"]
    else:
        if mutation == "another-query":
            record["pre_action_query_sha256"] = "f"*64
        elif mutation == "another-audio":
            record["speech_packet_sha256"] = "f"*64
        elif mutation == "unknown-field":
            record["future_answer"] = "not allowed"
        elif mutation == "future-state":
            record["decision"]["state_id"] = "after-solver"
        record.pop("decision_receipt_sha256")
        record["decision_receipt_sha256"] = content_hash(record)
        source.phase_results["s1"]["native_episode_receipt"]["system_policy_decision"] = copy.deepcopy(record)
        source.output_rows["s1"]["native_episode_receipt"]["system_policy_decision"] = copy.deepcopy(record)
        source.bundle.trace_records[key]["org_system_policy_decision"] = copy.deepcopy(record)
    with pytest.raises(SystemTrajectoryError, match="policy"):
        _row(source)


def test_legacy_source_keeps_its_pinned_trajectory_without_proposal_fields():
    row = _row(_source())
    assert "candidate_proposal" not in row
    assert row["trajectory_sha256"] == "bff6b696f65a377951568ca78810f89383cbbaa16ded39ad17e6c19671bca625"


def test_malformed_candidate_receipt_cannot_pass_through_score_free_export():
    source = _source()
    source.phase_results["s1"]["native_episode_receipt"]["candidate_proposal"] = {}
    source.output_rows["s1"]["native_episode_receipt"]["candidate_proposal"] = {}
    with pytest.raises(SystemTrajectoryError, match="proposal"):
        _row(source)
