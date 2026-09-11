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
