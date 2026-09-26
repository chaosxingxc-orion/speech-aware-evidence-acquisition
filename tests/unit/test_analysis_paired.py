"""``analysis.paired``: the one paired-analysis layer (C4d).

Identity tests reproduce numbers from three already-committed analyses:
(a) the September semantic-104 postseal transcript-vs-direct contrast
    (``docs/checks/speech-aware-evidence-acquisition/
    2026-09-03-a2t-semantic-agentloop-104-v1/postseal-result-summary.json``),
(b) ``dev100_reviewer_audit.mcnemar``'s exact binomial p-value, and
(c) a hand-checkable synthetic 40-row paired set.
"""

from __future__ import annotations

import json
import random

import pytest

from speech_aware_evidence_acquisition.analysis.paired import (
    BootstrapResult,
    PairedAnalysisError,
    mcnemar_exact,
    paired_contrast,
    paired_contrast_bootstrap_tasks,
    per_sample_scores_from_score_file,
    per_stratum_table,
    render_markdown,
    resampled_statistic,
)
from speech_aware_evidence_acquisition.analysis.parallel import map_by_key


# ---------------------------------------------------------------------------
# (a) September semantic-104: transcript_minus_direct_m0.
#
# The committed postseal-result-summary.json carries only the AGGREGATE
# paired_contrasts block (wins/losses/ties, delta, ci90, p_value) -- no
# per-row scores are embedded anywhere in the 5.5KB summary or its sha256-
# pinned sibling artifacts referenced from it, so the exact per-sample
# placement that produced the published bootstrap CI is not recoverable
# here. What IS recoverable, and reproduced bit for bit below, is the
# win/loss/tie multiset, the delta, and the exact sign-test p-value -- the
# sign test depends only on the (saves, harms) counts, never on which
# sample id holds which outcome.
# ---------------------------------------------------------------------------

_EXACT_MATCH_WINS = 10
_EXACT_MATCH_LOSSES = 8
_EXACT_MATCH_TIES = 86
_EXACT_MATCH_DELTA = 0.019230769230769232
_EXACT_MATCH_P = 0.8145294189453125

_TOOL_ACC_WINS = 18
_TOOL_ACC_LOSSES = 9
_TOOL_ACC_TIES = 77
_TOOL_ACC_DELTA = 0.08653846153846154
_TOOL_ACC_P = 0.12207812070846558


def _semantic104_synthetic_tables():
    ids = [f"tier1_direct:{index:06d}" for index in range(104)]
    exact_diffs = [1] * _EXACT_MATCH_WINS + [-1] * _EXACT_MATCH_LOSSES + [0] * _EXACT_MATCH_TIES
    tool_diffs = [1] * _TOOL_ACC_WINS + [-1] * _TOOL_ACC_LOSSES + [0] * _TOOL_ACC_TIES
    assert len(exact_diffs) == len(tool_diffs) == 104
    left: dict[str, dict[str, float]] = {}
    right: dict[str, dict[str, float]] = {}
    for sample_id, exact_diff, tool_diff in zip(ids, exact_diffs, tool_diffs):
        left[sample_id] = {
            "exact_match": 1.0 if exact_diff == -1 else 0.0,
            "tool_accuracy": 1.0 if tool_diff == -1 else 0.0,
        }
        right[sample_id] = {
            "exact_match": 1.0 if exact_diff == 1 else 0.0,
            "tool_accuracy": 1.0 if tool_diff == 1 else 0.0,
        }
    return left, right, tuple(ids)


