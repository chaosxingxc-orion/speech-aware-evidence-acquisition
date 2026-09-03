"""Model-free tests for the bounded SELECT/FILL AgentLoop phase boundary."""

from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
    JointDraftCall,
    SelectOccurrence,
    build_joint_draft_stage_envelope,
    build_select_stage_envelope,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_select_fill_agentloop as loop,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext


NAMES = ("setTimer", "sendMessage", "getWeather")
HASHES = {character: character * 64 for character in "123456789abcdef"}


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("ascii")).hexdigest()


def _response_format(*, selection: bool = False) -> dict[str, object]:
    item = {
        "type": "object",
        "properties": {"name": {"enum": list(NAMES)}},
        "required": ["name"],
        "additionalProperties": False,
    }
    if not selection:
        item["properties"]["arguments"] = {"type": "object"}
        item["required"] = ["name", "arguments"]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "test_phase",
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": 1,
                "maxItems": 7,
                "items": item,
            },
        },
    }


def _predecessor(phase: str):
    common = {
        "sample_identity_sha256": hashlib.sha256(b"fresh:000").hexdigest(),
        "split_identity_sha256": HASHES["1"],
        "speech_packet_sha256": HASHES["2"],
        "source_query_state_sha256": HASHES["3"],
        "source_response_sha256": HASHES["4"],
        "observation_state_sha256": _hash(
            {"retrieval_query": "set a short timer", "transcript": "set a timer"}
        ),
        "observation_source_response_sha256": HASHES["5"],
        "source_request_body_sha256": HASHES["6"],
        "candidate_tool_names": NAMES,
        "ground_sha256": HASHES["7"],
        "response_schema_sha256": HASHES["8"],
        "predecessor_envelope_sha256": None,
    }
    if phase == loop.FILL_PHASE:
        return build_select_stage_envelope(
            **common,
            occurrences=(
                SelectOccurrence("occurrence-000", "setTimer"),
                SelectOccurrence("occurrence-001", "setTimer"),
            ),
        )
    return build_joint_draft_stage_envelope(
        **common,
        calls=(JointDraftCall.from_arguments("setTimer", {"seconds": 5}),),
    )


def _material(phase: str = loop.SELECT_PHASE) -> loop.PhaseMaterial:
    observation = _canonical(
        {"retrieval_query": "set a short timer", "transcript": "set a timer"}
    )
    selection = phase == loop.SELECT_PHASE
    response_format = _response_format(selection=selection)
    ground = f"ASCII {phase} ground\n"
    predecessor = (
        _predecessor(phase) if phase in {loop.REVISE_PHASE, loop.FILL_PHASE} else None
    )
    return loop.PhaseMaterial(
        sample_id="fresh:000",
        phase=phase,
        candidate_tool_names=NAMES,
        ground_text=ground,
        ground_sha256=hashlib.sha256(ground.encode("ascii")).hexdigest(),
        response_format=response_format,
        response_format_sha256=_hash(response_format),
        observation_state_json=observation,
        observation_state_sha256=_hash(json.loads(observation)),
        observation_source_response_sha256=HASHES["5"],
        predecessor=predecessor,
    )


def _sample(index: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        sample_id=f"fresh:{index:03d}",
        audio_ref=AudioRef(path=f"audio/{index:03d}.wav", sha256=f"{index + 20:064x}"),
        audio_seconds=1.0,
    )


def _context(sample_id: str = "fresh:000") -> AgentRuntimeContext:
    query = QueryState(
        query_id=f"query:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=HASHES["2"],
        use_split_identity_hash=HASHES["1"],
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=HASHES["3"],
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=query,
        task_contract="phase ground",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def test_select_parser_preserves_order_and_repeated_occurrences() -> None:
    parsed = loop.parse_select_response(
        '[{"name":"setTimer"},{"name":"setTimer"},{"name":"sendMessage"}]',
        candidate_tool_names=NAMES,
    )

    assert parsed == ("setTimer", "setTimer", "sendMessage")


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ('```json\n[{"name":"setTimer"}]\n```', "JSON"),
        ('[{"name":"setTimer","name":"setTimer"}]', "duplicate"),
        ('[{"name":"setTim\u00e9r"}]', "ASCII"),
        ('[{"name":"setTimer","score":NaN}]', "JSON"),
        ('[{"name":"setTimer","arguments":{}}]', "exactly"),
        ("[]", "between 1 and 7"),
        (_canonical([{"name": "setTimer"}] * 8), "between 1 and 7"),
        ('[{"name":"unknownTool"}]', "candidate"),
    ],
)
def test_select_parser_rejects_every_nonexact_surface(raw: str, message: str) -> None:
    with pytest.raises(loop.SelectFillAgentLoopError, match=message):
        loop.parse_select_response(raw, candidate_tool_names=NAMES)


