"""Generic bound-context integration for native wire projections.

All dispatch is synthetic and in process. No model, tokenizer, scorer, GPU,
or external service is contacted.
"""

from __future__ import annotations

import copy
import json
from types import MappingProxyType, SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.base import NATIVE_EVIDENCE_PROJECTIONS
from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model import transport as transport_module
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    project_native_framework_history,
)
from speech_aware_evidence_acquisition.core.model.transport import LlamaServerTransport
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.session import SessionError
from speech_aware_evidence_acquisition.core.tracing import (
    TraceBuffer,
    set_current_trace_buffer,
)
from test_native_framework_history import world as feature_framework_world
from test_raw_native_transport import (
    _payload as raw_payload,
    _raw_framework_payload,
    _transport as raw_transport,
)
from test_slot_binding_view import _target as slot_target
from test_slot_binding_view import context_world


BOUND_POLICY_ID = "test-bound-native-evidence-projection-v1"
NEW_POLICY_ID = "native-candidate-slot-view-v1"
BOUND_CONTEXT = MappingProxyType({"marker": "bound-slot-context"})


def _validate_context(context):
    if context is not BOUND_CONTEXT:
        raise ValueError("bound projection context differs")


def _bound_projector(*, payload, messages, local_results, projection_context):
    _validate_context(projection_context)
    rendered = copy.deepcopy(messages)
    local_indices = [index for index, _document in local_results]
    for index in local_indices:
        content = json.loads(rendered[index]["content"])
        content["bound_projection_marker"] = projection_context["marker"]
        rendered[index]["content"] = json.dumps(content, sort_keys=True)
    return rendered, {
        "schema": "test-bound-native-evidence-projection-v1",
        "policy_id": BOUND_POLICY_ID,
        "context_marker": projection_context["marker"],
        "local_message_indices": local_indices,
    }


def _bind_config(values, data_root):
    _bind_config.calls.append((values, data_root))
    if values.get("native_evidence_projection_params") != {"marker": "configured"}:
        raise ValueError("projection params differ")
    return BOUND_CONTEXT


_bind_config.calls = []
_bound_projector.bind_config = _bind_config
_bound_projector.validate_context = _validate_context


@pytest.fixture
def bound_policy(monkeypatch):
    monkeypatch.setitem(
        NATIVE_EVIDENCE_PROJECTIONS._entries,
        BOUND_POLICY_ID,
        _bound_projector,
    )
    _bind_config.calls.clear()
    return BOUND_POLICY_ID


def _transport(tmp_path, *, prompt_order, context=BOUND_CONTEXT, captured=None):
    transport = raw_transport(tmp_path, prompt_order=prompt_order, captured=captured)
    transport._native_evidence_projection = BOUND_POLICY_ID
    transport._native_evidence_projection_context = context
    return transport


