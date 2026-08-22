"""``rails.probes.pslu_flight``: the P-SLU six-arm, two-phase flight
orchestration (docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test drives a
``MockCoreClient``.
"""

from __future__ import annotations

import json
import hashlib
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRegistry
from speech_aware_evidence_acquisition.core.driver.speech_native import (
    audit_speech_native_action_support,
    _assert_reusable_session_profile,
    _canonical_sha256,
    _evaluate_training_free_contextual_policy,
    _evaluate_training_free_episodic_policy,
    _evaluate_training_free_grounded_semantic_policy,
    _build_audio_key_bindings,
    _evaluate_training_free_agent_policies,
    _evaluate_m9_factor_graph_action_support,
    _evaluate_m10_candidate_evidence_action_support,
    _evaluate_m11_adaptive_evidence_gap,
    _load_decision_graph,
    _parse_m9_factor_graph_trajectory,
    _parse_m10_candidate_evidence_trajectory,
    _parse_m11_adaptive_evidence_gap_trajectory,
    _profile_completion_issues,
    _release_speech_native_session,
    _scan_server_log,
    _trace_speech_query_summary,
    SpeechNativeProfileError,
    _cli_speech_native_action_audit,
    build_profile_tasks,
    profile_timing_metrics,
    read_speech_native_predictions,
)
from speech_aware_evidence_acquisition.core.driver import (
    cli as driver_cli_module,
    speech_native as speech_native_module,
)
from speech_aware_evidence_acquisition.contracts import STUDY_SLUG
from speech_aware_evidence_acquisition.core.session import (
    SESSION_RECEIPT_SCHEMA_V2,
    ModelFileRef,
    SessionError,
    SessionReceipt,
)
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.core.tracing import DispatchingSink, TraceSink
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.slurp import (
    SlurpTrainMaterial,
    SlurpTrainRecording,
)
from speech_aware_evidence_acquisition.rails import MockCoreClient
from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpAdapter
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (
    CandidateCounterevidenceStateV1,
    CandidateSupportStateV1,
    DecisionBoundaryV1,
    DecisionFactorV1,
    DecisionGraphV1,
    FactorLinkStateV1,
    KeyCardV1,
    PSLU_ARMS,
    PsluFlightError,
    PsluRosters,
    PsluSampleManifest,
    _source_references_ontology_miner,
    assert_never_calls_ontology_miner,
    build_data_derived_decision_graph,
    build_speech_native_binding,
    candidate_counterevidence_response_format,
    candidate_support_response_format,
    decision_boundary_path,
    expand_decision_graph_candidates,
    expand_decision_graph_neighborhood,
    extend_speech_native_binding,
    refine_speech_native_binding_knowledge,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    load_speech_native_engineering_gate,
    pslu_supply_packet,
    factor_link_response_format,
    parse_candidate_counterevidence_state,
    parse_candidate_support_state,
    parse_factor_link_state,
    render_decision_graph_neighborhood,
    render_factor_link_state,
    render_roster_entries,
    render_speech_native_keys,
    render_type_vocabulary,
    run_pslu_flight,
    select_pslu_samples,
    run_speech_native_matcher,
    SpeechNativeMatchTask,
    run_speech_native_match_tasks,
)
from speech_aware_evidence_acquisition.rails.probes import pslu_flight as pslu_module
from speech_aware_evidence_acquisition.rails.silence_swap import (
    build_silence_swap_slice,
)

_ROSTERS = PsluRosters(
    scenario_rosters={
        "iot": (("house_place", "kitchen"), ("device_type", "light")),
        "email": (("email_folder", "inbox"),),
    },
    global_types=("house_place", "device_type", "email_folder", "time"),
    full_roster=(("house_place", "kitchen"), ("time", "six")),
    derangement={"iot": "email", "email": "iot"},
)

_KEY_CARDS = (
    KeyCardV1(
        key_id="K001",
        definition="Commands that create, change, inspect, or remove alarms.",
        positive_examples=("wake me at six", "cancel my morning alarm"),
        contrastive_boundary="Do not use for calendar appointments.",
        value_label="alarm",
    ).validate(),
    KeyCardV1(
        key_id="K002",
        definition="Commands about email messages and mailboxes.",
        positive_examples=("read my new email", "send an email to Alex"),
        contrastive_boundary="Do not use for social messages.",
        value_label="email",
    ).validate(),
)


def _resident_inference_session(**overrides):
    values = {
        "schema": SESSION_RECEIPT_SCHEMA_V2,
        "study": STUDY_SLUG,
        "session_id": "speech-native-resident-service",
        "binary_path": "llama.cpp/build/bin/llama-server",
        "binary_sha256": "a" * 64,
        "argv": (
            "/runtime/llama.cpp/build/bin/llama-server",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
            "-m",
            "/models/decoder.gguf",
            "--no-mmproj",
            "-c",
            "65536",
            "-np",
            "16",
        ),
        "pid": 12345,
        "host": "127.0.0.1",
        "port": 8080,
        "model_files": (ModelFileRef(path="models/decoder.gguf", sha256="b" * 64),),
        "started_at": "2026-08-22T00:00:00+00:00",
        "startup_stdout_sha256": "c" * 64,
        "server_log_path": "/runs/services/speech-native/server.log",
        "role": "inference",
        "server_env_keys": (
            "LLAMA_SPEECH_DECODER_SHA256",
            "LLAMA_SPEECH_FEATURE_ROOT",
        ),
    }
    values.update(overrides)
    return SessionReceipt(**values).validate()


def test_reusable_session_profile_accepts_exact_argv_and_environment():
    session = _resident_inference_session()

    assert (
        _assert_reusable_session_profile(
            session,
            host="127.0.0.1",
            port=8080,
            model_argv=("-m", "/models/decoder.gguf", "--no-mmproj"),
            server_args=("-c", "65536", "-np", "16"),
            server_env={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/slurp",
            },
            live_environment={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/slurp",
            },
        )
        is session
    )


def test_reusable_session_profile_refuses_different_batch_geometry():
    session = _resident_inference_session()

    with pytest.raises(SessionError, match="launch argv"):
        _assert_reusable_session_profile(
            session,
            host="127.0.0.1",
            port=8080,
            model_argv=("-m", "/models/decoder.gguf", "--no-mmproj"),
            server_args=("-c", "65536", "-np", "10"),
            server_env={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/slurp",
            },
            live_environment={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/slurp",
            },
        )


def test_reusable_session_profile_refuses_different_feature_root():
    session = _resident_inference_session()

    with pytest.raises(SessionError, match="server environment"):
        _assert_reusable_session_profile(
            session,
            host="127.0.0.1",
            port=8080,
            model_argv=("-m", "/models/decoder.gguf", "--no-mmproj"),
            server_args=("-c", "65536", "-np", "16"),
            server_env={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/slurp",
            },
            live_environment={
                "LLAMA_SPEECH_DECODER_SHA256": "decoder-sha",
                "LLAMA_SPEECH_FEATURE_ROOT": "/features/other",
            },
        )


def test_attached_session_release_does_not_stop_resident_server(tmp_path):
    stopped = []

    result = _release_speech_native_session(
        _resident_inference_session(),
        owns_process=False,
        runtime_receipt={"runtime": "pinned"},
        runtime_root=tmp_path,
        receipt_path=tmp_path / "must-not-exist.json",
        stop=lambda *args, **kwargs: stopped.append((args, kwargs)),
    )

    assert result is None
    assert stopped == []
    assert not (tmp_path / "must-not-exist.json").exists()


def test_owned_session_release_stops_exact_process(tmp_path):
    stopped = []

    result = _release_speech_native_session(
        _resident_inference_session(),
        owns_process=True,
        runtime_receipt={"runtime": "pinned"},
        runtime_root=tmp_path,
        receipt_path=tmp_path / "stop.json",
        stop=lambda session, **kwargs: (
            stopped.append((session, kwargs)) or {"stopped": True}
        ),
    )

    assert result == {"stopped": True}
    assert stopped[0][0].session_id == "speech-native-resident-service"
    assert stopped[0][1]["force_after_timeout"] is True


def test_server_log_scan_is_scoped_to_current_attempt_window(tmp_path):
    log = tmp_path / "resident-server.log"
    old = "CUDA error out of memory\ndecoded mmproj-free speech feature chunk\n"
    current = (
        "decoded mmproj-free speech feature chunk\n"
        "decoded mmproj-free speech feature chunk\n"
    )
    log.write_text(old + current, encoding="utf-8")

    scan = _scan_server_log(log, start_offset=len(old.encode("utf-8")))

    assert scan["oom_marker_hits"] == []
    assert scan["mmproj_free_chunk_count"] == 2


def test_trace_speech_query_summary_accepts_exact_query_with_audio_key(tmp_path):
    trace = tmp_path / "trace.jsonl"
    expected_query = {
        "packet_id": "slurp/train/query",
        "sha256": "a" * 64,
        "role": "query",
    }
    rows = (
        {
            "channel": "MODEL_REQUEST",
            "payload": {
                "payload": {
                    "sample_id": "slurp:train:query",
                    "query_source": "speech_features",
                    "mmproj_loaded": False,
                    "speech_packet_sha256": "a" * 64,
                    "speech_feature_parts": [
                        expected_query,
                        {
                            "packet_id": "slurp/train/key",
                            "sha256": "b" * 64,
                            "role": "key",
                        },
                    ],
                }
            },
        },
        {"channel": "MODEL_RESPONSE", "payload": {}},
    )
    trace.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    summary = _trace_speech_query_summary(
        trace,
        expected_queries={"slurp:train:query": expected_query},
    )

    assert summary == {
        "model_request_count": 1,
        "valid_speech_query_count": 1,
        "invalid_speech_query_count": 0,
        "unknown_sample_id_count": 0,
        "query_source_failure_count": 0,
        "mmproj_flag_failure_count": 0,
        "packet_binding_failure_count": 0,
    }


