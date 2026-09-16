"""Slot views accept both representations emitted by the shared renderer."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.tracing import (
    TraceBuffer,
    set_current_trace_buffer,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.phase_tools import (
    PHASE_KNOWLEDGE_TOOL,
    TASK_CONTRACT_TOOL,
    build_phase_tools,
)
from speech_aware_evidence_acquisition.rails.slot_binding_view import (
    SlotBindingViewError,
    project_slot_value,
    scope_for_payload,
)
from test_phase_native_tools import Custody
from test_native_slot_view_transport import (
    NEW_POLICY_ID,
    _prepare_feature_transport,
    _real_slot_feature_payload,
    _real_slot_raw_payload,
    _transport as projection_transport,
)
from test_slot_binding_view import _payload, _target, context_world


PLAIN = "canonical-plain-v1"
NAMED = "named-store-prefixed-v1"


class _NativeSolverProgram:
    program_id = "native-role-episode-v1"
    stop_rule = "native-role-episode"

    def phase_names(self):
        return ("solver", "final")


def _query(evidence_id: str) -> QueryState:
    return QueryState(
        query_id="query-shared-rendering",
        query_sample_id="sample-1",
        speech_packet_id="packet-shared-rendering",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
        retrieved_value_ids=(evidence_id,),
    ).validate()


def _render_target(context, representation: str) -> dict[str, object]:
    named = representation == NAMED
    tool_id = PHASE_KNOWLEDGE_TOOL if named else TASK_CONTRACT_TOOL
    spec = {
        "mode": "native-tools",
        "allowed_tools": [tool_id],
        "knowledge_views": ["text"],
        "source_authority_role": "solver",
    }
    if named:
        spec["knowledge_store_ids"] = ["slot-contracts"]
    dispatcher = build_phase_tools(
        {"phase_tools": {"solver": spec}},
        _NativeSolverProgram(),
        snapshot=context.knowledge_binding.composite_snapshot,
        knowledge_stores=context.knowledge_binding if named else None,
        # Rendering does not invoke the router. A callable is still required by
        # the named-store dispatcher construction contract.
        supply_for_store=(lambda *_args, **_kwargs: None) if named else None,
        tool_contact=Custody(),
    )
    evidence_id, _uri, _content = _target(context)
    blocks = dispatcher.render_values(
        context.knowledge_binding.composite_snapshot,
        _query(evidence_id),
        (),
    )
    assert len(blocks) == 1
    assert dispatcher.knowledge_stores is (
        context.knowledge_binding if named else None
    )
    return blocks[0]


def test_task_contract_only_renderer_projects_canonical_plain_body(tmp_path):
    context, _config, payload = context_world(tmp_path)
    block = _render_target(context, PLAIN)
    evidence_id, source_uri, named_content = _target(context)
    source_value = next(
        value
        for value in context.knowledge_binding.composite_snapshot.values
        if value.value_id == evidence_id
    )
    assert block == {
        "type": "text",
        "text": source_value.content,
        "evidence_id": evidence_id,
        "source_uri": source_uri,
        "knowledge_role": "value",
    }
    assert block["text"] != named_content

    projected, receipt = project_slot_value(
        context,
        evidence_id=evidence_id,
        source_uri=source_uri,
        content=block["text"],
        scope=scope_for_payload(payload, context),
    )

    assert receipt["source_representation"] == PLAIN
    assert projected.startswith("Slot shared.\n")
    assert "[knowledge store=" not in projected
    assert "alpha_one: Alpha role." in projected
    assert "beta_two: Beta role." in projected
    assert "gamma_three: Gamma role." not in projected


def test_named_store_renderer_projects_and_preserves_prefix(tmp_path):
    context, _config, payload = context_world(tmp_path)
    block = _render_target(context, NAMED)
    evidence_id, source_uri, named_content = _target(context)
    assert block["text"] == named_content

    projected, receipt = project_slot_value(
        context,
        evidence_id=evidence_id,
        source_uri=source_uri,
        content=block["text"],
        scope=scope_for_payload(payload, context),
    )

    assert receipt["source_representation"] == NAMED
    assert projected.startswith("[knowledge store=slot-contracts")
    assert "alpha_one: Alpha role." in projected
    assert "beta_two: Beta role." in projected
    assert "gamma_three: Gamma role." not in projected


@pytest.mark.parametrize("representation", [PLAIN, NAMED])
@pytest.mark.parametrize("tamper", ["source-uri", "content"])
def test_shared_renderer_sources_are_exactly_bound(
    tmp_path, representation, tamper
):
    context, _config, payload = context_world(tmp_path)
    block = _render_target(context, representation)
    evidence_id, source_uri, _named_content = _target(context)
    arguments = {
        "evidence_id": evidence_id,
        "source_uri": source_uri,
        "content": block["text"],
        "scope": scope_for_payload(payload, context),
    }
    if tamper == "source-uri":
        arguments["source_uri"] += "-tampered"
    else:
        arguments["content"] += "\nTampered."

    with pytest.raises(SlotBindingViewError, match="differs"):
        project_slot_value(context, **arguments)


@pytest.mark.parametrize("representation", [PLAIN, NAMED])
def test_fallback_retains_the_original_shared_renderer_representation(
    tmp_path, representation
):
    context, config, _payload_with_candidates = context_world(tmp_path)
    block = _render_target(context, representation)
    evidence_id, source_uri, _named_content = _target(context)
    fallback = scope_for_payload(_payload(config), context)
    assert fallback["fallback_reason"] == "missing-perception-candidates"

    retained, receipt = project_slot_value(
        context,
        evidence_id=evidence_id,
        source_uri=source_uri,
        content=block["text"],
        scope=fallback,
    )

    assert retained == block["text"]
    assert receipt["source_representation"] == representation
    assert receipt["disposition"] == "full-body-fallback"


def _plain_transport_world(tmp_path, monkeypatch, route):
    context, _config, context_payload = context_world(tmp_path)
    block = _render_target(context, PLAIN)
    evidence = {
        "evidence_id": block["evidence_id"],
        "source_uri": block["source_uri"],
        "content": block["text"],
        "knowledge_role": block["knowledge_role"],
    }
    if route == "raw":
        payload = _real_slot_raw_payload(tmp_path, context, context_payload)
        transport = projection_transport(
            tmp_path,
            prompt_order="native-raw-speech-v1",
            context=context,
        )
    else:
        payload = _real_slot_feature_payload(context, context_payload)
        transport = _prepare_feature_transport(tmp_path, monkeypatch)
        transport._native_evidence_projection_context = context
    payload["supplied_evidence"] = [evidence]
    transport._native_evidence_projection = NEW_POLICY_ID
    return context, evidence, transport, canonical_bytes(payload)


@pytest.mark.parametrize("route", ["raw", "feature"])
def test_dispatcher_plain_body_is_the_exact_fake_post_body(
    tmp_path, monkeypatch, route
):
    context, _evidence, transport, request = _plain_transport_world(
        tmp_path, monkeypatch, route
    )
    expected_body, expected_receipt = transport.render_request_with_receipt(request)
    posted = []
    records_before_post = []
    trace = TraceBuffer(f"SAEA-E-TEST-slot-shared-rendering-{route}")

    def post(_url, body):
        import json

        posted.append(json.loads(body))
        records_before_post.append(list(trace.records))
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
    assert records_before_post == [trace.records]
    assert len(trace.records) == 1
    assert trace.records[0][2]["org_native_evidence_projection"] == expected_receipt
    assert expected_receipt["context_sha256"] == context.context_sha256
    projected = [
        placement
        for placement in expected_receipt["placements"]
        if placement["disposition"] == "projected"
    ]
    assert len(projected) == 1
    assert projected[0]["view_audit"]["source_representation"] == PLAIN


@pytest.mark.parametrize("route", ["raw", "feature"])
def test_projection_off_preserves_the_plain_source_in_the_old_request_body(
    tmp_path, monkeypatch, route
):
    _context, evidence, transport, request = _plain_transport_world(
        tmp_path, monkeypatch, route
    )
    transport._native_evidence_projection = None
    transport._native_evidence_projection_context = None

    body, receipt = transport.render_request_with_receipt(request)

    assert receipt is None
    assert body == transport.render_request(request)
    expected = "[evidence {}] {}".format(
        evidence["evidence_id"], evidence["content"]
    )
    visible = [
        part["text"]
        for message in body["messages"]
        if isinstance(message.get("content"), list)
        for part in message["content"]
        if isinstance(part, dict) and part.get("type") == "text"
    ]
    assert visible.count(expected) == 1


@pytest.mark.parametrize("tamper", ["altered-prefix", "repeated-prefix"])
def test_named_store_prefix_tampering_is_rejected(tmp_path, tamper):
    context, _config, payload = context_world(tmp_path)
    block = _render_target(context, NAMED)
    evidence_id, source_uri, _named_content = _target(context)
    prefix = block["text"].splitlines()[0]
    if tamper == "altered-prefix":
        changed = block["text"].replace(
            "store=slot-contracts", "store=another-store", 1
        )
    else:
        changed = prefix + "\n" + block["text"]

    with pytest.raises(SlotBindingViewError, match="full content differs"):
        project_slot_value(
            context,
            evidence_id=evidence_id,
            source_uri=source_uri,
            content=changed,
            scope=scope_for_payload(payload, context),
        )
