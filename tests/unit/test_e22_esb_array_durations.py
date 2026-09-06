"""Unit tests for the ESB released-array duration check.

Everything here runs on SYNTHETIC containers, a SYNTHETIC segment table and a
SYNTHETIC parquet shard built inside ``tmp_path``. No ESB shard, no real
segment table, no clip and no sealed output is opened, so the suite carries no
exposure of any population.

The tests that matter most are the refusals and the no-text guarantee: every
synthetic row carries a sentinel ``sentence`` value, and the suite asserts that
the sentinel never reaches a parsed row, a summary or the CSV receipt.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.e22_esb_array_durations import (
    SPAN_TOLERANCE_SECONDS,
    AdjacentPair,
    ArrayDurationError,
    ReleasedArray,
    WavHeader,
    adjacent_pairs,
    build_arrays,
    build_summary,
    container_profile,
    difference_distribution,
    gap_distribution,
    headline,
    load_receipt,
    load_test_segment_table,
    parse_wav_header,
    per_call_overlap,
    per_utterance_table,
    read_shard_headers,
    resolve_shards,
    segment_id_coverage,
    verdict,
)

SENTINEL = "THIS GOLD SENTENCE MUST NEVER BE READ"


# ---------------------------------------------------------------------------
# Fixtures built by hand, so every byte under test is one this file wrote
# ---------------------------------------------------------------------------


def wav_bytes(
    frames: int,
    *,
    sample_rate: int = 16000,
    channels: int = 2,
    bits: int = 16,
    audio_format: int = 1,
    extra_chunk: bool = False,
) -> bytes:
    """A canonical RIFF/WAVE container carrying ``frames`` silent frames."""

    frame_bytes = channels * (bits // 8)
    data = b"\x00" * (frames * frame_bytes)
    fmt = struct.pack(
        "<HHIIHH",
        audio_format,
        channels,
        sample_rate,
        sample_rate * frame_bytes,
        frame_bytes,
        bits,
    )
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt
    if extra_chunk:
        chunks += b"LIST" + struct.pack("<I", 4) + b"INFO"
    chunks += b"data" + struct.pack("<I", len(data)) + data
    body = b"WAVE" + chunks
    return b"RIFF" + struct.pack("<I", len(body)) + body


def as_float32(value: float) -> float:
    """The float32 the upstream parquet would actually store."""

    return float(struct.unpack("<f", struct.pack("<f", value))[0])


def header(frames: int, *, sample_rate: int = 16000) -> WavHeader:
    blob = wav_bytes(frames, sample_rate=sample_rate)
    return parse_wav_header(blob[:4096], len(blob))


def released(
    sample_id: str,
    call: str,
    index: int,
    start: float,
    end: float,
    frames: int,
) -> ReleasedArray:
    return ReleasedArray(
        sample_id=sample_id,
        call=call,
        segment_index=index,
        start_seconds=start,
        end_seconds=end,
        header=header(frames),
    )


#: Four synthetic utterances over two calls. Call ``A`` reproduces the real
#: geometry under test -- adjacent published segments that OVERLAP by 0.15 s,
#: with arrays cut at exactly those boundaries. Call ``B`` is the tight
#: counter-example.
def synthetic_rows() -> list[dict[str, object]]:
    return [
        {"id": "A-0", "call": "A", "index": 0, "start": 0.0, "end": 2.0},
        {"id": "A-1", "call": "A", "index": 1, "start": 1.85, "end": 4.0},
        {"id": "A-2", "call": "A", "index": 2, "start": 3.85, "end": 5.5},
        {"id": "B-0", "call": "B", "index": 0, "start": 0.0, "end": 1.0},
        {"id": "B-1", "call": "B", "index": 1, "start": 1.5, "end": 2.25},
    ]


def synthetic_arrays(*, pad_seconds: float = 0.0) -> dict[str, ReleasedArray]:
    arrays: dict[str, ReleasedArray] = {}
    for row in synthetic_rows():
        start = as_float32(float(row["start"]))
        end = as_float32(float(row["end"]))
        frames = round((end - start + pad_seconds) * 16000)
        arrays[str(row["id"])] = released(
            str(row["id"]), str(row["call"]), int(row["index"]), start, end, frames
        )
    return arrays


def write_segment_table(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    """A synthetic ``segments-test.jsonl`` plus the receipt that pins it."""

    lines = []
    for row in synthetic_rows():
        lines.append(
            json.dumps(
                {
                    "source_id": row["call"],
                    "segment_id": str(row["index"]),
                    "sentence": SENTINEL,
                    "start_ts": as_float32(float(row["start"])),
                    "end_ts": as_float32(float(row["end"])),
                    "id": row["id"],
                },
                sort_keys=True,
            )
        )
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    root = tmp_path / "root"
    (root / "derived").mkdir(parents=True)
    path = root / "derived" / "segments-test.jsonl"
    path.write_bytes(payload)
    receipt = {
        "upstream": {"repo_id": "synthetic/earnings22_split", "revision": "0" * 40},
        "extracted_table": {
            "relpath": "derived/segments-test.jsonl",
            "sha256": hashlib.sha256(payload).hexdigest(),
            "rows": len(lines),
        },
        "parquet_files": [],
    }
    return root, receipt


# ---------------------------------------------------------------------------
# The container header
# ---------------------------------------------------------------------------


def test_header_reports_rate_channels_and_frames() -> None:
    blob = wav_bytes(32000, sample_rate=16000, channels=2, bits=16)
    parsed = parse_wav_header(blob[:4096], len(blob))
    assert (parsed.sample_rate, parsed.channels, parsed.bits_per_sample) == (16000, 2, 16)
    assert parsed.frames == 32000
    assert parsed.duration_seconds == pytest.approx(2.0)
    assert parsed.container_bytes == len(blob)


def test_header_walks_an_ancillary_chunk_before_data() -> None:
    blob = wav_bytes(1600, extra_chunk=True)
    assert parse_wav_header(blob[:4096], len(blob)).frames == 1600


def test_header_refuses_a_non_riff_container() -> None:
    with pytest.raises(ArrayDurationError, match="RIFF/WAVE"):
        parse_wav_header(b"OggS" + b"\x00" * 60, 64)


def test_header_refuses_a_riff_size_that_disagrees_with_the_blob() -> None:
    blob = wav_bytes(160)
    with pytest.raises(ArrayDurationError, match="does not match"):
        parse_wav_header(blob[:4096], len(blob) + 1)


def test_header_refuses_a_compressed_format_tag() -> None:
    blob = wav_bytes(160, audio_format=3)
    with pytest.raises(ArrayDurationError, match="not uncompressed PCM"):
        parse_wav_header(blob[:4096], len(blob))


def test_header_refuses_a_container_with_no_data_chunk() -> None:
    fmt = struct.pack("<HHIIHH", 1, 1, 16000, 32000, 2, 16)
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt
    blob = b"RIFF" + struct.pack("<I", len(body)) + body
    with pytest.raises(ArrayDurationError, match="no data chunk"):
        parse_wav_header(blob + b"\x00" * 8, len(blob))


def test_header_refuses_a_data_chunk_longer_than_the_blob() -> None:
    blob = bytearray(wav_bytes(160))
    struct.pack_into("<I", blob, 40, 10_000_000)
    with pytest.raises(ArrayDurationError, match="only"):
        parse_wav_header(bytes(blob[:4096]), len(blob))


def test_header_refuses_a_partial_frame() -> None:
    blob = bytearray(wav_bytes(160))
    struct.pack_into("<I", blob, 40, 638)
    with pytest.raises(ArrayDurationError, match="whole number"):
        parse_wav_header(bytes(blob[:4096]), len(blob))


# ---------------------------------------------------------------------------
# One released utterance
# ---------------------------------------------------------------------------


def test_difference_and_implied_pad_are_signed_array_minus_published() -> None:
    array = released("A-0", "A", 0, 0.0, 2.0, 32000 + 1600)
    assert array.published_seconds == pytest.approx(2.0)
    assert array.array_seconds == pytest.approx(2.1)
    assert array.difference_seconds == pytest.approx(0.1)
    assert array.implied_pad_seconds == pytest.approx(0.05)
    assert not array.span_faithful


def test_span_faithful_is_exactly_the_declared_tolerance() -> None:
    inside = ReleasedArray("x", "A", 0, 0.0, 1.0, header(16000))
    assert inside.span_faithful
    outside = ReleasedArray(
        "y", "A", 0, 0.0, 1.0 - 2.0 * SPAN_TOLERANCE_SECONDS, header(16000)
    )
    assert not outside.span_faithful


# ---------------------------------------------------------------------------
# Landed inputs
# ---------------------------------------------------------------------------


def test_segment_table_drops_the_gold_sentence(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    rows = load_test_segment_table(root, receipt)
    assert set(rows) == {row["id"] for row in synthetic_rows()}
    for row in rows.values():
        assert set(row) == {"id", "source_id", "segment_id", "start_ts", "end_ts"}
        assert SENTINEL not in json.dumps(row)


def test_segment_table_refuses_a_digest_drift(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    receipt["extracted_table"]["sha256"] = "0" * 64
    with pytest.raises(ArrayDurationError, match="identity drift"):
        load_test_segment_table(root, receipt)


def test_segment_table_refuses_a_row_count_drift(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    receipt["extracted_table"]["rows"] = 99
    with pytest.raises(ArrayDurationError, match="the receipt pins 99"):
        load_test_segment_table(root, receipt)


def test_resolve_shards_size_checks_every_pinned_shard(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "parquet").mkdir(parents=True)
    shard = root / "parquet" / "test-0.parquet"
    shard.write_bytes(b"x" * 128)
    receipt = {
        "parquet_files": [
            {
                "local_relpath": "parquet/test-0.parquet",
                "bytes": 128,
                "sha256": "a" * 64,
                "locally_rehashed": True,
                "local_matches_lfs_oid": True,
            }
        ]
    }
    resolved = resolve_shards(root, receipt)
    assert resolved[0]["bytes"] == 128
    assert resolved[0]["sha256_inherited"] == "a" * 64

    receipt["parquet_files"][0]["bytes"] = 129
    with pytest.raises(ArrayDurationError, match="the receipt pins 129"):
        resolve_shards(root, receipt)


def test_resolve_shards_refuses_a_shard_that_was_never_rehashed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    (root / "parquet").mkdir(parents=True)
    (root / "parquet" / "test-0.parquet").write_bytes(b"x" * 8)
    receipt = {
        "parquet_files": [
            {
                "local_relpath": "parquet/test-0.parquet",
                "bytes": 8,
                "sha256": "a" * 64,
                "locally_rehashed": False,
                "local_matches_lfs_oid": False,
            }
        ]
    }
    with pytest.raises(ArrayDurationError, match="never locally re-hashed"):
        resolve_shards(root, receipt)


def test_the_committed_receipt_this_check_pins_is_readable() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    receipt = load_receipt(repo_root)
    assert receipt["upstream"]["split"] == "test"
    assert len(receipt["parquet_files"]) == 4
    assert receipt["extracted_table"]["rows"] == 2735


# ---------------------------------------------------------------------------
# The synthetic shard
# ---------------------------------------------------------------------------


def write_shard(tmp_path: Path) -> Path:
    """A parquet shard with the upstream schema, ``sentence`` column included."""

    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")

    rows = synthetic_rows()
    blobs = []
    for row in rows:
        start = as_float32(float(row["start"]))
        end = as_float32(float(row["end"]))
        blobs.append({"bytes": wav_bytes(round((end - start) * 16000)), "path": "x.wav"})
    table = pa.table(
        {
            "source_id": pa.array([str(row["call"]) for row in rows], pa.string()),
            "audio": pa.array(
                blobs,
                pa.struct([("bytes", pa.binary()), ("path", pa.string())]),
            ),
            "segment_id": pa.array([str(row["index"]) for row in rows], pa.string()),
            "sentence": pa.array([SENTINEL] * len(rows), pa.string()),
            "start_ts": pa.array(
                [as_float32(float(row["start"])) for row in rows], pa.float32()
            ),
            "end_ts": pa.array(
                [as_float32(float(row["end"])) for row in rows], pa.float32()
            ),
            "id": pa.array([str(row["id"]) for row in rows], pa.string()),
        }
    )
    path = tmp_path / "shard.parquet"
    pq.write_table(table, path, row_group_size=2)
    return path


def test_the_shard_read_takes_lengths_and_headers_and_no_text(tmp_path: Path) -> None:
    rows = read_shard_headers(write_shard(tmp_path))
    assert len(rows) == len(synthetic_rows())
    assert SENTINEL not in json.dumps(
        [{key: str(value) for key, value in row.items()} for row in rows]
    )
    by_id = {row["id"]: row for row in rows}
    assert by_id["A-0"]["header"].frames == 32000
    assert by_id["A-0"]["header"].sample_rate == 16000
    assert by_id["A-0"]["container_bytes"] == 32000 * 4 + 44


def test_build_arrays_joins_the_shard_to_the_pinned_table(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    segments = load_test_segment_table(root, receipt)
    arrays = build_arrays(read_shard_headers(write_shard(tmp_path)), segments)
    assert set(arrays) == set(segments)
    assert all(array.span_faithful for array in arrays.values())


def test_build_arrays_refuses_a_shard_row_the_table_does_not_pin(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    segments = load_test_segment_table(root, receipt)
    rows = read_shard_headers(write_shard(tmp_path))
    rows[0]["id"] = "GHOST"
    with pytest.raises(ArrayDurationError, match="absent from the hash-pinned"):
        build_arrays(rows, segments)


def test_build_arrays_refuses_a_boundary_that_disagrees(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    segments = load_test_segment_table(root, receipt)
    rows = read_shard_headers(write_shard(tmp_path))
    rows[0]["start_ts"] = rows[0]["start_ts"] + 1.0
    with pytest.raises(ArrayDurationError, match="against pinned"):
        build_arrays(rows, segments)


def test_build_arrays_refuses_a_pinned_segment_with_no_shard_row(tmp_path: Path) -> None:
    root, receipt = write_segment_table(tmp_path)
    segments = load_test_segment_table(root, receipt)
    rows = read_shard_headers(write_shard(tmp_path))
    with pytest.raises(ArrayDurationError, match="have no shard row"):
        build_arrays(rows[:-1], segments)


# ---------------------------------------------------------------------------
# Geometry and distributions
# ---------------------------------------------------------------------------


def test_adjacent_pairs_are_within_a_call_and_in_segment_order() -> None:
    pairs = adjacent_pairs(synthetic_arrays())
    assert [(pair.left_id, pair.right_id) for pair in pairs] == [
        ("A-0", "A-1"),
        ("A-1", "A-2"),
        ("B-0", "B-1"),
    ]


def test_an_array_cut_at_the_published_span_reproduces_the_published_gap() -> None:
    pairs = adjacent_pairs(synthetic_arrays())
    for pair in pairs:
        assert pair.released_gap_seconds == pytest.approx(
            pair.published_gap_seconds, abs=1e-4
        )
        assert pair.centered_gap_seconds == pytest.approx(
            pair.published_gap_seconds, abs=1e-4
        )
    assert pairs[0].published_gap_seconds == pytest.approx(-0.15, abs=1e-4)
    assert pairs[2].published_gap_seconds == pytest.approx(0.5, abs=1e-4)


def test_a_symmetric_pad_widens_the_released_geometry_but_not_the_centered_one() -> None:
    pairs = adjacent_pairs(synthetic_arrays(pad_seconds=0.18))
    assert pairs[0].released_gap_seconds == pytest.approx(-0.33, abs=1e-3)
    assert pairs[0].centered_gap_seconds == pytest.approx(-0.33, abs=1e-3)
    assert pairs[2].released_gap_seconds == pytest.approx(0.32, abs=1e-3)


def test_gap_distribution_counts_overlap_and_duplicated_seconds() -> None:
    distribution = gap_distribution([-0.15, -0.15, 0.5, 0.0])
    assert distribution["pairs"] == 4
    assert distribution["overlapping_pairs"] == 2
    assert distribution["touching_pairs"] == 1
    assert distribution["separated_pairs"] == 1
    assert distribution["overlapping_share"] == pytest.approx(0.5)
    assert distribution["overlap_seconds_total"] == pytest.approx(0.3)


def test_difference_distribution_reports_faithful_share_and_frame_deltas() -> None:
    distribution = difference_distribution(synthetic_arrays())
    assert distribution["span_faithful"] == 5
    assert distribution["span_faithful_share"] == pytest.approx(1.0)
    assert set(distribution["frame_delta_counts"]) <= {"-1", "0", "1"}

    assert distribution["not_span_faithful"] == []

    padded = difference_distribution(synthetic_arrays(pad_seconds=0.18))
    assert padded["span_faithful"] == 0
    assert padded["implied_pad_seconds"]["median"] == pytest.approx(0.09, abs=1e-3)
    assert padded["not_span_faithful_listed"] == 5
    assert {row["sample_id"] for row in padded["not_span_faithful"]} == set(
        synthetic_arrays()
    )
    assert SENTINEL not in json.dumps(padded["not_span_faithful"])


def test_per_call_overlap_reports_every_call_separately() -> None:
    table = per_call_overlap(adjacent_pairs(synthetic_arrays()))
    assert table["A"]["overlapping_pairs"] == 2
    assert table["B"]["overlapping_pairs"] == 0
    assert table["A"]["overlap_seconds"] == pytest.approx(0.3, abs=1e-3)


def test_segment_id_coverage_finds_the_indices_the_release_does_not_ship() -> None:
    arrays = synthetic_arrays()
    arrays.pop("A-1")
    coverage = segment_id_coverage(arrays)
    assert coverage["by_call"]["A"]["missing_indices"] == [1]
    assert coverage["by_call"]["B"]["missing_indices"] == []
    assert coverage["rows"] == 4
    assert coverage["missing_indices_total"] == 1
    assert coverage["rows_plus_missing"] == 5


def test_container_profile_aggregates_shapes_without_reading_a_sample() -> None:
    profile = container_profile(synthetic_arrays())
    assert profile["distinct_shapes"] == 1
    assert "16000 Hz / 2 ch / 16 bit / format 1" in profile["shapes"]
    assert set(profile["shapes_by_call"]) == {"A", "B"}
    assert profile["shapes_by_call"]["A"]["16000 Hz / 2 ch / 16 bit / format 1"] == 3
    assert profile["array_seconds_total"] == pytest.approx(
        profile["published_seconds_total"], abs=1e-3
    )


# ---------------------------------------------------------------------------
# The verdict
# ---------------------------------------------------------------------------


def test_verdict_overlap_when_the_arrays_reproduce_the_published_geometry() -> None:
    arrays = synthetic_arrays()
    pairs = adjacent_pairs(arrays)
    call = verdict(
        difference_distribution(arrays),
        gap_distribution([pair.released_gap_seconds for pair in pairs]),
        gap_distribution([pair.published_gap_seconds for pair in pairs]),
    )
    assert call["verdict"] == "RELEASED ARRAYS OVERLAP"
    assert "incomparable" in call["comparability"]


def test_verdict_tight_when_the_release_cut_the_overlap_out() -> None:
    call = verdict(
        {"span_faithful_share": 0.02},
        {"overlapping_share": 0.0},
        {"overlapping_share": 0.777},
    )
    assert call["verdict"] == "TIGHT"
    assert "prohibition lifts" in call["comparability"]


def test_verdict_mixed_when_neither_pole_holds() -> None:
    call = verdict(
        {"span_faithful_share": 0.40},
        {"overlapping_share": 0.30},
        {"overlapping_share": 0.777},
    )
    assert call["verdict"] == "MIXED"
    assert "stays open" in call["comparability"]


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def test_per_utterance_table_carries_no_text_and_ends_each_call_open() -> None:
    arrays = synthetic_arrays()
    csv = per_utterance_table(arrays, adjacent_pairs(arrays))
    lines = csv.strip().split("\n")
    assert lines[0].startswith("sample_id,call,segment_index")
    assert len(lines) == 1 + len(arrays)
    assert SENTINEL not in csv
    last_of_call_a = [line for line in lines if line.startswith("A-2,")][0]
    assert last_of_call_a.endswith(",,,")


def test_summary_declares_zero_contacts_and_carries_the_verdict() -> None:
    arrays = synthetic_arrays()
    pairs = adjacent_pairs(arrays)
    summary = build_summary(
        arrays=arrays,
        pairs=pairs,
        shards=[{"relpath": "parquet/test-0.parquet", "bytes": 8, "sha256_inherited": "a"}],
        receipt={
            "upstream": {"repo_id": "synthetic", "split": "test"},
            "extracted_table": {"relpath": "derived/segments-test.jsonl", "rows": 5},
        },
        outbound_attempts=0,
        outbound_targets=[],
    )
    contacts = summary["contacts"]
    assert contacts["frozen_core"] == 0
    assert contacts["network"] == 0
    assert contacts["speech_seconds_delivered_to_any_service"] == 0
    assert contacts["outbound_connection_attempts"] == 0
    assert summary["reads"]["text_columns_read"] == 0
    assert summary["reads"]["audio_samples_decoded"] == 0
    assert "sentence" not in summary["reads"]["projected_columns"]
    assert summary["verdict"]["verdict"] == "RELEASED ARRAYS OVERLAP"
    assert summary["population"]["utterances"] == 5
    assert summary["non_monotonic_pairs"] == 0
    assert SENTINEL not in json.dumps(summary)
    assert "VERDICT RELEASED ARRAYS OVERLAP" in headline(summary)


def test_adjacent_pair_is_a_plain_record() -> None:
    pair = AdjacentPair("A", "A-0", "A-1", -0.15, -0.15, -0.15)
    assert pair.call == "A"
    assert pair.published_gap_seconds == pytest.approx(-0.15)
