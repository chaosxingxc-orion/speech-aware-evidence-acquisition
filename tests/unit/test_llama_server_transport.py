"""Transport maps boundary payloads to chat-completions bodies without network.

Also enforces its own INDEPENDENT media-confinement rail (I4): the transport
must refuse an absolute/backslash/traversal/escaping ``media_relpath`` on its
own inputs, without relying on the adapter having already checked it."""

import base64
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import threading
import time

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.base import EvidenceItem
from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreError,
    LlamaServerTransport,
    SpeechFeatureChunkData,
    legacy_audio_feature_cache_key,
    load_speech_feature_packet,
    load_speech_feature_packets,
    materialize_legacy_cached_speech_feature_packet,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.model.transport import _llama_server_factory
from speech_aware_evidence_acquisition.core.policies import build_arm_payload
from speech_aware_evidence_acquisition.core.session import (
    SESSION_RECEIPT_SCHEMA,
    SESSION_RECEIPT_SCHEMA_V2,
    ModelFileRef,
    SessionError,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.data.loader import SampleRef

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
# LISTEN on 127.0.0.1:<port> -- every test in this file uses the same
# base_url via ``_base_url()`` below -- for real, not merely sleep.
#
# 2026-08-09 (ephemeral port, do not re-hardcode 8080): this module used to
# hardcode _LIVE_PORT = 8080 and every base_url string to match. 8080 is
# also the port real experiments serve llama-server on; measured live, a
# real llama-server already listening on 8080 made this fixture's own
# readiness probe (a bare ``socket.create_connection`` to the hardcoded
# port) report success while the fixture's OWN bind() had actually failed
# with EADDRINUSE, so every test then failed downstream with a confusing
# "pid does not own the listening socket" error instead of a clear setup
# failure. The fixture now binds port 0 (OS-assigned, collision-free by
# construction) and the spawned child reports back the exact port it got;
# see ``_spawn_live_matching_process`` for how readiness is proven from
# that self-report rather than assumed from a hardcoded literal.

_BINARY_PATH = "llama.cpp/build/bin/llama-server"
_MODEL_FILES = (
    ModelFileRef(path="models/qwen3-omni/model.gguf", sha256="a" * 64),
    ModelFileRef(path="models/qwen3-omni/mmproj.gguf", sha256="b" * 64),
)

_live: dict[str, object] = {}


@pytest.fixture(scope="module", autouse=True)
def _spawn_live_matching_process(tmp_path_factory):
    import queue
    import socket
    import threading
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
    # bind(('127.0.0.1', 0)) asks the OS for an unused ephemeral port --
    # collision-free by construction, unlike a hardcoded literal (see
    # 2026-08-09 note above). The child prints back the exact port it was
    # handed so the parent never has to assume a number.
    listener_code = (
        "import socket, time\n"
        "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)\n"
        "s.bind(('127.0.0.1', 0))\n"
        "s.listen(1)\n"
        "print(s.getsockname()[1], flush=True)\n"
        "time.sleep(300)\n"
    )
    # Fresh-spawn retry (not just a longer wait): this sandboxed Windows
    # host occasionally stalls an individual spawned process for tens of
    # seconds under load; a fresh process recovers more reliably than
    # waiting longer on a possibly wedged one.
    process = None
    last_error = None
    live_port = None
    for _attempt in range(3):
        process = subprocess.Popen(
            [str(binary), "-c", listener_code],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        # Readiness proof, three independent legs -- a bare connect()
        # succeeding is NOT proof (that is exactly the T5 fix-2 defect this
        # fixture exists to demonstrate, and hardcoding a port made it
        # trivial to reintroduce by accident): (1) the child itself -- the
        # only party that actually knows which ephemeral port the OS gave
        # it -- self-reports that port over stdout; (2) the child process is
        # still alive at the moment we check; (3) a real connect() to
        # EXACTLY that self-reported port succeeds.
        port_box: "queue.Queue[str]" = queue.Queue(maxsize=1)

        def _read_port_line(stream=process.stdout, box=port_box):
            box.put(stream.readline())

        threading.Thread(target=_read_port_line, daemon=True).start()
        try:
            reported = port_box.get(timeout=15.0)
        except queue.Empty:
            reported = ""
        candidate_port = None
        if reported and process.poll() is None:
            try:
                candidate_port = int(reported.strip())
            except ValueError:
                last_error = f"listener printed non-port garbage: {reported!r}"
                candidate_port = None
        elif not reported:
            last_error = "listener never printed a port before the 15s deadline"
        elif process.poll() is not None:
            last_error = f"listener exited early (returncode={process.poll()})"
        if candidate_port is not None:
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                try:
                    with socket.create_connection(
                        ("127.0.0.1", candidate_port), timeout=0.5
                    ):
                        live_port = candidate_port
                        break
                except OSError as error:
                    last_error = error
                    time.sleep(0.05)
        if live_port is not None:
            break
        process.kill()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        process = None
    if process is None:
        raise AssertionError(
            f"no spawned listener ever self-reported and confirmed a live port "
            f"on 127.0.0.1: {last_error}"
        )
    _live["pid"] = process.pid
    _live["port"] = live_port
    yield
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _fake_runtime_receipt():
    return {
        "llama_cpp": {
            "binary_path": _BINARY_PATH,
            "binary_sha256": _live["binary_sha256"],
        },
        "gguf_files": [{"path": f.path, "sha256": f.sha256} for f in _MODEL_FILES],
    }


def _base_url():
    """The fixture's ephemeral port, read only after the module-scoped
    fixture has run (never a hardcoded literal -- see 2026-08-09 note)."""

    return f"http://127.0.0.1:{_live['port']}"


def _fake_session(*, host="127.0.0.1", port=None):
    if port is None:
        port = _live["port"]
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


def _fake_inference_session(*, host="127.0.0.1", port=None):
    if port is None:
        port = _live["port"]
    return SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA_V2,
        study=STUDY_SLUG,
        session_id="test-inference-session",
        binary_path=_BINARY_PATH,
        binary_sha256=_live["binary_sha256"],
        argv=(
            _BINARY_PATH,
            "--host",
            host,
            "--port",
            str(port),
            "-m",
            _MODEL_FILES[0].path,
            "--no-mmproj",
        ),
        pid=_live["pid"],
        host=host,
        port=port,
        model_files=(_MODEL_FILES[0],),
        started_at="2026-08-21T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
        role="inference",
        server_env_keys=(),
    )


def _transport(
    base_url,
    data_root,
    *,
    post,
    session=None,
    runtime_receipt=None,
    runtime_root=None,
    **kwargs,
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


def _materialize_packet(feature_root, packet_id="slurp/train/s1"):
    return materialize_speech_feature_packet(
        feature_root=feature_root,
        packet_id=packet_id,
        audio_sha256="a" * 64,
        encoder_receipt_sha256="e" * 64,
        decoder_gguf_sha256=_MODEL_FILES[0].sha256,
        mmproj_sha256=_MODEL_FILES[1].sha256,
        position_mode="mrope_1d",
        causal_attention=True,
        chunks=(
            SpeechFeatureChunkData(
                n_tokens=2,
                n_pos=2,
                n_embd=4,
                feature_bytes=struct.pack("<8f", *range(8)),
                position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
            ),
        ),
    )


def test_body_mapping_and_response_projection(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["url"] = url
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    raw = transport(json.dumps(_boundary_payload(tmp_path)).encode())
    result = json.loads(raw)
    assert result == {
        "text": "hello world",
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
    }
    assert captured["url"] == f"{_base_url()}/v1/chat/completions"
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


def test_speech_feature_prompt_order_sends_packet_reference_without_raw_audio(tmp_path):
    feature_root = tmp_path / "features"
    packet = _materialize_packet(feature_root)
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        session=_fake_inference_session(),
        prompt_order="speech-features-text-keys-v1",
        feature_root=feature_root,
    )
    payload = _boundary_payload(
        tmp_path,
        task_instruction="Choose exactly one opaque key id.",
        supplied_evidence=[{"evidence_id": "key-001", "content": "Turn a light on."}],
        speech_feature_parts=[
            {
                "packet_id": "slurp/train/s1",
                "sha256": packet.packet_sha256,
                "role": "query",
            }
        ],
        speech_packet_sha256=packet.packet_sha256,
        query_source="speech_features",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
        mmproj_loaded=False,
    )
    transport(json.dumps(payload).encode())
    parts = captured["body"]["messages"][1]["content"]
    assert parts[0] == {"type": "text", "text": "[evidence key-001] Turn a light on."}
    assert parts[1] == {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": "slurp/train/s1",
            "sha256": packet.packet_sha256,
            "role": "query",
        },
    }
    assert all(part["type"] != "input_audio" for part in parts)


@pytest.mark.parametrize(
    ("prompt_order", "expected_types", "expected_speech_roles"),
    (
        (
            "speech-query-prefix-v2",
            (
                "input_speech_features",
                "text",
                "input_speech_features",
                "text",
            ),
            ("query", "key"),
        ),
        (
            "knowledge-speech-state-v2",
            (
                "text",
                "input_speech_features",
                "input_speech_features",
                "text",
            ),
            ("key", "query"),
        ),
    ),
)
def test_agent_loop_prompt_orders_keep_mutable_state_after_the_query_packet(
    tmp_path, prompt_order, expected_types, expected_speech_roles
):
    feature_root = tmp_path / "features"
    query = _materialize_packet(feature_root, "slurp/train/query")
    key = _materialize_packet(feature_root, "slurp/train/key")
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        session=_fake_inference_session(),
        prompt_order=prompt_order,
        feature_root=feature_root,
    )
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {"evidence_id": "stable-key-catalog", "content": "Opaque key cards."},
            {"evidence_id": "dynamic-agent-step", "content": "Choose one key now."},
        ],
        speech_feature_parts=[
            {
                "packet_id": query.packet_id,
                "sha256": query.packet_sha256,
                "role": "query",
            },
            {
                "packet_id": key.packet_id,
                "sha256": key.packet_sha256,
                "role": "key",
            },
        ],
        speech_packet_sha256=query.packet_sha256,
        query_source="speech_features",
        key_representation_id="k4-hybrid-key-v1",
        matcher_policy_id="m11-agent-loop-v1",
        mmproj_loaded=False,
    )

    transport(json.dumps(payload).encode())

    parts = captured["body"]["messages"][1]["content"]
    assert tuple(part["type"] for part in parts) == expected_types
    assert (
        tuple(
            part["speech_features"]["role"]
            for part in parts
            if part["type"] == "input_speech_features"
        )
        == expected_speech_roles
    )
    assert parts[-1] == {
        "type": "text",
        "text": "[evidence dynamic-agent-step] Choose one key now.",
    }
    query_index = next(
        index
        for index, part in enumerate(parts)
        if part["type"] == "input_speech_features"
        and part["speech_features"]["role"] == "query"
    )
    assert query_index < len(parts) - 1
    assert all(part["type"] != "input_audio" for part in parts)


