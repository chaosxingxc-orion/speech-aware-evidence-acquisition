"""E2 (SLURP v2 base program M2): grouped-Solver decoding composition.

Proves ``reproduction.ojw.native_request.MeteredNativeSpeechRequest`` applies
the registered Solver ``decoding_overrides`` only to the registered Solver
role, only when a ``sample_index`` is bound, that N sibling requests of one
Solver visit are byte-identical except ``seed`` (and ``temperature`` versus
the fragment's own greedy value), that ``seed = fragment_seed + seed_offset +
sample_index``, and that every other role/contact is refused a
``sample_index`` and untouched by the override.
"""

from __future__ import annotations

import json
from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    MeteredNativeSpeechRequest,
    NativeRoleSpeechBinding,
    NativeSpeechRequestError,
    compose_solver_sample_decoding_params,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext, NativeRoleModelRequest,
)
from test_rails_core_client_native_tools import (
    _TOOLS,
    _World,
    _client,
    _speech_feature_messages,
    _speech_feature_world,
)

FRAGMENT_SEED = 1000
DECODING_OVERRIDES = {"temperature": 0.7, "seed_offset": 5}


def _role_request(*, role_id, contact_id, sample_index=None):
    visible = _TOOLS[1]["function"]
    return NativeRoleModelRequest(
        role_id=role_id,
        context=NativeRoleContactContext(
            sample_id="s1", agent_contact_id=contact_id, sample_index=sample_index,
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


def _binding(*, role_id, packet):
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
                "max_tokens": 256,
            },
        },
        tool_names=("setAlarm",),
    )


def _adapter(client, binding, sink, *, solver_role_id=None, solver_sampling=None):
    return MeteredNativeSpeechRequest(
        client=client,
        binding_provider=lambda _request: binding,
        render_request=lambda payload: json.loads(payload),
        completion_sink=lambda request, completion: sink.append((request, completion)),
        solver_role_id=solver_role_id,
        solver_sampling=solver_sampling,
    )


def _prepared_decoding(tmp_path, *, sample_index):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, _transport = _client(
        world, tmp_path, arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    adapter = _adapter(
        client, _binding(role_id="solver", packet=packet), [],
        solver_role_id="solver",
        solver_sampling={"fragment_seed": FRAGMENT_SEED, "decoding_overrides": DECODING_OVERRIDES},
    )
    request = _role_request(role_id="solver", contact_id=f"contact-{sample_index}", sample_index=sample_index)
    prepared = adapter.prepare(request)
    return prepared, prepared.rendered_body()["decoding_params"]


def test_compose_solver_sample_decoding_params_changes_only_temperature_and_seed():
    base = {"tool_choice": "auto", "parallel_tool_calls": False, "max_tokens": 256}
    composed0 = compose_solver_sample_decoding_params(
        base, fragment_seed=FRAGMENT_SEED, decoding_overrides=DECODING_OVERRIDES, sample_index=0,
    )
    composed1 = compose_solver_sample_decoding_params(
        base, fragment_seed=FRAGMENT_SEED, decoding_overrides=DECODING_OVERRIDES, sample_index=1,
    )
    assert composed0["seed"] == FRAGMENT_SEED + DECODING_OVERRIDES["seed_offset"] + 0
    assert composed1["seed"] == FRAGMENT_SEED + DECODING_OVERRIDES["seed_offset"] + 1
    assert composed0["temperature"] == composed1["temperature"] == DECODING_OVERRIDES["temperature"]
    for key in ("tool_choice", "parallel_tool_calls", "max_tokens"):
        assert composed0[key] == composed1[key] == base[key]
    assert set(composed0) - {"seed", "temperature"} == set(base) - {"seed", "temperature"}


@pytest.mark.parametrize("bad_overrides", [
    {"temperature": 0.7},
    {"seed_offset": 0},
    {"temperature": True, "seed_offset": 0},
    {"temperature": 0.7, "seed_offset": -1},
    {"temperature": 0.7, "seed_offset": True},
])
def test_compose_solver_sample_decoding_params_validates_overrides(bad_overrides):
    with pytest.raises(NativeSpeechRequestError):
        compose_solver_sample_decoding_params(
            {}, fragment_seed=1, decoding_overrides=bad_overrides, sample_index=0,
        )


def test_n_sample_requests_of_one_solver_visit_differ_only_by_seed(tmp_path):
    prepared = []
    decodings = []
    for sample_index in range(3):
        one_prepared, decoding = _prepared_decoding(tmp_path / str(sample_index), sample_index=sample_index)
        prepared.append(one_prepared)
        decodings.append(decoding)

    seeds = [decoding["seed"] for decoding in decodings]
    assert seeds == [FRAGMENT_SEED + DECODING_OVERRIDES["seed_offset"] + i for i in range(3)]
    assert len(set(seeds)) == 3
    temperatures = {decoding["temperature"] for decoding in decodings}
    assert temperatures == {DECODING_OVERRIDES["temperature"]}
    for decoding in decodings:
        stripped = {k: v for k, v in decoding.items() if k not in {"seed", "temperature"}}
        assert stripped == {
            k: v for k, v in decodings[0].items() if k not in {"seed", "temperature"}
        }
    assert [p.sample_index for p in prepared] == [0, 1, 2]


def test_only_the_registered_solver_role_may_bind_a_sample_index(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, _transport = _client(
        world, tmp_path, arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    adapter = _adapter(
        client, _binding(role_id="reviewer", packet=packet), [],
        solver_role_id="solver",
        solver_sampling={"fragment_seed": FRAGMENT_SEED, "decoding_overrides": DECODING_OVERRIDES},
    )
    request = _role_request(role_id="reviewer", contact_id="contact-x", sample_index=0)
    with pytest.raises(NativeSpeechRequestError, match="sample_index"):
        adapter.prepare(request)


def test_grouped_solver_contact_requires_a_bound_sample_index(tmp_path):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, _transport = _client(
        world, tmp_path, arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    adapter = _adapter(
        client, _binding(role_id="solver", packet=packet), [],
        solver_role_id="solver",
        solver_sampling={"fragment_seed": FRAGMENT_SEED, "decoding_overrides": DECODING_OVERRIDES},
    )
    request = _role_request(role_id="solver", contact_id="contact-x", sample_index=None)
    with pytest.raises(NativeSpeechRequestError, match="sample_index"):
        adapter.prepare(request)


def test_samples_one_ungrouped_adapter_is_unaffected(tmp_path):
    """No solver_role_id/solver_sampling bound at all: byte-identical to
    today's behaviour (the regression the E2 spec requires)."""

    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _gate, _transport = _client(
        world, tmp_path, arm="speech-feature-query-native-tools",
        tool_schemas=_TOOLS, speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    adapter = _adapter(client, _binding(role_id="solver", packet=packet), [])
    request = _role_request(role_id="solver", contact_id="contact-x")
    prepared = adapter.prepare(request)
    decoding = prepared.rendered_body()["decoding_params"]
    assert "seed" not in decoding
    assert prepared.sample_index is None
