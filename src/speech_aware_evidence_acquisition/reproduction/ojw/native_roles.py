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
import copy
import hashlib
import inspect
import itertools
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, Protocol

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.foundation.llm.schema.message import AssistantMessage, ToolMessage
from openjiuwen.core.foundation.llm.schema.tool_call import ToolCall
from openjiuwen.core.foundation.tool.base import Tool
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

FROZEN_CORE_CALLBACK_MODEL = "frozen-core-metered-callback"

RoleKind = Literal["perception", "reviewer", "planner", "solver"]
_ANALYTICAL_ROLE_KINDS = frozenset({"reviewer", "planner"})
_TOOL_FREE_ROLE_KINDS = frozenset({"perception", "solver"})

#: Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier),
#: 2026-09-19. The EXACT output the pinned framework returns when a ReAct
#: loop spends its whole iteration budget without ever producing an answer
#: (``openjiuwen.core.single_agent.agents.react_agent``, the ``else:`` branch
#: of the iteration ``for``). It is a framework literal, not a model response:
#: the loop never reached a completion with no tool call, so it has no answer
#: to return and says so. Matched EXACTLY -- ``result_type`` ``"error"`` also
#: carries genuine failures (``"No query provided"``, ``str(exception)``),
#: and those are NOT this class.
REACT_EXHAUSTION_OUTPUT = "Max iterations reached without completion"


