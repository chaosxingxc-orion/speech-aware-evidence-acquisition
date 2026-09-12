import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic
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
    output = tmp_path / "nested" / "result.json"
    result = run(config_path, output)
    assert result["contrasts"]["r-v-l"]["errors"]["natural_mixture"]["gain_pp"] == pytest.approx(25.0)
    assert result["provenance"]["contacts"] == {"model": 0, "scorer": 0, "reference": 0}
    assert len(result["provenance"]["implementation"]["sha256"]) == 64
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


def test_zero_denominator_cluster_only_unavailable_when_a_realized_draw_is_zero():
    left = _rows({"positive": (1, 1), "zero": (0, 0)})
    right = _rows({"positive": (0, 1), "zero": (0, 0)})
    metadata = _metadata(left, clusters={"positive": "positive", "zero": "zero"})
    safe = compare_pooled_ratios(
        left, right, metadata, _metric(), groupings={},
        seed=1, n_replicates=1, ci_level=0.9,
    )["errors"]["natural_mixture"]
    assert safe["bootstrap"]["n_replicates"] == 1
    failed = compare_pooled_ratios(
        left, right, metadata, _metric(), groupings={},
        seed=0, n_replicates=1, ci_level=0.9,
    )["errors"]["natural_mixture"]
    assert failed["status"] == "available"
    assert failed["bootstrap"] == {
        "status": "unavailable",
        "reason": "at least one realized bootstrap draw has zero pooled denominator",
    }


def test_nested_array_paths_and_summed_numerator_fields():
    left = {"a": {"entity_class_counts": {"__NON_ENTITY__": [2, 1, 10]}}}
    right = {"a": {"entity_class_counts": {"__NON_ENTITY__": [1, 0, 10]}}}
    metric = {
        "nonentity": {
            "numerator_field": [
                "entity_class_counts.__NON_ENTITY__.0",
                "entity_class_counts.__NON_ENTITY__.1",
            ],
            "denominator_field": "entity_class_counts.__NON_ENTITY__.2",
            "direction": "lower",
        }
    }
    result = compare_pooled_ratios(
        left, right, _metadata(left), metric, groupings={},
        seed=2, n_replicates=2, ci_level=0.9,
    )
    assert result["nonentity"]["natural_mixture"]["gain_pp"] == pytest.approx(20.0)


def test_equal_cluster_mean_matches_inherited_call_draws_with_unequal_windows():
    from collections import Counter
    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic

    left = _rows({"a1": (1, 2), "a2": (2, 8), "b1": (9, 9), "c1": (0, 1)})
    right = _rows({"a1": (0, 2), "a2": (1, 8), "b1": (1, 9), "c1": (1, 1)})
    metadata = _metadata(left, clusters={"a1": "a", "a2": "a", "b1": "b", "c1": "c"})
    rates = {"a": 0.2, "b": 8 / 9, "c": -1.0}
    windows = {"a": 2, "b": 1, "c": 1}

    def inherited(ids):
        counts = Counter(metadata[sid]["cluster"] for sid in ids)
        draws = {name: count / windows[name] for name, count in counts.items()}
        return sum(draws[name] * rates[name] for name in draws) / sum(draws.values())

    expected = resampled_statistic(
        sample_ids=tuple(sorted(left)), statistic=inherited, seed=20260903,
        n_replicates=100, ci_level=0.9, cluster_of=lambda sid: metadata[sid]["cluster"],
    )
    result = compare_pooled_ratios(
        left, right, metadata, _metric(), groupings={}, seed=20260903,
        n_replicates=100, ci_level=0.9, include_equal_cluster_mean=True,
    )["errors"]
    equal = result["equal_cluster_mean"]
    for field in ("point_estimate", "ci_low", "ci_high", "sigma_hat"):
        assert equal["bootstrap"][field] == pytest.approx(100 * getattr(expected, field))
    assert equal["gain_pp"] != pytest.approx(result["natural_mixture"]["gain_pp"])
    assert equal["excluded_zero_denominator_clusters"] == []


def test_equal_cluster_omissions_are_explicit_and_undefined_draws_are_not_zero():
    left = _rows({"positive": (1, 1), "zero": (0, 0)})
    right = _rows({"positive": (0, 1), "zero": (0, 0)})
    result = compare_pooled_ratios(
        left, right, _metadata(left), _metric(), groupings={}, seed=0,
        n_replicates=1, ci_level=0.9, include_equal_cluster_mean=True,
    )["errors"]["equal_cluster_mean"]
    assert result["eligible_clusters"] == 1
    assert result["excluded_zero_denominator_clusters"] == ["zero"]
    assert result["gain_pp"] == pytest.approx(100)
    assert result["bootstrap"]["status"] == "unavailable"


