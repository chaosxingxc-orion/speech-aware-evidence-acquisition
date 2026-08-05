"""Transport maps boundary payloads to chat-completions bodies without network.

Also enforces its own INDEPENDENT media-confinement rail (I4): the transport
must refuse an absolute/backslash/traversal/escaping ``media_relpath`` on its
own inputs, without relying on the adapter having already checked it."""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    LlamaServerTransport,
)
from speech_aware_evidence_acquisition.core.session import (
    SESSION_RECEIPT_SCHEMA,
    ModelFileRef,
    SessionReceipt,
)

# R0 repair T5 (I5): every LlamaServerTransport now requires a session receipt
# that has already been verified against a runtime receipt. These tests are
# about body-mapping/media-confinement behavior, not session attestation
# itself (see tests/unit/test_session.py for that) -- so every call site here
# goes through this one canonical, always-matching (session, runtime_receipt)
# pair via the ``_transport`` helper below, unless a test overrides them.
#
# R0 repair T5 fix-1 (reviewer-flagged CRITICAL gap): construction (and every
# send) now verifies the session's pid is ACTUALLY RUNNING the pinned binary
# image, not merely alive -- so the fake session below must be backed by a
# REAL process whose OS-reported executable image is genuinely the pinned
# binary file. A real copy of THIS interpreter, spawned once and shared for
# the whole module (session-attestation edge cases have their own dedicated
# coverage in tests/unit/test_session.py; these tests only need construction
# to succeed at all).
#
# R0 repair T5 fix-2 (materially equivalent gap a re-review demonstrated:
# PID/binary identity alone does not prove the pid OWNS the listening socket
# on the claimed port): the shared process must also genuinely bind and
# LISTEN on 127.0.0.1:8080 -- the literal base_url every test in this file
# already hardcodes -- for real, not merely sleep.

_BINARY_PATH = "llama.cpp/build/bin/llama-server"
_LIVE_PORT = 8080
_MODEL_FILES = (
    ModelFileRef(path="models/qwen3-omni/model.gguf", sha256="a" * 64),
    ModelFileRef(path="models/qwen3-omni/mmproj.gguf", sha256="b" * 64),
)

_live: dict[str, object] = {}


@pytest.fixture(scope="module", autouse=True)
def _spawn_live_matching_process(tmp_path_factory):
    import socket
    import time

    base = tmp_path_factory.mktemp("session-world")
    runtime_root = base / "runtime"
    binary = runtime_root / "llama.cpp" / "build" / "bin" / "llama-server"
    binary.parent.mkdir(parents=True)
    shutil.copy(sys.executable, binary)
    if os.name != "nt":
        binary.chmod(0o755)
    _live["runtime_root"] = runtime_root
    _live["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    listener_code = (
        "import socket, time\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        f"s.bind(('127.0.0.1', {_LIVE_PORT}))\n"
        "s.listen(1)\n"
        "time.sleep(300)\n"
    )
    process = subprocess.Popen(
        [str(binary), "-c", listener_code],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30.0  # first-exec AV-scan latency on a fresh copy, under load
    last_error = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", _LIVE_PORT), timeout=0.5):
                break
        except OSError as error:
            last_error = error
            time.sleep(0.05)
    else:
        process.kill()
        raise AssertionError(f"nothing ever listened on 127.0.0.1:{_LIVE_PORT}: {last_error}")
    _live["pid"] = process.pid
    yield
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _fake_runtime_receipt():
    return {
        "llama_cpp": {"binary_path": _BINARY_PATH, "binary_sha256": _live["binary_sha256"]},
        "gguf_files": [{"path": f.path, "sha256": f.sha256} for f in _MODEL_FILES],
    }


def _fake_session(*, host="127.0.0.1", port=8080):
    return SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id="test-session",
        binary_path=_BINARY_PATH,
        binary_sha256=_live["binary_sha256"],
        argv=(_BINARY_PATH, "--host", host, "--port", str(port)),
        pid=_live["pid"],
        host=host,
        port=port,
        model_files=_MODEL_FILES,
        started_at="2026-08-05T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
    )


def _transport(
    base_url, data_root, *, post, session=None, runtime_receipt=None, runtime_root=None, **kwargs
):
    return LlamaServerTransport(
        base_url,
        data_root,
        session if session is not None else _fake_session(),
        runtime_receipt if runtime_receipt is not None else _fake_runtime_receipt(),
        runtime_root if runtime_root is not None else _live["runtime_root"],
        post=post,
        **kwargs,
    )


def _boundary_payload(tmp_path, **overrides):
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
    payload.update(overrides)
    return payload


def _canned_response():
    return json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        }
    ).encode()


