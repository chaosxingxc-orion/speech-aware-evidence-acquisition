"""Adapter choke point: allowlist exact-set, boundary, budgets, tracing,
payload<->plan<->split value binding (I3) and media confinement (I4)."""

import json
import os
import subprocess

import pytest

from speech_aware_evidence_acquisition.contracts import (
    BoundaryViolation,
    ExecutionPlan,
)
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS
from speech_aware_evidence_acquisition.core.base import CoreError, PayloadBindingContext
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
