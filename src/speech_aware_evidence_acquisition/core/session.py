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
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import queue
import re
import socket
import subprocess
import threading
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..contracts import STUDY_SLUG

SESSION_RECEIPT_SCHEMA = "saea-session-receipt-v1"

DEFAULT_STARTUP_TIMEOUT_SECONDS = 5.0
DEFAULT_STARTUP_MAX_BYTES = 65536

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")
# Same shape as core.attempts._ID_PATTERN: embedded verbatim into a filesystem
# path (a session receipt's file stem) and echoed into trace/audit text.
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")

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


# ---------------------------------------------------------------------------
# Value types.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelFileRef:
    """One GGUF file's canonical relative path + sha256, as bound by the
    runtime receipt -- covers both the main model and the mmproj file."""

    path: str
    sha256: str

    def validate(self) -> "ModelFileRef":
        _safe_relative(self.path, "model file path")
        if not isinstance(self.sha256, str) or _SHA256.fullmatch(self.sha256) is None:
            raise SessionError(f"model file {self.path!r} lacks a valid sha256")
        return self


@dataclass(frozen=True)
class SessionReceipt:
    """Binds one run to the ONE process that will answer its model requests.

    Every field is either directly observed at spawn time (pid, argv, binary
    bytes re-hashed at that moment) or copied from the already-verified
    runtime receipt (model_files) -- never merely asserted by a caller.
    """

    schema: str
    study: str
    session_id: str
    binary_path: str
    binary_sha256: str
    argv: tuple[str, ...]
    pid: int
    host: str
    port: int
    model_files: tuple[ModelFileRef, ...]
    started_at: str
    startup_stdout_sha256: str

    def validate(self) -> "SessionReceipt":
        if self.schema != SESSION_RECEIPT_SCHEMA:
            raise SessionError(
                f"session receipt schema must be {SESSION_RECEIPT_SCHEMA!r}, got {self.schema!r}"
            )
        if self.study != STUDY_SLUG:
            raise SessionError(f"session receipt study must be {STUDY_SLUG!r}, got {self.study!r}")
        if not isinstance(self.session_id, str) or _ID_PATTERN.fullmatch(self.session_id) is None:
            raise SessionError(
                f"session_id must match {_ID_PATTERN.pattern!r}, got {self.session_id!r}"
            )
        _safe_relative(self.binary_path, "session binary_path")
        if not isinstance(self.binary_sha256, str) or _SHA256.fullmatch(self.binary_sha256) is None:
            raise SessionError("session binary_sha256 must be a 64-hex sha256")
        if (
            not isinstance(self.argv, tuple)
            or not self.argv
            or not all(isinstance(part, str) and part for part in self.argv)
        ):
            raise SessionError("session argv must be a non-empty tuple of non-empty strings")
        if isinstance(self.pid, bool) or not isinstance(self.pid, int) or self.pid <= 0:
            raise SessionError(f"session pid must be a positive integer, got {self.pid!r}")
        if not isinstance(self.host, str) or not self.host:
            raise SessionError("session host must be a non-empty string")
        if self.host not in _LOOPBACK_LITERALS and self.host.lower() != "localhost":
            raise SessionError(f"session host {self.host!r} is not loopback; refused (I5)")
        if isinstance(self.port, bool) or not isinstance(self.port, int) or not (0 < self.port < 65536):
            raise SessionError(f"session port must be an integer in 1..65535, got {self.port!r}")
        if not isinstance(self.model_files, tuple) or not self.model_files:
            raise SessionError("session model_files must be a non-empty tuple")
        seen: set[str] = set()
        for entry in self.model_files:
            if not isinstance(entry, ModelFileRef):
                raise SessionError("session model_files entries must be ModelFileRef")
            entry.validate()
            if entry.path in seen:
                raise SessionError(f"session model_files duplicates path {entry.path!r}")
            seen.add(entry.path)
        if not isinstance(self.started_at, str) or not self.started_at.strip():
            raise SessionError("session started_at must be a non-empty string")
        if (
            not isinstance(self.startup_stdout_sha256, str)
            or _SHA256.fullmatch(self.startup_stdout_sha256) is None
        ):
            raise SessionError("session startup_stdout_sha256 must be a 64-hex sha256")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "study": self.study,
            "session_id": self.session_id,
            "binary_path": self.binary_path,
            "binary_sha256": self.binary_sha256,
            "argv": list(self.argv),
            "pid": self.pid,
            "host": self.host,
            "port": self.port,
            "model_files": [{"path": f.path, "sha256": f.sha256} for f in self.model_files],
            "started_at": self.started_at,
            "startup_stdout_sha256": self.startup_stdout_sha256,
        }

    @staticmethod
    def from_json(document: Mapping[str, object]) -> "SessionReceipt":
        if not isinstance(document, Mapping):
            raise SessionError("session receipt document must be a JSON object")
        required = {
            "schema", "study", "session_id", "binary_path", "binary_sha256", "argv",
            "pid", "host", "port", "model_files", "started_at", "startup_stdout_sha256",
        }
        if set(document) != required:
            raise SessionError(
                f"session receipt must have exact keys {sorted(required)}, got {sorted(document)}"
            )
        argv = document["argv"]
        if not isinstance(argv, list):
            raise SessionError("session receipt argv must be a list")
        model_files = document["model_files"]
        if not isinstance(model_files, list):
            raise SessionError("session receipt model_files must be a list")
        refs = []
        for entry in model_files:
            if not isinstance(entry, Mapping) or set(entry) != {"path", "sha256"}:
                raise SessionError(
                    "session receipt model_files entries must have exact path/sha256 keys"
                )
            refs.append(ModelFileRef(path=entry["path"], sha256=entry["sha256"]))
        return SessionReceipt(
            schema=document["schema"],
            study=document["study"],
            session_id=document["session_id"],
            binary_path=document["binary_path"],
            binary_sha256=document["binary_sha256"],
            argv=tuple(argv),
            pid=document["pid"],
            host=document["host"],
            port=document["port"],
            model_files=tuple(refs),
            started_at=document["started_at"],
            startup_stdout_sha256=document["startup_stdout_sha256"],
        ).validate()


