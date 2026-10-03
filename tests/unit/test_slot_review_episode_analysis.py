"""Source-bound post-call diagnostics preserve every case and raw response."""

import copy
import hashlib
import json

import pytest

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_source import source as runtime_source  # noqa: F401,F811
from test_native_review_findings import source
from speech_aware_evidence_acquisition.analysis.review_findings import (
    analyze_slot_review_episode,
)


def review(types=("time",)):
    return json.dumps(
        {
            "findings": [
                {
                    "kind": "boundary",
                    "slot_types": list(types),
                    "draft_fragment": "a span",
                    "reason": "Inspect the named span.",
                }
            ],
            "checked": ["time"],
        }
    )


def set_reply(data, visit_index, text):
    row = data.phase_results["s1"]
    contact = row["native_episode_receipt"]["role_visits"][visit_index][
        "execution_receipt"
    ]["final_contact"]
    text_sha = hashlib.sha256(text.encode()).hexdigest()
    response_sha = hashlib.sha256(("response:" + text).encode()).hexdigest()
    contact.update(response_sha256=response_sha, response_text_sha256=text_sha)
    trace = data.bundle.trace_records
    rid = contact["request_id"]
    trace[rid + "/response"].update(
        text=text, response_sha256=response_sha, response_text_sha256=text_sha
    )
    trace[rid + "/native-role-contact"].update(
        use_response_sha256=response_sha, use_response_text_sha256=text_sha
    )
    for phase_contact in row["contacts"]:
        if phase_contact["plan"]["contact_id"] == contact["agent_contact_id"]:
            phase_contact["response_sha256"] = text_sha


def test_exact_context_visibility_is_not_semantic_consumption():
    from speech_aware_evidence_acquisition.rails.review_handoff import (
        normalize_review_handoff,
    )

    data = source(review())
    set_reply(data, 1, '{"scenario":"alarm","action":"set","entities":[]}')
    payload = data.bundle.trace_records["request-planner-1/request"]["payload"]
    payload["task_instruction"] = "Criticism: " + normalize_review_handoff(review())
    result = analyze_slot_review_episode(data, legal_slot_types=("time",))
    row = result["rows"][0]
    assert result["counts"]["reviews_valid"] == 1
    assert result["counts"]["solver_strict_task_json"] == 1
    assert row["reviews"][0]["handoff_in_next_planner_context"] is True
    assert row["reviews"][0]["planner_action"] == "ACCEPT"
    assert "draft_fragment" not in json.dumps(result)
    assert "Inspect the named span" not in json.dumps(result)
    assert result["claims_semantic_consumption"] is False


def test_valid_empty_criticism_and_invalid_format_are_distinct():
    empty = analyze_slot_review_episode(
        source('{"findings":[],"checked":[]}'), legal_slot_types=("time",)
    )
    malformed = analyze_slot_review_episode(
        source("prose only"), legal_slot_types=("time",)
    )
    assert empty["counts"].get("findings", 0) == 0
    assert empty["counts"]["reviews_valid"] == 1
    assert malformed["counts"]["reviews_invalid"] == 1


def test_non_slot_identifier_is_reported_without_repair():
    result = analyze_slot_review_episode(
        source(review(("alarm_set",))), legal_slot_types=("time",)
    )
    assert result["counts"]["findings_with_non_slot_identifiers"] == 1
    assert result["rows"][0]["reviews"][0]["non_slot_identifiers"] == ["alarm_set"]


@pytest.mark.parametrize(
    "text",
    [
        '<tool_call>{"name":"lookup"}</tool_call>',
        '```json\n{"scenario":"alarm","action":"set","entities":[]}\n```',
        '{"scenario":"alarm","scenario":"alarm","action":"set","entities":[]}',
        '{"scenario":"alarm","action":"set","entities":[{"type":"time","filler":NaN}]}',
        '{"scenario":"alarm","action":"set","entities":null}',
        '{"scenario":"alarm","action":"set","entities":[{"type":"time","filler":1}]}',
    ],
)
def test_invalid_solver_reply_remains_flagged(text):
    data = source(review())
    set_reply(data, 1, text)
    result = analyze_slot_review_episode(data, legal_slot_types=("time",))
    assert result["counts"]["solver_not_strict_task_json"] == 1
    assert result["rows"][0]["solver_visits"][0]["strict_task_json"] is False


def test_trace_tampering_and_foreign_roster_fail_closed():
    data = source(review())
    data.bundle.trace_records["request-reviewer-2/response"]["text"] = "{}"
    with pytest.raises(ValueError):
        analyze_slot_review_episode(data, legal_slot_types=("time",))
    data = source(review())
    data.phase_results["other"] = copy.deepcopy(data.phase_results["s1"])
    with pytest.raises(ValueError):
        analyze_slot_review_episode(data, legal_slot_types=("time",))


@pytest.mark.parametrize("inventory", [(), ("time", "time"), ("",), "time"])
def test_missing_or_ambiguous_inventory_is_refused(inventory):
    with pytest.raises(ValueError):
        analyze_slot_review_episode(source(review()), legal_slot_types=inventory)


def test_missing_review_is_not_a_valid_empty_report():
    from test_native_episode_diagnostics import _finite_fixture

    data = source()
    _, phase, output, trace = _finite_fixture(with_solver=False)
    data.phase_results["s1"] = phase
    data.output_rows["s1"] = output
    data.bundle.trace_records.clear()
    data.bundle.trace_records.update(trace)
    result = analyze_slot_review_episode(data, legal_slot_types=("time",))
    assert result["counts"]["reviews_missing"] == 1


def test_unverified_source_cannot_open_raw_roles():
    with pytest.raises(ValueError):
        analyze_slot_review_episode({}, legal_slot_types=("time",))


def test_duplicate_planner_route_is_refused():
    data = source(review())
    routes = data.phase_results["s1"]["native_episode_receipt"]["planner_routes"]
    routes.append(copy.deepcopy(routes[0]))
    with pytest.raises(ValueError):
        analyze_slot_review_episode(data, legal_slot_types=("time",))


def test_every_real_shared_runtime_case_and_revision_is_retained(runtime_source):  # noqa: F811
    from speech_aware_evidence_acquisition.analysis.native_episode_source import (
        verify_native_episode_source,
    )

    verified = verify_native_episode_source(**runtime_source["args"])
    result = analyze_slot_review_episode(verified, legal_slot_types=("time",))
    assert [r["sample_id"] for r in result["rows"]] == ["s2", "s1"]
    assert result["sample_count"] == 2
    assert result["counts"]["extra_solver_revisions"] == 2
    assert result["counts"]["reviews_invalid"] == 4
    assert result["planner_actions"] == {"REVISE": 2, "ACCEPT": 2}
