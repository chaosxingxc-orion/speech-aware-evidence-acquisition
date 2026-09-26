"""One paired-analysis layer (consolidation slice C4d).

Paired left-vs-right contrasts -- delta, saves/harms/ties, an exact sign
test, and a percentile bootstrap CI -- have been implemented separately in
at least four places: ``analysis.dev100_reviewer_audit.bootstrap_gain`` +
``.mcnemar``, ``analysis.dev500_confirmatory_read.paired_comparison`` (which
imports the two functions above), ``analysis.a2t_semantic_agentloop_postseal
._paired_contrast`` + ``._sign_test``, and ``analysis.a2t_select_fill_comparison
._contrast`` + ``._sign_test`` + ``.tier_stratified_paired_bootstrap``. All
four compute the SAME underlying quantities on the SAME kind of input (two
sample_id -> per-metric-score mappings); this module is the one place that
does it, reused instead of re-implemented.

Sign test is McNemar exact
---------------------------
The sign test both postseal modules compute (``exact-two-sided-paired-sign-
test``: ``tail = sum(comb(n, k) for k in range(min(a, b) + 1)) / 2**n``,
``p = min(1.0, 2 * tail)``) is, term for term, the same exact-binomial
two-sided McNemar computation as ``dev100_reviewer_audit.mcnemar``'s
``exact_binomial_two_sided_p``. :func:`mcnemar_exact` implements it once;
:func:`paired_contrast`'s ``sign_test_p`` is exactly
``mcnemar_exact(saves, harms)``.

Delta convention
-----------------
``delta = right_mean - left_mean`` (a positive delta means ``right`` is
better). ``saves`` counts samples where ``right`` beats ``left`` on the
metric, ``harms`` counts samples where ``left`` beats ``right``, ``ties``
the remainder. For a binary 0/1 metric this is literally "right recovers a
left failure" (saves) vs "right breaks a left success" (harms); for a
continuous metric it is a win/loss/tie count by the SIGN of the paired
difference, the same construction ``dev500_confirmatory_read.paired_comparison``
calls ``wrong_to_correct``/``correct_to_wrong`` and
``a2t_select_fill_comparison._contrast`` calls ``saves``/``harms``.

Stratified and clustered resampling
-------------------------------------
Passing ``strata_of`` reproduces ``a2t_select_fill_comparison
.tier_stratified_paired_bootstrap``'s exact resampling rule: strata are
processed in ascending name order, and EACH stratum is resampled
independently, with replacement, to its OWN size (not proportionally to the
pooled n) -- one shared ``random.Random(seed)`` instance is advanced across
strata in that order. Passing ``cluster_of`` resamples at the CLUSTER level
instead of the per-sample level: cluster keys (not individual sample ids)
are drawn with replacement, and a replicate's resampled id list is the
concatenation of every member of the drawn clusters. Passing both resamples
clusters independently within each stratum (every member of a cluster must
share one stratum, checked). Passing neither calls
``analysis.bootstrap.paired_cluster_bootstrap`` directly and unmodified.

Pooled statistics (2026-09-06, the Earnings window ruling)
-----------------------------------------------------------
:func:`paired_contrast`'s own bootstrap statistic is fixed: the MEAN of the
per-unit differences. That is right for a per-unit score (an exact-match flag, a
per-utterance F1) and wrong for a POOLED RATIO -- corpus WER and ConEC entity WER
are ``sum(errors) / sum(reference words)`` over the units, never an average of
per-unit rates, so a thin 8-second tail window would otherwise weigh as much as a
dense 90-second one. :func:`resampled_statistic` exposes the SAME stratum/cluster
resampling machinery for an arbitrary caller-supplied statistic, so a pooled ratio
gets the identical draws (same seed, same rule, same replicate sequence) as the
mean does -- one resampler, two estimators, never a second implementation of
"resample clusters with replacement".

One bootstrap is one unit of work (2026-09-26)
-----------------------------------------------
A percentile bootstrap of 10,000 draws over a 625-row roster is minutes of
pure-Python arithmetic, and a read asks for a dozen of them. They are
independent -- :func:`_bootstrap_result` seeds a FRESH ``random.Random`` per
bootstrap, so a bootstrap's replicate sequence is a function of its seed
alone and never of how many ran before it in the same process -- which is
what makes them safe to run in any order, in any process.

:func:`paired_contrast_bootstrap_tasks` exposes exactly that: one
zero-argument callable per metric, carrying the SAME statistic, the SAME
resampling rule and the SAME ``seed + offset`` this module has always used,
so a caller can hand them to ``analysis.parallel.map_by_key`` and give the
results back to :func:`paired_contrast` through its ``bootstraps`` argument.
The seed-offset convention stays HERE, in one place; a caller never
reconstructs it. ``paired_contrast`` with no ``bootstraps`` is byte-for-byte
what it always was.
"""

