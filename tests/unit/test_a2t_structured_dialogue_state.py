"""Strict structured dialogue state derived from sealed task-blind OBS."""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_structured_dialogue_state as dialogue,
)


SEALED_OBSERVATION = (
    "User: Turn the lamp on.\n"
    "Assistant: The lamp is on.\n"
    "User: Actually turn the lamp off; the weather comment is irrelevant."
)
NORMALIZED_TURNS = (
    "turn the lamp on.",
    "the lamp is on.",
    "actually turn the lamp off; the weather comment is irrelevant.",
)


def _value(surface: str, normalized: str, source_turn: int) -> dialogue.StateValue:
    return dialogue.StateValue(
        surface=surface,
        normalized=normalized,
        source_turn=source_turn,
    )


def _artifact() -> dialogue.StructuredDialogueStateArtifact:
    turns = dialogue.extract_role_labeled_g3_turns(
        SEALED_OBSERVATION,
        normalized_turns=NORMALIZED_TURNS,
    )
    return dialogue.build_structured_dialogue_state(
        SEALED_OBSERVATION,
        turns=turns,
        current_request=_value(
            "Actually turn the lamp off; the weather comment is irrelevant.",
            "actually turn the lamp off; the weather comment is irrelevant.",
            2,
        ),
        active_actions=(_value("turn the lamp off", "turn the lamp off", 2),),
        superseded_actions=(_value("Turn the lamp on", "turn the lamp on", 0),),
        superseded_values=(_value("on", "on", 0),),
        irrelevant_context=(_value("weather comment", "weather comment", 2),),
    )


def test_state_uses_exact_ascii_schema_and_preserves_surface_normalized_source() -> None:
    artifact = _artifact()
    document = artifact.document

    assert set(document) == {
        "active_actions",
        "current_request",
        "irrelevant_context",
        "superseded_actions",
        "superseded_values",
        "turns",
    }
    assert all(
        set(turn) == {"normalized", "role", "source_turn", "surface"}
        for turn in document["turns"]
    )
    for field in (
        "current_request",
        "active_actions",
        "superseded_actions",
        "superseded_values",
        "irrelevant_context",
    ):
        values = document[field] if isinstance(document[field], list) else [document[field]]
        assert all(
            set(value) == {"normalized", "source_turn", "surface"}
            for value in values
        )
    assert document["turns"][0] == {
        "normalized": "turn the lamp on.",
        "role": "user",
        "source_turn": 0,
        "surface": "Turn the lamp on.",
    }
    assert document["active_actions"][0] == {
        "normalized": "turn the lamp off",
        "source_turn": 2,
        "surface": "turn the lamp off",
    }
    assert artifact.json_text.isascii()
    assert len(artifact.json_text.encode("utf-8")) <= dialogue.MAX_STATE_UTF8_BYTES


def test_role_labeled_g3_extraction_and_explicit_flat_spans_are_chronological() -> None:
    labeled = dialogue.extract_role_labeled_g3_turns(
        SEALED_OBSERVATION,
        normalized_turns=NORMALIZED_TURNS,
    )
    assert tuple(turn.role for turn in labeled) == ("user", "assistant", "user")
    assert SEALED_OBSERVATION[labeled[0].start : labeled[0].end] == "Turn the lamp on."

    flat = "Turn music on.\nMusic is on.\nTurn music off."
    first = flat.index("Turn music on.")
    second = flat.index("Music is on.")
    third = flat.index("Turn music off.")
    spans = (
        dialogue.ObservationTurnSpan("user", first, first + 14, "turn music on."),
        dialogue.ObservationTurnSpan(
            "assistant", second, second + 12, "music is on."
        ),
        dialogue.ObservationTurnSpan("user", third, len(flat), "turn music off."),
    )
    artifact = dialogue.build_structured_dialogue_state(
        flat,
        turns=spans,
        current_request=_value("Turn music off.", "turn music off.", 2),
        active_actions=(_value("Turn music off", "turn music off", 2),),
    )
    assert [turn["role"] for turn in artifact.document["turns"]] == [
        "user",
        "assistant",
        "user",
    ]


