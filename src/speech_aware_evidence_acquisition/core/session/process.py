"""PID liveness and process-image identity (cross-platform).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). The Windows ``ctypes``/``kernel32``
bindings below are this file's own copy of the guard the original module set
up once for both PID-liveness AND socket-ownership use (now split between
here and ``sockets.py``); duplicating the ``if os.name == "nt":`` guard
across the two files changes nothing observable (``ctypes.windll.kernel32``
is a cheap, idempotent DLL handle lookup) and keeps each file's own
platform-specific setup next to the code that uses it.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from . import SessionError
from .paths import _resolve_under, _sha256_file
from .receipt import SessionReceipt, _pinned_binary

MM_PROJ_AUDIT_SCHEMA = "saea-mmproj-free-process-audit-v1"

#: The three states :func:`process_state` distinguishes. ``_pid_alive`` alone
#: cannot: a POSIX child that has exited but has not been reaped by its
#: parent is a ZOMBIE -- ``kill(pid, 0)`` still succeeds, so ``_pid_alive``
#: says "alive", while ``/proc/<pid>/exe`` no longer resolves, so every I5
#: identity check (:func:`_process_image_path` and everything above it)
#: refuses it. That combination is exactly what stranded both serving
#: sessions on 2026-09-07: ``stop`` sent its SIGTERM, llama-server exited,
#: the foreground wrapper never reaped it, and from then on every stop and
#: every attach refused with "cannot resolve executable image for pid ... via
#: /proc/<pid>/exe" while ``session.json`` still had no stop record and
#: ``start`` therefore refused the next geometry as "already resident".
#: Naming the state is what lets each of those callers say the true thing.
PROCESS_STATE_RUNNING = "running"
PROCESS_STATE_DEFUNCT = "defunct"
PROCESS_STATE_GONE = "gone"

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


def _linux_process_state_char(pid: int, proc_root: Path = Path("/proc")) -> str | None:
    """The one-letter Linux process state (``R``, ``S``, ``D``, ``Z``, ...)
    from ``/proc/<pid>/stat``, or ``None`` when ``/proc`` cannot answer (a
    non-Linux host, or a pid that is already gone).

    Parsed from the LAST ``)`` rather than by splitting on whitespace: the
    second field is the executable's ``comm``, in parentheses, and it may
    itself contain spaces and parentheses (``(llama-server (old))`` is a
    legal comm), so a naive ``split()[2]`` reads the wrong field for exactly
    the processes an operator is most likely to be confused by.
    """

    try:
        raw = (Path(proc_root) / str(int(pid)) / "stat").read_text(
            encoding="utf-8", errors="replace"
        )
    except (OSError, ValueError):
        return None
    close = raw.rfind(")")
    if close < 0:
        return None
    fields = raw[close + 1 :].split()
    return fields[0] if fields else None


def _pid_is_defunct(pid: int, proc_root: Path = Path("/proc")) -> bool:
    """True only for a POSIX zombie: exited, not yet reaped by its parent."""

    return _linux_process_state_char(pid, proc_root) == "Z"


def process_state(pid: int, *, proc_root: Path = Path("/proc")) -> str:
    """``running`` / ``defunct`` / ``gone`` for ``pid``, right now.

    The ``/proc`` reading comes first because it is the only one that can
    tell a zombie from a live process (see :data:`PROCESS_STATE_DEFUNCT`);
    ``_pid_alive`` is the fallback for a host without ``/proc`` (Windows, or
    a POSIX host that does not mount it), where a zombie is not a state a
    caller can observe anyway.
    """

    state = _linux_process_state_char(pid, proc_root)
    if state == "Z":
        return PROCESS_STATE_DEFUNCT
    if state is not None:
        return PROCESS_STATE_RUNNING
    return PROCESS_STATE_RUNNING if _pid_alive(pid) else PROCESS_STATE_GONE


def _defunct_wait_status(pid: int, proc_root: Path = Path("/proc")) -> int | None:
    """A zombie's own ``exit_code`` field (``/proc/<pid>/stat`` field 52), in
    the same encoding ``os.waitpid`` returns -- ADVISORY ONLY.

    The parent holds the authoritative status; this is what a process that is
    NOT the parent (``scripts/serving_session.sh stop``, say) can still learn
    about a zombie it is about to record as stale. Absent or unparseable on
    any kernel that does not expose the field, in which case ``None``.
    """

    try:
        raw = (Path(proc_root) / str(int(pid)) / "stat").read_text(
            encoding="utf-8", errors="replace"
        )
    except (OSError, ValueError):
        return None
    close = raw.rfind(")")
    if close < 0:
        return None
    # fields[0] is field 3 (state), so field 52 (exit_code) is index 49.
    fields = raw[close + 1 :].split()
    if len(fields) <= 49:
        return None
    try:
        return int(fields[49])
    except ValueError:
        return None


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


def audit_mmproj_free_inference(
    session: SessionReceipt,
    *,
    proc_root: Path = Path("/proc"),
) -> dict[str, object]:
    """Fail closed unless a live-process filesystem audit has zero mmproj hits.

    The explicit ``--no-mmproj`` switch is the sole allowed occurrence of the
    substring in argv. Any mmproj artifact or other flag in the receipt argv,
    live ``cmdline``, memory maps, or open-file targets is a failure. Formal
    inference records the returned mapping alongside its session receipt.
    """

    session.validate()
    if session.role != "inference":
        raise SessionError("mmproj-free process audit requires an inference session")
    process_root = Path(proc_root) / str(session.pid)
    cmdline_path = process_root / "cmdline"
    maps_path = process_root / "maps"
    fd_path = process_root / "fd"
    try:
        live_argv = tuple(
            part.decode("utf-8", "strict")
            for part in cmdline_path.read_bytes().split(b"\0")
            if part
        )
        map_lines = tuple(maps_path.read_text(encoding="utf-8").splitlines())
        fd_entries = tuple(fd_path.iterdir())
    except (OSError, UnicodeError) as error:
        raise SessionError(
            f"cannot audit inference pid {session.pid} through {process_root}: {error}"
        ) from error

    def argv_hits(parts: tuple[str, ...]) -> list[str]:
        return [
            part
            for part in parts
            if "mmproj" in part.lower() and part != "--no-mmproj"
        ]

    receipt_argv_hits = argv_hits(session.argv)
    live_argv_hits = argv_hits(live_argv)
    maps_hits = [line for line in map_lines if "mmproj" in line.lower()]
    open_file_hits: list[str] = []
    for entry in fd_entries:
        try:
            target = os.readlink(entry)
        except OSError as error:
            raise SessionError(
                f"cannot resolve open file {entry} while auditing inference: {error}"
            ) from error
        if "mmproj" in target.lower():
            open_file_hits.append(target)
    hit_count = (
        len(receipt_argv_hits)
        + len(live_argv_hits)
        + len(maps_hits)
        + len(open_file_hits)
    )
    if hit_count:
        raise SessionError(
            "inference process audit found an mmproj hit: "
            f"receipt_argv={receipt_argv_hits!r}, live_argv={live_argv_hits!r}, "
            f"maps={maps_hits!r}, open_files={open_file_hits!r}"
        )
    return {
        "schema": MM_PROJ_AUDIT_SCHEMA,
        "session_id": session.session_id,
        "pid": session.pid,
        "role": session.role,
        "mmproj_loaded": False,
        "mmproj_hit_count": 0,
        "receipt_argv_checked": True,
        "live_argv_checked": True,
        "process_maps_checked": True,
        "open_files_checked": True,
    }
