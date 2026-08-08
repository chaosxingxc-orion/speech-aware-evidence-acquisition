"""The two sanctioned ways to obtain a ``SessionReceipt``: ``start_session``
(spawn) and ``attach_session`` (bind to an already-resident server).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import queue
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import STUDY_SLUG
from . import SessionError, _bracketed, assert_session_alive, require_loopback
from .paths import _resolve_under, _sha256_file
from .receipt import (
    SESSION_RECEIPT_SCHEMA,
    ModelFileRef,
    SessionReceipt,
    _pinned_binary,
    _pinned_model_files,
    read_session_receipt,
    write_session_receipt,
)

DEFAULT_STARTUP_TIMEOUT_SECONDS = 5.0
DEFAULT_STARTUP_MAX_BYTES = 65536
# llama-server binds its port immediately but answers 503 until the model is
# loaded; a 30B GGUF takes minutes. 2026-08-08: the first real smoke aborted
# on exactly this, so start_session now waits for /health = 200 by default.
DEFAULT_READY_TIMEOUT_SECONDS = 1800.0
DEFAULT_READY_POLL_INTERVAL_SECONDS = 5.0


def _http_get_status(url: str, timeout_seconds: float) -> int:
    """Status code of a GET against a loopback URL (readiness probe only)."""

    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return int(error.code)


def _wait_until_ready(
    url: str,
    *,
    is_process_alive: Callable[[], bool],
    http_get_status: Callable[[str, float], int],
    timeout_seconds: float,
    poll_interval_seconds: float,
    startup_stdout_tail: bytes = b"",
) -> None:
    """Block until the spawned server answers ``url`` with HTTP 200.

    Fail-closed: the child exiting during load, or the deadline passing
    without a 200, raises :class:`SessionError` — a session receipt must
    never describe a server that cannot answer yet. Connection errors and
    non-200 statuses (llama-server answers 503 while loading) both count as
    not-ready.
    """

    deadline = time.monotonic() + timeout_seconds
    while True:
        if not is_process_alive():
            raise SessionError(
                "spawned server exited before becoming ready; startup output tail: "
                f"{startup_stdout_tail[-512:]!r}"
            )
        try:
            status = http_get_status(url, 5.0)
        except OSError:
            status = None
        if status == 200:
            return
        if time.monotonic() >= deadline:
            raise SessionError(
                f"spawned server not ready after {timeout_seconds:.0f}s "
                f"(last probe status: {status}); refusing to hand out a session "
                "receipt for a server that cannot answer"
            )
        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)


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
    ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS,
    ready_poll_interval_seconds: float = DEFAULT_READY_POLL_INTERVAL_SECONDS,
    http_get_status: Callable[[str, float], int] | None = None,
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
    if ready_timeout_seconds > 0:
        _wait_until_ready(
            f"http://{_bracketed(host)}:{port}/health",
            is_process_alive=lambda: process.poll() is None,
            http_get_status=http_get_status or _http_get_status,
            timeout_seconds=ready_timeout_seconds,
            poll_interval_seconds=ready_poll_interval_seconds,
            startup_stdout_tail=stdout_bytes,
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
