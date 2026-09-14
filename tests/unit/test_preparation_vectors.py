"""Model-free vector aliases preserve the frozen signal and refuse stale exports."""

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_vectors import prepare_vector_dimension_alias


@pytest.fixture
def alias_config(tmp_path):
    rows = [
        {"id": "sample-b", "vectors": {"content": [0.25, -0.0, 0.875]}},
        {"id": "sample-a", "vectors": {"content": [-0.25, 0.125, -0.75]}},
    ]
    source = tmp_path / "source.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    receipt = tmp_path / "source-receipt.json"
    receipt.write_text('{"status":"synthetic frozen source"}')
    return {
        "schema": "saea-sealed-vector-dimension-alias-v1",
        "source": {"relpath": "source.jsonl", "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                   "dimension": "content"},
        "target_dimension": "intent-boundary", "expected_rows": 2, "vector_width": 3,
        "output_relpath": "derived/vectors.jsonl", "receipt_relpath": "derived/receipt.json",
        "source_receipts": [{"root": "data", "relpath": "source-receipt.json",
                             "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}],
    }


@pytest.fixture
def segment_alias_config(tmp_path):
    rows = [
        {
            "id": "sample-b", "audio_sha256": "a" * 64,
            "source_frames": 4, "source_sample_rate_hz": 16000,
            "segments": [{
                "id": "sample-b:0", "start_frame": 0, "end_frame": 4,
                "vectors": {"content": [0.25, -0.0, 0.875]},
            }],
        },
        {
            "id": "sample-a", "audio_sha256": "b" * 64,
            "source_frames": 8, "source_sample_rate_hz": 8000,
            "segments": [
                {
                    "id": "sample-a:0", "start_frame": 0, "end_frame": 5,
                    "vectors": {"content": [-0.25, 0.125, -0.75]},
                },
                {
                    "id": "sample-a:1", "start_frame": 4, "end_frame": 8,
                    "vectors": {"content": [0.5, 0.25, -0.125]},
                },
            ],
        },
    ]
    source = tmp_path / "segments.jsonl"
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    receipt = tmp_path / "segment-source-receipt.json"
    receipt.write_text('{"status":"synthetic frozen segment source"}')
    return {
        "schema": "saea-sealed-segment-vector-dimension-alias-v1",
        "source": {
            "kind": "sealed-segment-vectors", "relpath": "segments.jsonl",
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "dimension": "content",
        },
        "target_dimension": "intent-boundary", "expected_rows": 2, "vector_width": 3,
        "output_relpath": "derived/segment-vectors.jsonl",
        "receipt_relpath": "derived/segment-receipt.json",
        "source_receipts": [{
            "root": "data", "relpath": "segment-source-receipt.json",
            "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
        }],
    }


def _rewrite_segment_source(config, tmp_path, mutate):
    source = tmp_path / config["source"]["relpath"]
    rows = [json.loads(line) for line in source.read_bytes().splitlines()]
    mutate(rows)
    source.write_text("".join(json.dumps(row) + "\n" for row in rows))
    config["source"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()


def test_alias_preserves_ids_order_floats_and_warm_cache(alias_config, tmp_path):
    source = (tmp_path / "source.jsonl").read_bytes()
    result = prepare_vector_dimension_alias(alias_config, repo_root=tmp_path, data_root=tmp_path)
    assert result["output"]["encoder_contacts"] == 0
    assert result["output"]["max_absolute_delta"] == 0
    rows = [json.loads(line) for line in (tmp_path / "derived/vectors.jsonl").read_bytes().splitlines()]
    assert [row["id"] for row in rows] == ["sample-b", "sample-a"]
    assert rows[0]["vectors"] == {"intent-boundary": [0.25, -0.0, 0.875]}
    assert "-0.0" in (tmp_path / "derived/vectors.jsonl").read_text()
    warm = prepare_vector_dimension_alias(alias_config, repo_root=tmp_path, data_root=tmp_path)
    assert warm["artifact"]["cache"] == "warm"
    assert warm["artifact"]["sha256"] == result["artifact"]["sha256"]
    assert (tmp_path / "source.jsonl").read_bytes() == source


@pytest.mark.parametrize("change", ["source_hash", "target", "count", "width", "overwrite", "escape"])
def test_alias_refuses_wrong_binding_and_paths(alias_config, tmp_path, change):
    config = copy.deepcopy(alias_config)
    if change == "source_hash":
        config["source"]["sha256"] = "f" * 64
    elif change == "target":
        config["target_dimension"] = "content"
    elif change == "count":
        config["expected_rows"] = 1
    elif change == "width":
        config["vector_width"] = 4
    elif change == "overwrite":
        config["output_relpath"] = "source.jsonl"
    else:
        config["output_relpath"] = "../outside.jsonl"
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(config, repo_root=tmp_path, data_root=tmp_path)
    assert not (tmp_path / "derived/vectors.jsonl").exists()


def test_alias_rechecks_warm_export_and_refuses_overwrite(alias_config, tmp_path):
    prepare_vector_dimension_alias(alias_config, repo_root=tmp_path, data_root=tmp_path)
    output = tmp_path / "derived/vectors.jsonl"
    output.write_text("corrupt")
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(alias_config, repo_root=tmp_path, data_root=tmp_path)
    assert output.read_text() == "corrupt"


def test_segment_alias_preserves_single_and_multiple_segments_and_all_metadata(
    segment_alias_config, tmp_path,
):
    source_rows = [
        json.loads(line) for line in (tmp_path / "segments.jsonl").read_bytes().splitlines()
    ]
    result = prepare_vector_dimension_alias(
        segment_alias_config, repo_root=tmp_path, data_root=tmp_path,
    )
    output = tmp_path / "derived/segment-vectors.jsonl"
    output_rows = [json.loads(line) for line in output.read_bytes().splitlines()]
    assert result["output"]["segment_count"] == 3
    assert result["output"]["source_kind"] == "sealed-segment-vectors"
    assert result["output"]["encoder_contacts"] == 0
    assert [row["id"] for row in output_rows] == ["sample-b", "sample-a"]
    for source_row, output_row in zip(source_rows, output_rows, strict=True):
        assert {key: output_row[key] for key in output_row if key != "segments"} == {
            key: source_row[key] for key in source_row if key != "segments"
        }
        for source_segment, output_segment in zip(
            source_row["segments"], output_row["segments"], strict=True,
        ):
            assert {
                key: output_segment[key] for key in output_segment if key != "vectors"
            } == {
                key: source_segment[key] for key in source_segment if key != "vectors"
            }
            assert output_segment["vectors"] == {
                "intent-boundary": source_segment["vectors"]["content"]
            }
    assert "-0.0" in output.read_text()
    warm = prepare_vector_dimension_alias(
        segment_alias_config, repo_root=tmp_path, data_root=tmp_path,
    )
    assert warm["artifact"]["cache"] == "warm"
    assert warm["artifact"]["sha256"] == result["artifact"]["sha256"]


@pytest.mark.parametrize(
    "change",
    ["unknown_dimension", "mixed_dimensions", "wrong_pin", "duplicate_row", "duplicate_segment"],
)
def test_segment_alias_refuses_invalid_or_unpinned_sources(
    segment_alias_config, tmp_path, change,
):
    config = copy.deepcopy(segment_alias_config)
    if change == "wrong_pin":
        config["source"]["sha256"] = "f" * 64
    elif change == "unknown_dimension":
        _rewrite_segment_source(
            config, tmp_path,
            lambda rows: rows[0]["segments"][0].update(vectors={"other": [1.0, 2.0, 3.0]}),
        )
    elif change == "mixed_dimensions":
        _rewrite_segment_source(
            config, tmp_path,
            lambda rows: rows[0]["segments"][0]["vectors"].update(other=[1.0, 2.0, 3.0]),
        )
    elif change == "duplicate_row":
        _rewrite_segment_source(config, tmp_path, lambda rows: rows.append(copy.deepcopy(rows[0])))
        config["expected_rows"] = 3
    else:
        _rewrite_segment_source(
            config, tmp_path,
            lambda rows: rows[1]["segments"][1].update(id=rows[1]["segments"][0]["id"]),
        )
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(config, repo_root=tmp_path, data_root=tmp_path)
    assert not (tmp_path / "derived/segment-vectors.jsonl").exists()


def test_segment_alias_requires_explicit_schema_and_source_kind(segment_alias_config, tmp_path):
    missing_kind = copy.deepcopy(segment_alias_config)
    del missing_kind["source"]["kind"]
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(missing_kind, repo_root=tmp_path, data_root=tmp_path)

    legacy_schema = copy.deepcopy(segment_alias_config)
    legacy_schema["schema"] = "saea-sealed-vector-dimension-alias-v1"
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(legacy_schema, repo_root=tmp_path, data_root=tmp_path)


def test_segment_alias_rechecks_warm_export(segment_alias_config, tmp_path):
    prepare_vector_dimension_alias(segment_alias_config, repo_root=tmp_path, data_root=tmp_path)
    output = tmp_path / "derived/segment-vectors.jsonl"
    output.write_text("corrupt")
    with pytest.raises(PreparationError):
        prepare_vector_dimension_alias(segment_alias_config, repo_root=tmp_path, data_root=tmp_path)
    assert output.read_text() == "corrupt"
