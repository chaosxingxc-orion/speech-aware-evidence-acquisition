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
    FrozenCoreRoleFiniteCompletionError,
    FrozenCoreRoleModel,
    FrozenCoreRoleModelError,
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
    build_native_role_workflow,
    project_native_assistant_message,
    restore_native_assistant_wire_message,
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
    wire_content: str | None = None,
    finish_reason: str | None = None,
) -> CoreCompletion:
    request_id = f"request-{serial}"
    if finish_reason is None:
        finish_reason = "tool_calls" if tool_calls else "stop"
    message = {
        "role": "assistant",
        "content": text if wire_content is None else wire_content,
    }
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    wire = json.dumps(
        {
            "choices": [{"message": message, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
        separators=(",", ":"),
    ).encode()
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
        wire_response_bytes=wire,
    )


def _tool_call(name: str, call_id: str, arguments: str) -> list[dict[str, object]]:
    return [
        {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": arguments},
        }
    ]


def _contact_receipt(
    *, text: str, contact_id: str, serial: int
) -> dict[str, str]:
    request_id = f"request-{serial}"
    return {
        "agent_contact_id": contact_id,
        "request_id": request_id,
        "request_sha256": hashlib.sha256(request_id.encode()).hexdigest(),
        "response_sha256": hashlib.sha256(("wire-" + text).encode()).hexdigest(),
        "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }


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
                text="I will inspect the supplied value.",
                tool_calls=_tool_call("analyze", "call-1", '{"value":4}'),
                wire_content="I will inspect the supplied value.",
            ),
            _completion(text="review complete", contact_id="contact-2", serial=2),
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
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id=f"contact-{index + 1}",
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
        "execution_receipt": {
            "contacts": [
                _contact_receipt(
                    text="I will inspect the supplied value.",
                    contact_id="contact-1",
                    serial=1,
                ),
                _contact_receipt(
                    text="review complete", contact_id="contact-2", serial=2
                ),
            ],
            "final_contact": _contact_receipt(
                text="review complete", contact_id="contact-2", serial=2
            ),
        },
    }
    assert observed == [4]
    assert len(script.requests) == 2
    assert [request.context.agent_contact_id for request in script.requests] == [
        "contact-1",
        "contact-2",
    ]
    assert script.requests[0].visible_tool_names == ("analyze",)
    assert [message["role"] for message in script.requests[1].messages][-2:] == [
        "assistant",
        "tool",
    ]
    assert (
        script.requests[1].messages[-2]["content"]
        == "I will inspect the supplied value."
    )
    assert script.requests[1].messages[-1]["tool_call_id"] == "call-1"
    assert (
        script.requests[1].messages[-2]["tool_calls"][0]["function"]["arguments"]
        == '{"value":4}'
    )
    assert script.requests[0].context.evidence_pins == {"packet": "a" * 64}


def test_successive_same_role_nodes_keep_tool_callbacks_instance_bound():
    observed: list[tuple[str, int]] = []

    def node(
        label: str,
        abilities: tuple[str, ...],
        selected: str,
        value: int,
    ) -> NativeRoleNode:
        resources = tuple(
            LocalFunction(
                card=_card(name),
                func=lambda value, *, _name=name: observed.append(
                    (f"{label}:{_name}", value)
                )
                or {"label": label, "value": value},
            )
            for name in abilities
        )
        role_node = NativeRoleNode(
            spec=NativeRoleNodeSpec(
                role_id="reviewer",
                role_kind="reviewer",
                prompt=f"Review with the {label} analytical tools.",
                max_iterations=2,
                ability_names=abilities,
            ),
            metered_request=_MeteredScript(
                [
                    _completion(
                        text=f"{label} tool call",
                        sample_id=f"sample-{label}",
                        tool_calls=_tool_call(
                            selected,
                            f"call-{label}",
                            json.dumps({"value": value}),
                        ),
                        wire_content=f"{label} tool call",
                    ),
                    _completion(
                        text=f"{label} complete",
                        sample_id=f"sample-{label}",
                        contact_id="contact-2",
                        serial=2,
                    ),
                ]
            ),
            contact_context_provider=lambda index: NativeRoleContactContext(
                sample_id=f"sample-{label}",
                agent_contact_id=f"contact-{index + 1}",
                evidence_pins={"packet": ("a" if label == "first" else "b") * 64},
            ),
            abilities=resources,
            tool_allowed=lambda role, name: (
                role == "reviewer" and name in abilities
            ),
        )
        assert tuple(resource.card.id for resource in resources) == abilities
        assert all(resource.card.stateless for resource in resources)
        return role_node

    first = node("first", ("analyze",), "analyze", 1)
    second = node("second", ("analyze", "inspect"), "analyze", 2)

    assert (
        asyncio.run(first.invoke_direct("Inspect the first state."))["actor_output"]
        == "first complete"
    )
    assert (
        asyncio.run(second.invoke_direct("Inspect the second state."))["actor_output"]
        == "second complete"
    )
    assert observed == [("first:analyze", 1), ("second:analyze", 2)]


def test_close_removes_only_the_node_owned_tool_and_rail_and_is_idempotent():
    def node(label: str) -> NativeRoleNode:
        tool = LocalFunction(
            card=_card("inspect"),
            func=lambda value: {"label": label, "value": value},
        )
        return NativeRoleNode(
            spec=NativeRoleNodeSpec(
                role_id="reviewer",
                role_kind="reviewer",
                prompt=f"Review the {label} state.",
                max_iterations=1,
                ability_names=("inspect",),
            ),
            metered_request=_MeteredScript(
                [
                    _completion(
                        text=f"{label} complete",
                        sample_id=f"sample-{label}",
                    )
                ]
            ),
            contact_context=NativeRoleContactContext(
                sample_id=f"sample-{label}", agent_contact_id="contact-1"
            ),
            abilities=(tool,),
            tool_allowed=lambda role, name: (
                role == "reviewer" and name == "inspect"
            ),
        )

    first = node("first")
    second = node("second")
    first_tool_id = f"inspect_{first._agent.card.id}"
    second_tool_id = f"inspect_{second._agent.card.id}"
    rail_event = next(iter(first._rail.get_callbacks()))

    async def exercise():
        try:
            await first.invoke_direct("Inspect the first state.")
            await second.invoke_direct("Inspect the second state.")
            assert Runner.resource_mgr.get_tool(first_tool_id) is not None
            assert Runner.resource_mgr.get_tool(second_tool_id) is not None
            assert first._agent.agent_callback_manager.has_hooks(rail_event)
            assert second._agent.agent_callback_manager.has_hooks(rail_event)

            await first.close()
            await first.close()

            assert Runner.resource_mgr.get_tool(first_tool_id) is None
            assert Runner.resource_mgr.get_tool(second_tool_id) is not None
            assert not first._agent.agent_callback_manager.has_hooks(rail_event)
            assert second._agent.agent_callback_manager.has_hooks(rail_event)
        finally:
            await first.close()
            await second.close()

    asyncio.run(exercise())


def test_close_after_role_error_removes_node_owned_resources():
    tool = LocalFunction(
        card=_card("inspect_after_error"),
        func=lambda value: {"value": value},
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review the state.",
            max_iterations=1,
            ability_names=("inspect_after_error",),
        ),
        metered_request=lambda _request: _completion(
            text="wrong sample", sample_id="sample-2"
        ),
        contact_context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="contact-1"
        ),
        abilities=(tool,),
        tool_allowed=lambda role, name: (
            role == "reviewer" and name == "inspect_after_error"
        ),
    )
    tool_id = f"inspect_after_error_{node._agent.card.id}"
    rail_event = next(iter(node._rail.get_callbacks()))

    async def exercise():
        try:
            with pytest.raises(FrozenCoreRoleModelError, match="binding"):
                await node.invoke_direct("Review the state.")
            assert Runner.resource_mgr.get_tool(tool_id) is not None
            assert node._agent.agent_callback_manager.has_hooks(rail_event)

            await node.close()

            assert Runner.resource_mgr.get_tool(tool_id) is None
            assert not node._agent.agent_callback_manager.has_hooks(rail_event)
        finally:
            await node.close()

    asyncio.run(exercise())


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
            _completion(
                text="continued after denial", contact_id="contact-2", serial=2
            ),
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
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}"
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
    assert result["execution_receipt"] == {
        "contacts": [
            _contact_receipt(text="repeat", contact_id="contact-1", serial=1),
        ],
        "final_contact": _contact_receipt(
            text="repeat", contact_id="contact-1", serial=1
        ),
    }
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