@pytest.mark.parametrize(
    ("prompt_order", "stable_prefix_length"),
    (
        ("speech-query-prefix-v2", 1),
        ("knowledge-speech-state-v2", 3),
    ),
)
def test_agent_loop_wire_requests_have_an_identical_prefix_before_mutable_state(
    tmp_path, prompt_order, stable_prefix_length
):
    feature_root = tmp_path / "features"
    query = _materialize_packet(feature_root, "slurp/train/query")
    key = _materialize_packet(feature_root, "slurp/train/key")
    captured = []

    def fake_post(url, body):
        captured.append(json.loads(body))
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        session=_fake_inference_session(),
        prompt_order=prompt_order,
        feature_root=feature_root,
    )
    common = {
        "speech_feature_parts": [
            {
                "packet_id": query.packet_id,
                "sha256": query.packet_sha256,
                "role": "query",
            },
            {
                "packet_id": key.packet_id,
                "sha256": key.packet_sha256,
                "role": "key",
            },
        ],
        "speech_packet_sha256": query.packet_sha256,
        "query_source": "speech_features",
        "key_representation_id": "k4-hybrid-key-v1",
        "matcher_policy_id": "m11-agent-loop-v1",
        "mmproj_loaded": False,
    }
    for evidence_id, instruction in (
        ("agent-step-a", "Choose one key."),
        ("agent-step-b", "Verify that key."),
    ):
        payload = _boundary_payload(
            tmp_path,
            supplied_evidence=[
                {"evidence_id": "stable-key-catalog", "content": "Opaque key cards."},
                {"evidence_id": evidence_id, "content": instruction},
            ],
            **common,
        )
        transport(json.dumps(payload).encode())

    first = captured[0]["messages"][1]["content"]
    second = captured[1]["messages"][1]["content"]
    assert first[:stable_prefix_length] == second[:stable_prefix_length]
    assert first[stable_prefix_length:] != second[stable_prefix_length:]


@pytest.mark.parametrize(
    ("prompt_order", "expected_order"),
    (
        (
            "speech-query-prefix-v2",
            (
                "speech:query",
                "[evidence stable-key-a] Opaque key A.",
                "[evidence stable-key-b] Opaque key B.",
                "[evidence retrieved-value] Train-derived value.",
                "[agent state state:operation-needed kind=intent-factor] "
                "The unresolved factor is the operation.",
                "[agent control contact-2] Solve the task now.",
            ),
        ),
        (
            "knowledge-speech-state-v2",
            (
                "[evidence stable-key-a] Opaque key A.",
                "[evidence stable-key-b] Opaque key B.",
                "speech:query",
                "[evidence retrieved-value] Train-derived value.",
                "[agent state state:operation-needed kind=intent-factor] "
                "The unresolved factor is the operation.",
                "[agent control contact-2] Solve the task now.",
            ),
        ),
    ),
)
def test_registered_v2_prompt_orders_preserve_agent_history_as_an_ordered_suffix(
    tmp_path, prompt_order, expected_order
):
    feature_root = tmp_path / "features"
    query = _materialize_packet(feature_root, "slurp/train/query")
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        session=_fake_inference_session(),
        prompt_order=prompt_order,
        feature_root=feature_root,
    )
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {
                "evidence_id": "stable-key-a",
                "content": "Opaque key A.",
                "knowledge_role": "key",
            },
            {
                "evidence_id": "stable-key-b",
                "content": "Opaque key B.",
                "knowledge_role": "key",
            },
            {
                "evidence_id": "retrieved-value",
                "content": "Train-derived value.",
                "knowledge_role": "value",
            },
        ],
        history=[
            {
                "turn": 1,
                "role": "agent_state",
                "state_id": "state:operation-needed",
                "state_kind": "intent-factor",
                "content": "The unresolved factor is the operation.",
                "content_sha256": hashlib.sha256(
                    b"The unresolved factor is the operation."
                ).hexdigest(),
                "source_query_state_sha256": "1" * 64,
                "source_response_sha256": "2" * 64,
                "producer_policy_id": "organize-v1",
                "cited_value_ids": [],
            },
            {
                "turn": 2,
                "role": "control",
                "contact_id": "contact-2",
                "content": "Solve the task now.",
                "content_sha256": hashlib.sha256(b"Solve the task now.").hexdigest(),
            },
        ],
        speech_feature_parts=[
            {
                "packet_id": query.packet_id,
                "sha256": query.packet_sha256,
                "role": "query",
            }
        ],
        speech_packet_sha256=query.packet_sha256,
        query_source="speech_features",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="agent-loop-v1",
        mmproj_loaded=False,
    )

    transport(json.dumps(payload).encode())

    parts = captured["body"]["messages"][1]["content"]
    observed_order = tuple(
        (
            f"speech:{part['speech_features']['role']}"
            if part["type"] == "input_speech_features"
            else part["text"]
        )
        for part in parts
    )
    assert observed_order == expected_order


