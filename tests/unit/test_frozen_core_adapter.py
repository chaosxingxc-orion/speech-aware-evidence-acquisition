"""Adapter choke point: allowlist exact-set, boundary, budgets, tracing,
payload<->plan<->split value binding (I3) and media confinement (I4)."""

import hashlib
import json
import os
import subprocess
import threading
import time

import pytest

from speech_aware_evidence_acquisition.contracts import (
    BoundaryViolation,
    ExecutionPlan,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
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
        attempt_id="attempt-0001",
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


def _binding(
    tmp_path,
    *,
    carrier_lock_key="earnings22-original",
    sample_id="5000001",
    audio_seconds=100.0,
    sample_rate_hz=16000,
    media_relpath="datasets/earnings21-22/earnings22/media/5000001.mp3",
):
    """A minimal real binding context: one verified sample id + loader fact,
    with a real media file materialized under a real data root so the
    adapter's confinement check (which resolves(strict=True)) has real bytes
    to resolve — exactly what the driver builds from a VerifiedSplit plus the
    carrier loader's SampleRef list."""

    data_root = tmp_path / "data"
    media = data_root / media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    carrier_root = data_root / "datasets" / "earnings21-22" / "earnings22"
    return PayloadBindingContext(
        carrier_lock_key=carrier_lock_key,
        allowed_sample_ids=frozenset({sample_id}),
        sample_facts={sample_id: (audio_seconds, sample_rate_hz)},
        data_root=data_root,
        carrier_root=carrier_root,
    )


def _adapter(tmp_path, gate=None, plan=None, arm="bare-core", binding=None):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-adapter")
    return FrozenCoreAdapter(
        gate=gate or _OpenGate(),
        plan=plan or _plan(),
        arm=arm,
        transport=_fake_transport,
        sink=sink,
        binding=binding or _binding(tmp_path),
    ), sink


def test_gate_is_checked_at_construction(tmp_path):
    gate = _OpenGate()
    _adapter(tmp_path, gate=gate)
    assert len(gate.checked_plans) == 1


# ---------------------------------------------------------------------------
# M-3 (external-threat-model review): the umbrella lock hash the gate returns
# from assert_model_touch_allowed is carried into cost_summary().
# ---------------------------------------------------------------------------


def test_cost_summary_reports_no_lock_hash_when_the_gate_returns_none(tmp_path):
    """`_OpenGate` (used throughout this file) returns None implicitly -- a
    test double isolating unrelated adapter behavior should not be forced to
    fabricate a hash; the field is simply absent (None), not a crash."""

    adapter, _ = _adapter(tmp_path)
    assert adapter.cost_summary()["umbrella_lock_sha256"] is None


def test_cost_summary_carries_the_gates_returned_lock_hash(tmp_path):
    class _GateReturningLockHash:
        def assert_model_touch_allowed(self, plan):
            return "f" * 64

    adapter, _ = _adapter(tmp_path, gate=_GateReturningLockHash())
    assert adapter.cost_summary()["umbrella_lock_sha256"] == "f" * 64


# ---------------------------------------------------------------------------
# I-4 (external-threat-model review): the adapter asks the gate to re-verify
# THIS run's media (via binding.media_relpaths) against D1's frozen facts,
# duck-typed like the session_check below so unrelated test doubles that
# don't implement `verify_media_identity` are unaffected.
# ---------------------------------------------------------------------------


class _MediaCheckingGate:
    def __init__(self):
        self.checked = []

    def assert_model_touch_allowed(self, plan):
        return None

    def verify_media_identity(self, carrier_lock_key, media_facts):
        self.checked.append((carrier_lock_key, dict(media_facts)))


def _binding_with_media(tmp_path, **overrides):
    binding = _binding(tmp_path, **overrides)
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext

    return PayloadBindingContext(
        carrier_lock_key=binding.carrier_lock_key,
        allowed_sample_ids=binding.allowed_sample_ids,
        sample_facts=binding.sample_facts,
        data_root=binding.data_root,
        carrier_root=binding.carrier_root,
        media_relpaths={
            sample_id: "datasets/earnings21-22/earnings22/media/5000001.mp3"
            for sample_id in binding.allowed_sample_ids
        },
    )


def test_adapter_calls_verify_media_identity_when_the_gate_and_binding_support_it(tmp_path):
    gate = _MediaCheckingGate()
    binding = _binding_with_media(tmp_path)
    _adapter(tmp_path, gate=gate, binding=binding)
    assert len(gate.checked) == 1
    carrier_lock_key, media_facts = gate.checked[0]
    assert carrier_lock_key == binding.carrier_lock_key
    assert media_facts == {
        "5000001": ("datasets/earnings21-22/earnings22/media/5000001.mp3", 100.0)
    }


def test_adapter_skips_media_identity_check_when_binding_carries_no_media_relpaths(tmp_path):
    """A binding built without media_relpaths (the default, empty mapping --
    e.g. every OTHER pre-existing test in this file) never invokes the check,
    even against a gate that implements it."""

    gate = _MediaCheckingGate()
    _adapter(tmp_path, gate=gate, binding=_binding(tmp_path))
    assert gate.checked == []


def test_adapter_construction_propagates_a_media_identity_refusal(tmp_path):
    from speech_aware_evidence_acquisition.contracts import GateClosed

    class _RefusingMediaGate:
        def assert_model_touch_allowed(self, plan):
            return None

        def verify_media_identity(self, carrier_lock_key, media_facts):
            raise GateClosed("media identity drift (test)")

    binding = _binding_with_media(tmp_path)
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-mediarefuse")
    with pytest.raises(GateClosed, match="media identity drift"):
        FrozenCoreAdapter(
            gate=_RefusingMediaGate(),
            plan=_plan(run_id="SAEA-E-000-mediarefuse", attempt_id="attempt-mediarefuse"),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=binding,
        )


# ---------------------------------------------------------------------------
# IMPORTANT 1 (external-threat-model review round 4): the evidence-layer
# counterpart to I-4 above -- the adapter asks the gate to re-verify THIS
# run's evidence (via binding.evidence_relpaths) against D1's frozen
# evidence-layer facts, duck-typed exactly the same way.
# ---------------------------------------------------------------------------


class _EvidenceCheckingGate:
    def __init__(self):
        self.checked = []

    def assert_model_touch_allowed(self, plan):
        return None

    def verify_evidence_identity(self, carrier_lock_key, evidence_facts):
        self.checked.append((carrier_lock_key, dict(evidence_facts)))


def _binding_with_evidence(tmp_path, **overrides):
    binding = _binding(tmp_path, **overrides)
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext

    return PayloadBindingContext(
        carrier_lock_key=binding.carrier_lock_key,
        allowed_sample_ids=binding.allowed_sample_ids,
        sample_facts=binding.sample_facts,
        data_root=binding.data_root,
        carrier_root=binding.carrier_root,
        evidence_relpaths={
            sample_id: f"datasets/conec/earnings21/contexts/{sample_id}.txt"
            for sample_id in binding.allowed_sample_ids
        },
    )


def test_adapter_calls_verify_evidence_identity_when_the_gate_and_binding_support_it(tmp_path):
    gate = _EvidenceCheckingGate()
    binding = _binding_with_evidence(tmp_path)
    _adapter(tmp_path, gate=gate, binding=binding)
    assert len(gate.checked) == 1
    carrier_lock_key, evidence_facts = gate.checked[0]
    assert carrier_lock_key == binding.carrier_lock_key
    assert evidence_facts == {"5000001": "datasets/conec/earnings21/contexts/5000001.txt"}


def test_adapter_skips_evidence_identity_check_when_binding_carries_no_evidence_relpaths(tmp_path):
    """A binding built without evidence_relpaths (the default, empty mapping
    -- e.g. every OTHER pre-existing test in this file, or a run whose
    evidence_source is "none") never invokes the check, even against a gate
    that implements it."""

    gate = _EvidenceCheckingGate()
    _adapter(tmp_path, gate=gate, binding=_binding(tmp_path))
    assert gate.checked == []


def test_adapter_construction_propagates_an_evidence_identity_refusal(tmp_path):
    from speech_aware_evidence_acquisition.contracts import GateClosed

    class _RefusingEvidenceGate:
        def assert_model_touch_allowed(self, plan):
            return None

        def verify_evidence_identity(self, carrier_lock_key, evidence_facts):
            raise GateClosed("evidence identity drift (test)")

    binding = _binding_with_evidence(tmp_path)
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-evidencerefuse")
    with pytest.raises(GateClosed, match="evidence identity drift"):
        FrozenCoreAdapter(
            gate=_RefusingEvidenceGate(),
            plan=_plan(run_id="SAEA-E-000-evidencerefuse", attempt_id="attempt-evidencerefuse"),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=binding,
        )


# ---------------------------------------------------------------------------
# IMPROVEMENT (fifth external-threat-model review): the content-identity
# counterpart to the two evidence tests above -- the adapter also asks the
# gate to re-verify THIS run's evidence via binding.evidence_contents (the
# bytes already read into memory), duck-typed exactly the same way.
# ---------------------------------------------------------------------------


class _EvidenceContentCheckingGate:
    def __init__(self):
        self.checked = []

    def assert_model_touch_allowed(self, plan):
        return None

    def verify_evidence_content_identity(self, carrier_lock_key, evidence_contents, evidence_relpaths):
        self.checked.append(
            (carrier_lock_key, dict(evidence_contents), dict(evidence_relpaths))
        )


def _binding_with_evidence_content(tmp_path, *, content=b"ctx", **overrides):
    binding = _binding(tmp_path, **overrides)
    from speech_aware_evidence_acquisition.core.base import PayloadBindingContext

    return PayloadBindingContext(
        carrier_lock_key=binding.carrier_lock_key,
        allowed_sample_ids=binding.allowed_sample_ids,
        sample_facts=binding.sample_facts,
        data_root=binding.data_root,
        carrier_root=binding.carrier_root,
        evidence_relpaths={
            sample_id: f"datasets/conec/earnings21/contexts/{sample_id}.txt"
            for sample_id in binding.allowed_sample_ids
        },
        evidence_contents={sample_id: content for sample_id in binding.allowed_sample_ids},
    )


def test_adapter_calls_verify_evidence_content_identity_when_the_gate_and_binding_support_it(
    tmp_path,
):
    gate = _EvidenceContentCheckingGate()
    binding = _binding_with_evidence_content(tmp_path)
    _adapter(tmp_path, gate=gate, binding=binding)
    assert len(gate.checked) == 1
    carrier_lock_key, evidence_contents, evidence_relpaths = gate.checked[0]
    assert carrier_lock_key == binding.carrier_lock_key
    assert evidence_contents == {"5000001": b"ctx"}
    # conec-names follow-up (2026-08-13): threaded from the SAME
    # binding.evidence_relpaths the file-identity check itself uses.
    assert evidence_relpaths == dict(binding.evidence_relpaths)


def test_adapter_skips_evidence_content_identity_check_when_binding_carries_none(tmp_path):
    gate = _EvidenceContentCheckingGate()
    _adapter(tmp_path, gate=gate, binding=_binding(tmp_path))
    assert gate.checked == []


def test_adapter_refuses_construction_when_content_read_was_tampered_even_though_the_file_check_would_pass(
    tmp_path,
):
    """The exact PROBE the review demonstrated, at the adapter/construction
    level: a gate whose FILE rail (verify_evidence_identity) always passes --
    modelling a file that was tampered, read, then RESTORED to pristine
    bytes before the gate ever runs -- but whose CONTENT rail
    (verify_evidence_content_identity) sees the tampered bytes actually read
    and refuses. Construction must still refuse overall: the content check is
    not bypassed just because the file check independently succeeded."""

    from speech_aware_evidence_acquisition.contracts import GateClosed

    class _FilePassesContentRefusesGate:
        def assert_model_touch_allowed(self, plan):
            return None

        def verify_evidence_identity(self, carrier_lock_key, evidence_facts):
            return None  # the restored, pristine file matches D1 -- passes

        def verify_evidence_content_identity(self, carrier_lock_key, evidence_contents, evidence_relpaths):
            raise GateClosed("evidence content identity drift (test)")

    binding = _binding_with_evidence_content(tmp_path, content=b"tampered-content-read-earlier")
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-contentrefuse")
    with pytest.raises(GateClosed, match="evidence content identity drift"):
        FrozenCoreAdapter(
            gate=_FilePassesContentRefusesGate(),
            plan=_plan(run_id="SAEA-E-000-contentrefuse", attempt_id="attempt-contentrefuse"),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=binding,
        )


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


def test_decoding_params_response_format_mapping_admitted(tmp_path):
    adapter, _ = _adapter(tmp_path)
    response = adapter.request(
        _payload(
            decoding_params={
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "schema": {
                            "type": "object",
                            "properties": {"key_id": {"const": "K001"}},
                            "required": ["key_id"],
                            "additionalProperties": False,
                        }
                    },
                },
            }
        )
    )
    assert response.text == "hello world"