def test_paired_contrast_reproduces_semantic104_counts_delta_and_sign_test():
    left, right, ids = _semantic104_synthetic_tables()
    contrasts = paired_contrast(
        left, right, metrics=["exact_match", "tool_accuracy"], sample_ids=ids,
        seed=20260903 + 50, n_replicates=500,
    )

    exact = contrasts["exact_match"]
    assert (exact.saves, exact.harms, exact.ties) == (
        _EXACT_MATCH_WINS, _EXACT_MATCH_LOSSES, _EXACT_MATCH_TIES,
    )
    assert exact.delta == pytest.approx(_EXACT_MATCH_DELTA)
    assert exact.sign_test_p == pytest.approx(_EXACT_MATCH_P)
    # the published ci90 is [-0.0480769..., 0.0865384...]; the exact bounds
    # are not reproducible from aggregate-only data (see module docstring),
    # but the point estimate must sit inside whatever CI this run computes.
    assert exact.bootstrap is not None
    assert exact.bootstrap.ci_low <= exact.delta <= exact.bootstrap.ci_high

    tool = contrasts["tool_accuracy"]
    assert (tool.saves, tool.harms, tool.ties) == (
        _TOOL_ACC_WINS, _TOOL_ACC_LOSSES, _TOOL_ACC_TIES,
    )
    assert tool.delta == pytest.approx(_TOOL_ACC_DELTA)
    assert tool.sign_test_p == pytest.approx(_TOOL_ACC_P)
    assert tool.bootstrap.ci_low <= tool.delta <= tool.bootstrap.ci_high


def test_sign_test_p_is_exactly_mcnemar_exact_of_saves_harms():
    left, right, ids = _semantic104_synthetic_tables()
    contrasts = paired_contrast(
        left, right, metrics=["exact_match"], sample_ids=ids, seed=1, n_replicates=10,
    )
    exact = contrasts["exact_match"]
    assert exact.sign_test_p == mcnemar_exact(exact.saves, exact.harms)


# ---------------------------------------------------------------------------
# (b) mcnemar_exact vs dev100_reviewer_audit.mcnemar on 20 random pairs.
# ---------------------------------------------------------------------------


def test_mcnemar_exact_matches_dev100_reviewer_audit_on_random_pairs():
    from speech_aware_evidence_acquisition.analysis import dev100_reviewer_audit as ra

    rng = random.Random(20260903)
    checked = 0
    while checked < 20:
        n01 = rng.randint(0, 30)
        n10 = rng.randint(0, 30)
        if n01 == 0 and n10 == 0:
            continue
        expected = ra.mcnemar(n01, n10)["exact_binomial_two_sided_p"]
        assert mcnemar_exact(n01, n10) == pytest.approx(expected)
        checked += 1


def test_mcnemar_exact_zero_discordant_pairs_is_one():
    assert mcnemar_exact(0, 0) == 1.0


def test_mcnemar_exact_is_symmetric():
    assert mcnemar_exact(3, 11) == mcnemar_exact(11, 3)


def test_mcnemar_exact_survives_thousands_of_discordant_pairs():
    """2026-09-05 regression, from the Earnings-22 DEV prompt A/B contrast.

    That contrast had 686 saves and 821 harms -- 1,507 discordant pairs -- and
    the original ``sum(comb(n, k)) * 0.5**n`` spelling raised ``OverflowError:
    int too large to convert to float``. Both halves of that expression break
    well before this size: ``0.5**n`` underflows to exactly 0.0 for n > 1074,
    and the exact integer numerator (about ``2**1506`` here) exceeds the float
    range, so Python cannot coerce it for the multiplication. Every roster this
    repository had run before was small enough to stay inside the float range.
    """

    p = mcnemar_exact(686, 821)
    assert 0.0 < p <= 1.0
    assert p == pytest.approx(0.0005525225119838559, rel=1e-12)
    assert mcnemar_exact(821, 686) == p
    # An order of magnitude larger still, and still exact.
    assert mcnemar_exact(2853, 2982) == pytest.approx(0.09379357949636571, rel=1e-12)
    # A case that underflows 0.5**n without overflowing the sum.
    assert 0.0 < mcnemar_exact(600, 600) <= 1.0
    # And an extreme where the true value really is below the smallest positive
    # double, so 0.0 is the correctly rounded answer rather than a failure.
    assert mcnemar_exact(10, 5000) == 0.0


def test_mcnemar_exact_rejects_negative_counts():
    with pytest.raises(PairedAnalysisError):
        mcnemar_exact(-1, 3)
    with pytest.raises(PairedAnalysisError):
        mcnemar_exact(3, -1)


# ---------------------------------------------------------------------------
# (c) synthetic 40-row set: delta = right_mean - left_mean, CI containment.
# ---------------------------------------------------------------------------


