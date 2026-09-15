"""Raw native transport preserves original audio and source-bound native history."""

import base64
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    framework_contact_instruction,
    native_tool_result_message,
)
from speech_aware_evidence_acquisition.core.model.transport import (
    LlamaServerTransport,
    _speech_history_texts,
)
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_native_history_projection import change_result, world as native_world
from test_native_tool_authority import _authority_world


def _transport(tmp_path, *, prompt_order="native-raw-speech-v1", captured=None):
    transport = object.__new__(LlamaServerTransport)
    transport._prompt_order = prompt_order
    transport._data_root = tmp_path
    transport._feature_root = None
    transport._feature_cache_guard = None
    transport._user_turn_text = None
    transport._user_turn_audio_first = True
    transport._omit_system_message = False
    transport._preserve_wire_responses = False
    transport._url = "http://127.0.0.1:1/v1/chat/completions"
    transport._assert_session_still_valid = lambda: None

    def post(_url, body):
        if captured is not None:
            captured.append(json.loads(body))
        return json.dumps({
            "choices": [{"message": {"content": "done"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }).encode()

    transport._post = post
    return transport


def _payload(tmp_path, **updates):
    raw = b"RIFF\x24\x00\x00\x00WAVEfmt synthetic raw speech"
    media = tmp_path / "media" / "window.wav"
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(raw)
    payload = {
        "request_id": "request-1",
        "carrier_lock_key": "earnings21-original",
        "sample_id": "call-1",
        "speech_ref": "earnings21-original/call-1",
        "media_relpath": "media/window.wav",
        "raw_speech_query": {
            "media_relpath": "media/window.wav",
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "audio_seconds": 1.0,
        "sample_rate_hz": 16000,
        "task_instruction": "Transcribe the speech.",
        "history": [],
        "decoding_params": {
            "temperature": 0,
            "tool_choice": "none",
            "parallel_tool_calls": False,
        },
        "supplied_evidence": [],
        "evidence_provenance": [],
        "tool_schemas": [],
    }
    payload.update(updates)
    return payload, raw


def _raw_framework_payload(tmp_path):
    payload, raw = _payload(tmp_path)
    _tool, _context, _completion, _step, native, _messages, _texts, _counted = (
        _authority_world()
    )
    old_identity = native["speech_feature_parts"][0]
    replacements = {
        old_identity["packet_id"]: payload["media_relpath"],
        old_identity["sha256"]: hashlib.sha256(raw).hexdigest(),
    }
    history = json.loads(json.dumps(native["history"]))
    for state in history:
        if state["role"] == "control":
            continue
        document = json.loads(state["content"])
        serialized = json.dumps(document, sort_keys=True)
        for old, new in replacements.items():
            serialized = serialized.replace(old, new)
        document = json.loads(serialized)
        if state.get("state_kind") == "tool-result":
            document["result_sha256"] = content_hash(document["result"])
            document["native_result_content_sha256"] = content_hash(
                {"blocks": document["native_result_content"]}
            )
        content = json.dumps(document, sort_keys=True)
        state.update(
            content=content,
            content_sha256=hashlib.sha256(content.encode()).hexdigest(),
        )
    result_state = next(
        state for state in history if state.get("state_kind") == "tool-result"
    )
    document = json.loads(result_state["content"])
    assistant = dict(document["source_authority"]["original_assistant_message"])
    if assistant.get("content") is None:
        assistant["content"] = ""
    framework = [
        {"role": "system", "content": "Solve the speech task."},
        {"role": "user", "content": "Review the original speech."},
        assistant,
        native_tool_result_message(document),
    ]
    control = history[-1]
    control_content = framework_contact_instruction(
        role_id=document["source_authority"]["role_id"],
        sample_id=native["sample_id"],
        contact_id=control["contact_id"],
        messages=framework,
        local_tool_result_ids=(result_state["state_id"],),
    )
    control.update(
        content=control_content,
        content_sha256=hashlib.sha256(control_content.encode()).hexdigest(),
    )
    payload.update(
        sample_id=native["sample_id"],
        speech_ref="earnings21-original/" + native["sample_id"],
        task_instruction="Solve the speech task.",
        history=history,
        tool_schemas=native["tool_schemas"],
        supplied_evidence=native["supplied_evidence"],
    )
    return payload, raw, framework


def test_empty_history_keeps_one_original_raw_audio_and_fit_equals_dispatch(tmp_path):
    payload, raw = _payload(tmp_path)
    captured = []
    transport = _transport(tmp_path, captured=captured)
    request = canonical_bytes(payload)

    fitted = transport.render_request(request)
    transport(request)

    assert captured == [fitted]
    assert [row["role"] for row in fitted["messages"]] == ["system", "user"]
    parts = fitted["messages"][1]["content"]
    audio = [part for part in parts if part["type"] == "input_audio"]
    assert len(audio) == 1
    assert base64.b64decode(audio[0]["input_audio"]["data"]) == raw
    assert "input_speech_features" not in json.dumps(fitted)


def test_framework_assistant_tool_history_is_rendered_once_after_original_audio(tmp_path):
    payload, raw, framework = _raw_framework_payload(tmp_path)
    body = _transport(tmp_path).render_request(canonical_bytes(payload))

    assert [row["role"] for row in body["messages"]] == [
        "system", "user", "assistant", "tool"
    ]
    assert base64.b64decode(
        next(
            part["input_audio"]["data"]
            for part in body["messages"][1]["content"]
            if part["type"] == "input_audio"
        )
    ) == raw
    assert body["messages"][2]["content"] is None
    assert body["messages"][2]["tool_calls"] == framework[2]["tool_calls"]
    assert body["messages"][3] == framework[3]
    assert sum(
        row.get("tool_call_id") == framework[3]["tool_call_id"]
        for row in body["messages"]
    ) == 1
    assert "agent state" not in json.dumps(body)


@pytest.mark.parametrize("change", ["reordered", "tampered"])
def test_reordered_or_tampered_framework_history_is_rejected(tmp_path, change):
    payload, _raw, _framework = _raw_framework_payload(tmp_path)
    control = json.loads(payload["history"][-1]["content"])
    if change == "reordered":
        control["messages"][-2:] = reversed(control["messages"][-2:])
    else:
        control["messages"][-1]["content"] = "{}"
    content = json.dumps(control, sort_keys=True)
    payload["history"][-1].update(
        content=content,
        content_sha256=hashlib.sha256(content.encode()).hexdigest(),
    )

    with pytest.raises(FrozenCoreError):
        _transport(tmp_path).render_request(canonical_bytes(payload))


def test_historical_feature_tool_return_is_refused_by_raw_order(tmp_path):
    payload, raw = _payload(tmp_path)
    native, _messages, texts = native_world(
        packet_id=payload["media_relpath"],
        packet_sha256=hashlib.sha256(raw).hexdigest(),
    )
    state = next(
        item for item in native["history"] if item.get("state_kind") == "tool-result"
    )
    document = json.loads(state["content"])
    raw_call = json.loads(document["native_tool_calls_json"])
    raw_call[0]["function"] = {
        "name": "saea-tool-phase-knowledge-v1",
        "arguments": '{"view":"paired"}',
    }
    raw_calls = json.dumps(raw_call)
    descriptor = {"packet_id": "train/example", "sha256": "e" * 64, "role": "key"}
    blocks = [
        {
            "type": "text",
            "text": "Prepared task knowledge.",
            "evidence_id": "value-one",
            "source_uri": (
                "knowledge-snapshot://"
                + document["snapshot_sha256"]
                + "/value-one"
            ),
            "knowledge_role": "value",
        },
        {"type": "input_speech_features", "speech_features": descriptor},
    ]
    result = {
        "knowledge_view": "paired",
        "selected_value_ids": ["value-one"],
        "speech_evidence_order": [{
            "value_id": "value-one",
            "packet_id": descriptor["packet_id"],
            "packet_sha256": descriptor["sha256"],
        }],
    }
    invocation = {
        **document["tool_invocation"],
        "tool_id": raw_call[0]["function"]["name"],
        "tool_calls_sha256": hashlib.sha256(raw_calls.encode()).hexdigest(),
        "arguments_sha256": content_hash({"view": "paired"}),
    }
    change_result(
        native,
        native_tool_calls_json=raw_calls,
        tool_invocation=invocation,
        tool_calls_sha256=hashlib.sha256(raw_calls.encode()).hexdigest(),
        tool_id=raw_call[0]["function"]["name"],
        arguments={"view": "paired"},
        result=result,
        result_sha256=content_hash(result),
        native_result_content=blocks,
        native_result_content_sha256=content_hash({"blocks": blocks}),
    )
    native["tool_schemas"].append({
        "type": "function",
        "function": {"name": "saea-tool-phase-knowledge-v1"},
    })
    payload.update(
        sample_id=native["sample_id"],
        speech_ref="earnings21-original/" + native["sample_id"],
        history=native["history"],
        tool_schemas=native["tool_schemas"],
        supplied_evidence=[],
    )
    _speech_history_texts(payload["history"])

    with pytest.raises(
        FrozenCoreError,
        match="refuses historical speech-feature descriptors",
    ):
        _transport(tmp_path).render_request(canonical_bytes(payload))


@pytest.mark.parametrize("tamper", ["missing", "path", "sha256", "mixed"])
def test_raw_identity_is_required_and_bound_to_loaded_audio(tmp_path, tamper):
    payload, _raw = _payload(tmp_path)
    if tamper == "missing":
        del payload["raw_speech_query"]
    elif tamper == "path":
        payload["raw_speech_query"]["media_relpath"] = "media/other.wav"
    elif tamper == "sha256":
        payload["raw_speech_query"]["sha256"] = "0" * 64
    else:
        payload["speech_feature_parts"] = []

    with pytest.raises(FrozenCoreError):
        _transport(tmp_path).render_request(canonical_bytes(payload))


def test_legacy_raw_prompt_order_remains_unchanged(tmp_path):
    payload, raw = _payload(tmp_path)
    payload["supplied_evidence"] = [{
        "evidence_id": "e1",
        "source_uri": "test://e1",
        "content": "A bound fact.",
    }]
    body = _transport(
        tmp_path, prompt_order="system-instruction-v1"
    ).render_request(canonical_bytes(payload))
    assert body["messages"][0] == {
        "role": "system",
        "content": payload["task_instruction"],
    }
    assert body["messages"][1]["content"][0] == {
        "type": "text",
        "text": "[evidence e1] A bound fact.",
    }
    assert base64.b64decode(
        body["messages"][1]["content"][1]["input_audio"]["data"]
    ) == raw
