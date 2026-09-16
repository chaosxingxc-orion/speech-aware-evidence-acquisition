"""Transport integration for the bounded native evidence projection.

Every test is synthetic. The POST callable is in-process and the packet
loader is replaced with a validating no-op, so this file cannot contact a
model, tokenizer, scorer, or external service.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.base import NATIVE_EVIDENCE_PROJECTIONS
from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_evidence_projection import POLICY_ID
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    native_tool_result_message,
)
from speech_aware_evidence_acquisition.core.model import transport as transport_module
from speech_aware_evidence_acquisition.core.model.transport import LlamaServerTransport
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.session import SessionError
from speech_aware_evidence_acquisition.core.tracing import (
    TraceBuffer,
    get_current_trace_buffer,
    set_current_trace_buffer,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_native_framework_history import world as feature_framework_world
from test_raw_native_transport import (
    _payload as raw_payload,
    _raw_framework_payload,
    _transport as raw_transport,
)


def _projection_transport(tmp_path, *, prompt_order: str, captured=None):
    transport = raw_transport(tmp_path, prompt_order=prompt_order, captured=captured)
    transport._native_evidence_projection = POLICY_ID
    return transport


def _feature_payload():
    payload, _messages, _texts, _framework = feature_framework_world()
    query = payload["speech_feature_parts"][0]
    payload.update(
        request_id="request-feature-1",
        carrier_lock_key="synthetic-carrier",
        speech_ref="synthetic-carrier/" + payload["sample_id"],
        media_relpath="unused/feature-query.wav",
        audio_seconds=1.0,
        sample_rate_hz=16000,
        query_source="speech_features",
        mmproj_loaded=False,
        key_representation_id="synthetic-key-v1",
        matcher_policy_id="synthetic-matcher-v1",
        speech_packet_sha256=query["sha256"],
    )
    _mark_local_result_as_visible_knowledge(payload)
    return payload


def _mark_local_result_as_visible_knowledge(payload):
    """Keep the fixture's custody intact while making its result knowledge."""

    state = next(
        item for item in payload["history"] if item.get("state_kind") == "tool-result"
    )
    document = json.loads(state["content"])
    evidence_ids = [
        block["evidence_id"]
        for block in document["native_result_content"]
        if block.get("type") == "text"
    ]
    for block in document["native_result_content"]:
        if block.get("type") != "text":
            continue
        block["source_uri"] = (
            f"knowledge-snapshot://{document['snapshot_sha256']}/"
            f"{block['evidence_id']}"
        )
        block["knowledge_role"] = "value"
        matching = next(
            (
                item
                for item in payload["supplied_evidence"]
                if item["evidence_id"] == block["evidence_id"]
            ),
            None,
        )
        if matching is None:
            matching = {
                "evidence_id": block["evidence_id"],
                "content": block["text"],
                "source_uri": block["source_uri"],
            }
            payload["supplied_evidence"].append(matching)
        else:
            matching["source_uri"] = block["source_uri"]
        matching["knowledge_role"] = "value"
    document["result"] = {
        **document["result"],
        "knowledge_view": "text",
        "selected_value_ids": evidence_ids,
    }
    document["result_sha256"] = content_hash(document["result"])
    document["native_result_content_sha256"] = content_hash(
        {"blocks": document["native_result_content"]}
    )
    state["content"] = json.dumps(document, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()

    control = payload["history"][-1]
    contract = json.loads(control["content"])
    contract["messages"][-1] = native_tool_result_message(document)
    control["content"] = json.dumps(
        contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    control["content_sha256"] = hashlib.sha256(control["content"].encode()).hexdigest()


def _prepare_feature_transport(tmp_path, monkeypatch):
    transport = _projection_transport(tmp_path, prompt_order="speech-query-prefix-v2")
    transport._feature_root = tmp_path
    transport._session = SimpleNamespace(
        model_files=(SimpleNamespace(path="model.gguf", sha256="d" * 64),)
    )
    loaded = []

    def validate_packets(feature_root, descriptors, **kwargs):
        loaded.append((feature_root, descriptors, kwargs))
        return []

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.model.transport.load_speech_feature_packets",
        validate_packets,
    )
    return transport, loaded


def _tool_message(body):
    return next(message for message in body["messages"] if message["role"] == "tool")


def _tool_call_ids(body):
    return [
        call["id"]
        for message in body["messages"]
        for call in message.get("tool_calls", [])
    ]


def _packet_identities(body):
    return [
        (part["speech_features"]["packet_id"], part["speech_features"]["sha256"])
        for message in body["messages"]
        if isinstance(message.get("content"), list)
        for part in message["content"]
        if part.get("type") == "input_speech_features"
    ]


def test_registry_resolves_the_one_native_projection():
    assert NATIVE_EVIDENCE_PROJECTIONS.resolve(POLICY_ID) is not None


@pytest.mark.parametrize("policy", [False, 7, [], {}])
def test_constructor_rejects_non_string_projection_policy_before_session(policy):
    with pytest.raises(SessionError, match="native_evidence_projection"):
        LlamaServerTransport(
            "http://127.0.0.1:1",
            Path("."),
            object(),
            {},
            Path("."),
            prompt_order="native-raw-speech-v1",
            native_evidence_projection=policy,
        )


def test_constructor_rejects_unknown_projection_policy_before_session(tmp_path):
    with pytest.raises(SessionError, match="unknown native evidence projection"):
        LlamaServerTransport(
            "http://127.0.0.1:1",
            tmp_path,
            object(),
            {},
            tmp_path,
            prompt_order="native-raw-speech-v1",
            native_evidence_projection="unknown-projection",
        )


def test_constructor_rejects_projection_for_non_native_prompt_order(tmp_path):
    with pytest.raises(SessionError, match="prompt_order"):
        LlamaServerTransport(
            "http://127.0.0.1:1",
            tmp_path,
            object(),
            {},
            tmp_path,
            prompt_order="system-instruction-v1",
            native_evidence_projection=POLICY_ID,
        )


def test_absent_projection_preserves_body_bytes_and_returns_no_receipt(tmp_path):
    payload, _raw = raw_payload(tmp_path)
    request = canonical_bytes(payload)
    transport = raw_transport(tmp_path)

    historical_body = transport.render_request(request)
    body, receipt = transport.render_request_with_receipt(request)

    assert canonical_bytes(body) == canonical_bytes(historical_body)
    assert receipt is None


def test_raw_path_projects_the_real_body_and_binds_receipt_to_its_source(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    _mark_local_result_as_visible_knowledge(payload)
    payload["request_id"] = "request-raw-projection"
    request = canonical_bytes(payload)
    baseline = raw_transport(tmp_path).render_request(request)

    body, receipt = _projection_transport(
        tmp_path, prompt_order="native-raw-speech-v1"
    ).render_request_with_receipt(request)

    assert receipt is not None
    assert canonical_bytes(_tool_message(body)) != canonical_bytes(_tool_message(baseline))
    projected_evidence = json.loads(_tool_message(body)["content"])["evidence"][0]
    baseline_evidence = json.loads(_tool_message(baseline)["content"])["evidence"][0]
    assert "content" not in projected_evidence
    assert projected_evidence["reference"]["message_index"] == 1
    assert baseline_evidence["content"]
    assert receipt["referenced_blocks"] == 1
    assert receipt["input_request_id"] == payload["request_id"]
    assert receipt["input_request_bytes_sha256"] == hashlib.sha256(request).hexdigest()
    assert receipt["rendered_body_canonical_sha256"] == hashlib.sha256(
        canonical_bytes(body)
    ).hexdigest()
    assert _tool_call_ids(body) == _tool_call_ids(baseline)
    assert body["temperature"] == baseline["temperature"]
    assert body["tool_choice"] == baseline["tool_choice"]
    assert body["parallel_tool_calls"] == baseline["parallel_tool_calls"]


def test_feature_path_projects_body_without_changing_packets_calls_or_decoding(
    tmp_path, monkeypatch
):
    payload = _feature_payload()
    request = canonical_bytes(payload)
    projected, loaded = _prepare_feature_transport(tmp_path, monkeypatch)
    baseline = raw_transport(tmp_path, prompt_order="speech-query-prefix-v2")
    baseline._feature_root = tmp_path
    baseline._session = projected._session

    baseline_body = baseline.render_request(request)
    body, receipt = projected.render_request_with_receipt(request)

    assert receipt is not None
    assert canonical_bytes(_tool_message(body)) != canonical_bytes(
        _tool_message(baseline_body)
    )
    projected_evidence = json.loads(_tool_message(body)["content"])["evidence"][0]
    baseline_evidence = json.loads(_tool_message(baseline_body)["content"])["evidence"][0]
    assert "content" not in projected_evidence
    assert projected_evidence["reference"]["message_index"] == 1
    assert baseline_evidence["content"]
    assert receipt["referenced_blocks"] == 1
    assert _packet_identities(body) == _packet_identities(baseline_body)
    assert _tool_call_ids(body) == _tool_call_ids(baseline_body)
    assert {key: value for key, value in body.items() if key != "messages"} == {
        key: value for key, value in baseline_body.items() if key != "messages"
    }
    assert receipt["input_request_bytes_sha256"] == hashlib.sha256(request).hexdigest()
    assert receipt["rendered_body_canonical_sha256"] == hashlib.sha256(
        canonical_bytes(body)
    ).hexdigest()
    assert len(loaded) == 2


def test_prepare_render_never_posts(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    _mark_local_result_as_visible_knowledge(payload)
    payload["request_id"] = "request-prepare-only"
    posted = []
    transport = _projection_transport(
        tmp_path, prompt_order="native-raw-speech-v1", captured=posted
    )

    body, receipt = transport.render_request_with_receipt(canonical_bytes(payload))

    assert body and receipt
    assert posted == []


def test_factory_forwards_absent_and_opt_in_projection_config(monkeypatch, tmp_path):
    captured = []

    class CapturingTransport:
        def __init__(self, *args, **kwargs):
            captured.append((args, kwargs))

    monkeypatch.setattr(transport_module, "LlamaServerTransport", CapturingTransport)
    common = {"base_url": "http://127.0.0.1:1"}
    factory_kwargs = {
        "session": object(),
        "runtime_receipt": {},
        "runtime_root": tmp_path,
    }

    transport_module._llama_server_factory(common, tmp_path, **factory_kwargs)
    transport_module._llama_server_factory(
        {**common, "native_evidence_projection": POLICY_ID},
        tmp_path,
        **factory_kwargs,
    )

    assert captured[0][1]["native_evidence_projection"] is None
    assert captured[1][1]["native_evidence_projection"] == POLICY_ID


def test_dispatch_emits_exactly_one_org_receipt_before_post(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    _mark_local_result_as_visible_knowledge(payload)
    payload["request_id"] = "request-dispatch-projection"
    trace = TraceBuffer("SAEA-E-TEST-native-evidence-projection")
    seen_before_post = []
    posted = []
    transport = _projection_transport(tmp_path, prompt_order="native-raw-speech-v1")
    request = canonical_bytes(payload)
    expected_body, expected_receipt = transport.render_request_with_receipt(request)

    def post(_url, body_bytes):
        seen_before_post.append(list(trace.records))
        posted.append(json.loads(body_bytes))
        return json.dumps(
            {
                "choices": [{"message": {"content": "done"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        ).encode()

    transport._post = post
    set_current_trace_buffer(trace)
    try:
        transport(request)
    finally:
        set_current_trace_buffer(None)

    assert get_current_trace_buffer() is None
    assert len(trace.records) == 1
    channel, record_id, record = trace.records[0]
    assert channel == "ORG"
    assert record_id == payload["request_id"] + "/native-evidence-projection"
    assert record == {
        "org_native_evidence_projection": record["org_native_evidence_projection"]
    }
    assert record["org_native_evidence_projection"] == expected_receipt
    assert seen_before_post == [trace.records]
    assert posted == [expected_body]
    assert "org_native_evidence_projection" not in json.dumps(posted[0])


def test_dispatch_without_active_trace_refuses_before_post(tmp_path):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    _mark_local_result_as_visible_knowledge(payload)
    payload["request_id"] = "request-missing-trace"
    posted = []
    transport = _projection_transport(
        tmp_path, prompt_order="native-raw-speech-v1", captured=posted
    )
    set_current_trace_buffer(None)

    with pytest.raises(FrozenCoreError, match="trace buffer"):
        transport(canonical_bytes(payload))

    assert posted == []
