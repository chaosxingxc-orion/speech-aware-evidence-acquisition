"""``rails.probes.pslu_flight``: the P-SLU six-arm, two-phase flight
orchestration (docs/readiness/2026-08-17-pslu-preregistration-REGISTERED.md).
Engineering-only, zero live model contact -- every test drives a
``MockCoreClient``.
"""

from __future__ import annotations

from collections import Counter
import json
import hashlib
import sys
import threading
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.model import (
    FrozenCoreAdapter,
    SliceRegistry,
)
from speech_aware_evidence_acquisition.core.resources import NOT_AVAILABLE
from speech_aware_evidence_acquisition.core.driver.speech_native import (
    audit_speech_native_action_support,
    _assert_reusable_session_profile,
    _audit_cuda_graph_moe_compatibility,
    _canonical_sha256,
    _evaluate_training_free_contextual_policy,
    _evaluate_training_free_episodic_policy,
    _evaluate_training_free_grounded_semantic_policy,
    _build_audio_key_bindings,
    _evaluate_training_free_agent_policies,
    _inspect_gguf_moe_metadata,
    _evaluate_m9_factor_graph_action_support,
    _evaluate_m10_candidate_evidence_action_support,
    _evaluate_m11_adaptive_evidence_gap,
    _evaluate_m11_memory_holdout_action_advantage_policy,
    _evaluate_m11_oof_action_advantage_policy,
    _audit_m11_prompt_fit,
    _m11_prompt_text_token_count,
    _enumerate_m11_prompt_envelopes,
    _wire_m11_prompt_envelope,
    _m11_reader_contract_from_values,
    _load_key_cards,
    _load_m11_prompt_fit_receipt,
    _resolve_m11_prompt_fit_config,
    _validate_m11_prompt_fit_for_profile,
    _load_decision_graph,
    _parse_m9_factor_graph_trajectory,
    _parse_m10_candidate_evidence_trajectory,
    _parse_m11_adaptive_evidence_gap_trajectory,
    _profile_completion_issues,
    _release_speech_native_session,
    _scan_server_log,
    profile_evaluated_work_metrics,
    profile_agent_kv_policy,
    profile_prompt_work_eligibility,
    profile_prompt_work_policy,
    _trace_speech_query_summary,
    SpeechNativeProfileError,
    _cli_speech_native_action_audit,
    _cli_speech_native_engine_audit,
    build_profile_tasks,
    profile_gpu_eligibility,
    profile_server_slot_event_gpu_metrics,
    profile_saturated_gpu_metrics,
    profile_timing_metrics,
    read_speech_native_predictions,
)
from speech_aware_evidence_acquisition.core.driver import (
    cli as driver_cli_module,
    speech_native as speech_native_module,
)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan, STUDY_SLUG
from speech_aware_evidence_acquisition.core.config import protocol_hash
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
from speech_aware_evidence_acquisition.rails import (
    AudioRef,
    FrozenCoreClient,
    KeyFacet,
    KnowledgeSnapshot,
    MockCoreClient,
    ValueBundle,
)
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
    build_speech_native_information_audit,
    build_speech_native_binding,
    build_speech_native_knowledge_snapshot,
    audit_speech_native_scale_capacity,
    candidate_action_state_response_format,
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
    partition_speech_native_train_knowledge,
    render_decision_graph_neighborhood,
    render_factor_link_state,
    render_roster_entries,
    render_speech_native_keys,
    render_type_vocabulary,
    run_openjiuwen_speech_native_match_tasks,
    run_pslu_flight,
    select_pslu_samples,
    run_speech_native_matcher,
    SpeechNativeMatchTask,
    run_speech_native_match_tasks,
    SpeechNativeEngineeringSample,
)
from speech_aware_evidence_acquisition.rails.probes import pslu_flight as pslu_module
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
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
        "decoded cross-slot speech feature batch, n_slots = 2, n_tokens = 91\n"
    )
    log.write_text(old + current, encoding="utf-8")

    scan = _scan_server_log(log, start_offset=len(old.encode("utf-8")))

    assert scan["oom_marker_hits"] == []
    assert scan["mmproj_free_chunk_count"] == 2
    assert scan["speech_feature_batch_count"] == 1
    assert scan["speech_feature_batch_slot_count_total"] == 2
    assert scan["speech_feature_batch_token_count_total"] == 91
    assert scan["speech_feature_batch_mean_slots"] == 2.0
    assert scan["prompt_eval_record_count"] == 0
    assert scan["prompt_eval_tokens_total"] == 0
    assert scan["one_token_prompt_eval_count"] == 0
    assert scan["prompt_cache_skip_count"] == 0
    assert scan["speculative_draft_record_count"] == 0
    assert scan["speculative_draft_generated_tokens_total"] == 0
    assert scan["speculative_draft_accepted_tokens_total"] == 0
    assert scan["speculative_draft_acceptance_ratio_pct"] == NOT_AVAILABLE
    assert scan["speculative_mean_acceptance_length_median"] == NOT_AVAILABLE


def test_server_log_scan_records_actual_prompt_work_and_cache_reuse(tmp_path):
    log = tmp_path / "resident-server.log"
    old = "prompt eval time = 10.00 ms / 999 tokens\n"
    current = """\
prompt eval time = 20.00 ms / 1870 tokens
prompt is already in the cache, skipping
prompt eval time = 1.00 ms / 1 tokens
prompt is already in the cache, skipping
prompt eval time = 8.00 ms / 740 tokens
"""
    log.write_text(old + current, encoding="utf-8")

    scan = _scan_server_log(log, start_offset=len(old.encode("utf-8")))

    assert scan["prompt_eval_record_count"] == 3
    assert scan["prompt_eval_tokens_total"] == 2611
    assert scan["prompt_eval_tokens_median"] == 740.0
    assert scan["one_token_prompt_eval_count"] == 1
    assert scan["prompt_cache_skip_count"] == 2


def test_prompt_work_eligibility_keeps_the_historical_cold_work_gate():
    work = {
        "prompt_eval_record_count_matches_contacts": True,
        "prompt_evaluation_ratio_pct": 96.5,
        "one_token_prompt_eval_fraction_pct": 0.0,
    }

    assert profile_prompt_work_policy("speech-features-text-keys-v1") == (
        "cold-evaluation-v1"
    )
    assert profile_prompt_work_eligibility(
        work, prompt_order="speech-features-text-keys-v1"
    ) == {
        "prompt_eval_records_match_contacts": True,
        "prompt_evaluation_ratio_at_least_90": True,
        "one_token_prompt_eval_fraction_at_most_5": True,
    }


@pytest.mark.parametrize(
    "prompt_order",
    ("speech-query-prefix-v2", "knowledge-speech-state-v2"),
)
def test_prompt_work_eligibility_treats_avoided_work_as_prefix_reuse(
    prompt_order,
):
    work = {
        "prompt_eval_record_count_matches_contacts": True,
        "prompt_evaluation_ratio_pct": 58.8,
        "one_token_prompt_eval_fraction_pct": 0.0,
    }

    assert profile_prompt_work_policy(prompt_order) == "prefix-reuse-v1"
    assert profile_prompt_work_eligibility(work, prompt_order=prompt_order) == {
        "prompt_eval_records_match_contacts": True,
        "prompt_evaluation_ratio_below_90": True,
        "one_token_prompt_eval_fraction_at_most_5": True,
    }


def test_prompt_work_eligibility_rejects_malformed_mechanics():
    work = {
        "prompt_eval_record_count_matches_contacts": True,
        "prompt_evaluation_ratio_pct": "NOT_AVAILABLE",
        "one_token_prompt_eval_fraction_pct": 0.0,
    }

    assert (
        profile_prompt_work_eligibility(work, prompt_order="speech-query-prefix-v2")[
            "prompt_evaluation_ratio_below_90"
        ]
        is False
    )


def test_prefix_agent_kv_policy_keeps_active_trajectories_in_hbm():
    policy = profile_agent_kv_policy(
        [
            "--cache-prompt",
            "--cache-ram",
            "0",
            "--no-cache-idle-slots",
        ],
        prompt_order="speech-query-prefix-v2",
    )

    assert policy == {
        "policy_id": "active-hbm-only-v1",
        "active_kv_residency": "gpu-hbm",
        "cpu_cold_tier_enabled": False,
        "host_prompt_state_serialization": False,
        "per_slot_hbm_cpu_migration_supported": False,
    }


@pytest.mark.parametrize(
    "server_args",
    (
        [
            "--cache-prompt",
            "--cache-ram",
            "0",
            "--no-cache-idle-slots",
            "--no-kv-offload",
        ],
        ["--cache-prompt", "--cache-ram", "8", "--no-cache-idle-slots"],
        ["--cache-prompt", "--cache-ram", "0"],
    ),
)
def test_prefix_agent_kv_policy_refuses_unsafe_cpu_state_paths(server_args):
    with pytest.raises(SpeechNativeProfileError, match="active-hbm-only"):
        profile_agent_kv_policy(
            server_args,
            prompt_order="knowledge-speech-state-v2",
        )


def test_server_log_scan_records_target_verified_speculative_work(tmp_path):
    log = tmp_path / "resident-server.log"
    old = (
        "draft acceptance = 1.00000 (    7 accepted /     7 generated), "
        "mean acceptance length =  8.00, acceptance rate per position = (1.000)\n"
    )
    current = """\
draft acceptance = 0.44444 (    4 accepted /     9 generated), mean acceptance length =  2.33, acceptance rate per position = (0.800, 0.400)
draft acceptance = 1.00000 (    6 accepted /     6 generated), mean acceptance length =  4.00, acceptance rate per position = (1.000, 1.000)
"""
    log.write_text(old + current, encoding="utf-8")

    scan = _scan_server_log(log, start_offset=len(old.encode("utf-8")))

    assert scan["speculative_draft_record_count"] == 2
    assert scan["speculative_draft_generated_tokens_total"] == 15
    assert scan["speculative_draft_accepted_tokens_total"] == 10
    assert scan["speculative_draft_acceptance_ratio_pct"] == pytest.approx(
        66.66666666666667
    )
    assert scan["speculative_mean_acceptance_length_median"] == 3.165


@pytest.mark.parametrize(
    "line",
    (
        "draft acceptance = unavailable\n",
        "draft acceptance = 1.20000 (    6 accepted /     5 generated), "
        "mean acceptance length =  4.00\n",
        "draft acceptance = 0.50000 (    4 accepted /     9 generated), "
        "mean acceptance length =  2.33\n",
    ),
)
def test_server_log_scan_rejects_untrustworthy_speculative_statistics(tmp_path, line):
    log = tmp_path / "resident-server.log"
    log.write_text(line, encoding="utf-8")

    with pytest.raises(SpeechNativeProfileError, match="speculative draft statistics"):
        _scan_server_log(log)


def test_evaluated_work_metrics_do_not_count_cached_declared_tokens_as_compute():
    metrics = profile_evaluated_work_metrics(
        server_scan={
            "prompt_eval_record_count": 3,
            "prompt_eval_tokens_total": 2611,
            "prompt_eval_tokens_median": 740.0,
            "one_token_prompt_eval_count": 1,
            "prompt_cache_skip_count": 2,
        },
        declared_prompt_tokens=3000,
        completion_tokens=89,
        wall_seconds=2.0,
        contact_count=3,
    )

    assert metrics == {
        "declared_prompt_tokens": 3000,
        "evaluated_prompt_tokens": 2611,
        "prompt_evaluation_ratio_pct": pytest.approx(87.03333333333333),
        "prompt_eval_record_count": 3,
        "prompt_eval_record_count_matches_contacts": True,
        "one_token_prompt_eval_count": 1,
        "one_token_prompt_eval_fraction_pct": pytest.approx(33.333333333333336),
        "prompt_cache_skip_count": 2,
        "actual_evaluated_tokens_per_second": 1350.0,
    }


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


def _openjiuwen_m1_plan(
    sample_count: int = 1,
    contacts_per_sample: int = 1,
) -> ExecutionPlan:
    return ExecutionPlan(
        run_id="SAEA-E-TEST-speech-native-openjiuwen-m1",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="slurp",
        split_role="discovery",
        split_identity_hash="a" * 64,
        planned_model_calls=sample_count * contacts_per_sample,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=60,
        protocol_hash=protocol_hash("f" * 64, "speech-feature-query", "a" * 64),
        attempt_id="attempt-speech-native-openjiuwen-m1-0001",
    ).validate()


def _openjiuwen_m1_snapshot(
    source_ids: tuple[str, ...] = (
        "slurp:train:knowledge-1",
        "slurp:train:knowledge-2",
    ),
) -> KnowledgeSnapshot:
    facets = tuple(
        KeyFacet(
            facet_id=f"facet:K{index:03d}",
            dimension="scenario",
            representation_kind="text",
            representation=(
                f"Definition: {card.definition}\n"
                f"Positive examples: {' | '.join(card.positive_examples)}\n"
                f"Contrastive boundary: {card.contrastive_boundary}"
            ),
            source_sample_ids=(source_id,),
        ).validate()
        for index, (card, source_id) in enumerate(
            zip(_KEY_CARDS, source_ids, strict=True), start=1
        )
    )
    values = tuple(
        ValueBundle(
            value_id=f"value:{card.key_id}",
            content=(
                f"Definition: {card.definition}\n"
                f"Positive examples: {' | '.join(card.positive_examples)}\n"
                f"Contrastive boundary: {card.contrastive_boundary}"
            ),
            associated_facet_ids=(facet.facet_id,),
            source_sample_ids=(source_id,),
            provenance_refs=(f"sample:{source_id}",),
            task_target=card.value_label,
        ).validate()
        for card, facet, source_id in zip(_KEY_CARDS, facets, source_ids, strict=True)
    )
    return KnowledgeSnapshot(
        snapshot_id="slurp-train-knowledge-test-v1",
        source_split_identity_hash="b" * 64,
        source_sample_ids=source_ids,
        builder_policy_id="test-train-builder-v1",
        facets=facets,
        values=values,
    ).validate()


def _openjiuwen_m1_sample() -> SpeechNativeEngineeringSample:
    return SpeechNativeEngineeringSample(
        sample_id="slurp:dev:000001:audio-query",
        audio_ref=AudioRef(path="query.flac", sha256="c" * 64).validate(),
        audio_seconds=2.5,
        media_relpath="query.flac",
        sample_rate_hz=16000,
        packet_id="slurp/dev/000001/audio-query",
    )


def _openjiuwen_m1_task(
    *, matcher_policy_id: str = "M1", key_representation_id: str = "K2"
) -> SpeechNativeMatchTask:
    sample = _openjiuwen_m1_sample()
    return SpeechNativeMatchTask(
        task_id=f"canonical:{sample.sample_id}",
        sample=sample,
        query_descriptor={
            "packet_id": sample.packet_id,
            "sha256": "d" * 64,
            "role": "query",
        },
        key_cards=_KEY_CARDS,
        key_representation_id=key_representation_id,
        matcher_policy_id=matcher_policy_id,
        request_layout_id="slot-affine-speech-prefix-v1",
        decoding_params={"temperature": 0.0, "id_slot": 99},
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="openJiuwen is optional")
def test_openjiuwen_m1_profile_uses_formal_agent_loop_and_original_speech(tmp_path):
    class RecordingCoreClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, **kwargs):
            self.calls.append((messages, kwargs))
            return '{"key_id":"K001"}'

    client = RecordingCoreClient()
    trace_records = []
    task = _openjiuwen_m1_task()
    outcomes = run_openjiuwen_speech_native_match_tasks(
        data_root=tmp_path,
        plan=_openjiuwen_m1_plan(),
        core_client=client,
        tasks=(task,),
        knowledge_snapshot=_openjiuwen_m1_snapshot(),
        slot_count=1,
        queue_depth=2,
        trace_flusher=lambda buffer: trace_records.extend(buffer.records),
    )

    assert len(outcomes) == 1
    assert outcomes[0].decision.key_id == "K001"
    assert outcomes[0].decision.value_label == "alarm"
    assert outcomes[0].decision.calls == 1
    assert outcomes[0].decision.raw_responses == ('{"key_id":"K001"}',)
    assert len(client.calls) == 1
    messages, kwargs = client.calls[0]
    content = messages[1]["content"]
    query_parts = [
        part for part in content if part.get("type") == "input_speech_features"
    ]
    assert query_parts == [
        {
            "type": "input_speech_features",
            "speech_features": task.query_descriptor,
        }
    ]
    key_parts = [part for part in content if part.get("type") == "text"]
    assert key_parts
    assert all(part["knowledge_role"] == "key" for part in key_parts)
    assert all(part["evidence_id"].startswith("key:facet:") for part in key_parts)
    assert all("value:" not in part["evidence_id"] for part in key_parts)
    assert all(part.get("type") != "input_audio" for part in content)
    assert kwargs["speech_feature_sample_id"] == task.sample.sample_id
    assert kwargs["agent_contact_id"].endswith(":listwise")
    assert "speech signal" in kwargs["contact_instruction"]
    assert kwargs["decoding_params"]["id_slot"] == 0
    assert kwargs["matcher_policy_id"] == "M1:openjiuwen-listwise-v1"
    runtime_records = [
        payload
        for channel, record_id, payload in trace_records
        if channel == "USE" and record_id.endswith("/runtime-use")
    ]
    assert len(runtime_records) == 1
    assert runtime_records[0]["use_agent_executor_id"] == "openjiuwen-workflow-v1"
    assert runtime_records[0]["use_speech_packet_sha256"] == "d" * 64
    supply_records = [
        payload
        for channel, record_id, payload in trace_records
        if channel == "SUPPLY" and record_id.endswith("/supply")
    ]
    assert supply_records[0]["supply_bootstrap_facet_ids"]
    assert supply_records[0]["supply_bootstrap_value_ids"] == []


