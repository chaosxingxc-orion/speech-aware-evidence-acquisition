"""Project source-bound framework history through the existing speech carrier.

This is a pure wire adapter. OpenJiuwen owns the sequence and its tool loop;
FlightRuntime and the phase dispatcher own completion and tool custody.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence

from . import FrozenCoreError
from .native_history import (
    _bound_blocks,
    _bound_result,
    _validate_bound_result_group,
    project_native_history,
)

FRAMEWORK_CONTACT_SCHEMA = "saea-native-framework-contact-v1"


def _refuse(message: str):
    raise FrozenCoreError("native framework history: " + message)


def framework_contact_instruction(
    *,
    role_id: str,
    sample_id: str,
    contact_id: str,
    messages: Sequence[Mapping[str, object]],
    local_tool_result_ids: Sequence[str],
) -> str:
    """Encode the complete local framework sequence in the existing control field."""
    return json.dumps(
        {
            "schema": FRAMEWORK_CONTACT_SCHEMA,
            "role_id": role_id,
            "sample_id": sample_id,
            "contact_id": contact_id,
            "messages": list(messages),
            "local_tool_result_ids": list(local_tool_result_ids),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def native_tool_result_message(document: Mapping[str, object]) -> dict[str, object]:
    """Render counted tool data as canonical JSON text, never Python mapping repr.

    The caller must supply the dispatcher-produced document. Historical use
    additionally verifies its source and counted custody through _bound_result.
    """
    blocks, _packets = _bound_blocks(document)
    content = {
        "result": document["result"],
        "evidence": [
            {
                "evidence_id": b["evidence_id"],
                "source_uri": b["source_uri"],
                "content": b["text"],
            }
            for b in blocks
        ],
    }
    return {
        "role": "tool",
        "tool_call_id": document["tool_call_id"],
        "content": json.dumps(content, ensure_ascii=False, sort_keys=True),
    }


def _speech_parts(document, packets):
    if not packets:
        return []
    return [
        {
            "type": "text",
            "text": "Speech evidence returned by tool call "
            + document["tool_call_id"]
            + "; packet-to-value order: "
            + json.dumps(document["result"]["speech_evidence_order"], sort_keys=True),
        },
        *({"type": "input_speech_features", "speech_features": p} for p in packets),
    ]


def validate_native_framework_contact(payload):
    """Validate the source envelope and local tool sequence without rendering.

    Runtime transport and offline TRAIN projection consume the same authority.
    Return None for historical contacts without the native framework envelope.
    """
    history = payload.get("history", [])
    if not history or history[-1].get("role") != "control":
        return None
    control = history[-1]
    try:
        contract = json.loads(control.get("content", ""))
    except (ValueError, TypeError):
        return None
    if (
        not isinstance(contract, Mapping)
        or contract.get("schema") != FRAMEWORK_CONTACT_SCHEMA
    ):
        return None
    if set(contract) != {
        "schema",
        "role_id",
        "sample_id",
        "contact_id",
        "messages",
        "local_tool_result_ids",
    }:
        _refuse("control envelope fields differ")
    if (
        not isinstance(contract["role_id"], str)
        or not contract["role_id"]
        or contract["sample_id"] != payload.get("sample_id")
        or contract["contact_id"] != control.get("contact_id")
    ):
        _refuse("control, sample or speech history binding differs")
    local_ids = contract["local_tool_result_ids"]
    framework = contract["messages"]
    if (
        not isinstance(local_ids, list)
        or any(not isinstance(x, str) or not x for x in local_ids)
        or len(set(local_ids)) != len(local_ids)
        or not isinstance(framework, list)
        or len(framework) < 2
        or any(not isinstance(x, Mapping) for x in framework)
    ):
        _refuse("the complete ordered framework tool sequence is required")
    if (
        dict(framework[0])
        != {"role": "system", "content": payload.get("task_instruction")}
        or set(framework[1]) != {"role", "content"}
        or framework[1]["role"] != "user"
        or not isinstance(framework[1]["content"], str)
        or not framework[1]["content"]
    ):
        _refuse("framework system or initial query differs")
    states, state_indices, selected, source_ids = {}, {}, {}, set()
    local_set = set(local_ids)
    encountered = []
    for history_index, item in enumerate(history[:-1]):
        if item.get("role") != "agent_state" or item.get("state_id") in states:
            _refuse("source history has invalid or duplicate states")
        state_id = item.get("state_id")
        if state_id in local_set:
            if item.get("state_kind") != "tool-result":
                _refuse("local history reference is not a tool result")
            document, call, assistant = _bound_result(item, states, set(), payload)
            if (
                document.get("schema")
                not in {
                    "saea-phase-tool-result-v2",
                    "saea-phase-tool-rejection-v1",
                }
                or document["source_authority"]["role_id"] != contract["role_id"]
            ):
                _refuse("local tool history lacks the role's source authority")
            source_id = document["native_source_state_id"]
            blocks, packets = _bound_blocks(document)
            selected[state_id] = (document, call, assistant, packets)
            source_ids.add(source_id)
            encountered.append(state_id)
        states[state_id] = item
        state_indices[state_id] = history_index
    if encountered != local_ids:
        _refuse("local tool results are missing or reordered")

    groups = []
    grouped = {}
    seen_sources = set()
    for state_id in local_ids:
        entry = selected[state_id]
        source_id = entry[0]["native_source_state_id"]
        if not groups or groups[-1][0] != source_id:
            if source_id in seen_sources:
                _refuse("one source group is split across local history")
            seen_sources.add(source_id)
            groups.append((source_id, []))
            grouped[source_id] = groups[-1][1]
        grouped[source_id].append((entry[0], entry[1], entry[2]))
    for source_id, group in groups:
        _validate_bound_result_group(group)
        result_indices = [
            state_indices[state_id]
            for state_id in local_ids
            if selected[state_id][0]["native_source_state_id"] == source_id
        ]
        source_index = state_indices.get(source_id)
        if source_index is None or result_indices != list(
            range(source_index + 1, source_index + 1 + len(group))
        ):
            _refuse("a native source and its complete result group must be adjacent")
    expected_length = 2 + len(local_ids) + len(groups)
    if len(framework) != expected_length:
        _refuse("the complete ordered framework tool sequence is required")

    cursor = 2
    for _source_id, group in groups:
        assistant = group[0][2]
        observed_assistant = dict(framework[cursor])
        expected_assistant = copy.deepcopy(assistant)
        expected_assistant["content"] = (
            "" if assistant.get("content") is None else assistant["content"]
        )
        # OpenJiuwen can retain finish_reason in its serialized AssistantMessage.
        finish = observed_assistant.pop("finish_reason", "tool_calls")
        if finish != "tool_calls" or observed_assistant != expected_assistant:
            _refuse("framework assistant differs from its original source turn")
        cursor += 1
        for document, _call, _assistant in group:
            tool_message = native_tool_result_message(document)
            if dict(framework[cursor]) != tool_message:
                _refuse("framework tool message differs from its counted observation")
            cursor += 1
    return contract, selected, source_ids


def project_native_framework_history(*, payload, messages, state_texts):
    """Return a validated full wire sequence, or None for the historical path."""
    validated = validate_native_framework_contact(payload)
    if validated is None:
        return None
    contract, selected, source_ids = validated
    history = payload["history"]
    framework = contract["messages"]
    local_ids = contract["local_tool_result_ids"]
    local_set = set(local_ids)
    if (
        len(history) != len(state_texts)
        or len(messages) != 2
        or messages[1].get("role") != "user"
        or not isinstance(messages[1].get("content"), list)
        or framework[0] != messages[0]
    ):
        _refuse("control, sample or speech history binding differs")
    if messages[1]["content"][-len(state_texts) :] != [
        {"type": "text", "text": text} for text in state_texts
    ]:
        _refuse("source history is not the complete speech suffix")
    excluded = local_set | source_ids
    prior = [
        (item, state_texts[index])
        for index, item in enumerate(history[:-1])
        if item.get("state_id") not in excluded
    ]
    prior_payload = copy.deepcopy(payload)
    prior_payload["history"] = [copy.deepcopy(item) for item, _text in prior]
    prior_texts = [text for _item, text in prior]
    base = copy.deepcopy(messages)
    base[1]["content"] = base[1]["content"][: -len(state_texts)] + [
        {"type": "text", "text": text} for text in prior_texts
    ]
    rendered, historical_packets = project_native_history(
        payload=prior_payload,
        messages=base,
        state_texts=prior_texts,
    )
    query_part = {"type": "text", "text": framework[1]["content"]}
    if rendered[-1]["role"] == "user" and isinstance(rendered[-1]["content"], list):
        rendered[-1]["content"].append(query_part)
    else:
        rendered.append({"role": "user", "content": [query_part]})
    packet_by_id = {p["packet_id"]: p for p in historical_packets}
    groups = []
    for state_id in local_ids:
        entry = selected[state_id]
        source_id = entry[0]["native_source_state_id"]
        if not groups or groups[-1][0] != source_id:
            groups.append((source_id, []))
        groups[-1][1].append(entry)
    for _source_id, group in groups:
        rendered.append(copy.deepcopy(group[0][2]))
        for document, _call, _assistant, packets in group:
            rendered.append(native_tool_result_message(document))
            for packet in packets:
                prior_packet = packet_by_id.setdefault(packet["packet_id"], packet)
                if prior_packet != packet:
                    _refuse("historical speech packet identity changed")
            parts = _speech_parts(document, packets)
            if parts:
                rendered.append({"role": "user", "content": parts})
    return rendered, list(packet_by_id.values())
