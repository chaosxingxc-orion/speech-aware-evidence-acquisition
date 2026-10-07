"""Prospective architecture diagnostics distinguish omission from missing evidence."""

import copy

import pytest

from speech_aware_evidence_acquisition.analysis import slurp_process_metrics as process
from speech_aware_evidence_acquisition.analysis.paired_process_diagnostics import (
    compare_process_rows,
)
from speech_aware_evidence_acquisition.analysis.review_findings import (
    analyze_slot_review_episode,
)
from speech_aware_evidence_acquisition.analysis.system_process_report import (
    build_process_comparison,
    render_process_comparison,
)
from test_slurp_process_metrics import _review, _review_source
from test_slurp_solver_stage_attribution import (
    _answer,
    _normalised_source,
    _reference,
    _saved_row,
    _source,
)
from test_system_process_report import documents


def bound_source(*, enabled=False, multi_contact=False):
    sid = "slurp:devel:save" if multi_contact else "slurp:devel:synthetic"
    answer = _answer("weather", "query", ("city", "paris"))
    source = _source({sid: [answer]})
    bind(source, enabled)
    ref = _reference(sid)
    return source, dict(
        reference_records=(ref,),
        official_final_rows=(_saved_row(ref, answer),),
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
        legal_slot_types=("city",),
        review_applicability=pin(source, enabled),
    )


def bind(source, enabled):
    source.composed.values["native_episode"] = {
        "review_loop": "on" if enabled else "off",
        "max_revisions": int(enabled),
        "roles": {
            role: {"max_iterations": int(enabled)} for role in ("reviewer", "planner")
        },
    }


def pin(source, enabled):
    return {
        "schema": "saea-review-applicability-v1",
        "config_sha256": source.composed.config_hash,
        "review_loop": "on" if enabled else "off",
    }


def test_off_is_not_missing_or_a_zero_detection_rate():
    source, args = bound_source()
    out = process.build_slurp_process_metrics(source, **args)
    assert out["schema"] == "saea-slurp-process-metrics-v2"
    assert out["review_applicability"] == args["review_applicability"]
    assert out["learner_export_allowed"] is False
    assert out["rows"][0]["review_applicable"] is False
    for key in (
        "review_valid",
        "review_error_detection",
        "review_false_alarm",
        "revision_after_alarm",
        "entity_repair_given_revision",
    ):
        value = out["metrics"][key]
        assert value["applicability"] == "not-applicable-by-design"
        assert value["excluded_by_design"] == 1
        assert value["unknown"] == value["eligible"] == value["denominator"] == 0
        assert value["value"] is value["ci95_wilson"] is None
    assert out["conditioning_unavailable"]["review_valid"] == 0
    assert out["conditioning_not_applicable"]["review_valid"] == 1
    assert out["metrics"]["revision_of_correct_draft"]["value"] == 0
    assert (
        out["by_scenario"]["weather"]["metrics"]["review_valid"]["excluded_by_design"]
        == 1
    )
    assert (
        out["role_counts"]["reviewer_contacts"]
        == out["role_counts"]["planner_visits"]
        == 0
    )


def test_on_missing_review_remains_unknown_and_on_valid_remains_measured():
    source, args = bound_source(enabled=True)
    missing = process.build_slurp_process_metrics(source, **args)["metrics"][
        "review_valid"
    ]
    assert missing["applicability"] == "applicable"
    assert missing["unknown"] == missing["eligible"] == 1
    assert missing["excluded_by_design"] == 0
    source, args = _review_source(_review())
    bind(source, True)
    measured = process.build_slurp_process_metrics(
        source, **args, review_applicability=pin(source, True)
    )["metrics"]["review_error_detection"]
    assert measured["applicability"] == "applicable"
    assert measured["value"] == 1 and measured["unknown"] == 0


def test_legacy_source_and_abstract_reducer_are_unchanged():
    source, args = bound_source()
    args.pop("review_applicability")
    out = process.build_slurp_process_metrics(source, **args)
    assert out["schema"] == "saea-slurp-process-metrics-v1"
    assert out["metrics"]["review_valid"] == process.rate([None])
    assert (
        "review_applicability" not in out and "review_applicable" not in out["rows"][0]
    )


@pytest.mark.parametrize(
    "fault",
    [
        "hash",
        "schema",
        "extra",
        "marker",
        "iterations",
        "revision",
        "boolean",
        "missing-config",
    ],
)
def test_applicability_refuses_unbound_or_inconsistent_configuration(fault):
    source, args = bound_source()
    config = source.composed.values["native_episode"]
    if fault == "hash":
        args["review_applicability"]["config_sha256"] = "f" * 64
    elif fault == "schema":
        args["review_applicability"]["schema"] = "unknown"
    elif fault == "extra":
        args["review_applicability"]["unchecked"] = True
    elif fault == "marker":
        config["review_loop"] = "on"
    elif fault == "iterations":
        config["roles"]["planner"]["max_iterations"] = 1
    elif fault == "revision":
        config["max_revisions"] = 1
    elif fault == "boolean":
        config["roles"]["reviewer"]["max_iterations"] = False
    else:
        source.composed.values.pop("native_episode")
    with pytest.raises(ValueError):
        process.build_slurp_process_metrics(source, **args)