def _canonical_sha256(value: object) -> str:
    """The sha256 of one tool argument set or one observation, never its text.

    A string is hashed as its own UTF-8 bytes (that is what the wire carried);
    anything else is hashed through canonical JSON, so the same arguments
    produce the same digest whatever order the framework handed them in. A
    value JSON cannot represent falls back to ``repr``, which is still a
    stable identity for the one thing this digest is for: telling "the same
    call again" from "a different call".
    """

    if isinstance(value, str):
        payload = value
    else:
        try:
            payload = json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            )
        except (TypeError, ValueError):
            payload = repr(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class FrozenCoreRoleModelError(RuntimeError):
    """The bridge refuses an invalid callback result or native call envelope."""


class FrozenCoreRoleContextFitError(FrozenCoreRoleModelError):
    """E20 (2026-09-19): this role's request does not fit the live slot.

    Raised INSTEAD of dispatching (the harness's own live-slot budget
    refused the realised request after the declared compaction passes) or
    instead of propagating the fork's HTTP 400
    ``exceed_context_size_error``. It carries NO completion, because there
    is none: the request was never answered. What it carries is why --
    which blocks were dropped, how many tokens before and after, which seam
    refused, and the server's own sentence when the server is the one that
    refused.

    ``role_id`` and ``execution_receipt`` are filled by
    :meth:`NativeRoleNode._run`, exactly as they are for a finite
    completion, so the episode's terminal outcome can bind the interrupted
    role to the contacts it had already made. ``execution_receipt`` is
    ``None`` when this was the role's FIRST contact, which a finite
    completion can never be.
    """

    def __init__(
        self,
        *,
        source: str,
        compaction_pass: int,
        dropped_identifiers: Sequence[str] = (),
        tokens_before: int = 0,
        tokens_after: int = 0,
        limit_tokens: int = 0,
        server_message: str | None = None,
    ) -> None:
        super().__init__(
            "metered request does not fit the live serving slot "
            f"({tokens_after} required, {limit_tokens} available, refused at "
            f"{source})"
        )
        self.source = source
        self.compaction_pass = compaction_pass
        self.dropped_identifiers = tuple(dropped_identifiers)
        self.tokens_before = tokens_before
        self.tokens_after = tokens_after
        self.limit_tokens = limit_tokens
        self.server_message = server_message
        self.role_id: str | None = None
        self.execution_receipt: Mapping[str, object] | None = None

    def __deepcopy__(self, memo):
        cloned = type(self)(
            source=self.source,
            compaction_pass=self.compaction_pass,
            dropped_identifiers=self.dropped_identifiers,
            tokens_before=self.tokens_before,
            tokens_after=self.tokens_after,
            limit_tokens=self.limit_tokens,
            server_message=self.server_message,
        )
        memo[id(self)] = cloned
        cloned.role_id = self.role_id
        cloned.execution_receipt = copy.deepcopy(self.execution_receipt, memo)
        return cloned


class FrozenCoreRoleFiniteCompletionError(FrozenCoreRoleModelError):
    """A valid source-bound completion ended before authoritative delivery."""

    def __init__(
        self,
        *,
        completion: CoreCompletion,
        finish_reason: Literal["length", "content_filter"],
        original_message: Mapping[str, object],
    ) -> None:
        super().__init__(
            "metered completion is non-authoritative because finish_reason "
            f"is {finish_reason!r}"
        )
        self.completion = completion
        self.finish_reason = finish_reason
        self.original_message = original_message
        self.role_id: str | None = None
        self.execution_receipt: Mapping[str, object] | None = None

    def __deepcopy__(self, memo):
        # Framework error snapshots copy exception objects through their constructor.
        # Preserve immutable completion custody instead of reconstructing from args.
        cloned = type(self)(
            completion=self.completion, finish_reason=self.finish_reason,
            original_message=self.original_message,
        )
        memo[id(self)] = cloned
        cloned.role_id = self.role_id
        cloned.execution_receipt = copy.deepcopy(self.execution_receipt, memo)
        return cloned

    @property
    def request_sha256(self) -> str:
        return self.completion.request_sha256

    @property
    def response_sha256(self) -> str:
        return self.completion.response_sha256

    @property
    def response_text_sha256(self) -> str:
        return self.completion.response_text_sha256


class NativeSourceFunction(Tool):
    """Validate native arguments without converting their wire representation.

    LocalFunction's JSON-Schema-to-Pydantic formatter rewrites input values and
    rejects uniqueItems with the pinned Pydantic version. Use the framework's
    public Tool extension and the original JSON schema instead. The bound
    dispatcher still verifies source hashes, role authority and task semantics.
    """

    def __init__(self, *, card, func, invalid_arguments=None):
        from jsonschema.validators import validator_for

        super().__init__(card)
        if not isinstance(card.input_params, dict) or not inspect.iscoroutinefunction(func):
            raise ValueError("native source tools require a JSON schema and async handler")
        validator = validator_for(card.input_params)
        validator.check_schema(card.input_params)
        self._validator = validator(card.input_params)
        self._source_handler = func
        if invalid_arguments is not None and not inspect.iscoroutinefunction(invalid_arguments):
            raise ValueError("invalid argument observation handler must be async")
        self._invalid_arguments = invalid_arguments

    async def invoke(self, inputs: Input, **kwargs) -> Output:
        # Never honor formatting/coercion skips: source identity requires the
        # unchanged validated dict and ordered arrays, including uniqueness.
        from jsonschema.exceptions import ValidationError
        try:
            self._validator.validate(inputs)
        except ValidationError:
            if self._invalid_arguments is None:
                raise
            return await self._invalid_arguments(inputs)
        return await self._source_handler(**inputs)

    async def stream(self, inputs: Input, **kwargs):
        yield await self.invoke(inputs, **kwargs)


@dataclass(frozen=True)
class NativeRoleContactContext:
    """Non-model-visible bindings carried to every metered role contact."""

    sample_id: str
    agent_contact_id: str
    evidence_pins: Mapping[str, str] = field(default_factory=dict)
    budget_id: str | None = None
    # E2 (SLURP v2 base program M2): the zero-based position of this contact
    # within one grouped Solver visit's N pinned-seed samples, bound by the
    # caller's contact_context_provider so native_request.py's decoding
    # composition knows which sample it is preparing. None for every
    # non-grouped role/contact -- today's entire behaviour.
    sample_index: int | None = None
    # Item E42 (2026-09-25, Stage-3 family VAR-2): the declared SUPPLY-variant
    # arm this contact is composed for, bound by the caller's
    # contact_context_provider so ``rails.runner``'s binding provider knows
    # which arm's knowledge construction to render. None for every
    # non-arm-grouped role/contact -- today's entire behaviour. Declared LAST
    # and defaulted, so every positional construction written before E42
    # composes exactly the context it always did.
    variant_arm_id: str | None = None
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md): the declared PERCEPTION-BRANCH this contact is composed
    # for, bound by the caller's contact_context_provider so ``rails.runner``
    # 's binding provider knows which branch's seed to render. None for
    # every non-branched role/contact -- today's entire behaviour. Declared
    # LAST and defaulted, for the same reason ``variant_arm_id`` is.
    perception_branch_id: str | None = None

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
        if self.sample_index is not None and (
            isinstance(self.sample_index, bool)
            or not isinstance(self.sample_index, int)
            or self.sample_index < 0
        ):
            raise ValueError("sample_index must be a nonnegative integer or None")
        if self.variant_arm_id is not None and (
            not isinstance(self.variant_arm_id, str) or not self.variant_arm_id
        ):
            raise ValueError("variant_arm_id must be a non-empty string or None")
        if self.perception_branch_id is not None and (
            not isinstance(self.perception_branch_id, str)
            or not self.perception_branch_id
        ):
            raise ValueError(
                "perception_branch_id must be a non-empty string or None"
            )
        object.__setattr__(self, "evidence_pins", MappingProxyType(pins))