def test_trace_speech_query_summary_rejects_wrong_packet_binding(tmp_path):
    trace = tmp_path / "trace.jsonl"
    expected_query = {
        "packet_id": "slurp/train/query",
        "sha256": "a" * 64,
        "role": "query",
    }
    trace.write_text(
        json.dumps(
            {
                "channel": "MODEL_REQUEST",
                "payload": {
                    "payload": {
                        "sample_id": "slurp:train:query",
                        "query_source": "speech_features",
                        "mmproj_loaded": False,
                        "speech_packet_sha256": "b" * 64,
                        "speech_feature_parts": [
                            {**expected_query, "sha256": "b" * 64}
                        ],
                    }
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    summary = _trace_speech_query_summary(
        trace,
        expected_queries={"slurp:train:query": expected_query},
    )

    assert summary["valid_speech_query_count"] == 0
    assert summary["invalid_speech_query_count"] == 1
    assert summary["packet_binding_failure_count"] == 1


def test_profile_completion_uses_trace_carriage_not_auxiliary_log_count():
    issues = _profile_completion_issues(
        calls_used=2,
        actual_contact_count=2,
        task_count=1,
        planned_contact_ceiling=2,
        request_failure_count=0,
        server_scan={
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 1,
        },
        trace_usage={
            "model_request_count": 2,
            "model_response_count": 2,
            "cost_record_count": 2,
        },
        trace_speech_query={
            "model_request_count": 2,
            "valid_speech_query_count": 2,
            "invalid_speech_query_count": 0,
        },
    )

    assert issues == ()


def test_profile_completion_rejects_missing_trace_speech_query():
    issues = _profile_completion_issues(
        calls_used=2,
        actual_contact_count=2,
        task_count=1,
        planned_contact_ceiling=2,
        request_failure_count=0,
        server_scan={
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 2,
        },
        trace_usage={
            "model_request_count": 2,
            "model_response_count": 2,
            "cost_record_count": 2,
        },
        trace_speech_query={
            "model_request_count": 2,
            "valid_speech_query_count": 1,
            "invalid_speech_query_count": 1,
        },
    )

    assert "trace speech-query carriage is incomplete" in issues


_M6_SUCCESS_ACTIONS = [
    "match:speech-only-primary",
    "retrieve:speech-only",
    "build:grounded-query-state",
    "retrieve:speech-plus-grounded-state",
    "verify:speech-plus-grounded-state",
    "select:refined-primary-fallback",
]


def _m6_action_audit_row(index, *, primary_key_id, refined_key_id):
    sample_id = f"slurp:train:audit-{index}"
    packet_sha256 = f"{index + 1:064x}"
    initial_ids = [primary_key_id, "K003", "K004"]
    refined_ids = [refined_key_id, "K003", "K004"]
    calls = 8 if index == 1 else 7
    scores = {
        key_id: {"compatible": key_id == refined_key_id, "confidence": 90}
        for key_id in refined_ids
    }
    return {
        "schema": "saea-speech-native-decision-v1",
        "task_id": f"canonical:{sample_id}",
        "sample_id": sample_id,
        "query_sample_id": sample_id,
        "mechanism_control_id": "matched",
        "speech_packet_sha256": packet_sha256,
        "key_representation_id": "K1",
        "matcher_policy_id": "M6",
        "key_id": refined_key_id,
        "predicted_value_label": "must-not-enter-audit-output",
        "top_key_ids": refined_ids,
        "calls": calls,
        "parse_failure": False,
        "agent_policy_id": "knowledge-grounded-semantic-refinement-schema-v2",
        "agent_actions": _M6_SUCCESS_ACTIONS,
        "agent_escalated": True,
        "agent_vote_key_ids": [primary_key_id, refined_key_id],
        "agent_steps": [
            {
                "action_id": "match:speech-only-primary",
                "key_id": primary_key_id,
                "top_key_ids": [primary_key_id],
                "calls": 1,
                "parse_failure": False,
            },
            {
                "action_id": "retrieve:speech-only",
                "key_id": initial_ids[0],
                "top_key_ids": initial_ids,
                "calls": 1,
                "parse_failure": False,
            },
            {
                "action_id": "build:grounded-query-state",
                "key_id": None,
                "top_key_ids": initial_ids,
                "calls": 1,
                "parse_failure": False,
                "grounded_query_state": {
                    "candidate_key_ids": initial_ids,
                    "domain": "home",
                    "operation": "control",
                    "target": "device",
                    "constraints": [],
                    "exclusions": [],
                    "unresolved_ambiguity": "none",
                    "evidence": [],
                },
            },
            {
                "action_id": "retrieve-and-verify:speech-plus-grounded-state",
                "key_id": refined_key_id,
                "top_key_ids": refined_ids,
                "calls": 4,
                "parse_failure": False,
                "verifier_scores": scores,
            },
        ],
        "agent_aggregator_id": "grounded-refined-primary-fallback-v1",
        "verifier_scores": scores,
        "response_text_sha256": [
            f"{index + 10 + offset:064x}" for offset in range(calls)
        ],
    }


def _write_m6_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "attempt"
    attempt_dir.mkdir()
    rows = (
        _m6_action_audit_row(0, primary_key_id="K001", refined_key_id="K002"),
        _m6_action_audit_row(1, primary_key_id="K002", refined_key_id="K002"),
    )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['sample_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    trace = attempt_dir / "SAEA-SN-AUDIT.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows), encoding="utf-8"
    )
    process_audit = attempt_dir / "SAEA-SN-AUDIT.mmproj-audit.json"
    process_audit.write_text(
        json.dumps(
            {
                "schema": "saea-inference-process-audit-v1",
                "role": "inference",
                "pid": 123,
                "mmproj_loaded": False,
                "mmproj_hit_count": 0,
                "mmproj_hits": [],
            }
        ),
        encoding="utf-8",
    )
    receipt = {
        "schema": "saea-speech-native-profile-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "COMPLETED",
        "run_id": "SAEA-SN-AUDIT",
        "attempt_id": "attempt-audit-001",
        "request_failures": [],
        "profile": {
            "matcher_policy_id": "M6",
            "agent_policy_id": "knowledge-grounded-semantic-refinement-schema-v2",
            "agent_aggregator_id": "grounded-refined-primary-fallback-v1",
            "mechanism_control_id": "matched",
            "task_count": 2,
            "actual_contact_count": 15,
            "planned_contact_ceiling": 16,
            "top_k": 3,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": 2,
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 14,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": 15}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "schema": "saea-attempt-v1",
                "run_id": "SAEA-SN-AUDIT",
                "attempt_id": "attempt-audit-001",
                "state": "ABORTED",
                "failure_reason": "speech-native profile completion checks failed",
                "actual": {"calls": 15, "audio_seconds": 1.0, "gpu_seconds": 2.0},
                "reserved": {"calls": 16, "audio_seconds": 2.0},
                "carrier_lock_key": "slurp",
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_is_structural_only_and_counts_policy_changes(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m6_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    assert report["source_attempt_state"] == "ABORTED"
    assert report["effectiveness_eligible"] is False
    assert report["gold_read"] is False
    assert report["decision_count"] == 2
    assert report["valid_speech_query_contact_count"] == 15
    assert report["grounded_state_valid_count"] == 2
    assert report["action_sensitive_count"] == 1
    assert report["initial_to_refined_top1_change_count"] == 1
    assert report["calls_distribution"] == {"7": 1, "8": 1}
    serialized = json.dumps(report, sort_keys=True)
    assert "must-not-enter-audit-output" not in serialized
    assert "correct" not in serialized


def test_action_support_audit_rejects_nonmatching_trace_packet(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m6_action_audit_fixture(tmp_path)
    )
    text = trace.read_text(encoding="utf-8")
    trace.write_text(text.replace(f"{1:064x}", f"{99:064x}", 1), encoding="utf-8")
    with pytest.raises(Exception, match="speech-query carriage"):
        audit_speech_native_action_support(
            attempt_dir=attempt_dir,
            attempt_record_path=attempt_record,
            attempt_record_sha256=hashlib.sha256(
                attempt_record.read_bytes()
            ).hexdigest(),
            flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
            decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
            trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
        )


def _write_m7_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "m7-attempt"
    attempt_dir.mkdir()
    rows = []
    state_policy_ids = (
        "balanced-evidence-v1",
        "primary-challenge-v1",
        "retrieval-gap-v1",
    )
    for index in range(108):
        sample_id = f"slurp:train:{index:06d}:audio-{index}"
        packet_sha256 = f"{index + 1:064x}"
        primary_key = "K001"
        branch_key = "K002" if index == 0 else primary_key
        initial_top = ["K001", "K002", "K003"]
        scores = {
            key_id: {
                "compatible": key_id == branch_key,
                "confidence": 90.0 if key_id == branch_key else 10.0,
            }
            for key_id in initial_top
        }
        branches = [
            {
                "action_id": f"explore:{state_policy_id}",
                "state_policy_id": state_policy_id,
                "key_id": branch_key,
                "top_key_ids": initial_top,
                "calls": 5,
                "parse_failure": False,
                "grounded_query_state": {
                    "candidate_key_ids": initial_top,
                    "domain": "home",
                    "operation": "control",
                    "target": "device",
                    "constraints": [],
                    "exclusions": [],
                    "unresolved_ambiguity": "none",
                    "evidence": [
                        {
                            "key_id": key_id,
                            "field": "definition",
                            "quote": f"frozen definition for {key_id}",
                        }
                        for key_id in initial_top
                    ],
                },
                "verifier_scores": scores,
                "causal_parent_ids": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                ],
            }
            for state_policy_id in state_policy_ids
        ]
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": sample_id,
                "query_sample_id": sample_id,
                "speech_packet_sha256": packet_sha256,
                "mechanism_control_id": "matched",
                "key_representation_id": "K1",
                "matcher_policy_id": "M7",
                "key_id": primary_key,
                "predicted_value_label": "must-not-enter-audit-output",
                "top_key_ids": initial_top,
                "verifier_scores": {},
                "calls": 17,
                "parse_failure": False,
                "agent_policy_id": "knowledge-grounded-multistate-action-support-v1",
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    *[f"explore:{policy_id}" for policy_id in state_policy_ids],
                    "select:retain-primary-for-support",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": [
                    primary_key,
                    branch_key,
                    branch_key,
                    branch_key,
                ],
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": primary_key,
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": initial_top[0],
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                    },
                    *branches,
                ],
                "agent_aggregator_id": "action-support-primary-control-v1",
                "response_text_sha256": [
                    f"{10000 + index * 20 + offset:064x}" for offset in range(17)
                ],
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['sample_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    trace = attempt_dir / "SAEA-SN-M7-AUDIT.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows),
        encoding="utf-8",
    )
    process_audit = attempt_dir / "SAEA-SN-M7-AUDIT.mmproj-audit.json"
    process_audit.write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}),
        encoding="utf-8",
    )
    contact_count = 108 * 17
    receipt = {
        "status": "COMPLETED",
        "run_id": "SAEA-SN-M7-AUDIT",
        "attempt_id": "attempt-m7-audit-001",
        "request_failures": [],
        "profile": {
            "key_representation_id": "K1",
            "matcher_policy_id": "M7",
            "agent_policy_id": "knowledge-grounded-multistate-action-support-v1",
            "agent_aggregator_id": "action-support-primary-control-v1",
            "mechanism_control_id": "matched",
            "top_k": 3,
            "task_count": 108,
            "actual_contact_count": contact_count,
            "planned_contact_ceiling": 108 * 20,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": 108,
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 0,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": contact_count}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "m7-attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "attempt_id": receipt["attempt_id"],
                "state": "FINALIZED",
                "actual": {
                    "calls": contact_count,
                    "audio_seconds": 1.0,
                    "gpu_seconds": 2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_accepts_complete_m7_without_reading_gold(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m7_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    assert report["source_attempt_state"] == "FINALIZED"
    assert report["gold_read"] is False
    assert report["effectiveness_read_authorized"] is True
    assert report["decision_count"] == 108
    assert report["grounded_state_valid_count"] == 324
    assert report["refined_retrieval_count"] == 324
    assert report["verifier_score_count"] == 972
    assert report["valid_speech_query_contact_count"] == 1836
    assert report["action_sensitive_count"] == 1
    assert "must-not-enter-audit-output" not in json.dumps(report, sort_keys=True)


def _write_m8_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "m8-attempt"
    attempt_dir.mkdir()
    rows = []
    initial_top = ["K001", "K002", "K003"]
    challengers = initial_top[1:]
    for index in range(108):
        sample_id = f"slurp:train:{index:06d}:audio-{index}"
        packet_sha256 = f"{index + 1:064x}"
        comparison_steps = []
        support_votes = ["K001"]
        for rank, challenger_key in enumerate(challengers, start=1):
            k1_vote = "K001"
            k2_vote = challenger_key if index == 0 and rank == 1 else "K001"
            k1_stable = None
            k2_stable = challenger_key if index == 0 and rank == 1 else None
            support_votes.extend((k1_stable, k2_stable))
            comparison_steps.append(
                {
                    "action_id": f"compare:pairwise-boundary-rank-{rank}",
                    "rank": rank,
                    "primary_key_id": "K001",
                    "challenger_key_id": challenger_key,
                    "k1_ab_key_id": k1_vote,
                    "k1_ba_key_id": k1_vote,
                    "k1_stable_key_id": k1_stable,
                    "k2_ab_key_id": k2_vote,
                    "k2_ba_key_id": k2_vote,
                    "k2_stable_key_id": k2_stable,
                    "calls": 4,
                    "parse_failure": False,
                    "causal_parent_ids": [
                        "match:speech-only-primary",
                        "retrieve:speech-only",
                    ],
                }
            )
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": sample_id,
                "query_sample_id": sample_id,
                "speech_packet_sha256": packet_sha256,
                "mechanism_control_id": "matched",
                "key_representation_id": "K1",
                "matcher_policy_id": "M8",
                "key_id": "K001",
                "predicted_value_label": "must-not-enter-audit-output",
                "top_key_ids": initial_top,
                "verifier_scores": {},
                "calls": 10,
                "parse_failure": False,
                "agent_policy_id": "speech-conditioned-pairwise-boundary-support-v1",
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "compare:pairwise-boundary-rank-1",
                    "compare:pairwise-boundary-rank-2",
                    "select:retain-primary-for-support",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": support_votes,
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": "K001",
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": "K001",
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                    },
                    *comparison_steps,
                ],
                "agent_aggregator_id": "pairwise-boundary-primary-control-v1",
                "response_text_sha256": [
                    f"{30000 + index * 10 + offset:064x}" for offset in range(10)
                ],
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['sample_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    trace = attempt_dir / "SAEA-SN-M8-AUDIT.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows), encoding="utf-8"
    )
    process_audit = attempt_dir / "SAEA-SN-M8-AUDIT.mmproj-audit.json"
    process_audit.write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}),
        encoding="utf-8",
    )
    contact_count = 108 * 10
    receipt = {
        "status": "COMPLETED",
        "run_id": "SAEA-SN-M8-AUDIT",
        "attempt_id": "attempt-m8-audit-001",
        "request_failures": [],
        "profile": {
            "key_representation_id": "K1",
            "matcher_policy_id": "M8",
            "agent_policy_id": "speech-conditioned-pairwise-boundary-support-v1",
            "agent_aggregator_id": "pairwise-boundary-primary-control-v1",
            "mechanism_control_id": "matched",
            "top_k": 3,
            "task_count": 108,
            "actual_contact_count": contact_count,
            "planned_contact_ceiling": 108 * 14,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": 108,
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 0,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": contact_count}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "m8-attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "attempt_id": receipt["attempt_id"],
                "state": "FINALIZED",
                "actual": {
                    "calls": contact_count,
                    "audio_seconds": 1.0,
                    "gpu_seconds": 2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_accepts_complete_m8_without_reading_gold(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m8_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    assert report["source_attempt_state"] == "FINALIZED"
    assert report["gold_read"] is False
    assert report["effectiveness_read_authorized"] is True
    assert report["decision_count"] == 108
    assert report["pairwise_comparison_count"] == 216
    assert report["valid_speech_query_contact_count"] == 1080
    assert report["action_sensitive_count"] == 1
    assert report["k1_stable_non_primary_query_count"] == 0
    assert report["k2_stable_non_primary_query_count"] == 1
    assert report["action_support_threshold_met"] is False
    assert "must-not-enter-audit-output" not in json.dumps(report, sort_keys=True)


def _write_m9_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "m9-attempt"
    attempt_dir.mkdir()
    graph_path = REPO_ROOT / "configs/knowledge/slurp-scenario-factor-graph-v1.json"
    graph_sha256 = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    audit_cards = tuple(
        KeyCardV1(
            key_id=f"K{index:03d}",
            definition="Audit-only opaque key definition.",
            positive_examples=("Audit-only example.",),
            contrastive_boundary=None,
            value_label=f"audit-{index:03d}",
        ).validate()
        for index in range(1, 19)
    )
    graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )
    initial_top = ("K001", "K003", "K005", "K009")
    state = FactorLinkStateV1(factor_ids=("F009", "F011"), boundary_id="B001")
    expansion = expand_decision_graph_candidates(
        graph=graph,
        initial_key_ids=initial_top,
        state=state,
        cap=6,
    )
    reranked = ("K003", "K001", "K005")
    boundary_path = decision_boundary_path(
        graph=graph,
        source_key_id="K001",
        target_key_id="K003",
        max_edges=2,
    )
    assert boundary_path == ("B001",)
    rows = []
    for index in range(108):
        sample_id = f"slurp:train:{index:06d}:audio-{index}"
        packet_sha256 = f"{index + 1:064x}"
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": sample_id,
                "query_sample_id": sample_id,
                "speech_packet_sha256": packet_sha256,
                "mechanism_control_id": "matched",
                "key_representation_id": "K1",
                "matcher_policy_id": "M9",
                "key_id": "K001",
                "predicted_value_label": "must-not-enter-audit-output",
                "top_key_ids": list(reranked),
                "verifier_scores": {},
                "calls": 6,
                "parse_failure": False,
                "agent_policy_id": "speech-conditioned-factor-graph-action-support-v1",
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "link:knowledge-factors",
                    "tool:expand-factor-graph",
                    "rerank:speech-plus-factor-state",
                    "compare:boundary-ab",
                    "compare:boundary-ba",
                    "select:retain-primary-for-support",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": ["K001", "K003", "K003", "K003"],
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": "K001",
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": "K001",
                        "top_key_ids": list(initial_top),
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "link:knowledge-factors",
                        "key_id": None,
                        "top_key_ids": list(initial_top),
                        "calls": 1,
                        "parse_failure": False,
                        "factor_link_state": {
                            "factor_ids": list(state.factor_ids),
                            "boundary_id": state.boundary_id,
                        },
                    },
                    {
                        "action_id": "tool:expand-factor-graph",
                        "key_id": None,
                        "top_key_ids": list(initial_top),
                        "calls": 0,
                        "parse_failure": False,
                        "expanded_key_ids": list(expansion.key_ids),
                        "distance_by_key": dict(expansion.distance_by_key),
                    },
                    {
                        "action_id": "rerank:speech-plus-factor-state",
                        "key_id": "K003",
                        "top_key_ids": list(reranked),
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "compare:factor-boundary",
                        "key_id": None,
                        "top_key_ids": ["K001", "K003"],
                        "calls": 2,
                        "parse_failure": False,
                        "boundary_path_ids": list(boundary_path),
                        "ab_key_id": "K003",
                        "ba_key_id": "K003",
                        "causal_parent_ids": [
                            "link:knowledge-factors",
                            "tool:expand-factor-graph",
                            "rerank:speech-plus-factor-state",
                        ],
                    },
                ],
                "agent_aggregator_id": "factor-graph-primary-control-v1",
                "response_text_sha256": [
                    f"{40000 + index * 6 + offset:064x}" for offset in range(6)
                ],
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['sample_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    run_id = "SAEA-SN-M9-AUDIT"
    trace = attempt_dir / f"{run_id}.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows), encoding="utf-8"
    )
    process_audit = attempt_dir / f"{run_id}.mmproj-audit.json"
    process_audit.write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}),
        encoding="utf-8",
    )
    contact_count = 108 * 6
    receipt = {
        "status": "COMPLETED",
        "run_id": run_id,
        "attempt_id": "attempt-m9-audit-001",
        "request_failures": [],
        "profile": {
            "key_representation_id": "K1",
            "matcher_policy_id": "M9",
            "agent_policy_id": "speech-conditioned-factor-graph-action-support-v1",
            "agent_aggregator_id": "factor-graph-primary-control-v1",
            "mechanism_control_id": "matched",
            "top_k": 4,
            "task_count": 108,
            "actual_contact_count": contact_count,
            "planned_contact_ceiling": contact_count,
            "decision_graph_id": graph.graph_id,
            "decision_graph_path": graph_path.relative_to(REPO_ROOT).as_posix(),
            "decision_graph_file_sha256": graph_sha256,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": 108,
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 0,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": contact_count}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "m9-attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "attempt_id": receipt["attempt_id"],
                "state": "FINALIZED",
                "actual": {
                    "calls": contact_count,
                    "audio_seconds": 1.0,
                    "gpu_seconds": 2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_accepts_complete_m9_without_reading_gold(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m9_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    assert report["schema"] == "saea-speech-native-factor-graph-action-audit-v1"
    assert report["source_attempt_state"] == "FINALIZED"
    assert report["gold_read"] is False
    assert report["effectiveness_read_authorized"] is True
    assert report["decision_count"] == 108
    assert report["contact_count"] == 648
    assert report["valid_speech_query_contact_count"] == 648
    assert report["factor_rerank_non_primary_query_count"] == 108
    assert report["boundary_stable_non_primary_query_count"] == 108
    assert report["action_variable_query_count"] == 108
    assert report["mechanism_failure_count"] == 0
    assert (
        report["decision_graph_file_sha256"]
        == hashlib.sha256(
            (
                REPO_ROOT / "configs/knowledge/slurp-scenario-factor-graph-v1.json"
            ).read_bytes()
        ).hexdigest()
    )
    assert "must-not-enter-audit-output" not in json.dumps(report, sort_keys=True)


def _write_m10_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "m10-attempt"
    attempt_dir.mkdir()
    graph_path = REPO_ROOT / "configs/knowledge/slurp-scenario-factor-graph-v1.json"
    graph_sha256 = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    audit_cards = tuple(
        KeyCardV1(
            key_id=f"K{index:03d}",
            definition="Audit-only opaque key definition.",
            positive_examples=("Audit-only example.",),
            contrastive_boundary=None,
            value_label=f"audit-{index:03d}",
        ).validate()
        for index in range(1, 19)
    )
    graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )

    class AuditM10Client:
        def complete(self, messages, **kwargs):
            del messages
            stage = kwargs["matcher_policy_id"]
            if stage.endswith(":primary-listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":speech-retrieve-top-4"):
                return '{"key_ids":["K001","K003","K005","K009"]}'
            if ":support-" in stage:
                factor_ids = kwargs["decoding_params"]["response_format"][
                    "json_schema"
                ]["schema"]["properties"]["factor_ids"]["items"]["enum"]
                return json.dumps(
                    {
                        "compatible": True,
                        "confidence": 90,
                        "factor_ids": factor_ids[:1],
                    }
                )
            if ":counterevidence-" in stage:
                return json.dumps(
                    {
                        "contradicted": False,
                        "confidence": 80,
                        "boundary_ids": [],
                    }
                )
            if ":reconcile-" in stage:
                return '{"action":"accept_candidate"}'
            raise AssertionError(stage)

    result = run_speech_native_matcher(
        core_client=AuditM10Client(),
        sample=type("AuditSample", (), {"sample_id": "audit-sample"})(),
        query_descriptor={
            "packet_id": "slurp/train/audit-sample",
            "sha256": "1" * 64,
            "role": "query",
        },
        key_cards=audit_cards,
        key_representation_id="K1",
        matcher_policy_id="M10",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-candidate-evidence-action-support-v1",
        agent_aggregator_id="candidate-evidence-primary-control-v1",
        decision_graph=graph,
        top_k=4,
    )
    rows = []
    for index in range(108):
        sample_id = f"slurp:train:{index:06d}:audio-{index}"
        packet_sha256 = f"{index + 1:064x}"
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": sample_id,
                "query_sample_id": sample_id,
                "speech_packet_sha256": packet_sha256,
                "mechanism_control_id": "matched",
                "key_representation_id": "K1",
                "matcher_policy_id": "M10",
                "key_id": result.key_id,
                "predicted_value_label": "must-not-enter-audit-output",
                "top_key_ids": list(result.top_key_ids),
                "verifier_scores": {},
                "calls": result.calls,
                "parse_failure": result.parse_failure,
                "agent_policy_id": result.agent_policy_id,
                "agent_actions": list(result.agent_actions),
                "agent_escalated": result.agent_escalated,
                "agent_vote_key_ids": list(result.agent_vote_key_ids),
                "agent_steps": list(result.agent_steps),
                "agent_aggregator_id": result.agent_aggregator_id,
                "response_text_sha256": [
                    f"{50000 + index * result.calls + offset:064x}"
                    for offset in range(result.calls)
                ],
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['sample_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    run_id = "SAEA-SN-M10-AUDIT"
    trace = attempt_dir / f"{run_id}.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows), encoding="utf-8"
    )
    process_audit = attempt_dir / f"{run_id}.mmproj-audit.json"
    process_audit.write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}),
        encoding="utf-8",
    )
    contact_count = 108 * result.calls
    receipt = {
        "status": "COMPLETED",
        "run_id": run_id,
        "attempt_id": "attempt-m10-audit-001",
        "request_failures": [],
        "profile": {
            "key_representation_id": "K1",
            "matcher_policy_id": "M10",
            "agent_policy_id": (
                "speech-conditioned-candidate-evidence-action-support-v1"
            ),
            "agent_aggregator_id": "candidate-evidence-primary-control-v1",
            "mechanism_control_id": "matched",
            "top_k": 4,
            "task_count": 108,
            "actual_contact_count": contact_count,
            "planned_contact_ceiling": 2160,
            "decision_graph_id": graph.graph_id,
            "decision_graph_path": graph_path.relative_to(REPO_ROOT).as_posix(),
            "decision_graph_file_sha256": graph_sha256,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": 108,
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 0,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": contact_count}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "m10-attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "attempt_id": receipt["attempt_id"],
                "state": "FINALIZED",
                "actual": {
                    "calls": contact_count,
                    "audio_seconds": 1.0,
                    "gpu_seconds": 2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_accepts_complete_m10_without_reading_gold(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m10_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )
    assert report["schema"] == "saea-speech-native-candidate-evidence-action-audit-v1"
    assert report["source_attempt_state"] == "FINALIZED"
    assert report["gold_read"] is False
    assert report["effectiveness_read_authorized"] is True
    assert report["decision_count"] == 108
    assert report["contact_count"] == 108 * 19
    assert report["valid_speech_query_contact_count"] == 108 * 19
    assert report["evidence_contact_count"] == 108 * 12
    assert report["reconciliation_contact_count"] == 108 * 5
    assert report["action_variable_query_count"] == 108
    assert report["mechanism_failure_count"] == 0
    assert "must-not-enter-audit-output" not in json.dumps(report, sort_keys=True)


def test_action_audit_cli_summarizes_m9_field_names(monkeypatch, tmp_path, capsys):
    report = {
        "schema": "saea-speech-native-factor-graph-action-audit-v1",
        "action_variable_query_count": 14,
        "action_variable_threshold_met": False,
        "gold_read": False,
        "effectiveness_read_authorized": True,
    }
    monkeypatch.setattr(
        speech_native_module,
        "audit_speech_native_action_support",
        lambda **kwargs: report,
    )
    output = tmp_path / "audit.json"
    result = _cli_speech_native_action_audit(
        SimpleNamespace(
            attempt_dir=str(tmp_path / "attempt"),
            attempt_record=str(tmp_path / "attempt.json"),
            attempt_record_sha256="a" * 64,
            flight_receipt_sha256="b" * 64,
            decisions_sha256="c" * 64,
            trace_sha256="d" * 64,
            output=str(output),
        )
    )
    summary = json.loads(capsys.readouterr().out)
    assert result == 0
    assert summary["action_sensitive_count"] == 14
    assert summary["action_support_threshold_met"] is False


def test_action_audit_cli_summarizes_m11_engineering_gate(
    monkeypatch, tmp_path, capsys
):
    report = {
        "schema": "saea-speech-native-adaptive-evidence-gap-audit-v1",
        "action_variable_query_count": 21,
        "engineering_gate_passed": True,
        "gold_read": False,
        "effectiveness_read_authorized": True,
    }
    monkeypatch.setattr(
        speech_native_module,
        "audit_speech_native_action_support",
        lambda **kwargs: report,
    )
    output = tmp_path / "audit.json"
    result = _cli_speech_native_action_audit(
        SimpleNamespace(
            attempt_dir=str(tmp_path / "attempt"),
            attempt_record=str(tmp_path / "attempt.json"),
            attempt_record_sha256="a" * 64,
            flight_receipt_sha256="b" * 64,
            decisions_sha256="c" * 64,
            trace_sha256="d" * 64,
            output=str(output),
        )
    )

    summary = json.loads(capsys.readouterr().out)
    assert result == 0
    assert summary["action_sensitive_count"] == 21
    assert summary["action_support_threshold_met"] is True
    assert summary["effectiveness_read_authorized"] is True


class _SpeechFeatureClient:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return next(self._responses)


class _SpeechSample:
    sample_id = "slurp:train:000001:audio-1"


_QUERY_DESCRIPTOR = {
    "packet_id": "slurp/train/query",
    "sha256": "a" * 64,
    "role": "query",
}


def _assert_every_call_carries_query(client):
    for messages, kwargs in client.calls:
        parts = messages[1]["content"]
        queries = [
            part["speech_features"]
            for part in parts
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert queries == [_QUERY_DESCRIPTOR]
        assert kwargs["speech_feature_sample_id"] == _SpeechSample.sample_id


def test_key_card_rendering_never_exposes_value_label_for_text_cards():
    rendered = render_speech_native_keys(_KEY_CARDS, "K2")
    assert "K001" in rendered and "wake me at six" in rendered
    assert "calendar appointments" in rendered
    assert "value_label" not in rendered
    assert '"alarm"' not in rendered


def _decision_graph_fixture() -> DecisionGraphV1:
    return DecisionGraphV1(
        graph_id="slurp-scenario-factor-graph-v1",
        factors=(
            DecisionFactorV1(
                factor_id="F001",
                kind="domain",
                statement="The request concerns time management.",
                key_ids=("K001",),
                provenance_ids=("key-card:K001:definition",),
            ),
            DecisionFactorV1(
                factor_id="F002",
                kind="operation",
                statement="The request creates or changes an alert.",
                key_ids=("K001",),
                provenance_ids=("key-card:K001:example:1",),
            ),
            DecisionFactorV1(
                factor_id="F003",
                kind="domain",
                statement="The request concerns written communication.",
                key_ids=("K002",),
                provenance_ids=("key-card:K002:definition",),
            ),
            DecisionFactorV1(
                factor_id="F004",
                kind="operation",
                statement="The request reads or sends a message.",
                key_ids=("K002",),
                provenance_ids=("key-card:K002:example:1",),
            ),
        ),
        boundaries=(
            DecisionBoundaryV1(
                boundary_id="B001",
                left_key_id="K001",
                right_key_id="K002",
                left_factor_ids=("F002",),
                right_factor_ids=("F004",),
                left_exclusion="Do not select this side for written messages.",
                right_exclusion="Do not select this side for timed alerts.",
                provenance_ids=(
                    "key-card:K001:contrastive-boundary",
                    "key-card:K002:contrastive-boundary",
                ),
            ),
        ),
    ).validate(_KEY_CARDS)


def test_decision_graph_validates_coverage_and_renders_one_hop_without_labels():
    graph = _decision_graph_fixture()

    neighborhood = graph.neighborhood(("K001",))
    assert neighborhood.key_ids == ("K001", "K002")
    assert neighborhood.factor_ids == ("F001", "F002", "F004")
    assert neighborhood.boundary_ids == ("B001",)

    rendered = render_decision_graph_neighborhood(
        graph=graph,
        key_cards=_KEY_CARDS,
        candidate_key_ids=("K001",),
    )
    assert "[F001]" in rendered
    assert "[F004]" in rendered
    assert "[B001] endpoints=K001,K002" in rendered
    assert "value_label" not in rendered
    assert '"alarm"' not in rendered
    assert '"email"' not in rendered


def test_decision_graph_rejects_unknown_key_and_wrong_boundary_factor_side():
    graph = _decision_graph_fixture()
    bad_factor = DecisionFactorV1(
        factor_id="F005",
        kind="target",
        statement="An unreachable target.",
        key_ids=("K999",),
        provenance_ids=("task-ontology:target",),
    )
    with pytest.raises(PsluFlightError, match="unknown key"):
        DecisionGraphV1(
            graph_id=graph.graph_id,
            factors=(*graph.factors, bad_factor),
            boundaries=graph.boundaries,
        ).validate(_KEY_CARDS)

    boundary = graph.boundaries[0]
    with pytest.raises(PsluFlightError, match="left factor"):
        DecisionGraphV1(
            graph_id=graph.graph_id,
            factors=graph.factors,
            boundaries=(
                DecisionBoundaryV1(
                    boundary_id=boundary.boundary_id,
                    left_key_id=boundary.left_key_id,
                    right_key_id=boundary.right_key_id,
                    left_factor_ids=("F004",),
                    right_factor_ids=boundary.right_factor_ids,
                    left_exclusion=boundary.left_exclusion,
                    right_exclusion=boundary.right_exclusion,
                    provenance_ids=boundary.provenance_ids,
                ),
            ),
        ).validate(_KEY_CARDS)


def test_factor_link_schema_and_parser_accept_only_neighborhood_ids():
    graph = _decision_graph_fixture()
    response_format = factor_link_response_format(
        graph=graph,
        key_cards=_KEY_CARDS,
        candidate_key_ids=("K001",),
    )
    schema = response_format["json_schema"]["schema"]
    assert schema["properties"]["factor_ids"]["items"]["enum"] == [
        "F001",
        "F002",
        "F004",
    ]
    assert schema["properties"]["boundary_id"]["enum"] == ["NONE", "B001"]

    state = parse_factor_link_state(
        '{"factor_ids":["F001","F002"],"boundary_id":"B001"}',
        graph=graph,
        key_cards=_KEY_CARDS,
        candidate_key_ids=("K001",),
    )
    assert state == FactorLinkStateV1(factor_ids=("F001", "F002"), boundary_id="B001")

    invalid_responses = (
        '{"factor_ids":["F001"],"boundary_id":"B001"}',
        '{"factor_ids":["F001","F001"],"boundary_id":"B001"}',
        '{"factor_ids":["F001","F999"],"boundary_id":"B001"}',
        '{"factor_ids":["F001","F002"],"boundary_id":"B999"}',
        '{"factor_ids":["F001","F002"],"boundary_id":"NONE","summary":"x"}',
    )
    for response in invalid_responses:
        assert (
            parse_factor_link_state(
                response,
                graph=graph,
                key_cards=_KEY_CARDS,
                candidate_key_ids=("K001",),
            )
            is None
        )


def test_candidate_evidence_expansion_and_dynamic_ids_are_graph_bound():
    graph = _decision_graph_fixture()
    expansion = expand_decision_graph_neighborhood(
        graph=graph,
        initial_key_ids=("K001",),
        cap=2,
    )
    assert expansion.key_ids == ("K001", "K002")
    assert expansion.distance_by_key == {"K001": 0, "K002": 1}

    support_format = candidate_support_response_format(
        graph=graph,
        candidate_key_id="K001",
    )
    support_enum = support_format["json_schema"]["schema"]["properties"]["factor_ids"][
        "items"
    ]["enum"]
    assert support_enum == ["F001", "F002"]
    assert parse_candidate_support_state(
        '{"compatible":true,"confidence":91,"factor_ids":["F001","F002"]}',
        graph=graph,
        candidate_key_id="K001",
    ) == CandidateSupportStateV1(
        compatible=True,
        confidence=91,
        factor_ids=("F001", "F002"),
    )
    assert (
        parse_candidate_support_state(
            '{"compatible":true,"confidence":91,"factor_ids":["F004"]}',
            graph=graph,
            candidate_key_id="K001",
        )
        is None
    )

    counter_format = candidate_counterevidence_response_format(
        graph=graph,
        candidate_key_id="K001",
    )
    boundary_enum = counter_format["json_schema"]["schema"]["properties"][
        "boundary_ids"
    ]["items"]["enum"]
    assert boundary_enum == ["B001"]
    assert parse_candidate_counterevidence_state(
        '{"contradicted":false,"confidence":86,"boundary_ids":["B001"]}',
        graph=graph,
        candidate_key_id="K001",
    ) == CandidateCounterevidenceStateV1(
        contradicted=False,
        confidence=86,
        boundary_ids=("B001",),
    )


def test_factor_graph_candidate_expansion_and_boundary_path_are_deterministic():
    graph = _decision_graph_fixture()
    state = FactorLinkStateV1(factor_ids=("F003", "F004"), boundary_id="B001")

    expanded = expand_decision_graph_candidates(
        graph=graph,
        initial_key_ids=("K001",),
        state=state,
        cap=2,
    )
    assert expanded.key_ids == ("K001", "K002")
    assert expanded.distance_by_key == {"K001": 0, "K002": 1}
    assert decision_boundary_path(
        graph=graph,
        source_key_id="K001",
        target_key_id="K002",
        max_edges=2,
    ) == ("B001",)

    rendered = render_factor_link_state(graph=graph, state=state)
    assert "[F003]" in rendered and "[F004]" in rendered
    assert "[B001] endpoints=K001,K002" in rendered
    assert "F001" not in rendered and "F002" not in rendered


class _M10CandidateEvidenceClient:
    def __init__(self):
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        stage = kwargs["matcher_policy_id"]
        if stage.endswith(":primary-listwise"):
            return '{"key_id":"K001"}'
        if stage.endswith(":speech-retrieve-top-2"):
            return '{"key_ids":["K001","K002"]}'
        if stage.endswith(":support-K001"):
            return '{"compatible":true,"confidence":93,"factor_ids":["F001","F002"]}'
        if stage.endswith(":support-K002"):
            return '{"compatible":true,"confidence":84,"factor_ids":["F003","F004"]}'
        if stage.endswith(":counterevidence-K001"):
            return '{"contradicted":false,"confidence":88,"boundary_ids":["B001"]}'
        if stage.endswith(":counterevidence-K002"):
            return '{"contradicted":false,"confidence":82,"boundary_ids":["B001"]}'
        if stage.endswith(":reconcile-K002"):
            return '{"action":"accept_candidate"}'
        raise AssertionError(stage)


def test_m10_candidate_evidence_loop_keeps_speech_and_primary_control():
    client = _M10CandidateEvidenceClient()
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M10",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-candidate-evidence-action-support-v1",
        agent_aggregator_id="candidate-evidence-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    assert result.key_id == "K001"
    assert result.top_key_ids == ("K001", "K002")
    assert result.calls == 7
    assert result.agent_vote_key_ids == ("K001", "K002")
    assert result.agent_actions[-1] == "select:retain-primary-for-support"
    evidence_steps = [
        step
        for step in result.agent_steps
        if str(step["action_id"]).startswith("acquire:candidate-evidence:")
    ]
    assert len(evidence_steps) == 2
    assert evidence_steps[1]["support_factor_ids"] == ["F003", "F004"]
    assert evidence_steps[1]["counterevidence_boundary_ids"] == ["B001"]
    reconcile = result.agent_steps[-1]
    assert reconcile["action_id"] == "reconcile:candidate:K002"
    assert reconcile["selected_action"] == "accept_candidate"
    assert reconcile["selected_factor_ids"] == ["F003", "F004"]
    _assert_every_call_carries_query(client)


def test_m10_reader_reconstructs_evidence_actions_and_oracle_support():
    result = run_speech_native_matcher(
        core_client=_M10CandidateEvidenceClient(),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M10",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-candidate-evidence-action-support-v1",
        agent_aggregator_id="candidate-evidence-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    row = {
        "key_id": result.key_id,
        "top_key_ids": list(result.top_key_ids),
        "calls": result.calls,
        "agent_policy_id": result.agent_policy_id,
        "agent_aggregator_id": result.agent_aggregator_id,
        "agent_escalated": result.agent_escalated,
        "agent_actions": list(result.agent_actions),
        "agent_vote_key_ids": list(result.agent_vote_key_ids),
        "agent_steps": list(result.agent_steps),
        "verifier_scores": {},
    }
    trajectory = _parse_m10_candidate_evidence_trajectory(
        row=row,
        sample_id="sample-m10",
        speaker_id="speaker-m10",
        gold_key_id="K002",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )
    assert trajectory["primary_key_id"] == "K001"
    assert trajectory["expanded_key_ids"] == ("K001", "K002")
    assert trajectory["supported_action_key_ids"] == ("K001", "K002")
    assert trajectory["dual_evidence_action_key_ids"] == ("K001", "K002")
    assert trajectory["reconciled_action_key_ids"] == ("K002",)
    assert trajectory["mechanism_failure"] is False

    metrics = _evaluate_m10_candidate_evidence_action_support((trajectory,))
    assert metrics["primary_correct"] == 0
    assert metrics["action_variable_query_count"] == 1
    assert metrics["oracle_correct"] == 1
    assert metrics["oracle_gain_vs_primary"] == 1
    assert metrics["action_families"]["reconciled"]["helpful_action_count"] == 1
    assert metrics["support_gate_passed"] is False


def test_m10_contact_dispatch_batches_candidate_evidence_across_tasks():
    class ConcurrentM10Client(_M10CandidateEvidenceClient):
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def complete(self, messages, **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                time.sleep(0.005)
                return super().complete(messages, **kwargs)
            finally:
                with self.lock:
                    self.active -= 1

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m10-{index}",
            sample=type("Sample", (), {"sample_id": f"m10-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m10-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M10",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            decision_graph=_decision_graph_fixture(),
            agent_policy_id=("speech-conditioned-candidate-evidence-action-support-v1"),
            agent_aggregator_id="candidate-evidence-primary-control-v1",
        )
        for index in range(4)
    )
    client = ConcurrentM10Client()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=8,
        dispatch_granularity="contact",
    )
    assert len(outcomes) == 4
    assert client.max_active == 2
    assert all(outcome.decision.calls == 7 for outcome in outcomes)
    assert all(outcome.decision.key_id == "K001" for outcome in outcomes)
    assert all(
        len(
            [
                part
                for part in messages[1]["content"]
                if part.get("type") == "input_speech_features"
                and part["speech_features"]["role"] == "query"
            ]
        )
        == 1
        for messages, _kwargs in client.calls
    )


def test_m0_schema_v4_constrains_the_final_label_at_llama_server_boundary():
    client = _SpeechFeatureClient(['{"label":"email"}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K0",
        matcher_policy_id="M0",
        prompt_policy_id="speech-native-json-copy-v4",
    )

    assert result.key_id == "K002"
    assert result.value_label == "email"
    response_format = client.calls[0][1]["decoding_params"]["response_format"]
    assert response_format == {
        "type": "json_schema",
        "json_schema": {
            "name": "direct_label_choice",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {"label": {"enum": ["alarm", "email"]}},
                "required": ["label"],
                "additionalProperties": False,
            },
        },
    }
    _assert_every_call_carries_query(client)


def test_m1_selects_an_opaque_key_id_and_maps_label_deterministically():
    client = _SpeechFeatureClient(['{"key_id":"K002"}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M1",
    )
    assert result.key_id == "K002"
    assert result.value_label == "email"
    assert result.calls == 1
    _assert_every_call_carries_query(client)


def test_m1_canonicalizes_safe_zero_padding_without_exposing_a_fake_key_example():
    client = _SpeechFeatureClient(['{"key_id":"K2"}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M1",
    )
    assert result.key_id == "K002"
    assert result.value_label == "email"
    system_text = client.calls[0][0][0]["content"]
    assert "K000" not in system_text
    assert "copied verbatim from a supplied key heading" in system_text


def test_m2_reintroduces_the_same_speech_query_for_factor_and_selection_steps():
    client = _SpeechFeatureClient(
        [
            '{"factors":["message medium"],"summary":"mail command"}',
            '{"key_id":"K002"}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M2",
    )
    assert result.value_label == "email"
    assert result.calls == 2
    _assert_every_call_carries_query(client)


def test_m6_refines_retrieval_with_a_knowledge_grounded_semantic_state():
    grounded_state = {
        "candidate_key_ids": ["K001", "K002"],
        "domain": "email",
        "operation": "read",
        "target": "message",
        "constraints": [],
        "exclusions": ["social messages"],
        "unresolved_ambiguity": "none",
        "evidence": [
            {
                "key_id": "K001",
                "field": "definition",
                "quote": "Commands that create, change, inspect, or remove alarms.",
            },
            {
                "key_id": "K002",
                "field": "contrastive_boundary",
                "quote": "Do not use for social messages.",
            },
        ],
    }
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            json.dumps(grounded_state),
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":20}',
        ]
    )

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M6",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        agent_policy_id="knowledge-grounded-semantic-refinement-full-action-v1",
        agent_aggregator_id="grounded-refined-primary-fallback-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    assert result.key_id == "K002"
    assert result.value_label == "email"
    assert result.top_key_ids == ("K002", "K001")
    assert result.calls == 6
    assert result.agent_vote_key_ids == ("K001", "K002")
    assert result.agent_actions == (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "build:grounded-query-state",
        "retrieve:speech-plus-grounded-state",
        "verify:speech-plus-grounded-state",
        "select:refined-primary-fallback",
    )
    refined_text = "\n".join(
        part["text"]
        for part in client.calls[3][0][1]["content"]
        if part.get("type") == "text"
    )
    assert '"operation":"read"' in refined_text
    assert "Keys:" in refined_text
    state_builder_text = "\n".join(
        part["text"]
        for part in client.calls[2][0][1]["content"]
        if part.get("type") == "text"
    )
    assert "Contrastive boundary: Do not use for social messages." in state_builder_text
    assert client.calls[2][1]["decoding_params"]["max_tokens"] == 512
    assert all(
        kwargs["decoding_params"]["max_tokens"] == 64
        for index, (_messages, kwargs) in enumerate(client.calls)
        if index != 2
    )
    _assert_every_call_carries_query(client)


def test_m6_fails_closed_to_speech_primary_when_grounding_quote_is_invented():
    invalid_state = {
        "candidate_key_ids": ["K001", "K002"],
        "domain": "email",
        "operation": "send",
        "target": "message",
        "constraints": [],
        "exclusions": [],
        "unresolved_ambiguity": "none",
        "evidence": [
            {
                "key_id": "K001",
                "field": "definition",
                "quote": "This text is absent from the key card.",
            },
            {
                "key_id": "K002",
                "field": "definition",
                "quote": "Commands about email messages and mailboxes.",
            },
        ],
    }
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            json.dumps(invalid_state),
        ]
    )

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M6",
        prompt_policy_id="speech-native-json-copy-v3",
        agent_policy_id="knowledge-grounded-semantic-refinement-full-action-v1",
        agent_aggregator_id="grounded-refined-primary-fallback-v1",
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 3
    assert result.parse_failure is False
    assert result.agent_vote_key_ids == ("K001", None)
    assert result.agent_actions[-1] == "backtrack:invalid-grounding"
    _assert_every_call_carries_query(client)


def test_m6_schema_v2_prompt_makes_the_grounded_state_contract_explicit():
    grounded_state = {
        "candidate_key_ids": ["K001", "K002"],
        "domain": "email",
        "operation": "read",
        "target": "message",
        "constraints": [],
        "exclusions": [],
        "unresolved_ambiguity": "none",
        "evidence": [
            {
                "key_id": "K001",
                "field": "definition",
                "quote": "Commands that create, change, inspect, or remove alarms.",
            },
            {
                "key_id": "K002",
                "field": "positive_examples",
                "quote": "read my new email",
            },
        ],
    }
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            json.dumps(grounded_state),
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":20}',
        ]
    )

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M6",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        agent_policy_id="knowledge-grounded-semantic-refinement-schema-v2",
        agent_aggregator_id="grounded-refined-primary-fallback-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    instruction = client.calls[2][0][0]["content"]
    assert result.agent_policy_id == "knowledge-grounded-semantic-refinement-schema-v2"
    assert 'candidate_key_ids must be exactly ["K001","K002"]' in instruction
    assert (
        "domain, operation, target, and unresolved_ambiguity must each be"
        in instruction
    )
    assert "a non-empty JSON string" in instruction
    assert "exactly one evidence object for each candidate" in instruction
    assert "definition, positive_examples, or contrastive_boundary" in instruction
    assert "never include the | separator" in instruction
    _assert_every_call_carries_query(client)


def test_m6_schema_v3_constrains_grounded_state_at_llama_server_boundary():
    grounded_state = {
        "candidate_key_ids": ["K001", "K002"],
        "domain": "email",
        "operation": "read",
        "target": "message",
        "constraints": [],
        "exclusions": [],
        "unresolved_ambiguity": "none",
        "evidence": [
            {
                "key_id": "K001",
                "field": "definition",
                "quote": "Commands that create, change, inspect, or remove alarms.",
            },
            {
                "key_id": "K002",
                "field": "positive_examples",
                "quote": "read my new email",
            },
        ],
    }
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            json.dumps(grounded_state),
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":20}',
        ]
    )

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M6",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        agent_policy_id="knowledge-grounded-semantic-refinement-schema-v3",
        agent_aggregator_id="grounded-refined-primary-fallback-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    assert result.agent_policy_id == "knowledge-grounded-semantic-refinement-schema-v3"
    state_params = client.calls[2][1]["decoding_params"]
    response_format = state_params["response_format"]
    assert response_format["type"] == "json_schema"
    schema = response_format["json_schema"]["schema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["candidate_key_ids"] == {
        "type": "array",
        "prefixItems": [{"const": "K001"}, {"const": "K002"}],
        "minItems": 2,
        "maxItems": 2,
    }
    evidence = schema["properties"]["evidence"]
    assert evidence["minItems"] == evidence["maxItems"] == 2
    first_alternatives = evidence["prefixItems"][0]["anyOf"]
    assert {
        alternative["properties"]["field"]["const"]
        for alternative in first_alternatives
    } == {"definition", "positive_examples", "contrastive_boundary"}
    assert all(
        alternative["properties"]["key_id"] == {"const": "K001"}
        for alternative in first_alternatives
    )
    positive = next(
        alternative
        for alternative in first_alternatives
        if alternative["properties"]["field"]["const"] == "positive_examples"
    )
    assert positive["properties"]["quote"] == {
        "enum": ["wake me at six", "cancel my morning alarm"]
    }
    assert all(
        "response_format" not in kwargs["decoding_params"]
        for index, (_messages, kwargs) in enumerate(client.calls)
        if index != 2
    )
    _assert_every_call_carries_query(client)


