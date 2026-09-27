"""End-to-end tests for bounded phase tool actions."""

from __future__ import annotations
import json
import re
import sys
from dataclasses import replace
from pathlib import Path
import pytest

# The shared fixtures live in tests/unit/test_rails_runner.py. pytest's default (prepend) import mode puts only
# THIS file's directory (tests/integration) on sys.path, and tests/integration is collected before tests/unit,
# so the bare import below failed collection in a full-suite run (it only passed when tests/unit had already
# been inserted). Put tests/unit on sys.path explicitly; the module name stays `test_rails_runner`, the same
# name pytest itself gives that file, so both resolve to one module object.
_UNIT_TESTS = str(Path(__file__).resolve().parents[1] / "unit")
if _UNIT_TESTS not in sys.path:
    sys.path.insert(0, _UNIT_TESTS)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_tools
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from test_rails_runner import _knowledge_snapshot, _one_sample_adapter, _plan

TASK = "saea-tool-task-contract-v1"


def _program():
    return replace(
        rc.default_phase_program("phase-draft-revise-v1"),
        stop_rule="always-run-full-program",
    )


def _material(name, context, _sealed):
    return PhaseMaterial(
        instruction=f"Do {name}",
        response_format=None,
        contact_id=f"{name}:{context.sample_id}",
        purpose=name,
    ).validate()


def _config(mode):
    entry = {"mode": mode, "allowed_tools": [TASK], "knowledge_views": ["text"]}
    if mode == "fixed":
        entry["fixed_action"] = {"tool_id": TASK, "arguments": {}}
    return {"phase_tools": {"draft": entry}}


class _Client:
    def __init__(self, response_factory):
        self.calls = []
        self.response_factory = response_factory

    def complete(self, messages, **options):
        self.calls.append((messages, options))
        return self.response_factory(len(self.calls), options)


def test_fixed_mode_runs_actual_tool_then_solver_and_preserves_final_answer(
    tmp_path, monkeypatch
):
    calls = []
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    original = ToolEntry.call

    def observed(self, *args, **kwargs):
        calls.append(self.manifest.tool_id)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ToolEntry, "call", observed)
    program = _program()
    dispatcher = phase_tools.build_phase_tools(
        _config("fixed"), program, snapshot=_knowledge_snapshot()
    )
    client = _Client(
        lambda index, _options: (
            "planner response" if index == 1 else "final Solver answer"
        )
    )
    plan = _plan(run_id="SAEA-E-TEST-phase-tools-fixed")
    summary = run_continuous_program(
        program=program,
        adapter=_one_sample_adapter(),
        plan=plan,
        data_root=tmp_path,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "p1", "sha256": "a" * 64}},
        trace_sink=TraceBuffer(plan.run_id),
        decoding_params={},
        material_for_phase=_material,
        tools_for_phase=dispatcher,
        agent_executor_id="openjiuwen-workflow-v1",
    )
    assert calls == [TASK]
    assert len(client.calls) == 2
    successor_states = client.calls[1][1]["agent_state"]
    tool_states = [
        state for state in successor_states if state["state_kind"] == "tool-result"
    ]
    assert len(tool_states) == 1
    assert json.loads(tool_states[0]["content"])["result"] == {
        "task_contract": "task-contract-for-s1"
    }
    assert summary.results[0].final_response_text == "final Solver answer"
    assert any(
        state.state_kind == "tool-result" for state in summary.results[0].agent_states
    )
    assert "planner response" not in summary.results[0].final_response_text


def test_core_choice_action_uses_dynamic_query_hash_and_unknown_refuses_before_second_contact(
    tmp_path, monkeypatch
):
    from openjiuwen.core.common.exception.errors import ExecutionError
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    tool_calls = []
    original = ToolEntry.call

    def observed(self, *args, **kwargs):
        tool_calls.append(self.manifest.tool_id)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ToolEntry, "call", observed)
    program = _program()
    dispatcher = phase_tools.build_phase_tools(
        _config("core-choice"), program, snapshot=_knowledge_snapshot()
    )
    client_calls = []

    class Client:
        def complete(self, messages, **options):
            client_calls.append((messages, options))
            match = re.search(
                r"query_state_sha256: ([0-9a-f]{64})",
                options.get("contact_instruction", ""),
            )
            assert match
            return json.dumps(
                {
                    "tool_id": "unknown",
                    "arguments": {},
                    "query_state_sha256": match.group(1),
                }
            )

    plan = _plan(run_id="SAEA-E-TEST-phase-tools-choice")
    with pytest.raises(
        ExecutionError, match="action tool is outside the configured allowlist"
    ):
        run_continuous_program(
            program=program,
            adapter=_one_sample_adapter(),
            plan=plan,
            data_root=tmp_path,
            core_client=Client(),
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={"s1": {"packet_id": "p1", "sha256": "a" * 64}},
            trace_sink=TraceBuffer(plan.run_id),
            decoding_params={},
            material_for_phase=_material,
            tools_for_phase=dispatcher,
            agent_executor_id="openjiuwen-workflow-v1",
        )
    assert len(client_calls) == 1
    assert tool_calls == []


