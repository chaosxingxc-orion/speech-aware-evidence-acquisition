"""``saea-tool-sealed-vector-query-v1`` -- speech-keyed retrieval material.

Wraps ``rails.phase_supply.load_sealed_vectors`` unchanged: the receipt-pinned
JSONL of query and facet vectors a supplied phase ranks the frozen knowledge
snapshot against. Fail-closed on a missing file, a sha256 that is not the
configured one, a malformed line, a duplicate id, an undeclared dimension, a
non-numeric or empty vector, or two vectors of different length in one
dimension.

Why the SEALED file and not a live embedder: an in-flight embedding contact
needs its own serving geometry, its own ExecutionPlan tool-contact clause and
one exposure row per contact, none of which this seam owns
(``rails.phase_supply``'s own refusal of the ``embedding-server`` kind). The
signal is embedded BEFORE the flight and pinned by hash, which is also what
keeps the owner's 2026-09-06 rule checkable -- a QUERY vector must carry
speech, and the fragment DECLARES that in ``embedded_signal``.

Ledger row type ``tool-contact``: the vectors this returns are the product of
a pinned local encoder run, whose own exposure row a user of them must cite.
The read itself is plain CPU.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..phase_supply import load_sealed_vectors

TOOL_ID = "saea-tool-sealed-vector-query-v1"

LEDGER_ROW_TYPE = "tool-contact"


def load_sealed_vectors_tool(
    path: Path, *, expected_sha256: str, dimensions: Sequence[str]
):
    """``load_sealed_vectors(...)`` verbatim; ``ToolResult.result`` is its own
    ``{id: {dimension: vector}}`` mapping, same floats, same tuples."""

    from ..tools import ToolResult

    return ToolResult(
        tool_id=TOOL_ID,
        result=load_sealed_vectors(
            path, expected_sha256=expected_sha256, dimensions=dimensions
        ),
    )
