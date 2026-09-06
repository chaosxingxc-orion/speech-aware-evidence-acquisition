"""Contract: the adapter is inseparable from the real gate (fail-closed end to end)."""

import json

import pytest

from gate_fixture import GateFixture

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError, GateClosed
from speech_aware_evidence_acquisition.core.roster import (
    RosterItem,
    freeze_roster,
    write_roster,
)
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


@pytest.mark.requires_wsl2_execution_authority
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


@pytest.mark.requires_wsl2_execution_authority
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


# ---------------------------------------------------------------------------
# The construction-proposer arm (E2.4): gold crosses only on a construction
# roster, and the gate proves it from the committed receipt, not from a claim.
# ---------------------------------------------------------------------------

PROPOSER_ARM = "construction-proposer-text"


def _land_construction_roster(
    fixture: GateFixture, sample_id: str, *, roster_role: str = "construction"
) -> str:
    """Write one roster receipt of ``fixture``'s carrier under the gate's own
    source root and return its split identity hash."""

    receipt = freeze_roster(
        carrier_lock_key=fixture.CARRIER,
        candidates=[RosterItem(sample_id=sample_id, stratum="only")],
        per_stratum=1,
        seed=5,
        split_role="discovery",
        roster_id=f"TEST-{roster_role.upper()}-ROSTER",
        roster_role=roster_role,
    )
    write_roster(
        receipt,
        fixture.source_root / "docs" / "receipts" / "rosters" / f"{roster_role}.json",
    )
    return str(receipt["split_identity_hash"])


def _proposer_plan(fixture: GateFixture, identity_hash: str):
    fixture.write_ledger_rows(
        f"| 2026-09-05 | {fixture.RUN_ID} | bounded-discovery-probe | proposer "
        f"| qwen3-omni | {fixture.CARRIER} construction | discovery | {identity_hash} "
        "| no | 10 | 600 | 1.0 | construction roster only | receipts | pre-registered |\n"
    )
    return fixture.plan(
        execution_profile="bounded-discovery-probe",
        split_role="discovery",
        split_identity_hash=identity_hash,
    )


@pytest.mark.requires_wsl2_execution_authority
def test_the_proposer_arm_opens_on_a_construction_role_identity(tmp_path):
    fixture = GateFixture(tmp_path)
    identity_hash = _land_construction_roster(fixture, "4000001")
    plan = _proposer_plan(fixture, identity_hash)
    adapter = FrozenCoreAdapter(
        gate=fixture.gate(),
        plan=plan,
        arm=PROPOSER_ARM,
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id),
        binding=_binding(fixture),
    )
    assert adapter.cost_summary()["calls_used"] == 0


@pytest.mark.requires_wsl2_execution_authority
def test_the_proposer_arm_is_refused_on_an_evaluation_role_identity(tmp_path):
    """The same roster, the same samples, the same hash -- only the role
    differs, and the gold-visible arm is refused."""

    fixture = GateFixture(tmp_path)
    identity_hash = _land_construction_roster(
        fixture, "4000001", roster_role="evaluation"
    )
    plan = _proposer_plan(fixture, identity_hash)
    with pytest.raises(GateClosed, match="roster_role='construction'"):
        FrozenCoreAdapter(
            gate=fixture.gate(),
            plan=plan,
            arm=PROPOSER_ARM,
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", plan.run_id),
            binding=_binding(fixture),
        )


@pytest.mark.requires_wsl2_execution_authority
def test_the_proposer_arm_is_refused_when_no_roster_is_committed(tmp_path):
    fixture = GateFixture(tmp_path)
    plan = _proposer_plan(fixture, "c" * 64)
    with pytest.raises(GateClosed, match="none committed"):
        FrozenCoreAdapter(
            gate=fixture.gate(),
            plan=plan,
            arm=PROPOSER_ARM,
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", plan.run_id),
            binding=_binding(fixture),
        )


@pytest.mark.requires_wsl2_execution_authority
def test_an_ordinary_arm_is_unaffected_by_the_construction_check(tmp_path):
    """The whole check is arm-scoped: an ordinary arm on the very identity
    hash the proposer arm was refused for still opens the gate."""

    fixture = GateFixture(tmp_path)
    identity_hash = _land_construction_roster(
        fixture, "4000001", roster_role="evaluation"
    )
    plan = _proposer_plan(fixture, identity_hash)
    adapter = FrozenCoreAdapter(
        gate=fixture.gate(),
        plan=plan,
        arm="bare-core",
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id),
        binding=_binding(fixture),
    )
    assert adapter.cost_summary()["calls_used"] == 0


@pytest.mark.requires_wsl2_execution_authority
def test_a_gate_that_cannot_receive_the_arm_refuses_the_gold_visible_arm(tmp_path):
    """A duck-typed gate whose ``assert_model_touch_allowed`` has no ``arm``
    parameter cannot perform the construction-roster check, so the one arm
    that would show gold is refused outright rather than silently ungated."""

    class _ArmBlindGate:
        def assert_model_touch_allowed(self, plan, *, full_hash=None, diagnostics=None):
            return None

    fixture = GateFixture(tmp_path)
    plan = fixture.plan()
    with pytest.raises(Exception, match="cannot receive the arm"):
        FrozenCoreAdapter(
            gate=_ArmBlindGate(),
            plan=plan,
            arm=PROPOSER_ARM,
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", plan.run_id),
            binding=_binding(fixture),
        )