def test_paired_contrast_synthetic_40_row_delta_and_ci_containment():
    rng = random.Random(7)
    ids = [f"s{index:03d}" for index in range(40)]
    left = {sid: {"score": rng.uniform(0.0, 1.0)} for sid in ids}
    right = {sid: {"score": rng.uniform(0.0, 1.0)} for sid in ids}

    contrasts = paired_contrast(left, right, metrics=["score"], seed=42, n_replicates=500)
    contrast = contrasts["score"]

    expected_delta = (
        sum(right[sid]["score"] for sid in ids) - sum(left[sid]["score"] for sid in ids)
    ) / len(ids)
    assert contrast.n == 40
    assert contrast.delta == pytest.approx(expected_delta)
    assert contrast.right_mean - contrast.left_mean == pytest.approx(expected_delta)
    assert contrast.bootstrap is not None
    assert contrast.bootstrap.ci_low <= contrast.delta <= contrast.bootstrap.ci_high


# ---------------------------------------------------------------------------
# Binary and continuous metrics: saves/harms/ties semantics.
# ---------------------------------------------------------------------------


def test_binary_metric_saves_harms_ties():
    left = {
        "a": {"exact_match": 0.0}, "b": {"exact_match": 1.0}, "c": {"exact_match": 1.0},
        "d": {"exact_match": 0.0}, "e": {"exact_match": 1.0},
    }
    right = {
        "a": {"exact_match": 1.0}, "b": {"exact_match": 0.0}, "c": {"exact_match": 1.0},
        "d": {"exact_match": 0.0}, "e": {"exact_match": 1.0},
    }
    contrasts = paired_contrast(left, right, metrics=["exact_match"], seed=1, n_replicates=50)
    contrast = contrasts["exact_match"]
    # a: 0->1 save, b: 1->0 harm, c: tie(1), d: tie(0), e: tie(1)
    assert (contrast.saves, contrast.harms, contrast.ties) == (1, 1, 3)
    assert contrast.delta == pytest.approx(0.0)


def test_continuous_metric_wins_losses_ties_by_sign_of_difference():
    left = {"a": {"slot_f1": 0.4}, "b": {"slot_f1": 0.9}, "c": {"slot_f1": 0.5}}
    right = {"a": {"slot_f1": 0.6}, "b": {"slot_f1": 0.9}, "c": {"slot_f1": 0.2}}
    contrasts = paired_contrast(left, right, metrics=["slot_f1"], seed=1, n_replicates=50)
    contrast = contrasts["slot_f1"]
    assert (contrast.saves, contrast.harms, contrast.ties) == (1, 1, 1)
    assert contrast.delta == pytest.approx((0.6 - 0.4 + 0.9 - 0.9 + 0.2 - 0.5) / 3)


# ---------------------------------------------------------------------------
# Validation / refusals.
# ---------------------------------------------------------------------------


def test_paired_contrast_refuses_mismatched_ids_without_explicit_sample_ids():
    left = {"a": {"x": 1.0}}
    right = {"b": {"x": 1.0}}
    with pytest.raises(PairedAnalysisError, match="same sample ids"):
        paired_contrast(left, right, metrics=["x"], seed=1, n_replicates=10)


def test_paired_contrast_refuses_empty_metrics():
    left = {"a": {"x": 1.0}}
    right = {"a": {"x": 1.0}}
    with pytest.raises(PairedAnalysisError, match="metrics"):
        paired_contrast(left, right, metrics=[], seed=1, n_replicates=10)


def test_paired_contrast_refuses_non_finite_score():
    left = {"a": {"x": float("nan")}}
    right = {"a": {"x": 1.0}}
    with pytest.raises(PairedAnalysisError, match="finite"):
        paired_contrast(left, right, metrics=["x"], seed=1, n_replicates=10)


# ---------------------------------------------------------------------------
# Stratified and clustered bootstrap.
# ---------------------------------------------------------------------------


def _tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


def test_stratified_bootstrap_is_reproducible_with_a_fixed_seed():
    rng = random.Random(3)
    ids = [f"tier{tier}:{index:03d}" for tier in (1, 2) for index in range(20)]
    left = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    right = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}

    contrasts_a = paired_contrast(
        left, right, metrics=["x"], strata_of=_tier_of, seed=99, n_replicates=300,
    )
    contrasts_b = paired_contrast(
        left, right, metrics=["x"], strata_of=_tier_of, seed=99, n_replicates=300,
    )
    assert contrasts_a["x"].bootstrap.replicates == contrasts_b["x"].bootstrap.replicates
    assert contrasts_a["x"].bootstrap.ci == contrasts_b["x"].bootstrap.ci

    contrasts_c = paired_contrast(
        left, right, metrics=["x"], strata_of=_tier_of, seed=100, n_replicates=300,
    )
    assert contrasts_a["x"].bootstrap.replicates != contrasts_c["x"].bootstrap.replicates