def write_session_receipt(path: Path, receipt: SessionReceipt) -> Path:
    """Atomic (temp-file + ``os.replace``) write, mirroring
    ``core.attempts.AttemptHandle._write``. Session receipts are RUN
    artifacts (live under the run directory, outside the repo) -- this
    function never writes anywhere inside the study tree by itself."""

    receipt.validate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{time.monotonic_ns()}")
    raw = json.dumps(receipt.as_json(), ensure_ascii=False, sort_keys=True, indent=2)
    try:
        tmp.write_text(raw, encoding="utf-8", newline="\n")
        os.replace(tmp, path)
    except OSError as error:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise SessionError(f"cannot persist session receipt {path}: {error}") from error
    return path


def read_session_receipt(path: Path) -> SessionReceipt:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SessionError(f"cannot read session receipt {path}: {error}") from error
    return SessionReceipt.from_json(document)


def load_runtime_receipt(path: Path) -> Mapping[str, object]:
    """Read the committed runtime receipt (``docs/receipts/runtime.json``)
    as plain JSON. This module never writes it -- it is the authority for
    the pinned binary path/hash and GGUF identity, read-only here."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SessionError(f"cannot read runtime receipt {path}: {error}") from error
    if not isinstance(document, Mapping):
        raise SessionError(f"runtime receipt {path} must be a JSON object")
    return document


# ---------------------------------------------------------------------------
# Runtime-receipt-bound verification (I5's substance: hash agreement).
# ---------------------------------------------------------------------------


def _pinned_binary(runtime_receipt: Mapping[str, object]) -> tuple[str, str]:
    llama_cpp = runtime_receipt.get("llama_cpp")
    if not isinstance(llama_cpp, Mapping):
        raise SessionError("runtime receipt lacks a llama_cpp mapping")
    path = llama_cpp.get("binary_path")
    sha = llama_cpp.get("binary_sha256")
    if not isinstance(path, str) or not path:
        raise SessionError("runtime receipt llama_cpp.binary_path must be a non-empty string")
    if not isinstance(sha, str) or _SHA256.fullmatch(sha) is None:
        raise SessionError("runtime receipt llama_cpp.binary_sha256 must be a 64-hex sha256")
    return path, sha


def _pinned_model_files(runtime_receipt: Mapping[str, object]) -> tuple[ModelFileRef, ...]:
    files = runtime_receipt.get("gguf_files")
    if not isinstance(files, list) or not files:
        raise SessionError("runtime receipt lacks a non-empty gguf_files list")
    refs = []
    for entry in files:
        if not isinstance(entry, Mapping):
            raise SessionError("runtime receipt gguf_files entries must be mappings")
        path = entry.get("path")
        sha = entry.get("sha256")
        if not isinstance(path, str) or not path:
            raise SessionError("runtime receipt gguf_files[*].path must be a non-empty string")
        if not isinstance(sha, str) or _SHA256.fullmatch(sha) is None:
            raise SessionError("runtime receipt gguf_files[*].sha256 must be a 64-hex sha256")
        refs.append(ModelFileRef(path=path, sha256=sha))
    return tuple(refs)


def verify_against_runtime_receipt(
    session: SessionReceipt, runtime_receipt: Mapping[str, object]
) -> SessionReceipt:
    """I5 defense-in-depth: even a hand-built ``SessionReceipt`` (bypassing
    ``start_session``/``attach_session`` entirely) is refused here unless its
    binary AND model-file identity are EXACTLY the runtime receipt's pinned
    set. Called by both ``attach_session`` and
    ``core.model.LlamaServerTransport`` -- the same object every model touch
    already re-hashes at gate-open time, read here, never modified."""

    session.validate()
    pinned_path, pinned_sha = _pinned_binary(runtime_receipt)
    if session.binary_path != pinned_path or session.binary_sha256 != pinned_sha:
        raise SessionError(
            f"session {session.session_id!r} binary identity "
            f"{session.binary_path!r}:{session.binary_sha256[:12]}... does not match the "
            f"runtime receipt's pinned binary {pinned_path!r}:{pinned_sha[:12]}...; refused (I5)"
        )
    pinned_files = {(entry.path, entry.sha256) for entry in _pinned_model_files(runtime_receipt)}
    session_files = {(entry.path, entry.sha256) for entry in session.model_files}
    if session_files != pinned_files:
        raise SessionError(
            f"session {session.session_id!r} model file set does not match the runtime "
            "receipt's pinned GGUF files; refused (I5)"
        )
    return session


# ---------------------------------------------------------------------------
# Safe-path + hashing helpers (deliberately NOT imported from contracts.py --
# an independent rail, same discipline core.model's media-confinement helpers
# already follow relative to contracts.py's).
# ---------------------------------------------------------------------------


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SessionError(f"{label} must be a non-empty relative path")
    if "\\" in value or value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise SessionError(f"{label} must be a relative POSIX path, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SessionError(f"{label} contains empty or traversal segments: {value!r}")
    return value


def _resolve_under(root: Path, relative: str, label: str, *, must_exist: bool) -> Path:
    _safe_relative(relative, label)
    try:
        root_resolved = Path(root).resolve(strict=True)
    except OSError as error:
        raise SessionError(f"{label}: controlled root {root} is unavailable: {error}") from error
    candidate = root_resolved / relative
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as error:
        raise SessionError(f"{label}: cannot resolve {candidate}: {error}") from error
    if not resolved.is_relative_to(root_resolved):
        raise SessionError(f"{label} escapes its controlled root {root}: {relative!r}")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise SessionError(f"cannot read {path}: {error}") from error
    return digest.hexdigest()


def _iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _model_file_argv(data_root: Path, model_files: tuple[ModelFileRef, ...]) -> list[str]:
    """Build ``-m <main>`` / ``--mmproj <mmproj>`` flags from the runtime
    receipt's GGUF set, classifying by filename (the real receipt's two
    entries are the main Q8_0 shard and an ``mmproj-``-prefixed file). Each
    referenced file must exist under ``data_root`` (a cheap existence check,
    NOT a re-hash -- the multi-GB GGUF re-hash is the gate's job, already
    done before a session is ever started)."""

    mmproj = [entry for entry in model_files if "mmproj" in Path(entry.path).name.lower()]
    primary = [entry for entry in model_files if entry not in mmproj]
    argv: list[str] = []
    for entry in primary:
        resolved = _resolve_under(data_root, entry.path, "runtime gguf_files path", must_exist=True)
        argv.extend(["-m", str(resolved)])
    for entry in mmproj:
        resolved = _resolve_under(data_root, entry.path, "runtime gguf_files path", must_exist=True)
        argv.extend(["--mmproj", str(resolved)])
    return argv


# ---------------------------------------------------------------------------
# PID liveness (cross-platform).
# ---------------------------------------------------------------------------

if os.name == "nt":  # pragma: sys-platform
    import ctypes
    import ctypes.wintypes as _wintypes

    _kernel32 = ctypes.windll.kernel32
    _kernel32.OpenProcess.restype = _wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [_wintypes.DWORD, _wintypes.BOOL, _wintypes.DWORD]
    _kernel32.GetExitCodeProcess.argtypes = [_wintypes.HANDLE, ctypes.POINTER(_wintypes.DWORD)]
    _kernel32.GetExitCodeProcess.restype = _wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [_wintypes.HANDLE]
    _kernel32.CloseHandle.restype = _wintypes.BOOL
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        _wintypes.HANDLE, _wintypes.DWORD, _wintypes.LPWSTR, ctypes.POINTER(_wintypes.DWORD)
    ]
    _kernel32.QueryFullProcessImageNameW.restype = _wintypes.BOOL
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259

    # T5 fix-2 (socket-ownership binding): GetExtendedTcpTable with
    # TCP_TABLE_OWNER_PID_LISTENER maps every listening TCP port to its
    # owning pid in one syscall-ish call -- the Windows equivalent of
    # parsing /proc/net/tcp + scanning /proc/<pid>/fd on POSIX.
    _iphlpapi = ctypes.windll.iphlpapi
    _iphlpapi.GetExtendedTcpTable.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(_wintypes.DWORD),
        _wintypes.BOOL,
        _wintypes.ULONG,
        ctypes.c_int,
        _wintypes.ULONG,
    ]
    _iphlpapi.GetExtendedTcpTable.restype = _wintypes.DWORD
    _AF_INET = 2
    _AF_INET6 = 23
    _TCP_TABLE_OWNER_PID_LISTENER = 3
    _ERROR_INSUFFICIENT_BUFFER = 122

    class _MibTcpRowOwnerPid(ctypes.Structure):
        _fields_ = [
            ("dwState", ctypes.c_ulong),
            ("dwLocalAddr", ctypes.c_ulong),
            ("dwLocalPort", ctypes.c_ulong),
            ("dwRemoteAddr", ctypes.c_ulong),
            ("dwRemotePort", ctypes.c_ulong),
            ("dwOwningPid", ctypes.c_ulong),
        ]

    class _MibTcp6RowOwnerPid(ctypes.Structure):
        _fields_ = [
            ("ucLocalAddr", ctypes.c_ubyte * 16),
            ("dwLocalScopeId", ctypes.c_ulong),
            ("dwLocalPort", ctypes.c_ulong),
            ("ucRemoteAddr", ctypes.c_ubyte * 16),
            ("dwRemoteScopeId", ctypes.c_ulong),
            ("dwRemotePort", ctypes.c_ulong),
            ("dwState", ctypes.c_ulong),
            ("dwOwningPid", ctypes.c_ulong),
        ]


def _pid_alive(pid: int) -> bool:
    if os.name == "nt":  # pragma: sys-platform
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = _wintypes.DWORD()
            if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == _STILL_ACTIVE
        finally:
            _kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists, owned by someone else -- still a live process.
        return True
    except OSError:
        return False
    return True


def _process_image_path(pid: int) -> Path:
    """Resolve the ACTUAL executable image the OS loaded for a running
    process -- the fact ``_pid_alive`` cannot tell you. Liveness alone proves
    nothing: ANY live process (this very pytest interpreter included)
    satisfies ``_pid_alive``, which is exactly the gap a forged
    ``SessionReceipt`` (correct binary_path/binary_sha256/model_files copied
    verbatim from the PUBLIC runtime receipt, but naming an unrelated live
    pid) exploits. Fails closed (:class:`SessionError`) if the image cannot
    be determined at all -- permissions, a raced-away pid, or a deleted-on-
    disk image are all refusals, never silent passes."""

    if os.name == "nt":  # pragma: sys-platform
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            raise SessionError(
                f"cannot open pid {pid} to resolve its executable image; refused (I5)"
            )
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            size = _wintypes.DWORD(len(buffer))
            if not _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                raise SessionError(
                    f"cannot resolve executable image for pid {pid}; refused (I5)"
                )
            return Path(buffer.value)
        finally:
            _kernel32.CloseHandle(handle)
    exe_link = Path(f"/proc/{pid}/exe")
    try:
        target = os.readlink(exe_link)
    except OSError as error:
        raise SessionError(
            f"cannot resolve executable image for pid {pid} via {exe_link}: {error}; "
            "refused (I5: liveness alone proves nothing)"
        ) from error
    if target.endswith(" (deleted)"):
        raise SessionError(
            f"pid {pid}'s executable image {target!r} was deleted from disk after "
            "exec; cannot prove identity against a file that no longer exists there"
        )
    return Path(target)


def _verify_pid_runs_pinned_binary(
    pid: int, runtime_root: Path, runtime_receipt: Mapping[str, object]
) -> None:
    """I5's actual substance for a PID-based claim (the reviewer-demonstrated
    gap this closes): resolve the OS-reported executable image backing
    ``pid`` RIGHT NOW and require it to be literally the pinned binary file
    -- re-hashed for certainty, not merely path-equal -- rather than trusting
    that a live pid plus a self-reported ``binary_path`` string means
    anything at all. A forged ``SessionReceipt`` can copy the correct
    ``binary_path``/``binary_sha256`` verbatim from the (public, committed)
    runtime receipt and name ANY live pid; only this check catches that."""

    pinned_relpath, pinned_sha = _pinned_binary(runtime_receipt)
    expected = _resolve_under(
        runtime_root, pinned_relpath, "runtime llama_cpp.binary_path", must_exist=True
    )
    image = _process_image_path(pid)
    try:
        image_resolved = image.resolve(strict=True)
    except OSError as error:
        raise SessionError(
            f"pid {pid}'s executable image {image} could not be resolved: {error}; "
            "refused (I5: process identity must be provable)"
        ) from error
    if image_resolved != expected:
        raise SessionError(
            f"pid {pid} is running {image_resolved}, not the pinned binary {expected}; "
            "refused (I5: PID liveness alone proves nothing -- a session receipt "
            "naming an unrelated live process must be rejected)"
        )
    actual_sha = _sha256_file(image_resolved)
    if actual_sha != pinned_sha:
        raise SessionError(
            f"pid {pid}'s executable image {image_resolved} hashes to "
            f"{actual_sha[:12]}... but the runtime receipt pins {pinned_sha[:12]}...; "
            "refused (I5)"
        )


# ---------------------------------------------------------------------------
# Socket-ownership binding (T5 fix-2): binary/PID identity alone does not
# prove the session's process is the one LISTENING on (host, port) --
# session.host/port/argv are self-declared receipt fields, and
# _verify_pid_runs_pinned_binary only proves "this pid runs the pinned
# binary somewhere", not "this pid owns THIS listening socket". A forged
# receipt can name a second, genuinely live, genuinely pinned-binary
# process that simply is not bound to the target port at all. This
# resolves the REAL kernel-level owner of the listening socket on `port`
# and requires it to equal `pid`, independent of anything the receipt or
# the transport's own base_url claims.
# ---------------------------------------------------------------------------

_SOCKET_FD_PATTERN = re.compile(r"socket:\[(\d+)\]\Z")
_PROC_NET_TCP_LISTEN_STATE = "0A"


def _listen_inodes_for_port(path: Path, port: int) -> set[int]:
    """Parse a ``/proc/net/tcp``- or ``/proc/net/tcp6``-shaped file for
    LISTEN-state socket inodes bound to ``port``. A missing file (e.g. IPv6
    disabled) yields an empty set -- a legitimate system configuration, not
    a failure; any OTHER read failure fails closed (:class:`SessionError`),
    never silently yielding an empty (falsely permissive-looking) set."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return set()
    except OSError as error:
        raise SessionError(
            f"cannot read {path} to determine socket ownership: {error}; refused "
            "(I5: socket ownership must be provable)"
        ) from error
    inodes: set[int] = set()
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 10:
            continue
        local_address, state, inode_field = fields[1], fields[3], fields[9]
        if state != _PROC_NET_TCP_LISTEN_STATE:
            continue
        try:
            _, hex_port = local_address.split(":")
            local_port = int(hex_port, 16)
            inode = int(inode_field)
        except ValueError:
            continue
        if local_port == port:
            inodes.add(inode)
    return inodes