def test_decoding_params_response_format_non_mapping_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="response_format"):
        adapter.request(
            _payload(decoding_params={"temperature": 0, "response_format": "json"})
        )


def test_decoding_params_id_slot_integer_admitted(tmp_path):
    """Slot affinity (2026-08-11): an executor-resolved integer id_slot is a
    legal decoding key — the request goes through the choke point."""

    adapter, _ = _adapter(tmp_path)
    response = adapter.request(
        _payload(decoding_params={"temperature": 0, "id_slot": 2})
    )
    assert response.text


def test_decoding_params_id_slot_unresolved_sentinel_refused(tmp_path):
    """The config-level sentinel 'per-sample' must be resolved to an integer
    by the batch executor BEFORE the adapter; an unresolved sentinel (or any
    non-integer/negative value) is refused at the choke point rather than
    reaching llama-server as a malformed field."""

    adapter, _ = _adapter(tmp_path)
    for bad in ("per-sample", -1, 1.5, True):
        with pytest.raises(FrozenCoreError, match="id_slot"):
            adapter.request(
                _payload(decoding_params={"temperature": 0, "id_slot": bad})
            )


def test_decoding_params_max_tokens_integer_admitted(tmp_path):
    """The ordinary case, unchanged: a plain positive integer cap goes through
    the choke point exactly as it always has."""

    adapter, _ = _adapter(tmp_path)
    response = adapter.request(
        _payload(decoding_params={"temperature": 0, "max_tokens": 1024})
    )
    assert response.text


