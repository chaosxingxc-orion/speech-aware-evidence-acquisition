"""``rails.silence_swap``: matched-duration silent-WAV generation plus the
``SliceRecord`` that chains it to a real parent sample (I3/I4 derivation
rail, ``core.model.slices``). Pure stdlib, zero model contact.
"""

from __future__ import annotations

import hashlib
import wave
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.rails.silence_swap import (
    SilenceSwapError,
    build_silence_swap_slice,
    generate_silent_wav,
)


def _write_wav(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 1.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = int(sample_rate_hz * seconds)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(b"\x00\x00" * n_frames)


# ---------------------------------------------------------------------------
# generate_silent_wav
# ---------------------------------------------------------------------------


def test_generate_silent_wav_writes_the_declared_duration_and_rate(tmp_path):
    path = tmp_path / "silence.wav"
    generate_silent_wav(path=path, duration_seconds=1.5, sample_rate_hz=8000)
    with wave.open(str(path), "rb") as handle:
        assert handle.getframerate() == 8000
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getnframes() == round(8000 * 1.5)
        frames = handle.readframes(handle.getnframes())
    assert frames == b"\x00" * len(frames)  # genuinely silent


def test_generate_silent_wav_rejects_non_positive_duration(tmp_path):
    with pytest.raises(SilenceSwapError, match="duration_seconds"):
        generate_silent_wav(path=tmp_path / "x.wav", duration_seconds=0.0, sample_rate_hz=16000)


def test_generate_silent_wav_rejects_non_positive_sample_rate(tmp_path):
    with pytest.raises(SilenceSwapError, match="sample_rate_hz"):
        generate_silent_wav(path=tmp_path / "x.wav", duration_seconds=1.0, sample_rate_hz=0)


# ---------------------------------------------------------------------------
# build_silence_swap_slice
# ---------------------------------------------------------------------------


def test_build_silence_swap_slice_chains_to_the_real_parent_and_registers_cleanly(tmp_path):
    data_root = tmp_path / "data"
    parent_relpath = "datasets/fake-carrier/media/s1.wav"
    parent_path = data_root / parent_relpath
    _write_wav(parent_path, sample_rate_hz=16000, seconds=2.0)

    registry = SliceRegistry(
        data_root=data_root, run_id="run-1", parent_facts={"s1": (parent_relpath, 2.0)}
    )
    record = build_silence_swap_slice(
        registry=registry,
        data_root=data_root,
        sample_id="s1",
        parent_media_relpath=parent_relpath,
        duration_seconds=2.0,
        sample_rate_hz=16000,
    )

    assert record.sample_id == "s1"
    assert record.parent_media_relpath == parent_relpath
    assert record.parent_sha256 == hashlib.sha256(parent_path.read_bytes()).hexdigest()
    assert record.audio_seconds == 2.0
    assert record.media_relpath == registry.slice_relpath("s1", 0)
    slice_path = data_root / record.media_relpath
    assert slice_path.is_file()
    assert record.sha256 == hashlib.sha256(slice_path.read_bytes()).hexdigest()
    assert record.bytes == slice_path.stat().st_size

    # The record chains cleanly through the SAME registration path any other
    # runtime slice uses -- no special-casing for a silence-swap record.
    registered = registry.register(record)
    assert registered is record
    assert registry.lookup("s1", record.media_relpath) is record


def test_build_silence_swap_slice_can_use_a_duration_different_from_the_parent(tmp_path):
    """Matched duration is a FLIGHT choice (docs/readiness/2026-08-17-pslu-
    preregistration-REGISTERED.md), not something this generator enforces --
    it is free-standing infrastructure, callable with any span the
    registry's own tolerance accepts."""

    data_root = tmp_path / "data"
    parent_relpath = "datasets/fake-carrier/media/s1.wav"
    _write_wav(data_root / parent_relpath, sample_rate_hz=16000, seconds=5.0)
    registry = SliceRegistry(
        data_root=data_root, run_id="run-1", parent_facts={"s1": (parent_relpath, 5.0)}
    )
    record = build_silence_swap_slice(
        registry=registry,
        data_root=data_root,
        sample_id="s1",
        parent_media_relpath=parent_relpath,
        duration_seconds=1.0,
        sample_rate_hz=16000,
    )
    assert record.audio_seconds == 1.0
    registry.register(record)  # 1.0s span lies well inside the 5.0s parent


def test_build_silence_swap_slice_raises_when_the_parent_media_is_missing(tmp_path):
    data_root = tmp_path / "data"
    registry = SliceRegistry(
        data_root=data_root,
        run_id="run-1",
        parent_facts={"s1": ("datasets/fake-carrier/media/s1.wav", 2.0)},
    )
    with pytest.raises(SilenceSwapError, match="parent media missing"):
        build_silence_swap_slice(
            registry=registry,
            data_root=data_root,
            sample_id="s1",
            parent_media_relpath="datasets/fake-carrier/media/s1.wav",
            duration_seconds=2.0,
            sample_rate_hz=16000,
        )
