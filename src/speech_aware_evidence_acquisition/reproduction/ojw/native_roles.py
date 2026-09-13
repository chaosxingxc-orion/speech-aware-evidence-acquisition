"""Public OpenJiuwen role nodes over a caller-owned frozen-core contact.

This module composes the framework's ``ReActAgent``, ``AbilityManager``,
``AgentRail`` and ``WorkflowComponent``. It does not create a model provider,
own a contact scheduler, or deliver task answers. A required callback is the
temporary integration seam: the caller must bind every request to the shared
``FrozenCoreClient.complete_with_metadata`` request-building, fit, budget and
evidence-custody path and return its source-bound ``CoreCompletion``.

The callback receives the complete framework message history and visible tool
schemas. It must preserve that history when building the repository request.
Audio carriage, conversion to the repository's bound Agent-state history, and
staged request-fit equality remain unsupported here until the flight runtime
provides that callback. The bridge never flattens or silently drops them.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm.schema.message import AssistantMessage
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.runner.callback.errors import AbortError
from openjiuwen.core.session.node import Session
from openjiuwen.core.single_agent import AgentCard, ReActAgent, ReActAgentConfig
from openjiuwen.core.single_agent.rail.base import AgentRail
from openjiuwen.core.workflow import (
    End,
    Start,
    Workflow,
    WorkflowComponent,
    create_workflow_session,
)

from ...rails.core_client import CoreCompletion, FrozenCoreClientError

RoleKind = Literal["perception", "reviewer", "planner", "solver"]
_ANALYTICAL_ROLE_KINDS = frozenset({"reviewer", "planner"})
_TOOL_FREE_ROLE_KINDS = frozenset({"perception", "solver"})


class FrozenCoreRoleModelError(RuntimeError):
    """The bridge refuses an invalid callback result or native call envelope."""


@dataclass(frozen=True)
class NativeRoleContactContext:
    """Non-model-visible bindings carried to every metered role contact."""

    sample_id: str
    agent_contact_id: str
    evidence_pins: Mapping[str, str] = field(default_factory=dict)
    budget_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise ValueError("sample_id must be a non-empty string")
        if not isinstance(self.agent_contact_id, str) or not self.agent_contact_id:
            raise ValueError("agent_contact_id must be a non-empty string")
        pins = dict(self.evidence_pins)
        for name, digest in pins.items():
            if (
                not isinstance(name, str)
                or not name
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError(
                    "evidence_pins must map non-empty names to lowercase SHA-256"
                )
        if self.budget_id is not None and (
            not isinstance(self.budget_id, str) or not self.budget_id
        ):
            raise ValueError("budget_id must be a non-empty string or None")
        object.__setattr__(self, "evidence_pins", MappingProxyType(pins))


@dataclass(frozen=True)
class NativeRoleNodeSpec:
    """Configuration for one public ReAct role node."""

    role_id: str
    role_kind: RoleKind
    prompt: str
    max_iterations: int
    ability_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role_id, str) or not self.role_id:
            raise ValueError("role_id must be a non-empty string")
        if self.role_kind not in _ANALYTICAL_ROLE_KINDS | _TOOL_FREE_ROLE_KINDS:
            raise ValueError(
                "role_kind must be perception, reviewer, planner, or solver"
            )
        if not isinstance(self.prompt, str) or not self.prompt:
            raise ValueError("prompt must be non-empty English text")
        if (
            isinstance(self.max_iterations, bool)
            or not isinstance(self.max_iterations, int)
            or self.max_iterations < 1
        ):
            raise ValueError("max_iterations must be a positive integer")
        if (
            not isinstance(self.ability_names, tuple)
            or any(
                not isinstance(name, str) or not name
                for name in self.ability_names
            )
            or len(set(self.ability_names)) != len(self.ability_names)
        ):
            raise ValueError("ability_names must be ordered unique non-empty strings")
        if self.role_kind in _TOOL_FREE_ROLE_KINDS and self.ability_names:
            raise ValueError(f"{self.role_kind} role must be tool-free")


@dataclass(frozen=True)
class NativeRoleModelRequest:
    """One full framework turn handed to the registered metered callback."""

    role_id: str
    context: NativeRoleContactContext
    messages: tuple[Mapping[str, object], ...]
    tool_schemas: tuple[Mapping[str, object], ...]
    visible_tool_names: tuple[str, ...]
    decoding_controls: Mapping[str, object]


class MeteredRoleRequest(Protocol):
    """Caller hook that uses the existing FrozenCoreClient request path."""

    def __call__(self, request: NativeRoleModelRequest) -> CoreCompletion: ...


def _document(value: object) -> dict[str, object]:
    if isinstance(value, Mapping):
        return dict(value)
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        document = dump(mode="json", exclude_none=True)
        if isinstance(document, Mapping):
            return dict(document)
    raise FrozenCoreRoleModelError(
        "OpenJiuwen supplied an unsupported message/tool value "
        f"{type(value).__name__}"
    )


def _tool_calls(completion: CoreCompletion) -> list[ToolCall] | None:
    raw = completion.tool_calls
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise FrozenCoreRoleModelError(
            "native tool_calls must be a non-empty list or null"
        )
    converted: list[ToolCall] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise FrozenCoreRoleModelError("native tool call must be an object")
        call_id = item.get("id")
        function = item.get("function")
        if (
            item.get("type") != "function"
            or not isinstance(call_id, str)
            or not call_id
            or call_id in seen
            or not isinstance(function, Mapping)
            or not isinstance(function.get("name"), str)
            or not function["name"]
            or not isinstance(function.get("arguments"), str)
        ):
            raise FrozenCoreRoleModelError(
                "native tool call requires a unique id, function name and raw "
                "argument text"
            )
        seen.add(call_id)
        converted.append(
            ToolCall(
                id=call_id,
                type="function",
                name=function["name"],
                arguments=function["arguments"],
            )
        )
    return converted


def _has_source_binding(completion: CoreCompletion) -> bool:
    digests = (
        completion.request_sha256,
        completion.response_sha256,
        completion.response_text_sha256,
    )
    return bool(
        isinstance(completion.request_id, str)
        and completion.request_id
        and all(
            isinstance(digest, str)
            and len(digest) == 64
            and all(character in "0123456789abcdef" for character in digest)
            for digest in digests
        )
    )


class FrozenCoreRoleModel:
    """Public ``ReActAgent.set_llm`` target backed only by a metered callback."""

    def __init__(
        self,
        *,
        role_id: str,
        context: NativeRoleContactContext,
        metered_request: MeteredRoleRequest,
    ) -> None:
        if not callable(metered_request):
            raise ValueError("metered_request must be callable")
        self._role_id = role_id
        self._context = context
        self._metered_request = metered_request

    async def invoke(self, messages, *, tools=None, **kwargs) -> AssistantMessage:
        message_documents = tuple(_document(message) for message in messages)
        tool_documents = tuple(_document(tool) for tool in (tools or ()))
        names: list[str] = []
        for tool in tool_documents:
            name = tool.get("name")
            if not isinstance(name, str) or not name:
                raise FrozenCoreRoleModelError("visible tool schema lacks a name")
            names.append(name)
        request = NativeRoleModelRequest(
            role_id=self._role_id,
            context=self._context,
            messages=message_documents,
            tool_schemas=tool_documents,
            visible_tool_names=tuple(names),
            decoding_controls=MappingProxyType(
                {key: value for key, value in kwargs.items() if value is not None}
            ),
        )
        completion = self._metered_request(request)
        if inspect.isawaitable(completion):
            completion = await completion
        if not isinstance(completion, CoreCompletion):
            raise FrozenCoreRoleModelError(
                "metered_request must return a source-bound CoreCompletion"
            )
        if not _has_source_binding(completion):
            raise FrozenCoreRoleModelError(
                "metered CoreCompletion is missing request/response source binding"
            )
        try:
            completion.assert_binding(
                sample_id=self._context.sample_id,
                agent_contact_id=self._context.agent_contact_id,
                response_text=completion.text,
            )
        except FrozenCoreClientError as error:
            raise FrozenCoreRoleModelError(
                f"metered completion binding failed: {error}"
            ) from error
        calls = _tool_calls(completion)
        return AssistantMessage(
            content="" if calls else completion.text, tool_calls=calls
        )


class _RoleAuthorityRail(AgentRail):
    def __init__(
        self,
        *,
        role_id: str,
        advertised_names: frozenset[str],
        tool_allowed: Callable[[str, str], bool],
    ) -> None:
        self._role_id = role_id
        self._advertised_names = advertised_names
        self._tool_allowed = tool_allowed

    async def before_tool_call(self, ctx) -> None:
        name = ctx.inputs.tool_call.name
        if (
            name not in self._advertised_names
            or not self._tool_allowed(self._role_id, name)
        ):
            cause = PermissionError(
                f"Tool {name!r} is outside role authority for {self._role_id!r}."
            )
            raise AbortError("role tool authority rejection", cause=cause)


class NativeRoleNode(WorkflowComponent):
    """One OpenJiuwen ReAct role that returns actor output without delivery."""

    def __init__(
        self,
        *,
        spec: NativeRoleNodeSpec,
        metered_request: MeteredRoleRequest,
        contact_context: NativeRoleContactContext,
        abilities: Sequence[object] = (),
        tool_allowed: Callable[[str, str], bool] | None = None,
        delivery_allowed: Callable[[str, str], bool] | None = None,
    ) -> None:
        super().__init__()
        self.spec = spec
        self._delivery_allowed = delivery_allowed or (
            lambda _role, _output: False
        )
        if spec.role_kind in _TOOL_FREE_ROLE_KINDS and tool_allowed is not None:
            raise ValueError(f"{spec.role_kind} role must be tool-free")
        names: list[str] = []
        self._agent = ReActAgent(
            card=AgentCard(
                id=spec.role_id,
                name=spec.role_id,
                description=f"Native {spec.role_kind} role node.",
            )
        )
        self._agent.configure(
            ReActAgentConfig(
                model_name="frozen-core-metered-callback",
                max_iterations=spec.max_iterations,
                parallel_tool_calls=False,
                prompt_template=[{"role": "system", "content": spec.prompt}],
            )
        )
        self._agent.set_llm(
            FrozenCoreRoleModel(
                role_id=spec.role_id,
                context=contact_context,
                metered_request=metered_request,
            )
        )
        for ability in abilities:
            card = getattr(ability, "card", None)
            name = getattr(card, "name", None)
            if not isinstance(name, str) or not name:
                raise ValueError(
                    "every ability must expose a ToolCard with a name"
                )
            if name in names:
                raise ValueError(f"duplicate ability name {name!r}")
            names.append(name)
            added = self._agent.ability_manager.add_ability(card, ability)
            if not added.added:
                raise ValueError(f"OpenJiuwen refused ability {name!r}")
        if tuple(names) != spec.ability_names:
            raise ValueError(
                "ability resources must exactly match spec.ability_names in order"
            )
        self._advertised_names = frozenset(names)
        allowed = tool_allowed or (lambda _role, _name: False)
        self._rail = _RoleAuthorityRail(
            role_id=spec.role_id,
            advertised_names=self._advertised_names,
            tool_allowed=allowed,
        )
        self._rail_registered = False
        self._registration_lock = asyncio.Lock()

    async def _ensure_rail(self) -> None:
        if self._rail_registered:
            return
        async with self._registration_lock:
            if not self._rail_registered:
                await self._agent.register_rail(self._rail)
                self._rail_registered = True

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        return await self._run(inputs.get("query"), conversation_id=id(session))

    async def _run(self, query: object, *, conversation_id: object) -> Output:
        await self._ensure_rail()
        if not isinstance(query, str) or not query:
            raise ValueError("native role query must be non-empty text")
        result = await self._agent.invoke(
            {
                "query": query,
                "conversation_id": f"{self.spec.role_id}-{conversation_id}",
            },
        )
        actor_output = result.get("output")
        result_type = result.get("result_type")
        if not isinstance(actor_output, str) or not isinstance(result_type, str):
            raise FrozenCoreRoleModelError(
                "OpenJiuwen returned a malformed role result"
            )
        delivery_eligible = bool(
            self.spec.role_kind == "solver"
            and result_type == "answer"
            and self._delivery_allowed(self.spec.role_id, actor_output)
        )
        return {
            "role_id": self.spec.role_id,
            "actor_output": actor_output,
            "result_type": result_type,
            "delivery_eligible": delivery_eligible,
        }

    async def invoke_direct(self, query: str) -> dict[str, object]:
        """Invoke this component with a fresh public framework session."""
        result = await self._run(query, conversation_id="direct")
        return dict(result)


class NativeRoleWorkflow:
    """Small facade over a public sequential OpenJiuwen ``Workflow``."""

    def __init__(self, nodes: tuple[NativeRoleNode, ...]) -> None:
        self.nodes = nodes
        self.role_ids = tuple(node.spec.role_id for node in nodes)

    def _build(self) -> Workflow:
        """Build inside the running loop, as OpenJiuwen binds graph futures."""
        workflow = Workflow()
        workflow.set_start_comp(
            "start", Start(), inputs_schema={"query": "${query}"}
        )
        previous = "start"
        for node in self.nodes:
            query_source = "query" if previous == "start" else "actor_output"
            workflow.add_workflow_comp(
                node.spec.role_id,
                node,
                inputs_schema={
                    "query": "${" + previous + "." + query_source + "}"
                },
            )
            workflow.add_connection(previous, node.spec.role_id)
            previous = node.spec.role_id
        workflow.set_end_comp(
            "end",
            End(),
            inputs_schema={
                role_id: "${" + role_id + "}" for role_id in self.role_ids
            },
        )
        workflow.add_connection(previous, "end")
        return workflow

    async def invoke_direct(self, query: str) -> dict[str, object]:
        output = await self._build().invoke(
            inputs={"query": query}, session=create_workflow_session()
        )
        result = output.result
        if not isinstance(result, Mapping):
            raise FrozenCoreRoleModelError(
                "OpenJiuwen workflow returned no role mapping"
            )
        result = result.get("output")
        if not isinstance(result, Mapping):
            raise FrozenCoreRoleModelError(
                "OpenJiuwen workflow end node returned no role mapping"
            )
        actors = {role_id: dict(result[role_id]) for role_id in self.role_ids}
        return {"actors": actors}


def build_native_role_workflow(
    nodes: Sequence[NativeRoleNode],
) -> NativeRoleWorkflow:
    """Compose role nodes sequentially; each output remains visible."""
    ordered = tuple(nodes)
    if not ordered:
        raise ValueError("native role workflow requires at least one node")
    role_ids = tuple(node.spec.role_id for node in ordered)
    if len(set(role_ids)) != len(role_ids):
        raise ValueError("native role workflow role ids must be unique")

    return NativeRoleWorkflow(ordered)


__all__ = [
    "FrozenCoreRoleModel",
    "FrozenCoreRoleModelError",
    "MeteredRoleRequest",
    "NativeRoleContactContext",
    "NativeRoleModelRequest",
    "NativeRoleNode",
    "NativeRoleNodeSpec",
    "NativeRoleWorkflow",
    "build_native_role_workflow",
]
