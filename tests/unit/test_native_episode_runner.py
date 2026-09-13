"""Actual native role episodes through the shared runner; no network or model."""

from __future__ import annotations

import hashlib
import json
import struct
import threading
from collections import Counter

import pytest

from speech_aware_evidence_acquisition.core.model import (
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
    NativeEpisodeRunBinding,
)
from speech_aware_evidence_acquisition.rails.phase_tools import (
    TASK_CONTRACT_TOOL,
    build_phase_tools,
)
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeError,
)

from test_llama_server_transport import (  # noqa: F401
    _MODEL_FILES,
    _base_url,
    _fake_inference_session,
    _spawn_live_matching_process,
    _transport,
)
from test_rails_frozen_core_client import _World, _client, _plan
from test_rails_runner import _FakeAdapter, _controller_registry, _knowledge_snapshot


PHASES = ("perception", "solver", "reviewer", "planner")
ACTIONS = ("ACCEPT", "REVISE", "ACQUIRE")


def _program(*, max_contacts: int) -> PhaseProgram:
    return PhaseProgram(
        program_id="native-role-runner-proof-v1",
        phases=tuple(
            PhaseSpec(
                name=phase,
                purpose=f"Run the {phase} role.",
                knowledge="none",
                response_format_id=None,
                barrier=False,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
        stop_rule="native-role-episode",
    ).validate()


def _config(
    *,
    max_revisions: int,
    max_contacts: int,
    reviewer_task_tool: bool = False,
    exhaustion_policy: str = "raise",
) -> NativeEpisodeConfig:
    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=max_revisions,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase,
                role_kind=phase,
                max_iterations=(2 if reviewer_task_tool and phase == "reviewer" else 1),
                tool_names=(
                    (TASK_CONTRACT_TOOL,)
                    if reviewer_task_tool and phase == "reviewer"
                    else ()
                ),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
        exhaustion_policy=exhaustion_policy,
    )


def _feature_bindings(world: _World, feature_root):
    bindings = {}
    for sample in world.samples:
        packet = materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=f"slurp/train/{sample.sample_id}",
            audio_sha256=sample.audio_ref.sha256,
            encoder_receipt_sha256="e" * 64,
            decoder_gguf_sha256=_MODEL_FILES[0].sha256,
            mmproj_sha256=_MODEL_FILES[1].sha256,
            position_mode="mrope_1d",
            causal_attention=True,
            chunks=(
                SpeechFeatureChunkData(
                    n_tokens=2,
                    n_pos=2,
                    n_embd=4,
                    feature_bytes=struct.pack("<8f", *range(8)),
                    position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
                ),
            ),
        )
        bindings[sample.sample_id] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }
    return bindings


def _wire_response(text: str) -> bytes:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        },
        separators=(",", ":"),
    ).encode()


