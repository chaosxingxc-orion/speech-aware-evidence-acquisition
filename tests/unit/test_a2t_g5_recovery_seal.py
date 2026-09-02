"""Tests for the no-contact external recovery seal for the G5 fixed16 flight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import protocol_hash
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_recovery_seal import (
    G5RecoverySealError,
    build_recovery_seal,
)


RUN_ID = "SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1"
ATTEMPT_ID = "attempt-test-g5"
IDS = ("tier1_direct:000001", "tier2_parametric:000002")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")


def _jsonl(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _trace_record(record_id: str, channel: str, payload: dict[str, object]) -> dict[str, object]:
    return {"record_id": record_id, "channel": channel, "payload": payload}


def _trace_manifest(records: list[dict[str, object]]) -> dict[str, object]:
    from speech_aware_evidence_acquisition.contracts import TraceRecord

    return {
        "run_id": RUN_ID,
        "records": {
            row["record_id"]: TraceRecord(
                channel=row["channel"], record_id=row["record_id"], payload=row["payload"]
            ).content_hash()
            for row in records
        },
    }


def _flight(tmp_path: Path) -> tuple[Path, Path]:
    mission = tmp_path / "flight"
    run_dir = mission / "g5"
    generic_hash = split_identity_hash(prefixed("audio2tool", IDS))
    prereg_hash = "8" * 64
    config_hash = "c" * 64
    plan = {
        "schema": "saea-execution-plan-v1", "study": "speech-aware-evidence-acquisition",
        "run_id": RUN_ID, "execution_profile": "bounded-discovery-probe",
        "carrier_lock_key": "audio2tool", "split_role": "discovery",
        "split_identity_hash": prereg_hash, "planned_model_calls": 4,
        "planned_gpu_hours": 1.0, "planned_speech_audio_seconds": 1,
        "protocol_hash": protocol_hash(config_hash, "speech-feature-query", prereg_hash),
        "attempt_id": ATTEMPT_ID,
    }
    _json(run_dir / "execution-plan.json", plan)
    _json(mission / "failure-receipt.json", {
        "run_id": RUN_ID, "attempt_id": ATTEMPT_ID,
        "error": f"BundleError('declared {prereg_hash[:12]}, recomputed {generic_hash[:12]}')",
    })
    output_rows = []
    output_trace = []
    agent_trace = []
    for index, sample_id in enumerate(IDS, start=1):
        text = f"[{{\"name\": \"tool-{index}\", \"arguments\": {{}}}}]"
        response_hash = hashlib.sha256(text.encode()).hexdigest()
        source_request = f"g5fixed16-{2 * index:04d}"
        agent_trace.extend([
            _trace_record(f"g5fixed16-{2 * index - 1:04d}/request", "MODEL_REQUEST", {"arm": "speech-feature-query", "payload": {}, "payload_sha256": "a" * 64}),
            _trace_record(f"g5fixed16-{2 * index - 1:04d}/response", "MODEL_RESPONSE", {"text": "{}", "response_sha256": "b" * 64, "response_text_sha256": hashlib.sha256(b"{}").hexdigest()}),
            _trace_record(f"g5fixed16-{2 * index:04d}/request", "MODEL_REQUEST", {"arm": "speech-feature-query", "payload": {}, "payload_sha256": "c" * 64}),
            _trace_record(f"{source_request}/response", "MODEL_RESPONSE", {"text": text, "response_sha256": "d" * 64, "response_text_sha256": response_hash}),
        ])
    agent_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    _jsonl(agent_path, agent_trace)
    agent_manifest = run_dir / "agent-trace" / f"{RUN_ID}.trace-manifest.json"
    _json(agent_manifest, _trace_manifest(agent_trace))
    for index, sample_id in enumerate(IDS, start=1):
        text = f"[{{\"name\": \"tool-{index}\", \"arguments\": {{}}}}]"
        response_hash = hashlib.sha256(text.encode()).hexdigest()
        request_id = f"factor-main-composite-{index:04d}"
        source = {"action": "g5-execute", "source_agent_trace_manifest_sha256": _sha256(agent_manifest), "source_artifact_sha256": _sha256(agent_path)}
        output_rows.append({"request_id": request_id, "sample_id": sample_id, "carrier_lock_key": "audio2tool", "arm": "speech-feature-query", "text": text, "admitted": True, "request_sha256": "e" * 64, "response_sha256": "f" * 64, "response_text_sha256": response_hash, "composite_source": source})
        output_trace.extend([
            _trace_record(f"{request_id}/request", "TOOL", {"payload_sha256": "e" * 64, "tool_id": "composite", "source": source}),
            _trace_record(f"{request_id}/response", "TOOL", {"text": text, "response_sha256": "f" * 64, "response_text_sha256": response_hash}),
        ])
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _jsonl(outputs, output_rows)
    trace = run_dir / f"{RUN_ID}.trace.jsonl"
    _jsonl(trace, output_trace)
    trace_manifest = run_dir / f"{RUN_ID}.trace-manifest.json"
    _json(trace_manifest, _trace_manifest(output_trace))
    _json(run_dir / "g5-plan-states.jsonl", {})
    plan_states = [{"sample_id": item, "contact_id": "g5-plan", "nonfinal": True} for item in IDS]
    _jsonl(run_dir / "g5-plan-states.jsonl", plan_states)
    _json(run_dir / "g5-plan-contact-manifest.json", {"run_id": RUN_ID, "row_count": 2, "contact_id": "g5-plan", "nonfinal": True, "rows_sha256": _sha256(run_dir / "g5-plan-states.jsonl")})
    manifest = {"schema": "saea-run-manifest-v1", "status": "COMPLETED", "run_id": RUN_ID, "arm": "speech-feature-query", "config": {"config_hash": config_hash}, "plan": plan, "protocol_hash": plan["protocol_hash"], "split": {"carrier_lock_key": "audio2tool", "identity_hash": prereg_hash, "ids": list(IDS), "count": 2}, "outputs": {"path": str(outputs), "sha256": _sha256(outputs)}, "raw_trace": {"path": str(trace), "sha256": _sha256(trace)}, "trace_manifest": {"path": str(trace_manifest), "sha256": _sha256(trace_manifest)}}
    _json(run_dir / f"{RUN_ID}.run-manifest.json", manifest)
    attempts = tmp_path / "attempts"
    _json(attempts / RUN_ID / f"{ATTEMPT_ID}.json", {"schema": "saea-attempt-v1", "run_id": RUN_ID, "attempt_id": ATTEMPT_ID, "state": "ABORTED", "actual": {"calls": 4, "audio_seconds": 1.0}, "reserved": {"calls": 4, "audio_seconds": 1.0}})
    return mission, attempts


def test_recovery_seal_preserves_the_invalid_candidate_and_records_its_limit(tmp_path):
    mission, attempts = _flight(tmp_path)
    candidate = mission / "g5" / f"{RUN_ID}.run-manifest.json"
    before = candidate.read_bytes()

    receipt = build_recovery_seal(mission, attempts_root=attempts)

    assert candidate.read_bytes() == before
    assert receipt["status"] == "EXTERNALLY_SEALED_UNVERIFIABLE"
    assert receipt["formal_verify_bundle"]["achievable"] is False
    assert "split_identity_hash_mismatch" in receipt["formal_verify_bundle"]["reasons"]
    assert receipt["attempt"]["state"] == "ABORTED"
    assert receipt["observed"]["model_contacts"] == 4
    assert receipt["prohibited_follow_up"] == ["model", "network", "retriever", "scorer", "tokenizer"]
    assert (mission / "g5-recovery-seal.json").is_file()


def test_recovery_seal_refuses_to_rewrite_an_existing_seal(tmp_path):
    mission, attempts = _flight(tmp_path)
    build_recovery_seal(mission, attempts_root=attempts)

    with pytest.raises(G5RecoverySealError, match="already exists"):
        build_recovery_seal(mission, attempts_root=attempts)
