"""Contract: the adapter is inseparable from the real gate (fail-closed end to end)."""

import json

import pytest

from gate_fixture import GateFixture

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError, GateClosed
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter
from speech_aware_evidence_acquisition.core.tracing import TraceSink


def _fake_transport(request_bytes):
    return json.dumps({"text": "ok", "usage": {}}).encode()


def test_adapter_construction_passes_through_a_real_open_gate(tmp_path):
    fixture = GateFixture(tmp_path)
    plan = fixture.plan()
    adapter = FrozenCoreAdapter(
        gate=fixture.gate(),
        plan=plan,
        arm="bare-core",
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id),
    )
    assert adapter.cost_summary()["calls_used"] == 0


def test_adapter_refuses_when_the_gate_is_closed(tmp_path):
    fixture = GateFixture(tmp_path)
    # No dedicated tamper helper exists on GateFixture; break the E0 receipt the
    # same way every other gate-refusal test in test_exposure_and_gate.py does —
    # corrupt a deliverable's recorded artifact hash before materializing the gate.
    fixture.deliverables["d2_leakage"]["sha256"] = "f" * 64
    with pytest.raises(GateClosed):
        FrozenCoreAdapter(
            gate=fixture.gate(),
            plan=fixture.plan(),
            arm="bare-core",
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", fixture.plan().run_id),
        )


def test_adapter_refuses_model_free_profiles(tmp_path):
    fixture = GateFixture(tmp_path)
    plan = fixture.plan(execution_profile="model-free-check")
    with pytest.raises(ExecutionScopeError):
        FrozenCoreAdapter(
            gate=fixture.gate(),
            plan=plan,
            arm="bare-core",
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", "SAEA-E-000-x"),
        )
