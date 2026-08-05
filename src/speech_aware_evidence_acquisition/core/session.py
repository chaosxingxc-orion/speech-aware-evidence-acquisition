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
    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    _STILL_ACTIVE = 259


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


def attach_session(receipt_path: Path, *, runtime_receipt: Mapping[str, object]) -> SessionReceipt:
    """Bind to an already-resident server via an on-disk session receipt.

    Valid ONLY if: the receipt exists and is well-formed; its binary AND
    model-file identity match the runtime receipt's pinned set (I5); its pid
    names a process that is alive RIGHT NOW; and its host is loopback.
    Anything else fails closed -- there is no other way to obtain a
    ``SessionReceipt`` for a server this process did not itself spawn.
    """

    receipt = read_session_receipt(receipt_path)
    verify_against_runtime_receipt(receipt, runtime_receipt)
    if not _pid_alive(receipt.pid):
        raise SessionError(
            f"session {receipt.session_id!r} pid {receipt.pid} is not a live process; "
            "attach refused (I5)"
        )
    require_loopback(f"http://{_bracketed(receipt.host)}:{receipt.port}")
    return receipt
