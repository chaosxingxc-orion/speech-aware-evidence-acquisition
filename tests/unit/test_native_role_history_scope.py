"""Role context scopes preserve speech custody and actual local tool history."""
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRole, load_native_episode_config, select_native_role_history,
)
from test_native_episode_config import config, program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

SCOPE = "latest-solver-and-local-tools"


def state(name, kind, content="content"):
    return SimpleNamespace(state_id=name, state_kind=kind, content=content)


def project(states, *, local=(), role=None):
    role = role or NativeEpisodeRole("reviewer", "reviewer", 3, ("tool",), SCOPE)
    return select_native_role_history(
        role=role, solver_phase_id="solver", states=states,
        local_tool_result_ids=local,
    )


def test_default_returns_the_same_complete_ordered_states():
    states = (state("p", "phase:perception"), state("s", "phase:solver"))
    role = NativeEpisodeRole("reviewer", "reviewer", 1, ())
    assert role.history_scope == "full"
    assert project(states, role=role) is states


def test_scope_retains_latest_solver_and_exact_local_call_result_pairs():
    states = (
        state("p", "phase:perception"), state("s1", "phase:solver"),
        state("old-review", "phase:reviewer"),
        state("old-tool", "tool-result", json.dumps({"native_source_state_id": "old-review"})),
        state("planner", "phase:planner"), state("s2", "phase:solver"),
        state("call1", "phase:reviewer"),
        state("result1", "tool-result", json.dumps({"native_source_state_id": "call1"})),
        state("call2", "phase:reviewer"),
        state("result2", "tool-result", json.dumps({"native_source_state_id": "call2"})),
    )
    actual = project(states, local=("result1", "result2"))
    assert actual == (states[5], *states[6:])
    assert all(x is y for x, y in zip(actual, (states[5], *states[6:])))
    assert project(states) == (states[5],)


@pytest.mark.parametrize("change", [
    "missing_solver", "missing_result", "wrong_kind", "invalid_json",
    "missing_source", "foreign_source", "prior_visit", "reversed", "duplicate",
])
def test_invalid_local_history_is_rejected(change):
    states = [
        state("s", "phase:solver"), state("call", "phase:reviewer"),
        state("result", "tool-result", json.dumps({"native_source_state_id": "call"})),
    ]
    local = ("result",)
    if change == "missing_solver":
        states = states[1:]
    elif change == "missing_result":
        local = ("absent",)
    elif change == "wrong_kind":
        states[2].state_kind = "phase:reviewer"
    elif change == "invalid_json":
        states[2].content = "not-json"
    elif change == "missing_source":
        states[2].content = "{}"
    elif change == "foreign_source":
        states[1].state_kind = "phase:planner"
    elif change == "prior_visit":
        states = [states[1], states[2], states[0]]
    elif change == "reversed":
        states = [states[0], states[2], states[1]]
    elif change == "duplicate":
        local = ("result", "result")
    with pytest.raises(ValueError):
        project(tuple(states), local=local)


def test_config_accepts_only_the_explicit_reviewer_scope():
    values = config()
    values["native_episode"]["roles"]["reviewer"]["history_scope"] = SCOPE
    parsed = load_native_episode_config(values, program())
    assert parsed.role("reviewer").history_scope == SCOPE
    assert all(parsed.role(role).history_scope == "full" for role in ("perception", "solver", "planner"))


