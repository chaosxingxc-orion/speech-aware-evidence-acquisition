"""``AttemptHandle``: a live reference to one attempt's durable state file.

Split out of the former monolithic ``core/attempts.py`` (R0 repair refactor
stage 2, pure move, no behaviour change). See ``core/attempts/__init__.py``
for the full module docstring this package shares.
"""

from __future__ import annotations

import fcntl
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    CONTACT_KINDS,
    CONTACT_KIND_SPEECH,
    CONTACT_KIND_TEXT_ENCODER,
    STATE_ABORTED,
    STATE_FINALIZED,
    STATE_OPENED,
    STATE_RESERVED,
)
from .errors import AttemptError, _non_negative_finite, _positive_finite, _zero_finite


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

    @contextmanager
    def _mutation_lock(self):
        """Serialize every read-modify-write mutation for this attempt."""

        lock_path = self.path.parent.parent / f".{self.run_id}.{self.attempt_id}.lock"
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            with lock_path.open("a+", encoding="utf-8") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except OSError as error:
            raise AttemptError(f"cannot lock attempt state {self.path}: {error}") from error

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
        with self._mutation_lock():
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
        """OPENED -> FINALIZED after the verified bundle is complete."""

        with self._mutation_lock():
            document = self._read()
            if document.get("state") != STATE_OPENED:
                raise AttemptError(
                    f"attempt {self.run_id}/{self.attempt_id} is not OPENED "
                    f"(found {document.get('state')!r}); cannot transition to FINALIZED"
                )
            document["state"] = STATE_FINALIZED
            self._write(document)
        return self

    def finalize_with_receipt(
        self, path: str, sha256: str, kind: str
    ) -> "AttemptHandle":
        """Finalize once with an exact, idempotent evidence binding."""

        if not isinstance(path, str) or not path.strip():
            raise AttemptError("finalization path must be a non-empty string")
        if (
            not isinstance(sha256, str)
            or len(sha256) != 64
            or any(character not in "0123456789abcdef" for character in sha256)
        ):
            raise AttemptError("finalization sha256 must be 64 lowercase hex characters")
        if not isinstance(kind, str) or not kind.strip():
            raise AttemptError("finalization kind must be a non-empty string")
        binding = {"path": path, "sha256": sha256, "kind": kind}
        with self._mutation_lock():
            document = self._read()
            state = document.get("state")
            existing = document.get("finalization")
            if state == STATE_FINALIZED and existing == binding:
                return self
            if state != STATE_OPENED:
                raise AttemptError(
                    f"attempt {self.run_id}/{self.attempt_id} is not OPENED "
                    f"(found {state!r}); cannot finalize with a receipt"
                )
            if existing is not None:
                raise AttemptError("attempt already carries a different finalization binding")
            document["finalization"] = binding
            document["state"] = STATE_FINALIZED
            self._write(document)
        return self

    def mark_aborted(self, reason: str) -> "AttemptHandle":
        """RESERVED/OPENED -> ABORTED with a durable failure reason."""

        if not isinstance(reason, str) or not reason.strip():
            raise AttemptError("mark_aborted reason must be a non-empty string")
        with self._mutation_lock():
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
        """Persist calls and contact-kind-appropriate audio under the lock."""

        if isinstance(calls, bool) or not isinstance(calls, int) or calls <= 0:
            raise AttemptError(f"record_usage calls must be a positive integer, got {calls!r}")
        with self._mutation_lock():
            document = self._read()
            if "contact_kind" in document:
                contact_kind = document["contact_kind"]
                if (
                    not isinstance(contact_kind, str)
                    or contact_kind not in CONTACT_KINDS
                ):
                    raise AttemptError(
                        "attempt state has malformed persisted contact_kind "
                        f"{contact_kind!r}"
                    )
            else:
                contact_kind = CONTACT_KIND_SPEECH
            if contact_kind == CONTACT_KIND_TEXT_ENCODER:
                reserved = document.get("reserved")
                actual = document.get("actual")
                if not isinstance(reserved, dict) or not isinstance(actual, dict):
                    raise AttemptError(
                        "text-encoder attempt state requires reserved and actual mappings"
                    )
                _zero_finite(
                    reserved.get("audio_seconds"),
                    "persisted text-encoder reserved.audio_seconds",
                )
                _zero_finite(
                    actual.get("audio_seconds"),
                    "persisted text-encoder actual.audio_seconds",
                )
                audio_seconds = _zero_finite(
                    audio_seconds, "record_usage audio_seconds"
                )
            else:
                audio_seconds = _positive_finite(
                    audio_seconds, "record_usage audio_seconds"
                )
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
        """Persist measured GPU-seconds under the per-attempt lock."""

        gpu_seconds = _non_negative_finite(gpu_seconds, "record_gpu_seconds gpu_seconds")
        with self._mutation_lock():
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
