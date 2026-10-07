"""Exercise Solver lookup through the shared runner, client and OpenJiuwen graph."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from test_released_target_index import _binding
from test_phase_native_tools import call
from test_solver_tool_access import TARGET, solver_values
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
import test_native_episode_runner as episode_runner
from test_solver_on_demand_routing import runtime_for, slot_binding

pytestmark = pytest.mark.usefixtures("_spawn_live_matching_process")

def harness_for(tmp_path, monkeypatch, *, arguments=None, opt_out=False, extra_call=False, repeat_call=False):
    binding = slot_binding(_binding(tmp_path / "stores"), tmp_path / "stores")
    values = solver_values()
    builder = episode_runner.build_phase_tools

    def tools(_config, program, **kwargs):
        runtime = runtime_for(values, binding, tmp_path / "stores")
        runtime._resolve_phase_supply(program, binding.composite_snapshot)
        router = runtime._knowledge_store_supply
        return builder(values, program, **{**kwargs, "snapshot": binding.composite_snapshot},
                       knowledge_stores=binding, supply_for_store=router)

    monkeypatch.setattr(episode_runner, "build_phase_tools", tools)
    monkeypatch.setattr(episode_runner, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode_runner, "TASK_CONTRACT_TOOL", TARGET)
    args = arguments if arguments is not None else {
        "store_id": "slot-contracts", "view": "text", "candidate_ids": ["event_time"],
        "distinction": "Read the fixed time-slot meaning before answering.",
    }
    calls = call(TARGET, args)
    if extra_call:
        calls += [{**deepcopy(calls[0]), "id": "second-call"}]
    def wire(_tool):
        return json.dumps({"choices": [{"message": {"role": "assistant", "content": "Read fixed slot evidence.",
                                                    "tool_calls": calls}, "finish_reason": "tool_calls"}],
                           "usage": {"prompt_tokens": 7, "completion_tokens": 3}}).encode()
    monkeypatch.setattr(episode_runner, "_wire_tool_call", wire)
    harness = episode_runner._ActualEpisodeHarness(tmp_path / "episode", sample_count=1,
        max_revisions=0, max_contacts=3, planner_actions=(), reviewer_task_tool=True)
    harness.analytical_tool_role = "solver"
    harness.config = load_native_episode_config(values, harness.program)
    if repeat_call:
        original = harness._output
        harness._output = lambda key: None if key[1] == "solver" else original(key)
    if opt_out:
        harness._output = lambda key: "intent: calendar_set\nentities: none" if key[1] == "solver" else "perception"
    shared_run = episode_runner.run_speech_native_agent_loop
    monkeypatch.setattr(episode_runner, "run_speech_native_agent_loop",
                       lambda **kwargs: shared_run(**kwargs, knowledge_value_renderer=harness.tools_for_phase.render_values))
    return harness


def test_valid_solver_lookup_result_precedes_final_answer_with_custody(tmp_path, monkeypatch):
    harness = harness_for(tmp_path, monkeypatch)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 3 and closed["cost"]["tool_calls"] == 1
    assert len(harness.tool_contacts) == 1
    assert harness.tool_contacts[0]["source_authority_role"] == "solver"
    first = harness.prepared[("s1", "solver", 1, 1)]["rendered"]
    final = harness.prepared[("s1", "solver", 1, 2)]["rendered"]
    assert first["tool_choice"] == "auto" and final["tool_choice"] == "none"
    body = json.loads(next(m for m in final["messages"] if m["role"] == "tool")["content"])
    assert body["result"]["store_id"] == "slot-contracts" and len(body["evidence"]) == 1
    result = summary.results[0]
    assert result.final_response_text == "solver-answer:s1:visit:1"
    accepted = result.native_episode_receipt["accepted_solver_receipt"]["final_contact"]
    assert accepted == harness.traced_contact(accepted["agent_contact_id"])
    assert [v["stage"] for v in result.native_episode_receipt["role_visits"]] == ["perception", "solver"]
    assert harness.material_visits[("s1", "reviewer")] == harness.material_visits[("s1", "planner")] == 0


def test_solver_can_opt_out_without_hidden_lookup_or_extra_answer_contact(tmp_path, monkeypatch):
    harness = harness_for(tmp_path, monkeypatch, opt_out=True)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 2 and not harness.tool_contacts
    assert summary.results[0].final_response_text == "intent: calendar_set\nentities: none"


def test_empty_lookup_remains_visible_before_the_final_answer(tmp_path, monkeypatch):
    args = {"store_id": "slot-contracts", "view": "text", "candidate_ids": ["unavailable-slot"],
            "distinction": "Check whether the fixed source has this slot meaning."}
    harness = harness_for(tmp_path, monkeypatch, arguments=args)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    final = harness.prepared[("s1", "solver", 1, 2)]["rendered"]
    body = json.loads(next(m for m in final["messages"] if m["role"] == "tool")["content"])
    assert body["evidence"] == []
    assert body["result"]["missing_candidate_ids"] == ["unavailable-slot"]
    assert closed["request_count"] == 3 and len(harness.tool_contacts) == 1
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"


def test_exhausted_tool_turn_cannot_invoke_again_or_deliver_tool_call_text(tmp_path, monkeypatch):
    harness = harness_for(tmp_path, monkeypatch, repeat_call=True)
    try:
        with pytest.raises(episode_runner.NativeEpisodeError, match="did not return an answer"):
            harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 3 and len(harness.tool_contacts) == 1
    assert len(harness.prepared) == 3


@pytest.mark.parametrize("args,extra_call", [
    ({"store_id": "other", "view": "text", "candidate_ids": ["event_time"], "distinction": "Check."}, False),
    ({"store_id": "slot-contracts", "view": "text", "candidate_ids": ["a", "b", "c"], "distinction": "Check."}, False),
    ({"store_id": "slot-contracts", "view": "text", "candidate_ids": ["event_time"], "distinction": ""}, False),
    (None, True),
])
def test_rejected_call_has_no_tool_transport_and_can_reach_final_response(tmp_path, monkeypatch, args, extra_call):
    harness = harness_for(tmp_path, monkeypatch, arguments=args, extra_call=extra_call)
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 3 and not harness.tool_contacts
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:1"
    final = harness.prepared[("s1", "solver", 1, 2)]["rendered"]
    tool_messages = [m for m in final["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == (2 if extra_call else 1)


def test_unbound_slot_lookup_refuses_before_any_model_or_tool_contact(tmp_path, monkeypatch):
    harness = harness_for(tmp_path, monkeypatch)
    harness.tools_for_phase.supply_for_store = None
    try:
        with pytest.raises(ValueError, match="slot|bound"):
            harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 0 and not harness.tool_contacts


def test_tool_access_without_review_off_cannot_bypass_loader_by_direct_config(tmp_path, monkeypatch):
    harness = harness_for(tmp_path, monkeypatch)
    roles = tuple(replace(r, max_iterations=1) if r.role_kind in {"reviewer", "planner"} else r
                  for r in harness.config.roles)
    harness.config = replace(harness.config, roles=roles)
    try:
        with pytest.raises(ValueError, match="review|Solver"):
            harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 0 and not harness.tool_contacts


def test_default_off_keeps_identical_shared_requests(tmp_path):
    # Recorded with the unchanged shared runner at ebb455945917, using this
    # synthetic harness and sorted compact JSON. Assert the complete requests.
    historical = {
        "perception": "11316ec9d7366f1fa2cbba50b3b993f8b9c3611630b0609c61fa3c539bdc1876",
        "solver": "fe48918f23dc3fd2f1404440ca5cdf28e54e366918a0684d0ff7ca703295e0ad",
    }
    harness = episode_runner._ActualEpisodeHarness(tmp_path, sample_count=1, max_revisions=0,
                                                   max_contacts=2, planner_actions=())
    harness.config = episode_runner._review_off_config(max_contacts=2)
    try:
        harness.run()
    finally:
        harness.close()
    actual = {key[1]: hashlib.sha256(json.dumps(value["rendered"], sort_keys=True,
                                              separators=(",", ":")).encode()).hexdigest()
              for key, value in harness.prepared.items()}
    assert actual == historical