@pytest.mark.skipif(not openjiuwen_available(), reason="openJiuwen is optional")
def test_openjiuwen_m2_adds_semantic_state_but_keeps_speech_on_both_contacts(
    tmp_path,
):
    semantic_response = json.dumps(
        {
            "intent_summary": "The speaker wants an alarm action.",
            "discriminative_cues": ["wake time", "alarm"],
        }
    )

    class RecordingCoreClient:
        def __init__(self):
            self.calls = []

        def complete(self, messages, **kwargs):
            self.calls.append((messages, kwargs))
            if kwargs["agent_contact_id"].endswith(":semantic-state"):
                return semantic_response
            return '{"key_id":"K001"}'

    client = RecordingCoreClient()
    task = _openjiuwen_m1_task(matcher_policy_id="M2")
    outcomes = run_openjiuwen_speech_native_match_tasks(
        data_root=tmp_path,
        plan=_openjiuwen_m1_plan(contacts_per_sample=2),
        core_client=client,
        tasks=(task,),
        knowledge_snapshot=_openjiuwen_m1_snapshot(),
        slot_count=2,
        queue_depth=4,
    )

    assert len(client.calls) == 2
    assert outcomes[0].decision.key_id == "K001"
    assert outcomes[0].decision.calls == 2
    assert outcomes[0].decision.raw_responses == (
        semantic_response,
        '{"key_id":"K001"}',
    )
    assert {kwargs["decoding_params"]["id_slot"] for _, kwargs in client.calls} == {0}
    for messages, _kwargs in client.calls:
        query_parts = [
            part
            for part in messages[1]["content"]
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert len(query_parts) == 1
    first_text_parts = [
        part for part in client.calls[0][0][1]["content"] if part.get("type") == "text"
    ]
    second_text_parts = [
        part for part in client.calls[1][0][1]["content"] if part.get("type") == "text"
    ]
    assert first_text_parts == []
    assert second_text_parts
    assert all(part["knowledge_role"] == "key" for part in second_text_parts)
    assert client.calls[0][1]["agent_state"] == ()
    assert client.calls[1][1]["agent_state"][0]["content"] == semantic_response


@pytest.mark.skipif(not openjiuwen_available(), reason="openJiuwen is optional")
def test_openjiuwen_m1_profile_batches_existing_tasks_across_slots(tmp_path):
    first = _openjiuwen_m1_task()
    second_sample = replace(
        first.sample,
        sample_id="slurp:dev:000002:audio-query",
        packet_id="slurp/dev/000002/audio-query",
    )
    second = replace(
        first,
        task_id=f"canonical:{second_sample.sample_id}",
        sample=second_sample,
        query_descriptor={
            "packet_id": second_sample.packet_id,
            "sha256": "e" * 64,
            "role": "query",
        },
    )

    class ConcurrentCoreClient:
        def __init__(self):
            self.lock = threading.Lock()
            self.active = 0
            self.max_active = 0
            self.sample_ids = []

        def complete(self, messages, **kwargs):
            del messages
            with self.lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.sample_ids.append(kwargs["speech_feature_sample_id"])
            try:
                time.sleep(0.02)
                return '{"key_id":"K001"}'
            finally:
                with self.lock:
                    self.active -= 1

    client = ConcurrentCoreClient()
    outcomes = run_openjiuwen_speech_native_match_tasks(
        data_root=tmp_path,
        plan=_openjiuwen_m1_plan(sample_count=2),
        core_client=client,
        tasks=(first, second),
        knowledge_snapshot=_openjiuwen_m1_snapshot(),
        slot_count=2,
        queue_depth=4,
    )

    assert [outcome.task_id for outcome in outcomes] == [
        first.task_id,
        second.task_id,
    ]
    assert client.max_active == 2
    assert set(client.sample_ids) == {first.sample.sample_id, second.sample.sample_id}
    assert {outcome.slot_id for outcome in outcomes} == {0, 1}


def test_openjiuwen_profile_refuses_unsupported_policy_before_core_contact(tmp_path):
    class RefusingCoreClient:
        def complete(self, *args, **kwargs):
            raise AssertionError("unsupported policy must fail before model contact")

    with pytest.raises(PsluFlightError, match="only supports M1/M2 with K2 text keys"):
        run_openjiuwen_speech_native_match_tasks(
            data_root=tmp_path,
            plan=_openjiuwen_m1_plan(),
            core_client=RefusingCoreClient(),
            tasks=(_openjiuwen_m1_task(matcher_policy_id="M11"),),
            knowledge_snapshot=_openjiuwen_m1_snapshot(),
            slot_count=1,
            queue_depth=2,
        )


def test_openjiuwen_profile_refuses_train_use_overlap_before_core_contact(tmp_path):
    class RefusingCoreClient:
        def complete(self, *args, **kwargs):
            raise AssertionError("overlap must fail before model contact")

    task = _openjiuwen_m1_task()
    overlapping_snapshot = _openjiuwen_m1_snapshot(
        (task.sample.sample_id, "slurp:train:knowledge-2")
    )
    with pytest.raises(PsluFlightError, match="overlap the TRAIN knowledge source"):
        run_openjiuwen_speech_native_match_tasks(
            data_root=tmp_path,
            plan=_openjiuwen_m1_plan(),
            core_client=RefusingCoreClient(),
            tasks=(task,),
            knowledge_snapshot=overlapping_snapshot,
            slot_count=1,
            queue_depth=2,
        )


def test_train_knowledge_partition_removes_use_utterance_speaker_and_sentence_groups():
    query = SlurpTrainMaterial(
        utterance_id="use-utterance",
        scenario="alarm",
        action="set",
        sentence="set an alarm for six",
        recordings=(
            SlurpTrainRecording(
                sample_id="slurp:train:000001:audio-use",
                media_relpath="datasets/slurp/slurp_real/audio-use.flac",
                speaker_id="speaker-use",
            ),
        ),
    )
    same_speaker = replace(
        query,
        utterance_id="train-same-speaker",
        sentence="set a different alarm",
        recordings=(
            replace(
                query.recordings[0],
                sample_id="slurp:train:000002:audio-same-speaker",
                media_relpath="datasets/slurp/slurp_real/audio-same-speaker.flac",
            ),
        ),
    )
    same_sentence = replace(
        query,
        utterance_id="train-same-sentence",
        recordings=(
            replace(
                query.recordings[0],
                sample_id="slurp:train:000003:audio-same-sentence",
                media_relpath="datasets/slurp/slurp_real/audio-same-sentence.flac",
                speaker_id="speaker-train-3",
            ),
        ),
    )
    retained = replace(
        query,
        utterance_id="train-retained",
        sentence="cancel the morning alarm",
        recordings=(
            replace(
                query.recordings[0],
                sample_id="slurp:train:000004:audio-retained",
                media_relpath="datasets/slurp/slurp_real/audio-retained.flac",
                speaker_id="speaker-train-4",
            ),
        ),
    )

    partition = partition_speech_native_train_knowledge(
        (query, same_speaker, same_sentence, retained),
        use_sample_ids=(query.recordings[0].sample_id,),
    )

    assert partition == (retained,)


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


def test_m11_key_conditioned_action_schema_binds_operation_factors_to_each_key():
    response_format = candidate_action_state_response_format(
        graph=_decision_graph_fixture(),
        candidate_key_ids=("K001", "K002"),
        key_conditioned=True,
    )

    schema = response_format["json_schema"]["schema"]
    assert "oneOf" in schema
    branches = {
        branch["properties"]["key_id"]["const"]: branch for branch in schema["oneOf"]
    }
    assert set(branches) == {"K001", "K002"}
    assert branches["K001"]["properties"]["factor_ids"]["prefixItems"] == [
        {"enum": ["F002"]}
    ]
    assert branches["K001"]["properties"]["factor_ids"]["items"] == {
        "enum": ["F001", "F002"]
    }
    assert branches["K002"]["properties"]["factor_ids"]["prefixItems"] == [
        {"enum": ["F004"]}
    ]
    assert branches["K002"]["properties"]["factor_ids"]["items"] == {
        "enum": ["F003", "F004"]
    }


def test_m11_v2_pushes_key_factor_binding_into_the_llama_cpp_grammar():
    client = _M11AdaptiveEvidenceClient(agree=True)
    result = run_speech_native_matcher(
        core_client=client,
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v2",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )

    action_messages, action_kwargs = next(
        (messages, kwargs)
        for messages, kwargs in client.calls
        if kwargs["matcher_policy_id"].endswith(":candidate-action-state")
    )
    schema = action_kwargs["decoding_params"]["response_format"]["json_schema"][
        "schema"
    ]
    assert "oneOf" in schema
    assert "first factor id must be an operation" in json.dumps(action_messages).lower()
    assert result.calls == 3
    assert result.agent_policy_id == "speech-conditioned-adaptive-evidence-gap-v2"
    _assert_every_call_carries_query(client)


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


def test_m11_contact_dispatch_preserves_the_v2_key_conditioned_grammar():
    tasks = tuple(
        SpeechNativeMatchTask(
            task_id=f"m11-v2-{index}",
            sample=type("Sample", (), {"sample_id": f"m11-v2-sample-{index}"})(),
            query_descriptor={
                "packet_id": f"slurp/train/m11-v2-sample-{index}",
                "sha256": f"{index + 1:064x}",
                "role": "query",
            },
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M11",
            prompt_policy_id="speech-native-json-copy-v4",
            top_k=2,
            decision_graph=_decision_graph_fixture(),
            agent_policy_id="speech-conditioned-adaptive-evidence-gap-v2",
            agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        )
        for index in range(2)
    )
    client = _M11AdaptiveEvidenceClient(agree=True)

    outcomes = run_speech_native_match_tasks(
        core_client=client,
        tasks=tasks,
        slot_count=2,
        queue_depth=4,
        dispatch_granularity="contact",
    )

    action_formats = [
        kwargs["decoding_params"]["response_format"]
        for _messages, kwargs in client.calls
        if kwargs["matcher_policy_id"].endswith(":candidate-action-state")
    ]
    assert len(action_formats) == 2
    assert all("oneOf" in item["json_schema"]["schema"] for item in action_formats)
    assert all(outcome.decision.calls == 3 for outcome in outcomes)
    assert all(
        outcome.decision.agent_policy_id
        == "speech-conditioned-adaptive-evidence-gap-v2"
        for outcome in outcomes
    )
    for messages, _kwargs in client.calls:
        query_parts = [
            part["speech_features"]
            for part in messages[1]["content"]
            if part.get("type") == "input_speech_features"
            and part["speech_features"]["role"] == "query"
        ]
        assert len(query_parts) == 1
        assert query_parts[0]["packet_id"].startswith("slurp/train/m11-v2-sample-")


def test_m11_prompt_enumerator_reuses_the_contact_batched_runtime_path():
    envelopes = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
        request_layout_id="slot-affine-speech-prefix-v1",
    )

    by_stage = Counter(envelope["stage_kind"] for envelope in envelopes)
    assert by_stage == {
        "primary": 1,
        "retrieval": 1,
        "action": 2,
        "boundary": 4,
    }
    assert len({envelope["envelope_id"] for envelope in envelopes}) == 8
    for envelope in envelopes:
        assert set(envelope) == {
            "envelope_id",
            "stage_kind",
            "stage_id",
            "candidate_key_ids",
            "boundary_id",
            "messages",
            "response_format",
        }
        query_parts = [
            part["speech_features"]
            for part in envelope["messages"][1]["content"]
            if part.get("type") == "input_speech_features"
        ]
        assert len(query_parts) == 1
        assert query_parts[0]["role"] == "query"
        assert envelope["messages"][1]["content"][0]["type"] == (
            "input_speech_features"
        )
        rendered = json.dumps(envelope, sort_keys=True)
        assert '"value_label"' not in rendered
        assert "Candidate labels:" not in rendered


@pytest.mark.parametrize(
    ("prompt_order", "expected_types"),
    (
        ("speech-query-prefix-v2", ("input_speech_features", "text", "text")),
        ("knowledge-speech-state-v2", ("text", "input_speech_features", "text")),
    ),
)
def test_m11_wire_prompt_envelope_matches_the_transport_cache_order(
    prompt_order, expected_types
):
    envelope = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
        request_layout_id="slot-affine-speech-prefix-v1",
    )[0]

    wire = _wire_m11_prompt_envelope(envelope, prompt_order=prompt_order)

    parts = wire["messages"][1]["content"]
    assert tuple(part["type"] for part in parts) == expected_types
    assert parts[-1]["text"].startswith("[evidence speech-supply-01-")
    assert wire["messages"] != envelope["messages"]
    assert wire["response_format"] == envelope["response_format"]


def test_m11_wire_prompt_envelope_preserves_the_historical_transport_contract():
    envelope = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
    )[0]

    assert _wire_m11_prompt_envelope(
        envelope, prompt_order="speech-features-text-keys-v1"
    ) == dict(envelope)


def test_m11_knowledge_speech_state_layout_keeps_dynamic_evidence_after_speech():
    envelopes = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
        request_layout_id="slot-affine-knowledge-speech-state-v1",
    )
    action = next(
        envelope for envelope in envelopes if envelope["stage_kind"] == "action"
    )

    wire = _wire_m11_prompt_envelope(action, prompt_order="knowledge-speech-state-v2")

    parts = wire["messages"][1]["content"]
    assert tuple(part["type"] for part in parts) == (
        "text",
        "input_speech_features",
        "text",
        "text",
    )
    assert parts[0]["text"].startswith("[evidence speech-supply-00-")
    assert "Opaque key catalog" in parts[0]["text"]
    assert "Linked keys:" in parts[2]["text"]
    assert parts[3]["text"].startswith("[evidence speech-supply-02-")


@pytest.mark.parametrize(
    "user_content",
    (None, [None], [{"type": "text", "text": ""}], [{"type": "input_audio"}]),
)
def test_m11_wire_prompt_envelope_rejects_malformed_content(user_content):
    envelope = dict(
        _enumerate_m11_prompt_envelopes(
            key_cards=_KEY_CARDS,
            decision_graph=_decision_graph_fixture(),
            top_k=2,
            key_order_ids=("canonical",),
        )[0]
    )
    envelope["messages"] = (
        {"role": "system", "content": "Stable policy."},
        {"role": "user", "content": user_content},
    )

    with pytest.raises(SpeechNativeProfileError, match="M11 wire prompt"):
        _wire_m11_prompt_envelope(envelope, prompt_order="speech-query-prefix-v2")


def test_m11_prompt_fit_audit_adds_speech_and_special_token_reserves():
    envelopes = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
    )
    token_counts = {
        envelope["envelope_id"]: 100 + index for index, envelope in enumerate(envelopes)
    }

    report = _audit_m11_prompt_fit(
        envelopes=envelopes,
        token_count=lambda envelope: token_counts[envelope["envelope_id"]],
        maximum_speech_feature_tokens=169,
        maximum_completion_tokens=64,
        context_tokens_per_slot=4096,
        special_token_reserve=2,
    )

    expected_prompt = max(token_counts.values()) + 169 + 2
    assert report["schema"] == "saea-speech-native-m11-prompt-fit-v1"
    assert report["envelope_count"] == 8
    assert report["stage_counts"] == {
        "action": 2,
        "boundary": 4,
        "primary": 1,
        "retrieval": 1,
    }
    assert report["maximum_text_prompt_tokens"] == max(token_counts.values())
    assert report["maximum_prompt_tokens_upper_bound"] == expected_prompt
    assert report["context_margin_tokens"] == 4096 - expected_prompt - 64
    assert report["maximum_prompt_fits_one_slot"] is True
    assert report["model_contact"] is False


def test_m11_prompt_fit_audit_fails_closed_on_a_missing_speech_query():
    envelopes = list(
        _enumerate_m11_prompt_envelopes(
            key_cards=_KEY_CARDS,
            decision_graph=_decision_graph_fixture(),
            top_k=2,
            key_order_ids=("canonical",),
        )
    )
    malformed = dict(envelopes[0])
    malformed["messages"] = (
        malformed["messages"][0],
        {"role": "user", "content": []},
    )
    envelopes[0] = malformed

    with pytest.raises(SpeechNativeProfileError, match="exactly one query speech"):
        _audit_m11_prompt_fit(
            envelopes=tuple(envelopes),
            token_count=lambda _envelope: 10,
            maximum_speech_feature_tokens=10,
            maximum_completion_tokens=10,
            context_tokens_per_slot=100,
            special_token_reserve=2,
        )


def test_m11_prompt_token_counter_uses_template_then_marker_split_tokenization():
    envelope = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
    )[0]
    calls = []

    def post_json(path, payload):
        calls.append((path, payload))
        if path == "/apply-template":
            return {"prompt": "prefix<__media__>suffix"}
        assert path == "/tokenize"
        return {"tokens": [1, 2] if payload["content"] == "prefix" else [3]}

    count = _m11_prompt_text_token_count(
        envelope=envelope,
        media_marker="<__media__>",
        post_json=post_json,
    )

    assert count == 3
    assert calls[0][0] == "/apply-template"
    assert calls[0][1] == {
        "messages": list(envelope["messages"]),
        "response_format": envelope["response_format"],
    }
    assert [call[1] for call in calls[1:]] == [
        {"content": "prefix", "add_special": False, "parse_special": True},
        {"content": "suffix", "add_special": False, "parse_special": True},
    ]


