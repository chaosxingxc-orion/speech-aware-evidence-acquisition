"""Stratified paired estimators shared by the read driver and the official-scoring step.

ONE implementation, two callers. ``scripts/analysis/stage3_paired_read.py`` computes the
per-stratum table and the three weightings (raw, post-stratified, equal-stratum) when it holds a
per-row stratum (``--strata-source roster-item`` or ``gold-bank``). ``core.scoring_strata``
(``--strata-inside-scorer``, coordinator ruling 2026-09-30) computes the SAME numbers inside the
official-scoring step -- the one place the allowance lets gold be read, after delivery -- when the
roster withholds its per-row stratum and no per-row gold channel is legal (the signed test
sample). Both call the functions below with the same sorted roster ids, the same stratum function
(the gold intent ``scenario_action``), the same cluster function, the same seed and the same draw
count, so both draw the SAME bootstrap indices: :func:`analysis.paired.resampled_statistic` seeds
a fresh ``random.Random(seed)`` per bootstrap, walks strata in ascending name order and resamples
each stratum's clusters in the order the ids arrive. Identical inputs therefore give bit-identical
replicates, point estimates and intervals; nothing here depends on which process runs it.

The formulas (owner, 2026-09-29):

* intent, post-stratified: ``sum_h w_h * mean_h(scenario_action_exact)`` per arm, then right
  minus left; the bootstrap statistic is ``sum_h w_h * delta_h`` over the resampled rows.
* SLU-F1, post-stratified: ``F1(sum_h w_h*TP_h/n_h, sum_h w_h*FP_h/n_h, sum_h w_h*FN_h/n_h)`` per
  arm, then right minus left -- the per-stratum totals are weighted BEFORE the F1 formula is
  applied, never each stratum's own F1.
* equal-stratum: the unweighted mean over strata of the per-stratum deltas.
* raw: the roster's own mixture, exactly the paired roster read's ``stage_contrast`` estimators
  (per-row intent through :func:`analysis.paired.paired_contrast` over the five per-row metrics,
  pooled SLU-F1 through :func:`analysis.paired.resampled_statistic`, no strata).

``w_h`` is the stratum's population share, renormalised over the strata the roster carries.
Every bootstrap here except ``raw`` resamples WITHIN strata.

MODEL-FREE and GOLD-FREE by itself: callers pass rows and a stratum function; this module never
opens a file.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from typing import Callable, Mapping, Sequence

from . import bootstrap as bs
from .null_calibration import f1_of_totals, pooled_f1, pooled_totals
from .paired import paired_contrast, resampled_statistic

INTENT = "scenario_action_exact"
SLU = "slu_f1_micro"

#: The five per-row metrics the paired roster read's ``stage_contrast`` bootstraps together; the
#: raw intent interval depends on the metric order (``paired_contrast`` seeds metric i at
#: ``seed + i``), so it is reproduced with the same tuple.
PER_ROW_METRICS = (
    "scenario_action_exact",
    "scenario_exact",
    "action_exact",
    "slot_f1_exact_f1",
    "slu_f1_f1",
)

#: (tp-fields, fp-fields, fn-fields) of the official pooled SLU-F1 (word + char halves), the
#: paired roster read's ``MICRO_METRICS["slu_f1_micro"]``.
SLU_FIELDS: tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]] = (
    ("slu_f1_word_tp", "slu_f1_char_tp"),
    ("slu_f1_word_fp", "slu_f1_char_fp"),
    ("slu_f1_word_fn", "slu_f1_char_fn"),
)

POST_STRATIFIED_DEFINITION = (
    "population-weighted, post-stratified: intent = sum_h w_h * mean_h(metric) per arm, then "
    "right - left; pooled SLU-F1 = F1(sum_h w_h * TP_h/n_h, sum_h w_h * FP_h/n_h, "
    "sum_h w_h * FN_h/n_h) per arm, then right - left -- the per-stratum TP/FP/FN totals are "
    "weighted and summed BEFORE the F1 formula is applied, never the per-stratum F1 scores "
    "themselves; w_h is the stratum's population share, renormalised over the strata this "
    "roster carries"
)

Rows = Mapping[str, Mapping[str, float]]


class StratifiedPairedError(ValueError):
    """An input cannot be read as a stratified paired contrast."""


def canonical_digest(document: Mapping[str, object], *, exclude: Sequence[str] = ()) -> str:
    """SHA-256 of ``document`` (minus ``exclude`` keys) as canonical JSON: sorted keys, compact
    separators, ASCII -- the receipt hash both the scorer step and the read driver compute."""

    payload = {k: v for k, v in document.items() if k not in set(exclude)}
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Intervals (identical to slurp_paired_roster_read.interval_block)
# --------------------------------------------------------------------------


def _ci(replicates: Sequence[float], level: float) -> tuple[float, float]:
    tail = (1.0 - level) / 2.0
    ordered = sorted(replicates)
    return bs._percentile(ordered, tail), bs._percentile(ordered, 1.0 - tail)


def interval_block(replicates: Sequence[float], point_estimate: float, seed: int) -> dict[str, object]:
    """CI90 and CI95 from ONE replicate set -- byte-for-byte the paired roster read's own block."""

    ci95 = _ci(replicates, 0.95)
    ci90 = _ci(replicates, 0.90)
    return {
        "point_estimate_pp": 100 * point_estimate,
        "sigma_hat_pp": 100 * (statistics.pstdev(replicates) if len(replicates) > 1 else 0.0),
        "ci95_pp": [100 * ci95[0], 100 * ci95[1]],
        "ci95_half_width_pp": 100 * (ci95[1] - ci95[0]) / 2.0,
        "ci90_pp": [100 * ci90[0], 100 * ci90[1]],
        "ci90_half_width_pp": 100 * (ci90[1] - ci90[0]) / 2.0,
        "n_replicates": len(replicates),
        "seed": seed,
        "resampling": "paired whole-cluster bootstrap",
    }


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------


