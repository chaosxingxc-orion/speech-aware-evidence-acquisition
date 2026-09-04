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
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
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
    computation (kept byte-identical): ``tail = sum(comb(n, k) for k in
    range(min(n01, n10) + 1)) / 2**n``, ``p = min(1.0, 2 * tail)``, where
    ``n = n01 + n10``. Zero discordant pairs (``n == 0``) is defined here as
    ``p = 1.0`` -- no evidence of a directional effect -- where the original
    dict-returning ``mcnemar`` left the field absent entirely.
    """

    if isinstance(n01, bool) or not isinstance(n01, int) or n01 < 0:
        raise PairedAnalysisError("n01 must be a nonnegative integer")
    if isinstance(n10, bool) or not isinstance(n10, int) or n10 < 0:
        raise PairedAnalysisError("n10 must be a nonnegative integer")
    n = n01 + n10
    if n == 0:
        return 1.0
    smaller = min(n01, n10)
    tail = sum(math.comb(n, k) for k in range(smaller + 1)) * (0.5**n)
    return min(1.0, 2.0 * tail)


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
) -> dict[str, PairedContrast]:
    """Build one :class:`PairedContrast` per metric. ``delta = right - left``."""

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

        def statistic(resampled_ids: Sequence[str], metric_name: str = metric) -> float:
            total = 0.0
            for sid in resampled_ids:
                total += _metric_value(right, sid, metric_name, "right") - _metric_value(
                    left, sid, metric_name, "left"
                )
            return total / len(resampled_ids)

        bootstrap = _bootstrap_result(
            ids=ids,
            statistic=statistic,
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
