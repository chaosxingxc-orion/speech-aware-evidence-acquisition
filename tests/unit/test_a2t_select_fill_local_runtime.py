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
from speech_aware_evidence_acquisition.core.bundle import verify_bundle
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit


REPO = Path(__file__).resolve().parents[2]
FACTORY = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1/launcher/"
    "local_runtime_factory.py"
)
LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1/launcher/"
    "launch_a2t_select_fill_agentloop_104.py"
)


def _factory():
    name = "test_a2t_select_fill_local_runtime_factory"
    spec = importlib.util.spec_from_file_location(name, FACTORY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _launcher():
    name = "test_a2t_select_fill_local_runtime_launcher"
    spec = importlib.util.spec_from_file_location(name, LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _authority(module):
    roles = (
        "JOINT_ONE_CALL",
        "SELECT",
        "JOINT_DRAFT_REVISE",
        "FILL",
    )
    preregistration = "e" * 64
    plans = {}
    for index, role in enumerate(roles):
        plan = ExecutionPlan(
            run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
            execution_profile="bounded-discovery-probe",
            carrier_lock_key="audio2tool",
            split_role="discovery",
            split_identity_hash="a" * 64,
            planned_model_calls=416,
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
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5-EMBED",
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


def test_execution_plans_bind_only_four_remaining_phases_and_budget() -> None:
    module = _factory()
    authority, roles = _authority(module)

    parsed = module.parse_execution_plans(
        authority,
        roles=roles,
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
    )

    assert tuple(parsed) == roles
    assert {plan.planned_model_calls for plan in parsed.values()} == {416}
    assert {plan.planned_gpu_hours for plan in parsed.values()} == {4.0}
    assert {plan.planned_speech_audio_seconds for plan in parsed.values()} == {3400}
    authority["execution_plans"][roles[1]][
        "exposure_preregistration_sha256"
    ] = "f" * 64
    with pytest.raises(RuntimeError, match="preregistration binding drift"):
        module.parse_execution_plans(
            authority,
            roles=roles,
            run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
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


def test_phase_trace_path_points_to_the_agent_loop_sink(tmp_path) -> None:
    module = _factory()

    assert module._phase_trace_path(tmp_path, "RUN-ID") == (
        tmp_path / "agent-loop" / "RUN-ID.trace.jsonl"
    )


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


def test_obs_trace_rehydration_proves_104_unique_responses_and_query_states(
    tmp_path,
) -> None:
    module = _factory()
    launcher = _launcher()
    sample_ids = tuple(f"fresh:{index:03d}" for index in range(104))
    requests = tuple(
        SimpleNamespace(
            sample_id=sample_id,
            body_sha256_by_slot=(f"{index + 1:064x}", f"{index + 201:064x}"),
        )
        for index, sample_id in enumerate(sample_ids)
    )
    packet_bindings = {
        sample_id: {"sha256": f"{index + 401:064x}"}
        for index, sample_id in enumerate(sample_ids)
    }
    sent = {
        sample_id: requests[index].body_sha256_by_slot[index % 2]
        for index, sample_id in enumerate(sample_ids)
    }
    records = []
    for index, sample_id in enumerate(sample_ids):
        request_id = f"obs-{index:03d}"
        request_payload = {
            "request_id": request_id,
            "sample_id": sample_id,
            "speech_packet_sha256": packet_bindings[sample_id]["sha256"],
        }
        response = f'{{"transcript":"utterance {index:03d}"}}'
        raw_response_sha256 = f"{index + 601:064x}"
        text_response_sha256 = hashlib.sha256(response.encode("ascii")).hexdigest()
        records.extend(
            (
                {
                    "channel": "MODEL_REQUEST",
                    "record_id": f"{request_id}/request",
                    "payload": {
                        "arm": "speech-feature-query",
                        "payload": request_payload,
                        "payload_sha256": module._sha256_json(request_payload),
                    },
                },
                {
                    "channel": "MODEL_RESPONSE",
                    "record_id": f"{request_id}/response",
                    "payload": {
                        "response_sha256": raw_response_sha256,
                        "response_text_sha256": text_response_sha256,
                        "text": response,
                        "usage": {},
                    },
                },
                {
                    "channel": "USE",
                    "record_id": f"{sample_id}/agent-loop/runtime-use",
                    "payload": {
                        "use_final_response_sha256": text_response_sha256,
                        "use_contacts": [
                            {
                                "query_state_sha256": f"{index + 801:064x}",
                                "response_sha256": text_response_sha256,
                            }
                        ],
                    },
                },
            )
        )
    trace = tmp_path / "obs.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="ascii",
    )

    output = module._load_recovery_trace_rows(
        launcher=launcher,
        phase=launcher.OBS_PHASE,
        trace_path=trace,
        expected_trace_sha256=module._sha256_file(trace),
        requests=requests,
        packet_bindings=packet_bindings,
        sent_body_sha256_by_sample=sent,
    )

    assert len(output.rows) == 104
    assert len({row.response_sha256 for row in output.rows}) == 104
    assert len({row.source_query_state_sha256 for row in output.rows}) == 104
    assert tuple(row.sample_id for row in output.rows) == sample_ids


def test_post_embedding_checkpoint_round_trips_k32_and_refuses_tampering(
    tmp_path,
) -> None:
    module = _factory()
    launcher = _launcher()
    sample_ids = tuple(f"fresh:{index:03d}" for index in range(104))
    observations = {
        sample_id: launcher.ObservationArtifact(
            sample_id=sample_id,
            transcript=f"utterance {index:03d}",
            state_sha256=f"{index + 1:064x}",
            source_response_sha256=f"{index + 201:064x}",
        )
        for index, sample_id in enumerate(sample_ids)
    }
    candidates = {
        sample_id: launcher.CandidateSet(
            sample_id=sample_id,
            tool_names=tuple(f"tool_{tool:02d}" for tool in range(32)),
            scores=tuple(1.0 - tool / 100 for tool in range(32)),
            query_state_sha256=observations[sample_id].state_sha256,
        )
        for sample_id in sample_ids
    }
    checkpoint = tmp_path / "post-embedding-k32.json"

    receipt = module._write_post_embedding_checkpoint(
        checkpoint,
        launcher=launcher,
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        source_report_sha256="a" * 64,
        observations=observations,
        candidates=candidates,
    )
    loaded = module._load_post_embedding_checkpoint(
        checkpoint,
        launcher=launcher,
        expected_sha256=receipt["checkpoint_sha256"],
        run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
        source_report_sha256="a" * 64,
        observations=observations,
    )

    assert loaded == candidates
    checkpoint.write_text(checkpoint.read_text(encoding="ascii") + " ", encoding="ascii")
    with pytest.raises(RuntimeError, match="checkpoint SHA-256 drift"):
        module._load_post_embedding_checkpoint(
            checkpoint,
            launcher=launcher,
            expected_sha256=receipt["checkpoint_sha256"],
            run_id="SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5",
            source_report_sha256="a" * 64,
            observations=observations,
        )


def test_recovered_direct_seals_a_standard_verified_source_named_bundle(
    tmp_path,
    monkeypatch,
) -> None:
    module = _factory()
    launcher = _launcher()
    roster = json.loads(launcher.ROSTER_PATH.read_text(encoding="utf-8"))
    sample_ids = tuple(sorted(row["sample_id"] for row in roster["items"]))
    source_plan = ExecutionPlan(
        run_id=launcher.SOURCE_RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=launcher.SPLIT_IDENTITY_HASH,
        planned_model_calls=624,
        planned_gpu_hours=4.0,
        planned_speech_audio_seconds=3400,
        protocol_hash="d" * 64,
        attempt_id="attempt-source-direct-v2",
    ).validate()
    source_trace = tmp_path / "source.trace.jsonl"
    trace_records = []
    responses = []
    for index, sample_id in enumerate(sample_ids):
        request_id = f"source-direct-{index:03d}"
        request_payload = {"sample_id": sample_id}
        request_sha256 = module._sha256_json(request_payload)
        text = "[]"
        text_sha256 = hashlib.sha256(text.encode("ascii")).hexdigest()
        trace_records.extend(
            (
                {
                    "channel": "MODEL_REQUEST",
                    "record_id": f"{request_id}/request",
                    "payload": {
                        "arm": module.GENERATION_ARM,
                        "payload": request_payload,
                        "payload_sha256": request_sha256,
                    },
                },
                {
                    "channel": "MODEL_RESPONSE",
                    "record_id": f"{request_id}/response",
                    "payload": {
                        "response_sha256": f"{index + 1:064x}",
                        "response_text_sha256": text_sha256,
                        "text": text,
                        "usage": {},
                    },
                },
                {
                    "channel": "COST",
                    "record_id": f"{request_id}/cost",
                    "payload": {
                        "calls": 1,
                        "audio_seconds": 549.0 / 104,
                        "latency_seconds": 1.0,
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                    },
                },
            )
        )
        responses.append(
            launcher.GenerationResponse(
                sample_id=sample_id,
                phase=launcher.M0_PHASE,
                request_body_sha256=f"{index + 201:064x}",
                response_bytes=text.encode("ascii"),
            )
        )
    source_trace.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace_records),
        encoding="ascii",
    )
    source_session = tmp_path / "source-session-receipt.json"
    source_session.write_text('{"status":"STOPPED"}\n', encoding="ascii")
    source_authority = tmp_path / "source-authority-binding.json"
    source_authority.write_text(
        json.dumps({"contact_plans": {launcher.M0_PHASE: asdict(source_plan)}}) + "\n",
        encoding="ascii",
    )
    data_root = tmp_path / "data"
    source_attempt = (
        data_root
        / "attempts"
        / source_plan.run_id
        / f"{source_plan.attempt_id}.json"
    )
    source_attempt.parent.mkdir(parents=True)
    source_attempt.write_text(
        json.dumps(
            {
                "schema": "saea-attempt-v1",
                "run_id": source_plan.run_id,
                "attempt_id": source_plan.attempt_id,
                "carrier_lock_key": "audio2tool",
                "state": "ABORTED",
                "reserved": {"calls": 624, "audio_seconds": 3400.0},
                "actual": {"calls": 104, "audio_seconds": 549.0},
                "failure_reason": "A later local preflight failed.",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="ascii",
    )
    runtime = object.__new__(module.LocalSelectFillRuntime)
    runtime.launcher = launcher
    runtime.repo = REPO
    runtime.data_root = data_root
    runtime.mission_dir = tmp_path / "v3-mission"
    runtime.mission_dir.mkdir()
    runtime.composed = module.compose(REPO, **module.COMMITTED_CONFIG_FRAGMENTS)
    runtime.verified_split = VerifiedSplit(
        name=launcher.SPLIT_ID,
        carrier_lock_key="audio2tool",
        split_role="discovery",
        ids=sample_ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in sample_ids),
        identity_hash=launcher.BUNDLE_SPLIT_IDENTITY_HASH,
    )
    runtime.recovered_prefix = SimpleNamespace(source_report_sha256="a" * 64)
    runtime.source_m0_plan = source_plan
    runtime.source_m0_trace_path = source_trace
    runtime.source_authority_binding_path = source_authority
    runtime.source_generation_session_receipt_path = source_session
    runtime.source_m0_attempt_path = source_attempt
    runtime.recovery_source_report = {
        "artifacts": {"m0_trace_sha256": module._sha256_file(source_trace)}
    }
    phase_run = SimpleNamespace(
        phase=launcher.M0_PHASE,
        output=launcher.GenerationPhaseOutput(
            phase=launcher.M0_PHASE,
            rows=tuple(responses),
        ),
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.bundle.manifest._resolve_study_commit",
        lambda *_args: ("1" * 40, []),
    )

    sealed = runtime.seal_recovered_direct_manifest("direct_m0", phase_run, {})
    verified = verify_bundle(Path(sealed["manifest"]))
    manifest = verified.manifest
    run_dir = Path(sealed["manifest"]).parent

    assert Path(sealed["manifest"]).name == f"{launcher.SOURCE_RUN_ID}.run-manifest.json"
    assert Path(manifest["outputs"]["path"]).name == f"{launcher.SOURCE_RUN_ID}.outputs.jsonl"
    assert Path(manifest["raw_trace"]["path"]).name == f"{launcher.SOURCE_RUN_ID}.trace.jsonl"
    assert Path(manifest["trace_manifest"]["path"]).name == (
        f"{launcher.SOURCE_RUN_ID}.trace-manifest.json"
    )
    assert Path(manifest["raw_trace"]["path"]).read_bytes() == source_trace.read_bytes()
    assert len(verified.outputs_rows) == 104
    assert verified.attempt_state == "ABORTED"
    assert manifest["plan"]["attempt_id"] == source_plan.attempt_id
    assert manifest["session_receipt"]["path"] == str(source_session.resolve())
    assert manifest["recovery_source"]["execution_plan"] == asdict(source_plan)
    assert manifest["recovery_source"]["attempt_state"] == "ABORTED"
    assert manifest["recovery_source"]["new_model_contacts"] == 0
    assert run_dir == runtime.mission_dir / "recovered-direct-m0"
