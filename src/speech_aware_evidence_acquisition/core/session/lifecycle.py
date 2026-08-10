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


class _ServerLogWriter:
    """Best-effort persistent server-log writer (Task 1, 2026-08-09 finding:
    llama-server's own combined stdout/stderr was captured for the startup
    window only, then thrown away -- hours of server output were
    unrecoverable after exactly the kind of mid-run stall that killed two
    arms). Opened once, unbuffered (``buffering=0``) so every write reaches
    disk immediately -- the whole point is an operator being able to read
    the file WHILE the server is wedged, not after the process eventually
    exits.

    Fail-open, always: a path that cannot even be opened (missing/unwritable
    parent, wrong permissions, ...) leaves this writer silently inert for
    its whole life -- ``write`` is then a no-op, never a raise. A write that
    fails after a successful open (disk full, path removed out from under
    it, ...) disables further attempts the same way. Either failure loses
    the log; neither is allowed to touch the reader thread that keeps the
    child's stdout pipe draining (module docstring above
    ``_capture_startup_stdout``) -- losing the log is acceptable, stalling
    the experiment is not.
    """

    def __init__(self, path: "Path | None") -> None:
        self._handle = None
        if path is None:
            return
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            self._handle = Path(path).open("ab", buffering=0)
        except OSError:
            self._handle = None

    def write(self, chunk: bytes) -> None:
        if self._handle is None:
            return
        try:
            self._handle.write(chunk)
        except OSError:
            self._handle = None  # stop trying after the first failure


def _capture_startup_stdout(
    process: "subprocess.Popen[bytes]",
    *,
    max_bytes: int,
    timeout_seconds: float,
    on_chunk: Callable[[bytes], None] | None = None,
) -> bytes:
    """Read up to ``max_bytes`` of the child's stdout, for up to
    ``timeout_seconds`` total -- WITHOUT waiting for the child to exit (a
    resident server never does). A background daemon thread does the actual
    blocking read; the caller only ever waits its own bounded budget.

    ``on_chunk`` (Task 1, 2026-08-09 finding): called, best-effort, with
    EVERY raw chunk the reader thread ever reads from the child's combined
    stdout/stderr -- both the chunks THIS function's own startup window
    collects below (so the startup bytes reach it too, in order, not just
    the bytes read after this function returns) and every later chunk the
    SAME thread keeps reading for the rest of the process's life (preserved
    from before this change: that continued reading is what stops the pipe
    filling and blocking the server). A raising/broken ``on_chunk`` is
    swallowed here and never stops the drain -- ``_ServerLogWriter`` above
    already fails open on its own; this is defense in depth for whatever
    else a caller might pass. Once this function's own collection window
    ends nothing reads the internal queue again, so the reader stops
    enqueuing into it (it keeps calling ``on_chunk`` regardless) -- an
    hours-long session would otherwise grow that queue unboundedly in
    memory for bytes nobody was ever going to consume.
    """

    chunks: "queue.Queue[bytes]" = queue.Queue()
    stop_enqueue = threading.Event()

    def _reader() -> None:
        stream = process.stdout
        if stream is None:
            chunks.put(b"")
            return
        try:
            while True:
                # read1, NOT read: a plain BufferedReader.read(n) on a
                # non-interactive stream (a subprocess pipe always is one)
                # blocks accumulating raw reads until it has n bytes OR the
                # child exits (io module docs) -- observed empirically
                # (2026-08-09) as a multi-second stall before ANY bytes
                # reached on_chunk, defeating the entire "flushed as
                # written, readable while the server is wedged" point of
                # the persisted log. read1 makes at most ONE underlying
                # syscall and returns whatever is available right now.
                chunk = stream.read1(4096)
                if not chunk:
                    if not stop_enqueue.is_set():
                        chunks.put(b"")
                    return
                if on_chunk is not None:
                    try:
                        on_chunk(chunk)
                    except Exception:
                        pass
                if not stop_enqueue.is_set():
                    chunks.put(chunk)
        except (OSError, ValueError):
            if not stop_enqueue.is_set():
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
    stop_enqueue.set()
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
    server_log_path: Path | None = None,
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

    ``server_log_path`` (Task 1, 2026-08-09 finding): optional; when given,
    the spawned process's combined stdout/stderr is persisted there for its
    whole life (startup bytes included, in order, flushed as written --
    ``_ServerLogWriter``/``_capture_startup_stdout``'s ``on_chunk``), so an
    operator can read the server's own output while a hung request has it
    wedged, rather than discovering only that llama-server's log was never
    kept. A log that cannot be opened/written never blocks the spawn or the
    pipe-draining thread that keeps the server itself unblocked -- it is
    simply lost (module docstring at ``_ServerLogWriter``).
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
    log_writer = _ServerLogWriter(Path(server_log_path) if server_log_path is not None else None)
    stdout_bytes = _capture_startup_stdout(
        process,
        max_bytes=startup_max_bytes,
        timeout_seconds=startup_timeout_seconds,
        on_chunk=log_writer.write,
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
        # Recorded regardless of whether the writer actually managed to open
        # the file (module docstring at _ServerLogWriter): the DECLARED
        # location, so an operator who finds it missing learns that the log
        # write failed, rather than finding no path recorded at all.
        server_log_path=str(server_log_path) if server_log_path is not None else None,
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
