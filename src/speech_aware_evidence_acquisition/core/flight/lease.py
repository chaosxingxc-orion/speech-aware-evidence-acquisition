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
PANEL_SCHEMA = "saea-generation-panel-lease-v1"


class GenerationLeaseError(RuntimeError):
    """Refuse ambiguous ownership or an invalid worker capability."""


def _member_pairs(members):
    if not isinstance(members, (tuple, list)) or not 2 <= len(members) <= 8:
        raise GenerationLeaseError("panel lease needs two to eight exact members")
    pairs = []
    for pair in members:
        if (not isinstance(pair, (tuple, list)) or len(pair) != 2
                or any(not isinstance(s, str) or not s.strip() for s in pair)):
            raise GenerationLeaseError("panel lease member needs run and attempt ids")
        pairs.append(tuple(pair))
    if len({p[0] for p in pairs}) != len(pairs) or len({p[1] for p in pairs}) != len(pairs):
        raise GenerationLeaseError("panel lease repeats a run or attempt")
    return tuple(pairs)


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
        document = {"schema": SCHEMA, **fields, "run_ids": [run_id], "study_head": study_head}
        return cls._acquire_document(data_root, document)

    @classmethod
    def acquire_panel(cls, data_root, *, owner, panel_id, members, session_id, study_head):
        """Hold one lease for a prospectively declared coordinated panel."""
        members = _member_pairs(members)
        if any(not isinstance(s, str) or not s.strip() for s in (owner, panel_id, session_id)):
            raise GenerationLeaseError("panel owner, id and session must be explicit")
        if not isinstance(study_head, str) or re.fullmatch(r"[0-9a-f]{40}", study_head) is None:
            raise GenerationLeaseError("lease study_head must be a full commit hash")
        document = {
            "schema": PANEL_SCHEMA, "owner": owner, "panel_id": panel_id,
            "run_id": members[0][0], "attempt_id": members[0][1],
            "run_ids": [p[0] for p in members], "members": [list(p) for p in members],
            "session_id": session_id, "study_head": study_head,
        }
        return cls._acquire_document(data_root, document)

    @classmethod
    def _acquire_document(cls, data_root, document):
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
                **document, "pid": os.getpid(), "token": secrets.token_hex(32),
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

    def __exit__(self, exc_type, *_exc) -> None:
        if exc_type is None:
            self.release()
        elif self._descriptor is not None:
            # An interrupted contact may still be executing in the resident
            # server. Preserve metadata until root proves contact quiescence.
            descriptor, self._descriptor = self._descriptor, None
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)


@dataclass(frozen=True)
class WorkerExecutionPolicy:
    """Require the coordinator's exact session and still-held generation lease."""

    expected_session_id: str
    lease_token: str
    require_resident: bool = True
    panel_id: str | None = None
    panel_members: tuple[tuple[str, str], ...] | None = None

    def __post_init__(self) -> None:
        if self.panel_id is None:
            if self.panel_members is not None:
                raise GenerationLeaseError("panel members need an explicit panel id")
        else:
            if not isinstance(self.panel_id, str) or not self.panel_id.strip():
                raise GenerationLeaseError("panel id must be nonempty text")
            object.__setattr__(self, "panel_members", _member_pairs(self.panel_members))
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
        if self.panel_id is not None:
            if (run_id, attempt_id) not in self.panel_members:
                raise GenerationLeaseError("worker run/attempt is outside its panel")
            expected = {
                "schema": PANEL_SCHEMA, "token": self.lease_token,
                "session_id": self.expected_session_id, "panel_id": self.panel_id,
                "members": [list(p) for p in self.panel_members],
                "run_ids": [p[0] for p in self.panel_members],
                "run_id": self.panel_members[0][0], "attempt_id": self.panel_members[0][1],
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