def _wire_tool_call() -> bytes:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I will inspect the registered task contract.",
                        "tool_calls": [
                            {
                                "id": "call-task-contract-1",
                                "type": "function",
                                "function": {
                                    "name": TASK_CONTRACT_TOOL,
                                    "arguments": "{}",
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        },
        separators=(",", ":"),
    ).encode()


class _ActualEpisodeHarness:
    def __init__(
        self,
        tmp_path,
        *,
        sample_count: int,
        max_revisions: int,
        max_contacts: int,
        planner_actions: tuple[str, ...],
        overlap: bool = False,
        arm: str = "speech-feature-query-native-tools",
        reviewer_task_tool: bool = False,
        exhaustion_policy: str = "raise",
    ):
        self.world = _World(tmp_path)
        self.world.samples = self.world.samples[:sample_count]
        self.samples = tuple(self.world.samples)
        self.adapter = _FakeAdapter(samples=self.samples)
        self.feature_root = tmp_path / "features"
        all_bindings = _feature_bindings(self.world, self.feature_root)
        self.speech_bindings = {
            sample.sample_id: all_bindings[sample.sample_id] for sample in self.samples
        }
        self.program = _program(max_contacts=max_contacts)
        self.config = _config(
            max_revisions=max_revisions,
            max_contacts=max_contacts,
            reviewer_task_tool=reviewer_task_tool,
            exhaustion_policy=exhaustion_policy,
        )
        self.reviewer_task_tool = reviewer_task_tool
        self.planner_actions = planner_actions
        self.material_visits = Counter()
        self.markers = {}
        self.prepared = {}
        self.dispatched = {}
        self.events = []
        self.tool_contacts = []
        self.lock = threading.Lock()
        self.first_contacts = (
            threading.Barrier(sample_count) if overlap and sample_count > 1 else None
        )

        def post(_url, body_bytes):
            body = json.loads(body_bytes)
            with self.lock:
                matches = [
                    key
                    for key, prepared in self.prepared.items()
                    if prepared["rendered"] == body and key not in self.dispatched
                ]
                assert len(matches) == 1
                key = matches[0]
                self.events.append(("dispatch", key))
            if self.first_contacts is not None and key[1] == "perception":
                self.first_contacts.wait(timeout=2.0)
            output = self._output(key)
            response = _wire_tool_call() if output is None else _wire_response(output)
            with self.lock:
                self.dispatched[key] = (
                    {}
                    if output is None
                    else {
                        "response_text_sha256": hashlib.sha256(
                            output.encode()
                        ).hexdigest(),
                    }
                )
            return response

        self.transport = _transport(
            _base_url(),
            self.world.data_root,
            post=post,
            session=_fake_inference_session(),
            feature_root=self.feature_root,
            preserve_wire_responses=True,
            prompt_order="speech-query-prefix-v2",
        )
        self.plan = _plan(
            run_id="SAEA-E-native-role-runner-proof",
            attempt_id="attempt-native-role-runner-proof",
            planned_model_calls=len(self.samples) * max_contacts,
        )
        self.tools_for_phase = None
        if reviewer_task_tool:

            def tool_contact(**facts):
                self.tool_contacts.append(facts)
                self.client.record_tool_call(count=1)
                arguments = facts["arguments"]
                authority = facts["source_authority"]
                packet = self.speech_bindings[facts["sample_id"]]
                return {
                    "schema": "saea-native-phase-tool-contact-v2",
                    "sample_id": facts["sample_id"],
                    **{
                        key: facts[key]
                        for key in (
                            "phase",
                            "next_phase",
                            "tool_id",
                            "source_response_sha256",
                            "request_id",
                            "tool_call_id",
                            "tool_calls_sha256",
                        )
                    },
                    "arguments_sha256": hashlib.sha256(
                        json.dumps(
                            arguments, sort_keys=True, separators=(",", ":")
                        ).encode()
                    ).hexdigest(),
                    "speech_packet_id": packet["packet_id"],
                    "speech_packet_sha256": packet["sha256"],
                    "source_authority_role": facts["source_authority_role"],
                    "source_authority_sha256": content_hash(authority),
                    "source_request_sha256": authority["source_request_sha256"],
                    "source_completion_sha256": authority["completion_sha256"],
                }

            self.tools_for_phase = build_phase_tools(
                {
                    "phase_tools": {
                        "reviewer": {
                            "mode": "native-tools",
                            "allowed_tools": [TASK_CONTRACT_TOOL],
                            "knowledge_views": ["text"],
                            "source_authority_role": "reviewer",
                        }
                    }
                },
                self.program,
                snapshot=_knowledge_snapshot(),
                tool_contact=tool_contact,
            )
        client_kwargs = {}
        if self.tools_for_phase is not None:
            client_kwargs["tool_schemas"] = self.tools_for_phase.native_tool_schemas()
        elif arm == "speech-feature-query-native-tools":
            client_kwargs["tool_schemas"] = (
                {
                    "type": "function",
                    "function": {
                        "name": "unselected_probe_tool",
                        "description": "A registered tool that no role may select.",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
            )
        self.client, _, _ = _client(
            self.world,
            tmp_path,
            plan=self.plan,
            transport=self.transport,
            arm=arm,
            speech_feature_root=self.feature_root,
            speech_packet_bindings=self.speech_bindings,
            **client_kwargs,
        )
        self.trace = TraceBuffer(self.plan.run_id)

    def _material_key(self, body):
        serialized = json.dumps(body, sort_keys=True)
        matches = [key for key, marker in self.markers.items() if marker in serialized]
        assert len(matches) == 1, (matches, serialized)
        return matches[0]

    def _output(self, key):
        sample_id, phase, visit, turn = key
        if self.reviewer_task_tool and phase == "reviewer" and visit == turn == 1:
            return None
        if phase == "planner":
            return self.planner_actions[visit - 1]
        if phase == "solver":
            return f"solver-answer:{sample_id}:visit:{visit}"
        return f"{phase}-analysis:{sample_id}:visit:{visit}"

    def material_for_phase(self, phase, context, _sealed):
        key = (context.sample_id, phase)
        self.material_visits[key] += 1
        visit = self.material_visits[key]
        contact_key = (context.sample_id, phase, visit)
        marker = f"native-role:{phase}:sample:{context.sample_id}:visit:{visit}"
        self.markers[contact_key] = marker
        return PhaseMaterial(
            instruction=marker,
            response_format=None,
            contact_id=marker,
            purpose=phase,
        )

    def request_gate(self, prepared_request):
        payload = prepared_request.as_payload()
        rendered = self.transport.render_request(prepared_request.payload_bytes)
        material_key = self._material_key(rendered)
        with self.lock:
            turn = 1 + sum(key[:3] == material_key for key in self.prepared)
            key = (*material_key, turn)
            assert key not in self.prepared
            self.prepared[key] = {
                "rendered": rendered,
                "slot_id": payload["decoding_params"]["id_slot"],
            }
            self.events.append(("fit", key))

    def run(self):
        binding = NativeEpisodeRunBinding(
            config=self.config,
            program=self.program,
            material_for_phase=self.material_for_phase,
            render_request=self.transport.render_request,
            request_gate=self.request_gate,
            tools_for_phase=self.tools_for_phase,
        )
        return run_speech_native_agent_loop(
            data_root=self.world.data_root,
            plan=self.plan,
            adapter=self.adapter,
            core_client=self.client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=self.speech_bindings,
            controller_policy_id=self.program.program_id,
            controller_registry=_controller_registry(
                self.program.program_id, lambda _sample_id: object()
            ),
            max_contacts=self.config.max_contacts,
            slot_count=len(self.samples),
            queue_depth=len(self.samples),
            trace_sink=self.trace,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params={"temperature": 0, "max_tokens": 64},
            native_episode_binding=binding,
        )

    def traced_contact(self, agent_contact_id):
        matches = [
            (record_id, payload)
            for channel, record_id, payload in self.trace.records
            if channel == "USE"
            and payload.get("use_agent_contact_id") == agent_contact_id
        ]
        assert len(matches) == 1
        record_id, payload = matches[0]
        return {
            "agent_contact_id": payload["use_agent_contact_id"],
            "request_id": record_id.removesuffix("/native-role-contact"),
            "request_sha256": payload["use_request_sha256"],
            "response_sha256": payload["use_response_sha256"],
            "response_text_sha256": payload["use_response_text_sha256"],
        }

    def close(self):
        return self.client.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    "arm",
    ("speech-feature-query", "speech-feature-query-native-tools"),
)
def test_actual_native_episode_accepts_only_solver_and_preserves_shared_fit_and_slots(
    tmp_path,
    arm,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
        overlap=True,
        arm=arm,
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert [result.final_response_text for result in summary.results] == [
        "solver-answer:s1:visit:1",
        "solver-answer:s2:visit:1",
    ]
    assert close_summary["request_count"] == 8
    assert all(len(result.contacts) == 4 for result in summary.results)
    for result in summary.results:
        sample_id = result.sample_id
        receipt = result.native_episode_receipt
        assert set(receipt) == {
            "role_visits",
            "planner_routes",
            "accepted_solver_receipt",
        }
        assert [visit["stage"] for visit in receipt["role_visits"]] == [
            "perception",
            "solver",
            "review",
            "planner",
        ]
        assert receipt["planner_routes"] == [
            {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"}
        ]
        final_contact = receipt["accepted_solver_receipt"]["final_contact"]
        assert final_contact == harness.traced_contact(
            final_contact["agent_contact_id"]
        )
        assert (
            final_contact["response_text_sha256"]
            == harness.dispatched[(sample_id, "solver", 1, 1)]["response_text_sha256"]
        )
        slots = [
            harness.prepared[(sample_id, phase, 1, 1)]["slot_id"] for phase in PHASES
        ]
        assert len(set(slots)) == 1
    assert {
        harness.prepared[(sample_id, "perception", 1, 1)]["slot_id"]
        for sample_id in ("s1", "s2")
    } == {0, 1}
    for key in harness.prepared:
        assert harness.events.index(("fit", key)) < harness.events.index(
            ("dispatch", key)
        )
        body = harness.prepared[key]["rendered"]
        if arm == "speech-feature-query-native-tools":
            assert body["tool_choice"] == "none"
            assert body["parallel_tool_calls"] is False
        else:
            assert "tool_choice" not in body
            assert "parallel_tool_calls" not in body


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_native_episode_revise_route_revisits_solver_reviewer_and_planner(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=7,
        planner_actions=("REVISE", "ACCEPT"),
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    receipt = result.native_episode_receipt
    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert close_summary["request_count"] == len(result.contacts) == 7
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
        "solver",
        "review",
        "planner",
    ]
    assert [route["action"] for route in receipt["planner_routes"]] == [
        "REVISE",
        "ACCEPT",
    ]
    final_contact = receipt["accepted_solver_receipt"]["final_contact"]
    assert final_contact == harness.traced_contact(final_contact["agent_contact_id"])
    assert (
        final_contact["response_text_sha256"]
        == harness.dispatched[("s1", "solver", 2, 1)]["response_text_sha256"]
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_native_episode_contact_cap_refusal_preserves_completed_contacts(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=4,
        planner_actions=("REVISE", "ACCEPT"),
    )
    try:
        with pytest.raises(NativeEpisodeError, match="registered contact ceiling"):
            harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 4
    assert list(harness.prepared) == [
        ("s1", "perception", 1, 1),
        ("s1", "solver", 1, 1),
        ("s1", "reviewer", 1, 1),
        ("s1", "planner", 1, 1),
    ]
    assert list(harness.dispatched) == list(harness.prepared)
    model_responses = [
        record
        for channel, record, _payload in harness.trace.records
        if channel == "MODEL_RESPONSE"
    ]
    assert len(model_responses) == 4


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    ("max_revisions", "planner_actions", "solver_visit", "terminal_action"),
    (
        (0, ("REVISE",), 1, "REVISE"),
        (0, ("ACQUIRE",), 1, "ACQUIRE"),
        (1, ("REVISE", "REVISE"), 2, "REVISE"),
        (1, ("REVISE", "ACQUIRE"), 2, "ACQUIRE"),
    ),
)
def test_actual_opt_in_terminal_delivery_preserves_last_solver_trace(
    tmp_path,
    max_revisions,
    planner_actions,
    solver_visit,
    terminal_action,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=max_revisions,
        max_contacts=4 + 3 * max_revisions,
        planner_actions=planner_actions,
        exhaustion_policy="deliver-latest-solver",
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    receipt = result.native_episode_receipt
    terminal = receipt["terminal_solver_receipt"]["final_contact"]
    assert close_summary["request_count"] == len(result.contacts) == 4 + 3 * max_revisions
    assert result.final_response_text == f"solver-answer:s1:visit:{solver_visit}"
    assert "accepted_solver_receipt" not in receipt
    assert terminal == harness.traced_contact(terminal["agent_contact_id"])
    assert terminal["response_text_sha256"] == harness.dispatched[
        ("s1", "solver", solver_visit, 1)
    ]["response_text_sha256"]
    assert receipt["terminal_disposition"] == {
        "reason": "revision_limit",
        "planner_action": terminal_action,
        "revision_count": max_revisions,
        "planner_accepted": False,
    }
    terminal_traces = [
        payload
        for channel, _record_id, payload in harness.trace.records
        if channel == "USE" and payload.get("use_native_episode") == receipt
    ]
    assert len(terminal_traces) == 1


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_reviewer_tool_result_reaches_next_contact_and_revised_solver(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert close_summary["request_count"] == len(result.contacts) == 8
    assert close_summary["cost"]["tool_calls"] == 1
    assert len(harness.tool_contacts) == 1
    assert harness.tool_contacts[0]["phase"] == "reviewer"
    assert harness.tool_contacts[0]["tool_id"] == TASK_CONTRACT_TOOL
    assert harness.tools_for_phase.receipt()["attempts"] == 1
    assert harness.tools_for_phase.receipt()["completed"] == 1

    reviewer_visits = [
        visit
        for visit in result.native_episode_receipt["role_visits"]
        if visit["role_id"] == "reviewer"
    ]
    assert [
        len(visit["execution_receipt"]["contacts"]) for visit in reviewer_visits
    ] == [
        2,
        1,
    ]
    assert [
        route["action"] for route in result.native_episode_receipt["planner_routes"]
    ] == ["REVISE", "ACCEPT"]

    reviewer_next = harness.prepared[("s1", "reviewer", 1, 2)]["rendered"]
    revised_solver = harness.prepared[("s1", "solver", 2, 1)]["rendered"]
    for body in (reviewer_next, revised_solver):
        tool_messages = [
            message for message in body["messages"] if message["role"] == "tool"
        ]
        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "call-task-contract-1"
        document = json.loads(tool_messages[0]["content"])
        assert document["result"] == {"task_contract": "task-contract-for-s1"}
    assert harness.events.index(
        ("fit", ("s1", "reviewer", 1, 2))
    ) < harness.events.index(("dispatch", ("s1", "reviewer", 1, 2)))