def _m7_grounded_state(state_policy_id):
    return {
        "candidate_key_ids": ["K001", "K002"],
        "domain": "email",
        "operation": state_policy_id,
        "target": "message",
        "constraints": [],
        "exclusions": ["social messages"],
        "unresolved_ambiguity": "alarm versus email operation",
        "evidence": [
            {
                "key_id": "K001",
                "field": "definition",
                "quote": "Commands that create, change, inspect, or remove alarms.",
            },
            {
                "key_id": "K002",
                "field": "contrastive_boundary",
                "quote": "Do not use for social messages.",
            },
        ],
    }


class _M7BatchClient:
    def __init__(self, *, invalid_state_policy_id=None):
        self.invalid_state_policy_id = invalid_state_policy_id
        self.calls = []
        self.batch_sizes = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        stage = kwargs["matcher_policy_id"]
        if stage.endswith(":primary-listwise"):
            return '{"key_id":"K001"}'
        if stage.endswith(":speech-retrieve-top-2"):
            return '{"key_ids":["K001","K002"]}'
        if ":state-" in stage:
            state_policy_id = stage.split(":state-", 1)[1]
            document = _m7_grounded_state(state_policy_id)
            if state_policy_id == self.invalid_state_policy_id:
                document["evidence"][0]["quote"] = "invented evidence"
            return json.dumps(document)
        if ":grounded-retrieve-" in stage:
            return (
                '{"key_ids":["K001","K002"]}'
                if "retrieval-gap-v1" in stage
                else '{"key_ids":["K002","K001"]}'
            )
        if ":grounded-verify-" in stage:
            key_id = stage.rsplit("-", 1)[-1]
            selects_primary = "retrieval-gap-v1" in stage
            compatible = key_id == ("K001" if selects_primary else "K002")
            confidence = 90 if compatible else 10
            return json.dumps({"compatible": compatible, "confidence": confidence})
        raise AssertionError(stage)

    def complete_many(self, requests, *, trace_parent=None):
        del trace_parent
        self.batch_sizes.append(len(requests))
        return tuple(self.complete(messages, **kwargs) for messages, kwargs in requests)


def test_m7_batches_three_counterfactual_state_branches_and_retains_primary():
    client = _M7BatchClient()

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M7",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        agent_policy_id="knowledge-grounded-multistate-action-support-v1",
        agent_aggregator_id="action-support-primary-control-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 14
    assert result.parse_failure is False
    assert result.agent_vote_key_ids == ("K001", "K002", "K002", "K001")
    assert result.agent_actions == (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "explore:balanced-evidence-v1",
        "explore:primary-challenge-v1",
        "explore:retrieval-gap-v1",
        "select:retain-primary-for-support",
    )
    assert client.batch_sizes == [2, 3, 3, 6]
    branches = result.agent_steps[2:]
    assert [branch["state_policy_id"] for branch in branches] == [
        "balanced-evidence-v1",
        "primary-challenge-v1",
        "retrieval-gap-v1",
    ]
    assert [branch["calls"] for branch in branches] == [4, 4, 4]
    assert all(branch["parse_failure"] is False for branch in branches)
    assert all(
        branch["causal_parent_ids"]
        == ["match:speech-only-primary", "retrieve:speech-only"]
        for branch in branches
    )
    assert all(
        kwargs["decoding_params"]["max_tokens"] == 512
        and "response_format" in kwargs["decoding_params"]
        for _messages, kwargs in client.calls
        if ":state-" in kwargs["matcher_policy_id"]
    )
    _assert_every_call_carries_query(client)


def test_m7_fails_one_invalid_state_branch_closed_without_canceling_siblings():
    client = _M7BatchClient(invalid_state_policy_id="primary-challenge-v1")

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M7",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        agent_policy_id="knowledge-grounded-multistate-action-support-v1",
        agent_aggregator_id="action-support-primary-control-v1",
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 11
    assert result.parse_failure is False
    assert result.agent_vote_key_ids == ("K001", "K002", None, "K001")
    assert client.batch_sizes == [2, 3, 2, 4]
    failed = result.agent_steps[3]
    assert failed["state_policy_id"] == "primary-challenge-v1"
    assert failed["grounded_query_state"] is None
    assert failed["key_id"] is None
    assert failed["calls"] == 1
    assert failed["parse_failure"] is True
    assert result.agent_steps[2]["key_id"] == "K002"
    assert result.agent_steps[4]["key_id"] == "K001"
    _assert_every_call_carries_query(client)


class _M8PairwiseClient:
    def __init__(self, *, unstable_k1=False):
        self.unstable_k1 = unstable_k1
        self.calls = []
        self.batch_sizes = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        stage = kwargs["matcher_policy_id"]
        if stage.endswith(":primary-listwise"):
            return '{"key_id":"K001"}'
        if stage.endswith(":speech-retrieve-top-2"):
            return '{"key_ids":["K001","K002"]}'
        if ":pairwise-K1-rank-1-ab" in stage:
            return '{"key_id":"K002"}'
        if ":pairwise-K1-rank-1-ba" in stage:
            return '{"key_id":"K001"}' if self.unstable_k1 else '{"key_id":"K002"}'
        if ":pairwise-K2-rank-1-" in stage:
            return '{"key_id":"K002"}'
        raise AssertionError(stage)

    def complete_many(self, requests, *, trace_parent=None):
        del trace_parent
        self.batch_sizes.append(len(requests))
        return tuple(self.complete(messages, **kwargs) for messages, kwargs in requests)


def test_m8_batches_order_controlled_k1_k2_pairwise_support_and_retains_primary():
    client = _M8PairwiseClient()

    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M8",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-pairwise-boundary-support-v1",
        agent_aggregator_id="pairwise-boundary-primary-control-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 6
    assert result.top_key_ids == ("K001", "K002")
    assert result.agent_vote_key_ids == ("K001", "K002", "K002")
    assert result.agent_actions == (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "compare:pairwise-boundary-rank-1",
        "select:retain-primary-for-support",
    )
    assert client.batch_sizes == [2, 4]
    comparison = result.agent_steps[2]
    assert comparison == {
        "action_id": "compare:pairwise-boundary-rank-1",
        "rank": 1,
        "primary_key_id": "K001",
        "challenger_key_id": "K002",
        "k1_ab_key_id": "K002",
        "k1_ba_key_id": "K002",
        "k1_stable_key_id": "K002",
        "k2_ab_key_id": "K002",
        "k2_ba_key_id": "K002",
        "k2_stable_key_id": "K002",
        "calls": 4,
        "parse_failure": False,
        "causal_parent_ids": [
            "match:speech-only-primary",
            "retrieve:speech-only",
        ],
    }
    pairwise_calls = client.calls[2:]
    assert [
        kwargs["matcher_policy_id"].rsplit("-", 1)[-1]
        for _messages, kwargs in pairwise_calls
    ] == ["ab", "ba", "ab", "ba"]
    assert all(
        kwargs["decoding_params"]["response_format"]["json_schema"]["schema"][
            "properties"
        ]["key_id"]["enum"]
        == ["K001", "K002"]
        for _messages, kwargs in pairwise_calls
    )
    rendered_pairs = [
        next(
            part["text"]
            for part in messages[1]["content"]
            if part.get("type") == "text"
        )
        for messages, _kwargs in pairwise_calls
    ]
    assert "Contrastive boundary:" not in rendered_pairs[0]
    assert "Contrastive boundary:" in rendered_pairs[2]
    _assert_every_call_carries_query(client)