@pytest.mark.parametrize(
    "fault",
    [
        "reviewer-visit",
        "planner-stage",
        "interrupted",
        "route",
        "orphan-contact",
        "second-solver",
    ],
)
def test_off_refuses_actual_review_or_revision_execution(fault):
    source, args = bound_source()
    episode = source.phase_results[source.sample_ids[0]]["native_episode_receipt"]
    if fault == "reviewer-visit":
        episode["role_visits"][0]["role_id"] = "reviewer"
    elif fault == "planner-stage":
        episode["role_visits"][0]["stage"] = "planner"
    elif fault == "interrupted":
        episode["interrupted_role"] = {"role_id": "reviewer"}
    elif fault == "route":
        episode["planner_routes"] = [{"action": "ACCEPT"}]
    elif fault == "orphan-contact":
        source.bundle.trace_records["orphan/native-role-contact"] = {
            "use_role_id": "planner"
        }
    else:
        episode["role_visits"].append(copy.deepcopy(episode["role_visits"][0]))
    with pytest.raises(ValueError):
        process.build_slurp_process_metrics(source, **args)


def test_slot_audit_does_not_invent_a_missing_review_when_disabled():
    source, args = bound_source(multi_contact=True)
    out = analyze_slot_review_episode(
        source,
        legal_slot_types=("city",),
        review_applicability=args["review_applicability"],
    )
    assert out["schema"] == "saea-slot-review-episode-analysis-v2"
    assert out["rows"][0]["reviews"] == []
    assert out["counts"]["solver_visits"] == 1
    assert out["counts"]["solver_contacts"] == 2
    assert out["counts"]["reviewer_visits"] == out["counts"]["reviewer_contacts"] == 0
    assert "reviews_missing" not in out["counts"]
    assert out["counts"]["extra_solver_revisions"] == 0


def test_multi_contact_first_answer_is_last_contact_not_a_reflective_revision():
    source, args = bound_source(multi_contact=True)
    out = process.build_slurp_process_metrics(source, **args)
    assert out["rows"][0]["draft_parsed"] is True
    assert out["rows"][0]["revised"] is False
    assert out["custody"][0]["initial_solver"]["contact_index"] == 1
    assert out["delivery_stages"]["model_revision"]["full"]["stable_correct"] == 1
    assert (
        out["delivery_stages"]["model_revision_applicability"]
        == "not-applicable-by-design"
    )


def test_postprocessing_repairs_remain_visible_without_review(monkeypatch):
    source, ref = _normalised_source(monkeypatch)
    bind(source, False)
    out = process.build_slurp_process_metrics(
        source,
        reference_records=(ref,),
        official_final_rows=(
            _saved_row(ref, source.output_rows[ref.sample_id]["text"]),
        ),
        reference_binding_sha256="d" * 64,
        official_score_result_sha256="e" * 64,
        legal_slot_types=("city",),
        review_applicability=pin(source, False),
    )
    stages = out["delivery_stages"]
    assert stages["model_revision"]["entity"]["wrong_to_correct"] == 0
    assert stages["postprocessing"]["entity"]["wrong_to_correct"] == 1
    assert stages["postprocessing_repair_rate"]["value"] == 1


def paired_inputs():
    source, args = bound_source(enabled=True)
    on = process.build_slurp_process_metrics(source, **args)["rows"]
    source, args = bound_source()
    off = process.build_slurp_process_metrics(source, **args)["rows"]
    return dict(
        baseline=on,
        candidate=off,
        sample_ids=list(source.sample_ids),
        bootstrap={"n_replicates": 20, "seed": 4, "ci_level": 0.95},
    )


def test_paired_inapplicable_reviews_have_no_missing_bounds_or_bootstrap():
    out = compare_process_rows(**paired_inputs())
    assert out["schema"] == "saea-paired-process-diagnostics-v2"
    for key in (
        "review_valid",
        "error_alarm_event",
        "false_alarm_event",
        "missed_error_event",
    ):
        m = out["metrics"][key]
        assert m["applicability"] == "not-applicable-by-design"
        assert m["excluded_by_design"] == 1 and m["paired_unknown"] == 0
        assert m["population_missing_bounds"] is m["paired_bootstrap"] is None
    assert out["metrics"]["final_full_correct"]["difference"] == 0
    assert out["metrics"]["revised"]["difference"] == 0


@pytest.mark.parametrize(
    "fault", ["mixed", "missing-row-flag", "nonboolean", "off-alarm", "off-revision"]
)
def test_prospective_rows_reject_ambiguous_or_contradictory_applicability(fault):
    args = paired_inputs()
    row = args["candidate"][0]
    if fault == "mixed":
        args["baseline"][0].pop("review_applicable")
    elif fault == "missing-row-flag":
        other = copy.deepcopy(row)
        other.update(sample_id="other")
        other.pop("review_applicable")
        with pytest.raises(ValueError):
            process.aggregate_process_metrics([row, other])
        return
    elif fault == "nonboolean":
        row["review_applicable"] = 0
    elif fault == "off-alarm":
        row.update(review_valid=True, review_alarm=False)
    else:
        row["revised"] = True
    with pytest.raises(ValueError):
        compare_process_rows(**args)


