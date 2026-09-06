"""ESB released-array duration check (``SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1``).

Section 3 of ``docs/readiness/2026-09-06-e22-dev-boundary-exact-v1-preregistration.md``
named this check, priced it at zero model contacts, and deliberately did not
take it. It is taken here, under the owner decision of 2026-09-06, because the
boundary-exact cell's binding claim rule turns on the answer.

**The question.** The 2026-09-06 clip-boundary audit established that this
study's slicer is exact -- it cuts the parent PCM at the published
``start_ts``/``end_ts`` verbatim, with zero padding -- and that the published
segments overlap anyway: 4,681 of 6,028 adjacent dev pairs (77.7 %), hard
capped at 0.1804 s, 668.7 s of dev audio delivered twice. The published 9.79 /
12.3 systems do not consume this study's clips; they consume the ESB release's
OWN per-utterance ``audio`` arrays. If those arrays are cut at the same two
columns, the published systems heard the same onsets, the overlap is not a
DIFFERENCE between the two systems, and a boundary-exact number is not
comparable to them. If the released arrays are tight, the boundary-exact cut is
the protocol-faithful one and the prohibition lifts.

**What is measured, and nothing beyond it.** Per utterance: the released
array's duration, taken from the RIFF/WAVE container header of the encoded blob
(sampling rate, channel count, bits per sample, ``data`` chunk byte count ->
frames), against the published ``end_ts - start_ts``; the distribution of that
difference; the implied per-side pad if the difference were a constant symmetric
pad; and the adjacent-pair geometry of the released arrays, each anchored at its
own published ``start_ts`` and extended by its own measured duration.

**No text, no audio content, no outputs.** The parquet ``sentence`` column is
never projected. The JSONL ``sentence`` field is discarded inside the parse
scope by :func:`load_test_segment_table` and never reaches a data structure, a
receipt or a log line. Of the ``audio.bytes`` leaf only the blob's byte LENGTH
and its container header are taken: no sample is decoded, no blob is
materialized as an object, written, hashed or retained. No sealed test output,
hypothesis, score or reference layer is opened. Model-free by construction: no
frozen core, tokenizer, embedder, retriever, scorer, network or GPU contact.

**Identity.** The shard SHA-256 values are INHERITED from the committed
2026-09-04 segment-table receipt (``locally_rehashed: true``,
``local_matches_lfs_oid: true``) rather than recomputed, because this row is
forbidden to hash the audio bytes. Identity is asserted instead from that
receipt's pinned byte sizes plus a row-for-row agreement of
``(id, source_id, segment_id, start_ts, end_ts)`` with the cryptographically
pinned ``segments-test.jsonl``, which is re-hashed on every load.

Nothing here licenses a fix. It answers one comparability question and writes
receipts; re-cutting any clip still needs its own owner decision and its own
exposure row.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ANALYSIS_VERSION = "saea-e22-esb-array-durations-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-ESB-ARRAY-DURATIONS-V1"

#: The committed receipt that pins the four ESB TEST parquet shards (paths,
#: byte sizes, git-LFS oids, the local re-hash made on 2026-09-04) and the
#: extracted ``segments-test.jsonl`` table with its own SHA-256.
SEGMENT_TABLE_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-e22-esb-shortform-alignment-400-v1/segment-table/segment-table-receipt.json"
)

#: The parquet leaves this check is allowed to project. ``audio.bytes`` is a
#: LEAF projection: the sibling ``audio.path`` and the whole ``sentence``
#: column stay on disk and are never decompressed.
PROJECTED_COLUMNS: tuple[str, ...] = (
    "source_id",
    "segment_id",
    "start_ts",
    "end_ts",
    "id",
    "audio.bytes",
)

#: Columns that must never be projected, asserted rather than assumed.
FORBIDDEN_COLUMNS: tuple[str, ...] = ("sentence",)

#: How many leading bytes of each blob are inspected. The canonical RIFF/WAVE
#: header is 44 bytes; 4,096 leaves room for a release that carries LIST or
#: other ancillary chunks before ``data``, and the parser REFUSES rather than
#: guesses if ``data`` is not reached inside the prefix.
HEADER_PREFIX_BYTES = 4096

#: A released array counts as SPAN-FAITHFUL when its duration matches
#: ``end_ts - start_ts`` to within this tolerance. Fixed before the numbers, and
#: derived rather than chosen: one sample frame at 16 kHz is 6.25e-05 s, and the
#: published boundaries are float32, whose ulp at a 4,000 s offset is about
#: 4.9e-04 s, so a difference of a millisecond is already generous for "the same
#: span". It is also two orders of magnitude below the ~0.09 s per-side pad that
#: would be needed to explain the measured neighbour overlap as padding, so the
#: verdict cannot turn on the tolerance.
SPAN_TOLERANCE_SECONDS = 1.0e-3

#: Verdict thresholds, fixed here before any shard is read.
FAITHFUL_SHARE_FOR_OVERLAP_VERDICT = 0.99
OVERLAP_SHARE_SLACK = 0.01
TIGHT_OVERLAP_SHARE = 0.01

#: Buckets for the duration difference (seconds). One frame at 16 kHz is
#: 6.25e-05 s, so the innermost pair of edges separates "identical to the
#: container's own resolution" from everything else.
DIFFERENCE_BUCKET_EDGES: tuple[float, ...] = (
    -0.09,
    -0.01,
    -0.001,
    -6.25e-05,
    6.25e-05,
    0.001,
    0.01,
    0.09,
)

#: Buckets for the adjacent-pair gap (seconds), byte-identical to the ones the
#: clip-boundary audit used, so the two geometries are read off the same ruler.
GAP_BUCKET_EDGES: tuple[float, ...] = (
    -0.18,
    -0.16,
    -0.12,
    -0.08,
    -0.04,
    0.0,
    0.25,
    1.0,
    4.0,
)

PER_UTTERANCE_COLUMNS: tuple[str, ...] = (
    "sample_id",
    "call",
    "segment_index",
    "start_seconds",
    "end_seconds",
    "published_seconds",
    "sample_rate",
    "channels",
    "bits_per_sample",
    "container_bytes",
    "data_bytes",
    "frames",
    "array_seconds",
    "difference_seconds",
    "implied_pad_seconds",
    "span_faithful",
    "published_gap_next_seconds",
    "released_gap_next_seconds",
    "centered_gap_next_seconds",
)


class ArrayDurationError(RuntimeError):
    """A refusal: an identity drift, a forbidden column, or an unparsable container."""


# ---------------------------------------------------------------------------
# The container header
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WavHeader:
    """What the RIFF/WAVE header of one released blob says about its length.

    Every field comes from the header's own declarations. No sample is read:
    ``frames`` is ``data_bytes // (channels * bits_per_sample // 8)``, which is
    exact for uncompressed PCM and is why :func:`parse_wav_header` refuses any
    other format tag rather than guessing a duration for it.
    """

    audio_format: int
    channels: int
    sample_rate: int
    bits_per_sample: int
    data_bytes: int
    container_bytes: int

    @property
    def frame_bytes(self) -> int:
        return self.channels * (self.bits_per_sample // 8)

    @property
    def frames(self) -> int:
        return self.data_bytes // self.frame_bytes

    @property
    def duration_seconds(self) -> float:
        return self.frames / float(self.sample_rate)


def parse_wav_header(prefix: bytes, container_bytes: int) -> WavHeader:
    """Parse the RIFF/WAVE header of one blob from its leading bytes.

    ``prefix`` is the first :data:`HEADER_PREFIX_BYTES` bytes of the blob and
    ``container_bytes`` its full length. The parser walks the chunk list to
    ``data`` and refuses -- never repairs -- a container it cannot read.
    """

    if len(prefix) < 44:
        raise ArrayDurationError(
            f"blob prefix is {len(prefix)} bytes; a RIFF/WAVE header needs at least 44"
        )
    if prefix[0:4] != b"RIFF" or prefix[8:12] != b"WAVE":
        raise ArrayDurationError(
            f"blob does not start with a RIFF/WAVE header: {prefix[0:12]!r}"
        )
    riff_size = struct.unpack_from("<I", prefix, 4)[0]
    if riff_size + 8 != container_bytes:
        raise ArrayDurationError(
            f"RIFF size {riff_size} + 8 does not match the blob's {container_bytes} bytes"
        )

    fmt: tuple[int, int, int, int] | None = None
    offset = 12
    while offset + 8 <= len(prefix):
        chunk_id = prefix[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", prefix, offset + 4)[0]
        body = offset + 8
        if chunk_id == b"fmt ":
            if body + 16 > len(prefix):
                raise ArrayDurationError("fmt chunk runs past the inspected prefix")
            audio_format, channels, sample_rate = struct.unpack_from("<HHI", prefix, body)
            bits_per_sample = struct.unpack_from("<H", prefix, body + 14)[0]
            fmt = (audio_format, channels, sample_rate, bits_per_sample)
        elif chunk_id == b"data":
            if fmt is None:
                raise ArrayDurationError("data chunk reached before any fmt chunk")
            audio_format, channels, sample_rate, bits_per_sample = fmt
            if audio_format != 1:
                raise ArrayDurationError(
                    f"container declares format tag {audio_format}, not uncompressed PCM; "
                    "a duration cannot be taken from its byte count without decoding it"
                )
            if channels <= 0 or sample_rate <= 0 or bits_per_sample % 8 != 0:
                raise ArrayDurationError(
                    f"unusable fmt chunk: channels={channels}, rate={sample_rate}, "
                    f"bits={bits_per_sample}"
                )
            available = container_bytes - body
            if chunk_size > available:
                raise ArrayDurationError(
                    f"data chunk declares {chunk_size} bytes but only {available} follow it"
                )
            header = WavHeader(
                audio_format=audio_format,
                channels=channels,
                sample_rate=sample_rate,
                bits_per_sample=bits_per_sample,
                data_bytes=chunk_size,
                container_bytes=container_bytes,
            )
            if chunk_size % header.frame_bytes != 0:
                raise ArrayDurationError(
                    f"data chunk of {chunk_size} bytes is not a whole number of "
                    f"{header.frame_bytes}-byte frames"
                )
            return header
        offset = body + chunk_size + (chunk_size % 2)
    raise ArrayDurationError(
        f"no data chunk inside the first {len(prefix)} bytes of the container"
    )


# ---------------------------------------------------------------------------
# One released utterance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReleasedArray:
    """One published ESB utterance: its boundaries, and its released duration."""

    sample_id: str
    call: str
    segment_index: int
    start_seconds: float
    end_seconds: float
    header: WavHeader

    @property
    def published_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def array_seconds(self) -> float:
        return self.header.duration_seconds

    @property
    def difference_seconds(self) -> float:
        """``array - published``. Positive means the release carries MORE audio."""

        return self.array_seconds - self.published_seconds

    @property
    def implied_pad_seconds(self) -> float:
        """The per-side pad the difference implies, IF it is a symmetric pad."""

        return self.difference_seconds / 2.0

    @property
    def span_faithful(self) -> bool:
        return abs(self.difference_seconds) <= SPAN_TOLERANCE_SECONDS


@dataclass(frozen=True)
class AdjacentPair:
    """One adjacent pair of published segments inside one call."""

    call: str
    left_id: str
    right_id: str
    published_gap_seconds: float
    released_gap_seconds: float
    centered_gap_seconds: float


# ---------------------------------------------------------------------------
# Landed inputs
# ---------------------------------------------------------------------------


def load_receipt(repo_root: Path) -> Mapping[str, Any]:
    """The committed 2026-09-04 segment-table receipt."""

    path = Path(repo_root) / SEGMENT_TABLE_RECEIPT_RELPATH
    if not path.is_file():
        raise ArrayDurationError(f"segment-table receipt is missing at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_test_segment_table(
    root: Path, receipt: Mapping[str, Any]
) -> dict[str, dict[str, Any]]:
    """The ESB TEST segment table, re-hashed against its receipt, WITHOUT text.

    ``sentence`` is the gold reference. It is dropped inside this function's
    parse scope: the returned rows carry identifiers and timestamps only, so no
    caller -- and no receipt this module writes -- can reach the text.
    """

    table = receipt["extracted_table"]
    path = Path(root) / str(table["relpath"])
    payload = path.read_bytes()
    measured = hashlib.sha256(payload).hexdigest()
    if measured != table["sha256"]:
        raise ArrayDurationError(
            f"test segment table identity drift: the receipt pins "
            f"{str(table['sha256'])[:12]}..., {path} now hashes to {measured[:12]}..."
        )
    rows: dict[str, dict[str, Any]] = {}
    for line in payload.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        parsed = json.loads(line)
        sample_id = str(parsed["id"])
        if sample_id in rows:
            raise ArrayDurationError(f"test segment table repeats sample {sample_id!r}")
        rows[sample_id] = {
            "id": sample_id,
            "source_id": str(parsed["source_id"]),
            "segment_id": int(str(parsed["segment_id"])),
            "start_ts": float(parsed["start_ts"]),
            "end_ts": float(parsed["end_ts"]),
        }
    if len(rows) != int(table["rows"]):
        raise ArrayDurationError(
            f"test segment table holds {len(rows)} rows, the receipt pins {table['rows']}"
        )
    return rows


def resolve_shards(root: Path, receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The four locally materialized TEST shards, size-checked against the receipt.

    The shard SHA-256 is inherited from the receipt's own 2026-09-04 local
    re-hash rather than recomputed: this row may not hash the audio bytes.
    """

    resolved: list[dict[str, Any]] = []
    for entry in receipt["parquet_files"]:
        path = Path(root) / str(entry["local_relpath"])
        if not path.is_file():
            raise ArrayDurationError(f"pinned test shard is not materialized at {path}")
        size = path.stat().st_size
        if size != int(entry["bytes"]):
            raise ArrayDurationError(
                f"{path} is {size} bytes; the receipt pins {entry['bytes']}"
            )
        if not entry.get("locally_rehashed") or not entry.get("local_matches_lfs_oid"):
            raise ArrayDurationError(
                f"{path} was never locally re-hashed against its published oid; this row "
                "inherits that digest and cannot recompute it"
            )
        resolved.append(
            {
                "path": path,
                "relpath": str(entry["local_relpath"]),
                "bytes": size,
                "sha256_inherited": str(entry["sha256"]),
            }
        )
    if not resolved:
        raise ArrayDurationError("the receipt pins no parquet shards")
    return resolved


