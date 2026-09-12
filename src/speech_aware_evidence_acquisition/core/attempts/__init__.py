"""Durable, one-time attempt accounting (R0 repair T4, invariant I6).

The reproduced defect: the frozen-core entry gate has no nonce, attempt id or
state machine. The exact same ``ExecutionPlan`` (and the exact same
pre-registered exposure-ledger row) can open the gate twice with no error,
and two independent ``FrozenCoreAdapter`` instances each meter their own
in-process counters from zero -- a row registered for N calls can be re-spent
per process/attempt indefinitely, because nothing ever persists what was
*actually* sent anywhere outside process memory.

The fix moves attempt state OUTSIDE the repository and outside process
memory, into one file per attempt under
``<data_root>/attempts/<run_id>/<attempt_id>.json``. Two properties make that
file the actual one-time-consumption boundary rather than another piece of
advisory bookkeeping:

- **Atomic, exclusive creation.** ``AttemptStore.open_attempt`` creates the
  file with ``O_CREAT | O_EXCL``; a second attempt at the identical
  ``(run_id, attempt_id)`` key -- whether a genuine race, a duplicate retry,
  or a second live ``FrozenCoreAdapter`` over the same plan -- gets
  ``FileExistsError`` translated into a fail-closed :class:`AttemptError`.
  There is deliberately no "attach to an already-OPENED attempt" operation:
  two independent handles issuing read-modify-write usage updates against the
  same file could interleave and silently lose an increment (a classic
  lost-update race), so a second open is always refused outright rather than
  resumed. A genuine retry after a crash mints a **fresh** ``attempt_id``;
  the crashed attempt's already-persisted actual usage is never discarded --
  :func:`AttemptStore.prior_actual_usage` folds it into the budget every
  later attempt under the same ``run_id`` is checked against.
- **Usage persisted before the request leaves the process.** The caller
  (``FrozenCoreAdapter.request``) calls :meth:`AttemptHandle.record_usage`
  -- a synchronous, durable rewrite of the attempt file -- before invoking
  the transport. A process that crashes between that write and the transport
  call has still durably recorded the spend; nothing is under-reported as
  free just because the process never came back to report a response.

Standard-library only, no dependency on ``contracts.py`` or the rest of
``core/`` -- this module is a pure, filesystem-backed ledger that any caller
in either direction may use without introducing an import cycle.

R0 repair refactor stage 2 (behaviour-preserving): this used to be one
~530-line ``attempts.py`` module (stage 1 flattened everything else but left
this one alone). It is now this package (``constants.py`` for the schema/
state-machine strings, ``errors.py`` for ``AttemptError`` and its id/numeric
validation helpers, ``handle.py`` for ``AttemptHandle``, ``store.py`` for
``AttemptStore``) purely for file size -- every name below was already part
of this module's public surface and remains importable from exactly
``speech_aware_evidence_acquisition.core.attempts`` as before.

No monkeypatch-safety concern applies here (unlike ``core.session``'s or
``core.driver``'s own stage-1 splits, see their module docstrings): nothing
in this repository's test suite patches an attribute of the ``core.attempts``
module itself (only ``AttemptStore``'s own class attributes, e.g.
``monkeypatch.setattr(AttemptStore, "actual_usage_in_states", ...)`` in
``tests/unit/test_bundle.py`` -- which resolves through the one live
``AttemptStore`` class object regardless of which submodule defines it, so
ordinary direct imports between ``constants.py``/``errors.py``/``handle.py``/
``store.py`` below need no live-package-self-reference indirection).
"""

from __future__ import annotations

from .constants import (
    ATTEMPT_SCHEMA,
    CONTACT_KINDS,
    CONTACT_KIND_SPEECH,
    CONTACT_KIND_TEXT_ENCODER,
    STATE_ABORTED,
    STATE_FINALIZED,
    STATE_OPENED,
    STATE_RESERVED,
)
from .errors import (
    AttemptError,
    _coerce_actual_field,
    _non_negative_finite,
    _positive_finite,
    _zero_finite,
    validate_id,
)
from .handle import AttemptHandle
from .store import AttemptStore

__all__ = [
    "ATTEMPT_SCHEMA",
    "CONTACT_KINDS",
    "CONTACT_KIND_SPEECH",
    "CONTACT_KIND_TEXT_ENCODER",
    "STATE_ABORTED",
    "STATE_FINALIZED",
    "STATE_OPENED",
    "STATE_RESERVED",
    "AttemptError",
    "AttemptHandle",
    "AttemptStore",
    "validate_id",
    "_coerce_actual_field",
    "_non_negative_finite",
    "_positive_finite",
    "_zero_finite",
]
