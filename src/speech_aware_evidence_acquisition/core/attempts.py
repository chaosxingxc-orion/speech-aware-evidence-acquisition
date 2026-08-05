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
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

ATTEMPT_SCHEMA = "saea-attempt-v1"

STATE_RESERVED = "RESERVED"
STATE_OPENED = "OPENED"
STATE_FINALIZED = "FINALIZED"
STATE_ABORTED = "ABORTED"

# The same safe-filename pattern core.tracing uses for a run id: both values
# are embedded verbatim into a filesystem path (a directory name and a file
# stem respectively), so both are restricted identically -- no empty string,
# no path separator, no leading dot/dash that a shell or a naive joiner could
# misparse.
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


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


@dataclass(frozen=True)
class AttemptHandle:
    """A live reference to one attempt's durable state file.

    The file, not any in-process field, is the source of truth: every
    mutation reads the current document, updates it, and rewrites the whole
    thing via a temp-file-plus-``os.replace`` (atomic on both POSIX and NTFS
    for a same-volume rename), so a concurrent reader never observes a
    half-written document.
    """

    path: Path
    run_id: str
    attempt_id: str

    def _read(self) -> dict:
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise AttemptError(f"cannot read attempt state {self.path}: {error}") from error
        if not isinstance(document, dict):
            raise AttemptError(f"attempt state {self.path} must be a JSON object")
        return document

    def _write(self, document: dict) -> None:
        tmp = self.path.with_name(f"{self.path.name}.tmp-{os.getpid()}-{time.monotonic_ns()}")
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2)
        try:
            tmp.write_text(raw, encoding="utf-8", newline="\n")
            os.replace(tmp, self.path)
        except OSError as error:
            try:
                tmp.unlink()
            except OSError:
                pass
            raise AttemptError(f"cannot persist attempt state {self.path}: {error}") from error

    def state(self) -> str:
        return str(self._read()["state"])

    def actual_totals(self) -> tuple[int, float]:
        actual = self._read()["actual"]
        return int(actual["calls"]), float(actual["audio_seconds"])

    def mark_opened(self) -> "AttemptHandle":
        document = self._read()
        if document.get("state") != STATE_RESERVED:
            raise AttemptError(
                f"attempt {self.run_id}/{self.attempt_id} is not RESERVED "
                f"(found {document.get('state')!r}); cannot transition to OPENED"
            )
        document["state"] = STATE_OPENED
        self._write(document)
        return self

    def mark_finalized(self) -> "AttemptHandle":
        """OPENED -> FINALIZED (R0 repair T6, invariant I7): the terminal,
        successful transition a ``core.bundle.finalize_bundle`` call makes only
        after the whole bundle (outputs/raw trace/trace manifest/scores) has
        re-verified. Refuses from any other state -- including a second call,
        which would otherwise silently no-op a double-finalize."""

        document = self._read()
        if document.get("state") != STATE_OPENED:
            raise AttemptError(
                f"attempt {self.run_id}/{self.attempt_id} is not OPENED "
                f"(found {document.get('state')!r}); cannot transition to FINALIZED"
            )
        document["state"] = STATE_FINALIZED
        self._write(document)
        return self

    def mark_aborted(self, reason: str) -> "AttemptHandle":
        """RESERVED/OPENED -> ABORTED (R0 repair T6, invariant I7): records why,
        so an aborted attempt still leaves an auditable trail rather than a
        silently dropped file. Refuses from FINALIZED/ABORTED -- a terminal
        state, once reached, is never overwritten by a later abort call."""

        if not isinstance(reason, str) or not reason.strip():
            raise AttemptError("mark_aborted reason must be a non-empty string")
        document = self._read()
        if document.get("state") not in (STATE_RESERVED, STATE_OPENED):
            raise AttemptError(
                f"attempt {self.run_id}/{self.attempt_id} is not RESERVED/OPENED "
                f"(found {document.get('state')!r}); cannot transition to ABORTED"
            )
        document["state"] = STATE_ABORTED
        document["failure_reason"] = reason
        self._write(document)
        return self

    def record_usage(self, *, calls: int, audio_seconds: float) -> tuple[int, float]:
        """Persist actual usage. MUST be called before the transport send it
        accounts for -- the whole point of this store is that a crash after
        this call still counts the spend against every later attempt on the
        same run_id. Returns the new cumulative (calls, audio_seconds)."""

        if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
            raise AttemptError(f"record_usage calls must be a positive integer, got {calls!r}")
        audio_seconds = _positive_finite(audio_seconds, "record_usage audio_seconds")
        document = self._read()
        if document.get("state") != STATE_OPENED:
            raise AttemptError(
                f"attempt {self.run_id}/{self.attempt_id} is not OPENED "
                f"(found {document.get('state')!r}); cannot record usage"
            )
        actual = document["actual"]
        new_calls = int(actual["calls"]) + calls
        new_audio = float(actual["audio_seconds"]) + audio_seconds
        actual["calls"] = new_calls
        actual["audio_seconds"] = new_audio
        self._write(document)
        return new_calls, new_audio


