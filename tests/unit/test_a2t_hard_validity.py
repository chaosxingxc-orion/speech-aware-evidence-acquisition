import json

import pytest

from speech_aware_evidence_acquisition.rails.a2t_hard_validity import (
    DRAFT_CONTACT_ID,
    HARD_VALIDITY_POLICY_ID,
    REPAIR_CONTACT_ID,
    HardValidityRepairController,
    validate_hard_validity,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.runner import (
    AgentContactPlan,
    AgentRuntimeContext,
)


REGISTRY_ROWS = (
    {
        "tool_name": "getBatteryStatus",
        "signature": "getBatteryStatus()",
        "argument_constraints": "",
    },
    {
        "tool_name": "getAirQuality",
        "signature": "getAirQuality(deviceId:String)",
        "argument_constraints": "",
    },
    {
        "tool_name": "setBrightness",
        "signature": "setBrightness(deviceId:String, level:Int)",
        "argument_constraints": "level: [0-100]",
    },
    {
        "tool_name": "enableWaterLock",
        "signature": "enableWaterLock(enabled:Boolean)",
        "argument_constraints": "enabled: [True, False]",
    },
    {
        "tool_name": "getBiometricData",
        "signature": "getBiometricData(metric:String)",
        "argument_constraints": "metric: [Heart Rate, Blood Oxygen]",
    },
)


def _codes(response: str) -> set[str]:
    return {
        violation.code
        for violation in validate_hard_validity(response, REGISTRY_ROWS).violations
    }


@pytest.mark.parametrize(
    ("sample_id", "response", "expected_code"),
    (
        (
            "tier1_direct:002510",
            '[{"name":"updateFirmware","arguments":{}}',
            "json_parse_error",
        ),
        ("tier7_dialogue_history:000000", "[]", "empty_call_list"),
        (
            "tier2_parametric:001693",
            '[{"name":"U100","arguments":{}}]',
            "internal_tool_code",
        ),
        (
            "tier1_direct:004218",
            '[{"name":"U140","arguments":{"_secondary":"U140"}}]',
            "internal_argument_key",
        ),
        (
            "tier1_direct:003210",
            '[{"name":"getBiometricData","arguments":{"key":"Heart Rate"}}]',
            "unknown_argument_key",
        ),
    ),
)
def test_g2_replays_are_hard_invalid_without_gold(
    sample_id: str, response: str, expected_code: str
) -> None:
    report = validate_hard_validity(response, REGISTRY_ROWS)

    assert sample_id
    assert report.policy_id == HARD_VALIDITY_POLICY_ID
    assert report.status == "hard-invalid"
    assert expected_code in {item.code for item in report.violations}


def test_deployment_visible_type_constraint_count_and_duplicate_checks() -> None:
    assert "argument_type_invalid" in _codes(
        '[{"name":"enableWaterLock","arguments":{"enabled":"true"}}]'
    )
    assert "argument_constraint_invalid" in _codes(
        '[{"name":"setBrightness","arguments":{"level":101}}]'
    )
    assert "too_many_calls" in _codes(
        json.dumps(
            [
                {"name": "getBatteryStatus", "arguments": {"slot": index}}
                for index in range(5)
            ]
        )
    )
    assert "duplicate_call" in _codes(
        '[{"name":"getBatteryStatus","arguments":{}},'
        '{"name":"getBatteryStatus","arguments":{}}]'
    )
    assert "duplicate_json_key" in _codes(
        '[{"name":"getBatteryStatus","name":"setBrightness","arguments":{}}]'
    )


@pytest.mark.parametrize(
    "response",
    (
        # Tool choice is semantic and cannot be judged without the utterance.
        '[{"name":"getBatteryStatus","arguments":{}}]',
        # Entity and canonicalization choices are semantic when the type is valid.
        '[{"name":"getAirQuality","arguments":{"deviceId":"guest_room_sensor"}}]',
        '[{"name":"getAirQuality","arguments":{"deviceId":"Guest Room"}}]',
        # Missing task arguments are deliberately outside hard_validity_v1.
        '[{"name":"setBrightness","arguments":{}}]',
        # Any nonempty sequence up to four is plausible without gold call counts.
        '[{"name":"getBatteryStatus","arguments":{}},'
        '{"name":"getAirQuality","arguments":{"deviceId":"hall"}},'
        '{"name":"setBrightness","arguments":{"level":30}},'
        '{"name":"enableWaterLock","arguments":{"enabled":true}}]',
    ),
)
def test_semantic_risks_do_not_trigger_hard_repair(response: str) -> None:
    report = validate_hard_validity(response, REGISTRY_ROWS)

    assert report.status == "valid"
    assert report.violations == ()


def _query_state(*, loop_step: int = 0, state_ids: tuple[str, ...] = ()) -> QueryState:
    return QueryState(
        query_id="query:sample-1",
        query_sample_id="sample-1",
        speech_packet_id="speech:sample-1",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
        loop_step=loop_step,
        visible_facet_ids=("facet:g3-same-packet",),
        agent_state_ids=state_ids,
        retrieved_value_ids=("value:g3-same-packet",),
    ).validate()


def _context(state: QueryState, *, contact_index: int = 0) -> AgentRuntimeContext:
    return AgentRuntimeContext(
        sample_id="sample-1",
        knowledge_snapshot_sha256="c" * 64,
        catalog_facet_ids=("facet:g3-same-packet",),
        catalog_value_ids=("value:g3-same-packet",),
        query_state=state,
        task_contract="Return the requested calls as JSON.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=contact_index,
    )


def _controller() -> HardValidityRepairController:
    return HardValidityRepairController(
        registry_rows=REGISTRY_ROWS,
        key_representation_id="g3-construction-semantic-same-packet-v1",
        matcher_policy_id="g3-same-packet-matcher-v1",
        decoding_params={"temperature": 0, "max_tokens": 1024},
    )


def test_valid_draft_stops_with_frozen_core_draft_as_final_authority() -> None:
    controller = _controller()
    context = _context(_query_state())
    contact = controller.initial_contact(context)

    advance = controller.advance(
        context,
        contact,
        '[{"name":"getBatteryStatus","arguments":{}}]',
    )

    assert isinstance(contact, AgentContactPlan)
    assert contact.contact_id == DRAFT_CONTACT_ID
    assert advance.transition.action_kind == "stop"
    assert advance.next_contact is None
    assert advance.new_agent_states == ()
    assert advance.final_response_contact_id == DRAFT_CONTACT_ID


def test_hard_invalid_draft_gets_exactly_one_same_core_repair_then_stops() -> None:
    controller = _controller()
    first_context = _context(_query_state())
    draft_contact = controller.initial_contact(first_context)

    repair_advance = controller.advance(first_context, draft_contact, "[]")

    assert repair_advance.transition.action_kind == "organize"
    assert repair_advance.next_query_state is not None
    assert repair_advance.next_query_state.loop_step == 1
    assert repair_advance.next_query_state.visible_facet_ids == (
        "facet:g3-same-packet",
    )
    assert repair_advance.next_query_state.retrieved_value_ids == (
        "value:g3-same-packet",
    )
    assert len(repair_advance.new_agent_states) == 1
    state = repair_advance.new_agent_states[0]
    assert state.producer_policy_id == HARD_VALIDITY_POLICY_ID
    assert "empty_call_list" in state.content
    repair_contact = repair_advance.next_contact
    assert isinstance(repair_contact, AgentContactPlan)
    assert repair_contact.contact_id == REPAIR_CONTACT_ID
    assert repair_contact.key_representation_id == draft_contact.key_representation_id
    assert "same supplied G3 knowledge packet" in repair_contact.instruction
    assert "Do not invent internal tool codes" in repair_contact.instruction

    second_context = AgentRuntimeContext(
        sample_id=first_context.sample_id,
        knowledge_snapshot_sha256=first_context.knowledge_snapshot_sha256,
        catalog_facet_ids=first_context.catalog_facet_ids,
        catalog_value_ids=first_context.catalog_value_ids,
        query_state=repair_advance.next_query_state,
        task_contract=first_context.task_contract,
        agent_states=repair_advance.new_agent_states,
        prior_response_sha256s=("d" * 64,),
        contact_index=1,
    )
    final_advance = controller.advance(second_context, repair_contact, "not JSON")

    assert final_advance.transition.action_kind == "stop"
    assert final_advance.next_contact is None
    assert final_advance.new_agent_states == ()
    assert final_advance.final_response_contact_id == REPAIR_CONTACT_ID


def test_controller_rejects_a_third_contact_sequence() -> None:
    controller = _controller()
    context = _context(_query_state(loop_step=2), contact_index=2)
    contact = AgentContactPlan(
        contact_id=REPAIR_CONTACT_ID,
        query_state_sha256=context.query_state.content_hash(),
        purpose="invalid third contact",
        instruction="Do not run.",
        key_representation_id="g3-construction-semantic-same-packet-v1",
        matcher_policy_id="g3-same-packet-matcher-v1",
        decoding_params={"temperature": 0},
    )

    with pytest.raises(ValueError, match="invalid contact sequence"):
        controller.advance(context, contact, "[]")