def read_shard_headers(path: Path) -> list[dict[str, Any]]:
    """Per row of one shard: identifiers, boundaries, blob length, blob header.

    pyarrow is imported here rather than at module scope, so importing this
    package still costs nothing. The read is a LEAF projection: ``audio.bytes``
    only, so ``audio.path`` and ``sentence`` are never decompressed. Each row
    group is released before the next is read, and the only values taken out of
    it are the blob's byte length and its :data:`HEADER_PREFIX_BYTES`-byte
    container prefix -- both computed inside Arrow, never as Python bytes over
    the whole column.
    """

    import pyarrow.compute as pc  # noqa: PLC0415 - keep the package import light
    import pyarrow.parquet as pq  # noqa: PLC0415 - keep the package import light

    parquet = pq.ParquetFile(str(path))
    for forbidden in FORBIDDEN_COLUMNS:
        if forbidden in PROJECTED_COLUMNS:
            raise ArrayDurationError(f"column {forbidden!r} must never be projected")
    rows: list[dict[str, Any]] = []
    for group in range(parquet.metadata.num_row_groups):
        table = parquet.read_row_group(group, columns=list(PROJECTED_COLUMNS))
        if set(table.column_names) & set(FORBIDDEN_COLUMNS):
            raise ArrayDurationError(
                f"projection returned forbidden columns: {sorted(set(table.column_names))}"
            )
        blobs = table.column("audio").combine_chunks().field("bytes")
        lengths = pc.binary_length(blobs).to_pylist()
        prefixes = pc.binary_slice(blobs, 0, HEADER_PREFIX_BYTES).to_pylist()
        ids = table.column("id").to_pylist()
        sources = table.column("source_id").to_pylist()
        segments = table.column("segment_id").to_pylist()
        starts = table.column("start_ts").to_pylist()
        ends = table.column("end_ts").to_pylist()
        for index in range(table.num_rows):
            rows.append(
                {
                    "id": str(ids[index]),
                    "source_id": str(sources[index]),
                    "segment_id": int(str(segments[index])),
                    "start_ts": float(starts[index]),
                    "end_ts": float(ends[index]),
                    "container_bytes": int(lengths[index]),
                    "header": parse_wav_header(prefixes[index], int(lengths[index])),
                }
            )
        del prefixes, lengths, blobs, table
    return rows