def test_decoding_params_max_tokens_unresolved_rule_refused(tmp_path):
    """E22 cell (b), 2026-09-06: a fragment may declare
    ``decoding_params.max_tokens`` as a PER-SAMPLE rule object which
    ``core.flight.FlightRuntime`` resolves to an integer from the sample's own
    ``audio_seconds``. An executor that did not resolve it must be refused at
    this choke point rather than sending a JSON object to llama-server as a
    generation cap -- the same discipline the unresolved ``id_slot`` sentinel
    above already gets."""

    adapter, _ = _adapter(tmp_path)
    unresolved = {
        "policy": "duration-proportional-v1",
        "alpha": 1.5,
        "words_per_second_p95": 4.999220954734555,
        "tokens_per_word": 1.2991996296395218,
        "floor": 1,
        "ceiling": 1024,
    }
    for bad in (unresolved, "1024", 1024.0, 0, -1, True):
        with pytest.raises(FrozenCoreError, match="max_tokens"):
            adapter.request(
                _payload(decoding_params={"temperature": 0, "max_tokens": bad})
            )


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
        binding=_binding(tmp_path),
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        adapter.request(_payload())
    assert len(calls) == 1
    summary = adapter.cost_summary()
    assert summary["calls_used"] == 1
    assert summary["audio_seconds_used"] == 100.0


# ---------------------------------------------------------------------------
# Binding-context construction discipline: no default, structurally checked.
# ---------------------------------------------------------------------------


def test_adapter_construction_without_binding_context_refuses(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-nobind")
    with pytest.raises(TypeError):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
        )


def test_adapter_construction_with_wrong_type_binding_refuses(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-badbind")
    with pytest.raises(FrozenCoreError):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding={"not": "a binding context"},
        )


def test_adapter_construction_with_malformed_binding_refuses(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-malformedbind")
    binding = _binding(tmp_path)
    # Drop the only sample fact -> sample_facts no longer covers allowed_sample_ids.
    tampered = PayloadBindingContext(
        carrier_lock_key=binding.carrier_lock_key,
        allowed_sample_ids=binding.allowed_sample_ids,
        sample_facts={},
        data_root=binding.data_root,
        carrier_root=binding.carrier_root,
    )
    with pytest.raises(FrozenCoreError):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=tampered,
        )


def test_adapter_construction_refuses_binding_carrier_mismatched_with_plan(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-carriermismatch")
    binding = _binding(tmp_path, carrier_lock_key="earnings21-original")
    with pytest.raises(FrozenCoreError, match="carrier"):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(carrier_lock_key="earnings22-original"),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=binding,
        )


# ---------------------------------------------------------------------------
# I3: payload<->plan<->split value binding.
# ---------------------------------------------------------------------------