def test_canonical_rendering_and_hash_are_deterministic() -> None:
    artifact = _artifact()
    document = artifact.document
    reversed_keys = {key: document[key] for key in reversed(tuple(document))}

    rendered = dialogue.render_structured_dialogue_state(reversed_keys)
    reparsed = dialogue.parse_structured_dialogue_state(rendered.json_text)

    assert rendered == artifact
    assert reparsed == artifact
    assert artifact.json_text == json.dumps(
        document,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert artifact.sha256 == hashlib.sha256(
        artifact.json_text.encode("utf-8")
    ).hexdigest()


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda document: {**document, "tool_name": "setLightState"},
            "exact top-level fields",
        ),
        (
            lambda document: {
                **document,
                "current_request": {
                    **document["current_request"],
                    "gold_value": "private",
                },
            },
            "exact value fields",
        ),
        (
            lambda document: {
                **document,
                "turns": [
                    {**document["turns"][0], "sample_id": "private"},
                    *document["turns"][1:],
                ],
            },
            "exact turn fields",
        ),
    ),
)
def test_schema_has_no_tool_candidate_sample_reference_or_gold_fields(
    mutate, message: str
) -> None:
    with pytest.raises(dialogue.StructuredDialogueStateError, match=message):
        dialogue.render_structured_dialogue_state(mutate(_artifact().document))


def test_state_rejects_identifiers_in_text_and_inferred_missing_values() -> None:
    document = _artifact().document
    with pytest.raises(dialogue.StructuredDialogueStateError, match="sample or tier identity"):
        dialogue.render_structured_dialogue_state(
            {
                **document,
                "active_actions": [
                    {
                        "surface": "tier7_multiturn:000318",
                        "normalized": "tier7_multiturn:000318",
                        "source_turn": 2,
                    }
                ],
            }
        )
    with pytest.raises(dialogue.StructuredDialogueStateError, match="not present"):
        dialogue.render_structured_dialogue_state(
            {
                **document,
                "active_actions": [
                    {
                        "surface": "set it to 72 degrees",
                        "normalized": "set it to 72 degrees",
                        "source_turn": 2,
                    }
                ],
            }
        )


def test_active_and_superseded_actions_are_mutually_exclusive() -> None:
    document = _artifact().document
    duplicate = document["active_actions"][0]

    with pytest.raises(dialogue.StructuredDialogueStateError, match="mutually exclusive"):
        dialogue.render_structured_dialogue_state(
            {**document, "superseded_actions": [duplicate]}
        )


@pytest.mark.parametrize(
    ("turns", "message"),
    (
        (
            (
                dialogue.ObservationTurnSpan("assistant", 6, 23, "turn the lamp on."),
                dialogue.ObservationTurnSpan("assistant", 35, 50, "the lamp is on."),
                dialogue.ObservationTurnSpan("user", 57, len(SEALED_OBSERVATION), NORMALIZED_TURNS[2]),
            ),
            "begin with user",
        ),
        (
            (
                dialogue.ObservationTurnSpan("user", 6, 23, "turn the lamp on."),
                dialogue.ObservationTurnSpan("user", 35, 50, "the lamp is on."),
                dialogue.ObservationTurnSpan("user", 57, len(SEALED_OBSERVATION), NORMALIZED_TURNS[2]),
            ),
            "alternate",
        ),
        (
            (
                dialogue.ObservationTurnSpan("user", 6, 23, "turn the lamp on."),
                dialogue.ObservationTurnSpan("assistant", 35, 50, "the lamp is on."),
                dialogue.ObservationTurnSpan(
                    "assistant", 57, len(SEALED_OBSERVATION), NORMALIZED_TURNS[2]
                ),
            ),
            "end with user",
        ),
    ),
)
def test_invalid_role_history_remains_invalid_without_fallback(turns, message: str) -> None:
    with pytest.raises(dialogue.StructuredDialogueStateError, match=message):
        dialogue.build_structured_dialogue_state(
            SEALED_OBSERVATION,
            turns=turns,
            current_request=_value(
                "Actually turn the lamp off; the weather comment is irrelevant.",
                NORMALIZED_TURNS[2],
                len(turns) - 1,
            ),
        )


def test_invalid_json_noncanonical_json_non_ascii_and_oversize_never_repair() -> None:
    with pytest.raises(dialogue.StructuredDialogueStateError, match="malformed JSON"):
        dialogue.parse_structured_dialogue_state("{broken")
    pretty = json.dumps(_artifact().document, indent=2, sort_keys=True)
    with pytest.raises(dialogue.StructuredDialogueStateError, match="canonical"):
        dialogue.parse_structured_dialogue_state(pretty)

    non_ascii = _artifact().document
    non_ascii["turns"][2]["surface"] = "caf\u00e9"
    with pytest.raises(dialogue.StructuredDialogueStateError, match="ASCII English"):
        dialogue.render_structured_dialogue_state(non_ascii)

    large = _artifact().document
    padding = "x" * 9000
    large["turns"][2]["surface"] = padding
    large["turns"][2]["normalized"] = padding
    large["current_request"] = {
        "surface": padding,
        "normalized": padding,
        "source_turn": 2,
    }
    large["active_actions"] = []
    large["irrelevant_context"] = []
    with pytest.raises(dialogue.StructuredDialogueStateError, match="8,192-byte cap"):
        dialogue.render_structured_dialogue_state(large)
