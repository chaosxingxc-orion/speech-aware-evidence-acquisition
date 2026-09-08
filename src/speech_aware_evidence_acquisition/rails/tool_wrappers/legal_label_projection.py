"""``saea-tool-legal-label-projection-v2`` -- the SLURP legality judge.

Wraps ``reproduction.slurp_scoring.project_slu_label_v2`` unchanged: the
deterministic Reviewer-side judge that maps an ILLEGAL ``(scenario, action)``
pair onto the nearest legal one under ``slurp-legal-label-projection-v2``
(promote an action-named scenario to its owner, else fall through to v1).

A judge, not an answer: entities are not an argument and are never touched, an
unparsed response stays unparsed, and a row already naming a legal pair is
returned unchanged. The wrapped function takes its inventory as an argument
and imports no loader, so the tool stays a pure function of its inputs.
"""

from __future__ import annotations

from ...reproduction.slurp_scoring import LegalIntentInventory, project_slu_label_v2

TOOL_ID = "saea-tool-legal-label-projection-v2"


def project_slu_label_v2_tool(
    scenario: str | None,
    action: str | None,
    inventory: LegalIntentInventory,
    *,
    parsed: bool = True,
):
    """``project_slu_label_v2(...)`` verbatim; ``ToolResult.result`` is its
    own ``LabelProjection``, branch bookkeeping included."""

    from ..tools import ToolResult

    return ToolResult(
        tool_id=TOOL_ID,
        result=project_slu_label_v2(scenario, action, inventory, parsed=parsed),
    )