def test_payload_carrier_mismatched_with_plan_carrier_refused(tmp_path):
    """Campaign probe P5: an earnings22 plan must refuse a payload whose
    carrier_lock_key names a different carrier (the independently reproduced
    defect used ``fsd50k``)."""

    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="carrier_lock_key"):
        adapter.request(
            _payload(carrier_lock_key="fsd50k", speech_ref="fsd50k/5000001")
        )


def test_payload_sample_id_not_in_verified_split_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="sample_id"):
        adapter.request(
            _payload(sample_id="9999999", speech_ref="earnings22-original/9999999")
        )


def test_payload_speech_ref_wrong_prefix_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="speech_ref"):
        adapter.request(_payload(speech_ref="conec/5000001"))


def test_payload_speech_ref_mismatched_pair_refused(tmp_path):
    """Right sample id, but speech_ref names a different sample: mismatched pair."""

    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="speech_ref"):
        adapter.request(_payload(speech_ref="earnings22-original/5000002"))


def test_payload_audio_seconds_disagrees_with_loader_fact_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="audio_seconds"):
        adapter.request(_payload(audio_seconds=999.0))


def test_payload_sample_rate_hz_disagrees_with_loader_fact_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="sample_rate_hz"):
        adapter.request(_payload(sample_rate_hz=8000))


# ---------------------------------------------------------------------------
# I4: media confinement.
# ---------------------------------------------------------------------------


def test_absolute_media_relpath_refused_at_adapter(tmp_path):
    """Campaign probe P3, adapter rail."""

    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(_payload(media_relpath="/etc/passwd"))


def test_drive_letter_media_relpath_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(_payload(media_relpath="C:/secret.txt"))


def test_backslash_media_relpath_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets\\earnings21-22\\earnings22\\media\\5000001.mp3")
        )


def test_traversal_media_relpath_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(_payload(media_relpath="../../../etc/passwd"))


def test_media_relpath_outside_carrier_root_refused_even_without_traversal_syntax(tmp_path):
    """A syntactically clean relative path that simply names a different
    carrier's media tree (no ``..``, no absolute prefix) must still be refused:
    it resolves outside this run's carrier_root."""

    binding = _binding(tmp_path)
    # Materialize a sibling carrier directory with a real file, so resolution
    # succeeds but lands outside carrier_root.
    other = binding.data_root / "datasets" / "earnings21-22" / "earnings21" / "media"
    other.mkdir(parents=True)
    (other / "4000001.mp3").write_bytes(b"other-carrier-audio")
    adapter, _ = _adapter(tmp_path, binding=binding)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings21/media/4000001.mp3")
        )


# ---------------------------------------------------------------------------
# IMPORTANT A (round-2 external-threat-model review): confinement under the
# carrier root is necessary but was never sufficient. The gate re-hashes
# ONLY the media_relpath the BINDING names (binding.media_relpaths); before
# this fix, the payload's own media_relpath was checked only for
# confinement, never compared to that binding value -- so a payload could
# name any OTHER file confined under the same carrier root (a "decoy") and
# it sailed straight through, while the gate's D1 re-hash (and the metered
# audio_seconds) stayed keyed to the BOUND sample's real facts, not the
# decoy actually sent.
# ---------------------------------------------------------------------------


def test_decoy_media_relpath_confined_under_the_same_carrier_root_is_refused(tmp_path):
    """The exact demonstrated defect: a decoy file that is fully confinement-
    legal (lives under the same carrier_root as the bound sample's real
    media) but is NOT the file the verified binding names for this
    sample_id must still be refused."""

    binding = _binding_with_media(tmp_path)
    decoy = binding.data_root / "datasets" / "earnings21-22" / "earnings22" / "media" / "decoy.mp3"
    decoy.write_bytes(b"decoy-mp3-bytes-a-completely-different-file")
    adapter, _ = _adapter(tmp_path, binding=binding)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings22/media/decoy.mp3")
        )


def test_the_legitimate_bound_media_relpath_is_still_accepted(tmp_path):
    """Positive control: the EXACT media_relpath the binding names for this
    sample_id is accepted (not merely "some confined path")."""

    binding = _binding_with_media(tmp_path)
    adapter, _ = _adapter(tmp_path, binding=binding, plan=_plan(planned_model_calls=3))
    response = adapter.request(_payload())
    assert response.text == "hello world"


def test_multiple_requests_for_one_sample_with_the_correct_media_relpath_still_work(tmp_path):
    """A policy that sends several requests for the same sample (e.g. a
    retry) must keep working once the exact-match binding is enforced --
    the fix must not accidentally make the correct path a one-shot value."""

    binding = _binding_with_media(tmp_path)
    adapter, _ = _adapter(tmp_path, binding=binding, plan=_plan(planned_model_calls=3))
    adapter.request(_payload(request_id="req-1"))
    adapter.request(_payload(request_id="req-2"))
    assert adapter.cost_summary()["calls_used"] == 2


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink required")
def test_media_relpath_symlink_escape_from_carrier_root_refused(tmp_path):
    """Campaign probe: symlink inside the data root pointing outside must be
    refused even though the resolved leaf file genuinely exists."""

    data_root = tmp_path / "data"
    carrier_root = data_root / "datasets" / "earnings21-22" / "earnings22"
    carrier_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leaked.mp3").write_bytes(b"leaked-bytes")
    (carrier_root / "media_link").symlink_to(outside, target_is_directory=True)
    binding = PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=data_root,
        carrier_root=carrier_root,
    )
    adapter, _ = _adapter(tmp_path, binding=binding)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings22/media_link/leaked.mp3")
        )


