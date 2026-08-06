"""Socket-ownership binding (T5 fix-2, corrected in fix-3): binary/PID
identity alone does not prove the session's process is the one LISTENING
on (host, port) -- session.host/port/argv are self-declared receipt
fields, and ``_verify_pid_runs_pinned_binary`` only proves "this pid runs the
pinned binary somewhere", not "this pid owns THIS listening socket". A
forged receipt can name a second, genuinely live, genuinely pinned-binary
process that simply is not bound to the target port at all.

T5 fix-3 (re-review round 3, a materially equivalent bypass IN the fix-2
design, live-reproduced end to end on Windows): the fix-2 version keyed
every lookup by PORT ALONE, discarding the local address entirely -- the
POSIX path parsed ``local_address`` and then threw the IP away; the
Windows path defined ``dwLocalAddr``/``ucLocalAddr`` on the row structs
and never read them. ``127.0.0.1`` and ``::1`` are DISTINCT,
SIMULTANEOUSLY BINDABLE addresses -- a pinned-binary process P can
genuinely, verifiably own a LISTEN socket on ``[::1]:PORT`` while a
completely different, unverified process Q owns ``127.0.0.1:PORT``; a
forged receipt naming P with ``host=127.0.0.1`` passed the port-only
check, and a real connection to ``127.0.0.1:PORT`` was answered by Q. The
fix-2 docstring's justification ("require_loopback already restricts host
to a fixed set") was WRONG: restricting the SET of legal host strings
says nothing about which address family a socket is actually bound to.
This version is address-aware end to end -- every lookup below is keyed
by (address family, literal address, port), never port alone.

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). ``_proc_net_listen_entries`` and
``_windows_tcp_table_owners`` are defined here but their direct callers
(``_posix_verify_pid_owns_listening_socket`` / ``_windows_verify_pid_owns_
listening_socket``) stay in ``core/session/__init__.py`` -- see that
module's own comment for why (``tests/unit/test_session.py`` monkeypatches
``speech_aware_evidence_acquisition.core.session._proc_net_listen_entries``/
``._windows_tcp_table_owners`` directly and relies on the real call chain
observing it).
"""

from __future__ import annotations

import os
import re
import socket
import struct
from pathlib import Path

from . import SessionError

_SOCKET_FD_PATTERN = re.compile(r"socket:\[(\d+)\]\Z")
_PROC_NET_TCP_LISTEN_STATE = "0A"

if os.name == "nt":  # pragma: sys-platform
    import ctypes
    import ctypes.wintypes as _wintypes

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


def _decode_proc_net_address(hex_ip: str, family: int) -> str:
    """Decode a ``/proc/net/tcp``(6) hex ``local_address`` into a literal IP
    string. IPv4: 4 raw bytes, byte-reversed (the kernel prints the address
    as one 32-bit word in host -- little-endian on x86/x64 -- byte order).
    IPv6: 16 raw bytes as four 32-bit words, each word independently
    byte-reversed but the four words kept in address order (the same
    per-word quirk, repeated four times) -- the standard, widely-documented
    ``/proc/net/tcp6`` decoding."""

    raw = bytes.fromhex(hex_ip)
    if family == socket.AF_INET:
        return socket.inet_ntop(socket.AF_INET, raw[::-1])
    words = struct.unpack("<4I", raw)
    return socket.inet_ntop(socket.AF_INET6, struct.pack(">4I", *words))


