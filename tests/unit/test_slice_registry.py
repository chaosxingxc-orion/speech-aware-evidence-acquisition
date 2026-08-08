"""Runtime-slice derivation chain (obs-agent-loop, owner directive 2026-08-08).

``core.model.SliceRegistry`` is the rail that lets the payload-binding check
admit a runtime-cut slice INSTEAD of the sample's registered parent media --
but ONLY when the slice's derivation record chains to that registered media:
right parent path, parent bytes hash to the recorded parent sha, offsets
inside the parent's loader-fact duration, slice file bytes hash to the
record. Everything else refuses (fail-closed): a foreign file, a tampered
record, an offset outside the parent, a path outside the run's slice tree.
"""

import hashlib
from array import array
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    SliceRecord,
    SliceRegistry,
)
from speech_aware_evidence_acquisition.reproduction.obs_audio import write_wav_bytes

RUN_ID = "SAEA-E-000-slices"
SAMPLE_ID = "5000001"
PARENT_RELPATH = "datasets/earnings21-22/earnings22/media/5000001.mp3"
PARENT_BYTES = b"fake-parent-mp3-bytes"
PARENT_SECONDS = 100.0


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture()
def world(tmp_path):
    data_root = tmp_path / "data"
    parent = data_root / PARENT_RELPATH
    parent.parent.mkdir(parents=True)
    parent.write_bytes(PARENT_BYTES)
    registry = SliceRegistry(
        data_root=data_root,
        run_id=RUN_ID,
        parent_facts={SAMPLE_ID: (PARENT_RELPATH, PARENT_SECONDS)},
    )
    return data_root, registry


def _write_slice(data_root: Path, registry: SliceRegistry, iteration: int = 0) -> tuple[str, bytes]:
    relpath = registry.slice_relpath(SAMPLE_ID, iteration)
    raw = write_wav_bytes(array("h", [100, -100] * 800), 16000)
    path = data_root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return relpath, raw


def _record(relpath: str, raw: bytes, **overrides) -> SliceRecord:
    base = dict(
        sample_id=SAMPLE_ID,
        parent_media_relpath=PARENT_RELPATH,
        parent_sha256=_sha(PARENT_BYTES),
        start_seconds=0.0,
        end_seconds=60.0,
        audio_seconds=60.0,
        sample_rate_hz=16000,
        media_relpath=relpath,
        sha256=_sha(raw),
        bytes=len(raw),
        iteration=0,
        preprocess=(),
        pre_sha256=None,
    )
    base.update(overrides)
    return SliceRecord(**base)


class TestRegisterHappyPath:
    def test_registers_and_looks_up(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        record = _record(relpath, raw)
        registry.register(record)
        assert registry.lookup(SAMPLE_ID, relpath) is record
        registry.verify_slice_bytes(record)  # send-time re-check passes

    def test_slice_relpath_convention(self, world):
        _, registry = world
        assert (
            registry.slice_relpath(SAMPLE_ID, 7)
            == f"derived/obs-slices/{RUN_ID}/{SAMPLE_ID}/i0007.wav"
        )

    def test_preprocessed_slice_carries_pre_hash(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        record = _record(
            relpath, raw, preprocess=("rms-norm",), pre_sha256="c" * 64
        )
        registry.register(record)
        assert registry.lookup(SAMPLE_ID, relpath).preprocess == ("rms-norm",)


class TestRegisterRefusals:
    def test_unknown_sample_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="not in the verified split"):
            registry.register(_record(relpath, raw, sample_id="9999999"))

    def test_wrong_parent_relpath_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="parent media"):
            registry.register(
                _record(relpath, raw, parent_media_relpath="datasets/elsewhere/x.mp3")
            )

    def test_tampered_parent_hash_refused(self, world):
        """A derivation record claiming a DIFFERENT parent hash does not chain
        to the registered media -- the demonstrated foreign-audio smuggle."""

        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="does not chain"):
            registry.register(_record(relpath, raw, parent_sha256="d" * 64))

    def test_offsets_outside_parent_duration_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="outside the parent"):
            registry.register(
                _record(relpath, raw, start_seconds=90.0, end_seconds=160.0, audio_seconds=70.0)
            )

    def test_negative_start_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError):
            registry.register(
                _record(relpath, raw, start_seconds=-1.0, end_seconds=59.0)
            )

    def test_audio_seconds_must_equal_span(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="audio_seconds"):
            registry.register(_record(relpath, raw, audio_seconds=59.0))

    def test_foreign_file_bytes_refused(self, world):
        """The slice file on disk must hash to the record -- a swapped wav
        (right path, wrong bytes) refuses at registration."""

        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        (data_root / relpath).write_bytes(b"not-the-derived-slice")
        with pytest.raises(FrozenCoreError, match="hash"):
            registry.register(_record(relpath, raw))

    def test_missing_slice_file_refused(self, world):
        data_root, registry = world
        relpath = registry.slice_relpath(SAMPLE_ID, 0)
        with pytest.raises(FrozenCoreError, match="missing"):
            registry.register(_record(relpath, b"whatever"))

    def test_path_outside_the_run_slice_tree_refused(self, world):
        data_root, registry = world
        rogue = "datasets/earnings21-22/earnings22/media/rogue.wav"
        raw = write_wav_bytes(array("h", [0] * 100), 16000)
        path = data_root / rogue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        with pytest.raises(FrozenCoreError, match="slice tree"):
            registry.register(_record(rogue, raw))

    def test_duplicate_registration_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        registry.register(_record(relpath, raw))
        with pytest.raises(FrozenCoreError, match="already registered"):
            registry.register(_record(relpath, raw))

    def test_preprocess_without_pre_hash_refused(self, world):
        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        with pytest.raises(FrozenCoreError, match="pre_sha256"):
            registry.register(_record(relpath, raw, preprocess=("rms-norm",)))


class TestSendTimeReverification:
    def test_bytes_swapped_after_registration_refused_at_send(self, world):
        """Registration alone is not enough: the send-path re-check catches a
        slice file swapped between registration and the actual request."""

        data_root, registry = world
        relpath, raw = _write_slice(data_root, registry)
        record = _record(relpath, raw)
        registry.register(record)
        (data_root / relpath).write_bytes(b"swapped-after-registration")
        with pytest.raises(FrozenCoreError, match="hash"):
            registry.verify_slice_bytes(record)

    def test_lookup_misses_return_none(self, world):
        _, registry = world
        assert registry.lookup(SAMPLE_ID, "derived/obs-slices/other/i0000.wav") is None
        assert registry.lookup("9999999", "derived/obs-slices/x/i0000.wav") is None
