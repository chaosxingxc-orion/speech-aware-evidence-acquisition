"""``saea-tool-repair-alignment-v1`` -- the substitution-only delivery rule.

Wraps ``core.repair_alignment.accept_entity_repair`` unchanged: the
Reviewer-side rule that accepts a pass-2 response only when it differs from
its predecessor by SUBSTITUTIONS ONLY, within the span/anchor/fraction bounds,
and otherwise REFUSES by delivering the predecessor verbatim.

Never raises on model output -- a malformed, truncated, translated or
hallucinated response is a named refusal, not an exception -- so the tool is
safe to call on anything the core emits. ``RepairAlignmentError`` stays
reserved for a caller's bad parameters, which is a harness defect.
"""

from __future__ import annotations

from ...core.repair_alignment import (
    DEFAULT_MAX_SPAN_TOKENS,
    DEFAULT_MAX_SUBSTITUTED_FRACTION,
    DEFAULT_MIN_ANCHOR_RATIO,
    accept_entity_repair,
)

TOOL_ID = "saea-tool-repair-alignment-v1"


def accept_entity_repair_tool(
    predecessor_text: str,
    response_text: str,
    *,
    max_span_tokens: int = DEFAULT_MAX_SPAN_TOKENS,
    min_anchor_ratio: float = DEFAULT_MIN_ANCHOR_RATIO,
    max_substituted_fraction: float = DEFAULT_MAX_SUBSTITUTED_FRACTION,
):
    """``accept_entity_repair(...)`` verbatim; ``ToolResult.result`` is its
    own ``RepairOutcome``, substitutions and refusal reason included."""

    from ..tools import ToolResult

    return ToolResult(
        tool_id=TOOL_ID,
        result=accept_entity_repair(
            predecessor_text,
            response_text,
            max_span_tokens=max_span_tokens,
            min_anchor_ratio=min_anchor_ratio,
            max_substituted_fraction=max_substituted_fraction,
        ),
    )