def test_call_parser_preserves_canonical_arguments_and_can_lock_names() -> None:
    parsed = loop.parse_call_array_response(
        '[{"name":"setTimer","arguments":{"seconds":5,"enabled":true}},'
        '{"name":"sendMessage","arguments":{"to":"A","tags":["b","a"]}}]',
        allowed_tool_names=NAMES,
        expected_tool_names=("setTimer", "sendMessage"),
    )

    assert tuple(item.name for item in parsed) == ("setTimer", "sendMessage")
    assert parsed[0].arguments == {"enabled": True, "seconds": 5}
    assert parsed[1].arguments_json == '{"tags":["b","a"],"to":"A"}'


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ('```json\n[{"name":"setTimer","arguments":{}}]\n```', "JSON"),
        ('[{"name":"setTimer","arguments":{"x":1,"x":2}}]', "duplicate"),
        ('[{"name":"setTimer","arguments":{"city":"Montr\u00e9al"}}]', "ASCII"),
        ('[{"name":"setTimer","arguments":{"x":Infinity}}]', "JSON"),
        ('[{"name":"setTimer"}]', "exactly name and arguments"),
        ('[{"name":"setTimer","arguments":{},"extra":1}]', "exactly"),
        ('[{"name":"setTimer","arguments":[]}]', "arguments"),
        ("[]", "between 1 and 7"),
        (_canonical([{"name": "setTimer", "arguments": {}}] * 8), "between 1 and 7"),
        ('[{"name":"unknownTool","arguments":{}}]', "allowed"),
    ],
)
def test_call_parser_rejects_every_nonexact_surface(raw: str, message: str) -> None:
    with pytest.raises(loop.SelectFillAgentLoopError, match=message):
        loop.parse_call_array_response(raw, allowed_tool_names=NAMES)


def test_call_parser_rejects_fill_name_or_multiplicity_drift() -> None:
    with pytest.raises(loop.SelectFillAgentLoopError, match="locked"):
        loop.parse_call_array_response(
            '[{"name":"setTimer","arguments":{}}]',
            allowed_tool_names=NAMES,
            expected_tool_names=("setTimer", "setTimer"),
        )


def test_phase_material_requires_exact_hashes_and_verified_predecessor() -> None:
    for phase in loop.PHASES:
        material = _material(phase)
        assert material.phase == phase

    values = _material(loop.FILL_PHASE).__dict__.copy()
    values["observation_state_sha256"] = HASHES["f"]
    with pytest.raises(loop.SelectFillAgentLoopError, match="observation"):
        loop.PhaseMaterial(**values)

    values = _material(loop.REVISE_PHASE).__dict__.copy()
    values["predecessor"] = _predecessor(loop.FILL_PHASE)
    with pytest.raises(loop.SelectFillAgentLoopError, match="predecessor"):
        loop.PhaseMaterial(**values)

    assert not hasattr(_material(loop.SELECT_PHASE), "source_request_body_sha256")


