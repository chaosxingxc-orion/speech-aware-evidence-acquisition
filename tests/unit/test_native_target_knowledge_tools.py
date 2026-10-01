"""On-demand named target knowledge reaches actual native role requests."""

from dataclasses import replace
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.core_client import _tool_schemas_sha256
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.phase_tools import (
    PhaseToolError,
    build_phase_tools,
    load_phase_tool_specs,
)
import test_knowledge_stores as store_fixtures
from test_phase_native_tools import Custody, NativeRoleProgram, call, staged_native

TARGET = "saea-tool-knowledge-target-lookup-v1"


def _binding(tmp_path, monkeypatch):
    original = store_fixtures._store_snapshot

    def snapshot(store_id):
        base = original(store_id)
        template = base.values[0]
        return replace(
            base,
            values=tuple(
                replace(
                    template,
                    value_id=f"value:{target}",
                    task_target=target,
                    content=f"{store_id}: distinguish {target} using its explicit evidence.",
                )
                for target in ("alpha", "beta")
            ),
        ).validate()

    monkeypatch.setattr(store_fixtures, "_store_snapshot", snapshot)
    config, _ = store_fixtures._config(
        tmp_path, ("tool-activation", "parameter-meaning")
    )
    return load_knowledge_store_binding(config, data_root=tmp_path)


def _config(role="reviewer"):
    return {
        "phase_tools": {
            role: {
                "mode": "native-tools",
                "source_authority_role": role,
                "allowed_tools": [TARGET],
                "knowledge_views": ["text"],
                "knowledge_store_ids": ["tool-activation", "parameter-meaning"],
                "candidate_limit": 4,
                "knowledge_values_per_candidate": 1,
                "knowledge_value_limit": 4,
            }
        }
    }


def _args(store="tool-activation", ids=("alpha", "beta")):
    return {
        "store_id": store,
        "view": "text",
        "candidate_ids": list(ids),
        "distinction": "Distinguish the requested operation from the competing action.",
    }


def _dispatcher(binding, *, role="reviewer", custody=None, program=None):
    return build_phase_tools(
        _config(role),
        program or NativeRoleProgram(),
        snapshot=binding.composite_snapshot,
        knowledge_stores=binding,
        tool_contact=custody or Custody(),
    )


def _context(
    tool, binding, args, *, role="reviewer", serial=1, query=None, prior_states=()
):
    calls = call(TARGET, args)
    calls[0]["id"] = f"target-{serial}"
    context = staged_native(
        calls, phase=role, query_state=query, prior_states=prior_states
    )
    context.knowledge_snapshot_sha256 = binding.binding_sha256
    context.agent_states = (
        *context.agent_states[:-1],
        replace(
            context.agent_states[-1],
            producer_policy_id=tool.program.program_id,
            state_id=f"{role}:request-{serial}:{context.sample_id}",
        ),
    )
    old = context.core_completions[0]
    wire = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": old.text,
                        "tool_calls": calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        separators=(",", ":"),
    ).encode()
    completion = replace(
        old,
        request_id=f"request-{role}-{serial}",
        agent_contact_id=f"{tool.program.program_id}:{role}:0:{context.sample_id}",
        wire_response_bytes=wire,
        tool_names=(TARGET,),
        tool_calls_json=json.dumps(
            calls, sort_keys=True, separators=(",", ":")
        ).encode(),
        tool_schemas_sha256=_tool_schemas_sha256(tool.native_tool_schemas()),
    )
    context.core_completions = (completion,)
    return context


def test_target_tool_schema_requires_named_problem_and_bounded_candidates(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path, monkeypatch)
    tool = _dispatcher(binding)
    params = tool.native_tool_schemas()[0]["function"]["parameters"]
    assert set(params["required"]) == set(_args())
    assert params["properties"]["candidate_ids"]["maxItems"] == 4
    assert (
        params["properties"]["store_id"]["enum"]
        == _config()["phase_tools"]["reviewer"]["knowledge_store_ids"]
    )
    assert params["additionalProperties"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("knowledge_store_ids", None),
        ("candidate_limit", 0),
        ("knowledge_values_per_candidate", True),
        ("knowledge_value_limit", 33),
        ("knowledge_views", ["speech"]),
        ("mode", "fixed"),
    ],
)
def test_target_tool_refuses_unbound_or_invalid_configuration(field, value):
    config = _config()
    if value is None:
        del config["phase_tools"]["reviewer"][field]
    else:
        config["phase_tools"]["reviewer"][field] = value
    with pytest.raises(PhaseToolError):
        load_phase_tool_specs(config, NativeRoleProgram())


