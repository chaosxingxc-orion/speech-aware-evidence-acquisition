"""Runtime-slice derivation chain: the I3/I4 rail extension for the OBS loop.

Owner directive (session message, 2026-08-08): the frozen core must never be
asked to process a whole 40-75-minute earnings call in one request. The
obs-agent-loop policy therefore cuts buffer slices from the sample's
registered parent media AT RUNTIME (one soundfile/ffmpeg decode per sample,
slices written as 16 kHz mono WAV under ``derived/obs-slices/<run_id>/``
inside the controlled data root) and sends ONE slice per request.

Before this module, the payload-binding rail (``core.model.binding``,
invariants I3/I4) required every payload's ``media_relpath`` to EXACTLY equal
the loader-verified parent media path -- exactly right for whole-file
requests, and exactly what would refuse every runtime slice. The extension
is deliberately NOT a relaxation: a slice is admitted ONLY when a
:class:`SliceRecord` registered here CHAINS to the sample's registered
media, meaning all of the following verified facts hold at registration time
(and the byte-identity fact again on every send,
:meth:`SliceRegistry.verify_slice_bytes`):

- the record names a sample id in this run's verified split, and the parent
  media path the LOADER bound for that exact sample id;
- the record's ``parent_sha256`` equals the SHA-256 of the parent media
  bytes actually on disk under the controlled data root -- the same file
  ``contracts.FrozenCoreGate.verify_media_identity`` already re-verified
  against D1's frozen identity when this run's gate opened, so the chain
  bottoms out at D1 without this module re-reading any receipt;
- the slice's ``[start_seconds, end_seconds)`` span lies inside the parent's
  loader-fact duration (a small tolerance absorbs CSV-vs-decoder rounding;
  a span materially outside the parent is refused);
- the slice file lives at the run's own convention path
  (``derived/obs-slices/<run_id>/<token>/i<NNNN>.wav`` -- never anywhere
  else under the data root), exists, and its measured (size, SHA-256) equal
  the record's. ``<token>`` is a path-safe filesystem TOKEN derived from the
  sample id (:func:`_slice_token`) -- an already path-safe id (every
  historical earnings id) is used unchanged, so no existing run's paths
  move; a raw id that is not path-safe (SLURP's ``carrier:split:index:stem``,
  Audio2Tool's ``tier:000001``) is sanitized and hash-suffixed instead. The
  RAW sample id, never the token, stays the one binding/lookup key
  (``parent_facts``, ``SliceRecord.sample_id``, ``register()``): this
  separates identity (what the slice chains to) from addressing (where it
  lives on disk).

Preprocessing provenance (owner addition, 2026-08-08): when the policy
applies a declared per-slice transform (v1: ``rms-norm`` only), the record
carries ``preprocess`` + ``pre_sha256`` (hash of the raw cut before the
transform) alongside ``sha256`` (hash of the bytes actually written and
sent). The rail re-verifies the WRITTEN bytes; the DSP itself is declared
provenance -- re-deriving it here would mean re-decoding the parent on every
request, and the honest guarantee is stated as exactly that split.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from . import FrozenCoreError

OBS_SLICES_SUBDIR = "derived/obs-slices"

# CSV metadata durations and decoded frame counts legitimately disagree by a
# fraction of a second (mp3 padding, metadata rounding); a slice whose end
# lies within this many seconds past the loader-fact duration still chains.
PARENT_DURATION_TOLERANCE_SECONDS = 1.0
_FLOAT_TOLERANCE = 1e-6
_SHA256 = re.compile(r"[0-9a-f]{64}")
_PATH_SAFE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_TOKEN_UNSAFE = re.compile(r"[^A-Za-z0-9._-]")


def _slice_token(raw_id: str) -> str:
    """Deterministic, injective path-safe filesystem token for ``raw_id``.

    Every slice directory before this function existed used the sample id
    itself, which only ever worked because every id in use (earnings' bare
    numeric ids) already satisfied ``_PATH_SAFE``. This keeps that case
    byte-identical -- an already path-safe id is returned UNCHANGED, so no
    historical run's paths move -- and extends addressing to ids that are
    not (SLURP's ``carrier:split:index:stem``, Audio2Tool's ``tier:000001``):
    every character outside ``_PATH_SAFE``'s alphabet is replaced with ``_``
    and a 12-hex-char slice of ``sha256(raw_id)`` is appended, so two
    different raw ids can never collide after sanitization even when their
    sanitized forms coincide (e.g. ``a:b`` and ``a;b``). The raw id remains
    the ONLY binding/lookup key anywhere in this module -- this token is
    filesystem addressing only, never identity."""

    if _PATH_SAFE.fullmatch(raw_id):
        return raw_id
    sanitized = _TOKEN_UNSAFE.sub("_", raw_id)
    digest = hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:12]
    token = f"{sanitized}-{digest}"
    if not _PATH_SAFE.fullmatch(token):
        # sanitization alone cannot fix a leading '.', '-', '_', or an empty
        # raw id; a single safe prefix keeps the token a legal path
        # component without touching injectivity (still keyed by raw_id).
        token = f"t{token}"
    return token


def _measure(path: Path, label: str) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with Path(path).open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except FileNotFoundError:
        raise FrozenCoreError(f"{label} is missing: {path}") from None
    except OSError as error:
        raise FrozenCoreError(f"cannot read {label} {path}: {error}") from error
    return size, digest.hexdigest()


@dataclass(frozen=True)
class SliceRecord:
    """One runtime slice's derivation facts (immutable, hash-chained)."""

    sample_id: str
    parent_media_relpath: str
    parent_sha256: str
    start_seconds: float
    end_seconds: float
    audio_seconds: float
    sample_rate_hz: int
    media_relpath: str
    sha256: str
    bytes: int
    iteration: int
    preprocess: tuple[str, ...] = ()
    pre_sha256: str | None = None

    def trace_view(self) -> dict[str, object]:
        """The record as a JSON-safe mapping for trace/derivation artifacts."""

        return {
            "sample_id": self.sample_id,
            "parent_media_relpath": self.parent_media_relpath,
            "parent_sha256": self.parent_sha256,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "audio_seconds": self.audio_seconds,
            "sample_rate_hz": self.sample_rate_hz,
            "media_relpath": self.media_relpath,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "iteration": self.iteration,
            "preprocess": list(self.preprocess),
            "pre_sha256": self.pre_sha256,
        }


