"""Deterministic routing and bounded packets for the semantic microground."""

from __future__ import annotations

from dataclasses import replace
import re

import pytest

from speech_aware_evidence_acquisition.rails import a2t_semantic_microground as ground
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    ExecutableSemanticCardCorpus,
    TaskSemanticCard,
    ToolSemanticCard,
)
from speech_aware_evidence_acquisition.rails import (
    a2t_structured_dialogue_state as dialogue,
)


def _card(
    name: str,
    choose: str,
    *,
    avoid: str = "Avoid a different operation.",
    keys: tuple[tuple[str, ...], ...] = ((),),
    roles: tuple[str, ...] = (),
    padding: str = "",
) -> ToolSemanticCard:
    examples = (f'{{"arguments":{{}},"name":"{name}"}}',)
    text = "\n".join(
        (
            f"TOOL CARD {name}",
            f"Exact tool name: {name}",
            f"Choose when: {choose}",
            f"Avoid when: {avoid}",
            "Legal argument-key sets: "
            + "; ".join("{" + ", ".join(row) + "}" for row in keys),
            *roles,
            *examples,
            padding,
        )
    )
    return ToolSemanticCard(
        tool_name=name,
        choose_semantics=choose,
        avoid_semantics=avoid,
        signature=f"{name}()",
        constraints="",
        legal_argument_key_sets=keys,
        compatibility_rules=(),
        role_guidance=roles,
        examples=examples,
        text=text,
    )


def _corpus(
    *, reverse: bool = False, padding: str = ""
) -> ExecutableSemanticCardCorpus:
    cards = (
        _card(
            "getLightState",
            "Read and inspect the current light state.",
            avoid="Avoid changing a light; sibling setLightState performs that operation.",
            keys=(("deviceId",),),
            roles=("Spoken role: device identifier -> deviceId (String).",),
        ),
        _card(
            "setLightState",
            "Switch on, switch off, or otherwise set a lamp light state.",
            avoid="Avoid reading a light; sibling getLightState performs that operation.",
            keys=(("deviceId", "state"),),
            roles=(
                "Spoken role: device identifier -> deviceId (String).",
                "Spoken role: state -> state (OnOff).",
            ),
        ),
        _card(
            "setThermostat",
            "Set the thermostat temperature to the requested number of degrees.",
            avoid="Avoid reading temperature; sibling getTemperature performs that operation.",
            keys=(("degrees", "room"),),
            roles=(
                "Spoken role: degrees -> degrees (Float).",
                "Spoken role: room -> room (String).",
            ),
        ),
        _card(
            "getTemperature",
            "Read the current room temperature.",
            avoid="Avoid changing temperature; sibling setThermostat performs that operation.",
            keys=(("room",),),
            roles=("Spoken role: room -> room (String).",),
        ),
        _card(
            "bookRide",
            "Book a taxi ride to a destination.",
            keys=(("destination",),),
            roles=("Spoken role: destination -> destination (String).",),
        ),
        _card(
            "planTrip",
            "Plan a travel route to a destination.",
            keys=(("destination",),),
            roles=("Spoken role: destination -> destination (String).",),
            padding=padding,
        ),
    )
    tasks = tuple(
        TaskSemanticCard(card_id=f"task-{index}", text=f"Task rule {index}.")
        for index in range(4)
    )
    if reverse:
        cards = tuple(reversed(cards))
        tasks = tuple(reversed(tasks))
    return ExecutableSemanticCardCorpus(
        text="unused complete corpus",
        sha256="a" * 64,
        tool_cards=cards,
        task_cards=tasks,
        report={"registry_tool_count": len(cards)},
    )


def _state() -> dict[str, object]:
    return {
        "current_request": "Switch on the desk lamp and set the office to 21 degrees.",
        "active_actions": [
            {
                "action_phrase": "switch on",
                "target_phrase": "desk lamp light",
                "values": [
                    {
                        "role": "device identifier",
                        "surface": "desk lamp",
                        "normalized": "desk lamp",
                        "source_turn": 1,
                        "status": "active",
                    }
                ],
            },
            {
                "action_phrase": "set temperature",
                "target_phrase": "office thermostat",
                "values": [
                    {
                        "role": "degrees",
                        "surface": "twenty one",
                        "normalized": "21",
                        "source_turn": 1,
                        "status": "active",
                    },
                    {
                        "role": "room",
                        "surface": "office",
                        "normalized": "office",
                        "source_turn": 1,
                        "status": "active",
                    },
                ],
            },
        ],
    }