def test_repeated_node_invocations_use_fresh_framework_history():
    script = _MeteredScript(
        [
            _completion(text="first answer"),
            _completion(text="second answer", contact_id="contact-2", serial=2),
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="Solve.", max_iterations=1
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}"
        ),
    )

    first = asyncio.run(node.invoke_direct("First independent query."))
    second = asyncio.run(node.invoke_direct("Second independent query."))

    assert first["actor_output"] == "first answer"
    assert second["actor_output"] == "second answer"
    assert len(script.requests) == 2
    assert [[message["role"] for message in request.messages] for request in script.requests] == [
        ["system", "user"],
        ["system", "user"],
    ]
    assert script.requests[0].messages[-1]["content"] == "First independent query."
    assert script.requests[1].messages[-1]["content"] == "Second independent query."
    assert first["execution_receipt"] == {
        "contacts": [
            _contact_receipt(
                text="first answer", contact_id="contact-1", serial=1
            ),
        ],
        "final_contact": _contact_receipt(
            text="first answer", contact_id="contact-1", serial=1
        ),
    }
    assert second["execution_receipt"] == {
        "contacts": [
            _contact_receipt(
                text="second answer", contact_id="contact-2", serial=2
            ),
        ],
        "final_contact": _contact_receipt(
            text="second answer", contact_id="contact-2", serial=2
        ),
    }


