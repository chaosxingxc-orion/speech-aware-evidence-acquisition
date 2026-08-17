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
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, ExecutionScopeError
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.core.flight_lock import FLIGHT_LOCK_RELPATH
from speech_aware_evidence_acquisition.rails import (
    AudioRef,
    MockCoreClient,
    ObsPacket,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    TaskAdapter,
    build_consumption_trace,
    run_rails_experiment,
)
from speech_aware_evidence_acquisition.rails.runner import RAILS_ARMS, RailsRunnerError

_SHA_A = "a" * 64


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
    build_query_calls: list[str] = field(default_factory=list)

    def load_split(self, split_id):
        if split_id != "all":
            return ()
        return self.samples

    def build_query(self, sample, obs: ObsPacket) -> str:
        self.build_query_calls.append(sample.sample_id)
        return f"query-for-{sample.sample_id}"

    def assemble_prompt(self, sample, supply):
        content = supply.prompt_block if supply is not None else "no-supply"
        return (
            {"role": "system", "content": "fake task"},
            {"role": "user", "content": content},
        )

    def score(self, sample, response):
        return {"response_length": len(response)}

    def extract_consumption(self, sample, supply, response):
        return build_consumption_trace(span_id="full", supply=supply, response_text=response)


def _one_sample_adapter() -> _FakeAdapter:
    return _FakeAdapter(
        samples=(_FakeSample(sample_id="s1", audio_ref=AudioRef(path="a.wav", sha256=_SHA_A), audio_seconds=2.0),)
    )


def _supply_builder(sample, obs, query):
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
    # build_query is resolved ONCE per sample and reused across every arm --
    # not re-derived per arm.
    assert adapter.build_query_calls == ["s1"]
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
