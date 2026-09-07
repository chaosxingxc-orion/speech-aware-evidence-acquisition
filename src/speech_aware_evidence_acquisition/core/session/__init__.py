"""Runtime session attestation (R0 repair T5, invariant I5).

Reproduced defect: ``contracts.FrozenCoreGate`` re-hashes the pinned llama.cpp
binary, its ``build/bin`` runtime libraries and the GGUF files on disk -- then
``core.model.LlamaServerTransport`` simply POSTs to whatever ``base_url`` the
config names. Nothing binds the RESPONDING PROCESS to those hashed artifacts:
no PID, no binary hash of the running process, no argv, no listening-socket
check, no loaded-model identity, and no localhost restriction. A formal run
could therefore be served by a different local process, a remote service, or
a different model, while the record inherits the receipt-pinned identity.

The fix introduces a :class:`SessionReceipt`: a small, JSON-persistable proof
that binds ONE run to the ONE process that will answer it -- binary path +
sha256 (re-hashed against ``docs/receipts/runtime.json``'s pinned value,
never merely copied), argv, pid, host, port, and the exact GGUF/mmproj file
set (also from the runtime receipt). There are exactly two ways to obtain a
legitimate :class:`SessionReceipt`:

- :func:`start_session` spawns the runtime-receipt-pinned binary itself and
  records exactly what it started (this process's own child, so pid/argv/
  binary-hash-at-spawn-time are all directly observed, not merely asserted).
- :func:`attach_session` binds to an ALREADY-resident server via an on-disk
  session receipt (presumably written by an earlier :func:`start_session`,
  possibly in another process/session), but only after independently
  re-verifying that receipt's binary identity against the runtime receipt,
  confirming its pid is a live process right now, and confirming its host is
  loopback. A receipt that fails any one of those checks is worthless paper;
  attach refuses rather than trusting it.

Both paths, and :func:`verify_against_runtime_receipt` directly, are also the
transport's OWN defense-in-depth rail (``core.model.LlamaServerTransport``
re-checks a session's binary/model identity against the runtime receipt at
construction time and refuses a host/port that disagrees with the session
it was given) -- mirroring the "two independent rails" discipline the R0
repair campaign already established for I3/I4 (payload/media confinement is
checked in both the adapter AND the transport, never trusted from one side
only). A hand-built ``SessionReceipt`` that bypasses ``start_session``/
``attach_session`` entirely still cannot reach the transport's send path
unless it independently re-verifies true.

Standard-library only, no dependency on ``core.base``/``core.model`` -- like
``core.attempts``, this module is a self-contained seam either direction may
import without a cycle.

R0 repair refactor stage 1 (behaviour-preserving): this used to be one
~1100-line ``session.py`` module. It is now this package (``paths.py`` for
path/hash helpers, ``receipt.py`` for the SessionReceipt value type + its
read/write + runtime-receipt-bound verification, ``process.py`` for PID
liveness/process-image identity, ``sockets.py`` for the socket-ownership
plumbing, ``lifecycle.py`` for start_session/attach_session) purely for file
size -- every name below was already part of this module's public surface
and remains importable from exactly ``speech_aware_evidence_acquisition.
core.session`` as before.

ONE deliberate exception to "pure move": ``_posix_verify_pid_owns_listening_
socket`` and ``_windows_verify_pid_owns_listening_socket`` stay defined HERE
(not in ``sockets.py``, where the rest of the socket-ownership plumbing
lives) because ``tests/unit/test_session.py`` does
``monkeypatch.setattr(session_module, "_proc_net_listen_entries", _boom)``
and ``monkeypatch.setattr(session_module, "_windows_tcp_table_owners", _boom)``
where ``session_module`` IS this package (``speech_aware_evidence_
acquisition.core.session``) -- Python resolves a bare-name call inside a
function via the MODULE THE FUNCTION IS DEFINED IN, not the module that
happens to call it. Had these two callers moved to ``sockets.py`` alongside
their callees, the monkeypatch would silently stop taking effect (it would
patch this package's own re-exported copy of the name, never the one
``sockets.py``'s own functions actually consult), turning a real,
behaviour-changing regression invisible to a casual read. ``assert_session_
alive`` and the platform dispatcher ``_verify_pid_owns_listening_socket``
are kept alongside them for the same reason plus straightforward import-
ordering (see below).
"""

from __future__ import annotations

