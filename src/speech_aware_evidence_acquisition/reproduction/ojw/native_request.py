"""Bind public OpenJiuwen turns to the shared prepared speech request path."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from ...core.model.native_framework_history import framework_contact_instruction
from ...rails.core_client import CoreCompletion, FrozenCoreClient, PreparedCoreRequest
from .native_roles import NativeRoleModelRequest


class NativeSpeechRequestError(ValueError):
    """Framework inputs differ from their registered speech/role binding."""


def _bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class NativeRoleSpeechBinding:
    """One caller-owned task state, rendered through the existing TaskAdapter."""

    role_id: str
    sample_id: str
    role_query: str
    base_messages: Sequence[Mapping[str, object]]
    core_kwargs: Mapping[str, object]
    tool_names: tuple[str, ...]
    local_tool_result_ids: tuple[str, ...] = ()
    _messages_bytes: bytes = field(init=False, repr=False)
    _kwargs_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self):
        for value in (self.role_id, self.sample_id, self.role_query):
            if not isinstance(value, str) or not value:
                raise NativeSpeechRequestError("role, sample and query must be nonempty")
        for values in (self.tool_names, self.local_tool_result_ids):
            if (
                not isinstance(values, tuple) or len(set(values)) != len(values)
                or any(not isinstance(x, str) or not x for x in values)
            ):
                raise NativeSpeechRequestError("tool and local result IDs must be ordered unique tuples")
        kwargs = dict(self.core_kwargs)
        reserved = {
            "agent_contact_id", "contact_instruction", "tool_names", "prepare_only",
            "text_only_sample_id", "speech_feature_sample_id",
        }
        if set(kwargs) & reserved:
            raise NativeSpeechRequestError("binding overrides a controlled request field")
        if "agent_state" not in kwargs:
            raise NativeSpeechRequestError("binding must name the complete ordered agent state")
        messages = list(self.base_messages)
        if (
            len(messages) != 2 or messages[0].get("role") != "system"
            or not isinstance(messages[0].get("content"), str)
            or messages[1].get("role") != "user"
        ):
            raise NativeSpeechRequestError("binding requires shared system/user speech messages")
        object.__setattr__(self, "_messages_bytes", _bytes(messages))
        object.__setattr__(self, "_kwargs_bytes", _bytes(kwargs))

    def messages(self):
        return json.loads(self._messages_bytes)

    def kwargs(self):
        return json.loads(self._kwargs_bytes)


@dataclass(frozen=True)
class PreparedNativeRoleContact:
    """Actual immutable request and rendered body exposed for existing fit checks."""

    request: PreparedCoreRequest
    role_request: NativeRoleModelRequest
    body_bytes: bytes

    def rendered_body(self) -> dict[str, object]:
        return json.loads(self.body_bytes)


class MeteredNativeSpeechRequest:
    """Use one flight client; delegate state and contact custody to its caller.

    The binding provider uses the existing TaskAdapter/AgentRuntimeContext.
    The completion sink uses the existing phase-state sealing path. This
    adapter neither stores conversation history nor executes tool backends.
    """

    def __init__(
        self, *, client: FrozenCoreClient,
        binding_provider: Callable[[NativeRoleModelRequest], NativeRoleSpeechBinding],
        render_request: Callable[[bytes], Mapping[str, object]],
        completion_sink: Callable[[NativeRoleModelRequest, CoreCompletion], None],
    ):
        if not isinstance(client, FrozenCoreClient):
            raise NativeSpeechRequestError("use the flight's existing FrozenCoreClient")
        if not all(callable(x) for x in (binding_provider, render_request, completion_sink)):
            raise NativeSpeechRequestError("binding, rendering and completion hooks are required")
        self._client = client
        self._binding_provider = binding_provider
        self._render_request = render_request
        self._completion_sink = completion_sink

    def prepare(self, request: NativeRoleModelRequest) -> PreparedNativeRoleContact:
        binding = self._binding_provider(request)
        if not isinstance(binding, NativeRoleSpeechBinding):
            raise NativeSpeechRequestError("binding provider returned no speech binding")
        if (
            request.role_id != binding.role_id
            or request.context.sample_id != binding.sample_id
            or request.visible_tool_names != binding.tool_names
        ):
            raise NativeSpeechRequestError("framework role, sample or tool scope differs")
        messages = binding.messages()
        if (
            len(request.messages) < 2
            or dict(request.messages[0]) != messages[0]
            or dict(request.messages[1]) != {"role": "user", "content": binding.role_query}
        ):
            raise NativeSpeechRequestError("framework system or original query differs")
        kwargs = binding.kwargs()
        decoding = dict(kwargs.get("decoding_params") or {})
        expected_choice = "auto" if binding.tool_names else "none"
        if decoding.get("tool_choice", expected_choice) != expected_choice:
            raise NativeSpeechRequestError("registered tool choice differs from role scope")
        if decoding.get("parallel_tool_calls", False) is not False:
            raise NativeSpeechRequestError("this role binding requires sequential native calls")
        # The registered flight owns decoding settings. Framework defaults
        # may repeat them, but cannot silently change the actual request.
        for key, value in request.decoding_controls.items():
            if key not in decoding or decoding[key] != value:
                raise NativeSpeechRequestError("framework decoding override is not registered: " + key)
        decoding.update(tool_choice=expected_choice, parallel_tool_calls=False)
        kwargs["decoding_params"] = decoding
        instruction = framework_contact_instruction(
            role_id=binding.role_id, sample_id=binding.sample_id,
            contact_id=request.context.agent_contact_id, messages=request.messages,
            local_tool_result_ids=binding.local_tool_result_ids,
        )
        prepared = self._client.prepare_request(
            messages, **kwargs, speech_feature_sample_id=binding.sample_id,
            agent_contact_id=request.context.agent_contact_id,
            contact_instruction=instruction, tool_names=binding.tool_names,
        )
        payload = prepared.as_payload()
        selected = payload.get("tool_schemas", [])
        if len(request.tool_schemas) != len(selected):
            raise NativeSpeechRequestError("framework schemas do not match the selected scope")
        for visible, schema in zip(request.tool_schemas, selected, strict=True):
            function = schema["function"]
            if any(visible.get(key) != function.get(key) for key in ("name", "description", "parameters")):
                raise NativeSpeechRequestError("framework tool schema differs from the registered tool")
        # The authoritative transport validates and renders the SAME object
        # that dispatch consumes; capacity checks can inspect this body.
        body = self._render_request(prepared.payload_bytes)
        return PreparedNativeRoleContact(prepared, request, _bytes(body))

    def dispatch(self, prepared: PreparedNativeRoleContact) -> CoreCompletion:
        if not isinstance(prepared, PreparedNativeRoleContact):
            raise NativeSpeechRequestError("dispatch requires a prepared native contact")
        completion = self._client.complete_prepared_with_metadata(prepared.request)
        self._completion_sink(prepared.role_request, completion)
        return completion

    def __call__(self, request: NativeRoleModelRequest) -> CoreCompletion:
        return self.dispatch(self.prepare(request))