def test_agent_history_retention_fails_closed_before_transport_contact(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.model import (
        transport as transport_module,
    )

    feature_root = tmp_path / "features"
    query = _materialize_packet(feature_root, "slurp/train/query")
    contacts = []

    def fake_post(url, body):
        contacts.append(json.loads(body))
        return _canned_response()

    original_ordering = transport_module._ordered_speech_feature_content

    def drop_agent_history(**kwargs):
        ordered = original_ordering(**kwargs)
        state_count = len(kwargs["state_texts"])
        return ordered[:-state_count] if state_count else ordered

    monkeypatch.setattr(
        transport_module,
        "_ordered_speech_feature_content",
        drop_agent_history,
    )
    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        session=_fake_inference_session(),
        prompt_order="knowledge-speech-state-v2",
        feature_root=feature_root,
    )
    control_text = "Solve the task using the original speech query."
    payload = _boundary_payload(
        tmp_path,
        history=[
            {
                "turn": 1,
                "role": "control",
                "contact_id": "contact-1",
                "content": control_text,
                "content_sha256": hashlib.sha256(control_text.encode()).hexdigest(),
            }
        ],
        speech_feature_parts=[
            {
                "packet_id": query.packet_id,
                "sha256": query.packet_sha256,
                "role": "query",
            }
        ],
        speech_packet_sha256=query.packet_sha256,
        query_source="speech_features",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="agent-loop-v1",
        mmproj_loaded=False,
    )

    with pytest.raises(FrozenCoreError, match="preserve Agent state/control"):
        transport(json.dumps(payload).encode())

    assert contacts == []


def test_speech_feature_transport_batch_validates_query_and_key_packets(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.model import (
        transport as transport_module,
    )

    feature_root = tmp_path / "features"
    query = _materialize_packet(feature_root, "slurp/train/query")
    key = _materialize_packet(feature_root, "slurp/train/key")
    original = transport_module.load_speech_feature_packets
    calls = []

    def tracked_loader(root, bindings, **kwargs):
        calls.append((root, tuple(bindings), kwargs))
        return original(root, bindings, **kwargs)

    monkeypatch.setattr(transport_module, "load_speech_feature_packets", tracked_loader)
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        session=_fake_inference_session(),
        prompt_order="speech-features-text-keys-v1",
        feature_root=feature_root,
    )
    payload = _boundary_payload(
        tmp_path,
        speech_feature_parts=[
            {
                "packet_id": query.packet_id,
                "sha256": query.packet_sha256,
                "role": "query",
            },
            {"packet_id": key.packet_id, "sha256": key.packet_sha256, "role": "key"},
        ],
        speech_packet_sha256=query.packet_sha256,
        query_source="speech_features",
        key_representation_id="k3-audio-key-v1",
        matcher_policy_id="m1-listwise-v1",
        mmproj_loaded=False,
    )

    transport(json.dumps(payload).encode())

    assert len(calls) == 1
    assert calls[0][2]["workers"] == 8
    assert [binding["packet_id"] for binding in calls[0][1]] == [
        query.packet_id,
        key.packet_id,
    ]


@pytest.mark.parametrize(
    "prompt_order",
    (
        "speech-features-text-keys-v1",
        "speech-query-prefix-v2",
        "knowledge-speech-state-v2",
    ),
)
def test_speech_feature_prompt_order_requires_inference_session_and_fixed_root(
    tmp_path, prompt_order
):
    with pytest.raises(SessionError, match="inference session"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda u, b: _canned_response(),
            prompt_order=prompt_order,
            feature_root=tmp_path / "features",
        )
    with pytest.raises(SessionError, match="feature_root"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda u, b: _canned_response(),
            session=_fake_inference_session(),
            prompt_order=prompt_order,
        )


def test_speech_feature_transport_fails_closed_on_corruption_and_inline_arrays(
    tmp_path,
):
    feature_root = tmp_path / "features"
    packet = _materialize_packet(feature_root)
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        session=_fake_inference_session(),
        prompt_order="speech-features-text-keys-v1",
        feature_root=feature_root,
    )
    payload = _boundary_payload(
        tmp_path,
        query_source="speech_features",
        key_representation_id="k1-text-card-v1",
        matcher_policy_id="m1-listwise-v1",
        mmproj_loaded=False,
        speech_packet_sha256=packet.packet_sha256,
        speech_feature_parts=[
            {
                "packet_id": "slurp/train/s1",
                "sha256": packet.packet_sha256,
                "role": "query",
                "values": [0.0, 1.0],
            }
        ],
    )
    with pytest.raises(FrozenCoreError, match="exact keys"):
        transport(json.dumps(payload).encode())

    feature_file = feature_root / "slurp/train/s1/chunks/0000.f32"
    feature_file.write_bytes(b"corrupt")
    payload["speech_feature_parts"] = [
        {
            "packet_id": "slurp/train/s1",
            "sha256": packet.packet_sha256,
            "role": "query",
        }
    ]
    with pytest.raises(FrozenCoreError, match="feature bytes"):
        transport(json.dumps(payload).encode())


def test_speech_feature_packet_loader_rejects_escape_model_and_dimension_mismatch(
    tmp_path,
):
    feature_root = tmp_path / "features"
    packet = _materialize_packet(feature_root)
    with pytest.raises(FrozenCoreError, match="traversal"):
        load_speech_feature_packet(feature_root, "../outside")
    with pytest.raises(FrozenCoreError, match="different decoder"):
        load_speech_feature_packet(
            feature_root,
            packet.packet_id,
            expected_decoder_gguf_sha256="c" * 64,
        )
    with pytest.raises(FrozenCoreError, match="n_embd"):
        load_speech_feature_packet(
            feature_root,
            packet.packet_id,
            expected_n_embd=8,
        )


def test_speech_feature_packet_batch_validation_is_parallel_and_ordered(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.model import speech_features

    feature_root = tmp_path / "features"
    packets = tuple(
        _materialize_packet(feature_root, f"slurp/train/s{index}") for index in range(6)
    )
    original = speech_features.load_speech_feature_packet
    lock = threading.Lock()
    active = 0
    peak = 0

    def tracked_loader(*args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        try:
            return original(*args, **kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(speech_features, "load_speech_feature_packet", tracked_loader)
    loaded = load_speech_feature_packets(
        feature_root,
        tuple(
            {"packet_id": packet.packet_id, "sha256": packet.packet_sha256}
            for packet in reversed(packets)
        ),
        workers=3,
        expected_decoder_gguf_sha256=_MODEL_FILES[0].sha256,
        expected_n_embd=4,
    )

    assert [packet.packet_id for packet in loaded] == [
        packet.packet_id for packet in reversed(packets)
    ]
    assert 2 <= peak <= 3


def test_speech_feature_packet_materialization_is_idempotent_but_never_overwrites(
    tmp_path,
):
    feature_root = tmp_path / "features"
    packet = _materialize_packet(feature_root)
    assert _materialize_packet(feature_root).packet_sha256 == packet.packet_sha256
    with pytest.raises(FrozenCoreError, match="different source/model metadata"):
        materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=packet.packet_id,
            audio_sha256="b" * 64,
            encoder_receipt_sha256="e" * 64,
            decoder_gguf_sha256=_MODEL_FILES[0].sha256,
            mmproj_sha256=_MODEL_FILES[1].sha256,
            position_mode="mrope_1d",
            causal_attention=True,
            chunks=(
                SpeechFeatureChunkData(
                    n_tokens=2,
                    n_pos=2,
                    n_embd=4,
                    feature_bytes=struct.pack("<8f", *range(8)),
                    position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
                ),
            ),
        )


def test_existing_legacy_featcache_is_promoted_without_reencoding(tmp_path):
    audio = tmp_path / "audio.flac"
    audio.write_bytes(b"existing-governed-audio")
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    key = legacy_audio_feature_cache_key(audio.read_bytes())
    features = struct.pack("<8f", *[float(i) for i in range(8)])
    (legacy / f"{key}_o0.feat").write_bytes(struct.pack("<QQ", 2, 4) + features)

    packet = materialize_legacy_cached_speech_feature_packet(
        feature_root=tmp_path / "packets",
        packet_id="slurp/devel/example",
        audio_path=audio,
        legacy_cache_dir=legacy,
        encoder_receipt_sha256="1" * 64,
        decoder_gguf_sha256="2" * 64,
        mmproj_sha256="3" * 64,
        expected_n_embd=4,
        causal_attention=True,
    )

    assert packet.audio_sha256 == hashlib.sha256(audio.read_bytes()).hexdigest()
    assert len(packet.chunks) == 1
    assert packet.chunks[0].n_tokens == packet.chunks[0].n_pos == 2
    packet_dir = tmp_path / "packets" / "slurp" / "devel" / "example"
    assert (packet_dir / packet.chunks[0].feature_relpath).read_bytes() == features
    assert struct.unpack(
        "<8i", (packet_dir / packet.chunks[0].position_relpath).read_bytes()
    ) == (0, 1, 0, 1, 0, 1, 0, 1)


def test_legacy_featcache_promotion_refuses_gaps_and_wrong_decoder_dimension(tmp_path):
    audio = tmp_path / "audio.flac"
    audio.write_bytes(b"existing-governed-audio")
    legacy = tmp_path / "legacy-cache"
    legacy.mkdir()
    key = legacy_audio_feature_cache_key(audio.read_bytes())
    (legacy / f"{key}_o1.feat").write_bytes(
        struct.pack("<QQ", 2, 4) + struct.pack("<8f", *([0.0] * 8))
    )
    kwargs = dict(
        feature_root=tmp_path / "packets",
        packet_id="slurp/devel/example",
        audio_path=audio,
        legacy_cache_dir=legacy,
        encoder_receipt_sha256="1" * 64,
        decoder_gguf_sha256="2" * 64,
        mmproj_sha256="3" * 64,
        expected_n_embd=4,
        causal_attention=True,
    )
    with pytest.raises(FrozenCoreError, match="ordinal zero"):
        materialize_legacy_cached_speech_feature_packet(**kwargs)

    (legacy / f"{key}_o0.feat").write_bytes(
        struct.pack("<QQ", 2, 5) + struct.pack("<10f", *([0.0] * 10))
    )
    with pytest.raises(FrozenCoreError, match="decoder dimension"):
        materialize_legacy_cached_speech_feature_packet(**kwargs)


def test_prompt_order_v2_moves_evidence_into_system_ahead_of_instruction(tmp_path):
    """SAEA-BENCH-cacheorder-q4km (2026-08-11): stable-first order — evidence
    text joins the SYSTEM message ahead of the instruction(+tail), user
    content carries only the audio, and the evidence formatting strings stay
    byte-identical to v1 (only their position moves)."""

    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        prompt_order="evidence-first-system-v2",
    )
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {"evidence_id": "e1", "content": "Acme Corp Q3"},
            {"evidence_id": "e2", "content": "CEO Jane Doe"},
        ],
    )
    transport(json.dumps(payload).encode())
    messages = captured["body"]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == (
        "[evidence e1] Acme Corp Q3\n\n[evidence e2] CEO Jane Doe\n\n"
        "Transcribe the speech verbatim."
    )
    assert [part["type"] for part in messages[1]["content"]] == ["input_audio"]


