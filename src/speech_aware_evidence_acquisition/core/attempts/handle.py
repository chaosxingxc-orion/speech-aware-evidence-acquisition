"""``AttemptHandle``: a live reference to one attempt's durable state file.

Split out of the former monolithic ``core/attempts.py`` (R0 repair refactor
stage 2, pure move, no behaviour change). See ``core/attempts/__init__.py``
for the full module docstring this package shares.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

from .constants import STATE_ABORTED, STATE_FINALIZED, STATE_OPENED, STATE_RESERVED
from .errors import AttemptError, _non_negative_finite, _positive_finite


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

    def record_gpu_seconds(self, gpu_seconds: float) -> float:
        """Persist measured GPU-seconds for this attempt (fix-wave2 Minor:
        gpu hours had no derived counterpart -- calls/audio already had a
        durably persisted actual figure while gpu hours was taken purely
        from self-declared ledger cells, even though ``gpu_seconds`` IS
        measured per run (``core.resources.ResourceSampler.summary``)).
        (The slice-wide budget-cap check this originally fed,
        ``contracts.FrozenCoreGate._require_exposure_preregistration``, was
        retired by the 2026-08-06 owner amendment
        (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS); durable per-run GPU
        cost accounting stays useful regardless.)

        Called by ``core.driver.run_experiment`` AFTER the request loop, once
        the run's own resource sampler has a final measured total -- unlike
        ``record_usage`` (per-request, called BEFORE the transport send it
        accounts for), gpu_seconds is a whole-run figure only available once
        sampling stops. Same OPENED-only, durable-file discipline as
        :meth:`record_usage`: an older attempt file with no ``gpu_seconds``
        key yet (written before this field existed) is read as ``0.0`` and
        accumulated from there. Returns the new cumulative gpu_seconds."""

        gpu_seconds = _non_negative_finite(gpu_seconds, "record_gpu_seconds gpu_seconds")
        document = self._read()
        if document.get("state") != STATE_OPENED:
            raise AttemptError(
                f"attempt {self.run_id}/{self.attempt_id} is not OPENED "
                f"(found {document.get('state')!r}); cannot record gpu usage"
            )
        actual = document["actual"]
        new_gpu_seconds = float(actual.get("gpu_seconds", 0.0)) + gpu_seconds
        actual["gpu_seconds"] = new_gpu_seconds
        self._write(document)
        return new_gpu_seconds

    def actual_gpu_seconds(self) -> float:
        """Read-only counterpart to :meth:`actual_totals`, for the one field
        that arrives on a separate write path (see :meth:`record_gpu_seconds`)."""

        actual = self._read()["actual"]
        return float(actual.get("gpu_seconds", 0.0))
