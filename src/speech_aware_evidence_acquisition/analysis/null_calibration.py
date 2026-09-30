"""Null-only operational calibration using the shared paired resampler.

This scoring-side module never loads a model or invokes a scorer. It separates
one-sided non-inferiority from two-sided equivalence and retains the direction
and unrounded endpoints of an already exposed null pair.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Callable, Mapping, Sequence

from .paired import paired_contrast, resampled_statistic

Counts = tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]


def classify_interval(lower: float, upper: float, *, margin: float) -> dict[str, bool]:
    """Classify percentage-point bounds with strict, signed boundaries."""
    for value in (lower, upper, margin):
        if (
            isinstance(value, bool)
            or not isinstance(value, (float, int))
            or not math.isfinite(value)
        ):
            raise ValueError("interval endpoints and margin must be finite numbers")
    if lower > upper or margin < 0:
        raise ValueError("interval must be ordered and margin nonnegative")
    return {
        "noninferior": lower > -margin,
        "equivalent": lower > -margin and upper < margin,
        "positive": lower > 0,
        "unacceptably_inferior": upper < -margin,
    }


def pooled_totals(
    rows: Mapping[str, Mapping[str, float]],
    sample_ids: Sequence[str],
    fields: Counts,
) -> tuple[float, float, float]:
    """(TP, FP, FN) pooled over the resampled sequence, preserving repeated IDs.

    Shared by :func:`pooled_f1` (pool, then take the F1 of the one total) and the
    population-weighted post-stratified estimator in ``stage3_paired_read.py``, which needs the
    three totals BEFORE they are combined into an F1 -- weighting a stratum's TP/FP/FN and then
    pooling is a different (and correct) number from weighting each stratum's own F1 score.
    """
    totals = [0.0, 0.0, 0.0]
    for sid, multiplicity in Counter(sample_ids).items():
        for index, names in enumerate(fields):
            for name in names:
                value = rows[sid][name]
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ValueError("F1 counts must be numbers")
                if not math.isfinite(value) or value < 0:
                    raise ValueError("F1 counts must be finite and nonnegative")
                totals[index] += multiplicity * value
    return totals[0], totals[1], totals[2]


def f1_of_totals(totals: tuple[float, float, float]) -> float:
    """The micro-F1 of one (TP, FP, FN) triple -- 0.0 by convention when all three are zero."""
    tp, fp, fn = totals
    return 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0


def pooled_f1(
    rows: Mapping[str, Mapping[str, float]],
    sample_ids: Sequence[str],
    fields: Counts,
) -> float:
    """Pool counts over the resampled sequence, preserving repeated IDs."""
    return f1_of_totals(pooled_totals(rows, sample_ids, fields))


def calibrate_null(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    *,
    sample_ids: Sequence[str],
    metrics: Sequence[str],
    cluster_of: Callable[[str], str],
    strata_of: Callable[[str], str],
    micro_metrics: Mapping[str, Counts] | None = None,
    seed: int = 20260903,
    n_replicates: int = 10000,
) -> dict[str, object]:
    """Freeze like-for-like margins; all numeric results are percentage points."""
    ids = tuple(sorted(sample_ids))
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("calibration needs a nonempty unique roster")
    if not set(ids) <= set(left) or not set(ids) <= set(right):
        raise ValueError("both null arms must contain every calibration row")
    contrasts = paired_contrast(
        left,
        right,
        metrics=metrics,
        sample_ids=ids,
        cluster_of=cluster_of,
        seed=seed,
        n_replicates=n_replicates,
        ci_level=0.90,
    )
    entries: dict[str, object] = {}
    for name, contrast in contrasts.items():
        assert contrast.bootstrap is not None
        interval = contrast.bootstrap.as_json()
        lo, hi = 100 * interval["ci_low"], 100 * interval["ci_high"]
        strata: dict[str, object] = {}
        for stratum in sorted({strata_of(sid) for sid in ids}):
            members = [sid for sid in ids if strata_of(sid) == stratum]
            lv = sum(left[sid][name] for sid in members) / len(members)
            rv = sum(right[sid][name] for sid in members) / len(members)
            strata[stratum] = {
                "n": len(members),
                "left_pct": 100 * lv,
                "right_pct": 100 * rv,
                "delta_pp": 100 * (rv - lv),
            }
        entries[name] = {
            "estimand": "mean-per-row",
            "direction": "right-minus-left",
            "left_pct": 100 * contrast.left_mean,
            "right_pct": 100 * contrast.right_mean,
            "delta_pp": 100 * contrast.delta,
            "ci90_pp": [lo, hi],
            "margin_pp": (hi - lo) / 2,
            "saves": contrast.saves,
            "harms": contrast.harms,
            "ties": contrast.ties,
            "sign_test_p": contrast.sign_test_p,
            "per_stratum": strata,
            "equal_stratum_delta_pp": sum(row["delta_pp"] for row in strata.values())
            / len(strata),
        }
    for name, fields in (micro_metrics or {}).items():
        if name in entries:
            raise ValueError("micro and mean estimands must have distinct names")

        def statistic(resampled, fields=fields):
            return pooled_f1(right, resampled, fields) - pooled_f1(
                left, resampled, fields
            )

        interval = resampled_statistic(
            sample_ids=ids,
            statistic=statistic,
            cluster_of=cluster_of,
            seed=seed,
            n_replicates=n_replicates,
            ci_level=0.90,
        ).as_json()
        lo, hi = 100 * interval["ci_low"], 100 * interval["ci_high"]
        strata = {}
        for stratum in sorted({strata_of(sid) for sid in ids}):
            members = [sid for sid in ids if strata_of(sid) == stratum]
            lv, rv = pooled_f1(left, members, fields), pooled_f1(right, members, fields)
            strata[stratum] = {
                "n": len(members),
                "left_pct": 100 * lv,
                "right_pct": 100 * rv,
                "delta_pp": 100 * (rv - lv),
            }
        entries[name] = {
            "estimand": "pooled-count-f1",
            "direction": "right-minus-left",
            "left_pct": 100 * pooled_f1(left, ids, fields),
            "right_pct": 100 * pooled_f1(right, ids, fields),
            "delta_pp": 100 * statistic(ids),
            "ci90_pp": [lo, hi],
            "margin_pp": (hi - lo) / 2,
            "per_stratum": strata,
            "equal_stratum_delta_pp": sum(row["delta_pp"] for row in strata.values())
            / len(strata),
        }
    return {
        "schema": "saea-null-operational-calibration-v1",
        "sample_count": len(ids),
        "cluster_count": len({cluster_of(sid) for sid in ids}),
        "seed": seed,
        "n_replicates": n_replicates,
        "ci_level": 0.90,
        "resampling": "paired-speaker-cluster",
        "margin_basis": "noise-based operational half-width; not a practical-value tolerance",
        "metrics": entries,
    }