def _pid_owns_any_inode(pid: int, inodes: set[int]) -> bool:
    """Scan ``/proc/<pid>/fd/*`` for a ``socket:[<inode>]`` symlink target
    matching one of ``inodes``. Fails closed if the fd directory cannot be
    enumerated at all (a process whose fds this process cannot read can
    never prove it owns anything -- refuse, do not assume innocence)."""

    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        entries = list(fd_dir.iterdir())
    except OSError as error:
        raise SessionError(
            f"cannot enumerate open file descriptors for pid {pid} ({fd_dir}): "
            f"{error}; refused (I5: socket ownership must be provable)"
        ) from error
    for entry in entries:
        try:
            target = os.readlink(entry)
        except OSError:
            continue  # fd raced away between listdir and readlink -- not fatal
        match = _SOCKET_FD_PATTERN.match(target)
        if match and int(match.group(1)) in inodes:
            return True
    return False


def _posix_verify_pid_owns_listening_socket(pid: int, port: int) -> None:
    inodes: set[int] = set()
    for relpath in ("/proc/net/tcp", "/proc/net/tcp6"):
        inodes |= _listen_inodes_for_port(Path(relpath), port)
    if not inodes:
        raise SessionError(
            f"no LISTEN socket found for port {port} in /proc/net/tcp(6); refused "
            "(I5: socket ownership must be provable)"
        )
    if not _pid_owns_any_inode(pid, inodes):
        raise SessionError(
            f"pid {pid} does not own the listening socket on port {port}; refused "
            "(I5: PID/binary identity alone does not prove the session's process "
            "is the one actually listening on this endpoint)"
        )


