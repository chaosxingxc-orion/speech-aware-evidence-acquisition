"""Prove optional node instructions precede speech without changing custody."""
import copy
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model import transport as module
from speech_aware_evidence_acquisition.core.model.native_framework_history import project_native_framework_history
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.session import SessionError
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer, set_current_trace_buffer
from test_native_framework_history import world
from test_native_evidence_projection_transport import (
    _feature_payload, _prepare_feature_transport, _packet_identities, _tool_call_ids,
)
from test_raw_native_transport import _transport, _raw_framework_payload, _payload


PLACEMENT = "before-speech-v1"


def test_projection_moves_only_the_declared_query_and_keeps_source_unchanged():
    payload, messages, texts, framework = world()
    original = copy.deepcopy((payload, messages, texts))
    old, old_packets = project_native_framework_history(payload=payload, messages=messages, state_texts=texts)
    receipts = []
    new, packets = project_native_framework_history(
        payload=payload, messages=messages, state_texts=texts,
        role_query_placement=PLACEMENT, layout_receipt_sink=receipts.append,
    )
    expected = copy.deepcopy(old)
    query = expected[1]["content"].pop()
    expected[1]["content"].insert(0, query)
    assert new == expected
    assert packets == old_packets
    assert (payload, messages, texts) == original
    assert len(receipts) == 1
    assert receipts[0]["role_query_sha256"] == hashlib.sha256(framework[1]["content"].encode()).hexdigest()
    assert receipts[0]["source_control_sha256"] == payload["history"][-1]["content_sha256"]


def test_raw_render_and_send_share_exact_layout_and_trace(tmp_path):
    payload, _raw, framework = _raw_framework_payload(tmp_path)
    request = canonical_bytes(payload)
    posted = []
    transport = _transport(tmp_path, captured=posted)
    original = transport.render_request(request)
    transport._native_role_query_placement = PLACEMENT
    body, receipt = transport.render_request_with_receipt(request)
    assert body["messages"][1]["content"][0] == {"type":"text", "text":framework[1]["content"]}
    assert body["messages"][2:] == original["messages"][2:]
    assert {k:v for k,v in body.items() if k != "messages"} == {k:v for k,v in original.items() if k != "messages"}
    assert receipt["role_query_layout"]["placement"] == PLACEMENT
    assert receipt["rendered_body_canonical_sha256"] == hashlib.sha256(canonical_bytes(body)).hexdigest()
    assert posted == []
    trace = TraceBuffer("layout-proof")
    set_current_trace_buffer(trace)
    try:
        transport(request)
    finally:
        set_current_trace_buffer(None)
    assert posted == [body]
    encoded = str(trace.records)
    assert "org_native_role_query_layout" in encoded
    assert "org_native_evidence_projection" not in encoded


def test_feature_layout_composes_with_bound_evidence_projection(tmp_path, monkeypatch):
    transport, loaded = _prepare_feature_transport(tmp_path, monkeypatch)
    payload = _feature_payload()
    request = canonical_bytes(payload)
    before, original_receipt = transport.render_request_with_receipt(request)
    transport._native_role_query_placement = PLACEMENT
    after, receipt = transport.render_request_with_receipt(request)
    assert _packet_identities(after) == _packet_identities(before)
    assert _tool_call_ids(after) == _tool_call_ids(before)
    assert after["messages"][0] == before["messages"][0]
    tool = next(m for m in after["messages"] if m["role"] == "tool")
    ref = json.loads(tool["content"])["evidence"][0]["reference"]
    assert ref["message_index"] == 1
    assert ref["content_part_index"] > 0
    visible = after["messages"][ref["message_index"]]["content"][ref["content_part_index"]]
    source = payload["supplied_evidence"][0]
    assert visible == {"type": "text", "text": f"[evidence {source['evidence_id']}] {source['content']}"}
    assert ref["content_sha256"] == hashlib.sha256(source["content"].encode()).hexdigest()
    assert receipt["policy_id"] == original_receipt["policy_id"]
    assert receipt["role_query_layout"]["placement"] == PLACEMENT
    assert len(loaded) == 2


def test_disabled_layout_preserves_exact_legacy_body_and_receipt(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    transport = _transport(tmp_path)
    old = transport.render_request_with_receipt(canonical_bytes(payload))
    transport._native_role_query_placement = None
    assert transport.render_request_with_receipt(canonical_bytes(payload)) == old


@pytest.mark.parametrize("placement", [True, 1, [], {}, "", "unknown", "after-history-v1"])
def test_constructor_refuses_invalid_option_before_touching_session(tmp_path, placement):
    with pytest.raises(SessionError, match="native_role_query_placement"):
        module.LlamaServerTransport("http://127.0.0.1:1", tmp_path, object(), {}, tmp_path,
            prompt_order="native-raw-speech-v1", native_role_query_placement=placement)


def test_constructor_refuses_non_native_layout_before_session(tmp_path):
    with pytest.raises(SessionError, match="prompt_order"):
        module.LlamaServerTransport("http://127.0.0.1:1", tmp_path, object(), {}, tmp_path,
            native_role_query_placement=PLACEMENT)


def test_missing_framework_or_receipt_sink_is_rejected(tmp_path):
    payload, _raw = _payload(tmp_path)
    transport = _transport(tmp_path)
    transport._native_role_query_placement = PLACEMENT
    with pytest.raises(FrozenCoreError, match="framework"):
        transport.render_request(canonical_bytes(payload))
    payload, messages, texts, _framework = world()
    with pytest.raises(FrozenCoreError, match="receipt sink"):
        project_native_framework_history(payload=payload, messages=messages, state_texts=texts,
                                         role_query_placement=PLACEMENT)


def test_factory_passes_the_declared_option_without_coercion(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(module, "LlamaServerTransport", lambda *a, **kw: seen.append(kw))
    common = dict(session=object(), runtime_receipt={}, runtime_root=tmp_path)
    module._llama_server_factory({"base_url":"http://127.0.0.1:1"}, tmp_path, **common)
    module._llama_server_factory({"base_url":"http://127.0.0.1:1", "native_role_query_placement":PLACEMENT}, tmp_path, **common)
    assert seen[0]["native_role_query_placement"] is None
    assert seen[1]["native_role_query_placement"] == PLACEMENT


def test_enabled_layout_refuses_dispatch_without_trace_before_post(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    posted = []
    transport = _transport(tmp_path, captured=posted)
    transport._native_role_query_placement = PLACEMENT
    set_current_trace_buffer(None)
    with pytest.raises(FrozenCoreError, match="trace buffer"):
        transport(canonical_bytes(payload))
    assert posted == []


def test_layout_requires_request_identity_for_auditable_provenance(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    payload.pop("request_id")
    transport = _transport(tmp_path)
    transport._native_role_query_placement = PLACEMENT
    with pytest.raises(FrozenCoreError, match="request_id"):
        transport.render_request(canonical_bytes(payload))


def test_projection_refuses_unknown_layout_without_mutating_source():
    payload, messages, texts, _framework = world()
    original = copy.deepcopy((payload, messages, texts))
    with pytest.raises(FrozenCoreError, match="unknown role query placement"):
        project_native_framework_history(
            payload=payload, messages=messages, state_texts=texts,
            role_query_placement="invented-layout", layout_receipt_sink=lambda r: None,
        )
    assert (payload, messages, texts) == original
