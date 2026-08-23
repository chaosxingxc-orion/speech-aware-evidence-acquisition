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
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, ExecutionScopeError
from speech_aware_evidence_acquisition.core.base import Registry
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.flight_lock import FLIGHT_LOCK_RELPATH
from speech_aware_evidence_acquisition.rails import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentStateArtifact,
    AgentStepTransition,
    AudioRef,
    KeyFacet,
    KnowledgeSnapshot,
    MockCoreClient,
    ObsPacket,
    QueryState,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    TaskAdapter,
    ValueBundle,
    build_consumption_trace,
    run_rails_experiment,
    run_speech_native_agent_loop,
)
from speech_aware_evidence_acquisition.rails.runner import RAILS_ARMS, RailsRunnerError

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
        return build_consumption_trace(span_id="full", supply=supply, response_text=response)


def _one_sample_adapter() -> _FakeAdapter:
    return _FakeAdapter(
        samples=(_FakeSample(sample_id="s1", audio_ref=AudioRef(path="a.wav", sha256=_SHA_A), audio_seconds=2.0),)
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
    lock_path.write_text(json.dumps({"study_head": "deadbeef", "pid": 123}), encoding="utf-8")

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
        query_id=f"{prior.query_id}:step{loop_step}",
        query_sample_id=prior.query_sample_id,
        speech_packet_id=prior.speech_packet_id,
        speech_packet_sha256=prior.speech_packet_sha256,
        use_split_identity_hash=prior.use_split_identity_hash,
        loop_step=loop_step,
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


class _OrganizeAcquireStopController:
    def __init__(self, events):
        self.events = events

    def initial_contact(self, context):
        assert not hasattr(context, "sample")
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
                snapshot_sha256=context.knowledge_snapshot.content_hash(),
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
            next_state = _query_state(
                context,
                loop_step=2,
                state_ids=context.query_state.agent_state_ids,
                value_ids=("value:dim-light",),
            )
            transition = AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot.content_hash(),
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
            )
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot.content_hash(),
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
        plan=_plan(),
        adapter=adapter,
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={
            "s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}
        },
        controller_policy_id="organize-acquire-stop-test-v1",
        controller_registry=_controller_registry(
            "organize-acquire-stop-test-v1",
            lambda _sample_id: _OrganizeAcquireStopController(events),
        ),
        max_contacts=3,
        slot_count=1,
        queue_depth=2,
    )

    assert len(summary.results) == 1
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
        }
    ]


class _ImmediateStopController:
    def initial_contact(self, context):
        return _contact(context.query_state, 0, "primary")

    def advance(self, context, contact, response_text):
        return AgentLoopAdvance(
            transition=AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot.content_hash(),
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
        plan=_plan(),
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
    )

    assert [result.sample_id for result in summary.results] == ["s0", "s1"]
    assert client.peak == 2
    assert {options["decoding_params"]["id_slot"] for _, options in client.calls} == {
        0,
        1,
    }


def test_speech_native_agent_loop_refuses_incomplete_packet_materialization_before_contact(
    tmp_path: Path,
):
    adapter = _one_sample_adapter()
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="materialize every query sample"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(),
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
        )

    assert client.calls == []


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
                snapshot_sha256=context.knowledge_snapshot.content_hash(),
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


def test_speech_native_agent_loop_refuses_a_controller_that_exceeds_contact_ceiling(
    tmp_path: Path,
):
    adapter = _one_sample_adapter()
    client = _RecordingAgentClient()

    with pytest.raises(RailsRunnerError, match="contact ceiling"):
        run_speech_native_agent_loop(
            data_root=tmp_path,
            plan=_plan(),
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
        )