def test_stratified_bootstrap_resamples_each_stratum_to_its_own_size():
    # A degenerate stratum (single constant value) must contribute ZERO
    # variance from its own resampling -- if pooled resampling were used
    # instead, drawing across strata could occasionally imbalance the tiny
    # stratum and change its contribution; per-stratum resampling to a fixed
    # size cannot.
    ids = [f"big:{i:03d}" for i in range(30)] + ["small:000"]
    rng = random.Random(11)
    left = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    right = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    contrasts = paired_contrast(
        left, right, metrics=["x"], strata_of=_tier_of, seed=5, n_replicates=200,
    )
    per_stratum = per_stratum_table(contrasts["x"])
    small = next(row for row in per_stratum if row["stratum"] == "small")
    assert small["n"] == 1
    assert small["delta"] == pytest.approx(right["small:000"]["x"] - left["small:000"]["x"])


def test_clustered_bootstrap_resamples_whole_clusters():
    ids = [f"c{cluster}:{index}" for cluster in range(4) for index in range(5)]
    rng = random.Random(2)
    left = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    right = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}

    def cluster_of(sample_id: str) -> str:
        return sample_id.split(":", 1)[0]

    contrasts = paired_contrast(
        left, right, metrics=["x"], cluster_of=cluster_of, seed=1, n_replicates=100,
    )
    contrast = contrasts["x"]
    assert contrast.bootstrap is not None
    assert contrast.bootstrap.ci_low <= contrast.delta <= contrast.bootstrap.ci_high


# ---------------------------------------------------------------------------
# per_stratum_table / render_markdown smoke tests.
# ---------------------------------------------------------------------------


def test_per_stratum_table_and_render_markdown_smoke():
    ids = [f"tier{tier}:{index:03d}" for tier in (1, 2) for index in range(6)]
    rng = random.Random(4)
    left = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    right = {sid: {"x": rng.uniform(0.0, 1.0)} for sid in ids}
    contrasts = paired_contrast(
        left, right, metrics=["x"], strata_of=_tier_of, seed=1, n_replicates=50,
    )
    table = per_stratum_table(contrasts["x"])
    assert {row["stratum"] for row in table} == {"tier1", "tier2"}
    assert all(row["n"] == 6 for row in table)

    text = render_markdown(
        contrasts, paper_row={"x": {"published_delta": 0.05, "published_ci_low": -0.01}}
    )
    assert "x" in text
    assert "delta" in text
    assert "published_delta=0.05" in text


# ---------------------------------------------------------------------------
# per_sample_scores_from_score_file (E3a, 2026-09-05): the reader that turns a
# `core.scoring_batch` `<job_id>.score.json` into the exact shape
# `paired_contrast` consumes. Fixtures are written in the driver's own output
# shape (`core.driver.cli._cli_score` with --include-per-sample), booleans
# included, because booleans are the reason this reader exists.
# ---------------------------------------------------------------------------

_SCORER = "a2t-toolcall-official"


def _score_document(rows, *, scorer=_SCORER, verified=True):
    return {
        "manifest": "/runs/example/manifest.json",
        "verified": verified,
        "scores": {
            scorer: {
                "aggregate": {"samples": len(rows), "tool_accuracy": 0.5},
                "per_sample": rows,
            }
        },
    }


def _write_score_file(tmp_path, document, name="job.score.json"):
    path = tmp_path / name
    path.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_score_file_reader_converts_booleans_to_floats(tmp_path):
    path = _write_score_file(
        tmp_path,
        _score_document(
            [
                {"sample_id": "tier1_direct:000001", "tool_correct": True, "param_f1": 0.75},
                {"sample_id": "tier1_direct:000002", "tool_correct": False, "param_f1": 0},
            ]
        ),
    )
    table = per_sample_scores_from_score_file(path, _SCORER, ["tool_correct", "param_f1"])
    assert table == {
        "tier1_direct:000001": {"tool_correct": 1.0, "param_f1": 0.75},
        "tier1_direct:000002": {"tool_correct": 0.0, "param_f1": 0.0},
    }
    assert all(isinstance(value, float) for row in table.values() for value in row.values())