def test_m8_marks_order_disagreement_as_no_supported_action():
    result = run_speech_native_matcher(
        core_client=_M8PairwiseClient(unstable_k1=True),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M8",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-pairwise-boundary-support-v1",
        agent_aggregator_id="pairwise-boundary-primary-control-v1",
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.agent_vote_key_ids == ("K001", None, "K002")
    assert result.agent_steps[2]["k1_stable_key_id"] is None


class _M9FactorGraphClient:
    def __init__(self, *, invalid_factor_state=False, invalid_rerank=False):
        self.invalid_factor_state = invalid_factor_state
        self.invalid_rerank = invalid_rerank
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        stage = kwargs["matcher_policy_id"]
        if stage.endswith(":primary-listwise"):
            return '{"key_id":"K001"}'
        if stage.endswith(":speech-retrieve-top-2"):
            return '{"key_ids":["K001","K002"]}'
        if stage.endswith(":link-factors"):
            if self.invalid_factor_state:
                return '{"factor_ids":["F999"],"boundary_id":"B001"}'
            return '{"factor_ids":["F003","F004"],"boundary_id":"B001"}'
        if stage.endswith(":factor-rerank-top-2"):
            if self.invalid_rerank:
                return '{"key_ids":["K002"]}'
            return '{"key_ids":["K002","K001"]}'
        if ":boundary-rank-1-" in stage:
            return '{"key_id":"K002"}'
        raise AssertionError(stage)

    def complete_many(self, requests, *, trace_parent=None):
        del trace_parent
        return tuple(self.complete(messages, **kwargs) for messages, kwargs in requests)


def test_m9_runs_speech_conditioned_factor_graph_loop_and_retains_primary():
    client = _M9FactorGraphClient()
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.top_key_ids == ("K002", "K001")
    assert result.calls == 6
    assert result.agent_vote_key_ids == ("K001", "K002", "K002", "K002")
    assert result.agent_actions == (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "link:knowledge-factors",
        "tool:expand-factor-graph",
        "rerank:speech-plus-factor-state",
        "compare:boundary-ab",
        "compare:boundary-ba",
        "select:retain-primary-for-support",
    )
    factor_step = result.agent_steps[2]
    assert factor_step["factor_link_state"] == {
        "factor_ids": ["F003", "F004"],
        "boundary_id": "B001",
    }
    assert result.agent_steps[3]["expanded_key_ids"] == ["K001", "K002"]
    link_format = client.calls[2][1]["decoding_params"]["response_format"]
    assert link_format["json_schema"]["schema"]["additionalProperties"] is False
    assert all(
        "transcript" not in json.dumps(messages).lower()
        for messages, _kwargs in client.calls
    )
    _assert_every_call_carries_query(client)


def test_m9_invalid_factor_ids_fail_closed_to_primary_without_rerank():
    client = _M9FactorGraphClient(invalid_factor_state=True)
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 3
    assert result.agent_actions[-1] == "backtrack:invalid-factor-link-state"
    assert len(client.calls) == 3
    _assert_every_call_carries_query(client)


class _M11AdaptiveEvidenceClient:
    def __init__(self, *, agree=False):
        self.agree = agree
        self.calls = []

    def complete(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        stage = kwargs["matcher_policy_id"]
        if stage.endswith(":primary-listwise"):
            return '{"key_id":"K001"}'
        if stage.endswith(":speech-retrieve-top-2"):
            return (
                '{"key_ids":["K001","K002"]}'
                if self.agree
                else '{"key_ids":["K002","K001"]}'
            )
        if stage.endswith(":candidate-action-state"):
            return (
                '{"key_id":"K001","factor_ids":["F001","F002"]}'
                if self.agree
                else '{"key_id":"K002","factor_ids":["F003","F004"]}'
            )
        if stage.endswith(":boundary-ab") or stage.endswith(":boundary-ba"):
            return '{"key_id":"K002"}'
        raise AssertionError(stage)

    def complete_many(self, requests, *, trace_parent=None):
        del trace_parent
        return tuple(self.complete(messages, **kwargs) for messages, kwargs in requests)


def test_m11_stops_when_primary_retrieval_and_action_state_are_complete():
    client = _M11AdaptiveEvidenceClient(agree=True)
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 3
    assert result.agent_escalated is False
    assert result.agent_vote_key_ids == ("K001", "K001", "K001")
    assert result.agent_actions[-1] == "stop:complete-consistent-state"
    assert result.agent_steps[-1]["factor_ids"] == ["F001", "F002"]
    assert result.agent_steps[-1]["new_knowledge_ids"] == ["F001", "F002"]
    assert not any("boundary-" in call[1]["matcher_policy_id"] for call in client.calls)
    _assert_every_call_carries_query(client)


def test_m11_retrieves_pair_boundary_only_for_an_observed_evidence_gap():
    client = _M11AdaptiveEvidenceClient()
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.top_key_ids == ("K002", "K001")
    assert result.calls == 5
    assert result.agent_escalated is True
    assert result.agent_vote_key_ids == (
        "K001",
        "K002",
        "K002",
        "K002",
        "K002",
    )
    assert result.agent_actions == (
        "match:speech-only-primary",
        "retrieve:speech-only",
        "link:candidate-action-state",
        "retrieve:pair-boundary:B001",
        "compare:boundary-ab",
        "compare:boundary-ba",
        "select:retain-primary-for-support",
    )
    boundary_step = result.agent_steps[-1]
    assert boundary_step["boundary_id"] == "B001"
    assert boundary_step["new_knowledge_ids"] == ["B001"]
    assert boundary_step["information_gap"] == "candidate-disagreement"
    assert boundary_step["ab_key_id"] == "K002"
    assert boundary_step["ba_key_id"] == "K002"
    assert all(
        "transcript" not in json.dumps(messages).lower()
        for messages, _kwargs in client.calls
    )
    _assert_every_call_carries_query(client)


def test_m11_contact_dispatch_interleaves_new_evidence_before_root_backlog():
    class ConcurrentM11Client(_M11AdaptiveEvidenceClient):
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.stage_order = []

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.stage_order.append(stage)
            try:
                time.sleep(0.005)
                return super().complete(messages, **kwargs)
            finally:
                with self.lock:
                    self.active -= 1

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m11-{index}",
            sample=type("Sample", (), {"sample_id": f"m11-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m11-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M11",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            decision_graph=_decision_graph_fixture(),
            agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
            agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        )
        for index in range(4)
    )
    client = ConcurrentM11Client()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=8,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 4
    assert client.max_active == 2
    assert all(outcome.decision.calls == 5 for outcome in outcomes)
    initial_positions = [
        index
        for index, stage in enumerate(client.stage_order)
        if stage.endswith(":primary-listwise")
        or stage.endswith(":speech-retrieve-top-2")
    ]
    first_evidence_position = next(
        index
        for index, stage in enumerate(client.stage_order)
        if stage.endswith(":candidate-action-state")
    )
    assert first_evidence_position < max(initial_positions)
    assert all(outcome.decision.key_id == "K001" for outcome in outcomes)


def _m11_decision_row(result, *, sample_id="sample-1", task_id=None):
    return {
        "schema": "saea-speech-native-decision-v1",
        "task_id": task_id or f"canonical:{sample_id}",
        "sample_id": sample_id,
        "query_sample_id": sample_id,
        "speech_packet_sha256": "1" * 64,
        "mechanism_control_id": "matched",
        "key_representation_id": "K1",
        "matcher_policy_id": "M11",
        "key_id": result.key_id,
        "predicted_value_label": result.value_label,
        "top_key_ids": list(result.top_key_ids),
        "verifier_scores": {},
        "calls": result.calls,
        "parse_failure": result.parse_failure,
        "agent_policy_id": result.agent_policy_id,
        "agent_actions": list(result.agent_actions),
        "agent_escalated": result.agent_escalated,
        "agent_vote_key_ids": list(result.agent_vote_key_ids),
        "agent_steps": list(result.agent_steps),
        "agent_aggregator_id": result.agent_aggregator_id,
        "response_text_sha256": [f"{index + 1:064x}" for index in range(result.calls)],
    }


def test_m11_reader_reconstructs_information_gain_and_action_space():
    result = run_speech_native_matcher(
        core_client=_M11AdaptiveEvidenceClient(),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    trajectory = _parse_m11_adaptive_evidence_gap_trajectory(
        row=_m11_decision_row(result),
        sample_id="sample-1",
        speaker_id="speaker-1",
        gold_key_id="K002",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )

    assert trajectory["primary_key_id"] == "K001"
    assert trajectory["retrieval_key_id"] == "K002"
    assert trajectory["action_key_id"] == "K002"
    assert trajectory["new_factor_ids"] == ("F003", "F004")
    assert trajectory["new_boundary_id"] == "B001"
    assert trajectory["boundary_stable_key_id"] == "K002"
    assert trajectory["total_calls"] == 5

    metrics = _evaluate_m11_adaptive_evidence_gap((trajectory,))
    assert metrics["primary_correct"] == 0
    assert metrics["retrieval_top1_correct"] == 1
    assert metrics["action_state_correct"] == 1
    assert metrics["boundary_stable_correct"] == 1
    assert metrics["oracle_gain_vs_primary"] == 1
    assert metrics["new_knowledge_query_count"] == 1
    assert metrics["adaptive_boundary_query_count"] == 1
    assert metrics["final_minus_primary_correct"] == 0


def _write_m11_engineering_action_audit_fixture(tmp_path):
    attempt_dir = tmp_path / "m11-attempt"
    attempt_dir.mkdir()
    graph_path = (
        REPO_ROOT / "configs/knowledge/slurp-data-derived-decision-graph-v2.json"
    )
    graph_sha256 = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    audit_cards = tuple(
        KeyCardV1(
            key_id=f"K{index:03d}",
            definition="Audit-only opaque key definition.",
            positive_examples=("Audit-only example.",),
            contrastive_boundary=None,
            value_label=f"audit-{index:03d}",
        ).validate()
        for index in range(1, 19)
    )
    graph = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=audit_cards,
    )
    operation_factor_id = next(
        factor.factor_id
        for factor in graph.factors
        if factor.kind == "operation" and "K003" in factor.key_ids
    )

    class AuditM11Client:
        def complete(self, messages, **kwargs):
            del messages
            stage = kwargs["matcher_policy_id"]
            if stage.endswith(":primary-listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":speech-retrieve-top-3"):
                return '{"key_ids":["K003","K001","K005"]}'
            if stage.endswith(":candidate-action-state"):
                return json.dumps(
                    {"key_id": "K003", "factor_ids": [operation_factor_id]}
                )
            if stage.endswith(":boundary-ab") or stage.endswith(":boundary-ba"):
                return '{"key_id":"K003"}'
            raise AssertionError(stage)

        def complete_many(self, requests, *, trace_parent=None):
            del trace_parent
            return tuple(
                self.complete(messages, **kwargs) for messages, kwargs in requests
            )

    result = run_speech_native_matcher(
        core_client=AuditM11Client(),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=audit_cards,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=graph,
        top_k=3,
    )
    assert result.calls == 5
    order_ids = ("canonical", "reverse", "rotate-1", "rotate-7")
    rows = []
    for order_id in order_ids:
        for index in range(8):
            sample_id = f"slurp:train:{index:06d}:audio-{index}"
            row = _m11_decision_row(
                result,
                sample_id=sample_id,
                task_id=f"{order_id}:{sample_id}",
            )
            row["speech_packet_sha256"] = f"{index + 1:064x}"
            row["predicted_value_label"] = "must-not-enter-audit-output"
            row["response_text_sha256"] = [
                f"{60000 + len(rows) * result.calls + offset:064x}"
                for offset in range(result.calls)
            ]
            rows.append(row)
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    trace_rows = []
    for row in rows:
        descriptor = {
            "packet_id": row["query_sample_id"].replace(":", "/"),
            "sha256": row["speech_packet_sha256"],
            "role": "query",
        }
        for contact_index in range(row["calls"]):
            trace_rows.extend(
                (
                    {
                        "channel": "MODEL_REQUEST",
                        "payload": {
                            "payload": {
                                "request_id": f"{row['task_id']}-{contact_index}",
                                "sample_id": row["query_sample_id"],
                                "query_source": "speech_features",
                                "mmproj_loaded": False,
                                "speech_packet_sha256": row["speech_packet_sha256"],
                                "speech_feature_parts": [descriptor],
                            }
                        },
                    },
                    {
                        "channel": "MODEL_RESPONSE",
                        "payload": {
                            "usage": {"prompt_tokens": 10, "completion_tokens": 2}
                        },
                    },
                    {"channel": "COST", "payload": {"calls": 1}},
                )
            )
    run_id = "SAEA-SN-M11-ENGINEERING-AUDIT"
    trace = attempt_dir / f"{run_id}.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row) + "\n" for row in trace_rows), encoding="utf-8"
    )
    process_audit = attempt_dir / f"{run_id}.mmproj-audit.json"
    process_audit.write_text(
        json.dumps({"mmproj_loaded": False, "mmproj_hit_count": 0}),
        encoding="utf-8",
    )
    contact_count = len(rows) * result.calls
    receipt = {
        "status": "COMPLETED",
        "run_id": run_id,
        "attempt_id": "attempt-m11-audit-001",
        "request_failures": [],
        "profile": {
            "key_representation_id": "K1",
            "matcher_policy_id": "M11",
            "agent_policy_id": "speech-conditioned-adaptive-evidence-gap-v1",
            "agent_aggregator_id": "adaptive-evidence-gap-primary-control-v1",
            "mechanism_control_id": "matched",
            "top_k": 3,
            "task_count": len(rows),
            "key_order_ids": list(order_ids),
            "actual_contact_count": contact_count,
            "planned_contact_ceiling": contact_count,
            "contact_ceiling_per_task": 5,
            "decision_graph_id": graph.graph_id,
            "decision_graph_path": graph_path.relative_to(REPO_ROOT).as_posix(),
            "decision_graph_file_sha256": graph_sha256,
        },
        "decisions": {
            "path": decisions.name,
            "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
            "count": len(rows),
            "contains_gold_labels": False,
        },
        "server_log_scan": {
            "oom_marker_hits": [],
            "host_spill_marker_hits": [],
            "runaway_marker_hits": [],
            "mmproj_free_chunk_count": 0,
        },
        "process_audit_sha256": hashlib.sha256(process_audit.read_bytes()).hexdigest(),
        "close": {"cost": {"calls_used": contact_count}},
    }
    flight = attempt_dir / "flight-receipt.json"
    flight.write_text(json.dumps(receipt), encoding="utf-8")
    attempt_record = tmp_path / "m11-attempt-record.json"
    attempt_record.write_text(
        json.dumps(
            {
                "run_id": receipt["run_id"],
                "attempt_id": receipt["attempt_id"],
                "state": "FINALIZED",
                "actual": {
                    "calls": contact_count,
                    "audio_seconds": 1.0,
                    "gpu_seconds": 2.0,
                },
            }
        ),
        encoding="utf-8",
    )
    return attempt_dir, attempt_record, flight, decisions, trace


def test_action_support_audit_accepts_m11_batched_orders_without_reading_gold(tmp_path):
    attempt_dir, attempt_record, flight, decisions, trace = (
        _write_m11_engineering_action_audit_fixture(tmp_path)
    )
    report = audit_speech_native_action_support(
        attempt_dir=attempt_dir,
        attempt_record_path=attempt_record,
        attempt_record_sha256=hashlib.sha256(attempt_record.read_bytes()).hexdigest(),
        flight_receipt_sha256=hashlib.sha256(flight.read_bytes()).hexdigest(),
        decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),
    )

    assert report["schema"] == "saea-speech-native-adaptive-evidence-gap-audit-v1"
    assert report["gold_read"] is False
    assert report["decision_count"] == 32
    assert report["key_order_count"] == 4
    assert report["contact_count"] == 160
    assert report["valid_speech_query_contact_count"] == 160
    assert report["adaptive_boundary_query_count"] == 32
    assert report["action_variable_query_count"] == 32
    assert report["mechanism_failure_count"] == 0
    assert report["calls_distribution"] == {"5": 32}
    assert "must-not-enter-audit-output" not in json.dumps(report, sort_keys=True)


@pytest.mark.parametrize(
    ("client", "expected_termination", "expected_calls"),
    [
        (
            _M9FactorGraphClient(invalid_factor_state=True),
            "invalid-factor-link-state",
            3,
        ),
        (_M9FactorGraphClient(invalid_rerank=True), "invalid-factor-rerank", 4),
    ],
)
def test_m9_reader_reconstructs_fail_closed_mechanism_trajectories(
    client, expected_termination, expected_calls
):
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    row = {
        "key_id": result.key_id,
        "top_key_ids": list(result.top_key_ids),
        "calls": result.calls,
        "agent_policy_id": result.agent_policy_id,
        "agent_aggregator_id": result.agent_aggregator_id,
        "agent_escalated": result.agent_escalated,
        "agent_actions": list(result.agent_actions),
        "agent_vote_key_ids": list(result.agent_vote_key_ids),
        "agent_steps": list(result.agent_steps),
        "verifier_scores": {},
    }
    trajectory = _parse_m9_factor_graph_trajectory(
        row=row,
        sample_id="sample-failure",
        speaker_id="speaker-failure",
        gold_key_id="K002",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )
    assert trajectory["termination"] == expected_termination
    assert trajectory["total_calls"] == expected_calls
    assert trajectory["mechanism_failure"] is True
    assert trajectory["reranked_key_ids"] == ("K001",)


def test_m9_reader_accepts_legacy_partial_rerank_failure_flag():
    result = run_speech_native_matcher(
        core_client=_M9FactorGraphClient(invalid_rerank=True),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    steps = [dict(step) for step in result.agent_steps]
    steps[-1]["parse_failure"] = False
    row = {
        "key_id": result.key_id,
        "top_key_ids": list(result.top_key_ids),
        "calls": result.calls,
        "agent_policy_id": result.agent_policy_id,
        "agent_aggregator_id": result.agent_aggregator_id,
        "agent_escalated": result.agent_escalated,
        "agent_actions": list(result.agent_actions),
        "agent_vote_key_ids": list(result.agent_vote_key_ids),
        "agent_steps": steps,
        "verifier_scores": {},
    }
    trajectory = _parse_m9_factor_graph_trajectory(
        row=row,
        sample_id="sample-legacy-partial",
        speaker_id="speaker-legacy-partial",
        gold_key_id="K002",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )
    assert trajectory["termination"] == "invalid-factor-rerank"
    assert trajectory["mechanism_failure"] is True


def test_m9_contact_dispatch_marks_partial_rerank_as_parse_failure():
    task = SpeechNativeMatchTask(
        task_id="m9-partial-rerank",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        top_k=2,
        decision_graph=_decision_graph_fixture(),
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
    )
    outcome = run_speech_native_match_tasks(
        core_client=_M9FactorGraphClient(invalid_rerank=True),
        tasks=(task,),
        slot_count=1,
        queue_depth=1,
        dispatch_granularity="contact",
    )[0]
    assert outcome.decision.agent_actions[-1] == "backtrack:invalid-factor-rerank"
    assert outcome.decision.agent_steps[-1]["parse_failure"] is True


def test_m9_reader_reconstructs_graph_state_and_action_support():
    result = run_speech_native_matcher(
        core_client=_M9FactorGraphClient(),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    row = {
        "key_id": result.key_id,
        "top_key_ids": list(result.top_key_ids),
        "calls": result.calls,
        "agent_policy_id": result.agent_policy_id,
        "agent_aggregator_id": result.agent_aggregator_id,
        "agent_escalated": result.agent_escalated,
        "agent_actions": list(result.agent_actions),
        "agent_vote_key_ids": list(result.agent_vote_key_ids),
        "agent_steps": list(result.agent_steps),
        "verifier_scores": {},
    }

    trajectory = _parse_m9_factor_graph_trajectory(
        row=row,
        sample_id="sample-1",
        speaker_id="speaker-1",
        gold_key_id="K002",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )
    metrics = _evaluate_m9_factor_graph_action_support((trajectory,))

    assert trajectory["initial_top_key_ids"] == ("K001", "K002")
    assert trajectory["expanded_key_ids"] == ("K001", "K002")
    assert trajectory["reranked_key_ids"] == ("K002", "K001")
    assert trajectory["boundary_stable_key_id"] == "K002"
    assert metrics["primary_correct"] == 0
    assert metrics["oracle_correct"] == 1
    assert metrics["initial_top_k_reachable_count"] == 1
    assert metrics["expanded_reachable_count"] == 1
    assert metrics["action_families"]["factor-rerank"]["helpful_action_count"] == 1
    assert metrics["action_families"]["boundary-stable"]["helpful_action_count"] == 1
    assert metrics["support_gate_passed"] is False

    broken = dict(row)
    broken_steps = [dict(step) for step in row["agent_steps"]]
    broken_steps[3]["expanded_key_ids"] = ["K002", "K001"]
    broken["agent_steps"] = broken_steps
    with pytest.raises(SpeechNativeProfileError, match="expansion"):
        _parse_m9_factor_graph_trajectory(
            row=broken,
            sample_id="sample-1",
            speaker_id="speaker-1",
            gold_key_id="K002",
            top_k=2,
            visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
            decision_graph=_decision_graph_fixture(),
        )


def test_m8_contact_dispatch_replays_heterogeneous_pairwise_dags_at_full_slots():
    extra_cards = (
        KeyCardV1(
            key_id="K003",
            definition="Commands about calendar events.",
            positive_examples=("show my calendar",),
            contrastive_boundary="Do not use for alarms.",
            value_label="calendar",
        ).validate(),
        KeyCardV1(
            key_id="K004",
            definition="Commands about current weather.",
            positive_examples=("will it rain",),
            contrastive_boundary="Do not use for calendar events.",
            value_label="weather",
        ).validate(),
    )
    cards = (*_KEY_CARDS, *extra_cards)

    class HeterogeneousPairwiseClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.calls = []

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            sample_id = kwargs["speech_feature_sample_id"]
            sample_index = int(sample_id.rsplit("-", 1)[-1])
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.calls.append((messages, kwargs))
            try:
                if stage.endswith(":primary-listwise"):
                    time.sleep(0.002)
                    return '{"key_id":"K001"}'
                if stage.endswith(":speech-retrieve-top-3"):
                    time.sleep(0.010)
                    top_ids = (
                        ["K001", "K002", "K003"]
                        if sample_index % 2 == 0
                        else ["K002", "K003", "K004"]
                    )
                    return json.dumps({"key_ids": top_ids})
                if ":pairwise-K1-" in stage:
                    time.sleep(0.003)
                    return '{"key_id":"K001"}'
                if ":pairwise-K2-" in stage:
                    time.sleep(0.007)
                    return '{"key_id":"K001"}'
                raise AssertionError(stage)
            finally:
                with self.lock:
                    self.active -= 1

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m8-replay-{index}",
            sample=type("Sample", (), {"sample_id": f"m8-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m8-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=cards,
            key_representation_id="K1",
            matcher_policy_id="M8",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=3,
            agent_policy_id="speech-conditioned-pairwise-boundary-support-v1",
            agent_aggregator_id="pairwise-boundary-primary-control-v1",
        )
        for index in range(12)
    )
    client = HeterogeneousPairwiseClient()

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=4,
        queue_depth=8,
        dispatch_granularity="contact",
    )

    assert client.max_active == 4
    assert [outcome.decision.calls for outcome in outcomes] == [
        10 if index % 2 == 0 else 14 for index in range(12)
    ]
    assert len(client.calls) == 144
    for messages, kwargs in client.calls:
        query_parts = [
            part["speech_features"]
            for part in messages[1]["content"]
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert len(query_parts) == 1
        assert query_parts[0]["packet_id"].endswith(kwargs["speech_feature_sample_id"])


def test_m8_contact_dispatch_uses_one_global_request_executor(monkeypatch):
    real_executor = pslu_module.ThreadPoolExecutor
    prefixes = []

    class RecordingExecutor:
        def __init__(self, *args, **kwargs):
            prefixes.append(kwargs.get("thread_name_prefix"))
            self.delegate = real_executor(*args, **kwargs)

        def submit(self, *args, **kwargs):
            return self.delegate.submit(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            return self.delegate.shutdown(*args, **kwargs)

        def __enter__(self):
            self.delegate.__enter__()
            return self

        def __exit__(self, *args):
            return self.delegate.__exit__(*args)

    monkeypatch.setattr(pslu_module, "ThreadPoolExecutor", RecordingExecutor)
    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m8-global-{index}",
            sample=type("Sample", (), {"sample_id": f"m8-global-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m8-global-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M8",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            agent_policy_id="speech-conditioned-pairwise-boundary-support-v1",
            agent_aggregator_id="pairwise-boundary-primary-control-v1",
        )
        for index in range(4)
    )

    outcomes = run_speech_native_match_tasks(
        core_client=_M8PairwiseClient(),
        tasks=tasks,
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 4
    assert prefixes == ["saea-speech-native-contact"]


def test_m8_global_ready_frontier_admits_all_initial_nodes_before_pairwise_children():
    class FrontierClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.calls = []

        def complete(self, messages, **kwargs):
            del messages
            stage = kwargs["matcher_policy_id"]
            sample_id = kwargs["speech_feature_sample_id"]
            with self.lock:
                self.calls.append((sample_id, stage))
            time.sleep(0.002)
            if stage.endswith(":primary-listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":speech-retrieve-top-2"):
                return '{"key_ids":["K001","K002"]}'
            if ":pairwise-" in stage:
                return '{"key_id":"K001"}'
            raise AssertionError(stage)

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"frontier-{index}",
            sample=type("Sample", (), {"sample_id": f"frontier-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/frontier-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M8",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            agent_policy_id="speech-conditioned-pairwise-boundary-support-v1",
            agent_aggregator_id="pairwise-boundary-primary-control-v1",
        )
        for index in range(4)
    )
    client = FrontierClient()

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=2,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 4
    first_pairwise_index = next(
        index
        for index, (_sample_id, stage) in enumerate(client.calls)
        if ":pairwise-" in stage
    )
    initial_prefix = client.calls[:first_pairwise_index]
    assert {sample_id for sample_id, _stage in initial_prefix} == {
        f"frontier-sample-{index}" for index in range(4)
    }
    assert len(initial_prefix) == 8


def _m9_match_tasks(count=4):
    return tuple(
        SpeechNativeMatchTask(
            task_id=f"m9-global-{index}",
            sample=type("Sample", (), {"sample_id": f"m9-global-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m9-global-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M9",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
            agent_aggregator_id="factor-graph-primary-control-v1",
            decision_graph=_decision_graph_fixture(),
        )
        for index in range(count)
    )


def test_m9_contact_dispatch_uses_one_global_request_executor(monkeypatch):
    real_executor = pslu_module.ThreadPoolExecutor
    prefixes = []

    class RecordingExecutor:
        def __init__(self, *args, **kwargs):
            prefixes.append(kwargs.get("thread_name_prefix"))
            self.delegate = real_executor(*args, **kwargs)

        def submit(self, *args, **kwargs):
            return self.delegate.submit(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            return self.delegate.shutdown(*args, **kwargs)

        def __enter__(self):
            self.delegate.__enter__()
            return self

        def __exit__(self, *args):
            return self.delegate.__exit__(*args)

    monkeypatch.setattr(pslu_module, "ThreadPoolExecutor", RecordingExecutor)

    outcomes = run_speech_native_match_tasks(
        core_client=_M9FactorGraphClient(),
        tasks=_m9_match_tasks(),
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 4
    assert all(outcome.decision.calls == 6 for outcome in outcomes)
    assert prefixes == ["saea-speech-native-contact"]


def test_m9_global_ready_frontier_batches_initial_contacts_before_graph_children():
    class FrontierClient(_M9FactorGraphClient):
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def complete(self, messages, **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            try:
                time.sleep(0.002)
                return super().complete(messages, **kwargs)
            finally:
                with self.lock:
                    self.active -= 1

    client = FrontierClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=_m9_match_tasks(),
        slot_count=2,
        queue_depth=2,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 4
    assert client.max_active == 2
    stages = [kwargs["matcher_policy_id"] for _messages, kwargs in client.calls]
    first_graph_child = next(
        index for index, stage in enumerate(stages) if stage.endswith(":link-factors")
    )
    initial_prefix = client.calls[:first_graph_child]
    assert {
        kwargs["speech_feature_sample_id"] for _messages, kwargs in initial_prefix
    } == {f"m9-global-sample-{index}" for index in range(4)}
    assert len(initial_prefix) == 8
    for messages, kwargs in client.calls:
        queries = [
            part["speech_features"]
            for part in messages[1]["content"]
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert len(queries) == 1
        assert queries[0]["packet_id"].endswith(kwargs["speech_feature_sample_id"])


def test_contact_dispatch_runs_m7_verifier_wave_as_one_batched_ready_stage():
    class ParallelM7Client(_M7BatchClient):
        def __init__(self):
            super().__init__()
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.verifier_barrier = threading.Barrier(6)

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            if ":grounded-verify-" in stage:
                self.verifier_barrier.wait(timeout=1)
            try:
                return super().complete(messages, **kwargs)
            finally:
                with self.lock:
                    self.active -= 1

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M7",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        decoding_params={"temperature": 0, "max_tokens": 64},
        top_k=2,
        agent_policy_id="knowledge-grounded-multistate-action-support-v1",
        agent_aggregator_id="action-support-primary-control-v1",
    )
    client = ParallelM7Client()

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=(task,),
        slot_count=6,
        queue_depth=6,
        dispatch_granularity="contact",
    )

    assert outcomes[0].decision.key_id == "K001"
    assert outcomes[0].decision.calls == 14
    assert outcomes[0].slot_id == -1
    assert client.max_active == 6
    _assert_every_call_carries_query(client)


def test_m3_verifies_each_retrieved_candidate_and_arbitrates_only_a_tie():
    client = _SpeechFeatureClient(
        [
            '```json\n{"key_ids":["K001","K002"]}\n```',
            '```json\n{"compatible":true,"confidence":80}\n```',
            '```json\n{"compatible":true,"confidence":80}\n```',
            '```json\n{"key_id":"K002"}\n```',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M3",
        top_k=2,
    )
    assert result.key_id == "K002"
    assert result.calls == 4
    assert result.top_key_ids == ("K001", "K002")
    _assert_every_call_carries_query(client)


def test_m3_v3_requires_exact_distinct_keys_without_markdown_fences():
    client = _SpeechFeatureClient(
        [
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M3",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )
    retrieval_prompt = client.calls[0][0][0]["content"]
    assert "exactly 2 distinct" in retrieval_prompt
    assert "single-line JSON" in retrieval_prompt
    assert "Do not use Markdown or code fences" in retrieval_prompt
    assert result.key_id == "K001"


def test_m3_v3_rejects_an_incomplete_retrieval_list_without_retrying():
    client = _SpeechFeatureClient(['{"key_ids":["K001"]}'])
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M3",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )
    assert result.key_id is None
    assert result.parse_failure is True
    assert result.calls == 1


def test_m3_contrastive_verifier_policy_tightens_candidate_compatibility_prompt():
    client = _SpeechFeatureClient(
        [
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M3",
        prompt_policy_id="speech-native-json-copy-v3",
        verifier_policy_id="speech-native-contrastive-verifier-v2",
        top_k=2,
    )
    verifier_prompt = client.calls[1][0][0]["content"]
    assert "both the domain and requested operation" in verifier_prompt
    assert "merely related topic" in verifier_prompt
    assert result.key_id == "K001"


def test_m4_trace_policy_preserves_ensemble_and_order_identity():
    client = _SpeechFeatureClient(
        ['{"key_id":"K001"}', '{"key_id":"K002"}', '{"key_id":"K001"}']
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K2",
        matcher_policy_id="M4",
        ensemble_base_policy_id="M1",
    )

    assert result.key_id == "K001"
    assert [kwargs["matcher_policy_id"] for _, kwargs in client.calls] == [
        "M4:M1:order-0:listwise",
        "M4:M1:order-1:listwise",
        "M4:M1:order-2:listwise",
    ]
    _assert_every_call_carries_query(client)


def test_m4_uses_rotate_seven_and_falls_back_to_the_canonical_vote_on_a_tie():
    cards = tuple(
        KeyCardV1(
            key_id=f"K{index:03d}",
            definition=f"Definition {index}",
            positive_examples=(f"Example {index}",),
            contrastive_boundary=None,
            value_label=f"label-{index}",
        ).validate()
        for index in range(1, 19)
    )
    client = _SpeechFeatureClient(
        ['{"key_id":"K003"}', '{"key_id":"K002"}', '{"key_id":"K001"}']
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=cards,
        key_representation_id="K1",
        matcher_policy_id="M4",
        ensemble_base_policy_id="M1",
    )

    assert result.key_id == "K003"
    rotate_text = client.calls[2][0][1]["content"][0]["text"]
    assert rotate_text.startswith("K008\n")
    _assert_every_call_carries_query(client)


def test_m5_stops_when_listwise_and_canonical_retrieve_verify_agree():
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )

    assert result.key_id == "K001"
    assert result.calls == 4
    assert result.agent_policy_id == "m1-m3-disagreement-escalation-v1"
    assert result.agent_actions == (
        "match:listwise-canonical",
        "retrieve-verify:canonical",
        "stop:agree",
    )
    assert result.agent_escalated is False
    assert result.agent_vote_key_ids == ("K001", "K001")
    assert all(
        ":reverse:" not in kwargs["matcher_policy_id"] for _, kwargs in client.calls
    )
    _assert_every_call_carries_query(client)


def test_m5_full_branch_explorer_records_counterfactual_actions_even_on_agreement():
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
        agent_policy_id="m1-m3-full-branch-explorer-v1",
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )

    assert result.key_id == "K001"
    assert result.calls == 10
    assert result.agent_policy_id == "m1-m3-full-branch-explorer-v1"
    assert result.agent_escalated is False
    assert result.agent_vote_key_ids == ("K001", "K001", "K002", "K001")
    assert result.agent_actions == (
        "match:listwise-canonical",
        "retrieve-verify:canonical",
        "explore:full-branch",
        "retrieve-verify:reverse",
        "retrieve-verify:rotate-7",
        "aggregate:m3-unanimous-primary-fallback",
    )
    _assert_every_call_carries_query(client)


def test_m5_escalates_disagreement_and_uses_m3_majority():
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
            '{"key_ids":["K002","K001"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
            '{"key_ids":["K001","K002"]}',
            '{"compatible":true,"confidence":90}',
            '{"compatible":false,"confidence":10}',
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )

    assert result.key_id == "K002"
    assert result.calls == 10
    assert result.agent_escalated is True
    assert result.agent_vote_key_ids == ("K001", "K002", "K002", "K001")
    assert result.agent_actions == (
        "match:listwise-canonical",
        "retrieve-verify:canonical",
        "escalate:disagreement",
        "retrieve-verify:reverse",
        "retrieve-verify:rotate-7",
        "aggregate:m3-majority-canonical-tie",
    )
    _assert_every_call_carries_query(client)


def test_m5_three_way_m3_tie_falls_back_to_canonical_m3_decision():
    cards = (
        *_KEY_CARDS,
        KeyCardV1(
            key_id="K003",
            definition="Commands about calendar events.",
            positive_examples=("add a meeting",),
            contrastive_boundary="Do not use for alarms.",
            value_label="calendar",
        ).validate(),
    )
    responses = ['{"key_id":"K001"}']
    for winner, others in (
        ("K002", ("K001",)),
        ("K003", ("K002",)),
        ("K001", ("K003",)),
    ):
        responses.extend(
            [
                json.dumps({"key_ids": [winner, *others]}),
                '{"compatible":true,"confidence":90}',
                '{"compatible":false,"confidence":10}',
            ]
        )
    client = _SpeechFeatureClient(responses)
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=cards,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )

    assert result.key_id == "K002"
    assert result.agent_vote_key_ids == ("K001", "K002", "K003", "K001")
    _assert_every_call_carries_query(client)


def test_m5_primary_fallback_requires_m3_consensus_before_overriding_m1():
    cards = (
        *_KEY_CARDS,
        KeyCardV1(
            key_id="K003",
            definition="Commands about calendar events.",
            positive_examples=("add a meeting",),
            contrastive_boundary="Do not use for alarms.",
            value_label="calendar",
        ).validate(),
    )
    responses = ['{"key_id":"K001"}']
    for winner, other in (("K002", "K001"), ("K003", "K002"), ("K001", "K003")):
        responses.extend(
            [
                json.dumps({"key_ids": [winner, other]}),
                '{"compatible":true,"confidence":90}',
                '{"compatible":false,"confidence":10}',
            ]
        )
    client = _SpeechFeatureClient(responses)
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=cards,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
        agent_aggregator_id="m3-majority-primary-tie-v2",
    )

    assert result.key_id == "K001"
    assert result.agent_aggregator_id == "m3-majority-primary-tie-v2"
    assert result.agent_actions[-1] == "aggregate:m3-majority-primary-tie"
    _assert_every_call_carries_query(client)


def test_m5_unanimous_policy_overrides_primary_only_with_all_three_m3_votes():
    client = _SpeechFeatureClient(
        [
            '{"key_id":"K001"}',
            *(
                response
                for _ in range(3)
                for response in (
                    '{"key_ids":["K002","K001"]}',
                    '{"compatible":true,"confidence":90}',
                    '{"compatible":false,"confidence":10}',
                )
            ),
        ]
    )
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )

    assert result.key_id == "K002"
    assert result.agent_actions[-1] == "aggregate:m3-unanimous-primary-fallback"
    _assert_every_call_carries_query(client)


def test_audio_key_mode_carries_ordered_key_packets_without_key_body_text():
    client = _SpeechFeatureClient(['{"key_id":"K001"}'])
    audio_keys = {
        "K001": {"packet_id": "slurp/train/key-1", "sha256": "b" * 64},
        "K002": {"packet_id": "slurp/train/key-2", "sha256": "c" * 64},
    }
    run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K3",
        matcher_policy_id="M1",
        audio_key_bindings=audio_keys,
    )
    parts = client.calls[0][0][1]["content"]
    key_parts = [
        part["speech_features"]
        for part in parts
        if part.get("type") == "input_speech_features"
    ][1:]
    assert [part["packet_id"] for part in key_parts] == [
        "slurp/train/key-1",
        "slurp/train/key-2",
    ]
    assert all(part["role"] == "key" for part in key_parts)
    text = "\n".join(part["text"] for part in parts if part.get("type") == "text")
    assert "wake me at six" not in text


def test_speech_native_match_tasks_keep_multistep_slot_affinity_and_flush_in_task_order(
    tmp_path,
):
    run_id = "SAEA-E-TEST-speech-native-batch"
    sink = TraceSink(tmp_path / "trace", run_id)
    dispatcher = DispatchingSink(sink)

    class ConcurrentClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.calls_by_sample = {}
            self.sequence = 0

        def complete(self, messages, **kwargs):
            sample_id = kwargs["speech_feature_sample_id"]
            slot = kwargs["decoding_params"]["id_slot"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.calls_by_sample.setdefault(sample_id, []).append(slot)
                self.sequence += 1
                sequence = self.sequence
            dispatcher.emit(
                "OBS",
                f"batch-{sequence:04d}/obs",
                {"obs_sample_id": sample_id},
            )
            time.sleep(0.02 if sample_id.endswith("0") else 0.005)
            with self.lock:
                self.active -= 1
            if kwargs["matcher_policy_id"].endswith(":intent-factors"):
                return '{"factors":["domain"],"summary":"command"}'
            return '{"key_id":"K001"}'

    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"task-{index}",
            sample=Sample(f"sample-{index}"),
            query_descriptor={
                "packet_id": f"slurp/train/query-{index}",
                "sha256": f"{index + 1:x}" * 64,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K2",
            matcher_policy_id="M2",
            decoding_params={"temperature": 0, "id_slot": "per-sample"},
        )
        for index in range(4)
    )
    client = ConcurrentClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=2,
        trace_run_id=run_id,
        trace_flusher=lambda buffer: buffer.flush_into(sink),
    )
    sink.close()

    assert [outcome.task_id for outcome in outcomes] == [task.task_id for task in tasks]
    assert all(outcome.decision.value_label == "alarm" for outcome in outcomes)
    assert client.max_active == 2
    assert all(len(set(slots)) == 1 for slots in client.calls_by_sample.values())
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / "trace" / f"{run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["payload"]["obs_sample_id"] for row in trace_rows] == [
        sample_id
        for sample_id in (f"sample-{index}" for index in range(4))
        for _ in range(2)
    ]


def test_speech_native_contact_dispatch_queues_each_multistep_call_independently():
    class ContactClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.stages = []

        def complete(self, messages, **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.stages.append(kwargs["matcher_policy_id"])
            time.sleep(0.01)
            with self.lock:
                self.active -= 1
            if kwargs["matcher_policy_id"].endswith(":intent-factors"):
                return '{"factors":["domain"],"summary":"command"}'
            return '{"key_id":"K001"}'

    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"task-{index}",
            sample=Sample(f"sample-{index}"),
            query_descriptor={
                "packet_id": f"slurp/train/query-{index}",
                "sha256": f"{index + 1:x}" * 64,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K2",
            matcher_policy_id="M2",
            decoding_params={"temperature": 0, "id_slot": "per-sample"},
        )
        for index in range(4)
    )
    client = ContactClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )
    assert client.max_active == 2
    assert all(stage.endswith(":intent-factors") for stage in client.stages[:4])
    assert all(outcome.slot_id == -1 for outcome in outcomes)


def test_contact_dispatch_parallelizes_independent_m3_verifier_contacts():
    class ParallelVerifierClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(0.02)
            with self.lock:
                self.active -= 1
            if stage.endswith(":retrieve-top-2"):
                return '{"key_ids":["K001","K002"]}'
            if stage.endswith(":verify-K001"):
                return '{"compatible":true,"confidence":90}'
            if stage.endswith(":verify-K002"):
                return '{"compatible":false,"confidence":10}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M3",
        prompt_policy_id="speech-native-json-copy-v3",
        decoding_params={"temperature": 0, "id_slot": "per-sample"},
        top_k=2,
    )
    client = ParallelVerifierClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=(task,),
        slot_count=2,
        queue_depth=2,
        dispatch_granularity="contact",
    )

    assert outcomes[0].decision.key_id == "K001"
    assert client.max_active == 2


def test_parallel_verifier_traces_merge_in_candidate_order(tmp_path):
    run_id = "SAEA-E-TEST-parallel-verifier-trace"
    sink = TraceSink(tmp_path / "trace", run_id)
    dispatcher = DispatchingSink(sink)

    class TracedVerifierClient:
        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            dispatcher.emit("MODEL_REQUEST", stage, {"stage": stage})
            if stage.endswith(":retrieve-top-2"):
                return '{"key_ids":["K001","K002"]}'
            if stage.endswith(":verify-K001"):
                time.sleep(0.02)
                return '{"compatible":true,"confidence":90}'
            if stage.endswith(":verify-K002"):
                return '{"compatible":false,"confidence":10}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M3",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=2,
    )
    run_speech_native_match_tasks(
        core_client=TracedVerifierClient(),
        tasks=(task,),
        slot_count=2,
        queue_depth=2,
        dispatch_granularity="contact",
        trace_run_id=run_id,
        trace_flusher=lambda buffer: buffer.flush_into(sink),
    )
    sink.close()

    rows = [
        json.loads(line)
        for line in (tmp_path / "trace" / f"{run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["payload"]["stage"].rsplit(":", 1)[-1] for row in rows] == [
        "retrieve-top-2",
        "verify-K001",
        "verify-K002",
    ]


def test_contact_dispatch_parallelizes_independent_m5_initial_branches():
    class ParallelBranchClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.initial_barrier = threading.Barrier(2)
            self.active = 0
            self.max_active = 0

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            if stage.endswith((":listwise", ":retrieve-top-1")):
                self.initial_barrier.wait(timeout=1)
            time.sleep(0.02)
            with self.lock:
                self.active -= 1
            if stage.endswith(":listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-1"):
                return '{"key_ids":["K001"]}'
            if stage.endswith(":verify-K001"):
                return '{"compatible":true,"confidence":90}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        decoding_params={"temperature": 0, "id_slot": "per-sample"},
        top_k=1,
    )
    client = ParallelBranchClient()
    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=(task,),
        slot_count=2,
        queue_depth=2,
        dispatch_granularity="contact",
    )

    assert outcomes[0].decision.key_id == "K001"
    assert client.max_active == 2