def test_m11_prompt_token_counter_rejects_an_ambiguous_media_marker():
    envelope = _enumerate_m11_prompt_envelopes(
        key_cards=_KEY_CARDS,
        decision_graph=_decision_graph_fixture(),
        top_k=2,
        key_order_ids=("canonical",),
    )[0]

    with pytest.raises(SpeechNativeProfileError, match="exactly one media marker"):
        _m11_prompt_text_token_count(
            envelope=envelope,
            media_marker="<__media__>",
            post_json=lambda _path, _payload: {"prompt": "a<__media__>b<__media__>c"},
        )


def _real_m11_v5_material():
    binding_path = (
        REPO_ROOT / "configs/probes/g0-binding/"
        "speech-native-train-binding-evidence-e108-information-complete-knowledge.json"
    )
    graph_path = (
        REPO_ROOT / "configs/knowledge/slurp-signature-complete-decision-graph-v5.json"
    )
    cards = _load_key_cards(
        binding_path,
        "a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe",
    )
    graph = _load_decision_graph(
        graph_path,
        expected_sha256=(
            "58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc"
        ),
        key_cards=cards,
    )
    return cards, graph


def _real_m11_v5_prompt_envelopes():
    cards, graph = _real_m11_v5_material()
    return _enumerate_m11_prompt_envelopes(
        key_cards=cards,
        decision_graph=graph,
        top_k=3,
        key_order_ids=("canonical",),
    )


def test_real_m11_v5_prompt_fit_receipt_is_self_consistent_and_session_bound():
    path = (
        REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    document = _load_m11_prompt_fit_receipt(
        path=path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        binding_sha256="a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe",
        graph_id="slurp-signature-complete-decision-graph-v5",
        graph_sha256="58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc",
        packet_promotion_sha256="4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555",
        session_receipt_sha256="bfe06fa0df23f51094ce1ebfcec185523e406fee025a5203390b1e454e611da8",
        decoder_sha256="0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d",
        key_count=18,
        boundary_count=55,
        key_order_count=1,
        top_k=3,
        packet_count=108,
        context_tokens_per_slot=4096,
        maximum_completion_tokens=64,
        expected_envelopes=_real_m11_v5_prompt_envelopes(),
    )

    assert document["maximum_prompt_tokens_upper_bound"] == 2341
    assert document["context_margin_tokens"] == 1691
    assert document["worst_envelope_id"] == "boundary:B001:K003:ba"


def test_real_m11_v5_prompt_fit_receipt_admits_the_exact_formal_profile():
    path = (
        REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    cards, graph = _real_m11_v5_material()

    document = _validate_m11_prompt_fit_for_profile(
        path=path,
        expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        binding_sha256="a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe",
        decision_graph=graph,
        graph_sha256="58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc",
        packet_promotion_sha256="4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555",
        session_receipt_sha256="bfe06fa0df23f51094ce1ebfcec185523e406fee025a5203390b1e454e611da8",
        server_env={
            "LLAMA_SPEECH_DECODER_SHA256": (
                "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
            )
        },
        key_cards=cards,
        key_order_ids=("canonical",),
        top_k=3,
        packet_count=108,
        context_tokens_per_slot=4096,
        maximum_completion_tokens=64,
    )

    assert document["maximum_prompt_fits_one_slot"] is True
    assert document["context_margin_tokens"] == 1691


def test_m11_formal_prompt_fit_gate_rejects_an_unbound_decoder():
    cards, graph = _real_m11_v5_material()

    with pytest.raises(SpeechNativeProfileError, match="decoder SHA-256"):
        _validate_m11_prompt_fit_for_profile(
            path=Path("unused.json"),
            expected_sha256="1" * 64,
            binding_sha256="2" * 64,
            decision_graph=graph,
            graph_sha256="3" * 64,
            packet_promotion_sha256="4" * 64,
            session_receipt_sha256="5" * 64,
            server_env={},
            key_cards=cards,
            key_order_ids=("canonical",),
            top_k=3,
            packet_count=108,
            context_tokens_per_slot=4096,
            maximum_completion_tokens=64,
        )


def test_m11_prompt_fit_config_requires_and_binds_a_resident_session():
    values = {
        "speech_native_prompt_fit_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
        ),
        "speech_native_prompt_fit_receipt_sha256": (
            "a5931ccd3c9e02150496d0475829e926becc02ed83322d45f4121dd00ee2a289"
        ),
        "decoding_params": {"max_tokens": 64},
    }

    with pytest.raises(SpeechNativeProfileError, match="resident session"):
        _resolve_m11_prompt_fit_config(
            repo_root=REPO_ROOT,
            values=values,
            matcher_policy_id="M11",
            session_receipt=None,
        )

    path, sha256, maximum_completion_tokens = _resolve_m11_prompt_fit_config(
        repo_root=REPO_ROOT,
        values=values,
        matcher_policy_id="M11",
        session_receipt="resident-session.json",
    )
    assert (
        path
        == (
            REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
        ).resolve()
    )
    assert sha256 == values["speech_native_prompt_fit_receipt_sha256"]
    assert maximum_completion_tokens == 64
    assert _resolve_m11_prompt_fit_config(
        repo_root=REPO_ROOT,
        values={},
        matcher_policy_id="M1",
        session_receipt=None,
    ) == (None, None, None)


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"speech_native_prompt_fit_receipt": "../outside.json"}, "repository"),
        ({"decoding_params": "invalid"}, "decoding_params"),
        ({"decoding_params": {"max_tokens": 0}}, "max_tokens"),
    ),
)
def test_m11_prompt_fit_config_rejects_unsafe_or_malformed_values(overrides, message):
    values = {
        "speech_native_prompt_fit_receipt": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
        ),
        "speech_native_prompt_fit_receipt_sha256": "1" * 64,
        "decoding_params": {"max_tokens": 64},
        **overrides,
    }

    with pytest.raises(SpeechNativeProfileError, match=message):
        _resolve_m11_prompt_fit_config(
            repo_root=REPO_ROOT,
            values=values,
            matcher_policy_id="M11",
            session_receipt="resident-session.json",
        )