def test_prompt_order_v2_without_evidence_is_byte_identical_to_v1(tmp_path):
    """Arms without evidence must produce byte-identical requests under both
    orders — the change is scoped to exactly the arms it targets."""

    bodies = {}

    def make_post(key):
        def fake_post(url, body):
            bodies[key] = body
            return _canned_response()

        return fake_post

    for key, order in (
        ("v1", "system-instruction-v1"),
        ("v2", "evidence-first-system-v2"),
    ):
        transport = _transport(
            _base_url(), tmp_path, post=make_post(key), prompt_order=order
        )
        transport(json.dumps(_boundary_payload(tmp_path)).encode())
    assert bodies["v1"] == bodies["v2"]


def test_unknown_prompt_order_refused_at_construction(tmp_path):
    with pytest.raises(Exception, match="prompt_order"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda u, b: _canned_response(),
            prompt_order="evidence-last",
        )


def test_usage_with_nested_detail_objects_keeps_scalar_counters_only(tmp_path):
    """2026-08-08: the first successful real request died at the LAST step —
    newer llama-server usage blocks carry nested objects (OpenAI-style
    `*_tokens_details`), and int(dict) raised. Scalar counters must survive;
    non-scalar entries are dropped, never fatal."""

    def fake_post(url, body):
        return json.dumps(
            {
                "choices": [{"message": {"content": "transcript text"}}],
                "usage": {
                    "prompt_tokens": 56032,
                    "completion_tokens": 800,
                    "total_tokens": 56832,
                    "prompt_tokens_details": {
                        "cached_tokens": 0,
                        "audio_tokens": 55000,
                    },
                },
            }
        ).encode()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    result = json.loads(transport(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert result["text"] == "transcript text"
    assert result["usage"] == {
        "prompt_tokens": 56032,
        "completion_tokens": 800,
        "total_tokens": 56832,
    }


def test_http_error_surfaces_status_and_server_body(tmp_path):
    """2026-08-08: the first real smoke died on a bare `HTTPError: 400` with the
    server's diagnostic body silently discarded — the transport must surface
    status + body so an operator learns WHY (context overflow, bad schema, …)
    without a second spend against the call budget."""

    import io
    import urllib.error

    def fake_post(url, body):
        raise urllib.error.HTTPError(
            url,
            400,
            "Bad Request",
            None,
            io.BytesIO(
                b'{"error":{"message":"the request exceeds the available context size"}}'
            ),
        )

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    with pytest.raises(
        FrozenCoreError, match="HTTP 400.*exceeds the available context"
    ):
        transport(json.dumps(_boundary_payload(tmp_path)).encode())


def test_evidence_items_become_text_parts(tmp_path):
    def fake_post(url, body):
        # 2026-08-09 prefix-cache reorder: evidence text parts now precede
        # the audio part (see test_content_order_* below for the full
        # ordering contract) -- this test keeps checking the text-part
        # SHAPE, now at index 0 rather than index 1.
        parts = json.loads(body)["messages"][1]["content"]
        assert parts[0] == {"type": "text", "text": "[evidence ev-1] context text"}
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {
                "evidence_id": "ev-1",
                "source_uri": "conec://x",
                "content": "context text",
            }
        ],
        evidence_provenance=[{"lock_key": "conec", "relpath": "x", "sha256": "0" * 64}],
    )
    transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# Prefix-cache-friendly content order (2026-08-09): stable evidence text
# FIRST, variable audio LAST -- see the module docstring for the measured
# server-side justification. The prefix (system message + evidence text)
# must be byte-identical and contiguous across requests sharing the same
# evidence block for llama-server to reuse its KV-cache prefix; content
# placed after the audio does not get this benefit, so audio must be last.
# ---------------------------------------------------------------------------


def test_content_order_is_evidence_then_audio_when_evidence_present(tmp_path):
    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert [part["type"] for part in parts] == ["text", "input_audio"]
        assert parts[0] == {"type": "text", "text": "[evidence ev-1] context text"}
        assert parts[1]["type"] == "input_audio"
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {
                "evidence_id": "ev-1",
                "source_uri": "conec://x",
                "content": "context text",
            }
        ],
        evidence_provenance=[{"lock_key": "conec", "relpath": "x", "sha256": "0" * 64}],
    )
    transport(json.dumps(payload).encode())


def test_content_order_is_audio_alone_when_no_evidence(tmp_path):
    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert [part["type"] for part in parts] == ["input_audio"]
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(tmp_path)
    assert "supplied_evidence" not in payload
    assert "retrieved_evidence" not in payload
    transport(json.dumps(payload).encode())


def test_content_order_preserves_multi_evidence_order_before_audio(tmp_path):
    """Multiple supplied_evidence AND retrieved_evidence items: all evidence
    text parts precede the audio part, in the existing deterministic order
    (supplied_evidence list order, then retrieved_evidence list order --
    unchanged from before this reorder, only their position relative to the
    audio part moves)."""

    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert [part["type"] for part in parts] == [
            "text",
            "text",
            "text",
            "input_audio",
        ]
        assert parts[0] == {"type": "text", "text": "[evidence sup-1] supplied one"}
        assert parts[1] == {"type": "text", "text": "[evidence sup-2] supplied two"}
        assert parts[2] == {"type": "text", "text": "[evidence ret-1] retrieved one"}
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {
                "evidence_id": "sup-1",
                "source_uri": "conec://a",
                "content": "supplied one",
            },
            {
                "evidence_id": "sup-2",
                "source_uri": "conec://b",
                "content": "supplied two",
            },
        ],
        retrieved_evidence=[
            {
                "evidence_id": "ret-1",
                "source_uri": "conec://c",
                "content": "retrieved one",
            },
        ],
        evidence_provenance=[
            {"lock_key": "conec", "relpath": "a", "sha256": "0" * 64},
            {"lock_key": "conec", "relpath": "b", "sha256": "1" * 64},
            {"lock_key": "conec", "relpath": "c", "sha256": "2" * 64},
        ],
    )
    transport(json.dumps(payload).encode())


