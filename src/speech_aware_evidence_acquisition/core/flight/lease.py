"""One coordinator-held generation lease, shared by flights and prompt fits.

Hold a kernel lock on a stable inode; atomically publish compatible flight
metadata separately. Never unlink the kernel lock file. A worker receives a
capability for one run/attempt/session, not permission to acquire or release it.
No server, model, tokenizer or encoder is contacted by this module.
"""
from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

SCHEMA = "saea-generation-lease-v1"


class GenerationLeaseError(RuntimeError):
    """Refuse ambiguous ownership or an invalid worker capability."""


def _paths(data_root: Path) -> tuple[Path, Path]:
    directory = Path(data_root) / "locks"
    return directory / "generation.guard", directory / "flight.lock"


def _read(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise GenerationLeaseError(f"lease metadata is unreadable: {path}") from error
    if not isinstance(document, dict):
        raise GenerationLeaseError("lease metadata must be an object")
    return document


def _alive(pid: object) -> bool:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise GenerationLeaseError("lease metadata has no valid owner pid")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _publish(path: Path, document: Mapping[str, object]) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=".flight-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class GenerationLease:
    """Keep the descriptor alive in the coordinator until seal or abort."""

    def __init__(self, descriptor: int, metadata: Path, document: dict):
        self._descriptor = descriptor
        self._metadata = metadata
        self._document = document
        self.token = str(document["token"])

    @classmethod
    def acquire(
        cls, data_root: Path, *, owner: str, run_id: str, attempt_id: str,
        session_id: str, study_head: str,
    ) -> GenerationLease:
        fields = dict(owner=owner, run_id=run_id, attempt_id=attempt_id, session_id=session_id)
        if any(not isinstance(value, str) or not value.strip() for value in fields.values()):
            raise GenerationLeaseError("lease owner/run/attempt/session must be non-empty strings")
        if not isinstance(study_head, str) or re.fullmatch(r"[0-9a-f]{40}", study_head) is None:
            raise GenerationLeaseError("lease study_head must be a full commit hash")
        guard, metadata = _paths(data_root)
        guard.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(guard, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise GenerationLeaseError("generation lease is already held") from error
            if metadata.exists():
                _read(metadata)
                # Owner death does not establish worker/server contact quiescence.
                # Preserve the evidence for explicit coordinator reconciliation.
                raise GenerationLeaseError(
                    "legacy or unreconciled flight metadata blocks generation; "
                    "record PID/socket/contact quiescence before manual reconciliation"
                )
            document = {
                "schema": SCHEMA, **fields, "run_ids": [run_id],
                "pid": os.getpid(), "token": secrets.token_hex(32),
                "study_head": study_head,
                "started_at": datetime.now(timezone.utc).isoformat(),
            }
            _publish(metadata, document)
            return cls(descriptor, metadata, document)
        except BaseException:
            os.close(descriptor)
            raise

    def release(self) -> None:
        if self._descriptor is None:
            return
        if os.getpid() != self._document["pid"]:
            raise GenerationLeaseError("only the owning process may release the lease")
        descriptor, self._descriptor = self._descriptor, None
        try:
            current = _read(self._metadata)
            if current != self._document:
                raise GenerationLeaseError("lease ownership changed; metadata was preserved")
            self._metadata.unlink()
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def __enter__(self) -> GenerationLease:
        return self

    def __exit__(self, *_exc) -> None:
        self.release()


@dataclass(frozen=True)
class WorkerExecutionPolicy:
    """Require the coordinator's exact session and still-held generation lease."""

    expected_session_id: str
    lease_token: str
    require_resident: bool = True

    def __post_init__(self) -> None:
        if self.require_resident is not True:
            raise GenerationLeaseError("campaign workers require a resident session")
        for value in (self.expected_session_id, self.lease_token):
            if not isinstance(value, str) or not value.strip():
                raise GenerationLeaseError("worker session and lease token must be explicit")

    def assert_lease(self, data_root: Path, *, run_id: str, attempt_id: str) -> dict:
        guard, metadata = _paths(data_root)
        document = _read(metadata)
        expected = {
            "schema": SCHEMA, "token": self.lease_token,
            "run_id": run_id, "attempt_id": attempt_id,
            "session_id": self.expected_session_id,
        }
        for name, value in expected.items():
            if document.get(name) != value:
                raise GenerationLeaseError(f"worker lease {name} does not match")
        if not _alive(document.get("pid")):
            raise GenerationLeaseError("generation lease owner is no longer alive")
        try:
            descriptor = os.open(guard, os.O_RDWR)
        except OSError as error:
            raise GenerationLeaseError("generation lease is not held") from error
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if _read(metadata) != document:
                    raise GenerationLeaseError("lease ownership changed during verification")
                return document
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            raise GenerationLeaseError("generation lease metadata exists but lock is not held")
        finally:
            os.close(descriptor)
