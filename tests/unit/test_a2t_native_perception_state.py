"""Pure native Audio2Tool Perception-state parsing."""

import json

import pytest

from speech_aware_evidence_acquisition.rails.adapters.audio2tool_runtime import (
    Audio2ToolPerceptionStateError,
    parse_audio2tool_perception_state,
)


def state(actions, constraints=None):
    return json.dumps(
        {"actions": actions, "global_constraints": constraints or []},
        ensure_ascii=False,
    )


def action(action_id, candidates, *, evidence="heard request", uncertain=None):
    return {
        "action_id": action_id,
        "candidate_tools": candidates,
        "evidence": evidence,
        "uncertain_arguments": uncertain or [],
    }


def parse(
    text,
    *,
    legal=("setLight", "setAmbientLighting", "setColor"),
    max_actions=7,
    max_candidates=8,
):
    return parse_audio2tool_perception_state(
        text,
        legal_tool_names=legal,
        max_actions=max_actions,
        max_candidates_per_action=max_candidates,
    )


def test_preserves_order_repeats_alternatives_constraints_and_unicode():
    actions = [
        action(
            f"turn:{index}",
            ["setLight", "setAmbientLighting", "setLight", "setColor"],
            evidence="José said the café light should change.",
            uncertain=["room name", "exact colour"],
        )
        for index in range(5)
    ]
    parsed = parse(
        state(actions, ["Apply the final correction.", "Keep call order."]),
        max_actions=5,
        max_candidates=4,
    )

    assert tuple(item.action_id for item in parsed.actions) == tuple(
        f"turn:{i}" for i in range(5)
    )
    assert parsed.actions[0].candidate_tools == (
        "setLight",
        "setAmbientLighting",
        "setLight",
        "setColor",
    )
    assert parsed.actions[0].evidence == "José said the café light should change."
    assert parsed.actions[0].uncertain_arguments == ("room name", "exact colour")
    assert parsed.global_constraints == (
        "Apply the final correction.",
        "Keep call order.",
    )
    assert parsed.unique_tool_names == ("setLight", "setAmbientLighting", "setColor")


def test_allows_no_actions_and_has_no_answer_field():
    parsed = parse(
        state([], ["The request contains no executable action."]), legal=("setLight",)
    )
    assert parsed.actions == ()
    assert parsed.unique_tool_names == ()
    assert parsed.global_constraints == ("The request contains no executable action.",)
    assert not hasattr(parsed, "answer")


@pytest.mark.parametrize(
    "text,legal,max_actions,max_candidates,match",
    [
        (
            state([action("a:1", ["unknownTool"])]),
            ("setLight",),
            1,
            1,
            "outside the authoritative inventory",
        ),
        (
            state([action("a:1", ["setLight"]), action("a:1", ["setLight"])]),
            ("setLight",),
            2,
            1,
            "action_id",
        ),
        (
            state([action("bad id", ["setLight"])]),
            ("setLight",),
            1,
            1,
            "canonical occurrence",
        ),
        (
            state([action("a:1", ["not-canonical"])]),
            ("not-canonical",),
            1,
            1,
            "canonical tool",
        ),
        (state([action("a:1", [])]), ("setLight",), 1, 1, "non-empty"),
        (
            state([action("a:1", ["setLight"]), action("a:2", ["setLight"])]),
            ("setLight",),
            1,
            1,
            "max_actions",
        ),
        (
            state([action("a:1", ["setLight", "setColor"])]),
            ("setLight", "setColor"),
            1,
            1,
            "max_candidates_per_action",
        ),
    ],
)
def test_rejects_illegal_identity_or_bound(
    text, legal, max_actions, max_candidates, match
):
    with pytest.raises(Audio2ToolPerceptionStateError, match=match):
        parse(text, legal=legal, max_actions=max_actions, max_candidates=max_candidates)


@pytest.mark.parametrize(
    "field,value",
    [
        ("max_actions", 0),
        ("max_actions", True),
        ("max_candidates_per_action", 0),
        ("max_candidates_per_action", False),
    ],
)
def test_requires_explicit_positive_integer_bounds(field, value):
    kwargs = {"max_actions": 1, "max_candidates_per_action": 1, field: value}
    with pytest.raises(Audio2ToolPerceptionStateError, match=field):
        parse_audio2tool_perception_state(
            state([]), legal_tool_names=("setLight",), **kwargs
        )


@pytest.mark.parametrize(
    "text,match",
    [
        ('{"actions":[],"actions":[],"global_constraints":[]}', "duplicate JSON key"),
        (
            '{"actions":[{"action_id":"a:1","candidate_tools":["setLight"],'
            '"evidence":"one","evidence":"two","uncertain_arguments":[]}],'
            '"global_constraints":[]}',
            "duplicate JSON key",
        ),
        (
            '```json\n{"actions":[],"global_constraints":[]}\n```',
            "unfenced JSON object",
        ),
        ('{"actions":[],"global_constraints":[],"extra":1}', "exactly actions"),
        ('{"actions":{},"global_constraints":[]}', "actions must be an ordered list"),
        (
            '{"actions":[{"action_id":"a:1","candidate_tools":["setLight"],'
            '"evidence":7,"uncertain_arguments":[]}],"global_constraints":[]}',
            "evidence must be text",
        ),
        (
            '{"actions":[],"global_constraints":[1]}',
            "global_constraints must contain text",
        ),
        ('{"actions":[],"global_constraints":[],"n":NaN}', "JSON"),
    ],
)
def test_rejects_malformed_or_ambiguous_json(text, match):
    with pytest.raises(Audio2ToolPerceptionStateError, match=match):
        parse(text, legal=("setLight",))