def test_score_file_reader_output_is_directly_usable_by_paired_contrast(tmp_path):
    ids = [f"tier1_direct:{index:06d}" for index in range(8)]
    left = _write_score_file(
        tmp_path,
        _score_document(
            [{"sample_id": sid, "tool_correct": index >= 4} for index, sid in enumerate(ids)]
        ),
        name="left.score.json",
    )
    right = _write_score_file(
        tmp_path,
        _score_document(
            [{"sample_id": sid, "tool_correct": index >= 2} for index, sid in enumerate(ids)]
        ),
        name="right.score.json",
    )
    contrasts = paired_contrast(
        per_sample_scores_from_score_file(left, _SCORER, ["tool_correct"]),
        per_sample_scores_from_score_file(right, _SCORER, ["tool_correct"]),
        metrics=["tool_correct"],
        seed=1,
        n_replicates=50,
    )
    contrast = contrasts["tool_correct"]
    assert (contrast.saves, contrast.harms, contrast.ties) == (2, 0, 6)
    assert contrast.delta == pytest.approx(0.25)


def test_score_file_reader_fails_closed_on_a_missing_metric(tmp_path):
    path = _write_score_file(
        tmp_path,
        _score_document(
            [
                {"sample_id": "a", "tool_correct": True},
                {"sample_id": "b"},
            ]
        ),
    )
    with pytest.raises(PairedAnalysisError, match="missing metric 'tool_correct'"):
        per_sample_scores_from_score_file(path, _SCORER, ["tool_correct"])


def test_score_file_reader_fails_closed_on_a_duplicate_sample_id(tmp_path):
    path = _write_score_file(
        tmp_path,
        _score_document(
            [
                {"sample_id": "a", "tool_correct": True},
                {"sample_id": "a", "tool_correct": False},
            ]
        ),
    )
    with pytest.raises(PairedAnalysisError, match="repeats sample_id"):
        per_sample_scores_from_score_file(path, _SCORER, ["tool_correct"])


def test_score_file_reader_fails_closed_on_an_absent_scorer(tmp_path):
    path = _write_score_file(
        tmp_path, _score_document([{"sample_id": "a", "tool_correct": True}])
    )
    with pytest.raises(PairedAnalysisError, match="carries no scorer 'slurp-slu'"):
        per_sample_scores_from_score_file(path, "slurp-slu", ["tool_correct"])


def test_score_file_reader_fails_closed_without_a_per_sample_block(tmp_path):
    # What `core.driver score --manifest` prints WITHOUT --include-per-sample:
    # aggregates only.
    path = _write_score_file(
        tmp_path,
        {
            "manifest": "/runs/example/manifest.json",
            "verified": True,
            "scores": {_SCORER: {"samples": 400, "tool_accuracy": 0.614}},
        },
    )
    with pytest.raises(PairedAnalysisError, match="--include-per-sample"):
        per_sample_scores_from_score_file(path, _SCORER, ["tool_correct"])


def test_score_file_reader_refuses_an_unverified_result_unless_asked(tmp_path):
    path = _write_score_file(
        tmp_path,
        _score_document([{"sample_id": "a", "tool_correct": True}], verified=False),
    )
    with pytest.raises(PairedAnalysisError, match="not an audit record"):
        per_sample_scores_from_score_file(path, _SCORER, ["tool_correct"])
    assert per_sample_scores_from_score_file(
        path, _SCORER, ["tool_correct"], require_verified=False
    ) == {"a": {"tool_correct": 1.0}}


@pytest.mark.parametrize(
    "row, message",
    [
        ({"sample_id": "", "tool_correct": True}, "no usable sample_id"),
        ({"sample_id": "a", "tool_correct": "yes"}, "is not a number"),
        ({"sample_id": "a", "tool_correct": float("nan")}, "is not finite"),
    ],
)
def test_score_file_reader_refuses_malformed_rows(tmp_path, row, message):
    path = tmp_path / "job.score.json"
    # NaN needs a hand-written document: json.dumps emits the bare token NaN,
    # which json.loads accepts back, which is exactly the case under test.
    path.write_text(json.dumps(_score_document([row])), encoding="utf-8")
    with pytest.raises(PairedAnalysisError, match=message):
        per_sample_scores_from_score_file(path, _SCORER, ["tool_correct"])