def build_arrays(
    shard_rows: Iterable[Mapping[str, Any]], segments: Mapping[str, Mapping[str, Any]]
) -> dict[str, ReleasedArray]:
    """Join the shards' headers to the hash-pinned table, asserting both agree.

    The boundaries used downstream are the JSONL's -- the cryptographically
    pinned copy -- and every shard row must reproduce them exactly, which is
    what stands in for a shard digest this row may not recompute.
    """

    arrays: dict[str, ReleasedArray] = {}
    for row in shard_rows:
        sample_id = str(row["id"])
        if sample_id in arrays:
            raise ArrayDurationError(f"sample {sample_id!r} appears in two shard rows")
        pinned = segments.get(sample_id)
        if pinned is None:
            raise ArrayDurationError(
                f"shard row {sample_id!r} is absent from the hash-pinned segment table"
            )
        for field in ("source_id", "segment_id", "start_ts", "end_ts"):
            if row[field] != pinned[field]:
                raise ArrayDurationError(
                    f"{sample_id}: shard {field}={row[field]!r} against pinned "
                    f"{pinned[field]!r}"
                )
        arrays[sample_id] = ReleasedArray(
            sample_id=sample_id,
            call=str(pinned["source_id"]),
            segment_index=int(pinned["segment_id"]),
            start_seconds=float(pinned["start_ts"]),
            end_seconds=float(pinned["end_ts"]),
            header=row["header"],
        )
    missing = sorted(set(segments) - set(arrays))
    if missing:
        raise ArrayDurationError(
            f"{len(missing)} pinned segments have no shard row, first {missing[0]!r}"
        )
    return arrays