def test_structured_state_routes_per_action_and_renders_only_selected_cards() -> None:
    route = ground.route_semantic_microground(_corpus(), structured_state=_state())

    assert route.action_queries == (
        "switch on desk lamp light device identifier desk lamp desk lamp",
        "set temperature office thermostat degrees twenty one 21 room office office",
    )
    assert 2 <= len(route.candidate_names) <= 8
    assert "setLightState" in route.candidate_names
    assert "setThermostat" in route.candidate_names
    assert all(
        any(
            reason.startswith(f"action-{action_index}-top1")
            for reason in candidate.reasons
        )
        for action_index, required in enumerate(("setLightState", "setThermostat"))
        for candidate in route.candidates
        if candidate.tool_name == required
    )
    assert len(route.task_card_ids) == 4
    assert route.packet.count("TASK CARD ") == 4
    for name in route.candidate_names:
        assert f"TOOL CARD {name}" in route.packet
    for name in set(_corpus().cards_by_name) - set(route.candidate_names):
        assert f"TOOL CARD {name}\n" not in route.packet
    assert route.packet_utf8_bytes == len(route.packet.encode("utf-8"))
    assert re.fullmatch(r"[0-9a-f]{64}", route.packet_sha256)
    assert re.fullmatch(r"[0-9a-f]{64}", route.trace_sha256)
    assert all(candidate.action_scores for candidate in route.candidates)
    assert all(candidate.reasons for candidate in route.candidates)


def test_validated_strict_dialogue_state_routes_using_normalized_active_action() -> None:
    observation = "User: Please switch the desk lamp on."
    turns = dialogue.extract_role_labeled_g3_turns(
        observation,
        normalized_turns=("please switch on the desk lamp.",),
    )
    artifact = dialogue.build_structured_dialogue_state(
        observation,
        turns=turns,
        current_request=dialogue.StateValue(
            surface="Please switch the desk lamp on.",
            normalized="please switch on the desk lamp.",
            source_turn=0,
        ),
        active_actions=(
            dialogue.StateValue(
                surface="switch the desk lamp on",
                normalized="switch on the desk lamp",
                source_turn=0,
            ),
        ),
    )
    validated = dialogue.parse_structured_dialogue_state(artifact.json_text)

    route = ground.route_semantic_microground(
        _corpus(), structured_state=validated.document
    )

    assert route.action_queries == ("switch on the desk lamp",)
    assert "setLightState" in route.candidate_names


def test_state_value_action_falls_back_to_surface_when_normalized_is_absent() -> None:
    route = ground.route_semantic_microground(
        _corpus(),
        structured_state={
            "active_actions": [
                {
                    "surface": "book a taxi ride to the station",
                    "source_turn": 0,
                }
            ]
        },
    )

    assert route.action_queries == ("book a taxi ride to the station",)
    assert "bookRide" in route.candidate_names


def test_empty_active_actions_route_once_from_current_request_without_promotion() -> None:
    route = ground.route_semantic_microground(
        _corpus(),
        structured_state={
            "current_request": {
                "surface": "Please book a taxi ride to the station.",
                "normalized": "book a taxi ride to the station",
                "source_turn": 0,
            },
            "active_actions": [],
        },
    )

    assert route.action_queries == ("book a taxi ride to the station",)
    assert route.representation == "structured-state:current-request-fallback"
    assert "bookRide" in route.candidate_names


def test_observation_route_is_byte_identical_under_reversed_corpus_input() -> None:
    observation = "Please book a taxi ride to the station destination."

    first = ground.route_semantic_microground(_corpus(), observation=observation)
    second = ground.route_semantic_microground(
        _corpus(reverse=True), observation=observation
    )

    assert first == second
    assert first.candidate_names[0] == "bookRide"
    assert first.action_queries == (observation,)
    assert first.packet.isascii()


