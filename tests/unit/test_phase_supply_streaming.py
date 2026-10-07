"""Bounded sealed-vector decoding preserves complete pinned-source semantics."""

import hashlib
import io
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import phase_supply as ps


def _pin(path, raw):
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _row(entry_id, vector):
    return json.dumps({"id": entry_id, "vectors": {"content": vector}})


@pytest.mark.parametrize("chunk_size", [1, 2, 7, io.DEFAULT_BUFFER_SIZE])
def test_streaming_preserves_every_splitlines_boundary(tmp_path, monkeypatch, chunk_size):
    raw = ("alpha\r\nbeta\rgamma\n\vdelta\f\x1c\x1d\x1e\x85\u2028\u2029"
           "multi-byte: \u00e9\u20ac\r\nlast").encode("utf-8")
    path = tmp_path / "boundaries.jsonl"
    digest = _pin(path, raw)
    monkeypatch.setattr(ps.io, "DEFAULT_BUFFER_SIZE", chunk_size)
    assert list(ps._sealed_vector_lines(
        path, expected_sha256=digest, label="sealed vector file"
    )) == raw.decode("utf-8").splitlines()


@pytest.mark.parametrize("tail", [b"", b"\n", b"\r", b"\r\n", b"\n\n"])
def test_streaming_preserves_empty_and_terminal_lines(tmp_path, tail):
    path = tmp_path / "tail.jsonl"
    raw = b"first\n" + tail
    digest = _pin(path, raw)
    assert list(ps._sealed_vector_lines(
        path, expected_sha256=digest, label="sealed vector file"
    )) == raw.decode("utf-8").splitlines()


def test_vectors_keep_order_and_exact_float_values(tmp_path):
    path = tmp_path / "vectors.jsonl"
    raw = ("  \r\n" + _row("second", [0, -0.0, 0.1, 1e-300]) + "\u2028"
           + _row("first", [1, -2.25, 3.141592653589793, 1e300])).encode()
    digest = _pin(path, raw)
    table = ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))
    assert list(table) == ["second", "first"]
    assert [v.hex() for v in table["second"]["content"]] == [
        float(v).hex() for v in [0, -0.0, 0.1, 1e-300]
    ]
    assert [v.hex() for v in table["first"]["content"]] == [
        float(v).hex() for v in [1, -2.25, 3.141592653589793, 1e300]
    ]


@pytest.mark.parametrize("raw", [b"invalid JSON\n", b"{}\n\xff"])
def test_hash_refusal_precedes_json_and_utf8(tmp_path, raw):
    path = tmp_path / "invalid.jsonl"
    _pin(path, raw)
    with pytest.raises(ps.PhaseSupplyError, match="hashes to"):
        ps.load_sealed_vectors(path, expected_sha256="0" * 64, dimensions=("content",))


def test_late_utf8_refusal_precedes_early_json(tmp_path):
    path = tmp_path / "invalid.jsonl"
    digest = _pin(path, b"invalid JSON\n" + b" " * 9000 + b"\xff")
    with pytest.raises(UnicodeDecodeError):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))


@pytest.mark.parametrize("late_row, message", [
    ("invalid JSON", "line 2 is not valid JSON"),
    (_row("first", [1.0]), "duplicate id"),
    (_row("late", [1.0, 2.0]), "mixes widths"),
    (_row("late", [True]), "non-numeric"),
    (json.dumps({"id": "late", "vectors": {"other": [1.0]}}), "does not declare"),
])
def test_all_late_records_are_validated(tmp_path, late_row, message):
    path = tmp_path / "late.jsonl"
    digest = _pin(path, (_row("first", [1.0]) + "\n" + late_row).encode())
    with pytest.raises(ps.PhaseSupplyError, match=message):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))


def test_generic_nonfinite_acceptance_is_unchanged(tmp_path):
    path = tmp_path / "nonfinite.jsonl"
    digest = _pin(path, _row("first", [float("nan"), float("inf")]).encode())
    table = ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))
    assert [v.hex() for v in table["first"]["content"]] == ["nan", "inf"]


def test_streaming_never_reads_a_whole_file_and_refuses_changed_second_pass(tmp_path, monkeypatch):
    path = tmp_path / "changed.jsonl"
    original = _row("first", [1.0]).encode()
    changed = _row("other", [1.0]).encode()
    assert len(original) == len(changed)
    digest = _pin(path, original)

    class MutatingStream(io.BytesIO):
        def read(self, size=-1):
            assert 0 < size <= io.DEFAULT_BUFFER_SIZE
            return super().read(size)

        def seek(self, offset, whence=0):
            assert offset == 0 and whence == 0
            super().seek(0)
            self.write(changed)
            return super().seek(0)

    real_open = Path.open

    def open_source(self, *args, **kwargs):
        return MutatingStream(original) if self == path else real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", open_source)
    with pytest.raises(ps.PhaseSupplyError, match="changed during decoding"):
        ps.load_sealed_vectors(path, expected_sha256=digest, dimensions=("content",))
    # The test changes only the simulated stream, never pinned source bytes.
    monkeypatch.undo()
    assert path.read_bytes() == original


@pytest.mark.parametrize("late_vector, message", [
    ([float("nan"), 1.0], "finite numbers"),
    ([1.0], "mixes widths"),
    ([True, 1.0], "finite numbers"),
])
def test_segment_loader_validates_late_records(tmp_path, late_vector, message):
    path = tmp_path / "late-segments.jsonl"
    rows = []
    for entry_id, vector in (("first", [1.0, 0.0]), ("late", late_vector)):
        rows.append({"id": entry_id, "audio_sha256": "a" * 64,
                     "source_frames": 16000, "source_sample_rate_hz": 16000,
                     "segments": [{"id": "segment", "start_frame": 0,
                                   "end_frame": 16000, "vectors": {"content": vector}}]})
    digest = _pin(path, "\n".join(json.dumps(row) for row in rows).encode())
    with pytest.raises(ps.PhaseSupplyError, match=message):
        ps.load_sealed_segment_vectors(path, expected_sha256=digest, dimensions=("content",))
