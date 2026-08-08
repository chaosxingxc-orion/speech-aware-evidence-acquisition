"""Payload-binding rail extension (I3/I4 + slices, owner directive 2026-08-08).

``FrozenCoreAdapter`` may now be constructed with a ``slice_registry``; a
payload whose ``media_relpath`` is NOT the sample's registered parent media
is admitted ONLY when that exact (sample_id, media_relpath) pair was
registered as a derivation-chained :class:`core.model.SliceRecord` -- and
then its ``audio_seconds``/``sample_rate_hz`` must match the SLICE record,
so metering charges exactly the seconds actually sent. Everything the parent
path already enforced is unchanged (regression-guarded here and by the whole
pre-existing test_frozen_core_adapter suite, which never passes a registry).
"""

import hashlib
import json
from array import array

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreAdapter,
    FrozenCoreError,
    SliceRecord,
    SliceRegistry,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes

RUN_ID = "SAEA-E-000-sliceadapter"
SAMPLE_ID = "5000001"
PARENT_RELPATH = "datasets/earnings21-22/earnings22/media/5000001.mp3"
PARENT_BYTES = b"fake-parent-mp3-bytes"
PARENT_SECONDS = 100.0


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        return None


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _plan():
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=10,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=500,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )


def _transport(request_bytes):
    return json.dumps({"text": "ok", "usage": {"prompt_tokens": 1}}).encode()


@pytest.fixture()
def world(tmp_path):
    data_root = tmp_path / "data"
    parent = data_root / PARENT_RELPATH
    parent.parent.mkdir(parents=True)
    parent.write_bytes(PARENT_BYTES)
    binding = PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({SAMPLE_ID}),
        sample_facts={SAMPLE_ID: (PARENT_SECONDS, 16000)},
        media_relpaths={SAMPLE_ID: PARENT_RELPATH},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
    )
    registry = SliceRegistry(
        data_root=data_root,
        run_id=RUN_ID,
        parent_facts={SAMPLE_ID: (PARENT_RELPATH, PARENT_SECONDS)},
    )
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=_plan(),
        arm="bare-core",
        transport=_transport,
        sink=TraceSink(tmp_path / "run", RUN_ID),
        binding=binding,
        slice_registry=registry,
    )
    return data_root, registry, adapter


def _registered_slice(data_root, registry, *, iteration=0, seconds=60.0):
    relpath = registry.slice_relpath(SAMPLE_ID, iteration)
    raw = write_wav_bytes(array("h", [120, -120] * 400), 16000)
    path = data_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    record = SliceRecord(
        sample_id=SAMPLE_ID,
        parent_media_relpath=PARENT_RELPATH,
        parent_sha256=_sha(PARENT_BYTES),
        start_seconds=0.0,
        end_seconds=seconds,
        audio_seconds=seconds,
        sample_rate_hz=16000,
        media_relpath=relpath,
        sha256=_sha(raw),
        bytes=len(raw),
        iteration=iteration,
    )
    registry.register(record)
    return record


def _payload(media_relpath, audio_seconds, sample_rate_hz=16000, request_id="req-1-i0000"):
    return {
        "request_id": request_id,
        "carrier_lock_key": "earnings22-original",
        "sample_id": SAMPLE_ID,
        "speech_ref": f"earnings22-original/{SAMPLE_ID}",
        "media_relpath": media_relpath,
        "audio_seconds": audio_seconds,
        "sample_rate_hz": sample_rate_hz,
        "task_instruction": "Transcribe the speech verbatim.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }


class TestSliceAdmission:
    def test_registered_slice_is_admitted_and_metered_by_slice_seconds(self, world):
        data_root, registry, adapter = world
        record = _registered_slice(data_root, registry, seconds=60.0)
        response = adapter.request(_payload(record.media_relpath, 60.0))
        assert response.text == "ok"
        assert adapter.cost_summary()["audio_seconds_used"] == 60.0

    def test_parent_path_behaviour_is_unchanged(self, world):
        data_root, registry, adapter = world
        response = adapter.request(
            _payload(PARENT_RELPATH, PARENT_SECONDS, request_id="req-1")
        )
        assert response.text == "ok"
        assert adapter.cost_summary()["audio_seconds_used"] == PARENT_SECONDS

    def test_unregistered_slice_path_refused(self, world):
        data_root, registry, adapter = world
        rogue = registry.slice_relpath(SAMPLE_ID, 3)
        raw = write_wav_bytes(array("h", [0] * 100), 16000)
        path = data_root / rogue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        with pytest.raises(FrozenCoreError, match="media_relpath"):
            adapter.request(_payload(rogue, 60.0))

    def test_slice_audio_seconds_must_match_the_record(self, world):
        """A payload understating the slice's metered seconds is refused --
        the budget rail charges exactly what the derivation record proves."""

        data_root, registry, adapter = world
        record = _registered_slice(data_root, registry, seconds=60.0)
        with pytest.raises(FrozenCoreError, match="audio_seconds"):
            adapter.request(_payload(record.media_relpath, 5.0))

    def test_slice_sample_rate_must_match_the_record(self, world):
        data_root, registry, adapter = world
        record = _registered_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="sample_rate_hz"):
            adapter.request(_payload(record.media_relpath, 60.0, sample_rate_hz=44100))

    def test_slice_bytes_swapped_after_registration_refused_at_send(self, world):
        data_root, registry, adapter = world
        record = _registered_slice(data_root, registry)
        (data_root / record.media_relpath).write_bytes(b"swapped")
        with pytest.raises(FrozenCoreError, match="hash mismatch"):
            adapter.request(_payload(record.media_relpath, 60.0))

    def test_without_a_registry_slice_paths_keep_the_original_refusal(self, tmp_path):
        data_root = tmp_path / "data"
        parent = data_root / PARENT_RELPATH
        parent.parent.mkdir(parents=True)
        parent.write_bytes(PARENT_BYTES)
        binding = PayloadBindingContext(
            carrier_lock_key="earnings22-original",
            allowed_sample_ids=frozenset({SAMPLE_ID}),
            sample_facts={SAMPLE_ID: (PARENT_SECONDS, 16000)},
            media_relpaths={SAMPLE_ID: PARENT_RELPATH},
            data_root=data_root,
            carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
        )
        adapter = FrozenCoreAdapter(
            gate=_OpenGate(),
            plan=_plan(),
            arm="bare-core",
            transport=_transport,
            sink=TraceSink(tmp_path / "run", RUN_ID),
            binding=binding,
        )
        with pytest.raises(FrozenCoreError, match="does not match the verified split"):
            adapter.request(
                _payload(f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0000.wav", 60.0)
            )

    def test_non_registry_object_refused_at_construction(self, world, tmp_path):
        data_root, registry, _ = world
        binding = PayloadBindingContext(
            carrier_lock_key="earnings22-original",
            allowed_sample_ids=frozenset({SAMPLE_ID}),
            sample_facts={SAMPLE_ID: (PARENT_SECONDS, 16000)},
            media_relpaths={SAMPLE_ID: PARENT_RELPATH},
            data_root=data_root,
            carrier_root=data_root / "datasets" / "earnings21-22" / "earnings22",
        )
        with pytest.raises(FrozenCoreError, match="slice_registry"):
            FrozenCoreAdapter(
                gate=_OpenGate(),
                plan=_plan(),
                arm="bare-core",
                transport=_transport,
                sink=TraceSink(tmp_path / "run2", RUN_ID),
                binding=binding,
                slice_registry=object(),
            )