def test_full_branch_contact_dispatch_schedules_all_four_branches_globally():
    class FullBranchClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.stages = []
            self.calls = []

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.stages.append(stage)
                self.calls.append((messages, kwargs))
            time.sleep(0.02)
            with self.lock:
                self.active -= 1
            if stage.endswith(":listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-1"):
                key_id = "K002" if ":reverse:" in stage else "K001"
                return json.dumps({"key_ids": [key_id]})
            if ":verify-" in stage:
                return '{"compatible":true,"confidence":90}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        decoding_params={"temperature": 0, "id_slot": "per-sample"},
        top_k=1,
        agent_policy_id="m1-m3-full-branch-explorer-v1",
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )
    client = FullBranchClient()

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=(task,),
        slot_count=4,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    decision = outcomes[0].decision
    assert client.max_active == 4
    assert decision.key_id == "K001"
    assert decision.calls == 7
    assert decision.agent_vote_key_ids == ("K001", "K001", "K002", "K001")
    assert decision.agent_actions == (
        "match:listwise-canonical",
        "retrieve-verify:canonical",
        "explore:full-branch",
        "retrieve-verify:reverse",
        "retrieve-verify:rotate-7",
        "aggregate:m3-unanimous-primary-fallback",
    )
    assert all(outcome.slot_id == -1 for outcome in outcomes)
    _assert_every_call_carries_query(client)


