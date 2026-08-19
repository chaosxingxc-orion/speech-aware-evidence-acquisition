"""Shared per-sample paired cluster bootstrap resampling core.

Registration-mandated discipline for TWO probes, not one: the P-KEY
2026-08-19 amendment (``docs/readiness/2026-08-18-pkey-preregistration-
REGISTERED.md`` section 7 item 1 -- "the read suite computes a per-sample
paired cluster bootstrap over the 60 samples ... and publishes sigma-hat(I)
and a 90% CI") and the P-TRAP preregistration's own section 6 ("the read
suite computes a per-sample paired bootstrap over the common-denominator
samples and publishes sigma-hat of the V1-V2 capture difference with a 90%
CI"). Both are the SAME primitive -- resample sample ids with replacement,
recompute a caller-supplied statistic per replicate, report sigma-hat and a
percentile CI -- so it lives here ONCE, imported by ``analysis.pkey_read``
now and intended for the future ``analysis.ptrap_read`` (module docstring of
that future module should say the same thing back).

Deliberately carrier-/metric-agnostic: this module knows nothing about
SLU-F1, INTERACTION, capture rates, or any other study-specific quantity --
:func:`paired_cluster_bootstrap` only resamples ids and calls back into a
caller-supplied ``statistic`` function once per replicate. Deliberately
dependency-free: pure stdlib (``random``, ``statistics``), no numpy -- N=10
000 replicates over 60-ish samples is a few hundred thousand float additions,
trivially fast in pure Python, and this keeps the shared primitive usable
without adding a new project dependency.

Deterministic: the SAME ``sample_ids``/``seed``/``n_replicates`` always
produces the SAME replicate sequence, sigma-hat, and CI -- ``random.Random(seed)``
is used throughout, never the process-global ``random`` module (which would
make two calls in the same process observably different, or a re-run on a
different machine silently non-reproducible)."""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass
from typing import Callable, Sequence

# Both registered amendments name this exact seed (P-KEY's own frozen
# 60-sample manifest was itself drawn with it) -- reused here as the shared
# DEFAULT so a caller never has to hand-type it, never as a hidden
# requirement (every parameter below is still overridable).
DEFAULT_SEED = 20260807
DEFAULT_N_REPLICATES = 10_000
DEFAULT_CI_LEVEL = 0.90


class BootstrapError(RuntimeError):
    """Malformed bootstrap input -- never raised for a legitimate data shape
    (a caller's own ``statistic`` is free to encode any domain-specific
    refusal it needs; this module only validates its OWN parameters)."""


@dataclass(frozen=True)
class BootstrapResult:
    """One bootstrap run's full, reviewable output -- never just the CI
    bounds: ``replicates`` is kept (immutable, hashable-shaped) so a caller
    can recompute/report any other percentile or diagnostic without re-
    running the resampling."""

    point_estimate: float
    replicates: tuple[float, ...]
    sigma_hat: float
    ci_low: float
    ci_high: float
    ci_level: float
    n_replicates: int
    seed: int

    @property
    def ci(self) -> tuple[float, float]:
        return (self.ci_low, self.ci_high)

    def contains(self, low: float, high: float) -> bool:
        """``True`` iff this result's ENTIRE CI is a subset of
        ``[low, high]`` -- the exact test both amendments' own equivalence
        clauses (P-KEY KEY-ONLY, P-TRAP KEY-ONLY-MATCHING) require ("the
        ENTIRE CI lies inside ..."), never a point-estimate-only check."""

        return self.ci_low >= low and self.ci_high <= high

    def as_json(self) -> dict[str, object]:
        return {
            "point_estimate": self.point_estimate,
            "sigma_hat": self.sigma_hat,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "ci_level": self.ci_level,
            "n_replicates": self.n_replicates,
            "seed": self.seed,
        }