def test_score_file_reader_refuses_unreadable_or_non_object_documents(tmp_path):
    missing = tmp_path / "absent.score.json"
    with pytest.raises(PairedAnalysisError, match="cannot read score file"):
        per_sample_scores_from_score_file(missing, _SCORER, ["tool_correct"])
    listy = tmp_path / "list.score.json"
    listy.write_text("[]", encoding="utf-8")
    with pytest.raises(PairedAnalysisError, match="must be a JSON object"):
        per_sample_scores_from_score_file(listy, _SCORER, ["tool_correct"])


# ---------------------------------------------------------------------------
# (d) The cluster bootstrap under CORRELATION -- the Earnings window ruling
#     (2026-09-06): the pairing unit is the 90-second window and the cluster is
#     the call. Windows inside one call share a speaker set, an acoustic channel
#     and a vocabulary, so a window-level interval that ignores the call is
#     optimistic. These tests pin the two properties that ruling rests on.
# ---------------------------------------------------------------------------


def _correlated_clusters(
    *, clusters: int, per_cluster: int, cluster_sigma: float, within_sigma: float, seed: int
):
    """Windows whose paired difference is a CALL-level effect plus small
    window-level noise: the dominant variance lives between calls, exactly the
    structure a call-clustered interval has to see and a window-level one cannot."""

    rng = random.Random(seed)
    left: dict[str, dict[str, float]] = {}
    right: dict[str, dict[str, float]] = {}
    for cluster in range(clusters):
        offset = rng.gauss(0.0, cluster_sigma)
        for index in range(per_cluster):
            sample_id = f"call{cluster:03d}#w{index:03d}"
            base = rng.uniform(0.0, 1.0)
            left[sample_id] = {"x": base}
            right[sample_id] = {"x": base + offset + rng.gauss(0.0, within_sigma)}
    return left, right


def _call_of(sample_id: str) -> str:
    return sample_id.split("#", 1)[0]


def test_the_cluster_bootstrap_widens_the_interval_when_windows_are_correlated():
    left, right = _correlated_clusters(
        clusters=20, per_cluster=30, cluster_sigma=0.30, within_sigma=0.02, seed=20260903
    )
    windowed = paired_contrast(
        left, right, metrics=["x"], seed=20260903, n_replicates=2000
    )["x"]
    clustered = paired_contrast(
        left,
        right,
        metrics=["x"],
        cluster_of=_call_of,
        seed=20260903,
        n_replicates=2000,
    )["x"]

    assert windowed.delta == pytest.approx(clustered.delta)
    windowed_width = windowed.bootstrap.ci_high - windowed.bootstrap.ci_low
    clustered_width = clustered.bootstrap.ci_high - clustered.bootstrap.ci_low
    # The honest width is several times the optimistic one: 20 real units, not 600.
    assert clustered_width > 3.0 * windowed_width


def test_the_two_intervals_agree_when_windows_are_independent():
    """The converse guard: clustering is not a blunt widener. With no call-level
    effect at all, resampling whole calls and resampling windows see the same
    variance, so the ruling costs nothing where it buys nothing."""

    left, right = _correlated_clusters(
        clusters=20, per_cluster=30, cluster_sigma=0.0, within_sigma=0.20, seed=20260903
    )
    windowed = paired_contrast(
        left, right, metrics=["x"], seed=20260903, n_replicates=2000
    )["x"]
    clustered = paired_contrast(
        left,
        right,
        metrics=["x"],
        cluster_of=_call_of,
        seed=20260903,
        n_replicates=2000,
    )["x"]
    windowed_width = windowed.bootstrap.ci_high - windowed.bootstrap.ci_low
    clustered_width = clustered.bootstrap.ci_high - clustered.bootstrap.ci_low
    assert 0.6 < clustered_width / windowed_width < 1.6


