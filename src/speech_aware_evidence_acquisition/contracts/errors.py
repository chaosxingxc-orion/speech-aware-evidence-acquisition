"""Exception types for the fail-closed E0 engineering contracts.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change): every exception class the contracts package
raises, in one place so every other submodule can import from here without
creating cross-submodule cycles.
"""

from __future__ import annotations


class BoundaryViolation(ValueError):
    """A payload tries to move gold/reference/test/future information across the runtime boundary."""


class TraceContractError(ValueError):
    """A trace record violates the OBS/SUPPLY separation or serializability contract."""


class ExposureSchemaError(ValueError):
    """An exposure claim does not carry the four required fields in the required shapes."""


class GateClosed(RuntimeError):
    """The frozen-core entry gate refuses: E0 closure or the runtime receipt is missing/invalid."""


class ExecutionScopeError(RuntimeError):
    """The requested execution profile is outside this study repository's Stage-2 authority."""
