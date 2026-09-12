"""``AttemptError`` + id/numeric validation helpers shared by handle.py/store.py.

Split out of the former monolithic ``core/attempts.py`` (R0 repair refactor
stage 2, pure move, no behaviour change). See ``core/attempts/__init__.py``
for the full module docstring this package shares.
"""

from __future__ import annotations

import math

# IMPORTANT 3 fix-wave3 (external-threat-model review round 3): imported,
# never re-copied -- the SAME pattern core.tracing and core.session use for a
# run/attempt/session id (both are embedded verbatim into a filesystem path:
# a directory name and a file stem respectively, so both are restricted
# identically -- no empty string, no path separator, no leading dot/dash that
# a shell or a naive joiner could misparse) and, as of this fix, the SAME
# pattern ``contracts.ExecutionPlan.validate`` itself now enforces on
# run_id/attempt_id at plan-construction time. contracts.py sits at the
# bottom of this package's import graph (stdlib-only, imports nothing from
# core/ at module level -- see contracts.py's own top-of-file NOTE), so
# importing FROM it here introduces no cycle: the only cycle contracts.py
# avoids is the reverse direction (importing core.attempts at ITS module
# level), which stays a lazy, function-local import there, unchanged.
from ...contracts import RUN_ID_PATTERN as _ID_PATTERN


class AttemptError(RuntimeError):
    """An attempt reservation, usage record, or lookup was refused.

    Covers: a malformed run/attempt id, a duplicate open of an already-
    reserved (run_id, attempt_id) key, a usage record against an attempt
    that is not OPENED, or an unreadable/malformed persisted attempt file.
    """


def validate_id(value: object, label: str) -> str:
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise AttemptError(
            f"{label} must be a non-empty string matching {_ID_PATTERN.pattern!r}, "
            f"got {value!r}"
        )
    return value


def _positive_finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise AttemptError(f"{label} must be a finite positive number, got {value!r}")
    return float(value)


def _non_negative_finite(value: object, label: str) -> float:
    """Like :func:`_positive_finite` but allows ``0.0`` (fix-wave2 Minor: a
    genuinely idle GPU for an entire run legitimately measures 0.0
    gpu_seconds -- that is not the same failure as a missing/non-finite/
    negative measurement)."""

    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise AttemptError(f"{label} must be a finite non-negative number, got {value!r}")
    return float(value)


def _zero_finite(value: object, label: str) -> float:
    """Require a real numeric zero for a contact with no speech carrier."""

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value != 0
    ):
        raise AttemptError(f"{label} must be exactly zero, got {value!r}")
    return 0.0


def _coerce_actual_field(value: object, kind: type, label: str):
    """MINOR fix-wave3 (external-threat-model review round 3): coerce a
    PERSISTED (already-written, therefore untrusted-on-re-read) attempt
    file's ``actual.*`` field to ``kind`` (``int`` or ``float``), wrapped
    fail-closed as :class:`AttemptError` -- never a bare ``ValueError``/
    ``TypeError`` escaping this module's own documented exception contract
    -- and refuses a negative or non-finite result, which would otherwise
    silently deflate :meth:`AttemptStore._sum_actual_for_run`'s summed
    actual-usage total (read back by :meth:`prior_actual_usage`/
    :meth:`all_actual_usage` for this module's own accounting correctness,
    independent of whatever a caller does with the figure).
    ``bool`` is rejected even though it is technically ``int`` (matching
    every other numeric guard in this module, e.g. :func:`_positive_finite`)."""

    if isinstance(value, bool):
        raise AttemptError(f"{label} must be a {kind.__name__}, got bool {value!r}")
    try:
        coerced = kind(value)
    except (TypeError, ValueError) as error:
        raise AttemptError(f"{label} must be a {kind.__name__}, got {value!r}: {error}") from error
    if not math.isfinite(coerced) or coerced < 0:
        raise AttemptError(f"{label} must be a finite non-negative number, got {value!r}")
    return coerced