def test_a_cluster_bootstrap_keeps_every_window_of_a_drawn_call():
    """Resampling is at the CLUSTER level: the statistic never sees a partial
    call, and a call drawn twice contributes all its windows twice."""

    seen: list[tuple[str, ...]] = []

    def statistic(resampled_ids):
        seen.append(tuple(resampled_ids))
        return float(len(resampled_ids))

    ids = [f"call{cluster}#w{index}" for cluster in range(4) for index in range(5)]
    result = resampled_statistic(
        sample_ids=ids,
        statistic=statistic,
        cluster_of=_call_of,
        seed=20260903,
        n_replicates=25,
    )
    assert result.point_estimate == 20.0
    replicates = seen[1:]
    assert len(replicates) == 25
    for draw in replicates:
        assert len(draw) == 20
        counts: dict[str, int] = {}
        for sample_id in draw:
            counts[_call_of(sample_id)] = counts.get(_call_of(sample_id), 0) + 1
        # every drawn call contributes a whole multiple of its five windows
        assert all(count % 5 == 0 for count in counts.values())


def test_resampled_statistic_pools_rather_than_averaging_rates():
    """A pooled ratio and a mean of per-unit rates are different estimands, and
    the Earnings metrics are pooled: two windows, one with 1 error in 100 words
    and one with 1 error in 1 word, pool to 2/101, not to (0.01 + 1.0) / 2."""

    errors = {"c0#w0": 1.0, "c0#w1": 1.0}
    words = {"c0#w0": 100.0, "c0#w1": 1.0}

    def pooled(resampled_ids):
        return sum(errors[sid] for sid in resampled_ids) / sum(
            words[sid] for sid in resampled_ids
        )

    result = resampled_statistic(
        sample_ids=sorted(errors),
        statistic=pooled,
        cluster_of=_call_of,
        seed=20260903,
        n_replicates=10,
    )
    assert result.point_estimate == pytest.approx(2.0 / 101.0)


def test_resampled_statistic_refuses_a_duplicate_id():
    with pytest.raises(PairedAnalysisError, match="duplicate"):
        resampled_statistic(
            sample_ids=["a", "a"], statistic=lambda ids: 0.0, seed=1, n_replicates=2
        )


# ---------------------------------------------------------------------------
# One bootstrap is one unit of work (2026-09-26): the task factory must agree
# with the function that consumes it, to the last bit, at any worker count.
# ---------------------------------------------------------------------------


def _paired_fixture(rows: int = 60):
    """A deterministic paired set with a cluster key and two metrics."""

    left, right = {}, {}
    for index in range(rows):
        sample_id = f"row-{index:03d}"
        left[sample_id] = {
            "exact": float(index % 3 == 0),
            "f1": 0.10 + 0.01 * (index % 11),
        }
        right[sample_id] = {
            "exact": float(index % 4 == 0),
            "f1": 0.12 + 0.01 * ((index * 3) % 11),
        }
    cluster_of = (lambda sid: f"c{int(sid.split('-')[1]) // 3:02d}")
    return left, right, cluster_of


@pytest.mark.parametrize("cluster", [False, True])
def test_bootstrap_tasks_reproduce_paired_contrast_exactly(cluster):
    """The seam is only safe if the tasks are the SAME bootstraps, with the
    same ``seed + position`` offsets, that ``paired_contrast`` would have run."""

    left, right, cluster_of = _paired_fixture()
    kwargs = dict(
        metrics=["exact", "f1"],
        sample_ids=sorted(left),
        seed=20260915,
        n_replicates=200,
        ci_level=0.95,
        cluster_of=cluster_of if cluster else None,
    )
    inline = paired_contrast(left, right, **kwargs)
    tasks = paired_contrast_bootstrap_tasks(left, right, **kwargs)
    assert sorted(tasks) == ["exact", "f1"]
    supplied = paired_contrast(
        left, right, bootstraps={key: task() for key, task in tasks.items()}, **kwargs
    )
    for metric in ("exact", "f1"):
        assert supplied[metric] == inline[metric], metric
        assert supplied[metric].bootstrap.replicates == inline[metric].bootstrap.replicates
        assert supplied[metric].bootstrap.seed == inline[metric].bootstrap.seed


