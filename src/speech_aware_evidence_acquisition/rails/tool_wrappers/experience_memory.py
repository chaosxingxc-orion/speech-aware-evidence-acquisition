"""Native corrective-memory selection behind the configured action bridge."""

from __future__ import annotations


def select_corrective_memory(memory_binding, next_phase, context):
    """Return deterministic procedural guidance for the successor phase."""
    from ..experience_memory_runtime import CORRECTIVE_MEMORY_TOOL
    from ..tools import ToolResult

    return ToolResult(
        tool_id=CORRECTIVE_MEMORY_TOOL,
        result=memory_binding.select(next_phase=next_phase, context=context),
    )
