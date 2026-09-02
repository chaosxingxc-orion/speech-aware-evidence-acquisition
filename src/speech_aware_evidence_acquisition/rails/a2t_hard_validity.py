"""Gold-free hard-validity repair for Audio2Tool AgentLoop contacts.

This module implements only deterministic, deployment-visible validity checks.
It deliberately excludes semantic confidence, reward, tier identity, expected call
count, and every other training-free decision variable.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Literal, Mapping, Sequence

from ..reproduction.toolcall_scoring import ToolCall, parse_tool_calls_text
from .knowledge import AgentStateArtifact, AgentStepTransition, QueryState
from .runner import (
    AgentContact,
    AgentContactPlan,
    AgentLoopAdvance,
    AgentResponse,
    AgentRuntimeContext,
)

HARD_VALIDITY_POLICY_ID = "hard_validity_v1"
DRAFT_CONTACT_ID = "hard-validity-draft"
REPAIR_CONTACT_ID = "hard-validity-repair"
HARD_VALIDITY_STATE_KIND = "hard-validity-report"
MAX_TOOL_CALLS = 4

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


def _stop(context: AgentRuntimeContext, contact_id: str) -> AgentLoopAdvance:
    return AgentLoopAdvance(
        transition=AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=None,
            action_kind="stop",
            action_target_refs=(),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        ).validate(),
        next_query_state=None,
        new_agent_states=(),
        next_contact=None,
        final_response_contact_id=contact_id,
    )


class HardValidityRepairController:
    """Allow one same-core repair contact after a hard-invalid draft."""

    def __init__(
        self,
        *,
        registry_rows: Sequence[Mapping[str, str]],
        key_representation_id: str,
        matcher_policy_id: str,
        decoding_params: Mapping[str, object],
    ) -> None:
        self._registry_rows = tuple(dict(row) for row in registry_rows)
        _registry_index(self._registry_rows)
        self._key_representation_id = key_representation_id
        self._matcher_policy_id = matcher_policy_id
        self._decoding_params = dict(decoding_params)

    def _contact(
        self,
        state: QueryState,
        *,
        contact_id: str,
        purpose: str,
        instruction: str,
    ) -> AgentContactPlan:
        return AgentContactPlan(
            contact_id=contact_id,
            query_state_sha256=state.content_hash(),
            purpose=purpose,
            instruction=instruction,
            key_representation_id=self._key_representation_id,
            matcher_policy_id=self._matcher_policy_id,
            decoding_params=self._decoding_params,
        ).validate()

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContact:
        if context.query_state.loop_step != 0:
            raise ValueError(
                "hard-validity controller requires loop step zero initially"
            )
        return self._contact(
            context.query_state,
            contact_id=DRAFT_CONTACT_ID,
            purpose="Produce the task tool-call draft from speech and G3 knowledge.",
            instruction=DRAFT_INSTRUCTION,
        )

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContact,
        response_text: AgentResponse,
    ) -> AgentLoopAdvance:
        if not isinstance(contact, AgentContactPlan) or not isinstance(
            response_text, str
        ):
            raise ValueError(
                "hard-validity controller requires one contact and one string response"
            )

        if (
            context.query_state.loop_step == 0
            and contact.contact_id == DRAFT_CONTACT_ID
        ):
            report = validate_hard_validity(response_text, self._registry_rows)
            if report.status == "valid":
                return _stop(context, DRAFT_CONTACT_ID)

            response_sha256 = _sha256_text(response_text)
            state_id = (
                f"state:hard-validity:{context.sample_id}:"
                f"{context.query_state.content_hash()[:12]}"
            )
            state_content = json.dumps(
                {
                    "instruction": "Repair the hard-invalid draft using only these findings.",
                    "report": report.as_json(),
                    "previous_draft": response_text,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            state = AgentStateArtifact(
                state_id=state_id,
                state_kind=HARD_VALIDITY_STATE_KIND,
                content=state_content,
                source_query_state_sha256=context.query_state.content_hash(),
                source_response_sha256=response_sha256,
                producer_policy_id=HARD_VALIDITY_POLICY_ID,
                cited_value_ids=(),
            ).validate()
            next_state = QueryState(
                query_id=context.query_state.query_id,
                query_sample_id=context.query_state.query_sample_id,
                speech_packet_id=context.query_state.speech_packet_id,
                speech_packet_sha256=context.query_state.speech_packet_sha256,
                use_split_identity_hash=context.query_state.use_split_identity_hash,
                loop_step=1,
                visible_facet_ids=context.query_state.visible_facet_ids,
                agent_state_ids=context.query_state.agent_state_ids + (state_id,),
                retrieved_value_ids=context.query_state.retrieved_value_ids,
            ).validate()
            transition = AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=next_state.content_hash(),
                action_kind="organize",
                action_target_refs=(f"agent-state:{state_id}",),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(state_id,),
                dropped_agent_state_ids=(),
            ).validate()
            return AgentLoopAdvance(
                transition=transition,
                next_query_state=next_state,
                new_agent_states=(state,),
                next_contact=self._contact(
                    next_state,
                    contact_id=REPAIR_CONTACT_ID,
                    purpose="Repair one hard-invalid tool-call draft.",
                    instruction=REPAIR_INSTRUCTION,
                ),
            )

        if (
            context.query_state.loop_step == 1
            and contact.contact_id == REPAIR_CONTACT_ID
        ):
            return _stop(context, REPAIR_CONTACT_ID)

        raise ValueError(
            "hard-validity controller received an invalid contact sequence"
        )


__all__ = [
    "DRAFT_CONTACT_ID",
    "DRAFT_INSTRUCTION",
    "HARD_VALIDITY_POLICY_ID",
    "HARD_VALIDITY_STATE_KIND",
    "MAX_TOOL_CALLS",
    "REPAIR_CONTACT_ID",
    "REPAIR_INSTRUCTION",
    "HardValidityRepairController",
    "HardValidityReport",
    "HardValidityViolation",
    "validate_hard_validity",
]
