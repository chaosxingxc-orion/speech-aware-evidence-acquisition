"""Finite supply decisions through the ordinary fake-transport OpenJiuwen graph."""

from dataclasses import replace
import json

import pytest

import test_native_episode_runner as harness_module
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_rails_controllers import _phase_supply
from test_rails_runner import _knowledge_snapshot
from speech_aware_evidence_acquisition.rails.finite_action_policy import PolicySnapshot
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import PolicySchedule
from speech_aware_evidence_acquisition.rails.finite_supply_policy import (
    AGREEMENT_STATES, EpisodeSupplyPolicy,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available


VALUE_ID = "value:dim-light"


def _bound_graph_policy(harness, monkeypatch, *, roster_ids):
    snapshot = PolicySnapshot.create(
        actions=("supplied", "none"), states=AGREEMENT_STATES, f0=0.58,
    )
    schedule = PolicySchedule.from_json({
        "schema": "saea-finite-action-policy-schedule-v1",
        "round_id": "synthetic-graph-round", "mode": "evaluation",
        "snapshot_sha256": snapshot.sha256, "roster_ids": list(roster_ids),
        "roster_identity_sha256": content_hash(list(roster_ids)),
        "split_identity_hash": "b" * 64, "seed": 23,
        "allocation_kind": "epsilon-greedy", "epsilon": 0.0,
        "initial_quotas": [],
    }).bind(snapshot)
    emitted = []

    def record_decision(record):
        emitted.append(record)
        with harness.lock:
            harness.events.append(("decision", record["sample_id"]))

    def supplied(_phase, context):
        return _phase_supply(context, value_ids=(VALUE_ID,), facet_ids=("operation:dim",))

    policy = EpisodeSupplyPolicy(
        snapshot=snapshot, schedule=schedule,
        phase_id="solver", perception_phase="perception",
        preview_supply=lambda context: supplied("solver", context),
        preview_snapshot_sha256=_knowledge_snapshot().content_hash(),
        preview_labels={VALUE_ID: "dim-light"},
        action_supplies={"supplied": supplied, "none": lambda phase, context: None},
        default_supply=lambda phase, context: None,
        candidate_reader=lambda state, sample_id: ("dim-light",),
        emit_decision=record_decision,
    )
    real_binding = harness_module.NativeEpisodeRunBinding
    monkeypatch.setattr(
        harness_module, "NativeEpisodeRunBinding",
        lambda **kwargs: real_binding(**kwargs, supply_for_phase=policy),
    )
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, knowledge="supplied") if phase.name == "solver" else phase
            for phase in harness.program.phases
        ),
    )
    return policy, emitted


def _requests(harness):
    return [payload["payload"] for channel, _record_id, payload in harness.trace.records
            if channel == "MODEL_REQUEST"]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_revision_keeps_one_pre_solver_decision_through_seven_ordinary_roles(tmp_path, monkeypatch):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=7,
        planner_actions=("REVISE", "ACCEPT"),
    )
    policy, emitted = _bound_graph_policy(harness, monkeypatch, roster_ids=("s1",))
    try:
        summary = harness.run()
    finally:
        close = harness.close()
    assert close["request_count"] == 7
    result = summary.results[0]
    assert [visit["stage"] for visit in result.native_episode_receipt["role_visits"]] == [
        "perception", "solver", "review", "planner", "solver", "review", "planner",
    ]
    assert len(emitted) == 1
    assert emitted[0]["state_id"] == "agree-ge-0.75"
    assert emitted[0]["decision"]["action"] == "supplied"
    assert emitted[0]["preview"]["exposed_to_model"] is False
    assert harness.events.index(("dispatch", ("s1", "perception", 1, 1))) < harness.events.index(("decision", "s1"))
    assert harness.events.index(("decision", "s1")) < harness.events.index(("fit", ("s1", "solver", 1, 1)))
    assert harness.events.index(("decision", "s1")) < harness.events.index(("dispatch", ("s1", "solver", 1, 1)))
    requests = _requests(harness)
    assert len(requests) == 7
    for index in (1, 4):
        assert [item["evidence_id"] for item in requests[index]["supplied_evidence"]] == [VALUE_ID]
    assert [visit["selected_value_ids"] for visit in policy.receipt["visits"]] == [[VALUE_ID], [VALUE_ID]]
    assert [visit["action"] for visit in policy.receipt["visits"]] == ["supplied", "supplied"]
    assert result.final_query_state.retrieved_value_ids == (VALUE_ID,)
    assert "supply_variants" not in json.dumps(result.native_episode_receipt)
    assert "supply_variants" not in json.dumps(requests)
    assert "variant_arm_id" not in json.dumps(requests)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_no_revision_and_concurrent_samples_keep_independent_decisions(tmp_path, monkeypatch):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=2, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), overlap=True,
    )
    policy, emitted = _bound_graph_policy(harness, monkeypatch, roster_ids=("s1", "s2"))
    try:
        summary = harness.run()
    finally:
        close = harness.close()
    assert close["request_count"] == 8
    assert len(emitted) == 2 and {item["sample_id"] for item in emitted} == {"s1", "s2"}
    assert {item["sequence_index"] for item in emitted} == {0, 1}
    for result in summary.results:
        sid = result.sample_id
        assert [visit["stage"] for visit in result.native_episode_receipt["role_visits"]] == [
            "perception", "solver", "review", "planner",
        ]
        assert result.final_query_state.retrieved_value_ids == (VALUE_ID,)
        assert harness.events.index(("decision", sid)) < harness.events.index(("dispatch", (sid, "solver", 1, 1)))
    assert len(policy.receipt["decisions"]) == 2
    assert len(policy.receipt["visits"]) == 2
    requests_by_id = {
        record_id.removesuffix("/request"): payload["payload"]
        for channel, record_id, payload in harness.trace.records if channel == "MODEL_REQUEST"
    }
    for result in summary.results:
        solver_visit = result.native_episode_receipt["role_visits"][1]
        request_id = solver_visit["execution_receipt"]["final_contact"]["request_id"]
        assert [item["evidence_id"] for item in requests_by_id[request_id]["supplied_evidence"]] == [VALUE_ID]
