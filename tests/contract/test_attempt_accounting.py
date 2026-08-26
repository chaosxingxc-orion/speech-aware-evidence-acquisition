"""Contract: one-time attempt accounting (R0 repair T4, invariant I6, campaign probe P4).

Independently reproduced defect (see task-4 brief): the frozen-core entry gate had
no nonce, attempt id or state machine. The identical ExecutionPlan, over the
identical pre-registered exposure-ledger row, opened the gate twice with no error,
and two independent FrozenCoreAdapter instances each metered their own in-process
counters from zero -- a row registered for N calls could be re-spent per
process/attempt indefinitely.

These probes exercise the fix through the REAL FrozenCoreGate (GateFixture) and
the real FrozenCoreAdapter, end to end -- not a stub gate (see
tests/unit/test_frozen_core_adapter.py and tests/unit/test_attempts.py for the
lower-level, gate-independent coverage of the same behaviors).
"""

import json

import pytest

from gate_fixture import GateFixture

from speech_aware_evidence_acquisition.contracts import ExecutionScopeError, GateClosed
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, FrozenCoreError
from speech_aware_evidence_acquisition.core.tracing import TraceSink


def _fake_transport(request_bytes):
    return json.dumps(
        {"text": "ok", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    ).encode()


def _binding(fixture: GateFixture, sample_id: str = "4000001") -> PayloadBindingContext:
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


def _payload(sample_id="4000001", audio_seconds=100.0, request_id="req-1"):
    return {
        "request_id": request_id,
        "carrier_lock_key": "earnings21-original",
        "sample_id": sample_id,
        "speech_ref": f"earnings21-original/{sample_id}",
        "media_relpath": f"datasets/earnings21-22/earnings21/media/{sample_id}.mp3",
        "audio_seconds": audio_seconds,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }


@pytest.fixture()
def world(tmp_path):
    return GateFixture(tmp_path)


@pytest.mark.requires_wsl2_execution_authority
def test_p4_same_run_and_attempt_id_opened_twice_second_refused(tmp_path, world):
    """Campaign probe P4, real gate: the identical (run_id, attempt_id) — here
    literally the same ExecutionPlan — must never open a second live adapter."""

    plan = world.plan(attempt_id="attempt-A")
    binding = _binding(world)
    adapter1 = FrozenCoreAdapter(
        gate=world.gate(),
        plan=plan,
        arm="bare-core",
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan.run_id),
        binding=binding,
    )
    assert adapter1.cost_summary()["calls_used"] == 0
    with pytest.raises(FrozenCoreError, match="attempt"):
        FrozenCoreAdapter(
            gate=world.gate(),
            plan=plan,
            arm="bare-core",
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run2", plan.run_id),
            binding=binding,
        )


@pytest.mark.requires_wsl2_execution_authority
def test_second_adapter_over_the_same_attempt_is_refused_not_resumed(tmp_path, world):
    """The stricter design choice (see task-4 report): after the first adapter
    has already spent budget, a second live adapter over the identical attempt
    is still refused outright -- it never silently resumes/attaches to the
    first adapter's in-flight, persisted usage."""

    plan = world.plan(attempt_id="attempt-B")
    binding = _binding(world)
    adapter1 = FrozenCoreAdapter(
        gate=world.gate(), plan=plan, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="req-1"))
    assert adapter1.cost_summary()["calls_used"] == 1

    with pytest.raises(FrozenCoreError, match="attempt"):
        FrozenCoreAdapter(
            gate=world.gate(), plan=plan, arm="bare-core", transport=_fake_transport,
            sink=TraceSink(tmp_path / "run2", plan.run_id), binding=binding,
        )

    # The refused second construction never touched the first attempt's
    # already-persisted usage.
    store = AttemptStore(world.data_root / "attempts")
    assert store.prior_actual_usage(plan.run_id) == (1, 100.0)


@pytest.mark.requires_wsl2_execution_authority
def test_plan_without_attempt_id_is_refused(tmp_path, world):
    plan = world.plan(attempt_id=None)
    with pytest.raises(FrozenCoreError, match="attempt_id"):
        FrozenCoreAdapter(
            gate=world.gate(), plan=plan, arm="bare-core", transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", plan.run_id), binding=_binding(world),
        )


