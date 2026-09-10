import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.pooled_ratio_compare import (
    PooledRatioError,
    _pooled_ratio,
    compare_pooled_ratios,
    run,
)


def _rows(values):
    return {key: {"num": num, "den": den} for key, (num, den) in values.items()}


def _metadata(ids, *, strata=None, clusters=None):
    return {
        key: {
            "cluster": (clusters or {}).get(key, key),
            "sector": (strata or {}).get(key, "all"),
        }
        for key in ids
    }


def _metric(direction="lower"):
    return {"errors": {"numerator_field": "num", "denominator_field": "den", "direction": direction}}


def test_pooled_ratio_is_not_mean_of_row_ratios_and_repeated_ids_retain_weight():
    rows = _rows({"a": (0, 1), "b": (9, 9)})
    assert _pooled_ratio(rows, ["a", "b"], "num", "den") == pytest.approx(0.9)
    assert _pooled_ratio(rows, ["a", "a", "b"], "num", "den") == pytest.approx(9 / 11)


def test_lower_and_higher_direction_and_sign_counts():
    left = _rows({"a": (0, 1), "b": (9, 9)})
    right = _rows({"a": (1, 1), "b": (0, 9)})
    metadata = _metadata(left)
    lower = compare_pooled_ratios(left, right, metadata, _metric("lower"), groupings={}, seed=7, n_replicates=20, ci_level=0.9)
    higher = compare_pooled_ratios(left, right, metadata, _metric("higher"), groupings={}, seed=7, n_replicates=20, ci_level=0.9)
    assert lower["errors"]["natural_mixture"]["gain_pp"] == pytest.approx(80.0)
    assert higher["errors"]["natural_mixture"]["gain_pp"] == pytest.approx(-80.0)
    assert lower["errors"]["sign_counts"] == {"saves": 1, "harms": 1, "ties": 0, "unavailable": 0}


def test_equal_stratum_means_frozen_stratum_ratios_and_clusters_within_strata():
    ids = ("a1", "a2", "a3", "b1")
    left = _rows({"a1": (1, 1), "a2": (1, 1), "a3": (1, 1), "b1": (0, 9)})
    right = _rows({"a1": (0, 1), "a2": (0, 1), "a3": (0, 1), "b1": (9, 9)})
    metadata = _metadata(ids, strata={"a1": "A", "a2": "A", "a3": "A", "b1": "B"}, clusters={"a1": "ca", "a2": "ca", "a3": "ca2", "b1": "cb"})
    for row in metadata.values():
        row["sample_rate"] = 16000
    result = compare_pooled_ratios(
        left, right, metadata, _metric(),
        groupings={"sector": "sector", "sample_rate": "sample_rate"},
        seed=11, n_replicates=30, ci_level=0.9,
    )["errors"]
    assert result["natural_mixture"]["gain_pp"] == pytest.approx(-50.0)
    grouped = result["groupings"]["sector"]
    assert grouped["equal_stratum"]["gain_pp"] == pytest.approx(0.0)
    assert grouped["per_stratum"]["A"]["gain_pp"] == pytest.approx(100.0)
    assert grouped["per_stratum"]["B"]["gain_pp"] == pytest.approx(-100.0)
    assert grouped["equal_stratum"]["bootstrap"]["n_replicates"] == 30
    assert result["groupings"]["sample_rate"]["per_stratum"]["16000"]["n"] == 4


def test_zero_denominator_stratum_is_explicitly_unavailable():
    left = _rows({"a": (1, 2), "b": (0, 0)})
    right = _rows({"a": (0, 2), "b": (0, 0)})
    metadata = _metadata(left, strata={"a": "seen", "b": "rare"})
    result = compare_pooled_ratios(left, right, metadata, _metric(), groupings={"sector": "sector"}, seed=1, n_replicates=10, ci_level=0.9)["errors"]
    assert result["groupings"]["sector"]["per_stratum"]["rare"]["status"] == "unavailable"
    assert result["groupings"]["sector"]["equal_stratum"] == {"status": "unavailable", "reason": "one or more frozen strata has zero pooled denominator"}
    assert result["sign_counts"]["unavailable"] == 1


def _write(path: Path, value):
    path.write_text(json.dumps(value, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_cli_pins_hash_roster_and_exclusive_output(tmp_path):
    left_path, right_path, meta_path = (tmp_path / name for name in ("left.json", "right.json", "meta.json"))
    left = [{"id": "a", "num": 1, "den": 2}, {"id": "b", "num": 0, "den": 2}]
    right = [{"id": "a", "num": 0, "den": 2}, {"id": "b", "num": 0, "den": 2}]
    metadata = {"rows": {"a": {"cluster": "c1", "sector": "x"}, "b": {"cluster": "c2", "sector": "y"}}}
    bindings = {
        "left": {"path": str(left_path), "sha256": _write(left_path, {"rows": left}), "rows_key": "rows"},
        "right": {"path": str(right_path), "sha256": _write(right_path, {"rows": right}), "rows_key": "rows"},
    }
    config = {"execution_profile": "model-free-check", "analysis": {"inputs": bindings, "metadata": {"path": str(meta_path), "sha256": _write(meta_path, metadata), "rows_key": "rows"}, "id_field": "id", "expected_ids_count": 2, "cluster_field": "cluster", "groupings": {"sector": "sector"}, "metrics": _metric(), "contrasts": [{"name": "r-v-l", "left": "left", "right": "right"}], "seed": 3, "n_replicates": 10, "ci_level": 0.9}}
    config_path = tmp_path / "config.json"
    _write(config_path, config)
    output = tmp_path / "result.json"
    result = run(config_path, output)
    assert result["contrasts"]["r-v-l"]["errors"]["natural_mixture"]["gain_pp"] == pytest.approx(25.0)
    with pytest.raises(FileExistsError):
        run(config_path, output)
    left_path.write_text("{}")
    with pytest.raises(PooledRatioError, match="hash mismatch"):
        run(config_path, tmp_path / "other.json")


def test_cli_refuses_metadata_roster_mismatch(tmp_path):
    table = tmp_path / "table.json"
    meta = tmp_path / "meta.json"
    th = _write(table, {"rows": [{"id": "a", "num": 0, "den": 1}]})
    mh = _write(meta, {"rows": {"b": {"cluster": "c", "sector": "s"}}})
    config = {"execution_profile": "model-free-check", "analysis": {"inputs": {"l": {"path": str(table), "sha256": th, "rows_key": "rows"}, "r": {"path": str(table), "sha256": th, "rows_key": "rows"}}, "metadata": {"path": str(meta), "sha256": mh, "rows_key": "rows"}, "id_field": "id", "expected_ids_count": 1, "cluster_field": "cluster", "groupings": {}, "metrics": _metric(), "contrasts": [{"name": "x", "left": "l", "right": "r"}], "seed": 1, "n_replicates": 5, "ci_level": 0.9}}
    cp = tmp_path / "config.json"
    _write(cp, config)
    with pytest.raises(PooledRatioError, match="roster"):
        run(cp, tmp_path / "out.json")

def test_missing_denominator_field_refuses_clearly():
    left = {"a": {"num": 1}}
    right = _rows({"a": (0, 1)})
    with pytest.raises(PooledRatioError, match="missing field path 'den'"):
        compare_pooled_ratios(
            left, right, _metadata(left), _metric(), groupings={},
            seed=1, n_replicates=5, ci_level=0.9,
        )
