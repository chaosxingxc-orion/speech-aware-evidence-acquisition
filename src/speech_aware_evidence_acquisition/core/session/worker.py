"""Attach-only worker access to the coordinator's registered resident session."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping

from . import attach_session
from .serving import SESSION_RECEIPT_NAME, assert_identity_matches, find_resident_session

if TYPE_CHECKING:
    from ..flight.lease import WorkerExecutionPolicy


def attach_worker_session(
    *, policy: WorkerExecutionPolicy, data_root: Path, run_id: str, attempt_id: str,
    required_identity: Mapping[str, object], runtime_receipt: Mapping[str, object],
    runtime_root: Path, finder: Callable = find_resident_session,
    attacher: Callable = attach_session,
) -> tuple[Path, Mapping[str, object], object]:
    """Validate custody and complete pinned identity before the existing attach API.

    Prompt fitting and generation use this same capability. No fallback starts
    a server, and the returned session conveys no shutdown ownership.
    """
    from ..flight.lease import GenerationLeaseError

    policy.assert_lease(data_root, run_id=run_id, attempt_id=attempt_id)
    resident = finder(data_root)
    if resident is None:
        raise GenerationLeaseError("required resident session is absent; worker cannot start it")
    session_dir, document = resident
    if document.get("session_id") != policy.expected_session_id:
        raise GenerationLeaseError("resident session differs from the coordinator capability")
    assert_identity_matches(document, required_identity)
    session_dir = Path(session_dir)
    session = attacher(
        session_dir / SESSION_RECEIPT_NAME,
        runtime_receipt=runtime_receipt, runtime_root=runtime_root,
    )
    policy.assert_lease(data_root, run_id=run_id, attempt_id=attempt_id)
    return session_dir, document, session


class LeaseCheckedTransport:
    """Preserve the shared transport while checking custody on every contact."""

    def __init__(self, transport: object, assert_lease: Callable[[], object]):
        self._transport = transport
        self._assert_lease = assert_lease

    def __call__(self, request_bytes: bytes) -> bytes:
        self._assert_lease()
        return self._transport(request_bytes)

    def __getattr__(self, name: str) -> object:
        return getattr(self._transport, name)