def _parallel_config(tmp_path, contrasts, *, max_workers=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    left_path, right_path, meta_path = (
        tmp_path / name for name in ("left.json", "right.json", "meta.json")
    )
    left = [{"id": "a", "num": 1, "den": 2}, {"id": "b", "num": 0, "den": 2}]
    right = [{"id": "a", "num": 0, "den": 2}, {"id": "b", "num": 0, "den": 2}]
    metadata = {
        "rows": {
            "a": {"cluster": "c1", "sector": "x"},
            "b": {"cluster": "c2", "sector": "y"},
        }
    }
    bindings = {
        "left": {
            "path": str(left_path),
            "sha256": _write(left_path, {"rows": left}),
            "rows_key": "rows",
        },
        "right": {
            "path": str(right_path),
            "sha256": _write(right_path, {"rows": right}),
            "rows_key": "rows",
        },
    }
    analysis = {
        "inputs": bindings,
        "metadata": {
            "path": str(meta_path),
            "sha256": _write(meta_path, metadata),
            "rows_key": "rows",
        },
        "id_field": "id",
        "expected_ids_count": 2,
        "cluster_field": "cluster",
        "groupings": {"sector": "sector"},
        "metrics": _metric(),
        "contrasts": contrasts,
        "seed": 3,
        "n_replicates": 10,
        "ci_level": 0.9,
    }
    if max_workers is not None:
        analysis["max_workers"] = max_workers
    return {"execution_profile": "model-free-check", "analysis": analysis}


def test_parallel_contrasts_match_serial_and_preserve_order(tmp_path):
    contrasts = [
        {"name": "first", "left": "left", "right": "right"},
        {"name": "second", "left": "left", "right": "right"},
    ]
    serial_config = tmp_path / "serial.json"
    parallel_config = tmp_path / "parallel.json"
    _write(serial_config, _parallel_config(tmp_path / "serial", contrasts))
    _write(parallel_config, _parallel_config(tmp_path / "parallel", contrasts, max_workers=2))
    serial = run(serial_config, tmp_path / "serial-output.json")
    parallel = run(parallel_config, tmp_path / "parallel-output.json")
    assert list(parallel["contrasts"]) == ["first", "second"]
    assert parallel["contrasts"] == serial["contrasts"]
    assert "max_workers" not in serial["provenance"]
    assert parallel["provenance"]["max_workers"] == 2
    assert parallel["provenance"]["effective_workers"] == 2


@pytest.mark.parametrize("workers", [0, -1, True, False, 1.5])
def test_invalid_analysis_max_workers_refuses(tmp_path, workers):
    config_path = tmp_path / "config.json"
    _write(
        config_path,
        _parallel_config(
            tmp_path / "inputs",
            [{"name": "only", "left": "left", "right": "right"}],
            max_workers=workers,
        ),
    )
    with pytest.raises(PooledRatioError, match="max_workers"):
        run(config_path, tmp_path / "result.json")


def test_default_grouping_resampling_refuses_cross_stratum_cluster():
    left = _rows({"a": (1, 1), "b": (0, 1)})
    right = _rows({"a": (0, 1), "b": (0, 1)})
    metadata = _metadata(
        left,
        strata={"a": "A", "b": "B"},
        clusters={"a": "one-cluster", "b": "one-cluster"},
    )
    with pytest.raises(PooledRatioError, match="not constant inside cluster"):
        compare_pooled_ratios(
            left, right, metadata, _metric(), groupings={"sector": "sector"},
            seed=3, n_replicates=10, ci_level=0.9,
        )


def test_whole_cluster_grouping_uses_shared_resampler_and_frozen_strata():
    left = _rows({
        "ca": (1, 1), "cb": (9, 9),
        "da": (0, 1), "db": (0, 81),
    })
    right = _rows({
        "ca": (0, 1), "cb": (0, 9),
        "da": (0, 1), "db": (0, 81),
    })
    metadata = _metadata(
        left,
        strata={"ca": "A", "cb": "B", "da": "A", "db": "B"},
        clusters={"ca": "c", "cb": "c", "da": "d", "db": "d"},
    )

    result = compare_pooled_ratios(
        left, right, metadata, _metric(), groupings={"sector": "sector"},
        seed=91, n_replicates=50, ci_level=0.9,
        grouping_resampling="whole-cluster",
    )["errors"]
    equal = result["groupings"]["sector"]["equal_stratum"]

    def statistic(sample_ids):
        gains = []
        for stratum in ("A", "B"):
            members = [sid for sid in sample_ids if metadata[sid]["sector"] == stratum]
            gains.append(
                _pooled_ratio(left, members, "num", "den")
                - _pooled_ratio(right, members, "num", "den")
            )
        return sum(gains) / len(gains)

    expected = resampled_statistic(
        sample_ids=tuple(sorted(left)),
        statistic=statistic,
        seed=91,
        n_replicates=50,
        ci_level=0.9,
        cluster_of=lambda sid: metadata[sid]["cluster"],
    )

    assert result["natural_mixture"]["gain_pp"] == pytest.approx(1000 / 92)
    assert equal["gain_pp"] == pytest.approx(30.0)
    for field in ("point_estimate", "ci_low", "ci_high", "sigma_hat"):
        assert equal["bootstrap"][field] == pytest.approx(100 * getattr(expected, field))


def test_whole_cluster_missing_frozen_stratum_marks_bootstrap_unavailable():
    left = _rows({"a": (1, 1), "b": (0, 1)})
    right = _rows({"a": (0, 1), "b": (0, 1)})
    metadata = _metadata(
        left,
        strata={"a": "A", "b": "B"},
        clusters={"a": "cluster-a", "b": "cluster-b"},
    )
    metric = _metric()
    metric["errors"]["zero_denominator"] = "zero"
    grouped = compare_pooled_ratios(
        left, right, metadata, metric, groupings={"sector": "sector"},
        seed=0, n_replicates=1, ci_level=0.9,
        grouping_resampling="whole-cluster",
    )["errors"]["groupings"]["sector"]["equal_stratum"]

    assert grouped["status"] == "available"
    assert grouped["bootstrap"] == {
        "status": "unavailable",
        "reason": "at least one realized bootstrap draw has zero pooled denominator",
    }


def test_run_forwards_opt_in_whole_cluster_grouping_mode(tmp_path):
    left_path, right_path, meta_path = (
        tmp_path / name for name in ("left.json", "right.json", "meta.json")
    )
    left = {"rows": [
        {"id": "a", "num": 1, "den": 1},
        {"id": "b", "num": 0, "den": 1},
    ]}
    right = {"rows": [
        {"id": "a", "num": 0, "den": 1},
        {"id": "b", "num": 0, "den": 1},
    ]}
    metadata = {"rows": {
        "a": {"cluster": "shared", "sector": "A"},
        "b": {"cluster": "shared", "sector": "B"},
    }}
    config = {
        "execution_profile": "model-free-check",
        "analysis": {
            "inputs": {
                "left": {"path": str(left_path), "sha256": _write(left_path, left), "rows_key": "rows"},
                "right": {"path": str(right_path), "sha256": _write(right_path, right), "rows_key": "rows"},
            },
            "metadata": {"path": str(meta_path), "sha256": _write(meta_path, metadata), "rows_key": "rows"},
            "id_field": "id",
            "expected_ids_count": 2,
            "cluster_field": "cluster",
            "groupings": {"sector": "sector"},
            "grouping_resampling": "whole-cluster",
            "metrics": _metric(),
            "contrasts": [{"name": "right-v-left", "left": "left", "right": "right"}],
            "seed": 2,
            "n_replicates": 5,
            "ci_level": 0.9,
        },
    }
    config_path = tmp_path / "config.json"
    _write(config_path, config)
    result = run(config_path, tmp_path / "result.json")

    assert result["contrasts"]["right-v-left"]["errors"]["groupings"]["sector"]["equal_stratum"]["gain_pp"] == pytest.approx(50.0)


def test_metric_zero_denominator_uses_scorer_zero_for_all_point_estimands():
    left = _rows({"zero": (0, 0), "positive": (1, 1)})
    right = _rows({"zero": (0, 0), "positive": (0, 1)})
    metadata = _metadata(
        left,
        strata={"zero": "A", "positive": "B"},
        clusters={"zero": "zero-cluster", "positive": "positive-cluster"},
    )
    metric = _metric()
    metric["errors"]["zero_denominator"] = "zero"

    result = compare_pooled_ratios(
        left, right, metadata, metric, groupings={"sector": "sector"},
        seed=4, n_replicates=10, ci_level=0.9,
        include_equal_cluster_mean=True,
    )["errors"]

    assert result["natural_mixture"]["status"] == "available"
    assert result["natural_mixture"]["gain_pp"] == pytest.approx(100.0)
    assert result["sign_counts"] == {
        "saves": 1,
        "harms": 0,
        "ties": 1,
        "unavailable": 0,
    }
    equal = result["groupings"]["sector"]["equal_stratum"]
    assert equal["status"] == "available"
    assert equal["gain_pp"] == pytest.approx(50.0)
    clusters = result["equal_cluster_mean"]
    assert clusters["eligible_clusters"] == 2
    assert clusters["excluded_zero_denominator_clusters"] == []
    assert clusters["gain_pp"] == pytest.approx(50.0)
