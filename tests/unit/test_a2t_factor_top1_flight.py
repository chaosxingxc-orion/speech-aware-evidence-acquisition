"""Flight-boundary tests for the semantic-factor top-1 AgentLoop."""

from __future__ import annotations

import hashlib
import json

from speech_aware_evidence_acquisition.rails.knowledge import (
    QueryState,
    assert_agent_step_binding,
    assert_knowledge_use_binding,
)
from speech_aware_evidence_acquisition.rails.probes import a2t_factor_top1_flight as flight
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext


REGISTRY = (
    {
        "tool_id": "11",
        "domain": "smart_home",
        "category": "lighting",
        "tool_name": "setLightBrightness",
        "signature": "setLightBrightness(deviceId: String, brightness: Int)",
        "description": "Set the brightness of a light in a room.",
        "argument_defaults": "deviceId=lamp; brightness=50",
        "argument_constraints": "brightness: [0-100]",
    },
    {
        "tool_id": "20",
        "domain": "weather",
        "category": "forecast",
        "tool_name": "getWeatherForecast",
        "signature": "getWeatherForecast(location: String, days: Int?)",
        "description": "Get a weather forecast for a location.",
        "argument_defaults": "days=1",
        "argument_constraints": "days: [1-10]",
    },
)


def _factor_response() -> str:
    return json.dumps(
        {
            "task_action": "set",
            "task_object": "room light brightness",
            "qualifiers": ["kitchen"],
            "argument_hints": [
                {"role": "brightness", "value_hint": "eighty percent"}
            ],
            "uncertainty": "low",
        }
    )


def _context(snapshot: object, query_state: QueryState) -> AgentRuntimeContext:
    return AgentRuntimeContext(
        sample_id=query_state.query_sample_id,
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(item.facet_id for item in snapshot.facets),
        catalog_value_ids=tuple(item.value_id for item in snapshot.values),
        query_state=query_state,
        task_contract="Select tools from the frozen registry.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=query_state.loop_step,
    )


def _query_state() -> QueryState:
    return QueryState(
        query_id="query:tier1:000001",
        query_sample_id="tier1:000001",
        speech_packet_id="packet:tier1:000001",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()


def test_registry_snapshot_is_external_governed_and_values_stripped() -> None:
    snapshot = flight.build_registry_snapshot(
        REGISTRY,
        registry_sha256="c" * 64,
    )
    snapshot.validate()
    assert snapshot.source_partition_role == "external-governed"
    assert len(snapshot.facets) == len(snapshot.values) == 2
    assert snapshot.source_split_identity_hash == hashlib.sha256(
        (snapshot.source_sample_ids[0] + "\n").encode()
    ).hexdigest()
    assert all("argument_defaults" not in value.content for value in snapshot.values)
    assert [value.task_target for value in snapshot.values] == [
        "setLightBrightness",
        "getWeatherForecast",
    ]


def test_initial_factor_contact_freezes_bounded_postvalidated_json_instruction() -> None:
    snapshot = flight.build_registry_snapshot(REGISTRY, registry_sha256="c" * 64)
    controller = flight.FactorTop1Controller(REGISTRY, snapshot)
    contact = controller.initial_contact(_context(snapshot, _query_state()))
    assert contact.contact_id == flight.FACTOR_CONTACT_ID
    assert contact.decoding_params == {"max_tokens": 256}
    schema = flight.factor_response_format()["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == flight.FACTOR_FIELDS
    serialized = json.dumps(schema)
    assert "tool_name" not in serialized
    assert "tool_calls" not in serialized
    assert "Do not name" in contact.instruction
    assert "raw JSON object" in contact.instruction


def test_valid_factor_acquires_exactly_one_row_and_one_org_state() -> None:
    snapshot = flight.build_registry_snapshot(REGISTRY, registry_sha256="c" * 64)
    controller = flight.FactorTop1Controller(REGISTRY, snapshot)
    initial = _query_state()
    context = _context(snapshot, initial)
    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, _factor_response())
    assert advance.transition.action_kind == "acquire"
    assert len(advance.transition.new_value_ids) == 1
    assert len(advance.transition.new_facet_ids) == 1
    assert len(advance.new_agent_states) == 1
    assert advance.next_query_state is not None
    assert len(advance.next_query_state.retrieved_value_ids) == 1
    assert len(advance.next_query_state.visible_facet_ids) == 1
    assert len(advance.next_query_state.agent_state_ids) == 1
    assert advance.rank_result is not None
    assert len(advance.rank_result.candidates) == 1
    assert advance.fusion_decision is not None
    assert len(advance.fusion_decision.selected_value_ids) == 1
    assert_knowledge_use_binding(
        snapshot=snapshot,
        query_state=initial,
        rank_result=advance.rank_result,
        fusion_decision=advance.fusion_decision,
        snapshot_sha256=snapshot.content_hash(),
    )
    assert_agent_step_binding(
        snapshot=snapshot,
        prior_query_state=initial,
        next_query_state=advance.next_query_state,
        transition=advance.transition,
        snapshot_sha256=snapshot.content_hash(),
    )
    assert advance.next_contact is not None
    assert advance.next_contact.contact_id == flight.FINAL_CONTACT_ID
    assert "setLightBrightness" not in advance.next_contact.instruction
    state = advance.new_agent_states[0]
    assert state.content == json.dumps(
        json.loads(_factor_response()), ensure_ascii=True, separators=(",", ":")
    )
    assert state.cited_value_ids == ()


def test_invalid_factor_organizes_fixed_sentinel_without_supply() -> None:
    snapshot = flight.build_registry_snapshot(REGISTRY, registry_sha256="c" * 64)
    controller = flight.FactorTop1Controller(REGISTRY, snapshot)
    initial = _query_state()
    context = _context(snapshot, initial)
    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, "not-json")
    assert advance.transition.action_kind == "organize"
    assert advance.transition.new_value_ids == ()
    assert advance.transition.new_facet_ids == ()
    assert advance.rank_result is None
    assert advance.fusion_decision is None
    assert advance.next_query_state is not None
    assert advance.next_query_state.retrieved_value_ids == ()
    assert advance.new_agent_states[0].content == flight.INVALID_FACTOR_SENTINEL
    assert advance.next_contact is not None
    assert advance.next_contact.contact_id == flight.FINAL_CONTACT_ID


