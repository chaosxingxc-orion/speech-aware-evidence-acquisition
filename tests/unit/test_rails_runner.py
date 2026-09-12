"""The rails runner skeleton (B0): ExecutionPlan/assert_execution_scope
enforcement, the advisory flight lock, and zero-supply/supplied arm
execution through a mock CoreClient -- exercised here against a tiny
in-memory fake TaskAdapter; the Audio2Tool-specific end-to-end integration
lives in test_rails_audio2tool_adapter.py (the mission's own required
"runner executes end-to-end with the mock core client on the Audio2Tool
adapter" test).
"""

from __future__ import annotations

import json
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import (
    ExecutionPlan,
    ExecutionScopeError,
)
from speech_aware_evidence_acquisition.core.base import Registry
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.flight_lock import FLIGHT_LOCK_RELPATH
from speech_aware_evidence_acquisition.core.tracing import DispatchingSink, TraceBuffer
from speech_aware_evidence_acquisition.rails import (
    AgentContactPlan,
    AgentContactBatch,
    ContactDAGAdvance,
    AgentLoopAdvance,
    AgentStateArtifact,
    AgentStepTransition,
    AudioRef,
    KeyFacet,
    KnowledgeSnapshot,
    MockCoreClient,
    ObsPacket,
    QueryState,
    RankedFacet,
    RankResult,
    FusionDecision,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    TaskAdapter,
    ValueBundle,
    agent_response_sha256,
    build_consumption_trace,
    run_rails_experiment,
    run_speech_native_agent_loop,
    run_bounded_contact_dag,
)
from speech_aware_evidence_acquisition.rails import runner as rails_runner_module
from speech_aware_evidence_acquisition.rails.runner import RAILS_ARMS, RailsRunnerError
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

_SHA_A = "a" * 64
_SHA_B = "b" * 64
_SHA_C = "c" * 64


def _plan(**overrides) -> ExecutionPlan:
    values = dict(
        run_id="SAEA-E-TEST-rails-runner",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="rails-fake",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-rails-runner-0001",
    )
    values.update(overrides)
    return ExecutionPlan(**values)


@dataclass(frozen=True)
class _FakeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


@dataclass
class _FakeAdapter(TaskAdapter):
    samples: tuple[_FakeSample, ...]
    build_task_contract_calls: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    def load_split(self, split_id):
        if split_id != "all":
            return ()
        return self.samples

    def build_task_contract(self, sample, obs: ObsPacket) -> str:
        self.build_task_contract_calls.append(sample.sample_id)
        return f"task-contract-for-{sample.sample_id}"

    def assemble_prompt(self, sample, supply):
        content = []
        if supply is not None:
            content.append({"type": "text", "text": supply.prompt_block})
        content.append({"type": "input_audio", "media_relpath": sample.audio_ref.path})
        return (
            {"role": "system", "content": "fake task"},
            {"role": "user", "content": content},
        )

    def score(self, sample, response):
        self.events.append(f"score:{sample.sample_id}")
        return {"response_length": len(response)}

    def extract_consumption(self, sample, supply, response):
        return build_consumption_trace(
            span_id="full", supply=supply, response_text=response
        )


def _one_sample_adapter() -> _FakeAdapter:
    return _FakeAdapter(
        samples=(
            _FakeSample(
                sample_id="s1",
                audio_ref=AudioRef(path="a.wav", sha256=_SHA_A),
                audio_seconds=2.0,
            ),
        )
    )


def _supply_builder(sample, obs, task_contract):
    assert task_contract == f"task-contract-for-{sample.sample_id}"
    return SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="roster: acme",
        assembly_template_id="t1",
        items=(SupplyItem(item_id="i1", text="acme"),),
    )


def test_runner_executes_zero_supply_then_supplied_and_reuses_obs_query(tmp_path: Path):
    adapter = _one_sample_adapter()
    client = MockCoreClient()

    summary = run_rails_experiment(
        data_root=tmp_path,
        plan=_plan(),
        adapter=adapter,
        core_client=client,
        split_id="all",
        supply_builder=_supply_builder,
    )

    assert summary.arms == ("zero-supply", "supplied")
    assert [r.arm for r in summary.results] == ["zero-supply", "supplied"]
    assert len(client.calls) == 2
    # The task contract is resolved ONCE per sample and reused across every
    # arm. It is stable task knowledge, never mislabeled as the speech query.
    assert adapter.build_task_contract_calls == ["s1"]
    zero_supply_result, supplied_result = summary.results
    assert zero_supply_result.consumption.records == ()
    assert supplied_result.consumption.records != ()
    assert summary.run_id == "SAEA-E-TEST-rails-runner"
    assert summary.protocol_hash == protocol_hash("f" * 64, "bare-core", _SHA_A)


def test_agent_artifact_result_never_reads_task_quality_or_consumption(tmp_path: Path):
    class ArtifactAdapter(_FakeAdapter):
        def score(self, sample, response):
            raise AssertionError("artifact result must not read task quality")

        def extract_consumption(self, sample, supply, response):
            raise AssertionError("artifact result must not derive answer consumption")

    adapter = ArtifactAdapter(samples=_one_sample_adapter().samples)
    client = _RecordingAgentClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="artifact-stop-test-v1",
        controller_registry=_controller_registry(
            "artifact-stop-test-v1", lambda _sample_id: _ImmediateStopController()
        ),
        max_contacts=1,
        slot_count=1,
        queue_depth=1,
        trace_sink=_agent_trace(),
        agent_executor_id="reference-trajectory-v1",
        result_kind="artifact",
    )

    assert summary.result_kind == "artifact"
    assert summary.as_json()["result_kind"] == "artifact"
    assert summary.results[0].result_kind == "artifact"
    assert summary.results[0].metrics == {}
    assert summary.results[0].consumption is None
    assert summary.results[0].as_json()["consumption"] is None
    assert len(client.calls) == 1