# ---------------------------------------------------------------------------
# Distributions
# ---------------------------------------------------------------------------


def _percentile(ordered: Sequence[float], point: float) -> float:
    if not ordered:
        raise ArrayDurationError("percentile of an empty sequence")
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * point / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[int(position)])
    weight = position - lower
    return float(ordered[lower] * (1.0 - weight) + ordered[upper] * weight)


def _bucket_label(value: float, edges: Sequence[float], digits: int) -> str:
    if value <= edges[0]:
        return f"<= {edges[0]:.{digits}g}"
    for lower, upper in zip(edges, edges[1:]):
        if lower < value <= upper:
            return f"({lower:.{digits}g}, {upper:.{digits}g}]"
    return f"> {edges[-1]:.{digits}g}"


def _describe(
    values: Sequence[float], *, edges: Sequence[float], digits: int
) -> dict[str, Any]:
    if not values:
        raise ArrayDurationError("cannot describe an empty distribution")
    ordered = sorted(values)
    buckets: dict[str, int] = {}
    for value in values:
        label = _bucket_label(value, edges, digits)
        buckets[label] = buckets.get(label, 0) + 1
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    return {
        "n": len(values),
        "min": ordered[0],
        "max": ordered[-1],
        "mean": mean,
        "stdev": math.sqrt(variance),
        "percentiles": {
            str(point): _percentile(ordered, point)
            for point in (1, 5, 25, 50, 75, 95, 99)
        },
        "buckets": buckets,
        "bucket_edges": list(edges),
    }