def intent_delta(left: Rows, right: Rows, ids: Sequence[str]) -> float:
    return sum(right[s][INTENT] - left[s][INTENT] for s in ids) / len(ids)


def slu_delta(left: Rows, right: Rows, ids: Sequence[str]) -> float:
    return pooled_f1(right, ids, SLU_FIELDS) - pooled_f1(left, ids, SLU_FIELDS)


def grouped_by_stratum(resampled: Sequence[str], stratum_of: Callable[[str], str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for sample_id in resampled:
        groups[stratum_of(sample_id)].append(sample_id)
    return groups


def post_stratified_intent_statistic(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], left: Rows, right: Rows,
) -> Callable[[Sequence[str]], float]:
    def statistic(resampled: Sequence[str]) -> float:
        groups = grouped_by_stratum(resampled, stratum_of)
        return sum(weights[s] * intent_delta(left, right, members) for s, members in groups.items())

    return statistic


def post_stratified_intent_level(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], rows: Rows, ids: Sequence[str],
) -> float:
    groups = grouped_by_stratum(ids, stratum_of)
    return sum(
        weights[s] * statistics.fmean(rows[sid][INTENT] for sid in members) for s, members in groups.items()
    )


def _weighted_totals(
    weights: Mapping[str, float], groups: Mapping[str, Sequence[str]], rows: Rows, fields,
) -> tuple[float, float, float]:
    totals = [0.0, 0.0, 0.0]
    for stratum, members in groups.items():
        weight, n = weights[stratum], len(members)
        triple = pooled_totals(rows, members, fields)
        totals[0] += weight * triple[0] / n
        totals[1] += weight * triple[1] / n
        totals[2] += weight * triple[2] / n
    return totals[0], totals[1], totals[2]