def test_m11_prompt_fit_receipt_rejects_hash_and_session_drift():
    path = (
        REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    common = {
        "path": path,
        "binding_sha256": (
            "a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe"
        ),
        "graph_id": "slurp-signature-complete-decision-graph-v5",
        "graph_sha256": (
            "58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc"
        ),
        "packet_promotion_sha256": (
            "4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555"
        ),
        "decoder_sha256": (
            "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
        ),
        "key_count": 18,
        "boundary_count": 55,
        "key_order_count": 1,
        "top_k": 3,
        "packet_count": 108,
        "context_tokens_per_slot": 4096,
        "maximum_completion_tokens": 64,
        "expected_envelopes": _real_m11_v5_prompt_envelopes(),
    }
    with pytest.raises(SpeechNativeProfileError, match="receipt SHA-256 mismatch"):
        _load_m11_prompt_fit_receipt(
            **common,
            expected_sha256="0" * 64,
            session_receipt_sha256=(
                "bfe06fa0df23f51094ce1ebfcec185523e406fee025a5203390b1e454e611da8"
            ),
        )
    with pytest.raises(SpeechNativeProfileError, match="runtime identity"):
        _load_m11_prompt_fit_receipt(
            **common,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            session_receipt_sha256="9" * 64,
        )


@pytest.mark.parametrize(
    ("overrides", "message"),
    (
        ({"expected_sha256": "invalid"}, "SHA-256 is malformed"),
        ({"key_count": 0}, "key_count must be positive"),
        ({"top_k": 19}, "top_k exceeds key count"),
    ),
)
def test_m11_prompt_fit_receipt_rejects_malformed_contract_arguments(
    overrides, message
):
    arguments = {
        "path": Path("unused.json"),
        "expected_sha256": "1" * 64,
        "binding_sha256": "2" * 64,
        "graph_id": "graph",
        "graph_sha256": "3" * 64,
        "packet_promotion_sha256": "4" * 64,
        "session_receipt_sha256": "5" * 64,
        "decoder_sha256": "6" * 64,
        "key_count": 18,
        "boundary_count": 55,
        "key_order_count": 1,
        "top_k": 3,
        "packet_count": 108,
        "context_tokens_per_slot": 4096,
        "maximum_completion_tokens": 64,
        "expected_envelopes": (),
        **overrides,
    }

    with pytest.raises(SpeechNativeProfileError, match=message):
        _load_m11_prompt_fit_receipt(**arguments)


def test_m11_prompt_fit_receipt_rejects_incomplete_envelope_coverage(tmp_path):
    source = (
        REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    document = json.loads(source.read_text(encoding="utf-8"))
    document["stage_counts"]["boundary"] -= 1
    path = tmp_path / "prompt-fit.json"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(SpeechNativeProfileError, match="stage coverage"):
        _load_m11_prompt_fit_receipt(
            path=path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            binding_sha256=document["binding_file_sha256"],
            graph_id=document["decision_graph_id"],
            graph_sha256=document["decision_graph_file_sha256"],
            packet_promotion_sha256=document["packet_promotion_receipt_sha256"],
            session_receipt_sha256=document["runtime"]["session_receipt_sha256"],
            decoder_sha256=document["runtime"]["decoder_sha256"],
            key_count=18,
            boundary_count=55,
            key_order_count=1,
            top_k=3,
            packet_count=108,
            context_tokens_per_slot=4096,
            maximum_completion_tokens=64,
            expected_envelopes=_real_m11_v5_prompt_envelopes(),
        )


def test_m11_prompt_fit_receipt_rejects_prompt_constructor_drift():
    path = (
        REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-22-m11-v5-prompt-fit/prompt-fit.json"
    )
    envelopes = list(_real_m11_v5_prompt_envelopes())
    drifted = dict(envelopes[0])
    drifted["messages"] = [
        *drifted["messages"],
        {"role": "system", "content": "Unregistered prompt drift."},
    ]
    envelopes[0] = drifted

    with pytest.raises(SpeechNativeProfileError, match="token accounting"):
        _load_m11_prompt_fit_receipt(
            path=path,
            expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            binding_sha256=(
                "a2ccd4b004ce2e31329bf7b69ce0ebb9cff642eec2d25cde8087ffc679203dfe"
            ),
            graph_id="slurp-signature-complete-decision-graph-v5",
            graph_sha256=(
                "58c9457312d71a7c7a13e92e53e2a4f9fff5c45a9722eb5680d0fd465fe8a2fc"
            ),
            packet_promotion_sha256=(
                "4aafd75ab86734159e39d8dedfc3ec12346d75d683119984c7b1aece761c1555"
            ),
            session_receipt_sha256=(
                "bfe06fa0df23f51094ce1ebfcec185523e406fee025a5203390b1e454e611da8"
            ),
            decoder_sha256=(
                "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
            ),
            key_count=18,
            boundary_count=55,
            key_order_count=1,
            top_k=3,
            packet_count=108,
            context_tokens_per_slot=4096,
            maximum_completion_tokens=64,
            expected_envelopes=envelopes,
        )


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
    assert trajectory["information_flow"] == {
        "schema": "m11-information-flow-v1",
        "observation_source": "speech_features",
        "candidate_factor_supply_ids": ("F001", "F002", "F003", "F004"),
        "model_selected_factor_ids": ("F003", "F004"),
        "model_selected_state_is_external_supply": False,
        "incremental_boundary_supply_ids": ("B001",),
    }

    metrics = _evaluate_m11_adaptive_evidence_gap((trajectory,))
    assert metrics["primary_correct"] == 0
    assert metrics["retrieval_top1_correct"] == 1
    assert metrics["action_state_correct"] == 1
    assert metrics["boundary_stable_correct"] == 1
    assert metrics["oracle_gain_vs_primary"] == 1
    assert metrics["new_knowledge_query_count"] == 1
    assert metrics["adaptive_boundary_query_count"] == 1
    assert metrics["final_minus_primary_correct"] == 0
    assert metrics["information_flow"]["factor_supply_query_count"] == 1
    assert metrics["information_flow"]["factor_selection_query_count"] == 1
    assert metrics["information_flow"]["boundary_supply_query_count"] == 1
    assert metrics["information_flow"]["generated_state_external_supply_count"] == 0


def test_m11_reader_preserves_the_versioned_key_conditioned_policy_identity():
    result = run_speech_native_matcher(
        core_client=_M11AdaptiveEvidenceClient(agree=True),
        sample=_SpeechSample(),
        query_descriptor=_QUERY_DESCRIPTOR,
        key_cards=_KEY_CARDS,
        key_representation_id="K1",
        matcher_policy_id="M11",
        prompt_policy_id="speech-native-json-copy-v4",
        agent_policy_id="speech-conditioned-adaptive-evidence-gap-v2",
        agent_aggregator_id="adaptive-evidence-gap-primary-control-v1",
        decision_graph=_decision_graph_fixture(),
        top_k=2,
    )
    trajectory = _parse_m11_adaptive_evidence_gap_trajectory(
        row=_m11_decision_row(result),
        sample_id="sample-1",
        speaker_id="speaker-1",
        gold_key_id="K001",
        top_k=2,
        visible_card_by_key={card.key_id: card for card in _KEY_CARDS},
        decision_graph=_decision_graph_fixture(),
    )

    assert trajectory["policy_id"] == "speech-conditioned-adaptive-evidence-gap-v2"
    metrics = _evaluate_m11_adaptive_evidence_gap((trajectory,))
    assert metrics["policy_id"] == "speech-conditioned-adaptive-evidence-gap-v2"


def _m11_policy_trajectory(
    index,
    *,
    primary="K001",
    retrieval="K001",
    action="K001",
    boundary="K001",
    gold="K001",
    boundary_id="B001",
    speaker_id=None,
    factor_kinds=("operation", "entity"),
):
    """Build one already-recorded M11 trajectory for model-free policy tests."""

    factor_ids = ("F001", "F002")
    return {
        "policy_id": "speech-conditioned-adaptive-evidence-gap-v2",
        "sample_id": f"sample-{index:03d}",
        "speaker_id": speaker_id or f"speaker-{index % 9}",
        "gold_key_id": gold,
        "primary_key_id": primary,
        "initial_top_key_ids": (primary, "K002", "K003"),
        "retrieval_key_id": retrieval,
        "action_key_id": action,
        "new_factor_ids": factor_ids,
        "new_factor_kinds": factor_kinds,
        "new_boundary_id": boundary_id,
        "boundary_ab_key_id": boundary if boundary_id is not None else None,
        "boundary_ba_key_id": boundary if boundary_id is not None else None,
        "boundary_stable_key_id": boundary if boundary_id is not None else None,
        "termination": (
            "pair-boundary-compared"
            if boundary_id is not None
            else "no-registered-pair-boundary"
        ),
        "mechanism_failure": False,
        "total_calls": 5 if boundary_id is not None else 3,
        "information_flow": {
            "schema": "m11-information-flow-v1",
            "observation_source": "speech_features",
            "candidate_factor_supply_ids": factor_ids,
            "model_selected_factor_ids": factor_ids,
            "model_selected_state_is_external_supply": False,
            "incremental_boundary_supply_ids": (
                (boundary_id,) if boundary_id is not None else ()
            ),
        },
    }


def _m11_information_complete_support_fixture():
    rows = []
    for index in range(108):
        if index < 8:
            rows.append(
                _m11_policy_trajectory(
                    index,
                    retrieval="K002",
                    action="K002",
                    boundary="K002",
                    gold="K002",
                )
            )
        elif index < 12:
            rows.append(
                _m11_policy_trajectory(
                    index,
                    retrieval="K003",
                    action="K003",
                    boundary="K002",
                    gold="K002",
                )
            )
        elif index < 30:
            rows.append(
                _m11_policy_trajectory(
                    index,
                    retrieval="K003",
                    action="K003",
                    boundary="K001",
                    factor_kinds=("operation", "target"),
                )
            )
        else:
            rows.append(
                _m11_policy_trajectory(
                    index,
                    boundary_id=None,
                )
            )
    return tuple(rows)


def test_m11_information_gate_freezes_support_before_oof_policy_selection():
    metrics = _evaluate_m11_adaptive_evidence_gap(
        _m11_information_complete_support_fixture(),
        enable_training_free_controller=True,
    )

    assert metrics["support_gate_passed"] is True
    assert metrics["boundary_incremental_helpful_action_count"] == 4
    assert metrics["boundary_stable_non_primary_action_count"] == 12
    controller = metrics["training_free_controller"]
    assert controller["policy_id"] == "speaker-grouped-oof-information-advantage-v1"
    assert controller["wrong_to_correct_vs_primary"] == 12
    assert controller["correct_to_wrong_vs_primary"] == 0
    assert (
        controller["mean_estimated_calls"] < controller["full_acquisition_mean_calls"]
    )
    assert controller["promotion_checks"]["mean_calls_below_full_acquisition"] is True
    assert controller["promotion_gate_passed"] is True


def test_m11_information_flow_attributes_factor_and_boundary_marginal_transitions():
    rows = (
        _m11_policy_trajectory(
            0,
            retrieval="K003",
            action="K003",
            boundary="K002",
            gold="K002",
        ),
        _m11_policy_trajectory(
            1,
            retrieval="K001",
            action="K001",
            boundary="K002",
            gold="K001",
        ),
        {
            **_m11_policy_trajectory(
                2,
                retrieval="K001",
                action="K002",
                boundary="K003",
                gold="K002",
            ),
            "boundary_stable_key_id": None,
        },
    )

    metrics = _evaluate_m11_adaptive_evidence_gap(rows)
    flow = metrics["information_flow"]

    assert flow["factor_supply_transition"] == {
        "attribution_scope": "factor-supply-plus-speech-reobservation",
        "eligible_count": 3,
        "unresolved_count": 0,
        "changed_prediction_count": 1,
        "helpful_transition_count": 1,
        "harmful_transition_count": 0,
        "neutral_transition_count": 2,
        "estimated_net_gain": 1,
        "helpful_sample_ids": ["sample-002"],
        "harmful_sample_ids": [],
    }
    assert flow["boundary_supply_transition"] == {
        "attribution_scope": "boundary-supply-plus-pairwise-comparison",
        "eligible_count": 2,
        "unresolved_count": 1,
        "changed_prediction_count": 2,
        "helpful_transition_count": 1,
        "harmful_transition_count": 1,
        "neutral_transition_count": 0,
        "estimated_net_gain": 0,
        "helpful_sample_ids": ["sample-000"],
        "harmful_sample_ids": ["sample-001"],
    }


@pytest.mark.parametrize(
    "flow_override",
    (
        {"model_selected_state_is_external_supply": True},
        {
            "candidate_factor_supply_ids": ("F001",),
            "model_selected_factor_ids": ("F001", "F002"),
        },
    ),
)
def test_m11_information_flow_rejects_false_external_supply_claims(flow_override):
    row = _m11_policy_trajectory(
        0,
        retrieval="K001",
        action="K002",
        boundary="K002",
        gold="K002",
    )
    corrupted = {
        **row,
        "information_flow": {**row["information_flow"], **flow_override},
    }

    with pytest.raises(
        SpeechNativeProfileError,
        match="information-flow ledger contradicts",
    ):
        _evaluate_m11_adaptive_evidence_gap((corrupted,))


def test_m11_support_does_not_enable_post_hoc_policy_without_pinned_reader():
    metrics = _evaluate_m11_adaptive_evidence_gap(
        _m11_information_complete_support_fixture()
    )

    assert metrics["support_gate_passed"] is True
    assert metrics["training_free_controller"] == {
        "status": "deferred-reader-contract-not-preregistered",
        "policy_id": "speaker-grouped-oof-information-advantage-v1",
    }


def test_m11_reader_contract_rejects_threshold_drift():
    valid = {
        "speech_native_training_free_reader_policy_id": (
            "speaker-grouped-oof-information-advantage-v1"
        ),
        "speech_native_training_free_reader_contract": {
            "support_minimum_query_count": 100,
            "support_minimum_top_k_reachable": 100,
            "support_minimum_action_variable_queries": 24,
            "support_minimum_adaptive_boundary_queries": 18,
            "support_minimum_boundary_non_primary_actions": 12,
            "support_minimum_incremental_boundary_repairs": 3,
            "support_minimum_oracle_gain": 6,
            "support_maximum_mechanism_failures": 0,
            "oof_fold_count": 3,
            "oof_minimum_state_support": 5,
            "oof_minimum_changed_prediction_support": 3,
            "oof_minimum_helpful_transitions": 2,
            "oof_minimum_estimated_net_gain": 2,
            "oof_maximum_harmful_transitions": 0,
            "promotion_minimum_net_gain": 3,
            "promotion_minimum_positive_folds": 2,
            "promotion_minimum_worst_fold_delta": 0,
            "promotion_maximum_harmful_transitions": 1,
            "promotion_minimum_action_rate": 0.05,
            "promotion_maximum_action_rate": 0.5,
            "promotion_requires_lower_mean_calls": True,
        },
    }
    policy_id, contract = _m11_reader_contract_from_values(valid, "M11")
    drifted = {
        **valid,
        "speech_native_training_free_reader_contract": {
            **valid["speech_native_training_free_reader_contract"],
            "oof_maximum_harmful_transitions": 1,
        },
    }

    assert policy_id == "speaker-grouped-oof-information-advantage-v1"
    assert contract == valid["speech_native_training_free_reader_contract"]
    with pytest.raises(SpeechNativeProfileError, match="reader contract"):
        _m11_reader_contract_from_values(drifted, "M11")


def test_m11_oof_policy_never_uses_held_out_fold_rewards_to_choose_its_actions():
    rows = _m11_information_complete_support_fixture()
    first = _evaluate_m11_oof_action_advantage_policy(rows)
    held_out_fold = first["action_audit"][0]["fold_id"]
    changed = tuple(
        {
            **row,
            "gold_key_id": (
                "K003" if audit["fold_id"] == held_out_fold else row["gold_key_id"]
            ),
        }
        for row, audit in zip(rows, first["action_audit"], strict=True)
    )

    second = _evaluate_m11_oof_action_advantage_policy(changed)

    first_actions = {
        row["sample_id"]: row["selected_action_id"]
        for row in first["action_audit"]
        if row["fold_id"] == held_out_fold
    }
    second_actions = {
        row["sample_id"]: row["selected_action_id"]
        for row in second["action_audit"]
        if row["fold_id"] == held_out_fold
    }
    assert second_actions == first_actions


def _m11_speaker_isolated_holdout_fixture():
    return tuple(
        {
            **row,
            "sample_id": f"holdout-{index:03d}",
            "speaker_id": f"holdout-speaker-{index:03d}",
        }
        for index, row in enumerate(_m11_information_complete_support_fixture())
    )


def test_m11_memory_holdout_policy_never_uses_holdout_rewards_to_choose_actions():
    memory = _m11_information_complete_support_fixture()
    holdout = _m11_speaker_isolated_holdout_fixture()

    first = _evaluate_m11_memory_holdout_action_advantage_policy(memory, holdout)
    changed = tuple({**row, "gold_key_id": "K003"} for row in holdout)
    second = _evaluate_m11_memory_holdout_action_advantage_policy(memory, changed)

    assert first["status"] == "evaluated-discovery-memory-to-unread-holdout"
    assert first["reward_scope"] == "discovery-memory-only"
    assert first["memory_query_count"] == 108
    assert first["holdout_query_count"] == 108
    assert first["sample_identity_overlap_count"] == 0
    assert first["speaker_identity_overlap_count"] == 0
    assert first["memory_support_gate_passed"] is True
    assert first["memory_promotion_gate_passed"] is True
    assert second["action_audit"] == first["action_audit"]


def test_m11_memory_holdout_policy_actions_depend_on_discovery_rewards():
    boundary_memory = _m11_information_complete_support_fixture()
    action_memory = tuple(
        {
            **row,
            **(
                {
                    "retrieval_key_id": "K003",
                    "action_key_id": "K003",
                    "boundary_ab_key_id": "K002",
                    "boundary_ba_key_id": "K002",
                    "boundary_stable_key_id": "K002",
                    "gold_key_id": "K003" if index < 8 else "K002",
                }
                if index < 12
                else {}
            ),
        }
        for index, row in enumerate(boundary_memory)
    )
    holdout = _m11_speaker_isolated_holdout_fixture()

    boundary_policy = _evaluate_m11_memory_holdout_action_advantage_policy(
        boundary_memory, holdout
    )
    action_policy = _evaluate_m11_memory_holdout_action_advantage_policy(
        action_memory, holdout
    )

    boundary_actions = {
        row["sample_id"]: row["selected_action_id"]
        for row in boundary_policy["action_audit"]
    }
    action_actions = {
        row["sample_id"]: row["selected_action_id"]
        for row in action_policy["action_audit"]
    }
    assert boundary_actions != action_actions
    assert boundary_actions["holdout-000"] == "acquire-boundary-stable"
    assert action_actions["holdout-000"] == "select-retrieval-top1"


def test_m11_memory_holdout_policy_does_not_open_holdout_rewards_before_memory_gate():
    memory = _m11_information_complete_support_fixture()[:36]
    holdout_without_rewards = tuple(
        {key: value for key, value in row.items() if key != "gold_key_id"}
        for row in _m11_speaker_isolated_holdout_fixture()
    )

    evaluation = _evaluate_m11_memory_holdout_action_advantage_policy(
        memory, holdout_without_rewards
    )

    assert evaluation["status"] == "deferred-discovery-memory-gate-failed"
    assert evaluation["memory_support_gate_passed"] is False
    assert evaluation["holdout_rewards_read"] is False
    assert evaluation["action_audit"] == []


@pytest.mark.parametrize("overlap_kind", ("sample", "speaker"))
def test_m11_memory_holdout_policy_rejects_identity_overlap(overlap_kind):
    memory = _m11_information_complete_support_fixture()
    holdout = list(_m11_speaker_isolated_holdout_fixture())
    overlap_field = "sample_id" if overlap_kind == "sample" else "speaker_id"
    holdout[0] = {**holdout[0], overlap_field: memory[0][overlap_field]}

    with pytest.raises(SpeechNativeProfileError, match=f"{overlap_kind} identity"):
        _evaluate_m11_memory_holdout_action_advantage_policy(memory, tuple(holdout))


def test_m11_oof_policy_retains_primary_when_training_memory_contains_harm():
    rows = tuple(
        _m11_policy_trajectory(
            index,
            boundary=("K002" if index % 2 == 0 else "K003"),
            gold=("K002" if index % 2 == 0 else "K001"),
            speaker_id=f"speaker-{index // 2}",
        )
        for index in range(18)
    )

    controller = _evaluate_m11_oof_action_advantage_policy(rows)

    assert controller["action_count"] == 0
    assert controller["correct_delta_vs_primary"] == 0
    assert {row["selection_reason"] for row in controller["action_audit"]} == {
        "retain:no-zero-harm-positive-advantage-action"
    }


def test_m11_reader_defers_controller_when_information_support_is_too_small():
    metrics = _evaluate_m11_adaptive_evidence_gap(
        _m11_information_complete_support_fixture()[:36]
    )

    assert metrics["support_gate_passed"] is False
    assert metrics["support_checks"]["query_count_at_least_100"] is False
    assert metrics["training_free_controller"] == {
        "status": "deferred-support-gate-failed",
        "policy_id": "speaker-grouped-oof-information-advantage-v1",
    }


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
    assert report["information_flow"] == {
        "schema": "m11-information-flow-v1",
        "factor_supply_query_count": 32,
        "factor_supply_id_reference_count": report["information_flow"][
            "factor_supply_id_reference_count"
        ],
        "factor_selection_query_count": 32,
        "factor_selection_id_reference_count": 32,
        "boundary_supply_query_count": 32,
        "boundary_supply_id_reference_count": 32,
        "generated_state_external_supply_count": 0,
    }
    assert (
        report["information_flow"]["factor_supply_id_reference_count"]
        > report["information_flow"]["factor_selection_id_reference_count"]
    )
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
        request_layout_id="slot-affine-speech-prefix-v1",
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


def test_slot_affine_speech_prefix_layout_keeps_query_before_dynamic_agent_state():
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
        request_layout_id="slot-affine-speech-prefix-v1",
        top_k=2,
    )

    assert result.key_id == "K001"
    assert len(client.calls) == 3
    system_messages = {messages[0]["content"] for messages, _kwargs in client.calls}
    assert len(system_messages) == 1
    for messages, _kwargs in client.calls:
        parts = messages[1]["content"]
        assert parts[0] == {
            "type": "input_speech_features",
            "speech_features": _QUERY_DESCRIPTOR,
        }
        assert parts[-1]["type"] == "text"
        assert parts[-1]["text"].startswith("Task instruction:\n")
    _assert_every_call_carries_query(client)


def test_speech_native_matcher_rejects_unknown_request_layout_before_contact():
    client = _SpeechFeatureClient(['{"key_id":"K001"}'])

    with pytest.raises(PsluFlightError, match="unknown request layout"):
        run_speech_native_matcher(
            core_client=client,
            sample=_SpeechSample(),
            query_descriptor=_QUERY_DESCRIPTOR,
            key_cards=_KEY_CARDS,
            key_representation_id="K1",
            matcher_policy_id="M1",
            request_layout_id="unregistered-layout",
        )

    assert client.calls == []


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
            assert messages[1]["content"][0]["speech_features"]["packet_id"] == (
                f"slurp/train/query-{sample_id.removeprefix('sample-')}"
            )
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
            request_layout_id="slot-affine-speech-prefix-v1",
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
            if kwargs["matcher_policy_id"].endswith(":intent-factors"):
                # The dispatcher admits the four tasks on four task threads, each of which submits its first
                # contact on start. A bare 10 ms sleep let task 0's SECOND contact overtake a task thread that
                # a loaded host started late (seen in a full reverse-order suite run), so the ordering below
                # asserted thread-start latency, not dispatch. Hold each first-stage contact until all four
                # task threads are alive, plus a margin for them to reach their first submission.
                deadline = time.monotonic() + 5.0
                while time.monotonic() < deadline and sum(
                    thread.name.startswith("saea-speech-native_") for thread in threading.enumerate()
                ) < 4:
                    time.sleep(0.001)
                time.sleep(0.05)
            else:
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


def test_saturated_gpu_metrics_exclude_dependency_drain_without_hiding_occupancy():
    timings = (
        {
            "started_at": "2026-08-21T12:00:00+00:00",
            "latency_seconds": 3.0,
        },
        {
            "started_at": "2026-08-21T12:00:00+00:00",
            "latency_seconds": 3.0,
        },
        {
            "started_at": "2026-08-21T12:00:02+00:00",
            "latency_seconds": 2.0,
        },
    )
    epoch = 1_787_313_600.0  # 2026-08-21T12:00:00+00:00
    resource = {
        "request_gpu_samples": [
            {"sampled_at_unix_seconds": epoch + 0.5, "utilization_pct": 100.0},
            {"sampled_at_unix_seconds": epoch + 1.5, "utilization_pct": 96.0},
            {"sampled_at_unix_seconds": epoch + 2.5, "utilization_pct": 92.0},
            {"sampled_at_unix_seconds": epoch + 3.5, "utilization_pct": 10.0},
        ]
    }

    assert profile_saturated_gpu_metrics(
        timing_rows=timings,
        resource_summary=resource,
        slot_count=2,
    ) == {
        "saturation_source": "client-http-intervals-v1",
        "minimum_active_requests": 2,
        "sample_count": 3,
        "sample_fraction_pct": 75.0,
        "utilization_median_pct": 96.0,
        "utilization_p10_pct": 92.0,
    }


def test_saturated_gpu_metrics_use_server_slots_instead_of_live_http_requests():
    timings = tuple(
        {
            "started_at": "2026-08-21T12:00:00+00:00",
            "latency_seconds": 4.0,
        }
        for _ in range(2)
    )
    resource = {
        "server_slot_sampling_configured": True,
        "server_slot_sampling_reason": None,
        "server_slot_probe_failure_count": 0,
        "request_gpu_samples": [
            {
                "sampled_at_unix_seconds": 1.0,
                "utilization_pct": 100.0,
                "server_busy_slots": 1,
                "server_total_slots": 2,
                "server_slot_sampled_at_unix_seconds": 1.005,
                "server_slot_gpu_skew_milliseconds": 5.0,
            },
            {
                "sampled_at_unix_seconds": 2.0,
                "utilization_pct": 96.0,
                "server_busy_slots": 2,
                "server_total_slots": 2,
                "server_slot_sampled_at_unix_seconds": 2.006,
                "server_slot_gpu_skew_milliseconds": 6.0,
            },
            {
                "sampled_at_unix_seconds": 3.0,
                "utilization_pct": 92.0,
                "server_busy_slots": 2,
                "server_total_slots": 2,
                "server_slot_sampled_at_unix_seconds": 3.004,
                "server_slot_gpu_skew_milliseconds": 4.0,
            },
            {
                "sampled_at_unix_seconds": 4.0,
                "utilization_pct": 10.0,
                "server_busy_slots": 0,
                "server_total_slots": 2,
                "server_slot_sampled_at_unix_seconds": 4.003,
                "server_slot_gpu_skew_milliseconds": 3.0,
            },
        ],
    }

    assert profile_saturated_gpu_metrics(
        timing_rows=timings,
        resource_summary=resource,
        slot_count=2,
    ) == {
        "saturation_source": "llama-server-slots-v1",
        "minimum_active_requests": 2,
        "sample_count": 2,
        "sample_fraction_pct": 50.0,
        "utilization_median_pct": 94.0,
        "utilization_p10_pct": 92.0,
        "server_slot_sample_count": 4,
        "server_slot_sample_coverage_pct": 100.0,
        "server_slot_probe_failure_count": 0,
        "server_slot_gpu_skew_max_milliseconds": 6.0,
        "server_slot_occupancy_mean_pct": 62.5,
    }


def test_server_slot_metric_refuses_a_profile_slot_count_mismatch():
    resource = {
        "server_slot_sampling_configured": True,
        "server_slot_probe_failure_count": 0,
        "request_gpu_samples": [
            {
                "sampled_at_unix_seconds": 1.0,
                "utilization_pct": 100.0,
                "server_busy_slots": 2,
                "server_total_slots": 3,
                "server_slot_sampled_at_unix_seconds": 1.001,
                "server_slot_gpu_skew_milliseconds": 1.0,
            }
        ],
    }

    with pytest.raises(SpeechNativeProfileError, match="slot count"):
        profile_saturated_gpu_metrics(
            timing_rows=(),
            resource_summary=resource,
            slot_count=2,
        )


def test_server_slot_metric_refuses_a_missing_slot_timestamp():
    resource = {
        "server_slot_sampling_configured": True,
        "server_slot_probe_failure_count": 0,
        "request_gpu_samples": [
            {
                "sampled_at_unix_seconds": 1.0,
                "utilization_pct": 100.0,
                "server_busy_slots": 2,
                "server_total_slots": 2,
                "server_slot_gpu_skew_milliseconds": 1.0,
            }
        ],
    }

    with pytest.raises(SpeechNativeProfileError, match="incomplete"):
        profile_saturated_gpu_metrics(
            timing_rows=(),
            resource_summary=resource,
            slot_count=2,
        )


def test_new_gpu_admission_rejects_historical_http_concurrency_proxy():
    fallback_metric = profile_saturated_gpu_metrics(
        timing_rows=(
            {
                "started_at": "2026-08-21T12:00:00+00:00",
                "latency_seconds": 3.0,
            },
        ),
        resource_summary={
            "request_gpu_samples": [
                {
                    "sampled_at_unix_seconds": 1_787_313_600.5,
                    "utilization_pct": 100.0,
                }
            ]
        },
        slot_count=1,
    )

    eligibility = profile_gpu_eligibility(fallback_metric)

    assert eligibility["saturation_source_is_server_slots"] is False
    assert eligibility["server_slot_sample_coverage_is_complete"] is False
    assert eligibility["server_slot_measurement_failures_are_zero"] is False


def test_new_gpu_admission_accepts_only_a_complete_exact_slot_metric():
    eligibility = profile_gpu_eligibility(
        {
            "saturation_source": "llama-server-slots-v1",
            "server_slot_sample_coverage_pct": 100.0,
            "server_slot_probe_failure_count": 0,
            "server_slot_gpu_skew_max_milliseconds": 10.0,
            "sample_count": 30,
            "sample_fraction_pct": 60.0,
            "utilization_median_pct": 95.0,
            "utilization_p10_pct": 90.0,
            "server_slot_occupancy_mean_pct": 90.0,
        }
    )

    assert eligibility
    assert all(eligibility.values())


def test_server_slot_event_metrics_pair_gpu_samples_without_http_probe_skew(tmp_path):
    first_line = "0.00.050.000 I log_info: startup\n"
    log_path = tmp_path / "server.log"
    log_path.write_text(
        first_line
        + "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n"
        + "0.01.100.000 I slot launch_slot_: id  1 | task 102 | processing task\n"
        + "0.02.000.000 I slot      release: id  0 | task 101 | stop processing\n"
        + "0.03.000.000 I slot      release: id  1 | task 102 | stop processing\n",
        encoding="utf-8",
    )
    epoch = 1_787_313_600.0
    resource = {
        "request_gpu_samples": [
            {"sampled_at_unix_seconds": epoch + 1.05, "utilization_pct": 80.0},
            {"sampled_at_unix_seconds": epoch + 1.50, "utilization_pct": 96.0},
            {"sampled_at_unix_seconds": epoch + 2.50, "utilization_pct": 60.0},
        ]
    }

    assert profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=len(first_line.encode("utf-8")),
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary=resource,
        slot_count=2,
        expected_contact_count=2,
    ) == {
        "saturation_source": "llama-server-slot-events-v1",
        "minimum_active_requests": 2,
        "sample_count": 1,
        "sample_fraction_pct": 100.0 / 3.0,
        "utilization_median_pct": 96.0,
        "utilization_p10_pct": 96.0,
        "server_slot_sample_count": 3,
        "server_slot_sample_coverage_pct": 100.0,
        "server_slot_measurement_failure_count": 0,
        "server_slot_clock_alignment_upper_bound_milliseconds": 50.0,
        "server_slot_occupancy_mean_pct": 200.0 / 3.0,
        "server_slot_event_count": 4,
        "server_slot_launch_count": 2,
        "server_slot_release_count": 2,
    }


