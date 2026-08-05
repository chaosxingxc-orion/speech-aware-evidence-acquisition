"""Contract: the adapter is inseparable from the real gate (fail-closed end to end)."""

import json

import pytest

from gate_fixture import GateFixture

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError, GateClosed
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter
from speech_aware_evidence_acquisition.core.tracing import TraceSink


def _fake_transport(request_bytes):
    return json.dumps({"text": "ok", "usage": {}}).encode()


def _binding(fixture: GateFixture, sample_id: str = "4000001") -> PayloadBindingContext:
    """A minimal real binding context matching ``fixture``'s carrier: one
    verified sample id with a real media file materialized under the
    fixture's own data root (the driver builds this from a T1 VerifiedSplit
    plus the carrier loader's SampleRef facts)."""

    carrier_root = fixture.data_root / "datasets" / "earnings21-22" / "earnings21"
    media = carrier_root / "media" / f"{sample_id}.mp3"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    return PayloadBindingContext(
        carrier_lock_key=fixture.CARRIER,
        allowed_sample_ids=frozenset({sample_id}),
        sample_facts={sample_id: (100.0, 16000)},
        data_root=fixture.data_root,
        carrier_root=carrier_root,
    )


def test_adapter_construction_passes_through_a_real_open_gate(tmp_path):
    fixture = GateFixture(tmp_path)
    plan = fixture.plan()
    adapter = FrozenCoreAdapter(
        gate=fixture.gate(),
        plan=plan,
        arm="bare-core",
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id),
        binding=_binding(fixture),
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
            binding=_binding(fixture),
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
            binding=_binding(fixture),
        )
