"""Raw native speech keeps source-bound evidence and the prepared request contract."""

import copy
import base64
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRecord
from speech_aware_evidence_acquisition.rails import build_slice_registry
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClientError
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
)
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_runner import (
    run_agent_phase,
    run_program,
)
from speech_aware_evidence_acquisition.rails.runner import (
    RailsRunnerError,
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    NativeRoleSpeechBinding, NativeSpeechRequestError,
)
from test_native_request_regressions import _adapter, _role_request
from test_native_episode_runner import (  # noqa: F401
    _ActualEpisodeHarness,
    _spawn_live_matching_process,
    _knowledge_snapshot,
    _wire_response,
)
from test_rails_core_client_native_tools import _TOOLS, _World, _client, _plan

ARM = "raw-speech-agent-native-tools"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_direct_only_phase_uses_the_shared_raw_client_and_original_audio(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        arm=ARM,
        query_source="speech_audio",
    )
    bodies = []

    def post(_url, body_bytes):
        bodies.append(json.loads(body_bytes))
        return _wire_response("direct raw answer")

    harness.transport._post = post
    program = default_phase_program("phase-direct-only-v1")
    try:
        summary = run_agent_phase(
            phase_name="direct",
            program=program,
            adapter=harness.adapter,
            plan=harness.plan,
            data_root=harness.world.data_root,
            core_client=harness.client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=harness.speech_bindings,
            query_source="speech_audio",
            trace_sink=harness.trace,
            decoding_params={"temperature": 0, "max_tokens": 64},
            material_for_phase=lambda _phase, _context: PhaseMaterial(
                instruction="Answer the original speech.",
                response_format=None,
                contact_id="direct-raw-contact",
                purpose="direct",
            ),
        )
    finally:
        close_summary = harness.close()

    assert len(summary.results) == 1
    assert len(summary.results[0].contacts) == 1
    assert close_summary["request_count"] == 1
    assert len(bodies) == 1
    content = bodies[0]["messages"][1]["content"]
    audio = [part for part in content if part["type"] == "input_audio"]
    assert len(audio) == 1
    assert all(part["type"] != "input_speech_features" for part in content)
    assert base64.b64decode(audio[0]["input_audio"]["data"]) == (
        harness.world.data_root / harness.samples[0].audio_ref.path
    ).read_bytes()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_direct_only_raw_phase_uses_a_registered_slice_with_parent_identity(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), arm=ARM, query_source="speech_audio",
    )
    parent = harness.samples[0]
    # The public client registration path requires the flight-owned registry.
    # This harness normally exercises original audio only, so attach the same
    # real registry constructor before registering the test slice.
    slice_registry = build_slice_registry(
        data_root=harness.world.data_root,
        run_id=harness.plan.run_id,
        samples=harness.samples,
    )
    harness.client._slice_registry = slice_registry  # noqa: SLF001
    harness.client._adapter._slice_registry = slice_registry  # noqa: SLF001
    slice_relpath = slice_registry.slice_relpath(parent.sample_id, 0)
    slice_path = harness.world.data_root / slice_relpath
    slice_path.parent.mkdir(parents=True, exist_ok=True)
    slice_bytes = b"RIFF registered direct raw slice"
    slice_path.write_bytes(slice_bytes)
    record = SliceRecord(
        sample_id=parent.sample_id,
        parent_media_relpath=parent.audio_ref.path,
        parent_sha256=parent.audio_ref.sha256,
        start_seconds=0.0,
        end_seconds=0.5,
        audio_seconds=0.5,
        sample_rate_hz=16000,
        media_relpath=slice_relpath,
        sha256=hashlib.sha256(slice_bytes).hexdigest(),
        bytes=len(slice_bytes),
        iteration=0,
    )
    harness.client.register_slice(record)
    harness.speech_bindings[parent.sample_id] = {
        "packet_id": record.media_relpath,
        "sha256": record.sha256,
    }
    bodies = []
    harness.transport._post = lambda _url, body: (
        bodies.append(json.loads(body)) or _wire_response("slice direct answer")
    )
    program = default_phase_program("phase-direct-only-v1")
    try:
        summary = run_agent_phase(
            phase_name="direct", program=program, adapter=harness.adapter,
            plan=harness.plan, data_root=harness.world.data_root,
            core_client=harness.client, split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=harness.speech_bindings,
            query_source="speech_audio", trace_sink=harness.trace,
            decoding_params={"temperature": 0, "max_tokens": 64},
            material_for_phase=lambda _phase, _context: PhaseMaterial(
                instruction="Answer the registered speech slice.",
                response_format=None, contact_id="direct-slice-contact", purpose="direct",
            ),
        )
    finally:
        harness.close()

    assert summary.results[0].sample_id == parent.sample_id
    audio = [
        part for part in bodies[0]["messages"][1]["content"]
        if part["type"] == "input_audio"
    ]
    assert len(audio) == 1
    assert base64.b64decode(audio[0]["input_audio"]["data"]) == slice_bytes


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_public_direct_raw_phase_keeps_two_registered_windows_of_one_parent(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), arm=ARM, query_source="speech_audio",
    )
    parent = harness.samples[0]
    slice_registry = build_slice_registry(
        data_root=harness.world.data_root,
        run_id=harness.plan.run_id,
        samples=harness.samples,
    )
    harness.client._slice_registry = slice_registry  # noqa: SLF001
    harness.client._adapter._slice_registry = slice_registry  # noqa: SLF001
    units = []
    window_bytes = (b"RIFF registered raw window zero", b"RIFF registered raw window one")
    for iteration, payload in enumerate(window_bytes):
        relpath = slice_registry.slice_relpath(parent.sample_id, iteration)
        path = harness.world.data_root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        units.append(
            ExecutionUnit(
                parent.sample_id,
                f"{parent.sample_id}/window-{iteration}",
                SliceRecord(
                    sample_id=parent.sample_id,
                    parent_media_relpath=parent.audio_ref.path,
                    parent_sha256=parent.audio_ref.sha256,
                    start_seconds=float(iteration), end_seconds=float(iteration + 1),
                    audio_seconds=1.0, sample_rate_hz=16000, media_relpath=relpath,
                    sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload),
                    iteration=iteration,
                ),
            )
        )
    roster = ExecutionUnitRoster(tuple(units))
    bodies = []
    harness.transport._post = lambda _url, body: (
        bodies.append(json.loads(body)) or _wire_response("window direct answer")
    )
    try:
        summary = run_agent_phase(
            phase_name="direct", program=default_phase_program("phase-direct-only-v1"),
            adapter=harness.adapter, plan=harness.plan, data_root=harness.world.data_root,
            core_client=harness.client, split_id="all", knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=harness.speech_bindings, execution_units=roster,
            query_source="speech_audio", trace_sink=harness.trace,
            decoding_params={"temperature": 0, "max_tokens": 64}, expected_row_count=2,
            material_for_phase=lambda _phase, _context: PhaseMaterial(
                instruction="Answer this registered window.", response_format=None,
                contact_id="two-window-direct", purpose="direct",
            ),
        )
    finally:
        close_summary = harness.close()

    assert [result.execution_unit_id for result in summary.results] == [
        "s1/window-0", "s1/window-1"
    ]
    assert close_summary["request_count"] == 2
    assert {
        base64.b64decode(part["input_audio"]["data"])
        for body in bodies
        for part in body["messages"][1]["content"]
        if part["type"] == "input_audio"
    } == set(window_bytes)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_run_program_forwards_raw_query_source_to_direct_phase(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), arm=ARM, query_source="speech_audio",
    )
    bodies = []
    harness.transport._post = lambda _url, body: (
        bodies.append(json.loads(body)) or _wire_response("program direct answer")
    )
    program = default_phase_program("phase-direct-only-v1")
    try:
        summaries = run_program(
            program=program, adapter=harness.adapter, plan=harness.plan,
            data_root=harness.world.data_root, core_client=harness.client,
            split_id="all", knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=harness.speech_bindings,
            query_source="speech_audio", trace_sink=harness.trace,
            decoding_params={"temperature": 0, "max_tokens": 64},
            material_for_phase=lambda _phase, _context, _sealed: PhaseMaterial(
                instruction="Answer through the shared program.", response_format=None,
                contact_id="program-direct-contact", purpose="direct",
            ),
        )
    finally:
        harness.close()

    assert len(summaries) == len(bodies) == 1
    assert any(
        part["type"] == "input_audio" for part in bodies[0]["messages"][1]["content"]
    )


