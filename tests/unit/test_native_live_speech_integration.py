"""Full native tool loop with real shared client, executor, dispatcher and provider."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.controllers import (
    EvidenceAgentController,
    default_phase_program,
)
from speech_aware_evidence_acquisition.rails.live_speech_observation import (
    LiveSpeechObservationProvider,
)
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_tools import (
    LIVE_SPEECH_OBSERVATION_TOOL as LIVE,
    PHASE_KNOWLEDGE_TOOL as KNOWLEDGE,
    build_phase_tools,
)
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_live_speech_observation import (
    FakeBackend,
    inventory,
    protocol,
    resolved_source,
)
from test_rails_controllers import _phase_supply
from test_rails_frozen_core_client import _World, _client, _plan, _speech_feature_world
from test_rails_runner import _FakeAdapter, _controller_registry, _knowledge_snapshot


ARGS = {
    "span": "full-utterance",
    "representation": "asr-transcript",
    "distinction": "Resolve the spoken command.",
}


class ScenarioTransport:
    def __init__(self, scenario):
        self.scenario = scenario
        self.calls = []

    def __call__(self, request_bytes):
        payload = json.loads(request_bytes)
        self.calls.append(payload)
        sample = payload["sample_id"]
        phase = payload["history"][-1]["contact_id"].rsplit(":", 1)[-1]
        calls = self._calls(sample, phase)
        if calls is None:
            text = f"final-answer-{sample}-{phase}"
        else:
            canonical = []
            for call in calls:
                raw = call["function"]["arguments"]
                try:
                    arguments = json.loads(raw)
                except (TypeError, ValueError):
                    arguments = {}
                canonical.append({
                    "name": call["function"]["name"],
                    "arguments": arguments,
                })
            text = json.dumps(canonical)
        return json.dumps({
            "text": text,
            "usage": {"prompt_tokens": 8, "completion_tokens": 4},
            "tool_calls": calls,
        }).encode()

    def _calls(self, sample, phase):
        if sample == "s1":
            return None
        if self.scenario == "live-then-knowledge":
            if phase == "decision-1":
                return native_call(LIVE, ARGS)
            if phase == "decision-2":
                return native_call(KNOWLEDGE, {"view": "text"})
            return None
        if self.scenario == "repeat-live":
            return native_call(LIVE, ARGS) if phase != "final" else None
        if self.scenario == "malformed":
            if phase == "decision-1":
                return native_call(LIVE, ARGS) * 2
            return None
        raise AssertionError(self.scenario)


def native_call(name, arguments):
    return [{
        "id": f"call-{name}",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]


def build_system(tmp_path, scenario):
    world = _World(tmp_path)
    feature_root, _packet, packet_bindings = _speech_feature_world(world, tmp_path)
    base_snapshot = _knowledge_snapshot()
    prototype = base_snapshot.values[0]
    snapshot = replace(
        base_snapshot,
        values=tuple(
            replace(
                prototype,
                value_id=f"value:dim-light-{index}",
                content=f"Knowledge value {index}: use the dim-light operation.",
            )
            for index in range(5)
        ),
    ).validate()
    source_bindings = {
        sample.sample_id: {
            "packet_id": packet_bindings[sample.sample_id]["packet_id"],
            "packet_sha256": packet_bindings[sample.sample_id]["sha256"],
            "source_audio_relpath": sample.audio_ref.path,
            "source_audio_sha256": sample.audio_ref.sha256,
            "source_audio_duration_seconds": sample.audio_seconds,
        }
        for sample in world.samples
    }
    backend_events = []
    asr_contacts = []

    def asr_contact(**facts):
        asr_contacts.append(facts)
        return {"contact_id": f"asr-{len(asr_contacts)}"}

    def backend_factory(actual_inventory, actual_protocol, data_root, event):
        backend_events.append(("backend", actual_protocol["device"]))
        return FakeBackend(backend_events, event=event)

    provider = LiveSpeechObservationProvider(
        inventory=inventory(),
        protocol=protocol(),
        source_bindings=source_bindings,
        data_root=world.data_root,
        output_root=tmp_path / "live-observations",
        contact=asr_contact,
        backend_factory=backend_factory,
        host_memory_guard=lambda: backend_events.append(("guard", None)),
        source_resolver=lambda binding: resolved_source(binding),
    )
    client_box = {}
    custody = []

    def tool_contact(**facts):
        client_box["client"].record_tool_call()
        custody.append(facts)
        return {
            "invocation_id": f"internal-{len(custody)}",
            "sample_id": facts["sample_id"],
            "phase": facts["phase"],
            "tool_id": facts["tool_id"],
            "source_response_sha256": facts["source_response_sha256"],
        }

    config = {
        "phase_tools": {
            phase: {
                "mode": "native-tools",
                "allowed_tools": [LIVE, KNOWLEDGE],
                "knowledge_views": ["text"],
            }
            for phase in ("decision-1", "decision-2")
        }
    }

    def supply(_next_phase, context):
        return _phase_supply(
            context,
            value_ids=tuple(value.value_id for value in snapshot.values),
            facet_ids=(snapshot.facets[0].facet_id,),
        )

    dispatcher = build_phase_tools(
        config,
        default_phase_program("native-answer-or-tool-v1"),
        snapshot=snapshot,
        supply_for_phase=supply,
        live_speech_observations=provider,
        tool_contact=tool_contact,
    )
    transport = ScenarioTransport(scenario)
    client, _, _ = _client(
        world,
        tmp_path,
        plan=_plan(),
        transport=transport,
        arm="speech-feature-query-native-tools",
        speech_feature_root=feature_root,
        speech_packet_bindings=packet_bindings,
        tool_schemas=dispatcher.native_tool_schemas(),
    )
    client_box["client"] = client
    registry = _controller_registry(
        "native-live-integration-v1",
        lambda _sample_id: EvidenceAgentController(
            program=default_phase_program("native-answer-or-tool-v1"),
            tools_for_phase=dispatcher,
            material_for_phase=lambda name, context: PhaseMaterial(
                instruction="Answer directly or call one needed internal tool.",
                response_format=None,
                contact_id=f"{context.sample_id}:{name}",
                purpose=name,
            ),
        ),
    )
    trace = TraceBuffer(_plan().run_id)
    summary = run_speech_native_agent_loop(
        data_root=world.data_root,
        plan=_plan(),
        adapter=_FakeAdapter(samples=tuple(world.samples)),
        core_client=client,
        split_id="all",
        knowledge_snapshot=snapshot,
        speech_packet_bindings=packet_bindings,
        controller_policy_id="native-live-integration-v1",
        controller_registry=registry,
        max_contacts=3,
        slot_count=2,
        queue_depth=2,
        trace_sink=trace,
        agent_executor_id="openjiuwen-workflow-v1",
        decoding_params={"max_tokens": 256},
        knowledge_value_renderer=dispatcher.render_values,
    )
    return {
        "world": world,
        "summary": summary,
        "transport": transport,
        "provider": provider,
        "dispatcher": dispatcher,
        "client": client,
        "custody": custody,
        "asr_contacts": asr_contacts,
        "backend_events": backend_events,
    }


def request(system, sample, phase):
    return next(
        payload
        for payload in system["transport"].calls
        if payload["sample_id"] == sample
        and payload["history"][-1]["contact_id"].endswith(":" + phase)
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_immediate_answer_and_live_then_knowledge_reach_real_next_requests(tmp_path):
    system = build_system(tmp_path, "live-then-knowledge")
    assert [len(row.contacts) for row in system["summary"].results] == [1, 3]
    assert [row.final_response_text for row in system["summary"].results] == [
        "final-answer-s1-decision-1",
        "final-answer-s2-final",
    ]
    assert len(system["asr_contacts"]) == 1
    assert system["provider"].receipt()["new_forwards"] == 1
    assert {row["sample_id"] for row in system["custody"]} == {"s2"}

    decision_two = json.dumps(request(system, "s2", "decision-2"))
    final = json.dumps(request(system, "s2", "final"))
    assert "turn on the kitchen lights" in decision_two
    assert "Knowledge value" not in decision_two
    assert "turn on the kitchen lights" in final
    for index in range(5):
        assert f"Knowledge value {index}:" in final
    assert "turn on the kitchen lights" not in json.dumps(request(system, "s1", "decision-1"))
    closed = system["client"].close()
    assert closed["cost"]["tool_calls"] == 2


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_repeated_live_call_has_one_forward_two_invocations_and_no_duplicate_evidence(tmp_path):
    system = build_system(tmp_path, "repeat-live")
    receipt = system["provider"].receipt()
    assert receipt["invocations"] == 2
    assert receipt["cache_hits"] == 1
    assert receipt["new_forwards"] == 1
    assert len(system["asr_contacts"]) == 1
    assert len(system["custody"]) == 2
    for phase in ("decision-2", "final"):
        payload = request(system, "s2", phase)
        supplied = [
            row for row in payload["supplied_evidence"]
            if row["evidence_id"].startswith("live-speech-observation:")
        ]
        assert len(supplied) == 1
        assert supplied[0]["content"].count("turn on the kitchen lights") == 1
    closed = system["client"].close()
    assert closed["cost"]["tool_calls"] == 2


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_malformed_native_call_supplies_error_then_accepts_plain_final(tmp_path):
    system = build_system(tmp_path, "malformed")
    assert [len(row.contacts) for row in system["summary"].results] == [1, 2]
    assert system["summary"].results[1].final_response_text == "final-answer-s2-decision-2"
    assert system["custody"] == []
    assert system["asr_contacts"] == []
    assert system["provider"].receipt()["new_forwards"] == 0
    retry = json.dumps(request(system, "s2", "decision-2"))
    assert "internal tool request was rejected" in retry.lower()
    rejected = system["dispatcher"].receipt()["native_rejected_requests"]
    assert rejected["count"] == 1 and len(rejected["hashes"]) == 1
    system["client"].close()