@dataclass(frozen=True)
class NativeRoleNodeSpec:
    """Configuration for one public ReAct role node."""

    role_id: str
    role_kind: RoleKind
    prompt: str
    max_iterations: int
    ability_names: tuple[str, ...] = ()
    reserve_final_report: bool = False
    # Item E39 (2026-09-22): whether a ``length``-truncated completion of THIS
    # role ends the episode. ``False`` -- every spec written before E39 and
    # every ``native_episode.finite_completion_scope`` ``"episode"`` config --
    # re-raises the finite-completion refusal exactly as before, so item E13
    # keeps its whole-episode scope. ``True`` -- set by the runner only for a
    # NON-answering role under ``"answering-node"`` -- keeps the truncated
    # text as this role's output and lets the graph continue to the node that
    # does answer. Only the Solver answers, so the answering role may never
    # carry it. Declared LAST so every positional construction written before
    # E39 composes exactly the spec it always did.
    tolerate_length_truncation: bool = False
    solver_tool_access: str | None = None

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
        if self.solver_tool_access is not None:
            from ...rails.native_episode_config import SOLVER_TOOL_ACCESS_MODE, SOLVER_SLOT_TOOL

            if (self.solver_tool_access != SOLVER_TOOL_ACCESS_MODE or self.role_kind != "solver"
                    or self.ability_names != (SOLVER_SLOT_TOOL,) or self.max_iterations != 2
                    or not self.reserve_final_report):
                raise ValueError("Solver tool access requires one bounded lookup and a reserved final answer")
        if self.role_kind in _TOOL_FREE_ROLE_KINDS and self.ability_names and self.solver_tool_access is None:
            raise ValueError(f"{self.role_kind} role must be tool-free")
        if type(self.reserve_final_report) is not bool or (
            self.reserve_final_report
            and (not self.ability_names or self.max_iterations < 2)
        ):
            raise ValueError("final report reservation requires a tool role with two or more iterations")
        if type(self.tolerate_length_truncation) is not bool:
            raise ValueError("tolerate_length_truncation must be a boolean")
        if self.tolerate_length_truncation and self.role_kind == "solver":
            # Item E39: the Solver IS the answering node, so its truncation is
            # exactly the case item E13 exists for. Refused by name rather
            # than silently ignored.
            raise ValueError(
                "the answering Solver role always ends the episode on a truncated "
                "completion"
            )


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


class ContactContextProvider(Protocol):
    """Resolve one preallocated registered context by zero-based invocation."""

    def __call__(self, invocation_index: int) -> NativeRoleContactContext: ...


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


def _wire_turn(
    completion: CoreCompletion,
) -> tuple[object | None, list[ToolCall] | None, str]:
    """Validate and project one source-bound native assistant turn.

    The original wire message is the only assistant content accepted here.
    CoreCompletion.text is the normalized scorer text and may be a
    canonical tool-call array, so it must never become framework history.
    """

    try:
        message = completion.original_message
        finish_reason = completion.finish_reason
    except ValueError as error:
        raise FrozenCoreRoleModelError(
            f"metered completion wire metadata is invalid: {error}"
        ) from error
    if message is None or finish_reason is None:
        raise FrozenCoreRoleModelError(
            "metered completion requires preserved wire metadata"
        )
    if not isinstance(message, Mapping):
        raise FrozenCoreRoleModelError(
            "metered completion wire message must be an object"
        )
    content = message.get("content")
    if content is not None and not isinstance(content, (str, list, tuple)):
        raise FrozenCoreRoleModelError(
            "metered completion wire message content is not framework-compatible"
        )
    if isinstance(finish_reason, str) and finish_reason in {"length", "content_filter"}:
        raise FrozenCoreRoleFiniteCompletionError(
            completion=completion,
            finish_reason=finish_reason,
            original_message=message,
        )
    if not isinstance(finish_reason, str) or finish_reason not in {"stop", "tool_calls"}:
        raise FrozenCoreRoleModelError(
            f"metered completion has unsupported finish_reason {finish_reason!r}"
        )
    calls = _tool_calls(completion)
    if finish_reason == "stop" and calls is not None:
        raise FrozenCoreRoleModelError(
            "finish_reason 'stop' cannot carry native tool_calls"
        )
    if finish_reason == "tool_calls" and calls is None:
        raise FrozenCoreRoleModelError(
            "finish_reason 'tool_calls' requires native tool_calls"
        )
    return content, calls, finish_reason