def test_agent_result_kind_rejects_unknown_value_before_adapter_work(tmp_path: Path):
    adapter = _one_sample_adapter()
    with pytest.raises(RailsRunnerError, match="result_kind"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=adapter,
            core_client=_RecordingAgentClient(),
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="artifact-stop-test-v1",
            controller_registry=_controller_registry(
                "artifact-stop-test-v1", lambda _sample_id: _ImmediateStopController()
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=1,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
            result_kind="scoreless-ish",
        )


def test_runner_supplied_arm_without_a_supply_builder_is_refused(tmp_path: Path):
    adapter = _one_sample_adapter()
    with pytest.raises(RailsRunnerError, match="supply_builder"):
        run_rails_experiment(
            data_root=tmp_path,
            plan=_plan(),
            adapter=adapter,
            core_client=MockCoreClient(),
            split_id="all",
        )


def test_runner_rejects_an_unknown_arm(tmp_path: Path):
    adapter = _one_sample_adapter()
    with pytest.raises(RailsRunnerError, match="unknown rails arm"):
        run_rails_experiment(
            data_root=tmp_path,
            plan=_plan(),
            adapter=adapter,
            core_client=MockCoreClient(),
            split_id="all",
            arms=("zero-supply", "bogus-arm"),
        )


def test_runner_rejects_a_malformed_execution_plan(tmp_path: Path):
    adapter = _one_sample_adapter()
    with pytest.raises(ExecutionScopeError):
        run_rails_experiment(
            data_root=tmp_path,
            plan=_plan(execution_profile="paper-scale-confirmatory"),
            adapter=adapter,
            core_client=MockCoreClient(),
            split_id="all",
        )


def test_runner_refuses_a_split_with_zero_samples(tmp_path: Path):
    adapter = _FakeAdapter(samples=())
    with pytest.raises(RailsRunnerError, match="zero samples"):
        run_rails_experiment(
            data_root=tmp_path,
            plan=_plan(),
            adapter=adapter,
            core_client=MockCoreClient(),
            split_id="all",
            arms=("zero-supply",),
        )


def test_runner_flight_lock_is_none_when_absent(tmp_path: Path):
    adapter = _one_sample_adapter()
    summary = run_rails_experiment(
        data_root=tmp_path,
        plan=_plan(),
        adapter=adapter,
        core_client=MockCoreClient(),
        split_id="all",
        arms=("zero-supply",),
    )
    assert summary.flight_lock is None


def test_runner_threads_the_flight_lock_through_when_present(tmp_path: Path):
    lock_path = tmp_path / FLIGHT_LOCK_RELPATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text(
        json.dumps({"study_head": "deadbeef", "pid": 123}), encoding="utf-8"
    )

    adapter = _one_sample_adapter()
    summary = run_rails_experiment(
        data_root=tmp_path,
        plan=_plan(),
        adapter=adapter,
        core_client=MockCoreClient(),
        split_id="all",
        arms=("zero-supply",),
    )
    assert summary.flight_lock == {"study_head": "deadbeef", "pid": 123}


def test_rails_arms_constant_is_zero_supply_then_supplied():
    assert RAILS_ARMS == ("zero-supply", "supplied")


def _knowledge_snapshot() -> KnowledgeSnapshot:
    return KnowledgeSnapshot(
        snapshot_id="fake-train-knowledge-v1",
        source_split_identity_hash=_SHA_B,
        source_sample_ids=("train:t1",),
        builder_policy_id="coverage-builder-v1",
        facets=(
            KeyFacet(
                facet_id="operation:dim",
                dimension="operation",
                representation_kind="text",
                representation="Decrease the brightness of a light.",
                source_sample_ids=("train:t1",),
            ),
        ),
        values=(
            ValueBundle(
                value_id="value:dim-light",
                content="Use the dim-light operation when brightness must decrease.",
                associated_facet_ids=("operation:dim",),
                source_sample_ids=("train:t1",),
                provenance_refs=("train:t1",),
                task_target="dim-light",
            ),
        ),
    ).validate()


def _query_state(context, *, loop_step, state_ids=(), value_ids=()) -> QueryState:
    prior = context.query_state
    return QueryState(
        query_id=prior.query_id,
        query_sample_id=prior.query_sample_id,
        speech_packet_id=prior.speech_packet_id,
        speech_packet_sha256=prior.speech_packet_sha256,
        use_split_identity_hash=prior.use_split_identity_hash,
        loop_step=loop_step,
        visible_facet_ids=prior.visible_facet_ids,
        agent_state_ids=state_ids,
        retrieved_value_ids=value_ids,
    ).validate()


def _contact(state: QueryState, index: int, purpose: str) -> AgentContactPlan:
    return AgentContactPlan(
        contact_id=f"contact-{index}",
        query_state_sha256=state.content_hash(),
        purpose=purpose,
        instruction=f"Execute {purpose} while grounding the decision in speech.",
        key_representation_id="K1",
        matcher_policy_id=f"agent-test:{purpose}",
        decoding_params={"temperature": 0},
    )


def _controller_registry(policy_id, factory):
    registry = Registry("test Agent controller")
    registry.register(policy_id, factory)
    return registry


def _agent_trace() -> TraceBuffer:
    return TraceBuffer(_plan().run_id)


class _OrganizeAcquireStopController:
    def __init__(self, events):
        self.events = events

    def initial_contact(self, context):
        assert not hasattr(context, "sample")
        assert not hasattr(context, "knowledge_snapshot")
        assert context.knowledge_snapshot_sha256 == _knowledge_snapshot().content_hash()
        assert context.catalog_facet_ids == ("operation:dim",)
        assert context.catalog_value_ids == ("value:dim-light",)
        assert context.query_state.query_source == "speech_features"
        return _contact(context.query_state, 0, "primary")

    def advance(self, context, contact, response_text):
        step = context.query_state.loop_step
        self.events.append(f"advance:{context.query_state.query_sample_id}:{step}")
        response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        if step == 0:
            state = AgentStateArtifact(
                state_id="state:operation-needed",
                state_kind="intent-factor",
                content="The unresolved factor is the requested operation.",
                source_query_state_sha256=context.query_state.content_hash(),
                source_response_sha256=response_sha256,
                producer_policy_id="organize-test-v1",
                cited_value_ids=(),
            )
            next_state = _query_state(
                context,
                loop_step=1,
                state_ids=(state.state_id,),
            )
            transition = AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=next_state.content_hash(),
                action_kind="organize",
                action_target_refs=("intent-factor-schema-v1",),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(state.state_id,),
                dropped_agent_state_ids=(),
            )
            return AgentLoopAdvance(
                transition=transition,
                next_query_state=next_state,
                new_agent_states=(state,),
                next_contact=_contact(next_state, 1, "retrieve"),
            )
        if step == 1:
            rank_result = RankResult(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                ranking_policy_id="speech-agent-rank-test-v1",
                candidates=(RankedFacet("operation:dim", 1.0),),
            ).validate()
            fusion_decision = FusionDecision(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                query_state_sha256=context.query_state.content_hash(),
                rank_result_sha256=rank_result.content_hash(),
                fusion_policy_id="speech-agent-fusion-test-v1",
                supporting_facet_ids=("operation:dim",),
                selected_value_ids=("value:dim-light",),
            ).validate()
            next_state = _query_state(
                context,
                loop_step=2,
                state_ids=context.query_state.agent_state_ids,
                value_ids=("value:dim-light",),
            )
            transition = AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=next_state.content_hash(),
                action_kind="acquire",
                action_target_refs=("operation",),
                new_value_ids=("value:dim-light",),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            )
            return AgentLoopAdvance(
                transition=transition,
                next_query_state=next_state,
                new_agent_states=(),
                next_contact=_contact(next_state, 2, "solve"),
                rank_result=rank_result,
                fusion_decision=fusion_decision,
            )
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=None,
            action_kind="stop",
            action_target_refs=(),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        )
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
        )


