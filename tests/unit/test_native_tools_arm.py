"""Tests for the D1a native chat-template tool-calling arm
("bare-core-native-tools"): ``build_arm_payload`` refusals,
``core.policies.TOOL_SCHEMA_FILLS`` wiring through ``FixedPolicy``, and
``LlamaServerTransport``'s ``tools`` pass-through + ``tool_calls``
canonicalization.

The transport-level tests need a real ``LlamaServerTransport`` (session
liveness -- PID identity AND listening-socket ownership -- is re-verified on
every send, not merely a declared value comparison), so this module carries
its own self-contained live-process fixture rather than importing
tests/unit/test_llama_server_transport.py's private one -- mirrors that
file's own approach (see its module docstring) but kept independent so
neither file's edits couple to the other's internals.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.contracts import STUDY_SLUG, ExecutionPlan
from speech_aware_evidence_acquisition.core import policies  # noqa: F401 (registration)
from speech_aware_evidence_acquisition.core.base import (
    EvidenceItem,
    PayloadBindingContext,
    SampleContext,
)
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, FrozenCoreError
from speech_aware_evidence_acquisition.core.model.transport import LlamaServerTransport
from speech_aware_evidence_acquisition.core.preparation_fit import fit_requests
from speech_aware_evidence_acquisition.core.policies import (
    TOOL_SCHEMA_FILLS,
    ArmError,
    FixedPolicy,
    build_arm_payload,
)
from speech_aware_evidence_acquisition.core.session import (
    SESSION_RECEIPT_SCHEMA,
    ModelFileRef,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.loader import SampleRef
from speech_aware_evidence_acquisition.e0.d2_leakage import ARM_VISIBLE_FIELDS


_REF = SampleRef(
    carrier_lock_key="audio2tool",
    sample_id="tier1_direct:000001",
    media_relpath="datasets/audio2tool/public/tier1_direct_audios/query_00001/turn.wav",
    audio_seconds=1.5,
    sample_rate_hz=16000,
)
_DECODING = {"temperature": 0, "seed": 20260803}
_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "setZoneTemperature",
            "description": "Sets the target climate control temperature.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string", "enum": ["Driver", "Passenger"]},
                    "temperature": {"type": "number", "minimum": 15.0, "maximum": 30.0},
                },
                "required": [],
            },
        },
    }
]
_EVIDENCE = [
    EvidenceItem(
        evidence_id="conec/1",
        source_uri="conec://x/1.txt",
        content="ctx",
        provenance={"lock_key": "conec", "relpath": "x/1.txt", "sha256": "0" * 64},
    )
]


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


# ---------------------------------------------------------------------------
# build_arm_payload: "bare-core-native-tools" own shape and refusals
# ---------------------------------------------------------------------------


def test_bare_core_native_tools_is_bare_core_plus_tool_schemas():
    assert ARM_VISIBLE_FIELDS["bare-core-native-tools"] == (
        *ARM_VISIBLE_FIELDS["bare-core"],
        "tool_schemas",
    )


def test_bare_core_native_tools_exact_fields():
    payload = build_arm_payload(
        "bare-core-native-tools", _REF, "req-1", "T.", _DECODING, tool_schemas=_TOOL_SCHEMAS
    )
    assert set(payload) == set(ARM_VISIBLE_FIELDS["bare-core-native-tools"])
    assert payload["tool_schemas"] == _TOOL_SCHEMAS
    # A copy, not the caller's own list object (mirrors exemplar_bank /
    # delta_candidates, which build_arm_payload also copies rather than
    # aliasing).
    assert payload["tool_schemas"] is not _TOOL_SCHEMAS


def test_bare_core_native_tools_requires_tool_schemas():
    with pytest.raises(ArmError, match="tool_schemas"):
        build_arm_payload("bare-core-native-tools", _REF, "req-1", "T.", _DECODING)


def test_bare_core_native_tools_refuses_an_empty_tool_schemas_list():
    with pytest.raises(ArmError, match="tool_schemas"):
        build_arm_payload(
            "bare-core-native-tools", _REF, "req-1", "T.", _DECODING, tool_schemas=[]
        )


def test_bare_core_native_tools_refuses_evidence_like_bare_core():
    with pytest.raises(ArmError):
        build_arm_payload(
            "bare-core-native-tools",
            _REF,
            "req-1",
            "T.",
            _DECODING,
            tool_schemas=_TOOL_SCHEMAS,
            evidence=_EVIDENCE,
        )


@pytest.mark.parametrize(
    "arm,kwargs",
    [
        ("bare-core", {}),
        ("fixed-legal-context", {"evidence": _EVIDENCE}),
        ("fixed-retrieval", {"evidence": _EVIDENCE, "retrieval_query": "acme q2"}),
        ("exemplar-context", {"evidence": _EVIDENCE}),
        ("fixed-legal-context-replay", {"evidence": _EVIDENCE}),
    ],
)
def test_every_other_registered_arm_refuses_tool_schemas(arm, kwargs):
    with pytest.raises(ArmError, match="tool_schemas"):
        build_arm_payload(
            arm, _REF, "req-1", "T.", _DECODING, tool_schemas=_TOOL_SCHEMAS, **kwargs
        )


def test_build_arm_payload_omitting_tool_schemas_is_byte_identical_for_bare_core():
    without = build_arm_payload("bare-core", _REF, "req-1", "T.", _DECODING)
    with_explicit_none = build_arm_payload(
        "bare-core", _REF, "req-1", "T.", _DECODING, tool_schemas=None
    )
    assert without == with_explicit_none
    assert "tool_schemas" not in without


# ---------------------------------------------------------------------------
# core.policies.TOOL_SCHEMA_FILLS resolution through FixedPolicy.run_sample
# ---------------------------------------------------------------------------


def test_audio2tool_openai_tools_fill_is_registered():
    assert "audio2tool-openai-tools" in TOOL_SCHEMA_FILLS.names()


def test_fixed_policy_resolves_tool_schema_fill_end_to_end(tmp_path, monkeypatch):
    fake_tools = [
        {
            "type": "function",
            "function": {
                "name": "f",
                "description": "d",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]
    seen_args = []
    monkeypatch.setitem(
        TOOL_SCHEMA_FILLS._entries,
        "test-native-tools-fill",
        lambda lock, root: seen_args.append((lock, root)) or fake_tools,
    )

    sink = TraceSink(tmp_path / "run", "SAEA-E-000-native-tools")
    plan = ExecutionPlan(
        run_id="SAEA-E-000-native-tools",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=5,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
        attempt_id="attempt-0001",
    )
    data_root = tmp_path / "data"
    media = data_root / _REF.media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-wav-bytes")
    binding = PayloadBindingContext(
        carrier_lock_key=_REF.carrier_lock_key,
        allowed_sample_ids=frozenset({_REF.sample_id}),
        sample_facts={_REF.sample_id: (_REF.audio_seconds, _REF.sample_rate_hz)},
        data_root=data_root,
        carrier_root=data_root / "datasets" / "audio2tool",
    )
    captured = []

    def fake_transport(request_bytes: bytes) -> bytes:
        captured.append(json.loads(request_bytes.decode("utf-8")))
        return json.dumps({"text": "[]", "usage": {}}).encode()

    adapter = FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm="bare-core-native-tools",
        transport=fake_transport,
        sink=sink,
        binding=binding,
    )
    ctx = SampleContext(
        sample=_REF,
        evidence=[],
        adapter=adapter,
        sink=sink,
        arm="bare-core-native-tools",
        task_instruction="T.",
        decoding_params=_DECODING,
        request_id_base="req-0001",
        extras={
            "config_values": {"tool_schema_fill": "test-native-tools-fill"},
            "data_root": data_root,
        },
    )

    outcome = FixedPolicy().run_sample(ctx)

    assert outcome.admitted is True
    assert len(captured) == 1
    assert captured[0]["tool_schemas"] == fake_tools
    # The fill was called with (lock, data_root) -- root matches extras,
    # never something the fill has to re-derive on its own.
    assert len(seen_args) == 1
    assert seen_args[0][1] == data_root


def test_fixed_policy_refuses_native_tools_arm_without_a_configured_fill(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-native-tools-missing-fill")
    ctx = SampleContext(
        sample=_REF,
        evidence=[],
        adapter=None,
        sink=sink,
        arm="bare-core-native-tools",
        task_instruction="T.",
        decoding_params=_DECODING,
        request_id_base="req-0001",
        extras={"config_values": {}, "data_root": Path("/unused")},
    )
    with pytest.raises(ArmError, match="tool_schema_fill"):
        FixedPolicy().run_sample(ctx)


def test_fixed_policy_refuses_native_tools_arm_with_an_unregistered_fill_name(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-native-tools-bad-fill")
    ctx = SampleContext(
        sample=_REF,
        evidence=[],
        adapter=None,
        sink=sink,
        arm="bare-core-native-tools",
        task_instruction="T.",
        decoding_params=_DECODING,
        request_id_base="req-0001",
        extras={
            "config_values": {"tool_schema_fill": "no-such-fill"},
            "data_root": Path("/unused"),
        },
    )
    with pytest.raises(Exception, match="no-such-fill"):
        FixedPolicy().run_sample(ctx)


# ---------------------------------------------------------------------------
# Config fragment composition: the new baseline+model fragments are
# well-formed against the real repo (mirrors tests/unit/test_audio2tool_
# loader.py's own test_p1_config_fragments_compose_against_the_real_repo),
# and core.config.compose tolerates the model fragment's top-level "_note"
# key (goal 5's own explicit check).
# ---------------------------------------------------------------------------


def test_native_tools_config_fragments_compose_against_the_real_repo():
    from speech_aware_evidence_acquisition.core.config import compose
    from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT

    composed = compose(
        REPO_ROOT,
        "q8-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-r1-sample400",
        "a2t-direct-native-tools",
        "r1-audio2tool",
    )
    values = composed.values
    assert values["carrier_lock_key"] == "audio2tool"
    assert values["arm"] == "bare-core-native-tools"
    assert values["scorers"] == ["a2t-toolcall", "cost"]
    assert values["tool_schema_fill"] == "audio2tool-openai-tools"
    # A literal instruction, not the template+fill mechanism: the frozen
    # template's own placeholder contract (core.instructions.
    # resolve_task_instruction: "if TOOL_SCHEMAS_PLACEHOLDER not in
    # template_text: raise") requires the {tool_schemas} token in ANY
    # template_rel it is given, and this arm's short instruction
    # deliberately carries no schema text at all (goal 5) -- so
    # task_instruction_template is never set for this baseline.
    assert "task_instruction_template" not in values
    assert "task_instruction_fill" not in values
    assert isinstance(values["task_instruction"], str) and values["task_instruction"]
    # compose() merges the model fragment's top-level "_note" key like any
    # other -- no special-casing needed, confirmed against the real fragment
    # rather than assumed.
    assert isinstance(values.get("_note"), str) and values["_note"]
    assert values["model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf"
    assert values["execution_profile"] == "baseline-reproduction"

    # The probe file exists and its text matches the baseline's literal
    # instruction byte-for-byte (module docstring: kept as the canonical
    # reference copy even though it is not loaded through
    # task_instruction_template).
    probe_path = REPO_ROOT / "configs" / "probes" / "r1_audio2tool_direct_native_tools.txt"
    assert probe_path.read_text(encoding="utf-8").rstrip("\n") == values["task_instruction"]


# ---------------------------------------------------------------------------
# LlamaServerTransport: tools pass-through + tool_calls canonicalization.
# Needs a real (spawned) session-liveness match -- see module docstring.
# ---------------------------------------------------------------------------

_BINARY_PATH = "llama.cpp/build/bin/llama-server"
_MODEL_FILES = (ModelFileRef(path="models/qwen3-omni/model.gguf", sha256="a" * 64),)
_live: dict[str, object] = {}


@pytest.fixture(scope="module", autouse=True)
def _spawn_live_matching_process(tmp_path_factory):
    base = tmp_path_factory.mktemp("native-tools-session-world")
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
        "s.bind(('127.0.0.1', 0))\n"
        "s.listen(1)\n"
        "print(s.getsockname()[1], flush=True)\n"
        "time.sleep(300)\n"
    )
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
                    with socket.create_connection(("127.0.0.1", candidate_port), timeout=0.5):
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


def _base_url():
    return f"http://127.0.0.1:{_live['port']}"


def _fake_session():
    return SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study=STUDY_SLUG,
        session_id="test-native-tools-session",
        binary_path=_BINARY_PATH,
        binary_sha256=_live["binary_sha256"],
        argv=(_BINARY_PATH, "--host", "127.0.0.1", "--port", str(_live["port"])),
        pid=_live["pid"],
        host="127.0.0.1",
        port=_live["port"],
        model_files=_MODEL_FILES,
        started_at="2026-09-03T00:00:00+00:00",
        startup_stdout_sha256=hashlib.sha256(b"").hexdigest(),
    )


def _fake_runtime_receipt():
    return {
        "llama_cpp": {"binary_path": _BINARY_PATH, "binary_sha256": _live["binary_sha256"]},
        "gguf_files": [{"path": f.path, "sha256": f.sha256} for f in _MODEL_FILES],
    }


def _transport(*, post, data_root):
    return LlamaServerTransport(
        _base_url(),
        data_root,
        _fake_session(),
        _fake_runtime_receipt(),
        _live["runtime_root"],
        post=post,
    )


def _native_tools_payload(tmp_path, **overrides):
    media = tmp_path / "media" / "1.wav"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(b"fake-wav-bytes")
    payload = {
        "request_id": "req-1",
        "carrier_lock_key": "audio2tool",
        "sample_id": "tier1_direct:000001",
        "speech_ref": "audio2tool/tier1_direct:000001",
        "media_relpath": "media/1.wav",
        "audio_seconds": 1.5,
        "sample_rate_hz": 16000,
        "task_instruction": "You are a voice assistant.",
        "history": [],
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "tool_schemas": _TOOL_SCHEMAS,
    }
    payload.update(overrides)
    return payload


def _request_adapter(tmp_path, *, arm, transport):
    plan = ExecutionPlan(
        run_id="SAEA-E-000-native-request-controls",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=2,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=10.0,
        protocol_hash="b" * 64,
        attempt_id="attempt-native-request-controls",
    )
    binding = PayloadBindingContext(
        carrier_lock_key="audio2tool",
        allowed_sample_ids=frozenset({_REF.sample_id}),
        sample_facts={_REF.sample_id: (_REF.audio_seconds, _REF.sample_rate_hz)},
        data_root=tmp_path,
        carrier_root=tmp_path / "media",
    )
    return FrozenCoreAdapter(
        gate=_OpenGate(),
        plan=plan,
        arm=arm,
        transport=transport,
        sink=TraceSink(tmp_path / f"run-{arm}", plan.run_id),
        binding=binding,
    )


def _canned_content_response():
    return json.dumps(
        {
            "choices": [{"message": {"content": "hello world"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        }
    ).encode()


def test_transport_sends_tools_verbatim_and_never_a_tool_choice(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_content_response()

    transport = _transport(post=fake_post, data_root=tmp_path)
    transport(json.dumps(_native_tools_payload(tmp_path)).encode())

    assert captured["body"]["tools"] == _TOOL_SCHEMAS
    assert "tool_choice" not in captured["body"]
    # decoding_params still merge in exactly as before this arm existed.
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["seed"] == 20260803
    assert "parallel_tool_calls" not in captured["body"]


@pytest.mark.parametrize("tool_choice", ["auto", "none"])
def test_adapter_and_production_transport_send_native_request_controls_at_top_level(
    tmp_path, tool_choice
):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_content_response()

    transport = _transport(post=fake_post, data_root=tmp_path)
    adapter = _request_adapter(
        tmp_path, arm="bare-core-native-tools", transport=transport
    )
    payload = _native_tools_payload(
        tmp_path,
        decoding_params={
            **_DECODING,
            "tool_choice": tool_choice,
            "parallel_tool_calls": False,
        },
    )

    response = adapter.request(payload)

    assert response.text == "hello world"
    assert captured["body"]["tool_choice"] == tool_choice
    assert captured["body"]["parallel_tool_calls"] is False
    assert captured["body"]["temperature"] == 0
    assert captured["body"]["seed"] == 20260803


def test_transport_omits_wire_tools_for_explicit_empty_final_scope(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_content_response()

    transport = _transport(post=fake_post, data_root=tmp_path)
    payload = _native_tools_payload(
        tmp_path,
        tool_schemas=[],
        decoding_params={**_DECODING, "tool_choice": "none"},
    )
    transport(json.dumps(payload).encode())

    assert "tools" not in captured["body"]
    assert captured["body"]["tool_choice"] == "none"


def test_transport_refuses_empty_tools_with_nonfinal_choice_before_post(tmp_path):
    posts = []
    transport = _transport(post=lambda url, body: posts.append((url, body)), data_root=tmp_path)
    payload = _native_tools_payload(
        tmp_path,
        tool_schemas=[],
        decoding_params={**_DECODING, "tool_choice": "auto"},
    )

    with pytest.raises(FrozenCoreError, match="empty tool_schemas"):
        transport(json.dumps(payload).encode())
    assert posts == []


def test_native_parallel_false_is_independently_optional(tmp_path):
    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_content_response()

    transport = _transport(post=fake_post, data_root=tmp_path)
    adapter = _request_adapter(
        tmp_path, arm="bare-core-native-tools", transport=transport
    )
    payload = _native_tools_payload(
        tmp_path, decoding_params={**_DECODING, "parallel_tool_calls": False}
    )

    adapter.request(payload)

    assert captured["body"]["parallel_tool_calls"] is False
    assert "tool_choice" not in captured["body"]


def test_actual_request_fit_renders_native_controls_at_top_level(tmp_path):
    seen = {}
    transport = _transport(post=lambda u, b: _canned_content_response(), data_root=tmp_path)
    payload = _native_tools_payload(
        tmp_path,
        decoding_params={
            **_DECODING,
            "tool_choice": "auto",
            "parallel_tool_calls": False,
        },
    )

    def request_measure(client, body, **kwargs):
        seen.update(body)
        return {"fits": True, "margin_tokens": 8}

    receipt = fit_requests(
        [payload],
        expected_sample_ids=[payload["sample_id"]],
        transport=transport,
        client=object(),
        speech_counts=lambda _payload: [1],
        media_marker="<unused>",
        slot_tokens=1024,
        request_measure=request_measure,
    )

    assert receipt["every_request_fits"] is True
    assert seen["tools"] == _TOOL_SCHEMAS
    assert seen["tool_choice"] == "auto"
    assert seen["parallel_tool_calls"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("tool_choice", "required"),
        ("tool_choice", True),
        ("tool_choice", None),
        ("parallel_tool_calls", True),
        ("parallel_tool_calls", "false"),
        ("parallel_tool_calls", 0),
    ],
)
def test_adapter_rejects_unsupported_native_request_control_values_before_transport(
    tmp_path, field, value
):
    contacted = False

    def forbidden_transport(_request):
        nonlocal contacted
        contacted = True
        raise AssertionError("invalid request control reached transport")

    adapter = _request_adapter(
        tmp_path, arm="bare-core-native-tools", transport=forbidden_transport
    )
    payload = _native_tools_payload(tmp_path, decoding_params={**_DECODING, field: value})

    with pytest.raises(FrozenCoreError, match=field):
        adapter.request(payload)

    assert contacted is False


@pytest.mark.parametrize(
    "request_controls",
    [{"tool_choice": "auto"}, {"parallel_tool_calls": False}],
)
def test_adapter_rejects_native_request_controls_on_non_native_arms(
    tmp_path, request_controls
):
    contacted = False

    def forbidden_transport(_request):
        nonlocal contacted
        contacted = True
        raise AssertionError("native request control reached transport")

    adapter = _request_adapter(tmp_path, arm="bare-core", transport=forbidden_transport)
    payload = _native_tools_payload(
        tmp_path, decoding_params={**_DECODING, **request_controls}
    )
    payload.pop("tool_schemas")

    with pytest.raises(FrozenCoreError, match="native tool"):
        adapter.request(payload)

    assert contacted is False


@pytest.mark.parametrize(
    "decoding_params",
    [
        {**_DECODING, "tool_choice": "auto"},
        {**_DECODING, "parallel_tool_calls": False},
    ],
)
def test_transport_refuses_native_request_controls_without_tool_schemas(
    tmp_path, decoding_params
):
    transport = _transport(post=lambda u, b: _canned_content_response(), data_root=tmp_path)
    payload = _native_tools_payload(tmp_path, decoding_params=decoding_params)
    payload.pop("tool_schemas")

    with pytest.raises(FrozenCoreError, match="native tool"):
        transport.render_request(json.dumps(payload).encode())


def test_transport_refuses_an_empty_tool_schemas_list_on_the_wire(tmp_path):
    transport = _transport(post=lambda u, b: _canned_content_response(), data_root=tmp_path)
    payload = _native_tools_payload(tmp_path, tool_schemas=[])
    with pytest.raises(FrozenCoreError, match="tool_schemas"):
        transport(json.dumps(payload).encode())


def test_transport_absent_tool_schemas_is_byte_identical_to_before_this_arm(tmp_path):
    """A payload that never carries "tool_schemas" (every arm registered
    before D1a) sends a body with no "tools" key at all -- unchanged."""

    captured = {}

    def fake_post(url, body):
        captured["body"] = json.loads(body)
        return _canned_content_response()

    transport = _transport(post=fake_post, data_root=tmp_path)
    payload = _native_tools_payload(tmp_path)
    del payload["tool_schemas"]
    transport(json.dumps(payload).encode())
    assert "tools" not in captured["body"]


def test_transport_canonicalizes_tool_calls_into_text_and_raw_envelope(tmp_path):
    server_response = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "setZoneTemperature",
                                    "arguments": json.dumps(
                                        {"zone": "Driver", "temperature": 22.0}
                                    ),
                                },
                            }
                        ],
                    }
                }
            ],
            "usage": {"prompt_tokens": 11, "completion_tokens": 4},
        }
    ).encode()

    transport = _transport(post=lambda u, b: server_response, data_root=tmp_path)
    raw = transport(json.dumps(_native_tools_payload(tmp_path)).encode())
    envelope = json.loads(raw)

    assert json.loads(envelope["text"]) == [
        {"name": "setZoneTemperature", "arguments": {"zone": "Driver", "temperature": 22.0}}
    ]
    assert envelope["usage"] == {"prompt_tokens": 11, "completion_tokens": 4}
    # Raw pass-through: the server's own tool_calls list, untouched --
    # arguments still the original JSON STRING, not the parsed dict.
    assert envelope["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "setZoneTemperature",
                "arguments": json.dumps({"zone": "Driver", "temperature": 22.0}),
            },
        }
    ]
    assert "tool_call_argument_parse_errors" not in envelope


def test_transport_multiple_tool_calls_preserve_call_order(tmp_path):
    server_response = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "setFanSpeed",
                                    "arguments": json.dumps({"level": 7}),
                                }
                            },
                            {
                                "function": {
                                    "name": "setHvacMode",
                                    "arguments": json.dumps({"mode": "COOL"}),
                                }
                            },
                        ],
                    }
                }
            ],
            "usage": {},
        }
    ).encode()

    transport = _transport(post=lambda u, b: server_response, data_root=tmp_path)
    raw = transport(json.dumps(_native_tools_payload(tmp_path)).encode())
    envelope = json.loads(raw)

    assert json.loads(envelope["text"]) == [
        {"name": "setFanSpeed", "arguments": {"level": 7}},
        {"name": "setHvacMode", "arguments": {"mode": "COOL"}},
    ]


def test_transport_malformed_tool_call_arguments_fail_closed_into_empty_with_a_flag(tmp_path):
    server_response = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "goodCall",
                                    "arguments": json.dumps({"x": 1}),
                                }
                            },
                            {
                                "function": {
                                    "name": "badCall",
                                    "arguments": "{not valid json",
                                }
                            },
                            {
                                "function": {
                                    # Decodes to a JSON array, not an object.
                                    "name": "alsoBadCall",
                                    "arguments": "[1, 2]",
                                }
                            },
                        ],
                    }
                }
            ],
            "usage": {},
        }
    ).encode()

    transport = _transport(post=lambda u, b: server_response, data_root=tmp_path)
    raw = transport(json.dumps(_native_tools_payload(tmp_path)).encode())
    envelope = json.loads(raw)

    assert json.loads(envelope["text"]) == [
        {"name": "goodCall", "arguments": {"x": 1}},
        {"name": "badCall", "arguments": {}},
        {"name": "alsoBadCall", "arguments": {}},
    ]
    assert envelope["tool_call_argument_parse_errors"] == [1, 2]
    # The raw pass-through still carries the ORIGINAL (unparseable) strings.
    assert envelope["tool_calls"][1]["function"]["arguments"] == "{not valid json"


def test_transport_empty_tool_calls_list_behaves_like_absent(tmp_path):
    server_response = json.dumps(
        {
            "choices": [{"message": {"content": "hello world", "tool_calls": []}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 2},
        }
    ).encode()
    transport = _transport(post=lambda u, b: server_response, data_root=tmp_path)
    raw = transport(json.dumps(_native_tools_payload(tmp_path)).encode())
    envelope = json.loads(raw)
    assert envelope == {
        "text": "hello world",
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
    }
    assert "tool_calls" not in envelope


def test_transport_missing_tool_calls_key_is_byte_identical_to_the_legacy_response(tmp_path):
    """The strict-equality canned-response contract this module must never
    break (tests/unit/test_llama_server_transport.py's own
    test_body_mapping_and_response_projection) -- re-affirmed here through a
    request that DOES carry tool_schemas, proving a response that simply
    never uses them still degrades to the exact legacy envelope shape."""

    transport = _transport(post=lambda u, b: _canned_content_response(), data_root=tmp_path)
    raw = transport(json.dumps(_native_tools_payload(tmp_path)).encode())
    envelope = json.loads(raw)
    assert envelope == {
        "text": "hello world",
        "usage": {"prompt_tokens": 7, "completion_tokens": 2},
    }