def project_native_assistant_message(
    completion: CoreCompletion,
) -> AssistantMessage:
    """Project one preserved native wire turn into OpenJiuwen losslessly.

    OpenJiuwen 0.1.16 requires non-null assistant content. A validated wire
    ``null`` is represented as an empty framework string; every other content
    value is preserved. Reversal remains possible only with the same
    source-bound ``CoreCompletion`` and its unchanged wire bytes.
    """

    if not isinstance(completion, CoreCompletion) or not _has_source_binding(
        completion
    ):
        raise FrozenCoreRoleModelError(
            "native assistant projection requires a CoreCompletion with source binding"
        )
    content, calls, finish_reason = _wire_turn(completion)
    return AssistantMessage(
        content="" if content is None else content,
        tool_calls=calls,
        finish_reason=finish_reason,
    )


def restore_native_assistant_wire_message(
    message: AssistantMessage,
    *,
    completion: CoreCompletion,
) -> Mapping[str, object]:
    """Restore the preserved wire message after exact projection validation.

    An empty assistant string never implies a source ``null`` by itself. The
    helper reprojects the supplied completion, compares actual OpenJiuwen
    serialization (including raw call ids, names and argument text), then
    returns a detached JSON-shaped copy of the original wire message. Empty
    source strings and structured content therefore remain distinct from
    source nulls.
    """

    if not isinstance(completion, CoreCompletion) or not _has_source_binding(
        completion
    ):
        raise FrozenCoreRoleModelError(
            "native assistant restoration requires a CoreCompletion with source binding"
        )
    if not isinstance(message, AssistantMessage):
        raise FrozenCoreRoleModelError(
            "native assistant restoration requires an AssistantMessage"
        )
    expected = project_native_assistant_message(completion)
    if _document(message) != _document(expected):
        raise FrozenCoreRoleModelError(
            "framework projected content or native tool calls were changed"
        )
    try:
        original = completion.original_message
    except ValueError as error:
        raise FrozenCoreRoleModelError(
            f"metered completion wire metadata is invalid: {error}"
        ) from error
    if original is None:
        raise FrozenCoreRoleModelError(
            "metered completion requires preserved wire metadata"
        )
    restored = _thaw_wire_value(original)
    assert isinstance(restored, dict)
    return restored


def _thaw_wire_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_wire_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_wire_value(item) for item in value]
    return value


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


def _contact_receipt(completion: CoreCompletion) -> dict[str, str]:
    """Select compact identity and hashes from one bound completion."""
    assert isinstance(completion.agent_contact_id, str)
    return {
        "agent_contact_id": completion.agent_contact_id,
        "request_id": completion.request_id,
        "request_sha256": completion.request_sha256,
        "response_sha256": completion.response_sha256,
        "response_text_sha256": completion.response_text_sha256,
    }


class FrozenCoreRoleModel:
    """Public ``ReActAgent.set_llm`` target backed only by a metered callback."""

    def __init__(
        self,
        *,
        role_id: str,
        metered_request: MeteredRoleRequest,
        context: NativeRoleContactContext | None = None,
        context_provider: ContactContextProvider | None = None,
    ) -> None:
        if not callable(metered_request):
            raise ValueError("metered_request must be callable")
        if (context is None) == (context_provider is None):
            raise ValueError(
                "provide exactly one fixed context or contact-context provider"
            )
        if context is not None and not isinstance(context, NativeRoleContactContext):
            raise ValueError("fixed context must be a NativeRoleContactContext")
        if context_provider is not None and not callable(context_provider):
            raise ValueError("contact-context provider must be callable")
        self._role_id = role_id
        self._metered_request = metered_request
        self._fixed_context = context
        self._context_provider = context_provider
        self._contact_index = itertools.count(0)
        self._used_contact_ids: set[str] = set()
        self._receipt_contacts: ContextVar[list[dict[str, str]] | None] = (
            ContextVar(
                f"native_role_receipts_{uuid.uuid4().hex}", default=None
            )
        )

    def _begin_receipt_capture(
        self,
    ) -> tuple[Token[list[dict[str, str]] | None], list[dict[str, str]]]:
        contacts: list[dict[str, str]] = []
        return self._receipt_contacts.set(contacts), contacts

    def _end_receipt_capture(
        self, token: Token[list[dict[str, str]] | None]
    ) -> None:
        self._receipt_contacts.reset(token)

    def _next_context(self) -> NativeRoleContactContext:
        index = next(self._contact_index)
        if self._fixed_context is not None:
            if index > 0:
                raise FrozenCoreRoleModelError(
                    "fixed contact context is exhausted after one invocation"
                )
            context = self._fixed_context
        else:
            assert self._context_provider is not None
            try:
                context = self._context_provider(index)
            except (IndexError, StopIteration) as error:
                raise FrozenCoreRoleModelError(
                    f"contact-context provider is exhausted at invocation {index}"
                ) from error
        if not isinstance(context, NativeRoleContactContext):
            raise FrozenCoreRoleModelError(
                f"contact-context provider returned no registered context at "
                f"invocation {index}"
            )
        if context.agent_contact_id in self._used_contact_ids:
            raise FrozenCoreRoleModelError(
                f"contact-context provider repeated agent_contact_id "
                f"{context.agent_contact_id!r}"
            )
        self._used_contact_ids.add(context.agent_contact_id)
        return context

    async def invoke(self, messages, *, tools=None, **kwargs) -> AssistantMessage:
        context = self._next_context()
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
            context=context,
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
                sample_id=context.sample_id,
                agent_contact_id=context.agent_contact_id,
                response_text=completion.text,
            )
        except FrozenCoreClientError as error:
            raise FrozenCoreRoleModelError(
                f"metered completion binding failed: {error}"
            ) from error
        contacts = self._receipt_contacts.get()
        if contacts is not None:
            contacts.append(_contact_receipt(completion))
        return project_native_assistant_message(completion)


