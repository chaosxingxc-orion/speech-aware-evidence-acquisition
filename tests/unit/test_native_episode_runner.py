"""Actual native role episodes through the shared runner; no network or model."""

from __future__ import annotations

import hashlib
import json
import struct
import threading
from collections import Counter
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.model import (
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.controllers import (
    PhaseProgram,
    PhaseSpec,
    native_planner_action_response_format,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
    NativeEpisodeRunBinding,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    is_illegal_planner_route,
)
from speech_aware_evidence_acquisition.rails.candidate_experience_memory import (
    LoadedCandidateExperienceMemory,
)
from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability,
    ExperienceRecord,
    ExperienceSource,
    ValidationBinding,
)
from speech_aware_evidence_acquisition.rails.experience_memory_runtime import (
    CORRECTIVE_MEMORY_TOOL,
)
from speech_aware_evidence_acquisition.rails.experience_memory_sources import (
    reward_link_hash_source_ref,
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
    reviewer_tool: str | None = None,
    analytical_tool_role: str = "reviewer",
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
                max_iterations=(2 if reviewer_tool and phase == analytical_tool_role else 1),
                tool_names=(
                    (reviewer_tool,) if reviewer_tool and phase == analytical_tool_role else ()
                ),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
        exhaustion_policy=exhaustion_policy,
    )


