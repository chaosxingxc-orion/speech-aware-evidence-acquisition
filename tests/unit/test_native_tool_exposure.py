from __future__ import annotations

import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from speech_aware_evidence_acquisition.analysis.native_tool_exposure import (
    NativeToolExposureError,
    analyze_verified_native_tool_exposure,
)

from test_native_episode_diagnostics import _fixture
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _inputs(summary, trace):
    phase = summary.results[0].as_json()
    output = {
        "sample_id": phase["sample_id"],
        "text": phase["final_response_text"],
        "native_episode_receipt": phase["native_episode_receipt"],
    }
    records = {record_id: payload for _channel, record_id, payload in trace.records}
    return {
        "sample_ids": (phase["sample_id"],),
        "controller_policy_id": summary.controller_policy_id,
        "phase_results": {phase["sample_id"]: phase},
        "output_rows": {phase["sample_id"]: output},
        "trace_records": records,
    }


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_repeated_native_calls_are_source_bound_projected_and_fit_before_send(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=10,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness.tools_for_phase.trace_sink = harness.trace
    original = harness._output

    def two_calls(key):
        _sample_id, phase, _visit, turn = key
        if phase == "reviewer" and turn == 1:
            return None
        return original(key)

    harness._output = two_calls
    try:
        summary = harness.run()
        inputs = _inputs(summary, harness.trace)
        report = analyze_verified_native_tool_exposure(**inputs)
    finally:
        harness.close()

    assert report["successful_call_count"] == 2
    assert report["exposed_successful_call_count"] == 2
    assert (
        len(
            {
                (row["source_request_id"], row["tool_call_id"], row["state_id"])
                for row in report["calls"]
            }
        )
        == 2
    )
    assert all(row["exposed_request_ids"] for row in report["calls"])
    assert all(
        row["source_completion_trace_available"] is False for row in report["calls"]
    )
    for prepared_key in harness.prepared:
        assert harness.events.index(("fit", prepared_key)) < harness.events.index(
            ("dispatch", prepared_key)
        )
    encoded = json.dumps(report, sort_keys=True)
    assert "task-contract-for-" not in encoded
    assert "solver-answer:" not in encoded
    assert report["semantics"].endswith(
        "it does not establish semantic use, causal benefit, or task quality."
    )


def test_toolless_episode_remains_representable():
    policy, phase, output, trace = _fixture()
    for key in [key for key in trace if "/tool-" in key]:
        del trace[key]

    report = analyze_verified_native_tool_exposure(
        sample_ids=("s1",),
        controller_policy_id=policy,
        phase_results={"s1": phase},
        output_rows={"s1": output},
        trace_records=trace,
    )

    assert report["successful_call_count"] == 0
    assert report["calls"] == []
    assert report["unexposed_successful_call_count"] == 0


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_forged_result_and_foreign_history_fail_closed(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    harness.tools_for_phase.trace_sink = harness.trace
    try:
        summary = harness.run()
        original = _inputs(summary, harness.trace)
    finally:
        harness.close()

    unexposed = copy.deepcopy(original)
    for key, outer in unexposed["trace_records"].items():
        if not key.endswith("/request"):
            continue
        payload = outer["payload"]
        payload["history"] = [
            state
            for state in payload.get("history", [])
            if state.get("state_kind") != "tool-result"
        ]
        control = payload["history"][-1] if payload["history"] else None
        if control and control.get("role") == "control":
            try:
                contract = json.loads(control["content"])
            except ValueError:
                contract = None
            if isinstance(contract, dict) and contract.get("schema") == (
                "saea-native-framework-contact-v1"
            ):
                contract["local_tool_result_ids"] = []
                contract["messages"] = contract["messages"][:2]
                control["content"] = json.dumps(
                    contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                control["content_sha256"] = hashlib.sha256(
                    control["content"].encode()
                ).hexdigest()
    unexposed_report = analyze_verified_native_tool_exposure(**unexposed)
    assert unexposed_report["successful_call_count"] == 1
    assert unexposed_report["unexposed_successful_call_count"] == 1
    assert unexposed_report["calls"][0]["exposed_request_ids"] == []

    result_id = next(key for key in original["trace_records"] if "/tool-result/" in key)
    forged = copy.deepcopy(original)
    forged["trace_records"][result_id]["use_result"] = {"forged": True}
    with pytest.raises(NativeToolExposureError):
        analyze_verified_native_tool_exposure(**forged)

    for field, value in (
        ("role_id", "solver"),
        ("sample_id", "foreign-sample"),
        ("request_id", "foreign-request"),
        ("source_request_sha256", "0" * 64),
    ):
        changed = copy.deepcopy(original)
        changed["trace_records"][result_id]["use_source_authority"][field] = value
        with pytest.raises(NativeToolExposureError):
            analyze_verified_native_tool_exposure(**changed)

    foreign = copy.deepcopy(original)
    source_request = next(
        row["request_id"]
        for visit in summary.results[0].native_episode_receipt["role_visits"]
        for row in visit["execution_receipt"]["contacts"]
        if visit["role_id"] == "reviewer"
    )
    later = next(
        payload["payload"]
        for key, payload in foreign["trace_records"].items()
        if key.endswith("/request")
        and payload["payload"]["request_id"] != source_request
        and any(
            state.get("state_kind") == "tool-result"
            for state in payload["payload"].get("history", [])
        )
    )
    state = next(
        state for state in later["history"] if state.get("state_kind") == "tool-result"
    )
    document = json.loads(state["content"])
    document["core_request_id"] = "foreign-request"
    state["content"] = json.dumps(document, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    with pytest.raises(NativeToolExposureError):
        analyze_verified_native_tool_exposure(**foreign)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("empty", (False, True))
def test_provisional_selection_is_visible_locally_and_in_revised_solver(tmp_path, empty):
    from dataclasses import replace
    from test_native_episode_runner import _provisional_memory_for_native_episode

    memory = _provisional_memory_for_native_episode()
    if empty:
        memory = replace(memory, records=())
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_memory=memory,
    )
    harness.tools_for_phase.trace_sink = harness.trace
    try:
        summary = harness.run()
        inputs = _inputs(summary, harness.trace)
        report = analyze_verified_native_tool_exposure(**inputs)
    finally:
        harness.close()

    assert report["successful_call_count"] == 1
    assert report["exposed_successful_call_count"] == 1
    call = report["calls"][0]
    assert call["selection_count"] == (0 if empty else 2)
    assert call["selection_empty"] is empty
    exposed_roles = {
        visit["role_id"]
        for visit in summary.results[0].native_episode_receipt["role_visits"]
        for contact in visit["execution_receipt"]["contacts"]
        if contact["request_id"] in call["exposed_request_ids"]
    }
    assert {"reviewer", "solver"} <= exposed_roles
    assert "Guidance 1." not in json.dumps(report)
    for key in (("s1", "reviewer", 1, 2), ("s1", "solver", 2, 1)):
        assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
