"""Prove template compatibility through the installed native role callback."""

import asyncio
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.instructions import render_template_with_fill
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    MeteredNativeSpeechRequest,
    NativeRoleSpeechBinding,
    NativeSpeechRequestError,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
)
from test_rails_core_client_native_tools import (
    _TOOLS,
    _World,
    _client,
    _speech_feature_messages,
    _speech_feature_world,
)


class _PreparedOnly(RuntimeError):
    """End the framework callback before dispatch."""


@pytest.mark.parametrize("version,tamper,accepted", [
    ("v2", False, False),
    ("v3", False, True),
    ("v3", True, False),
])
def test_native_template_callback_reaches_exact_preparation(
    tmp_path, slurp_world, version, tamper, accepted,
):
    repo = Path(__file__).resolve().parents[2]
    prompt = render_template_with_fill(
        f"probes/slurp_native_role_context_{version}.txt",
        "slurp-label-inventory", repo,
        load_lock(slurp_world.lock_path), slurp_world.data_root,
    )
    assert (prompt == prompt.strip()) is (version == "v3")
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world, tmp_path, arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    query = 'Return candidates as {"hypotheses": []}.\n'
    messages = list(_speech_feature_messages(packet))
    messages[0] = {"role": "system", "content": prompt + (" changed" if tamper else "")}
    binding = NativeRoleSpeechBinding(
        role_id="perception", sample_id="s1", role_query=query,
        base_messages=messages,
        core_kwargs={
            "agent_state": (),
            "key_representation_id": "key-v1",
            "matcher_policy_id": "matcher-v1",
        },
        tool_names=(),
    )
    prepared, requests, failures = [], [], []
    adapter = MeteredNativeSpeechRequest(
        client=client, binding_provider=lambda request: binding,
        render_request=json.loads,
        completion_sink=lambda request, completion: pytest.fail("No dispatch"),
    )

    def prepare_only(request):
        requests.append(request)
        try:
            prepared.append(adapter.prepare(request))
        except NativeSpeechRequestError as error:
            failures.append(str(error))
            raise
        raise _PreparedOnly("Preparation completed; do not dispatch")

    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="perception", role_kind="perception",
            prompt=prompt, max_iterations=1,
        ),
        metered_request=prepare_only,
        contact_context=NativeRoleContactContext(
            sample_id="s1", agent_contact_id="contact-1",
        ),
        abilities=(),
    )

    async def exercise():
        try:
            with pytest.raises(Exception):
                await node.invoke_direct(query)
        finally:
            await node.close()

    asyncio.run(exercise())
    assert len(requests) == 1
    assert requests[0].messages[0]["content"] == prompt.strip()
    assert requests[0].messages[1]["content"] == query
    assert len(prepared) == int(accepted)
    assert failures == ([] if accepted else ["framework system or original query differs"])
    assert transport.calls == []
    if accepted:
        assert prepared[0].role_request.messages[0]["content"] == prompt
        assert prepared[0].role_request.messages[1]["content"] == query
