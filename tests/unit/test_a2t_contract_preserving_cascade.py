"""Contract, canary, and phase gates for the Audio2Tool cascade v2."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from speech_aware_evidence_acquisition.analysis import (
    a2t_contract_preserving_cascade as cascade,
)
from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_self_transcript_cascade as selftx,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    AUDIO2TOOL_OUTPUT_INSTRUCTION,
    _INSTRUCTION_TEMPLATE,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_contract_preserving_cascade_flight as flight,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext


def _valid(name: str = "setLighting") -> str:
    return json.dumps([{"name": name, "arguments": {}}], separators=(",", ":"))


def _runtime_context(*, loop_step: int = 0) -> AgentRuntimeContext:
    state = QueryState(
        query_id="query:tier1:000001",
        query_sample_id="tier1:000001",
        speech_packet_id="packet:tier1:000001",
        speech_packet_sha256="a" * 64,
        use_split_identity_hash="b" * 64,
        loop_step=loop_step,
    ).validate()
    return AgentRuntimeContext(
        sample_id="tier1:000001",
        knowledge_snapshot_sha256="c" * 64,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=state,
        task_contract="Complete registry contract.",
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )


def _liveness_receipt() -> selftx.LivenessReceipt:
    return selftx.LivenessReceipt(
        passed=True,
        row_count=104,
        report_sha256="d" * 64,
        gates={"all": True},
    )


def test_strict_envelope_accepts_only_exact_nonempty_registry_calls() -> None:
    registry = {"setLighting", "getWeather"}
    valid = cascade.validate_output_envelope(_valid(), registry)
    assert valid.valid is True
    assert valid.call_count == 1

    invalid = (
        "```json\n" + _valid() + "\n```",
        "prefix " + _valid(),
        "[]",
        json.dumps([{"name": "unknown", "arguments": {}}]),
        json.dumps([{"name": "setLighting", "arguments": [],}]),
        json.dumps([{"name": "setLighting", "arguments": {}, "extra": 1}]),
        json.dumps([{"name": "setLighting", "arguments": {}}] * 5),
    )
    assert all(
        cascade.validate_output_envelope(text, registry).valid is False
        for text in invalid
    )


def test_canary_selection_is_one_per_tier_and_order_invariant() -> None:
    tiers = {
        f"tier{tier}:{index:06d}": f"tier{tier}"
        for tier in range(1, 9)
        for index in range(1, 14)
    }
    selected = cascade.select_canary_ids(tiers)
    reversed_selected = cascade.select_canary_ids(dict(reversed(tuple(tiers.items()))))

    assert selected == reversed_selected
    assert len(selected) == 8
    assert {tiers[sample_id] for sample_id in selected} == {
        f"tier{tier}" for tier in range(1, 9)
    }


def test_structural_canary_gate_is_label_free_and_conjunctive() -> None:
    ids = tuple(f"tier{tier}:000001" for tier in range(1, 9))
    sample_tiers = {sample_id: sample_id.split(":", 1)[0] for sample_id in ids}
    matched = {sample_id: _valid() for sample_id in ids}
    shuffled = dict(matched)
    report = cascade.evaluate_structural_canary(
        matched=matched,
        shuffled=shuffled,
        sample_tiers=sample_tiers,
        registry_names={"setLighting"},
    )
    assert report.passed is True
    assert report.pooled_valid == 16
    assert report.matched_valid == report.shuffled_valid == 8
    assert report.gold_read is False

    shuffled[ids[0]] = "not json"
    report = cascade.evaluate_structural_canary(
        matched=matched,
        shuffled=shuffled,
        sample_tiers=sample_tiers,
        registry_names={"setLighting"},
    )
    assert report.passed is True
    shuffled[ids[1]] = "not json"
    report = cascade.evaluate_structural_canary(
        matched=matched,
        shuffled=shuffled,
        sample_tiers=sample_tiers,
        registry_names={"setLighting"},
    )
    assert report.passed is False
    assert report.gates["pooled_valid"] is False

    matched[ids[0]] = "not json"
    report = cascade.evaluate_structural_canary(
        matched=matched,
        shuffled=shuffled,
        sample_tiers=sample_tiers,
        registry_names={"setLighting"},
    )
    assert report.passed is False
    assert report.gates["tier_coverage"] is False


def test_v2_promotion_requires_increment_beyond_always_use_and_canary() -> None:
    metrics = SimpleNamespace(
        n_samples=104,
        top5_gold_tool_correct_count=70,
        m0_tool_correct_count=62,
        matched_m0_exact_gain=8,
        matched_m0_tool_gain=7,
        matched_shuffled_exact_gain=6,
        matched_shuffled_tool_gain=5,
        matched_shuffled_ci_low=0.01,
        used=20,
        saved=6,
        harmed=1,
        net_gain=5,
        policy_ci_low=0.01,
        tool_accuracy_net_gain=1,
        slot_micro_f1_net_gain=0.01,
        fold_net_gains=(1, 0, 2, 0, 2),
        always_use_net_gain=3,
        final_contacts=20,
    )
    base = SimpleNamespace(
        metrics=metrics,
        gates={"state_liveness": True},
    )

    gates = cascade.promotion_gates(
        base,
        liveness_passed=True,
        canary_passed=True,
        route_available_count=104,
        resend_absolute_exact_count_difference=2,
    )

    assert all(gates.values())
    metrics.always_use_net_gain = 4
    gates = cascade.promotion_gates(
        base,
        liveness_passed=True,
        canary_passed=True,
        route_available_count=104,
        resend_absolute_exact_count_difference=2,
    )
    assert gates["policy_gain_exceeds_always_use_by_two"] is False
    assert cascade.promotion_gates(
        base,
        liveness_passed=True,
        canary_passed=False,
        route_available_count=104,
        resend_absolute_exact_count_difference=2,
    )["structural_canary"] is False


def test_use_system_contract_preserves_the_direct_final_bytes() -> None:
    registry = '[{"tool_name":"setLighting"}]'
    rendered = flight.render_use_system_contract(
        tool_schemas=registry,
        recipient_transcript="turn on the kitchen light",
        evidence_contents=('{"name":"setLighting","arguments":{}}',),
        phase=flight.MATCHED_USE_PHASE,
    )

    assert rendered.endswith(AUDIO2TOOL_OUTPUT_INSTRUCTION)
    assert rendered.count(AUDIO2TOOL_OUTPUT_INSTRUCTION) == 1
    assert rendered.index("English self-transcript Agent state") < rendered.index(
        AUDIO2TOOL_OUTPUT_INSTRUCTION
    )
    assert rendered.index("Supplied matched evidence") < rendered.index(
        AUDIO2TOOL_OUTPUT_INSTRUCTION
    )


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
    return tuple(
        SimpleNamespace(
            sample_id=item["sample_id"],
            media_relpath=item["media_relpath"],
            audio_ref=SimpleNamespace(sha256=item["audio_sha256"]),
        )
        for item in reversed(_receipt_items())
    )


def _material() -> flight.UseMaterial:
    return flight.UseMaterial(
        sample_id="tier1:000001",
        recipient_transcript="turn on the kitchen light",
        route=selftx.EvidenceRoute(
            available=True,
            facet_ids=("facet-1",),
            value_ids=("value-1",),
            task_targets=("setLighting",),
            scores=(2.0,),
            positive_facet_count=1,
            top1_margin=1.0,
            prompt_block="setLighting controls a light",
        ),
        evidence_contents=("setLighting controls a light",),
        donor_id=None,
        retrieval_query_sha256="b" * 64,
    )


def test_direct_adapter_is_byte_identical_and_use_context_precedes_suffix() -> None:
    registry = '[{"tool_name":"setLighting"}]'
    direct_messages = (
        {
            "role": "system",
            "content": _INSTRUCTION_TEMPLATE.format(tool_schemas=registry),
        },
        {
            "role": "user",
            "content": [{"type": "input_audio", "media_relpath": "audio/one.wav"}],
        },
    )
    with (
        patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None),
        patch.object(flight.Audio2ToolAdapter, "load_split", return_value=_samples()),
        patch.object(
            flight.Audio2ToolAdapter, "build_task_contract", return_value=registry
        ),
        patch.object(
            flight.Audio2ToolAdapter, "assemble_prompt", return_value=direct_messages
        ),
    ):
        direct = flight.A2TContractPreservingAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=flight.M0_DIRECT_PHASE,
        )
        samples = direct.load_split(flight.SPLIT_ID)
        direct.build_task_contract(samples[0], object())
        assert direct.assemble_prompt(samples[0], None) == direct_messages

        use = flight.A2TContractPreservingAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=flight.MATCHED_USE_PHASE,
            use_material={"tier1:000001": _material()},
        )
        selected = use.load_split(flight.SPLIT_ID)
        contract = use.build_task_contract(selected[0], object())
        messages = use.assemble_prompt(selected[0], None)
        assert contract.endswith(AUDIO2TOOL_OUTPUT_INSTRUCTION)
        assert messages[0]["content"] == contract
        assert use.score(selected[0], _valid()) == {"scoring_deferred": True}


@pytest.mark.parametrize(
    "phase",
    (flight.OBSERVATION_PHASE, flight.MATCHED_USE_PHASE, flight.SHUFFLED_USE_PHASE),
)
def test_non_direct_phases_reject_a_second_supply_channel(phase: str) -> None:
    material = None if phase == flight.OBSERVATION_PHASE else {"tier1:000001": _material()}
    with patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None):
        adapter = flight.A2TContractPreservingAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=phase,
            use_material=material,
        )
    with pytest.raises(flight.A2TContractPreservingFlightError, match="supply"):
        adapter.assemble_prompt(SimpleNamespace(sample_id="tier1:000001"), object())


def test_v2_controller_is_one_contact_and_liveness_bound() -> None:
    obs = flight.SingleContactController(phase=flight.OBSERVATION_PHASE)
    context = _runtime_context()
    contact = obs.initial_contact(context)
    assert contact.contact_id == flight.OBSERVATION_CONTACT_ID
    assert contact.instruction == selftx.SELF_TRANSCRIPT_INSTRUCTION
    advance = obs.advance(context, contact, "turn on the light")
    assert advance.next_contact is None
    assert advance.final_response_contact_id == flight.OBSERVATION_CONTACT_ID

    use = flight.SingleContactController(
        phase=flight.MATCHED_USE_PHASE,
        liveness_receipt=_liveness_receipt(),
    )
    assert use.initial_contact(context).contact_id == flight.MATCHED_CONTACT_ID
    failed = SimpleNamespace(passed=False, row_count=104, report_sha256="e" * 64)
    with pytest.raises(flight.A2TContractPreservingFlightError, match="liveness"):
        flight.SingleContactController(
            phase=flight.MATCHED_USE_PHASE,
            liveness_receipt=failed,
        )
    with pytest.raises(flight.A2TContractPreservingFlightError, match="unknown"):
        flight.SingleContactController(phase="UNKNOWN")
    with pytest.raises(flight.A2TContractPreservingFlightError, match="loop step"):
        obs.initial_contact(_runtime_context(loop_step=1))


def test_v2_run_phase_binds_openjiuwen_one_contact_and_packet_ids() -> None:
    summary = SimpleNamespace(
        results=(
            SimpleNamespace(sample_id="tier1:000001", contacts=(object(),)),
            SimpleNamespace(sample_id="tier1:000002", contacts=(object(),)),
        ),
        agent_executor_id=flight.AGENT_EXECUTOR_ID,
    )

    def fake_runner(**kwargs: object) -> object:
        assert kwargs["agent_executor_id"] == flight.AGENT_EXECUTOR_ID
        assert kwargs["max_contacts"] == 1
        return summary

    returned = flight.run_phase(
        phase=flight.OBSERVATION_PHASE,
        data_root=SimpleNamespace(),
        plan=SimpleNamespace(),
        adapter=SimpleNamespace(),
        core_client=SimpleNamespace(),
        split_id=flight.SPLIT_ID,
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings={
            "tier1:000001": {},
            "tier1:000002": {},
        },
        trace_sink=SimpleNamespace(),
        slot_count=2,
        queue_depth=4,
        decoding_params={},
        agent_runner=fake_runner,
    )
    assert returned is summary

    with pytest.raises(flight.A2TContractPreservingFlightError, match="identity"):
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
            queue_depth=4,
            decoding_params={},
            agent_runner=fake_runner,
        )


def test_direct_phase_has_no_agent_history_and_keeps_system_bytes() -> None:
    samples = (
        SimpleNamespace(sample_id="tier1:000001", media_relpath="one.wav"),
        SimpleNamespace(sample_id="tier1:000002", media_relpath="two.wav"),
    )
    system = _INSTRUCTION_TEMPLATE.format(tool_schemas="registry")

    class Adapter:
        def load_split(self, split_id: str):
            assert split_id == flight.SPLIT_ID
            return samples

        def build_task_contract(self, sample: object, obs: object) -> str:
            return "registry"

        def assemble_prompt(self, sample: object, supply: object):
            assert supply is None
            return (
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_audio",
                            "media_relpath": sample.media_relpath,
                        }
                    ],
                },
            )

    calls: list[tuple[object, dict[str, object]]] = []

    class Client:
        def complete(self, messages: object, **kwargs: object) -> str:
            calls.append((messages, kwargs))
            return _valid()

    summary = flight.run_direct_phase(
        adapter=Adapter(),
        core_client=Client(),
        split_id=flight.SPLIT_ID,
        speech_packet_bindings={
            "tier1:000001": {"packet_id": "packet/one", "sha256": "1" * 64},
            "tier1:000002": {"packet_id": "packet/two", "sha256": "2" * 64},
        },
        slot_count=2,
        decoding_params={"temperature": 0},
    )

    assert [result.sample_id for result in summary.results] == [
        "tier1:000001",
        "tier1:000002",
    ]
    assert len(calls) == 2
    for messages, kwargs in calls:
        assert messages[0]["content"] == system
        assert messages[1]["content"][0]["type"] == "input_speech_features"
        assert "agent_state" not in kwargs
        assert "agent_contact_id" not in kwargs
        assert "contact_instruction" not in kwargs


def test_observation_adapter_keeps_registry_and_output_schema_out() -> None:
    with (
        patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None),
        patch.object(flight.Audio2ToolAdapter, "load_split", return_value=_samples()),
    ):
        adapter = flight.A2TContractPreservingAdapter(
            {},
            SimpleNamespace(),
            repo_root=SimpleNamespace(),
            receipt_items=_receipt_items(),
            phase=flight.OBSERVATION_PHASE,
        )
        samples = adapter.load_split(flight.SPLIT_ID)
        contract = adapter.build_task_contract(samples[0], object())
        messages = adapter.assemble_prompt(samples[0], None)
    assert contract == selftx.SELF_TRANSCRIPT_INSTRUCTION
    assert messages[0]["content"] == contract
    assert "Available tools" not in repr(messages)
    assert "arguments" not in repr(messages)


def test_v2_adapter_rejects_drifted_receipts_and_material() -> None:
    with patch.object(flight.Audio2ToolAdapter, "__init__", return_value=None):
        with pytest.raises(flight.A2TContractPreservingFlightError, match="unknown"):
            flight.A2TContractPreservingAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=_receipt_items(),
                phase="UNKNOWN",
            )
        with pytest.raises(flight.A2TContractPreservingFlightError, match="duplicate"):
            flight.A2TContractPreservingAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=(_receipt_items()[0], _receipt_items()[0]),
                phase=flight.OBSERVATION_PHASE,
            )
        with pytest.raises(flight.A2TContractPreservingFlightError, match="USE material"):
            flight.A2TContractPreservingAdapter(
                {},
                SimpleNamespace(),
                repo_root=SimpleNamespace(),
                receipt_items=_receipt_items(),
                phase=flight.MATCHED_USE_PHASE,
            )


def test_committed_mechanism_result_closes_failed_policy_without_losing_gain() -> None:
    repo = Path(__file__).resolve().parents[2]
    path = (
        repo
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-contract-preserving-cascade-104-v2"
        / "mechanism-result.json"
    )
    result = json.loads(path.read_text(encoding="utf-8"))
    scores = result["official_scores"]
    effects = result["mechanism_effects"]
    policy = result["training_free_policy"]
    conclusion = result["scientific_conclusion"]

    assert scores["matched_always_use"]["exact_count"] - scores["m0_direct"][
        "exact_count"
    ] == effects["matched_minus_m0_exact_count"] == 8
    assert scores["matched_always_use"]["exact_count"] - scores[
        "shuffled_evidence"
    ]["exact_count"] == effects["matched_minus_shuffled_exact_count"] == 12
    assert policy["saved"] == 0
    assert policy["harmed"] == 2
    assert policy["net_exact_count"] == -2
    assert policy["promotion_passed"] is False
    assert conclusion == {
        "agent_over_single_call": True,
        "matched_information_gain": True,
        "training_free_rl_positive_contribution": False,
        "support_flight_authorized": False,
        "approximately_1000_scale_authorized": False,
        "baseline_change_authorized": False,
        "decision": conclusion["decision"],
    }