def _review_off_config(*, max_contacts: int) -> NativeEpisodeConfig:
    """The M0 shape (E1): Reviewer and Planner both declare max_iterations 0
    and max_revisions is 0, so neither ever gets a NativeRoleNode."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase,
                role_kind=phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _feature_bindings(world: _World, feature_root):
    bindings = {}
    for sample in world.samples:
        packet_key = (
            hashlib.sha256(sample.sample_id.encode()).hexdigest()
            if ":" in sample.sample_id else sample.sample_id
        )
        packet = materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=f"slurp/train/{packet_key}",
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


def _wire_tool_call(tool_id: str = TASK_CONTRACT_TOOL) -> bytes:
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
                                    "name": tool_id,
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
        analytical_tool_role: str = "reviewer",
        reviewer_memory: LoadedCandidateExperienceMemory | None = None,
        exhaustion_policy: str = "raise",
        sample_ids: tuple[str, ...] | None = None,
        execution_plan=None,
        data_root=None,
        query_source: str = "speech_features",
        execution_units_factory=None,
    ):
        self.world = _World(tmp_path, data_root=data_root)
        self.world.samples = self.world.samples[:sample_count]
        if sample_ids is not None:
            from dataclasses import replace
            assert len(sample_ids) == sample_count
            self.world.samples = [
                replace(sample, sample_id=sample_id)
                for sample, sample_id in zip(self.world.samples, sample_ids, strict=True)
            ]
        self.samples = tuple(self.world.samples)
        self.adapter = _FakeAdapter(samples=self.samples)
        self.query_source = query_source
        self.feature_root = tmp_path / "features"
        if execution_units_factory is not None:
            self.feature_root.mkdir(parents=True, exist_ok=True)
        all_bindings = {} if execution_units_factory is not None else (
            _feature_bindings(self.world, self.feature_root)
            if query_source == "speech_features"
            else {
                sample.sample_id: {
                    "packet_id": sample.audio_ref.path,
                    "sha256": sample.audio_ref.sha256,
                }
                for sample in self.samples
            }
        )
        self.speech_bindings = {} if execution_units_factory is not None else {
            sample.sample_id: all_bindings[sample.sample_id] for sample in self.samples
        }
        self.program = _program(max_contacts=max_contacts)
        assert analytical_tool_role in {"reviewer", "planner"}
        self.analytical_tool_role = analytical_tool_role
        self.reviewer_tool = (
            CORRECTIVE_MEMORY_TOOL
            if reviewer_memory is not None
            else TASK_CONTRACT_TOOL if reviewer_task_tool else None
        )
        self.config = _config(
            max_revisions=max_revisions,
            max_contacts=max_contacts,
            reviewer_tool=self.reviewer_tool,
            analytical_tool_role=analytical_tool_role,
            exhaustion_policy=exhaustion_policy,
        )
        self.planner_actions = planner_actions
        # E8a: the repository root a declared node-context policy reads its
        # committed templates from. None -- every episode proof written before
        # E8a -- binds exactly as before.
        self.repo_root = None
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
            response = (
                _wire_tool_call(self.reviewer_tool)
                if output is None
                else _wire_response(output)
            )
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
            feature_root=(
                self.feature_root if query_source == "speech_features" else None
            ),
            preserve_wire_responses=True,
            prompt_order=(
                "speech-query-prefix-v2"
                if query_source == "speech_features"
                else "native-raw-speech-v1"
            ),
        )
        self.plan = execution_plan or _plan(
            run_id="SAEA-E-native-role-runner-proof",
            attempt_id="attempt-native-role-runner-proof",
            planned_model_calls=len(self.samples) * max_contacts,
        )
        self.tools_for_phase = None
        if self.reviewer_tool:

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

            tool_config = {
                "phase_tools": {
                    analytical_tool_role: {
                            "mode": "native-tools",
                            "allowed_tools": [self.reviewer_tool],
                            "knowledge_views": ["text"],
                            "source_authority_role": analytical_tool_role,
                    }
                }
            }
            if reviewer_memory is not None:
                tool_config["candidate_experience_memory"] = {"test": "bound"}
            self.tools_for_phase = build_phase_tools(
                tool_config,
                self.program,
                snapshot=_knowledge_snapshot(),
                experience_memory=reviewer_memory,
                tool_contact=tool_contact,
            )
        client_kwargs = {}
        if self.tools_for_phase is not None:
            client_kwargs["tool_schemas"] = self.tools_for_phase.native_tool_schemas()
        elif arm in {
            "speech-feature-query-native-tools",
            "raw-speech-agent-native-tools",
        }:
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
        if execution_plan is not None:
            from speech_aware_evidence_acquisition.rails import build_payload_binding
            client_kwargs["binding"] = build_payload_binding(
                carrier_lock_key=execution_plan.carrier_lock_key,
                samples=self.samples,
                data_root=self.world.data_root,
                carrier_root=self.world.carrier_root,
            )
        if execution_units_factory is not None:
            self.execution_units, registry = execution_units_factory(self)
            client_kwargs.update(
                speech_feature_root=self.feature_root,
                execution_units=self.execution_units,
                slice_registry=registry,
            )
        elif query_source == "speech_features":
            client_kwargs.update(
                speech_feature_root=self.feature_root,
                speech_packet_bindings=self.speech_bindings,
            )
        self.client, _, _ = _client(
            self.world, tmp_path, plan=self.plan, transport=self.transport,
            arm=arm, **client_kwargs,
        )
        self.trace = TraceBuffer(self.plan.run_id)

    def _material_key(self, body):
        serialized = json.dumps(body, sort_keys=True)
        matches = [key for key, marker in self.markers.items() if marker in serialized]
        assert len(matches) == 1, (matches, serialized)
        return matches[0]

    def _output(self, key):
        sample_id, phase, visit, turn = key
        if self.reviewer_tool and phase == self.analytical_tool_role and visit == turn == 1:
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

    def run(self, *, decoding_params=None, snapshot=None):
        # E13 (2026-09-19): an OPTIONAL override of this fixture's decoding
        # params, so a proof that needs the carrier's real output cap (the
        # 512-token SLURP geometry a finite completion stops at) can say so.
        # Omitted -- every caller written before E13 -- the historical
        # {"temperature": 0, "max_tokens": 64} is used, byte-identically.
        # Same-flight instrument, PHASE 2, "What to build" item 2: an
        # OPTIONAL override of this fixture's default knowledge snapshot, so
        # a proof needing intent-boundary-shaped value ids (for
        # ``top2-contrast-v1``'s own rank-1/rank-2 derivation) can supply its
        # own. Omitted -- every caller written before this item -- the
        # historical ``_knowledge_snapshot()`` is used, byte-identically.
        active_snapshot = _knowledge_snapshot() if snapshot is None else snapshot
        binding = NativeEpisodeRunBinding(
            config=self.config,
            program=self.program,
            material_for_phase=self.material_for_phase,
            render_request=self.transport.render_request,
            request_gate=self.request_gate,
            tools_for_phase=self.tools_for_phase,
            repo_root=self.repo_root,
            # E14: the controlled data root a declared
            # ``native_episode.solver_hints`` block reads its RELEASED
            # scenario-hints view from. None -- every harness written
            # before E14 and every OFF arm -- leaves this binding
            # byte-identical to its pre-E14 self.
            data_root=getattr(self, "solver_hints_data_root", None),
            # E18: the flight-owned knowledge re-query a ``knowledge-requery``
            # acquisition runs. None -- every harness written before E18 and
            # every unarmed episode -- leaves this binding byte-identical to
            # its pre-E18 self.
            acquisition_requery=getattr(self, "acquisition_requery", None),
            # E20: the live serving budget a dispatch-time context-fit check
            # measures each realised request against. None -- every harness
            # written before E20 and every unarmed episode -- leaves this
            # binding byte-identical to its pre-E20 self.
            context_fit_budget=getattr(self, "context_fit_budget", None),
            # Item E42: the flight-owned per-arm supply resolver a declared
            # ``roles.solver.supply_variants`` group needs. None -- every
            # harness written before E42 and every episode that declares no arm
            # group -- leaves this binding byte-identical to its pre-E42 self,
            # and the runner refuses a resolver it did not ask for.
            supply_variant_for_phase=getattr(self, "supply_variant_for_phase", None),
            # Same-flight instrument, PHASE 2 (merge set C): every declared
            # Perception branch's own pre-flight seed. None -- every harness
            # written before phase 2 and every episode that declares no
            # branch group -- leaves this binding byte-identical to its
            # pre-phase-2 self.
            perception_branch_seeds=getattr(self, "perception_branch_seeds", None),
            # Same-flight instrument, PHASE 2, "What to build" item 1: every
            # declared branch's own contrast-pair table. None -- every
            # harness written before this table existed and every episode
            # that declares no ``contrast_pairs`` branch -- leaves this
            # binding byte-identical to its pre-existing self.
            perception_contrast_pairs=getattr(self, "perception_contrast_pairs", None),
            # NX programme E1: one material builder per template arm. None --
            # every harness written before the programme and every episode
            # that declares no template group -- binds byte-identically.
            template_variant_materials=getattr(self, "template_variant_materials", None),
            prefix_slots=getattr(self, "prefix_slots", None),
            node_batch=getattr(self, "node_batch", None),
            node_pipeline=getattr(self, "node_pipeline", None),
        )
        source_kwargs = (
            {}
            if self.query_source == "speech_features"
            else {"query_source": self.query_source}
        )
        return run_speech_native_agent_loop(
            data_root=self.world.data_root,
            plan=self.plan,
            adapter=self.adapter,
            core_client=self.client,
            split_id="all",
            knowledge_snapshot=active_snapshot,
            speech_packet_bindings=self.speech_bindings,
            **source_kwargs,
            controller_policy_id=self.program.program_id,
            controller_registry=_controller_registry(
                self.program.program_id, lambda _sample_id: object()
            ),
            max_contacts=self.config.max_contacts,
            slot_count=getattr(self, "slot_count", len(self.samples)),
            queue_depth=getattr(self, "slot_count", len(self.samples)),
            trace_sink=self.trace,
            agent_executor_id="openjiuwen-workflow-v1",
            decoding_params=decoding_params or {"temperature": 0, "max_tokens": 64},
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
        serialized = json.dumps(body)
        assert serialized.count('"type": "input_speech_features"') == 1
        assert '"type": "input_audio"' not in serialized
        if arm == "speech-feature-query-native-tools":
            assert body["tool_choice"] == "none"
            assert body["parallel_tool_calls"] is False
        else:
            assert "tool_choice" not in body
            assert "parallel_tool_calls" not in body


# ---------------------------------------------------------------------------
# E1: review loop off (M0), through the actual shared runner.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_review_loop_off_runs_exactly_two_contacts_and_skips_by_configuration(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=2,
        planner_actions=(),
    )
    harness.config = _review_off_config(max_contacts=2)
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert [result.final_response_text for result in summary.results] == [
        "solver-answer:s1:visit:1",
    ]
    assert close_summary["request_count"] == 2
    result = summary.results[0]
    assert len(result.contacts) == 2
    receipt = result.native_episode_receipt
    assert set(receipt) == {
        "role_visits",
        "planner_routes",
        "accepted_solver_receipt",
        "review_loop_disposition",
    }
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception",
        "solver",
    ]
    assert receipt["planner_routes"] == []
    assert receipt["review_loop_disposition"] == {
        "schema": "saea-native-review-loop-skip-v1",
        "status": "skipped_by_configuration",
        "reviewer_phase_id": "reviewer",
        "planner_phase_id": "planner",
    }
    final_contact = receipt["accepted_solver_receipt"]["final_contact"]
    assert final_contact == harness.traced_contact(final_contact["agent_contact_id"])
    assert (
        final_contact["response_text_sha256"]
        == harness.dispatched[("s1", "solver", 1, 1)]["response_text_sha256"]
    )
    # Reviewer and Planner were never even queried for a request, let alone
    # contacted -- their material_for_phase visit counters stay at zero.
    assert harness.material_visits[("s1", "reviewer")] == 0
    assert harness.material_visits[("s1", "planner")] == 0


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_review_loop_off_solver_history_matches_the_review_loop_on_shape(tmp_path):
    """Request-identity proof (E1 item 5): the Solver's conversation HISTORY
    -- the original query plus Perception's candidates, with no review
    findings in either shape -- is byte-identical whether the review loop is
    on or off. The one channel the module may move is the trailing per-turn
    instruction, where the injected 'Native episode limits' epilogue
    legitimately differs (max_revisions, available Planner actions): that is
    the module's own channel, not a leak (spec section 6: 'the request
    differs from the base only in the module's channel')."""

    on = _ActualEpisodeHarness(
        tmp_path / "on",
        sample_count=1,
        max_revisions=1,
        max_contacts=7,
        planner_actions=("ACCEPT",),
    )
    off = _ActualEpisodeHarness(
        tmp_path / "off",
        sample_count=1,
        max_revisions=0,
        max_contacts=2,
        planner_actions=(),
    )
    off.config = _review_off_config(max_contacts=2)

    try:
        on_summary = on.run()
        off_summary = off.run()
    finally:
        on.close()
        off.close()

    assert on_summary.results[0].final_response_text == "solver-answer:s1:visit:1"
    assert off_summary.results[0].final_response_text == "solver-answer:s1:visit:1"

    on_body = on.prepared[("s1", "solver", 1, 1)]["rendered"]
    off_body = off.prepared[("s1", "solver", 1, 1)]["rendered"]
    on_messages = on_body["messages"]
    off_messages = off_body["messages"]
    assert len(on_messages) == len(off_messages)

    differing = [
        index for index in range(len(on_messages))
        if on_messages[index] != off_messages[index]
    ]
    assert differing == [len(on_messages) - 1], (
        "the Solver request must differ from the review-loop-on shape in "
        f"nothing but its final instruction message; differing indices: {differing}"
    )
    assert on_messages[:-1] == off_messages[:-1]

    def _text_parts(content):
        # The Solver's per-turn message bundles the speech-feature part with
        # TWO text parts: the exposed Perception "agent state" and the
        # per-turn instruction (marker + the limits epilogue). Only the
        # instruction part may legitimately carry the module's channel.
        assert isinstance(content, list)
        return [part["text"] for part in content if part.get("type") == "text"]

    marker = "native-role:solver:sample:s1:visit:1"
    on_texts = _text_parts(on_messages[-1]["content"])
    off_texts = _text_parts(off_messages[-1]["content"])
    assert len(on_texts) == len(off_texts) == 2

    on_instruction = [text for text in on_texts if text.startswith(marker)]
    off_instruction = [text for text in off_texts if text.startswith(marker)]
    assert len(on_instruction) == len(off_instruction) == 1
    on_content, off_content = on_instruction[0], off_instruction[0]
    assert on_content != off_content

    # The OTHER text part is the exposed Perception agent state -- same role
    # history, no review findings in either shape -- and it must be
    # byte-identical, which is the request-identity claim item 5 asks for.
    on_state = [text for text in on_texts if text != on_content]
    off_state = [text for text in off_texts if text != off_content]
    assert on_state == off_state

    on_limits = json.loads(on_content.split("Native episode limits: ", 1)[1])
    off_limits = json.loads(off_content.split("Native episode limits: ", 1)[1])
    assert on_limits["max_revisions"] == 1
    assert off_limits["max_revisions"] == 0
    assert on_limits["available_planner_actions"] == ["ACCEPT", "REVISE"]
    assert off_limits["available_planner_actions"] == ["ACCEPT"]


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
    ("max_revisions", "planner_actions", "solver_visit"),
    (
        (0, ("ACQUIRE",), 1),
        (1, ("REVISE", "ACQUIRE"), 2),
    ),
)
def test_e15_actual_terminal_acquire_is_a_retained_row_not_a_terminal_delivery(
    tmp_path, max_revisions, planner_actions, solver_visit
):
    """E15 (finding I-1 of the 2026-09-19 base-lock draft).

    No configuration this runner accepts can build an acquisition node --
    ``rails.native_episode_config`` admits exactly the perception, solver,
    reviewer and planner roles -- so ACQUIRE is an action no production
    episode can execute.  Before E15 the same Planner word meant two
    different things depending on WHEN it arrived: at a non-terminal revision
    it raised inside the graph and killed the flight, and at the terminal
    revision it was recorded as a ``revision_limit`` terminal delivery.  After
    E15 it means one thing everywhere: the E8c retained-row disposition.

    These two shapes are the terminal-revision cases this proof's sibling
    above used to carry.  The episode makes exactly the same contacts it made
    before; only its seal changed.
    """

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
    assert close_summary["request_count"] == len(result.contacts) == 4 + 3 * max_revisions
    assert result.final_response_text == f"solver-answer:s1:visit:{solver_visit}"
    assert "terminal_solver_receipt" not in receipt
    assert "terminal_disposition" not in receipt
    accepted = receipt["accepted_solver_receipt"]["final_contact"]
    assert accepted == harness.traced_contact(accepted["agent_contact_id"])
    assert accepted["response_text_sha256"] == harness.dispatched[
        ("s1", "solver", solver_visit, 1)
    ]["response_text_sha256"]
    route = receipt["planner_routes"][-1]
    assert is_illegal_planner_route(route)
    assert route["action"] == "ACQUIRE"
    assert route["revision_count"] == max_revisions
    assert receipt["planner_action_illegal"] == {
        "schema": "saea-native-planner-action-illegal-v1",
        "count": 1,
        "action_sha256": [hashlib.sha256(b"ACQUIRE").hexdigest()],
    }


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    ("max_revisions", "planner_actions", "solver_visit", "terminal_action"),
    (
        (0, ("REVISE",), 1, "REVISE"),
        (1, ("REVISE", "REVISE"), 2, "REVISE"),
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
@pytest.mark.parametrize("local_tool_workers", [0, 1])
def test_actual_reviewer_tool_result_reaches_next_contact_and_revised_solver(
    tmp_path, local_tool_workers,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    from dataclasses import replace
    harness.config = replace(harness.config, local_tool_workers=local_tool_workers)
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


def _provisional_memory_for_native_episode() -> LoadedCandidateExperienceMemory:
    construction_sha = "c" * 64
    validation = ValidationBinding(
        status="provisional",
        decision_sha256="d" * 64,
        protocol_sha256="e" * 64,
        roster_sha256=construction_sha,
        result_sha256="f" * 64,
    )
    applicability = Applicability(
        task_ids=("slurp",),
        phases=("reviewer",),
        component_tags=("org",),
        required_conditions=("state:prior-response-present",),
        excluded_conditions=(),
    )
    records = tuple(
        ExperienceRecord.create(
            record_id=f"candidate-{index}",
            revision=1,
            kind="corrective-experience",
            train_construction_sha256=construction_sha,
            source=ExperienceSource(
                "train",
                f"slurp:train:construction-{index}",
                str(index) * 64,
                chr(96 + index) * 64,
                chr(98 + index) * 64,
                chr(100 + index) * 64,
            ),
            applicability=applicability,
            diagnosis=f"Diagnosis {index}.",
            guidance=f"Guidance {index}.",
            limitations=("Evaluate this provisionally.",),
            supporting_source_refs=(
                reward_link_hash_source_ref(str(5 + index) * 64),
            ),
            validation=validation,
        )
        for index in (1, 2)
    )
    return LoadedCandidateExperienceMemory(
        records=(records[1], records[0]),
        artifact_sha256="1" * 64,
        artifact_output_sha256="2" * 64,
        source_attestation_sha256="3" * 64,
        evaluation_decision_sha256="4" * 64,
        construction_roster_sha256=construction_sha,
        evaluation_roster_sha256="5" * 64,
        task_id="slurp",
        component_tags=("org",),
        allowed_roles=("reviewer",),
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_provisional_memory_visible_guidance_reaches_fitted_native_history(tmp_path):
    memory = _provisional_memory_for_native_episode()
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_memory=memory,
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert close_summary["cost"]["tool_calls"] == 1
    schemas = harness.tools_for_phase.native_tool_schemas()
    assert schemas[0]["function"]["description"] == (
        "Read provisional guidance for this registered TRAIN evaluation."
    )
    for key in (
        ("s1", "reviewer", 1, 2),
        ("s1", "solver", 2, 1),
    ):
        body = harness.prepared[key]["rendered"]
        messages = [message for message in body["messages"] if message["role"] == "tool"]
        assert len(messages) == 1
        document = json.loads(messages[0]["content"])
        selection = document["result"]
        assert selection["status"] == "provisional"
        assert [row["record_sha256"] for row in selection["selected_records"]] == [
            record.record_sha256 for record in memory.records
        ]
        assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
    receipt = harness.tools_for_phase.receipt()
    assert receipt["memory_lineage"][0]["candidate_artifact_sha256"] == "1" * 64
    assert receipt["memory_lineage"][0]["ordered_pack_record_sha256s"] == [
        record.record_sha256 for record in memory.records
    ]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_refresh_request_is_fitted_and_bound_before_second_solver(tmp_path):
    from dataclasses import replace

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=8,
        planner_actions=("REFRESH_CANDIDATES", "ACCEPT"),
    )
    harness.config = replace(
        harness.config, refresh_action="REFRESH_CANDIDATES", max_candidate_refreshes=1,
    )
    try:
        result = harness.run().results[0]
        assert len(harness.prepared) == len(harness.dispatched) == 8
        for key in harness.prepared:
            assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
        keys = list(harness.prepared)
        assert [key[1] for key in keys] == [
            "perception", "solver", "reviewer", "planner",
            "perception", "solver", "reviewer", "planner",
        ]
        def limits(rendered):
            def strings(value):
                if isinstance(value, str):
                    yield value
                elif isinstance(value, dict):
                    for item in value.values():
                        yield from strings(item)
                elif isinstance(value, list):
                    for item in value:
                        yield from strings(item)
            matches = []
            for text in strings(rendered):
                for line in text.splitlines():
                    if line.startswith("Native episode limits: "):
                        matches.append(json.loads(line.removeprefix("Native episode limits: ")))
            assert len(matches) == 1
            return matches[0]

        initial_limits = limits(harness.prepared[keys[3]]["rendered"])
        final_limits = limits(harness.prepared[keys[-1]]["rendered"])
        assert initial_limits["available_planner_actions"] == [
            "ACCEPT", "REVISE", "REFRESH_CANDIDATES",
        ]
        assert initial_limits["remaining_candidate_refreshes"] == 1
        assert final_limits["available_planner_actions"] == ["ACCEPT"]
        assert final_limits["remaining_candidate_refreshes"] == 0
        visits = result.native_episode_receipt["role_visits"]
        perceptions = [v for v in visits if v["stage"] == "perception"]
        assert len(perceptions) == 2
        assert perceptions[0]["execution_receipt"] != perceptions[1]["execution_receipt"]
        assert result.final_response_text.endswith(":visit:2")
        from copy import deepcopy
        from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
            validate_native_candidate_refresh_receipt,
        )

        def verify(receipt):
            return validate_native_candidate_refresh_receipt(
                receipt, refresh_action="REFRESH_CANDIDATES",
                max_refreshes=1, max_revisions=1, accept_action="ACCEPT", revise_action="REVISE",
            )
        assert verify(result.native_episode_receipt) == 1
        corrupted = deepcopy(result.native_episode_receipt)
        corrupted["planner_routes"][0]["action"] = "REVISE"
        with pytest.raises(ValueError, match="ordered role/route"):
            verify(corrupted)
        corrupted = deepcopy(result.native_episode_receipt)
        corrupted["role_visits"][4]["stage"] = "solver"
        with pytest.raises(ValueError, match="following Perception"):
            verify(corrupted)
        corrupted = deepcopy(result.native_episode_receipt)
        corrupted["planner_routes"][1]["revision_count"] = 0
        with pytest.raises(ValueError, match="ordered role/route"):
            verify(corrupted)
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_json_planner_schema_tracks_graph_at_revision_exhaustion(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=7,
        planner_actions=('{"action":"REVISE"}', '{"action":"REVISE"}'),
        exhaustion_policy="deliver-latest-solver",
    )
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(
                phase,
                response_format_id=(
                    "saea-native-planner-action-v1"
                    if phase.name == "planner"
                    else None
                ),
            )
            for phase in harness.program.phases
        ),
    ).validate()
    harness.config = replace(
        harness.config,
        planner_output_format="json-action-v1",
    )
    legacy_material = harness.material_for_phase
    configured_format = native_planner_action_response_format(ACTIONS[:2])

    def material_for_phase(phase, context, sealed):
        material = legacy_material(phase, context, sealed)
        if phase == "planner":
            return replace(material, response_format=configured_format).validate()
        return material

    harness.material_for_phase = material_for_phase
    try:
        result = harness.run().results[0]
        planner_bodies = [
            prepared["rendered"]
            for key, prepared in harness.prepared.items()
            if key[1] == "planner"
        ]
        assert len(harness.dispatched) == 7
        assert result.final_response_text.endswith(":visit:2")
        assert result.native_episode_receipt["terminal_disposition"][
            "planner_action"
        ] == "REVISE"
        assert result.native_episode_receipt["plan"] == '{"action":"REVISE"}'
        assert result.native_episode_receipt["planner_control"] == {"action": "REVISE"}
        from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
            validate_native_episode_delivery_receipt,
        )
        validate_native_episode_delivery_receipt(result.native_episode_receipt)
        corrupted = dict(result.native_episode_receipt, planner_control={"action": "ACCEPT"})
        with pytest.raises(ValueError, match="structured Planner control differs"):
            validate_native_episode_delivery_receipt(corrupted)
        assert [
            body["response_format"]["json_schema"]["schema"]["properties"][
                "action"
            ]["enum"]
            for body in planner_bodies
        ] == [
            ["ACCEPT", "REVISE"],
            ["ACCEPT", "REVISE"],
        ]
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_refreshed_native_trajectory_projects_verified_c0_and_c1(tmp_path):
    from copy import deepcopy
    from dataclasses import replace
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis.native_candidate_stage_projections import (
        NativeCandidateStageProjectionError,
        project_verified_native_candidate_stages,
    )

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=8,
        planner_actions=("REFRESH_CANDIDATES", "ACCEPT"),
    )
    harness.config = replace(
        harness.config,
        refresh_action="REFRESH_CANDIDATES",
        max_candidate_refreshes=1,
    )
    original_output = harness._output

    def candidate_output(key):
        sample_id, phase, visit, _turn = key
        if phase != "perception":
            return original_output(key)
        intent_id = "alpha" if visit == 1 else "beta"
        return json.dumps(
            {
                "candidates": [
                    {
                        "intent_id": intent_id,
                        "distinction": f"Evidence for {intent_id}.",
                        "evidence_refs": ["speech"],
                        "unresolved_fields": [],
                    }
                ]
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    harness._output = candidate_output
    try:
        result = harness.run().results[0]
        trace_records = {
            record_id: payload
            for _channel, record_id, payload in harness.trace.records
        }
        source = SimpleNamespace(
            sample_ids=(result.sample_id,),
            phase_results={result.sample_id: result.as_json()},
            bundle=SimpleNamespace(trace_records=trace_records),
        )
        pairs = project_verified_native_candidate_stages(
            source,
            legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
            max_candidates=3,
        )
        assert len(pairs) == 1
        assert pairs[0].c0.candidate_ids == ("alpha",)
        assert pairs[0].c1.candidate_ids == ("beta",)
        assert pairs[0].c0.visit_index == 0
        assert pairs[0].c1.visit_index == 4
        assert pairs[0].refresh_executed is True

        missing = deepcopy(result.as_json())
        missing["agent_states"] = [
            state
            for state in missing["agent_states"]
            if state["state_id"] != pairs[0].c1.state_id
        ]
        with pytest.raises(NativeCandidateStageProjectionError, match="sealed phase state"):
            project_verified_native_candidate_stages(
                SimpleNamespace(
                    sample_ids=source.sample_ids,
                    phase_results={result.sample_id: missing},
                    bundle=source.bundle,
                ),
                legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
                max_candidates=3,
            )

        corrupted = deepcopy(result.as_json())
        next(
            state
            for state in corrupted["agent_states"]
            if state["state_id"] == pairs[0].c1.state_id
        )["source_query_state_sha256"] = "0" * 64
        with pytest.raises(NativeCandidateStageProjectionError, match="state binding"):
            project_verified_native_candidate_stages(
                SimpleNamespace(
                    sample_ids=source.sample_ids,
                    phase_results={result.sample_id: corrupted},
                    bundle=source.bundle,
                ),
                legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
                max_candidates=3,
            )

        wrong_request = deepcopy(result.as_json())
        wrong_request["native_episode_receipt"]["role_visits"][4][
            "execution_receipt"
        ]["contacts"][0]["request_sha256"] = "0" * 64
        wrong_request["native_episode_receipt"]["role_visits"][4][
            "execution_receipt"
        ]["final_contact"]["request_sha256"] = "0" * 64
        with pytest.raises(NativeCandidateStageProjectionError, match="verified trace"):
            project_verified_native_candidate_stages(
                SimpleNamespace(
                    sample_ids=source.sample_ids,
                    phase_results={result.sample_id: wrong_request},
                    bundle=source.bundle,
                ),
                legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
                max_candidates=3,
            )

        reordered = deepcopy(result.as_json())
        reordered["native_episode_receipt"]["role_visits"][0:2] = reversed(
            reordered["native_episode_receipt"]["role_visits"][0:2]
        )
        with pytest.raises(NativeCandidateStageProjectionError):
            project_verified_native_candidate_stages(
                SimpleNamespace(
                    sample_ids=source.sample_ids,
                    phase_results={result.sample_id: reordered},
                    bundle=source.bundle,
                ),
                legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
                max_candidates=3,
            )
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_zero_refresh_native_trajectory_reuses_c0_as_c1(tmp_path):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis.native_candidate_stage_projections import (
        project_verified_native_candidate_stages,
    )

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    original_output = harness._output

    def candidate_output(key):
        _sample_id, phase, _visit, _turn = key
        if phase != "perception":
            return original_output(key)
        return json.dumps(
            {
                "candidates": [
                    {
                        "intent_id": "alpha",
                        "distinction": "Evidence for alpha.",
                        "evidence_refs": ["speech"],
                        "unresolved_fields": [],
                    }
                ]
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    harness._output = candidate_output
    try:
        result = harness.run().results[0]
        source = SimpleNamespace(
            sample_ids=(result.sample_id,),
            phase_results={result.sample_id: result.as_json()},
            bundle=SimpleNamespace(
                trace_records={
                    record_id: payload
                    for _channel, record_id, payload in harness.trace.records
                }
            ),
        )
        pair = project_verified_native_candidate_stages(
            source,
            legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
            max_candidates=3,
        )[0]
        assert pair.c0 == pair.c1
        assert pair.c0.visit_index == 0
        assert pair.refresh_executed is False
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_refresh_at_ceiling_delivers_without_a_third_perception(tmp_path):
    from dataclasses import replace
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.analysis.native_candidate_stage_projections import (
        project_verified_native_candidate_stages,
    )

    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=8,
        planner_actions=("REFRESH_CANDIDATES", "REFRESH_CANDIDATES"),
        exhaustion_policy="deliver-latest-solver",
    )
    harness.config = replace(
        harness.config,
        refresh_action="REFRESH_CANDIDATES",
        max_candidate_refreshes=1,
    )
    original_output = harness._output

    def candidate_output(key):
        _sample_id, phase, visit, _turn = key
        if phase != "perception":
            return original_output(key)
        intent_id = "alpha" if visit == 1 else "beta"
        return json.dumps(
            {
                "candidates": [
                    {
                        "intent_id": intent_id,
                        "distinction": f"Evidence for {intent_id}.",
                        "evidence_refs": ["speech"],
                        "unresolved_fields": [],
                    }
                ]
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    harness._output = candidate_output
    try:
        result = harness.run().results[0]
        visits = result.native_episode_receipt["role_visits"]
        assert [index for index, visit in enumerate(visits) if visit["stage"] == "perception"] == [0, 4]
        assert "accepted_solver_receipt" not in result.native_episode_receipt
        assert result.native_episode_receipt["terminal_disposition"] == {
            "reason": "revision_limit",
            "planner_action": "REFRESH_CANDIDATES",
            "revision_count": 1,
            "planner_accepted": False,
        }
        source = SimpleNamespace(
            sample_ids=(result.sample_id,),
            phase_results={result.sample_id: result.as_json()},
            bundle=SimpleNamespace(
                trace_records={
                    record_id: payload
                    for _channel, record_id, payload in harness.trace.records
                }
            ),
        )
        pair = project_verified_native_candidate_stages(
            source,
            legal_candidate_ids=frozenset({"alpha", "beta", "gamma"}),
            max_candidates=3,
        )[0]
        assert pair.c0.candidate_ids == ("alpha",)
        assert pair.c1.candidate_ids == ("beta",)
        assert pair.c1.visit_index == 4
        assert pair.refresh_executed is True
    finally:
        harness.close()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_reserved_final_reviewer_turn_has_no_tools_in_actual_fitted_request(tmp_path, monkeypatch):
    from dataclasses import replace
    import sys

    original_wire = _wire_tool_call
    serial = 0

    def unique_tool_call(tool_id):
        nonlocal serial
        serial += 1
        document = json.loads(original_wire(tool_id))
        document["choices"][0]["message"]["tool_calls"][0]["id"] = f"report-tool-{serial}"
        return json.dumps(document, separators=(",", ":")).encode()

    monkeypatch.setattr(sys.modules[__name__], "_wire_tool_call", unique_tool_call)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
    )
    harness.config = replace(
        harness.config, reserve_final_report=True, local_tool_workers=1,
        roles=tuple(
            replace(role, max_iterations=3) if role.role_kind == "reviewer" else role
            for role in harness.config.roles
        ),
    )
    original_output = harness._output

    def output(key):
        if key[1] == "reviewer":
            return None if key[3] < 3 else "review report with source-bound evidence"
        return original_output(key)
    harness._output = output
    try:
        result = harness.run().results[0]
    finally:
        closed = harness.close()

    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert closed["request_count"] == 11
    assert closed["cost"]["tool_calls"] == 4
    assert len(harness.tool_contacts) == 4
    for visit in (1, 2):
        for turn in (1, 2, 3):
            key = ("s1", "reviewer", visit, turn)
            request = harness.prepared[key]["rendered"]
            assert request["tool_choice"] == ("none" if turn == 3 else "auto")
            assert bool(request.get("tools")) == (turn < 3)
            assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
        final = harness.prepared[("s1", "reviewer", visit, 3)]["rendered"]
        assert sum(message["role"] == "tool" for message in final["messages"]) == 2 * visit