def _percentile(sorted_values: Sequence[float], fraction: float) -> float:
    """Linear-interpolation percentile over an ALREADY-SORTED sequence
    (``fraction`` in ``[0, 1]``) -- the standard percentile-bootstrap CI
    construction (Efron & Tibshirani's basic percentile method), never a
    nearest-rank shortcut that would silently under-cover at small N."""

    if not sorted_values:
        raise BootstrapError("cannot take a percentile of zero values")
    if len(sorted_values) == 1:
        return sorted_values[0]
    if fraction <= 0.0:
        return sorted_values[0]
    if fraction >= 1.0:
        return sorted_values[-1]
    position = fraction * (len(sorted_values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    weight = position - lower_index
    return sorted_values[lower_index] * (1.0 - weight) + sorted_values[upper_index] * weight


def paired_cluster_bootstrap(
    *,
    sample_ids: Sequence[str],
    statistic: Callable[[Sequence[str]], float],
    n_replicates: int = DEFAULT_N_REPLICATES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapResult:
    """A per-sample paired CLUSTER bootstrap: resample ``sample_ids`` WITH
    replacement (drawing a fresh length-``len(sample_ids)`` multiset on
    every replicate), recompute ``statistic`` on each resampled id list, and
    report sigma-hat (population stdev of the replicate distribution) plus a
    percentile ``ci_level`` CI (default 90%, two-sided: the
    ``(1-level)/2``/``1-(1-level)/2`` quantiles of the replicate
    distribution).

    PAIRED, not four independent bootstraps: the SAME resampled id multiset
    is handed to ``statistic`` as a single argument, so a caller whose own
    ``statistic`` reads MULTIPLE per-sample series internally (P-KEY's own
    four arms) applies the identical resampled draw to every one of them --
    a sample_id drawn twice contributes twice to EVERY series' own replicate
    score, preserving the pairing an interaction/difference contrast depends
    on. This module never sees those series itself; ``statistic`` is where a
    caller closes over its own per-sample data and returns a single float.

    ``point_estimate`` is ``statistic`` evaluated on ``sample_ids`` itself
    (unresampled) -- reported alongside, never derived FROM the replicates
    (a percentile CI need not itself contain the exact point estimate for a
    skewed statistic; that is a property of the data, not a bug here).

    Deterministic (module docstring): ``random.Random(seed)``, drawn via
    ``randrange`` once per resampled slot, in order -- the SAME
    ``sample_ids``/``seed``/``n_replicates`` always reproduces the SAME
    ``replicates`` sequence bit-for-bit."""

    if not sample_ids:
        raise BootstrapError("paired_cluster_bootstrap requires at least one sample id")
    if isinstance(n_replicates, bool) or not isinstance(n_replicates, int) or n_replicates <= 0:
        raise BootstrapError(f"n_replicates must be a positive integer, got {n_replicates!r}")
    if not (0.0 < ci_level < 1.0):
        raise BootstrapError(f"ci_level must be strictly between 0 and 1, got {ci_level!r}")

    ids = tuple(sample_ids)
    point_estimate = float(statistic(ids))

    rng = random.Random(seed)
    n = len(ids)
    replicates: list[float] = []
    for _ in range(n_replicates):
        resampled = tuple(ids[rng.randrange(n)] for _ in range(n))
        replicates.append(float(statistic(resampled)))

    sigma_hat = statistics.pstdev(replicates) if len(replicates) > 1 else 0.0
    ordered = sorted(replicates)
    tail = (1.0 - ci_level) / 2.0
    ci_low = _percentile(ordered, tail)
    ci_high = _percentile(ordered, 1.0 - tail)

    return BootstrapResult(
        point_estimate=point_estimate,
        replicates=tuple(replicates),
        sigma_hat=sigma_hat,
        ci_low=ci_low,
        ci_high=ci_high,
        ci_level=ci_level,
        n_replicates=n_replicates,
        seed=seed,
    )


__all__ = [
    "DEFAULT_CI_LEVEL",
    "DEFAULT_N_REPLICATES",
    "DEFAULT_SEED",
    "BootstrapError",
    "BootstrapResult",
    "paired_cluster_bootstrap",
]