def test_missing_media_fails_closed(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="media/absent.mp3")
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_decoding_params_cannot_override_constructed_messages(tmp_path):
    """Defense in depth: even called directly, a decoding_params "messages" key
    must never silently replace the constructed message list (which would drop
    audio while the adapter still meters it as delivered)."""

    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, decoding_params={"messages": []})
    with pytest.raises(FrozenCoreError, match="messages"):
        transport(json.dumps(payload).encode())


def test_response_format_is_forwarded_without_replacing_messages(tmp_path):
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "key_choice",
            "strict": True,
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"key_id": {"const": "K001"}},
                    "required": ["key_id"],
                    "additionalProperties": False,
                },
            },
        },
    }

    def fake_post(url, body):
        request = json.loads(body)
        assert request["response_format"] == response_format
        assert len(request["messages"]) == 2
        assert request["messages"][1]["content"][-1]["type"] == "input_audio"
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path, decoding_params={"response_format": response_format}
    )
    transport(json.dumps(payload).encode())


def test_malformed_usage_value_raises_frozen_core_error(tmp_path):
    response = json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": "NaN-ish-string", "completion_tokens": 2},
        }
    ).encode()
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: response)
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
    transport = _transport(_base_url(), data_root, post=_canary_post)
    payload = _boundary_payload(data_root, media_relpath=str(secret))
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_drive_letter_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="C:/secret.txt")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_backslash_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="media\\5000001.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_traversal_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="../outside/secret.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_missing_media_still_raises_file_not_found_after_confinement_check(tmp_path):
    """The confinement check must not change the existing missing-media
    behavior for a syntactically clean, in-root relative path."""

    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
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

    transport = _transport(_base_url(), data_root, post=lambda u, b: _canned_response())
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

    transport = _transport(_base_url(), data_root, post=lambda u, b: _canned_response())
    payload = _boundary_payload(data_root, media_relpath="media_link/leaked.mp3")
    with pytest.raises(FrozenCoreError, match="escapes"):
        transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# Multimedia array (Part 1) + "evidence-first-system-v3" four-tier layout
# (Part 2, prep infrastructure for the future listen-score-replay policy).
# ---------------------------------------------------------------------------


def test_existing_style_request_produces_byte_identical_wire_payload(tmp_path):
    """Part 1 back-compat requirement: a request built in the pre-existing
    single-audio style (no exemplar_bank/delta_candidates) must produce the
    EXACT SAME wire bytes it always did -- checked against the literal body,
    not merely a structural/partial comparison."""

    captured = {}

    def fake_post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(tmp_path)
    transport(json.dumps(payload).encode())

    media = tmp_path / payload["media_relpath"]
    expected_body = {
        "messages": [
            {"role": "system", "content": "Transcribe the speech verbatim."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(media.read_bytes()).decode(
                                "ascii"
                            ),
                            "format": "mp3",
                        },
                    }
                ],
            },
        ],
        "temperature": 0,
        "seed": 20260803,
    }
    assert captured["raw"] == json.dumps(expected_body).encode("utf-8")


def test_v3_delta_candidates_preserve_caller_order_on_the_wire(tmp_path):
    """Part 1: an ORDERED LIST of media items keeps EXACTLY the order the
    caller supplied. Unlike the canonically-sorted exemplar bank (see
    test_v3_exemplar_bank_canonical_serialization_is_order_independent
    below), tier 3 delta candidates are per-request and position-sensitive
    -- labels are chosen so alphabetical (canonical) order would disagree
    with caller order, discriminating the two behaviors."""

    media_b = tmp_path / "media" / "b_candidate.mp3"
    media_b.parent.mkdir(parents=True, exist_ok=True)
    media_b.write_bytes(b"candidate-b-bytes")
    media_a = tmp_path / "media" / "a_candidate.mp3"
    media_a.write_bytes(b"candidate-a-bytes")

    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert parts[0] == {"type": "text", "text": "[candidate b]"}
        assert base64.b64decode(parts[1]["input_audio"]["data"]) == b"candidate-b-bytes"
        assert parts[2] == {"type": "text", "text": "[candidate a]"}
        assert base64.b64decode(parts[3]["input_audio"]["data"]) == b"candidate-a-bytes"
        assert parts[4]["type"] == "input_audio"  # tier 4, the target, always last
        assert len(parts) == 5
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v3"
    )
    payload = _boundary_payload(
        tmp_path,
        delta_candidates=[
            {"media_relpath": "media/b_candidate.mp3", "label": "b"},
            {"media_relpath": "media/a_candidate.mp3", "label": "a"},
        ],
    )
    transport(json.dumps(payload).encode())


def test_v3_text_only_delta_candidate_produces_single_text_part(tmp_path):
    def fake_post(url, body):
        parts = json.loads(body)["messages"][1]["content"]
        assert parts[0] == {"type": "text", "text": "[candidate] a text-only guess"}
        assert parts[1]["type"] == "input_audio"  # tier 4, the target
        assert len(parts) == 2
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v3"
    )
    payload = _boundary_payload(
        tmp_path, delta_candidates=[{"text": "a text-only guess"}]
    )
    transport(json.dumps(payload).encode())


def test_v3_exemplar_bank_appears_in_system_message_after_instruction(tmp_path):
    media_one = tmp_path / "media" / "one.mp3"
    media_one.parent.mkdir(parents=True, exist_ok=True)
    media_one.write_bytes(b"exemplar-one-bytes")

    def fake_post(url, body):
        system = json.loads(body)["messages"][0]
        assert system["role"] == "system"
        assert system["content"] == [
            {"type": "text", "text": "Transcribe the speech verbatim."},
            {"type": "text", "text": "[exemplar alpha]"},
            {
                "type": "input_audio",
                "input_audio": {
                    "data": base64.b64encode(b"exemplar-one-bytes").decode("ascii"),
                    "format": "mp3",
                },
            },
        ]
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v3"
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/one.mp3", "label": "alpha"}]
    )
    transport(json.dumps(payload).encode())


def test_v3_exemplar_bank_canonical_serialization_is_order_independent(tmp_path):
    """Tier 2: the SAME bank (same members) must serialize to the SAME
    bytes regardless of the order the caller assembled it in -- required
    for llama-server KV-cache prefix reuse across requests sharing a bank
    (see the module docstring's v1->v2 cache-order rationale)."""

    media_one = tmp_path / "media" / "one.mp3"
    media_one.parent.mkdir(parents=True, exist_ok=True)
    media_one.write_bytes(b"exemplar-one-bytes")
    media_two = tmp_path / "media" / "two.mp3"
    media_two.write_bytes(b"exemplar-two-bytes")

    entry_one = {"media_relpath": "media/one.mp3", "label": "alpha"}
    entry_two = {"media_relpath": "media/two.mp3", "label": "beta"}

    bodies = {}

    def make_post(key):
        def fake_post(url, body):
            bodies[key] = body
            return _canned_response()

        return fake_post

    for key, bank in (
        ("forward", [entry_one, entry_two]),
        ("reversed", [entry_two, entry_one]),
    ):
        transport = _transport(
            _base_url(),
            tmp_path,
            post=make_post(key),
            prompt_order="evidence-first-system-v3",
        )
        payload = _boundary_payload(tmp_path, exemplar_bank=bank)
        transport(json.dumps(payload).encode())

    assert bodies["forward"] == bodies["reversed"]


def test_v3_empty_bank_and_no_deltas_matches_v2_shape(tmp_path):
    """Fail-closed clause counterpart: v3 with an empty bank and no delta
    candidates must produce a payload equivalent to v2's shape for the same
    inputs -- including evidence, which v3 places exactly like v2 does."""

    bodies = {}

    def make_post(key):
        def fake_post(url, body):
            bodies[key] = body
            return _canned_response()

        return fake_post

    payload_kwargs = dict(
        supplied_evidence=[
            {"evidence_id": "e1", "source_uri": "conec://x", "content": "context text"}
        ],
        evidence_provenance=[{"lock_key": "conec", "relpath": "x", "sha256": "0" * 64}],
    )
    for key, order in (
        ("v2", "evidence-first-system-v2"),
        ("v3", "evidence-first-system-v3"),
    ):
        transport = _transport(
            _base_url(), tmp_path, post=make_post(key), prompt_order=order
        )
        payload = _boundary_payload(tmp_path, **payload_kwargs)
        transport(json.dumps(payload).encode())
    assert bodies["v2"] == bodies["v3"]


