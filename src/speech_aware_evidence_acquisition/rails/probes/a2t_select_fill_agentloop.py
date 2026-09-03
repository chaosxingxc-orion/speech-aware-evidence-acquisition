"""Fresh one-contact phases for the Audio2Tool SELECT/FILL experiment.

JOINT, SELECT, REVISE, and FILL are deliberately separate OpenJiuwen
workflows.  Only canonical observation state and a verified canonical
predecessor payload may cross a phase boundary; raw responses and cumulative
history are not part of this module's request surface.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import re

from ...core.base import Registry
from ...core.model import FrozenCoreError
from ...core.model.transport import (
    _assert_agent_history_suffix,
    _ordered_speech_feature_content,
    _speech_history_texts,
)
from ..a2t_stage_state import (
    JOINT_DRAFT_STAGE,
    SELECT_STAGE,
    SelectPayload,
    StageStateEnvelope,
)
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..core_client import _agent_history
from ..knowledge import AgentStepTransition
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from ..supply import SupplyPacket
from ..task_adapter import TaskAdapter, TaskSample


JOINT_PHASE = "JOINT_ONE_CALL"
SELECT_PHASE = "SELECT"
REVISE_PHASE = "JOINT_DRAFT_REVISE"
FILL_PHASE = "FILL"
PHASES = (JOINT_PHASE, SELECT_PHASE, REVISE_PHASE, FILL_PHASE)

AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"
SLOT_COUNT = 2
QUEUE_DEPTH = 4
FRESH_DISCOVERY_ROW_COUNT = 104
MAX_CALLS = 7

JOINT_CONTACT_ID = "select-fill-joint"
SELECT_CONTACT_ID = "select-fill-select"
REVISE_CONTACT_ID = "select-fill-revise"
FILL_CONTACT_ID = "select-fill-fill"

_PHASE_CONTACT = {
    JOINT_PHASE: JOINT_CONTACT_ID,
    SELECT_PHASE: SELECT_CONTACT_ID,
    REVISE_PHASE: REVISE_CONTACT_ID,
    FILL_PHASE: FILL_CONTACT_ID,
}
_PHASE_POLICY = {
    JOINT_PHASE: "saea-a2t-select-fill-joint-v1",
    SELECT_PHASE: "saea-a2t-select-fill-select-v1",
    REVISE_PHASE: "saea-a2t-select-fill-revise-v1",
    FILL_PHASE: "saea-a2t-select-fill-fill-v1",
}
_PHASE_PURPOSE = {
    JOINT_PHASE: "jointly-select-and-fill-candidate-calls",
    SELECT_PHASE: "select-ordered-tool-occurrences",
    REVISE_PHASE: "revise-canonical-joint-draft",
    FILL_PHASE: "fill-locked-selected-occurrences",
}
_PREDECESSOR_STAGE = {
    REVISE_PHASE: JOINT_DRAFT_STAGE,
    FILL_PHASE: SELECT_STAGE,
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z", flags=re.ASCII)
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z", flags=re.ASCII)
_SUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "additionalProperties",
        "const",
        "enum",
        "items",
        "maximum",
        "maxItems",
        "minimum",
        "minItems",
        "oneOf",
        "prefixItems",
        "properties",
        "required",
        "type",
    }
)
_JSON_TYPES = frozenset(
    {"array", "boolean", "integer", "null", "number", "object", "string"}
)

_BASE_INSTRUCTION = {
    JOINT_PHASE: (
        "Use the original speech, canonical observation state, and joint "
        "candidate ground. Return only a nonempty JSON array of one to seven "
        "tool-call objects with exactly name and arguments."
    ),
    SELECT_PHASE: (
        "Use the original speech, canonical observation state, and routing "
        "ground. Return only a nonempty JSON array of one to seven ordered "
        "tool-occurrence objects with exactly name. Do not emit arguments."
    ),
    REVISE_PHASE: (
        "Use the original speech, canonical observation state, joint ground, "
        "and the verified canonical draft payload. Revise the complete answer "
        "and return only a nonempty JSON array of one to seven tool-call "
        "objects with exactly name and arguments."
    ),
    FILL_PHASE: (
        "Use the original speech, canonical observation state, selected-only "
        "parameter ground, and the verified canonical selector payload. Keep "
        "the exact occurrence count, positions, and tool names locked. Return "
        "only the JSON call array with exactly name and arguments."
    ),
}


class SelectFillAgentLoopError(RuntimeError):
    """A SELECT/FILL phase input or output violated its frozen contract."""


def _assert_ascii_json(value: object, *, path: str = "value") -> None:
    if value is None or isinstance(value, (bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SelectFillAgentLoopError(f"{path} contains a non-finite number")
        return
    if isinstance(value, str):
        if not value.isascii():
            raise SelectFillAgentLoopError(f"{path} must contain ASCII only")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _assert_ascii_json(item, path=f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise SelectFillAgentLoopError(
                    f"{path} object keys must be ASCII strings"
                )
            _assert_ascii_json(item, path=f"{path}.{key}")
        return
    raise SelectFillAgentLoopError(f"{path} contains a non-JSON value")


def _canonical_json_bytes(value: object) -> bytes:
    _assert_ascii_json(value)
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise SelectFillAgentLoopError("value must be canonical ASCII JSON") from error


def _json_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _require_hash(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SelectFillAgentLoopError(f"{field} must be a lowercase SHA-256")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _load_exact_json(response_text: object, *, label: str) -> object:
    if (
        not isinstance(response_text, str)
        or not response_text
        or not response_text.isascii()
    ):
        raise SelectFillAgentLoopError(f"{label} must be nonempty ASCII JSON")
    try:
        value = json.loads(
            response_text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as error:
        detail = (
            "duplicate JSON key"
            if "duplicate JSON key" in str(error)
            else "invalid JSON"
        )
        raise SelectFillAgentLoopError(f"{label} is {detail}") from error
    _assert_ascii_json(value, path=label)
    return value


def _tool_names(
    value: Sequence[str], *, field: str, maximum: int = 32
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise SelectFillAgentLoopError(f"{field} must be a sequence")
    try:
        names = tuple(value)
    except TypeError as error:
        raise SelectFillAgentLoopError(f"{field} must be a sequence") from error
    if not 1 <= len(names) <= maximum:
        raise SelectFillAgentLoopError(
            f"{field} must contain between 1 and {maximum} names"
        )
    if any(
        not isinstance(name, str) or _TOOL_NAME.fullmatch(name) is None
        for name in names
    ):
        raise SelectFillAgentLoopError(f"{field} must contain ASCII tool names")
    return names


def _call_rows(value: object, *, label: str) -> list[object]:
    if not isinstance(value, list):
        raise SelectFillAgentLoopError(f"{label} must be one JSON array")
    if not 1 <= len(value) <= MAX_CALLS:
        raise SelectFillAgentLoopError(
            f"{label} must contain between 1 and {MAX_CALLS} items"
        )
    return value


def _matches_schema_type(value: object, raw_types: object) -> bool:
    if isinstance(raw_types, str):
        types = (raw_types,)
    elif isinstance(raw_types, list) and raw_types:
        types = tuple(raw_types)
    else:
        raise SelectFillAgentLoopError("response schema type is malformed")
    if any(not isinstance(item, str) or item not in _JSON_TYPES for item in types):
        raise SelectFillAgentLoopError("response schema type is unsupported")
    return any(
        (item == "null" and value is None)
        or (item == "boolean" and isinstance(value, bool))
        or (item == "integer" and isinstance(value, int) and not isinstance(value, bool))
        or (
            item == "number"
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
        or (item == "string" and isinstance(value, str))
        or (item == "array" and isinstance(value, list))
        or (item == "object" and isinstance(value, dict))
        for item in types
    )


def _validate_schema_value(
    value: object, schema: object, *, path: str = "$"
) -> None:
    """Validate the exact schema subset emitted by Audio2Tool builders."""

    if not isinstance(schema, Mapping):
        raise SelectFillAgentLoopError(
            f"response schema at {path} must be one object"
        )
    unknown = set(schema) - _SUPPORTED_SCHEMA_KEYS
    if unknown:
        raise SelectFillAgentLoopError(
            f"response schema at {path} contains unsupported keys {sorted(unknown)!r}"
        )
    if "const" in schema and value != schema["const"]:
        raise SelectFillAgentLoopError(
            f"response schema mismatch at {path}: const"
        )
    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not enum:
            raise SelectFillAgentLoopError(
                f"response schema enum at {path} is malformed"
            )
        if value not in enum:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: enum"
            )
    if "type" in schema and not _matches_schema_type(value, schema["type"]):
        raise SelectFillAgentLoopError(
            f"response schema mismatch at {path}: type"
        )
    if "oneOf" in schema:
        branches = schema["oneOf"]
        if not isinstance(branches, list) or not branches:
            raise SelectFillAgentLoopError(
                f"response schema oneOf at {path} is malformed"
            )
        matches = 0
        for branch in branches:
            try:
                _validate_schema_value(value, branch, path=path)
            except SelectFillAgentLoopError:
                continue
            matches += 1
        if matches != 1:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: oneOf"
            )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: non-finite number"
            )
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and (
            isinstance(minimum, bool)
            or not isinstance(minimum, (int, float))
            or not math.isfinite(float(minimum))
        ):
            raise SelectFillAgentLoopError(
                f"response schema minimum at {path} is malformed"
            )
        if maximum is not None and (
            isinstance(maximum, bool)
            or not isinstance(maximum, (int, float))
            or not math.isfinite(float(maximum))
        ):
            raise SelectFillAgentLoopError(
                f"response schema maximum at {path} is malformed"
            )
        if minimum is not None and value < minimum:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: minimum"
            )
        if maximum is not None and value > maximum:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: maximum"
            )
    if isinstance(value, list):
        minimum_items = schema.get("minItems")
        maximum_items = schema.get("maxItems")
        if minimum_items is not None and (
            isinstance(minimum_items, bool)
            or not isinstance(minimum_items, int)
            or minimum_items < 0
        ):
            raise SelectFillAgentLoopError(
                f"response schema minItems at {path} is malformed"
            )
        if maximum_items is not None and (
            isinstance(maximum_items, bool)
            or not isinstance(maximum_items, int)
            or maximum_items < 0
        ):
            raise SelectFillAgentLoopError(
                f"response schema maxItems at {path} is malformed"
            )
        if minimum_items is not None and len(value) < minimum_items:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: minItems"
            )
        if maximum_items is not None and len(value) > maximum_items:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: maxItems"
            )
        prefix_items = schema.get("prefixItems")
        if prefix_items is not None:
            if not isinstance(prefix_items, list):
                raise SelectFillAgentLoopError(
                    f"response schema prefixItems at {path} is malformed"
                )
            for index, item_schema in enumerate(prefix_items[: len(value)]):
                _validate_schema_value(
                    value[index], item_schema, path=f"{path}[{index}]"
                )
        item_schema = schema.get("items")
        if item_schema is not None:
            start = len(prefix_items) if isinstance(prefix_items, list) else 0
            for index, item in enumerate(value[start:], start=start):
                _validate_schema_value(item, item_schema, path=f"{path}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, Mapping) or not isinstance(required, list):
            raise SelectFillAgentLoopError(
                f"response object schema at {path} is malformed"
            )
        if any(not isinstance(key, str) for key in required):
            raise SelectFillAgentLoopError(
                f"response required keys at {path} are malformed"
            )
        missing = [key for key in required if key not in value]
        if missing:
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: required"
            )
        if schema.get("additionalProperties") is False and not set(value).issubset(
            properties
        ):
            raise SelectFillAgentLoopError(
                f"response schema mismatch at {path}: additionalProperties"
            )
        for key, item in value.items():
            if key in properties:
                _validate_schema_value(item, properties[key], path=f"{path}.{key}")


def _validate_response_format(value: object, response_format: object) -> None:
    if (
        not isinstance(response_format, Mapping)
        or response_format.get("type") != "json_schema"
    ):
        raise SelectFillAgentLoopError(
            "response schema wrapper must use json_schema"
        )
    wrapper = response_format.get("json_schema")
    if (
        not isinstance(wrapper, Mapping)
        or set(wrapper) != {"name", "strict", "schema"}
        or not isinstance(wrapper.get("name"), str)
        or not wrapper["name"]
        or wrapper.get("strict") is not True
    ):
        raise SelectFillAgentLoopError("response schema wrapper is malformed")
    _validate_schema_value(value, wrapper.get("schema"))


@dataclass(frozen=True)
class ExactCall:
    """One parsed call with immutable canonical argument bytes."""

    name: str
    arguments_json: str

    def __post_init__(self) -> None:
        if _TOOL_NAME.fullmatch(self.name) is None:
            raise SelectFillAgentLoopError("call name must be an ASCII tool name")
        arguments = _load_exact_json(self.arguments_json, label="call arguments")
        if not isinstance(arguments, dict):
            raise SelectFillAgentLoopError("call arguments must be one JSON object")
        if self.arguments_json != _canonical_json_bytes(arguments).decode("ascii"):
            raise SelectFillAgentLoopError("call arguments must be canonical JSON")

    @classmethod
    def from_arguments(cls, name: str, arguments: Mapping[str, object]) -> "ExactCall":
        if not isinstance(arguments, Mapping):
            raise SelectFillAgentLoopError("call arguments must be one JSON object")
        return cls(
            name=name, arguments_json=_canonical_json_bytes(arguments).decode("ascii")
        )

    @property
    def arguments(self) -> dict[str, object]:
        value = json.loads(self.arguments_json)
        if not isinstance(value, dict):  # pragma: no cover - constructor invariant
            raise AssertionError("sealed call arguments must remain an object")
        return value

    def as_json(self) -> dict[str, object]:
        return {"name": self.name, "arguments": self.arguments}


def parse_select_response(
    response_text: object,
    *,
    candidate_tool_names: Sequence[str],
) -> tuple[str, ...]:
    """Parse exact argument-free SELECT JSON without extraction or repair."""

    candidates = _tool_names(candidate_tool_names, field="candidate tool names")
    if len(candidates) != len(set(candidates)):
        raise SelectFillAgentLoopError("candidate tool names must be unique")
    rows = _call_rows(
        _load_exact_json(response_text, label="SELECT response"),
        label="SELECT response",
    )
    selected: list[str] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name"}:
            raise SelectFillAgentLoopError(
                "SELECT items must contain exactly the name key"
            )
        name = row["name"]
        if not isinstance(name, str) or name not in candidates:
            raise SelectFillAgentLoopError(
                "SELECT name must be an exact candidate tool name"
            )
        selected.append(name)
    return tuple(selected)


def parse_call_array_response(
    response_text: object,
    *,
    allowed_tool_names: Sequence[str],
    expected_tool_names: Sequence[str] | None = None,
) -> tuple[ExactCall, ...]:
    """Parse an exact nonempty call array, optionally locking positional names."""

    allowed = _tool_names(allowed_tool_names, field="allowed tool names")
    if len(allowed) != len(set(allowed)):
        raise SelectFillAgentLoopError("allowed tool names must be unique")
    expected: tuple[str, ...] | None = None
    if expected_tool_names is not None:
        expected = _tool_names(
            expected_tool_names,
            field="expected tool names",
            maximum=MAX_CALLS,
        )
        if not set(expected).issubset(allowed):
            raise SelectFillAgentLoopError(
                "locked expected names must belong to the allowed tools"
            )
    rows = _call_rows(
        _load_exact_json(response_text, label="call response"), label="call response"
    )
    calls: list[ExactCall] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "arguments"}:
            raise SelectFillAgentLoopError(
                "call items must contain exactly name and arguments"
            )
        name = row["name"]
        arguments = row["arguments"]
        if not isinstance(name, str) or name not in allowed:
            raise SelectFillAgentLoopError(
                "call name must be an exact allowed tool name"
            )
        if not isinstance(arguments, dict):
            raise SelectFillAgentLoopError("call arguments must be one JSON object")
        calls.append(ExactCall.from_arguments(name, arguments))
    names = tuple(call.name for call in calls)
    if expected is not None and names != expected:
        raise SelectFillAgentLoopError(
            "call names and multiplicity differ from the locked occurrence sequence"
        )
    return tuple(calls)


@dataclass(frozen=True)
class PhaseMaterial:
    """Complete immutable material for one fresh model phase."""

    sample_id: str
    phase: str
    candidate_tool_names: tuple[str, ...]
    ground_text: str
    ground_sha256: str
    response_format: Mapping[str, object]
    response_format_sha256: str
    observation_state_json: str
    observation_state_sha256: str
    observation_source_response_sha256: str
    predecessor: StageStateEnvelope | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sample_id, str)
            or not self.sample_id
            or not self.sample_id.isascii()
        ):
            raise SelectFillAgentLoopError("sample_id must be nonempty ASCII")
        if self.phase not in PHASES:
            raise SelectFillAgentLoopError("phase is not a SELECT/FILL phase")
        names = _tool_names(self.candidate_tool_names, field="candidate tool names")
        if len(names) != len(set(names)):
            raise SelectFillAgentLoopError("candidate tool names must be unique")
        object.__setattr__(self, "candidate_tool_names", names)
        if (
            not isinstance(self.ground_text, str)
            or not self.ground_text
            or not self.ground_text.isascii()
        ):
            raise SelectFillAgentLoopError(
                "phase ground must be nonempty ASCII English"
            )
        _require_hash(self.ground_sha256, field="ground_sha256")
        if (
            hashlib.sha256(self.ground_text.encode("ascii")).hexdigest()
            != self.ground_sha256
        ):
            raise SelectFillAgentLoopError("phase ground hash does not match")
        if not isinstance(self.response_format, Mapping):
            raise SelectFillAgentLoopError("response_format must be a mapping")
        response_copy = json.loads(_canonical_json_bytes(self.response_format))
        object.__setattr__(self, "response_format", response_copy)
        _require_hash(self.response_format_sha256, field="response_format_sha256")
        if _json_hash(response_copy) != self.response_format_sha256:
            raise SelectFillAgentLoopError("response_format hash does not match")
        if (
            not isinstance(self.observation_state_json, str)
            or not self.observation_state_json.isascii()
        ):
            raise SelectFillAgentLoopError(
                "observation state must be canonical ASCII JSON"
            )
        observation = _load_exact_json(
            self.observation_state_json, label="observation state"
        )
        if not isinstance(
            observation, dict
        ) or self.observation_state_json != _canonical_json_bytes(observation).decode(
            "ascii"
        ):
            raise SelectFillAgentLoopError("observation state must be canonical JSON")
        _require_hash(self.observation_state_sha256, field="observation_state_sha256")
        if _json_hash(observation) != self.observation_state_sha256:
            raise SelectFillAgentLoopError("observation state hash does not match")
        _require_hash(
            self.observation_source_response_sha256,
            field="observation_source_response_sha256",
        )
        required_stage = _PREDECESSOR_STAGE.get(self.phase)
        if required_stage is None:
            if self.predecessor is not None:
                raise SelectFillAgentLoopError(
                    "JOINT and SELECT phases forbid predecessor state"
                )
            return
        if (
            not isinstance(self.predecessor, StageStateEnvelope)
            or self.predecessor.stage != required_stage
        ):
            raise SelectFillAgentLoopError(
                f"{self.phase} requires a verified {required_stage} predecessor"
            )
        predecessor = self.predecessor
        predecessor.to_json()  # Re-run all envelope invariants before accepting it.
        if (
            predecessor.sample_identity_sha256
            != hashlib.sha256(self.sample_id.encode("ascii")).hexdigest()
        ):
            raise SelectFillAgentLoopError("predecessor sample identity does not match")
        if predecessor.observation_state_sha256 != self.observation_state_sha256:
            raise SelectFillAgentLoopError(
                "predecessor observation state does not match"
            )
        if (
            predecessor.observation_source_response_sha256
            != self.observation_source_response_sha256
        ):
            raise SelectFillAgentLoopError(
                "predecessor observation source response does not match"
            )
        if predecessor.candidate_set_sha256 != _json_hash(list(names)):
            raise SelectFillAgentLoopError(
                "predecessor candidate ordering does not match"
            )

    @property
    def expected_tool_names(self) -> tuple[str, ...] | None:
        if self.phase != FILL_PHASE:
            return None
        predecessor = self.predecessor
        if predecessor is None or not isinstance(predecessor.payload, SelectPayload):
            raise SelectFillAgentLoopError(
                "FILL predecessor payload is not SELECT state"
            )
        return tuple(item.tool_name for item in predecessor.payload.occurrences)


def _predecessor_json(material: PhaseMaterial) -> str | None:
    predecessor = material.predecessor
    if predecessor is None:
        return None
    return _canonical_json_bytes(
        {
            "stage": predecessor.stage,
            "envelope_sha256": predecessor.envelope_sha256,
            "payload": predecessor.payload.as_json(),
            "payload_sha256": predecessor.payload_sha256,
            "source_request_body_sha256": predecessor.source_request_body_sha256,
        }
    ).decode("ascii")


def _contact_instruction(material: PhaseMaterial) -> str:
    sections = [
        _BASE_INSTRUCTION[material.phase],
        "Canonical observation state:",
        material.observation_state_json,
    ]
    predecessor = _predecessor_json(material)
    if predecessor is not None:
        sections.extend(("Verified canonical predecessor state:", predecessor))
    instruction = "\n".join(sections)
    if not instruction.isascii():  # pragma: no cover - component invariants
        raise SelectFillAgentLoopError("phase instruction must remain ASCII")
    return instruction


@dataclass(frozen=True)
class RenderedPhaseRequest:
    """Exact rails and transport surfaces for whole-phase preflight."""

    phase: str
    prompt_order: str
    rails_messages: tuple[Mapping[str, object], ...]
    contact_instruction: str
    response_format: Mapping[str, object]
    decoding_params: Mapping[str, object]
    history: tuple[Mapping[str, object], ...]
    rails_envelope: Mapping[str, object]
    rails_envelope_ascii_bytes: int
    rails_envelope_sha256: str
    transport_messages: tuple[Mapping[str, object], ...]
    transport_messages_ascii_bytes: int
    transport_messages_sha256: str
    request_body: Mapping[str, object]
    request_body_ascii_bytes: int
    request_body_sha256: str


def render_phase_request(
    material: PhaseMaterial,
    speech_packet_binding: Mapping[str, object],
    *,
    prompt_order: str,
    decoding_params: Mapping[str, object] | None = None,
) -> RenderedPhaseRequest:
    """Purely render one exact request before any phase contact is allowed."""

    if not isinstance(material, PhaseMaterial):
        raise SelectFillAgentLoopError("request rendering requires PhaseMaterial")
    if not isinstance(speech_packet_binding, Mapping) or set(speech_packet_binding) != {
        "packet_id",
        "sha256",
    }:
        raise SelectFillAgentLoopError("speech packet binding keys are malformed")
    packet_id = speech_packet_binding["packet_id"]
    packet_sha256 = speech_packet_binding["sha256"]
    if (
        not isinstance(packet_id, str)
        or not packet_id
        or not packet_id.isascii()
        or not isinstance(packet_sha256, str)
        or _SHA256.fullmatch(packet_sha256) is None
    ):
        raise SelectFillAgentLoopError("speech packet binding values are malformed")
    if (
        material.predecessor is not None
        and material.predecessor.speech_packet_sha256 != packet_sha256
    ):
        raise SelectFillAgentLoopError(
            "speech packet lineage does not match predecessor"
        )
    if decoding_params is None:
        decode = {}
    elif not isinstance(decoding_params, Mapping):
        raise SelectFillAgentLoopError("decoding_params must be a mapping")
    else:
        decode = dict(decoding_params)
    if "response_format" in decode:
        raise SelectFillAgentLoopError(
            "decoding_params must leave response_format to PhaseMaterial"
        )
    _assert_ascii_json(decode, path="decoding_params")
    effective_decode = {**decode, "response_format": material.response_format}
    feature = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": packet_id,
            "sha256": packet_sha256,
            "role": "query",
        },
    }
    rails_messages: tuple[Mapping[str, object], ...] = (
        {"role": "system", "content": material.ground_text},
        {"role": "user", "content": [feature]},
    )
    instruction = _contact_instruction(material)
    history = tuple(
        _agent_history(
            agent_state=(),
            agent_contact_id=_PHASE_CONTACT[material.phase],
            contact_instruction=instruction,
        )
    )
    rails_envelope: Mapping[str, object] = {
        "messages": rails_messages,
        "agent_state": [],
        "agent_contact_id": _PHASE_CONTACT[material.phase],
        "contact_instruction": instruction,
        "response_format": material.response_format,
    }
    try:
        state_texts = _speech_history_texts(list(history))
        ordered_content = _ordered_speech_feature_content(
            prompt_order=prompt_order,
            evidence_texts=[],
            feature_parts=[feature],
            state_texts=state_texts,
            knowledge_roles=(),
        )
        _assert_agent_history_suffix(
            prompt_order=prompt_order,
            content=ordered_content,
            state_texts=state_texts,
        )
    except FrozenCoreError as error:
        raise SelectFillAgentLoopError(
            f"unsupported or invalid transport prompt order: {error}"
        ) from error
    transport_messages: tuple[Mapping[str, object], ...] = (
        {"role": "system", "content": material.ground_text},
        {"role": "user", "content": ordered_content},
    )
    request_body: Mapping[str, object] = {
        "messages": transport_messages,
        "decoding_params": effective_decode,
        "phase": material.phase,
    }
    rails_bytes = _canonical_json_bytes(rails_envelope)
    transport_bytes = _canonical_json_bytes(transport_messages)
    request_bytes = _canonical_json_bytes(request_body)
    return RenderedPhaseRequest(
        phase=material.phase,
        prompt_order=prompt_order,
        rails_messages=rails_messages,
        contact_instruction=instruction,
        response_format=material.response_format,
        decoding_params=effective_decode,
        history=history,
        rails_envelope=rails_envelope,
        rails_envelope_ascii_bytes=len(rails_bytes),
        rails_envelope_sha256=hashlib.sha256(rails_bytes).hexdigest(),
        transport_messages=transport_messages,
        transport_messages_ascii_bytes=len(transport_bytes),
        transport_messages_sha256=hashlib.sha256(transport_bytes).hexdigest(),
        request_body=request_body,
        request_body_ascii_bytes=len(request_bytes),
        request_body_sha256=hashlib.sha256(request_bytes).hexdigest(),
    )


class FreshSelectFillPhaseAdapter(TaskAdapter):
    """In-memory, score-deferred adapter for any one fresh experiment phase."""

    def __init__(
        self,
        *,
        split_id: str,
        samples: Sequence[TaskSample],
        phase: str,
        material: Mapping[str, PhaseMaterial],
    ) -> None:
        if not isinstance(split_id, str) or not split_id or not split_id.isascii():
            raise SelectFillAgentLoopError("split_id must be nonempty ASCII")
        if phase not in PHASES:
            raise SelectFillAgentLoopError("adapter phase is unknown")
        rows = tuple(samples)
        sample_ids = tuple(getattr(sample, "sample_id", None) for sample in rows)
        if (
            not rows
            or any(
                not isinstance(sample_id, str) or not sample_id
                for sample_id in sample_ids
            )
            or len(set(sample_ids)) != len(sample_ids)
        ):
            raise SelectFillAgentLoopError("phase samples need unique nonempty ids")
        material_by_id = dict(material)
        if set(material_by_id) != set(sample_ids):
            raise SelectFillAgentLoopError("phase material must cover samples exactly")
        for sample_id, item in material_by_id.items():
            if (
                not isinstance(item, PhaseMaterial)
                or item.sample_id != sample_id
                or item.phase != phase
            ):
                raise SelectFillAgentLoopError(
                    "phase material sample or phase binding does not match"
                )
        self.split_id = split_id
        self.phase = phase
        self.samples = rows
        self.sample_ids = tuple(sample_ids)
        self.material = material_by_id

    def load_split(self, split_id: str) -> tuple[TaskSample, ...]:
        if split_id != self.split_id:
            raise SelectFillAgentLoopError("phase adapter split identity drift")
        return self.samples

    def build_task_contract(self, sample: TaskSample, obs: object) -> str:
        del obs
        try:
            return self.material[sample.sample_id].ground_text
        except (AttributeError, KeyError) as error:
            raise SelectFillAgentLoopError(
                "sample is outside phase material"
            ) from error

    def assemble_prompt(
        self, sample: TaskSample, supply: SupplyPacket | None
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise SelectFillAgentLoopError("phase adapter rejects untraced supply")
        return (
            {"role": "system", "content": self.build_task_contract(sample, None)},
            {"role": "user", "content": []},
        )

    def score(self, sample: TaskSample, response: str) -> Mapping[str, object]:
        del sample, response
        return {"scoring_deferred": True}

    def extract_consumption(
        self,
        sample: TaskSample,
        supply: SupplyPacket | None,
        response: str,
    ) -> ConsumptionTrace:
        del sample
        return build_consumption_trace(
            span_id=f"select-fill-{self.phase.casefold()}",
            supply=supply,
            response_text=response,
        )

    def render_request(
        self,
        sample_id: str,
        speech_packet_binding: Mapping[str, object],
        *,
        prompt_order: str,
        decoding_params: Mapping[str, object] | None = None,
    ) -> RenderedPhaseRequest:
        try:
            item = self.material[sample_id]
        except KeyError as error:
            raise SelectFillAgentLoopError(
                "request sample is outside phase material"
            ) from error
        return render_phase_request(
            item,
            speech_packet_binding,
            prompt_order=prompt_order,
            decoding_params=decoding_params,
        )


class SingleContactPhaseController:
    """Exactly one fresh contact for JOINT, SELECT, REVISE, or FILL."""

    def __init__(self, *, material: PhaseMaterial) -> None:
        if not isinstance(material, PhaseMaterial):
            raise SelectFillAgentLoopError("controller requires PhaseMaterial")
        self.material = material
        self.parsed_response: tuple[str, ...] | tuple[ExactCall, ...] | None = None

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if (
            context.sample_id != self.material.sample_id
            or context.query_state.loop_step != 0
            or context.contact_index != 0
            or context.agent_states
            or context.prior_response_sha256s
            or context.query_state.retrieved_value_ids
        ):
            raise SelectFillAgentLoopError(
                "phase requires a fresh step-zero context with no cumulative history"
            )
        if (
            self.material.predecessor is not None
            and context.query_state.speech_packet_sha256
            != self.material.predecessor.speech_packet_sha256
        ):
            raise SelectFillAgentLoopError("phase speech packet lineage drift")
        return AgentContactPlan(
            contact_id=_PHASE_CONTACT[self.material.phase],
            query_state_sha256=context.query_state.content_hash(),
            purpose=_PHASE_PURPOSE[self.material.phase],
            instruction=_contact_instruction(self.material),
            key_representation_id=f"{_PHASE_POLICY[self.material.phase]}:speech",
            matcher_policy_id=_PHASE_POLICY[self.material.phase],
            decoding_params={
                "temperature": 0,
                "response_format": self.material.response_format,
            },
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if (
            not isinstance(contact, AgentContactPlan)
            or context.sample_id != self.material.sample_id
            or context.query_state.loop_step != 0
            or context.contact_index != 0
            or contact.contact_id != _PHASE_CONTACT[self.material.phase]
            or contact.query_state_sha256 != context.query_state.content_hash()
        ):
            raise SelectFillAgentLoopError("invalid single-contact phase sequence")
        parsed_json = _load_exact_json(response_text, label="phase response")
        _validate_response_format(parsed_json, self.material.response_format)
        if self.material.phase == SELECT_PHASE:
            parsed: tuple[str, ...] | tuple[ExactCall, ...] = parse_select_response(
                response_text,
                candidate_tool_names=self.material.candidate_tool_names,
            )
        else:
            parsed = parse_call_array_response(
                response_text,
                allowed_tool_names=self.material.candidate_tool_names,
                expected_tool_names=self.material.expected_tool_names,
            )
        self.parsed_response = parsed
        transition = AgentStepTransition(
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
        ).validate()
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=contact.contact_id,
        )


def run_phase(
    *,
    phase: str,
    data_root: object,
    plan: object,
    adapter: FreshSelectFillPhaseAdapter,
    core_client: object,
    split_id: str,
    knowledge_snapshot: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    decoding_params: Mapping[str, object],
    expected_row_count: int = FRESH_DISCOVERY_ROW_COUNT,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Run one complete, prospectively sized phase with fixed concurrency."""

    if phase not in PHASES:
        raise SelectFillAgentLoopError("run phase is unknown")
    if (
        not isinstance(adapter, FreshSelectFillPhaseAdapter)
        or adapter.phase != phase
        or adapter.split_id != split_id
    ):
        raise SelectFillAgentLoopError("run phase requires its matching fresh adapter")
    if (
        isinstance(expected_row_count, bool)
        or not isinstance(expected_row_count, int)
        or expected_row_count <= 0
    ):
        raise SelectFillAgentLoopError(
            "expected row count must be a positive integer"
        )
    if (
        len(adapter.sample_ids) != expected_row_count
        or len(speech_packet_bindings) != expected_row_count
    ):
        raise SelectFillAgentLoopError(
            f"fresh phase requires exactly {expected_row_count} samples"
        )
    if set(adapter.sample_ids) != set(speech_packet_bindings):
        raise SelectFillAgentLoopError(
            "speech packet and phase sample identities differ"
        )
    if not isinstance(decoding_params, Mapping) or "response_format" in decoding_params:
        raise SelectFillAgentLoopError(
            "run decoding parameters must leave response_format per sample"
        )
    controller_registry = Registry("fresh SELECT/FILL phase controller")
    controller_registry.register(
        _PHASE_POLICY[phase],
        lambda sample_id: SingleContactPhaseController(
            material=adapter.material[sample_id]
        ),
    )
    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=split_id,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        controller_policy_id=_PHASE_POLICY[phase],
        max_contacts=1,
        slot_count=SLOT_COUNT,
        queue_depth=QUEUE_DEPTH,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params=decoding_params,
        controller_registry=controller_registry,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise SelectFillAgentLoopError(
            "phase summary is not bound to openjiuwen-workflow-v1"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != expected_row_count:
        raise SelectFillAgentLoopError(
            f"phase must return exactly {expected_row_count} results"
        )
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise SelectFillAgentLoopError("phase result lacks a sample identity")
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise SelectFillAgentLoopError(
                "every fresh phase result must contain exactly one contact"
            )
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids) or set(result_ids) != set(
        adapter.sample_ids
    ):
        raise SelectFillAgentLoopError(
            "phase result identities differ from fresh samples"
        )
    return summary


__all__ = [
    "AGENT_EXECUTOR_ID",
    "FILL_CONTACT_ID",
    "FILL_PHASE",
    "FRESH_DISCOVERY_ROW_COUNT",
    "JOINT_CONTACT_ID",
    "JOINT_PHASE",
    "MAX_CALLS",
    "PHASES",
    "QUEUE_DEPTH",
    "REVISE_CONTACT_ID",
    "REVISE_PHASE",
    "SELECT_CONTACT_ID",
    "SELECT_PHASE",
    "SLOT_COUNT",
    "ExactCall",
    "FreshSelectFillPhaseAdapter",
    "PhaseMaterial",
    "RenderedPhaseRequest",
    "SelectFillAgentLoopError",
    "SingleContactPhaseController",
    "parse_call_array_response",
    "parse_select_response",
    "render_phase_request",
    "run_phase",
]
