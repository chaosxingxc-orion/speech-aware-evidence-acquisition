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
        "llama_cpp": {"binary_path": _BINARY_PATH, "binary_sha256": _live["binary_sha256"]},
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
        supplied_evidence=[
            {"evidence_id": "key-001", "content": "Turn a light on."}
        ],
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


def test_speech_feature_transport_batch_validates_query_and_key_packets(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.model import transport as transport_module

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
            {"packet_id": query.packet_id, "sha256": query.packet_sha256, "role": "query"},
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


def test_speech_feature_prompt_order_requires_inference_session_and_fixed_root(tmp_path):
    with pytest.raises(SessionError, match="inference session"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda u, b: _canned_response(),
            prompt_order="speech-features-text-keys-v1",
            feature_root=tmp_path / "features",
        )
    with pytest.raises(SessionError, match="feature_root"):
        _transport(
            _base_url(),
            tmp_path,
            post=lambda u, b: _canned_response(),
            session=_fake_inference_session(),
            prompt_order="speech-features-text-keys-v1",
        )


def test_speech_feature_transport_fails_closed_on_corruption_and_inline_arrays(tmp_path):
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


def test_speech_feature_packet_loader_rejects_escape_model_and_dimension_mismatch(tmp_path):
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


def test_speech_feature_packet_batch_validation_is_parallel_and_ordered(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.model import speech_features

    feature_root = tmp_path / "features"
    packets = tuple(
        _materialize_packet(feature_root, f"slurp/train/s{index}")
        for index in range(6)
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


def test_speech_feature_packet_materialization_is_idempotent_but_never_overwrites(tmp_path):
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
        _base_url(), tmp_path, post=fake_post,
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

    for key, order in (("v1", "system-instruction-v1"), ("v2", "evidence-first-system-v2")):
        transport = _transport(
            _base_url(), tmp_path, post=make_post(key), prompt_order=order
        )
        transport(json.dumps(_boundary_payload(tmp_path)).encode())
    assert bodies["v1"] == bodies["v2"]


def test_unknown_prompt_order_refused_at_construction(tmp_path):
    with pytest.raises(Exception, match="prompt_order"):
        _transport(
            _base_url(), tmp_path, post=lambda u, b: _canned_response(),
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
                    "prompt_tokens_details": {"cached_tokens": 0, "audio_tokens": 55000},
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
    with pytest.raises(FrozenCoreError, match="HTTP 400.*exceeds the available context"):
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
            {"evidence_id": "ev-1", "source_uri": "conec://x", "content": "context text"}
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
            {"evidence_id": "ev-1", "source_uri": "conec://x", "content": "context text"}
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
        assert [part["type"] for part in parts] == ["text", "text", "text", "input_audio"]
        assert parts[0] == {"type": "text", "text": "[evidence sup-1] supplied one"}
        assert parts[1] == {"type": "text", "text": "[evidence sup-2] supplied two"}
        assert parts[2] == {"type": "text", "text": "[evidence ret-1] retrieved one"}
        return _canned_response()

    transport = _transport(_base_url(), tmp_path, post=fake_post)
    payload = _boundary_payload(
        tmp_path,
        supplied_evidence=[
            {"evidence_id": "sup-1", "source_uri": "conec://a", "content": "supplied one"},
            {"evidence_id": "sup-2", "source_uri": "conec://b", "content": "supplied two"},
        ],
        retrieved_evidence=[
            {"evidence_id": "ret-1", "source_uri": "conec://c", "content": "retrieved one"},
        ],
        evidence_provenance=[
            {"lock_key": "conec", "relpath": "a", "sha256": "0" * 64},
            {"lock_key": "conec", "relpath": "b", "sha256": "1" * 64},
            {"lock_key": "conec", "relpath": "c", "sha256": "2" * 64},
        ],
    )
    transport(json.dumps(payload).encode())


def test_missing_media_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/absent.mp3")
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_decoding_params_cannot_override_constructed_messages(tmp_path):
    """Defense in depth: even called directly, a decoding_params "messages" key
    must never silently replace the constructed message list (which would drop
    audio while the adapter still meters it as delivered)."""

    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
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
                "type": "object",
                "properties": {"key_id": {"const": "K001"}},
                "required": ["key_id"],
                "additionalProperties": False,
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
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: response
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
    transport = _transport(_base_url(), data_root, post=_canary_post)
    payload = _boundary_payload(data_root, media_relpath=str(secret))
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_drive_letter_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="C:/secret.txt")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_backslash_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media\\5000001.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_traversal_media_relpath_refused_at_transport(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="../outside/secret.mp3")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_missing_media_still_raises_file_not_found_after_confinement_check(tmp_path):
    """The confinement check must not change the existing missing-media
    behavior for a syntactically clean, in-root relative path."""

    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
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
        _base_url(), data_root, post=lambda u, b: _canned_response()
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
        _base_url(), data_root, post=lambda u, b: _canned_response()
    )
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
                            "data": base64.b64encode(media.read_bytes()).decode("ascii"),
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
    payload = _boundary_payload(tmp_path, delta_candidates=[{"text": "a text-only guess"}])
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
            _base_url(), tmp_path, post=make_post(key), prompt_order="evidence-first-system-v3"
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
    for key, order in (("v2", "evidence-first-system-v2"), ("v3", "evidence-first-system-v3")):
        transport = _transport(_base_url(), tmp_path, post=make_post(key), prompt_order=order)
        payload = _boundary_payload(tmp_path, **payload_kwargs)
        transport(json.dumps(payload).encode())
    assert bodies["v2"] == bodies["v3"]


def test_v3_bank_entry_missing_label_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/5000001.mp3"}]
    )
    with pytest.raises(FrozenCoreError, match="label"):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_nonexistent_media_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/absent.mp3", "label": "x"}]
    )
    with pytest.raises(FileNotFoundError):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_wrong_type_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, exemplar_bank=[{"media_relpath": "media/5000001.mp3", "label": 123}]
    )
    with pytest.raises(FrozenCoreError, match="label"):
        transport(json.dumps(payload).encode())


def test_v3_bank_entry_not_a_mapping_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, exemplar_bank=["not-a-mapping"])
    with pytest.raises(FrozenCoreError, match="exemplar_bank"):
        transport(json.dumps(payload).encode())


def test_v3_bank_not_a_list_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
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
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
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
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
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
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(tmp_path, delta_candidates=[{"label": "x"}])
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


def test_v3_more_than_two_delta_candidates_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
        prompt_order="evidence-first-system-v3",
    )
    payload = _boundary_payload(
        tmp_path, delta_candidates=[{"text": "one"}, {"text": "two"}, {"text": "three"}]
    )
    with pytest.raises(FrozenCoreError, match="delta_candidates"):
        transport(json.dumps(payload).encode())


def test_v3_delta_candidates_not_a_list_fails_closed(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response(),
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
            base64.b64decode(user_content[0]["input_audio"]["data"]) == b"target-audio-bytes"
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
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3.")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_trailing_space_segment_refused_at_transport(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3 ")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())


def test_media_relpath_colon_in_segment_refused_at_transport(tmp_path):
    transport = _transport(
        _base_url(), tmp_path, post=lambda u, b: _canned_response()
    )
    payload = _boundary_payload(tmp_path, media_relpath="media/5000001.mp3:hidden")
    with pytest.raises(FrozenCoreError, match="media_relpath"):
        transport(json.dumps(payload).encode())
