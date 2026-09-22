"""Unit tests for the generalised query-content derivative builder (cell B6
item 1): ``scripts/build_slurp_query_content_derivative.py``.

Exercises the transform on a synthetic two-row ``sealed-segment-vectors``
file so no real E: bytes are needed; the real DEV-2000-ADDED derivative this
script actually produced is proven separately by
``tests/unit/test_slurp_b6_dev2000_cells.py`` item (e), which hashes the real
file on E: when it is reachable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_slurp_query_content_derivative.py"

_spec = importlib.util.spec_from_file_location("_build_slurp_query_content_derivative", SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

build_query_content_derivative = _module.build_query_content_derivative


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_source(root: Path, relpath: str, rows: list[tuple[str, list[float]]]) -> str:
    lines = [
        json.dumps({"id": entry_id, "segments": [{"vectors": {"intent-boundary": vector}}]})
        for entry_id, vector in rows
    ]
    raw = ("\n".join(lines) + "\n").encode("utf-8")
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return _sha256(raw)


def test_flattens_two_rows_and_renames_dimension(tmp_path: Path) -> None:
    rows = [("sample:a", [0.1, 0.2, 0.3]), ("sample:b", [0.4, 0.5, 0.6])]
    source_sha256 = _write_source(tmp_path, "vectors/synthetic-v1/query-vectors-speech-segments.jsonl", rows)

    result = build_query_content_derivative(
        tmp_path,
        source_relpath="vectors/synthetic-v1/query-vectors-speech-segments.jsonl",
        source_sha256=source_sha256,
        out_dir_relpath="vectors/synthetic-v1",
        out_name="query-vectors-speech-content-v1.jsonl",
        ledger_row="SAEA-SYNTHETIC-TEST-V1",
        check=False,
    )

    assert result["row_count"] == 2
    out_path = tmp_path / "vectors" / "synthetic-v1" / "query-vectors-speech-content-v1.jsonl"
    assert out_path.is_file()
    assert _sha256(out_path.read_bytes()) == result["sha256"]

    written_rows = [json.loads(line) for line in out_path.read_text(encoding="utf-8").splitlines()]
    assert [row["id"] for row in written_rows] == ["sample:a", "sample:b"]
    for (_, vector), row in zip(rows, written_rows):
        assert set(row["vectors"]) == {"content"}
        assert row["vectors"]["content"] == vector  # byte-identical floats, only the key renamed

    provenance_path = tmp_path / "vectors" / "synthetic-v1" / "query-vectors-speech-content-v1.provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    assert provenance["schema"] == "saea-slurp-exemplar-query-vectors-provenance-v1"
    assert provenance["execution_profile"] == "model-free-check"
    assert provenance["exposure_ledger_row"] == "SAEA-SYNTHETIC-TEST-V1"
    assert provenance["row_count"] == 2
    assert provenance["sha256"] == result["sha256"]
    assert provenance["source_dimension"] == "intent-boundary"
    assert provenance["target_dimension"] == "content"


def test_check_mode_writes_nothing(tmp_path: Path) -> None:
    rows = [("sample:a", [0.1, 0.2])]
    source_sha256 = _write_source(tmp_path, "vectors/synthetic-v2/query-vectors-speech-segments.jsonl", rows)

    build_query_content_derivative(
        tmp_path,
        source_relpath="vectors/synthetic-v2/query-vectors-speech-segments.jsonl",
        source_sha256=source_sha256,
        out_dir_relpath="vectors/synthetic-v2",
        out_name="query-vectors-speech-content-v1.jsonl",
        ledger_row="SAEA-SYNTHETIC-TEST-V2",
        check=True,
    )

    assert not (tmp_path / "vectors" / "synthetic-v2" / "query-vectors-speech-content-v1.jsonl").exists()
    assert not (tmp_path / "vectors" / "synthetic-v2" / "query-vectors-speech-content-v1.provenance.json").exists()


def test_refuses_to_overwrite_an_existing_derivative(tmp_path: Path) -> None:
    rows = [("sample:a", [0.1, 0.2])]
    source_sha256 = _write_source(tmp_path, "vectors/synthetic-v3/query-vectors-speech-segments.jsonl", rows)
    kwargs = dict(
        root=tmp_path,
        source_relpath="vectors/synthetic-v3/query-vectors-speech-segments.jsonl",
        source_sha256=source_sha256,
        out_dir_relpath="vectors/synthetic-v3",
        out_name="query-vectors-speech-content-v1.jsonl",
        ledger_row="SAEA-SYNTHETIC-TEST-V3",
        check=False,
    )
    build_query_content_derivative(**kwargs)
    with pytest.raises(SystemExit):
        build_query_content_derivative(**kwargs)


def test_refuses_a_source_hash_mismatch(tmp_path: Path) -> None:
    rows = [("sample:a", [0.1, 0.2])]
    _write_source(tmp_path, "vectors/synthetic-v4/query-vectors-speech-segments.jsonl", rows)
    with pytest.raises(SystemExit):
        build_query_content_derivative(
            tmp_path,
            source_relpath="vectors/synthetic-v4/query-vectors-speech-segments.jsonl",
            source_sha256="0" * 64,
            out_dir_relpath="vectors/synthetic-v4",
            out_name="query-vectors-speech-content-v1.jsonl",
            ledger_row="SAEA-SYNTHETIC-TEST-V4",
            check=False,
        )


def test_refuses_more_than_one_segment(tmp_path: Path) -> None:
    raw = (
        json.dumps({"id": "sample:a", "segments": [
            {"vectors": {"intent-boundary": [0.1]}},
            {"vectors": {"intent-boundary": [0.2]}},
        ]})
        + "\n"
    ).encode("utf-8")
    path = tmp_path / "vectors" / "synthetic-v5" / "query-vectors-speech-segments.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    with pytest.raises(SystemExit):
        build_query_content_derivative(
            tmp_path,
            source_relpath="vectors/synthetic-v5/query-vectors-speech-segments.jsonl",
            source_sha256=_sha256(raw),
            out_dir_relpath="vectors/synthetic-v5",
            out_name="query-vectors-speech-content-v1.jsonl",
            ledger_row="SAEA-SYNTHETIC-TEST-V5",
            check=False,
        )


def test_refuses_the_wrong_dimension(tmp_path: Path) -> None:
    raw = (json.dumps({"id": "sample:a", "segments": [{"vectors": {"content": [0.1]}}]}) + "\n").encode("utf-8")
    path = tmp_path / "vectors" / "synthetic-v6" / "query-vectors-speech-segments.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    with pytest.raises(SystemExit):
        build_query_content_derivative(
            tmp_path,
            source_relpath="vectors/synthetic-v6/query-vectors-speech-segments.jsonl",
            source_sha256=_sha256(raw),
            out_dir_relpath="vectors/synthetic-v6",
            out_name="query-vectors-speech-content-v1.jsonl",
            ledger_row="SAEA-SYNTHETIC-TEST-V6",
            check=False,
        )
