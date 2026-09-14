"""Audio2ToolAdapter (B0 rails, first concrete TaskAdapter) + the mission's
own required "runner executes end-to-end with the mock core client on the
Audio2Tool adapter" test.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails import (
    ConsumptionOutcome,
    MockCoreClient,
    SupplyDose,
    SupplyForm,
    SupplyItem,
    SupplyPacket,
    run_rails_experiment,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    AUDIO2TOOL_OUTPUT_INSTRUCTION,
    _INSTRUCTION_TEMPLATE,
    Audio2ToolAdapter,
    render_audio2tool_instruction,
)
from speech_aware_evidence_acquisition.rails.task_adapter import CandidateInventory
from speech_aware_evidence_acquisition.rails.obs import default_obs_packet

_SHA_A = "a" * 64
_SET_LIGHTING_RESPONSE = json.dumps([{"name": "setLighting", "arguments": {}}])


def _adapter(world) -> Audio2ToolAdapter:
    lock = load_lock(world.lock_path)
    return Audio2ToolAdapter(lock, world.data_root, repo_root=world.repo_root)


def test_load_split_discovery_returns_the_receipt_samples_sorted(audio2tool_world):
    samples = _adapter(audio2tool_world).load_split("discovery")
    assert [s.sample_id for s in samples] == [
        "tier1_direct:000001",
        "tier3_multi_intent:000004",
        "tier7_multiturn:000009",
    ]
    assert samples[0].media_relpath == (
        "datasets/audio2tool/public/tier1_direct_audios/query_00001/turn.wav"
    )
    assert samples[0].audio_ref.path == samples[0].media_relpath
    assert len(samples[0].audio_ref.sha256) == 64


def test_load_split_unknown_split_role_raises(audio2tool_world):
    with pytest.raises(ValueError, match="split_role"):
        _adapter(audio2tool_world).load_split("confirmatory")


def test_build_task_contract_is_the_rendered_tool_schema_registry(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    # The contract does not read obs for this carrier: it is stable task
    # schema knowledge, while the query remains the speech observation.
    obs = default_obs_packet(sample)
    task_contract = adapter.build_task_contract(sample, obs)
    assert '"tool_name": "setLighting"' in task_contract
    assert '"tool_name": "setSecurityMode"' in task_contract


def test_candidate_inventory_is_lazy_cached_source_bound_and_gold_free(
    audio2tool_world, monkeypatch
):
    from speech_aware_evidence_acquisition.rails.adapters import audio2tool as module

    calls = []
    real_load = module.load_tool_registry_with_sha256

    def load_once(*args):
        calls.append(args)
        return real_load(*args)

    def forbidden_gold(*args, **kwargs):
        raise AssertionError("candidate inventory must not read scorer-side gold")

    monkeypatch.setattr(module, "load_tool_registry_with_sha256", load_once)
    monkeypatch.setattr(module, "load_expected_calls", forbidden_gold)
    monkeypatch.setattr(module, "load_audio2tool", forbidden_gold)
    monkeypatch.setattr(module, "audio2tool_receipts", forbidden_gold)
    adapter = _adapter(audio2tool_world)
    assert calls == []

    first = adapter.candidate_inventory()
    second = adapter.candidate_inventory()
    registry_bytes = (audio2tool_world.carrier_dir / "tools_registry.csv").read_bytes()

    assert first is second
    assert calls and len(calls) == 1
    assert first == CandidateInventory(
        candidate_ids=("setLighting", "setSecurityMode"),
        source_sha256=hashlib.sha256(registry_bytes).hexdigest(),
        source_authority="audio2tool-public-tool-registry",
    )


def test_assemble_prompt_zero_supply_has_no_text_content_part(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    messages = adapter.assemble_prompt(sample, None)
    assert messages[0]["role"] == "system"
    assert "{tool_schemas}" not in messages[0]["content"]
    user_content = messages[1]["content"]
    assert all(part["type"] != "text" for part in user_content)
    assert user_content[-1] == {"type": "input_audio", "media_relpath": sample.media_relpath}


def test_instruction_renderer_preserves_direct_bytes_and_final_output_contract():
    registry = '[{"tool_name":"setLighting"}]'
    direct = render_audio2tool_instruction(registry)
    enriched = render_audio2tool_instruction(
        registry,
        auxiliary_context="English self-transcript Agent state:\nturn on the light",
    )

    assert direct == _INSTRUCTION_TEMPLATE.format(tool_schemas=registry)
    assert direct.endswith(AUDIO2TOOL_OUTPUT_INSTRUCTION)
    assert enriched.endswith(AUDIO2TOOL_OUTPUT_INSTRUCTION)
    assert enriched.count(AUDIO2TOOL_OUTPUT_INSTRUCTION) == 1
    assert "English self-transcript Agent state" in enriched
    assert enriched.index("English self-transcript Agent state") < enriched.index(
        AUDIO2TOOL_OUTPUT_INSTRUCTION
    )
    assert '[{"name": "x", "arguments": {}}]' in enriched

    with pytest.raises(ValueError, match="tool schemas"):
        render_audio2tool_instruction("")
    with pytest.raises(ValueError, match="auxiliary context"):
        render_audio2tool_instruction(registry, auxiliary_context=" ")


def test_assemble_prompt_with_supply_includes_the_prompt_block(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=2),
        prompt_block="Known tools: setLighting",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="setLighting"),),
    )
    messages = adapter.assemble_prompt(sample, supply)
    user_content = messages[1]["content"]
    assert user_content[0] == {"type": "text", "text": "Known tools: setLighting"}
    assert user_content[-1]["type"] == "input_audio"


def test_score_matches_the_frozen_gold(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]  # tier1_direct:000001 -> setLighting()
    metrics = adapter.score(sample, _SET_LIGHTING_RESPONSE)
    assert metrics["tool_accuracy"] == 1.0
    assert metrics["exact_match"] == 1.0
    assert metrics["parsed"] is True


def test_score_unknown_sample_id_raises(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    bogus = type(sample)(
        sample_id="tier1_direct:999999",
        audio_ref=sample.audio_ref,
        audio_seconds=sample.audio_seconds,
        media_relpath=sample.media_relpath,
    )
    with pytest.raises(ValueError, match="probe receipt"):
        adapter.score(bogus, _SET_LIGHTING_RESPONSE)


def test_extract_consumption_zero_supply_is_empty(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    trace = adapter.extract_consumption(sample, None, _SET_LIGHTING_RESPONSE)
    assert trace.records == ()


def test_extract_consumption_with_supply_detects_the_copy(audio2tool_world):
    adapter = _adapter(audio2tool_world)
    sample = adapter.load_split("discovery")[0]
    supply = SupplyPacket(
        form=SupplyForm.ROSTER,
        dose=SupplyDose(n_items=1, token_count=1),
        prompt_block="setLighting",
        assembly_template_id="roster-v1",
        items=(SupplyItem(item_id="i1", text="setLighting"),),
    )
    trace = adapter.extract_consumption(sample, supply, _SET_LIGHTING_RESPONSE)
    assert trace.records[0].outcome == ConsumptionOutcome.COPY
    assert trace.copy_rate == 1.0


# ---------------------------------------------------------------------------
# Mission-required test: runner executes end-to-end with the mock core
# client on the Audio2Tool adapter.
# ---------------------------------------------------------------------------


def _plan() -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-E-TEST-rails-a2t",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=_SHA_A,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash=protocol_hash("f" * 64, "bare-core", _SHA_A),
        attempt_id="attempt-rails-a2t-0001",
    )


def test_runner_executes_end_to_end_with_the_mock_core_client_on_audio2tool(audio2tool_world, tmp_path):
    adapter = _adapter(audio2tool_world)
    client = MockCoreClient(responder=lambda messages: _SET_LIGHTING_RESPONSE)

    def supply_builder(sample, obs, task_contract):
        return SupplyPacket(
            form=SupplyForm.ROSTER,
            dose=SupplyDose(n_items=1, token_count=1),
            prompt_block="setLighting",
            assembly_template_id="roster-v1",
            items=(SupplyItem(item_id="i1", text="setLighting"),),
        )

    summary = run_rails_experiment(
        data_root=tmp_path,
        plan=_plan(),
        adapter=adapter,
        core_client=client,
        split_id="discovery",
        supply_builder=supply_builder,
    )

    # 3 receipt samples x 2 arms (zero-supply, supplied)
    assert len(summary.results) == 6
    assert len(client.calls) == 6
    zero_supply = [r for r in summary.results if r.arm == "zero-supply"]
    supplied = [r for r in summary.results if r.arm == "supplied"]
    assert len(zero_supply) == len(supplied) == 3
    assert all(r.response_text == _SET_LIGHTING_RESPONSE for r in summary.results)
    assert all(r.consumption.records == () for r in zero_supply)
    assert all(r.consumption.copy_rate == 1.0 for r in supplied)
    # score() ran real, frozen-gold scoring for every result -- the
    # tier1_direct:000001 sample's gold really is setLighting().
    tier1_zero = next(r for r in zero_supply if r.sample_id == "tier1_direct:000001")
    assert tier1_zero.metrics["tool_accuracy"] == 1.0
