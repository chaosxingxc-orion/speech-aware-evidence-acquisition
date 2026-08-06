"""``SessionReceipt``/``ModelFileRef`` value types, their read/write, and
runtime-receipt-bound verification (I5's substance: hash agreement).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

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