def test_media_relpath_missing_file_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(
                media_relpath="datasets/earnings21-22/earnings22/media/absent.mp3"
            )
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows junction probe")
def test_media_relpath_windows_junction_escape_from_carrier_root_refused(tmp_path):
    """Windows-native equivalent of the POSIX symlink-escape probe above: a
    junction (``mklink /J``, no elevation required) is a reparse point
    ``Path.resolve()`` follows exactly like a symlink. If junction creation
    itself fails in this environment (e.g. permissions), the test skips with
    that reason rather than passing vacuously."""

    data_root = tmp_path / "data"
    carrier_root = data_root / "datasets" / "earnings21-22" / "earnings22"
    carrier_root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leaked.mp3").write_bytes(b"leaked-bytes")
    link = carrier_root / "media_link"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not link.exists():
        pytest.skip(
            "Windows junction creation failed in this environment "
            f"(rc={result.returncode}): {result.stderr or result.stdout}"
        )
    binding = PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=data_root,
        carrier_root=carrier_root,
    )
    adapter, _ = _adapter(tmp_path, binding=binding)
    with pytest.raises(FrozenCoreError, match="escapes"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings22/media_link/leaked.mp3")
        )


# ---------------------------------------------------------------------------
# I4 defense in depth: per-segment Windows-only looseness that is not itself
# an escape but would let a forged relpath silently land on a legitimate
# file (Windows strips trailing dots/spaces from a path component; a colon
# inside a segment is NTFS alternate-data-stream syntax).
# ---------------------------------------------------------------------------


def test_media_relpath_trailing_dot_segment_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings22/media/5000001.mp3.")
        )


def test_media_relpath_trailing_space_segment_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(media_relpath="datasets/earnings21-22/earnings22/media/5000001.mp3 ")
        )


def test_media_relpath_colon_in_segment_refused(tmp_path):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        adapter.request(
            _payload(
                media_relpath="datasets/earnings21-22/earnings22/media/5000001.mp3:hidden"
            )
        )


# ---------------------------------------------------------------------------
# R0 repair T4, invariant I6: one-time attempt accounting. The contract-level
# campaign probe (P4, real gate, two live adapters) lives in
# tests/contract/test_attempt_accounting.py; these unit tests isolate the
# same behaviors from real-gate/receipt overhead using the stub gate already
# used throughout this file.
# ---------------------------------------------------------------------------


def test_adapter_construction_opens_a_durable_attempt_file(tmp_path):
    adapter, _ = _adapter(tmp_path)
    store = AttemptStore(adapter._binding.data_root / "attempts")
    calls, audio = store.prior_actual_usage(adapter._plan.run_id)
    assert (calls, audio) == (0, 0.0)
    path = adapter._binding.data_root / "attempts" / "SAEA-E-000-adapter" / "attempt-0001.json"
    assert path.is_file()


def test_gate_check_runs_before_attempt_reservation(tmp_path):
    """R0 repair T6, carried T4-review minor: pins the ordering the
    conservative-ceiling slice-budget argument depends on -- the gate must be
    consulted BEFORE a durable attempt file is ever created, so a refused
    gate leaves no attempt behind to spend budget against later. Proved via
    the actual filesystem side effect (no attempt file), not merely by
    reading source order."""

    class _RefusingGate:
        def assert_model_touch_allowed(self, plan):
            raise RuntimeError("gate refused")

    plan = _plan(run_id="SAEA-E-000-gateorder", attempt_id="attempt-gateorder")
    sink = TraceSink(tmp_path / "run", plan.run_id)
    binding = _binding(tmp_path)
    with pytest.raises(RuntimeError, match="gate refused"):
        FrozenCoreAdapter(
            gate=_RefusingGate(),
            plan=plan,
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=binding,
        )
    attempt_path = binding.data_root / "attempts" / plan.run_id / "attempt-gateorder.json"
    assert not attempt_path.is_file(), (
        "a refused gate must never leave an attempt file behind -- the gate "
        "check must run before any attempt reservation"
    )
    store = AttemptStore(binding.data_root / "attempts")
    assert store.prior_actual_usage(plan.run_id) == (0, 0.0)


def test_plan_without_attempt_id_is_refused(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-noattempt")
    with pytest.raises(FrozenCoreError, match="attempt_id"):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(run_id="SAEA-E-000-noattempt", attempt_id=None),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=_binding(tmp_path),
        )


@pytest.mark.parametrize(
    "bad_attempt_id",
    ["", "   ", "has space", "has/slash", "../escape", ".leading-dot", 7, True],
)
def test_plan_with_malformed_attempt_id_is_refused(tmp_path, bad_attempt_id):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-badattempt")
    with pytest.raises(FrozenCoreError, match="attempt"):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(run_id="SAEA-E-000-badattempt", attempt_id=bad_attempt_id),
            arm="bare-core",
            transport=_fake_transport,
            sink=sink,
            binding=_binding(tmp_path),
        )


def test_second_adapter_over_the_identical_attempt_is_refused(tmp_path):
    """P4 at the adapter layer: the same (run_id, attempt_id) -- here carried by
    literally the same plan object -- must never open twice. This is the exact
    reproduced defect: two FrozenCoreAdapters over the same plan."""

    plan = _plan(run_id="SAEA-E-000-dup", attempt_id="attempt-dup")
    binding = _binding(tmp_path)
    FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm="bare-core",
        transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan.run_id),
        binding=binding,
    )
    with pytest.raises(FrozenCoreError, match="attempt"):
        FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=plan,
            arm="bare-core",
            transport=_fake_transport,
            sink=TraceSink(tmp_path / "run2", plan.run_id),
            binding=binding,
        )


def test_usage_is_persisted_before_transport_even_when_transport_raises(tmp_path):
    """Belt-and-suspenders with test_metering_counts_before_transport_even_when_
    transport_raises: this asserts the DURABLE file, not just the in-process
    counters, carries the spend a crash right after this point would lose from
    memory."""

    def _raising_transport(request_bytes):
        raise RuntimeError("transport exploded")

    plan = _plan(run_id="SAEA-E-000-crashmeter", attempt_id="attempt-crashmeter")
    binding = _binding(tmp_path)
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm="bare-core",
        transport=_raising_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id),
        binding=binding,
    )
    with pytest.raises(RuntimeError, match="transport exploded"):
        adapter.request(_payload())
    store = AttemptStore(binding.data_root / "attempts")
    calls, audio = store.prior_actual_usage(plan.run_id, exclude_attempt_id=None)
    assert (calls, audio) == (1, 100.0)


