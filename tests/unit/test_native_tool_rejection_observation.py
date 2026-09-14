"""Expected candidate input rejection stays in the actual bounded native tool loop."""

import json

import pytest

import test_native_episode_runner as episode_runner
from speech_aware_evidence_acquisition.rails.phase_tools import CANDIDATE_CONTRACT_TOOL
from test_candidate_contract_lookup import SyntheticProvider, _result
from test_native_candidate_schema_integration import _candidate_wire_call
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


@pytest.mark.parametrize("sample_count", [1, 2])
@pytest.mark.parametrize("candidate_ids", [
    ("unknown_candidate",), ("intent_alpha", "unknown_candidate"),
])
def test_unknown_candidate_is_counted_feedback_without_lookup(
    tmp_path, monkeypatch, sample_count, candidate_ids,
):
    provider = SyntheticProvider(_result)
    provider.candidate_ids = ("intent_alpha", "intent_beta", "intent_gamma")
    builder = episode_runner.build_phase_tools

    def candidate_tools(config, *args, **kwargs):
        config = {
            **config,
            "phase_tools": {
                **config["phase_tools"],
                "reviewer": {**config["phase_tools"]["reviewer"], "candidate_limit": 3},
            },
        }
        return builder(config, *args, **kwargs, candidate_contracts=provider)

    monkeypatch.setattr(episode_runner, "TASK_CONTRACT_TOOL", CANDIDATE_CONTRACT_TOOL)
    monkeypatch.setattr(episode_runner, "build_phase_tools", candidate_tools)
    monkeypatch.setattr(
        episode_runner, "_wire_tool_call",
        lambda tool_id: _candidate_wire_call(tool_id, candidate_ids),
    )
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path, sample_count=sample_count, max_revisions=1, max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
    )
    harness.tools_for_phase.trace_sink = harness.trace
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert len(summary.results) == sample_count
    assert closed["request_count"] == 8 * sample_count
    assert closed["cost"]["tool_calls"] == sample_count
    assert provider.requests == []
    assert len(harness.tool_contacts) == sample_count
    for contact in harness.tool_contacts:
        assert contact["arguments"] == {"candidate_ids": list(candidate_ids)}
    for index, result in enumerate(summary.results, 1):
        sample_id = f"s{index}"
        assert result.final_response_text == f"solver-answer:{sample_id}:visit:2"
        assert len(result.contacts) == 8
        for key in ((sample_id, "reviewer", 1, 2), (sample_id, "solver", 2, 1)):
            messages = [
                item for item in harness.prepared[key]["rendered"]["messages"]
                if item["role"] == "tool"
            ]
            assert len(messages) == 1
            assert messages[0]["tool_call_id"] == "call-candidate-contract-1"
            feedback = json.loads(messages[0]["content"])
            assert feedback["evidence"] == []
            assert feedback["result"]["status"] == "rejected"
            assert feedback["result"]["error_code"] == "unknown-candidate-ids"
            assert feedback["result"]["lookup_performed"] is False
            assert feedback["result"]["invalid_candidate_ids"] == ["unknown_candidate"]
            assert "candidates" not in feedback["result"]
    receipt = harness.tools_for_phase.receipt()
    assert receipt["attempts"] == sample_count
    assert receipt["completed"] == 0
    assert receipt["native_rejected_requests"]["count"] == sample_count
    assert receipt["candidate_contracts"]["supply_events"] == 0

    from speech_aware_evidence_acquisition.analysis.native_tool_exposure import (
        analyze_verified_native_tool_exposure,
    )
    phases = {item.sample_id: item.as_json() for item in summary.results}
    outputs = {
        key: {"sample_id": key, "text": row["final_response_text"],
              "native_episode_receipt": row["native_episode_receipt"]}
        for key, row in phases.items()
    }
    report = analyze_verified_native_tool_exposure(
        sample_ids=tuple(phases), controller_policy_id=summary.controller_policy_id,
        phase_results=phases, output_rows=outputs,
        trace_records={key: row for _channel, key, row in harness.trace.records},
    )
    assert report["successful_call_count"] == 0
    assert report["calls"] == []
    assert report["rejected_call_count"] == sample_count
    assert report["exposed_rejected_call_count"] == sample_count
    assert report["non_result_event_counts"]["rejected"] == sample_count
    assert all(row["outcome"] == "rejected" for row in report["rejected_calls"])
