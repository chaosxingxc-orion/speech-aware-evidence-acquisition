"""Adapter choke point: allowlist exact-set, boundary, budgets, tracing."""

import json

import pytest

from speech_aware_evidence_acquisition.contracts import (
    BoundaryViolation,
    ExecutionPlan,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, FrozenCoreError
from speech_aware_evidence_acquisition.core.tracing import TraceSink


class _OpenGate:
    def __init__(self):
        self.checked_plans = []

    def assert_model_touch_allowed(self, plan):
        self.checked_plans.append(plan)


def _plan(**overrides):
    base = dict(
        run_id="SAEA-E-000-adapter",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=2,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=250,
        protocol_hash="b" * 64,
    )
    base.update(overrides)
    return ExecutionPlan(**base)


def _payload(arm="bare-core", **overrides):
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "earnings22-original",
        "sample_id": "5000001",
        "speech_ref": "earnings22-original/5000001",
        "media_relpath": "datasets/earnings21-22/earnings22/media/5000001.mp3",
        "audio_seconds": 100.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe the speech verbatim.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    assert set(payload) == set(ARM_VISIBLE_FIELDS[arm])
    payload.update(overrides)
    return payload


def _fake_transport(request_bytes):
    assert isinstance(request_bytes, bytes)
    return json.dumps(
        {"text": "hello world", "usage": {"prompt_tokens": 5, "completion_tokens": 2}}
    ).encode()


def _adapter(tmp_path, gate=None, plan=None, arm="bare-core"):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-adapter")
    return FrozenCoreAdapter(
        gate=gate or _OpenGate(),
        plan=plan or _plan(),
        arm=arm,
        transport=_fake_transport,
        sink=sink,
    ), sink


def test_gate_is_checked_at_construction(tmp_path):
    gate = _OpenGate()
    _adapter(tmp_path, gate=gate)
    assert len(gate.checked_plans) == 1


def test_request_round_trip_traces_and_counts(tmp_path):
    adapter, sink = _adapter(tmp_path)
    response = adapter.request(_payload())
    assert response.text == "hello world"
    assert len(response.request_sha256) == 64
    assert list(sink.manifest()) == ["req-1/request", "req-1/response", "req-1/cost"]
    summary = adapter.cost_summary()
    assert summary["calls_used"] == 1
    assert summary["audio_seconds_used"] == 100.0
    assert summary["completion_tokens_total"] == 2


def test_extra_field_refused_before_transport(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="allowlist"):
        adapter.request(_payload(supplied_evidence=[{"content": "x"}]))


def test_missing_field_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    payload = _payload()
    del payload["decoding_params"]
    with pytest.raises(FrozenCoreError, match="allowlist"):
        adapter.request(payload)


def test_forbidden_field_inside_value_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(BoundaryViolation):
        adapter.request(_payload(history=[{"reference_transcript": "gold"}]))


def test_decoding_params_messages_key_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="decoding_params"):
        adapter.request(
            _payload(decoding_params={"temperature": 0, "messages": [{"role": "user"}]})
        )


def test_decoding_params_unknown_key_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="decoding_params"):
        adapter.request(_payload(decoding_params={"logit_bias": {"1": 10}}))


def test_call_budget_exhaustion_fails_closed(tmp_path):
    adapter, _ = _adapter(tmp_path, plan=_plan(planned_model_calls=1))
    adapter.request(_payload())
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter.request(_payload(request_id="req-2"))


def test_audio_budget_exhaustion_fails_closed(tmp_path):
    adapter, _ = _adapter(tmp_path, plan=_plan(planned_speech_audio_seconds=150))
    adapter.request(_payload())
    with pytest.raises(FrozenCoreError, match="audio budget"):
        adapter.request(_payload(request_id="req-2"))


def test_unknown_arm_refused(tmp_path):
    with pytest.raises(FrozenCoreError, match="arm"):
        _adapter(tmp_path, arm="oracle-arm")


def test_audio_seconds_nan_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="finite positive number"):
        adapter.request(_payload(audio_seconds=float("nan")))


def test_audio_seconds_infinite_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="finite positive number"):
        adapter.request(_payload(audio_seconds=float("inf")))


def test_audio_seconds_bool_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="finite positive number"):
        adapter.request(_payload(audio_seconds=True))


def test_audio_seconds_valid_float_still_accepted(tmp_path):
    adapter, _ = _adapter(tmp_path)
    response = adapter.request(_payload(audio_seconds=100.0))
    assert response.text == "hello world"
    assert adapter.cost_summary()["audio_seconds_used"] == 100.0


def test_metering_counts_before_transport_even_when_transport_raises(tmp_path):
    calls = []

    def _raising_transport(request_bytes):
        calls.append(request_bytes)
        raise RuntimeError("transport exploded")

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-meter")
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_raising_transport,
        sink=sink,
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        adapter.request(_payload())
    assert len(calls) == 1
    summary = adapter.cost_summary()
    assert summary["calls_used"] == 1
    assert summary["audio_seconds_used"] == 100.0
