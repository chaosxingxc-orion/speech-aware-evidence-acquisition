"""``SessionReceipt``/``ModelFileRef`` value types, their read/write, and
runtime-receipt-bound verification (I5's substance: hash agreement).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ...contracts import RUN_ID_PATTERN as _ID_PATTERN
from ...contracts import STUDY_SLUG
from . import SessionError, _LOOPBACK_LITERALS
from .paths import _safe_relative

SESSION_RECEIPT_SCHEMA = "saea-session-receipt-v1"
SESSION_RECEIPT_SCHEMA_V2 = "saea-session-receipt-v2"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


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
    # Persisted server-log path (2026-08-09 finding: llama-server's own
    # stdout/stderr was captured for the startup window only, then thrown
    # away -- hours of server output were unrecoverable after a mid-run
    # stall). Optional/defaulted: a dry-run smoke receipt and every
    # pre-existing hand-built receipt in this module's own test suite spawn
    # no real process at all, so None is a legitimate "no log for this
    # session" answer, not a missing field. Set only by start_session, from
    # exactly the path (if any) its caller asked the spawned process's
    # combined stdout/stderr to be persisted to -- never independently
    # re-derived here.
    server_log_path: str | None = None
    # V2 makes the two-stage speech-feature boundary explicit. Historical
    # V1 receipts remain byte-compatible and read as ``legacy``.
    role: str = "legacy"
    server_env_keys: tuple[str, ...] = ()

    def validate(self) -> "SessionReceipt":
        if self.schema not in (SESSION_RECEIPT_SCHEMA, SESSION_RECEIPT_SCHEMA_V2):
            raise SessionError(
                "session receipt schema must be "
                f"{SESSION_RECEIPT_SCHEMA!r} or {SESSION_RECEIPT_SCHEMA_V2!r}, "
                f"got {self.schema!r}"
            )
        if self.schema == SESSION_RECEIPT_SCHEMA and self.role != "legacy":
            raise SessionError("session receipt v1 role must be 'legacy'")
        if self.schema == SESSION_RECEIPT_SCHEMA_V2 and self.role not in {
            "preprocess",
            "inference",
        }:
            raise SessionError(
                "session receipt v2 role must be 'preprocess' or 'inference'"
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
        if self.server_log_path is not None and (
            not isinstance(self.server_log_path, str) or not self.server_log_path.strip()
        ):
            raise SessionError("session server_log_path must be a non-empty string or None")
        if (
            not isinstance(self.server_env_keys, tuple)
            or not all(isinstance(key, str) and key for key in self.server_env_keys)
            or len(set(self.server_env_keys)) != len(self.server_env_keys)
        ):
            raise SessionError(
                "session server_env_keys must be a tuple of unique non-empty strings"
            )
        if self.role == "inference":
            forbidden_argv = [
                part
                for part in self.argv
                if "mmproj" in part.lower() and part != "--no-mmproj"
            ]
            if forbidden_argv:
                raise SessionError(
                    "inference session argv must not mention mmproj artifacts or flags: "
                    f"{forbidden_argv!r}"
                )
            if "--no-mmproj" not in self.argv:
                raise SessionError("inference session argv must include explicit --no-mmproj")
            if any("mmproj" in Path(entry.path).name.lower() for entry in self.model_files):
                raise SessionError("inference session model_files must not contain mmproj")
            if "LLAMA_MTMD_FEAT_CACHE_DIR" in self.server_env_keys:
                raise SessionError(
                    "inference session must not set LLAMA_MTMD_FEAT_CACHE_DIR"
                )
        if self.role == "preprocess" and not any(
            "mmproj" in Path(entry.path).name.lower() for entry in self.model_files
        ):
            raise SessionError("preprocess session must bind an mmproj model file")
        return self

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {
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
            "server_log_path": self.server_log_path,
        }
        if self.schema == SESSION_RECEIPT_SCHEMA_V2:
            document["role"] = self.role
            document["server_env_keys"] = list(self.server_env_keys)
        return document

    @staticmethod
    def from_json(document: Mapping[str, object]) -> "SessionReceipt":
        if not isinstance(document, Mapping):
            raise SessionError("session receipt document must be a JSON object")
        required = {
            "schema", "study", "session_id", "binary_path", "binary_sha256", "argv",
            "pid", "host", "port", "model_files", "started_at", "startup_stdout_sha256",
            "server_log_path",
        }
        if document.get("schema") == SESSION_RECEIPT_SCHEMA_V2:
            required |= {"role", "server_env_keys"}
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
        server_env_keys = document.get("server_env_keys", [])
        if not isinstance(server_env_keys, list):
            raise SessionError("session receipt server_env_keys must be a list")
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
            server_log_path=document["server_log_path"],
            role=document.get("role", "legacy"),
            server_env_keys=tuple(server_env_keys),
        ).validate()


def archived_session_receipt_path(path: Path, sha256: str) -> Path:
    """The content-addressed store entry for receipt bytes whose sha256 is ``sha256``.

    Every receipt :func:`write_session_receipt` writes at ``path`` is kept at
    ``<path>.archive/<sha256>.json``. An entry is created exclusively, is never
    overwritten and is never moved; its name is the hash of its bytes. A bundle
    pins a resident receipt by path AND hash, so the hash resolves here after
    the resident file has been replaced by a restart of the same session id.
    """
    if not isinstance(sha256, str) or _SHA256.fullmatch(sha256) is None:
        raise SessionError("session receipt archive requires a 64-hex sha256")
    path = Path(path)
    return path.parent / f"{path.name}.archive" / f"{sha256}.json"


def store_session_receipt_bytes(path: Path, raw: bytes) -> Path:
    """Append ``raw`` to the content-addressed store beside ``path``; idempotent.

    The entry is created with ``O_EXCL`` and read-only permissions, fsynced,
    and its directory fsynced, so it exists durably before any caller replaces
    the resident file. An existing entry with identical bytes is accepted as
    is; an existing entry with different bytes is refused as a collision or
    tampering and is left untouched.
    """
    digest = hashlib.sha256(raw).hexdigest()
    archive = archived_session_receipt_path(path, digest)
    try:
        archive.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
        except FileExistsError:
            if archive.read_bytes() != raw:
                raise SessionError(
                    f"session receipt archive collision or tampering at {archive}"
                ) from None
            return archive
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        except BaseException:
            archive.unlink(missing_ok=True)
            raise
        # The store entry must be durable before the resident file changes.
        directory_fd = os.open(archive.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except OSError as error:
        raise SessionError(f"cannot store session receipt bytes for {path}: {error}") from error
    return archive


def _archive_existing_session_receipt(path: Path) -> None:
    """Durably retain exact prior bytes before replacing a resident receipt.

    Receipts written before the store existed (commit 46e03f3d, 2026-09-24)
    are only resident; this keeps them when their session id restarts.
    """
    try:
        prior = path.read_bytes()
    except FileNotFoundError:
        return
    except OSError as error:
        raise SessionError(f"cannot archive prior session receipt {path}: {error}") from error
    store_session_receipt_bytes(path, prior)


def resolve_pinned_session_receipt(path: Path, sha256: str) -> bytes:
    """Return the exact receipt bytes a bundle pinned as ``{path, sha256}``.

    The resident file answers when it still holds the pinned bytes; otherwise
    the content-addressed store entry for ``sha256`` must exist and must hash
    to its own name. Nothing else is consulted and nothing is written.
    """
    expected = archived_session_receipt_path(path, sha256)
    path = Path(path)
    resident_hash = None
    try:
        resident = path.read_bytes()
    except OSError:
        resident = None
    if resident is not None:
        resident_hash = hashlib.sha256(resident).hexdigest()
        if resident_hash == sha256:
            return resident
    try:
        stored = expected.read_bytes()
    except FileNotFoundError:
        held = (
            f"holds {resident_hash[:12]}..." if resident_hash is not None else "is absent"
        )
        raise SessionError(
            f"pinned session receipt {sha256[:12]}... resolves nowhere: the resident "
            f"{path} {held} and the content-addressed store has no {expected}"
        ) from None
    except OSError as error:
        raise SessionError(
            f"cannot read session receipt store entry {expected}: {error}"
        ) from error
    if hashlib.sha256(stored).hexdigest() != sha256:
        raise SessionError(
            f"session receipt store entry {expected} does not hash to its name (tampered)"
        )
    return stored


def write_session_receipt(path: Path, receipt: SessionReceipt) -> Path:
    """Atomic (temp-file + ``os.replace``) write, mirroring
    ``core.attempts.AttemptHandle._write``. Session receipts are RUN
    artifacts (live under the run directory, outside the repo) -- this
    function never writes anywhere inside the study tree by itself.

    Before the resident file changes, the NEW bytes enter the
    content-addressed store (so every receipt ever written resolves by hash
    for as long as the store is kept) and the PRIOR resident bytes are stored
    too (receipts written before the store existed).
    """

    receipt.validate()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{time.monotonic_ns()}")
    raw = json.dumps(receipt.as_json(), ensure_ascii=False, sort_keys=True, indent=2)
    try:
        tmp.write_text(raw, encoding="utf-8", newline="\n")
        store_session_receipt_bytes(path, raw.encode("utf-8"))
        _archive_existing_session_receipt(path)
        os.replace(tmp, path)
    except (OSError, SessionError) as error:
        try:
            tmp.unlink()
        except OSError:
            pass
        if isinstance(error, SessionError):
            raise
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
    pinned_refs = _pinned_model_files(runtime_receipt)
    if session.role == "inference":
        pinned_refs = tuple(
            entry
            for entry in pinned_refs
            if "mmproj" not in Path(entry.path).name.lower()
        )
    pinned_files = {(entry.path, entry.sha256) for entry in pinned_refs}
    session_files = {(entry.path, entry.sha256) for entry in session.model_files}
    if session_files != pinned_files:
        raise SessionError(
            f"session {session.session_id!r} model file set does not match the runtime "
            "receipt's pinned GGUF files; refused (I5)"
        )
    return session
