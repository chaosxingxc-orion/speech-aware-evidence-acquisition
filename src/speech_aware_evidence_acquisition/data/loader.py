"""Deterministic, boundary-safe carrier sample loading (E0 D4 substrate, reused at R0).

A loader never reads transcript, annotation or context *content*; it resolves sample
identity, media location, duration and sample rate from the carrier's metadata layer.
Everything a loader exposes to the runtime side passes
:func:`speech_aware_evidence_acquisition.contracts.assert_information_boundary`
before it is returned — gold and reference layers exist on disk next to the media,
and this module is the choke point that keeps them out of runtime payloads.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..contracts import assert_information_boundary
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


def load_earnings22(lock: Mapping[str, object], root: Path) -> list[SampleRef]:
    """All 125 Earnings22 samples, sorted by sample id, identity-checked against media."""

    entry = lock_entry(lock, "earnings22-original")
    carrier_dir = asset_dir(lock, "earnings22-original", root)
    subdir = str(entry["local_subdir"]).rstrip("/")
    rows = _metadata_rows(carrier_dir / "metadata.csv", "File ID")
    media_dir = carrier_dir / "media"
    media_ids = {
        path.name[: -len(".mp3")] for path in media_dir.glob("*.mp3") if path.is_file()
    }
    if media_ids != set(rows):
        raise LoaderError(
            "earnings22 media/metadata identity drift: "
            f"media_only={sorted(media_ids - set(rows))[:5]} "
            f"metadata_only={sorted(set(rows) - media_ids)[:5]}"
        )
    samples = []
    for sample_id in sorted(rows):
        row = rows[sample_id]
        samples.append(
            SampleRef(
                carrier_lock_key="earnings22-original",
                sample_id=sample_id,
                media_relpath=f"{subdir}/media/{sample_id}.mp3",
                audio_seconds=_float_field(row, "File Length (seconds)", sample_id),
                sample_rate_hz=int(_float_field(row, "Sampling Rate (Hz)", sample_id)),
            )
        )
    return samples


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
