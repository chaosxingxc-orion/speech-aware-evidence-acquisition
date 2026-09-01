"""Flight-boundary tests for the self-transcript cascade."""

from __future__ import annotations

from types import SimpleNamespace

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
