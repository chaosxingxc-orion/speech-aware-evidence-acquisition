"""Decision 283 A: the Thinking-core knobs on the wire and in the native request seam, with stub servers only.

The transport is driven through its injected ``post`` (no socket), the adapter through a recording trace sink, and the native request
composer through a real ``FrozenCoreClient`` over a scripted in-process transport. No llama.cpp, GPU, encoder or dataset is contacted.
"""

from __future__ import annotations

import base64
import hashlib
import json
from types import MappingProxyType

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter, FrozenCoreError
from speech_aware_evidence_acquisition.core.model.transport import _llama_server_factory
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer, TraceSink, set_current_trace_buffer
from speech_aware_evidence_acquisition.reproduction.ojw.native_request import (
    MeteredNativeSpeechRequest,
    NativeRoleSpeechBinding,
    NativeSpeechRequestError,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import NativeRoleContactContext, NativeRoleModelRequest

from test_frozen_core_adapter import _OpenGate, _binding as _adapter_binding, _payload as _adapter_payload, _plan as _adapter_plan
from test_llama_server_transport import (  # noqa: F401  (the autouse fixture must be imported to run)
    _base_url,
    _boundary_payload,
    _fake_runtime_receipt,
    _fake_session,
    _live,
    _spawn_live_matching_process,
    _transport,
)
from test_rails_core_client_native_tools import (
    _TOOLS, _World, _client, _plan as _native_plan, _speech_feature_messages, _speech_feature_world,
)

GUARD = "refuse-think-marker-in-content"
MESSAGE = "Considering the limited time by the user, I have to give the solution based on the thinking directly now."
KNOBS = {"thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}, "max_tokens": 4096}


def _post_script(responses, captured):
    """A ``post`` that records each request body and replays scripted wire responses."""

    state = {"i": 0}

    def post(_url, body):
        captured.append(json.loads(body))
        wire = responses[min(state["i"], len(responses) - 1)]
        state["i"] += 1
        return json.dumps(wire).encode()

    return post


def _wire(content, *, reasoning="private thoughts", finish="stop", completion_tokens=40, usage_extra=None):
    usage = {"prompt_tokens": 100, "completion_tokens": completion_tokens}
    if usage_extra:
        usage.update(usage_extra)
    message = {"role": "assistant", "content": content}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return {"choices": [{"message": message, "finish_reason": finish}], "usage": usage}


def _send(transport, tmp_path, **decoding):
    payload = _boundary_payload(tmp_path)
    payload["decoding_params"] = {"temperature": 0, "seed": 20260913, **decoding}
    return json.loads(transport(json.dumps(payload).encode()))


def _thinking_transport(tmp_path, post, **kwargs):
    return _transport(_base_url(), tmp_path, post=post, reasoning_content_guard=GUARD, reasoning_telemetry=True,
                      forced_close_message=MESSAGE, **kwargs)


# ---------------------------------------------------------------------------
# the wire
# ---------------------------------------------------------------------------


def test_the_request_carries_the_two_declared_reasoning_fields_verbatim(tmp_path):
    captured = []
    transport = _thinking_transport(tmp_path, _post_script([_wire("turn on the lights")], captured))
    _send(transport, tmp_path, **KNOBS)
    body = captured[0]
    assert body["thinking_budget_tokens"] == 3072
    assert body["chat_template_kwargs"] == {"enable_thinking": True}
    assert body["max_tokens"] == 4096 and body["temperature"] == 0
    assert "reasoning_budget_message" not in body and "forced_close_message" not in json.dumps(body)


def test_a_request_without_the_knobs_has_exactly_the_historical_body(tmp_path):
    """No request-bytes change for a fragment that declares no knob, guarded or not: the body is messages plus the decoding keys."""

    for kwargs in ({}, {"reasoning_content_guard": GUARD}):
        captured = []
        transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x")], captured), **kwargs)
        _send(transport, tmp_path, max_tokens=8192)
        assert set(captured[0]) == {"messages", "temperature", "seed", "max_tokens"}
        assert captured[0]["max_tokens"] == 8192


def test_reasoning_controls_are_refused_without_the_reasoning_guard(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x")], []))
    with pytest.raises(FrozenCoreError, match="no reasoning_content_guard"):
        _send(transport, tmp_path, thinking_budget_tokens=10)


@pytest.mark.parametrize("bad", [
    {"thinking_budget_tokens": -1}, {"thinking_budget_tokens": True},
    {"chat_template_kwargs": {"enable_thinking": "no"}}, {"chat_template_kwargs": {"enable_thinking": True, "extra": 1}},
])
def test_malformed_reasoning_controls_are_refused_at_the_transport(tmp_path, bad):
    transport = _thinking_transport(tmp_path, _post_script([_wire("x")], []))
    with pytest.raises(FrozenCoreError):
        _send(transport, tmp_path, **bad)


def test_telemetry_requires_the_guard_and_a_message_must_be_non_empty(tmp_path):
    from speech_aware_evidence_acquisition.core.session import SessionError

    with pytest.raises(SessionError, match="requires reasoning_content_guard"):
        _transport(_base_url(), tmp_path, post=lambda *_: b"", reasoning_telemetry=True)
    with pytest.raises(SessionError, match="forced_close_message"):
        _transport(_base_url(), tmp_path, post=lambda *_: b"", reasoning_content_guard=GUARD, forced_close_message="")


# ---------------------------------------------------------------------------
# the response: normal, forced close, empty at the cap
# ---------------------------------------------------------------------------


def test_a_normal_answer_records_counts_and_no_forced_close(tmp_path):
    transport = _thinking_transport(tmp_path, _post_script([_wire("turn on the lights", reasoning="think think")], []))
    envelope = _send(transport, tmp_path, **KNOBS)
    assert envelope["text"] == "turn on the lights" and envelope["finish_reason"] == "stop"
    assert envelope["reasoning"] == {
        "reasoning_content_sha256": hashlib.sha256(b"think think").hexdigest(),
        "reasoning_chars": 11, "reasoning_tokens": None, "reasoning_tokens_basis": "not-reported-by-server",
        "forced_close": False, "forced_close_basis": "reasoning-ends-with-pinned-budget-message",
        "finish_reason": "stop", "reasoning_bytes_policy": "hash-and-stats-only-v1",
    }
    assert "think think" not in json.dumps(envelope)


def test_a_forced_close_is_detected_from_the_end_of_the_reasoning_channel(tmp_path):
    reasoning = "a very long chain of thought that ran into the budget " + MESSAGE
    transport = _thinking_transport(tmp_path, _post_script([_wire("set an alarm", reasoning=reasoning, completion_tokens=4000)], []))
    envelope = _send(transport, tmp_path, **KNOBS)
    assert envelope["reasoning"]["forced_close"] is True and envelope["reasoning"]["reasoning_chars"] == len(reasoning)
    assert envelope["text"] == "set an alarm" and MESSAGE not in envelope["text"]
    assert reasoning not in json.dumps(envelope)


def test_server_reported_reasoning_tokens_are_used_when_present(tmp_path):
    wire = _wire("x", usage_extra={"completion_tokens_details": {"reasoning_tokens": 812}})
    envelope = _send(_thinking_transport(tmp_path, _post_script([wire], [])), tmp_path, **KNOBS)
    assert envelope["reasoning"]["reasoning_tokens"] == 812
    assert envelope["reasoning"]["reasoning_tokens_basis"] == "server-usage-details"
    assert envelope["usage"] == {"prompt_tokens": 100, "completion_tokens": 40}


def test_forced_close_is_undetectable_without_a_pinned_message(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x", reasoning="r " + MESSAGE)], []),
                           reasoning_content_guard=GUARD, reasoning_telemetry=True)
    reasoning = _send(transport, tmp_path, **KNOBS)["reasoning"]
    assert reasoning["forced_close"] is None and reasoning["forced_close_basis"] == "no-pinned-budget-message"


def test_empty_content_at_the_cap_is_delivered_empty_with_its_finish_reason(tmp_path):
    transport = _thinking_transport(tmp_path, _post_script([_wire("", reasoning="runaway", finish="length", completion_tokens=4096)], []))
    envelope = _send(transport, tmp_path, **KNOBS)
    assert envelope["text"] == "" and envelope["finish_reason"] == "length"
    assert envelope["reasoning"]["forced_close"] is False and envelope["usage"]["completion_tokens"] == 4096


def test_the_guarded_envelope_without_telemetry_is_unchanged(tmp_path):
    """The existing Thinking max8192 fragment declares no knob, so its transport has no telemetry and its envelope keeps its keys."""

    transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x", reasoning=None)], []), reasoning_content_guard=GUARD)
    assert set(_send(transport, tmp_path, max_tokens=8192)) == {"text", "usage", "finish_reason"}
    # Decision 286: when the response does carry reasoning bytes the projection is added whatever the knobs.
    carrying = _transport(_base_url(), tmp_path, post=_post_script([_wire("x")], []), reasoning_content_guard=GUARD)
    assert set(_send(carrying, tmp_path, max_tokens=8192)) == {"text", "usage", "finish_reason", "reasoning"}


def test_the_factory_arms_telemetry_and_the_pinned_message_from_the_composed_config(tmp_path):
    values = {
        "base_url": _base_url(), "prompt_order": "evidence-first-system-v3", "reasoning_content_guard": GUARD,
        "reasoning_budget_tokens": 3072, "server_args": ["-c", "1", "--reasoning-budget-message", MESSAGE],
    }
    transport = _llama_server_factory(values, tmp_path, session=_fake_session(), runtime_receipt=_fake_runtime_receipt(),
                                      runtime_root=_live["runtime_root"])
    assert transport._reasoning_telemetry is True and transport._forced_close_message == MESSAGE
    plain = _llama_server_factory({"base_url": _base_url(), "prompt_order": "evidence-first-system-v3"}, tmp_path,
                                  session=_fake_session(), runtime_receipt=_fake_runtime_receipt(), runtime_root=_live["runtime_root"])
    assert plain._reasoning_telemetry is False and plain._forced_close_message is None


# ---------------------------------------------------------------------------
# the adapter: COST record fields
# ---------------------------------------------------------------------------


class _RecordingSink(TraceSink):
    seen: list

    def emit(self, channel, record_id, payload):
        self.seen.append((channel, record_id, dict(payload)))
        return super().emit(channel, record_id, payload)


def _adapter_cost(tmp_path, envelope):
    sink = _RecordingSink(tmp_path / "run", "SAEA-E-000-reasoning-cost")
    sink.seen = []
    adapter = FrozenCoreAdapter(
        gate=_OpenGate(), plan=_adapter_plan(), arm="bare-core", sink=sink, binding=_adapter_binding(tmp_path),
        transport=lambda _bytes: json.dumps(envelope).encode(),
    )
    adapter.request(_adapter_payload())
    return next(payload for channel, rid, payload in sink.seen if channel == "COST")


def test_the_cost_record_carries_reasoning_counts_only_when_the_transport_forwarded_them(tmp_path):
    usage = {"prompt_tokens": 5, "completion_tokens": 2}
    plain = _adapter_cost(tmp_path / "a", {"text": "hi", "usage": usage, "finish_reason": "stop"})
    assert set(plain) == {"calls", "audio_seconds", "latency_seconds", "prompt_tokens", "completion_tokens", "finish_reason"}
    reasoning = {"reasoning_chars": 90, "reasoning_tokens": None, "forced_close": True, "reasoning_tokens_basis": "not-reported-by-server"}
    cost = _adapter_cost(tmp_path / "b", {"text": "hi", "usage": usage, "finish_reason": "stop", "reasoning": reasoning})
    assert cost["finish_reason"] == "stop" and cost["forced_close"] is True
    assert cost["reasoning_chars"] == 90 and cost["reasoning_tokens"] is None
    assert "reasoning_tokens_basis" not in cost


def test_the_adapter_refuses_malformed_reasoning_controls_before_the_call(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-reasoning-refuse")
    adapter = FrozenCoreAdapter(gate=_OpenGate(), plan=_adapter_plan(), arm="bare-core", sink=sink,
                                binding=_adapter_binding(tmp_path), transport=lambda _b: b"")
    payload = _adapter_payload(decoding_params={"temperature": 0, "chat_template_kwargs": {"enable_thinking": "false"}})
    with pytest.raises(FrozenCoreError, match="chat_template_kwargs"):
        adapter.request(payload)
    allowed = _adapter_payload(decoding_params={"temperature": 0, **KNOBS})
    with pytest.raises(FrozenCoreError, match="malformed response|non-JSON|Expecting"):
        adapter.request(allowed)  # reaches the (empty) transport: the keys are admitted


# ---------------------------------------------------------------------------
# the native request seam: per-role policy, answer-only composition, fallback dispatch
# ---------------------------------------------------------------------------


def _role_request(role_id, contact_id):
    return NativeRoleModelRequest(
        role_id=role_id,
        context=NativeRoleContactContext(sample_id="s1", agent_contact_id=contact_id),
        messages=({"role": "system", "content": "Choose exactly one opaque key id."}, {"role": "user", "content": "Inspect the speech."}),
        tool_schemas=(), visible_tool_names=(), decoding_controls=MappingProxyType({}),
    )


def _native_binding(role_id, packet, **decoding):
    return NativeRoleSpeechBinding(
        role_id=role_id, sample_id="s1", role_query="Inspect the speech.", base_messages=_speech_feature_messages(packet),
        core_kwargs={"agent_state": (), "key_representation_id": "key-v1", "matcher_policy_id": "matcher-v1",
                     "decoding_params": dict(KNOBS if not decoding else decoding)},
        tool_names=(),
    )


class _ScriptedTransport:
    """A core transport scripted per call: ``(text, finish_reason, completion_tokens)``; preserves wire bytes like a guarded transport."""

    def __init__(self, script):
        self.script, self.calls = list(script), []

    def __call__(self, request_bytes):
        payload = json.loads(request_bytes.decode("utf-8"))
        self.calls.append(payload)
        text, finish, tokens = self.script[len(self.calls) - 1]
        raw = json.dumps({"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": finish}],
                          "usage": {"prompt_tokens": 3, "completion_tokens": tokens}}, separators=(",", ":")).encode()
        return json.dumps({
            "text": text, "usage": {"prompt_tokens": 3, "completion_tokens": tokens}, "finish_reason": finish,
            "wire_response_b64": base64.b64encode(raw).decode("ascii"), "wire_response_sha256": hashlib.sha256(raw).hexdigest(),
            "wire_finish_reason": finish,
        }).encode("utf-8")


def _native(tmp_path, script, *, policy=None, role_id="solver", **decoding):
    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    transport = _ScriptedTransport(script)
    client, _gate, _t = _client(world, tmp_path, transport=transport, arm="speech-feature-query-native-tools", tool_schemas=_TOOLS,
                                speech_feature_root=feature_root, speech_packet_bindings=bindings,
                                plan=_native_plan(planned_model_calls=50))
    sunk = []
    adapter = MeteredNativeSpeechRequest(
        client=client, binding_provider=lambda r: _native_binding(r.role_id, packet, **decoding), render_request=lambda b: json.loads(b),
        completion_sink=lambda request, completion: sunk.append(completion), role_thinking_policy=policy,
    )
    return adapter, transport, sunk


def test_native_prepare_resolves_the_per_role_policy_and_leaves_other_roles_alone(tmp_path):
    adapter, _t, _s = _native(tmp_path, [("a", "stop", 3)], policy={"solver": {"reasoning_budget_tokens": 1024}})
    decoding = adapter.prepare(_role_request("solver", "c-solver")).rendered_body()["decoding_params"]
    assert decoding["thinking_budget_tokens"] == 1024 and decoding["max_tokens"] == 2048
    other = adapter.prepare(_role_request("perception", "c-perception")).rendered_body()["decoding_params"]
    assert other["thinking_budget_tokens"] == 3072 and other["max_tokens"] == 4096
    adapter, _t, _s = _native(tmp_path / "n", [("a", "stop", 3)], policy={"solver": {"enable_thinking": False}})
    nothink = adapter.prepare(_role_request("solver", "c-solver")).rendered_body()["decoding_params"]
    assert "thinking_budget_tokens" not in nothink and nothink["chat_template_kwargs"] == {"enable_thinking": False}
    assert nothink["max_tokens"] == 1024


def test_native_answer_only_composition_and_policy_shape_checks(tmp_path):
    adapter, _t, _s = _native(tmp_path, [("a", "stop", 3)])
    prepared = adapter.prepare(_role_request("solver", "c-solver"), answer_only=True)
    decoding = prepared.rendered_body()["decoding_params"]
    assert "thinking_budget_tokens" not in decoding and decoding["max_tokens"] == 1024
    assert decoding["chat_template_kwargs"] == {"enable_thinking": False}
    with pytest.raises(NativeSpeechRequestError, match="role_thinking_policy"):
        MeteredNativeSpeechRequest(client=adapter._client, binding_provider=lambda r: None, render_request=lambda b: {},
                                   completion_sink=lambda *a: None, role_thinking_policy={"solver": "x"})
    plain, _t, _s = _native(tmp_path / "p", [("a", "stop", 3)], max_tokens=512)
    with pytest.raises(NativeSpeechRequestError, match="no answer reserve"):
        plain.prepare(_role_request("solver", "c-solver"), answer_only=True)


def _dispatch(adapter, buffer):
    set_current_trace_buffer(buffer)
    try:
        return adapter.dispatch(adapter.prepare(_role_request("solver", "c-solver")))
    finally:
        set_current_trace_buffer(None)


def _receipts(buffer):
    return [payload for channel, rid, payload in buffer.iter_records() if channel == "TOOL" and rid.endswith("/reasoning-fallback")]


def test_native_normal_answer_is_one_contact_and_no_receipt(tmp_path):
    adapter, transport, sunk = _native(tmp_path, [("slot values", "stop", 700)])
    buffer = TraceBuffer("SAEA-E-TEST-native-tools-client")
    completion = _dispatch(adapter, buffer)
    assert completion.text == "slot values" and len(transport.calls) == 1 and sunk == [completion]
    assert _receipts(buffer) == []


def test_native_empty_at_the_cap_makes_one_answer_only_re_ask_and_sinks_the_re_ask(tmp_path):
    adapter, transport, sunk = _native(tmp_path, [("", "length", 4096), ("slot values", "stop", 20)])
    buffer = TraceBuffer("SAEA-E-TEST-native-tools-client")
    completion = _dispatch(adapter, buffer)
    assert completion.text == "slot values" and len(transport.calls) == 2
    first, second = (call["decoding_params"] for call in transport.calls)
    assert first["thinking_budget_tokens"] == 3072 and first["max_tokens"] == 4096
    assert "thinking_budget_tokens" not in second and second["max_tokens"] == 1024
    assert second["chat_template_kwargs"] == {"enable_thinking": False}
    assert transport.calls[0]["history"] == transport.calls[1]["history"], "the same contact context is re-asked"
    assert sunk == [completion], "only the final completion reaches the episode"
    (receipt,) = _receipts(buffer)
    assert receipt["schema"] == "saea-thinking-answer-fallback-v1" and receipt["agent_contact_id"] == "c-solver"
    assert (receipt["first_finish_reason"], receipt["reask_finish_reason"]) == ("length", "stop")
    assert receipt["answered"] is True and receipt["first_request_id"] != receipt["reask_request_id"]


def test_native_empty_twice_returns_the_empty_re_ask_for_the_existing_disposition(tmp_path):
    adapter, transport, sunk = _native(tmp_path, [("", "length", 4096), ("", "length", 1024)])
    buffer = TraceBuffer("SAEA-E-TEST-native-tools-client")
    completion = _dispatch(adapter, buffer)
    assert completion.text == "" and len(transport.calls) == 2 and sunk == [completion]
    (receipt,) = _receipts(buffer)
    assert receipt["answered"] is False and receipt["disposition"] == "empty-after-fallback-abstention"


def test_native_instruct_style_contact_is_never_re_asked(tmp_path):
    adapter, transport, sunk = _native(tmp_path, [("", "length", 512)], max_tokens=512)
    buffer = TraceBuffer("SAEA-E-TEST-native-tools-client")
    completion = _dispatch(adapter, buffer)
    assert completion.text == "" and len(transport.calls) == 1 and sunk == [completion] and _receipts(buffer) == []


def test_native_empty_stop_is_not_re_asked(tmp_path):
    adapter, transport, _sunk = _native(tmp_path, [("", "stop", 5)])
    buffer = TraceBuffer("SAEA-E-TEST-native-tools-client")
    assert _dispatch(adapter, buffer).text == "" and len(transport.calls) == 1 and _receipts(buffer) == []
