"""Check native framework contracts with synthetic models and tools only."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any

import openjiuwen
from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm.schema.message import AssistantMessage
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.foundation.tool import LocalFunction, ToolCard
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner import Runner
from openjiuwen.core.runner.callback.errors import AbortError
from openjiuwen.core.session.node import Session
from openjiuwen.core.single_agent import AgentCard, ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.rail.base import AgentRail
from openjiuwen.core.workflow import End, Start, Workflow, WorkflowComponent, create_workflow_session

logging.disable(logging.CRITICAL)


def tool_card(name: str) -> ToolCard:
    return ToolCard(
        id=name,
        name=name,
        description=f"Synthetic {name} analytical tool.",
        input_params={
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        stateless=True,
        idempotent=True,
    )


class ScriptedModel:
    def __init__(self, responses: list[AssistantMessage]):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def invoke(self, messages, *, tools=None, **kwargs):
        self.calls.append(
            {
                "roles": [message.role for message in messages],
                "contents": [message.content for message in messages],
                "tool_call_ids": [getattr(message, "tool_call_id", None) for message in messages],
                "tool_names": [tool.name for tool in (tools or [])],
            }
        )
        if not self.responses:
            raise AssertionError("synthetic model response script exhausted")
        return self.responses.pop(0)


def call(name: str, call_id: str, value: int) -> AssistantMessage:
    return AssistantMessage(
        content="",
        tool_calls=[ToolCall(id=call_id, type="function", name=name, arguments=json.dumps({"value": value}))],
    )


def answer(text: str) -> AssistantMessage:
    return AssistantMessage(content=text)


def agent(name: str, model: ScriptedModel, *, max_iterations: int) -> ReActAgent:
    instance = ReActAgent(card=AgentCard(id=name, name=name, description=f"Synthetic {name}."))
    instance.configure(
        ReActAgentConfig(
            model_name="synthetic-no-contact",
            max_iterations=max_iterations,
            parallel_tool_calls=False,
            prompt_template=[{"role": "system", "content": "Use only synthetic evidence."}],
        )
    )
    instance.set_llm(model)
    return instance


class DenyToolRail(AgentRail):
    def __init__(self, denied_name: str):
        self.denied_name = denied_name
        self.seen: list[str] = []

    async def before_tool_call(self, ctx):
        name = ctx.inputs.tool_call.name
        self.seen.append(name)
        if name == self.denied_name:
            cause = PermissionError(f"Tool {name} is outside this agent's authority.")
            raise AbortError("synthetic authority rejection", cause=cause)


class AgentComponent(WorkflowComponent):
    def __init__(self, instance: ReActAgent, component_name: str):
        super().__init__()
        self.instance = instance
        self.component_name = component_name
        self.invocations = 0

    async def invoke(self, inputs: Input, session: Session, context: ModelContext) -> Output:
        self.invocations += 1
        result = await self.instance.invoke(
            {"query": str(inputs["query"]), "conversation_id": f"workflow-{self.component_name}"}
        )
        return {"answer": result["output"]}


async def prove() -> dict[str, Any]:
    analytical_calls: list[int] = []

    def analyze(value: int):
        analytical_calls.append(value)
        return {"doubled": value * 2}

    analytical_tool = LocalFunction(card=tool_card("audit_analyze"), func=analyze)
    roundtrip_model = ScriptedModel(
        [call("audit_analyze", "call-roundtrip", 4), answer("analysis complete")]
    )
    roundtrip_agent = agent("audit-roundtrip-agent", roundtrip_model, max_iterations=3)
    add_result = roundtrip_agent.ability_manager.add_ability(
        analytical_tool.card, analytical_tool
    )
    roundtrip_result = await roundtrip_agent.invoke(
        {"query": "Analyze four.", "conversation_id": "audit-roundtrip"}
    )
    assert add_result.added
    assert roundtrip_result == {"output": "analysis complete", "result_type": "answer"}
    assert analytical_calls == [4]
    assert roundtrip_model.calls[0]["tool_names"] == ["audit_analyze"]
    second = roundtrip_model.calls[1]
    assert second["roles"][-2:] == ["assistant", "tool"]
    assert second["tool_call_ids"][-1] == "call-roundtrip"
    assert "doubled" in second["contents"][-1]

    hidden_calls: list[int] = []

    def hidden(value: int):
        hidden_calls.append(value)
        return {"hidden": value}

    hidden_tool = LocalFunction(card=tool_card("audit_hidden_global"), func=hidden)
    Runner.resource_mgr.add_tool(hidden_tool, refresh=True)
    hidden_model = ScriptedModel(
        [call("audit_hidden_global", "call-hidden", 7), answer("hidden completed")]
    )
    hidden_agent = agent("audit-hidden-agent", hidden_model, max_iterations=3)
    hidden_result = await hidden_agent.invoke(
        {"query": "Request an unadvertised tool.", "conversation_id": "audit-hidden"}
    )
    assert hidden_model.calls[0]["tool_names"] == []
    assert hidden_calls == [7]
    assert hidden_result["result_type"] == "answer"
    assert hidden_model.calls[1]["roles"][-2:] == ["assistant", "tool"]

    denied_model = ScriptedModel(
        [call("audit_hidden_global", "call-denied", 9), answer("continued after denial")]
    )
    denied_agent = agent("audit-denied-agent", denied_model, max_iterations=2)
    deny_rail = DenyToolRail("audit_hidden_global")
    await denied_agent.register_rail(deny_rail)
    denied_result = await denied_agent.invoke(
        {"query": "Try denied tool.", "conversation_id": "audit-denied"}
    )
    assert deny_rail.seen == ["audit_hidden_global"]
    assert hidden_calls == [7]
    assert denied_result == {"output": "continued after denial", "result_type": "answer"}
    assert denied_model.calls[1]["roles"][-2:] == ["assistant", "tool"]
    assert "outside this agent's authority" in denied_model.calls[1]["contents"][-1]

    capped_calls: list[int] = []

    def capped(value: int):
        capped_calls.append(value)
        return {"seen": value}

    capped_tool = LocalFunction(card=tool_card("audit_capped"), func=capped)
    capped_model = ScriptedModel([call("audit_capped", "call-capped", 1)])
    capped_agent = agent("audit-capped-agent", capped_model, max_iterations=1)
    capped_agent.ability_manager.add_ability(capped_tool.card, capped_tool)
    capped_result = await capped_agent.invoke(
        {"query": "Keep calling.", "conversation_id": "audit-capped"}
    )
    assert capped_result["result_type"] == "error"
    assert capped_result["output"] == "Max iterations reached without completion"
    assert len(capped_model.calls) == 1 and capped_calls == [1]

    reviewer_model = ScriptedModel([answer("review finished")])
    solver_model = ScriptedModel([answer("solver finished")])
    reviewer = AgentComponent(agent("audit-reviewer-agent", reviewer_model, max_iterations=1), "reviewer")
    solver = AgentComponent(agent("audit-solver-agent", solver_model, max_iterations=1), "solver")
    flow = Workflow()
    flow.set_start_comp("start", Start(), inputs_schema={"query": "$" + "{query}"})
    flow.add_workflow_comp(
        "reviewer", reviewer, inputs_schema={"query": "$" + "{start.query}"}
    )
    flow.add_workflow_comp(
        "solver", solver, inputs_schema={"query": "$" + "{reviewer.answer}"}
    )
    flow.set_end_comp("end", End(), inputs_schema={"answer": "$" + "{solver.answer}"})
    flow.add_connection("start", "reviewer")
    flow.add_connection("reviewer", "solver")
    flow.add_connection("solver", "end")
    workflow_output = await flow.invoke(
        inputs={"query": "Review then solve."}, session=create_workflow_session()
    )
    assert reviewer.invocations == 1 and solver.invocations == 1
    assert solver_model.calls[0]["contents"][-1] == "review finished"

    package = Path(openjiuwen.__file__).parent
    source_files = [
        package / "core/single_agent/agents/react_agent.py",
        package / "core/single_agent/ability_manager.py",
        package / "core/single_agent/rail/base.py",
        package / "core/runner/callback/framework.py",
        package / "core/runner/callback/errors.py",
        package / "core/foundation/tool/function/function.py",
        package / "core/workflow/workflow.py",
    ]
    pinned_sources = {
        str(path.relative_to(package)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_files
    }
    return {
        "schema": "saea-openjiuwen-native-framework-proof-v1",
        "openjiuwen_version": openjiuwen.__version__,
        "public_api": {
            "agent": "ReActAgent.configure/set_llm/invoke",
            "tool": "ToolCard/LocalFunction and AbilityManager.add_ability",
            "rail": "ReActAgent.register_rail with AgentRail.before_tool_call and AbortError",
            "private_api_required_for_tested_behavior": False,
            "workflow": "Workflow/WorkflowComponent/Start/End",
        },
        "proofs": {
            "advertised_tool_round_trip": {
                "passed": True,
                "advertised_names": roundtrip_model.calls[0]["tool_names"],
                "second_model_roles": second["roles"],
                "tool_call_id_preserved": second["tool_call_ids"][-1],
                "callback_invocations": len(analytical_calls),
            },
            "per_agent_visibility": {
                "passed": True,
                "agent_with_tool": roundtrip_model.calls[0]["tool_names"],
                "agent_without_tool": hidden_model.calls[0]["tool_names"],
            },
            "global_fallback_is_not_authority": {
                "passed": True,
                "unadvertised_callback_invocations": len(hidden_calls),
                "observation_reached_second_model_call": hidden_model.calls[1]["roles"][-1] == "tool",
            },
            "before_tool_call_rail_rejection": {
                "passed": True,
                "seen_tool_names": deny_rail.seen,
                "hidden_callback_count_before_and_after_rejection": [1, len(hidden_calls)],
                "tool_error_observation_reached_model": (
                    denied_model.calls[1]["roles"][-1] == "tool"
                ),
                "whole_react_run_aborted": False,
            },
            "max_iterations": {
                "configured": 1,
                "model_calls": len(capped_model.calls),
                "tool_calls": len(capped_calls),
                "result_type": capped_result["result_type"],
                "passed": True,
            },
            "workflow_reviewer_then_solver": {
                "passed": True,
                "reviewer_invocations": reviewer.invocations,
                "solver_invocations": solver.invocations,
                "solver_received_reviewer_output": True,
                "workflow_output_type": type(workflow_output).__name__,
            },
        },
        "limitations": [
            "A per-agent tool list controls model-visible schemas, but AbilityManager falls back to the process-global tool registry by requested name.",
            "AgentRail.before_tool_call plus public AbortError blocks before callback invocation; the ReAct tool layer converts the failure to a tool observation and continues the bounded loop.",
            "No private API was needed for the tested rejection. Supplying a custom replacement ToolMessage without raising would rely on the underscore-prefixed _skip_tool convention.",
            "ReActAgentComp does not expose set_llm; workflow injection uses a small public WorkflowComponent that calls a public ReActAgent.",
            "This proves framework behavior with deterministic fakes, not the repository service bridge, custody policy, or task efficacy.",
        ],
        "installed_source_sha256": pinned_sources,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output.resolve()
    if output.exists():
        parser.error("The output already exists; preserve the earlier proof.")
    output.parent.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(prove())
    output.write_text(
        json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "result_path": str(output),
        "result_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "proofs": {name: value["passed"] for name, value in result["proofs"].items()},
    }, sort_keys=True))