def test_controller_revalidates_exact_argument_schema_after_generation() -> None:
    material = _material(loop.FILL_PHASE)
    strict_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "typed_fill",
            "strict": True,
            "schema": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "prefixItems": [
                    {
                        "oneOf": [
                            {
                                "type": "object",
                                "properties": {
                                    "name": {"const": "setTimer"},
                                    "arguments": {
                                        "type": "object",
                                        "properties": {
                                            "seconds": {
                                                "type": "integer",
                                                "minimum": 1,
                                                "maximum": 60,
                                            }
                                        },
                                        "required": ["seconds"],
                                        "additionalProperties": False,
                                    },
                                },
                                "required": ["name", "arguments"],
                                "additionalProperties": False,
                            }
                        ]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "name": {"enum": ["setTimer"]},
                            "arguments": {
                                "type": "object",
                                "properties": {
                                    "enabled": {"type": ["boolean", "null"]}
                                },
                                "required": ["enabled"],
                                "additionalProperties": False,
                            },
                        },
                        "required": ["name", "arguments"],
                        "additionalProperties": False,
                    },
                ],
            },
        },
    }
    values = material.__dict__.copy()
    values["response_format"] = strict_format
    values["response_format_sha256"] = _hash(strict_format)
    controller = loop.SingleContactPhaseController(
        material=loop.PhaseMaterial(**values)
    )
    contact = controller.initial_contact(_context())

    with pytest.raises(loop.SelectFillAgentLoopError, match="response schema"):
        controller.advance(
            _context(),
            contact,
            '[{"name":"setTimer","arguments":{"seconds":"five"}},'
            '{"name":"setTimer","arguments":{"enabled":true}}]',
        )
    with pytest.raises(loop.SelectFillAgentLoopError, match="response schema"):
        controller.advance(
            _context(),
            contact,
            '[{"name":"setTimer","arguments":{"seconds":61}},'
            '{"name":"setTimer","arguments":{"enabled":true}}]',
        )

    accepted = controller.advance(
        _context(),
        contact,
        '[{"name":"setTimer","arguments":{"seconds":5}},'
        '{"name":"setTimer","arguments":{"enabled":null}}]',
    )
    assert accepted.final_response_contact_id == loop.FILL_CONTACT_ID


def test_exact_request_renderer_is_pure_hash_bound_and_has_no_raw_history() -> None:
    material = _material(loop.FILL_PHASE)
    binding = {"packet_id": "speech/fresh-000", "sha256": HASHES["2"]}

    first = loop.render_phase_request(
        material,
        binding,
        prompt_order="speech-query-prefix-v2",
        decoding_params={"temperature": 0, "top_p": 1},
    )
    second = loop.render_phase_request(
        material,
        binding,
        prompt_order="speech-query-prefix-v2",
        decoding_params={"temperature": 0, "top_p": 1},
    )

    assert first == second
    assert (
        first.request_body_sha256
        == hashlib.sha256(_canonical(first.request_body).encode("ascii")).hexdigest()
    )
    assert first.transport_messages[0] == {
        "role": "system",
        "content": material.ground_text,
    }
    assert (
        sum(
            part.get("type") == "input_speech_features"
            for part in first.transport_messages[1]["content"]
        )
        == 1
    )
    assert len(first.history) == 1
    assert all(item["role"] != "agent_state" for item in first.history)
    assert material.observation_state_json in first.contact_instruction
    assert material.predecessor.payload_sha256 in first.contact_instruction
    assert "raw_response" not in _canonical(first.request_body).casefold()


def test_request_renderer_rejects_speech_lineage_or_decode_schema_drift() -> None:
    material = _material(loop.FILL_PHASE)
    with pytest.raises(loop.SelectFillAgentLoopError, match="speech"):
        loop.render_phase_request(
            material,
            {"packet_id": "speech/fresh-000", "sha256": HASHES["3"]},
            prompt_order="speech-query-prefix-v2",
        )
    with pytest.raises(loop.SelectFillAgentLoopError, match="response_format"):
        loop.render_phase_request(
            material,
            {"packet_id": "speech/fresh-000", "sha256": HASHES["2"]},
            prompt_order="speech-query-prefix-v2",
            decoding_params={"response_format": {}},
        )