def _windows_tcp_table_owners(address_family: int, row_type: type) -> dict[int, int]:
    """port -> owning pid, for one address family's LISTENER-only TCP table
    (``GetExtendedTcpTable`` with ``TCP_TABLE_OWNER_PID_LISTENER`` -- the
    table already contains listening sockets only, no state filtering
    needed). Retries a bounded number of times on the standard
    grow-between-calls race (first call learns the required size, second
    call can still return ``ERROR_INSUFFICIENT_BUFFER`` if the table grew
    in between)."""

    size = _wintypes.DWORD(0)
    for _attempt in range(4):
        probe = _iphlpapi.GetExtendedTcpTable(
            None, ctypes.byref(size), False, address_family, _TCP_TABLE_OWNER_PID_LISTENER, 0
        )
        if probe == 0:
            return {}
        if probe != _ERROR_INSUFFICIENT_BUFFER:
            raise SessionError(
                f"GetExtendedTcpTable size query failed (error {probe}); refused "
                "(I5: socket ownership must be provable)"
            )
        buffer = ctypes.create_string_buffer(size.value)
        result = _iphlpapi.GetExtendedTcpTable(
            buffer, ctypes.byref(size), False, address_family, _TCP_TABLE_OWNER_PID_LISTENER, 0
        )
        if result == 0:
            num_entries = ctypes.c_ulong.from_buffer(buffer, 0).value
            row_size = ctypes.sizeof(row_type)
            offset = ctypes.sizeof(ctypes.c_ulong)
            owners: dict[int, int] = {}
            for index in range(num_entries):
                row = row_type.from_buffer(buffer, offset + index * row_size)
                local_port = socket.ntohs(row.dwLocalPort & 0xFFFF)
                owners[local_port] = row.dwOwningPid
            return owners
        if result == _ERROR_INSUFFICIENT_BUFFER:
            continue
        raise SessionError(
            f"GetExtendedTcpTable failed (error {result}); refused (I5: socket "
            "ownership must be provable)"
        )
    raise SessionError(
        "GetExtendedTcpTable did not stabilize after repeated retries; refused "
        "(I5: socket ownership must be provable)"
    )


