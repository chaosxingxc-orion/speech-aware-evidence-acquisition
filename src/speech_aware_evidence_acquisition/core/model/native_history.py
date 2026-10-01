"""Project bound native invocations into assistant/tool turns without contacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from . import FrozenCoreError


def _refuse(message):
    raise FrozenCoreError("native history: " + message)


def _json(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError) as error:
        raise FrozenCoreError("native history contains invalid JSON") from error


def _query_speech_identity(payload):
    """Return one source-bound query speech identity for native history custody."""

    feature_parts = payload.get("speech_feature_parts")
    raw = payload.get("raw_speech_query")
    raw_declared = "raw_speech_query" in payload
    if raw_declared and "speech_feature_parts" in payload:
        _refuse("raw and feature query speech identities cannot be mixed")
    if feature_parts is None:
        feature_parts = []
    if not isinstance(feature_parts, list):
        _refuse("speech feature identities must be a list")
    feature_queries = [
        item
        for item in feature_parts
        if isinstance(item, Mapping) and item.get("role") == "query"
    ]
    if raw_declared:
        if (
            not isinstance(raw, Mapping)
            or set(raw) != {"media_relpath", "sha256"}
            or not isinstance(raw["media_relpath"], str)
            or not raw["media_relpath"]
            or not isinstance(raw["sha256"], str)
            or len(raw["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in raw["sha256"])
        ):
            _refuse("raw query speech identity is malformed")
        return raw["media_relpath"], raw["sha256"]
    if len(feature_queries) != 1:
        _refuse("one raw or feature query speech identity is required")
    query = feature_queries[0]
    return query.get("packet_id"), query.get("sha256")


def _bound_result(state, states, allowed_names, payload):
    from ...rails.hashing import content_hash
    from ...rails.native_tool_authority import (
        MULTIPLE_CALL_REJECTION_SCHEMA,
        NativeToolAuthorityError,
        validate_native_call_rejection,
        validate_native_tool_authority,
    )

    document = _json(state["content"])
    schema = document.get("schema") if isinstance(document, Mapping) else None
    result_schemas = {"saea-phase-tool-result-v1", "saea-phase-tool-result-v2"}
    if schema not in {*result_schemas, MULTIPLE_CALL_REJECTION_SCHEMA}:
        _refuse("tool result has an unsupported native envelope")
    source = states.get(document.get("native_source_state_id"))
    if (
        document.get("selection_mode") != "native-tools"
        or source is None
        or not source.get("state_kind", "").startswith("phase:")
        or source["content_sha256"] != source["source_response_sha256"]
        or any(
            state[key] != source[key]
            for key in (
                "source_query_state_sha256",
                "source_response_sha256",
                "producer_policy_id",
            )
        )
        or document.get("query_state_sha256") != source["source_query_state_sha256"]
        or document.get("source_response_sha256") != source["source_response_sha256"]
    ):
        _refuse("tool result is not bound to its preceding phase")

    authority = None
    assistant_message = {"role": "assistant", "content": None}
    call = None
    if schema == MULTIPLE_CALL_REJECTION_SCHEMA:
        try:
            authority, call = validate_native_call_rejection(document)
        except NativeToolAuthorityError as error:
            raise FrozenCoreError(
                "native history: source-bound call rejection is invalid"
            ) from error
    elif schema == "saea-phase-tool-result-v2":
        try:
            authority = validate_native_tool_authority(document.get("source_authority"))
        except NativeToolAuthorityError as error:
            raise FrozenCoreError(
                "native history: source authority is invalid"
            ) from error

    if authority is not None:
        authority_sha256 = content_hash(authority)
        if (
            document.get("source_authority_sha256") != authority_sha256
            or authority["phase_id"] != document.get("phase")
            or authority["sample_id"] != document.get("sample_id")
            or authority["request_id"] != document.get("core_request_id")
            or authority["source_response_text_sha256"]
            != document.get("source_response_sha256")
            or authority["source_tool_calls_sha256"]
            != document.get("tool_calls_sha256")
        ):
            _refuse("source authority differs from the tool result")
        allowed_names = set(authority["selected_tool_names"])
        assistant_message = dict(authority["original_assistant_message"])

    query_packet_id, query_packet_sha256 = _query_speech_identity(payload)
    phase = document.get("phase")
    if (
        not isinstance(phase, str)
        or not phase
        or source["state_kind"] != "phase:" + phase
        or document.get("sample_id") != payload.get("sample_id")
        or document.get("speech_packet_id") != query_packet_id
        or document.get("speech_packet_sha256") != query_packet_sha256
    ):
        _refuse("tool invocation lacks matching counted custody")

    raw = document.get("native_tool_calls_json")
    if not isinstance(raw, str) or hashlib.sha256(
        raw.encode()
    ).hexdigest() != document.get("tool_calls_sha256"):
        _refuse("native call bytes changed")
    calls = _json(raw)
    if not isinstance(calls, list) or not calls:
        _refuse("one or more actual calls are required per result")

    if schema in result_schemas:
        invocation = document.get("tool_invocation")
        invocation_schema = (
            "saea-native-phase-tool-contact-v2"
            if schema == "saea-phase-tool-result-v2"
            else "saea-native-phase-tool-contact-v1"
        )
        fields = (
            "sample_id",
            "phase",
            "next_phase",
            "tool_id",
            "source_response_sha256",
            "tool_call_id",
            "tool_calls_sha256",
            "speech_packet_id",
            "speech_packet_sha256",
        )
        if (
            not isinstance(invocation, Mapping)
            or invocation.get("schema") != invocation_schema
            or any(
                not isinstance(document.get(key), str)
                or not document[key]
                or invocation.get(key) != document[key]
                for key in fields
            )
            or invocation.get("request_id") != document.get("core_request_id")
            or (
                authority is not None
                and (
                    invocation.get("source_authority_sha256")
                    != document.get("source_authority_sha256")
                    or invocation.get("source_authority_role") != authority["role_id"]
                    or invocation.get("source_request_sha256")
                    != authority["source_request_sha256"]
                    or invocation.get("source_completion_sha256")
                    != authority["completion_sha256"]
                )
            )
            or not isinstance(document.get("core_request_id"), str)
            or not document["core_request_id"]
            or invocation.get("arguments_sha256")
            != hashlib.sha256(
                json.dumps(
                    document.get("arguments"),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
        ):
            _refuse("tool invocation lacks matching counted custody")
        if schema == "saea-phase-tool-result-v1" and not allowed_names:
            _refuse("legacy native result requires the current tool schema scope")
        if len(calls) != 1 or not isinstance(calls[0], Mapping):
            _refuse("one actual call is required per result")
        call = calls[0]
        function = call.get("function")
        if (
            set(call) != {"id", "type", "function"}
            or call["type"] != "function"
            or not isinstance(call["id"], str)
            or not call["id"]
            or call["id"] != document.get("tool_call_id")
            or not isinstance(function, Mapping)
            or set(function) != {"name", "arguments"}
            or function["name"] not in allowed_names
            or function["name"] != document.get("tool_id")
            or not isinstance(function["arguments"], str)
            or _json(function["arguments"]) != document.get("arguments")
        ):
            _refuse("call identity or exact arguments are not bound")
        if authority is not None:
            if assistant_message.get("tool_calls") != [call]:
                _refuse("source assistant message differs from the executed call")
        else:
            assistant_message["tool_calls"] = [call]
    else:
        if call not in calls or assistant_message.get("tool_calls") != calls:
            _refuse("rejected call differs from its complete source batch")

    result = document.get("result")
    blocks = document.get("native_result_content")
    if (
        not isinstance(result, Mapping)
        or content_hash(result) != document.get("result_sha256")
        or not isinstance(blocks, list)
        or content_hash({"blocks": blocks})
        != document.get("native_result_content_sha256")
    ):
        _refuse("tool return content changed")
    return document, call, assistant_message


def _bound_blocks(document):
    """Validate returned text and packet identities against the selected result."""
    result = document["result"]
    text_blocks, packets = [], []
    knowledge = "knowledge_view" in result
    for block in document["native_result_content"]:
        if not isinstance(block, Mapping):
            _refuse("tool content is not a typed block")
        if block.get("type") == "text":
            evidence_id, uri, text = (
                block.get(key) for key in ("evidence_id", "source_uri", "text")
            )
            if not all(
                isinstance(value, str) and value for value in (evidence_id, uri, text)
            ):
                _refuse("text evidence identity is incomplete")
            if knowledge:
                if (
                    evidence_id not in result.get("selected_value_ids", [])
                    or result["knowledge_view"] not in {"text", "paired"}
                    or uri
                    != f"knowledge-snapshot://{document['snapshot_sha256']}/{evidence_id}"
                    or block.get("knowledge_role") != "value"
                ):
                    _refuse("knowledge text differs from its selected value")
            elif evidence_id != result.get("evidence_id") or uri != result.get(
                "source_uri"
            ):
                _refuse("observation differs from its selected source")
            text_blocks.append(dict(block))
        elif block.get("type") == "input_speech_features":
            descriptor = block.get("speech_features")
            if (
                not knowledge
                or result["knowledge_view"] not in {"speech", "paired"}
                or not isinstance(descriptor, Mapping)
                or set(descriptor) != {"packet_id", "sha256", "role"}
                or descriptor["role"] != "key"
                or not isinstance(descriptor["packet_id"], str)
                or not descriptor["packet_id"]
                or not isinstance(descriptor["sha256"], str)
                or len(descriptor["sha256"]) != 64
                or any(c not in "0123456789abcdef" for c in descriptor["sha256"])
            ):
                _refuse("historical feature is not a selected knowledge key")
            packets.append(dict(descriptor))
        else:
            _refuse("unsupported native result content")
    expected = [
        {
            "packet_id": entry["packet_id"],
            "sha256": entry["packet_sha256"],
            "role": "key",
        }
        for entry in result.get("speech_evidence_order", [])
    ]
    if packets != expected:
        _refuse("speech key order differs from the selected return")
    if knowledge:
        expected_text_ids = (
            result.get("selected_value_ids", [])
            if result["knowledge_view"] in {"text", "paired"}
            else []
        )
        if [block["evidence_id"] for block in text_blocks] != expected_text_ids:
            _refuse("knowledge return omits or reorders selected text")
    elif "evidence_id" in result and [
        block["evidence_id"] for block in text_blocks
    ] != [result["evidence_id"]]:
        _refuse("observation return is missing")
    return text_blocks, packets


def _validate_bound_result_group(group):
    """Validate one source assistant followed by its complete result group."""
    if not group:
        _refuse("a native source group cannot be empty")
    schemas = {entry[0]["schema"] for entry in group}
    assistant = group[0][2]
    if any(entry[2] != assistant for entry in group):
        _refuse("one source group has conflicting assistant bytes")
    calls = [entry[1] for entry in group]
    source_calls = assistant.get("tool_calls")
    rejection = "saea-phase-tool-rejection-v1"
    if schemas == {rejection}:
        if (
            not isinstance(source_calls, list)
            # Each observation has already validated its rejection cause:
            # schema and episode-budget rejections cover one original call.
            or len(source_calls) < 1
            or calls != source_calls
            or len({call["id"] for call in calls}) != len(calls)
        ):
            _refuse("rejected results do not completely cover the source batch")
    elif len(group) != 1 or schemas not in (
        {"saea-phase-tool-result-v1"},
        {"saea-phase-tool-result-v2"},
    ):
        _refuse("successful and rejected native results cannot be mixed")
    elif source_calls != calls:
        _refuse("source assistant message differs from the executed call")
    return assistant


def project_native_history(*, payload, messages, state_texts):
    """Return native chat messages plus historical packet descriptors to validate.

    Historical envelopes without raw native call bytes retain their old wire
    representation. New envelopes preserve each invocation's returned view, even
    when a later selection replaces the current aggregate knowledge view.
    """
    history = payload.get("history", [])
    native_indices = []
    for index, state in enumerate(history):
        if state.get("state_kind") == "tool-result":
            try:
                document = json.loads(state["content"])
            except (TypeError, ValueError):
                # Legacy generic tool states may contain plain text.
                continue
            if isinstance(document, Mapping) and "native_tool_calls_json" in document:
                native_indices.append(index)
    if not native_indices:
        return messages, []
    if (
        payload.get("decoding_params", {}).get("tool_choice")
        not in {"auto", "none", "required"}
        or len(messages) != 2
        or messages[1]["role"] != "user"
        or len(state_texts) != len(history)
    ):
        _refuse("explicit native controls and the complete source history are required")
    schemas = payload.get("tool_schemas")
    allowed = (
        {
            tool["function"]["name"]
            for tool in schemas
            if isinstance(tool, Mapping)
            and isinstance(tool.get("function"), Mapping)
            and isinstance(tool["function"].get("name"), str)
        }
        if isinstance(schemas, list)
        else set()
    )
    states, state_indices, calls_by_source, result_indices = {}, {}, {}, {}
    evidence, feature_identities = {}, {}
    for index, state in enumerate(history):
        if index in native_indices:
            document, call, assistant_message = _bound_result(
                state, states, allowed, payload
            )
            source_id = document["native_source_state_id"]
            text_blocks, packets = _bound_blocks(document)
            calls_by_source.setdefault(source_id, []).append(
                (document, call, assistant_message)
            )
            result_indices[index] = (
                document,
                call,
                assistant_message,
                text_blocks,
                packets,
            )
            for block in text_blocks:
                previous = evidence.setdefault(block["evidence_id"], block)
                if previous != block:
                    _refuse("one evidence identity has conflicting returned content")
            for descriptor in packets:
                previous = feature_identities.setdefault(
                    descriptor["packet_id"], descriptor
                )
                if previous != descriptor:
                    _refuse("one historical packet has conflicting identities")
        if state.get("role") == "agent_state":
            if state["state_id"] in states:
                _refuse("duplicate state identity")
            states[state["state_id"]] = state
            state_indices[state["state_id"]] = index

    for source_id, group in calls_by_source.items():
        _validate_bound_result_group(group)
        source_index = state_indices.get(source_id)
        result_order = [
            index
            for index, entry in result_indices.items()
            if entry[0]["native_source_state_id"] == source_id
        ]
        if source_index is None or result_order != list(
            range(source_index + 1, source_index + 1 + len(group))
        ):
            _refuse("a native source and its complete result group must be adjacent")

    # Suppress current aggregate copies only when they equal an actual return.
    removed_texts = set()
    for field in ("supplied_evidence", "retrieved_evidence"):
        for item in payload.get(field, []):
            block = evidence.get(item["evidence_id"])
            if block is not None:
                if (
                    item["content"] != block["text"]
                    or item.get("source_uri") != block["source_uri"]
                ):
                    _refuse("current evidence differs from the sealed tool return")
                removed_texts.add(f"[evidence {item['evidence_id']}] {item['content']}")
    initial = []
    for part in messages[1]["content"][: -len(state_texts)]:
        if part.get("type") == "text" and part.get("text") in removed_texts:
            continue
        descriptor = part.get("speech_features")
        if isinstance(descriptor, Mapping) and descriptor.get("role") == "key":
            prior = feature_identities.get(descriptor["packet_id"])
            if prior is not None:
                if prior != descriptor:
                    _refuse("current packet differs from its native return")
                continue
        initial.append(part)
    rendered = [messages[0], {"role": "user", "content": initial}]
    returned_evidence, returned_packets = set(), set()

    def user_parts(parts):
        if rendered[-1]["role"] == "user":
            rendered[-1]["content"].extend(parts)
        else:
            rendered.append({"role": "user", "content": parts})

    for index, state in enumerate(history):
        source_group = calls_by_source.get(state.get("state_id"))
        if source_group is not None:
            rendered.append(dict(source_group[0][2]))
        elif index in result_indices:
            document, call, _assistant_message, blocks, packets = result_indices[index]
            fresh = [b for b in blocks if b["evidence_id"] not in returned_evidence]
            repeated = [
                b["evidence_id"]
                for b in blocks
                if b["evidence_id"] in returned_evidence
            ]
            tool_content = {
                "result": document["result"],
                "evidence": [
                    {
                        "evidence_id": b["evidence_id"],
                        "source_uri": b["source_uri"],
                        "content": b["text"],
                    }
                    for b in fresh
                ],
            }
            if repeated:
                tool_content["previously_returned_evidence_ids"] = repeated
            rendered.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(
                        tool_content, ensure_ascii=False, sort_keys=True
                    ),
                }
            )
            returned_evidence.update(b["evidence_id"] for b in blocks)
            fresh_packets = [
                p for p in packets if p["packet_id"] not in returned_packets
            ]
            if fresh_packets:
                user_parts(
                    [
                        {
                            "type": "text",
                            "text": "Speech evidence returned by tool call "
                            + call["id"]
                            + "; packet-to-value order: "
                            + json.dumps(
                                document["result"]["speech_evidence_order"],
                                sort_keys=True,
                            ),
                        },
                        *(
                            {"type": "input_speech_features", "speech_features": p}
                            for p in fresh_packets
                        ),
                    ]
                )
                returned_packets.update(p["packet_id"] for p in fresh_packets)
        else:
            user_parts([{"type": "text", "text": state_texts[index]}])
    return rendered, list(feature_identities.values())