class _RecordingAgentClient:
    def __init__(self):
        self.calls = []
        self._lock = threading.Lock()

    def complete(self, messages, **options):
        with self._lock:
            self.calls.append((tuple(messages), dict(options)))
            call_index = len(self.calls)
        return f"agent-response-{call_index}"


def test_speech_native_agent_loop_keeps_speech_primary_and_separates_state_from_supply(
    tmp_path: Path,
):
    events = []
    adapter = _one_sample_adapter()
    adapter.events = events
    client = _RecordingAgentClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="organize-acquire-stop-test-v1",
        controller_registry=_controller_registry(
            "organize-acquire-stop-test-v1",
            lambda _sample_id: _OrganizeAcquireStopController(events),
        ),
        max_contacts=3,
        slot_count=1,
        queue_depth=2,
        trace_sink=_agent_trace(),
        agent_executor_id="reference-trajectory-v1",
    )

    assert len(summary.results) == 1
    assert summary.agent_executor_version == "repository-reference-v1"
    result = summary.results[0]
    assert result.final_query_state.loop_step == 2
    assert result.final_query_state.retrieved_value_ids == ("value:dim-light",)
    assert [record.plan.purpose for record in result.contacts] == [
        "primary",
        "retrieve",
        "solve",
    ]
    assert [transition.action_kind for transition in result.transitions] == [
        "organize",
        "acquire",
        "stop",
    ]
    assert events == ["advance:s1:0", "advance:s1:1", "advance:s1:2", "score:s1"]

    for messages, options in client.calls:
        parts = messages[1]["content"]
        assert all(part["type"] != "input_audio" for part in parts)
        queries = [
            part["speech_features"]
            for part in parts
            if part["type"] == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert queries == [
            {"packet_id": "fake/dev/s1", "sha256": _SHA_C, "role": "query"}
        ]
        assert options["speech_feature_sample_id"] == "s1"
        assert options["decoding_params"]["id_slot"] == 0
        assert options["agent_contact_id"].startswith("contact-")

    assert client.calls[0][1]["agent_state"] == ()
    assert client.calls[1][1]["agent_state"][0]["state_id"] == (
        "state:operation-needed"
    )
    assert client.calls[2][1]["agent_state"][0]["state_id"] == (
        "state:operation-needed"
    )
    final_text_parts = [
        part for part in client.calls[2][0][1]["content"] if part["type"] == "text"
    ]
    assert final_text_parts == [
        {
            "type": "text",
            "text": "Use the dim-light operation when brightness must decrease.",
            "evidence_id": "value:dim-light",
            "source_uri": (
                f"knowledge-snapshot://{_knowledge_snapshot().content_hash()}/"
                "value:dim-light"
            ),
            "knowledge_role": "value",
        }
    ]


class _ImmediateStopController:
    def initial_contact(self, context):
        return _contact(context.query_state, 0, "primary")

    def advance(self, context, contact, response_text):
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
        )


