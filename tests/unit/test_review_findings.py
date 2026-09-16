"""Structured review findings preserve uncertainty and decision authority."""
import json
import pytest
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from speech_aware_evidence_acquisition.analysis.review_findings import (
    REVIEW_FINDINGS_SCHEMA, ReviewFindingsError, parse_review_findings,
)

def report(**changes):
    value = {
        "schema": "saea-review-findings-v1",
        "verdict": "supported-issue",
        "findings": [{
            "dimension": "intent",
            "rationale": "The requested operation conflicts with the selected intent.",
            "evidence_ids": ["value:intent-boundary:1"],
        }],
        "recommendation": "reconsider",
        "remaining_uncertainty": "",
    }
    value.update(changes)
    return json.dumps(value)

def test_supported_issue_is_a_recommendation_not_a_planner_action():
    parsed = parse_review_findings(report())
    assert parsed["schema"] == REVIEW_FINDINGS_SCHEMA
    assert parsed["verdict"] == "supported-issue"
    assert parsed["recommendation"] == "reconsider"
    assert "action" not in parsed
    assert parsed["findings"][0]["evidence_ids"] == ["value:intent-boundary:1"]

def test_accept_supported_draft_without_inventing_a_problem():
    parsed = parse_review_findings(report(
        verdict="no-supported-issue", findings=[], recommendation="retain"
    ))
    assert parsed["findings"] == []

def test_insufficient_evidence_is_not_a_detected_error():
    parsed = parse_review_findings(report(
        verdict="insufficient-evidence", recommendation="seek-evidence",
        remaining_uncertainty="The last entity cannot be resolved from the current observation."
    ))
    assert parsed["verdict"] != "supported-issue"

@pytest.mark.parametrize("text", [
    "", "There is an error.", chr(96)*3 + "json\n{}\n" + chr(96)*3, "[]", "null",
    '{"schema":"saea-review-findings-v1","schema":"other"}',
    report(extra="unregistered"),
    report(schema="other"),
    report(verdict="wrong"),
    report(recommendation="REVISE"),
    report(findings=[]),
    report(verdict="no-supported-issue", recommendation="retain"),
    report(verdict="supported-issue", recommendation="retain"),
    report(verdict="insufficient-evidence", remaining_uncertainty=""),
    report(remaining_uncertainty="x" * 241),
    report(findings=[{
        "dimension": "intent", "rationale": " ", "evidence_ids": []
    }]),
    report(findings=[{
        "dimension": "answer", "rationale": "Unsupported dimension.", "evidence_ids": []
    }]),
    report(findings=[{
        "dimension": "intent", "rationale": "A concern.", "evidence_ids": ["x", "x"]
    }]),
    report(findings=[{
        "dimension": "intent", "rationale": "A concern.", "evidence_ids": [1]
    }]),
    report(findings=[{
        "dimension": "intent", "rationale": "A concern.", "evidence_ids": [],
        "replacement_answer": "not allowed",
    }]),
])
def test_refuse_malformed_or_ambiguous_reports_without_inventing_a_verdict(text):
    with pytest.raises(ReviewFindingsError):
        parse_review_findings(text)

def test_json_whitespace_is_allowed_but_content_is_not_rewritten():
    parsed = parse_review_findings(" \n" + report() + "\n ")
    assert parsed["findings"][0]["rationale"].endswith("intent.")

@pytest.mark.parametrize("field,value", [
    ("findings", [{"dimension": "intent", "rationale": "x", "evidence_ids": []}] * 3),
    ("findings", "issue"),
    ("remaining_uncertainty", None),
])
def test_bound_report_shape(field, value):
    with pytest.raises(ReviewFindingsError):
        parse_review_findings(report(**{field: value}))


def test_nonfinite_and_nonstring_reports_are_rejected():
    for text in [None, 4, "x" * 16385, report().replace('""', 'NaN')]:
        with pytest.raises(ReviewFindingsError):
            parse_review_findings(text)


def test_whitespace_only_citation_is_not_a_valid_evidence_id():
    with pytest.raises(ReviewFindingsError):
        parse_review_findings(report(findings=[{
            "dimension": "slot-span", "rationale": "The span includes unrelated speech.",
            "evidence_ids": [" "],
        }]))


def test_held_config_changes_only_the_review_prompt_and_description():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    first = json.loads((root / "configs/baseline/slurp-native-evidence-review-train-a-held-v1.json").read_text())
    second = json.loads((root / "configs/baseline/slurp-native-evidence-review-train-a-held-v2.json").read_text())
    changed = second["phase_material"]["reviewer"]["instruction_template"]
    assert changed == "probes/slurp_native_role_reviewer_findings_v1.txt"
    second["phase_material"]["reviewer"]["instruction_template"] = first["phase_material"]["reviewer"]["instruction_template"]
    second["what_this_is"] = first["what_this_is"]
    assert second == first
    assert "no-supported-issue" in (root / "configs" / changed).read_text()


def test_framework_carries_review_report_but_planner_keeps_routing_authority(tmp_path):
    from dataclasses import replace
    from pathlib import Path
    from test_native_episode_runner import _ActualEpisodeHarness

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=10,
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    report_text = report()
    original_output = harness._output
    original_material = harness.material_for_phase
    root = Path(__file__).resolve().parents[2]
    prompt = (root / "configs/probes/slurp_native_role_reviewer_findings_v1.txt").read_text()

    def output(key):
        _sample, role, _visit, turn = key
        if role == "reviewer" and turn > 1:
            return report_text
        return original_output(key)

    def material(phase, context, sealed):
        value = original_material(phase, context, sealed)
        return replace(value, instruction=value.instruction + "\n" + prompt) if phase == "reviewer" else value

    harness._output = output
    harness.material_for_phase = material
    try:
        result = harness.run().results[0].as_json()
    finally:
        harness.close()
    assert result["final_response_text"].startswith("solver-answer:")
    assert result["native_episode_receipt"]["planner_routes"][0]["action"] == "ACCEPT"
    assert sum(v["role_id"] == "solver" for v in result["native_episode_receipt"]["role_visits"]) == 1
    planner_requests = [
        item["rendered"] for key, item in harness.prepared.items() if key[1] == "planner"
    ]
    assert len(planner_requests) == 1
    assert report_text in json.dumps(planner_requests[0], ensure_ascii=False).replace('\\"', '"')
    assert any(prompt in json.dumps(item["rendered"], ensure_ascii=False).replace("\\n", "\n").replace('\\"', '"')
               for key, item in harness.prepared.items() if key[1] == "reviewer")
