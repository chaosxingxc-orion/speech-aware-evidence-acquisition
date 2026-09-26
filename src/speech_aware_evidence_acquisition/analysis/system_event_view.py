"""Declared semantic views of full verified episodes, without outcome filtering.

All contacts, actual tool events, knowledge bodies and deliveries survive. JSON
history wrappers are decoded for sharing; known duplicate custody metadata and
wire timing fields are omitted explicitly. This is not a literal wire replay.
Unknown fields and malformed JSON remain visible rather than being discarded.
"""

from __future__ import annotations

import copy
import hashlib
import json

from ..rails.hashing import content_hash

VIEW_ID = "complete-system-events-per-input-v1"
_TOOL_CUSTODY = frozenset(
    {
        "source_authority",
        "source_authority_sha256",
        "internal_memory_lineage",
        "native_source_state_id",
        "native_tool_calls_json",
        "tool_calls_sha256",
        "source_response_sha256",
        "tool_source_sha256",
        "query_state_sha256",
        "snapshot_sha256",
        "speech_packet_id",
        "speech_packet_sha256",
        "result_sha256",
        "native_result_content_sha256",
    }
)
_WIRE_METADATA = frozenset(
    {"created", "model", "system_fingerprint", "object", "id", "timings"}
)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _nonfinite(_value):
    raise ValueError("nonfinite JSON number")


def _decoded(text, omitted):
    if not isinstance(text, str):
        return None
    try:
        document = json.loads(
            text, object_pairs_hook=_unique, parse_constant=_nonfinite
        )
    except ValueError:
        return None
    if not isinstance(document, dict):
        return None
    return {
        "encoding": "decoded-json-object",
        "source_utf8_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "document": {k: v for k, v in document.items() if k not in omitted},
        "omitted_fields": sorted(set(document) & omitted),
    }


def project_system_events(episode):
    """Project a source-verified project_episode result; never authorize its read."""
    result = copy.deepcopy(episode)
    result["source_projection_sha256"] = content_hash(episode)
    result["view_id"] = VIEW_ID
    for contact in result["contacts"]:
        request = contact["recorded_request"]
        for state in request.get("history", []):
            if state.get("role") == "control":
                omit = frozenset()
            elif state.get("state_kind") == "tool-result":
                omit = _TOOL_CUSTODY
            else:
                continue
            decoded = _decoded(state.get("content"), omit)
            if decoded is not None:
                state.pop("content")
                state["content_view"] = decoded
        decoded = _decoded(contact.get("wire_response_utf8"), _WIRE_METADATA)
        if decoded is not None:
            contact.pop("wire_response_utf8")
            contact["wire_response_view"] = decoded
    omitted = {"use_" + field for field in _TOOL_CUSTODY}
    for tool in result["actual_tool_records"]:
        raw = tool["record"]
        tool["source_record_sha256"] = content_hash(raw)
        tool["omitted_fields"] = sorted(set(raw) & omitted)
        tool["record"] = {k: v for k, v in raw.items() if k not in omitted}
    return result