from __future__ import annotations

import functools
import json
import math
import random
import statistics
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable, Mapping, Sequence

from . import bootstrap as bs
from .bootstrap import BootstrapResult

RESULT_SCHEMA = "saea-paired-contrast-v1"

__all__ = [
    "RESULT_SCHEMA",
    "PairedAnalysisError",
    "StratumRow",
    "PairedContrast",
    "mcnemar_exact",
    "paired_contrast",
    "resampled_statistic",
    "per_sample_scores_from_score_file",
    "per_stratum_table",
    "render_markdown",
]


class PairedAnalysisError(ValueError):
    """A paired-analysis input is malformed -- fail closed, never guess."""


@dataclass(frozen=True)
class StratumRow:
    """One stratum's descriptive paired outcome for one metric."""

    stratum: str
    n: int
    left_mean: float
    right_mean: float
    delta: float
    saves: int
    harms: int
    ties: int

    def as_dict(self) -> dict[str, object]:
        return {
            "stratum": self.stratum,
            "n": self.n,
            "left_mean": self.left_mean,
            "right_mean": self.right_mean,
            "delta": self.delta,
            "saves": self.saves,
            "harms": self.harms,
            "ties": self.ties,
        }


@dataclass(frozen=True)
class PairedContrast:
    """One metric's complete paired left-vs-right contrast."""

    metric: str
    n: int
    left_mean: float
    right_mean: float
    delta: float
    saves: int
    harms: int
    ties: int
    sign_test_p: float
    bootstrap: BootstrapResult | None
    per_stratum: Mapping[str, StratumRow]

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric,
            "n": self.n,
            "left_mean": self.left_mean,
            "right_mean": self.right_mean,
            "delta": self.delta,
            "saves": self.saves,
            "harms": self.harms,
            "ties": self.ties,
            "sign_test_p": self.sign_test_p,
            "bootstrap": self.bootstrap.as_json() if self.bootstrap is not None else None,
            "per_stratum": {
                name: row.as_dict() for name, row in sorted(self.per_stratum.items())
            },
        }


def mcnemar_exact(n01: int, n10: int) -> float:
    """Exact two-sided binomial McNemar p-value on ``n01``/``n10`` discordant pairs.

    Moved from ``dev100_reviewer_audit.mcnemar``'s ``exact_binomial_two_sided_p``
    computation: ``tail = sum(comb(n, k) for k in range(min(n01, n10) + 1)) /
    2**n``, ``p = min(1.0, 2 * tail)``, where ``n = n01 + n10``. Zero discordant
    pairs (``n == 0``) is defined here as ``p = 1.0`` -- no evidence of a
    directional effect -- where the original dict-returning ``mcnemar`` left the
    field absent entirely.

    2026-09-05 defect fix (Earnings-22 DEV prompt A/B: 686 saves and 821 harms,
    n = 1,507 discordant pairs). The original spelling multiplied the exact integer numerator by the
    float ``0.5**n``. Both halves break above a few thousand pairs: ``0.5**n``
    UNDERFLOWS to 0.0 for ``n > 1074``, and the numerator -- which can exceed
    ``2**5000`` -- OVERFLOWS when Python coerces it to float for the
    multiplication, raising ``OverflowError: int too large to convert to
    float``. The rosters this repository ran before were small enough to stay
    inside the float range and never reached it.

    The fix keeps the computation EXACT and changes no returned value in the
    range where the old spelling worked: the ratio is formed as a
    :class:`fractions.Fraction` of two exact integers and converted once, which
    is correctly rounded for any magnitude and yields a true 0.0 only when the
    real value is below the smallest positive double. No approximation, no
    log-space term, no change of definition.
    """

    if isinstance(n01, bool) or not isinstance(n01, int) or n01 < 0:
        raise PairedAnalysisError("n01 must be a nonnegative integer")
    if isinstance(n10, bool) or not isinstance(n10, int) or n10 < 0:
        raise PairedAnalysisError("n10 must be a nonnegative integer")
    n = n01 + n10
    if n == 0:
        return 1.0
    smaller = min(n01, n10)
    numerator = sum(math.comb(n, k) for k in range(smaller + 1))
    tail = Fraction(numerator, 1 << n)
    return min(1.0, float(2 * tail))


