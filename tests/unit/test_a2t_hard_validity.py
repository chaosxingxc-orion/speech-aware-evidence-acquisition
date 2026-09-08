import json

import pytest

from speech_aware_evidence_acquisition.rails.a2t_hard_validity import (
    DRAFT_CONTACT_ID,
    HARD_VALIDITY_POLICY_ID,
    MAX_AGENT_STATE_UTF8_BYTES,
    MAX_STORED_DRAFT_CHARS,
    REPAIR_CONTACT_ID,
    validate_hard_validity,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    HARD_VALIDITY_PROGRAM_ID,
    RailsControllersError,
    make_hard_validity_phase_controller,
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


VALID_DRAFT = json.dumps([{"name": "getBatteryStatus", "arguments": {}}])


def _successor(first_context, advance):
    """The context the runner would rebuild for the repair contact."""

    return AgentRuntimeContext(
        sample_id=first_context.sample_id,
        knowledge_snapshot_sha256=first_context.knowledge_snapshot_sha256,
        catalog_facet_ids=first_context.catalog_facet_ids,
        catalog_value_ids=first_context.catalog_value_ids,
        query_state=advance.next_query_state,
        task_contract=first_context.task_contract,
        agent_states=advance.new_agent_states,
        prior_response_sha256s=("d" * 64,),
        contact_index=1,
    )


def _controller():
    """The WAVE R7 fold: the same cell, built on
    ``rails.controllers.EvidenceAgentController`` walking
    ``phase-hard-validity-repair-v1``. Same registry rows, same declared arm
    identity; ``decoding_params`` now belong to the runner, which already
    merges the run-level mapping into every plan."""

    factory = make_hard_validity_phase_controller(
        registry_rows=REGISTRY_ROWS,
        key_representation_id="g3-construction-semantic-same-packet-v1",
        matcher_policy_id="g3-same-packet-matcher-v1",
        decoding_params={},
    )
    return factory("g3-sample")


def test_decoding_params_on_the_contact_are_refused_by_name() -> None:
    with pytest.raises(RailsControllersError, match="belong to the run"):
        make_hard_validity_phase_controller(
            registry_rows=REGISTRY_ROWS,
            key_representation_id="k",
            matcher_policy_id="m",
            decoding_params={"temperature": 0},
        )


def test_valid_draft_stops_with_frozen_core_draft_as_final_authority() -> None:
    controller = _controller()
    context = _context(_query_state())
    contact = controller.initial_contact(context)

    advance = controller.advance(
        context,
        contact,
        VALID_DRAFT,
    )

    assert isinstance(contact, AgentContactPlan)
    assert contact.contact_id == DRAFT_CONTACT_ID
    assert contact.key_representation_id == "g3-construction-semantic-same-packet-v1"
    assert contact.matcher_policy_id == "g3-same-packet-matcher-v1"
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
    # The identity fields now name the PROGRAM, which is the point of the fold;
    # the CONTENT is the same registered validity report as before.
    assert state.producer_policy_id == HARD_VALIDITY_PROGRAM_ID
    assert state.state_id == "draft:sample-1"
    assert state.state_kind == "phase:draft"
    assert "empty_call_list" in state.content
    repair_contact = repair_advance.next_contact
    assert isinstance(repair_contact, AgentContactPlan)
    assert repair_contact.contact_id == REPAIR_CONTACT_ID
    assert repair_contact.key_representation_id == draft_contact.key_representation_id
    assert "same supplied G3 knowledge packet" in repair_contact.instruction
    assert "Do not invent internal tool codes" in repair_contact.instruction

    second_context = _successor(first_context, repair_advance)
    final_advance = controller.advance(second_context, repair_contact, "not JSON")

    assert final_advance.transition.action_kind == "stop"
    assert final_advance.next_contact is None
    assert final_advance.new_agent_states == ()
    assert final_advance.final_response_contact_id == REPAIR_CONTACT_ID


def test_controller_rejects_a_third_contact_sequence() -> None:
    controller = _controller()
    first_context = _context(_query_state())
    draft_contact = controller.initial_contact(first_context)
    repair_advance = controller.advance(first_context, draft_contact, "[]")
    repair_contact = repair_advance.next_contact
    assert isinstance(repair_contact, AgentContactPlan)
    second_context = _successor(first_context, repair_advance)
    controller.advance(second_context, repair_contact, "[]")

    # The retired controller refused a third contact by inspecting
    # ``QueryState.loop_step``. The base refuses it because the program has two
    # phases and both are spent -- no loop-step arithmetic anywhere.
    with pytest.raises(RailsControllersError, match="advanced past its program"):
        controller.advance(second_context, repair_contact, "[]")


def test_long_malformed_draft_has_bounded_repair_state_and_one_repair() -> None:
    controller = _controller()
    first_context = _context(_query_state())
    draft_contact = controller.initial_contact(first_context)
    response = "malformed tool-call output " * 1024

    repair_advance = controller.advance(first_context, draft_contact, response)

    state = repair_advance.new_agent_states[0]
    state_document = json.loads(state.content)
    assert len(state.content.encode("utf-8")) <= MAX_AGENT_STATE_UTF8_BYTES
    assert len(state_document["previous_draft"]) <= MAX_STORED_DRAFT_CHARS
    assert state_document["previous_draft_omitted_chars"] == (
        len(response) - len(state_document["previous_draft"])
    )
    assert len(state_document["report"]["violations"]) == 1
    assert state_document["report"]["omitted_count"] == 0

    assert repair_advance.next_query_state is not None
    assert isinstance(repair_advance.next_contact, AgentContactPlan)
    second_context = _successor(first_context, repair_advance)
    final_advance = controller.advance(
        second_context,
        repair_advance.next_contact,
        response,
    )
    assert final_advance.next_contact is None
    assert final_advance.final_response_contact_id == REPAIR_CONTACT_ID