@pytest.mark.parametrize("scope", [None, True, 1, {}, "unknown"])
def test_unknown_scope_is_rejected(scope):
    values = config()
    values["native_episode"]["roles"]["reviewer"]["history_scope"] = scope
    with pytest.raises(ValueError, match="history"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("role", ["perception", "solver", "planner"])
def test_other_roles_cannot_opt_into_the_review_scope(role):
    values = config()
    values["native_episode"]["roles"][role]["history_scope"] = SCOPE
    with pytest.raises(ValueError, match="Reviewer"):
        load_native_episode_config(values, program())


@pytest.mark.parametrize("two_tools", [False, True])
def test_actual_scoped_reviewer_preserves_fitted_local_tool_sequence(tmp_path, monkeypatch, two_tools):
    import test_native_episode_runner as episode_tests
    from test_native_episode_runner import _ActualEpisodeHarness

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=11 if two_tools else 9,
        planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=True,
    )
    harness.config = replace(
        harness.config,
        roles=tuple(replace(role, history_scope=SCOPE) if role.role_kind == "reviewer" else role
                    for role in harness.config.roles),
    )
    if two_tools:
        harness.config = replace(
            harness.config, reserve_final_report=True,
            roles=tuple(replace(role, max_iterations=3) if role.role_kind == "reviewer" else role
                        for role in harness.config.roles),
        )
        original_wire = episode_tests._wire_tool_call
        counter = 0

        def unique_call(tool_id):
            nonlocal counter
            counter += 1
            result = json.loads(original_wire(tool_id))
            result["choices"][0]["message"]["tool_calls"][0]["id"] = f"scoped-call-{counter}"
            return json.dumps(result).encode()

        monkeypatch.setattr(episode_tests, "_wire_tool_call", unique_call)
        original_output = harness._output

        def output(key):
            if key[1] == "reviewer":
                return None if key[3] < 3 else f"reviewer-analysis:s1:visit:{key[2]}"
            return original_output(key)

        harness._output = output
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert summary.results[0].final_response_text == "solver-answer:s1:visit:2"
    assert closed["request_count"] == (11 if two_tools else 8)
    assert len(harness.tool_contacts) == (4 if two_tools else 1)
    turns = [(visit, turn) for visit in (1, 2) for turn in (1, 2, 3)] if two_tools else [(1, 1), (1, 2), (2, 1)]
    for visit, turn in turns:
        key = ("s1", "reviewer", visit, turn)
        actual = harness.prepared[key]
        body = actual["rendered"]
        text = json.dumps(body)
        assert f"solver-answer:s1:visit:{visit}" in text
        assert "perception-analysis:s1:" not in text
        if visit == 2:
            assert "solver-answer:s1:visit:1" not in text
            assert "reviewer-analysis:s1:visit:1" not in text
        expected_tools = turn - 1 if two_tools else int(visit == 1 and turn == 2)
        assert sum(message["role"] == "tool" for message in body["messages"]) == expected_tools
        assert text.count('"type": "input_speech_features"') == 1
        assert harness.events.index(("fit", key)) < harness.events.index(("dispatch", key))
    # Full episode custody and unscoped roles keep their original prior history.
    result = summary.results[0]
    assert len(result.native_episode_receipt["role_visits"]) == 7
    revised_solver = json.dumps(harness.prepared[("s1", "solver", 2, 1)]["rendered"])
    assert "solver-answer:s1:visit:1" in revised_solver
    assert ("scoped-call-1" if two_tools else "call-task-contract-1") in revised_solver


def test_local_pair_list_cannot_reorder_results_or_reuse_one_source():
    states = (
        state("s", "phase:solver"), state("c1", "phase:reviewer"),
        state("r1", "tool-result", json.dumps({"native_source_state_id": "c1"})),
        state("c2", "phase:reviewer"),
        state("r2", "tool-result", json.dumps({"native_source_state_id": "c2"})),
    )
    with pytest.raises(ValueError, match="order"):
        project(states, local=("r2", "r1"))
    states[-1].content = json.dumps({"native_source_state_id": "c1"})
    with pytest.raises(ValueError, match="repeated"):
        project(states, local=("r1", "r2"))


def test_interleaved_call_result_pairs_are_rejected_before_rendering():
    states = (
        state("s", "phase:solver"), state("c1", "phase:reviewer"),
        state("c2", "phase:reviewer"),
        state("r1", "tool-result", json.dumps({"native_source_state_id": "c1"})),
        state("r2", "tool-result", json.dumps({"native_source_state_id": "c2"})),
    )
    with pytest.raises(ValueError):
        project(states, local=("r1", "r2"))


def test_duplicate_state_identity_and_nonsequence_local_ids_are_rejected():
    draft = state("s", "phase:solver")
    with pytest.raises(ValueError, match="duplicate"):
        project((draft, draft))
    with pytest.raises(ValueError, match="sequence"):
        project((draft,), local=None)