def _percentile(values: Sequence[float], fraction: float) -> float:
    return bs._percentile(sorted(values), fraction)


def _validate_scores(
    table: Mapping[str, Mapping[str, float]], label: str
) -> Mapping[str, Mapping[str, float]]:
    if not isinstance(table, Mapping) or not table:
        raise PairedAnalysisError(f"{label} must be a non-empty mapping")
    for sample_id, row in table.items():
        if not isinstance(sample_id, str) or not sample_id:
            raise PairedAnalysisError(f"{label} has a non-text sample id")
        if not isinstance(row, Mapping):
            raise PairedAnalysisError(f"{label}[{sample_id!r}] must be a mapping")
    return table


def _metric_value(
    table: Mapping[str, Mapping[str, float]], sample_id: str, metric: str, label: str
) -> float:
    row = table.get(sample_id)
    if row is None or metric not in row:
        raise PairedAnalysisError(f"{label}[{sample_id!r}] is missing metric {metric!r}")
    value = row[metric]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PairedAnalysisError(
            f"{label}[{sample_id!r}][{metric!r}] must be a finite number"
        )
    result = float(value)
    if not math.isfinite(result):
        raise PairedAnalysisError(
            f"{label}[{sample_id!r}][{metric!r}] must be finite"
        )
    return result


def _resolve_sample_ids(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    sample_ids: Sequence[str] | None,
) -> tuple[str, ...]:
    if sample_ids is None:
        if set(left) != set(right):
            raise PairedAnalysisError(
                "left and right must carry the exact same sample ids when "
                "sample_ids is not given explicitly"
            )
        return tuple(sorted(left))
    if isinstance(sample_ids, (str, bytes)) or not sample_ids:
        raise PairedAnalysisError("sample_ids must be a non-empty sequence of ids")
    ids = tuple(sample_ids)
    if len(set(ids)) != len(ids):
        raise PairedAnalysisError("sample_ids contains a duplicate")
    missing_left = set(ids) - set(left)
    missing_right = set(ids) - set(right)
    if missing_left or missing_right:
        raise PairedAnalysisError(
            f"sample_ids names ids absent from left ({sorted(missing_left)}) or "
            f"right ({sorted(missing_right)})"
        )
    return ids


def _grouped_strata(
    ids: Sequence[str], strata_of: Callable[[str], str] | None
) -> dict[str, tuple[str, ...]]:
    if strata_of is None:
        return {}
    by_stratum: dict[str, list[str]] = {}
    for sample_id in ids:
        stratum = strata_of(sample_id)
        if not isinstance(stratum, str) or not stratum:
            raise PairedAnalysisError(f"strata_of({sample_id!r}) must return non-empty text")
        by_stratum.setdefault(stratum, []).append(sample_id)
    return {name: tuple(members) for name, members in sorted(by_stratum.items())}


def _grouped_clusters(
    ids: Sequence[str], cluster_of: Callable[[str], str] | None
) -> dict[str, tuple[str, ...]]:
    if cluster_of is None:
        return {}
    by_cluster: dict[str, list[str]] = {}
    for sample_id in ids:
        cluster = cluster_of(sample_id)
        if not isinstance(cluster, str) or not cluster:
            raise PairedAnalysisError(f"cluster_of({sample_id!r}) must return non-empty text")
        by_cluster.setdefault(cluster, []).append(sample_id)
    return {name: tuple(members) for name, members in sorted(by_cluster.items())}