def difference_distribution(arrays: Mapping[str, ReleasedArray]) -> dict[str, Any]:
    """How far each released array's duration sits from ``end_ts - start_ts``."""

    differences = [array.difference_seconds for array in arrays.values()]
    described = _describe(differences, edges=DIFFERENCE_BUCKET_EDGES, digits=3)
    faithful = sum(1 for array in arrays.values() if array.span_faithful)
    frame_deltas = [
        array.header.frames - round(array.published_seconds * array.header.sample_rate)
        for array in arrays.values()
    ]
    delta_counts: dict[str, int] = {}
    for delta in frame_deltas:
        key = str(delta) if abs(delta) <= 4 else "beyond +-4"
        delta_counts[key] = delta_counts.get(key, 0) + 1
    outliers = sorted(
        (array for array in arrays.values() if not array.span_faithful),
        key=lambda array: abs(array.difference_seconds),
        reverse=True,
    )
    described.update(
        {
            "span_faithful": faithful,
            "span_faithful_share": faithful / len(arrays),
            "span_tolerance_seconds": SPAN_TOLERANCE_SECONDS,
            "not_span_faithful": [
                {
                    "sample_id": array.sample_id,
                    "call": array.call,
                    "segment_index": array.segment_index,
                    "published_seconds": array.published_seconds,
                    "array_seconds": array.array_seconds,
                    "difference_seconds": array.difference_seconds,
                    "sample_rate": array.header.sample_rate,
                }
                for array in outliers[:50]
            ],
            "not_span_faithful_listed": min(len(outliers), 50),
            "longer_than_published": sum(1 for value in differences if value > 0.0),
            "shorter_than_published": sum(1 for value in differences if value < 0.0),
            "exactly_equal": sum(1 for value in differences if value == 0.0),
            "frame_delta_counts": dict(sorted(delta_counts.items())),
            "implied_pad_seconds": {
                "median": _percentile(sorted(differences), 50) / 2.0,
                "mean": described["mean"] / 2.0,
                "max_absolute": max(abs(value) for value in differences) / 2.0,
            },
        }
    )
    return described


def adjacent_pairs(arrays: Mapping[str, ReleasedArray]) -> list[AdjacentPair]:
    """One entry per adjacent pair inside a call, in published segment order.

    Three gaps per pair, all signed, all in seconds, negative meaning OVERLAP:

    * ``published`` -- ``start_next - end_previous``, the geometry of the two
      float32 columns, which is what this study's own clips inherit;
    * ``released`` -- each released array ANCHORED AT ITS OWN ``start_ts`` and
      extended by its measured duration, i.e.
      ``start_next - (start_previous + array_seconds_previous)``;
    * ``centered`` -- the sensitivity reading, where each array is instead
      centred on its published span with a symmetric pad of
      ``difference / 2`` per side.
    """

    by_call: dict[str, list[ReleasedArray]] = {}
    for array in arrays.values():
        by_call.setdefault(array.call, []).append(array)
    pairs: list[AdjacentPair] = []
    for call, members in sorted(by_call.items()):
        ordered = sorted(members, key=lambda item: item.segment_index)
        for left, right in zip(ordered, ordered[1:]):
            pairs.append(
                AdjacentPair(
                    call=call,
                    left_id=left.sample_id,
                    right_id=right.sample_id,
                    published_gap_seconds=right.start_seconds - left.end_seconds,
                    released_gap_seconds=(
                        right.start_seconds - (left.start_seconds + left.array_seconds)
                    ),
                    centered_gap_seconds=(
                        (right.start_seconds - right.implied_pad_seconds)
                        - (left.end_seconds + left.implied_pad_seconds)
                    ),
                )
            )
    if not pairs:
        raise ArrayDurationError("no adjacent pairs; the population is empty")
    return pairs