def _loopback_family_and_address(host: str) -> tuple[int, str]:
    """Resolve a session's ``host`` (already ``require_loopback``-validated)
    to the EXACT (address family, literal address) the socket-ownership
    check must match -- ``127.0.0.1`` and ``::1`` are different,
    simultaneously bindable endpoints, never interchangeable.

    ``localhost`` is resolved via the same ``getaddrinfo`` mechanism
    ``require_loopback`` already uses (every resolved address is already
    proven loopback there); if it resolves to BOTH families -- common on
    dual-stack systems -- there is no reliable way from user space to know
    which family whatever HTTP client actually dials (resolver/ordering
    behavior is platform- and configuration-dependent), so the ambiguity is
    REFUSED rather than guessed. In practice this is a defensive edge case,
    not the production shape: ``LlamaServerTransport`` requires
    ``session.host`` to be the EXACT literal string in ``base_url`` (T5
    fix-1), and the study's own config pins the literal ``127.0.0.1``
    (``configs/model/qwen3-omni-llamacpp.json``), so this function only
    ever sees whatever literal string the transport is actually configured
    to dial."""

    if host == "127.0.0.1":
        return socket.AF_INET, "127.0.0.1"
    if host == "::1":
        return socket.AF_INET6, "::1"
    if host.lower() == "localhost":
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError as error:
            raise SessionError(
                f"cannot resolve host {host!r} to determine socket ownership: "
                f"{error}; refused (I5)"
            ) from error
        families = {info[0] for info in infos}
        if socket.AF_INET in families and socket.AF_INET6 in families:
            raise SessionError(
                f"host {host!r} resolves to both IPv4 and IPv6 loopback "
                "addresses; refused (I5: socket ownership must be bound to one "
                "unambiguous endpoint, not guessed)"
            )
        if socket.AF_INET6 in families:
            return socket.AF_INET6, "::1"
        return socket.AF_INET, "127.0.0.1"
    raise SessionError(f"host {host!r} is not a recognized loopback literal; refused (I5)")


def _proc_net_listen_entries(path: Path, family: int) -> list[tuple[str, int, int]]:
    """Parse a ``/proc/net/tcp``(6)-shaped file for LISTEN-state rows,
    returning ``(address, port, inode)`` for the given ``family``. A
    missing file (e.g. IPv6 disabled) yields an empty list -- legitimate
    configuration, not a failure; any OTHER read failure fails closed."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as error:
        raise SessionError(
            f"cannot read {path} to determine socket ownership: {error}; refused "
            "(I5: socket ownership must be provable)"
        ) from error
    entries: list[tuple[str, int, int]] = []
    for line in text.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 10:
            continue
        local_address, state, inode_field = fields[1], fields[3], fields[9]
        if state != _PROC_NET_TCP_LISTEN_STATE:
            continue
        try:
            hex_addr, hex_port = local_address.split(":")
            address = _decode_proc_net_address(hex_addr, family)
            port = int(hex_port, 16)
            inode = int(inode_field)
        except (ValueError, OSError):
            continue
        entries.append((address, port, inode))
    return entries


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


def _windows_tcp_table_owners(
    address_family: int, row_type: type
) -> dict[tuple[int, str, int], int]:
    """``(family, address, port) -> owning pid``, for one address family's
    LISTENER-only TCP table (``GetExtendedTcpTable`` with
    ``TCP_TABLE_OWNER_PID_LISTENER`` -- the table already contains
    listening sockets only, no state filtering needed). Keyed by the FULL
    tuple, never port alone (T5 fix-3: a port-only key let a v6 entry
    silently overwrite a v4 owner for the same port number, causing a FALSE
    REFUSAL of a legitimate v4 session whenever an unrelated v6 listener
    happened to share the port). Retries a bounded number of times on the
    standard grow-between-calls race."""

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
            owners: dict[tuple[int, str, int], int] = {}
            for index in range(num_entries):
                row = row_type.from_buffer(buffer, offset + index * row_size)
                local_port = socket.ntohs(row.dwLocalPort & 0xFFFF)
                if address_family == _AF_INET:
                    address = socket.inet_ntoa(
                        struct.pack("<L", row.dwLocalAddr & 0xFFFFFFFF)
                    )
                else:
                    address = socket.inet_ntop(socket.AF_INET6, bytes(row.ucLocalAddr))
                owners[(address_family, address, local_port)] = row.dwOwningPid
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