@pytest.mark.parametrize(
    ("arm", "controller_policy_id", "max_contacts"),
    [
        ("speech-feature-query-native-tools", "phase-direct-only-v1", 1),
        (ARM, "phase-direct-evidence-alpha-blend-v1", 1),
        (ARM, "phase-direct-only-v1", 2),
    ],
)
def test_raw_direct_gate_refuses_invalid_arm_or_shape_before_transport(
    tmp_path, arm, controller_policy_id, max_contacts
):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",), arm=arm,
        query_source="speech_features" if arm != ARM else "speech_audio",
    )
    harness.transport._post = lambda *_args: pytest.fail("raw gate touched transport")
    try:
        with pytest.raises(RailsRunnerError, match="speech_audio requires"):
            run_speech_native_agent_loop(
                data_root=harness.world.data_root, plan=harness.plan,
                adapter=harness.adapter, core_client=harness.client, split_id="all",
                knowledge_snapshot=_knowledge_snapshot(),
                speech_packet_bindings=harness.speech_bindings,
                query_source="speech_audio", controller_policy_id=controller_policy_id,
                max_contacts=max_contacts, slot_count=1, queue_depth=1,
                trace_sink=harness.trace, agent_executor_id="openjiuwen-workflow-v1",
            )
    finally:
        harness.close()


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