def post_stratified_slu_statistic(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], left: Rows, right: Rows, fields=SLU_FIELDS,
) -> Callable[[Sequence[str]], float]:
    """Weight each stratum's TP/FP/FN totals (normalised by its resampled row count) before
    pooling; take the micro-F1 once per arm; return right minus left."""

    def statistic(resampled: Sequence[str]) -> float:
        groups = grouped_by_stratum(resampled, stratum_of)
        return (f1_of_totals(_weighted_totals(weights, groups, right, fields))
                - f1_of_totals(_weighted_totals(weights, groups, left, fields)))

    return statistic


def post_stratified_slu_level(
    weights: Mapping[str, float], stratum_of: Callable[[str], str], rows: Rows, ids: Sequence[str], fields=SLU_FIELDS,
) -> float:
    return f1_of_totals(_weighted_totals(weights, grouped_by_stratum(ids, stratum_of), rows, fields))


def equal_stratum_statistic(
    kind: str, stratum_of: Callable[[str], str], left: Rows, right: Rows,
) -> Callable[[Sequence[str]], float]:
    delta = intent_delta if kind == "intent" else slu_delta

    def statistic(resampled: Sequence[str]) -> float:
        groups = grouped_by_stratum(resampled, stratum_of)
        return statistics.fmean(delta(left, right, members) for members in groups.values())

    return statistic


# --------------------------------------------------------------------------
# Population weights
# --------------------------------------------------------------------------


def population_weights(counts: object, strata: Sequence[str], *, label: str) -> dict[str, float]:
    """Population share per stratum, renormalised over ``strata``.

    ``counts`` is ``{"population_counts": {stratum: count}, ...}`` or a bare mapping. A stratum
    in ``strata`` without a count refuses; strata the roster does not carry are dropped.
    """

    mapping = (
        counts.get("population_counts")
        if isinstance(counts, Mapping) and "population_counts" in counts
        else counts
    )
    if not isinstance(mapping, Mapping) or not mapping:
        raise StratifiedPairedError(f"{label} must carry a non-empty {{stratum: count}} mapping")
    wanted = sorted(set(strata))
    missing = [s for s in wanted if s not in mapping]
    if missing:
        raise StratifiedPairedError(
            f"{label} is missing a population count for stratum/strata the roster carries: {missing}"
        )
    values: dict[str, float] = {}
    for stratum in wanted:
        value = mapping[stratum]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or not math.isfinite(value):
            raise StratifiedPairedError(f"{label}[{stratum!r}] must be a nonnegative number")
        values[stratum] = float(value)
    total = sum(values.values())
    if total <= 0:
        raise StratifiedPairedError(f"{label} sums to zero over the roster's own strata")
    return {stratum: values[stratum] / total for stratum in wanted}


def dropped_strata(counts: object, strata: Sequence[str]) -> list[str]:
    mapping = counts.get("population_counts") if isinstance(counts, Mapping) and "population_counts" in counts else counts
    return sorted(set(mapping) - set(strata)) if isinstance(mapping, Mapping) else []


# --------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------


def _check_inputs(left: Rows, right: Rows, ids: Sequence[str], stratum_of: Callable[[str], str]) -> None:
    if not ids or len(set(ids)) != len(ids):
        raise StratifiedPairedError("a stratified paired read needs a non-empty unique roster")
    missing = [s for s in ids if s not in left or s not in right]
    if missing:
        raise StratifiedPairedError(f"{len(missing)} roster rows are missing from an arm's scored rows")
    for sample_id in ids:
        stratum = stratum_of(sample_id)
        if not isinstance(stratum, str) or not stratum:
            raise StratifiedPairedError("every roster row needs a non-empty text stratum")


def stratum_members(ids: Sequence[str], stratum_of: Callable[[str], str]) -> dict[str, list[str]]:
    by_stratum: dict[str, list[str]] = defaultdict(list)
    for sample_id in ids:
        by_stratum[stratum_of(sample_id)].append(sample_id)
    return {s: sorted(by_stratum[s]) for s in sorted(by_stratum)}


