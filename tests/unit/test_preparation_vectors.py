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