class _BarrierAgentClient(_RecordingAgentClient):
    def __init__(self):
        super().__init__()
        self.barrier = threading.Barrier(2)
        self.active = 0
        self.peak = 0

    def complete(self, messages, **options):
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        self.barrier.wait(timeout=2)
        try:
            return super().complete(messages, **options)
        finally:
            with self._lock:
                self.active -= 1


class _OutOfOrderTracingClient(_RecordingAgentClient):
    def __init__(self, sink):
        super().__init__()
        self.sink = DispatchingSink(sink)
        self.second_finished = threading.Event()

    def complete(self, messages, **options):
        sample_id = options["speech_feature_sample_id"]
        self.sink.emit(
            "MODEL_REQUEST",
            f"{sample_id}/fake-request",
            {"sample_id": sample_id},
        )
        if sample_id == "s0":
            assert self.second_finished.wait(timeout=2)
        response = super().complete(messages, **options)
        self.sink.emit(
            "MODEL_RESPONSE",
            f"{sample_id}/fake-response",
            {"sample_id": sample_id, "text": response},
        )
        if sample_id == "s1":
            self.second_finished.set()
        return response


def test_speech_native_agent_loop_batches_trajectories_and_keeps_slot_affinity(
    tmp_path: Path,
):
    samples = tuple(
        _FakeSample(
            sample_id=f"s{index}",
            audio_ref=AudioRef(path=f"a-{index}.wav", sha256=_SHA_A),
            audio_seconds=2.0,
        )
        for index in range(2)
    )
    adapter = _FakeAdapter(samples=samples)
    client = _BarrierAgentClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={
            sample.sample_id: {
                "packet_id": f"fake/dev/{sample.sample_id}",
                "sha256": _SHA_C,
            }
            for sample in samples
        },
        controller_policy_id="immediate-stop-test-v1",
        controller_registry=_controller_registry(
            "immediate-stop-test-v1",
            lambda _sample_id: _ImmediateStopController(),
        ),
        max_contacts=1,
        slot_count=2,
        queue_depth=4,
        trace_sink=_agent_trace(),
        agent_executor_id="reference-trajectory-v1",
    )

    assert [result.sample_id for result in summary.results] == ["s0", "s1"]
    assert client.peak == 2
    assert {options["decoding_params"]["id_slot"] for _, options in client.calls} == {
        0,
        1,
    }


def test_speech_native_agent_loop_flushes_concurrent_model_traces_in_split_order(
    tmp_path: Path,
):
    samples = tuple(
        _FakeSample(
            sample_id=f"s{index}",
            audio_ref=AudioRef(path=f"a-{index}.wav", sha256=_SHA_A),
            audio_seconds=2.0,
        )
        for index in range(2)
    )
    trace = _agent_trace()
    client = _OutOfOrderTracingClient(trace)

    run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=_FakeAdapter(samples=samples),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={
            sample.sample_id: {
                "packet_id": f"fake/dev/{sample.sample_id}",
                "sha256": _SHA_C,
            }
            for sample in samples
        },
        controller_policy_id="immediate-stop-test-v1",
        controller_registry=_controller_registry(
            "immediate-stop-test-v1",
            lambda _sample_id: _ImmediateStopController(),
        ),
        max_contacts=1,
        slot_count=2,
        queue_depth=4,
        trace_sink=trace,
        agent_executor_id="reference-trajectory-v1",
    )

    assert [record_id for _, record_id, _ in trace.records] == [
        "s0/fake-request",
        "s0/fake-response",
        "s0/agent-loop/org",
        "s0/agent-loop/supply",
        "s0/agent-loop/runtime-use",
        "s1/fake-request",
        "s1/fake-response",
        "s1/agent-loop/org",
        "s1/agent-loop/supply",
        "s1/agent-loop/runtime-use",
        "s0/agent-loop/posthoc-use",
        "s1/agent-loop/posthoc-use",
    ]


def test_speech_native_agent_loop_refuses_incomplete_packet_materialization_before_contact(
    tmp_path: Path,
):
    adapter = _one_sample_adapter()
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="materialize every query sample"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=adapter,
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={},
            controller_policy_id="immediate-stop-test-v1",
            controller_registry=_controller_registry(
                "immediate-stop-test-v1",
                lambda _sample_id: _ImmediateStopController(),
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )

    assert client.calls == []


def test_reference_agent_executor_is_model_free_only(tmp_path: Path):
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="restricted to model-free-check"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(),
            adapter=_one_sample_adapter(),
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="immediate-stop-test-v1",
            controller_registry=_controller_registry(
                "immediate-stop-test-v1",
                lambda _sample_id: _ImmediateStopController(),
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )

    assert client.calls == []


class _KnowledgeLeakingController(_ImmediateStopController):
    def initial_contact(self, context):
        return AgentContactPlan(
            contact_id="contact-leak",
            query_state_sha256=context.query_state.content_hash(),
            purpose="leak",
            instruction=("Use the dim-light operation when brightness must decrease."),
            key_representation_id="K1",
            matcher_policy_id="agent-test:leak",
            decoding_params={"temperature": 0},
        )


