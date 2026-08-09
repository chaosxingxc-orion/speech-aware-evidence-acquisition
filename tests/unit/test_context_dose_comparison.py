"""R4 (SAEA-E-002) context-dose comparison tool -- synthetic fixtures only,
never real run outputs (this module is a reader over run bundles, not a
generator of them)."""

import json
import statistics
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.context_dose import (
    ARM_NAMES,
    REPORT_SCHEMA,
    AttemptSelection,
    ComparisonError,
    assert_comparable,
    bootstrap_ci,
    build_report,
    corpus_wer,
    find_completed_attempt,
    macro_wer,
    report_to_json,
    wilcoxon_signed_rank_exact,
)
from speech_aware_evidence_acquisition.core.bundle import STATUS_ABORTED, STATUS_COMPLETED
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT, sha256_file

BASELINE_BY_ARM = {
    "nocontext": "bare-core-ojw",
    "matched": "fixed-legal-context-ojw",
    "mismatched": "mismatched-evidence-ojw",
}
_FRAGMENTS = {"model": "qwen3-omni-llamacpp-q4km", "dataset": "r4-e21-sub10", "experiment": "r4-context-dose"}


# ---------------------------------------------------------------------------
# find_completed_attempt: an ABORTED attempt is skipped, a COMPLETED one chosen.
# ---------------------------------------------------------------------------


def _write_manifest(attempt_dir: Path, run_id: str, document: dict) -> Path:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    path = attempt_dir / f"{run_id}.run-manifest.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_find_completed_attempt_skips_aborted_and_picks_completed(tmp_path):
    run_dir = tmp_path / "run"
    aborted_path = _write_manifest(
        run_dir / "attempt-20260809T090000Z-aaaaaa",
        "X",
        {"status": STATUS_ABORTED, "failure_reason": "server died", "created_at": "2026-08-09T09:00:00+00:00"},
    )
    completed_path = _write_manifest(
        run_dir / "attempt-20260809T100000Z-bbbbbb",
        "X",
        {"status": STATUS_COMPLETED, "created_at": "2026-08-09T10:00:00+00:00"},
    )

    selection = find_completed_attempt(run_dir)

    assert selection.manifest_path == completed_path
    assert selection.manifest["status"] == STATUS_COMPLETED
    assert len(selection.skipped) == 1
    assert selection.skipped[0].manifest_path == aborted_path
    assert selection.skipped[0].status == STATUS_ABORTED
    assert "server died" in selection.skipped[0].reason


def test_find_completed_attempt_refuses_when_every_attempt_aborted(tmp_path):
    run_dir = tmp_path / "run"
    _write_manifest(
        run_dir / "attempt-20260809T090000Z-aaaaaa", "X",
        {"status": STATUS_ABORTED, "failure_reason": "OOM"},
    )
    with pytest.raises(ComparisonError, match="no COMPLETED attempt"):
        find_completed_attempt(run_dir)