def test_target_query_acquires_exact_store_values_and_keeps_source_receipt(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path, monkeypatch)
    custody = Custody()
    tool = _dispatcher(binding, custody=custody)
    context = _context(tool, binding, _args())
    step = tool("reviewer", "reviewer", context)
    assert step.supply.fusion_decision.selected_value_ids == (
        "tool-activation::value:alpha",
        "tool-activation::value:beta",
    )
    document = json.loads(step.state.content)
    assert document["result"]["store_id"] == "tool-activation"
    assert document["result"]["supply_disposition"] == "acquired"
    assert len(document["native_result_content"]) == 2
    assert all(
        "tool-activation:" in b["text"] for b in document["native_result_content"]
    )
    assert "parameter-meaning:" not in json.dumps(document["native_result_content"])
    assert len(custody.calls) == 1
    assert custody.calls[0]["arguments"]["distinction"] == _args()["distinction"]
    assert document["source_authority"]["role_id"] == "reviewer"
    assert (
        step.supply.rank_result.query_state_sha256 == context.query_state.content_hash()
    )


def test_partial_overlap_and_repeated_lookup_do_not_resupply_visible_values(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path, monkeypatch)
    tool = _dispatcher(binding)
    first_context = _context(tool, binding, _args(ids=("alpha",)))
    first = tool("reviewer", "reviewer", first_context)
    query = replace(
        first_context.query_state,
        retrieved_value_ids=first.state.cited_value_ids,
        agent_state_ids=(first.state.state_id,),
    )
    second_context = _context(
        tool, binding, _args(), serial=2, query=query, prior_states=(first.state,)
    )
    second = tool("reviewer", "reviewer", second_context)
    assert second.supply.fusion_decision.selected_value_ids == (
        "tool-activation::value:beta",
    )
    assert second.state.cited_value_ids == (
        "tool-activation::value:alpha",
        "tool-activation::value:beta",
    )
    query = replace(
        query,
        retrieved_value_ids=second.state.cited_value_ids,
        agent_state_ids=(first.state.state_id, second.state.state_id),
    )
    third_context = _context(
        tool,
        binding,
        _args(),
        serial=3,
        query=query,
        prior_states=(first.state, second.state),
    )
    third = tool("reviewer", "reviewer", third_context)
    assert third.supply is None
    assert (
        json.loads(third.state.content)["result"]["supply_disposition"]
        == "already-visible"
    )
    assert len(json.loads(third.state.content)["native_result_content"]) == 2
    assert tool.receipt()["completed"] == 3


def test_missing_target_returns_explicit_gap_without_guessing(tmp_path, monkeypatch):
    binding = _binding(tmp_path, monkeypatch)
    tool = _dispatcher(binding)
    context = _context(tool, binding, _args(ids=("not-in-source",)))
    step = tool("reviewer", "reviewer", context)
    doc = json.loads(step.state.content)
    assert step.supply is None and step.state.cited_value_ids == ()
    assert doc["result"]["missing_candidate_ids"] == ["not-in-source"]
    assert doc["result"]["supply_disposition"] == "no-mapping"
    assert doc["native_result_content"] == []


def test_undeclared_store_is_rejected_before_lookup(tmp_path, monkeypatch):
    binding = _binding(tmp_path, monkeypatch)
    custody = Custody()
    tool = _dispatcher(binding, custody=custody)
    context = _context(tool, binding, _args(store="private-store"))
    with pytest.raises(PhaseToolError):
        tool("reviewer", "reviewer", context)
    assert custody.calls == []


def test_native_planner_can_use_tools_when_it_is_the_last_graph_phase(
    tmp_path, monkeypatch
):
    binding = _binding(tmp_path, monkeypatch)
    program = SimpleNamespace(
        program_id="actual-role-order",
        stop_rule="native-role-episode",
        phase_names=lambda: ("perception", "solver", "reviewer", "planner"),
    )
    tool = _dispatcher(binding, role="planner", program=program)
    assert tool.is_native_phase("planner")
    assert tool.native_tool_schemas()[0]["function"]["name"] == TARGET
    context = _context(tool, binding, _args(), role="planner")
    step = tool("planner", "planner", context)
    assert json.loads(step.state.content)["source_authority"]["role_id"] == "planner"