def test_agent_control_cannot_embed_unacquired_knowledge_payload(tmp_path: Path):
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="cannot embed frozen knowledge"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=_one_sample_adapter(),
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="knowledge-leak-test-v1",
            controller_registry=_controller_registry(
                "knowledge-leak-test-v1",
                lambda _sample_id: _KnowledgeLeakingController(),
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )

    assert client.calls == []


# ---------------------------------------------------------------------------
# C4 scale fixes (docs/readiness/2026-08-23-knowledge-plane-baseline-
# rulings.md Sec 4, items 1-2): the payload guard's protected-material tuple
# is precomputed once per run and threaded down, instead of being
# re-materialized from the snapshot on every contact wave.
# ---------------------------------------------------------------------------


def test_protected_knowledge_material_casefolds_facets_and_values_once():
    material = rails_runner_module._protected_knowledge_material(_knowledge_snapshot())
    assert material == (
        "decrease the brightness of a light.",
        "use the dim-light operation when brightness must decrease.",
    )


def test_assert_agent_control_excludes_knowledge_payloads_uses_the_passed_tuple():
    # Same refusal/acceptance behavior as before the refactor, but the
    # function now only ever sees the precomputed tuple -- it has no
    # `snapshot` parameter to re-derive it from any more.
    protected_material = rails_runner_module._protected_knowledge_material(
        _knowledge_snapshot()
    )
    leaking_plan = AgentContactPlan(
        contact_id="contact-leak",
        query_state_sha256=_SHA_A,
        purpose="leak",
        instruction="Use the dim-light operation when brightness must decrease.",
        key_representation_id="K1",
        matcher_policy_id="agent-test:leak",
        decoding_params={"temperature": 0},
    )
    with pytest.raises(RailsRunnerError, match="cannot embed frozen knowledge"):
        rails_runner_module._assert_agent_control_excludes_knowledge_payloads(
            leaking_plan, protected_material
        )

    safe_plan = AgentContactPlan(
        contact_id="contact-safe",
        query_state_sha256=_SHA_A,
        purpose="safe",
        instruction="Ask a grounded clarification question about the speech query.",
        key_representation_id="K1",
        matcher_policy_id="agent-test:safe",
        decoding_params={"temperature": 0},
    )
    rails_runner_module._assert_agent_control_excludes_knowledge_payloads(
        safe_plan, protected_material
    )


def test_speech_native_agent_loop_builds_the_knowledge_payload_guard_once_per_run(
    tmp_path: Path, monkeypatch
):
    """Perf-shaped sanity: across 2 samples x 3 contact waves each (6 waves
    total), the protected-material tuple is built exactly once -- in
    run_speech_native_agent_loop, after snapshot validation -- never rebuilt
    per wave or per trajectory.
    """
    calls: list[object] = []
    original = rails_runner_module._protected_knowledge_material

    def counting_builder(snapshot):
        calls.append(snapshot)
        return original(snapshot)

    monkeypatch.setattr(
        rails_runner_module, "_protected_knowledge_material", counting_builder
    )

    samples = tuple(
        _FakeSample(
            sample_id=f"s{index}",
            audio_ref=AudioRef(path=f"a-{index}.wav", sha256=_SHA_A),
            audio_seconds=2.0,
        )
        for index in range(2)
    )
    adapter = _FakeAdapter(samples=samples)
    events: list[str] = []

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=_RecordingAgentClient(),
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={
            sample.sample_id: {
                "packet_id": f"fake/dev/{sample.sample_id}",
                "sha256": _SHA_C,
            }
            for sample in samples
        },
        controller_policy_id="organize-acquire-stop-test-v1",
        controller_registry=_controller_registry(
            "organize-acquire-stop-test-v1",
            lambda _sample_id: _OrganizeAcquireStopController(events),
        ),
        max_contacts=3,
        slot_count=2,
        queue_depth=4,
        trace_sink=_agent_trace(),
        agent_executor_id="reference-trajectory-v1",
    )

    assert len(summary.results) == 2
    assert sum(len(result.contacts) for result in summary.results) == 6
    assert len(calls) == 1
    assert calls[0] == _knowledge_snapshot()


class _NeverStopController(_ImmediateStopController):
    def advance(self, context, contact, response_text):
        next_step = context.query_state.loop_step + 1
        state_id = f"state:{next_step}"
        next_state = _query_state(
            context,
            loop_step=next_step,
            state_ids=(*context.query_state.agent_state_ids, state_id),
        )
        state = AgentStateArtifact(
            state_id=state_id,
            state_kind="unresolved",
            content="The controller requests another observation.",
            source_query_state_sha256=context.query_state.content_hash(),
            source_response_sha256=hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest(),
            producer_policy_id="never-stop-test-v1",
            cited_value_ids=(),
        )
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=next_state.content_hash(),
                action_kind="organize",
                action_target_refs=("state",),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(state_id,),
                dropped_agent_state_ids=(),
            ),
            next_query_state=next_state,
            new_agent_states=(state,),
            next_contact=_contact(next_state, next_state.loop_step, "organize"),
        )


class _UnboundAcquireController(_OrganizeAcquireStopController):
    def advance(self, context, contact, response_text):
        advance = super().advance(context, contact, response_text)
        if advance.transition.action_kind == "acquire":
            return replace(advance, rank_result=None, fusion_decision=None)
        return advance


