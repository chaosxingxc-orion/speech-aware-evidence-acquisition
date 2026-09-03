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
    audio2tool_locked_call_array_response_format,
    audio2tool_locked_outer_call_array_response_format,
    audio2tool_outer_call_array_response_format,
    audio2tool_selection_response_format,
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


def test_exact_no_public_constraint_sentinel_adds_no_schema_constraint() -> None:
    response_format = audio2tool_call_array_response_format(
        (
            _row(
                "getLightState",
                "getLightState(deviceId: String)",
                "No public constraint is declared.",
            ),
        ),
        (_card("getLightState", (("deviceId",),)),),
    )

    device_id = _branches(response_format)[
        ("getLightState", ("deviceId",))
    ]["properties"]["arguments"]["properties"]["deviceId"]
    assert device_id == {"type": "string"}


@pytest.mark.parametrize(
    "malformed",
    (
        "No public constraints are declared.",
        "No public constraint is declared",
        "No public constraint is declared. trailing text",
    ),
)
def test_only_exact_no_public_constraint_sentinel_is_accepted(
    malformed: str,
) -> None:
    with pytest.raises(A2tResponseSchemaError, match="constraints.*malformed"):
        audio2tool_call_array_response_format(
            (_row("getLightState", "getLightState(deviceId: String)", malformed),),
            (_card("getLightState", (("deviceId",),)),),
        )


def test_strict_subset_schema_can_allow_an_empty_family_local_abstention() -> None:
    response_format = audio2tool_call_array_response_format(
        (_row("ping", "ping()"),),
        (_card("ping", ((),)),),
        min_calls=0,
        max_calls=1,
    )

    schema = response_format["json_schema"]["schema"]
    assert schema["minItems"] == 0
    assert schema["maxItems"] == 1


def test_selection_schema_allows_empty_and_repeated_exact_candidate_names() -> None:
    rows = (
        _row("setLightState", "setLightState(deviceId: String, state: OnOff?)"),
        _row("getLightState", "getLightState(deviceId: String)"),
        _row("unselectedTool", "unselectedTool()"),
    )

    first = audio2tool_selection_response_format(
        rows,
        ("setLightState", "getLightState"),
        max_calls=7,
    )
    second = audio2tool_selection_response_format(
        tuple(reversed(rows)),
        ("getLightState", "setLightState"),
        max_calls=7,
    )

    assert first == second
    document = first["json_schema"]["schema"]
    assert document["type"] == "array"
    assert document["minItems"] == 0
    assert document["maxItems"] == 7
    assert "uniqueItems" not in document
    item = document["items"]
    assert item == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": ["getLightState", "setLightState"],
            }
        },
        "required": ["name"],
        "additionalProperties": False,
    }


def test_selection_schema_refuses_empty_duplicate_or_unknown_candidates() -> None:
    rows = (_row("known", "known()"),)

    for candidates, message in (
        ((), "at least one candidate"),
        (("known", "known"), "duplicate candidate"),
        (("unknown",), "not in the registry"),
    ):
        with pytest.raises(A2tResponseSchemaError, match=message):
            audio2tool_selection_response_format(rows, candidates)

    with pytest.raises(A2tResponseSchemaError, match="bounds"):
        audio2tool_selection_response_format(
            rows,
            ("known",),
            min_calls=2,
            max_calls=1,
        )


def test_locked_call_schema_preserves_occurrences_positions_and_legal_types() -> None:
    rows = (
        _row(
            "setLightState",
            "setLightState(deviceId: String, state: OnOff?, level: Int?)",
            "state: [On, Off], level: [1-10]",
        ),
        _row("getLightState", "getLightState(deviceId: String)"),
    )
    cards = (
        _card("getLightState", (("deviceId",),)),
        _card(
            "setLightState",
            (("deviceId", "state"), ("deviceId", "level")),
        ),
    )
    occurrences = ("setLightState", "getLightState", "setLightState")

    response_format = audio2tool_locked_call_array_response_format(
        rows,
        cards,
        occurrences,
    )

    document = response_format["json_schema"]["schema"]
    assert document["minItems"] == document["maxItems"] == 3
    assert "items" not in document
    prefix = document["prefixItems"]
    assert len(prefix) == 3
    assert [
        {branch["properties"]["name"]["const"] for branch in item["oneOf"]}
        for item in prefix
    ] == [
        {"setLightState"},
        {"getLightState"},
        {"setLightState"},
    ]
    first_forms = {
        tuple(branch["properties"]["arguments"]["required"]): branch
        for branch in prefix[0]["oneOf"]
    }
    assert set(first_forms) == {
        ("deviceId", "level"),
        ("deviceId", "state"),
    }
    assert first_forms[("deviceId", "level")]["properties"]["arguments"][
        "properties"
    ]["level"] == {"type": "integer", "minimum": 1, "maximum": 10}
    assert first_forms[("deviceId", "state")]["properties"]["arguments"][
        "properties"
    ]["state"] == {"type": "string", "enum": ["On", "Off"]}
    assert prefix[0] == prefix[2]


