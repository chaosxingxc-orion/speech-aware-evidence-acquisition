"""Join the real Audio2Tool adapter to runtime dispatch and terminal custody.

Speech, released knowledge, capacity admission and model replies are synthetic.
No target, scorer, remote service or research result is consumed. This proves
whole-episode engineering paths, not a GPU flight, capacity or task quality.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _minimum_model_calls_from_trace,
    _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.adapters import audio2tool as task_module
from speech_aware_evidence_acquisition.rails.adapters.audio2tool_runtime import Audio2ToolRuntimeAdapter
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

from test_audio2tool_native_episode_integration import CONTRACT, FINAL, STATE, _real_adapter
from test_e35_earnings_native_episode_wire import PROGRAM_ID, _values
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, _plan
from test_raw_execution_unit_runner import _runtime

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = "Preserve repeated tool calls and request order; apply the latest explicit correction."


@pytest.mark.parametrize("route", [
    "accept", "revise", "lookup", "empty-lookup", "exhaust",
    "abstain", "blank-revision", "whitespace", "empty-length",
])
def test_a2t_native_branches_preserve_complete_answers_and_terminal_custody(
    tmp_path, monkeypatch, route,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime must not read targets, task rows or score answers.")

    from speech_aware_evidence_acquisition.data import audio2tool as raw_loader
    for name in ("load_expected_calls", "load_audio2tool", "audio2tool_receipts"):
        monkeypatch.setattr(task_module, name, forbidden)
    monkeypatch.setattr(raw_loader, "load_query_rows", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "gold", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "score_response", forbidden)

    ids = ("tier3_multi_intent:000001", "tier3_multi_intent:000002")
    plan = _plan(
        carrier_lock_key="audio2tool",
        split_identity_hash=split_identity_hash(prefixed("audio2tool", ids)),
        planned_model_calls=22,
    )
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=2, sample_ids=ids, max_revisions=1,
        max_contacts=11, planner_actions=("ACCEPT",),
        arm="speech-feature-query-native-tools", execution_plan=plan,
    )
    program = default_phase_program(PROGRAM_ID)
    harness.program = program
    harness.adapter = _real_adapter(harness, tmp_path, PROGRAM_ID)
    assert isinstance(harness.adapter, Audio2ToolRuntimeAdapter)
    assert tuple(s.sample_id for s in harness.adapter.load_split("all")) == ids
    values = _values(armed=False, carrier="audio2tool")
    values["native_episode"].update(
        finite_completion_policy="deliver-latest-or-abstain",
        react_exhaustion_policy="continue-without-answer",
        exhaustion_policy="deliver-latest-solver",
    )
    values["native_contact_fit"] = {
        "run_id": "SAEA-SYNTHETIC-A2T-BRANCH-FIT",
        "attempt_id": "attempt-synthetic-a2t-branch-fit", "contact_cap": 22,
    }
    runtime = _runtime(harness, None, harness.material_for_phase, values)
    runtime._repo_root = ROOT
    queried = []
    original_binding = runtime._acquisition_requery_binding

    def bind_acquisition(config, supply, snapshot):
        def prepared_supply(phase, context):
            queried.append((phase, context.sample_id))
            return SimpleNamespace(fusion_decision=SimpleNamespace(
                selected_value_ids=("synthetic:ordered-actions",) if route == "lookup" else (),
            ))
        return original_binding(config, prepared_supply, SimpleNamespace(values=(SimpleNamespace(
            value_id="synthetic:ordered-actions", content=EVIDENCE,
            associated_facet_ids=("ordered-actions",),
        ),)))

    runtime._acquisition_requery_binding = bind_acquisition

    def output(key):
        sid, role, visit, _ = key
        affected = sid == ids[0]
        if role == "planner":
            if affected and route in {"revise", "lookup", "empty-lookup", "exhaust", "blank-revision"}:
                if visit == 1 or route == "exhaust":
                    return "ACQUIRE" if "lookup" in route else "REVISE"
            return "ACCEPT"
        if role == "solver":
            empty = affected and (route in {"abstain", "whitespace", "empty-length"}
                                  or (route == "blank-revision" and visit == 2))
            if empty:
                return "  \n" if route == "whitespace" else ""
            return FINAL if not affected or visit == 2 else FINAL.replace("level=20", "level=50")
        if role == "perception":
            return STATE
        return "Check the active correction; the Reviewer does not deliver tool calls."

    harness._output = output
    if route == "empty-length":
        original_post = harness.transport._post

        def post(url, raw):
            response = json.loads(original_post(url, raw))
            if response["choices"][0]["message"].get("content") == "":
                response["choices"][0]["finish_reason"] = "length"
            return json.dumps(response).encode()

        harness.transport._post = post

    def fit(request):
        harness.request_gate(request)

    fit.receipts = []
    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", lambda *_: fit)
    try:
        rows, contacts, *_ = runtime._dispatch_phase_program(harness.client, plan, PROGRAM_ID)
        runtime._output_rows = rows
        canonical = runtime._canonical_output_rows(harness.client)
        summary = runtime._phase_summaries[0]
    finally:
        closed = harness.close()

    assert contacts == closed["request_count"] == len(harness.prepared)
    assert len(canonical) == len(summary.results) == 2
    final_rows = {r["sample_id"]: r for r in canonical}
    assert final_rows[ids[1]]["text"] == FINAL
    expected = ("" if route in {"abstain", "whitespace", "empty-length"} else
                FINAL if route in {"revise", "lookup", "empty-lookup", "exhaust"} else
                FINAL.replace("level=20", "level=50"))
    assert final_rows[ids[0]]["text"] == expected
    for row in canonical:
        assert row["carrier_lock_key"] == "audio2tool"
        if row["text"]:
            assert len(row["text"].split("; ")) == 5
            assert row["text"].count("setLight(") == 4
    for (sid, role, visit, _), entry in harness.prepared.items():
        rendered = entry["rendered"]
        assert rendered["messages"][0]["content"] == CONTRACT
        assert next(other for other in ids if other != sid) not in json.dumps(rendered)
        assert not {"setLight", "setVolume"}.intersection(
            tool["function"]["name"] for tool in rendered.get("tools", [])
        )
        if sid == ids[0] and role == "solver" and visit == 2:
            assert (EVIDENCE in json.dumps(rendered)) == (route == "lookup")
    assert queried == ([("solver", ids[0])] if "lookup" in route else [])
    for result in summary.results:
        episode = result.native_episode_receipt
        assert len(episode["acquisition"]["acquisitions"]) == int(
            result.sample_id == ids[0] and "lookup" in route
        )
        assert episode["acquisition"]["contacts_used"] == 0
    trace = harness.world.run_dir / f"{plan.run_id}.trace.jsonl"
    records = [json.loads(line) for line in trace.read_text().splitlines()]
    payloads = {r["record_id"]: r["payload"] for r in records}
    assert len(payloads) == len(records)
    _verify_outputs_trace_binding(tuple(canonical), payloads)
    assert _minimum_model_calls_from_trace(payloads) == contacts