def test_v3_bank_entry_missing_label_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/5000001.mp3"}]
    )
    with pytest.raises(FrozenCoreError, match="label"):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_nonexistent_media_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/absent.mp3", "label": "x"}]
    )
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_wrong_type_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/5000001.mp3", "label": 123}]
    )
    with pytest.raises(FrozenCoreError, match="label"):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_not_a_mapping_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, exemplar_bank=["not-a-mapping"])
    with pytest.raises(FrozenCoreError, match="exemplar_bank"):
        transport(json.dumps(payload).encode())


def test_v3_bank_not_a_list_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, exemplar_bank={"label": "x"})
    with pytest.raises(FrozenCoreError, match="exemplar_bank"):
        transport(json.dumps(payload).encode())


def test_v3_bank_media_relpath_traversal_refused_at_transport(tmp_path):
    """The bank's media items go through the SAME I4 confinement rail as the
    target audio (``_load_audio_part`` is shared) -- never a weaker check
    just because the item is one of several."""

    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path,
        exemplar_bank=[{"media_relpath": "../outside/secret.mp3", "label": "x"}],
    )
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_v3_delta_candidate_both_text_and_media_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path,
        delta_candidates=[
            {"text": "a candidate", "media_relpath": "media/5000001.mp3", "label": "x"}
        ],
    )
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


def test_v3_delta_candidate_neither_text_nor_media_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, delta_candidates=[{"label": "x"}])
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


def test_v3_more_than_two_delta_candidates_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, delta_candidates=[{"text": "one"}, {"text": "two"}, {"text": "three"}]
    )
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


def test_v3_delta_candidates_not_a_list_fails_closed(tmp_path):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, delta_candidates={"text": "x"})
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# New-arm resolution + payload attachment, end to end (2026-08-13): a REAL
# D2-registered arm's own core.policies.build_arm_payload output -- not a
# hand-built _boundary_payload -- driving the transport's own v3 tier
# assembly, mock-transport-asserting-tier-contents style.
# ---------------------------------------------------------------------------


def test_exemplar_context_arm_payload_produces_correct_v3_tiers_on_the_wire(tmp_path):
    """core.policies.build_arm_payload("exemplar-context", ...) ->
    LlamaServerTransport's own v3 tier assembly: evidence in tier 1's
    system text, the exemplar bank in tier 2, the target audio last -- the
    exact same shape test_v3_exemplar_bank_appears_in_system_message_
    after_instruction already proves for a hand-built payload, but here
    the payload comes from the real arm-payload builder for a real,
    D2-registered arm ("exemplar-context" -- e0.d2_leakage.
    ARM_VISIBLE_FIELDS)."""

    target = tmp_path / "media" / "5000001.mp3"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"target-audio-bytes")
    exemplar = tmp_path / "media" / "alpha.mp3"
    exemplar.write_bytes(b"exemplar-audio-bytes")

    ref = SampleRef(
        carrier_lock_key="earnings22-original",
        sample_id="5000001",
        media_relpath="media/5000001.mp3",
        audio_seconds=10.0,
        sample_rate_hz=16000,
    )
    evidence = [
        EvidenceItem(
            evidence_id="conec/5000001",
            source_uri="conec://earnings22/contexts/5000001.txt",
            content="Acme Corp Q3",
            provenance={"lock_key": "conec", "relpath": "x.txt", "sha256": "0" * 64},
        )
    ]
    payload = build_arm_payload(
        "exemplar-context",
        ref,
        "req-1",
        "Transcribe the speech verbatim.",
        {"temperature": 0, "seed": 20260803},
        evidence=evidence,
        exemplar_bank=[{"media_relpath": "media/alpha.mp3", "label": "alpha"}],
    )

    def fake_post(url, body):
        parsed = json.loads(body)
        system = parsed["messages"][0]
        assert system["role"] == "system"
        assert system["content"] == [
            {"type": "text", "text": "[evidence conec/5000001] Acme Corp Q3"},
            {"type": "text", "text": "Transcribe the speech verbatim."},
            {"type": "text", "text": "[exemplar alpha]"},
            {
                "type": "input_audio",
                "input_audio": {
                    "data": base64.b64encode(b"exemplar-audio-bytes").decode("ascii"),
                    "format": "mp3",
                },
            },
        ]
        user_content = parsed["messages"][1]["content"]
        assert len(user_content) == 1
        assert (
            base64.b64decode(user_content[0]["input_audio"]["data"])
            == b"target-audio-bytes"
        )
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v3"
    )
    transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# I4 defense in depth: per-segment Windows-only looseness (trailing dot/space,
# NTFS alternate-data-stream colon) -- see test_frozen_core_adapter.py's
# mirror tests for the rationale.
# ---------------------------------------------------------------------------


def test_media_relpath_trailing_dot_segment_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3.")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_trailing_space_segment_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3 ")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_colon_in_segment_refused_at_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=lambda u, b: _canned_response())
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3:hidden")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


# ---------------------------------------------------------------------------
# Fragment-driven user-turn text (2026-09-04, Audio2Tool official-protocol
# replication). The published protocol puts a fixed sentence in the USER turn
# AFTER the audio; every arm built before it sends a user turn of evidence
# text plus audio only. The seam is config, not code: `user_turn_text` and
# `user_turn_audio_first` on the composed config. These tests pin both the
# new behaviour and the unchanged old one.
# ---------------------------------------------------------------------------

_OFFICIAL_USER_TURN = "Convert this voice command to a tool call."


def _audio_part_for(tmp_path, payload):
    media = tmp_path / payload["media_relpath"]
    return {
        "type": "input_audio",
        "input_audio": {
            "data": base64.b64encode(media.read_bytes()).decode("ascii"),
            "format": "mp3",
        },
    }


def test_user_turn_text_follows_the_audio_part_on_the_wire(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        prompt_order="evidence-first-system-v2",
        user_turn_text=_OFFICIAL_USER_TURN,
    )
    payload = _boundary_payload(tmp_path)
    transport(json.dumps(payload).encode())

    expected_body = {
        "messages": [
            {"role": "system", "content": "Transcribe the speech verbatim."},
            {
                "role": "user",
                "content": [
                    _audio_part_for(tmp_path, payload),
                    {"type": "text", "text": _OFFICIAL_USER_TURN},
                ],
            },
        ],
        "temperature": 0,
        "seed": 20260803,
    }
    assert captured["raw"] == json.dumps(expected_body).encode("utf-8")


def test_user_turn_text_also_applies_under_the_historical_v1_order(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, user_turn_text=_OFFICIAL_USER_TURN
    )
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[{"evidence_id": "e1", "content": "ctx"}],
    )
    transport(json.dumps(payload).encode())

    content = captured["body"]["messages"][1]["content"]
    assert [part["type"] for part in content] == ["text", "input_audio", "text"]
    assert content[0]["text"] == "[evidence e1] ctx"
    assert content[-1]["text"] == _OFFICIAL_USER_TURN


def test_user_turn_audio_first_false_puts_the_text_before_the_audio(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        prompt_order="evidence-first-system-v2",
        user_turn_text=_OFFICIAL_USER_TURN,
        user_turn_audio_first=False,
    )
    transport(json.dumps(_boundary_payload(tmp_path)).encode())

    content = captured["body"]["messages"][1]["content"]
    assert [part["type"] for part in content] == ["text", "input_audio"]
    assert content[0]["text"] == _OFFICIAL_USER_TURN


def test_legacy_calibration_cell_payload_is_unchanged_without_the_seam(tmp_path):
    """Regression for the 2026-09-04 calibration cells specifically.

    A0'-legacy-raw / P0-legacy-packets fly ``prompt_order:
    evidence-first-system-v2`` with no ``user_turn_text``. Their wire bytes
    must be exactly what they were before the seam existed: one system
    message, one user message whose content is the audio part ALONE.
    """

    captured = {}

    def fake_post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v2"
    )
    payload = _boundary_payload(tmp_path)
    transport(json.dumps(payload).encode())

    expected_body = {
        "messages": [
            {"role": "system", "content": "Transcribe the speech verbatim."},
            {"role": "user", "content": [_audio_part_for(tmp_path, payload)]},
        ],
        "temperature": 0,
        "seed": 20260803,
    }
    assert captured["raw"] == json.dumps(expected_body).encode("utf-8")


