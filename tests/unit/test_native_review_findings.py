"""Post-seal Reviewer declarations bind to exact role and decision receipts."""
import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_episode_source import VerifiedNativeEpisodeSource
from speech_aware_evidence_acquisition.analysis.review_findings import (
    ReviewFindingsError, analyze_native_review_findings,
)
from test_native_episode_diagnostics import _fixture
from test_review_findings import report


def source(text=None):
    policy, phase, output, trace = _fixture()
    if text is not None:
        final = phase["native_episode_receipt"]["role_visits"][2]["execution_receipt"]["final_contact"]
        request_id = final["request_id"]
        text_sha = hashlib.sha256(text.encode()).hexdigest()
        response_sha = hashlib.sha256(("response:" + text).encode()).hexdigest()
        # The receipt and both its serialized copies share the fixture's contact.
        final.update(response_sha256=response_sha, response_text_sha256=text_sha)
        trace[request_id + "/response"].update(
            text=text, response_sha256=response_sha, response_text_sha256=text_sha,
        )
        trace[request_id + "/native-role-contact"].update(
            use_response_sha256=response_sha, use_response_text_sha256=text_sha,
        )
        for contact in phase["contacts"]:
            if contact["plan"]["contact_id"] == final["agent_contact_id"]:
                contact["response_sha256"] = text_sha
    return VerifiedNativeEpisodeSource(
        bundle=SimpleNamespace(trace_records=trace, manifest={"run_id": "synthetic"}),
        composed=SimpleNamespace(config_hash="a"*64),
        plan=SimpleNamespace(run_id="synthetic", attempt_id="synthetic-attempt"),
        sample_ids=("s1",), phase_results={"s1": phase}, output_rows={"s1": output},
        phase_artifact_sha256="b"*64, diagnostics={},
    )


def test_report_is_joined_to_reviewed_solver_and_actual_planner_not_recommendation():
    result = analyze_native_review_findings(source(report()))
    row = result["rows"][0]
    assert row["report_status"] == "parsed"
    assert row["reviewer_source"]["request_id"] == "request-reviewer-2"
    assert row["reviewed_solver_source"]["request_id"] == "request-solver-1"
    assert row["recommendation"] == "reconsider"
    assert row["planner_action"] == "ACCEPT"
    assert row["solver_revision_attempted"] is False
    assert row["solver_revision_completed"] is False
    assert row["finding_dimensions"] == ["intent"]
    assert row["declared_evidence_ids"] == ["value:intent-boundary:1"]
    assert "rationale" not in json.dumps(result)
    assert "tool call" not in json.dumps(result)
    assert result["report_status_counts"] == {"parsed": 1}
    assert result["source"]["phase_artifact_sha256"] == "b"*64


def test_unstructured_historical_report_is_malformed_not_a_no_issue_vote():
    result = analyze_native_review_findings(source())
    row = result["rows"][0]
    assert row["report_status"] == "malformed"
    assert row["verdict"] is None
    assert row["recommendation"] is None
    assert result["verdict_counts"] == {}


def test_foreign_or_missing_roster_is_refused():
    data = source(report())
    data.phase_results["foreign"] = copy.deepcopy(data.phase_results["s1"])
    with pytest.raises(ReviewFindingsError, match="roster"):
        analyze_native_review_findings(data)
    with pytest.raises(ReviewFindingsError):
        analyze_native_review_findings(SimpleNamespace())


def test_report_source_mutation_is_rejected_not_counted_as_bad_model_json():
    data = source(report())
    data.bundle.trace_records["request-reviewer-2/response"]["text"] = "{}"
    with pytest.raises(ValueError):
        analyze_native_review_findings(data)


@pytest.mark.parametrize("with_solver,expected", [(True, "finite"), (False, "missing")])
def test_unfinished_or_absent_review_is_never_a_no_issue_declaration(with_solver, expected):
    from test_native_episode_diagnostics import _finite_fixture

    data = source()
    _, phase, output, trace = _finite_fixture(with_solver=with_solver)
    data.phase_results["s1"] = phase
    data.output_rows["s1"] = output
    data.bundle.trace_records.clear()
    data.bundle.trace_records.update(trace)
    row = analyze_native_review_findings(data)["rows"][0]
    assert row["report_status"] == expected
    assert row["verdict"] is None
    assert row["planner_action"] is None
    assert row["solver_revision_attempted"] is False


@pytest.mark.parametrize("completed", [True, False])
def test_revision_attempt_and_completion_are_distinct(completed):
    data = source(report())
    episode = data.phase_results["s1"]["native_episode_receipt"]
    episode["planner_routes"][0]["action"] = "REVISE"
    later_solver = copy.deepcopy(episode["role_visits"][1])
    if completed:
        episode["role_visits"].append(later_solver)
    else:
        episode["interrupted_role"] = later_solver
    row = analyze_native_review_findings(data)["rows"][0]
    assert row["planner_action"] == "REVISE"
    assert row["solver_revision_attempted"] is True
    assert row["solver_revision_completed"] is completed
