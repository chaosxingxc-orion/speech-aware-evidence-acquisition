"""Deterministic, boundary-safe carrier sample loading (E0 D4 substrate, reused at R0).

A loader never reads transcript, annotation or context *content*; it resolves sample
identity, media location, duration and sample rate from the carrier's metadata layer.
Everything a loader exposes to the runtime side passes
:func:`speech_aware_evidence_acquisition.contracts.assert_information_boundary`
before it is returned — gold and reference layers exist on disk next to the media,
and this module is the choke point that keeps them out of runtime payloads.

R0 repair refactor stage 2 (part B): ``load_earnings21``/``load_earnings22`` used
to each hardcode their own media subdir+extension, metadata filename, and metadata
column names. Both are now thin wrappers over :func:`load_carrier`, a single
descriptor-driven loader (``data.carriers.CarrierDescriptor``) -- every public name
below is unchanged, so nothing importing ``load_earnings21``/``load_earnings22``
(including ``e0/d4_trace.py``, which this module stays behaviour-identical for)
needs to change.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..contracts import assert_information_boundary
from .carriers import CarrierDescriptor, EARNINGS21_ORIGINAL, EARNINGS22_ORIGINAL
from .identity import FileFact, hash_file
from .lock import asset_dir, lock_entry


class LoaderError(RuntimeError):
    """Deterministic loading failed: identity drift, missing media or bad metadata."""


@dataclass(frozen=True)
class SampleRef:
    """One sample's identity + runtime-legal descriptors (no annotation content)."""

    carrier_lock_key: str
    sample_id: str
    media_relpath: str
    audio_seconds: float
    sample_rate_hz: int

    def runtime_view(self) -> dict[str, object]:
        view: dict[str, object] = {
            "carrier_lock_key": self.carrier_lock_key,
            "sample_id": self.sample_id,
            "speech_ref": f"{self.carrier_lock_key}/{self.sample_id}",
            "media_relpath": self.media_relpath,
            "audio_seconds": self.audio_seconds,
            "sample_rate_hz": self.sample_rate_hz,
        }
        assert_information_boundary(view)
        return view


@dataclass(frozen=True)
class MaterializedSample:
    """A :class:`SampleRef` plus the re-measured media bytes (provenance-grade)."""

    ref: SampleRef
    media_bytes: int
    media_sha256: str


