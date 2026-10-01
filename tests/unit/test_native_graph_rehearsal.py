"""Synthetic native rehearsal must never dispatch a live transport."""
import base64
import hashlib
import json
import pytest
from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import (
    RehearsalTransport, synthetic_tool_contact, FourPathResponder,
)

def test_capture_renders_exact_request_and_preserves_typed_tool_authority():
    requests = []
    def render(raw):
        requests.append(raw)
        return {"messages": [{"role": "user", "content": "Exact context"}], "max_tokens": 512}
    response = {"role": "assistant", "content": None, "tool_calls": [{
        "id": "synthetic-lookup", "type": "function",
        "function": {"name": "lookup", "arguments": '{"key":"value"}'},
    }]}
    transport = RehearsalTransport(render, lambda payload: response)
    raw = b'{"sample_id":"synthetic-row"}'
    envelope = json.loads(transport(raw))
    wire = base64.b64decode(envelope["wire_response_b64"])
    assert envelope["wire_response_sha256"] == hashlib.sha256(wire).hexdigest()
    assert json.loads(wire)["choices"][0]["message"] == response
    assert envelope["wire_finish_reason"] == "tool_calls"
    assert json.loads(envelope["text"]) == [{"name": "lookup", "arguments": {"key": "value"}}]
    assert requests == [raw]
    assert transport.records[0]["request"] == transport.render_request(raw)
    assert transport.records[0]["synthetic_response"] == response

def test_plain_response_has_no_tool_call():
    transport = RehearsalTransport(lambda _: {"messages": []},
                                  lambda _: {"role": "assistant", "content": "ACCEPT"})
    envelope = json.loads(transport(b'{"sample_id":"row"}'))
    assert envelope["text"] == "ACCEPT"
    assert envelope["wire_finish_reason"] == "stop"
    assert "tool_calls" not in envelope

def test_invalid_synthetic_response_is_refused_before_recording():
    transport = RehearsalTransport(lambda _: {}, lambda _: {"role": "user", "content": "bad"})
    with pytest.raises(ValueError, match="assistant"):
        transport(b'{}')
    assert not transport.records

def test_synthetic_tool_custody_refuses_real_run_and_invalid_authority():
    from speech_aware_evidence_acquisition.rails.native_tool_authority import NativeToolAuthorityError
    with pytest.raises(ValueError, match="scratch"):
        synthetic_tool_contact("SAEA-REAL", {}, lambda **_: None, {})
    with pytest.raises(NativeToolAuthorityError):
        synthetic_tool_contact("SAEA-WIRE-CHECK-rehearsal", {}, lambda **_: None, {})

def test_tool_turn_is_not_mistaken_for_second_planner_visit():
    responder = FourPathResponder(["a", "b", "c", "d"], ["person", "place_name"])
    def payload(index):
        return {"sample_id": "d", "history": [{"role": "control",
                "contact_id": f"native:planner:{index}:d"}]}
    assert responder(payload(0))["tool_calls"]
    assert responder(payload(1))["content"] == "REVISE"
    assert responder(payload(2))["content"] == "ACCEPT"

def test_four_paths_include_legal_empty_lookup_and_decline():
    responder = FourPathResponder(["a", "b", "c", "d"], ["person", "place_name"])
    def request(sample):
        return {"sample_id": sample, "history": [{"role": "control", "contact_id": f"native:planner:0:{sample}"}]}
    assert responder(request("a"))["content"] == "ACCEPT"
    call = responder(request("b"))["tool_calls"][0]
    assert json.loads(call["function"]["arguments"])["candidate_ids"] == ["synthetic_absent_slot_type"]
    with pytest.raises(ValueError):
        FourPathResponder(["one"], ["person", "place_name"])