def test_crashed_attempts_actual_usage_counts_against_a_fresh_attempts_row_budget(tmp_path):
    """A crashed attempt (state stuck OPENED, never finalized -- finalization is
    T6, out of scope here) still counts: a fresh attempt on the same run_id must
    not get to spend the row's full budget again from zero."""

    binding = _binding(tmp_path)
    plan1 = _plan(
        run_id="SAEA-E-000-crashbudget",
        attempt_id="attempt-1",
        planned_model_calls=2,
        planned_speech_audio_seconds=250,
    )
    adapter1 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="req-1"))
    # adapter1 "crashes" here: never finalized, its state stays OPENED on disk.

    plan2 = _plan(
        run_id="SAEA-E-000-crashbudget",
        attempt_id="attempt-2",
        planned_model_calls=2,
        planned_speech_audio_seconds=250,
    )
    adapter2 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    # The crashed attempt already spent 1 of the row's 2 calls; the retry gets
    # exactly the remaining 1 call, then is refused at the request that would
    # cross the row's total budget.
    adapter2.request(_payload(request_id="req-1"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter2.request(_payload(request_id="req-2"))
    # The refused request must never have been persisted as spent.
    store = AttemptStore(binding.data_root / "attempts")
    calls, _ = store.prior_actual_usage(plan2.run_id)
    assert calls == 2


# ---------------------------------------------------------------------------
# R0 repair T7, invariant I8: tool_calls counter. Zero today (no registered
# policy is tool-using), but wired through the same choke point every other
# cost figure flows through -- ``cost_summary()`` -- so a future tool-using
# policy has a path to increment it without inventing a new one.
# ---------------------------------------------------------------------------


def test_cost_summary_reports_zero_tool_calls_by_default(tmp_path):
    adapter, _ = _adapter(tmp_path)
    assert adapter.cost_summary()["tool_calls"] == 0


def test_record_tool_call_increments_the_cost_summary_counter(tmp_path):
    adapter, _ = _adapter(tmp_path)
    adapter.record_tool_call()
    adapter.record_tool_call(count=2)
    assert adapter.cost_summary()["tool_calls"] == 3
    # Independent of, not entangled with, request-based metering.
    adapter.request(_payload())
    assert adapter.cost_summary()["tool_calls"] == 3
    assert adapter.cost_summary()["calls_used"] == 1


@pytest.mark.parametrize("bad_count", [0, -1, -5, "1", 1.5, True])
def test_record_tool_call_refuses_a_non_positive_or_non_integer_count(tmp_path, bad_count):
    adapter, _ = _adapter(tmp_path)
    with pytest.raises(FrozenCoreError, match="record_tool_call"):
        adapter.record_tool_call(bad_count)


# ---------------------------------------------------------------------------
# I3 (fresh-usage enforcement): the reproduced defect was `prior_actual_usage`
# read ONCE at __init__ and compared against for the adapter's entire
# lifetime. Two attempts on one run_id, BOTH constructed before either
# recorded any usage, each therefore saw "0 spent elsewhere" forever -- so
# together they could spend up to 2x the row's budget (demonstrated: 4 calls
# / 402 audio-seconds against a plan registering 2 calls). These probes
# construct both adapters FIRST (neither has recorded anything when the
# other is built) and then drive requests through them, proving the combined
# spend across both never exceeds the shared plan budget.
# ---------------------------------------------------------------------------


def test_two_overlapping_adapters_built_before_either_records_cannot_together_exceed_the_call_budget(
    tmp_path,
):
    binding = _binding(tmp_path)
    plan1 = _plan(
        run_id="SAEA-E-000-overlap-calls",
        attempt_id="attempt-1",
        planned_model_calls=2,
        planned_speech_audio_seconds=1000,
    )
    plan2 = _plan(
        run_id="SAEA-E-000-overlap-calls",
        attempt_id="attempt-2",
        planned_model_calls=2,
        planned_speech_audio_seconds=1000,
    )
    # Both constructed before EITHER records any usage -- the exact race a
    # frozen construction-time snapshot cannot see.
    adapter1 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter2 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    # Interleaved: adapter1 spends 1, adapter2 spends 1 (now the shared 2-call
    # row budget is exhausted), then EITHER adapter's next call must refuse.
    adapter1.request(_payload(request_id="a-1"))
    adapter2.request(_payload(request_id="b-1"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter1.request(_payload(request_id="a-2"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter2.request(_payload(request_id="b-2"))
    store = AttemptStore(binding.data_root / "attempts")
    calls, _ = store.prior_actual_usage(plan1.run_id)
    assert calls == 2, "combined actual spend must never exceed the plan's 2-call budget"


def test_two_overlapping_adapters_built_before_either_records_cannot_together_exceed_the_audio_budget(
    tmp_path,
):
    binding = _binding(tmp_path)
    plan1 = _plan(
        run_id="SAEA-E-000-overlap-audio",
        attempt_id="attempt-1",
        planned_model_calls=10,
        planned_speech_audio_seconds=150,
    )
    plan2 = _plan(
        run_id="SAEA-E-000-overlap-audio",
        attempt_id="attempt-2",
        planned_model_calls=10,
        planned_speech_audio_seconds=150,
    )
    adapter1 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter2 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="a-1", audio_seconds=100.0))
    with pytest.raises(FrozenCoreError, match="audio budget"):
        adapter2.request(_payload(request_id="b-1", audio_seconds=100.0))
    store = AttemptStore(binding.data_root / "attempts")
    _, audio = store.prior_actual_usage(plan1.run_id)
    assert audio == 100.0, "combined actual spend must never exceed the plan's 150s budget"


def test_single_attempt_happy_path_budget_enforcement_is_unchanged(tmp_path):
    """I3 regression guard: a lone adapter (no sibling attempt ever
    constructed) must still be refused exactly at the request that would
    cross its own plan budget -- the fresh-read fix must not change the
    single-attempt case, only the multi-attempt one."""

    plan = _plan(
        run_id="SAEA-E-000-solo",
        attempt_id="attempt-solo",
        planned_model_calls=2,
        planned_speech_audio_seconds=250,
    )
    binding = _binding(tmp_path)
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    adapter.request(_payload(request_id="req-1"))
    adapter.request(_payload(request_id="req-2"))
    with pytest.raises(FrozenCoreError, match="call budget"):
        adapter.request(_payload(request_id="req-3"))
    store = AttemptStore(binding.data_root / "attempts")
    calls, _ = store.prior_actual_usage(plan.run_id)
    assert calls == 2


def test_crashed_attempts_audio_usage_counts_against_a_fresh_attempts_row_budget(tmp_path):
    binding = _binding(tmp_path)
    plan1 = _plan(
        run_id="SAEA-E-000-crashaudio",
        attempt_id="attempt-1",
        planned_model_calls=5,
        planned_speech_audio_seconds=150,
    )
    adapter1 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan1, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run1", plan1.run_id), binding=binding,
    )
    adapter1.request(_payload(request_id="req-1", audio_seconds=100.0))

    plan2 = _plan(
        run_id="SAEA-E-000-crashaudio",
        attempt_id="attempt-2",
        planned_model_calls=5,
        planned_speech_audio_seconds=150,
    )
    adapter2 = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan2, arm="bare-core", transport=_fake_transport,
        sink=TraceSink(tmp_path / "run2", plan2.run_id), binding=binding,
    )
    with pytest.raises(FrozenCoreError, match="audio budget"):
        adapter2.request(_payload(request_id="req-1", audio_seconds=100.0))


# ---------------------------------------------------------------------------
# Intra-process metering thread-safety (owner batching directive 2026-08-08):
# under sample-level concurrency N tasks call adapter.request from worker
# threads; the sibling-read -> budget-check -> record_usage section must be
# atomic or two threads can jointly overshoot the plan's budget (the I3
# comment admitted the simultaneous double-read was open -- it is now closed
# for the one-adapter-per-run case the driver actually builds).
# ---------------------------------------------------------------------------


class _ThreadSafeSink:
    """Minimal duck-typed sink safe under concurrent emits (the production
    concurrent path routes per-sample TraceBuffers; this test isolates the
    adapter, so a locked list is enough)."""

    def __init__(self):
        self.records = []
        self._lock = threading.Lock()

    def emit(self, channel, record_id, payload):
        with self._lock:
            self.records.append((channel, record_id))
        return "0" * 64


def _hammer(adapter, *, threads, requests_each, audio_seconds=100.0):
    """All threads released together; each fires requests_each requests.
    Returns (successes, refusals); any non-budget error propagates."""

    results = []
    results_lock = threading.Lock()
    errors = []
    barrier = threading.Barrier(threads)

    def worker(worker_index):
        try:
            barrier.wait()
            for attempt_index in range(requests_each):
                payload = _payload(
                    request_id=f"req-t{worker_index:02d}-{attempt_index}",
                    audio_seconds=audio_seconds,
                )
                try:
                    adapter.request(payload)
                except FrozenCoreError as error:
                    if "budget exhausted" not in str(error):
                        raise
                    with results_lock:
                        results.append("refused")
                else:
                    with results_lock:
                        results.append("ok")
        except BaseException as error:  # surfaced to the main thread below
            errors.append(error)

    pool = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    for thread in pool:
        thread.start()
    for thread in pool:
        thread.join()
    assert not errors, errors
    return results.count("ok"), results.count("refused")


def _widen_race_window(monkeypatch, seconds=0.005):
    """Deterministically widen the check->record window: the sibling usage
    read sleeps AFTER reading, so an unlocked adapter reliably lets several
    threads pass the budget check on the same stale figure. Patched on the
    CLASS (AttemptStore is a frozen dataclass -- per-instance setattr is
    refused), which is equally precise here: the test builds one store."""

    real = AttemptStore.prior_actual_usage

    def slow(self, *args, **kwargs):
        result = real(self, *args, **kwargs)
        time.sleep(seconds)
        return result

    monkeypatch.setattr(AttemptStore, "prior_actual_usage", slow)


def _slow_transport(request_bytes):
    time.sleep(0.002)
    return json.dumps({"text": "ok", "usage": {"prompt_tokens": 1}}).encode()


def test_concurrent_requests_never_jointly_exceed_the_call_budget(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path)
    plan = _plan(planned_model_calls=5, planned_speech_audio_seconds=1_000_000)
    sink = _ThreadSafeSink()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=_slow_transport,
        sink=sink, binding=binding,
    )
    _widen_race_window(monkeypatch)
    successes, refusals = _hammer(adapter, threads=12, requests_each=3)
    assert successes == 5
    assert refusals == 12 * 3 - 5
    # exact in-process metering
    summary = adapter.cost_summary()
    assert summary["calls_used"] == 5
    assert summary["audio_seconds_used"] == 500.0
    # exact durable metering (the attempt file, the cross-attempt authority)
    store = AttemptStore(binding.data_root / "attempts")
    calls, audio = store.prior_actual_usage(plan.run_id)
    assert (calls, audio) == (5, 500.0)
    # a refused request is never traced as sent: exactly 5 MODEL_REQUESTs
    request_records = [r for r in sink.records if r[0] == "MODEL_REQUEST"]
    assert len(request_records) == 5


def test_concurrent_requests_never_jointly_exceed_the_audio_budget(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path)
    plan = _plan(planned_model_calls=1_000_000, planned_speech_audio_seconds=350.0)
    sink = _ThreadSafeSink()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=_slow_transport,
        sink=sink, binding=binding,
    )
    _widen_race_window(monkeypatch)
    successes, refusals = _hammer(adapter, threads=8, requests_each=2)
    assert successes == 3  # 3 x 100s fits 350s; a 4th would cross
    assert refusals == 8 * 2 - 3
    store = AttemptStore(binding.data_root / "attempts")
    calls, audio = store.prior_actual_usage(plan.run_id)
    assert (calls, audio) == (3, 300.0)


