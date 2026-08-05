"""Runtime session attestation (R0 repair T5, invariant I5).

Reproduced defect: the frozen-core gate re-hashes the pinned llama.cpp binary,
its runtime libraries and the GGUF files on disk -- then the transport simply
POSTs to whatever ``base_url`` the config names. Nothing binds the RESPONDING
PROCESS to those hashed artifacts. These probes exercise the fix: a
``SessionReceipt`` binding binary/model identity, pid, argv, host and port,
obtained ONLY via ``start_session`` (spawns and observes) or ``attach_session``
(re-verifies an on-disk receipt against the runtime receipt, a live pid,
process IMAGE identity, AND -- T5 fix-2, closing a materially equivalent gap
an independent re-review demonstrated live on both Windows and WSL2 -- kernel-
level SOCKET OWNERSHIP of ``(host, port)``) -- and re-checked independently by
``LlamaServerTransport`` at construction AND on every single send, plus a
complementary call site inside ``FrozenCoreAdapter`` (T5 fix-3).

NO MODEL TOUCH: every spawn in this file launches either a FAKE POSIX
shell-script "binary" (``TestStartSessionSpawn``, the same pattern
``tests/unit/test_e0_generators.py`` already uses for `llama-server
--version`) or a plain COPY of the current Python interpreter, invoked with
``-c "..."`` (the process-identity/socket-ownership tests below, some of
which additionally bind a REAL localhost TCP socket in the spawned child --
still never the real llama-server, never a real model file, never any
network I/O beyond localhost loopback plumbing internal to the test).
"""

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG, ExecutionPlan
from speech_aware_evidence_acquisition.core.base import PayloadBindingContext
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, LlamaServerTransport
from speech_aware_evidence_acquisition.core.session import (
    SESSION_RECEIPT_SCHEMA,
    ModelFileRef,
    SessionError,
    SessionReceipt,
    attach_session,
    read_session_receipt,
    require_loopback,
    start_session,
    verify_against_runtime_receipt,
    write_session_receipt,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _model_files():
    return (
        ModelFileRef(path="models/x/model.gguf", sha256="a" * 64),
        ModelFileRef(path="models/x/mmproj.gguf", sha256="b" * 64),
    )


def _session(**overrides):
    base = dict(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id="test-session-1",
        binary_path="llama.cpp/build/bin/llama-server",
        binary_sha256="c" * 64,
        argv=("llama-server", "--host", "127.0.0.1", "--port", "8080"),
        pid=os.getpid(),
        host="127.0.0.1",
        port=8080,
        model_files=_model_files(),
        started_at="2026-08-05T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
    )
    base.update(overrides)
    return SessionReceipt(**base)


def _canned_response():
    return json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
    ).encode()


def _runtime_world(tmp_path):
    """A tiny model/runtime file world plus a matching runtime receipt dict
    (no real network, no real model -- fake bytes, like gate_fixture.py).
    The 'binary' here is NOT a real executable -- fine for every test that
    is refused BEFORE reaching the process-identity check (declared-value
    mismatches, loopback/host-port mismatches), but NOT usable for a test
    that must actually reach ``_verify_pid_runs_pinned_binary`` -- those use
    ``_live_runtime_world`` below instead."""

    runtime_root = tmp_path / "runtime"
    data_root = tmp_path / "data"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    binary_bytes = b"fake-llama-server"
    binary.write_bytes(binary_bytes)
    (binary.parent / "lib-fake.so").write_bytes(b"fake-lib")

    model_dir = data_root / "models" / "qwen3-omni-30b-a3b-instruct-gguf"
    model_dir.mkdir(parents=True)
    main_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/model.gguf"
    mmproj_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/mmproj.gguf"
    main_bytes = b"fake-main-gguf"
    mmproj_bytes = b"fake-mmproj-gguf"
    (data_root / main_relpath).write_bytes(main_bytes)
    (data_root / mmproj_relpath).write_bytes(mmproj_bytes)

    runtime_receipt = {
        "schema": "saea-runtime-receipt-v2",
        "study": "speech-aware-evidence-acquisition",
        "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
        "llama_cpp": {
            "build_commit": "a" * 40,
            "reported_build": "version: 1 (aaaaaaa)",
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_bytes": len(binary_bytes),
            "binary_sha256": _sha(binary_bytes),
        },
        "gguf_files": [
            {"path": main_relpath, "bytes": len(main_bytes), "sha256": _sha(main_bytes)},
            {"path": mmproj_relpath, "bytes": len(mmproj_bytes), "sha256": _sha(mmproj_bytes)},
        ],
        "runtime_libraries": [
            {"path": "llama.cpp/build/bin/lib-fake.so", "bytes": 8, "sha256": _sha(b"fake-lib")},
        ],
    }
    return runtime_root, data_root, binary, runtime_receipt


