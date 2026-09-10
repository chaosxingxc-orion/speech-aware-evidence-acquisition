"""The two sanctioned ways to obtain a ``SessionReceipt``: ``start_session``
(spawn) and ``attach_session`` (bind to an already-resident server).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import signal
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import STUDY_SLUG, assert_wsl_execution_environment
from . import SessionError, _bracketed, assert_session_alive, require_loopback
from .paths import _resolve_under, _sha256_file
from .process import (
    PROCESS_STATE_DEFUNCT,
    PROCESS_STATE_GONE,
    _pid_alive,
    _pid_is_defunct,
    _verify_pid_runs_pinned_binary,
)
from .receipt import (
    SESSION_RECEIPT_SCHEMA,
    SESSION_RECEIPT_SCHEMA_V2,
    ModelFileRef,
    SessionReceipt,
    _pinned_binary,
    _pinned_model_files,
    read_session_receipt,
    verify_against_runtime_receipt,
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


# ---------------------------------------------------------------------------
# ext4-first model source resolution (2026-08-16 perf fix). The pinned GGUF
# set's canonical location is $SPEECHRL_DATA_DIR (``data_root``), which on
# this host is a 9p-mounted /mnt/e path -- fine once a model is resident in
# llama-server's own memory, but a COLD-CACHE reload from that mount measured
# ~20 MB/s on 2026-08-16, costing one arm roughly 45 minutes it should never
# have spent. Bit-identical copies of both GGUFs were placed directly on the
# WSL2 ext4 filesystem (no 9p hop) at ``EXT4_MODELS_ROOT_DEFAULT``.
#
# ``_resolve_model_file_source`` prefers that ext4 copy ONLY when both (a)
# the file exists there and (b) it re-hashes to EXACTLY the receipt-pinned
# sha256 for that filename -- any miss (file absent, unreadable, or hash
# mismatch) falls back to the existing ``data_root`` resolution UNCHANGED, so
# a host without the ext4 mirror, or a stale/partial one, behaves exactly as
# before this change.
#
# Expected pins: the two hashes in ``EXT4_MODEL_SHA256_PINS`` are the SAME
# two values the runtime receipt's own ``gguf_files[*].sha256`` carries (what
# the existing ``data_root`` branch has always trusted -- gate-verified
# before any model touch is allowed, see
# ``contracts.gate_runtime_gguf._verify_gguf_files``) and the umbrella lock's
# live authority record, ``docs/datasets.lock.json`` -> ``models[]`` where
# ``name == "qwen3-omni-30b-a3b-instruct-gguf-q4km"`` -> its ``note`` field
# (prose, not a structured per-file key, so it is not machine-read from the
# lock at runtime -- see that entry for the identical two hashes quoted
# verbatim: "requant product sha256 0751c279..." for the main shard and
# "mmproj sha256 f0dfe825..." for the mmproj file). Do not hand-edit these
# constants without re-deriving them from that lock entry. They are also
# cross-checked against the runtime receipt's own per-file pin below (a
# filename whose receipt-pinned sha256 disagrees with this constant is
# refused for the ext4 fast path and falls back to data_root instead of
# silently trusting whichever value happens to be embedded here), so a drift
# between the two sources fails toward the slower-but-already-verified path,
# never toward loading an unverified file.
EXT4_MODELS_ROOT_ENV = "SAEA_EXT4_MODELS_ROOT"
EXT4_MODELS_ROOT_DEFAULT = Path("/home/chao/models/qwen3-omni-30b-a3b-instruct-gguf-q4km")
EXT4_MODEL_SHA256_PINS: Mapping[str, str] = {
    "Qwen3-Omni-30B-A3B-Instruct-Q4_K_M.gguf": (
        "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
    ),
    "mmproj-Qwen3-Omni-30B-A3B-Instruct-bf16.gguf": (
        "f0dfe825fb692d426362b1ac79678fc08daa4758f7151526cad110515f122883"
    ),
}


def _ext4_models_root() -> Path:
    """``EXT4_MODELS_ROOT_ENV`` overrides the default -- test-only in
    practice, but also lets an operator point at a differently-placed mirror
    without editing source."""

    override = os.environ.get(EXT4_MODELS_ROOT_ENV)
    return Path(override) if override else EXT4_MODELS_ROOT_DEFAULT


def _resolve_model_file_source(
    data_root: Path,
    entry: ModelFileRef,
    *,
    ext4_root: Path | None = None,
    sha256_file: Callable[[Path], str] = _sha256_file,
) -> Path:
    """Resolve ONE runtime-receipt-pinned GGUF file's real, on-disk path.

    Prefers the ext4 mirror (default :data:`EXT4_MODELS_ROOT_DEFAULT`,
    overridable via :data:`EXT4_MODELS_ROOT_ENV`) over the canonical
    ``data_root`` (/mnt/e) path -- but ONLY when ALL of: (1) this filename has
    a pinned entry in :data:`EXT4_MODEL_SHA256_PINS`; (2) that pin agrees with
    the runtime receipt's own ``entry.sha256`` for this file (a drifted
    constant refuses the fast path rather than trusting itself over the
    receipt); (3) the ext4 candidate file exists; (4) re-hashing it produces
    EXACTLY the pinned sha256. Any failure at any of those four steps falls
    back to :func:`_resolve_under` against ``data_root`` UNCHANGED -- this
    function never raises for a missing/mismatched ext4 copy, and never
    trusts the ext4 file on file size or mtime alone.
    """

    filename = Path(entry.path).name
    expected_pin = EXT4_MODEL_SHA256_PINS.get(filename)
    if expected_pin is not None and expected_pin == entry.sha256:
        root = ext4_root if ext4_root is not None else _ext4_models_root()
        candidate = root / filename
        if candidate.is_file() and sha256_file(candidate) == expected_pin:
            return candidate
    return _resolve_under(data_root, entry.path, "runtime gguf_files path", must_exist=True)


def _model_file_argv(
    data_root: Path,
    model_files: tuple[ModelFileRef, ...],
    *,
    role: str = "legacy",
    model_root: Path | None = None,
) -> list[str]:
    """Build ``-m <main>`` / ``--mmproj <mmproj>`` flags from the runtime
    receipt's GGUF set, classifying by filename (the real receipt's two
    entries are the main Q8_0 shard and an ``mmproj-``-prefixed file). Each
    file is resolved via :func:`_resolve_model_file_source` -- ext4-first when
    a verified mirror is present, otherwise the existing ``data_root``
    resolution (a cheap existence check, NOT a re-hash -- the multi-GB GGUF
    re-hash against ``data_root`` is the gate's job, already done before a
    session is ever started; only the ext4 branch re-hashes here, and only
    the (typically much smaller, always-local) ext4 copy)."""

    mmproj = [entry for entry in model_files if "mmproj" in Path(entry.path).name.lower()]
    primary = [entry for entry in model_files if entry not in mmproj]
    if role not in {"legacy", "preprocess", "inference"}:
        raise SessionError(f"unknown session role {role!r}")
    if not primary:
        raise SessionError("runtime receipt has no decoder GGUF")
    if role == "preprocess" and not mmproj:
        raise SessionError("preprocess session requires a runtime-receipt-pinned mmproj")
    argv: list[str] = []

    def resolve(entry: ModelFileRef) -> Path:
        if model_root is not None:
            return _resolve_under(
                Path(model_root),
                entry.path,
                "runtime gguf_files path",
                must_exist=True,
            )
        return _resolve_model_file_source(data_root, entry)

    for entry in primary:
        resolved = resolve(entry)
        argv.extend(["-m", str(resolved)])
    if role == "inference":
        argv.append("--no-mmproj")
    else:
        for entry in mmproj:
            resolved = resolve(entry)
            argv.extend(["--mmproj", str(resolved)])
    return argv


# ---------------------------------------------------------------------------
# Feature-cache directory convention (2026-08-16, docs/featcache-directories.md).
# The llama.cpp mtmd feature-cache patch
# (docs/patches/2026-08-11-mtmd-feature-cache.diff) reads ONE environment
# variable, ``LLAMA_MTMD_FEAT_CACHE_DIR``, off the spawned server's own
# process environment (a model fragment's ``server_env``, W3 2026-08-11 --
# ``core.driver.smoke._server_env``, merged with ``os.environ`` in
# ``start_session`` below with the config's own value always winning). Every
# cache-enabled fragment to date (docs/arms/featcache-bench.arms and its
# np8/validate variants) hand-types the SAME literal absolute path,
# ``/home/chao/feat-cache/q4km`` -- correct for the warm, 26GB earnings21/22
# cache, but it left a brand-new dataset campaign (e.g. SLURP) no NAMED
# parameter to point elsewhere with, only a copy-pasted string to hand-edit:
# exactly the typo hazard that could otherwise mix a new campaign's writes
# into the warm q4km cache.
#
# ``FEAT_CACHE_DIR_DEFAULT`` is that legacy path, pinned here as the single
# source of truth -- it must never change (the on-disk q4km cache must never
# be renamed or moved) -- and it is still what ``feat_cache_dir()`` returns
# when no override is given, so every existing q4km-family fragment's
# behaviour is completely unchanged by this. The resolver is opt-in, never
# force-injected into every spawn: an unset ``FEAT_CACHE_DIR_ENV`` changes
# nothing (a model fragment's own ``server_env``, if any, is still fully
# authoritative), and ``scripts/run_arm_sequence.sh --feat-cache-dir`` is the
# one place that exports it, only when an operator asks. See
# docs/featcache-directories.md for the per-dataset naming convention new
# campaigns should follow (``/home/chao/feat-cache/<dataset>-<encoder>/``)
# and the ext4-only rule.
FEAT_CACHE_DIR_ENV = "SAEA_FEAT_CACHE_DIR"
FEAT_CACHE_DIR_DEFAULT = "/home/chao/feat-cache/q4km"


def feat_cache_dir() -> str:
    """``FEAT_CACHE_DIR_ENV`` overrides the default -- lets one invocation
    (an operator's shell, or ``run_arm_sequence.sh --feat-cache-dir``) name a
    NEW campaign's feature-cache directory without hand-editing a model
    config fragment's ``server_env``. Unset resolves to the legacy,
    already-warm q4km cache (docs/featcache-directories.md), so nothing
    already relying on that literal path changes."""

    override = os.environ.get(FEAT_CACHE_DIR_ENV)
    return override if override else FEAT_CACHE_DIR_DEFAULT


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


@dataclass(frozen=True)
class ServerCommand:
    """Everything ``start_session`` needs to spawn ONE llama-server, and
    everything a cross-process attach needs to prove it is looking at the
    same server: the full argv, the receipt-relative pinned binary path, the
    binary's re-hashed sha256, and the exact GGUF set this role serves.

    Built by :func:`build_server_command`, which is the ONLY place this
    repository composes a llama-server command line. ``core.serving`` (the
    always-on serving session) and ``start_session`` both call it, so an
    operator-started resident server and a flight-started one cannot drift.
    """

    argv: tuple[str, ...]
    binary: Path
    binary_path: str
    binary_sha256: str
    model_files: tuple[ModelFileRef, ...]


def build_server_command(
    *,
    runtime_root: Path,
    data_root: Path,
    runtime_receipt: Mapping[str, object],
    host: str,
    port: int,
    extra_argv: Sequence[str] = (),
    extra_env: Mapping[str, str] | None = None,
    role: str = "legacy",
    model_root: Path | None = None,
) -> ServerCommand:
    """The one llama-server argument builder (see :class:`ServerCommand`).

    Fail-closed, exactly as ``start_session`` has always been before it
    spawned anything: ``host``/``port`` must be loopback (I5); the binary at
    the receipt's pinned relative path must exist and re-hash to EXACTLY the
    receipt's pinned sha256 (a binary swapped on disk between gate-open time
    and spawn time is refused here, never silently executed); an
    ``inference`` role must not smuggle an mmproj through ``extra_argv`` or a
    feature-cache directory through ``extra_env``.

    Deliberately does NOT call ``assert_wsl_execution_environment()``: this
    function starts no process and touches no model, so it is safe to call
    from a check or a test on any host. The spawn itself
    (:func:`start_session`) still asserts the execution environment first.
    """

    require_loopback(f"http://{_bracketed(host)}:{port}")
    pinned_path, pinned_sha = _pinned_binary(runtime_receipt)
    binary = _resolve_under(
        runtime_root, pinned_path, "runtime llama_cpp.binary_path", must_exist=True
    )
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
    from .feature_cache_serving import validate_strict_feature_cache_serving

    validate_strict_feature_cache_serving(
        role=role, extra_argv=extra_argv, extra_env=extra_env, model_files=model_files
    )
    model_argv = _model_file_argv(
        Path(data_root), model_files, role=role, model_root=model_root
    )
    if role == "inference":
        forbidden_extra = [part for part in extra_argv if "mmproj" in part.lower()]
        if forbidden_extra:
            raise SessionError(
                "inference extra_argv must not mention mmproj; --no-mmproj is injected "
                f"by start_session: {forbidden_extra!r}"
            )
        if extra_env and "LLAMA_MTMD_FEAT_CACHE_DIR" in extra_env:
            raise SessionError(
                "inference extra_env must not set LLAMA_MTMD_FEAT_CACHE_DIR"
            )
        session_model_files = tuple(
            entry
            for entry in model_files
            if "mmproj" not in Path(entry.path).name.lower()
        )
    else:
        session_model_files = model_files
    argv = [str(binary), "--host", host, "--port", str(port), *model_argv, *list(extra_argv)]
    return ServerCommand(
        argv=tuple(argv),
        binary=binary,
        binary_path=pinned_path,
        binary_sha256=actual_sha,
        model_files=tuple(session_model_files),
    )


def start_session(
    *,
    runtime_root: Path,
    data_root: Path,
    runtime_receipt: Mapping[str, object],
    host: str,
    port: int,
    session_id: str,
    extra_argv: Sequence[str] = (),
    extra_env: Mapping[str, str] | None = None,
    startup_timeout_seconds: float = DEFAULT_STARTUP_TIMEOUT_SECONDS,
    startup_max_bytes: int = DEFAULT_STARTUP_MAX_BYTES,
    receipt_path: Path | None = None,
    popen: Callable[..., "subprocess.Popen[bytes]"] = subprocess.Popen,
    now: Callable[[], float] = time.time,
    ready_timeout_seconds: float = DEFAULT_READY_TIMEOUT_SECONDS,
    ready_poll_interval_seconds: float = DEFAULT_READY_POLL_INTERVAL_SECONDS,
    http_get_status: Callable[[str, float], int] | None = None,
    server_log_path: Path | None = None,
    role: str = "legacy",
    model_root: Path | None = None,
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

    assert_wsl_execution_environment()
    command = build_server_command(
        runtime_root=runtime_root,
        data_root=data_root,
        runtime_receipt=runtime_receipt,
        host=host,
        port=port,
        extra_argv=tuple(extra_argv),
        extra_env=extra_env,
        role=role,
        model_root=model_root,
    )
    binary = command.binary
    pinned_path = command.binary_path
    actual_sha = command.binary_sha256
    session_model_files = command.model_files
    argv = list(command.argv)

    started_wall = now()
    # server_env (W3, 2026-08-11): runtime-behaviour environment for the
    # spawned server (e.g. GGML_CUDA_DISABLE_GRAPHS). It rides the MODEL
    # fragment and therefore the config hash — a decode-rate-changing
    # environment variable is serving identity, never an operator-shell
    # accident. Fail-closed on non-string content; None = inherit only.
    env = None
    if extra_env:
        for key, value in extra_env.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise SessionError(
                    f"extra_env entries must be str->str, got {key!r}={value!r}"
                )
        env = {**os.environ, **extra_env}
    process = popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=str(binary.parent), env=env,
    )
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
        schema=(
            SESSION_RECEIPT_SCHEMA
            if role == "legacy"
            else SESSION_RECEIPT_SCHEMA_V2
        ),
        study=STUDY_SLUG,
        session_id=session_id,
        binary_path=pinned_path,
        binary_sha256=actual_sha,
        argv=tuple(argv),
        pid=process.pid,
        host=host,
        port=port,
        model_files=session_model_files,
        started_at=_iso(started_wall),
        startup_stdout_sha256=hashlib.sha256(stdout_bytes).hexdigest(),
        # Recorded regardless of whether the writer actually managed to open
        # the file (module docstring at _ServerLogWriter): the DECLARED
        # location, so an operator who finds it missing learns that the log
        # write failed, rather than finding no path recorded at all.
        server_log_path=str(server_log_path) if server_log_path is not None else None,
        role=role,
        server_env_keys=(tuple(sorted(extra_env or {})) if role != "legacy" else ()),
    ).validate()
    if receipt_path is not None:
        write_session_receipt(receipt_path, receipt)
    return receipt


def reap_child(pid: int) -> tuple[bool, int | None]:
    """``(reaped, wait status)`` for ``pid`` via ``waitpid(WNOHANG)``.

    Only the process that SPAWNED ``pid`` can reap it, so a stopper that is
    not the parent always gets ``(False, None)`` (``ChildProcessError``) --
    that is not a failure, it is the reason the parent has to do this itself
    (2026-09-07: the serving wrapper never did, and its exited llama-server
    stayed a zombie for the rest of the day). No-op off POSIX.
    """

    if os.name == "nt" or not hasattr(os, "waitpid"):
        return False, None
    try:
        waited, status = os.waitpid(pid, os.WNOHANG)
    except (ChildProcessError, OSError):
        return False, None
    if waited != pid:
        # 0 means "still running" (WNOHANG); nothing was reaped.
        return False, None
    return True, int(status)


def describe_wait_status(status: int | None) -> dict[str, object]:
    """A ``waitpid`` status as the two facts an operator reads: the exit code
    a process chose, or the signal that ended it.

    ``None`` in, ``None`` out for every field -- an unknown status is
    recorded as unknown, never as a clean exit 0.
    """

    if status is None:
        return {
            "raw": None,
            "exit_code": None,
            "signal": None,
            "signal_name": None,
            "description": "unknown (this process did not reap it)",
        }
    raw = int(status)
    exit_code: int | None = None
    signal_number: int | None = None
    if hasattr(os, "WIFEXITED") and os.WIFEXITED(raw):
        exit_code = int(os.WEXITSTATUS(raw))
        description = f"exited with code {exit_code}"
    elif hasattr(os, "WIFSIGNALED") and os.WIFSIGNALED(raw):
        signal_number = int(os.WTERMSIG(raw))
        description = f"killed by signal {signal_number}"
    else:
        description = f"raw wait status {raw}"
    signal_name = None
    if signal_number is not None:
        try:
            signal_name = signal.Signals(signal_number).name
        except ValueError:
            signal_name = None
        description = f"killed by {signal_name or f'signal {signal_number}'}"
    return {
        "raw": raw,
        "exit_code": exit_code,
        "signal": signal_number,
        "signal_name": signal_name,
        "description": description,
    }


def _reap_stopped_child(pid: int) -> bool:
    """Return true when this process reaped ``pid``; no-op off POSIX."""

    reaped, _status = reap_child(pid)
    return reaped


def _write_stop_receipt(path: Path, document: Mapping[str, object]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except OSError as error:
        raise SessionError(f"cannot write session stop receipt {target}: {error}") from error


def _canonical_document_sha256(document: Mapping[str, object]) -> str:
    encoded = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stop_session(
    session: SessionReceipt,
    *,
    runtime_receipt: Mapping[str, object],
    runtime_root: Path,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.1,
    force_after_timeout: bool = False,
    receipt_path: Path | None = None,
) -> dict[str, object]:
    """Stop only the process proven by ``session`` and write a receipt.

    Identity, process image, and listening-socket ownership are rechecked
    immediately before SIGTERM. A timeout never widens the target: optional
    SIGKILL is sent only after re-verifying that the still-live PID continues
    to run the pinned binary. If the receipt-bound child has already exited,
    its declared runtime identity is still verified and the durable outcome is
    ``ALREADY_EXITED``; cleanup never masks the original server failure. This
    replaces broad ``pkill llama-server`` cleanup in the two-stage speech
    packet workflow.

    A DEFUNCT pid (exited, not yet reaped by its parent) counts as exited
    everywhere below -- both before the signal is sent and while waiting for
    it to land. 2026-09-07: it did not, and the consequence was that every
    stop of an always-on serving session refused. The stopper is a different
    process from the wrapper that spawned the server, so its ``waitpid``
    cannot reap the zombie and ``_pid_alive`` (``kill(pid, 0)``) keeps saying
    "alive"; the wait therefore ran its full timeout and then took the force
    path, where re-verifying the pinned binary raised "cannot resolve
    executable image for pid ... via /proc/<pid>/exe" -- so no stop record
    was written for a server that had in fact stopped. A zombie holds no
    VRAM, no port and no listening socket: it has stopped, and the receipt
    says so, naming the observed state in ``final_process_state``.
    """

    session.validate()
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or timeout_seconds <= 0
        or isinstance(poll_interval_seconds, bool)
        or not isinstance(poll_interval_seconds, (int, float))
        or poll_interval_seconds <= 0
    ):
        raise SessionError("session stop timeout and poll interval must be positive numbers")
    if not isinstance(force_after_timeout, bool):
        raise SessionError("force_after_timeout must be boolean")
    def finish(
        termination_signal: str, forced: bool, final_state: str
    ) -> dict[str, object]:
        document: dict[str, object] = {
            "schema": "saea-session-stop-receipt-v1",
            "study": STUDY_SLUG,
            "session_id": session.session_id,
            "session_role": session.role,
            "session_receipt_sha256": _canonical_document_sha256(session.as_json()),
            "runtime_receipt_sha256": _canonical_document_sha256(runtime_receipt),
            "pid": session.pid,
            "termination_signal": termination_signal,
            "forced": forced,
            "stopped_at": _iso(time.time()),
            # What the pid actually is once this returns: ``gone`` normally,
            # ``defunct`` when the parent has not reaped it yet (a stopper
            # that is not the parent cannot; see the docstring). Passed in
            # by each caller from what it already observed -- deriving it
            # here would cost one more ``kill(pid, 0)`` liveness probe
            # against a pid this function has just finished stopping.
            "final_process_state": final_state,
        }
        if receipt_path is not None:
            _write_stop_receipt(receipt_path, document)
        return document

    verify_against_runtime_receipt(session, runtime_receipt)
    defunct = _pid_is_defunct(session.pid)
    if defunct or not _pid_alive(session.pid):
        # A zombie has already exited; reap it first when this process is
        # the parent, so the record describes a pid that is truly gone.
        reaped = _reap_stopped_child(session.pid)
        return finish(
            "ALREADY_EXITED",
            False,
            PROCESS_STATE_DEFUNCT if defunct and not reaped else PROCESS_STATE_GONE,
        )
    try:
        assert_session_alive(session, runtime_receipt, Path(runtime_root))
    except SessionError:
        if _pid_alive(session.pid):
            raise
        return finish("ALREADY_EXITED", False, PROCESS_STATE_GONE)
    try:
        os.kill(session.pid, signal.SIGTERM)
    except OSError as error:
        raise SessionError(
            f"cannot signal receipt-bound session pid {session.pid}: {error}"
        ) from error

    termination_signal = "SIGTERM"
    forced = False

    def wait_until_stopped(seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        while True:
            # Three ways a signalled server counts as stopped: this process
            # reaped it (it is the parent), the pid is gone, or the pid is a
            # zombie somebody else has yet to reap. The third was missing.
            if (
                _reap_stopped_child(session.pid)
                or not _pid_alive(session.pid)
                or _pid_is_defunct(session.pid)
            ):
                return True
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            time.sleep(min(float(poll_interval_seconds), remaining))

    stopped = wait_until_stopped(float(timeout_seconds))
    if not stopped and force_after_timeout:
        _verify_pid_runs_pinned_binary(session.pid, Path(runtime_root), runtime_receipt)
        kill_signal = getattr(signal, "SIGKILL", signal.SIGTERM)
        try:
            os.kill(session.pid, kill_signal)
        except OSError as error:
            raise SessionError(
                f"cannot force-stop receipt-bound session pid {session.pid}: {error}"
            ) from error
        termination_signal = "SIGKILL" if kill_signal != signal.SIGTERM else "SIGTERM"
        forced = True
        stopped = wait_until_stopped(min(float(timeout_seconds), 10.0))
    if not stopped:
        raise SessionError(
            f"receipt-bound session pid {session.pid} did not stop within "
            f"{timeout_seconds} seconds"
        )
    # Read from /proc, never by signalling: the pid has just been stopped and
    # a liveness probe here would be a second signal against it.
    return finish(
        termination_signal,
        forced,
        PROCESS_STATE_DEFUNCT if _pid_is_defunct(session.pid) else PROCESS_STATE_GONE,
    )


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
