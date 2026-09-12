"""Prepare full-coverage speech queries through the shared immutable cache."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from .preparation import (
    PreparationError,
    canonical_bytes,
    digest,
    hash_stable_file,
    load_artifact,
    prepare_artifact,
)

KIND = "speech-query-segment-vectors-v1"
SEGMENT_KIND = "speech-query-segment-vector-v1"
SCHEMA = "saea-speech-query-segment-vectors-v1"
_REQUIRED = {
    "id",
    "media_relpath",
    "audio_sha256",
    "source_frames",
    "source_sample_rate_hz",
}
_ALLOWED = _REQUIRED | {"channels", "format", "subtype"}


def _positive_int(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreparationError(f"{label} must be a positive integer")
    return value


def _duration(value, label, *, zero=False):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (not zero and value == 0)
    ):
        raise PreparationError(f"{label} must be a finite valid duration")
    return float(value)


def segment_plan(
    frame_count: int,
    sample_rate_hz: int,
    *,
    max_seconds: float = 120.0,
    overlap_seconds: float = 8.0,
) -> tuple[dict[str, int], ...]:
    """Keep original frame indices, a fixed stride and the complete final tail."""
    frames = _positive_int(frame_count, "frame_count")
    rate = _positive_int(sample_rate_hz, "sample_rate_hz")
    width_seconds = _duration(max_seconds, "max_seconds")
    overlap = _duration(overlap_seconds, "overlap_seconds", zero=True)
    width = math.floor(width_seconds * rate)
    overlap_frames = math.floor(overlap * rate)
    if width < 1 or overlap >= width_seconds or overlap_frames >= width:
        raise PreparationError("overlap must be smaller than a positive window")
    result = []
    start = 0
    while True:
        end = min(start + width, frames)
        result.append({"start_frame": start, "end_frame": end})
        if end == frames:
            break
        start += width - overlap_frames
    return tuple(result)


def _verified_rows(rows, data_root):
    """Verify the complete media-only inventory before the first encoder call."""
    import soundfile

    if not isinstance(rows, (list, tuple)) or not rows:
        raise PreparationError("speech query roster must be a non-empty sequence")
    root = Path(data_root).resolve()
    seen = set()
    verified = []
    checked_paths = {}
    for row in rows:
        if not isinstance(row, Mapping) or not _REQUIRED <= set(row) <= _ALLOWED:
            raise PreparationError("speech query row must contain media-only fields")
        sample_id = row["id"]
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen:
            raise PreparationError(
                "speech query sample IDs must be non-empty and unique"
            )
        seen.add(sample_id)
        sha = row["audio_sha256"]
        if (
            not isinstance(sha, str)
            or len(sha) != 64
            or set(sha) - set("0123456789abcdef")
        ):
            raise PreparationError("audio_sha256 must be lowercase SHA256")
        rel = row["media_relpath"]
        if (
            not isinstance(rel, str)
            or not rel
            or "\\" in rel
            or Path(rel).is_absolute()
            or ".." in Path(rel).parts
        ):
            raise PreparationError("speech query media path must be confined")
        path = (root / rel).resolve()
        if not path.is_relative_to(root):
            raise PreparationError("speech query media escapes data_root")
        frames = _positive_int(row["source_frames"], "source_frames")
        rate = _positive_int(row["source_sample_rate_hz"], "source_sample_rate_hz")
        if path not in checked_paths:
            _size, actual_sha, fingerprint = hash_stable_file(
                path, "speech query source"
            )
            try:
                info = soundfile.info(path)
            except (OSError, RuntimeError) as error:
                raise PreparationError(
                    "speech query media header is unreadable"
                ) from error
            checked_paths[path] = actual_sha, fingerprint, info
        actual_sha, fingerprint, info = checked_paths[path]
        if actual_sha != sha or info.frames != frames or info.samplerate != rate:
            raise PreparationError("speech query source hash or frame geometry changed")
        for field in ("channels", "format", "subtype"):
            if field in row and row[field] != getattr(info, field):
                raise PreparationError(f"speech query source {field} changed")
        verified.append(
            {
                "id": sample_id,
                "media_relpath": rel,
                "audio_sha256": sha,
                "source_frames": frames,
                "source_sample_rate_hz": rate,
                "media_path": str(path),
                "verified_fingerprint": fingerprint,
            }
        )
    return tuple(sorted(verified, key=lambda row: row["id"]))


def _checked_vector(value, dimension):
    if not isinstance(value, (list, tuple)) or len(value) != dimension:
        raise PreparationError("encoder vector has the wrong dimension")
    if any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
        for x in value
    ):
        raise PreparationError("encoder vector must contain finite numbers")
    values = [float(x) for x in value]
    if not any(values):
        raise PreparationError("encoder vector must be nonzero")
    return values


def prepare_speech_query_vectors(
    path: Path,
    *,
    rows: Sequence[Mapping[str, object]],
    data_root: Path,
    cache_root: Path,
    encoder: Callable[[Mapping[str, object]], Sequence[float]],
    encoder_identity: Mapping[str, object],
    protocol_id: str,
    dimension: int,
    max_seconds: float = 120.0,
    overlap_seconds: float = 8.0,
    prepare_sources: Callable[[Sequence[Mapping[str, object]]], None] | None = None,
) -> dict[str, object]:
    """Cache every spent segment separately; never replay an ambiguous contact."""
    dimension = _positive_int(dimension, "dimension")
    if not isinstance(protocol_id, str) or not protocol_id.strip():
        raise PreparationError("protocol_id must be non-empty")
    if not isinstance(encoder_identity, Mapping) or not encoder_identity:
        raise PreparationError("encoder_identity must be a non-empty binding")
    try:
        canonical_bytes(encoder_identity)
    except (TypeError, ValueError) as error:
        raise PreparationError(
            "encoder_identity must be finite canonical JSON"
        ) from error
    verified = _verified_rows(rows, data_root)
    plans = {
        row["id"]: segment_plan(
            row["source_frames"],
            row["source_sample_rate_hz"],
            max_seconds=max_seconds,
            overlap_seconds=overlap_seconds,
        )
        for row in verified
    }
    geometry = {
        "max_seconds": float(max_seconds),
        "overlap_seconds": float(overlap_seconds),
        "boundary_policy": "fixed-stride-complete-final-tail-v1",
    }
    inputs = {
        "encoder_identity": dict(encoder_identity),
        "protocol_id": protocol_id,
        "dimension": dimension,
        "geometry": geometry,
        "sources": [{k: r[k] for k in sorted(_REQUIRED)} for r in verified],
    }
    if Path(path).exists():
        artifact = prepare_artifact(
            path,
            kind=KIND,
            inputs=inputs,
            producer=lambda: None,
            contact_class="model-free",
        )
        output = load_artifact(
            path, expected_sha256=artifact["sha256"], kind=KIND, inputs=inputs
        )
        return {
            "artifact": {
                "path": artifact["path"],
                "sha256": artifact["sha256"],
                "output": output,
            },
            "accounting": {
                "encoder_calls": 0,
                "cache_hits": output["unique_span_count"],
                "deduplicated_references": 0,
            },
        }
    if prepare_sources is not None:
        prepare_sources(
            [dict(row, **span) for row in verified for span in plans[row["id"]]]
        )
    prepared = {}
    result_rows = []
    accounting = {"encoder_calls": 0, "cache_hits": 0, "deduplicated_references": 0}
    for row in verified:
        segments = []
        for span in plans[row["id"]]:
            source = {
                k: row[k]
                for k in ("audio_sha256", "source_frames", "source_sample_rate_hz")
            } | span
            binding = {
                "source": source,
                "encoder_identity": dict(encoder_identity),
                "protocol_id": protocol_id,
                "dimension": dimension,
                "geometry": geometry,
            }
            segment_id = digest(binding)
            if segment_id not in prepared:
                called = False

                def produce(row=row, source=source, segment_id=segment_id):
                    nonlocal called
                    called = True
                    accounting["encoder_calls"] += 1
                    vector = _checked_vector(encoder(dict(row, **source)), dimension)
                    return {"id": segment_id, "vectors": {"content": vector}}

                record = prepare_artifact(
                    Path(cache_root) / (segment_id + ".json"),
                    kind=SEGMENT_KIND,
                    inputs=binding,
                    producer=produce,
                    contact_class="encoder",
                )
                if not called:
                    accounting["cache_hits"] += 1
                saved = load_artifact(
                    Path(record["path"]),
                    expected_sha256=record["sha256"],
                    kind=SEGMENT_KIND,
                    inputs=binding,
                )
                if (
                    set(saved) != {"id", "vectors"}
                    or saved["id"] != segment_id
                    or set(saved["vectors"]) != {"content"}
                ):
                    raise PreparationError(
                        "cached speech segment output binding changed"
                    )
                _checked_vector(saved["vectors"]["content"], dimension)
                prepared[segment_id] = saved
            else:
                accounting["deduplicated_references"] += 1
            segments.append({**prepared[segment_id], **span})
        result_rows.append(
            {
                k: row[k]
                for k in (
                    "id",
                    "audio_sha256",
                    "source_frames",
                    "source_sample_rate_hz",
                )
            }
            | {"segments": segments}
        )
    output = {
        "schema": SCHEMA,
        "rows": result_rows,
        "unique_span_count": len(prepared),
        "encoder_identity": dict(encoder_identity),
        "protocol_id": protocol_id,
        "dimension": dimension,
        "geometry": geometry,
    }
    # GPU contacts are already sealed per segment. Publishing the assembled
    # index is model-free, so an interrupted publication can reuse those seals.
    artifact = prepare_artifact(
        path,
        kind=KIND,
        inputs=inputs,
        producer=lambda: output,
        contact_class="model-free",
    )
    return {
        "artifact": {
            "path": artifact["path"],
            "sha256": artifact["sha256"],
            "output": output,
        },
        "accounting": accounting,
    }
