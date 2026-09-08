"""``saea-tool-diarization-artifact-v1`` -- read the pinned diarizer's output.

Wraps ``reproduction.diarization.load_diarization`` unchanged: the OBS
segmentation tool the design note names ("Sortformer diarization (pinned tool
row)") reaches this repository as a SEALED ``saea-diarization-v1`` artifact,
and this is the repository-side entry point to it.

The MODEL never runs here. The Sortformer pass is a separate, already-ledgered
batch contact (``scripts/e21_diarization_pass.py``); this wrapper only reads
and re-derives what that pass sealed, which is why the manifest's ledger row
type is ``tool-contact`` -- a reader of the artifact must cite the pinned tool
row that produced it -- while its cost class is plain ``cpu``. Nothing in this
module imports, spawns or otherwise reaches a diarizer runtime, and the unit
tests exercise only the DRY RUN and the sealed-artifact read, never a model.

:func:`load_diarization_tool` accepts ``dry_run=True`` so the Planner can
price the contact -- which artifact, which ledger row -- before committing to
the read, without touching the filesystem at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...reproduction.diarization import DIARIZATION_SCHEMA, load_diarization

TOOL_ID = "saea-tool-diarization-artifact-v1"

#: The ledger row a caller must cite when it USES what this tool returns.
LEDGER_ROW_TYPE = "tool-contact"


@dataclass(frozen=True)
class DiarizationReadPlan:
    """What a dry run reports: the read this tool WOULD perform.

    No filesystem access, no validation, no model -- the point of a dry run
    is that a Planner can read the plan when the artifact is not even there.
    """

    tool_id: str
    artifact_path: str
    schema: str
    ledger_row_type: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "artifact_path": self.artifact_path,
            "schema": self.schema,
            "ledger_row_type": self.ledger_row_type,
        }


def load_diarization_tool(path: Path | str, *, dry_run: bool = False):
    """Read and validate one sealed ``saea-diarization-v1`` artifact.

    ``dry_run=True`` returns a :class:`DiarizationReadPlan` instead and reads
    nothing. Otherwise the call is ``load_diarization(path)``, unchanged, and
    ``ToolResult.result`` is that function's ``DiarizationArtifact`` itself.
    """

    from ..tools import ToolResult

    if dry_run:
        return ToolResult(
            tool_id=TOOL_ID,
            result=DiarizationReadPlan(
                tool_id=TOOL_ID,
                artifact_path=str(path),
                schema=DIARIZATION_SCHEMA,
                ledger_row_type=LEDGER_ROW_TYPE,
            ),
        )
    return ToolResult(tool_id=TOOL_ID, result=load_diarization(path))