def test_find_completed_attempt_refuses_when_no_attempt_dirs_exist(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    with pytest.raises(ComparisonError, match="no attempt-\\* subdirectories"):
        find_completed_attempt(run_dir)


def test_find_completed_attempt_refuses_when_run_dir_missing(tmp_path):
    with pytest.raises(ComparisonError, match="does not exist"):
        find_completed_attempt(tmp_path / "never-created")


def test_find_completed_attempt_prefers_most_recent_when_several_completed(tmp_path):
    run_dir = tmp_path / "run"
    old_path = _write_manifest(
        run_dir / "attempt-20260809T090000Z-aaaaaa", "X",
        {"status": STATUS_COMPLETED, "created_at": "2026-08-09T09:00:00+00:00"},
    )
    new_path = _write_manifest(
        run_dir / "attempt-20260809T110000Z-cccccc", "X",
        {"status": STATUS_COMPLETED, "created_at": "2026-08-09T11:00:00+00:00"},
    )

    selection = find_completed_attempt(run_dir)

    assert selection.manifest_path == new_path
    assert selection.other_completed == (old_path,)


# ---------------------------------------------------------------------------
# assert_comparable: the single most important behaviour -- refuse and name
# exactly which field differs.
# ---------------------------------------------------------------------------


def _fake_selection(manifest: dict) -> AttemptSelection:
    return AttemptSelection(Path("run"), Path("run/attempt-x/X.run-manifest.json"), manifest, (), ())


def _manifest(*, identity_hash, ids, baseline, config_hash="h", fragments=None):
    fragments = dict(fragments or _FRAGMENTS)
    fragments["baseline"] = baseline
    return {
        "split": {"identity_hash": identity_hash, "ids": ids},
        "config": {"fragments": fragments, "config_hash": config_hash},
    }


def test_assert_comparable_refuses_on_split_identity_hash_mismatch():
    selections = {
        "nocontext": _fake_selection(_manifest(identity_hash="aaa", ids=["1", "2"], baseline="b1")),
        "matched": _fake_selection(_manifest(identity_hash="bbb", ids=["1", "2"], baseline="b2")),
        "mismatched": _fake_selection(_manifest(identity_hash="aaa", ids=["1", "2"], baseline="b3")),
    }
    with pytest.raises(ComparisonError, match="split.identity_hash differs"):
        assert_comparable(selections, repo_root=Path("unused"))


def test_assert_comparable_refuses_on_split_ids_mismatch():
    selections = {
        "nocontext": _fake_selection(_manifest(identity_hash="same", ids=["1", "2"], baseline="b1")),
        "matched": _fake_selection(_manifest(identity_hash="same", ids=["1", "3"], baseline="b2")),
        "mismatched": _fake_selection(_manifest(identity_hash="same", ids=["1", "2"], baseline="b3")),
    }
    with pytest.raises(ComparisonError, match="split.ids differ"):
        assert_comparable(selections, repo_root=Path("unused"))


def test_assert_comparable_refuses_when_a_non_baseline_fragment_differs():
    selections = {
        "nocontext": _fake_selection(
            _manifest(identity_hash="same", ids=["1"], baseline="b1", fragments={**_FRAGMENTS, "dataset": "d1"})
        ),
        "matched": _fake_selection(
            _manifest(identity_hash="same", ids=["1"], baseline="b2", fragments={**_FRAGMENTS, "dataset": "d2"})
        ),
        "mismatched": _fake_selection(
            _manifest(identity_hash="same", ids=["1"], baseline="b3", fragments={**_FRAGMENTS, "dataset": "d1"})
        ),
    }
    with pytest.raises(ComparisonError, match=r"config.fragments\['dataset'\] differs"):
        assert_comparable(selections, repo_root=Path("unused"))


def test_assert_comparable_refuses_when_baselines_are_not_pairwise_distinct():
    selections = {
        "nocontext": _fake_selection(_manifest(identity_hash="same", ids=["1"], baseline="same-baseline")),
        "matched": _fake_selection(_manifest(identity_hash="same", ids=["1"], baseline="same-baseline")),
        "mismatched": _fake_selection(_manifest(identity_hash="same", ids=["1"], baseline="other-baseline")),
    }
    with pytest.raises(ComparisonError, match="pairwise distinct"):
        assert_comparable(selections, repo_root=Path("unused"))


def test_assert_comparable_refuses_on_config_hash_drift():
    """Fragment names agree and baselines are distinct, but the recorded
    config_hash does not match what the COMMITTED fragment files in THIS
    checkout produce -- catches a stale/hand-edited manifest."""

    selections = {
        arm: _fake_selection(
            _manifest(identity_hash="same", ids=["1", "2"], baseline=baseline, config_hash="0" * 64)
        )
        for arm, baseline in BASELINE_BY_ARM.items()
    }
    with pytest.raises(ComparisonError, match="config_hash"):
        assert_comparable(selections, repo_root=REPO_ROOT)


# ---------------------------------------------------------------------------
# corpus vs macro WER: must diverge on uneven reference lengths.
# ---------------------------------------------------------------------------


def test_corpus_and_macro_wer_diverge_on_uneven_reference_lengths():
    per_sample = {
        "a": {"ref_hit_mask": [False] + [True] * 9, "substitutions": 1, "deletions": 0, "insertions": 0, "wer": 0.1},
        "b": {"ref_hit_mask": [False, True], "substitutions": 1, "deletions": 0, "insertions": 0, "wer": 0.5},
    }
    assert corpus_wer(per_sample) == pytest.approx(2 / 12)
    assert macro_wer(per_sample) == pytest.approx(0.3)
    assert corpus_wer(per_sample) != pytest.approx(macro_wer(per_sample))


# ---------------------------------------------------------------------------
# Paired statistics: hand-checkable tiny inputs.
# ---------------------------------------------------------------------------


def test_wilcoxon_signed_rank_exact_on_a_hand_checkable_pair():
    """diffs=[+1, -3]: ranks of |1|,|3| are 1,2 (no ties). observed W+ = 1
    (only the +1 pair contributes). The 4 equally-likely sign assignments
    give statistics {3, 1, 2, 0} (++, +-, -+, --); 2 of them are <=1 and 3
    are >=1, so p_two_sided = 2*min(2,3)/4 = 1.0 -- NOT at the n=2 floor of
    2/4=0.5, a genuinely typical (non-extreme) exact result."""

    result = wilcoxon_signed_rank_exact([1.0, -3.0])
    assert result.n_pairs == 2
    assert result.n_effective == 2
    assert result.statistic == pytest.approx(1.0)
    assert result.pvalue == pytest.approx(1.0)
    assert result.min_two_sided_p == pytest.approx(0.5)


def test_wilcoxon_signed_rank_exact_extreme_case_hits_its_own_floor():
    """diffs=[1,1,1]: all positive, tied magnitude (avg rank 2 each) -> the
    most extreme possible outcome (only 1 of 8 sign assignments matches or
    exceeds it), so p_two_sided must equal min_two_sided_p exactly."""

    result = wilcoxon_signed_rank_exact([1.0, 1.0, 1.0])
    assert result.n_effective == 3
    assert result.statistic == pytest.approx(6.0)
    assert result.pvalue == pytest.approx(0.25)
    assert result.min_two_sided_p == pytest.approx(0.25)
    assert result.pvalue == pytest.approx(result.min_two_sided_p)


def test_wilcoxon_signed_rank_exact_at_n10_matches_the_briefs_stated_floor():
    result = wilcoxon_signed_rank_exact([1.0] * 10)
    assert result.n_effective == 10
    assert result.min_two_sided_p == pytest.approx(2 / 1024)


def test_wilcoxon_signed_rank_exact_drops_zero_diffs():
    result = wilcoxon_signed_rank_exact([0.0, 0.0, 1.0, -3.0])
    assert result.n_pairs == 4
    assert result.n_effective == 2


def test_wilcoxon_signed_rank_exact_all_zero_is_the_null_no_op():
    result = wilcoxon_signed_rank_exact([0.0, 0.0])
    assert result.n_effective == 0
    assert result.pvalue == 1.0
    assert result.min_two_sided_p == 1.0


def test_bootstrap_ci_is_reproducible_and_brackets_its_own_point_estimate():
    diffs = [-0.1, 0.05, -0.2, 0.0, 0.15]
    first = bootstrap_ci(diffs, resamples=2000, seed=42)
    second = bootstrap_ci(diffs, resamples=2000, seed=42)
    assert first == second
    assert first.point_estimate == pytest.approx(statistics.fmean(diffs))
    assert first.ci_low <= first.point_estimate <= first.ci_high
    assert first.resamples == 2000
    assert first.seed == 42


def test_bootstrap_ci_refuses_on_empty_input():
    with pytest.raises(ComparisonError, match="zero paired"):
        bootstrap_ci([], resamples=100, seed=1)


# ---------------------------------------------------------------------------
# build_report: full happy path over synthetic outputs/reference layers.
# ---------------------------------------------------------------------------


def _write_arm_bundle(tmp_path, arm, *, identity_hash, split_ids, hyp_texts):
    from speech_aware_evidence_acquisition.core.config import compose

    run_id = f"SAEA-TEST-{arm}"
    baseline = BASELINE_BY_ARM[arm]
    composed = compose(REPO_ROOT, _FRAGMENTS["model"], _FRAGMENTS["dataset"], baseline, _FRAGMENTS["experiment"])
    run_dir = tmp_path / f"runs-{arm}"
    attempt_dir = run_dir / "attempt-20260809T100000Z-000001"
    attempt_dir.mkdir(parents=True)
    outputs_path = attempt_dir / f"{run_id}.outputs.jsonl"
    rows = [
        {
            "sample_id": sample_id, "carrier_lock_key": "earnings21-original", "arm": arm,
            "request_id": f"req-{sample_id}", "text": hyp_texts[sample_id],
            "request_sha256": "0" * 64, "response_sha256": "0" * 64,
        }
        for sample_id in split_ids
    ]
    outputs_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    manifest = {
        "schema": "saea-run-manifest-v1",
        "run_id": run_id,
        "created_at": "2026-08-09T10:00:00+00:00",
        "status": STATUS_COMPLETED,
        "failure_reason": None,
        "arm": baseline,
        "config": {"fragments": composed.fragments, "config_hash": composed.config_hash},
        "split": {"identity_hash": identity_hash, "ids": sorted(split_ids)},
        "outputs": {"path": str(outputs_path), "sha256": sha256_file(outputs_path)},
        "attempt": {"run_id": run_id, "attempt_id": "attempt-20260809T100000Z-000001"},
    }
    _write_manifest(attempt_dir, run_id, manifest)
    return run_dir


def test_build_report_end_to_end_happy_path(tmp_path, synthetic_world):
    nlp_dir = synthetic_world.e21 / "transcripts" / "nlp_references"
    (nlp_dir / "4000001.nlp").write_text("token|tags\nthe|\nquick|\nbrown|\nfox|\n", encoding="utf-8")
    (nlp_dir / "4000002.nlp").write_text("token|tags\nhello|\nworld|\ntoday|\n", encoding="utf-8")
    (nlp_dir / "4000003.nlp").write_text("token|tags\none|\ntwo|\nthree|\nfour|\nfive|\n", encoding="utf-8")

    split_ids = ["4000001", "4000002", "4000003"]
    identity_hash = "deadbeef" * 8
    hyp_texts = {
        "nocontext": {
            "4000001": "the quick brown fox", "4000002": "hello world", "4000003": "one two three four five",
        },
        "matched": {
            "4000001": "the quick brown fox", "4000002": "hello world today", "4000003": "one two three four five",
        },
        "mismatched": {
            "4000001": "the quick brown cat", "4000002": "hello word today", "4000003": "one two three four",
        },
    }
    run_dirs = {
        arm: _write_arm_bundle(tmp_path, arm, identity_hash=identity_hash, split_ids=split_ids, hyp_texts=hyp_texts[arm])
        for arm in ARM_NAMES
    }

    lock = load_lock(synthetic_world.lock_path)
    report = build_report(run_dirs, lock, synthetic_world.data_root, repo_root=REPO_ROOT)

    assert set(report.arms) == set(ARM_NAMES)
    for arm in ARM_NAMES:
        assert report.aggregate[arm]["n"] == 3

    # hand-computed: nocontext drops "today" on 4000002 (1 deletion, ref len 3);
    # everything else is exact.
    assert report.aggregate["nocontext"]["macro_wer"] == pytest.approx((0 + 1 / 3 + 0) / 3)
    assert report.aggregate["nocontext"]["corpus_wer"] == pytest.approx(1 / 12)
    # matched: every sample transcribed exactly.
    assert report.aggregate["matched"]["macro_wer"] == pytest.approx(0.0)
    assert report.aggregate["matched"]["corpus_wer"] == pytest.approx(0.0)
    # mismatched: one substitution/substitution/deletion, one error per sample.
    assert report.aggregate["mismatched"]["corpus_wer"] == pytest.approx(3 / 12)

    assert set(report.contrasts) == {"matched_vs_nocontext", "mismatched_vs_nocontext", "matched_vs_mismatched"}
    matched_vs_mismatched = report.contrasts["matched_vs_mismatched"]
    assert matched_vs_mismatched.bootstrap_mean.point_estimate < 0  # matched arm is better

    document = report_to_json(report)
    assert document["schema"] == REPORT_SCHEMA
    assert document["comparability"]["ok"] is True
    assert document["comparability"]["n_samples"] == 3
    assert document["comparability"]["split_identity_hash"] == identity_hash
    assert set(document["per_sample"]) == set(split_ids)
    assert document["arms"]["nocontext"]["baseline_fragment"] == "bare-core-ojw"


def test_build_report_refuses_when_arms_use_mismatched_sample_ids(tmp_path, synthetic_world):
    nlp_dir = synthetic_world.e21 / "transcripts" / "nlp_references"
    for sample_id in ("4000001", "4000002", "4000003"):
        (nlp_dir / f"{sample_id}.nlp").write_text("token|tags\nhello|\n", encoding="utf-8")

    identity_hash = "cafebabe" * 8
    all_ids = ["4000001", "4000002", "4000003"]
    hyp_texts = {arm: {sample_id: "hello" for sample_id in all_ids} for arm in ARM_NAMES}

    run_dirs = {}
    for arm in ARM_NAMES:
        ids_for_arm = all_ids if arm != "matched" else all_ids[:2]  # deliberately short one arm
        run_dirs[arm] = _write_arm_bundle(
            tmp_path, arm, identity_hash=identity_hash, split_ids=ids_for_arm, hyp_texts=hyp_texts[arm]
        )

    lock = load_lock(synthetic_world.lock_path)
    with pytest.raises(ComparisonError, match="split.ids differ"):
        build_report(run_dirs, lock, synthetic_world.data_root, repo_root=REPO_ROOT)
