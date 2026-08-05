"""Runtime session attestation (R0 repair T5, invariant I5).

Reproduced defect: the frozen-core gate re-hashes the pinned llama.cpp binary,
its runtime libraries and the GGUF files on disk -- then the transport simply
POSTs to whatever ``base_url`` the config names. Nothing binds the RESPONDING
PROCESS to those hashed artifacts. These probes exercise the fix: a
``SessionReceipt`` binding binary/model identity, pid, argv, host and port,
obtained ONLY via ``start_session`` (spawns and observes) or ``attach_session``
(re-verifies an on-disk receipt against the runtime receipt, a live pid, and a
loopback host) -- and enforced a second, independent time by
``LlamaServerTransport`` itself at construction.

NO MODEL TOUCH: every spawn test below launches a FAKE POSIX shell-script
"binary" (the same pattern ``tests/unit/test_e0_generators.py`` already uses
for ``llama-server --version``), never the real llama-server.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.model import LlamaServerTransport
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
    (no real network, no real model -- fake bytes, like gate_fixture.py)."""

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
# verify_against_runtime_receipt -- probe 3 (binary hash mismatch refused).
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
# ---------------------------------------------------------------------------


def test_transport_refuses_without_a_session_receipt(tmp_path):
    """Probe 2: asked to send with no session receipt -> refused, before any
    __call__/send is even possible (construction itself fails closed)."""

    with pytest.raises(SessionError, match="session"):
        LlamaServerTransport("http://127.0.0.1:8080", tmp_path, None, {}, post=lambda u, b: b"")


def test_transport_refuses_non_loopback_base_url(tmp_path):
    """Probe 1 at the transport."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=8080)
    with pytest.raises(SessionError, match="loopback"):
        LlamaServerTransport(
            "http://10.0.0.5:8080", tmp_path, session, runtime_receipt, post=lambda u, b: b""
        )


def test_transport_refuses_session_with_binary_hash_mismatch(tmp_path):
    """Probe 3 at the transport: even a hand-built SessionReceipt (bypassing
    start_session/attach_session entirely) is refused here."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64)
    with pytest.raises(SessionError, match="binary identity"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, post=lambda u, b: b""
        )


def test_transport_refuses_session_port_mismatch_with_base_url(tmp_path):
    """Probe 6: a session receipt recorded for a different port than the
    transport's own base_url is refused, even though both are individually
    loopback-valid."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=9090)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, post=lambda u, b: b""
        )


def test_transport_refuses_session_host_mismatch_with_base_url(tmp_path):
    """Probe 6, host variant: 'localhost' and '127.0.0.1' are both loopback
    but not the SAME endpoint a session receipt was recorded for."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="localhost", port=8080)
    with pytest.raises(SessionError, match="does not match"):
        LlamaServerTransport(
            "http://127.0.0.1:8080", tmp_path, session, runtime_receipt, post=lambda u, b: b""
        )


def test_transport_accepts_a_valid_matching_session_and_sends(tmp_path):
    """Probe 7 (transport half): a legitimate session accepted, and an actual
    send still works exactly as before T5."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, host="127.0.0.1", port=8080)
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080",
        tmp_path,
        session,
        runtime_receipt,
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


# ---------------------------------------------------------------------------
# attach_session -- probes 3, 4.
# ---------------------------------------------------------------------------


def test_attach_refuses_missing_receipt_file(tmp_path):
    with pytest.raises(SessionError, match="cannot read"):
        attach_session(tmp_path / "does-not-exist.json", runtime_receipt={})


def test_attach_refuses_binary_hash_mismatch(tmp_path):
    """Probe 3 via attach."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, binary_sha256="0" * 64, pid=os.getpid())
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="binary identity"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt)


def test_attach_refuses_dead_pid(tmp_path):
    """Probe 4: attach to a dead PID -> refused."""

    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    session = _matching_session(runtime_receipt, pid=proc.pid)
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    with pytest.raises(SessionError, match="not a live process"):
        attach_session(receipt_path, runtime_receipt=runtime_receipt)


def test_attach_succeeds_for_a_live_matching_session(tmp_path):
    _, _, _, runtime_receipt = _runtime_world(tmp_path)
    session = _matching_session(runtime_receipt, pid=os.getpid())
    receipt_path = tmp_path / "session.json"
    write_session_receipt(receipt_path, session)
    attached = attach_session(receipt_path, runtime_receipt=runtime_receipt)
    assert attached == session


# ---------------------------------------------------------------------------
# start_session -- real spawn, POSIX-only, FAKE binary (never llama-server).
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