class _RoleAuthorityRail(AgentRail):
    def __init__(
        self,
        *,
        role_id: str,
        advertised_names: frozenset[str],
        tool_allowed: Callable[[str, str], bool],
        final_report_iteration: int | None = None,
        reject_tool_batch=None,
    ) -> None:
        self._role_id = role_id
        self._advertised_names = advertised_names
        self._tool_allowed = tool_allowed
        self._final_report_iteration = final_report_iteration
        self._iteration_key = f"saea-native-report-turn:{role_id}"
        self._reject_tool_batch = reject_tool_batch
        self._rejection_key = f"saea-native-rejected-batch:{role_id}"

    async def before_model_call(self, ctx) -> None:
        if self._final_report_iteration is None:
            return
        iteration = ctx.extra.get(self._iteration_key, 0) + 1
        ctx.extra[self._iteration_key] = iteration
        if iteration >= self._final_report_iteration:
            # Use the framework's public hook to reserve an actual model report.
            ctx.inputs.tools = []


    async def after_model_call(self, ctx) -> None:
        if self._reject_tool_batch is None:
            return
        if ctx.extra.get(self._rejection_key):
            raise FrozenCoreRoleModelError("framework omitted a rejected call result")
        response = ctx.inputs.response
        calls = getattr(response, "tool_calls", None)
        if not calls or len(calls) <= 1:
            return
        for call in calls:
            self._assert_allowed(ctx, call.name)
        messages = self._reject_tool_batch(self._role_id, response)
        if (
            len(messages) != len(calls)
            or [message.get("tool_call_id") for message in messages] != [call.id for call in calls]
            or any(set(message) != {"role", "tool_call_id", "content"}
                   or message["role"] != "tool" or not isinstance(message["content"], str)
                   for message in messages)
        ):
            raise FrozenCoreRoleModelError("batch rejection changed original call identities")
        ctx.extra[self._rejection_key] = {
            call.id: (call.name, call.arguments, message["content"])
            for call, message in zip(calls, messages, strict=True)
        }

    def _assert_allowed(self, ctx, name):
        if (
            name not in self._advertised_names
            or not self._tool_allowed(self._role_id, name)
            or (
                self._final_report_iteration is not None
                and ctx.extra.get(self._iteration_key, 0) >= self._final_report_iteration
            )
        ):
            cause = PermissionError(
                f"Tool {name!r} is outside role authority for {self._role_id!r}."
            )
            raise AbortError("role tool authority rejection", cause=cause)

    async def before_tool_call(self, ctx) -> None:
        call = ctx.inputs.tool_call
        self._assert_allowed(ctx, call.name)
        rejected = ctx.extra.get(self._rejection_key, {})
        if not rejected:
            return
        item = rejected.pop(call.id, None)
        if item is None or item[:2] != (call.name, call.arguments):
            raise FrozenCoreRoleModelError("framework changed a rejected tool call")
        content = item[2]
        ctx.inputs.tool_result = content
        ctx.inputs.tool_msg = ToolMessage(content=content, tool_call_id=call.id)
        ctx.extra["_skip_tool"] = True