def gap_distribution(gaps: Sequence[float]) -> dict[str, Any]:
    """The signed-gap distribution, on the clip-boundary audit's own buckets."""

    described = _describe(gaps, edges=GAP_BUCKET_EDGES, digits=3)
    negative = [value for value in gaps if value < 0.0]
    described.update(
        {
            "pairs": len(gaps),
            "overlapping_pairs": len(negative),
            "overlapping_share": len(negative) / len(gaps),
            "touching_pairs": sum(1 for value in gaps if value == 0.0),
            "separated_pairs": sum(1 for value in gaps if value > 0.0),
            "overlap_seconds_total": -sum(negative),
        }
    )
    return described


def per_call_overlap(pairs: Sequence[AdjacentPair]) -> dict[str, dict[str, Any]]:
    """The released-array overlap, one row per call, so no call hides inside a mean."""

    table: dict[str, dict[str, Any]] = {}
    for pair in pairs:
        entry = table.setdefault(
            pair.call,
            {"pairs": 0, "overlapping_pairs": 0, "overlap_seconds": 0.0},
        )
        entry["pairs"] += 1
        if pair.released_gap_seconds < 0.0:
            entry["overlapping_pairs"] += 1
            entry["overlap_seconds"] -= pair.released_gap_seconds
    for entry in table.values():
        entry["overlapping_share"] = entry["overlapping_pairs"] / entry["pairs"]
    return dict(sorted(table.items()))


def segment_id_coverage(arrays: Mapping[str, ReleasedArray]) -> dict[str, Any]:
    """Which published segment indices the release actually ships, per call.

    A by-product of the join, computed from identifiers this check already
    holds and costing no additional read. It exists because the 2026-09-04
    segment-table receipt records an UNEXPLAINED six-row gap between the
    2,735 rows the pinned table carries and the 2,741 the leaderboard config
    and the NeMo post both state. If the shipped rows are a proper subset of a
    contiguous index range, the size of the hole is decidable here.
    """

    by_call: dict[str, list[int]] = {}
    for array in arrays.values():
        by_call.setdefault(array.call, []).append(array.segment_index)
    calls: dict[str, dict[str, Any]] = {}
    missing_total = 0
    for call, indices in sorted(by_call.items()):
        present = set(indices)
        lowest, highest = min(present), max(present)
        missing = sorted(set(range(lowest, highest + 1)) - present)
        missing_total += len(missing)
        calls[call] = {
            "rows": len(indices),
            "min_index": lowest,
            "max_index": highest,
            "missing_indices": missing,
        }
    return {
        "by_call": calls,
        "rows": len(arrays),
        "missing_indices_total": missing_total,
        "rows_plus_missing": len(arrays) + missing_total,
    }


def container_profile(arrays: Mapping[str, ReleasedArray]) -> dict[str, Any]:
    """What the released containers are, aggregated. No sample is read."""

    shapes: dict[str, int] = {}
    by_call: dict[str, dict[str, int]] = {}
    for array in arrays.values():
        header = array.header
        key = (
            f"{header.sample_rate} Hz / {header.channels} ch / "
            f"{header.bits_per_sample} bit / format {header.audio_format}"
        )
        shapes[key] = shapes.get(key, 0) + 1
        call = by_call.setdefault(array.call, {})
        call[key] = call.get(key, 0) + 1
    return {
        "shapes": dict(sorted(shapes.items())),
        "shapes_by_call": {
            call: dict(sorted(counts.items())) for call, counts in sorted(by_call.items())
        },
        "distinct_shapes": len(shapes),
        "array_seconds_total": sum(array.array_seconds for array in arrays.values()),
        "published_seconds_total": sum(
            array.published_seconds for array in arrays.values()
        ),
        "data_bytes_total": sum(array.header.data_bytes for array in arrays.values()),
    }


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


