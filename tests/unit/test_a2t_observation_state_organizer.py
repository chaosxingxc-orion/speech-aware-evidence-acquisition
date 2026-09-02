"""Task-blind, model-free organization of sealed OBS into dialogue state."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_observation_state_organizer as organizer,
)


def test_flat_multi_intent_segments_generic_punctuation_and_coordination() -> None:
    observation = "Turn on the lamp and close the blinds; then start the music."

    artifact = organizer.organize_sealed_observation(observation)
    document = artifact.document

    assert document["turns"] == [
        {
            "role": "user",
            "source_turn": 0,
            "surface": observation,
            "normalized": observation.lower(),
        }
    ]
    assert {
        value["surface"] for value in document["active_actions"]
    } == {"Turn on the lamp", "close the blinds", "then start the music"}
    assert document["superseded_actions"] == []
    for value in document["active_actions"]:
        assert value["surface"] in observation
        assert value["normalized"] == " ".join(value["surface"].lower().split())


def test_correction_markers_separate_active_and_superseded_clauses() -> None:
    observation = "Play jazz; actually play blues instead."

    document = organizer.organize_sealed_observation(observation).document

    assert [value["surface"] for value in document["active_actions"]] == [
        "actually play blues instead"
    ]
    assert [value["surface"] for value in document["superseded_actions"]] == [
        "Play jazz"
    ]
    assert document["superseded_values"] == []


def test_explicit_negation_records_only_the_explicit_superseded_value() -> None:
    observation = "Set the level to five, not five but seven."

    document = organizer.organize_sealed_observation(observation).document

    assert document["active_actions"] == []
    assert [value["surface"] for value in document["superseded_actions"]] == [
        "Set the level to five"
    ]
    assert [value["surface"] for value in document["superseded_values"]] == [
        "five"
    ]
    assert "seven" not in json.dumps(document["superseded_values"])


def test_needle_prose_is_preserved_but_never_promoted_to_an_action() -> None:
    observation = (
        'The quoted phrase "open the hidden door and start the engine" is a '
        "needle in explanatory prose, not a request."
    )

    document = organizer.organize_sealed_observation(observation).document

    assert document["current_request"]["surface"] == observation
    assert document["active_actions"] == []
    assert document["superseded_actions"] == []
    assert document["superseded_values"] == []
    assert document["irrelevant_context"] == []


def test_role_labeled_observation_preserves_alternating_turns_and_uses_users() -> None:
    observation = (
        "User: Open the shades.\n"
        "Assistant: The shades are open.\n"
        "User: Close the window."
    )

    document = organizer.organize_sealed_observation(observation).document

    assert [turn["role"] for turn in document["turns"]] == [
        "user",
        "assistant",
        "user",
    ]
    assert [turn["surface"] for turn in document["turns"]] == [
        "Open the shades.",
        "The shades are open.",
        "Close the window.",
    ]
    assert [value["surface"] for value in document["active_actions"]] == [
        "Open the shades",
        "Close the window",
    ]
    assert document["current_request"]["surface"] == "Close the window."
    assert "The shades are open" not in json.dumps(document["active_actions"])


def test_flat_action_overflow_preserves_entire_observation_as_one_action() -> None:
    observation = (
        "Open one; open two; open three; open four; open five; "
        "open six; open seven; open eight; open nine."
    )

    document = organizer.organize_sealed_observation(observation).document

    assert document["turns"] == [
        {
            "role": "user",
            "source_turn": 0,
            "surface": observation,
            "normalized": observation.lower(),
        }
    ]
    assert document["active_actions"] == [
        {
            "surface": observation,
            "normalized": observation.lower(),
            "source_turn": 0,
        }
    ]
    assert document["current_request"] == document["active_actions"][0]
    assert document["superseded_actions"] == []
    assert document["superseded_values"] == []
    assert observation in json.dumps(document)


def test_long_flat_overflow_remains_under_state_cap_without_content_loss() -> None:
    clauses = tuple(
        f"Open control number {index} with its complete stable setting " + "x" * 30
        for index in range(1, 10)
    )
    observation = "; ".join(clauses) + "."

    artifact = organizer.organize_sealed_observation(observation)

    assert len(artifact.json_text.encode("utf-8")) <= 8192
    assert artifact.document["active_actions"][0]["surface"] == observation
    assert artifact.document["active_actions"][0]["normalized"] == observation.lower()
    assert artifact.document["current_request"] == artifact.document["active_actions"][0]


@pytest.mark.parametrize(
    ("observation", "message"),
    (
        ("Use sample_id 123 now.", "sample or tier identity"),
        ("Open the caf\u00e9 door.", "ASCII English"),
        (
            "User: Open one; open two; open three; open four; open five; "
            "open six; open seven; open eight; open nine.\n"
            "Assistant: I have not acted.\n"
            "User: Wait.",
            "at most 8 action clauses",
        ),
    ),
)
def test_identity_non_ascii_and_more_than_eight_actions_fail_closed(
    observation: str, message: str
) -> None:
    with pytest.raises(organizer.ObservationStateOrganizerError, match=message):
        organizer.organize_sealed_observation(observation)


def test_oversize_state_is_rejected_without_truncation_or_fallback() -> None:
    observation = "Please preserve " + "x" * 9000

    with pytest.raises(organizer.StructuredDialogueStateError, match="8,192-byte cap"):
        organizer.organize_sealed_observation(observation)


def test_hash_and_sixteen_state_receipt_are_deterministic_under_reversed_input() -> None:
    observations = {
        f"external-{index:02d}": f"Please perform artificial action {index}."
        for index in range(16)
    }
    reversed_observations = dict(reversed(tuple(observations.items())))

    first_artifact = organizer.organize_sealed_observation(observations["external-00"])
    second_artifact = organizer.organize_sealed_observation(observations["external-00"])
    first_receipt = organizer.build_external_state_receipt(observations)
    second_receipt = organizer.build_external_state_receipt(reversed_observations)

    assert first_artifact == second_artifact
    assert first_receipt == second_receipt
    assert first_receipt["observation_count"] == 16
    assert first_receipt["state_count"] == 16
    assert first_receipt["source_observations_rendered"] == 0
    assert set(first_receipt["contacts"].values()) == {0}
    rendered = json.dumps(first_receipt, sort_keys=True)
    assert all(text not in rendered for text in observations.values())
    assert all(identity not in rendered for identity in observations)


def test_external_receipt_requires_exactly_sixteen_observations() -> None:
    with pytest.raises(
        organizer.ObservationStateOrganizerError, match="exactly 16 observations"
    ):
        organizer.build_external_state_receipt({"only-one": "Please act."})