@pytest.mark.parametrize("mode", ["fixed", "core-choice"])
def test_knowledge_action_executes_shared_supply_and_changes_solver_evidence(
    tmp_path, mode, monkeypatch
):
    from speech_aware_evidence_acquisition.rails.knowledge import (
        RankResult,
        RankedFacet,
        FusionDecision,
    )
    from speech_aware_evidence_acquisition.rails.tools import ToolEntry

    knowledge = phase_tools.PHASE_KNOWLEDGE_TOOL
    p = rc.default_phase_program("phase-task-tools-then-solve-v1")
    entry = {"mode": mode, "allowed_tools": [knowledge], "knowledge_views": ["text"]}
    if mode == "fixed":
        entry["fixed_action"] = {"tool_id": knowledge, "arguments": {"view": "text"}}
    snapshot = _knowledge_snapshot()
    provider_calls = []
    tool_calls = []
    original = ToolEntry.call

    def observed(self, *args, **kw):
        tool_calls.append(self.manifest.tool_id)
        return original(self, *args, **kw)

    monkeypatch.setattr(ToolEntry, "call", observed)

    def supply(phase, ctx):
        provider_calls.append((phase, ctx.sample_id))
        rank = RankResult(
            snapshot_sha256=snapshot.content_hash(),
            query_state_sha256=ctx.query_state.content_hash(),
            ranking_policy_id="test-rank",
            candidates=(RankedFacet("operation:dim", 1.0),),
        ).validate()
        decision = FusionDecision(
            snapshot_sha256=snapshot.content_hash(),
            query_state_sha256=ctx.query_state.content_hash(),
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id="test-fuse",
            supporting_facet_ids=("operation:dim",),
            selected_value_ids=("value:dim-light",),
        ).validate()
        return rc.PhaseSupply(rank_result=rank, fusion_decision=decision)

    sink = TraceBuffer(_plan().run_id)
    dispatcher = phase_tools.build_phase_tools(
        {"phase_tools": {"plan": entry}},
        p,
        snapshot=snapshot,
        supply_for_phase=supply,
        trace_sink=sink,
    )

    def respond(index, options):
        if index == 2:
            return "final Solver answer"
        if mode == "fixed":
            return "task hypothesis"
        state_hash = re.search(
            r"query_state_sha256: ([0-9a-f]{64})", options["contact_instruction"]
        ).group(1)
        return json.dumps(
            {
                "tool_id": knowledge,
                "arguments": {"view": "text"},
                "query_state_sha256": state_hash,
            }
        )

    client = _Client(respond)
    summary = run_continuous_program(
        program=p,
        adapter=_one_sample_adapter(),
        plan=_plan(),
        data_root=tmp_path,
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings={"s1": {"packet_id": "p1", "sha256": "a" * 64}},
        trace_sink=sink,
        decoding_params={},
        material_for_phase=_material,
        tools_for_phase=dispatcher,
        supply_for_phase=supply,
        agent_executor_id="openjiuwen-workflow-v1",
    )
    assert provider_calls == [("solve", "s1")] and tool_calls == [knowledge]
    assert summary.results[0].final_response_text == "final Solver answer"
    first = client.calls[0][0][1]["content"]
    second = client.calls[1][0][1]["content"]
    assert not any(part.get("evidence_id") == "value:dim-light" for part in first)
    evidence = [part for part in second if part.get("evidence_id") == "value:dim-light"]
    assert len(evidence) == 1 and evidence[0]["text"] == snapshot.values[0].content
    assert any(
        state["state_kind"] == "tool-result"
        for state in client.calls[1][1]["agent_state"]
    )
    assert dispatcher.receipt()["completed"] == 1
