"""Model-free tests for the fresh semantic Audio2Tool AgentLoop boundary."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground import (
    SelectedToolDecisionPacket,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_semantic_agentloop as flight,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext


REGISTERED = ("adjustVolume", "setAdaptiveLighting", "getWeather")


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    ).hexdigest()


def _packet(name: str, *, count: int = 1) -> SelectedToolDecisionPacket:
    names = tuple(f"{name}{index}" for index in range(count))
    text = (
        "SELECTED-TOOL DECISION CARDS\n"
        + "\n".join(f"Exact tool: {tool}" for tool in names)
        + "\n"
    )
    branches = [
        {
            "type": "object",
            "properties": {
                "name": {"const": tool},
                "arguments": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            },
            "required": ["name", "arguments"],
            "additionalProperties": False,
        }
        for tool in names
    ]
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "audio2tool_selected_calls",
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": 0,
                "maxItems": 7,
                "items": {"oneOf": branches},
            },
        },
    }
    return SelectedToolDecisionPacket(
        selected_tool_names=names,
        text=text,
        text_sha256=hashlib.sha256(text.encode("ascii")).hexdigest(),
        response_format=response_format,
        response_format_sha256=_canonical_hash(response_format),
        report={"selected_tool_count": count},
    )


def _observation(index: int = 0) -> flight.ObservationState:
    response = json.dumps(
        {
            "transcript": f"please make the room comfortable number {index}",
            "retrieval_query": "change the desired room condition",
        },
        separators=(",", ":"),
    )
    return flight.parse_observation_response(response, registered_tool_names=REGISTERED)


def _sample(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        sample_id=f"fresh:{index:03d}",
        audio_ref=AudioRef(path=f"audio/{index:03d}.wav", sha256=f"{index + 1:064x}"),
        audio_seconds=1.0,
    )


def _context(sample_id: str = "fresh:000") -> AgentRuntimeContext:
    query = QueryState(
        query_id=f"query:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256="c" * 64,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=query,
        task_contract="fresh phase",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def test_observation_schema_and_exact_parser_are_bounded_ascii_and_label_free() -> None:
    response_format = flight.observation_response_format()
    schema = response_format["json_schema"]["schema"]
    assert schema["type"] == "object"
    assert schema["required"] == ["transcript", "retrieval_query"]
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]) == {"transcript", "retrieval_query"}
    assert (
        schema["properties"]["transcript"]["maxLength"]
        == flight.OBS_TRANSCRIPT_MAX_CHARS
    )
    assert (
        schema["properties"]["retrieval_query"]["maxLength"]
        == flight.OBS_QUERY_MAX_CHARS
    )

    raw = '{"transcript":"turn the volume down","retrieval_query":"reduce the current audio level"}'
    parsed = flight.parse_observation_response(raw, registered_tool_names=REGISTERED)
    assert parsed.transcript == "turn the volume down"
    assert parsed.retrieval_query == "reduce the current audio level"
    assert parsed.response_sha256 == hashlib.sha256(raw.encode("ascii")).hexdigest()


@pytest.mark.parametrize(
    ("raw", "message"),
    (
        ('{"transcript":"ok","retrieval_query":"reduce audio","extra":1}', "exactly"),
        (
            '{"transcript":"ok","transcript":"again","retrieval_query":"reduce audio"}',
            "duplicate",
        ),
        ('{"transcript":"caf\\u00e9","retrieval_query":"reduce audio"}', "ASCII"),
        (
            '{"transcript":"ok","retrieval_query":"adjustVolume now"}',
            "registered tool name",
        ),
        ('{"transcript":"ok","retrieval_query":"volume"}', "paraphrase"),
        ("not json", "JSON"),
    ),
)
def test_observation_parser_refuses_without_repair_or_retry(
    raw: str, message: str
) -> None:
    with pytest.raises(flight.SemanticAgentLoopError, match=message):
        flight.parse_observation_response(raw, registered_tool_names=REGISTERED)


def test_matched_and_same_tier_shuffled_change_only_equal_count_donor_packets() -> None:
    ids = tuple(f"fresh:{index:03d}" for index in range(4))
    observations = {
        sample_id: _observation(index) for index, sample_id in enumerate(ids)
    }
    packets = {
        sample_id: _packet(f"candidate{index}", count=2)
        for index, sample_id in enumerate(ids)
    }
    tiers = {sample_id: "implicit" for sample_id in ids}

    matched, shuffled = flight.build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=packets,
        sample_tiers=tiers,
        seed="fresh-104-v1",
    )

    assert set(matched) == set(shuffled) == set(ids)
    for sample_id in ids:
        assert matched[sample_id].recipient_observation is observations[sample_id]
        assert shuffled[sample_id].recipient_observation is observations[sample_id]
        assert matched[sample_id].donor_sample_id == sample_id
        assert shuffled[sample_id].donor_sample_id != sample_id
        assert shuffled[sample_id].tier == matched[sample_id].tier
        assert len(shuffled[sample_id].packet.selected_tool_names) == len(
            matched[sample_id].packet.selected_tool_names
        )
        assert (
            shuffled[sample_id].packet is packets[shuffled[sample_id].donor_sample_id]
        )

    donors = flight.deterministic_same_stratum_derangement(
        {sample_id: (tiers[sample_id], 2) for sample_id in ids},
        seed="fresh-104-v1",
    )
    assert donors == {
        sample_id: shuffled[sample_id].donor_sample_id for sample_id in ids
    }


def test_derangement_refuses_singleton_tier_and_card_count_strata() -> None:
    with pytest.raises(flight.SemanticAgentLoopError, match="derangement"):
        flight.deterministic_same_stratum_derangement(
            {"one": ("implicit", 5), "two": ("direct", 5)}, seed="fixed"
        )


def test_use_adapter_system_is_exact_selected_card_and_receipt_binds_actual_request() -> (
    None
):
    sample = _sample(0)
    observation = _observation()
    packet = _packet("candidate", count=2)
    material = flight.UseMaterial(
        recipient_sample_id=sample.sample_id,
        donor_sample_id=sample.sample_id,
        tier="implicit",
        recipient_observation=observation,
        packet=packet,
        phase=flight.MATCHED_USE_PHASE,
    )
    adapter = flight.FreshSemanticPhaseAdapter(
        split_id="fresh-discovery-104-v1",
        samples=(sample,),
        phase=flight.MATCHED_USE_PHASE,
        use_material={sample.sample_id: material},
    )

    contract = adapter.build_task_contract(sample, object())
    messages = adapter.assemble_prompt(sample, None)
    receipt = adapter.render_use_request(
        sample.sample_id,
        {"packet_id": "speech/fresh-000", "sha256": "d" * 64},
        prompt_order="speech-query-prefix-v2",
    )

    assert contract == packet.text
    assert messages == (
        {"role": "system", "content": packet.text},
        {"role": "user", "content": []},
    )
    assert receipt.rails_messages[0] == {"role": "system", "content": packet.text}
    assert observation.transcript not in receipt.rails_messages[0]["content"]
    assert observation.transcript in receipt.contact_instruction
    assert observation.retrieval_query in receipt.contact_instruction
    assert receipt.response_format is packet.response_format
    assert receipt.rails_messages_sha256 == _canonical_hash(receipt.rails_messages)
    assert receipt.rails_envelope_sha256 == _canonical_hash(receipt.rails_envelope)
    assert receipt.rails_messages_ascii_bytes == len(
        json.dumps(
            receipt.rails_messages,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    )
    assert receipt.prompt_order == "speech-query-prefix-v2"
    assert receipt.transport_messages[0] == {
        "role": "system",
        "content": packet.text,
    }
    transport_parts = receipt.transport_messages[1]["content"]
    assert transport_parts[0]["type"] == "input_speech_features"
    assert transport_parts[-1] == {
        "type": "text",
        "text": (
            f"[agent control {flight.MATCHED_CONTACT_ID}] {receipt.contact_instruction}"
        ),
    }
    assert observation.transcript in transport_parts[-1]["text"]
    assert observation.retrieval_query in transport_parts[-1]["text"]
    assert receipt.transport_messages_sha256 == _canonical_hash(
        receipt.transport_messages
    )
    assert not hasattr(receipt, "request_ascii_bytes")
    for forbidden in ("gold", "score", "sample id", "construction example"):
        assert forbidden not in receipt.rails_messages[0]["content"].casefold()


def test_transport_messages_apply_one_media_marker_and_bind_observation_bytes() -> None:
    sample = _sample(0)
    packet = _packet("candidate")

    def render(observation: flight.ObservationState) -> flight.RenderedUseRequest:
        material = flight.UseMaterial(
            recipient_sample_id=sample.sample_id,
            donor_sample_id=sample.sample_id,
            tier="implicit",
            recipient_observation=observation,
            packet=packet,
            phase=flight.MATCHED_USE_PHASE,
        )
        adapter = flight.FreshSemanticPhaseAdapter(
            split_id="fresh-discovery-104-v1",
            samples=(sample,),
            phase=flight.MATCHED_USE_PHASE,
            use_material={sample.sample_id: material},
        )
        return adapter.render_use_request(
            sample.sample_id,
            {"packet_id": "speech/fresh-000", "sha256": "d" * 64},
            prompt_order="speech-query-prefix-v2",
        )

    first = render(_observation(0))
    second = render(_observation(1))

    def apply_template(messages: tuple[object, ...]) -> str:
        rendered: list[str] = []
        for message in messages:
            content = message["content"]
            if isinstance(content, str):
                rendered.append(content)
                continue
            for part in content:
                if part["type"] == "input_speech_features":
                    rendered.append("<MEDIA>")
                else:
                    rendered.append(part["text"])
        return "\n".join(rendered)

    prompt = apply_template(first.transport_messages)
    assert prompt.count("<MEDIA>") == 1
    assert first.contact_instruction in prompt
    assert first.transport_messages_sha256 != second.transport_messages_sha256


def test_transport_render_refuses_unsupported_prompt_order() -> None:
    sample = _sample(0)
    material = flight.UseMaterial(
        recipient_sample_id=sample.sample_id,
        donor_sample_id=sample.sample_id,
        tier="direct",
        recipient_observation=_observation(),
        packet=_packet("candidate"),
        phase=flight.MATCHED_USE_PHASE,
    )
    adapter = flight.FreshSemanticPhaseAdapter(
        split_id="fresh",
        samples=(sample,),
        phase=flight.MATCHED_USE_PHASE,
        use_material={sample.sample_id: material},
    )

    with pytest.raises(flight.SemanticAgentLoopError, match="prompt order"):
        adapter.render_use_request(
            sample.sample_id,
            {"packet_id": "speech/fresh-000", "sha256": "d" * 64},
            prompt_order="not-supported",
        )


def test_controllers_are_one_contact_with_dynamic_per_sample_response_formats() -> None:
    obs_controller = flight.SingleContactController(
        phase=flight.OBSERVATION_PHASE,
        registered_tool_names=REGISTERED,
    )
    context = _context()
    obs_contact = obs_controller.initial_contact(context)
    assert (
        obs_contact.decoding_params["response_format"]
        == flight.observation_response_format()
    )
    obs_response = '{"transcript":"turn it down","retrieval_query":"reduce the current audio level"}'
    advance = obs_controller.advance(context, obs_contact, obs_response)
    assert advance.next_contact is None
    assert obs_controller.observation is not None

    first = flight.UseMaterial(
        recipient_sample_id="fresh:000",
        donor_sample_id="fresh:000",
        tier="direct",
        recipient_observation=_observation(),
        packet=_packet("first"),
        phase=flight.MATCHED_USE_PHASE,
    )
    second = flight.UseMaterial(
        recipient_sample_id="fresh:001",
        donor_sample_id="fresh:001",
        tier="direct",
        recipient_observation=_observation(1),
        packet=_packet("second"),
        phase=flight.MATCHED_USE_PHASE,
    )
    first_contact = flight.SingleContactController(
        phase=flight.MATCHED_USE_PHASE, use_material=first
    ).initial_contact(_context("fresh:000"))
    second_contact = flight.SingleContactController(
        phase=flight.MATCHED_USE_PHASE, use_material=second
    ).initial_contact(_context("fresh:001"))
    assert (
        first_contact.decoding_params["response_format"] is first.packet.response_format
    )
    assert (
        second_contact.decoding_params["response_format"]
        is second.packet.response_format
    )
    assert (
        first_contact.decoding_params["response_format"]
        != second_contact.decoding_params["response_format"]
    )


def test_run_phase_hard_binds_fresh_104_openjiuwen_geometry_and_one_contact() -> None:
    samples = tuple(_sample(index) for index in range(104))
    observations = {
        sample.sample_id: _observation(index) for index, sample in enumerate(samples)
    }
    packets = {
        sample.sample_id: _packet(f"candidate{index}")
        for index, sample in enumerate(samples)
    }
    tiers = {sample.sample_id: "direct" for sample in samples}
    matched, _shuffled = flight.build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=packets,
        sample_tiers=tiers,
        seed="fresh-flight",
    )
    adapter = flight.FreshSemanticPhaseAdapter(
        split_id="fresh-discovery-sealed-v1",
        samples=samples,
        phase=flight.MATCHED_USE_PHASE,
        use_material=matched,
    )
    bindings = {
        sample.sample_id: {
            "packet_id": f"speech/{index:03d}",
            "sha256": f"{index + 500:064x}",
        }
        for index, sample in enumerate(samples)
    }
    summary = SimpleNamespace(
        agent_executor_id=flight.AGENT_EXECUTOR_ID,
        results=tuple(
            SimpleNamespace(sample_id=sample.sample_id, contacts=(object(),))
            for sample in samples
        ),
    )

    def fake_runner(**kwargs: object) -> object:
        assert kwargs["agent_executor_id"] == "openjiuwen-workflow-v1"
        assert kwargs["slot_count"] == 2
        assert kwargs["queue_depth"] == 4
        assert kwargs["max_contacts"] == 1
        registry = kwargs["controller_registry"]
        factory = registry.resolve(kwargs["controller_policy_id"])
        first = factory("fresh:000").initial_contact(_context("fresh:000"))
        second = factory("fresh:001").initial_contact(_context("fresh:001"))
        assert (
            first.decoding_params["response_format"]
            is packets["fresh:000"].response_format
        )
        assert (
            second.decoding_params["response_format"]
            is packets["fresh:001"].response_format
        )
        return summary

    returned = flight.run_phase(
        phase=flight.MATCHED_USE_PHASE,
        data_root=SimpleNamespace(),
        plan=SimpleNamespace(),
        adapter=adapter,
        core_client=SimpleNamespace(),
        split_id="fresh-discovery-sealed-v1",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=bindings,
        trace_sink=SimpleNamespace(),
        decoding_params={"temperature": 0},
        agent_runner=fake_runner,
    )
    assert returned is summary

    with pytest.raises(flight.SemanticAgentLoopError, match="exactly 104"):
        flight.run_phase(
            phase=flight.MATCHED_USE_PHASE,
            data_root=SimpleNamespace(),
            plan=SimpleNamespace(),
            adapter=adapter,
            core_client=SimpleNamespace(),
            split_id="fresh-discovery-sealed-v1",
            knowledge_snapshot=SimpleNamespace(),
            speech_packet_bindings=dict(tuple(bindings.items())[:103]),
            trace_sink=SimpleNamespace(),
            decoding_params={},
            agent_runner=fake_runner,
        )
