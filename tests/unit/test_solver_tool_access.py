"""Admit one explicit Solver lookup while preserving the default tool-free path."""
from copy import deepcopy
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import NativeRoleNodeSpec
from test_native_episode_config import config, program

TARGET = "saea-tool-knowledge-target-lookup-v1"
MODE = "bounded-slot-lookup-v1"


def solver_values():
    values = config()
    native = values["native_episode"]
    native.update(solver_tool_access=MODE, review_loop="off", tool_iteration_policy="reserve-final-report")
    native["roles"]["solver"]["max_iterations"] = 2
    for kind in ("reviewer", "planner"):
        native["roles"][kind]["max_iterations"] = 0
    values["knowledge_stores"] = {"slot-contracts": {"release": "caller-pinned"}}
    values["phase_tools"] = {"solver": {
        "mode": "native-tools", "source_authority_role": "solver", "allowed_tools": [TARGET],
        "knowledge_views": ["text"], "knowledge_store_ids": ["slot-contracts"],
        "knowledge_target_axis": "slot-type", "knowledge_selection_mode": "targeted",
        "candidate_limit": 2, "knowledge_values_per_candidate": 1,
        "knowledge_value_limit": 2, "max_calls_per_sample": 1,
    }}
    return values


def test_solver_opt_in_counts_the_final_response_and_preserves_tool_contract():
    values = solver_values()
    before = deepcopy(values)
    parsed = load_native_episode_config(values, program(ceiling=3))
    assert values == before
    assert parsed.solver_tool_access == MODE
    assert parsed.role("solver").tool_names == (TARGET,)
    assert parsed.max_contacts == 3 and parsed.reserve_final_report
    assert not parsed.review_loop_enabled


@pytest.mark.parametrize("change", [
    lambda v: v["native_episode"].pop("solver_tool_access"),
    lambda v: v["native_episode"].update(solver_tool_access=None),
    lambda v: v["native_episode"].update(solver_tool_access=True),
    lambda v: v["native_episode"].update(solver_tool_access="on"),
    lambda v: v["native_episode"].pop("tool_iteration_policy"),
    lambda v: v["native_episode"]["roles"]["solver"].update(max_iterations=1),
    lambda v: v["native_episode"]["roles"]["solver"].update(max_iterations=3),
    lambda v: v["native_episode"]["roles"]["solver"].update(samples=2),
    lambda v: v["native_episode"]["roles"]["reviewer"].update(max_iterations=1),
    lambda v: v["native_episode"].update(max_revisions=1),
    lambda v: v["native_episode"].update(tool_schema_rendering="constant"),
    lambda v: v["phase_tools"].pop("solver"),
    lambda v: v["phase_tools"].update(perception=deepcopy(v["phase_tools"]["solver"])),
    lambda v: v["phase_tools"].update(planner=deepcopy(v["phase_tools"]["solver"])),
    lambda v: v["phase_tools"]["solver"].update(allowed_tools=[TARGET, "saea-tool-task-contract-v1"]),
    lambda v: v["phase_tools"]["solver"].update(source_authority_role="planner"),
    lambda v: v["phase_tools"]["solver"].update(knowledge_store_ids=["intent-boundaries"]),
    lambda v: v["phase_tools"]["solver"].update(knowledge_target_axis="task"),
    lambda v: v["phase_tools"]["solver"].update(knowledge_selection_mode="reread"),
    lambda v: v["phase_tools"]["solver"].update(candidate_limit=3),
    lambda v: v["phase_tools"]["solver"].update(knowledge_value_limit=3),
    lambda v: v["phase_tools"]["solver"].update(knowledge_values_per_candidate=2),
    lambda v: v["phase_tools"]["solver"].pop("max_calls_per_sample"),
    lambda v: v["phase_tools"]["solver"].update(max_calls_per_sample=True),
    lambda v: v["phase_tools"]["solver"].update(max_calls_per_sample=2),
    lambda v: v.pop("knowledge_stores"),
])
def test_solver_access_fails_closed_before_contact(change):
    values = solver_values()
    change(values)
    with pytest.raises(ValueError):
        load_native_episode_config(values, program(ceiling=3))


def test_default_solver_permissions_and_config_are_unchanged():
    parsed = load_native_episode_config(config(), program())
    assert parsed.solver_tool_access is None
    assert parsed.role("solver").tool_names == ()
    with pytest.raises(ValueError, match="tool-free"):
        NativeRoleNodeSpec("solver", "solver", "Answer the task.", 2, (TARGET,))


def test_framework_solver_requires_explicit_bounded_mode_and_final_report_reserve():
    spec = NativeRoleNodeSpec("solver", "solver", "Answer using fixed evidence when needed.", 2,
                              (TARGET,), True, solver_tool_access=MODE)
    for change in ({"reserve_final_report": False}, {"ability_names": ("other",)},
                   {"max_iterations": 3}, {"solver_tool_access": "on"}, {"role_kind": "perception"}):
        with pytest.raises(ValueError):
            replace(spec, **change)