class _InstanceOwnedAbility(Tool):
    """Bind one caller ability to this role node without mutating its card.

    E22: it is also the node's own record of what this role actually called.
    ``record`` is the node's invocation-local recorder (``None`` outside an
    invocation, which is the state of every direct construction in the
    tests); it is handed the tool id and the arguments BEFORE the call and
    the observation after, so a call that raises still leaves its identity
    in the log. Recording changes no argument, no result and no request
    byte -- it only remembers digests.
    """

    def __init__(self, ability: Tool, record=None) -> None:
        card = ability.card.model_copy(deep=True, update={"stateless": False})
        super().__init__(card)
        self._ability = ability
        self._record = record
        self._tool_id = card.name

    def _begin(self, inputs):
        if self._record is None:
            return None
        return self._record(self._tool_id, inputs)

    async def invoke(self, inputs, **kwargs):
        entry = self._begin(inputs)
        result = await self._ability.invoke(inputs, **kwargs)
        if entry is not None:
            entry["observation_sha256"] = _canonical_sha256(result)
        return result

    async def stream(self, inputs, **kwargs):
        entry = self._begin(inputs)
        last = None
        async for item in self._ability.stream(inputs, **kwargs):
            last = item
            yield item
        if entry is not None and last is not None:
            entry["observation_sha256"] = _canonical_sha256(last)