@pytest.mark.usefixtures("_spawn_live_matching_process")
@pytest.mark.parametrize("role", ("reviewer", "planner"))
@pytest.mark.parametrize("store", ("tool-activation", "parameter-meaning"))
def test_real_native_graph_returns_target_evidence_to_calling_role_and_solver(
    tmp_path,
    monkeypatch,
    role,
    store,
):
    import test_native_episode_runner as episode_runner

    binding = _binding(tmp_path / "stores", monkeypatch)
    builder = episode_runner.build_phase_tools

    def target_tools(config, *args, **kwargs):
        config = {**config, **_config(role)}
        return builder(config, *args, **kwargs, knowledge_stores=binding)

    monkeypatch.setattr(
        episode_runner, "_knowledge_snapshot", lambda: binding.composite_snapshot
    )
    monkeypatch.setattr(episode_runner, "TASK_CONTRACT_TOOL", TARGET)
    monkeypatch.setattr(episode_runner, "build_phase_tools", target_tools)

    def wire(tool_id):
        return json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Check the competing operation.",
                            "tool_calls": call(tool_id, _args(store=store)),
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }
        ).encode()

    monkeypatch.setattr(episode_runner, "_wire_tool_call", wire)
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path / "episode",
        sample_count=2,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
        analytical_tool_role=role,
    )
    shared_run = episode_runner.run_speech_native_agent_loop

    def run_with_named_store_renderer(**kwargs):
        # Match the shared phase_runner wiring used by FlightRuntime.
        return shared_run(
            **kwargs, knowledge_value_renderer=harness.tools_for_phase.render_values
        )

    monkeypatch.setattr(
        episode_runner, "run_speech_native_agent_loop", run_with_named_store_renderer
    )
    try:
        summary = harness.run()
    finally:
        closed = harness.close()
    assert closed["request_count"] == 16
    assert closed["cost"]["tool_calls"] == 2
    for row in summary.results:
        assert row.final_response_text == f"solver-answer:{row.sample_id}:visit:2"
        for key in ((row.sample_id, role, 1, 2), (row.sample_id, "solver", 2, 1)):
            messages = harness.prepared[key]["rendered"]["messages"]
            tool_messages = [m for m in messages if m["role"] == "tool"]
            assert len(tool_messages) == 1
            body = json.loads(tool_messages[0]["content"])
            assert body["result"]["store_id"] == store
            assert len(body["evidence"]) == 2
            assert all("distinguish" in block["content"] for block in body["evidence"])
    assert len(harness.tool_contacts) == 2


from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401


def test_target_tool_is_opt_in_and_only_offered_to_analytical_roles():
    from speech_aware_evidence_acquisition.rails.tools import (
        REPO_ROOT,
        TASK_TYPES,
        TOOLKIT_ROLES,
        default_toolkit_table,
        load_toolkit_table,
    )

    table = load_toolkit_table(
        REPO_ROOT / "configs/toolkit/task-toolkits-v4-target-knowledge-v1.json"
    )
    default = default_toolkit_table()
    for task in TASK_TYPES:
        assert table.for_task(task).may_call("reviewer", TARGET)
        assert table.for_task(task).may_call("planner", TARGET)
        assert not table.for_task(task).may_call("observer", TARGET)
        assert all(
            not default.for_task(task).may_call(role, TARGET) for role in TOOLKIT_ROLES
        )


def test_episode_tool_limit_refuses_second_call_before_custody(tmp_path, monkeypatch):
    binding = _binding(tmp_path, monkeypatch)
    config = _config("planner")
    config["phase_tools"]["planner"]["max_calls_per_sample"] = 1
    custody = Custody()
    tool = build_phase_tools(config, NativeRoleProgram(), snapshot=binding.composite_snapshot,
                            knowledge_stores=binding, tool_contact=custody)
    first = tool("planner", "planner", _context(tool, binding, _args(), role="planner"))
    assert first.state.cited_value_ids
    second = tool("planner", "planner", _context(tool, binding, _args(), role="planner", serial=2))
    assert second.supply is None
    assert "limit" in second.state.content
    assert len(custody.calls) == 1


@pytest.mark.parametrize("field,value", [("knowledge_target_axis", "made-up"),
    ("knowledge_selection_mode", "guess"), ("max_calls_per_sample", True),
    ("max_calls_per_sample", 0)])
def test_invalid_lookup_settings_are_refused(field, value):
    config = _config("planner")
    config["phase_tools"]["planner"][field] = value
    with pytest.raises(PhaseToolError):
        load_phase_tool_specs(config, NativeRoleProgram())


@pytest.mark.usefixtures("_spawn_live_matching_process")
def test_normalized_reviewer_state_reaches_planner_and_revised_solver(tmp_path, monkeypatch):
    import test_native_episode_runner as episode_runner
    harness = episode_runner._ActualEpisodeHarness(tmp_path, sample_count=1,
        max_revisions=1, max_contacts=7, planner_actions=("REVISE", "ACCEPT"))
    harness.config = replace(harness.config, review_handoff="slot-issues-v1")
    output = harness._output
    def with_review(key):
        if key[1] == "reviewer":
            return json.dumps({"findings": [{"kind": "boundary", "slot_types": ["event_time"],
                "draft_fragment": "tomorrow", "reason": "Check extraction scope."}], "checked": []})
        return output(key)
    monkeypatch.setattr(harness, "_output", with_review)
    try:
        summary = harness.run()
    finally:
        harness.close()
    row = summary.results[0]
    assert row.final_response_text == f"solver-answer:{row.sample_id}:visit:2"
    for key in ((row.sample_id, "planner", 1, 1), (row.sample_id, "solver", 2, 1)):
        rendered = json.dumps(harness.prepared[key]["rendered"])
        assert "saea-slot-review-handoff-v1" in rendered
        assert "model-criticism" in rendered
