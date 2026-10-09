"""Synthetic persisted-stage identity consistency regressions; no source replay."""
import copy
import pytest
from speech_aware_evidence_acquisition.analysis import slurp_process_metrics as metrics
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_solver_stage_statistics import built, validate, _answer


def reports():
    source, args = built()
    value = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    other, other_args = built({"slurp:devel:one":[_answer("calendar", "remove", ("date", "tomorrow"))]})
    wrong = metrics.build_slurp_process_metrics(other, **other_args, solver_stage_statistics=True)
    return value, wrong


def repin(value):
    stage = value["solver_stage_statistics"]
    stage["rows_sha256"] = content_hash(stage["rows"])
    stage["aggregate"] = metrics.aggregate_solver_stage_statistics(stage["rows"], value["rows"])


@pytest.mark.parametrize("endpoint", ["draft", "pre_delivery", "final"])
def test_repinned_identical_text_cannot_claim_different_numeric_endpoint(endpoint):
    value, wrong = reports()
    row = value["solver_stage_statistics"]["rows"][0]
    assert row["custody"]["initial_solver"]["response_text_sha256"] == row["custody"]["final_delivery"]["response_text_sha256"]
    assert row["custody"]["final_delivery"]["response_text_sha256"] == row["custody"]["final_delivery"]["delivered_text_sha256"]
    row["metrics"][endpoint] = copy.deepcopy(wrong["solver_stage_statistics"]["rows"][0]["metrics"][endpoint])
    repin(value)
    with pytest.raises(ValueError, match="identical stage text hashes"):
        validate(value)


def test_identical_text_across_distinct_visits_retains_real_revision_without_harm():
    text = _answer("weather", "query", ("city", "paris"))
    source, args = built({"slurp:devel:one":[text, text]})
    report = metrics.build_slurp_process_metrics(source, **args, solver_stage_statistics=True)
    row = report["solver_stage_statistics"]["rows"][0]
    assert row["revision"]["completed_solver_revision"] is True
    assert row["revision"]["delivered_solver_revision"] is True
    assert row["revision"]["response_changed"] is False
    assert row["custody"]["initial_solver"]["visit_index"] != row["custody"]["final_delivery"]["visit_index"]
    assert row["metrics"]["draft"] == row["metrics"]["pre_delivery"] == row["metrics"]["final"]
    assert report["solver_stage_statistics"]["aggregate"]["transitions"]["raw_model"]["entity"]["correct_to_wrong"] == 0
    validate(report)


def joined_normalisation(value):
    row = value["solver_stage_statistics"]["rows"][0]
    custody = row["custody"]["final_delivery"]
    custody["normalisation"] = {"normaliser_id":"synthetic-no-op", "carrier_lock_key":"slurp",
        "input_sha256":custody["response_text_sha256"], "output_sha256":custody["delivered_text_sha256"]}
    value["custody"][0]["final_delivery"] = copy.deepcopy(custody)
    repin(value)


@pytest.mark.parametrize("field", ["input_sha256", "output_sha256"])
def test_repinned_normaliser_must_join_original_raw_and_delivered_hashes(field):
    value, _ = reports()
    joined_normalisation(value)
    validate(value)
    value["solver_stage_statistics"]["rows"][0]["custody"]["final_delivery"]["normalisation"][field] = "f"*64
    value["custody"][0]["final_delivery"] = copy.deepcopy(value["solver_stage_statistics"]["rows"][0]["custody"]["final_delivery"])
    repin(value)
    with pytest.raises(ValueError, match="normalisation input/output"):
        validate(value)


def test_repinned_non_normalised_delivery_cannot_change_selected_raw_hash():
    value, _ = reports()
    value["solver_stage_statistics"]["rows"][0]["custody"]["final_delivery"]["delivered_text_sha256"] = "f"*64
    value["custody"][0]["final_delivery"] = copy.deepcopy(value["solver_stage_statistics"]["rows"][0]["custody"]["final_delivery"])
    repin(value)
    with pytest.raises(ValueError, match="unmodified delivery"):
        validate(value)


def test_repinned_noop_normaliser_cannot_claim_numeric_postprocessing_repair():
    value, wrong = reports()
    joined_normalisation(value)
    row = value["solver_stage_statistics"]["rows"][0]
    row["metrics"]["pre_delivery"] = copy.deepcopy(wrong["solver_stage_statistics"]["rows"][0]["metrics"]["pre_delivery"])
    repin(value)
    with pytest.raises(ValueError, match="identical stage text hashes"):
        validate(value)
