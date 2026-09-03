"""Contact-free tests for the concrete SELECT/FILL 104-row runtime."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan


REPO = Path(__file__).resolve().parents[2]
FACTORY = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1/launcher/"
    "local_runtime_factory.py"
)


def _factory():
    name = "test_a2t_select_fill_local_runtime_factory"
    spec = importlib.util.spec_from_file_location(name, FACTORY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _authority(module):
    roles = (
        "M0_DIRECT",
        "OBS_SEMANTIC_STATE",
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    preregistration = "e" * 64
    plans = {}
    for index, role in enumerate(roles):
        plan = ExecutionPlan(
            run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2",
            execution_profile="bounded-discovery-probe",
            carrier_lock_key="audio2tool",
            split_role="discovery",
            split_identity_hash="a" * 64,
            planned_model_calls=624,
            planned_gpu_hours=4.0,
            planned_speech_audio_seconds=3400,
            protocol_hash="b" * 64,
            attempt_id=f"attempt-select-fill-{index}",
        ).validate()
        plans[role] = {
            **asdict(plan),
            "exposure_preregistration_sha256": preregistration,
        }
    plan_material = {
        role: {
            key: value
            for key, value in plans[role].items()
            if key in ExecutionPlan.__dataclass_fields__
        }
        for role in roles
    }
    embedding = ExecutionPlan(
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2-EMBED",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=104,
        planned_gpu_hours=0.2,
        planned_speech_audio_seconds=1,
        protocol_hash="b" * 64,
        attempt_id="attempt-select-fill-embedding",
    ).validate()
    return {
        "split_identity_hash": "a" * 64,
        "core_protocol_sha256": "b" * 64,
        "hashes": {
            "exposure_preregistration_sha256": preregistration,
            "execution_plan_set_sha256": module._sha256_json(plan_material),
            "embedding_execution_plan_sha256": module._sha256_json(
                asdict(embedding)
            ),
        },
        "execution_plans": plans,
        "embedding_execution_plan": {
            **asdict(embedding),
            "exposure_preregistration_sha256": preregistration,
        },
    }, roles


def test_execution_plans_bind_six_phases_and_full_flight_budget() -> None:
    module = _factory()
    authority, roles = _authority(module)

    parsed = module.parse_execution_plans(
        authority,
        roles=roles,
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2",
    )

    assert tuple(parsed) == roles
    assert {plan.planned_model_calls for plan in parsed.values()} == {624}
    assert {plan.planned_gpu_hours for plan in parsed.values()} == {4.0}
    assert {plan.planned_speech_audio_seconds for plan in parsed.values()} == {3400}
    authority["execution_plans"][roles[1]][
        "exposure_preregistration_sha256"
    ] = "f" * 64
    with pytest.raises(RuntimeError, match="preregistration binding drift"):
        module.parse_execution_plans(
            authority,
            roles=roles,
            run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2",
        )


def test_embedding_plan_is_separate_and_counts_104_logical_items() -> None:
    module = _factory()
    authority, _roles = _authority(module)

    plan = module.parse_embedding_execution_plan(
        authority, protocol_sha256="b" * 64
    )

    assert plan.planned_model_calls == 104
    authority["embedding_execution_plan"]["planned_model_calls"] = 103
    with pytest.raises(RuntimeError, match="identity or budget drift"):
        module.parse_embedding_execution_plan(
            authority, protocol_sha256="b" * 64
        )


def test_flattened_physical_body_hashes_include_slot_and_packet_role() -> None:
    module = _factory()
    launcher = SimpleNamespace(
        M0_PHASE="M0_DIRECT",
        OBS_PHASE="OBS_SEMANTIC_STATE",
        JOINT_PHASE="JOINT_ONE_CALL",
        SELECT_PHASE="SELECT",
        REVISE_PHASE="JOINT_DRAFT_REVISE",
        FILL_PHASE="FILL",
        PreparedGenerationRequest=SimpleNamespace(from_body=lambda **kwargs: kwargs),
    )
    binding = {"packet_id": "tier1_direct/000001", "sha256": "c" * 64}
    body = module._physical_body(
        messages=(
            {"role": "system", "content": "English ground"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {**binding, "role": "query"},
                    }
                ],
            },
        ),
        decoding_params={"temperature": 0, "max_tokens": 1024},
    )
    prepared = module._prepared_request(
        launcher,
        phase="M0_DIRECT",
        sample_id="tier1_direct:000001",
        binding=binding,
        body=body,
    )

    assert "decoding_params" not in body
    assert body["temperature"] == 0
    assert prepared["packet_id"] == binding["packet_id"]
    for slot, encoded in enumerate(prepared["body"].get("unused", ())):
        assert json.loads(encoded)["id_slot"] == slot


def test_phase_gate_registry_keeps_paired_preflights_independent() -> None:
    module = _factory()
    runtime = object.__new__(module.LocalSelectFillRuntime)
    runtime.phase_gates = {"JOINT_ONE_CALL": object(), "SELECT": object()}

    joint = runtime._phase_gate("JOINT_ONE_CALL")
    select = runtime._phase_gate("SELECT")

    assert joint is not select
    assert runtime._phase_gate("JOINT_ONE_CALL") is joint


def test_stage_envelope_is_sealed_from_exact_response_and_lineage() -> None:
    module = _factory()
    candidate_names = ("alpha",) + tuple(f"tool_{index}" for index in range(31))
    candidate = SimpleNamespace(
        tool_names=candidate_names,
        candidate_set_sha256=module._sha256_json(list(candidate_names)),
    )
    observation = SimpleNamespace(
        state_sha256="1" * 64,
        source_response_sha256="2" * 64,
    )
    request = SimpleNamespace(
        sample_id="sample-1",
        ground_sha256="3" * 64,
        base_body={
            "response_format": {
                "type": "json_schema",
                "json_schema": {"strict": True, "schema": {}},
            }
        },
    )
    response = SimpleNamespace(
        sample_id="sample-1",
        response_bytes=b'[{"name":"alpha","arguments":{}}]',
        response_sha256=hashlib.sha256(
            b'[{"name":"alpha","arguments":{}}]'
        ).hexdigest(),
        request_body_sha256="4" * 64,
        source_query_state_sha256="5" * 64,
    )

    envelope = module._seal_stage_envelope(
        expected_stage="JOINT_DRAFT",
        sample_id="sample-1",
        request=request,
        response=response,
        observation=observation,
        candidate=candidate,
        packet_sha256="6" * 64,
        split_identity_sha256="7" * 64,
    )

    assert envelope.source_response_sha256 == response.response_sha256
    assert envelope.source_request_body_sha256 == response.request_body_sha256
    assert envelope.candidate_set_sha256 == candidate.candidate_set_sha256
    assert envelope.payload.calls[0].arguments == {}
