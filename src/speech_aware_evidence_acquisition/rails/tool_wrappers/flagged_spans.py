"""``saea-tool-flagged-spans-v1`` -- the flagged-span detector, both sources.

ONE tool over TWO unmodified detector bodies, because the repository already
treats them as one object with several sources (``core/flag_sources.py`` is
literally named for the plural):

* ``logprob`` -- ``core.replay_signals.flag_spans``: contiguous runs of
  low-scoring words from a per-token confidence signal;
* ``roster-band`` -- ``core.flag_sources.roster_band_flags``: the top
  non-overlapping roster-band near-misses for one slice's draft words.

Both return non-overlapping spans in ascending start order -- the contract
``reproduction.replay_loop``'s ACCEPT stage depends on -- so a caller can
switch source without changing how it splices. The dispatch below is a
lookup and nothing else: no argument is renamed, defaulted or reinterpreted
on the way through.

Fail-closed: an unknown source name refuses rather than silently picking one.
"""

from __future__ import annotations

from typing import Any

from ...core.flag_sources import roster_band_flags
from ...core.replay_signals import flag_spans

TOOL_ID = "saea-tool-flagged-spans-v1"

FLAG_SOURCE_LOGPROB = "logprob"
FLAG_SOURCE_ROSTER_BAND = "roster-band"

#: source name -> the UNMODIFIED repository function it dispatches to.
FLAG_SOURCES = {
    FLAG_SOURCE_LOGPROB: flag_spans,
    FLAG_SOURCE_ROSTER_BAND: roster_band_flags,
}

#: A manifest carries exactly ONE ``source_ref`` (the design note's field
#: list), and this tool dispatches to two bodies. The manifest pins
#: ``core.replay_signals:flag_spans`` -- the primitive the "non-overlapping,
#: ascending-start" span contract is defined by -- and the SECOND body is
#: pinned here, so no dispatched body is left unhashed.
#: ``scripts/checks/tool_catalog_check.py`` verifies every entry of this
#: mapping exactly as it verifies a manifest's own pin; the empty mapping is
#: the normal case and every other wrapper module omits it.
ADDITIONAL_PINNED_SOURCES = {
    "speech_aware_evidence_acquisition.core.flag_sources:roster_band_flags": (
        "925b0408748d0aa5f46b98a57a2634bbe80408e4a3657a9d333d1c44bf25d3c4"
    ),
}


def flagged_spans_tool(source: str, *args: Any, **kwargs: Any):
    """Dispatch to one pinned detector and return its result untouched.

    ``ToolResult.result`` is exactly what ``FLAG_SOURCES[source]`` returned:
    a ``list[tuple[int, int]]`` for ``logprob``, a ``list[RosterBandFlag]``
    for ``roster-band``.
    """

    from ..tools import ToolCatalogError, ToolResult

    body = FLAG_SOURCES.get(source)
    if body is None:
        raise ToolCatalogError(
            f"unknown flag source {source!r}; registered: {sorted(FLAG_SOURCES)}"
        )
    return ToolResult(tool_id=TOOL_ID, result=body(*args, **kwargs))
