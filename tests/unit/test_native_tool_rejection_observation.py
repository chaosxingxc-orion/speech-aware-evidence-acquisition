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


@pytest.mark.parametrize("sample_count", [1, 2])
def test_multiple_calls_are_rejected_together_without_executing_tools(
    tmp_path, monkeypatch, sample_count,
):
    from copy import deepcopy
    single_wire = episode_runner._wire_tool_call

    def multiple_calls(tool_id):
        wire = json.loads(single_wire(tool_id))
        calls = wire["choices"][0]["message"]["tool_calls"]
        second = deepcopy(calls[0])
        second["id"] = "call-task-contract-2"
        calls.append(second)
        return json.dumps(wire).encode()

    monkeypatch.setattr(episode_runner, "_wire_tool_call", multiple_calls)
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path, sample_count=sample_count, max_revisions=1, max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
        overlap=sample_count > 1,
    )
    harness.tools_for_phase.trace_sink = harness.trace
    try:
        summary = harness.run()
    finally:
        closed = harness.close()

    assert closed["request_count"] == 8 * sample_count
    assert closed["cost"]["tool_calls"] == 0
    assert harness.tool_contacts == []
    for result in summary.results:
        assert result.final_response_text == f"solver-answer:{result.sample_id}:visit:2"
        for key in ((result.sample_id, "reviewer", 1, 2),
                    (result.sample_id, "solver", 2, 1)):
            messages = harness.prepared[key]["rendered"]["messages"]
            tool_messages = [row for row in messages if row["role"] == "tool"]
            assert [row["tool_call_id"] for row in tool_messages] == [
                "call-task-contract-1", "call-task-contract-2",
            ]
            for row in tool_messages:
                feedback = json.loads(row["content"])
                assert feedback["evidence"] == []
                assert feedback["result"]["status"] == "rejected"
                assert feedback["result"]["error_code"] == "multiple-tool-calls"
                assert feedback["result"]["lookup_performed"] is False
            assistant = next(row for row in messages if row.get("tool_calls"))
            assert [row["id"] for row in assistant["tool_calls"]] == [
                "call-task-contract-1", "call-task-contract-2",
            ]

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
    assert report["rejected_call_count"] == sample_count * 2
    assert report["exposed_rejected_call_count"] == sample_count * 2


@pytest.mark.parametrize("typed", [False, True])
def test_rejected_batches_preserve_reserved_report_and_actual_role_context(
    tmp_path, monkeypatch, typed,
):
    from copy import deepcopy
    from dataclasses import replace
    from test_role_context_runner import _configure_typed_context

    original_wire = episode_runner._wire_tool_call
    def batch(tool_id):
        wire = json.loads(original_wire(tool_id))
        calls = wire["choices"][0]["message"]["tool_calls"]
        second = deepcopy(calls[0])
        second["id"] = "batch-second"
        calls.append(second)
        return json.dumps(wire).encode()
    monkeypatch.setattr(episode_runner, "_wire_tool_call", batch)
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
    )
    expected = _configure_typed_context(harness) if typed else None
    harness.config = replace(
        harness.config, reserve_final_report=True, local_tool_workers=1,
        roles=tuple(
            replace(role, max_iterations=3, history_scope="latest-solver-and-local-tools")
            if role.role_kind == "reviewer" else role
            for role in harness.config.roles
        ),
    )
    output = harness._output
    def repeated(key):
        if key[1] == "reviewer" and key[3] < 3:
            return None
        return output(key)
    harness._output = repeated
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 11
    assert closed["cost"]["tool_calls"] == 0
    assert harness.tool_contacts == []
    assert summary.results[0].final_response_text == (
        expected["revised_draft"] if typed else "solver-answer:s1:visit:2"
    )
    for visit in (1, 2):
        final = harness.prepared[("s1", "reviewer", visit, 3)]["rendered"]
        assert final["tool_choice"] == "none"
        assert not final.get("tools")
        assert len([m for m in final["messages"] if m["role"] == "tool"]) == 4
        assert all(
            json.loads(m["content"])["result"]["lookup_performed"] is False
            for m in final["messages"] if m["role"] == "tool"
        )


def test_multi_target_lookup_executes_neither_store_and_supplies_no_values(
    tmp_path, monkeypatch,
):
    from test_native_target_knowledge_tools import _binding, _config, _args, TARGET
    from test_phase_native_tools import call

    binding = _binding(tmp_path / "stores", monkeypatch)
    builder = episode_runner.build_phase_tools
    def target_tools(config, *args, **kwargs):
        return builder({**config, **_config()}, *args, **kwargs, knowledge_stores=binding)
    monkeypatch.setattr(episode_runner, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode_runner, "TASK_CONTRACT_TOOL", TARGET)
    monkeypatch.setattr(episode_runner, "build_phase_tools", target_tools)
    def wire(tool_id):
        calls = call(tool_id, _args("tool-activation"))
        second = call(tool_id, _args("parameter-meaning"))[0]
        second["id"] = "second-store"
        calls.append(second)
        return json.dumps({
            "choices": [{"message": {"role": "assistant", "content": None, "tool_calls": calls},
                         "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        }).encode()
    monkeypatch.setattr(episode_runner, "_wire_tool_call", wire)
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path / "episode", sample_count=1, max_revisions=1, max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
    )
    shared_run = episode_runner.run_speech_native_agent_loop
    monkeypatch.setattr(
        episode_runner, "run_speech_native_agent_loop",
        lambda **kwargs: shared_run(
            **kwargs, knowledge_value_renderer=harness.tools_for_phase.render_values,
        ),
    )
    try:
        result = harness.run().results[0]
    finally:
        closed = harness.close()
    assert closed["request_count"] == 8
    assert closed["cost"]["tool_calls"] == 0
    assert harness.tool_contacts == []
    assert result.final_query_state.retrieved_value_ids == ()
    for key in (("s1", "reviewer", 1, 2), ("s1", "solver", 2, 1)):
        messages = harness.prepared[key]["rendered"]["messages"]
        returns = [json.loads(row["content"]) for row in messages if row["role"] == "tool"]
        assert len(returns) == 2
        assert all(row["evidence"] == [] and row["result"]["lookup_performed"] is False for row in returns)