def test_empty_user_turn_text_is_refused_at_construction(tmp_path):
    with pytest.raises(SessionError, match="user_turn_text"):
        _transport(_base_url(), tmp_path, post=lambda url, body: b"", user_turn_text="   ")


def test_user_turn_text_is_refused_under_speech_feature_orders(tmp_path):
    feature_root = tmp_path / "features"
    feature_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(SessionError, match="not supported under prompt_order"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda url, body: b"",
            prompt_order="speech-features-text-keys-v1",
            feature_root=feature_root,
            user_turn_text=_OFFICIAL_USER_TURN,
        )


# ---------------------------------------------------------------------------
# Fragment-driven SYSTEM-MESSAGE SUPPRESSION (2026-09-05, Earnings-22 DEV ESB
# shape-C arm). The Qwen3-Omni model card's "Setting for Evaluation" section
# prescribes, for every evaluation benchmark, no system prompt and the
# instruction text AFTER the multimodal data in the user turn. `user_turn_text`
# already expressed the second half; `omit_system_message` expresses the first.
# The failure mode being guarded is SILENT loss: a dropped system message would
# take `task_instruction` (and, under the evidence-first orders, the evidence
# block and the exemplar bank) off the wire while every receipt and protocol
# hash still recorded them.
# ---------------------------------------------------------------------------

_OFFICIAL_ASR_INSTRUCTION = "Transcribe the English audio into text."


def test_omit_system_message_sends_one_user_turn_with_the_audio_before_the_text(tmp_path):
    """Arm C's exact wire bytes: no system block, audio part first, text last."""

    captured = {}

    def fake_post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        prompt_order="evidence-first-system-v3",
        user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
        user_turn_audio_first=True,
        omit_system_message=True,
    )
    payload = _boundary_payload(tmp_path, task_instruction=_OFFICIAL_ASR_INSTRUCTION)
    transport(json.dumps(payload).encode())

    expected_body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    _audio_part_for(tmp_path, payload),
                    {"type": "text", "text": _OFFICIAL_ASR_INSTRUCTION},
                ],
            }
        ],
        "temperature": 0,
        "seed": 20260803,
    }
    assert captured["raw"] == json.dumps(expected_body).encode("utf-8")
    assert [message["role"] for message in json.loads(captured["raw"])["messages"]] == [
        "user"
    ]


@pytest.mark.parametrize(
    "prompt_order",
    ["system-instruction-v1", "evidence-first-system-v2", "evidence-first-system-v3"],
)
def test_omit_system_message_holds_under_every_non_speech_feature_order(
    tmp_path, prompt_order
):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(),
        tmp_path,
        post=fake_post,
        prompt_order=prompt_order,
        user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
        omit_system_message=True,
    )
    transport(
        json.dumps(
            _boundary_payload(tmp_path, task_instruction=_OFFICIAL_ASR_INSTRUCTION)
        ).encode()
    )

    messages = captured["body"]["messages"]
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert [part["type"] for part in messages[0]["content"]] == ["input_audio", "text"]
    assert messages[0]["content"][-1]["text"] == _OFFICIAL_ASR_INSTRUCTION


def test_omit_system_message_without_user_turn_text_is_refused_at_construction(tmp_path):
    with pytest.raises(SessionError, match="omit_system_message requires user_turn_text"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda url, body: b"",
            omit_system_message=True,
        )


def test_omit_system_message_is_refused_under_speech_feature_orders(tmp_path):
    feature_root = tmp_path / "features"
    feature_root.mkdir(parents=True, exist_ok=True)
    with pytest.raises(SessionError, match="not supported under prompt_order"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda url, body: b"",
            prompt_order="speech-features-text-keys-v1",
            feature_root=feature_root,
            user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
            omit_system_message=True,
        )


def test_omit_system_message_is_refused_for_a_non_bool(tmp_path):
    with pytest.raises(SessionError, match="omit_system_message must be a bool"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda url, body: b"",
            user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
            omit_system_message="yes",
        )


def test_omit_system_message_refuses_an_instruction_the_user_turn_does_not_carry(
    tmp_path,
):
    """The instruction the payload records must be the instruction that is sent."""

    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda url, body: _canned_response(),
        prompt_order="evidence-first-system-v3",
        user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
        omit_system_message=True,
    )
    payload = _boundary_payload(tmp_path, task_instruction="Something else entirely.")
    with pytest.raises(FrozenCoreError, match="byte-identical to the configured"):
        transport(json.dumps(payload).encode())


@pytest.mark.parametrize(
    "prompt_order", ["evidence-first-system-v2", "evidence-first-system-v3"]
)
def test_omit_system_message_refuses_a_request_carrying_evidence(tmp_path, prompt_order):
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda url, body: _canned_response(),
        prompt_order=prompt_order,
        user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
        omit_system_message=True,
    )
    payload = _boundary_payload(
        tmp_path,
        task_instruction=_OFFICIAL_ASR_INSTRUCTION,
        supplied_evidence=[{"evidence_id": "e1", "content": "ctx"}],
    )
    with pytest.raises(FrozenCoreError, match="refuses a request carrying evidence"):
        transport(json.dumps(payload).encode())


def test_omit_system_message_refuses_a_request_carrying_an_exemplar_bank(tmp_path):
    media = tmp_path / "media" / "5000001.mp3"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-mp3-bytes")
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda url, body: _canned_response(),
        prompt_order="evidence-first-system-v3",
        user_turn_text=_OFFICIAL_ASR_INSTRUCTION,
        omit_system_message=True,
    )
    payload = _boundary_payload(
        tmp_path,
        task_instruction=_OFFICIAL_ASR_INSTRUCTION,
        exemplar_bank=[{"media_relpath": "media/5000001.mp3", "label": "L"}],
    )
    with pytest.raises(FrozenCoreError, match="carrying an exemplar bank"):
        transport(json.dumps(payload).encode())


def test_sealed_e22_arm_a_payload_is_byte_identical_without_the_seam(tmp_path):
    """Regression for the sealed 2026-09-05 Earnings-22 DEV arms A and B.

    They fly ``prompt_order: evidence-first-system-v3`` with no
    ``user_turn_text`` and no ``omit_system_message``. Their wire bytes must be
    exactly what they were before either key existed: one system message
    carrying the instruction, one user message whose content is the audio part
    ALONE.
    """

    captured = {}

    def fake_post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=fake_post, prompt_order="evidence-first-system-v3"
    )
    payload = _boundary_payload(tmp_path)
    transport(json.dumps(payload).encode())

    expected_body = {
        "messages": [
            {"role": "system", "content": "Transcribe the speech verbatim."},
            {"role": "user", "content": [_audio_part_for(tmp_path, payload)]},
        ],
        "temperature": 0,
        "seed": 20260803,
    }
    assert captured["raw"] == json.dumps(expected_body).encode("utf-8")


def test_transport_factory_defaults_omit_system_message_to_false(tmp_path):
    """A composed config that never declares the key keeps the system message."""

    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _llama_server_factory(
        {"base_url": _base_url(), "prompt_order": "evidence-first-system-v3"},
        tmp_path,
        session=_fake_session(),
        runtime_receipt=_fake_runtime_receipt(),
        runtime_root=_live["runtime_root"],
    )
    transport._post = fake_post
    transport(json.dumps(_boundary_payload(tmp_path)).encode())
    assert [message["role"] for message in captured["body"]["messages"]] == [
        "system",
        "user",
    ]


