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

from typing import TYPE_CHECKING

if TYPE_CHECKING:
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

# PEP 562 lazy exports: ``from core.flight import FlightRuntime`` still works, but importing a light
# submodule (``core.flight.repin``, ``core.flight.cli --help``) no longer loads the whole runtime stack.
_LAZY = {
    "FLIGHT_RECEIPTS_SCHEMA": "receipts",
    "FLIGHT_STAGES": "receipts",
    "FlightReceiptError": "receipts",
    "FlightReceipts": "receipts",
    "FlightQueue": "queue",
    "FlightQueueEntry": "queue",
    "FlightQueueError": "queue",
    "FlightRuntime": "runtime",
    "FlightRuntimeError": "runtime",
    "FlightServeGeometryMismatchError": "runtime",
    "FlightStageOrderError": "runtime",
}


def __getattr__(name: str):
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    value = getattr(import_module(f".{module}", __name__), name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY))


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