def test_agent_acquisition_requires_rank_and_fusion_binding(tmp_path: Path):
    client = _RecordingAgentClient()

    with pytest.raises(
        RailsRunnerError,
        match="requires RankResult and FusionDecision",
    ):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=_one_sample_adapter(),
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="unbound-acquire-test-v1",
            controller_registry=_controller_registry(
                "unbound-acquire-test-v1",
                lambda _sample_id: _UnboundAcquireController([]),
            ),
            max_contacts=3,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )

    assert len(client.calls) == 2


def test_speech_native_agent_loop_refuses_a_controller_that_exceeds_contact_ceiling(
    tmp_path: Path,
):
    adapter = _one_sample_adapter()
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="contact ceiling"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=adapter,
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="never-stop-test-v1",
            controller_registry=_controller_registry(
                "never-stop-test-v1",
                lambda _sample_id: _NeverStopController(),
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )


def test_speech_native_agent_loop_bootstrap_supply_is_visible_and_persisted(
    tmp_path: Path,
):
    adapter = _one_sample_adapter()
    client = _RecordingAgentClient()
    trace = _agent_trace()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="immediate-stop-test-v1",
        controller_registry=_controller_registry(
            "immediate-stop-test-v1",
            lambda _sample_id: _ImmediateStopController(),
        ),
        bootstrap_value_ids=("value:dim-light",),
        max_contacts=1,
        slot_count=1,
        queue_depth=2,
        trace_sink=trace,
        agent_executor_id="reference-trajectory-v1",
    )

    result = summary.results[0]
    assert result.initial_query_state.retrieved_value_ids == ("value:dim-light",)
    assert result.final_query_state.retrieved_value_ids == ("value:dim-light",)
    text_parts = [
        part for part in client.calls[0][0][1]["content"] if part["type"] == "text"
    ]
    assert [part["evidence_id"] for part in text_parts] == ["value:dim-light"]
    assert [channel for channel, _, _ in trace.records] == [
        "ORG",
        "SUPPLY",
        "USE",
        "USE",
    ]
    assert trace.records[1][2]["supply_bootstrap_value_ids"] == ["value:dim-light"]
    runtime_payload = trace.records[2][2]
    assert runtime_payload["use_speech_packet_sha256"] == _SHA_C
    assert runtime_payload["use_contacts"][0]["slot_id"] == 0
    assert runtime_payload["use_waves"][0]["fanout_semantics"] == "single"
    assert runtime_payload["use_waves"][0]["termination_reason"] == ("controller-stop")
    assert runtime_payload["use_transitions"][0]["action_kind"] == "stop"
    posthoc_payload = trace.records[3][2]
    assert (
        posthoc_payload["use_runtime_trace_sha256"]
        == runtime_payload["use_runtime_trace_sha256"]
    )
    assert posthoc_payload["use_metrics"] == {"response_length": 16}
    json.dumps(summary.as_json(), sort_keys=True)


def test_speech_native_agent_loop_keeps_key_facets_separate_from_values(
    tmp_path: Path,
):
    client = _RecordingAgentClient()
    trace = _agent_trace()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="immediate-stop-test-v1",
        controller_registry=_controller_registry(
            "immediate-stop-test-v1",
            lambda _sample_id: _ImmediateStopController(),
        ),
        bootstrap_facet_ids=("operation:dim",),
        max_contacts=1,
        slot_count=1,
        queue_depth=2,
        trace_sink=trace,
        agent_executor_id="reference-trajectory-v1",
    )

    result = summary.results[0]
    assert result.initial_query_state.visible_facet_ids == ("operation:dim",)
    assert result.initial_query_state.retrieved_value_ids == ()
    text_parts = [
        part for part in client.calls[0][0][1]["content"] if part["type"] == "text"
    ]
    assert text_parts == [
        {
            "type": "text",
            "text": "Decrease the brightness of a light.",
            "evidence_id": "key:operation:dim",
            "source_uri": (
                f"knowledge-snapshot://{_knowledge_snapshot().content_hash()}/"
                "operation:dim"
            ),
            "knowledge_role": "key",
        }
    ]
    supply_payload = next(
        payload for channel, _, payload in trace.records if channel == "SUPPLY"
    )
    assert supply_payload["supply_bootstrap_facet_ids"] == ["operation:dim"]
    assert supply_payload["supply_bootstrap_value_ids"] == []


def test_speech_native_agent_loop_refuses_unknown_bootstrap_value_before_contact(
    tmp_path: Path,
):
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="bootstrap_value_ids.*outside"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(execution_profile="model-free-check"),
            adapter=_one_sample_adapter(),
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="immediate-stop-test-v1",
            controller_registry=_controller_registry(
                "immediate-stop-test-v1",
                lambda _sample_id: _ImmediateStopController(),
            ),
            bootstrap_value_ids=("value:unknown",),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="reference-trajectory-v1",
        )

    assert client.calls == []


@dataclass(frozen=True)
class _DAGNode:
    node_id: str
    trajectory_id: str
    stage_index: int


