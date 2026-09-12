"""``AttemptStore``: bound to one controlled data root's ``attempts/`` subtree.

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
from typing import Mapping

from .constants import (
    ATTEMPT_SCHEMA,
    CONTACT_KINDS,
    CONTACT_KIND_SPEECH,
    CONTACT_KIND_TEXT_ENCODER,
    STATE_RESERVED,
)
from .errors import (
    AttemptError,
    _coerce_actual_field,
    _positive_finite,
    _zero_finite,
    validate_id,
)
from .handle import AttemptHandle


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
        contact_kind: str = CONTACT_KIND_SPEECH,
    ) -> AttemptHandle:
        """Atomically create a brand-new attempt file (RESERVED -> OPENED).

        Fail-closed on an invalid run/attempt id, a reservation inconsistent
        with its contact kind, or -- the invariant this method enforces -- a
        ``(run_id, attempt_id)`` pair that was ever opened before, whether by
        this process or another.
        """

        validate_id(run_id, "run_id")
        validate_id(attempt_id, "attempt_id")
        if not isinstance(carrier_lock_key, str) or not carrier_lock_key.strip():
            raise AttemptError("carrier_lock_key must be a non-empty string")
        if not isinstance(contact_kind, str) or contact_kind not in CONTACT_KINDS:
            raise AttemptError(
                f"contact_kind must be one of {sorted(CONTACT_KINDS)}, "
                f"got {contact_kind!r}"
            )
        reserved_calls_value = reserved_calls
        if isinstance(reserved_calls_value, bool) or not isinstance(reserved_calls_value, int) or reserved_calls_value <= 0:
            raise AttemptError(
                f"reserved_calls must be a positive integer, got {reserved_calls!r}"
            )
        if contact_kind == CONTACT_KIND_TEXT_ENCODER:
            reserved_audio_value = _zero_finite(
                reserved_audio_seconds, "reserved_audio_seconds"
            )
        else:
            reserved_audio_value = _positive_finite(
                reserved_audio_seconds, "reserved_audio_seconds"
            )

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
        if contact_kind == CONTACT_KIND_TEXT_ENCODER:
            document["contact_kind"] = CONTACT_KIND_TEXT_ENCODER
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

    def _sum_actual_for_run(
        self, run_id: str, *, exclude_attempt_id: str | None = None
    ) -> tuple[int, float, float]:
        """Shared summation core for :meth:`prior_actual_usage` and
        :meth:`all_actual_usage` (fix-wave2 Minor: refactored to also carry
        ``gpu_seconds`` -- see :meth:`AttemptHandle.record_gpu_seconds`).
        Every state counts, including a crashed attempt stuck at OPENED: once
        usage is durably persisted it was genuinely about to be (or was)
        sent/measured, and a later attempt never un-spends it. An older
        attempt file with no ``gpu_seconds`` key (written before that field
        existed) reads as ``0.0`` for that field, never an error.

        MINOR fix-wave3 (external-threat-model review round 3): a JSON-valid
        attempt file whose ``actual.calls``/``audio_seconds``/``gpu_seconds``
        is a non-numeric value (e.g. ``"calls": "lots"``) previously raised a
        bare ``ValueError`` straight out of the unguarded ``int()``/``float()``
        calls below -- past the ``except AttemptError`` wrapper at every real
        caller, leaking an internal implementation detail as an undocumented
        exception type instead of this module's own documented
        ``AttemptError``. Also, a NEGATIVE persisted value (a corrupted or
        hand-tampered attempt file) previously summed straight through with
        no check at all, silently deflating the summed actual-usage total.
        Both are now refused fail-closed, wrapped as ``AttemptError``, via
        :func:`_coerce_actual_field`."""

        validate_id(run_id, "run_id")
        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            return 0, 0.0, 0.0
        total_calls = 0
        total_audio = 0.0
        total_gpu = 0.0
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
            total_calls += _coerce_actual_field(
                actual.get("calls", 0), int, f"{entry} actual.calls"
            )
            total_audio += _coerce_actual_field(
                actual.get("audio_seconds", 0.0), float, f"{entry} actual.audio_seconds"
            )
            total_gpu += _coerce_actual_field(
                actual.get("gpu_seconds", 0.0), float, f"{entry} actual.gpu_seconds"
            )
        return total_calls, total_audio, total_gpu

    def prior_actual_usage(self, run_id: str, *, exclude_attempt_id: str | None = None) -> tuple[int, float]:
        """Sum persisted actual calls/audio_seconds from every attempt file
        already recorded for ``run_id`` (calls/audio budget enforcement, I3/
        I6 -- gpu hours is not part of this per-request check; see
        :meth:`all_actual_usage` for the slice-wide figure that includes it)."""

        calls, audio, _gpu_seconds = self._sum_actual_for_run(
            run_id, exclude_attempt_id=exclude_attempt_id
        )
        return calls, audio

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

    def all_actual_usage(self) -> tuple[int, float, float]:
        """Sum persisted actual (calls, audio_seconds, gpu_seconds) across
        every run_id under this store -- the global counterpart to
        :meth:`prior_actual_usage`. Returns a 3-tuple (fix-wave2 Minor:
        gpu_seconds joined calls/audio_seconds here, the one budget dimension
        that previously had no derived counterpart). Not consumed by
        ``contracts.FrozenCoreGate`` since the 2026-08-06 owner amendment
        retired the slice-wide budget-cap check that used to read this figure
        (SAEA-OWNER-AMENDMENT-2026-08-06-BUDGET-CAPS); kept as a general
        cross-run actual-usage accounting utility."""

        root = Path(self.attempts_root)
        if not root.is_dir():
            return 0, 0.0, 0.0
        total_calls = 0
        total_audio = 0.0
        total_gpu = 0.0
        for run_dir in sorted(entry for entry in root.iterdir() if entry.is_dir()):
            calls, audio, gpu = self._sum_actual_for_run(run_dir.name)
            total_calls += calls
            total_audio += audio
            total_gpu += gpu
        return total_calls, total_audio, total_gpu

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
