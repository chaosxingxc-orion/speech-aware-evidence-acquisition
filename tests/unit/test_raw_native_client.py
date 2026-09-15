"""Raw native speech keeps source-bound evidence and the prepared request contract."""

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRecord
from speech_aware_evidence_acquisition.rails import build_slice_registry
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClientError
from speech_aware_evidence_acquisition.rails.runner import RailsRunnerError
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    NativeRoleSpeechBinding, NativeSpeechRequestError,
)
from test_native_request_regressions import _adapter, _role_request
from test_native_episode_runner import (  # noqa: F401
    _ActualEpisodeHarness,
    _spawn_live_matching_process,
)
from test_rails_core_client_native_tools import _TOOLS, _World, _client, _plan

ARM = "raw-speech-agent-native-tools"


def messages(world):
    return [
        {"role": "system", "content": "Choose exactly one opaque key id."},
        {"role": "user", "content": [
            {"type": "input_audio", "media_relpath": world.media_relpath("s1")},
            {"type": "text", "text": "A named alarm can be checked.",
             "evidence_id": "contract:alarm", "source_uri": "test://contract/alarm",
             "knowledge_role": "value"},
        ]},
    ]


def arguments():
    return {
        "raw_agent_sample_id": "s1", "agent_state": (),
        "agent_contact_id": "review-1", "contact_instruction": "Review the speech.",
        "tool_names": ("setAlarm",),
        "decoding_params": {"tool_choice": "auto", "parallel_tool_calls": False},
    }


def test_raw_preparation_preserves_supplied_identity_and_one_use(tmp_path):
    world = _World(tmp_path)
    client, gate, transport = _client(world, tmp_path, arm=ARM, tool_schemas=_TOOLS)
    constructor_gate_calls = list(gate.checked_plans)
    prepared = client.prepare_request(messages(world), **arguments())
    before = prepared.as_payload()
    assert transport.calls == []
    assert gate.checked_plans == constructor_gate_calls
    assert before["media_relpath"] == world.media_relpath("s1")
    assert before["raw_speech_query"] == {
        "media_relpath": world.media_relpath("s1"),
        "sha256": hashlib.sha256(
            (world.data_root / world.media_relpath("s1")).read_bytes()
        ).hexdigest(),
    }
    assert "speech_feature_parts" not in before
    assert before["supplied_evidence"][0]["evidence_id"] == "contract:alarm"
    assert before["supplied_evidence"][0]["source_uri"] == "test://contract/alarm"
    client.complete_prepared(prepared)
    sent = transport.calls[0]
    assert sent["supplied_evidence"] == before["supplied_evidence"]
    assert sent["history"] == before["history"]
    assert sent["media_relpath"] == before["media_relpath"]
    with pytest.raises(FrozenCoreClientError):
        client.complete_prepared(prepared)
    assert len(transport.calls) == 1


@pytest.mark.parametrize("change", ["wrong_sample", "missing_opt_in", "text_mode", "feature_mode", "missing_evidence_id", "missing_source", "two_audio"])
def test_raw_native_binding_refuses_ambiguous_inputs_before_post(tmp_path, change):
    world = _World(tmp_path)
    client, gate, transport = _client(world, tmp_path, arm=ARM, tool_schemas=_TOOLS)
    constructor_gate_calls = list(gate.checked_plans)
    raw, kwargs = messages(world), arguments()
    if change == "wrong_sample":
        kwargs["raw_agent_sample_id"] = "s2"
    elif change == "missing_opt_in":
        kwargs.pop("raw_agent_sample_id")
    elif change == "text_mode":
        kwargs["text_only_sample_id"] = "s1"
    elif change == "feature_mode":
        kwargs["speech_feature_sample_id"] = "s1"
    elif change == "missing_evidence_id":
        raw[1]["content"][1].pop("evidence_id")
    elif change == "missing_source":
        raw[1]["content"][1].pop("source_uri")
    else:
        raw[1]["content"].append(copy.deepcopy(raw[1]["content"][0]))
    with pytest.raises(FrozenCoreClientError):
        client.prepare_request(raw, **kwargs)
    assert transport.calls == []
    assert gate.checked_plans == constructor_gate_calls