def test_server_slot_event_metrics_refuse_an_unbalanced_lifecycle(tmp_path):
    first_line = "0.00.050.000 I log_info: startup\n"
    log_path = tmp_path / "server.log"
    log_path.write_text(
        first_line
        + "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n",
        encoding="utf-8",
    )

    with pytest.raises(SpeechNativeProfileError, match="unbalanced"):
        profile_server_slot_event_gpu_metrics(
            server_log_path=log_path,
            server_log_start_offset=len(first_line.encode("utf-8")),
            session_started_at="2026-08-21T12:00:00+00:00",
            resource_summary={"request_gpu_samples": []},
            slot_count=2,
            expected_contact_count=1,
        )


def test_server_slot_event_metrics_stop_at_the_attempt_log_boundary(tmp_path):
    first_line = "0.00.050.000 I log_info: startup\n"
    attempt_lines = (
        "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n"
        "0.02.000.000 I slot      release: id  0 | task 101 | stop processing\n"
    )
    later_line = (
        "0.04.000.000 I slot launch_slot_: id  1 | task 999 | processing task\n"
    )
    log_path = tmp_path / "server.log"
    log_path.write_text(first_line + attempt_lines + later_line, encoding="utf-8")

    result = profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=len(first_line.encode("utf-8")),
        server_log_end_offset=len((first_line + attempt_lines).encode("utf-8")),
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary={
            "request_gpu_samples": [
                {
                    "sampled_at_unix_seconds": 1_787_313_601.5,
                    "utilization_pct": 95.0,
                }
            ]
        },
        slot_count=2,
        expected_contact_count=1,
    )

    assert result["server_slot_launch_count"] == 1
    assert result["server_slot_release_count"] == 1


def test_gpu_admission_accepts_a_balanced_server_event_timeline():
    eligibility = profile_gpu_eligibility(
        {
            "saturation_source": "llama-server-slot-events-v1",
            "server_slot_sample_coverage_pct": 100.0,
            "server_slot_measurement_failure_count": 0,
            "server_slot_clock_alignment_upper_bound_milliseconds": 70.0,
            "sample_count": 30,
            "sample_fraction_pct": 60.0,
            "utilization_median_pct": 95.0,
            "utilization_p10_pct": 90.0,
            "server_slot_occupancy_mean_pct": 90.0,
        }
    )

    assert all(eligibility.values())


# --- 2026-08-23 E108 telemetry-defect repair -------------------------------
# docs/readiness/2026-08-23-e108-attempt-finalization-adjudication.md S3: a
# GPU sampler outage must degrade the flight receipt's GPU fields to
# NOT_AVAILABLE plus an explicit defect note and let finalization complete --
# never raise and destroy an otherwise-complete run. The 95/90 saturation
# gate stays a hard fail for a caller that opts into
# ``gpu_timeline_required=True`` (owner ruling
# docs/readiness/2026-08-23-knowledge-plane-baseline-rulings.md S2.1 keeps it
# for ENGINEERING-baseline admission).


def _balanced_two_slot_server_log(tmp_path):
    first_line = "0.00.050.000 I log_info: startup\n"
    log_path = tmp_path / "server.log"
    log_path.write_text(
        first_line
        + "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n"
        + "0.01.100.000 I slot launch_slot_: id  1 | task 102 | processing task\n"
        + "0.02.000.000 I slot      release: id  0 | task 101 | stop processing\n"
        + "0.03.000.000 I slot      release: id  1 | task 102 | stop processing\n",
        encoding="utf-8",
    )
    return log_path, len(first_line.encode("utf-8"))


def test_server_slot_event_metrics_degrade_on_sampler_start_failure(tmp_path):
    """(a) A failed sampler poll degrades to NOT_AVAILABLE + a defect note;
    finalization is never destroyed and the log-derived lifecycle fields
    (proven independently of the GPU sampler) are unaffected."""

    log_path, start_offset = _balanced_two_slot_server_log(tmp_path)
    sampler_reason = (
        "nvidia-smi sampling failed and was disabled for the rest of this "
        "run: [Errno 2] No such file or directory: 'nvidia-smi'"
    )
    resource = {"request_gpu_samples": [], "gpu_sampling_reason": sampler_reason}

    result = profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=start_offset,
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary=resource,
        slot_count=2,
        expected_contact_count=2,
    )

    assert result["sample_count"] == 0
    assert result["sample_fraction_pct"] == NOT_AVAILABLE
    assert result["utilization_median_pct"] == NOT_AVAILABLE
    assert result["utilization_p10_pct"] == NOT_AVAILABLE
    assert result["server_slot_sample_count"] == 0
    assert result["server_slot_sample_coverage_pct"] == NOT_AVAILABLE
    assert result["server_slot_occupancy_mean_pct"] == NOT_AVAILABLE
    assert result["gpu_telemetry_defect"] == sampler_reason
    # log-derived slot-event lifecycle fields still prove the run itself.
    assert result["server_slot_launch_count"] == 2
    assert result["server_slot_release_count"] == 2
    assert result["server_slot_event_count"] == 4

    eligibility = profile_gpu_eligibility(result)
    assert eligibility["gpu_telemetry_available"] is False
    # every saturation threshold is an explicit "not evaluable" False, never
    # a silent pass over missing data.
    assert eligibility["saturated_gpu_median_at_least_95"] is False
    assert eligibility["saturated_gpu_p10_at_least_90"] is False
    assert eligibility["server_slot_occupancy_at_least_90"] is False
    assert not all(eligibility.values())


def test_server_slot_event_metrics_degrade_uses_a_generic_reason_when_sampler_is_silent(
    tmp_path,
):
    """A missing/absent ``gpu_sampling_reason`` still degrades cleanly."""

    log_path, start_offset = _balanced_two_slot_server_log(tmp_path)

    result = profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=start_offset,
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary={"request_gpu_samples": []},
        slot_count=2,
        expected_contact_count=2,
    )

    assert result["gpu_telemetry_defect"] == "request GPU sample timeline is unavailable"


def test_server_slot_event_metrics_engineering_gate_fails_closed_on_missing_timeline(
    tmp_path,
):
    """(b) The engineering-admission caller (``gpu_timeline_required=True``)
    still fails closed on a missing timeline, with a clear, distinguishable
    reason instead of the old generic error."""

    log_path, start_offset = _balanced_two_slot_server_log(tmp_path)

    with pytest.raises(SpeechNativeProfileError, match="telemetry unavailable"):
        profile_server_slot_event_gpu_metrics(
            server_log_path=log_path,
            server_log_start_offset=start_offset,
            session_started_at="2026-08-21T12:00:00+00:00",
            resource_summary={
                "request_gpu_samples": [],
                "gpu_sampling_reason": "'nvidia-smi' not found on PATH",
            },
            slot_count=2,
            expected_contact_count=2,
            gpu_timeline_required=True,
        )


def test_server_slot_event_metrics_lifecycle_check_precedes_the_engineering_gate(
    tmp_path,
):
    """The slot-event lifecycle checks run and fail closed on their own
    merits before the GPU-timeline check, in both admission modes."""

    first_line = "0.00.050.000 I log_info: startup\n"
    log_path = tmp_path / "server.log"
    log_path.write_text(
        first_line
        + "0.01.000.000 I slot launch_slot_: id  0 | task 101 | processing task\n",
        encoding="utf-8",
    )

    with pytest.raises(SpeechNativeProfileError, match="unbalanced"):
        profile_server_slot_event_gpu_metrics(
            server_log_path=log_path,
            server_log_start_offset=len(first_line.encode("utf-8")),
            session_started_at="2026-08-21T12:00:00+00:00",
            resource_summary={"request_gpu_samples": []},
            slot_count=2,
            expected_contact_count=1,
            gpu_timeline_required=True,
        )


def test_server_slot_event_metrics_healthy_path_is_unaffected_by_the_new_parameter(
    tmp_path,
):
    """(c) Regression: a healthy GPU timeline is byte-identical to the
    pre-repair receipt shape, and ``gpu_timeline_required=True`` changes
    nothing when the timeline is actually present."""

    log_path, start_offset = _balanced_two_slot_server_log(tmp_path)
    epoch = 1_787_313_600.0
    resource = {
        "request_gpu_samples": [
            {"sampled_at_unix_seconds": epoch + 1.05, "utilization_pct": 80.0},
            {"sampled_at_unix_seconds": epoch + 1.50, "utilization_pct": 96.0},
            {"sampled_at_unix_seconds": epoch + 2.50, "utilization_pct": 60.0},
        ]
    }

    lenient = profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=start_offset,
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary=resource,
        slot_count=2,
        expected_contact_count=2,
    )
    strict = profile_server_slot_event_gpu_metrics(
        server_log_path=log_path,
        server_log_start_offset=start_offset,
        session_started_at="2026-08-21T12:00:00+00:00",
        resource_summary=resource,
        slot_count=2,
        expected_contact_count=2,
        gpu_timeline_required=True,
    )

    assert "gpu_telemetry_defect" not in lenient
    assert lenient == strict
    assert lenient == {
        "saturation_source": "llama-server-slot-events-v1",
        "minimum_active_requests": 2,
        "sample_count": 1,
        "sample_fraction_pct": 100.0 / 3.0,
        "utilization_median_pct": 96.0,
        "utilization_p10_pct": 96.0,
        "server_slot_sample_count": 3,
        "server_slot_sample_coverage_pct": 100.0,
        "server_slot_measurement_failure_count": 0,
        "server_slot_clock_alignment_upper_bound_milliseconds": 50.0,
        "server_slot_occupancy_mean_pct": 200.0 / 3.0,
        "server_slot_event_count": 4,
        "server_slot_launch_count": 2,
        "server_slot_release_count": 2,
    }

    eligibility = profile_gpu_eligibility(lenient)
    assert eligibility["gpu_telemetry_available"] is True


def _cuda_graph_engine_audit_inputs(*, slot_count=16, expert_types=("Q4_K", "Q6_K")):
    binary_sha256 = "a" * 64
    decoder_sha256 = "b" * 64
    build_commit = "c" * 40
    runtime = {
        "schema": "saea-runtime-receipt-v3",
        "role": "inference",
        "llama_cpp": {
            "binary_sha256": binary_sha256,
            "build_commit": build_commit,
        },
        "gguf_files": [{"path": "models/decoder.gguf", "sha256": decoder_sha256}],
    }
    session = {
        "schema": "saea-session-receipt-v2",
        "role": "inference",
        "binary_sha256": binary_sha256,
        "argv": [
            "llama-server",
            "-m",
            "/data/models/decoder.gguf",
            "--no-mmproj",
            "-np",
            str(slot_count),
        ],
        "model_files": [{"path": "models/decoder.gguf", "sha256": decoder_sha256}],
    }
    return {
        "runtime_receipt": runtime,
        "session_receipt": session,
        "checkout_commit": build_commit,
        "server_log_text": (
            "CUDA0 : NVIDIA GeForce RTX 5090 Laptop GPU "
            "| CUDA : ARCHS = 1200 | USE_GRAPHS = 1 |\n"
        ),
        "gguf_metadata": {
            "general.architecture": "qwen3vlmoe",
            "qwen3vlmoe.expert_count": 128,
            "qwen3vlmoe.expert_used_count": 8,
        },
        "expert_tensor_types": expert_types,
        "mmvq_header_text": "#define MMVQ_MAX_BATCH_SIZE 8\n",
        "mmvq_source_text": (
            "if (cc == GGML_CUDA_CC_VOLTA || "
            "cc >= GGML_CUDA_CC_ADA_LOVELACE) {\n"
            "    return MMVQ_MAX_BATCH_SIZE;\n"
            "}\n"
        ),
        "mmq_source_text": (
            "bool ggml_cuda_should_use_mmq(enum ggml_type type, int cc, "
            "int64_t ne11, int64_t n_experts) {\n"
            "  switch (type) {\n"
            "    case GGML_TYPE_Q4_K:\n"
            "    case GGML_TYPE_Q6_K:\n"
            "      mmq_supported = true;\n"
            "  }\n"
            "  if (turing_mma_available(cc)) { return true; }\n"
            "}\n"
        ),
        "cmake_cache_text": (
            "CMAKE_CUDA_ARCHITECTURES:UNINITIALIZED=120\n"
            "GGML_CUDA:BOOL=ON\n"
            "GGML_CUDA_FORCE_CUBLAS:BOOL=OFF\n"
            "GGML_CUDA_GRAPHS:BOOL=ON\n"
        ),
        "cuda_source_text": (
            "if (node->op == GGML_OP_MUL_MAT_ID) {\n"
            "  const int mmvq_mmid_max = get_mmvq_mmid_max_batch("
            "node->src[0]->type, cc);\n"
            "  if (!ggml_is_quantized(node->src[0]->type) || "
            "node->ne[2] > mmvq_mmid_max) {\n"
            "    use_cuda_graph = false;\n"
            "  }\n"
            "}\n"
        ),
        "server_context_text": (
            "std::vector<pending_speech_feature> pending_speech_features;\n"
            "auto speech_feature_batch = "
            "pack_server_speech_feature_batch(batch_items);\n"
            "auto speech_batch_view = speech_feature_batch.as_llama_batch();\n"
            "llama_decode(ctx_tgt, speech_batch_view);\n"
            'SRV_INF("decoded cross-slot speech feature batch");\n'
        ),
        "server_common_header_text": (
            "struct server_speech_feature_batch_item {};\n"
            "struct server_speech_feature_batch {};\n"
            "server_speech_feature_batch pack_server_speech_feature_batch(...);\n"
        ),
        "server_common_source_text": (
            "packed.positions[static_cast<size_t>(axis) * "
            "packed.n_tokens + token_offset + i] = item.base_pos;\n"
            "packed.seq_id_values[token_offset + i] = item.id_slot;\n"
            "packed.seq_ids[i] = &packed.seq_id_values[i];\n"
        ),
    }