def _bootstrap_result(
    *,
    ids: tuple[str, ...],
    statistic: Callable[[Sequence[str]], float],
    n_replicates: int,
    seed: int,
    ci_level: float,
    strata: Mapping[str, tuple[str, ...]],
    clusters: Mapping[str, tuple[str, ...]],
) -> BootstrapResult:
    point_estimate = float(statistic(ids))

    if not clusters and not strata:
        return bs.paired_cluster_bootstrap(
            sample_ids=ids,
            statistic=statistic,
            n_replicates=n_replicates,
            seed=seed,
            ci_level=ci_level,
        )

    rng = random.Random(seed)
    replicates: list[float] = []

    if clusters and strata:
        # Every cluster member must share one stratum; group clusters by it.
        cluster_stratum: dict[str, str] = {}
        for stratum, members in strata.items():
            member_set = set(members)
            for cluster_name, cluster_members in clusters.items():
                if set(cluster_members) & member_set:
                    if not set(cluster_members) <= member_set:
                        raise PairedAnalysisError(
                            f"cluster {cluster_name!r} spans more than one stratum"
                        )
                    cluster_stratum[cluster_name] = stratum
        clusters_by_stratum: dict[str, list[str]] = {}
        for cluster_name, stratum in cluster_stratum.items():
            clusters_by_stratum.setdefault(stratum, []).append(cluster_name)
        for _ in range(n_replicates):
            resampled: list[str] = []
            for stratum in sorted(clusters_by_stratum):
                names = sorted(clusters_by_stratum[stratum])
                for _pick in range(len(names)):
                    chosen = names[rng.randrange(len(names))]
                    resampled.extend(clusters[chosen])
            replicates.append(float(statistic(tuple(resampled))))
    elif clusters:
        names = sorted(clusters)
        for _ in range(n_replicates):
            resampled = []
            for _pick in range(len(names)):
                chosen = names[rng.randrange(len(names))]
                resampled.extend(clusters[chosen])
            replicates.append(float(statistic(tuple(resampled))))
    else:  # strata only
        for _ in range(n_replicates):
            resampled = []
            for stratum, members in strata.items():
                resampled.extend(
                    members[rng.randrange(len(members))] for _ in members
                )
            replicates.append(float(statistic(tuple(resampled))))

    tail = (1.0 - ci_level) / 2.0
    sigma_hat = statistics.pstdev(replicates) if len(replicates) > 1 else 0.0
    return BootstrapResult(
        point_estimate=point_estimate,
        replicates=tuple(replicates),
        sigma_hat=sigma_hat,
        ci_low=_percentile(replicates, tail),
        ci_high=_percentile(replicates, 1.0 - tail),
        ci_level=ci_level,
        n_replicates=n_replicates,
        seed=seed,
    )


def _stratum_row(
    stratum: str,
    members: Sequence[str],
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    metric: str,
) -> StratumRow:
    left_values = [_metric_value(left, sid, metric, "left") for sid in members]
    right_values = [_metric_value(right, sid, metric, "right") for sid in members]
    saves = sum(1 for lv, rv in zip(left_values, right_values) if rv > lv)
    harms = sum(1 for lv, rv in zip(left_values, right_values) if rv < lv)
    ties = len(members) - saves - harms
    left_mean = sum(left_values) / len(members)
    right_mean = sum(right_values) / len(members)
    return StratumRow(
        stratum=stratum,
        n=len(members),
        left_mean=left_mean,
        right_mean=right_mean,
        delta=right_mean - left_mean,
        saves=saves,
        harms=harms,
        ties=ties,
    )


