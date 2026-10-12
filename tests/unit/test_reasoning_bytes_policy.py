"""Owner decision 286: reasoning bytes are never part of the sealed trace; only their hash and statistics are.

Stub servers only (the transport's injected ``post``); no llama.cpp, GPU, encoder or dataset is contacted.
"""

from __future__ import annotations

import base64
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError, wire_response_message
from speech_aware_evidence_acquisition.core.reasoning_knobs import REASONING_BYTES_POLICY

from test_llama_server_transport import (  # noqa: F401  (the autouse fixture must be imported to run)
    _base_url,
    _boundary_payload,
    _fake_runtime_receipt,
    _fake_session,
    _live,
    _spawn_live_matching_process,
    _transport,
)
from test_thinking_transport_and_native_knobs import (  # noqa: F401
    GUARD, KNOBS, MESSAGE, _adapter_cost, _post_script, _send, _thinking_transport, _wire,
)

SECRET = "the private chain of thought SECRET-REASONING-BYTES"
FIVE = {"reasoning_content_sha256", "reasoning_chars", "reasoning_tokens", "forced_close", "finish_reason"}


def _stored(envelope):
    return base64.b64decode(envelope["wire_response_b64"])


def test_the_envelope_has_the_five_fields_and_never_the_bytes(tmp_path):
    reasoning = SECRET + " " + MESSAGE
    wire = _wire("turn on the lights", reasoning=reasoning, finish="length",
                 usage_extra={"completion_tokens_details": {"reasoning_tokens": 77}})
    envelope = _send(_thinking_transport(tmp_path, _post_script([wire], [])), tmp_path, **KNOBS)
    summary = envelope["reasoning"]
    assert FIVE <= set(summary)
    assert summary["reasoning_content_sha256"] == hashlib.sha256(reasoning.encode("utf-8")).hexdigest()
    assert summary["reasoning_chars"] == len(reasoning) and summary["reasoning_tokens"] == 77
    assert summary["forced_close"] is True and summary["finish_reason"] == "length"
    assert summary["reasoning_bytes_policy"] == REASONING_BYTES_POLICY == "hash-and-stats-only-v1"
    assert "SECRET-REASONING-BYTES" not in json.dumps(envelope) and "reasoning_content" not in json.dumps(envelope).replace("reasoning_content_sha256", "")


def test_forced_close_is_false_when_the_pinned_message_does_not_end_the_reasoning(tmp_path):
    envelope = _send(_thinking_transport(tmp_path, _post_script([_wire("x", reasoning=MESSAGE + " and then more thinking")], [])),
                     tmp_path, **KNOBS)
    assert envelope["reasoning"]["forced_close"] is False


def test_the_policy_is_unconditional_even_on_an_unguarded_transport(tmp_path):
    transport = _transport(_base_url(), tmp_path, post=_post_script([_wire("x", reasoning=SECRET)], []))
    envelope = json.loads(transport(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert envelope["reasoning"]["reasoning_content_sha256"] == hashlib.sha256(SECRET.encode()).hexdigest()
    assert "SECRET-REASONING-BYTES" not in json.dumps(envelope)


def test_a_preserved_wire_response_stores_the_projection_and_hashes_the_stored_bytes(tmp_path):
    reasoning = SECRET
    wire = _wire("turn on the lights", reasoning=reasoning)
    envelope = _send(_thinking_transport(tmp_path, _post_script([wire], []), preserve_wire_responses=True), tmp_path, **KNOBS)
    stored = _stored(envelope)
    assert b"SECRET-REASONING-BYTES" not in stored and b'"reasoning_content"' not in stored
    assert envelope["wire_response_sha256"] == hashlib.sha256(stored).hexdigest()
    assert envelope["wire_response_sha256"] != hashlib.sha256(json.dumps(wire).encode()).hexdigest()
    document = json.loads(stored)
    message = document["choices"][0]["message"]
    assert message["content"] == "turn on the lights" and message["reasoning"] == envelope["reasoning"]
    assert message["reasoning"]["reasoning_content_sha256"] == hashlib.sha256(reasoning.encode()).hexdigest()
    assert document["usage"] == wire["usage"] and envelope["wire_finish_reason"] == "stop"
    # The stored bytes are still a readable wire response (the replay/resume reader).
    parsed_message, finish = wire_response_message(stored, None)
    assert parsed_message["content"] == "turn on the lights" and finish == "stop"


def test_a_preserved_malformed_response_is_projected_too(tmp_path):
    wire = {"choices": [{"message": {"reasoning_content": SECRET}, "finish_reason": "length"}], "usage": {"prompt_tokens": 1}}
    transport = _thinking_transport(tmp_path, _post_script([wire], []), preserve_wire_responses=True)
    payload = _boundary_payload(tmp_path)
    payload["decoding_params"] = {"temperature": 0, "seed": 1, **KNOBS}
    envelope = json.loads(transport(json.dumps(payload).encode()))
    assert "wire_response_error" in envelope
    stored = _stored(envelope)
    assert b"SECRET-REASONING-BYTES" not in stored
    assert envelope["wire_response_sha256"] == hashlib.sha256(stored).hexdigest()


def test_a_response_without_reasoning_is_stored_byte_identical(tmp_path):
    """The Instruct direct-only response bytes do not change: no ``reasoning_content`` key, no projection, no envelope key."""

    wire = {"choices": [{"message": {"role": "assistant", "content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1}}
    raw = json.dumps(wire).encode()
    transport = _transport(_base_url(), tmp_path, post=lambda _u, _b: raw, preserve_wire_responses=True)
    envelope = json.loads(transport(json.dumps(_boundary_payload(tmp_path)).encode()))
    assert _stored(envelope) == raw and envelope["wire_response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert "reasoning" not in envelope
    plain = _transport(_base_url(), tmp_path, post=lambda _u, _b: raw)
    assert set(json.loads(plain(json.dumps(_boundary_payload(tmp_path)).encode()))) == {"text", "usage"}


def test_the_cost_record_carries_the_hash_and_policy_but_no_bytes(tmp_path):
    reasoning = SECRET + " " + MESSAGE
    envelope = _send(_thinking_transport(tmp_path, _post_script([_wire("hi", reasoning=reasoning)], [])), tmp_path, **KNOBS)
    cost = _adapter_cost(tmp_path / "cost", envelope)
    assert cost["reasoning_content_sha256"] == hashlib.sha256(reasoning.encode()).hexdigest()
    assert cost["reasoning_bytes_policy"] == REASONING_BYTES_POLICY and cost["forced_close"] is True
    assert cost["reasoning_chars"] == len(reasoning) and "SECRET-REASONING-BYTES" not in json.dumps(cost)


def test_the_empty_completion_cap_hit_envelope_is_unchanged_apart_from_the_projection(tmp_path):
    envelope = _send(_thinking_transport(tmp_path, _post_script([_wire("", reasoning="runaway", finish="length", completion_tokens=4096)], [])),
                     tmp_path, **KNOBS)
    assert envelope["text"] == "" and envelope["finish_reason"] == "length" and envelope["usage"]["completion_tokens"] == 4096