def test_full_branch_contact_dispatch_uses_one_persistent_executor(monkeypatch):
    real_executor = pslu_module.ThreadPoolExecutor
    prefixes = []

    class RecordingExecutor:
        def __init__(self, *args, **kwargs):
            prefixes.append(kwargs.get("thread_name_prefix"))
            self.delegate = real_executor(*args, **kwargs)

        def submit(self, *args, **kwargs):
            return self.delegate.submit(*args, **kwargs)

        def shutdown(self, *args, **kwargs):
            return self.delegate.shutdown(*args, **kwargs)

        def __enter__(self):
            self.delegate.__enter__()
            return self

        def __exit__(self, *args):
            return self.delegate.__exit__(*args)

    class FullBranchClient:
        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            if stage.endswith(":listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-1"):
                return '{"key_ids":["K001"]}'
            if ":verify-" in stage:
                return '{"compatible":true,"confidence":90}'
            raise AssertionError(stage)

    monkeypatch.setattr(pslu_module, "ThreadPoolExecutor", RecordingExecutor)
    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=1,
        agent_policy_id="m1-m3-full-branch-explorer-v1",
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )

    outcomes = run_speech_native_match_tasks(
        core_client=FullBranchClient(),
        tasks=(task,),
        slot_count=4,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    assert outcomes[0].decision.key_id == "K001"
    assert prefixes == ["saea-speech-native-contact"]


def test_full_branch_stage_dag_bounds_submitted_contacts_by_queue_depth(monkeypatch):
    real_executor = pslu_module.ThreadPoolExecutor
    instances = []

    class TrackingExecutor:
        def __init__(self, *args, **kwargs):
            self.prefix = kwargs.get("thread_name_prefix")
            self.delegate = real_executor(*args, **kwargs)
            self.lock = threading.Lock()
            self.pending = 0
            self.max_pending = 0
            instances.append(self)

        def submit(self, *args, **kwargs):
            with self.lock:
                self.pending += 1
                self.max_pending = max(self.max_pending, self.pending)
            future = self.delegate.submit(*args, **kwargs)

            def complete(_future):
                with self.lock:
                    self.pending -= 1

            future.add_done_callback(complete)
            return future

        def shutdown(self, *args, **kwargs):
            return self.delegate.shutdown(*args, **kwargs)

        def __enter__(self):
            self.delegate.__enter__()
            return self

        def __exit__(self, *args):
            return self.delegate.__exit__(*args)

    class FullBranchClient:
        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            time.sleep(0.005)
            if stage.endswith(":listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-2"):
                return '{"key_ids":["K001","K002"]}'
            if ":verify-" in stage:
                return '{"compatible":true,"confidence":90}'
            return '{"key_id":"K001"}'

    monkeypatch.setattr(pslu_module, "ThreadPoolExecutor", TrackingExecutor)
    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"task-{index}",
            sample=type("Sample", (), {"sample_id": f"sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/sample-{index}",
                "sha256": f"{index + 1:x}" * 64,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M5",
            prompt_policy_id="speech-native-json-copy-v3",
            top_k=2,
            agent_policy_id="m1-m3-full-branch-explorer-v1",
            agent_aggregator_id="m3-unanimous-primary-fallback-v3",
        )
        for index in range(4)
    )

    outcomes = run_speech_native_match_tasks(
        core_client=FullBranchClient(),
        tasks=tasks,
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    contact_executor = next(
        item for item in instances if item.prefix == "saea-speech-native-contact"
    )
    assert len(outcomes) == 4
    assert contact_executor.max_pending <= 4


def test_generic_contact_dispatch_bounds_submitted_contacts_by_queue_depth(monkeypatch):
    real_executor = pslu_module.ThreadPoolExecutor
    instances = []

    class TrackingExecutor:
        def __init__(self, *args, **kwargs):
            self.prefix = kwargs.get("thread_name_prefix")
            self.delegate = real_executor(*args, **kwargs)
            self.lock = threading.Lock()
            self.pending = 0
            self.max_pending = 0
            instances.append(self)

        def submit(self, *args, **kwargs):
            with self.lock:
                self.pending += 1
                self.max_pending = max(self.max_pending, self.pending)
            future = self.delegate.submit(*args, **kwargs)

            def complete(_future):
                with self.lock:
                    self.pending -= 1

            future.add_done_callback(complete)
            return future

        def shutdown(self, *args, **kwargs):
            return self.delegate.shutdown(*args, **kwargs)

        def __enter__(self):
            self.delegate.__enter__()
            return self

        def __exit__(self, *args):
            return self.delegate.__exit__(*args)

    class SlowM7Client(_M7BatchClient):
        def complete(self, messages, **kwargs):
            time.sleep(0.005)
            return super().complete(messages, **kwargs)

    monkeypatch.setattr(pslu_module, "ThreadPoolExecutor", TrackingExecutor)
    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m7-task-{index}",
            sample=type("Sample", (), {"sample_id": f"m7-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m7-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M7",
            prompt_policy_id="speech-native-json-copy-v3",
            verifier_policy_id="speech-native-contrastive-verifier-v2",
            top_k=2,
            agent_policy_id="knowledge-grounded-multistate-action-support-v1",
            agent_aggregator_id="action-support-primary-control-v1",
        )
        for index in range(4)
    )

    outcomes = run_speech_native_match_tasks(
        core_client=SlowM7Client(),
        tasks=tasks,
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    contact_executor = next(
        item for item in instances if item.prefix == "saea-speech-native-contact"
    )
    assert len(outcomes) == 4
    assert contact_executor.max_pending <= 4


def test_full_branch_stage_dag_replay_fills_all_slots_across_stage_transitions():
    class LatencyReplayClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.calls = []

        def complete(self, messages, **kwargs):
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.calls.append((messages, kwargs))
            try:
                time.sleep(0.003)
                stage = kwargs["matcher_policy_id"]
                if stage.endswith(":listwise"):
                    return '{"key_id":"K001"}'
                if stage.endswith(":retrieve-top-2"):
                    return '{"key_ids":["K001","K002"]}'
                if ":verify-K001" in stage:
                    return '{"compatible":true,"confidence":90}'
                if ":verify-K002" in stage:
                    return '{"compatible":false,"confidence":20}'
                raise AssertionError(stage)
            finally:
                with self.lock:
                    self.active -= 1

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"replay-{index}",
            sample=type("Sample", (), {"sample_id": f"replay-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/replay-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M5",
            prompt_policy_id="speech-native-json-copy-v3",
            top_k=2,
            agent_policy_id="m1-m3-full-branch-explorer-v1",
            agent_aggregator_id="m3-unanimous-primary-fallback-v3",
        )
        for index in range(12)
    )
    client = LatencyReplayClient()

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=4,
        queue_depth=8,
        dispatch_granularity="contact",
    )

    assert len(outcomes) == 12
    assert client.max_active == 4
    assert all(outcome.decision.key_id == "K001" for outcome in outcomes)
    assert all(outcome.decision.calls == 10 for outcome in outcomes)
    assert len(client.calls) == 120
    for messages, kwargs in client.calls:
        query_parts = [
            part["speech_features"]
            for part in messages[1]["content"]
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert len(query_parts) == 1
        assert query_parts[0]["packet_id"].endswith(kwargs["speech_feature_sample_id"])


def test_global_full_branch_traces_merge_in_registered_branch_order(tmp_path):
    run_id = "SAEA-E-TEST-global-full-branch-trace"
    sink = TraceSink(tmp_path / "trace", run_id)
    dispatcher = DispatchingSink(sink)

    class TracedFullBranchClient:
        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            dispatcher.emit("MODEL_REQUEST", stage, {"stage": stage})
            if stage.endswith(":listwise"):
                time.sleep(0.03)
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-1"):
                key_id = "K002" if ":reverse:" in stage else "K001"
                return json.dumps({"key_ids": [key_id]})
            if ":verify-" in stage:
                return '{"compatible":true,"confidence":90}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=1,
        agent_policy_id="m1-m3-full-branch-explorer-v1",
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )
    run_speech_native_match_tasks(
        core_client=TracedFullBranchClient(),
        tasks=(task,),
        slot_count=4,
        queue_depth=4,
        dispatch_granularity="contact",
        trace_run_id=run_id,
        trace_flusher=lambda buffer: buffer.flush_into(sink),
    )
    sink.close()

    rows = [
        json.loads(line)
        for line in (tmp_path / "trace" / f"{run_id}.trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [row["payload"]["stage"] for row in rows] == [
        "M5:M1:canonical:listwise",
        "M5:M3:canonical:retrieve-top-1",
        "M5:M3:canonical:verify-K001",
        "M5:M3:reverse:retrieve-top-1",
        "M5:M3:reverse:verify-K002",
        "M5:M3:rotate-7:retrieve-top-1",
        "M5:M3:rotate-7:verify-K001",
    ]


def test_full_branch_stage_dag_never_retries_a_failed_contact():
    class FailingFullBranchClient:
        def __init__(self):
            self.calls = []
            self.stage_counts = {}

        def complete(self, messages, **kwargs):
            stage = kwargs["matcher_policy_id"]
            self.calls.append((messages, kwargs))
            self.stage_counts[stage] = self.stage_counts.get(stage, 0) + 1
            if stage == "M5:M3:reverse:verify-K001":
                raise RuntimeError("registered verifier failure")
            if stage.endswith(":listwise"):
                return '{"key_id":"K001"}'
            if stage.endswith(":retrieve-top-1"):
                return '{"key_ids":["K001"]}'
            if ":verify-" in stage:
                return '{"compatible":true,"confidence":90}'
            raise AssertionError(stage)

    task = SpeechNativeMatchTask(
        task_id="task-0",
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M5",
        prompt_policy_id="speech-native-json-copy-v3",
        top_k=1,
        agent_policy_id="m1-m3-full-branch-explorer-v1",
        agent_aggregator_id="m3-unanimous-primary-fallback-v3",
    )
    client = FailingFullBranchClient()

    with pytest.raises(RuntimeError, match="registered verifier failure"):
        run_speech_native_match_tasks(
            core_client=client,
            tasks=(task,),
            slot_count=4,
            queue_depth=4,
            dispatch_granularity="contact",
        )

    assert client.stage_counts["M5:M3:reverse:verify-K001"] == 1
    _assert_every_call_carries_query(client)


def test_speech_native_match_tasks_reject_queue_smaller_than_slot_pool():
    with pytest.raises(
        PsluFlightError, match="queue_depth must be at least slot_count"
    ):
        run_speech_native_match_tasks(
            core_client=object(),
            tasks=(),
            slot_count=2,
            queue_depth=1,
        )


def test_speech_native_match_tasks_never_retry_a_failed_task():
    class FailingClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, **kwargs):
            sample_id = kwargs["speech_feature_sample_id"]
            self.calls.append(sample_id)
            if sample_id == "sample-fail":
                raise RuntimeError("registered one-shot failure")
            return '{"key_id":"K001"}'

    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=sample_id,
            sample=Sample(sample_id),
            query_descriptor={
                "packet_id": f"slurp/train/{sample_id}",
                "sha256": digest,
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K2",
            matcher_policy_id="M1",
            decoding_params={"id_slot": "per-sample"},
        )
        for sample_id, digest in (("sample-ok", "a" * 64), ("sample-fail", "b" * 64))
    )
    client = FailingClient()
    with pytest.raises(RuntimeError, match="registered one-shot failure"):
        run_speech_native_match_tasks(
            core_client=client,
            tasks=tasks,
            slot_count=2,
            queue_depth=2,
        )
    assert sorted(client.calls) == ["sample-fail", "sample-ok"]


def test_profile_task_expansion_and_slot_metrics_are_deterministic():
    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    samples = (Sample("s1"), Sample("s2"))
    bindings = {
        "s1": {"packet_id": "slurp/train/s1", "sha256": "a" * 64},
        "s2": {"packet_id": "slurp/train/s2", "sha256": "b" * 64},
    }
    tasks = build_profile_tasks(
        samples=samples,
        packet_bindings=bindings,
        key_cards=_KEY_CARDS,
        order_ids=("canonical", "reverse"),
        decoding_params={"temperature": 0, "id_slot": "per-sample"},
        key_representation_id="K2",
        matcher_policy_id="M1",
        agent_policy_id="m1-m3-full-branch-explorer-v1",
    )
    assert [task.task_id for task in tasks] == [
        "canonical:s1",
        "canonical:s2",
        "reverse:s1",
        "reverse:s2",
    ]
    assert [card.key_id for card in tasks[2].key_cards] == ["K002", "K001"]
    assert all(
        task.agent_policy_id == "m1-m3-full-branch-explorer-v1" for task in tasks
    )
    metrics = profile_timing_metrics(
        (
            {
                "started_at": "2026-08-21T12:00:00+00:00",
                "latency_seconds": 2.0,
            },
            {
                "started_at": "2026-08-21T12:00:00+00:00",
                "latency_seconds": 2.0,
            },
        ),
        slot_count=2,
        prompt_tokens=180,
        completion_tokens=20,
    )
    assert metrics == {
        "request_window_seconds": 2.0,
        "slot_occupancy_pct": 100.0,
        "aggregate_tokens_per_second": 100.0,
    }


def test_decision_graph_artifact_is_hash_pinned_and_enters_profile_tasks(tmp_path):
    graph = _decision_graph_fixture()
    graph_path = tmp_path / "decision-graph.json"
    graph_path.write_text(
        json.dumps(graph.as_json(), sort_keys=True) + "\n", encoding="utf-8"
    )
    graph_sha256 = hashlib.sha256(graph_path.read_bytes()).hexdigest()

    loaded = _load_decision_graph(
        graph_path,
        expected_sha256=graph_sha256,
        key_cards=_KEY_CARDS,
    )
    tasks = build_profile_tasks(
        samples=(type("Sample", (), {"sample_id": "s1"})(),),
        packet_bindings={"s1": {"packet_id": "slurp/train/s1", "sha256": "a" * 64}},
        key_cards=_KEY_CARDS,
        order_ids=("canonical",),
        decoding_params={"temperature": 0},
        key_representation_id="K1",
        matcher_policy_id="M9",
        prompt_policy_id="speech-native-json-copy-v4",
        top_k=2,
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=loaded,
    )

    assert loaded == graph
    assert tasks[0].decision_graph == graph
    with pytest.raises(SpeechNativeProfileError, match="SHA-256 mismatch"):
        _load_decision_graph(
            graph_path,
            expected_sha256="0" * 64,
            key_cards=_KEY_CARDS,
        )


def test_m10_profile_tasks_reuse_the_pinned_decision_graph():
    graph = _decision_graph_fixture()
    tasks = build_profile_tasks(
        samples=(type("Sample", (), {"sample_id": "s1"})(),),
        packet_bindings={"s1": {"packet_id": "slurp/train/s1", "sha256": "a" * 64}},
        key_cards=_KEY_CARDS,
        order_ids=("canonical",),
        decoding_params={"temperature": 0},
        key_representation_id="K1",
        matcher_policy_id="M10",
        prompt_policy_id="speech-native-json-copy-v4",
        top_k=2,
        agent_policy_id="speech-conditioned-candidate-evidence-action-support-v1",
        agent_aggregator_id="candidate-evidence-primary-control-v1",
        decision_graph=graph,
    )
    assert tasks[0].decision_graph == graph


def test_m11_profile_tasks_reuse_the_data_derived_decision_graph():
    graph = _decision_graph_fixture()
    tasks = build_profile_tasks(
        samples=(type("Sample", (), {"sample_id": "s1"})(),),
        packet_bindings={"s1": {"packet_id": "slurp/train/s1", "sha256": "a" * 64}},
        key_cards=_KEY_CARDS,
        order_ids=("canonical",),
        decoding_params={"temperature": 0},
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        top_k=2,
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v1",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=graph,
    )
    assert tasks[0].decision_graph == graph


def test_training_free_policy_search_uses_complete_action_support():
    frontier = _evaluate_training_free_agent_policies(
        (
            {
                "speaker_id": "speaker-a",
                "gold_key_id": "K001",
                "primary_key_id": "K001",
                "canonical_key_id": "K001",
                "reverse_key_id": "K002",
                "rotate_key_id": "K002",
            },
            {
                "speaker_id": "speaker-b",
                "gold_key_id": "K002",
                "primary_key_id": "K001",
                "canonical_key_id": "K002",
                "reverse_key_id": "K002",
                "rotate_key_id": "K002",
            },
            {
                "speaker_id": "speaker-c",
                "gold_key_id": "K003",
                "primary_key_id": "K003",
                "canonical_key_id": "K003",
                "reverse_key_id": "K002",
                "rotate_key_id": "K002",
            },
            {
                "speaker_id": "speaker-d",
                "gold_key_id": "K002",
                "primary_key_id": "K001",
                "canonical_key_id": "K002",
                "reverse_key_id": "K002",
                "rotate_key_id": "K003",
            },
        )
    )

    by_policy = {row["policy_id"]: row for row in frontier}
    disagreement = by_policy["trigger-disagreement__m3-majority-primary-v1"]
    assert disagreement["correct"] == 4
    assert disagreement["count"] == 4
    assert disagreement["accuracy"] == 1.0
    assert disagreement["wrong_to_correct_vs_primary"] == 2
    assert disagreement["correct_to_wrong_vs_primary"] == 0
    assert disagreement["branch_action_count"] == 2
    assert disagreement["branch_action_rate"] == 0.5
    assert disagreement["speaker_fold_policy_id"] == (
        "speaker-grouped-3fold-sha256-load-balanced-v1"
    )
    assert sum(fold["count"] for fold in disagreement["speaker_folds"]) == 4
    assert sum(fold["speaker_count"] for fold in disagreement["speaker_folds"]) == 4
    assert disagreement["positive_delta_fold_count"] >= 1
    assert by_policy["trigger-never__primary-v1"]["correct"] == 2
    assert (
        by_policy["trigger-always__m3-majority-primary-v1"][
            "correct_to_wrong_vs_primary"
        ]
        == 2
    )


def test_training_free_contextual_policy_is_speaker_grouped_and_out_of_fold():
    trajectories = []
    for index in range(9):
        trajectories.append(
            {
                "speaker_id": f"speaker-{index}",
                "gold_key_id": "K002",
                "primary_key_id": "K001",
                "canonical_key_id": "K002",
                "reverse_key_id": "K002",
                "rotate_key_id": "K002",
            }
        )

    evaluation = _evaluate_training_free_contextual_policy(tuple(trajectories))

    assert evaluation["policy_id"] == ("speaker-grouped-oof-observable-state-action-v1")
    assert evaluation["correct"] == 9
    assert evaluation["primary_correct"] == 0
    assert evaluation["wrong_to_correct_vs_primary"] == 9
    assert evaluation["correct_to_wrong_vs_primary"] == 0
    assert evaluation["action_oracle_correct"] == 9
    assert evaluation["action_oracle_headroom_vs_primary"] == 9
    assert evaluation["reward_spread_state_count"] == 1
    assert evaluation["oof_action_counts"] == {"m3-unanimous-primary-fallback": 9}
    assert len(evaluation["speaker_folds"]) == 3
    assert sum(fold["count"] for fold in evaluation["speaker_folds"]) == 9
    assert all(
        fold["correct_delta_vs_primary"] > 0 for fold in evaluation["speaker_folds"]
    )


def test_training_free_contextual_policy_keeps_repeated_speaker_in_one_fold():
    trajectories = tuple(
        {
            "speaker_id": "shared-speaker" if index < 3 else f"speaker-{index}",
            "gold_key_id": "K001",
            "primary_key_id": "K001",
            "canonical_key_id": "K001",
            "reverse_key_id": "K001",
            "rotate_key_id": "K001",
        }
        for index in range(8)
    )

    evaluation = _evaluate_training_free_contextual_policy(trajectories)
    assignments = {
        item["speaker_id"]: item["fold_id"]
        for item in evaluation["speaker_fold_assignments"]
    }

    assert assignments["shared-speaker"] in {"fold-0", "fold-1", "fold-2"}
    shared_fold = next(
        fold
        for fold in evaluation["speaker_folds"]
        if fold["fold_id"] == assignments["shared-speaker"]
    )
    assert shared_fold["count"] >= 3


def _episodic_trajectory(index, *, primary_correct, candidate_correct):
    primary_key = "K001"
    candidate_key = "K002"
    gold_key = primary_key if primary_correct else candidate_key
    if not candidate_correct:
        candidate_key = "K003" if not primary_correct else "K002"
    return {
        "sample_id": f"sample-{index}",
        "speaker_id": f"speaker-{index}",
        "gold_key_id": gold_key,
        "primary_key_id": primary_key,
        "canonical_key_id": candidate_key,
        "reverse_key_id": candidate_key,
        "rotate_key_id": candidate_key,
        "canonical_top_key_ids": (candidate_key, primary_key),
        "canonical_verifier_scores": {
            candidate_key: (True, 90.0),
            primary_key: (False, 80.0),
        },
        "primary_calls": 1,
        "canonical_calls": 3,
        "reverse_calls": 3,
        "rotate_calls": 3,
    }


def test_training_free_episodic_policy_retrieves_action_advantage_out_of_fold():
    trajectories = tuple(
        _episodic_trajectory(
            index,
            primary_correct=False,
            candidate_correct=True,
        )
        for index in range(12)
    )

    evaluation = _evaluate_training_free_episodic_policy(trajectories)

    assert evaluation["policy_id"] == (
        "speaker-grouped-oof-episodic-action-advantage-v2"
    )
    assert evaluation["correct"] == 12
    assert evaluation["primary_correct"] == 0
    assert evaluation["wrong_to_correct_vs_primary"] == 12
    assert evaluation["correct_to_wrong_vs_primary"] == 0
    assert evaluation["positive_delta_fold_count"] == 3
    assert evaluation["oof_action_counts"] == {"canonical-primary-fallback": 12}
    assert evaluation["mean_contacts"] == 4.0


def test_training_free_episodic_policy_rejects_neighbors_with_observed_harm():
    trajectories = tuple(
        _episodic_trajectory(
            index,
            primary_correct=index < 6,
            candidate_correct=index >= 6,
        )
        for index in range(9)
    )

    evaluation = _evaluate_training_free_episodic_policy(trajectories)

    assert evaluation["correct"] == 6
    assert evaluation["primary_correct"] == 6
    assert evaluation["wrong_to_correct_vs_primary"] == 0
    assert evaluation["correct_to_wrong_vs_primary"] == 0
    assert evaluation["oof_action_counts"] == {"primary": 9}


def _grounded_semantic_trajectory(
    index, *, primary_correct, refined_correct, semantic_cluster="alarm schedule"
):
    primary_key = "K001"
    refined_key = "K002"
    gold_key = primary_key if primary_correct else refined_key
    if not refined_correct:
        refined_key = "K003" if not primary_correct else "K002"
    words = semantic_cluster.split()
    return {
        "sample_id": f"sample-{index:02d}",
        "speaker_id": f"speaker-{index:02d}",
        "gold_key_id": gold_key,
        "primary_key_id": primary_key,
        "refined_key_id": refined_key,
        "initial_top_key_ids": (primary_key, refined_key, "K004"),
        "refined_top_key_ids": (refined_key, primary_key, "K004"),
        "verifier_scores": {
            refined_key: (True, 90.0),
            primary_key: (False, 40.0),
            "K004": (False, 20.0),
        },
        "grounded_query_state": {
            "domain": words[0],
            "operation": words[-1],
            "target": "weekday",
            "constraints": ["morning"],
            "exclusions": ["cancel"],
            "unresolved_ambiguity": "none",
        },
        "total_calls": 7,
    }


def test_training_free_grounded_semantic_policy_accepts_supported_helpful_memory():
    trajectories = tuple(
        _grounded_semantic_trajectory(
            index,
            primary_correct=False,
            refined_correct=True,
        )
        for index in range(12)
    )

    evaluation = _evaluate_training_free_grounded_semantic_policy(trajectories)

    assert evaluation["policy_id"] == (
        "speaker-grouped-oof-grounded-semantic-action-advantage-v1"
    )
    assert evaluation["correct"] == 12
    assert evaluation["primary_correct"] == 0
    assert evaluation["wrong_to_correct_vs_primary"] == 12
    assert evaluation["correct_to_wrong_vs_primary"] == 0
    assert evaluation["oof_action_counts"] == {"accept_refined": 12}
    assert evaluation["positive_delta_fold_count"] == 3
    assert evaluation["mean_realized_contacts"] == 7.0


def test_training_free_grounded_semantic_policy_rejects_memory_with_harm():
    trajectories = tuple(
        _grounded_semantic_trajectory(
            index,
            primary_correct=True,
            refined_correct=False,
        )
        for index in range(12)
    )

    evaluation = _evaluate_training_free_grounded_semantic_policy(trajectories)

    assert evaluation["correct"] == 12
    assert evaluation["primary_correct"] == 12
    assert evaluation["wrong_to_correct_vs_primary"] == 0
    assert evaluation["correct_to_wrong_vs_primary"] == 0
    assert evaluation["oof_action_counts"] == {"retain_primary": 12}
    assert evaluation["action_oracle_correct"] == 12


def test_profile_tasks_build_label_blind_speech_swap_and_key_text_shuffle_controls():
    class Sample:
        def __init__(self, sample_id):
            self.sample_id = sample_id

    samples = tuple(Sample(f"s{index}") for index in range(3))
    bindings = {
        sample.sample_id: {
            "packet_id": f"slurp/train/{sample.sample_id}",
            "sha256": f"{index + 1:x}" * 64,
        }
        for index, sample in enumerate(samples)
    }
    swapped = build_profile_tasks(
        samples=samples,
        packet_bindings=bindings,
        key_cards=_KEY_CARDS,
        order_ids=("canonical",),
        decoding_params={},
        key_representation_id="K1",
        matcher_policy_id="M1",
        mechanism_control_id="speech-swap-v1",
    )
    assert [task.scoring_sample_id for task in swapped] == ["s0", "s1", "s2"]
    assert [task.sample.sample_id for task in swapped] == ["s1", "s2", "s0"]

    shuffled = build_profile_tasks(
        samples=samples,
        packet_bindings=bindings,
        key_cards=_KEY_CARDS,
        order_ids=("canonical",),
        decoding_params={},
        key_representation_id="K1",
        matcher_policy_id="M1",
        mechanism_control_id="key-text-shuffle-v1",
    )
    first_cards = shuffled[0].key_cards
    assert [card.key_id for card in first_cards] == ["K001", "K002"]
    assert [card.value_label for card in first_cards] == ["alarm", "email"]
    assert first_cards[0].definition == _KEY_CARDS[1].definition
    assert first_cards[1].definition == _KEY_CARDS[0].definition


def test_audio_key_bindings_resolve_frozen_key_sources_from_packet_index():
    binding = {
        "key_material": [
            {
                "key_id": "K001",
                "audio_key_source_sample_id": "slurp:train:000001:audio-1",
            },
            {
                "key_id": "K002",
                "audio_key_source_sample_id": "slurp:train:000002:audio-2",
            },
        ]
    }
    packet_index = {
        "slurp/train/000001/audio-1": {
            "packet_id": "slurp/train/000001/audio-1",
            "sha256": "a" * 64,
        },
        "slurp/train/000002/audio-2": {
            "packet_id": "slurp/train/000002/audio-2",
            "sha256": "b" * 64,
        },
    }
    assert _build_audio_key_bindings(binding, packet_index, _KEY_CARDS) == {
        "K001": {
            "packet_id": "slurp/train/000001/audio-1",
            "sha256": "a" * 64,
        },
        "K002": {
            "packet_id": "slurp/train/000002/audio-2",
            "sha256": "b" * 64,
        },
    }


def test_model_free_prediction_read_verifies_and_selects_the_better_cell(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {
        card["value_label"]: card["key_id"] for card in binding["key_cards"]
    }

    def write_cell(cell_id, *, make_first_wrong, top_k=3):
        key_representation_id, matcher_policy_id = cell_id.split("-")
        attempt_dir = tmp_path / cell_id
        attempt_dir.mkdir()
        rows = []
        for index, item in enumerate(items):
            key_id = key_by_label[item["value_label"]]
            if index == 0 and make_first_wrong:
                key_id = next(
                    candidate
                    for candidate in key_by_label.values()
                    if candidate != key_id
                )
            predicted = next(
                card["value_label"]
                for card in binding["key_cards"]
                if card["key_id"] == key_id
            )
            rows.append(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "sample_id": item["sample_id"],
                    "key_id": key_id,
                    "predicted_value_label": predicted,
                    "parse_failure": False,
                }
            )
        decisions = attempt_dir / "decisions.jsonl"
        decisions.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        digest = hashlib.sha256(decisions.read_bytes()).hexdigest()
        receipt = {
            "status": "COMPLETED",
            "request_failures": [],
            "split_identity_hash": "a" * 64,
            "run_id": f"run-{cell_id}",
            "profile": {
                "key_representation_id": key_representation_id,
                "matcher_policy_id": matcher_policy_id,
                "actual_contact_count": len(rows),
                "top_k": top_k,
            },
            "decisions": {
                "path": decisions.name,
                "sha256": digest,
                "count": len(rows),
            },
            "timing": {"aggregate_tokens_per_second": 100.0},
        }
        (attempt_dir / "flight-receipt.json").write_text(
            json.dumps(receipt), encoding="utf-8"
        )
        return attempt_dir

    baseline_dir = write_cell("K0-M1", make_first_wrong=True)
    candidate_dir = write_cell("K2-M1", make_first_wrong=False)
    report = read_speech_native_predictions(
        attempt_dirs=(baseline_dir, candidate_dir),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    assert report["selected_cell_id"] == "K2-M1"
    candidate = next(
        item for item in report["aggregates"] if item["cell_id"] == "K2-M1"
    )
    assert candidate["correct"] == 36
    assert candidate["wrong_to_correct_vs_baseline"] == 1
    assert candidate["correct_to_wrong_vs_baseline"] == 0
    assert report["cell_pairwise"] == [
        {
            "left_cell_id": "K0-M1",
            "right_cell_id": "K2-M1",
            "prediction_disagreement_count": 1,
        }
    ]
    assert report["selection_policy_id"] == "accuracy-regression-parse-order-cost-v1"


def test_model_free_prediction_read_distinguishes_m3_top_k_cells(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {
        card["value_label"]: card["key_id"] for card in binding["key_cards"]
    }

    def write_cell(
        top_k,
        prompt_policy_id="speech-native-json-copy-v2",
        order_id="canonical",
        verifier_policy_id="speech-native-compatibility-v1",
        mechanism_control_id="matched",
    ):
        suffix = "-".join(
            value
            for value in (
                "v3" if prompt_policy_id.endswith("-v3") else "v2",
                order_id,
                verifier_policy_id.rsplit("-", 1)[-1],
                mechanism_control_id,
            )
        )
        attempt_dir = tmp_path / f"m3-k{top_k}{suffix}"
        attempt_dir.mkdir()
        rows = []
        for index, item in enumerate(items):
            key_id = key_by_label[item["value_label"]]
            query_sample_id = (
                items[(index + 1) % len(items)]["sample_id"]
                if mechanism_control_id == "speech-swap-v1"
                else item["sample_id"]
            )
            rows.append(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "sample_id": item["sample_id"],
                    "key_id": key_id,
                    "predicted_value_label": item["value_label"],
                    "query_sample_id": query_sample_id,
                    "mechanism_control_id": mechanism_control_id,
                    "top_key_ids": [
                        key_id,
                        *[
                            candidate
                            for candidate in key_by_label.values()
                            if candidate != key_id
                        ][: top_k - 1],
                    ],
                    "parse_failure": False,
                }
            )
        decisions = attempt_dir / "decisions.jsonl"
        decisions.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        (attempt_dir / "flight-receipt.json").write_text(
            json.dumps(
                {
                    "status": "COMPLETED",
                    "request_failures": [],
                    "split_identity_hash": "a" * 64,
                    "run_id": f"run-m3-k{top_k}",
                    "profile": {
                        "key_representation_id": "K1",
                        "matcher_policy_id": "M3",
                        "matcher_prompt_policy_id": prompt_policy_id,
                        "matcher_verifier_policy_id": verifier_policy_id,
                        "mechanism_control_id": mechanism_control_id,
                        "key_order_ids": [order_id],
                        "top_k": top_k,
                        "actual_contact_count": len(rows),
                    },
                    "decisions": {
                        "path": decisions.name,
                        "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                        "count": len(rows),
                    },
                }
            ),
            encoding="utf-8",
        )
        return attempt_dir

    report = read_speech_native_predictions(
        attempt_dirs=(
            write_cell(3),
            write_cell(5),
            write_cell(3, "speech-native-json-copy-v3"),
            write_cell(
                3,
                "speech-native-json-copy-v3",
                order_id="reverse",
            ),
            write_cell(
                3,
                "speech-native-json-copy-v3",
                order_id="rotate-7",
            ),
            write_cell(
                3,
                "speech-native-json-copy-v3",
                verifier_policy_id="speech-native-contrastive-verifier-v2",
            ),
            write_cell(
                3,
                "speech-native-json-copy-v3",
                mechanism_control_id="speech-swap-v1",
            ),
        ),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    assert [item["cell_id"] for item in report["aggregates"]] == [
        "K1-M3-k3",
        "K1-M3-k5",
        "K1-M3-k3-v3",
        "K1-M3-k3-v3-order-reverse",
        "K1-M3-k3-v3-order-rotate-7",
        "K1-M3-k3-v3-verify-contrastive-v2",
        "K1-M3-k3-v3-control-speech-swap-v1",
        "K1-M4-k3-v3-order-ensemble-v1",
    ]
    assert all(
        item["top_k_reachable_count"] == 36
        for item in report["aggregates"]
        if item["cell_id"] != "K1-M4-k3-v3-order-ensemble-v1"
    )
    ensemble = report["aggregates"][-1]
    assert ensemble["correct"] == 36
    assert ensemble["source_cell_ids"] == [
        "K1-M3-k3-v3",
        "K1-M3-k3-v3-order-reverse",
        "K1-M3-k3-v3-order-rotate-7",
    ]
    assert ensemble["tie_break_count"] == 0


def test_model_free_read_replays_disagreement_escalation_frontier(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {
        card["value_label"]: card["key_id"] for card in binding["key_cards"]
    }
    labels = tuple(key_by_label)

    def write_cell(matcher_policy_id, *, order_id="canonical", wrong_offset=None):
        attempt_dir = tmp_path / f"{matcher_policy_id}-{order_id}"
        attempt_dir.mkdir()
        rows = []
        for index, item in enumerate(items):
            predicted = item["value_label"]
            calls = 1 if matcher_policy_id == "M1" else 4
            if index == 0 and matcher_policy_id == "M3" and order_id == "rotate-7":
                calls += 1
            if index == 0 and wrong_offset is not None:
                predicted = labels[
                    (labels.index(predicted) + wrong_offset) % len(labels)
                ]
            key_id = key_by_label[predicted]
            gold_key_id = key_by_label[item["value_label"]]
            rows.append(
                {
                    "schema": "saea-speech-native-decision-v1",
                    "sample_id": item["sample_id"],
                    "key_id": key_id,
                    "predicted_value_label": predicted,
                    "top_key_ids": (
                        []
                        if matcher_policy_id == "M1"
                        else [
                            gold_key_id,
                            *[
                                candidate
                                for candidate in key_by_label.values()
                                if candidate != gold_key_id
                            ][:2],
                        ]
                    ),
                    "calls": calls,
                    "parse_failure": False,
                }
            )
        decisions = attempt_dir / "decisions.jsonl"
        decisions.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )
        (attempt_dir / "flight-receipt.json").write_text(
            json.dumps(
                {
                    "status": "COMPLETED",
                    "request_failures": [],
                    "split_identity_hash": "a" * 64,
                    "run_id": f"run-{matcher_policy_id}-{order_id}",
                    "profile": {
                        "key_representation_id": "K1",
                        "matcher_policy_id": matcher_policy_id,
                        "matcher_prompt_policy_id": "speech-native-json-copy-v3",
                        "matcher_verifier_policy_id": "speech-native-compatibility-v1",
                        "mechanism_control_id": "matched",
                        "key_order_ids": [order_id],
                        "top_k": 3,
                        "actual_contact_count": sum(row["calls"] for row in rows),
                    },
                    "decisions": {
                        "path": decisions.name,
                        "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                        "count": len(rows),
                    },
                }
            ),
            encoding="utf-8",
        )
        return attempt_dir

    report = read_speech_native_predictions(
        attempt_dirs=(
            write_cell("M1", wrong_offset=1),
            write_cell("M3", wrong_offset=2),
            write_cell("M3", order_id="reverse"),
            write_cell("M3", order_id="rotate-7", wrong_offset=None),
        ),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    assert report["adaptive_policies"] == [
        {
            "policy_id": "K1-M5-disagreement-escalation-v1",
            "discovery_status": "post-read-policy-discovery",
            "correct": 36,
            "count": 36,
            "accuracy": 1.0,
            "actual_contact_count": 189,
            "stop_agree_count": 35,
            "escalation_count": 1,
            "wrong_to_correct_vs_primary": 1,
            "correct_to_wrong_vs_primary": 0,
            "parse_failure_count": 0,
            "source_cell_ids": [
                "K1-M1",
                "K1-M3-k3-v3",
                "K1-M3-k3-v3-order-reverse",
                "K1-M3-k3-v3-order-rotate-7",
            ],
            "escalation_policy_id": "m1-m3-disagree-v1",
            "escalation_aggregator_id": "m3-majority-canonical-tie-v1",
        }
    ]
    assert [item["policy_id"] for item in report["accuracy_cost_frontier"]] == [
        "K1-M1",
        "K1-M5-disagreement-escalation-v1",
    ]


def test_model_free_read_reports_agent_loop_optimization_signals(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {
        card["value_label"]: card["key_id"] for card in binding["key_cards"]
    }
    labels = tuple(key_by_label)
    attempt_dir = tmp_path / "m5"
    attempt_dir.mkdir()
    rows = []
    for index, item in enumerate(items):
        gold_label = item["value_label"]
        gold_key = key_by_label[gold_label]
        wrong_label = labels[(labels.index(gold_label) + 1) % len(labels)]
        wrong_key = key_by_label[wrong_label]
        if index == 0:
            votes = [wrong_key, gold_key, gold_key, wrong_key]
            final_key = gold_key
            escalated = True
        elif index == 1:
            votes = [wrong_key, wrong_key]
            final_key = wrong_key
            escalated = False
        elif index == 2:
            votes = [gold_key, wrong_key, wrong_key, wrong_key]
            final_key = wrong_key
            escalated = True
        else:
            votes = [gold_key, gold_key]
            final_key = gold_key
            escalated = False
        step_actions = [
            "match:listwise-canonical",
            "retrieve-verify:canonical",
            *(
                ["retrieve-verify:reverse", "retrieve-verify:rotate-7"]
                if escalated
                else []
            ),
        ]
        agent_actions = [
            "match:listwise-canonical",
            "retrieve-verify:canonical",
            *(
                [
                    "escalate:disagreement",
                    "retrieve-verify:reverse",
                    "retrieve-verify:rotate-7",
                    "aggregate:m3-majority-canonical-tie",
                ]
                if escalated
                else ["stop:agree"]
            ),
        ]
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": item["sample_id"],
                "key_id": final_key,
                "predicted_value_label": (
                    gold_label if final_key == gold_key else wrong_label
                ),
                "top_key_ids": [votes[1]],
                "calls": 10 if escalated else 4,
                "parse_failure": False,
                "agent_policy_id": "m1-m3-disagreement-escalation-v1",
                "agent_actions": agent_actions,
                "agent_escalated": escalated,
                "agent_vote_key_ids": votes,
                "agent_steps": [
                    {
                        "action_id": action_id,
                        "key_id": vote,
                        "top_key_ids": [] if step_index == 0 else [vote],
                        "calls": 1 if step_index == 0 else 3,
                        "parse_failure": False,
                    }
                    for step_index, (action_id, vote) in enumerate(
                        zip(step_actions, votes, strict=True)
                    )
                ],
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (attempt_dir / "flight-receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "request_failures": [],
                "split_identity_hash": "a" * 64,
                "run_id": "run-m5",
                "profile": {
                    "key_representation_id": "K1",
                    "matcher_policy_id": "M5",
                    "matcher_prompt_policy_id": "speech-native-json-copy-v3",
                    "matcher_verifier_policy_id": "speech-native-compatibility-v1",
                    "mechanism_control_id": "matched",
                    "key_order_ids": ["canonical"],
                    "top_k": 3,
                    "actual_contact_count": sum(row["calls"] for row in rows),
                },
                "decisions": {
                    "path": decisions.name,
                    "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                    "count": len(rows),
                },
            }
        ),
        encoding="utf-8",
    )

    report = read_speech_native_predictions(
        attempt_dirs=(attempt_dir,),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    aggregate = report["aggregates"][0]
    assert aggregate["cell_id"] == "K1-M5-k3-v3"
    assert aggregate["correct"] == 34
    assert aggregate["agent_loop_metrics"] == {
        "policy_id": "m1-m3-disagreement-escalation-v1",
        "aggregator_id": "m3-majority-canonical-tie-v1",
        "primary_correct": 34,
        "primary_accuracy": 34 / 36,
        "final_minus_primary_correct": 0,
        "stop_count": 34,
        "escalation_count": 2,
        "escalation_rate": 2 / 36,
        "helpful_escalation_count": 1,
        "harmful_escalation_count": 1,
        "neutral_escalation_count": 0,
        "recoverable_error_count": 1,
        "missed_stop_error_count": 1,
        "action_sensitive_escalation_count": 1,
        "action_counts": {
            "aggregate:m3-majority-canonical-tie": 2,
            "escalate:disagreement": 2,
            "match:listwise-canonical": 36,
            "retrieve-verify:canonical": 36,
            "retrieve-verify:reverse": 2,
            "retrieve-verify:rotate-7": 2,
            "stop:agree": 34,
        },
        "counterfactual_aggregators": [
            {
                "aggregator_id": "m3-majority-primary-tie-v2",
                "discovery_status": "post-read-policy-discovery",
                "correct": 34,
                "count": 36,
                "accuracy": 34 / 36,
                "wrong_to_correct_vs_observed": 0,
                "correct_to_wrong_vs_observed": 0,
            },
            {
                "aggregator_id": "m3-unanimous-primary-fallback-v3",
                "discovery_status": "post-read-policy-discovery",
                "correct": 33,
                "count": 36,
                "accuracy": 33 / 36,
                "wrong_to_correct_vs_observed": 0,
                "correct_to_wrong_vs_observed": 1,
            },
        ],
    }


def test_model_free_read_accepts_complete_full_branch_action_support(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    key_by_label = {
        card["value_label"]: card["key_id"] for card in binding["key_cards"]
    }
    attempt_dir = tmp_path / "m5-full"
    attempt_dir.mkdir()
    rows = []
    for item in items:
        gold_label = item["value_label"]
        gold_key = key_by_label[gold_label]
        votes = [gold_key] * 4
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": item["sample_id"],
                "key_id": gold_key,
                "predicted_value_label": gold_label,
                "top_key_ids": [gold_key],
                "verifier_scores": {gold_key: {"compatible": True, "confidence": 90.0}},
                "calls": 10,
                "parse_failure": False,
                "agent_policy_id": "m1-m3-full-branch-explorer-v1",
                "agent_actions": [
                    "match:listwise-canonical",
                    "retrieve-verify:canonical",
                    "explore:full-branch",
                    "retrieve-verify:reverse",
                    "retrieve-verify:rotate-7",
                    "aggregate:m3-unanimous-primary-fallback",
                ],
                "agent_escalated": False,
                "agent_vote_key_ids": votes,
                "agent_steps": [
                    {
                        "action_id": action_id,
                        "key_id": gold_key,
                        "top_key_ids": [] if step_index == 0 else [gold_key],
                        "calls": 1 if step_index == 0 else 3,
                        "parse_failure": False,
                    }
                    for step_index, action_id in enumerate(
                        (
                            "match:listwise-canonical",
                            "retrieve-verify:canonical",
                            "retrieve-verify:reverse",
                            "retrieve-verify:rotate-7",
                        )
                    )
                ],
                "agent_aggregator_id": "m3-unanimous-primary-fallback-v3",
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (attempt_dir / "flight-receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "request_failures": [],
                "split_identity_hash": "a" * 64,
                "run_id": "run-m5-full",
                "profile": {
                    "key_representation_id": "K1",
                    "matcher_policy_id": "M5",
                    "matcher_prompt_policy_id": "speech-native-json-copy-v3",
                    "matcher_verifier_policy_id": "speech-native-compatibility-v1",
                    "agent_policy_id": "m1-m3-full-branch-explorer-v1",
                    "agent_aggregator_id": "m3-unanimous-primary-fallback-v3",
                    "mechanism_control_id": "matched",
                    "key_order_ids": ["canonical"],
                    "top_k": 3,
                    "actual_contact_count": sum(row["calls"] for row in rows),
                },
                "decisions": {
                    "path": decisions.name,
                    "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                    "count": len(rows),
                },
            }
        ),
        encoding="utf-8",
    )

    report = read_speech_native_predictions(
        attempt_dirs=(attempt_dir,),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )
    aggregate = report["aggregates"][0]
    assert aggregate["cell_id"] == (
        "K1-M5-k3-v3-aggregate-unanimous-v3-agent-full-branch-v1"
    )
    metrics = aggregate["agent_loop_metrics"]
    assert metrics["full_branch_count"] == 36
    assert metrics["action_support_complete"] is True
    assert metrics["wrong_agreement_count"] == 0
    assert all(
        policy["correct"] == 36 for policy in metrics["training_free_policy_frontier"]
    )
    episodic = metrics["training_free_episodic_policy"]
    assert episodic["correct"] == 36
    assert episodic["primary_correct"] == 36
    assert episodic["correct_to_wrong_vs_primary"] == 0
    assert episodic["oof_action_counts"] == {"primary": 36}
    assert episodic["mean_contacts"] == 4.0


@pytest.mark.parametrize(
    ("agent_policy_id", "cell_suffix", "mechanism_control_id"),
    (
        (
            "knowledge-grounded-semantic-refinement-full-action-v1",
            "grounded-v1",
            "matched",
        ),
        (
            "knowledge-grounded-semantic-refinement-schema-v2",
            "grounded-schema-v2",
            "matched",
        ),
        (
            "knowledge-grounded-semantic-refinement-schema-v3",
            "grounded-schema-v3",
            "matched",
        ),
        (
            "knowledge-grounded-semantic-refinement-schema-v3",
            "grounded-schema-v3-control-key-text-shuffle-v1",
            "key-text-shuffle-v1",
        ),
    ),
)
def test_model_free_read_reports_grounded_semantic_refinement_actions(
    tmp_path, agent_policy_id, cell_suffix, mechanism_control_id
):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    cards = {card["key_id"]: card for card in binding["key_cards"]}
    ordered_cards = tuple(binding["key_cards"])
    visible_cards = (
        {
            target["key_id"]: {
                **target,
                "definition": donor["definition"],
                "positive_examples": donor["positive_examples"],
                "contrastive_boundary": donor["contrastive_boundary"],
            }
            for target, donor in zip(
                ordered_cards,
                ordered_cards[1:] + ordered_cards[:1],
                strict=True,
            )
        }
        if mechanism_control_id == "key-text-shuffle-v1"
        else cards
    )
    key_by_label = {card["value_label"]: card["key_id"] for card in cards.values()}
    labels = tuple(key_by_label)
    attempt_dir = tmp_path / "m6-grounded"
    attempt_dir.mkdir()
    rows = []
    for index, item in enumerate(items):
        gold_label = item["value_label"]
        gold_key = key_by_label[gold_label]
        wrong_label = labels[(labels.index(gold_label) + 1) % len(labels)]
        wrong_key = key_by_label[wrong_label]
        primary_key = wrong_key if index == 0 else gold_key
        refined_key = wrong_key if index == 1 else gold_key
        initial_top = [
            primary_key,
            *[key_id for key_id in key_by_label.values() if key_id != primary_key][:2],
        ]
        refined_top = [
            refined_key,
            *[key_id for key_id in key_by_label.values() if key_id != refined_key][:2],
        ]
        if gold_key not in refined_top:
            refined_top[-1] = gold_key
        state = {
            "candidate_key_ids": initial_top,
            "domain": "bounded-domain",
            "operation": "bounded-operation",
            "target": "bounded-target",
            "constraints": [],
            "exclusions": [],
            "unresolved_ambiguity": "none",
            "evidence": [
                {
                    "key_id": key_id,
                    "field": "definition",
                    "quote": visible_cards[key_id]["definition"],
                }
                for key_id in initial_top
            ],
        }
        verifier_scores = {
            key_id: {
                "compatible": key_id == refined_key,
                "confidence": 90.0 if key_id == refined_key else 20.0,
            }
            for key_id in refined_top
        }
        predicted_label = cards[refined_key]["value_label"]
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": item["sample_id"],
                "key_id": refined_key,
                "predicted_value_label": predicted_label,
                "top_key_ids": refined_top,
                "verifier_scores": verifier_scores,
                "calls": 7,
                "parse_failure": False,
                "agent_policy_id": agent_policy_id,
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "build:grounded-query-state",
                    "retrieve:speech-plus-grounded-state",
                    "verify:speech-plus-grounded-state",
                    "select:refined-primary-fallback",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": [primary_key, refined_key],
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": primary_key,
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": initial_top[0],
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "build:grounded-query-state",
                        "key_id": None,
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                        "grounded_query_state": state,
                    },
                    {
                        "action_id": ("retrieve-and-verify:speech-plus-grounded-state"),
                        "key_id": refined_key,
                        "top_key_ids": refined_top,
                        "calls": 4,
                        "parse_failure": False,
                        "verifier_scores": verifier_scores,
                    },
                ],
                "agent_aggregator_id": "grounded-refined-primary-fallback-v1",
            }
        )
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (attempt_dir / "flight-receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "request_failures": [],
                "split_identity_hash": "a" * 64,
                "run_id": "run-m6-grounded",
                "profile": {
                    "key_representation_id": "K1",
                    "matcher_policy_id": "M6",
                    "matcher_prompt_policy_id": "speech-native-json-copy-v3",
                    "matcher_verifier_policy_id": (
                        "speech-native-contrastive-verifier-v2"
                    ),
                    "agent_policy_id": agent_policy_id,
                    "agent_aggregator_id": ("grounded-refined-primary-fallback-v1"),
                    "mechanism_control_id": mechanism_control_id,
                    "key_text_mapping_sha256": (
                        _canonical_sha256(
                            {
                                card["key_id"]: ordered_cards[
                                    (index + 1) % len(ordered_cards)
                                ]["key_id"]
                                for index, card in enumerate(ordered_cards)
                            }
                        )
                        if mechanism_control_id == "key-text-shuffle-v1"
                        else None
                    ),
                    "key_order_ids": ["canonical"],
                    "top_k": 3,
                    "actual_contact_count": sum(row["calls"] for row in rows),
                },
                "decisions": {
                    "path": decisions.name,
                    "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                    "count": len(rows),
                },
            }
        ),
        encoding="utf-8",
    )

    attempt_dirs = (attempt_dir,)
    if mechanism_control_id == "key-text-shuffle-v1":
        matched_dir = tmp_path / "m6-grounded-matched"
        matched_dir.mkdir()
        matched_rows = json.loads(json.dumps(rows))
        for row in matched_rows:
            for evidence in row["agent_steps"][2]["grounded_query_state"]["evidence"]:
                evidence["quote"] = cards[evidence["key_id"]]["definition"]
        matched_decisions = matched_dir / "decisions.jsonl"
        matched_decisions.write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in matched_rows),
            encoding="utf-8",
        )
        matched_receipt = json.loads(
            (attempt_dir / "flight-receipt.json").read_text(encoding="utf-8")
        )
        matched_receipt["run_id"] = "run-m6-grounded-matched"
        matched_receipt["profile"]["mechanism_control_id"] = "matched"
        matched_receipt["profile"]["key_text_mapping_sha256"] = None
        matched_receipt["decisions"]["sha256"] = hashlib.sha256(
            matched_decisions.read_bytes()
        ).hexdigest()
        (matched_dir / "flight-receipt.json").write_text(
            json.dumps(matched_receipt),
            encoding="utf-8",
        )
        attempt_dirs = (matched_dir, attempt_dir)

    report = read_speech_native_predictions(
        attempt_dirs=attempt_dirs,
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )

    expected_cell_id = f"K1-M6-k3-v3-verify-contrastive-v2-{cell_suffix}"
    aggregate = next(
        item for item in report["aggregates"] if item["cell_id"] == expected_cell_id
    )
    assert aggregate["cell_id"] == (expected_cell_id)
    assert aggregate["correct"] == 35
    assert aggregate["top_k_reachable_count"] == 36
    metrics = aggregate["agent_loop_metrics"]
    expected_metrics = {
        "policy_id": agent_policy_id,
        "aggregator_id": "grounded-refined-primary-fallback-v1",
        "primary_correct": 35,
        "primary_accuracy": 35 / 36,
        "final_minus_primary_correct": 0,
        "grounded_state_valid_count": 36,
        "grounded_state_valid_rate": 1.0,
        "backtrack_count": 0,
        "refined_change_count": 2,
        "helpful_refinement_count": 1,
        "harmful_refinement_count": 1,
        "neutral_refinement_count": 34,
        "recoverable_error_count": 1,
        "action_sensitive_count": 2,
        "action_counts": {
            "build:grounded-query-state": 36,
            "match:speech-only-primary": 36,
            "retrieve:speech-only": 36,
            "retrieve:speech-plus-grounded-state": 36,
            "select:refined-primary-fallback": 36,
            "verify:speech-plus-grounded-state": 36,
        },
    }
    assert {key: metrics[key] for key in expected_metrics} == expected_metrics
    assert metrics["speaker_fold_policy_id"] == (
        "speaker-grouped-3fold-sha256-load-balanced-v1"
    )
    folds = metrics["speaker_folds_vs_primary"]
    assert len(folds) == 3
    assert sum(fold["count"] for fold in folds) == 36
    assert sum(fold["correct_delta_vs_primary"] for fold in folds) == 0
    assert metrics["positive_delta_fold_count"] == sum(
        fold["correct_delta_vs_primary"] > 0 for fold in folds
    )
    assert metrics["worst_fold_delta_vs_primary"] == min(
        fold["correct_delta_vs_primary"] for fold in folds
    )
    if (
        agent_policy_id == "knowledge-grounded-semantic-refinement-schema-v3"
        and mechanism_control_id == "matched"
    ):
        policy = metrics["training_free_grounded_semantic_policy"]
        assert policy["correct"] == 35
        assert policy["primary_correct"] == 35
        assert policy["wrong_to_correct_vs_primary"] == 0
        assert policy["correct_to_wrong_vs_primary"] == 0
        assert policy["action_variable_count"] == 2
        assert policy["oof_action_counts"] == {"retain_primary": 36}
        assert policy["promotion_gate_passed"] is False


