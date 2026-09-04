"""``core.flight``: the one flight runtime every arm and carrier runs through
(C4c consolidation).

``FlightRuntime`` (``runtime.py``) is a seam-injectable, hash-bound harness
walking six ordered stages -- ``preflight -> preprocess -> serve ->
run_phases -> seal -> score`` -- each producing exactly one receipt
(``receipts.py``'s ``FlightReceipts``). ``FlightQueue`` (``queue.py``)
sequences many ``FlightRuntime`` instances, preferring same-serving-geometry
flights so the resident server restarts only on a genuine geometry change,
and overlaps official scoring with the next flight's generation.

No submodule here performs model/GPU/llama-server/embedding/network I/O
directly -- every such effect is reached only through a caller-injected seam
on ``FlightRuntime``; see that class's own module docstring.
"""

from __future__ import annotations

from .queue import FlightQueue, FlightQueueEntry, FlightQueueError
from .receipts import (
    FLIGHT_RECEIPTS_SCHEMA,
    FLIGHT_STAGES,
    FlightReceiptError,
    FlightReceipts,
)
from .runtime import (
    FlightRuntime,
    FlightRuntimeError,
    FlightServeGeometryMismatchError,
    FlightStageOrderError,
)

__all__ = [
    "FLIGHT_RECEIPTS_SCHEMA",
    "FLIGHT_STAGES",
    "FlightQueue",
    "FlightQueueEntry",
    "FlightQueueError",
    "FlightReceiptError",
    "FlightReceipts",
    "FlightRuntime",
    "FlightRuntimeError",
    "FlightServeGeometryMismatchError",
    "FlightStageOrderError",
]