def test_cuda_graph_engine_audit_closes_np16_on_blackwell_quantized_moe():
    report = _audit_cuda_graph_moe_compatibility(**_cuda_graph_engine_audit_inputs())

    assert report["schema"] == "saea-speech-native-engine-compatibility-audit-v3"
    assert report["hardware"]["cuda_compute_arch"] == 1200
    assert report["model"]["expert_count"] == 128
    assert report["engine"]["mmvq_moe_max_batch_size"] == 8
    assert (
        report["engine"]["speech_feature_transport_policy"]
        == "cross-slot-embedding-batch-v1"
    )
    assert report["profile"]["slot_count"] == 16
    assert report["profile"]["speech_feature_cross_slot_batch_static"] is True
    assert report["profile"]["full_slot_decode_exceeds_graph_limit"] is True
    assert report["decision"]["current_binary_profile_search_closed"] is True
    assert report["decision"]["live_contact_authorized"] is False


def test_cuda_graph_engine_audit_admits_sync_free_mmq_candidate_at_np16():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["cuda_source_text"] = (
        "static bool ggml_cuda_mul_mat_id_needs_sync(const ggml_tensor * dst, "
        "const int cc) {\n"
        "  const ggml_tensor * src0 = dst->src[0];\n"
        "  const ggml_tensor * src1 = dst->src[1];\n"
        "  if (ggml_cuda_should_use_mmq(src0->type, cc, src1->ne[2], "
        "/*n_experts=*/src0->ne[2])) { return false; }\n"
        "  if (ggml_cuda_should_use_mmf(src0->type, cc, WARP_SIZE, src0->ne, "
        "src0->nb, src1->ne[2], /*mul_mat_id=*/true)) { return false; }\n"
        "  return true;\n"
        "}\n"
        "if (node->op == GGML_OP_MUL_MAT_ID) {\n"
        "  if (ggml_cuda_mul_mat_id_needs_sync(node, cc)) {\n"
        "    use_cuda_graph = false;\n"
        "  }\n"
        "}\n"
        "GGML_ASSERT(ggml_cuda_mul_mat_id_needs_sync(dst, cc));\n"
    )

    report = _audit_cuda_graph_moe_compatibility(**inputs)

    assert report["engine"]["graph_guard_policy"] == "sync-aware-dispatch-mirror-v2"
    assert report["engine"]["sync_free_mmq_expert_tensor_types"] == [
        "Q4_K",
        "Q6_K",
    ]
    assert report["profile"]["full_slot_decode_graph_eligible_static"] is True
    assert report["decision"]["engine_candidate_static_admissible"] is True
    assert report["decision"]["current_binary_profile_search_closed"] is False
    assert report["decision"]["live_contact_authorized"] is False


def test_cuda_graph_engine_audit_reports_zero_dynamic_batch_events_before_contact():
    report = _audit_cuda_graph_moe_compatibility(**_cuda_graph_engine_audit_inputs())

    assert report["runtime_evidence"] == {
        "speech_feature_batch_event_count": 0,
        "speech_feature_batch_slot_total": 0,
        "speech_feature_batch_token_total": 0,
        "speech_feature_batch_max_slots": 0,
        "speech_feature_chunk_success_count": 0,
        "speech_feature_chunk_token_total": 0,
        "batch_chunk_count_matches": True,
        "batch_chunk_tokens_match": True,
        "cross_slot_batch_observed": False,
    }


def test_cuda_graph_engine_audit_counts_dynamic_cross_slot_batch_evidence():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["server_log_text"] += (
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 39\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 26\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 39\n"
        "server decoded cross-slot speech feature batch, n_slots = 3, "
        "n_tokens = 104\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 26\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 52\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 65\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 52\n"
        "slot decoded mmproj-free speech feature chunk in cross-slot batch, "
        "n_tokens = 39\n"
        "server decoded cross-slot speech feature batch, n_slots = 5, "
        "n_tokens = 234\n"
    )

    report = _audit_cuda_graph_moe_compatibility(**inputs)

    assert report["runtime_evidence"] == {
        "speech_feature_batch_event_count": 2,
        "speech_feature_batch_slot_total": 8,
        "speech_feature_batch_token_total": 338,
        "speech_feature_batch_max_slots": 5,
        "speech_feature_chunk_success_count": 8,
        "speech_feature_chunk_token_total": 338,
        "batch_chunk_count_matches": True,
        "batch_chunk_tokens_match": True,
        "cross_slot_batch_observed": True,
    }


def test_cuda_graph_engine_audit_rejects_sync_free_candidate_when_mmq_is_forced_off():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["cuda_source_text"] = (
        "static bool ggml_cuda_mul_mat_id_needs_sync(const ggml_tensor * dst, "
        "const int cc) {\n"
        "  const ggml_tensor * src0 = dst->src[0];\n"
        "  const ggml_tensor * src1 = dst->src[1];\n"
        "  if (ggml_cuda_should_use_mmq(src0->type, cc, src1->ne[2], "
        "/*n_experts=*/src0->ne[2])) { return false; }\n"
        "  if (ggml_cuda_should_use_mmf(src0->type, cc, WARP_SIZE, src0->ne, "
        "src0->nb, src1->ne[2], /*mul_mat_id=*/true)) { return false; }\n"
        "  return true;\n"
        "}\n"
        "if (node->op == GGML_OP_MUL_MAT_ID) {\n"
        "  if (ggml_cuda_mul_mat_id_needs_sync(node, cc)) {\n"
        "    use_cuda_graph = false;\n"
        "  }\n"
        "}\n"
        "GGML_ASSERT(ggml_cuda_mul_mat_id_needs_sync(dst, cc));\n"
    )
    inputs["cmake_cache_text"] = inputs["cmake_cache_text"].replace(
        "GGML_CUDA_FORCE_CUBLAS:BOOL=OFF",
        "GGML_CUDA_FORCE_CUBLAS:BOOL=ON",
    )

    report = _audit_cuda_graph_moe_compatibility(**inputs)

    assert report["engine"]["mmq_forced_off"] is True
    assert report["profile"]["full_slot_decode_graph_eligible_static"] is False
    assert report["decision"]["engine_candidate_static_admissible"] is False


def test_cuda_graph_engine_audit_rejects_per_slot_speech_feature_decode():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["cuda_source_text"] = (
        "static bool ggml_cuda_mul_mat_id_needs_sync(const ggml_tensor * dst, "
        "const int cc) {\n"
        "  const ggml_tensor * src0 = dst->src[0];\n"
        "  const ggml_tensor * src1 = dst->src[1];\n"
        "  if (ggml_cuda_should_use_mmq(src0->type, cc, src1->ne[2], "
        "/*n_experts=*/src0->ne[2])) { return false; }\n"
        "  if (ggml_cuda_should_use_mmf(src0->type, cc, WARP_SIZE, src0->ne, "
        "src0->nb, src1->ne[2], /*mul_mat_id=*/true)) { return false; }\n"
        "  return true;\n"
        "}\n"
        "if (node->op == GGML_OP_MUL_MAT_ID) {\n"
        "  if (ggml_cuda_mul_mat_id_needs_sync(node, cc)) {\n"
        "    use_cuda_graph = false;\n"
        "  }\n"
        "}\n"
        "GGML_ASSERT(ggml_cuda_mul_mat_id_needs_sync(dst, cc));\n"
    )
    inputs["server_context_text"] = (
        "const int32_t decode_result = llama_decode(ctx_tgt, batch);\n"
        'SLT_INF(*this, "decoded mmproj-free speech feature chunk");\n'
    )

    report = _audit_cuda_graph_moe_compatibility(**inputs)

    assert (
        report["engine"]["speech_feature_transport_policy"]
        == "per-slot-immediate-decode-v1"
    )
    assert report["profile"]["speech_feature_cross_slot_batch_static"] is False
    assert report["decision"]["engine_candidate_static_admissible"] is False
    assert report["decision"]["required_change"] == (
        "cross-slot speech-feature embedding batch"
    )


def test_cuda_graph_engine_audit_does_not_claim_np8_exceeds_the_static_limit():
    report = _audit_cuda_graph_moe_compatibility(
        **_cuda_graph_engine_audit_inputs(slot_count=8)
    )

    assert report["profile"]["full_slot_decode_exceeds_graph_limit"] is False
    assert report["decision"]["current_binary_profile_search_closed"] is False
    assert report["decision"]["live_contact_authorized"] is False


def test_cuda_graph_engine_audit_treats_unquantized_expert_weights_as_no_graph_path():
    report = _audit_cuda_graph_moe_compatibility(
        **_cuda_graph_engine_audit_inputs(expert_types=("Q4_K", "F32"))
    )

    assert report["engine"]["effective_moe_graph_batch_limit"] == 0
    assert report["profile"]["full_slot_decode_exceeds_graph_limit"] is True


def test_cuda_graph_engine_audit_fails_closed_on_source_contract_drift():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["cuda_source_text"] = "use_cuda_graph = true;\n"

    with pytest.raises(SpeechNativeProfileError, match="MUL_MAT_ID CUDA graph guard"):
        _audit_cuda_graph_moe_compatibility(**inputs)


def test_cuda_graph_engine_audit_fails_closed_on_receipt_commit_mismatch():
    inputs = _cuda_graph_engine_audit_inputs()
    inputs["checkout_commit"] = "d" * 40

    with pytest.raises(SpeechNativeProfileError, match="checkout commit"):
        _audit_cuda_graph_moe_compatibility(**inputs)


def test_cuda_graph_engine_audit_cli_writes_a_receipt_bound_model_free_report(
    tmp_path, monkeypatch
):
    inputs = _cuda_graph_engine_audit_inputs()
    runtime_path = tmp_path / "runtime.json"
    session_path = tmp_path / "session.json"
    server_log_path = tmp_path / "server.log"
    source_root = tmp_path / "llama.cpp"
    output_path = tmp_path / "audit.json"
    model_path = tmp_path / "decoder.gguf"
    model_path.write_bytes(b"not-read-by-test")
    inputs["session_receipt"]["argv"][2] = str(model_path)
    inputs["session_receipt"]["server_log_path"] = str(server_log_path)
    runtime_path.write_text(json.dumps(inputs["runtime_receipt"]), encoding="utf-8")
    session_path.write_text(json.dumps(inputs["session_receipt"]), encoding="utf-8")
    server_log_path.write_text(inputs["server_log_text"], encoding="utf-8")
    (source_root / "ggml/src/ggml-cuda").mkdir(parents=True)
    (source_root / "ggml/src/ggml-cuda/mmvq.cuh").write_text(
        inputs["mmvq_header_text"], encoding="utf-8"
    )
    (source_root / "ggml/src/ggml-cuda/mmvq.cu").write_text(
        inputs["mmvq_source_text"], encoding="utf-8"
    )
    (source_root / "ggml/src/ggml-cuda/mmq.cu").write_text(
        inputs["mmq_source_text"], encoding="utf-8"
    )
    (source_root / "ggml/src/ggml-cuda/ggml-cuda.cu").write_text(
        inputs["cuda_source_text"], encoding="utf-8"
    )
    (source_root / "tools/server").mkdir(parents=True)
    (source_root / "tools/server/server-context.cpp").write_text(
        inputs["server_context_text"], encoding="utf-8"
    )
    (source_root / "tools/server/server-common.h").write_text(
        inputs["server_common_header_text"], encoding="utf-8"
    )
    (source_root / "tools/server/server-common.cpp").write_text(
        inputs["server_common_source_text"], encoding="utf-8"
    )
    (source_root / "build").mkdir()
    (source_root / "build/CMakeCache.txt").write_text(
        inputs["cmake_cache_text"], encoding="utf-8"
    )
    monkeypatch.setattr(
        speech_native_module,
        "_inspect_gguf_moe_metadata",
        lambda path: (inputs["gguf_metadata"], inputs["expert_tensor_types"]),
    )
    monkeypatch.setattr(
        speech_native_module.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout=inputs["checkout_commit"] + "\n"
        ),
    )

    result = _cli_speech_native_engine_audit(
        SimpleNamespace(
            runtime_receipt=str(runtime_path),
            session_receipt=str(session_path),
            llama_cpp_root=str(source_root),
            output=str(output_path),
        )
    )

    assert result == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["decision"]["current_binary_profile_search_closed"] is True
    assert (
        report["inputs"]["runtime_receipt_sha256"]
        == hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    )
    assert (
        report["inputs"]["session_receipt_sha256"]
        == hashlib.sha256(session_path.read_bytes()).hexdigest()
    )
    assert report["inputs"]["source_files"]["mmq_source"]["sha256"] == (
        hashlib.sha256(inputs["mmq_source_text"].encode()).hexdigest()
    )
    assert report["inputs"]["source_files"]["server_context"]["sha256"] == (
        hashlib.sha256(inputs["server_context_text"].encode()).hexdigest()
    )
    assert report["inputs"]["build_files"]["cmake_cache"]["sha256"] == (
        hashlib.sha256(inputs["cmake_cache_text"].encode()).hexdigest()
    )


