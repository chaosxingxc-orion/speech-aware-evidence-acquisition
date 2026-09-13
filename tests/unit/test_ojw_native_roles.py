"""Model-free tests for the public OpenJiuwen native role bridge."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from dataclasses import replace

import pytest
from openjiuwen.core.foundation.tool import LocalFunction, ToolCard
from openjiuwen.core.runner import Runner

from speech_aware_evidence_acquisition.rails.core_client import CoreCompletion
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    FrozenCoreRoleModelError,
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
    build_native_role_workflow,
)


def _card(name: str) -> ToolCard:
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


def _completion(
    *,
    text: str,
    sample_id: str = "sample-1",
    contact_id: str = "contact-1",
    tool_calls: object = None,
    serial: int = 1,
) -> CoreCompletion:
    request_id = f"request-{serial}"
    return CoreCompletion(
        text=text,
        request_id=request_id,
        sample_id=sample_id,
        agent_contact_id=contact_id,
        request_sha256=hashlib.sha256(request_id.encode()).hexdigest(),
        response_sha256=hashlib.sha256(("wire-" + text).encode()).hexdigest(),
        response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        tool_calls_json=json.dumps(
            tool_calls, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode(),
    )


def _tool_call(name: str, call_id: str, arguments: str) -> list[dict[str, object]]:
    return [
        {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        }
    ]


@dataclass
class _MeteredScript:
    responses: list[CoreCompletion]
    requests: list[object] = field(default_factory=list)

    def __call__(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("metered response script exhausted")
        return self.responses.pop(0)


def test_analytical_role_uses_framework_tool_history_and_meters_every_call():
    observed: list[int] = []

    def analyze(value: int):
        observed.append(value)
        return {"doubled": value * 2}

    tool = LocalFunction(card=_card("analyze"), func=analyze)
    script = _MeteredScript(
        [
            _completion(
                text='[{"name":"analyze","arguments":{"value":4}}]',
                tool_calls=_tool_call("analyze", "call-1", '{"value":4}'),
            ),
            _completion(text="review complete", serial=2),
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review with an analytical tool only when useful.",
            max_iterations=3,
            ability_names=("analyze",),
        ),
        metered_request=script,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id="contact-1",
            evidence_pins={"packet": "a" * 64},
        ),
        abilities=(tool,),
        tool_allowed=lambda role, name: role == "reviewer" and name == "analyze",
    )

    result = asyncio.run(node.invoke_direct("Inspect the supplied state."))

    assert result == {
        "role_id": "reviewer",
        "actor_output": "review complete",
        "result_type": "answer",
        "delivery_eligible": False,
    }
    assert observed == [4]
    assert len(script.requests) == 2
    assert script.requests[0].visible_tool_names == ("analyze",)
    assert [message["role"] for message in script.requests[1].messages][-2:] == [
        "assistant",
        "tool",
    ]
    assert script.requests[1].messages[-1]["tool_call_id"] == "call-1"
    assert (
        script.requests[1].messages[-2]["tool_calls"][0]["function"]["arguments"]
        == '{"value":4}'
    )
    assert script.requests[0].context.evidence_pins == {"packet": "a" * 64}


def test_role_spec_rejects_tools_for_perception_and_solver():
    for kind in ("perception", "solver"):
        with pytest.raises(ValueError, match="must be tool-free"):
            NativeRoleNodeSpec(
                role_id=kind,
                role_kind=kind,
                prompt="Produce the role output.",
                max_iterations=1,
                ability_names=("analyze",),
            )


def test_global_unadvertised_tool_is_denied_before_callback():
    hidden_calls: list[int] = []

    def hidden(value: int):
        hidden_calls.append(value)
        return {"hidden": value}

    name = "native_role_hidden_global"
    hidden_tool = LocalFunction(card=_card(name), func=hidden)
    Runner.resource_mgr.add_tool(hidden_tool, refresh=True)
    script = _MeteredScript(
        [
            _completion(
                text="hidden request",
                tool_calls=_tool_call(name, "hidden-1", '{"value":7}'),
            ),
            _completion(text="continued after denial", serial=2),
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="planner",
            role_kind="planner",
            prompt="Plan with only your advertised tools.",
            max_iterations=2,
        ),
        metered_request=script,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="contact-1"
        ),
        tool_allowed=lambda _role, _name: False,
    )

    result = asyncio.run(node.invoke_direct("Try an unavailable action."))

    assert hidden_calls == []
    assert result["actor_output"] == "continued after denial"
    assert result["delivery_eligible"] is False
    assert len(script.requests) == 2
    assert script.requests[0].visible_tool_names == ()
    assert [message["role"] for message in script.requests[1].messages][-2:] == [
        "assistant",
        "tool",
    ]
    assert "outside role authority" in script.requests[1].messages[-1]["content"]


def test_max_iteration_error_remains_nondeliverable():
    calls: list[int] = []
    tool = LocalFunction(
        card=_card("repeat"),
        func=lambda value: calls.append(value) or {"again": True},
    )
    script = _MeteredScript(
        [
            _completion(
                text="repeat",
                tool_calls=_tool_call("repeat", "repeat-1", '{"value":1}'),
            )
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review.",
            max_iterations=1,
            ability_names=("repeat",),
        ),
        metered_request=script,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="contact-1"
        ),
        abilities=(tool,),
        tool_allowed=lambda _role, name: name == "repeat",
    )

    result = asyncio.run(node.invoke_direct("Continue until done."))

    assert result["result_type"] == "error"
    assert result["actor_output"] == "Max iterations reached without completion"
    assert result["delivery_eligible"] is False
    assert calls == [1]
    assert len(script.requests) == 1


def test_workflow_keeps_reviewer_output_intermediate_and_only_solver_delivers():
    reviewer_script = _MeteredScript([_completion(text="review finding")])
    solver_script = _MeteredScript(
        [_completion(text='{"intent":"accepted"}', serial=2)]
    )
    context = NativeRoleContactContext(
        sample_id="sample-1", agent_contact_id="contact-1"
    )
    reviewer = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review.",
            max_iterations=1,
        ),
        metered_request=reviewer_script,
        contact_context=context,
    )
    solver = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver",
            role_kind="solver",
            prompt="Solve.",
            max_iterations=1,
        ),
        metered_request=solver_script,
        contact_context=context,
        delivery_allowed=lambda role, output: (
            role == "solver" and output == '{"intent":"accepted"}'
        ),
    )
    workflow = build_native_role_workflow((reviewer, solver))

    result = asyncio.run(workflow.invoke_direct("Review then solve."))

    assert result["actors"]["reviewer"]["actor_output"] == "review finding"
    assert result["actors"]["reviewer"]["delivery_eligible"] is False
    assert result["actors"]["solver"]["delivery_eligible"] is True
    assert solver_script.requests[0].messages[-1]["content"] == "review finding"
    assert len(reviewer_script.requests) + len(solver_script.requests) == 2


def test_bridge_refuses_noncompletion_and_cross_sample_completion():
    context = NativeRoleContactContext(
        sample_id="sample-1", agent_contact_id="contact-1"
    )
    bad_type = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="Solve.", max_iterations=1
        ),
        metered_request=lambda _request: "plain text",
        contact_context=context,
    )
    with pytest.raises(FrozenCoreRoleModelError, match="CoreCompletion"):
        asyncio.run(bad_type.invoke_direct("Solve."))

    wrong_sample = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="Solve.", max_iterations=1
        ),
        metered_request=lambda _request: _completion(
            text="answer", sample_id="sample-2"
        ),
        contact_context=context,
    )
    with pytest.raises(FrozenCoreRoleModelError, match="binding"):
        asyncio.run(wrong_sample.invoke_direct("Solve."))

    missing_source = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="Solve.", max_iterations=1
        ),
        metered_request=lambda _request: replace(
            _completion(text="answer"), request_sha256=""
        ),
        contact_context=context,
    )
    with pytest.raises(FrozenCoreRoleModelError, match="source binding"):
        asyncio.run(missing_source.invoke_direct("Solve."))