def test_locked_call_schema_allows_only_an_empty_array_for_empty_selection() -> None:
    response_format = audio2tool_locked_call_array_response_format(
        (_row("known", "known()"),),
        (),
        (),
    )

    assert response_format["json_schema"]["schema"] == {
        "type": "array",
        "minItems": 0,
        "maxItems": 0,
        "prefixItems": [],
    }


def test_locked_call_schema_requires_cards_to_match_occurrences_exactly() -> None:
    rows = (
        _row("first", "first()"),
        _row("second", "second()"),
    )

    with pytest.raises(A2tResponseSchemaError, match="exactly match occurrence"):
        audio2tool_locked_call_array_response_format(
            rows,
            (_card("first", ((),)), _card("second", ((),))),
            ("first",),
        )


def test_outer_response_format_constrains_only_shape_and_registered_names() -> None:
    rows = (
        _row("setLightState", "setLightState(deviceId: String, state: OnOff?)"),
        _row("getLightState", "getLightState(deviceId: String)"),
    )

    first = audio2tool_outer_call_array_response_format(
        tuple(reversed(rows)),
        ("setLightState", "getLightState"),
        schema_name="audio2tool_outer_calls",
        min_calls=0,
        max_calls=5,
    )
    second = audio2tool_outer_call_array_response_format(
        rows,
        ("getLightState", "setLightState"),
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


def test_outer_response_format_restricts_names_to_per_sample_candidates() -> None:
    rows = (
        _row("selected", "selected(value: Int)"),
        _row("alsoSelected", "alsoSelected(flag: Boolean)"),
        _row("notSelected", "notSelected(required: String)"),
    )

    response_format = audio2tool_outer_call_array_response_format(
        rows,
        ("selected", "alsoSelected"),
        min_calls=1,
        max_calls=2,
    )

    call = response_format["json_schema"]["schema"]["items"]
    assert call == {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "enum": ["alsoSelected", "selected"],
            },
            "arguments": {"type": "object"},
        },
        "required": ["name", "arguments"],
        "additionalProperties": False,
    }
    assert "notSelected" not in call["properties"]["name"]["enum"]


def test_locked_outer_response_format_preserves_exact_occurrence_order() -> None:
    rows = (
        _row("setLightState", "setLightState(deviceId: String, level: Int)"),
        _row("getLightState", "getLightState(deviceId: String)"),
    )
    occurrences = ("setLightState", "getLightState", "setLightState")

    response_format = audio2tool_locked_outer_call_array_response_format(
        rows,
        occurrences,
    )

    document = response_format["json_schema"]["schema"]
    assert document["minItems"] == document["maxItems"] == 3
    assert "items" not in document
    assert [
        item["properties"]["name"]["const"]
        for item in document["prefixItems"]
    ] == list(occurrences)
    for item in document["prefixItems"]:
        assert item["required"] == ["name", "arguments"]
        assert item["additionalProperties"] is False
        assert item["properties"]["arguments"] == {"type": "object"}
        assert "properties" not in item["properties"]["arguments"]
        assert "required" not in item["properties"]["arguments"]
        assert "additionalProperties" not in item["properties"]["arguments"]


def test_locked_outer_response_format_allows_only_empty_array_for_no_occurrences() -> None:
    response_format = audio2tool_locked_outer_call_array_response_format(
        (_row("known", "known(required: String)"),),
        (),
    )

    assert response_format["json_schema"]["schema"] == {
        "type": "array",
        "minItems": 0,
        "maxItems": 0,
        "prefixItems": [],
    }


def test_outer_response_formats_do_not_read_parameter_contract_material() -> None:
    rows = (
        {
            "tool_name": "known",
            "signature": "malformed parameter material",
            "argument_constraints": "also malformed",
        },
    )

    joint = audio2tool_outer_call_array_response_format(rows, ("known",))
    fill = audio2tool_locked_outer_call_array_response_format(rows, ("known",))

    assert joint["json_schema"]["schema"]["items"]["properties"]["name"] == {
        "type": "string",
        "enum": ["known"],
    }
    assert fill["json_schema"]["schema"]["prefixItems"][0]["properties"][
        "name"
    ] == {"const": "known"}


def test_outer_response_formats_refuse_invalid_candidate_names() -> None:
    rows = (_row("known", "known()"),)

    for candidates, message in (
        ((), "at least one candidate"),
        (("known", "known"), "duplicate candidate"),
        (("unknown",), "not in the registry"),
    ):
        with pytest.raises(A2tResponseSchemaError, match=message):
            audio2tool_outer_call_array_response_format(rows, candidates)

    with pytest.raises(A2tResponseSchemaError, match="not in the registry"):
        audio2tool_locked_outer_call_array_response_format(rows, ("unknown",))


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
            ("ping",),
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