class SliceRegistry:
    """Per-run registry of derivation-chained slices (module docstring).

    Built by ``core.driver.run_experiment`` from the SAME loader facts the
    :class:`~core.base.PayloadBindingContext` carries, handed both to the
    adapter (which consults it in ``_enforce_payload_binding``) and to the
    policy via ``SampleContext.extras`` (which registers each slice BEFORE
    building the request payload that names it). An empty registry admits
    nothing -- constructing one changes no whole-file behaviour.
    """

    def __init__(
        self,
        *,
        data_root: Path,
        run_id: str,
        parent_facts: Mapping[str, tuple[str, float]],
    ) -> None:
        if not isinstance(run_id, str) or not _PATH_SAFE.fullmatch(run_id):
            raise FrozenCoreError(f"slice registry run_id {run_id!r} is not path-safe")
        self._data_root = Path(data_root)
        self._run_id = run_id
        self._parent_facts = dict(parent_facts)
        self._records: dict[tuple[str, str], SliceRecord] = {}
        self._parent_sha_cache: dict[str, str] = {}

    @property
    def root_relpath(self) -> str:
        return f"{OBS_SLICES_SUBDIR}/{self._run_id}"

    def slice_root(self) -> Path:
        return self._data_root / OBS_SLICES_SUBDIR / self._run_id

    def slice_relpath(self, sample_id: str, iteration: int) -> str:
        """This run's convention path for one iteration of a slice derived
        from ``sample_id``. ``sample_id`` is always the RAW binding id; the
        path component is :func:`_slice_token` of it, so this never raises
        for a raw id merely because it is not path-safe -- it only raises
        for a non-string or empty id (nothing to derive a token from) or an
        out-of-range iteration."""

        if not isinstance(sample_id, str) or not sample_id:
            raise FrozenCoreError(f"slice sample_id {sample_id!r} is not path-safe")
        if isinstance(iteration, bool) or not isinstance(iteration, int) or not (
            0 <= iteration <= 9999
        ):
            raise FrozenCoreError(f"slice iteration {iteration!r} outside 0..9999")
        token = _slice_token(sample_id)
        return f"{self.root_relpath}/{token}/i{iteration:04d}.wav"

    def _parent_sha256(self, sample_id: str, parent_relpath: str) -> str:
        cached = self._parent_sha_cache.get(sample_id)
        if cached is None:
            _, cached = _measure(
                self._data_root / parent_relpath, f"parent media for {sample_id!r}"
            )
            self._parent_sha_cache[sample_id] = cached
        return cached

    def register(self, record: SliceRecord) -> SliceRecord:
        if not isinstance(record, SliceRecord):
            raise FrozenCoreError(
                f"slice registration requires a SliceRecord, got {type(record).__name__}"
            )
        fact = self._parent_facts.get(record.sample_id)
        if fact is None:
            raise FrozenCoreError(
                f"slice sample_id {record.sample_id!r} is not in the verified split "
                "bound to this run; a slice of an unverified sample can never be sent"
            )
        parent_relpath, parent_seconds = fact
        if record.parent_media_relpath != parent_relpath:
            raise FrozenCoreError(
                f"slice record for {record.sample_id!r} names parent media "
                f"{record.parent_media_relpath!r}, but the verified split bound "
                f"{parent_relpath!r} -- refused"
            )
        if not isinstance(record.parent_sha256, str) or _SHA256.fullmatch(
            record.parent_sha256
        ) is None:
            raise FrozenCoreError("slice record parent_sha256 must be a sha256 hex digest")
        actual_parent_sha = self._parent_sha256(record.sample_id, parent_relpath)
        if record.parent_sha256 != actual_parent_sha:
            raise FrozenCoreError(
                f"slice record for {record.sample_id!r} does not chain to the "
                f"registered media: record parent_sha256 {record.parent_sha256[:12]}..., "
                f"the on-disk parent is {actual_parent_sha[:12]}... -- foreign audio "
                "can never enter through the slice rail"
            )
        for label, value in (
            ("start_seconds", record.start_seconds),
            ("end_seconds", record.end_seconds),
            ("audio_seconds", record.audio_seconds),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise FrozenCoreError(f"slice record {label} must be a finite number")
        if record.start_seconds < 0 or record.end_seconds <= record.start_seconds:
            raise FrozenCoreError(
                f"slice span [{record.start_seconds}, {record.end_seconds}) is not a "
                "positive span inside the parent"
            )
        if record.end_seconds > parent_seconds + PARENT_DURATION_TOLERANCE_SECONDS:
            raise FrozenCoreError(
                f"slice span end {record.end_seconds}s lies outside the parent's "
                f"verified duration {parent_seconds}s (+{PARENT_DURATION_TOLERANCE_SECONDS}s "
                "tolerance) -- an offset outside the parent is refused"
            )
        if abs(record.audio_seconds - (record.end_seconds - record.start_seconds)) > _FLOAT_TOLERANCE:
            raise FrozenCoreError(
                f"slice record audio_seconds {record.audio_seconds} disagrees with its "
                f"own span ({record.end_seconds - record.start_seconds})"
            )
        if (
            isinstance(record.sample_rate_hz, bool)
            or not isinstance(record.sample_rate_hz, int)
            or record.sample_rate_hz <= 0
        ):
            raise FrozenCoreError("slice record sample_rate_hz must be a positive integer")
        expected_relpath = self.slice_relpath(record.sample_id, record.iteration)
        if record.media_relpath != expected_relpath:
            raise FrozenCoreError(
                f"slice media_relpath {record.media_relpath!r} is outside this run's "
                f"slice tree (expected {expected_relpath!r}); slices live only under "
                f"{self.root_relpath}/"
            )
        if not isinstance(record.preprocess, tuple) or not all(
            isinstance(name, str) and name for name in record.preprocess
        ):
            raise FrozenCoreError("slice record preprocess must be a tuple of names")
        if record.preprocess:
            if not isinstance(record.pre_sha256, str) or _SHA256.fullmatch(record.pre_sha256) is None:
                raise FrozenCoreError(
                    "a preprocessed slice must carry pre_sha256 (hash of the raw cut "
                    "before the declared transform)"
                )
        elif record.pre_sha256 is not None:
            raise FrozenCoreError(
                "pre_sha256 without a declared preprocess transform is meaningless -- refused"
            )
        key = (record.sample_id, record.media_relpath)
        if key in self._records:
            raise FrozenCoreError(
                f"slice {record.media_relpath!r} is already registered for sample "
                f"{record.sample_id!r}; a derivation record is written exactly once"
            )
        self.verify_slice_bytes(record)
        self._records[key] = record
        return record

    def lookup(self, sample_id: str, media_relpath: str) -> SliceRecord | None:
        return self._records.get((str(sample_id), str(media_relpath)))

    def verify_slice_bytes(self, record: SliceRecord) -> None:
        """Re-measure the slice file and require exact (size, sha256) equality
        with the record -- called at registration AND again on every send
        (``binding._enforce_payload_binding``), so a slice swapped between the
        two is caught before its bytes ever leave the process."""

        if not isinstance(record.sha256, str) or _SHA256.fullmatch(record.sha256) is None:
            raise FrozenCoreError("slice record sha256 must be a sha256 hex digest")
        actual_bytes, actual_sha = _measure(
            self._data_root / record.media_relpath,
            f"slice media for {record.sample_id!r}",
        )
        if actual_bytes != record.bytes or actual_sha != record.sha256:
            raise FrozenCoreError(
                f"slice byte-identity drift for {record.media_relpath!r}: record says "
                f"{record.bytes} bytes / {record.sha256[:12]}..., the live file is "
                f"{actual_bytes} bytes / {actual_sha[:12]}... -- hash mismatch, refused"
            )
