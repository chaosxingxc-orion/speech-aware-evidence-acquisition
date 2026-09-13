"""Synthetic regressions for prepared native speech request ownership."""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    MeteredNativeSpeechRequest,
    NativeRoleSpeechBinding,
    NativeSpeechRequestError,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext,
    NativeRoleModelRequest,
)
from test_rails_core_client_native_tools import (
    _TOOLS,
    _World,
    _client,
    _speech_feature_messages,
    _speech_feature_world,
)


def _role_request(
    *,
    role_id: str,
    contact_id: str,
    packet,
) -> NativeRoleModelRequest:
    visible = _TOOLS[1]["function"]
    return NativeRoleModelRequest(
        role_id=role_id,
        context=NativeRoleContactContext(
            sample_id="s1",
            agent_contact_id=contact_id,
        ),
        messages=(
            {"role": "system", "content": "Choose exactly one opaque key id."},
            {"role": "user", "content": "Inspect the speech."},
        ),
        tool_schemas=(
            {
                "name": visible["name"],
                "description": visible["description"],
                "parameters": visible["parameters"],
            },
        ),
        visible_tool_names=("setAlarm",),
        decoding_controls=MappingProxyType({}),
    )


def _binding(*, role_id: str, packet) -> NativeRoleSpeechBinding:
    return NativeRoleSpeechBinding(
        role_id=role_id,
        sample_id="s1",
        role_query="Inspect the speech.",
        base_messages=_speech_feature_messages(packet),
        core_kwargs={
            "agent_state": (),
            "key_representation_id": "key-v1",
            "matcher_policy_id": "matcher-v1",
            "decoding_params": {
                "tool_choice": "auto",
                "parallel_tool_calls": False,
            },
        },
        tool_names=("setAlarm",),
    )


def _adapter(client, binding, sink):
    return MeteredNativeSpeechRequest(
        client=client,
        binding_provider=lambda _request: binding,
        render_request=lambda payload: json.loads(payload),
        completion_sink=lambda request, completion: sink.append(
            (request, completion)
        ),
    )


def test_prepared_contact_cannot_cross_dispatch_adapters_before_post(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS,
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    request = _role_request(role_id="reviewer", contact_id="contact-a", packet=packet)
    prepared = _adapter(
        client,
        _binding(role_id="reviewer", packet=packet),
        [],
    ).prepare(request)
    foreign_sink = []
    foreign_adapter = _adapter(
        client,
        _binding(role_id="planner", packet=packet),
        foreign_sink,
    )

    with pytest.raises(NativeSpeechRequestError):
        foreign_adapter.dispatch(prepared)

    assert transport.calls == []
    assert foreign_sink == []


def test_prepared_contact_snapshots_nested_role_request_before_dispatch(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS,
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    sink = []
    adapter = _adapter(
        client,
        _binding(role_id="reviewer", packet=packet),
        sink,
    )
    request = _role_request(
        role_id="reviewer",
        contact_id="contact-a",
        packet=packet,
    )
    prepared = adapter.prepare(request)

    request.messages[0]["content"] = "tampered system"
    request.tool_schemas[0]["description"] = "tampered schema"

    adapter.dispatch(prepared)

    assert len(transport.calls) == 1
    sent_control = json.loads(transport.calls[0]["history"][-1]["content"])
    assert sent_control["messages"][0]["content"] == (
        "Choose exactly one opaque key id."
    )
    assert sent_control["messages"][1]["content"] == "Inspect the speech."
    assert len(sink) == 1
    sunk_request, _completion = sink[0]
    assert sunk_request.messages[0]["content"] == (
        "Choose exactly one opaque key id."
    )
    assert sunk_request.tool_schemas[0]["description"] == _TOOLS[1]["function"][
        "description"
    ]
