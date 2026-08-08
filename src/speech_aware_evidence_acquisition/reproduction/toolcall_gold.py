"""Gold-side parsing for the Audio2Tool tier manifests (P1 scaffold): the
deterministic rules that turn one manifest entry's ground-truth fields into
the ``ToolCall`` tuple ``toolcall_scoring.score_item`` expects.

This is the interpretation layer the paper's unreleased eval scripts would
otherwise pin down. The observed manifest shapes it must handle (surveyed
2026-08-08 over the frozen 400-item receipt; the engineering notes record
counts per tier):

- ``expected_tool_call`` is either a call-string (``"setLighting()"``,
  ``"getAirQuality(deviceId='living_room_sensor')"``, sometimes
  domain-dotted: ``"smart_home.setApplianceMode(...)"``) or a BARE name
  (``"setSecurityMode"`` — common in tier3/tier4/tier5/tier8).
- ``extracted_params`` is a flat mapping whose values are mostly strings,
  including JSON-stringified typed values (``"1.0"``, ``'["Weekdays"]'``).
  It can be INCOMPLETE relative to the call-string (tier5 id 2007 carries
  ``deviceId='monitor_1'`` in the call-string but ``{}`` here), so the
  call-string's own kwargs win whenever they parse.
- ``additional_tool_calls`` is ``None``, or a list of strings, each a bare
  name, one call-string, or several call-strings CONCATENATED into one
  string (tier3 id 2560: ``"setTargetTemperature(temperature=68.0)
  setLighting(on=false, ...)"``). Bare additional names have no argument
  record anywhere in the manifest — they parse to ``ToolCall(name, {})``
  and this is a recorded data limitation, not a parser gap.
- ``tool_name`` is the identity authority for the PRIMARY call: it is the
  clean (never dotted) name on every manifest row.

Rules (``a2t-gold-v1`` — any semantic change requires a new constant):

1. Primary call name = the entry's ``tool_name``. Arguments = the first
   parsed call-string segment's kwargs IF that segment's (dot-stripped)
   name equals ``tool_name``; otherwise the JSON-coerced
   ``extracted_params``.
2. Every further segment parsed out of ``expected_tool_call`` and every
   segment of every ``additional_tool_calls`` element becomes its own
   ``ToolCall``; bare names get ``{}``.
3. Call-string kwarg values parse as Python literals
   (``ast.literal_eval``); a non-literal value (bare identifier such as
   ``false`` or ``Driver``) falls back to its source text as a string.
   Positional arguments are not representable in a name->value mapping and
   are dropped (none observed in the survey).
4. ``extracted_params`` string values are JSON-coerced: if the trimmed
   string parses as JSON the parsed value is used (``"1.0"`` -> 1.0,
   ``'["Weekdays"]'`` -> list), otherwise the string is kept verbatim.

Fail-closed: a missing/blank ``tool_name`` or a non-mapping
``extracted_params`` raises :class:`GoldParseError` — gold that cannot be
parsed must never silently score as an empty expectation.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Mapping

from .toolcall_scoring import ToolCall

A2T_GOLD_VERSION = "a2t-gold-v1"

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")


class GoldParseError(RuntimeError):
    """A manifest entry's ground-truth fields cannot be parsed into ToolCalls."""


def coerce_param_value(value: object) -> object:
    """JSON-coerce one ``extracted_params`` value (rule 4 above)."""

    if not isinstance(value, str):
        return value
    try:
        return json.loads(value.strip())
    except (json.JSONDecodeError, ValueError):
        return value


def _matching_paren(text: str, open_index: int) -> int | None:
    """Index of the ``)`` closing ``text[open_index] == '('``, quote-aware;
    ``None`` when unbalanced."""

    depth = 0
    quote: str | None = None
    for index in range(open_index, len(text)):
        char = text[index]
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _parse_kwargs(args_source: str) -> dict[str, object] | None:
    """Parse ``(...)`` argument source into a kwargs dict (rule 3); ``None``
    when the call expression does not parse at all."""

    try:
        tree = ast.parse(f"__gold_call__{args_source}", mode="eval")
    except SyntaxError:
        return None
    node = tree.body
    if not isinstance(node, ast.Call):
        return None
    kwargs: dict[str, object] = {}
    for keyword in node.keywords:
        if keyword.arg is None:  # **spread — not representable, not observed
            continue
        try:
            kwargs[keyword.arg] = ast.literal_eval(keyword.value)
        except (ValueError, SyntaxError, TypeError):
            kwargs[keyword.arg] = ast.unparse(keyword.value)
    return kwargs


def parse_call_segments(text: str) -> list[tuple[str, dict[str, object] | None]]:
    """Split a gold call blob into ``(name, kwargs)`` segments.

    ``kwargs`` is ``None`` for a bare name (no parenthesized argument list —
    the caller decides the fallback), ``{}`` for an explicit zero-argument
    call. Domain-dotted names keep only the final identifier. Handles the
    observed concatenated-call shape by scanning name-by-name.
    """

    segments: list[tuple[str, dict[str, object] | None]] = []
    pos = 0
    while True:
        match = _NAME_RE.search(text, pos)
        if match is None:
            break
        name = match.group(0).rsplit(".", 1)[-1]
        end = match.end()
        if end < len(text) and text[end] == "(":
            close = _matching_paren(text, end)
            if close is None:
                segments.append((name, None))
                break
            segments.append((name, _parse_kwargs(text[end : close + 1])))
            pos = close + 1
        else:
            segments.append((name, None))
            pos = end
    return segments


def _coerced_extracted_params(entry: Mapping[str, object]) -> dict[str, object]:
    raw = entry.get("extracted_params") or {}
    if not isinstance(raw, Mapping):
        raise GoldParseError(
            f"extracted_params must be a mapping or null, got {type(raw).__name__}"
        )
    return {str(key): coerce_param_value(value) for key, value in raw.items()}


def expected_tool_calls_for_entry(entry: Mapping[str, object]) -> tuple[ToolCall, ...]:
    """One manifest entry's full expected ``ToolCall`` tuple (rules 1–4)."""

    tool_name = entry.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise GoldParseError("manifest entry lacks a non-empty tool_name")
    tool_name = tool_name.strip()

    expected_raw = entry.get("expected_tool_call")
    segments = (
        parse_call_segments(expected_raw) if isinstance(expected_raw, str) else []
    )

    primary_args: dict[str, object] | None = None
    extras: list[ToolCall] = []
    for index, (name, kwargs) in enumerate(segments):
        if index == 0:
            if name == tool_name and kwargs is not None:
                primary_args = kwargs
            continue
        extras.append(ToolCall(name=name, arguments=kwargs or {}))
    if primary_args is None:
        primary_args = _coerced_extracted_params(entry)

    calls: list[ToolCall] = [ToolCall(name=tool_name, arguments=primary_args), *extras]

    additional = entry.get("additional_tool_calls") or []
    if not isinstance(additional, (list, tuple)):
        raise GoldParseError(
            f"additional_tool_calls must be a list or null, got {type(additional).__name__}"
        )
    for raw in additional:
        if not isinstance(raw, str):
            raise GoldParseError(
                f"additional_tool_calls elements must be strings, got {type(raw).__name__}"
            )
        for name, kwargs in parse_call_segments(raw):
            calls.append(ToolCall(name=name, arguments=kwargs or {}))
    return tuple(calls)
