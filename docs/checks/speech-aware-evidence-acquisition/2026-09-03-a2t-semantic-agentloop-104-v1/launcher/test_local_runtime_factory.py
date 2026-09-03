"""Contact-free tests for the concrete semantic flight runtime."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    render_audio2tool_instruction,
)


FACTORY = Path(__file__).with_name("local_runtime_factory.py")


def _factory():
    name = "test_a2t_semantic_local_runtime_factory"
    spec = importlib.util.spec_from_file_location(name, FACTORY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _authority(module):
    roles = (
        "direct_m0",
        "obs_semantic_retrieval",
        "transcript_top16_use",
        "model_query_top16_use",
        "rrf_fused_top16_use",
        "same_stratum_shuffled_fused_use",
    )
    preregistration = "e" * 64
    plans = {}
    for index, role in enumerate(roles):
        plan = ExecutionPlan(
            run_id="SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
            execution_profile="bounded-discovery-probe",
            carrier_lock_key="audio2tool",
            split_role="discovery",
            split_identity_hash="a" * 64,
            planned_model_calls=624,
            planned_gpu_hours=1.0,
            planned_speech_audio_seconds=1,
            protocol_hash="b" * 64,
            attempt_id=f"attempt-semantic-{index}",
        ).validate()
        plans[role] = {**asdict(plan), "exposure_preregistration_sha256": preregistration}
    material = {
        role: {key: value for key, value in plans[role].items()
               if key in ExecutionPlan.__dataclass_fields__}
        for role in roles
    }
    embedding_plan = ExecutionPlan(
        run_id="SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=208,
        planned_gpu_hours=0.2,
        planned_speech_audio_seconds=1,
        protocol_hash="b" * 64,
        attempt_id="attempt-semantic-embedding",
    ).validate()
    return {
        "split_identity_hash": "a" * 64,
        "core_protocol_sha256": "b" * 64,
        "hashes": {
            "exposure_preregistration_sha256": preregistration,
            "execution_plan_set_sha256": module._sha256_json(material),
            "embedding_execution_plan_sha256": module._sha256_json(
                asdict(embedding_plan)
            ),
        },
        "execution_plans": plans,
        "embedding_execution_plan": {
            **asdict(embedding_plan),
            "exposure_preregistration_sha256": preregistration,
        },
    }, roles


def test_execution_plan_parser_filters_and_binds_preregistration() -> None:
    module = _factory()
    authority, roles = _authority(module)

    parsed = module.parse_execution_plans(
        authority,
        roles=roles,
        run_id="SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
    )
    assert tuple(parsed) == roles
    assert all(isinstance(value, ExecutionPlan) for value in parsed.values())

    authority["execution_plans"][roles[2]]["exposure_preregistration_sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="preregistration binding drift"):
        module.parse_execution_plans(
            authority,
            roles=roles,
            run_id="SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1",
        )


def test_embedding_execution_plan_is_separate_and_exact() -> None:
    module = _factory()
    authority, _roles = _authority(module)

    plan = module.parse_embedding_execution_plan(
        authority, protocol_sha256="b" * 64
    )

    assert plan.run_id == "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED"
    assert plan.planned_model_calls == 208
    authority["embedding_execution_plan"]["planned_model_calls"] = 207
    with pytest.raises(RuntimeError, match="identity or budget drift"):
        module.parse_embedding_execution_plan(
            authority, protocol_sha256="b" * 64
        )


def test_embedding_spec_pins_historical_last_pooling_argv() -> None:
    module = _factory()
    runtime = object.__new__(module.LocalSemanticRuntime)
    runtime.spec = {"embedding": {
        "base_url": "http://127.0.0.1:8082",
        "server_args": [
            "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
            "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
        ],
        "expected_dim": 1024,
        "physical_batch_size": 32,
    }}
    assert runtime._embedding_spec()["physical_batch_size"] == 32
    runtime.spec["embedding"]["server_args"][2] = "mean"
    with pytest.raises(RuntimeError, match="last pooling"):
        runtime._embedding_spec()


def test_direct_contract_is_the_standard_audio2tool_instruction() -> None:
    module = _factory()
    registry = '{"name":"exampleTool","arguments":{}}'
    assert module.build_direct_task_contract(registry) == render_audio2tool_instruction(
        registry
    )
    assert module.build_direct_task_contract(registry) != registry


def test_factory_pins_committed_four_fragment_composition() -> None:
    module = _factory()
    assert module.COMMITTED_CONFIG_FRAGMENTS == {
        "model": "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "dataset": "audio2tool-semantic-agentloop-104-v2",
        "baseline": "a2t-semantic-agentloop-top16",
        "experiment": "a2t-semantic-agentloop-104-v1",
    }
    composed = compose(FACTORY.resolve().parents[5], **module.COMMITTED_CONFIG_FRAGMENTS)
    assert composed.config_hash == (
        "b35b37829cef7fb792980c4099efb6a5efb34605c0b1da5be97a5b12aed38113"
    )
    assert "split_name" not in composed.values
    assert composed.values["a2t_semantic_agentloop_split_name"] == (
        "A2T-AGENTLOOP-FRESH-FLIGHT"
    )
    assert protocol_hash(
        composed.config_hash,
        "speech-feature-query",
        "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0",
    ) == "6d793633efd6d7222d9b1cf0811520c116fca90e9043b3a3222284350f499c38"


def test_semantic_materializer_accepts_new_roles_and_rejects_unknown() -> None:
    module = _factory()
    results = tuple(
        SimpleNamespace(sample_id=f"s-{index:03d}", final_response_text="[]")
        for index in range(104)
    )
    traces = []
    for index in range(104):
        request_id = f"req-{index:03d}"
        sample_id = f"s-{index:03d}"
        request_hash = hashlib.sha256(sample_id.encode()).hexdigest()
        response_hash = hashlib.sha256(b"response").hexdigest()
        traces.extend((
            {"channel": "MODEL_REQUEST", "record_id": request_id + "/request",
             "payload": {"arm": "speech-feature-query", "payload": {"sample_id": sample_id},
                         "payload_sha256": request_hash}},
            {"channel": "MODEL_RESPONSE", "record_id": request_id + "/response",
             "payload": {"text": "[]", "response_text_sha256": hashlib.sha256(b"[]").hexdigest(),
                         "response_sha256": response_hash}},
            {"channel": "COST", "record_id": request_id + "/cost",
             "payload": {"calls": 1, "audio_seconds": 1.0, "latency_seconds": 0.1,
                         "prompt_tokens": 10, "completion_tokens": 2}},
        ))
    rows, cost = module._semantic_bundle_material(
        SimpleNamespace(results=results),
        traces,
        role="rrf_fused_top16_use",
        umbrella_lock_sha256="c" * 64,
    )
    assert len(rows) == 104
    assert {row["phase"] for row in rows} == {"rrf_fused_top16_use"}
    assert cost["calls_used"] == 104
    with pytest.raises(RuntimeError, match="role or lock"):
        module._semantic_bundle_material(
            SimpleNamespace(results=results), traces, role="USE_MATCHED",
            umbrella_lock_sha256="c" * 64,
        )
