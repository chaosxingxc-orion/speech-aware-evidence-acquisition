"""Bind a historical native tool call to the exact source request authority."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence

from .core_client import CoreCompletion, _tool_schemas_sha256
from .errors import RailsError
from .hashing import content_hash

AUTHORITY_SCHEMA = "saea-native-tool-source-authority-v1"


class NativeToolAuthorityError(RailsError):
    """A purported source authority differs from its metered completion."""


def _digest(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(c in "0123456789abcdef" for c in value)
    )


def _plain(value: object) -> object:
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise NativeToolAuthorityError(
                "native authority JSON object keys must be strings"
            )
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise NativeToolAuthorityError("native authority contains a non-JSON value")


def _schemas(value: object) -> tuple[list[dict[str, object]], list[str], str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise NativeToolAuthorityError(
            "selected tool schemas must be a nonempty sequence"
        )
    schemas = _plain(list(value))
    if not isinstance(schemas, list) or any(
        not isinstance(item, dict) for item in schemas
    ):
        raise NativeToolAuthorityError("selected tool schemas must contain objects")
    names = []
    for schema in schemas:
        function = schema.get("function")
        name = function.get("name") if isinstance(function, Mapping) else None
        if schema.get("type") != "function" or not isinstance(name, str) or not name:
            raise NativeToolAuthorityError("selected tool schema lacks a function name")
        names.append(name)
    if len(names) != len(set(names)):
        raise NativeToolAuthorityError("selected tool schema names must be unique")
    return schemas, names, _tool_schemas_sha256(schemas)


def select_completion_tool_schemas(
    completion: CoreCompletion,
    registered_tool_schemas: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    """Select exact registered schemas in the actual per-contact payload order."""
    schemas, names, _schemas_sha = _schemas(registered_tool_schemas)
    actual_names = completion.tool_names
    if (
        not isinstance(actual_names, tuple)
        or not actual_names
        or any(not isinstance(name, str) or not name for name in actual_names)
        or len(set(actual_names)) != len(actual_names)
    ):
        raise NativeToolAuthorityError(
            "native completion tool names must be nonempty, ordered, and unique"
        )
    by_name = dict(zip(names, schemas, strict=True))
    if any(name not in by_name for name in actual_names):
        raise NativeToolAuthorityError(
            "native completion names an unregistered source tool schema"
        )
    selected = tuple(by_name[name] for name in actual_names)
    if _tool_schemas_sha256(selected) != completion.tool_schemas_sha256:
        raise NativeToolAuthorityError(
            "selected source schemas differ from the actual request payload"
        )
    return selected


def _completion_identity(document: Mapping[str, object]) -> dict[str, object]:
    return {
        key: document[key]
        for key in (
            "request_id",
            "sample_id",
            "agent_contact_id",
            "source_request_sha256",
            "source_response_sha256",
            "source_response_text_sha256",
            "source_tool_calls_sha256",
            "source_finish_reason",
            "selected_tool_names",
            "selected_tool_schemas_sha256",
            "original_assistant_message_sha256",
        )
    }


def validate_native_tool_authority(authority: object) -> dict[str, object]:
    """Return an independent validated authority document."""
    if not isinstance(authority, Mapping):
        raise NativeToolAuthorityError("native source authority must be an object")
    document = _plain(authority)
    assert isinstance(document, dict)
    required = {
        "schema",
        "role_id",
        "phase_id",
        "request_id",
        "sample_id",
        "agent_contact_id",
        "source_request_sha256",
        "source_response_sha256",
        "source_response_text_sha256",
        "source_tool_calls_sha256",
        "source_finish_reason",
        "selected_tool_names",
        "selected_tool_schemas",
        "selected_tool_schemas_sha256",
        "original_assistant_message",
        "original_assistant_message_sha256",
        "completion_sha256",
    }
    if set(document) != required or document.get("schema") != AUTHORITY_SCHEMA:
        raise NativeToolAuthorityError(
            "native source authority has the wrong schema fields"
        )
    for field in (
        "role_id",
        "phase_id",
        "request_id",
        "sample_id",
        "agent_contact_id",
        "source_finish_reason",
    ):
        if not isinstance(document[field], str) or not document[field]:
            raise NativeToolAuthorityError(
                f"native source authority {field} is missing"
            )
    for field in (
        "source_request_sha256",
        "source_response_sha256",
        "source_response_text_sha256",
        "source_tool_calls_sha256",
        "selected_tool_schemas_sha256",
        "original_assistant_message_sha256",
        "completion_sha256",
    ):
        if not _digest(document[field]):
            raise NativeToolAuthorityError(
                f"native source authority {field} is not SHA-256"
            )
    schemas, names, schemas_sha = _schemas(document["selected_tool_schemas"])
    if (
        document["selected_tool_names"] != names
        or document["selected_tool_schemas_sha256"] != schemas_sha
    ):
        raise NativeToolAuthorityError(
            "native source authority selected schema identity changed"
        )
    message = document["original_assistant_message"]
    if (
        not isinstance(message, dict)
        or message.get("role") != "assistant"
        or (
            message.get("content") is not None
            and not isinstance(message.get("content"), (str, list))
        )
    ):
        raise NativeToolAuthorityError(
            "native source authority assistant message is invalid"
        )
    if document["source_finish_reason"] != "tool_calls":
        raise NativeToolAuthorityError(
            "native source authority finish reason does not authorize tool calls"
        )
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or not calls:
        raise NativeToolAuthorityError(
            "native source authority assistant message lacks calls"
        )
    calls_blob = json.dumps(
        calls, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if hashlib.sha256(calls_blob).hexdigest() != document["source_tool_calls_sha256"]:
        raise NativeToolAuthorityError("native source authority call bytes changed")
    if any(
        not isinstance(call, dict)
        or not isinstance(call.get("function"), dict)
        or call["function"].get("name") not in names
        for call in calls
    ):
        raise NativeToolAuthorityError(
            "native source authority call is outside its source scope"
        )
    if content_hash(message) != document["original_assistant_message_sha256"]:
        raise NativeToolAuthorityError(
            "native source authority assistant message changed"
        )
    if content_hash(_completion_identity(document)) != document["completion_sha256"]:
        raise NativeToolAuthorityError(
            "native source authority completion identity changed"
        )
    document["selected_tool_schemas"] = schemas
    return document


def build_native_tool_authority(
    completion: CoreCompletion,
    *,
    role_id: str,
    phase_id: str,
    selected_tool_schemas: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Build authority from one real source-bound completion and selected schemas."""
    if not isinstance(completion, CoreCompletion):
        raise NativeToolAuthorityError(
            "native source authority requires CoreCompletion"
        )
    if (
        not isinstance(role_id, str)
        or not role_id
        or not isinstance(phase_id, str)
        or not phase_id
    ):
        raise NativeToolAuthorityError(
            "native source authority requires role and phase IDs"
        )
    schemas, names, schemas_sha = _schemas(selected_tool_schemas)
    if (
        completion.tool_names != tuple(names)
        or completion.tool_schemas_sha256 != schemas_sha
    ):
        raise NativeToolAuthorityError(
            "selected schemas differ from the actual request payload"
        )
    if (
        not isinstance(completion.agent_contact_id, str)
        or not completion.agent_contact_id
    ):
        raise NativeToolAuthorityError("native completion lacks a contact identity")
    for digest in (
        completion.request_sha256,
        completion.response_sha256,
        completion.response_text_sha256,
    ):
        if not _digest(digest):
            raise NativeToolAuthorityError(
                "native completion contains an invalid source hash"
            )
    try:
        completion.assert_binding(
            sample_id=completion.sample_id,
            agent_contact_id=completion.agent_contact_id,
            response_text=completion.text,
        )
        calls = completion.tool_calls
        message = completion.original_message
        finish_reason = completion.finish_reason
    except Exception as error:
        raise NativeToolAuthorityError(
            "native completion wire metadata is invalid"
        ) from error
    if finish_reason != "tool_calls":
        raise NativeToolAuthorityError(
            "native completion finish reason does not authorize tool calls"
        )
    if message is None:
        raise NativeToolAuthorityError(
            "native completion lacks original assistant metadata"
        )
    plain_message = _plain(message)
    if not isinstance(plain_message, dict) or plain_message.get("tool_calls") != calls:
        raise NativeToolAuthorityError(
            "native completion call metadata disagrees with original assistant"
        )
    raw_calls = json.dumps(
        calls, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    if raw_calls != completion.tool_calls_json:
        raise NativeToolAuthorityError("native completion call bytes are not canonical")
    document = {
        "schema": AUTHORITY_SCHEMA,
        "role_id": role_id,
        "phase_id": phase_id,
        "request_id": completion.request_id,
        "sample_id": completion.sample_id,
        "agent_contact_id": completion.agent_contact_id,
        "source_request_sha256": completion.request_sha256,
        "source_response_sha256": completion.response_sha256,
        "source_response_text_sha256": completion.response_text_sha256,
        "source_tool_calls_sha256": completion.tool_calls_sha256,
        "source_finish_reason": finish_reason,
        "selected_tool_names": names,
        "selected_tool_schemas": schemas,
        "selected_tool_schemas_sha256": schemas_sha,
        "original_assistant_message": plain_message,
        "original_assistant_message_sha256": content_hash(plain_message),
    }
    document["completion_sha256"] = content_hash(_completion_identity(document))
    return validate_native_tool_authority(document)


MULTIPLE_CALL_REJECTION_SCHEMA = "saea-phase-tool-rejection-v1"


def multiple_call_rejection_result(count: int) -> dict[str, object]:
    """Describe a rejected selection, never an executed tool or new evidence."""
    if not isinstance(count, int) or isinstance(count, bool) or count < 2:
        raise NativeToolAuthorityError("batch rejection requires multiple calls")
    return {
        "status": "rejected",
        "error_code": "multiple-tool-calls",
        "message": (
            "No requested tool was executed. Select at most one tool call "
            "in a model turn, or provide the required final report."
        ),
        "tool_call_count": count,
        "lookup_performed": False,
    }


def episode_call_limit_rejection_result(count: int) -> dict[str, object]:
    """Return auditable exhausted-budget feedback without executing a tool."""
    if isinstance(count, bool) or not isinstance(count, int) or count != 1:
        raise NativeToolAuthorityError("episode limit rejection requires one call")
    return {"status": "rejected", "error_code": "episode-tool-call-limit",
            "message": "The episode tool call limit is exhausted. Use existing evidence or accept the current answer.",
            "tool_call_count": count, "lookup_performed": False}


def invalid_arguments_rejection_result(count: int) -> dict[str, object]:
    """Describe a schema-refused call; no tool or evidence was produced."""
    if isinstance(count, bool) or not isinstance(count, int) or count != 1:
        raise NativeToolAuthorityError("argument rejection requires one call")
    return {"status": "rejected", "error_code": "invalid-tool-arguments",
            "message": "No tool was executed. Use arguments matching the advertised schema or provide the required final report.",
            "tool_call_count": count, "lookup_performed": False}


def validate_native_call_rejection(document):
    """Validate one rejected call while retaining the entire original batch."""
    if not isinstance(document, Mapping):
        raise NativeToolAuthorityError("native call rejection must be an object")
    limit_rejection = isinstance(document.get("result"), Mapping) and document["result"].get("error_code") == "episode-tool-call-limit"
    argument_rejection = isinstance(document.get("result"), Mapping) and document["result"].get("error_code") == "invalid-tool-arguments"
    authority = validate_native_tool_authority(document.get("source_authority"))
    calls = authority["original_assistant_message"].get("tool_calls")
    raw = document.get("native_tool_calls_json")
    try:
        parsed_calls = json.loads(raw) if isinstance(raw, str) else None
    except ValueError as error:
        raise NativeToolAuthorityError("native rejected call bytes are malformed") from error
    if (
        document.get("schema") != MULTIPLE_CALL_REJECTION_SCHEMA
        or document.get("selection_mode") != "native-tools"
        or "tool_invocation" in document
        or not isinstance(calls, list) or len(calls) < (1 if limit_rejection or argument_rejection else 2)
        or not isinstance(raw, str)
        or hashlib.sha256(raw.encode()).hexdigest() != authority["source_tool_calls_sha256"]
        or parsed_calls != calls
        or document.get("tool_calls_sha256") != authority["source_tool_calls_sha256"]
        or document.get("source_authority_sha256") != content_hash(authority)
        or document.get("source_response_sha256") != authority["source_response_text_sha256"]
        or document.get("core_request_id") != authority["request_id"]
        or document.get("sample_id") != authority["sample_id"]
        or document.get("phase") != authority["phase_id"]
        or document.get("next_phase") != authority["phase_id"]
        or authority["role_id"] != authority["phase_id"]
    ):
        raise NativeToolAuthorityError("native batch rejection source differs")
    call_ids, parsed = [], {}
    for call in calls:
        function = call.get("function") if isinstance(call, Mapping) else None
        if (
            not isinstance(call, Mapping) or set(call) != {"id", "type", "function"}
            or call.get("type") != "function"
            or not isinstance(call.get("id"), str) or not call["id"]
            or call["id"] in call_ids
            or not isinstance(function, Mapping) or set(function) != {"name", "arguments"}
            or function.get("name") not in authority["selected_tool_names"]
            or not isinstance(function.get("arguments"), str)
        ):
            raise NativeToolAuthorityError("native batch rejection call shape differs")
        try:
            arguments = json.loads(function["arguments"])
        except ValueError as error:
            raise NativeToolAuthorityError("native rejected arguments are malformed") from error
        if not isinstance(arguments, dict):
            raise NativeToolAuthorityError("native rejected arguments must be an object")
        call_ids.append(call["id"])
        parsed[call["id"]] = arguments
    matches = [call for call in calls if call["id"] == document.get("tool_call_id")]
    if len(matches) != 1:
        raise NativeToolAuthorityError("native batch rejection call identity differs")
    call = matches[0]
    if argument_rejection:
        from jsonschema.validators import validator_for
        schema = next(s["function"]["parameters"] for s in authority["selected_tool_schemas"]
                      if s["function"]["name"] == call["function"]["name"])
        validator = validator_for(schema)
        validator.check_schema(schema)
        if validator(schema).is_valid(parsed[call["id"]]):
            raise NativeToolAuthorityError("argument rejection claims a schema-valid call")
    result = (invalid_arguments_rejection_result(len(calls)) if argument_rejection else
              episode_call_limit_rejection_result(len(calls)) if limit_rejection
              else multiple_call_rejection_result(len(calls)))
    if (
        document.get("tool_id") != call["function"]["name"]
        or document.get("arguments") != parsed[call["id"]]
        or document.get("result") != result
        or document.get("result_sha256") != content_hash(result)
        or document.get("native_result_content") != []
        or document.get("native_result_content_sha256") != content_hash({"blocks": []})
    ):
        raise NativeToolAuthorityError("native batch rejection claims changed content or evidence")
    return authority, dict(call)