def _metadata_rows(path: Path, id_column: str) -> dict[str, Mapping[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or id_column not in reader.fieldnames:
                raise LoaderError(f"metadata {path} lacks id column {id_column!r}")
            rows: dict[str, Mapping[str, str]] = {}
            for row_number, row in enumerate(reader, start=2):
                raw = row[id_column]
                if raw is None:
                    raise LoaderError(
                        f"metadata {path}: malformed row {row_number} (missing {id_column!r})"
                    )
                sample_id = str(raw).strip()
                if not sample_id or sample_id in rows:
                    raise LoaderError(f"metadata {path}: blank or duplicate id {sample_id!r}")
                rows[sample_id] = row
    except (OSError, UnicodeError, csv.Error) as error:
        raise LoaderError(f"cannot read metadata {path}: {error}") from error
    if not rows:
        raise LoaderError(f"metadata {path} has no rows")
    return rows


def _float_field(row: Mapping[str, str], column: str, context: str) -> float:
    try:
        value = float(str(row[column]).strip())
    except (KeyError, TypeError, ValueError) as error:
        raise LoaderError(f"{context}: bad numeric column {column!r}: {error}") from error
    if not math.isfinite(value) or value <= 0:
        raise LoaderError(
            f"{context}: column {column!r} must be a finite positive number, got {value}"
        )
    return value


def load_carrier(descriptor: CarrierDescriptor, lock: Mapping[str, object], root: Path) -> list[SampleRef]:
    """Every sample for ONE carrier, sorted by sample id, identity-checked against
    media -- driven entirely by ``descriptor``'s media/metadata layout facts
    (R0 repair refactor stage 2, part B). ``load_earnings21``/``load_earnings22``
    are thin wrappers over this; a future carrier needs only its own descriptor
    (``data.carriers.register_carrier_descriptor``) plus a loader registration
    (``core.carriers``) to load through the exact same code path."""

    if descriptor.metadata_filename is None or descriptor.metadata_columns is None:
        raise LoaderError(
            f"{descriptor.lock_key} declares no metadata layer "
            "(data.carriers.CarrierDescriptor.metadata_filename/metadata_columns is "
            "None); load_carrier only loads a carrier whose sample universe is a "
            "per-carrier metadata CSV -- this carrier needs its own dedicated loader"
        )
    entry = lock_entry(lock, descriptor.lock_key)
    carrier_dir = asset_dir(lock, descriptor.lock_key, root)
    subdir = str(entry["local_subdir"]).rstrip("/")
    columns = descriptor.metadata_columns
    rows = _metadata_rows(carrier_dir / descriptor.metadata_filename, columns.id_column)
    media_dir = carrier_dir / descriptor.media_subdir
    extension = descriptor.media_extension
    media_ids = {
        path.name[: -len(extension)]
        for path in media_dir.glob(f"*{extension}")
        if path.is_file()
    }
    if media_ids != set(rows):
        raise LoaderError(
            f"{descriptor.lock_key} media/metadata identity drift: "
            f"media_only={sorted(media_ids - set(rows))[:5]} "
            f"metadata_only={sorted(set(rows) - media_ids)[:5]}"
        )
    samples = []
    for sample_id in sorted(rows):
        row = rows[sample_id]
        samples.append(
            SampleRef(
                carrier_lock_key=descriptor.lock_key,
                sample_id=sample_id,
                media_relpath=f"{subdir}/{descriptor.media_subdir}/{sample_id}{extension}",
                audio_seconds=_float_field(row, columns.duration_column, sample_id),
                sample_rate_hz=int(_float_field(row, columns.sample_rate_column, sample_id)),
            )
        )
    return samples


def load_earnings22(lock: Mapping[str, object], root: Path) -> list[SampleRef]:
    """All 125 Earnings22 samples, sorted by sample id, identity-checked against media."""

    return load_carrier(EARNINGS22_ORIGINAL, lock, root)


def load_earnings21(lock: Mapping[str, object], root: Path) -> list[SampleRef]:
    """All Earnings21 samples, sorted by sample id, identity-checked against media."""

    return load_carrier(EARNINGS21_ORIGINAL, lock, root)


def earnings22_subset10_ids(lock: Mapping[str, object], root: Path) -> list[str]:
    """The upstream-curated Earnings22 ten-call subset (deterministic, not hand-picked)."""

    carrier_dir = asset_dir(lock, "earnings22-original", root)
    subset_dir = carrier_dir / "subset10" / "media"
    if not subset_dir.is_dir():
        raise LoaderError(f"earnings22 subset10 media directory missing: {subset_dir}")
    ids = sorted(
        path.name[: -len(".mp3")]
        for path in subset_dir.iterdir()
        # is_file() follows symlinks, so a dangling subset symlink fails closed here
        # with the count error instead of silently shrinking the selection.
        if path.name.endswith(".mp3") and path.is_file()
    )
    if len(ids) != 10:
        raise LoaderError(f"earnings22 subset10 must name exactly 10 calls, got {len(ids)}")
    return ids


def materialize(sample: SampleRef, root: Path) -> MaterializedSample:
    """Re-measure the sample's media bytes under the controlled root (fail-closed)."""

    media = Path(root) / sample.media_relpath
    if not media.is_file():
        raise LoaderError(f"media missing for {sample.sample_id}: {media}")
    fact: FileFact = hash_file(media)
    return MaterializedSample(ref=sample, media_bytes=fact.bytes, media_sha256=fact.sha256)