def test_fixed_contact_context_refuses_a_second_episode_before_callback():
    script = _MeteredScript([_completion(text="first answer")])
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver", role_kind="solver", prompt="Solve.", max_iterations=1
        ),
        metered_request=script,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="contact-1"
        ),
    )

    assert asyncio.run(node.invoke_direct("First."))["result_type"] == "answer"
    with pytest.raises(FrozenCoreRoleModelError, match="fixed contact context is exhausted"):
        asyncio.run(node.invoke_direct("Second."))
    assert len(script.requests) == 1


@pytest.mark.parametrize("bad_context", [None, "duplicate"])
def test_context_provider_exhaustion_or_duplicate_refuses_before_callback(bad_context):
    calls = []
    tool_name = f"continue_{bad_context or 'missing'}"
    tool = LocalFunction(
        card=_card(tool_name),
        func=lambda value: calls.append(value) or {"continue": True},
    )
    first_context = NativeRoleContactContext(
        sample_id="sample-1", agent_contact_id="contact-1"
    )

    def contexts(index):
        if index == 0 or bad_context == "duplicate":
            return first_context
        return None

    script = _MeteredScript(
        [
            _completion(
                text="Continue.",
                tool_calls=_tool_call(tool_name, "continue-1", '{"value":1}'),
            )
        ]
    )
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review.",
            max_iterations=2,
            ability_names=(tool_name,),
        ),
        metered_request=script,
        contact_context_provider=contexts,
        abilities=(tool,),
        tool_allowed=lambda _role, name: name == tool_name,
    )

    match = "repeated agent_contact_id" if bad_context == "duplicate" else "no registered context"
    with pytest.raises(FrozenCoreRoleModelError, match=match):
        asyncio.run(node.invoke_direct("Review twice."))
    assert calls == [1]
    assert len(script.requests) == 1


