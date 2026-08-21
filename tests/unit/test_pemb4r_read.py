"""``analysis.pemb4r_read``: the P-EMB-4R pinned offline read suite
(docs/readiness/2026-08-20-pemb4r-preregistration-REGISTERED.md section 4).
Model-free, read-only -- every test drives synthetic retrieval-plan
documents and flight facts, never a real model/server contact.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis import pemb4r_read as r
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as flight


def _retrieval_row(labels: list[str], cosines: list[float]) -> dict:
    return {
        "top_k_bank_ids": [f"b{i}" for i in range(len(labels))],
        "top_k_cosines": cosines,
        "top_k_labels": labels,
        "dedup_labels_k1": labels[:1],
        "dedup_labels_k3": sorted(set(labels[:3]), key=labels[:3].index),
        "dedup_labels_k5": sorted(set(labels[:5]), key=labels[:5].index),
    }


def _plan_for_arm(arm_id: str, per_sample_labels: dict[str, list[str]], per_sample_cosines: dict[str, list[float]]) -> dict:
    per_sample = {
        sid: _retrieval_row(labels, per_sample_cosines[sid]) for sid, labels in per_sample_labels.items()
    }
    return {
        "schema": flight.RETRIEVAL_PLAN_SCHEMA,
        "k_primary": 5,
        "winner_arm_id": arm_id,
        "winner_selection_rule": flight.WINNER_SELECTION_RULE,
        "arms": {arm_id: {"mean_top1_cosine": 0.9, "per_sample": per_sample}},
    }


# ---------------------------------------------------------------------------
# majority_vote_label.
# ---------------------------------------------------------------------------


def test_majority_vote_label_plain_majority():
    assert r.majority_vote_label(["a", "a", "b"], [0.9, 0.8, 0.7]) == "a"


def test_majority_vote_label_tie_breaks_by_highest_mean_cosine():
    # "a" appears once at 0.9; "b" appears once at 0.5 -- tie on COUNT (1
    # each), "a" wins on mean cosine.
    assert r.majority_vote_label(["a", "b"], [0.9, 0.5]) == "a"


def test_majority_vote_label_tie_on_count_and_cosine_breaks_by_sorted_label():
    assert r.majority_vote_label(["z", "a"], [0.5, 0.5]) == "a"


def test_majority_vote_label_refuses_empty():
    with pytest.raises(r.Pemb4rReadError, match="non-empty"):
        r.majority_vote_label([], [])


# ---------------------------------------------------------------------------
# compute_recall_at_k / compute_top1_margin / evaluate_argmax_stability.
# ---------------------------------------------------------------------------


def test_compute_recall_at_k_hit_and_miss():
    assert r.compute_recall_at_k(["iot", "weather", "play"], "weather", 3) is True
    assert r.compute_recall_at_k(["iot", "weather", "play"], "weather", 1) is False


def test_compute_top1_margin_two_or_more():
    assert r.compute_top1_margin([0.9, 0.6, 0.5]) == pytest.approx(0.3)


def test_compute_top1_margin_single_value():
    assert r.compute_top1_margin([0.9]) == pytest.approx(0.9)


def test_compute_top1_margin_refuses_empty():
    with pytest.raises(r.Pemb4rReadError, match="non-empty"):
        r.compute_top1_margin([])


def test_evaluate_argmax_stability_none_without_a_measured_delta():
    assert r.evaluate_argmax_stability(0.05, None) is None


def test_evaluate_argmax_stability_stable_when_margin_clears_delta():
    assert r.evaluate_argmax_stability(0.10, 0.02) == r.ARGMAX_STABLE


def test_evaluate_argmax_stability_within_jitter_noise_when_margin_does_not_clear():
    assert r.evaluate_argmax_stability(0.01, 0.02) == r.ARGMAX_WITHIN_JITTER_NOISE


# ---------------------------------------------------------------------------
# build_arm_report.
# ---------------------------------------------------------------------------


def test_build_arm_report_dropped_arm_carries_no_accuracy():
    report = r.build_arm_report(flight.ARM_A_LCO7, None, {}, dropped_reason="DROPPED-LCO7: server sanity failed")
    assert report.dropped is True
    assert report.vote_accuracy_k5 is None
    assert report.recall_at_5 is None
    assert report.predictions == ()


def test_build_arm_report_happy_path_computes_vote_accuracy_and_recall():
    labels = {"s1": ["iot", "iot", "weather"], "s2": ["weather", "weather", "iot"]}
    cosines = {"s1": [0.9, 0.8, 0.3], "s2": [0.9, 0.8, 0.3]}
    document = _plan_for_arm(flight.ARM_A_GLAP, labels, cosines)
    gold = {"s1": "iot", "s2": "weather"}
    report = r.build_arm_report(flight.ARM_A_GLAP, document, gold)
    assert report.dropped is False
    assert report.n_samples == 2
    assert report.vote_accuracy_k5 == pytest.approx(1.0)
    assert report.recall_at_1 == pytest.approx(1.0)


def test_build_arm_report_records_argmax_stability_when_repeat_delta_given():
    labels = {"s1": ["iot", "weather", "play"]}
    cosines = {"s1": [0.50, 0.49, 0.10]}  # tiny top1-top2 margin
    document = _plan_for_arm(flight.ARM_T_QW, labels, cosines)
    report = r.build_arm_report(flight.ARM_T_QW, document, {"s1": "iot"}, repeat_delta=0.05)
    assert report.predictions[0].argmax_stability == r.ARGMAX_WITHIN_JITTER_NOISE
    assert report.n_within_jitter_noise == 1


def test_build_arm_report_refuses_unknown_arm_id():
    with pytest.raises(r.Pemb4rReadError, match="unknown arm_id"):
        r.build_arm_report("not-a-real-arm", None, {}, dropped_reason="x")


def test_build_arm_report_refuses_missing_gold():
    labels = {"s1": ["iot"]}
    cosines = {"s1": [0.9]}
    document = _plan_for_arm(flight.ARM_A_GLAP, labels, cosines)
    with pytest.raises(r.Pemb4rReadError, match="no gold scenario"):
        r.build_arm_report(flight.ARM_A_GLAP, document, {})


# ---------------------------------------------------------------------------
# Per-arm and sweep-level verdict findings.
# ---------------------------------------------------------------------------


def test_evaluate_audio_arm_findings_register_rescue_only():
    findings, detail = r.evaluate_audio_arm_findings(flight.ARM_A_GLAP, 0.35, pooling_override_present=None)
    assert findings == ("REGISTER-RESCUE",)
    assert "0.3500" in detail


def test_evaluate_audio_arm_findings_both_register_rescue_and_audio_routes():
    findings, _detail = r.evaluate_audio_arm_findings(flight.ARM_A_GLAP, 0.70, pooling_override_present=None)
    assert findings == ("REGISTER-RESCUE", "AUDIO-ROUTES")


def test_evaluate_audio_arm_findings_none_below_floor():
    findings, _detail = r.evaluate_audio_arm_findings(flight.ARM_A_GLAP, 0.10, pooling_override_present=None)
    assert findings == ()


def test_evaluate_audio_arm_findings_lco_scoped_when_pooling_override_present():
    findings, detail = r.evaluate_audio_arm_findings(flight.ARM_A_LCO3, 0.50, pooling_override_present=True)
    assert findings == ("REGISTER-RESCUE",)
    assert "SCOPED" in detail


def test_evaluate_audio_arm_findings_dropped_arm():
    findings, detail = r.evaluate_audio_arm_findings(flight.ARM_A_LCO7, None, pooling_override_present=None)
    assert findings == ()
    assert "dropped" in detail


def test_evaluate_audio_content_absent_fires():
    audio = {flight.ARM_A_LCO3: 0.05, flight.ARM_A_LCO7: 0.10, flight.ARM_A_GLAP: 0.02}
    text = {flight.ARM_T_QW: 0.70}
    fired, detail = r.evaluate_audio_content_absent(audio, text)
    assert fired is True
    assert "FIRED" in detail


def test_evaluate_audio_content_absent_not_met_when_an_audio_arm_is_high():
    audio = {flight.ARM_A_LCO3: 0.50}
    text = {flight.ARM_T_QW: 0.70}
    fired, _detail = r.evaluate_audio_content_absent(audio, text)
    assert fired is False


def test_evaluate_audio_content_absent_cannot_evaluate_when_all_dropped():
    fired, detail = r.evaluate_audio_content_absent({flight.ARM_A_LCO3: None}, {flight.ARM_T_QW: 0.7})
    assert fired is False
    assert "cannot evaluate" in detail


def test_evaluate_knn_beats_label_match_fires_over_threshold():
    fired, detail = r.evaluate_knn_beats_label_match({flight.ARM_T_QW: 0.80})
    assert fired is True
    assert flight.ARM_T_QW in detail


def test_evaluate_knn_beats_label_match_not_met_at_threshold():
    fired, _detail = r.evaluate_knn_beats_label_match({flight.ARM_T_QW: 0.7500})
    assert fired is False  # strictly greater than, registration section 4


# ---------------------------------------------------------------------------
# C-DECODE paired comparison.
# ---------------------------------------------------------------------------


def test_evaluate_c_decode_vs_cited_fs_none_helps():
    c_decode = {f"s{i}": True for i in range(3)} | {f"s{i}": False for i in range(3, 60)}
    cited = {f"s{i}": False for i in range(3)} | {f"s{i}": False for i in range(3, 60)}
    comparison = r.evaluate_c_decode_vs_cited_fs_none(c_decode, cited)
    assert comparison.net == 3
    assert comparison.verdict == "RETRIEVAL-SUPPLY-HELPS"


def test_evaluate_c_decode_vs_cited_fs_none_hurts():
    c_decode = {f"s{i}": False for i in range(60)}
    cited = {f"s{i}": (i < 3) for i in range(60)}
    comparison = r.evaluate_c_decode_vs_cited_fs_none(c_decode, cited)
    assert comparison.net == -3
    assert comparison.verdict == "RETRIEVAL-SUPPLY-HURTS"


def test_evaluate_c_decode_vs_cited_fs_none_descriptive_when_net_small():
    c_decode = {"s1": True, "s2": False}
    cited = {"s1": False, "s2": False}
    comparison = r.evaluate_c_decode_vs_cited_fs_none(c_decode, cited)
    assert comparison.net == 1
    assert comparison.verdict == "DESCRIPTIVE"


def test_evaluate_c_decode_vs_cited_fs_none_refuses_zero_overlap():
    with pytest.raises(r.Pemb4rReadError, match="no common sample"):
        r.evaluate_c_decode_vs_cited_fs_none({"a": True}, {"b": False})


# ---------------------------------------------------------------------------
# Feasibility matrix.
# ---------------------------------------------------------------------------


def test_build_feasibility_matrix_includes_nemotron_and_clsp_as_env_gated():
    matrix = r.build_feasibility_matrix()
    names = {row.name: row.status for row in matrix}
    assert names["omni-embed-nemotron-3b"] == r.FEASIBILITY_ENV_GATED
    assert names["clsp"] == r.FEASIBILITY_ENV_GATED
    for arm_id in flight.ARM_IDS:
        assert names[arm_id] == r.FEASIBILITY_FLYABLE


def test_build_feasibility_matrix_marks_a_dropped_arm_env_gated():
    matrix = r.build_feasibility_matrix(dropped_arms={flight.ARM_A_LCO7: "DROPPED-LCO7: server sanity failed"})
    row = next(row for row in matrix if row.name == flight.ARM_A_LCO7)
    assert row.status == r.FEASIBILITY_ENV_GATED


# ---------------------------------------------------------------------------
# verify_retrieval_plan_document.
# ---------------------------------------------------------------------------


def test_verify_retrieval_plan_document_matches_a_correctly_derived_plan():
    bank_vectors = {"b1": (1.0, 0.0), "b2": (0.0, 1.0)}
    bank_labels = {"b1": "iot", "b2": "weather"}
    query_vectors = {"s1": (1.0, 0.0)}
    retrieval = flight.build_arm_retrieval(flight.ARM_A_GLAP, query_vectors, bank_vectors, bank_labels)
    document = flight.build_retrieval_plan_document({flight.ARM_A_GLAP: retrieval}, flight.ARM_A_GLAP)
    ok, mismatches = r.verify_retrieval_plan_document(
        document,
        bank_vectors_by_model={flight.MODEL_GLAP: bank_vectors},
        bank_labels=bank_labels,
        query_vectors_by_arm={flight.ARM_A_GLAP: query_vectors},
    )
    assert ok is True
    assert mismatches == ()


def test_verify_retrieval_plan_document_catches_a_tampered_dedup_set():
    bank_vectors = {"b1": (1.0, 0.0), "b2": (0.0, 1.0)}
    bank_labels = {"b1": "iot", "b2": "weather"}
    query_vectors = {"s1": (1.0, 0.0)}
    retrieval = flight.build_arm_retrieval(flight.ARM_A_GLAP, query_vectors, bank_vectors, bank_labels)
    document = flight.build_retrieval_plan_document({flight.ARM_A_GLAP: retrieval}, flight.ARM_A_GLAP)
    document["arms"][flight.ARM_A_GLAP]["per_sample"]["s1"]["dedup_labels_k5"] = ["TAMPERED"]
    ok, mismatches = r.verify_retrieval_plan_document(
        document,
        bank_vectors_by_model={flight.MODEL_GLAP: bank_vectors},
        bank_labels=bank_labels,
        query_vectors_by_arm={flight.ARM_A_GLAP: query_vectors},
    )
    assert ok is False
    assert any("dedup_labels_k5 mismatch" in m for m in mismatches)


# ---------------------------------------------------------------------------
# build_pemb4r_sweep_report -- integration, pure function of explicit inputs.
# ---------------------------------------------------------------------------


def _full_retrieval_plan_document() -> dict:
    arms: dict[str, object] = {}
    for arm_id in flight.ARM_IDS:
        per_sample = {}
        for i, (sid, gold) in enumerate([("s1", "iot"), ("s2", "weather")]):
            labels = [gold, "other", "other2"]
            per_sample[sid] = _retrieval_row(labels, [0.9, 0.5, 0.1])
        arms[arm_id] = {"mean_top1_cosine": 0.9, "per_sample": per_sample}
    return {
        "schema": flight.RETRIEVAL_PLAN_SCHEMA,
        "k_primary": 5,
        "winner_arm_id": flight.ARM_T_QW,
        "winner_selection_rule": flight.WINNER_SELECTION_RULE,
        "arms": arms,
    }


def test_build_pemb4r_sweep_report_full_sweep_all_arms_flown():
    document = _full_retrieval_plan_document()
    gold = {"s1": "iot", "s2": "weather"}
    report = r.build_pemb4r_sweep_report(retrieval_plan_document=document, gold_scenarios=gold)
    assert set(report.arm_reports) == set(flight.ARM_IDS)
    assert all(not report.arm_reports[arm_id].dropped for arm_id in flight.ARM_IDS)
    assert report.verdict.overall  # non-empty string, either a finding join or INCONCLUSIVE-4R
    # every audio arm hits vote_accuracy_k5 == 1.0 with this construction
    for arm_id in flight.AUDIO_ARM_IDS:
        assert "REGISTER-RESCUE" in report.verdict.per_audio_arm_findings[arm_id]


def test_build_pemb4r_sweep_report_respects_dropped_arms_fact():
    document = _full_retrieval_plan_document()
    gold = {"s1": "iot", "s2": "weather"}
    report = r.build_pemb4r_sweep_report(
        retrieval_plan_document=document, gold_scenarios=gold, dropped_arms={flight.ARM_A_LCO7: "DROPPED-LCO7: x"}
    )
    assert report.arm_reports[flight.ARM_A_LCO7].dropped is True
    assert report.feasibility_matrix
    matrix_names = {row.name: row.status for row in report.feasibility_matrix}
    assert matrix_names[flight.ARM_A_LCO7] == r.FEASIBILITY_ENV_GATED


def test_build_pemb4r_sweep_report_wires_c_decode_comparison():
    document = _full_retrieval_plan_document()
    gold = {"s1": "iot", "s2": "weather"}
    c_decode_correct = {f"s{i}": True for i in range(3)} | {f"s{i}": False for i in range(3, 60)}
    cited = {f"s{i}": False for i in range(60)}
    report = r.build_pemb4r_sweep_report(
        retrieval_plan_document=document,
        gold_scenarios=gold,
        c_decode_correct_by_sample=c_decode_correct,
        cited_fs_none_correct_by_sample=cited,
    )
    assert report.verdict.c_decode is not None
    assert report.verdict.c_decode.verdict == "RETRIEVAL-SUPPLY-HELPS"
    assert "RETRIEVAL-SUPPLY-HELPS" in report.verdict.overall


def test_sweep_report_to_json_and_render_do_not_raise():
    document = _full_retrieval_plan_document()
    gold = {"s1": "iot", "s2": "weather"}
    report = r.build_pemb4r_sweep_report(retrieval_plan_document=document, gold_scenarios=gold)
    payload = r.sweep_report_to_json(report)
    assert payload["schema"] == r.REPORT_SCHEMA
    rendered = r.render_sweep_report(report)
    assert "OVERALL" in rendered


def test_model_free_closure_records_owner_cancellation_of_c_decode():
    document = _full_retrieval_plan_document()
    gold = {"s1": "iot", "s2": "weather"}
    report = r.build_pemb4r_sweep_report(
        retrieval_plan_document=document,
        gold_scenarios=gold,
        c_decode_status=r.C_DECODE_CANCELED_OWNER_20260821,
    )

    payload = r.sweep_report_to_json(report)
    assert report.verdict.c_decode is None
    assert payload["verdict"]["c_decode_status"] == r.C_DECODE_CANCELED_OWNER_20260821
    assert "CANCELED-BY-OWNER" in r.render_sweep_report(report)


def test_repeat_delta_is_derived_from_persisted_vector_pairs(tmp_path):
    (tmp_path / "lco3-jitter-vectors.json").write_text(
        json.dumps({"a": [1.0, 0.0], "b": [1.0, 0.0]}), encoding="utf-8"
    )
    (tmp_path / "lco7-jitter-vectors.json").write_text(
        json.dumps({"a": [0.0, 1.0], "b": [0.0, 1.0]}), encoding="utf-8"
    )
    (tmp_path / "qw-jitter-vectors.json").write_text(
        json.dumps({"a": [1.0, 0.0], "b": [0.0, 1.0]}), encoding="utf-8"
    )

    deltas = r.load_repeat_delta_by_model(tmp_path)

    assert deltas == {flight.MODEL_LCO3: 0.0, flight.MODEL_LCO7: 0.0, flight.MODEL_QW: 1.0}


def test_flight_facts_are_reused_from_the_landed_state():
    state = {
        "gate_c_pooling_differ_lco3": {"pooling_override_present": True},
        "gate_c_pooling_differ_lco7": {"pooling_override_present": False},
        "sweeps": {arm_id: {"arm_id": arm_id} for arm_id in flight.ARM_IDS},
    }

    dropped, pooling = r.flight_facts_from_state(state)

    assert dropped == {}
    assert pooling == {flight.MODEL_LCO3: True, flight.MODEL_LCO7: False}
