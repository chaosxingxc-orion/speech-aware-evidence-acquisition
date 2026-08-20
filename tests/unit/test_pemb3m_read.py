"""``analysis.pemb3m_read``: the P-EMB-3M pinned offline read suite delta
(docs/readiness/2026-08-20-pemb3m-preregistration-REGISTERED.md section 4).
Model-free, read-only -- every test drives hand-built synthetic manifests.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.analysis.pemb3m_read import (
    CASCADE_ROUTES_MIN_ACCURACY,
    CASCADE_WEAK_MAX_ACCURACY,
    CONTROL_ANOMALY_MIN_ACCURACY,
    EMB_ROUTES_MIN_ACCURACY,
    EMB_WEAK_MAX_ACCURACY,
    JITTER_COSINE_TOLERANCE,
    CosineSignProfile,
    Pemb3mReadError,
    build_arm_report,
    build_pemb3m_sweep_report,
    compute_cosine_sign_profile,
    compute_cross_arm_agreement,
    evaluate_control_anomaly,
    evaluate_m1_verdict,
    evaluate_m4_jitter_tolerance,
    evaluate_m4_verdict,
    evaluate_pemb3m_verdict,
    render_sweep_report,
    sweep_report_to_json,
)
from speech_aware_evidence_acquisition.rails.probes.pemb3m_flight import (
    ARM_IDS,
    ARM_M1_ID,
    ARM_M2_ID,
    ARM_M3_ID,
    ARM_M4_ID,
    LoadedPemb3mManifest,
    arm_run_id,
)


# ---------------------------------------------------------------------------
# compute_cosine_sign_profile.
# ---------------------------------------------------------------------------


def test_compute_cosine_sign_profile_counts_signs():
    profile = compute_cosine_sign_profile([0.5, -0.3, 0.0, 0.2, -0.1])
    assert isinstance(profile, CosineSignProfile)
    assert profile.n == 5
    assert profile.n_positive == 2
    assert profile.n_negative == 2
    assert profile.n_zero == 1
    assert profile.positive_share == pytest.approx(2 / 5)
    assert profile.max_cosine == 0.5
    assert profile.min_cosine == -0.3


def test_compute_cosine_sign_profile_refuses_empty():
    with pytest.raises(Pemb3mReadError, match="non-empty"):
        compute_cosine_sign_profile([])


# ---------------------------------------------------------------------------
# compute_cross_arm_agreement.
# ---------------------------------------------------------------------------


def test_compute_cross_arm_agreement_two_arms_full_agreement():
    predictions = {
        "a": {"s1": "iot", "s2": "email"},
        "b": {"s1": "iot", "s2": "email"},
    }
    result = compute_cross_arm_agreement(predictions)
    assert len(result) == 1
    pair = result[0]
    assert pair.arm_a == "a"
    assert pair.arm_b == "b"
    assert pair.n_common_samples == 2
    assert pair.n_agree == 2
    assert pair.agreement_rate == pytest.approx(1.0)


def test_compute_cross_arm_agreement_partial_agreement():
    predictions = {
        "a": {"s1": "iot", "s2": "email"},
        "b": {"s1": "iot", "s2": "calendar"},
    }
    result = compute_cross_arm_agreement(predictions)[0]
    assert result.n_agree == 1
    assert result.agreement_rate == pytest.approx(0.5)


def test_compute_cross_arm_agreement_disjoint_sample_sets():
    predictions = {"a": {"s1": "iot"}, "b": {"s2": "iot"}}
    result = compute_cross_arm_agreement(predictions)[0]
    assert result.n_common_samples == 0
    assert result.agreement_rate == 0.0


def test_compute_cross_arm_agreement_four_arms_produces_six_pairs():
    predictions = {arm_id: {"s1": "iot"} for arm_id in ("a", "b", "c", "d")}
    result = compute_cross_arm_agreement(predictions)
    assert len(result) == 6  # C(4,2)


def test_compute_cross_arm_agreement_single_arm_produces_no_pairs():
    assert compute_cross_arm_agreement({"a": {"s1": "iot"}}) == ()


# ---------------------------------------------------------------------------
# evaluate_m4_jitter_tolerance.
# ---------------------------------------------------------------------------


def test_jitter_tolerance_identical_vectors_pass():
    labels = {"iot": (1.0, 0.0), "email": (0.0, 1.0)}
    result = evaluate_m4_jitter_tolerance((1.0, 0.0), (1.0, 0.0), labels)
    assert result.cosine == pytest.approx(1.0)
    assert result.within_tolerance is True
    assert result.argmax_stable is True
    assert result.argmax_a == "iot"


def test_jitter_tolerance_below_declared_tolerance():
    labels = {"iot": (1.0, 0.0), "email": (0.0, 1.0)}
    # cos(45deg) ~= 0.707, well under 0.9999
    result = evaluate_m4_jitter_tolerance((1.0, 0.0), (1.0, 1.0), labels, tolerance=JITTER_COSINE_TOLERANCE)
    assert result.within_tolerance is False


def test_jitter_tolerance_argmax_unstable_when_labels_flip():
    labels = {"iot": (1.0, 0.0), "email": (0.0, 1.0)}
    result = evaluate_m4_jitter_tolerance((1.0, 0.0), (0.0, 1.0), labels)
    assert result.argmax_stable is False
    assert result.argmax_a == "iot"
    assert result.argmax_b == "email"


# ---------------------------------------------------------------------------
# evaluate_m1_verdict.
# ---------------------------------------------------------------------------


def test_m1_verdict_routes_above_floor():
    label, detail = evaluate_m1_verdict(EMB_ROUTES_MIN_ACCURACY, pooling_override_present=False)
    assert label == "EMB-ROUTES"
    assert "0.65" in detail or str(EMB_ROUTES_MIN_ACCURACY) in detail


def test_m1_verdict_weak_below_ceiling_clean_gate():
    label, _detail = evaluate_m1_verdict(EMB_WEAK_MAX_ACCURACY, pooling_override_present=False)
    assert label == "EMB-WEAK"


def test_m1_verdict_weak_scoped_when_pooling_override_present():
    label, detail = evaluate_m1_verdict(0.05, pooling_override_present=True)
    assert label == "EMB-WEAK-SCOPED"
    assert "SCOPED" in detail


def test_m1_verdict_inconclusive_strictly_between():
    label, _detail = evaluate_m1_verdict(0.5, pooling_override_present=False)
    assert label == "INCONCLUSIVE-3M-M1"


def test_m1_verdict_none_accuracy_is_inconclusive():
    label, _detail = evaluate_m1_verdict(None, pooling_override_present=False)
    assert label == "INCONCLUSIVE-3M-M1"


def test_m1_verdict_boundaries():
    just_under_routes = EMB_ROUTES_MIN_ACCURACY - 0.0001
    label, _ = evaluate_m1_verdict(just_under_routes, pooling_override_present=False)
    assert label == "INCONCLUSIVE-3M-M1"
    just_over_weak = EMB_WEAK_MAX_ACCURACY + 0.0001
    label, _ = evaluate_m1_verdict(just_over_weak, pooling_override_present=False)
    assert label == "INCONCLUSIVE-3M-M1"


# ---------------------------------------------------------------------------
# evaluate_m4_verdict.
# ---------------------------------------------------------------------------


def test_m4_verdict_cascade_routes():
    label, _detail = evaluate_m4_verdict(CASCADE_ROUTES_MIN_ACCURACY)
    assert label == "CASCADE-ROUTES"


def test_m4_verdict_cascade_weak():
    label, _detail = evaluate_m4_verdict(CASCADE_WEAK_MAX_ACCURACY)
    assert label == "CASCADE-WEAK"


def test_m4_verdict_inconclusive():
    label, _detail = evaluate_m4_verdict(0.5)
    assert label == "INCONCLUSIVE-3M-M4"


def test_m4_verdict_none_is_inconclusive():
    label, _detail = evaluate_m4_verdict(None)
    assert label == "INCONCLUSIVE-3M-M4"


# ---------------------------------------------------------------------------
# evaluate_control_anomaly.
# ---------------------------------------------------------------------------


def test_control_anomaly_fires_when_control_beats_both_primaries_above_floor():
    fired, detail = evaluate_control_anomaly(
        m1_accuracy=0.10, m2_accuracy=CONTROL_ANOMALY_MIN_ACCURACY, m3_accuracy=0.05, m4_accuracy=0.10
    )
    assert fired is True
    assert "FIRED" in detail


def test_control_anomaly_does_not_fire_below_floor():
    fired, _detail = evaluate_control_anomaly(m1_accuracy=0.05, m2_accuracy=0.20, m3_accuracy=0.10, m4_accuracy=0.05)
    assert fired is False


def test_control_anomaly_does_not_fire_when_primary_beats_control():
    fired, _detail = evaluate_control_anomaly(m1_accuracy=0.80, m2_accuracy=0.35, m3_accuracy=0.30, m4_accuracy=0.10)
    assert fired is False


def test_control_anomaly_excludes_a_dropped_control_never_treats_it_as_zero():
    # M3 dropped (None); M2 alone at 0.30 vs primaries both 0.0 -- fires.
    fired, detail = evaluate_control_anomaly(m1_accuracy=0.0, m2_accuracy=0.30, m3_accuracy=None, m4_accuracy=0.0)
    assert fired is True
    assert "0.3000" in detail


def test_control_anomaly_both_controls_dropped_cannot_fire():
    fired, detail = evaluate_control_anomaly(m1_accuracy=0.80, m2_accuracy=None, m3_accuracy=None, m4_accuracy=0.10)
    assert fired is False
    assert "cannot be evaluated" in detail


def test_control_anomaly_both_primaries_missing_uses_zero_floor():
    fired, _detail = evaluate_control_anomaly(m1_accuracy=None, m2_accuracy=0.35, m3_accuracy=None, m4_accuracy=None)
    assert fired is True


# ---------------------------------------------------------------------------
# evaluate_pemb3m_verdict -- combined.
# ---------------------------------------------------------------------------


def test_overall_verdict_all_inconclusive_and_no_anomaly():
    verdict = evaluate_pemb3m_verdict(
        m1_accuracy=0.5, m2_accuracy=0.05, m3_accuracy=0.05, m4_accuracy=0.5, pooling_override_present=False
    )
    assert verdict.m1_label == "INCONCLUSIVE-3M-M1"
    assert verdict.m4_label == "INCONCLUSIVE-3M-M4"
    assert verdict.control_anomaly is False
    assert verdict.overall == "INCONCLUSIVE-3M"


def test_overall_verdict_m1_routes_and_m4_weak():
    verdict = evaluate_pemb3m_verdict(
        m1_accuracy=0.80, m2_accuracy=0.05, m3_accuracy=0.05, m4_accuracy=0.10, pooling_override_present=False
    )
    assert verdict.m1_label == "EMB-ROUTES"
    assert verdict.m4_label == "CASCADE-WEAK"
    assert verdict.overall == "EMB-ROUTES + CASCADE-WEAK"


def test_overall_verdict_can_combine_a_routes_label_with_control_anomaly():
    # M1 routes AND a control matches it -- both fire simultaneously
    # ("named finding, any verdict", the registration's own parenthetical).
    verdict = evaluate_pemb3m_verdict(
        m1_accuracy=0.80, m2_accuracy=0.80, m3_accuracy=0.05, m4_accuracy=0.05, pooling_override_present=False
    )
    assert verdict.m1_label == "EMB-ROUTES"
    assert verdict.control_anomaly is True
    assert verdict.overall == "EMB-ROUTES + CASCADE-WEAK + CONTROL-ANOMALY"


def test_overall_verdict_weak_scoped_propagates_from_pooling_override():
    verdict = evaluate_pemb3m_verdict(
        m1_accuracy=0.05, m2_accuracy=0.05, m3_accuracy=0.05, m4_accuracy=0.05, pooling_override_present=True
    )
    assert verdict.m1_label == "EMB-WEAK-SCOPED"


# ---------------------------------------------------------------------------
# build_arm_report.
# ---------------------------------------------------------------------------


def _manifest(arm_id: str, *, correct_query_id: str = "s1", n=3) -> LoadedPemb3mManifest:
    # Two labels, "iot"/"email"; query "s1" is closest to "iot" (correct if
    # gold["s1"] == "iot"), others closer to "email".
    query = {}
    for i in range(n):
        sample_id = f"s{i + 1}"
        query[sample_id] = (1.0, 0.0) if sample_id == correct_query_id else (0.0, 1.0)
    label = {"iot": (1.0, 0.0), "email": (0.0, 1.0)}
    return LoadedPemb3mManifest(
        run_id=arm_run_id(arm_id), arm_id=arm_id, dims=2, query=MappingProxyType(query), label=MappingProxyType(label)
        , jitter=MappingProxyType({})
    )


def test_build_arm_report_scores_correctly():
    manifest = _manifest(ARM_M1_ID, correct_query_id="s1", n=3)
    gold = {"s1": "iot", "s2": "iot", "s3": "email"}
    report = build_arm_report(ARM_M1_ID, manifest, gold, ["iot", "email"], expected_query_n=3, expected_label_n=2)
    assert report.dropped is False
    assert report.n_samples == 3
    assert report.n_correct == 2  # s1 (iot/iot correct) + s3 (email/email correct); s2 wrong (predicted email)
    assert report.accuracy == pytest.approx(2 / 3)
    assert report.attractor is not None
    assert report.cosine_sign_profile is not None


def test_build_arm_report_none_manifest_is_dropped():
    report = build_arm_report(ARM_M2_ID, None, {}, ["iot", "email"])
    assert report.dropped is True
    assert report.accuracy is None
    assert report.predictions == ()
    assert report.attractor is None


def test_build_arm_report_refuses_unknown_arm_id():
    with pytest.raises(Pemb3mReadError, match="unknown arm_id"):
        build_arm_report("not-a-real-arm", None, {}, [])


def test_build_arm_report_refuses_run_id_mismatch():
    manifest = _manifest(ARM_M1_ID, n=1)
    wrong_manifest = LoadedPemb3mManifest(
        run_id="wrong-run-id", arm_id=ARM_M1_ID, dims=2, query=manifest.query, label=manifest.label, jitter=manifest.jitter
    )
    with pytest.raises(Pemb3mReadError, match="run_id"):
        build_arm_report(ARM_M1_ID, wrong_manifest, {"s1": "iot"}, ["iot", "email"], expected_query_n=1, expected_label_n=2)


# ---------------------------------------------------------------------------
# build_pemb3m_sweep_report.
# ---------------------------------------------------------------------------


def test_build_pemb3m_sweep_report_end_to_end_with_one_dropped_control():
    gold = {"s1": "iot", "s2": "email", "s3": "iot"}
    labels = ["iot", "email"]
    manifests = {
        ARM_M1_ID: _manifest(ARM_M1_ID, correct_query_id="s1", n=3),
        ARM_M2_ID: None,  # DROPPED-DEPS
        ARM_M3_ID: _manifest(ARM_M3_ID, correct_query_id="s2", n=3),
        ARM_M4_ID: _manifest(ARM_M4_ID, correct_query_id="s1", n=3),
    }
    report = build_pemb3m_sweep_report(
        manifests,
        gold,
        labels,
        pooling_override_present=False,
        control_import_status={ARM_M2_ID: "DROPPED-DEPS", ARM_M3_ID: "OK"},
        cascade_source_status="COMPLETE",
        expected_query_n=3,
        expected_label_n=2,
    )
    assert set(report.arm_reports) == set(ARM_IDS)
    assert report.arm_reports[ARM_M2_ID].dropped is True
    # cross-arm agreement excludes the dropped M2: 3 non-dropped arms -> 3 pairs.
    assert len(report.cross_arm_agreement) == 3
    assert report.verdict.overall  # non-empty string either way
    document = sweep_report_to_json(report)
    assert document["schema"] == "saea-pemb3m-read-v1"
    rendered = render_sweep_report(report)
    assert "DROPPED-DEPS" in rendered
    assert "[OVERALL]" in rendered


def test_build_pemb3m_sweep_report_with_jitter_vectors():
    gold = {"s1": "iot"}
    labels = ["iot", "email"]
    manifests = {
        ARM_M1_ID: _manifest(ARM_M1_ID, correct_query_id="s1", n=1),
        ARM_M2_ID: _manifest(ARM_M2_ID, correct_query_id="s1", n=1),
        ARM_M3_ID: _manifest(ARM_M3_ID, correct_query_id="s1", n=1),
        ARM_M4_ID: _manifest(ARM_M4_ID, correct_query_id="s1", n=1),
    }
    report = build_pemb3m_sweep_report(
        manifests,
        gold,
        labels,
        pooling_override_present=False,
        control_import_status={ARM_M2_ID: "OK", ARM_M3_ID: "OK"},
        cascade_source_status="COMPLETE",
        jitter_vectors=((1.0, 0.0), (1.0, 0.0)),
        expected_query_n=1,
        expected_label_n=2,
    )
    assert report.jitter is not None
    assert report.jitter.within_tolerance is True
    document = sweep_report_to_json(report)
    assert document["jitter"]["within_tolerance"] is True


def test_build_pemb3m_sweep_report_missing_arm_key_treated_as_dropped():
    gold = {"s1": "iot"}
    labels = ["iot", "email"]
    manifests = {ARM_M1_ID: _manifest(ARM_M1_ID, correct_query_id="s1", n=1)}  # M2/M3/M4 absent entirely
    report = build_pemb3m_sweep_report(
        manifests,
        gold,
        labels,
        pooling_override_present=False,
        control_import_status={},
        cascade_source_status="ABSENT",
        expected_query_n=1,
        expected_label_n=2,
    )
    assert report.arm_reports[ARM_M4_ID].dropped is True
