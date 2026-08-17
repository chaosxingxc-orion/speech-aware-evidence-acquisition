"""Silence-swap control media: a runtime-generated, matched-duration silent
WAV substituted for a sample's real audio -- the audio-only negative control
``docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md`` section 2
names ("silence-swap on 3 seeded A1' samples"). Registered as a
``core.model.slices.SliceRecord`` -- the EXISTING I3/I4 derivation-chain
rail (``core.model.slices`` module docstring: "a payload naming something
OTHER than the sample's registered parent media is admitted ONLY as a
derivation-chained runtime slice") -- never a new admission mechanism or a
mutation of the committed carrier bytes.

Pure stdlib generation (the ``wave`` module only): writing silence needs no
model contact and no external audio library; :func:`build_silence_swap_slice`
also re-reads the WRITTEN bytes to build the record's own ``sha256``/
``bytes`` fields, the same "measure what is actually on disk" discipline
``core.model.slices.SliceRegistry.verify_slice_bytes`` re-checks on every
send.
"""

from __future__ import annotations

import hashlib
import wave
from pathlib import Path

from ..core.model import SliceRegistry
from ..core.model.slices import SliceRecord


class SilenceSwapError(RuntimeError):
    """A silence-swap generation input is malformed, or the parent media it
    must chain to is missing."""


def generate_silent_wav(*, path: Path, duration_seconds: float, sample_rate_hz: int) -> None:
    """Write a mono, 16-bit PCM, all-zero-sample WAV of exactly
    ``duration_seconds`` at ``sample_rate_hz`` to ``path``. Matched duration
    is the whole point of a silence-SWAP control: the roster/prompt text is
    unchanged, only the audio is replaced with silence of the SAME length,
    so an unchanged answer would indicate the roster text alone (not
    anything actually heard) determined it."""

    if (
        isinstance(duration_seconds, bool)
        or not isinstance(duration_seconds, (int, float))
        or duration_seconds <= 0
    ):
        raise SilenceSwapError(
            f"duration_seconds must be a positive number, got {duration_seconds!r}"
        )
    if isinstance(sample_rate_hz, bool) or not isinstance(sample_rate_hz, int) or sample_rate_hz <= 0:
        raise SilenceSwapError(f"sample_rate_hz must be a positive integer, got {sample_rate_hz!r}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = max(1, round(sample_rate_hz * duration_seconds))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate_hz)
        handle.writeframes(b"\x00\x00" * n_frames)


def build_silence_swap_slice(
    *,
    registry: SliceRegistry,
    data_root: Path,
    sample_id: str,
    parent_media_relpath: str,
    duration_seconds: float,
    sample_rate_hz: int,
    iteration: int = 0,
) -> SliceRecord:
    """Generate a matched-duration silent WAV for ``sample_id`` at
    ``registry``'s own slice-tree convention path (``SliceRegistry.
    slice_relpath``) and build the :class:`~core.model.slices.SliceRecord`
    that chains it to the sample's REAL parent media on disk (module
    docstring). Does NOT register it -- the caller registers via
    ``FrozenCoreClient.register_slice``/``SliceRegistry.register``, exactly
    like any other slice, so a caller can inspect the record (or decide not
    to admit it) before it becomes sendable."""

    data_root = Path(data_root)
    parent_path = data_root / parent_media_relpath
    if not parent_path.is_file():
        raise SilenceSwapError(f"parent media missing for {sample_id!r}: {parent_path}")
    parent_sha256 = hashlib.sha256(parent_path.read_bytes()).hexdigest()
    slice_relpath = registry.slice_relpath(sample_id, iteration)
    slice_path = data_root / slice_relpath
    generate_silent_wav(
        path=slice_path, duration_seconds=duration_seconds, sample_rate_hz=sample_rate_hz
    )
    slice_bytes_content = slice_path.read_bytes()
    return SliceRecord(
        sample_id=sample_id,
        parent_media_relpath=parent_media_relpath,
        parent_sha256=parent_sha256,
        start_seconds=0.0,
        end_seconds=duration_seconds,
        audio_seconds=duration_seconds,
        sample_rate_hz=sample_rate_hz,
        media_relpath=slice_relpath,
        sha256=hashlib.sha256(slice_bytes_content).hexdigest(),
        bytes=len(slice_bytes_content),
        iteration=iteration,
    )


__all__ = ["SilenceSwapError", "build_silence_swap_slice", "generate_silent_wav"]