# ---------------------------------------------------------------------------
# Phase 3a (2026-09-04): the adapter carries the envelope's raw tool_calls.
#
# core.model.transport canonicalizes a native message.tool_calls into the same
# [{"name": ..., "arguments": {...}}] TEXT a free-text arm produces, and puts
# the raw list on the envelope beside it. This is the one place that envelope
# is parsed, so it is the one place the distinction can still be read.
# ---------------------------------------------------------------------------


def _native_transport(request_bytes):
    assert isinstance(request_bytes, bytes)
    return json.dumps(
        {
            "text": '[{"name": "setLighting", "arguments": {}}]',
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            "tool_calls": [
                {
                    "id": "c0",
                    "type": "function",
                    "function": {"name": "setLighting", "arguments": "{}"},
                }
            ],
        }
    ).encode()


def test_response_carries_the_raw_tool_calls_when_the_envelope_has_them(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-adapter-tool-calls")
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_native_transport,
        sink=sink,
        binding=_binding(tmp_path),
    )
    response = adapter.request(_payload())

    assert isinstance(response.tool_calls, list)
    assert len(response.tool_calls) == 1
    # Raw, not canonicalized: still the server's own arguments JSON string.
    assert response.tool_calls[0]["function"]["arguments"] == "{}"
    # The canonical text is unchanged, which is exactly why the raw list is
    # needed to tell a native call from model-authored JSON text.
    assert response.text == '[{"name": "setLighting", "arguments": {}}]'