def verdict(
    differences: Mapping[str, Any],
    released: Mapping[str, Any],
    published: Mapping[str, Any],
) -> dict[str, Any]:
    """RELEASED ARRAYS OVERLAP / TIGHT / MIXED, on rules fixed before the read.

    * **RELEASED ARRAYS OVERLAP** -- at least
      :data:`FAITHFUL_SHARE_FOR_OVERLAP_VERDICT` of utterances are span-faithful
      within :data:`SPAN_TOLERANCE_SECONDS`, AND the released arrays' own
      adjacent-pair overlap share is at least the published-timestamp share
      minus :data:`OVERLAP_SHARE_SLACK`. The release reproduces the published
      geometry, so the published systems heard the same onsets.
    * **TIGHT** -- fewer than :data:`TIGHT_OVERLAP_SHARE` of adjacent pairs
      overlap once each array is placed at its own start. The release cut the
      overlap out, and this study's cut is the deviation.
    * **MIXED** -- anything else, which is a finding in its own right and is
      reported as one rather than rounded to either pole.
    """

    faithful_share = float(differences["span_faithful_share"])
    released_share = float(released["overlapping_share"])
    published_share = float(published["overlapping_share"])
    if (
        faithful_share >= FAITHFUL_SHARE_FOR_OVERLAP_VERDICT
        and released_share >= published_share - OVERLAP_SHARE_SLACK
    ):
        label = "RELEASED ARRAYS OVERLAP"
    elif released_share < TIGHT_OVERLAP_SHARE:
        label = "TIGHT"
    else:
        label = "MIXED"
    return {
        "verdict": label,
        "span_faithful_share": faithful_share,
        "released_overlapping_share": released_share,
        "published_overlapping_share": published_share,
        "thresholds": {
            "span_tolerance_seconds": SPAN_TOLERANCE_SECONDS,
            "faithful_share_for_overlap_verdict": FAITHFUL_SHARE_FOR_OVERLAP_VERDICT,
            "overlap_share_slack": OVERLAP_SHARE_SLACK,
            "tight_overlap_share": TIGHT_OVERLAP_SHARE,
        },
        "comparability": (
            "The published systems consume these arrays. They carry the published "
            "boundaries, so they carry the same neighbour overlap this study's cut "
            "carries, and a boundary-exact number changes the audio the protocol "
            "delivers: it stays incomparable to the published 9.79 / 12.3."
            if label == "RELEASED ARRAYS OVERLAP"
            else (
                "The released arrays do not carry the published overlap, so the "
                "boundary-exact cut is the protocol-faithful one and section 1.6's "
                "prohibition lifts."
                if label == "TIGHT"
                else "Neither pole holds; the comparability question stays open and "
                "the prohibition stands until it is settled."
            )
        ),
    }


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return ""
        return f"{value:.6f}"
    return str(value)


def per_utterance_table(
    arrays: Mapping[str, ReleasedArray], pairs: Sequence[AdjacentPair]
) -> str:
    """The per-utterance receipt, as CSV. Numbers and identifiers only -- no text."""

    by_left = {pair.left_id: pair for pair in pairs}
    lines = [",".join(PER_UTTERANCE_COLUMNS)]
    for sample_id in sorted(
        arrays, key=lambda key: (arrays[key].call, arrays[key].segment_index)
    ):
        array = arrays[sample_id]
        pair = by_left.get(sample_id)
        row = [
            array.sample_id,
            array.call,
            array.segment_index,
            array.start_seconds,
            array.end_seconds,
            array.published_seconds,
            array.header.sample_rate,
            array.header.channels,
            array.header.bits_per_sample,
            array.header.container_bytes,
            array.header.data_bytes,
            array.header.frames,
            array.array_seconds,
            array.difference_seconds,
            array.implied_pad_seconds,
            array.span_faithful,
            pair.published_gap_seconds if pair else None,
            pair.released_gap_seconds if pair else None,
            pair.centered_gap_seconds if pair else None,
        ]
        lines.append(",".join(_cell(value) for value in row))
    return "\n".join(lines) + "\n"


def _round(value: Any, digits: int = 9) -> Any:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if isinstance(value, int):
        return value
    return round(float(value), digits)


def _rounded(payload: Any, digits: int = 9) -> Any:
    if isinstance(payload, Mapping):
        return {key: _rounded(value, digits) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_rounded(value, digits) for value in payload]
    return _round(payload, digits)