def _live_runtime_world(tmp_path):
    """Like ``_runtime_world``, but the pinned binary is a REAL executable
    (a byte-for-byte copy of the CURRENTLY RUNNING interpreter) so process-
    IDENTITY checks (T5 fix-1) can be genuinely exercised: a real process
    spawned from this exact file legitimately matches it; any OTHER live
    process (e.g. this test's own interpreter, or a forger's chosen pid)
    legitimately does not. No model bytes, no network -- copying/spawning
    the test's own interpreter is the same idea as
    ``tests/unit/test_e0_generators.py``'s fake ``llama-server --version``
    shell script, just for a check that needs a REAL OS-reported image
    rather than merely an executable-and-exiting one (a shebang script's
    reported image is its INTERPRETER, e.g. ``/bin/sh``, not the script
    itself, so it cannot exercise this specific check)."""

    runtime_root = tmp_path / "runtime"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    shutil.copy(sys.executable, binary)
    if os.name != "nt":
        binary.chmod(0o755)
    binary_sha256 = _sha(binary.read_bytes())
    model_files = _model_files()
    runtime_receipt = {
        "llama_cpp": {
            "binary_path": "llama.cpp/build/bin/llama-server",
            "binary_sha256": binary_sha256,
        },
        "gguf_files": [{"path": f.path, "sha256": f.sha256} for f in model_files],
    }
    return runtime_root, binary, runtime_receipt