import ipaddress
import os
import socket
import urllib.parse
from pathlib import Path
from typing import Mapping

_LOOPBACK_LITERALS = ("127.0.0.1", "::1")


class SessionError(RuntimeError):
    """A session receipt, spawn, attach, or transport binding is refused."""


# ---------------------------------------------------------------------------
# Loopback enforcement.
# ---------------------------------------------------------------------------


def require_loopback(base_url: str) -> tuple[str, int]:
    """Parse ``base_url`` and refuse (:class:`SessionError`) unless its host
    is loopback. Only ``127.0.0.1``, ``::1`` and ``localhost`` are accepted --
    ``localhost`` is additionally resolved and EVERY returned address must
    itself be a loopback address, so a hosts-file/DNS override that points
    ``localhost`` off-box is refused too, not silently trusted by name alone.
    Returns ``(host, port)`` for the caller to bind a session against.
    """

    try:
        parsed = urllib.parse.urlsplit(base_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as error:
        raise SessionError(f"cannot parse base_url {base_url!r}: {error}") from error
    if not hostname:
        raise SessionError(f"base_url has no parseable host: {base_url!r}")
    if port is None:
        raise SessionError(f"base_url has no parseable port: {base_url!r}")
    if hostname in _LOOPBACK_LITERALS:
        return hostname, port
    if hostname.lower() == "localhost":
        try:
            infos = socket.getaddrinfo(hostname, None)
        except OSError as error:
            raise SessionError(f"cannot resolve base_url host {hostname!r}: {error}") from error
        if not infos:
            raise SessionError(f"base_url host {hostname!r} resolved to no addresses")
        for info in infos:
            address = info[4][0]
            try:
                is_loopback = ipaddress.ip_address(address).is_loopback
            except ValueError:
                is_loopback = False
            if not is_loopback:
                raise SessionError(
                    f"base_url host {hostname!r} resolves off-box to non-loopback "
                    f"address {address!r}; refused (I5)"
                )
        return hostname, port
    raise SessionError(
        "base_url host must be loopback (127.0.0.1, ::1 or localhost only); got "
        f"{hostname!r} in {base_url!r}"
    )


def _bracketed(host: str) -> str:
    """Wrap a bare IPv6 literal for URL construction; a no-op otherwise."""

    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


from .paths import _DRIVE_PREFIX, _resolve_under, _safe_relative, _sha256_file  # noqa: E402
from .receipt import (  # noqa: E402
    SESSION_RECEIPT_SCHEMA,
    SESSION_RECEIPT_SCHEMA_V2,
    STUDY_SLUG,
    ModelFileRef,
    SessionReceipt,
    _ID_PATTERN,
    _pinned_binary,
    _pinned_model_files,
    _SHA256,
    load_runtime_receipt,
    read_session_receipt,
    verify_against_runtime_receipt,
    write_session_receipt,
)
from .process import (  # noqa: E402
    MM_PROJ_AUDIT_SCHEMA,
    PROCESS_STATE_DEFUNCT,
    PROCESS_STATE_GONE,
    PROCESS_STATE_RUNNING,
    _defunct_wait_status,
    _pid_alive,
    _pid_is_defunct,
    _process_image_path,
    _verify_pid_runs_pinned_binary,
    audit_mmproj_free_inference,
    process_state,
)
from .sockets import (  # noqa: E402
    _PROC_NET_TCP_LISTEN_STATE,
    _SOCKET_FD_PATTERN,
    _decode_proc_net_address,
    _loopback_family_and_address,
    _pid_owns_any_inode,
    _proc_net_listen_entries,
    _windows_tcp_table_owners,
)
from . import sockets as _sockets  # noqa: E402  (module ref: see docstring above)


def _posix_verify_pid_owns_listening_socket(pid: int, host: str, port: int) -> None:
    family, expected_address = _loopback_family_and_address(host)
    path = Path("/proc/net/tcp") if family == socket.AF_INET else Path("/proc/net/tcp6")
    entries = _proc_net_listen_entries(path, family)
    # DESIGN DECISION (stated explicitly, per re-review round 3): a wildcard
    # bind (0.0.0.0 / ::) is NEVER treated as owning a specific loopback
    # address here -- only an EXACT address match counts. Real llama-server
    # invoked with --host 127.0.0.1 binds exactly that address, never a
    # wildcard, so this costs nothing for this study's actual usage while
    # sidestepping entirely the harder question of whether a wildcard bind
    # could be shadowed by a more specific, unverified listener on the same
    # port (which a real OS generally refuses to let coexist on the exact
    # same port without SO_REUSEPORT participation from both sides, but
    # this function does not try to reason about that at all -- it simply
    # never accepts a wildcard as proof of a specific address, the more
    # conservative of the two choices the re-review explicitly allowed).
    matching_inodes = {
        inode
        for address, entry_port, inode in entries
        if entry_port == port and address == expected_address
    }
    if not matching_inodes:
        raise SessionError(
            f"no LISTEN socket found for {expected_address}:{port} ({path}); "
            "refused (I5: socket ownership must be provable)"
        )
    if not _pid_owns_any_inode(pid, matching_inodes):
        raise SessionError(
            f"pid {pid} does not own the listening socket on {expected_address}:"
            f"{port}; refused (I5: PID/binary identity alone does not prove the "
            "session's process is the one actually listening on this endpoint)"
        )


def _windows_verify_pid_owns_listening_socket(pid: int, host: str, port: int) -> None:
    family, expected_address = _loopback_family_and_address(host)
    row_type = _sockets._MibTcpRowOwnerPid if family == _sockets._AF_INET else _sockets._MibTcp6RowOwnerPid
    owners = _windows_tcp_table_owners(family, row_type)
    # Same wildcard design decision as POSIX (see _posix_verify_...): a
    # 0.0.0.0/:: bind is a distinct address from 127.0.0.1/::1 and is never
    # treated as satisfying it -- only the exact tuple key matches.
    owner_pid = owners.get((family, expected_address, port))
    if owner_pid is None:
        raise SessionError(
            f"no LISTEN socket found for {expected_address}:{port}; refused (I5: "
            "socket ownership must be provable)"
        )
    if owner_pid != pid:
        raise SessionError(
            f"{expected_address}:{port} is owned by pid {owner_pid}, not the "
            f"session's pid {pid}; refused (I5: PID/binary identity alone does "
            "not prove the session's process is the one actually listening on "
            "this endpoint)"
        )


def _verify_pid_owns_listening_socket(pid: int, host: str, port: int) -> None:
    """Dispatch to the platform-specific, ADDRESS-AWARE socket-ownership
    check.

    T5 fix-3 correction, recorded rather than silently deleted: an earlier
    version of this function's docstring claimed ``host`` did not need to
    be used because ``require_loopback`` already restricts every session's
    host to a fixed set -- THAT REASONING WAS WRONG. Restricting the SET of
    legal host STRINGS says nothing about which ADDRESS FAMILY a socket is
    actually bound to: ``127.0.0.1`` and ``::1`` are two distinct,
    simultaneously bindable endpoints. A process can genuinely, verifiably
    own a LISTEN socket on ``::1:PORT`` while a completely different,
    unverified process owns ``127.0.0.1:PORT`` on the exact same port
    number -- checking "is `port` owned by `pid`" without the address let
    exactly that forgery through, live-reproduced end to end. Every lookup
    below is keyed by (address family, literal address, port); see
    :func:`_loopback_family_and_address` for how ``host`` resolves to that
    family+address (including the explicit ``localhost`` ambiguity
    refusal), and :func:`_posix_verify_pid_owns_listening_socket`'s
    docstring for the wildcard-bind design decision.
    """

    if os.name == "nt":  # pragma: sys-platform
        _windows_verify_pid_owns_listening_socket(pid, host, port)
    else:
        _posix_verify_pid_owns_listening_socket(pid, host, port)


def assert_session_alive(
    session: SessionReceipt, runtime_receipt: Mapping[str, object], runtime_root: Path
) -> None:
    """The full I5 liveness+identity+socket-ownership re-check: declared-value
    agreement with the runtime receipt, PID liveness RIGHT NOW, that the pid
    is actually running the pinned binary's executable image (T5 fix-1, not
    merely SOME live process that happens to share a number with a forged
    receipt), and -- T5 fix-2, closing a materially equivalent gap an
    independent re-review demonstrated live on both platforms -- that the
    pid actually OWNS the kernel-level listening socket on ``session.host``/
    ``session.port``, not merely that it happens to be a live, pinned-binary
    process somewhere (a forged receipt can name a genuine SECOND instance
    of the pinned binary that isn't bound to the target port at all). Every
    check re-touches ground truth; nothing here is ever cached across calls.

    This is the ONE place the full check is implemented; it is called from
    THREE independent enforcement sites (``attach_session``,
    ``core.model.LlamaServerTransport`` at construction AND every send, and
    -- as a complementary adapter-level call, R0 repair T5 fix-3 --
    ``core.model.FrozenCoreAdapter`` before every request when its transport
    exposes an ``assert_session_alive()`` method). The sites are independent
    (each can catch a failure the others miss, e.g. a future refactor that
    accidentally drops the transport's own per-call check would still be
    caught by the adapter's); the underlying verification CODE is shared,
    unlike I3/I4's payload/media-confinement checks, which T3 deliberately
    reimplemented twice. Full reimplementation is not appropriate here:
    binary/PID/process-image/socket identity is inherently specific to a
    subprocess-backed HTTP transport, not a generic concept every
    ``Callable[[bytes], bytes]`` transport shares the way a payload's
    ``media_relpath`` is."""

    verify_against_runtime_receipt(session, runtime_receipt)
    if not _pid_alive(session.pid):
        raise SessionError(
            f"session {session.session_id!r} pid {session.pid} is not a live process; "
            "refused (I5)"
        )
    _verify_pid_runs_pinned_binary(session.pid, runtime_root, runtime_receipt)
    _verify_pid_owns_listening_socket(session.pid, session.host, session.port)


from .lifecycle import (  # noqa: E402
    DEFAULT_STARTUP_MAX_BYTES,
    DEFAULT_STARTUP_TIMEOUT_SECONDS,
    EXT4_MODEL_SHA256_PINS,
    EXT4_MODELS_ROOT_DEFAULT,
    EXT4_MODELS_ROOT_ENV,
    FEAT_CACHE_DIR_DEFAULT,
    FEAT_CACHE_DIR_ENV,
    ServerCommand,
    _capture_startup_stdout,
    _ext4_models_root,
    _iso,
    _model_file_argv,
    _resolve_model_file_source,
    attach_session,
    build_server_command,
    describe_wait_status,
    feat_cache_dir,
    reap_child,
    start_session,
    stop_session,
)

__all__ = [
    "DEFAULT_STARTUP_MAX_BYTES",
    "DEFAULT_STARTUP_TIMEOUT_SECONDS",
    "EXT4_MODEL_SHA256_PINS",
    "EXT4_MODELS_ROOT_DEFAULT",
    "EXT4_MODELS_ROOT_ENV",
    "FEAT_CACHE_DIR_DEFAULT",
    "FEAT_CACHE_DIR_ENV",
    "SESSION_RECEIPT_SCHEMA",
    "SESSION_RECEIPT_SCHEMA_V2",
    "STUDY_SLUG",
    "ModelFileRef",
    "MM_PROJ_AUDIT_SCHEMA",
    "PROCESS_STATE_DEFUNCT",
    "PROCESS_STATE_GONE",
    "PROCESS_STATE_RUNNING",
    "ServerCommand",
    "SessionError",
    "SessionReceipt",
    "assert_session_alive",
    "audit_mmproj_free_inference",
    "attach_session",
    "build_server_command",
    "describe_wait_status",
    "feat_cache_dir",
    "load_runtime_receipt",
    "process_state",
    "reap_child",
    "read_session_receipt",
    "require_loopback",
    "start_session",
    "stop_session",
    "verify_against_runtime_receipt",
    "write_session_receipt",
    "_DRIVE_PREFIX",
    "_ID_PATTERN",
    "_PROC_NET_TCP_LISTEN_STATE",
    "_SHA256",
    "_SOCKET_FD_PATTERN",
    "_bracketed",
    "_capture_startup_stdout",
    "_decode_proc_net_address",
    "_defunct_wait_status",
    "_ext4_models_root",
    "_iso",
    "_loopback_family_and_address",
    "_model_file_argv",
    "_pid_alive",
    "_pid_is_defunct",
    "_pid_owns_any_inode",
    "_pinned_binary",
    "_pinned_model_files",
    "_posix_verify_pid_owns_listening_socket",
    "_process_image_path",
    "_proc_net_listen_entries",
    "_resolve_model_file_source",
    "_resolve_under",
    "_safe_relative",
    "_sha256_file",
    "_verify_pid_owns_listening_socket",
    "_verify_pid_runs_pinned_binary",
    "_windows_tcp_table_owners",
    "_windows_verify_pid_owns_listening_socket",
]