def test_final_contact_stops_with_frozen_core_answer_authority() -> None:
    snapshot = flight.build_registry_snapshot(REGISTRY, registry_sha256="c" * 64)
    controller = flight.FactorTop1Controller(REGISTRY, snapshot)
    initial = _query_state()
    context = _context(snapshot, initial)
    first = controller.initial_contact(context)
    first_advance = controller.advance(context, first, _factor_response())
    assert first_advance.next_query_state is not None
    next_context = AgentRuntimeContext(
        sample_id=initial.query_sample_id,
        knowledge_snapshot_sha256=snapshot.content_hash(),
        catalog_facet_ids=tuple(item.facet_id for item in snapshot.facets),
        catalog_value_ids=tuple(item.value_id for item in snapshot.values),
        query_state=first_advance.next_query_state,
        task_contract=context.task_contract,
        agent_states=first_advance.new_agent_states,
        prior_response_sha256s=(hashlib.sha256(_factor_response().encode()).hexdigest(),),
        contact_index=1,
    )
    final_contact = first_advance.next_contact
    assert final_contact is not None
    final = controller.advance(next_context, final_contact, "[]")
    assert final.transition.action_kind == "stop"
    assert final.next_query_state is None
    assert final.next_contact is None
    assert final.final_response_contact_id == flight.FINAL_CONTACT_ID


def test_controller_rejects_wrong_contact_sequence() -> None:
    snapshot = flight.build_registry_snapshot(REGISTRY, registry_sha256="c" * 64)
    controller = flight.FactorTop1Controller(REGISTRY, snapshot)
    context = _context(snapshot, _query_state())
    contact = controller.initial_contact(context)
    wrong = replace_contact_id(contact, flight.FINAL_CONTACT_ID)
    try:
        controller.advance(context, wrong, _factor_response())
    except flight.A2TFactorTop1FlightError as error:
        assert "contact" in str(error)
    else:
        raise AssertionError("wrong contact sequence was accepted")


def replace_contact_id(contact: object, contact_id: str) -> object:
    from dataclasses import replace

    return replace(contact, contact_id=contact_id)