def _spawn_matching_process(binary):
    return subprocess.Popen(
        [str(binary), "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _terminate(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _listener_code(port: int) -> str:
    """A tiny real TCP listener, run inside a spawned child via ``-c`` --
    binds and LISTENs on ``127.0.0.1:<port>`` for real (localhost only, no
    external network reachability), then idles. T5 fix-2: socket-ownership
    verification needs a genuinely bound, kernel-visible listening socket to
    exercise at all -- a sleeping process alone (the T5 fix-1 pattern) is not
    enough."""

    return (
        "import socket, time\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        f"s.bind(('127.0.0.1', {port}))\n"
        "s.listen(1)\n"
        "time.sleep(90)\n"
    )


def _spawn_listening_process(binary, port: int):
    """Spawn ``binary`` (any real executable -- the pinned copy OR an
    unrelated one, per test) running ``_listener_code``, and block until the
    socket is genuinely accepting connections before returning (removes the
    spawn/bind race)."""

    process = subprocess.Popen(
        [str(binary), "-c", _listener_code(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30.0  # first-exec AV-scan latency on a fresh copy, under load
    last_error: OSError | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return process
        except OSError as error:
            last_error = error
            time.sleep(0.05)
    _terminate(process)
    raise AssertionError(f"nothing ever listened on 127.0.0.1:{port}: {last_error}")


def _matching_session(runtime_receipt, **overrides):
    llama_cpp = runtime_receipt["llama_cpp"]
    base = dict(
        binary_path=llama_cpp["binary_path"],
        binary_sha256=llama_cpp["binary_sha256"],
        model_files=tuple(
            ModelFileRef(path=e["path"], sha256=e["sha256"]) for e in runtime_receipt["gguf_files"]
        ),
    )
    base.update(overrides)
    return _session(**base)


# ---------------------------------------------------------------------------
# require_loopback -- probe 1 (non-loopback base_url refused).
# ---------------------------------------------------------------------------


def test_require_loopback_accepts_127001():
    assert require_loopback("http://127.0.0.1:8080") == ("127.0.0.1", 8080)


def test_require_loopback_accepts_bracketed_ipv6_literal():
    assert require_loopback("http://[::1]:8080") == ("::1", 8080)


def test_require_loopback_accepts_localhost():
    host, port = require_loopback("http://localhost:8080")
    assert (host, port) == ("localhost", 8080)


@pytest.mark.parametrize(
    "base_url", ["http://10.0.0.5:8080", "http://example.com:8080", "http://192.168.1.5:8080"]
)
def test_require_loopback_refuses_non_loopback_host(base_url):
    with pytest.raises(SessionError, match="loopback"):
        require_loopback(base_url)


# ---------------------------------------------------------------------------
# SessionReceipt structural validation + JSON round trip.
# ---------------------------------------------------------------------------


def test_valid_session_receipt_round_trips_through_json(tmp_path):
    receipt = _session().validate()
    path = tmp_path / "runs" / "session.json"
    write_session_receipt(path, receipt)
    assert read_session_receipt(path) == receipt


def test_session_receipt_refuses_non_loopback_host():
    with pytest.raises(SessionError, match="loopback"):
        _session(host="10.0.0.5").validate()


def test_session_receipt_refuses_wrong_schema():
    with pytest.raises(SessionError, match="schema"):
        _session(schema="wrong").validate()


def test_read_session_receipt_refuses_missing_file(tmp_path):
    with pytest.raises(SessionError, match="cannot read"):
        read_session_receipt(tmp_path / "does-not-exist.json")


# ---------------------------------------------------------------------------
# verify_against_runtime_receipt -- probe 3 (declared-value mismatch refused).
# Pure declared-value comparison: no pid/process involved at all.
# ---------------------------------------------------------------------------


def test_verify_against_runtime_receipt_accepts_matching_identity(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    verify_against_runtime_receipt(_matching_session(runtime_receipt), runtime_receipt)


def test_verify_against_runtime_receipt_refuses_binary_hash_mismatch(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="f" * 64)
    with pytest.raises(SessionError, match="binary identity"):
        verify_against_runtime_receipt(session, runtime_receipt)


def test_verify_against_runtime_receipt_refuses_model_file_mismatch(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(
        runtime_receipt,
        model_files=(ModelFileRef(path="models/x/other.gguf", sha256="d" * 64),),
    )
    with pytest.raises(SessionError, match="model file set"):
        verify_against_runtime_receipt(session, runtime_receipt)


# ---------------------------------------------------------------------------
# LlamaServerTransport -- probes 1, 2, 3, 6, 7 at the send choke point.
# These declared-value/loopback probes are refused BEFORE the process-
# identity check is ever reached, so a placeholder (non-existent, non-real)
# runtime_root is fine for them -- it is never resolved.
# ---------------------------------------------------------------------------


def test_transport_refuses_without_a_session_receipt(tmp_path):
    """Probe 2: asked to send with no session receipt -> refused, before any
    __call__/send is even possible (construction itself fails closed)."""

    with pytest.raises(SessionError, match="session"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, None, {}, tmp_path, post=lambda u, b: b""
        )


def test_transport_refuses_non_loopback_base_url(tmp_path):
    """Probe 1 at the transport."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=8080)
    with pytest.raises(SessionError, match="loopback"):
        LlamaServerTransport(
            "http://10.0.0.5:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_with_binary_hash_mismatch(tmp_path):
    """Probe 3 at the transport: even a hand-built SessionReceipt (bypassing
    start_session/attach_session entirely) is refused here."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64)
    with pytest.raises(SessionError, match="binary identity"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_port_mismatch_with_base_url(tmp_path):
    """Probe 6: a session receipt recorded for a different port than the
    transport's own base_url is refused, even though both are individually
    loopback-valid."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=9090)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_refuses_session_host_mismatch_with_base_url(tmp_path):
    """Probe 6, host variant: 'localhost' and '127.0.0.1' are both loopback
    but not the SAME endpoint a session receipt was recorded for."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="localhost", port=8080)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, tmp_path,
            post=lambda u, b: b"",
        )


def test_transport_accepts_a_valid_matching_session_and_sends(tmp_path):
    """Probe 7 (transport half) / T5 fix-2 probe 3 (legitimate ACCEPT): a
    session naming a process that is BOTH the pinned binary AND genuinely
    listening on the claimed port is accepted, and an actual send still
    works exactly as before T5."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18190)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18190, pid=process.pid)
        transport = LlamaServerTransport(
            "http://127.0.0.1:18190",
            tmp_path,
            session,
            runtime_receipt,
            runtime_root,
            post=lambda u, b: _canned_response(),
        )
        media = tmp_path / "media" / "5000001.mp3"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"fake-mp3-bytes")
        payload = {
            "request_id": "req-1",
            "carrier_lock_key": "earnings22-original",
            "sample_id": "5000001",
            "speech_ref": "earnings22-original/5000001",
            "media_relpath": "media/5000001.mp3",
            "audio_seconds": 10.0,
            "sample_rate_hz": 16000,
            "task_instruction": "Transcribe the speech verbatim.",
            "history": [],
            "decoding_params": {"temperature": 0, "seed": 20260803},
        }
        raw = transport(json.dumps(payload).encode())
        assert json.loads(raw)["text"] == "hello world"
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# CRITICAL, reviewer-demonstrated exploit: a forged SessionReceipt with the
# CORRECT, PUBLIC binary_path/binary_sha256/model_files (copied verbatim from
# the committed runtime receipt) but naming an unrelated LIVE pid (here: this
# very test process). Before the fix, attach_session and LlamaServerTransport
# construction both only checked declared-value agreement plus bare
# liveness -- both trivially satisfied by such a forgery -- and returned/
# accepted the receipt as genuine, letting an "answered-by-imposter" request
# round-trip successfully. Standing regressions, exercised at BOTH
# independent enforcement layers.
# ---------------------------------------------------------------------------


def test_attach_refuses_alive_but_unrelated_pid(tmp_path):
    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    forged = _matching_session(runtime_receipt, pid=os.getpid())
    receipt_path = tmp_path / "forged-session.json"
    write_session_receipt(receipt_path, forged)
    with pytest.raises(SessionError, match="is running"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)


def test_transport_refuses_alive_but_unrelated_pid(tmp_path):
    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    forged = _matching_session(runtime_receipt, pid=os.getpid())
    with pytest.raises(SessionError, match="is running"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, forged, runtime_receipt, runtime_root,
            post=lambda u, b: b"",
        )


# ---------------------------------------------------------------------------
# T5 fix-2: socket-ownership binding. A materially equivalent, still-open
# gap in the SAME invariant an independent re-review demonstrated live on
# BOTH Windows and WSL2: _verify_pid_runs_pinned_binary proves "the process
# at this pid runs the pinned binary", but nothing bound that pid to the
# SOCKET the transport actually talks to -- session.host/port/argv are
# self-declared receipt fields. The re-reviewer spawned a SECOND genuine
# instance of the pinned binary (not listening on the target port at all),
# forged a SessionReceipt naming that pid with port=8080, and construction
# SUCCEEDED. Standing regressions below (probes 1/2 from that finding);
# probe 3 (legitimate ACCEPT) is exercised by
# test_transport_accepts_a_valid_matching_session_and_sends and
# test_attach_succeeds_for_a_live_matching_session above, both of which now
# spawn a process that REALLY binds the claimed port; probe 4 (undeterminable
# ownership) is the last test in this section.
# ---------------------------------------------------------------------------


def test_attach_refuses_pinned_binary_process_not_listening_on_claimed_port(tmp_path):
    """T5 fix-2 probe 1 -- THE re-reviewer's exact exploit: a SECOND genuine,
    live instance of the pinned binary (so the T5 fix-1 identity check ALONE
    would accept it) that is NOT listening on the claimed port at all. Must
    fail before this fix, pass (refuse) after it."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    idle_process = _spawn_matching_process(binary)  # alive, pinned binary, binds nothing
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18193, pid=idle_process.pid
        )
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="no LISTEN socket found"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(idle_process)


def test_transport_refuses_pinned_binary_process_not_listening_on_claimed_port(tmp_path):
    """Same exploit, transport-construction layer."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    idle_process = _spawn_matching_process(binary)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18194, pid=idle_process.pid
        )
        with pytest.raises(SessionError, match="no LISTEN socket found"):
            LlamaServerTransport(
                "http://127.0.0.1:18194", tmp_path, forged, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(idle_process)


def test_attach_refuses_listener_that_is_not_the_pinned_binary(tmp_path):
    """T5 fix-2 probe 2: a process IS genuinely listening on the claimed
    port, but it is NOT the pinned binary (a different real executable, the
    interpreter's own un-copied path). The EXISTING T5 fix-1 identity check
    must fire -- proving the two checks compose, neither alone sufficient."""

    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    impostor = _spawn_listening_process(Path(sys.executable), 18195)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18195, pid=impostor.pid
        )
        receipt_path = tmp_path / "forged-session.json"
        write_session_receipt(receipt_path, forged)
        with pytest.raises(SessionError, match="is running"):
            attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root)
    finally:
        _terminate(impostor)


def test_transport_refuses_listener_that_is_not_the_pinned_binary(tmp_path):
    """Same composition proof, transport-construction layer."""

    runtime_root, _binary, runtime_receipt = _live_runtime_world(tmp_path)
    impostor = _spawn_listening_process(Path(sys.executable), 18196)
    try:
        forged = _matching_session(
            runtime_receipt, host="127.0.0.1", port=18196, pid=impostor.pid
        )
        with pytest.raises(SessionError, match="is running"):
            LlamaServerTransport(
                "http://127.0.0.1:18196", tmp_path, forged, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(impostor)


def test_socket_ownership_undeterminable_fails_closed(tmp_path, monkeypatch):
    """T5 fix-2 probe 4: if socket ownership cannot be determined AT ALL
    (simulating a ``/proc/net/tcp`` read failure on POSIX, or a failed
    ``GetExtendedTcpTable`` lookup on Windows), the touch is refused --
    never silently treated as 'unknown, so allow'. (The OTHER undeterminable
    shape -- the lookup mechanism working fine but finding no entry at all --
    is exactly probe 1 above, already a standing regression via the real,
    unmocked code path.)"""

    from speech_aware_evidence_acquisition.core import session as session_module

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18197)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18197, pid=process.pid)

        def _boom(*_args, **_kwargs):
            raise SessionError("simulated socket-ownership lookup failure")

        if os.name == "nt":
            monkeypatch.setattr(session_module, "_windows_tcp_table_owners", _boom)
        else:
            monkeypatch.setattr(session_module, "_listen_inodes_for_port", _boom)

        with pytest.raises(SessionError, match="simulated socket-ownership lookup failure"):
            LlamaServerTransport(
                "http://127.0.0.1:18197", tmp_path, session, runtime_receipt, runtime_root,
                post=lambda u, b: b"",
            )
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# IMPORTANT fix-2: the process dying MID-RUN must be caught on the NEXT
# send, not only at construction.
# ---------------------------------------------------------------------------


def test_transport_send_refuses_after_process_dies_mid_run(tmp_path):
    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18191)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18191, pid=process.pid)
        transport = LlamaServerTransport(
            "http://127.0.0.1:18191",
            tmp_path,
            session,
            runtime_receipt,
            runtime_root,
            post=lambda u, b: _canned_response(),
        )
        media = tmp_path / "media" / "5000001.mp3"
        media.parent.mkdir(parents=True, exist_ok=True)
        media.write_bytes(b"fake-mp3-bytes")
        payload = {
            "request_id": "req-1",
            "carrier_lock_key": "earnings22-original",
            "sample_id": "5000001",
            "speech_ref": "earnings22-original/5000001",
            "media_relpath": "media/5000001.mp3",
            "audio_seconds": 10.0,
            "sample_rate_hz": 16000,
            "task_instruction": "Transcribe the speech verbatim.",
            "history": [],
            "decoding_params": {"temperature": 0, "seed": 20260803},
        }
        raw = transport(json.dumps(payload).encode())
        assert json.loads(raw)["text"] == "hello world"

        process.terminate()
        process.wait(timeout=5)
        with pytest.raises(SessionError, match="not a live process"):
            transport(json.dumps(payload).encode())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)


# ---------------------------------------------------------------------------
# attach_session -- probes 3, 4 (declared-value / dead-pid; refused before
# the process-identity check is reached, so the placeholder runtime_root is
# fine).
# ---------------------------------------------------------------------------


def test_attach_refuses_missing_receipt_file(tmp_path):
    with pytest.raises(SessionError, match="cannot read"):
        attach_session(tmp_path / "does-not-exist.json", runtime_receipt={}, runtime_root=tmp_path)


def test_attach_refuses_binary_hash_mismatch(tmp_path):
    """Probe 3 via attach."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64, pid=os.getpid())
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="binary identity"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=tmp_path)


def test_attach_refuses_dead_pid(tmp_path):
    """Probe 4: attach to a dead PID -> refused."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    session = _matching_session(runtime_receipt, pid=proc.pid)
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="not a live process"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt, runtime_root=tmp_path)


def test_attach_succeeds_for_a_live_matching_session(tmp_path):
    """Fixed per reviewer feedback: the ORIGINAL version of this test used
    ``pid=os.getpid()`` (the test's own interpreter), which is exactly why
    the CRITICAL gap (attach_session trusting declared values + bare
    liveness) went uncaught. attach_session now ALSO requires the pid to be
    ACTUALLY RUNNING the pinned binary image AND to genuinely own the
    listening socket on the claimed port (T5 fix-2) -- proven here with a
    REAL spawned process running a genuine copy of that exact binary file,
    really bound to the claimed port."""

    runtime_root, binary, runtime_receipt = _live_runtime_world(tmp_path)
    process = _spawn_listening_process(binary, 18192)
    try:
        session = _matching_session(runtime_receipt, host="127.0.0.1", port=18192, pid=process.pid)
        receipt_path = tmp_path / "session.json"
        write_session_receipt(receipt_path, session)
        attached = attach_session(
            receipt_path, runtime_receipt=runtime_receipt, runtime_root=runtime_root
        )
        assert attached == session
    finally:
        _terminate(process)


# ---------------------------------------------------------------------------
# IMPORTANT fix-3: FrozenCoreAdapter's complementary session-liveness check.
# ---------------------------------------------------------------------------


class _RecordingSessionTransport:
    """Duck-typed stand-in exposing assert_session_alive(), the SAME
    protocol LlamaServerTransport exposes -- proves FrozenCoreAdapter really
    calls it (construction + before every request) and never invokes the
    underlying transport when it raises, without needing a real llama-server
    or even a real subprocess."""

    def __init__(self) -> None:
        self.session_checks = 0
        self.calls = 0
        self.should_fail = False

    def assert_session_alive(self) -> None:
        self.session_checks += 1
        if self.should_fail:
            raise SessionError("forced session failure for the test")

    def __call__(self, request_bytes: bytes) -> bytes:
        self.calls += 1
        return _canned_response_as_core_response()


def _canned_response_as_core_response() -> bytes:
    return json.dumps(
        {"text": "hello world", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    ).encode()


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _adapter_world(tmp_path):
    media = tmp_path / "media" / "5000001.mp3"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key="earnings22-original",
        allowed_sample_ids=frozenset({"5000001"}),
        sample_facts={"5000001": (100.0, 16000)},
        data_root=tmp_path,
        carrier_root=tmp_path,
    )
    plan = ExecutionPlan(
        run_id="SAEA-E-000-session-adapter",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original",
        split_role="dev",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=0.5,
        planned_speech_audio_seconds=500,
        protocol_hash="b" * 64,
        attempt_id="attempt-session-check",
    )
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "earnings22-original",
        "sample_id": "5000001",
        "speech_ref": "earnings22-original/5000001",
        "media_relpath": "media/5000001.mp3",
        "audio_seconds": 100.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
    }
    return binding, plan, payload


def test_adapter_checks_transport_session_at_construction(tmp_path):
    binding, plan, _payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    assert transport.session_checks == 1


def test_adapter_rechecks_transport_session_before_every_request(tmp_path):
    binding, plan, payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    assert transport.session_checks == 1
    adapter.request(payload)
    assert transport.session_checks == 2
    assert transport.calls == 1


def test_adapter_never_sends_when_the_session_check_fails(tmp_path):
    """A failing session check must refuse the request WITHOUT ever reaching
    the underlying transport -- no partial or leaked send."""

    binding, plan, payload = _adapter_world(tmp_path)
    transport = _RecordingSessionTransport()
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    transport.should_fail = True
    with pytest.raises(SessionError, match="forced session failure"):
        adapter.request(payload)
    assert transport.calls == 0


def test_adapter_with_a_bare_callable_transport_is_unaffected(tmp_path):
    """A transport with no assert_session_alive() attribute at all (every
    fake/bare-callable transport used elsewhere in this repo's own tests)
    must behave EXACTLY as before T5 -- the duck-typed check is strictly
    additive, never mandatory for a transport that never claimed to have
    one."""

    binding, plan, payload = _adapter_world(tmp_path)

    def bare_transport(request_bytes: bytes) -> bytes:
        return _canned_response_as_core_response()

    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=plan, arm="bare-core", transport=bare_transport,
        sink=TraceSink(tmp_path / "run", plan.run_id), binding=binding,
    )
    response = adapter.request(payload)
    assert response.text == "hello world"


# ---------------------------------------------------------------------------
# start_session -- real spawn, POSIX-only, FAKE binary (never llama-server).
# start_session itself is unchanged by this fix (it directly hash-verifies
# then immediately Popen()s the exact same path -- no separate PID-identity
# gap to close there the way attach_session/LlamaServerTransport had), so
# these probes are unchanged.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.name == "nt", reason="POSIX shell-script fake executable required for a real spawn"
)
class TestStartSessionSpawn:
    def _fake_binary_world(self, tmp_path, *, sleep_seconds=5):
        runtime_root = tmp_path / "runtime"
        data_root = tmp_path / "data"
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.parent.mkdir(parents=True)
        binary.write_text(
            "#!/bin/sh\n"
            "echo 'server listening on 127.0.0.1'\n"
            f"sleep {sleep_seconds}\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)
        binary_bytes = binary.read_bytes()

        model_dir = data_root / "models" / "qwen3-omni-30b-a3b-instruct-gguf"
        model_dir.mkdir(parents=True)
        main_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/model.gguf"
        mmproj_relpath = "models/qwen3-omni-30b-a3b-instruct-gguf/mmproj.gguf"
        (data_root / main_relpath).write_bytes(b"fake-main-gguf")
        (data_root / mmproj_relpath).write_bytes(b"fake-mmproj-gguf")

        runtime_receipt = {
            "llama_cpp": {
                "binary_path": "llama.cpp/build/bin/llama-server",
                "binary_sha256": _sha(binary_bytes),
            },
            "gguf_files": [
                {"path": main_relpath, "sha256": _sha(b"fake-main-gguf")},
                {"path": mmproj_relpath, "sha256": _sha(b"fake-mmproj-gguf")},
            ],
        }
        return runtime_root, data_root, runtime_receipt

    def test_spawn_writes_a_session_receipt_bound_to_the_real_process(self, tmp_path):
        """Probe 7 (spawn half): a legitimate spawn of the FAKE pinned binary
        produces a SessionReceipt with a REAL pid/argv/binary hash/port/model
        paths, and the process is genuinely alive at that pid; the receipt is
        written to disk and re-reads identically."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        receipt_path = tmp_path / "runs" / "session.json"
        receipt = start_session(
            runtime_root=runtime_root,
            data_root=data_root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=18080,
            session_id="spawn-test-1",
            receipt_path=receipt_path,
            startup_timeout_seconds=2.0,
        )
        try:
            assert receipt.pid > 0
            assert receipt.host == "127.0.0.1"
            assert receipt.port == 18080
            assert receipt.binary_sha256 == runtime_receipt["llama_cpp"]["binary_sha256"]
            assert {f.path for f in receipt.model_files} == {
                e["path"] for e in runtime_receipt["gguf_files"]
            }
            assert "--host" in receipt.argv
            assert "127.0.0.1" in receipt.argv
            assert receipt_path.is_file()
            assert read_session_receipt(receipt_path) == receipt
            os.kill(receipt.pid, 0)  # the real subprocess is alive right now
        finally:
            try:
                os.kill(receipt.pid, 15)
            except OSError:
                pass
            try:
                os.waitpid(receipt.pid, 0)
            except OSError:
                pass

    def test_spawn_of_a_binary_whose_hash_does_not_match_pinned_is_refused(self, tmp_path):
        """Probe 5: the binary on disk was swapped after the receipt captured
        a hash for the ORIGINAL bytes -- spawn must refuse, not execute it."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
        binary.write_text("#!/bin/sh\necho tampered\n", encoding="utf-8")
        binary.chmod(0o755)
        with pytest.raises(SessionError, match="hash"):
            start_session(
                runtime_root=runtime_root,
                data_root=data_root,
                runtime_receipt=runtime_receipt,
                host="127.0.0.1",
                port=18081,
                session_id="spawn-test-2",
            )

    def test_start_session_refuses_non_loopback_host(self, tmp_path):
        """Probe 1 (spawn half): refused before any process is spawned."""

        runtime_root, data_root, runtime_receipt = self._fake_binary_world(tmp_path)
        with pytest.raises(SessionError, match="loopback"):
            start_session(
                runtime_root=runtime_root,
                data_root=data_root,
                runtime_receipt=runtime_receipt,
                host="10.0.0.5",
                port=18082,
                session_id="spawn-test-3",
            )