def test_role_requires_wire_metadata_and_rejects_terminal_saturation():
    context = NativeRoleContactContext(
        sample_id="sample-1", agent_contact_id="contact-1"
    )
    missing_wire = _completion(text="answer")
    missing_wire = replace(missing_wire, wire_response_bytes=None)
    model = FrozenCoreRoleModel(
        role_id="solver",
        metered_request=lambda _request: missing_wire,
        context=context,
    )
    with pytest.raises(FrozenCoreRoleModelError, match="wire metadata") as missing:
        asyncio.run(model.invoke(
            ({"role": "user", "content": "Solve."},),
            tools=(),
        ))
    assert not isinstance(missing.value, FrozenCoreRoleFiniteCompletionError)

    tool_calls = _tool_call("analyze", "call-length", '{"value":1}')
    invoked: list[int] = []
    saturated = _completion(
        text='[{"name":"analyze","arguments":{"value":1}}]',
        tool_calls=tool_calls,
        finish_reason="length",
    )
    saturated_node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review.",
            max_iterations=2,
            ability_names=("analyze",),
        ),
        metered_request=lambda _request: saturated,
        contact_context=context,
        abilities=(
            LocalFunction(
                card=_card("analyze"),
                func=lambda value: invoked.append(value) or {"accepted": True},
            ),
        ),
        tool_allowed=lambda role, name: role == "reviewer" and name == "analyze",
    )
    with pytest.raises(FrozenCoreRoleFiniteCompletionError, match="length") as caught:
        asyncio.run(saturated_node.invoke_direct("Review."))
    assert caught.value.completion is saturated
    assert caught.value.role_id == "reviewer"
    assert caught.value.execution_receipt["final_contact"]["request_id"] == saturated.request_id
    assert len(caught.value.execution_receipt["contacts"]) == 1
    assert caught.value.finish_reason == "length"
    assert caught.value.original_message == saturated.original_message
    assert caught.value.request_sha256 == saturated.request_sha256
    assert caught.value.response_sha256 == saturated.response_sha256
    assert caught.value.response_text_sha256 == saturated.response_text_sha256
    assert invoked == []


@pytest.mark.parametrize("finish_reason", ["length", "content_filter"])
def test_finite_solver_completion_cannot_reach_delivery(finish_reason):
    delivered: list[str] = []
    terminal_completion = _completion(
        text="partial answer",
        finish_reason=finish_reason,
    )
    terminal_node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="solver",
            role_kind="solver",
            prompt="Solve.",
            max_iterations=1,
        ),
        metered_request=lambda _request: terminal_completion,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id="contact-1",
        ),
        delivery_allowed=lambda _role, output: delivered.append(output) or True,
    )

    with pytest.raises(
        FrozenCoreRoleFiniteCompletionError,
        match=finish_reason,
    ) as caught:
        asyncio.run(terminal_node.invoke_direct("Deliver the answer."))

    assert caught.value.completion is terminal_completion
    assert caught.value.finish_reason == finish_reason
    assert delivered == []


@pytest.mark.parametrize("finish_reason", ["length", "content_filter"])
def test_finite_completion_error_preserves_exact_source_completion(finish_reason):
    completion = _completion(
        text="finite output",
        finish_reason=finish_reason,
        serial=7,
    )

    with pytest.raises(FrozenCoreRoleFiniteCompletionError) as caught:
        project_native_assistant_message(completion)

    error = caught.value
    assert isinstance(error, FrozenCoreRoleModelError)
    assert error.completion is completion
    assert error.finish_reason == finish_reason
    assert error.original_message == completion.original_message
    assert error.request_sha256 == completion.request_sha256
    assert error.response_sha256 == completion.response_sha256
    assert error.response_text_sha256 == completion.response_text_sha256


def test_finite_completion_is_classified_before_partial_tool_call_parsing():
    partial_call = _completion(
        text="partial call",
        tool_calls=[{"id": "unfinished"}],
        finish_reason="length",
    )

    with pytest.raises(FrozenCoreRoleFiniteCompletionError) as caught:
        project_native_assistant_message(partial_call)

    assert caught.value.completion is partial_call


@pytest.mark.parametrize("finish_reason", [[], {}])
def test_malformed_finish_metadata_remains_a_generic_fatal_error(finish_reason):
    completion = _completion(text="invalid metadata", finish_reason=finish_reason)
    with pytest.raises(FrozenCoreRoleModelError, match="unsupported") as caught:
        project_native_assistant_message(completion)
    assert not isinstance(caught.value, FrozenCoreRoleFiniteCompletionError)


def test_malformed_wire_content_is_not_a_finite_completion():
    completion = _completion(text="invalid content", wire_content=123, finish_reason="length")
    with pytest.raises(FrozenCoreRoleModelError, match="content") as caught:
        project_native_assistant_message(completion)
    assert not isinstance(caught.value, FrozenCoreRoleFiniteCompletionError)