def build_summary(
    *,
    arrays: Mapping[str, ReleasedArray],
    pairs: Sequence[AdjacentPair],
    shards: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> dict[str, Any]:
    """Everything this check measured, in one JSON-serialisable object."""

    differences = difference_distribution(arrays)
    released = gap_distribution([pair.released_gap_seconds for pair in pairs])
    published = gap_distribution([pair.published_gap_seconds for pair in pairs])
    centered = gap_distribution([pair.centered_gap_seconds for pair in pairs])
    calls = sorted({array.call for array in arrays.values()})
    non_monotonic = sum(
        1
        for pair in pairs
        if arrays[pair.right_id].start_seconds < arrays[pair.left_id].start_seconds
    )
    summary = {
        "schema": "saea-e22-esb-array-durations-summary-v1",
        "analysis_version": ANALYSIS_VERSION,
        "exposure_row": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "question": (
            "Are the ESB release's own per-utterance audio arrays cut at exactly "
            "[start_ts, end_ts], and do they therefore carry the same neighbour "
            "overlap this study's own clips carry?"
        ),
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
            "speech_seconds_delivered_to_any_service": 0,
            "outbound_connection_attempts": outbound_attempts,
            "outbound_connection_targets": list(outbound_targets),
        },
        "reads": {
            "text_columns_read": 0,
            "audio_samples_decoded": 0,
            "audio_blobs_written_or_hashed": 0,
            "sealed_outputs_opened": 0,
            "reference_layers_opened": 0,
            "projected_columns": list(PROJECTED_COLUMNS),
            "forbidden_columns": list(FORBIDDEN_COLUMNS),
            "header_prefix_bytes": HEADER_PREFIX_BYTES,
            "what_left_the_blob": (
                "the blob's byte length and its RIFF/WAVE container header only"
            ),
        },
        "population": {
            "utterances": len(arrays),
            "calls": len(calls),
            "call_ids": calls,
            "split": "ESB Earnings22 test (calibration-exposed 2026-09-04)",
            "touched_for": "durations only",
        },
        "identity": {
            "upstream": dict(receipt["upstream"]),
            "segment_table": dict(receipt["extracted_table"]),
            "shards": [
                {
                    "relpath": shard["relpath"],
                    "bytes": shard["bytes"],
                    "sha256_inherited": shard["sha256_inherited"],
                }
                for shard in shards
            ],
            "shard_digest_policy": (
                "inherited from the committed 2026-09-04 receipt's own local re-hash; "
                "this row may not hash the audio bytes, so shard identity rests on the "
                "pinned byte sizes plus row-for-row agreement with the hash-pinned "
                "segments-test.jsonl"
            ),
        },
        "containers": container_profile(arrays),
        "segment_id_coverage": segment_id_coverage(arrays),
        "difference_distribution": differences,
        "released_gap_distribution": released,
        "published_gap_distribution": published,
        "centered_gap_distribution": centered,
        "per_call_released_overlap": per_call_overlap(pairs),
        "non_monotonic_pairs": non_monotonic,
        "dev_side": (
            "The dev population cannot answer this question offline: the 55 train "
            "shards that hold the 6,038 dev10 rows were never downloaded, only "
            "column-projected over the network, so no released dev array exists on "
            "disk. Every number here is the TEST release's."
        ),
    }
    summary["verdict"] = verdict(differences, released, published)
    return _rounded(summary)


def headline(summary: Mapping[str, Any]) -> str:
    """The operator-facing summary of one run."""

    differences = summary["difference_distribution"]
    released = summary["released_gap_distribution"]
    published = summary["published_gap_distribution"]
    containers = summary["containers"]
    lines = [
        f"utterances {summary['population']['utterances']} over "
        f"{summary['population']['calls']} calls; containers "
        f"{list(containers['shapes'])}",
        f"array - published seconds: min {differences['min']:.6f}, median "
        f"{differences['percentiles']['50']:.6f}, max {differences['max']:.6f}; "
        f"span-faithful {differences['span_faithful']} "
        f"({100.0 * differences['span_faithful_share']:.2f} %) within "
        f"{differences['span_tolerance_seconds']} s",
        f"implied per-side pad: median "
        f"{differences['implied_pad_seconds']['median']:.6f} s, max absolute "
        f"{differences['implied_pad_seconds']['max_absolute']:.6f} s",
        f"released arrays, adjacent pairs {released['pairs']}: overlapping "
        f"{released['overlapping_pairs']} "
        f"({100.0 * released['overlapping_share']:.1f} %), min gap "
        f"{released['min']:.5f} s, median {released['percentiles']['50']:.5f} s, "
        f"duplicated {released['overlap_seconds_total']:.1f} s",
        f"published timestamps, same pairs: overlapping "
        f"{published['overlapping_pairs']} "
        f"({100.0 * published['overlapping_share']:.1f} %), min gap "
        f"{published['min']:.5f} s",
        f"VERDICT {summary['verdict']['verdict']}",
        summary["verdict"]["comparability"],
    ]
    return "\n".join(lines)


__all__ = [
    "ANALYSIS_VERSION",
    "AdjacentPair",
    "ArrayDurationError",
    "DIFFERENCE_BUCKET_EDGES",
    "EXPOSURE_ROW_ID",
    "FORBIDDEN_COLUMNS",
    "GAP_BUCKET_EDGES",
    "HEADER_PREFIX_BYTES",
    "PER_UTTERANCE_COLUMNS",
    "PROJECTED_COLUMNS",
    "ReleasedArray",
    "SEGMENT_TABLE_RECEIPT_RELPATH",
    "SPAN_TOLERANCE_SECONDS",
    "WavHeader",
    "adjacent_pairs",
    "build_arrays",
    "build_summary",
    "container_profile",
    "difference_distribution",
    "gap_distribution",
    "headline",
    "load_receipt",
    "load_test_segment_table",
    "parse_wav_header",
    "per_call_overlap",
    "per_utterance_table",
    "segment_id_coverage",
    "read_shard_headers",
    "resolve_shards",
    "verdict",
]