def _feature_payload():
    payload, _messages, _texts, _framework = feature_framework_world()
    query = payload["speech_feature_parts"][0]
    payload.update(
        request_id="request-feature-bound-context",
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
    return payload


def _prepare_feature_transport(tmp_path, monkeypatch):
    transport = _transport(tmp_path, prompt_order="speech-query-prefix-v2")
    transport._feature_root = tmp_path
    transport._session = SimpleNamespace(
        model_files=(SimpleNamespace(path="model.gguf", sha256="d" * 64),)
    )
    monkeypatch.setattr(
        transport_module,
        "load_speech_feature_packets",
        lambda *_args, **_kwargs: [],
    )
    return transport


def _bound_tool_content(body):
    message = next(row for row in body["messages"] if row["role"] == "tool")
    return json.loads(message["content"])


def _slot_evidence(context):
    evidence_id, source_uri, content = slot_target(context)
    return {
        "evidence_id": evidence_id,
        "source_uri": source_uri,
        "content": content,
        "knowledge_role": "value",
    }


def _real_slot_raw_payload(tmp_path, context, context_payload):
    payload, _raw = raw_payload(tmp_path)
    payload.update(
        sample_id=context_payload["sample_id"],
        speech_ref="synthetic-carrier/" + context_payload["sample_id"],
        task_instruction=context_payload["task_instruction"],
        history=copy.deepcopy(context_payload["history"]),
        supplied_evidence=[_slot_evidence(context)],
    )
    return payload


def _real_slot_feature_payload(context, context_payload):
    payload = _feature_payload()
    payload.update(
        sample_id=context_payload["sample_id"],
        speech_ref="synthetic-carrier/" + context_payload["sample_id"],
        task_instruction=context_payload["task_instruction"],
        history=copy.deepcopy(context_payload["history"]),
        supplied_evidence=[_slot_evidence(context)],
    )
    return payload


def _derived_slot_text(body):
    parts = [
        part["text"]
        for message in body["messages"]
        if message.get("role") == "user" and isinstance(message.get("content"), list)
        for part in message["content"]
        if isinstance(part, dict)
        and part.get("type") == "text"
        and "derived knowledge view" in part.get("text", "")
    ]
    assert len(parts) == 1
    return parts[0]


def test_new_slot_view_policy_is_registered():
    assert NATIVE_EVIDENCE_PROJECTIONS.resolve(NEW_POLICY_ID) is not None


def test_factory_binds_context_from_the_full_composed_values(
    monkeypatch, tmp_path, bound_policy
):
    captured = []

    class CapturingTransport:
        def __init__(self, *args, **kwargs):
            captured.append((args, kwargs))

    monkeypatch.setattr(transport_module, "LlamaServerTransport", CapturingTransport)
    values = {
        "base_url": "http://127.0.0.1:1",
        "native_evidence_projection": bound_policy,
        "native_evidence_projection_params": {"marker": "configured"},
        "full_composed_value": {"must": "remain visible to binder"},
    }

    transport_module._llama_server_factory(
        values,
        tmp_path,
        session=object(),
        runtime_receipt={},
        runtime_root=tmp_path,
    )

    assert _bind_config.calls == [(values, tmp_path)]
    assert captured[0][1]["native_evidence_projection"] == bound_policy
    assert captured[0][1]["native_evidence_projection_context"] is BOUND_CONTEXT


def test_factory_binds_the_real_slot_view_context(monkeypatch, tmp_path):
    expected_context, config, _payload = context_world(tmp_path)
    captured = []

    class CapturingTransport:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(transport_module, "LlamaServerTransport", CapturingTransport)
    transport_module._llama_server_factory(
        {
            **config,
            "base_url": "http://127.0.0.1:1",
            "native_evidence_projection": NEW_POLICY_ID,
        },
        tmp_path,
        session=object(),
        runtime_receipt={},
        runtime_root=tmp_path,
    )

    context = captured[0]["native_evidence_projection_context"]
    assert context.policy_id == NEW_POLICY_ID
    assert context.context_sha256 == expected_context.context_sha256


def test_factory_normalizes_bind_config_value_error(tmp_path, bound_policy):
    with pytest.raises(SessionError, match="projection params differ"):
        transport_module._llama_server_factory(
            {
                "base_url": "http://127.0.0.1:1",
                "native_evidence_projection": bound_policy,
                "native_evidence_projection_params": {"marker": "wrong"},
            },
            tmp_path,
            session=object(),
            runtime_receipt={},
            runtime_root=tmp_path,
        )


@pytest.mark.parametrize(
    "values",
    [
        {"native_evidence_projection_params": {}},
        {
            "native_evidence_projection": "native-knowledge-reference-v1",
            "native_evidence_projection_params": {},
        },
        {
            "native_evidence_projection": "native-knowledge-reference-v1",
            "native_evidence_projection_params": [],
        },
    ],
)
def test_factory_rejects_orphan_or_malformed_projection_params(
    tmp_path, values
):
    with pytest.raises(SessionError, match="native_evidence_projection_params"):
        transport_module._llama_server_factory(
            {"base_url": "http://127.0.0.1:1", **values},
            tmp_path,
            session=object(),
            runtime_receipt={},
            runtime_root=tmp_path,
        )


def test_absent_projection_keeps_factory_context_none(monkeypatch, tmp_path):
    captured = []

    class CapturingTransport:
        def __init__(self, *args, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(transport_module, "LlamaServerTransport", CapturingTransport)
    transport_module._llama_server_factory(
        {"base_url": "http://127.0.0.1:1"},
        tmp_path,
        session=object(),
        runtime_receipt={},
        runtime_root=tmp_path,
    )

    assert len(captured) == 1
    assert captured[0]["native_evidence_projection"] is None
    assert captured[0]["native_evidence_projection_context"] is None


@pytest.mark.parametrize(
    ("policy", "context"),
    [
        (None, BOUND_CONTEXT),
        ("native-knowledge-reference-v1", BOUND_CONTEXT),
        (BOUND_POLICY_ID, None),
        (BOUND_POLICY_ID, object()),
    ],
)
def test_constructor_rejects_missing_or_unexpected_context_before_session(
    tmp_path, bound_policy, policy, context
):
    with pytest.raises(SessionError, match="context"):
        LlamaServerTransport(
            "http://127.0.0.1:1",
            tmp_path,
            object(),
            {},
            tmp_path,
            prompt_order="native-raw-speech-v1",
            native_evidence_projection=policy,
            native_evidence_projection_context=context,
        )


def test_framework_normalizes_validate_context_value_error(bound_policy):
    payload, messages, texts, _framework = feature_framework_world()

    with pytest.raises(FrozenCoreError, match="bound projection context differs"):
        project_native_framework_history(
            payload=payload,
            messages=messages,
            state_texts=texts,
            evidence_projection=bound_policy,
            projection_context=object(),
            receipt_sink=[].append,
        )


def test_framework_passes_context_only_to_a_context_bound_policy(bound_policy):
    payload, messages, texts, _framework = feature_framework_world()
    receipts = []

    rendered, descriptors = project_native_framework_history(
        payload=payload,
        messages=messages,
        state_texts=texts,
        evidence_projection=bound_policy,
        projection_context=BOUND_CONTEXT,
        receipt_sink=receipts.append,
    )

    assert descriptors == []
    assert receipts == [
        {
            "schema": "test-bound-native-evidence-projection-v1",
            "policy_id": BOUND_POLICY_ID,
            "context_marker": "bound-slot-context",
            "local_message_indices": [3],
        }
    ]
    assert json.loads(rendered[3]["content"])["bound_projection_marker"] == (
        "bound-slot-context"
    )


def test_framework_rejects_context_for_absent_or_unbound_policy(bound_policy):
    payload, messages, texts, _framework = feature_framework_world()
    for policy in (None, "native-knowledge-reference-v1"):
        with pytest.raises(FrozenCoreError, match="context"):
            project_native_framework_history(
                payload=payload,
                messages=messages,
                state_texts=texts,
                evidence_projection=policy,
                projection_context=BOUND_CONTEXT,
                receipt_sink=[].append,
            )


def test_framework_does_not_retry_projector_type_errors_without_context(monkeypatch):
    def broken_projector(*, payload, messages, local_results, projection_context):
        raise TypeError("projector implementation defect")

    broken_projector.validate_context = lambda context: None
    policy_id = "test-broken-bound-projection-v1"
    monkeypatch.setitem(NATIVE_EVIDENCE_PROJECTIONS._entries, policy_id, broken_projector)
    payload, messages, texts, _framework = feature_framework_world()

    with pytest.raises(TypeError, match="implementation defect"):
        project_native_framework_history(
            payload=payload,
            messages=messages,
            state_texts=texts,
            evidence_projection=policy_id,
            projection_context=BOUND_CONTEXT,
            receipt_sink=[].append,
        )


def test_raw_and_feature_render_paths_forward_the_same_bound_context(
    tmp_path, monkeypatch, bound_policy
):
    raw_payload, _raw, _framework = _raw_framework_payload(tmp_path)
    raw_payload["request_id"] = "request-raw-bound-context"
    raw_body, raw_receipt = _transport(
        tmp_path, prompt_order="native-raw-speech-v1"
    ).render_request_with_receipt(canonical_bytes(raw_payload))

    feature_payload = _feature_payload()
    feature_body, feature_receipt = _prepare_feature_transport(
        tmp_path, monkeypatch
    ).render_request_with_receipt(canonical_bytes(feature_payload))

    assert _bound_tool_content(raw_body)["bound_projection_marker"] == (
        "bound-slot-context"
    )
    assert _bound_tool_content(feature_body)["bound_projection_marker"] == (
        "bound-slot-context"
    )
    assert raw_receipt["context_marker"] == feature_receipt["context_marker"]


def test_bound_dispatch_posts_projected_body_and_traces_receipt_before_post(
    tmp_path, bound_policy
):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    payload["request_id"] = "request-bound-dispatch"
    request = canonical_bytes(payload)
    trace = TraceBuffer("SAEA-E-TEST-native-slot-view")
    posted = []
    seen_before_post = []
    transport = _transport(tmp_path, prompt_order="native-raw-speech-v1")
    expected_body, expected_receipt = transport.render_request_with_receipt(request)

    def post(_url, body):
        posted.append(json.loads(body))
        seen_before_post.append(list(trace.records))
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

    assert posted == [expected_body]
    assert len(trace.records) == 1
    assert seen_before_post == [trace.records]
    assert trace.records[0][2]["org_native_evidence_projection"] == expected_receipt
    assert "native_evidence_projection_context" not in json.dumps(posted[0])


def test_real_slot_view_projects_raw_and_feature_and_dispatches_exact_body(
    tmp_path, monkeypatch
):
    context, _config, context_payload = context_world(tmp_path)

    raw_request = canonical_bytes(
        _real_slot_raw_payload(tmp_path, context, context_payload)
    )
    raw = _transport(
        tmp_path,
        prompt_order="native-raw-speech-v1",
        context=context,
    )
    raw._native_evidence_projection = NEW_POLICY_ID
    raw_body, raw_receipt = raw.render_request_with_receipt(raw_request)

    feature_request = canonical_bytes(
        _real_slot_feature_payload(context, context_payload)
    )
    feature = _prepare_feature_transport(tmp_path, monkeypatch)
    feature._native_evidence_projection = NEW_POLICY_ID
    feature._native_evidence_projection_context = context
    feature_body, feature_receipt = feature.render_request_with_receipt(
        feature_request
    )

    for body, receipt in (
        (raw_body, raw_receipt),
        (feature_body, feature_receipt),
    ):
        projected_text = _derived_slot_text(body)
        assert "alpha_one: Alpha role." in projected_text
        assert "beta_two: Beta role." in projected_text
        assert "gamma_three: Gamma role." not in projected_text
        assert receipt["policy_id"] == NEW_POLICY_ID
        assert receipt["context_sha256"] == context.context_sha256
        assert receipt["projected_occurrences"] == 1
        assert "native_evidence_projection_context" not in json.dumps(body)

    trace = TraceBuffer("SAEA-E-TEST-real-native-slot-view")
    posted = []
    records_before_post = []

    def post(_url, body):
        posted.append(json.loads(body))
        records_before_post.append(list(trace.records))
        return json.dumps(
            {
                "choices": [{"message": {"content": "done"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        ).encode()

    raw._post = post
    set_current_trace_buffer(trace)
    try:
        raw(raw_request)
    finally:
        set_current_trace_buffer(None)

    assert posted == [raw_body]
    assert len(trace.records) == 1
    assert records_before_post == [trace.records]
    assert trace.records[0][2]["org_native_evidence_projection"] == raw_receipt
