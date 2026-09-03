"""Contact-free unit tests for the semantic AgentLoop flight launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

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
        "TRANSCRIPT_TOP16_USE",
        "MODEL_QUERY_TOP16_USE",
        "RRF_FUSED_TOP16_USE",
        "SAME_STRATUM_SHUFFLED_FUSED_USE",
    )
    assert module.SAMPLE_COUNT == 104
    assert module.GENERATION_CONTACTS == 624
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
    assert module.MANIFEST_ROLES == (
        "direct_m0",
        "obs_semantic_retrieval",
        "transcript_top16_use",
        "model_query_top16_use",
        "rrf_fused_top16_use",
        "same_stratum_shuffled_fused_use",
    )


def test_exact_preprocess_v2_and_promoted_packet_tokens_are_bound() -> None:
    module = _launcher()
    roster = module.validate_roster(_roster(module))
    report = json.loads(module.PREPROCESS_REPORT_PATH.read_text(encoding="utf-8"))
    promotion_path = Path(
        "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a/"
        "A2T-SEMANTIC-AGENTLOOP-104-V1-promotion.json"
    )
    promotion = json.loads(promotion_path.read_text(encoding="utf-8"))

    packets = module.validate_preprocessing_documents(report, promotion, roster)

    assert len(packets.bindings) == 104
    assert len(packets.speech_tokens) == 104
    values = sorted(packets.speech_tokens.values())
    assert min(values) == 26
    assert max(values) == 481
    assert packets.promotion_receipt_sha256 == (
        "6f5d77438b50ebba8130122c6cc39acff18f0707836c61e72a03f6af1380c6b5"
    )
    sample_id = roster.sample_ids[0]
    assert packets.bindings[sample_id]["packet_id"] == sample_id.replace(":", "/", 1)

    drift = json.loads(json.dumps(promotion))
    drift["speech_feature_tokens"]["distribution"]["max"] = 480
    with pytest.raises(RuntimeError, match="distribution drift"):
        module.validate_preprocessing_documents(report, drift, roster)


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
        gate("http://127.0.0.1:1/v1/chat/completions", json.dumps({**base, "n": 2}).encode())
    missing = dict(base)
    del missing["response_format"]
    with pytest.raises(RuntimeError, match="per-request response_format"):
        gate("http://127.0.0.1:1/v1/chat/completions", json.dumps(missing).encode())


def test_direct_m0_alone_may_omit_response_format_after_exact_measurement() -> None:
    module = _launcher()
    marker = "<|SPEECH|>"
    events = []
    body = {
        "messages": [{"role": "user", "content": [{
            "type": "input_speech_features",
            "speech_features": {"packet_id": "p"},
        }]}],
        "max_tokens": 32,
    }

    def post_json(endpoint, payload):
        events.append((endpoint, payload))
        return ({"prompt": f"left{marker}right"} if endpoint == "/apply-template"
                else {"tokens": [1]})

    gate = module.ExactPromptBudgetTransport(
        media_marker=marker,
        speech_packet_tokens={"p": 13},
        post_json=post_json,
        send=lambda _url, raw: events.append(("send", raw)) or b"{}",
        request_role="direct_m0",
        allow_missing_response_format=True,
    )
    gate("http://127.0.0.1:1/v1/chat/completions", json.dumps(body).encode())
    assert events[0] == ("/apply-template", {"messages": body["messages"]})
    assert [event[0] for event in events] == [
        "/apply-template", "/tokenize", "/tokenize", "send"
    ]
    assert gate.audits[0]["response_format_sha256"] is None
    assert gate.audits[0]["request_role"] == "direct_m0"

    with pytest.raises(RuntimeError, match="reserved for the direct M0"):
        module.ExactPromptBudgetTransport(
            media_marker=marker,
            speech_packet_tokens={"p": 13},
            post_json=post_json,
            send=lambda _url, _raw: b"{}",
            request_role="obs_semantic_retrieval",
            allow_missing_response_format=True,
        )


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
        gate("http://127.0.0.1:1/v1/chat/completions", json.dumps(body).encode())

    body["messages"][0]["content"][0]["speech_features"]["packet_id"] = "known"
    del body["max_tokens"]
    with pytest.raises(RuntimeError, match="max_tokens"):
        gate("http://127.0.0.1:1/v1/chat/completions", json.dumps(body).encode())


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


def test_concrete_runtime_factory_module_loads_without_contact() -> None:
    module = _launcher()
    factory_path = LAUNCHER.with_name("local_runtime_factory.py")

    factory = module._load_runtime_factory(
        f"{factory_path}:build_runtime",
        expected_sha256=module.sha256_file(factory_path),
    )

    assert callable(factory)
    with pytest.raises(RuntimeError, match="runtime factory path"):
        module._load_runtime_factory(
            f"{factory_path}:build_runtime",
            expected_sha256="0" * 64,
        )
    assert factory.__module__ == "a2t_flight_runtime"


def _resolved_hashes(module):
    return {
        name: (expected if expected is not None else "a" * 64)
        for name, expected in module.REQUIRED_AUTHORITY_HASHES.items()
    }


class _Runtime:
    agent_executor_id = "openjiuwen-workflow-v1"
    slot_count = 2
    queue_depth = 4
    registered_tool_names = ("knownTool",)

    def __init__(self, module, sample_ids):
        self.module = module
        self.sample_ids = sample_ids
        self.events = []

    def assert_attempt_unopened(self):
        self.events.append("unopened")

    def start_generation(self, window):
        self.events.append(f"start-gen:{window}")

    def stop_generation(self, window):
        self.events.append(f"stop-gen:{window}")

    def start_embedding(self):
        self.events.append("start-embed")

    def stop_embedding(self):
        self.events.append("stop-embed")

    def m0_kwargs(self, bindings):
        assert set(bindings) == set(self.sample_ids)
        return {"kind": "m0"}

    def observation_kwargs(self, bindings):
        assert set(bindings) == set(self.sample_ids)
        return {"kind": "obs"}

    def embedding_client(self):
        return object()

    def semantic_index(self):
        return object()

    def selected_tool_ground(self):
        return object()

    def use_kwargs(self, public_phase, material, bindings):
        self.events.append(f"prepare:{public_phase}")
        assert set(material) == set(self.sample_ids)
        assert set(bindings) == set(self.sample_ids)
        return {"kind": public_phase}

    def prompt_budget_audits(self):
        return tuple(
            {
                "context_decision": "ALLOW",
                "required_window_tokens": 100,
            }
            for _ in range(624)
        )

    def seal_runtime_receipt(self, role, summary):
        self.events.append(f"runtime:{role}")
        assert len(summary.results) == 104
        return {
            "role": role,
            "status": "STOPPED",
            "sha256": self.module.sha256_json({"runtime_role": role}),
        }

    def seal_manifest(self, role, summary, extras):
        self.events.append(f"seal:{role}")
        assert len(summary.results) == 104
        assert extras["protocol_sha256"] == self.module.PROTOCOL_SHA256
        if role.endswith("use"):
            assert "tool_ranking_receipts" in extras
        return {
            "role": role,
            "status": "COMPLETE",
            "complete_rows": 104,
            "manifest": f"{role}.run-manifest.json",
            "runtime_receipt_sha256": extras["runtime_receipt"]["sha256"],
        }

    def seal_flight(self, descriptors, events, config_hash, protocol_hash):
        assert tuple(row["role"] for row in descriptors) == self.module.MANIFEST_ROLES
        assert events[-1] == "seal"
        assert config_hash == self.module.CONFIG_SHA256
        assert protocol_hash == self.module.PROTOCOL_SHA256
        return {"status": "SEALED", "manifest_count": len(descriptors)}


def test_contact_ready_coordinator_runs_exact_order_and_seals_six_manifests(
    monkeypatch,
) -> None:
    module = _launcher()
    roster = module.validate_roster(_roster(module))
    bindings = {
        sample_id: {"packet_id": sample_id.replace(":", "/", 1), "sha256": "b" * 64}
        for sample_id in roster.sample_ids
    }
    packets = module.PreprocessedPackets(
        bindings=bindings,
        speech_tokens={value["packet_id"]: 26 for value in bindings.values()},
        feature_root=module.PROMOTED_PACKET_ROOT,
        promotion_receipt_sha256=module.PROMOTION_RECEIPT_SHA256,
        decoder_gguf_sha256=module.GENERATION_DECODER_GGUF_SHA256,
    )
    runtime = _Runtime(module, roster.sample_ids)

    def summary(text):
        return SimpleNamespace(
            results=tuple(
                SimpleNamespace(sample_id=sample_id, final_response_text=text)
                for sample_id in roster.sample_ids
            )
        )

    def m0_runner(**kwargs):
        runtime.events.append(kwargs["kind"])
        return summary("[]")

    def agent_runner(*, phase, **kwargs):
        runtime.events.append(f"agent:{phase}:{kwargs['kind']}")
        if phase == module.OBSERVATION_PHASE:
            return summary(
                '{"transcript":"Turn the lights on.",'
                '"retrieval_query":"Enable the room lights."}'
            )
        return summary("[]")

    def fake_embed(_client, observations):
        runtime.events.append("embed-208")
        assert len(observations) == 104
        return {"vectors": ()}

    routing = SimpleNamespace(
        transcript_packets={sample_id: object() for sample_id in roster.sample_ids},
        model_query_packets={sample_id: object() for sample_id in roster.sample_ids},
        fused_packets={sample_id: object() for sample_id in roster.sample_ids},
        routing_receipts={sample_id: {"full": True} for sample_id in roster.sample_ids},
    )

    def fake_route(**kwargs):
        runtime.events.append("route-full-rankings")
        return routing

    arm_map = {sample_id: object() for sample_id in roster.sample_ids}
    monkeypatch.setattr(module, "embed_observations", fake_embed)
    monkeypatch.setattr(module, "route_observations", fake_route)
    monkeypatch.setattr(
        module,
        "build_use_materials",
        lambda **_kwargs: module.UseArmMaterial(
            transcript=arm_map,
            model_query=arm_map,
            fused=arm_map,
            shuffled_fused=arm_map,
        ),
    )

    receipt = module.execute_contact_ready_flight(
        runtime=runtime,
        roster=roster,
        packets=packets,
        authority_hashes=_resolved_hashes(module),
        m0_runner=m0_runner,
        agentloop_runner=agent_runner,
    )

    assert receipt == {"status": "SEALED", "manifest_count": 6}
    assert runtime.events[:6] == [
        "unopened",
        "start-gen:pre-embedding",
        "m0",
        "agent:OBS_SEMANTIC_STATE:obs",
        "stop-gen:pre-embedding",
        "start-embed",
    ]
    assert runtime.events.count("embed-208") == 1
    assert runtime.events.count("route-full-rankings") == 1
    assert [event for event in runtime.events if event.startswith("prepare:")] == [
        "prepare:TRANSCRIPT_TOP16_USE",
        "prepare:MODEL_QUERY_TOP16_USE",
        "prepare:RRF_FUSED_TOP16_USE",
        "prepare:SAME_STRATUM_SHUFFLED_FUSED_USE",
    ]
    assert [event for event in runtime.events if event.startswith("seal:")] == [
        f"seal:{role}" for role in module.MANIFEST_ROLES
    ]
    assert [event for event in runtime.events if event.startswith("runtime:")] == [
        f"runtime:{role}" for role in module.MANIFEST_ROLES
    ]


def test_invalid_observation_aborts_before_embedding(monkeypatch) -> None:
    module = _launcher()
    roster = module.validate_roster(_roster(module))
    bindings = {
        sample_id: {"packet_id": sample_id.replace(":", "/", 1), "sha256": "b" * 64}
        for sample_id in roster.sample_ids
    }
    packets = module.PreprocessedPackets(
        bindings=bindings,
        speech_tokens={value["packet_id"]: 26 for value in bindings.values()},
        feature_root=module.PROMOTED_PACKET_ROOT,
        promotion_receipt_sha256=module.PROMOTION_RECEIPT_SHA256,
        decoder_gguf_sha256=module.GENERATION_DECODER_GGUF_SHA256,
    )
    runtime = _Runtime(module, roster.sample_ids)
    def result(text):
        return SimpleNamespace(
            results=tuple(
                SimpleNamespace(sample_id=sample_id, final_response_text=text)
                for sample_id in roster.sample_ids
            )
        )

    with pytest.raises(RuntimeError, match="invalid JSON"):
        module.execute_contact_ready_flight(
            runtime=runtime,
            roster=roster,
            packets=packets,
            authority_hashes=_resolved_hashes(module),
            m0_runner=lambda **_kwargs: result("[]"),
            agentloop_runner=lambda **_kwargs: result("not-json"),
        )
    assert runtime.events == [
        "unopened",
        "start-gen:pre-embedding",
        "stop-gen:pre-embedding",
    ]


def test_cli_is_preflight_only_and_never_contacts(capsys) -> None:
    module = _launcher()

    assert module.main(["--preflight-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PREFLIGHT_ONLY_NO_CONTACT"
    assert report["generation_contact_ceiling"] == 624
    assert report["embedding_physical_request_ceiling"] == 7
    assert report["contacts_made"] == {
        "embedding_physical_requests": 0,
        "generation": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    with pytest.raises(SystemExit, match="No contact is the default"):
        module.main([])
