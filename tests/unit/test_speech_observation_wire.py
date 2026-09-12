"""Prove cached speech OBS crosses the complete shared wire path."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.attempts import AttemptStore
from speech_aware_evidence_acquisition.core.flight import runtime as flight_runtime
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes, digest
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
from speech_aware_evidence_acquisition.rails.phase_runner import run_program
from speech_aware_evidence_acquisition.rails.speech_observation import (
    PREPARED_SPEECH_OBSERVATION_TOOL,
)
from test_flight_runtime import _git_init_commit, _make_runtime, _write_configs
from test_phase_speech_observation import config as observation_tool_config
from test_rails_frozen_core_client import (
    _World,
    _binding as payload_binding,
    _speech_feature_world,
)
from test_rails_runner import _FakeAdapter
from test_speech_observation import _artifact_inputs, _write_pinned
from test_rails_runner import _knowledge_snapshot


RUN_ID = "SAEA-SYNTHETIC-SPEECH-OBS-WIRE-V1"
ATTEMPT_ID = "attempt-synthetic-speech-obs-wire-v1"
PREP_RUN_ID = "SAEA-SYNTHETIC-SPEECH-OBS-PREP-V1"
PREP_ATTEMPT_ID = "attempt-synthetic-speech-obs-prep-v1"
TRANSCRIPT = "Cached ASR heard fifteen minutes."
SOLVER_RESPONSE = "Final answer produced by the Solver."


def _write_exposure_ledger(repo_root: Path, split_sha256: str) -> str:
    columns = (
        "run/experiment id",
        "speech carrier + split",
        "execution profile",
        "split role",
        "split identity hash",
        "consumed",
        "calls",
        "speech audio seconds",
        "gpu hours",
    )
    rows = (
        (
            PREP_RUN_ID,
            "fake-carrier, discovery",
            "bounded-discovery-probe",
            "discovery",
            split_sha256,
            "yes",
            "1",
            "2",
            "0.1",
        ),
        (
            RUN_ID,
            "fake-carrier, discovery",
            "bounded-discovery-probe",
            "discovery",
            split_sha256,
            "no",
            "10",
            "100",
            "1.0",
        ),
    )
    lines = (
        "| " + " | ".join(columns) + " |",
        "|" + "|".join("---" for _ in columns) + "|",
        *("| " + " | ".join(row) + " |" for row in rows),
    )
    return _write_pinned(repo_root, "docs/exposure-ledger.md", "\n".join(lines) + "\n")


def _prepare_catalog(
    *,
    repo_root: Path,
    data_root: Path,
    sample,
    packet: dict[str, str],
    split_sha256: str,
) -> dict[str, object]:
    checkpoint_sha256 = _write_pinned(
        repo_root, "receipts/synthetic-asr-checkpoint.json", "synthetic checkpoint"
    )
    plan = {
        "execution_plan": {
            "run_id": PREP_RUN_ID,
            "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "fake-carrier",
            "split_role": "discovery",
            "split_identity_hash": split_sha256,
            "planned_model_calls": 1,
            "planned_gpu_hours": 0.1,
            "planned_speech_audio_seconds": 2,
            "protocol_hash": "a" * 64,
            "attempt_id": PREP_ATTEMPT_ID,
        }
    }
    plan_sha256 = _write_pinned(
        repo_root, "plans/synthetic-speech-observation.json", json.dumps(plan)
    )
    ledger_sha256 = _write_exposure_ledger(repo_root, split_sha256)
    row = {
        "sample_id": sample.sample_id,
        "speech_packet_id": packet["packet_id"],
        "speech_packet_sha256": packet["sha256"],
        "source_audio_relpath": sample.audio_ref.path,
        "source_audio_sha256": sample.audio_ref.sha256,
        "source_audio_duration_seconds": sample.audio_seconds,
        "span": {
            "kind": "full-utterance",
            "start_seconds": 0.0,
            "end_seconds": sample.audio_seconds,
        },
        "artifact_relpath": "prepared/speech-observation/sample-1.json",
        "artifact_sha256": "pending",
        "output_sha256": "pending",
    }
    catalog = {
        "schema": "saea-prepared-speech-observation-catalog-v1",
        "catalog_id": "synthetic-speech-observation-wire-v1",
        "use_split_identity_hash": split_sha256,
        "checkpoint_receipt": {
            "relpath": "receipts/synthetic-asr-checkpoint.json",
            "sha256": checkpoint_sha256,
        },
        "decoding_config_sha256": "d" * 64,
        "producer": {
            "run_id": PREP_RUN_ID,
            "attempt_id": PREP_ATTEMPT_ID,
            "execution_plan": {
                "relpath": "plans/synthetic-speech-observation.json",
                "sha256": plan_sha256,
            },
            "protocol_sha256": "a" * 64,
            "ledger_row": {
                "relpath": "docs/exposure-ledger.md",
                "sha256": ledger_sha256,
                "row_id": PREP_RUN_ID,
            },
            "contacts": {"calls": 1, "audio_seconds": sample.audio_seconds},
        },
        "observations": [row],
    }
    output = {
        "schema": "saea-prepared-speech-observation-v1",
        "status": "ok",
        "transcript": TRANSCRIPT,
        "diagnostics": {"language": "en"},
    }
    row["output_sha256"] = digest(output)
    artifact = {
        "schema": "saea-prepared-artifact-v1",
        "kind": "prepared-speech-observation-v1",
        "inputs": _artifact_inputs(row, catalog),
        "contact_class": "speech-tool",
        "output": output,
        "output_sha256": row["output_sha256"],
    }
    artifact_path = data_root / row["artifact_relpath"]
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_bytes(canonical_bytes(artifact))
    row["artifact_sha256"] = hashlib.sha256(artifact_path.read_bytes()).hexdigest()

    catalog_relpath = "prepared/speech-observation/catalog.json"
    catalog_path = data_root / catalog_relpath
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_bytes(canonical_bytes(catalog))
    catalog_sha256 = hashlib.sha256(catalog_path.read_bytes()).hexdigest()
    attempt = AttemptStore(data_root / "attempts").open_attempt(
        PREP_RUN_ID,
        PREP_ATTEMPT_ID,
        carrier_lock_key="fake-carrier",
        reserved_calls=1,
        reserved_audio_seconds=sample.audio_seconds,
    )
    attempt.record_usage(calls=1, audio_seconds=sample.audio_seconds)
    attempt.finalize_with_receipt(
        catalog_relpath, catalog_sha256, "speech-observation-catalog"
    )
    return {
        "prepared_speech_observations": {
            "relpath": catalog_relpath,
            "sha256": catalog_sha256,
        }
    }


def _wire_runtime(tmp_path: Path, observation_config: str):
    world = _World(tmp_path)
    world.samples = [world.samples[0]]
    sample = world.samples[0]
    feature_root, _packet, packets = _speech_feature_world(world, tmp_path)
    split_sha256 = split_identity_hash(prefixed("fake-carrier", (sample.sample_id,)))
    repo_root = tmp_path / "repo"
    data_root = tmp_path / "data"

    baseline = {
        "phase_material": {
            phase: {
                "instruction_template": f"probes/{phase}.txt",
                "predecessor_binding": "none",
            }
            for phase in ("draft", "revise")
        }
    }
    if observation_config == "enabled":
        baseline.update(
            _prepare_catalog(
                repo_root=repo_root,
                data_root=data_root,
                sample=sample,
                packet=packets[sample.sample_id],
                split_sha256=split_sha256,
            )
        )
        baseline.update(observation_tool_config())
    else:
        _write_exposure_ledger(repo_root, split_sha256)
        if observation_config == "null":
            baseline["prepared_speech_observations"] = None

    _write_configs(
        repo_root,
        arm="speech-feature-query",
        policy="phase-draft-revise-v1",
        carrier_lock_key="fake-carrier",
        model_extra={"speech_feature_root": str(feature_root)},
        baseline_extra=baseline,
    )
    (repo_root / "configs/dataset/d.json").write_text(
        json.dumps({"carrier_lock_key": "fake-carrier", "split_id": "all"}),
        encoding="utf-8",
    )
    for phase in ("draft", "revise"):
        prompt = repo_root / f"configs/probes/{phase}.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(f"Solve the task during {phase}.", encoding="utf-8")
    _git_init_commit(repo_root)

    runtime = _make_runtime(
        tmp_path,
        run_id=RUN_ID,
        attempt_id=ATTEMPT_ID,
        happy_path=True,
        repo_root=repo_root,
        adapter_cls=lambda _lock, _root: _FakeAdapter(samples=tuple(world.samples)),
        client_factory=FrozenCoreClient,
        phase_runner=run_program,
        payload_binding_factory=lambda **_kwargs: payload_binding(world),
    )
    runtime._load_knowledge_snapshot = _knowledge_snapshot
    runtime.speech_packet_bindings = lambda: packets
    runtime._speech_feature_root = lambda: feature_root
    return runtime, packets[sample.sample_id]


def _run_wire(runtime):
    payloads = []
    final_responses = []
    rows_from_summaries = runtime._rows_from_phase_summaries

    def capture_final_responses(summaries, *, policy):
        final_responses.extend(
            result.final_response_text
            for summary in summaries
            for result in summary.results
        )
        return rows_from_summaries(summaries, policy=policy)

    runtime._rows_from_phase_summaries = capture_final_responses
    receipt = runtime.wire_check(
        seal_and_score=False,
        response_text=SOLVER_RESPONSE,
        request_payload_observer=payloads.append,
    )
    return receipt, payloads, final_responses


def test_cached_asr_crosses_real_next_solver_request_and_opt_out_is_byte_stable(
    tmp_path, monkeypatch
):
    enabled, packet = _wire_runtime(tmp_path / "enabled", "enabled")
    receipt, payloads, final_responses = _run_wire(enabled)

    serialized = [json.dumps(payload, sort_keys=True) for payload in payloads]
    successor = [payload for payload in serialized if TRANSCRIPT in payload]
    assert receipt["model_contacts"] == 0
    assert receipt["seal_and_score"]["status"] == "SKIPPED"
    assert receipt["dispatch"]["dispatch"] == "phase-program-continuous"
    observation_receipt = receipt["dispatch"]["phase_tools"]["speech_observations"]
    assert {
        key: observation_receipt[key]
        for key in (
            "catalog_id",
            "prepared_count",
            "producer_contacts",
            "new_neural_contacts",
            "supplied_samples",
        )
    } == {
        "catalog_id": "synthetic-speech-observation-wire-v1",
        "prepared_count": 1,
        "producer_contacts": {"calls": 1, "audio_seconds": 2.0},
        "new_neural_contacts": 0,
        "supplied_samples": 1,
    }
    assert receipt["typed_knowledge_blocks_total"] == 0
    assert receipt["typed_speech_observation_blocks_total"] == 1
    assert len(payloads) == receipt["contact_count"] == 2
    assert len(successor) == 1
    assert successor[0].count(TRANSCRIPT) == 1
    assert packet["packet_id"] in successor[0]
    assert "speech_feature_parts" in successor[0]
    assert PREPARED_SPEECH_OBSERVATION_TOOL in successor[0]
    assert final_responses == [SOLVER_RESPONSE]

    historical_messages = []
    for name in ("absent", "null"):
        runtime, historical_packet = _wire_runtime(tmp_path / name, name)
        old_receipt, old_payloads, old_finals = _run_wire(runtime)
        old_serialized = json.dumps(old_payloads, sort_keys=True)
        assert old_receipt["dispatch"]["dispatch"] == "phase-program"
        assert "phase_tools" not in old_receipt["dispatch"]
        assert TRANSCRIPT not in old_serialized
        assert PREPARED_SPEECH_OBSERVATION_TOOL not in old_serialized
        assert historical_packet["packet_id"] in old_serialized
        assert old_finals == [SOLVER_RESPONSE, SOLVER_RESPONSE]
        historical_messages.append(
            [
                {
                    key: payload[key]
                    for key in (
                        "history",
                        "task_instruction",
                        "supplied_evidence",
                        "speech_packet_sha256",
                    )
                }
                for payload in old_payloads
            ]
        )
    assert historical_messages[0] == historical_messages[1]

    original_transport = flight_runtime.WireCheckTransport

    class TamperingTransport(original_transport):
        def __call__(self, request_bytes):
            response = super().__call__(request_bytes)
            for item in self.payloads[-1].get("supplied_evidence") or []:
                if str(item.get("source_uri") or "").startswith(
                    "prepared-speech-observation://"
                ):
                    item["content"] = "Tampered cached ASR."
            return response

    with monkeypatch.context() as patch:
        patch.setattr(flight_runtime, "WireCheckTransport", TamperingTransport)
        tampered, _ = _wire_runtime(tmp_path / "tampered", "enabled")
        with pytest.raises(
            FlightRuntimeError,
            match="differs from the sample's source-bound speech observation",
        ):
            _run_wire(tampered)