def test_raw_native_opt_in_does_not_relax_legacy_arms(tmp_path):
    world = _World(tmp_path)
    client, gate, transport = _client(world, tmp_path, arm="bare-core-native-tools", tool_schemas=_TOOLS)
    constructor_gate_calls = list(gate.checked_plans)
    with pytest.raises(FrozenCoreClientError):
        client.prepare_request(messages(world), **arguments())
    assert not transport.calls
    assert gate.checked_plans == constructor_gate_calls


def test_raw_source_mutation_after_prepare_is_refused_and_consumes_request(tmp_path):
    world = _World(tmp_path)
    client, gate, transport = _client(world, tmp_path, arm=ARM, tool_schemas=_TOOLS)
    constructor_gate_calls = list(gate.checked_plans)
    prepared = client.prepare_request(messages(world), **arguments())
    source = world.data_root / world.media_relpath("s1")
    source.write_bytes(source.read_bytes() + b"post-prepare mutation")

    with pytest.raises(FrozenCoreClientError, match="bytes changed after preparation"):
        client.complete_prepared(prepared)
    with pytest.raises(FrozenCoreClientError, match="foreign, changed or consumed"):
        client.complete_prepared(prepared)

    assert transport.calls == []
    assert gate.checked_plans == constructor_gate_calls


def test_registered_slice_identity_and_audio_facts_replace_parent_facts(tmp_path):
    world = _World(tmp_path)
    plan = _plan()
    registry = build_slice_registry(
        data_root=world.data_root, run_id=plan.run_id, samples=world.samples
    )
    client, gate, transport = _client(
        world, tmp_path, arm=ARM, tool_schemas=_TOOLS,
        plan=plan, slice_registry=registry,
    )
    constructor_gate_calls = list(gate.checked_plans)
    parent_relpath = world.media_relpath("s1")
    parent_path = world.data_root / parent_relpath
    slice_relpath = registry.slice_relpath("s1", 0)
    slice_path = world.data_root / slice_relpath
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_bytes = b"RIFF synthetic registered raw slice"
    slice_path.write_bytes(slice_bytes)
    record = SliceRecord(
        sample_id="s1",
        parent_media_relpath=parent_relpath,
        parent_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),
        start_seconds=0.25,
        end_seconds=1.5,
        audio_seconds=1.25,
        sample_rate_hz=8000,
        media_relpath=slice_relpath,
        sha256=hashlib.sha256(slice_bytes).hexdigest(),
        bytes=len(slice_bytes),
        iteration=0,
    )
    client.register_slice(record)
    raw_messages = messages(world)
    raw_messages[1]["content"][0]["media_relpath"] = slice_relpath

    prepared = client.prepare_request(raw_messages, **arguments())
    payload = prepared.as_payload()

    assert payload["raw_speech_query"] == {
        "media_relpath": slice_relpath,
        "sha256": record.sha256,
    }
    assert payload["audio_seconds"] == record.audio_seconds
    assert payload["sample_rate_hz"] == record.sample_rate_hz
    assert payload["raw_speech_query"]["sha256"] != hashlib.sha256(
        parent_path.read_bytes()
    ).hexdigest()
    assert transport.calls == []
    assert gate.checked_plans == constructor_gate_calls


