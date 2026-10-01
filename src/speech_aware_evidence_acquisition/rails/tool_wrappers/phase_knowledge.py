"""Native primitives behind the explicit configured task-action bridge."""

from __future__ import annotations


def read_task_contract(context):
    """Return the current task's legal contract without reading a dataset row."""
    from ..tools import ToolResult

    return ToolResult(
        tool_id="saea-tool-task-contract-v1",
        result={"task_contract": context.task_contract},
    )


def retrieve_phase_knowledge(supply_for_phase, next_phase, context):
    """Execute the shared prepared knowledge provider for the successor state."""
    from ..tools import ToolResult

    return ToolResult(
        tool_id="saea-tool-phase-knowledge-v1",
        result=supply_for_phase(next_phase, context),
    )


def lookup_target_knowledge(
    snapshot, query_state, candidate_ids, *, max_values_per_candidate,
    max_total_values, already_visible_value_ids=(), target_index=None, selection_mode="targeted",
):
    """Select requested task-target values from an already bound frozen store."""
    from ..knowledge_target_lookup import lookup_knowledge_targets
    from ..tools import ToolResult

    return ToolResult(
        tool_id="saea-tool-knowledge-target-lookup-v1",
        result=lookup_knowledge_targets(
            snapshot, query_state, candidate_ids,
            max_values_per_candidate=max_values_per_candidate,
            max_total_values=max_total_values,
            already_visible_value_ids=already_visible_value_ids,
            target_index=target_index, selection_mode=selection_mode,
        ),
    )
