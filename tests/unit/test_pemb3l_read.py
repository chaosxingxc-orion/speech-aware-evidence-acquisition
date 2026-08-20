"""``analysis.pemb3l_read``: the P-EMB-3L pinned offline read suite delta
(docs/readiness/2026-08-20-pemb3l-preregistration-REGISTERED.md). Model-free,
read-only -- every test drives hand-built synthetic manifests/fixtures; this
module is never pointed at a real embedding-vector manifest by the task that
wrote it.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.pemb3l_read import (
    LOCAL_EXHAUSTED_MAX_ACCURACY,
    LOCAL_SPACE_EXISTS_MIN_ACCURACY,
    AttractorStructure,
    Pemb3lReadError,
    build_arm_report,
    build_pemb3l_sweep_report,
    compute_attractor_structure,
    evaluate_pemb3l_verdict,
    render_sweep_report,
    sweep_report_to_json,
)
from speech_aware_evidence_acquisition.analysis.pemb_read import PembReadError
from speech_aware_evidence_acquisition.rails.probes.pemb3l_flight import (
    ARM_IDS,
    ARM_L1_ID,
    ARM_L2_ID,
    ARM_L3_ID,
    CITED_MEAN_BARE_ACCURACY,
    arm_run_id,
)
from speech_aware_evidence_acquisition.rails.probes.pemb_flight import LoadedEmbeddingManifest

# ---------------------------------------------------------------------------
# compute_attractor_structure.
# ---------------------------------------------------------------------------


def test_compute_attractor_structure_counts_shares_and_orders_desc():
    structure = compute_attractor_structure(["iot", "email", "email"], n_labels_available=2)
    assert isinstance(structure, AttractorStructure)
    assert structure.n_predictions == 3
    assert structure.n_labels_available == 2
    assert structure.n_labels_predicted == 2
    assert structure.shares[0].label == "email"
    assert structure.shares[0].count == 2
    assert structure.shares[0].share == pytest.approx(2 / 3)
    assert structure.shares[1].label == "iot"
    assert structure.top1_share == pytest.approx(2 / 3)
    assert structure.top2_share == pytest.approx(1.0)  # only two labels total


def test_compute_attractor_structure_refuses_empty_predictions():
    with pytest.raises(Pemb3lReadError, match="non-empty"):
        compute_attractor_structure([], n_labels_available=2)


def test_compute_attractor_structure_refuses_non_positive_labels_available():
    with pytest.raises(Pemb3lReadError, match="positive"):
        compute_attractor_structure(["a"], n_labels_available=0)


# ---------------------------------------------------------------------------
# evaluate_pemb3l_verdict -- all three branches, boundaries included.
# ---------------------------------------------------------------------------


def _accuracies(l1: float, l2: float, l3: float) -> dict[str, float]:
    return {ARM_L1_ID: l1, ARM_L2_ID: l2, ARM_L3_ID: l3}


def test_evaluate_pemb3l_verdict_local_space_exists_when_any_arm_meets_the_floor():
    verdict, detail = evaluate_pemb3l_verdict(_accuracies(0.05, 0.05, LOCAL_SPACE_EXISTS_MIN_ACCURACY))
    assert verdict == "LOCAL-SPACE-EXISTS"
    assert ARM_L3_ID in detail


def test_evaluate_pemb3l_verdict_local_space_exists_above_the_floor():
    verdict, _detail = evaluate_pemb3l_verdict(_accuracies(1.0, 0.0, 0.0))
    assert verdict == "LOCAL-SPACE-EXISTS"


def test_evaluate_pemb3l_verdict_local_exhausted_when_every_arm_at_or_below_ceiling():
    verdict, detail = evaluate_pemb3l_verdict(_accuracies(0.10, 0.15, 0.0))
    assert verdict == "LOCAL-EXHAUSTED"
    assert "0.1500" in detail or "margin" in detail


def test_evaluate_pemb3l_verdict_local_exhausted_at_zero():
    verdict, _detail = evaluate_pemb3l_verdict(_accuracies(0.0, 0.0, 0.0))
    assert verdict == "LOCAL-EXHAUSTED"


def test_evaluate_pemb3l_verdict_inconclusive_strictly_between():
    verdict, _detail = evaluate_pemb3l_verdict(_accuracies(0.20, 0.16, 0.29))
    assert verdict == "INCONCLUSIVE-EMB3L"


def test_evaluate_pemb3l_verdict_boundary_just_below_local_space_exists_is_inconclusive():
    just_under = LOCAL_SPACE_EXISTS_MIN_ACCURACY - 0.0001
    verdict, _detail = evaluate_pemb3l_verdict(_accuracies(just_under, 0.0, 0.0))
    assert verdict == "INCONCLUSIVE-EMB3L"


def test_evaluate_pemb3l_verdict_boundary_just_above_local_exhausted_is_inconclusive():
    just_over = LOCAL_EXHAUSTED_MAX_ACCURACY + 0.0001
    verdict, _detail = evaluate_pemb3l_verdict(_accuracies(just_over, 0.0, 0.0))
    assert verdict == "INCONCLUSIVE-EMB3L"


def test_evaluate_pemb3l_verdict_refuses_a_missing_arm():
    with pytest.raises(Pemb3lReadError, match="missing accuracy"):
        evaluate_pemb3l_verdict({ARM_L1_ID: 0.5, ARM_L2_ID: 0.5})


def test_evaluate_pemb3l_verdict_refuses_an_unknown_arm():
    with pytest.raises(Pemb3lReadError, match="unknown arm"):
        evaluate_pemb3l_verdict(_accuracies(0.1, 0.1, 0.1) | {"not-a-real-arm": 0.9})


# ---------------------------------------------------------------------------
# CITED mean-bare constant -- sourced from rails.probes.pemb3l_flight, never
# re-derived here.
# ---------------------------------------------------------------------------


def test_cited_mean_bare_accuracy_is_the_registered_0500():
    assert CITED_MEAN_BARE_ACCURACY == 0.0500
    assert CITED_MEAN_BARE_ACCURACY == pytest.approx(3 / 60)


# ---------------------------------------------------------------------------
# build_arm_report -- synthetic 2D-vector manifest, exact predictions.
# ---------------------------------------------------------------------------


def _manifest(arm_id: str) -> LoadedEmbeddingManifest:
    audio = {
        "s1": [0.9, 0.1],  # close to "iot"
        "s2": [0.1, 0.9],  # close to "email"
        "s3": [0.2, 0.8],  # close to "email" -- gold is "iot", a miss
    }
    text = {"iot": [1.0, 0.0], "email": [0.0, 1.0]}
    return LoadedEmbeddingManifest(run_id=arm_run_id(arm_id), audio=audio, text=text)


_GOLD = {"s1": "iot", "s2": "email", "s3": "iot"}
_LABELS = ("email", "iot")


def test_build_arm_report_computes_accuracy_confusion_and_attractor():
    manifest = _manifest(ARM_L1_ID)
    report = build_arm_report(ARM_L1_ID, manifest, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    assert report.arm_id == ARM_L1_ID
    assert report.n_samples == 3
    assert report.n_correct == 2
    assert report.accuracy == pytest.approx(2 / 3)
    by_id = {p.sample_id: p for p in report.predictions}
    assert by_id["s1"].predicted_scenario == "iot"
    assert by_id["s1"].top1_correct is True
    assert by_id["s3"].predicted_scenario == "email"
    assert by_id["s3"].top1_correct is False
    assert set((c.gold, c.predicted, c.count) for c in report.confusion) == {
        ("iot", "iot", 1),
        ("email", "email", 1),
        ("iot", "email", 1),
    }
    assert report.attractor.n_predictions == 3
    assert report.attractor.top1_share == pytest.approx(2 / 3)  # "email" predicted twice (s2, s3)


def test_build_arm_report_is_idempotent():
    manifest = _manifest(ARM_L2_ID)
    report1 = build_arm_report(ARM_L2_ID, manifest, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    report2 = build_arm_report(ARM_L2_ID, manifest, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    assert report1 == report2


def test_build_arm_report_rejects_unknown_arm_id():
    manifest = _manifest(ARM_L1_ID)
    with pytest.raises(Pemb3lReadError, match="unknown arm_id"):
        build_arm_report("not-a-real-arm", manifest, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)


def test_build_arm_report_rejects_a_manifest_from_a_different_arm():
    manifest = _manifest(ARM_L1_ID)  # run_id tagged for L1
    with pytest.raises(Pemb3lReadError, match="does not match arm"):
        build_arm_report(ARM_L3_ID, manifest, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)


def test_build_arm_report_rejects_audio_gold_id_mismatch():
    # _assert_key_sets_equal is analysis.pemb_read's own, reused verbatim
    # (module docstring) -- it raises PembReadError, never Pemb3lReadError.
    manifest = _manifest(ARM_L1_ID)
    bad_gold = dict(_GOLD)
    del bad_gold["s3"]
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_arm_report(ARM_L1_ID, manifest, bad_gold, _LABELS, expected_audio_n=3, expected_label_n=2)


def test_build_arm_report_rejects_label_set_mismatch():
    manifest = _manifest(ARM_L1_ID)
    with pytest.raises(PembReadError, match="id sets disagree"):
        build_arm_report(ARM_L1_ID, manifest, _GOLD, ("iot",), expected_audio_n=3, expected_label_n=2)


def test_build_arm_report_rejects_wrong_expected_counts():
    manifest = _manifest(ARM_L1_ID)
    with pytest.raises(Pemb3lReadError, match="audio vector"):
        build_arm_report(ARM_L1_ID, manifest, _GOLD, _LABELS, expected_audio_n=60, expected_label_n=2)


# ---------------------------------------------------------------------------
# build_pemb3l_sweep_report -- three arms combined + verdict + delta.
# ---------------------------------------------------------------------------


def _all_manifests() -> dict[str, LoadedEmbeddingManifest]:
    return {arm_id: _manifest(arm_id) for arm_id in ARM_IDS}


def test_build_pemb3l_sweep_report_combines_arms_and_computes_delta():
    report = build_pemb3l_sweep_report(_all_manifests(), _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    assert set(report.arm_reports.keys()) == set(ARM_IDS)
    for arm_id in ARM_IDS:
        assert report.arm_reports[arm_id].accuracy == pytest.approx(2 / 3)
    assert report.cited_mean_bare_accuracy == CITED_MEAN_BARE_ACCURACY
    assert report.l3_accuracy == pytest.approx(2 / 3)
    assert report.l3_vs_cited_mean_bare_delta == pytest.approx(2 / 3 - CITED_MEAN_BARE_ACCURACY)
    # 2/3 = 0.6667 >= 0.30 -- LOCAL-SPACE-EXISTS.
    assert report.verdict == "LOCAL-SPACE-EXISTS"


def test_build_pemb3l_sweep_report_is_idempotent():
    manifests = _all_manifests()
    report1 = build_pemb3l_sweep_report(manifests, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    report2 = build_pemb3l_sweep_report(manifests, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    assert report1 == report2


def test_build_pemb3l_sweep_report_rejects_a_missing_arm_manifest():
    manifests = _all_manifests()
    del manifests[ARM_L3_ID]
    with pytest.raises(Pemb3lReadError, match="missing manifest"):
        build_pemb3l_sweep_report(manifests, _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)


def test_sweep_report_to_json_and_render_round_trip():
    report = build_pemb3l_sweep_report(_all_manifests(), _GOLD, _LABELS, expected_audio_n=3, expected_label_n=2)
    document = sweep_report_to_json(report)
    text = json.dumps(document)
    parsed = json.loads(text)
    assert parsed["verdict"] == "LOCAL-SPACE-EXISTS"
    assert set(parsed["arms"].keys()) == set(ARM_IDS)
    assert parsed["cited_mean_bare_accuracy"] == pytest.approx(0.0500)
    rendered = render_sweep_report(report)
    assert "LOCAL-SPACE-EXISTS" in rendered
    assert ARM_L1_ID in rendered
    assert ARM_L2_ID in rendered
    assert ARM_L3_ID in rendered
