"""``analysis.bootstrap``: the shared per-sample paired cluster bootstrap
core (P-KEY 2026-08-19 amendment section 7 item 1; reused by the future
P-TRAP read suite, preregistration section 6). Pure stdlib, no model
contact, no I/O -- every test here is a hand-checkable synthetic statistic.
"""

from __future__ import annotations

import random

import pytest

from speech_aware_evidence_acquisition.analysis.bootstrap import (
    DEFAULT_CI_LEVEL,
    DEFAULT_N_REPLICATES,
    DEFAULT_SEED,
    BootstrapError,
    BootstrapResult,
    paired_cluster_bootstrap,
)


def test_default_constants_match_the_registered_discipline():
    # docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md section 7
    # item 1: "N=10,000 replicates, seeded 20260807"; "a 90% CI".
    assert DEFAULT_SEED == 20260807
    assert DEFAULT_N_REPLICATES == 10_000
    assert DEFAULT_CI_LEVEL == 0.90


# ---------------------------------------------------------------------------
# Input validation.
# ---------------------------------------------------------------------------


def test_rejects_empty_sample_ids():
    with pytest.raises(BootstrapError, match="at least one sample id"):
        paired_cluster_bootstrap(sample_ids=(), statistic=lambda ids: 0.0, n_replicates=10)


def test_rejects_non_positive_n_replicates():
    with pytest.raises(BootstrapError, match="n_replicates must be a positive integer"):
        paired_cluster_bootstrap(sample_ids=("a",), statistic=lambda ids: 0.0, n_replicates=0)


def test_rejects_a_bool_n_replicates():
    with pytest.raises(BootstrapError, match="n_replicates must be a positive integer"):
        paired_cluster_bootstrap(sample_ids=("a",), statistic=lambda ids: 0.0, n_replicates=True)


def test_rejects_ci_level_outside_open_unit_interval():
    with pytest.raises(BootstrapError, match="ci_level must be strictly between 0 and 1"):
        paired_cluster_bootstrap(sample_ids=("a",), statistic=lambda ids: 0.0, n_replicates=10, ci_level=1.0)
    with pytest.raises(BootstrapError, match="ci_level must be strictly between 0 and 1"):
        paired_cluster_bootstrap(sample_ids=("a",), statistic=lambda ids: 0.0, n_replicates=10, ci_level=0.0)


# ---------------------------------------------------------------------------
# Determinism.
# ---------------------------------------------------------------------------


def _noisy_statistic(seed_for_noise: int):
    """A per-sample-id lookup that ALSO depends on how many times an id was
    drawn (sum of a per-id value) -- exercises real cluster-resampling
    behaviour (a repeated id contributes its value multiple times), while
    staying fully deterministic given the ids passed in."""

    values = {"s1": 0.10, "s2": 0.30, "s3": 0.50, "s4": 0.70}

    def statistic(ids):
        return sum(values[i] for i in ids) / len(ids)

    return statistic


def test_same_seed_same_inputs_gives_byte_identical_results():
    ids = ("s1", "s2", "s3", "s4")
    result_a = paired_cluster_bootstrap(sample_ids=ids, statistic=_noisy_statistic(0), n_replicates=500, seed=20260807)
    result_b = paired_cluster_bootstrap(sample_ids=ids, statistic=_noisy_statistic(0), n_replicates=500, seed=20260807)
    assert result_a.replicates == result_b.replicates
    assert result_a.sigma_hat == result_b.sigma_hat
    assert result_a.ci == result_b.ci
    assert result_a.point_estimate == result_b.point_estimate


def test_different_seed_gives_a_different_replicate_sequence():
    ids = ("s1", "s2", "s3", "s4")
    result_a = paired_cluster_bootstrap(sample_ids=ids, statistic=_noisy_statistic(0), n_replicates=500, seed=1)
    result_b = paired_cluster_bootstrap(sample_ids=ids, statistic=_noisy_statistic(0), n_replicates=500, seed=2)
    assert result_a.replicates != result_b.replicates