def test_prospective_report_preserves_applicability_and_explains_answer_stage():
    source, args = bound_source()
    out = process.build_slurp_process_metrics(source, **args)
    values = documents()
    sid = source.sample_ids[0]
    values["recipe"]["sample_ids"] = [sid]
    for member in values["process"]["members"]:
        values["process"]["members"][member] = copy.deepcopy(out)
    report = build_process_comparison(**values)
    assert report["schema"] == "saea-business-process-cost-comparison-v2"
    assert (
        report["process"]["seed"]["review_applicability"]
        == args["review_applicability"]
    )
    assert report["process"]["seed"]["role_counts"]["reviewer_contacts"] == 0
    text = render_process_comparison(report)
    assert "not applicable by design" in text
    assert "First raw answer to selected raw answer" in text
    assert '"paris"' not in text


def test_architecture_process_data_cannot_enter_legacy_learner_export():
    from test_abstract_process_feedback import fixture
    from speech_aware_evidence_acquisition.analysis.abstract_process_feedback import (
        project_process_feedback,
    )

    report, config, bindings = fixture()
    for member in report["families"]["part"].values():
        for row in member["rows"]:
            row["review_applicable"] = True
        member.update(process.aggregate_process_metrics(member["rows"]))
    with pytest.raises(ValueError, match="export"):
        project_process_feedback(report, config=config, bindings=bindings)


def test_on_missing_review_paired_with_on_still_has_missing_bounds():
    args = paired_inputs()
    args["candidate"] = copy.deepcopy(args["baseline"])
    out = compare_process_rows(**args)["metrics"]["error_alarm_event"]
    assert out["applicability"] == "applicable"
    assert out["paired_unknown"] == 1 and out["excluded_by_design"] == 0
    assert out["population_missing_bounds"] == [-1, 1]


def test_current_on_configuration_without_redundant_marker_is_supported():
    source, args = bound_source(enabled=True)
    source.composed.values["native_episode"].pop("review_loop")
    assert (
        process.build_slurp_process_metrics(source, **args)["review_applicability"][
            "review_loop"
        ]
        == "on"
    )


def test_interrupted_first_solver_keeps_contact_count_but_not_completed_visit():
    source, args = bound_source()
    episode = source.phase_results[source.sample_ids[0]]["native_episode_receipt"]
    episode["interrupted_role"] = episode["role_visits"].pop()
    out = analyze_slot_review_episode(
        source,
        legal_slot_types=("city",),
        review_applicability=args["review_applicability"],
    )
    assert out["counts"]["solver_visits"] == 0
    assert out["counts"]["solver_contacts"] == 1
    assert out["rows"][0]["reviews"] == []


def test_malformed_interrupted_role_cannot_hide_review_off_execution():
    source, args = bound_source()
    episode = source.phase_results[source.sample_ids[0]]["native_episode_receipt"]
    episode["interrupted_role"] = "unbound"
    with pytest.raises(ValueError, match="interrupted"):
        process.build_slurp_process_metrics(source, **args)


@pytest.mark.parametrize("fault", ["third-role", "orphan-third-role", "interrupted-third-role", "repeated-perception"])
def test_off_profile_allows_only_one_perception_and_one_solver_attempt(fault):
    from speech_aware_evidence_acquisition.analysis.review_findings import validate_review_applicability

    source, args = bound_source()
    episode = source.phase_results[source.sample_ids[0]]["native_episode_receipt"]
    if fault == "third-role":
        episode["role_visits"].append({"role_id": "acquisition", "stage": "acquisition"})
    elif fault == "orphan-third-role":
        source.bundle.trace_records["orphan/native-role-contact"] = {"use_role_id": "acquisition"}
    elif fault == "interrupted-third-role":
        episode["interrupted_role"] = {"role_id": "acquisition", "stage": "acquisition"}
    else:
        episode["role_visits"].extend([{"role_id": "perception", "stage": "perception"}] * 2)
    with pytest.raises(ValueError):
        validate_review_applicability(source, args["review_applicability"])


@pytest.mark.parametrize("fault", ["mixed-version", "export-enabled"])
def test_prospective_presentation_requires_complete_applicability_and_no_export(fault):
    source, args = bound_source()
    out = process.build_slurp_process_metrics(source, **args)
    values = documents()
    values["recipe"]["sample_ids"] = list(source.sample_ids)
    for member in values["process"]["members"]:
        values["process"]["members"][member] = copy.deepcopy(out)
    bad = values["process"]["members"]["child"]
    if fault == "mixed-version":
        bad["schema"] = "saea-slurp-process-metrics-v1"
    else:
        bad["learner_export_allowed"] = True
    with pytest.raises(ValueError):
        build_process_comparison(**values)