def _paired_contrast_plan(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    *,
    metrics: Sequence[str],
    sample_ids: Sequence[str] | None,
    strata_of: Callable[[str], str] | None,
    seed: int,
    n_replicates: int,
    ci_level: float,
    cluster_of: Callable[[str], str] | None,
) -> tuple[tuple[str, ...], Mapping[str, tuple[str, ...]], Mapping[str, tuple[str, ...]]]:
    """:func:`paired_contrast`'s validation and grouping, once, so the task
    factory beside it cannot drift from the function that consumes it.

    The checks run in exactly the order and with exactly the messages
    ``paired_contrast`` has always used; the per-metric NAME check stays in
    each caller's own loop, where it always was.
    """

    _validate_scores(left, "left")
    _validate_scores(right, "right")
    if isinstance(metrics, (str, bytes)) or not metrics:
        raise PairedAnalysisError("metrics must be a non-empty sequence of metric names")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PairedAnalysisError("seed must be an integer")
    if isinstance(n_replicates, bool) or not isinstance(n_replicates, int) or n_replicates <= 0:
        raise PairedAnalysisError("n_replicates must be a positive integer")
    if not 0.0 < ci_level < 1.0:
        raise PairedAnalysisError("ci_level must be strictly within (0, 1)")

    ids = _resolve_sample_ids(left, right, sample_ids)
    strata = _grouped_strata(ids, strata_of)
    clusters = _grouped_clusters(ids, cluster_of)
    return ids, strata, clusters


def _paired_metric_statistic(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    metric: str,
) -> Callable[[Sequence[str]], float]:
    """The mean paired difference on one metric -- this module's own bootstrap
    statistic, defined once and used by both the in-line and the task path."""

    def statistic(resampled_ids: Sequence[str], metric_name: str = metric) -> float:
        total = 0.0
        for sid in resampled_ids:
            total += _metric_value(right, sid, metric_name, "right") - _metric_value(
                left, sid, metric_name, "left"
            )
        return total / len(resampled_ids)

    return statistic


def paired_contrast_bootstrap_tasks(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    *,
    metrics: Sequence[str],
    sample_ids: Sequence[str] | None = None,
    strata_of: Callable[[str], str] | None = None,
    seed: int,
    n_replicates: int = 10_000,
    ci_level: float = 0.90,
    cluster_of: Callable[[str], str] | None = None,
) -> dict[str, Callable[[], BootstrapResult]]:
    """``{metric: zero-argument callable}`` -- one independent bootstrap each.

    Every callable is the bootstrap :func:`paired_contrast` would have run
    for that metric: the same statistic, the same ids, the same stratum /
    cluster grouping and the same ``seed + offset``, where ``offset`` is the
    metric's position in ``metrics`` (the convention this module has always
    used, kept here so no caller has to reproduce it). Each seeds a fresh
    ``random.Random``, so the results do not depend on execution order and
    the callables may be run in any order, in any process.

    Hand the returned mapping to ``analysis.parallel.map_by_key`` and give
    the results back to :func:`paired_contrast` as ``bootstraps=``.
    """

    ids, strata, clusters = _paired_contrast_plan(
        left, right, metrics=metrics, sample_ids=sample_ids, strata_of=strata_of,
        seed=seed, n_replicates=n_replicates, ci_level=ci_level, cluster_of=cluster_of,
    )
    tasks: dict[str, Callable[[], BootstrapResult]] = {}
    for offset, metric in enumerate(metrics):
        if not isinstance(metric, str) or not metric:
            raise PairedAnalysisError("every metric name must be non-empty text")
        if metric in tasks:
            raise PairedAnalysisError(f"metric {metric!r} is requested twice")
        tasks[metric] = functools.partial(
            _bootstrap_result,
            ids=ids,
            statistic=_paired_metric_statistic(left, right, metric),
            n_replicates=n_replicates,
            seed=seed + offset,
            ci_level=ci_level,
            strata=strata,
            clusters=clusters,
        )
    return tasks


