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
from .receipt import _pinned_binary

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