def test_body_mapping_and_response_projection(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["url"] = url
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport("http://127.0.0.1:8080", tmp_path, post=fake_post)
    raw = transport(json.dumps(_boundary_payload(tmp_path)).encode())
    result = json.loads(raw)
    assert result == {
        "text": "hello world",
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
    }
    assert captured["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    body = captured["body"]
    assert body["temperature"] == 0
    assert body["seed"] == 20260803
    assert body["messages"][0] == {
        "role": "system",
        "content": "Transcribe the speech verbatim.",
    }
    audio_part = body["messages"][1]["content"][0]
    assert audio_part["type"] == "input_audio"
    assert audio_part["input_audio"]["format"] == "mp3"
    assert base64.b64decode(audio_part["input_audio"]["data"]) == b"fake-mp3-bytes"


def test_evidence_items_become_text_parts(tmp_path):
    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert parts[1] == {"type": "text", "text": "[evidence ev-1] context text"}
        return _canned_response()

    transport = _transport("http://127.0.0.1:8080", tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {"evidence_id": "ev-1", "source_uri": "conec://x", "content": "context text"}
        ],
        evidence_provenance=[{"lock_key": "conec", "relpath": "x", "sha256": "0" * 64}],
    )
    transport(json.dumps(payload).encode())


def test_missing_media_fails_closed(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/absent.mp3")
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_decoding_params_cannot_override_constructed_messages(tmp_path):
    """Defense in depth: even called directly, a decoding_params "messages" key
    must never silently replace the constructed message list (which would drop
    audio while the adapter still meters it as delivered)."""

    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, decoding_params={"messages": []})
    with pytest.raises(FrozenCoreError, match="messages"):
        transport(json.dumps(payload).encode())


def test_malformed_usage_value_raises_frozen_core_error(tmp_path):
    response = json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": "NaN-ish-string", "completion_tokens": 2},
        }
    ).encode()
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: response
    )
    with pytest.raises(FrozenCoreError, match="malformed"):
        transport(json.dumps(_boundary_payload(tmp_path)).encode())


# ---------------------------------------------------------------------------
# I4: media confinement, the transport's own INDEPENDENT rail.
# ---------------------------------------------------------------------------


def test_absolute_media_relpath_outside_data_root_is_refused_not_read(tmp_path):
    """The reproduced defect, verified live: ``Path.__truediv__`` with an
    absolute right-hand side discards the left side, so
    ``self._data_root / payload["media_relpath"]`` silently resolved to a
    temp file OUTSIDE the data root, which was read and base64-sent. A
    canary transport (``post``) that would fail the test if it ever receives
    the outside file's bytes proves the fix refuses before any read/send."""

    outside_dir = tmp_path / "outside_data_root"
    outside_dir.mkdir()
    secret = outside_dir / "secret.mp3"
    secret.write_bytes(b"outside-the-data-root-should-never-be-sent")

    def _canary_post(url, body):
        decoded = json.loads(body)
        for part in decoded["messages"][1]["content"]:
            if part.get("type") == "input_audio":
                sent = base64.b64decode(part["input_audio"]["data"])
                assert sent != secret.read_bytes(), "outside-root file bytes were sent"
        return _canned_response()

    data_root = tmp_path / "data"
    data_root.mkdir()
    transport = _transport("http://127.0.0.1:8080", data_root, post=_canary_post)
    payload = _boundary_payload(data_root, media_relpath=str(secret))
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_drive_letter_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="C:/secret.txt")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_backslash_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media\\5000001.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_traversal_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="../outside/secret.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_missing_media_still_raises_file_not_found_after_confinement_check(tmp_path):
    """The confinement check must not change the existing missing-media
    behavior for a syntactically clean, in-root relative path."""

    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/absent.mp3")
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


@pytest.mark.skipif(os.name == "nt", reason="POSIX symlink required")
def test_media_relpath_symlink_escape_refused_at_transport(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leaked.mp3").write_bytes(b"leaked-bytes")
    (data_root / "media_link").symlink_to(outside, target_is_directory=True)

    transport = _transport(
        "http://127.0.0.1:8080", data_root, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(data_root, media_relpath="media_link/leaked.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


@pytest.mark.skipif(os.name != "nt", reason="Windows junction probe")
def test_media_relpath_windows_junction_escape_refused_at_transport(tmp_path):
    """Windows-native equivalent of the POSIX symlink-escape probe above: a
    junction (``mklink /J``, no elevation required) is a reparse point
    ``Path.resolve()`` follows exactly like a symlink. If junction creation
    itself fails in this environment, the test skips with that reason rather
    than passing vacuously."""

    data_root = tmp_path / "data"
    data_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "leaked.mp3").write_bytes(b"leaked-bytes")
    link = data_root / "media_link"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not link.exists():
        pytest.skip(
            "Windows junction creation failed in this environment "
            f"(rc={result.returncode}): {result.stderr or result.stdout}"
        )

    transport = _transport(
        "http://127.0.0.1:8080", data_root, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(data_root, media_relpath="media_link/leaked.mp3")
    with pytest.raises(FrozenCoreError, match="escapes"):
        transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# I4 defense in depth: per-segment Windows-only looseness (trailing dot/space,
# NTFS alternate-data-stream colon) -- see test_frozen_core_adapter.py's
# mirror tests for the rationale.
# ---------------------------------------------------------------------------


def test_media_relpath_trailing_dot_segment_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3.")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_trailing_space_segment_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3 ")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_colon_in_segment_refused_at_transport(tmp_path):
    transport = _transport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3:hidden")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())