def _windows_verify_pid_owns_listening_socket(pid: int, port: int) -> None:
    owners: dict[int, int] = {}
    owners.update(_windows_tcp_table_owners(_AF_INET, _MibTcpRowOwnerPid))
    owners.update(_windows_tcp_table_owners(_AF_INET6, _MibTcp6RowOwnerPid))
    owner_pid = owners.get(port)
    if owner_pid is None:
        raise SessionError(
            f"no LISTEN socket found for port {port}; refused (I5: socket "
            "ownership must be provable)"
        )
    if owner_pid != pid:
        raise SessionError(
            f"port {port} is owned by pid {owner_pid}, not the session's pid "
            f"{pid}; refused (I5: PID/binary identity alone does not prove the "
            "session's process is the one actually listening on this endpoint)"
        )


def _verify_pid_owns_listening_socket(pid: int, host: str, port: int) -> None:
    """Dispatch to the platform-specific socket-ownership check.

    ``host`` is accepted for API symmetry with the rest of I5's checks and
    documents intent, but is deliberately NOT used to filter by local
    address: ``require_loopback`` already restricts every session's ``host``
    to the fixed, tiny loopback set (``127.0.0.1``/``::1``/``localhost``),
    so the port-plus-pid-ownership binding this function enforces already
    closes the exploit (a process not bound to the claimed port at all, or
    bound to it under a different pid) without needing address-level
    matching too.
    """

    if os.name == "nt":  # pragma: sys-platform
        _windows_verify_pid_owns_listening_socket(pid, port)
    else:
        _posix_verify_pid_owns_listening_socket(pid, port)


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


