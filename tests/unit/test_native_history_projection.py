"""Native chat projection preserves real call/result turns and bound evidence."""

import copy
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.model import FrozenCoreError
from speech_aware_evidence_acquisition.core.model.native_history import project_native_history
from speech_aware_evidence_acquisition.core.model.transport import _speech_history_texts
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_phase_native_tools import ARGS, LIVE, LiveProvider, call, dispatcher, staged_native


def world(*, repeat=False, packet_id=None, packet_sha256=None):
    context = staged_native(call())
    if packet_id is not None:
        context = staged_native(call(), query_state=replace(
            context.query_state, speech_packet_id=packet_id,
            speech_packet_sha256=packet_sha256,
        ))
    custody_runtime = SimpleNamespace(
        _samples=[SimpleNamespace(sample_id=context.sample_id)],
        _live_speech_source_bindings={context.sample_id: {
            "packet_id": context.query_state.speech_packet_id,
            "packet_sha256": context.query_state.speech_packet_sha256,
        }},
        _client=SimpleNamespace(record_tool_call=lambda **_facts: None),
        assert_generation_lease=lambda: None,
        _live_speech_units=lambda: None,
    )
    tool = dispatcher(LIVE, provider=LiveProvider(), custody=lambda **facts:
                      FlightRuntime._record_phase_tool_contact(custody_runtime, **facts))
    step = tool("decision-1", "decision-2", context)
    states = (*context.agent_states, step.state)
    if repeat:
        context = staged_native(
            call(), phase="decision-2", prior_states=states,
            query_state=replace(context.query_state, agent_state_ids=tuple(s.state_id for s in states)),
        )
        step = tool("decision-2", "final", context)
        states = (*context.agent_states, step.state)
    history = _agent_history(
        agent_state=[s.as_json() for s in states],
        agent_contact_id="final", contact_instruction="Deliver the final task JSON.",
    )
    query = replace(context.query_state, agent_state_ids=tuple(s.state_id for s in states))
    blocks = tool.render_values(tool.snapshot, query, states)
    payload = {
        "sample_id": context.sample_id,
        "speech_feature_parts": [{
            "packet_id": context.query_state.speech_packet_id,
            "sha256": context.query_state.speech_packet_sha256, "role": "query",
        }],
        "speech_packet_sha256": context.query_state.speech_packet_sha256,
        "history": history,
        "tool_schemas": list(tool.native_tool_schemas()),
        "decoding_params": {"tool_choice": "none", "parallel_tool_calls": False},
        "supplied_evidence": [
            {"evidence_id": b["evidence_id"], "content": b["text"], "source_uri": b["source_uri"]}
            for b in blocks if b["type"] == "text"
        ],
    }
    history_texts = _speech_history_texts(history)
    query_part = {"type": "input_speech_features",
                  "speech_features": payload["speech_feature_parts"][0]}
    messages = [
        {"role": "system", "content": "Solve the speech task."},
        {"role": "user", "content": [
            query_part,
            *({"type": "text", "text": f"[evidence {b['evidence_id']}] {b['content']}"}
              for b in payload["supplied_evidence"]),
            *({"type": "text", "text": text} for text in history_texts),
        ]},
    ]
    return payload, messages, history_texts


def project(payload, messages, texts):
    return project_native_history(payload=payload, messages=messages, state_texts=texts)


def test_actual_dispatch_retains_raw_call_and_observation_in_native_turns():
    payload, messages, texts = world()
    before = copy.deepcopy((payload, messages))
    result, descriptors = project(payload, messages, texts)
    assert [m["role"] for m in result] == ["system", "user", "assistant", "tool", "user"]
    native_call = result[2]["tool_calls"][0]
    assert native_call == call()[0]
    assert json.loads(native_call["function"]["arguments"]) == ARGS
    assert result[3]["tool_call_id"] == native_call["id"]
    assert "Set the timer for fifteen minutes." in result[3]["content"]
    assert "Set the timer for fifteen minutes." not in json.dumps(result[1])
    assert sum(json.dumps(m).count("Set the timer for fifteen minutes.") for m in result) == 1
    assert result[-1]["content"][-1]["text"].endswith("Deliver the final task JSON.")
    assert descriptors == []
    assert (payload, messages) == before


def test_repeated_cached_evidence_retains_both_calls_but_one_transcript():
    payload, messages, texts = world(repeat=True)
    result, _ = project(payload, messages, texts)
    assert [m["role"] for m in result].count("assistant") == 2
    assert [m["role"] for m in result].count("tool") == 2
    assert sum(json.dumps(m).count("Set the timer for fifteen minutes.") for m in result) == 1
    tool_results = [json.loads(m["content"]) for m in result if m["role"] == "tool"]
    assert tool_results[1]["previously_returned_evidence_ids"] == ["live-one"]