def _binding_material():
    material = []
    for scenario_index, scenario in enumerate(("alarm", "email")):
        for item_index in range(24):
            speaker = f"speaker-{scenario_index}-{item_index}"
            sample_id = f"slurp:train:{scenario_index:02d}{item_index:04d}:audio-{scenario_index}-{item_index}"
            material.append(
                SlurpTrainMaterial(
                    utterance_id=f"{scenario_index:02d}{item_index:04d}",
                    scenario=scenario,
                    action="act",
                    sentence=f"unique {scenario} example {item_index}",
                    recordings=(
                        SlurpTrainRecording(
                            sample_id=sample_id,
                            media_relpath=f"datasets/slurp/slurp_real/audio-{scenario_index}-{item_index}.flac",
                            speaker_id=speaker,
                        ),
                    ),
                )
            )
    return tuple(material)


def _knowledge_refinement_material():
    action_sentences = {
        "alarm": {
            "set": "set an alarm for six",
            "query": "show my active alarms",
            "remove": "cancel my morning alarm",
        },
        "email": {
            "query": "read my newest email",
            "sendemail": "send an email to alex",
            "querycontact": "find alex in my email contacts",
            "addcontact": "add alex to my email contacts",
        },
    }
    material = []
    item_index = 0
    for scenario, actions in action_sentences.items():
        for action, sentence in actions.items():
            for replica in range(8):
                item_index += 1
                utterance_id = f"knowledge-{item_index:04d}"
                material.append(
                    SlurpTrainMaterial(
                        utterance_id=utterance_id,
                        scenario=scenario,
                        action=action,
                        sentence=f"{sentence} example {replica}",
                        recordings=(
                            SlurpTrainRecording(
                                sample_id=(
                                    f"slurp:train:{item_index:06d}:"
                                    f"audio-knowledge-{item_index}"
                                ),
                                media_relpath=(
                                    "datasets/slurp/slurp_real/"
                                    f"audio-knowledge-{item_index}.flac"
                                ),
                                speaker_id=f"knowledge-speaker-{item_index}",
                            ),
                        ),
                    )
                )
    material.extend(
        (
            SlurpTrainMaterial(
                utterance_id="knowledge-noise-alarm",
                scenario="alarm",
                action="remove",
                sentence="teach children to never answer the door when home alone",
                recordings=(
                    SlurpTrainRecording(
                        sample_id="slurp:train:990001:audio-noise-alarm",
                        media_relpath="datasets/slurp/slurp_real/audio-noise-alarm.flac",
                        speaker_id="knowledge-noise-speaker-alarm",
                    ),
                ),
            ),
            SlurpTrainMaterial(
                utterance_id="knowledge-noise-email",
                scenario="email",
                action="querycontact",
                sentence="what is his number",
                recordings=(
                    SlurpTrainRecording(
                        sample_id="slurp:train:990002:audio-noise-email",
                        media_relpath="datasets/slurp/slurp_real/audio-noise-email.flac",
                        speaker_id="knowledge-noise-speaker-email",
                    ),
                ),
            ),
        )
    )
    return tuple(material)


def test_speech_native_knowledge_refinement_is_data_derived_and_isolated():
    material = _knowledge_refinement_material()
    base = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )

    successor = refine_speech_native_binding_knowledge(
        base,
        material,
        seed=20260827,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )

    assert successor["splits"] == base["splits"]
    assert successor["engineering_gate"] == base["engineering_gate"]
    assert successor["knowledge_parent_binding_sha256"] == base["binding_sha256"]
    assert successor["binding_sha256"] == _binding_document_sha256(
        {key: value for key, value in successor.items() if key != "binding_sha256"}
    )
    assert successor["knowledge_revision"]["policy_id"] == (
        "slurp-action-stratified-specificity-v1"
    )
    assert successor["knowledge_revision"]["query_excluded_corpus_utterances"] > 0

    material_by_utterance = {entry.utterance_id: entry for entry in material}
    expected_actions = {
        "alarm": {"set", "query", "remove"},
        "email": {"query", "sendemail", "querycontact", "addcontact"},
    }
    labels_by_key = {
        card["key_id"]: card["value_label"] for card in successor["key_cards"]
    }
    for card in successor["key_cards"]:
        assert "Dataset-derived action facets:" in card["definition"]
        assert len(card["positive_examples"]) == 5
        assert "teach children" not in " ".join(card["positive_examples"])
        assert "what is his number" not in card["positive_examples"]
    for key in successor["key_material"]:
        scenario = labels_by_key[key["key_id"]]
        selected_actions = {
            material_by_utterance[source["utterance_id"]].action
            for source in key["sources"]
        }
        assert selected_actions == expected_actions[scenario]

    query_items = [
        item for split in successor["splits"].values() for item in split["items"]
    ]
    key_sources = [
        source for key in successor["key_material"] for source in key["sources"]
    ]
    for field in ("sample_id", "utterance_id", "speaker_id", "normalized_sentence"):
        assert {item[field] for item in query_items}.isdisjoint(
            source[field] for source in key_sources
        )

    repeated = refine_speech_native_binding_knowledge(
        base,
        reversed(material),
        seed=20260827,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    assert json.dumps(successor, sort_keys=True) == json.dumps(repeated, sort_keys=True)


def test_data_derived_decision_graph_uses_remaining_train_actions_and_pair_signal():
    material = _knowledge_refinement_material()
    base = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    knowledge = refine_speech_native_binding_knowledge(
        base,
        material,
        seed=20260827,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )

    graph = build_data_derived_decision_graph(
        knowledge,
        material,
        graph_id="slurp-data-derived-decision-graph-v2",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
    )

    cards = tuple(
        KeyCardV1(
            key_id=raw["key_id"],
            definition=raw["definition"],
            positive_examples=tuple(raw["positive_examples"]),
            contrastive_boundary=raw["contrastive_boundary"],
            value_label=raw["value_label"],
        )
        for raw in knowledge["key_cards"]
    )
    assert graph.validate(cards) is graph
    assert graph.graph_id == "slurp-data-derived-decision-graph-v2"
    assert len(graph.boundaries) == 1
    assert {(factor.kind, factor.key_ids) for factor in graph.factors} >= {
        ("target", ("K001",)),
        ("target", ("K002",)),
    }
    action_provenance = {
        provenance
        for factor in graph.factors
        if factor.kind == "operation"
        for provenance in factor.provenance_ids
    }
    assert {
        "slurp-train-action:alarm:set",
        "slurp-train-action:alarm:query",
        "slurp-train-action:alarm:remove",
        "slurp-train-action:email:query",
        "slurp-train-action:email:sendemail",
        "slurp-train-action:email:querycontact",
        "slurp-train-action:email:addcontact",
    } <= action_provenance
    boundary = graph.boundaries[0]
    assert {boundary.left_key_id, boundary.right_key_id} == {"K001", "K002"}
    assert any(
        provenance.startswith("slurp-train-pair-signal:")
        for provenance in boundary.provenance_ids
    )
    assert "instead expresses" in boundary.left_exclusion
    assert "instead expresses" in boundary.right_exclusion

    repeated = build_data_derived_decision_graph(
        knowledge,
        reversed(material),
        graph_id="slurp-data-derived-decision-graph-v2",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
    )
    assert graph.as_json() == repeated.as_json()


def test_speech_native_successor_binding_preserves_keys_and_adds_isolated_split():
    material = _binding_material()
    base = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    successor = extend_speech_native_binding(
        base,
        material,
        seed=20260822,
        split_name="DISCOVERY-X12",
        per_scenario=6,
        expected_scenarios=("alarm", "email"),
    )

    assert successor["key_cards"] == base["key_cards"]
    assert successor["key_material"] == base["key_material"]
    assert {name: successor["splits"][name] for name in base["splits"]} == base[
        "splits"
    ]
    extension = successor["splits"]["DISCOVERY-X12"]
    assert len(extension["items"]) == 12
    assert successor["parent_binding_sha256"] == base["binding_sha256"]

    old_items = [item for split in base["splits"].values() for item in split["items"]]
    key_sources = [source for key in base["key_material"] for source in key["sources"]]
    for field in (
        "sample_id",
        "utterance_id",
        "speaker_id",
        "normalized_sentence",
    ):
        excluded = {item[field] for item in (*old_items, *key_sources)}
        selected = {item[field] for item in extension["items"]}
        assert selected.isdisjoint(excluded)
    assert successor["isolation_audit"]["query_sample_count"] == 20
    assert successor["isolation_audit"]["query_key_speaker_overlap"] == 0


def test_binding_extension_cli_reuses_frozen_builder(monkeypatch, tmp_path, capsys):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")
    output = tmp_path / "successor-binding.json"
    material = _binding_material()
    captured = {}

    monkeypatch.setattr(driver_cli_module, "load_lock", lambda _path: {"lock": True})
    monkeypatch.setattr(driver_cli_module, "umbrella_lock_path", lambda: tmp_path)
    monkeypatch.setattr(driver_cli_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver_cli_module,
        "load_slurp_train_material",
        lambda lock, root, *, media_validation_workers: (
            captured.update(
                {
                    "lock": lock,
                    "root": root,
                    "workers": media_validation_workers,
                }
            )
            or material
        ),
    )

    def fake_extend(base, loaded_material, **kwargs):
        captured.update(
            {
                "base": base,
                "material": loaded_material,
                "extension": kwargs,
            }
        )
        return {
            "binding_sha256": "a" * 64,
            "extension_audit": {
                "query_count": 12,
                "parent_query_speaker_overlap_count": 3,
            },
        }

    monkeypatch.setattr(driver_cli_module, "extend_speech_native_binding", fake_extend)
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--output",
            str(output),
            "--seed",
            "20260826",
            "--split-name",
            "EVIDENCE-E12",
            "--per-scenario",
            "6",
            "--workers",
            "8",
            "--allow-parent-query-speaker-overlap",
        ]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["binding_sha256"] == (
        "a" * 64
    )
    assert captured["workers"] == 8
    assert captured["material"] == material
    assert captured["extension"] == {
        "seed": 20260826,
        "split_name": "EVIDENCE-E12",
        "per_scenario": 6,
        "isolate_parent_query_speakers": False,
    }
    summary = json.loads(capsys.readouterr().out)
    assert summary["query_count"] == 12
    assert summary["parent_query_speaker_overlap_count"] == 3


def test_binding_extension_cli_reuses_selector_for_knowledge_only_successor(
    monkeypatch, tmp_path, capsys
):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")
    output = tmp_path / "knowledge-binding.json"
    material = _knowledge_refinement_material()
    captured = {}

    monkeypatch.setattr(driver_cli_module, "load_lock", lambda _path: {"lock": True})
    monkeypatch.setattr(driver_cli_module, "umbrella_lock_path", lambda: tmp_path)
    monkeypatch.setattr(driver_cli_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver_cli_module,
        "load_slurp_train_material",
        lambda lock, root, *, media_validation_workers: material,
    )

    def fake_refine(base, loaded_material, **kwargs):
        captured.update(
            {"base": base, "material": loaded_material, "refinement": kwargs}
        )
        return {
            "binding_sha256": "b" * 64,
            "knowledge_revision": {
                "policy_id": "slurp-action-stratified-specificity-v1",
                "key_count": 18,
            },
        }

    monkeypatch.setattr(
        driver_cli_module,
        "refine_speech_native_binding_knowledge",
        fake_refine,
    )
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--output",
            str(output),
            "--seed",
            "20260827",
            "--knowledge-policy",
            "slurp-action-stratified-specificity-v1",
            "--workers",
            "8",
        ]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["binding_sha256"] == (
        "b" * 64
    )
    assert captured["base"] == {"binding_sha256": "parent"}
    assert captured["material"] == material
    assert captured["refinement"] == {
        "seed": 20260827,
        "policy_id": "slurp-action-stratified-specificity-v1",
    }
    summary = json.loads(capsys.readouterr().out)
    assert summary["query_count"] is None
    assert summary["knowledge_policy_id"] == ("slurp-action-stratified-specificity-v1")


def test_binding_extension_cli_emits_graph_from_same_knowledge_successor(
    monkeypatch, tmp_path, capsys
):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")
    output = tmp_path / "knowledge-binding.json"
    graph_output = tmp_path / "knowledge-graph.json"
    material = _knowledge_refinement_material()
    knowledge = {
        "binding_sha256": "b" * 64,
        "knowledge_revision": {
            "policy_id": "slurp-action-stratified-specificity-v1",
            "key_count": 18,
        },
    }
    captured = {}

    monkeypatch.setattr(driver_cli_module, "load_lock", lambda _path: {"lock": True})
    monkeypatch.setattr(driver_cli_module, "umbrella_lock_path", lambda: tmp_path)
    monkeypatch.setattr(driver_cli_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver_cli_module,
        "load_slurp_train_material",
        lambda lock, root, *, media_validation_workers: material,
    )
    monkeypatch.setattr(
        driver_cli_module,
        "refine_speech_native_binding_knowledge",
        lambda base, loaded_material, **kwargs: knowledge,
    )

    class FakeGraph:
        def as_json(self):
            return {
                "schema": "saea-decision-graph-v1",
                "graph_id": "slurp-data-derived-decision-graph-v2",
                "factors": [],
                "boundaries": [],
            }

    def fake_build(successor, loaded_material, **kwargs):
        captured.update(
            {
                "successor": successor,
                "material": loaded_material,
                "graph": kwargs,
            }
        )
        return FakeGraph()

    monkeypatch.setattr(
        driver_cli_module,
        "build_data_derived_decision_graph",
        fake_build,
    )
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--output",
            str(output),
            "--seed",
            "20260827",
            "--knowledge-policy",
            "slurp-action-stratified-specificity-v1",
            "--decision-graph-output",
            str(graph_output),
            "--maximum-boundaries",
            "27",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "successor": knowledge,
        "material": material,
        "graph": {
            "graph_id": "slurp-data-derived-decision-graph-v2",
            "maximum_boundaries": 27,
        },
    }
    assert json.loads(graph_output.read_text(encoding="utf-8"))["graph_id"] == (
        "slurp-data-derived-decision-graph-v2"
    )
    summary = json.loads(capsys.readouterr().out)
    assert summary["decision_graph_output"] == str(graph_output.resolve())
    assert len(summary["decision_graph_artifact_sha256"]) == 64


def test_binding_extension_cli_allows_graph_only_from_existing_knowledge(
    monkeypatch, tmp_path, capsys
):
    parent = tmp_path / "knowledge-binding.json"
    knowledge = {
        "binding_sha256": "b" * 64,
        "knowledge_revision": {"policy_id": "slurp-action-stratified-specificity-v1"},
    }
    parent.write_text(json.dumps(knowledge), encoding="utf-8")
    graph_output = tmp_path / "knowledge-graph.json"
    material = _knowledge_refinement_material()

    monkeypatch.setattr(driver_cli_module, "load_lock", lambda _path: {"lock": True})
    monkeypatch.setattr(driver_cli_module, "umbrella_lock_path", lambda: tmp_path)
    monkeypatch.setattr(driver_cli_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver_cli_module,
        "load_slurp_train_material",
        lambda lock, root, *, media_validation_workers: material,
    )

    class FakeGraph:
        def as_json(self):
            return {
                "schema": "saea-decision-graph-v1",
                "graph_id": "slurp-data-derived-decision-graph-v2",
                "factors": [],
                "boundaries": [],
            }

    monkeypatch.setattr(
        driver_cli_module,
        "build_data_derived_decision_graph",
        lambda successor, loaded_material, **kwargs: FakeGraph(),
    )
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--seed",
            "20260827",
            "--decision-graph-output",
            str(graph_output),
        ]
    )

    assert exit_code == 0
    assert graph_output.is_file()
    summary = json.loads(capsys.readouterr().out)
    assert summary["output"] is None
    assert summary["artifact_sha256"] is None


def test_binding_extension_cli_requires_one_extension_or_knowledge_operation(
    tmp_path,
):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")

    with pytest.raises(ValueError, match="split extension or knowledge refinement"):
        driver_cli_module.main(
            [
                "extend-speech-native-binding",
                "--parent-binding",
                str(parent),
                "--output",
                str(tmp_path / "unused.json"),
                "--seed",
                "20260827",
            ]
        )


def test_binding_extension_cli_refuses_existing_output(monkeypatch, tmp_path):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")
    output = tmp_path / "successor-binding.json"
    output.write_text("do not replace", encoding="utf-8")

    with pytest.raises(ValueError, match="already exists"):
        driver_cli_module.main(
            [
                "extend-speech-native-binding",
                "--parent-binding",
                str(parent),
                "--output",
                str(output),
                "--seed",
                "20260826",
                "--split-name",
                "EVIDENCE-E12",
                "--per-scenario",
                "6",
            ]
        )