def test_transport_factory_reads_omit_system_message_from_the_composed_config(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _llama_server_factory(
        {
            "base_url": _base_url(),
            "prompt_order": "evidence-first-system-v3",
            "user_turn_text": _OFFICIAL_ASR_INSTRUCTION,
            "user_turn_audio_first": True,
            "omit_system_message": True,
        },
        tmp_path,
        session=_fake_session(),
        runtime_receipt=_fake_runtime_receipt(),
        runtime_root=_live["runtime_root"],
    )
    transport._post = fake_post
    transport(
        json.dumps(
            _boundary_payload(tmp_path, task_instruction=_OFFICIAL_ASR_INSTRUCTION)
        ).encode()
    )
    assert [message["role"] for message in captured["body"]["messages"]] == ["user"]


def test_opt_in_wire_response_keeps_exact_bytes_and_finish_reason(tmp_path):
    raw = json.dumps(
        {
            "choices": [{"message": {"content": "hello"}, "finish_reason": "length"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2},
        },
        separators=(",", ":"),
    ).encode()
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda _url, _body: raw,
        preserve_wire_responses=True,
    )
    envelope = json.loads(transport(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert envelope["wire_response_b64"] == base64.b64encode(raw).decode("ascii")
    assert envelope["wire_response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert envelope["wire_finish_reason"] == "length"
    assert envelope["text"] == "hello"


def test_opt_in_malformed_http_response_returns_provenance_envelope(tmp_path):
    raw = b"malformed-http-json"
    transport = _transport(
        _base_url(),
        tmp_path,
        post=lambda _url, _body: raw,
        preserve_wire_responses=True,
    )
    envelope = json.loads(transport(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert "text" not in envelope
    assert envelope["wire_response_b64"] == base64.b64encode(raw).decode("ascii")
    assert envelope["wire_response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert envelope["wire_finish_reason"] is None


def test_wire_response_capture_flag_must_be_boolean(tmp_path):
    with pytest.raises(SessionError, match="preserve_wire_responses must be a bool"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda _url, _body: _canned_response(),
            preserve_wire_responses="yes",
        )


def test_a_construction_proposer_payload_sends_no_audio_part(tmp_path):
    """The ONE text-only arm. Its payload still NAMES the anchor's media so the
    gate's media-identity rail and the trace bind a real recording, but loading
    those bytes onto the wire would contradict the arm's own registered scope
    ("zero audio parts are sent") and is refused outright by the mmproj-free
    server every EVO cell serves."""

    captured = {}

    def post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=post, prompt_order="evidence-first-system-v2"
    )
    payload = _boundary_payload(
        tmp_path,
        construction_targets=[
            {"sample_id": "tier1_direct:000001", "query": "turn on the light",
             "gold_call": "setLighting(state='on')"}
        ],
    )
    transport(json.dumps(payload).encode("utf-8"))
    user = [m for m in captured["body"]["messages"] if m["role"] == "user"]
    assert len(user) == 1
    parts = user[0]["content"]
    assert not [part for part in parts if part.get("type") == "input_audio"]
    assert parts == []


def test_a_payload_without_construction_targets_still_sends_its_audio(tmp_path):
    """Identity behaviour for every other arm, which is the whole point of
    keying on the D2-frozen field rather than on an arm-name literal."""

    captured = {}

    def post(url, body):
        captured["body"] = json.loads(body)
        return _canned_response()

    transport = _transport(
        _base_url(), tmp_path, post=post, prompt_order="evidence-first-system-v2"
    )
    transport(json.dumps(_boundary_payload(tmp_path)).encode("utf-8"))
    user = [m for m in captured["body"]["messages"] if m["role"] == "user"]
    assert [part["type"] for part in user[0]["content"]] == ["input_audio"]


# ---------------------------------------------------------------------------
# Decode-confidence request/response shape (2026-09-08 logprob-as-judge probe).
#
# The study talks to llama-server's OpenAI-compatible /v1/chat/completions
# endpoint (``LlamaServerTransport.__init__`` builds exactly that URL), NOT the
# native /completion endpoint -- so the request field is ``logprobs`` +
# ``top_logprobs`` and the response field is ``choices[0].logprobs``, never
# ``n_probs`` and never ``completion_probabilities``. On the pinned build
# (llama.cpp 04ccc72a) ``tools/server/server-common.cpp:1525-1529`` is what
# translates the former into the latter's ``n_probs``.
# ---------------------------------------------------------------------------


def _canned_logprobs_response(k=2):
    """A chat response carrying the pinned server's own logprobs shape:
    ``choices[0].logprobs.content[]``, each entry ``{id, token, bytes,
    logprob, top_logprobs[]}`` (``tools/server/server-task.cpp:456-460`` builds
    the object, ``:306-325`` builds each entry, ``:287-302`` each alternative).
    """

    def alternative(token, logprob):
        return {
            "id": abs(hash(token)) % 100000,
            "token": token,
            "bytes": list(token.encode("utf-8")),
            "logprob": logprob,
        }

    content = []
    for index, token in enumerate(("hello", " world")):
        entry = dict(alternative(token, -0.1 - index))
        entry["top_logprobs"] = [
            alternative(token, -0.1 - index),
            *[alternative(f"alt{rank}", -3.0 - rank) for rank in range(1, k)],
        ]
        content.append(entry)
    return json.dumps(
        {
            "choices": [
                {
                    "message": {"content": "hello world"},
                    "logprobs": {"content": content},
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        }
    ).encode()


def test_the_request_body_carries_no_logprobs_key_unless_the_config_declares_one(tmp_path):
    """Byte identity: the wire bytes of a request whose decoding_params never
    name logprobs are exactly what they were before the probe existed."""

    captured = {}

    def post(url, body):
        captured["raw"] = body
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=post)
    transport(json.dumps(_boundary_payload(tmp_path)).encode())
    body = json.loads(captured["raw"])
    assert "logprobs" not in body
    assert "top_logprobs" not in body
    assert "n_probs" not in body


def test_declaring_the_decoding_keys_puts_exactly_them_on_the_wire(tmp_path):
    """The only difference from the byte-identical baseline body above is the
    two declared decoding keys -- no other field moves, and nothing is renamed
    to the native endpoint's ``n_probs`` on this side of the wire."""

    bodies = {}

    def post(url, body):
        bodies[len(bodies)] = json.loads(body)
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=post)
    transport(json.dumps(_boundary_payload(tmp_path)).encode())
    transport(
        json.dumps(
            _boundary_payload(
                tmp_path,
                decoding_params={
                    "temperature": 0,
                    "seed": 20260803,
                    "logprobs": True,
                    "top_logprobs": 5,
                },
            )
        ).encode()
    )
    baseline, probe = bodies[0], bodies[1]
    assert probe["logprobs"] is True
    assert probe["top_logprobs"] == 5
    assert set(probe) - set(baseline) == {"logprobs", "top_logprobs"}
    assert all(probe[key] == baseline[key] for key in baseline)


def test_the_response_envelope_is_byte_identical_without_a_logprobs_choice(tmp_path):
    """The pre-existing strict-equality contract: a server choice with no
    ``logprobs`` key adds no envelope key."""

    transport = _transport(
        _base_url(), tmp_path, post=lambda url, body: _canned_response()
    )
    raw = transport(json.dumps(_boundary_payload(tmp_path)).encode())
    assert json.loads(raw) == {
        "text": "hello world",
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
    }


def test_a_logprobs_choice_is_forwarded_verbatim_into_the_envelope(tmp_path):
    """The transport neither reshapes nor summarizes the distribution: whatever
    the server put on ``choices[0].logprobs`` is what the adapter receives."""

    raw_response = _canned_logprobs_response(k=5)
    transport = _transport(
        _base_url(), tmp_path, post=lambda url, body: raw_response
    )
    payload = _boundary_payload(
        tmp_path,
        decoding_params={
            "temperature": 0,
            "seed": 20260803,
            "logprobs": True,
            "top_logprobs": 5,
        },
    )
    envelope = json.loads(transport(json.dumps(payload).encode()))
    expected = json.loads(raw_response)["choices"][0]["logprobs"]
    assert envelope["logprobs"] == expected
    assert envelope["text"] == "hello world"
    assert [entry["token"] for entry in envelope["logprobs"]["content"]] == [
        "hello",
        " world",
    ]
    assert len(envelope["logprobs"]["content"][0]["top_logprobs"]) == 5


def test_preparation_render_is_exact_send_body_and_never_posts(tmp_path):
    captured = []
    transport = _transport(_base_url(), tmp_path,
                           post=lambda url, body: captured.append(json.loads(body)) or _canned_response())
    payload = json.dumps(_boundary_payload(tmp_path, decoding_params={"max_tokens": 64, "temperature": 0})).encode()
    prepared = transport.render_request(payload)
    assert captured == []
    transport(payload)
    assert captured == [prepared]
    assert prepared["max_tokens"] == 64