def test_generic_adapter_and_controller_cover_all_four_fresh_phases() -> None:
    sample = _sample()
    responses = {
        loop.JOINT_PHASE: '[{"name":"setTimer","arguments":{"seconds":5}}]',
        loop.SELECT_PHASE: '[{"name":"setTimer"},{"name":"setTimer"}]',
        loop.REVISE_PHASE: '[{"name":"setTimer","arguments":{"seconds":6}}]',
        loop.FILL_PHASE: (
            '[{"name":"setTimer","arguments":{"seconds":5}},'
            '{"name":"setTimer","arguments":{"seconds":6}}]'
        ),
    }
    for phase in loop.PHASES:
        material = _material(phase)
        adapter = loop.FreshSelectFillPhaseAdapter(
            split_id="fresh-split",
            samples=(sample,),
            phase=phase,
            material={sample.sample_id: material},
        )
        assert adapter.build_task_contract(sample, object()) == material.ground_text
        controller = loop.SingleContactPhaseController(material=material)
        contact = controller.initial_contact(_context())
        assert contact.decoding_params["response_format"] is material.response_format
        advance = controller.advance(_context(), contact, responses[phase])
        assert advance.next_contact is None
        assert advance.final_response_contact_id == contact.contact_id
        assert controller.parsed_response is not None


def test_controller_rejects_nonfresh_context_instead_of_using_history() -> None:
    context = _context()
    dirty = AgentRuntimeContext(
        **{
            **context.__dict__,
            "prior_response_sha256s": (HASHES["1"],),
        }
    )
    with pytest.raises(loop.SelectFillAgentLoopError, match="fresh"):
        loop.SingleContactPhaseController(
            material=_material(loop.SELECT_PHASE)
        ).initial_contact(dirty)


def test_run_phase_binds_104_rows_one_contact_openjiuwen_slot2_queue4() -> None:
    samples = tuple(_sample(index) for index in range(104))
    materials = {
        sample.sample_id: loop.PhaseMaterial(
            **{
                **_material(loop.SELECT_PHASE).__dict__,
                "sample_id": sample.sample_id,
            }
        )
        for sample in samples
    }
    adapter = loop.FreshSelectFillPhaseAdapter(
        split_id="fresh-split",
        samples=samples,
        phase=loop.SELECT_PHASE,
        material=materials,
    )
    bindings = {
        sample.sample_id: {
            "packet_id": f"speech/{index:03d}",
            "sha256": f"{index + 500:064x}",
        }
        for index, sample in enumerate(samples)
    }
    summary = SimpleNamespace(
        agent_executor_id=loop.AGENT_EXECUTOR_ID,
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
        controller = registry.resolve(kwargs["controller_policy_id"])("fresh:000")
        assert isinstance(controller, loop.SingleContactPhaseController)
        return summary

    returned = loop.run_phase(
        phase=loop.SELECT_PHASE,
        data_root=SimpleNamespace(),
        plan=SimpleNamespace(),
        adapter=adapter,
        core_client=SimpleNamespace(),
        split_id="fresh-split",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=bindings,
        trace_sink=SimpleNamespace(),
        decoding_params={"temperature": 0},
        agent_runner=fake_runner,
    )

    assert returned is summary


def test_run_phase_accepts_explicitly_bound_128_row_factorial_cell() -> None:
    samples = tuple(_sample(index) for index in range(128))
    materials = {
        sample.sample_id: loop.PhaseMaterial(
            **{
                **_material(loop.SELECT_PHASE).__dict__,
                "sample_id": sample.sample_id,
            }
        )
        for sample in samples
    }
    adapter = loop.FreshSelectFillPhaseAdapter(
        split_id="fresh-factorial-split",
        samples=samples,
        phase=loop.SELECT_PHASE,
        material=materials,
    )
    bindings = {
        sample.sample_id: {
            "packet_id": f"speech/{index:03d}",
            "sha256": f"{index + 800:064x}",
        }
        for index, sample in enumerate(samples)
    }
    summary = SimpleNamespace(
        agent_executor_id=loop.AGENT_EXECUTOR_ID,
        results=tuple(
            SimpleNamespace(sample_id=sample.sample_id, contacts=(object(),))
            for sample in samples
        ),
    )

    returned = loop.run_phase(
        phase=loop.SELECT_PHASE,
        data_root=SimpleNamespace(),
        plan=SimpleNamespace(),
        adapter=adapter,
        core_client=SimpleNamespace(),
        split_id="fresh-factorial-split",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings=bindings,
        trace_sink=SimpleNamespace(),
        decoding_params={"temperature": 0},
        expected_row_count=128,
        agent_runner=lambda **_kwargs: summary,
    )

    assert returned is summary
