"""Shared error type every rails module raises for a malformed value or a
runner/task-adapter contract violation.

One exception type across the whole ``rails`` package (mirroring
``core.base.CoreError``/``core.model.FrozenCoreError``'s own "one error type
per seam" discipline) so a caller catching rails failures never has to know
which submodule raised.
"""

from __future__ import annotations


class RailsError(RuntimeError):
    """A rails packet is malformed, or a runner/task-adapter contract was violated."""
