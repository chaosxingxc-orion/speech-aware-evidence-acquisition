"""Contact-free unit tests for the semantic AgentLoop flight launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


LAUNCHER = Path(__file__).with_name("launch_semantic_agentloop_104.py")


def _launcher():
    name = "test_semantic_agentloop_104_launcher"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _roster(module):
    return json.loads(module.ROSTER_PATH.read_text(encoding="utf-8"))


def test_protocol_is_exact_and_hashes_are_mechanical() -> None:
    module = _launcher()

    assert module.PHASE_ORDER == (
        "M0_DIRECT",
        "OBS_SEMANTIC_STATE",
        "EMBED_TRANSCRIPT_AND_RETRIEVAL_QUERY",
        "USE_MATCHED_SELECTED_TOOLS",
        "USE_SAME_TIER_SHUFFLED_SELECTED_TOOLS",
    )
    assert module.SAMPLE_COUNT == 104
    assert module.GENERATION_CONTACTS == 416
    assert module.SEMANTIC_ITEM_COUNT == 208
    assert module.EMBEDDING_BATCH_SIZE == 32
    assert module.EMBEDDING_PHYSICAL_REQUESTS == 7
    assert module.SLOT_COUNT == 2
    assert module.QUEUE_DEPTH == 4
    assert module.PHYSICAL_CONTEXT_PER_SLOT == 32_768
    assert module.CONTEXT_RESERVE == 8_192
    assert module.MAX_REQUIRED_WINDOW_TOKENS == 24_576
    assert module.REGISTERED_SPECIAL_TOKEN_RESERVE == 2
    assert module.RRF_CONSTANT == 60
    assert module.TOP_K == 16
    assert module.CONFIG_SHA256 == module.sha256_json(module.protocol_config())
    assert module.PROTOCOL_SHA256 == module.protocol_hash()


def test_fresh_roster_is_exactly_104_unexposed_discovery_rows() -> None:
    module = _launcher()
    roster = _roster(module)

    validated = module.validate_roster(roster)

    assert len(validated.sample_ids) == 104
    assert set(validated.tiers.values()) == {
        "tier1_direct",
        "tier2_parametric",
        "tier3_multi_intent",
        "tier4_implicit",
        "tier5_needle",
        "tier6_correction",
        "tier7_multiturn",
        "tier8_intent_blending",
    }
    assert all(
        tuple(validated.tiers.values()).count(tier) == 13
        for tier in set(validated.tiers.values())
    )
    assert roster["contacts"] == {
        "audio": 0,
        "model": 0,
        "network": 0,
        "scorer": 0,
    }

    drift = json.loads(json.dumps(roster))
    drift["items"][0]["audio_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="media roster hash drift"):
        module.validate_roster(drift)


def test_observation_embedding_schedule_is_208_items_in_frozen_batches() -> None:
    module = _launcher()
    roster = module.validate_roster(_roster(module))
    observations = {
        sample_id: module.ObservationState(
            transcript=f"Transcript for {index}.",
            retrieval_query=f"Perform requested action {index}.",
            response_sha256=f"{index % 16:x}" * 64,
        )
        for index, sample_id in enumerate(roster.sample_ids)
    }

    batches = module.build_embedding_batches(observations)

    assert tuple(len(batch) for batch in batches) == (32, 32, 32, 32, 32, 32, 16)
    flat = tuple(item for batch in batches for item in batch)
    assert len(flat) == 208
    assert len({item[0] for item in flat}) == 208
    for index, sample_id in enumerate(sorted(roster.sample_ids)):
        transcript, query = flat[index * 2 : index * 2 + 2]
        assert transcript[0] == f"semantic:{sample_id}:transcript"
        assert transcript[1] == observations[sample_id].transcript
        assert query[0] == f"semantic:{sample_id}:retrieval_query"
        assert query[1] == observations[sample_id].retrieval_query


class _BatchClient:
    def __init__(self) -> None:
        self.calls = []

    def embed_text_batch(self, items):
        self.calls.append(tuple(items))
        return tuple(
            type(
                "Vector", (), {"contact_id": item[0], "values": (float(index + 1), 1.0)}
            )()
            for index, item in enumerate(items)
        )


def test_embedding_execution_uses_only_physical_batches_of_32() -> None:
    module = _launcher()
    roster = module.validate_roster(_roster(module))
    observations = {
        sample_id: module.ObservationState(
            transcript="A faithful English transcript.",
            retrieval_query="Perform the requested action.",
            response_sha256="a" * 64,
        )
        for sample_id in roster.sample_ids
    }
    client = _BatchClient()

    vectors = module.embed_observations(client, observations)

    assert len(vectors) == 208
    assert tuple(map(len, client.calls)) == (32, 32, 32, 32, 32, 32, 16)


def test_precontact_gate_sends_exact_messages_then_refuses_overflow() -> None:
    module = _launcher()
    events = []
    marker = "<|SPEECH|>"
    response_format = {
        "type": "json_schema",
        "json_schema": {"name": "one", "strict": True, "schema": {"type": "array"}},
    }
    body = {
        "messages": [
            {"role": "system", "content": "Act."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "before"},
                    {
                        "type": "input_speech_features",
                        "speech_features": {"packet_id": "p"},
                    },
                    {"type": "text", "text": "after"},
                ],
            },
        ],
        "response_format": response_format,
        "temperature": 0,
        "max_tokens": 32,
        "id_slot": 1,
    }

    def post_json(path, payload):
        events.append((path, payload))
        if path == "/apply-template":
            assert payload == {
                "messages": body["messages"],
                "response_format": response_format,
            }
            return {"prompt": f"left{marker}right"}
        assert path == "/tokenize"
        return {"tokens": [1, 2, 3]}

    def send(url, raw):
        events.append(("send", json.loads(raw)))
        return b'{"choices":[{"message":{"content":"[]"}}]}'

    gate = module.ExactPromptBudgetTransport(
        media_marker=marker,
        speech_packet_tokens={"p": 13},
        post_json=post_json,
        send=send,
    )
    result = gate(
        "http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode()
    )

    assert result.startswith(b'{"choices"')
    assert [event[0] for event in events] == [
        "/apply-template",
        "/tokenize",
        "/tokenize",
        "send",
    ]
    assert gate.audits[0]["measured_text_tokens"] == 6
    assert gate.audits[0]["speech_feature_tokens"] == 13
    assert gate.audits[0]["completion_token_ceiling"] == 32
    assert gate.audits[0]["special_token_reserve"] == 2
    assert gate.audits[0]["required_window_tokens"] == 53
    assert gate.audits[0]["operational_margin_tokens"] == 24_523
    assert gate.audits[0]["response_format_sha256"] == module.sha256_json(
        response_format
    )

    events.clear()

    def overflow(_path, payload):
        if "messages" in payload:
            return {"prompt": f"left{marker}right"}
        return {"tokens": list(range(module.MAX_REQUIRED_WINDOW_TOKENS - 16))}

    refusing = module.ExactPromptBudgetTransport(
        media_marker=marker,
        speech_packet_tokens={"p": 13},
        post_json=overflow,
        send=send,
    )
    with pytest.raises(RuntimeError, match="required window .* exceeds 24576"):
        refusing("http://127.0.0.1:8080/v1/chat/completions", json.dumps(body).encode())
    assert events == []


def test_precontact_gate_rejects_prompt_level_multi_sample_and_missing_schema() -> None:
    module = _launcher()
    gate = module.ExactPromptBudgetTransport(
        media_marker="<|SPEECH|>",
        speech_packet_tokens={"p": 13},
        post_json=lambda _path, _payload: pytest.fail("must not contact"),
        send=lambda _url, _raw: pytest.fail("must not contact"),
    )
    base = {"messages": [{"role": "user", "content": "x"}], "response_format": {}}

    with pytest.raises(RuntimeError, match="n=1"):
        gate("http://127.0.0.1:1", json.dumps({**base, "n": 2}).encode())
    missing = dict(base)
    del missing["response_format"]
    with pytest.raises(RuntimeError, match="per-request response_format"):
        gate("http://127.0.0.1:1", json.dumps(missing).encode())


def test_precontact_gate_requires_exact_packet_tokens_and_completion_ceiling() -> None:
    module = _launcher()
    marker = "<|SPEECH|>"
    body = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {"packet_id": "unknown"},
                    }
                ],
            }
        ],
        "response_format": {"type": "json_schema"},
        "max_tokens": 32,
    }
    gate = module.ExactPromptBudgetTransport(
        media_marker=marker,
        speech_packet_tokens={"known": 13},
        post_json=lambda _path, _payload: pytest.fail("must not contact"),
        send=lambda _url, _raw: pytest.fail("must not contact"),
    )
    with pytest.raises(RuntimeError, match="packet token count"):
        gate("http://127.0.0.1:1", json.dumps(body).encode())

    body["messages"][0]["content"][0]["speech_features"]["packet_id"] = "known"
    del body["max_tokens"]
    with pytest.raises(RuntimeError, match="max_tokens"):
        gate("http://127.0.0.1:1", json.dumps(body).encode())


def test_server_phase_gate_enforces_separate_embedding_and_two_generation_windows() -> (
    None
):
    module = _launcher()
    gate = module.ServerPhaseGate()

    gate.start_generation("pre-embedding")
    with pytest.raises(RuntimeError, match="already active"):
        gate.start_embedding()
    gate.stop_generation("pre-embedding")
    gate.start_embedding()
    gate.stop_embedding()
    gate.start_generation("post-embedding")
    gate.stop_generation("post-embedding")
    gate.seal()

    assert gate.events == (
        "start-generation:pre-embedding",
        "stop-generation:pre-embedding",
        "start-embedding",
        "stop-embedding",
        "start-generation:post-embedding",
        "stop-generation:post-embedding",
        "seal",
    )


def test_cli_is_preflight_only_and_never_contacts(capsys) -> None:
    module = _launcher()

    assert module.main(["--preflight-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PREFLIGHT_ONLY_NO_CONTACT"
    assert report["contacts_made"] == {
        "embedding_physical_requests": 0,
        "generation": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    with pytest.raises(SystemExit, match="execution authority"):
        module.main([])