def test_result_reproduces_the_exact_stdlib_random_draw_sequence():
    """Hand-reconstructs the SAME rng draw path this module documents
    (random.Random(seed).randrange(n) once per resampled slot, in order) --
    proves the implementation, not just its own self-consistency."""

    ids = ("a", "b", "c")
    n_replicates = 5

    def statistic(resampled):
        return sum(1.0 for x in resampled if x == "a")

    result = paired_cluster_bootstrap(sample_ids=ids, statistic=statistic, n_replicates=n_replicates, seed=42)

    rng = random.Random(42)
    expected_replicates = []
    for _ in range(n_replicates):
        resampled = tuple(ids[rng.randrange(3)] for _ in range(3))
        expected_replicates.append(float(sum(1.0 for x in resampled if x == "a")))
    assert result.replicates == tuple(expected_replicates)


# ---------------------------------------------------------------------------
# Hand-checkable tiny case: two sample ids, a linear statistic.
#
# With n=2 ids {"lo": 0.0, "hi": 1.0} resampled with replacement, EVERY
# possible resample is one of: (lo, lo) -> 0.0, (hi, hi) -> 1.0, or a mix
# (lo, hi)/(hi, lo) -> 0.5 -- so every replicate MUST be exactly 0.0, 0.5, or
# 1.0, and the point estimate over the unresampled ids is exactly 0.5.
# ---------------------------------------------------------------------------


def test_two_sample_hand_checkable_case_replicates_are_exactly_the_three_possible_means():
    values = {"lo": 0.0, "hi": 1.0}

    def statistic(ids):
        return sum(values[i] for i in ids) / len(ids)

    result = paired_cluster_bootstrap(
        sample_ids=("lo", "hi"), statistic=statistic, n_replicates=2000, seed=20260807
    )
    assert result.point_estimate == pytest.approx(0.5)
    assert set(result.replicates) <= {0.0, 0.5, 1.0}
    # All three outcomes must actually occur at n_replicates=2000 (each has
    # probability >= 0.25 under iid uniform resampling) -- proves the
    # resampling is genuinely exercising all cases, not silently degenerate.
    assert {0.0, 0.5, 1.0} <= set(result.replicates)
    assert 0.0 <= result.ci_low <= result.ci_high <= 1.0
    assert result.sigma_hat > 0.0


def test_constant_statistic_gives_zero_sigma_and_a_degenerate_ci():
    result = paired_cluster_bootstrap(
        sample_ids=("s1", "s2", "s3"), statistic=lambda ids: 7.0, n_replicates=200, seed=1
    )
    assert result.point_estimate == pytest.approx(7.0)
    assert result.sigma_hat == pytest.approx(0.0)
    assert result.ci_low == pytest.approx(7.0)
    assert result.ci_high == pytest.approx(7.0)


def test_single_sample_id_is_always_resampled_to_itself():
    result = paired_cluster_bootstrap(
        sample_ids=("only",), statistic=lambda ids: 3.0 * len(ids), n_replicates=50, seed=9
    )
    assert set(result.replicates) == {3.0}


# ---------------------------------------------------------------------------
# n_replicates == 1 (sigma_hat degenerate case).
# ---------------------------------------------------------------------------


def test_single_replicate_sigma_hat_is_zero_not_a_crash():
    result = paired_cluster_bootstrap(
        sample_ids=("s1", "s2"), statistic=lambda ids: len(ids), n_replicates=1, seed=1
    )
    assert result.sigma_hat == 0.0
    assert len(result.replicates) == 1


# ---------------------------------------------------------------------------
# BootstrapResult.contains / .ci / .as_json.
# ---------------------------------------------------------------------------


def test_contains_is_true_iff_the_entire_ci_is_a_subset():
    result = BootstrapResult(
        point_estimate=0.0, replicates=(-0.01, 0.0, 0.01), sigma_hat=0.005,
        ci_low=-0.02, ci_high=0.02, ci_level=0.90, n_replicates=3, seed=1,
    )
    assert result.contains(-0.03, 0.03) is True
    assert result.contains(-0.015, 0.015) is False  # CI crosses the band
    assert result.ci == (-0.02, 0.02)


def test_as_json_carries_the_summary_fields_only():
    result = BootstrapResult(
        point_estimate=0.1, replicates=(0.1, 0.2), sigma_hat=0.05,
        ci_low=0.05, ci_high=0.15, ci_level=0.90, n_replicates=2, seed=20260807,
    )
    document = result.as_json()
    assert document == {
        "point_estimate": 0.1, "sigma_hat": 0.05, "ci_low": 0.05, "ci_high": 0.15,
        "ci_level": 0.90, "n_replicates": 2, "seed": 20260807,
    }
    assert "replicates" not in document