# ---------------------------------------------------------------------------
# Bounded, non-blocking-to-the-caller startup stdout capture.
# ---------------------------------------------------------------------------


def _capture_startup_stdout(
    process: "subprocess.Popen[bytes]", *, max_bytes: int, timeout_seconds: float
) -> bytes:
    """Read up to ``max_bytes`` of the child's stdout, for up to
    ``timeout_seconds`` total -- WITHOUT waiting for the child to exit (a
    resident server never does). A background daemon thread does the actual
    blocking read; the caller only ever waits its own bounded budget."""

    chunks: "queue.Queue[bytes]" = queue.Queue()

    def _reader() -> None:
        stream = process.stdout
        if stream is None:
            chunks.put(b"")
            return
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    chunks.put(b"")
                    return
                chunks.put(chunk)
        except (OSError, ValueError):
            chunks.put(b"")

    threading.Thread(target=_reader, daemon=True).start()
    collected = bytearray()
    deadline = time.monotonic() + timeout_seconds
    while len(collected) < max_bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            chunk = chunks.get(timeout=remaining)
        except queue.Empty:
            break
        if not chunk:
            break
        collected.extend(chunk)
    return bytes(collected[:max_bytes])


# ---------------------------------------------------------------------------
# The two sanctioned ways to obtain a SessionReceipt.
# ---------------------------------------------------------------------------