def test_response_tool_calls_is_none_for_a_text_answer(tmp_path):
    adapter, _ = _adapter(tmp_path)
    response = adapter.request(_payload())

    assert response.tool_calls is None
    assert response.text == "hello world"


def test_tool_calls_changes_no_audited_artifact(tmp_path):
    """The sealed outputs and trace contracts are deliberately untouched:
    this field is provenance for the run receipt, not a new payload field.
    The response hashes must be identical whether or not the caller reads
    it."""

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-adapter-tool-calls-hashes")
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_native_transport,
        sink=sink,
        binding=_binding(tmp_path),
    )
    response = adapter.request(_payload())

    raw = _native_transport(b"{}")
    assert response.response_sha256 == hashlib.sha256(raw).hexdigest()
    assert (
        response.response_text_sha256
        == hashlib.sha256(response.text.encode("utf-8")).hexdigest()
    )


def _wire_native_transport(request_bytes):
    assert isinstance(request_bytes, bytes)
    raw = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "native explanation",
                        "tool_calls": [
                            {
                                "id": "call-raw-7",
                                "type": "function",
                                "function": {
                                    "name": "setLighting",
                                    "arguments": '{"zone":"kitchen","level":7}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
        },
        separators=(",", ":"),
    ).encode()
    return json.dumps(
        {
            "text": '[{"name": "setLighting", "arguments": {"zone": "kitchen", "level": 7}}]',
            "usage": {"prompt_tokens": 5, "completion_tokens": 2},
            "tool_calls": [
                {
                    "id": "call-raw-7",
                    "type": "function",
                    "function": {
                        "name": "setLighting",
                        "arguments": '{"zone":"kitchen","level":7}',
                    },
                }
            ],
            "wire_response_b64": __import__("base64").b64encode(raw).decode("ascii"),
            "wire_response_sha256": hashlib.sha256(raw).hexdigest(),
            "wire_finish_reason": "tool_calls",
        }
    ).encode()


def test_preserved_wire_metadata_exposes_original_message_without_changing_text(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-adapter-wire-metadata")
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_wire_native_transport,
        sink=sink,
        binding=_binding(tmp_path),
    )
    response = adapter.request(_payload())

    assert response.text == '[{"name": "setLighting", "arguments": {"zone": "kitchen", "level": 7}}]'
    assert response.wire_response_bytes is not None
    assert response.original_message["content"] == "native explanation"
    assert response.original_message["tool_calls"][0]["id"] == "call-raw-7"
    assert response.original_message["tool_calls"][0]["function"]["arguments"] == '{"zone":"kitchen","level":7}'
    assert response.finish_reason == "tool_calls"
    with pytest.raises(TypeError):
        response.original_message["content"] = "changed"


def test_wire_tool_calls_must_match_original_message_when_accessed(tmp_path):
    def mismatching_transport(request_bytes):
        envelope = json.loads(_wire_native_transport(request_bytes).decode())
        envelope["tool_calls"][0]["id"] = "different"
        return json.dumps(envelope).encode()

    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=_plan(), arm="bare-core",
        transport=mismatching_transport, sink=TraceSink(tmp_path / "run", "mismatch"),
        binding=_binding(tmp_path),
    )
    response = adapter.request(_payload())
    with pytest.raises(ValueError, match="tool_calls"):
        _ = response.original_message


def test_wire_metadata_is_absent_by_default(tmp_path):
    adapter, _ = _adapter(tmp_path)
    response = adapter.request(_payload())
    assert response.wire_response_bytes is None
    assert response.original_message is None
    assert response.finish_reason is None
