"""Transport maps boundary payloads to chat-completions bodies without network.

Also enforces its own INDEPENDENT media-confinement rail (I4): the transport
must refuse an absolute/backslash/traversal/escaping ``media_relpath`` on its
own inputs, without relying on the adapter having already checked it."""

import base64
import json
import os
import subprocess

import pytest

from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    LlamaServerTransport,
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

    transport = LlamaServerTransport("http://127.0.0.1:8080", tmp_path, post=fake_post)
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

    transport = LlamaServerTransport("http://127.0.0.1:8080", tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {"evidence_id": "ev-1", "source_uri": "conec://x", "content": "context text"}
        ],
        evidence_provenance=[{"lock_key": "conec", "relpath": "x", "sha256": "0" * 64}],
    )
    transport(json.dumps(payload).encode())


def test_missing_media_fails_closed(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/absent.mp3")
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_decoding_params_cannot_override_constructed_messages(tmp_path):
    """Defense in depth: even called directly, a decoding_params "messages" key
    must never silently replace the constructed message list (which would drop
    audio while the adapter still meters it as delivered)."""

    transport = LlamaServerTransport(
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
    transport = LlamaServerTransport(
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
    transport = LlamaServerTransport("http://127.0.0.1:8080", data_root, post=_canary_post)
    payload = _boundary_payload(data_root, media_relpath=str(secret))
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_drive_letter_media_relpath_refused_at_transport(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="C:/secret.txt")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_backslash_media_relpath_refused_at_transport(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media\\5000001.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_traversal_media_relpath_refused_at_transport(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="../outside/secret.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_missing_media_still_raises_file_not_found_after_confinement_check(tmp_path):
    """The confinement check must not change the existing missing-media
    behavior for a syntactically clean, in-root relative path."""

    transport = LlamaServerTransport(
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

    transport = LlamaServerTransport(
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

    transport = LlamaServerTransport(
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
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3.")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_trailing_space_segment_refused_at_transport(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3 ")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_colon_in_segment_refused_at_transport(tmp_path):
    transport = LlamaServerTransport(
        "http://127.0.0.1:8080", tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3:hidden")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())