def change_result(payload, **changes):
    state = next(s for s in payload["history"] if s.get("state_kind") == "tool-result")
    doc = json.loads(state["content"])
    doc.update(changes)
    state["content"] = json.dumps(doc, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()


@pytest.mark.parametrize("changes", [
    {"tool_calls_sha256": "0" * 64},
    {"tool_call_id": "foreign-call"},
    {"native_source_state_id": "foreign-state"},
    {"result_sha256": "0" * 64},
    {"native_result_content_sha256": "0" * 64},
    {"tool_invocation": None},
    {"core_request_id": "foreign-request"},
    {"sample_id": "foreign-sample"},
])
def test_changed_native_lineage_fails_closed(changes):
    payload, messages, texts = world()
    change_result(payload, **changes)
    with pytest.raises(FrozenCoreError):
        project(payload, messages, texts)


def test_unbound_observation_and_missing_native_controls_fail_closed():
    payload, messages, texts = world()
    payload["supplied_evidence"][0]["content"] = "A substituted transcript."
    with pytest.raises(FrozenCoreError):
        project(payload, messages, texts)
    payload, messages, texts = world()
    del payload["decoding_params"]["tool_choice"]
    with pytest.raises(FrozenCoreError):
        project(payload, messages, texts)


def test_history_without_new_native_envelope_is_byte_identical():
    payload, messages, texts = world()
    state = next(s for s in payload["history"] if s.get("state_kind") == "tool-result")
    doc = json.loads(state["content"])
    for key in ("native_tool_calls_json", "native_source_state_id",
                "native_result_content", "native_result_content_sha256"):
        doc.pop(key, None)
    state["content"] = json.dumps(doc, sort_keys=True)
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    result, descriptors = project(payload, messages, texts)
    assert json.dumps(result) == json.dumps(messages)
    assert descriptors == []


def test_historical_paired_knowledge_packets_remain_after_their_call():
    payload, messages, texts = world()
    state = next(s for s in payload["history"] if s.get("state_kind") == "tool-result")
    doc = json.loads(state["content"])
    raw_call = json.loads(doc["native_tool_calls_json"])
    raw_call[0]["function"] = {"name": "saea-tool-phase-knowledge-v1", "arguments": '{"view":"paired"}'}
    raw_calls = json.dumps(raw_call)
    descriptor = {"packet_id": "train/exemplar", "sha256": "e" * 64, "role": "key"}
    block = {"type": "input_speech_features", "speech_features": descriptor}
    blocks = [{"type": "text", "text": "A discriminative training value.",
               "evidence_id": "value-one",
               "source_uri": "knowledge-snapshot://" + doc["snapshot_sha256"] + "/value-one",
               "knowledge_role": "value"}, block]
    result = {"knowledge_view": "paired", "selected_value_ids": ["value-one"],
              "speech_evidence_order": [{"value_id": "value-one", "packet_id": "train/exemplar",
                                         "packet_sha256": "e" * 64}]}
    invocation = {**doc["tool_invocation"],
                  "tool_id": raw_call[0]["function"]["name"],
                  "tool_calls_sha256": hashlib.sha256(raw_calls.encode()).hexdigest(),
                  "arguments_sha256": content_hash({"view": "paired"})}
    change_result(payload, native_tool_calls_json=raw_calls, tool_invocation=invocation,
                  tool_calls_sha256=hashlib.sha256(raw_calls.encode()).hexdigest(),
                  tool_id=raw_call[0]["function"]["name"], arguments={"view": "paired"},
                  result=result, result_sha256=content_hash(result),
                  native_result_content=blocks,
                  native_result_content_sha256=content_hash({"blocks": blocks}))
    payload["tool_schemas"].append({"type": "function", "function": {
        "name": "saea-tool-phase-knowledge-v1"}})
    payload["supplied_evidence"] = []
    # The current view may have changed; preserve packets in earlier bound tool results.
    messages[1]["content"] = [messages[1]["content"][0], *messages[1]["content"][-len(texts):]]
    rendered, descriptors = project(payload, messages, texts)
    assert descriptors == [descriptor]
    assert "A discriminative training value." in rendered[3]["content"]
    assert rendered[4]["role"] == "user"
    assert block in rendered[4]["content"]
    assert all(part.get("speech_features", {}).get("role") != "key"
               for part in rendered[1]["content"])


def test_plain_legacy_tool_result_remains_unchanged():
    payload, messages, texts = world()
    state = next(s for s in payload["history"] if s.get("state_kind") == "tool-result")
    state["content"] = "An old generic tool observation."
    state["content_sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
    result, descriptors = project(payload, messages, texts)
    assert result == messages and descriptors == []


@pytest.mark.parametrize("field,value", [
    ("sample_id", "wrong-sample"),
    ("request_id", "wrong-request"),
    ("arguments_sha256", "0" * 64),
    ("speech_packet_sha256", "0" * 64),
    ("schema", "unaccounted-result"),
])
def test_foreign_custody_is_rejected(field, value):
    payload, messages, texts = world()
    state = next(s for s in payload["history"] if s.get("state_kind") == "tool-result")
    doc = json.loads(state["content"])
    change_result(payload, tool_invocation={**doc["tool_invocation"], field: value})
    with pytest.raises(FrozenCoreError, match="custody"):
        project(payload, messages, texts)