def stratum_counts(rows: Rows, members: Sequence[str]) -> dict[str, float]:
    """The per-stratum AGGREGATE counts of one arm: rows, intent-correct rows, and the pooled
    SLU-F1 TP / FP / FN totals (word + char halves)."""

    tp, fp, fn = pooled_totals(rows, members, SLU_FIELDS)
    return {"n": len(members), "intent_correct": sum(rows[s][INTENT] for s in members),
            "tp": tp, "fp": fp, "fn": fn}


def per_stratum_table(
    left: Rows, right: Rows, ids: Sequence[str], *, stratum_of: Callable[[str], str],
    cluster_of: Callable[[str], str], seed: int, draws: int,
) -> dict[str, dict]:
    """Per stratum: n, intent (left/right %, delta, saves, harms, CI95) and pooled SLU-F1 (left/right
    %, delta, CI95), each CI from a bootstrap over that stratum's own rows."""

    table: dict[str, dict] = {}
    for stratum, members in stratum_members(ids, stratum_of).items():
        l_int = [left[s][INTENT] for s in members]
        r_int = [right[s][INTENT] for s in members]
        intent_point = intent_delta(left, right, members)
        slu_point = slu_delta(left, right, members)
        intent_boot = resampled_statistic(
            sample_ids=members, statistic=lambda r: intent_delta(left, right, r),
            seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of,
        )
        slu_boot = resampled_statistic(
            sample_ids=members, statistic=lambda r: slu_delta(left, right, r),
            seed=seed, n_replicates=draws, ci_level=0.95, cluster_of=cluster_of,
        )
        table[stratum] = {
            "n": len(members),
            "intent": {
                "left_pct": 100 * statistics.fmean(l_int),
                "right_pct": 100 * statistics.fmean(r_int),
                "delta_pp": 100 * intent_point,
                "saves": sum(1 for a, b in zip(l_int, r_int) if b > a),
                "harms": sum(1 for a, b in zip(l_int, r_int) if b < a),
                "ci95_pp": interval_block(intent_boot.replicates, intent_point, seed)["ci95_pp"],
            },
            "slu_f1": {
                "left_pct": 100 * pooled_f1(left, members, SLU_FIELDS),
                "right_pct": 100 * pooled_f1(right, members, SLU_FIELDS),
                "delta_pp": 100 * slu_point,
                "ci95_pp": interval_block(slu_boot.replicates, slu_point, seed)["ci95_pp"],
            },
        }
    return table