def start_session(
    *,
    runtime_root: Path,
    data_root: Path,
    runtime_receipt: Mapping[str, object],
    host: str,
    port: int,
    session_id: str,
    extra_argv: Sequence[str] = (),
    startup_timeout_seconds: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    startup_max_bytes: int = DEFAULT_STARTUP_MAX_BYTES,
    receipt_path: Path | None = None,
    popen: Callable[..., "subprocess.Popen[bytes]"] = subprocess.Popen,
    now: Callable[[], float] = time.time,
) -> SessionReceipt:
    """Spawn the runtime-receipt-pinned llama.cpp binary and return the
    :class:`SessionReceipt` that binds this run to the EXACT process it
    started.

    Fail-closed, before any process is spawned: ``host``/``port`` must be
    loopback (I5), and the binary at the receipt's pinned relative path must
    re-hash to EXACTLY the receipt's pinned sha256 -- a binary swapped on
    disk between gate-open time and spawn time is refused here, never
    silently executed. This is the one place besides the gate itself that
    re-hashes real bytes (the binary only -- a ~18 KB stub -- never the
    multi-GB GGUF files, whose re-hash the gate already performed).
    """

    require_loopback(f"http://{_bracketed(host)}:{port}")
    pinned_path, pinned_sha = _pinned_binary(runtime_receipt)
    binary = _resolve_under(runtime_root, pinned_path, "runtime llama_cpp.binary_path", must_exist=True)
    if not binary.is_file():
        raise SessionError(f"pinned binary is not a regular file: {binary}")
    actual_sha = _sha256_file(binary)
    if actual_sha != pinned_sha:
        raise SessionError(
            f"spawn refused: {binary} hashes to {actual_sha[:12]}... but the runtime "
            f"receipt pins {pinned_sha[:12]}... (binary swapped on disk since the gate "
            "verified it; I5)"
        )
    model_files = _pinned_model_files(runtime_receipt)
    model_argv = _model_file_argv(Path(data_root), model_files)
    argv = [str(binary), "--host", host, "--port", str(port), *model_argv, *list(extra_argv)]

    started_wall = now()
    process = popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=str(binary.parent))
    stdout_bytes = _capture_startup_stdout(
        process, max_bytes=startup_max_bytes, timeout_seconds=startup_timeout_seconds
    )
    receipt = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id=session_id,
        binary_path=pinned_path,
        binary_sha256=actual_sha,
        argv=tuple(argv),
        pid=process.pid,
        host=host,
        port=port,
        model_files=model_files,
        started_at=_iso(started_wall),
        startup_stdout_sha256=hashlib.sha256(stdout_bytes).hexdigest(),
    ).validate()
    if receipt_path is not None:
        write_session_receipt(receipt_path, receipt)
    return receipt


def attach_session(
    receipt_path: Path, *, runtime_receipt: Mapping[str, object], runtime_root: Path
) -> SessionReceipt:
    """Bind to an already-resident server via an on-disk session receipt.

    Valid ONLY if: the receipt exists and is well-formed; its host is
    loopback; and (:func:`assert_session_alive`) its declared binary/model
    identity matches the runtime receipt's pinned set, its pid names a
    process that is alive RIGHT NOW, AND -- the fix for the CRITICAL gap an
    independent reviewer demonstrated end-to-end (a from-scratch forged
    ``SessionReceipt`` copying the correct, PUBLIC binary_path/binary_sha256
    but naming the reviewer's own live, unrelated pid previously passed
    every check this function ran) -- that pid's ACTUAL OS-reported
    executable image is literally the pinned binary file. Anything else
    fails closed: there is no other way to obtain a ``SessionReceipt`` for a
    server this process did not itself spawn.
    """

    receipt = read_session_receipt(receipt_path)
    require_loopback(f"http://{_bracketed(receipt.host)}:{receipt.port}")
    assert_session_alive(receipt, runtime_receipt, runtime_root)
    return receipt
