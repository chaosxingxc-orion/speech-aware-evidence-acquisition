"""Join actual summaries to full terminal outcomes without hiding unusable groups."""
import copy
import hashlib

import pytest

from test_system_semantic_feedback import inputs
from speech_aware_evidence_acquisition.analysis.system_semantic_feedback import (
    SemanticFeedbackError, prepare_semantic_feedback_groups, join_recorded_summaries,
)
from speech_aware_evidence_acquisition.analysis.system_summary_source import VerifiedSystemSummaries


def summary_fixture(**options):
    grouped, reports = inputs(**options)
    feedback = prepare_semantic_feedback_groups(grouped, reports)
    summaries = []
    for i, report in enumerate(reports):
        contexts, rows = [], {}
        for episode in report["episodes"]:
            sid = episode["trajectory"]["sample_id"]
            text = f"Recorded complete episode {i}: Solver delivered after Reviewer and Planner."
            contexts.append({"source_sample_id": sid, "model_context": {"trajectory": episode}})
            rows[sid] = {
                "sample_id": sid, "summary": text, "status": "usable",
                "episode_sha256": episode["content_sha256"],
                "summary_manifest_sha256": str(i)*64, "summary_request_id": f"summary-{i}-{sid}",
                "summary_response_sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        summaries.append(VerifiedSystemSummaries({}, str(i)*64, {}, {"contexts": contexts}, rows))
    return feedback, summaries


def test_recorded_summary_feedback_join_preserves_signed_empty_entity_signal():
    feedback, summaries = summary_fixture()
    before = copy.deepcopy((feedback, summaries))
    result = join_recorded_summaries(feedback, summaries)
    group = result["groups"][0]
    assert group["disposition"] == "ready"
    assert result["ready_sample_ids"] == ["s1"]
    attempts = group["model_context"]["attempts"]
    assert [a["terminal_feedback"]["utility"] for a in attempts] == [0, -1]
    assert [a["terminal_feedback"]["fp"] for a in attempts] == [0, 2]
    assert attempts[0]["summary"] == summaries[0].rows["s1"]["summary"]
    assert "advantage" not in attempts[0]["terminal_feedback"]
    assert group["candidate_bindings"][0]["run_id"] == "run-0"
    assert group["candidate_bindings"][1]["summary_request_id"] == "summary-1-s1"
    assert before == (feedback, summaries)
    assert result == join_recorded_summaries(feedback, reversed(summaries))


@pytest.mark.parametrize("status", ["empty", "output-limit", "unknown-completion", "nonstandard-finish"])
def test_unusable_summary_retains_whole_group_without_retry(status):
    feedback, summaries = summary_fixture()
    summaries[1].rows["s1"]["status"] = status
    result = join_recorded_summaries(feedback, summaries)
    assert result["ready_sample_ids"] == []
    assert len(result["groups"]) == 1
    group = result["groups"][0]
    assert group["disposition"] == "blocked-unusable-summary"
    assert len(group["model_context"]["attempts"]) == 2
    assert group["model_context"]["attempts"][1]["summary"] == summaries[1].rows["s1"]["summary"]
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0


def test_different_trajectories_with_tied_outcomes_are_kept_as_no_update():
    feedback, summaries = summary_fixture(counts=((0, 0, 0), (0, 0, 0)), finite=True)
    result = join_recorded_summaries(feedback, summaries)
    assert result["ready_sample_ids"] == []
    assert result["groups"][0]["disposition"] == "no-update-terminal-tie"
    assert len(result["groups"][0]["candidate_bindings"]) == 2


@pytest.mark.parametrize("change", ["missing", "duplicate", "episode", "text", "fingerprint", "unverified"])
def test_wrong_summary_identity_or_content_is_refused(change):
    feedback, summaries = summary_fixture()
    if change == "missing":
        summaries.pop()
    elif change == "duplicate":
        summaries.append(summaries[0])
    elif change == "episode":
        summaries[0].rows["s1"]["episode_sha256"] = "f"*64
    elif change == "text":
        summaries[0].rows["s1"]["summary"] += " injected"
    elif change == "fingerprint":
        feedback["round_id"] = "unregistered"
    else:
        summaries[0] = {}
    with pytest.raises(SemanticFeedbackError):
        join_recorded_summaries(feedback, summaries)