@pytest.mark.parametrize("bad_attempt_id", ["", "has space", "has/slash", "../escape"])
def test_plan_with_malformed_attempt_id_is_refused(tmp_path, world, bad_attempt_id):
    """IMPORTANT 3 fix-wave3 (round-3 external-threat-model review):
    ``ExecutionPlan.validate()`` now refuses a malformed attempt_id itself
    (a structural identity-contract violation, ``ExecutionScopeError``) --
    strictly EARLIER than the previous refusal point deep inside
    ``FrozenCoreAdapter``'s own ``AttemptStore.open_attempt`` call
    (``AttemptError`` translated to ``FrozenCoreError``). ``gate.
    assert_model_touch_allowed(plan)`` is the FIRST thing
    ``FrozenCoreAdapter.__init__`` does, and it calls ``ExecutionPlan.
    validate(plan)`` before touching any receipt, so the malformed id is now
    caught before ANY gate/attempt-store work happens at all."""

    plan = world.plan(attempt_id=bad_attempt_id)
    with pytest.raises(ExecutionScopeError, match="attempt_id"):
        FrozenCoreAdapter(
            gate=world.gate(), plan=plan, arm="bare-core", transport=_fake_transport,
            sink=TraceSink(tmp_path / "run", plan.run_id), binding=_binding(world),
        )


@pytest.mark.requires_wsl2_execution_authority
def test_crashed_attempt_actuals_count_toward_a_new_attempts_row_budget(tmp_path, world):
    """A crashed attempt (state stuck OPENED, never finalized -- finalization is
    T6, out of scope for this task) still counts against the row's registered
    budget when a fresh attempt opens on the same run_id, and the fresh attempt
    is refused exactly at the request that would cross the row's total."""

    binding = _binding(world)
    plan1 = world.plan(attempt_id="attempt-1", planned_model_calls=2, planned_speech_audio_seconds=250)
    adapter1 = FrozenCoreAdapter(
        gate=world.gate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="req-1"))
    # adapter1 "crashes" here: never finalized, its file stays state OPENED.

    plan2 = world.plan(attempt_id="attempt-2", planned_model_calls=2, planned_speech_audio_seconds=250)
    adapter2 = FrozenCoreAdapter(
        gate=world.gate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    # 1 of the row's 2 calls was already spent by the crashed attempt; the
    # retry gets exactly the remaining 1, then is refused at the crossing request.
    adapter2.request(_payload(request_id="req-1"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter2.request(_payload(request_id="req-2"))

    store = AttemptStore(world.data_root / "attempts")
    assert store.prior_actual_usage(plan1.run_id) == (2, 200.0)


@pytest.mark.requires_wsl2_execution_authority
def test_two_overlapping_adapters_over_the_real_gate_cannot_together_exceed_the_plan_budget(
    tmp_path, world
):
    """I3, real gate: the same overlapping-construction race as
    tests/unit/test_frozen_core_adapter.py, but through the REAL
    FrozenCoreGate. Both adapters are constructed (each independently opens
    the gate, re-reading the ledger and receipts) before either records any
    usage, then their requests interleave."""

    binding = _binding(world)
    plan1 = world.plan(attempt_id="attempt-1", planned_model_calls=2, planned_speech_audio_seconds=500)
    plan2 = world.plan(attempt_id="attempt-2", planned_model_calls=2, planned_speech_audio_seconds=500)
    adapter1 = FrozenCoreAdapter(
        gate=world.gate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter2 = FrozenCoreAdapter(
        gate=world.gate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="a-1"))
    adapter2.request(_payload(request_id="b-1"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter1.request(_payload(request_id="a-2"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter2.request(_payload(request_id="b-2"))

    store = AttemptStore(world.data_root / "attempts")
    # I3: durable per-attempt usage accounting must stay race-safe regardless
    # of any slice-wide consumer -- AttemptStore.all_actual_usage() (a general
    # cross-run accounting utility; no longer read by a slice-wide budget-cap
    # check, which the 2026-08-06 owner amendment retired) must still report
    # the total correctly bounded to what the shared plan actually allowed
    # (2), not inflated to 4 by the race.
    actual_calls, _, _ = store.all_actual_usage()
    assert actual_calls == 2, "the race must never let the actual-usage total double-count"