def paired_contrast(
    left: Mapping[str, Mapping[str, float]],
    right: Mapping[str, Mapping[str, float]],
    *,
    metrics: Sequence[str],
    sample_ids: Sequence[str] | None = None,
    strata_of: Callable[[str], str] | None = None,
    seed: int,
    n_replicates: int = 10_000,
    ci_level: float = 0.90,
    cluster_of: Callable[[str], str] | None = None,
    bootstraps: Mapping[str, BootstrapResult] | None = None,
) -> dict[str, PairedContrast]:
    """Build one :class:`PairedContrast` per metric. ``delta = right - left``.

    ``bootstraps`` accepts the results of
    :func:`paired_contrast_bootstrap_tasks` for THESE metrics -- the same
    bootstraps, already computed elsewhere (in parallel, typically) -- and
    then no bootstrap is run here. Every requested metric must be present;
    a missing or wrongly-typed entry fails closed rather than silently
    falling back to recomputing it, because a silent fallback would hide a
    caller that paired the wrong seeds.
    """

    ids, strata, clusters = _paired_contrast_plan(
        left, right, metrics=metrics, sample_ids=sample_ids, strata_of=strata_of,
        seed=seed, n_replicates=n_replicates, ci_level=ci_level, cluster_of=cluster_of,
    )
    if bootstraps is not None:
        if not isinstance(bootstraps, Mapping):
            raise PairedAnalysisError("bootstraps must be a mapping metric -> BootstrapResult")
        for metric in metrics:
            if not isinstance(metric, str) or not metric:
                continue  # the per-metric loop below raises with the usual message
            if metric not in bootstraps:
                raise PairedAnalysisError(
                    f"bootstraps has no entry for requested metric {metric!r}"
                )
            if not isinstance(bootstraps[metric], BootstrapResult):
                raise PairedAnalysisError(
                    f"bootstraps[{metric!r}] must be a BootstrapResult"
                )

    results: dict[str, PairedContrast] = {}
    for offset, metric in enumerate(metrics):
        if not isinstance(metric, str) or not metric:
            raise PairedAnalysisError("every metric name must be non-empty text")
        left_values = [_metric_value(left, sid, metric, "left") for sid in ids]
        right_values = [_metric_value(right, sid, metric, "right") for sid in ids]
        saves = sum(1 for lv, rv in zip(left_values, right_values) if rv > lv)
        harms = sum(1 for lv, rv in zip(left_values, right_values) if rv < lv)
        ties = len(ids) - saves - harms
        left_mean = sum(left_values) / len(ids)
        right_mean = sum(right_values) / len(ids)

        if bootstraps is not None:
            bootstrap = bootstraps[metric]
        else:
            bootstrap = _bootstrap_result(
                ids=ids,
                statistic=_paired_metric_statistic(left, right, metric),
                n_replicates=n_replicates,
                seed=seed + offset,
                ci_level=ci_level,
                strata=strata,
                clusters=clusters,
            )

        per_stratum = {
            name: _stratum_row(name, members, left, right, metric)
            for name, members in strata.items()
        }

        results[metric] = PairedContrast(
            metric=metric,
            n=len(ids),
            left_mean=left_mean,
            right_mean=right_mean,
            delta=right_mean - left_mean,
            saves=saves,
            harms=harms,
            ties=ties,
            sign_test_p=mcnemar_exact(saves, harms),
            bootstrap=bootstrap,
            per_stratum=per_stratum,
        )
    return results


def resampled_statistic(
    *,
    sample_ids: Sequence[str],
    statistic: Callable[[Sequence[str]], float],
    seed: int,
    n_replicates: int = 10_000,
    ci_level: float = 0.90,
    strata_of: Callable[[str], str] | None = None,
    cluster_of: Callable[[str], str] | None = None,
) -> BootstrapResult:
    """One bootstrap of an ARBITRARY statistic under this module's own stratum /
    cluster resampling rule (module docstring's "Pooled statistics" section).

    ``paired_contrast`` is the right tool when the estimand is the mean of a
    per-unit difference. When it is a pooled ratio -- corpus WER, ConEC entity
    WER, numeric-value accuracy, all of which are ``sum(numerator) /
    sum(denominator)`` over the resampled units -- the caller supplies that ratio
    here and gets the identical draws: ``cluster_of`` resamples whole clusters
    (every member of a drawn cluster is kept, and a cluster drawn twice
    contributes its members twice), ``strata_of`` resamples each stratum to its
    own size, both together resample clusters within strata, and neither is the
    plain per-unit bootstrap.

    ``statistic`` receives the resampled id sequence -- ids REPEAT, and a pooled
    statistic must therefore sum over the sequence rather than over ``set(ids)``.
    """

    if isinstance(sample_ids, (str, bytes)) or not sample_ids:
        raise PairedAnalysisError("sample_ids must be a non-empty sequence of ids")
    ids = tuple(sample_ids)
    if len(set(ids)) != len(ids):
        raise PairedAnalysisError("sample_ids contains a duplicate")
    if not all(isinstance(sample_id, str) and sample_id for sample_id in ids):
        raise PairedAnalysisError("sample_ids must all be non-empty text")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise PairedAnalysisError("seed must be an integer")
    if isinstance(n_replicates, bool) or not isinstance(n_replicates, int) or n_replicates <= 0:
        raise PairedAnalysisError("n_replicates must be a positive integer")
    if not 0.0 < ci_level < 1.0:
        raise PairedAnalysisError("ci_level must be strictly within (0, 1)")
    return _bootstrap_result(
        ids=ids,
        statistic=statistic,
        n_replicates=n_replicates,
        seed=seed,
        ci_level=ci_level,
        strata=_grouped_strata(ids, strata_of),
        clusters=_grouped_clusters(ids, cluster_of),
    )