def test_unknown_finish_and_invalid_source_are_not_finite_completion_errors():
    unknown = _completion(text="answer", finish_reason="server_error")
    with pytest.raises(FrozenCoreRoleModelError, match="unsupported") as caught:
        project_native_assistant_message(unknown)
    assert not isinstance(caught.value, FrozenCoreRoleFiniteCompletionError)

    invalid_source = replace(
        _completion(text="partial", finish_reason="length"),
        response_sha256="",
    )
    with pytest.raises(FrozenCoreRoleModelError, match="source binding") as invalid:
        project_native_assistant_message(invalid_source)
    assert not isinstance(invalid.value, FrozenCoreRoleFiniteCompletionError)

    wrong_sample = _completion(
        text="partial",
        sample_id="sample-2",
        finish_reason="length",
    )
    model = FrozenCoreRoleModel(
        role_id="solver",
        metered_request=lambda _request: wrong_sample,
        context=NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id="contact-1",
        ),
    )
    with pytest.raises(FrozenCoreRoleModelError, match="binding") as mismatch:
        asyncio.run(
            model.invoke(
                ({"role": "user", "content": "Solve."},),
                tools=(),
            )
        )
    assert not isinstance(mismatch.value, FrozenCoreRoleFiniteCompletionError)


def test_role_preserves_structured_wire_content_supported_by_assistant_message():
    completion = _completion(
        text="normalized scorer text",
        wire_content=[{"type": "text", "text": "structured assistant content"}],
    )
    model = FrozenCoreRoleModel(
        role_id="solver",
        metered_request=lambda _request: completion,
        context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="contact-1"
        ),
    )

    message = asyncio.run(model.invoke(
        ({"role": "user", "content": "Solve."},),
        tools=(),
    ))

    assert message.content == [{"type": "text", "text": "structured assistant content"}]
    assert message.content != completion.text


def test_null_tool_content_round_trips_only_through_preserved_wire_binding():
    calls = _tool_call("analyze", "call-null", '{"value":1}')
    completion = _completion(
        text='[{"name":"analyze","arguments":{"value":1}}]',
        tool_calls=calls,
    )
    wire = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        separators=(",", ":"),
    ).encode()
    completion = replace(completion, wire_response_bytes=wire)

    projected = project_native_assistant_message(completion)
    serialized = projected.model_dump(mode="json", exclude_none=True)
    restored = restore_native_assistant_wire_message(projected, completion=completion)
    through_model = asyncio.run(
        FrozenCoreRoleModel(
            role_id="reviewer",
            metered_request=lambda _request: completion,
            context=NativeRoleContactContext(
                sample_id="sample-1", agent_contact_id="contact-1"
            ),
        ).invoke(
            ({"role": "user", "content": "Review."},),
            tools=({"name": "analyze"},),
        )
    )

    assert projected.content == ""
    assert through_model.model_dump(mode="json", exclude_none=True) == serialized
    assert serialized["content"] == ""
    assert serialized["tool_calls"][0]["id"] == "call-null"
    assert serialized["tool_calls"][0]["function"]["arguments"] == '{"value":1}'
    assert restored["content"] is None
    assert restored["tool_calls"] == calls
    assert completion.wire_response_bytes == wire


@pytest.mark.parametrize(
    ("wire_content", "expected"),
    [
        ("", ""),
        ([{"type": "text", "text": "structured"}], [{"type": "text", "text": "structured"}]),
    ],
)
def test_empty_and_structured_content_round_trip_without_null_inference(
    wire_content, expected
):
    completion = _completion(text="normalized", wire_content=wire_content)

    projected = project_native_assistant_message(completion)
    restored = restore_native_assistant_wire_message(projected, completion=completion)

    assert projected.content == expected
    assert restored["content"] == expected


def test_null_projection_refuses_tampered_content_calls_and_source_binding():
    calls = _tool_call("analyze", "call-null", '{"value":1}')
    completion = _completion(text="normalized", tool_calls=calls)
    document = json.loads(completion.wire_response_bytes)
    document["choices"][0]["message"]["content"] = None
    completion = replace(
        completion,
        wire_response_bytes=json.dumps(document, separators=(",", ":")).encode(),
    )
    projected = project_native_assistant_message(completion)
    changed_content = projected.model_copy(update={"content": "" + "tampered"})
    changed_calls = projected.model_copy(
        update={
            "tool_calls": [
                projected.tool_calls[0].model_copy(update={"arguments": '{"value":2}'})
            ]
        }
    )

    with pytest.raises(FrozenCoreRoleModelError, match="projected content"):
        restore_native_assistant_wire_message(changed_content, completion=completion)
    with pytest.raises(FrozenCoreRoleModelError, match="projected content"):
        restore_native_assistant_wire_message(changed_calls, completion=completion)
    with pytest.raises(FrozenCoreRoleModelError, match="source binding"):
        restore_native_assistant_wire_message(
            projected, completion=replace(completion, request_sha256="")
        )


