"""``saea-tool-speaker-turn-units-v2`` -- the OBS-E1 unit planner, as a tool.

Wraps ``analysis.e21_speaker_turn_units.plan_units_v2`` unchanged: the v2
plan (coordinator's decision, 2026-09-08) that turns a call's diarization
segments plus its pause/activity structure into a TILING of speaker-turn
units, proved by the module's own ``assert_tiles``.

Carrier-scoped: the plan is defined against the Earnings-21 discovery calls
and their sealed slice activity, so the manifest names ``carrier:earnings21``
rather than claiming generality it has not earned.
"""

from __future__ import annotations

from typing import Sequence

from ...analysis.e21_speaker_turn_units import (
    MAX_UNIT_SECONDS,
    MIN_UNIT_SECONDS,
    SNAP_RADIUS_SECONDS,
    Pause,
    plan_units_v2,
)
from ...reproduction.diarization import SpeakerSegment

TOOL_ID = "saea-tool-speaker-turn-units-v2"


def plan_units_v2_tool(
    sample_id: str,
    segments: Sequence[SpeakerSegment],
    duration_seconds: float,
    pauses: Sequence[Pause],
    active,
    frame_seconds: float,
    *,
    max_seconds: float = MAX_UNIT_SECONDS,
    min_seconds: float = MIN_UNIT_SECONDS,
    snap_radius: float = SNAP_RADIUS_SECONDS,
):
    """``plan_units_v2(...)`` verbatim; ``ToolResult.result`` is its own
    ``tuple[UnitV2, ...]``, same objects, same order."""

    from ..tools import ToolResult

    return ToolResult(
        tool_id=TOOL_ID,
        result=plan_units_v2(
            sample_id,
            segments,
            duration_seconds,
            pauses,
            active,
            frame_seconds,
            max_seconds=max_seconds,
            min_seconds=min_seconds,
            snap_radius=snap_radius,
        ),
    )