def test_native_callback_uses_raw_binding_and_shared_prepared_contact(tmp_path):
    world = _World(tmp_path)
    client, gate, transport = _client(world, tmp_path, arm=ARM, tool_schemas=_TOOLS)
    kwargs = arguments()
    for key in ("raw_agent_sample_id", "agent_contact_id", "contact_instruction", "tool_names"):
        kwargs.pop(key)
    binding = NativeRoleSpeechBinding(
        role_id="reviewer", sample_id="s1", role_query="Inspect the speech.",
        base_messages=messages(world), core_kwargs=kwargs,
        tool_names=("setAlarm",), query_source="speech_audio",
    )
    sink = []
    adapter = _adapter(client, binding, sink)
    request = _role_request(role_id="reviewer", contact_id="review-1", packet=None)
    prepared = adapter.prepare(request)
    assert not transport.calls
    body = prepared.rendered_body()
    assert body["media_relpath"] == world.media_relpath("s1")
    assert "speech_feature_parts" not in body
    adapter.dispatch(prepared)
    assert len(transport.calls) == len(sink) == 1
    assert json.loads(transport.calls[0]["history"][-1]["content"])["contact_id"] == "review-1"


def test_raw_binding_cannot_override_its_source_selector(tmp_path):
    world = _World(tmp_path)
    with pytest.raises(NativeSpeechRequestError):
        NativeRoleSpeechBinding(
            role_id="reviewer", sample_id="s1", role_query="Inspect the speech.",
            base_messages=messages(world),
            core_kwargs={"agent_state": (), "raw_agent_sample_id": "s2"},
            tool_names=(), query_source="speech_audio",
        )


def test_public_native_runner_preserves_one_raw_query_and_reviewer_tool_history(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        arm=ARM,
        reviewer_task_tool=True,
        query_source="speech_audio",
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert summary.results[0].final_response_text == "solver-answer:s1:visit:2"
    assert close_summary["request_count"] == 8
    assert close_summary["cost"]["tool_calls"] == 1
    assert len(harness.tool_contacts) == 1
    for prepared in harness.prepared.values():
        body = prepared["rendered"]
        serialized = json.dumps(body)
        audio_parts = [
            part
            for message in body["messages"]
            if isinstance(message.get("content"), list)
            for part in message["content"]
            if part.get("type") == "input_audio"
        ]
        assert len(audio_parts) == 1
        assert "input_speech_features" not in serialized
    reviewer_next = harness.prepared[("s1", "reviewer", 1, 2)]["rendered"]
    tool_messages = [
        message for message in reviewer_next["messages"] if message["role"] == "tool"
    ]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call-task-contract-1"
    assert json.loads(tool_messages[0]["content"])["result"] == {
        "task_contract": "task-contract-for-s1"
    }


@pytest.mark.parametrize(
    "change",
    ["invalid_source", "missing_identity", "mismatched_identity", "foreign_identity"],
)
def test_public_native_runner_refuses_bad_raw_source_before_fit(tmp_path, change):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        arm=ARM,
        query_source="speech_audio",
    )
    if change == "invalid_source":
        harness.query_source = "generated_text"
    elif change == "missing_identity":
        harness.speech_bindings["s1"] = {
            "packet_id": harness.speech_bindings["s1"]["packet_id"]
        }
    elif change == "mismatched_identity":
        harness.speech_bindings["s1"] = {
            **harness.speech_bindings["s1"],
            "sha256": "0" * 64,
        }
    else:
        foreign_path = "datasets/fake-carrier/media/foreign.wav"
        foreign_file = harness.world.data_root / foreign_path
        foreign_file.write_bytes(b"RIFF foreign synthetic speech")
        harness.speech_bindings["s1"] = {
            "packet_id": foreign_path,
            "sha256": hashlib.sha256(foreign_file.read_bytes()).hexdigest(),
        }
    try:
        with pytest.raises(RailsRunnerError):
            harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 0
    assert harness.prepared == harness.dispatched == {}


@pytest.mark.parametrize(
    ("arm", "built_source", "requested_source"),
    [
        ("speech-feature-query-native-tools", "speech_features", "speech_audio"),
        (ARM, "speech_audio", "speech_features"),
    ],
)
def test_public_native_runner_refuses_mixed_client_and_query_source(
    tmp_path, arm, built_source, requested_source,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        arm=arm,
        query_source=built_source,
    )
    harness.query_source = requested_source
    try:
        with pytest.raises(RailsRunnerError):
            harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 0
    assert harness.prepared == harness.dispatched == {}