def test_gguf_engine_inspection_keeps_expert_used_count(tmp_path, monkeypatch):
    fields = {
        "general.architecture": SimpleNamespace(contents=lambda: "qwen3vlmoe"),
        "qwen3vlmoe.expert_count": SimpleNamespace(contents=lambda: 128),
        "qwen3vlmoe.expert_used_count": SimpleNamespace(contents=lambda: 8),
    }
    reader = SimpleNamespace(
        fields=fields,
        tensors=[SimpleNamespace(name="blk.0.ffn_gate_exps.weight", tensor_type=12)],
    )
    fake_gguf = SimpleNamespace(
        GGUFReader=lambda path, mode: reader,
        GGMLQuantizationType=lambda value: SimpleNamespace(name="Q4_K"),
    )
    monkeypatch.setitem(sys.modules, "gguf", fake_gguf)

    metadata, tensor_types = _inspect_gguf_moe_metadata(tmp_path / "decoder.gguf")

    assert metadata["qwen3vlmoe.expert_used_count"] == 8
    assert tensor_types == ("Q4_K",)


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
        request_layout_id="slot-affine-speech-prefix-v1",
        top_k=2,
        agent_policy_id="speech-conditioned-factor-graph-action-support-v1",
        agent_aggregator_id="factor-graph-primary-control-v1",
        decision_graph=loaded,
    )

    assert loaded == graph
    assert tasks[0].decision_graph == graph
    assert tasks[0].request_layout_id == "slot-affine-speech-prefix-v1"
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
            for replica in range(16):
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
                        entity_types=(
                            ("time",)
                            if scenario == "alarm" and action == "query"
                            else (
                                ("email_folder", "person")
                                if scenario == "email" and action == "query"
                                else ()
                            )
                        )
                        + (
                            ("time",)
                            if scenario == "email"
                            and action == "query"
                            and replica == 0
                            else ()
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


def _residual_information_material():
    query_seen = {"alarm": 0, "email": 0}
    material = []
    for entry in _knowledge_refinement_material():
        if entry.action == "query" and query_seen[entry.scenario] < 8:
            query_seen[entry.scenario] += 1
            entry = replace(entry, entity_types=())
        material.append(entry)
    return tuple(material)


def _multi_residual_information_material():
    """Expose two stable action/entity residuals for the same scenario pair."""

    query_seen = {"alarm": 0, "email": 0}
    material = []
    for entry in _knowledge_refinement_material():
        if entry.action == "query":
            signature = () if query_seen[entry.scenario] < 8 else ("shared_slot",)
            query_seen[entry.scenario] += 1
            entry = replace(entry, entity_types=signature)
        material.append(entry)
    for scenario in ("alarm", "email"):
        signature_replica_counts = (
            ("none", 4),
            ("shared_slot", 4),
            (f"{scenario}_exclusive", 8),
        )
        for signature_name, replica_count in signature_replica_counts:
            for replica in range(replica_count):
                index = len(material) + 1
                material.append(
                    SlurpTrainMaterial(
                        utterance_id=f"multi-residual-{index:04d}",
                        scenario=scenario,
                        action="query",
                        sentence=(
                            f"inspect {scenario} {signature_name} residual {replica}"
                        ),
                        recordings=(
                            SlurpTrainRecording(
                                sample_id=(
                                    f"slurp:train:{index:06d}:"
                                    f"audio-multi-residual-{index}"
                                ),
                                media_relpath=(
                                    "datasets/slurp/slurp_real/"
                                    f"audio-multi-residual-{index}.flac"
                                ),
                                speaker_id=f"multi-residual-speaker-{index}",
                            ),
                        ),
                        entity_types=(
                            () if signature_name == "none" else (signature_name,)
                        ),
                    )
                )
    return tuple(material)


def _action_complete_knowledge_material():
    actions = {
        "alarm": ("set", "query", "remove"),
        "iot": (
            "cleaning",
            "coffee",
            "hue_lightchange",
            "hue_lightdim",
            "hue_lightoff",
            "hue_lighton",
            "hue_lightup",
            "wemo_off",
            "wemo_on",
        ),
    }
    material = []
    item_index = 0
    for scenario, scenario_actions in actions.items():
        for action in scenario_actions:
            for replica in range(8):
                item_index += 1
                material.append(
                    SlurpTrainMaterial(
                        utterance_id=f"complete-{item_index:04d}",
                        scenario=scenario,
                        action=action,
                        sentence=f"{scenario} {action} example {replica}",
                        recordings=(
                            SlurpTrainRecording(
                                sample_id=(
                                    f"slurp:train:{item_index:06d}:"
                                    f"audio-complete-{item_index}"
                                ),
                                media_relpath=(
                                    "datasets/slurp/slurp_real/"
                                    f"audio-complete-{item_index}.flac"
                                ),
                                speaker_id=f"complete-speaker-{item_index}",
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
    assert "knowledge_snapshot" not in successor
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


def _standalone_knowledge_construction_partition(material, query_binding):
    query_items = [
        item for split in query_binding["splits"].values() for item in split["items"]
    ]
    query_samples = {item["sample_id"] for item in query_items}
    query_utterances = {item["utterance_id"] for item in query_items}
    query_sentences = {item["normalized_sentence"] for item in query_items}
    query_speakers = {item["speaker_id"] for item in query_items}
    construction = []
    for entry in material:
        if (
            entry.utterance_id in query_utterances
            or " ".join(entry.sentence.casefold().split()) in query_sentences
        ):
            continue
        recordings = tuple(
            recording
            for recording in entry.recordings
            if recording.sample_id not in query_samples
            and recording.speaker_id not in query_speakers
        )
        if recordings:
            construction.append(replace(entry, recordings=recordings))
    return (
        tuple(construction),
        query_samples,
        query_utterances,
        query_speakers,
    )


def test_standalone_train_knowledge_snapshot_binds_source_and_build_identity():
    material = _knowledge_refinement_material()
    query_binding = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    construction, _samples, _utterances, _speakers = (
        _standalone_knowledge_construction_partition(material, query_binding)
    )
    snapshot = build_speech_native_knowledge_snapshot(
        construction,
        seed=20260829,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    expected_source_ids = tuple(
        sorted(
            recording.sample_id
            for entry in construction
            for recording in entry.recordings
        )
    )
    expected_source_hash = hashlib.sha256(
        "\n".join(expected_source_ids).encode("utf-8")
    ).hexdigest()
    build_document = {
        "schema": "saea-speech-native-knowledge-build-v1",
        "source_split_identity_hash": expected_source_hash,
        "seed": 20260829,
        "policy_id": "slurp-action-stratified-specificity-v1",
        "scenarios": ["alarm", "email"],
        "key_examples_per_scenario": 5,
    }
    build_sha256 = hashlib.sha256(
        json.dumps(
            build_document,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    assert snapshot.source_sample_ids == expected_source_ids
    assert snapshot.source_split_identity_hash == expected_source_hash
    assert snapshot.snapshot_id == f"slurp-train-knowledge-{build_sha256[:16]}"
    assert snapshot.builder_policy_id == (
        f"slurp-action-stratified-specificity-v1@{build_sha256}"
    )
    assert snapshot.frozen_json()["snapshot_sha256"] == snapshot.content_hash()

    reordered = build_speech_native_knowledge_snapshot(
        tuple(reversed(construction)),
        seed=20260829,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    assert reordered.frozen_json() == snapshot.frozen_json()

    different_build = build_speech_native_knowledge_snapshot(
        construction,
        seed=20260830,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    assert different_build.builder_policy_id != snapshot.builder_policy_id
    assert different_build.content_hash() != snapshot.content_hash()


def test_standalone_train_snapshot_excludes_opt_dev_identity_groups():
    material = _knowledge_refinement_material()
    query_binding = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "email"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )
    construction, query_samples, query_utterances, query_speakers = (
        _standalone_knowledge_construction_partition(material, query_binding)
    )
    snapshot = build_speech_native_knowledge_snapshot(
        construction,
        seed=20260829,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )

    assert query_samples.isdisjoint(snapshot.source_sample_ids)
    provenance = {
        reference for value in snapshot.values for reference in value.provenance_refs
    }
    snapshot_utterances = {
        reference.removeprefix("utterance:")
        for reference in provenance
        if reference.startswith("utterance:")
    }
    snapshot_speakers = {
        reference.removeprefix("speaker:")
        for reference in provenance
        if reference.startswith("speaker:")
    }
    assert query_utterances.isdisjoint(snapshot_utterances)
    assert query_speakers.isdisjoint(snapshot_speakers)
    assert snapshot.source_partition_role == "train"


def test_standalone_train_knowledge_build_has_no_model_contact(monkeypatch):
    contacts = []

    def refuse_contact(*args, **kwargs):
        contacts.append((args, kwargs))
        raise AssertionError("knowledge BUILD must not contact a model")

    monkeypatch.setattr(FrozenCoreClient, "complete", refuse_contact)
    monkeypatch.setattr(MockCoreClient, "complete", refuse_contact)
    monkeypatch.setattr(FrozenCoreAdapter, "request", refuse_contact)
    snapshot = build_speech_native_knowledge_snapshot(
        _knowledge_refinement_material(),
        seed=20260829,
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    assert snapshot.values
    assert contacts == []


def test_action_complete_knowledge_policy_adds_one_example_for_every_train_action():
    material = _action_complete_knowledge_material()
    base = build_speech_native_binding(
        material,
        seed=20260821,
        expected_scenarios=("alarm", "iot"),
        opt_a_per_scenario=2,
        opt_b_per_scenario=1,
        gate_per_scenario=1,
        key_examples_per_scenario=5,
    )

    successor = refine_speech_native_binding_knowledge(
        base,
        material,
        seed=20260828,
        policy_id="slurp-action-complete-specificity-v2",
        expected_scenarios=("alarm", "iot"),
        key_examples_per_scenario=5,
    )

    assert successor["knowledge_revision"]["policy_id"] == (
        "slurp-action-complete-specificity-v2"
    )
    material_by_utterance = {entry.utterance_id: entry for entry in material}
    labels_by_key = {
        card["key_id"]: card["value_label"] for card in successor["key_cards"]
    }
    action_sets = {
        labels_by_key[key["key_id"]]: {
            material_by_utterance[source["utterance_id"]].action
            for source in key["sources"]
        }
        for key in successor["key_material"]
    }
    assert action_sets["alarm"] == {"set", "query", "remove"}
    assert action_sets["iot"] == {
        "cleaning",
        "coffee",
        "hue_lightchange",
        "hue_lightdim",
        "hue_lightoff",
        "hue_lighton",
        "hue_lightup",
        "wemo_off",
        "wemo_on",
    }
    iot_key = next(
        key
        for key in successor["knowledge_revision"]["keys"]
        if key["value_label"] == "iot"
    )
    assert iot_key["covered_action_mass"] == 1.0
    assert iot_key["missing_example_actions"] == []
    assert len(iot_key["selected_source_sample_ids"]) == 9
    assert successor["knowledge_revision"]["minimum_examples_per_key"] == 5
    assert successor["knowledge_revision"]["maximum_examples_per_key"] == 9
    assert sorted(successor["knowledge_revision"]["example_count_by_key"].values()) == [
        5,
        9,
    ]
    assert "examples_per_key" not in successor["knowledge_revision"]


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
        boundary_policy_id="ranked-pair-signal-v1",
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
        boundary_policy_id="ranked-pair-signal-v1",
    )
    assert graph.as_json() == repeated.as_json()


def test_shared_action_entity_graph_covers_the_actual_ambiguity_and_entity_signal():
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
        graph_id="slurp-shared-action-entity-decision-graph-v3",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-action-entity-boundaries-v2",
    )

    assert len(graph.boundaries) == 1
    boundary = graph.boundaries[0]
    assert "slurp-train-stable-shared-actions:alarm:email:query" in (
        boundary.provenance_ids
    )
    assert any(
        provenance.startswith("slurp-train-entity-rate:alarm:email:alarm:time:")
        for provenance in boundary.provenance_ids
    )
    assert any(
        provenance.startswith("slurp-train-entity-rate:alarm:email:email:email_folder:")
        for provenance in boundary.provenance_ids
    )
    assert "at least 5x more prevalent" in boundary.left_exclusion
    assert "email folder" in boundary.left_exclusion
    assert "person" in boundary.left_exclusion
    assert "time" in boundary.right_exclusion
    factors_by_id = {factor.factor_id: factor for factor in graph.factors}
    assert {
        factors_by_id[factor_id].provenance_ids[0]
        for factor_id in boundary.left_factor_ids
        if factors_by_id[factor_id].kind == "operation"
    } == {"slurp-train-action:alarm:query"}
    assert {
        factors_by_id[factor_id].provenance_ids[0]
        for factor_id in boundary.right_factor_ids
        if factors_by_id[factor_id].kind == "operation"
    } == {"slurp-train-action:email:query"}

    repeated = build_data_derived_decision_graph(
        knowledge,
        reversed(material),
        graph_id="slurp-shared-action-entity-decision-graph-v3",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-action-entity-boundaries-v2",
    )
    assert graph.as_json() == repeated.as_json()


def test_signature_lexical_graph_adds_new_pair_specific_train_prototypes():
    material = _residual_information_material()
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
        policy_id="slurp-action-complete-specificity-v2",
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )

    graph = build_data_derived_decision_graph(
        knowledge,
        material,
        graph_id="slurp-signature-lexical-decision-graph-v4",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-lexical-boundaries-v3",
    )

    assert len(graph.boundaries) == 1
    boundary = graph.boundaries[0]
    assert any(
        item.startswith("slurp-train-signature-lexical:alarm:email:query:none:support-")
        for item in boundary.provenance_ids
    )
    assert "Train-derived prototype supporting K002" in boundary.left_exclusion
    assert "Train-derived prototype supporting K001" in boundary.right_exclusion
    assert "show my active alarms" in boundary.right_exclusion
    assert "read my newest email" in boundary.left_exclusion

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        graph,
        expected_scenarios=("alarm", "email"),
    )
    assert audit["admission"]["status"] == "admitted"
    assert audit["knowledge_supply"]["signature_lexical_pair_coverage"] == {
        "covered": 1,
        "required": 1,
    }
    repeated = build_data_derived_decision_graph(
        knowledge,
        reversed(material),
        graph_id="slurp-signature-lexical-decision-graph-v4",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-lexical-boundaries-v3",
    )
    assert graph.as_json() == repeated.as_json()


def test_information_audit_blocks_pair_complete_but_relation_incomplete_supply():
    material = _multi_residual_information_material()
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
        policy_id="slurp-action-complete-specificity-v2",
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    graph = build_data_derived_decision_graph(
        knowledge,
        material,
        graph_id="slurp-signature-lexical-decision-graph-v4",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-lexical-boundaries-v3",
    )

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        graph,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["residual_ambiguity"]["residual_signature_pair_count"] == 1
    assert audit["residual_ambiguity"]["residual_signature_relation_count"] == 2
    assert audit["knowledge_supply"]["signature_lexical_pair_coverage"] == {
        "covered": 1,
        "required": 1,
    }
    assert audit["knowledge_supply"]["signature_lexical_relation_coverage"] == {
        "covered": 1,
        "required": 2,
    }
    assert audit["admission"]["status"] == "blocked"
    assert "residual_signature_lexical_supply" in audit["admission"]["failed_checks"]


def test_complete_signature_policy_supplies_every_relation_inside_one_boundary():
    material = _multi_residual_information_material()
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
        policy_id="slurp-action-complete-specificity-v2",
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )

    graph = build_data_derived_decision_graph(
        knowledge,
        material,
        graph_id="slurp-signature-complete-decision-graph-v5",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-complete-boundaries-v4",
    )
    lexical_relations = [
        item
        for item in graph.boundaries[0].provenance_ids
        if item.startswith("slurp-train-signature-lexical-v4:")
    ]
    assert len(graph.boundaries) == 1
    assert len(lexical_relations) == 2
    assert any(":query:none:" in item for item in lexical_relations)
    assert any(":query:shared_slot:" in item for item in lexical_relations)
    assert "Train-derived lexical cues supporting K001" in (
        graph.boundaries[0].right_exclusion
    )
    assert "Train-derived lexical cues supporting K002" in (
        graph.boundaries[0].left_exclusion
    )

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        graph,
        expected_scenarios=("alarm", "email"),
    )
    assert audit["knowledge_supply"]["signature_lexical_relation_coverage"] == {
        "covered": 2,
        "required": 2,
    }
    heldout = audit["knowledge_supply"]["signature_lexical_heldout_validation"]
    assert heldout["validated_relation_count"] == 2
    assert heldout["bilateral_signal_relation_count"] == 2
    assert heldout["crossfit_cue_signal_relation_count"] == 2
    assert heldout["required_relation_count"] == 2
    assert all(row["bilateral_heldout_signal"] for row in heldout["relations"])
    assert all(
        row["crossfit_lexical_cue_balanced_accuracy"] >= 0.5
        for row in heldout["relations"]
    )
    assert audit["admission"]["status"] == "admitted"

    repeated = build_data_derived_decision_graph(
        knowledge,
        reversed(material),
        graph_id="slurp-signature-complete-decision-graph-v5",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-complete-boundaries-v4",
    )
    assert graph.as_json() == repeated.as_json()


def test_information_audit_blocks_lexical_relations_without_heldout_signal():
    counters: Counter[tuple[str, tuple[str, ...]]] = Counter()
    material = []
    for entry in _multi_residual_information_material():
        signature = tuple(sorted(set(entry.entity_types)))
        if entry.action == "query" and signature in {(), ("shared_slot",)}:
            index = counters[(entry.scenario, signature)]
            counters[(entry.scenario, signature)] += 1
            signature_id = "none" if not signature else "shared-slot"
            entry = replace(
                entry,
                sentence=f"inspect shared {signature_id} residual variant {index}",
            )
        material.append(entry)
    material = tuple(material)
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
        policy_id="slurp-action-complete-specificity-v2",
        expected_scenarios=("alarm", "email"),
        key_examples_per_scenario=5,
    )
    graph = build_data_derived_decision_graph(
        knowledge,
        material,
        graph_id="slurp-signature-complete-decision-graph-v5",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-signature-complete-boundaries-v4",
    )

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        graph,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["knowledge_supply"]["signature_lexical_relation_coverage"] == {
        "covered": 2,
        "required": 2,
    }
    heldout = audit["knowledge_supply"]["signature_lexical_heldout_validation"]
    assert heldout["bilateral_signal_relation_count"] < 2
    assert heldout["crossfit_cue_signal_relation_count"] < 2
    assert audit["checks"]["residual_signature_lexical_heldout_signal"] is False
    assert audit["checks"]["residual_signature_discriminative_supply"] is False
    assert (
        audit["diagnostics"]["residual_signature_lexical_crossfit_cue_signal"] is False
    )
    assert audit["admission"]["status"] == "blocked"
    assert (
        "residual_signature_lexical_heldout_signal"
        in audit["admission"]["failed_checks"]
    )
    assert (
        "residual_signature_discriminative_supply"
        in audit["admission"]["failed_checks"]
    )


def test_dataset_semantic_boundary_supply_is_bilateral_and_source_bound():
    material = tuple(
        SlurpTrainMaterial(
            utterance_id=utterance_id,
            scenario=scenario,
            action="query",
            sentence=sentence,
            recordings=(),
            entity_types=("event_name",),
        )
        for utterance_id, scenario, sentence in (
            ("cal-1", "calendar", "what time is my meeting"),
            ("cal-2", "calendar", "when is my next appointment"),
            ("cal-3", "calendar", "show my calendar event"),
            ("dt-1", "datetime", "when is halloween"),
            ("dt-2", "datetime", "what day is christmas"),
            ("dt-3", "datetime", "when is the next holiday"),
        )
    )

    supply = pslu_module._dataset_semantic_boundary_supply(
        material,
        left="calendar",
        right="datetime",
        left_key_id="K003",
        right_key_id="K005",
    )

    assert "public or named event" in supply.left_exclusion
    assert "stored or scheduled calendar item" in supply.right_exclusion
    assert supply.provenance_ids == (
        "slurp-train-semantic-boundary-v1:calendar:datetime:calendar:"
        "sources-cal-1+cal-2+cal-3",
        "slurp-train-semantic-boundary-v1:calendar:datetime:datetime:"
        "sources-dt-1+dt-2+dt-3",
    )
    boundary = DecisionBoundaryV1(
        boundary_id="B001",
        left_key_id="K003",
        right_key_id="K005",
        left_factor_ids=("F001",),
        right_factor_ids=("F002",),
        left_exclusion=supply.left_exclusion,
        right_exclusion=supply.right_exclusion,
        provenance_ids=supply.provenance_ids,
    )
    assert pslu_module._semantic_boundary_present(boundary, supply) is True
    assert (
        pslu_module._semantic_boundary_present(
            replace(boundary, left_exclusion="provenance without semantic text"),
            supply,
        )
        is False
    )


def test_shared_action_entity_graph_fails_without_discriminative_entity_information():
    material = tuple(
        replace(entry, entity_types=("shared_entity",))
        if entry.action == "query"
        else entry
        for entry in _knowledge_refinement_material()
    )
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

    with pytest.raises(PsluFlightError, match="entity asymmetry"):
        build_data_derived_decision_graph(
            knowledge,
            material,
            graph_id="slurp-shared-action-entity-decision-graph-v3",
            expected_scenarios=("alarm", "email"),
            maximum_boundaries=1,
            boundary_policy_id="shared-action-entity-boundaries-v2",
        )


def test_information_audit_blocks_entity_only_knowledge_with_residual_ambiguity():
    material = _residual_information_material()
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
        graph_id="slurp-shared-action-entity-decision-graph-v3",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-action-entity-boundaries-v2",
    )

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        graph,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["schema"] == "saea-speech-native-information-audit-v1"
    assert audit["source"]["query_isolated_train_utterance_count"] > 0
    assert audit["label_space"]["scenario_count"] == 2
    layers = audit["information_layers"]
    assert (
        layers["action_plus_entity_signature"]["majority_oracle_accuracy"]
        >= (layers["action"]["majority_oracle_accuracy"])
    )
    assert audit["residual_ambiguity"]["stable_shared_action_pair_count"] == 1
    assert audit["knowledge_supply"]["entity_boundary_pair_coverage"] == {
        "covered": 1,
        "required": 1,
    }
    assert audit["knowledge_supply"]["signature_lexical_pair_coverage"] == {
        "covered": 0,
        "required": 1,
    }
    assert audit["admission"]["status"] == "blocked"
    assert "residual_signature_lexical_supply" in audit["admission"]["failed_checks"]


def test_information_audit_rejects_provenance_without_actual_lexical_supply():
    material = _residual_information_material()
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
        graph_id="slurp-shared-action-entity-decision-graph-v3",
        expected_scenarios=("alarm", "email"),
        maximum_boundaries=1,
        boundary_policy_id="shared-action-entity-boundaries-v2",
    )
    boundary = graph.boundaries[0]
    lexical_graph = replace(
        graph,
        boundaries=(
            replace(
                boundary,
                provenance_ids=boundary.provenance_ids
                + (
                    "slurp-train-signature-lexical:alarm:email:query:"
                    "none:support-16-16",
                ),
            ),
        ),
    )

    audit = build_speech_native_information_audit(
        knowledge,
        material,
        lexical_graph,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["knowledge_supply"]["signature_lexical_relation_coverage"] == {
        "covered": 0,
        "required": 1,
    }
    assert audit["admission"]["status"] == "blocked"
    assert "residual_signature_lexical_supply" in audit["admission"]["failed_checks"]


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


def test_speech_native_scale_capacity_audit_accounts_for_cumulative_memory_and_holdout():
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
    evidence = extend_speech_native_binding(
        base,
        material,
        seed=20260822,
        split_name="EVIDENCE-E4",
        per_scenario=2,
        expected_scenarios=("alarm", "email"),
    )

    audit = audit_speech_native_scale_capacity(
        evidence,
        material,
        seed=20260823,
        existing_memory_split_name="EVIDENCE-E4",
        cumulative_query_count=10,
        memory_query_count=6,
        holdout_query_count=4,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["schema"] == "saea-speech-native-scale-capacity-audit-v1"
    assert audit["targets"] == {
        "cumulative_query_count": 10,
        "memory_query_count": 6,
        "existing_memory_query_count": 4,
        "new_memory_query_count": 2,
        "holdout_query_count": 4,
    }
    assert audit["allocations"]["new_memory"]["query_count"] == 2
    assert audit["allocations"]["holdout"]["query_count"] == 4
    assert audit["allocations"]["cumulative_memory"]["query_count"] == 6
    assert audit["isolation"]["memory_holdout_speaker_overlap_count"] == 0
    assert audit["isolation"]["query_key_speaker_overlap_count"] == 0
    assert audit["study_wide_speaker_unseen_holdout"]["feasible"] is True
    assert audit["isolation"]["holdout_historical_nonmemory_speaker_overlap_count"] == 0
    assert (
        audit["information_interpretation"]["cumulative_memory_action_coverage_rate"]
        == 1.0
    )
    assert (
        audit["information_interpretation"][
            "cumulative_memory_scenario_action_coverage_rate"
        ]
        == 1.0
    )
    assert audit["checks"]["cumulative_memory_action_complete"] is True
    assert audit["checks"]["cumulative_memory_scenario_action_complete"] is True
    assert audit["agentloop_actionability"]["stable_action_pair_count"] == 1
    assert audit["agentloop_actionability"]["residual_signature_pair_count"] == 1
    assert (
        audit["allocations"]["cumulative_memory"]["stable_shared_action_query_count"]
        == 6
    )
    assert (
        audit["allocations"]["cumulative_memory"][
            "residual_shared_signature_query_count"
        ]
        == 6
    )
    assert (
        audit["allocations"]["cumulative_memory"][
            "entity_free_stable_action_query_count"
        ]
        == 6
    )
    assert audit["allocations"]["cumulative_memory"][
        "stable_action_pair_bilateral_coverage"
    ] == {"covered": 1, "required": 1}
    assert audit["allocations"]["cumulative_memory"][
        "residual_signature_pair_bilateral_coverage"
    ] == {"covered": 1, "required": 1}
    assert audit["allocations"]["cumulative_memory"][
        "residual_signature_pair_minimum_side_support"
    ] == {
        "minimum": 3,
        "pairs_at_least_2": 1,
        "pairs_at_least_3": 1,
        "pairs_at_least_5": 0,
        "required": 1,
    }
    assert (
        audit["allocation_policy"]["new_memory_prioritizes_residual_pair_completion"]
        is True
    )
    assert audit["allocation_policy"]["id"] == (
        "speaker-unseen-holdout-residual-support-memory-v4"
    )
    assert (
        audit["allocation_policy"][
            "new_memory_prioritizes_residual_pair_minimum_support"
        ]
        is True
    )
    assert audit["checks"]["cumulative_memory_stable_action_pair_complete"] is True
    assert audit["checks"]["cumulative_memory_residual_signature_pair_complete"] is True
    assert audit["admission"]["status"] == "feasible"
    assert audit["admission"]["new_model_contact_authorized"] is False
    serialized = json.dumps(audit, sort_keys=True)
    for forbidden_field in (
        '"sample_id"',
        '"utterance_id"',
        '"speaker_id"',
        '"normalized_sentence"',
        '"media_relpath"',
    ):
        assert forbidden_field not in serialized


def test_speech_native_scale_capacity_audit_blocks_an_infeasible_holdout_without_ids():
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
    evidence = extend_speech_native_binding(
        base,
        material,
        seed=20260822,
        split_name="EVIDENCE-E4",
        per_scenario=2,
        expected_scenarios=("alarm", "email"),
    )

    audit = audit_speech_native_scale_capacity(
        evidence,
        material,
        seed=20260823,
        existing_memory_split_name="EVIDENCE-E4",
        cumulative_query_count=40,
        memory_query_count=10,
        holdout_query_count=30,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["admission"]["status"] == "blocked"
    assert "holdout_capacity" in audit["admission"]["failed_checks"]
    assert audit["admission"]["new_model_contact_authorized"] is False
    assert '"sample_id"' not in json.dumps(audit, sort_keys=True)


def test_speech_native_scale_capacity_audit_separates_stage_and_study_speakers():
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
    evidence = extend_speech_native_binding(
        base,
        material,
        seed=20260822,
        split_name="EVIDENCE-E4",
        per_scenario=2,
        expected_scenarios=("alarm", "email"),
    )
    registered_utterances = {
        item["utterance_id"]
        for split in evidence["splits"].values()
        for item in split["items"]
    }
    historical_nonmemory_speakers = [
        item["speaker_id"]
        for split_name, split in evidence["splits"].items()
        if split_name != "EVIDENCE-E4"
        for item in split["items"]
    ]
    remapped = []
    remap_index = 0
    for entry in material:
        if entry.utterance_id in registered_utterances:
            remapped.append(entry)
            continue
        speaker = historical_nonmemory_speakers[
            remap_index % len(historical_nonmemory_speakers)
        ]
        remap_index += 1
        remapped.append(
            SlurpTrainMaterial(
                utterance_id=entry.utterance_id,
                scenario=entry.scenario,
                action=entry.action,
                sentence=entry.sentence,
                recordings=tuple(
                    SlurpTrainRecording(
                        sample_id=recording.sample_id,
                        media_relpath=recording.media_relpath,
                        speaker_id=speaker,
                    )
                    for recording in entry.recordings
                ),
                entity_types=entry.entity_types,
            )
        )

    audit = audit_speech_native_scale_capacity(
        evidence,
        tuple(remapped),
        seed=20260823,
        existing_memory_split_name="EVIDENCE-E4",
        cumulative_query_count=8,
        memory_query_count=6,
        holdout_query_count=2,
        expected_scenarios=("alarm", "email"),
    )

    assert audit["admission"]["status"] == "feasible"
    assert audit["study_wide_speaker_unseen_holdout"]["feasible"] is False
    assert audit["isolation"]["memory_holdout_speaker_overlap_count"] == 0
    assert audit["isolation"]["holdout_historical_nonmemory_speaker_overlap_count"] > 0


def test_speech_native_scale_capacity_audit_rejects_inconsistent_targets():
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

    with pytest.raises(PsluFlightError, match="must equal memory plus holdout"):
        audit_speech_native_scale_capacity(
            base,
            material,
            seed=20260823,
            existing_memory_split_name="OPT-A36",
            cumulative_query_count=11,
            memory_query_count=6,
            holdout_query_count=4,
            expected_scenarios=("alarm", "email"),
        )


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

    monkeypatch.setattr(pslu_module, "extend_speech_native_binding", fake_extend)
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


def test_binding_extension_cli_reuses_loader_for_scale_capacity_audit(
    monkeypatch, tmp_path, capsys
):
    parent = tmp_path / "parent-binding.json"
    parent.write_text('{"binding_sha256":"parent"}', encoding="utf-8")
    output = tmp_path / "scale-capacity-audit.json"
    material = _binding_material()
    captured = {}

    monkeypatch.setattr(driver_cli_module, "load_lock", lambda _path: {"lock": True})
    monkeypatch.setattr(driver_cli_module, "umbrella_lock_path", lambda: tmp_path)
    monkeypatch.setattr(driver_cli_module, "data_root", lambda: tmp_path)
    monkeypatch.setattr(
        driver_cli_module,
        "load_slurp_train_material",
        lambda lock, root, *, media_validation_workers: material,
    )

    def fake_audit(base, loaded_material, **kwargs):
        captured.update(
            {
                "base": base,
                "material": loaded_material,
                "capacity": kwargs,
            }
        )
        return {
            "schema": "saea-speech-native-scale-capacity-audit-v1",
            "admission": {"status": "feasible"},
        }

    monkeypatch.setattr(
        pslu_module,
        "audit_speech_native_scale_capacity",
        fake_audit,
    )
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--seed",
            "20260823",
            "--scale-capacity-audit-output",
            str(output),
            "--existing-memory-split",
            "EVIDENCE-E108",
            "--cumulative-query-count",
            "500",
            "--memory-query-count",
            "360",
            "--holdout-query-count",
            "140",
            "--workers",
            "8",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "base": {"binding_sha256": "parent"},
        "material": material,
        "capacity": {
            "seed": 20260823,
            "existing_memory_split_name": "EVIDENCE-E108",
            "cumulative_query_count": 500,
            "memory_query_count": 360,
            "holdout_query_count": 140,
        },
    }
    assert json.loads(output.read_text(encoding="utf-8"))["admission"] == {
        "status": "feasible"
    }
    summary = json.loads(capsys.readouterr().out)
    assert summary["scale_capacity_audit_output"] == str(output.resolve())
    assert len(summary["scale_capacity_audit_artifact_sha256"]) == 64
    assert summary["scale_capacity_status"] == "feasible"


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
        pslu_module,
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
        pslu_module,
        "refine_speech_native_binding_knowledge",
        lambda base, loaded_material, **kwargs: knowledge,
    )

    class FakeGraph:
        def as_json(self):
            return {
                "schema": "saea-decision-graph-v1",
                "graph_id": "slurp-shared-action-entity-decision-graph-v3",
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
        pslu_module,
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
            "--decision-graph-id",
            "slurp-shared-action-entity-decision-graph-v3",
            "--boundary-policy",
            "shared-action-entity-boundaries-v2",
            "--maximum-boundaries",
            "27",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "successor": knowledge,
        "material": material,
        "graph": {
            "graph_id": "slurp-shared-action-entity-decision-graph-v3",
            "maximum_boundaries": 27,
            "boundary_policy_id": "shared-action-entity-boundaries-v2",
        },
    }
    assert json.loads(graph_output.read_text(encoding="utf-8"))["graph_id"] == (
        "slurp-shared-action-entity-decision-graph-v3"
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
        pslu_module,
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


def test_binding_extension_cli_reuses_existing_loader_for_information_audit(
    monkeypatch, tmp_path, capsys
):
    parent = tmp_path / "knowledge-binding.json"
    knowledge = {
        "binding_sha256": "b" * 64,
        "knowledge_revision": {"policy_id": "slurp-action-stratified-specificity-v1"},
    }
    parent.write_text(json.dumps(knowledge), encoding="utf-8")
    audit_output = tmp_path / "information-audit.json"
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

    class FakeGraph:
        graph_id = "slurp-shared-action-entity-decision-graph-v3"

        def as_json(self):
            return {
                "schema": "saea-decision-graph-v1",
                "graph_id": self.graph_id,
                "factors": [],
                "boundaries": [],
            }

    graph = FakeGraph()
    monkeypatch.setattr(
        pslu_module,
        "build_data_derived_decision_graph",
        lambda successor, loaded_material, **kwargs: graph,
    )

    def fake_audit(successor, loaded_material, loaded_graph):
        captured.update(
            {
                "successor": successor,
                "material": loaded_material,
                "graph": loaded_graph,
            }
        )
        return {
            "schema": "saea-speech-native-information-audit-v1",
            "admission": {"status": "blocked"},
        }

    monkeypatch.setattr(
        pslu_module,
        "build_speech_native_information_audit",
        fake_audit,
    )
    exit_code = driver_cli_module.main(
        [
            "extend-speech-native-binding",
            "--parent-binding",
            str(parent),
            "--seed",
            "20260827",
            "--information-audit-output",
            str(audit_output),
            "--decision-graph-id",
            "slurp-shared-action-entity-decision-graph-v3",
            "--boundary-policy",
            "shared-action-entity-boundaries-v2",
            "--maximum-boundaries",
            "1",
        ]
    )

    assert exit_code == 0
    assert captured == {
        "successor": knowledge,
        "material": material,
        "graph": graph,
    }
    assert json.loads(audit_output.read_text(encoding="utf-8"))["admission"] == {
        "status": "blocked"
    }
    summary = json.loads(capsys.readouterr().out)
    assert summary["information_audit_output"] == str(audit_output.resolve())
    assert len(summary["information_audit_artifact_sha256"]) == 64
    assert summary["information_audit_status"] == "blocked"


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


def _rewrite_runtime_view(path, **overrides):
    document = json.loads(path.read_text(encoding="utf-8"))
    unsigned = {
        key: value for key, value in document.items() if key != "runtime_view_sha256"
    }
    unsigned["schema"] = "saea-speech-native-runtime-view-v1"
    unsigned.update(overrides)
    canonical = json.dumps(
        unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    path.write_text(
        json.dumps(
            {**unsigned, "runtime_view_sha256": hashlib.sha256(canonical).hexdigest()}
        ),
        encoding="utf-8",
    )
    return path


def test_engineering_loader_accepts_a_dev_role_runtime_view(tmp_path):
    """The DEV ladder (owner ruling 2026-08-23 section 2.2) is the FIRST
    runtime view whose split role is not ``discovery``. The loader used to
    hard-require ``discovery``, which would have forced a DEV-100 view to
    mislabel itself as a discovery split to pass promotion. It now admits
    exactly the two Stage-2 roles ``contracts.plan.STAGE2_SPLIT_ROLES``
    already names."""

    path = _rewrite_runtime_view(
        _write_engineering_gate_view(tmp_path),
        split_name="DEV-100",
        split_role="dev",
    )

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        expected_split_name="DEV-100",
        media_probe=lambda media_path: (
            hashlib.sha256(media_path.read_bytes()).hexdigest(),
            1.25,
            16000,
        ),
    )

    assert len(gate.samples) == 4


def test_engineering_loader_accepts_a_supplement_free_runtime_view(tmp_path):
    """A D1 media supplement is an ADDITIVE successor for a slice OUTSIDE the
    immutable D1 closure, and ``contracts.gate_media_identity`` refuses any
    supplement entry that duplicates a base D1 sample. SLURP devel is already
    recorded in base D1 in full, so a DEV runtime view has nothing to
    supplement and carries the whole triple as null."""

    path = _rewrite_runtime_view(
        _write_engineering_gate_view(tmp_path),
        split_name="DEV-100",
        split_role="dev",
        d1_media_supplement=None,
        d1_media_supplement_sha256=None,
        d1_manifest_sha256=None,
    )

    gate = load_speech_native_engineering_gate(
        path,
        data_root=tmp_path,
        expected_count=4,
        expected_split_name="DEV-100",
        media_probe=lambda media_path: (
            hashlib.sha256(media_path.read_bytes()).hexdigest(),
            1.25,
            16000,
        ),
    )

    assert gate.d1_media_supplement is None
    assert gate.d1_media_supplement_sha256 is None


def test_engineering_loader_refuses_a_partially_null_supplement_triple(tmp_path):
    """All-or-nothing, mirroring ``core.config._d1_media_supplement_pair``:
    a half-declared supplement is a defect, never a shorthand."""

    path = _rewrite_runtime_view(
        _write_engineering_gate_view(tmp_path),
        d1_media_supplement=None,
        d1_manifest_sha256=None,
    )

    with pytest.raises(PsluFlightError, match="d1_manifest_sha256 is malformed"):
        load_speech_native_engineering_gate(
            path,
            data_root=tmp_path,
            expected_count=4,
            media_probe=lambda _path: ("0" * 64, 1.25, 16000),
        )


def test_engineering_loader_still_refuses_a_confirmatory_runtime_view(tmp_path):
    """Widening the role check must not open the confirmatory surface: a
    runtime view can never name a confirmatory split."""

    path = _rewrite_runtime_view(
        _write_engineering_gate_view(tmp_path),
        split_name="DEV-100",
        split_role="confirmatory",
    )

    with pytest.raises(PsluFlightError, match="identity mismatch"):
        load_speech_native_engineering_gate(
            path,
            data_root=tmp_path,
            expected_count=4,
            expected_split_name="DEV-100",
            media_probe=lambda _path: ("0" * 64, 1.25, 16000),
        )


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