def test_zero_score_ties_use_exact_tool_name_order() -> None:
    route = ground.route_semantic_microground(
        _corpus(), observation="qxzv unmatched vocabulary"
    )

    assert route.candidate_names[:2] == ("bookRide", "getLightState")
    assert route.candidates[0].action_scores[0].rank == 1
    assert route.candidates[1].action_scores[0].rank == 2


@pytest.mark.parametrize(
    ("structured_state", "observation", "message"),
    (
        (None, None, "exactly one"),
        (_state(), "also supplied", "exactly one"),
        ({"active_actions": []}, None, "active action"),
        ({"active_actions": [{"action_phrase": "caf\u00e9"}]}, None, "ASCII English"),
        (
            {
                "gold_label": "setLightState",
                "active_actions": [{"action_phrase": "switch on"}],
            },
            None,
            "forbidden runtime feature",
        ),
        (
            {
                "active_actions": [
                    {"action_phrase": f"action {index}"} for index in range(9)
                ]
            },
            None,
            "at most eight",
        ),
    ),
)
def test_query_surface_fails_closed(
    structured_state: dict[str, object] | None,
    observation: str | None,
    message: str,
) -> None:
    with pytest.raises(ground.SemanticMicrogroundError, match=message):
        ground.route_semantic_microground(
            _corpus(), structured_state=structured_state, observation=observation
        )


def test_synthetic_example_literals_are_rejected_from_any_query_surface() -> None:
    synthetic = "SYNTHETIC_SETLIGHTSTATE_DEVICEID_001"

    with pytest.raises(ground.SemanticMicrogroundError, match="synthetic-example"):
        ground.route_semantic_microground(
            _corpus(), observation=f"Switch on {synthetic}."
        )
    unsafe_state = _state()
    unsafe_state["active_actions"] = [
        {"action_phrase": "switch on", "target_phrase": synthetic}
    ]
    with pytest.raises(ground.SemanticMicrogroundError, match="synthetic-example"):
        ground.route_semantic_microground(_corpus(), structured_state=unsafe_state)


def test_packet_byte_limit_refuses_without_partial_truncation() -> None:
    corpus = _corpus(padding="X" * 20_000)

    with pytest.raises(ground.SemanticMicrogroundError, match="byte budget"):
        ground.route_semantic_microground(
            corpus,
            observation="Plan a travel route to a destination.",
        )
    with pytest.raises(ground.SemanticMicrogroundError, match="between one and 16384"):
        ground.route_semantic_microground(
            _corpus(), observation="Book a ride.", max_utf8_bytes=16_385
        )


def test_stage1_structural_metrics_use_only_public_registry_contract() -> None:
    responses = (
        '[{"name":"setLightState","arguments":{"deviceId":"desk","state":"On"}}]',
        '[{"name":"setLightState","arguments":{"deviceId":"desk"}}]',
        '[{"name":"unknownTool","arguments":{}}]',
        "not json",
        "[]",
    )

    outcomes = tuple(
        ground.evaluate_stage1_structure(text, _corpus()) for text in responses
    )
    metrics = ground.aggregate_stage1_structure(outcomes)

    assert [outcome.parsed for outcome in outcomes] == [True, True, True, False, True]
    assert [outcome.registry_names_only for outcome in outcomes] == [
        True,
        True,
        False,
        False,
        False,
    ]
    assert [outcome.legal_key_sets_only for outcome in outcomes] == [
        True,
        False,
        False,
        False,
        False,
    ]
    assert metrics.total_count == 5
    assert metrics.parse_count == 4
    assert metrics.registry_names_only_count == 2
    assert metrics.legal_key_sets_only_count == 1
    assert metrics.parse_rate == pytest.approx(0.8)


def test_corpus_and_task_card_invariants_fail_closed() -> None:
    duplicate = replace(
        _corpus(), tool_cards=(*_corpus().tool_cards, _corpus().tool_cards[0])
    )
    short_tasks = replace(_corpus(), task_cards=_corpus().task_cards[:3])

    with pytest.raises(ground.SemanticMicrogroundError, match="unique tool"):
        ground.route_semantic_microground(duplicate, observation="switch on a light")
    with pytest.raises(ground.SemanticMicrogroundError, match="exactly four"):
        ground.route_semantic_microground(short_tasks, observation="switch on a light")