def test_speech_native_successor_groups_repeated_speakers_within_one_split():
    base = build_speech_native_binding(
        _binding_material(),
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    extension_material = tuple(
        SlurpTrainMaterial(
            utterance_id=f"ext-{scenario}-{index}",
            scenario=scenario,
            action="act",
            sentence=f"new isolated {scenario} command {index}",
            recordings=(
                SlurpTrainRecording(
                    sample_id=f"slurp:train:ext-{scenario}-{index}:audio-{index}",
                    media_relpath=f"datasets/slurp/slurp_real/ext-{scenario}-{index}.flac",
                    speaker_id="extension-shared-speaker",
                ),
            ),
        )
        for scenario in ("alarm", "email")
        for index in range(6)
    )

    successor = extend_speech_native_binding(
        base,
        extension_material,
        seed=20260822,
        split_name="DISCOVERY-X12",
        per_scenario=6,
        expected_scenarios=("alarm", "email"),
    )

    extension = successor["splits"]["DISCOVERY-X12"]
    assert len(extension["items"]) == 12
    assert {item["speaker_id"] for item in extension["items"]} == {
        "extension-shared-speaker"
    }


def test_speech_native_successor_can_audit_parent_query_speaker_overlap():
    base = build_speech_native_binding(
        _binding_material(),
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    parent_speaker = base["splits"]["OPT-A36"]["items"][0]["speaker_id"]
    extension_material = tuple(
        SlurpTrainMaterial(
            utterance_id=f"overlap-{scenario}",
            scenario=scenario,
            action="act",
            sentence=f"new isolated {scenario} command",
            recordings=(
                SlurpTrainRecording(
                    sample_id=f"slurp:train:overlap-{scenario}:audio",
                    media_relpath=f"datasets/slurp/slurp_real/overlap-{scenario}.flac",
                    speaker_id=parent_speaker,
                ),
            ),
        )
        for scenario in ("alarm", "email")
    )

    with pytest.raises(PsluFlightError, match="insufficient isolated extension"):
        extend_speech_native_binding(
            base,
            extension_material,
            seed=20260823,
            split_name="GATE-C2",
            per_scenario=1,
            expected_scenarios=("alarm", "email"),
        )

    successor = extend_speech_native_binding(
        base,
        extension_material,
        seed=20260823,
        split_name="GATE-C2",
        per_scenario=1,
        expected_scenarios=("alarm", "email"),
        isolate_parent_query_speakers=False,
    )

    audit = successor["extension_audit"]
    assert audit["parent_query_speaker_isolation"] is False
    assert audit["parent_query_speaker_overlap_count"] == 1
    assert successor["isolation_audit"]["query_key_speaker_overlap"] == 0


def test_speech_native_binding_is_stratified_and_query_key_isolated():
    binding = build_speech_native_binding(
        _binding_material(),
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    assert len(binding["splits"]["OPT-A36"]["items"]) == 4
    assert len(binding["splits"]["OPT-B18"]["items"]) == 2
    assert len(binding["splits"]["GATE18"]["items"]) == 2
    engineering_gate = binding["engineering_gate"]
    assert engineering_gate["name"] == "ENG-GATE8"
    assert len(engineering_gate["items"]) == 4
    assert all(
        set(item) == {"sample_id", "media_relpath"}
        for item in engineering_gate["items"]
    )
    assert engineering_gate["sample_ids"] == [
        item["sample_id"] for item in binding["splits"]["OPT-A36"]["items"]
    ]
    assert engineering_gate["split_identity_hash"] == _binding_document_sha256(
        {key: engineering_gate[key] for key in ("schema", "name", "seed", "sample_ids")}
    )
    assert len(binding["key_cards"]) == 2
    query_items = [
        item for split in binding["splits"].values() for item in split["items"]
    ]
    key_sources = [
        source for key in binding["key_material"] for source in key["sources"]
    ]
    assert {item["speaker_id"] for item in query_items}.isdisjoint(
        source["speaker_id"] for source in key_sources
    )
    assert {item["sample_id"] for item in query_items}.isdisjoint(
        source["sample_id"] for source in key_sources
    )
    assert {item["normalized_sentence"] for item in query_items}.isdisjoint(
        source["normalized_sentence"] for source in key_sources
    )


def _binding_document_sha256(document):
    import hashlib

    raw = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_speech_native_binding_is_byte_deterministic_for_the_same_seed():
    first = build_speech_native_binding(
        _binding_material(), seed=7, expected_scenarios=("alarm", "email")
    )
    second = build_speech_native_binding(
        reversed(_binding_material()), seed=7, expected_scenarios=("alarm", "email")
    )
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_speech_native_binding_refuses_insufficient_isolated_material():
    with pytest.raises(PsluFlightError, match="insufficient"):
        build_speech_native_binding(
            _binding_material()[:8],
            seed=1,
            expected_scenarios=("alarm", "email"),
        )


def _write_engineering_gate_view(tmp_path):
    media_root = tmp_path / "datasets/slurp/slurp_real"
    media_root.mkdir(parents=True)
    items = []
    for index in range(4):
        raw = f"speech-{index}".encode()
        media_relpath = f"datasets/slurp/slurp_real/audio-{index}.flac"
        (tmp_path / media_relpath).write_bytes(raw)
        items.append(
            {
                "sample_id": f"slurp:train:{index:06d}:audio-{index}",
                "media_relpath": media_relpath,
                "audio_sha256": hashlib.sha256(raw).hexdigest(),
                "audio_seconds": 1.25,
                "sample_rate_hz": 16000,
                "packet_id": f"slurp/train/{index:06d}/audio-{index}",
            }
        )
    unsigned = {
        "schema": "saea-speech-native-engineering-gate-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": "slurp",
        "split_name": "ENG-GATE8",
        "split_role": "discovery",
        "seed": 7,
        "split_identity_hash": "a" * 64,
        "source_binding_sha256": "b" * 64,
        "d1_media_supplement": "receipts/artifacts/d1.json",
        "d1_media_supplement_sha256": "c" * 64,
        "d1_manifest_sha256": "d" * 64,
        "count": 4,
        "audio_seconds_total": 5.0,
        "items": items,
    }
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path = tmp_path / "gate.json"
    path.write_text(
        json.dumps(
            {**unsigned, "runtime_view_sha256": hashlib.sha256(canonical).hexdigest()}
        ),
        encoding="utf-8",
    )
    return path


def test_engineering_gate_loader_validates_media_in_parallel_without_gold(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    lock = threading.Lock()
    active = 0
    peak = 0

    def media_probe(media_path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        try:
            raw = media_path.read_bytes()
            return hashlib.sha256(raw).hexdigest(), 1.25, 16000
        finally:
            with lock:
                active -= 1

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        workers=3,
        media_probe=media_probe,
    )

    assert len(gate.samples) == 4
    assert 2 <= peak <= 3
    assert gate.samples[0].packet_id == "slurp/train/000000/audio-0"
    assert not hasattr(gate.samples[0], "scenario")
    assert gate.d1_media_supplement_sha256 == "c" * 64


def test_engineering_loader_accepts_generalized_runtime_view_for_named_split(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    unsigned = {
        key: value for key, value in document.items() if key != "runtime_view_sha256"
    }
    unsigned["schema"] = "saea-speech-native-runtime-view-v1"
    unsigned["split_name"] = "OPT-A36"
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.write_text(
        json.dumps(
            {**unsigned, "runtime_view_sha256": hashlib.sha256(canonical).hexdigest()}
        ),
        encoding="utf-8",
    )

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        expected_split_name="OPT-A36",
        media_probe=lambda media_path: (
            hashlib.sha256(media_path.read_bytes()).hexdigest(),
            1.25,
            16000,
        ),
    )

    assert len(gate.samples) == 4
    assert gate.split_identity_hash == "a" * 64


def test_engineering_gate_loader_refuses_gold_fields_and_hash_drift(tmp_path):
    path = _write_engineering_gate_view(tmp_path)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["items"][0]["value_label"] = "alarm"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(PsluFlightError, match="label-free"):
        load_speech_native_engineering_gate(
            path,
            data_root=tmp_path,
            expected_count=4,
            media_probe=lambda _path: ("0" * 64, 1.25, 16000),
        )


def _adapter(slurp_world) -> SlurpAdapter:
    lock = load_lock(slurp_world.lock_path)
    return SlurpAdapter(lock, slurp_world.data_root)


# ---------------------------------------------------------------------------
# render_roster_entries / render_type_vocabulary
# ---------------------------------------------------------------------------


def test_render_roster_entries_joins_type_value_pairs():
    text = render_roster_entries([("house_place", "kitchen"), ("device_type", "light")])
    assert text == "house_place=kitchen; device_type=light"


def test_render_type_vocabulary_comma_joins_bare_types():
    assert render_type_vocabulary(["a", "b", "c"]) == "a, b, c"


# ---------------------------------------------------------------------------
# load_pslu_rosters
# ---------------------------------------------------------------------------


def _write_roster_table(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "legality_tier": "legal",
        "train_synthetic_refused": {"train_jsonl_overlap_with_devel": 0},
        "arms": {
            "A1_scenario_roster": {
                "rosters": {
                    "iot": [["house_place", "kitchen"], ["device_type", "light"]],
                    "email": [["email_folder", "inbox"]],
                }
            },
            "A2_global_type_vocabulary": {
                "types": ["house_place", "device_type", "email_folder", "time"]
            },
            "A3_full_ontology_dose_capped": {
                "roster": [["house_place", "kitchen"], ["time", "six"]]
            },
            "A4_deranged": {"mapping": {"iot": "email", "email": "iot"}},
        },
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_rosters_happy_path(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path)
    rosters = load_pslu_rosters(path)
    assert rosters.scenario_rosters["iot"] == (
        ("house_place", "kitchen"),
        ("device_type", "light"),
    )
    assert rosters.global_types == (
        "house_place",
        "device_type",
        "email_folder",
        "time",
    )
    assert rosters.full_roster == (("house_place", "kitchen"), ("time", "six"))
    assert rosters.derangement == {"iot": "email", "email": "iot"}


def test_load_pslu_rosters_rejects_wrong_probe(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, probe="P-A2T")
    with pytest.raises(PsluFlightError, match="probe must be"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_non_legal_tier(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(path, legality_tier="ceiling")
    with pytest.raises(PsluFlightError, match="legality_tier"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_rejects_nonzero_devel_overlap(tmp_path):
    path = tmp_path / "rosters.json"
    _write_roster_table(
        path, train_synthetic_refused={"train_jsonl_overlap_with_devel": 5}
    )
    with pytest.raises(PsluFlightError, match="overlap_with_devel"):
        load_pslu_rosters(path)


def test_load_pslu_rosters_against_the_real_binding_table():
    """The mission's own registered artifact -- proves this loader actually
    parses it, not merely a hand-shrunk test fixture."""

    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "probes"
        / "g0-binding"
        / "pslu-rosters-train-only.json"
    )
    rosters = load_pslu_rosters(path)
    assert "iot" in rosters.scenario_rosters
    assert len(rosters.global_types) == 55
    assert len(rosters.full_roster) == 100
    assert rosters.derangement["audio"] == "cooking"


# ---------------------------------------------------------------------------
# load_pslu_sample_manifest / select_pslu_samples
# ---------------------------------------------------------------------------


def _write_sample_manifest(path: Path, **overrides) -> None:
    document = {
        "probe": "P-SLU",
        "seed": 20260807,
        "split_identity_hash": "a" * 64,
        "items": [
            {"sample_id": "slurp:devel:000102:audio-102"},
            {"sample_id": "slurp:devel:000101:audio-101"},
        ],
    }
    document.update(overrides)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_load_pslu_sample_manifest_happy_path(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(path)
    manifest = load_pslu_sample_manifest(path)
    assert manifest.sample_ids == (
        "slurp:devel:000102:audio-102",
        "slurp:devel:000101:audio-101",
    )
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == "a" * 64


def test_load_pslu_sample_manifest_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "manifest.json"
    _write_sample_manifest(
        path,
        items=[{"sample_id": "x"}, {"sample_id": "x"}],
    )
    with pytest.raises(PsluFlightError, match="duplicate sample_id"):
        load_pslu_sample_manifest(path)


def test_load_pslu_sample_manifest_against_the_real_binding_table():
    path = (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "probes"
        / "g0-binding"
        / "pslu-sample-devel-n60.json"
    )
    manifest = load_pslu_sample_manifest(path)
    assert len(manifest.sample_ids) == 60
    assert manifest.seed == 20260807
    assert manifest.split_identity_hash == (
        "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"
    )


def test_select_pslu_samples_filters_and_reorders(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split(
        "devel"
    )  # sorted by sample_id: 101, 101-headset, 102
    manifest = PsluSampleManifest(
        sample_ids=("slurp:devel:000102:audio-102", "slurp:devel:000101:audio-101"),
        split_identity_hash="a" * 64,
        seed=1,
    )
    selected = select_pslu_samples(all_devel, manifest)
    assert [s.sample_id for s in selected] == list(manifest.sample_ids)


def test_select_pslu_samples_raises_on_a_missing_id(slurp_world):
    adapter = _adapter(slurp_world)
    all_devel = adapter.load_split("devel")
    manifest = PsluSampleManifest(
        sample_ids=("bogus-id",), split_identity_hash="a" * 64, seed=1
    )
    with pytest.raises(PsluFlightError, match="not present in the loaded split"):
        select_pslu_samples(all_devel, manifest)


# ---------------------------------------------------------------------------
# pslu_supply_packet -- per-arm roster selection
# ---------------------------------------------------------------------------


def test_a0_has_no_supply():
    assert pslu_supply_packet("A0", scenario=None, rosters=_ROSTERS) is None


def test_a1_uses_the_named_scenarios_roster():
    packet = pslu_supply_packet("A1", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; device_type=light"


def test_a1_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A1 requires"):
        pslu_supply_packet("A1", scenario=None, rosters=_ROSTERS)


def test_a1_unknown_scenario_raises():
    with pytest.raises(PsluFlightError, match="no A1 roster"):
        pslu_supply_packet("A1", scenario="bogus", rosters=_ROSTERS)


def test_a1p_uses_the_predicted_scenarios_roster():
    packet = pslu_supply_packet("A1p", scenario="email", rosters=_ROSTERS)
    assert packet.prompt_block == "email_folder=inbox"


def test_a1p_falls_back_to_a2_when_scenario_is_none():
    packet = pslu_supply_packet("A1p", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)
    assert packet.assembly_template_id == "pslu-A1p-fallback-A2-roster-v1"


def test_a1p_falls_back_to_a2_when_scenario_is_unknown():
    packet = pslu_supply_packet("A1p", scenario="not-a-real-scenario", rosters=_ROSTERS)
    assert packet.prompt_block == render_type_vocabulary(_ROSTERS.global_types)


def test_a2_is_the_global_type_vocabulary():
    packet = pslu_supply_packet("A2", scenario="iot", rosters=_ROSTERS)
    assert packet.prompt_block == "house_place, device_type, email_folder, time"


def test_a3_is_the_full_dose_capped_roster():
    packet = pslu_supply_packet("A3", scenario=None, rosters=_ROSTERS)
    assert packet.prompt_block == "house_place=kitchen; time=six"


def test_a4_uses_the_deranged_partners_roster():
    packet = pslu_supply_packet("A4", scenario="iot", rosters=_ROSTERS)
    assert (
        packet.prompt_block == "email_folder=inbox"
    )  # iot's deranged partner is email


def test_a4_without_a_scenario_raises():
    with pytest.raises(PsluFlightError, match="A4 requires"):
        pslu_supply_packet("A4", scenario=None, rosters=_ROSTERS)


def test_unknown_arm_raises():
    with pytest.raises(PsluFlightError, match="unknown P-SLU arm"):
        pslu_supply_packet("A99", scenario="iot", rosters=_ROSTERS)


# ---------------------------------------------------------------------------
# the ontology-miner call guard
# ---------------------------------------------------------------------------


def test_the_real_module_source_never_references_the_ontology_miner():
    assert_never_calls_ontology_miner()  # no args -- self-checks the real file


def test_guard_catches_a_live_import():
    source = "from ...data.slurp import load_slurp_ontology\n"
    assert _source_references_ontology_miner(source) is True
    with pytest.raises(PsluFlightError, match="load_slurp_ontology"):
        assert_never_calls_ontology_miner(source)


def test_guard_catches_a_bare_call():
    source = "def f(lock, root):\n    return load_slurp_ontology(lock, root)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_catches_an_attribute_access():
    source = "import speech_aware_evidence_acquisition.data.slurp as slurp\nslurp.load_slurp_ontology(1, 2)\n"
    assert _source_references_ontology_miner(source) is True


def test_guard_does_not_trip_on_a_docstring_mention():
    source = '"""This module never calls load_slurp_ontology -- see the docstring."""\nx = 1\n'
    assert _source_references_ontology_miner(source) is False
    assert_never_calls_ontology_miner(source)  # does not raise


# ---------------------------------------------------------------------------
# run_pslu_flight -- end to end
# ---------------------------------------------------------------------------


def _flight_world(slurp_world):
    adapter = _adapter(slurp_world)
    devel = adapter.load_split("devel")
    s_iot = devel[0]  # slurp:devel:000101:audio-101, gold scenario "iot"
    s_email = devel[2]  # slurp:devel:000102:audio-102, gold scenario "email"
    return adapter, s_iot, s_email


def _responder(s_iot):
    def responder(messages):
        content = messages[1]["content"]
        is_phase1 = (
            len(content) == 1
        )  # A0 sends audio only, every other arm prepends text
        if is_phase1:
            # Deliberately WRONG for s_iot (gold "iot") -- proves A1' reads
            # the phase-1 prediction, never the gold scenario.
            return json.dumps({"scenario": "email", "action": "query", "entities": []})
        return json.dumps({"scenario": "iot", "action": "hue_lighton", "entities": []})

    return responder


def test_run_pslu_flight_produces_a0_then_five_phase2_arms_per_sample(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS
    )

    assert [r.arm for r in summary.results] == [
        "A0",
        "A0",
        "A1",
        "A1p",
        "A2",
        "A3",
        "A4",
        "A1",
        "A1p",
        "A2",
        "A3",
        "A4",
    ]
    assert len(client.calls) == 12
    assert set(PSLU_ARMS) == {"A0", "A1", "A1p", "A2", "A3", "A4"}


def test_run_pslu_flight_a1_prime_reads_the_phase1_prediction_not_gold(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))

    summary = run_pslu_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS
    )

    assert (
        summary.predicted_scenario_by_sample_id[s_iot.sample_id] == "email"
    )  # wrong, as scripted
    assert (
        summary.predicted_scenario_by_sample_id[s_email.sample_id] == "email"
    )  # right

    a1_iot = next(
        r for r in summary.results if r.arm == "A1" and r.sample_id == s_iot.sample_id
    )
    a1p_iot = next(
        r
        for r in summary.results
        if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    a1_text = a1_iot.messages[1]["content"][0]["text"]
    a1p_text = a1p_iot.messages[1]["content"][0]["text"]
    assert a1_text == "house_place=kitchen; device_type=light"  # A1: gold "iot" roster
    assert (
        a1p_text == "email_folder=inbox"
    )  # A1': predicted "email" roster -- differs from A1
    assert a1_text != a1p_text


def test_run_pslu_flight_phase1_row_carries_whether_it_parsed(slurp_world):
    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    summary = run_pslu_flight(
        adapter=adapter, core_client=client, samples=[s_iot, s_email], rosters=_ROSTERS
    )
    a0_rows = [r for r in summary.results if r.arm == "A0"]
    assert all(row.phase1_scenario_parsed is True for row in a0_rows)
    phase2_rows = [r for r in summary.results if r.arm != "A0"]
    assert all(row.phase1_scenario_parsed is None for row in phase2_rows)


def test_run_pslu_flight_silence_swap_adds_one_extra_a1p_row(slurp_world):
    """``silence_swap_media_relpaths`` carries whatever media_relpath a REAL
    SliceRegistry actually produced for s_iot's raw, colon-bearing SLURP id
    (``slurp:devel:000101:audio-101``) -- not a hand-typed path the real
    registry could never build. This is the regression test for
    docs/checks/speech-aware-evidence-acquisition/2026-08-17-pslu-flight/
    2026-08-18-attempt2-flight-execution.md: the original version of this
    test hardcoded exactly the string the pre-fix registry refused to
    produce, so it hid the defect behind a green suite."""

    adapter, s_iot, s_email = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    assert ":" in s_iot.sample_id  # the defect only bites a colon-bearing raw id
    registry = SliceRegistry(
        data_root=slurp_world.data_root,
        run_id="run-x",
        parent_facts={s_iot.sample_id: (s_iot.media_relpath, s_iot.audio_seconds)},
    )
    silence_record = build_silence_swap_slice(
        registry=registry,
        data_root=slurp_world.data_root,
        sample_id=s_iot.sample_id,
        parent_media_relpath=s_iot.media_relpath,
        duration_seconds=s_iot.audio_seconds,
        sample_rate_hz=16000,
    )
    registry.register(silence_record)
    silence_relpath = silence_record.media_relpath
    assert ":" not in silence_relpath  # raw id sanitized into the filesystem token

    summary = run_pslu_flight(
        adapter=adapter,
        core_client=client,
        samples=[s_iot, s_email],
        rosters=_ROSTERS,
        silence_swap_media_relpaths={s_iot.sample_id: silence_relpath},
    )

    assert len(summary.results) == 13  # 12 base + 1 silence-swap
    swapped = [r for r in summary.results if r.silence_swapped]
    assert len(swapped) == 1
    assert swapped[0].arm == "A1p"
    assert swapped[0].sample_id == s_iot.sample_id
    assert swapped[0].messages[1]["content"][-1] == {
        "type": "input_audio",
        "media_relpath": silence_relpath,
    }
    # The roster text is UNCHANGED by the swap -- only the audio changes.
    normal_a1p = next(
        r
        for r in summary.results
        if r.arm == "A1p" and r.sample_id == s_iot.sample_id and not r.silence_swapped
    )
    assert swapped[0].messages[1]["content"][0] == normal_a1p.messages[1]["content"][0]


def test_run_pslu_flight_rejects_empty_samples(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    with pytest.raises(PsluFlightError, match="at least one sample"):
        run_pslu_flight(
            adapter=adapter, core_client=MockCoreClient(), samples=(), rosters=_ROSTERS
        )


def test_run_pslu_flight_rejects_unknown_silence_swap_sample_ids(slurp_world):
    adapter, s_iot, _ = _flight_world(slurp_world)
    client = MockCoreClient(responder=_responder(s_iot))
    with pytest.raises(PsluFlightError, match="outside this flight"):
        run_pslu_flight(
            adapter=adapter,
            core_client=client,
            samples=[s_iot],
            rosters=_ROSTERS,
            silence_swap_media_relpaths={"bogus-sample-id": "x.wav"},
        )


def test_model_free_read_reports_m7_multistate_action_support_and_safe_consensus(
    tmp_path,
):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    cards = {card["key_id"]: card for card in binding["key_cards"]}
    key_by_label = {card["value_label"]: card["key_id"] for card in cards.values()}
    label_by_key = {key_id: card["value_label"] for key_id, card in cards.items()}
    all_key_ids = tuple(cards)
    state_policy_ids = (
        "balanced-evidence-v1",
        "primary-challenge-v1",
        "retrieval-gap-v1",
    )
    rows = []
    for index, item in enumerate(items):
        gold_key = key_by_label[item["value_label"]]
        wrong_key = all_key_ids[(all_key_ids.index(gold_key) + 1) % len(all_key_ids)]
        primary_key = wrong_key if index == 0 else gold_key
        initial_top = list(
            dict.fromkeys((primary_key, gold_key, wrong_key, *all_key_ids))
        )[:3]
        branch_key = (
            gold_key if index == 0 else wrong_key if index == 1 else primary_key
        )
        branch_top = list(dict.fromkeys((branch_key, *initial_top, *all_key_ids)))[:3]
        branch_steps = []
        for state_policy_id in state_policy_ids:
            state = {
                "candidate_key_ids": initial_top,
                "domain": "personal productivity",
                "operation": "manage a requested item",
                "target": "requested object",
                "constraints": [],
                "exclusions": [],
                "unresolved_ambiguity": "none",
                "evidence": [
                    {
                        "key_id": key_id,
                        "field": "definition",
                        "quote": cards[key_id]["definition"],
                    }
                    for key_id in initial_top
                ],
            }
            selected_confidence = 25.0 if index == 1 else 90.0
            verifier_scores = {
                key_id: {
                    "compatible": key_id == branch_key,
                    "confidence": selected_confidence if key_id == branch_key else 10.0,
                }
                for key_id in branch_top
            }
            branch_steps.append(
                {
                    "action_id": f"explore:{state_policy_id}",
                    "state_policy_id": state_policy_id,
                    "key_id": branch_key,
                    "top_key_ids": branch_top,
                    "calls": 5,
                    "parse_failure": False,
                    "grounded_query_state": state,
                    "verifier_scores": verifier_scores,
                    "causal_parent_ids": [
                        "match:speech-only-primary",
                        "retrieve:speech-only",
                    ],
                }
            )
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": item["sample_id"],
                "key_id": primary_key,
                "predicted_value_label": label_by_key[primary_key],
                "top_key_ids": initial_top,
                "verifier_scores": {},
                "calls": 17,
                "parse_failure": False,
                "agent_policy_id": "knowledge-grounded-multistate-action-support-v1",
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    "explore:balanced-evidence-v1",
                    "explore:primary-challenge-v1",
                    "explore:retrieval-gap-v1",
                    "select:retain-primary-for-support",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": [primary_key, branch_key, branch_key, branch_key],
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": primary_key,
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": initial_top[0],
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                    },
                    *branch_steps,
                ],
                "agent_aggregator_id": "action-support-primary-control-v1",
            }
        )

    attempt_dir = tmp_path / "m7-multistate"
    attempt_dir.mkdir()
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (attempt_dir / "flight-receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "request_failures": [],
                "split_identity_hash": "a" * 64,
                "run_id": "run-m7-multistate",
                "profile": {
                    "key_representation_id": "K1",
                    "matcher_policy_id": "M7",
                    "matcher_prompt_policy_id": "speech-native-json-copy-v3",
                    "matcher_verifier_policy_id": "speech-native-contrastive-verifier-v2",
                    "agent_policy_id": "knowledge-grounded-multistate-action-support-v1",
                    "agent_aggregator_id": "action-support-primary-control-v1",
                    "mechanism_control_id": "matched",
                    "key_order_ids": ["canonical"],
                    "top_k": 3,
                    "actual_contact_count": sum(row["calls"] for row in rows),
                },
                "decisions": {
                    "path": decisions.name,
                    "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                    "count": len(rows),
                },
            }
        ),
        encoding="utf-8",
    )

    report = read_speech_native_predictions(
        attempt_dirs=(attempt_dir,),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )

    aggregate = report["aggregates"][0]
    assert aggregate["cell_id"] == (
        "K1-M7-k3-v3-verify-contrastive-v2-multistate-support-v1"
    )
    assert aggregate["correct"] == 35
    metrics = aggregate["agent_loop_metrics"]
    assert metrics["primary_correct"] == 35
    assert metrics["action_variable_query_count"] == 2
    assert metrics["oracle_correct"] == 36
    assert metrics["oracle_gain_vs_primary"] == 1
    assert metrics["support_gate_passed"] is False
    assert [branch["selected_correct"] for branch in metrics["branch_policies"]] == [
        35,
        35,
        35,
    ]
    controller = metrics["consistency_controller"]
    assert controller["correct"] == 36
    assert controller["correct_delta_vs_primary"] == 1
    assert controller["wrong_to_correct_vs_primary"] == 1
    assert controller["correct_to_wrong_vs_primary"] == 0
    assert controller["action_count"] == 1
    assert controller["qualified"] is False


def test_model_free_read_reports_m8_pairwise_boundary_support(tmp_path):
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/speech-native-train-binding.json"
    )
    binding_sha256 = hashlib.sha256(binding_path.read_bytes()).hexdigest()
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    items = binding["splits"]["OPT-A36"]["items"]
    cards = {card["key_id"]: card for card in binding["key_cards"]}
    key_by_label = {card["value_label"]: card["key_id"] for card in cards.values()}
    label_by_key = {key_id: card["value_label"] for key_id, card in cards.items()}
    all_key_ids = tuple(cards)
    rows = []
    for index, item in enumerate(items):
        gold_key = key_by_label[item["value_label"]]
        wrong_key = all_key_ids[(all_key_ids.index(gold_key) + 1) % len(all_key_ids)]
        primary_key = wrong_key if index < 4 else gold_key
        initial_top = list(
            dict.fromkeys((primary_key, gold_key, wrong_key, *all_key_ids))
        )[:3]
        challengers = [key_id for key_id in initial_top if key_id != primary_key]
        comparison_steps = []
        support_votes = [primary_key]
        for rank, challenger_key in enumerate(challengers, start=1):
            k1_supports = index == 0 and rank == 1 and challenger_key == gold_key
            k2_supports = index < 3 and rank == 1 and challenger_key == gold_key
            k1_vote = challenger_key if k1_supports else primary_key
            k2_vote = challenger_key if k2_supports else primary_key
            k1_stable = challenger_key if k1_supports else None
            k2_stable = challenger_key if k2_supports else None
            support_votes.extend((k1_stable, k2_stable))
            comparison_steps.append(
                {
                    "action_id": f"compare:pairwise-boundary-rank-{rank}",
                    "rank": rank,
                    "primary_key_id": primary_key,
                    "challenger_key_id": challenger_key,
                    "k1_ab_key_id": k1_vote,
                    "k1_ba_key_id": k1_vote,
                    "k1_stable_key_id": k1_stable,
                    "k2_ab_key_id": k2_vote,
                    "k2_ba_key_id": k2_vote,
                    "k2_stable_key_id": k2_stable,
                    "calls": 4,
                    "parse_failure": False,
                    "causal_parent_ids": [
                        "match:speech-only-primary",
                        "retrieve:speech-only",
                    ],
                }
            )
        rows.append(
            {
                "schema": "saea-speech-native-decision-v1",
                "sample_id": item["sample_id"],
                "key_id": primary_key,
                "predicted_value_label": label_by_key[primary_key],
                "top_key_ids": initial_top,
                "verifier_scores": {},
                "calls": 2 + 4 * len(challengers),
                "parse_failure": False,
                "agent_policy_id": "speech-conditioned-pairwise-boundary-support-v1",
                "agent_actions": [
                    "match:speech-only-primary",
                    "retrieve:speech-only",
                    *[
                        f"compare:pairwise-boundary-rank-{rank}"
                        for rank in range(1, len(challengers) + 1)
                    ],
                    "select:retain-primary-for-support",
                ],
                "agent_escalated": True,
                "agent_vote_key_ids": support_votes,
                "agent_steps": [
                    {
                        "action_id": "match:speech-only-primary",
                        "key_id": primary_key,
                        "top_key_ids": [],
                        "calls": 1,
                        "parse_failure": False,
                    },
                    {
                        "action_id": "retrieve:speech-only",
                        "key_id": initial_top[0],
                        "top_key_ids": initial_top,
                        "calls": 1,
                        "parse_failure": False,
                    },
                    *comparison_steps,
                ],
                "agent_aggregator_id": "pairwise-boundary-primary-control-v1",
            }
        )

    attempt_dir = tmp_path / "m8-pairwise"
    attempt_dir.mkdir()
    decisions = attempt_dir / "decisions.jsonl"
    decisions.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (attempt_dir / "flight-receipt.json").write_text(
        json.dumps(
            {
                "status": "COMPLETED",
                "request_failures": [],
                "split_identity_hash": "a" * 64,
                "run_id": "run-m8-pairwise",
                "profile": {
                    "key_representation_id": "K1",
                    "matcher_policy_id": "M8",
                    "matcher_prompt_policy_id": "speech-native-json-copy-v4",
                    "matcher_verifier_policy_id": "speech-native-compatibility-v1",
                    "agent_policy_id": "speech-conditioned-pairwise-boundary-support-v1",
                    "agent_aggregator_id": "pairwise-boundary-primary-control-v1",
                    "mechanism_control_id": "matched",
                    "key_order_ids": ["canonical"],
                    "top_k": 3,
                    "actual_contact_count": sum(row["calls"] for row in rows),
                },
                "decisions": {
                    "path": decisions.name,
                    "sha256": hashlib.sha256(decisions.read_bytes()).hexdigest(),
                    "count": len(rows),
                },
            }
        ),
        encoding="utf-8",
    )

    report = read_speech_native_predictions(
        attempt_dirs=(attempt_dir,),
        binding_path=binding_path,
        binding_sha256=binding_sha256,
        split_name="OPT-A36",
    )

    aggregate = report["aggregates"][0]
    assert aggregate["cell_id"] == ("K1-M8-k3-v4-pairwise-boundary-support-v1")
    assert aggregate["correct"] == 32
    metrics = aggregate["agent_loop_metrics"]
    assert metrics["primary_correct"] == 32
    assert metrics["representations"]["K1"]["helpful_action_count"] == 1
    assert metrics["representations"]["K2"]["helpful_action_count"] == 3
    assert metrics["representations"]["K2"]["stable_non_primary_query_count"] == 3
    assert metrics["oracle_correct"] == 35
    assert metrics["oracle_gain_vs_primary"] == 3
    assert metrics["support_gate_passed"] is False
    controller = metrics["consistency_controller"]
    assert controller["correct"] == 33
    assert controller["correct_delta_vs_primary"] == 1
    assert controller["wrong_to_correct_vs_primary"] == 1
    assert controller["correct_to_wrong_vs_primary"] == 0
    assert controller["action_count"] == 1
    assert controller["qualified"] is False