def per_sample_scores_from_score_file(
    path: Path | str,
    scorer_id: str,
    metrics: Sequence[str],
    *,
    require_verified: bool = True,
) -> dict[str, dict[str, float]]:
    """One scorer's per-sample rows out of a ``core.scoring_batch`` result
    file, in exactly the ``{sample_id: {metric: value}}`` shape
    :func:`paired_contrast` consumes.

    The input is a ``<job_id>.score.json`` as ``core.scoring_batch
    .run_score_batch`` writes it: the verbatim stdout of ``core.driver score
    --manifest ... --include-per-sample``, i.e.::

        {"manifest": ..., "verified": true,
         "scores": {"<scorer_id>": {"aggregate": {...},
                                    "per_sample": [{"sample_id": ..., ...}, ...]}}}

    Without ``--include-per-sample`` the driver emits ONLY each scorer's
    ``aggregate`` block, so a file produced that way has no ``per_sample`` key
    and is refused here rather than silently yielding an empty table.

    Booleans are the reason this is a reader and not a dict comprehension:
    the official Audio2Tool scorer records ``tool_correct`` / ``exact_match``
    as real ``bool`` values, and :func:`paired_contrast`'s own value check
    REJECTS ``bool`` (a deliberate guard against a metric name accidentally
    resolving to a flag). They are the metrics every paired A2T contrast is
    actually about, so this reader converts ``True``/``False`` to ``1.0`` /
    ``0.0`` once, here, and hands ``paired_contrast`` plain floats.

    Fail-closed on everything else: an unreadable or non-object document, a
    missing ``scores`` block, an absent ``scorer_id``, a missing or empty
    ``per_sample`` list, a row without usable text ``sample_id``, a duplicate
    ``sample_id``, a requested metric absent from a row, and a metric whose
    value is neither bool nor a finite number.

    ``require_verified`` (default ``True``) additionally demands
    ``"verified": true``. The driver sets that key only on the
    ``--manifest`` path, which is the one that verifies the bundle's splits,
    traces and hashes; its ``--outputs`` path prints a loud warning and
    ``"verified": false`` precisely because such a result is NOT an audit
    record. A paired contrast that decides an evolution round must never be
    computed over one by accident.
    """

    if not isinstance(scorer_id, str) or not scorer_id:
        raise PairedAnalysisError("scorer_id must be non-empty text")
    if isinstance(metrics, (str, bytes)) or not metrics:
        raise PairedAnalysisError("metrics must be a non-empty sequence of metric names")
    metric_names = tuple(metrics)
    for metric in metric_names:
        if not isinstance(metric, str) or not metric:
            raise PairedAnalysisError("every metric name must be non-empty text")
    if len(set(metric_names)) != len(metric_names):
        raise PairedAnalysisError("metrics contains a duplicate name")

    score_path = Path(path)
    try:
        document = json.loads(score_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PairedAnalysisError(
            f"cannot read score file {score_path}: {error}"
        ) from error
    if not isinstance(document, Mapping):
        raise PairedAnalysisError(f"score file {score_path} must be a JSON object")
    if require_verified and document.get("verified") is not True:
        raise PairedAnalysisError(
            f"score file {score_path} is not a verified manifest score "
            "(\"verified\" is not true); it is not an audit record"
        )

    scores = document.get("scores")
    if not isinstance(scores, Mapping):
        raise PairedAnalysisError(f"score file {score_path} carries no scores object")
    entry = scores.get(scorer_id)
    if not isinstance(entry, Mapping):
        raise PairedAnalysisError(
            f"score file {score_path} carries no scorer {scorer_id!r}; it has "
            f"{sorted(scores)}"
        )
    rows = entry.get("per_sample")
    if not isinstance(rows, list) or not rows:
        raise PairedAnalysisError(
            f"score file {score_path} scorer {scorer_id!r} has no non-empty "
            "per_sample block; re-run the scorer with --include-per-sample"
        )

    table: dict[str, dict[str, float]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise PairedAnalysisError(
                f"score file {score_path} scorer {scorer_id!r} per_sample row "
                f"{index} is not an object"
            )
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise PairedAnalysisError(
                f"score file {score_path} scorer {scorer_id!r} per_sample row "
                f"{index} has no usable sample_id"
            )
        if sample_id in table:
            raise PairedAnalysisError(
                f"score file {score_path} scorer {scorer_id!r} repeats sample_id "
                f"{sample_id!r}"
            )
        values: dict[str, float] = {}
        for metric in metric_names:
            if metric not in row:
                raise PairedAnalysisError(
                    f"score file {score_path} scorer {scorer_id!r} sample "
                    f"{sample_id!r} is missing metric {metric!r}"
                )
            raw = row[metric]
            if isinstance(raw, bool):
                values[metric] = 1.0 if raw else 0.0
                continue
            if not isinstance(raw, (int, float)):
                raise PairedAnalysisError(
                    f"score file {score_path} scorer {scorer_id!r} sample "
                    f"{sample_id!r} metric {metric!r} is not a number"
                )
            number = float(raw)
            if not math.isfinite(number):
                raise PairedAnalysisError(
                    f"score file {score_path} scorer {scorer_id!r} sample "
                    f"{sample_id!r} metric {metric!r} is not finite"
                )
            values[metric] = number
        table[sample_id] = values
    return table


def per_stratum_table(contrast: PairedContrast) -> list[dict[str, object]]:
    """The stratum rows of one contrast, sorted by stratum name."""

    return [row.as_dict() for _, row in sorted(contrast.per_stratum.items())]


def render_markdown(
    contrasts: Mapping[str, PairedContrast],
    *,
    paper_row: Mapping[str, Mapping[str, float]] | None = None,
) -> str:
    """Render every contrast as a markdown table.

    ``paper_row`` (contrast name -> published column name -> value) adds a
    row of published numbers beside the computed ones, for a reviewer to
    compare at a glance.
    """

    if not isinstance(contrasts, Mapping) or not contrasts:
        raise PairedAnalysisError("contrasts must be a non-empty mapping")
    lines: list[str] = []
    for name in sorted(contrasts):
        contrast = contrasts[name]
        lines.append(f"## {name} ({contrast.metric})")
        lines.append("")
        lines.append("| n | left_mean | right_mean | delta | saves | harms | ties | sign_test_p | ci_low | ci_high |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        ci_low = f"{contrast.bootstrap.ci_low:.4f}" if contrast.bootstrap is not None else ""
        ci_high = f"{contrast.bootstrap.ci_high:.4f}" if contrast.bootstrap is not None else ""
        lines.append(
            f"| {contrast.n} | {contrast.left_mean:.4f} | {contrast.right_mean:.4f} | "
            f"{contrast.delta:.4f} | {contrast.saves} | {contrast.harms} | {contrast.ties} | "
            f"{contrast.sign_test_p:.6f} | {ci_low} | {ci_high} |"
        )
        if contrast.per_stratum:
            lines.append("")
            lines.append("| stratum | n | left_mean | right_mean | delta | saves | harms | ties |")
            lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
            for row in per_stratum_table(contrast):
                lines.append(
                    f"| {row['stratum']} | {row['n']} | {row['left_mean']:.4f} | "
                    f"{row['right_mean']:.4f} | {row['delta']:.4f} | {row['saves']} | "
                    f"{row['harms']} | {row['ties']} |"
                )
        if paper_row is not None and name in paper_row:
            lines.append("")
            published = paper_row[name]
            columns = " | ".join(f"{key}={value}" for key, value in sorted(published.items()))
            lines.append(f"published: {columns}")
        lines.append("")
    return "\n".join(lines)
