"""Actual shared runner, graph, delivery and trace proofs with synthetic responses."""

import copy
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

import test_native_episode_runner as fixtures
from test_native_episode_runner import _ActualEpisodeHarness
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _minimum_model_calls_from_trace, _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError


def _finite_wire(monkeypatch, phase, *, finish="length"):
    original = fixtures._wire_response

    def render(text):
        payload = json.loads(original(text))
        if text.startswith(f"{phase}-") and ":s1:" in text:
            payload["choices"][0]["finish_reason"] = finish
        return json.dumps(payload, separators=(",", ":")).encode()

    monkeypatch.setattr(fixtures, "_wire_response", render)


def _canonical_runtime(harness, summary):
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"native_episode": {
        "finite_completion_policy": harness.config.finite_completion_policy,
        "exhaustion_policy": "raise", "max_revisions": 0,
        "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
    }})
    runtime._plan = harness.plan
    runtime._phase_summaries = [summary]
    runtime._output_rows = [
        {"sample_id": row.sample_id, "final_response_text": row.final_response_text,
         "native_episode_receipt": row.native_episode_receipt}
        for row in summary.results
    ]
    runtime._result_kind = lambda: "answer"
    runtime._arm = lambda: harness.client.arm
    return runtime


@pytest.mark.parametrize("finish", ["length", "content_filter"])
@pytest.mark.parametrize("phase,expected_kind,s1_contacts", [
    ("perception", "abstention", 1),
    ("solver", "abstention", 2),
    ("reviewer", "finite", 4),
    ("planner", "finite", 5),
])
def test_actual_four_role_finite_outcomes_keep_roster_and_source_custody(
    tmp_path, monkeypatch, phase, expected_kind, s1_contacts, finish,
):
    _finite_wire(monkeypatch, phase, finish=finish)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=2, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, finite_completion_policy="deliver-latest-or-abstain")
    if phase == "planner":
        original_output = harness._output
        harness._output = lambda key: (
            "planner-partial:s1:visit:1"
            if key[0] == "s1" and key[1] == "planner" else original_output(key)
        )
    try:
        summary = harness.run()
        runtime = _canonical_runtime(harness, summary)
        outputs = runtime._canonical_output_rows(harness.client)
    finally:
        closed = harness.close()
    assert len(summary.results) == len(outputs) == 2
    assert closed["request_count"] == s1_contacts + 5
    first, normal = summary.results
    receipt = first.native_episode_receipt
    assert "accepted_solver_receipt" not in receipt
    assert receipt["terminal_disposition"]["finish_reason"] == finish
    assert normal.final_response_text == "solver-answer:s2:visit:1"
    assert normal.native_episode_receipt["planner_routes"][-1]["action"] == "ACCEPT"
    assert len(receipt["role_visits"]) == fixtures.PHASES.index(phase)
    interrupted = receipt["interrupted_role"]["execution_receipt"]
    assert len(interrupted["contacts"]) == (2 if phase == "reviewer" else 1)
    rejected = receipt["terminal_disposition"]["rejected_contact"]
    assert rejected == interrupted["final_contact"]
    assert len(first.contacts) == s1_contacts
    assert len(first.waves) == s1_contacts
    assert not any(state.source_response_sha256 == rejected["response_text_sha256"]
                   for state in first.agent_states)
    assert len(harness.tool_contacts) == (2 if phase in {"reviewer", "planner"} else 1)

    records = {rid: payload for _, rid, payload in harness.trace.records}
    raw = records[rejected["request_id"] + "/response"]
    assert raw["text"] and hashlib.sha256(raw["text"].encode()).hexdigest() == rejected["response_text_sha256"]
    assert not any(row["text"] == raw["text"] for row in outputs)
    _verify_outputs_trace_binding(tuple(outputs), records)
    assert _minimum_model_calls_from_trace(records) == s1_contacts + 5
    from speech_aware_evidence_acquisition.analysis.native_episode_diagnostics import (
        analyze_verified_native_episode_statistics,
    )
    diagnostics = analyze_verified_native_episode_statistics(
        sample_ids=[row.sample_id for row in summary.results],
        controller_policy_id=summary.controller_policy_id,
        phase_results={row.sample_id: row.as_json() for row in summary.results},
        output_rows={row["sample_id"]: row for row in outputs}, trace_records=records,
    )
    assert diagnostics["finite_stops"]["count"] == 1
    assert diagnostics["finite_stops"]["abstention_count"] == int(expected_kind == "abstention")
    if expected_kind == "abstention":
        assert first.final_response_text == outputs[0]["text"] == ""
        assert outputs[0]["request_id"] != rejected["request_id"]
        assert "terminal_solver_receipt" not in receipt
    else:
        source = receipt["terminal_solver_receipt"]["final_contact"]
        assert first.final_response_text == "solver-answer:s1:visit:1"
        assert outputs[0]["request_id"] == source["request_id"]

    changed = copy.deepcopy(outputs)
    changed[0]["response_sha256"] = "0" * 64
    with pytest.raises(BundleError):
        _verify_outputs_trace_binding(tuple(changed), records)
    runtime._output_rows[0] = {
        **runtime._output_rows[0], "final_response_text": "forged",
    }
    with pytest.raises(FlightRuntimeError):
        runtime._canonical_output_rows(harness.client)


@pytest.mark.parametrize("policy,finish", [("raise", "length"), ("deliver-latest-or-abstain", "server_error")])
def test_actual_runner_keeps_default_and_unknown_errors_fatal(tmp_path, monkeypatch, policy, finish):
    _finite_wire(monkeypatch, "reviewer", finish=finish)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, finite_completion_policy=policy)
    try:
        with pytest.raises(Exception, match="finish_reason|unsupported"):
            harness.run()
    finally:
        harness.close()


def test_actual_runner_never_executes_a_finite_tool_directive(tmp_path, monkeypatch):
    original = fixtures._wire_tool_call
    def finite_call(tool_id):
        wire = json.loads(original(tool_id))
        wire["choices"][0]["finish_reason"] = "length"
        return json.dumps(wire, separators=(",", ":")).encode()
    monkeypatch.setattr(fixtures, "_wire_tool_call", finite_call)
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=5,
        planner_actions=("ACCEPT",), reviewer_task_tool=True,
    )
    harness.config = replace(harness.config, finite_completion_policy="deliver-latest-or-abstain")
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 3
    assert harness.tool_contacts == []
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
    receipt = summary.results[0].native_episode_receipt
    assert len(receipt["interrupted_role"]["execution_receipt"]["contacts"]) == 1
    assert receipt["terminal_disposition"]["stage"] == "review"
