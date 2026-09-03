"""Strict JSON-schema response formats for routed Audio2Tool candidates."""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    CompatibilityRule,
    ToolSemanticCard,
)
from speech_aware_evidence_acquisition.rails.a2t_response_schema import (
    A2tResponseSchemaError,
    audio2tool_call_array_response_format,
    audio2tool_outer_call_array_response_format,
)


def _row(name: str, signature: str, constraints: str = "") -> dict[str, str]:
    return {
        "tool_name": name,
        "signature": signature,
        "argument_constraints": constraints,
    }


def _card(
    name: str,
    skeletons: tuple[tuple[str, ...], ...],
    *,
    rules: tuple[CompatibilityRule, ...] = (),
) -> ToolSemanticCard:
    return ToolSemanticCard(
        tool_name=name,
        choose_semantics="Choose this exact action.",
        avoid_semantics="Avoid another action.",
        signature=f"{name}()",
        constraints="",
        legal_argument_key_sets=skeletons,
        compatibility_rules=rules,
        role_guidance=(),
        examples=(),
        text="English-only test card.",
    )


def _branches(response_format: dict[str, object]) -> dict[tuple[str, tuple[str, ...]], dict[str, object]]:
    schema = response_format["json_schema"]["schema"]  # type: ignore[index]
    items = schema["items"]  # type: ignore[index]
    return {
        (
            branch["properties"]["name"]["const"],  # type: ignore[index]
            tuple(branch["properties"]["arguments"]["required"]),  # type: ignore[index]
        ): branch
        for branch in items["oneOf"]  # type: ignore[index]
    }


def test_builds_a_deterministic_strict_subset_schema_per_legal_skeleton() -> None:
    rows = (
        _row(
            "setLightState",
            "setLightState(deviceId: String, state: OnOff?, level: Int?)",
            "state: [On, Off], level: [1-10]",
        ),
        _row("getLightState", "getLightState(deviceId: String)"),
        _row("unselectedTool", "unselectedTool()"),
    )
    cards = (
        _card("getLightState", (("deviceId",),)),
        _card(
            "setLightState",
            (("deviceId",), ("deviceId", "state"), ("deviceId", "level")),
        ),
    )

    first = audio2tool_call_array_response_format(rows, cards)
    second = audio2tool_call_array_response_format(tuple(reversed(rows)), tuple(reversed(cards)))

    assert first == second
    wrapper = first["json_schema"]
    assert wrapper["name"] == "audio2tool_tool_calls"
    assert wrapper["strict"] is True
    schema = wrapper["schema"]
    assert schema["type"] == "array"
    assert schema["minItems"] == 1
    assert schema["maxItems"] == 4
    branches = _branches(first)
    assert set(branches) == {
        ("getLightState", ("deviceId",)),
        ("setLightState", ("deviceId",)),
        ("setLightState", ("deviceId", "level")),
        ("setLightState", ("deviceId", "state")),
    }
    state = branches[("setLightState", ("deviceId", "state"))]["properties"][
        "arguments"
    ]["properties"]["state"]
    level = branches[("setLightState", ("deviceId", "level"))]["properties"][
        "arguments"
    ]["properties"]["level"]
    assert state == {"type": "string", "enum": ["On", "Off"]}
    assert level == {"type": "integer", "minimum": 1, "maximum": 10}
    for branch in branches.values():
        assert branch["required"] == ["name", "arguments"]
        assert branch["additionalProperties"] is False
        assert branch["properties"]["arguments"]["additionalProperties"] is False


