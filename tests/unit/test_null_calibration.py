"""Calibration and decision contracts without model or data contact."""

import math

import pytest

from speech_aware_evidence_acquisition.analysis.null_calibration import (
    classify_interval,
    calibrate_null,
    pooled_f1,
)


def test_noninferiority_does_not_imply_equivalence_or_efficacy():
    result = classify_interval(-0.2, 2.0, margin=0.5)
    assert result["noninferior"] is True
    assert result["equivalent"] is False
    assert result["positive"] is False


def test_small_confident_loss_can_be_noninferior():
    result = classify_interval(-0.4, -0.1, margin=0.5)
    assert result["noninferior"] is True
    assert result["positive"] is False
    assert result["unacceptably_inferior"] is False


@pytest.mark.parametrize(
    "lo,hi,margin",
    [
        (1, -1, 1),
        (math.nan, 1, 1),
        (0, math.inf, 1),
        (0, 1, -1),
        (False, 1, 1),
        (0, 1, True),
    ],
)
def test_invalid_interval_refuses(lo, hi, margin):
    with pytest.raises(ValueError):
        classify_interval(lo, hi, margin=margin)


def test_boundary_is_strict():
    assert classify_interval(-1, 1, margin=1)["noninferior"] is False
    assert classify_interval(-0.9, 1, margin=1)["equivalent"] is False
    assert classify_interval(-2, -1, margin=1)["unacceptably_inferior"] is False


def test_pooled_f1_preserves_repeated_cluster_members():
    rows = {
        "a": {"tp": 1.0, "fp": 0.0, "fn": 0.0},
        "b": {"tp": 0.0, "fp": 3.0, "fn": 1.0},
    }
    assert pooled_f1(
        rows, ["a", "a", "b"], (("tp",), ("fp",), ("fn",))
    ) == pytest.approx(0.5)
    assert pooled_f1(rows, ["a", "b"], (("tp",), ("fp",), ("fn",))) == pytest.approx(
        1 / 3
    )


def test_calibration_is_paired_roster_bound_and_unrounded():
    left = {str(i): {"exact": float(i % 2)} for i in range(8)}
    right = {str(i): {"exact": float(i % 3 == 0)} for i in range(8)}
    kwargs = dict(
        sample_ids=["0", "1", "2", "3"],
        metrics=("exact",),
        cluster_of=lambda sid: "speaker-" + str(int(sid) // 2),
        strata_of=lambda sid: "scenario-" + str(int(sid) % 2),
        seed=20260903,
        n_replicates=101,
    )
    result = calibrate_null(left, right, **kwargs)
    assert result["sample_count"] == 4
    assert result["cluster_count"] == 2
    assert result == calibrate_null(left, right, **kwargs)
    entry = result["metrics"]["exact"]
    assert entry["margin_pp"] == (entry["ci90_pp"][1] - entry["ci90_pp"][0]) / 2
    assert entry["direction"] == "right-minus-left"
    assert len(entry["per_stratum"]) == 2


def test_roster_missing_row_refuses():
    with pytest.raises(ValueError):
        calibrate_null(
            {"a": {"m": 0.0}},
            {"b": {"m": 1.0}},
            sample_ids=["a"],
            metrics=["m"],
            cluster_of=lambda _: "s",
            strata_of=lambda _: "x",
            n_replicates=10,
        )


def test_micro_calibration_uses_counts_not_row_mean():
    left = {
        "a": {"m": 1.0, "tp": 10.0, "fp": 0.0, "fn": 0.0},
        "b": {"m": 0.0, "tp": 0.0, "fp": 1.0, "fn": 1.0},
    }
    right = {
        "a": {"m": 0.0, "tp": 0.0, "fp": 10.0, "fn": 10.0},
        "b": {"m": 1.0, "tp": 1.0, "fp": 0.0, "fn": 0.0},
    }
    result = calibrate_null(
        left,
        right,
        sample_ids=["a", "b"],
        metrics=["m"],
        cluster_of=lambda x: x,
        strata_of=lambda x: x,
        micro_metrics={"micro": (("tp",), ("fp",), ("fn",))},
        n_replicates=20,
    )
    assert result["metrics"]["m"]["delta_pp"] == 0
    assert result["metrics"]["micro"]["delta_pp"] == pytest.approx(-100 * 9 / 11)


def test_negative_counts_refuse():
    with pytest.raises(ValueError):
        pooled_f1(
            {"a": {"tp": -1, "fp": 0, "fn": 0}}, ["a"], (("tp",), ("fp",), ("fn",))
        )
