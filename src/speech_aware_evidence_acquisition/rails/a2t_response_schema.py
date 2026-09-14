"""Strict JSON Schema response formats for routed Audio2Tool tool subsets.

The helper derives a response grammar only from public registry rows and the
already-qualified legal key skeletons on :class:`ToolSemanticCard`.  It reads
no examples, observations, construction values, or evaluation labels.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``audio2tool_call_array_response_format`` is catalog id
``saea-tool-a2t-call-array-response-format-v1`` on the ``USE`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .a2t_executable_semantic_cards import CompatibilityRule, ToolSemanticCard


DEFAULT_MAX_CALLS = 4
DEFAULT_SCHEMA_NAME = "audio2tool_tool_calls"

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SIGNATURE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")
_PARAMETER = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+)$")
_CONSTRAINT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[([^\]]*)\]")
_NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_RANGE = re.compile(rf"^\s*({_NUMBER})\s*-\s*({_NUMBER})\s*$")
_NO_PUBLIC_CONSTRAINT_SENTINEL = "No public constraint is declared."

_COMPATIBILITY_FORMS = frozenset(
    {
        "boolean",
        "boolean-string",
        "integer",
        "list",
        "map",
        "nullable-string",
        "number",
        "string",
    }
)


class A2tResponseSchemaError(ValueError):
    """The public registry/card inputs cannot form a strict response schema."""


@dataclass(frozen=True)
class _Argument:
    key: str
    type_name: str


@dataclass(frozen=True)
class _Tool:
    name: str
    arguments: tuple[_Argument, ...]
    constraints: Mapping[str, str]


def _split_arguments(text: str) -> tuple[str, ...]:
    if not text.strip():
        return ()
    parts: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(text):
        if character in "<[{(":
            depth += 1
        elif character in ">]})":
            depth -= 1
            if depth < 0:
                raise A2tResponseSchemaError("registry signature brackets are malformed")
        elif character == "," and depth == 0:
            parts.append(text[start:index].strip())
            start = index + 1
    if depth:
        raise A2tResponseSchemaError("registry signature brackets are malformed")
    parts.append(text[start:].strip())
    return tuple(parts)


def _parse_signature(name: str, value: object) -> tuple[_Argument, ...]:
    if not isinstance(value, str):
        raise A2tResponseSchemaError(f"registry signature for {name!r} must be text")
    matched = _SIGNATURE.fullmatch(value.strip())
    if matched is None or matched.group(1) != name:
        raise A2tResponseSchemaError(
            f"registry signature identity drift for {name!r}"
        )
    arguments: list[_Argument] = []
    seen: set[str] = set()
    for raw in _split_arguments(matched.group(2)):
        parameter = _PARAMETER.fullmatch(raw)
        if parameter is None:
            raise A2tResponseSchemaError(
                f"registry signature for {name!r} has a malformed argument"
            )
        key, type_name = parameter.groups()
        type_name = type_name.strip()
        if type_name.endswith("?"):
            type_name = type_name[:-1].strip()
        if key in seen or not type_name or not type_name.isascii():
            raise A2tResponseSchemaError(
                f"registry signature for {name!r} repeats or omits an argument"
            )
        seen.add(key)
        arguments.append(_Argument(key=key, type_name=type_name))
    return tuple(arguments)


def _parse_constraints(name: str, value: object, keys: set[str]) -> Mapping[str, str]:
    if value in (None, "", _NO_PUBLIC_CONSTRAINT_SENTINEL):
        return {}
    if not isinstance(value, str) or not value.isascii():
        raise A2tResponseSchemaError(
            f"registry constraints for {name!r} must be ASCII English text"
        )
    matches = tuple(_CONSTRAINT.finditer(value))
    if not matches:
        raise A2tResponseSchemaError(f"registry constraints for {name!r} are malformed")
    cursor = 0
    parsed: dict[str, str] = {}
    for match in matches:
        if value[cursor : match.start()].strip(" ,"):
            raise A2tResponseSchemaError(f"registry constraints for {name!r} are malformed")
        cursor = match.end()
        key, body = match.groups()
        if key not in keys or key in parsed or not body.strip():
            raise A2tResponseSchemaError(f"registry constraints for {name!r} are malformed")
        parsed[key] = body.strip()
    if value[cursor:].strip(" ,"):
        raise A2tResponseSchemaError(f"registry constraints for {name!r} are malformed")
    return parsed


def _load_registry(rows: Sequence[Mapping[str, str]]) -> Mapping[str, _Tool]:
    registry: dict[str, _Tool] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise A2tResponseSchemaError("registry rows must be mappings")
        name = row.get("tool_name")
        if not isinstance(name, str) or _IDENTIFIER.fullmatch(name) is None:
            raise A2tResponseSchemaError("registry rows need an exact tool_name")
        if name in registry:
            raise A2tResponseSchemaError(f"registry has duplicate tool {name!r}")
        arguments = _parse_signature(name, row.get("signature"))
        registry[name] = _Tool(
            name=name,
            arguments=arguments,
            constraints=_parse_constraints(
                name,
                row.get("argument_constraints"),
                {argument.key for argument in arguments},
            ),
        )
    if not registry:
        raise A2tResponseSchemaError("registry must contain at least one tool")
    return registry


def _load_registry_names(rows: Sequence[Mapping[str, str]]) -> frozenset[str]:
    """Load only public tool identities without reading parameter material."""

    names: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            raise A2tResponseSchemaError("registry rows must be mappings")
        name = row.get("tool_name")
        if not isinstance(name, str) or _IDENTIFIER.fullmatch(name) is None:
            raise A2tResponseSchemaError("registry rows need an exact tool_name")
        if name in names:
            raise A2tResponseSchemaError(f"registry has duplicate tool {name!r}")
        names.add(name)
    if not names:
        raise A2tResponseSchemaError("registry must contain at least one tool")
    return frozenset(names)


def audio2tool_perception_state_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    *,
    max_actions: int,
    max_candidates_per_action: int,
) -> dict[str, object]:
    """Build the strict native Perception candidate-state response schema.

    Tool names come from the complete authoritative registry. Arrays preserve
    action order, alternative order, and repeated candidate occurrences.
    Unique action occurrence identifiers are enforced by the matching parser
    because JSON Schema cannot require uniqueness of one field across objects.
    """

    if (
        isinstance(max_actions, bool)
        or not isinstance(max_actions, int)
        or max_actions < 1
        or isinstance(max_candidates_per_action, bool)
        or not isinstance(max_candidates_per_action, int)
        or max_candidates_per_action < 1
    ):
        raise A2tResponseSchemaError(
            "Perception-state bounds must be positive integers"
        )
    tool_names = sorted(_load_registry_names(registry_rows))
    text_list = {
        "type": "array",
        "items": {"type": "string"},
    }
    action = {
        "type": "object",
        "properties": {
            "action_id": {
                "type": "string",
                "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
            },
            "candidate_tools": {
                "type": "array",
                "minItems": 1,
                "maxItems": max_candidates_per_action,
                "items": {
                    "type": "string",
                    "enum": tool_names,
                },
            },
            "evidence": {"type": "string"},
            "uncertain_arguments": text_list,
        },
        "required": [
            "action_id",
            "candidate_tools",
            "evidence",
            "uncertain_arguments",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "audio2tool_perception_state",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "actions": {
                        "type": "array",
                        "maxItems": max_actions,
                        "items": action,
                    },
                    "global_constraints": text_list,
                },
                "required": ["actions", "global_constraints"],
                "additionalProperties": False,
            },
        },
    }


def _base_type_schema(type_name: str) -> dict[str, object]:
    lowered = type_name.lower()
    if lowered in {"boolean", "bool"}:
        return {"type": "boolean"}
    if lowered in {"int", "integer"}:
        return {"type": "integer"}
    if lowered in {"float", "number", "double"}:
        return {"type": "number"}
    generic = re.fullmatch(r"list<(.+)>", type_name, re.IGNORECASE)
    if generic is not None:
        return {"type": "array", "items": _base_type_schema(generic.group(1).strip())}
    if lowered.endswith("[]"):
        return {"type": "array", "items": _base_type_schema(type_name[:-2].strip())}
    if lowered == "list" or lowered.startswith("list<"):
        return {"type": "array"}
    if lowered.startswith("map") or lowered in {"object", "dict"}:
        return {"type": "object"}
    return {"type": "string"}


def _compatibility_type_schema(value_form: str) -> dict[str, object]:
    if value_form == "boolean":
        return {"type": "boolean"}
    if value_form == "boolean-string":
        return {"type": "string", "enum": ["True", "False"]}
    if value_form == "integer":
        return {"type": "integer"}
    if value_form == "list":
        return {"type": "array", "items": {"type": "string"}}
    if value_form == "map":
        return {"type": "object"}
    if value_form == "nullable-string":
        return {"type": ["string", "null"]}
    if value_form == "number":
        return {"type": "number"}
    if value_form == "string":
        return {"type": "string"}
    raise A2tResponseSchemaError(
        f"unsupported compatibility value form {value_form!r}"
    )


def _constraint_schema(
    schema: dict[str, object], constraint: str, *, tool_name: str, key: str
) -> dict[str, object]:
    result = dict(schema)
    range_match = _RANGE.fullmatch(constraint)
    type_value = result.get("type")
    if range_match is not None:
        if type_value not in {"integer", "number"}:
            raise A2tResponseSchemaError(
                f"numeric range constraint for {tool_name}.{key} is incompatible with its type"
            )
        low, high = (float(item) for item in range_match.groups())
        if low > high:
            raise A2tResponseSchemaError(
                f"numeric range constraint for {tool_name}.{key} is inverted"
            )
        if type_value == "integer" and (not low.is_integer() or not high.is_integer()):
            raise A2tResponseSchemaError(
                f"integer range constraint for {tool_name}.{key} is not integral"
            )
        result["minimum"] = int(low) if type_value == "integer" else low
        result["maximum"] = int(high) if type_value == "integer" else high
        return result

    values = tuple(part.strip() for part in constraint.split(","))
    if not all(values):
        raise A2tResponseSchemaError(f"enum constraint for {tool_name}.{key} is malformed")
    if type_value == "boolean":
        decoded = []
        for value in values:
            if value not in {"True", "False"}:
                raise A2tResponseSchemaError(
                    f"Boolean enum constraint for {tool_name}.{key} is malformed"
                )
            decoded.append(value == "True")
        result["enum"] = decoded
        return result
    if type_value == "integer":
        try:
            decoded = [int(value) for value in values]
        except ValueError as error:
            raise A2tResponseSchemaError(
                f"integer enum constraint for {tool_name}.{key} is malformed"
            ) from error
        if any(str(value) != raw for value, raw in zip(decoded, values, strict=True)):
            raise A2tResponseSchemaError(
                f"integer enum constraint for {tool_name}.{key} is malformed"
            )
        result["enum"] = decoded
        return result
    if type_value == "number":
        try:
            result["enum"] = [float(value) for value in values]
        except ValueError as error:
            raise A2tResponseSchemaError(
                f"numeric enum constraint for {tool_name}.{key} is malformed"
            ) from error
        return result
    if type_value == "array":
        items = result.get("items")
        if not isinstance(items, Mapping) or items.get("type") != "string":
            raise A2tResponseSchemaError(
                f"array enum constraint for {tool_name}.{key} lacks string item type"
            )
        result["items"] = {**items, "enum": list(values)}
        return result
    if type_value != "string":
        raise A2tResponseSchemaError(
            f"enum constraint for {tool_name}.{key} is incompatible with its type"
        )
    result["enum"] = list(values)
    return result


def _card_forms(
    card: ToolSemanticCard, tool: _Tool
) -> Mapping[tuple[str, ...], Mapping[str, str]]:
    known_skeletons = {tuple(sorted(skeleton)) for skeleton in card.legal_argument_key_sets}
    forms_by_skeleton: dict[tuple[str, ...], dict[str, str]] = {}
    public_keys = {argument.key for argument in tool.arguments}
    for rule in card.compatibility_rules:
        if not isinstance(rule, CompatibilityRule) or rule.tool_name != card.tool_name:
            raise A2tResponseSchemaError(
                f"compatibility rules for {card.tool_name!r} are malformed"
            )
        skeleton = tuple(sorted(rule.legal_argument_key_set))
        if skeleton not in known_skeletons:
            raise A2tResponseSchemaError(
                f"compatibility skeleton for {card.tool_name!r} is not legal"
            )
        forms = forms_by_skeleton.setdefault(skeleton, {})
        for key, value_form in rule.value_forms:
            if key not in skeleton or value_form not in _COMPATIBILITY_FORMS:
                raise A2tResponseSchemaError(
                    f"compatibility value form for {card.tool_name!r} is malformed"
                )
            prior = forms.get(key)
            if prior is not None and prior != value_form:
                raise A2tResponseSchemaError(
                    f"compatibility value forms disagree for {card.tool_name}.{key}"
                )
            forms[key] = value_form
        extension_keys = set(skeleton) - public_keys
        if extension_keys - set(key for key, _form in rule.value_forms):
            raise A2tResponseSchemaError(
                f"compatibility extension keys for {card.tool_name!r} lack value forms"
            )
    return forms_by_skeleton


def _argument_schema(
    tool: _Tool, key: str, forms: Mapping[str, str]
) -> dict[str, object]:
    if key in forms:
        return _compatibility_type_schema(forms[key])
    argument = next((item for item in tool.arguments if item.key == key), None)
    if argument is None:
        raise A2tResponseSchemaError(
            f"legal key {key!r} for {tool.name!r} is outside its signature"
        )
    schema = _base_type_schema(argument.type_name)
    constraint = tool.constraints.get(key)
    if constraint is not None:
        schema = _constraint_schema(schema, constraint, tool_name=tool.name, key=key)
    return schema


def _call_branch(tool: _Tool, skeleton: tuple[str, ...], forms: Mapping[str, str]) -> dict[str, object]:
    properties = {key: _argument_schema(tool, key, forms) for key in skeleton}
    return {
        "type": "object",
        "properties": {
            "name": {"const": tool.name},
            "arguments": {
                "type": "object",
                "properties": properties,
                "required": list(skeleton),
                "additionalProperties": False,
            },
        },
        "required": ["name", "arguments"],
        "additionalProperties": False,
    }


def audio2tool_call_array_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    selected_cards: Sequence[ToolSemanticCard],
    *,
    schema_name: str = DEFAULT_SCHEMA_NAME,
    min_calls: int = 1,
    max_calls: int = DEFAULT_MAX_CALLS,
) -> dict[str, object]:
    """Build strict array-only JSON Schema for the exact routed tool subset.

    Every selected tool/key-skeleton pair becomes an independent ``oneOf``
    branch.  This makes each argument object exact: optional arguments are
    represented by the qualified skeletons, rather than by permissive optional
    properties.  Repeated calls remain legal; this helper does not impose a
    uniqueness policy beyond the configured array bounds.
    """

    if not isinstance(schema_name, str) or _IDENTIFIER.fullmatch(schema_name) is None:
        raise A2tResponseSchemaError("schema_name must be an ASCII identifier")
    if (
        isinstance(min_calls, bool)
        or isinstance(max_calls, bool)
        or not isinstance(min_calls, int)
        or not isinstance(max_calls, int)
        or min_calls < 0
        or max_calls < min_calls
    ):
        raise A2tResponseSchemaError("call bounds must be non-negative integers with min <= max")
    registry = _load_registry(registry_rows)
    if not selected_cards:
        raise A2tResponseSchemaError("at least one selected tool card is required")

    cards_by_name: dict[str, ToolSemanticCard] = {}
    for card in selected_cards:
        if not isinstance(card, ToolSemanticCard):
            raise A2tResponseSchemaError("selected cards must be ToolSemanticCard instances")
        if card.tool_name in cards_by_name:
            raise A2tResponseSchemaError(f"duplicate selected tool {card.tool_name!r}")
        if card.tool_name not in registry:
            raise A2tResponseSchemaError(
                f"selected tool {card.tool_name!r} is not in the registry"
            )
        cards_by_name[card.tool_name] = card

    branches: list[dict[str, object]] = []
    for name in sorted(cards_by_name):
        card = cards_by_name[name]
        tool = registry[name]
        forms_by_skeleton = _card_forms(card, tool)
        if not card.legal_argument_key_sets:
            raise A2tResponseSchemaError(
                f"selected tool {name!r} has no legal argument-key skeleton"
            )
        skeletons: set[tuple[str, ...]] = set()
        for raw_skeleton in card.legal_argument_key_sets:
            if not isinstance(raw_skeleton, tuple) or len(raw_skeleton) != len(set(raw_skeleton)):
                raise A2tResponseSchemaError(
                    f"legal key skeleton for {name!r} is malformed"
                )
            if any(not isinstance(key, str) or _IDENTIFIER.fullmatch(key) is None for key in raw_skeleton):
                raise A2tResponseSchemaError(
                    f"legal key skeleton for {name!r} is malformed"
                )
            skeletons.add(tuple(sorted(raw_skeleton)))
        for skeleton in sorted(skeletons, key=lambda item: (len(item), item)):
            branches.append(
                _call_branch(tool, skeleton, forms_by_skeleton.get(skeleton, {}))
            )

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": min_calls,
                "maxItems": max_calls,
                "items": {"oneOf": branches},
            },
        },
    }


def audio2tool_selection_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    candidate_tool_names: Sequence[str],
    *,
    schema_name: str = "audio2tool_tool_selection",
    min_calls: int = 0,
    max_calls: int = DEFAULT_MAX_CALLS,
) -> dict[str, object]:
    """Build a strict argument-free tool-selection response schema.

    The output is an array of exact candidate tool names wrapped in objects.
    The array may be empty and may repeat a candidate name, preserving call
    occurrence multiplicity without exposing any argument field to SELECT.
    """

    if not isinstance(schema_name, str) or _IDENTIFIER.fullmatch(schema_name) is None:
        raise A2tResponseSchemaError("schema_name must be an ASCII identifier")
    if (
        isinstance(min_calls, bool)
        or isinstance(max_calls, bool)
        or not isinstance(min_calls, int)
        or not isinstance(max_calls, int)
        or min_calls < 0
        or max_calls < min_calls
    ):
        raise A2tResponseSchemaError(
            "selection bounds must be non-negative integers with min <= max"
        )
    registry = _load_registry(registry_rows)
    if isinstance(candidate_tool_names, (str, bytes)):
        raise A2tResponseSchemaError("at least one candidate tool is required")
    try:
        candidates = tuple(candidate_tool_names)
    except TypeError as error:
        raise A2tResponseSchemaError(
            "at least one candidate tool is required"
        ) from error
    if not candidates:
        raise A2tResponseSchemaError("at least one candidate tool is required")
    if any(not isinstance(name, str) or not name for name in candidates):
        raise A2tResponseSchemaError(
            "candidate tools must be non-empty registered names"
        )
    if len(candidates) != len(set(candidates)):
        raise A2tResponseSchemaError("duplicate candidate tool")
    unknown = tuple(sorted(set(candidates) - set(registry)))
    if unknown:
        raise A2tResponseSchemaError(
            f"candidate tool {unknown[0]!r} is not in the registry"
        )

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": min_calls,
                "maxItems": max_calls,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "enum": sorted(candidates),
                        }
                    },
                    "required": ["name"],
                    "additionalProperties": False,
                },
            },
        },
    }


def audio2tool_locked_call_array_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    selected_cards: Sequence[ToolSemanticCard],
    selected_tool_occurrences: Sequence[str],
    *,
    schema_name: str = "audio2tool_locked_calls",
) -> dict[str, object]:
    """Build a strict positional FILL schema for selected call occurrences.

    Each selected occurrence receives its own positional schema with an exact
    tool-name constant and that tool's qualified argument skeletons and types.
    Repeated names therefore remain repeated positions. An empty selection
    produces a schema that accepts only the empty array.
    """

    if not isinstance(schema_name, str) or _IDENTIFIER.fullmatch(schema_name) is None:
        raise A2tResponseSchemaError("schema_name must be an ASCII identifier")
    registry = _load_registry(registry_rows)
    if isinstance(selected_tool_occurrences, (str, bytes)):
        raise A2tResponseSchemaError(
            "selected tool occurrences must be a sequence"
        )
    try:
        occurrences = tuple(selected_tool_occurrences)
    except TypeError as error:
        raise A2tResponseSchemaError(
            "selected tool occurrences must be a sequence"
        ) from error
    if any(not isinstance(name, str) or not name for name in occurrences):
        raise A2tResponseSchemaError(
            "selected tool occurrences must contain non-empty names"
        )
    unknown_occurrences = tuple(sorted(set(occurrences) - set(registry)))
    if unknown_occurrences:
        raise A2tResponseSchemaError(
            f"selected tool {unknown_occurrences[0]!r} is not in the registry"
        )
    if isinstance(selected_cards, (str, bytes)):
        raise A2tResponseSchemaError("selected cards must be a sequence")
    try:
        cards = tuple(selected_cards)
    except TypeError as error:
        raise A2tResponseSchemaError("selected cards must be a sequence") from error

    cards_by_name: dict[str, ToolSemanticCard] = {}
    for card in cards:
        if not isinstance(card, ToolSemanticCard):
            raise A2tResponseSchemaError(
                "selected cards must be ToolSemanticCard instances"
            )
        if card.tool_name in cards_by_name:
            raise A2tResponseSchemaError(
                f"duplicate selected tool {card.tool_name!r}"
            )
        if card.tool_name not in registry:
            raise A2tResponseSchemaError(
                f"selected tool {card.tool_name!r} is not in the registry"
            )
        cards_by_name[card.tool_name] = card
    if set(cards_by_name) != set(occurrences):
        raise A2tResponseSchemaError(
            "selected cards must exactly match occurrence tool names"
        )

    branches_by_name: dict[str, list[dict[str, object]]] = {}
    for name in sorted(cards_by_name):
        card = cards_by_name[name]
        tool = registry[name]
        forms_by_skeleton = _card_forms(card, tool)
        if not card.legal_argument_key_sets:
            raise A2tResponseSchemaError(
                f"selected tool {name!r} has no legal argument-key skeleton"
            )
        skeletons: set[tuple[str, ...]] = set()
        for raw_skeleton in card.legal_argument_key_sets:
            if not isinstance(raw_skeleton, tuple) or len(raw_skeleton) != len(
                set(raw_skeleton)
            ):
                raise A2tResponseSchemaError(
                    f"legal key skeleton for {name!r} is malformed"
                )
            if any(
                not isinstance(key, str) or _IDENTIFIER.fullmatch(key) is None
                for key in raw_skeleton
            ):
                raise A2tResponseSchemaError(
                    f"legal key skeleton for {name!r} is malformed"
                )
            skeletons.add(tuple(sorted(raw_skeleton)))
        branches_by_name[name] = [
            _call_branch(tool, skeleton, forms_by_skeleton.get(skeleton, {}))
            for skeleton in sorted(skeletons, key=lambda item: (len(item), item))
        ]

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": len(occurrences),
                "maxItems": len(occurrences),
                "prefixItems": [
                    {"oneOf": branches_by_name[name]} for name in occurrences
                ],
            },
        },
    }


def audio2tool_outer_call_array_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    candidate_tool_names: Sequence[str] | None = None,
    *,
    schema_name: str = DEFAULT_SCHEMA_NAME,
    min_calls: int = 0,
    max_calls: int = DEFAULT_MAX_CALLS,
) -> dict[str, object]:
    """Build an outer-shape-only schema for a clean constrained-decoding factor.

    This variant fixes the documented array/call envelope and per-sample
    candidate tool spelling while deliberately leaving ``arguments`` open.
    It therefore isolates native output-shape enforcement from the
    executable-card intervention and from the stronger per-tool
    skeleton/type constraints in
    :func:`audio2tool_call_array_response_format`.
    """

    if not isinstance(schema_name, str) or _IDENTIFIER.fullmatch(schema_name) is None:
        raise A2tResponseSchemaError("schema_name must be an ASCII identifier")
    if (
        isinstance(min_calls, bool)
        or isinstance(max_calls, bool)
        or not isinstance(min_calls, int)
        or not isinstance(max_calls, int)
        or min_calls < 0
        or max_calls < 1
        or max_calls < min_calls
    ):
        raise A2tResponseSchemaError(
            "call bounds must be non-negative integers with max >= 1 and min <= max"
        )
    registry_names = _load_registry_names(registry_rows)
    if candidate_tool_names is None:
        candidate_tool_names = tuple(sorted(registry_names))
    if isinstance(candidate_tool_names, (str, bytes)):
        raise A2tResponseSchemaError("at least one candidate tool is required")
    try:
        candidates = tuple(candidate_tool_names)
    except TypeError as error:
        raise A2tResponseSchemaError(
            "at least one candidate tool is required"
        ) from error
    if not candidates:
        raise A2tResponseSchemaError("at least one candidate tool is required")
    if any(not isinstance(name, str) or not name for name in candidates):
        raise A2tResponseSchemaError(
            "candidate tools must be non-empty registered names"
        )
    if len(candidates) != len(set(candidates)):
        raise A2tResponseSchemaError("duplicate candidate tool")
    unknown = tuple(sorted(set(candidates) - registry_names))
    if unknown:
        raise A2tResponseSchemaError(
            f"candidate tool {unknown[0]!r} is not in the registry"
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": min_calls,
                "maxItems": max_calls,
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "enum": sorted(candidates),
                        },
                        "arguments": {"type": "object"},
                    },
                    "required": ["name", "arguments"],
                    "additionalProperties": False,
                },
            },
        },
    }


def audio2tool_locked_outer_call_array_response_format(
    registry_rows: Sequence[Mapping[str, str]],
    selected_tool_occurrences: Sequence[str],
    *,
    schema_name: str = "audio2tool_locked_outer_calls",
) -> dict[str, object]:
    """Build an outer-only FILL schema locked to selected occurrences.

    The result fixes the exact occurrence count, order, and tool name while
    deliberately leaving every argument object open. Repeated tool names stay
    repeated positions, and an empty selection accepts only an empty array.
    """

    if not isinstance(schema_name, str) or _IDENTIFIER.fullmatch(schema_name) is None:
        raise A2tResponseSchemaError("schema_name must be an ASCII identifier")
    registry_names = _load_registry_names(registry_rows)
    if isinstance(selected_tool_occurrences, (str, bytes)):
        raise A2tResponseSchemaError(
            "selected tool occurrences must be a sequence"
        )
    try:
        occurrences = tuple(selected_tool_occurrences)
    except TypeError as error:
        raise A2tResponseSchemaError(
            "selected tool occurrences must be a sequence"
        ) from error
    if any(not isinstance(name, str) or not name for name in occurrences):
        raise A2tResponseSchemaError(
            "selected tool occurrences must contain non-empty names"
        )
    unknown = tuple(sorted(set(occurrences) - registry_names))
    if unknown:
        raise A2tResponseSchemaError(
            f"selected tool {unknown[0]!r} is not in the registry"
        )

    def positional_call(name: str) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "name": {"const": name},
                "arguments": {"type": "object"},
            },
            "required": ["name", "arguments"],
            "additionalProperties": False,
        }

    return {
        "type": "json_schema",
        "json_schema": {
            "name": schema_name,
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": len(occurrences),
                "maxItems": len(occurrences),
                "prefixItems": [positional_call(name) for name in occurrences],
            },
        },
    }


__all__ = [
    "A2tResponseSchemaError",
    "DEFAULT_MAX_CALLS",
    "DEFAULT_SCHEMA_NAME",
    "audio2tool_call_array_response_format",
    "audio2tool_locked_call_array_response_format",
    "audio2tool_locked_outer_call_array_response_format",
    "audio2tool_outer_call_array_response_format",
    "audio2tool_selection_response_format",
]