@pytest.mark.parametrize("reserve", [False, True])
def test_final_report_tool_scope_resets_per_framework_invocation(reserve):
    calls = []
    responses = []
    for index in range(6):
        final = index % 3 == 2
        responses.append(_completion(
            text="report" if final else "inspect",
            contact_id=f"contact-{index + 1}", serial=index + 1,
            tool_calls=None if final else _tool_call("analyze", f"call-{index}", '{"value":1}'),
        ))
    script = _MeteredScript(responses)
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer", role_kind="reviewer", prompt="Review and report.",
            max_iterations=3, ability_names=("analyze",), reserve_final_report=reserve,
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}",
        ),
        abilities=(LocalFunction(
            card=_card("analyze"), func=lambda value: calls.append(value) or {"evidence": value},
        ),),
        tool_allowed=lambda _role, name: name == "analyze",
    )

    async def invoke_twice():
        try:
            return [await node.invoke_direct("First review."), await node.invoke_direct("Second review.")]
        finally:
            await node.close()

    results = asyncio.run(invoke_twice())
    assert [item["result_type"] for item in results] == ["answer", "answer"]
    assert calls == [1, 1, 1, 1]
    expected = [("analyze",), ("analyze",), () if reserve else ("analyze",)] * 2
    assert [request.visible_tool_names for request in script.requests] == expected
    for index in (2, 5):
        assert sum(message["role"] == "tool" for message in script.requests[index].messages) == 2


def test_final_report_authority_refuses_noncompliant_third_tool_invocation():
    calls = []
    responses = [
        _completion(
            text="inspect",
            contact_id=f"contact-{index + 1}",
            serial=index + 1,
            tool_calls=_tool_call("analyze", f"call-{index}", '{"value":1}'),
        )
        for index in range(3)
    ]
    script = _MeteredScript(responses)
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review and report.",
            max_iterations=3,
            ability_names=("analyze",),
            reserve_final_report=True,
        ),
        metered_request=script,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"contact-{index + 1}",
        ),
        abilities=(
            LocalFunction(
                card=_card("analyze"),
                func=lambda value: calls.append(value) or {"evidence": value},
            ),
        ),
        tool_allowed=lambda _role, name: name == "analyze",
    )

    async def invoke_once():
        try:
            return await node.invoke_direct("Review.")
        finally:
            await node.close()

    result = asyncio.run(invoke_once())
    assert result["result_type"] == "error"
    assert calls == [1, 1]
    assert [request.visible_tool_names for request in script.requests] == [
        ("analyze",),
        ("analyze",),
        (),
    ]


@pytest.mark.parametrize("kwargs", [
    {"max_iterations": 1, "ability_names": ("analyze",), "reserve_final_report": True},
    {"max_iterations": 3, "ability_names": (), "reserve_final_report": True},
    {"max_iterations": 3, "ability_names": ("analyze",), "reserve_final_report": 1},
])
def test_final_report_reservation_rejects_invalid_role_shapes(kwargs):
    with pytest.raises(ValueError, match="final report reservation"):
        NativeRoleNodeSpec(role_id="reviewer", role_kind="reviewer", prompt="Review.", **kwargs)


def test_finite_exception_framework_copy_preserves_exact_completion():
    import copy
    completion = _completion(text="partial", finish_reason="length")
    with pytest.raises(FrozenCoreRoleFiniteCompletionError) as caught:
        project_native_assistant_message(completion)
    copied = copy.deepcopy(caught.value)
    assert copied.completion is completion
    assert copied.finish_reason == "length"
    assert copied.original_message == completion.original_message


def test_custody_error_wrapping_finite_completion_is_not_downgraded():
    from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
        _finite_error_in_chain,
    )
    try:
        try:
            project_native_assistant_message(_completion(text="partial", finish_reason="length"))
        except FrozenCoreRoleFiniteCompletionError as error:
            raise FrozenCoreRoleModelError("custody lost") from error
    except FrozenCoreRoleModelError as caught:
        assert _finite_error_in_chain(caught) is None
