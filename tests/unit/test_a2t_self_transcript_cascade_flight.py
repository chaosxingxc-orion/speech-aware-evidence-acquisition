"""Flight-boundary tests for the self-transcript cascade."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_self_transcript_cascade as cascade,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_self_transcript_cascade_flight as flight,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext


def _query_state() -> QueryState:
    return QueryState(
        query_id="query:tier1:000001",
        query_sample_id="tier1:000001",
        speech_packet_id="packet:tier1:000001",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
    ).validate()


def _context() -> AgentRuntimeContext:
    return AgentRuntimeContext(
        sample_id="tier1:000001",
        knowledge_snapshot_sha256="c" * 64,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=_query_state(),
        task_contract="Choose a tool from the complete frozen registry.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def _receipt() -> cascade.LivenessReceipt:
    return cascade.LivenessReceipt(
        passed=True,
        row_count=104,
        report_sha256="d" * 64,
        gates={
            "response_count": True,
            "valid_transcript_count": True,
            "positive_route_count": True,
            "transcript_diversity": True,
            "mode_count": True,
            "prohibited_structure": True,
            "same_tier_derangement": True,
        },
    )


def test_observation_contact_is_asr_only_and_task_blind() -> None:
    controller = flight.SingleContactController(phase=flight.OBSERVATION_PHASE)
    contact = controller.initial_contact(_context())
    assert contact.contact_id == flight.OBSERVATION_CONTACT_ID
    assert contact.instruction == cascade.SELF_TRANSCRIPT_INSTRUCTION
    assert contact.decoding_params == {"max_tokens": 192, "temperature": 0}
    serialized = repr(contact)
    for forbidden in (
        "setLightBrightness",
        "tool_schemas",
        "reference transcript",
        "arguments",
        "gold",
        "score",
    ):
        assert forbidden not in serialized


def test_use_contact_requires_a_passing_bound_liveness_receipt() -> None:
    controller = flight.SingleContactController(
        phase=flight.MATCHED_USE_PHASE,
        liveness_receipt=_receipt(),
    )
    contact = controller.initial_contact(_context())
    assert contact.contact_id == flight.MATCHED_CONTACT_ID
    assert "original speech" in contact.instruction
    assert "self-transcript" in contact.instruction
    assert "supplied evidence" in contact.instruction

    failed = SimpleNamespace(passed=False, row_count=104, report_sha256="e" * 64)
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="liveness"):
        flight.SingleContactController(
            phase=flight.MATCHED_USE_PHASE,
            liveness_receipt=failed,
        )


def test_single_contact_controller_stops_with_the_current_response() -> None:
    controller = flight.SingleContactController(phase=flight.OBSERVATION_PHASE)
    context = _context()
    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, "turn on the light")
    assert advance.transition.action_kind == "stop"
    assert advance.next_query_state is None
    assert advance.next_contact is None
    assert advance.final_response_contact_id == flight.OBSERVATION_CONTACT_ID


def test_matched_and_shuffled_prompt_blocks_keep_the_recipient_state() -> None:
    matched = flight.render_use_prompt_block(
        task_contract="Complete registry contract.",
        recipient_transcript="turn on the kitchen light",
        evidence_contents=("matched evidence one", "matched evidence two"),
        phase=flight.MATCHED_USE_PHASE,
    )
    shuffled = flight.render_use_prompt_block(
        task_contract="Complete registry contract.",
        recipient_transcript="turn on the kitchen light",
        evidence_contents=("donor-retrieved evidence",),
        phase=flight.SHUFFLED_USE_PHASE,
    )
    assert "turn on the kitchen light" in matched
    assert "turn on the kitchen light" in shuffled
    assert "matched evidence one" in matched
    assert "donor-retrieved evidence" in shuffled
    assert "donor transcript words" not in shuffled
    assert matched.count("Complete registry contract.") == 1


def test_use_material_changes_only_the_shuffled_retrieval_query() -> None:
    from test_training_free_a2t_self_transcript_cascade import _snapshot

    transcripts = {
        "tier0:000001": cascade.validate_self_transcript(
            "dim the kitchen lights to eighty percent"
        ),
        "tier0:000002": cascade.validate_self_transcript(
            "get the weather forecast in Boston tomorrow"
        ),
        "tier1:000003": cascade.validate_self_transcript(
            "set an alarm for seven in the morning"
        ),
        "tier1:000004": cascade.validate_self_transcript(
            "dim the kitchen lights to eighty percent please"
        ),
    }
    tiers = {sample_id: sample_id.split(":", 1)[0] for sample_id in transcripts}
    snapshot = _snapshot()
    matched = flight.build_use_material(
        transcripts=transcripts,
        sample_tiers=tiers,
        snapshot=snapshot,
        phase=flight.MATCHED_USE_PHASE,
    )
    shuffled = flight.build_use_material(
        transcripts=transcripts,
        sample_tiers=tiers,
        snapshot=snapshot,
        phase=flight.SHUFFLED_USE_PHASE,
    )
    assert set(matched) == set(shuffled) == set(transcripts)
    for sample_id in matched:
        assert matched[sample_id].recipient_transcript == transcripts[sample_id].text
        assert shuffled[sample_id].recipient_transcript == transcripts[sample_id].text
        assert matched[sample_id].donor_id is None
        assert shuffled[sample_id].donor_id != sample_id
        assert tiers[shuffled[sample_id].donor_id] == tiers[sample_id]
        assert 1 <= len(matched[sample_id].evidence_contents) <= 6
        assert 1 <= len(shuffled[sample_id].evidence_contents) <= 6


def test_observation_system_contract_cannot_render_task_material() -> None:
    prompt = flight.render_observation_system_contract()
    assert prompt == cascade.SELF_TRANSCRIPT_INSTRUCTION
    assert "Available tools" not in prompt
    assert "arguments" not in prompt
    assert "JSON array" not in prompt


def test_run_phase_requires_openjiuwen_and_exactly_one_contact_per_sample() -> None:
    summary = SimpleNamespace(
        results=tuple(
            SimpleNamespace(sample_id=f"tier1:{index:06d}", contacts=(object(),))
            for index in range(3)
        ),
        agent_executor_id="openjiuwen-workflow-v1",
    )

    def fake_runner(**kwargs: object) -> object:
        assert kwargs["agent_executor_id"] == "openjiuwen-workflow-v1"
        assert kwargs["max_contacts"] == 1
        return summary

    returned = flight.run_phase(
        phase=flight.OBSERVATION_PHASE,
        data_root=SimpleNamespace(),
        plan=SimpleNamespace(),
        adapter=SimpleNamespace(),
        core_client=SimpleNamespace(),
        split_id="A2T-SELF-TRANSCRIPT-104",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings={
            f"tier1:{index:06d}": {"packet": index} for index in range(3)
        },
        trace_sink=SimpleNamespace(),
        slot_count=2,
        queue_depth=2,
        decoding_params={},
        agent_runner=fake_runner,
    )
    assert returned is summary


def _receipt_items() -> tuple[dict[str, str], ...]:
    return (
        {
            "sample_id": "tier1:000001",
            "media_relpath": "audio/one.wav",
            "audio_sha256": "1" * 64,
        },
        {
            "sample_id": "tier1:000002",
            "media_relpath": "audio/two.wav",
            "audio_sha256": "2" * 64,
        },
    )


def _samples() -> tuple[SimpleNamespace, ...]:
    return (
        SimpleNamespace(
            sample_id="tier1:000002",
            media_relpath="audio/two.wav",
            audio_ref=SimpleNamespace(sha256="2" * 64),
        ),
        SimpleNamespace(
            sample_id="tier1:000001",
            media_relpath="audio/one.wav",
            audio_ref=SimpleNamespace(sha256="1" * 64),
        ),
    )


def _material(sample_id: str) -> flight.UseMaterial:
    return flight.UseMaterial(
        sample_id=sample_id,
        recipient_transcript="turn on the kitchen light",
        route=cascade.EvidenceRoute(
            available=True,
            facet_ids=("facet-1",),
            value_ids=("value-1",),
            task_targets=("setLightBrightness",),
            scores=(2.0,),
            positive_facet_count=1,
            top1_margin=1.0,
            prompt_block="setLightBrightness controls a light",
        ),
        evidence_contents=("setLightBrightness controls a light",),
        donor_id=None,
        retrieval_query_sha256="b" * 64,
    )


def test_receipt_filtered_adapters_render_observation_and_use_prompts() -> None:
    with (
        patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None),
        patch.object(
            flight.Audio2ToolAdapter,
            "load_split",
            return_value=_samples(),
        ),
        patch.object(
            flight.Audio2ToolAdapter,
            "build_task_contract",
            return_value="Complete registry contract.",
        ),
    ):
        observation = flight.A2TSelfTranscriptAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=flight.OBSERVATION_PHASE,
        )
        observed = observation.load_split(flight.SPLIT_ID)
        assert [sample.sample_id for sample in observed] == [
            "tier1:000001",
            "tier1:000002",
        ]
        assert observation.load_split(flight.SPLIT_ID) is observed
        contract = observation.build_task_contract(observed[0], object())
        prompt = observation.assemble_prompt(observed[0], None)
        assert contract == cascade.SELF_TRANSCRIPT_INSTRUCTION
        assert prompt[0] == {"role": "system", "content": contract}
        assert prompt[1]["content"][0]["media_relpath"] == "audio/one.wav"
        assert observation.score(observed[0], "words") == {
            "scoring_deferred": True
        }

        use = flight.A2TSelfTranscriptAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=flight.MATCHED_USE_PHASE,
            use_material={"tier1:000001": _material("tier1:000001")},
        )
        selected = use.load_split(flight.SPLIT_ID)
        assert [sample.sample_id for sample in selected] == ["tier1:000001"]
        use_contract = use.build_task_contract(selected[0], object())
        assert "Complete registry contract." in use_contract
        assert "turn on the kitchen light" in use_contract
        assert "setLightBrightness controls a light" in use_contract


def test_adapter_and_controller_fail_closed_on_malformed_boundaries() -> None:
    with patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None):
        with pytest.raises(flight.A2TSelfTranscriptFlightError, match="unknown"):
            flight.A2TSelfTranscriptAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=_receipt_items(),
                phase="UNKNOWN",
            )
        with pytest.raises(flight.A2TSelfTranscriptFlightError, match="duplicate"):
            flight.A2TSelfTranscriptAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=(_receipt_items()[0], _receipt_items()[0]),
                phase=flight.OBSERVATION_PHASE,
            )
        with pytest.raises(flight.A2TSelfTranscriptFlightError, match="cannot receive"):
            flight.A2TSelfTranscriptAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=_receipt_items(),
                phase=flight.OBSERVATION_PHASE,
                use_material={"tier1:000001": _material("tier1:000001")},
            )

    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="cannot receive"):
        flight.SingleContactController(
            phase=flight.OBSERVATION_PHASE,
            liveness_receipt=_receipt(),
        )
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="unknown"):
        flight.SingleContactController(phase="UNKNOWN")
    malformed = SimpleNamespace(
        passed=True,
        row_count=104,
        report_sha256="not-a-hash",
    )
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="64-hex"):
        flight.SingleContactController(
            phase=flight.MATCHED_USE_PHASE,
            liveness_receipt=malformed,
        )


def test_prompt_and_single_contact_sequence_reject_unsafe_inputs() -> None:
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="USE phase"):
        flight.render_use_prompt_block(
            task_contract="contract",
            recipient_transcript="spoken words",
            evidence_contents=("evidence",),
            phase=flight.OBSERVATION_PHASE,
        )
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="task contract"):
        flight.render_use_prompt_block(
            task_contract=" ",
            recipient_transcript="spoken words",
            evidence_contents=("evidence",),
            phase=flight.MATCHED_USE_PHASE,
        )
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="evidence"):
        flight.render_use_prompt_block(
            task_contract="contract",
            recipient_transcript="spoken words",
            evidence_contents=(),
            phase=flight.MATCHED_USE_PHASE,
        )

    controller = flight.SingleContactController(phase=flight.OBSERVATION_PHASE)
    context = _context()
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="contact"):
        controller.advance(context, object(), "words")
    contact = controller.initial_contact(context)
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match="string"):
        controller.advance(context, contact, object())


@pytest.mark.parametrize(
    ("summary", "pattern"),
    (
        (SimpleNamespace(results=(), agent_executor_id="wrong"), "openjiuwen"),
        (SimpleNamespace(results=[], agent_executor_id=flight.AGENT_EXECUTOR_ID), "tuple"),
        (
            SimpleNamespace(
                results=(SimpleNamespace(sample_id="", contacts=(object(),)),),
                agent_executor_id=flight.AGENT_EXECUTOR_ID,
            ),
            "sample_id",
        ),
        (
            SimpleNamespace(
                results=(
                    SimpleNamespace(sample_id="tier1:000001", contacts=()),
                ),
                agent_executor_id=flight.AGENT_EXECUTOR_ID,
            ),
            "exactly one",
        ),
    ),
)
def test_run_phase_rejects_unbound_agent_results(
    summary: SimpleNamespace, pattern: str
) -> None:
    with pytest.raises(flight.A2TSelfTranscriptFlightError, match=pattern):
        flight.run_phase(
            phase=flight.OBSERVATION_PHASE,
            data_root=SimpleNamespace(),
            plan=SimpleNamespace(),
            adapter=SimpleNamespace(),
            core_client=SimpleNamespace(),
            split_id=flight.SPLIT_ID,
            knowledge_snapshot=SimpleNamespace(),
            speech_packet_bindings={"tier1:000001": {}},
            trace_sink=SimpleNamespace(),
            slot_count=2,
            queue_depth=2,
            decoding_params={},
            agent_runner=lambda **_kwargs: summary,
        )
