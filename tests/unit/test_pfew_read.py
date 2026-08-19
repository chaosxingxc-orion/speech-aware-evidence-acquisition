"""``analysis.pfew_read``: the P-FEW pinned offline read suite (closed-set
accuracy per arm vs gold, mapping-outcome distributions, the per-sample
3-arm table, the paired bootstrap on both registered contrasts, the
skew-label capture rate, the mandatory reachability statement, and the
CI-gated FS-HELPS/FS-INERT/BIAS-SENSITIVE/INCONCLUSIVE-FEW evaluator).

Engineering-only, zero live model contact -- every fixture here is either a
hand-authored synthetic attempt directory or a directly hand-built
dataclass/float fixture. This module is NEVER pointed at a real P-FEW
flight attempt (module docstring of ``analysis.pfew_read`` itself: a later,
separately-registered one-shot read session does that).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.bootstrap import BootstrapResult
from speech_aware_evidence_acquisition.analysis.pfew_read import (
    BIAS_SENSITIVE_MIN_CAPTURE,
    BIAS_SENSITIVE_MIN_DIFF,
    FS_HELPS_MIN_DIFF,
    FS_INERT_MAX_ABS,
    PFewReadError,
    PFewSampleRow,
    build_pfew_report,
    compute_reachability_statement,
    compute_skew_capture,
    evaluate_pfew_ci_gated,
    evaluate_point,
    main as pfew_read_main,
    report_to_json,
)
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pfew_flight import (
    FS_BAL_ARM,
    FS_NONE_ARM,
    FS_SKEW_ARM,
)
from speech_aware_evidence_acquisition.rails.probes.pslu_s2_flight import map_predicted_scenario_to_canonical

CANONICAL_LABELS = ("alarm", "calendar", "email", "iot", "music", "weather")


# ---------------------------------------------------------------------------
# Synthetic SLURP gold world -- 6 devel samples, one per canonical label,
# mirroring tests/unit/test_ptrap_read.py's own SlurpReadWorld pattern.
# ---------------------------------------------------------------------------


def _write_flac(path: Path, *, sample_rate_hz: int = 16000, seconds: float = 0.2) -> None:
    import numpy as np
    import soundfile as sf

    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate_hz * seconds)
    sf.write(str(path), np.zeros(frames, dtype="float32"), sample_rate_hz, format="FLAC")


def _tokens(*surfaces: str) -> list[dict]:
    return [{"surface": s, "id": i, "lemma": s, "pos": "NN"} for i, s in enumerate(surfaces)]


DEVEL_RECORDS = [
    {
        "slurp_id": 100 + index,
        "sentence": f"sample sentence for {label}",
        "sentence_annotation": f"sample sentence for {label}",
        "intent": f"{label}_query",
        "scenario": label,
        "action": "query",
        "tokens": _tokens("sample", "sentence", "for", label),
        "entities": [],
        "recordings": [{"file": f"audio-{100 + index}.flac", "wer": 0.0, "ent_wer": None, "status": "correct"}],
    }
    for index, label in enumerate(CANONICAL_LABELS)
]


class SlurpReadWorld:
    def __init__(self, tmp_path: Path) -> None:
        self.data_root = tmp_path / "data"
        self.lock_path = tmp_path / "lock.json"
        audio_root = self.data_root / "datasets" / "slurp"
        metadata_dir = audio_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        (metadata_dir / "devel.jsonl").write_text(
            "\n".join(json.dumps(r) for r in DEVEL_RECORDS) + "\n", encoding="utf-8"
        )
        real_dir = audio_root / "slurp_real"
        for record in DEVEL_RECORDS:
            for recording in record["recordings"]:
                _write_flac(real_dir / recording["file"])
        lock_doc = {
            "datasets": [
                {
                    "name": "slurp",
                    "kind": "dataset",
                    "local_subdir": "repos/slurp/scripts/audio",
                    "license": "mixed: textual part CC BY 4.0, audio part CC BY-NC 4.0",
                    "annotations": {"governed_copy": "datasets/slurp/metadata"},
                }
            ]
        }
        self.lock_path.write_text(json.dumps(lock_doc), encoding="utf-8")
        self.lock = load_lock(self.lock_path)
        self.adapter = SlurpAdapter(self.lock, self.data_root)
        samples = {s.sample_id: s for s in self.adapter.load_split("devel")}
        self.by_label = {record["scenario"]: self._find(samples, record["slurp_id"]) for record in DEVEL_RECORDS}

    @staticmethod
    def _find(samples: dict, slurp_id: int):
        needle = f":{slurp_id:06d}:"
        for sample_id, sample in samples.items():
            if needle in sample_id:
                return sample
        raise KeyError(slurp_id)


@pytest.fixture()
def read_world(tmp_path):
    return SlurpReadWorld(tmp_path)


def _roster_table_path(tmp_path: Path) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    roster_doc = {
        "probe": "P-SLU",
        "legality_tier": "legal",
        "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
        "arms": {
            "A1_scenario_roster": {"rosters": {label: [["dummy_type", "dummy_value"]] for label in CANONICAL_LABELS}},
            "A2_global_type_vocabulary": {"types": ["dummy_type"]},
            "A3_full_ontology_dose_capped": {"roster": [["dummy_type", "dummy_value"]]},
            "A4_deranged": {
                "mapping": {
                    label: CANONICAL_LABELS[(i + 1) % len(CANONICAL_LABELS)]
                    for i, label in enumerate(CANONICAL_LABELS)
                }
            },
        },
    }
    path = tmp_path / "rosters.json"
    path.write_text(json.dumps(roster_doc), encoding="utf-8")
    return path


def _manifest_path(world: SlurpReadWorld, tmp_path: Path, labels: list[str]) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    manifest_doc = {
        "probe": "P-SLU",
        "seed": 20260807,
        "split_identity_hash": "a" * 64,
        "items": [{"sample_id": world.by_label[label].sample_id} for label in labels],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest_doc), encoding="utf-8")
    return path


def _row(arm: str, sample, predicted_label: str | None, demos: tuple[dict, ...] = ()) -> dict:
    mapping = map_predicted_scenario_to_canonical(predicted_label, CANONICAL_LABELS)
    response_text = json.dumps({"scenario": predicted_label, "action": "query", "entities": []})
    return {
        "arm": arm,
        "sample_id": sample.sample_id,
        "messages": [],
        "response_text": response_text,
        "metrics": {},
        "consumption": {"records": []},
        "closed_set_mapping": mapping.as_json(),
        "demos": list(demos),
    }


def _write_attempt_dir(path: Path, rows: list[dict], *, status: str = "COMPLETED", error=None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    with (path / "outputs.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (path / "flight-receipt.json").write_text(json.dumps({"status": status, "error": error}), encoding="utf-8")
    return path


def _demo(label: str, index: int = 0) -> dict:
    return {"train_sample_id": f"slurp:train:{index:06d}", "utterance_text": f"u{index}", "scenario_label": label}


# ---------------------------------------------------------------------------
# 1. compute_reachability_statement -- pure arithmetic.
# ---------------------------------------------------------------------------


def test_compute_reachability_statement_high_accuracy_makes_fs_helps_unreachable():
    stmt = compute_reachability_statement(0.95)
    assert stmt.max_attainable_bal_none_diff == pytest.approx(0.05)
    assert stmt.fs_helps_reachable is False


def test_compute_reachability_statement_comparison_is_non_strict_ge_not_gt():
    """``>=``, not ``>``: reachability is derived from the SAME ``max_diff
    >= floor`` comparison the function's own docstring/detail text names --
    verified generically against the function's own arithmetic rather than
    a hardcoded float literal (``1.0 - 0.90`` does not equal ``0.10``
    bit-for-bit in IEEE754 binary64, which would make a hardcoded-boundary
    assertion a coin flip on float rounding)."""

    for fs_none_accuracy in (0.85, 0.90, 0.95, 0.5, 0.1):
        stmt = compute_reachability_statement(fs_none_accuracy)
        expected_bal_none = (1.0 - fs_none_accuracy) >= FS_HELPS_MIN_DIFF
        expected_none_skew = fs_none_accuracy >= BIAS_SENSITIVE_MIN_DIFF
        assert stmt.fs_helps_reachable == expected_bal_none
        assert stmt.bias_sensitive_reachable == expected_none_skew


def test_compute_reachability_statement_just_above_the_floor_is_reachable():
    stmt = compute_reachability_statement(0.85)  # max diff 0.15, comfortably above the 0.10 floor
    assert stmt.fs_helps_reachable is True


def test_compute_reachability_statement_low_accuracy_makes_bias_sensitive_unreachable():
    stmt = compute_reachability_statement(0.10)
    assert stmt.max_attainable_none_skew_diff == pytest.approx(0.10)
    assert stmt.bias_sensitive_reachable is False  # need >= 0.15 headroom


def test_compute_reachability_statement_mid_accuracy_both_reachable():
    stmt = compute_reachability_statement(0.50)
    assert stmt.fs_helps_reachable is True
    assert stmt.bias_sensitive_reachable is True


# ---------------------------------------------------------------------------
# 2. compute_skew_capture -- capture-denominator exclusion accounting.
# ---------------------------------------------------------------------------


def _sample_row(sample_id: str, gold: str, skew_label_answer: str | None) -> PFewSampleRow:
    return PFewSampleRow(
        sample_id=sample_id, gold_scenario=gold, fs_none_label=None, fs_bal_label=None,
        fs_skew_label=skew_label_answer, fs_none_correct=False, fs_bal_correct=False,
        fs_skew_correct=(skew_label_answer == gold),
    )


def test_compute_skew_capture_excludes_samples_where_gold_equals_skew_label():
    per_sample = [
        _sample_row("s1", gold="iot", skew_label_answer="iot"),  # gold == skew_label -> EXCLUDED
        _sample_row("s2", gold="email", skew_label_answer="iot"),  # wrong-for-this-sample, parroted -> captured
        _sample_row("s3", gold="weather", skew_label_answer="weather"),  # wrong-for-this-sample, NOT parroted
    ]
    stats = compute_skew_capture(per_sample, "iot")
    assert stats.n_samples == 3
    assert stats.n_excluded_gold_equals_skew == 1
    assert stats.n_denominator == 2
    assert stats.capture_count == 1
    assert stats.capture_rate == pytest.approx(0.5)


def test_compute_skew_capture_all_excluded_yields_zero_rate_not_a_crash():
    per_sample = [_sample_row("s1", gold="iot", skew_label_answer="iot")]
    stats = compute_skew_capture(per_sample, "iot")
    assert stats.n_denominator == 0
    assert stats.capture_rate == 0.0


def test_compute_skew_capture_full_capture_rate_one():
    per_sample = [_sample_row(f"s{i}", gold="email", skew_label_answer="iot") for i in range(4)]
    stats = compute_skew_capture(per_sample, "iot")
    assert stats.capture_count == 4
    assert stats.n_denominator == 4
    assert stats.capture_rate == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# 3. evaluate_point -- registered point thresholds.
# ---------------------------------------------------------------------------


def test_evaluate_point_fs_helps_met_at_the_boundary():
    verdict = evaluate_point(FS_HELPS_MIN_DIFF, 0.0, 0.0)
    assert verdict.fs_helps_point.verdict == "met"


def test_evaluate_point_fs_helps_not_met_just_under_the_boundary():
    verdict = evaluate_point(FS_HELPS_MIN_DIFF - 0.01, 0.0, 0.0)
    assert verdict.fs_helps_point.verdict == "not_met"


def test_evaluate_point_fs_inert_met_at_the_boundary_both_directions():
    assert evaluate_point(FS_INERT_MAX_ABS, 0.0, 0.0).fs_inert_point.verdict == "met"
    assert evaluate_point(-FS_INERT_MAX_ABS, 0.0, 0.0).fs_inert_point.verdict == "met"


def test_evaluate_point_between_inert_and_helps_is_not_met_for_either():
    mid = (FS_INERT_MAX_ABS + FS_HELPS_MIN_DIFF) / 2.0
    verdict = evaluate_point(mid, 0.0, 0.0)
    assert verdict.fs_helps_point.verdict == "not_met"
    assert verdict.fs_inert_point.verdict == "not_met"


def test_evaluate_point_bias_sensitive_requires_both_conditions():
    both = evaluate_point(0.0, BIAS_SENSITIVE_MIN_DIFF, BIAS_SENSITIVE_MIN_CAPTURE)
    assert both.bias_sensitive_point.verdict == "met"
    diff_only = evaluate_point(0.0, BIAS_SENSITIVE_MIN_DIFF, BIAS_SENSITIVE_MIN_CAPTURE - 0.01)
    assert diff_only.bias_sensitive_point.verdict == "not_met"
    capture_only = evaluate_point(0.0, BIAS_SENSITIVE_MIN_DIFF - 0.01, BIAS_SENSITIVE_MIN_CAPTURE)
    assert capture_only.bias_sensitive_point.verdict == "not_met"


# ---------------------------------------------------------------------------
# 4. evaluate_pfew_ci_gated -- all verdict branches, incl. CI-crossing.
# ---------------------------------------------------------------------------


def _boot(ci_low: float, ci_high: float) -> BootstrapResult:
    return BootstrapResult(
        point_estimate=(ci_low + ci_high) / 2.0, replicates=(ci_low, ci_high), sigma_hat=0.02,
        ci_low=ci_low, ci_high=ci_high, ci_level=0.90, n_replicates=100, seed=1,
    )


def test_evaluate_pfew_ci_gated_fs_helps_fires_when_point_and_ci_both_clear():
    point = evaluate_point(0.20, 0.0, 0.0)
    bal_none = _boot(0.10, 0.30)  # ci_low > 0
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_helps.verdict == "met"
    assert verdict.overall == "FS-HELPS"


def test_evaluate_pfew_ci_gated_fs_helps_not_met_when_ci_crosses_zero():
    point = evaluate_point(0.20, 0.0, 0.0)
    bal_none = _boot(-0.01, 0.41)  # ci_low <= 0 despite a strong point estimate
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_helps.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-FEW"


def test_evaluate_pfew_ci_gated_fs_inert_fires_when_point_and_ci_both_inside_band():
    point = evaluate_point(0.02, 0.0, 0.0)
    bal_none = _boot(-0.03, 0.05)  # entirely inside [-0.05, +0.05]
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.50)  # FS-HELPS reachable here
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_inert.verdict == "met"
    assert verdict.overall == "FS-INERT"


def test_evaluate_pfew_ci_gated_ci_crossing_the_band_is_inconclusive_not_fs_inert():
    """Point estimate satisfies |diff|<=0.05, but the CI is NOT entirely
    inside the band -- this is the registered "CI-crossing -> INCONCLUSIVE"
    case, never an affirmative FS-INERT."""

    point = evaluate_point(0.02, 0.0, 0.0)
    bal_none = _boot(-0.03, 0.09)  # point inside the band, CI crosses out to 0.09
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.point.fs_inert_point.verdict == "met"  # point alone WOULD qualify
    assert verdict.fs_inert.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-FEW"
    assert "CI" in verdict.fs_inert.detail


def test_evaluate_pfew_ci_gated_fs_inert_gated_to_inconclusive_when_fs_helps_unreachable():
    """The unreachable-branch gate (module docstring note 4, mirrors
    ptrap/pkey precedent): point+CI both qualify FS-INERT, but FS-NONE's own
    accuracy already puts FS-HELPS out of reach -- FS-INERT may not be
    reported as an affirmative "no help" finding here."""

    point = evaluate_point(0.01, 0.0, 0.0)
    bal_none = _boot(-0.02, 0.04)  # entirely inside the band
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.97)  # max attainable diff = 0.03 < 0.10
    assert reachability.fs_helps_reachable is False
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_inert.verdict == "not_met"
    assert verdict.overall == "INCONCLUSIVE-FEW"
    assert "unreachable" in verdict.fs_inert.detail.lower() or "UNREACHABLE" in verdict.fs_inert.detail


def test_evaluate_pfew_ci_gated_bias_sensitive_co_fires_as_an_overlay_with_fs_helps():
    point = evaluate_point(0.20, BIAS_SENSITIVE_MIN_DIFF, BIAS_SENSITIVE_MIN_CAPTURE)
    bal_none = _boot(0.05, 0.35)
    none_skew = _boot(0.05, 0.25)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_helps.verdict == "met"
    assert verdict.bias_sensitive.verdict == "met"
    assert verdict.overall == "FS-HELPS + BIAS-SENSITIVE"


def test_evaluate_pfew_ci_gated_bias_sensitive_co_fires_alongside_inconclusive():
    point = evaluate_point(0.20, BIAS_SENSITIVE_MIN_DIFF, BIAS_SENSITIVE_MIN_CAPTURE)
    bal_none = _boot(-0.01, 0.41)  # FS-HELPS point met but CI crosses zero -> not met
    none_skew = _boot(0.05, 0.25)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.fs_helps.verdict == "not_met"
    assert verdict.fs_inert.verdict == "not_met"  # point diff (0.20) is outside the inert band anyway
    assert verdict.bias_sensitive.verdict == "met"
    assert verdict.overall == "INCONCLUSIVE-FEW + BIAS-SENSITIVE"


def test_evaluate_pfew_ci_gated_neither_helps_nor_inert_nor_bias_is_inconclusive_few():
    mid = (FS_INERT_MAX_ABS + FS_HELPS_MIN_DIFF) / 2.0
    point = evaluate_point(mid, 0.0, 0.0)
    bal_none = _boot(mid - 0.02, mid + 0.02)
    none_skew = _boot(-0.02, 0.02)
    reachability = compute_reachability_statement(0.50)
    verdict = evaluate_pfew_ci_gated(point, bal_none, none_skew, reachability)
    assert verdict.overall == "INCONCLUSIVE-FEW"


# ---------------------------------------------------------------------------
# 5. Full read-suite integration (build_pfew_report / report_to_json / the
#    idempotence guard) over a hand-authored synthetic attempt dir.
# ---------------------------------------------------------------------------


def _build_report(world: SlurpReadWorld, tmp_path: Path):
    labels = list(CANONICAL_LABELS)  # 6 samples, one per canonical label
    samples = [world.by_label[label] for label in labels]
    bal_demos = tuple(_demo(label, i) for i, label in enumerate(["alarm", "calendar", "email", "iot"]))
    skew_demos = tuple(_demo("music", i) for i in range(4))

    rows: list[dict] = []
    for sample in samples:
        gold = sample.scenario
        rows.append(_row(FS_NONE_ARM, sample, gold))  # FS-NONE always gets it right
        rows.append(_row(FS_BAL_ARM, sample, gold, bal_demos))  # FS-BAL also always right
        # FS-SKEW parrots "music" -- correct only for the sample whose own gold is "music".
        rows.append(_row(FS_SKEW_ARM, sample, "music", skew_demos))

    attempt_dir = _write_attempt_dir(tmp_path / "pfew-attempt", rows)
    manifest_path = _manifest_path(world, tmp_path, labels)
    roster_table_path = _roster_table_path(tmp_path)
    report = build_pfew_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
    )
    return report, attempt_dir


def test_build_pfew_report_wiring_and_capture_accounting(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    assert report.flight_status == "COMPLETED"
    assert not report.harness_defect_reasons
    assert len(report.per_sample) == 6
    assert report.fs_none_accuracy == pytest.approx(1.0)
    assert report.fs_bal_accuracy == pytest.approx(1.0)
    assert report.fs_skew_accuracy == pytest.approx(1 / 6)  # only the "music" sample is right by chance
    assert report.skew_label == "music"
    # capture: excluded is the "music" sample (gold == skew_label); every
    # OTHER sample's FS-SKEW answer equals "music" -- full capture.
    assert report.capture_stats.n_excluded_gold_equals_skew == 1
    assert report.capture_stats.n_denominator == 5
    assert report.capture_stats.capture_count == 5
    assert report.capture_stats.capture_rate == pytest.approx(1.0)


def test_build_pfew_report_json_round_trips(read_world, tmp_path):
    report, _ = _build_report(read_world, tmp_path)
    document = report_to_json(report)
    assert document["schema"] == "saea-pfew-read-v1"
    assert document["skew_label"] == "music"
    assert len(document["per_sample"]) == 6
    assert document["capture"]["capture_rate"] == pytest.approx(1.0)
    assert "overall" in document["verdict"]


def test_build_pfew_report_flags_a_mismatched_embedded_mapping_as_a_harness_defect(read_world, tmp_path):
    """Read-side re-derivation (module docstring note 1, defense in depth):
    a row whose embedded closed_set_mapping disagrees with what its OWN
    response_text re-derives to is flagged, never silently trusted."""

    world = read_world
    labels = list(CANONICAL_LABELS)
    samples = [world.by_label[label] for label in labels]
    bal_demos = tuple(_demo(label, i) for i, label in enumerate(["alarm", "calendar", "email", "iot"]))
    skew_demos = tuple(_demo("music", i) for i in range(4))

    rows = []
    for sample in samples:
        gold = sample.scenario
        rows.append(_row(FS_NONE_ARM, sample, gold))
        rows.append(_row(FS_BAL_ARM, sample, gold, bal_demos))
        rows.append(_row(FS_SKEW_ARM, sample, "music", skew_demos))

    # Tamper with one row's own embedded mapping AFTER construction.
    tampered = dict(rows[0])
    tampered["closed_set_mapping"] = {
        "predicted_raw": "not-what-the-response-says",
        "canonical_label": "weather",
        "outcome": "exact",
        "fallback": False,
    }
    rows[0] = tampered

    attempt_dir = _write_attempt_dir(tmp_path / "pfew-attempt", rows)
    manifest_path = _manifest_path(world, tmp_path, labels)
    roster_table_path = _roster_table_path(tmp_path)
    report = build_pfew_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
    )
    assert any("disagrees with a re-derivation" in reason for reason in report.harness_defect_reasons)


def test_build_pfew_report_flags_missing_arm_rows_as_a_harness_defect(read_world, tmp_path):
    world = read_world
    labels = list(CANONICAL_LABELS)
    samples = [world.by_label[label] for label in labels]
    bal_demos = tuple(_demo(label, i) for i, label in enumerate(["alarm", "calendar", "email", "iot"]))

    rows = []
    for sample in samples:
        gold = sample.scenario
        rows.append(_row(FS_NONE_ARM, sample, gold))
        rows.append(_row(FS_BAL_ARM, sample, gold, bal_demos))
        # FS-SKEW rows entirely omitted.

    attempt_dir = _write_attempt_dir(tmp_path / "pfew-attempt", rows)
    manifest_path = _manifest_path(world, tmp_path, labels)
    roster_table_path = _roster_table_path(tmp_path)
    report = build_pfew_report(
        attempt_dir, world.lock, world.data_root,
        sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
    )
    assert any("FS-SKEW: missing" in reason for reason in report.harness_defect_reasons)


def test_build_pfew_report_refuses_a_missing_attempt_dir(read_world, tmp_path):
    world = read_world
    manifest_path = _manifest_path(world, tmp_path, list(CANONICAL_LABELS))
    roster_table_path = _roster_table_path(tmp_path)
    with pytest.raises(PFewReadError, match="no outputs.jsonl"):
        build_pfew_report(
            tmp_path / "does-not-exist", world.lock, world.data_root,
            sample_manifest_path=manifest_path, roster_table_path=roster_table_path,
        )


# ---------------------------------------------------------------------------
# 6. Idempotence guard (the CLI's own one-shot read discipline).
# ---------------------------------------------------------------------------


def _cli_repo_layout(tmp_path: Path, world: SlurpReadWorld) -> Path:
    """Mirrors tests/unit/test_ptrap_read.py's own ``_cli_repo_layout``: a
    minimal umbrella/study directory shape so ``main()``'s own
    ``umbrella_lock_path(repo_root)`` resolves to a real (copied) lock
    file, without needing the REAL umbrella checkout."""

    repo_root = tmp_path / "umbrella" / "studies" / "study"
    repo_root.mkdir(parents=True)
    lock_dest = tmp_path / "umbrella" / "docs" / "datasets.lock.json"
    lock_dest.parent.mkdir(parents=True, exist_ok=True)
    lock_dest.write_text(world.lock_path.read_text(encoding="utf-8"), encoding="utf-8")
    return repo_root


def test_main_refuses_to_run_twice_against_the_same_output_dir(read_world, tmp_path, monkeypatch, capsys):
    world = read_world
    _, attempt_dir = _build_report(world, tmp_path)
    manifest_path = _manifest_path(world, tmp_path / "cfg", list(CANONICAL_LABELS))
    roster_table_path = _roster_table_path(tmp_path / "cfg")

    repo_root = _cli_repo_layout(tmp_path, world)
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(world.data_root))
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    argv = [
        str(attempt_dir),
        "--output-dir", str(output_dir),
        "--repo-root", str(repo_root),
        "--sample-manifest", str(manifest_path),
        "--roster-table", str(roster_table_path),
    ]

    first_exit = pfew_read_main(argv)
    assert first_exit == 0
    verdict_path = output_dir / "verdict.json"
    assert verdict_path.is_file()
    first_bytes = verdict_path.read_bytes()

    second_exit = pfew_read_main(argv)
    assert second_exit == 1
    captured = capsys.readouterr()
    assert "REFUSED" in captured.err
    assert verdict_path.read_bytes() == first_bytes  # untouched by the refused second attempt