@dataclass(frozen=True)
class AttemptStore:
    """Bound to one controlled data root's ``attempts/`` subtree."""

    attempts_root: Path

    def _run_dir(self, run_id: str) -> Path:
        return Path(self.attempts_root) / run_id

    def open_attempt(
        self,
        run_id: str,
        attempt_id: str,
        *,
        carrier_lock_key: str,
        reserved_calls: int,
        reserved_audio_seconds: float,
    ) -> AttemptHandle:
        """Atomically create a brand-new attempt file (RESERVED -> OPENED).

        Fail-closed on: an invalid run/attempt id, a non-positive reservation,
        or -- the invariant this method exists to enforce -- a
        ``(run_id, attempt_id)`` pair that was ever opened before, whether by
        this process or another.
        """

        validate_id(run_id, "run_id")
        validate_id(attempt_id, "attempt_id")
        if not isinstance(carrier_lock_key, str) or not carrier_lock_key.strip():
            raise AttemptError("carrier_lock_key must be a non-empty string")
        reserved_calls_value = reserved_calls
        if isinstance(reserved_calls_value, bool) or not isinstance(reserved_calls_value, int) or reserved_calls_value <= 0:
            raise AttemptError(
                f"reserved_calls must be a positive integer, got {reserved_calls!r}"
            )
        reserved_audio_value = _positive_finite(reserved_audio_seconds, "reserved_audio_seconds")

        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        path = run_dir / f"{attempt_id}.json"
        document = {
            "schema": ATTEMPT_SCHEMA,
            "run_id": run_id,
            "attempt_id": attempt_id,
            "carrier_lock_key": carrier_lock_key,
            "state": STATE_RESERVED,
            "reserved": {
                "calls": int(reserved_calls_value),
                "audio_seconds": reserved_audio_value,
            },
            "actual": {"calls": 0, "audio_seconds": 0.0},
        }
        raw = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        # Carried T4-review minor (R0 repair T6): create+write must be atomic.
        # The old code did `os.open(O_CREAT|O_EXCL)` (making an EMPTY file
        # visible under `path` immediately) and only then wrote the bytes --
        # a concurrent reader (another AttemptHandle, or prior_actual_usage's
        # glob) could observe that empty file in between and raise
        # JSONDecodeError/AttemptError. The fix stages the FULL content in a
        # temp file in the same directory (so the final link is same-volume),
        # flushes+fsyncs it, and only ever makes `path` exist via `os.link`
        # from that already-fully-written temp file. `os.link` itself is the
        # atomic, exclusive step (POSIX and NTFS both refuse a link to an
        # existing destination), so a reader either sees `path` fully
        # populated or does not see it at all -- never a partial write.
        tmp = path.with_name(f".{path.name}.reserving-{os.getpid()}-{time.monotonic_ns()}")
        try:
            with open(tmp, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(tmp, path)
            except FileExistsError as error:
                raise AttemptError(
                    f"attempt {run_id}/{attempt_id} is already reserved or opened at {path}; "
                    "a (run_id, attempt_id) pair is a one-time key -- a retry must mint a "
                    "fresh attempt_id, never reuse this one"
                ) from error
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
        return AttemptHandle(path=path, run_id=run_id, attempt_id=attempt_id).mark_opened()

    def prior_actual_usage(self, run_id: str, *, exclude_attempt_id: str | None = None) -> tuple[int, float]:
        """Sum persisted actual usage from every attempt file already recorded
        for ``run_id``. Every state counts, including a crashed attempt stuck
        at OPENED: once usage is durably persisted it was genuinely about to
        be (or was) sent, and a later attempt never un-spends it."""

        validate_id(run_id, "run_id")
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            return 0, 0.0
        total_calls = 0
        total_audio = 0.0
        for entry in sorted(run_dir.glob("*.json")):
            if exclude_attempt_id is not None and entry.name == f"{exclude_attempt_id}.json":
                continue
            try:
                document = json.loads(entry.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise AttemptError(f"cannot read prior attempt state {entry}: {error}") from error
            actual = document.get("actual") if isinstance(document, dict) else None
            if not isinstance(actual, Mapping):
                raise AttemptError(f"attempt state {entry} lacks a usable actual mapping")
            total_calls += int(actual.get("calls", 0))
            total_audio += float(actual.get("audio_seconds", 0.0))
        return total_calls, total_audio

    def actual_usage_in_states(
        self,
        run_id: str,
        states: frozenset[str],
        *,
        exclude_attempt_id: str | None = None,
    ) -> tuple[int, float]:
        """Sum persisted actual usage from attempt files under ``run_id``
        whose CURRENT state is in ``states`` (R0 repair T7, invariant I8:
        failed-attempt cost). Distinct from :meth:`prior_actual_usage`, which
        sums every state unconditionally for budget enforcement (I6) -- this
        narrows to specific states for cost reporting, e.g.
        ``{STATE_ABORTED}`` to answer "how much did prior failed attempts on
        this run cost, on top of what the caller's own attempt spent"."""

        validate_id(run_id, "run_id")
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            return 0, 0.0
        total_calls = 0
        total_audio = 0.0
        for entry in sorted(run_dir.glob("*.json")):
            if exclude_attempt_id is not None and entry.name == f"{exclude_attempt_id}.json":
                continue
            try:
                document = json.loads(entry.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise AttemptError(f"cannot read prior attempt state {entry}: {error}") from error
            if not isinstance(document, dict) or document.get("state") not in states:
                continue
            actual = document.get("actual")
            if not isinstance(actual, Mapping):
                raise AttemptError(f"attempt state {entry} lacks a usable actual mapping")
            total_calls += int(actual.get("calls", 0))
            total_audio += float(actual.get("audio_seconds", 0.0))
        return total_calls, total_audio

    def all_actual_usage(self) -> tuple[int, float]:
        """Sum persisted actual usage across every run_id under this store --
        the global counterpart to :meth:`prior_actual_usage`, used by the
        slice-cap conservative-maximum check (registered vs. actual)."""

        root = Path(self.attempts_root)
        if not root.is_dir():
            return 0, 0.0
        total_calls = 0
        total_audio = 0.0
        for run_dir in sorted(entry for entry in root.iterdir() if entry.is_dir()):
            calls, audio = self.prior_actual_usage(run_dir.name)
            total_calls += calls
            total_audio += audio
        return total_calls, total_audio

    def handle(self, run_id: str, attempt_id: str) -> AttemptHandle:
        """A handle over an attempt file this store did NOT necessarily just
        open -- the caller is responsible for the file existing (R0 repair T6:
        used by ``core.bundle`` to re-read/transition an attempt's live state
        from only ``(run_id, attempt_id)``, without holding onto the original
        ``open_attempt`` return value across a process boundary)."""

        validate_id(run_id, "run_id")
        validate_id(attempt_id, "attempt_id")
        path = self._run_dir(run_id) / f"{attempt_id}.json"
        return AttemptHandle(path=path, run_id=run_id, attempt_id=attempt_id)

    def abort_if_opened(self, run_id: str, attempt_id: str, *, reason: str) -> bool:
        """Best-effort failure path (R0 repair T6, invariant I7): if this
        attempt was ever reserved/opened, mark it ABORTED with ``reason`` and
        return True. If it was never opened at all (a failure before
        ``FrozenCoreAdapter`` construction ever ran) there is nothing to
        abort -- returns False, not an error. If it is already FINALIZED or
        ABORTED, that terminal state is left exactly as it is (also False):
        a late failure elsewhere must never overwrite an already-settled
        attempt's outcome."""

        path = self.handle(run_id, attempt_id).path
        if not path.is_file():
            return False
        handle = AttemptHandle(path=path, run_id=run_id, attempt_id=attempt_id)
        try:
            handle.mark_aborted(reason)
        except AttemptError:
            return False
        return True