class NativeRoleNode(WorkflowComponent):
    """One OpenJiuwen ReAct role that returns actor output without delivery."""

    def __init__(
        self,
        *,
        spec: NativeRoleNodeSpec,
        metered_request: MeteredRoleRequest,
        contact_context: NativeRoleContactContext | None = None,
        contact_context_provider: ContactContextProvider | None = None,
        abilities: Sequence[object] = (),
        tool_allowed: Callable[[str, str], bool] | None = None,
        delivery_allowed: Callable[[str, str], bool] | None = None,
        reject_tool_batch=None,
    ) -> None:
        super().__init__()
        self.spec = spec
        # E22: the invocation-local log of what this role's ReAct loop
        # actually called, in order. Built exactly as
        # ``FrozenCoreRoleModel._receipt_contacts`` is -- a ContextVar whose
        # list object the framework's own tasks append to by reference -- so
        # two concurrent invocations of the same node never see each other's
        # calls. ``None`` outside an invocation, which is when nothing
        # records.
        self._tool_calls: ContextVar[list[dict[str, object]] | None] = ContextVar(
            f"native_role_tool_calls_{uuid.uuid4().hex}", default=None
        )
        self._delivery_allowed = delivery_allowed or (
            lambda _role, _output: False
        )
        if (spec.role_kind in _TOOL_FREE_ROLE_KINDS and spec.solver_tool_access is None
                and tool_allowed is not None):
            raise ValueError(f"{spec.role_kind} role must be tool-free")
        names: list[str] = []
        self._invocation_namespace = uuid.uuid4().hex
        framework_agent_id = f"{spec.role_id}-{self._invocation_namespace}"
        self._agent = ReActAgent(
            card=AgentCard(
                id=framework_agent_id,
                name=spec.role_id,
                description=f"Native {spec.role_kind} role node.",
            )
        )
        self._agent.configure(
            ReActAgentConfig(
                model_name=FROZEN_CORE_CALLBACK_MODEL,
                max_iterations=spec.max_iterations,
                parallel_tool_calls=False,
                prompt_template=[{"role": "system", "content": spec.prompt}],
            )
        )
        self._model = FrozenCoreRoleModel(
            role_id=spec.role_id,
            metered_request=metered_request,
            context=contact_context,
            context_provider=contact_context_provider,
        )
        self._agent.set_llm(self._model)
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
            if not isinstance(ability, Tool):
                raise ValueError("every ability must be an OpenJiuwen Tool")
            owned_ability = _InstanceOwnedAbility(ability, self._record_tool_call)
            added = self._agent.ability_manager.add_ability(
                owned_ability.card, owned_ability
            )
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
            final_report_iteration=(spec.max_iterations if spec.reserve_final_report else None),
            reject_tool_batch=reject_tool_batch,
        )
        self._rail_registered = False
        self._registration_lock = asyncio.Lock()
        self._close_requested = False
        self._tools_closed = False
        self._resources_closed = False
        self._invocation_serial = itertools.count(1)

    def _record_tool_call(self, tool_id: str, arguments: object):
        """E22: remember one attempted tool call of the live invocation.

        Returns the mutable entry the ability fills with the observation
        digest, or ``None`` when no invocation is capturing -- which is the
        only way this can fail, and it fails by remembering nothing rather
        than by raising into a tool call.
        """

        log = self._tool_calls.get()
        if log is None:
            return None
        entry: dict[str, object] = {
            "tool_id": tool_id,
            "arguments_sha256": _canonical_sha256(arguments),
            "observation_sha256": None,
        }
        log.append(entry)
        return entry

    def _begin_tool_capture(
        self,
    ) -> tuple[Token[list[dict[str, object]] | None], list[dict[str, object]]]:
        calls: list[dict[str, object]] = []
        return self._tool_calls.set(calls), calls

    def _end_tool_capture(
        self, token: Token[list[dict[str, object]] | None]
    ) -> None:
        self._tool_calls.reset(token)

    async def _ensure_rail(self) -> None:
        if self._close_requested:
            raise FrozenCoreRoleModelError("native role node is closed")
        if self._rail_registered:
            return
        async with self._registration_lock:
            if self._close_requested:
                raise FrozenCoreRoleModelError("native role node is closed")
            if not self._rail_registered:
                await self._agent.register_rail(self._rail)
                self._rail_registered = True

    async def close(self) -> None:
        """Release only the OpenJiuwen resources owned by this role instance."""

        async with self._registration_lock:
            if self._resources_closed:
                return
            self._close_requested = True
            try:
                if self._rail_registered:
                    await self._agent.unregister_rail(self._rail)
                    self._rail_registered = False
            finally:
                if not self._tools_closed:
                    self._agent.ability_manager.teardown_tools()
                    self._tools_closed = True
            self._resources_closed = True

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        return await self._run(inputs.get("query"))

    async def _run(self, query: object) -> Output:
        await self._ensure_rail()
        if not isinstance(query, str) or not query:
            raise ValueError("native role query must be non-empty text")
        receipt_token, receipt_contacts = self._model._begin_receipt_capture()
        tool_token, tool_calls = self._begin_tool_capture()
        try:
            result = await self._agent.invoke(
                {
                    "query": query,
                    "conversation_id": (
                        f"{self.spec.role_id}-{self._invocation_namespace}-"
                        f"{next(self._invocation_serial):08d}"
                    ),
                },
            )
        except FrozenCoreRoleContextFitError as error:
            # E20: the request never reached the wire (or the wire refused
            # it), so there is no completion to bind -- only the contacts
            # this role had already completed, which may be none.
            error.role_id = self.spec.role_id
            error.execution_receipt = (
                None if not receipt_contacts
                else {
                    "contacts": [dict(contact) for contact in receipt_contacts],
                    "final_contact": dict(receipt_contacts[-1]),
                }
            )
            raise
        except FrozenCoreRoleFiniteCompletionError as error:
            if not receipt_contacts or receipt_contacts[-1] != _contact_receipt(error.completion):
                raise FrozenCoreRoleModelError(
                    "finite role completion lost its actual contact receipt"
                ) from error
            tolerated = self._tolerated_truncation(error, receipt_contacts)
            if tolerated is not None:
                # Item E39: a NON-answering role under ``answering-node``
                # scope. The contact was made, metered and traced exactly as
                # any other; what changes is that its partial text becomes
                # this role's output instead of ending the row.
                return tolerated
            error.role_id = self.spec.role_id
            error.execution_receipt = {
                "contacts": [dict(contact) for contact in receipt_contacts],
                "final_contact": dict(receipt_contacts[-1]),
            }
            raise
        finally:
            self._model._end_receipt_capture(receipt_token)
            self._end_tool_capture(tool_token)
        actor_output = result.get("output")
        result_type = result.get("result_type")
        if not isinstance(actor_output, str) or not isinstance(result_type, str):
            raise FrozenCoreRoleModelError(
                "OpenJiuwen returned a malformed role result"
            )
        if not receipt_contacts:
            raise FrozenCoreRoleModelError(
                "OpenJiuwen returned a role result without a source-bound contact"
            )
        delivery_eligible = bool(
            self.spec.role_kind == "solver"
            and result_type == "answer"
            and self._delivery_allowed(self.spec.role_id, actor_output)
        )
        role_result: dict[str, object] = {
            "role_id": self.spec.role_id,
            "actor_output": actor_output,
            "result_type": result_type,
            "delivery_eligible": delivery_eligible,
            "execution_receipt": {
                "contacts": [dict(contact) for contact in receipt_contacts],
                "final_contact": dict(receipt_contacts[-1]),
            },
        }
        exhaustion = self._react_exhaustion(
            result_type, actor_output, receipt_contacts, tool_calls
        )
        if exhaustion is not None:
            # E22: present ONLY on this one framework outcome, so every other
            # role result is the exact dict it has always been. It carries no
            # text -- tool ids and digests only.
            role_result["react_exhaustion"] = exhaustion
        return role_result

    def _tolerated_truncation(
        self,
        error: FrozenCoreRoleFiniteCompletionError,
        receipt_contacts: Sequence[Mapping[str, str]],
    ) -> dict[str, object] | None:
        """Item E39: this role's truncated output, or ``None`` to re-raise.

        Four conditions, all required: this role's spec tolerates truncation
        (which the runner sets only for a NON-answering role of an
        ``answering-node`` episode), the completion stopped on ``length`` (a
        ``content_filter`` stop is a refusal, not a partial answer, and keeps
        its pre-E39 whole-episode effect), the completion carries no native
        tool call (a half-rendered call is not an instruction this graph may
        execute), and the truncated text is non-empty (no text is no output,
        and item E13's disposition is the honest record of that). Any one of
        them missing leaves the result exactly as it was before E39 -- the
        refusal the caller re-raises.

        The returned result is the same dict an answering visit returns, plus
        one ``length_truncation`` mark carrying ids and digests only -- never
        text.
        """

        if (
            not self.spec.tolerate_length_truncation
            or error.finish_reason != "length"
            or error.completion.tool_calls
        ):
            return None
        actor_output = error.completion.text
        if not isinstance(actor_output, str) or not actor_output:
            return None
        return {
            "role_id": self.spec.role_id,
            "actor_output": actor_output,
            "result_type": "answer",
            # Item E39: a truncated draft is never delivery-eligible, and no
            # role that can carry this flag is the delivering one anyway.
            "delivery_eligible": False,
            "execution_receipt": {
                "contacts": [dict(contact) for contact in receipt_contacts],
                "final_contact": dict(receipt_contacts[-1]),
            },
            "length_truncation": {
                "role_id": self.spec.role_id,
                "role_kind": self.spec.role_kind,
                "finish_reason": error.finish_reason,
                "contact": _contact_receipt(error.completion),
            },
        }

    def _react_exhaustion(
        self,
        result_type: str,
        actor_output: str,
        receipt_contacts: Sequence[Mapping[str, str]],
        tool_calls: Sequence[Mapping[str, object]],
    ) -> dict[str, object] | None:
        """E22: this invocation's ReAct-exhaustion evidence, or ``None``.

        The class is recognised by ALL of: a tool-bearing role (a role with
        no advertised ability cannot spend its iterations on tool calls), the
        framework's exact exhaustion literal
        (:data:`REACT_EXHAUSTION_OUTPUT`) under ``result_type`` ``"error"``,
        at least one recorded call, and an iteration budget actually spent to
        the end. Any one of them missing leaves the result exactly as it was
        before E22 -- a non-answer the graph refuses.
        """

        if (
            result_type != "error"
            or actor_output != REACT_EXHAUSTION_OUTPUT
            or not self._advertised_names
            or not tool_calls
            or len(receipt_contacts) != self.spec.max_iterations
        ):
            return None
        calls = [
            {
                "tool_id": call["tool_id"],
                "arguments_sha256": call["arguments_sha256"],
            }
            for call in tool_calls
        ]
        signatures = {(call["tool_id"], call["arguments_sha256"]) for call in calls}
        observations = [
            call["observation_sha256"]
            for call in tool_calls
            if call["observation_sha256"] is not None
        ]
        return {
            "role_id": self.spec.role_id,
            "role_kind": self.spec.role_kind,
            "iterations_used": len(receipt_contacts),
            "max_iterations": self.spec.max_iterations,
            "calls": calls,
            # Every call of this loop had the same tool id and the same
            # arguments digest -- the shape the flown failure took (413 of
            # 413 executions of one tool with ``{}``). Vacuously true for a
            # single call, which is what "all of them were the same" means
            # when there is one.
            "identical_calls": len(signatures) == 1,
            "last_observation_sha256": observations[-1] if observations else None,
        }

    async def invoke_direct(self, query: str) -> dict[str, object]:
        """Invoke this component with a fresh public framework session."""
        result = await self._run(query)
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
    "ContactContextProvider",
    "FrozenCoreRoleContextFitError",
    "FrozenCoreRoleFiniteCompletionError",
    "FrozenCoreRoleModel",
    "FrozenCoreRoleModelError",
    "MeteredRoleRequest",
    "NativeRoleContactContext",
    "NativeRoleModelRequest",
    "NativeRoleNode",
    "NativeRoleNodeSpec",
    "NativeRoleWorkflow",
    "REACT_EXHAUSTION_OUTPUT",
    "build_native_role_workflow",
    "project_native_assistant_message",
    "restore_native_assistant_wire_message",
]