def test_bootstrap_tasks_carry_the_positional_seed_offset():
    left, right, cluster_of = _paired_fixture(20)
    tasks = paired_contrast_bootstrap_tasks(
        left, right, metrics=["exact", "f1"], sample_ids=sorted(left),
        seed=1000, n_replicates=20, ci_level=0.95, cluster_of=cluster_of,
    )
    assert tasks["exact"]().seed == 1000
    assert tasks["f1"]().seed == 1001


@pytest.mark.parametrize("workers", [1, 4])
def test_bootstrap_tasks_through_the_fan_out_are_worker_count_invariant(workers):
    left, right, cluster_of = _paired_fixture()
    tasks = paired_contrast_bootstrap_tasks(
        left, right, metrics=["exact", "f1"], sample_ids=sorted(left),
        seed=20260915, n_replicates=200, ci_level=0.95, cluster_of=cluster_of,
    )
    through_pool = map_by_key(tasks, workers=workers)
    assert list(through_pool) == ["exact", "f1"]
    for metric, task in sorted(tasks.items()):
        assert through_pool[metric] == task(), metric


def test_supplied_bootstraps_refuse_a_missing_metric():
    left, right, _ = _paired_fixture(20)
    tasks = paired_contrast_bootstrap_tasks(
        left, right, metrics=["exact", "f1"], sample_ids=sorted(left),
        seed=1, n_replicates=10, ci_level=0.95,
    )
    with pytest.raises(PairedAnalysisError, match="no entry for requested metric 'f1'"):
        paired_contrast(
            left, right, metrics=["exact", "f1"], sample_ids=sorted(left),
            seed=1, n_replicates=10, ci_level=0.95,
            bootstraps={"exact": tasks["exact"]()},
        )


def test_supplied_bootstraps_refuse_a_wrong_type():
    left, right, _ = _paired_fixture(20)
    with pytest.raises(PairedAnalysisError, match="must be a BootstrapResult"):
        paired_contrast(
            left, right, metrics=["exact"], sample_ids=sorted(left),
            seed=1, n_replicates=10, ci_level=0.95, bootstraps={"exact": 0.5},
        )


def test_supplied_bootstraps_refuse_a_non_mapping():
    left, right, _ = _paired_fixture(20)
    with pytest.raises(PairedAnalysisError, match="bootstraps must be a mapping"):
        paired_contrast(
            left, right, metrics=["exact"], sample_ids=sorted(left),
            seed=1, n_replicates=10, ci_level=0.95, bootstraps=[1, 2],
        )


def test_bootstrap_tasks_refuse_a_repeated_metric():
    left, right, _ = _paired_fixture(20)
    with pytest.raises(PairedAnalysisError, match="requested twice"):
        paired_contrast_bootstrap_tasks(
            left, right, metrics=["exact", "exact"], sample_ids=sorted(left),
            seed=1, n_replicates=10, ci_level=0.95,
        )


def test_bootstrap_tasks_share_paired_contrast_refusals():
    left, right, _ = _paired_fixture(20)
    with pytest.raises(PairedAnalysisError, match="non-empty sequence of metric names"):
        paired_contrast_bootstrap_tasks(
            left, right, metrics=[], sample_ids=sorted(left), seed=1, n_replicates=10
        )
    with pytest.raises(PairedAnalysisError, match="seed must be an integer"):
        paired_contrast_bootstrap_tasks(
            left, right, metrics=["exact"], sample_ids=sorted(left),
            seed="x", n_replicates=10,
        )


def test_several_independent_bootstraps_do_not_depend_on_execution_order():
    """The VAR-1 shape: many arm pairs' bootstraps in one flat batch."""

    left, right, cluster_of = _paired_fixture(40)
    third = {key: {"exact": 1.0 - value["exact"], "f1": value["f1"] * 0.5}
             for key, value in right.items()}
    tasks = {}
    for prefix, other in (("pairA", right), ("pairB", third)):
        for metric, task in paired_contrast_bootstrap_tasks(
            left, other, metrics=["exact", "f1"], sample_ids=sorted(left),
            seed=20260915, n_replicates=100, ci_level=0.95, cluster_of=cluster_of,
        ).items():
            tasks[f"{prefix}|{metric}"] = task
    serial = map_by_key(tasks, workers=1)
    parallel = map_by_key(tasks, workers=4)
    assert serial == parallel
    assert list(serial) == sorted(tasks) == list(parallel)
    assert all(isinstance(value, BootstrapResult) for value in serial.values())