def test_outer_response_format_constrains_only_shape_and_registered_names() -> None:
    rows = (
        _row("setLightState", "setLightState(deviceId: String, state: OnOff?)"),
        _row("getLightState", "getLightState(deviceId: String)"),
    )

    first = audio2tool_outer_call_array_response_format(
        tuple(reversed(rows)),
        schema_name="audio2tool_outer_calls",
        min_calls=0,
        max_calls=5,
    )
    second = audio2tool_outer_call_array_response_format(
        rows,
        schema_name="audio2tool_outer_calls",
        min_calls=0,
        max_calls=5,
    )

    assert first == second
    document = first["json_schema"]["schema"]
    assert first["type"] == "json_schema"
    assert first["json_schema"]["strict"] is True
    assert document["type"] == "array"
    assert document["minItems"] == 0
    assert document["maxItems"] == 5
    call = document["items"]
    assert call["required"] == ["name", "arguments"]
    assert call["additionalProperties"] is False
    assert call["properties"]["name"] == {
        "type": "string",
        "enum": ["getLightState", "setLightState"],
    }
    assert call["properties"]["arguments"] == {"type": "object"}


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    ((-1, 4), (2, 1), (False, 4), (0, True)),
)
def test_outer_response_format_rejects_invalid_bounds(
    minimum: object, maximum: object
) -> None:
    with pytest.raises(A2tResponseSchemaError, match="call bounds"):
        audio2tool_outer_call_array_response_format(
            (_row("ping", "ping()"),),
            min_calls=minimum,  # type: ignore[arg-type]
            max_calls=maximum,  # type: ignore[arg-type]
        )


def test_preserves_zero_argument_arrays_nested_values_and_compatibility_forms() -> None:
    compatibility = CompatibilityRule(
        tool_name="configureRoute",
        legal_argument_key_set=("enabled", "label"),
        value_forms=(("enabled", "boolean-string"), ("label", "nullable-string")),
        construction_support_count=2,
    )
    rows = (
        _row("ping", "ping()"),
        _row(
            "configureRoute",
            "configureRoute(tags: List<String>, metadata: Map, enabled: Boolean?, label: String?)",
        ),
    )
    cards = (
        _card("ping", ((),)),
        _card(
            "configureRoute",
            (("metadata", "tags"), ("enabled", "label")),
            rules=(compatibility,),
        ),
    )

    branches = _branches(audio2tool_call_array_response_format(rows, cards))

    assert branches[("ping", ())]["properties"]["arguments"]["properties"] == {}
    normal = branches[("configureRoute", ("metadata", "tags"))]["properties"][
        "arguments"
    ]["properties"]
    compatible = branches[("configureRoute", ("enabled", "label"))]["properties"][
        "arguments"
    ]["properties"]
    assert normal["tags"] == {"type": "array", "items": {"type": "string"}}
    assert normal["metadata"] == {"type": "object"}
    assert compatible["enabled"] == {"type": "string", "enum": ["True", "False"]}
    assert compatible["label"] == {"type": ["string", "null"]}


def test_compatibility_value_forms_apply_only_to_their_legal_skeleton() -> None:
    compatibility = CompatibilityRule(
        tool_name="setMode",
        legal_argument_key_set=("enabled", "label"),
        value_forms=(("enabled", "boolean-string"),),
        construction_support_count=2,
    )
    rows = (_row("setMode", "setMode(enabled: Boolean, label: String?)"),)
    cards = (
        _card(
            "setMode",
            (("enabled",), ("enabled", "label")),
            rules=(compatibility,),
        ),
    )

    branches = _branches(audio2tool_call_array_response_format(rows, cards))

    assert branches[("setMode", ("enabled",))]["properties"]["arguments"][
        "properties"
    ]["enabled"] == {"type": "boolean"}
    assert branches[("setMode", ("enabled", "label"))]["properties"][
        "arguments"
    ]["properties"]["enabled"] == {"type": "string", "enum": ["True", "False"]}


@pytest.mark.parametrize(
    ("rows", "cards", "kwargs", "message"),
    (
        (
            (_row("known", "known()"),),
            (_card("unknown", ((),)),),
            {},
            "not in the registry",
        ),
        (
            (_row("known", "known()"),),
            (_card("known", (("ghost",),)),),
            {},
            "outside its signature",
        ),
        (
            (_row("known", "known()"),),
            (_card("known", ((),)), _card("known", ((),))),
            {},
            "duplicate selected tool",
        ),
        (
            (_row("known", "known()"),),
            (),
            {},
            "at least one selected tool",
        ),
        (
            (_row("known", "known()"),),
            (_card("known", ((),)),),
            {"min_calls": 2, "max_calls": 1},
            "call bounds",
        ),
    ),
)
def test_refuses_invalid_subset_or_contract_inputs(
    rows: tuple[dict[str, str], ...],
    cards: tuple[ToolSemanticCard, ...],
    kwargs: dict[str, int],
    message: str,
) -> None:
    with pytest.raises(A2tResponseSchemaError, match=message):
        audio2tool_call_array_response_format(rows, cards, **kwargs)
