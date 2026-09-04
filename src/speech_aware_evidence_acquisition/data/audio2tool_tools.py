"""OpenAI-format ``tools`` schema renderer for the Audio2Tool D1a native-tool-
calling arm.

The direct-prompt baseline (``data.audio2tool.render_tool_schemas``) pastes
the full ``tools_registry.csv`` as ~13k tokens of raw JSON into the system
message and asks for a bare JSON array back; 6-14% of outputs fail to parse.
The pinned llama.cpp build (``--jinja``, the GGUF chat template) supports
native OpenAI-format function calling: send the registry as
``{"type":"function","function":{...}}`` entries under the request's
``tools`` key, let the template render ``<tools>...</tools>``, and parse
``message.tool_calls`` back rather than free text. This module renders that
``tools`` list; it never edits ``data.audio2tool`` and never changes what
that module's own ``load_tool_registry``/``render_tool_schemas`` return.

Design decisions, made once here rather than re-derived ad hoc, verified
against the real 152-row ``tools_registry.csv`` (2026-09-03):

- ``required`` is decided purely by "does this parameter have an
  ``argument_defaults`` entry" -- independent of the signature's own ``?``
  (nullable) marker. The two do not always coincide: e.g.
  ``setAlarm(time: Time, label: String?, repeat: List<String>?)`` gives
  ``label`` a real default (``'Wake Up'``), not ``null``, even though its
  type is marked optional. A parameter is never both required AND
  auto-filled: Tier 1 is argument-free by the paper's own protocol, so a
  JSON-schema ``default`` is never populated -- the registry default is
  named only in the property's ``description`` text (``"default: ..."``),
  where a model reading the schema can see it without the harness silently
  supplying it.
- ``Boolean`` parameters never receive an ``enum``/``minimum``/``maximum``
  from their constraint bracket (e.g. ``enabled: [True, False]``): the JSON
  Schema ``"type": "boolean"`` already carries exactly that information: a
  string enum of ``["True", "False"]`` would conflict with the boolean type
  rather than add anything.
- ``List<X>`` parameters attach their constraint bracket (when present) to
  the array's ``items`` schema, not to the array schema itself -- the
  bracket enumerates legal ELEMENT values (e.g. ``zones: List<String>?``
  constrained to ``[Living_Room, Kitchen, Bedroom, Hallway]`` describes each
  zone in the list, not the list as a whole).
- A constraint bracket is read as a numeric range (``minimum``/``maximum``)
  only when its ENTIRE body matches ``<number> - <number>`` (spaces
  optional, either side may be negative, e.g. ``[-10 - 10]``,
  ``[0000-9999]``, ``[15.0-30.0]``); otherwise every top-level
  comma-separated entry becomes an ``enum`` member verbatim. This is a
  single generic rule, not a per-type special case: it also covers
  ``HsbColor``'s compound constraint body (``"Hue:0-360, Sat:0-100,
  Bri:0-100"``), which is not a clean range and degrades to a 3-member
  string enum rather than raising -- the renderer must still close 152/152.
- The signature's ``?`` (nullable) marker is stripped before type mapping
  and does not otherwise change the rendered schema -- JSON Schema has no
  first-class "nullable" concept this repository's tool-calling consumer
  reads, and ``required`` already tracks presence-of-default independently
  (see above).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping, Sequence

from .audio2tool import load_tool_registry


class Audio2ToolSchemaError(RuntimeError):
    """A ``tools_registry.csv`` row cannot be rendered as an OpenAI tool schema."""


_SIGNATURE_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)\((?P<params>.*)\)$")
_PARAM_RE = re.compile(
    r"^(?P<name>[A-Za-z_]\w*):\s*(?P<type>[A-Za-z_]\w*(?:<[A-Za-z_]\w*>)?)(?P<optional>\?)?$"
)
_LIST_TYPE_RE = re.compile(r"^List<([A-Za-z_]\w*)>$")
_CONSTRAINT_ENTRY_RE = re.compile(r"(\w+):\s*\[([^\]]*)\]")
_RANGE_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$")
_DEFAULT_ENTRY_RE = re.compile(r"^([A-Za-z_]\w*)=(.*)$")

_PRIMITIVE_JSON_TYPES: dict[str, str] = {
    "Int": "integer",
    "Float": "number",
    "Boolean": "boolean",
    "String": "string",
}


def _parse_signature(tool_name: str, signature: str) -> list[tuple[str, str, bool]]:
    """``[(param_name, base_type_without_'?', optional), ...]`` in signature order."""

    match = _SIGNATURE_RE.match(signature.strip())
    if match is None:
        raise ValueError(f"signature {signature!r} does not match 'name(params)'")
    if match.group("name") != tool_name:
        raise ValueError(
            f"signature function name {match.group('name')!r} does not match "
            f"tool_name {tool_name!r}"
        )
    params_text = match.group("params").strip()
    if not params_text:
        return []
    params: list[tuple[str, str, bool]] = []
    seen: set[str] = set()
    for chunk in params_text.split(","):
        chunk = chunk.strip()
        param_match = _PARAM_RE.match(chunk)
        if param_match is None:
            raise ValueError(f"unparsable parameter {chunk!r} in signature {signature!r}")
        name = param_match.group("name")
        if name in seen:
            raise ValueError(f"duplicate parameter {name!r} in signature {signature!r}")
        seen.add(name)
        params.append((name, param_match.group("type"), param_match.group("optional") is not None))
    return params


def _split_top_level_commas(text: str) -> list[str]:
    """Split on ``,`` outside single quotes -- ``"color='0,0,100'"`` (an
    HsbColor default, the one row in ``tools_registry.csv`` whose own
    quoted default VALUE contains a comma) must stay one chunk, not three."""

    chunks: list[str] = []
    current: list[str] = []
    in_quotes = False
    for character in text:
        if character == "'":
            in_quotes = not in_quotes
            current.append(character)
        elif character == "," and not in_quotes:
            chunks.append("".join(current))
            current = []
        else:
            current.append(character)
    chunks.append("".join(current))
    return chunks


def _parse_defaults(defaults_text: str) -> dict[str, str]:
    """``{param_name: raw_default_text}`` -- quotes stripped, everything else verbatim."""

    text = defaults_text.strip()
    if not text:
        return {}
    defaults: dict[str, str] = {}
    for chunk in _split_top_level_commas(text):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = _DEFAULT_ENTRY_RE.match(chunk)
        if match is None:
            raise ValueError(f"unparsable default entry {chunk!r} in {defaults_text!r}")
        name, raw_value = match.groups()
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
            value = value[1:-1]
        defaults[name] = value
    return defaults


def _parse_constraints(constraints_text: str) -> dict[str, str]:
    """``{param_name: bracket_body_text}`` for every ``name: [...]`` entry."""

    return {name: body.strip() for name, body in _CONSTRAINT_ENTRY_RE.findall(constraints_text)}


def _constraint_values(body: str) -> tuple[str, object]:
    """``("range", (low, high))`` when the WHOLE body is one numeric range,
    else ``("enum", [values...])`` from a top-level comma split -- see the
    module docstring for why this single rule also covers ``HsbColor``."""

    range_match = _RANGE_RE.match(body)
    if range_match is not None:
        low_text, high_text = range_match.groups()

        def _num(text: str) -> float | int:
            return float(text) if "." in text else int(text)

        return "range", (_num(low_text), _num(high_text))
    values = [item.strip() for item in body.split(",") if item.strip()]
    if any(":" in item for item in values):
        # A compound ``Name:low-high, ...`` body (HsbColor: "Hue:0-360,
        # Sat:0-100, Bri:0-100") describes the FIELDS of one composite value,
        # not a closed set of legal literals -- rendering it as an enum would
        # steer the model toward emitting "Hue:0-360" as the value. It becomes
        # a free string whose legal shape is stated in the description.
        return "composite", body
    return "enum", values


def _json_type_for(base_type: str) -> tuple[str, str | None]:
    """``(json_schema_type, array_item_json_type_or_None)``."""

    list_match = _LIST_TYPE_RE.match(base_type)
    if list_match is not None:
        return "array", _PRIMITIVE_JSON_TYPES.get(list_match.group(1), "string")
    if base_type == "Map":
        return "object", None
    if base_type in _PRIMITIVE_JSON_TYPES:
        return _PRIMITIVE_JSON_TYPES[base_type], None
    return "string", None  # enum-like custom type (Zone, HvacMode, ...)


def _build_parameter_schema(
    *,
    name: str,
    base_type: str,
    optional: bool,
    defaults: Mapping[str, str],
    constraints: Mapping[str, str],
) -> dict[str, object]:
    json_type, item_json_type = _json_type_for(base_type)
    schema: dict[str, object] = {"type": json_type}
    constraint_body = constraints.get(name)
    if constraint_body and json_type != "boolean":
        kind, value = _constraint_values(constraint_body)
        if json_type == "array":
            items: dict[str, object] = {"type": item_json_type}
            if kind == "range":
                items["minimum"], items["maximum"] = value
            else:
                items["enum"] = value
            schema["items"] = items
        elif kind == "composite":
            pass  # described below, never an enum
        else:
            if kind == "range":
                schema["minimum"], schema["maximum"] = value
            else:
                schema["enum"] = value
    description_bits = [f"type: {base_type}{'?' if optional else ''}"]
    if constraint_body and json_type != "boolean" and _constraint_values(constraint_body)[0] == "composite":
        description_bits.append(f"format: {constraint_body}")
    if name in defaults:
        # Named in the description text ONLY -- never a JSON-schema
        # "default" key (module docstring: Tier 1 is argument-free by the
        # paper's own protocol, so nothing here may be silently auto-filled).
        description_bits.append(f"default: {defaults[name]}")
    schema["description"] = "; ".join(description_bits)
    return schema


def _build_tool_schema(row: Mapping[str, str]) -> dict[str, object]:
    tool_name = row["tool_name"]
    params = _parse_signature(tool_name, row["signature"])
    defaults = _parse_defaults(row["argument_defaults"])
    constraints = _parse_constraints(row["argument_constraints"])
    properties: dict[str, object] = {}
    required: list[str] = []
    for name, base_type, optional in params:
        properties[name] = _build_parameter_schema(
            name=name,
            base_type=base_type,
            optional=optional,
            defaults=defaults,
            constraints=constraints,
        )
        if name not in defaults:
            required.append(name)
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": row["description"],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def render_openai_tools(lock: Mapping[str, object], root: Path) -> list[dict[str, object]]:
    """Every ``tools_registry.csv`` row as an OpenAI-format ``tools`` entry,
    in registry (``tool_id``) order -- the same order
    :func:`~.audio2tool.load_tool_registry` already sorts by. Fail-closed: a
    row whose signature/defaults/constraints cannot be rendered is collected
    (by tool name only, never by leaking row content into an exception
    string beyond the name) and the whole call refuses if any failed, rather
    than silently emitting a partial tool list a real request could then
    send with missing tools.
    """

    rows = load_tool_registry(lock, root)
    tools: list[dict[str, object]] = []
    failures: list[str] = []
    for row in rows:
        try:
            tools.append(_build_tool_schema(row))
        except ValueError:
            failures.append(row["tool_name"])
    if failures:
        raise Audio2ToolSchemaError(
            f"{len(failures)}/{len(rows)} tools_registry.csv rows failed to render an "
            f"OpenAI tool schema: {failures}"
        )
    return tools


def openai_tools_sha256(tools: Sequence[Mapping[str, object]]) -> str:
    """SHA-256 over the canonical (sorted-key, compact) JSON of ``tools``."""

    blob = json.dumps(list(tools), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