def test_shared_contact_dag_prioritizes_new_evidence_over_root_backlog():
    execution_order = []
    root_zero = _DAGNode("root-0", "sample-0", 0)
    root_one = _DAGNode("root-1", "sample-1", 0)
    evidence = _DAGNode("evidence-0", "sample-0", 1)

    with ThreadPoolExecutor(max_workers=1) as pool:
        completions = run_bounded_contact_dag(
            initial_nodes=(root_zero, root_one),
            max_in_flight=1,
            queue_depth=2,
            node_key=lambda node: node.node_id,
            sort_key=lambda node: (node.trajectory_id, node.stage_index),
            is_runnable=lambda _node: True,
            submit=lambda node: pool.submit(
                lambda: execution_order.append(node.node_id) or node.node_id
            ),
            on_result=lambda node, _response: (
                ContactDAGAdvance(ready_front=(evidence,))
                if node is root_zero
                else ContactDAGAdvance()
            ),
            on_error=lambda _node, error: (_ for _ in ()).throw(error),
        )

    assert execution_order == ["root-0", "evidence-0", "root-1"]
    assert [completion.node.node_id for completion in completions] == execution_order


def test_shared_contact_dag_never_resubmits_a_duplicate_node():
    root = _DAGNode("root", "sample-0", 0)

    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RailsRunnerError, match="duplicate contact DAG node"):
            run_bounded_contact_dag(
                initial_nodes=(root,),
                max_in_flight=1,
                queue_depth=1,
                node_key=lambda node: node.node_id,
                sort_key=lambda node: (node.stage_index,),
                is_runnable=lambda _node: True,
                submit=lambda node: pool.submit(lambda: node.node_id),
                on_result=lambda _node, _response: ContactDAGAdvance(
                    ready_front=(root,)
                ),
                on_error=lambda _node, error: (_ for _ in ()).throw(error),
            )


class _ParallelBatchStopController:
    def __init__(self):
        self.observed = None

    def initial_contact(self, context):
        return AgentContactBatch(
            batch_id="initial-primary-retrieval",
            query_state_sha256=context.query_state.content_hash(),
            contacts=(
                _contact(context.query_state, 0, "primary"),
                _contact(context.query_state, 1, "retrieve"),
            ),
        )

    def advance(self, context, contact, response_text):
        self.observed = (contact, response_text)
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id="contact-0",
        )


class _ParallelBatchClient(_RecordingAgentClient):
    def __init__(self):
        super().__init__()
        self.active = 0
        self.peak = 0

    def complete(self, messages, **options):
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            super().complete(messages, **options)
            return f"response:{options['agent_contact_id']}"
        finally:
            with self._lock:
                self.active -= 1


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_agent_batch_serializes_on_one_slot_and_aggregates_in_order(
    tmp_path: Path,
):
    controller = _ParallelBatchStopController()
    client = _ParallelBatchClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="parallel-batch-stop-test-v1",
        controller_registry=_controller_registry(
            "parallel-batch-stop-test-v1", lambda _sample_id: controller
        ),
        max_contacts=2,
        slot_count=2,
        queue_depth=4,
        trace_sink=_agent_trace(),
        agent_executor_id="openjiuwen-workflow-v1",
    )

    assert client.peak == 1
    assert summary.agent_executor_id == "openjiuwen-workflow-v1"
    assert summary.agent_executor_version == "0.1.16.post2"
    assert isinstance(controller.observed[0], AgentContactBatch)
    assert controller.observed[1] == (
        "response:contact-0",
        "response:contact-1",
    )
    result = summary.results[0]
    assert [record.plan.contact_id for record in result.contacts] == [
        "contact-0",
        "contact-1",
    ]
    assert {record.slot_id for record in result.contacts} == {0}
    assert result.final_response_text == "response:contact-0"
    assert len(result.waves) == 1
    wave = result.waves[0]
    assert wave.batch_id == "initial-primary-retrieval"
    assert wave.fanout_semantics == "evidence_parallel"
    assert wave.slot_ids == (0, 0)
    assert wave.selected_final_contact_id == "contact-0"
    assert wave.response_envelope_sha256 == agent_response_sha256(
        controller.observed[0], controller.observed[1]
    )
    for messages, _options in client.calls:
        query_parts = [
            part
            for part in messages[1]["content"]
            if part["type"] == "input_speech_features"
        ]
        assert len(query_parts) == 1
        assert query_parts[0]["speech_features"]["sha256"] == _SHA_C


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_agent_advances_multiple_causal_waves(tmp_path: Path):
    events = []
    client = _RecordingAgentClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="contact-causal-waves-test-v1",
        controller_registry=_controller_registry(
            "contact-causal-waves-test-v1",
            lambda _sample_id: _OrganizeAcquireStopController(events),
        ),
        max_contacts=3,
        slot_count=2,
        queue_depth=4,
        trace_sink=_agent_trace(),
        agent_executor_id="openjiuwen-workflow-v1",
    )

    result = summary.results[0]
    assert len(result.contacts) == 3
    assert [transition.action_kind for transition in result.transitions] == [
        "organize",
        "acquire",
        "stop",
    ]
    assert len({record.slot_id for record in result.contacts}) == 1
    assert result.final_query_state.retrieved_value_ids == ("value:dim-light",)
    assert events == ["advance:s1:0", "advance:s1:1", "advance:s1:2"]


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_agent_parallelizes_across_trajectory_affine_samples(
    tmp_path: Path,
):
    samples = tuple(
        _FakeSample(
            sample_id=f"s{index}",
            audio_ref=AudioRef(path=f"a-{index}.wav", sha256=_SHA_A),
            audio_seconds=2.0,
        )
        for index in range(2)
    )
    client = _BarrierAgentClient()

    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(),
        adapter=_FakeAdapter(samples=samples),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={
            sample.sample_id: {
                "packet_id": f"fake/dev/{sample.sample_id}",
                "sha256": _SHA_C,
            }
            for sample in samples
        },
        controller_policy_id="openjiuwen-parallel-samples-test-v1",
        controller_registry=_controller_registry(
            "openjiuwen-parallel-samples-test-v1",
            lambda _sample_id: _ImmediateStopController(),
        ),
        max_contacts=1,
        slot_count=2,
        queue_depth=2,
        trace_sink=_agent_trace(),
        agent_executor_id="openjiuwen-workflow-v1",
    )

    assert client.peak == 2
    assert {result.contacts[0].slot_id for result in summary.results} == {0, 1}


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_agent_matches_the_reference_trajectory_semantics(
    tmp_path: Path,
):
    summaries = []
    for executor_id in (
        "reference-trajectory-v1",
        "openjiuwen-workflow-v1",
    ):
        events = []
        summaries.append(
            run_speech_native_agent_loop(
                data_root=tmp_path / executor_id,
                plan=_plan(
                    execution_profile=(
                        "model-free-check"
                        if executor_id == "reference-trajectory-v1"
                        else "bounded-discovery-probe"
                    )
                ),
                adapter=_one_sample_adapter(),
                core_client=_RecordingAgentClient(),
                split_id="all",
                knowledge_snapshot=_knowledge_snapshot(),
                speech_packet_bindings={
                    "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
                },
                controller_policy_id=f"equivalence-{executor_id}",
                controller_registry=_controller_registry(
                    f"equivalence-{executor_id}",
                    lambda _sample_id, events=events: _OrganizeAcquireStopController(
                        events
                    ),
                ),
                max_contacts=3,
                slot_count=1,
                queue_depth=2,
                trace_sink=_agent_trace(),
                agent_executor_id=executor_id,
            )
        )

    assert summaries[0].results[0].as_json() == summaries[1].results[0].as_json()


