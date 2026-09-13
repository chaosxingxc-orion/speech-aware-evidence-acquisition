"""Project source-bound native control and tool meaning into TRAIN feedback.

This pure reader shares runtime history validation. It does not execute tools,
load speech or grant proposal/admission authority. Custody remains in the pinned
source trace; model-facing calls receive candidate-local labels.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from ..core.model.native_framework_history import validate_native_framework_contact
from ..core.model.native_history import _bound_blocks, _bound_result
from .hashing import content_hash


class NativeTrainingContextError(ValueError):
    """A native trajectory lacks its exact original completion or tool return."""


def _refuse(message):
    raise NativeTrainingContextError(message)


def _text_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


# Remove transport/custody metadata, not semantic task fields or tool results.
# Do not redact free text: any embedded forbidden identity fails the final
# proposal-context boundary instead of silently changing an instruction.
_CUSTODY_FIELDS = frozenset({
    "sample_id", "source_sample_ids", "source_uri", "source_path",
    "request_id", "core_request_id", "agent_contact_id", "run_id", "attempt_id",
    "speech_packet_id", "packet_id", "source_authority", "tool_invocation",
    "native_tool_calls_json", "native_result_content", "lineage",
    "evidence_id",
})
_LOCAL_REFERENCE_FIELDS = frozenset({
    "selected_value_ids", "supporting_facet_ids", "value_id", "facet_id",
    "record_id", "selected_record_ids", "local_value_ids", "local_facet_ids",
})


class NativeTrainingContextProjector:
    """Keep call/result associations local to one sample's candidate trajectory."""

    def __init__(self):
        self.calls = {}
        self.sources = {}
        self.references = {}

    def _reference(self, value):
        if isinstance(value, list):
            return [self._reference(item) for item in value]
        if not isinstance(value, str):
            _refuse("native semantic reference is not text")
        return self.references.setdefault(value, f"reference-{len(self.references) + 1}")

    def _semantic_result(self, value):
        if isinstance(value, Mapping):
            result = {}
            for key, item in value.items():
                if key in _CUSTODY_FIELDS or key.endswith("_sha256"):
                    continue
                result[key] = (
                    self._reference(item) if key in _LOCAL_REFERENCE_FIELDS
                    else self._semantic_result(item)
                )
            return result
        if isinstance(value, list):
            return [self._semantic_result(item) for item in value]
        return value

    def _completion_calls(self, request, control, response, completion):
        if response is None:
            if completion is not None:
                _refuse("native completion exists without its observed response")
            return []
        if not isinstance(completion, Mapping) or completion.get("schema") != "saea-native-completion-v1":
            _refuse("native response lacks its source completion receipt")
        expected = {
            "request_id": request["request_id"], "sample_id": request["sample_id"],
            "agent_contact_id": control["contact_id"],
            "request_sha256": content_hash(request),
            "response_sha256": response.get("response_sha256"),
            "response_text_sha256": response["response_text_sha256"],
        }
        if any(completion.get(key) != value for key, value in expected.items()):
            _refuse("native completion differs from its source request or response")
        raw = completion.get("native_tool_calls_json")
        if not isinstance(raw, str) or _text_sha(raw) != completion.get("native_tool_calls_sha256"):
            _refuse("native completion tool call bytes changed")
        calls = json.loads(raw)
        if not isinstance(calls, list):
            _refuse("native completion calls are not a list")
        schemas = request.get("tool_schemas", [])
        if not isinstance(schemas, list):
            _refuse("native request tool schemas are not a list")
        allowed = {
            tool["function"]["name"] for tool in schemas
            if isinstance(tool, Mapping) and isinstance(tool.get("function"), Mapping)
            and isinstance(tool["function"].get("name"), str)
        }
        projected = []
        seen = set()
        for call in calls:
            function = call.get("function") if isinstance(call, Mapping) else None
            if (
                not isinstance(call, Mapping) or set(call) != {"id", "type", "function"}
                or call["type"] != "function" or not isinstance(call["id"], str) or not call["id"]
                or call["id"] in seen or not isinstance(function, Mapping)
                or set(function) != {"name", "arguments"} or function["name"] not in allowed
                or not isinstance(function["arguments"], str)
            ):
                _refuse("native completion has an invalid or out-of-scope function call")
            arguments = json.loads(function["arguments"])
            if not isinstance(arguments, dict):
                _refuse("native function arguments are not an object")
            seen.add(call["id"])
            key = (request["request_id"], call["id"])
            value = {
                "label": f"call-{len(self.calls) + 1}",
                "name": function["name"], "arguments": arguments,
            }
            self.calls[key] = (call, value)
            projected.append(value)
        return projected

    def project(self, request, response, completion):
        """Return additive semantic fields, or None for a historical contact."""
        validated = validate_native_framework_contact(request)
        if validated is None:
            if completion is not None:
                _refuse("native completion requires its framework contact envelope")
            return None
        contract, _selected, _source_ids = validated
        history = request["history"]
        control = history[-1]
        if control.get("content_sha256") != _text_sha(control["content"]):
            _refuse("native control content hash differs")
        states, results = {}, []
        for state in history[:-1]:
            if _text_sha(state["content"]) != state.get("content_sha256"):
                _refuse("native history state content hash differs")
            if state.get("state_kind") == "tool-result":
                document, call, _assistant = _bound_result(state, states, set(), request)
                blocks, packets = _bound_blocks(document)
                source_id = document["core_request_id"]
                source = self.sources.get(source_id)
                original = self.calls.get((source_id, call["id"]))
                if source is None or original is None or original[0] != call:
                    _refuse("native tool result has no preceding actual model call")
                source_request, source_response, source_completion = source
                authority = document.get("source_authority", {})
                if (
                    source_response is None or source_completion is None
                    or authority.get("source_request_sha256") != content_hash(source_request)
                    or authority.get("source_response_sha256") != source_response.get("response_sha256")
                    or authority.get("source_tool_calls_sha256") != source_completion["native_tool_calls_sha256"]
                    or authority.get("agent_contact_id") != source_completion["agent_contact_id"]
                    or states[document["native_source_state_id"]]["content"] != source_response["text"]
                ):
                    _refuse("native tool return authority differs from its original contact")
                visible = {
                    "call_label": original[1]["label"], "name": original[1]["name"],
                    "arguments": original[1]["arguments"],
                    "result": self._semantic_result(document["result"]),
                    "evidence": [
                        {"reference": self._reference(block["evidence_id"]),
                         "content": block["text"], "kind": block.get("knowledge_role", "observation")}
                        for block in blocks
                    ],
                }
                if packets:
                    # Never misrepresent a feature descriptor as decoded speech.
                    visible["speech_evidence"] = {
                        "count": len(packets), "content_available_in_text_projection": False,
                    }
                results.append(visible)
            states[state["state_id"]] = state
        tool_calls = self._completion_calls(request, control, response, completion)
        self.sources[request["request_id"]] = (request, response, completion)
        return {
            "role_id": contract["role_id"],
            "instruction": contract["messages"][1]["content"],
            "system_instruction": contract["messages"][0]["content"],
            "available_tools": request.get("tool_schemas", []),
            "tool_calls": tool_calls, "tool_results": results,
        }
