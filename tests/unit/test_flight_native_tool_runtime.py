"""Fake-only custody checks for model-selected native speech tools."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime(tmp_path: Path) -> FlightRuntime:
    runtime = object.__new__(FlightRuntime)
    runtime._repo_root = tmp_path / "repo"
    runtime._data_root = tmp_path / "data"
    runtime._repo_root.mkdir()
    runtime._data_root.mkdir()
    runtime._attempt_store_factory = lambda root: AttemptStore(root / "attempts")
    runtime._live_speech_attempt_handle = None
    runtime._live_speech_provider = None
    runtime._live_speech_finalized = False
    runtime._live_speech_source_bindings = {
        "s1": {
            "packet_id": "packet/s1", "packet_sha256": "b" * 64,
            "source_audio_relpath": "audio/s1.wav", "source_audio_sha256": "a" * 64,
            "source_audio_duration_seconds": 2.5,
        }
    }
    return runtime


def test_live_config_loads_exact_pins_and_registered_roster(tmp_path):
    runtime = _runtime(tmp_path)
    inventory = runtime._data_root / "inventory.json"
    protocol = runtime._data_root / "protocol.json"
    plan_path = runtime._repo_root / "plan.json"
    inventory.write_text(json.dumps({"schema": "inventory"}))
    protocol.write_text(json.dumps({"schema": "protocol"}))
    plan = ExecutionPlan(
        run_id="SAEA-LIVE-SPEECH-1", attempt_id="attempt-1",
        execution_profile="bounded-discovery-probe", carrier_lock_key="carrier",
        split_role="discovery", split_identity_hash="c" * 64,
        planned_model_calls=1, planned_gpu_hours=1.0,
        planned_speech_audio_seconds=3, protocol_hash="d" * 64,
    ).validate()
    plan_path.write_text(json.dumps({"execution_plan": plan.__dict__}))
    spec = {
        "inventory": {"relpath": "inventory.json", "sha256": _sha(inventory)},
        "protocol": {"relpath": "protocol.json", "sha256": _sha(protocol)},
        "execution_plan": {"relpath": "plan.json", "sha256": _sha(plan_path)},
        "output_relpath": "prepared/SAEA-LIVE-SPEECH-1/attempt-1/live",
    }
    loaded = runtime._load_live_speech_observation_config(
        spec, carrier_lock_key="carrier", split_identity_hash="c" * 64
    )
    assert loaded["plan"] == plan
    assert loaded["source_bindings_sha256"]
    assert loaded["output_root"] == runtime._data_root / spec["output_relpath"]


def test_live_contact_debits_before_returning_source_bound_receipt(tmp_path):
    runtime = _runtime(tmp_path)
    runtime._live_speech_config = {
        "plan": ExecutionPlan(
            run_id="SAEA-LIVE-SPEECH-1", attempt_id="attempt-1",
            execution_profile="bounded-discovery-probe", carrier_lock_key="carrier",
            split_role="discovery", split_identity_hash="c" * 64,
            planned_model_calls=1, planned_gpu_hours=1.0,
            planned_speech_audio_seconds=3, protocol_hash="d" * 64,
        ).validate()
    }
    receipt = runtime._record_live_speech_contact(
        sample_id="s1", audio_seconds=2.5,
        source={"audio_sha256": "a" * 64, "span": {"kind": "full-utterance", "start_seconds": 0.0, "end_seconds": 2.5}},
        arguments={"span": "full-utterance"}, source_response_sha256="e" * 64,
        cache_key="f" * 64,
    )
    assert receipt["schema"] == "saea-live-speech-neural-contact-v1"
    assert runtime._live_speech_attempt_handle.actual_totals() == (1, 2.5)
    assert json.loads(runtime._live_speech_attempt_handle.path.read_text())["state"] == "OPENED"


def test_live_contact_rejects_source_mismatch_without_opening_attempt(tmp_path):
    runtime = _runtime(tmp_path)
    runtime._live_speech_config = {"plan": SimpleNamespace()}
    with pytest.raises(FlightRuntimeError, match="source identity"):
        runtime._record_live_speech_contact(
            sample_id="s1", audio_seconds=2.5,
            source={"audio_sha256": "9" * 64, "span": {"kind": "full-utterance", "start_seconds": 0.0, "end_seconds": 2.5}},
            arguments={}, source_response_sha256="e" * 64, cache_key="f" * 64,
        )
    assert runtime._live_speech_attempt_handle is None


def test_phase_tool_contact_counts_action_without_speech_debit(tmp_path):
    runtime = _runtime(tmp_path)
    counted = []
    runtime._client = SimpleNamespace(record_tool_call=lambda **facts: counted.append(facts))
    receipt = runtime._record_phase_tool_contact(
        sample_id="s1", phase="decision-1", next_phase="decision-2",
        tool_id="saea-tool-live-speech-observation-v1",
        arguments={"span": "full-utterance"}, source_response_sha256="e" * 64,
        request_id="request-1", tool_call_id="call-1", tool_calls_sha256="f" * 64,
    )
    assert counted == [{"count": 1}]
    assert receipt["schema"] == "saea-native-phase-tool-contact-v1"
    assert receipt["speech_packet_id"] == "packet/s1"
    assert runtime._live_speech_attempt_handle is None


def test_native_dispatcher_receives_live_provider_and_custody_callback(tmp_path):
    runtime = _runtime(tmp_path)
    provider = object()
    runtime._live_speech_config = {"inventory": {}, "protocol": {}, "output_root": tmp_path}
    runtime._live_speech_provider = provider
    runtime._speech_observations = None
    runtime._experience_memory = None
    runtime._composed = SimpleNamespace(values={"phase_planner": None})
    runtime._phase_tool_specs = lambda _policy: {"decision-1": {"mode": "native-tools"}}
    runtime._phase_knowledge_catalog = lambda _snapshot: object()
    captured = {}

    class Dispatcher:
        native_enabled = True

        def native_tool_schemas(self):
            return ({"type": "function"},)

    def builder(values, program, **kwargs):
        captured.update(kwargs)
        return Dispatcher()

    runtime._phase_tool_builder = builder
    program = SimpleNamespace(stop_rule="native-answer-or-tool")
    dispatcher = runtime._build_phase_tool_dispatcher(
        "native-answer-or-tool-v1", program,
        binding={"knowledge_snapshot": object(), "supply_for_phase": None},
        sink=object(), client=None,
    )
    assert dispatcher.native_tool_schemas() == ({"type": "function"},)
    assert captured["live_speech_observations"] is provider
    assert captured["tool_contact"] == runtime._record_phase_tool_contact


def test_seal_closes_provider_and_finalizes_cold_attempt_with_receipt(tmp_path):
    runtime = _runtime(tmp_path)
    runtime._live_speech_config = {
        "plan": ExecutionPlan(
            run_id="SAEA-LIVE-SPEECH-1", attempt_id="attempt-1",
            execution_profile="bounded-discovery-probe", carrier_lock_key="carrier",
            split_role="discovery", split_identity_hash="c" * 64,
            planned_model_calls=1, planned_gpu_hours=1.0,
            planned_speech_audio_seconds=3, protocol_hash="d" * 64,
        ).validate(),
        "source_bindings_sha256": "1" * 64,
        "pins": {"inventory": {}, "protocol": {}, "execution_plan": {}},
    }
    runtime._record_live_speech_contact(
        sample_id="s1", audio_seconds=2.5,
        source={"audio_sha256": "a" * 64, "span": {"kind": "full-utterance", "start_seconds": 0.0, "end_seconds": 2.5}},
        arguments={}, source_response_sha256="e" * 64, cache_key="f" * 64,
    )

    class Provider:
        closed = False

        def close(self):
            self.closed = True

        def receipt(self):
            return {"schema": "provider", "new_forwards": 1, "cache_hits": 0}

    provider = Provider()
    runtime._live_speech_provider = provider
    closed = runtime._close_live_speech_provider(finalize=True)
    state = json.loads(runtime._live_speech_attempt_handle.path.read_text())
    assert provider.closed is True
    assert state["state"] == "FINALIZED"
    assert state["finalization"]["sha256"] == closed["sha256"]


def test_explicit_fit_audio_cap_replaces_generation_cap():
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"live_phase_fit_audio_seconds_cap": 6170})
    plan = ExecutionPlan(
        run_id="SAEA-GEN", attempt_id="a", execution_profile="bounded-discovery-probe",
        carrier_lock_key="carrier", split_role="discovery", split_identity_hash="c" * 64,
        planned_model_calls=10, planned_gpu_hours=1.0,
        planned_speech_audio_seconds=7351, protocol_hash="d" * 64,
    ).validate()
    assert runtime._fit_base_plan(plan).planned_speech_audio_seconds == 6170