class _BatchOrganizeStopController:
    def __init__(self):
        self.batch_response = None

    def initial_contact(self, context):
        return AgentContactBatch(
            batch_id="parallel-factors",
            query_state_sha256=context.query_state.content_hash(),
            contacts=(
                _contact(context.query_state, 0, "content-factor"),
                _contact(context.query_state, 1, "boundary-factor"),
            ),
        )

    def advance(self, context, contact, response_text):
        if context.query_state.loop_step == 0:
            self.batch_response = response_text
            response_sha256 = agent_response_sha256(contact, response_text)
            state = AgentStateArtifact(
                state_id="state:parallel-factors",
                state_kind="intent-factors",
                content="The content and boundary factors were analyzed in parallel.",
                source_query_state_sha256=context.query_state.content_hash(),
                source_response_sha256=response_sha256,
                producer_policy_id="batch-organize-stop-test-v1",
                cited_value_ids=(),
            )
            next_state = _query_state(
                context,
                loop_step=1,
                state_ids=(state.state_id,),
            )
            return AgentLoopAdvance(
                transition=AgentStepTransition(
                    snapshot_sha256=context.knowledge_snapshot_sha256,
                    prior_query_state_sha256=context.query_state.content_hash(),
                    next_query_state_sha256=next_state.content_hash(),
                    action_kind="organize",
                    action_target_refs=("parallel-factors",),
                    new_value_ids=(),
                    used_value_ids=(),
                    dropped_value_ids=(),
                    new_agent_state_ids=(state.state_id,),
                    dropped_agent_state_ids=(),
                ),
                next_query_state=next_state,
                new_agent_states=(state,),
                next_contact=_contact(next_state, 2, "solve"),
            )
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ),
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
        )


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_batch_response_can_materialize_next_wave_agent_state(
    tmp_path: Path,
):
    controller = _BatchOrganizeStopController()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(),
        adapter=_one_sample_adapter(),
        core_client=_RecordingAgentClient(),
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="batch-organize-stop-test-v1",
        controller_registry=_controller_registry(
            "batch-organize-stop-test-v1",
            lambda _sample_id: controller,
        ),
        max_contacts=3,
        slot_count=2,
        queue_depth=4,
        trace_sink=_agent_trace(),
        agent_executor_id="openjiuwen-workflow-v1",
    )

    result = summary.results[0]
    assert len(result.contacts) == 3
    assert result.final_query_state.agent_state_ids == ("state:parallel-factors",)
    assert result.agent_states[0].source_response_sha256 == agent_response_sha256(
        AgentContactBatch(
            batch_id="parallel-factors",
            query_state_sha256=result.initial_query_state.content_hash(),
            contacts=tuple(record.plan for record in result.contacts[:2]),
        ),
        controller.batch_response,
    )


@pytest.mark.skipif(
    not openjiuwen_available(),
    reason="openjiuwen is absent; the reference executor remains dependency-free",
)
def test_openjiuwen_agent_refuses_an_oversized_batch_before_model_contact(
    tmp_path: Path,
):
    controller = _ParallelBatchStopController()
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="contact ceiling"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(),
            adapter=_one_sample_adapter(),
            core_client=client,
            split_id="all",
            knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings={
                "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
            },
            controller_policy_id="oversized-contact-batch-test-v1",
            controller_registry=_controller_registry(
                "oversized-contact-batch-test-v1",
                lambda _sample_id: controller,
            ),
            max_contacts=1,
            slot_count=1,
            queue_depth=2,
            trace_sink=_agent_trace(),
            agent_executor_id="openjiuwen-workflow-v1",
        )

    assert client.calls == []