def equal_stratum_block(
    left: Rows, right: Rows, ids: Sequence[str], *, stratum_of: Callable[[str], str],
    cluster_of: Callable[[str], str], seed: int, draws: int,
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for kind in ("intent", "slu_f1"):
        statistic = equal_stratum_statistic(kind, stratum_of, left, right)
        point = statistic(ids)
        boot = resampled_statistic(
            sample_ids=ids, statistic=statistic, seed=seed, n_replicates=draws, ci_level=0.95,
            strata_of=stratum_of, cluster_of=cluster_of,
        )
        block = interval_block(boot.replicates, point, seed)
        block["resampling"] = "paired cluster bootstrap within scenario strata"
        out[kind] = {"delta_pp": 100 * point, **block}
    return out


def post_stratified_estimates(
    left: Rows, right: Rows, ids: Sequence[str], *, weights: Mapping[str, float],
    stratum_of: Callable[[str], str], cluster_of: Callable[[str], str], seed: int, draws: int,
) -> dict[str, dict]:
    intent_statistic = post_stratified_intent_statistic(weights, stratum_of, left, right)
    intent_point = intent_statistic(ids)
    intent_boot = resampled_statistic(
        sample_ids=ids, statistic=intent_statistic, seed=seed, n_replicates=draws, ci_level=0.95,
        strata_of=stratum_of, cluster_of=cluster_of,
    )
    slu_statistic = post_stratified_slu_statistic(weights, stratum_of, left, right)
    slu_point = slu_statistic(ids)
    slu_boot = resampled_statistic(
        sample_ids=ids, statistic=slu_statistic, seed=seed, n_replicates=draws, ci_level=0.95,
        strata_of=stratum_of, cluster_of=cluster_of,
    )
    return {
        "intent": {
            "left_pct": 100 * post_stratified_intent_level(weights, stratum_of, left, ids),
            "right_pct": 100 * post_stratified_intent_level(weights, stratum_of, right, ids),
            "delta_pp": 100 * intent_point,
            "ci95_pp": interval_block(intent_boot.replicates, intent_point, seed)["ci95_pp"],
        },
        "slu_f1": {
            "left_pct": 100 * post_stratified_slu_level(weights, stratum_of, left, ids),
            "right_pct": 100 * post_stratified_slu_level(weights, stratum_of, right, ids),
            "delta_pp": 100 * slu_point,
            "ci95_pp": interval_block(slu_boot.replicates, slu_point, seed)["ci95_pp"],
        },
    }


def raw_estimates(
    left: Rows, right: Rows, ids: Sequence[str], *, cluster_of: Callable[[str], str], seed: int, draws: int,
) -> dict[str, dict]:
    """The roster's own mixture, reproducing the paired roster read's ``stage_contrast`` numbers
    (per-row intent from ``paired_contrast`` over :data:`PER_ROW_METRICS`, pooled SLU-F1 from an
    unstratified ``resampled_statistic``)."""

    contrasts = paired_contrast(
        left, right, metrics=PER_ROW_METRICS, sample_ids=ids, cluster_of=cluster_of,
        strata_of=None, seed=seed, n_replicates=draws, ci_level=0.95,
    )
    intent = contrasts[INTENT]
    assert intent.bootstrap is not None
    slu = resampled_statistic(
        sample_ids=ids, statistic=lambda r: slu_delta(left, right, r), seed=seed,
        n_replicates=draws, ci_level=0.95, cluster_of=cluster_of,
    )
    return {
        "intent": {
            "left_pct": 100 * intent.left_mean, "right_pct": 100 * intent.right_mean,
            "delta_pp": 100 * intent.delta,
            "ci95_pp": interval_block(intent.bootstrap.replicates, intent.bootstrap.point_estimate, seed)["ci95_pp"],
        },
        "slu_f1": {
            "left_pct": 100 * pooled_f1(left, ids, SLU_FIELDS),
            "right_pct": 100 * pooled_f1(right, ids, SLU_FIELDS),
            "delta_pp": 100 * slu.point_estimate,
            "ci95_pp": interval_block(slu.replicates, slu.point_estimate, seed)["ci95_pp"],
        },
    }


def stratified_paired_read(
    left: Rows, right: Rows, ids: Sequence[str], *, stratum_of: Callable[[str], str],
    cluster_of: Callable[[str], str], weights: Mapping[str, float] | None, seed: int, draws: int,
    include_raw: bool = True,
) -> dict[str, object]:
    """Every stratified number of one pair: per-stratum table, raw, post-stratified (when
    ``weights``), equal-stratum. ``ids`` must be the roster ids in the order the read uses
    (sorted), or the draws differ from the read driver's."""

    ids = list(ids)
    _check_inputs(left, right, ids, stratum_of)
    out: dict[str, object] = {
        "per_stratum": per_stratum_table(left, right, ids, stratum_of=stratum_of,
                                         cluster_of=cluster_of, seed=seed, draws=draws),
        "equal_stratum": equal_stratum_block(left, right, ids, stratum_of=stratum_of,
                                             cluster_of=cluster_of, seed=seed, draws=draws),
    }
    if weights is not None:
        out["post_stratified"] = post_stratified_estimates(
            left, right, ids, weights=weights, stratum_of=stratum_of, cluster_of=cluster_of,
            seed=seed, draws=draws,
        )
    if include_raw:
        out["raw"] = raw_estimates(left, right, ids, cluster_of=cluster_of, seed=seed, draws=draws)
    return out
