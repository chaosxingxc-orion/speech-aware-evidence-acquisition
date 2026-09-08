"""Gold-free hard-validity checking for Audio2Tool AgentLoop contacts.

This module implements only deterministic, deployment-visible validity checks.
It deliberately excludes semantic confidence, reward, tier identity, expected call
count, and every other training-free decision variable.

WAVE R7 (owner Decision 12-F, 2026-09-08): FOLDED ONTO THE BASE
---------------------------------------------------------------

``HardValidityRepairController`` used to live here -- an ``AgentController``
outside ``rails/controllers.py``, listed by the engineering-base ratchet, that
sequenced a draft contact and a conditional repair contact and branched on
``QueryState.loop_step == 0`` / ``== 1`` to decide which was which. The whole
of that sequencing is now the registered phase program
``phase-hard-validity-repair-v1`` walked by
``rails.controllers.EvidenceAgentController``, built by
``rails.controllers.make_hard_validity_phase_controller``. **The hard-coded
``loop_step`` is gone**: the phase index decides which phase is running, which
is what let W2 relax the observation invariant without this module noticing.

What stayed here is what always belonged here: the pure, deterministic
functions. :func:`validate_hard_validity` is unchanged, byte for byte. The
bounded repair report this module used to seal from inside a controller is now
:func:`hard_validity_repair_state_view`, a registered
``core.base.PHASE_STATE_VIEWS`` entry -- a pure ``(response_text) ->
state_content`` function, so the state the repair contact reads is named,
hashable and config-reachable instead of being a branch nobody could switch
off. The two instruction constants are unchanged and are what the folded
program's material renders.

The module therefore imports nothing from ``rails.knowledge`` or
``rails.runner`` any more, which is what lets ``rails.controllers`` import the
view from here without a cycle.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``validate_hard_validity`` is catalog id
``saea-tool-a2t-hard-validity-v1`` on the ``USE`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from ..reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text

HARD_VALIDITY_POLICY_ID = "hard_validity_v1"
DRAFT_CONTACT_ID = "hard-validity-draft"
REPAIR_CONTACT_ID = "hard-validity-repair"
HARD_VALIDITY_STATE_KIND = "hard-validity-report"
MAX_TOOL_CALLS = 4
MAX_STORED_DRAFT_CHARS = 4096
MAX_SERIALIZED_VIOLATIONS = 16
MAX_AGENT_STATE_UTF8_BYTES = 8192

DRAFT_INSTRUCTION = (
    "Use the original speech and the supplied G3 construction-semantic knowledge "
    "packet. Return only a nonempty JSON array of at most four tool-call objects. "
    'Each object must have exactly the shape {"name": "registeredToolName", '
    '"arguments": {}}. Use registered tool names and their public argument schemas. '
    "Do not explain the answer."
)

REPAIR_INSTRUCTION = (
    "The previous frozen-core draft was hard-invalid under hard_validity_v1. Read "
    "the attached hard-validity report. Repair only the listed JSON, registry, "
    "schema, type, constraint, or duplication failures. Re-evaluate the original "
    "speech using the same supplied G3 knowledge packet. Return only a nonempty "
    "JSON array of at most four tool-call objects with registered tool names and "
    "public argument keys. Do not invent internal tool codes or internal argument "
    "fields. Do not explain the answer."
)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_INTERNAL_CODE = re.compile(r"^[UKP]\d+$")
_SIGNATURE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$")
_PARAMETER = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*"
    r"([A-Za-z_][A-Za-z0-9_]*(?:<[A-Za-z_][A-Za-z0-9_]*>)?)(\?)?$"
)
_CONSTRAINT_CLAUSE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\[([^\]]*)\]")
_NUMBER = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
_RANGE = re.compile(rf"^\s*({_NUMBER})\s*-\s*({_NUMBER})\s*$")


@dataclass(frozen=True)
class _Parameter:
    name: str
    type_name: str


@dataclass(frozen=True)
class _Constraint:
    kind: Literal["enum", "numeric-range", "uncheckable"]
    enum_values: tuple[str, ...] = ()
    numeric_range: tuple[float, float] | None = None


@dataclass(frozen=True)
class _ToolSchema:
    parameters: Mapping[str, _Parameter] | None
    constraints: Mapping[str, _Constraint]


@dataclass(frozen=True)
class HardValidityViolation:
    """One deterministic hard-invalid finding."""

    code: str
    message: str
    call_index: int | None = None
    tool_name: str | None = None
    argument_key: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "call_index": self.call_index,
            "tool_name": self.tool_name,
            "argument_key": self.argument_key,
        }


@dataclass(frozen=True)
class HardValidityReport:
    """The isolated output of ``hard_validity_v1``."""

    status: Literal["valid", "hard-invalid"]
    violations: tuple[HardValidityViolation, ...]
    parsed_call_count: int | None
    policy_id: str = HARD_VALIDITY_POLICY_ID

    def as_json(self) -> dict[str, object]:
        return {
            "policy_id": self.policy_id,
            "status": self.status,
            "parsed_call_count": self.parsed_call_count,
            "violations": [item.as_json() for item in self.violations],
        }


def _parse_signature(tool_name: str, value: object) -> Mapping[str, _Parameter] | None:
    if not isinstance(value, str):
        return None
    matched = _SIGNATURE.fullmatch(value.strip())
    if matched is None or matched.group(1) != tool_name:
        return None
    body = matched.group(2)
    if not body.strip():
        return {}
    parameters: dict[str, _Parameter] = {}
    for raw_parameter in body.split(","):
        parsed = _PARAMETER.fullmatch(raw_parameter.strip())
        if parsed is None:
            return None
        name, type_name, _optional = parsed.groups()
        if name in parameters:
            return None
        parameters[name] = _Parameter(name=name, type_name=type_name)
    return parameters


def _parse_constraints(value: object) -> Mapping[str, _Constraint]:
    if not isinstance(value, str) or not value.strip():
        return {}
    matches = list(_CONSTRAINT_CLAUSE.finditer(value))
    if not matches:
        return {}
    cursor = 0
    for match in matches:
        if value[cursor : match.start()].strip(" ,"):
            return {}
        cursor = match.end()
    if value[cursor:].strip(" ,"):
        return {}

    parsed: dict[str, _Constraint] = {}
    for match in matches:
        name, raw_body = match.groups()
        if name in parsed:
            return {}
        body = raw_body.strip()
        range_match = _RANGE.fullmatch(body)
        if range_match is not None:
            low, high = (float(item) for item in range_match.groups())
            parsed[name] = (
                _Constraint("numeric-range", numeric_range=(low, high))
                if low <= high
                else _Constraint("uncheckable")
            )
        elif ":" in body or not body:
            parsed[name] = _Constraint("uncheckable")
        else:
            choices = tuple(item.strip() for item in body.split(","))
            parsed[name] = (
                _Constraint("enum", enum_values=choices)
                if all(choices)
                else _Constraint("uncheckable")
            )
    return parsed


def _registry_index(
    registry_rows: Sequence[Mapping[str, str]],
) -> Mapping[str, _ToolSchema]:
    indexed: dict[str, _ToolSchema] = {}
    for row in registry_rows:
        tool_name = row.get("tool_name")
        if not isinstance(tool_name, str) or not tool_name:
            raise ValueError("registry row lacks a nonempty tool_name")
        if tool_name in indexed:
            raise ValueError(f"registry has duplicate tool_name {tool_name!r}")
        indexed[tool_name] = _ToolSchema(
            parameters=_parse_signature(tool_name, row.get("signature")),
            constraints=_parse_constraints(row.get("argument_constraints")),
        )
    return indexed


def _payload_has_tool_call_shape(payload: object) -> bool:
    rows = payload if isinstance(payload, list) else [payload]
    return all(
        isinstance(row, Mapping)
        and isinstance(row.get("name"), str)
        and isinstance(row.get("arguments"), Mapping)
        for row in rows
    )


class _DuplicateKeyError(ValueError):
    def __init__(self, key: str):
        super().__init__(key)
        self.key = key


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKeyError(key)
        result[key] = value
    return result


def _selected_duplicate_json_key(text: str) -> str | None:
    """Return a duplicate key in the candidate selected by the shared parser."""

    stripped = text.strip()
    candidates = [match.group(1).strip() for match in _FENCE.finditer(stripped)]
    candidates.append(stripped)
    for candidate in candidates:
        try:
            ordinary = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if not _payload_has_tool_call_shape(ordinary):
            continue
        try:
            json.loads(candidate, object_pairs_hook=_strict_object)
        except _DuplicateKeyError as error:
            return error.key
        return None
    return None


def _type_valid(type_name: str, value: object) -> bool:
    base = type_name.split("<", 1)[0]
    if base == "Boolean":
        return isinstance(value, bool)
    if base == "Int":
        return isinstance(value, int) and not isinstance(value, bool)
    if base == "Float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if base == "List":
        return isinstance(value, list)
    if base == "Map":
        return isinstance(value, Mapping)
    return isinstance(value, str)


def _enum_value(value: object) -> str | None:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _constraint_invalid(spec: _Constraint, value: object) -> bool:
    if spec.kind == "uncheckable":
        return False
    if spec.kind == "enum":
        return _enum_value(value) not in spec.enum_values
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    assert spec.numeric_range is not None
    low, high = spec.numeric_range
    return not low <= float(value) <= high


def _canonical_call(call: ToolCall) -> str:
    return json.dumps(
        {"name": call.name, "arguments": call.arguments},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validate_hard_validity(
    response_text: str,
    registry_rows: Sequence[Mapping[str, str]],
) -> HardValidityReport:
    """Validate only hard deployment-visible conditions, without task labels."""

    if not isinstance(response_text, str):
        raise TypeError("response_text must be a string")
    registry = _registry_index(registry_rows)
    calls, parsed = parse_tool_calls_text(response_text)
    if not parsed:
        return HardValidityReport(
            status="hard-invalid",
            parsed_call_count=None,
            violations=(
                HardValidityViolation(
                    code="json_parse_error",
                    message="The response does not contain a parseable tool-call JSON value.",
                ),
            ),
        )

    violations: list[HardValidityViolation] = []
    duplicate_key = _selected_duplicate_json_key(response_text)
    if duplicate_key is not None:
        violations.append(
            HardValidityViolation(
                code="duplicate_json_key",
                message=f"The selected JSON value repeats key {duplicate_key!r}.",
                argument_key=duplicate_key,
            )
        )
    if not calls:
        violations.append(
            HardValidityViolation(
                code="empty_call_list",
                message="The tool-call list must be nonempty.",
            )
        )
    if len(calls) > MAX_TOOL_CALLS:
        violations.append(
            HardValidityViolation(
                code="too_many_calls",
                message=f"The response has more than the global maximum of {MAX_TOOL_CALLS} calls.",
            )
        )

    seen_calls: set[str] = set()
    for call_index, call in enumerate(calls):
        canonical = _canonical_call(call)
        if canonical in seen_calls:
            violations.append(
                HardValidityViolation(
                    code="duplicate_call",
                    message="The response repeats an identical tool call.",
                    call_index=call_index,
                    tool_name=call.name,
                )
            )
        seen_calls.add(canonical)

        internal_argument_keys = {
            key
            for key in call.arguments
            if key.startswith("_") or _INTERNAL_CODE.fullmatch(key)
        }
        for argument_key in sorted(internal_argument_keys):
            violations.append(
                HardValidityViolation(
                    code="internal_argument_key",
                    message="An internal construction field was used as an argument key.",
                    call_index=call_index,
                    tool_name=call.name,
                    argument_key=argument_key,
                )
            )

        if _INTERNAL_CODE.fullmatch(call.name):
            violations.append(
                HardValidityViolation(
                    code="internal_tool_code",
                    message="An internal construction code was used as a tool name.",
                    call_index=call_index,
                    tool_name=call.name,
                )
            )
            continue
        schema = registry.get(call.name)
        if schema is None:
            violations.append(
                HardValidityViolation(
                    code="unknown_tool_name",
                    message="The tool name is absent from the deployment registry.",
                    call_index=call_index,
                    tool_name=call.name,
                )
            )
            continue
        if schema.parameters is None:
            continue

        for argument_key, value in call.arguments.items():
            if argument_key in internal_argument_keys:
                continue
            parameter = schema.parameters.get(argument_key)
            if parameter is None:
                violations.append(
                    HardValidityViolation(
                        code="unknown_argument_key",
                        message="The argument key is absent from the registered tool schema.",
                        call_index=call_index,
                        tool_name=call.name,
                        argument_key=argument_key,
                    )
                )
                continue
            if not _type_valid(parameter.type_name, value):
                violations.append(
                    HardValidityViolation(
                        code="argument_type_invalid",
                        message=(
                            "The argument value does not match its registered public type "
                            f"{parameter.type_name}."
                        ),
                        call_index=call_index,
                        tool_name=call.name,
                        argument_key=argument_key,
                    )
                )
                continue
            constraint = schema.constraints.get(argument_key)
            if constraint is not None and _constraint_invalid(constraint, value):
                violations.append(
                    HardValidityViolation(
                        code="argument_constraint_invalid",
                        message="The argument value violates a registered public constraint.",
                        call_index=call_index,
                        tool_name=call.name,
                        argument_key=argument_key,
                    )
                )

    return HardValidityReport(
        status="hard-invalid" if violations else "valid",
        violations=tuple(violations),
        parsed_call_count=len(calls),
    )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_repair_state_content(
    report: HardValidityReport,
    response_text: str,
) -> str:
    serialized_violations = report.violations[:MAX_SERIALIZED_VIOLATIONS]
    report_document = {
        "policy_id": report.policy_id,
        "status": report.status,
        "parsed_call_count": report.parsed_call_count,
        "violations": [item.as_json() for item in serialized_violations],
        "omitted_count": len(report.violations) - len(serialized_violations),
    }
    draft_prefix = response_text[:MAX_STORED_DRAFT_CHARS]

    def render(stored_draft: str) -> str:
        return json.dumps(
            {
                "instruction": (
                    "Repair the hard-invalid draft using only these findings."
                ),
                "report": report_document,
                "previous_draft": stored_draft,
                "previous_draft_omitted_chars": len(response_text) - len(stored_draft),
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    content = render(draft_prefix)
    if len(content.encode("utf-8")) <= MAX_AGENT_STATE_UTF8_BYTES:
        return content

    empty_content = render("")
    if len(empty_content.encode("utf-8")) > MAX_AGENT_STATE_UTF8_BYTES:
        raise ValueError(
            "hard-validity repair state exceeds 8192 UTF-8 bytes without draft text"
        )

    low = 0
    high = len(draft_prefix)
    while low < high:
        midpoint = (low + high + 1) // 2
        candidate = render(draft_prefix[:midpoint])
        if len(candidate.encode("utf-8")) <= MAX_AGENT_STATE_UTF8_BYTES:
            low = midpoint
        else:
            high = midpoint - 1
    content = render(draft_prefix[:low])
    if len(content.encode("utf-8")) > MAX_AGENT_STATE_UTF8_BYTES:
        raise ValueError("hard-validity repair state exceeds 8192 UTF-8 bytes")
    return content


#: The registered ``core.base.PHASE_STATE_VIEWS`` id for the bounded repair
#: report. A phase program declaring it seals, as that phase's state, exactly
#: the document ``HardValidityRepairController`` used to seal from inside its
#: own ``advance`` -- same builder, same 8192-byte cap, same binary search over
#: the stored draft prefix, byte for byte.
HARD_VALIDITY_REPAIR_STATE_VIEW_V1 = "a2t-hard-validity-repair-report-v1"


def hard_validity_repair_state_view(
    response_text: str, registry_rows: Sequence[Mapping[str, str]]
) -> str:
    """The bounded repair report for one draft, as sealed state content.

    Pure: it reads the draft text and the pinned registry rows and nothing
    else -- no gold, no sample, no manifest, no network. A VALID draft still
    renders a report (``status: "valid"``, no violations); the folded program
    never reaches this phase-to-phase transition for a valid draft, because its
    stop policy ends the trajectory on the draft itself, exactly as the retired
    controller did.
    """

    report = validate_hard_validity(response_text, registry_rows)
    return _bounded_repair_state_content(report, response_text)


__all__ = [
    "DRAFT_CONTACT_ID",
    "DRAFT_INSTRUCTION",
    "HARD_VALIDITY_POLICY_ID",
    "HARD_VALIDITY_REPAIR_STATE_VIEW_V1",
    "HARD_VALIDITY_STATE_KIND",
    "MAX_AGENT_STATE_UTF8_BYTES",
    "MAX_SERIALIZED_VIOLATIONS",
    "MAX_STORED_DRAFT_CHARS",
    "MAX_TOOL_CALLS",
    "REPAIR_CONTACT_ID",
    "REPAIR_INSTRUCTION",
    "HardValidityReport",
    "HardValidityViolation",
    "hard_validity_repair_state_view",
    "validate_hard_validity",
]
